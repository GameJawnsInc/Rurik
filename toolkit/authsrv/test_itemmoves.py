"""The inventory pair -- c2s 0x004F ITEM_MOVE and 0x0030 EQUIP_ITEM -- and the
item store behind them (DESKWORK-D1 step 8; studies/cmsg/FINDINGS.md
DESKWORK-D1 "Inventory"; itemstore.py's docstring for the tapes).

    python toolkit/authsrv/test_itemmoves.py

  * §1 RETAIL'S BATCHES, value for value against the TRANSCRIPTION, through
    the pure leaf with retail's own ids, bag ids, inventory keys and agent
    ids: the three field unequips and three field re-equips of
    20260917T090355 :53310 (head 213, gloves 215, boots 214 -- the ldufr bag
    order and the GWLP-R visual order both reproduced), the outpost off-hand
    move of 20260919T103604 :58638 (no 0x006F), the Factions wand of
    20260913T210901 :60877, and the four outpost swaps of 20260819T132414
    :53419 (0x0152 alone, the occupant first). KNOWN-BAD arms: our identity
    visual mapping on retail's head (visual 4, the tape says 6), our
    visual-order bag on retail's equip, a visual in the outpost.
  * §1b THE SAME TWELVE DECODED FROM THE TAPES (vault-gated; LEDGER.skip on a
    bare machine): livewire.decode_conn on the four connections, the item
    state built from the tape's own 0x013F/0x013E/0x014B/0x0152 rows (the
    equipped bag = the type-2 bag, the key, the field bit and the agent all
    read off the tape), the planner's batch compared to the s2c rows inside
    0.1 s of each request. Only the item TYPES are transcribed.
  * §2 REFUSALS return no batch: an empty source slot, the equipped bag as a
    destination, an undeclared bag, a slot past the bag, a FILLED destination
    (ItCliInv:105); an unknown item, one already worn, a type with no slot, an
    off hand beside a two-handed lead; and the two-hander that displaces a
    worn off hand (RECONSTRUCTION: the off hand leaves first, to the
    backpack's first free slot).
  * §3 RESTORE: a stored armour cell wins, a hand change is kept at the
    default with a note, an unknown id is ignored, an illegal cell or a
    collision discards the whole store.
  * §4 THE SERVER: item_layout_begin's default layout is the constants' and
    itemstore.worn_array over it equals the 0x006E fill the load path built
    before this step; --outpost wins over --explorable (ENG-M3); the real
    handlers with a fake send in a field and in a town (the visual rides the
    field only); the DAMAGE MODEL follows the store (a head in the backpack
    leaves a bare location, ENG-B5); the hands mirror (a weapon moved out
    empties SET_ITEMS_OVERRIDE[0] and says so; equipped back, the swing model
    follows while the LAUNCH RECORDS stand, ENG-B4; a set switch after an
    equip reads the swing model off the hands); select_weapon_set after an
    emptied hand sends 0x014B into slot 0, never a 0x0152 with a 0; THE NEXT
    CONNECTION dresses set 0's items again (no duplicated sword, the shield
    re-declared, ENG-B4); RESERVED cells: a 0x004F into a worn set item's
    return cell is refused, the switch avoids a filled one (ENG-B3);
    --persist writes item_locations, a fresh dress restores the armour cell
    and not the hand -- from a BARE state, the store looked up by the dress
    itself, with the no-store control (ENG-B1); a restored set-item slot
    survives declare_weapon_sets (ENG-M2); charstore refuses malformed cells,
    --no-item-moves reads nothing stored.
  * §5 SOURCE LOCKS (syntax tree over authsrv.py): both arms call their
    handler only under ITEM_MOVES_ENABLED (mutation reddens), main() wires the
    flag, the dress calls item_layout_begin BEFORE the weapon's create and
    item_cell at every placement, declare_weapon_sets takes the state, the
    0x006E build reads itemstore.worn_array, weapon_set_items reads
    SET_ITEMS_OVERRIDE first, test_dispatch carries no allowlist row for
    either opcode, serverargs defines --no-item-moves; the fix pass's five
    (the dress's lookup and re-apply, the mirror's untouched records, the
    slot map, the reserved cells, the armour read).

Floor from the green run (see the ledger line).
"""
import ast
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import charstore                                             # noqa: E402
import itemstore                                             # noqa: E402
import authsrv                                               # noqa: E402

led = checks.Ledger("inventory moves (DESKWORK-D1 step 8)", floor=102)   # 2026-09-23, from the green run: the bare-machine core (78 -> 102 at the fix pass); §1b's 17 ride the vault

CHG, SWAP, VIS = 0x014B, 0x0152, 0x006F
MOVE, EQUIP = authsrv.GAME_CMSG_ITEM_MOVE, authsrv.GAME_CMSG_EQUIP_ITEM
assert (CHG, SWAP, VIS, MOVE, EQUIP) == (authsrv.GAME_SMSG_ITEM_CHANGE_LOCATION,
                                         authsrv.GAME_SMSG_ITEM_SWAP_LOCATIONS,
                                         authsrv.GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT,
                                         0x004F, 0x0030)
HANDS = authsrv.item_hands_of_type()
UUID = "44444444444444444444444444444444"


def ops_vals(batch):
    return [(op, list(v)) for op, v, _l in batch]


def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals) if isinstance(vals, (list, tuple)) else vals))
    return sent, send


led.ok(HANDS.get(15) == "two" and HANDS.get(27) == "one" and HANDS.get(32) == "two"
       and HANDS.get(24) == "off" and HANDS.get(22) == "one" and HANDS.get(28) == "npc",
       "the weapon-type rows give hammer two / sword one / daggers two / shield off / "
       "wand one / the hostile type npc", f"{sorted(HANDS.items())}")

# ---- §1 retail's batches -------------------------------------------------------------
# 20260917T090355 :53310 -- player agent 25, inventory key 1, equipped bag 3, backpack 2.
bags_53310 = {2: 20, 3: 9, 4: 12, 5: 25, 6: 25, 7: 25, 8: 25, 9: 25, 10: 42}
it = {}
itemstore.place(it, 213, 3, 4, item_type=16)   # head, the load's 0x013E [1, 213, 3, 4]
itemstore.place(it, 214, 3, 5, item_type=4)    # boots
itemstore.place(it, 215, 3, 6, item_type=13)   # gloves
RV = itemstore.retail_visual_of_bag_slot
tape_moves = ((4, 2, 1, [(CHG, [1, 213, 2, 1]), (VIS, [25, 6, 0])]),
              (6, 2, 2, [(CHG, [1, 215, 2, 2]), (VIS, [25, 5, 0])]),
              (5, 2, 3, [(CHG, [1, 214, 2, 3]), (VIS, [25, 3, 0])]))
for src, bag, slot, expect in tape_moves:
    batch, changes, why = itemstore.plan_move(it, bags_53310, src, bag, slot, key=1,
                                              equipped_bag=3, agent=25, visuals=True,
                                              visual_of=RV)
    led.ok(why is None and ops_vals(batch) == expect,
           f"TAPE 0x004F [{src}, {bag}, {slot}] -> {expect} (t=406.2/411.1/412.4, field)",
           f"got {why or ops_vals(batch)}")
    itemstore.apply(it, changes or [])
led.ok(itemstore.in_bag(it, 3) == {} and itemstore.in_bag(it, 2) == {1: 213, 2: 215, 3: 214},
       "after the three unequips the equipped bag is empty and the backpack holds 213/215/214 "
       "at slots 1/2/3")
