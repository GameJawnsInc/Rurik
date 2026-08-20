"""Prove the delta by reconstituting from it, and by breaking it on purpose.

`datdelta.py` exists so a 4.2 GB staged archive can be deleted. That makes it a
tool whose failure mode is silent and permanent: a delta that reconstitutes to
*almost* the staged archive is a delta nobody discovers is wrong until the
original is gone. So every section here ends at a whole-file sha256 -- the same
gate the module itself uses -- and the refusal sections check the TARGET as well
as the message, because a refusal that arrives after the write has already
happened has not refused anything.

WHAT IT RUNS AGAINST. Files it writes into a temp directory, and `RURIK_VAULT`
pointed at another temp directory, so the store guard is exercised for real
rather than skipped. It never opens `vault/`, never reads `C:\\gw`, never needs
a corpus -- the floor below is a real floor and not a corpus-shaped hope.

Most sections use plain byte strings rather than archives, because the span
logic is size-agnostic and a 400-byte fixture makes the arithmetic checkable by
hand. Section 8 is the exception: it builds a real 14 KB archive (the fixture is
cribbed from `test_datalloc.py`, minus the parts only an allocator needs) so the
MFT-row annotation runs against a table that actually exists.

THREE SABOTAGES LIVE IN THE FILE, because three of this module's guards cannot
be reached in normal operation and an unreachable guard is a wish:

  * `prove()` hashes the reconstituted copy ITSELF rather than believing
    `apply()`'s report. In a healthy run that check can never fail, since
    `apply` refuses on the same comparison first -- so section 9 stubs `apply`
    out and requires `prove` to say NOT PROVEN anyway.
  * `apply`'s write loop refuses a blob that runs out mid-span. With
    `_verify_blobs` sizing every span that cannot happen, so section 4 stubs
    `_verify_blobs` down to a sha -> path map -- which is what it amounted to
    for the second span naming an already-cleared blob -- and the loop has to
    stop by itself. It used to spin there for ever.
  * the 256 MiB difference cap would need a 512 MiB fixture to reach honestly,
    which is I/O the suite should not pay on every run. Section 5 tightens the
    constant instead, and exercises the SPAN cap for real -- 4,100 genuine
    spans, which cost 266,500 bytes of fixture.

Fourteen more were applied to `datdelta.py` by source surgery and reverted;
their measured reds, and what the weak ones say, are in the comment above
`LEDGER`.

TWO CALLS RUN ON A DEADLINE (`bounded_refusal`), and that is not belt-and-braces
either: the defect they cover was a hang, and a test that hangs on a defect has
reported nothing at all -- the suite stops and the operator gets a cursor
instead of a name.

    python toolkit/mapdata/test_datdelta.py
"""

import binascii
import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import ENTRY_SIZE                          # noqa: E402
import datdelta                                         # noqa: E402
import vaultpath                                        # noqa: E402
import checks                                           # noqa: E402

# FLOOR: 84, MEASURED from a green run on 2026-08-20, not guessed. Per section,
# counted from the log rather than predicted: {1: 9, 2: 10, 3: 6, 4: 19, 5: 5,
# 6: 13, 7: 6, 8: 6, 9: 5, 10: 5}. Nothing here can legitimately skip -- every
# fixture is built in a temp directory and the vault is one too, so there is no
# corpus to be missing.
#
# SABOTAGES, applied one at a time to `datdelta.py` by source surgery and then
# reverted (the file was restored from its own bytes and the restore verified by
# sha256). These are the counts OBSERVED, not predicted, and the whole table was
# RE-MEASURED after the three defects below were fixed -- an old count against
# new code is not a measurement of anything:
#
#   `_verify_blobs` stops sizing and hashing (paths only)         9 checks red
#   the tail span past min(size) is dropped                       8 checks red
#   `_refuse_clobber` is not called                               5 checks red
#   `_verify_blobs`'s LENGTH check alone is disabled              5 checks red
#   `_verify_blobs` dedupes the CHECK and not just the hash       4 checks red
#   drop the SOURCE-hash check from `apply`                       4 checks red
#   drop the final DESTINATION-hash check from `apply`            3 checks red
#   `_check_span_table` returns immediately                       3 checks red
#   `apply`'s write loop drops its spent-blob guard               2 checks red
#   `_merge` stops merging                                        2 checks red
#   `resolve_store` allows anywhere outside dat_study/C:\gw       2 checks red
#   `manifest_path` falls back to `sorted(...)[-1]`               1 check  red
#   `apply` stops truncating to the destination size              1 check  red
#   `_stash` re-writes an existing blob instead of reusing it     1 check  red
#
# THREE OF THOSE ROWS ARE NEW, AND SO IS THIS FILE'S REASON FOR TRUSTING THE
# OTHERS. A skeptic pass found three defects that had walked past the version of
# this file that scored the first ten counts, and each one is now a row above:
#
#   * `_verify_blobs` deduped by sha BEFORE checking the length, so only the
#     FIRST span naming a blob was sized. Two spans naming one blob is the
#     dedupe this tool advertises, and a table where they declare different
#     lengths reached `apply`'s write loop, which then spun for ever on a spent
#     file handle with the target open "r+b" and half written. MEASURED against
#     the unfixed module in a subprocess: `timeout 20` killed it, still running.
#     A hang is not a refusal, and this module's contract is that everything
#     wrong is one.
#   * `capture` overwrote an existing manifest of the same name in silence. The
#     default name is a basename stem, so `run/Gw.dat` and `run-live/Gw.dat` are
#     both `gw` -- and the span table an overwrite destroys is the thing that
#     licenses deleting a 4.2 GB archive.
#   * the check labelled "a blob whose length no longer matches its span"
#     tampered a 6 B blob with 6 B of different bytes, so it fired the HASH
#     branch and the length branch had NO coverage. The decisive measurement:
#     `if False and size != length:` left this file green at 74 PASS, 0 FAIL.
#     That is the shape this repo calls a check that cannot fail, and it was
#     sitting inside a section named for catching exactly that.
#
# THE MEASUREMENT ITSELF HAD A DEFECT WORTH RECORDING. Several of these
# sabotages add exactly `False and ` -- ten characters -- so the sabotaged
# sources are the same SIZE as each other, and CPython invalidates a cached
# `.pyc` on (mtime, size). Consecutive sweeps disagreed: the tail-span sabotage
# scored 8 red in one and 2 in the next, because the second run had imported the
# previous sabotage's bytecode. Re-measured with `-B` and
# `PYTHONDONTWRITEBYTECODE=1`, three runs each, identical every time. A sabotage
# count taken without that is not a measurement of the code on disk.
#
# Three readings worth keeping rather than tidying away.
#
# The DESTINATION hash is this module's one irreducible gate and it started at
# ONE red, which is a poor showing for the check that decides whether a 4.2 GB
# archive may be deleted. Section 4 now drives three separate shapes through it
# -- a span shifted within range, a span whose two sides are swapped, and a span
# table emptied -- because all three are structurally flawless and only the
# output hash can tell. That is where 1 became 3.
#
# `apply stops truncating` scored 0 red and a HARD STOP before section 3 was
# rewritten. A bare `datdelta.apply(...)` turns a broken apply into an uncaught
# SystemExit: loud, and nameless. Routing both applies through `refusal()` and
# asserting `m is None` converts the same defect into a named `[FAIL]`, which is
# the difference between a test that reports and a test that dies.
#
# `_stash` reddens ONE check and the label says exactly what was broken: the
# reuse, not the addressing. Re-writing an existing blob still lands the same
# bytes under the same sha256 name, so the store is correct and only the
# written/reused counters move. Claiming this sabotage proves content-addressing
# would be claiming more than the red says.
LEDGER = checks.Ledger("dat delta", floor=84)
check = checks.adopt(LEDGER)

