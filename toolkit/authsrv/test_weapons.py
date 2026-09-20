"""test_weapons.py -- WEAPONS-W1: one weapon table, a row and an item per type.

The three item-type dicts in authsrv.py (attribute, rates key, weapon_req bit) were
literals with four rows; they are built from content [weapon_type.*] now. This test
holds the KNOWN-GOOD ARM still -- the four melee rows read exactly what the literals
said -- and then checks what the new rows claim against things that can refute them:
the skill table's own weapon_req -> attribute column, the rates table, the item rows'
modifier words, and the character the server actually builds when it is handed each
weapon. No vault: everything here is content and code.
"""
import math
import collections
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import agents  # noqa: E402
import authsrv  # noqa: E402
import combatmath  # noqa: E402

LEDGER = checks.Ledger("weapons: one table, a row and an item per type", floor=237)   # the BARE-MACHINE number: 237 = 228 + 9 (section 26, Fireball's splash, 2026-09-20; a vault run gives 254 -- the tape's bursts are the one vault-only check); before that 228 = 219 + 9 (section 25, a body's spell projectile, 2026-09-20; a vault run gives 244 -- the tape's activations are the one vault-only check); before that 219 = 208 + 11 (section 24, a player's spell projectile, 2026-09-20; a vault run gives 234 -- the tapes' speeds are the one vault-only check); before that 208 = 203 + 5 (section 23, base armour penetration, 2026-09-19; a vault run gives 222 -- the six checks that read the skills table are vault-only); before that 203 = 198 + 5 (section 22, a spell's own damage type, 2026-09-19; a vault run gives 211 -- the Dancing Daggers tape is the one vault-only check); before that 198 = 195 + 3 (section 19 gains identifier 573, 2026-09-19; a vault run gives 205); before that 195 = 186 + 9 (section 21, WEAPONS-Q2 / the hornbow, 2026-09-19; a vault run gives 202 -- the extractor read-back is the one vault-only check); before that 186 = 177 + 9 (section 20, WEAPONS-W5b, 2026-09-19; a vault run gives 192 -- the three press checks want skill 83's row); before that 177 = 155 + 22 (section 19, WEAPONS-W4, 2026-09-19; a vault run gives 180 -- the pinned-client read-back is the one vault-only check); before that 155 = 151 + 4 (section 18, the W9 desk close, 2026-09-19; a vault run gives 157); before that 151 = 129 + 22 (section 18, WEAPONS-W9, 2026-09-19; a vault run gives 152); before that 129 = 114 + 15 (sections 15-17, 2026-09-19; a vault run gives 131); before that 114 without the vault's full skills table (section 2 skips), 115 with it; from green runs (WEAPONS-W2c: 43 -> 59; W2b: 59 -> 66; W5: 66 -> 74; W4c: 74 -> 84; W2d: 84 -> 91; W2e: 91 -> 101; W2f: 101 -> 105; W7: 105 -> 114)
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
    refused = False
    try:
        authsrv.apply_party_character({"player_weapon": "hostile_bow"})
    except SystemExit:
        refused = True
    check(1 not in authsrv.WEAPON_TYPE_ROW
          and authsrv.WEAPON_TYPE_ROW[28].get("holder") == "hostile" and refused
          and [t for t, r in authsrv.WEAPON_TYPE_ROW.items() if r.get("holder")] == [28],
          "the hostile-only types (WEAPONS-C2): 1 is no row at all, 28 is a row a HOSTILE "
          "holds (WEAPONS-W6a) and the player loader REFUSES an item of it")
    bits = list(authsrv.WEAPON_TYPE_REQ_BIT.values())
    check(len(set(bits)) == len(bits) and all(b and b & (b - 1) == 0 for b in bits)
          and sum(bits) == 0xFB,
          "every weapon_req bit is ONE bit, none shared, and together they are the mask's "
          "seven named bits (0x01 0x02 0x08 0x10 0x20 0x40 0x80)", hex(sum(bits)))
    check(all(authsrv.WEAPON_TYPE_RATE[t] in agents.ATTACK_SPEED
              for t in authsrv.WEAPON_TYPE_RATE)
          and {t: agents.ATTACK_SPEED[k] for t, k in authsrv.WEAPON_TYPE_RATE.items()}
          == {2: 1.33, 27: 1.33, 32: 1.33, 15: 1.75, 22: 1.75, 26: 1.75,
              35: 1.5, 36: 1.5, 5: 2.475, 28: 1.75},
          "every rate is an [attack_speed.rates] key -- 1.33 / 1.75 / 2.475 are the numbers "
          "retail's 0x0035 sent while the type was held (test_weaponcensus), 1.5 is WIKI's")
    check(22 not in authsrv.WEAPON_TYPE_ATTRIBUTE and 26 not in authsrv.WEAPON_TYPE_ATTRIBUTE
          and 22 not in authsrv.WEAPON_TYPE_REQ_BIT,
          "a caster weapon has no mastery and no weapon_req bit: attribute 0 and req_bit 0 "
          "stay OUT of the dicts, so .get() means what it meant")
    by_delivery = {}
    for typ, row in authsrv.WEAPON_TYPE_ROW.items():
        by_delivery.setdefault(row["delivery"], set()).add(typ)
    check(by_delivery == {"melee": {2, 27, 32, 15, 35}, "projectile": {36, 5, 22, 26, 28},
                          "none": {24, 12}},
          "delivery: five melee types, five projectile types (the hostile's among them), "
          "two off-hand items",
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


PLAYER, FOE = 1, 10


def _world(distance):
    entry = {"name": "suit", "dead": False, "died_at": 0.0,
             "health": 9000.0, "max_health": 9000.0, "last_hit": 0.0,
             "pos": (float(distance), 0.0), "plane": 0, "armor_rating": 60.0,
             "allegiance": agents.ALLEGIANCE_HOSTILE,
             "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
             "effects": 0, "attacks_back": False, "skills": (), "skill_ready": []}
    return {"agents": {FOE: entry}, "pos": (0.0, 0.0), "player_health": 480.0}


def _f(word):
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def _one_shot(weapon, distance):
    """Open one swing through the real loop, pass its windup, pass its flight.
    Returns (state, what went out at the windup, what went out at the arrival)."""
    authsrv.apply_party_character({"player_weapon": weapon})
    st, sent = _world(distance), []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    authsrv.begin_attack(send, st, FOE, 1)
    authsrv.attack_tick(send, st, 1)
    opened = len(sent)
    if st.get("player_swing"):
        st["player_swing"]["lands_at"] -= 30.0
    authsrv.attack_tick(send, st, 1)
    at_windup = sent[opened:]
    mark = len(sent)
    for shot in st.get("player_projectiles") or ():
        shot["arrives_at"] -= 30.0
    authsrv.projectile_tick(send, st, 1)
    return st, at_windup, sent[mark:]


def section_ranged():
    print("\n5. WEAPONS-W2a: the windup RELEASES, the hit lands a flight later")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE)
    words = lambda batch: [v for op, v in batch if op == 0x00A3]              # noqa: E731
    prop1 = lambda batch: [v for op, v in batch                                # noqa: E731
                           if op == 0x009F and v[0] == agents.GV_MELEE_ATTACK_FINISHED]
    try:
        hows = {}
        for key in ("starter_bow", "starter_wand", "caster_staff", "starter_spear",
                    "starter_sword", "starter_scythe"):
            authsrv.apply_party_character({"player_weapon": key})
            hows[key] = authsrv.player_ranged()
        check(hows["starter_bow"] == {"projectile": 143, "arrow": 1, "damage_type": 1,
                                      "speed": 1600.0, "range": 1498.0}
              and hows["starter_wand"]["projectile"] == 0 and hows["starter_wand"]["arrow"] == 0
              and hows["starter_wand"]["damage_type"] == 6
              and (hows["caster_staff"]["projectile"], hows["caster_staff"]["damage_type"]) == (5, 8),
              "how each ranged weapon shoots: the bow's DEFAULT 143 (it carries no 617), the "
              "wand's and the staff's own 617, each with its own 587 damage type -- the staff's "
              "(5, 8) is a pair retail's 0x00A4 / 0x00A7 carry together", str(hows["starter_bow"]))
        check(hows["starter_sword"] is None and hows["starter_scythe"] is None
              and hows["starter_spear"] == {"projectile": 143, "arrow": 1, "damage_type": 1,
                                            "speed": 1600.0, "range": 1004.0},
              "a sword and a scythe swing; the SPEAR shoots since RUN-WEAPONS-1A named its "
              "projectile (143 / flag 1 / 1594 u/s, 54 of 54) -- section 15 has the throw",
              str(hows["starter_spear"]))
        recurve = dict(agents.item_template("starter_bow"))
        recurve["modifiers"] = [0x26180300 if (w >> 20) & 0x3FF == 609 else w
                                for w in recurve["modifiers"]]
        agents.PLAYER_WEAPON = recurve
        check((authsrv.player_ranged()["speed"], authsrv.player_ranged()["range"])
              == (2800.0, 1273.0),
              "a bow's 609 CLASS picks its speed and range: class 3 is the measured 2800 u/s")
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        far = authsrv.attack_reach()
        authsrv.apply_party_character({"player_weapon": "starter_sword"})
        check(far == 1498.0 and authsrv.attack_reach() == authsrv.ATTACK_REACH == 144.0,
              "the press opens from the WEAPON's range: 1498 with the bow, 144 with a sword")

        st, at_windup, at_arrival = _one_shot("starter_bow", 800.0)
        launch = [v for op, v in at_windup if op == 0x00A4]
        check(len(launch) == 1 and launch[0][0] == PLAYER and list(launch[0][1]) == [800.0, 0.0]
              and launch[0][2] == 0 and abs(_f(launch[0][3]) - 0.5) < 1e-6
              and launch[0][4:] == [143, 1, 1],
              "at the windup: ONE 0x00A4 [me, the target's position, 0, flight, 143, handle "
              "1, arrow 1] -- 800 u at 1600 u/s is half a second", str(launch))
        check([op for op, _v in at_windup] == [0x00A4],
              "and NOTHING lands there: no word, no property 1, the launch alone",
              str([hex(op) for op, _v in at_windup]))
        ops = [op for op, _v in at_arrival]
        check(ops[0] == 0x00A7 and at_arrival[0][1] == [PLAYER, 1, 1]
              and ops.count(0x00A7) == 1 and len(words(at_arrival)) == 1
              and words(at_arrival)[0][1:3] == [FOE, PLAYER],
              "a flight later: 0x00A7 [me, handle 1, damage type 1] FIRST and then the hit's "
              "own batch with its one word -- retail's order",
              str([(hex(op), v) for op, v in at_arrival]))
        held, sent_h = _world(800.0), []
        held["action_hold"] = 1
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        authsrv._land_player_swing(lambda op, vals, label="", quiet=False:
                                   sent_h.append((op, list(vals))), held, 1, {"target": FOE})
        check([op for op, _v in sent_h] == [0x00A4, 0x009F] and sent_h[1][1] == [8, PLAYER, 0],
              "a movement hold, when one is up, ends AT THE RELEASE -- retail's [8, me, 0] "
              "rides the launch or follows it, never the hit", str(sent_h[1:]))
        check(not prop1(at_arrival) and not st.get("player_projectiles"),
              "no property 1 closes a shot (retail sends none), and the handle is spent")

        st, at_windup, _ = _one_shot("starter_wand", 320.0)
        bolt = [v for op, v in at_windup if op == 0x00A4]
        check(len(bolt) == 1 and abs(_f(bolt[0][3]) - 0.2) < 1e-6 and bolt[0][4:] == [0, 1, 0],
              "a wand: projectile 0 (its own 617), arrow 0, 320 u in 0.2 s", str(bolt))

        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        st, sent = _world(600.0), []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        for _ in range(2):
            authsrv.launch_player_projectile(send, st, 1, {"target": FOE},
                                             authsrv.player_ranged())
        due = authsrv.combat_deadlines(st)
        check([v[5] for op, v in sent if op == 0x00A4] == [1, 2]
              and all(s["arrives_at"] in due for s in st["player_projectiles"]),
              "two in the air: handles 1 and 2 (retail counts a shooter's outstanding "
              "shots), and both arrivals are combat DEADLINES the world thread wakes for")
        st["agents"][FOE]["dead"] = True
        sent.clear()
        for shot in st["player_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        check([op for op, _v in sent] == [0x00A7, 0x00A7],
              "an arrow whose target died in flight is still CLOSED (0x00A7) and lands nothing")

        authsrv.RANGED_DELIVERY = False
        try:
            _st, at_windup, at_arrival = _one_shot("starter_bow", 100.0)
            check(authsrv.player_ranged() is None and authsrv.attack_reach() == 144.0
                  and len(words(at_windup)) == 1 and len(prop1(at_windup)) == 1
                  and not any(op in (0x00A4, 0x00A7) for op, _v in at_windup + at_arrival),
                  "--no-projectiles: the word and property 1 at the windup from melee reach, "
                  "no 0x00A4 and no 0x00A7 -- the arm before today")
        finally:
            authsrv.RANGED_DELIVERY = True
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE) = saved


HERO, INT, INT_T, FLOAT_T = 200, 0x009F, 0x00A0, 0x00A3


def _body_world(hostile_pos, **hostile):
    """A player at the origin, one hostile (agent 10) and one party caster (200)."""
    foe = {"name": "archer", "dead": False, "died_at": 0.0, "health": 200.0,
           "max_health": 200.0, "last_hit": 0.0, "pos": hostile_pos, "plane": 0,
           "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": 1.75,
           "effects": 0, "attacks_back": True, "skills": (), "skill_ready": [],
           "npc": {"profession": 2, "level": 5}}
    foe.update(hostile)
    monk = {"name": "monk", "dead": False, "died_at": 0.0, "health": 100.0,
            "max_health": 100.0, "last_hit": 0.0, "pos": (0.0, 110.0), "plane": 0,
            "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0, "attack_speed": 1.75,
            "attacks_back": False, "skills": (), "skill_ready": [],
            "npc": {"profession": 3, "level": 5}, "party_slot": 0,
            "weapon_item": "caster_staff"}
    return {"agents": {FOE: foe, HERO: monk}, "pos": (0.0, 0.0),
            "player_health": 480.0, "player_dead": False}


def section_bodies():
    print("\n6. WEAPONS-W6a: heroes and hostiles shoot")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    melee_close = lambda batch, who: [v for op, v in batch if op == INT              # noqa: E731
                                      and v[:2] == [agents.GV_MELEE_ATTACK_FINISHED, who]]
    hows = {k: authsrv.body_ranged({"weapon_item": k})
            for k in ("hostile_bow", "hostile_bolt", "caster_staff", "starter_hammer")}
    check((hows["hostile_bow"]["projectile"], hows["hostile_bow"]["arrow"],
           hows["hostile_bow"]["damage_type"], hows["hostile_bow"]["speed"]) == (143, 1, 1, 1200.0)
          and (hows["hostile_bolt"]["projectile"], hows["hostile_bolt"]["arrow"],
               hows["hostile_bolt"]["damage_type"]) == (1, 0, 3)
          and hows["starter_hammer"] is None and authsrv.body_ranged({}) is None
          and authsrv.body_ranged({"weapon_item": "no_such_item"}) is None,
          "what a body HOLDS decides: a type-28 bow shoots arrow 143 (flag DERIVED, 1), its "
          "bolt-thrower projectile 1 (flag 0, kind 3 -- retail's pair, 145 of 145), both at "
          "1200 u/s; a hammer, empty hands and a missing item row swing", str(hows["hostile_bow"]))
    check(authsrv.body_reach({"weapon_item": "hostile_bow"}) == 1248.0
          and authsrv.body_reach({"weapon_item": "starter_hammer"}) == authsrv.enemy_reach()
          and authsrv.party_reach({"weapon_item": "caster_staff", "npc": {"profession": 3}})
          == authsrv.PARTY_RANGED_REACH == 1248.0,
          "an archer's reach is its range, a hammer's the melee disc; a party caster's staff "
          "reads 1248 -- the number PARTY_RANGED_REACH already was, so its stance is unmoved")

    # a HOSTILE archer 600 u out, its swing at the windup, through the real tick
    st = _body_world((600.0, 0.0), weapon_item="hostile_bow", swinging=True,
                     swing_lands_at=time.time() - 0.01, last_swing=time.time())
    authsrv.enemy_attack_tick(send, st, 1)
    launch = [v for op, v in sent if op == 0x00A4]
    check(len(launch) == 1 and launch[0][0] == FOE and list(launch[0][1]) == [0.0, 0.0]
          and abs(_f(launch[0][3]) - 0.5) < 1e-6 and launch[0][4:] == [143, 1, 1]
          and not [v for op, v in sent if op == FLOAT_T],
          "a hostile archer's windup from 600 u: ONE 0x00A4 [it, the PLAYER's position, 0, "
          "0.5 s at 1200 u/s, 143, handle 1, arrow 1] and nothing lands", str(launch))
    health = st["player_health"]
    sent.clear()
    for shot in st["body_projectiles"]:
        shot["arrives_at"] -= 30.0
    authsrv.projectile_tick(send, st, 1)
    words = [v for op, v in sent if op == FLOAT_T and v[0] in (16, 17)]
    check(sent and sent[0] == (0x00A7, [FOE, 1, 1]) and len(words) == 1
          and words[0][1:3] == [authsrv.PLAYER_AGENT_ID, FOE] and not melee_close(sent, FOE)
          and authsrv.player_pools(st) is not None and not st["body_projectiles"],
          "a flight later: 0x00A7 [it, handle 1, damage type 1] FIRST, the word on the player, "
          "and NO [1, it, 0] -- land_swing's melee close is filtered out of a shot",
          str([(hex(op), v) for op, v in sent]))
    sent.clear()
    melee = _body_world((60.0, 0.0), weapon_item="starter_hammer", swinging=True,
                        swing_lands_at=time.time() - 0.01, last_swing=time.time())
    authsrv.enemy_attack_tick(send, melee, 1)
    check(len(melee_close(sent, FOE)) == 1 and not [v for op, v in sent if op in (0x00A4, 0x00A7)],
          "the control: the same tick with a HAMMER in the hand closes with [1, it, 0] and "
          "launches nothing")

    # a PARTY CASTER with its staff, at the leader's target from its slot
    st = _body_world((300.0, 0.0))
    now = time.time()
    authsrv.leader_engaged(st, FOE, now, "swing")
    sent.clear()
    saved_pf = authsrv.PARTY_FIGHTS
    authsrv.PARTY_FIGHTS = True
    try:
        authsrv.ally_attack_tick(send, st, 1)
        opened = [v for op, v in sent if op == INT_T and v[0] == 4]
        st["agents"][HERO]["swing_lands_at"] = time.time() - 0.01
        sent.clear()
        authsrv.ally_attack_tick(send, st, 1)
        bolt = [v for op, v in sent if op == 0x00A4]
        check(opened == [[4, HERO, FOE, 0]] and len(bolt) == 1 and bolt[0][0] == HERO
              and list(bolt[0][1]) == [300.0, 0.0] and bolt[0][4:] == [5, 1, 0]
              and not [v for op, v in sent if op == FLOAT_T],
              "the party caster opens [4, body, foe, 0] from its slot and, at the windup, its "
              "STAFF releases projectile 5 (its 617), arrow 0 -- where it used to land a word "
              "with nothing in the air", str(bolt))
        hp = st["agents"][FOE]["health"]
        sent.clear()
        for shot in st["body_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        check(sent and sent[0] == (0x00A7, [HERO, 1, 8])
              and len([v for op, v in sent if op == FLOAT_T and v[1:3] == [FOE, HERO]]) == 1
              and not melee_close(sent, HERO) and st["agents"][FOE]["health"] < hp,
              "and lands it a flight later: 0x00A7 [body, 1, the staff's damage type 8], the "
              "word on the foe, no melee close, the foe's health down",
              str([(hex(op), v) for op, v in sent]))
    finally:
        authsrv.PARTY_FIGHTS = saved_pf

    # handles are per SHOOTER; a target dead in flight is closed and unhurt
    st = _body_world((600.0, 0.0), weapon_item="hostile_bolt")
    sent.clear()
    for who in (FOE, FOE, HERO):
        authsrv.launch_body_projectile(send, st, 1, who, st["agents"][who],
                                       HERO if who == FOE else FOE,
                                       authsrv.body_ranged(st["agents"][who]))
    check([(v[0], v[5]) for op, v in sent if op == 0x00A4] == [(FOE, 1), (FOE, 2), (HERO, 1)]
          and all(s["arrives_at"] in authsrv.combat_deadlines(st)
                  for s in st["body_projectiles"]),
          "handles count each SHOOTER's own outstanding shots, and every arrival is a "
          "combat deadline")
    st["agents"][HERO]["dead"] = True
    hp = st["agents"][HERO]["health"]
    sent.clear()
    for shot in st["body_projectiles"]:
        shot["arrives_at"] -= 30.0
    authsrv.projectile_tick(send, st, 1)
    check([op for op, _v in sent].count(0x00A7) == 3 and st["agents"][HERO]["health"] == hp,
          "every shot is CLOSED, and the two at a body that died in flight land nothing")

    authsrv.RANGED_DELIVERY = False
    try:
        off = _body_world((60.0, 0.0), weapon_item="hostile_bow", swinging=True,
                          swing_lands_at=time.time() - 0.01, last_swing=time.time())
        sent.clear()
        authsrv.enemy_attack_tick(send, off, 1)
        check(authsrv.body_ranged(off["agents"][FOE]) is None
              and authsrv.body_reach(off["agents"][FOE]) == authsrv.enemy_reach()
              and len(melee_close(sent, FOE)) == 1
              and not [v for op, v in sent if op in (0x00A4, 0x00A7)],
              "--no-projectiles: the archer swings from the melee disc and closes with "
              "[1, it, 0] -- the arm before today")
    finally:
        authsrv.RANGED_DELIVERY = True
    src = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check('"--enemy-weapon"' in src, "--enemy-weapon exists: the fixture hostile holds an item")


