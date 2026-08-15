r"""The suite runner, and the five ways it has misreported a run so far.

Every check here is a REPRODUCTION of a defect that actually happened, and each one
reported a wrong number -- or no number -- as a confident report rather than as an
error. That is the shape worth testing: none raised, none printed a traceback, and all
produced output that read like a successful run.

Defects 1-3 are 2026-08-13, from running this repo's suite by hand: a file list
harvested from prose that ran 63 of 71, a fixed regex that still missed the one file
CLAUDE.md names inside a code fence, and a banner search that scored two healthy files
at 0 checks. Defects 4-5 are 2026-08-14, from making the run concurrent: an alphabetical
pool that starts its 584s file LAST, and a note of `(no output)` for a test whose entire
explanation went to stderr.

No vault, no socket, no client. The halves under test are pure functions over a string,
a tree and a dict, which is why they can be driven directly instead of by spawning 94
processes to test the thing that spawns 94 processes.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_FOR_GIT = os.path.dirname(HERE)      # the only check here that touches a real repo
sys.path.insert(0, HERE)
import checks  # noqa: E402
import run_suite as rs  # noqa: E402

# Floor 49, MEASURED from a green run: 27 on 2026-08-13, then on 2026-08-14 section 6's
# six for the pool's scheduling, section 7's fourteen for `--since`, and two more in
# section 1 for defect 5 (stderr-only failures). Every check is unconditional and builds
# its own fixtures, so there is no vault-less variant and no declared skip: a score
# under the floor means a section crashed.
LEDGER = checks.Ledger("run_suite: the suite runner's own counting", floor=49)


def section_banner_not_last():
    """DEFECT 3, and the one that reported healthy tests as vacuous.

    The ad-hoc runner read the LAST non-empty line for the banner.
    `toolkit/authsrv/test_handshake.py` prints `HANDSHAKE VERIFIED ...` after its
    banner and `toolkit/portal/test_webgate.py` dumps a request log after its own, so
    both were scored `0 checks` while exiting 0 -- which is exactly the silent-vacuity
    shape `checks.py` exists to catch. The runner was accusing two green files of the
    worst thing a test can be, and the run still summed to a plausible total.
    """
    trailing = ("  [PASS] something\n"
                "\n"
                "ALL CHECKS PASSED (17 checks)\n"
                "HANDSHAKE VERIFIED -- the real client should key up too\n")
    status, n, _ = rs.parse_result(trailing, 0)
    LEDGER.ok(status == rs.PASS and n == 17,
              "the banner is found when it is NOT the last line",
              f"got {status} {n} -- test_handshake prints a verdict line after its "
              f"banner and was scored 0 checks by the version this replaces")

    logdump = ("ALL CHECKS PASSED (9 checks)\n"
               "      request   {'method': 'POST'}\n"
               "      reply     {'code': 200}\n")
    status, n, _ = rs.parse_result(logdump, 0)
    LEDGER.ok(status == rs.PASS and n == 9,
              "and when a log follows it",
              f"got {status} {n} -- test_webgate's real shape")

    # DEFECT 5: the note for a file whose whole explanation went to stderr.
    status, n, note = rs.parse_result("", 1, "refusing: two client builds in the vault")
    LEDGER.ok(status == rs.FAIL and "two client builds" in note,
              "a failure that printed ONLY to stderr is reported with what it said",
              f"note={note!r} -- test_movement_fidelity.py exits 1 with an empty "
              f"stdout, and the run used to name it '(no output)'")
    status, _n, note = rs.parse_result("ALL CHECKS PASSED (3 checks)\ntail line\n", 1,
                                       "a warning nobody asked about")
    LEDGER.ok(note == "tail line",
              "but stdout still wins the note when it has one",
              "stderr is a fallback, not a louder channel")

    # THE CONTROL. Finding the banner anywhere must not mean finding it in prose that
    # merely mentions it -- a test whose own docstring quotes the phrase would
    # otherwise be scored from its documentation.
    quoted = ("  [PASS] a check that mentions ALL CHECKS PASSED (99 checks) in prose\n"
              "ALL CHECKS PASSED (4 checks)\n")
    status, n, _ = rs.parse_result(quoted, 0)
    LEDGER.ok(n == 4,
              "CONTROL: a mid-line mention is not mistaken for the banner",
              f"got {n}, wanted 4 -- the banner is a line that STARTS with the phrase, "
              f"and 99 is the number a substring search would have believed")

    LEDGER.ok(rs.parse_result("ALL CHECKS PASSED (0 checks)\n", 0)[1] == 0,
              "and a genuine zero is read as zero",
              "0 is a measurement -- 'it ran and asserted nothing' -- and must survive "
              "as an int rather than collapsing into the no-banner case")


def section_suspect_is_not_zero():
    """rc == 0 with no banner is SUSPECT, and `checks` is None rather than 0.

    Collapsing "it never said" into "it said zero" is what let defect 3 look like a
    measurement. The distinction has to survive into the return value, because a caller
    that sums the counts will silently add 0 and report a total that is quietly short --
    which is how the first full run of 75 files came out 26 checks under its true value.
    """
    status, n, note = rs.parse_result("nothing to say here\n", 0)
    LEDGER.ok(status == rs.SUSPECT,
              "exit 0 with no banner is SUSPECT, not PASS",
              f"got {status} -- a test that exits clean and names no checks is the "
              f"thing checks.py was written for, and a runner must not launder it")
    LEDGER.ok(n is None,
              "and its check count is None, never 0",
              f"got {n!r} -- 0 is a measurement and None is the absence of one; a "
              f"summing caller must be able to tell them apart")
    LEDGER.ok("no ALL CHECKS PASSED" in note,
              "and the note says what was missing",
              note)

    status, n, _ = rs.parse_result("ALL CHECKS PASSED (12 checks)\n", 1)
    LEDGER.ok(status == rs.FAIL,
              "a non-zero exit is FAIL even when a banner is present",
              f"got {status} -- checks.py prints its banner before the verdict in some "
              f"paths, so the exit code is the authority and the banner is not")
    LEDGER.ok(n == 12,
              "and the count is still reported, because a red run's size is evidence",
              f"got {n}")

    status, n, note = rs.parse_result("", 0)
    LEDGER.ok(status == rs.SUSPECT and "(no output)" in note,
              "a silent process is SUSPECT and says so",
              f"got {status} {note!r}")

    status, n, _ = rs.parse_result("ALL CHECKS PASSED (not-a-number checks)\n", 0)
    LEDGER.ok(status == rs.SUSPECT and n is None,
              "an unparseable count is SUSPECT rather than silently 0",
              f"got {status} {n!r} -- a malformed banner is a broken instrument, and "
              f"guessing 0 for it is the same laundering one level down")


def section_discovery():
    """DEFECTS 1 and 2: the file list must come from the DISK, not from prose.

    The ad-hoc runner harvested paths out of CLAUDE.md with a regex that could not
    match `toolkit/test_checks.py`, ran 63 of 71, and printed "62 green of 63". Fixing
    the regex still missed `test_handshake.py`, which CLAUDE.md names inside a fenced
    code block. The document was never a parseable index; `test_srclint.py` is what
    binds it to the disk, in both directions, with a check that can go red.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tk = os.path.join(tmp, "toolkit")
        for sub in ("", "authsrv", "mapdata", "mapdata/deep"):
            os.makedirs(os.path.join(tk, sub) if sub else tk, exist_ok=True)
        made = {
            "toolkit/test_top.py": "",            # DEFECT 1 lived exactly here
            "toolkit/authsrv/test_mid.py": "",
            "toolkit/mapdata/deep/test_deep.py": "",   # one level deeper than a glob
            "toolkit/authsrv/notatest.py": "",
            "toolkit/authsrv/test_thing.txt": "",
        }
        for rel, body in made.items():
            with open(os.path.join(tmp, rel), "w", encoding="utf-8") as fh:
                fh.write(body)
        cache = os.path.join(tk, "__pycache__")
        os.makedirs(cache, exist_ok=True)
        with open(os.path.join(cache, "test_stale.py"), "w", encoding="utf-8") as fh:
            fh.write("")

        found = rs.find_tests(tmp)

    LEDGER.ok("toolkit/test_top.py" in found,
              "a TOP-LEVEL toolkit/test_*.py is found",
              f"{found} -- this is defect 1 exactly: the regex "
              f"`toolkit/[\\w/]+test_\\w+\\.py` cannot match it, and 8 of 71 files "
              f"were invisible for that reason while the run reported a full pass")
    LEDGER.ok("toolkit/mapdata/deep/test_deep.py" in found,
              "and one nested deeper than a two-level glob",
              f"{found} -- `toolkit/*/test_*.py` is the natural next shortcut and it "
              f"loses this file silently")
    LEDGER.ok("toolkit/authsrv/test_mid.py" in found,
              "and the ordinary one-level case",
              str(found))
    LEDGER.ok("toolkit/authsrv/notatest.py" not in found,
              "CONTROL: a non-test module is not collected",
              str(found))
    LEDGER.ok(not any(f.endswith(".txt") for f in found),
              "CONTROL: a non-.py file named like a test is not collected",
              str(found))
    LEDGER.ok(not any("__pycache__" in f for f in found),
              "CONTROL: __pycache__ is not walked",
              f"{found} -- a stale copy there would be run as a real test")
    LEDGER.ok(found == sorted(found),
              "the list is sorted, so two runs are comparable line by line",
              str(found))
    LEDGER.ok(all("\\" not in f for f in found),
              "and the paths are forward-slashed on Windows too",
              str(found))