ENTRY_CRC = 0x14        # offset of the crc inside a 24-byte MFT row


# ------------------------------------------------------------------ plumbing

@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def use_vault(path):
    """Point the vault at `path` for the rest of the run.

    `vaultpath` memoizes its answer in a module global on the first call
    (vaultpath.py:37), so setting the environment variable alone is not enough
    once anything has resolved -- the memo has to be dropped with it. Reaching
    into a private name is not a habit worth spreading; it is done here because
    the alternative is a test whose store guard never runs against a vault it
    controls.
    """
    os.makedirs(path, exist_ok=True)
    os.environ["RURIK_VAULT"] = path
    vaultpath._resolved = None
    return path


def spill(path, data):
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def blob(path):
    with open(path, "rb") as fh:
        return fh.read()


def line_of(text, n=0, want=None, default="-- nothing was printed"):
    """The n-th line of `text` (or of the lines containing `want`). Never raises.

    A detail expression that raises turns a named `[FAIL]` into a nameless
    crash, and a test that only crashes has told you the machine is unhappy
    rather than what broke. MEASURED here: three of the sabotages below
    hard-stopped inside a `.splitlines()[0]` before this existed, scoring 0 red
    against defects the check right beside them had already caught.
    """
    lines = [ln for ln in (text or "").splitlines() if want is None or want in ln]
    return (lines[n] if len(lines) > n else default).strip()[:70]


def refusal(fn, *a, **kw):
    """Run and return the refusal text, or None if it did not refuse."""
    try:
        with quiet():
            fn(*a, **kw)
    except SystemExit as exc:
        return str(exc)
    return None


BOUNDED_SECONDS = 10.0


def bounded_refusal(fn, *a, **kw):
    """`refusal()` for a call whose BROKEN form is a hang rather than a return.

    Two checks in section 4 drive `apply` at a manifest that used to spin it
    for ever: `read()` past the end of a blob returns b"" for as long as anyone
    asks, so the write loop's `left` never moved and the target sat open "r+b"
    and half written. MEASURED against the unfixed module with a subprocess and
    `timeout 20`: killed, still spinning.

    A test that HANGS on a defect has not reported it. The suite stops, nothing
    after this file runs, and the operator gets a cursor instead of a name -- the
    same failure `line_of` exists to prevent, one step worse. So these two calls
    run on a daemon thread with a join deadline, and a thread still alive at the
    deadline returns a string that no check's substring matches: a named [FAIL],
    with the process still able to exit.

    Deliberately NOT routed through `refusal()`: `quiet()` redirects the
    process-wide `sys.stdout`, so a thread hung inside it would swallow every
    line this file prints afterwards. `apply` prints nothing of its own.
    """
    got = []

    def body():
        try:
            fn(*a, **kw)
            got.append(None)
        except SystemExit as exc:
            got.append(str(exc))
        except BaseException as exc:                        # noqa: BLE001
            got.append(f"{type(exc).__name__}: {exc}")

    worker = threading.Thread(target=body, daemon=True)
    worker.start()
    worker.join(BOUNDED_SECONDS)
    if not got:
        return (f"-- STILL RUNNING after {BOUNDED_SECONDS:.0f} s, which is the "
                f"hang this check exists for")
    return got[0]