def section_skill_shots():
    print("\n7. WEAPONS-W2c: attack skills shoot")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.skill_timing, authsrv._is_attack_skill, authsrv.skill_cost,
             authsrv.skill_projectile, authsrv.skill_damage, authsrv.attack_skill_terms,
             authsrv.apply_condition, authsrv.weapon_satisfies)
    words = lambda batch: [v for op, v in batch if op == 0x00A3 and v[0] in (16, 17)]   # noqa: E731
    close = lambda batch, who, prop: [v for op, v in batch if op == 0x009F              # noqa: E731
                                      and v[:2] == [prop, who]]
    launches = lambda batch: [v for op, v in batch if op == 0x00A4]                     # noqa: E731

    # THE PURE READER, against a table the test controls: the real
    # skill_projectile on injected rows (a bare machine has no skills table).
    tables = agents.WORLD.tables
    had, kept = "skills" in tables, tables.get("skills")
    tables["skills"] = {"394": {"projectile": 680}, "404": {"projectile": 2077},
                        "7": {}, "8": {"projectile": 0}}
    try:
        got = [authsrv.skill_projectile(k) for k in (394, 404, 7, 8, 999)]
    finally:
        if had:
            tables["skills"] = kept
        else:
            del tables["skills"]
    check(got == [680, None, None, None, None] and authsrv.SKILL_NO_PROJECTILE == 2077,
          "skill_projectile reads the row's +0x88 (Power Shot's 680) and answers None for "
          "2077 -- the table's own 'none' -- for 0, for a row without the column and for no "
          "row at all", str(got))
    authsrv.skill_projectile = lambda sid: 680 if sid == 394 else None   # the table's answer, pinned by test_skilltable
    check(authsrv.skill_shot_how({"projectile": 143, "arrow": 1, "damage_type": 1}, 394)
          == {"projectile": 680, "arrow": 1, "damage_type": 1}
          and authsrv.skill_shot_how({"projectile": 143, "arrow": 1, "damage_type": 1}, 404)
          == {"projectile": 143, "arrow": 1, "damage_type": 1},
          "skill_shot_how swaps in the SKILL's projectile and nothing else -- the arrow "
          "flag and the kind stay the weapon's (retail: 680 with flag 1 / kind 1 from a "
          "plain bow, 12 of 12); a skill with no projectile of its own shoots the arrow")

    # the stubs test_castcycle's attack sections use, so the press and the tick run bare
    authsrv.skill_timing = lambda sid: (0.0, 0.0, 3.0)
    authsrv._is_attack_skill = lambda sid: True
    authsrv.skill_cost = lambda sid: (0, 0)
    authsrv.weapon_satisfies = lambda sid: True    # the gate (DAGGERS-B4) is test_daggers' business
    authsrv.skill_damage = lambda sid, rank: (10.0, "additive")
    COND = ("a condition", 5.0)
    authsrv.attack_skill_terms = lambda state, sid, rank, tid, bonus, conn, who: (bonus, COND, False)
    applied = []
    authsrv.apply_condition = lambda send, state, tid, cond, dur, rank, conn, sid=None: \
        applied.append((tid, cond, dur, sid))

    def press_and_e5(distance, skill=394, armour=True):
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        authsrv.PLAYER_SWING_DAMAGE = (5, 5)       # after the loader, which sets the bow's
        st, sent = _world(distance), []
        if not armour:
            del st["agents"][FOE]["armor_rating"]      # the raw-range branch: 5 + bonus, no roll
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.handle_skill_press([0, skill, 0, FOE], send, st, 1,
                                   authsrv.GAME_CMSG_USE_SKILL)
        pressed = list(sent)
        sent.clear()
        for cast in st["pending_casts"]:
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        authsrv.cast_tick(send, st, 1)
        return st, send, sent, pressed

    try:
        authsrv.PLAYER_SWING_DAMAGE = (5, 5)
        st, send, at_e5, pressed = press_and_e5(800.0, armour=False)
        ops = [op for op, _v in at_e5]
        launch = launches(at_e5)
        check([v for op, v in pressed if op == 0x00A0 and v[0] == agents.GV_ATTACK_SKILL_ACTIVATED]
              == [[agents.GV_ATTACK_SKILL_ACTIVATED, PLAYER, FOE, 394]]
              and not launches(pressed),
              "the press: the attack skill announces itself [50, me, foe, 394] and nothing "
              "leaves yet", str([(hex(op), v) for op, v in pressed]))
        check(ops[:2] == [0x00E5, 0x00A4] and 0x00E3 in ops and len(launch) == 1
              and launch[0][0] == PLAYER and list(launch[0][1]) == [800.0, 0.0]
              and abs(_f(launch[0][3]) - 0.5) < 1e-6 and launch[0][4:] == [680, 1, 1],
              "at the E5: 0x00E5, then ONE 0x00A4 [me, the target's position, 0, 0.5 s at "
              "1600 u/s, the SKILL's 680, handle 1, the BOW's arrow flag 1], then 0x00E3 -- "
              "retail's one batch, 22 of 22", str([(hex(op), v) for op, v in at_e5]))
        check(not close(at_e5, PLAYER, agents.GV_ATTACK_SKILL_FINISHED)
              and not words(at_e5) and st["agents"][FOE]["health"] == 9000.0
              and not applied,
              "and NO 46, no word, no damage and no condition at the E5 -- retail's ranged "
              "attack skill carries no close (0 of 22) and lands nothing there")
        shot = st["player_projectiles"][0]
        check(shot["strike"]["skill_id"] == 394 and shot["strike"]["bonus"] == 10.0
              and shot["strike"]["inflicted"] == COND
              and shot["arrives_at"] in authsrv.combat_deadlines(st),
              "the shot carries the strike it will land -- the skill, its + Damage, its "
              "condition -- and its arrival is a combat DEADLINE")
        e5 = [v for op, v in at_e5 if op == 0x00E5]
        check(e5 == [[PLAYER, 394, 0, 3]]
              and [v for op, v in at_e5 if op == 0x00E3] == [[PLAYER, 394, 0]],
              "the recharge and the E3 are the E5's (aftercast 0), as before")
        at_e5.clear()
        shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        at_arrival = list(at_e5)
        ops = [op for op, _v in at_arrival]
        check(ops[0] == 0x00A7 and at_arrival[0][1] == [PLAYER, 1, 1]
              and len(words(at_arrival)) == 1 and words(at_arrival)[0][1:3] == [FOE, PLAYER]
              and st["agents"][FOE]["health"] == 9000.0 - 15.0,
              "a flight later: 0x00A7 [me, handle 1, kind 1] FIRST, then the strike's ONE "
              "word -- the weapon's 5 plus the skill's 10, one number as on the E5 path",
              str([(hex(op), v) for op, v in at_arrival]))
        check(not close(at_arrival, PLAYER, agents.GV_MELEE_ATTACK_FINISHED)
              and not close(at_arrival, PLAYER, agents.GV_ATTACK_SKILL_FINISHED)
              and applied == [(FOE, COND[0], COND[1], 394)] and not st["player_projectiles"],
              "no property 1 and no 46 at the arrival either; the skill's condition lands "
              "THERE, on the live target, and the handle is spent", str(applied))

        # a skill with no projectile of its own shoots the bow's arrow
        applied.clear()
        st, send, at_e5, _p = press_and_e5(400.0, skill=404)
        check(launches(at_e5) and launches(at_e5)[0][4:] == [143, 1, 1]
              and abs(_f(launches(at_e5)[0][3]) - 0.25) < 1e-6,
              "Poison Arrow (no +0x88 of its own) releases the BOW's 143 -- retail 10 of 10")

        # a target dead in flight: closed, nothing lands, no condition
        applied.clear()
        st, send, at_e5, _p = press_and_e5(800.0)
        st["agents"][FOE]["dead"] = True
        at_e5.clear()
        for shot in st["player_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        check([op for op, _v in at_e5] == [0x00A7] and not applied,
              "an arrow whose target died in flight is CLOSED, lands nothing and inflicts "
              "nothing")

        # a MELEE weapon's attack skill is untouched: the strike at the E5 with its 46
        applied.clear()
        authsrv.apply_party_character({"player_weapon": "starter_sword"})
        authsrv.PLAYER_SWING_DAMAGE = (5, 5)
        st, sent = _world(100.0), []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.handle_skill_press([0, 394, 0, FOE], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
        sent.clear()
        for cast in st["pending_casts"]:
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        authsrv.cast_tick(send, st, 1)
        check(len(close(sent, PLAYER, agents.GV_ATTACK_SKILL_FINISHED)) == 1
              and len(words(sent)) == 1 and not launches(sent) and len(applied) == 1
              and not st.get("player_projectiles"),
              "the KNOWN-GOOD arm: the same press with a SWORD strikes at the E5 -- 46, the "
              "word, the condition -- and launches nothing")

        # a BODY's attack skill with a bow in its hands: through land_skill
        applied.clear()
        st = _body_world((600.0, 0.0), weapon_item="hostile_bow",
                         skills=[[394, 0.0, 3.0]], skill_ready=[0.0], casting=0,
                         cast_target=PLAYER, last_swing=time.time())
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        launch = launches(sent)
        check(len(launch) == 1 and launch[0][0] == FOE and list(launch[0][1]) == [0.0, 0.0]
              and abs(_f(launch[0][3]) - 0.5) < 1e-6 and launch[0][4:] == [680, 1, 1]
              and not close(sent, FOE, agents.GV_ATTACK_SKILL_FINISHED)
              and not [v for op, v in sent if op == FLOAT_T] and not applied
              and st["body_projectiles"][0]["strike"]["skill_id"] == 394,
              "a hostile ARCHER's Power Shot at its windup: ONE 0x00A4 [it, the player's "
              "position, 0, 0.5 s at 1200 u/s, 680, handle 1, arrow 1], no 46, no word, no "
              "condition -- the strike rides the shot", str([(hex(op), v) for op, v in sent]))
        health = st["player_health"]
        sent.clear()
        for shot in st["body_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        hits = [v for op, v in sent if op == FLOAT_T and v[0] in (16, 17)]
        check(sent and sent[0] == (0x00A7, [FOE, 1, 1]) and len(hits) == 1
              and hits[0][1:3] == [PLAYER, FOE] and st["player_health"] < health
              and not close(sent, FOE, agents.GV_MELEE_ATTACK_FINISHED)
              and not close(sent, FOE, agents.GV_ATTACK_SKILL_FINISHED)
              and applied == [(PLAYER, COND[0], COND[1], 394)] and not st["body_projectiles"],
              "a flight later: 0x00A7 [it, 1, kind 1] FIRST, the word on the player, NO [1] "
              "and NO [46] (both closes filtered out of a shot), the condition landing there",
              str([(hex(op), v) for op, v in sent]))
        applied.clear()
        melee = _body_world((60.0, 0.0), weapon_item="starter_hammer",
                            skills=[[394, 0.0, 3.0]], skill_ready=[0.0], casting=0,
                            cast_target=PLAYER, last_swing=time.time())
        sent.clear()
        authsrv.land_skill(send, melee, FOE, melee["agents"][FOE], 1)
        check(len(close(sent, FOE, agents.GV_ATTACK_SKILL_FINISHED)) == 1
              and not launches(sent) and len(applied) == 1,
              "the control: the same skill with a HAMMER closes with [46, it, 0] at the "
              "windup and launches nothing")

        authsrv.RANGED_DELIVERY = False
        try:
            applied.clear()
            st, send, at_e5, _p = press_and_e5(100.0)
            check(not launches(at_e5) and len(close(at_e5, PLAYER, agents.GV_ATTACK_SKILL_FINISHED)) == 1
                  and len(words(at_e5)) == 1 and len(applied) == 1,
                  "--no-projectiles: the bow's Power Shot strikes at the E5 with its 46 -- "
                  "the arm before today")
        finally:
            authsrv.RANGED_DELIVERY = True
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.skill_timing, authsrv._is_attack_skill, authsrv.skill_cost,
         authsrv.skill_projectile, authsrv.skill_damage, authsrv.attack_skill_terms,
         authsrv.apply_condition, authsrv.weapon_satisfies) = saved


def section_approach():
    print("\n8. WEAPONS-W2b: the approach ends at the weapon's range")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.APPROACH_STOPS_AT_RANGE)
    follows = lambda batch: [v for op, v in batch if op == 0x002A]                  # noqa: E731
    try:
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        bow = authsrv.approach_stop({})
        authsrv.apply_party_character({"player_weapon": "starter_sword"})
        sword = authsrv.approach_stop({})
        check(bow == 1498.0 and sword == authsrv.follow_stop_radius({}) == 80.0,
              "approach_stop: the bow's RANGE (1498, its attack_reach), a sword's the melee "
              "disc (80) -- never less than the disc", f"bow {bow}, sword {sword}")

        # a press from 2000 u with the bow: the follow leg ends at range
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        st, sent = _world(2000.0), []
        st["approach"] = None
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        now = time.time()
        authsrv._approach_send(send, st, 1, FOE, st["agents"][FOE], now)
        fol = follows(sent)
        ap, leg = st.get("approach"), st.get("click_leg")
        check(len(fol) == 1 and fol[0][0] == PLAYER and list(fol[0][1]) == [2000.0, 0.0]
              and fol[0][4] == FOE,
              "the wire is unchanged: ONE 0x002A [me, the TARGET's own position, plane, plane, "
              "target] -- retail's follow, bit for bit as for melee", str(fol))
        check(ap is not None and leg is not None
              and abs(leg["dest"][0] - 502.0) < 1e-6 and abs(leg["dest"][1]) < 1e-6
              and abs(st["dest"][0] - 502.0) < 1e-6
              and abs((leg["eta"] - now) - 502.0 / leg["speed"]) < 1e-6,
              "but the LEG ends 1498 u short of the target -- at x = 502, the integrator's "
              "dest and the follow's eta with it -- where it ended 80 u short before today",
              f"leg dest {leg['dest'] if leg else None}, state dest {st.get('dest')}")
        # arrival: the copy walked to the leg's end; approach_tick calls it arrived
        st["pos"] = (502.0, 0.0)
        st["last_report"] = (502.0, 0.0, True, now)
        st["click_moving_at"] = None
        st["approach"]["eta"] = now - 1.0
        st["approach"]["t0"] = None
        check(authsrv.approach_tick(send, st, 1, FOE, st["agents"][FOE], time.time()) is False
              and st.get("approach") is None,
              "at the leg's end the follow is OVER and the reach gate may open the swing "
              "(1498 u out is not > attack_reach)")
        check(not (math.hypot(2000.0 - 502.0, 0.0) > authsrv.attack_reach()),
              "-- and it does: the gate's strict > lets a body AT range shoot")

        # the sword's press from 2000 u: the disc, as before
        authsrv.apply_party_character({"player_weapon": "starter_sword"})
        st, sent = _world(2000.0), []
        authsrv._approach_send(send, st, 1, FOE, st["agents"][FOE], time.time())
        leg = st.get("click_leg")
        check(leg is not None and abs(leg["dest"][0] - 1920.0) < 1e-6,
              "the KNOWN-GOOD arm: a sword's leg still ends at the 80 u disc (x = 1920)")

        # the revert arm: the bow's leg to the disc
        authsrv.APPROACH_STOPS_AT_RANGE = False
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        st, sent = _world(2000.0), []
        authsrv._approach_send(send, st, 1, FOE, st["agents"][FOE], time.time())
        leg = st.get("click_leg")
        check(authsrv.approach_stop({}) == 80.0 and leg is not None
              and abs(leg["dest"][0] - 1920.0) < 1e-6,
              "--legacy-ranged-approach: the bow's leg walks to the disc -- the arm before today")
        src = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('"--legacy-ranged-approach"' in src, "--legacy-ranged-approach exists")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.APPROACH_STOPS_AT_RANGE) = saved


def section_weapon_energy():
    print("\n9. WEAPONS-W5: a staff's or a focus's energy")
    import morale  # noqa: PLC0415
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE, authsrv.WEAPON_ENERGY)
    try:
        base = agents.PLAYER_ENERGY
        authsrv.apply_party_character({"player_weapon": "starter_wand",
                                       "player_offhand": "starter_focus"})
        focus = authsrv.weapon_energy_bonus()
        st = {}
        authsrv.player_pools(st)
        with_focus = authsrv.player_max_energy(st)
        pool = authsrv.player_energy(st)
        authsrv.apply_party_character({"player_weapon": "caster_staff"})
        staff = authsrv.weapon_energy_bonus()
        authsrv.apply_party_character({"player_weapon": "starter_sword",
                                       "player_offhand": "starter_shield"})
        sword = authsrv.weapon_energy_bonus()
        st_s = {}
        authsrv.player_pools(st_s)
        plain = authsrv.player_max_energy(st_s)
        check(focus == 5 and staff == 10 and sword == 0,
              "the held set's 556: the retail focus +5 in the off hand, the henchman's staff "
              "+10 in the lead, a sword and shield nothing (the words OBSERVED on the items; "
              "the rule WIKI's)", f"focus {focus}, staff {staff}, sword {sword}")
        check(with_focus == base + 5 and plain == base and base == agents.PLAYER_ENERGY,
              "player_max_energy is the row's typed pool plus the held set's word at neutral "
              "morale, and the row's pool alone without one -- the row itself untouched",
              f"{with_focus} vs {plain}, row {base}")
        check(pool.maximum == float(base + 5)
              and abs(pool.rate - authsrv.pools.wire_regen_rate(authsrv.PLAYER_ENERGY_PIPS,
                                                                  base + 5)) < 1e-9,
              "the pool the player is seeded with carries it, and the f32 regen rate "
              "(property 43) is the pips over the LARGER pool -- what the client integrates")
        authsrv.apply_party_character({"player_weapon": "starter_wand",
                                       "player_offhand": "starter_focus"})
        check(authsrv.player_max_energy({"morale": 85})
              == int(morale.effective_max(base + 5, morale.BASE_ENERGY, 85))
              and authsrv.player_max_energy({"morale": 85}) < with_focus,
              "at -15 % morale the focus rides like a rune: effective_max scales the innate "
              "20 and leaves the +5 whole")
        authsrv.apply_party_character({"player_weapon": "caster_staff",
                                       "player_offhand": "starter_focus"})
        check(authsrv.weapon_energy_bonus() == 15 and agents.PLAYER_OFFHAND is not None,
              "a row naming BOTH a staff and a focus keeps both (the loader's own rule: a "
              "row's off hand wins over the two-handed emptying) and the words sum -- "
              "stated, not endorsed: retail lets no one hold both")
        authsrv.WEAPON_ENERGY = False
        try:
            authsrv.apply_party_character({"player_weapon": "starter_wand",
                                           "player_offhand": "starter_focus"})
            check(authsrv.weapon_energy_bonus() == 0 and authsrv.player_max_energy({}) == base,
                  "--no-weapon-energy: the row's pool alone -- the arm before today")
        finally:
            authsrv.WEAPON_ENERGY = True
        src = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('"--no-weapon-energy"' in src, "--no-weapon-energy exists")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.WEAPON_ENERGY) = saved


def _foe(armour, level=None):
    row = {"name": "t", "dead": False, "died_at": 0.0, "health": 9000.0,
           "max_health": 9000.0, "last_hit": 0.0, "pos": (100.0, 0.0), "plane": 0,
           "armor_rating": float(armour), "allegiance": agents.ALLEGIANCE_HOSTILE,
           "effects": 0, "attacks_back": False, "skills": (), "skill_ready": []}
    if level is not None:
        row["npc"] = {"level": level, "profession": 2}
    return row


def _dealt(level, armour, weapon="starter_wand", rng=(5, 5)):
    """One armed wand hit through the real hit_enemy at `level` against `armour`."""
    authsrv.apply_party_character({"player_weapon": weapon})
    authsrv.PLAYER_SWING_DAMAGE = rng
    st = {"agents": {FOE: _foe(armour)}, "pos": (0.0, 0.0), "level": level}
    hp = st["agents"][FOE]["health"]
    authsrv.hit_enemy(lambda *a, **k: None, st, FOE, 1, armed=True)
    return hp - st["agents"][FOE]["health"]


def section_caster_level():
    print("\n10. WEAPONS-W4c: a wand or staff scales on the character's level")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.CASTER_LEVEL, authsrv.caster_critical_rate)
    try:
        check(authsrv.caster_weapon(agents.item_template("starter_wand"))
              and authsrv.caster_weapon(agents.item_template("caster_staff"))
              and not authsrv.caster_weapon(agents.item_template("starter_sword"))
              and not authsrv.caster_weapon(agents.item_template("starter_bow"))
              and not authsrv.caster_weapon(agents.item_template("starter_focus"))
              and not authsrv.caster_weapon(None),
              "a wand and a staff are caster weapons (rows with no mastery); a sword, a bow, "
              "a focus and empty hands are not")
        c11, c2020 = authsrv.caster_critical_rate(1, 1), authsrv.caster_critical_rate(20, 20)
        check(abs(c11 - 0.05 * 2 ** ((8 - 15 - 100) / 40)) < 1e-9 and c11 < 0.01
              and abs(c2020 - 0.05 * 2 ** (-6)) < 1e-9 and c2020 < 0.001
              and authsrv.caster_critical_rate(None, None) == c2020,
              "the caster critical is GWW's no-skill chance: 0.8 % at level 1 vs 1, 0.08 % at "
              "20 vs 20 (the plan's 'very low'), a missing level read as 20",
              f"{c11:.4f}, {c2020:.5f}")
        check(authsrv.caster_strike_level(20) == 60.0 and authsrv.caster_strike_level(1) == 3.0
              and combatmath.swing_damage(0, 60.0, (5, 5), roll=5.0, strike_level=60.0,
                                          ARMOUR_DIVISOR=40.0, CRITICAL_ARMOUR_REDUCTION=20.0)
              == 5.0
              and combatmath.swing_damage(0, 60.0, (5, 5), roll=5.0, strike_level=30.0,
                                          ARMOUR_DIVISOR=40.0, CRITICAL_ARMOUR_REDUCTION=20.0)
              == 3.0
              and combatmath.swing_damage(12, 60.0, (5, 5), roll=5.0,
                                          ARMOUR_DIVISOR=40.0, CRITICAL_ARMOUR_REDUCTION=20.0)
              == 5.0,
              "strike level 3 x level handed straight to swing_damage: 60 at level 20 is the "
              "listed damage against 60 armour, 30 at level 10 is 3 of a 5; without it the "
              "attribute's own strike level as before")
        authsrv.caster_critical_rate = lambda a, d: 0.0        # the roll, not the rule
        check(_dealt(20, 60.0) == 5.0 and _dealt(10, 60.0) == 3.0 and _dealt(20, 100.0) == 2.0,
              "through the real hit_enemy with a wand: 5 at level 20 vs AL 60 (the listed "
              "damage, WIKI's 'a level 20 player ... will deal the listed base damage'), 3 at "
              "level 10, 2 against AL 100 -- the armour term a wand never had")
        check(_dealt(1, 3.0) == 5.0 and _dealt(1, 6.0) in (4.0, 5.0)
              and _dealt(1, 3.0, rng=(3, 3)) == 3.0,
              "the owner's plain wand hits (20260807T143055, level 1, a 3-5 wand): 5 on a level-1 "
              "creature (AL 3) and 3-5 on a level-2 one (AL 6) -- reproduced; CONSISTENT, not "
              "discriminating (the rank-0 rule rounds to the same)")
        check(11.0 <= _dealt(20, 60.0, weapon="caster_staff", rng=(11, 22)) <= 22.0,
              "the henchman's 11-22 staff in the player's hands at level 20 vs AL 60 lands in "
              "its listed range (the henchmen's own 10-26 on 20260817T231139)")
        # a body: the party Monk's staff swings on ITS level
        monk = {"name": "monk", "weapon_item": "caster_staff", "damage": [20, 20],
                "npc": {"profession": 3, "level": 3}, "attributes": [[13, 3]],
                "weapon_attribute": 13}
        with_level = authsrv.body_swing_damage(monk, 60.0)
        authsrv.CASTER_LEVEL = False
        legacy = authsrv.body_swing_damage(monk, 60.0)
        authsrv.CASTER_LEVEL = True
        check(with_level == 8.0 and legacy == 9.0,
              "a level-3 body holding the caster staff swings at strike level 9 (3 x 3): a "
              "20-point roll lands 8 against AL 60, where its rank-3 mastery gave 9 -- the "
              "same rule, the body's own level", f"{with_level} vs {legacy}")
        hammer = dict(monk, weapon_item="starter_hammer")
        check(authsrv.body_swing_damage(hammer, 60.0) == 9.0,
              "and a body with a HAMMER keeps its mastery's strike level")
        authsrv.CASTER_LEVEL = False
        try:
            check(_dealt(10, 60.0) == 5.0 and _dealt(20, 100.0) == 5.0,
                  "--no-caster-level: the raw range at any level and any armour -- the branch "
                  "before today")
        finally:
            authsrv.CASTER_LEVEL = True
        src = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('"--no-caster-level"' in src, "--no-caster-level exists")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.CASTER_LEVEL, authsrv.caster_critical_rate) = saved


