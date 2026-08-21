r"""Two arms, one declared difference, and evidence that survives the window closing.

    python toolkit/harness/abrun.py --run retail vault/overlays/slowmo.toml \
                                    --out vault/research/abrun/2026-08-20-slowmo --yes
    python toolkit/harness/abrun.py --compare vault/research/abrun/2026-08-20-slowmo

WHY IT EXISTS. An archive profile is only worth building if somebody can say
afterwards what it changed, and the way that question has been answered so far
is a person watching two client sessions and reporting that one "felt"
different. MEMORY, in its own words: "it feels different, not sure" is a failed
experiment. This is the MECHANICAL half of the answer -- the half that can be
counted, that does not need anybody to look at anything, and that is still on
disk after the operator alt-F4s the client. The half that needs eyes stays with
the operator and is not modelled here at all.

NOTHING HERE LAUNCHES A CLIENT, AND THAT IS THE DESIGN. `a10stage.py`'s
separation is kept: staging archive bytes is one tool and launching is another,
so the launch re-runs its own gates (`cage.assert_launch_safe`,
`datcheck.assert_archive_safe`) rather than trusting that this one already
checked -- a guard that only guards one of two doors is the shape of the defect
it is there to prevent. This prints the exact command and waits. It also means
the run has a HUMAN in it by construction, which is the point: scripted input is
the traffic pattern the live rule is about, and a hand-driven session is what an
archive profile is actually judged on.

THE ARM BOUNDARY IS READ OFF THE ARCHIVE ITSELF. A running client holds
`Gw.dat` open exclusively, so `open(ACTIVE, "r+b")` fails with `PermissionError`
for exactly as long as a client is up and succeeds the moment it is not
(`a10stage.swap`'s probe, RUNBOOK "While Gw.exe is up, vault/run/<build>/Gw.dat
cannot even be opened"). One arm is therefore one hold: from the first refusal
to the first success. A second launch inside one arm would be a second arm, so
the capture this arm binds is the one that appeared with it and never a newer
one that turned up later.

AND NEVER AN OLDER ONE, WHICH IS THE HARDER HALF. A capture is bound BY NAME
against a census taken the moment the arm deployed: a directory that already
existed then is the previous arm's and can never become this one's, however
recently its log was written to. Binding on the log's MTIME alone was not
enough and the hole was MEASURED -- `session.py` keeps relaying to `gamesrv.log`
while it tears a stack down, and `capture_error_dialog` looks for a dialog for
up to twelve seconds after the client exits (session.py:1184, 1234), while this
tool's flip is a whole-file copy of a 4.2 GB archive. One teardown line landing
in arm 1's log during arm 2's flip made arm 1's directory the "newest after
arm 2's deploy", and arm 2 then read that log from byte zero and reported arm
1's entire session as its own, ok=True, with a number nobody could tell from a
real one. The census is the fix; `bytes_at_bind` is recorded beside it so a
reader can see what the arm found when it bound, rather than having to trust
that it found nothing.

EACH ARM STARTS FROM THE BASELINE, AND THE TOOL PUTS IT BACK. An overlay
`--deploy` reads a three-valued premise off ACTIVE first and hard-refuses when
the archive is neither retail nor its own profile, which is right -- but between
two OVERLAY arms the archive is exactly that, because arm 1 left its own profile
in it. MEASURED: `--run alpha beta` played arm 1 to a finished verdict and then
refused arm 2 for "neither retail nor 'beta'", spending a whole hand-driven
session to say so. So a RETAIL restore runs between two overlay arms -- the
a10stage runsheet's own deploy/play/retail/play ordering -- and it is recorded in
the second arm's verdict rather than done quietly.

WHAT IS COUNTED IS ANCHORED, BECAUSE THE LINES ARE FREE TEXT. The gamesrv's
combat and navmesh prints are f-strings with no delimiter guarantee -- `[c3]
agent 41 (Skale) casts skill 1234 (slot 2 of 8)` -- so every counter here is a
whole-line regex and never a split. The two that already have a home,
`deploy.NAVMESH_RE` and `deploy.PLACED_RE`, are IMPORTED rather than copied:
they are the log-line contract with `authsrv.py:2222` and `authsrv.py:6106`, and
a second copy would be a second thing to keep in agreement with the first.

THERE ARE NO TIMESTAMPS IN THAT LOG. Not one gamesrv print carries a clock, so
every time in a verdict is OUR OWN observation clock -- the poll that first saw a
counter move and the poll that last saw it. That makes each one a bracket, not
an instant: the event happened somewhere between the previous poll and this one.
Reported as `first_seen`/`last_seen` rather than `first`/`last` for that reason.

THE VERDICT IS WRITTEN AFTER EVERY POLL AND IT IS ALWAYS COMPLETE ON DISK.
`json.dump` into a temp file, `flush`, `fsync`, then `os.replace` -- so a reader
arriving at any instant sees either the previous document or the new one, never
half of either. This is `Journal`'s discipline applied to a document that is
rewritten rather than appended to, and it is the whole reason this tool can be
killed: the owner closing the client, a reboot, a Ctrl-C in the wrong terminal.
What it does NOT promise is that the last write survives a power cut -- the
directory entry is not separately fsync'able on Windows -- so the guarantee is
"a reader always sees a whole document", not "no update is ever lost".

AND IT WRITES ON EVERY POLL RATHER THAN ON EVERY CHANGE. A heartbeat that only
ticks when new evidence arrives cannot be told apart from a poller that died, and
the difference between "the log has been quiet for ten minutes" and "abrun has
been dead for ten minutes" is the difference between a result and a wasted
session.

A DIFFERENCE IS A RESULT, AND `--compare` EXITS 0 ON ONE. What it exits 1 on is
evidence that is MISSING or TORN -- an arm that never finalised, a verdict that
does not parse, a run record naming an arm that is not there, two arms naming
one verdict file, two arms that bound one capture directory. That separation is
`datcheck.py`'s (0 ran / 1 a finding / 2 could not be read at all) and it matters
here because the interesting outcome and the failure outcome would otherwise
share an exit code.

WHAT A DIFFERENCE IS NOT, AND THE TABLE SAYS SO EVERY TIME IT PRINTS. The two
arms are two hand-driven sessions. Nothing here controls how long the operator
played, where they walked, or what they attacked, and none of the counts is
normalised per second -- the hold duration is printed BESIDE them precisely so
that nobody reads `hit agent 41` against `hit agent 12` as an effect of the
archive when one arm ran three times as long. This tool measures the arms; it
does not control them, and a count that differs is a question rather than an
answer.

Exit codes follow `datcheck.py`: 0 the verb ran, 1 a mechanical finding (an arm
did not finalise, a compare found torn evidence), 2 refused or unreadable.
"""

import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))
import datcheck                                               # noqa: E402
import datwrite                                               # noqa: E402
# The two regexes below are the LOG-LINE CONTRACT with `toolkit/authsrv/`, and
# `deploy.py` already owns them. Importing is not a convenience here: a copy
# would go on matching a format the server had stopped printing, and nothing
# would go red.
import deploy                                                 # noqa: E402
import overlay                                                # noqa: E402
import vaultpath                                              # noqa: E402

FORMAT = "rurik-abrun-verdict"
RUN_FORMAT = "rurik-abrun-run"
FORMAT_VERSION = 1

#: The literal an arm may be instead of a manifest path. It takes its ACTIVE and
#: RETAIL from the OTHER arm's manifest, because a baseline arm is a baseline OF
#: something and inventing its own archive pair would let the two arms differ in
#: more than the one declared thing.
RETAIL_ARM = "retail"

