r"""A/B differential runs: the counters must match the server's real formats, and
the verdict must still parse after the process is killed mid-write.

    python toolkit/harness/test_abrun.py

NO CLIENT AND NO VAULT. Every fixture below is built in a temp directory: the
gamesrv logs, the capture directories, the manifests, the archives.
`RURIK_VAULT` is pointed at a temp directory so that nothing can reach the real
one by accident, and no section here reads a corpus -- so no section can
legitimately skip except the one the platform decides (section 3's real
share-mode lock, which is a Windows mechanism).

SECTION 0 IS THE CONTRACT AND IT IS TWO CHECKS DEEP. The log lines this tool
counts are f-strings in `toolkit/authsrv/authsrv.py` with no schema -- `[c3]
agent 41 (Skale) casts skill 1234 (slot 2 of 8)` -- so the fixture lines are
written in the server's own shapes and then, separately, each counter's
distinctive fragment is required to still be present in `authsrv.py`'s source.
The first check proves the regex reads the line; the second is what goes red the
day somebody rewords the print, which is the failure the recon named outright:
"changing either print's format silently breaks deploy.py's parser with no test
catching it". The NEAR MISSES are checked in the same section, because a counter
that matches everything is not a counter: `player hit by 41:` and `player hit by
skill 41:` are one word apart and must never be charged to each other.

SECTION 2 IS THE INTERRUPTION, AND IT CARRIES ITS OWN POSITIVE CONTROL. Proving
that an atomically-written verdict survives a kill is worthless unless the test
can DETECT a torn file at all, so the section first writes a document the naive
way, truncates it, and requires the reader to REFUSE it. Only then does it kill
`os.replace` mid-write and require the previous document to still parse. Without
the control, an unconditionally-forgiving reader would pass both halves.

SECTION 3 IS THE PROBE AGAINST A REAL LOCK. The client holds `Gw.dat` with an
exclusive share mode, which is not what `msvcrt.locking` does and not what a
second Python handle does -- a byte-range lock still lets `open()` through, so a
test built on one would prove nothing about the mechanism the arm boundary is
read from. This opens the file through `CreateFileW` with a share mode of 0 --
pure `ctypes`, the way `keytap.py` already reaches Win32 -- and requires
`client_holds` to answer True, then False after the handle closes. Off Windows
there is no such share mode and the section is skip-declared.

SECTION 4b IS THE ARM BOUNDARY, AND IT CARRIES THE DEFECT AS ITS CONTROL. An
arm binds one capture directory and counts out of it; binding on the log's MTIME
alone let an arm bind the PREVIOUS arm's capture, because a stack goes on
relaying while it tears down and one teardown line moves that log's mtime past
this arm's deploy. The section runs the same arm twice against the same fixture:
once told nothing existed before it, where it reads 30 hits that belong to
somebody else's session, and once with the census it takes for itself, where it
reads zero. Thirty and thirty-one both look like a session, which is why the
control is there rather than only the fix.

SECTION 5 IS THE ONE THAT MATTERS AFTER A CRASH. `post_checks` runs a LAUNCH
gate on the way out, and a launch gate raises -- so an archive the client
damaged, which is the single most interesting thing an arm can find, would
otherwise kill the scorer and finalise nothing. The section builds a healthy
archive and a header-CRC-poked one and requires the second to be RECORDED, with
the arm still reaching `finished`.

SECTION 6 ASKS OF EVERY REFUSAL *WHEN*, NOT ONLY *WHETHER*. `resolve_arms`
promises that every refusal in it happens before a byte is flipped, and two of
them did not: which client opens the archive is a directory listing, and whether
the build record is a build record is one `json.load`, and both were announced
only after a whole-file copy had already landed on the shared ACTIVE archive.
So those two are asked through `--run` against a fixture whose ACTIVE and RETAIL
carry DIFFERENT bytes, and the check is the archive's own checksum afterwards.
`build_world`'s two archives are byte-identical and could not have answered it.

SECTION 8 IS THE REAL THING: real archives, real build records, real deploys,
`test_overlay.py`'s own fixture. It exists because the ordering defect it covers
was invisible to every fake -- two overlay arms owning one row resolve cleanly,
play the first arm to a finished verdict, and then hard-refuse the second for
"neither retail nor 'beta'", having spent the operator's evening to say the pair
was never comparable. Only the real `overlay.deploy` computes that premise, so
only a real pair could show it, and only a real pair can show the RETAIL restore
between the arms fixing it.
"""

import binascii
import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))
import abrun                                                   # noqa: E402
import deploy                                                  # noqa: E402
import overlay                                                 # noqa: E402
import vaultpath                                               # noqa: E402
import checks                                                  # noqa: E402
# SECTION 8 RUNS AGAINST REAL ARCHIVES AND REAL DEPLOYS, and it borrows the
# fixture `test_overlay.py` already maintains for that -- the repo's own
# pattern (`test_datwrite` imports `test_datcheck`, `test_rebloat` imports its
# `build_archive`). Building a second archive population here would be a second
# thing to keep in agreement with `overlay.py`, and the arm-ordering defect this
# section exists for was only ever visible against the real verbs.
import test_overlay as TO                                      # noqa: E402

# FLOOR: 120, measured from a real green run on 2026-08-20 and not guessed.
# Per section, counted off the log rather than predicted:
# {0: 31, 1: 13, 2: 6, 3: 6, 4: 10, "4b": 7, 5: 6, 6: 17, 7: 16, 8: 8}.
# It was 93 before the review; the 27 that landed with it are the four defects
# below and their controls.
#
# TWO OF SECTION 3'S SIX ARE THE REAL-LOCK CELL and are `LEDGER.skip`'d off
# Windows, where no exclusive share mode exists -- so a non-Windows run executes
# 118 and this floor makes that a FAIL. That is deliberate and it is the
# framework's own rule ("a skip that drops the run below its declared floor is a
# FAIL, not a note"): the arm boundary is READ OFF a Windows lock, so a platform
# that cannot hold one has not tested this tool, and a floor set to the weakest
# platform would let the machine this repo actually runs on lose two checks in
# silence.
#
# SABOTAGES, applied one at a time as in-memory patches to names the real code
# path resolves through, then reverted. Nothing on disk was edited, and these
# are the reds OBSERVED, not predicted. The seven marked (*) are the review's
# four findings and the guards that came with them:
#
#   count_line charges every line to the first counter             26 red
#   run() never puts the baseline back between arms (*)             6 red
#   write_json_atomic writes in place (no temp, no replace)         4 red
#   newest_capture ignores the census (*)                           4 red
#   the line patterns lose their ^ and $ anchors                    3 red
#   post_checks lets the launch gate's refusal propagate            3 red
#   the tail counts its held-back partial line                      2 red
#   resolve_arms only STATS the build record (*)                    2 red
#   client_exe falls back to sorted(exes)[-1]                       2 red
#   resolve_arms stops comparing the two manifests' ACTIVE paths    1 red
#   resolve_arms resolves the exe only where it PRINTS it (*)       1 red
#   resolve_arms compares the manifests, not the arm names (*)      1 red
#   prepare_out stops refusing a second run into one directory      1 red
#   load_run reads one verdict twice without noticing (*)           1 red
#   compare treats an unfinished arm as evidence                    1 red
#   compare says nothing when both arms bound one capture (*)       1 red
#   client_holds answers False on any OSError                       1 red
#
# EVERY SABOTAGE RAN ALL 120 CHECKS, and three of them had to be made to. The
# anchor sabotage first scored ZERO -- the near misses were all missing a field
# rather than carrying spare text, so nothing in the file could tell an anchored
# pattern from an unanchored one, and the `^`/`$` were decoration this test
# certified. `WRAPPED` exists for that and nothing else. The `post_checks`
# sabotage first ended the run at 65 of 93: a scorer that raises takes the rest
# of the file with it, so section 5 goes through `scored()`. And the eager-exe
# sabotage first HUNG THE FILE for a quarter of an hour: with that refusal
# defeated the run reaches the wait, and the wait's default is 900 s -- which is
# why section 6's two "before a byte is flipped" checks pass zero timeouts. A
# sabotage that hangs has reported nothing at all, which is worse than a
# sabotage that scores zero.
#
# THE ONE-RED SABOTAGES ARE THIN AND ARE NAMED AS THIN -- each is a single
# refusal that nothing else depends on. The count is not the measure of what
# they are worth: `sorted(exes)[-1]` is the defect MEMORY records three times in
# three files, and it is catchable at all only because the fixture run directory
# holds two executables where neither is named Gw.exe. The same goes for the
# eager-exe sabotage at 1: what it breaks is not WHETHER the refusal fires but
# whether it fires before a whole-file copy of a shared 4.2 GB archive, and
# there is exactly one honest way to ask that.
LEDGER = checks.Ledger("A/B differential runs", floor=120)
check = checks.adopt(LEDGER)