def run_cli(argv):
    """`datdelta._main(argv)` with both streams captured. -> (rc, out, err).

    `_main` prints its refusals to STDERR before returning 2, so a test that
    only redirects stdout reads a refusal as silence.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = datdelta._main(argv)
    return rc, out.getvalue(), err.getvalue()


def noise(seed, n):
    """Deterministic bytes with no structure. No `random` seed to drift."""
    out = bytearray(n)
    x = (seed * 2654435761) & 0xFFFFFFFF
    for i in range(n):
        x = (x * 1103515245 + 12345) & 0xFFFFFFFF
        out[i] = (x >> 16) & 0xFF
    return bytes(out)


def pair(tmp, tag, retail_bytes, edits, grow=b""):
    """(retail path, staged path). `edits` is {offset: bytes}."""
    r = spill(os.path.join(tmp, tag + ".retail"), retail_bytes)
    buf = bytearray(retail_bytes)
    for off, data in edits.items():
        buf[off:off + len(data)] = data
    s = spill(os.path.join(tmp, tag + ".staged"), bytes(buf) + grow)
    return r, s


# ------------------------------------------------------- 1. the span finder

def section_spans(tmp):
    print("\n1. the span table, against arithmetic done by hand")
    base = bytes(400)

    b = bytearray(base)
    b[10] = 1
    b[20] = 1                       # 9 zeros apart: one span
    b[200] = 1                      # 179 apart: its own span
    got = datdelta._differing_runs(base, bytes(b), 64)
    check(got == [(10, 11), (200, 1)],
          "two differences 9 B apart are ONE span; one 179 B away is another",
          f"{got}")

    b = bytearray(base)
    b[10] = 1
    b[10 + 1 + 63] = 1              # exactly 63 zeros between
    got = datdelta._differing_runs(base, bytes(b), 64)
    check(got == [(10, 65)], "63 B of agreement between two differences merges",
          f"{got}")

    b = bytearray(base)
    b[10] = 1
    b[10 + 1 + 64] = 1              # exactly 64 zeros between
    got = datdelta._differing_runs(base, bytes(b), 64)
    check(got == [(10, 1), (75, 1)], "64 B of agreement splits them",
          f"{got}  (the merge gap is {datdelta.MERGE_GAP} B)")

    check(datdelta._differing_runs(base, base, 64) == [],
          "two identical buffers have no differing runs")

    # A difference straddling a chunk seam must not be reported as two. This is
    # the one bug a per-chunk scan is born with, and the final merge is what
    # closes it -- so the fixture puts a byte either side of the boundary.
    r, s = pair(tmp, "seam", bytes(4096), {511: b"\x03\x04"})
    got = datdelta.diff_spans(s, r, chunk=512)
    check(got == [(511, 2)], "a difference across a chunk seam is ONE span",
          f"{got} with chunk=512")

    r, s = pair(tmp, "same", noise(1, 900), {})
    check(datdelta.diff_spans(s, r) == [],
          "identical files produce no spans at all")

    r, s = pair(tmp, "grown", noise(2, 1000), {}, grow=noise(3, 137))
    got = datdelta.diff_spans(s, r)
    check(got == [(1000, 137)],
          "everything past min(size) is ONE span: the grown tail",
          f"{got}")

    r, s = pair(tmp, "grown2", noise(2, 1000), {990: b"\xff" * 10},
                grow=noise(3, 137))
    got = datdelta.diff_spans(s, r)
    check(got == [(990, 147)],
          "a difference reaching the old EOF merges with the grown tail",
          f"{got}")

    m = refusal(datdelta.diff_spans, s, r, datdelta.CHUNK, 0)
    check(m and "cannot separate" in m,
          "a merge gap of 0 is refused rather than silently merging everything",
          line_of(m, default="-- it did not refuse"))


# ------------------------------------------------- 2. capture, apply, return

def section_roundtrip(tmp, vault):
    print("\n2. capture -> apply -> the same bytes, both directions")
    store = os.path.join(vault, "store2")
    r, s = pair(tmp, "rt", noise(4, 5000),
                {100: b"CHANGED-EARLY", 3000: noise(5, 40)})
    retail_bytes, staged_bytes = blob(r), blob(s)

    doc = datdelta.capture(s, r, store, name="rt")
    check(doc["totals"]["spans"] == 2 and len(doc["spans"]) == 2,
          "two edits 2,900 B apart capture as two spans",
          f"{[ (sp['offset'], sp['length']) for sp in doc['spans'] ]}")
    check(doc["spans"][0]["offset"] == 100 and doc["spans"][0]["length"] == 13,
          "the first span is exactly the 13 bytes that were overwritten")
    check(doc["staged"]["sha256"] != doc["retail"]["sha256"]
          and doc["staged"]["size"] == doc["retail"]["size"] == 5000,
          "both identities are recorded, and they differ")

    man = os.path.join(store, "rt.delta.json")
    check(os.path.isfile(man), "the manifest lands as <name>.delta.json", man)
    with open(man, "r", encoding="utf-8") as fh:
        on_disk = json.load(fh)
    check(on_disk["spans"] == doc["spans"]
          and on_disk["format"] == "rurik-datdelta",
          "and what is on disk is what capture returned")
    blobs = sorted(os.listdir(os.path.join(store, "blobs")))
    check(len(blobs) == 4 and all(b.endswith(".bin") for b in blobs),
          "four blobs: both sides of both spans, named by their own sha256",
          f"{[b[:12] for b in blobs]}")

    # retail -> staged
    target = spill(os.path.join(tmp, "rt.target"), retail_bytes)
    rep = datdelta.apply(store, target, "staged")
    check(blob(target) == staged_bytes,
          "a copy of retail reconstitutes to the staged archive, byte for byte")
    check(rep["sha256"] == doc["staged"]["sha256"] and rep["bytes_written"] == 53,
          "and the report says so: 13 + 40 B written",
          f"{rep['bytes_written']} B, {rep['sha256'][:16]}...")

    # staged -> retail, from the same store
    back = datdelta.apply(store, target, "retail")
    check(blob(target) == retail_bytes,
          "and back again: the same store puts retail back on top of it")
    check(back["direction"] == "retail" and back["size"] == 5000,
          "a delta is two-way by construction; the staged copy is not needed "
          "to go either direction")


# ------------------------------------------------------- 3. the grown tail

def section_grown(tmp, vault):
    print("\n3. a staged archive that GREW")
    store = os.path.join(vault, "store3")
    r, s = pair(tmp, "grow", noise(6, 2048), {8: b"\x01\x02\x03\x04"},
                grow=noise(7, 700))
    retail_bytes, staged_bytes = blob(r), blob(s)
    doc = datdelta.capture(s, r, store, name="grow")
    tail = doc["spans"][-1]
    check(tail["offset"] == 2048 and tail["length"] == 700,
          "the tail past retail's EOF is one span",
          f"0x{tail['offset']:X} + {tail['length']}")
    check(tail["retail"]["length"] == 0 and tail["staged"]["length"] == 700,
          "its retail side is ZERO bytes long -- there is nothing there to keep")

    # Both applies go through `refusal()` even though neither should refuse.
    # A bare call would turn a broken apply into an uncaught SystemExit, which
    # kills the run with a loud, NAMELESS message -- measured: dropping the
    # truncate scored 0 red and a hard stop before this was written.
    target = spill(os.path.join(tmp, "grow.target"), retail_bytes)
    m = refusal(datdelta.apply, store, target, "staged")
    check(m is None and blob(target) == staged_bytes
          and os.path.getsize(target) == 2748,
          "reconstituting forwards GROWS the file to the staged size",
          line_of(m, default="-- it did not refuse, which is right"))
    m = refusal(datdelta.apply, store, target, "retail")
    check(m is None and blob(target) == retail_bytes
          and os.path.getsize(target) == 2048,
          "and reconstituting back TRUNCATES it to the retail size",
          line_of(m, default="the destination size is a recorded fact"))

    empty_sha = datdelta.sha256_file(
        spill(os.path.join(tmp, "empty"), b""))
    check(tail["retail"]["sha256"] == empty_sha,
          "the zero-length side is content-addressed like any other blob")
    check(os.path.isfile(os.path.join(store, "blobs", empty_sha + ".bin")),
          "and it is really in the store, 0 B, rather than a special case")


# -------------------------------------------------------- 4. the refusals

def section_refusals(tmp, vault):
    print("\n4. every way a delta can be wrong, and the target afterwards")
    store = os.path.join(vault, "store4")
    r, s = pair(tmp, "ref", noise(8, 3000), {1500: b"EDITED"})
    retail_bytes, staged_bytes = blob(r), blob(s)
    doc = datdelta.capture(s, r, store, name="ref")

    m = refusal(datdelta.apply, store, os.path.join(tmp, "ref.target"), "sideways")
    check(m and "neither 'staged' nor 'retail'" in m,
          "a direction that is not one of the two generations is refused",
          line_of(m, default="-- it did not refuse"))

    other = spill(os.path.join(tmp, "unrelated"), noise(9, 3000))
    m = refusal(datdelta.apply, store, other, "staged")
    check(m and doc["retail"]["sha256"] in m,
          "an archive that is neither generation is refused, naming the hash "
          "the delta was cut from",
          line_of(m, 1, default="-- it did not refuse"))
    check(blob(other) == noise(9, 3000),
          "and it is untouched -- the source hash is checked before the open")

    already = spill(os.path.join(tmp, "already"), staged_bytes)
    m = refusal(datdelta.apply, store, already, "staged")
    check(m and "ALREADY the staged generation" in m and "--direction retail" in m,
          "a target that is already the destination says so, and names the "
          "flag that goes the other way")

    # A tampered blob. The whole store is verified BEFORE the target is opened,
    # so the check that matters here is that the target did not move.
    target = spill(os.path.join(tmp, "ref.target"), retail_bytes)
    victim = os.path.join(store, "blobs",
                          doc["spans"][0]["staged"]["sha256"] + ".bin")
    was = blob(victim)
    # FIVE bytes, not six. This tamper used to be b"WRONG!" -- the right length
    # and the wrong bytes -- so it fired the HASH branch, identically to the
    # check immediately below it, and the `size != length` branch beside it had
    # no coverage at all. MEASURED: disabling only the length check
    # (`if False and size != length:`) left the whole file green at 74 PASS, 0
    # FAIL. Two tampers, two branches, and the predicates now say which is which.
    spill(victim, b"WRONG")
    m = refusal(datdelta.apply, store, target, "staged")
    check(m and "is 5 B" in m and "declares 6 B" in m
          and os.path.basename(victim)[:16] in m,
          "a blob whose LENGTH no longer matches its span is refused, by name "
          "and by both numbers",
          line_of(m, default="-- it did not refuse"))
    spill(victim, bytearray(was[:-1]) + bytes([was[-1] ^ 0xFF]))
    m = refusal(datdelta.apply, store, target, "staged")
    check(m and "hashes to" in m and "is filed under" in m,
          "a blob of the right LENGTH but the wrong bytes is refused too -- "
          "the store is content-addressed and the address is checked")
    check(blob(target) == retail_bytes,
          "and in both cases the target is byte-unchanged: nothing is written "
          "until every blob the direction needs has been read and hashed")
    spill(victim, was)

    # A doctored manifest. Two kinds: one the structural check catches before
    # the write, one it cannot -- which is what the destination hash is for.
    man = os.path.join(store, "ref.delta.json")
    good = blob(man)
    doctored = json.loads(good)
    doctored["spans"][0]["offset"] = 2999
    doctored["spans"][0]["length"] = 6
    spill(man, json.dumps(doctored).encode())
    m = refusal(datdelta.apply, store, target, "staged")
    check(m and "past the end" in m,
          "a span edited to run past both archives is refused before the write",
          line_of(m, default="-- it did not refuse"))
    check(blob(target) == retail_bytes, "target still untouched")

    doctored = json.loads(good)
    doctored["spans"][0]["offset"] = 1508      # still in range, still ordered
    spill(man, json.dumps(doctored).encode())
    m = refusal(datdelta.apply, store, target, "staged")
    check(m and "RECONSTITUTION FAILED" in m
          and doc["staged"]["sha256"] in m,
          "a span SHIFTED within range survives every cheap check and is "
          "refused by the destination hash -- the gate nothing can walk around",
          line_of(m, default="-- it did not refuse"))
    check(blob(target) != retail_bytes and blob(target) != staged_bytes,
          "and that refusal says the target is now NEITHER generation, because "
          "it is", "which is why the message names the file to delete")

    # Two more shapes the cheap checks cannot see, because the destination hash
    # is the only gate that can. Both sides of this span are 6 B, so swapping
    # which blob each names is structurally perfect and semantically backwards.
    doctored = json.loads(good)
    doctored["spans"][0]["staged"], doctored["spans"][0]["retail"] = \
        doctored["spans"][0]["retail"], doctored["spans"][0]["staged"]
    spill(man, json.dumps(doctored).encode())
    spill(target, retail_bytes)
    m = refusal(datdelta.apply, store, target, "staged")
    check(m and "RECONSTITUTION FAILED" in m,
          "a span whose two sides have been SWAPPED is refused: it writes the "
          "retail bytes where the staged ones belong and the file hashes wrong")

    doctored = json.loads(good)
    doctored["spans"] = []
    spill(man, json.dumps(doctored).encode())
    spill(target, retail_bytes)
    m = refusal(datdelta.apply, store, target, "staged")
    check(m and "RECONSTITUTION FAILED" in m,
          "and so is a span table with the span REMOVED -- an empty delta is "
          "structurally flawless and reconstitutes the wrong generation")
    spill(man, good)

    os.remove(victim)
    m = refusal(datdelta.apply, store,
                spill(os.path.join(tmp, "ref.t2"), retail_bytes), "staged")
    check(m and "not in the store" in m,
          "a missing blob is a refusal, not a short write",
          line_of(m, default="-- it did not refuse"))
    spill(victim, was)

    # ONE BLOB, TWO SPANS -- the dedupe this tool advertises, and the shape that
    # used to HANG it. The same four bytes staged at two offsets are one
    # content-addressed blob named by two spans, so the two spans are entitled
    # to disagree about its length; a table where they do is structurally
    # flawless (both side lengths agree with both file sizes, the spans are
    # ordered and inside the archives) and used to walk straight past the store
    # verification, because that loop deduped the CHECK and not just the hash.
    # What it reached was `apply`'s write loop filling a 400 B span from a 4 B
    # file, asking a spent handle for more bytes for ever.
    r2, s2 = pair(tmp, "dup", noise(20, 2000), {100: b"AAAA", 900: b"AAAA"})
    dup = datdelta.capture(s2, r2, store, name="dup")
    check(dup["spans"][0]["staged"]["sha256"]
          == dup["spans"][1]["staged"]["sha256"],
          "the same bytes staged at two offsets are ONE blob named by TWO spans",
          dup["spans"][0]["staged"]["sha256"][:24] + "...")
    man2 = os.path.join(store, "dup.delta.json")
    doctored = json.loads(blob(man2))
    doctored["spans"][1]["length"] = 400
    doctored["spans"][1]["staged"]["length"] = 400
    doctored["spans"][1]["retail"]["length"] = 400
    spill(man2, json.dumps(doctored).encode())
    t2 = spill(os.path.join(tmp, "dup.target"), blob(r2))
    m = bounded_refusal(datdelta.apply, store, t2, "staged", "dup")
    check(m and "is 4 B" in m and "declares 400 B" in m,
          "the SECOND span naming an already-cleared blob is length-checked "
          "too: the dedupe is on the hashing, never on the check",
          line_of(m, default="-- it did not refuse"))
    check(blob(t2) == blob(r2),
          "and the target is byte-unchanged rather than open and spinning")

    # SABOTAGE. With that length check in place, `apply`'s own guard against a
    # spent blob cannot be reached in normal operation -- and an unreachable
    # guard is a wish. So `_verify_blobs` is stubbed down to what it was in
    # effect for the second span (a sha -> path map and no checks) and the write
    # loop has to stop by itself. Nothing else in this file can reach that line.
    real_verify = datdelta._verify_blobs
    try:
        datdelta._verify_blobs = lambda store_, doc_, side_: {
            sp[side_]["sha256"]: os.path.join(
                store_, "blobs", sp[side_]["sha256"] + ".bin")
            for sp in doc_["spans"]}
        m = bounded_refusal(datdelta.apply, store, t2, "staged", "dup")
    finally:
        datdelta._verify_blobs = real_verify
    check(m and "ran out" in m and "396 B short" in m,
          "SABOTAGE: with the store verification stubbed out, the write loop "
          "REFUSES on the spent blob instead of spinning on it for ever",
          line_of(m, default="-- it did not refuse; it is still running"))
    check(m and "NEITHER GENERATION" in m and t2 in m and blob(t2) != blob(r2),
          "and it says the target is now neither generation, because a write "
          "that stopped half way through is exactly that")


# ------------------------------------------------------------- 5. the caps

def section_caps(tmp, vault):
    print("\n5. the caps, which are a premise check and not a limit")
    store = os.path.join(vault, "store5")

    # 4,100 genuine spans: one differing byte every 65 B, so every gap is 64 --
    # exactly the width that does NOT merge. Costs 267 KB, so it is exercised
    # for real rather than by tightening anything.
    n = datdelta.MAX_SPANS + 4
    base = bytearray(n * 65)
    edits = {i * 65: b"\x01" for i in range(n)}
    r, s = pair(tmp, "shred", bytes(base), edits)
    check(len(datdelta.diff_spans(s, r)) == n,
          f"the fixture really does differ in {n} separate places",
          "one byte every 65, which is the width that does not merge")
    m = refusal(datdelta.capture, s, r, store, name="shred")
    check(m and f"{n} differing spans" in m and str(datdelta.MAX_SPANS) in m,
          "more spans than the cap is refused, naming both numbers",
          line_of(m, default="-- it did not refuse"))
    check(not os.path.isfile(os.path.join(store, "shred.delta.json")),
          "and no manifest was written: the premise is judged before the store "
          "is touched")

    # The byte cap needs a 512 MiB fixture to reach honestly. Tightened instead,
    # and restored in a `finally` -- what is measured is that the branch fires
    # and names its number, which is all a 512 MiB fixture would have shown.
    r, s = pair(tmp, "fat", noise(10, 4000), {100: noise(11, 900)})
    real = datdelta.MAX_DELTA_BYTES
    try:
        datdelta.MAX_DELTA_BYTES = 512
        m = refusal(datdelta.capture, s, r, store, name="fat")
    finally:
        datdelta.MAX_DELTA_BYTES = real
    check(m and "900 B differ" in m and "512 B" in m,
          "more differing bytes than the cap is refused, naming both numbers",
          line_of(m, default="-- it did not refuse"))
    doc = datdelta.capture(s, r, store, name="fat")
    check(doc["totals"]["covered_bytes"] == 900,
          "and with the real cap back the same capture goes through -- the "
          "constant was restored, checked by re-running its own input")


# --------------------------------------------------------- 6. one store

def section_store(tmp, vault):
    print("\n6. one store, several deltas, blobs paid for once")
    store = os.path.join(vault, "store6")
    common = noise(12, 64)
    retail = noise(13, 4000)
    r = spill(os.path.join(tmp, "shared.retail"), retail)

    def staged(tag, at):
        buf = bytearray(retail)
        buf[at:at + 64] = common
        return spill(os.path.join(tmp, tag), bytes(buf))

    a = datdelta.capture(staged("sh.a", 500), r, store, name="alpha")
    b = datdelta.capture(staged("sh.b", 2500), r, store, name="beta")
    check(a["spans"][0]["staged"]["sha256"] == b["spans"][0]["staged"]["sha256"],
          "two deltas that stage the SAME 64 bytes name the same blob",
          a["spans"][0]["staged"]["sha256"][:24] + "...")
    check(a["totals"]["blobs_written"] == 2 and b["totals"]["blobs_written"] == 1
          and b["totals"]["blobs_reused"] == 1,
          "so the second capture writes one blob where the first wrote two",
          f"alpha {a['totals']['blobs_written']}/{a['totals']['blobs_reused']}, "
          f"beta {b['totals']['blobs_written']}/{b['totals']['blobs_reused']}")
    check(len(os.listdir(os.path.join(store, "blobs"))) == 3,
          "three blob files in the store for four span sides")

    m = refusal(datdelta.apply, store, os.path.join(tmp, "sh.a"), "retail")
    check(m and "2 deltas" in m and "--name" in m
          and "does not pick the last one" in m,
          "a store holding two deltas and no --name REFUSES rather than "
          "picking one", line_of(m, default="-- it did not refuse"))

    target = spill(os.path.join(tmp, "sh.target"), retail)
    rep = datdelta.apply(store, target, "staged", name="beta")
    check(blob(target) == blob(os.path.join(tmp, "sh.b"))
          and rep["name"] == "beta",
          "and with --name it reconstitutes the one that was asked for")

    m = refusal(datdelta.apply, store, target, "staged", "gamma")
    check(m and "no delta named 'gamma'" in m,
          "a name the store does not hold is a refusal that names the path it "
          "looked at")
    m = refusal(datdelta.resolve_store, os.path.join(vault, "store6-empty"))
    check(m and "no delta store" in m,
          "and a store that was never captured into does not resolve at all",
          line_of(m, default="-- it did not refuse"))
    os.makedirs(os.path.join(vault, "store6-bare"), exist_ok=True)
    m = refusal(datdelta.load, os.path.join(vault, "store6-bare"))
    check(m and "no delta manifest" in m,
          "and an empty directory that IS a store holds no delta to load")

    # THE WRITE SIDE OF THE SAME RULE. `manifest_path` above refuses to GUESS
    # which of several deltas an operator meant; until this gate existed,
    # `capture` was free to silently make the store hold only one. The default
    # stem is a basename, so `run/Gw.dat` and `run-live/Gw.dat` -- ours and
    # ArenaNet's, the one distinction CLAUDE.md is most emphatic about -- are
    # both `gw`. What an overwrite destroyed was the span table; the blobs
    # survived, content-addressed and named by nothing.
    ours, theirs = os.path.join(tmp, "run"), os.path.join(tmp, "run-live")
    os.makedirs(ours, exist_ok=True)
    os.makedirs(theirs, exist_ok=True)
    buf = bytearray(retail)
    buf[1000:1064] = common
    g1 = spill(os.path.join(ours, "Gw.dat"), bytes(buf))
    buf[3000:3064] = common
    g2 = spill(os.path.join(theirs, "Gw.dat"), bytes(buf))

    first = datdelta.capture(g1, r, store)              # no --name: stem "gw"
    man = os.path.join(store, "gw.delta.json")
    was = blob(man)
    m = refusal(datdelta.capture, g2, r, store)
    check(m and first["staged"]["sha256"] in m and "--replace" in m
          and "--name SOMETHING-ELSE" in m,
          "a second archive whose basename stems to a name already taken is "
          "REFUSED, naming the hash on disk and both ways out",
          line_of(m, want="on disk", default="-- it did not refuse"))
    check(blob(man) == was,
          "and the delta already filed under that name is byte-untouched -- an "
          "overwrite would have orphaned its blobs and lost its span table")

    with quiet() as out:
        again = datdelta.capture(g1, r, store)
    check(again["staged"]["sha256"] == first["staged"]["sha256"]
          and "re-capturing" in out.getvalue(),
          "re-capturing the SAME pair under the same name is not a clobber: it "
          "recomputes the same answer, and says so",
          line_of(out.getvalue(), want="re-capturing"))

    m = refusal(datdelta.capture, g1, r, store, "beta")
    check(m and "came from --name" in m,
          "and an explicit --name is no licence either; the refusal says where "
          "the name it collided on came from",
          line_of(m, want="came from", default="-- it did not refuse"))

    with quiet() as out:
        third = datdelta.capture(g2, r, store, replace=True)
    with open(man, "r", encoding="utf-8") as fh:
        now = json.load(fh)
    check(third["staged"]["sha256"] != first["staged"]["sha256"]
          and now["staged"]["sha256"] == third["staged"]["sha256"]
          and "--replace" in out.getvalue(),
          "--replace overwrites deliberately -- the only way it happens -- and "
          "the manifest on disk then describes the archive that replaced it",
          line_of(out.getvalue(), want="--replace"))


# ------------------------------------------------------------- 7. the vault

def section_vault(tmp, vault):
    print("\n7. ArenaNet's bytes stay under the vault")
    outside = os.path.join(tmp, "outside-the-vault")
    os.makedirs(outside, exist_ok=True)
    r, s = pair(tmp, "guard", noise(14, 800), {10: b"x"})

    m = refusal(datdelta.capture, s, r, outside, name="nope")
    check(m and "ArenaNet" in m and vault in m,
          "a store outside the vault is refused, naming the vault it wanted",
          line_of(m, default="-- it did not refuse"))
    check(not os.path.exists(os.path.join(outside, "blobs")),
          "and nothing was created there -- the guard runs before the makedirs")

    m = refusal(datdelta.resolve_store,
                os.path.join(vault, "dat_study", "d"), True)
    check(m and "dat_study" in m and "SOURCE snapshot" in m,
          "vault/dat_study is refused BEFORE the vault is allowed, or the "
          "allow would swallow it")
    check(not os.path.exists(os.path.join(vault, "dat_study")),
          "and that directory was not created either")

    m = refusal(datdelta.resolve_store, r"C:\gw\deltas", True)
    check(m and "read-only to this project" in m,
          "the owner's install is refused as a store",
          line_of(m, default="-- it did not refuse"))

    store = os.path.join(vault, "store7")
    datdelta.capture(s, r, store, name="guard")
    m = refusal(datdelta.apply, store, r"C:\gw\Gw.dat", "staged")
    check(m and "unjournalled whole-file overwrite" in m
          and "live install" in m,
          "and it is refused as a TARGET too, with datwrite's own wording "
          "underneath rather than a second copy of the rule",
          line_of(m, default="-- it did not refuse"))


# -------------------------------------------------- 8. a real MFT to annotate

BLOCK = 512
NBLOCKS = 28
FILE_SIZE = NBLOCKS * BLOCK
MFT_BLOCK = 26
MFT_OFF = MFT_BLOCK * BLOCK
ENTRY_COUNT = 23
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE
FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_A, ROW_B = 16, 17
# (offset, size, extraBytes, flags, nextStream) -- the shape test_datalloc.py
# builds, trimmed to what an annotation needs: real extents and a real MFT.
ROWS = {
    ROW_HEADER:  (0 * BLOCK, 32, 0, 3, 0),
    ROW_IDTABLE: (1 * BLOCK, 16, 0, 3, 0),
    ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 3, 0),
    ROW_A:       (2 * BLOCK, 1000, 0, 3, 0),
    ROW_B:       (4 * BLOCK, 300, 0, 3, 0),
}
ID_PAIRS = ((0x1000, ROW_A), (0x1001, ROW_B))


def build_archive(path):
    """A 14 KB archive with a real MFT. Cribbed from test_datalloc.py's fixture."""
    buf = bytearray(bytes([0xCC]) * FILE_SIZE)
    for row in (ROW_IDTABLE, ROW_A, ROW_B):
        off, size, _e, _f, _n = ROWS[row]
        data = (b"".join(struct.pack("<II", i, r) for i, r in ID_PAIRS)
                if row == ROW_IDTABLE
                else bytes(1 + ((i * 37 + row * 101) % 255) for i in range(size)))
        buf[off:off + size] = data

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, MFT_OFF)
    struct.pack_into("<I", head, 0x18, MFT_SIZE)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(MFT_SIZE)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row, (off, size, extra, flags, nxt) in ROWS.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, extra, flags, nxt, crc)
    buf[MFT_OFF:MFT_OFF + MFT_SIZE] = mft
    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return bytes(buf)


