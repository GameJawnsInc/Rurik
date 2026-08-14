r"""Run every test under `toolkit/`, one process each, and report a number you can trust.

`CLAUDE.md` calls its suite list "the suite" and says a test in the tree but not on
that list is a test nobody runs. That rule has been enforced from both directions by
`test_srclint.py` since 2026-08-12 -- but until now **nothing actually ran them**. The
2026-08-13 recon census measured it: 66 test files, **0 scripts that run them**
(`studies/recon/FINDINGS.md` gap 12). Every "the suite is green" in this repo's history
was a human pasting paths into a shell, which is precisely how 2026-08-06's report of
"twenty of twenty-three green" happened, with both omitted files red.

WHAT THIS FILE IS REALLY FOR, AND WHY ITS PARSER IS THE INTERESTING PART. Running N
subprocesses is trivial. Reporting honestly about them is not, and an ad-hoc version of
this runner got the count WRONG THREE TIMES IN ONE DAY, each time in the direction that
looks like success:

  1. It harvested the file list out of CLAUDE.md's prose with the regex
     `toolkit/[\w/]+test_\w+\.py`. That cannot match `toolkit/test_checks.py` -- the `+`
     demands at least one character between the slash and `test_` -- so it silently ran
     **63 of 71** files and printed "62 green of 63". A partial run presented as a full
     one, which is the same defect `CLAUDE.md` names from the other side.
  2. Fixed to `(?:[\w/]+/)?`, it found 70 of 71. The missing one was
     `test_handshake.py`, which `CLAUDE.md` names inside a fenced code block rather than
     in backticks -- so the prose is not a parseable index and never was.
  3. Reading the LAST line of a test's stdout for the banner scored
     `test_handshake.py` and `test_webgate.py` at **0 checks** while they exited 0,
     because both print after their banner (a `HANDSHAKE VERIFIED` line, and a request
     log). `0 checks, exit 0` is exactly the silent-vacuity shape `checks.py` exists to
     catch, so the runner was reporting two healthy tests as the worst thing a test can
     be.

The lesson those three share is one sentence: **a runner that miscounts in either
direction turns the suite's verdict into a guess**, and the failure is invisible because
the output still looks like a report. So:

  * The file list comes from **the disk**, never from prose. `test_srclint.py` already
    asserts the disk and `CLAUDE.md` agree in both directions, with a check that can go
    red -- so the disk IS the suite, established by something falsifiable, and this
    runner does not re-derive it from a document that was never an index.
  * The banner is looked for on **every line**, not the last.
  * `rc == 0` with **no banner at all** is reported as `SUSPECT`, never as zero checks
    and never as a pass. A test that exits clean and asserts nothing it can name is the
    thing `checks.py` was written for, and a runner must not launder it into a number.

Both halves are pure functions over strings so `test_run_suite.py` can drive them
without spawning anything.

    python toolkit/run_suite.py                 # everything, one process each
    python toolkit/run_suite.py --only mapdata  # substring filter on the path
    python toolkit/run_suite.py --list          # what would run, and stop

Exit code is 0 only when every file passed AND none was SUSPECT.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PASS = "PASS"
FAIL = "FAIL"
SUSPECT = "SUSPECT"


def find_tests(root=None):
    """Every `test_*.py` under `toolkit/`, from the DISK, sorted, repo-relative.

    Deliberately a walk and not a glob. `toolkit/test_*.py` plus `toolkit/*/test_*.py`
    is the shape somebody reaches for next, and it silently loses any test that lands
    one directory deeper -- the same class as defect (1) in this module's docstring,
    which is the one that cost a full-looking run over 63 of 71 files.
    """
    root = root or ROOT
    out = []
    for where, dirs, files in os.walk(os.path.join(root, "toolkit")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                rel = os.path.relpath(os.path.join(where, f), root)
                out.append(rel.replace(os.sep, "/"))
    return sorted(out)


def parse_result(stdout, returncode):
    """(status, checks, note) for one finished test process.

    `checks` is None when no banner was found -- NOT 0. The difference is the whole
    point: 0 is a measurement ("it ran and asserted nothing"), None is the absence of
    one ("it never said"), and collapsing them is how defect (3) reported two healthy
    files as vacuous. A caller that sums `checks` must skip the Nones rather than
    coerce them, which is why this returns None and not a falsy int.
    """
    lines = [l.strip() for l in (stdout or "").splitlines() if l.strip()]
    checks = None
    for line in lines:
        if line.startswith("ALL CHECKS PASSED"):
            try:
                checks = int(line.split("(")[1].split()[0])
            except (IndexError, ValueError):
                checks = None
            break
    last = lines[-1] if lines else "(no output)"
    if returncode != 0:
        return FAIL, checks, last
    if checks is None:
        # Exit 0 and nothing named. Never call this a pass: `checks.py` exists because
        # `test_codec.py` once printed ALL CHECKS PASSED over a fixture glob matching
        # nothing, and a test that does not even print the banner is further from
        # measured than that was.
        return SUSPECT, None, f"exit 0 but no ALL CHECKS PASSED line -- last: {last}"
    return PASS, checks, ""


def run_one(rel, root=None, python=None):
    root = root or ROOT
    t0 = time.time()
    p = subprocess.run([python or sys.executable, rel], cwd=root,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    status, checks, note = parse_result(p.stdout, p.returncode)
    return status, checks, note, time.time() - t0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=None,
                    help="run only files whose path contains this substring")
    ap.add_argument("--list", action="store_true",
                    help="print what would run and stop")
    a = ap.parse_args()

    tests = find_tests()
    if a.only:
        tests = [t for t in tests if a.only in t]
    if not tests:
        print("no test files matched -- refusing to report a green run over nothing")
        return 2
    if a.list:
        for t in tests:
            print(t)
        print(f"\n{len(tests)} file(s)")
        return 0

    print(f"{len(tests)} test file(s) on disk\n", flush=True)
    tally = {PASS: 0, FAIL: 0, SUSPECT: 0}
    total = 0
    bad = []
    t_all = time.time()
    for rel in tests:
        status, checks, note, dt = run_one(rel)
        tally[status] += 1
        if checks:
            total += checks
        shown = "   -" if checks is None else f"{checks:>4}"
        tag = {PASS: "[PASS]", FAIL: "[FAIL]", SUSPECT: "[SUSP]"}[status]
        print(f"{tag} {rel:<52} {shown} checks {dt:7.1f}s"
              + (f"  {note[:70]}" if note else ""), flush=True)
        if status != PASS:
            bad.append((rel, status, note))

    print("\n" + "=" * 72)
    print(f"{tally[PASS]} green / {tally[FAIL]} red / {tally[SUSPECT]} suspect "
          f"of {len(tests)}    {total} checks    {time.time() - t_all:.0f}s")
    for rel, status, note in bad:
        print(f"  {status} {rel}  {note}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
