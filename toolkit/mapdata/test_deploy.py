r"""Check rung G's one command: `deploy.py`, the whole ladder from `content/`.

WHAT THIS FILE IS FOR. `deploy.py` is an ORCHESTRATOR -- almost every line it
runs belongs to a module that has its own test. So this does not re-check the
terrain codec or the archive writer; it checks the things that are only true of
the composition, and those are exactly the things the first three runs of the
command got wrong:

  * **The two kinds of borrowing are different.** Structural constants (Header,
    Zones) must come from a map SHAPED LIKE OURS; the biome (textures, sun, env,
    sound) comes from wherever you like. The first run took both from
    Pre-Searing, whose Zones chunk is 7,208 bytes against the 32x32 reference
    map's 34, and built an 11,115-byte map for a 4,608-byte reservation. Section
    2 pins the split by building with both and requiring the borrowed census to
    stay small.
  * **The client you launch must own the archive you armed.** Every run
    directory has its own `Gw.dat`. The first run armed the C2 copy and launched
    the DEFAULT client, which read unarmed bytes and compiled nothing -- the
    same defect as FINDINGS 54's, from the other side. Section 3 asserts on the
    SYNTAX TREE that the exe is derived from `--dat`, because "it happens to be
    right today" is not a check.
  * **A generator must produce a field the codec can actually hold.** Section 1
    runs every named generator through the lattice snap and requires the
    terrain round trip to close exactly, which is what catches a shape whose
    heights are off the reachable sublattice.

NO VAULT, NO ARCHIVE, NO CLIENT for sections 0-1 and 3. Section 2 needs the
archive because the borrowed halves are read from it at run time -- that is the
provenance rule, not a convenience -- and the floor turns a vault-less run into
the FAIL it is.

    python toolkit/mapdata/test_deploy.py
"""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
import content as content_mod  # noqa: E402
import deploy  # noqa: E402
import mapfile as mfile  # noqa: E402
import stripbuild as sb  # noqa: E402
import strippedterrain as stx  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# MEASURED 2026-08-13 on the plaza area. The census is the load-bearing number:
# Header 8 + Zones 34 + env 639 + sound 89 = 770, and nothing else.
REFERENCE_ROW = 46196          # the 32x32 map whose Zones is 34 B
BIOME_ROW = 7982               # Pre-Searing
BORROWED_MAX = 900             # generous ceiling; the real figure is 770
PRESEARING_ZONES = 7208        # what the first run wrongly pulled in

# FLOOR: 14, MEASURED from a green run 2026-08-13. Sections 0, 1 and 3 score 10
# and need no vault.
LEDGER = checks.Ledger("test_deploy", floor=14)
check = checks.adopt(LEDGER)


def section0():
    print("\n0. the area row loads, and says what it borrows")
    world = content_mod.load()
    area = world.get("area", "plaza")
    check(int(area["map_id"]) in {int(k) for k in world.rows("map")},
          "the area's map_id names a real maps.toml row", f"{area['map_id']}")
    check(area.provenance["source"] == "invented",
          "an authored area is provenance 'invented' -- ours, chosen rather "
          "than observed", f"{area.provenance['source']}")
    check(int(area["constants_row"]) != int(area["donor_row"]),
          "the structural donor and the biome donor are SEPARATE fields",
          f"constants {area['constants_row']}, biome {area['donor_row']}")
    return area


def section1(area):
    print("\n1. every generator lands on the codec's lattice")
    dim = int(area["dims"])
    for name, gen in sorted(deploy.GENERATORS.items()):
        raw = gen(dim)
        snapped, worst = stx.snap_block(raw)
        trn = stx.StrippedTerrain.build(dim, dim, snapped)
        back = stx.StrippedTerrain.decode(trn.encode())
        same = sum(1 for a, b in zip(back.heights, snapped) if a == b)
        check(same == len(snapped),
              f"generator {name!r} round-trips exactly after the snap",
              f"{same}/{len(snapped)}, worst moved {worst}")