# ---------------------------------------------------------------------------
# Fixture log lines, in the server's own shapes
# ---------------------------------------------------------------------------

#: Written the way `authsrv.py` writes them. Each entry is (line, the counter it
#: must be charged to, a fragment of the producing print that must still be in
#: authsrv.py's source). The fragment is the half that goes red on a reword.
LINES = [
    ("[c3] hit agent 41: 42/120", "hit_agent", "] hit agent "),
    ("[c3] player hit by 41: 380/480", "player_hit_melee", "] player hit by "),
    ("[c3] player hit by skill 1234: 320/480", "player_hit_skill",
     "] player hit by skill "),
    ("[c3] agent 41 (Skale) casts skill 1234 (slot 2 of 8)", "agent_casts",
     ") casts skill "),
    ("[c3] agent 41 (Skale) attacks the player", "agent_attacks",
     ") attacks the "),
    ("[map] navmesh 0x287D3: 1 planes, 13 trapezoids", "navmesh",
     "[map] navmesh 0x"),
    ("[c3] area 'sculpt': 3 of 3 placed", "area_placed",
     " of {len(rows)} placed"),
]

#: Lines that must be charged to NOTHING. A counter that matches these is a
#: counter that would have reported a startup banner as combat.
#:
#: THE `s2c` LINES ARE REAL AND THEY ARE THE POINT OF THIS LIST. Every send goes
#: through `authsrv.py:7064`, which prints `[c{n}] s2c {label} (0x{op:04x},
#: {len}B)` -- and the label the cast site hands it is `f"agent {agent_id} casts
#: skill {skill_id}"` (authsrv.py:5066), written one line above the cast print
#: this file counts. So a looser pattern does not merely match noise: it counts
#: EVERY CAST TWICE, once for the event and once for the packet that carried it,
#: and the number would look entirely plausible.
NEAR_MISSES = [
    "[c3] hit agent 41",                       # no health pair
    "hit agent 41: 42/120",                    # no connection prefix
    "[c3] player hit by nobody: 380/480",      # the id is not a number
    "[c3] agent 41 (Skale) casts skill 1234",  # no slot clause
    "[map] navmesh: 1 planes, 13 trapezoids",  # no file id
    "[c3] area 'sculpt': placed",              # no counts
    "[gate] listening on 127.0.0.1:6112",      # ordinary server chatter
    "[c3] s2c agent 41 casts skill 1234 (0x0057, 12B)",     # the packet echo
    "[c3] s2c skill 1234 deals 60 to the player (0x0047, 20B)",
]

#: Lines whose ONLY defect is something around the edges -- the counted text is
#: there, whole, with other text on one side of it. Only the `^`/`$` anchors
#: refuse these, which is why they are asked separately: `session.py`'s pump
#: prefixes `[{name}] ` when it echoes a server (session.py:596), so a relayed
#: copy of a log is a shape this repo already produces, and a relayed copy of an
#: event is not a second event.
WRAPPED = [
    "[gamesrv] [c3] hit agent 41: 42/120",
    "[gamesrv] [c3] player hit by skill 1234: 320/480",
    "[c3] agent 41 (Skale) attacks the player, and misses",
]


# ------------------------------------------------------------------ plumbing

@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def use_vault(path):
    """Point the vault at `path`. `vaultpath` memoizes, so the memo goes too."""
    os.makedirs(path, exist_ok=True)
    os.environ["RURIK_VAULT"] = path
    vaultpath._resolved = None
    return path


def refusal(fn, *a, **kw):
    """Run and return the refusal text, or "" if it did not refuse."""
    try:
        with quiet():
            fn(*a, **kw)
    except SystemExit as exc:
        return str(exc)
    return ""


def scored(fn, *a, **kw):
    """Run something that must not raise; a raise becomes a value, not the end.

    A sabotage that makes a scorer die takes the rest of the file with it, and a
    run that stopped has said the machine is unhappy rather than what broke
    (test_overlay.py measured three sabotages at half coverage before its own
    version of this landed). Every call here that is checked for NOT raising
    goes through this.
    """
    try:
        with quiet():
            return fn(*a, **kw), None
    except BaseException as exc:                               # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding=None if "b" in mode else "utf-8",
              newline="" if "b" not in mode else None) as fh:
        fh.write(text)
    return path


# ---------------------------------------------------------------------------
# A small archive, written from its own byte literals
# ---------------------------------------------------------------------------

BLOCK, ENTRY_SIZE, ENTRY_CRC = 512, 24, 0x14
FILE_MAGIC, MFT_MAGIC = b"3AN\x1a", b"Mft\x1a"
ROW_HEADER, ROW_IDTABLE, ROW_SELF, FIRST_ROW = 1, 2, 3, 16
USED_FIRST = 3
FID_ONE, FID_TWO = 700001, 700002


def self_crc_of(mft, count):
    """Row 3's own crc: the table either side of row 3's own 24 bytes."""
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:count * ENTRY_SIZE]), acc)