def section_dual_shot():
    print("\n11. WEAPONS-W2d: Dual Shot's two arrows")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.skill_timing, authsrv._is_attack_skill, authsrv.skill_cost,
             authsrv.skill_projectile, authsrv.skill_damage, authsrv.attack_skill_terms,
             authsrv.apply_condition, authsrv.weapon_satisfies)
    words = lambda batch: [v for op, v in batch if op == 0x00A3 and v[0] in (16, 17)]   # noqa: E731
    launches = lambda batch: [v for op, v in batch if op == 0x00A4]                     # noqa: E731
    arrivals = lambda batch: [v for op, v in batch if op == 0x00A7]                     # noqa: E731
    authsrv.skill_timing = lambda sid: (0.0, 0.0, 10.0)
    authsrv._is_attack_skill = lambda sid: True
    authsrv.skill_cost = lambda sid: (0, 0)
    authsrv.weapon_satisfies = lambda sid: True
    authsrv.skill_projectile = lambda sid: 680 if sid in (394, 396) else None
    authsrv.skill_damage = lambda sid, rank: (10.0, "additive") if sid == 394 else None
    COND = ("a condition", 5.0)
    authsrv.attack_skill_terms = lambda state, sid, rank, tid, bonus, conn, who: (bonus, COND, False)
    applied = []
    authsrv.apply_condition = lambda send, state, tid, cond, dur, rank, conn, sid=None: \
        applied.append((tid, cond, dur, sid))

    def press_and_e5(distance, skill, rng=(8, 8)):
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        authsrv.PLAYER_SWING_DAMAGE = rng
        st, sent = _world(distance), []
        del st["agents"][FOE]["armor_rating"]          # the raw-range branch: the roll exactly
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.handle_skill_press([0, skill, 0, FOE], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
        sent.clear()
        for cast in st["pending_casts"]:
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        authsrv.cast_tick(send, st, 1)
        return st, send, sent

    try:
        check(authsrv.skill_arrows(396) == (2, 0.75) and authsrv.skill_arrows(394) == (1, 1.0)
              and authsrv.skill_arrows(999999) == (1, 1.0),
              "skill_arrows: Dual Shot's row says two arrows at 75 % (WIKI; the shape OBSERVED "
              "on 8 pairs); every other skill one arrow at 100 %")
        st, send, at_e5 = press_and_e5(800.0, 396)
        la = launches(at_e5)
        check(len(la) == 2 and [v[5] for v in la] == [1, 2] and la[0][4] == la[1][4] == 680
              and la[0][1] == la[1][1] and la[0][3] == la[1][3]
              and [op for op, _v in at_e5][:3] == [0x00E5, 0x00A4, 0x00A4]
              and len(st["player_projectiles"]) == 2
              and [s["strike"]["first"] for s in st["player_projectiles"]] == [True, False]
              and all(s["strike"]["mult"] == 0.75 for s in st["player_projectiles"]),
              "at Dual Shot's E5: TWO 0x00A4 in one instant, handles 1 and 2, the same 680 at "
              "the same aim and flight -- the tape's shape -- each shot carrying the strike, "
              "the first flagged as the one the condition rides", str(la))
        hp = st["agents"][FOE]["health"]
        at_e5.clear()
        for shot in st["player_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        ops = [op for op, _v in at_e5]
        check(len(arrivals(at_e5)) == 2 and [v[1] for v in arrivals(at_e5)] == [1, 2]
              and len(words(at_e5)) == 2 and hp - st["agents"][FOE]["health"] == 12.0
              and ops[0] == 0x00A7 and not st["player_projectiles"],
              "a flight later: both handles close and TWO words land, each 6 of an 8-point "
              "roll (75 %), the foe down 12 -- each arrow its own roll and word",
              str([(hex(op), v) for op, v in at_e5]))
        check(applied == [(FOE, COND[0], COND[1], 396)],
              "the skill's condition lands ONCE, with the first arrow, not per arrow",
              str(applied))
        applied.clear()
        st, send, at_e5 = press_and_e5(800.0, 394)
        hp = st["agents"][FOE]["health"]
        at_e5.clear()
        for shot in st["player_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        check(len(launches(at_e5)) == 0 and len(words(at_e5)) == 1
              and hp - st["agents"][FOE]["health"] == 18.0,
              "the KNOWN-GOOD arm: Power Shot is ONE arrow at 100 % plus its +10 -- 18 of an "
              "8-point roll, and the bonus is never scaled")
        # a BODY's Dual Shot: two launches, two arrivals, two words on the player, one condition
        applied.clear()
        # The body's damage is PINNED here, and that is a fix rather than a
        # convenience: with hostile_bow's own 1-3 roll, Dual Shot's 0.75 and the
        # level-5 archer's strike 15 against armour 45, only a roll of 3 survives
        # `_whole_points` -- so both arrows landed ZERO on (2/3)^2 = 44 % of runs
        # and this check failed on about half of them (measured 3 of 6 on
        # f44e7343's own tree, 2026-09-18). The roll is not what the check is
        # about; the two arrivals, the two words and the single condition are.
        st = _body_world((600.0, 0.0), weapon_item="hostile_bow", damage=[20, 20],
                         skills=[[396, 0.0, 10.0]], skill_ready=[0.0], casting=0,
                         cast_target=PLAYER, last_swing=time.time())
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        la = launches(sent)
        check(len(la) == 2 and [v[5] for v in la] == [1, 2] and la[0][4] == la[1][4] == 680
              and len(st["body_projectiles"]) == 2,
              "a hostile archer's Dual Shot at its windup: two 0x00A4, handles 1 and 2, 680")
        health = st["player_health"]
        sent.clear()
        for shot in st["body_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        hits = [v for op, v in sent if op == FLOAT_T and v[0] in (16, 17)]
        check(len(arrivals(sent)) == 2 and len(hits) == 2 and st["player_health"] < health
              and applied == [(PLAYER, COND[0], COND[1], 396)],
              "and a flight later both arrows arrive and word the player, the condition once "
              "-- at the FULL weapon number each (land_swing carries no factor; said)")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.skill_timing, authsrv._is_attack_skill, authsrv.skill_cost,
         authsrv.skill_projectile, authsrv.skill_damage, authsrv.attack_skill_terms,
         authsrv.apply_condition, authsrv.weapon_satisfies) = saved


def section_preparation_wire():
    print("\n12. WEAPONS-W2e: a preparation on the wire")
    KINDLE = 433
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.PREPARATION_WIRE, authsrv.skill_projectile, authsrv.skill_impact_visual,
             authsrv.swing_preparation_bonus)
    authsrv.skill_projectile = lambda sid: {KINDLE: 343, 394: 680}.get(sid)   # the vault rows' +0x88
    authsrv.skill_impact_visual = lambda sid: 344 if sid == KINDLE else None   # and its +0x84
    words = lambda batch: [v for op, v in batch if op == 0x00A3 and v[0] in (16, 17)]   # noqa: E731
    impacts = lambda batch: [v for op, v in batch if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]   # noqa: E731

    def kindled(st):
        authsrv.effect_table(st).apply(PLAYER, KINDLE, 0, 24.0, time.time(), type_code=19)
        return st

    try:
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        check(agents.item_template("starter_bow").get("fires_arrows") is True
              and agents.item_template("hostile_bow").get("fires_arrows") is True
              and not agents.item_template("starter_wand").get("fires_arrows"),
              "the bows carry `fires_arrows` (the preparation gate the plan left off the "
              "starter bow); a wand does not")
        row = agents.WORLD.get("skill_effect", str(KINDLE))
        check(row["scale_means"] == "Fire damage" and int(row["damage_type"]) == 5,
              "Kindle Arrows' row: a fire-damage preparation whose arrows arrive as kind 5")
        st = kindled({"agents": {}})
        check(authsrv.open_preparation(st, PLAYER)[:2] == (KINDLE, 0)
              and authsrv.open_preparation({"agents": {}}, PLAYER) == (None, None, None),
              "open_preparation finds the episode on the player and nothing without one")
        plain, under = authsrv.player_ranged({"agents": {}}), authsrv.player_ranged(st)
        check((plain["projectile"], plain["arrow"], plain["damage_type"]) == (143, 1, 1)
              and (under["projectile"], under["arrow"], under["damage_type"]) == (343, 0, 5)
              and under["speed"] == plain["speed"] and under["range"] == plain["range"]
              and authsrv.player_ranged() == plain,
              "under Kindle Arrows the bow's shot flies as the preparation's 343 with flag 0 "
              "and kind 5 -- the tape's launch and arrival -- speed and range the bow's; "
              "without a state, or without the episode, the plain 143 / 1 / 1")
        check(authsrv.skill_shot_how(under, 394)["projectile"] == 680
              and authsrv.skill_shot_how(under, 394)["arrow"] == 0
              and authsrv.skill_shot_how(under, 394)["damage_type"] == 5,
              "a skill's own projectile still wins under it, with the preparation's flag and "
              "kind (Power Shot's 680 / 0 / 5 on the tape)")

        # one plain shot under Kindle Arrows, through the real loop
        authsrv.swing_preparation_bonus = lambda state, w, a: (3.0, KINDLE)   # the rank-0 scale
        authsrv.PLAYER_SWING_DAMAGE = (8, 8)
        st, sent = kindled(_world(800.0)), []
        del st["agents"][FOE]["armor_rating"]                # the raw branch: 8 and 3 exactly
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.begin_attack(send, st, FOE, 1)
        authsrv.attack_tick(send, st, 1)
        st["player_swing"]["lands_at"] -= 30.0
        sent.clear()
        authsrv.attack_tick(send, st, 1)
        launch = [v for op, v in sent if op == 0x00A4]
        check(len(launch) == 1 and launch[0][4:] == [343, 1, 0],
              "at the windup the launch carries 343 with flag 0", str(launch))
        hp = st["agents"][FOE]["health"]
        sent.clear()
        for shot in st["player_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        ops = [op for op, _v in sent]
        w = words(sent)
        check(ops[0] == 0x00A7 and sent[0][1] == [PLAYER, 1, 5]
              and len(w) == 2 and w[0][0] == 16 and w[1][0] == 16
              and abs(_f(w[0][3]) + 8.0 / 9000.0) < 1e-7
              and abs(_f(w[1][3]) + 3.0 / 9000.0) < 1e-7
              and hp - st["agents"][FOE]["health"] == 11.0,
              "a flight later: 0x00A7 [me, 1, kind 5], then the arrow's word of 8 and a "
              "SECOND word of the preparation's 3 -- dealt separately (WIKI), the foe down 11",
              str([(hex(op), v) for op, v in sent]))
        imp = impacts(sent)
        seq = [(op, v[0] if op == 0x00A0 else None) for op, v in sent if op in (0x00A0, 0x00A3)]
        check(len(imp) == 2 and all(v[1:] == [FOE, PLAYER, 344] for v in imp)
              and [x for x in seq if x[0] == 0x00A3 or x[1] == agents.GV_EFFECT_ON_TARGET]
              == [(0x00A0, 20), (0x00A3, None), (0x00A0, 20), (0x00A3, None)],
              "the impact [20, foe, me, 344] rides BEFORE each word -- the tape's order")

        authsrv.PREPARATION_WIRE = False
        try:
            st, sent = kindled(_world(800.0)), []
            del st["agents"][FOE]["armor_rating"]
            send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
            authsrv.begin_attack(send, st, FOE, 1)
            authsrv.attack_tick(send, st, 1)
            st["player_swing"]["lands_at"] -= 30.0
            sent.clear()
            authsrv.attack_tick(send, st, 1)
            hp = st["agents"][FOE]["health"]
            for shot in st["player_projectiles"]:
                shot["arrives_at"] -= 30.0
            authsrv.projectile_tick(send, st, 1)
            check([v for op, v in sent if op == 0x00A4][0][4:] == [143, 1, 1]
                  and len(words(sent)) == 1 and not impacts(sent)
                  and hp - st["agents"][FOE]["health"] == 11.0,
                  "--no-preparation-wire: the plain 143, ONE word of 11 (the fold), no impact "
                  "-- the shape before today")
        finally:
            authsrv.PREPARATION_WIRE = True
        src = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('"--no-preparation-wire"' in src, "--no-preparation-wire exists")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.PREPARATION_WIRE, authsrv.skill_projectile, authsrv.skill_impact_visual,
         authsrv.swing_preparation_bonus) = saved


def section_body_parity():
    print("\n13. WEAPONS-W2f: a body's preparation and its arrow factor")
    KINDLE = 433
    saved = (authsrv.PREPARATION_WIRE, authsrv.skill_projectile, authsrv.skill_impact_visual,
             authsrv.swing_preparation_bonus, authsrv.ARMOUR_TERM)
    authsrv.skill_projectile = lambda sid: {KINDLE: 343, 396: 680}.get(sid)
    authsrv.skill_impact_visual = lambda sid: 344 if sid == KINDLE else None
    authsrv.swing_preparation_bonus = lambda state, w, a: (3.0, KINDLE) if state.get("effects") and state["effects"].on_agent(a) else (0.0, None)
    words = lambda batch: [v for op, v in batch if op == FLOAT_T and v[0] in (16, 17)]           # noqa: E731
    impacts = lambda batch: [v for op, v in batch if op == INT_T and v[0] == agents.GV_EFFECT_ON_TARGET]   # noqa: E731
    try:
        st = _body_world((600.0, 0.0), weapon_item="hostile_bow", swinging=True,
                         swing_lands_at=time.time() - 0.01, last_swing=time.time())
        plain = authsrv.body_ranged(st["agents"][FOE], st, FOE)
        authsrv.effect_table(st).apply(FOE, KINDLE, 0, 24.0, time.time(), type_code=19)
        under = authsrv.body_ranged(st["agents"][FOE], st, FOE)
        check((plain["projectile"], plain["arrow"], plain["damage_type"]) == (143, 1, 1)
              and (under["projectile"], under["arrow"], under["damage_type"]) == (343, 0, 5)
              and authsrv.body_ranged(st["agents"][FOE]) == plain,
              "a hostile archer under Kindle Arrows shoots 343 / 0 / 5 (retail's rangers on "
              "20260817T231139: 343 / 0 / 5 on every arrow under it), the plain 143 / 1 / 1 "
              "without the episode or without a state")
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.enemy_attack_tick(send, st, 1)
        launch = [v for op, v in sent if op == 0x00A4]
        check(len(launch) == 1 and launch[0][4:] == [343, 1, 0],
              "through the real tick its windup launches 343 with flag 0", str(launch))
        health = st["player_health"]
        sent.clear()
        for shot in st["body_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        w, imp = words(sent), impacts(sent)
        seq = [(op, v[0]) for op, v in sent if (op == INT_T and v[0] == agents.GV_EFFECT_ON_TARGET) or op == FLOAT_T]
        check(sent[0] == (0x00A7, [FOE, 1, 5]) and len(w) == 2 and w[1][1:3] == [PLAYER, FOE]
              and len(imp) == 2 and all(v[1:] == [PLAYER, FOE, 344] for v in imp)
              and [x[0] for x in seq] == [INT_T, FLOAT_T, INT_T, FLOAT_T]
              and health - st["player_health"] > 0,
              "a flight later: 0x00A7 kind 5, then impact 344, the arrow's word, impact 344 and "
              "the preparation's own word on the player -- W2e's shape from a body",
              str([(hex(op), v) for op, v in sent]))
        # the arrow factor: Dual Shot's two arrows at 75 % of the plain hit. A fixed
        # 40-point row and no armour term, so the only roll is the body's own
        # strike level against the baseline 60 -- the same on both fixtures.
        authsrv.ARMOUR_TERM = False
        base = _body_world((600.0, 0.0), weapon_item="hostile_bow", damage=[40, 40],
                           swinging=True, swing_lands_at=time.time() - 0.01,
                           last_swing=time.time())
        sent = []
        authsrv.enemy_attack_tick(send, base, 1)
        for shot in base["body_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, base, 1)
        plain_hit = 480.0 - base["player_health"]
        dual = _body_world((600.0, 0.0), weapon_item="hostile_bow", damage=[40, 40],
                           skills=[[396, 0.0, 10.0]], skill_ready=[0.0], casting=0,
                           cast_target=PLAYER, last_swing=time.time())
        sent = []
        authsrv.land_skill(send, dual, FOE, dual["agents"][FOE], 1)
        for shot in dual["body_projectiles"]:
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, dual, 1)
        per_arrow = (480.0 - dual["player_health"]) / 2.0
        check(plain_hit >= 10.0 and per_arrow == float(int(plain_hit * 0.75))
              and per_arrow < plain_hit and len(words(sent)) == 2,
              f"a body's Dual Shot lands each arrow at 75 % of the weapon's number through "
              f"land_swing's factor -- {per_arrow:.0f} a piece against a plain {plain_hit:.0f} "
              f"(the level-5 archer's own rank), two words -- W2d's body gap closed")
    finally:
        (authsrv.PREPARATION_WIRE, authsrv.skill_projectile, authsrv.skill_impact_visual,
         authsrv.swing_preparation_bonus, authsrv.ARMOUR_TERM) = saved


def section_splash():
    print("\n14. WEAPONS-W7: Ignite Arrows' adjacency splash")
    IGNITE, KINDLE = 431, 433
    NEAR, FAR = 11, 12
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.PREPARATION_SPLASH, authsrv.swing_preparation_bonus,
             authsrv.skill_impact_visual, authsrv.blind_miss)
    words = lambda batch: [v for op, v in batch                                    # noqa: E731
                           if op == FLOAT_T and v[0] in (16, 17, 55)]

    def world(extra_at=None):
        """The suit at 600 u, a NEAR foe beside it and a FAR one well outside 156."""
        st = _world(600.0)
        base = st["agents"][FOE]
        st["agents"][FOE]["pos"] = (600.0, 0.0)
        for aid, pos in ((NEAR, (600.0, 100.0)), (FAR, (600.0, 900.0))):
            row = dict(base)
            row["pos"] = pos
            row["health"] = row["max_health"] = 500.0
            st["agents"][aid] = row
        return st

    try:
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        authsrv.PLAYER_SWING_DAMAGE = (5, 5)
        # the row and the radius come from content and the CLIENT's own table
        row = agents.WORLD.get("skill_effect", str(IGNITE))
        radius = float(agents.WORLD.get("skills", str(IGNITE)).get("aoe_range", 0.0))
        check(row.get("adjacent_damage") == "scale" and row.get("damage_type") is None
              and radius == 156.0,
              "Ignite Arrows' row opts into the splash and carries NO damage_type -- the "
              "arrow keeps the weapon's kind (GWW: 'Unlike Kindle Arrows, the damage type "
              "of the arrows is not converted to fire') -- and the radius is the client's "
              f"own aoe_range, 156", f"row {dict(row)}, radius {radius}")
        check(agents.WORLD.get("skill_effect", str(KINDLE)).get("adjacent_damage") is None,
              "and Kindle Arrows does NOT opt in -- its page says target only, so the "
              "splash is one skill's, not every preparation's")

        # a landed hit under Ignite Arrows: the target's two words, then the NEAR foe
        authsrv.swing_preparation_bonus = lambda st_, w, a: (10.0, IGNITE)
        authsrv.skill_impact_visual = lambda sid: 734 if sid == IGNITE else None
        st, sent = world(), []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        near0, far0 = st["agents"][NEAR]["health"], st["agents"][FAR]["health"]
        authsrv.hit_enemy(send, st, FOE, 1)
        hit_ids = [v[1] for v in words(sent)]
        check(FOE in hit_ids and NEAR in hit_ids and FAR not in hit_ids
              and st["agents"][NEAR]["health"] < near0
              and st["agents"][FAR]["health"] == far0,
              "a landed arrow words the target AND the foe 100 u from it, and never the "
              "one 900 u away -- the client's own 156 u radius", str(hit_ids))
        splash = [v for op, v in sent if op == INT_T
                  and v[0] == agents.GV_EFFECT_ON_TARGET and v[1] == NEAR]
        check(len(splash) == 1 and splash[0][3] == 734,
              "the splash carries the preparation's own impact visual (734, the record's "
              "+0x84) before its word", str(splash))

        # ARMOUR-RESPECTING, and against the NEIGHBOUR's own armour, not the target's
        st = world()
        st["agents"][NEAR]["armor_rating"] = 0.0
        st["agents"][FOE]["armor_rating"] = 60.0
        soft0 = st["agents"][NEAR]["health"]
        sent = []
        authsrv.hit_enemy(send, st, FOE, 1)
        soft_taken = soft0 - st["agents"][NEAR]["health"]
        st2 = world()
        st2["agents"][NEAR]["armor_rating"] = 120.0
        hard0 = st2["agents"][NEAR]["health"]
        sent = []
        authsrv.hit_enemy(send, st2, FOE, 1)
        hard_taken = hard0 - st2["agents"][NEAR]["health"]
        check(soft_taken > hard_taken > 0.0,
              f"and it RESPECTS ARMOUR through the neighbour's OWN rating -- {soft_taken:.0f} "
              f"on a bare foe against {hard_taken:.0f} on a 120-armour one beside the same "
              f"target (GWW: 'armor-respecting fire damage') -- where Death Blossom's "
              f"adjacent damage ignores armour entirely")

        # THE MISS: the explosion happens anyway (GWW)
        authsrv.blind_miss = lambda st_, a: True
        st, sent = world(), []
        near0 = st["agents"][NEAR]["health"]
        res = authsrv.hit_enemy(send, st, FOE, 1)
        check(res == "missed" and st["agents"][NEAR]["health"] < near0
              and not [v for v in words(sent) if v[1] == FOE],
              "a BLIND MISS still splashes: the target takes nothing and the adjacent foe "
              "is worded anyway -- GWW: 'The explosion occurs regardless of whether the "
              "arrow actually hits its target (even if it misses, strays or is blocked)'")
        authsrv.blind_miss = saved[8]

        # the revert arm, and Kindle Arrows as the known-good control
        authsrv.PREPARATION_SPLASH = False
        st, sent = world(), []
        near0 = st["agents"][NEAR]["health"]
        authsrv.hit_enemy(send, st, FOE, 1)
        check(st["agents"][NEAR]["health"] == near0
              and [v[1] for v in words(sent)] .count(FOE) >= 1,
              "--no-preparation-splash: the target still takes both words and the adjacent "
              "foe takes nothing")
        authsrv.PREPARATION_SPLASH = True
        authsrv.swing_preparation_bonus = lambda st_, w, a: (10.0, KINDLE)
        st, sent = world(), []
        near0 = st["agents"][NEAR]["health"]
        authsrv.hit_enemy(send, st, FOE, 1)
        check(st["agents"][NEAR]["health"] == near0,
              "the KNOWN-GOOD arm: under Kindle Arrows, which does not opt in, the same "
              "shot splashes nobody")
        src = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('"--no-preparation-splash"' in src, "--no-preparation-splash exists")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.PREPARATION_SPLASH, authsrv.swing_preparation_bonus,
         authsrv.skill_impact_visual, authsrv.blind_miss) = saved



