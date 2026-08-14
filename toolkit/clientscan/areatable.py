#!/usr/bin/env python3
"""Read the client's per-map metadata array (`AreaInfo`) out of Gw.exe.

Python 3 standard library only, per the house rules. Read-only: it opens the
client binary, never writes to it, and never launches it.

WHY THIS EXISTS. studies/mapdata/FORMAT.md can enumerate all 349 map files in
the archive and name 249 of them, but only by borrowing an unlicensed upstream
table. A hundred map files are named by nobody. The client itself knows what
every map is called -- `AreaInfo.name_id` is a string id into the archive's own
text records -- so the naming problem is a static-analysis problem, not a
capture problem.

TWO INDEPENDENT LOCATORS, AND THEY MUST AGREE.

  structural  Scan .rdata at 4-byte steps for a 124-byte-stride run of records
              that satisfies eight constraints at once: four small enum fields,
              three min<=max pairs, and a populated name id. Any one could
              coincide; a false positive has to satisfy all of them across
              dozens of consecutive records.

  from code   The compiler turns `array[i]` on a 124-byte record into
              `imul reg, reg, 0x7C`, and the array base is an absolute address
              in the same neighbourhood. Scan .text for that multiply and
              collect nearby dwords that land in .rdata.

The structural scan does not know what the code scan found and vice versa. If
they name the same address, the stride and the base are both corroborated by a
witness that does not share a method with the other. If they disagree, this
tool says so rather than picking one, because a check that cannot fail is not a
check.

LAYOUT PROVENANCE. The field offsets below are UPSTREAM. Four mirrors state
them identically -- GWCA (two forks), GWToolboxpp's vendored copy, and
Py4GW_Reforged_Native -- but GWCA's own header credits `entice/gw-interface`,
so the apparent agreement is partly one ancestor counted four times. Treat the
layout as a hypothesis that this tool's constraints either fit or do not.

The interesting fields, and what each is worth:

    +0x00 campaign   +0x04 continent   +0x08 region   +0x0C type
    +0x18/+0x1C party size min/max     +0x20/+0x24 player size min/max
    +0x30/+0x34 level min/max

    +0x04 IS NO LONGER UPSTREAM, as of 2026-08-14 (studies/minimap rung S4,
    build 38797). It is the WORLD index -- the index into `s_worldData` -- and
    three of the client's own witnesses say so. `0x0084DE50` is four
    instructions long and is exactly
    `s_missionClientData[missionContext+0x230] + 0x04`; its return value goes
    straight into `[CompassMap+0x84]` (`0x008C1C78`, the constructor) and from
    there, unmodified, into the tier getter at `0x005A93E0`, whose FIRST act is
    `cmp edi, 0xa` guarding `ConstWorldMap:1313 world < WORLDS`. Separately,
    `GmMapWorld` at `0x0054E900` compares another row's `+0x04` against that
    same return value as "same world". Over all 888 rows the field takes
    {0,1,2,3,4,5,9}, every one below WORLDS=10 -- and that range test is
    deliberately the WEAK witness, because FIVE of the record's dword fields
    are always < 10 (+0x00, +0x04, +0x18, +0x20, +0x2C), so a bound identifies
    nothing and only the code does.

    The NAME "continent" is still ArenaNet-unattested: `asserts.py --grep
    '(?i)continent'` returns 0 sites (against that tool's 370-site floor).
    Everywhere the client speaks, its word is `world`.
    +0x68 file_id       -- the archive file. UPSTREAM says it is zero for
                           outposts and "many maps"; §"census" below measures
                           how true that is on our build.
    +0x74 name_id       -- string id of the map's name. The prize.
    +0x78 description_id

Output is JSON on stdout or to --out. Never write it into the repo: extracted
client values are ArenaNet's and the provenance gate is absolute. Send it to
vault/, which is gitignored.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gwpe import PE  # noqa: E402
import pinned  # noqa: E402

RECORD_SIZE = 0x7C  # 124

# Field offsets. UPSTREAM -- see the module docstring on how much that is worth.
OFF_CAMPAIGN = 0x00
OFF_CONTINENT = 0x04   # CORROBORATED from client code, not UPSTREAM -- it is the
                       # index into s_worldData. See the docstring; the blanket
                       # "UPSTREAM" on the line above does not cover this one.
OFF_REGION = 0x08
OFF_TYPE = 0x0C
OFF_FLAGS = 0x10
OFF_THUMBNAIL = 0x14
OFF_MIN_PARTY = 0x18
OFF_MAX_PARTY = 0x1C
OFF_MIN_PLAYERS = 0x20
OFF_MAX_PLAYERS = 0x24
OFF_MIN_LEVEL = 0x30
OFF_MAX_LEVEL = 0x34
OFF_FILE_ID = 0x68
OFF_NAME_ID = 0x74
OFF_DESC_ID = 0x78

# Upper bounds for the small enum and range fields. Deliberately loose: they
# only have to exclude noise, and a bound tight enough to be wrong on one real
# map would cost us the whole table.
LIMITS = {
    OFF_CAMPAIGN: 8,
    OFF_CONTINENT: 16,
    OFF_REGION: 64,
    OFF_TYPE: 32,
    OFF_MAX_PARTY: 16,
    OFF_MAX_PLAYERS: 16,
    OFF_MAX_LEVEL: 32,
}
PAIRS = ((OFF_MIN_PARTY, OFF_MAX_PARTY),
         (OFF_MIN_PLAYERS, OFF_MAX_PLAYERS),
         (OFF_MIN_LEVEL, OFF_MAX_LEVEL))

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool in
# this directory. This module used to name an absolute path into `vault/run/`,
# which was wrong twice over: it hardcoded `C:\gd\Rurik\vault` past
# `vaultpath.py` (so a moved vault or a git worktree resolved to nothing), and
# `run/` is OUR PATCHED copy -- `pinned.py` makes the pristine one canonical
# precisely because a study of the shipped client that reads our own patch is
# reading us. The two differ in nine `.text` bytes and the DH modulus.
find_exe = pinned.find
PROBE_ROWS = 64      # rows a candidate must satisfy to be scored at all
IMUL_WINDOW = 24     # bytes after an imul to look in for the array base


def u32(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]


def record_ok(blob: bytes, base: int) -> bool:
    """Does one 124-byte record look like map metadata?

    A wholly zero record passes -- index 0 is the "no map" slot and runs of
    unused slots are expected in a table indexed by a sparse id space.
    """
    if base + RECORD_SIZE > len(blob):
        return False
    if not any(blob[base:base + RECORD_SIZE]):
        return True
    for off, limit in LIMITS.items():
        if u32(blob, base + off) > limit:
            return False
    for lo, hi in PAIRS:
        if u32(blob, base + lo) > u32(blob, base + hi):
            return False
    return True


def score(blob: bytes, base: int, rows: int = PROBE_ROWS) -> int:
    """How many consecutive records from `base` look like map metadata."""
    n = 0
    while n < rows and record_ok(blob, base + n * RECORD_SIZE):
        n += 1
    return n


def locate_structural(pe: PE, section: str = ".rdata"):
    """Every .rdata offset where at least PROBE_ROWS records validate.

    Runs are collapsed to their first offset: a real table also validates when
    entered one record late, and reporting 800 near-duplicates would bury the
    answer.
    """
    s = pe.section(section)
    if not s:
        return []
    lo, hi = s["rawptr"], s["rawptr"] + s["rawsize"]
    blob = pe.data
    hits = []
    off = lo
    while off + RECORD_SIZE * PROBE_ROWS < hi:
        if score(blob, off) >= PROBE_ROWS:
            live = sum(1 for i in range(PROBE_ROWS)
                       if any(blob[off + i * RECORD_SIZE:
                                   off + (i + 1) * RECORD_SIZE]))
            named = sum(1 for i in range(PROBE_ROWS)
                        if u32(blob, off + i * RECORD_SIZE + OFF_NAME_ID))
            hits.append({"off": off, "va": pe.off_to_rva(off) + pe.image_base,
                         "live": live, "named": named})
            off += RECORD_SIZE * PROBE_ROWS
        else:
            off += 4
    return hits


def locate_from_code(pe: PE):
    """Array bases implied by `imul reg, reg, 0x7C` in .text.

    `6B /r ib` is the 8-bit-immediate three-operand imul, so the encoding is
    0x6B, a modrm byte, then the immediate -- here 0x7C, the record size. The
    base address is loaded near the multiply, so collect every dword in the
    following window that lands in .rdata and is 4-byte aligned.
    """
    text = pe.section(".text")
    rdata = pe.section(".rdata")
    if not text or not rdata:
        return {}
    lo, hi = text["rawptr"], text["rawptr"] + text["rawsize"]
    r_lo = rdata["vaddr"] + pe.image_base
    r_hi = r_lo + rdata["rawsize"]
    d = pe.data
    out = {}
    i = d.find(b"\x6b", lo, hi)
    while i != -1:
        if i + 3 <= hi and d[i + 2] == 0x7C:
            for j in range(i + 3, min(i + 3 + IMUL_WINDOW, hi - 4)):
                v = u32(d, j)
                if r_lo <= v < r_hi and v % 4 == 0:
                    e = out.setdefault(v, {"va": v, "sites": []})
                    e["sites"].append(pe.off_to_rva(i) + pe.image_base)
        i = d.find(b"\x6b", i + 1, hi)
    return out


def parse_record(blob: bytes, base: int) -> dict:
    g = lambda off: u32(blob, base + off)  # noqa: E731
    return {
        "campaign": g(OFF_CAMPAIGN),
        "continent": g(OFF_CONTINENT),
        "region": g(OFF_REGION),
        "type": g(OFF_TYPE),
        "flags": g(OFF_FLAGS),
        "thumbnail_id": g(OFF_THUMBNAIL),
        "min_party": g(OFF_MIN_PARTY),
        "max_party": g(OFF_MAX_PARTY),
        "min_players": g(OFF_MIN_PLAYERS),
        "max_players": g(OFF_MAX_PLAYERS),
        "min_level": g(OFF_MIN_LEVEL),
        "max_level": g(OFF_MAX_LEVEL),
        "file_id": g(OFF_FILE_ID),
        "name_id": g(OFF_NAME_ID),
        "description_id": g(OFF_DESC_ID),
    }


def extent(blob: bytes, base: int, limit: int = 4096) -> int:
    """How many consecutive records validate from `base`."""
    n = 0
    while n < limit and record_ok(blob, base + n * RECORD_SIZE):
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine "
                         "build, and the choice is printed")
    ap.add_argument("--out", help="write the decoded table here (use vault/)")
    ap.add_argument("--rows", type=int, default=12,
                    help="how many records to print")
    ap.add_argument("--names", action="store_true",
                    help="resolve name ids to text through Gw.dat (textrec)")
    ap.add_argument("--dat", default=None, help="archive, with --names")
    args = ap.parse_args()
    args.exe, why = ((args.exe, "given on the command line") if args.exe
                     else find_exe())

    pe = PE(args.exe)
    print(f"{args.exe}\n  ({why})")
    print(f"  {pe.arch}, image base 0x{pe.image_base:08x}, "
          f"{os.path.getsize(args.exe)} bytes")

    print("\n1. structural scan of .rdata for a 124-byte-stride table")
    hits = locate_structural(pe)
    hits.sort(key=lambda h: -h["named"])
    for h in hits[:8]:
        print(f"   VA 0x{h['va']:08x}  file 0x{h['off']:06x}  "
              f"{h['live']}/{PROBE_ROWS} live, {h['named']} with a name id")
    if not hits:
        print("   NOTHING MATCHED. The layout hypothesis or the stride is wrong;"
              " do not paper over this.")
        return 2

    print("\n2. array bases implied by `imul reg, reg, 0x7C` in .text")
    code = locate_from_code(pe)
    ranked = sorted(code.values(), key=lambda e: -len(e["sites"]))
    for e in ranked[:8]:
        print(f"   VA 0x{e['va']:08x}  {len(e['sites'])} site(s)  "
              f"first at 0x{e['sites'][0]:08x}")
    if not code:
        print("   no candidates")

    print("\n3. do the two locators agree?")
    struct_vas = {h["va"] for h in hits}
    agreed = sorted(struct_vas & set(code))
    for va in agreed:
        print(f"   BOTH: VA 0x{va:08x}")
    if not agreed:
        print("   THEY DO NOT. Report this rather than picking a winner --")
        print("   two methods disagreeing is the finding.")

    base_va = agreed[0] if agreed else hits[0]["va"]
    base_off = pe.rva_to_off(base_va - pe.image_base)
    n = extent(pe.data, base_off)
    print(f"\n4. the table at VA 0x{base_va:08x} "
          f"({'corroborated' if agreed else 'STRUCTURAL ONLY'})")
    print(f"   {n} consecutive valid records before the pattern breaks")

    rows = [parse_record(pe.data, base_off + i * RECORD_SIZE) for i in range(n)]
    live = [r for r in rows if any(r.values())]
    named = [r for r in rows if r["name_id"]]
    filed = [r for r in rows if r["file_id"]]
    print(f"   {len(live)} non-empty, {len(named)} with a name id, "
          f"{len(filed)} with a file id")
    if named:
        ids = [r["name_id"] for r in named]
        print(f"   name ids run {min(ids)}..{max(ids)}, "
              f"{len(set(ids))} distinct")
    if filed:
        f = [r["file_id"] for r in filed]
        print(f"   file ids run 0x{min(f):x}..0x{max(f):x}, "
              f"{len(set(f))} distinct")
    else:
        print("   file_id is zero in EVERY record -- upstream's claim that the "
              "client gets it from the server holds on this build.")

    if args.names:
        import textrec
        kw = {"exe": args.exe}
        if args.dat:
            kw["dat"] = args.dat
        with textrec.TextIndex(**kw) as ix:
            print(f"\n5. names, via the text records "
                  f"(pointer array VA 0x{ix.table_va:08x})")
            got = 0
            for r in rows:
                r["name"] = ix.get(r["name_id"])
                r["name_kind"] = ix.kind_of(r["name_id"])
                got += r["name"] is not None
            print(f"   {got} of {n} name ids resolved to text")
            unresolved = {}
            for r in rows:
                if r["name"] is None:
                    k = r["name_kind"]
                    unresolved[k] = unresolved.get(k, 0) + 1
            for k in sorted(unresolved, key=lambda x: (x is None, x)):
                print(f"     {got and ''}unresolved with record kind "
                      f"{'unreachable' if k is None else hex(k)}: "
                      f"{unresolved[k]}")

    print(f"\n6. first {args.rows} non-empty records")
    hdr = ["idx", "camp", "cont", "reg", "type", "party", "lvl",
           "file_id", "name_id"]
    if args.names:
        hdr.append("name")
    print("   " + "  ".join(h.rjust(8) for h in hdr))
    shown = 0
    for i, r in enumerate(rows):
        if not any(v for k, v in r.items() if k not in ("name", "name_kind")):
            continue
        cells = [i, r["campaign"], r["continent"], r["region"], r["type"],
                 f"{r['min_party']}-{r['max_party']}",
                 f"{r['min_level']}-{r['max_level']}",
                 f"0x{r['file_id']:x}", r["name_id"]]
        line = "   " + "  ".join(str(v).rjust(8) for v in cells)
        if args.names:
            line += "  " + repr(r.get("name"))
        print(line)
        shown += 1
        if shown >= args.rows:
            break

    if args.out:
        payload = {"exe": args.exe, "base_va": base_va, "records": n,
                   "corroborated_by_code": bool(agreed), "rows": rows}
        Path(args.out).write_text(json.dumps(payload, indent=1), "utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
