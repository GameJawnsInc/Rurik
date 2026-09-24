"""The TOWN body's hands: in an outpost the player's WORLD body carries no
weapon, on retail, ever -- the lead hand (0x006E / 0x006F visual 0) and the
off hand (visual 1) are empty on every outpost body and no outpost hand
change is answered with a 0x006F -- while the paper doll (the equipped BAG)
still holds the weapon (DESKWORK-D1, the town weapon, 2026-09-23;
studies/cmsg/FINDINGS.md "The town weapon").

WHERE EVERY NUMBER HERE COMES FROM (`livewire.decode_conn` over every
origin=LIVE game connection, 96 of 96 decoding closed; the regime is the
0x0199 INSTANCE_LOAD_INFO byte -- 47 outpost connections, 44 field, 5 with
no 0x0199; reproduced by test_townweapon.py section 2):

  * THE LOAD (0x006E [agent, lead, off, five armour, two costumes]).
    OUTPOST: 2,245 bodies -- 2,195 strangers and the owner's OWN body on 50
    loads -- and visual 0 AND visual 1 are zero on ALL of them. The own body
    is the 0x006E whose armour ids all sit in ONE type-2 (equipped) bag of
    the connection (a hero's equipped bag is type 2 too: 4 connections carry
    more than one, and the first pass of this census counted a hero's shield
    as the player's); that bag holds a lead on all 50 outpost loads (28 lead
    only, 22 lead + off hand). FIELD: 48 own loads -- 8 with no bag weapon
    carry none, 17 with a lead alone carry visual 0 and leave 1 empty, 23
    with lead + off hand carry both: 40 of 40 leads, 23 of 23 off hands. So
    the array reflects the bag in a field and is empty-handed in a town:
    OBSERVED, per regime, on the owner's own body under one inventory.
  * THE CHANGES (0x006F [agent, slot, item]). Fourteen outpost hand changes
    are on tape and NONE carries a hand 0x006F: the four weapon-set switches
    (c2s 0x0032 on 20260919T103604 :58638 at t=150.257 / 159.967 / 172.746 /
    224.632 -- 0x0148 then 0x014B / 0x0152 only), the four double-click
    equips of a weapon onto the occupied lead hand (c2s 0x0030 on
    20260819T132414 :53419 -- 0x0152 alone), the off hand dragged out (c2s
    0x004F on :58638 -- 0x014B alone) and the PvP equipment panel's five
    creations straight into equipped slot 0 or 1 (c2s 0x0086 on :58638 --
    axe 23247, scythe 12689, spear 13633, shield 13467, spear 23652). In a
    FIELD the four switches (:56576, agent 25, RUN-WEAPONS-1A) each carry the
    hands' 0x006F (0x006F [25, 0, 209]; ... [25, 1, 207] and [25, 1, 0]).
    THE RULE IS THE SLOT, NOT THE REGIME: the same PvP panel in the same
    outpost created a HEAD piece (23284, type 16, into equipped (843, 4) on
    20260917T160915 :58557 at t=73.5) and retail sent 0x006F [336, 6, 23284]
    for it -- the one outpost 0x006F on an own body. Armour visuals are
    written in a town; the hands are not.
  * WHY THE SERVER MUST DO IT: the client's 0x006E / 0x006F handlers reach
    the AvApi dresser (0x007DFCE0) through ChCliApi message workers with no
    regime test on the path (visstatus.py's reader census; the display-mode
    pass), and our own town body stood armed on every run before this day
    because our 0x006E said so. Shape OBSERVED; mechanism (the server strips
    rather than the client ignoring) RECONSTRUCTION from that negative.
  * WHAT THIS DOES NOT TOUCH: the equipped BAG (0x013E / 0x014B / 0x0152 --
    the doll and the weapon-set panel read it, and retail's outpost switches
    still moved the items), the 0x0147 / 0x0148 set declarations, the
    server's own swing model (a town never swings), and NPC bodies -- retail's
    outpost NPCs DO carry weapons in 0x006D (466 of 1,653 with a lead), so an
    NPC's hands are not this rule's. Heroes have no body in a town on retail
    (3 party heroes over the outpost connections, none created, none with a
    0x006D) or on ours (PARTY_BODY_IN_OUTPOST).

Standard library only; a leaf (no repo import).
"""

# The 0x006E / 0x006F visual positions of the two hands (studies/newopcodes
# 0x006F; weaponcensus.py: slot 0 the lead hand, 1 the off hand).
HAND_LEAD = 0
HAND_OFF = 1
HAND_SLOTS = (HAND_LEAD, HAND_OFF)
HAND_NAMES = {HAND_LEAD: "lead hand", HAND_OFF: "off hand"}


def hands_shown(explorable):
    """Does the WORLD body carry its hands in this regime? A field does
    (40 of 40 leads, 23 of 23 off hands on the own body); a town never
    (0 of 2,245 bodies). OBSERVED."""
    return bool(explorable)


def drops(slot, explorable):
    """Is a player 0x006F into this visual slot withheld here? The hands in
    a town (retail sent none on 14 of 14 outpost hand changes); nothing in a
    field; never an armour or costume slot (the town's one own-body 0x006F
    was the head's)."""
    return int(slot) in HAND_SLOTS and not hands_shown(explorable)


def strip_hands(worn, explorable):
    """The 0x006E array the WORLD sees under this regime: a copy of `worn`
    with visuals 0 and 1 zeroed in a town, untouched in a field. Returns
    (array, [(slot, item id it hid)]) -- an empty hand reports nothing."""
    out = list(worn)
    hid = []
    if hands_shown(explorable):
        return out, hid
    for slot in HAND_SLOTS:
        if slot < len(out) and out[slot]:
            hid.append((slot, out[slot]))
            out[slot] = 0
    return out, hid


def filter_hand_writes(writes, explorable):
    """The per-slot writes the WORLD may see: `writes` is [(slot, item)];
    in a town a write into visual 0 or 1 is DROPPED (not zeroed -- retail
    sends nothing), every other write passes in order. Returns
    (kept, dropped)."""
    kept, dropped = [], []
    for slot, item in writes:
        if drops(slot, explorable):
            dropped.append((int(slot), int(item)))
        else:
            kept.append((int(slot), int(item)))
    return kept, dropped