def section_spear():
    print("\n15. RUN-WEAPONS-1A: the spear shoots -- projectile 143, flag 1, its 587, the 1600 class")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE)
    try:
        authsrv.apply_party_character({"player_weapon": "starter_spear"})
        how = authsrv.player_ranged()
        check(how == {"projectile": 143, "arrow": 1, "damage_type": 1,
                      "speed": 1600.0, "range": 1004.0},
              "the spear's row shoots: the type's own 143 (its item carries no 617), the arrow "
              "flag, piercing, the 1600 class (1594 measured), WIKI's 1004 (the tape says "
              ">= 755) -- RUN-WEAPONS-1A, 54 of 54", str(how))
        st, at_windup, at_arrival = _one_shot("starter_spear", 755.0)
        launches = [v for op, v in at_windup if op == 0x00A4]
        flight = _f(launches[0][3]) if launches else None
        check(len(launches) == 1 and launches[0][4:] == [143, 1, 1] and flight is not None
              and abs(flight - 755.0 / 1600.0) < 0.002,
              "one 0x00A4 at the windup with [143, handle 1, arrow 1] and a flight of "
              "755 / 1600 s -- retail threw from 755 u with a 0.4735 s flight",
              f"{launches} flight {flight}")
        arrivals = [v for op, v in at_arrival if op == 0x00A7]
        words = [v for op, v in at_arrival if op == FLOAT_T and v[0] in (16, 17)]
        check(len(arrivals) == 1 and arrivals[0][1:] == [1, 1] and len(words) == 1
              and at_arrival and at_arrival[0][0] == 0x00A7,
              "the arrival closes handle 1 with kind 1 -- the spear's 587, WEAPONS-C9 on a "
              "spear -- FIRST, then the word", f"{arrivals} {words}")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE) = saved


def section_scythe():
    print("\n16. WEAPONS-W3: the scythe's extra targets, and its smaller critical")
    NEAR, FAR, EDGE_IN, EDGE_OUT, A, B = 21, 22, 23, 24, 26, 27
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.SCYTHE_EXTRA_TARGETS, authsrv.critical_rate,
             authsrv.player_weapon_rank, authsrv.blind_miss, authsrv.blocks)
    words = lambda batch: [v for op, v in batch                                    # noqa: E731
                           if op == FLOAT_T and v[0] in (16, 17)]
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731

    def world(distance, foes):
        """The target `distance` u from the player along +x; `foes` = {id: pos} beside it."""
        st = _world(distance)
        base = st["agents"][FOE]
        for aid, pos in foes.items():
            row = dict(base)
            row["pos"] = pos
            row["health"] = row["max_health"] = 500.0
            st["agents"][aid] = row
        return st

    def arm(weapon, rng=(10, 10)):
        authsrv.apply_party_character({"player_weapon": weapon})
        authsrv.PLAYER_SWING_DAMAGE = rng

    try:
        authsrv.blind_miss = lambda st_, a: False
        authsrv.blocks = lambda st_, t: False
        authsrv.critical_rate = lambda r: 0.0
        arm("starter_scythe")
        check(authsrv.scythe_extra_reach() == 80.0 and authsrv.SCYTHE_EXTRA_ATTACKER_REACH == 180.0
              and authsrv.SCYTHE_EXTRA_MAX == 2,
              "the two terms, said out loud: 80 u from the TARGET (r + r + the def pad, inside "
              "the tape's [78, 94) bracket) and 180 u from the attacker (hit at 182, missed at "
              "186); at most two extras (WIKI, untested on tape)")
        # geometry 1: 78 u from the target is hit, 94 u is not -- both inside 180 u of the player
        st = world(60.0, {NEAR: (138.0, 0.0), FAR: (60.0, 94.0)})
        del sent[:]
        authsrv.hit_enemy(send, st, FOE, 1)
        ids = [v[1] for v in words(sent)]
        check(ids == [NEAR, FOE] and st["agents"][FAR]["health"] == 500.0
              and st["agents"][NEAR]["health"] < 500.0,
              "a scythe swing words the foe 78 u from the target BEFORE the target and never "
              "the foe 94 u from it, though both stand inside 180 u of the player -- retail's "
              "29-of-29 order and its 17-swing null on the 94 u suit", str(ids))
        gains = [i for i, (op, v) in enumerate(sent) if op == 0x00CF]
        widx = [i for i, (op, v) in enumerate(sent) if op == FLOAT_T and v[0] in (16, 17)]
        check(len(gains) == 2 and len(widx) == 2 and gains[0] < widx[0] < gains[1] < widx[1],
              "each hit carries its own 0x00CF gain ahead of its word -- the extra's pair, then "
              "the target's (retail: 168 gains for 139 swings + 29 extras)",
              f"gains at {gains}, words at {widx}")
        # geometry 2: the attacker term at its edge -- 179 u hit, 186 u missed, both ~70 u from the target
        st = world(110.0, {EDGE_IN: (179.0, 0.0), EDGE_OUT: (186.0, 0.0)})
        del sent[:]
        authsrv.hit_enemy(send, st, FOE, 1)
        ids = [v[1] for v in words(sent)]
        check(ids == [EDGE_IN, FOE],
              "the attacker term at its edge: a foe 179 u from the player is hit and one 186 u "
              "away is not, both inside 80 u of the target", str(ids))
        # the cap: three candidates, two words, the two nearest the target
        st = world(60.0, {NEAR: (138.0, 0.0), A: (60.0, 70.0), B: (60.0, -75.0)})
        del sent[:]
        authsrv.hit_enemy(send, st, FOE, 1)
        ids = [v[1] for v in words(sent)]
        check(len(ids) == 3 and set(ids[:2]) == {A, B} and ids[2] == FOE
              and st["agents"][NEAR]["health"] == 500.0,
              "at most two extras, the two nearest the target (WIKI's cap; the tape never had "
              "three candidates, so this is the one unmeasured term)", str(ids))
        # a sword in the same geometry words the target alone
        arm("starter_sword")
        st = world(60.0, {NEAR: (138.0, 0.0)})
        del sent[:]
        authsrv.hit_enemy(send, st, FOE, 1)
        check([v[1] for v in words(sent)] == [FOE],
              "a sword in the same geometry words the target alone")
        # the revert flag
        arm("starter_scythe")
        authsrv.SCYTHE_EXTRA_TARGETS = False
        st = world(60.0, {NEAR: (138.0, 0.0)})
        del sent[:]
        authsrv.hit_enemy(send, st, FOE, 1)
        check([v[1] for v in words(sent)] == [FOE],
              "--no-scythe-extras: the target alone")
        authsrv.SCYTHE_EXTRA_TARGETS = True
        # the critical: the type's own armour term
        check(authsrv.weapon_critical_reduction(agents.item_template("starter_scythe")) == 5.0
              and authsrv.weapon_critical_reduction(agents.item_template("starter_sword")) == 20.0
              and authsrv.weapon_critical_reduction(None) == 20.0,
              "a scythe's critical takes 5 armour off the target, every other weapon's 20, "
              "and no weapon reads as 20")
        kw = dict(ARMOUR_DIVISOR=40.0)
        plain = combatmath.swing_damage(9, 60.0, (400, 400), roll=400.0,
                                        CRITICAL_ARMOUR_REDUCTION=20.0, **kw)
        c5 = combatmath.swing_damage(9, 60.0, (400, 400), critical=True,
                                     CRITICAL_ARMOUR_REDUCTION=5.0, **kw)
        c20 = combatmath.swing_damage(9, 60.0, (400, 400), critical=True,
                                      CRITICAL_ARMOUR_REDUCTION=20.0, **kw)
        check(abs(c5 / plain - 2 ** 0.125) < 0.01 and abs(c20 / plain - 2 ** 0.5) < 0.01,
              f"on the maximum roll the two terms are x{c5 / plain:.3f} and x{c20 / plain:.3f} "
              "-- 2^0.125 and 2^0.5; the tape's one scythe critical (6 points against a plain "
              "ceiling of 5) excludes root two")
        # and the primary hit reads it: force every swing critical on the same target and range
        authsrv.critical_rate = lambda r: 1.0
        authsrv.player_weapon_rank = lambda st_: 9

        def taken(weapon):
            arm(weapon, (40, 40))
            st = world(60.0, {})
            del sent[:]
            h0 = st["agents"][FOE]["health"]
            authsrv.hit_enemy(send, st, FOE, 1)
            return h0 - st["agents"][FOE]["health"], [v[0] for v in words(sent)]

        sc, sc_props = taken("starter_scythe")
        sw, sw_props = taken("starter_sword")
        check(sc_props == [17] and sw_props == [17] and 0 < sc < sw
              and abs(sc / sw - 2 ** (-15.0 / 40.0)) < 0.06,
              f"a forced critical: the scythe's {sc:.0f} against the sword's {sw:.0f} on the same "
              "target, rank and range, the ratio 2^(-15/40) -- the primary hit reads the type's term")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.SCYTHE_EXTRA_TARGETS, authsrv.critical_rate,
         authsrv.player_weapon_rank, authsrv.blind_miss, authsrv.blocks) = saved


def section_customisation():
    print("\n17. WEAPONS-W8: the customisation word (585) scales the range")
    W584 = 0xA488160F     # 584: 15-22, the isle sword's own range
    W585 = 0xA4987800     # 585 arg 120: the word on every one of the owner's PvP weapons (85 items)
    plain = combatmath.weapon_damage_range({"modifiers": [W584]})
    custom = combatmath.weapon_damage_range({"modifiers": [W584, W585]})
    check(plain == (15, 22) and custom == (18, 26),
          "a 15-22 range with (585, 120) reads 18-26 -- the isle study's own fit ('an integer "
          "roll over the customized range 18..26'); without the word, 15-22", f"{plain} {custom}")
    check(combatmath.weapon_damage_range({"modifiers": [W585, W584]}) == (18, 26)
          and combatmath.weapon_damage_range({"modifiers": [W584, 0xA4986400]}) == (15, 22)
          and combatmath.weapon_damage_range({"modifiers": [W585]}) is None,
          "word order does not matter, a 585 of 100 changes nothing, and the word alone is no range")
    check(all(combatmath.weapon_damage_range(agents.item_template(k)) is not None
              and 585 not in [(w >> 20) & 0x3FF for w in agents.item_template(k)["modifiers"]]
              for k in ("starter_axe", "starter_scythe", "starter_spear", "starter_sword")),
          "no repo item carries the word, so every party weapon's range is what it was")

def section_weapon_sets():
    print("\n18. WEAPONS-W9: the weapon-set switch -- retail's one batch, from the 1A tape")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             list(authsrv.WEAPON_SETS), dict(authsrv.WEAPON_SET_BACKPACK_SLOTS))
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    P = authsrv.PLAYER_AGENT_ID
    rate = lambda t: float(agents.ATTACK_SPEED[authsrv.WEAPON_TYPE_RATE[t]])       # noqa: E731
    try:
        # the 1A observer's four sets: axe; scythe; spear; spear + shield
        authsrv.WEAPON_SETS[:] = [{"lead": "starter_hammer", "off": None}, None, None, None]
        authsrv.apply_party_character({"player_weapon": "starter_axe"})
        changed = authsrv.configure_weapon_sets(["1=starter_scythe", "2=starter_spear",
                                                  "3=starter_spear+starter_shield"])
        check(authsrv.WEAPON_SETS[0] == {"lead": "starter_axe", "off": None}
              and authsrv.WEAPON_SETS[3] == {"lead": "starter_spear", "off": "starter_shield"}
              and len(changed) == 3,
              "three --weapon-set flags fill sets 1-3, and set 0 is the --player-weapon row's",
              str(authsrv.WEAPON_SETS))
        check([authsrv.weapon_set_items(k) for k in range(4)]
              == [(1, 0), (11, 0), (13, 0), (15, 16)],
              "the ids: set 0 is item 1; sets 1-3 take 11/12, 13/14, 15/16 (the tape's 212; "
              "209; 210; 208 + 207)")
        # the create: every inactive item declared and put in the backpack
        del sent[:]
        authsrv.declare_weapon_sets(send)
        ops = [op for op, _ in sent]
        moves = [v for op, v in sent if op == authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION]
        check(ops == [0x0161, 0x013E] * 4
              and moves == [[1, 11, 2, 0], [1, 13, 2, 1], [1, 15, 2, 2], [1, 16, 2, 3]],
              "the create declares the four inactive items and moves each into the backpack "
              "(bag 2) at slots 0..3 in order -- retail's 206..211 at 0..6, creation order",
              str(moves))
        # the switches, as the tape's four batches
        st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 480.0}

        def switch(k):
            del sent[:]
            authsrv.select_weapon_set(send, st, k, 1)
            return list(sent)

        # the energy words: our scythe and spear rows carry a 556 (+5); retail's
        # 1A weapons carried none, so the re-declaration is INFERRED from the
        # morale path (property 41 then the rescaled 43, test_pools 2b)
        def energy(maximum):
            rate = authsrv._f32(authsrv.morale.regen_fraction(
                agents.PLAYER_FLOAT_43, agents.PLAYER_ENERGY, maximum))
            return [(0x009F, [41, P, maximum]), (0x00A2, [43, P, rate])]

        E25, E30 = agents.PLAYER_ENERGY, agents.PLAYER_ENERGY + 5
        b1 = switch(1)
        check(b1 == [(0x0148, [1, 1]), (0x0152, [1, 1, 11]), (0x006F, [P, 0, 11])] + energy(E30),
              "0 -> 1 (axe -> scythe): 0x0148, the lead swap 0x0152 [1, old, new], one 0x006F "
              "for hand 0 -- the tape's [1,1] / [1,212,209] / [25,0,209] -- then, because OUR "
              "scythe row carries a +5 energy word, the maximum re-declared (41) with its "
              "rescaled regeneration (43)", str(b1))
        check(agents.PLAYER_WEAPON["item_type"] == 35 and agents.PLAYER_OFFHAND is None
              and authsrv.ATTACK_INTERVAL == rate(35) and st["weapon_set"] == 1,
              "and the server's hands follow: a scythe (type 35), no off hand, its own interval",
              f"{authsrv.ATTACK_INTERVAL} against {rate(35)}")
        b2 = switch(2)
        check(b2 == [(0x0148, [1, 2]), (0x0152, [1, 11, 13]), (0x006F, [P, 0, 13])],
              "1 -> 2 (scythe -> spear): the same three, and NO energy words -- both rows "
              "carry the same +5, so the maximum did not move", str(b2))
        b3 = switch(3)
        check(b3 == [(0x0148, [1, 3]), (0x014B, [1, 16, 1, 1]), (0x0152, [1, 13, 15]),
                     (0x006F, [P, 0, 15]), (0x006F, [P, 1, 16])],
              "2 -> 3 (spear -> spear + shield): the shield's 0x014B into the equipped bag's "
              "slot 1 BEFORE the lead swap, then hand 0, then hand 1 -- the tape's "
              "[1,207,3,1] / [1,210,208] / [25,0,208] / [25,1,207]", str(b3))
        check(agents.PLAYER_OFFHAND is not None and agents.PLAYER_OFFHAND["item_type"] == 24
              and agents.PLAYER_WEAPON["item_type"] == 36,
              "a spear in hand and the shield on the arm")
        b0 = switch(0)
        check(b0 == [(0x0148, [1, 0]), (0x014B, [1, 16, 2, 3]), (0x0152, [1, 15, 1]),
                     (0x006F, [P, 1, 0]), (0x006F, [P, 0, 1])] + energy(E25),
              "3 -> 0 (spear + shield -> axe): the shield back to ITS backpack slot, the swap, "
              "the EMPTIED off hand first, then hand 0 -- the tape's [1,207,2,1] / "
              "[1,208,212] / [25,1,0] / [25,0,212] -- then the maximum back to 25", str(b0))
        check(agents.PLAYER_WEAPON["item_type"] == 2 and agents.PLAYER_OFFHAND is None
              and authsrv.ATTACK_INTERVAL == rate(2) and st["weapon_set"] == 0,
              "and the axe is back, no off hand, the axe's interval")

        # RUN-W9-2 (2026-09-19): a BASE change re-declares the 0x0035 (base,
        # modifier) pair, and retail TIMES IT TO THE NEXT ATTACK START, not to
        # the switch batch -- OBSERVED on RUN-1A (20260919T103604, agent 25):
        # the axe->scythe switch at t=303.4 is answered by 0x0035 [25, 1.5, 1.0]
        # at the observer's next swing t=323.5, spear+shield->axe at 590.7 by
        # [25, 1.33, 1.0] at 597.0, and the two SAME-base switches sent none
        # (2 of 2 each way). So the switch batch carries NO 0x0035; the pending
        # is armed and `attack_speed_flush` sends it at the start.
        st2 = {"agents": {}, "pos": (0.0, 0.0), "player_health": 480.0,
               "weapon_set": 0}
        authsrv.apply_party_character({"player_weapon": "starter_axe"})   # 1.33

        def batch_then_flush(kk):
            del sent[:]
            authsrv.select_weapon_set(send, st2, kk, 1)
            in_batch = [(op, v) for op, v in sent if op == 0x0035]
            del sent[:]
            authsrv.attack_speed_flush(send, st2, P)
            at_start = [(op, v) for op, v in sent if op == 0x0035]
            return in_batch, at_start

        ib1, f1 = batch_then_flush(1)     # axe 1.33 -> scythe 1.5: base change
        ib2, f2 = batch_then_flush(2)     # scythe 1.5 -> spear 1.5: same base
        ib0, f0 = batch_then_flush(0)     # spear 1.5 -> axe 1.33: base change
        A133, A150, A10 = authsrv._f32(1.33), authsrv._f32(1.5), authsrv._f32(1.0)
        check(ib1 == [] and ib2 == [] and ib0 == []
              and f1 == [(0x0035, [P, A150, A10])]
              and f2 == []
              and f0 == [(0x0035, [P, A133, A10])],
              "RUN-W9-2: the switch batch carries no 0x0035; a base-changing "
              "switch arms it for the NEXT start (axe->scythe 1.5, ->axe 1.33) "
              "and a same-base switch arms nothing -- retail's 2/2 each way",
              f"in-batch {ib1}/{ib2}/{ib0}, at-start {f1}/{f2}/{f0}")

        # nothing on a same-set press or an empty set
        st["weapon_set"] = 0
        authsrv.apply_party_character({"player_weapon": "starter_axe"})
        check(switch(0) == [] and st["weapon_set"] == 0,
              "a press on the ACTIVE set sends nothing (NOT OBSERVED on retail; the smaller claim)")
        authsrv.WEAPON_SETS[2] = None
        check(switch(2) == [] and st["weapon_set"] == 0,
              "a press on an EMPTY set sends nothing (NOT OBSERVED; the log names --weapon-set)")
        # set 0 with a shield: the shield gets a backpack slot and comes BACK
        authsrv.WEAPON_SETS[:] = [{"lead": "starter_hammer", "off": None}, None, None, None]
        authsrv.apply_party_character({"player_weapon": "starter_sword",
                                       "player_offhand": "starter_shield"})
        authsrv.configure_weapon_sets(["1=starter_scythe"])
        st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 480.0}
        b1 = switch(1)
        b0 = switch(0)
        check(b1 == [(0x0148, [1, 1]), (0x014B, [1, 10, 2, 0]), (0x0152, [1, 1, 11]),
                     (0x006F, [P, 1, 0]), (0x006F, [P, 0, 11])] + energy(E30)
              and b0 == [(0x0148, [1, 0]), (0x014B, [1, 10, 1, 1]), (0x0152, [1, 11, 1]),
                         (0x006F, [P, 0, 1]), (0x006F, [P, 1, 10])] + energy(E25)
              and agents.PLAYER_OFFHAND is not None,
              "a sword-and-shield set 0 against a scythe: the shield (item 10) leaves to "
              "backpack slot 0 and comes back to equipped slot 1, and the server's off hand "
              "is restored with it (RECONSTRUCTION: set 0's shield was never in the backpack)",
              f"{b1} / {b0}")
        # ---- the desk close, 2026-09-19 (studies/weapons/PLAN.md 29): the
        # CLIENT'S reading of the batch, as a model of ItCliInv's own asserts.
        # 0x0152's handler (0x00846840) resolves both items by id and the
        # inventory by the FIRST field (ItCliApi:2253 item1 / :2254 item2 /
        # :2257 inventory) and calls the swap worker 0x84b020: both items must
        # be IN a bag (ItCliInv:687/688 item->IsInInventory()), both are
        # REMOVED (0x84aeb0, :621/622 bag->GetItem(slot) == item) and each is
        # ADDED at the other's old (bag, slot) (0x849ea0, :105
        # !bagParent->GetItem(slot) -- the slot must be EMPTY). 0x013E is the
        # add worker alone; 0x014B is remove-if-in-a-bag then add. The model
        # IS those asserts, so a batch that would crash the client reddens here
        # -- and the last check proves the model can go red.
        EQ, BP = authsrv.EQUIPPED_BAG_ID, authsrv.BACKPACK_BAG_ID

        class ClientBags:
            def __init__(self):
                self.at, self.where = {}, {}     # (bag, slot) -> item; item -> (bag, slot)

            def add(self, item, bag, slot):
                if (bag, slot) in self.at:
                    raise AssertionError(f"ItCliInv:105 !bagParent->GetItem(slot): "
                                         f"{(bag, slot)} holds {self.at[(bag, slot)]}, "
                                         f"adding {item}")
                self.at[(bag, slot)] = item
                self.where[item] = (bag, slot)

            def remove(self, item):
                if item not in self.where:
                    raise AssertionError(f"ItCliInv:621 bag: item {item} is in no bag")
                del self.at[self.where.pop(item)]

            def feed(self, msgs):
                for op, v in msgs:
                    if op == 0x013E:
                        self.add(v[1], v[2], v[3])
                    elif op == 0x014B:
                        if v[1] in self.where:
                            self.remove(v[1])
                        self.add(v[1], v[2], v[3])
                    elif op == 0x0152:
                        a, b = v[1], v[2]
                        if a not in self.where or b not in self.where:
                            raise AssertionError(f"ItCliInv:687/688 IsInInventory: {a} / {b}")
                        pa, pb = self.where[a], self.where[b]
                        self.remove(a)
                        self.remove(b)
                        self.add(a, *pb)
                        self.add(b, *pa)
                return self

            def hands(self):
                return (self.at.get((EQ, 0), 0), self.at.get((EQ, 1), 0))

        def client_after(sets, weapon, offhand=None):
            """The create as the client files it: set 0 into the equipped bag
            (authsrv's ITEM_MOVED_TO_LOCATION(weapon -> equipped 0) and
            (offhand -> equipped 1)), then declare_weapon_sets' moves."""
            authsrv.WEAPON_SETS[:] = [{"lead": "starter_hammer", "off": None}, None, None, None]
            authsrv.apply_party_character({"player_weapon": weapon, "player_offhand": offhand})
            authsrv.configure_weapon_sets(sets)
            cb = ClientBags()
            cb.add(authsrv.WEAPON_ITEM_ID, EQ, 0)
            if offhand:
                cb.add(authsrv.OFFHAND_ITEM_ID, EQ, 1)
            del sent[:]
            authsrv.declare_weapon_sets(send)
            return cb.feed(sent)

        def cycle(cb, ks):
            hands_ok, crash = [], None
            try:
                for kk in ks:
                    cb.feed(switch(kk))
                    hands_ok.append(cb.hands() == authsrv.weapon_set_items(kk))
            except AssertionError as e:                                        # noqa: BLE001
                crash = str(e)
            return hands_ok, crash

        st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 480.0}
        cb = client_after(["1=starter_scythe", "2=starter_spear",
                           "3=starter_spear+starter_shield"], "starter_axe")
        created = dict(cb.where)
        ok1, crash1 = cycle(cb, (1, 2, 3, 0))
        check(crash1 is None and ok1 == [True] * 4
              and cb.where[15] == created[11] and cb.where[11] == created[13]
              and cb.where[13] == created[15] and cb.where[1] == (EQ, 0)
              and cb.where[16] == created[16] and created[16] == (BP, 3),
              "the client's swap ROTATES the leads: after one 0->1->2->3->0 cycle each "
              "inactive lead sits in the NEXT set's created slot (15 at 11's, 11 at 13's, 13 "
              "at 15's), the axe is back in the hands and the shield in ITS created slot -- "
              "why the server names no lead's slot after the create",
              f"{crash1} / {ok1} / {cb.where} from {created}")
        ok2, crash2 = cycle(cb, (1, 2, 3, 0, 3, 1, 0))
        check(crash2 is None and ok2 == [True] * 7,
              "a second cycle and a scramble (3 -> 1 -> 0) trip none of the client's asserts "
              "(ItCliInv:105 empty slot, :621 in a bag, :687/688 both in inventory), and the "
              "equipped bag holds exactly the active set's items after every switch",
              f"{crash2} / {ok2}")
        # a shield at BOTH ends: set 0 sword + shield (item 10) against set 3
        # spear + shield (item 16) -- one batch moves one shield OUT and one IN,
        # and the add worker's empty-slot assert is why the leaving one is first
        cb = client_after(["1=starter_scythe", "3=starter_spear+starter_shield"],
                          "starter_sword", "starter_shield")
        st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 480.0}
        b3 = switch(3)
        moves = [v for op, v in b3 if op == 0x014B]
        try:
            cb.feed(b3)
            cb3_ok, crash3 = cb.hands() == (15, 16), None
            cb.feed(switch(0))
            cb0_ok = cb.hands() == (1, 10) and cb.where[16] == (BP, 3)
        except AssertionError as e:                                            # noqa: BLE001
            cb3_ok, cb0_ok, crash3 = False, False, str(e)
        check(crash3 is None and cb3_ok and cb0_ok
              and moves == [[1, 10, BP, 0], [1, 16, EQ, 1]],
              "a shield at both ends (sword + shield -> spear + shield -> back): the leaving "
              "shield's 0x014B (10 -> backpack 0) precedes the entering one's (16 -> equipped 1) "
              "and the model accepts both batches -- the hands read (15, 16) then (1, 10), the "
              "second shield back in its created slot",
              f"{crash3} / {moves} / {cb.where}")
        # the control: the same two moves the other way round would put 16 into
        # equipped slot 1 while 10 still holds it -- the client's ItCliInv:105
        cbx = client_after(["3=starter_spear+starter_shield"], "starter_sword", "starter_shield")
        try:
            cbx.feed([(0x014B, [1, 16, EQ, 1]), (0x014B, [1, 10, BP, 0])])
            tripped = None
        except AssertionError as e:                                            # noqa: BLE001
            tripped = str(e)
        check(tripped is not None and "ItCliInv:105" in tripped,
              "and the model can go red: the entering shield sent FIRST trips the empty-slot "
              "assert (ItCliInv:105) -- the order above is a client constraint, not taste",
              str(tripped))
        # the flag's refusals
        for bad in ("4=starter_axe", "1=hostile_bow", "x=starter_axe", "1=", "1=no_such_item"):
            try:
                authsrv.configure_weapon_sets([bad])
                ok = False
            except (SystemExit, Exception):                                    # noqa: BLE001
                ok = True
            check(ok, f"--weapon-set {bad!r} is refused at launch")
        authsrv.configure_weapon_sets(["2=starter_bow+starter_shield"])
        check(authsrv.WEAPON_SETS[2] == {"lead": "starter_bow", "off": None},
              "a two-handed lead drops its off hand at configure time (WEAPONS-W1's rule)")
        row = authsrv.apply_party_character({"player_weapon_sets": [[3, "starter_spear", "starter_shield"]]})
        check(authsrv.WEAPON_SETS[3] == {"lead": "starter_spear", "off": "starter_shield"}
              and any("set 3" in c for c in row),
              "a party row's player_weapon_sets fills a set through the same door")
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check("elif opcode == GAME_CMSG_SELECT_WEAPON_SET:" in src
              and "select_weapon_set(send, state, int(values[1]), conn_id)" in src
              and '"--weapon-set"' in sargs and "configure_weapon_sets(a.weapon_set)" in src,
              "the dispatch arm for c2s 0x0032 and the --weapon-set flag exist")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE) = saved[:5]
        authsrv.WEAPON_SETS[:] = saved[5]
        authsrv.WEAPON_SET_BACKPACK_SLOTS.clear()
        authsrv.WEAPON_SET_BACKPACK_SLOTS.update(saved[6])


