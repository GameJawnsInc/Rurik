"""The pre-registration seal: hashing the plan BEFORE the run, and comparing two seals after.

Split out of `toolkit/harness/livesession.py`, where all sixteen names below are still
re-exported at the site they used to occupy. `livesession.seal_plan`,
`livesession.plan_manifest`, `livesession.write_seal_file` and the rest keep working:
`toolkit/harness/test_livesession.py` reads twelve of them as `ls.<name>` across sections
5b-5e, and `livesession.run()` and `livesession.reassemble()` call `seal_plan`,
`write_seal_file`, `marks_instructions`, `plan_manifest` and `compare_plan_seals` as bare
globals. That last part is load-bearing rather than incidental: §5g patches
`mod.seal_plan` and `mod.write_seal_file` onto the livesession module object and then runs
`run()` to see the order they fire in, which works because the re-export binds those names
in `livesession`'s own namespace and `run()` resolves them there.

WHY THIS IS ITS OWN MODULE. Everything here is a pure read of the operator's plan file and
of a capture directory: `seal_plan` hashes and parses, `plan_manifest` and
`write_seal_file` render, and `seal_records`/`recorded_seal`/`internal_seal_conflict`/
`compare_plan_seals` read artifacts back off disk. Nothing launches, sniffs, taps or
touches the network, and the only repo-local code it needs is `marks.py` -- the format's
one parser -- and the refusal class. The live driver it came out of imports the
packet-capture backend, the codec, ARC4, `accounts`, `origin` and `vaultpath` to do its
job; none of that is the seal's.

ONE `sys.path` insert, not six. `HERE` reaches `marks` and `liveerror`, which are the only
two repo-local modules named below. `HERE` is also a value this module USES rather than
merely a path fixture: `marks_instructions` spells the marker command as
`python "<HERE>/marks.py"`, and because this file sits in the same directory as
`livesession.py` that string is byte-identical to the one the driver printed before the
split. The toolkit root, `clientpatch`, `authsrv`, `schema` and `mapdata` are the driver's
and this file copies none of them -- though MEASURED 2026-09-11, and stated because the
first draft of this paragraph implied otherwise: `marks.py` does its own
`sys.path.insert(0, os.path.dirname(HERE))` at import time (`marks.py:215`), so after
`import planseal` the toolkit ROOT is on the path anyway. The claim this module can make
is the one that was measured on the modules rather than on the path -- importing it loads
none of `livesession`, `wirecapture`, `accounts`, `origin`, `vaultpath`, `codec`,
`gwcrypto` or `wiresplit` -- and `clientpatch`, `authsrv`, `schema` and `mapdata` stay off
the path entirely. This module does not import its origin (R4): the live driver runs as
`python livesession.py`, so importing it back would load a second copy whose flags `main()`
never set.

THE REFERENTS OF FIVE MOVED COMMENTS STAY IN `livesession.py`. The comments below travel
verbatim, so the pointers are written down here instead of reworded there:

  * `seal_plan`'s docstring -- "what the rest of this module's pre-launch gates are, so
    `main()`'s exit path and `--confirm`/`--mode` all behave the same way" -- is about
    `livesession.preflight` and `livesession.main`, which stay.
  * `write_seal_file`'s docstring names `_install_sigint` (the Ctrl-C that cost a session's
    manifest) and `KeyRing._persist` ("one artifact over"). Both are `livesession`'s.
  * the same docstring's closing paragraph -- "the CALL SITE in `run()` is what makes any
    of this true" -- is `livesession.run()`, and the syntax-tree and runtime checks that
    pin it read `livesession.py`'s source, not this file's.
  * `internal_seal_conflict`'s docstring cites the sabotage `"plan_sha256":
    sha256(seal.path)` "using this module's own file hasher" -- that hasher is
    `livesession.sha256`, called three times in `run()`'s manifest literal.
  * `compare_plan_seals`'s docstring -- "`run()` records the verdict at manifest time and
    `reassemble()` recomputes and rewrites it" -- names two functions that stay, and its
    `marks.bind()` paragraph is about `marks.py`.

`LiveError` is imported rather than redefined, and after the refusal split there is exactly
one such class object in the process, so `test_livesession.py`'s `LiveErrorType = ls.LiveError`
still catches everything `seal_plan` raises.
"""
import collections
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import marks  # noqa: E402
from liveerror import LiveError  # noqa: E402