def exe_derived_from_dat(source):
    """True iff main() assigns `exe` from dirname(dat).

    Deliberately narrow, and the narrowness is the whole point. The first
    version of this asked whether main() contained ANY `join(dirname(dat), ...)`
    -- and it does, twice, because the output path defaults that way too. So it
    returned True against a sabotaged source that defaulted the exe, i.e. it was
    a check that could not fail. Section 3 now runs that exact sabotage and
    requires this to answer False.
    """
    fn = next(n for n in ast.walk(ast.parse(source))
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    for node in ast.walk(fn):
        targets = ([t.id for t in node.targets if isinstance(t, ast.Name)]
                   if isinstance(node, ast.Assign) else [])
        if "exe" not in targets:
            continue
        for n in ast.walk(node.value):
            if (isinstance(n, ast.Call)
                    and getattr(n.func, "attr", "") == "dirname"
                    and any(isinstance(x, ast.Name) and x.id == "dat"
                            for x in n.args)):
                return True
    return False


def section3():
    print("\n3. the client is DERIVED from the archive, not defaulted")
    source = open(deploy.__file__, encoding="utf-8").read()
    tree = ast.parse(source)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    src = ast.dump(fn)
    check(exe_derived_from_dat(source),
          "main() assigns the client path from dirname(dat) -- the client that "
          "reads the archive we armed is the only one that can load it")
    # NEGATIVE CONTROL: default the exe and require the check to notice.
    sabotage = source.replace(
        'exe = args.exe or os.path.join(os.path.dirname(dat), "Gw.exe")',
        'exe = args.exe or DEFAULT_EXE')
    check(sabotage != source and not exe_derived_from_dat(sabotage),
          "and an exe that is DEFAULTED instead makes that check go red -- "
          "without this control the check passed on the output path's own "
          "dirname(dat) and could not fail")
    check('"--exe"' in ast.dump(fn) or "'--exe'" in src,
          "and passes --exe to the harness rather than letting it default")
    check("--map" in open(deploy.__file__, encoding="utf-8").read(),
          "and points the harness at the area's own map id -- a harness PASS "
          "means the client reached A map, not ours")
    # the readback must exist and must be called
    called = any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "readback"
                 for n in ast.walk(fn))
    check(called, "main() actually calls readback() -- a documented stage that "
                  "no line runs is a docstring, not a check")


def section2(area):
    print("\n2. the two donors, and the census that separates them")
    try:
        dat = os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    except SystemExit:
        LEDGER.skip("section 2, which needs the archive",
                    "no vault/dat_study/Gw.dat; the borrowed halves are read "
                    "from it at run time, so this run has measured nothing "
                    "about what an area actually borrows")
        return
    dim = int(area["dims"])
    heights, _worst = stx.snap_block(deploy.GENERATORS[area["heights"]](dim))
    with Archive(dat) as ar:
        good = deploy.Donor(ar, BIOME_ROW, REFERENCE_ROW)
        bad = deploy.Donor(ar, BIOME_ROW, BIOME_ROW)
    n_good = sum(len(v) for v in good.constants.values())
    n_bad = sum(len(v) for v in bad.constants.values())
    check(n_good < n_bad,
          "constants from the 32x32 reference are far smaller than from the "
          "biome donor", f"{n_good} B vs {n_bad} B")
    check(n_bad - n_good > PRESEARING_ZONES - 100,
          "and the difference is the biome donor's per-map Zones chunk, which "
          "is what blew the reservation on the first run",
          f"{n_bad - n_good} B")

    rep = deploy.assemble(area, heights, good, dim, verbose=False)
    check(rep.borrowed <= BORROWED_MAX,
          f"an assembled area borrows under {BORROWED_MAX} B",
          f"{rep.borrowed} B borrowed, {rep.generated} B generated")
    ids = [c.chunk_id for c in mfile.MapFile.decode(rep.blob).chunks]
    check(ids == [c for c in sb.ORDER if c in ids] and sb.ENV in ids
          and sb.SOUND in ids and sb.PROPS_DEPS in ids,
          "and carries the full presentation set in ORDER",
          f"{len(ids)} chunks")


def main():
    area = section0()
    section1(area)
    section3()
    section2(area)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
