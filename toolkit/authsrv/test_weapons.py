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

LEDGER = checks.Ledger("weapons: one table, a row and an item per type", floor=43)   # the BARE-MACHINE number: 43 without the vault's full skills table (section 2 skips), 44 with it; from green runs
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


def main():
    section_table()
    section_skills()
    section_items()
    section_character()
    section_ranged()
    section_bodies()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
