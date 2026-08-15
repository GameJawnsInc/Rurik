#!/usr/bin/env python3
"""Read the client's `s_attrib` table out of Gw.exe.

Python 3 standard library only, per the house rules -- no capstone, no pefile,
so this keeps working on a bare machine. Read-only: it opens the client binary,
never writes to it, and never launches it.

WHAT THIS SETTLES. `studies/combat/PLAN.md`'s registry carried an attribute
numbering CONTESTED between "contiguous 0-41" (OpenTyria, one witness, and what
`authsrv.ATTRIBUTE_COUNT = 42` was built on) and "gapped 0-44, ids 26/27/28
reserved" (three lineages). **Both are right, about different sets**, and this
table shows why in one read:

  * the client's index space -- what `0x003A`'s first array is bound-checked
    against, and what the per-agent record is indexed by -- is CONTIGUOUS
    0..50, 51 rows. There are no gaps in it at all.
  * the ten REAL professions own exactly 42 of those rows. That is OpenTyria's
    `Attribute_Count`, and it counts attributes, not indices.
  * the other 9 rows (26, 27, 28 and 45..50) belong to profession 11, which is
    no playable profession. Enumerate only the real professions in id order and
    you skip 26/27/28 in the middle -- which is exactly the "+3 offset from
    Dagger Mastery on" the gapped scheme describes.

So the two schemes never disagreed about a fact; they answered "how many
attributes are there" and "what may this index be". The WIRE wants the second.

THE TABLE IS LOCATED STRUCTURALLY, never by address, for the same reason
`skilltable.py` is: an address is not part of any file format and must not be
carried between builds. The conjunction a candidate must satisfy:

  * every row's dword at +0x04 equals its own row index, for all 51 rows (the
    table declares its own indices -- the same self-index idiom `s_skill` and
    `s_effect` use)
  * every row's profession byte at +0x00 is in 1..11
  * every row's flag at +0x10 is 0 or 1
  * each of professions 1..10 has EXACTLY ONE row flagged 1 (its primary)
  * the ten real professions together own exactly 42 rows

Any one of those could coincide. A false positive would have to satisfy all of
them at a 20-byte stride, including the per-profession primary count.

Row layout, measured from the client's own four accessors (the bound-check
`cmp esi, 0x33` then `lea eax,[esi+esi*4]; mov eax,[eax*4 + <base+column>]`
idiom, at VAs 0x005A9340 / 0x005A9310 / 0x005A9290 / 0x005A92C0 on build
38797, giving columns +0x00, +0x08, +0x0C, +0x10):

  +0x00  profession id (1..10 playable, 11 = none)
  +0x04  the row's own index -- self-declared
  +0x08  name string id
  +0x0C  description string id
  +0x10  1 if this is the profession's PRIMARY attribute, else 0

+0x04 is not read by any of the four accessors; it is read here because it is
what makes the location check refutable.

Output is JSON on stdout or to --out, or content rows with --emit-content.
Never write the JSON into the repo: extracted client values are ArenaNet's.
Send it to vault/ (gitignored). The content rows are a different matter -- they
are MEASUREMENTS with per-row provenance, which the gate permits; see
`toolkit/content.py` and CLAUDE.md's provenance section.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinned  # noqa: E402

find_exe = pinned.find

RECORD_SIZE = 20
EXPECTED_COUNT = 51          # CHAR_ATTRIBS; the accessors' own `cmp esi, 0x33`
REAL_PROFESSIONS = tuple(range(1, 11))
NO_PROFESSION = 11
EXPECTED_REAL = 42           # OpenTyria's Attribute_Count, derived here

# Profession names. OURS, for reading the dump -- the client resolves its own
# from string ids and nothing here depends on these being right.
PROFESSION_NAMES = {
    1: "Warrior", 2: "Ranger", 3: "Monk", 4: "Necromancer", 5: "Mesmer",
    6: "Elementalist", 7: "Assassin", 8: "Ritualist", 9: "Paragon",
    10: "Dervish", 11: "(none)",
}


def _sections(data: bytes):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    imgbase = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    off = pe + 24 + optsz
    out = []
    for i in range(nsec):
        s = data[off + 40 * i: off + 40 * (i + 1)]
        vsize, vaddr, rsize, raw = struct.unpack_from("<IIII", s, 8)
        out.append((imgbase + vaddr, max(vsize, rsize), raw, rsize))
    return out


def parse_record(data: bytes, base: int, index: int) -> dict:
    r = base + index * RECORD_SIZE
    prof, self_index, name_id, desc_id, primary = struct.unpack_from("<5I", data, r)
    return {
        "id": index,
        "profession": prof,
        "self_index": self_index,
        "name_id": name_id,
        "description_id": desc_id,
        "is_primary": bool(primary),
    }


def _plausible(data: bytes, off: int) -> bool:
    """The whole conjunction, at one candidate file offset."""
    try:
        rows = [parse_record(data, off, i) for i in range(EXPECTED_COUNT)]
    except struct.error:
        return False
    if any(r["self_index"] != i for i, r in enumerate(rows)):
        return False
    if any(not 1 <= r["profession"] <= NO_PROFESSION for r in rows):
        return False
    for p in REAL_PROFESSIONS:
        if sum(1 for r in rows if r["profession"] == p and r["is_primary"]) != 1:
            return False
    real = sum(1 for r in rows if r["profession"] != NO_PROFESSION)
    return real == EXPECTED_REAL


def locate_table(data: bytes):
    """(file_offset, count) for `s_attrib`, or raise.

    Scans initialised data at 4-byte steps. The self-index run is what makes
    this cheap: row 0's +0x04 must be 0 and row 1's must be 1, which rejects
    almost every offset before the expensive checks run.
    """
    hits = []
    span = EXPECTED_COUNT * RECORD_SIZE
    for _vaddr, _vsize, raw, rsize in _sections(data):
        if not rsize:
            continue
        start, end = raw, min(raw + rsize, len(data)) - span
        off = start
        while off <= end:
            # cheap gate first: rows 0 and 1 declare indices 0 and 1
            if (struct.unpack_from("<I", data, off + 4)[0] == 0
                    and struct.unpack_from("<I", data, off + RECORD_SIZE + 4)[0] == 1
                    and _plausible(data, off)):
                hits.append(off)
            off += 4
    if not hits:
        raise SystemExit(
            "s_attrib not found. Every constraint is structural, so a miss "
            "means the layout moved -- re-read the four accessors "
            "(ConstAttrib.cpp's `index < arrsize(s_attrib)` asserts name them) "
            "before trusting any number from this build.")
    if len(hits) > 1:
        raise SystemExit(f"s_attrib is ambiguous: {len(hits)} candidates at "
                         f"{[hex(h) for h in hits]}. Refusing to guess.")
    return hits[0], EXPECTED_COUNT


def build_of(data: bytes):
    """The build of this exact image, from its own bytes, or None.

    Same rule as `skilltable.build_of`: a stamp nothing checks is an
    unfalsifiable self-declaration, so the number is derived by hashing the
    image against the registry's PRISTINE hashes and an unknown image gets
    None rather than a plausible-looking guess.
    """
    import hashlib
    digest = hashlib.sha256(data).hexdigest()
    for b in pinned.BUILDS:
        if digest == b.pristine:
            return b.number
    return None


def emit_content(rows, build, exe, out_path) -> int:
    """Write vault/content/attributes.toml -- one row per attribute id.

    `client-table` provenance per row: extractor named, build recorded. These
    are MEASUREMENTS -- ids, professions, string ids and a flag -- which is the
    permitted side of CLAUDE.md's measurement/expression boundary. No authored
    text is written: the name is carried as its string id and resolved at run
    time from the owner's own archive, the pattern mapbuild.py already proves.
    """
    lines = [
        "# GENERATED -- do not hand-edit. "
        "toolkit/clientscan/attribtable.py --emit-content",
        f"# exe: {exe}",
        f"# build: {build} (derived from the image's own sha256 via "
        f"clientscan/pinned.py, never typed in)",
        f"# rows: {len(rows)} -- the client's whole s_attrib index space.",
        "# Ids are CONTIGUOUS 0..50. The 42 that belong to professions 1-10 are",
        "# what OpenTyria's Attribute_Count counts; profession 11 owns the rest.",
        "",
    ]
    for r in rows:
        lines.append(f"[attribute.{r['id']}]")
        lines.append(f"profession = {r['profession']}")
        lines.append(f"name_string_id = {r['name_id']}")
        lines.append(f"description_string_id = {r['description_id']}")
        lines.append(f"is_primary = {'true' if r['is_primary'] else 'false'}")
        lines.append(f"[attribute.{r['id']}.provenance]")
        lines.append('source = "client-table"')
        lines.append('extractor = "toolkit/clientscan/attribtable.py"')
        lines.append(f"build = {build}")
        lines.append("")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return len(rows)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", default=None,
                   help="client binary to read (read-only); defaults to the "
                        "pinned pristine build")
    p.add_argument("--out", help="write JSON here (keep it out of the repo)")
    p.add_argument("--summary", action="store_true",
                   help="print the per-profession breakdown instead of JSON")
    p.add_argument("--emit-content", metavar="PATH",
                   help="write content rows (TOML) here -- "
                        "vault/content/attributes.toml is the intended home")
    a = p.parse_args(argv)
    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    print(f"client: {a.exe}\n        ({why})\n", file=sys.stderr)

    data = Path(a.exe).read_bytes()
    base, count = locate_table(data)
    rows = [parse_record(data, base, i) for i in range(count)]

    if a.emit_content:
        build = build_of(data)
        if build is None:
            print("REFUSED: this exe's sha256 matches no PRISTINE build in "
                  "clientscan/pinned.py, so no honest `build` stamp exists.",
                  file=sys.stderr)
            return 2
        n = emit_content(rows, build, a.exe, a.emit_content)
        print(f"wrote {a.emit_content}: {n} attribute rows, build {build}",
              file=sys.stderr)
        return 0

    if a.summary:
        print(f"table at file offset {base}, {count} rows of {RECORD_SIZE}")
        by = {}
        for r in rows:
            by.setdefault(r["profession"], []).append(r)
        for prof in sorted(by):
            ids = [r["id"] for r in by[prof]]
            prim = [r["id"] for r in by[prof] if r["is_primary"]]
            shown = str(prim[0]) if prim else "--"
            print(f"  {prof:>2} {PROFESSION_NAMES.get(prof, '?'):<13} "
                  f"{len(ids):>2} attrs  primary={shown:<4} {ids}")
        real = sum(1 for r in rows if r["profession"] != NO_PROFESSION)
        print(f"\n  {real} attributes across professions 1-10 "
              f"(OpenTyria's Attribute_Count), {count} index slots in total")
        return 0

    payload = {"meta": {"exe": str(a.exe), "table_file_offset": base,
                        "record_count": count,
                        "build": build_of(data)},
               "attributes": rows}
    text = json.dumps(payload, indent=1)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}: {count} rows", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
