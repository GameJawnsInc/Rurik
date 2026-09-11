"""Pre-registered operator marks, on the wire capture's own clock.

    python toolkit/harness/marks.py --check-plan plan.tsv           # before the run
    python toolkit/harness/marks.py --plan plan.tsv --capture <dir> # during the run
    python toolkit/harness/marks.py --bind --capture <dir> --plan plan.tsv   # after

THE GAP. `labelrun.py` writes its step marks through OUR OWN server's recorder, and there
is no Rurik process in a live capture -- `livesession.py` launches, sniffs, taps, holds,
assembles and scrubs, and writes no mark of the operator's own doing. So both live captures
in the vault are NARRATED (a human wrote down afterwards what they had done) and never
LABELLED, and studies/reconstruction/FINDINGS.md §3.2/§10.5 makes this module a
precondition for the next live run rather than a rider on it. It is the difference between
the live corpus being prose and being a dataset.

WHAT IT IS NOT, AND THIS IS THE LINE THE LIVE-AUTOMATION RULE TURNS ON. It READS the
keyboard and never writes it. `RegisterHotKey` + a message pump is a receiver; there is no
`SendInput`, no `keybd_event`, no `PostMessage`, no mouse call anywhere in this file, and
`test_marks.py` asserts that from the SYNTAX TREE rather than from a grep, the way
`test_dispatch.py` asks the AST about its `else` chains. `drive_client.hold_key` is the
thing on the other side of that line: CLAUDE.md's live rule is that the operator plays and
the harness sends no keystrokes and no clicks, because the traffic pattern scripted input
produces is exactly what closes accounts. A tool that marks a live session must be
provably on the reading side of that, and "provably" means a check, not a docstring.

AND THE PROOF WAS WEAKER THAN IT READ, WHICH IS WHY THE HANDLE NO LONGER SURVIVES
`__init__`. A skeptic pass on 2026-08-13 built five copies of this file, each reaching
`SendInput` by a different lookup, and ran the whole suite against them. Two were caught.
THREE PASSED, all 139 checks, exit 0: `self.user32["Send" + "Input"](...)`,
`operator.attrgetter("Send" + "Input")(self.user32)(...)` and an aliased subscript. The
scan walked `ast.Attribute` off a base spelled `user32` and matched `getattr`/`setattr` by
name, so a SUBSCRIPT of the handle and any dynamic lookup that is not literally spelled
`getattr` walked past all three detectors -- and every one of them resolves a real
`_FuncPtr` off a real `ctypes.WinDLL`, which was verified against a live handle. The
detectors were widened, and more usefully the capability was taken away at the source:
`Hotkeys.__init__` binds the FOUR functions it uses and lets the handle go out of scope,
so there is no object on this class from which a fifth name can be fetched at all. The
whitelist stopped being a claim about what the scan could see and became a claim about
what exists.

WHY A HOTKEY AND NOT A KEY POLL. The client owns the foreground -- the operator is looking
at the game, which is the same reason `livesession._hold` picks marks up out of a FILE
rather than off the console. `RegisterHotKey` SWALLOWS the key: the keypress reaches this
process and never reaches Guild Wars. `GetAsyncKeyState` does not swallow, so an F9 that
marks a moment would ALSO fire whatever GW binds to F9, changing the traffic the mark
exists to describe -- an instrument that perturbs its subject. If `RegisterHotKey` fails
(another marks.py is up, or another app holds the key) this REFUSES; it does not quietly
fall back to polling, because a silent downgrade to a perturbing instrument is worse than
no instrument at all.

WHY A PRE-REGISTERED PLAN AND NOTHING TYPED DURING THE RUN. Two reasons and both are house
rules. A probe states its prediction FIRST, so the plan is written and hashed before the
client launches and the marks are ordinals into it -- after the run the plan is what the
marks MEAN, and it cannot have been edited to agree with what happened. And nothing the
operator TYPES DURING THE RUN goes into the capture, so that class of operator PII cannot
reach the artifact BY CONSTRUCTION rather than by a scrubber (§9.5 already has one leak
`test_scrub.py` reports because it cannot clean it). F11 emits a note with NO TEXT; the
text is attached afterwards by ORDINAL, from a side file -- see NOTES below for why it is
a side file and not an edit to the plan.

THAT SENTENCE USED TO SAY "nothing the operator types", FULL STOP, AND IT WAS TOO BIG.
The plan's own step text lands in `plan_marks.jsonl` verbatim, and `scrub_captures` does
not handle a `text` field -- it falls through the trailing `else` and is copied with no
count and no report, which a skeptic pass measured on 2026-08-13 by putting an account
email in a step. The property this module really has is narrower and still worth having:
the run itself has no input path, so a session cannot acquire PII it did not start with.
The plan is authored and reviewed BEFORE the client launches, which is where that review
belongs -- but it is a review, not a construction, and the header now says which.

THE OUTPUT FILE IS NOT `marks.jsonl`, AND THAT IS A CORRECTION TO THE SPEC. §10.5.1 says
"marks.jsonl, beside wire.jsonl in the same capture directory", and that name is ALREADY
TAKEN: `livesession.py:596-597` opens `<outdir>/marks.jsonl` in "w" mode and holds the handle
for the whole session, writing the driver's own `{n, label, wall, perf, wire_t}` records
through `wirecapture.write_mark`, and `behaviourrun.py:385` reads them back. Two writers on
one file, one of them holding a stale offset, is silent data loss: our appends land at end
of file and the driver's next `write` overwrites them from wherever its own handle sat. And
both record shapes use `"kind": "mark"`, so `wirecapture.read_marks` would hand
`mark_skew` our records and get "missing a channel" for every one. So this writes
`plan_marks.jsonl`, `open_marks()` REFUSES the driver's filename by name, and `read()`
refuses a file that holds both shapes -- that refusal is what catches the collision if the
two channels are ever merged deliberately. The record SHAPE is exactly §10.5.1's.

AND THE SPLIT IS A RULING, NOT A WORKAROUND. Everything above argues the separation from a
MECHANICAL cause -- the name was taken, two handles corrupt one file -- and that argument
evaporates the day somebody makes `livesession` release its handle or namespace its
records. **Owner's decision, 2026-08-13: keep them split, because "driver marks and
operator marks are different things."** That reason is semantic and does not evaporate.
The driver's channel records what the HARNESS did -- session_start, session_end, whatever
`livesession` stamps for itself -- on its own authority, with no prediction attached. This
channel records what a HUMAN did against a plan sealed before the client launched, and its
entire evidential value comes from that seal. Merged, a pre-registered record and an
un-pre-registered one would sit in one file under one `"kind"`, and no consumer could tell
which rows carry a prediction and which are the harness narrating itself. A future session
that removes the collision has removed the LESSER of the two reasons; do not merge on the
strength of it.

BINDING TO THE WIRE CLOCK, AND THE THREE CHANNELS THAT MAKE IT A CLAIM.
`wirecapture.open_capture` stamps every segment `"t": perf_counter() - t0`, and it runs as
a SEPARATE SUBPROCESS spawned by `livesession.run` -- so `t0` is not in this process and
`perf_counter()`'s reference point is undefined by CPython's own contract. `wire_meta` now
carries BOTH `t0_perf` and `t0_wall` (the `t0_perf` half was added for this module), and
every mark carries `t_perf`, `t_wall` and `wire_t`. `bind()` puts a mark on wire time as
`t = t_perf - t0_perf` and checks it two independent ways:

  * THE WALL WITNESS. `|(t_perf - t0_perf) - (t_wall - t0_wall)| <= 0.250` for every mark.
    Both stamps are sampled adjacently inside one process, so this difference is the
    OS-wide `(QPC - system time)` offset differenced against itself -- which means it can
    catch a `perf_counter` whose origin is per-process (the launch gap shows up as a
    constant offset) and a wall clock that STEPPED or drifted, and it cannot say anything
    about the axis the SEGMENTS are on. That limit is measured, not assumed: on this
    machine two processes stamping the pair adjacently agree to 5 MICROSECONDS worst case
    over 12 spawns, drifting at -0.004 ppm, so 0.250 s is roughly 50,000x the phenomenon
    its own name suggests and will essentially never fire for it. The number is kept
    because it is §10.5.1's stated criterion and because the two faults above are real;
    what changed is that this paragraph no longer claims it measures something it cannot.
  * THE WIRE WITNESS, which is the one that IS on the segment axis. Every mark records
    `wire_t`: the `t` of the last record then present in `wire.jsonl`, read off the file
    (`wirecapture.write_mark` has carried this third channel all along and this module
    shipped without it). A mark cannot have seen a segment stamped LATER than its own
    bound time, so `wire_t <= t + tolerance` is a one-sided check on the binding itself.
    It is what catches a capture whose PUBLISHED epoch is not the epoch its segments were
    stamped from -- a skeptic built exactly that on 2026-08-13, 0.9 s of silent
    mislabelling, and both clock channels reported 0.0001 ms of skew because both were
    perfectly fine. One-sided on purpose: a quiet network makes `t - wire_t` arbitrarily
    large and that is not a fault.

WHY A DRIFT VIOLATION RAISES RATHER THAN RETURNING A FLAGGED ROW. The tolerance is not a
statement about one mark. If the two clocks disagree, what may have been refuted is that
the two processes share a comparable perf_counter -- and that is the assumption under
EVERY `t` in the list, not just the one that tripped. Returning a flagged row invites a
consumer to drop it and analyse the rest, which is building an analysis on an artifact
whose central assumption has just failed; this repo's name for that is a fixture that
silently resolves to the wrong thing, turning every assertion behind it into a no-op. So
`bind()` raises, and it has no `strict=False`. §8.9's control 3 is that it goes red, and
this is that.

BUT IT SCANS EVERY MARK FIRST, AND THE SHAPE VOCABULARY HAD TO GROW A THIRD WORD. The
message used to offer two hypotheses -- an OFFSET or a RATE -- and a skeptic pass fed it
the commonest real cause, a single +0.5 s wall-clock STEP at t=70 of a 146 s session with
the perf axis untouched. It answered with BOTH diagnoses wrong: "11 of 20 marks disagree,
so this is a stamping fault at those marks" (it was one clock event, not eleven bad
stamps) and "the skew moves -3.6 ms per second, so it is a RATE (a drifting clock)" (it
was a step, which is neither). `wirecapture.mark_skew` already carries the lesson in a
comment: a wrong diagnosis sends someone hunting an NTP event that never happened. So the
skew is now differenced PAIRWISE as well as cumulatively -- the cumulative number decides
(a constant offset is invisible pairwise, and a constant offset is the launch-gap
hypothesis), the pairwise sequence names the shape -- and STEP is reported with the mark
it happened at and with the observation that the sides are flat. `drift()` is the same
computation with no verdict, for a report that wants the numbers without an escape hatch
on `bind`.

WHAT A DRIFT REFUSAL COSTS, STATED HERE BECAUSE IT IS REAL. A wall-clock step past
tolerance refuses a whole session's labels even though every perf-derived `t` in it was
correct -- measured, 20 of 20 landing exactly on their own segment. That is deliberate and
it is not free: `bind()` sees a DIFFERENCE and cannot know which of the two clocks moved,
and a stepped `perf_counter` would make every `t` after it wrong. The recovery is to bind
with an explicit larger `tolerance` (it is a parameter, and passing one is an operator
recording a judgement) and to read the STEP diagnosis first. There is no flag that makes
it quiet.

NOTES, AND THE ONE PLACE §10.5.1 CONTRADICTS ITSELF. It says a note's text is "added
afterwards by ordinal, by editing the plan", and it also says a plan whose sha256 disagrees
with `marks_meta` is REFUSED. Editing the plan changes its sha256, so following both
sentences literally makes every annotated run unbindable. The seal is the more important
half -- it is what makes the plan a pre-registration -- so notes are annotated in a
SEPARATE file, `<ordinal><TAB><text>` per line, passed to `bind(notes=...)`. The plan stays
byte-identical to what was hashed, and the note text is still recoverable by ordinal.

REFUSALS, each of them a failure this project has already had in some other form:
  * no plan file                     -- an unlabelled run must not be reachable by accident
  * a plan with no steps             -- same failure wearing a file
  * plan sha256 != marks_meta        -- the prediction was edited after the fact
  * no wire.jsonl in the directory   -- nothing to bind to
  * no wire_meta line                -- }  the capture-started-late defect
  * a mark whose t_perf < t0_perf    -- }  (20260807T124912) arriving from the other side
  * EVERY mark after the last segment -- the same defect from the END: the sniffer has a
        `--seconds` ceiling and `livesession` keeps the session going when it dies, so
        marks can outlive the recording. Disjoint is refusable without inventing a
        threshold; a PARTIAL overlap is REPORTED instead, because "the network went quiet"
        and "the sniff stopped" are not separable from the artifact and this module does
        not guess between them.
  * a mark whose wire_t is after its own bound t -- the published epoch is not the one the
        segments were stamped from
  * advance past the last plan step  -- refuse rather than wrap
  * RegisterHotKey fails             -- refuse rather than fall back to polling
  * writing to the driver's marks.jsonl -- see above
  * writing into the owner's install, vault/dat_study, any checkout of this repo, or ON
        TOP of a file that already exists -- see `resolve_out`

THE EXCEPTIONS ARE `Exception`, NOT `SystemExit`, AND THAT IS DELIBERATE. `test_atex.py`
and `test_stripbuild.py` both paid for the other choice: a refusal that is a `SystemExit`
is a `BaseException`, so a control written as `try: ...  except Exception:` does not catch
it -- the run dies with no verdict banner and no ledger, and a caught defect reads as a
crash. Every refusal here is a `MarksError`. `main()` is the only thing that turns one into
an exit code.

Windows only for the HOTKEY half, standard library only, importable anywhere. `ctypes` is
imported at module scope (it is stdlib on every platform) but `ctypes.windll` is resolved
lazily inside `_load_user32`, and no `wintypes` name appears anywhere -- `keytap.py` and
`tcptable.py` both bind `wintypes` at import and are therefore unimportable off Windows,
which is why `test_keytap.py` has to skip whole. This file's plan, writer, reader and
binder are pure, and its message loop takes the `user32` handle as an argument, so
`test_marks.py` drives the whole thing off a fake on any platform.
"""
import argparse
import collections
import ctypes
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))


