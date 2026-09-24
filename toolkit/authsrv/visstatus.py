"""The per-slot DISPLAY MODE of the inventory panel -- the eye beside the cape,
the headgear and the two costume slots -- as the client keeps it: ONE byte of
visibility flags, two bits per slot kind (DESKWORK-D1, the owner's answer of
2026-09-23; studies/cmsg/FINDINGS.md "The display mode").

WHERE EVERY NUMBER HERE COMES FROM (build 38797, the pinned pristine client;
`codescan.py --dis/--xrefs/--field`, `asserts.py`, `msgshape.py`):

  * THE STATE is one dword at the character context +0x7C8 -- getter 0x00815EF0
    (`ctx->[0x2c]->[0x7c8]`), bit tester 0x00815EA0 (`vis < CHAR_STATS_VIS`,
    ChCliApi.cpp:5032, and the bound it compares against is 8: eight bits).
    `CHAR_STATS_VIS` is ArenaNet's own name for the enum; the roster blob's
    "helm_shown" bit 14 is `CHAR_STATS_VIS(3)` packed by UiGame's summary
    packer (0x004A8C59, the tester's ONE caller), which is what ties kind 1
    to the HEADGEAR from a second direction (the three server lineages'
    `helm_status`, studies/character/FINDINGS.md).
  * THE ONLY WRITER is 0x00814BE0(value, mask): `flags = (flags & ~mask) |
    value`, then frame 0x1000006C {mask, flags} to the bus. Its ONE caller is
    the RECV stub 0x0091F7F0 = GAME_SMSG 0x00EF [u32 value, u32 mask]
    (msgshape RECV table 0x00BC8F68, 10 B). So the client never changes the
    flags itself -- a drop-down choice reaches the wire and waits for 0x00EF.
  * THE SENDER is the drop-down (InvVisibilityStatus.cpp, 0x008ECF30's
    "selected" arm): it calls 0x00816C10(bits & mask, mask), a thunk to the
    send wrapper 0x00920FE0 = GAME_CMSG 0x0057 [u32 value, u32 mask]
    (msgshape SEND table 0x00BC8CB8, 10 B; sendsites.py names the wrapper).
  * THE KIND TABLES: masks at 0xBA38D4 (KIND_MASK below), one (code, bits)
    table per kind at 0xBA3854/74/94/B4 read by 0x008ECD00 (KIND_MENU below);
    0x008ECD90 picks the code whose `bits & mask == flags & mask`, first
    match, else 7; the string per code is 0x008ECDF0's (CODE_STRING_ID); the
    icon per code is the widget's draw arm 0x008EC7F5 (CODE_ICON).
  * THE REGIME is GmAgentDoll's (0x005384B0): `MissionCliGetMap()` (0x0084D9B0,
    OBSERVED 0 = OUTPOST, 1 = GAME, studies/minimap) selects the HIGH bit of
    each pair in a town and the LOW bit in a field; a clear bit hides the
    kind. Kinds 2 and 3 (the costumes) are also hidden in a field whose map
    flags carry 0x40000 without 0x40000000 (0x0084D950) -- a PvP rule this
    server never meets and does not model.
  * WHO READS THE FLAGS (the fix pass, ENG-VIS-3/EVR-VIS-4: the census is
    the GETTER's callers, not `--field`'s direct hits, which see only the
    writer, the tester, the getter and three context resets). The getter
    0x00815EF0 has EIGHT direct callers (`codescan --xrefs`): three in the
    drop-down (0x008EC6E3 the icon, 0x008ECEA8 the menu, 0x008ECF5B the
    "selected" arm); 0x005384E1 GmAgentDoll (the paper doll's figure);
    0x005046F8, 0x00508C91 and 0x0050CDFE, three UI sites (the second gates
    bag slots 7/8 on the town bits 0x20/0x80, the third on the field bits
    0x10/0x40); and ONE outside UI, 0x0081DE5E in 0x0081DDD0 -- a
    ChCliObserver.cpp record builder (the asserts inside it), called from
    0x0080E3F5/0x0080E485, which copies the player's equipped bag slots 2..6
    into a record and overrides with bag 7 under 0x10 (0x0081DED4) and bag
    8 under 0x40 (0x0081DEBD): the costume FIELD bits, no regime test, into
    a record and not onto the body. The tester 0x00815EA0 has one caller
    (the roster packer); the writer has one (0x00EF's stub); and the frame
    id 0x1000006C occurs at exactly SIX .text sites and in no data section
    (the writer 0x00814C17, the doll's subscribe 0x0053761D, four in the
    widget). None of those reaches the AvApi dresser 0x007DFCE0, whose three
    callers are all ChCliApi message workers (the 0x006E bulk and 0x006F
    slot writes among them). So the WORLD model follows the mode only
    because the SERVER sends the body's visual array without the hidden
    piece: RECONSTRUCTION from that negative.
  * WHAT THE TAPES SAY, and what they cannot (the fix pass, EVR-VIS-1/
    ENG-VIS-2). The landing quoted "0x006E's head slot 0 on 756 of 2,245
    outpost bodies vs 0 of 48 field bodies" as corroboration; it is NOT --
    every one of the 48 field bodies is the owner's OWN body (its armour
    ids all in the connection's equipped bag) under 0x00EF [0xFF, 0xFF], and
    every one of the 756 bare outpost heads is a STRANGER whose mode and
    inventory the tape does not carry, so the comparison is strangers in
    towns against the owner in fields and a tape with no strip at all gives
    the same numbers. The own body carries its equipped helm on 50 of 50
    outpost loads and 48 of 48 field loads under Always Show: consistent
    with the strip, not discriminating. The OBSERVED precedent that retail
    tailors the own 0x006E per regime is the WEAPON: no outpost 0x006E
    carries one (2,245 of 2,245 bodies, visual 0 and 1 both zero -- the
    owner's own 50 among them, with a weapon in the equipped bag on all 50),
    while in a field every body whose bag holds one carries it (40 of 40;
    the other 8 field loads have no bag weapon). The head strip itself is
    unwitnessed on any body whose mode is known (every owner character on
    tape is Always Show) and stays RECONSTRUCTION.
  * RETAIL'S DEFAULT: 0x00EF [0xFF, 0xFF] once per connection on 95 of 96
    live connections, immediately after 0x00E9 CHARACTER_UPDATE_FACTIONS and
    before 0x003C -- every slot Always Show (the owner's screenshot). c2s
    0x0057 is on NO tape: the reply's shape is RECONSTRUCTION.

Standard library only; a leaf (no repo import).
"""

