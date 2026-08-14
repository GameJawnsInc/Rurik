#!/usr/bin/env python3
r"""Name the archive's 349 map rows, by matching footprints to terrain dims.

    python toolkit/clientscan/maprows.py                  # the mapping
    python toolkit/clientscan/maprows.py --check          # the join's own controls
    python toolkit/clientscan/maprows.py --out vault/maprows.json

Python 3 standard library only. Read-only on the client and the archive.

WHY THIS EXISTS. `studies/mapdata/FORMAT.md` could enumerate all 349 map files
and name 249 of them only by borrowing an unlicensed upstream table; a hundred
were named by nobody. `studies/areatable/FINDINGS.md` then solved map id -> name
for all 888 rows out of the client, and stopped dead at the join, because
`s_missionClientData`'s file id is a loading-screen texture. Both documents
concluded the map file id "is not in the client's static data".

THAT CONCLUSION IS CORRECT AND IT IS NOW PROVEN RATHER THAN ASSUMED -- twice,
by methods that share nothing (studies/maprows/FINDINGS.md §2). What neither
document noticed is that the join does not need a file id at all.

THE JOIN. `s_missionClientData` carries, at +0x48 and +0x58, the map's
FOOTPRINT on its continent: four dwords, a rect in TERRAIN CELLS. The map file
carries its own rect in world units in chunk 0x2000000C. The cell pitch is
96.0 -- the same constant `terrain.py` and `stripbuild.py` already measured from
the other side -- and

    footprint_width  == (rect.x1 - rect.x0) / 96
    footprint_height == (rect.y1 - rect.y0) / 96

holds for **319 of 319** footprints in the image. The offset between the two is
the map's continent placement and differs per map, so only the SIZE is shared;
that is the whole join and also its whole limit.

WHY THAT IS A MEASUREMENT AND NOT A COINCIDENCE. The controls are in `--check`
and they are the reason this file is worth running: shifting every footprint by
ONE cell in x drops the match from 319/319 to **0/319**, and sizes drawn at
random from the observed ranges score **~41%**. A relation that survives the
first and beats the second is not a fit.

WHAT IT CANNOT DO, stated here because the output would otherwise imply
otherwise. Size is a two-number key and the archive has no continent field, so
maps sharing a size cannot be told apart: 110 footprints have the dims 512x512,
which 60 map rows also have. This tool therefore reports, per row, the SET of
names its size admits, and marks a row `exact` only when its dims are unique in
the archive. Everything else is a candidate list and is labelled as one. A row
with several names is also a real outcome and not always ambiguity -- ArenaNet's
own wire puts three named zones (Ascalon City, Lakeside County, Ashford Abbey)
in the one file 0x1B97D, OBSERVED in 9 of 9 live connections.

PROVENANCE. The names are ArenaNet's authored text and never enter the repo:
resolved at run time out of the owner's own archive, exactly as `areatable.py`
and `mapbuild.py` do. `--out` writes to a path you give; send it to `vault/`.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import random
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "mapdata"))

import areatable                                              # noqa: E402
import pinned                                                 # noqa: E402
import textrec                                                # noqa: E402
import vaultpath                                              # noqa: E402
from archive import Archive, ffna_chunks, DEFAULT_DAT         # noqa: E402
from gwpe import PE                                           # noqa: E402
import mapbuild                                               # noqa: E402

RECORD_SIZE = areatable.RECORD_SIZE          # 124
MAP_FLAGS = 259                              # stream 1, entry flags 3
MAP_PARAMS_CHUNK = 0x2000000C

# The two footprint rects, (x0, y0, x1, y1) in terrain cells, equal on 716 of
# the 888 rows. UNNAMED in every upstream mirror -- these offsets are ours.
#
# WHICH ONE THE CLIENT PREFERS IS NO LONGER OPEN, and this comment said it was
# for as long as it stood. SETTLED 2026-08-14 on build 38797 (studies/minimap
# rung S2; studies/maprows/FINDINGS.md section 9 item 4): `MissionCliGetMap()`
# (0x0084D9B0, reading missionContext+0x238) picks, and the branch is
# `test eax,eax; jne` -- 0 takes +0x48, non-zero takes +0x58. The enum is
# ArenaNet's own and is TWO-VALUED, so the branch is a real choice and not a
# collapse: MISSION_MAP_OUTPOST == 0 (`QuestLog:261 MISSION_MAP_OUTPOST ==
# MissionCliGetMap()`, compiled `call 0x0084D9B0; test eax,eax; je` at
# 0x0057BEBA -- the assert is SKIPPED when the answer is zero),
# MISSION_MAP_GAME == 1 (`MsCliApi:251`, `cmp [esi+0x238],1` @ 0x0084D9EC),
# MISSION_MAPS == 2 (`MsCliMan:486`, `cmp [edi+0x238],2` @ 0x0085204B). So
# +0x48 is the rect the client crops the continent atlas with while this area
# is an OUTPOST instance and +0x58 the one it uses while it is a GAME
# (explorable/mission) instance. -- OBSERVED.
#
# SIX readers apply it and no seventh is visible to three sweeps that share no
# premise -- int3-block co-occurrence with the 106 `call 0x005A8580` sites, a
# shape sweep for a contiguous four-dword rect at both offsets on one base
# register, and a forward sweep from all 171 `MissionCliGetMap()` sites. They
# are CompassMap.cpp 0x008C2160 (a helper) and 0x008C2761 (an inline re-fetch
# of the ORIGIN only), the compass block at 0x008C3141, ChCliApi.cpp
# 0x00811C64 (the fog mark, which then `shr`s by 5 into the block grid), and
# GmMapHelpers.cpp 0x0054E6A0 and 0x0054E830. GmMapView.cpp reads NEITHER
# offset. What makes that countable rather than hopeful: the table base
# 0x0096DE38 occurs EXACTLY ONCE in the image, at 0x005A85A8 inside the
# accessor, so every row pointer in the client comes from there; and
# s_missionClientData is .rdata, so any site that WRITES [base+0x48] is
# provably not an area row. Blind to indirect calls and to a row pointer
# cached across functions.
#
# BOTH RECTS ARE STILL KEPT -- now for a measured reason instead of for want
# of one. The two GmMapHelpers readers FALL BACK to the other rect when the
# preferred one is all zeros (0x0054E876..0x0054E894 and its mirror at
# 0x0054E8A4), and the population is why that matters: of the 172 rows where
# the two differ, 136 have +0x48 all-zero, 16 have +0x58 all-zero, and only
# 20 carry two different NON-ZERO rects. 152 of the 172 are one ABSENT rect,
# not two rival ones, so dropping either side would lose a real footprint on
# 152 rows. `read_footprints` already skips an all-zero rect, which is the
# same rule arrived at from the other end. (The compass has NO fallback; it
# bails on a degenerate rect at 0x008C274F instead.)
FOOTPRINT_A = (0x48, 0x4C, 0x50, 0x54)   # MISSION_MAP_OUTPOST == 0
FOOTPRINT_B = (0x58, 0x5C, 0x60, 0x64)   # MISSION_MAP_GAME    == 1

# MEASURED elsewhere in this repo and re-derived here rather than trusted:
# `terrain.py` gets rect/dims == 96.0 exactly and nothing else, and
# `stripbuild.py` derives its rect as `dims * 96.0`. `--check` re-runs that.
CELL_PITCH = 96.0

# Bumped BY HAND, and only for what has no value to fold into the stamp: the
# shape of the cached dict, the integrality rule in `map_dims`, or a change in
# `mapbuild.decode_map_parameters`. Everything that IS a value -- the pitch, the
# row filter, the chunk id -- goes into the stamp directly instead, because a
# constant somebody has to remember to bump is a constant somebody forgets to
# bump, and that is exactly the defect `_stamp` records below.
CACHE_FORMAT = 1


def i32(blob: bytes, off: int) -> int:
    return struct.unpack_from("<i", blob, off)[0]


def locate_table(pe: PE):
    """(base_va, base_off, corroborated) for `s_missionClientData`.

    Never a hardcoded address: `areatable.py`'s two locators are used and must
    agree, exactly as they do there. The client's own accessor at 0x005A8580
    asserts `index < arrsize(s_missionClientData)` against `cmp esi, 0x378` and
    indexes with `imul eax, esi, 0x7c`, which is where 888 and 124 come from --
    but that address is build-specific and this is not.
    """
    hits = areatable.locate_structural(pe)
    if not hits:
        raise LookupError(
            "no 124-byte-stride record table found in .rdata. The layout or "
            "the stride is wrong; do not fall back to a hardcoded address.")
    hits.sort(key=lambda h: -h["named"])
    code = areatable.locate_from_code(pe)
    agreed = sorted({h["va"] for h in hits} & set(code))
    va = agreed[0] if agreed else hits[0]["va"]
    return va, pe.rva_to_off(va - pe.image_base), bool(agreed)


def read_footprints(pe: PE, base_off: int, count: int):
    """[{id, continent, name_id, rects:[(x0,y0,x1,y1), ...]}] for every row."""
    out = []
    for i in range(count):
        rec = base_off + i * RECORD_SIZE
        rects = []
        for group in (FOOTPRINT_A, FOOTPRINT_B):
            r = tuple(i32(pe.data, rec + d) for d in group)
            if any(r) and r not in rects:
                rects.append(r)
        out.append({
            "id": i,
            "continent": i32(pe.data, rec + areatable.OFF_CONTINENT),
            "region": i32(pe.data, rec + areatable.OFF_REGION),
            "type": i32(pe.data, rec + areatable.OFF_TYPE),
            "name_id": i32(pe.data, rec + areatable.OFF_NAME_ID),
            "rects": rects,
        })
    return out


def _stamp(dat: str) -> dict:
    """The cache's validity key: the archive, AND the parameters used to read it.

    THIS SHIPPED WITHOUT THE SECOND HALF, AND IT SILENTLY DISARMED A DOCUMENTED
    CONTROL FOR AS LONG AS IT DID. Until 2026-08-13 the stamp was
    `{dat, size, mtime}` -- the archive alone -- while `CELL_PITCH` is consumed at
    the `/ CELL_PITCH` in `map_dims` **before** the cache is written. So a dims
    table computed under one pitch was served under another, and
    `test_maprows.py`'s own docstring recorded a control that no longer fired:
    "CELL_PITCH was set to 64.0 ... 6 checks go red" is true on a COLD cache and
    false on a warm one, which is the way anyone actually runs it (9.2 s against
    ~9 minutes). MEASURED the day this was fixed: warm, with the pitch set to any
    of 64.0, 48.0, 100.0, 112.0, 97.0, 96.5, 96.1, 96.01, 96.001 or 96.0000001,
    the file printed ALL CHECKS PASSED (23 checks) and exited 0. Only `--all`,
    which deletes the cache file outright, could see any of it. A cache is not
    supposed to be able to change a measurement's answer, and this one could.

    WHY THE PARAMETERS ARE FOLDED IN RATHER THAN LEFT TO `CACHE_FORMAT`.
    `mapchunks.archive_stamp`, the model for this function, carries a hand-bumped
    `format` integer and nothing else -- and that is the right answer THERE,
    because what its cache stores is chunk offsets: a shape, with no coding
    parameter to fold. Here there are three, and a hand-bumped integer would have
    to be remembered by whoever next edits `CELL_PITCH`. The whole defect above is
    somebody not remembering something, so a version number that has to be
    remembered is the same bet a second time. A FOLDED parameter cannot go stale,
    because the value that produced the cache and the value being asked about are
    the same expression. `CACHE_FORMAT` is therefore kept for exactly what cannot
    be folded -- the stored dict's shape, the integrality rule,
    `mapbuild.decode_map_parameters` -- and the three constants the cached numbers
    are arithmetic in go in by value.

    The comparison is plain dict equality over JSON round-tripped values, which is
    exact for these: Python's encoder reprs a float round-trip-exactly, so
    96.0000001 stays distinguishable from 96.0 rather than collapsing onto it. A
    NaN pitch would never compare equal to itself and would drop the cache on
    every run -- slow, but in the safe direction, which is the direction a stamp
    should fail in.
    """
    st = os.stat(dat)
    return {"format": CACHE_FORMAT,
            "dat": os.path.abspath(dat), "size": st.st_size,
            "mtime": int(st.st_mtime),
            # The coding parameters the cached dims are arithmetic in. Move any
            # one of these and the stored numbers are answers to a different
            # question, so they must key the cache the same way the archive does.
            "cell_pitch": float(CELL_PITCH),
            "map_flags": MAP_FLAGS,
            "params_chunk": MAP_PARAMS_CHUNK}


def map_dims(dat=DEFAULT_DAT, cache=None, verbose=True):
    """{mft_row: (w_cells, h_cells)} for every map-flagged row.

    Decompressing 349 maps costs minutes, so the result is cached -- and the
    cache is DROPPED rather than trusted when its stamp disagrees, the way
    `mapchunks.py`'s chunk index is. A cache keyed to a different archive would
    silently answer about a different set of maps.

    Note the ORDER, because it is what made the stamp's missing half invisible:
    `CELL_PITCH` is consumed below, at the division, and the cache is written
    after that. The stored numbers are therefore already pitch-dependent, and
    `_stamp` -- read it -- now says so.
    """
    want = _stamp(dat)
    if cache and os.path.isfile(cache):
        try:
            blob = json.loads(Path(cache).read_text("utf-8"))
            if blob.get("stamp") == want:
                return {int(k): tuple(v) for k, v in blob["dims"].items()}
            if verbose:
                print(f"  cache {cache} is for another archive -- ignoring it")
        except (ValueError, KeyError):
            if verbose:
                print(f"  cache {cache} is unreadable -- ignoring it")

    dims, bad = {}, []
    with Archive(dat) as ar:
        rows = [e for e in ar.entries if e.flags == MAP_FLAGS]
        if verbose:
            print(f"  {len(rows)} map-flagged rows; decompressing "
                  f"(minutes, then cached)")
        for n, e in enumerate(rows):
            try:
                data = ar.read(e)
                rect = None
                for cid, poff, size in ffna_chunks(data):
                    if cid == MAP_PARAMS_CHUNK:
                        rect = mapbuild.decode_map_parameters(
                            data[poff:poff + size])[0]
                        break
            except Exception as exc:                          # noqa: BLE001
                bad.append((e.index, str(exc)))
                continue
            if rect is None:
                bad.append((e.index, f"no 0x{MAP_PARAMS_CHUNK:08X} chunk"))
                continue
            w, h = (rect[2] - rect[0]) / CELL_PITCH, (rect[3] - rect[1]) / CELL_PITCH
            if abs(w - round(w)) > 1e-9 or abs(h - round(h)) > 1e-9:
                # The whole reading rests on the extent being a whole number of
                # cells. One that is not would mean the pitch is wrong, and
                # rounding it away would hide that.
                bad.append((e.index, f"extent {w}x{h} is not integral in cells"))
                continue
            dims[e.index] = (round(w), round(h))
            if verbose and (n + 1) % 50 == 0:
                print(f"    {n + 1}/{len(rows)}")
    if bad and verbose:
        print(f"  {len(bad)} row(s) yielded no usable rect:")
        for row, why in bad[:10]:
            print(f"    row {row}: {why}")
    if cache:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(json.dumps(
            {"stamp": want, "dims": {str(k): list(v) for k, v in dims.items()}}),
            "utf-8")
        if verbose:
            print(f"  cached to {cache}")
    return dims


def footprint_sizes(rows):
    """{(w, h): {map ids carrying a footprint of that size}}."""
    out = collections.defaultdict(set)
    for r in rows:
        for x0, y0, x1, y1 in r["rects"]:
            out[(x1 - x0, y1 - y0)].add(r["id"])
    return out


def distinct_footprints(rows):
    """{(continent, rect)} -- one per map file, on the reading in the docstring."""
    return {(r["continent"], rect) for r in rows for rect in r["rects"]}


def check(rows, dims, trials=200, seed=20260813):
    """The join's own controls. Returns a dict; `--check` prints it.

    Three questions, each of which the artifact could answer against us:
    does every footprint size exist in the archive; does the match survive a
    one-cell shift (it must not); and how does it compare to random sizes.
    """
    dimset = collections.Counter(dims.values())
    foot = distinct_footprints(rows)
    sizes = collections.Counter((r[2] - r[0], r[3] - r[1]) for _c, r in foot)
    total = sum(sizes.values())
    hit = sum(n for s, n in sizes.items() if s in dimset)
    shift_x = sum(n for s, n in sizes.items() if (s[0] + 1, s[1]) in dimset)
    shift_xy = sum(n for s, n in sizes.items()
                   if (s[0] + 1, s[1] + 1) in dimset)
    rng = random.Random(seed)
    xs, ys = [s[0] for s in sizes], [s[1] for s in sizes]
    rates = []
    for _ in range(trials):
        fake = [(rng.choice(xs), rng.choice(ys)) for _ in range(len(sizes))]
        rates.append(sum(1 for s in fake if s in dimset) / len(fake))
    rates.sort()
    return {
        "footprints": total, "distinct_sizes": len(sizes),
        "map_rows": len(dims), "distinct_dims": len(dimset),
        "matched": hit, "shift_x": shift_x, "shift_xy": shift_xy,
        "random_mean": sum(rates) / len(rates),
        "random_p95": rates[int(0.95 * len(rates))],
        "missing": {f"{s[0]}x{s[1]}": n for s, n in sizes.items()
                    if s not in dimset},
    }


def solve(rows, dims):
    """{mft_row: {"dims", "map_ids", "exact"}}.

    A row is `exact` when its dims are unique among all map rows: then every
    footprint of that size can only be describing this file. Otherwise the map
    ids are candidates, and the count of rival rows is reported so a reader can
    see how far from an answer it is.
    """
    by_dims = collections.defaultdict(list)
    for row, d in dims.items():
        by_dims[d].append(row)
    sizes = footprint_sizes(rows)
    out = {}
    for row, d in dims.items():
        rivals = len(by_dims[d])
        out[row] = {"dims": d, "rival_rows": rivals,
                    "map_ids": sorted(sizes.get(d, ())), "exact": rivals == 1}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine build")
    ap.add_argument("--dat", default=DEFAULT_DAT, help="the archive")
    ap.add_argument("--cache", default=None,
                    help="terrain-dims cache (default: vault/areatable/)")
    ap.add_argument("--check", action="store_true",
                    help="the join's controls, and nothing else")
    ap.add_argument("--out", help="write the mapping as JSON (use vault/)")
    ap.add_argument("--rows", type=int, default=30, help="rows to print")
    a = ap.parse_args()

    exe, why = ((a.exe, "given on the command line") if a.exe
                else pinned.find())
    print(f"client: {exe}\n        ({why})")
    print(f"archive: {a.dat}")
    pe = PE(exe)
    va, off, corroborated = locate_table(pe)
    n = areatable.extent(pe.data, off)
    print(f"s_missionClientData at VA 0x{va:08X}: {n} records of "
          f"{RECORD_SIZE} B, "
          f"{'corroborated by code' if corroborated else 'STRUCTURAL ONLY'}")

    rows = read_footprints(pe, off, n)
    foot = distinct_footprints(rows)
    print(f"  {sum(1 for r in rows if r['rects'])} of {n} rows carry a "
          f"footprint; {len(foot)} distinct (continent, rect)")

    cache = a.cache or str(Path(vaultpath.vault_root()) / "areatable"
                           / "maprows-dims.json")
    print("terrain dims:")
    dims = map_dims(a.dat, cache)
    print(f"  {len(dims)} map rows with a rect, "
          f"{len(set(dims.values()))} distinct dims")

    c = check(rows, dims)
    print(f"\nTHE JOIN, and its controls")
    print(f"  footprint size found in the archive : "
          f"{c['matched']} of {c['footprints']}")
    print(f"  CONTROL, every footprint +1 cell x  : "
          f"{c['shift_x']} of {c['footprints']}  (must be ~0)")
    print(f"  CONTROL, +1 cell in x and y         : "
          f"{c['shift_xy']} of {c['footprints']}  (must be ~0)")
    print(f"  CONTROL, random sizes in range      : "
          f"{100 * c['random_mean']:.1f}% mean, "
          f"{100 * c['random_p95']:.1f}% at p95")
    if c["missing"]:
        print(f"  sizes with NO map of those dims: {c['missing']}")
    if c["matched"] != c["footprints"]:
        print("  NOT 100%. The relation does not hold on this build/archive; "
              "report that rather than using the mapping below.")
    if a.check:
        return 0 if c["matched"] == c["footprints"] else 2

    sol = solve(rows, dims)
    ix = textrec.TextIndex(exe=exe, dat=a.dat)
    try:
        name = {r["id"]: ix.get(r["name_id"]) for r in rows}
        exact = [r for r in sol.values() if r["exact"]]
        named = [r for r in sol.values() if r["map_ids"]]
        print(f"\n{len(exact)} of {len(sol)} rows have dims unique in the "
              f"archive, so their names are forced")
        print(f"{len(named)} of {len(sol)} rows have at least one candidate; "
              f"{len(sol) - len(named)} have none (no footprint of their size)")

        print(f"\nrows whose name is FORCED (first {a.rows}):")
        shown = 0
        for row in sorted(sol, key=lambda r: -len(sol[r]["map_ids"])):
            e = sol[row]
            if not e["exact"] or not e["map_ids"]:
                continue
            names = sorted({name[i] for i in e["map_ids"] if name[i]})
            print(f"  row {row:>6}  {e['dims'][0]:>4}x{e['dims'][1]:<4} "
                  f"{len(e['map_ids']):>2} map id(s)  {names}")
            shown += 1
            if shown >= a.rows:
                break

        if a.out:
            payload = {
                "client": exe, "archive": os.path.abspath(a.dat),
                "table_va": va, "records": n, "controls": c,
                "rows": {str(k): {**v, "names": sorted(
                    {name[i] for i in v["map_ids"] if name[i]})}
                    for k, v in sol.items()},
            }
            Path(a.out).write_text(json.dumps(payload, indent=1), "utf-8")
            print(f"\nwrote {a.out}")
    finally:
        ix.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