#: Arm states, in the order an arm passes through them. Only `finished` counts
#: as finalised evidence; everything else is torn and `--compare` says so.
PLANNED, DEPLOYED, WAITING, RUNNING = "planned", "deployed", "waiting", "running"
FINISHED, ABANDONED, INTERRUPTED = "finished", "abandoned", "interrupted"

#: How many parsed samples (navmesh shapes, population lines) a verdict keeps.
#: The document is rewritten whole on every poll, so an unbounded list makes the
#: writes grow with the run; the COUNT is exact either way and only the parsed
#: numbers are capped. What was dropped is recorded rather than discarded
#: silently.
SAMPLE_CAP = 64

DEFAULT_POLL = 3.0
DEFAULT_WAIT_LAUNCH = 900.0
DEFAULT_MAX_HOLD = 7200.0


# ---------------------------------------------------------------------------
# What is counted
# ---------------------------------------------------------------------------

class Counter:
    """One anchored line pattern and what a match of it means.

    `fields` names the capture groups worth keeping as parsed samples. Where it
    is None the line is counted and nothing else -- a count is what survives a
    format that carries a float with no fixed precision.
    """

    __slots__ = ("key", "pattern", "what", "fields")

    def __init__(self, key, pattern, what, fields=None):
        self.key = key
        self.pattern = pattern
        self.what = what
        self.fields = fields


#: EVERY PATTERN HERE IS WHOLE-LINE ANCHORED except the two imported ones, which
#: `deploy.py` uses unanchored against whole-file text and are left exactly as
#: that module wrote them. The agent-name group is non-greedy and the suffix
#: after it is required, so a name containing a bracket cannot swallow the rest
#: of the line.
COUNTERS = (
    Counter("hit_agent",
            re.compile(r"^\[c(\d+)\] hit agent (\d+): ([\d.]+)/([\d.]+)$"),
            "the player's swing landed on an NPC "
            "(authsrv.py:4224)"),
    Counter("player_hit_melee",
            re.compile(r"^\[c(\d+)\] player hit by (\d+): ([\d.]+)/([\d.]+)$"),
            "an NPC's swing landed on the player (authsrv.py:5286)"),
    Counter("player_hit_skill",
            re.compile(
                r"^\[c(\d+)\] player hit by skill (\d+): ([\d.]+)/([\d.]+)$"),
            "an NPC's skill landed on the player (authsrv.py:5410)"),
    Counter("agent_casts",
            re.compile(r"^\[c(\d+)\] agent (\d+) \((.+?)\) casts skill (\d+) "
                       r"\(slot (\d+) of (\d+)\)$"),
            "an NPC started a cast (authsrv.py:5068)"),
    Counter("agent_attacks",
            re.compile(r"^\[c(\d+)\] agent (\d+) \((.+?)\) attacks the "
                       r"player$"),
            "an NPC started swinging at the player (authsrv.py:5022)"),
    Counter("navmesh", deploy.NAVMESH_RE,
            "the server loaded a map's pathing mesh (authsrv.py:2222)",
            fields=("map_file_id", "planes", "trapezoids")),
    Counter("area_placed", deploy.PLACED_RE,
            "the server placed an area's spawn rows (authsrv.py:6106)",
            fields=("area", "placed", "total")),
)

COUNTER_KEYS = tuple(c.key for c in COUNTERS)


def new_counts():
    """A fresh counter block: n, and the bracket our own clock observed it in."""
    return {c.key: {"n": 0, "first_seen": None, "last_seen": None}
            for c in COUNTERS}


def count_line(line, counts, samples, stamp):
    """Fold one log line into `counts`/`samples`. -> the counter key or None.

    A line is charged to the FIRST pattern that matches and no other. The two
    `player hit by` forms are distinguishable only by the literal word `skill`
    in the middle of them, so ordering here is not cosmetic -- but neither
    pattern can match the other's line (`player hit by skill 12:` has no digits
    where the melee form needs them), and that is why the anchors are on both
    ends.
    """
    for c in COUNTERS:
        m = c.pattern.search(line)
        if not m:
            continue
        rec = counts[c.key]
        rec["n"] += 1
        if rec["first_seen"] is None:
            rec["first_seen"] = stamp
        rec["last_seen"] = stamp
        if c.fields:
            bucket = samples.setdefault(c.key, {"kept": [], "dropped": 0})
            if len(bucket["kept"]) < SAMPLE_CAP:
                bucket["kept"].append(dict(zip(c.fields, m.groups())))
            else:
                bucket["dropped"] += 1
        return c.key
    return None


# ---------------------------------------------------------------------------
# Writing a document that is always whole
# ---------------------------------------------------------------------------

def write_json_atomic(path, doc):
    """Write `doc` so that no reader ever sees half of it. -> path.

    Temp file in the SAME directory (`os.replace` is only atomic within one
    filesystem), flushed and fsync'd before the rename, so the bytes are on the
    platter before the name points at them. A kill between the fsync and the
    replace loses this update and leaves the PREVIOUS document intact and
    parseable, which is the property the whole tool rests on.

    The directory entry itself is not fsync'd -- there is no portable way to on
    Windows -- so this is a guarantee about what a READER sees, not a guarantee
    that the last write survives a power cut. Stated rather than implied,
    because the two are easy to conflate and only one of them is true here.
    """
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path