def _mod(ident, arg, arg2=0):
    """Compose one modifier word by the client walker's own layout."""
    return (ident << 20) | (arg << 8) | arg2


def section_damage_type_and_requirement():
    print("\n19. WEAPONS-W4: the damage type against the vs-type armour, and the 633 requirement")
    cm = combatmath
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.TYPED_ARMOUR, authsrv.UNMET_REQUIREMENT, agents.item_template)
    try:
        # the enum: the client's fourteen, the wiki's two classes
        table = agents.WORLD.get("damage_type", "table")
        classes = agents.WORLD.get("damage_type", "classes")
        check(len(table["name_ids"]) == 14 and len(table["adjective_ids"]) == 14
              and len(table["labels"]) == 14 and table["none"] == 14
              and table["name_ids"][0] == 2014 and table["name_ids"][5] == 2020
              and table["name_ids"][11] == 2018 and table["name_ids"][13] == table["name_ids"][7]
              and table["adjective_ids"][13] == table["adjective_ids"][7],
              "content carries the client's fourteen-entry s_charDamage tables (names 2014.., "
              "adjectives 2001..), index 13 duplicating 7 in both, and 14 as 'no type'")
        check([cm.damage_class(i) for i in (0, 1, 2)] == ["physical"] * 3
              and [cm.damage_class(i) for i in (3, 4, 5, 11)] == ["elemental"] * 4
              and [cm.damage_class(i) for i in (6, 7, 8, 9, 10, 12)] == ["other"] * 6
              and cm.damage_class(14) is None and cm.damage_class(None) is None
              and cm.damage_class("elemental") == "elemental"
              and sorted(classes["physical"]) == [0, 1, 2]
              and sorted(classes["elemental"]) == [3, 4, 5, 11],
              "blunt / piercing / slashing are physical, cold / lightning / fire / earth "
              "elemental, chaos / dark / holy / nature / sacrifice / generic neither, 14 and "
              "None untyped (WIKI's grouping over the client's ids)")
        check(cm.damage_type_label(0) == "blunt" and cm.damage_type_label(2) == "slashing"
              and cm.damage_type_label(11) == "earth" and cm.damage_type_label(14) == "untyped"
              and cm.damage_type_label("physical") == "physical",
              "the one-word labels resolve by id")
        # the vault: the tables against the pinned client itself
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
            import itemmods, pinned                                       # noqa: PLC0415
            img = itemmods.Image(pinned.find()[0])
            names = [img.u32(0x00A38624 + 4 * i) for i in range(14)]
            adjs = [img.u32(0x00A385CC + 4 * i) for i in range(14)]
        except (Exception, SystemExit) as e:                               # noqa: BLE001
            names = adjs = None                    # pinned.find exits on a bare machine
            LEDGER.skip("section 19", f"the pinned client is absent ({type(e).__name__}) -- 1 check")
        if names is not None:
            check(names == list(table["name_ids"]) and adjs == list(table["adjective_ids"]),
                  "and the two tables read back from the pinned client (VA 0x00A38624 and "
                  "0x00A385CC) byte for byte -- a re-extraction that could disagree",
                  f"{names} / {adjs}")
        # what our items deal
        item = agents.item_template
        check(cm.item_damage_type(item("starter_axe")) == 2
              and cm.item_damage_type(item("starter_bow")) == 1
              and cm.item_damage_type(item("starter_hammer")) == 0
              and cm.item_damage_type(item("starter_spear")) == 1
              and cm.item_damage_type(item("hostile_bow")) == 1
              and cm.damage_class(cm.item_damage_type(item("starter_wand"))) in ("elemental", "other")
              and cm.item_damage_type({"modifiers": []}) is None,
              "the 587 reader: axe slashing, bow / spear / hostile bow piercing, hammer blunt, "
              "the wand an element or chaos, an item with no type line None")
        # the pieces, typed
        body = item("warrior_body")
        check(cm.item_words(body) == [(572, 25, 0), (4, 0, 0), (527, 20, 0)]
              and authsrv.armour_of_piece(body, 2) == (25.0, 20.0)
              and authsrv.armour_of_piece(body, "physical") == (25.0, 20.0)
              and authsrv.armour_of_piece(body, 5) == (25.0, 0.0)
              and authsrv.armour_of_piece(body, 6) == (25.0, 0.0)
              and authsrv.armour_of_piece(body, None) == (25.0, 0.0)
              and authsrv.armour_of_piece(body, physical=False) == (25.0, 0.0),
              "the warrior body [572 25, 4, 527 20]: +20 against slashing (2) and 'physical', "
              "nothing against fire (5), chaos (6), an untyped hit or the old physical=False")
        elem = {"modifiers": [_mod(572, 25), _mod(3, 0), _mod(527, 10)]}
        named = {"modifiers": [_mod(572, 25), _mod(5, 5), _mod(527, 10)]}
        situ = {"modifiers": [_mod(572, 25), _mod(9, 0), _mod(527, 10)]}
        plain = {"modifiers": [_mod(572, 25), _mod(527, 10)]}
        both = {"modifiers": [_mod(572, 25), _mod(4, 0), _mod(527, 20), _mod(3, 0), _mod(527, 10)]}
        check(authsrv.armour_of_piece(elem, 5) == (25.0, 10.0)
              and authsrv.armour_of_piece(elem, 3) == (25.0, 10.0)
              and authsrv.armour_of_piece(elem, 2) == (25.0, 0.0)
              and authsrv.armour_of_piece(elem, 6) == (25.0, 0.0),
              "a [572, 3, 527 10] piece (+10 vs. elemental, the corpus's 55): counts against "
              "fire and cold, not slashing, not chaos")
        check(authsrv.armour_of_piece(named, 5) == (25.0, 10.0)
              and authsrv.armour_of_piece(named, 3) == (25.0, 0.0)
              and authsrv.armour_of_piece(named, "elemental") == (25.0, 0.0),
              "a [572, 5 arg 5, 527 10] piece (+10 vs. fire, the named form, on no corpus item): "
              "fire only -- not cold, and not a bare class")
        check(authsrv.armour_of_piece(situ, 2) == (25.0, 0.0)
              and authsrv.armour_of_piece(situ, 5) == (25.0, 0.0)
              and authsrv.armour_of_piece(plain, 2) == (25.0, 10.0)
              and authsrv.armour_of_piece(plain, 5) == (25.0, 10.0)
              and authsrv.armour_of_piece(both, 2) == (25.0, 20.0)
              and authsrv.armour_of_piece(both, 5) == (25.0, 10.0),
              "a situational condition (9, 'while attacking') adds nothing to anything -- not "
              "modelled, said once; an unconditioned 527 counts against everything; two "
              "conditioned lines each answer their own type")
        # through the location reader and the body's item
        state = {"agents": {}, "pos": (0.0, 0.0), "player_health": 480.0}
        authsrv.apply_party_character({"player_weapon": "starter_axe"})
        agents.PLAYER_OFFHAND = None
        chest_phys = authsrv.player_armour_at("warrior_body", 2, state)
        chest_cold = authsrv.player_armour_at("warrior_body", 3, state)
        check(chest_phys == 45.0 and chest_cold == 25.0
              and authsrv.player_armour_at("warrior_body") == 45.0
              and authsrv.player_spell_armour() == 25.0,
              "the chest reads 45 against a slashing hit and 25 against a cold one; the default "
              "is physical and a spell is elemental, as before",
              f"{chest_phys} / {chest_cold}")
        wand_type = cm.item_damage_type(item("starter_wand"))
        check(authsrv.body_damage_type({"weapon_item": "starter_wand"}) == wand_type
              and authsrv.body_damage_type({"weapon_item": "hostile_bow"}) == 1
              and authsrv.body_damage_type({}) == "physical"
              and authsrv.body_damage_type({"weapon_item": "no_such_item"}) == "physical",
              "land_swing's type is the body's own item's 587 -- a wand's element, a bow's "
              "piercing -- and 'physical' for a creature with no item or an unknown one")
        authsrv.TYPED_ARMOUR = False
        check(authsrv.body_damage_type({"weapon_item": "starter_wand"}) == "physical",
              "--no-typed-armour: every body deals 'physical' (the pre-W4 reading)")
        authsrv.TYPED_ARMOUR = True
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check("player_armour_at(location, damage_type=body_damage_type(agent)," in src
              and '"--no-typed-armour"' in sargs and '"--no-unmet-requirement"' in sargs,
              "land_swing reads the armour against the body's type, and both revert flags exist")
        # the requirement: 633 {attribute, rank}
        req_hammer = dict(item("starter_hammer"))
        req_hammer["modifiers"] = [_mod(587, 0), _mod(634, 22, 15), _mod(633, 19, 9)]
        check(cm.weapon_requirement(item("starter_axe")) is None
              and cm.weapon_requirement(req_hammer) == (19, 9)
              and cm.requirement_met(item("starter_axe"), {}) is True
              and cm.requirement_met(req_hammer, {19: 9}) is True
              and cm.requirement_met(req_hammer, {19: 8}) is False
              and cm.requirement_met(req_hammer, {}) is False
              and cm.requirement_met(req_hammer, lambda a: 12 if a == 19 else 0) is True
              and cm.weapon_damage_range(req_hammer) == (15, 22),
              "633 reads (attribute 19, rank 9) on a made hammer; met at 9 and above, unmet "
              "below or with no rank; a callable rank works; the 634 range reads as before")
        # the player's rank in the ITEM's attribute, and the divisor
        req_sword = dict(item("starter_sword"))
        req_sword["modifiers"] = [_mod(587, 2), _mod(634, 22, 15), _mod(633, 17, 9)]
        plain_sword = dict(req_sword, modifiers=[_mod(587, 2), _mod(584, 22, 15)])
        agents.PLAYER_WEAPON = req_sword
        r17 = authsrv.player_rank_of(17)
        via_633 = authsrv.player_weapon_rank({})
        agents.PLAYER_WEAPON = plain_sword
        r20 = authsrv.player_rank_of(20)
        via_table = authsrv.player_weapon_rank({})
        check(via_633 == r17 and via_table == r20 and r17 != r20,
              "player_weapon_rank reads the item's 633 attribute first (a sword requiring "
              "Strength 17 swings on the Strength rank), and the type table (Swordsmanship "
              "20) for an item with none", f"{via_633} = {r17} / {via_table} = {r20}")
        agents.PLAYER_WEAPON = req_hammer                  # Hammer Mastery 19 at 9
        r19 = authsrv.player_rank_of(19)
        div = cm.UNMET_REQUIREMENT_DIVISOR
        check(abs(div - 3.098) < 1e-9
              and authsrv.player_requirement_factor(None, rank=8) == 1.0 / div
              and authsrv.player_requirement_factor(None, rank=9) == 1.0
              and authsrv.player_requirement_factor(None) == (1.0 if r19 >= 9 else 1.0 / div)
              and authsrv.player_requirement_met(req_hammer, None, rank=3) is False
              and authsrv.player_requirement_met(req_hammer, None, rank=9) is True,
              "the unmet factor is 1 / 3.098 (the isle's divisor) below the requirement and 1 "
              "at or above it, on the rank handed in (the Weakness-cut one at a hit site)")
        authsrv.UNMET_REQUIREMENT = False
        check(authsrv.player_requirement_factor(None, rank=1) == 1.0
              and authsrv.body_requirement_factor({"weapon_item": "starter_axe"}) == 1.0,
              "--no-unmet-requirement: the factor is 1 whatever the rank")
        authsrv.UNMET_REQUIREMENT = True
        # the isle's rank ladder, reproduced through swing_damage with the divisor
        # as the multiplier (studies/isle/FINDINGS.md 9.1-9.2: a 15-22 hammer,
        # customised x1.2, AR 60, ranks 5..8 -- means 3.864 / 4.296 / 4.637 /
        # 5.093 and bands 3..5 / 4..5 / 4..5 / 4..6)
        observed = {5: 3.864, 6: 4.296, 7: 4.637, 8: 5.093}
        bands = {5: {3, 4, 5}, 8: {4, 5, 6}}
        means, sets = {}, {}
        for r in (5, 6, 7, 8):
            vals = [cm.swing_damage(r, 60.0, (15, 22), roll=float(x), mult=1.2 / div,
                                    ARMOUR_DIVISOR=40.0, CRITICAL_ARMOUR_REDUCTION=20.0)
                    for x in range(15, 23)]
            means[r] = sum(vals) / len(vals)
            sets[r] = set(vals)
        check(all(abs(means[r] / observed[r] - 1.0) < 0.03 for r in observed)
              and sets[5] == bands[5] and sets[8] == bands[8],
              "the isle's rank ladder reproduced: the divisor on the rank-appropriate damage "
              "puts every block's mean within 3 % of the observed 3.864 / 4.296 / 4.637 / "
              "5.093, with rank 5's band 3..5 (its eleven 3s) and rank 8's 4..6 (its twenty 6s)",
              f"{ {r: round(m, 3) for r, m in means.items()} } bands {sets[5]} / {sets[8]}")
        # a body under the same rule
        agents.item_template = lambda key, _it=item: req_hammer if key == "req_hammer" else _it(key)
        low = {"weapon_item": "req_hammer", "attributes": [[19, 3]]}
        high = {"weapon_item": "req_hammer", "attributes": [[19, 12]]}
        check(authsrv.body_requirement_factor(low) == 1.0 / div
              and authsrv.body_requirement_factor(high) == 1.0
              and authsrv.body_requirement_factor({"weapon_item": "starter_axe"}) == 1.0
              and authsrv.body_requirement_factor({}) == 1.0,
              "a body swinging a hammer it lacks the rank for divides too; met, unrequired "
              "or unarmed bodies do not")
        agents.item_template = item
        # a required shield: 635 in full when met, the wiki's 8 / 5 when not
        shield16 = {"item_type": 24, "modifiers": [_mod(633, 17, 9), _mod(635, 16)]}
        shield12 = {"item_type": 24, "modifiers": [_mod(633, 17, 9), _mod(635, 12)]}
        check(authsrv.armour_of_piece(shield16, 2, met=True) == (16.0, 0.0)
              and authsrv.armour_of_piece(shield16, 2, met=False) == (8.0, 0.0)
              and authsrv.armour_of_piece(shield12, 2, met=False) == (5.0, 0.0)
              and authsrv.armour_of_piece(item("starter_shield"), 2) is not None,
              "a required shield's 635 is its armour when met; unmet, 8 for a 16-armour "
              "shield and 5 below it (WIKI, GWW 'Requirement'); a plain 572 shield as before")
        agents.PLAYER_OFFHAND = shield16
        agents.PLAYER_WEAPON = item("starter_sword")
        r17 = authsrv.player_rank_of(17)
        off_now = authsrv.offhand_armour("physical")
        authsrv.UNMET_REQUIREMENT = False
        off_off = authsrv.offhand_armour("physical")
        authsrv.UNMET_REQUIREMENT = True
        check(off_now == (16.0 if r17 >= 9 else 8.0) and off_off == 16.0,
              "the held shield's contribution follows the character's Strength rank against "
              "its 633, and --no-unmet-requirement gives the full 16",
              f"rank 17 = {r17}: {off_now} / {off_off}")
        # a required focus: 636 in full when met, +3 when not
        focus = {"item_type": 12, "modifiers": [_mod(633, 5, 8), _mod(636, 12)]}
        agents.PLAYER_OFFHAND = focus
        r5 = authsrv.player_rank_of(5)
        e_now = authsrv.weapon_energy_bonus()
        authsrv.UNMET_REQUIREMENT = False
        e_off = authsrv.weapon_energy_bonus()
        authsrv.UNMET_REQUIREMENT = True
        agents.PLAYER_OFFHAND = item("starter_focus")
        e_plain = authsrv.weapon_energy_bonus()
        check(e_now == (12 if r5 >= 8 else 3) and e_off == 12 and e_plain == 5,
              "a required focus's 636 is its energy when met and +3 when not (WIKI); the "
              "revert gives the full 12; a plain 556 focus still gives its 5 (WEAPONS-W5)",
              f"rank 5 = {r5}: {e_now} / {e_off} / {e_plain}")
        # the launch banner
        agents.PLAYER_OFFHAND = None
        b_axe = authsrv.requirement_banner(item("starter_axe"))
        b_req = authsrv.requirement_banner(req_hammer)
        b_met = authsrv.requirement_banner(req_sword if r17 >= 9 else
                                           dict(req_sword, modifiers=[_mod(587, 2), _mod(633, 17, 0)]))
        check(b_axe == "weapon: deals slashing [WEAPONS-W4]"
              and "deals blunt" in b_req and "requires attribute 19 at 9" in b_req
              and ("UNMET" in b_req) == (r19 < 9)
              and "MET" in b_met and "UNMET" not in b_met
              and authsrv.requirement_banner({"modifiers": []}) is None,
              "the banner names the type dealt and the requirement, MET or UNMET with the "
              "penalty; nothing for an item with no words", f"{b_axe} | {b_req} | {b_met}")
        # ---- identifier 573, "Armor: N (depends on level)" -- a hero's piece
        # (2026-09-19, studies/weapons/PLAN.md 33): (573, high, low) rates
        # the line from `low` at level 1 to `high` at level 20 -- the wiki's
        # hero-armour rows, and the isle's 3 x level + bonus
        hero_w = {"modifiers": [_mod(573, 80, 23), _mod(4, 0), _mod(527, 20)]}   # the corpus's set
        hero_r = {"modifiers": [_mod(573, 70, 13)]}
        hero_c = {"modifiers": [_mod(573, 60, 3)]}
        check(all(cm.level_scaled_rating(23, 80, L) == 3 * L + 20 for L in range(1, 21))
              and all(cm.level_scaled_rating(13, 70, L) == 3 * L + 10 for L in range(1, 21))
              and all(cm.level_scaled_rating(3, 60, L) == 3 * L for L in range(1, 21))
              and cm.level_scaled_rating(23, 80, 0) == 23 and cm.level_scaled_rating(23, 80, 25) == 80
              and cm.level_scaled_rating(23, 80, None) == 23,
              "a 573 pair rates the line from its low end at level 1 to its high end at 20 -- "
              "the wiki's three hero-armour rows (23..80, 13..70, 3..60) are 3 x level + 20 / "
              "10 / 0 at every level, the isle's creature formula; clamped to 1..20; no "
              "level reads the low end")
        check(authsrv.armour_of_piece(hero_w, 2, level=1) == (23.0, 20.0)
              and authsrv.armour_of_piece(hero_w, 2, level=5) == (35.0, 20.0)
              and authsrv.armour_of_piece(hero_w, 2, level=20) == (80.0, 20.0)
              and authsrv.armour_of_piece(hero_w, 5, level=20) == (80.0, 0.0)
              and authsrv.armour_of_piece(hero_r, 2, level=10) == (40.0, 0.0)
              and authsrv.armour_of_piece(hero_c, 2, level=10) == (30.0, 0.0),
              "the corpus's hero set [573 (80, 23), 4, 527 20] reads 23 / 35 / 80 at levels 1 / "
              "5 / 20 with its +20 vs. physical still counting for a slashing hit and not a fire "
              "one; a ranger's and a caster's pair read their own rows")
        agents.item_template = (lambda key, _it=item: hero_w if key == "warrior_body" else _it(key))
        agents.PLAYER_OFFHAND = None
        at7 = authsrv.player_armour_at("warrior_body", 2, {"level": 7})
        at20 = authsrv.player_armour_at("warrior_body", 2, {"level": 20})
        seed = authsrv.player_armour_at("warrior_body", 2)
        agents.item_template = item
        check(at7 == 41.0 + 20.0 and at20 == 80.0 + 20.0
              and seed == 3 * int(agents.PLAYER_LEVEL) + 20 + 20.0,
              "through player_armour_at the connection's level rates the chest -- 61 at level "
              "7, 100 at 20 -- and without a state the character's seed level does",
              f"{at7} / {at20} / {seed} at seed level {agents.PLAYER_LEVEL}")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.TYPED_ARMOUR, authsrv.UNMET_REQUIREMENT, agents.item_template) = saved