# --------------------------------------------------------------------- names --
# The driver's own marks channel. NOT ours: see the header. `wirecapture.MARKS_NAME` is
# the authority when it can be imported, and it usually cannot -- wirecapture imports
# tcptable, which binds `ctypes.wintypes` at module scope and blows up off Windows. So the
# literal is pinned here and `driver_marks_name()` prefers the real one when it is
# reachable, which keeps the two from drifting apart on the platform that matters.
DRIVER_MARKS_NAME = "marks.jsonl"
PLAN_MARKS_NAME = "plan_marks.jsonl"
WIRE_NAME = "wire.jsonl"


def driver_marks_name():
    """The filename `livesession.py` writes its own marks to, resolved not assumed."""
    try:
        import wirecapture
        return wirecapture.MARKS_NAME
    except Exception:            # noqa: BLE001 -- off Windows this is an unimportable dep
        return DRIVER_MARKS_NAME


# ---------------------------------------------------------------- exceptions --
class MarksError(Exception):
    """Any refusal in this module. An `Exception`, never a `SystemExit` -- see header."""


class PlanError(MarksError):
    """The pre-registered plan is missing, empty, malformed, or not the one that was run."""


class PlanExhausted(MarksError):
    """Advance past the last step. Refused rather than wrapped: a wrapped ordinal would
    quietly re-label the rest of the session as the beginning of the script."""


class NothingToRepeat(MarksError):
    """Repeat before the first advance. There is no current step to re-emit."""


class BindError(MarksError):
    """The capture and the marks cannot be put on one clock."""


class ClockDrift(BindError):
    """`|dperf - dwall|` exceeded the tolerance -- the two processes' clocks are not
    comparable, so no mark's wire time can be trusted. Raised, never flagged: see header."""


class HotkeyRefused(MarksError):
    """A hotkey could not be registered. The run refuses rather than polling instead."""


# ---------------------------------------------------------- where it may write --
def _inside(path, root):
    """True if `path` is `root` or below it. Case-folded, because this is Windows."""
    path = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(os.path.abspath(root))
    return path == root or path.startswith(root + os.sep)


def working_tree_roots():
    """Every checkout of this repository a write could land in.

    `atex.working_tree_roots`'s shape and its reason: inside a git worktree `REPO_ROOT`
    is NOT the main checkout -- the worktree's `.git` is a FILE reading
    `gitdir: <main>/.git/worktrees/<name>` -- so a refusal that tested `REPO_ROOT` alone
    lets a write land straight in the other tree of the same repository. `mapbuild.py`
    measured that from a worktree: `<main>/toolkit/out.dat` was ALLOWED.

    Never raises. An unreadable `.git` yields the roots we could establish and the caller
    still refuses `REPO_ROOT`.
    """
    roots = [os.path.abspath(REPO_ROOT)]
    dotgit = os.path.join(REPO_ROOT, ".git")
    if not os.path.isfile(dotgit):
        return roots                       # a normal checkout, or no git at all
    try:
        with open(dotgit, "r", encoding="utf-8", errors="replace") as fh:
            line = fh.read().strip()
    except OSError:
        return roots
    if not line.startswith("gitdir:"):
        return roots
    gitdir = line.split(":", 1)[1].strip()
    if not os.path.isabs(gitdir):
        gitdir = os.path.join(REPO_ROOT, gitdir)
    node = os.path.abspath(gitdir)         # <main>/.git/worktrees/<name>  ->  <main>
    while os.path.basename(node) != ".git":
        parent = os.path.dirname(node)
        if parent == node:
            return roots
        node = parent
    main_root = os.path.dirname(node)
    if main_root and not _inside(main_root, roots[0]):
        roots.append(main_root)
    return roots