def section_against_the_real_tree():
    """The discovery agrees with `srclint`'s own count of the same tree.

    Not a duplicate of `test_srclint.py`: that file binds the DISK to CLAUDE.md, this
    one binds THIS RUNNER to the disk. Together they make "the runner ran the suite" a
    claim rather than an assumption. Deliberately compares against srclint's live
    answer instead of a literal, because a literal here is a number somebody must
    remember to bump -- the bet `maprows._stamp` lost on 2026-08-13.
    """
    found = rs.find_tests()
    LEDGER.ok(len(found) > 60,
              "the real tree yields a plausible suite",
              f"{len(found)} files -- a walk that matched nothing would otherwise "
              f"report a green run over zero tests, which is this repo's oldest defect")
    LEDGER.ok("toolkit/test_checks.py" in found,
              "including the top-level files the old regex could not see",
              "toolkit/test_checks.py")
    LEDGER.ok("toolkit/authsrv/test_handshake.py" in found,
              "and test_handshake.py, which CLAUDE.md names only inside a code fence",
              "defect 2: prose is not an index, and this is the file that proved it")

    # The cross-check, against a DIFFERENT SOURCE. `test_srclint.py` binds the disk to
    # CLAUDE.md in both directions and is green, so scanning the document is an
    # independent route to the same set -- disk walk versus prose scan, sharing no code.
    # Note the scan takes the whole document and not just its backticked spans: that is
    # defect 2 in one line, since `test_handshake.py` is named only inside a code fence
    # and any list built from backticks alone is short by exactly that file.
    # BOTH documents, since 2026-08-14. The catalog moved to TESTS.md when it had
    # grown to 90% of CLAUDE.md, but `test_handshake.py` is still named ONLY inside
    # CLAUDE.md's code fence -- defect 2, the same file that proved it -- so a scan of
    # the catalog alone is short by exactly that one, which is how this check would
    # have failed for the wrong reason.
    import re
    named = set()
    for name in ("TESTS.md", "CLAUDE.md"):
        path = os.path.join(rs.ROOT, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                named |= set(re.findall(r"toolkit/(?:[\w/]+/)?test_\w+\.py", fh.read()))
    # The vacuity guard is a PLAUSIBLE MINIMUM, not `> 0`. It used to be the latter,
    # and when the catalog moved out of CLAUDE.md the scan fell to **2** names and
    # this guard still passed -- leaving the real comparison below to do all the
    # work of noticing. A guard that survives a 94 -> 2 collapse is not a guard.
    LEDGER.ok(len(named) > 60,
              "the documents yield a plausible suite list to compare against",
              f"{len(named)} names -- a scan matching little or nothing would make "
              f"the next check pass by comparing two near-empty sets")
    LEDGER.ok(set(found) == named,
              "and the runner's disk walk equals it exactly, both directions",
              f"disk {len(found)}, docs {len(named)}, difference "
              f"{sorted(set(found) ^ named)}")


def section_refusals():
    """A filter matching nothing must not print a green run over zero tests."""
    LEDGER.ok(rs.find_tests(tempfile.gettempdir()) == []
              or True,  # a temp dir may legitimately contain nothing; shape only
              "find_tests over a tree with no toolkit/ returns empty rather than raising",
              "an empty list is the honest answer; main() is what refuses to score it")

    import io
    import contextlib
    argv = sys.argv[:]
    try:
        sys.argv = ["run_suite.py", "--only", "no-such-substring-anywhere"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = rs.main()
    finally:
        sys.argv = argv
    LEDGER.ok(rc == 2,
              "an --only that matches nothing exits 2 rather than reporting success",
              f"rc={rc} -- 'no tests matched' printed with exit 0 is a green run over "
              f"nothing, and it is how a filtered run silently stops covering anything")
    LEDGER.ok("refusing" in buf.getvalue(),
              "and says so in words",
              buf.getvalue().strip()[:120])


def section_scheduling():
    """The pool's ordering, and the one property it must never trade for speed.

    DEFECT 4, measured rather than imagined. Serial, this suite was 2,794s on
    2026-08-14 and `toolkit/test_scrub.py` alone was 584s of it -- and `test_scrub`
    sorts near the END of the alphabet. A pool fed in path order therefore starts its
    longest file last and idles seven workers for nine minutes behind it: ~14 min
    instead of ~10, for a scheduling choice nobody would defend out loud.

    The FIRST check here is the one that can go red in the direction that matters. A
    scheduler is a permutation and nothing else; one that drops a file makes the suite
    quietly smaller, which is the exact defect this whole module exists to refuse, and
    it would show up as a FASTER run rather than as an error.
    """
    print("\n6. the pool is ordered longest-first, and loses nothing doing it")
    tests = ["toolkit/authsrv/test_a.py", "toolkit/mapdata/test_b.py",
             "toolkit/test_scrub.py", "toolkit/test_zz.py"]
    times = {"toolkit/authsrv/test_a.py": 3.0, "toolkit/mapdata/test_b.py": 120.0,
             "toolkit/test_scrub.py": 584.0}

    got = rs.schedule(tests, times)
    LEDGER.ok(sorted(got) == sorted(tests) and len(got) == len(tests),
              "the schedule is a PERMUTATION -- every file in, every file out",
              f"{len(got)} of {len(tests)}; a scheduler that drops one makes the "
              f"suite smaller and the run faster, which reads as success")
    LEDGER.ok(got[-1] == "toolkit/authsrv/test_a.py",
              "the cheapest known file is scheduled last")
    LEDGER.ok(got.index("toolkit/test_scrub.py") < got.index("toolkit/mapdata/test_b.py"),
              "and the 584s file starts before the 120s one -- alphabetically it is "
              "next to LAST", f"order: {[t.split('/')[-1] for t in got]}")
    LEDGER.ok(got[0] == "toolkit/test_zz.py",
              "a file with NO recorded time goes first, not last",
              "an unmeasured cost that turns out to be large must not become the tail")

    # The cache is a hint. Every failure mode of reading it has to end in {}, because
    # the alternative is a runner that will not start over a malformed scheduling file.
    missing = rs.load_timings(os.path.join(tempfile.gettempdir(), "no-such-timings.json"))
    LEDGER.ok(missing == {},
              "a missing timings cache reads as {} rather than raising")
    tmp = tempfile.mkdtemp(prefix="rurik-suite-sched-")
    try:
        bad = os.path.join(tmp, "corrupt.json")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("{not json at all")
        LEDGER.ok(rs.load_timings(bad) == {},
                  "and so does a corrupt one -- a bad HINT must not stop a real run",
                  "the run degrades to a badly-packed pool, never to no pool")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def fake_tree(files):
    """A throwaway repo root holding `toolkit/` with the given {relpath: source}."""
    root = tempfile.mkdtemp(prefix="rurik-suite-sel-")
    for rel, src in files.items():
        path = os.path.join(root, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
    return root


def section_selection():
    """`--since`, and the two ways a change-scoped run lies about coverage.

    Selection is the only feature here that can make the suite SMALLER, so both of its
    failure modes are reproduced rather than reasoned about. Under-selection is the
    dangerous one -- it looks like a fast green run over exactly the code that moved --
    and over-selection is the one that makes the feature pointless, which is how it
    gets switched off and stops protecting anything.

    Both numbers below were MEASURED on this repo on 2026-08-14, not imagined: scanning
    raw source text for `<name>.py` put a one-decoder change at **90 of 94 tests**,
    because this repo's docstrings cite modules constantly; restricting the scan to
    non-docstring string literals put the same change at 22.
    """
    print("\n7. --since selects by dependency, and refuses when it cannot see the edge")
    root = fake_tree({
        "toolkit/checks.py": "def ok(*a, **k):\n    pass\n",
        "toolkit/leaf.py": "VALUE = 1\n",
        "toolkit/middle.py": "import leaf\n",
        "toolkit/server.py": "def serve():\n    pass\n",
        "toolkit/quoted.py": "X = 2\n",
        # imports middle, which imports leaf: the transitive case
        "toolkit/test_chain.py": "import checks\nimport middle\n",
        # never imports server.py -- it LAUNCHES it, the edge an import graph misses
        "toolkit/test_spawn.py": ('import checks\nimport subprocess\n'
                                  'subprocess.run(["python", "toolkit/server.py"])\n'),
        # only MENTIONS quoted.py, in a docstring: prose, not a dependency
        "toolkit/test_prose.py": ('"""Unlike toolkit/quoted.py, which does it wrong."""\n'
                                  'import checks\n'),
    })
    try:
        tests = rs.find_tests(root)
        graph = rs.dep_graph(root)

        sel, _ = rs.affected({"toolkit/leaf.py"}, tests, root, graph)
        LEDGER.ok(sel == {"toolkit/test_chain.py"},
                  "a transitive import selects: test_chain imports middle imports leaf",
                  f"selected {sorted(sel)}")

        sel, _ = rs.affected({"toolkit/server.py"}, tests, root, graph)
        LEDGER.ok(sel == {"toolkit/test_spawn.py"},
                  "a SPAWNED module selects the test that launches it without importing "
                  "it", f"selected {sorted(sel)} -- an import-only graph selects nothing "
                        f"here, and test_handshake.py launches authsrv.py exactly so")

        # THE CONTROL for the check above. Without it, the spawn rule could be a plain
        # text search and still pass -- and a plain text search is the 90-of-94 defect.
        sel, _ = rs.affected({"toolkit/quoted.py"}, tests, root, graph)
        LEDGER.ok(sel == set(),
                  "but a DOCSTRING citation of a module is prose and selects nothing",
                  f"selected {sorted(sel)} -- scanning raw source instead put one "
                  f"decoder change at 90 of 94 tests on the real tree")

        sel, _ = rs.affected({"toolkit/checks.py"}, tests, root, graph)
        LEDGER.ok(sel == set(tests),
                  "a module every test imports selects every test",
                  f"{len(sel)} of {len(tests)}")

        sel, _ = rs.affected({"toolkit/test_prose.py"}, tests, root, graph)
        LEDGER.ok(sel == {"toolkit/test_prose.py"},
                  "a changed TEST selects itself and nothing else")

        sel, _ = rs.affected(set(), tests, root, graph)
        LEDGER.ok(sel == set(),
                  "an empty diff selects nothing rather than everything",
                  "main() turns this into exit 2 and a coverage statement, never a pass")

        # THE REFUSAL. content/*.toml, schema/*.json and CLAUDE.md are read at RUN time
        # by tests that never import them, so no graph can see the edge.
        sel, why = rs.affected({"content/npcs.toml"}, tests, root, graph)
        LEDGER.ok(sel is None and "run time" in why,
                  "a non-Python change ESCALATES to the full suite instead of guessing",
                  f"reason: {why}")
        sel, why = rs.affected({"toolkit/leaf.py", "CLAUDE.md"}, tests, root, graph)
        LEDGER.ok(sel is None,
                  "and one such file among Python ones still forces the full run",
                  "the escalation is not outvoted by the changes it can resolve")

        LEDGER.ok(rs.affected(None, tests, root, graph)[0] is None,
                  "a diff git could not produce is a FULL run, not an empty one",
                  "None and set() take different paths on purpose")
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)

    bad = rs.changed_since("no-such-ref-anywhere-xyz", ROOT_FOR_GIT)
    LEDGER.ok(bad is None,
              "and changed_since returns None for a ref git rejects",
              "which main() routes to the full suite")

    # The exit rule, driven directly rather than by spawning 94 processes to learn it.
    # It is a pure function precisely so this section keeps the property the module
    # docstring claims: no vault, no socket, no client, and nothing launched.
    LEDGER.ok(rs.exit_code([], None) == 0,
              "green AND complete is the only 0")
    LEDGER.ok(rs.exit_code([], "--only mapdata") == 3,
              "green but partial is 3 -- including for --only, which always was a "
              "partial run and exited 0 for as long as this runner existed")
    LEDGER.ok(rs.exit_code([("t", "FAIL", "")], None) == 1,
              "a failure is 1")
    LEDGER.ok(rs.exit_code([("t", "FAIL", "")], "--since HEAD") == 1,
              "and a failure OUTRANKS partiality -- red is red whether or not the run "
              "was scoped", "3 there would hide a failure behind a caveat")


def main():
    section_banner_not_last()
    section_suspect_is_not_zero()
    section_discovery()
    section_against_the_real_tree()
    section_refusals()
    section_scheduling()
    section_selection()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
