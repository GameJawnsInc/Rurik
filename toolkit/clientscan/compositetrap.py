r"""Watch the composite pipeline resolve a character, in a LIVE client.

    python toolkit/clientscan/compositetrap.py --wait --seconds 240
    python toolkit/clientscan/compositetrap.py --pid 1234 --selftest

WHY THIS EXISTS. `studies/playercomposite/FINDINGS.md` §4.12 is the arc's last
honest unknown and it is one sentence: **"Nothing here was checked against a
running client. Every claim is static or archive-side. The cheapest
confirmation is a breakpoint on `0x00833420` during a character load, logging
`(id, record)` pairs."** Everything the arc built rests on two data files and a
disassembly: the composite table parsed off disk (§1.18), the type→component
map read out of `.rdata` (§1.20), the equipment path traced through
`m_slotItemData` (§9.2). All of it predicts what the CLIENT will ask for. None
of it has ever watched the client ask.

WHAT IT DOES. It is a debugger, and it is `commandertrap.py`'s machinery
re-used rather than re-written -- `DebugActiveProcess` plus EXECUTE breakpoints
in DR0..DR3. **Nothing is written into the client**: no `int3` patch, no code
cave, no DLL, no thread. That matters here more than usual, because the bytes
this arc reads are the bytes a patch would mutate.

THE TWO SITES, both `__cdecl`, both re-read from the image this session:

    0x008332E0  f(type, race, prof, *outCount) -- the BASE lookup.
                Bounds asserted by ArenaNet: `prof < 0xB` (CpsData:392) and
                `type < 0x14` (:393), out non-null (:394). This is the
                assembly ORDER: one call per component the identity needs.
    0x00833420  f(index) -> s_items + index*48 -- the RECORD resolver.
                `index < [0x00BF980C]` asserted (CpsData:432/:438 plus an
                inlined Array.h:587). The equipment path reaches HERE with
                `ItemData.fileId` unmodified (§2 step E), so an equipped
                armour piece's composite index arrives at this site and
                nowhere else.

At each breakpoint `push ebp` has NOT executed, so `[esp]` is the return
address and the arguments start at `[esp+4]`. The record site also reads the
resolved record out of the live process -- `[0x00BF9804] + index*48`, first
dword -- so the hit carries `hdr>>22`, the composite TYPE, which is the number
§9.2 says decides the component. That is the `(id, record)` pair §4.12 asked
for, resolved by the client's own table in the client's own memory.

THE PREDICTIONS, stated here before the run because a probe with no stated
expectation can be rationalised into agreeing with anything afterwards. On a
loopback character load with `EQUIP_ARMOUR` on, our server declares five
composite items (`content/items.toml`, masked file ids 91, 90, 94, 92, 93) and
wears them in slots 2..6:

  P1  The base lookup FIRES, and its `type` arguments are drawn from the
      static set {1 or 2 (shell), 3, 4, 5, 6 (base pieces), 9, 10, 11 (face),
      12, 13 (hair)} -- §2 step C's table. A type outside that set refutes the
      table.
  P2  The shell lookup asks type **1**, not 2 -- §7's arg0 answer ("author
      against type 1"), whose whole evidence is six static call sites.
  P3  `prof` and `race` are CONSTANT across one character's lookups and inside
      ArenaNet's own bounds (prof < 11, race < the runtime bound).
  P4  The record resolver fires with our five armour indices **91, 90, 94, 92,
      93**, and the record types read back from the client's own table are
      **15, 14, 18, 16, 17** in that order -- the exact pairs
      `test_wearmap.py` §4 pins from the archive. This is the one that makes
      the runtime check worth spending: it closes the loop archive -> wire ->
      client memory on the same five numbers.
  P5  No `0x00833420` index is >= 3803, and none carries bit 31 (§9.1) --
      the client asserts both; seeing it never approach them is the weaker
      but free half.

REFUTED IF: the shell lookup asks type 2 in world (kills §7); a record index
resolves to a type the static table does not pair with its wire type (kills
§9.2's "the record is authoritative" in the only place it could be tested);
or the base lookup never fires while the character visibly loads (kills the
site attribution, and no verdict is given about anything downstream).

THE THIRD AND FOURTH SITES: WHAT THE OVERRIDE ACTUALLY DOES TO THE ROW
---------------------------------------------------------------------
§9.9 and §9.10 closed WHICH records a costume causes to be fetched, and both
ended on the same sentence: whether the override REPLACES the armour row or
MERGES with it cannot be told from the record site, because both records are
fetched for every component and the resolver cannot say which one survives.
The surviving one is written HERE.

`0x0082EDA0` is `CpsBase::__thiscall f(slot, itemId, arg2)`, `ret 0xc`, and it
asserts its own bound: **`CpsBase:173  slot < arrsize(m_slotItemId)`** with
`cmp esi,9`. It owns three parallel nine-slot arrays that are contiguous and
close to the byte:

    +0x24 .. +0xB3   m_slotItemData[9], 16 bytes each  (ArenaNet's name, :147/:156)
    +0xB4 .. +0xD7   m_slotItemId[9],   one dword each (ArenaNet's name, :173)
    +0xD8 .. +0xFB   the costume override file ids[9]  (§9.2's CpsBase+0xD8)

and §9.2's "+0x99 / +0xA9 dye bytes" resolve inside the first of them: 0x99 is
`m_slotItemData[7] + 5` and 0xA9 is `m_slotItemData[8] + 5` — byte 1 of each
costume slot's OWN row, which is the dye tint. The costume's dye is not a
loose pair of fields; it is read back out of the costume slot's cache row.

The override is applied at `0x0082EFCA` and it is FIELD BY FIELD, which is why
"replace or merge" has no one-word answer:

    mov eax,[edi+ebx*4]      ; override[slot], ebx = slot + 0x36 -> +0xD8
    test eax,eax / je        ; zero -> the armour keeps the slot
    or  edx,0x20000006       ; flags  MERGED (an OR, not an assignment)
    mov [ebp-8],eax          ; fileId REPLACED outright
    ... [edi+0xA9] if slot 4, else [edi+0x99]   ; dye REPLACED from the costume row
                             ; the TYPE byte is never touched -- it stays the
                             ; armour item's, carried through from [eax+4]

and the four dwords land in the row at `[edx+edi+0x24]` at one of two exits:
`0x0082F0F9` when the slot's item CHANGED (the load path, `m_slotItemId[slot]`
still 0) and `0x0082F0A3` when the same item was re-set. Both are armed;
leaving one off would make a silent path look like an absent one.

  S2  `m_slotItemId` holds OUR wire item ids at OUR wire slots — 3..7 in
      slots 2..6, 8 in slot 7, 9 in slot 8. A different arrangement means
      CpsBase re-indexes the wire slot and §9.2's slot vocabulary needs a
      second column. This is not bookkeeping: the dye branch above singles out
      **slot 4**, which on the wire is LEGS, and reads the costume HEAD's row
      for it. Either that is what the client does, or the index is not the
      wire slot, and S2 is what tells them apart.
  S3  REPLACE, on the file id: an overridden slot's row carries the COSTUME's
      record (2805..2808 / 2654), never the armour's (90..94). This is the one
      §9.9 and §9.10 could not reach.
  S4  CARRY-THROUGH, on the type byte: the same row's type byte is the
      ARMOUR's wire type (7/4/19/13/16), never the costume's 44/45. The
      sharpest of the set, because it is the single field where the armour
      wins — and it is what makes the answer per-field rather than one word.
  S5  The flags carry 0x20000006. **Stated with its own limit: this run
      CANNOT separate the OR from an assignment**, because our armour rows and
      our costume rows both declare 0x20001006, so both readings predict the
      same dword. The `or` at 0x0082EFD4 is static evidence only; the
      discriminator would be an armour row carrying a bit outside 0x20001006.
  S6  The override array says WHERE the five-record run expands. Four
      DISTINCT ids at slots 2..5 means the expansion happened at registration
      and is visible here; the same id repeated, or non-zero only at 7/8,
      means it happens downstream and §9.9's "walks from a computed run base"
      is sited in the wrong function. Both outcomes are results.
  S7  The dye tint is a THREE-WAY discriminator our content rows already
      carry: armour 19, `costume_body` 0, `costume_head` 35. So an overridden
      slot reading **35** proves both that the dye comes from the costume row
      and that the +0xA9 branch really is the head costume's. **The body half
      is NOT decisive and says so: `costume_body` declares tint 0, which is
      also what an unwritten row holds**, so slots reading 0 are ambiguous
      between "the costume's tint" and "row 7 not built yet". The head half
      carries S7 alone.

THE CONTROL, and it is `commandertrap.py`'s lesson wired in rather than
restated: **the base lookup MUST fire.** It runs for every composited
character the client draws, ours included. If it never hits, the instrument is
unproven and NO verdict is given about the record site -- "it never happened"
and "we cannot see it happen" look identical from here.

Windows, standard library only (`ctypes`, via `commandertrap`'s machinery and
`harness/keytap.py`'s read-only reader). Read-only against the target's memory;
the only thing it writes anywhere is DR0..DR3/DR7 in the target's own thread
contexts, and it clears them on detach.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))

import commandertrap as ct                                   # noqa: E402

IMAGE_BASE = ct.IMAGE_BASE

# The two globals the record resolver itself reads (0x0083347D / 0x0083343F).
RECORD_BASE_PTR = 0x00BF9804
RECORD_COUNT_PTR = 0x00BF980C
RECORD_STRIDE = 48          # `lea eax,[esi+esi*2]; shl eax,4` at 0x00833477
TYPE_SHIFT = 22             # hdr >> 22 -- cpsdata.Record.type
FILE_ID_RESERVED_BIT = 0x80000000

#: §2 step C's table: every composite type an identity's base lookup may ask
#: for. P1 is refuted by anything outside it.
BASE_TYPES = frozenset({1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13})

#: What our own server declares and wears (content/items.toml masked file ids
#: -> the record type test_wearmap §4 pins from the archive).
OUR_ARMOUR = {91: 15, 90: 14, 94: 18, 92: 16, 93: 17}

# --- CpsBase, for the slot-cache sites -------------------------------------
# The three arrays are contiguous and the arithmetic closes exactly:
# 0x24 + 9*16 = 0xB4 = m_slotItemId, and 0xB4 + 9*4 = 0xD8 = the override
# array. `CpsBase:173 slot < arrsize(m_slotItemId)` is ArenaNet's own bound
# and `cmp esi,9` at 0x0082EDAE is its value.
CPS_SLOTS = 9
CPS_ITEMDATA = 0x24
CPS_ROW = 16
CPS_ITEMID = 0xB4
CPS_OVERRIDE = 0xD8
#: `or edx,0x20000006` at 0x0082EFD4 -- what an overridden row must carry.
COSTUME_FLAG_BITS = 0x20000006

#: authsrv.py's own numbering, MIRRORED here (a clientscan tool does not import
#: the server) and cross-checked against that file's source by
#: test_compositetrap §6, so drift goes red rather than quiet: equip slot ->
#: the wire item id our server puts in it. 3..7 are STARTER_ARMOUR; 8 and 9
#: arrive only with --costume / --costume-head.
OUR_SLOT_ITEM = {2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}
#: The same slots -> the masked composite record content/items.toml declares.
OUR_SLOT_RECORD = {2: 91, 3: 90, 4: 94, 5: 92, 6: 93}
#: ... and the wire item type, which S4 says survives the override untouched.
OUR_SLOT_TYPE = {2: 7, 3: 4, 4: 19, 5: 13, 6: 16, 7: 44, 8: 45}
#: The two costume records we wear, by the slot that names them.
OUR_COSTUME_RECORD = {7: 2806, 8: 2654}
#: content/items.toml's declared dye tints. Three distinct values is what
#: makes S7 a discriminator rather than a description -- but 0 is also the
#: value of an unwritten row, which is exactly why the body half is weak.
TINT_ARMOUR = 19
TINT_COSTUME_BODY = 0
TINT_COSTUME_HEAD = 35


def _slid(va):
    return va + ct.SLIDE


def _cap_getids(ctx, reader):
    """(type, race, prof) off the live stack, plus the return address."""
    w = ct._dw(reader, ctx.Esp, 5)
    if not w:
        return {"VERDICT": "unreadable stack"}
    ret, ty, race, prof, out = w
    ok = ty in BASE_TYPES
    return {
        "return address (VA)": ct.unslide(ret),
        "type": ty, "race": race, "prof": prof,
        "out non-null": bool(out),
        "VERDICT": (f"type {ty} race {race} prof {prof}"
                    + ("" if ok else "  <-- OUTSIDE the step-C table (P1)")),
    }


def _cap_record(ctx, reader):
    """The index argument AND the record the client's own table resolves.

    This is §4.12's `(id, record)` pair. The record is read through the
    client's own base pointer rather than our parsed copy, so a disagreement
    would be a real finding rather than a bookkeeping error.
    """
    w = ct._dw(reader, ctx.Esp, 2)
    if not w:
        return {"VERDICT": "unreadable stack"}
    ret, idx = w
    base = ct._dw(reader, _slid(RECORD_BASE_PTR), 1)
    count = ct._dw(reader, _slid(RECORD_COUNT_PTR), 1)
    out = {"return address (VA)": ct.unslide(ret), "index": idx,
           "record count": count[0] if count else None}
    if idx & FILE_ID_RESERVED_BIT:
        out["VERDICT"] = f"index 0x{idx:08X} carries the RESERVED BIT (P5)"
        return out
    if not base or not base[0] or (count and idx >= count[0]):
        out["VERDICT"] = f"index {idx} out of range or table not loaded (P5)"
        return out
    hdr = ct._dw(reader, base[0] + idx * RECORD_STRIDE, 1)
    if not hdr:
        out["VERDICT"] = f"index {idx}: record unreadable"
        return out
    ctype = hdr[0] >> TYPE_SHIFT
    out["hdr"] = hdr[0]
    out["composite type"] = ctype
    note = ""
    if idx in OUR_ARMOUR:
        note = ("  <-- OUR armour piece, type MATCHES (P4)"
                if OUR_ARMOUR[idx] == ctype else
                f"  <-- OUR armour piece but type {ctype} != "
                f"{OUR_ARMOUR[idx]} (P4 REFUTED)")
    out["VERDICT"] = f"index {idx} -> composite type {ctype}{note}"
    return out


def _cap_slotcache(ctx, reader):
    """The row the client just wrote, read back out of CpsBase itself.

    Both exits are reached with `edi` = the CpsBase instance and `esi` = the
    slot, after all four stores. The row is recomputed from `esi` rather than
    trusted from `edx` (which the two paths restore differently), and `edx` is
    captured beside it so a disagreement would show rather than hide.
    """
    cps, slot = ctx.Edi, ctx.Esi
    out = {"CpsBase": cps, "slot": slot, "edx (slot*16)": ctx.Edx}
    if slot >= CPS_SLOTS:
        out["VERDICT"] = (f"slot {slot} is outside ArenaNet's own bound of "
                          f"{CPS_SLOTS} (CpsBase:173) -- site attribution is "
                          f"wrong, or this is not CpsBase")
        return out
    row = ct._dw(reader, cps + CPS_ITEMDATA + slot * CPS_ROW, 4)
    ids = ct._dw(reader, cps + CPS_ITEMID, CPS_SLOTS)
    ovr = ct._dw(reader, cps + CPS_OVERRIDE, CPS_SLOTS)
    args = ct._dw(reader, ctx.Ebp + 4, 3)      # [ebp+8], [ebp+0xc], [ebp+0x10]
    if not row or not ids or not ovr:
        out["VERDICT"] = f"CpsBase 0x{cps:08X} unreadable"
        return out
    out["item id (arg1)"] = args[1] if args else None
    out["file id"] = row[0]
    out["record"] = row[0] & ~FILE_ID_RESERVED_BIT
    out["type byte"] = row[1] & 0xFF
    out["dye tint"] = (row[1] >> 8) & 0xFF
    out["dye colors"] = (row[1] >> 16) & 0xFFFF
    out["row+8"] = row[2]
    out["flags"] = row[3]
    out["m_slotItemId"] = list(ids)
    out["override"] = list(ovr)
    over = ovr[slot]
    mark = ""
    if over:
        mark = ("  <-- OVERRIDDEN, row carries the override"
                if (row[0] & ~FILE_ID_RESERVED_BIT) ==
                   (over & ~FILE_ID_RESERVED_BIT)
                else f"  <-- override 0x{over:08X} SET but the row kept "
                     f"0x{row[0]:08X} (S3 REFUTED)")
    out["VERDICT"] = (
        f"slot {slot} item {out['item id (arg1)']} -> file 0x{row[0]:08X} "
        f"(record {out['record']}) type {out['type byte']} "
        f"tint {out['dye tint']} flags 0x{row[3]:08X}{mark}")
    return out


SITES = {
    "getids": ct.Site(
        "getids", 0x008332E0, bytes.fromhex("558bec538b5d10"),
        "the BASE lookup f(type, race, prof, *out) -- THE CONTROL and the "
        "assembly order (§2 step C). If this never fires, nothing below it "
        "means anything.", _cap_getids),
    "record": ct.Site(
        "record", 0x00833420, bytes.fromhex("558bec568b7508"),
        "the RECORD resolver f(index) -> s_items + index*48 -- §4.12's "
        "`(id, record)` pair, with the record read out of the client's own "
        "table", _cap_record),
    "cache": ct.Site(
        "cache", 0x0082F0F9, bytes.fromhex("8b0756ff500885db7408"),
        "the m_slotItemData row written on the CHANGE path -- the slot's item "
        "differs from what was there, which is every slot on a load. This is "
        "where the costume override either wins or does not (§9.9/§9.10's "
        "open question).", _cap_slotcache),
    "cachesame": ct.Site(
        "cachesame", 0x0082F0A3, bytes.fromhex("8b0756ff500c5f5e5b"),
        "the same row written on the RE-SET path -- the slot already held "
        "this item id. Armed beside `cache` so a path that never runs is "
        "reported as never running rather than as absent.", _cap_slotcache),
}
CACHE_SITES = ("cache", "cachesame")
DEFAULT_SITES = ("getids", "record")


def _timeline(sites, hits, limit=80):
    """Every record fetch in TIME order: `+t  index -> composite type`.

    `commandertrap._report` summarises any site with more than a dozen hits
    into a census, which is the right call for a repeated event and the wrong
    one for this question -- an EQUIP CHANGE rebuilds the composite seconds
    after the load burst, and telling the two apart needs the clock the
    census drops. So this prints the record site's hits with their offsets
    and nothing else, and it is the only place the rebuild is visible.
    """
    order = [s.name for s in sites]
    rows = [h for h in hits
            if order[h["slot"]] == "record" and h.get("cap")]
    if not rows:
        return []
    t0 = min(h.get("t", 0.0) for h in hits)
    out = ["", "RECORD FETCHES, in time order "
           f"({len(rows)}; a fetch well after the load burst is a REBUILD)"]
    for h in rows[:limit]:
        c = h["cap"]
        out.append(f"  +{h.get('t', 0.0) - t0:7.2f}s  index "
                   f"{c.get('index')!s:>5}  -> composite type "
                   f"{c.get('composite type')}")
    if len(rows) > limit:
        out.append(f"  ... {len(rows) - limit} more not listed")
    return out


def _cache_timeline(sites, hits, limit=60):
    """Every slot-cache write in TIME order.

    The ORDER is load-bearing for S7 and nothing else records it: the costume
    slots' rows are the source of the dye the armour slots copy, so a run that
    built slot 2 before slot 7 would read an unwritten row and the tint would
    mean nothing. Printing the order lets the next reader check that rather
    than assume it.
    """
    order = [s.name for s in sites]
    rows = [h for h in hits
            if order[h["slot"]] in CACHE_SITES and h.get("cap")
            and "file id" in h["cap"]]
    if not rows:
        return []
    t0 = min(h.get("t", 0.0) for h in hits)
    out = ["", f"SLOT-CACHE WRITES, in time order ({len(rows)})"]
    for h in rows[:limit]:
        c = h["cap"]
        out.append(
            f"  +{h.get('t', 0.0) - t0:7.2f}s  [{order[h['slot']]:9}] "
            f"cps 0x{c['CpsBase']:08X} slot {c['slot']}  item "
            f"{c.get('item id (arg1)')!s:>4}  record {c['record']!s:>6}  "
            f"type {c['type byte']:>3}  tint {c['dye tint']:>3}  "
            f"flags 0x{c['flags']:08X}")
    if len(rows) > limit:
        out.append(f"  ... {len(rows) - limit} more not listed")
    return out


def _analyse_cache(sites, hits):
    """Score S2..S7 from the slot-cache hits. Returns (lines, rc or None).

    `None` means NO VERDICT -- the same discipline the base-lookup control
    enforces for P1..P5. A row nobody watched being written and a row that was
    never written look identical from here.
    """
    order = [s.name for s in sites]
    caps = [h["cap"] for h in hits
            if order[h["slot"]] in CACHE_SITES and h.get("cap")
            and "file id" in h["cap"]]
    L = []
    if not caps:
        armed = [n for n in order if n in CACHE_SITES]
        L.append(
            "CONTROL: the slot-cache writer never fired"
            + ("" if armed else " -- and neither cache site was ARMED")
            + ". NO VERDICT on S2..S7.")
        return L, None

    inst = {}
    for c in caps:
        inst.setdefault(c["CpsBase"], []).append(c)
    L.append(f"CONTROL: the slot-cache writer fired {len(caps)} time(s) "
             f"across {len(inst)} CpsBase instance(s)")
    for cps, cs in sorted(inst.items()):
        L.append(f"  0x{cps:08X}: {len(cs)} write(s), final m_slotItemId="
                 f"{cs[-1]['m_slotItemId']}")

    # The instance that wears OUR items. There can be two -- §9.6 saw the
    # character-select doll and the world agent build in one session -- and
    # scoring the doll's empty slots as a refutation would be a rig error.
    def worn(cs):
        ids = cs[-1]["m_slotItemId"]
        return sum(1 for s, i in OUR_SLOT_ITEM.items()
                   if s < len(ids) and ids[s] == i)
    best = max(sorted(inst), key=lambda k: worn(inst[k]))
    L.append(f"  scoring 0x{best:08X} -- it carries {worn(inst[best])} of our "
             f"{len(OUR_SLOT_ITEM)} slots")

    final, ids = {}, inst[best][-1]["m_slotItemId"]
    for c in inst[best]:
        final[c["slot"]] = c
    ovr = inst[best][-1]["override"]

    got = {s: ids[s] for s in range(min(CPS_SLOTS, len(ids))) if ids[s]}
    mis = {s: v for s, v in got.items() if OUR_SLOT_ITEM.get(s) != v}
    s2 = (f"REFUTED -- CpsBase re-indexes the wire slot: {mis} against our "
          f"{OUR_SLOT_ITEM}" if mis else
          f"PASS -- slots {sorted(got)} hold our own item ids at our own "
          f"wire slots")
    L.append(f"S2 m_slotItemId is the WIRE slot: {s2}")

    overridden = [s for s in sorted(final) if s < len(ovr) and ovr[s]]
    L.append(f"   override array (CpsBase+0xD8) = "
             f"{[hex(v) for v in ovr]}; non-zero at {overridden}")
    if not overridden:
        L.append("S3..S7: no slot carries an override. Either no costume was "
                 "worn (run with --costume/--costume-head) or the registry "
                 "never reached CpsBase -- NO VERDICT either way.")
        return L, None

    bad3 = {s: (final[s]["record"], ovr[s] & ~FILE_ID_RESERVED_BIT)
            for s in overridden
            if final[s]["record"] != (ovr[s] & ~FILE_ID_RESERVED_BIT)}
    kept = {s: final[s]["record"] for s in overridden
            if OUR_SLOT_RECORD.get(s) == final[s]["record"]}
    if bad3:
        s3 = f"REFUTED -- row != override at {bad3} (got, wanted)"
    elif kept:
        s3 = (f"REFUTED -- {kept} still hold the ARMOUR's own record, so the "
              f"override did not replace the file id")
    else:
        rows3 = {s: final[s]["record"] for s in overridden}
        s3 = (f"PASS -- every overridden slot's row carries the COSTUME "
              f"record: {rows3}")
    L.append(f"S3 REPLACE on the file id: {s3}")

    bad4 = {s: final[s]["type byte"] for s in sorted(final)
            if s in OUR_SLOT_TYPE and final[s]["type byte"] != OUR_SLOT_TYPE[s]}
    seen4 = {s: final[s]["type byte"] for s in overridden if s in OUR_SLOT_TYPE}
    s4 = (f"REFUTED -- {bad4} against our declared {OUR_SLOT_TYPE}" if bad4
          else f"PASS -- the armour's own wire type survives the override "
               f"({seen4}); no row carries 44/45 in a slot we did not wear "
               f"a costume in")
    L.append(f"S4 CARRY-THROUGH on the type byte: {s4}")

    bad5 = {s: hex(final[s]["flags"]) for s in overridden
            if (final[s]["flags"] & COSTUME_FLAG_BITS) != COSTUME_FLAG_BITS}
    s5 = (f"VIOLATED at {bad5}" if bad5 else
          f"PASS -- 0x{COSTUME_FLAG_BITS:08X} present on all of {overridden}")
    L.append(f"S5 the flag bits: {s5}")
    L.append("   LIMIT, stated: our armour and costume rows both declare "
             "0x20001006, so an OR and an assignment predict the SAME dword "
             "here. This run does not separate them; the `or` at 0x0082EFD4 "
             "is static evidence only.")

    vals = {s: ovr[s] & ~FILE_ID_RESERVED_BIT for s in overridden}
    armour_over = [s for s in overridden if s in OUR_SLOT_RECORD]
    distinct = sorted({vals[s] for s in armour_over})
    if not armour_over:
        s6 = ("only the costume slots themselves carry an override -- the run "
              "expansion is DOWNSTREAM of this function")
    elif len(distinct) > 1:
        s6 = (f"the run expands AT REGISTRATION and is visible here: "
              f"{len(distinct)} distinct ids across armour slots "
              f"{armour_over} -> {vals}")
    else:
        s6 = (f"one id repeated across armour slots {armour_over} "
              f"({distinct}), so the expansion is DOWNSTREAM -- §9.9's "
              f"'walks from a computed run base' is sited past this function")
    L.append(f"S6 where the five-record run expands: {s6}")

    head = [s for s in overridden if s == 4]
    tints = {s: final[s]["dye tint"] for s in overridden}
    if head and tints.get(4) == TINT_COSTUME_HEAD:
        s7 = (f"PASS, and DECISIVELY -- slot 4 reads tint "
              f"{TINT_COSTUME_HEAD}, which only `costume_head` declares, so "
              f"the +0xA9 branch is m_slotItemData[8] byte 5")
    elif head and tints.get(4) == TINT_ARMOUR:
        s7 = (f"REFUTED -- slot 4 kept the ARMOUR tint {TINT_ARMOUR}; the dye "
              f"is not replaced")
    elif head:
        s7 = (f"UNEXPECTED -- slot 4 reads tint {tints.get(4)}, neither the "
              f"armour's {TINT_ARMOUR} nor the head costume's "
              f"{TINT_COSTUME_HEAD}")
    else:
        s7 = ("NO VERDICT -- slot 4 carries no override, and it is the only "
              "slot whose tint value is unambiguous")
    L.append(f"S7 the dye tint: {s7}")
    others = {s: t for s, t in tints.items() if s != 4 and s in OUR_SLOT_RECORD}
    if others:
        L.append(f"   the body half, NOT decisive: {others} against "
                 f"`costume_body`'s {TINT_COSTUME_BODY} -- which is also what "
                 f"an unwritten row holds, so these agree without proving.")

    bad = bool(mis or bad3 or kept or bad4 or bad5
               or (head and tints.get(4) != TINT_COSTUME_HEAD))
    return L, (1 if bad else 0)


def _analyse(sites, hits):
    """Score the five predictions from the hits. Returns (lines, verdict)."""
    order = [s.name for s in sites]
    caps = {n: [h["cap"] for h in hits
                if order[h["slot"]] == n and h.get("cap")] for n in order}
    L = []
    base_hits, rec_hits = caps.get("getids", []), caps.get("record", [])

    L.append(f"CONTROL: the base lookup fired {len(base_hits)} time(s)")
    if not base_hits:
        L.append("  -> the instrument is UNPROVEN. No verdict is given about "
                 "the record site: 'it never happened' and 'we cannot see it "
                 "happen' are indistinguishable from here.")
        return L, 2

    types = [c["type"] for c in base_hits if "type" in c]
    outside = sorted({t for t in types if t not in BASE_TYPES})
    p1 = "PASS" if not outside else f"REFUTED, outside={outside}"
    L.append(f"P1 base types within step C's table: {p1} "
             f"(seen {sorted(set(types))})")

    # P2, RESTATED AFTER THE FIRST RUN (2026-08-23) -- the original form was
    # "type 1 ONLY", and it scored the first real run as a refutation of §7
    # when §7 predicts exactly what was seen. A session that logs in passes
    # through CHARACTER SELECT, and §7 names UiChModel/GmDoll as the only
    # callers that pass arg0 bit 0 = 1 -> type 2. So a type-2 lookup is
    # EXPECTED whenever the run crossed that screen, and the claim under test
    # is narrower: the in-world composite is built from type 1. Type 1 present
    # confirms it; type 2 present alongside is the UI path and is reported;
    # only type 2 with NO type 1 would refute §7. The sequence is printed in
    # time order because that is what separates the two phases -- the preview
    # is built before the world agent, and a future run can read the split off
    # this line without new code.
    shell_seq = [t for t in types if t in (1, 2)]
    shell = sorted(set(shell_seq))
    if not shell:
        p2 = "no shell lookup seen -- NO VERDICT"
    elif shell == [1]:
        p2 = ("PASS -- type 1 only; this run never built a preview doll "
              "(§7's arg0 answer holds live)")
    elif 1 in shell:
        p2 = (f"PASS -- type 1 IS built in world; type 2 also seen, which is "
              f"§7's own UI path (character select / paperdoll). Order: "
              f"{shell_seq}")
    else:
        p2 = (f"REFUTED -- type 2 and NO type 1: the in-world composite is "
              f"not the animated set §7 says it is. Order: {shell_seq}")
    L.append(f"P2 the in-world shell type: {p2}")

    profs = sorted({c.get("prof") for c in base_hits if "prof" in c})
    races = sorted({c.get("race") for c in base_hits if "race" in c})
    p3 = ("PASS" if len(profs) == 1 and len(races) == 1
          and all(p < 11 for p in profs) else "CHECK")
    L.append(f"P3 prof/race constant and in bounds: profs={profs} "
             f"races={races} {p3}")

    seen = {}
    for c in rec_hits:
        if "index" in c and "composite type" in c:
            seen[c["index"]] = c["composite type"]
    ours = {i: t for i, t in seen.items() if i in OUR_ARMOUR}
    wrong = {i: t for i, t in ours.items() if OUR_ARMOUR[i] != t}
    if wrong:
        p4 = f"REFUTED -- {wrong} against the archive's {OUR_ARMOUR}"
    elif ours:
        p4 = (f"PASS -- every resolved type matches the archive "
              f"({len(ours)} of {len(OUR_ARMOUR)} pieces seen)")
    else:
        p4 = "NOT SEEN -- no armour index reached the resolver, NO VERDICT"
    L.append(f"P4 our armour indices: resolved {sorted(ours)} of "
             f"{sorted(OUR_ARMOUR)} -- {p4}")

    cap = next((c.get("record count") for c in rec_hits
                if c.get("record count")), None)
    bad5 = [i for i in seen
            if (i & FILE_ID_RESERVED_BIT) or (cap is not None and i >= cap)]
    p5 = "PASS" if not bad5 else f"VIOLATED {bad5}"
    L.append(f"P5 every index in range (< {cap}) and no reserved bit: {p5} "
             f"({len(seen)} distinct indices)")
    shell_refuted = bool(shell) and 1 not in shell
    return L, (0 if (not outside and not wrong and not shell_refuted) else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int)
    ap.add_argument("--wait", action="store_true",
                    help="wait for a Gw.exe to appear")
    ap.add_argument("--seconds", type=float, default=240.0)
    ap.add_argument("--sites", default=",".join(DEFAULT_SITES))
    ap.add_argument("--out", help="also write the report here")
    a = ap.parse_args(argv)

    want = [s.strip() for s in a.sites.split(",") if s.strip()]
    for n in want:
        if n not in SITES:
            ap.error(f"unknown site {n!r}; have {', '.join(SITES)}")
    if len(want) > ct.MAX_SLOTS:
        ap.error(f"{len(want)} sites; the processor has {ct.MAX_SLOTS} debug "
                 f"registers. Choose from {', '.join(SITES)}.")
    sites = [SITES[n] for n in want]

    import time
    import commanderpeek
    pid = a.pid
    if pid is None:
        t_end = time.time() + (180 if a.wait else 0)
        while True:
            pids = commanderpeek.find_client_pids()
            if pids:
                if len(pids) > 1:
                    raise SystemExit(
                        f"{len(pids)} clients running {pids}. Refusing to "
                        f"guess which one -- pass --pid. Two clients is how a "
                        f"run measures the wrong process.")
                pid = pids[0]
                break
            if time.time() >= t_end:
                raise SystemExit("no Gw.exe. Start the session, or --wait.")
            time.sleep(0.25)
    print(f"pid {pid}")

    base, checked = ct.verify_sites(pid, sites)
    ct.SLIDE = base - IMAGE_BASE
    print(f"Gw.exe base 0x{base:08X} (slide 0x{ct.SLIDE:X})")
    bad = []
    for s, ok, detail in checked:
        mark = {True: "ok  ", False: "BAD ", None: "??  "}[ok]
        print(f"  {mark}{s.name:8} va 0x{s.va:08X}  {detail}")
        if ok is False:
            bad.append(s.name)
    if bad:
        raise SystemExit(
            f"REFUSING to arm: {', '.join(bad)} do not hold the instruction "
            f"bytes recorded for them. These addresses are build 38797's; a "
            f"hardware breakpoint on the wrong build does not error -- it "
            f"arms on whatever is there and reports it as the pipeline.")

    reader_h = ct.keytap.open_read(pid)

    def reader(addr, size):
        return ct.keytap.read_handle(reader_h, addr, size)

    def on_hit(trap, hit):
        site = sites[hit["slot"]]
        if site.capture and hit["ctx"] is not None:
            hit["cap"] = site.capture(hit["ctx"], reader)
        print(f"  HIT {site.name} (0x{site.va:08X})"
              + (f"  {hit['cap'].get('VERDICT', '')}" if hit.get("cap") else ""),
              flush=True)

    trap = ct.HwTrap(on_hit=on_hit)
    trap.max_hits = 400          # the base lookup runs per component
    trap.addrs = [base + (s.va - IMAGE_BASE) for s in sites]
    trap.attach(pid)
    print(f"attached; armed {len(sites)} execute breakpoints, holding "
          f"{a.seconds:.0f}s", flush=True)
    try:
        trap.pump(a.seconds)
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        trap.detach()
        ct.kernel32.CloseHandle(reader_h)
        print("detached, debug registers cleared")

    ct._report(sites, trap.hits, base, trap=trap)
    tl = _timeline(sites, trap.hits) + _cache_timeline(sites, trap.hits)
    for ln in tl:
        print(ln)
    lines, rc = _analyse(sites, trap.hits)
    clines, crc = _analyse_cache(sites, trap.hits)
    if crc is not None:
        rc = rc or crc
    lines = lines + [""] + clines
    print("\n" + "=" * 72 + "\nPREDICTIONS\n" + "=" * 72)
    for ln in lines:
        print("  " + ln)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            ct._report(sites, trap.hits, base, out=fh, trap=trap)
            for ln in tl:
                fh.write(ln + "\n")
            fh.write("\nPREDICTIONS\n")
            for ln in lines:
                fh.write("  " + ln + "\n")
        print(f"\nwritten to {a.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