# KNOWN-BAD: our identity visual mapping on retail's cells.
bad, _c, _w = itemstore.plan_move(dict((k, dict(v)) for k, v in
                                       {213: {"bag": 3, "slot": 4, "key": None, "kind": None, "item_type": 16}}.items()),
                                  bags_53310, 4, 2, 1, key=1, equipped_bag=3, agent=25, visuals=True)
led.ok(ops_vals(bad) == [(CHG, [1, 213, 2, 1]), (VIS, [25, 4, 0])] and ops_vals(bad) != tape_moves[0][3],
       "KNOWN-BAD: the identity visual mapping (ours) on retail's head gives 0x006F slot 4; the "
       "tape says 6 -- the bag order and the visual order are two arrays")
tape_equips = ((213, [(CHG, [1, 213, 3, 4]), (VIS, [25, 6, 213])]),
               (215, [(CHG, [1, 215, 3, 6]), (VIS, [25, 5, 215])]),
               (214, [(CHG, [1, 214, 3, 5]), (VIS, [25, 3, 214])]))
for item, expect in tape_equips:
    batch, changes, why = itemstore.plan_equip(it, bags_53310, item, key=1, equipped_bag=3,
                                               backpack_bag=2, agent=25, visuals=True,
                                               hands_of_type=HANDS, visual_of=RV,
                                               bag_slot_of_type=itemstore.RETAIL_BAG_SLOT_OF_TYPE)
    led.ok(why is None and ops_vals(batch) == expect,
           f"TAPE 0x0030 [{item}] -> {expect} (t=559.0/559.5/560.4, an EMPTY slot, field)",
           f"got {why or ops_vals(batch)}")
    itemstore.apply(it, changes or [])
led.ok(itemstore.in_bag(it, 3) == {4: 213, 5: 214, 6: 215},
       "...and the three pieces are back at the load's cells (3,4) (3,5) (3,6)")
bad3, _c, _w = itemstore.plan_equip({213: {"bag": 2, "slot": 1, "key": None, "kind": None, "item_type": 16}},
                                    bags_53310, 213, key=1, equipped_bag=3, backpack_bag=2, agent=25,
                                    visuals=True, hands_of_type=HANDS, visual_of=RV)
led.ok(ops_vals(bad3) == [(CHG, [1, 213, 3, 6]), (VIS, [25, 5, 213])] and ops_vals(bad3) != tape_equips[0][1],
       "KNOWN-BAD: our visual-order bag layout on retail's head equips it at bag slot 6 (visual 5); "
       "the tape says bag 4, visual 6 -- retail's bag is ldufr's order")

# 20260919T103604 :58638 -- an OUTPOST; key 241; equipped bag 231; 17730 = set 0's off hand at (231, 1).
it2 = {}
itemstore.place(it2, 17730, 231, 1, item_type=24)
itemstore.place(it2, 24945, 231, 0, item_type=36)
bags_58638 = {136: 20, 231: 9, 1161: 12, 1020: 25, 655: 25, 946: 25, 1834: 25, 822: 25, 347: 42}
batch, changes, why = itemstore.plan_move(it2, bags_58638, 1, 136, 6, key=241, equipped_bag=231,
                                          agent=45, visuals=False, visual_of=RV)
led.ok(why is None and ops_vals(batch) == [(CHG, [241, 17730, 136, 6])],
       "TAPE 0x004F [1, 136, 6] -> 0x014B [241, 17730, 136, 6] and nothing else (t=232.975, "
       "outpost: no 0x006F)", f"got {why or ops_vals(batch)}")
bad2, _c, _w = itemstore.plan_move(it2, bags_58638, 1, 136, 6, key=241, equipped_bag=231,
                                   agent=45, visuals=True, visual_of=RV)
led.ok(len(bad2) == 2 and ops_vals(bad2)[1] == (VIS, [45, 1, 0]),
       "KNOWN-BAD: a visual in the outpost adds a 0x006F the tape does not carry")

# 20260913T210901 :60877 -- the Factions wand: item 40 (type 22) from bag 2 slot 0; agent 9; equipped bag 3.
it3 = {}
itemstore.place(it3, 40, 2, 0, item_type=22)
batch, changes, why = itemstore.plan_equip(it3, {2: 20, 3: 9}, 40, key=1, equipped_bag=3,
                                           backpack_bag=2, agent=9, visuals=True,
                                           hands_of_type=HANDS, visual_of=RV)
led.ok(why is None and ops_vals(batch) == [(CHG, [1, 40, 3, 0]), (VIS, [9, 0, 40])],
       "TAPE 0x0030 [40] -> 0x014B [1, 40, 3, 0] + 0x006F [9, 0, 40] (t=211.678, the wand "
       "into an empty slot 0, field)", f"got {why or ops_vals(batch)}")

# 20260819T132414 :53419 -- Shing Jea, an OUTPOST; key 159; equipped bag 662; backpack 474.
it4 = {}
itemstore.place(it4, 2767, 662, 0, item_type=15)   # hammer in hand
itemstore.place(it4, 1469, 474, 4, item_type=32)   # daggers
itemstore.place(it4, 3451, 474, 6, item_type=27)   # sword
swaps = ((3451, [(SWAP, [159, 2767, 3451])]), (1469, [(SWAP, [159, 3451, 1469])]),
         (3451, [(SWAP, [159, 1469, 3451])]), (1469, [(SWAP, [159, 3451, 1469])]))
for item, expect in swaps:
    batch, changes, why = itemstore.plan_equip(it4, {474: 20, 662: 9}, item, key=159, equipped_bag=662,
                                               backpack_bag=474, agent=404, visuals=False,
                                               hands_of_type=HANDS, visual_of=RV)
    led.ok(why is None and ops_vals(batch) == expect,
           f"TAPE 0x0030 [{item}] -> {expect} alone (t=84.8/89.4/92.2/93.2, an OCCUPIED slot, outpost)",
           f"got {why or ops_vals(batch)}")
    itemstore.apply(it4, changes or [])
led.ok(itemstore.at(it4, 662, 0) == 1469 and itemstore.at(it4, 474, 6) == 2767
       and itemstore.at(it4, 474, 4) == 3451,
       "after the four swaps: 1469 in hand, 2767 at (474,6), 3451 at (474,4) -- each occupant "
       "took the cell the incoming item came from (the client's own exchange)")

# ---- §1b the same twelve batches DECODED FROM THE TAPES (vault-gated) ----------------
# §1 above compares the planner to values transcribed by hand; a reviewer noted
# that drift between the transcription and the vault would be invisible to it
# (EVID-D1C-4). This section decodes the four connections with
# livewire.decode_conn and runs the planner against the ITEM STATE THE TAPE
# ITSELF BUILDS -- every 0x013E / 0x014B / 0x0152 applied as it arrives, the
# equipped bag being the 0x013F row of type 2 (the client's own gate,
# 0x008454F0), the inventory key the 0x013E rows', the field/outpost bit the
# 0x0199 byte, the player's agent the load's own 0x006E -- and compares the
# plan to the s2c rows that follow each request inside 0.1 s. Only the item
# TYPES are transcribed (the 0x0161 declare's field is not decoded here).
import livewire                                                       # noqa: E402
TAPES = (("20260917T090355", 53310, {213: 16, 214: 4, 215: 13}),
         ("20260919T103604", 58638, {17730: 24, 24945: 36}),
         ("20260913T210901", 60877, {40: 22}),
         ("20260819T132414", 53419, {2767: 15, 3451: 27, 1469: 32}))
