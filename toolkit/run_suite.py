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

WHY IT RUNS CONCURRENTLY, AND WHAT THAT DOES NOT CHANGE. Serial, this suite measured
**2,794s over 94 files on 2026-08-14** -- and half of those files finish in under five
seconds and are 83 seconds put together, while two of them are 38% of the run. That is
a scheduling problem, not a testing one: every file is already its own process reading
its own fixtures, so the only thing serial execution was buying was the order of the
output lines. Concurrency changes **nothing** about what is asserted, what is counted,
or what `parse_result` will call a pass -- a test that was red serially is red in a
pool, and the check total is the same number. The report is sorted by path before it is
printed, so two runs are diffable regardless of who finished first.

The ordering is LONGEST-FIRST and that is the whole trick. Alphabetically,
`toolkit/test_scrub.py` -- 584s, the longest pole in the suite -- sorts near the END, so
a naive pool finishes everything else and then waits nine minutes for one file, landing
at ~14 min instead of ~10. So each run writes what it measured to `.suite-timings.json`
and the next run starts the known-slow files first. A file with no recorded time is
scheduled FIRST, not last: an unknown cost that turns out to be large must not become
the tail. The file is a cache and never a source of truth -- delete it, and the only
consequence is one badly-packed run.

WHAT CONCURRENCY CANNOT LAUNDER, because this runner's whole purpose is not lying about
a count: a parallel run that disagrees with a serial one about ANY file's verdict is a
collision, not a flake, and `--jobs 1` is kept so the two can be compared directly.
That comparison was run when this landed -- 94 files, same 93/1/0 split, same 4,620
checks, same single red file -- which is the evidence that the pool is safe here rather
than the assumption that it is.

`--since`: THE ONLY FEATURE HERE THAT CAN MAKE THE SUITE SMALLER. Twelve minutes is
still too long to sit through after every edit, so `--since HEAD` runs the tests
reachable from what actually changed -- 3 minutes for a change under `authsrv/`,
`schema/` or `portal/`. A selector has two failure modes and they are not symmetric:
over-selecting wastes time, and UNDER-selecting produces a fast green run over exactly
the code that moved. So:

  * Dependencies come from a real graph, never from a name or a directory. `ast` for
    imports, plus SPAWN edges -- `test_handshake.py` does not import `authsrv.py`, it
    launches it as a subprocess, and an import-only graph leaves it unselected when the
    server changes. Spawn edges are read from non-docstring STRING LITERALS: scanning
    raw source text instead put a one-decoder change at 90 of 94 tests, because this
    repo cites modules in prose constantly.
  * Anything the graph cannot see ESCALATES to the full suite and says which file did
    it. `content/*.toml`, `schema/messages.json` and `CLAUDE.md` are read at run time
    by tests that never import them, so a graph is structurally blind to those edges.
    Refusing to guess is `CLAUDE.md`'s rule and this is where it applies.
  * A green partial run exits **3, never 0**, and prints how many files never ran. The
    banner is what survives being pasted into a report; the exit code is what survives
    being consumed by a script. **`--only` counts as partial too** -- it always was one,
    and it exited 0 for as long as this runner existed. That is the same defect from
    the same side, so it moved to 3 with `--since`; a bare run is untouched.
  * Selecting NOTHING is reported as a coverage statement and exit 2 -- eleven modules
    in `toolkit/` have no test reachable from them at all, and a change confined to one
    of those must not read as an all-clear.

`python toolkit/run_suite.py`, with no flags, is the suite. Nothing else is.

    python toolkit/run_suite.py                 # everything, concurrently
    python toolkit/run_suite.py --since HEAD    # only what your edits can reach
    python toolkit/run_suite.py --since main    # everything this branch touches
    python toolkit/run_suite.py --jobs 1        # one at a time, the old behaviour
    python toolkit/run_suite.py --only mapdata  # substring filter on the path
    python toolkit/run_suite.py --list          # what would run, and stop

Exit code is 0 only when every file passed, none was SUSPECT, and every file RAN.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

TIMINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       ".suite-timings.json")

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


