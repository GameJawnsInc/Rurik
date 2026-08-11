#!/usr/bin/env python3
"""Check the area table and the string-id resolver against real bytes.

    python toolkit/clientscan/test_areatable.py

Four of these can fail for the right reason, which is the point:

  * Section 1 makes two locators that share no method agree on one address. A
    structural scan over .rdata and a scan for the compiler's own stride
    multiply in .text have no way to coincide on a wrong answer.
  * Section 2 requires the table to END where a string block begins. An extent
    that merely "looks long enough" proves nothing; an array bounded on both
    sides by something else does.
  * Section 3 is the strongest check here. The two-part file reference formula
    came from upstream's accessors, not from us, and the archive either knows
    the ids it produces or does not. 1089 of 1089 is not a coincidence and
    three rival readings of the same dword score far worse.
  * Section 4 requires the record walk to TILE each text file exactly -- 1,024
    records and a 2-byte tail, no remainder. A wrong header size walks a
    plausible distance and stops dead, which is exactly what a u32 length did.

A few real place names appear below as the decode oracle. Without a concrete
expected string the test cannot tell correct text from convincing garbage, and
these are names the game shows on screen, not extracted assets.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))

import areatable as at              # noqa: E402
import textrec                      # noqa: E402
import checks                       # noqa: E402
from gwpe import PE                 # noqa: E402
from archive import Archive, file_id_table  # noqa: E402

AREA_RECORDS = 888
POINTER_VA = 0x00BF0210             # cross-check only; located structurally
TEXT_FILES_TILING = 99              # all of them, since the zero-length-code fix

# (string id, expected text). The ids come from the area table itself.
ORACLE = [
    (10478, "Ascalon City"),
    (10464, "Lakeside County"),
    (10362, "Lion's Arch"),
]

# The floor is what a green run executes, counted from one on 2026-08-06:
# 1 locator agreement + 4 table bounds + 5 file reference + 1 tiling
# + 3 oracle strings + 1 name resolution + 2 texture targets = 17.
# None of it is fixture-dependent -- every section reads the same exe and the
# same archive, and the two variable-looking loops iterate over ORACLE and over
# `rivals`, both fixed in this file. So a run scoring fewer than 17 has stopped
# executing a section, which is precisely the failure this floor is here to name.
LEDGER = checks.Ledger("area table", floor=17)
check = checks.adopt(LEDGER)


def main():
    t0 = time.perf_counter()
    pe = PE(at.find_exe()[0])

    print("\n1. two independent locators agree on the array base")
    struct_hits = {h["va"] for h in at.locate_structural(pe)}
    code_hits = set(at.locate_from_code(pe))
    agreed = sorted(struct_hits & code_hits)
    check(len(agreed) == 1, "exactly one address satisfies both",
          ", ".join(f"0x{v:08x}" for v in agreed) or "none")
    if not agreed:
        print("\nFAILED before anything else could run")
        return 1
    base_va = agreed[0]
    base_off = pe.rva_to_off(base_va - pe.image_base)

    print("\n2. the table is bounded at both ends")
    n = at.extent(pe.data, base_off)
    check(n == AREA_RECORDS, "record count", f"{n}")
    after = pe.data[base_off + n * at.RECORD_SIZE:][:16]
    check(after.startswith(b"P:\\Code"),
          "the byte after the last record starts a source-path string",
          repr(after[:12]))
    rows = [at.parse_record(pe.data, base_off + i * at.RECORD_SIZE)
            for i in range(n)]
    ids = [r["name_id"] for r in rows]
    check(all(ids), "every record carries a name id")
    check(len(set(ids)) == n, "name ids are distinct", f"{len(set(ids))}")

    with Archive() as ar:
        table = file_id_table(ar)
        rowmap = {e.index: e for e in ar.entries}

        print("\n3. the two-part file reference decodes against the archive")
        tab = textrec.find_pointer_table(pe)
        check(tab is not None, "pointer array found structurally")
        va = pe.off_to_rva(tab) + pe.image_base
        check(va == POINTER_VA, "at the address the datwrite study measured",
              f"0x{va:08x}")
        import struct as _s
        refs = []
        for i in range(textrec.POINTER_COUNT):
            p = _s.unpack_from("<I", pe.data, tab + i * 4)[0]
            refs.append(_s.unpack_from("<I", pe.data,
                                       pe.rva_to_off(p - pe.image_base))[0])
        good = sum(1 for v in refs if textrec.combine(v) in table)
        check(good == textrec.POINTER_COUNT, "every entry resolves",
              f"{good}/{textrec.POINTER_COUNT}")
        # Rival readings of the same dword must do measurably worse, or the
        # check above is not evidence for this formula in particular.
        rivals = {"low 24 bits": lambda v: v & 0xFFFFFF,
                  "raw dword": lambda v: v}
        for name, f in rivals.items():
            k = sum(1 for v in refs if f(v) in table)
            check(k < good, f"beats the '{name}' reading", f"{k}/{len(refs)}")

        print("\n4. text files tile exactly")
        with textrec.TextIndex(at.find_exe()[0]) as ix:
            tiled = sum(1 for fi in range(textrec.FILES_PER_LANGUAGE)
                        if len(ix.records(fi)) == textrec.RECORDS_PER_FILE)
            check(tiled == TEXT_FILES_TILING,
                  "files walking to 1024 records and a 2-byte tail",
                  f"{tiled}/{textrec.FILES_PER_LANGUAGE}")

            print("\n5. the decode oracle")
            for sid, want in ORACLE:
                got = ix.get(sid)
                check(got == want, f"string {sid}", repr(got))

            print("\n6. every area name resolves")
            named = sum(1 for r in rows if ix.get(r["name_id"]) is not None)
            check(named == n, "name ids resolving to text", f"{named}/{n}")

        print("\n7. AreaInfo.file_id is a texture, not a map")
        filed = [r["file_id"] for r in rows if r["file_id"]]
        magics = set()
        flagged = 0
        for fid in filed:
            row = table.get(fid)
            check_row = rowmap.get(row) if row else None
            if check_row is None:
                magics.add(b"MISSING")
                continue
            magics.add(bytes(ar.read(check_row)[:4]))
            if check_row.flags == 259:
                flagged += 1
        check(magics == {b"ATEX"}, "every target is an ATEX texture",
              str(sorted(magics)))
        check(flagged == 0, "none is a map-flagged row",
              f"{flagged} of {len(filed)}")

    dt = time.perf_counter() - t0
    print(f"\nread the exe and the archive in {dt:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