def resolve_out(path):
    """Where a marks file may be written. Raises `MarksError` otherwise.

    THIS MODULE HAD NO DESTINATION GUARD AT ALL AND IT IS A WRITER. A skeptic pass on
    2026-08-13 read the syntax tree: the only conditional on the destination was the
    driver-filename basename compare, the only write-mode call was `open(self.path, "w")`
    straight off `--out`, and there were zero calls to any path guard. Measured: `--out`
    aimed at a pre-existing 4,096-byte file named `Gw.dat` in a scratch directory replaced
    it with 533 bytes of JSON, because `open(path, "w")` TRUNCATES ON OPEN -- before a
    single mark is written. That is `atex.py --make C:\\gw\\Gw.dat` in a new module, the
    exact defect `test_atex.py` section 3 was built for, and it would have taken the
    owner's 4.2 GB archive.

    Four refusals and each has a POSITIVE CONTROL in `test_marks.py`, because a guard that
    refuses everything protects nothing -- the tool then never runs and gets deleted:

      * `C:\\gw`             the owner's install, read-only to this project, permanently.
      * `vault/dat_study`   the SOURCE snapshot every measurement in `studies/` was taken
                            against. Inside the vault, so it is refused BEFORE the vault
                            is allowed -- the order is load-bearing, as in `atex.py`.
      * every checkout      a capture artifact is vault data and `.gitignore` keeps it out
                            of the tree; the worktree case is why `working_tree_roots`
                            exists rather than one `REPO_ROOT` test.
      * a path that EXISTS  the file is opened "w". A marks file already sitting in a
                            capture directory is a previous run's artifact in the one
                            place a live run cannot be reproduced, so this refuses rather
                            than truncates. `--out` names another path.

    `MarksError`, never a `SystemExit`, unlike `atex.Refused` -- the header says why, and
    `test_atex.py` records the cost of the other choice.
    """
    full = os.path.abspath(path)
    parts = os.path.normcase(full).replace("\\", "/").split("/")
    if "dat_study" in parts:
        raise MarksError(
            f"refusing to write marks to {full}\n"
            f"  vault/dat_study is the SOURCE snapshot every other archive in the vault "
            f"is cut from, and every measurement in studies/ was taken against it.")
    if _inside(full, LIVE_INSTALL):
        raise MarksError(
            f"refusing to write marks to {full}\n"
            f"  That is the owner's own install at {LIVE_INSTALL} and it is read-only to "
            f"this project, permanently (CLAUDE.md). This file is opened in 'w' mode, so "
            f"naming an existing file there would TRUNCATE it before the first mark.")
    # THE VAULT IS THE INTENDED DESTINATION and it sits inside the main checkout, so it is
    # allowed BY NAME before the tree test below. It is gitignored, which is exactly why
    # captures live in it.
    in_vault = False
    try:
        import vaultpath
        in_vault = _inside(full, vaultpath.vault_root())
    except (ImportError, SystemExit, OSError):
        pass                               # no vault resolvable; fall through to the tree
    if not in_vault:
        for root in working_tree_roots():
            if _inside(full, root):
                raise MarksError(
                    f"refusing to write marks into a checkout of this repository: {full}\n"
                    f"  That tree is {root}"
                    + (" -- the MAIN checkout, which this worktree shares a repository "
                       "with.\n" if root != os.path.abspath(REPO_ROOT) else "\n")
                    + f"  A capture and its marks are vault data: personal, from the "
                    f"owner's own account, and gitignored on purpose. Write under the "
                    f"capture directory the run created.")
    if os.path.exists(full):
        raise MarksError(
            f"refusing to write marks to {full}: something is already there.\n"
            f"  This file is opened in 'w' mode, which TRUNCATES on open -- so pointing "
            f"a run at an existing path destroys it before the first mark is written, "
            f"and a marks file already in a capture directory is a previous run's "
            f"artifact in the one place a live session cannot be reproduced. Move it "
            f"aside, or name another path with --out.")
    return full


# --------------------------------------------------------------------- plan ----
Step = collections.namedtuple("Step", "index kind text")

_COMMENT = "#"


def plan_sha256(path):
    """sha256 of the plan file's RAW BYTES.

    Raw bytes, not a normalised parse: this is a pre-registration SEAL, so a changed line
    ending or a stripped trailing space is a different plan and should read as one. The
    hash is what lets a reader of the artifact know the prediction was not rewritten to
    agree with the result.
    """
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError as exc:
        raise PlanError(f"cannot read the plan file {path!r}: {exc}") from exc


def load_plan(path):
    """[Step(index, kind, text)] for a plan file. Refuses a missing or empty plan.

    One step per line, `kind<TAB>text`. Blank lines and full-line `#` comments are ignored
    and do NOT consume an ordinal, so the plan can be annotated for the operator without
    moving the step numbers the marks refer to. `kind` alone with no tab is accepted (some
    steps genuinely have nothing to predict beyond their name); an empty `kind` is not,
    because a step that names nothing cannot be a prediction.
    """
    if not path:
        raise PlanError(
            "no plan file. An unlabelled run must not be reachable by accident: the plan "
            "IS the pre-registered prediction, and without it a mark is an ordinal into "
            "nothing. Write one (kind<TAB>text per line) and pass --plan.")
    if not os.path.isfile(path):
        raise PlanError(
            f"no plan file at {path!r}. The plan is written and hashed BEFORE the client "
            f"launches -- see RUNBOOK's live-capture procedure.")
    steps = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith(_COMMENT):
                continue
            kind, _tab, text = line.partition("\t")
            kind = kind.strip()
            if not kind:
                raise PlanError(
                    f"{os.path.basename(path)} line {lineno}: the step kind is empty. "
                    f"The line is {line!r}; the format is kind<TAB>text.")
            steps.append(Step(len(steps), kind, text.strip()))
    if not steps:
        raise PlanError(
            f"{os.path.basename(path)} has no steps. An empty plan is the unlabelled run "
            f"wearing a file -- refused for the same reason a missing one is.")
    return steps


def load_notes(path):
    """{ordinal: text} for a note-annotation file, or {} when there is none.

    `<ordinal><TAB><text>` per line, ordinal 1-based over the NOTES of a run (not over the
    plan). This is the file the spec's "edit the plan afterwards" would have been, moved
    out so the plan's sha256 seal survives the annotation -- see the header.
    """
    if not path:
        return {}
    if not os.path.isfile(path):
        raise PlanError(f"no notes file at {path!r}")
    out = {}
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith(_COMMENT):
                continue
            head, _tab, text = line.partition("\t")
            try:
                n = int(head.strip())
            except ValueError:
                raise PlanError(
                    f"{os.path.basename(path)} line {lineno}: {head.strip()!r} is not a "
                    f"note ordinal. The format is <ordinal><TAB><text>.") from None
            out[n] = text.strip()
    return out