# Slot kinds, in the client's own order (the index into both tables).
KIND_CAPE = 0
KIND_HEADGEAR = 1
KIND_COSTUME_BODY = 2
KIND_COSTUME_HEAD = 3
KIND_NAMES = {KIND_CAPE: "cape", KIND_HEADGEAR: "headgear",
              KIND_COSTUME_BODY: "costume body", KIND_COSTUME_HEAD: "costume head"}

# 0xBA38D4: the two bits each kind owns. Low bit of the pair = shown in a
# FIELD (MISSION_MAP_GAME), high bit = shown in a TOWN (OUTPOST) -- the doll's
# two regime branches (0x00538535 tests 0x2/0x8/0x20/0x80 when the map is an
# outpost; 0x005384F6 tests 0x1/0x4/0x10/0x40 when it is a field).
KIND_MASK = {KIND_CAPE: 0x03, KIND_HEADGEAR: 0x0C,
             KIND_COSTUME_BODY: 0x30, KIND_COSTUME_HEAD: 0xC0}
FLAG_BITS = 0xFF           # CHAR_STATS_VIS == 8 (ChCliApi.cpp:5032's bound)
DEFAULT_FLAGS = 0xFF       # retail's load, 95 of 95: every slot Always Show

# 0xBA3854..0xBA38B4, four (code, bits) rows per kind, in the client's order
# (the menu's order). `bits` is masked by the kind's mask before the compare,
# so 0xFFFFFFFF is "both bits set". Kind 0 (the cape) has its own third and
# fourth codes; kinds 2 and 3 (the costumes) their own first code.
KIND_MENU = {
    KIND_CAPE: ((0, 0xFFFFFFFF), (2, 0x01), (5, 0x02), (6, 0x00)),
    KIND_HEADGEAR: ((0, 0xFFFFFFFF), (2, 0x04), (4, 0x08), (3, 0x00)),
    KIND_COSTUME_BODY: ((1, 0xFFFFFFFF), (2, 0x10), (4, 0x20), (3, 0x00)),
    KIND_COSTUME_HEAD: ((1, 0xFFFFFFFF), (2, 0x40), (4, 0x80), (3, 0x00)),
}
CODE_NONE = 7              # 0x008ECD90's "no row matched"
# 0x008ECDF0: the string id each code draws (the menu's text; unread bodies),
# read THROUGH ITS JUMP TABLE at 0x008ECE3C -- code 3 lands on 0x008ECE25
# (0x330), 4 on 0x008ECE17 (0x32E), 5 on 0x008ECE1E (0x32F) -- and the menu
# builder's copy (table 0x008ED080) agrees. The landing had 3/4/5 as 0x32E/
# 0x32F/0x330, the case bodies taken in ADDRESS order (the fix pass,
# EVR-VIS-3). So the headgear/costume menu reads 0x32C, 0x32D, 0x32E, 0x330 in
# row order, and the cape's two own strings are 0x32F and 0x331. Nothing on the
# server reads this table; test_visstatus pins it against the address order.
CODE_STRING_ID = {0: 0x32C, 1: 0x15BDE, 2: 0x32D, 3: 0x330, 4: 0x32E, 5: 0x32F,
                  6: 0x331}