def section_half_recharge():
    print("\n20. WEAPONS-W5b: a staff's 570 -- halves a spell's recharge at the completion")
    cm = combatmath
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.HALF_RECHARGE, authsrv.half_recharge_roll)
    try:
        item = agents.item_template
        hsr = item("hsr_staff")
        check(cm.item_words(hsr)[:4] == cm.item_words(item("caster_staff"))
              and cm.item_words(hsr)[4] == (570, 20, 1)
              and (int(hsr["modifiers"][4]) >> 19) & 1 == 1
              and cm.half_recharge_chances((hsr,)) == [20]
              and cm.half_recharge_chances((item("caster_staff"), item("starter_wand"),
                                            item("starter_focus"), None)) == []
              and cm.half_recharge_chances((hsr, hsr)) == [20, 20],
              "hsr_staff is the henchman's staff plus one 570 (arg 20, arg2 1, bit 19 -- the "
              "corpus's encoding); the reader lists one chance per 570 held and none for the "
              "corpus's other caster items")
        check([cm.halved_recharge(s) for s in (0, 1, 2, 3, 4, 5, 8, 12, 20, 45)]
              == [0, 1, 1, 2, 2, 3, 4, 6, 10, 23],
              "half a whole-second recharge to the nearest second, a .5 rounding UP: 5 -> 3, "
              "3 -> 2, 45 -> 23, 1 -> 1 (WIKI 'round to the nearest second'; the .5 is ours)")
        check(all(cm.is_spell_type(c) for c in (4, 5, 6, 9, 11, 24, 25))
              and not any(cm.is_spell_type(c) for c in (3, 7, 8, 10, 12, 14, 15, 16, 19, 22))
              and not cm.is_spell_type(None),
              "the spell types are the client namer's own seven -- hex, spell, enchantment, "
              "well, ward, item and weapon spell -- and a stance, signet, condition, glyph, "
              "attack, shout, preparation or ritual is not one")
        # the roll, rigged
        r = authsrv.half_recharge_roll
        check(r((hsr,), 83, rng=lambda: 0.199) == (True, [20])
              and r((hsr,), 83, rng=lambda: 0.20) == (False, [20])
              and r((hsr,), 1, rng=lambda: 0.0) == (False, [20])
              and r((item("caster_staff"),), 83, rng=lambda: 0.0) == (False, [])
              and r((), 83, rng=lambda: 0.0) == (False, []),
              "the roll: under 20 % halves a spell (83, type 5), at or over it does not; a "
              "signet (1) never; a staff with no 570 or empty hands never")
        draws = iter([0.5, 0.1])
        check(r((hsr, hsr), 83, rng=lambda: next(draws)) == (True, [20, 20]),
              "two 570s are two triggers: the second succeeding halves when the first missed "
              "(the cap is a halving, so one success is the whole effect)")
        authsrv.HALF_RECHARGE = False
        check(r((hsr,), 83, rng=lambda: 0.0) == (False, [20]),
              "--no-half-recharge: never, the chances still read")
        authsrv.HALF_RECHARGE = True
        # through the real press -> completion: the E5's integer and the E6 clock
        try:
            row = agents.WORLD.get("skills", "83")
            ok_row = (int(row["type_code"]) == 5 and int(row["recharge"]) == 5
                      and int(row["energy"]) <= 10)
        except Exception:                                                  # noqa: BLE001
            ok_row = False
        if not ok_row:
            LEDGER.skip("section 20", "skill 83's row (a 5 s self spell) is absent -- 3 checks")
        else:
            P = authsrv.PLAYER_AGENT_ID

            def press_spell(force):
                authsrv.half_recharge_roll = (
                    lambda items, sid, rng=None, _o=r: _o(items, sid, rng=lambda: force))
                authsrv.apply_party_character({"player_weapon": "hsr_staff"})
                st, sent = _world(300.0), []
                send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
                authsrv.handle_skill_press([0, 83, 0, P], send, st, 1,
                                           authsrv.GAME_CMSG_USE_SKILL)
                sent.clear()
                casts = st.get("pending_casts") or []
                for cast in casts:
                    for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                        cast[k] -= float(cast.get("activation", 1.0)) + 0.05
                authsrv.cast_tick(send, st, 1)
                e5 = [v for op, v in sent if op == 0x00E5]
                cast = casts[0] if casts else {}
                return e5, cast

            e5_h, cast_h = press_spell(0.0)                 # the roll succeeds
            e5_t, cast_t = press_spell(0.99)                # the roll misses
            check(e5_h == [[P, 83, 0, 3]] and cast_h.get("recharge") == 3
                  and abs(cast_h["e6_at"] - cast_h["e5_at"] - 3.0) < 1e-6,
                  "a spell completing under a 570 that triggers: the 0x00E5 carries 3 where "
                  "the table says 5, and the E6 clock is 3 s past the E5", f"{e5_h} / {cast_h}")
            check(e5_t == [[P, 83, 0, 5]] and cast_t.get("recharge") == 5
                  and abs(cast_t["e6_at"] - cast_t["e5_at"] - 5.0) < 1e-6,
                  "and one whose roll misses carries the table's 5 with the E6 5 s out",
                  f"{e5_t}")
            authsrv.HALF_RECHARGE = False
            e5_off, _c = press_spell(0.0)
            authsrv.HALF_RECHARGE = True
            check(e5_off == [[P, 83, 0, 5]],
                  "--no-half-recharge: the table's 5 even when the roll would have hit")
        authsrv.half_recharge_roll = r
        # a body: its staff's roll rides its own 0x00E5 through cast_recharge
        body = {"weapon_item": "hsr_staff"}
        check(authsrv.body_weapon_items(body) == (hsr,)
              and authsrv.body_weapon_items({}) == ()
              and authsrv.body_weapon_items({"weapon_item": "no_such"}) == ()
              and r(authsrv.body_weapon_items(body), 83, rng=lambda: 0.0) == (True, [20]),
              "a body holding hsr_staff rolls the same 20 %; a body with nothing or an "
              "unknown key never")
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('agent.pop("cast_recharge",' in src
              and 'agent["cast_recharge"] = recharge' in src
              and "cast[\"e6_at\"] = cast[\"e5_at\"] + cast[\"recharge_s\"]" in src
              and '"--no-half-recharge"' in sargs,
              "the body's halved value is stashed at its start and popped into its 0x00E5; "
              "the player's E6 clock moves with the halving; the revert flag exists")
        check("halves spell recharge at 20 %" in (authsrv.requirement_banner(hsr) or "")
              and "halves" not in (authsrv.requirement_banner(item("caster_staff")) or ""),
              "the launch banner names the chance, and says nothing for a staff without one")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.HALF_RECHARGE, authsrv.half_recharge_roll) = saved


def section_bow_classes():
    print("\n21. WEAPONS-Q2 and the hornbow's 10 %: the client's own bow-class names, the class rate, the penetration")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.BOW_CLASSES, agents.item_template, authsrv.critical_rate)
    try:
        item = agents.item_template
        table = agents.WORLD.get("bow_class", "table")
        rules = agents.WORLD.get("bow_class", "rules")
        check(list(table["name_ids"]) == [69416, 69417, 69418, 69419, 69420]
              and list(table["labels"]) == ["shortbow", "longbow", "flatbow", "recurve", "hornbow"]
              and list(rules["rates"]) == ["shortbow", "longbow", "flatbow", "recurve", "hornbow"]
              and all(k in agents.ATTACK_SPEED for k in rules["rates"])
              and [agents.ATTACK_SPEED[k] for k in rules["rates"]] == [2.025, 2.475, 2.025, 2.475, 2.7]
              and list(rules["armour_penetration"]) == [0.0, 0.0, 0.0, 0.0, 0.10],
              "content: the five class names (0 shortbow, 1 longbow, 2 flatbow, 3 recurve, 4 "
              "hornbow), their rates 2.025 / 2.475 / 2.025 / 2.475 / 2.7 and the hornbow's 0.10 "
              "-- the corpus's two 2.475 classes (1 and 3) ARE the longbow and the recurve")
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
            import itemmods, pinned                                       # noqa: PLC0415
            bc = itemmods.bow_class_table(itemmods.Image(pinned.find()[0]))
        except (Exception, SystemExit) as e:                               # noqa: BLE001
            bc = None
            LEDGER.skip("section 21", f"the pinned client is absent ({type(e).__name__}) -- 1 check")
        if bc is not None:
            check(bc["name_ids"] == list(table["name_ids"]) and bc["table"] == 0x00BCAAEC
                  and bc["handler"] == 0x00924F71,
                  "and the extractor reads the same five ids back from the pinned client's 609 "
                  "handler (0x00924F71, table 0x00BCAAEC)", str(bc))
        sb = item("starter_bow")
        plain = [m for m in sb["modifiers"] if (int(m) >> 20) & 0x3FF != 609]

        def bow(klass):
            return dict(sb, modifiers=plain + [(609 << 20) | (klass << 8)])

        horn, flat = bow(4), bow(2)
        check(authsrv.bow_class(sb) == 1 and authsrv.bow_class(item("hostile_bow")) is None
              and [authsrv.bow_class(bow(k)) for k in range(5)] == [0, 1, 2, 3, 4]
              and authsrv.bow_class(bow(7)) is None
              and authsrv.bow_class(dict(sb, modifiers=plain)) is None
              and authsrv.bow_class(item("starter_axe")) is None,
              "the reader: starter_bow is class 1 (a longbow); the type-28 hostile bow has NO class "
              "(the handler reads 609 on type 5 only); classes 0..4 read; a 7, a bow with no 609 "
              "and an axe read None")
        check([authsrv.bow_class_label(bow(k)) for k in range(5)]
              == ["shortbow", "longbow", "flatbow", "recurve", "hornbow"]
              and [agents.ATTACK_SPEED[authsrv.weapon_rate_key(bow(k))] for k in range(5)]
              == [2.025, 2.475, 2.025, 2.475, 2.7]
              and authsrv.weapon_rate_key(item("starter_axe")) == "axe"
              and authsrv.weapon_rate_key(item("hostile_bow")) == authsrv.WEAPON_TYPE_RATE[28],
              "the labels and the class rate per 609; an axe and the type-28 bow keep their type "
              "row's key")
        agents.item_template = (lambda key, _it=item: horn if key == "test_hornbow"
                                else flat if key == "test_flatbow" else _it(key))
        authsrv.apply_party_character({"player_weapon": "test_hornbow"})
        i_horn = authsrv.ATTACK_INTERVAL
        authsrv.apply_party_character({"player_weapon": "test_flatbow"})
        i_flat = authsrv.ATTACK_INTERVAL
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        i_long = authsrv.ATTACK_INTERVAL
        check((i_horn, i_flat, i_long) == (2.7, 2.025, 2.475),
              "the character's interval follows the held bow's class: 2.7 with a hornbow, 2.025 "
              "with a flatbow, 2.475 with the starter longbow as before",
              f"{i_horn} / {i_flat} / {i_long}")
        check(authsrv.weapon_armour_penetration(horn) == 0.10
              and all(authsrv.weapon_armour_penetration(bow(k)) == 0.0 for k in range(4))
              and authsrv.weapon_armour_penetration(item("starter_axe")) == 0.0
              and [authsrv.penetrated_armour(a, horn) for a in (60.0, 45.0, 81.0, 100.0, 0.0)]
              == [54.0, 41.0, 73.0, 90.0, 0.0]
              and authsrv.penetrated_armour(60.0, sb) == 60.0
              and authsrv.penetrated_armour(None, horn) is None,
              "the hornbow ignores 10 % of the rating -- 60 -> 54, 45 -> 41 (40.5 up), 81 -> 73, "
              "100 -> 90 (the wiki's step 3, rounded) -- and no other class or weapon any")
        # through the real hit_enemy: a hornbow against a longbow on the same target
        authsrv.critical_rate = lambda rank: 0.0            # the roll, not the rule

        def dealt(key, armour=60.0, roll=(20, 20)):
            authsrv.apply_party_character({"player_weapon": key})
            authsrv.PLAYER_SWING_DAMAGE = roll
            st = {"agents": {FOE: _foe(armour)}, "pos": (0.0, 0.0)}
            hp = st["agents"][FOE]["health"]
            rank = authsrv.player_weapon_rank(st) or 0
            authsrv.hit_enemy(lambda *a, **k: None, st, FOE, 1, armed=True)
            return hp - st["agents"][FOE]["health"], rank

        d_horn, r1 = dealt("test_hornbow")
        d_long, r2 = dealt("starter_bow")
        sl = combatmath.attack_strength(r1)
        want_horn = max(0.0, round(20.0 * 2.0 ** ((sl - 54.0) / 40.0)))
        want_long = max(0.0, round(20.0 * 2.0 ** ((sl - 60.0) / 40.0)))
        check(r1 == r2 and d_horn == want_horn and d_long == want_long and d_horn > d_long,
              "a 20-roll hornbow hit on AR 60 lands as if the target wore 54 and out-deals the "
              "longbow's same roll at 60, through the real hit_enemy at the character's own "
              "Marksmanship rank", f"rank {r1}: hornbow {d_horn} (want {want_horn}), "
              f"longbow {d_long} (want {want_long})")
        authsrv.BOW_CLASSES = False
        check(authsrv.weapon_rate_key(horn) == "longbow"
              and authsrv.weapon_armour_penetration(horn) == 0.0
              and authsrv.penetrated_armour(60.0, horn) == 60.0
              and dealt("test_hornbow")[0] == want_long,
              "--no-bow-classes: every bow is the type row's 2.475 and no hornbow penetrates -- "
              "the pre-Q2 reading")
        authsrv.BOW_CLASSES = True
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('armour = penetrated_armour(agent.get("armor_rating"), agents.PLAYER_WEAPON,' in src
              and "armour = penetrated_armour(armour, (body_weapon_items(agent) or (None,))[0]," in src
              and 'arm = penetrated_armour(foe.get("armor_rating"), agents.PLAYER_WEAPON)' in src
              and "_rate = weapon_rate_key(agents.PLAYER_WEAPON)" in src
              and '"--no-bow-classes"' in sargs,
              "the penetration sits at hit_enemy's rating read, at a body's swing on the player "
              "and on a body, and at the preparation splash; the rate at the character's door; "
              "the revert flag exists")
        check("a hornbow (609 = 4) at 2.7 s, +10 % armour penetration" in (authsrv.requirement_banner(horn) or "")
              and "a longbow (609 = 1) at 2.475 s" in (authsrv.requirement_banner(sb) or "")
              and "penetration" not in (authsrv.requirement_banner(sb) or ""),
              "the launch banner names the class, its rate and the hornbow's penetration")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.BOW_CLASSES, agents.item_template, authsrv.critical_rate) = saved


def section_spell_own_type():
    print("\n22. a spell's own damage type: the row's label, the armour it meets, the kind its projectile carries")
    cm = combatmath
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE, authsrv.SPELL_OWN_TYPE)
    try:
        check([cm.damage_type_from_label(l) for l in
               ("Fire damage", "+ Holy damage", "Cold damage", "Lightning damage",
                "Earth damage", "Dark damage", "+ Damage", "Heal", "physical damage", None)]
              == [5, 8, 3, 4, 11, 7, None, None, None, None],
              "a wiki scale label names the client's type: 'Fire damage' 5, '+ Holy damage' 8, "
              "'Cold damage' 3, 'Lightning damage' 4, 'Earth damage' 11, 'Dark damage' 7; "
              "'+ Damage', 'Heal', a class word and None name nothing")
        check([authsrv.spell_damage_type(s) for s in (194, 312, 252, 433, 394, 99999)]
              == [5, 8, 8, 5, None, None],
              "Flare's row reads fire (5), Holy Strike's and Banish's holy (8), Kindle Arrows' "
              "own key fire (5); an attack skill with no label and an unknown id read None")
        authsrv.SPELL_OWN_TYPE = False
        off_194 = authsrv.spell_damage_type(194)
        authsrv.SPELL_OWN_TYPE = True
        how = {"projectile": 1, "arrow": 0, "damage_type": 6, "speed": 1600.0, "range": 1248.0}
        spell_how = authsrv.skill_shot_how(how, 194)
        attack_how = authsrv.skill_shot_how(dict(how, projectile=143), 394)
        authsrv.SPELL_OWN_TYPE = False
        off_how = authsrv.skill_shot_how(how, 194)
        authsrv.SPELL_OWN_TYPE = True
        check(off_194 is None and spell_how["damage_type"] == 5 and spell_how["projectile"] == 343
              and attack_how["damage_type"] == 6 and attack_how["projectile"] == 680
              and off_how["damage_type"] == 6,
              "a spell's shot carries ITS type as the 0x00A7 kind (Flare 5 over a chaos wand's 6) "
              "beside its own projectile; an attack skill keeps the weapon's kind (Power Shot "
              "over the same wand: 6, its own 680); --no-spell-own-type keeps the weapon's",
              f"{spell_how} / {attack_how} / {off_how}")
        authsrv.apply_party_character({"player_weapon": "starter_wand"})
        agents.PLAYER_OFFHAND = None
        elem = combatmath.player_spell_armour(authsrv.EQUIP_ARMOUR, 572, 527)
        phys = combatmath.player_spell_armour(authsrv.EQUIP_ARMOUR, 572, 527, damage_type=2)
        holy = combatmath.player_spell_armour(authsrv.EQUIP_ARMOUR, 572, 527, damage_type=8)
        check(elem == 25.0 and phys == 45.0 and holy == 25.0
              and authsrv.spell_armour_for(194) == 25.0 and authsrv.player_spell_armour() == 25.0
              and authsrv.ARMOUR_RESPECTING_MEANS == frozenset({"Fire damage", "Cold damage",
                                                               "Lightning damage", "Earth damage"})
              and "Holy damage" not in authsrv.ARMOUR_RESPECTING_MEANS,
              "against the pieces' +20 vs. physical an elemental or holy spell meets 25 and a "
              "physical-damage one 45; Flare resolves at 25 as before; the four elemental labels "
              "respect armour and holy skill damage does not", f"{elem} / {phys} / {holy}")
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('_shot = player_ranged(state) if (cast["attack"] and target) else None' in src
              and '"--no-spell-own-type"' in sargs
              and int(agents.WORLD.get("skill_effect", "194")["damage_type"]) == 5,
              "the player's own spells land at the E5 with no projectile (only an attack skill "
              "launches one -- the kind reaches the wire through a body's shot today); the revert "
              "flag exists; Flare's content row carries the key")
        # the wire's witness: Dancing Daggers arrives as EARTH with daggers in hand
        try:
            sys.path.insert(0, HERE)
            import weaponcensus as wc                                     # noqa: PLC0415
            kinds, types = [], set()
            for _name, _gf, s2c in wc.connections("20260819T132414"):
                for r in wc.skill_shots(s2c):
                    if r["skill"] == 858:
                        kinds.append(r.get("kind"))
                        types.add(r["type"])
        except (Exception, SystemExit) as e:                               # noqa: BLE001
            kinds = None
            LEDGER.skip("section 22", f"capture 20260819T132414 is absent ({type(e).__name__}) -- 1 check")
        if kinds is not None:
            check(len(kinds) >= 10 and set(kinds) == {11} and types == {32},
                  "and the tape says so: on 20260819T132414 every Dancing Daggers arrival "
                  "carries kind 11 (earth) with daggers (type 32, piercing) in the caster's hand "
                  "-- the spell's type, not the weapon's", f"{len(kinds)} arrivals {set(kinds)} held {types}")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE, authsrv.SPELL_OWN_TYPE) = saved