# ------------------------------------------------------------------- writer ----
class Marker:
    """Writes `plan_marks.jsonl`: the meta line, then one record per operator mark.

    The clock is injected (`clock`, `wall`) exactly the way `wirecapture.open_capture`
    injects it, so a pure test supplies deterministic ones and every timestamp in this
    file becomes something a test can assert on rather than something it has to tolerate.

    `advance` / `repeat` / `note` are the whole surface, and each RAISES on the state it
    cannot represent rather than inventing one. The run loop catches those, writes no
    record, says so, and keeps going -- an operator whose finger slips past the last step
    must not lose the rest of the session's marks, and killing the process would do
    exactly that while they are looking at the game and not at this console. The refusals
    are counted into the closing `marks_end` record so they are visible in the ARTIFACT
    and not only on a console nobody was reading.
    """

    def __init__(self, path, steps, plan_sha, plan_name="", pid=None,
                 clock=time.perf_counter, wall=time.time, wire_path=""):
        self.path = path
        self.steps = list(steps)
        self.plan_sha = plan_sha
        self.plan_name = plan_name
        self.pid = os.getpid() if pid is None else pid
        self.clock = clock
        self.wall = wall
        # The THIRD channel. "" means none was offered, and every mark then omits the
        # field rather than carrying a null that reads as "no segment yet" -- those are
        # different facts and a consumer must be able to tell them apart.
        self.wire_path = wire_path
        self.fh = None
        self.seq = 0
        self.cur = None            # index of the step in effect; None before the first
        self.notes = 0
        self.refused = 0

    # -- lifecycle -----------------------------------------------------------
    def open(self):
        """Create the file and write `marks_meta`. Refuses the driver's filename.

        The reserved-name test comes FIRST because it is the more specific answer: aimed
        at `<capture>/marks.jsonl` an operator wants to hear about the driver's channel,
        not about directories. `resolve_out` then rules on WHERE, and it is the guard this
        module shipped without.
        """
        reserved = driver_marks_name()
        if os.path.basename(self.path).lower() == reserved.lower():
            raise MarksError(
                f"refusing to write {reserved!r}: livesession.py opens that file in 'w' "
                f"mode and holds the handle for the whole session, so a second writer's "
                f"records are overwritten from the driver's own stale offset -- silent "
                f"loss, in the one artifact a live run cannot reproduce. Write "
                f"{PLAN_MARKS_NAME!r} instead (the default).")
        self.path = resolve_out(self.path)
        self.fh = open(self.path, "w", encoding="utf-8")
        t0_perf, t0_wall = self.clock(), self.wall()
        self._write({"kind": "marks_meta", "plan_sha256": self.plan_sha,
                     "plan": self.plan_name, "steps": len(self.steps),
                     "t0_perf": t0_perf, "t0_wall": t0_wall, "pid": self.pid,
                     "tool": "toolkit/harness/marks.py"})
        return self

    def close(self, why="clean"):
        """Write the closing record and close. Idempotent.

        `marks_end` is not decoration: without it a marks file that was truncated by a
        kill is indistinguishable from one that finished, and "the operator stopped
        marking" and "the marker died" are different facts about a session.
        """
        if self.fh is None:
            return
        try:
            self._write({"kind": "marks_end", "why": why, "marks": self.seq,
                         "notes": self.notes, "refused": self.refused,
                         "last_step": self.cur,
                         "t_perf": self.clock(), "t_wall": self.wall()})
        finally:
            fh, self.fh = self.fh, None
            fh.close()

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close("clean" if exc_type is None else f"{exc_type.__name__}")
        return False

    # -- the three marks -----------------------------------------------------
    def advance(self):
        """Emit the next plan step. Raises PlanExhausted past the last one."""
        nxt = 0 if self.cur is None else self.cur + 1
        if nxt >= len(self.steps):
            self.refused += 1
            raise PlanExhausted(
                f"the plan has {len(self.steps)} steps and step {self.steps[-1].index} "
                f"({self.steps[-1].kind}) is already current; there is no step "
                f"{nxt} to advance to. Refused rather than wrapped -- a wrapped ordinal "
                f"would silently re-label the rest of the session as the top of the "
                f"script. Press F11 to note the moment instead.")
        self.cur = nxt
        return self._mark("advance")

    def repeat(self):
        """Re-emit the current step -- the operator did the same thing again."""
        if self.cur is None:
            self.refused += 1
            raise NothingToRepeat(
                "repeat before the first advance: there is no current step to re-emit. "
                "Press F9 to open step 0 first.")
        return self._mark("repeat")

    def note(self):
        """Emit a note with NO TEXT. Text is attached afterwards by ordinal."""
        self.notes += 1
        return self._mark("note", note_ordinal=self.notes)

    # -- record --------------------------------------------------------------
    def _mark(self, mark, **extra):
        step = self.steps[self.cur] if self.cur is not None else None
        rec = {"kind": "mark", "seq": self.seq + 1, "mark": mark,
               "step": None if step is None else step.index,
               # A NOTE CARRIES NO TEXT, and that is the PII property, not a default.
               # advance/repeat text is the PLAN's, which was written before the client
               # launched; nothing the operator types during the run reaches this file.
               "text": "" if mark == "note" or step is None else step.text,
               "t_perf": self.clock(), "t_wall": self.wall()}
        if self.wire_path:
            # Read the capture's own last `t` -- the only channel of the three that is on
            # the SEGMENT axis. None until the sniffer has written a segment, which is a
            # real state (the mark that says "the sniff is up") and is recorded as such.
            rec["wire_t"] = last_wire_t(self.wire_path)
        rec.update(extra)
        self.seq = rec["seq"]
        self._write(rec)
        return rec

    def _write(self, rec):
        # No `origin` field, ever, and none of origin.PEER_FIELDS either: origin.origin_of
        # reads EVERY record in a file looking for contradictions, so a mark that named a
        # peer or stated an origin could flip a capture's provenance verdict. §10.5.1 names
        # this; it is checked in test_marks.py rather than left to this comment.
        if self.fh is None:
            raise MarksError("the marks file is not open")
        self.fh.write(json.dumps(rec) + "\n")
        self.fh.flush()


def open_marks(capture_dir, plan_path, out=None, pid=None,
               clock=time.perf_counter, wall=time.time, wire_path=None):
    """Load and seal the plan, then open a Marker in `capture_dir`. The usual entry.

    `wire_path` is a THREE-VALUED argument and the three values are different facts:
    `None` (the default) DERIVES `<capture_dir>/wire.jsonl`, so the third channel is on by
    default in every real run rather than being an option somebody remembers; `""` says
    explicitly that there is no capture to read, which is what a fixture wants; and an
    explicit path is an explicit path.
    """
    steps = load_plan(plan_path)
    sha = plan_sha256(plan_path)
    path = out or os.path.join(capture_dir, PLAN_MARKS_NAME)
    if wire_path is None:
        wire_path = os.path.join(capture_dir, WIRE_NAME) if capture_dir else ""
    return Marker(path, steps, sha, plan_name=os.path.basename(plan_path),
                  pid=pid, clock=clock, wall=wall, wire_path=wire_path).open()


# ------------------------------------------------------------------ hotkeys ----
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A

# MOD_NOREPEAT is the OS doing the edge detection for us: with it, holding F9 down fires
# ONE WM_HOTKEY, not one per auto-repeat. That is half of "an edge fires once per press";
# the other half is that WM_HOTKEY is a QUEUED message, so the number of marks is the
# number of presses however often the loop wakes up. Neither property is available to a
# GetAsyncKeyState poll, which is the other reason not to use one.
MOD_NOREPEAT = 0x4000

WM_QUIT = 0x0012
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
QS_ALLINPUT = 0x04FF
WAIT_TIMEOUT = 0x00000102
ERROR_HOTKEY_ALREADY_REGISTERED = 1409

# Application hotkey ids must be in 0x0000..0xBFFF. Nothing else in this repo registers
# one, so the base is arbitrary; it is high to stay clear of any id a future window
# procedure in the same thread might pick.
HOTKEY_BASE = 0xBEE0

ADVANCE, REPEAT, NOTE = "advance", "repeat", "note"

