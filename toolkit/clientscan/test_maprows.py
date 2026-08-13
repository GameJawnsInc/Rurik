#!/usr/bin/env python3
"""Check the footprint join that names archive map rows.

    python toolkit/clientscan/test_maprows.py
    python toolkit/clientscan/test_maprows.py --all      # every map row, ~9 min

WHAT EARNS THIS FILE, because the headline number is the weak half. "319 of 319
footprints have a size the archive carries" is a claim about a two-number key
over an 84-value alphabet, and a two-number key matches a lot by accident: sizes
drawn at RANDOM from the observed ranges already score ~41%. So the round number
proves much less than it looks like, and three controls carry the file instead:

  * Section 4 shifts every footprint by ONE CELL and requires the match to
    COLLAPSE. 319/319 -> 0/319 is what says the relation is the arithmetic and
    not the alphabet. A version of this test without it would pass against a
    join that had the pitch wrong by a factor it happened to absorb.
  * Section 5 requires the random-size null to stay far below the real rate.
    It is the number that makes "100%" mean something, and it is asserted
    rather than printed, because a control nobody compares against is a comment.
  * Section 7 is the ANCHOR: two rows whose identity was established WITHOUT
    this join -- row 7982 from ArenaNet's own wire (three named zones, 9 of 9
    live connections) and row 22371 from `archive.py`'s own measured note. The
    join must admit both. It never saw either.

WHICH OF THOSE IS LOAD-BEARING WAS MEASURED, not assumed. `CELL_PITCH` was set
to 64.0 and the file re-run: **6 checks go red, and section 5 is not one of
them.** The random null falls with the real rate (3.9% against 9.1%), so it
still "passes" -- it is a ratio, and a wrong pitch moves both terms. What
catches the sabotage is section 4's one-cell control and, decisively, the
anchors: both go to **0 candidates**. A version of this test built only out of
corpus statistics would have called a wrong pitch green.

AND THAT PARAGRAPH WAS TRUE ONLY ON A COLD CACHE, WHICH IS WHY SECTION 2 EXISTS.
`maprows.map_dims` caches 349 decompressions, and its stamp named the archive and
nothing else while `CELL_PITCH` was consumed BEFORE the cache was written -- so a
dims table computed at 96.0 was served back under any other pitch. MEASURED
2026-08-13, warm: 64.0, 48.0, 100.0, 112.0, 97.0, 96.5, 96.1, 96.01, 96.001 and
96.0000001 each printed ALL CHECKS PASSED (23 checks) and exited 0 in 9.2 s. Only
`--all`, which deletes the cache file, ever saw the six. The paragraph above is a
claim about the six checks; section 2 is the claim that they get the chance to
run, and it asserts the drop directly rather than trusting the stamp's field list.
It needs no archive and no vault, so it is also one of the few things this file
can still measure on a machine without one.

Section 6 is the negative result that the arc turned on, and it is asserted so
it can go red if a future build changes: NO dword column of the 888-record table
resolves to a map-flagged row, in either the raw or the packed reading. If that
ever fails, the client gained a map-id -> file-id table and
`studies/maprows/FINDINGS.md` §2 needs rewriting.

Section 3 pins the pitch as a DERIVATION rather than a constant: every map's
terrain extent must be a whole number of 96-unit cells, which the archive could
refuse and which is what makes `/96` legitimate.

Sections 0-2 need no archive and no vault; sections 3-7 all rest on `map_dims`,
which reads every map's Map Parameters chunk and is cached in the vault after
the first run (~9 min cold, ~9 s warm).

Four real place names appear below as the anchor oracle, the same way
`test_areatable.py` carries a few: without a concrete expected string an anchor
cannot tell a correct join from a convincing one. These are names the game shows
on screen and they are the EVIDENCE for a claim, not an extracted table -- the
349-row mapping itself is written to `vault/`, never here.
"""

import argparse
import collections
import json
import os
import random
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))

import areatable                                              # noqa: E402
import checks                                                 # noqa: E402
import maprows                                                # noqa: E402
import pinned                                                 # noqa: E402
import vaultpath                                              # noqa: E402
from archive import Archive, file_id_table, DEFAULT_DAT       # noqa: E402
from gwpe import PE                                           # noqa: E402

# MEASURED on build 38797 + dat_study, 2026-08-13: a healthy run executes 29 --
# the 23 this file ran before section 2 existed, plus that section's 6.
# Set from a real green run and not from a guess -- the first value here was 24,
# picked by counting `check(` calls in the source, and a vault-backed run went
# red naming the shortfall. Which is the guard working, and is why it is 29.
FLOOR = 29