def section_archive(tmp, vault):
    print("\n8. the row annotation, against a table that exists")
    store = os.path.join(vault, "store8")
    r = os.path.join(tmp, "arc.retail")
    retail_bytes = build_archive(r)

    buf = bytearray(retail_bytes)
    a_off, a_size = ROWS[ROW_A][0], ROWS[ROW_A][1]
    buf[a_off:a_off + a_size] = bytes(b ^ 0xFF for b in
                                      retail_bytes[a_off:a_off + a_size])
    # And one byte inside the MFT itself, in row 16's crc field: the annotation
    # has to say MFT for that span and row 3, whose extent IS the table.
    crc_at = MFT_OFF + ROW_A * ENTRY_SIZE + ENTRY_CRC
    buf[crc_at] ^= 0xFF
    s = spill(os.path.join(tmp, "arc.staged"), bytes(buf))

    doc = datdelta.capture(s, r, store, name="arc")
    check(doc["note"] == "", "both archives opened, so the rows are annotated",
          f"note {doc['note']!r}")
    first, second = doc["spans"][0], doc["spans"][1]
    check(first["offset"] == a_off and first["length"] == a_size
          and first["rows"] == [ROW_A] and first["row_count"] == 1
          and not first["mft"],
          f"the payload span names row {ROW_A} and only row {ROW_A}",
          f"0x{first['offset']:X} + {first['length']}, rows {first['rows']}")
    check(second["rows"] == [ROW_SELF] and second["mft"],
          "the span inside the table names row 3 AND is flagged as the MFT",
          f"0x{second['offset']:X}, rows {second['rows']}, mft {second['mft']}")

    target = spill(os.path.join(tmp, "arc.target"), retail_bytes)
    datdelta.apply(store, target, "staged")
    check(blob(target) == bytes(buf),
          "and the archive reconstitutes byte-identically, MFT edit included")

    # Annotation is best-effort by design: a staged copy that will not open must
    # not stop the delta being captured.
    r2, s2 = pair(tmp, "notarc", b"this is not an archive at all" * 40,
                  {10: b"EDIT"})
    doc2 = datdelta.capture(s2, r2, store, name="notarc")
    check("not a GW archive" in doc2["note"] and doc2["totals"]["spans"] == 1,
          "a file that is not an archive still captures, with the reason in a "
          "note", doc2["note"][:66])
    check(doc2["spans"][0]["rows"] == [] and doc2["spans"][0]["row_count"] == 0,
          "and its annotation is empty rather than invented")


