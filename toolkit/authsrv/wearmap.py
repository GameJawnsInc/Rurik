r"""Which of an item's three vocabularies puts it on a body -- and the refusals.

    python toolkit/authsrv/test_wearmap.py      # the proof, all four witnesses

An equipped item carries THREE small integers a server must keep straight, and
until 2026-08-23 no document said which one does what
(studies/playercomposite/FINDINGS.md 2 step E's standing unknown, resolved in
9.2). The ruling, each half read from the client AND measured on retail's wire:

  1. The EQUIP SLOT (0x006E array position / 0x006F index / the equipped bag's
     slot -- one vocabulary) is a HANGER. It never chooses a body component.
     Retail itself wears three DIFFERENT leggings-class items in the Boots,
     Legs and Gloves slots of one agent (capture 20260817T231139), all three
     resolving to the legs component. Slots are special-cased three ways only:
     slot 0 caches the weapon's type byte on the agent (+0x48) and raises the
     bundle events; slots 7/8 feed the costume registry, whose per-slot
     override handles REPLACE the armour slots' fileId+flags+dye at
     m_slotItemData build time (flags |= 0x20000006) -- which is why a costume
     covers armour without any walk-order rule.

  2. The WIRE ITEM TYPE (the byte at item+0x20, cached at
     m_slotItemData+0x04) NEVER picks the composite component. Proof by
     counting: type 16 (Head) resolves to record types 17 AND 19; record type
     15 is reached from wire types 7 AND 44 -- many-to-many both ways, so
     neither derives the other. Its real consumers on the dressing path are
     the ATTACH CLASSIFIER below (which hand/bone a MODEL-type item hangs on),
     the weapon-class cache, and the bundle checks; armour body types are
     deliberately in the classifier's fail class.

  3. The COMPOSITE RECORD (flags bit 2 set => fileId is an index into the
     3,803-record CpsData table) is what picks the component:
     `record.hdr >> 22` is the composite type and `s_components[type]` the
     component it replaces. Wire corpus: flags-bit-2 <=> fileId-in-range is
     exact, 5,528 / 182 wears with zero mixed cells. Head items go BOTH ways
     under one wire type -- 658 composite wears vs 132 attach wears
     (festival masks), discriminated by the FLAG, never by the type.

So a server authoring an item must pick the three CONSISTENTLY -- the client
will not correct a contradiction, it will draw it. `check_wear` refuses the
combinations retail never produced; `authsrv.py` runs it over STARTER_ARMOUR
at import so a bad row dies at the desk, not thirty seconds into a run.

The classifier transcription below is CLIENT DATA (build 38797, class table
0x0082E840, jump table 0x0082E828), extracted by
`toolkit/clientscan/composite.py` (`_attach_class`, anchor-located, refusing);
`test_wearmap.py` 2 proves this transcription equals that extraction, the
same pattern `test_playerassembly.py` 7 uses for the geometry split. The
attach-code MEANINGS (which bone each code names) are RECONSTRUCTION and
deliberately unnamed here; the fail/non-fail split is OBSERVED.
"""

ITEM_FLAG_COMPOSITE = 0x4

# Wire item types, named only where the corpus join earns the name (slot the
# type is worn in, times seen; test_wearmap 3 pins the counts as floors).
WIRE_TYPE_BODY = 7            # worn slot 2, n=1153
WIRE_TYPE_BOOTS = 4           # worn slot 3, n=1152
WIRE_TYPE_GLOVES = 13         # worn slot 5, n=1151
WIRE_TYPE_HEAD = 16           # worn slot 6, n=790 (658 composite, 132 attach)
WIRE_TYPE_LEGS = 19           # worn slot 4, n=1157 (+5 each in slots 3 and 5)
WIRE_TYPE_SHIELD = 24         # worn slot 1, n=20; the classifier's own class
WIRE_TYPE_COSTUME_BODY = 44   # worn slot 7, n=97, record type 15
WIRE_TYPE_COSTUME_HEAD = 45   # worn slot 8, n=150, record types 17/19
WIRE_TYPE_BUNDLE = 6          # the equip workers' own `cmp type, 6` events

# The attach classifier: ATTACH_CLASS_OF_TYPE[type - 1] -> class,
# ATTACH_OUT_OF_CLASS[class] -> attach code (None = the fail case: not an
# attachable model; armour body pieces land here BY DESIGN -- they are
# composited through the record instead).
ATTACH_CLASS_OF_TYPE = (
    0, 0, 5, 5, 1, 0, 5, 5, 5, 5,     # types  1..10
    5, 1, 5, 5, 1, 2, 5, 5, 5, 5,     # types 11..20
    5, 0, 5, 3, 5, 0, 0, 0, 5, 5,     # types 21..30
    5, 4, 5, 5, 1, 0, 5, 5, 5, 5,     # types 31..40
    5, 0,                             # types 41..42
)
ATTACH_OUT_OF_CLASS = (1, 0, 2, 3, -1, None)


