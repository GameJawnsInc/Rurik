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
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import srclint  # noqa: E402

# 11, from a real green run. Section 3 is deliberately ONE check over 18 cases rather
# than 18 checks: the failure that matters is "any ordinary binding form is flagged",
# and the message names which. Guessed at 17 first; the floor guard rejected the run.
LEDGER = checks.Ledger("srclint", floor=11)


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

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