# ------------------------------------------------- the pre-registration seal --
# `path` is absolute, `sha256` is over the RAW BYTES (marks.plan_sha256's rule: a changed
# line ending is a different plan and should read as one), `steps` is the parsed step
# count and exists to be compared against `marks_meta`'s own, `sealed_utc` records WHEN --
# which is the only claim this whole object makes that the manifest could not have made
# for itself at the end of the run -- and `body` is the plan's own text, carried so the
# capture can ARCHIVE the prediction rather than only a hash of it (see write_seal_file).
PlanSeal = collections.namedtuple("PlanSeal", "path sha256 steps sealed_utc body")


def _plan_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def seal_plan(plan_path):
    """Parse and hash the operator-mark plan. Call this BEFORE anything launches.

    The parse and the hash both go through `marks.py` rather than being re-implemented
    here: two parsers for one format is how they drift, and `marks.load_plan` is the one
    that will actually read this file in the second shell. So a plan this driver accepts
    is a plan the marker can run, by construction and not by agreement.

    THE HASHED BYTES MUST BE THE PARSED BYTES, and the first version of this function did
    not guarantee that. It called `marks.load_plan(path)` and then `marks.plan_sha256(path)`
    -- two independent reads with a window between them -- and adversarial review 2026-08-13
    drove a rewrite into that window: `steps` came from read #1 and `sha256` from read #2,
    so the manifest recorded a hash of bytes that were never parsed and never passed a
    refusal, beside a step count describing a different file. The consequence was worse than
    the window: `compare_plan_seals` would then hit its step-skew branch and report "the two
    parsers disagree, not the file moved", which is a confident WRONG diagnosis.
    The atomic fix -- read once, hash that buffer, parse that buffer -- is not available
    without a second parser, because `marks.load_plan` takes a PATH and owns the format.
    So the seal buys atomicity with a RE-HASH instead: hash, parse, hash again, and refuse
    if the two hashes differ. What that certifies is exact -- these bytes were on disk both
    before and after the parse -- and it is checkable, which "there is a small window" is
    not.

    Every refusal is re-raised as a `LiveError`, which is what the rest of this module's
    pre-launch gates are, so `main()`'s exit path and `--confirm`/`--mode` all behave the
    same way. `marks.MarksError` is deliberately an `Exception` rather than a `SystemExit`
    over there (see its header); here it must be a refusal that stops the run, and the
    translation is this function's job rather than the caller's.

    THE `except` CLAUSE USED TO NAME ONLY `marks.MarksError`, and two whole classes of
    unreadable plan escaped it as bare tracebacks with no mention of `--plan`: a file saved
    as UTF-16 or cp1252 by a human's text editor (`marks.load_plan` opens `encoding="utf-8"`
    and wraps nothing, so a smart quote raises `UnicodeDecodeError`), and a file that is
    locked or on a network path that drops (`PermissionError`/`OSError` -- and note the
    asymmetry inside marks.py, where `plan_sha256` DOES wrap `OSError` into `PlanError` and
    `load_plan` does not, so which of the two read first decided whether the operator got a
    refusal or a traceback). Both land before the launch, so neither ever cost a session --
    this is the refusal contract breaking, not the seal. The encoding case gets its own
    message because the remedy the generic one offers (`--check-plan`) reads the file with
    the same loader and fails on the same bytes.
    """
    try:
        if not plan_path or not os.path.isfile(plan_path):
            # Delegate these two to marks.py, whose messages are the right ones: "no plan
            # file. An unlabelled run must not be reachable by accident" is the exact
            # sentence for the `--plan ""` an unset shell variable produces.
            marks.load_plan(plan_path)
        raw = _plan_bytes(plan_path)
    except (marks.MarksError, OSError) as exc:
        raise LiveError(_plan_refusal(plan_path, exc)) from exc
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LiveError(
            f"--plan {plan_path!r} is not UTF-8 text: {exc}\n"
            f"  This is what a text editor's \"Unicode\" (UTF-16) save looks like, or a\n"
            f"  smart quote pasted in as cp1252. The marker reads it as UTF-8 too, so\n"
            f"  --check-plan would fail on the same bytes: re-save the file as UTF-8.\n"
            f"  Nothing has launched -- this costs a re-save, not a session.") from exc
    sha = hashlib.sha256(raw).hexdigest()
    try:
        steps = marks.load_plan(plan_path)        # empty / malformed refuse here
        again = hashlib.sha256(_plan_bytes(plan_path)).hexdigest()
    except (marks.MarksError, OSError) as exc:
        raise LiveError(_plan_refusal(plan_path, exc)) from exc
    if again != sha:
        raise LiveError(
            f"--plan {plan_path!r} CHANGED WHILE IT WAS BEING SEALED: {sha} before the\n"
            f"  parse and {again} after it. The seal would certify bytes that were never\n"
            f"  parsed. Close whatever is writing the file and re-run -- nothing has\n"
            f"  launched.")
    return PlanSeal(os.path.abspath(plan_path), sha, len(steps),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), body)


