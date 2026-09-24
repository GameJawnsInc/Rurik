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
  * THE CARRIER (read from the binary and matched to CONFIRM-2's frames,
    2026-09-24; CORROBORATED for the town, with OBSERVED owed to the
    runsheet's ARM 1 -- the fix pass's relabel the same day). The 0x006E
    array is NOT the only channel into the body's hands -- the first
    record's (e) said it was, and the client refuted it: with the town
    0x006E empty-handed the body still drew the bag's hammer (runs
    20260924T084418 = 084637, strip on and off), and after an outpost F2 it
    kept the OLD weapon while the doll changed (084811). The likeliest
    carrier is OUR OWN load's 0x006D NPC_UPDATE_WEAPONS for the PLAYER
    (`NPC_UPDATE_WEAPONS(leadhand = item 1)`, two messages after the 0x006E
    in all four logs) -- a message RETAIL NEVER SENDS THE OWN BODY: 0 of 46
    outpost connections with a controlled agent (47 carry a 0x0199;
    20260807T133758 :54560 has 91 messages and no 0x0022, 0x006E or 0x006D)
    and 0 of 44 field connections carry a 0x006D addressed to 0x0022's
    controlled agent (weaponcensus.py's "every NPC, never a player" holds
    over all 91; across the corpus no (connection, agent) gets both a 0x006E
    and a 0x006D -- outpost 1,981 / 1,510 bodies, field 44 / 2,081, overlap
    0 -- OBSERVED). The mechanism (build 38797): the client keeps ONE
    visual-equipment store per agent, at record+0x24, slots 0..8; the 0x006D
    worker (0x00810B70, from handler 0x0091E1A0; slots 0..1 -- `cmp ebx, 2`
    at 0x00810DD6 -- BOTH written unconditionally), the 0x006E worker
    (0x00810E30, slots 0..8) and the 0x006F worker (0x008110F0) all write it
    through the one setter 0x0081BE10 -- its only three direct callers
    (`codescan --xrefs 0x0081BE10`: 0x00810BCB, 0x00810E8B, 0x00811145),
    each resolving the agent through 0x005FC380 and storing
    `[record + slot*4 + 0x24] = item`; a slot-0 write also puts the item's
    type byte at record+0x48, or 0x2E when the item is 0. Its reader,
    bounded to direct calls: the AvApi dresser 0x007DFCE0 is called by
    exactly those three workers (0x00810D5E, 0x0081101E, 0x008112D0), and
    its callee 0x007F70B0's other four direct callers take slots 0/1 from
    the getter 0x0080D4C0 over the same record. Last writer wins -- and THAT
    is OBSERVED on our client, in a FIELD: run 20260923T154229 (c1 seq 111
    0x006E [1, 1, 10, ...], the shield at visual 1; seq 113 0x006D [1, 1, 0])
    drew the sword and NO shield, while CONFIRM-2 A4b's 0x006F [1, 1, 12]
    drew the same shield model. So in the town the 0x006D re-armed what the
    0x006E had emptied and the dropped town 0x006F left it there -- the
    reading of every frame, not yet the ablation: no run has withheld the
    message (it went out in all four), and a client arming the body from the
    equipped bag once at load would give the same four frames (the
    runsheet's rival). And on retail's fourteen outpost hand changes NOTHING
    is addressed to the own agent within 5 s but movement rows (t=224.632's
    0x0029/0x002B; the 0x004F's 0x0025/0x0029/0x002B/0x0028/0x00F1); outpost
    strangers with more than one 0x006D never change hands (0 of 1,510
    bodies; a field's do, 6). So retail's town body is bare because every
    carrier leaves it bare -- there is no redraw to send, and the fix is to
    withhold ours: player_weapons_sent. The regime-read negative below still
    stands and is now moot for the hands.
  * THE REGIME READ (a bounded negative, kept): the 0x006E / 0x006F handlers
    (0x0091E1C0 / 0x0091E1E0) reach the AvApi dresser (0x007DFCE0) through
    the ChCliApi workers above, and those handlers, workers and every
    function the workers call directly hold no direct call to
    MissionCliGetMap (0x0084D9B0) or the map-flags reader (0x0084D950):
    `msghandler.py 0x006E --follow --depth 2` and the same for 0x006F, read
    on the fix pass; of MissionCliGetMap's 37 direct callers (`codescan
    --xrefs`) none lies in them. NOT searched: the dresser's callee
    0x007F70B0 and deeper, and indirect calls (visstatus.py's census, which
    the first pass cited here, was of the display FLAGS' readers and said
    nothing about a regime read). Our own town 0x006E carried the hand (run
    20260923T210546, c1 seq 100: visual 0 = item 1 under a map-148 outpost
    load) and the body stood armed -- consistent with the shared store above.
  * WHAT THIS DOES NOT TOUCH: the equipped BAG (0x013E / 0x014B / 0x0152 --
    the doll and the weapon-set panel read it, and retail's outpost switches
    still moved the items), the 0x0147 / 0x0148 set declarations, the
    server's own swing model (a town never swings), and NPC bodies -- retail's
    outpost NPCs DO carry weapons in 0x006D (466 of 1,653 outpost 0x006D
    MESSAGES with a lead; 403 of 1,510 distinct bodies), so an NPC's hands are
    not this rule's. Heroes have no body in a town on retail
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
    (0 of 2,245 outpost 0x006E messages, 1,981 bodies). OBSERVED."""
    return bool(explorable)


def player_weapons_sent(explorable):
    """Does the load send the PLAYER a 0x006D NPC_UPDATE_WEAPONS here? In a
    TOWN, no: retail sends the own body none (0 of 46 outpost connections
    with a controlled agent -- and 0 of 44 field ones, OBSERVED, CONFIRM-2's
    census), and on our client that message is the likeliest carrier that
    armed the empty-handed town body and kept the OLD weapon standing across
    F2 (the docstring's THE CARRIER: one store per agent, three writers, last
    one wins -- CORROBORATED; the runsheet's ARM 1 is the observation). In a
    FIELD ours still sends it, [player, lead, 0] -- and that is NOT harmless:
    the zero off hand is the last hand write, so on a sword-and-shield field
    load the body draws the sword and NO shield (run 20260923T154229, c1 seq
    111/113, walk1-wait.png -- OBSERVED; CONFIRM-2 A4b draws the same shield
    through a 0x006F). A field defect of its own (PLAN.md 8.1's D1 line):
    carry the bag's off hand as the third field, or withhold the message as
    retail does -- the second UNVERIFIED for the swing path (the send site's
    ItCliApi.cpp(400) history of 2026-08-06 was about a wrong VALUE, not
    absence, and the 0x006D worker does more than the setter for slot 0), so
    it is a field run's choice, not this town fix's."""
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
