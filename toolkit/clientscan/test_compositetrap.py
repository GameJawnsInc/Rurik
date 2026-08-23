r"""The composite trap's addresses and its verdict logic, with no client.

    python toolkit/clientscan/test_compositetrap.py

`compositetrap.py` is the instrument for playercomposite §4.12 -- the one
open item that needs a running client. This file is what can be checked
WITHOUT one, and it is two different things:

  * §1-§2 the ADDRESSES: every site's recorded bytes must be what the pinned
    image actually holds at that VA, and the two sites must decode as the
    functions the module claims (the record resolver's stride-48 arithmetic
    and its two globals; the base lookup's ArenaNet bounds). An address typo
    is otherwise invisible until a run wastes itself arming on the wrong
    instruction -- and `verify_sites` would then pass, because it compares
    the same wrong bytes against themselves.
  * §3-§4 the VERDICT LOGIC: the analyser scored against synthetic hits,
    including the sabotages that must make it go red. A probe whose analyser
    cannot fail is a probe that will agree with anything -- which is the
    rule `probes.py` exists for, applied to the reporting half.

§5 ties the prediction to the CONTENT: P4's index->type table must be what
`content/items.toml` and the archive's composite table jointly say, so the
prediction cannot quietly drift away from the rows the server actually sends.

§6-§8 do the same three jobs for the SLOT-CACHE half (the `cache`/`cachesame`
sites, S2..S8). §6 is the one worth reading: it does not merely check the
three CpsBase offsets, it checks that they CLOSE -- `0x24 + 9*16 = 0xB4` and
`0xB4 + 9*4 = 0xD8`, three contiguous nine-slot arrays -- and that §9.2's
"+0x99/+0xA9 dye bytes" land inside the first of them, on rows 7 and 8 at byte
1. Three independently-read displacements agreeing to the byte is an assertion
the artifact can refute; a list of offsets copied out of a disassembly is not.
§8 pins the slot tables to `authsrv.py`'s own source and `content/items.toml`,
including the deliberately awkward one: `costume_body`'s dye tint is 0, which
is also what an unwritten row holds, so the check exists to keep the module
honest about which half of S7 can actually decide anything.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import checks             # noqa: E402
import compositetrap as t  # noqa: E402

# Floor set from a real green run, never guessed -- 18 checks 2026-08-23,
# then 48 / 49 / 52 / 53 / 59 / 60 / 70 as the slot-cache half, the _report
# regression guard, the S2/S4/S8 restatements, S5's three readings, the
# caller map and the CLEAR analyser landed the same day.
LEDGER = checks.Ledger("composite trap", floor=70)
check = checks.adopt(LEDGER)

# ---------------------------------------------------------------- section 1
print("== 1. the recorded site bytes ARE the pinned image's bytes ==")
try:
    import pinned
    exe, why = pinned.find()
    data = open(exe, "rb").read()
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("image sections", f"pinned client unavailable: {exc}")
    data = None

if data is not None:
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    osz = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + osz + i * 40
        vs, va, rs, raw = struct.unpack_from("<IIII", data, o + 8)
        secs.append((t.IMAGE_BASE + va, max(vs, rs), rs, raw))

    def at(va, n):
        for sva, vsize, rs, raw in secs:
            if sva <= va < sva + vsize:
                off = va - sva
                if off >= rs:
                    return b"\x00" * n
                return data[raw + off:raw + off + n]
        return None

    for name, site in sorted(t.SITES.items()):
        got = at(site.va, len(site.code))
        check(got == site.code,
              f"{name}: 0x{site.va:08X} holds the recorded "
              f"{site.code.hex()} in the pinned image",
              f"image has {got.hex() if got else None}")

    print("== 2. and they decode as the functions the module claims ==")
    # The record resolver's own arithmetic: `lea eax,[esi+esi*2]; shl eax,4`
    # is stride 48, and it adds the base global the capture reads.
    body = at(0x00833477, 12)
    check(body[:3] == bytes.fromhex("8d0476")        # lea eax,[esi+esi*2]
          and body[3:6] == bytes.fromhex("c1e004")   # shl eax, 4
          and struct.unpack_from("<I", body, 8)[0] == t.RECORD_BASE_PTR,
          f"the resolver computes index*3*16 = index*{t.RECORD_STRIDE} and "
          f"adds [0x{t.RECORD_BASE_PTR:08X}] -- the stride and the base the "
          f"capture uses are read from the instruction, not assumed",
          f"bytes {body.hex()}")
    cnt = at(0x0083343F, 6)
    check(cnt[:2] == bytes.fromhex("3b35")
          and struct.unpack_from("<I", cnt, 2)[0] == t.RECORD_COUNT_PTR,
          f"and it bounds the index against [0x{t.RECORD_COUNT_PTR:08X}] -- "
          f"the count global P5 reads", f"bytes {cnt.hex()}")
    # The base lookup's ArenaNet bounds, which is why BASE_TYPES is 11 wide.
    profcmp = at(0x008332E9, 3)
    typecmp = at(0x00833302, 4)
    check(profcmp == bytes.fromhex("83fb0b") and typecmp[:3] ==
          bytes.fromhex("837d08") and typecmp[3] == 0x14,
          "the base lookup asserts prof < 0xB and type < 0x14 -- so a type "
          "argument outside BASE_TYPES is a real signal, not a decode error",
          f"prof {profcmp.hex()} type {typecmp.hex()}")
    check(max(t.BASE_TYPES) < 0x14 and len(t.BASE_TYPES) == 11,
          "BASE_TYPES sits inside the client's own type bound",
          f"{sorted(t.BASE_TYPES)}")

# ---------------------------------------------------------------- section 3
print("== 3. the analyser's verdicts on synthetic hits ==")
SITES = [t.SITES["getids"], t.SITES["record"]]


def hits(base_rows, rec_rows):
    """Synthetic hit list in the shape HwTrap produces."""
    out = []
    for ty, race, prof in base_rows:
        out.append({"slot": 0, "cap": {"type": ty, "race": race,
                                       "prof": prof}})
    for idx, ctype in rec_rows:
        out.append({"slot": 1, "cap": {"index": idx, "composite type": ctype,
                                       "record count": 3803}})
    return out


GOOD_BASE = [(1, 0, 1), (11, 0, 1), (13, 0, 1),
             (3, 0, 1), (4, 0, 1), (5, 0, 1), (6, 0, 1), (9, 0, 1)]
GOOD_REC = [(i, ty) for i, ty in t.OUR_ARMOUR.items()]

lines, rc = t._analyse(SITES, hits(GOOD_BASE, GOOD_REC))
blob = "\n".join(lines)
check(rc == 0 and "P1 base types within step C's table: PASS" in blob,
      "the predicted-good run scores rc 0 with P1 PASS", blob)
check("PASS -- type 1 only" in blob,
      "P2 reads the in-world shell as type 1")
check("P4 our armour indices: resolved [90, 91, 92, 93, 94]" in blob
      and "PASS -- every resolved type matches" in blob,
      "P4 sees all five armour pieces and matches every type")
check("P5 every index in range (< 3803) and no reserved bit: PASS" in blob,
      "P5 passes on in-range indices")

print("== 4. the sabotages, each of which MUST redden ==")
lines, rc = t._analyse(SITES, hits([], GOOD_REC))
check(rc == 2 and "UNPROVEN" in "\n".join(lines),
      "CONTROL SILENT: with no base-lookup hit the analyser refuses a "
      "verdict entirely (rc 2) even though every record hit is perfect -- "
      "'it never happened' and 'we cannot see it happen' are the same "
      "picture from here")

lines, rc = t._analyse(SITES, hits(GOOD_BASE, [(91, 14)] + GOOD_REC[1:]))
check(rc == 1 and "P4" in "\n".join(lines)
      and "REFUTED" in "\n".join(lines),
      "WRONG TYPE: an armour index resolving to a type the archive does not "
      "pair with it REFUTES P4 -- the check that would catch the record "
      "reading being wrong in the one place it can be tested live")

lines, rc = t._analyse(SITES, hits(GOOD_BASE + [(19, 0, 1)], GOOD_REC))
check(rc == 1 and "REFUTED, outside=[19]" in "\n".join(lines),
      "OUT-OF-TABLE TYPE: a base lookup for type 19 (an ARMOUR type, which "
      "step C's table does not carry) refutes P1")

lines, rc = t._analyse(SITES, hits(GOOD_BASE + [(2, 0, 1)], GOOD_REC))
blob = "\n".join(lines)
check(rc == 0 and "PASS -- type 1 IS built in world" in blob
      and "Order: [1, 2]" in blob,
      "MIXED SHELL PASSES, and this is the FIRST RUN's own correction: a "
      "type-2 lookup alongside type 1 is §7's UI path (character select), "
      "not a refutation -- the original 'type 1 ONLY' form scored the first "
      "real run as refuting the very claim it confirmed. The order is "
      "printed so the two phases can be told apart.", blob)
lines, rc = t._analyse(SITES, hits([(2, 0, 1)] + GOOD_BASE[1:], GOOD_REC))
check(rc == 1 and "REFUTED -- type 2 and NO type 1" in "\n".join(lines),
      "TYPE-2 ONLY still REFUTES: a run that builds a world composite from "
      "the near-static set contradicts 'author against type 1' outright -- "
      "the strongest single result this probe could return, and the "
      "restatement above does not soften it")

lines, _rc = t._analyse(SITES, hits(GOOD_BASE, [(0x80000005, 15)]))
check("VIOLATED" in "\n".join(lines),
      "RESERVED BIT: an index carrying bit 31 violates P5 (§9.1's namespace)")

lines, _rc = t._analyse(SITES, hits(GOOD_BASE, []))
check("NOT SEEN" in "\n".join(lines) and "NO VERDICT" in "\n".join(lines),
      "NO ARMOUR SEEN: P4 reports no verdict rather than passing vacuously "
      "-- an absent measurement is not a green one")

# ---------------------------------------------------------------- section 5
print("== 5. P4's table is the CONTENT's, not a hand-copy ==")
try:
    import agents
    import archive
    import cpsdata
    import vaultpath
    ar = archive.Archive(vaultpath.vault_path("dat_study", "Gw.dat"))
    table = cpsdata.CompositeTable.load(ar)
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("the content cross-check", f"vault unavailable: {exc}")
else:
    got = {}
    for key in ("warrior_body", "warrior_boots", "warrior_legs",
                "warrior_gloves", "warrior_head"):
        row = agents.item_template(key)
        got[row["file_id"] & 0x7FFFFFFF] = table.records[
            row["file_id"] & 0x7FFFFFFF].type
    check(got == t.OUR_ARMOUR,
          "OUR_ARMOUR is exactly what content/items.toml's five armour rows "
          "resolve to through the archive's composite table -- so changing a "
          "content row without changing the prediction goes RED here rather "
          "than producing a run that cannot fail",
          f"content says {got}, module says {t.OUR_ARMOUR}")

# ---------------------------------------------------------------- section 6
print("== 6. CpsBase's three arrays, decoded from the image ==")
if data is not None:
    check(at(0x0082EDAE, 3) == bytes.fromhex("83fe09")
          and t.CPS_SLOTS == 9,
          f"the function bounds its slot at {t.CPS_SLOTS} -- ArenaNet's own "
          f"`cmp esi,9`, the value behind `CpsBase:173 slot < "
          f"arrsize(m_slotItemId)`", f"bytes {at(0x0082EDAE, 3).hex()}")
    row = at(0x0082F0E0, 4)
    shl = at(0x0082F03F, 3)
    check(row == bytes.fromhex("89443a24") and row[3] == t.CPS_ITEMDATA
          and shl == bytes.fromhex("c1e204") and t.CPS_ROW == 1 << shl[2],
          f"m_slotItemData starts at +0x{t.CPS_ITEMDATA:02X} with a "
          f"{t.CPS_ROW}-byte row -- both read off the store's own "
          f"displacement and the shift that builds its index",
          f"store {row.hex()} shift {shl.hex()}")
    itemid = at(0x0082F05C, 3)
    ovr = at(0x0082EF21, 5)
    check(itemid == bytes.fromhex("8d4e2d") and itemid[2] * 4 == t.CPS_ITEMID
          and ovr == bytes.fromhex("ba36000000")
          and ovr[1] * 4 == t.CPS_OVERRIDE,
          f"m_slotItemId is at +0x{t.CPS_ITEMID:02X} (`lea ecx,[esi+0x2d]`) "
          f"and the costume override array at +0x{t.CPS_OVERRIDE:02X} "
          f"(`mov edx,0x36`) -- both scaled indices, not guessed offsets",
          f"itemId {itemid.hex()} override {ovr.hex()}")
    # THE CHECK THAT CAN REFUTE THE WHOLE LAYOUT. Three arrays, nine slots
    # each, and the arithmetic has to close to the byte in both joints. It
    # does -- 0x24 + 9*16 = 0xB4 and 0xB4 + 9*4 = 0xD8 -- which is why the
    # dye bytes are not loose fields: 0x99 and 0xA9 land INSIDE the first
    # array, on rows 7 and 8, at byte 1 of the packed dword. If any of the
    # three offsets were wrong this identity would miss.
    check(t.CPS_ITEMDATA + t.CPS_SLOTS * t.CPS_ROW == t.CPS_ITEMID
          and t.CPS_ITEMID + t.CPS_SLOTS * 4 == t.CPS_OVERRIDE,
          "the three nine-slot arrays are CONTIGUOUS and the arithmetic "
          "closes exactly at both joints -- an offset off by one row would "
          "break it",
          f"0x{t.CPS_ITEMDATA:02X} + 9*{t.CPS_ROW} = "
          f"0x{t.CPS_ITEMDATA + t.CPS_SLOTS * t.CPS_ROW:02X} vs "
          f"0x{t.CPS_ITEMID:02X}")
    body_dye = at(0x0082F001, 6)
    head_dye = at(0x0082EFEF, 6)
    check(body_dye[:2] == bytes.fromhex("8a87")
          and struct.unpack_from("<I", body_dye, 2)[0]
          == t.CPS_ITEMDATA + 7 * t.CPS_ROW + 5
          and head_dye[:2] == bytes.fromhex("8a87")
          and struct.unpack_from("<I", head_dye, 2)[0]
          == t.CPS_ITEMDATA + 8 * t.CPS_ROW + 5,
          "§9.2's '+0x99/+0xA9 dye bytes' ARE m_slotItemData[7]+5 and [8]+5 "
          "-- byte 1 of each costume slot's own row, i.e. its dye tint. The "
          "costume's dye is read back out of its cache row, not held loose",
          f"body {body_dye.hex()} head {head_dye.hex()}")
    slot4 = at(0x0082EFEA, 3)
    check(slot4 == bytes.fromhex("83fe04"),
          "and the branch that picks between them tests slot == 4, which on "
          "the wire is LEGS -- so S2 has to establish the index vocabulary "
          "before S7's value can be read",
          f"bytes {slot4.hex()}")
    # WRITER_CALLERS is a RETURN-address map, so every key must be the byte
    # after a `call rel32` whose target is the writer. Checked from the image
    # rather than trusted: a return address off by one names the wrong caller
    # confidently, and the whole point of the field is to name callers.
    bad = {}
    for va, why in sorted(t.WRITER_CALLERS.items()):
        ins = at(va - 5, 5)
        if not ins or ins[0] != 0xE8:
            bad[hex(va)] = f"not a call: {ins.hex() if ins else None}"
            continue
        rel = struct.unpack_from("<i", ins, 1)[0]
        if va + rel != 0x0082EDA0:
            bad[hex(va)] = f"targets 0x{va + rel:08X}"
    check(not bad and len(t.WRITER_CALLERS) == 6,
          f"all {len(t.WRITER_CALLERS)} entries of WRITER_CALLERS are the "
          f"byte after a `call 0x0082EDA0` in the pinned image -- and there "
          f"are exactly six, which is what `codescan --xrefs` finds and what "
          f"makes an UNLISTED return address a result rather than a gap",
          f"{bad}")

    orins = at(0x0082EFD4, 6)
    repl = at(0x0082EFDA, 3)
    check(orins[0] == 0x81 and orins[1] == 0xCA
          and struct.unpack_from("<I", orins, 2)[0] == t.COSTUME_FLAG_BITS
          and repl == bytes.fromhex("8945f8"),
          f"the override MERGES the flags (`or edx,0x{t.COSTUME_FLAG_BITS:08X}"
          f"`, opcode 0x81 /1 -- an OR, not a MOV) and REPLACES the file id "
          f"(`mov [ebp-8],eax`) in adjacent instructions. Per-field, which is "
          f"why 'replace or merge' has no one-word answer",
          f"or {orins.hex()} replace {repl.hex()}")

# ---------------------------------------------------------------- section 7
print("== 7. the cache analyser, and the sabotages it must redden on ==")
CSITES = [t.SITES["getids"], t.SITES["record"],
          t.SITES["cache"], t.SITES["cachesame"]]
#: THE FIXTURE IS THE FIRST RUN'S OWN READING, verbatim: CpsBase's measured
#: order (weapon, offhand, chest, LEGS, HEAD, BOOTS, gloves, costume body,
#: costume head), the item ids it held, the override array it held, and the
#: rows it wrote. Synthesising a tidier arrangement would let the analyser
#: pass on a shape the client does not produce -- and the tidier arrangement
#: is exactly what S2's first form assumed and the client refuted.
GOOD_IDS = [1, 0, 3, 5, 7, 4, 6, 8, 9]
GOOD_OVR = [0, 0, 2806, 2808, 2654, 2805, 2807, 2806, 2654]
GOOD_ROWS = {0: (39776, 15, 6),                      # the weapon, untouched
             2: (2806, 7, 0), 3: (2808, 19, 0), 4: (2654, 16, 35),
             5: (2805, 4, 0), 6: (2807, 13, 0),
             7: (2806, 44, 0), 8: (2654, 45, 35)}
CPS_ITEM = t._by_cps(t.OUR_SLOT_ITEM)


def chits(rows, ids=None, ovr=None, cps=0x0AB00000, site=2, extra=(),
          flags=None):
    """Synthetic slot-cache hits in the shape HwTrap + _cap_slotcache give."""
    ids = GOOD_IDS if ids is None else ids
    ovr = GOOD_OVR if ovr is None else ovr
    flags = flags or {}
    out = []
    for slot in sorted(rows):
        rec, tb, tint = rows[slot]
        out.append({"slot": site, "t": float(slot), "cap": {
            "CpsBase": cps, "slot": slot, "edx (slot*16)": slot * 16,
            "item id": CPS_ITEM.get(slot),
            "file id": rec, "record": rec & 0x7FFFFFFF, "type byte": tb,
            "dye tint": tint, "dye colors": 11, "row+8": 0,
            "flags": flags.get(slot, 0x20001006), "m_slotItemId": list(ids),
            "override": list(ovr)}})
    return list(extra) + out


lines, rc = t._analyse_cache(CSITES, chits(GOOD_ROWS))
blob = "\n".join(lines)
check(rc == 0 and "S2 m_slotItemId in CpsBase's measured order: PASS" in blob,
      "the predicted-good run scores rc 0 and S2 PASS", blob)
check("S3 REPLACE on the file id: PASS" in blob,
      "S3 PASSES when every overridden row carries the costume record -- the "
      "question §9.9 and §9.10 both closed on and could not reach")
check("S4 CARRY-THROUGH on the type byte: PASS" in blob,
      "S4 PASSES when the armour's own wire type survives into the row")
check("S5 the flag bits: PASS" in blob
      and "NO VERDICT between OR and copy" in blob,
      "S5 passes on the mask AND refuses the harder half -- with no "
      "--flags-clear our rows already declare the whole mask, so OR and "
      "copy-unchanged predict the same dword and the report says so instead "
      "of claiming the stronger result")
check("a CONSTANT ASSIGNMENT is refuted independently" in blob
      and "'0x1000', '0x1000'" in blob,
      "and it still gets ONE of the three readings for free from the same "
      "rows: we declare bit 0x1000, which is OUTSIDE the mask, and the built "
      "row keeps it -- an assignment would have cleared it. This is the "
      "correction to my own first statement of S5's limit, which said the "
      "run separated NOTHING")
check("expands AT REGISTRATION" in blob,
      "S6 reads four distinct override ids as the run expanding at "
      "registration time")
check("PASS, and DECISIVELY" in blob and "S7 the dye tint" in blob,
      "S7 is decisive on the HEAD half: tint 35 is a value only "
      "`costume_head` declares")
check("the body half, NOT decisive" in blob,
      "and it refuses to claim the body half, because `costume_body` declares "
      "tint 0 and so does an unwritten row -- the one place this rig agrees "
      "with itself for free")
check("S8 the null control (unoverridden slots): PASS" in blob
      and "n=1, which is small and is said rather than smoothed" in blob,
      "S8 PASSES on the weapon -- the one worn slot no costume covers -- and "
      "prints its own n, because a control of size one is still a control and "
      "is not improved by leaving the size out")

lines, rc = t._analyse_cache(CSITES, [])
check(rc is None and "never fired" in "\n".join(lines)
      and "NO VERDICT" in "\n".join(lines),
      "CONTROL SILENT: no cache hit is NO VERDICT (rc None), not a pass -- "
      "the same discipline the base-lookup control enforces for P1..P5")

bad3 = {**GOOD_ROWS, 2: (91, 7, 0)}
lines, rc = t._analyse_cache(CSITES, chits(bad3))
check(rc == 1 and "S3 REPLACE on the file id: REFUTED" in "\n".join(lines),
      "S3 SABOTAGE: a row that kept the ARMOUR's record while its override "
      "slot is set refutes REPLACE -- the single result this whole run is "
      "for, so it must be able to come out the other way")

bad4 = {**GOOD_ROWS, 2: (2806, 44, 0)}
lines, rc = t._analyse_cache(CSITES, chits(bad4))
check(rc == 1 and "S4 CARRY-THROUGH on the type byte: REFUTED"
      in "\n".join(lines),
      "S4 SABOTAGE: a costume wire type reaching an armour slot's type byte "
      "refutes the carry-through")

bad7 = {**GOOD_ROWS, 4: (2654, 16, t.TINT_ARMOUR)}
lines, rc = t._analyse_cache(CSITES, chits(bad7))
check(rc == 1 and "S7 the dye tint: REFUTED" in "\n".join(lines),
      "S7 SABOTAGE: the head slot keeping the armour tint refutes the dye "
      "replacement in the one slot where the value is unambiguous")

# S5's THREE READINGS, under the flag clear that separates them. Declared
# 0x00001006; OR predicts 0x20001006, copy predicts 0x00001006, a constant
# assignment predicts 0x20000006. All three are exercised, because a scorer
# that can only recognise the answer it expects is not a scorer.
ARM = [t.CPS_SLOT_OF_WIRE[w] for w in (2, 3, 4, 5, 6)]
t.FLAGS_CLEAR = 0x20000000
try:
    lines, rc = t._analyse_cache(CSITES, chits(
        GOOD_ROWS, flags={s: 0x20001006 for s in ARM}))
    check(rc == 0 and "OR, OBSERVED SETTING A BIT" in "\n".join(lines),
          "S5 OR: with 0x20000000 cleared from what we declared, a built row "
          "that carries it again is the client putting the bit back -- the "
          "only shape in which the `or` at 0x0082EFD4 is visible at all, "
          "since retail composite armour never lacks the mask's other bits")

    lines, rc = t._analyse_cache(CSITES, chits(
        GOOD_ROWS, flags={s: 0x00001006 for s in ARM}))
    check(rc == 1 and "COPIED UNCHANGED, the OR REFUTED" in "\n".join(lines),
          "S5 COPY: a row that keeps the cleared bit clear REFUTES the OR and "
          "reddens -- the reading the un-cleared run could not rule out")

    lines, rc = t._analyse_cache(CSITES, chits(
        GOOD_ROWS, flags={s: 0x20000006 for s in ARM}))
    check(rc == 1 and "CONSTANT ASSIGNMENT" in "\n".join(lines),
          "S5 ASSIGN: a row that is the mask and nothing else is the third "
          "reading, and it reddens too")
finally:
    t.FLAGS_CLEAR = 0

bad8 = {**GOOD_ROWS, 0: (39776, 15, 99)}
lines, rc = t._analyse_cache(CSITES, chits(bad8))
check(rc == 1 and "S8 the null control" in "\n".join(lines)
      and "REFUTED" in "\n".join(lines),
      "S8 SABOTAGE: a slot with a ZERO override whose row moved anyway "
      "refutes the null control -- without which 'every overridden row "
      "changed' has nothing to be measured against")

lines, rc = t._analyse_cache(
    CSITES, chits(GOOD_ROWS, ids=[1, 0, 3, 4, 5, 6, 7, 8, 9]))
check(rc == 1 and "REFUTED the other way" in "\n".join(lines),
      "S2 SABOTAGE, the IDENTITY direction: a later run indexing by the WIRE "
      "slot would mean the measured permutation was a fluke of one load, and "
      "the restatement has to be able to lose that way too")

lines, rc = t._analyse_cache(
    CSITES, chits(GOOD_ROWS, ids=[1, 0, 7, 6, 5, 4, 3, 8, 9]))
check(rc == 1 and "a THIRD arrangement" in "\n".join(lines),
      "S2 SABOTAGE, the OTHER direction: an arrangement that is neither the "
      "wire identity nor the measured permutation refutes it as well, and is "
      "reported as its own case rather than folded into either")

lines, rc = t._analyse_cache(
    CSITES, chits(GOOD_ROWS, ovr=[0, 0, 2806, 2806, 2806, 2806, 2806,
                                  2806, 2654]))
check("DOWNSTREAM" in "\n".join(lines),
      "S6's OTHER branch is a result, not a failure: one id repeated across "
      "the armour slots sites the run expansion past this function, which "
      "would move §9.9's reconstruction rather than refute it")

lines, rc = t._analyse_cache(CSITES, chits(GOOD_ROWS, ovr=[0] * 9))
check(rc is None and "no slot carries an override" in "\n".join(lines),
      "NO OVERRIDE: with an empty override array the analyser gives NO "
      "VERDICT on S3..S7 rather than passing them vacuously -- a run without "
      "--costume looks exactly like a costume path that never fired")

doll = chits({s: (0, 0, 0) for s in range(2, 7)},
             ids=[0] * 9, ovr=[0] * 9, cps=0x0AC00000)
lines, rc = t._analyse_cache(CSITES, chits(GOOD_ROWS, extra=doll))
check(rc == 0 and "2 CpsBase instance(s)" in "\n".join(lines)
      and "scoring 0x0AB00000" in "\n".join(lines),
      "TWO INSTANCES: §9.6 saw the character-select doll and the world agent "
      "build in one session, so the analyser picks the instance wearing our "
      "items instead of scoring the doll's empty slots as a refutation")

# REGRESSION, and it cost a completed run. `_report` keys its census on the
# captured values, and these captures hold CpsBase's nine-slot ARRAYS. The
# first live run trapped everything it was built to trap and then died in the
# census with `unhashable type: 'list'` -- after the client had exited, so
# every hit was in memory and none of it reached the page. Both sides are
# fixed (tuples here, coercion in `_report`); this proves the report survives
# the shape either way, because a formatting bug that eats a run is worse than
# a wrong number.
import io as _io                                                # noqa: E402
_bulk = []
for i in range(3):
    for h in chits(GOOD_ROWS):
        h["cap"]["m_slotItemId"] = list(h["cap"]["m_slotItemId"])
        h["cap"]["override"] = list(h["cap"]["override"])
        h.update(tid=1000 + i, dr6_agrees=True, dr6_slot=2)
        _bulk.append(h)
try:
    t.ct._report(CSITES, _bulk, t.IMAGE_BASE, out=_io.StringIO())
    _survived = True
except TypeError:
    _survived = False
check(_survived and len(_bulk) > 12,
      f"REGRESSION: _report survives a capture holding LIST values over the "
      f"census threshold ({len(_bulk)} hits) -- the exact shape that killed "
      f"the first live run of these sites after it had already collected "
      f"everything",
      f"{len(_bulk)} synthetic hits")

# ------------------------------------------------------------ section 7b
print("== 7b. the CLEAR analyser (R1..R4) and its refusals ==")
RSITES = [t.SITES["getids"], t.SITES["record"],
          t.SITES["cache"], t.SITES["clear"]]


def rhits(bursts, recs=(), writes=()):
    """Clear bursts as (t, [slots]), plus record fetches and row writes."""
    out = []
    for tt, slots in bursts:
        for i, s in enumerate(slots):
            out.append({"slot": 3, "t": tt + i * 0.01, "cap": {
                "CpsBase": 0x0AB00000, "slot": s, "item id": 0,
                "file id": 90, "record": 90, "type byte": 4, "dye tint": 19,
                "dye colors": 11, "row+8": 0, "flags": 0x20001006,
                "m_slotItemId": list(GOOD_IDS), "override": [0] * 9}})
    for tt, idx in recs:
        out.append({"slot": 1, "t": tt, "cap": {
            "index": idx, "composite type": 14, "record count": 3803}})
    for tt, s in writes:
        out.append({"slot": 2, "t": tt, "cap": {
            "CpsBase": 0x0AB00000, "slot": s, "item id": 4, "file id": 90,
            "record": 90, "type byte": 4, "dye tint": 19, "dye colors": 11,
            "row+8": 0, "flags": 0x20001006,
            "m_slotItemId": list(GOOD_IDS), "override": [0] * 9}})
    return out


GOOD_CLEAR = [(18.6, [2, 3, 4, 5, 6]), (29.6, [3])]
lines, rc = t._analyse_clear(
    RSITES, rhits(GOOD_CLEAR, recs=[(18.7, 90), (18.8, 94), (29.7, 90)]))
blob = "\n".join(lines)
check(rc == 0 and "a second reset clears FEWER slots (5 -> 1): PASS" in blob,
      "R1's in-run control: an already-empty slot returns at 0x0082EF40 "
      "before the notify, so a second reset must clear strictly fewer -- "
      "which is the shape §9.8 saw from the record side (five, then one)",
      blob)
check("R2 every clear carries item id 0: PASS" in blob,
      "R2 passes when every clear carries item id 0")
check("R3 a clear is not a write: PASS" in blob,
      "R3 passes when no row write lands inside a clear burst -- the reading "
      "that the clear path jumps past BOTH write exits")
check("R4 what the reset actually re-reads: PASS" in blob
      and "0x0082EF4B" in blob,
      "R4 places §9.8's reset-arm fetches on the vtable notify rather than on "
      "the cache being refilled, and only when writes are absent from the "
      "same window")

lines, rc = t._analyse_clear(RSITES, rhits([], recs=[(18.7, 90)]))
check(rc is None and "never fired" in "\n".join(lines)
      and "NO VERDICT" in "\n".join(lines),
      "CONTROL SILENT: no clear is NO VERDICT -- 'no reset reached the "
      "client' and 'the path is not what was read' are the same picture")

lines, rc = t._analyse_clear(
    RSITES, rhits(GOOD_CLEAR, recs=[(18.7, 90)], writes=[(18.65, 2)]))
check(rc == 1 and "R3 a clear is not a write: REFUTED" in "\n".join(lines),
      "R3 SABOTAGE: a row write inside a clear burst refutes the static "
      "reading of the clear path, and must redden rather than be explained")

lines, rc = t._analyse_clear(RSITES, rhits(GOOD_CLEAR))
check("R4 what the reset actually re-reads: NOT SEEN" in "\n".join(lines),
      "R4 with NO record fetch after a clear reports NOT SEEN and says it "
      "would contradict §9.8's own timeline -- rather than quietly passing "
      "on an absence")

lines, rc = t._analyse_clear(RSITES, rhits([(18.6, [2, 3, 4, 5, 6])],
                                           recs=[(18.7, 90)]))
check("only one clear burst seen" in "\n".join(lines),
      "and with a single burst it declines the already-empty control instead "
      "of scoring it")

lines, _rc = t._analyse_clear(
    [t.SITES["getids"], t.SITES["record"]], rhits(GOOD_CLEAR))
check(lines == [],
      "with no clear site ARMED the analyser emits nothing at all, so a run "
      "that never asked the question does not print a section implying it did")

# ---------------------------------------------------------------- section 8
print("== 8. the slot tables are authsrv's and content's, not a hand-copy ==")
import re                                                     # noqa: E402
srv = os.path.join(os.path.dirname(HERE), "authsrv", "authsrv.py")
try:
    src = open(srv, encoding="utf-8").read()
    blk = re.search(r"STARTER_ARMOUR = \((.*?)\n\)", src, re.S).group(1)
    armour = {int(s): (int(i), k) for i, k, s in
              re.findall(r"\(\s*(\d+),\s*\"([a-z_]+)\",\s*(\d+)\)", blk)}
    cslot = int(re.search(r"^COSTUME_SLOT = (\d+)", src, re.M).group(1))
    citem = int(re.search(r"^COSTUME_ITEM_ID = (\d+)", src, re.M).group(1))
    hslot = int(re.search(r"^COSTUME_HEAD_SLOT = (\d+)", src, re.M).group(1))
    hitem = int(re.search(r"^COSTUME_HEAD_ITEM_ID = (\d+)", src, re.M).group(1))
    witem = int(re.search(r"^WEAPON_ITEM_ID = (\d+)", src, re.M).group(1))
except Exception as exc:                                      # noqa: BLE001
    LEDGER.skip("the authsrv slot cross-check", f"unreadable: {exc}")
else:
    want = {s: i for s, (i, _k) in armour.items()}
    want[cslot], want[hslot], want[0] = citem, hitem, witem
    check(want == t.OUR_SLOT_ITEM,
          "OUR_SLOT_ITEM is exactly authsrv.py's STARTER_ARMOUR plus its two "
          "costume constants and the weapon -- S2 compares the client's array "
          "against what the SERVER sends, so a slot renumbered on one side "
          "has to redden here rather than quietly refute a prediction",
          f"authsrv says {want}, module says {t.OUR_SLOT_ITEM}")
    try:
        import agents
        keys = {s: k for s, (_i, k) in armour.items()}
        keys[cslot], keys[hslot] = "costume_body", "costume_head"
        keys[0] = "starter_hammer"
        rows = {s: agents.item_template(k) for s, k in keys.items()}
    except Exception as exc:                                  # noqa: BLE001
        LEDGER.skip("the content slot cross-check", f"unavailable: {exc}")
    else:
        types = {s: r["item_type"] for s, r in rows.items()}
        check(types == t.OUR_SLOT_TYPE,
              "and OUR_SLOT_TYPE is content/items.toml's own item_type per "
              "slot -- the value S4 says survives the override",
              f"content says {types}, module says {t.OUR_SLOT_TYPE}")
        recs = {s: rows[s]["file_id"] & 0x7FFFFFFF
                for s in rows if s in t.OUR_SLOT_RECORD}
        cost = {s: rows[s]["file_id"] & 0x7FFFFFFF for s in (cslot, hslot)}
        check(recs == t.OUR_SLOT_RECORD and cost == t.OUR_COSTUME_RECORD,
              "and both record tables are the content's masked file ids",
              f"content {recs} / {cost}, module {t.OUR_SLOT_RECORD} / "
              f"{t.OUR_COSTUME_RECORD}")
        allflags = {s: r["flags"] for s, r in rows.items()}
        check(allflags == t.OUR_SLOT_FLAGS,
              "and OUR_SLOT_FLAGS is the content's own flags per slot -- S5 "
              "scores the built row against what the SERVER declared, so a "
              "hand-copied value could make OR and copy look alike",
              f"content says {allflags}, module says {t.OUR_SLOT_FLAGS}")
        check(all(v | t.COSTUME_FLAG_BITS == v
                  for s, v in allflags.items() if s in t.OUR_SLOT_RECORD),
              "and EVERY armour row already contains the override's whole "
              "mask -- pinned deliberately, because it is the reason S5 needs "
              "--armour-flags-clear to say anything at all. If a future row "
              "lacked a mask bit this line reddens and somebody can drop the "
              "flag",
              f"{ {hex(v) for s, v in allflags.items() if s in t.OUR_SLOT_RECORD} }")
        alltints = {s: r["dye_tint"] for s, r in rows.items()}
        check(alltints == t.OUR_SLOT_TINT,
              "and OUR_SLOT_TINT is the content's own dye_tint per slot -- "
              "S8's null control compares an unoverridden row against it, so "
              "a hand-copied value would make the control agree by accident",
              f"content says {alltints}, module says {t.OUR_SLOT_TINT}")
        tints = (rows[2]["dye_tint"], rows[cslot]["dye_tint"],
                 rows[hslot]["dye_tint"])
        check(tints == (t.TINT_ARMOUR, t.TINT_COSTUME_BODY,
                        t.TINT_COSTUME_HEAD),
              "S7's three tints are the rows' own dye_tint values",
              f"content {tints}, module {(t.TINT_ARMOUR, t.TINT_COSTUME_BODY, t.TINT_COSTUME_HEAD)}")
        check(len(set(tints)) == 3,
              "and they are DISTINCT, which is the whole reason the tint can "
              "discriminate at all. Two rows sharing a tint would make S7 a "
              "description instead of a measurement",
              f"{tints}")
        check(t.TINT_COSTUME_BODY == 0,
              "while `costume_body`'s tint IS zero -- the value an unwritten "
              "row also holds. Pinned deliberately: it is why the module "
              "calls the body half not decisive, and if a future content "
              "edit made it non-zero this line should redden so somebody "
              "strengthens the claim rather than leaving it hedged",
              f"tint {t.TINT_COSTUME_BODY}")

sys.exit(LEDGER.verdict())