def tiny_archive(path, payloads):
    """An archive of `payloads` that clears all ten open-time rules.

    Written from struct literals rather than by asking `archive.py` to make one:
    a fixture the module under test constructed can only prove the module agrees
    with itself.
    """
    entry_count = FIRST_ROW + len(payloads)
    mft_size = entry_count * ENTRY_SIZE
    idtable = b"".join(struct.pack("<II", FID_ONE + i, FIRST_ROW + i)
                       for i in range(len(payloads)))
    extents = {ROW_HEADER: (0, 32), ROW_IDTABLE: (BLOCK, len(idtable))}
    blobs = {ROW_IDTABLE: idtable}
    off = BLOCK + max(1, -(-len(idtable) // BLOCK)) * BLOCK
    for i, payload in enumerate(payloads):
        extents[FIRST_ROW + i] = (off, len(payload))
        blobs[FIRST_ROW + i] = payload
        off += max(1, -(-len(payload) // BLOCK)) * BLOCK
    mft_off = off
    buf = bytearray(mft_off + mft_size)

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, mft_off)
    struct.pack_into("<I", head, 0x18, mft_size)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head
    for row, blob in blobs.items():
        o = extents[row][0]
        buf[o:o + len(blob)] = blob

    fields = {ROW_HEADER: (0, 32, USED_FIRST),
              ROW_IDTABLE: (BLOCK, len(idtable), USED_FIRST),
              ROW_SELF: (mft_off, mft_size, USED_FIRST)}
    for i, payload in enumerate(payloads):
        fields[FIRST_ROW + i] = (extents[FIRST_ROW + i][0], len(payload),
                                 USED_FIRST)
    mft = bytearray(mft_size)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, entry_count)
    for row, (o, size, flags) in fields.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[o:o + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE, o, size, 0, flags,
                         0, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC,
                     self_crc_of(mft, entry_count))
    buf[mft_off:mft_off + mft_size] = mft
    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


MANIFEST = """\
[overlay]
name = "{name}"
active = "{active}"
retail = "{retail}"

[[edit]]
file_id = 0x{fid:X}
compression = 0
plain = "{plain}"
acknowledge_shared_with = []
"""


def manifest_at(path, name, active, retail, payload, fid=FID_ONE):
    """A real overlay manifest on disk. `load_manifest` opens no archive."""
    plain = os.path.join(os.path.dirname(path), f"{name}.bin")
    with open(plain, "wb") as fh:
        fh.write(payload)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(MANIFEST.format(
            name=name, fid=fid,
            active=active.replace("\\", "/"),
            retail=retail.replace("\\", "/"),
            plain=os.path.basename(plain)))
    return path


def build_record(man, row=FIRST_ROW, format_=None):
    """A build record `overlay.load_fingerprints` ACCEPTS, for a tiny archive.

    Written through `overlay.write_fingerprints` with the retail stamp read off
    the real file, because that is what makes it acceptable: the record is
    matched on its own digest, its manifest's sha and the baseline's identity,
    and a fixture that skipped any of those would be testing a refusal rather
    than the path past it. `format_` is the one knob a sabotage needs -- a
    record with the wrong format is the shape whose refusal used to arrive
    after the flip.
    """
    with overlay.Archive(man.retail) as ar:
        ident = overlay.archive_identity(ar)
    edit = man.edits[0]
    doc = {"format": overlay.FORMAT if format_ is None else format_,
           "format_version": overlay.FORMAT_VERSION,
           "overlay": man.name,
           "manifest": man.path,
           "manifest_sha256": man.sha256,
           "built": "2026-08-20T00:00:00",
           "staged": overlay.staged_path(man, create=True),
           "journal": overlay.journal_path(man),
           "retail": ident,
           "staged_identity": ident,
           "file_ids": {str(row): edit.file_id},
           # What a real --build of this one stored edit would have produced.
           "rows": {str(row): [len(edit.plain),
                               f"{binascii.crc32(edit.plain) & 0xFFFFFFFF:08x}",
                               edit.compression]},
           "retail_rows": overlay.fingerprint_block(man.retail, [row])}
    return overlay.write_fingerprints(overlay.fingerprints_path(man), doc)


def sha_of(path):
    with open(path, "rb") as fh:
        return binascii.crc32(fh.read()) & 0xFFFFFFFF


class FakeClient:
    """A scripted client hold, which may write to the gamesrv log as it goes.

    Each call answers the next state in `states` and, at the poll indices named
    in `writes`, appends bytes to `log` FIRST -- so a line lands between two
    polls exactly as the server's would, and the harvest that follows has to
    pick it up rather than having been handed it.
    """

    def __init__(self, states, log=None, writes=None):
        self.states = list(states)
        self.log = log
        self.writes = dict(writes or {})
        self.calls = 0
        self.paths = []

    def __call__(self, path):
        i = self.calls
        self.calls += 1
        self.paths.append(path)
        if self.log is not None and i in self.writes:
            os.makedirs(os.path.dirname(self.log), exist_ok=True)
            with open(self.log, "ab") as fh:
                fh.write(self.writes[i])
        return self.states[min(i, len(self.states) - 1)]


def crlf(*lines):
    """The bytes the harness actually writes: text mode on Windows is \r\n."""
    return b"".join((ln + "\r\n").encode("utf-8") for ln in lines)


# ---------------------------------------------------------------------------
# 0. the log-line contract
# ---------------------------------------------------------------------------

def section0():
    print("\n== section 0: what the counters match, and what they must not ==")
    src = open(os.path.join(TOOLKIT, "authsrv", "authsrv.py"),
               encoding="utf-8").read()
    for line, key, fragment in LINES:
        counts, samples = abrun.new_counts(), {}
        got = abrun.count_line(line, counts, samples, "2026-08-20T00:00:00")
        check(got == key and counts[key]["n"] == 1,
              f"{key} matches its own line and charges exactly one count",
              f"charged to {got!r}: {line}")
    for line, key, fragment in LINES:
        check(fragment in src,
              f"and {key}'s producing print is still in authsrv.py: "
              f"{fragment!r}",
              "the format moved and this counter would silently read zero")

    for line in NEAR_MISSES:
        counts, samples = abrun.new_counts(), {}
        got = abrun.count_line(line, counts, samples, "t")
        check(got is None,
              f"nothing is charged for a near miss: {line[:44]!r}",
              f"charged to {got!r}")

    for line in WRAPPED:
        counts, samples = abrun.new_counts(), {}
        got = abrun.count_line(line, counts, samples, "t")
        check(got is None,
              f"nor for a line the counted text merely sits INSIDE: "
              f"{line[:44]!r}",
              f"charged to {got!r} -- an anchor is missing")

    counts, samples = abrun.new_counts(), {}
    abrun.count_line("[c3] player hit by skill 1234: 320/480", counts, samples,
                     "t")
    check(counts["player_hit_melee"]["n"] == 0
          and counts["player_hit_skill"]["n"] == 1,
          "`player hit by skill N` is a skill and never a melee hit -- the two "
          "formats are one word apart",
          f"melee {counts['player_hit_melee']['n']}")

    counts, samples = abrun.new_counts(), {}
    abrun.count_line("[c3] agent 41 (Ancient Skale (young)) casts skill 7 "
                     "(slot 1 of 4)", counts, samples, "t")
    check(counts["agent_casts"]["n"] == 1,
          "an agent whose NAME carries brackets is still one cast: the name "
          "group is non-greedy and the slot clause after it is required")

    check(abrun.COUNTERS[5].pattern is deploy.NAVMESH_RE
          and abrun.COUNTERS[6].pattern is deploy.PLACED_RE,
          "the two regexes that already had a home are IMPORTED from deploy.py, "
          "not copied: they are the contract with authsrv and a second copy "
          "would drift silently")

    counts, samples = abrun.new_counts(), {}
    for line, _key, _f in LINES:
        abrun.count_line(line, counts, samples, "2026-08-20T01:02:03")
    kept = (samples.get("navmesh") or {}).get("kept") or [{}]
    check(counts["navmesh"]["first_seen"] == "2026-08-20T01:02:03"
          and kept[0].get("trapezoids") == "13",
          "a counter records the bracket OUR clock observed it in, and keeps "
          "the parsed numbers where the line carries any",
          json.dumps(samples.get("navmesh")))

    counts, samples = abrun.new_counts(), {}
    for i in range(abrun.SAMPLE_CAP + 5):
        abrun.count_line(f"[map] navmesh 0x{i:X}: 1 planes, {i} trapezoids",
                         counts, samples, "t")
    nav = samples.get("navmesh") or {"kept": [], "dropped": None}
    check(counts["navmesh"]["n"] == abrun.SAMPLE_CAP + 5
          and len(nav["kept"]) == abrun.SAMPLE_CAP
          and nav["dropped"] == 5,
          "the COUNT is exact past the sample cap and what was dropped is "
          "recorded -- the document is rewritten whole on every poll, so the "
          "samples are what has to be bounded",
          json.dumps({k: v for k, v in nav.items() if k != "kept"}))


# ---------------------------------------------------------------------------
# 1. the tail
# ---------------------------------------------------------------------------

def section1(tmp):
    print("\n== section 1: the byte cursor over a growing log ==")
    path = os.path.join(tmp, "tail", "gamesrv.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(crlf("[c3] hit agent 41: 42/120",
                      "[c3] hit agent 41: 30/120"))
    t = abrun.Tail(path)
    lines = t.read_new()
    check(lines == ["[c3] hit agent 41: 42/120", "[c3] hit agent 41: 30/120"],
          "two whole lines come back with the \\r stripped, not three",
          repr(lines))
    check(t.read_new() == [],
          "and a second read of an unchanged file returns nothing")

    with open(path, "ab") as fh:
        fh.write(b"[c3] player hit by 41: 380/480")     # no newline yet
    check(t.read_new() == [] and t.partial,
          "a line with no newline yet is HELD BACK -- a poll that lands between "
          "the server's write and its flush must not count half a line",
          f"partial {t.partial!r}")

    with open(path, "ab") as fh:
        fh.write(b"\r\n")
    check(t.read_new() == ["[c3] player hit by 41: 380/480"],
          "and it comes back whole, once, when its newline arrives")

    with open(path, "ab") as fh:
        fh.write(b"[map] navmesh 0x\xff\xfe: 1 planes, 2 trapezoids\r\n")
    lines = t.read_new()
    check(len(lines) == 1 and "\ufffd" in lines[0],
          "a byte that is not utf-8 is replaced, never raised: an instrument "
          "that dies on the data it is reading is not an instrument",
          repr(lines))
    check(t.pos == os.path.getsize(path),
          "the cursor sits exactly at end of file after every read",
          f"{t.pos} vs {os.path.getsize(path)}")

    gone = abrun.Tail(os.path.join(tmp, "tail", "not-there.log"))
    check(gone.read_new() == [],
          "a log that is not there yet reads as nothing, not as a crash: the "
          "harness writes it seconds after the client starts")

    root = os.path.join(tmp, "captures")
    old = os.path.join(root, "2026-08-19_aaaa", "gamesrv.log")
    write(old, "old\n")
    os.utime(old, (time.time() - 600, time.time() - 600))
    log, cap = abrun.newest_capture(time.time() - 5, root)
    check(log is None and cap is None,
          "a capture older than the arm's deploy is not the arm's capture")
    new = os.path.join(root, "2026-08-20_bbbb", "gamesrv.log")
    write(new, "new\n")
    log, cap = abrun.newest_capture(time.time() - 5, root)
    check(log == new and cap == os.path.dirname(new),
          "and the newest one after it is, with its DIRECTORY -- crash-dialog "
          "sits beside the log and is the only assert there is",
          f"{log}")

    # THE CENSUS, AND WHY THE MTIME ALONE IS NOT ENOUGH. `old` is the previous
    # arm's capture; one line appended to it during this arm's flip makes it
    # the newest log on disk by a wide margin.
    census = abrun.capture_names(root)
    check(census == {"2026-08-19_aaaa", "2026-08-20_bbbb"},
          "the census names every capture directory that exists at the moment "
          "an arm deploys", f"{sorted(census)}")
    since = time.time()                  # this arm's deploy finished HERE
    time.sleep(0.02)
    with open(old, "a", encoding="utf-8") as fh:
        fh.write("[c3] connection closed\n")     # the previous stack, tearing down
    log, cap = abrun.newest_capture(since, root)
    check(log == old,
          "the CONTROL: by mtime alone the previous arm's log IS the newest "
          "one after this arm's deploy -- one teardown line is all it takes",
          f"{log}")
    log, cap = abrun.newest_capture(since, root, known=census)
    check(log is None and cap is None,
          "and against the census it is not bindable at all: a directory that "
          "was already there belongs to a run that started before this arm, "
          "however late its log was last written to", f"{log}")
    mine = os.path.join(root, "2026-08-20_cccc", "gamesrv.log")
    write(mine, "[c3] hit agent 41: 42/120\n")
    log, cap = abrun.newest_capture(since, root, known=census)
    check(log == mine,
          "while the one that appeared AFTER the census binds normally -- the "
          "census excludes the previous arm and nothing else", f"{log}")


# ---------------------------------------------------------------------------
# 2. the interruption
# ---------------------------------------------------------------------------

def section2(tmp):
    print("\n== section 2: a document that is always whole ==")
    d = os.path.join(tmp, "atomic")
    os.makedirs(d, exist_ok=True)
    naive = os.path.join(d, "naive.json")

    # THE POSITIVE CONTROL FIRST. Proving a file survives a tear is worthless
    # unless the reader can see a tear at all.
    with open(naive, "w", encoding="utf-8") as fh:
        json.dump({"format": abrun.FORMAT, "a": list(range(200))}, fh)
    size = os.path.getsize(naive)
    with open(naive, "r+b") as fh:
        fh.truncate(size // 2)
    doc, why = abrun.read_json(naive, "verdict")
    check(doc is None and "does not parse" in why,
          "the control: a document written in place and truncated is REFUSED, "
          "so this section can tell a torn file from a whole one",
          why or "it parsed")

    good = os.path.join(d, "verdict.json")
    abrun.write_json_atomic(good, {"format": abrun.FORMAT, "n": 1})
    doc, why = abrun.read_json(good, "verdict")
    check(doc and doc["n"] == 1, "an atomic write reads back", why)

    real_replace = os.replace
    boom = []

    def die(src, dst):
        boom.append(src)
        raise KeyboardInterrupt("killed between the fsync and the rename")

    os.replace = die
    try:
        try:
            abrun.write_json_atomic(good, {"format": abrun.FORMAT, "n": 2})
        except KeyboardInterrupt:
            pass
    finally:
        os.replace = real_replace
    doc, why = abrun.read_json(good, "verdict")
    check(doc and doc["n"] == 1,
          "killed between the fsync and the rename, the PREVIOUS document is "
          "still whole and still the one on disk -- the update is lost and "
          "nothing is torn", f"{doc} / {why}")
    check(boom and os.path.isfile(good + ".tmp"),
          "and the half-written update is in the .tmp file, where no reader of "
          "the verdict looks")

    with open(good + ".tmp", "wb") as fh:
        fh.write(b'{"format": "rurik-abrun-verd')
    doc, why = abrun.read_json(good, "verdict")
    check(doc and doc["n"] == 1,
          "a torn .tmp left behind by an earlier kill does not shadow the "
          "verdict", why)
    abrun.write_json_atomic(good, {"format": abrun.FORMAT, "n": 3})
    doc, _ = abrun.read_json(good, "verdict")
    check(doc["n"] == 3 and not os.path.exists(good + ".tmp"),
          "and the next successful write replaces both")


# ---------------------------------------------------------------------------
# 3. the client-hold probe
# ---------------------------------------------------------------------------

def deny_all_handle(path):
    """A Win32 handle with share mode 0 -- the client's own exclusive hold.

    NOT `msvcrt.locking` and not a second Python handle: both of those leave
    `open()` working, so a test built on either would prove nothing about the
    mechanism an arm's start and end are read from.
    """
    import ctypes
    import ctypes.wintypes as wt
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateFileW.restype = wt.HANDLE
    k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                              wt.DWORD, wt.DWORD, wt.HANDLE]
    h = k.CreateFileW(path, 0x80000000, 0, None, 3, 0x80, None)
    if h in (None, -1, 0xFFFFFFFFFFFFFFFF):
        raise OSError(ctypes.get_last_error(), "CreateFileW")
    return k, h


def section3(tmp):
    print("\n== section 3: the hold probe against a real exclusive handle ==")
    path = os.path.join(tmp, "hold", "Gw.dat")
    write(path, "x" * 64)
    check(abrun.client_holds(path) is False,
          "an archive nobody is holding probes as free")

    if sys.platform != "win32":
        LEDGER.skip("the real exclusive-hold probe",
                    f"{sys.platform} has no Win32 share mode; the arm boundary "
                    f"is read from one, so there is nothing here to imitate")
    else:
        k, h = deny_all_handle(path)
        try:
            check(abrun.client_holds(path) is True,
                  "and probes as HELD while a handle with share mode 0 is open "
                  "-- the client's own hold, and the whole arm boundary")
        finally:
            k.CloseHandle(h)
        check(abrun.client_holds(path) is False,
              "and free again the moment that handle closes")

    why = refusal(abrun.client_holds, os.path.join(tmp, "hold", "gone.dat"))
    check("REFUSED" in why and "not the same answer" in why,
          "an archive that is not there REFUSES rather than answering False: "
          "'no client is holding it' and 'there is no file' are not one answer",
          why[:80])

    ticks = []
    fake = FakeClient([False, False, True])
    got = abrun.wait_for_hold(path, True, time.monotonic() + 5, 0.0,
                              on_tick=ticks.append, probe=fake)
    check(got is True and ticks == [False, False, True],
          "the wait polls until the state is the one asked for, and reports "
          "every poll to its tick", f"{ticks}")
    got = abrun.wait_for_hold(path, True, time.monotonic() - 1, 0.0,
                              probe=FakeClient([False]))
    check(got is False,
          "and returns False when the deadline passes rather than waiting "
          "forever on a client nobody launched")


# ---------------------------------------------------------------------------
# 4. an arm, driven by a scripted client
# ---------------------------------------------------------------------------

def build_world(tmp):
    """A run directory, two archives, two manifests and a capture root."""
    run = os.path.join(tmp, "run", "2026-08-20_build")
    os.makedirs(run, exist_ok=True)
    active = tiny_archive(os.path.join(run, "Gw.dat"), [b"payload one" * 4])
    retail = tiny_archive(os.path.join(run, "Gw.dat.retail"),
                          [b"payload one" * 4])
    write(os.path.join(run, "Gw.exe"), "not really a client")
    vault = use_vault(os.path.join(tmp, "vault"))
    mdir = os.path.join(vault, "overlays")
    os.makedirs(mdir, exist_ok=True)
    m1 = manifest_at(os.path.join(mdir, "slowmo.toml"), "slowmo", active,
                     retail, b"a different payload")
    m2 = manifest_at(os.path.join(mdir, "fastmo.toml"), "fastmo", active,
                     retail, b"another payload")
    return {"run": run, "active": active, "retail": retail, "vault": vault,
            "m1": m1, "m2": m2, "captures": os.path.join(tmp, "caps")}


def flip_world(w, tmp, name, exes=("Gw.exe",), record_format=None):
    """A run dir whose ACTIVE differs from its RETAIL, so a flip is VISIBLE.

    `build_world`'s two archives are byte-identical, which is fine for
    everything that reads them and useless for asking whether a refusal fired
    before or after a whole-file copy: the copy would leave the file the same.
    Here retail and active carry different payloads, so the archive's own
    checksum answers that question.
    """
    d = os.path.join(tmp, "flip", name)
    os.makedirs(d, exist_ok=True)
    retail = tiny_archive(os.path.join(d, "Gw.dat.retail"), [b"RETAIL" * 8])
    active = tiny_archive(os.path.join(d, "Gw.dat"), [b"ACTIVE" * 8])
    for exe in exes:
        write(os.path.join(d, exe), "not really a client")
    path = manifest_at(os.path.join(w["vault"], "overlays", f"{name}.toml"),
                       name, active, retail, b"a payload")
    build_record(overlay.load_manifest(path, echo=False),
                 format_=record_format)
    return {"dir": d, "active": active, "retail": retail, "manifest": path,
            "crc": sha_of(active)}


def drive_arm(w, name, out, lines, hold_polls=2, crash=None):
    """One arm from `start_arm` to `finalize`, with a scripted client. -> Arm."""
    man = overlay.load_manifest(w["m1"], echo=False)
    arm = abrun.Arm(name, "overlay", man, out, name, 0)
    abrun.start_arm(arm, 0.0, 5.0, 5.0)
    cap = os.path.join(w["captures"], f"2026-08-20_{name}")
    log = os.path.join(cap, "gamesrv.log")
    since = time.time()
    time.sleep(0.02)                    # the capture must be NEWER than the flip
    writes = {1: crlf(*lines[:1])} if lines else {}
    if len(lines) > 1:
        writes[2] = crlf(*lines[1:])
    states = [False, True] + [True] * hold_polls + [False]
    fake = FakeClient(states, log=log, writes=writes)
    with quiet():
        ok = abrun.observe(arm, 0.0, 5.0, 5.0, captures=w["captures"],
                           probe=fake, since=since, echo=False)
    if crash:
        write(os.path.join(cap, "crash-dialog.txt"), crash)
        abrun._harvest(arm, [abrun.Tail(log)], since, w["captures"])
    return arm, ok, fake


def section4(w, tmp):
    print("\n== section 4: an arm from deploy to finalise, with no client ==")
    out = os.path.join(tmp, "runA")
    lines = [ln for ln, _k, _f in LINES]
    arm, ok, fake = drive_arm(w, "slowmo", out, lines, crash=None)
    check(ok is True, "the arm saw a whole hold: open, then closed")
    check(arm.doc["counts"]["hit_agent"]["n"] == 1
          and arm.doc["counts"]["agent_casts"]["n"] == 1
          and arm.doc["log"]["lines"] == len(lines),
          f"and counted every one of the {len(lines)} lines the server wrote "
          f"DURING the hold, from a log it found itself",
          json.dumps({k: v["n"] for k, v in arm.doc["counts"].items()}))
    check(arm.doc["log"]["path"] and arm.doc["log"]["bytes"] > 0,
          "binding the capture it found", arm.doc["log"]["path"] or "none")
    check(arm.doc["hold_seconds"] is not None and arm.doc["polls"] >= 4,
          "and recorded how long the hold was and how many times it looked -- "
          "the counts mean nothing without the window they were taken over",
          f"{arm.doc['hold_seconds']}s over {arm.doc['polls']} polls")
    check(arm.doc["state"] == abrun.RUNNING and not arm.doc["finished"],
          "the arm is NOT finished until something scores it: observing is not "
          "finalising", arm.doc["state"])

    doc, why = abrun.read_json(arm.verdict_path, "verdict")
    check(doc and doc["counts"] == arm.doc["counts"],
          "and every poll's write is on disk and parses", why)

    arm2, _ok2, _f2 = drive_arm(
        w, "crashy", os.path.join(tmp, "runCrash"), lines[:2],
        crash="=== window 0x1\n--- control class=Static (40 chars)\n"
              "Assertion: m_seqCount != 0\nFile: Mdl.cpp(300)\n")
    check(arm2.doc["crash_dialog"]["present"] is True
          and arm2.doc["crash_dialog"]["assertion"] == "m_seqCount != 0",
          "a crash-dialog.txt beside the log is found and its ONE assert line "
          "is lifted out -- Gw.log does not record asserts, so a quiet log is "
          "not evidence of a quiet client",
          json.dumps(arm2.doc["crash_dialog"]))

    out2 = os.path.join(tmp, "runNever")
    man = overlay.load_manifest(w["m1"], echo=False)
    arm3 = abrun.Arm("never", "overlay", man, out2, "never", 1)
    abrun.start_arm(arm3, 0.0, 0.0, 5.0)
    with quiet():
        ok3 = abrun.observe(arm3, 0.0, 0.0, 5.0, captures=w["captures"],
                            probe=FakeClient([False]), since=time.time(),
                            echo=False)
    check(ok3 is False and arm3.doc["state"] == abrun.ABANDONED
          and "no client opened" in (arm3.doc["note"] or ""),
          "an arm nobody ever launched is ABANDONED and says so, and is never "
          "finished", arm3.doc["state"])
    doc, _ = abrun.read_json(arm3.verdict_path, "verdict")
    check(doc and doc["state"] == abrun.ABANDONED and not doc["finished"],
          "with that written down rather than left in memory")

    long_arm = abrun.Arm("stuck", "overlay", man,
                         os.path.join(tmp, "runStuck"), "stuck", 1)
    abrun.start_arm(long_arm, 0.0, 5.0, 0.0)
    with quiet():
        ok4 = abrun.observe(long_arm, 0.0, 5.0, 0.0, captures=w["captures"],
                            probe=FakeClient([True]), since=time.time(),
                            echo=False)
    check(ok4 is False and long_arm.doc["state"] == abrun.ABANDONED
          and "still held" in (long_arm.doc["note"] or ""),
          "and a client that never lets go is abandoned too, rather than "
          "counted forever", long_arm.doc["note"] or "")
    return arm


class TwoLogClient:
    """A hold that can write into TWO capture logs: the last arm's, and its own.

    The previous arm's stack does not stop when its client exits -- it relays
    until it is torn down and `capture_error_dialog` waits up to twelve seconds
    for a dialog (session.py:1184, 1234) -- so a line landing in the OLD log
    while this arm is flipping 4.2 GB is ordinary, not contrived. That line is
    the whole mechanism: it moves the old log's mtime past this arm's deploy.
    """

    def __init__(self, states, script):
        self.states = list(states)
        self.script = dict(script)      # poll index -> (log path, bytes)
        self.calls = 0

    def __call__(self, path):
        i = self.calls
        self.calls += 1
        if i in self.script:
            log, blob = self.script[i]
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "ab") as fh:
                fh.write(blob)
        return self.states[min(i, len(self.states) - 1)]