def read_json(path, what):
    """Load a document this tool wrote, or say what is wrong with it.

    -> (doc, None) or (None, reason). Never raises: every caller of this is
    reporting on evidence, and evidence that cannot be read is a finding rather
    than a crash.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        return None, f"there is no {what} at {path}"
    except (OSError, ValueError) as exc:
        return None, (f"the {what} at {path} does not parse "
                      f"({type(exc).__name__}: {exc})")
    if not isinstance(doc, dict):
        return None, f"the {what} at {path} is a {type(doc).__name__}"
    return doc, None


def now_stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Tailing the gamesrv log
# ---------------------------------------------------------------------------

def capture_root(root=None):
    return root or os.path.join(vaultpath.require_dir(
        why="abrun reads the harness capture directories"),
        "captures", "harness")


def capture_names(root=None):
    """Every capture directory that exists RIGHT NOW. -> set of bare names.

    Taken once per arm, at the moment its deploy finished, and handed to
    `newest_capture` as the set that arm may never bind. `session.py:1688`
    names a capture directory for the second it was created in and makes it
    fresh per run, so a name is a run: one that was already there belongs to a
    run that started before this arm did.

    A name census rather than a timestamp comparison, because the timestamp
    comparison is the thing that failed -- see the module docstring. This
    answers "was this directory here before the arm" and nothing about it can
    be moved by anything the previous session writes afterwards.
    """
    try:
        return set(os.listdir(capture_root(root)))
    except OSError:
        return set()


def newest_capture(after, root=None, known=()):
    """(gamesrv.log, its capture dir) for the newest harness run after `after`.

    `deploy.newest_harness_log` is the same scan and the precedent; this returns
    the DIRECTORY as well, because `crash-dialog.txt` is written beside the log
    and is the only machine-readable assert a client leaves. It also takes the
    root explicitly so a test can point it at a fixture without a vault.

    `known` is the census `capture_names` took when the arm deployed, and a
    directory in it is SKIPPED whatever its log's mtime says. Both conditions
    are kept: the mtime keeps the precedent's behaviour for a caller that has no
    census, and the census is what actually decides, because a previous arm's
    log goes on growing through its own teardown and its mtime moves with it.
    """
    root = capture_root(root)
    known = set(known)
    best, best_t = None, after
    try:
        names = os.listdir(root)
    except OSError:
        return None, None
    for name in sorted(names):
        if name in known:
            continue
        d = os.path.join(root, name)
        log = os.path.join(d, "gamesrv.log")
        if not os.path.isfile(log):
            continue
        t = os.path.getmtime(log)
        if t > best_t:
            best, best_t = log, t
    return best, (os.path.dirname(best) if best else None)


class Tail:
    """A byte cursor over one growing log file.

    READ IN BINARY, on purpose. The offset has to be exact across polls and
    text-mode newline translation would desync it on Windows, where the harness
    writes `\r\n`. Decoding is `errors="replace"` for the harness's own reason:
    one U+FFFD out of a GW name once killed the pump thread and wedged a server,
    and an instrument that dies on the data it is reading is not an instrument.

    A LINE WITHOUT ITS NEWLINE IS NOT A LINE. Whatever sits past the last `\n`
    is held back as `partial` and folded into the next read, so a poll that
    lands between a server's `write` and its `flush` cannot count half a line
    now and the other half later.
    """

    __slots__ = ("path", "pos", "partial")

    def __init__(self, path):
        self.path = path
        self.pos = 0
        self.partial = b""

    def read_new(self):
        """-> list of complete lines added since the last call."""
        try:
            with open(self.path, "rb") as fh:
                fh.seek(self.pos)
                blob = fh.read()
        except OSError:
            return []
        if not blob:
            return []
        self.pos += len(blob)
        blob = self.partial + blob
        keep = blob.rfind(b"\n")
        if keep < 0:
            self.partial = blob
            return []
        self.partial = blob[keep + 1:]
        text = blob[:keep].decode("utf-8", "replace")
        return [ln.rstrip("\r") for ln in text.split("\n")]


ASSERT_RE = re.compile(r"Assertion:\s*(.+)")


def crash_dialog(capture_dir):
    """What the client's own error dialog says, if it put one up. -> dict.

    `session.capture_error_dialog` writes `crash-dialog.txt` into the capture
    directory and NOTHING ELSE records an assert: `Gw.log` does not, so a quiet
    log is not evidence of a quiet client. One line is lifted out -- the
    `Assertion:` record the dialog puts at the top -- because that single quote
    is what lets a reader audit the arm without the binary, and a single assert
    cited as evidence for a claim is a measurement (CLAUDE.md's 2026-08-12
    refinement). The file is not copied and not bulk-read.
    """
    out = {"present": False, "path": None, "bytes": 0, "assertion": None}
    if not capture_dir:
        return out
    path = os.path.join(capture_dir, "crash-dialog.txt")
    if not os.path.isfile(path):
        return out
    out["present"] = True
    out["path"] = path
    try:
        out["bytes"] = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = ASSERT_RE.search(line)
                if m:
                    out["assertion"] = m.group(1).strip()[:200]
                    break
    except OSError as exc:
        out["assertion"] = f"(unreadable: {exc})"
    return out


# ---------------------------------------------------------------------------
# The client-hold probe
# ---------------------------------------------------------------------------

def client_holds(path):
    """True while a client holds this archive open. Reads nothing, writes nothing.

    `a10stage.swap`'s probe and `overlay._require_closed`'s: the client opens
    `Gw.dat` with an exclusive share mode for its whole run, so `open(..,"r+b")`
    is `PermissionError` while it is up and succeeds the moment it is gone.
    Every OTHER `OSError` is a refusal rather than a `False`, because "the file
    is not there" and "no client is holding it" are the same answer from this
    function and must not be.
    """
    try:
        open(path, "r+b").close()
    except PermissionError:
        return True
    except OSError as exc:
        raise SystemExit(
            f"REFUSED: cannot probe {path} for a client's hold: {exc}\n"
            f"  This probe is the only thing that tells an arm when the run "
            f"started and when it ended, and an error here is not the same "
            f"answer as 'no client is holding it'.") from None
    return False


def wait_for_hold(path, want, deadline, poll, on_tick=None, probe=client_holds):
    """Poll until the hold state is `want`, or `deadline` passes. -> bool.

    `probe` and the clock are parameters so the loop can be driven at speed by
    something other than a real client. `on_tick` is called once per poll with
    the current state, which is where the verdict's heartbeat is written from --
    a wait that records nothing while it waits is a wait nobody can audit
    afterwards.
    """
    while True:
        state = probe(path)
        if on_tick is not None:
            on_tick(state)
        if state == want:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll)


# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------

class Arm:
    """One half of a differential run: a flip, a hold, and what came out of it."""

    __slots__ = ("name", "kind", "manifest", "dir", "doc", "verdict_path",
                 "expect", "index", "exe")

    def __init__(self, name, kind, manifest, out_dir, expect, index, exe=None):
        self.name = name
        self.kind = kind
        self.manifest = manifest
        self.index = index
        self.dir = os.path.join(out_dir, name)
        self.verdict_path = os.path.join(self.dir, "verdict.json")
        self.expect = expect
        #: Resolved once, at RESOLVE time, by `resolve_arms` -- so that an
        #: ambiguous run directory is a refusal before the first flip rather
        #: than after a whole arm has been played. `None` means "not resolved
        #: yet", and `launch_command` resolves it then, which is the path a
        #: directly-constructed Arm takes.
        self.exe = exe
        self.doc = None

    @property
    def active(self):
        return self.manifest.active

    def save(self):
        self.doc["updated"] = now_stamp()
        write_json_atomic(self.verdict_path, self.doc)


def client_exe(active):
    """The client that will open THIS archive. Never `sorted(exes)[-1]`.

    The client has no `-dat` flag: it opens `Gw.dat` from its own working
    directory, so the only binary that can open the archive an arm just
    deployed is one sitting beside it. That makes the run directory the
    resolution rule and nothing else -- not a filename, not a date, not a sort.
    MEMORY, three times in three files: "last one wins" picks the wrong build,
    and filtering to the right build is only half the fix. So an ambiguous
    directory is REFUSED rather than resolved.
    """
    run_dir = os.path.dirname(os.path.abspath(active))
    named = os.path.join(run_dir, "Gw.exe")
    if os.path.isfile(named):
        return named
    try:
        exes = sorted(n for n in os.listdir(run_dir)
                      if n.lower().endswith(".exe"))
    except OSError as exc:
        raise SystemExit(
            f"REFUSED: cannot list {run_dir} to find the client that opens "
            f"{active}: {exc}") from None
    if len(exes) == 1:
        return os.path.join(run_dir, exes[0])
    raise SystemExit(
        f"REFUSED: {run_dir} holds {len(exes)} .exe file(s) and no Gw.exe, so "
        f"which client opens {os.path.basename(active)} is a GUESS.\n"
        f"  {exes if exes else 'nothing there is an executable'}\n"
        f"  The client has no -dat flag -- it opens Gw.dat from its own "
        f"directory -- so the archive this arm deploys can only be read by a "
        f"binary in that directory, and picking the one that sorts last has "
        f"chosen the wrong build three times in this repo's history.\n"
        f"  Stage the run directory with "
        f"python toolkit/clientpatch/make_run_dir.py, or point overlay.active "
        f"at the archive beside the client you mean.")


def launch_command(arm, hold=None):
    """The exact command the operator runs for this arm. -> list of argv words.

    `--exe` is ALWAYS spelled out. Omitted, `session.py` defaults to the newest
    thing under `vault/run`, which is the rule this repo has been bitten by
    three times; here the exe is derived from the archive the arm just deployed,
    which is the only binding that is actually true. It was RESOLVED at resolve
    time and is merely spelled here; resolving it here was a refusal that fired
    after the flip.
    """
    argv = [sys.executable, os.path.join(TOOLKIT, "harness", "session.py"),
            "--replace", "--keep-open",
            "--exe", arm.exe or client_exe(arm.active)]
    if hold:
        argv += ["--hold", str(hold)]
    return argv


def _resolve_one(spec):
    """(kind, manifest-or-None) for one arm spec, without touching an archive."""
    if spec.strip().lower() == RETAIL_ARM:
        return RETAIL_ARM, None
    return "overlay", overlay.load_manifest(spec, echo=False)


def resolve_arms(spec_a, spec_b, out_dir):
    """(run record, [Arm, Arm]). Reads manifests and refuses; writes nothing.

    EVERY REFUSAL IN HERE HAPPENS BEFORE A BYTE IS FLIPPED. An A/B run costs the
    operator two hand-driven client sessions, and a tool that discovers halfway
    through the second one that the two arms were never comparable has spent
    somebody's evening to say so.

    AND THAT SENTENCE IS A CLAIM ABOUT WHAT IS DECIDED HERE, not about where the
    refusals are written. Two of them used to sit outside: which client opens
    the archive was resolved where the launch command is PRINTED, after the
    flip, and the build record was only stat'd here and first opened by
    `deployed_state`, also after the flip. Both are pure reads of files this
    function already has in hand -- a directory listing and one `json.load` --
    and on an [overlay, retail] ordering both landed after a whole hand-driven
    session. They are taken here now, in the order a refusal costs least:
    the manifests, the pair, the archives, the client, the records.
    """
    kinds, mans = [], []
    for spec in (spec_a, spec_b):
        kind, man = _resolve_one(spec)
        kinds.append(kind)
        mans.append(man)

    if kinds[0] == RETAIL_ARM and kinds[1] == RETAIL_ARM:
        raise SystemExit(
            "REFUSED: both arms are `retail`.\n"
            "  Two arms of a differential run differ in ONE declared thing, "
            "and these two differ in nothing at all -- the result would be a "
            "measurement of how much a hand-driven session varies from itself, "
            "which is worth taking but is not what this tool reports.")

    # THE COMPARISON IS BETWEEN THE RESOLVED ARM NAMES, NOT BETWEEN THE
    # MANIFESTS. `overlay.NAME_RE` is `[a-z0-9-]+`, so a profile may legally be
    # called `retail`, and paired with the LITERAL `retail` arm the two names
    # collide while the two specs look nothing alike. MEASURED: both arms wrote
    # `retail/verdict.json`, the second overwrote the first, and `--compare`
    # read one file twice and printed a perfect null -- every row `same`, exit
    # 0 -- for a comparison that never happened. Comparing the manifests missed
    # it because one arm has no manifest of its own.
    names = [RETAIL_ARM if k == RETAIL_ARM else m.name
             for k, m in zip(kinds, mans)]
    if names[0] == names[1]:
        raise SystemExit(
            f"REFUSED: both arms resolve to the arm name {names[0]!r}.\n"
            f"    arm A: {spec_a}\n"
            f"    arm B: {spec_b}\n"
            f"  The name becomes the arm's directory under --out, so the "
            f"second arm would write its verdict over the first one's and the "
            f"comparison would be an archive against itself -- and it would "
            f"print as a difference of zero rather than as an error.\n"
            f"  Rename one of them: overlay.name is what this is read from.")

    carrier = mans[0] or mans[1]
    if mans[0] and mans[1]:
        for field in ("active", "retail"):
            a, b = getattr(mans[0], field), getattr(mans[1], field)
            if os.path.normcase(os.path.abspath(a)) != os.path.normcase(
                    os.path.abspath(b)):
                raise SystemExit(
                    f"REFUSED: the two manifests name different {field.upper()} "
                    f"archives.\n"
                    f"    {a}\n"
                    f"    {b}\n"
                    f"  Then the arms differ in the whole world and not in the "
                    f"one thing either of them declares, and nothing that came "
                    f"out of them could be attributed to either profile.")

    for role, path in (("ACTIVE", carrier.active), ("RETAIL", carrier.retail)):
        if not os.path.isfile(path):
            raise SystemExit(
                f"REFUSED: the manifest's {role} archive is not there:\n"
                f"    {path}\n"
                f"  Both arms are flips between these two files, and a run "
                f"that discovers a missing one after the first deploy has "
                f"already overwritten the archive it was going to compare "
                f"against.")

    # WHICH CLIENT OPENS THE ARCHIVE IS DECIDED HERE, not where the command is
    # printed. It is a directory listing and nothing else, so there is no
    # excuse for its refusal to arrive after a flip -- and it did: an ambiguous
    # run directory was announced only once `restore_retail` had already copied
    # RETAIL over the shared ACTIVE archive. Both arms share ACTIVE by the
    # refusal above, so one resolution serves both.
    exe = client_exe(carrier.active)

    # THE BUILD RECORD IS READ HERE, AND WHAT MAKES IT TRUSTWORTHY IS STILL
    # `overlay.load_fingerprints`'s to decide -- its own digest, its manifest
    # sha, its retail stamp. Nothing is re-decided in this file; the record is
    # simply OPENED at the only moment where a refusal is free. Checking merely
    # that the file exists was not enough: the first reader was
    # `overlay.deployed_state`, AFTER the flip, so a record with the wrong
    # format was announced with the ACTIVE archive already overwritten.
    for man in {id(m): m for m in mans if m}.values():
        record = overlay.fingerprints_path(man)
        if not os.path.isfile(record):
            raise SystemExit(
                f"REFUSED: overlay {man.name!r} has no build record at "
                f"{record}.\n"
                f"  A --deploy reads it, and the `retail` arm's own identity "
                f"is read out of it too, so neither arm can run without one.\n"
                f"  python toolkit/mapdata/overlay.py --build {man.path}")
        overlay.load_fingerprints(man, why="resolve the arms of", kind="build")

    arms = []
    for i, (kind, man) in enumerate(zip(kinds, mans)):
        if kind == RETAIL_ARM:
            arms.append(Arm(RETAIL_ARM, RETAIL_ARM, carrier, out_dir,
                            overlay.STATE_RETAIL, i, exe=exe))
        else:
            arms.append(Arm(man.name, "overlay", man, out_dir, man.name, i,
                            exe=exe))

    run = {"format": RUN_FORMAT,
           "format_version": FORMAT_VERSION,
           "started": now_stamp(),
           "out": os.path.abspath(out_dir),
           "active": carrier.active,
           "retail": carrier.retail,
           "exe": exe,
           "arms": [{"name": a.name, "kind": a.kind,
                     "manifest": a.manifest.path if a.kind == "overlay" else None,
                     "manifest_sha256": (a.manifest.sha256 if a.kind == "overlay"
                                         else None),
                     "carrier_manifest": a.manifest.path,
                     "expect": a.expect,
                     "verdict": os.path.join(a.name, "verdict.json")}
                    for a in arms]}
    return run, arms


# ---------------------------------------------------------------------------
# Running one arm
# ---------------------------------------------------------------------------

def start_arm(arm, poll, wait_launch, max_hold):
    """The arm's opening document, on disk before anything is flipped."""
    os.makedirs(arm.dir, exist_ok=True)
    arm.doc = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "arm": arm.name,
        "kind": arm.kind,
        "index": arm.index,
        "manifest": arm.manifest.path,
        "manifest_sha256": arm.manifest.sha256,
        "active": arm.active,
        "expect": arm.expect,
        "state": PLANNED,
        "started": now_stamp(),
        "updated": None,
        "finished": None,
        "polls": 0,
        "settings": {"poll": poll, "wait_launch": wait_launch,
                     "max_hold": max_hold},
        "premise": None,
        "state_before": None,
        "state_after": None,
        "launch_command": None,
        "baseline_restored": None,
        "log": {"path": None, "capture_dir": None, "bytes": 0,
                "partial_bytes": 0, "lines": 0, "matched": 0,
                "bound_at": None, "bytes_at_bind": None,
                "captures_before": None},
        "counts": new_counts(),
        "samples": {},
        "crash_dialog": crash_dialog(None),
        "gate": None,
        "post": None,
        "hold_seconds": None,
        "note": None,
    }
    arm.save()
    return arm.doc


