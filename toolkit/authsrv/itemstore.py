r"""Where the player's items ARE -- bag and slot -- and the two client actions that
move them: c2s 0x004F ITEM_MOVE (an item leaving the EQUIPPED bag for a cell)
and c2s 0x0030 EQUIP_ITEM (an item entering it). DESKWORK-D1 step 8,
studies/cmsg/FINDINGS.md DESKWORK-D1 "Inventory".

Pure: a dict of items, a dict of bag sizes, and functions that PLAN a reply
batch as [(opcode, values, label)] and the cell changes to apply, or refuse
with a reason. No server import, no sockets, so every retail batch on disk can
be replayed here byte for byte with retail's own ids -- and the server's own
ids on the same code.

WHAT THE TWO MESSAGES ARE, read from the client (build 38797) and the tapes:

  * 0x004F [byte slot, word bag, byte slot] is sent by GmItemHelpers'
    equipped-bag move (0x00526900; asserts `sourceItemId` :279,
    `ItemCliValidate(sourceItemId)` :280, `quantity` :281, `targetBag <
    ITEM_BAG_SLOTS` :282). Its GATE is 0x008454F0(item): the item's PARENT
    bag (item+0xC) must be of type 2 -- the EQUIPPED bag -- and the answer
    is then the item's slot byte (item+0x50); for any other bag it answers 9
    and 0x00526900 branches to the local path at 0x00526AC3 and sends
    nothing. It packs (that slot, the target bag's id, the target slot). So
    field 1 is the item's SOURCE SLOT in the equipped bag, and the source bag
    is implied. (The first cut read the gate as "the item's bag has model
    21": 0x00844800 writes 21 as its DEFAULT for any item that is not itself
    a bag container -- the `cmp [ebp+8], 0x15` at 0x0052698C only refuses a
    dragged bag, a non-empty one at 0x0052699C -- so a backpack sword gets 21
    too; the fix pass, EVID-D1C-2. Same conclusion, different mechanism.)
    CORROBORATED 4 of 4 on retail: each moved item sat at (equipped bag,
    field 1) when the move came -- 20260917T090355 :53310 213@(3,4) /
    215@(3,6) / 214@(3,5) from the load's 0x013E, moved as [4,2,1] / [6,2,2]
    / [5,2,3]; 20260919T103604 :58638 17730, set 0's off hand, loaded at
    (231,1) at 90.764, LEFT it on the set-1 switch (0x014B [241,17730,136,1]
    at 150.310), and came BACK to it by the 0x0152 [241,13467,17730] at
    224.681 (13467 having been put at (231,1) by a 0x013E at 176.813), before
    [1,136,6] moved it at 232.975 -- that chain, not the load cell, is its
    witness (EVID-D1C-7). The general bag-to-bag move is another message and
    is on no tape.
  * 0x0030 [dword item] is GmItemHelpers' equip for the player (0x00526860;
    the hero form is 0x0031 [agent, item]).

WHAT RETAIL ANSWERS (the batches this module reproduces):

  * a move:  0x014B [key, item, bag, slot]           (4 of 4)
             + 0x006F [agent, visual slot, 0]        (3 of 4 -- see VISUALS)
  * an equip into an EMPTY slot:
             0x014B [key, item, equipped bag, slot]  (4 of 4, all in a field)
             + 0x006F [agent, visual slot, item]
  * an equip onto an OCCUPIED slot:
             0x0152 [key, occupant, item] ALONE      (4 of 4, all in an outpost)
    -- the client's handler exchanges the two items' bag and slot
    (ItCliInv:687/688 both in a bag, :621 removed, :105 added to an EMPTY
    slot; studies/weapons/PLAN.md 29), so the occupant lands in the cell the
    item came from.

VISUALS. 0x006F rode every own-agent equip and unequip in a FIELD (7 of 7)
and none in an OUTPOST (0 of 5: the four swaps and the off-hand unequip).
Whether the rule is the outpost or the swap is CONFOUNDED for the swaps; the
outpost unequip breaks the tie toward the outpost, and that is what `visuals`
means to the callers: True in a field. The mechanism is UNVERIFIED.

TWO SLOT ORDERS, and both lineages were right about DIFFERENT arrays. The
equipped BAG's cells on retail follow ldufr's order (Legs 3, Head 4, Boots
5, Gloves 6: the equips put head 213 at bag slot 4 with visual 6, gloves 215
at 6 with visual 5, boots 214 at 5 with visual 3), while the 0x006E/0x006F
VISUAL array follows GWLP-R's (Boots 3, Legs 4, Gloves 5, Head 6;
studies/newopcodes 0x006F). `RETAIL_VISUAL_OF_BAG_SLOT` is that permutation,
OBSERVED on the three armour pieces and the identity on 0, 1, 2, 7, 8. This
server puts its armour into the equipped bag at the VISUAL slot (STARTER_ARMOUR
and wearmap.SLOT_*), which the client accepts because a bag cell is opaque to
it, so OUR mapping is the identity (`visual_of_bag_slot`).

Standard library only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import wearmap                                              # noqa: E402

GAME_SMSG_ITEM_CHANGE_LOCATION = 0x014B
GAME_SMSG_ITEM_SWAP_LOCATIONS = 0x0152
GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT = 0x006F

SLOT_WEAPON = wearmap.SLOT_WEAPON
SLOT_OFFHAND = wearmap.SLOT_OFFHAND
EQUIPPED_SLOTS = 9

# Wire item type -> the equipped-bag slot an EQUIP puts it in (our layout, the
# visual order). Armour from wearmap's canonical slot per type; the costume
# pair from its two slots. Weapons are decided by their type's `hands` row
# (content/world.toml [weapon_type.*]) through `slot_of_type`.
ARMOUR_SLOT_OF_TYPE = {
    wearmap.WIRE_TYPE_BODY: wearmap.SLOT_BODY,
    wearmap.WIRE_TYPE_BOOTS: wearmap.SLOT_BOOTS,
    wearmap.WIRE_TYPE_LEGS: wearmap.SLOT_LEGS,
    wearmap.WIRE_TYPE_GLOVES: wearmap.SLOT_GLOVES,
    wearmap.WIRE_TYPE_HEAD: wearmap.SLOT_HEAD,
    wearmap.WIRE_TYPE_COSTUME_BODY: wearmap.SLOT_COSTUME_BODY,
    wearmap.WIRE_TYPE_COSTUME_HEAD: wearmap.SLOT_COSTUME_HEAD,
}

# Retail's equipped-bag slot -> its visual (0x006E/0x006F) position: ldufr's
# bag order read through GWLP-R's visual order. OBSERVED for the WHOLE
# permutation on 20260917T090355 :53310's load (the fix pass, EVID-D1C-6):
# 0x013E put items 209..215 at (3,0)..(3,6) and the 0x006E that followed was
# [25, 209, 210, 211, 214, 212, 215, 213, 0, 0] -- so bag 0->0, 1->1, 2->2,
# 3->4 (legs), 4->6 (head), 5->3 (boots), 6->5 (gloves); the three unequips
# and re-equips later on the same tape agree (head 4 -> 6, gloves 6 -> 5,
# boots 5 -> 3). 7 and 8 (the costume pair) are the identity by assumption:
# no tape carries a costume in a bag cell.
RETAIL_VISUAL_OF_BAG_SLOT = {0: 0, 1: 1, 2: 2, 3: 4, 4: 6, 5: 3, 6: 5, 7: 7, 8: 8}
# Retail's equipped-bag slot per armour wire type -- ldufr's order (Body 2,
# Legs 3, Head 4, Boots 5, Gloves 6), OBSERVED on the three :53310 re-equips
# (head 16 -> 4, gloves 13 -> 6, boots 4 -> 5); the costume pair by their
# visual slots (unobserved in a bag cell). The replay of retail's equips passes
# this as `bag_slot_of_type`; the server's own layout uses ARMOUR_SLOT_OF_TYPE.
RETAIL_BAG_SLOT_OF_TYPE = {
    wearmap.WIRE_TYPE_BODY: 2, wearmap.WIRE_TYPE_LEGS: 3, wearmap.WIRE_TYPE_HEAD: 4,
    wearmap.WIRE_TYPE_BOOTS: 5, wearmap.WIRE_TYPE_GLOVES: 6,
    wearmap.WIRE_TYPE_COSTUME_BODY: 7, wearmap.WIRE_TYPE_COSTUME_HEAD: 8,
}


def visual_of_bag_slot(slot):
    """OUR server's mapping: the identity (armour sits at its visual slot)."""
    return int(slot)