def _plan_refusal(plan_path, exc):
    return (f"--plan {plan_path!r} is refused: {exc}\n"
            f"  The plan is the PRE-REGISTERED prediction and it is read BEFORE the client\n"
            f"  launches, so this costs you nothing but a retype. Check it first with:\n"
            f"      python toolkit/harness/marks.py --check-plan \"{plan_path}\"")


def plan_manifest(seal):
    """The manifest's plan block, for a seal or for the explicit absence of one.

    THE ABSENT CASE WRITES THE KEYS, and that is the design rather than tidiness. A
    consumer reading a manifest has to be able to tell three states apart: this run sealed
    a plan; this run had the flag and did not use it; this manifest was written before the
    flag existed. The first two are `plan_sealed` true/false and the third is the key not
    being there at all -- so omitting the key on an unsealed run would collapse "the
    operator chose not to" into "the tool could not", which is the same shape as
    `origin.py` refusing to let UNKNOWN and OURS share a value.

    BOTH BRANCHES CARRY THE SAME SEVEN KEYS, which they did not at first: `plan_sealed_utc`
    was on the sealed branch only and `plan_unsealed_reason` on the unsealed one only, so a
    consumer reading either by name got a `KeyError` on the other half of the corpus. That
    is the same defect this docstring's first paragraph is about, one level down -- an
    omitted key is not a null one -- so the branch-specific fields are written as `None`
    rather than left out, and `plan_sealed` stays the single discriminator.

    The path is written UNREDACTED and the reason is worth stating, because `args` two
    lines below it is not: `accounts.redact_for_file` blanks the VALUE following a secret
    FLAG (`-password`, `-email`) in an argv list, and a plan path is neither of those. The
    protection this field relies on is the same one `exe` and `gw_log` already rely on --
    `manifest.json` is not a `.jsonl`, so `scrub_captures.scrub_tree` never copies it, and
    it stays in the vault with the rest of the capture. MEASURED 2026-08-13 by adversarial
    review, which ran `scrub_tree` over a capture whose plan path was
    `C:\\Users\\<a real name>\\Documents\\gw plan.txt` and confirmed the scrubbed output held
    `SCRUB-MANIFEST.json` and `wire.jsonl` and nothing else. Worth recording rather than
    assuming next time: `plan_path` is the FIRST manifest field that is an arbitrary
    OPERATOR-chosen path from outside the vault (`exe` is under `vault/run-live`, `gw_log`
    sits beside it), and `C:\\Users\\<name>\\Documents` is exactly where a person writes a
    text file on Windows.
    """
    if seal is None:
        return {"plan_sealed": False, "plan": None, "plan_path": None,
                "plan_sha256": None, "plan_steps": None, "plan_sealed_utc": None,
                "plan_unsealed_reason":
                    "no --plan was passed: this session carries no pre-registered "
                    "operator-mark plan, so its marks (if any) are labels written after "
                    "the fact rather than a prediction stated first"}
    return {"plan_sealed": True,
            # The BASENAME under `plan`, matching what `marks_meta` records under the same
            # key, so a reader of either artifact sees the same name. It is deliberately
            # NOT what `compare_plan_seals` decides on -- an earlier comment here claimed
            # the two seals "compare field-for-field", and adversarial review 2026-08-13
            # pointed out that no comparison of the names exists or should: the seal is
            # over CONTENT, so two files with identical bytes are the same prediction
            # whatever they are called, and the manifest stores an absolute path while
            # `marks_meta` stores a basename, which is not a comparison at all. The names
            # are carried into the verdict MESSAGE instead, where a reader can use them.
            # The absolute path is beside it because that is what re-binding needs months
            # later.
            "plan": os.path.basename(seal.path), "plan_path": seal.path,
            "plan_sha256": seal.sha256, "plan_steps": seal.steps,
            "plan_sealed_utc": seal.sealed_utc, "plan_unsealed_reason": None}


