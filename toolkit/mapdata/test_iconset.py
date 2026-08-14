#!/usr/bin/env python3
"""Check the 132-row icon armer -- the guards and the join, not the pictures.

    python toolkit/mapdata/test_iconset.py

`iconset.py` is an ORCHESTRATOR: `glyphs` draws, `atex` wraps, `datwrite` writes,
`archive` resolves, and each of those has its own test. So this file checks only
what is true of the COMPOSITION, and every section is a way this particular tool
can destroy 4 GB of somebody's archive or quietly arm the wrong rows.

1. THE WRITE GUARDS, each with a POSITIVE CONTROL. A guard that refuses
   everything protects nothing, because the tool then never runs. `C:\\gw` is the
   owner's install and read-only forever; `vault/dat_study` is the reference copy
   every measurement in `studies/` was taken against, and `datwrite` does NOT
   refuse it -- that refusal exists only here.

2. THE ROW INDEXING, on the syntax tree. `file_id_table` returns one-based MFT
   ROW NUMBERS and `Archive.entries` is POSITIONAL, so `entries[row]` reads the
   row BEFORE the one you named. On 2026-08-14 that put two authored icons into
   the wrong archive rows, and nothing caught it -- not a checksum, not the
   client, not a verify. `datwrite` refused a third arm as a relocation and the
   numbers in its refusal did not match the row it named; that is the only reason
   it was found. A grep cannot tell `a.row(r)` from `a.entries[r]` in prose, so
   this asks the AST whether the module contains any Subscript on an `entries`
   attribute at all, with a sabotage that must flip the answer.

3. THE PRE-FLIGHT. A row whose reservation is too small is a relocation, which
   `datwrite` refuses -- on row 87 of 132, after 86 rows are already written. The
   whole plan must therefore be checked before anything is written, and the
   ordering of those two things is a property of `main()`, not of a comment.

No vault is needed for sections 1-3. Section 4 exercises the real join and
declares a skip without an archive.
"""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import vaultpath                                                 # noqa: E402
from mapdata import iconset                                      # noqa: E402

# MEASURED from a green run, 2026-08-14: 16 with no vault, 20 with one.
LEDGER = checks.Ledger("icon armer", floor=16)
check = checks.adopt(LEDGER)

SRC = os.path.join(HERE, "iconset.py")


def guarded(fn):
    try:
        fn()
    except Exception as exc:                                     # noqa: BLE001
        check(False, "section %s completed" % fn.__name__,
              "%s: %s" % (type(exc).__name__, exc))


def refuses(path):
    try:
        iconset.guard(path)
        return False
    except SystemExit:
        return True


# --- 1. write guards, both directions -------------------------------------

def section_guards():
    print("\n== 1. write guards -- with positive controls ==")
    for p in (r"C:\gw\Gw.dat", r"c:\GW\sub\Gw.dat", r"C:\gw"):
        check(refuses(p), "refuses the owner's install: %s" % p)
    for p in (r"C:\gd\Rurik\vault\dat_study\Gw.dat",
              r"C:\gd\Rurik\VAULT\DAT_STUDY\Gw.dat"):
        check(refuses(p), "refuses the reference copy: %s" % p)
    # POSITIVE CONTROLS. Without these the guards could refuse everything and
    # every check above would still pass while the tool was useless.
    for p in (r"C:\gd\Rurik\vault\run\reskin-roster\Gw.dat",
              r"D:\scratch\Gw.dat"):
        check(not refuses(p), "still allows an ordinary run-dir copy: %s" % p)
    # `C:\gwsomething` is not inside `C:\gw`; a prefix test without a separator
    # would refuse it.
    check(not refuses(r"C:\gwtest\Gw.dat"),
          "and does not refuse a path that merely starts with the same letters")


# --- 2. the row indexing, on the syntax tree ------------------------------

def entries_subscripts(src):
    """Count `<anything>.entries[...]` -- the shape that reads the wrong row."""
    n = 0
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Subscript):
            v = node.value
            if isinstance(v, ast.Attribute) and v.attr == "entries":
                n += 1
    return n


def section_indexing():
    print("\n== 2. row indexing -- .row(n), never entries[n] ==")
    src = open(SRC, encoding="utf-8").read()
    check(entries_subscripts(src) == 0,
          "iconset.py never subscripts .entries -- a row number is not a "
          "position", entries_subscripts(src))
    check(".row(" in src, "and it does call .row()")

    # SABOTAGE: the detector must flip on the exact defect it is named for.
    bad = src.replace("a.row(row).size", "a.entries[row].size")
    check(bad != src, "the sabotage actually changed the source")
    check(entries_subscripts(bad) == 1,
          "and the AST check catches entries[row] where a grep for 'entries' "
          "would also hit the import and the docstring",
          entries_subscripts(bad))


# --- 3. plan before write, in main() --------------------------------------

def section_ordering():
    print("\n== 3. the whole plan is checked before anything is written ==")
    tree = ast.parse(open(SRC, encoding="utf-8").read())
    main = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    plan_line = writer_line = None
    for node in ast.walk(main):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "plan" and plan_line is None:
            plan_line = node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "Writer":
            writer_line = node.lineno
    check(plan_line is not None and writer_line is not None,
          "main() both plans and opens a Writer", (plan_line, writer_line))
    check(plan_line < writer_line,
          "and it plans BEFORE it opens the writer -- otherwise the refusal "
          "lands on row 87 of 132 with 86 already written",
          (plan_line, writer_line))
    # The refusal must also RETURN rather than warn and carry on.
    src = open(SRC, encoding="utf-8").read()
    i = src.index("REFUSING")
    check("return 2" in src[i:i + 600],
          "a too-small reservation exits non-zero rather than warning")
    check("--arm needs --journal" in src,
          "and an unjournalled 132-row write is refused outright")


# --- 4. the real join ------------------------------------------------------

def section_join():
    print("\n== 4. the real join, against the vault ==")
    try:
        dat = vaultpath.vault_path("run", "reskin-roster", "Gw.dat")
        exe = vaultpath.vault_path("run", "reskin-roster", "Gw.exe")
    except SystemExit:
        LEDGER.skip("section 4: no vault", "the join needs an archive and an exe")
        return
    if not (os.path.exists(dat) and os.path.exists(exe)):
        LEDGER.skip("section 4: no reskin-roster run dir",
                    "the join needs an archive and an exe")
        return
    mine, skills, rows, skipped, toosmall, need = iconset.plan(dat, exe, 8, False)
    check(len(mine) == 132 and skills == 188,
          "profession 8 is 188 skills behind 132 distinct icons",
          (skills, len(mine)))
    check(len(rows) + len(skipped) == len(mine),
          "every icon is either armable or explains itself -- none is dropped",
          (len(rows), len(skipped)))
    check(not toosmall,
          "and every armable row reserves at least the %d B a 64x64 needs" % need,
          toosmall[:3])
    # The shared ones must be HELD BACK by default and released on demand -- a
    # skip list that never shrinks is indistinguishable from a hard-coded one.
    more, _s, rows2, skipped2, _t, _n = iconset.plan(dat, exe, 8, True)
    check(len(rows2) > len(rows) and len(skipped2) < len(skipped),
          "--allow-shared releases the shared icons rather than ignoring the flag",
          (len(rows), len(rows2)))


def main():
    print("=" * 70)
    print("ICON ARMER -- guards and the join, not the pictures")
    print("=" * 70)
    for fn in (section_guards, section_indexing, section_ordering, section_join):
        guarded(fn)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