CODE_STRING_ADDRESS_ORDER = (0x32C, 0x15BDE, 0x32D, 0x32E, 0x32F, 0x330, 0x331)  # KNOWN-BAD
# 0x008EC7F5 (the widget's icon arm): the icon each code draws. 0 is the eye
# (Always Show, the owner's retail screenshot), 3 the circled bar (Always
# Hide, ours on 20260923T185124); 1 and 2 are the two half-modes.
CODE_ICON = {0: 0, 1: 0, 2: 1, 3: 3, 4: 2, 5: 2, 6: 3}
# The four menu texts in the owner's screenshot (images/3.png) for the
# headgear's codes; the cape's codes 5/6 and the costumes' code 1 draw other
# string ids (unread) with the same icons.
ICON_LABEL = {0: "Always Show", 1: "Hide in Towns and Outposts",
              2: "Hide in Combat Areas", 3: "Always Hide"}

# The 0x006E visual positions the kinds occupy (studies/newopcodes: 6 head;
# ConstCostume.cpp:1188/1217: 7 body costume, 8 hat costume). The cape has no
# visual slot: it rides 0x0048 AGENT_SET_TABARD_VISIBLE.
KIND_VISUAL_SLOT = {KIND_HEADGEAR: 6, KIND_COSTUME_BODY: 7, KIND_COSTUME_HEAD: 8}


def apply(flags, value, mask):
    """The client's own writer, 0x00814BE0: `(flags & ~mask) | value`, kept
    to the eight CHAR_STATS_VIS bits."""
    return ((int(flags) & ~int(mask)) | int(value)) & FLAG_BITS


def load_flags(stored):
    """The byte a connection starts with: the store row's `vis_flags` when it
    is an int (kept to the eight bits), else retail's default -- 0xFF, every
    slot Always Show, 95 of 95 live loads. Absence is the default, never
    zero: the zero is the defect (the fix pass, ENG-VIS-4 -- the burst reads
    the byte through this so a test can drive it)."""
    if isinstance(stored, bool) or not isinstance(stored, int):
        return DEFAULT_FLAGS
    return int(stored) & FLAG_BITS


def load_message(flags):
    """The 0x00EF the load sends: [flags, 0xFF] -- the whole byte under the
    full mask, the shape of retail's own [0xFF, 0xFF]."""
    return [int(flags) & FLAG_BITS, FLAG_BITS]


def slot_kind(slot):
    """The kind a 0x006E/0x006F visual position belongs to, or None (the
    hands and the armour carry no display mode)."""
    for kind, s in KIND_VISUAL_SLOT.items():
        if s == int(slot):
            return kind
    return None


def filter_slot_writes(writes, flags, explorable):
    """The per-slot 0x006F writes the WORLD may see under this regime
    (the fix pass, ENG-VIS-1/EVR-VIS-2: the equip path's writes went out
    unfiltered, so re-equipping a helm hidden in a field re-helmed the body).
    `writes` is [(slot, item)]; a write that puts an item into a slot whose
    kind the mode hides here goes out as item 0 instead -- the slot is
    already 0 on the body, and the client's 0x006F handler is regime-blind,
    so the zero is idempotent. Returns (writes, [(kind, slot, item hidden)]).
    RECONSTRUCTION: retail's reply to an equip under a hiding mode is on no
    tape."""
    out, hid = [], []
    for slot, item in writes:
        kind = slot_kind(slot)
        if item and kind is not None and not shown(flags, kind, explorable):
            hid.append((kind, int(slot), int(item)))
            out.append((int(slot), 0))
        else:
            out.append((int(slot), int(item)))
    return out, hid


