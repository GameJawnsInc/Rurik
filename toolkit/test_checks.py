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
    led = checks.Ledger("checks.py itself", floor=14)

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
    # TESTS.md IS the definition of "run the tests" (it was CLAUDE.md's pre-flight
    # list until 2026-08-14, when the catalog was split out). A test in
    # the tree but not on the list is one nobody runs: test_pathmap.py,
    # test_skillcast.py and test_textrec.py were each off it for days while
    # passing, which is the same failure as a green vacuous test one level up.
    # Enforced here rather than asserted in prose, per the house rule that a law
    # in a docstring is a wish.
    tree, named = suite_on_disk(), suite_in_docs()
    missing = sorted(tree - named)
    phantom = sorted(named - tree)
    led.ok(not missing, "every test in the tree is named in TESTS.md",
           f"unlisted: {', '.join(missing)}" if missing else f"{len(tree)} tests")
    led.ok(not phantom, "every test the docs name still exists",
           f"missing from tree: {', '.join(phantom)}" if phantom else "")

    # --- the top-level documents point at things that exist ---------------------
    # PLAN.md §3 is now the single status authority and stamps each landed rung with
    # a commit hash, and §3.2 grades R4b/R4c against a manifest. Both are claims that
    # rot silently: a hash typo or a renamed study leaves a document confidently
    # citing nothing. The rule is only worth writing down if something checks it.
    dangling = broken_doc_links()
    led.ok(not dangling, "every repo-relative link in the top-level docs resolves",
           "; ".join(f"{d}: {t}" for d, t in dangling[:4]) if dangling else "")

    bad_hashes = unresolvable_hashes()
    if bad_hashes is None:
        led.skip("commit stamps", "git not available to resolve them")
    else:
        led.ok(not bad_hashes,
               "every commit hash PLAN.md §3 stamps a rung with resolves",
               ", ".join(bad_hashes) if bad_hashes else "")

    return led.verdict()


TOP_DOCS = ("CLAUDE.md", "PLAN.md", "RUNBOOK.md", "HANDOFF.md", "TESTS.md")


def broken_doc_links():
    """(doc, target) for every markdown link to a repo path that does not exist."""
    root = repo_root()
    out = []
    for doc in TOP_DOCS:
        path = os.path.join(root, doc)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for target in re.findall(r"\]\(([^)#\s]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not os.path.exists(os.path.join(root, target.split("#")[0])):
                out.append((doc, target))
    return out


def unresolvable_hashes():
    """Short hashes PLAN.md §3 cites that git cannot resolve. None if no git."""
    import subprocess
    root = repo_root()
    path = os.path.join(root, "PLAN.md")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    section = text[text.find("## 3. The revised ladder"):text.find("## 4.")]
    # Backticked 7-to-10 hex words. Long enough not to catch `0x1B97D` or a year.
    candidates = set(re.findall(r"`([0-9a-f]{7,10})`", section))
    if not candidates:
        return []
    bad = []
    for h in sorted(candidates):
        try:
            r = subprocess.run(["git", "-C", root, "cat-file", "-t", h],
                               capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode != 0 or r.stdout.strip() != "commit":
            bad.append(h)
    return bad


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


def suite_in_docs():
    """Every toolkit test path the house documents name.

    BOTH files since 2026-08-14, when the catalog moved to TESTS.md (it had
    reached 90% of CLAUDE.md). Not TESTS.md alone: `test_handshake.py` is named
    only inside CLAUDE.md's code fence, so a scan of the catalog by itself is
    short by exactly that one.
    """
    out = set()
    for name in ("TESTS.md", "CLAUDE.md"):
        path = os.path.join(repo_root(), name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                out |= set(re.findall(r"toolkit/[\w/]*test_\w+\.py", fh.read()))
    return out


if __name__ == "__main__":
    sys.exit(main())