def section4b(w, tmp):
    print("\n== section 4b: an arm may never bind the arm before it ==")
    caps = os.path.join(tmp, "caps4b")
    prev_log = os.path.join(caps, "20260820T120000", "gamesrv.log")
    write(prev_log, "")
    with open(prev_log, "ab") as fh:
        fh.write(crlf(*["[c3] hit agent 41: 42/120"] * 30))
    check(os.path.getsize(prev_log) == 810,
          "the fixture: the previous arm's log holds 30 counted lines before "
          "this arm exists at all", f"{os.path.getsize(prev_log)} B")

    man = overlay.load_manifest(w["m1"], echo=False)
    own_log = os.path.join(caps, "20260820T130000", "gamesrv.log")
    teardown = (prev_log, crlf("[c3] connection closed"))

    def arm_of(name, script, known=None):
        arm = abrun.Arm(name, "overlay", man,
                        os.path.join(tmp, "run4b"), name, 1)
        abrun.start_arm(arm, 0.0, 5.0, 5.0)
        since = time.time()
        time.sleep(0.02)
        with quiet():
            ok = abrun.observe(arm, 0.0, 5.0, 5.0, captures=caps,
                               probe=TwoLogClient([False, True, True, False],
                                                  script),
                               since=since, known=known, echo=False)
        return arm, ok

    # THE POSITIVE CONTROL FIRST, and it is the defect itself: with an empty
    # census -- which is what binding on mtime alone amounts to -- one teardown
    # line hands this arm the whole of the previous arm's session.
    arm, ok = arm_of("bymtime", {1: teardown}, known=set())
    check(ok is True and arm.doc["counts"]["hit_agent"]["n"] == 30,
          "the control: told nothing existed before it, an arm binds the "
          "PREVIOUS capture on one teardown line and reads its log from byte "
          "zero -- 30 hits that belong to somebody else's session",
          json.dumps({k: v["n"] for k, v in arm.doc["counts"].items() if v["n"]}))

    arm, ok = arm_of("empty", {1: teardown})
    check(ok is True and arm.doc["log"]["path"] is None
          and arm.doc["counts"]["hit_agent"]["n"] == 0,
          "and with the census it takes for itself, the same arm binds NOTHING "
          "and counts zero: an arm with no capture of its own reports no "
          "evidence, which is a fact, rather than the last arm's",
          f"{arm.doc['log']['path']} / "
          f"{arm.doc['counts']['hit_agent']['n']} hits")
    check(arm.doc["log"]["captures_before"] == 1,
          "with the census's own size written into the verdict, so a reader "
          "can see what the arm ruled out", f"{arm.doc['log']}")

    arm, ok = arm_of("mine", {1: teardown,
                              2: (own_log, crlf("[c3] hit agent 41: 42/120"))})
    check(ok is True and arm.doc["log"]["capture_dir"] == os.path.dirname(
              own_log),
          "and when its OWN capture appears mid-hold it binds that one",
          arm.doc["log"]["capture_dir"] or "nothing")
    check(arm.doc["counts"]["hit_agent"]["n"] == 1
          and arm.doc["log"]["lines"] == 1,
          "counting its own single line and none of the previous arm's thirty "
          "-- the number that made this defect survive review is that 30 and 31 "
          "both look like a session",
          json.dumps({k: v["n"] for k, v in arm.doc["counts"].items() if v["n"]}))
    check(arm.doc["log"]["bytes_at_bind"] is not None
          and arm.doc["log"]["bound_at"],
          "and the verdict records what the log already held when it bound, "
          "because the failure this replaces produced a plausible count and "
          "nothing on the document said where the bytes came from",
          json.dumps(arm.doc["log"]))