def parse_result(stdout, returncode, stderr=""):
    """(status, checks, note) for one finished test process.

    DEFECT 5, and it cost a real diagnosis on 2026-08-14. `test_movement_fidelity.py`
    refuses to pool captures from two client builds, and it prints that refusal to
    STDERR and exits 1 with stdout completely empty -- so the run reported
    `FAIL ... (no output)`, which names nothing and sends the reader to run the file by
    hand to find out what it already knew. The banner is still looked for on stdout
    alone, because a verdict line is stdout by construction; stderr is consulted only
    to answer "what did it SAY", which is the entire value of the note.

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
    err = [l.strip() for l in (stderr or "").splitlines() if l.strip()]
    last = lines[-1] if lines else (f"(stderr) {err[-1]}" if err else "(no output)")
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
    status, checks, note = parse_result(p.stdout, p.returncode, p.stderr)
    return status, checks, note, time.time() - t0


def changed_since(ref, root=None):
    """Repo-relative paths differing from `ref`, working tree and untracked included.

    Untracked files count. A brand-new module nobody has added yet is exactly the
    change most likely to break something, and `git diff` alone cannot see it.
    Returns None -- not an empty set -- when git cannot answer, because "nothing
    changed" and "I could not tell" must take different paths at the call site.
    """
    root = root or ROOT
    out = set()
    for cmd in (["git", "diff", "--name-only", ref],
                ["git", "ls-files", "--others", "--exclude-standard"]):
        try:
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
        except OSError:
            return None
        if p.returncode != 0:
            return None
        out.update(l.strip().replace("\\", "/") for l in p.stdout.splitlines()
                   if l.strip())
    return out


def module_index(root=None):
    """Bare module name -> every `toolkit/` file that could satisfy it.

    Imports in this repo are FLAT -- `import checks`, `import vaultpath`, `import
    gwdat` -- because each entry point does `sys.path.insert(0, HERE)` rather than
    installing a package. So a name resolves by basename, and where two directories
    hold the same basename it resolves to BOTH. Over-selecting is the safe direction:
    the cost is a test that did not need to run, and the cost of the other mistake is
    a change that ships untested behind a green banner.
    """
    idx = {}
    for where, dirs, files in os.walk(os.path.join(root or ROOT, "toolkit")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(where, f), root or ROOT)
                idx.setdefault(f[:-3], set()).add(rel.replace(os.sep, "/"))
    return idx


def dep_graph(root=None):
    """file -> the `toolkit/` files it depends on, by IMPORT and by SPAWN.

    The spawn edges are the half a naive selector gets wrong, and they are not an
    edge case here: `test_handshake.py` does not import `authsrv.py`, it launches it
    as a subprocess, and so do a dozen others. An import-only graph would leave every
    one of them unselected when the server changed -- a fast green run over exactly
    the code that moved. So a file also depends on any non-test module whose FILENAME
    appears in a STRING LITERAL THAT IS NOT A DOCSTRING.

    That qualifier is doing real work and was measured, not assumed. Scanning raw
    source text instead, a change to one decoder selected **90 of 94 tests** -- this
    repo's docstrings cite other modules constantly, and prose citations are not
    dependencies. Comments fall out for free (the AST never sees them); docstrings are
    excluded explicitly. What survives is `[sys.executable, "toolkit/authsrv/
    authsrv.py"]`, which is exactly the edge that matters.
    """
    root = root or ROOT
    idx = module_index(root)
    graph = {}
    for names in idx.values():
        for rel in names:
            try:
                with open(os.path.join(root, rel), encoding="utf-8",
                          errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            deps = set()
            try:
                tree = ast.parse(src)
            except SyntaxError:
                graph[rel] = set()        # unparseable: claim no edges, never guess
                continue
            docstrings = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef,
                                     ast.AsyncFunctionDef)):
                    body = getattr(node, "body", None) or []
                    if (body and isinstance(body[0], ast.Expr)
                            and isinstance(body[0].value, ast.Constant)
                            and isinstance(body[0].value.value, str)):
                        docstrings.add(id(body[0].value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        deps |= idx.get(a.name.split(".")[0], set())
                elif isinstance(node, ast.ImportFrom) and node.module:
                    deps |= idx.get(node.module.split(".")[0], set())
                elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and id(node) not in docstrings):
                    for hit in re.findall(r"\b(\w+)\.py\b", node.value):
                        if not hit.startswith("test_"):
                            deps |= idx.get(hit, set())
            graph[rel] = deps - {rel}
    return graph


def affected(changed, tests, root=None, graph=None):
    """(selected_tests, reason). `selected` is None when the diff forces a FULL run.

    THE REFUSAL IS THE POINT. A change to `content/*.toml`, `schema/messages.json`,
    `CLAUDE.md` or any other non-Python file is read at RUN time by tests that never
    import it, so no dependency graph can see the edge -- `test_content.py` and
    `test_srclint.py` would go unselected by a change aimed straight at them. This
    function does not guess at those; it escalates to the whole suite and says which
    file made it do so. `CLAUDE.md` calls that refusing to guess, and the direction of
    error a selector must never take is the one that looks like a faster green run.
    """
    if changed is None:
        return None, "git could not report a diff"
    py = {c for c in changed if c.startswith("toolkit/") and c.endswith(".py")}
    other = sorted(changed - py)
    if other:
        return None, (f"{len(other)} change(s) outside toolkit/*.py, which tests read "
                      f"at run time rather than import: {', '.join(other[:3])}"
                      + (" ..." if len(other) > 3 else ""))
    if not py:
        return set(), "no change since the ref"

    graph = dep_graph(root) if graph is None else graph
    picked = set()
    for t in tests:
        seen, stack = set(), [t]
        while stack:                                  # transitive: A spawns B imports C
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(graph.get(cur, ()))
        if seen & py:
            picked.add(t)
    return picked, f"{len(py)} changed module(s)"


def exit_code(bad, partial):
    """0 only when everything passed AND everything ran.

    Pure, so the rule can be checked without spawning 94 processes to find out. A
    failure outranks partiality -- red is red whether or not the run was scoped, and
    reporting 3 for a run with a red file in it would hide the failure behind a
    caveat.
    """
    if bad:
        return 1
    return 3 if partial is not None else 0


def load_timings(path=TIMINGS):
    """Last run's per-file seconds, or {} -- a missing or corrupt cache is not an error.

    Deliberately swallows everything. This file exists to pack the pool better; a
    runner that refused to start because a scheduling HINT was malformed would be
    trading a real capability for a cosmetic one.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            got = json.load(fh)
        return {k: float(v) for k, v in got.items()} if isinstance(got, dict) else {}
    except Exception:
        return {}


