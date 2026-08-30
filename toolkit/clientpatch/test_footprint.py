#!/usr/bin/env python3
r"""Check the footprint patcher: does it write the right bytes, and ONLY those?

    python toolkit/clientpatch/test_footprint.py

WHAT EARNS THIS FILE. `footprint.py` writes into `s_missionClientData`, a
`.rdata` table 888 rows long that every other tool in this repo only READS. A
wrong base offset there does not raise -- it returns four plausible-looking
int32 from the wrong place and patches them. That is not hypothetical: the
first version of `locate()` treated `Table.base` as a VA and ran it through
`rva_to_off`, landing 0x400B90 bytes short, and printed four numbers for map
143 that looked like data. Nothing in the containment check could catch it,
because containment only asks whether the bytes that moved were inside the
range it was TOLD to write.

So the sections here are the two directions that matter:

  * Section 1 pins the read against an INDEPENDENT reader -- `Table.record`,
    which is what `maprows.py` and the whole minimap arc used for 319 rows.
    Agreement between two readers that reach the bytes differently is the check;
    `footprint.read_rect` computes an offset, `Table.record` slices a record.
  * Section 3 is the sabotage set. Each one breaks a single guard on purpose and
    requires the tool to refuse, because a guard nobody has watched fail is a
    wish -- `test_datcrc.py` and `test_worldmap.py` both earned that rule.

Section 4 asserts the output guard on the SYNTAX TREE as well as by calling it,
because "it refuses to write into the repo" is a claim about a code path that a
passing call does not prove is still wired up.

Read-only on the client. Writes nothing outside a temp directory.
"""

import ast
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))

import checks                                                  # noqa: E402
import footprint                                               # noqa: E402
import consttable                                              # noqa: E402
import maprows                                                 # noqa: E402
import pinned                                                  # noqa: E402

# MEASURED from the green run of 2026-08-15. Every check here is unconditional
# once a client is present; the client-less path declares a skip and goes red,
# which is deliberate -- the whole file is about bytes in a real image.
#
# AND THE BARE-MACHINE PATH IS NOW MEASURED, 2026-08-30, rather than assumed:
# `RURIK_VAULT` pointed at an empty directory gives **0 checks, 1 declared skip
# ("everything"), rc=1**, and the reason printed is `checks.py`'s zero-checks
# rule -- NOT the floor. So 21 is not a claim about a mandatory core: this file
# HAS no client-free core -- not because it has no client-free CHECKS (§4 is
# pure AST work and §3's four `sane_rect` calls touch nothing), but because
# both sit after `main()`'s early return. And no floor could make the bare run
# green anyway; `Ledger` refuses a floor below 1 for exactly this reason.
# Before that day the same run gave rc=1 and NO verdict at all: `pinned.find()`
# raises `SystemExit`, which the `except Exception` in `main()` did not catch,
# so the skip this comment describes was unreachable and had never been walked.
FLOOR = 21
LEDGER = checks.Ledger("footprint patcher (PLAN A2)", floor=FLOOR)
check = checks.adopt(LEDGER)

# Stated as literals so the test carries its own expectation instead of asking
# the module under test. Map 143's two rects are EQUAL, which is also what makes
# it rung C3's negative control.
MAP = 143
WANT = (960, 448, 1280, 992)