# The two anchors. Neither was derived from the join under test.
#   7982  -- GAME_SMSG 0x0195 carried file 0x1B97D in 9 of 9 live connections
#            and 0x0199 named maps 146/148/164 in them.
#   22371 -- archive.py's docstring: file id 0x345CC resolves here, map-flagged.
ANCHORS = {
    7982: ("Ascalon City", "Lakeside County", "Ashford Abbey"),
    22371: ("Kamadan, Jewel of Istan",),
}

LEDGER = checks.Ledger("maprows footprint join", floor=FLOOR)
check = checks.adopt(LEDGER)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=None)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--all", action="store_true",
                    help="ignore the cache and re-read every map")
    a = ap.parse_args()
    t0 = time.perf_counter()

    exe, why = ((a.exe, "given on the command line") if a.exe
                else pinned.find())
    print(f"client: {exe}\n        ({why})")
    kind, detail = pinned.identify(exe)
    print(f"        {kind}: {detail}\n")

    # -- 0. the table, located by two methods that share nothing -------------
    print("0. s_missionClientData, located structurally and from code")
    pe = PE(exe)
    va, off, corroborated = maprows.locate_table(pe)
    check(corroborated,
          "the structural scan and the imul-0x7C scan name the same address",
          f"VA 0x{va:08X}")
    n = areatable.extent(pe.data, off)
    check(n == 888, "888 records", str(n))
    # The client's own accessor asserts `index < arrsize(s_missionClientData)`
    # against `cmp esi, 0x378`. Reading 0x378 back out of the image is what
    # makes 888 ArenaNet's number rather than our structural inference.
    sig = bytes([0x81, 0xFE, 0x78, 0x03, 0x00, 0x00])   # cmp esi, 0x378
    check(pe.data.find(sig) != -1,
          "the client's own bound `cmp esi, 0x378` is in the image",
          "888, from ArenaNet rather than from our walk")

    # -- 1. the footprints ---------------------------------------------------
    print("\n1. the footprint rects")
    rows = maprows.read_footprints(pe, off, n)
    withfoot = [r for r in rows if r["rects"]]
    check(len(withfoot) > 400,
          "several hundred rows carry a footprint",
          f"{len(withfoot)} of {n}")
    foot = maprows.distinct_footprints(rows)
    check(len(foot) > 250, "distinct (continent, rect) footprints",
          str(len(foot)))
    # Every rect must be well formed -- x0 < x1 and y0 < y1. A decoder reading
    # the wrong four dwords produces inverted spans in bulk.
    bad = [(r["id"], rect) for r in rows for rect in r["rects"]
           if not (rect[0] < rect[2] and rect[1] < rect[3])]
    check(not bad, "every footprint has a positive span in x and y",
          f"{len(bad)} malformed" if bad else "")

    # -- 2. the dims cache cannot outlive the parameters that produced it ----
    # THE CHECK THAT WOULD HAVE CAUGHT IT. Everything from section 3 on reads
    # `map_dims`, which caches 349 decompressions; its stamp used to name the
    # archive alone, so a wrong `CELL_PITCH` was absorbed by the cache and the
    # docstring's six red checks became 23 green ones. The assertion is
    # deliberately BEHAVIOURAL rather than a look at the stamp's field names: a
    # test that read `"cell_pitch" in maprows._stamp(...)` would pass against a
    # stamp that carried the key and compared it loosely, and against a
    # `map_dims` that built the stamp and then ignored it. So each parameter is
    # actually moved and `map_dims` is actually asked.
    #
    # The fixture is a few bytes in a temp directory, because the stamp only
    # STATS its archive -- and a cache MISS then falls through to opening those
    # bytes as an archive, which raises `not a GW archive`. That raise is the
    # observable: "the cache did not answer". No vault, no client, no 4.2 GB.
    #
    # FOUR SABOTAGES WERE BUILT AND RUN against this section, 2026-08-13, and
    # each reddens a DIFFERENT set, which is what says the six checks are six
    # checks and not one repeated:
    #   * `_stamp` restored to `{dat, size, mtime}` -- the real defect -- 5 red.
    #   * `_stamp` rounding the pitch to 3 decimals: 1 red, and it is the
    #     96.0000001 row alone. That is what pays for having a second pitch.
    #   * `_stamp` carrying every field while `map_dims` compares only the old
    #     three: 5 red. A test asserting the stamp's field NAMES would have
    #     called this fixed, which is why nothing here looks at the field names.
    #   * `map_dims` never loading the cache at all: the five refusals all go
    #     vacuously GREEN and only the positive control reddens. That is the
    #     one measuring whether this section can fail for the wrong reason.
    print("\n2. the dims cache moves when a coding parameter moves")
    tmp = tempfile.mkdtemp(prefix="rurik-maprows-")
    try:
        fakedat = os.path.join(tmp, "NotReallyAnArchive.dat")
        with open(fakedat, "wb") as fh:
            fh.write(b"not an archive")
        cachefile = os.path.join(tmp, "dims.json")
        planted = {"7982": [128, 128]}

        def replant():
            """Write a cache that is valid for the CURRENT parameter values."""
            with open(cachefile, "w", encoding="utf-8") as fh:
                json.dump({"stamp": maprows._stamp(fakedat), "dims": planted}, fh)

        def cache_answered():
            """True only if map_dims served the planted table without reading."""
            try:
                got = maprows.map_dims(fakedat, cachefile, verbose=False)
            except Exception:                                  # noqa: BLE001
                return False        # fell through to the archive -- dropped
            return got == {7982: (128, 128)}

        # THE POSITIVE CONTROL COMES FIRST, and it is not decoration. Every
        # check under it asserts that the cache did NOT answer, and all of them
        # would pass vacuously against a cache that can never answer at all --
        # a mistyped path, a stamp that never matches itself. This is the one
        # check here that requires the cache to work.
        replant()
        check(cache_answered(),
              "CONTROL: an untouched stamp does serve the planted cache",
              "so the refusals below are refusals and not vacuum")

        # EVERY WRONG VALUE IS DERIVED FROM THE LIVE ONE, and that is not
        # fastidiousness -- it is what the control run taught. The first version
        # wrote the literal `64.0`, which is the pitch `test_maprows`'s docstring
        # sabotages with; running the fix's own control arm, i.e. this file
        # against `CELL_PITCH = 64.0`, turned that row into `64.0 -> 64.0`, a
        # mutation that mutates nothing, and it went red for a reason that had
        # nothing to do with the cache. A parameter check whose "wrong" value can
        # coincide with the right one is a check that reddens on a legitimate
        # edit, so `x * 2/3` lands on the documented 64.0 from 96.0 and can never
        # land on the value it started from. `+ 1e-7` is the small end of the
        # same idea: it reproduces 96.0000001, the smallest wrong pitch the old
        # stamp was measured to swallow, and a stamp storing the pitch any
        # lossier than a round-trip float lets exactly that one back through.
        for param, mutate in (("CELL_PITCH", lambda v: v * 2 / 3),
                              ("CELL_PITCH", lambda v: v + 1e-7),
                              ("MAP_FLAGS", lambda v: v + 1),
                              ("MAP_PARAMS_CHUNK", lambda v: v + 1),
                              ("CACHE_FORMAT", lambda v: v + 1)):
            was = getattr(maprows, param)
            wrong = mutate(was)
            if wrong == was:
                raise RuntimeError(
                    f"{param}: the mutation is a no-op ({was!r}), so this row "
                    "would assert that an UNCHANGED parameter drops the cache. "
                    "Fix the expression rather than the expectation.")
            replant()                       # valid for `was`, asked under `wrong`
            setattr(maprows, param, wrong)
            try:
                served = cache_answered()
            finally:
                setattr(maprows, param, was)
            check(not served,
                  f"a cache written under a different {param} is DROPPED",
                  f"{was!r} -> {wrong!r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # -- 3. the pitch, derived rather than assumed ---------------------------
    print("\n3. the cell pitch is a derivation the archive could refuse")
    cache = str(vaultpath.vault_path("areatable", "maprows-dims.json"))
    if a.all and os.path.isfile(cache):
        os.remove(cache)
    try:
        dims = maprows.map_dims(a.dat, cache, verbose=False)
    except OSError as exc:
        LEDGER.skip("everything from section 3 on",
                    f"cannot read the archive: {exc}")
        return LEDGER.verdict()
    check(len(dims) == 349, "349 map rows yield a terrain rect", str(len(dims)))
    # map_dims REFUSES a non-integral extent rather than rounding, so a full
    # 349 is itself the assertion that every map is a whole number of cells.
    check(all(w > 0 and h > 0 for w, h in dims.values()),
          "every map's extent is positive in both axes")
    ndims = len(set(dims.values()))
    check(ndims < len(dims),
          "map dims are NOT unique per map -- the join's central limitation",
          f"{ndims} distinct dims over {len(dims)} rows")

    # -- 4. the join, and the one-cell control -------------------------------
    print("\n4. the join, and the control that makes it a measurement")
    c = maprows.check(rows, dims)
    check(c["matched"] == c["footprints"],
          "every footprint's size exists in the archive",
          f"{c['matched']} of {c['footprints']}")
    check(c["shift_x"] == 0,
          "CONTROL: shifting every footprint +1 cell in x matches NOTHING",
          f"{c['shift_x']} of {c['footprints']}")
    check(c["shift_xy"] == 0,
          "CONTROL: shifting +1 cell in x and y matches NOTHING",
          f"{c['shift_xy']} of {c['footprints']}")
    check(not c["missing"], "no footprint size is absent from the archive",
          str(c["missing"]) if c["missing"] else "")

    # -- 5. the random null --------------------------------------------------
    print("\n5. the null: how well do random sizes do?")
    real = c["matched"] / c["footprints"]
    check(c["random_mean"] < 0.75 * real,
          "random sizes score far below the real rate",
          f"{100*c['random_mean']:.1f}% mean vs {100*real:.1f}%")
    check(c["random_p95"] < real,
          "even the 95th percentile of the null is under the real rate",
          f"{100*c['random_p95']:.1f}%")

    # -- 6. the negative result the arc turned on ----------------------------
    print("\n6. no column of the table resolves to a map row")
    with Archive(a.dat) as ar:
        maprowset = {e.index for e in ar.entries if e.flags == maprows.MAP_FLAGS}
        fid = file_id_table(ar)
    mapids = {f for f, r in fid.items() if r in maprowset}
    check(len(mapids) > 690, "file ids naming a map row", str(len(mapids)))
    import struct

    def combine(p):
        return ((p >> 16) - 0x100) * 0xFF00 + ((p & 0xFFFF) - 0x100) + 1

    worst_raw = worst_packed = 0
    for d in range(0, maprows.RECORD_SIZE, 4):
        vals = [struct.unpack_from("<I", pe.data,
                                   off + i * maprows.RECORD_SIZE + d)[0]
                for i in range(n)]
        nz = [v for v in vals if v]
        worst_raw = max(worst_raw, sum(1 for v in nz if v in mapids))
        worst_packed = max(worst_packed, sum(
            1 for v in nz
            if (v & 0xFFFF) >= 0x100 and (v >> 16) >= 0x100
            and combine(v) in mapids))
    # A stray hit is a small integer colliding with a low file id; a COLUMN of
    # them would be the table this arc refuted. The bound is what matters.
    check(worst_raw <= 5,
          "no dword column is a raw map-file-id column",
          f"best column scores {worst_raw} of {n}")
    check(worst_packed <= 5,
          "no dword column is a PACKED map-file-id column",
          f"best column scores {worst_packed} of {n}")

    # -- 7. the anchors ------------------------------------------------------
    print("\n7. anchors established without this join")
    sol = maprows.solve(rows, dims)
    import textrec
    with textrec.TextIndex(exe=exe, dat=a.dat) as ix:
        name = {r["id"]: ix.get(r["name_id"]) for r in rows}
        for row, want in ANCHORS.items():
            e = sol.get(row)
            if e is None:
                LEDGER.skip(f"anchor row {row}", "not a map row in this archive")
                continue
            got = {name[i] for i in e["map_ids"] if name[i]}
            check(set(want) <= got,
                  f"row {row} admits its independently-known name(s)",
                  f"{len(got)} candidate(s)")
        # Row 7982's three names are one FILE with three zones -- the wire
        # measured that, and it is why the tool reports a set per row rather
        # than a name. Asserting it keeps a future "one name per row"
        # simplification from silently dropping two of them.
        e = sol.get(7982)
        if e:
            got = {name[i] for i in e["map_ids"] if name[i]}
            check(len({"Ascalon City", "Lakeside County",
                       "Ashford Abbey"} & got) == 3,
                  "one row legitimately carries several names",
                  "OBSERVED on ArenaNet's wire, 9 of 9 connections")

        # And the resolving power, asserted so it cannot quietly degrade.
        exact = [v for v in sol.values() if v["exact"]]
        single = [v for v in exact
                  if len({name[i] for i in v["map_ids"] if name[i]}) == 1]
        check(len(exact) >= 50, "rows whose dims are unique in the archive",
              str(len(exact)))
        check(len(single) >= 18, "rows resolving to exactly one name",
              str(len(single)))

    print(f"\nread the exe and the archive in {time.perf_counter() - t0:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