def save_timings(times, path=TIMINGS):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({k: round(v, 1) for k, v in sorted(times.items())}, fh, indent=1)
    except OSError:
        pass


def schedule(tests, times):
    """Longest-known-first, unknowns before everything.

    An unrecorded file sorts first BECAUSE its cost is unknown. The opposite choice --
    treating "never measured" as "probably quick" -- is how a newly added corpus sweep
    would end up starting last and setting the wall clock single-handedly, which is
    exactly the shape `test_scrub.py` has today.
    """
    return sorted(tests, key=lambda t: (-times.get(t, float("inf")), t))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=None,
                    help="run only files whose path contains this substring")
    ap.add_argument("--list", action="store_true",
                    help="print what would run and stop")
    ap.add_argument("--jobs", "-j", type=int, default=min(8, os.cpu_count() or 1),
                    help="files in flight at once (1 = serial, the old behaviour)")
    ap.add_argument("--since", metavar="REF", default=None,
                    help="only tests reachable from what changed vs REF (e.g. HEAD, "
                         "main). PARTIAL: exits 3 when green, never 0")
    a = ap.parse_args()

    everything = find_tests()
    tests = everything
    partial = None
    if a.since:
        picked, why = affected(changed_since(a.since, ROOT), tests, ROOT)
        if picked is None:
            print(f"FULL RUN FORCED: {why}\n")
        else:
            partial = why
            tests = sorted(picked)
    if a.only:
        tests = [t for t in tests if a.only in t]
        partial = partial or f"--only {a.only}"
    if not tests:
        # "Nothing to run" is the most dangerous thing this tool can say, so it never
        # says it quietly and never says it with exit 0. Eleven modules in `toolkit/`
        # have NO test reachable from them at all -- `rawlisten.py`, `flagscan.py`,
        # `admin.py` among them -- and a change confined to one of those lands here.
        # That is a true report about coverage, not an all-clear about the change.
        print("no test files matched -- refusing to report a green run over nothing")
        if a.since:
            print(f"  selection: {partial} vs {a.since}")
            print("  NO test in the suite depends on what you changed. That is a "
                  "statement about coverage,\n  not a pass -- run the full suite, or "
                  "write the test that would have caught this.")
        return 2
    if a.list:
        for t in tests:
            print(t)
        print(f"\n{len(tests)} file(s)")
        return 0

    jobs = max(1, a.jobs)
    times = load_timings()
    order = schedule(tests, times)
    known = sum(1 for t in order if t in times)
    if partial is not None:
        vs = f" vs {a.since}" if a.since else ""
        print(f"PARTIAL RUN -- {len(tests)} of {len(everything)} test file(s), "
              f"selected by {partial}{vs}.")
        print("This is NOT the suite and must not be reported as one.\n")
    print(f"{len(tests)} test file(s), {jobs} at a time"
          f" ({known} with a recorded time to schedule by)\n", flush=True)

    results = {}
    lock = threading.Lock()
    t_all = time.time()

    def work(rel):
        # A worker that raises must cost ONE file, not the run. `pool.map` re-raises on
        # iteration, so an unhandled OSError here -- a spawn failure, a full disk --
        # would discard 93 finished results and report a traceback instead of a count,
        # which is the same "no number at all" outcome the module docstring is about.
        try:
            status, checks, note, dt = run_one(rel)
        except Exception as exc:                                   # noqa: BLE001
            status, checks, note, dt = FAIL, None, f"runner raised: {exc!r}", 0.0
        with lock:
            results[rel] = (status, checks, note, dt)
            tag = {PASS: "[PASS]", FAIL: "[FAIL]", SUSPECT: "[SUSP]"}[status]
            shown = "   -" if checks is None else f"{checks:>4}"
            print(f"  {len(results):>3}/{len(tests)} {tag} {rel:<50} "
                  f"{shown} checks {dt:7.1f}s", flush=True)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(work, order))

    # The report is rebuilt in PATH order, never completion order, so that a parallel
    # run and a serial one produce byte-comparable output. Finishing order is a fact
    # about this machine's scheduler; it must not leak into the artifact people paste.
    tally = {PASS: 0, FAIL: 0, SUSPECT: 0}
    total = 0
    bad = []
    print()
    for rel in sorted(results):
        status, checks, note, dt = results[rel]
        tally[status] += 1
        if checks:
            total += checks
        shown = "   -" if checks is None else f"{checks:>4}"
        tag = {PASS: "[PASS]", FAIL: "[FAIL]", SUSPECT: "[SUSP]"}[status]
        print(f"{tag} {rel:<52} {shown} checks {dt:7.1f}s"
              + (f"  {note[:70]}" if note else ""))
        if status != PASS:
            bad.append((rel, status, note))

    wall = time.time() - t_all
    save_timings({**times, **{r: v[3] for r, v in results.items()}})
    cpu = sum(v[3] for v in results.values())
    print("\n" + "=" * 72)
    scope = (f"of {len(tests)} SELECTED ({len(everything)} on disk)"
             if partial is not None else f"of {len(tests)}")
    print(f"{tally[PASS]} green / {tally[FAIL]} red / {tally[SUSPECT]} suspect "
          f"{scope}    {total} checks    {wall:.0f}s wall"
          + (f" ({cpu:.0f}s serial, {jobs} jobs)" if jobs > 1 else " (serial)"))
    for rel, status, note in bad:
        print(f"  {status} {rel}  {note}")
    rc = exit_code(bad, partial)
    if rc == 3:
        # Exit 3, never 0, and the difference is the whole safety property. A green
        # PARTIAL run is a true statement about a subset and a false one about the
        # suite, and the summary line above is the only thing that survives being
        # pasted into a report -- so the banner carries the warning for humans and
        # this carries it for anything that branches on a status code. A bare
        # `run_suite.py` is untouched; `--only` reaches here too, because it always
        # was a partial run and exiting 0 for one was the same defect from the same
        # side.
        print(f"\nexit 3: green, but {len(everything) - len(tests)} file(s) never "
              f"ran. `python toolkit/run_suite.py` is the suite.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