# ---------------------------------------------------------------------------
# 5. scoring an archive the client may have broken
# ---------------------------------------------------------------------------

def section5(w, tmp):
    print("\n== section 5: a refusal on the way out is the RESULT ==")
    man = overlay.load_manifest(w["m1"], echo=False)
    arm = abrun.Arm("healthy", "overlay", man, os.path.join(tmp, "post"),
                    "healthy", 0)
    abrun.start_arm(arm, 0.0, 5.0, 5.0)
    post, blew = scored(abrun.post_checks, arm, echo=True)
    post = post or {}
    check(not blew and post.get("refused") is None and post.get("archive"),
          "a healthy archive clears the gate and its summary is recorded",
          blew or post.get("refused") or post.get("archive"))
    check(post.get("crc_bad") == 0 and (post.get("preflight_checks") or 0) >= 10,
          "with the ten open-time rules and the payload CRC sweep behind it",
          f"{post.get('preflight_checks')} rules, {post.get('crc_bad')} bad")
    check(post.get("state_after") is None
          and any("deployed_state" in n for n in post.get("notes") or []),
          "and overlay's own refusal -- there is no build record here -- is "
          "written into notes rather than ending the scorer",
          json.dumps(post.get("notes"))[:120])

    broken = os.path.join(tmp, "post", "broken.dat")
    tiny_archive(broken, [b"payload one" * 4])
    with open(broken, "r+b") as fh:
        fh.seek(0x0C)
        fh.write(b"\xDE\xAD\xBE\xEF")          # the header CRC, poked
    man2 = overlay.load_manifest(
        manifest_at(os.path.join(w["vault"], "overlays", "broke.toml"),
                    "broke", broken, w["retail"], b"payload"), echo=False)
    arm2 = abrun.Arm("broke", "overlay", man2, os.path.join(tmp, "post2"),
                     "broke", 1)
    abrun.start_arm(arm2, 0.0, 5.0, 5.0)
    post2, blew2 = scored(abrun.post_checks, arm2, echo=True)
    post2 = post2 or {}
    check(not blew2 and post2.get("refused")
          and "header CRC" in post2["refused"],
          "an archive whose header CRC no longer verifies is REFUSED by the "
          "gate, and the refusal is RECORDED rather than raised -- a launch "
          "gate that fires on the way OUT must not kill the scorer",
          blew2 or (post2.get("refused") or "it cleared")[:100])
    _fin, blew3 = scored(abrun.finalize, arm2, echo=True)
    check(not blew3 and arm2.doc["state"] == abrun.FINISHED
          and arm2.doc["finished"],
          "and the arm still FINALISES -- an archive the client damaged is the "
          "most interesting thing an arm can find, and a scorer that died on "
          "it would record nothing at all", blew3 or arm2.doc["state"])
    doc, why = abrun.read_json(arm2.verdict_path, "verdict")
    check(doc and (doc.get("post") or {}).get("refused")
          and doc.get("state") == abrun.FINISHED,
          "with the refusal on disk in the same document that says finished",
          why or json.dumps(doc.get("state") if doc else None))


