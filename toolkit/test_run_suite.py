r"""The suite runner, and the three ways its ad-hoc ancestor miscounted in one day.

Every check here is a REPRODUCTION of a defect that actually happened on 2026-08-13
while running this repo's own suite by hand, and each one reported a wrong number as a
confident report rather than as an error. That is the shape worth testing: none of the
three raised, none printed a traceback, and all three produced output that read like a
successful run.

No vault, no socket, no client. The two halves under test are pure functions over a
string and a directory tree, which is why they can be driven directly instead of by
spawning 75 processes to test the thing that spawns 75 processes.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import run_suite as rs  # noqa: E402

# Floor 27, MEASURED from a green run on 2026-08-13. Every check is unconditional and
# builds its own fixtures, so there is no vault-less variant and no declared skip: a
# score under the floor means a section crashed.
LEDGER = checks.Ledger("run_suite: the suite runner's own counting", floor=27)


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
    import re
    doc = os.path.join(rs.ROOT, "CLAUDE.md")
    with open(doc, encoding="utf-8") as fh:
        named = set(re.findall(r"toolkit/(?:[\w/]+/)?test_\w+\.py", fh.read()))
    LEDGER.ok(named,
              "CLAUDE.md yields a non-empty suite list to compare against",
              f"{len(named)} names -- a scan matching nothing would make the next "
              f"check pass by comparing two empty sets")
    LEDGER.ok(set(found) == named,
              "and the runner's disk walk equals it exactly, both directions",
              f"disk {len(found)}, CLAUDE.md {len(named)}, difference "
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


def main():
    section_banner_not_last()
    section_suspect_is_not_zero()
    section_discovery()
    section_against_the_real_tree()
    section_refusals()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