def check_request(value, mask):
    """Why a c2s 0x0057 [value, mask] is refused, or None. The drop-down
    sends `bits & mask, mask` with the mask one kind's pair (0x008ECFAA), so
    anything else is not the client's request: an empty mask, bits outside
    CHAR_STATS_VIS, or a value carrying bits its mask does not."""
    value, mask = int(value), int(mask)
    if mask == 0:
        return "an empty mask changes nothing"
    if mask & ~FLAG_BITS or value & ~FLAG_BITS:
        return (f"bits outside CHAR_STATS_VIS (8 bits): value 0x{value:x} "
                f"mask 0x{mask:x}")
    if value & ~mask:
        return f"value 0x{value:x} carries bits outside its mask 0x{mask:x}"
    return None


def shown(flags, kind, explorable):
    """Does the regime show this kind? The doll's rule (0x005384B0): the LOW
    bit of the pair in a field, the HIGH bit in a town."""
    bit = 2 * int(kind) + (0 if explorable else 1)
    return bool((int(flags) >> bit) & 1)


def hidden_kinds(flags, explorable):
    """The kinds the regime hides, ascending."""
    return [k for k in sorted(KIND_MASK) if not shown(flags, k, explorable)]


def kinds_in(mask):
    """The kinds a mask touches, ascending."""
    return [k for k, m in sorted(KIND_MASK.items()) if int(mask) & m]


def mode_code(flags, kind):
    """0x008ECD90: the menu code the drop-down shows for this kind -- the first
    row whose `bits & mask` equals `flags & mask`, else CODE_NONE (7)."""
    mask = KIND_MASK[int(kind)]
    want = int(flags) & mask
    for code, bits in KIND_MENU[int(kind)]:
        if (bits & mask) == want:
            return code
    return CODE_NONE


def mode_bits(kind, code):
    """The inverse of the menu: the bits (already masked) a chosen code
    sends, or None when the kind's menu has no such code."""
    mask = KIND_MASK[int(kind)]
    for c, bits in KIND_MENU[int(kind)]:
        if c == int(code):
            return bits & mask
    return None


def mode_label(flags, kind):
    """For a log line: the icon's text for this kind's current mode."""
    code = mode_code(flags, kind)
    if code == CODE_NONE:
        return "no menu row"
    return ICON_LABEL[CODE_ICON[code]]


def describe(flags):
    """One line, all four kinds."""
    return ", ".join(f"{KIND_NAMES[k]} {mode_label(flags, k)}"
                     for k in sorted(KIND_MASK))


def strip_visual(worn, flags, explorable):
    """The 0x006E array the WORLD sees under this regime: a copy of `worn`
    with each hidden kind's visual position zeroed (RECONSTRUCTION -- the
    client has no reader of the flags on the dresser's path, so the server's
    array is the only channel; the tapes' regime pattern corroborates it).
    Returns (array, [(kind, slot, item id it hid)])."""
    out = list(worn)
    hid = []
    for kind in hidden_kinds(flags, explorable):
        slot = KIND_VISUAL_SLOT.get(kind)
        if slot is None or slot >= len(out):
            continue
        if out[slot]:
            hid.append((kind, slot, out[slot]))
            out[slot] = 0
    return out, hid


def slot_changes(old_flags, new_flags, worn, explorable):
    """After a mode change: the 0x006F per-slot writes the world needs --
    [(kind, slot, item id or 0)] for every kind whose shown-state under the
    CURRENT regime changed and whose visual slot holds a piece. A kind whose
    change only concerns the other regime sends nothing now (the next
    instance load's array carries it)."""
    out = []
    for kind, slot in sorted(KIND_VISUAL_SLOT.items()):
        if slot >= len(worn) or not worn[slot]:
            continue
        before = shown(old_flags, kind, explorable)
        after = shown(new_flags, kind, explorable)
        if before != after:
            out.append((kind, slot, worn[slot] if after else 0))
    return out