# ---------------------------------------------------------------------------
# 6. resolving two arms, and refusing the ones that are not comparable
# ---------------------------------------------------------------------------

def section6(w, tmp):
    print("\n== section 6: what two arms may be ==")
    out = os.path.join(tmp, "resolve")
    os.makedirs(out, exist_ok=True)
    why = refusal(abrun.resolve_arms, "retail", "retail", out)
    check("both arms are `retail`" in why,
          "two retail arms are refused: they differ in nothing, so the result "
          "would measure how much a hand-driven session varies from itself",
          why[:70])

    same = manifest_at(os.path.join(w["vault"], "overlays", "twin.toml"),
                       "slowmo", w["active"], w["retail"], b"twin")
    why = refusal(abrun.resolve_arms, w["m1"], same, out)
    check("arm name 'slowmo'" in why and "directory" in why,
          "two manifests with one name are refused: the second arm's verdict "
          "would land on the first one's", why[:70])

    # THE COLLISION THAT LOOKS LIKE NO COLLISION. `overlay.NAME_RE` is
    # [a-z0-9-]+, so `retail` is a legal profile name -- and it is the name a
    # person gives a baseline profile.
    named = manifest_at(os.path.join(w["vault"], "overlays", "named.toml"),
                        "retail", w["active"], w["retail"], b"named retail")
    why = refusal(abrun.resolve_arms, "retail", named, out)
    check("arm name 'retail'" in why and "difference of zero" in why,
          "and a manifest legally NAMED `retail` collides with the literal "
          "`retail` arm exactly the same way: both arms would write one "
          "verdict, and the compare would print a perfect null it never "
          "measured", why[:80])

    other = tiny_archive(os.path.join(tmp, "elsewhere.dat"), [b"other"])
    lone = manifest_at(os.path.join(w["vault"], "overlays", "lone.toml"),
                       "lone", other, w["retail"], b"lone")
    why = refusal(abrun.resolve_arms, w["m1"], lone, out)
    check("different ACTIVE" in why,
          "two manifests naming different ACTIVE archives are refused: then "
          "the arms differ in the whole world, not in one declared thing",
          why[:70])

    why = refusal(abrun.resolve_arms, "retail", w["m1"], out)
    check("no build record" in why and "--build" in why,
          "a profile that was never built is refused BEFORE the operator is "
          "told to launch anything, and the remedy is named", why[:80])

    # From here on both manifests have a REAL build record, so resolution
    # reaches the end. A stub `{}` no longer gets this far, and that is the
    # point of the next check rather than an inconvenience.
    for path in (w["m1"], w["m2"]):
        build_record(overlay.load_manifest(path, echo=False))
    run, arms = abrun.resolve_arms("retail", w["m1"], out)
    check([a.name for a in arms] == ["retail", "slowmo"]
          and arms[0].kind == abrun.RETAIL_ARM
          and arms[0].manifest.path == arms[1].manifest.path,
          "a `retail` arm takes its archives from the OTHER arm's manifest: a "
          "baseline is a baseline OF something",
          f"{[a.name for a in arms]}")
    check(arms[0].expect == overlay.STATE_RETAIL
          and arms[1].expect == "slowmo",
          "and each arm knows what the ACTIVE archive must read as once it is "
          "deployed")
    check(run["format"] == abrun.RUN_FORMAT and len(run["arms"]) == 2
          and run["arms"][1]["manifest_sha256"],
          "the run record names both arms and pins the overlay arm's manifest "
          "by sha256")
    check(run["exe"] == os.path.join(w["run"], "Gw.exe")
          and arms[0].exe == run["exe"] and arms[1].exe == run["exe"],
          "and names the client both arms will be launched with, RESOLVED "
          "here: it is a directory listing, so there is no excuse for its "
          "refusal to arrive after a flip", f"{run['exe']}")

    # THE BUILD RECORD IS OPENED HERE, not merely stat'd. Its first reader used
    # to be `deployed_state`, after the flip.
    bad = manifest_at(os.path.join(w["vault"], "overlays", "badrec.toml"),
                      "badrec", w["active"], w["retail"], b"bad record")
    build_record(overlay.load_manifest(bad, echo=False), format_="not-ours")
    why = refusal(abrun.resolve_arms, "retail", bad, out)
    check("is not an overlay build record" in why,
          "a build record that is not one is refused at RESOLVE time -- "
          "checking only that the file exists left the first real read on the "
          "far side of a whole-file write of the shared archive", why[:90])

    gone = os.path.join(tmp, "gone")
    os.makedirs(gone, exist_ok=True)
    missing = manifest_at(os.path.join(w["vault"], "overlays", "missing.toml"),
                          "missing", os.path.join(gone, "Gw.dat"),
                          os.path.join(gone, "Gw.dat.retail"), b"x")
    why = refusal(abrun.resolve_arms, "retail", missing, out)
    check("ACTIVE archive is not there" in why,
          "an ACTIVE archive that is not on disk is refused before the first "
          "flip, not discovered after it", why[:70])

    check(abrun.client_exe(w["active"]) == os.path.join(w["run"], "Gw.exe"),
          "the client that opens an archive is the one BESIDE it: there is no "
          "-dat flag, so the run directory is the only true binding")
    argv = abrun.launch_command(abrun.Arm("x", "overlay",
                                          overlay.load_manifest(w["m1"],
                                                                echo=False),
                                          out, "x", 0))
    check("--exe" in argv and os.path.join(w["run"], "Gw.exe") in argv,
          "and the printed command spells --exe out: omitted, session.py takes "
          "the newest thing under vault/run, which is the defect this repo has "
          "shipped three times", " ".join(argv[-3:]))
    src = open(os.path.join(HERE, "session.py"), encoding="utf-8").read()
    flags = [a for a in argv if a.startswith("--")]
    unknown = [f for f in flags if f'"{f}"' not in src]
    check(not unknown,
          f"and every flag it prints ({', '.join(flags)}) is one session.py "
          f"actually defines", f"unknown: {unknown}")

    two = os.path.join(tmp, "twoexe")
    os.makedirs(two, exist_ok=True)
    tiny_archive(os.path.join(two, "Gw.dat"), [b"x"])
    write(os.path.join(two, "a-build.exe"), "one")
    write(os.path.join(two, "z-build.exe"), "two")
    why = refusal(abrun.client_exe, os.path.join(two, "Gw.dat"))
    check("is a GUESS" in why and "sorts last" in why,
          "a run directory with two candidate clients and no Gw.exe is "
          "REFUSED, never resolved by sorting -- picking the one that sorts "
          "last has chosen the wrong build three times", why[:70])

    # AND NOW THE HALF THAT MATTERS: not that the refusals exist, but that they
    # happen while the shared archive is still untouched. `resolve_arms`'s own
    # docstring promises it ("EVERY REFUSAL IN HERE HAPPENS BEFORE A BYTE IS
    # FLIPPED") and two of them used to fire on the far side of a whole-file
    # copy -- for an [overlay, retail] ordering, on the far side of a whole
    # hand-driven session as well.
    for label, kw, want in (
            ("an ambiguous run directory",
             {"exes": ("a-build.exe", "z-build.exe")}, "is a GUESS"),
            ("a build record that is not one",
             {"record_format": "not-ours"}, "is not an overlay build record")):
        fw = flip_world(w, tmp, "pre" + label.split()[-1], **kw)
        # THE TIMEOUTS ARE ZERO ON PURPOSE. A defect that lets one of these
        # refusals through does not fail here -- it reaches the wait, and on
        # the DEFAULT 900 s it hangs the whole file for a quarter of an hour
        # rather than going red. MEASURED while sabotaging exactly that.
        why = refusal(abrun.run, "retail", fw["manifest"],
                      os.path.join(tmp, "pre-" + label.split()[-1]), yes=True,
                      poll=0.0, wait_launch=0.0, max_hold=0.0)
        check(want in why and sha_of(fw["active"]) == fw["crc"],
              f"--run refuses {label} with the ACTIVE archive still "
              f"byte-for-byte what it was: nothing was flipped, and nobody was "
              f"told to launch anything",
              f"{why[:60]!r} / archive "
              f"{'unchanged' if sha_of(fw['active']) == fw['crc'] else 'REWRITTEN'}")