def retail_visual_of_bag_slot(slot):
    return RETAIL_VISUAL_OF_BAG_SLOT[int(slot)]


def place(items, item_id, bag, slot, key=None, kind=None, item_type=None):
    """Record (or move) one item's cell. `key` is the content template key
    (None for an item of retail's), `kind` a caller's label, `item_type` the
    wire type byte when known."""
    items[int(item_id)] = {"bag": int(bag), "slot": int(slot), "key": key,
                           "kind": kind, "item_type": item_type}
    return items[int(item_id)]


def at(items, bag, slot):
    """The item id in a cell, or None."""
    for iid, row in items.items():
        if row["bag"] == int(bag) and row["slot"] == int(slot):
            return iid
    return None


def in_bag(items, bag):
    """{slot: item_id} for one bag."""
    return {row["slot"]: iid for iid, row in items.items() if row["bag"] == int(bag)}


def first_free(items, bag, size, avoid=()):
    """The lowest empty slot of a bag, or None when it is full."""
    used = set(in_bag(items, bag)) | set(avoid)
    for s in range(int(size)):
        if s not in used:
            return s
    return None


def slot_of_type(item_type, hands_of_type, bag_slot_of_type=None):
    """The equipped-bag slot an item of this wire type is worn in, or None.

    `hands_of_type` maps a weapon type -> "one" / "two" / "off" / "npc" (the
    server's WEAPON_TYPE_ROW rows). A one- or two-handed weapon goes to slot
    0, an off-hand item to slot 1, armour and costumes per `bag_slot_of_type`
    (ARMOUR_SLOT_OF_TYPE, the server's visual-order layout, when None;
    RETAIL_BAG_SLOT_OF_TYPE replays retail's ldufr-order bag); an "npc"-only
    type (a body's, never a player's) and an unknown type have no slot -- the
    caller refuses."""
    if item_type is None:
        return None
    t = int(item_type)
    armour = ARMOUR_SLOT_OF_TYPE if bag_slot_of_type is None else bag_slot_of_type
    if t in armour:
        return armour[t]
    hands = (hands_of_type or {}).get(t)
    if hands in ("one", "two"):
        return SLOT_WEAPON
    if hands == "off":
        return SLOT_OFFHAND
    return None


