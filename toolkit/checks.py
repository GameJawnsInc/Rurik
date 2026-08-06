"""One verdict rule for every test in `toolkit/`: a run that measured nothing failed.

WHY THIS EXISTS, with the two times it has already cost us.

`toolkit/schema/test_codec.py` once printed ALL CHECKS PASSED and exited 0 with its
primary fixture glob matching nothing. It had 130 real captured frames available and
was checking none of them. Commit `024a982` fixed that file -- and only that file.

On 2026-08-06 `toolkit/authsrv/test_movement_fidelity.py` did the same thing in the
partial form, which is harder to see: it skipped its speed section entirely, scored
its headline number over n=2, and still printed ALL CHECKS PASSED, exit 0. It even
printed a "not measured this run" list first. The file knew what it had not done,
said so, and went green anyway.

Both are the same defect and neither was caught by a test, because the thing that was
broken WAS the test. A gate whose failure mode is silent success is worse than no gate:
it converts "we do not know" into "we verified", and it does so in the exit code that
everything else reads.

So the rule here is deliberately blunt:

  * Zero checks executed is a FAIL. Always, with no way to opt out. A run that
    asserted nothing has not passed, whatever it printed.
  * A test declares a FLOOR -- the number of checks a healthy run executes. Falling
    below it is a FAIL naming the shortfall. This is what catches partial vacuity,
    where a section quietly stops running and the remaining checks still pass.
  * Skips are allowed, but they must be declared, they are printed in the verdict,
    and they can never be silent. A skip that drops the run under its floor is a
    failure, not a note.

The floor is the load-bearing part. "Zero checks" alone would not have caught
test_movement_fidelity, which ran two.

HOW TO SET A FLOOR HONESTLY. Set it to what the test executes today on real data, not
to what you hope it executes. A floor above the real count makes a green suite
impossible and gets lowered in irritation a week later; a floor of 1 is barely better
than nothing. If a test's check count legitimately varies with the fixture, set the
floor to its mandatory core and let the optional sections declare skips.

This module is proved by `toolkit/test_checks.py`, which deliberately breaks each rule
and asserts the verdict goes red -- because a guard nobody has seen fail is exactly the
kind of thing this module exists to complain about.

A NOTE ON PRINTING, which is not incidental. Test output routinely carries bytes out of
the client: Korean strings, mojibake, raw record fragments. The default Windows console
here is cp1252, and `print()` of a non-encodable character raises UnicodeEncodeError --
which crashes the test with a traceback and a non-zero exit that has nothing to do with
what it was measuring. `test_textrec.py` did exactly this on 2026-08-06, and nobody knew,
because it was in the tree but not on CLAUDE.md's pre-flight list. A test instrument that
dies on the data it is reading is not an instrument, so every line this module prints
goes through `_say`, which degrades unencodable characters to escapes rather than
throwing. Losing the glyph is acceptable; losing the run is not.
"""
import sys


def _say(text):
    """print(), but a console that cannot encode a character never kills the run."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


class Ledger:
    """Records checks, skips and failures for one test run, and rules on the result.

    Usage:

        led = checks.Ledger("movement fidelity", floor=3)
        led.ok(p50 <= LIMIT, f"median drift under {LIMIT}")
        led.skip("run speed", "only 0 straight-run samples; need 10")
        sys.exit(led.verdict())
    """

    def __init__(self, name, floor=1):
        if floor < 1:
            raise ValueError(
                f"{name}: a floor below 1 would permit a run that checks nothing, "
                "which is the whole thing this module exists to refuse")
        self.name = name
        self.floor = floor
        self.ran = 0
        self.fails = []
        self.skips = []

    def ok(self, cond, label, detail=""):
        """Record one check. Prints [PASS]/[FAIL]. Returns the condition."""
        cond = bool(cond)
        self.ran += 1
        _say(f"  [{'PASS' if cond else 'FAIL'}] {label}"
             + (f"  {detail}" if detail else ""))
        if not cond:
            self.fails.append(label)
        return cond

    def skip(self, label, why):
        """Record a section that did not run. Never silent, never green on its own."""
        _say(f"  [SKIP] {label} -- {why}")
        self.skips.append((label, why))

    def verdict(self):
        """Print the banner and return the process exit code. 0 only if truly green."""
        if self.skips:
            _say("\nnot measured this run:")
            for label, why in self.skips:
                _say(f"  - {label}: {why}")

        reasons = []
        if self.fails:
            reasons.append(f"{len(self.fails)} CHECK(S) FAILED")
        if self.ran == 0:
            reasons.append(
                "NO CHECKS RAN -- this run asserted nothing and proves nothing")
        elif self.ran < self.floor:
            reasons.append(
                f"ONLY {self.ran} OF A DECLARED FLOOR OF {self.floor} CHECKS RAN"
                f" -- {self.floor - self.ran} did not execute, so this run is"
                " incomplete rather than passing")

        _say("")
        if reasons:
            for r in reasons:
                _say(r)
            return 1

        tail = f" ({self.ran} checks"
        tail += f", {len(self.skips)} declared skip(s))" if self.skips else ")"
        _say("ALL CHECKS PASSED" + tail)
        return 0


def adopt(ledger):
    """Return a `check(cond, msg)` callable bound to `ledger`.

    A shim for the tests that already have hundreds of `check(...)` call sites in the
    (cond, msg) order. Lets a file adopt the floor rule by changing its `def check`
    and its banner, without touching a single call.
    """
    def check(cond, msg, detail=""):
        return ledger.ok(cond, msg, detail)
    return check


def adopt_named(ledger):
    """Same as `adopt`, for the files whose signature is `check(name, cond, ...)`."""
    def check(name, cond, detail=""):
        return ledger.ok(cond, name, detail)
    return check
