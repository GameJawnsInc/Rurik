"""Check the s_attrib reader, and the numbering question it settles.

    python toolkit/clientscan/test_attribtable.py
    python toolkit/clientscan/test_attribtable.py --exe <path>

Sections 1-3 are our decoder agreeing with the shape our decoder went looking
for: necessary, not sufficient. They can still fail for the right reason -- if
the locator drifts onto a lookalike run of bytes the self-index collapses, the
per-profession primary counts stop being exactly one, and the 42/9 partition
breaks.

**Section 4 is the one with no circularity in it.** The profession column lives
in `Gw.exe`; the attribute NAMES live in the owner's `Gw.dat` archive and are
resolved through `textrec`, a decoder written for an entirely different arc.
Nothing makes those two agree. The claim under test is that the 42 rows the
EXE assigns to professions 1-10 are exactly the 42 rows the ARCHIVE can name,
and that the 9 profession-11 rows resolve to nothing -- a partition drawn twice,
from two files, by two unrelated mechanisms. That is what earns the numbering
verdict in studies/combat/PLAN.md.

WHAT THE VERDICT IS. The registry carried "contiguous 0-41" (OpenTyria, the
source of `authsrv.ATTRIBUTE_COUNT = 42`) against "gapped 0-44, 26/27/28
reserved" (three lineages) as CONTESTED. Neither is wrong; they answer
different questions, and this file pins both answers:

  * the INDEX SPACE is contiguous 0..50 -- what `0x003A`'s first array is
    bound-checked against (`cmp esi, 0x33`) and what the per-agent record is
    indexed by. No gaps exist in it.
  * the ATTRIBUTE COUNT for the ten playable professions is 42, which is what
    OpenTyria counts.
  * ids 26/27/28 belong to profession 11 and have no name, so an enumeration of
    real attributes in id order skips three in the middle -- immediately before
    Dagger Mastery at 29, which is exactly the "+3 offset from Dagger Mastery
    on" the gapped scheme describes.

READ-ONLY. Opens the client binary and the archive; never writes to either,
never patches, never launches.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from attribtable import (  # noqa: E402
    EXPECTED_COUNT, EXPECTED_REAL, NO_PROFESSION, RECORD_SIZE, REAL_PROFESSIONS,
    build_of, emit_content, locate_table, parse_record,
)
import checks  # noqa: E402
import pinned  # noqa: E402

find_exe = pinned.find

# Retail attribute counts per profession. WIKI/common knowledge, and the point
# is that they are NOT derived from the table under test: Warrior and
# Elementalist have five attributes, every other profession has four.
EXPECTED_PER_PROFESSION = {1: 5, 2: 4, 3: 4, 4: 4, 5: 4,
                           6: 5, 7: 4, 8: 4, 9: 4, 10: 4}

# Two names, pinned as literals, following test_skilltable.py's precedent of
# pinning exactly two ("Power Attack", "Defy Pain") rather than a name dump --
# CLAUDE.md's measurement/expression boundary. These two carry the most
# discriminating power: STRENGTH is a primary and Warrior's, and DAGGER_MASTERY
# is the row the rival numbering scheme describes its offset from.
STRENGTH_ID, STRENGTH = 17, "Strength"
DAGGER_ID, DAGGER = 29, "Dagger Mastery"

# FLOOR 25, and it is deliberately the ARCHIVE-LESS number rather than the full
# one. A green run on 2026-08-15 executes 29: 4 structural (S1) + 13 partition
# (S2: one per playable profession, plus the primaries and the two totals) + 3
# numbering (S3) + 4 text (S4) + 5 emitter (S5). Only S4 needs `Gw.dat`, and it
# declares LEDGER.skip when the archive will not open -- so 25 is what a bare
# machine still runs, and a floor of 29 would turn "no archive" into a failure
# that names the wrong thing. Measured from the run, never guessed.
LEDGER = checks.Ledger("attribute table", floor=25)
check = checks.adopt(LEDGER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None)
    args = ap.parse_args()

    args.exe = args.exe or find_exe()[0]
    if not os.path.exists(args.exe):
        print(f"no client binary at {args.exe}")
        print("Pass --exe, or see RUNBOOK.md. This test reads the client "
              "read-only; it never patches or launches it.")
        return 1

    with open(args.exe, "rb") as fh:
        data = fh.read()
    print(f"client: {args.exe} ({len(data):,} bytes)")

    base, count = locate_table(data)
    rows = [parse_record(data, base, i) for i in range(count)]
    by_prof = {}
    for r in rows:
        by_prof.setdefault(r["profession"], []).append(r)
    print(f"s_attrib at file offset {base}, {count} rows of {RECORD_SIZE}")

    print("\n1. the table declares itself, and closes where the client says")
    check(count == EXPECTED_COUNT,
          f"{EXPECTED_COUNT} rows -- the accessors' own `cmp esi, 0x33`")
    check(all(r["self_index"] == i for i, r in enumerate(rows)),
          "every row's +0x04 equals its own index (the self-index idiom "
          "s_skill and s_effect share)")
    check(base + count * RECORD_SIZE <= len(data),
          "the whole table fits inside the image")
    # The byte-exact closure: the row after the last one is the start of
    # ConstAttrib.cpp's own __FILE__ string, which is the module whose asserts
    # name s_attrib. A stride or count that is wrong by one misses this.
    tail = data[base + count * RECORD_SIZE:
                base + count * RECORD_SIZE + 64].split(b"\0")[0]
    check(tail.endswith(b"ConstAttrib.cpp"),
          "the table ends EXACTLY where ConstAttrib.cpp's path string begins",
          f"{tail.decode('ascii', 'replace')!r} -- a check the count and the "
          f"stride must both be right to pass")

    print("\n2. the profession partition")
    for prof in REAL_PROFESSIONS:
        got = len(by_prof.get(prof, []))
        want = EXPECTED_PER_PROFESSION[prof]
        check(got == want, f"profession {prof} owns {want} attributes (got {got})")
    for prof in REAL_PROFESSIONS:
        prim = [r["id"] for r in by_prof.get(prof, []) if r["is_primary"]]
        if prof == REAL_PROFESSIONS[0]:
            check(all(len([r for r in by_prof.get(p, []) if r["is_primary"]]) == 1
                      for p in REAL_PROFESSIONS),
                  "each of the ten playable professions has EXACTLY ONE primary",
                  f"primaries: "
                  f"{ {p: [r['id'] for r in by_prof.get(p, []) if r['is_primary']] for p in REAL_PROFESSIONS} }")
        del prim
    real = sum(1 for r in rows if r["profession"] != NO_PROFESSION)
    check(real == EXPECTED_REAL,
          f"{EXPECTED_REAL} attributes across professions 1-10 -- which is "
          f"exactly OpenTyria's Attribute_Count (got {real})")
    check(len([r for r in by_prof.get(NO_PROFESSION, []) if r["is_primary"]]) == 0,
          f"profession {NO_PROFESSION} has no primary -- it is not a playable "
          f"profession")

    print("\n3. the numbering, both answers")
    ids = sorted(r["id"] for r in rows)
    check(ids == list(range(EXPECTED_COUNT)),
          "the INDEX SPACE is contiguous 0..50 with no gaps -- this is what "
          "0x003A's first array may carry")
    reserved = sorted(r["id"] for r in by_prof.get(NO_PROFESSION, []) if r["id"] < 40)
    check(reserved == [26, 27, 28],
          "ids 26/27/28 are profession 11's, sitting mid-range",
          f"{reserved} -- which is why enumerating only real attributes looks "
          f"'gapped' from here on")
    check(min(r["id"] for r in by_prof[7]) == 29,
          "and the next real id after them is 29, the row the rival scheme "
          "names its '+3 offset from Dagger Mastery' against")

    print("\n4. the archive names exactly the real ones (the independent leg)")
    try:
        import textrec
        ix = textrec.TextIndex(args.exe)
    except Exception as exc:                                   # noqa: BLE001
        LEDGER.skip("section 4: the two-file partition",
                    f"section 4: no readable archive ({exc!r}). The exe-side "
                    f"claims above still ran; the two-file partition did not.")
    else:
        with ix:
            named = {r["id"] for r in rows if ix.get(r["name_id"])}
            expect = {r["id"] for r in rows if r["profession"] != NO_PROFESSION}
            check(named == expect,
                  "the rows the EXE gives a profession are EXACTLY the rows "
                  "the ARCHIVE can name -- 42 of 51, partitioned twice by two "
                  "unrelated mechanisms",
                  f"{len(named)} named, {len(expect)} real; "
                  f"named-not-real={sorted(named - expect)}, "
                  f"real-not-named={sorted(expect - named)}")
            check(len(named) == EXPECTED_REAL,
                  f"and that partition is {EXPECTED_REAL} of {EXPECTED_COUNT}")
            got = ix.get(next(r["name_id"] for r in rows if r["id"] == STRENGTH_ID))
            check(got == STRENGTH,
                  f"id {STRENGTH_ID} resolves to {STRENGTH!r} (got {got!r})")
            got = ix.get(next(r["name_id"] for r in rows if r["id"] == DAGGER_ID))
            check(got == DAGGER,
                  f"id {DAGGER_ID} resolves to {DAGGER!r} (got {got!r})")

    print("\n5. the content emitter, stamped from the bytes")
    import tempfile
    import tomllib
    build = build_of(data)
    check(build == 38797,
          f"the build stamp is DERIVED from the image's sha256 (got {build})")
    check(build_of(b"not a client image") is None,
          "an image matching no pristine build stamps nothing -- the emitter "
          "refuses rather than writing a guessed build")
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "attributes.toml")
        n = emit_content(rows, build, args.exe, out)
        with open(out, "rb") as fh:
            doc = tomllib.load(fh)
        attrs = doc["attribute"]
        check(n == count and len(attrs) == count,
              f"one TOML table per attribute id ({count})")
        # No authored text may reach the rows: the id is committed, the string
        # is resolved at run time from the owner's own archive.
        leaked = [k for k, v in attrs.items()
                  if any(isinstance(x, str) and x not in ("client-table",
                         "toolkit/clientscan/attribtable.py")
                         for x in list(v.values()) + list(v["provenance"].values()))]
        check(not leaked,
              "no attribute NAME reaches the content rows -- id committed, "
              "string resolved at run time",
              f"rows carrying authored text: {leaked[:5]}")
        import content
        content._check_provenance("attribute", "17", dict(attrs["17"]))
        check(True, "content.py's client-table gate accepts an emitted row")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
