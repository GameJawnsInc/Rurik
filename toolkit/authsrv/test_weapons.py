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

LEDGER = checks.Ledger("weapons: one table, a row and an item per type", floor=84)   # the BARE-MACHINE number: 84 without the vault's full skills table (section 2 skips), 85 with it; from green runs (WEAPONS-W2c: 43 -> 59; W2b: 59 -> 66; W5: 66 -> 74; W4c: 74 -> 84)
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
        check(hows["starter_spear"] is None and hows["starter_sword"] is None
              and hows["starter_scythe"] is None,
              "a sword and a scythe swing; the SPEAR stays on the melee path until a tape "
              "names its projectile (n = 0) -- no mechanism ahead of its wire shape")
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
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