def worn_array(items, equipped_bag, n=EQUIPPED_SLOTS, visual_of=visual_of_bag_slot):
    """The 0x006E array: the equipped bag's contents by visual position."""
    worn = [0] * n
    for iid, row in items.items():
        if row["bag"] == int(equipped_bag) and 0 <= row["slot"] < n:
            worn[visual_of(row["slot"])] = iid
    return worn


def hand_items(items, equipped_bag):
    """(lead item id or 0, off-hand item id or 0)."""
    return (at(items, equipped_bag, SLOT_WEAPON) or 0,
            at(items, equipped_bag, SLOT_OFFHAND) or 0)


def plan_move(items, bags, src_slot, dst_bag, dst_slot, *, key, equipped_bag,
              agent, visuals, visual_of=visual_of_bag_slot, reserved_cells=()):
    """c2s 0x004F [src_slot, dst_bag, dst_slot] -> (batch, changes, None) or
    (None, None, reason). `changes` is [(item, bag, slot)] to apply on send.

    Refused (retail's refusal reply NOT FOUND, so nothing is sent): no item in
    that equipped slot; a destination that is the equipped bag itself
    (unobserved -- the equip is how an item enters it); a bag this launch
    never declared; a slot past the bag's size; an OCCUPIED destination --
    the client's add worker asserts the slot empty (ItCliInv:105), so a
    0x014B into a filled cell would assert the client rather than swap; a
    RESERVED destination (`reserved_cells`, {(bag, slot)}: the cells the
    caller's set machinery will send a worn set item back to -- the fix pass,
    ENG-B3: filling one meant the next set switch sent 0x014B into a filled
    cell).
    """
    src_slot, dst_bag, dst_slot = int(src_slot), int(dst_bag), int(dst_slot)
    item = at(items, equipped_bag, src_slot)
    if item is None:
        return None, None, (f"no item in equipped slot {src_slot} "
                            f"(worn: {sorted(in_bag(items, equipped_bag).items())})")
    if dst_bag == int(equipped_bag):
        return None, None, (f"destination is the equipped bag itself (slot {dst_slot}); "
                            f"a move within it is UNOBSERVED -- an equip is how an item "
                            f"enters it")
    if dst_bag not in bags:
        return None, None, f"bag {dst_bag} was never declared ({sorted(bags)})"
    if not 0 <= dst_slot < int(bags[dst_bag]):
        return None, None, f"slot {dst_slot} outside bag {dst_bag}'s 0..{int(bags[dst_bag]) - 1}"
    occupant = at(items, dst_bag, dst_slot)
    if occupant is not None:
        return None, None, (f"bag {dst_bag} slot {dst_slot} holds item {occupant}; the "
                            f"client's add worker asserts the destination EMPTY "
                            f"(ItCliInv:105), and retail's own reply to a filled cell "
                            f"is NOT FOUND")
    if (dst_bag, dst_slot) in set(reserved_cells or ()):
        return None, None, (f"bag {dst_bag} slot {dst_slot} is RESERVED for a worn set "
                            f"item's return (the set switch sends 0x014B there, and the "
                            f"client asserts that cell EMPTY, ItCliInv:105)")
    batch = [(GAME_SMSG_ITEM_CHANGE_LOCATION, [int(key), item, dst_bag, dst_slot],
              f"ITEM_CHANGE_LOCATION(item {item}: equipped {src_slot} -> bag "
              f"{dst_bag} slot {dst_slot}) [DESKWORK-D1 step 8]")]
    if visuals:
        batch.append((GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT,
                      [int(agent), visual_of(src_slot), 0],
                      f"AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT(slot {visual_of(src_slot)} "
                      f"emptied) [DESKWORK-D1 step 8]"))
    return batch, [(item, dst_bag, dst_slot)], None