def write_seal_file(outdir, seal):
    """Put the seal on disk the moment the capture directory exists. Returns the path.

    The manifest is written at the END of the run and a live run does not always reach its
    end -- a Ctrl-C inside cleanup already cost this project a whole session's manifest
    once (see `_install_sigint`). The seal is the one field whose value depends on WHEN it
    was taken, so re-deriving it afterwards is exactly what it exists to prevent: a run
    that died would leave `marks_meta`'s post-launch hash as the only surviving seal. Same
    lesson as `KeyRing._persist`, one artifact over.

    Both this file and the manifest are rendered from the SAME `PlanSeal`, so they cannot
    disagree; this one is just earlier. It is written for an UNSEALED run too, carrying
    `plan_sealed: false` -- the absence is recorded for the same reason the manifest
    records it, and a directory with no `plan_seal.json` at all then means a run whose
    driver predates the flag.

    THIS FILE, AND NOT THE MANIFEST, ARCHIVES THE PLAN'S TEXT. Until 2026-08-13 the capture
    held a hash of a file living somewhere else entirely, so an operator who deleted or
    rewrote the plan afterwards left a pre-registration that could only ever be FAILED
    against and never READ -- which is half of what a pre-registration is for. `plan_body`
    is the plan verbatim, and it is self-checking rather than decorative: it is the same
    buffer the seal was taken over, so `sha256(plan_body.encode("utf-8"))` must equal
    `plan_sha256`, and a reader who finds it does not can say which of the two is wrong.
    It goes here rather than in the manifest because the manifest is the file a census
    walks over hundreds of captures, and a multi-line body belongs beside the capture
    rather than in the index.

    Because two rounds of adversarial review both got here: the CALL SITE in `run()` is
    what makes any of this true, and deleting that one line left the whole suite green.
    The syntax-tree and runtime checks in `test_livesession.py` §5a/§5f pin it now.
    """
    path = os.path.join(outdir, "plan_seal.json")
    rec = plan_manifest(seal)
    if seal is not None:
        rec["plan_body"] = seal.body
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return path


MARKS_BANNER = "*** THIS RUN HAS NO PRE-REGISTERED PLAN ***"