REPLY_OPS = {CHG, SWAP, VIS}
root = livewire.captures_root()
have = [os.path.isdir(os.path.join(root, cap)) for cap, _p, _t in TAPES]
if all(have):
    n_requests = 0
    for cap, port, types in TAPES:
        capdir = os.path.join(root, cap)
        gf = next((g for g in livewire.connections(capdir) if f"_{port}-to-" in g), None)
        conn, merged, ok = livewire.decode_conn(capdir, gf) if gf else (None, [], False)
        led.ok(ok and merged, f"TAPE {cap} :{port} decodes closed ({len(merged)} rows)")
        tape_items, bags, equipped_bag, key, field, agent = {}, {}, None, None, None, None
        for i, (t, d, op, v) in enumerate(merged):
            if d == "s2c":
                if op == 0x013F:                       # INVENTORY_CREATE_BAG [key, type, model, bag, slots, item]
                    bags[int(v[4])] = int(v[5])
                    if int(v[2]) == 2:
                        equipped_bag = int(v[4])
                elif op == 0x0199:
                    field = bool(int(v[3]))
                elif op == 0x006E and agent is None and field is not None:
                    agent = int(v[1])
                elif op == 0x013E or op == CHG:        # [key, item, bag, slot]
                    key = int(v[1]) if key is None else key
                    row = tape_items.get(int(v[2]))
                    itemstore.place(tape_items, int(v[2]), int(v[3]), int(v[4]),
                                    item_type=types.get(int(v[2]), (row or {}).get("item_type")))
                elif op == SWAP:                       # [key, a, b]: exchange cells
                    a, b = tape_items.get(int(v[2])), tape_items.get(int(v[3]))
                    if a and b:
                        (a["bag"], a["slot"]), (b["bag"], b["slot"]) = (b["bag"], b["slot"]), (a["bag"], a["slot"])
                continue
            if op not in (MOVE, EQUIP):
                continue
            n_requests += 1
            replies = [(op2, list(v2[1:])) for t2, d2, op2, v2 in merged[i + 1:i + 40]
                       if d2 == "s2c" and t2 - t <= 0.1 and op2 in REPLY_OPS]
            if op == MOVE:
                batch, _c, why = itemstore.plan_move(
                    tape_items, bags, int(v[1]), int(v[2]), int(v[3]), key=key,
                    equipped_bag=equipped_bag, agent=agent, visuals=field, visual_of=RV)
            else:
                cur = tape_items.get(int(v[1])) or {}
                batch, _c, why = itemstore.plan_equip(
                    tape_items, bags, int(v[1]), key=key, equipped_bag=equipped_bag,
                    backpack_bag=cur.get("bag", 0), agent=agent, visuals=field,
                    hands_of_type=HANDS, visual_of=RV,
                    bag_slot_of_type=itemstore.RETAIL_BAG_SLOT_OF_TYPE)
            led.ok(why is None and ops_vals(batch) == replies,
                   f"TAPE {cap}:{port} t={t:.3f} c2s 0x{op:04X} {list(v[1:])} -> the planner "
                   f"reproduces the tape's {len(replies)} reply row(s) from the tape's own state "
                   f"({'field' if field else 'outpost'}, key {key}, equipped bag {equipped_bag})",
                   f"tape {replies} planner {why or ops_vals(batch)}")
    led.ok(n_requests == 12, "the four connections carry the twelve requests the transcription "
           "names (4 moves, 8 equips)", f"{n_requests}")
else:
    led.skip("§1b the batches decoded from the tapes",
             f"vault captures missing under {root}: "
             f"{[c for (c, _p, _t), h in zip(TAPES, have) if not h]}")

# ---- §2 refusals ----------------------------------------------------------------------
it5 = {}
itemstore.place(it5, 1, 1, 0, item_type=15, key="starter_hammer")
itemstore.place(it5, 7, 1, 6, item_type=16, key="warrior_head")
itemstore.place(it5, 11, 2, 0, item_type=27, key="starter_sword")
itemstore.place(it5, 12, 2, 1, item_type=24, key="starter_shield")
itemstore.place(it5, 30, 2, 2, item_type=28, key="hostile_bow")
bags5 = {1: 9, 2: 20, 3: 12}
for args, why_frag, what in (((7, 2, 5), "no item", "an EMPTY source slot"),
                             ((6, 1, 3), "equipped bag itself", "the equipped bag as destination"),
                             ((6, 9, 0), "never declared", "an undeclared bag"),
                             ((6, 3, 12), "outside bag", "a slot past the bag's size"),
                             ((6, 2, 0), "ItCliInv:105", "a FILLED destination")):
    batch, changes, why = itemstore.plan_move(it5, bags5, *args, key=1, equipped_bag=1, agent=25,
                                              visuals=True)
    led.ok(batch is None and changes is None and why and why_frag in why,
           f"REFUSED move {args}: {what}", f"why {why!r}")
for item, why_frag, what in ((99, "not one this connection declared", "an unknown item"),
                             (7, "already in the equipped bag", "an item already worn"),
                             (30, "no equipped slot", "a type with no slot (the hostile bow)"),
                             (12, "two-handed lead", "an off hand beside a two-handed lead")):
    batch, changes, why = itemstore.plan_equip(it5, bags5, item, key=1, equipped_bag=1, backpack_bag=2,
                                               agent=25, visuals=True, hands_of_type=HANDS)
    led.ok(batch is None and why and why_frag in why, f"REFUSED equip [{item}]: {what}", f"why {why!r}")
# the two-hander displacing a worn off hand
it6 = {}
itemstore.place(it6, 11, 1, 0, item_type=27)   # a sword in hand
itemstore.place(it6, 12, 1, 1, item_type=24)   # a shield worn
itemstore.place(it6, 1, 2, 3, item_type=15)    # the hammer in the backpack
batch, changes, why = itemstore.plan_equip(it6, bags5, 1, key=1, equipped_bag=1, backpack_bag=2,
                                           agent=25, visuals=True, hands_of_type=HANDS)
led.ok(why is None and ops_vals(batch) == [(CHG, [1, 12, 2, 0]), (VIS, [25, 1, 0]),
                                           (SWAP, [1, 11, 1]), (VIS, [25, 0, 1])],
       "a two-handed hammer over sword+shield: the shield LEAVES FIRST to the backpack's first "
       "free slot (0x014B + its visual 0), then the lead swap and its visual (RECONSTRUCTION, "
       "the set switch's shape)", f"got {why or ops_vals(batch)}")
itemstore.apply(it6, changes)
led.ok(itemstore.hand_items(it6, 1) == (1, 0) and itemstore.at(it6, 2, 3) == 11
       and itemstore.at(it6, 2, 0) == 12,
       "...and the cells: hammer in hand, sword at the hammer's old cell, shield at backpack 0")
full = {}
itemstore.place(full, 12, 1, 1, item_type=24)
itemstore.place(full, 11, 1, 0, item_type=27)
itemstore.place(full, 1, 3, 0, item_type=15)
for s in range(20):
    itemstore.place(full, 1000 + s, 2, s, item_type=4)
batch, changes, why = itemstore.plan_equip(full, bags5, 1, key=1, equipped_bag=1, backpack_bag=2,
                                           agent=25, visuals=True, hands_of_type=HANDS)
led.ok(batch is None and why and "no free backpack slot" in why,
       "REFUSED: a two-hander whose displaced off hand has no free backpack slot", f"{why!r}")