def main():
    try:
        exe = pinned.find()[0]
    except (Exception, SystemExit) as e:                        # noqa: BLE001
        # SystemExit, and it has to be named: `pinned.find()` RAISES one when
        # the build is not in the vault, and `Exception` does not catch it --
        # so on a machine without the vault this file died here with rc=1 and
        # NO verdict at all, instead of declaring the skip below and letting
        # the floor rule name the shortfall.
        LEDGER.skip("everything", f"no pinned client to read: {e}")
        return LEDGER.verdict()
    pe = maprows.PE(exe)

    # -- 1. the read, against an independent reader --------------------------
    print("1. the read agrees with the reader every other tool uses")
    base, stride, count = footprint.locate(pe)
    check(count == 888, "888 area rows", str(count))
    check(stride == 124, "stride 124", str(stride))
    t = consttable.table_for(pe, footprint.SYMBOL)
    rec = t.record(pe, MAP)
    for which, off in (("A", footprint.OFF_A), ("B", footprint.OFF_B)):
        mine, _o = footprint.read_rect(pe.data, base, stride, MAP, which)
        theirs = struct.unpack_from("<4i", rec, off)
        check(mine == theirs == WANT,
              f"map {MAP} rect {which} == {WANT} by BOTH readers",
              f"footprint.read_rect={mine} Table.record={theirs}")

    # -- 2. the write is exactly 16 bytes per rect ---------------------------
    print("\n2. the patch moves exactly the bytes it names")
    new, log = footprint.patch(pe.data, base, stride, MAP, (960, 448, 1024, 512),
                               ["A"])
    changed = [i for i in range(len(new)) if new[i] != pe.data[i]]
    check(len(new) == len(pe.data), "same length as the input", str(len(new)))
    check(len(changed) <= 16, "at most 16 bytes changed for one rect",
          f"{len(changed)}")
    a_off = base + MAP * stride + footprint.OFF_A
    check(all(a_off <= i < a_off + 16 for i in changed),
          "and every one of them is inside rect A",
          f"{[hex(i) for i in changed[:4]]}")
    back = struct.unpack_from("<4i", new, a_off)
    check(back == (960, 448, 1024, 512), "the new rect reads back", str(back))
    # B must be untouched when only A is named -- the two sit 16 bytes apart and
    # a stride slip would take both.
    b_off = base + MAP * stride + footprint.OFF_B
    check(struct.unpack_from("<4i", new, b_off) == WANT,
          "rect B is untouched when only A is written",
          "they are adjacent; a slip would take both")

    # -- 3. sabotages: each guard must FIRE ----------------------------------
    print("\n3. every guard, broken on purpose")
    check(not footprint.sane_rect((138644224, 1962948739, -1171494383, 9721912)),
          "sane_rect REFUSES the garbage a wrong base produced",
          "this exact tuple is what the double-converted offset returned")
    check(not footprint.sane_rect((100, 100, 100, 200)), "and refuses a zero width")
    check(not footprint.sane_rect((100, 100, 90, 200)), "and refuses an inverted x")
    check(footprint.sane_rect(WANT), "but ACCEPTS the real rect -- not a "
          "predicate that refuses everything")

    tmp = tempfile.mkdtemp(prefix="fp_")
    for label, dest in (("the input itself", exe),
                        ("the owner's install", r"C:\gw\Gw.exe"),
                        ("a checkout of this repo",
                         os.path.join(os.path.dirname(HERE), "Gw.exe"))):
        try:
            footprint.refuse_bad_output(exe, dest)
            fired = False
        except SystemExit:
            fired = True
        check(fired, f"refuse_bad_output REFUSES {label}")
    # ...and PERMITS the vault, or the tool could not do its job at all.
    try:
        import vaultpath
        footprint.refuse_bad_output(
            exe, os.path.join(vaultpath.vault_root(), "client-tier3", "Gw.exe"))
        permitted = True
    except SystemExit:
        permitted = False
    check(permitted, "but PERMITS the vault -- the intended destination",
          "a guard that refuses its own purpose is how the first reskin "
          "version shipped")

    # -- 4. the output guard is CALLED, not merely present -------------------
    print("\n4. the guard is wired into main(), on the syntax tree")
    src = open(os.path.join(HERE, "footprint.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    check(fn is not None, "footprint.main exists")
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name)
             and n.func.id == "refuse_bad_output"]
    check(len(calls) == 1, "main() calls refuse_bad_output exactly once",
          f"{len(calls)} -- a guard that exists and is never called is the "
          f"failure test_atex.py 3 names")
    opens = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "open"]
    check(len(opens) == 1, "and writes through exactly one open()",
          f"{len(opens)}")
    # The locate() docstring must keep naming the VA bug, because the next
    # reader's instinct is to 'fix' base into a VA again.
    check("rva_to_off" in footprint.locate.__doc__,
          "locate() still records why Table.base is NOT a VA",
          "the comment IS the guard against re-introducing it")

    print(f"\nread {os.path.basename(exe)}")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
