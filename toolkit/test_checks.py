"""Proves `toolkit/checks.py` can go red, by breaking each of its rules on purpose.

This is the check on the checker. Every other test in the toolkit now routes its
verdict through `Ledger.verdict()`, so if that function cannot fail, nothing below it
can either -- and the failure would look exactly like a green suite.

Note the shape: each case constructs a run that SHOULD be refused and asserts the exit
code is non-zero. The negative cases (a genuinely complete run) are here too, because a
guard that reddens everything is just as useless as one that reddens nothing -- it gets
switched off within the week.

  python toolkit/test_checks.py
"""
import contextlib
import io
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks  # noqa: E402


def run(build):
    """Drive a Ledger through `build`, capturing its output. Returns (code, text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = build()
    return code, buf.getvalue()


def main():
    led = checks.Ledger("checks.py itself", floor=12)

    # --- the rule that would have caught test_codec.py in 2026-08 ---------------
    def empty():
        return checks.Ledger("empty run", floor=1).verdict()
    code, text = run(empty)
    led.ok(code != 0, "a run with zero checks is refused", f"exit={code}")
    led.ok("NO CHECKS RAN" in text,
           "and the banner says so rather than printing a pass")
    led.ok("ALL CHECKS PASSED" not in text,
           "a zero-check run never prints ALL CHECKS PASSED")

    # --- the rule that would have caught test_movement_fidelity.py -------------
    # Two passing checks, a declared skip, and a floor of three: exactly the shape
    # that printed green on 2026-08-06.
    def partial():
        p = checks.Ledger("partial run", floor=3)
        p.ok(True, "median drift under limit")
        p.ok(True, "accept rate over floor")
        p.skip("run speed", "only 0 straight-run samples; need 10")
        return p.verdict()
    code, text = run(partial)
    led.ok(code != 0,
           "a run that passes every check it ran but misses its floor is refused",
           f"exit={code}")
    led.ok("FLOOR" in text.upper(),
           "and the banner names the shortfall, not just 'failed'")

    # --- skips are never silent -------------------------------------------------
    def skipped():
        p = checks.Ledger("skip visibility", floor=1)
        p.ok(True, "the one mandatory check")
        p.skip("optional section", "fixture absent")
        return p.verdict()
    code, text = run(skipped)
    led.ok(code == 0,
           "a complete run with a declared skip still passes", f"exit={code}")
    led.ok("not measured this run" in text,
           "but the skip is printed in the verdict, not swallowed")

    # --- a real failure is still a failure --------------------------------------
    def failing():
        p = checks.Ledger("failing run", floor=1)
        p.ok(False, "a check that is false")
        return p.verdict()
    code, _ = run(failing)
    led.ok(code != 0, "a failed check is refused", f"exit={code}")

    # --- and the guard does not redden a healthy run -----------------------------
    def healthy():
        p = checks.Ledger("healthy run", floor=2)
        p.ok(True, "one")
        p.ok(True, "two")
        return p.verdict()
    code, text = run(healthy)
    led.ok(code == 0 and "ALL CHECKS PASSED" in text,
           "a run that meets its floor with no failures passes", f"exit={code}")

    # A floor below 1 is a programming error, not a policy choice.
    try:
        checks.Ledger("bad", floor=0)
        raised = False
    except ValueError:
        raised = True
    led.ok(raised, "a floor of 0 is rejected at construction")

    # --- and the suite list is the suite ----------------------------------------
    # CLAUDE.md's pre-flight list IS the definition of "run the tests". A test in
    # the tree but not on the list is one nobody runs: test_pathmap.py,
    # test_skillcast.py and test_textrec.py were each off it for days while
    # passing, which is the same failure as a green vacuous test one level up.
    # Enforced here rather than asserted in prose, per the house rule that a law
    # in a docstring is a wish.
    tree, named = suite_on_disk(), suite_in_claude_md()
    missing = sorted(tree - named)
    phantom = sorted(named - tree)
    led.ok(not missing, "every test in the tree is named in CLAUDE.md",
           f"unlisted: {', '.join(missing)}" if missing else f"{len(tree)} tests")
    led.ok(not phantom, "every test CLAUDE.md names still exists",
           f"missing from tree: {', '.join(phantom)}" if phantom else "")

    return led.verdict()


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def suite_on_disk():
    """Every test_*.py under toolkit/, as repo-relative posix paths."""
    root = repo_root()
    out = set()
    for base, dirs, files in os.walk(os.path.join(root, "toolkit")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                rel = os.path.relpath(os.path.join(base, f), root)
                out.add(rel.replace(os.sep, "/"))
    return out


def suite_in_claude_md():
    """Every toolkit test path CLAUDE.md names, from its pre-flight section."""
    path = os.path.join(repo_root(), "CLAUDE.md")
    with open(path, encoding="utf-8") as fh:
        return set(re.findall(r"toolkit/[\w/]*test_\w+\.py", fh.read()))


if __name__ == "__main__":
    sys.exit(main())