def marks_instructions(seal, outdir, pid=None):
    """The console block for the second shell: the command, or the loud absence of one.

    Returns a list of lines rather than printing, so the one thing that MUST differ
    between a sealed run and an unsealed one is a value a test can assert on. That is not
    style: `test_harness.py` earned the same shape on `--enemy`, where a warning that
    fires either way is noise and a warning that fires neither way is silence, and only a
    check on both branches separates them.

    The capture directory is spelled RESOLVED and in quotes because the operator has to
    type it into a different shell while a client is coming up -- the same reason the STOP
    and MARK lines beside it are absolute.

    The unsealed branch deliberately prints NO runnable marks.py command. An operator who
    started the marker now would be writing a plan AFTER the client launched, which is a
    label and not a pre-registration, and offering the command would invite exactly that.
    """
    if seal is None:
        return [
            f"  {MARKS_BANNER}",
            "  --plan was not passed, so nothing seals what you are about to do before you",
            "  do it. The capture is still worth taking -- it is UNLABELLED, not spoiled --",
            "  and the manifest records that as \"plan_sealed\": false rather than by",
            "  leaving the key out.",
            "  Do NOT start marks.py now: a plan written after the client launched is a",
            "  label, not a prediction. Next run, write the plan first, check it with",
            "    python toolkit/harness/marks.py --check-plan <plan.txt>",
            "  and pass --plan to this driver.",
        ]
    cmd = (f"python \"{os.path.join(HERE, 'marks.py')}\" "
           f"--plan \"{seal.path}\" --capture \"{os.path.abspath(outdir)}\"")
    if pid:
        cmd += f" --pid {pid}"
    return [
        "  A SECOND SHELL, FOR THE PRE-REGISTERED MARKS (F9 advance / F10 repeat / F11 note):",
        f"    {cmd}",
        f"  plan {os.path.basename(seal.path)}: {seal.steps} step(s), "
        f"sha256 {seal.sha256[:16]}...",
        "  That hash was taken BEFORE this client launched and is already in the manifest.",
        "  marks.py prints its own on startup, from its own read -- if the two differ, the",
        "  plan changed in between and neither run is a pre-registration any more.",
        # The one failure this driver can warn about and cannot prevent: marks.py is handed
        # the capture directory that already holds plan_seal.json and does not read it, so
        # a RETYPED --plan naming a different file starts cleanly and is only contradicted
        # afterwards, in the manifest's plan_seals field. Adversarial review 2026-08-13
        # built exactly that (seal plan_A, mark against plan_B) and got a manifest reading
        # plan_sealed true with nothing in it disagreeing. Copying the line is the fix an
        # operator can apply today; a refusal inside marks.py is the one that belongs.
        "  COPY the line above -- do not retype it. A different file with the same name",
        "  seals nothing, and marks.py cannot tell: the mismatch is only reported after",
        "  the run, in manifest.json's plan_seals field.",
        "  Start it before you log in. Its keys are SWALLOWED and never reach the client.",
    ]


# ---------------------------------------- the second witness, on the way back --
SEAL_AGREE, SEAL_DISAGREE, SEAL_UNCHECKED = "agree", "disagree", "unchecked"


SEAL_FILES = ("manifest.json", "plan_seal.json")