def flip(arm, echo=True):
    """Put this arm's archive into ACTIVE, through overlay's own verbs. -> premise.

    Neither half of this is reimplemented. `--deploy`'s three-valued baseline
    premise, its staged-copy re-verification, its banner and its before-image
    all belong to `overlay.py` and are reached by calling it; the `retail` arm
    goes through `--retail`, which deliberately takes NO premise because its
    whole job is to make an unknown archive known again.
    """
    if arm.kind == RETAIL_ARM:
        return overlay.restore_retail(arm.manifest, yes=True, echo=echo)
    return overlay.deploy(arm.manifest, yes=True, echo=echo)


def restore_baseline(manifest, echo=True):
    """Put RETAIL back between two overlay arms. -> what was restored, as a dict.

    A `--deploy` refuses outright when ACTIVE is neither retail nor its own
    profile, and after an overlay arm ACTIVE is exactly that: it carries the
    PREVIOUS profile. So the second of two overlay arms could never deploy, and
    it found out after the operator had already played the first one to a
    finished verdict -- MEASURED, `--run alpha beta`, both profiles owning one
    row. Restoring the baseline first is what makes the second arm's premise a
    fact rather than an accident of which profile ran before it.

    IT IS THE PREVIOUS ARM'S MANIFEST THAT IS HANDED IN, not the next one's,
    because `restore_retail` also drops the before-image a deploy took and the
    image that is now a lie is the one belonging to the deploy being undone.
    The previous arm's `verify_after` has already run by then -- inside its own
    finalize, at the only moment it is meaningful.

    Only between two OVERLAY arms. A `retail` arm's own flip IS this copy, and
    doing it twice would be a second whole-file write of a 4.2 GB archive for
    no change at all.
    """
    if echo:
        print(f"\n  putting the RETAIL baseline back between the two arms, so "
              f"the next arm's premise is a fact and not whatever the last one "
              f"left behind (overlay {manifest.name!r}'s deploy is what is "
              f"being undone).")
    state = overlay.restore_retail(manifest, yes=True, echo=echo)
    return {"undid": manifest.name, "state": state, "at": now_stamp()}