def plan_equip(items, bags, item_id, *, key, equipped_bag, backpack_bag, agent,
               visuals, hands_of_type, visual_of=visual_of_bag_slot,
               bag_slot_of_type=None, reserved_cells=()):
    """c2s 0x0030 [item] -> (batch, changes, None) or (None, None, reason).

    The slot is the item's TYPE's (slot_of_type). An occupied slot answers
    with 0x0152 [key, occupant, item] -- the occupant takes the item's old
    cell (the client does the same exchange) -- and, in a field, the visual;
    an empty slot with 0x014B + the visual. A TWO-HANDED lead entering while
    an off hand is worn sends the off hand to the backpack's first free slot
    FIRST (0x014B, then its visual 0) -- RECONSTRUCTION from the set switch's
    shape, where a shield LEAVING the hands goes out before one entering
    (studies/weapons/PLAN.md 27); retail's own two-hander-over-shield equip is
    on no tape. Refused: an unknown item, an item already in the equipped
    bag, a type with no slot, an off-hand item while a two-handed lead is
    worn (retail's answer NOT FOUND), no free backpack slot for a displaced
    off hand. `reserved_cells` ({(bag, slot)}) are never chosen for the
    displaced off hand (the fix pass, ENG-B3).
    """
    item_id = int(item_id)
    row = items.get(item_id)
    if row is None:
        return None, None, f"item {item_id} is not one this connection declared"
    if row["bag"] == int(equipped_bag):
        return None, None, (f"item {item_id} is already in the equipped bag (slot "
                            f"{row['slot']}); re-equipping a worn item is UNOBSERVED")
    slot = slot_of_type(row.get("item_type"), hands_of_type, bag_slot_of_type)
    if slot is None:
        return None, None, (f"item {item_id} (wire type {row.get('item_type')}) has no "
                            f"equipped slot this server knows")
    hands = (hands_of_type or {}).get(int(row.get("item_type") or -1))
    batch, changes = [], []
    lead, off = hand_items(items, equipped_bag)
    if slot == SLOT_OFFHAND and lead:
        lead_row = items.get(lead) or {}
        if (hands_of_type or {}).get(int(lead_row.get("item_type") or -1)) == "two":
            return None, None, (f"a two-handed lead (item {lead}) is worn; retail's "
                                f"answer to an off hand equipped beside it is NOT FOUND")
    if slot == SLOT_WEAPON and hands == "two" and off:
        free = first_free(items, backpack_bag, bags.get(backpack_bag, 0),
                          avoid={s for b, s in (reserved_cells or ()) if b == int(backpack_bag)})
        if free is None:
            return None, None, (f"no free backpack slot for the displaced off hand "
                                f"{off}")
        batch.append((GAME_SMSG_ITEM_CHANGE_LOCATION, [int(key), off, int(backpack_bag), free],
                      f"ITEM_CHANGE_LOCATION(off hand {off} -> backpack {free}; a "
                      f"two-handed lead enters) [DESKWORK-D1 step 8, RECONSTRUCTION]"))
        if visuals:
            batch.append((GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT,
                          [int(agent), visual_of(SLOT_OFFHAND), 0],
                          "AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT(off hand emptied) "
                          "[DESKWORK-D1 step 8]"))
        changes.append((off, int(backpack_bag), free))
    occupant = at(items, equipped_bag, slot)
    if occupant is not None:
        batch.append((GAME_SMSG_ITEM_SWAP_LOCATIONS, [int(key), occupant, item_id],
                      f"ITEM_SWAP_LOCATIONS(item {occupant} <-> {item_id}: {item_id} "
                      f"into equipped {slot}, {occupant} to bag {row['bag']} slot "
                      f"{row['slot']}) [DESKWORK-D1 step 8]"))
        changes.append((occupant, row["bag"], row["slot"]))
    else:
        batch.append((GAME_SMSG_ITEM_CHANGE_LOCATION, [int(key), item_id, int(equipped_bag), slot],
                      f"ITEM_CHANGE_LOCATION(item {item_id}: bag {row['bag']} slot "
                      f"{row['slot']} -> equipped {slot}) [DESKWORK-D1 step 8]"))
    if visuals:
        batch.append((GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT,
                      [int(agent), visual_of(slot), item_id],
                      f"AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT(slot {visual_of(slot)} = item "
                      f"{item_id}) [DESKWORK-D1 step 8"
                      + (", RECONSTRUCTION -- retail's four swaps were in an outpost"
                         if occupant is not None else "") + "]"))
    changes.append((item_id, int(equipped_bag), slot))
    return batch, changes, None