# ---------------------------------------------------------------- 9. prove

def section_prove(tmp, vault):
    print("\n9. the gate before anyone deletes 4.2 GB")
    store = os.path.join(vault, "store9")
    r, s = pair(tmp, "pv", noise(15, 6000), {2000: noise(16, 120)})
    doc = datdelta.capture(s, r, store, name="pv")

    with quiet() as out:
        rep = datdelta.prove(store, r)
    text = out.getvalue()
    check(rep["proven"] and rep["sha256"] == doc["staged"]["sha256"],
          "prove reconstitutes a fresh copy of retail and it hashes staged")
    check("PROVEN" in text and "can be deleted" in text,
          "it says PROVEN and names what may now be deleted",
          line_of(text, want="PROVEN"))
    check(not os.path.isfile(os.path.join(store, "proof", "pv.proof.dat")),
          "and the proof copy is gone -- keeping it defeats the whole purpose")

    wrong = spill(os.path.join(tmp, "pv.wrong"), noise(17, 6000))
    m = refusal(datdelta.prove, store, wrong)
    check(m and "proves nothing" in m,
          "proving against the wrong baseline is refused, not attempted",
          line_of(m, default="-- it did not refuse"))

    # SABOTAGE. `prove` hashes the copy itself instead of believing `apply`'s
    # report -- a check that cannot fail while `apply` is honest, which is
    # exactly the shape this repo calls a wish. So `apply` is stubbed into
    # dishonesty and `prove` must still refuse.
    real = datdelta.apply
    try:
        datdelta.apply = lambda *a, **kw: {
            "spans": 1, "bytes_written": 0, "sha256": doc["staged"]["sha256"]}
        m = refusal(datdelta.prove, store, r)
    finally:
        datdelta.apply = real
    kept = os.path.join(store, "proof", "pv.proof.dat")
    check(m and "NOT PROVEN" in m and os.path.isfile(kept),
          "SABOTAGE: with apply stubbed to write nothing and report success, "
          "prove's own hash still refuses -- and KEEPS the copy as evidence",
          line_of(m, default="-- it did not refuse"))
    os.remove(kept)