def expected_fingerprints(arm):
    """The row block this arm's ACTIVE archive must match, or None.

    An overlay arm is identified by what the DEPLOY wrote (the pre-launch
    record), not by what was staged -- the two answer different questions and
    only the first one is about the archive a client is about to open. A retail
    arm has no pre-launch record by construction (`--retail` deletes the
    before-image it would have invalidated), so its comparand is the build
    record's own retail side.
    """
    doc = overlay.load_fingerprints(
        arm.manifest, why="identify the arm's archive for",
        kind="build" if arm.kind == RETAIL_ARM else "prelaunch")
    return doc["retail_rows"] if arm.kind == RETAIL_ARM else doc["rows"]


def gate_archive(arm, why):
    """Refuse to tell the operator to launch at an archive a client would repair.

    THIS SITE RUNS THE GATE ITSELF. `overlay.deploy` does not call it and is not
    asked to: `datcheck.assert_archive_safe`'s own docstring names four launch
    doors and the rule that each one checks rather than trusting an upstream
    caller, and this is a fifth in everything but the `Popen` -- it is the thing
    that prints the command. The identity tier is included because here, unlike
    the live path, there IS a profile that is supposed to be deployed and a
    mismatch means the arm would be recorded under the wrong name.

    THE TWO SIDES OF THE IDENTITY COMPARE READ DIFFERENT THINGS, and that is
    what makes it a check rather than a tautology: `overlay.fingerprint_block`
    computed its crc from the PAYLOAD BYTES on disk, and this tier compares it
    against the MFT's own crc FIELD. They can only agree if the row's field and
    its bytes agree -- which `crc_sweep`, three lines earlier in the same call,
    has just proved for every used row. So a mismatch here means the profile is
    wrong, and never that a checksum went stale.
    """
    return datcheck.assert_archive_safe(
        arm.active, fingerprints=expected_fingerprints(arm), why=why)


def observe(arm, poll, wait_launch, max_hold, captures=None,
            probe=client_holds, since=None, known=None, echo=True):
    """Wait for the client, count while it holds, stop when it lets go.

    -> True if the arm saw a whole hold, False if it timed out waiting.

    `since` and `known` are the SAME moment in two forms -- the instant this
    arm's deploy finished -- and together they are what makes the capture
    directory this arm binds be this arm's. `since` is that moment as a clock
    reading; `known` is it as a set of directory names. Both are threaded in
    from the flip rather than taken here, because between the two there is a
    whole-file copy of a 4.2 GB archive and a capture written during it would
    belong to whatever ran before. A caller that hands neither gets a census
    taken now, which is right for a direct call and wrong for a second arm --
    hence `run_arm` handing both.

    Every poll writes the verdict, whether anything moved or not: see the module
    docstring on why a heartbeat that only ticks on new evidence is unreadable.
    """
    t0 = time.time() if since is None else since
    known = capture_names(captures) if known is None else set(known)
    arm.doc["log"]["captures_before"] = len(known)
    tail = [None]

    def tick(_state):
        arm.doc["polls"] += 1
        _harvest(arm, tail, t0, captures, known=known)
        arm.save()

    arm.doc["state"] = WAITING
    arm.save()
    started = wait_for_hold(arm.active, True,
                            time.monotonic() + wait_launch, poll,
                            on_tick=tick, probe=probe)
    if not started:
        arm.doc["state"] = ABANDONED
        arm.doc["note"] = (
            f"no client opened {arm.active} within {wait_launch:.0f}s of the "
            f"deploy. The archive is left as this arm deployed it; re-run "
            f"--run, or put the baseline back with overlay.py --retail --yes.")
        arm.save()
        if echo:
            print(f"  {arm.doc['note']}")
        return False

    hold_started = time.monotonic()
    arm.doc["state"] = RUNNING
    arm.save()
    if echo:
        print(f"  the client has {os.path.basename(arm.active)} open -- "
              f"counting until it lets go")
    ended = wait_for_hold(arm.active, False,
                          hold_started + max_hold, poll,
                          on_tick=tick, probe=probe)
    arm.doc["hold_seconds"] = round(time.monotonic() - hold_started, 1)
    if not ended:
        arm.doc["state"] = ABANDONED
        arm.doc["note"] = (
            f"the client still held {arm.active} after {max_hold:.0f}s, so "
            f"this arm was left open rather than scored. Nothing was written "
            f"to the archive.")
        arm.save()
        if echo:
            print(f"  {arm.doc['note']}")
        return False
    # One last harvest AFTER the release: the server's final lines and the
    # crash dialog both land at teardown, and a poll loop that stops at the
    # release misses exactly the evidence a crash produces.
    _harvest(arm, tail, t0, captures, known=known)
    arm.save()
    return True