def section_base_penetration():
    print("\n23. base armour penetration: the largest base source, the bonus on top, at every site")
    cm = combatmath
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.BASE_PENETRATION, agents.item_template, authsrv.critical_rate)

    def close(a, b):
        return abs(float(a) - float(b)) < 1e-9

    try:
        rules = agents.WORLD.get("armour_penetration", "rules")
        check(int(rules["strength_attribute"]) == 17 and close(rules["strength_per_rank"], 0.01)
              and int(rules["air_magic_attribute"]) == 8 and int(rules["air_magic_damage_type"]) == 4
              and close(rules["air_magic"], 0.25)
              and cm.BASE_PENETRATION_MEANS == "Armor penetration %"
              and authsrv.SCALE_MEANS_DAMAGE.get("Lightning damage") == "standalone"
              and "Lightning damage" in authsrv.ARMOUR_RESPECTING_MEANS
              and all(agents.WORLD.get("skill_effect", str(s)).get("bonus_scale_means")
                      == "Armor penetration %" for s in (398, 1191, 339, 1136, 1551))
              and int(agents.WORLD.get("skill_effect", "229")["damage_type"]) == 4
              and agents.WORLD.get("skill_effect", "230")["scale_means"] == "Lightning damage",
              "content: the rules row -- Strength (17) 1 % a rank, Air Magic (8) 25 % on a "
              "lightning (4) spell -- and the slot's label on the five attack skills' rows; "
              "'Lightning damage' is a standalone damage label that respects armour; the Orb's "
              "and the Javelin's rows carry the wire's lightning")
        check(close(cm.armour_penetration([0.09, 0.20], [0.10]), 0.30)
              and close(cm.armour_penetration([0.11, 0.10]), 0.11)
              and close(cm.armour_penetration([0.09, 0.10]), 0.10)
              and close(cm.armour_penetration([], [0.10]), 0.10)
              and close(cm.armour_penetration([0.0, None], []), 0.0)
              and close(cm.armour_penetration(), 0.0)
              and close(cm.strength_penetration(9), 0.09) and cm.strength_penetration(0) == 0.0
              and cm.strength_penetration(None) == 0.0 and close(cm.strength_penetration(20), 0.20),
              "the wiki's tiers: the LARGEST base (Penetrating Chop's 20 over Strength 9's 9; "
              "Strength 11 over Penetrating Attack's 10, the page's own sentence; 10 over 9), "
              "never their sum, plus every bonus (the hornbow's 10 on top); 1 % a Strength rank")
        check([cm.penetrated_rating(a, p) for a, p in
               ((81, 0.25), (131, 0.25), (80, 0.25), (100, 0.10), (60, 0.09), (60, 0.0), (45, 0.20))]
              == [61.0, 98.0, 60.0, 90.0, 55.0, 60, 36.0]
              and cm.penetrated_rating(None, 0.25) is None
              and close(100.0 * 2.0 ** ((60.0 - cm.penetrated_rating(80, 0.25)) / 40.0), 100.0)
              and abs(2.0 ** (60.0 / 40.0) - 286.0 / 101.0) < 0.015,
              "the wiki's step 3: 81 x 0.75 -> 61 and 131 x 0.75 -> 98 (its own worked examples), "
              "80 -> 60 under an Orb, 100 -> 90, 60 -> 55 at Strength 9 (54.6 up), p = 0 untouched, "
              "None None -- and the tape's Orb: onto 80 it reads its tooltip because 60 IS the "
              "baseline, and 286 / 101 bare is 2^(60/40) within 1.5 % (studies/skills 50.1)")
        item = agents.item_template
        sb = item("starter_bow")
        plain = [m for m in sb["modifiers"] if (int(m) >> 20) & 0x3FF != 609]
        horn = dict(sb, modifiers=plain + [(609 << 20) | (4 << 8)])
        agents.item_template = (lambda key, _it=item: horn if key == "test_hornbow" else _it(key))
        check(authsrv.penetrated_armour(60.0, None, base=0.09) == 55.0
              and authsrv.penetrated_armour(60.0, horn, base=0.10) == 48.0
              and authsrv.penetrated_armour(60.0, sb, base=0.10) == 54.0
              and authsrv.penetrated_armour(60.0, horn) == 54.0
              and authsrv.penetrated_armour(60.0, None) == 60.0
              and authsrv.penetrated_armour(None, None, base=0.2) is None
              and authsrv.skill_base_penetration(99999) == 0.0
              and authsrv.skill_base_penetration(None) == 0.0
              and authsrv.strength_base_penetration(9, None) == 0.0
              and authsrv.player_base_penetration({}, None) == 0.0
              and authsrv.body_base_penetration({}, None) == 0.0,
              "penetrated_armour composes the tiers: a 9 % base alone 60 -> 55, a 10 % base under a "
              "hornbow 48 (the bonus stacks), under a longbow 54, the hornbow alone 54 as before, "
              "nothing 60, None None; no skill, an unknown skill and a plain swing carry no base")
        # the skills' own numbers and the client's slot -- the vault's skills table
        try:
            _ = agents.WORLD.get("skills", "398")["bonus_scale0"]
            have_table = True
        except Exception:                                                  # noqa: BLE001
            have_table = False
            LEDGER.skip("section 23", "the vault's skills table is absent -- 6 checks (the "
                        "skills' own numbers, the slot, the hits, the revert, the bodies, the "
                        "incoming Orb)")
        if have_table:
            got = {s: authsrv.skill_base_penetration(s)
                   for s in (398, 1191, 339, 1136, 1551, 229, 230, 322, 194, 336, 433)}
            check(got == {398: 0.10, 1191: 0.10, 339: 0.20, 1136: 0.20, 1551: 0.25,
                          229: 0.25, 230: 0.25, 322: 0.0, 194: 0.0, 336: 0.0, 433: 0.0},
                  "a skill's own base: Penetrating / Sundering Attack 10 %, Penetrating Blow / "
                  "Chop 20 %, Spear of Lightning 25 %, Lightning Orb and Javelin 25 % (the Air "
                  "Magic rule on their lightning type); Power Attack, Flare, Executioner's Strike "
                  "and Kindle Arrows (fire) none", str(got))

            def slot(s):
                r = agents.WORLD.get("skills", str(s))
                return (int(r["bonus_scale0"]), int(r["bonus_scale15"]), int(r["skill_arguments"]))

            check({s: slot(s) for s in (398, 1191, 339, 1136, 1551)}
                  == {398: (10, 10, 2), 1191: (10, 10, 2), 339: (20, 20, 2), 1136: (20, 20, 2),
                      1551: (25, 25, 6)}
                  and slot(229)[0] == 1800 and int(agents.WORLD.get("skills", "229")["attribute"]) == 8
                  and int(agents.WORLD.get("skills", "230")["attribute"]) == 8,
                  "and the client's own record holds the wiki's number in the bonus slot with equal "
                  "endpoints on five of five (bit clear on the four, set on the spear's), and NOT "
                  "on Lightning Orb (1800) -- its 25 % is the attribute (8) rule")
            # through the real hit_enemy at the seed's Strength 9
            authsrv.critical_rate = lambda rank: 0.0

            def dealt(key, skill_id=None, armour=60.0, roll=(20, 20)):
                authsrv.apply_party_character({"player_weapon": key})
                authsrv.PLAYER_SWING_DAMAGE = roll
                st = {"agents": {FOE: _foe(armour)}, "pos": (0.0, 0.0)}
                hp = st["agents"][FOE]["health"]
                rank = authsrv.player_weapon_rank(st) or 0
                authsrv.hit_enemy(lambda *a, **k: None, st, FOE, 1, armed=True,
                                  skill_strike=skill_id is not None, skill_id=skill_id)
                return hp - st["agents"][FOE]["health"], rank

            s9 = authsrv.player_rank_of(17)
            d_plain, r = dealt("starter_bow")
            d_power, _ = dealt("starter_bow", 322)
            d_blow, _ = dealt("starter_bow", 339)
            d_pen_long, _ = dealt("starter_bow", 398)
            d_pen_horn, _ = dealt("test_hornbow", 398)
            sl = combatmath.attack_strength(r)

            def want(ar):
                return max(0.0, round(20.0 * 2.0 ** ((sl - ar) / 40.0)))

            check(s9 == 9 and d_plain == want(60.0) and d_power == want(55.0)
                  and d_blow == want(48.0) and d_pen_long == want(54.0) and d_pen_horn == want(48.0)
                  and d_power > d_plain and d_blow > d_power,
                  "through the real hit_enemy at the seed's Strength 9 on AR 60: a plain swing lands "
                  "as on 60, Power Attack as on 55 (Strength's 9 %), Penetrating Blow as on 48 (its "
                  "own 20 % beats the 9), Penetrating Attack as on 54 with a longbow and 48 with a "
                  "hornbow (its 10 % plus the bow's 10 %)",
                  f"rank {r}: plain {d_plain} / power {d_power} / blow {d_blow} / pen {d_pen_long} / "
                  f"pen+horn {d_pen_horn}; want {want(60.0)} / {want(55.0)} / {want(48.0)} / "
                  f"{want(54.0)} / {want(48.0)}")
            authsrv.BASE_PENETRATION = False
            d_power_off, _ = dealt("starter_bow", 322)
            d_pen_horn_off, _ = dealt("test_hornbow", 398)
            off = (authsrv.skill_base_penetration(339), authsrv.player_base_penetration({}, 322),
                   authsrv.body_base_penetration({"attributes": [[17, 8]]}, 322),
                   authsrv.spell_armour_for(229), authsrv.strength_banner())
            authsrv.BASE_PENETRATION = True
            check(d_power_off == want(60.0) and d_pen_horn_off == want(54.0)
                  and off == (0.0, 0.0, 0.0, 25.0, None),
                  "--no-base-penetration: Power Attack lands as on 60 and Penetrating Attack under "
                  "a hornbow as on 54 (the bonus alone, the pre-35 reading); every base reads 0, "
                  "an Orb meets the full rating, no banner", str(off))
            check(close(authsrv.body_base_penetration({"attributes": [[17, 8]]}, 322), 0.08)
                  and close(authsrv.body_base_penetration({"npc": {"attributes": [[17, 2]]}}, 322), 0.02)
                  and authsrv.body_base_penetration({}, 322) == 0.0
                  and close(authsrv.body_base_penetration({"attributes": [[17, 8]]}, 339), 0.20)
                  and authsrv.body_base_penetration({"attributes": [[17, 8]]}, 194) == 0.0
                  and close(authsrv.body_base_penetration({"attributes": [[17, 8]]}, 229), 0.25),
                  "a body's base: its own Strength 8 gives its Power Attack 8 %, a raider row's 2 "
                  "gives 2 %, no ranks 0; Penetrating Blow's 20 beats the 8; a Flare none and an "
                  "Orb the attribute's 25 whatever the ranks")
            check(authsrv.spell_armour_for(229) == 19.0 and authsrv.spell_armour_for(230) == 19.0
                  and authsrv.spell_armour_for(194) == 25.0
                  and authsrv.skill_damage(229, 12)[1] == "standalone"
                  and "Strength 9: an attack skill ignores 9 %" in (authsrv.strength_banner() or ""),
                  "an incoming Lightning Orb or Javelin resolves against the pieces' 25 as 19 "
                  "(25 x 0.75 = 18.75, up), Flare against 25 as before; the Orb's row deals its "
                  "scale standalone; the door names the Strength rank",
                  f"{authsrv.spell_armour_for(229)} / {authsrv.strength_banner()}")
        # the source locks
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check(src.count("base=player_base_penetration(state, skill_id))") == 2
              and src.count("base=body_base_penetration(agent, skill_id))") == 2
              and "return penetrated_armour(got, None, base=skill_base_penetration(skill_id))" in src
              and "_sb = strength_banner()" in src
              and '"--no-base-penetration"' in sargs,
              "the base rides every rating read: the player's hit and the scythe's extras, a body's "
              "swing on the player and on a body, the incoming spell; the door's clause; the revert "
              "flag exists")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.BASE_PENETRATION, agents.item_template, authsrv.critical_rate) = saved