# ---------------------------------------------------------------------------
# 7. the compare table and the CLI
# ---------------------------------------------------------------------------

def section7(w, tmp):
    print("\n== section 7: the differential table ==")
    out = os.path.join(tmp, "compare")
    os.makedirs(out, exist_ok=True)
    man = overlay.load_manifest(w["m1"], echo=False)
    build_record(man)
    run, arms = abrun.resolve_arms("retail", w["m1"], out)
    abrun.write_json_atomic(os.path.join(out, "abrun.json"), run)

    lines = [ln for ln, _k, _f in LINES]
    for arm, howmany in ((arms[0], 1), (arms[1], len(lines))):
        cap = os.path.join(w["captures"], f"cmp-{arm.name}")
        log = os.path.join(cap, "gamesrv.log")
        abrun.start_arm(arm, 0.0, 5.0, 5.0)
        since = time.time()
        time.sleep(0.02)
        fake = FakeClient([False, True, True, False], log=log,
                          writes={1: crlf(*lines[:howmany])})
        with quiet():
            abrun.observe(arm, 0.0, 5.0, 5.0, captures=w["captures"],
                          probe=fake, since=since, echo=False)
            abrun.finalize(arm, echo=False)

    rc, table = abrun.compare_lines(out)
    text = "\n".join(table)
    check(rc == 0,
          "two finalised arms compare with exit 0 EVEN THOUGH they differ: a "
          "difference is a result, not an error", f"rc {rc}")
    check("retail" in text and "slowmo" in text and "hit_agent" in text,
          "and the table names both arms and every counter")
    casts = [ln for ln in table if ln.strip().startswith("agent_casts")]
    read = [ln for ln in table if "log lines read" in ln]
    check(casts and casts[0].rstrip().endswith("+1")
          and read and read[0].rstrip().endswith("+6"),
          "with the difference in every row spelled out: the arm that saw one "
          "line and the arm that saw seven differ by six, and by one cast",
          f"{casts[:1]} {read[:1]}")
    check("normalised per second" in text and "hold, seconds" in text,
          "and it says, every time it prints, that neither arm's duration was "
          "controlled and that no count is normalised -- a row that differs is "
          "a question, not an answer")
    bound = [ln for ln in table if "capture bound" in ln]
    check(bound and "cmp-retail" in bound[0] and "cmp-slowmo" in bound[0],
          "and it prints WHICH capture each column was counted out of, on the "
          "face of the table -- two arms showing one directory is the shape of "
          "an arm that read the previous session, and it is invisible in the "
          "counters", f"{bound[:1]}")

    # ONE CAPTURE CANNOT BE TWO ARMS, and both arms are `finished`, so nothing
    # else in this table has anything to say about it.
    for arm in arms:
        d, _why = abrun.read_json(arm.verdict_path, "verdict")
        d["log"]["capture_dir"] = os.path.join(w["captures"], "cmp-retail")
        abrun.write_json_atomic(arm.verdict_path, d)
    rc, table = abrun.compare_lines(out)
    check(rc == 1 and "BOTH ARMS BOUND THE SAME CAPTURE" in "\n".join(table),
          "two finalised arms that bound ONE capture are torn evidence and "
          "exit 1: every count on one side was read out of the other side's "
          "session, and nothing above that line would have said so", f"rc {rc}")

    # A run record whose two arms name one verdict file -- what an older build
    # wrote before the arm names were compared, and what a hand-edited record
    # can still say.
    collide = os.path.join(tmp, "collide")
    os.makedirs(os.path.join(collide, "retail"), exist_ok=True)
    rec = dict(run)
    rec["arms"] = [dict(a, name="retail",
                        verdict=os.path.join("retail", "verdict.json"))
                   for a in run["arms"]]
    abrun.write_json_atomic(os.path.join(collide, "abrun.json"), rec)
    d, _why = abrun.read_json(arms[0].verdict_path, "verdict")
    abrun.write_json_atomic(os.path.join(collide, "retail", "verdict.json"), d)
    rc, table = abrun.compare_lines(collide)
    check(rc == 1 and "one verdict read twice" in "\n".join(table),
          "and a run record whose two arms name ONE verdict file is refused "
          "rather than read twice -- an arm against itself prints every row "
          "`same` and exits 0, which is the worst answer this tool can give",
          f"rc {rc}")

    doc, _ = abrun.read_json(arms[1].verdict_path, "verdict")
    doc["state"] = abrun.INTERRUPTED
    doc["note"] = "the operator closed the terminal"
    abrun.write_json_atomic(arms[1].verdict_path, doc)
    rc, table = abrun.compare_lines(out)
    text = "\n".join(table)
    check(rc == 1 and "missing or torn" in text and "interrupted" in text,
          "an arm that did not finalise makes the compare exit 1 and say which "
          "arm and why -- a torn arm is not a null result", f"rc {rc}")
    check("not a null result" in text,
          "and says so in as many words, because a zero and an unmeasured arm "
          "print the same otherwise")

    os.remove(arms[1].verdict_path)
    rc, _t = abrun.compare_lines(out)
    check(rc == 1, "a verdict that is not there is the same finding", f"rc {rc}")
    rc, table = abrun.compare_lines(os.path.join(tmp, "nowhere"))
    check(rc == 1 and "no run record" in "\n".join(table),
          "and so is a directory that was never a run", f"rc {rc}")

    with quiet() as buf:
        rc = abrun.main(["--compare", out])
    check(rc == 1 and "CANNOT COMPARE" in buf.getvalue(),
          "the CLI carries that verdict out as exit 1", f"rc {rc}")
    with quiet() as buf:
        rc = abrun.main(["--run", "retail", w["m1"], "--out",
                         os.path.join(tmp, "unyes")])
    check(rc == 2 and "--yes" in buf.getvalue(),
          "--run without --yes writes nothing and exits 2: it overwrites the "
          "shared ACTIVE archive twice", f"rc {rc}")
    check(not os.path.exists(os.path.join(tmp, "unyes", "abrun.json")),
          "and really wrote nothing")

    why = refusal(abrun.prepare_out, out)
    check("already there" in why,
          "a second run into a directory that already holds one is refused: "
          "evidence overwritten in place is evidence nobody can audit",
          why[:70])
    why = refusal(abrun.prepare_out, r"C:\gw\abrun")
    check("live install" in why,
          "and the owner's install is refused as an output directory")


