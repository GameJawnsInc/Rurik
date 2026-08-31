r"""The wear mapping: equip slot / wire type / composite record, kept straight.

    python toolkit/authsrv/test_wearmap.py

`wearmap.py` is the ruling (playercomposite FINDINGS 9.2): the equip slot is
a hanger, the wire type feeds the attach classifier and the UI but NEVER
picks a component, and the composite record (flags bit 2 -> fileId indexes
the CpsData table) is what the client draws. This file proves it four ways --
the module's own refusals, the exe's classifier (transcription == extraction,
the `test_playerassembly` 7 pattern), the live wire, and the archive join
whose many-to-many counts are the no-derivation proof. Floors are from the
green run they were measured on, never guessed.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
import checks       # noqa: E402
import wearmap      # noqa: E402

# Floor set from a real green run: 36 on 2026-08-23, 40 on 2026-08-24 when
# section 5's type-45 taxonomy landed.
#
# BUT THE FLOOR IS THE MANDATORY CORE, WHICH IS 16 + 4 = 20. Sections 3-5 all
# need the vault, and the block above them `sys.exit`s with a declared skip
# when it is absent -- so on a machine without one this run ends at 20 and a
# floor of 36 or 40 would have failed it on the SHORTFALL, naming the wrong
# thing entirely. `checks.py`'s guidance is to floor at the mandatory core and
# let the optional sections declare skips; the same correction was made to
# `test_compositetrap.py` the same day, which had the same latent bug for the
# same reason -- a floor read off a full green run on a machine that always
# has the vault.
LEDGER = checks.Ledger("wear mapping", floor=20)
check = checks.adopt(LEDGER)

W = wearmap

# ---------------------------------------------------------------- section 1
print("== 1. the module's own tables, and every refusal direction ==")
check(len(W.ATTACH_CLASS_OF_TYPE) == 42 and len(W.ATTACH_OUT_OF_CLASS) == 6
      and W.ATTACH_OUT_OF_CLASS.count(None) == 1,
      "42 types, 6 classes, exactly one fail class -- the classifier's shape")
check(W.attach_of(0) is None and W.attach_of(43) is None,
      "types 0 and 43 fail by the classifier's own bounds (dec; cmp; ja)")
check(W.attach_of(W.WIRE_TYPE_HEAD) == 2 and W.attach_of(W.WIRE_TYPE_SHIELD) == 3,
      "Head (16) and Shield (24) each have a class of their OWN -- the "
      "attach codes the masks and shields hang by")
check(W.attach_of(32) == -1,
      "type 32's code is -1, the one negative (a both-hands special)")
check(all(W.attach_of(t) is None for t in (4, 7, 13, 19)),
      "all four armour body types are the FAIL class BY DESIGN -- they are "
      "composited through the record, not attached")
check(all(W.attach_of(t) is not None for t in (2, 5, 6, 15, 22, 26, 27)),
      "the held classes cover the weapon types retail wears in slot 0")
for slot, ty, flags, rt, why in (
        (W.SLOT_WEAPON, 7, 0, None, "an armour type in a hand slot"),
        (W.SLOT_WEAPON, 27, W.ITEM_FLAG_COMPOSITE, None,
         "a composite flag on a hand item"),
        (W.SLOT_BODY, 4, W.ITEM_FLAG_COMPOSITE, None,
         "boots-typed item in the body slot (retail never pairs them)"),
        (W.SLOT_BODY, 7, 0, None, "a non-composite body piece"),
        (W.SLOT_BODY, 7, W.ITEM_FLAG_COMPOSITE, 14,
         "a body-typed item whose record draws as boots"),
        (W.SLOT_COSTUME_BODY, 7, W.ITEM_FLAG_COMPOSITE, None,
         "plain armour in the costume slot"),
):
    try:
        W.check_wear(slot, ty, flags, record_type=rt)
        check(False, f"check_wear must refuse {why}")
    except W.WearError:
        check(True, f"check_wear refuses {why}")
for slot, ty, flags, rt, why in (
        (W.SLOT_WEAPON, 27, 0, None, "a sword in the weapon slot"),
        (W.SLOT_HEAD, 16, 0, None,
         "a NON-composite head item (the 132 festival masks attach)"),
        (W.SLOT_HEAD, 16, W.ITEM_FLAG_COMPOSITE, 19,
         "head wire type with EITHER of its two record types"),
        (W.SLOT_BOOTS, 19, W.ITEM_FLAG_COMPOSITE, 18,
         "the measured anomaly: a legs item hung on the Boots slot"),
):
    W.check_wear(slot, ty, flags, record_type=rt)
    check(True, f"check_wear accepts {why}")

# ---------------------------------------------------------------- section 2
print("== 2. transcription == extraction (the exe cross-witness) ==")
try:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import composite
    t = composite.extract()
# SystemExit too: `composite.extract()` reaches `pinned.find()`, which RAISES
# one when the build is not in the vault. The call is INDIRECT, so
# test_srclint.py section 11 cannot see it -- that lint reads the try body for a
# direct call and is a floor, not a census. Found 2026-08-31 by running the file
# with no vault, which is the only thing that finds this class reliably.
except (Exception, SystemExit) as exc:                      # noqa: BLE001
    LEDGER.skip("exe cross-witness", f"pinned client unavailable: {exc}")
    t = None
else:
    check(tuple(t["attach_class"]) == W.ATTACH_CLASS_OF_TYPE,
          "wearmap's class table IS the exe's (anchor-located, 42 bytes)",
          f"exe={t['attach_class']}")
    check(tuple(t["attach_out"]) == W.ATTACH_OUT_OF_CLASS,
          "and the per-class attach codes match, fail case included",
          f"exe={t['attach_out']}")
    comp = t["s_components"]
    check(all(comp[rt] < 8 for rts in W.RECORD_TYPES_OF_WIRE.values()
              for rt in rts),
          "every record type the mapping names resolves to a REAL component "
          "through the exe's own s_components (8 = none)")
    check({comp[rt] for rt in W.RECORD_TYPES_OF_WIRE[W.WIRE_TYPE_HEAD]}
          == {1, 2},
          "Head's two record types land on TWO components (hair-replace 2, "
          "second head slot 1) -- what a type->record function could never "
          "express, which is WHY the record is authoritative")

# ---------------------------------------------------------------- the vault
try:
    import tape         # noqa: E402
    import vaultpath    # noqa: E402
    from codec import Codec  # noqa: E402
    live = vaultpath.require_dir("captures", "live", why="the wear census")
except (Exception, SystemExit) as exc:                                    # noqa: BLE001
    LEDGER.skip("wire census + archive join", f"vault unavailable: {exc}")
    sys.exit(LEDGER.verdict())

try:
    import archive      # noqa: E402
    import cpsdata      # noqa: E402
    ar = archive.Archive(vaultpath.vault_path("dat_study", "Gw.dat"))
    table = cpsdata.CompositeTable.load(ar)
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("archive join", f"study archive unavailable: {exc}")
    table = None

LOW, HIGH, EQ_ALL, EQ_ONE = 0x015E, 0x0161, 0x006E, 0x006F
MASK = 0x7FFFFFFF
codec = Codec()

declares = wears = undeclared = 0
slot_type = collections.Counter()
type_rectype = collections.Counter()
flag_comp = collections.Counter()
hand_wears = collections.Counter()      # attachable? -> n (slots 0/1)
head_split = collections.Counter()      # composite? -> n (slot 6)
armour_nocomp = 0                       # slots 2..5 without bit 2
# Corpus-wide, because `items` below is per-CONNECTION and is reset for each
# one: a census read off it after the loop sees only the last connection, and
# the first version of section 5 skipped on "0 ids" for exactly that reason.
t45_ids = set()
starter_like = 0

for stamp in sorted(os.listdir(live)):
    cap = os.path.join(live, stamp)
    if not os.path.isdir(cap):
        continue
    for chan in tape.channel_files(cap):
        try:
            _i, events = tape.load_tape(cap, chan["connection"])
            msgs, _r = tape.decode_all(events, codec, "GAME_SMSG", 0)
        except Exception:                                   # noqa: BLE001
            continue
        items = {}
        for _t, op, v in msgs:
            if op in (LOW, HIGH) and len(v) > 9:
                items[int(v[1])] = (int(v[3]), int(v[2]), int(v[8]))
                declares += 1
                if int(v[3]) == W.WIRE_TYPE_COSTUME_HEAD:
                    t45_ids.add(int(v[2]) & MASK)
        for _t, op, v in msgs:
            worn = []
            if op == EQ_ALL and len(v) > 10:
                worn = [(s, int(v[2 + s])) for s in range(9)]
            elif op == EQ_ONE and len(v) > 3:
                # (agent, slot, item): the worker 0x008110f0 indexes the
                # equip array with its SECOND argument, so the order is the
                # binary's, not a guess.
                worn = [(int(v[2]), int(v[3]))]
            for slot, iid in worn:
                if not iid:
                    continue
                wears += 1
                if iid not in items:
                    undeclared += 1
                    continue
                wt, fid, fl = items[iid]
                comp = bool(fl & W.ITEM_FLAG_COMPOSITE)
                slot_type[(slot, wt)] += 1
                if slot in (0, 1):
                    hand_wears[W.attach_of(wt) is not None] += 1
                elif slot == W.SLOT_HEAD:
                    head_split[comp] += 1
                elif slot in (2, 3, 4, 5):
                    armour_nocomp += not comp
                if table is not None:
                    mfid = fid & MASK
                    flag_comp[(comp, mfid < len(table.records))] += 1
                    if comp and mfid < len(table.records):
                        type_rectype[(wt, table.records[mfid].type)] += 1

# ---------------------------------------------------------------- section 3
print("== 3. retail's wire obeys the mapping (the census) ==")
check(declares >= 6445 and wears >= 5709 and undeclared == 0,
      "corpus floors: >= 6,445 declares, >= 5,709 non-null wears, every "
      "worn item declared first on its own connection (an early census said "
      "5,710: one 0x006F UNEQUIP, item id 0, misread by an order-probe "
      "heuristic -- the binary-confirmed order counts 5,709)",
      f"declares={declares} wears={wears} undeclared={undeclared}")
worn_pairs = {(s, ty) for (s, ty), n in slot_type.items()}
body_pairs = {(s, ty) for (s, ty) in worn_pairs if s >= 2}
check(all(ty in W.WORN_TYPES[s] for s, ty in body_pairs),
      "every body-slot (slot, wire type) pair retail wears is in "
      "wearmap.WORN_TYPES -- the table IS the corpus, nothing invented",
      f"pairs={sorted(body_pairs)}")
check(all(ty in {ty2 for tys in W.WORN_TYPES.values() for ty2 in tys}
          or W.attach_of(ty) is not None
          for _s, ty in worn_pairs),
      "and every worn type is either enumerated or attachable")
check(hand_wears.get(False, 0) == 0 and hand_wears.get(True, 0) >= 49,
      "EVERY hand wear (slots 0/1) is an attachable type -- the classifier "
      "read from the exe, holding against the wire it never saw",
      f"{dict(hand_wears)}")
check(armour_nocomp == 0,
      "slots 2..5 are composite in every single wear (retail 100%)")
check(head_split.get(True, 0) >= 658 and head_split.get(False, 0) >= 132,
      "the head slot goes BOTH ways under ONE wire type -- >= 658 composite "
      "vs >= 132 attach wears, discriminated by the FLAG",
      f"{dict(head_split)}")
check(slot_type.get((3, 19), 0) >= 5 and slot_type.get((5, 19), 0) >= 5,
      "the anomaly stands: legs-typed items worn on the Boots AND Gloves "
      "slots (three distinct items, one agent, 20260817T231139) -- the "
      "slot is a hanger, or these would draw on the feet and hands",
      f"boots19={slot_type.get((3, 19), 0)} gloves19={slot_type.get((5, 19), 0)}")

# ---------------------------------------------------------------- section 4
if table is not None:
    print("== 4. the archive join: the record is authoritative ==")
    check(flag_comp.get((True, False), 0) == 0
          and flag_comp.get((False, True), 0) == 0
          and flag_comp.get((True, True), 0) >= 5528
          and flag_comp.get((False, False), 0) >= 181,
          "flags bit 2 <=> fileId-indexes-the-record-table, ZERO mixed "
          "cells over the whole corpus", f"{dict(flag_comp)}")
    measured = collections.defaultdict(set)
    for (wt, rt), _n in type_rectype.items():
        measured[wt].add(rt)
    check(dict(measured) == {k: set(v)
                             for k, v in W.RECORD_TYPES_OF_WIRE.items()},
          "wire-type -> record-type sets EQUAL wearmap's table both ways -- "
          "no pair missing, no pair invented",
          f"measured={dict(measured)}")
    check(type_rectype.get((16, 17), 0) >= 435
          and type_rectype.get((16, 19), 0) >= 223,
          "ONE wire type (16) -> TWO record types: the client cannot derive "
          "the record from the type",
          f"17:{type_rectype.get((16, 17), 0)} 19:{type_rectype.get((16, 19), 0)}")
    check(type_rectype.get((7, 15), 0) >= 1153
          and type_rectype.get((44, 15), 0) >= 97,
          "TWO wire types (7, 44) -> ONE record type (15): nor the type "
          "from the record. Many-to-many both ways ends the derivation "
          "question")
    import agents   # noqa: E402
    for key, slot in (("warrior_body", 2), ("warrior_boots", 3),
                      ("warrior_legs", 4), ("warrior_gloves", 5),
                      ("warrior_head", 6)):
        row = agents.item_template(key)
        rt = table.records[row["file_id"] & MASK].type
        W.check_wear(slot, row["item_type"], row["flags"], record_type=rt)
        check(True, f"{key}: slot {slot}, type {row['item_type']}, record "
                    f"type {rt} -- the served row passes the full check")

    # ---------------------------------------------------------- section 5
    print("== 5. the type-45 (costume head) taxonomy, and it has no third "
          "kind ==")
    # §9.10 sorted the costume-head ids into three kinds by how the RECORD
    # sits in the composite table, and carried the third as an open item for
    # weeks: "record type 17 OUTSIDE any run, and neither of the two tested".
    # §9.24 closed it at a desk. These are the two facts the closure rests on,
    # pinned so a rebuilt archive cannot quietly change them.
    t45 = sorted(i for i in t45_ids if i < len(table.records))
    if len(t45) < 20:
        LEDGER.skip("the type-45 taxonomy", f"only {len(t45)} id(s) in the "
                    f"corpus -- the census needs the whole vault")
    else:
        rtypes = {i: table.records[i].type for i in t45}
        check(set(rtypes.values()) == {17, 19},
              f"every one of the {len(t45)} type-45 records is record type "
              f"17 or 19, and nothing else",
              f"{sorted(set(rtypes.values()))}")
        if t is not None:
            comp = t["s_components"]
            byty = {rt: {comp[table.records[i].type] for i in t45
                         if rtypes[i] == rt} for rt in (17, 19)}
            check(byty == {17: {2}, 19: {1}},
                  "and the COMPONENT is a function of the record type alone "
                  "-- 17 -> 2, 19 -> 1, with no exceptions. That is the whole "
                  "closure: component comes from s_components[hdr>>22], a "
                  "field of the record, so no property of the TABLE's layout "
                  "(run membership included) can reach the dressing path",
                  f"{byty}")
        unresolved = [(i, sex) for i in t45 for sex in (0, 1)
                      if table.records[i].base_file(sex) is None]
        check(not unresolved,
              f"and all {len(t45)} resolve geometry for BOTH sexes -- so none "
              f"of them is a degenerate record that would have predicted a "
              f"visible failure",
              f"unresolvable: {unresolved[:6]}")
        shared = [i for i in t45 if 0 not in table.records[i].files
                  and 5 not in table.records[i].files]
        check(shared,
              f"including {len(shared)} that carry NO per-sex slot and "
              f"resolve only through the SHARED slot {cpsdata.SHARED_SLOT} "
              f"-- the shape that looked degenerate at a glance and is not. "
              f"A census that found none of these would be reading a "
              f"different archive",
              f"{shared}")

sys.exit(LEDGER.verdict())
