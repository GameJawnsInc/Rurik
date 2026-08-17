"""Prove the unbound-name checker catches the bug it was written for, and stays quiet.

`srclint.py` exists because on 2026-08-10 `session.py` read a name in `run_client()`
that was only ever bound in `main()`. `ast.parse` accepted it, `py_compile` accepted it,
and all 32 tests passed. It surfaced as a NameError thirty seconds into a live session,
tore the stack down, and took the capture with it.

TWO THINGS ARE TESTED HERE AND THE SECOND IS THE REAL ONE.

  1. It catches the bug. Section 2 reconstructs the exact shape.
  2. IT IS NOT VACUOUS. The first version of `_bound_at_module` used a full-subtree
     walk, so every local in every function counted as a module-scope binding -- which
     is precisely the binding the bug hides behind. Run against the source that had
     actually crashed minutes earlier, it reported ZERO. Section 4 pins that specific
     failure so it cannot come back, and section 5 runs the real toolkit, because a
     checker nobody can leave switched on is a checker that is off.

A false positive is worse than a miss here: a linter people learn to ignore is a linter
that is off. Section 3 is therefore the long one -- every ordinary Python binding form
that must NOT be reported.

standard library only.

    python toolkit/test_srclint.py
"""
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import srclint  # noqa: E402

# 11, from a real green run. Section 3 is deliberately ONE check over 18 cases rather
# than 18 checks: the failure that matters is "any ordinary binding form is flagged",
# and the message names which. Guessed at 17 first; the floor guard rejected the run.
#
# 11 -> 13 on 2026-08-12 with section 7, which checks CLAUDE.md's suite list against
# the tree in both directions. That rule had been written down since the list existed
# and enforced by nothing; it names three tests that went unrun for days, and on the
# day section 7 was written a runner reported "51 of 51 green" over 52 test files.
#
# 13 -> 15 the same day with section 5b, which extends the corpus to `tools/`. That
# directory holds the two halves of the Blender pipeline, which import `bpy` and so
# cannot be run outside Blender at all -- exactly the place an unbound name hides
# longest -- and nothing had ever linted it.
#
# 15 -> 20 on 2026-08-16 with section 8, `conditional_globals`. Section 2 is blind
# by design to a `global X` that is assigned only inside a CLI block: name
# resolution is satisfied, runtime ordering is not. Three such names shipped and
# every DEFAULT launch died with NameError inside the instance load. Set from a
# real green run, not a guess -- the first write of section 8 asserted `== []`
# where the honest assertion was narrower, and the floor guard would have taken
# the wrong number.
LEDGER = checks.Ledger("srclint", floor=20)


def names(src):
    return [n for _line, n in srclint.check_source(textwrap.dedent(src))]