def _harvest(arm, tail, t0, captures, known=()):
    """Fold whatever the log has grown into the arm's counts. Never raises."""
    log = arm.doc["log"]
    if tail[0] is None:
        path, capture_dir = newest_capture(t0, captures, known=known)
        if path is None:
            return
        # ONCE BOUND, NEVER RE-SCANNED. One arm is one hold, so the capture
        # that appeared with this arm is the arm's evidence; a newer directory
        # turning up later belongs to a run that is not this one, and following
        # it would silently mix two sessions into one count. `known` is the
        # other half of that sentence and the half that was missing: a capture
        # that was already there when the arm deployed is not this arm's
        # either, however late its log was last written to.
        tail[0] = Tail(path)
        log["path"], log["capture_dir"] = path, capture_dir
        log["bound_at"] = now_stamp()
        # WHAT THE LOG ALREADY HELD WHEN THIS ARM BOUND IT. Not a refusal: a
        # capture that is this arm's own is minutes younger than the poll that
        # finds it and the harness has already written its startup lines into
        # it, so a nonzero number here is ordinary. It is recorded because the
        # failure it belongs to -- an arm reading a previous session from byte
        # zero -- produced a plausible count and nothing else on the document
        # said where the bytes came from.
        try:
            log["bytes_at_bind"] = os.path.getsize(path)
        except OSError:
            log["bytes_at_bind"] = None
    t = tail[0]
    stamp = now_stamp()
    for line in t.read_new():
        log["lines"] += 1
        if count_line(line, arm.doc["counts"], arm.doc["samples"], stamp):
            log["matched"] += 1
    log["bytes"] = t.pos
    log["partial_bytes"] = len(t.partial)
    arm.doc["crash_dialog"] = crash_dialog(log["capture_dir"])


def post_checks(arm, echo=True):
    """What the archive is after the client had it. -> dict, never an exception.

    A refusal HERE IS THE RESULT. `assert_archive_safe` is a launch gate and
    raises, which is right on the way in and wrong on the way out: an archive
    the client damaged is precisely what this arm is trying to find out, and a
    post-flight that dies on it records nothing and finalises nothing. So the
    refusal is caught and written down, with the arm still finalised.
    """
    out = {"archive": None, "refused": None, "preflight_failed": [],
           "preflight_checks": 0, "crc_bad": None, "crc_checked": None,
           "state_after": None, "verify_after": None, "notes": []}
    try:
        cleared = datcheck.assert_archive_safe(arm.active, why="score an A/B arm")
        out["archive"] = cleared["summary"]
        out["preflight_checks"] = len(cleared["preflight"])
        out["crc_checked"] = cleared["crc_sweep"]["checked"]
        out["crc_bad"] = 0
    except datcheck.ArchiveUnsafe as exc:
        out["refused"] = str(exc)
        # The gate stops at the FIRST fault, so the finer-grained numbers are
        # taken separately -- an arm that reddens the gate is the one whose
        # detail is worth the most.
        try:
            cs, _facts = datcheck.preflight(arm.active)
            out["preflight_checks"] = len(cs)
            out["preflight_failed"] = [c.name for c in cs if not c.ok]
            sweep = datcheck.crc_sweep(arm.active)
            out["crc_bad"] = len(sweep["bad"])
            out["crc_checked"] = sweep["checked"]
        except Exception as exc2:                              # noqa: BLE001
            out["notes"].append(f"the detail pass could not run: "
                                f"{type(exc2).__name__}: {exc2}")
    try:
        out["state_after"] = overlay.deployed_state(arm.manifest)
    except SystemExit as exc:
        # overlay refuses through SystemExit for every fault, and here that is
        # an observation about the archive rather than a reason to stop.
        out["state_after"] = None
        out["notes"].append(f"deployed_state could not answer: {exc}")
    if arm.kind != RETAIL_ARM:
        try:
            va = overlay.verify_after(arm.manifest, echo=False)
            out["verify_after"] = {
                "our_rows_changed": va["our_rows_changed"],
                "changed_rows": va["changed_rows"],
                "unchanged": va["unchanged"],
                "growth": va["growth"]}
        except SystemExit as exc:
            out["notes"].append(f"verify-after could not run: {exc}")
    if echo:
        if out["refused"]:
            print("  the archive did NOT clear the gate afterwards:")
            for line in str(out["refused"]).splitlines():
                print(f"    {line}")
        else:
            print(f"  archive after the run: {out['archive']}")
        print(f"  deployed state after the run: {out['state_after']}")
    return out


def finalize(arm, echo=True):
    """Score the arm and mark it finished. -> the post-check block.

    `finished` and the state are written in the SAME atomic replace as the post
    checks. A verdict that said `finished` a moment before its post block landed
    would be a document `--compare` reads as evidence while it is still being
    written.
    """
    arm.doc["post"] = post_checks(arm, echo=echo)
    arm.doc["state_after"] = arm.doc["post"]["state_after"]
    arm.doc["state"] = FINISHED
    arm.doc["finished"] = now_stamp()
    arm.save()
    if echo:
        print(f"  arm {arm.name!r} finalised -> {arm.verdict_path}")
    return arm.doc["post"]


def run_arm(arm, poll, wait_launch, max_hold, captures=None,
            probe=client_holds, hold=None, echo=True, restore_from=None):
    """Flip, print the command, watch, score. -> True if the arm finalised."""
    start_arm(arm, poll, wait_launch, max_hold)
    if client_holds(arm.active):
        raise SystemExit(
            f"REFUSED: something already holds {arm.active} open before arm "
            f"{arm.name!r} has deployed anything.\n"
            f"  A client is running. Close it: this arm's start and end are "
            f"read off that same lock, so an arm begun under a client that was "
            f"already up would be scored over somebody else's session.")

    what = ("the RETAIL baseline" if arm.kind == RETAIL_ARM
            else f"overlay {arm.name!r}")
    if echo:
        print(f"\n=== arm {arm.index + 1} of 2: {arm.name} ({what}) ===")
    if restore_from is not None:
        # RECORDED IN THIS ARM'S VERDICT, not done quietly. A whole-file write
        # of the shared ACTIVE archive that nobody asked for by name is the
        # kind of thing a reader has to be able to find afterwards.
        arm.doc["baseline_restored"] = restore_baseline(restore_from, echo=echo)
        arm.save()
    arm.doc["premise"] = flip(arm, echo=echo)
    deployed_at = time.time()
    known = capture_names(captures)
    arm.doc["state"] = DEPLOYED
    arm.save()

    state = overlay.deployed_state(arm.manifest)
    arm.doc["state_before"] = state
    arm.save()
    if state != arm.expect:
        raise SystemExit(
            f"REFUSED: arm {arm.name!r} deployed and the ACTIVE archive does "
            f"not say so.\n"
            f"  expected: {arm.expect}\n"
            f"  reads as: {state}\n"
            f"  The flip reported success and the bytes disagree, so whatever "
            f"a client did next would be recorded under the wrong arm's name.")

    cleared = gate_archive(arm, f"launch arm {arm.name!r}")
    arm.doc["gate"] = cleared["summary"]
    arm.save()
    if echo:
        print(f"  archive gate: {cleared['summary']}")

    argv = launch_command(arm, hold=hold)
    arm.doc["launch_command"] = argv
    arm.save()
    if echo:
        print("")
        print("  " + "-" * 68)
        print(f"  LAUNCH THIS, BY HAND, AND PLAY THE ARM:")
        print("    " + " ".join(f'"{w}"' if " " in w else w for w in argv))
        print(f"  Nothing here launches it. When the client opens "
              f"{os.path.basename(arm.active)} this arm starts; when it lets "
              f"go, this arm ends.")
        print("  " + "-" * 68)
        print("")

    ok = observe(arm, poll, wait_launch, max_hold, captures=captures,
                 probe=probe, since=deployed_at, known=known, echo=echo)
    if not ok:
        return False
    finalize(arm, echo=echo)
    return True


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def prepare_out(out_dir):
    """Make the output directory, and refuse to write a second run into it.

    `datwrite`'s two path refusals are called rather than restated: `guard`
    keeps everything out of the owner's install, and `guard_source` keeps it out
    of `vault/dat_study`, the copy every other archive is cut from.
    """
    out_dir = os.path.abspath(out_dir)
    datwrite.guard(out_dir)         # called for the refusal, not the return:
    datwrite.guard_source(out_dir)  # guard() normcases and this path is printed
    record = os.path.join(out_dir, "abrun.json")
    if os.path.exists(record):
        raise SystemExit(
            f"REFUSED: {record} is already there.\n"
            f"  A second run into one directory overwrites the first one's "
            f"arms in place, and evidence overwritten in place is evidence "
            f"nobody can audit. Name a new --out.")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir, record