def seal_records(outdir):
    """({filename: record}, {filename: why-not}) over `manifest.json` and `plan_seal.json`.

    Split out of `recorded_seal` so the two seals this DRIVER writes can be compared
    against each other, which is a claim nobody was making. Both are rendered from one
    `PlanSeal` minutes apart, so they cannot legitimately disagree -- and adversarial
    review 2026-08-13 built the version that makes them: a `run()` whose manifest re-hashes
    the plan at the end wrote a manifest certifying the EDITED plan while `plan_seal.json`
    sat in the same directory still holding the original. The evidence was on disk, in two
    files, and nothing read the second one. See `compare_plan_seals`.

    THE SECOND DICT IS NOT TIDINESS. "No seal here" has three causes and they are three
    different facts about a capture: the file is absent, the file is UNREADABLE, or the
    file is a manifest written before `--plan` existed. The first draft of this split
    collapsed the middle one into the last and would have reported a truncated manifest as
    "written before --plan existed" -- a confident wrong statement about provenance, which
    is the same defect as the DISAGREE message that asserted one cause of two.
    """
    out, notes = {}, {}
    for name in SEAL_FILES:
        path = os.path.join(outdir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                rec = json.load(fh)
        except (OSError, ValueError) as exc:
            notes[name] = f"{name} cannot be read as JSON ({exc}), so it answers nothing"
            continue
        if not isinstance(rec, dict):
            notes[name] = f"{name} is not a JSON object, so it answers nothing"
        elif "plan_sealed" not in rec:
            notes[name] = (f"{name} carries no plan_sealed key, so it was written "
                           f"before --plan existed -- unsealed by construction, not "
                           f"by choice")
        else:
            out[name] = rec
    return out, notes


def recorded_seal(outdir):
    """(seal dict, source-or-reason) as this driver recorded it, or (None, reason).

    Prefers `manifest.json` and falls back to `plan_seal.json`, because a run that died
    before assembly has the second and not the first -- which is the whole reason
    `write_seal_file` exists. The second element NAMES the file the seal came from on
    success, and the caller carries that into its verdict: "the seals agree" is a
    different claim depending on which artifact was read, and a fallback that is invisible
    in the report is a fallback nobody can tell fired.

    A file with no `plan_sealed` key at all does NOT stop the search -- it is a driver
    older than the flag rather than an answer -- so the older reason is remembered and
    only returned if nothing better turns up.
    """
    recs, notes = seal_records(outdir)
    for name in SEAL_FILES:
        if name not in recs:
            continue
        rec = recs[name]
        if not rec.get("plan_sealed"):
            return None, (f"{name} records plan_sealed false: this run was driven without "
                          f"--plan and there is no pre-launch seal to compare")
        return rec, name
    # Nothing carried a seal. Say WHICH of the three reasons, in file order -- a capture
    # from a driver older than --plan and one whose manifest is truncated are not the same
    # finding, and the second must not be reported as the first.
    for name in SEAL_FILES:
        if name in notes:
            return None, notes[name]
    return None, f"no manifest.json and no plan_seal.json in {outdir}"


def internal_seal_conflict(outdir):
    """(True, why) when this driver's OWN two seal records disagree, else (False, why-not).

    `manifest.json` and `plan_seal.json` are rendered from the same `PlanSeal` at two
    moments in one run, so a disagreement is not a fact about the operator's plan at all
    -- it is a fact about the DRIVER, and it means something between the two writes
    re-derived a value that was supposed to be carried. That is exactly the sabotage that
    got through two rounds of checks on 2026-08-13 (`manifest = {..., "plan_sha256":
    sha256(seal.path)}` using this module's own file hasher), and its evidence was sitting
    in the capture directory the whole time.

    Checked BEFORE the marker comparison, because the marker cannot arbitrate it: if the
    driver contradicts itself, "which of the two does marks.py agree with" is the wrong
    question and answering it would launder a broken driver into an AGREE.
    """
    recs = {n: r for n, r in seal_records(outdir)[0].items() if r.get("plan_sealed")}
    if len(recs) < 2:
        return False, (f"only {len(recs)} sealed record here, so there is nothing for this "
                       f"driver to contradict itself with")
    shas = {n: r.get("plan_sha256") for n, r in recs.items()}
    if len(set(shas.values())) == 1:
        return False, "this driver's own two seal records agree"
    return True, (
        "THIS DRIVER CONTRADICTS ITSELF. " + ", ".join(
            f"{n} says {s}" for n, s in sorted(shas.items())) +
        ". Both are rendered from ONE PlanSeal taken before the launch, so they cannot "
        "legitimately differ: something between the two writes re-read the plan file "
        "instead of using the carried value, which means the later of the two is a hash "
        "of the plan as it stood AFTER the session. Trust neither, and read plan_seal.json "
        "-- it is written when the capture directory appears and is the earlier of the two.")


def compare_plan_seals(outdir):
    """(verdict, why) -- the driver's PRE-LAUNCH seal against marks.py's own.

    THREE-VALUED, never two. `SEAL_UNCHECKED` is not a pass: the operator may legitimately
    never have run the marker, and folding that into `agree` would turn the one comparison
    this pair of tools makes possible into a field that reads green whenever it is absent.
    Same rule `origin.py` applies to ours/live/unknown.

    WHAT IT CATCHES THAT `marks.bind()` CANNOT. `bind` hashes the plan as it is NOW and
    refuses if that disagrees with `marks_meta` -- which catches an edit made after the
    marker started, and is blind to one made BETWEEN the client launching and the marker
    starting, since both of its reads would then see the edited file. Only the driver's
    pre-launch hash can refute that, and only here are all three artifacts on disk.

    The step counts are compared too, and they are not redundant with the hash: they are
    two different readings of the same file by two processes, so a disagreement in counts
    with matching hashes would mean the two parsers disagree rather than the file moved.

    WHERE THIS IS CALLED FROM CHANGED ON 2026-08-13, and the argument that kept it off the
    live path was wrong on its own terms. It used to run only from `reassemble()`, i.e.
    only under `--assemble`, on the reasoning that `plan_marks.jsonl` might not exist when
    the manifest is written and a check that skips in every real run is a check that cannot
    fail. Two things were being conflated. This is not a check -- it is a THREE-VALUED
    RECORDED FIELD, the same shape `origin.py` uses, and `UNCHECKED` is a legitimate value
    for it rather than a skip. And the timing does not bite anyway: the driver prints
    `--pid <client.pid>` in the marks command, `marks.run` ends on that pid, and the
    manifest is written after client teardown, pruning, assembly and the scrub, so a marker
    the operator actually ran has long since closed its file. So `run()` records the verdict
    at manifest time and `reassemble()` recomputes and rewrites it -- because until then the
    one comparison this pair of tools makes possible existed only in console scrollback,
    and a verdict that never reaches an artifact is a verdict nobody can act on months
    later.

    THE DISAGREE MESSAGE NAMES BOTH CAUSES, which it did not at first. A sha mismatch has
    two: the file changed between the two reads, or the operator typed a DIFFERENT file
    into the second shell. The first version asserted the first cause in capitals, and
    adversarial review 2026-08-13 produced the second by sealing `plan_A.txt` and marking
    against `plan_B.txt` -- the message then said "THE PLAN CHANGED" about two files that
    were both untouched and both still on disk. The two names are reported because a reader
    can use them (different basenames make cause two likely), and they are deliberately NOT
    part of the verdict: the seal is over CONTENT, so two paths holding identical bytes are
    the same prediction, and a name comparison would manufacture a DISAGREE out of a file
    that was merely copied.
    """
    conflict, why = internal_seal_conflict(outdir)
    if conflict:
        return SEAL_DISAGREE, why
    ours, source = recorded_seal(outdir)
    if ours is None:
        return SEAL_UNCHECKED, source
    mpath = os.path.join(outdir, marks.PLAN_MARKS_NAME)
    if not os.path.isfile(mpath):
        return SEAL_UNCHECKED, (
            f"a plan was sealed ({ours.get('plan')}, sha256 "
            f"{str(ours.get('plan_sha256'))[:16]}...) but there is no "
            f"{marks.PLAN_MARKS_NAME} here, so the marker was never run or wrote elsewhere")
    try:
        meta, _rows = marks.read(mpath)
    except marks.MarksError as exc:
        return SEAL_UNCHECKED, f"{marks.PLAN_MARKS_NAME} cannot be read: {exc}"
    theirs = meta.get("plan_sha256")
    if not theirs:
        return SEAL_UNCHECKED, f"{marks.PLAN_MARKS_NAME}'s marks_meta carries no plan_sha256"
    if theirs != ours.get("plan_sha256"):
        return SEAL_DISAGREE, (
            f"THE TWO SEALS ARE OF DIFFERENT BYTES. Per {source}, this driver hashed "
            f"{ours.get('plan_sha256')} before the client launched (plan "
            f"{ours.get('plan')}); marks.py hashed {theirs} when the marker started (plan "
            f"{meta.get('plan')}). TWO CAUSES produce this and the artifact cannot tell "
            f"them apart on its own: the plan file was EDITED between the launch and the "
            f"marker, or the operator pointed the second shell at a DIFFERENT file -- "
            f"compare the two names above, and read plan_seal.json's plan_body, which is "
            f"the prediction as it stood before the launch. Either way the marks in this "
            f"capture are labels against a plan that is not the one that was "
            f"pre-registered, and marks.bind() cannot see this -- it compares the marker's "
            f"hash against the file as it stands now, and under the first cause both of "
            f"those are the edited version.")
    if meta.get("steps") is not None and ours.get("plan_steps") is not None \
            and meta["steps"] != ours["plan_steps"]:
        return SEAL_DISAGREE, (
            f"the two seals agree on the bytes and disagree on the STEPS: this driver "
            f"parsed {ours['plan_steps']} and marks.py parsed {meta['steps']} out of the "
            f"same sha256. That is the two parsers disagreeing, not the file moving.")
    # The names are REPORTED and not decided on -- see the docstring. `marks_meta` stores a
    # basename and the manifest an absolute path, so they are quoted separately rather than
    # compared: a reader who sees two different names beside one sha knows the plan was
    # copied or renamed, which is a fact worth having and not a disagreement.
    return SEAL_AGREE, (
        f"two independent seals agree: sha256 {theirs[:16]}..., "
        f"{ours.get('plan_steps')} step(s), taken in different processes at different "
        f"moments -- one before the client launched (per {source}, plan "
        f"{ours.get('plan')}), one when the marker started (plan {meta.get('plan')})")