# ---- §3 restore --------------------------------------------------------------------------
defaults = {1: (1, 0), 3: (1, 2), 7: (1, 6), 11: (2, 0)}
dec, notes = itemstore.restore(defaults, {7: (2, 5), 99: (2, 9)}, bags5, 1)
led.ok(dec == {1: (1, 0), 3: (1, 2), 7: (2, 5), 11: (2, 0)} and notes == [],
       "a stored armour cell wins and an id this launch does not declare is ignored", f"{dec} {notes}")
dec, notes = itemstore.restore(defaults, {1: (2, 4), 11: (1, 0)}, bags5, 1)
led.ok(dec == defaults and len(notes) == 2 and all("HAND" in n for n in notes),
       "a stored HAND change (the weapon out, a set item in) is NOT restored, with a note each",
       f"{dec} {notes}")
dec, notes = itemstore.restore(defaults, {7: (9, 0)}, bags5, 1)
led.ok(dec == defaults and notes and "IGNORED" in notes[0],
       "an illegal stored cell discards the whole store with the reason", f"{notes}")
dec, notes = itemstore.restore(defaults, {7: (2, 0)}, bags5, 1)
led.ok(dec == defaults and notes and "both stored" in notes[0],
       "a collision (the head onto set 1's lead) discards the whole store", f"{notes}")
dec, notes = itemstore.restore(defaults, {}, bags5, 1)
led.ok(dec == defaults and notes == [], "an empty store leaves the defaults")

# ---- §4 the server -----------------------------------------------------------------------
_saved = {k: getattr(authsrv, k) for k in
          ("PERSIST", "ITEM_MOVES_ENABLED", "EXPLORABLE", "OUTPOST", "EQUIP_WEAPON",
           "EQUIP_ARMOUR", "EQUIP_COSTUME", "EQUIP_COSTUME_HEAD", "WEAPON_SETS",
           "PLAYER_SWING_DAMAGE", "WEAPON_ATTACK_SPEED", "ATTACK_INTERVAL")}