def attach_of(item_type):
    """The client's attach code for a wire type, or None (not attachable).

    Out-of-range types take the classifier's own bounds path: `dec; cmp; ja`
    sends type 0 and types > 42 to the fail case.
    """
    if not 1 <= item_type <= len(ATTACH_CLASS_OF_TYPE):
        return None
    return ATTACH_OUT_OF_CLASS[ATTACH_CLASS_OF_TYPE[item_type - 1]]


# The nine visual-equipment slots (0x006E positions; studies/character 2's
# measured order, re-confirmed by the 0x006F join in test_wearmap 3).
SLOT_WEAPON = 0
SLOT_OFFHAND = 1
SLOT_BODY = 2
SLOT_BOOTS = 3
SLOT_LEGS = 4
SLOT_GLOVES = 5
SLOT_HEAD = 6
SLOT_COSTUME_BODY = 7
SLOT_COSTUME_HEAD = 8

# What retail actually wears where (every (slot, type) pair in the corpus).
# Slots 0/1 are attach-ruled rather than enumerated: any attachable type.
WORN_TYPES = {
    SLOT_BODY: frozenset({WIRE_TYPE_BODY}),
    SLOT_BOOTS: frozenset({WIRE_TYPE_BOOTS, WIRE_TYPE_LEGS}),
    SLOT_LEGS: frozenset({WIRE_TYPE_LEGS}),
    SLOT_GLOVES: frozenset({WIRE_TYPE_GLOVES, WIRE_TYPE_LEGS}),
    SLOT_HEAD: frozenset({WIRE_TYPE_HEAD}),
    SLOT_COSTUME_BODY: frozenset({WIRE_TYPE_COSTUME_BODY}),
    SLOT_COSTUME_HEAD: frozenset({WIRE_TYPE_COSTUME_HEAD}),
}

# Wire type -> the composite record types retail pairs it with. Head's TWO
# record types under one wire type (17 replaces hair, 19 the second head
# slot) is the counting proof that the record, not the type, is authoritative
# -- the choice between 17 and 19 is a property of WHICH record the fileId
# names, and nothing else on the item can express it.
RECORD_TYPES_OF_WIRE = {
    WIRE_TYPE_BODY: frozenset({15}),
    WIRE_TYPE_BOOTS: frozenset({14}),
    WIRE_TYPE_LEGS: frozenset({18}),
    WIRE_TYPE_GLOVES: frozenset({16}),
    WIRE_TYPE_HEAD: frozenset({17, 19}),
    WIRE_TYPE_COSTUME_BODY: frozenset({15}),
    WIRE_TYPE_COSTUME_HEAD: frozenset({17, 19}),
}


class WearError(ValueError):
    """An authored (slot, type, flags, record) combination retail never
    produced and the client would mis-draw. A refusal, never a warning."""


def check_wear(slot, item_type, flags, record_type=None):
    """Refuse a wear the mapping contradicts; return None when consistent.

    `record_type` is the composite record's `hdr >> 22` when the caller has
    the table open (the tests do); a server hot path may pass None and keep
    the slot/type/flags checks, which need no vault.
    """
    composite = bool(flags & ITEM_FLAG_COMPOSITE)
    if slot in (SLOT_WEAPON, SLOT_OFFHAND):
        if composite:
            raise WearError(
                f"slot {slot} (hands) with ITEM_FLAG_COMPOSITE: hand items "
                f"are attached models, and retail's 182 hand wears carry "
                f"real file ids, never record indices")
        if attach_of(item_type) is None:
            raise WearError(
                f"wire type {item_type} in hand slot {slot} lands in the "
                f"attach classifier's fail class -- the client has no bone "
                f"to hang it on and draws nothing")
        return None
    if slot not in WORN_TYPES:
        raise WearError(f"slot {slot} is not one of the nine equip slots")
    if item_type not in WORN_TYPES[slot]:
        raise WearError(
            f"wire type {item_type} in slot {slot}: retail wears only "
            f"{sorted(WORN_TYPES[slot])} there. The type does not PLACE the "
            f"piece (the record does) -- but the inventory UI, the equip "
            f"request path and the attach classifier all read it, so an "
            f"unprecedented pair is an experiment, not content")
    if not composite:
        if slot != SLOT_HEAD:
            raise WearError(
                f"slot {slot} without ITEM_FLAG_COMPOSITE: armour body "
                f"pieces are composite 100% on retail's wire (5,528/5,528); "
                f"only the head slot also takes attach-class models (masks)")
        if attach_of(item_type) is None:
            raise WearError(
                f"non-composite head item of wire type {item_type} has no "
                f"attach class -- the client can neither composite nor "
                f"attach it")
        return None
    if record_type is not None:
        allowed = RECORD_TYPES_OF_WIRE.get(item_type, frozenset())
        if record_type not in allowed:
            raise WearError(
                f"wire type {item_type} with composite record type "
                f"{record_type}: retail pairs it only with "
                f"{sorted(allowed)}. The record is what the client DRAWS "
                f"(s_components[{record_type}] names the component), so "
                f"this item would render as a different body part than its "
                f"type claims everywhere else")
    return None


def check_content_row(slot, row):
    """`check_wear` over a content item row (the dict item_template returns)."""
    return check_wear(slot, row["item_type"], row["flags"])