def run(spec_a, spec_b, out_dir, yes=False, poll=DEFAULT_POLL,
        wait_launch=DEFAULT_WAIT_LAUNCH, max_hold=DEFAULT_MAX_HOLD,
        captures=None, probe=client_holds, hold=None, echo=True):
    """Both arms, in order. -> 0 if both finalised, 1 if either did not.

    THE ORDER IS: resolve everything and refuse; arm 1; put the baseline back
    if arm 2 needs it; arm 2. The restore is the a10stage runsheet's own
    deploy/play/retail/play ordering and it happens only between two OVERLAY
    arms -- see `restore_baseline` for what it costs and what it buys.
    """
    if not yes:
        raise SystemExit(
            "REFUSED: --run writes over the ACTIVE archive at least TWICE -- "
            "once per arm, and a third time to put the baseline back between "
            "two overlay arms -- and that archive is shared with every other "
            "session.\n"
            "  Nothing has been written. Re-run with --yes when you mean it.")
    out_dir, record = prepare_out(out_dir)
    run_doc, arms = resolve_arms(spec_a, spec_b, out_dir)
    write_json_atomic(record, run_doc)
    both_overlay = all(a.kind != RETAIL_ARM for a in arms)
    if echo:
        print(f"A/B run -> {out_dir}")
        print(f"  ACTIVE {run_doc['active']}")
        print(f"  RETAIL {run_doc['retail']}")
        print(f"  client {run_doc['exe']}")
        print(f"  arms   {arms[0].name} then {arms[1].name}"
              + (" (with a RETAIL restore between them: two overlay arms, and "
                 "the second one's deploy reads its premise off what the first "
                 "left behind)" if both_overlay else ""))

    finished = []
    try:
        for arm in arms:
            # Only between two OVERLAY arms: after a `retail` arm ACTIVE is
            # already the baseline, and a `retail` arm's own flip is this same
            # copy.
            restore_from = (arms[arm.index - 1].manifest
                            if both_overlay and arm.index > 0 else None)
            try:
                finished.append(run_arm(arm, poll, wait_launch, max_hold,
                                        captures=captures, probe=probe,
                                        hold=hold, echo=echo,
                                        restore_from=restore_from))
            except SystemExit as exc:
                # A REFUSAL MID-RUN IS ITSELF EVIDENCE. The ACTIVE archive may
                # already be carrying this arm's profile, so the verdict says
                # what stopped and where rather than leaving a `planned`
                # document for somebody to guess at.
                if arm.doc is not None:
                    arm.doc["state"] = INTERRUPTED
                    arm.doc["note"] = f"refused: {exc}"
                    arm.save()
                raise
            if not finished[-1]:
                break
    except KeyboardInterrupt:
        for arm in arms:
            if arm.doc is not None and arm.doc["state"] not in (FINISHED,
                                                                ABANDONED):
                arm.doc["state"] = INTERRUPTED
                arm.doc["note"] = ("interrupted at the keyboard; the ACTIVE "
                                   "archive is left as this arm deployed it")
                arm.save()
        if echo:
            print("\ninterrupted. Every verdict on disk is complete and "
                  "parseable; none of the unfinished ones is evidence.")
        return 1
    crc, lines = compare_lines(out_dir)
    if echo:
        print("")
        print("\n".join(lines))
    # THE COMPARE'S OWN VERDICT COUNTS TOWARDS THIS ONE. Two arms can both
    # finalise and still leave evidence that is torn -- two arms on one capture
    # is the case -- and a run that exited 0 while its own table said the
    # evidence was unusable would be the tool disagreeing with itself.
    ran = all(finished) and len(finished) == 2
    return 0 if ran and crc == 0 else 1


# ---------------------------------------------------------------------------
# The differential table
# ---------------------------------------------------------------------------

def load_run(out_dir):
    """(run record, [ (arm name, verdict|None, why-not|None) ]) for a run dir."""
    record = os.path.join(out_dir, "abrun.json")
    doc, why = read_json(record, "run record")
    if doc is None:
        return None, why, []
    if doc.get("format") != RUN_FORMAT:
        return None, (f"{record} is not an abrun run record "
                      f"(format {doc.get('format')!r})"), []
    arms, seen = [], {}
    for spec in doc.get("arms", []):
        name = spec.get("name")
        path = os.path.join(out_dir, spec.get("verdict", ""))
        v, vwhy = read_json(path, f"verdict for arm {name!r}")
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            # TWO ARMS, ONE FILE. `resolve_arms` refuses the pair that produces
            # this, and it is checked again here because the failure it makes is
            # the worst kind this tool has: not an error but a perfect null,
            # every row `same`, exit 0, for a comparison of one arm with itself.
            # A run record written by an older build is still readable here.
            v, vwhy = None, (
                f"arms {seen[key]!r} and {name!r} both name {path} -- one "
                f"verdict read twice is not a comparison, it is an arm against "
                f"itself")
        seen.setdefault(key, name)
        if v is not None and v.get("format") != FORMAT:
            vwhy = (f"{path} is not an abrun verdict "
                    f"(format {v.get('format')!r})")
            v = None
        if v is not None and (v.get("state") != FINISHED
                              or not v.get("finished")):
            # AN UNFINISHED ARM IS NOT A ZERO. Every state but `finished` means
            # the arm stopped somewhere it was not scored, and reading its
            # counters as a result would report an interruption as an effect.
            vwhy = (f"arm {name!r} is {v.get('state')!r}, not {FINISHED!r}"
                    + (f" -- {v['note']}" if v.get("note") else ""))
            v = None
        arms.append((name, v, vwhy))
    return doc, None, arms


def _cell(v, default="-"):
    return default if v is None else v


