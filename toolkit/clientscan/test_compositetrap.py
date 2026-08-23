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

# Floor set from a real green run (18 checks, 2026-08-23).
LEDGER = checks.Ledger("composite trap", floor=18)
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

lines, _rc = t._analyse(SITES, hits(GOOD_BASE + [(2, 0, 1)], GOOD_REC))
check("REFUTED or mixed: saw [1, 2]" in "\n".join(lines),
      "MIXED SHELL: a type-2 shell lookup ALONGSIDE type 1 is reported, not "
      "averaged away -- §7's arg0 answer is what this would contest")
lines, _rc = t._analyse(SITES, hits([(2, 0, 1)] + GOOD_BASE[1:], GOOD_REC))
check("REFUTED or mixed: saw [2]" in "\n".join(lines),
      "TYPE-2 ONLY: a run whose only shell lookup is type 2 refutes §7's "
      "'author against type 1' outright -- the strongest single result this "
      "probe could return")

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

sys.exit(LEDGER.verdict())