_saved_off = authsrv.agents.PLAYER_OFFHAND
_saved_wpn = authsrv.agents.PLAYER_WEAPON
_saved_slots = dict(authsrv.WEAPON_SET_BACKPACK_SLOTS)
_saved_over = dict(authsrv.SET_ITEMS_OVERRIDE)
base = tempfile.mkdtemp(prefix="itemmoves-test-")
try:
    authsrv.PERSIST = False
    authsrv.ITEM_MOVES_ENABLED = True
    authsrv.EQUIP_WEAPON, authsrv.EQUIP_ARMOUR = True, True
    authsrv.EQUIP_COSTUME, authsrv.EQUIP_COSTUME_HEAD = False, False
    authsrv.WEAPON_SETS = [{"lead": "starter_hammer", "off": None}, None, None, None]
    authsrv.agents.PLAYER_OFFHAND = None
    authsrv.EXPLORABLE, authsrv.OUTPOST = True, False
    W, EQ, BP = authsrv.WEAPON_ITEM_ID, authsrv.EQUIPPED_BAG_ID, authsrv.BACKPACK_BAG_ID

    st = {"agents": {}, "char_uuid": UUID, "map_id": 145}
    items = authsrv.item_layout_begin(st, 0)
    expect_default = {W: (EQ, authsrv.EQUIPPED_SLOT_WEAPON)}
    expect_default.update({iid: (EQ, slot) for iid, _k, slot in authsrv.STARTER_ARMOUR})
    led.ok({k: (v["bag"], v["slot"]) for k, v in items.items()} == expect_default,
           "item_layout_begin's default layout is the constants': the weapon at equipped 0 and "
           "the five STARTER_ARMOUR pieces at their slots", f"{ {k: (v['bag'], v['slot']) for k, v in items.items()} }")
    legacy = [0] * authsrv.VISUAL_EQUIPMENT_SLOTS
    legacy[0] = W
    for iid, _k, slot in authsrv.STARTER_ARMOUR:
        legacy[slot] = iid
    led.ok(itemstore.worn_array(items, EQ, authsrv.VISUAL_EQUIPMENT_SLOTS) == legacy,
           "itemstore.worn_array over the default layout == the 0x006E fill the load path built "
           "before this step (byte-identity of the array)", f"{itemstore.worn_array(items, EQ)}")
    led.ok(items[W]["key"] == "starter_hammer" and items[W]["item_type"] == 15
           and items[7]["key"] == "warrior_head" and items[7]["item_type"] == 16,
           "the rows carry the content key and the wire type (what the equip's slot is decided from)")
    led.ok(authsrv.instance_is_field(st) is True,
           "--explorable makes this a field (the 0x0199 byte's rule)")
    authsrv.OUTPOST = True
    led.ok(authsrv.instance_is_field(st) is False,
           "...and --outpost WINS over --explorable (a town): no visual -- the case the "
           "reviewer's `visual_always` mutant survived without (ENG-M3)")
    authsrv.OUTPOST = False

    # the real handlers, in a field
    sent, send = fake_send_factory()
    authsrv.handle_item_move([MOVE, 6, BP, 1], send, st, 0)
    led.ok(sent == [(CHG, [1, 7, BP, 1]), (VIS, [authsrv.PLAYER_AGENT_ID, 6, 0])],
           "handle_item_move: the head (equipped 6) to backpack 1 -> 0x014B [1, 7, 2, 1] + "
           "0x006F [player, 6, 0] (a field)", f"{sent}")
    led.ok(items[7]["bag"] == BP and items[7]["slot"] == 1
           and itemstore.worn_array(items, EQ)[6] == 0,
           "...the store moved the head and the 0x006E array now has 0 at visual 6")
    # the damage model follows the store (the fix pass, ENG-B5)
    ar_body = authsrv.player_armour_at("warrior_body", state=st)
    ar_head = authsrv.player_armour_at("warrior_head", state=st)
    led.ok(ar_body is not None and ar_body > 0 and ar_head == 0.0,
           "with the head in the backpack player_armour_at('warrior_head') is 0.0 (a bare "
           "location) while the chest keeps its rating -- the first cut kept the head's 45 "
           "(ENG-B5)", f"head {ar_head} body {ar_body}")
    led.ok(authsrv.player_armour_at("warrior_head", state={"agents": {}}) not in (None, 0.0),
           "CONTROL: with no item layout on the state the fixture's piece counts (the "
           "pre-step path)")
    sent2, send2 = fake_send_factory()
    authsrv.handle_equip_item([EQUIP, 7], send2, st, 0)
    led.ok(sent2 == [(CHG, [1, 7, EQ, 6]), (VIS, [authsrv.PLAYER_AGENT_ID, 6, 7])],
           "handle_equip_item: the head back -> 0x014B [1, 7, 1, 6] + 0x006F [player, 6, 7]", f"{sent2}")
    led.ok(authsrv.player_armour_at("warrior_head", state=st) == ar_body
           or authsrv.player_armour_at("warrior_head", state=st) not in (None, 0.0),
           "...and equipped back, the head protects again",
           f"{authsrv.player_armour_at('warrior_head', state=st)}")
    # the same two in a TOWN: no visual
    authsrv.EXPLORABLE, authsrv.OUTPOST = False, True
    sent3, send3 = fake_send_factory()
    authsrv.handle_item_move([MOVE, 6, BP, 1], send3, st, 0)
    authsrv.handle_equip_item([EQUIP, 7], send3, st, 0)
    led.ok(sent3 == [(CHG, [1, 7, BP, 1]), (CHG, [1, 7, EQ, 6])],
           "in a TOWN (--outpost) the same move and equip send the 0x014B rows and NO 0x006F "
           "(retail: 0 of 5 own-agent visuals in outposts)", f"{sent3}")
    authsrv.EXPLORABLE, authsrv.OUTPOST = True, False
    # refusals through the handler send nothing
    sent4, send4 = fake_send_factory()
    authsrv.handle_item_move([MOVE, 7, BP, 1], send4, st, 0)      # empty source
    authsrv.handle_item_move([MOVE, 6, 99, 1], send4, st, 0)      # undeclared bag
    authsrv.handle_equip_item([EQUIP, 7], send4, st, 0)           # already worn
    authsrv.handle_equip_item([EQUIP, 999], send4, st, 0)         # unknown
    authsrv.handle_item_move([MOVE, 6], send4, st, 0)             # malformed
    authsrv.handle_item_move([MOVE, 6, BP, 1], send4, {"agents": {}}, 0)   # no layout
    led.ok(sent4 == [], "six refusals through the real handlers send NOTHING")

    # the hands mirror
    authsrv.SET_ITEMS_OVERRIDE.clear()
    sent5, send5 = fake_send_factory()
    authsrv.handle_item_move([MOVE, 0, BP, 3], send5, st, 0)      # the hammer out
    led.ok(sent5 == [(CHG, [1, W, BP, 3]), (VIS, [authsrv.PLAYER_AGENT_ID, 0, 0])]
           and itemstore.hand_items(items, EQ) == (0, 0)
           and authsrv.SET_ITEMS_OVERRIDE.get(0) == (0, 0)
           and authsrv.weapon_set_items(0) == (0, 0),
           "the weapon moved out: 0x014B + visual 0 for slot 0, the hands empty, set 0's items "
           "read (0, 0) through the override", f"{sent5} {authsrv.SET_ITEMS_OVERRIDE}")
    led.ok(itemstore.worn_array(items, EQ)[0] == 0, "...and the 0x006E array's slot 0 is 0")
    # select_weapon_set with an emptied hand: set 1 = a sword
    authsrv.configure_weapon_sets(["1=starter_sword"])
    st_b = {"agents": {}, "char_uuid": UUID, "map_id": 145}
    items_b = authsrv.item_layout_begin(st_b, 0)
    led.ok(11 in items_b and items_b[11]["bag"] == BP
           and items_b[11]["slot"] == authsrv.WEAPON_SET_BACKPACK_SLOTS[11],
           "with --weapon-set 1=starter_sword the layout holds set 1's lead (item 11) at its "
           "backpack slot")
    sent6, send6 = fake_send_factory()
    authsrv.handle_item_move([MOVE, 0, BP, 5], send6, st_b, 0)    # hammer out to backpack 5
    authsrv.player_pools(st_b)
    sent7, send7 = fake_send_factory()
    authsrv.select_weapon_set(send7, st_b, 1, 0)
    ops7 = [op for op, _v in sent7]
    led.ok(SWAP not in ops7 and (CHG, [1, 11, EQ, 0]) in sent7
           and not any(op == SWAP and 0 in v for op, v in sent7),
           "select_weapon_set after an emptied hand: the sword ENTERS slot 0 by 0x014B [1, 11, 1, 0] "
           "and no 0x0152 carries a 0 (ItCliApi:2253 asserts item1)", f"{sent7}")
    led.ok(itemstore.hand_items(items_b, EQ) == (11, 0) and items_b[W]["bag"] == BP
           and items_b[W]["slot"] == 5,
           "...and the cells follow: 11 in hand, the hammer still at backpack 5")
    sent8, send8 = fake_send_factory()
    authsrv.select_weapon_set(send8, st_b, 0, 0)                  # back to set 0, whose lead is 0
    led.ok(SWAP not in [op for op, _v in sent8]
           and any(op == CHG and v[1] == 11 and v[2] == BP for op, v in sent8)
           and itemstore.hand_items(items_b, EQ) == (0, 0),
           "back to set 0 (its lead moved out): the sword LEAVES to a free backpack slot by 0x014B, "
           "no 0x0152; the hands are empty again", f"{sent8}")
    # equip back: set 0's record and the swing model follow
    sent9, send9 = fake_send_factory()
    authsrv.handle_equip_item([EQUIP, W], send9, st_b, 0)
    led.ok((CHG, [1, W, EQ, 0]) in sent9 and authsrv.SET_ITEMS_OVERRIDE.get(0) == (W, 0)
           and authsrv.WEAPON_SETS[0]["lead"] == "starter_hammer"
           and authsrv.agents.PLAYER_WEAPON.get("item_type") == 15,
           "the hammer equipped back into the empty slot 0: 0x014B into equipped 0, set 0's items "
           "(1, 0), the record and agents.PLAYER_WEAPON the hammer (apply_party_character)", f"{sent9}")
    sent10, send10 = fake_send_factory()
    authsrv.handle_equip_item([EQUIP, 11], send10, st_b, 0)      # the sword over the hammer
    led.ok(sent10[0] == (SWAP, [1, W, 11]) and sent10[1] == (VIS, [authsrv.PLAYER_AGENT_ID, 0, 11])
           and itemstore.hand_items(items_b, EQ) == (11, 0)
           and authsrv.agents.PLAYER_WEAPON.get("item_type") == 27
           and authsrv.SET_ITEMS_OVERRIDE.get(0) == (11, 0)
           and authsrv.WEAPON_SETS[0]["lead"] == "starter_hammer"
           and authsrv.WEAPON_SETS[1] == {"lead": "starter_sword", "off": None},
           "the sword over the worn hammer (a field): 0x0152 [1, 1, 11] + 0x006F [player, 0, 11]; "
           "the swing model is the sword's (type 27), set 0's ITEMS for this session read (11, 0), "
           "and the LAUNCH records are untouched (the first cut rewrote set 0's to the sword -- "
           "ENG-B4)", f"{sent10} {authsrv.WEAPON_SETS}")
    # a set switch after that equip reads the swing model off the HANDS, not the record
    sent11, send11 = fake_send_factory()
    authsrv.select_weapon_set(send11, st_b, 1, 0)                  # F2: set 1 IS the sword now in hand
    led.ok(not any(op == SWAP for op, _v in sent11)
           and authsrv.agents.PLAYER_WEAPON.get("item_type") == 27
           and itemstore.hand_items(items_b, EQ) == (11, 0),
           "F2 with the sword already in hand: no 0x0152 (nothing to exchange), the swing model "
           "stays the sword's", f"{sent11}")
    sent12, send12 = fake_send_factory()
    authsrv.select_weapon_set(send12, st_b, 0, 0)                  # F1: set 0's items are (11, 0) this session
    led.ok(not any(op == SWAP for op, _v in sent12)
           and authsrv.agents.PLAYER_WEAPON.get("item_type") == 27,
           "F1 back: set 0's items are the sword this session, so the swing model is the "
           "sword's -- NOT the record's hammer (the first cut applied WEAPON_SETS[0] and the "
           "model disagreed with the hand)", f"{sent12} type {authsrv.agents.PLAYER_WEAPON.get('item_type')}")

    # -- the NEXT connection (a zone): the dress re-applies set 0 (the fix pass, ENG-B4) ----
    st_z = {"agents": {}, "char_uuid": UUID, "map_id": 145}
    items_z = authsrv.item_layout_begin(st_z, 0)
    led.ok(items_z[W]["key"] == "starter_hammer" and items_z[W]["item_type"] == 15
           and items_z[11]["key"] == "starter_sword" and items_z[11]["bag"] == BP
           and authsrv.agents.PLAYER_WEAPON.get("item_type") == 15
           and authsrv.SET_ITEMS_OVERRIDE == {},
           "a NEW connection after the equip dresses item 1 as the HAMMER and item 11 as the sword "
           "(the reviewer's probe_zone had two swords and no hammer) and the swing model is set 0's",
           f"{ {k: v['key'] for k, v in items_z.items() if k in (W, 11)} } type {authsrv.agents.PLAYER_WEAPON.get('item_type')}")
    led.ok(authsrv.item_layout_defaults()[W][2] == "starter_hammer"
           and authsrv.weapon_set_items(0) == (W, 0) and authsrv.weapon_set_items(1) == (11, 0),
           "...and the 0x0147 rows name set 0 = (1, 0), set 1 = (11, 0)")
    # the off-hand form: set 0 = sword + shield, the shield dragged out, then a zone
    authsrv.WEAPON_SETS = [{"lead": "starter_hammer", "off": None}, None, None, None]
    authsrv.SET_ITEMS_OVERRIDE.clear()
    authsrv.apply_party_character({"player_weapon": "starter_sword", "player_offhand": "starter_shield"})
    st_o = {"agents": {}, "char_uuid": UUID, "map_id": 145}
    items_o = authsrv.item_layout_begin(st_o, 0)
    sent_o, send_o = fake_send_factory()
    authsrv.handle_item_move([MOVE, 1, BP, 5], send_o, st_o, 0)        # the shield out
    led.ok(sent_o == [(CHG, [1, authsrv.OFFHAND_ITEM_ID, BP, 5]), (VIS, [authsrv.PLAYER_AGENT_ID, 1, 0])]
           and authsrv.agents.PLAYER_OFFHAND is None
           and authsrv.SET_ITEMS_OVERRIDE.get(0) == (W, 0),
           "set 0 = sword + shield: the shield dragged out -> 0x014B + visual 1 = 0; the swing "
           "model drops the shield for this session; set 0's items read (1, 0)", f"{sent_o}")
    st_o2 = {"agents": {}, "char_uuid": UUID, "map_id": 145}
    items_o2 = authsrv.item_layout_begin(st_o2, 0)
    led.ok(authsrv.agents.PLAYER_OFFHAND is not None
           and authsrv.OFFHAND_ITEM_ID in items_o2
           and items_o2[authsrv.OFFHAND_ITEM_ID]["bag"] == EQ
           and authsrv.weapon_set_items(0) == (W, authsrv.OFFHAND_ITEM_ID),
           "the NEXT connection declares the shield again, in hand, and 0x0147 names an item "
           "the dress declared (the reviewer's probe_offhand_zone named item 10 undeclared)",
           f"offhand {authsrv.agents.PLAYER_OFFHAND is not None} items {sorted(items_o2)}")
    authsrv.WEAPON_SETS = [{"lead": "starter_hammer", "off": None}, None, None, None]
    authsrv.agents.PLAYER_OFFHAND = None
    authsrv.apply_party_character({"player_weapon": "starter_hammer"})

    # -- RESERVED cells (the fix pass, ENG-B3) ---------------------------------------------
    authsrv.configure_weapon_sets(["1=starter_sword+starter_shield"])
    st_r = {"agents": {}, "char_uuid": UUID, "map_id": 145}
    items_r = authsrv.item_layout_begin(st_r, 0)
    authsrv.player_pools(st_r)
    sent_r, send_r = fake_send_factory()
    authsrv.select_weapon_set(send_r, st_r, 1, 0)                     # F2: sword + shield into the hands
    res = authsrv.WEAPON_SET_BACKPACK_SLOTS[12]
    led.ok(itemstore.hand_items(items_r, EQ) == (11, 12) and itemstore.at(items_r, BP, res) is None
           and authsrv.reserved_backpack_slots(st_r) == {authsrv.WEAPON_SET_BACKPACK_SLOTS[11], res},
           f"after F2 the shield's return cell (backpack {res}) is EMPTY and RESERVED, with the "
           f"sword's", f"reserved {authsrv.reserved_backpack_slots(st_r)}")
    sent_r.clear()
    authsrv.handle_item_move([MOVE, 6, BP, res], send_r, st_r, 0)     # the head into the reserved cell
    led.ok(sent_r == [] and items_r[7]["bag"] == EQ,
           "a 0x004F into the RESERVED cell is REFUSED with nothing sent (the first cut accepted "
           "it and the next F1 sent 0x014B into a filled cell -- ItCliInv:105)")
    authsrv.handle_item_move([MOVE, 6, BP, 9], send_r, st_r, 0)       # CONTROL: an unreserved cell
    led.ok(len(sent_r) == 2 and items_r[7]["bag"] == BP and items_r[7]["slot"] == 9,
           "CONTROL: the same drag into an unreserved cell is accepted")
    sent_r.clear()
    authsrv.select_weapon_set(send_r, st_r, 0, 0)                     # F1
    cells_r = [(r["bag"], r["slot"]) for r in items_r.values()]
    led.ok((CHG, [1, 12, BP, res]) in sent_r and len(cells_r) == len(set(cells_r)),
           "F1 sends the shield back to its reserved cell and every item has a cell of its own")
    # the RESTORED case: a stored layout puts another item in a hand item's return cell,
    # and the switch chooses a free cell instead (select_weapon_set's fallback)
    itemstore.place(items_r, 7, BP, authsrv.WEAPON_SET_BACKPACK_SLOTS[12])   # the head where the shield returns
    authsrv.select_weapon_set(send_r, st_r, 1, 0)                     # F2 again
    sent_r.clear()
    authsrv.select_weapon_set(send_r, st_r, 0, 0)                     # F1: the shield's cell is filled
    shield_rows = [v for op, v in sent_r if op == CHG and v[1] == 12]
    cells_r = [(r["bag"], r["slot"]) for r in items_r.values()]
    led.ok(len(shield_rows) == 1 and shield_rows[0][2] == BP and shield_rows[0][3] != items_r[7]["slot"]
           and items_r[12]["slot"] == shield_rows[0][3]
           and authsrv.WEAPON_SET_BACKPACK_SLOTS[12] == shield_rows[0][3]
           and len(cells_r) == len(set(cells_r)),
           "with its return cell FILLED (a restored layout) the leaving shield goes to a FREE "
           "cell by 0x014B, the reservation follows, no two items share a cell",
           f"{shield_rows} head at {items_r[7]['slot']}")
    authsrv.WEAPON_SETS = [{"lead": "starter_hammer", "off": None}, None, None, None]
    authsrv._assign_backpack_slots()
    authsrv.SET_ITEMS_OVERRIDE.clear()

    # --persist: the round trip
    authsrv.PERSIST = True
    authsrv.WEAPON_SETS = [{"lead": "starter_hammer", "off": None}, None, None, None]
    authsrv.SET_ITEMS_OVERRIDE.clear()
    authsrv.apply_party_character({"player_weapon": "starter_hammer"})
    store = charstore.Store.open("items@rurik.invalid", base=base)
    store.ensure_character(UUID, "Mover", "ee" * 37)
    stp = {"agents": {}, "char_uuid": UUID, "map_id": 145, "charstore_game": store}
    itp = authsrv.item_layout_begin(stp, 0)
    sentp, sendp = fake_send_factory()
    authsrv.handle_item_move([MOVE, 6, BP, 2], sendp, stp, 0)     # head -> backpack 2
    authsrv.handle_item_move([MOVE, 0, BP, 4], sendp, stp, 0)     # hammer -> backpack 4
    locs = charstore.Store.open("items@rurik.invalid", base=base).item_locations(UUID)
    led.ok(locs == {7: (BP, 2), W: (BP, 4)},
           "under --persist both accepted moves are on disk as item_locations", f"{locs}")
    fresh = {"agents": {}, "char_uuid": UUID, "map_id": 145,
             "charstore_game": charstore.Store.open("items@rurik.invalid", base=base)}
    itf = authsrv.item_layout_begin(fresh, 0)
    led.ok(itf[7]["bag"] == BP and itf[7]["slot"] == 2,
           "a FRESH dress puts the head where it was left (backpack 2)")
    led.ok(itf[W]["bag"] == EQ and itf[W]["slot"] == 0,
           "...but the HAND is restored to its default (the weapon sets own slot 0; said in the log)")
    led.ok(authsrv.item_cell(fresh, 7, EQ, 6) == [BP, 2] and authsrv.item_cell(fresh, 3, EQ, 2) == [EQ, 2]
           and authsrv.item_cell({}, 7, EQ, 6) == [EQ, 6],
           "item_cell hands the dress the stored cell for the head, the default for the body, and "
           "the caller's constants with no layout")
    led.ok(itemstore.worn_array(itf, EQ)[6] == 0 and itemstore.worn_array(itf, EQ)[0] == W,
           "the fresh 0x006E array has no head and the hammer in hand")
    # THE REAL ORDER (the fix pass, ENG-B1): REQUEST_ITEMS -- the dress -- runs
    # BEFORE the load attaches charstore_game (REQUEST_PLAYERS), so a bare
    # state is what item_layout_begin really sees. The first cut read the state
    # and restored nothing on any real connection; the check above pre-seeded
    # the store and could not see it.
    _saved_find = authsrv.charstore.find_character
    _store_disk = charstore.Store.open("items@rurik.invalid", base=base)
    authsrv.charstore.find_character = lambda uuid, base=None: (_store_disk, _store_disk.character_by_uuid(uuid))
    try:
        bare = {"agents": {}, "char_uuid": UUID, "map_id": 145}
        itb = authsrv.item_layout_begin(bare, 0)
        led.ok(itb[7]["bag"] == BP and itb[7]["slot"] == 2 and bare.get("charstore_game") is _store_disk,
               "a BARE state (no charstore_game yet, as REQUEST_ITEMS sees it) still dresses the "
               "head at its stored cell -- the store is looked up here (find_character) and attached",
               f"head at ({itb[7]['bag']}, {itb[7]['slot']}) attached {bare.get('charstore_game') is _store_disk}")
        authsrv.charstore.find_character = lambda uuid, base=None: (None, None)
        bare2 = {"agents": {}, "char_uuid": UUID, "map_id": 145}
        itb2 = authsrv.item_layout_begin(bare2, 0)
        led.ok(itb2[7]["bag"] == EQ and itb2[7]["slot"] == 6 and "charstore_game" not in bare2,
               "KNOWN-BAD / CONTROL: with no store to find the dress is the constants' -- what "
               "every real connection got before this fix")
    finally:
        authsrv.charstore.find_character = _saved_find
    # the RESTORED set-item slot survives declare_weapon_sets (the fix pass, ENG-M2)
    authsrv.configure_weapon_sets(["1=starter_sword+starter_shield"])
    _store_disk.set_item_location(UUID, 12, BP, 7)                    # set 1's shield left at backpack 7
    _store_disk.set_item_location(UUID, W, EQ, 0)                     # the hammer back in hand
    _store_disk.set_item_location(UUID, 7, BP, 1)                     # the head in the shield's default cell
    stm = {"agents": {}, "char_uuid": UUID, "map_id": 145, "charstore_game": _store_disk}
    itm = authsrv.item_layout_begin(stm, 0)
    led.ok(itm[12]["slot"] == 7 and itm[7]["slot"] == 1 and authsrv.WEAPON_SET_BACKPACK_SLOTS[12] == 7,
           "the dress restores set 1's shield at backpack 7 and the slot map follows")
    sentm, sendm = fake_send_factory()
    authsrv.declare_weapon_sets(sendm, stm)
    led.ok([v for op, v in sentm if op == authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION and v[1] == 12] == [[1, 12, BP, 7]]
           and authsrv.WEAPON_SET_BACKPACK_SLOTS[12] == 7,
           "declare_weapon_sets places the shield at (2, 7) AND leaves the slot map at 7 (the first "
           "cut re-assigned it to 1, the head's cell -- ENG-M2)", f"map {dict(authsrv.WEAPON_SET_BACKPACK_SLOTS)}")
    authsrv.player_pools(stm)
    authsrv.select_weapon_set(sendm, stm, 1, 0)
    sentm.clear()
    authsrv.select_weapon_set(sendm, stm, 0, 0)
    led.ok((CHG, [1, 12, BP, 7]) in sentm and itm[7]["slot"] == 1,
           "F2 then F1 sends the shield back to backpack 7, not into the head's cell", f"{sentm}")
    authsrv.WEAPON_SETS = [{"lead": "starter_hammer", "off": None}, None, None, None]
    authsrv._assign_backpack_slots()
    authsrv.SET_ITEMS_OVERRIDE.clear()
    authsrv.ITEM_MOVES_ENABLED = False
    off = {"agents": {}, "char_uuid": UUID, "map_id": 145,
           "charstore_game": charstore.Store.open("items@rurik.invalid", base=base)}
    ito = authsrv.item_layout_begin(off, 0)
    led.ok(ito[7]["bag"] == EQ and ito[7]["slot"] == 6,
           "--no-item-moves: the stored cell is NOT read; the dress is the constants'")
    authsrv.ITEM_MOVES_ENABLED = True
    for bad in ({"7": [2]}, {"7": [-1, 2]}, {"x": [2, 2]}, {"7": [True, 2]}, [1, 2]):
        data = {"version": charstore.STORE_VERSION, "account": {}, "characters": {
            UUID: {"name": "X", "level": 1, "xp": 0, "skill_points": 0, "item_locations": bad}}}
        try:
            charstore.validate(data, "<mem>")
            refused = False
        except ValueError:
            refused = True
        led.ok(refused, f"charstore.validate refuses item_locations = {bad!r}")
    data_ok = {"version": charstore.STORE_VERSION, "account": {}, "characters": {
        UUID: {"name": "X", "level": 1, "xp": 0, "skill_points": 0, "item_locations": {"7": [2, 2]}}}}
    try:
        charstore.validate(data_ok, "<mem>")
        accepted = True
    except ValueError:
        accepted = False
    led.ok(accepted, "CONTROL: validate() accepts item_locations = {'7': [2, 2]}")
    authsrv.PERSIST = False

    # ---- §5 source locks ---------------------------------------------------------------------
    with open(os.path.join(HERE, "authsrv.py"), encoding="utf-8") as f:
        SRC = f.read()
    TREE = ast.parse(SRC)

    def _func(tree, name):
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name == name:
                return n
        return None

    def _calls(node):
        return {c.func.id for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}

    def dispatch_lock(tree, const, flag, handler):
        handle = _func(tree, "handle")
        for n in ast.walk(handle):
            if not (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)):
                continue
            t = n.test
            if not (isinstance(t.left, ast.Name) and t.left.id == "opcode"
                    and len(t.comparators) == 1
                    and isinstance(t.comparators[0], ast.Name)
                    and t.comparators[0].id == const):
                continue
            inner = [s for s in n.body if isinstance(s, ast.If)]
            direct = any(handler in _calls(s) for s in n.body if not isinstance(s, ast.If))
            return (len(inner) == 1 and not direct
                    and isinstance(inner[0].test, ast.Name) and inner[0].test.id == flag
                    and any(handler in _calls(s) for s in inner[0].body)
                    and not any(handler in _calls(s) for s in inner[0].orelse))
        return False

    led.ok(dispatch_lock(TREE, "GAME_CMSG_ITEM_MOVE", "ITEM_MOVES_ENABLED", "handle_item_move")
           and dispatch_lock(TREE, "GAME_CMSG_EQUIP_ITEM", "ITEM_MOVES_ENABLED", "handle_equip_item"),
           "LOCK: both arms call their handler ONLY under `if ITEM_MOVES_ENABLED:`")
    led.ok(SRC.count("if ITEM_MOVES_ENABLED:") == 2, "the two arms' conditions appear twice")
    mut = ast.parse(SRC.replace("if ITEM_MOVES_ENABLED:", "if True:", 1))
    led.ok(not dispatch_lock(mut, "GAME_CMSG_ITEM_MOVE", "ITEM_MOVES_ENABLED", "handle_item_move"),
           "KNOWN-BAD: an arm that ignores the flag fails the lock")
    main_fn = _func(TREE, "main")
    wired = any(isinstance(n, ast.If) and isinstance(n.test, ast.Attribute)
                and n.test.attr == "no_item_moves"
                and any(isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Name)
                        and s.targets[0].id == "ITEM_MOVES_ENABLED"
                        and isinstance(s.value, ast.Constant) and s.value.value is False
                        for s in n.body)
                for n in ast.walk(main_fn))
    led.ok(wired and _saved["ITEM_MOVES_ENABLED"] is True,
           "LOCK: main() wires --no-item-moves to ITEM_MOVES_ENABLED = False, and the default is ON")
    handle_src = ast.get_source_segment(SRC, _func(TREE, "handle"))
    i_begin = handle_src.find("item_layout_begin(state, conn_id)")
    i_wpn = handle_src.find('"CREATE_NAMED_ITEM(the player\'s weapon)"')
    led.ok(0 < i_begin < i_wpn,
           "LOCK: the dress calls item_layout_begin BEFORE the weapon's create")
    led.ok(handle_src.count("item_cell(state, ") == 5
           and "declare_weapon_sets(send, state)" in handle_src,
           "LOCK: the five placements (weapon, off hand, armour, costume, costume head) read item_cell "
           "and declare_weapon_sets gets the state",
           f"item_cell x{handle_src.count('item_cell(state, ')}")
    dws = ast.get_source_segment(SRC, _func(TREE, "declare_weapon_sets"))
    led.ok("item_cell(state, item_id, BACKPACK_BAG_ID, slot)" in dws,
           "LOCK: declare_weapon_sets places a set item at its decided cell")
    players_src = ast.get_source_segment(SRC, _func(TREE, "_handle_request_players"))
    led.ok("itemstore.worn_array(state[\"items\"], EQUIPPED_BAG_ID," in players_src
           and 'if state.get("items"):' in players_src
           and "itemstore.hand_items(state[\"items\"], EQUIPPED_BAG_ID)[0]" in players_src,
           "LOCK: the 0x006E build reads itemstore.worn_array when a layout exists (the constants' "
           "fill is the fallback) and NPC_UPDATE_WEAPONS reads the hand")
    wsi = ast.get_source_segment(SRC, _func(TREE, "weapon_set_items"))
    led.ok(wsi.index("SET_ITEMS_OVERRIDE") < wsi.index("if k == 0:"),
           "LOCK: weapon_set_items reads SET_ITEMS_OVERRIDE before the constants")
    sws = ast.get_source_segment(SRC, _func(TREE, "select_weapon_set"))
    led.ok("if old_lead and new_lead and old_lead != new_lead:" in sws
           and "elif new_lead and not old_lead:" in sws
           and "item_cells_after_set_switch" in _calls(_func(TREE, "select_weapon_set")),
           "LOCK: select_weapon_set swaps only two REAL leads, enters an empty hand by 0x014B, and "
           "mirrors the cells")
    # the fix pass's locks
    ilb = ast.get_source_segment(SRC, _func(TREE, "item_layout_begin"))
    led.ok("charstore.find_character" in ilb and "apply_party_character" in _calls(_func(TREE, "item_layout_begin"))
           and ilb.index("apply_party_character") < ilb.index("item_layout_defaults()"),
           "LOCK: item_layout_begin looks the store up itself (ENG-B1) and re-applies set 0's record "
           "BEFORE reading the layout (ENG-B4)")
    mir = ast.get_source_segment(SRC, _func(TREE, "_item_hands_mirror"))
    led.ok("record_set0=False" in mir and "WEAPON_SETS[k] =" not in mir and "record_set0=(k == 0)" not in mir,
           "LOCK: _item_hands_mirror never rewrites a launch-level set record (ENG-B4)")
    dws2 = ast.get_source_segment(SRC, _func(TREE, "declare_weapon_sets"))
    led.ok('if not (state or {}).get("items"):' in dws2
           and dws2.index('if not (state or {}).get("items"):') < dws2.index("_assign_backpack_slots()"),
           "LOCK: declare_weapon_sets re-assigns the slot map only when no layout ran (ENG-M2)")
    led.ok("reserved_backpack_cells" in _calls(_func(TREE, "handle_item_move"))
           and "reserved_backpack_cells" in _calls(_func(TREE, "handle_equip_item"))
           and "reserved_backpack_slots" in _calls(_func(TREE, "select_weapon_set")),
           "LOCK: both handlers pass the reserved cells to the planner and the set switch avoids "
           "them (ENG-B3)")
    paa = ast.get_source_segment(SRC, _func(TREE, "player_armour_at"))
    led.ok("armour_item_id_at" in _calls(_func(TREE, "player_armour_at"))
           and 'state.get("items")' in paa and "return 0.0 + offhand_armour(damage_type, state)" in paa,
           "LOCK: player_armour_at reads the item store and a removed piece leaves a bare location "
           "(ENG-B5)")
    with open(os.path.join(HERE, "test_dispatch.py"), encoding="utf-8") as f:
        TD = f.read()
    led.ok("    0x004F: " not in TD and "    0x0030: " not in TD,
           "LOCK: test_dispatch's allowlist carries no row for 0x004F or 0x0030 (both armed)")
    with open(os.path.join(HERE, "serverargs.py"), encoding="utf-8") as f:
        ARGS = f.read()
    led.ok('"--no-item-moves"' in ARGS, "LOCK: serverargs.py defines --no-item-moves")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    authsrv.agents.PLAYER_OFFHAND = _saved_off
    authsrv.agents.PLAYER_WEAPON = _saved_wpn
    authsrv.WEAPON_SET_BACKPACK_SLOTS.clear()
    authsrv.WEAPON_SET_BACKPACK_SLOTS.update(_saved_slots)
    authsrv.SET_ITEMS_OVERRIDE.clear()
    authsrv.SET_ITEMS_OVERRIDE.update(_saved_over)
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