def compare_lines(out_dir):
    """(exit code, printable lines) for a finished (or unfinished) run."""
    doc, why, arms = load_run(out_dir)
    if doc is None:
        return 1, [f"CANNOT COMPARE: {why}"]
    out = ["differential: " + " vs ".join(a[0] or "?" for a in arms),
           f"  ACTIVE {doc.get('active')}",
           f"  run    {os.path.abspath(out_dir)}",
           ""]
    missing = [(name, w) for name, v, w in arms if v is None]
    if len(arms) != 2:
        return 1, out + [f"CANNOT COMPARE: the run record names {len(arms)} "
                         f"arm(s); a differential has two."]
    if missing:
        out.append("CANNOT COMPARE: evidence is missing or torn.")
        for name, w in missing:
            out.append(f"  {name}: {w}")
        out.append("  A torn arm is not a null result -- it is an arm that was "
                   "not measured, and the difference between those two is the "
                   "whole reason this exits 1 rather than printing zeroes.")
        return 1, out

    va, vb = arms[0][1], arms[1][1]
    names = [arms[0][0], arms[1][0]]
    width = max(24, len(names[0]), len(names[1]))

    def row(label, a, b, delta=""):
        out.append((f"  {label:<28}{str(a):>{width}}  {str(b):>{width}}  "
                    f"{delta}").rstrip())

    row("", names[0], names[1], "difference")
    out.append("  " + "-" * (28 + 2 * width + 12))
    for label, key in (("hold, seconds", "hold_seconds"),
                       ("polls", "polls")):
        a, b = va.get(key), vb.get(key)
        d = "" if a is None or b is None else _fmt_delta(a, b)
        row(label, _cell(a), _cell(b), d)
    row("log lines read", va["log"]["lines"], vb["log"]["lines"],
        _fmt_delta(va["log"]["lines"], vb["log"]["lines"]))
    # WHICH CAPTURE EACH COUNT CAME OUT OF, on the face of the table. Two arms
    # printing one directory name is the shape of the defect where an arm read
    # the previous session's log, and it is invisible in the counters.
    row("capture bound",
        os.path.basename(va["log"].get("capture_dir") or "") or "NONE",
        os.path.basename(vb["log"].get("capture_dir") or "") or "NONE",
        "one arm is one capture")
    out.append("")
    for c in COUNTERS:
        a = va["counts"].get(c.key, {}).get("n", 0)
        b = vb["counts"].get(c.key, {}).get("n", 0)
        row(c.key, a, b, _fmt_delta(a, b))
    out.append("")
    row("crash dialog",
        "YES" if va["crash_dialog"]["present"] else "no",
        "YES" if vb["crash_dialog"]["present"] else "no",
        "a client assert is the only one there is")
    for v, name in ((va, names[0]), (vb, names[1])):
        if v["crash_dialog"].get("assertion"):
            out.append(f"    {name}: {v['crash_dialog']['assertion']}")
    pa, pb = va.get("post") or {}, vb.get("post") or {}
    row("preflight rules failed", len(pa.get("preflight_failed") or []),
        len(pb.get("preflight_failed") or []), "")
    row("payload CRCs bad", _cell(pa.get("crc_bad")),
        _cell(pb.get("crc_bad")), "")
    row("state before / after",
        f"{va.get('state_before')} / {va.get('state_after')}",
        f"{vb.get('state_before')} / {vb.get('state_after')}", "")
    for v, name in ((va, names[0]), (vb, names[1])):
        changed = ((v.get("post") or {}).get("verify_after") or {}).get(
            "our_rows_changed") or []
        if changed:
            out.append(f"    {name}: the client wrote to "
                       f"{len(changed)} row(s) this profile owns: "
                       f"{[r['row'] for r in changed]}")
    rc = 0
    ca, cb = (va["log"].get("capture_dir"), vb["log"].get("capture_dir"))
    if ca and cb and os.path.normcase(os.path.abspath(ca)) == os.path.normcase(
            os.path.abspath(cb)):
        # ONE CAPTURE CANNOT BE TWO ARMS. Both arms finalised, so nothing above
        # says anything is wrong -- and every counter on one side of this table
        # was read out of the other side's session. It is torn evidence, and it
        # leaves by the same exit code as the rest of the torn evidence.
        rc = 1
        out += ["",
                f"  BOTH ARMS BOUND THE SAME CAPTURE: {ca}",
                "  Every count above was read out of one session, so the "
                "difference between the two",
                "  columns is a difference between two readings of one arm. "
                "This is not a null result;",
                "  it is an unmeasured arm, and the run has to be repeated."]
    out += [
        "",
        "  WHAT THIS TABLE IS. Two hand-driven sessions, counted the same way.",
        "  Nothing here controlled how long either arm ran, where the operator "
        "walked",
        "  or what they attacked, and no count is normalised per second -- the "
        "hold",
        "  duration is printed above them for exactly that reason. A row that "
        "differs",
        "  is a question. Attributing it to the archive needs the arms to have "
        "been",
        "  comparable, and only the operator can say whether they were.",
    ]
    return rc, out


def _fmt_delta(a, b):
    try:
        d = b - a
    except TypeError:
        return ""
    if d == 0:
        return "same"
    return f"{d:+g}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", nargs=2, metavar=("ARM_A", "ARM_B"),
                    help="two arms: an overlay manifest, or the literal "
                         "`retail` (which takes its archives from the other "
                         "arm's manifest)")
    ap.add_argument("--out", metavar="DIR",
                    help="where the two arms' verdicts are written")
    ap.add_argument("--compare", metavar="DIR",
                    help="print the differential table for a finished run")
    ap.add_argument("--yes", action="store_true",
                    help="required by --run, which writes over the shared "
                         "ACTIVE archive once per arm")
    ap.add_argument("--poll", type=float, default=DEFAULT_POLL,
                    metavar="SECONDS", help="how often the archive is probed "
                                            "and the verdict rewritten")
    ap.add_argument("--wait-launch", type=float, default=DEFAULT_WAIT_LAUNCH,
                    metavar="SECONDS",
                    help="how long an arm waits for the operator to start the "
                         "client before giving up")
    ap.add_argument("--max-hold", type=float, default=DEFAULT_MAX_HOLD,
                    metavar="SECONDS",
                    help="how long an arm counts before deciding the session "
                         "is not going to end")
    ap.add_argument("--hold", type=float, default=None, metavar="SECONDS",
                    help="if given, the printed launch command carries "
                         "session.py's own --hold, so both arms are bounded "
                         "the same way")
    ap.add_argument("--captures", metavar="DIR", default=None,
                    help="harness capture root; default is the vault's "
                         "captures/harness")
    args = ap.parse_args(argv)
    chosen = [v for v in ("run", "compare") if getattr(args, v)]
    if len(chosen) != 1:
        print("REFUSED: pick exactly one of --run or --compare.\n"
              "  --run drives two arms and writes their verdicts; --compare "
              "reads verdicts that are already written. Running both in one "
              "invocation would report on a run while it was still happening.")
        return 2
    try:
        if args.compare:
            rc, lines = compare_lines(args.compare)
            print("\n".join(lines))
            return rc
        if not args.out:
            print("REFUSED: --run needs --out DIR to write the two arms into.")
            return 2
        return run(args.run[0], args.run[1], args.out, yes=args.yes,
                   poll=args.poll, wait_launch=args.wait_launch,
                   max_hold=args.max_hold, captures=args.captures,
                   hold=args.hold)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        print(str(exc.code))
        return 2
    except Exception as exc:                                   # noqa: BLE001
        # `bit31.py`'s reason: a run that could not be read must never leave by
        # the interpreter's own exit code and be mistaken for a result.
        print(f"REFUSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