def main():
    # ---- 1. it runs at all -----------------------------------------------------
    print("1. the checker parses and reports")
    LEDGER.ok(names("def f():\n    return 1\n") == [],
              "a trivial clean function reports nothing")

    # ---- 2. THE BUG ------------------------------------------------------------
    print("\n2. the 2026-08-10 defect, reconstructed")
    sibling = """
        def main():
            labelling = True
            return run_client(labelling)

        def run_client(a):
            return hold_open(quiet=labelling)

        def hold_open(quiet=False):
            return quiet
        """
    LEDGER.ok(names(sibling) == ["labelling"],
              "a name bound in one function and read in its SIBLING is caught",
              "this is session.py:594 exactly -- computed in main(), read in "
              "run_client()")
    line = srclint.check_source(textwrap.dedent(sibling))[0][0]
    LEDGER.ok(line == 7, "and it is reported at the line that reads it", f"line {line}")

    # ---- 3. and it stays quiet on every ordinary binding form -------------------
    print("\n3. legitimate Python is not flagged")
    cases = {
        "module global": "X = 1\ndef f():\n    return X\n",
        "import": "import os\ndef f():\n    return os.sep\n",
        "from-import as": "from os import sep as S\ndef f():\n    return S\n",
        "builtin": "def f():\n    return len([])\n",
        "parameter": "def f(a, *b, c=1, **d):\n    return a, b, c, d\n",
        "closure over enclosing": "def f():\n    x = 1\n    def g():\n        return x\n    return g\n",
        "comprehension var": "def f(xs):\n    return [y for y in xs if y]\n",
        "walrus": "def f(xs):\n    if (n := len(xs)):\n        return n\n",
        "for target": "def f(xs):\n    for i in xs:\n        return i\n",
        "with as": "def f(p):\n    with open(p) as fh:\n        return fh.read()\n",
        "except as": "def f():\n    try:\n        pass\n    except OSError as ex:\n        return ex\n",
        "global decl": "def s():\n    global G\n    G = 1\ndef f():\n    return G\n",
        "nested def name": "def f():\n    def g():\n        return 1\n    return g()\n",
        "class method self": "class C:\n    def m(self):\n        return self\n",
        "recursion": "def f(n):\n    return f(n - 1) if n else 0\n",
        "decorator": "import functools\n@functools.cache\ndef f():\n    return 1\n",
        "lambda arg": "def f():\n    return (lambda q: q)(1)\n",
        "type annotation": "def f(a: int) -> int:\n    return a\n",
    }
    noisy = {label: got for label, src in cases.items() if (got := names(src))}
    LEDGER.ok(not noisy,
              f"none of {len(cases)} ordinary binding forms is reported",
              "a linter with false positives is a linter that gets switched off"
              + (f" -- FLAGGED: {noisy}" if noisy else ""))

    # ---- 4. THE VACUITY GUARD --------------------------------------------------
    print("\n4. the checker cannot be quietly disarmed")
    # If _bound_at_module descends into function bodies, `helper`'s local `tmp`
    # becomes a module-scope binding and `user`'s read of it looks fine. That is the
    # bug this checker shipped with, and it made it report zero on the real defect.
    leak = """
        def helper():
            tmp = 1
            return tmp

        def user():
            return tmp
        """
    LEDGER.ok(names(leak) == ["tmp"],
              "a local in one function does NOT bind that name for another",
              "the first _bound_at_module walked the whole tree and made every "
              "local module-scope; it then reported 0 on the source that had "
              "crashed minutes earlier")
    mod_bound = srclint._bound_at_module(__import__("ast").parse(textwrap.dedent(leak)))
    LEDGER.ok("tmp" not in mod_bound and "helper" in mod_bound and "user" in mod_bound,
              "module scope holds the def NAMES and not their locals",
              f"{sorted(mod_bound)}")

    # ---- 5. the real corpus, which is the point --------------------------------
    print("\n5. the toolkit itself")
    root = HERE
    bad, skipped, n = {}, [], 0
    for path in srclint.python_files(root):
        n += 1
        try:
            hits = srclint.check_file(path)
        except srclint.StarImport:
            skipped.append(os.path.relpath(path, root))
            continue
        except SyntaxError as ex:
            bad[os.path.relpath(path, root)] = [(ex.lineno, f"SyntaxError: {ex.msg}")]
            continue
        if hits:
            bad[os.path.relpath(path, root)] = hits
    LEDGER.ok(n >= 90, f"the whole toolkit is checked, not a sample", f"{n} files")
    LEDGER.ok(not bad, "and no file reads a name nothing could have bound",
              "; ".join(f"{p}:{h[0][0]} {h[0][1]}" for p, h in sorted(bad.items()))
              or "clean")
    if skipped:
        LEDGER.skip("star-import files", f"cannot judge: {', '.join(skipped)}")
    else:
        LEDGER.ok(True, "and no file was skipped for a star-import",
                  "a skipped file is unjudged, so it is named rather than counted "
                  "as clean")

    # ---- 5b. tools/, which nothing was checking --------------------------------
    # `tools/blender/` holds the two halves of the Blender pipeline. They import
    # `bpy` and therefore CANNOT be run outside Blender, so an unbound name in
    # one of them survives every ordinary smoke test and surfaces as a traceback
    # inside a headless render -- which is worse than the session.py NameError
    # this checker exists for, not better. Added 2026-08-12 with
    # `export_gwmap.py`; until then the directory was linted by nobody.
    tools = os.path.join(os.path.dirname(HERE), "tools")
    if not os.path.isdir(tools):
        LEDGER.skip("5b. tools/", f"no tools directory at {tools}")
    else:
        tbad, tn = {}, 0
        for path in srclint.python_files(tools):
            tn += 1
            try:
                hits = srclint.check_file(path)
            except srclint.StarImport:
                tbad[os.path.relpath(path, tools)] = [(0, "star-import")]
                continue
            except SyntaxError as ex:
                tbad[os.path.relpath(path, tools)] = [(ex.lineno, f"SyntaxError: {ex.msg}")]
                continue
            if hits:
                tbad[os.path.relpath(path, tools)] = hits
        LEDGER.ok(tn >= 2, "tools/ is checked too, not just toolkit/",
                  f"{tn} files")
        LEDGER.ok(not tbad, "and no file under tools/ reads a name nothing "
                            "could have bound",
                  "; ".join(f"{p}:{h[0][0]} {h[0][1]}"
                            for p, h in sorted(tbad.items())) or "clean")

    # ---- 6. failure modes are loud ---------------------------------------------
    print("\n6. what it refuses to judge, it names")
    try:
        names("from os import *\ndef f():\n    return sep\n")
        raised = False
    except srclint.StarImport:
        raised = True
    LEDGER.ok(raised,
              "a star-import raises rather than guessing",
              "the wildcard could bind anything; reporting `sep` as undefined would "
              "be a false positive and reporting nothing would be a silent pass")
    try:
        srclint.check_source("def f(:\n")
        syntax_raised = False
    except SyntaxError:
        syntax_raised = True
    LEDGER.ok(syntax_raised, "and a file that does not parse raises SyntaxError")

    # ---- 7. CLAUDE.md's suite list IS the suite --------------------------------
    print("\n7. every test in the tree is named in CLAUDE.md's suite list")
    # THE RULE EXISTED AND NOTHING CHECKED IT. CLAUDE.md: "This list is the
    # suite. A test in the tree but not named here is a test nobody runs" --
    # and it names three that were missing for days. On 2026-08-12 a runner
    # reported "51 of 51 green" over a tree holding 52 test files, which is the
    # same defect from the other side and is worse, because the count was
    # self-consistent. A rule nothing checks is a wish.
    #
    # Both directions, and the second is not decoration: an entry naming a test
    # that no longer exists makes the list look complete while covering less
    # than it claims, and a checker that only walked the tree would call that
    # healthy.
    #
    # The list MOVED to TESTS.md on 2026-08-14 -- it had reached 2,458 of
    # CLAUDE.md's 2,725 lines (90%) and buried the house rules. The two
    # directions now read DIFFERENT files on purpose:
    #
    #   forward (every test on disk is named) -> TESTS.md ONLY. Reading both
    #   would let a test be mentioned in CLAUDE.md's prose and absent from the
    #   catalog while this check stayed green, which is precisely the "list is
    #   the suite" rule being subverted.
    #
    #   reverse (every name cited still exists) -> BOTH, because a stale
    #   `test_foo.py` citation in CLAUDE.md's rules is the same defect as one
    #   in the catalog: it reads as coverage that is not there.
    root = os.path.dirname(HERE)
    claude = os.path.join(root, "CLAUDE.md")
    tests_md = os.path.join(root, "TESTS.md")
    if not os.path.isfile(tests_md):
        LEDGER.skip("7. the suite list", f"no TESTS.md at {tests_md}")
    else:
        text = open(tests_md, encoding="utf-8").read()
        both = text + (open(claude, encoding="utf-8").read()
                       if os.path.isfile(claude) else "")
        on_disk = set()
        for dirpath, _dirs, files in os.walk(HERE):
            if "__pycache__" in dirpath:
                continue
            for f in files:
                if f.startswith("test_") and f.endswith(".py"):
                    on_disk.add(f)
        # `test_` files this list deliberately does not carry: none today. If one
        # is ever added, name it HERE with the reason rather than loosening the
        # walk, so the exemption is visible.
        EXEMPT = set()
        unnamed = sorted(f for f in on_disk - EXEMPT if f not in text)
        LEDGER.ok(not unnamed,
                  f"all {len(on_disk)} test files in toolkit/ are named in TESTS.md",
                  f"UNNAMED: {unnamed} -- add the entry in the same commit as the "
                  f"test, or the suite silently stops covering it")
        # The reverse. Only names that look like our test files, so ordinary
        # prose mentioning a module cannot trip it.
        cited = set(re.findall(r"\btest_[a-z0-9_]+\.py\b", both))
        missing = sorted(cited - on_disk)
        LEDGER.ok(not missing,
                  f"and all {len(cited)} tests named in TESTS.md or CLAUDE.md exist",
                  f"STALE: {missing} -- the list reads as complete while "
                  f"covering less than it claims")

    # ---- 8. globals bound only on a conditional path ---------------------------
    print("\n8. a `global X` with no module-level default")
    # THE 2026-08-16 DEFECT, RECONSTRUCTED. Section 2's checker reports ZERO on
    # this shape and is RIGHT to: `global X` really does bind X at module scope
    # for NAME RESOLUTION. What it cannot see is RUNTIME ORDERING -- the
    # assignment happens only if the CLI block runs, so every other path reads a
    # name that does not exist yet. Three names shipped this way and every
    # DEFAULT launch died with NameError inside the instance load, showing the
    # client Code=007 -- indistinguishable from a bad map row, which is what
    # made it expensive for the two sessions that hit it.
    defect = """
        HERO_BODY = False

        def handle():
            for x in (hero_slots() if HERO_ATTRIBS else ()):
                pass

        def main(a):
            global HERO_ATTRIBS
            HERO_ATTRIBS = not a.no_hero_attribs
        """
    hits = srclint.conditional_globals(textwrap.dedent(defect))
    LEDGER.ok([n for _l, n in hits] == ["HERO_ATTRIBS"],
              "the real defect is caught",
              f"{hits}")
    # Section 2 DOES flag `hero_slots` here (it is undefined in this snippet),
    # so the honest assertion is the narrow one: it never names HERO_ATTRIBS,
    # which is the name that actually raised NameError in production. Asserting
    # `== []` passed nothing and failed for the wrong reason on first write.
    seen2 = [n for _l, n in srclint.check_source(textwrap.dedent(defect))]
    LEDGER.ok("HERO_ATTRIBS" not in seen2,
              "and section 2's checker is CONFIRMED blind to THAT name",
              f"section 2 reports {seen2}; if HERO_ATTRIBS ever appears there, "
              f"section 8 is redundant and should go")
    fixed = textwrap.dedent(defect).replace(
        "HERO_BODY = False", "HERO_BODY = False\nHERO_ATTRIBS = True")
    LEDGER.ok(srclint.conditional_globals(fixed) == [],
              "a module-level default clears it")
    imported = """
        import os

        def main():
            global os
            os = None
        """
    LEDGER.ok(srclint.conditional_globals(textwrap.dedent(imported)) == [],
              "an import counts as a module-level binding",
              "otherwise every `global` on an imported name is a false positive")
    live = []
    for d in (HERE, os.path.join(os.path.dirname(HERE), "tools")):
        if not os.path.isdir(d):
            continue
        for p in srclint.python_files(d):
            try:
                live += [(os.path.basename(p), n)
                         for _l, n in srclint.conditional_globals_file(p)]
            except SyntaxError:
                pass
    LEDGER.ok(not live,
              "and the whole tree is clean of it",
              f"CONDITIONAL GLOBALS: {live} -- these raise NameError on any path "
              f"that does not run the block assigning them")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