def apply(items, changes):
    """Move the items a plan named; returns the ids whose cell changed."""
    moved = []
    for iid, bag, slot in changes:
        row = items.get(int(iid))
        if row is None:
            continue
        if (row["bag"], row["slot"]) != (int(bag), int(slot)):
            row["bag"], row["slot"] = int(bag), int(slot)
            moved.append(int(iid))
    return moved


def restore(defaults, stored, bags, equipped_bag, keep_hands=True):
    """The login layout: `defaults` {item: (bag, slot)} for this launch's
    items, `stored` the character's saved cells. Returns (decided, notes).

    A stored cell wins for an item this launch declares; an id the launch does
    not declare is ignored. `keep_hands`: a stored cell that would change
    what sits in equipped slots 0 or 1 (or move a hand item elsewhere) is NOT
    applied -- the hands belong to the weapon-set machinery (WEAPONS-W9) and
    a restored hand change is an open edge, said in `notes`. A stored cell
    outside the declared bags, or two items on one cell, discards the WHOLE
    store for this login (the defaults stand) with the reason in `notes`.
    """
    notes = []
    decided = dict(defaults)
    hand_cells = {(int(equipped_bag), SLOT_WEAPON), (int(equipped_bag), SLOT_OFFHAND)}
    for iid, cell in (stored or {}).items():
        iid = int(iid)
        if iid not in defaults:
            continue
        cell = (int(cell[0]), int(cell[1]))
        if keep_hands and (cell in hand_cells or tuple(defaults[iid]) in hand_cells):
            if cell != tuple(defaults[iid]):
                notes.append(f"item {iid}: stored at bag {cell[0]} slot {cell[1]}, "
                             f"default {defaults[iid]} -- a HAND cell, not restored "
                             f"(the weapon sets own slots 0/1; open edge)")
            continue
        decided[iid] = cell
    for iid, (bag, slot) in decided.items():
        if bag not in bags or not 0 <= slot < int(bags[bag]):
            notes.append(f"item {iid}: bag {bag} slot {slot} is not a cell of this "
                         f"launch -- the whole stored layout is IGNORED")
            return dict(defaults), notes
    seen = {}
    for iid, cell in decided.items():
        if cell in seen:
            notes.append(f"items {seen[cell]} and {iid} both stored at bag {cell[0]} "
                         f"slot {cell[1]} -- the whole stored layout is IGNORED")
            return dict(defaults), notes
        seen[cell] = iid
    return decided, notes
