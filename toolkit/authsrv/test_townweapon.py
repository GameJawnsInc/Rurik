"""The TOWN WEAPON -- in an outpost the player's WORLD body carries no weapon: the
hands (0x006E / 0x006F visuals 0 and 1) leave the town body's array and a town's
hand 0x006F is never sent, while the equipped BAG (the paper doll, the weapon-set
panel) keeps the weapon (DESKWORK-D1, the town weapon, 2026-09-23;
studies/cmsg/FINDINGS.md "The town weapon"; townweapon.py's docstring for the
census).

    python toolkit/authsrv/test_townweapon.py

  * §1 THE LEAF (bare-machine): the two hand slots; hands_shown per regime;
    strip_hands in a town (both hands, a lead alone, a short array) and a field
    (untouched) with a VACUITY guard (empty hands report nothing) and a KNOWN-BAD
    (the unstripped town array disagrees); drops / filter_hand_writes (the hands
    dropped in a town, an emptied hand's zero too, armour and a field untouched,
    order kept).
  * §2 RETAIL'S WIRE (vault-gated; LEDGER.skip on a bare machine, ~10 s): over
    every origin=LIVE game connection -- every outpost 0x006E empty-handed on
    BOTH visuals (>= 2,000 bodies; the OWN body, the 0x006E whose armour ids all
    sit in ONE type-2 bag, on >= 40 outpost loads with a lead in that bag and
    >= 15 with an off hand); the own FIELD body carrying every hand its bag
    holds (>= 30 leads, >= 15 off hands, no miss) and none when the bag has none;
    no outpost 0x006F into slot 0 or 1 on ANY agent, the own outpost 0x006F that
    does exist going to an ARMOUR slot (the PvP panel's head); every outpost
    c2s 0x0032 switch answered with 0x0148 and no 0x006F, every field switch
    with a hand 0x006F; the outpost 0x0030 equips and 0x004F move with none;
    the PvP panel's hand placements with none and its armour placement with one;
    retail's outpost NPCs DO carry 0x006D weapons (the rule is the player's
    hands); no hero body in an outpost (party heroes never created), a hero body
    in a field; every connection decoded.
  * §3 THE SERVER: source locks (the leaf imported; the flag in serverargs.py
    and main(); visible_worn and visible_slot_writes gated; select_weapon_set's
    three hand 0x006F built into a batch that passes visible_slot_writes and no
    direct send left -- the ONE gate; the only direct player 0x006F sender left
    is handle_visibility_flags, whose slots are the display mode's 6/7/8); the
    real item layout in a TOWN: the dressed array keeps the hammer at visual 0
    (the doll) while visible_worn zeroes 0 and 1; the FIELD control; the
    KNOWN-BAD revert arm (the weapon kept in a town, and it disagrees); VACUITY
    (empty hands); F2/F1 (--weapon-set 1=sword+shield) in a TOWN -- 0x0148 +
    0x014B + 0x0152 and NO 0x006F, the bag and the doll's array swapped -- and
    in a FIELD -- the same rows plus the two hand 0x006F in retail's order; the
    revert arm's town F2 carrying them (KNOWN-BAD); the equip path (0x004F out,
    0x0030 back) in a town with no 0x006F and in a field with them; the
    composition with the display mode (Hide in Towns helm + the town: 0, 1 and
    6 zeroed; each flag alone zeroes its own slots); visible_slot_writes leaving
    another agent's hand and the player's armour slot alone in a town, dropping
    the player's hand under either display-mode setting, and passing the batch
    whole with both flags off.
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import townweapon as tw                                      # noqa: E402
import itemstore                                             # noqa: E402
import authsrv                                               # noqa: E402

led = checks.Ledger("the town weapon (DESKWORK-D1)", floor=35)  # 2026-09-23, from the green run with RURIK_VAULT pointed at an empty directory (the bare-machine core, 1 declared skip); section 2's 11 ride the vault (46 vaulted)

VIS = authsrv.GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT           # 0x006F
WORN = authsrv.GAME_SMSG_UPDATE_AGENT_VISUAL_EQUIPMENT               # 0x006E
CHG, SWAP, ACTIVE = (authsrv.GAME_SMSG_ITEM_CHANGE_LOCATION, authsrv.GAME_SMSG_ITEM_SWAP_LOCATIONS,
                     authsrv.GAME_SMSG_ITEM_SET_ACTIVE_WEAPON_SET)   # 0x014B, 0x0152, 0x0148
P = authsrv.PLAYER_AGENT_ID
UUID = "66666666666666666666666666666666"


def fake_send_factory():
    sent = []

    def send(op, vals, label=None, **_k):
        sent.append((op, list(vals)))
    return sent, send


# ---- §1 the leaf -----------------------------------------------------------------------
led.ok(tw.HAND_SLOTS == (0, 1) and tw.HAND_LEAD == 0 and tw.HAND_OFF == 1
       and tw.HAND_NAMES == {0: "lead hand", 1: "off hand"},
       "the hands are visuals 0 (lead) and 1 (off) -- weaponcensus.py's slot reading")
led.ok(tw.hands_shown(True) is True and tw.hands_shown(False) is False,
       "hands_shown: a field shows the hands, a town does not")
worn = [1, 12, 3, 4, 5, 6, 7, 8, 9]
out, hid = tw.strip_hands(worn, False)
outf, hidf = tw.strip_hands(worn, True)
led.ok(out == [0, 0, 3, 4, 5, 6, 7, 8, 9] and hid == [(0, 1), (1, 12)] and outf == worn and hidf == []
       and worn == [1, 12, 3, 4, 5, 6, 7, 8, 9],
       "strip_hands: a town zeroes visuals 0 and 1 and names both items; a field is untouched; the "
       "input is not mutated", f"{out} {hid} / {outf} {hidf}")
out, hid = tw.strip_hands([1, 0, 3, 4, 5, 6, 7, 0, 0], False)
led.ok(out == [0, 0, 3, 4, 5, 6, 7, 0, 0] and hid == [(0, 1)],
       "a lead alone: visual 0 zeroed, the empty off hand not reported")
led.ok(tw.strip_hands([5], False) == ([0], [(0, 5)]) and tw.strip_hands([], False) == ([], []),
       "a short array: only the positions that exist are touched")
led.ok(tw.strip_hands([0, 0, 3, 4, 5, 6, 7, 0, 0], False) == ([0, 0, 3, 4, 5, 6, 7, 0, 0], []),
       "VACUITY: a town body whose hands are already empty reports nothing hidden")
led.ok(list(worn) != tw.strip_hands(worn, False)[0] and list(worn) == tw.strip_hands(worn, True)[0],
       "KNOWN-BAD: the unstripped array (every run before this day) disagrees with the town strip "
       "and agrees with the field's -- the pin can tell the arms apart")
led.ok(tw.drops(0, False) and tw.drops(1, False) and not tw.drops(6, False) and not tw.drops(2, False)
       and not tw.drops(0, True) and not tw.drops(1, True),
       "drops: the hands in a town; never an armour slot (the town's own-body 0x006F was the head's); "
       "nothing in a field")
led.ok(tw.filter_hand_writes([(0, 11), (6, 7), (1, 12)], False) == ([(6, 7)], [(0, 11), (1, 12)])
       and tw.filter_hand_writes([(0, 11), (6, 7), (1, 12)], True) == ([(0, 11), (6, 7), (1, 12)], []),
       "filter_hand_writes: a town drops the two hand writes and keeps the head's in order; a field "
       "keeps all three")
led.ok(tw.filter_hand_writes([(1, 0)], False) == ([], [(1, 0)]) and tw.filter_hand_writes([(1, 0)], True) == ([(1, 0)], []),
       "an emptied hand's zero is dropped in a town too (retail's outpost off-hand unequip carried no "
       "0x006F) and kept in a field (the tape's [25, 1, 0])")
led.ok(tw.filter_hand_writes([], False) == ([], []), "CONTROL: an empty batch stays empty")

# ---- §2 retail's wire ------------------------------------------------------------------
import vaultpath                                             # noqa: E402
import livewire                                              # noqa: E402
live_root = vaultpath.vault_path("captures", "live")
conns = list(livewire.live_connections()) if os.path.isdir(live_root) else []
if not conns:
    led.skip("section 2, retail's wire", f"no live captures under {live_root}")
if conns:
    R = {0: "outpost", 1: "field"}
    decoded = 0
    bodies = collections.Counter()      # (regime, own?, v0 != 0, v1 != 0)
    own_bag = collections.Counter()     # (regime, bag lead?, bag off?, v0 != 0, v1 != 0)
    slot6f = collections.Counter()      # (regime, own?, slot, item != 0)
    switches = collections.Counter()    # (regime, has 0x0148, has hand 0x006F)
    equips = collections.Counter()      # (regime, c2s op, has hand 0x006F)
    pvp = collections.Counter()         # (placed slot kind, has 0x006F, 0x006F slots all armour?)
    npc6d = collections.Counter()       # (regime, lead != 0)
    heroes = collections.Counter()      # (regime, created?, has 0x006D?)
    for capdir, gf in conns:
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        decoded += 1 if ok else 0
        s2c = [(t, op, v) for (t, d, op, v) in merged if d == "s2c"]
        c2s = [(t, op, v) for (t, d, op, v) in merged if d == "c2s"]
        regime = next((int(v[3]) for _t, op, v in s2c if op == 0x0199 and len(v) > 3), None)
        if regime not in R:
            continue
        rg = R[regime]
        type2, cells, own_ids, own_bag_id = set(), {}, set(), None
        hero_agents, created, d6 = set(), set(), {}
        for t, op, v in s2c:
            if op == 0x013F and int(v[2]) == 2:
                type2.add(int(v[4]))
            elif op in (0x013E, 0x014B):
                cells[int(v[2])] = (int(v[3]), int(v[4]))
            elif op == 0x0152:
                a, b = cells.get(int(v[2])), cells.get(int(v[3]))
                if a and b:
                    cells[int(v[2])], cells[int(v[3])] = b, a
            elif op == 0x01C2 and len(v) > 3:
                hero_agents.add(int(v[3]))
            elif op in (0x0020, 0x0021) and len(v) > 1:
                created.add(int(v[1]))
            elif op == 0x006D and len(v) > 3:
                d6[int(v[1])] = (int(v[2]), int(v[3]))
                npc6d[(rg, int(v[2]) != 0)] += 1
            elif op == WORN and len(v) > 10:
                armour = [int(x) for x in v[4:8] if int(x)]
                bags = {cells[a][0] for a in armour if a in cells}
                is_own = bool(armour) and len(bags) == 1 and bags <= type2
                if is_own:
                    own_ids.add(int(v[1]))
                    own_bag_id = next(iter(bags))
                own = is_own or int(v[1]) in own_ids
                bodies[(rg, own, int(v[2]) != 0, int(v[3]) != 0)] += 1
                if own and own_bag_id is not None:
                    mine = {i: s for i, (b, s) in cells.items() if b == own_bag_id}
                    own_bag[(rg, any(s == 0 for s in mine.values()), any(s == 1 for s in mine.values()),
                             int(v[2]) != 0, int(v[3]) != 0)] += 1
            elif op == VIS and len(v) > 3:
                slot6f[(rg, int(v[1]) in own_ids, int(v[2]), int(v[3]) != 0)] += 1
        for h in hero_agents:
            heroes[(rg, h in created, h in d6)] += 1

        def reply(t, ops):
            return [(rop, list(rv)) for (rt, rop, rv) in s2c if t <= rt <= t + 1.5 and rop in ops]
        for t, op, v in c2s:
            if op == 0x0032:
                r = reply(t, (ACTIVE, VIS))
                switches[(rg, any(o == ACTIVE for o, _ in r),
                          any(o == VIS and int(rv[2]) in tw.HAND_SLOTS for o, rv in r))] += 1
            elif op in (0x0030, 0x004F):
                r = reply(t, (VIS,))
                equips[(rg, op, any(int(rv[2]) in tw.HAND_SLOTS for _o, rv in r))] += 1
            elif op == 0x0086 and regime == 0:
                placed = [(int(rv[3]), int(rv[4])) for _o, rv in reply(t, (0x013E,)) if int(rv[3]) in type2]
                vis = [int(rv[2]) for _o, rv in reply(t, (VIS,))]
                for _bag, slot in placed:
                    pvp[("hand" if slot in tw.HAND_SLOTS else "armour", bool(vis),
                         bool(vis) and all(s not in tw.HAND_SLOTS for s in vis))] += 1
    o_bodies = sum(n for (r, _o, _a, _b), n in bodies.items() if r == "outpost")
    o_armed = sum(n for (r, _o, a, b), n in bodies.items() if r == "outpost" and (a or b))
    led.ok(len(conns) >= 90 and decoded == len(conns), f"every live connection decoded ({decoded} of {len(conns)})")
    led.ok(o_bodies >= 2000 and o_armed == 0,
           f"OBSERVED: every outpost 0x006E is empty-handed on BOTH visuals ({o_armed} of {o_bodies} bodies "
           f"carry a lead or an off hand)", f"{dict(bodies)}")
    o_own_lead = sum(n for (r, bl, _bo, _a, _b), n in own_bag.items() if r == "outpost" and bl)
    o_own_off = sum(n for (r, _bl, bo, _a, _b), n in own_bag.items() if r == "outpost" and bo)
    o_own_armed = sum(n for (r, _bl, _bo, a, b), n in own_bag.items() if r == "outpost" and (a or b))
    led.ok(o_own_lead >= 40 and o_own_off >= 15 and o_own_armed == 0,
           f"...the OWN body among them (its armour ids all in ONE type-2 bag): {o_own_lead} outpost loads "
           f"with a lead in that bag, {o_own_off} with an off hand, and {o_own_armed} carry either -- the "
           f"bag holds the weapon the body does not show", f"{dict(own_bag)}")
    f_lead_c = own_bag[("field", True, False, True, False)] + own_bag[("field", True, True, True, True)]
    f_lead_m = sum(n for (r, bl, _bo, a, _b), n in own_bag.items() if r == "field" and bl and not a)
    f_off_c = own_bag[("field", True, True, True, True)]
    f_off_m = sum(n for (r, _bl, bo, _a, b), n in own_bag.items() if r == "field" and bo and not b)
    f_none = own_bag[("field", False, False, False, False)]
    f_ghost = sum(n for (r, bl, bo, a, b), n in own_bag.items() if r == "field" and ((a and not bl) or (b and not bo)))
    led.ok(f_lead_c >= 30 and f_lead_m == 0 and f_off_c >= 15 and f_off_m == 0 and f_none >= 1 and f_ghost == 0,
           f"CONTROL, the FIELD: the own body carries every hand its bag holds ({f_lead_c} of "
           f"{f_lead_c + f_lead_m} leads, {f_off_c} of {f_off_c + f_off_m} off hands), none when the bag "
           f"holds none ({f_none}), and never a hand the bag lacks -- the array reflects the bag there")
    o_hand_6f = sum(n for (r, _o, s, _i), n in slot6f.items() if r == "outpost" and s in tw.HAND_SLOTS)
    f_own_hand_6f = sum(n for (r, o, s, _i), n in slot6f.items() if r == "field" and o and s in tw.HAND_SLOTS)
    o_own_6f = {s: n for (r, o, s, _i), n in slot6f.items() if r == "outpost" and o}
    led.ok(o_hand_6f == 0 and f_own_hand_6f >= 5,
           f"OBSERVED: no outpost 0x006F writes a hand on ANY agent ({o_hand_6f}); the own field body's hands "
           f"are written {f_own_hand_6f} times", f"{dict(slot6f)}")
    led.ok(o_own_6f and all(s not in tw.HAND_SLOTS for s in o_own_6f) and any(2 <= s <= 8 for s in o_own_6f),
           f"...and the own outpost 0x006F that DOES exist goes to an armour slot ({o_own_6f}): the rule is "
           f"the SLOT, not the regime")
    o_sw = sum(n for (r, _a, _h), n in switches.items() if r == "outpost")
    f_sw = sum(n for (r, _a, _h), n in switches.items() if r == "field")
    led.ok(o_sw >= 3 and switches[("outpost", True, False)] == o_sw
           and f_sw >= 3 and switches[("field", True, True)] == f_sw,
           f"OBSERVED: every outpost c2s 0x0032 switch ({o_sw}) is answered with 0x0148 and NO hand 0x006F; "
           f"every field switch ({f_sw}) with 0x0148 and a hand 0x006F", f"{dict(switches)}")
    o_eq = sum(n for (r, _op, _h), n in equips.items() if r == "outpost")
    led.ok(o_eq >= 4 and all(not h for (r, _op, h) in equips if r == "outpost")
           and equips[("outpost", 0x0030, False)] >= 3 and equips[("outpost", 0x004F, False)] >= 1,
           f"OBSERVED: the outpost 0x0030 equips and 0x004F move ({o_eq}) carry no hand 0x006F",
           f"{ {(r, hex(o), h): n for (r, o, h), n in equips.items()} }")
    led.ok(pvp[("hand", False, False)] >= 3 and pvp[("armour", True, True)] >= 1
           and not any(k[0] == "hand" and k[1] for k in pvp),
           f"OBSERVED, the discriminator: the PvP equipment panel (c2s 0x0086) in an outpost placed "
           f"{pvp[('hand', False, False)]} items straight into equipped slot 0/1 with no 0x006F and "
           f"{pvp[('armour', True, True)]} into an armour cell WITH one to a non-hand slot", f"{dict(pvp)}")
    o_npc = npc6d[("outpost", True)] + npc6d[("outpost", False)]
    led.ok(o_npc >= 1000 and npc6d[("outpost", True)] >= 100,
           f"REPORT: retail's outpost NPCs carry 0x006D weapons ({npc6d[('outpost', True)]} of {o_npc} with a "
           f"lead) -- the empty hands are the PLAYER body's rule, not a town's")
    o_heroes = sum(n for (r, _c, _d), n in heroes.items() if r == "outpost")
    led.ok(o_heroes >= 1 and heroes[("outpost", False, False)] == o_heroes and heroes[("field", True, True)] >= 1,
           f"OBSERVED: no hero body in an outpost ({o_heroes} party heroes over the outpost connections, none "
           f"created, none with a 0x006D); a field hero has a body and a 0x006D ({heroes[('field', True, True)]})",
           f"{dict(heroes)}")

# ---- §3 the server ---------------------------------------------------------------------
SRC = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
ARGS = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()


def func_src(name):
    start = SRC.find(f"\ndef {name}(")
    end = SRC.find("\ndef ", start + 1)
    return SRC[start:end] if start > 0 else ""


def func_at(pos):
    return SRC.rfind("\ndef ", 0, pos), SRC[SRC.rfind("\ndef ", 0, pos) + 5:SRC.find("(", SRC.rfind("\ndef ", 0, pos))]


led.ok("\nimport townweapon" in SRC and "TOWN_WEAPON_STRIP_ENABLED = True" in SRC,
       "SOURCE LOCK: the leaf is imported and the flag global defaults ON")
led.ok('"--no-town-weapon-strip"' in ARGS and "a.no_town_weapon_strip" in SRC
       and "TOWN_WEAPON_STRIP_ENABLED = False" in SRC,
       "SOURCE LOCK: the revert flag is declared in serverargs.py and wired in main()")
vw = func_src("visible_worn")
led.ok("if TOWN_WEAPON_STRIP_ENABLED:" in vw and "townweapon.strip_hands(shown, field)" in vw
       and "visstatus.strip_visual(" in vw and vw.index("visstatus.strip_visual(") < vw.index("townweapon.strip_hands("),
       "SOURCE LOCK: visible_worn applies the display mode then the town's hands, each behind its flag")
vsw = func_src("visible_slot_writes")
led.ok("if not VISIBILITY_STATUS_ENABLED and not TOWN_WEAPON_STRIP_ENABLED:" in vsw
       and "townweapon.drops(vals[1], field)" in vsw and "int(vals[0]) == PLAYER_AGENT_ID" in vsw,
       "SOURCE LOCK: visible_slot_writes drops the PLAYER's hand writes in a town behind the flag and "
       "passes the batch whole only when both flags are off")
sws = func_src("select_weapon_set")
led.ok("_send(GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT" not in sws
       and sws.count("_vis.append((GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT") == 3
       and "visible_slot_writes(_vis, state, conn_id)" in sws
       and sws.index("_vis.append((GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT") < sws.index("visible_slot_writes(_vis"),
       "SOURCE LOCK: select_weapon_set builds its three hand 0x006F into a batch and sends only what "
       "visible_slot_writes returns -- no direct hand send left")
senders = sorted({func_at(m.start())[1] for m in re.finditer(r"\bsend\(GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT", SRC)})
led.ok(senders == ["handle_visibility_flags"],
       "SOURCE LOCK: the only direct `send(0x006F ...)` left in authsrv.py is handle_visibility_flags' "
       "(the display mode's slots 6/7/8, never a hand); every other player 0x006F passes "
       "visible_slot_writes", f"{senders}")
import visstatus                                             # noqa: E402
led.ok(set(visstatus.KIND_VISUAL_SLOT.values()) == {6, 7, 8}
       and all(s not in tw.HAND_SLOTS for _k, s, _i in visstatus.slot_changes(0xFF, 0x00, [1, 12, 3, 4, 5, 6, 7, 8, 9], False)),
       "...and the display mode's slot_changes never names a hand")

_saved = {k: getattr(authsrv, k) for k in
          ("PERSIST", "ITEM_MOVES_ENABLED", "EXPLORABLE", "OUTPOST", "EQUIP_WEAPON",
           "EQUIP_ARMOUR", "EQUIP_COSTUME", "EQUIP_COSTUME_HEAD", "WEAPON_SETS",
           "PLAYER_SWING_DAMAGE", "WEAPON_ATTACK_SPEED", "ATTACK_INTERVAL",
           "EQUIPPED_VISUAL_ORDER", "VISIBILITY_STATUS_ENABLED", "TOWN_WEAPON_STRIP_ENABLED")}
_saved_off, _saved_wpn = authsrv.agents.PLAYER_OFFHAND, authsrv.agents.PLAYER_WEAPON
_saved_slots, _saved_over = dict(authsrv.WEAPON_SET_BACKPACK_SLOTS), dict(authsrv.SET_ITEMS_OVERRIDE)
try:
    authsrv.PERSIST, authsrv.ITEM_MOVES_ENABLED = False, True
    authsrv.EQUIP_WEAPON, authsrv.EQUIP_ARMOUR = True, True
    authsrv.EQUIP_COSTUME, authsrv.EQUIP_COSTUME_HEAD = False, False
    authsrv.EQUIPPED_VISUAL_ORDER = False
    authsrv.VISIBILITY_STATUS_ENABLED, authsrv.TOWN_WEAPON_STRIP_ENABLED = True, True
    W, EQ, BP = authsrv.WEAPON_ITEM_ID, authsrv.EQUIPPED_BAG_ID, authsrv.BACKPACK_BAG_ID
    MOVE, EQUIP = authsrv.GAME_CMSG_ITEM_MOVE, authsrv.GAME_CMSG_EQUIP_ITEM

    def fresh(outpost, strip=True, vis=True, flags=None):
        """A real item layout (--weapon-set 1=starter_sword+starter_shield) in a town or a field."""
        authsrv.WEAPON_SETS = [{"lead": "starter_hammer", "off": None}, None, None, None]
        authsrv.agents.PLAYER_OFFHAND = None
        authsrv.SET_ITEMS_OVERRIDE.clear()
        authsrv.configure_weapon_sets(["1=starter_sword+starter_shield"])
        authsrv.OUTPOST, authsrv.EXPLORABLE = outpost, not outpost
        authsrv.TOWN_WEAPON_STRIP_ENABLED, authsrv.VISIBILITY_STATUS_ENABLED = strip, vis
        st = {"agents": {}, "char_uuid": UUID, "map_id": 145}
        if flags is not None:
            st["vis_flags"] = flags
        items = authsrv.item_layout_begin(st, 0)
        authsrv.player_pools(st)
        return st, items

    # the load, in a TOWN
    st, items = fresh(outpost=True)
    dressed = authsrv.player_worn_array(st)
    world = authsrv.visible_worn(dressed, st, 0)
    led.ok(dressed[0] == W and dressed[6] and world[:2] == [0, 0] and world[2:] == dressed[2:]
           and itemstore.hand_items(items, EQ) == (W, 0) and authsrv.player_worn_array(st) == dressed,
           f"TOWN load: the dressed array (the doll's) keeps the hammer (item {W}) at visual 0 and the "
           f"world's 0x006E leaves visuals 0 and 1 empty with the armour intact; the equipped bag still "
           f"holds the hammer", f"{dressed} -> {world}")
    stf, itemsf = fresh(outpost=False)
    led.ok(authsrv.visible_worn(authsrv.player_worn_array(stf), stf, 0) == authsrv.player_worn_array(stf)
           and authsrv.player_worn_array(stf)[0] == W,
           "FIELD CONTROL: the world's 0x006E carries the hammer at visual 0 (retail's 40 of 40)")
    stk, _ik = fresh(outpost=True, strip=False)
    kept = authsrv.visible_worn(authsrv.player_worn_array(stk), stk, 0)
    led.ok(kept == authsrv.player_worn_array(stk) and kept[0] == W and kept != world,
           "KNOWN-BAD (--no-town-weapon-strip): the town body still wears the hammer -- every run before "
           "this day, and it disagrees with the default arm")
    st_empty, items_empty = fresh(outpost=True)
    authsrv.handle_item_move([MOVE, 0, BP, 9], fake_send_factory()[1], st_empty, 0)   # the hammer out
    bare = authsrv.player_worn_array(st_empty)
    led.ok(bare[0] == 0 and authsrv.visible_worn(bare, st_empty, 0) == bare,
           "VACUITY: a town body whose hands are already empty (the hammer dragged out) is unchanged by "
           "the strip")

    # F2 / F1 in a TOWN: retail's outpost shape (0 of 4 switches carried a 0x006F)
    st, items = fresh(outpost=True)
    sent, send = fake_send_factory()
    authsrv.select_weapon_set(send, st, 1, 0)
    led.ok([op for op, _v in sent] == [ACTIVE, CHG, SWAP] and sent[0][1] == [1, 1]
           and sent[1][1] == [1, 12, EQ, 1] and sent[2][1] == [1, W, 11]
           and itemstore.hand_items(items, EQ) == (11, 12) and authsrv.player_worn_array(st)[:2] == [11, 12]
           and authsrv.visible_worn(authsrv.player_worn_array(st), st, 0)[:2] == [0, 0],
           "TOWN F2 (sword + shield): 0x0148 [1, 1], the shield's 0x014B into equipped 1, the lead swap "
           "0x0152 [1, hammer, sword] and NO 0x006F -- retail's outpost batch (20260919T103604 :58638, "
           "0 of 4 with a visual); the bag and the doll's array hold the new set, the world's hands stay "
           "empty", f"{sent}")
    sent.clear()
    authsrv.select_weapon_set(send, st, 0, 0)
    led.ok([op for op, _v in sent] == [ACTIVE, CHG, SWAP] and sent[1][1] == [1, 12, BP, 1]
           and sent[2][1] == [1, 11, W] and itemstore.hand_items(items, EQ) == (W, 0),
           "TOWN F1: the shield back to its backpack cell, the swap, NO 0x006F for the emptied off hand or "
           "the lead (retail's 0x0148 + 0x014B / 0x0152 only)", f"{sent}")
    # the same two in a FIELD: retail's field shape (4 of 4 carried the hands)
    stf, itemsf = fresh(outpost=False)
    sentf, sendf = fake_send_factory()
    authsrv.select_weapon_set(sendf, stf, 1, 0)
    led.ok([op for op, _v in sentf] == [ACTIVE, CHG, SWAP, VIS, VIS]
           and sentf[3][1] == [P, 0, 11] and sentf[4][1] == [P, 1, 12],
           "FIELD F2: the same three rows THEN 0x006F [player, 0, sword], [player, 1, shield] -- retail's "
           "[25, 0, 208] / [25, 1, 207] (:56576)", f"{sentf}")
    sentf.clear()
    authsrv.select_weapon_set(sendf, stf, 0, 0)
    led.ok([op for op, _v in sentf] == [ACTIVE, CHG, SWAP, VIS, VIS]
           and sentf[3][1] == [P, 1, 0] and sentf[4][1] == [P, 0, W],
           "FIELD F1: the emptied off hand's 0x006F [player, 1, 0] before the lead's [player, 0, hammer] -- "
           "retail's [25, 1, 0] / [25, 0, 212]", f"{sentf}")
    stk, _ik = fresh(outpost=True, strip=False)
    sentk, sendk = fake_send_factory()
    authsrv.select_weapon_set(sendk, stk, 1, 0)
    led.ok([op for op, _v in sentk] == [ACTIVE, CHG, SWAP, VIS, VIS] and sentk[3][1] == [P, 0, 11],
           "KNOWN-BAD (--no-town-weapon-strip): the town F2 carries the two hand 0x006F -- the divergence "
           "every run before this day sent", f"{sentk}")

    # the equip path: 0x004F out, 0x0030 back
    st, items = fresh(outpost=True)
    sent, send = fake_send_factory()
    authsrv.handle_item_move([MOVE, 0, BP, 9], send, st, 0)
    authsrv.handle_equip_item([EQUIP, W], send, st, 0)
    led.ok(sent == [(CHG, [1, W, BP, 9]), (CHG, [1, W, EQ, 0])] and itemstore.hand_items(items, EQ) == (W, 0),
           "TOWN equip path: the hammer out (0x004F) and back (0x0030) ride 0x014B alone -- retail's "
           "outpost 0x004F (1 of 1) and 0x0030 (4 of 4) carried no hand 0x006F", f"{sent}")
    stf, itemsf = fresh(outpost=False)
    sentf, sendf = fake_send_factory()
    authsrv.handle_item_move([MOVE, 0, BP, 9], sendf, stf, 0)
    authsrv.handle_equip_item([EQUIP, W], sendf, stf, 0)
    led.ok(sentf == [(CHG, [1, W, BP, 9]), (VIS, [P, 0, 0]), (CHG, [1, W, EQ, 0]), (VIS, [P, 0, W])],
           "FIELD equip path CONTROL: 0x014B + 0x006F [player, 0, 0] out, 0x014B + 0x006F [player, 0, hammer] "
           "back (retail's field 0x0030: 0x014B + 0x006F, 4 of 4)", f"{sentf}")

    # composition with the display mode: headgear Hide in Towns (0xF7) in a town
    st, items = fresh(outpost=True, flags=0xF7)
    dressed = authsrv.player_worn_array(st)
    both = authsrv.visible_worn(dressed, st, 0)
    led.ok(dressed[0] == W and dressed[6] and both[0] == 0 and both[1] == 0 and both[6] == 0
           and both[2:6] == dressed[2:6],
           "BOTH RULES in a town under Hide in Towns: visuals 0, 1 AND 6 leave the array, the other armour "
           "stays", f"{dressed} -> {both}")
    st_v, _iv = fresh(outpost=True, strip=False, flags=0xF7)
    only_mode = authsrv.visible_worn(authsrv.player_worn_array(st_v), st_v, 0)
    st_t, _it = fresh(outpost=True, vis=False, flags=0xF7)
    only_town = authsrv.visible_worn(authsrv.player_worn_array(st_t), st_t, 0)
    led.ok(only_mode[0] == W and only_mode[6] == 0 and only_town[0] == 0 and only_town[6] == dressed[6],
           "each flag alone zeroes its own slots: the display mode the head, the town weapon the hands")

    # visible_slot_writes' edges
    authsrv.OUTPOST, authsrv.EXPLORABLE = True, False
    authsrv.TOWN_WEAPON_STRIP_ENABLED, authsrv.VISIBILITY_STATUS_ENABLED = True, True
    plain = [(CHG, [1, 2, 3, 4], "x"), (VIS, [P, 0, 9], "hand"), (VIS, [P + 1, 0, 9], "npc hand"),
             (VIS, [P, 6, 7], "head"), (VIS, [P, 1, 0], "emptied off hand")]
    got = authsrv.visible_slot_writes(plain, {"vis_flags": 0xFF}, 0)
    led.ok(got == [plain[0], plain[2], plain[3]],
           "visible_slot_writes in a town: the player's lead and emptied off hand are DROPPED; another "
           "agent's hand and the player's head pass (the PvP head precedent)", f"{got}")
    authsrv.VISIBILITY_STATUS_ENABLED = False
    got2 = authsrv.visible_slot_writes(plain, {"vis_flags": 0xFF}, 0)
    led.ok(got2 == [plain[0], plain[2], plain[3]],
           "...the hands are dropped whatever the display-mode flag (the gates are independent)")
    authsrv.TOWN_WEAPON_STRIP_ENABLED = False
    led.ok(authsrv.visible_slot_writes(plain, {"vis_flags": 0xFF}, 0) == plain,
           "KNOWN-BAD, both flags off: the batch passes whole (every run before the display-mode pass)")
    authsrv.TOWN_WEAPON_STRIP_ENABLED, authsrv.VISIBILITY_STATUS_ENABLED = True, True
    authsrv.OUTPOST, authsrv.EXPLORABLE = False, True
    led.ok(authsrv.visible_slot_writes(plain, {"vis_flags": 0xFF}, 0) == plain,
           "FIELD CONTROL: the same batch passes whole")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    authsrv.agents.PLAYER_OFFHAND, authsrv.agents.PLAYER_WEAPON = _saved_off, _saved_wpn
    authsrv.WEAPON_SET_BACKPACK_SLOTS.clear()
    authsrv.WEAPON_SET_BACKPACK_SLOTS.update(_saved_slots)
    authsrv.SET_ITEMS_OVERRIDE.clear()
    authsrv.SET_ITEMS_OVERRIDE.update(_saved_over)

sys.exit(led.verdict())