# ----------------------------------------------------------------- 10. CLI

def section_cli(tmp, vault):
    print("\n10. the three verbs through the command line")
    store = os.path.join(vault, "store10")
    r, s = pair(tmp, "cli", noise(18, 7000), {4096: noise(19, 200)})
    staged_bytes = blob(s)

    rc, out, _err = run_cli(["--capture", s, "--retail", r, "--out", store,
                             "--name", "cli"])
    check(rc == 0 and "1 span(s) covering 200 B" in out,
          "--capture exits 0 and prints the span table",
          line_of(out, want="span(s) covering"))

    target = spill(os.path.join(tmp, "cli.target"), blob(r))
    rc, out, _err = run_cli(["--apply", store, "--target", target])
    check(rc == 0 and blob(target) == staged_bytes,
          "--apply exits 0 and the target is the staged archive")

    rc, out, _err = run_cli(["--prove", store, "--retail", r])
    check(rc == 0 and "PROVEN" in out, "--prove exits 0 and says PROVEN")

    rc, _out, err = run_cli(["--apply", store, "--target", target])
    check(rc == 2 and "REFUSED" in err and "ALREADY" in err,
          "a refusal exits 2 and goes to stderr, never 0 and never 1",
          line_of(err))

    rc, _out, err = run_cli(["--capture", s, "--retail", r, "--out", store,
                             "--prove", store])
    check(rc == 2 and "exactly one of" in err,
          "two verbs at once is refused rather than half-run",
          line_of(err))


def main():
    # `ignore_cleanup_errors` is for one case and it is a red one: if section
    # 4's write loop ever spins again, its daemon thread is still holding the
    # target open when this block exits, and Windows will not delete a file
    # under an open handle. Without this the run dies in the cleanup with a
    # PermissionError and NEVER PRINTS ITS VERDICT -- the [FAIL] that names the
    # hang would be replaced by a traceback about a temp directory.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        was = os.environ.get("RURIK_VAULT")
        vault = use_vault(os.path.join(tmp, "vault"))
        try:
            section_spans(tmp)
            section_roundtrip(tmp, vault)
            section_grown(tmp, vault)
            section_refusals(tmp, vault)
            section_caps(tmp, vault)
            section_store(tmp, vault)
            section_vault(tmp, vault)
            section_archive(tmp, vault)
            section_prove(tmp, vault)
            section_cli(tmp, vault)
        finally:
            if was is None:
                os.environ.pop("RURIK_VAULT", None)
            else:
                os.environ["RURIK_VAULT"] = was
            vaultpath._resolved = None
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