# ---------------------------------------------------------------------------
# 8. two arms, for real: real archives, real deploys, real premises
# ---------------------------------------------------------------------------

def real_world(tmp):
    """test_overlay's own fixture, with two profiles built over ONE row."""
    root = os.path.join(tmp, "real")
    os.makedirs(root, exist_ok=True)
    w = TO.World(root)                      # repoints RURIK_VAULT at real/vault
    write(os.path.join(w.run, "Gw.exe"), "not really a client")
    w.payload("alpha.bin", b"A" * 100)
    w.payload("beta.bin", b"B" * 100)
    specs = {}
    idx = w.index()
    for name in ("alpha", "beta"):
        specs[name] = w.manifest(
            name, [TO.toml_edit(TO.FID_D, plain=f"payloads/{name}.bin")])
        with quiet():
            overlay.build(overlay.load_manifest(specs[name], echo=False),
                          index=idx, echo=False)
    return w, specs


def two_arm_client(caproot, lines_a, lines_b):
    """One scripted operator for a WHOLE run: four polls per arm, two captures.

    The poll indices are deterministic because `run_arm` probes the archive's
    hold through the real `client_holds` and only the WAIT goes through this --
    four calls an arm, and the second of each set is where that arm's capture
    directory appears.
    """
    a = os.path.join(caproot, "20260820T140000", "gamesrv.log")
    b = os.path.join(caproot, "20260820T150000", "gamesrv.log")
    return TwoLogClient([False, True, True, False] * 2,
                        {1: (a, crlf(*lines_a)), 5: (b, crlf(*lines_b))})


def section8(tmp):
    print("\n== section 8: two arms end to end, against real archives ==")
    w, specs = real_world(tmp)
    caproot = os.path.join(tmp, "real", "caps")
    lines_a = ["[c3] hit agent 41: 42/120"]
    lines_b = ["[c3] hit agent 41: 42/120", "[c3] hit agent 41: 30/120",
               "[c3] agent 41 (Skale) casts skill 1234 (slot 2 of 8)"]

    out = os.path.join(tmp, "real", "ab")
    rc, blew = scored(abrun.run, specs["alpha"], specs["beta"], out, yes=True,
                      poll=0.0, wait_launch=5.0, max_hold=5.0,
                      captures=caproot,
                      probe=two_arm_client(caproot, lines_a, lines_b),
                      echo=True)
    check(rc == 0 and not blew,
          "TWO OVERLAY ARMS OWNING THE SAME ROW RUN TO COMPLETION: the natural "
          "A/B shape. It used to play arm 1 to a finished verdict and then "
          "refuse arm 2 for 'neither retail nor beta' -- a whole hand-driven "
          "session spent to say the pair was never comparable",
          blew or f"rc {rc}")
    va, _why = abrun.read_json(os.path.join(out, "alpha", "verdict.json"), "v")
    vb, _why = abrun.read_json(os.path.join(out, "beta", "verdict.json"), "v")
    va, vb = va or {}, vb or {}
    check(va.get("state") == abrun.FINISHED and vb.get("state") == abrun.FINISHED,
          "both arms finalised", f"{va.get('state')} / {vb.get('state')}")
    check(va.get("state_before") == "alpha" and vb.get("state_before") == "beta",
          "and each one's ACTIVE archive READ AS its own profile at launch "
          "time, which is the thing the second arm could not reach",
          f"{va.get('state_before')} / {vb.get('state_before')}")
    check(va.get("baseline_restored") is None
          and (vb.get("baseline_restored") or {}).get("undid") == "alpha",
          "with the RETAIL restore recorded in the SECOND arm's verdict and "
          "named for the deploy it undid -- a whole-file write of a shared "
          "archive is not something to do quietly",
          json.dumps(vb.get("baseline_restored")))
    check(va["log"]["capture_dir"] != vb["log"]["capture_dir"]
          and va["counts"]["hit_agent"]["n"] == 1
          and vb["counts"]["hit_agent"]["n"] == 2,
          "the two arms bound two DIFFERENT captures and counted only their "
          "own lines",
          f"{va['counts']['hit_agent']['n']} vs "
          f"{vb['counts']['hit_agent']['n']}")
    crc, table = abrun.compare_lines(out)
    check(crc == 0 and "difference" in "\n".join(table),
          "and the differential table prints, exit 0, on a real difference",
          f"rc {crc}")

    # AND THE ORDERING THAT NEEDS NO RESTORE: after a `retail` arm the archive
    # IS the baseline, and a second copy of 4.2 GB would buy nothing. Note that
    # ACTIVE is left carrying `beta` from the run above -- which is exactly the
    # unknown state `--retail` exists to resolve, so nothing is reset here.
    out2 = os.path.join(tmp, "real", "ab2")
    rc, blew = scored(abrun.run, "retail", specs["alpha"], out2, yes=True,
                      poll=0.0, wait_launch=5.0, max_hold=5.0,
                      captures=caproot,
                      probe=two_arm_client(os.path.join(caproot, "second"),
                                           lines_a, lines_b),
                      echo=True)
    vr, _why = abrun.read_json(os.path.join(out2, "retail", "verdict.json"), "v")
    va2, _why = abrun.read_json(os.path.join(out2, "alpha", "verdict.json"), "v")
    vr, va2 = vr or {}, va2 or {}
    check(rc == 0 and vr.get("state_before") == overlay.STATE_RETAIL
          and va2.get("state_before") == "alpha",
          "a [retail, overlay] pair runs from an ACTIVE archive left carrying "
          "the PREVIOUS run's profile: --retail takes no premise, because its "
          "whole job is to make an unknown archive known",
          blew or f"rc {rc}, {vr.get('state_before')} / "
                  f"{va2.get('state_before')}")
    check(va2.get("baseline_restored") is None,
          "and no restore is taken between them -- after a `retail` arm the "
          "baseline is already what ACTIVE holds",
          json.dumps(va2.get("baseline_restored")))


def main():
    was = os.environ.get("RURIK_VAULT")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            # BEFORE THE FIRST SECTION, not before the first section that needs
            # it. `require_dir` resolving to the real vault would make a fixture
            # that silently pointed at somebody's captures, and a fixture that
            # resolves to the wrong thing turns every assertion behind it into a
            # no-op (vaultpath.py's own reasoning).
            use_vault(os.path.join(tmp, "vault"))
            section0()
            section1(tmp)
            section2(tmp)
            section3(tmp)
            w = build_world(tmp)
            section4(w, tmp)
            section4b(w, tmp)
            section5(w, tmp)
            section6(w, tmp)
            section7(w, tmp)
            # LAST, because it repoints the vault at its own fixture: World
            # takes RURIK_VAULT for itself and every section above reads the
            # one `build_world` made.
            section8(tmp)
    finally:
        if was is None:
            os.environ.pop("RURIK_VAULT", None)
        else:
            os.environ["RURIK_VAULT"] = was
        vaultpath._resolved = None
    sys.exit(LEDGER.verdict())


if __name__ == "__main__":
    main()