# The three the spec names, in id order. Kept as data so the loop has no VK literals in it
# and a test can bind a different set without touching the loop.
DEFAULT_BINDINGS = ((VK_F9, ADVANCE), (VK_F10, REPEAT), (VK_F11, NOTE))


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    """The Win32 MSG, spelled in PLATFORM-NEUTRAL ctypes types on purpose.

    `wintypes` cannot be imported off Windows, and this module has to be importable
    everywhere so `test_marks.py` can drive the loop against a fake `user32` on any
    machine -- the thing `test_keytap.py` could not do, which is why it skips whole. The
    widths are the same ones `wintypes` would give: HWND is a pointer, WPARAM/LPARAM are
    pointer-sized, `time` is a DWORD.
    """
    _fields_ = [("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint),
                ("wParam", ctypes.c_size_t),
                ("lParam", ctypes.c_ssize_t),
                ("time", ctypes.c_ulong),
                ("pt", _POINT)]


def _load_user32():
    """The real user32, resolved lazily so importing this module works off Windows."""
    if not hasattr(ctypes, "windll"):
        raise HotkeyRefused(
            f"the hotkey loop is Windows-only (RegisterHotKey); this is "
            f"{sys.platform}. The plan, writer, reader and binder are pure and run "
            f"anywhere -- only --plan/--capture (the run) needs Windows.")
    return ctypes.WinDLL("user32", use_last_error=True)


class Hotkeys:
    """Registers the mark hotkeys and hands back one event per press. Never sends a key.

    Four `user32` calls and nothing else, so a fake is four methods:

        class FakeUser32:
            def RegisterHotKey(self, hwnd, hk_id, mods, vk) -> 1/0
            def UnregisterHotKey(self, hwnd, hk_id)         -> 1/0
            def MsgWaitForMultipleObjects(self, n, handles, all_, ms, mask) -> 0 or 258
            def PeekMessageW(self, msg, hwnd, lo, hi, flags) -> 1/0, setting
                                                                msg._obj.message/.wParam

    (the `msg._obj` idiom is `test_harness.FakeUser32.GetWindowThreadProcessId`'s, because
    the module passes `ctypes.byref(...)` and a fake reads the referent back off it.)

    THE DRAIN COMES BEFORE THE WAIT, and that ordering is not stylistic.
    `MsgWaitForMultipleObjects` only reports messages that arrived since the last
    message-retrieval call marked the queue read, so "wait, then peek once" parks forever
    with a message already sitting in the queue -- the classic Win32 message-loop bug. So
    every pass drains with `PeekMessage` until it returns 0, and only then waits.

    THE HANDLE DOES NOT SURVIVE `__init__`, AND THAT IS THE POINT OF THE FOUR BINDINGS
    BELOW. `self.user32` used to be a public attribute holding an unrestricted
    `ctypes.WinDLL("user32")`, and a skeptic proved on a live handle that
    `hk.user32["Send" + "Input"]` and `operator.attrgetter("Send" + "Input")(hk.user32)`
    both resolve real `_FuncPtr` objects -- three such routes passed the entire test file,
    139 checks, exit 0, because the scan modelled attribute access and not subscript or
    computed lookup. Binding the four functions here and letting the handle go out of
    scope means the class holds no object from which a fifth name CAN be fetched. The
    whitelist in `test_marks.py` is then a claim about what exists rather than about what
    a scanner noticed, which is the difference between a proof and a sampling.

    A HOTKEY CANNOT SURVIVE THIS OBJECT, AND FIVE PATHS ONCE SAID OTHERWISE. `register`
    installs its `atexit` hook BEFORE taking the first key and releases on ANY exception,
    `unregister` is idempotent, does not drop an id it has not actually released, and
    REPORTS what the OS refused. The five leaks a skeptic drove out on 2026-08-13, each
    against a fake keeping its own OS-side ledger, each now covered:

      * `RegisterHotKey` RAISING mid-loop. The failure branch only fired on a falsy
        RETURN, and the `atexit` hook was installed AFTER the loop -- so there was no net
        at all: two keys held, `UnregisterHotKey` called zero times, zero atexit callbacks.
      * the same inside `main()`'s `with Hotkeys() as hk`, where `__enter__` raised so
        `__exit__` never ran.
      * Ctrl-C between two `RegisterHotKey` calls: F9 left held.
      * `UnregisterHotKey` returning 0. The return value was discarded, so the object
        believed it had released while the OS still held all three -- and that is not a
        fixture artefact: a real `UnregisterHotKey` from the wrong thread was measured
        returning 0 with WinError 1419 on a key that was demonstrably still taken.
      * Ctrl-C INSIDE `unregister`: `except Exception` does not catch a `BaseException`,
        and the id had already been popped from `_taken`, so the `atexit` hook's later
        call could never reach it.

    Underneath all five, Windows itself releases a thread's hotkeys when that thread
    exits, and that backstop is now MEASURED rather than asserted: a child process took
    VK_F24 globally, a live control confirmed the parent could not take it (WinError 1409,
    ERROR_HOTKEY_ALREADY_REGISTERED), `taskkill /F` killed the child with no `finally` and
    no `atexit`, and the parent took the key at +0.0 s. VK_F24 rather than VK_F9 so a
    negative result would have cost a key no keyboard has. So the leaks above were bounded
    to a LIVE process -- which is exactly the case §10.5.1's integration creates, since
    `livesession.run` is long-lived and a leaked registration there keeps SWALLOWING
    F9/F10/F11 from the client mid-capture.
    """

    def __init__(self, user32=None, bindings=DEFAULT_BINDINGS, base_id=HOTKEY_BASE,
                 last_error=None, mods=MOD_NOREPEAT):
        user32 = user32 if user32 is not None else _load_user32()
        # THE FOUR, BOUND HERE AND NOWHERE ELSE. `user32` is a local and is not stored:
        # see the class docstring. A fake supplies four methods and works unchanged.
        self._register_hotkey = user32.RegisterHotKey
        self._unregister_hotkey = user32.UnregisterHotKey
        self._wait_for_message = user32.MsgWaitForMultipleObjects
        self._peek_message = user32.PeekMessageW
        self.bindings = tuple(bindings)
        self.base_id = base_id
        self.mods = mods
        self._last_error = last_error or (lambda: ctypes.get_last_error())
        self.ids = {}              # hotkey id -> action name
        self._taken = []           # ids actually registered, for the teardown
        self._atexit = None
        self.unreleased = []       # ids the OS refused to give back, last teardown

    # -- registration --------------------------------------------------------
    def register(self, say=None):
        """Take every hotkey, or take none and raise. No partial state survives ANY path.

        The `atexit` hook goes on BEFORE the first key, not after the last: a
        `RegisterHotKey` that RAISES used to leave keys held with no net whatever, because
        the only cleanup was reached by a falsy return and the hook was installed past it.
        """
        import atexit
        if self._atexit is None:
            self._atexit = self.unregister
            atexit.register(self._atexit)
        try:
            for n, (vk, action) in enumerate(self.bindings):
                hk_id = self.base_id + n
                if not self._register_hotkey(None, hk_id, self.mods, vk):
                    err = None
                    try:
                        err = self._last_error()
                    except Exception:        # noqa: BLE001 -- a fake need not have one
                        pass
                    why = (" -- something already holds it: another marks.py, or an app "
                           "that binds the F-keys globally. Close it and re-run."
                           if err == ERROR_HOTKEY_ALREADY_REGISTERED else "")
                    raise HotkeyRefused(
                        f"RegisterHotKey failed for {_vk_name(vk)} ({action})"
                        f"{'' if err is None else f' [WinError {err}]'}{why}\n"
                        f"REFUSING rather than falling back to GetAsyncKeyState: a poll "
                        f"does not swallow the key, so every mark would ALSO fire "
                        f"whatever Guild Wars binds to that F-key and change the traffic "
                        f"the mark exists to describe. A silently perturbing instrument "
                        f"is worse than none.")
                self._taken.append(hk_id)
                self.ids[hk_id] = action
        except BaseException:
            # EVERY failure path, not just the falsy return: a ctypes error, a Ctrl-C
            # between two calls, anything. BaseException on purpose -- KeyboardInterrupt
            # is not an Exception and it is the one an operator actually produces.
            self.unregister(say=say)
            raise
        return self

    def unregister(self, say=None):
        """Release every hotkey taken. Safe in any state, any number of times.

        Returns the ids the OS REFUSED to release, and records them on `self.unreleased`.
        The old version discarded both the return value and the error, so a genuine
        refusal was indistinguishable from a release -- and the consequence is not
        abstract: after a leak, the module's own next refusal reads "something already
        holds it: another marks.py, or an app that binds the F-keys globally", and the app
        holding the key is this process.
        """
        import atexit
        failed = []
        while self._taken:
            hk_id = self._taken[-1]          # NOT popped yet, and that is the fix
            ok, err = 0, None
            try:
                ok = self._unregister_hotkey(None, hk_id)
            except Exception as exc:         # noqa: BLE001 -- teardown never raises
                err = exc
            # A BaseException (Ctrl-C) leaves `hk_id` ON `_taken` and propagates, so the
            # atexit hook's later call still tries it. Popping first made that unreachable.
            self._taken.pop()
            self.ids.pop(hk_id, None)
            if not ok:
                failed.append(hk_id)
                if say:
                    say(f"  [WARNING] UnregisterHotKey({hk_id}) failed"
                        f"{'' if err is None else f' ({err})'} -- that hotkey may still "
                        f"be held by this process, so the key is still swallowed away "
                        f"from the client. Ending this process releases it: Windows "
                        f"drops a thread's hotkeys when the thread exits.")
        if self._atexit is not None:
            try:
                atexit.unregister(self._atexit)
            except Exception:                # noqa: BLE001
                pass
            self._atexit = None
        self.unreleased = failed
        return failed

    def __enter__(self):
        return self.register()

    def __exit__(self, exc_type, exc, tb):
        self.unregister()
        return False

    # -- the pump ------------------------------------------------------------
    def poll(self, timeout_ms=200):
        """Actions for every hotkey press since the last call, oldest first.

        Returns `[]` on a quiet pass and `["advance", ...]` otherwise -- one entry per
        PRESS, never per poll: the presses are WM_HOTKEY messages sitting in this thread's
        queue and `PM_REMOVE` takes each exactly once. Calling this a hundred times after
        one press yields one action and then ninety-nine empty lists.

        `WM_QUIT` is reported as the pseudo-action `"quit"` so a caller can end on it
        (`PostThreadMessage` from elsewhere in the process); anything else in the queue is
        discarded, which is the whole of it for a thread that owns no window.
        """
        out = self._drain()
        if out:
            return out
        self._wait_for_message(0, None, False, int(timeout_ms), QS_ALLINPUT)
        return self._drain()

    def _drain(self):
        out = []
        msg = MSG()
        # Peek the WHOLE range, not just WM_HOTKEY: a filtered peek leaves everything else
        # in the queue, and MsgWaitForMultipleObjects would then wake instantly forever on
        # a message nobody ever removes -- a busy loop that looks like a working one.
        while self._peek_message(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            if msg.message == WM_HOTKEY:
                action = self.ids.get(int(msg.wParam))
                if action:
                    out.append(action)
            elif msg.message == WM_QUIT:
                out.append("quit")
        return out


def _vk_name(vk):
    return {VK_F9: "VK_F9", VK_F10: "VK_F10", VK_F11: "VK_F11"}.get(vk, f"VK 0x{vk:02X}")


# --------------------------------------------------------------------- run ----
def run(marker, hotkeys, alive=None, stop_file=None, seconds=0, timeout_ms=200,
        clock=time.monotonic, say=print):
    """Pump hotkeys into `marker` until the session ends. Returns why it ended.

    THE SHUTDOWN, WHICH IS THE HALF THE SPEC LEAVES OPEN. `GetMessage` blocks with no
    timeout and the operator ends a run by CLOSING THE CLIENT, not by alt-tabbing to this
    console -- the same reason `livesession._hold` grew a STOP file. So the wait here is
    bounded (`MsgWaitForMultipleObjects`, 200 ms) and every pass re-tests four independent
    endings, none of which needs console focus:

      * `alive()` says the subject process is gone -- the ordinary ending. Injected as a
        callable rather than read from a pid here, so the test drives it deterministically
        and this file needs no kernel32.
      * a STOP file appears -- the same convention livesession prints to the operator, so
        one `echo. > STOP` ends both.
      * the `seconds` ceiling, if one was set.
      * Ctrl-C, if this console does happen to have focus, and WM_QUIT if something in the
        process posts one.

    Whatever the ending, the `finally` releases the hotkeys and closes the marks file. A
    press past the last step is caught, counted and announced; it does NOT end the run,
    because an operator whose finger slips must not lose the rest of the session's marks
    while they are looking at the game.
    """
    deadline = clock() + seconds if seconds else None
    why = "unknown"
    try:
        while True:
            if deadline is not None and clock() > deadline:
                why = "ceiling"
                break
            if alive is not None and not alive():
                why = "subject exited"
                break
            if stop_file and os.path.exists(stop_file):
                why = "STOP file"
                break
            for action in hotkeys.poll(timeout_ms):
                if action == "quit":
                    why = "WM_QUIT"
                    return why
                try:
                    rec = {ADVANCE: marker.advance, REPEAT: marker.repeat,
                           NOTE: marker.note}[action]()
                except (PlanExhausted, NothingToRepeat) as exc:
                    say(f"  [refused] {action}: {exc}")
                    continue
                say(f"  mark {rec['seq']}: {rec['mark']}"
                    + (f" step {rec['step']} -- {rec['text']}" if rec["text"] else "")
                    + (f" (note {rec['note_ordinal']})" if "note_ordinal" in rec else ""))
    except KeyboardInterrupt:
        why = "Ctrl-C"
    finally:
        # `say` is passed so a hotkey the OS refused to give back is ANNOUNCED. Silently
        # discarding that answer is what let a leaked registration keep swallowing the
        # operator's F9 while this module's own next refusal blamed "another app".
        hotkeys.unregister(say=say)
        marker.close(why)
    return why


def process_alive(pid):
    """A callable answering "is this pid still running", or None for pid 0/None.

    Windows-only and deliberately outside `run`: keeping the liveness probe here means the
    loop takes a plain callable and `test_marks.py` never needs kernel32. `os.kill(pid, 0)`
    is NOT usable -- on Windows CPython implements it with TerminateProcess, so the
    "harmless" liveness idiom from POSIX would kill the client mid-session.
    """
    if not pid:
        return None
    if not hasattr(ctypes, "windll"):
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0x0
    kernel32.OpenProcess.restype = ctypes.c_void_p

    def alive():
        h = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
        if not h:
            return False
        try:
            return kernel32.WaitForSingleObject(ctypes.c_void_p(h), 0) != WAIT_OBJECT_0
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(h))
    return alive


# ------------------------------------------------------------------ reading ----
TOLERANCE = 0.250


def read(path):
    """(meta, [mark records]) for a marks file, in file order.

    Refuses a file carrying the DRIVER's mark shape as well as ours. Both channels use
    `"kind": "mark"` and BOTH now carry `wire_t`, so the discriminant is the rest of the
    shape: `n`/`label`/`wall`/`perf` against `seq`/`mark`/`step`/`text`/`t_perf`/`t_wall`.
    A merged file would otherwise read as a run with holes in it rather than as an error.
    Naming the collision is the only way it stays visible if the two are ever pointed at
    one file.
    """
    if not os.path.isfile(path):
        raise BindError(f"no marks file at {path!r}")
    meta, marks, foreign = None, [], 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(rec, dict):
                continue
            if rec.get("kind") == "marks_meta":
                meta = meta or rec
            elif rec.get("kind") == "mark":
                if "mark" in rec and "t_perf" in rec:
                    marks.append(rec)
                else:
                    foreign += 1
    if foreign:
        raise BindError(
            f"{os.path.basename(path)} holds {foreign} record(s) in livesession.py's own "
            f"mark shape as well as {len(marks)} in this module's. Two writers are "
            f"sharing one file: the driver opens its marks file in 'w' mode and holds the "
            f"handle, so its next write overwrites whatever was appended after it. "
            f"Separate them -- this module defaults to {PLAN_MARKS_NAME!r}.")
    if meta is None:
        raise BindError(
            f"{os.path.basename(path)} has no marks_meta line, so its plan cannot be "
            f"identified and its own epoch is unknown.")
    return meta, marks


def wire_epoch(wire_path):
    """(t0_perf, t0_wall) from a capture's `wire_meta`. Refuses what cannot be bound.

    THE TWO REFUSALS HERE ARE THE SAME DEFECT FROM TWO SIDES. `20260807T124912` is the
    capture that started LATE -- the sniff opened after the thing it was meant to record,
    so the artifact looks complete and is missing its beginning. A capture with no
    `wire_meta` at all is that failure at its limit (the sniff never opened), and a mark
    stamped before `t0_perf` is that failure seen from the marks side: the operator was
    already marking while the capture had not begun. Both are refused by name rather than
    bound to a t=0 that means nothing.
    """
    if not os.path.isfile(wire_path):
        raise BindError(
            f"no {os.path.basename(wire_path)} at {wire_path!r}: there is no wire clock "
            f"to put these marks on.")
    meta = None
    with open(wire_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"wire_meta"' not in line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(rec, dict) and rec.get("kind") == "wire_meta":
                meta = rec
                break
    if meta is None:
        raise BindError(
            f"{os.path.basename(wire_path)} has no wire_meta line. open_capture writes it "
            f"immediately after WinDivertOpen succeeds, so its absence means the sniff "
            f"never opened -- the capture-started-late defect (20260807T124912) at its "
            f"limit. Nothing in this file can be placed on a clock.")
    t0_perf, t0_wall = meta.get("t0_perf"), meta.get("t0_wall")
    if not isinstance(t0_perf, (int, float)) or not isinstance(t0_wall, (int, float)):
        # THE OLD MESSAGE ASSERTED A FACT THE VAULT CONTRADICTS. It said "a capture
        # written before 2026-08-13 has only t0_wall", and measured, every one of the ten
        # real wire.jsonl in the vault carries NEITHER: the keys are client, kind, pid,
        # server, server_ports. `t0_wall` landed 2026-08-11 and the newest live capture is
        # 2026-08-10, so the whole existing corpus is one vintage older than the message
        # claimed. Say what was actually found instead of naming a vintage.
        have = sorted(k for k in ("t0_perf", "t0_wall") if isinstance(
            meta.get(k), (int, float)))
        raise BindError(
            f"{os.path.basename(wire_path)}'s wire_meta carries "
            f"t0_perf={t0_perf!r} t0_wall={t0_wall!r}; it has "
            f"{', '.join(have) if have else 'NEITHER epoch'}. Both are needed: t0_perf is "
            f"what puts a mark on wire time and t0_wall is the second witness that says "
            f"the two processes' perf_counters were comparable at all. Captures written "
            f"before 2026-08-11 carry neither and the ten in the vault today are all of "
            f"that vintage, so none of them can be bound this way -- this module's first "
            f"real input is the NEXT live run.")
    return float(t0_perf), float(t0_wall)


def last_wire_t(wire_path):
    """The `t` of the last wire record in a capture, or None if there is none yet.

    A DELIBERATE DUPLICATE of `wirecapture.last_wire_t`, and the reason is the same one
    `driver_marks_name` pins its own literal for: `wirecapture` imports `tcptable`, which
    binds `ctypes.wintypes` at module scope and is therefore unimportable off Windows,
    while this module has to run everywhere so `test_marks.py` can measure it. Eight lines
    of file walk is a cheaper price than an import that fails on half the platforms and
    takes the third channel down with it.

    Reads the file rather than sharing state with the sniffer, because the sniffer is a
    SUBPROCESS -- there is no shared state to have. Cheap at human cadence: a mark happens
    once per plan step, not per packet.
    """
    t = None
    try:
        with open(wire_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"wire"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(rec, dict) and rec.get("kind") == "wire" and "t" in rec:
                    t = rec["t"]
    except OSError:
        return None
    return t


Skew = collections.namedtuple("Skew", "seq mark dperf dwall skew")


def drift(wire_path, marks_path, marks=None):
    """[Skew(...)] per mark: its two deltas from the capture's epoch and their difference.

    The same computation `bind()` rules on, with no verdict, so a report can print the
    numbers without `bind` having to grow a way to ignore them.
    """
    t0_perf, t0_wall = wire_epoch(wire_path)
    if marks is None:
        _meta, marks = read(marks_path)
    rows = []
    for m in marks:
        tp, tw = m.get("t_perf"), m.get("t_wall")
        if not isinstance(tp, (int, float)) or not isinstance(tw, (int, float)):
            raise BindError(f"mark {m.get('seq')} is missing a clock "
                            f"(t_perf={tp!r}, t_wall={tw!r})")
        dp, dw = float(tp) - t0_perf, float(tw) - t0_wall
        rows.append(Skew(m.get("seq"), m.get("mark"), dp, dw, dp - dw))
    return rows


def worst_skew(rows):
    """The largest |skew| in a drift table, or None for an EMPTY one.

    None rather than 0.0, and this three-line function exists for that one word. A marks
    file with a valid header and no marks -- the operator never pressed a key, or the
    marker died after `open()` -- made the CLI print "worst |dperf - dwall| = 0.0 ms
    against a 250 ms tolerance", which is a run that measured NOTHING reporting the best
    possible measurement, in the operator's only readout. That is precisely the failure
    `toolkit/checks.py` exists to prevent, reproduced inside a tool.
    """
    return max((abs(r.skew) for r in rows), default=None)


def drift_shape(rows, tolerance=TOLERANCE):
    """(shape, sentence) for a drift table: OFFSET, RATE, STEP or SCATTER.

    THE VOCABULARY USED TO HAVE TWO WORDS AND THE COMMONEST REAL CAUSE IS THE THIRD.
    Fed a single +0.5 s wall-clock step at t=70 of a 146 s session -- an NTP correction or
    a resume, with the perf axis untouched and every perf-derived time CORRECT -- the old
    message answered with both of its hypotheses and was wrong about both: "11 of 20 marks
    disagree, so this is a stamping fault at those marks" (it was ONE clock event) and
    "the skew moves -3.6 ms per second, so it is a RATE (a drifting clock)" (a step
    averaged over a session looks exactly like a rate).

    So the skew is differenced PAIRWISE here, and the cumulative number keeps deciding.
    Those are different jobs and neither can do the other's: a constant OFFSET -- the
    launch-gap hypothesis, the one thing this check has real power over -- is invisible
    pairwise, and a STEP is invisible cumulatively because every mark after it inherits
    the whole displacement.
    """
    if not rows:
        return "NONE", "there are no marks to have a shape."
    if len(rows) == 1:
        return "SINGLE", ("one mark, so there is no shape to read -- a single "
                          "disagreement cannot separate a bad stamp from a bad clock.")
    steps = [(b.skew - a.skew, a, b) for a, b in zip(rows, rows[1:])]
    big = [s for s in steps if abs(s[0]) > tolerance]
    total = rows[-1].skew - rows[0].skew
    largest = max(steps, key=lambda s: abs(s[0]))
    # A STEP IS "ONE DIFFERENCE ACCOUNTS FOR THE WHOLE CHANGE", which is the definition
    # rather than a count: a drifting clock also produces pairwise differences above the
    # tolerance, so "exactly one is big" would file a fast drift as a step.
    if big and abs(total) > 0 and abs(largest[0]) >= 0.9 * abs(total):
        d, a, b = largest
        return "STEP", (
            f"the skew is FLAT on both sides of one boundary and jumps {d:+.3f}s between "
            f"mark {a.seq} (t={a.dperf:.3f}s) and mark {b.seq} (t={b.dperf:.3f}s), which "
            f"is {abs(d) / abs(total) * 100:.0f}% of the whole session's change. That is "
            f"ONE clock DISCONTINUITY -- an NTP correction, a resume, a manual change -- "
            f"not a drift and not a series of bad stamps. Every mark after that boundary "
            f"inherits the whole displacement, which is why the COUNT of disagreeing "
            f"marks is not the number of faults.")
    span = rows[-1].dwall - rows[0].dwall
    per = total / span if span > 0 else 0.0
    if len(big) > 1 and abs(per) <= 1e-4:
        return "SCATTER", (
            f"{len(big)} separate jumps in the skew that cancel out across the session, "
            f"so these are individual stamping faults rather than one clock event.")
    if abs(per) > 1e-4:
        return "RATE", (
            f"the skew moves {per * 1000:+.1f} ms per second of session with no single "
            f"jump in it, so it is a RATE (a drifting clock), not an offset.")
    return "OFFSET", (
        f"the skew is flat across the session at {rows[0].skew:+.3f}s, so it is a "
        f"constant offset rather than a drifting clock -- which is what a per-process "
        f"perf_counter epoch looks like: the two processes started {abs(rows[0].skew):.3f}"
        f"s apart and nothing has moved since.")


Mark = collections.namedtuple("Mark", "t mark step text")


def bind(wire_path, marks_path, plan=None, notes=None, tolerance=TOLERANCE):
    """[Mark(t, mark, step, text)] on WIRE time, or raise naming what cannot be bound.

    `t = t_perf - t0_perf`, the same origin every `"t"` in `wire.jsonl` is measured from,
    so a mark and a TCP segment are directly comparable numbers. The rows are 4-tuples by
    construction (`Mark` is a namedtuple), so `t, mark, step, text = rows[0]` unpacks and
    `rows[0] == (1.5, "advance", 0, "...")` compares equal to a plain tuple.

    `plan` is the plan file's path (or an already-loaded [Step]) and is CHECKED, not used:
    its sha256 must equal the one `marks_meta` recorded, because the plan is what the
    marks mean and a plan edited after the run is a prediction written to fit its result.
    Omitting it skips only that check -- the text is already in the records.

    `notes` is `{ordinal: text}` or a path to a notes file; it fills in the text of `note`
    marks, which by design carry none. See the header for why the annotation is not an
    edit to the plan.

    RAISES `ClockDrift` if any mark's two deltas disagree by more than `tolerance`, after
    examining ALL of them -- the header argues why that is a raise and not a flag, and why
    the message reports the shape rather than the first offender.
    """
    meta, marks = read(marks_path)
    t0_perf, t0_wall = wire_epoch(wire_path)

    if plan is not None:
        steps = plan if isinstance(plan, (list, tuple)) else load_plan(plan)
        if not isinstance(plan, (list, tuple)):
            got = plan_sha256(plan)
            want = meta.get("plan_sha256")
            if got != want:
                raise PlanError(
                    f"{os.path.basename(str(plan))} is not the plan this run was marked "
                    f"against: the file hashes {got[:16]}... and marks_meta recorded "
                    f"{str(want)[:16]}.... The plan is the PRE-REGISTERED prediction, so "
                    f"an edited one cannot be used to read the marks -- that is a "
                    f"prediction rewritten to agree with its result. Recover the original "
                    f"(git, or the capture's manifest) or bind without --plan.")
        if len(steps) != meta.get("steps"):
            raise PlanError(
                f"the plan has {len(steps)} steps and marks_meta recorded "
                f"{meta.get('steps')}")

    if isinstance(notes, str):
        notes = load_notes(notes)
    notes = notes or {}

    early = [m for m in marks
             if isinstance(m.get("t_perf"), (int, float)) and m["t_perf"] < t0_perf]
    if early:
        first = early[0]
        raise BindError(
            f"{len(early)} of {len(marks)} mark(s) were taken BEFORE the capture's epoch "
            f"-- mark {first.get('seq')} ({first.get('mark')}) is "
            f"{t0_perf - first['t_perf']:.3f}s early. The capture started late: the "
            f"operator was already marking while the sniff had not opened, which is the "
            f"20260807T124912 defect arriving from the marks side. Those marks describe "
            f"traffic that was never recorded, so they are refused rather than clamped "
            f"to t=0.")

    rows = drift(wire_path, marks_path, marks=marks)
    bad = [r for r in rows if abs(r.skew) > tolerance]
    if bad:
        worst = max(bad, key=lambda r: abs(r.skew))
        count = ("EVERY mark disagrees, so the two processes' perf_counters may not be on "
                 "a comparable timebase at all"
                 if len(bad) == len(rows) else
                 f"{len(bad)} of {len(rows)} marks disagree")
        shape, sentence = drift_shape(rows, tolerance)
        raise ClockDrift(
            f"the marks and the capture are not on one clock: {count}, and the SHAPE is "
            f"{shape} -- {sentence} Worst is mark "
            f"{worst.seq} ({worst.mark}) -- perf says {worst.dperf:.3f}s after t0, wall "
            f"says {worst.dwall:.3f}s, a difference of {worst.skew:+.3f}s against a "
            f"{tolerance:.3f}s tolerance.\n"
            f"This is REFUSED rather than reported per row because what has failed is the "
            f"assumption under every t in the list, not just this one -- bind() sees a "
            f"DIFFERENCE and cannot know which of the two clocks moved. If the shape is "
            f"STEP the perf axis is probably fine and every t here is probably right; "
            f"binding with an explicit larger tolerance is an operator recording that "
            f"judgement, and there is no flag that makes this quiet. "
            f"t0_perf={t0_perf!r} t0_wall={t0_wall!r}.")

    # ---- THE THIRD CHANNEL, and the only one on the SEGMENT axis.
    ahead = [(m, r) for m, r in zip(marks, rows)
             if isinstance(m.get("wire_t"), (int, float))
             and m["wire_t"] > r.dperf + tolerance]
    if ahead:
        m, r = ahead[0]
        raise BindError(
            f"{len(ahead)} of {len(marks)} mark(s) report having SEEN a segment stamped "
            f"later than the mark itself -- mark {m.get('seq')} binds to t={r.dperf:.3f}s "
            f"and its wire_t is {m['wire_t']:.3f}s, {m['wire_t'] - r.dperf:+.3f}s ahead. "
            f"A mark cannot see the future, so the capture's PUBLISHED epoch is not the "
            f"epoch its segments were stamped from and every t computed from it is off by "
            f"about that much. Both clock channels will look perfect here, because they "
            f"are sampled adjacently in one process and only ever measure the OS-wide "
            f"(QPC - system time) offset against itself -- this is the witness that is "
            f"actually on the segments' own axis.")
    if [m for m in marks if isinstance(m.get("wire_t"), (int, float))]:
        seen = [m["wire_t"] for m in marks if isinstance(m.get("wire_t"), (int, float))]
        if any(b < a for a, b in zip(seen, seen[1:])):
            raise BindError(
                f"the marks' wire_t goes BACKWARDS ({seen}). The capture's last recorded "
                f"`t` cannot decrease while a session runs, so the file was replaced or "
                f"truncated under the marker and these marks are not all describing the "
                f"same recording.")

    # ---- the capture-started-late defect from the END, which is a different refusal.
    t_last = last_wire_t(wire_path)
    if t_last is not None and rows and all(r.dperf > t_last for r in rows):
        raise BindError(
            f"all {len(rows)} mark(s) fall AFTER the capture's last recorded segment "
            f"(t={t_last:.3f}s; the earliest mark is at t={min(r.dperf for r in rows):.3f}"
            f"s). The marks and the recording do not overlap at all, so every label here "
            f"is on traffic that was never captured. The sniffer is spawned with a hard "
            f"`--seconds` ceiling and `livesession` prints 'THE OFF-WIRE CAPTURE DIED' "
            f"and deliberately KEEPS THE SESSION GOING, while this process watches the "
            f"CLIENT and knows nothing about the sniffer -- so this is reachable and it "
            f"is the 20260807T124912 defect arriving from the other end. A partial "
            f"overlap is reported by `unbacked()` rather than refused, because 'the "
            f"network went quiet' and 'the sniff stopped' are not separable from the "
            f"artifact and this module does not guess between them.")

    out = []
    for m, r in zip(marks, rows):
        text = m.get("text") or ""
        if m.get("mark") == NOTE and m.get("note_ordinal") in notes:
            text = notes[m["note_ordinal"]]
        out.append(Mark(round(r.dperf, 6), m.get("mark"), m.get("step"), text))
    return out


def unbacked(wire_path, rows):
    """The bound marks that fall after the capture's last recorded segment.

    A REPORT, not a refusal, and the reason is that a refusal here would need a threshold
    nobody has measured. A mark seconds after the last packet is ordinary (the operator
    closed the client and the network went quiet); a mark eight minutes after it means the
    sniffer died and every label since has been on nothing. Those two are not separable
    from the artifact, so this module names the fact and refuses to guess -- `bind()`
    refuses only the case the artifact CAN prove, which is zero overlap.

    Returns `([Mark], t_last)`. `t_last` is None when the capture holds no segment at all,
    in which case every mark is unbacked and nothing here is news.
    """
    t_last = last_wire_t(wire_path)
    if t_last is None:
        return list(rows), None
    return [r for r in rows if r.t > t_last], t_last


def on_tape(info, marks):
    """`bind()`'s rows re-based onto ONE tape's clock, from `tape.load_tape`'s info.

    A tape event's time is relative to that connection's first s2c segment, not to the
    capture -- `load_tape` computed that `t0` and threw it away until this module needed
    it. So a mark in wire time and an event in tape time were two numbers that looked
    comparable and were not, off by however long the client took to reach that connection.
    Subtracting `info["t0"]` is the whole join.

    A NEGATIVE result is legitimate and is returned, not refused: a mark taken during the
    handshake, or on an earlier connection, genuinely precedes this tape's first server
    byte. Refusing it would throw away the very marks that describe the instance load.
    """
    if not isinstance(info, dict) or "t0" not in info:
        raise BindError(
            "this tape info carries no 't0'. tape.load_tape exposes it as of 2026-08-13; "
            "before that it was computed and discarded, and a mark in wire time cannot be "
            "joined to a tape without it.")
    t0 = info["t0"]
    if t0 is None:
        raise BindError(
            f"tape {info.get('connection')!r} has no events, so it has no first s2c "
            f"segment to measure from and no clock to put a mark on.")
    return [Mark(round(m.t - t0, 6), m.mark, m.step, m.text) for m in marks]


# --------------------------------------------------------------------- CLI ----
def _resolve(capture_dir, name, explicit=None):
    if explicit:
        return explicit
    if not capture_dir:
        raise MarksError(f"--capture <dir> (or an explicit path) is needed to find {name}")
    return os.path.join(capture_dir, name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", default=None,
                    help="the pre-registered plan file, kind<TAB>text per line")
    ap.add_argument("--capture", default=None,
                    help="the capture directory holding wire.jsonl; marks are written "
                         f"to {PLAN_MARKS_NAME} inside it")
    ap.add_argument("--out", default=None,
                    help=f"marks file to write (default <capture>/{PLAN_MARKS_NAME}; "
                         f"{DRIVER_MARKS_NAME} is refused -- livesession.py owns it)")
    ap.add_argument("--wire", default=None, help=f"explicit path to {WIRE_NAME}")
    ap.add_argument("--notes", default=None,
                    help="<ordinal><TAB><text> per line, attached to note marks by --bind")
    ap.add_argument("--pid", type=int, default=0,
                    help="the client process; the run ends when it exits")
    ap.add_argument("--stop-file", default=None,
                    help="end when this file appears (default <capture>/STOP)")
    ap.add_argument("--seconds", type=int, default=0, help="ceiling (0 = until stopped)")
    ap.add_argument("--check-plan", default=None,
                    help="print a plan's sha256 and its steps, and exit. Pre-flight: run "
                         "this BEFORE the client launches and record the hash")
    ap.add_argument("--bind", action="store_true",
                    help="read the marks back on wire time and exit")
    ap.add_argument("--tape-t0", type=float, default=None,
                    help="with --bind, re-base onto a tape whose load_tape info['t0'] is "
                         "this (see marks.on_tape)")
    a = ap.parse_args(argv)

    try:
        if a.check_plan:
            steps = load_plan(a.check_plan)
            print(f"{os.path.basename(a.check_plan)}: {len(steps)} steps")
            print(f"sha256 {plan_sha256(a.check_plan)}")
            for s in steps:
                print(f"  {s.index:3d}  {s.kind:<16} {s.text}")
            return 0

        if a.bind:
            wire = _resolve(a.capture, WIRE_NAME, a.wire)
            mpath = _resolve(a.capture, PLAN_MARKS_NAME, a.out)
            rows = bind(wire, mpath, plan=a.plan, notes=a.notes)
            # A RUN THAT MEASURED NOTHING FAILED, and this readout used to say the
            # opposite: with no marks at all it printed "worst |dperf - dwall| = 0.0 ms",
            # the best possible measurement, for a session in which the operator pressed
            # nothing or the marker died after open(). checks.py's rule, inside a tool.
            if not rows:
                raise MarksError(
                    f"{os.path.basename(mpath)} carries a valid header and ZERO marks, so "
                    f"there is nothing to bind and the two-clock agreement is UNMEASURED "
                    f"-- not 0.0 ms. Read its marks_end record: 'why' says whether the "
                    f"operator stopped marking or the marker died.")
            late, t_last = unbacked(wire, rows)
            if a.tape_t0 is not None:
                rows = on_tape({"t0": a.tape_t0, "connection": "--tape-t0"}, rows)
            print(f"{len(rows)} mark(s) on "
                  f"{'tape' if a.tape_t0 is not None else 'wire'} time")
            for r in rows:
                step = "  -" if r.step is None else f"{r.step:3d}"
                print(f"  {r.t:9.3f}  {r.mark:<8} {step}  {r.text}")
            worst = worst_skew(drift(wire, mpath))
            print(f"two-clock agreement: worst |dperf - dwall| = "
                  f"{'UNMEASURED' if worst is None else f'{worst * 1000:.1f} ms'} "
                  f"against a {TOLERANCE * 1000:.0f} ms tolerance")
            if late:
                print(f"\n  WARNING: {len(late)} of {len(rows)} mark(s) fall after the "
                      f"capture's last recorded segment"
                      + ("" if t_last is None else f" (t={t_last:.3f}s)") + ".\n"
                      f"  Either the network went quiet or THE SNIFF STOPPED -- the "
                      f"sniffer has a --seconds ceiling and livesession keeps the session\n"
                      f"  going when it dies. Those marks may be labels on traffic that "
                      f"was never recorded; check the driver's log before using them.")
            return 0

        # -- the run --------------------------------------------------------
        if not a.capture and not a.out:
            raise MarksError("--capture <dir> names where the marks go")
        marker = open_marks(a.capture, a.plan, out=a.out, pid=a.pid or None)
        stop = a.stop_file or (os.path.join(a.capture, "STOP") if a.capture else None)
        print(f"marking {len(marker.steps)} steps into {marker.path}")
        print(f"  plan {marker.plan_name} sha256 {marker.plan_sha[:16]}...")
        print("  F9  advance -- emit the next plan step")
        print("  F10 repeat  -- re-emit the current step")
        print("  F11 note    -- an unlabelled moment; text is attached afterwards")
        print("  The keys are SWALLOWED, so they never reach the client. Nothing is sent.")
        print(f"  Ends when the client exits, when {stop} appears, or on Ctrl-C.")
        print(f"  wire clock read from {marker.wire_path or '(none -- no --capture)'}\n")
        try:
            with Hotkeys() as hk:
                why = run(marker, hk, alive=process_alive(a.pid), stop_file=stop,
                          seconds=a.seconds)
        finally:
            marker.close("aborted")
        print(f"\nended: {why} -- {marker.seq} mark(s) to {marker.path}")
        return 0
    except MarksError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