def section_spell_projectiles():
    print("\n24. a player's spell projectile: the E5 launches it, the arrival lands the damage")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.skill_timing, authsrv._is_attack_skill, authsrv.skill_cost,
             authsrv.skill_projectile, authsrv.skill_damage, authsrv.skill_impact_visual,
             authsrv.skill_chain_fields, authsrv.SPELL_PROJECTILES, authsrv.RANGED_DELIVERY,
             authsrv.weapon_satisfies)
    words = lambda batch: [v for op, v in batch if op == 0x00A3 and v[0] in (16, 17)]   # noqa: E731
    launches = lambda batch: [v for op, v in batch if op == 0x00A4]                     # noqa: E731
    visuals = lambda batch: [v for op, v in batch if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]  # noqa: E731
    try:
        speeds = agents.WORLD.get("spell_projectile", "speed")
        check({k: int(v) for k, v in speeds.items()} == {"343": 1800, "403": 1800, "405": 1200, "854": 1200}
              and authsrv.spell_projectile_speed(343) == 1800.0
              and authsrv.spell_projectile_speed(854) == 1200.0
              and authsrv.spell_projectile_speed(680) is None
              and authsrv.spell_projectile_speed(2077) is None,
              "content: the four timed spell projectiles -- 343 (Flare / Fireball) and 403 (Orb) at "
              "1800 u/s, 405 (Javelin) and 854 (Daggers) at 1200; an arrow's id and the table's "
              "none have no spell speed")
        row = agents.WORLD.get("skill_effect", "858")
        check(row["scale_means"] == "Earth damage" and int(row["damage_type"]) == 11
              and int(row["projectiles"]) == 3 and abs(float(row["projectile_interval"]) - 0.333) < 1e-9
              and authsrv.spell_projectiles(858) == (3, 0.333)
              and authsrv.spell_projectiles(194) == (1, 0.0)
              and authsrv.spell_projectiles(99999) == (1, 0.0),
              "Dancing Daggers' row: earth (11), three projectiles a third of a second apart; "
              "Flare sends one, an unknown skill one")
        # the pure reader on injected rows (a bare machine has no skills table)
        tables = agents.WORLD.tables
        had, kept = "skills" in tables, tables.get("skills")
        tables["skills"] = {"194": {"projectile": 343, "impact_visual": 344, "type_code": 5},
                            "858": {"projectile": 854, "impact_visual": 855, "type_code": 5, "combo": 1},
                            "222": {"projectile": 2077, "impact_visual": 2077, "type_code": 4},
                            "394": {"projectile": 680, "impact_visual": 2077, "type_code": 14},
                            "2": {"projectile": 500, "impact_visual": 2077, "type_code": 5}}
        try:
            hows = {s: authsrv.spell_shot_how(s) for s in (194, 858, 222, 394, 2, 99999)}
            authsrv.SPELL_PROJECTILES = False
            off = authsrv.spell_shot_how(194)
            authsrv.SPELL_PROJECTILES = True
            authsrv.RANGED_DELIVERY = False
            off2 = authsrv.spell_shot_how(194)
            authsrv.RANGED_DELIVERY = True
        finally:
            if had:
                tables["skills"] = kept
            else:
                del tables["skills"]
        check(hows[194] == {"projectile": 343, "arrow": 0, "speed": 1800.0, "range": None, "damage_type": 5}
              and hows[858] == {"projectile": 854, "arrow": 0, "speed": 1200.0, "range": None, "damage_type": 11}
              and hows[222] is None and hows[394] is None and hows[2] is None and hows[99999] is None
              and off is None and off2 is None,
              "spell_shot_how: Flare flies its 343 at 1800 with flag 0 and its own fire (5) as the "
              "kind, the Daggers their 854 at 1200 as earth (11); Lightning Strike (2077), an attack "
              "skill, a projectile no tape has timed and an unknown skill fly nothing; nor does "
              "anything under --no-spell-projectiles or --no-projectiles", str(hows))

        # through the real press, E5 and arrival
        authsrv.skill_timing = lambda sid: (1.0, 0.75, 0.0)
        authsrv._is_attack_skill = lambda sid: False
        authsrv.skill_cost = lambda sid: (0, 0)
        authsrv.weapon_satisfies = lambda sid: True
        authsrv.skill_damage = lambda sid, rank: (20.0, "standalone")
        authsrv.skill_projectile = lambda sid: {194: 343, 858: 854}.get(sid)
        authsrv.skill_impact_visual = lambda sid: {194: 344, 858: 855}.get(sid)
        authsrv.skill_chain_fields = lambda sid: (1, 0, 0) if sid == 858 else (0, 0, 0)

        def press_and_e5(distance, skill):
            authsrv.apply_party_character({"player_weapon": "starter_wand"})
            st, sent = _world(distance), []
            send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
            authsrv.handle_skill_press([0, skill, 0, FOE], send, st, 1,
                                       authsrv.GAME_CMSG_USE_SKILL)
            sent.clear()
            for cast in st["pending_casts"]:
                for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                    cast[k] -= 30.0
            authsrv.cast_tick(send, st, 1)
            return st, send, sent

        st, send, at_e5 = press_and_e5(900.0, 194)
        ops = [op for op, _v in at_e5]
        launch = launches(at_e5)
        i_e5, i_58 = ops.index(0x00E5), [i for i, (op, v) in enumerate(at_e5)
                                           if op == 0x009F and v[:2] == [58, PLAYER]]
        i_a4 = ops.index(0x00A4) if 0x00A4 in ops else -1
        holds = [v for op, v in at_e5 if op == 0x009F and v[:2] == [8, PLAYER]]
        check(len(launch) == 1 and launch[0][0] == PLAYER and list(launch[0][1]) == [900.0, 0.0]
              and abs(_f(launch[0][3]) - 0.5) < 1e-6 and launch[0][4:] == [343, 1, 0]
              and i_58 and i_e5 < i_58[0] < i_a4
              and holds and ops.index(0x009F, i_a4) > i_a4
              and [h[2] for h in holds][-2:] == [0, 1],
              "Flare's E5: 0x00E5, then [58, me, 0], then ONE 0x00A4 [me, the target's position, 0, "
              "0.5 s at 1800 u/s, 343, handle 1, flag 0], then the hold pulse [8 -> 0], [8 -> 1] -- "
              "retail's one batch (Dancing Daggers, 17 of 17)", str([(hex(op), v) for op, v in at_e5]))
        shot = st["player_projectiles"][0]
        check(not words(at_e5) and not visuals(at_e5) and st["agents"][FOE]["health"] == 9000.0
              and shot["spell"] == {"skill_id": 194, "rank": shot["spell"]["rank"], "amount": 20.0,
                                    "visual": 344, "first": True}
              and shot["damage_type"] == 5 and shot["arrives_at"] in authsrv.combat_deadlines(st)
              and not st.get("player_spell_queue"),
              "and no word, no visual and no damage at the E5: the shot carries the spell's 20 and "
              "its impact 344 to the arrival, flies as fire, is a combat DEADLINE, and Flare "
              "queues nothing behind it")
        at_e5.clear()
        shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        arr = list(at_e5)
        ops = [op for op, _v in arr]
        check(ops[:3] == [0x00A7, 0x00A0, 0x00A3] and arr[0][1] == [PLAYER, 1, 5]
              and arr[1][1] == [agents.GV_EFFECT_ON_TARGET, FOE, PLAYER, 344]
              and words(arr)[0][1:3] == [FOE, PLAYER]
              and st["agents"][FOE]["health"] == 9000.0 - 20.0 and not st["player_projectiles"],
              "a flight later: 0x00A7 [me, handle 1, kind 5 -- the SPELL's fire] first, then "
              "[20, foe, me, 344] (the record's impact), then the ONE word for the spell's 20 -- "
              "the Orb's shape onto the owner (11 of 11) and the Daggers' (15 of 17); the handle "
              "is spent", str([(hex(op), v) for op, v in arr]))

        # Dancing Daggers: three projectiles, a third of a second apart, the chain on the first
        st, send, at_e5 = press_and_e5(600.0, 858)
        launch = launches(at_e5)
        queue = st.get("player_spell_queue") or []
        e5_t = launch and st["player_projectiles"][0]["arrives_at"] - 0.5
        check(len(launch) == 1 and launch[0][4:] == [854, 1, 0] and abs(_f(launch[0][3]) - 0.5) < 1e-6
              and not visuals(at_e5) and len(queue) == 2
              and all(q["spell"]["first"] is False and q["target"] == FOE for q in queue)
              and abs((queue[1]["launch_at"] - queue[0]["launch_at"]) - 0.333) < 1e-6
              and all(q["launch_at"] in authsrv.combat_deadlines(st) for q in queue),
              "the Daggers' E5 batch launches ONE 854 (0.5 s at 1200 u/s, flag 0, no visual) and "
              "queues two more a third of a second apart, each a combat deadline")
        at_e5.clear()
        for q in queue:
            q["launch_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        later = list(at_e5)
        ops = [op for op, _v in later]
        check(ops == [0x00A0, 0x00A4, 0x00A0, 0x00A4]
              and visuals(later) == [[agents.GV_EFFECT_ON_TARGET, FOE, PLAYER, 855]] * 2
              and [v[5] for v in launches(later)] == [2, 3]
              and all(v[4:] == [854, h, 0] for v, h in zip(launches(later), (2, 3)))
              and not words(later) and not st.get("player_spell_queue"),
              "the second and third dagger each leave behind a [20, foe, me, 855] (4 of 4 on the "
              "tape), handles 2 and 3, nothing landing yet", str([(hex(op), v) for op, v in later]))
        at_e5.clear()
        for s in st["player_projectiles"]:
            s["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        arr = list(at_e5)
        ops = [op for op, _v in arr]
        combos = [v for op, v in arr if op == authsrv.GAME_SMSG_AGENT_COMBO_STATE]
        i_combo = ops.index(authsrv.GAME_SMSG_AGENT_COMBO_STATE) if combos else -1
        check(ops == [0x00A7, 0x00A0, authsrv.GAME_SMSG_AGENT_COMBO_STATE, 0x00A3,
                      0x00A7, 0x00A0, 0x00A3, 0x00A7, 0x00A0, 0x00A3]
              and [v[2] for op, v in arr if op == 0x00A7] == [11, 11, 11]
              and combos == [[PLAYER, FOE, 1]] and i_combo == 2
              and len(words(arr)) == 3 and len({tuple(w) for w in words(arr)}) == 1
              and st["agents"][FOE]["health"] == 9000.0 - 60.0,
              "three arrivals, each 0x00A7 [me, handle, 11 -- earth] then [20, foe, me, 855] then "
              "the word, three words of one amount; the chain's 0x005C [me, foe, lead] rides the "
              "FIRST landing between its visual and its word and no other (5 of 5)",
              str([(hex(op), v) for op, v in arr]))

        # the revert: the E5 lands the damage with nothing in the air
        authsrv.SPELL_PROJECTILES = False
        st, send, at_e5 = press_and_e5(900.0, 194)
        authsrv.SPELL_PROJECTILES = True
        check(not launches(at_e5) and len(words(at_e5)) == 1
              and st["agents"][FOE]["health"] == 9000.0 - 20.0 and not st.get("player_projectiles"),
              "--no-spell-projectiles: Flare's word rides the E5 batch and nothing flies -- the "
              "reading every run before 2026-09-20 made")
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check('if shot.get("spell") is not None:' in src
              and "spell_queue_tick(send, state, conn_id)" in src
              and "launch_player_spell_shot(" in src
              and 'out.append(q["launch_at"])' in src
              and '"--no-spell-projectiles"' in sargs,
              "the source: the arrival lands a spell's shot, the tick sends the queue, the E5 "
              "launches, a queued launch is a deadline, the revert flag exists")
        # the tapes: the speeds the table carries, re-derived
        try:
            sys.path.insert(0, HERE)
            import weaponcensus as wc                                     # noqa: PLC0415
            got = collections.defaultdict(list)
            for stamp in ("20260819T132414", "20260917T090355", "20260917T224104",
                          "20260817T231139"):
                for _name, _gf, s2c in wc.connections(stamp):
                    for r in wc.spell_speeds(s2c):
                        if r["speed"] is not None and r["distance"] >= 50.0:
                            got[r["projectile"]].append(round(r["speed"]))
        except (Exception, SystemExit) as e:                               # noqa: BLE001
            got = None
            LEDGER.skip("section 24", f"the four tapes are absent ({type(e).__name__}) -- 1 check")
        if got is not None:
            want = {343: 1800, 403: 1800, 405: 1200, 854: 1200}
            exact = {p: sum(1 for s in got.get(p, []) if abs(s - w) <= 0.02 * w)
                     for p, w in want.items()}
            n = {p: len(got.get(p, [])) for p in want}
            check(exact[854] == n[854] >= 2 and exact[403] == n[403] >= 10
                  and exact[405] == n[405] >= 8 and exact[343] >= 15
                  and exact[343] >= 0.7 * n[343],
                  "and the tapes say so, through the extractor: every positioned Dancing Daggers "
                  "launch (at least two), every Orb (at least ten) and every Javelin (at least "
                  "eight) flies within 2 % of the table's speed, and Fireball's does on at least "
                  "fifteen and seven in ten (the rest are walking casters' stale positions)",
                  f"exact {exact} of {n}")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.skill_timing, authsrv._is_attack_skill, authsrv.skill_cost,
         authsrv.skill_projectile, authsrv.skill_damage, authsrv.skill_impact_visual,
         authsrv.skill_chain_fields, authsrv.SPELL_PROJECTILES, authsrv.RANGED_DELIVERY,
         authsrv.weapon_satisfies) = saved


def section_body_spell_projectiles():
    print("\n25. a body's spell projectile: the completion launches it, the arrival lands it")
    saved = (authsrv.skill_damage, authsrv._is_attack_skill, authsrv.skill_projectile,
             authsrv.skill_impact_visual, authsrv.SPELL_PROJECTILES)
    words = lambda batch: [v for op, v in batch if op == 0x00A3 and v[0] in (16, 17)]   # noqa: E731
    launches = lambda batch: [v for op, v in batch if op == 0x00A4]                     # noqa: E731
    visuals = lambda batch: [v for op, v in batch if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]  # noqa: E731
    try:
        authsrv._is_attack_skill = lambda sid: False
        authsrv.skill_damage = lambda sid, rank: (60.0, "standalone")
        authsrv.skill_projectile = lambda sid: {229: 403, 858: 854}.get(sid)
        authsrv.skill_impact_visual = lambda sid: {229: 404, 858: 855}.get(sid)

        def cast(distance, skill):
            st = _body_world((float(distance), 0.0), skills=[[skill, 0.0, 5.0]],
                             skill_ready=[0.0], casting=0, cast_target=PLAYER)
            sent = []
            send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
            health = st["player_health"]
            authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
            return st, send, sent, health

        st, send, sent, health = cast(900.0, 229)
        ops = [op for op, _v in sent]
        launch = launches(sent)
        check(sent and sent[0][1][:2] == [58, FOE] and len(launch) == 1 and launch[0][0] == FOE
              and list(launch[0][1]) == [0.0, 0.0] and abs(_f(launch[0][3]) - 0.5) < 1e-6
              and launch[0][4:] == [403, 1, 0] and not words(sent) and not visuals(sent)
              and st["player_health"] == health and st["agents"][FOE]["casting"] is None
              and st["body_projectiles"][0]["spell"]["amount"] == 60.0
              and st["body_projectiles"][0]["damage_type"] == 4
              and st["body_projectiles"][0]["arrives_at"] in authsrv.combat_deadlines(st)
              and not st.get("body_spell_queue"),
              "a hostile's Lightning Orb completes: [58, it, 0] first, then ONE 0x00A4 [it, the "
              "player's position, 0, 0.5 s at 1800 u/s, 403, handle 1, flag 0] -- no word, no "
              "visual, no damage yet; the caster is released; the shot carries the spell's 60 and "
              "flies as lightning (4), a combat deadline", str([(hex(op), v) for op, v in sent]))
        sent.clear()
        st["body_projectiles"][0]["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        arr = list(sent)
        ops = [op for op, _v in arr if op != authsrv.AGENT_ADRENALINE_GAIN]   # the gain precedes the word (SKILLS-AD2)
        ar = authsrv.spell_armour_for(229)
        want = authsrv._whole_points(60.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar))
        check(ops[:3] == [0x00A7, 0x00A0, 0x00A3] and arr[0][1] == [FOE, 1, 4]
              and arr[1][1] == [agents.GV_EFFECT_ON_TARGET, PLAYER, FOE, 404]
              and words(arr)[0][1:3] == [PLAYER, FOE] and ar == 19.0
              and st["player_health"] == health - want and want > 0 and not st["body_projectiles"],
              "a flight later: 0x00A7 [it, 1, 4 -- the Orb's lightning] first, then [20, me, it, "
              "404] (the record's impact), then the word -- the Master of Lightning's shape onto the "
              "owner (11 of 11); the amount is the spell's 60 against the pieces' 19 (the 25 % came "
              "off, section 35) at the caster's strike level, computed at the arrival",
              f"{[(hex(op), v) for op, v in arr]} want {want}")

        # a body's Dancing Daggers: three, a third of a second apart, each behind its visual
        st, send, sent, health = cast(600.0, 858)
        launch = launches(sent)
        queue = st.get("body_spell_queue") or []
        check(len(launch) == 1 and launch[0][4:] == [854, 1, 0] and abs(_f(launch[0][3]) - 0.5) < 1e-6
              and not visuals(sent) and len(queue) == 2
              and all(q["shooter"] == FOE and q["target"] == PLAYER and q["spell"]["first"] is False
                      for q in queue)
              and abs((queue[1]["launch_at"] - queue[0]["launch_at"]) - 0.333) < 1e-6
              and all(q["launch_at"] in authsrv.combat_deadlines(st) for q in queue),
              "a body's Daggers complete with ONE 854 (0.5 s at 1200, flag 0) and two queued a "
              "third of a second apart, each a combat deadline")
        sent.clear()
        for q in queue:
            q["launch_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        later = list(sent)
        check([op for op, _v in later] == [0x00A0, 0x00A4, 0x00A0, 0x00A4]
              and visuals(later) == [[agents.GV_EFFECT_ON_TARGET, PLAYER, FOE, 855]] * 2
              and [v[5] for v in launches(later)] == [2, 3] and not words(later)
              and not st.get("body_spell_queue"),
              "the second and third leave behind their [20, me, it, 855] with handles 2 and 3 "
              "(the player's shape, section 36; no body cast one on any tape)",
              str([(hex(op), v) for op, v in later]))
        sent.clear()
        for s in st["body_projectiles"]:
            s["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        arr = list(sent)
        ar858 = authsrv.spell_armour_for(858)
        want858 = authsrv._whole_points(60.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar858))
        check([op for op, _v in arr if op != authsrv.AGENT_ADRENALINE_GAIN] == [0x00A7, 0x00A0, 0x00A3] * 3
              and [v[2] for op, v in arr if op == 0x00A7] == [11, 11, 11]
              and len(words(arr)) == 3 and len({tuple(w) for w in words(arr)}) == 1
              and ar858 == 25.0 and st["player_health"] == health - 3 * want858,
              "three arrivals, each 0x00A7 [it, h, 11 -- earth] / [20, me, it, 855] / the word, "
              "three words of one amount against the pieces' 25 (earth respects armour, no "
              "penetration)", f"{[(hex(op), v) for op, v in arr]} want {want858}")

        # a target dead in flight: the 0x00A7 and nothing else
        st, send, sent, health = cast(900.0, 229)
        sent.clear()
        st["player_dead"] = True
        st["body_projectiles"][0]["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        check([op for op, _v in sent] == [0x00A7] and st["player_health"] == health,
              "an Orb whose target died in flight is CLOSED and lands nothing")

        # the revert, and the control
        authsrv.SPELL_PROJECTILES = False
        st, send, sent, health = cast(900.0, 229)
        authsrv.SPELL_PROJECTILES = True
        check(not launches(sent) and len(words(sent)) == 1 and sent[0][1][:2] == [58, FOE]
              and st["player_health"] < health and not st.get("body_projectiles"),
              "--no-spell-projectiles: the body's completion lands the word behind its 58 with "
              "nothing in the air -- the reading every run before 2026-09-20 made")
        st, send, sent, health = cast(900.0, 185)
        check(not launches(sent) and len(words(sent)) == 1 and st["player_health"] < health,
              "the control: Mind Burn (no projectile of its own) lands at the completion as ever")
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        check('if shot.get("spell") is not None:                      # studies/weapons 37' in src
              and "body_spell_queue_tick(send, state, conn_id)" in src
              and "launch_body_spell_shot(send, state, conn_id, agent_id, agent, _tid," in src
              and 'out.append(q["launch_at"])' in src
              and src.count("body_spell_terms(") >= 3 and src.count("body_spell_word(") >= 3,
              "the source: the tick lands a body's spell shot and sends its queue, the completion "
              "launches, a queued launch is a deadline, the terms and the word are shared between "
              "the completion and the arrival")
        # the tapes: a body's launch sits at the client's own activation
        try:
            sys.path.insert(0, HERE)
            import weaponcensus as wc                                     # noqa: PLC0415
            at = collections.defaultdict(list)
            for _name, _gf, s2c in wc.connections("20260917T090355"):
                for r in wc.skill_shots(s2c):
                    if r["skill"] in (229, 230) and r["event"] == "announce60":
                        at[r["skill"]].append(r["event_to_launch"])
        except (Exception, SystemExit) as e:                               # noqa: BLE001
            at = None
            LEDGER.skip("section 25", f"capture 20260917T090355 is absent ({type(e).__name__}) -- 1 check")
        if at is not None:
            check(len(at[229]) >= 10 and all(abs(x - 2.0) <= 0.05 for x in at[229])
                  and len(at[230]) >= 8 and all(abs(x - 1.0) <= 0.05 for x in at[230]),
                  "and the tape says so: every Lightning Orb launch on 20260917T090355 (at least "
                  "ten) leaves 2.0 s after its announce and every Javelin (at least eight) 1.0 s "
                  "-- the client's own activations, the completion instant", str(dict(at)))
    finally:
        (authsrv.skill_damage, authsrv._is_attack_skill, authsrv.skill_projectile,
         authsrv.skill_impact_visual, authsrv.SPELL_PROJECTILES) = saved


def section_spell_areas():
    print("\n26. Fireball's splash: a burst at the aim -- the explosion, then a word and an impact per foe")
    saved = (authsrv.skill_damage, authsrv._is_attack_skill, authsrv.skill_projectile,
             authsrv.skill_impact_visual, authsrv.SPELL_AREAS, authsrv.skill_timing,
             authsrv.skill_cost, authsrv.weapon_satisfies, agents.PLAYER_WEAPON,
             agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL, authsrv.WEAPON_ATTACK_SPEED,
             authsrv.PLAYER_SWING_DAMAGE)
    A1 = authsrv.GAME_SMSG_EFFECT_AT_POINT
    words = lambda batch: [v for op, v in batch if op == 0x00A3 and v[0] in (16, 17)]   # noqa: E731
    launches = lambda batch: [v for op, v in batch if op == 0x00A4]                     # noqa: E731
    visuals = lambda batch: [v for op, v in batch if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]  # noqa: E731
    grounds = lambda batch: [v for op, v in batch if op == A1]                          # noqa: E731
    tables = agents.WORLD.tables
    had, kept = "skills" in tables, tables.get("skills")
    # Fireball's record row in full (skilltable.py, build 38797), so the press path
    # reads it on a bare machine too; Flare's and the Orb's the columns the readers need
    tables["skills"] = {"186": {"activation": 1.5, "aftercast": 0.75, "recharge": 7, "energy": 10,
                                "adrenaline": 0, "adrenaline_units": 0, "attribute": 10,
                                "profession": 6, "type_code": 5, "target": 16, "combo": 0,
                                "combo_req": 0, "weapon_req": 0, "aoe_range": 240.0,
                                "skill_arguments": 2, "duration0": 0, "duration15": 0,
                                "scale0": 7, "scale15": 112, "bonus_scale0": 1800,
                                "bonus_scale15": 1800, "projectile": 343, "impact_visual": 344},
                        "194": {"target": 5, "aoe_range": 156.0, "projectile": 343,
                                "impact_visual": 344, "type_code": 5, "attribute": 10},
                        "229": {"target": 5, "aoe_range": 0.0, "projectile": 403,
                                "impact_visual": 404, "type_code": 5, "attribute": 8}}
    try:
        row = agents.WORLD.get("skill_effect", "186")
        check(row["scale_means"] == "Fire damage" and int(row["damage_type"]) == 5
              and int(row["area_visual"]) == 333 and authsrv.spell_area_visual(186) == 333
              and authsrv.spell_area_visual(194) is None
              and authsrv.spell_area(186) == 240.0 and authsrv.spell_area(194) is None
              and authsrv.spell_area(229) is None and authsrv.spell_area(99999) is None
              and authsrv.AREA_TARGET_BYTE == 16 and authsrv.GAME_SMSG_EFFECT_AT_POINT == 0x00A1,
              "content and the reader: Fireball's row (fire, the explosion 333) and its record "
              "(target byte 16, 240 u) make it a burst over 240; Flare (byte 5, its Overcast 156) "
              "and the Orb are one target; an unknown skill too")
        authsrv.SPELL_AREAS = False
        off = authsrv.spell_area(186)
        authsrv.SPELL_AREAS = True
        st = _body_world((900.0, 0.0))
        st["agents"][300] = dict(st["agents"][HERO], pos=(0.0, 400.0))      # a far party body
        st["agents"][11] = dict(st["agents"][FOE], pos=(950.0, 0.0))        # a hostile beside the caster
        st["agents"][12] = dict(st["agents"][FOE], pos=(1300.0, 0.0))       # a far hostile
        st["agents"][13] = dict(st["agents"][FOE], pos=(920.0, 0.0), dead=True)
        near = authsrv.foes_within(st, FOE, (0.0, 0.0), 240.0)
        mine = authsrv.foes_within(st, PLAYER, (900.0, 0.0), 240.0)
        heros = authsrv.foes_within(st, HERO, (900.0, 0.0), 240.0)
        st["player_dead"] = True
        dead = authsrv.foes_within(st, FOE, (0.0, 0.0), 240.0)
        st["player_dead"] = False
        check(off is None and near == [PLAYER, HERO] and mine == [FOE, 11] and heros == [FOE, 11]
              and dead == [HERO],
              "foes_within: a hostile's burst at the origin reaches the player and the monk 110 u "
              "off, not the body 400 u off; the player's or the monk's burst at the archer reaches "
              "it and the hostile 50 u beside it, not the one 400 u off nor the dead one, never the "
              "caster; a dead player is not reached; --no-spell-areas makes every spell one target",
              f"{near} / {mine} / {heros} / {dead}")

        # a hostile's Fireball at the player, the monk 110 u off
        authsrv._is_attack_skill = lambda sid: False
        authsrv.skill_damage = lambda sid, rank: (60.0, "standalone")
        authsrv.skill_projectile = lambda sid: 343
        authsrv.skill_impact_visual = lambda sid: 344
        st = _body_world((900.0, 0.0), skills=[[186, 0.0, 7.0]], skill_ready=[0.0],
                         casting=0, cast_target=PLAYER)
        st["agents"][300] = dict(st["agents"][HERO], pos=(0.0, 400.0))
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        health, monk_hp = st["player_health"], st["agents"][HERO]["health"]
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        launch = launches(sent)
        check(len(launch) == 1 and launch[0][4:] == [343, 1, 0] and not words(sent)
              and st["body_projectiles"][0]["aim"] == (0.0, 0.0),
              "the completion launches the 343 at the player's position, the aim the shot "
              "remembers")
        sent.clear()
        st["body_projectiles"][0]["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        arr = [(op, v) for op, v in sent if op != authsrv.AGENT_ADRENALINE_GAIN]
        ops = [op for op, _v in arr]
        ar = authsrv.spell_armour_for(186)
        want_me = authsrv._whole_points(60.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar))
        check(ops[:3] == [0x00A7, 0x00A0, A1] and arr[0][1] == [FOE, 1, 5]
              and arr[1][1] == [agents.GV_EFFECT_ON_TARGET, PLAYER, FOE, 344]
              and arr[2][1] == [[0.0, 0.0], 0, 0, 333, 0, 0]
              and ops[3:] == [0x00A3, 0x00A0, 0x00A3, 0x00A0]
              and [w[1] for w in words(arr)] == [PLAYER, HERO]
              and visuals(arr)[1:] == [[agents.GV_EFFECT_ON_TARGET, PLAYER, FOE, 344],
                                       [agents.GV_EFFECT_ON_TARGET, HERO, FOE, 344]]
              and st["player_health"] == health - want_me and st["agents"][HERO]["health"] < monk_hp
              and st["agents"][300]["health"] == monk_hp and not grounds(arr)[1:],
              "the burst: 0x00A7 [it, 1, 5], the impact ON the player (inside the area), the "
              "explosion 0x00A1 [aim, 0, 0, 333, 0, 0], then the player's word and [20, me, it, "
              "344], then the monk's word and its [20] -- word first per foe, each its own number; "
              "the body 400 u off untouched", str([(hex(op), v) for op, v in arr]))

        # the target ran: the impact on the ground, the monk alone in the area
        st = _body_world((900.0, 0.0), skills=[[186, 0.0, 7.0]], skill_ready=[0.0],
                         casting=0, cast_target=PLAYER)
        sent.clear()
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        sent.clear()
        st["pos"] = (0.0, -600.0)
        health = st["player_health"]
        st["body_projectiles"][0]["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        arr = [(op, v) for op, v in sent if op != authsrv.AGENT_ADRENALINE_GAIN]
        check([op for op, _v in arr] == [0x00A7, A1, A1, 0x00A3, 0x00A0]
              and grounds(arr) == [[[0.0, 0.0], 0, FOE, 344, 0, 0], [[0.0, 0.0], 0, 0, 333, 0, 0]]
              and words(arr)[0][1] == HERO and st["player_health"] == health,
              "the player 600 u from the aim: the impact 344 on the GROUND at the aim with the "
              "caster's id (the tape's 21 of 35), the explosion, and only the monk's word and "
              "visual -- the player takes nothing", str([(hex(op), v) for op, v in arr]))

        # the player's Fireball at a hostile with a second one 50 u beside it
        authsrv.skill_timing = lambda sid: (1.5, 0.75, 0.0)
        authsrv.skill_cost = lambda sid: (0, 0)
        authsrv.weapon_satisfies = lambda sid: True
        authsrv.apply_party_character({"player_weapon": "starter_wand"})
        st, sent = _world(600.0), []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        st["agents"][11] = dict(st["agents"][FOE], pos=(650.0, 0.0))
        st["agents"][12] = dict(st["agents"][FOE], pos=(1000.0, 0.0))
        authsrv.handle_skill_press([0, 186, 0, FOE], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
        sent.clear()
        for cast in st["pending_casts"]:
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        authsrv.cast_tick(send, st, 1)
        launch = launches(sent)
        check(len(launch) == 1 and launch[0][4:] == [343, 1, 0]
              and st["player_projectiles"][0]["aim"] == (600.0, 0.0) and not words(sent),
              "the player's Fireball leaves at the E5 with its aim remembered")
        sent.clear()
        st["player_projectiles"][0]["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        arr = list(sent)
        ops = [op for op, _v in arr]
        check(ops[:3] == [0x00A7, 0x00A0, A1] and arr[0][1] == [PLAYER, 1, 5]
              and arr[1][1] == [agents.GV_EFFECT_ON_TARGET, FOE, PLAYER, 344]
              and arr[2][1] == [[600.0, 0.0], 0, 0, 333, 0, 0]
              and [w[1] for w in words(arr)] == [FOE, 11]
              and visuals(arr)[1:] == [[agents.GV_EFFECT_ON_TARGET, FOE, PLAYER, 344],
                                       [agents.GV_EFFECT_ON_TARGET, 11, PLAYER, 344]]
              and st["agents"][FOE]["health"] == 9000.0 - 60.0
              and st["agents"][11]["health"] == 9000.0 - 60.0
              and st["agents"][12]["health"] == 9000.0,
              "the player's burst: 0x00A7 [me, 1, 5], the impact on the target, the explosion at "
              "the aim, then a word and a [20] for the target and for the hostile 50 u beside it, "
              "60 each (the spell's own, exact); the one 400 u off untouched",
              str([(hex(op), v) for op, v in arr]))

        # the revert: one target, no explosion
        authsrv.SPELL_AREAS = False
        st = _body_world((900.0, 0.0), skills=[[186, 0.0, 7.0]], skill_ready=[0.0],
                         casting=0, cast_target=PLAYER)
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        sent.clear()
        st["body_projectiles"][0]["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
        authsrv.SPELL_AREAS = True
        arr = [(op, v) for op, v in sent if op != authsrv.AGENT_ADRENALINE_GAIN]
        check([op for op, _v in arr] == [0x00A7, 0x00A0, 0x00A3] and not grounds(arr)
              and [w[1] for w in words(arr)] == [PLAYER] and st["agents"][HERO]["health"] == 100.0,
              "--no-spell-areas: the Orb's single-target shape -- the impact, one word, no "
              "explosion, the monk untouched")
        src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
        sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
        check("return land_player_spell_area(send, state, conn_id, shot, radius)" in src
              and "return land_body_spell_area(send, state, conn_id, shot, agent, radius)" in src
              and src.count('"aim": (') == 2 and '"--no-spell-areas"' in sargs,
              "the source: both landings branch to the area on a burst spell, both launchers "
              "remember the aim, the revert flag exists")
        # the tape: every Fireball arrival explodes at its aim
        try:
            sys.path.insert(0, HERE)
            import weaponcensus as wc                                     # noqa: PLC0415
            n_arr, n_333, n_ground, n_direct, per_foe_ok = 0, 0, 0, 0, 0
            for _name, _gf, s2c in wc.connections("20260817T231139"):
                for i, (tt, op, v) in enumerate(s2c):
                    if op != 0x00A7 or len(v) < 4 or v[3] != 5:
                        continue
                    batch = [(o, w) for (t2, o, w) in s2c[i:i + 60] if abs(t2 - tt) < 0.001]
                    g = [w for o, w in batch if o == 0x00A1]
                    if not any(w[4] == 333 and w[3] == 0 for w in g):
                        continue                    # not a Fireball burst
                    n_arr += 1
                    n_333 += 1
                    if any(w[4] == 344 and w[3] == v[1] for w in g):
                        n_ground += 1
                    else:
                        n_direct += 1
                    ws = [w[2] for o, w in batch if o == 0x00A3 and w[1] in (16, 17) and w[3] == v[1]]
                    vs = [w[2] for o, w in batch if o == 0x00A0 and w[1] == 20 and w[3] == v[1]]
                    if ws and all(f in vs for f in ws):
                        per_foe_ok += 1
        except (Exception, SystemExit) as e:                               # noqa: BLE001
            n_arr = None
            LEDGER.skip("section 26", f"capture 20260817T231139 is absent ({type(e).__name__}) -- 1 check")
        if n_arr is not None:
            check(n_arr >= 30 and n_333 == n_arr and n_ground + n_direct == n_arr
                  and n_ground >= 15 and n_direct >= 10 and per_foe_ok == n_arr,
                  "and the tape says so: every fire arrival with an explosion (at least thirty) "
                  "draws the 333 at the aim with no agent, the impact 344 on the ground with the "
                  "caster's id on some (at least fifteen) and on the target on others (at least "
                  "ten), and every foe worded gets its [20, foe, caster, 344]",
                  f"arrivals {n_arr}, 333 {n_333}, ground {n_ground}, direct {n_direct}, "
                  f"per-foe {per_foe_ok}")
    finally:
        if had:
            tables["skills"] = kept
        else:
            del tables["skills"]
        (authsrv.skill_damage, authsrv._is_attack_skill, authsrv.skill_projectile,
         authsrv.skill_impact_visual, authsrv.SPELL_AREAS, authsrv.skill_timing,
         authsrv.skill_cost, authsrv.weapon_satisfies, agents.PLAYER_WEAPON,
         agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL, authsrv.WEAPON_ATTACK_SPEED,
         authsrv.PLAYER_SWING_DAMAGE) = saved


def main():
    section_table()
    section_skills()
    section_items()
    section_character()
    section_ranged()
    section_bodies()
    section_skill_shots()
    section_approach()
    section_weapon_energy()
    section_caster_level()
    section_dual_shot()
    section_preparation_wire()
    section_body_parity()
    section_splash()
    section_spear()
    section_scythe()
    section_customisation()
    section_weapon_sets()
    section_damage_type_and_requirement()
    section_half_recharge()
    section_bow_classes()
    section_spell_own_type()
    section_base_penetration()
    section_spell_projectiles()
    section_body_spell_projectiles()
    section_spell_areas()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
