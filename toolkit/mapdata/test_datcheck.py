"""Check the pre-flight and the detector by breaking every rule they enforce.

`datcheck.py` is a gate, and a gate nobody has watched fail is a wish. Every
check it makes is about a copy of a 4 GB archive that we are about to hand to a
client -- so the only honest way to know the gate works is to build an archive
that violates one rule at a time and require the matching item, and only the
matching item, to go red.

WHAT IT RUNS AGAINST. A 5.5 KB archive this file builds in a temp directory. It
never opens `vault/dat_study/Gw.dat`, never reads `C:\\gw`, never opens anything
for writing except its own fixture, and needs no vault -- so the floor below is
a real floor and not a corpus-shaped hope.

The fixture is laid out with real reserved rows: 0 descriptor, 1 file header, 2
file-id table, 3 the MFT, 4..15 all-zero spares, and FIVE real rows at index
>= 16 including a head/partner pair (`alloc.flags 3 / alloc.stream 1` linked
through `nextStream` to a `flags 1 / stream 0` row). The pair is not decoration:
a non-first stream is the one row shape that legitimately has NO file-id record,
and without one the "USED clear at index >= 16" sabotage could not be isolated
from the directory invariant.

EACH SABOTAGE IS CHECKED TWICE -- the item it targets must fail AND every other
item must still pass. A gate that goes red at everything is as useless as one
that goes red at nothing, and the isolation half is what catches a check whose
predicate is accidentally broad. The fixture's own layout was relaid twice to
make that possible: the past-EOF sabotage needs free space at the END of the
file or it also trips the overlap rule, and the misalignment sabotage needs a
row with a gap after it or it trips the same.

Section 12 is the LAUNCH GATE, `assert_archive_safe`, and it is the one section
that checks a REFUSAL rather than a verdict. The two rules it adds to the
pre-flight are there because each has a control here that shows the pre-flight
blind to it: an archive with a wrong MFT self-crc answers 10 of 10 clear and is
still rejected by the client's own LoadMft, and an archive whose row was
rewritten legitimately (payload and crc agreeing) is clean by every integrity
rule and is a different world. It also asks the FOUR launch sites' syntax trees
whether each one calls the gate ITSELF -- session.py's two-doors rule, applied
to the archive rather than to the binary -- because a gate wired into three of
four launch paths is the defect it exists to prevent, which is what the first
revision of that section was: it named three sites and `drive_client.main`, the
standalone operator launcher and the other of the two doors that comment is
actually about, was not one of them. So the list is now checked against a census
of the harness files that hand an exe to `Popen`, and the live site is checked
for the ORDER of its call as well as its presence -- above the client census,
the gate answers a held-open archive as unreadable damage instead of as the
running client it is.

Section 12e is the seam on the far side of the identity tier: `overlay.py` WRITES
the fingerprint documents this gate READS, and until 2026-08-20 no wired call
site had ever passed the two together, so nothing had measured whether they agree.
A probe found five ways they did not -- the gate compared by ROW NUMBER while all
of overlay is addressed by FILE ID, it honoured none of overlay's three trust
checks, five doctored shapes escaped as raw exceptions, and a record with its
`rows` block deleted fell through to `retail_rows` and cleared a retail archive.
Every check there carries a control that watches the pre-fix code clear the same
input, and one of them hands ONE document to both readers and requires the same
verdict, because two readers of one file drifting apart is the defect itself.

Section 4 is a different thing sharing this file: `archive.py`'s new `RURIK_DAT`
override, which is a lever on the SERVER path. It exists because a running client
holds an exclusive lock on the archive it launched from, so the two sides can
never share one file; C2's server copy is only reachable through it. It is
checked by reloading the module with the variable set and opening `Archive()`
with no path at all -- reading the constant would pass against a module that
never uses it.

    python toolkit/mapdata/test_datcheck.py
"""

import ast
import binascii
import glob
import hashlib
import importlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import archive as archive_mod  # noqa: E402
import datcheck  # noqa: E402
import checks  # noqa: E402

# FLOOR: measured from a green run on 2026-08-11. Every check below runs
# unconditionally -- the fixture is built by this file and there is no corpus to
# be absent -- so a count under this means a section stopped executing, which on
# a gate is indistinguishable from the gate being removed.
#
# RAISED 69 -> 75 on 2026-08-13 with section 0b, which pins `row_identity` --
# the file id and role every row named by `--diff` now carries. It is six more
# checks on the SAME fixture (no vault, no client), so the floor moves by
# exactly six and the bare-machine property is unchanged.
#
# RAISED 75 -> 83 on 2026-08-14 with section 3b, and that one is the correction:
# 0b pinned the LOGIC and nothing pinned the OUTPUT. `format_diff` -- the only
# thing an operator ever reads -- was referenced by no test in this tree, so a
# sabotage reverting it and the `--preflight` banner to their exact pre-fix bare
# form left this file at 75/75 and `test_archive.py` at 29/29, both exit 0. The
# whole human-facing half of the fix could be deleted green. Eight more checks
# in 3b plus one in §7 -- the `--preflight` banner is a separate `print` in
# `_main` that no function-level check can see, and the revert sabotage's six
# reds did not include it until §7 ran the real CLI. Same fixture, still no
# vault and no client. MEASURED, not counted by hand: a green run prints 84.
#
# RAISED 84 -> 108 on 2026-08-17 with sections 8, 9 and 10 -- the generation
# census, the payload CRC sweep and the file-length half of `--diff`. Same
# fixture, still no vault and no client. Two of the three carry a CONTROL that
# is the actual point of the section: §9 asserts that a stale payload CRC
# passes ALL TEN open-time rules (10 of 10 clear) before the sweep names it,
# and §10 asserts that appending past every extent changes NO MFT row, so
# nothing else in this tool could have caught it. A check whose control does
# not first demonstrate the blind spot is not evidence that the new code sees
# anything. MEASURED from a green run: 108.
#
# RAISED 108 -> 112 on 2026-08-17 with section 11, the mftOffset width (C-7).
# Four checks, and the reason they are cheap is the point: proving a u64 read
# does NOT need a 4 GB file, only the high dword set and a failure that names
# the full offset. A `<I` reader truncates, finds the MFT where it always was,
# and opens the archive reporting success -- so the check is refutable in both
# directions on a 5.5 KB fixture. MEASURED from a green run: 112.
#
# RAISED 112 -> 142 on 2026-08-20 with sections 12, 12b, 12c and 12d --
# `assert_archive_safe`, the launch-side gate. Thirty checks on the same 5.5 KB
# fixture (no vault, no client, no network), and two of them are the point:
# §12's CONTROL that a wrong MFT self-crc passes ALL TEN open-time rules, which
# is why the gate had to add a rule the pre-flight never made, and §12b's
# CONTROL that an archive with a legitimately-rewritten row is integrity-clean,
# so nothing above the identity tier could tell the two profiles apart. §12d is
# structural rather than behavioural because the launch sites need a client to
# run: it asks each one's syntax tree whether the call is written down in THAT
# function, with a negative control that deleting the line flips it.
# MEASURED from a green run: 142.
#
# RAISED 142 -> 149 on 2026-08-20 by the fix pass over that section, and all
# seven are about the gate's SURROUNDINGS rather than the gate: four sites
# instead of three (`drive_client.main` was missed, and it is the other of the
# two doors session.py's comment names), a CENSUS check that derives the list of
# doors from disk so a fifth one cannot appear unlisted, the live site's call
# ORDER with its own wrong-way-round control, and three on the one unreadable
# cause that is not damage -- a client already holding the archive open, which
# raises PermissionError and used to be reported as "could not be read far
# enough to have findings" with no action named. Still the same 5.5 KB fixture,
# still no vault and no client: the platform-dependent half of the lock check
# writes its expectation against the errno the platform actually produced.
# MEASURED from a green run: 149.
#
# RAISED 149 -> 168 on 2026-08-20 with section 12e, the FINGERPRINT DOCUMENT.
# Nineteen checks on the same 5.5 KB fixture, and SEVEN of them are controls
# that watch the pre-fix code clear the very input the fix now refuses --
# `prefix_side` monkeypatched over the resolver, `_verify_overlay_record`
# neutered, `prefix_parse` raising the raw exceptions that used to escape. That
# ratio is deliberate: a probe had just shown this gate CLEARING an archive
# `overlay.py --status` calls unscoreable, and "the gate refuses X" is
# compatible with the gate having always refused X. One of the nineteen is an
# EQUIVALENCE check -- one document, read by `overlay.load_fingerprints` and by
# this gate, required to give the same accept/refuse -- because the two readers
# agreeing is the only thing that keeps them from drifting again. Still no
# vault: the section points `RURIK_VAULT` at its own temp directory and puts it
# back. MEASURED from a green run: 168.
LEDGER = checks.Ledger("dat pre-flight and detector", floor=168)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ENTRY_SIZE = 24
BLOCK = 512

FILE_SIZE = 0x1600
MFT_OFF = 0x1200
ENTRY_COUNT = 21                       # rows 0..20; row 0 is the descriptor
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE    # 504, one block
SLACK = 0xCC

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_A, ROW_B, ROW_HEAD, ROW_D, ROW_PARTNER = 16, 17, 18, 19, 20

# row -> (offset, size, extraBytes, flags16, nextStream)
# flags16 is `alloc.flags | alloc.stream << 8`, the two bytes archive.py reads as
# one u16. Reservations, in order: 0x0000-0x0200 header, 0x0200-0x0400 id table,
# 0x0400-0x0600 A, 0x0600-0x0A00 B, 0x0A00-0x0C00 head, 0x0C00-0x0E00 D,
# 0x0E00-0x1000 partner, 0x1000-0x1200 FREE, 0x1200-0x1400 MFT,
# 0x1400-0x1600 FREE. The two holes are what let a misalignment and a past-EOF
# extent be sabotaged one at a time.
ROWS = {
    ROW_HEADER:  (0x0000, 32, 0, 0x0003, 0),
    ROW_IDTABLE: (0x0200, 40, 0, 0x0003, 0),
    ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 0x0003, 0),
    ROW_A:       (0x0400, 300, 0, 0x0003, 0),
    ROW_B:       (0x0600, 900, 8, 0x0003, 0),
    ROW_HEAD:    (0x0A00, 500, 8, 0x0103, ROW_PARTNER),
    ROW_D:       (0x0C00, 100, 0, 0x0003, 0),
    ROW_PARTNER: (0x0E00, 200, 8, 0x0001, 0),
}
PAYLOAD_ROWS = (ROW_IDTABLE, ROW_A, ROW_B, ROW_HEAD, ROW_D, ROW_PARTNER)

# (file_id, row). Row 20 is deliberately absent: it is a non-first stream and is
# reached through nextStream, never through the directory. The (0, 0) record is
# a RELEASED slot -- three of them exist in the real archive and the invariant
# must count them rather than call them dangling.
ID_RECORDS = [(0x1000, ROW_A), (0x1001, ROW_B), (0x1002, ROW_HEAD),
              (0x1003, ROW_D), (0, 0)]

ALL_ITEMS = ["0x1C bit 0 clear", "0x1C bit 1 clear", "header CRC over 0x00..0x0C",
             "every extent 512-aligned", "every extent inside EOF",
             "no overlapping reservations",
             "every USED|FIRST row >= 16 is named",
             "every file-id record names a USED row",
             "no row below index 16 touched",
             "no USED-clear row that something points at"]


def pattern(seed, n):
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def role_of(ident, row):
    """`ident[row]["role"]`, or a string saying the row is absent.

    NEVER a bare `ident[row]`. A `row_identity` that has LOST a row -- which is
    exactly what a reader changing convention produces -- raises KeyError here
    and kills the run before `LEDGER.verdict()`: no banner, no floor, no ledger,
    the one failure `checks.py` cannot see. MEASURED on the
    consistent-renumber sabotage: four [FAIL] lines had already printed and the
    run then died at the fifth check with a traceback. A broken module has to
    score as WRONG, not as absent.
    """
    rec = ident.get(row)
    return "NO SUCH ROW %d in the identity map" % row if rec is None         else rec["role"]


def ids_of(ident, row):
    """`ident[row]["file_ids"]`, or None if the row is absent. See `role_of`."""
    rec = ident.get(row)
    return None if rec is None else rec["file_ids"]


def build_archive(path):
    """A small, complete, self-consistent archive. Returns nothing it needs back."""
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)

    for row in PAYLOAD_ROWS:
        off, size, _extra, _flags, _nxt = ROWS[row]
        if row == ROW_IDTABLE:
            data = b"".join(struct.pack("<II", i, r) for i, r in ID_RECORDS)
            assert len(data) == size, (len(data), size)
        else:
            data = pattern(row, size)
        buf[off:off + size] = data

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, MFT_OFF)
    struct.pack_into("<I", head, 0x18, MFT_SIZE)
    struct.pack_into("<I", head, 0x1C, 0)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(MFT_SIZE)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x04, 7)              # the flush counter
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row, (off, size, extra, flags, nxt) in ROWS.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else \
            binascii.crc32(bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, extra, flags, nxt, crc)
    buf[MFT_OFF:MFT_OFF + MFT_SIZE] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


# ---------------------------------------------------------------- surgery --

def poke(path, offset, data):
    """Change bytes in the fixture. Only ever the fixture."""
    with open(path, "r+b") as fh:
        fh.seek(offset)
        fh.write(data)


def poke_row(path, row, **fields):
    """Rewrite one MFT row's fields in place."""
    with open(path, "r+b") as fh:
        fh.seek(MFT_OFF + row * ENTRY_SIZE)
        cur = fh.read(ENTRY_SIZE)
        off, size, extra, flags, nxt, crc = struct.unpack("<QIHHII", cur)
        vals = {"offset": off, "size": size, "extra": extra, "flags": flags,
                "nxt": nxt, "crc": crc}
        vals.update(fields)
        fh.seek(MFT_OFF + row * ENTRY_SIZE)
        fh.write(struct.pack("<QIHHII", vals["offset"], vals["size"],
                             vals["extra"], vals["flags"], vals["nxt"],
                             vals["crc"]))


def verdicts(path):
    """name -> ok, for one pre-flight run."""
    got, _facts = datcheck.preflight(path)
    return {c.name: c.ok for c in got}


def expect_only(path, label, failing):
    """The named item fails and every other item still passes."""
    v = verdicts(path)
    missing = [n for n in ALL_ITEMS if n not in v]
    check(not missing, f"{label}: pre-flight still reports every item",
          f"missing {missing}" if missing else f"{len(v)} items")
    check(v.get(failing) is False, f"{label}: '{failing}' goes RED")
    others = [n for n, ok in v.items() if n != failing and not ok]
    check(not others, f"{label}: nothing else goes red",
          f"also red: {others}" if others else "isolated")


TOOL = os.path.join(HERE, "datcheck.py")


def run_cli(*argv):
    """The real CLI, in a real subprocess. Module level since 2026-08-17 --
    §7 had it as a local closure and §§8-10 need the same one, and two
    definitions of "run the tool" is how they drift apart."""
    return subprocess.run([sys.executable, TOOL] + list(argv),
                          capture_output=True, text=True)


def cli(*argv):
    return run_cli(*argv).returncode


def plant_generation(path, at, counter, rows=ENTRY_COUNT):
    """Write a second MFT descriptor into the fixture's slack, block-aligned.

    A real archive accumulates these because the client rotates its table on
    flush; the fixture has to be given one, and giving it one is what makes the
    "no fallback" check able to go BOTH ways instead of only red.
    """
    desc = bytearray(ENTRY_SIZE)
    desc[0:4] = MFT_MAGIC
    struct.pack_into("<I", desc, 0x04, counter)
    struct.pack_into("<I", desc, 0x08, 0)
    struct.pack_into("<I", desc, 0x0C, rows)
    poke(path, at, bytes(desc))


def section_generations(tmp):
    print("\n8. the MFT generation census -- what a repair would have to adopt")

    one = fresh(tmp, "gen-one.dat")
    gens = datcheck.generations(one)
    live = [g for g in gens if g["live"]]
    check(len(gens) == 1 and len(live) == 1,
          "a fresh fixture has exactly one generation, and it is the live one",
          f"{len(gens)} candidate(s), {len(live)} live")
    check(gens[0]["offset"] == MFT_OFF and gens[0]["rows"] == ENTRY_COUNT,
          "and the scan finds it where the header says it is",
          f"0x{gens[0]['offset']:X}, {gens[0]['rows']} rows")
    check(cli("--dat", one, "--generations") == 1,
          "ONE generation REFUSES -- a repair would have nothing to adopt",
          "exit 1")

    # The control the refusal needs: plant an older generation in the slack
    # between the payload rows and the MFT, and the same verb must go green.
    two = fresh(tmp, "gen-two.dat")
    plant_generation(two, 0x1000, counter=6)
    gens2 = datcheck.generations(two)
    ok2 = [g for g in gens2 if g["shape_ok"]]
    check(len(gens2) == 2 and len(ok2) == 2,
          "CONTROL: with a planted older generation the scan finds two",
          f"{len(gens2)} candidate(s), {len(ok2)} passing the shape gate")
    check([g["counter"] for g in gens2] == [7, 6],
          "and they are ordered newest-first by the flush counter",
          f"{[g['counter'] for g in gens2]}")
    check(gens2[0]["live"] and not gens2[1]["live"],
          "with only the header's own marked live")
    check(cli("--dat", two, "--generations") == 0,
          "TWO generations pass -- the refusal is not unconditional", "exit 0")

    # Shape gate: a candidate with +0x08 != 0 is one ScanMft would not adopt.
    bad = fresh(tmp, "gen-shape.dat")
    plant_generation(bad, 0x1000, counter=6)
    poke(bad, 0x1000 + 0x08, struct.pack("<I", 1))
    shaped = [g for g in datcheck.generations(bad) if g["shape_ok"]]
    check(len(shaped) == 1,
          "a candidate with +0x08 != 0 fails the shape gate ScanMft applies",
          f"{len(shaped)} of 2 pass")
    check(cli("--dat", bad, "--generations") == 1,
          "so it does not count as a fallback either", "exit 1")

    # And the census must not quietly become a pre-flight item again: see
    # datcheck.preflight's comment for why it was removed after one test run.
    names = [c.name for c in datcheck.preflight(one)[0]]
    check(not any("generation" in n for n in names),
          "the census stays OUT of --preflight, which never reads a payload",
          f"{len(names)} pre-flight items, none naming a generation")


def section_crc_sweep(tmp):
    print("\n9. the payload CRC sweep -- what the ten open-time rules cannot see")

    clean = fresh(tmp, "crc-clean.dat")
    sw = datcheck.crc_sweep(clean)
    check(not sw["bad"], "a healthy fixture has no CRC finding",
          f"{sw['checked']} payload(s) recomputed")
    check(sw["skipped"] == list(datcheck.CRC_STRUCTURAL_ROWS),
          "and the structural rows are skipped BY NAME, not silently",
          f"skipped {sw['skipped']}")
    check(sw["checked"] == len(PAYLOAD_ROWS),
          "every payload row is actually read -- the sweep is not vacuous",
          f"{sw['checked']} checked, {len(PAYLOAD_ROWS)} payload rows")

    # A stale CRC is invisible to every rule the client applies at OPEN, and
    # costs the whole nextStream chain the moment repair fires for any reason.
    stale = fresh(tmp, "crc-stale.dat")
    poke_row(stale, ROW_A, crc=0xDEADBEEF)
    v = verdicts(stale)
    check(all(v.values()),
          "CONTROL: a stale payload CRC passes ALL TEN open-time rules",
          f"{sum(v.values())} of {len(v)} clear -- which is the point")
    bad = datcheck.crc_sweep(stale)["bad"]
    check(len(bad) == 1 and bad[0][0] == ROW_A,
          "but the sweep names it", f"rows {[b[0] for b in bad]}")
    check(cli("--dat", stale, "--crc-sweep") == 1,
          "and the CLI refuses", "exit 1")

    # C-6, the live trap: datmove flattens compression to 0 while the bytes
    # stay compressed. The CRC is over the STORED bytes and does not move, so
    # this is the one defect the sweep cannot catch by checksum -- it is caught
    # by reporting the row, and the test says so rather than claiming more.
    body = fresh(tmp, "crc-flat.dat")
    poke(body, ROWS[ROW_A][0], b"\xff" * 16)     # payload changed, CRC not
    flat = datcheck.crc_sweep(body)["bad"]
    check(len(flat) == 1 and flat[0][0] == ROW_A,
          "a payload edited without its CRC is caught", f"{len(flat)} finding(s)")

    past = fresh(tmp, "crc-eof.dat")
    poke_row(past, ROW_B, offset=FILE_SIZE - 16)
    hits = [b for b in datcheck.crc_sweep(past)["bad"] if b[0] == ROW_B]
    check(hits and hits[0][3] == "extent past EOF",
          "a row whose extent runs past EOF is named, not read off the end",
          f"{hits[0][3] if hits else 'MISSED'}")


def section_growth(tmp):
    print("\n10. --diff sees the file's own length")

    before = fresh(tmp, "grow-before.dat")
    snap = datcheck.snapshot(before, datcheck.scan(before))
    d = datcheck.diff(snap, path=before)
    check(d["unchanged"] and d["growth"] is None,
          "an untouched archive reports no growth", "unchanged")

    grown = fresh(tmp, "grow-after.dat")
    with open(grown, "ab") as fh:                # append past every extent
        fh.write(b"\x00" * BLOCK)
    d2 = datcheck.diff(snap, path=grown)
    check(d2["growth"] is not None
          and d2["growth"]["delta"] == BLOCK,
          "appending past every extent IS detected",
          f"{d2['growth']}" if d2["growth"] else "MISSED -- no row records it")
    check(not d2["unchanged"],
          "and growth alone makes the diff non-clean")
    check(not d2["changes"] and not d2["corroboration"],
          "CONTROL: no MFT row changed, so nothing else could have caught it",
          f"{len(d2['changes'])} row change(s)")
    check("LENGTH CHANGED" in datcheck.format_diff(d2),
          "and the formatter says so out loud")
    check(cli("--dat", grown, "--diff",
              write_snap(tmp, before, "grow.json")) == 1,
          "the CLI exits 1 on growth alone", "exit 1")


def section_mft_offset_width(tmp):
    """The header's mftOffset is a u64, and all three readers must say so.

    C-7 of studies/archivewrite/FINDINGS.md: `archive.py` read this field as
    `<I` while `datcheck.read_header` and `datwrite.mft_offset_of` both read
    `<Q`. Two of three said u64 and the OUTLIER WAS THE ONE EVERY TOOL IMPORTS.

    It never fired, because every archive on this machine keeps the high dword
    zero -- which is exactly why it needed a test rather than a reading. And it
    was not harmless: `dat_study`'s live MFT sits 121,634,304 B below the u32
    ceiling, so it silently CAPPED how far the archive could grow, which is the
    route the same study scores as contested.

    The test does not need a 4 GB file. Setting the high dword and requiring the
    failure to NAME the full 64-bit offset is refutable both ways: a `<I` reader
    truncates to the low dword, finds the MFT exactly where it always was, and
    opens the archive with no complaint at all.
    """
    print("\n11. the header's mftOffset is a u64 in every reader")

    good = fresh(tmp, "u64-good.dat")
    a_off = archive_mod.Archive(good).mft_offset
    d_off = datcheck.read_header(good)["mft_offset"]
    check(a_off == d_off == MFT_OFF,
          "all readers agree on an ordinary archive",
          f"archive={a_off:#x} datcheck={d_off:#x}")

    # The high dword, set on a copy. Nothing else about the archive changes.
    high = fresh(tmp, "u64-high.dat")
    poke(high, 0x14, struct.pack("<I", 1))          # mftOffset += 2**32
    want = MFT_OFF + (1 << 32)

    check(datcheck.read_header(high)["mft_offset"] == want,
          "datcheck reads the full 64 bits", f"{want:#x}")

    failed = None
    try:
        archive_mod.Archive(high)
    except (ValueError, OSError) as exc:
        failed = str(exc)
    check(failed is not None,
          "archive.py does NOT quietly open it by truncating to the low dword",
          "a <I reader finds the MFT at 0x1200 and reports success")
    check(failed is not None and hex(want)[2:].upper() in failed.upper(),
          "and the failure names the FULL offset, which is the u64 evidence",
          failed.split(":")[0] if failed else "opened cleanly")


def write_snap(tmp, path, name):
    out = os.path.join(tmp, name)
    datcheck.write_snapshot(path, out)
    return out


# ------------------------------------------------------- the launch gate --

ROW_CRC_OFF = 0x14                      # the crc dword inside a 24-byte row


def self_crc_of(path):
    """The MFT self-crc this fixture OUGHT to carry, computed here.

    THE FORMULA IS WRITTEN OUT RATHER THAN IMPORTED. `datwrite.mft_self_crc` is
    what `assert_archive_safe` uses; asking it would make every check below
    agree with itself no matter what either side said. This is the rule as
    `datwrite.py`'s own docstring states it -- CRC-32 over the table with row
    3's own 24 bytes skipped, because a checksum cannot cover the field it is
    stored in -- expressed a second time, independently, so the two can differ.
    """
    with open(path, "rb") as fh:
        fh.seek(MFT_OFF)
        mft = fh.read(MFT_SIZE)
    acc = binascii.crc32(mft[0:ROW_SELF * ENTRY_SIZE])
    return binascii.crc32(mft[(ROW_SELF + 1) * ENTRY_SIZE:MFT_SIZE], acc)


def seal_self_crc(path):
    """Give the fixture the MFT self-crc a real archive carries.

    `build_archive` writes 0 into row 3's crc field, which was correct for as
    long as nothing in this tree read it -- `--preflight` never has. The launch
    gate does, so the sections below need a fixture that is healthy by that rule
    too, and one that can then be broken on purpose. Row 3's own bytes are
    outside the sum, so writing the answer in does not change the answer.
    """
    poke(path, MFT_OFF + ROW_SELF * ENTRY_SIZE + ROW_CRC_OFF,
         struct.pack("<I", self_crc_of(path)))
    return path


def sealed(tmp, name):
    """A fixture that is healthy by every rule the launch gate applies."""
    return seal_self_crc(fresh(tmp, name))


def reseal_row_crc(path, row):
    """Recompute one row's payload crc from the bytes now on disk.

    What a legitimate write leaves behind: payload and crc agreeing, so the
    sweep is green and the archive is nonetheless a DIFFERENT archive. Without
    this the identity tier could never be reached -- the CRC sweep would refuse
    first and the fingerprint comparison would go untested.
    """
    off, size = ROWS[row][0], ROWS[row][1]
    with open(path, "r+b") as fh:
        fh.seek(off)
        crc = binascii.crc32(fh.read(size))
        fh.seek(MFT_OFF + row * ENTRY_SIZE + ROW_CRC_OFF)
        fh.write(struct.pack("<I", crc))
    return path


def fingerprint_block(path, rows):
    """{row: [size, crc_hex, compression]} -- the a10stage document's shape."""
    mft = datcheck.read_mft(path)
    out = {}
    for row in rows:
        f = datcheck.row_fields(datcheck.row_bytes(mft, row))
        out[str(row)] = [f["size"], "0x%08X" % f["crc"], f["extra_bytes"]]
    return out


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def refused_by_gate(*args, **kw):
    """(refused, message) for one `assert_archive_safe` call."""
    try:
        datcheck.assert_archive_safe(*args, **kw)
        return False, ""
    except datcheck.ArchiveUnsafe as exc:
        return True, str(exc)


def cleared_by_gate(*args, **kw):
    """The gate's receipt, or an empty one and a printed reason.

    NEVER a bare call. A gate that refuses the HEALTHY case has to score as a
    red check, not as a `SystemExit` that kills the run before
    `LEDGER.verdict()` -- no banner, no floor, no ledger, which is the one
    failure `checks.py` cannot see. Same rule as `role_of` above, for the same
    reason: a broken module must score as WRONG, not as absent.
    """
    try:
        return datcheck.assert_archive_safe(*args, **kw)
    except datcheck.ArchiveUnsafe as exc:
        print("   unexpected refusal: %s"
              % " / ".join(ln.strip() for ln in str(exc).splitlines()[:2]))
        return {}


def gate_calls(source, funcname):
    """Every `assert_archive_safe(...)` call inside `funcname`, as AST nodes.

    Asked of the syntax tree because the two things that matter are invisible to
    a grep: that the call is inside THAT function, and which keywords it hands
    over. A file mentioning the name in a comment greps identically.
    """
    fn = next((n for n in ast.walk(ast.parse(source))
               if isinstance(n, ast.FunctionDef) and n.name == funcname), None)
    if fn is None:
        return []
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name == "assert_archive_safe":
                out.append(n)
    return out


def gate_after_client_census(source):
    """(gate line, "already running" refusal line) inside `preflight`.

    ORDER, not presence, and it is the one thing about this call site that a
    presence check cannot see. A running client holds an EXCLUSIVE lock on the
    archive it launched from, so a gate placed ABOVE the client census answers a
    left-open client with "could not be read far enough to have findings" --
    unreadable, no action named -- and buries the purpose-written refusal that
    says a client is already running and to close it. Both lines are read out of
    the syntax tree so a comment mentioning either one cannot satisfy this.

    Either line missing comes back as None, which scores as a red check rather
    than an exception: a site that stopped calling the gate at all must not be
    reported as a passing order.
    """
    tree = ast.parse(source)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "preflight"), None)
    if fn is None:
        return None, None
    calls = gate_calls(source, "preflight")
    census = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Raise)
              and "already running" in (ast.get_source_segment(source, n) or "")]
    return (calls[0].lineno if calls else None,
            min(census) if census else None)


# A `preflight` with the two in the WRONG order -- the negative control for the
# check above. Without it "gate line > census line" passes on any file where one
# of the two is missing, and would go on passing after the gate moved back up.
WRONG_ORDER_PREFLIGHT = '''
def preflight(exe, account_label=None):
    cleared = datcheck.assert_archive_safe(live_dat, why="launch at the live service")
    running = one_live_client()
    if running != 0:
        raise LiveError(f"{running} Gw.exe already running -- close them first")
'''


def open_error(path):
    """The exception `open(path, "rb")` actually raises here, or None.

    Asked rather than assumed because the answer is the platform's, not ours: a
    directory standing in for an archive raises `PermissionError` on Windows and
    `IsADirectoryError` on POSIX, and only the first is the shape a held-open
    client produces. The check that uses this compares the gate's message
    against what the platform DID, so it stays refutable on either.
    """
    try:
        with open(path, "rb"):
            return None
    except OSError as exc:
        return exc


def section_launch_gate(tmp):
    """The gate a launch site runs before it hands an archive to a client.

    WHY A GATE AND NOT A REPORT. Everything above answers a question; this
    refuses. The two failure modes it stands in front of have no clean error
    between them and the archive: a header whose CRC does not verify tail-jumps
    `ArchiveOpen` into `ArchiveCreate`, which writes a fresh empty archive over
    4.2 GB with nothing logged, and a stale payload CRC costs the whole
    `nextStream` chain the moment the client's repair fires for any reason at
    all. So the sabotages below are checked for the REFUSAL, not for a verdict
    string, and each one names the rule it broke.
    """
    print("\n12. the launch gate refuses an archive a client would repair")

    good = sealed(tmp, "gate-good.dat")
    cleared = cleared_by_gate(good)
    check(len(cleared.get("preflight", [])) == len(ALL_ITEMS)
          and cleared.get("crc_sweep", {}).get("checked") == len(PAYLOAD_ROWS),
          "a healthy archive clears, and the receipt says what was measured",
          f"{len(cleared.get('preflight', []))} rules, "
          f"{cleared.get('crc_sweep', {}).get('checked')} payload CRC(s)")
    # The self-crc in the receipt is compared against THIS FILE's own reading of
    # the rule, not against itself -- see `self_crc_of`.
    check(cleared.get("rows") == ENTRY_COUNT
          and cleared.get("self_crc") == self_crc_of(good)
          and os.path.basename(good) in cleared.get("summary", "")
          and "self-crc" in cleared.get("summary", ""),
          "and the one line a caller prints names the archive and its self-crc",
          cleared.get("summary", "(refused)")[:96])

    # IT VERIFIES AND NEVER MODIFIES, which is the property the LIVE path rests
    # on -- `vault/run-live`'s archive streams new content into itself during a
    # real session, and a gate that wrote so much as a flag byte there would be
    # editing ArenaNet's own copy between a login and a capture.
    quiet = sealed(tmp, "gate-quiet.dat")
    fps = fingerprint_block(quiet, (ROW_A, ROW_B, ROW_HEAD))
    plant_generation(quiet, 0x1000, counter=6)
    was = sha256_of(quiet)
    cleared_by_gate(quiet, fingerprints=fps, deep=True)
    check(sha256_of(quiet) == was,
          "the whole gate -- deep, fingerprinted -- leaves the file byte-identical",
          f"sha256 {was[:16]}")

    hdr = sealed(tmp, "gate-hdrcrc.dat")
    poke(hdr, 0x0C, struct.pack("<I", 0xDEADBEEF))
    red, msg = refused_by_gate(hdr)
    check(red and "header CRC" in msg and "ArchiveCreate" in msg,
          "a bad header CRC is refused, naming the rebuild it causes",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    magic = sealed(tmp, "gate-magic.dat")
    poke(magic, 0, b"XXXX")
    red, msg = refused_by_gate(magic)
    check(red and "magic" in msg, "and so is a file header with the wrong magic",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    # One open-time rule, and the gate must name WHICH -- a refusal that says
    # only "pre-flight failed" sends the reader back to run the pre-flight.
    rule = sealed(tmp, "gate-rule.dat")
    poke_row(rule, ROW_PARTNER, flags=0x0000)
    red, msg = refused_by_gate(rule)
    check(red and "no USED-clear row that something points at" in msg,
          "a broken open-time rule is refused, naming the rule",
          "named" if red and "USED-clear" in msg else msg[:78])

    # THE SELF-CRC, AND ITS CONTROL. This is the rule `preflight()` has never
    # made, so the control is the whole point of adding it: the same archive
    # answers 10 of 10 clear and is still rejected by the client's own LoadMft.
    selfcrc = sealed(tmp, "gate-selfcrc.dat")
    poke(selfcrc, MFT_OFF + ROW_SELF * ENTRY_SIZE + ROW_CRC_OFF,
         struct.pack("<I", 0x1BADC0DE))
    v = verdicts(selfcrc)
    check(all(v.values()),
          "CONTROL: a wrong MFT self-crc passes ALL TEN open-time rules",
          f"{sum(v.values())} of {len(v)} clear -- which is why the gate adds it")
    red, msg = refused_by_gate(selfcrc)
    check(red and "self-crc" in msg,
          "but the gate refuses it, naming the self-crc",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    stale = sealed(tmp, "gate-payload.dat")
    poke_row(stale, ROW_A, crc=0xDEADBEEF)
    seal_self_crc(stale)                      # the table is consistent again
    red, msg = refused_by_gate(stale)
    check(red and "stored 0x%08X" % 0xDEADBEEF in msg
          and f"row {ROW_A}" in msg,
          "a stale payload CRC is refused, and the row is named not counted",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    # DEEP IS OPT-IN, and the pair below is what says so: one generation is a
    # fact about an archive's HISTORY, and a fresh cut has exactly one.
    one = sealed(tmp, "gate-deep-one.dat")
    red, msg = refused_by_gate(one, deep=True)
    check(red and "generation" in msg,
          "deep=True refuses an archive with no fallback generation",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")
    check(not refused_by_gate(one)[0],
          "CONTROL: the SAME archive clears without deep -- the census is the "
          "thing that refused, not the archive")
    two = sealed(tmp, "gate-deep-two.dat")
    plant_generation(two, 0x1000, counter=6)
    deep = cleared_by_gate(two, deep=True)
    check(deep.get("generations") == 2,
          "and a planted older generation clears it, counted in the receipt",
          f"{deep.get('generations')} candidate(s)")

    print("\n12b. the identity tier: is the profile I built the one deployed?")
    base = sealed(tmp, "gate-fp-base.dat")
    want = fingerprint_block(base, (ROW_A, ROW_B, ROW_HEAD))
    ident = cleared_by_gate(base, fingerprints=want)
    check(ident.get("identity") and ident["identity"]["rows"] == 3,
          "an archive matching its own fingerprints clears, and says how many "
          "rows it matched", f"{ident.get('identity')}")

    # A DIFFERENT ARCHIVE, INTEGRITY-CLEAN. Row A's payload and its crc agree,
    # so every integrity rule is green; only the fingerprints can tell it apart.
    other = sealed(tmp, "gate-fp-other.dat")
    poke(other, ROWS[ROW_A][0], b"\x5A" * 32)
    reseal_row_crc(other, ROW_A)
    seal_self_crc(other)
    check(not refused_by_gate(other)[0],
          "CONTROL: a DIFFERENT archive is integrity-clean -- nothing above the "
          "identity tier can see the difference at all")
    red, msg = refused_by_gate(other, fingerprints=want)
    check(red and f"row {ROW_A}" in msg and "overlay.py --status" in msg,
          "but the identity tier names the row and the remedy",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    # The document shape a10stage actually writes: provenance fields beside a
    # `rows` block. Through a FILE, because that is how a launch site gets one.
    doc_path = os.path.join(tmp, "gate-fp.json")
    with open(doc_path, "w", encoding="utf-8") as fh:
        json.dump({"stage": base, "built": "2026-08-20", "rows": want}, fh)
    got = cleared_by_gate(base, fingerprints=doc_path)
    check(got.get("identity") and got["identity"]["rows"] == 3
          and "rows" in got["identity"]["source"],
          "a fingerprint DOCUMENT resolves to its row block and is named in the "
          "receipt", got.get("identity", {}).get("source", "(refused)")[-40:])

    # TWO BLOCKS AND NO NAMED ONE. An overlay document carries both sides of a
    # profile; picking one by position would pass on the archive it was written
    # to refuse.
    ambiguous = os.path.join(tmp, "gate-fp-ambiguous.json")
    with open(ambiguous, "w", encoding="utf-8") as fh:
        json.dump({"before": want, "after": fingerprint_block(other, (ROW_A,))},
                  fh)
    red, msg = refused_by_gate(base, fingerprints=ambiguous)
    check(red and "GUESS" in msg and "before" in msg and "after" in msg,
          "a document holding TWO unnamed row blocks is refused, naming both",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    absent = dict(want)
    absent[str(ENTRY_COUNT + 5)] = [1, "0x00000000", 0]
    red, msg = refused_by_gate(base, fingerprints=absent)
    check(red and "does not exist" in msg,
          "and a fingerprint naming a row this archive does not have is refused",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    # FAIL CLOSED ON UNREADABLE. Not a pass, and not the same answer as a
    # finding: the CLI has to keep 1 and 2 apart or a crash reads as a verdict.
    broken = sealed(tmp, "gate-broken.dat")
    poke(broken, MFT_OFF, b"XXXX")
    try:
        datcheck.assert_archive_safe(broken)
        unreadable, red = None, False
    except datcheck.ArchiveUnsafe as exc:
        unreadable, red = exc.unreadable, True
    check(red and unreadable is True,
          "an archive that cannot be read is REFUSED, and says so as unreadable",
          f"refused={red} unreadable={unreadable}")

    # A LOCK IS NOT DAMAGE, and the refusal has to say which one it is looking
    # at. A running client holds the archive it launched from exclusively --
    # Python raises PermissionError, not a partial read (RUNBOOK, "The third copy
    # of Gw.dat") -- so on the launch sites with no client census of their own,
    # the ONLY thing standing between "close the game" and "your 4.2 GB archive
    # is corrupt" is this sentence.
    check("Gw.exe" in datcheck._unreadable_remedy(
              PermissionError(13, "Permission denied")),
          "a refusal that could not read the archive because of a PERMISSION "
          "error names the running client as the cause")
    check("Gw.exe" not in datcheck._unreadable_remedy(ValueError("bad magic")),
          "and a refusal that could not PARSE it does not blame a client that "
          "may not exist -- the two readings stay apart")
    # End to end, against a real errno rather than a constructed one: a directory
    # where the archive should be. What that raises is the platform's business,
    # so the expectation is written against what it DID raise.
    standin = os.path.join(tmp, "gate-locked.dat")
    os.mkdir(standin)
    red, msg = refused_by_gate(standin, why="launch")
    check(red and ("Gw.exe" in msg) is isinstance(open_error(standin),
                                                  PermissionError),
          "and the live gate refuses an archive it cannot open, naming the lock "
          "exactly when the errno is the lock's",
          f"{type(open_error(standin)).__name__}: "
          f"{'names' if 'Gw.exe' in msg else 'does not name'} the client")

    print("\n12c. the gate through the real CLI")
    check(cli("--dat", good, "--assert-safe") == 0, "a healthy archive exits 0")
    check(cli("--dat", hdr, "--assert-safe") == 1,
          "a finding exits 1", "--assert-safe")
    check(cli("--dat", broken, "--assert-safe") == 2,
          "and an unreadable archive exits 2, never 1 -- a crash is not a "
          "verdict", "--assert-safe")
    out = run_cli("--dat", good, "--assert-safe").stdout
    check("archive gate:" in out and datcheck.ROW_CONVENTION in out,
          "the verb prints its receipt and the row convention above its numbers",
          out.splitlines()[0][:78] if out else "(no output)")
    check(cli("--dat", base, "--assert-safe", "--fingerprints", doc_path) == 0
          and cli("--dat", other, "--assert-safe", "--fingerprints", doc_path) == 1,
          "--fingerprints clears the archive it describes and refuses the one "
          "it does not", "exit 0 then 1")
    check(cli("--dat", one, "--assert-safe", "--deep") == 1
          and cli("--dat", two, "--assert-safe", "--deep") == 0,
          "--deep refuses a lone generation and clears a pair", "exit 1 then 0")

    print("\n12d. every launch site runs the gate ITSELF, and in the right order")
    # session.py's own comment, and it is the reason this is checked per SITE:
    # "A guard that only guards one of two doors is the shape of the defect it
    # is here to prevent -- vault/run held two patched binaries and one was
    # caged." Read by PATH, never imported: session.py pulls in ctypes windows
    # bindings and livesession.py pulls in the capture backend, and neither has
    # anything to do with whether the call is written down.
    # FOUR, not three. `drive_client.main` is the standalone operator launcher
    # and it is the OTHER of the two doors the comment above is about -- PLAN.md
    # names the pair outright ("both launch sites (`drive_client.py`,
    # `session.py`) assert it"). It went unlisted for one revision of this
    # section, which is the enumerated-sites version of the same defect: a list
    # of launch paths is only as good as its own census of them.
    harness = os.path.join(os.path.dirname(HERE), "harness")
    sites = {
        "session.run_client": (os.path.join(harness, "session.py"), "run_client"),
        "drive_client.main": (os.path.join(harness, "drive_client.py"), "main"),
        "livesession.preflight": (os.path.join(harness, "livesession.py"),
                                  "preflight"),
        "deploy.launch": (os.path.join(HERE, "deploy.py"), "launch"),
    }
    sources = {}
    for label, (path, fn) in sites.items():
        sources[label] = open(path, encoding="utf-8").read()
        check(len(gate_calls(sources[label], fn)) == 1,
              f"{label} calls assert_archive_safe itself",
              f"{len(gate_calls(sources[label], fn))} call(s) in {fn}()")

    # THE LIVE PATH TAKES NO FINGERPRINTS, and that is not an omission. The
    # live build's updater is LIVE by design and streams new content into its
    # own Gw.dat during a session, so the archive legitimately drifts -- a
    # fingerprint check there would refuse the one configuration that works.
    live_call = gate_calls(sources["livesession.preflight"], "preflight")[0]
    kwargs = {k.arg for k in live_call.keywords}
    check("fingerprints" not in kwargs,
          "and the LIVE site passes no fingerprints -- run-live's archive "
          "drifts on purpose", f"keywords: {sorted(kwargs)}")

    # AND THE LIVE SITE RUNS IT AFTER ITS CLIENT CENSUS, which is the half of
    # that site a presence check cannot see. See `gate_after_client_census`.
    gate_line, census_line = gate_after_client_census(
        sources["livesession.preflight"])
    check(gate_line is not None and census_line is not None
          and gate_line > census_line,
          "the LIVE site runs the gate BELOW its already-running-client refusal, "
          "so a held-open archive is diagnosed as a client and not as damage",
          f"gate at line {gate_line}, census refusal at line {census_line}")
    # NEGATIVE CONTROL for exactly that ordering: the same two statements the
    # other way round must come back the other way round.
    bad_gate, bad_census = gate_after_client_census(WRONG_ORDER_PREFLIGHT)
    check(bad_gate is not None and bad_census is not None
          and bad_gate < bad_census,
          "and a preflight written the other way round reads as the other way "
          "round, so the order check is measuring the order",
          f"gate at line {bad_gate}, census refusal at line {bad_census}")

    # THE SITE LIST IS ITSELF A CENSUS, and an enumerated list of launch paths is
    # only as good as it. Every file in the harness that hands an EXE to Popen is
    # a door; if one appears that this section does not name, the four checks
    # above go on passing while the new door stands open -- which is how
    # `drive_client.main` was missed. Read from disk, both sides.
    launchers = set()
    for path in sorted(glob.glob(os.path.join(harness, "*.py"))):
        if os.path.basename(path).startswith("test_"):
            continue
        src = open(path, encoding="utf-8").read()
        for n in ast.walk(ast.parse(src)):
            f = getattr(n, "func", None)
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name != "Popen" or not getattr(n, "args", None):
                continue
            first = ast.get_source_segment(src, n.args[0]) or ""
            if re.search(r"\bexe\b", first):
                launchers.add(os.path.normcase(path))
    named = {os.path.normcase(p) for p, _fn in sites.values()}
    check(launchers and launchers <= named,
          "and every harness file that hands an exe to Popen is one this "
          "section already names -- no unlisted fifth door",
          ", ".join(sorted(os.path.basename(p) for p in launchers))
          or "(found none, which is itself wrong)")

    # NEGATIVE CONTROL. Without it the checks above pass on any file that
    # merely mentions the name, and they would go on passing after the call was
    # deleted from a body they never re-parse.
    gutted = re.sub(r"[^\n]*assert_archive_safe\([^\n]*\n", "",
                    sources["deploy.launch"])
    check(gutted != sources["deploy.launch"]
          and not gate_calls(gutted, "launch"),
          "and deleting that one line from a COPY of deploy.py makes the check "
          "go red, so it is not satisfied by the name appearing somewhere")


# ------------------------------------------ the document the gate is handed --

def gate_raised(*args, **kw):
    """(exception name, `unreadable`, message) for one `assert_archive_safe`.

    CATCHES `BaseException` ON PURPOSE, and that is the whole point of the
    helper. The defect §12e is pointed at is five exception types leaving a
    launch gate raw -- `ValueError`, `struct.error`, `FileNotFoundError`,
    `JSONDecodeError` -- past every `except ArchiveUnsafe` in this tree,
    including the two helpers above. A helper that only caught `ArchiveUnsafe`
    would re-create the blind spot inside the test that is here to close it, and
    the run would die at whatever check came next with no red scored.
    """
    try:
        datcheck.assert_archive_safe(*args, **kw)
        return "CLEARED", None, ""
    except datcheck.ArchiveUnsafe as exc:
        return "ArchiveUnsafe", exc.unreadable, str(exc)
    except BaseException as exc:                            # noqa: BLE001
        return type(exc).__name__, None, str(exc)


def prefix_side(doc, source, side=None):
    """`_fingerprint_side` AS IT WAS before 2026-08-20. The negative control.

    A named block by tuple order, else the ONLY unnamed candidate, else refuse.
    Monkeypatched over the real resolver so the checks below can watch the whole
    gate -- not a re-expression of it -- clear the documents they now refuse.
    Without that, "the gate refuses X" is compatible with the gate having always
    refused X, and the fix would be unmeasured.
    """
    if datcheck._is_row_block(doc):
        return doc, source
    named = [k for k in ("rows", "staged")
             if isinstance(doc, dict) and datcheck._is_row_block(doc.get(k))]
    if named:
        return doc[named[0]], "%s[%r]" % (source, named[0])
    cands = sorted(k for k, v in doc.items() if datcheck._is_row_block(v)) \
        if isinstance(doc, dict) else []
    if len(cands) == 1:
        return doc[cands[0]], "%s[%r]" % (source, cands[0])
    raise datcheck.ArchiveUnsafe("two or more unnamed blocks: %s" % cands)


def prefix_parse(block):
    """The row parse AS IT WAS: `int(crc, 16)`, `int(size)`, and no lower bound."""
    out = {}
    for key, (size, crc, comp) in block.items():
        crc = int(crc, 16) if isinstance(crc, str) else int(crc)
        out[int(key)] = (int(size), crc & 0xFFFFFFFF, int(comp))
    return out


def raised_by(fn, *a):
    """The name of whatever `fn` raises, or "(nothing)"."""
    try:
        fn(*a)
        return "(nothing)"
    except Exception as exc:                                # noqa: BLE001
        return type(exc).__name__


def swap_id_records(path, first=0, second=1):
    """Swap the ROWS two file-id records name, and leave the archive healthy.

    Every row keeps the bytes it had; only the DIRECTORY changes. That is the
    state `overlay.deployed_state` exists to catch and the one a row-addressed
    comparison cannot see at all -- and it is not exotic: a client relocating
    rows during play is what `--verify-after` is for.
    """
    off, size = ROWS[ROW_IDTABLE][0], ROWS[ROW_IDTABLE][1]
    with open(path, "r+b") as fh:
        fh.seek(off)
        table = bytearray(fh.read(size))
        fid_a, row_a = struct.unpack_from("<II", table, first * 8)
        fid_b, row_b = struct.unpack_from("<II", table, second * 8)
        struct.pack_into("<II", table, first * 8, fid_a, row_b)
        struct.pack_into("<II", table, second * 8, fid_b, row_a)
        fh.seek(off)
        fh.write(bytes(table))
    reseal_row_crc(path, ROW_IDTABLE)
    return seal_self_crc(path)


def deployed_copy(tmp, name):
    """A sealed fixture with ROW_A rewritten legitimately -- payload and crc agree.

    Stands in for "the overlay is deployed": integrity-clean, and a different
    archive from the retail copy on exactly the rows a record fingerprints.
    """
    path = sealed(tmp, name)
    poke(path, ROWS[ROW_A][0], b"\x5A" * 40)
    reseal_row_crc(path, ROW_A)
    return seal_self_crc(path)


def write_doc(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return path


def section_gate_documents(tmp):
    """§12e. The FINGERPRINT DOCUMENT: whose word the identity tier takes.

    §12b showed the identity tier comparing rows. This is the seam on the other
    side of it -- `overlay.py` WRITES these documents and this gate READS them,
    and until 2026-08-20 no wired call site had ever passed the two together, so
    the contract between them had never been measured. A probe measured it and
    the two disagreed on the same bytes five ways. Each is checked here WITH a
    control that watches the pre-fix code clear the same input, because a
    refusal with no such control is compatible with the gate having always
    refused and would leave the fix unmeasured.

    STILL NO VAULT AND NO CLIENT. `overlay.py` resolves its record paths through
    `vaultpath`, so this section points `RURIK_VAULT` at its OWN temp directory
    and puts it back afterwards. The archives are the same 5.5 KB fixture every
    other section uses.
    """
    print("\n12e. the fingerprint document, and whose word the gate takes")
    was_vault = os.environ.get("RURIK_VAULT")
    try:
        _gate_documents(tmp)
    finally:
        if was_vault is None:
            os.environ.pop("RURIK_VAULT", None)
        else:
            os.environ["RURIK_VAULT"] = was_vault
        import vaultpath
        vaultpath._resolved = None


def _gate_documents(tmp):
    # ---- M1: the ADDRESSING UNIT -------------------------------------------
    # A plain document (no overlay header) carrying a `file_ids` block, so this
    # half needs neither overlay.py nor a vault.
    swapped = sealed(tmp, "doc-swapped.dat")
    want = fingerprint_block(swapped, (ROW_A, ROW_B))
    swap_id_records(swapped)
    ids = {str(ROW_A): ID_RECORDS[0][0], str(ROW_B): ID_RECORDS[1][0]}
    with_ids = write_doc(os.path.join(tmp, "doc-ids.json"),
                         {"rows": want, "file_ids": ids})
    no_ids = write_doc(os.path.join(tmp, "doc-no-ids.json"), {"rows": want})

    v = verdicts(swapped)
    pre_fix = all(
        (lambda f: (f["size"], f["crc"], f["extra_bytes"]))(
            datcheck.row_fields(datcheck.row_bytes(datcheck.read_mft(swapped),
                                                   int(r))))
        == (want[r][0], int(want[r][1], 16), want[r][2]) for r in want)
    check(all(v.values()) and not datcheck.crc_sweep(swapped)["bad"] and pre_fix,
          "CONTROL: an archive whose two file-id records were SWAPPED passes "
          "every integrity rule AND every row-number fingerprint -- comparing "
          "by row number cannot see this state at all",
          f"{sum(v.values())} of {len(v)} rules, row-addressed compare "
          f"{'clears' if pre_fix else 'refuses'}")

    red, msg = refused_by_gate(swapped, fingerprints=with_ids)
    check(red and ("file id 0x%X" % ID_RECORDS[0][0]) in msg
          and "REARRANGED" in msg and "overlay.py --status" in msg,
          "but with the document's file_ids the gate REFUSES, naming the id, "
          "the row it used to name and the rearrangement",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")
    got = cleared_by_gate(swapped, fingerprints=no_ids)
    check(got.get("identity", {}).get("addressing", "").startswith("BY ROW NUMBER")
          and "trusting the row numbers" in got.get("summary", ""),
          "and the SAME archive with a document carrying no file_ids clears -- "
          "which is allowed, and the one line a caller prints says outright "
          "that it is trusting row numbers",
          got.get("identity", {}).get("addressing", "(refused)")[:70])
    ok = cleared_by_gate(sealed(tmp, "doc-ok.dat"), fingerprints=no_ids)
    check(ok.get("identity", {}).get("addressing") == "BY ROW NUMBER -- this "
          "document carries no file_ids, so you are trusting the row numbers",
          "CONTROL: the wording is the receipt's, not a substring of the "
          "refusal -- an unswapped archive with the same document says it too",
          ok.get("summary", "(refused)")[-60:])

    # ---- the overlay record, and a vault of its own ------------------------
    vault = os.path.join(tmp, "e-vault")
    os.makedirs(vault, exist_ok=True)
    os.environ["RURIK_VAULT"] = vault
    import vaultpath
    vaultpath._resolved = None
    import overlay

    retail = sealed(tmp, "e-retail.dat")
    active = deployed_copy(tmp, "e-active.dat")
    mdir = os.path.join(tmp, "e-overlays")
    os.makedirs(os.path.join(mdir, "payloads"), exist_ok=True)
    with open(os.path.join(mdir, "payloads", "p.bin"), "wb") as fh:
        fh.write(b"a payload a reader must get back")
    mpath = os.path.join(mdir, "gate.toml")
    with open(mpath, "w", encoding="utf-8") as fh:
        fh.write('[overlay]\nname = "gate"\n'
                 'active = "%s"\nretail = "%s"\n'
                 '[[edit]]\nfile_id = 0x%X\ncompression = 0\n'
                 'plain = "payloads/p.bin"\nacknowledge_shared_with = []\n'
                 % (active.replace("\\", "/"), retail.replace("\\", "/"),
                    ID_RECORDS[0][0]))
    man = overlay.load_manifest(mpath)
    with overlay.Archive(man.retail) as ar:
        stamp = overlay.archive_identity(ar)
    base = {"format": overlay.FORMAT,
            "format_version": overlay.FORMAT_VERSION,
            "overlay": man.name, "manifest": man.path,
            "manifest_sha256": man.sha256, "built": "2026-08-20T00:00:00",
            "staged": overlay.staged_path(man, create=True),
            "journal": overlay.journal_path(man),
            "retail": stamp, "staged_identity": stamp,
            "file_ids": ids,
            "rows": fingerprint_block(active, (ROW_A, ROW_B)),
            "retail_rows": fingerprint_block(retail, (ROW_A, ROW_B))}
    canonical = overlay.fingerprints_path(man)
    overlay.write_fingerprints(canonical, base)

    def signed(name, mutate):
        """A doctored record with its digest RECOMPUTED -- one fault at a time."""
        doc = json.loads(json.dumps(base))
        mutate(doc)
        return overlay.write_fingerprints(os.path.join(tmp, name + ".json"), doc)

    check(not refused_by_gate(active, fingerprints=canonical)[0]
          and refused_by_gate(retail, fingerprints=canonical)[0],
          "FIXTURE PREMISE: the record clears the archive it describes and "
          "refuses the retail baseline -- so every refusal below is the "
          "document and never the rows")

    # ---- M2: the three trust checks overlay makes on the same file ----------
    variants = [
        ("self digest", lambda d: d.update({"self_sha256": "0" * 64}), False),
        ("manifest sha", lambda d: d.update({"manifest_sha256": "0" * 64}), True),
        ("retail stamp", lambda d: d["retail"].update({"mft_sha256": "0" * 64}),
         True),
        ("format_version", lambda d: d.update({"format_version": 99}), True),
    ]
    both = []
    for label, mutate, resign in variants:
        doc = json.loads(json.dumps(base))
        mutate(doc)
        if resign:
            overlay.write_fingerprints(canonical, doc)
        else:
            write_doc(canonical, doc)       # digest left stale ON PURPOSE
        try:
            overlay.load_fingerprints(man, why="check", kind="build")
            ov = "accept"
        except SystemExit:
            ov = "refuse"
        gate = "refuse" if refused_by_gate(active,
                                           fingerprints=canonical)[0] else "accept"
        both.append((label, ov, gate))
    overlay.write_fingerprints(canonical, base)         # put the good one back
    try:
        overlay.load_fingerprints(man, why="check", kind="build")
        pristine = ("accept", "accept" if not refused_by_gate(
            active, fingerprints=canonical)[0] else "refuse")
    except SystemExit:
        pristine = ("refuse", "-")
    check(all(ov == gate == "refuse" for _l, ov, gate in both)
          and pristine == ("accept", "accept"),
          "EQUIVALENCE: one document, two readers -- overlay.load_fingerprints "
          "and the gate agree accept/refuse on the pristine record and on each "
          "of the four doctored ones, so the trust checks cannot drift apart",
          "; ".join(f"{l}: overlay {o} / gate {g}" for l, o, g in both))

    doctored = signed("m2-stamp", lambda d: d["retail"].update(
        {"mft_sha256": "0" * 64}))
    red, msg = refused_by_gate(active, fingerprints=doctored)
    check(red and "RETAIL" in msg and "mft_sha256" in msg,
          "and the refusal names WHICH of the three failed and what it was "
          "measured against",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")

    was = datcheck._verify_overlay_record
    try:
        datcheck._verify_overlay_record = lambda doc, source: None
        pre = [not refused_by_gate(active, fingerprints=signed(
            "m2-pre-%d" % i, mutate))[0]
            for i, (_l, mutate, _r) in enumerate(variants[1:])]
        stale = json.loads(json.dumps(base))
        stale["self_sha256"] = "0" * 64
        pre.append(not refused_by_gate(active, fingerprints=write_doc(
            os.path.join(tmp, "m2-pre-self.json"), stale))[0])
    finally:
        datcheck._verify_overlay_record = was
    check(all(pre),
          "CONTROL: with the record check removed the gate CLEARS all four -- "
          "it was reading rows out of a file overlay.py will not open",
          f"{sum(pre)} of {len(pre)} cleared pre-fix")

    # ---- M3: a doctored SHAPE is a finding about the DOCUMENT ---------------
    plain = {"rows": fingerprint_block(active, (ROW_A,))}

    def plain_doc(name, mutate):
        doc = json.loads(json.dumps(plain))
        mutate(doc)
        return write_doc(os.path.join(tmp, name + ".json"), doc)

    shapes = [
        ("crc is not hex",
         plain_doc("m3-crc", lambda d: d["rows"][str(ROW_A)].__setitem__(
             1, "not-a-crc"))),
        ("size is a word",
         plain_doc("m3-size", lambda d: d["rows"][str(ROW_A)].__setitem__(
             0, "big"))),
        ("a negative row key",
         plain_doc("m3-neg", lambda d: d["rows"].update({"-1": [1, "0", 0]}))),
        ("the document is not there", os.path.join(tmp, "m3-absent.json")),
        ("truncated JSON", None),
    ]
    torn = os.path.join(tmp, "m3-torn.json")
    with open(torn, "w", encoding="utf-8") as fh:
        fh.write('{"rows": {"16": [1, "0", 0],')
    shapes[-1] = ("truncated JSON", torn)

    outcomes = []
    for label, path in shapes:
        kind, unreadable, msg = gate_raised(active, fingerprints=path)
        outcomes.append((label, kind, unreadable,
                         os.path.basename(path) in msg))
    check(all(k == "ArchiveUnsafe" and u is False and named
              for _l, k, u, named in outcomes),
          "every doctored document SHAPE refuses as ArchiveUnsafe with "
          "unreadable=False and the DOCUMENT named -- the archive was read and "
          "is not what failed",
          "; ".join(f"{l}: {k} unreadable={u}" for l, k, u, _n in outcomes))
    controls = [
        raised_by(prefix_parse, {str(ROW_A): [300, "not-a-crc", 0]}),
        raised_by(prefix_parse, {str(ROW_A): ["big", "0", 0]}),
        raised_by(lambda: datcheck.row_fields(
            datcheck.row_bytes(datcheck.read_mft(active), -1))),
        raised_by(lambda: open(shapes[3][1], encoding="utf-8")),
        raised_by(lambda: json.load(open(torn, encoding="utf-8"))),
    ]
    check(all(c not in ("(nothing)", "ArchiveUnsafe") for c in controls),
          "CONTROL: each of the five is a RAW exception in the pre-fix "
          "expression -- which is what escaped the gate, past every "
          "`except ArchiveUnsafe` in this tree",
          ", ".join(controls))
    rc = run_cli("--dat", active, "--assert-safe", "--fingerprints", shapes[0][1])
    check(rc.returncode == 1
          and "could not be read far enough" not in (rc.stdout + rc.stderr),
          "and at the CLI it is exit 1 with the document named, never exit 2 "
          "with the ARCHIVE blamed for it",
          f"exit {rc.returncode}: "
          f"{(rc.stdout + rc.stderr).strip().splitlines()[0][:60]}")

    # ---- M4: no fall-through to the other side of a profile -----------------
    gone = signed("m4-gone", lambda d: d.pop("rows"))
    empty = signed("m4-empty", lambda d: d.update({"rows": {}}))
    reds = [refused_by_gate(retail, fingerprints=p) for p in (gone, empty)]
    check(all(r for r, _m in reds)
          and all("retail_rows" in m and "fall-through" in m for _r, m in reds),
          "a record whose `rows` side is REMOVED or EMPTY refuses against a "
          "retail archive, naming the side that is missing and the block it "
          "did NOT fall through to",
          reds[0][1].splitlines()[1].strip()[:78] if reds[0][0] else "CLEARED IT")
    was = datcheck._fingerprint_side
    try:
        datcheck._fingerprint_side = prefix_side
        pre = [cleared_by_gate(retail, fingerprints=p) for p in (gone, empty)]
    finally:
        datcheck._fingerprint_side = was
    check(all(c.get("identity", {}).get("source", "").endswith("['retail_rows']")
              for c in pre),
          "CONTROL: the pre-fix resolver CLEARS both against retail, out of "
          "`retail_rows` -- the caller asked whether its overlay was deployed "
          "and got a pass on an archive carrying none of it",
          "; ".join(c.get("identity", {}).get("source", "(refused)")[-14:]
                    for c in pre))
    check(not refused_by_gate(retail, fingerprints=canonical,
                              side="retail_rows")[0]
          and refused_by_gate(active, fingerprints=canonical,
                              side="retail_rows")[0],
          "and side='retail_rows' is how that question is asked DELIBERATELY: "
          "it clears the baseline and refuses the deployed archive",
          "clear then refuse")

    # ---- M5: two names for one side is an ambiguity, not a precedence -------
    ambig = signed("m5-both", lambda d: d.update({"staged": dict(d["rows"])}))
    red, msg = refused_by_gate(active, fingerprints=ambig)
    check(red and "'rows'" in msg and "'staged'" in msg and "GUESS" in msg
          and "side=" in msg,
          "a record holding BOTH `rows` and `staged` -- two names for the same "
          "side -- refuses naming both and saying how to choose",
          msg.splitlines()[1].strip()[:78] if red else "CLEARED IT")
    try:
        datcheck._fingerprint_side = prefix_side
        pre = cleared_by_gate(active, fingerprints=ambig)
    finally:
        datcheck._fingerprint_side = was
    check(pre.get("identity", {}).get("source", "").endswith("['rows']"),
          "CONTROL: the pre-fix resolver took the first key of a two-tuple, "
          "silently -- no note, no refusal",
          pre.get("identity", {}).get("source", "(refused)")[-12:])
    check(not refused_by_gate(active, fingerprints=ambig, side="rows")[0],
          "and naming the side resolves it -- the ambiguity is in the QUESTION, "
          "not in the document")

    # ---- M6: an argument that did nothing is a pass on the wrong archive ----
    check(cli("--dat", retail, "--preflight", "--fingerprints", canonical) != 0
          and cli("--dat", retail, "--preflight", "--deep") != 0
          and cli("--dat", retail, "--preflight", "--side", "rows") != 0,
          "--fingerprints, --deep and --side without --assert-safe are refused "
          "as nonsense invocations rather than silently ignored",
          "three refusals")
    check(cli("--dat", retail, "--preflight") == 0,
          "CONTROL: --preflight alone still exits 0, so the check above is "
          "measuring the dependency and not the verb")


# ------------------------------------------------------------------ main --

def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datcheck-")
    try:
        run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


def fresh(tmp, name):
    return build_archive(os.path.join(tmp, name))


def run(tmp):
    print("\n0. the fixture is a healthy archive")
    good = fresh(tmp, "good.dat")
    got, facts = datcheck.preflight(good)
    for c in got:
        if not c.ok:
            print("   unexpected: " + c.line())
    check(len(got) == len(ALL_ITEMS), "the pre-flight makes every declared item",
          f"{len(got)} of {len(ALL_ITEMS)}")
    check(all(c.ok for c in got), "a clean fixture passes every item",
          f"{sum(1 for c in got if c.ok)}/{len(got)}")
    inv = facts["invariant"]
    check(inv["first_stream_rows"] == 4 and inv["rows_named"] == 4,
          "the directory invariant counts the four head rows",
          f"first_stream={inv['first_stream_rows']} named={inv['rows_named']}")
    check(inv["released_records"] == 1,
          "a (0, 0) record is counted as RELEASED, not dangling",
          f"released={inv['released_records']} dangling={len(inv['dangling_records'])}")
    # The partner is the row shape that proves the invariant is not simply
    # "every USED row is named": it is USED, it is >= 16, and it has no record.
    check(not inv["orphan_rows"],
          "a USED non-first stream needs no file-id record",
          f"orphans={inv['orphan_rows']}")

    print("\n0b. every row this tool names carries its own identity")
    # WHY THIS IS HERE AND NOT ONLY IN test_archive. `row_identity` exists
    # because two bare integers were the whole of the evidence in
    # `studies/crossbuild/FINDINGS.md` §4b.1: `--diff` said row 71496 changed
    # and `deploy.py` said "head 71496, partner 71497", and the pair was read as
    # the client having eaten an authored map. It had not -- 71496 is the
    # Bloated HEAD that `deploy` arms to zero on purpose, and the re-bloat is
    # the experiment working. `test_archive.py` §1c checks the labels against a
    # 4 GB archive; this checks the LOGIC on a 5.5 KB fixture whose head,
    # partner, spare and reserved rows are known by construction, so it runs on
    # a bare machine and can be wrong for exactly one reason.
    mft = datcheck.read_mft(good)
    records, _blob = datcheck.file_id_records(good, mft,
                                              datcheck.read_header(good))
    ident = datcheck.row_identity(mft, records)
    check(role_of(ident, ROW_HEAD) == "stream head"
          and ids_of(ident, ROW_HEAD) == [0x1002],
          "the head row is a stream head and carries its file id",
          f"{role_of(ident, ROW_HEAD)!r} {ids_of(ident, ROW_HEAD)}")
    # The partner is the whole point: it is USED, it has NO file-id record, and
    # `alloc.nextStream` is the only thing in the archive that names it. A
    # labeller reading the directory alone would call it anonymous, which is
    # precisely the row a reader most needs told apart from its head.
    check(role_of(ident, ROW_PARTNER) == f"stream partner of row {ROW_HEAD}"
          and not ids_of(ident, ROW_PARTNER),
          "the partner names the head that points at it, from nextStream alone",
          f"{role_of(ident, ROW_PARTNER)!r} {ids_of(ident, ROW_PARTNER)}")
    check(role_of(ident, 0) == "MFT descriptor"
          and role_of(ident, datcheck.MFT_SELF_ROW) == "the MFT itself"
          and role_of(ident, datcheck.FILE_ID_TABLE_ROW) == "file-id table"
          and role_of(ident, 7) == "reserved spare",
          "rows 0..15 get the client's own structural names",
          f"0={role_of(ident, 0)!r} 7={role_of(ident, 7)!r}")
    # A (0, 0) record is a RELEASED slot. Filing it under row 0 would put file
    # id 0 on the MFT descriptor and make the descriptor read as a file.
    check(ids_of(ident, 0) == [],
          "the released (0, 0) record does not name row 0",
          f"{ids_of(ident, 0)}")
    check(datcheck.label_row(ident, ROW_HEAD)
          == f"row {ROW_HEAD} [file id 0x1002; stream head]"
          and datcheck.label_row(None, ROW_HEAD) == f"row {ROW_HEAD}",
          "label_row prints the identity, and a BARE row when it has none",
          datcheck.label_row(ident, ROW_HEAD))
    # A spare and a row something still points at are the two USED-clear shapes,
    # and the pre-flight treats them differently -- one is the allocator working
    # (row 35301 in the owner's own install), one is corruption. The label must
    # separate them too, or a diff line contradicts the gate above it.
    spare = fresh(tmp, "ident_spare.dat")
    poke_row(spare, ROW_D, flags=0x0002)         # USED clear, nothing points here
    s_mft = datcheck.read_mft(spare)
    s_ident = datcheck.row_identity(
        s_mft, datcheck.file_id_records(spare, s_mft,
                                        datcheck.read_header(spare))[0])
    lost = fresh(tmp, "ident_lost.dat")
    poke_row(lost, ROW_PARTNER, flags=0x0000)    # USED clear, the head points here
    l_mft = datcheck.read_mft(lost)
    l_ident = datcheck.row_identity(
        l_mft, datcheck.file_id_records(lost, l_mft,
                                        datcheck.read_header(lost))[0])
    check(role_of(s_ident, ROW_D) == "free spare"
          and role_of(l_ident, ROW_PARTNER)
          == f"USED CLEAR but row {ROW_HEAD} points here",
          "a free spare and a referenced row that lost USED are labelled apart",
          f"{role_of(s_ident, ROW_D)!r} vs {role_of(l_ident, ROW_PARTNER)!r}")

    print("\n1. every pre-flight item goes red on its own")

    p = fresh(tmp, "mod0.dat")
    poke(p, 0x1C, struct.pack("<I", 1))
    expect_only(p, "0x1C bit 0 set", "0x1C bit 0 clear")

    p = fresh(tmp, "mod1.dat")
    poke(p, 0x1C, struct.pack("<I", 2))
    expect_only(p, "0x1C bit 1 set", "0x1C bit 1 clear")

    p = fresh(tmp, "hdrcrc.dat")
    poke(p, 0x0C, struct.pack("<I", 0xDEADBEEF))
    expect_only(p, "header CRC corrupted", "header CRC over 0x00..0x0C")

    p = fresh(tmp, "misalign.dat")
    poke_row(p, ROW_PARTNER, offset=0x0E04)
    expect_only(p, "one extent misaligned by 4", "every extent 512-aligned")

    p = fresh(tmp, "eof.dat")
    poke_row(p, ROW_D, offset=0x1400, size=0x300)
    expect_only(p, "one extent past EOF", "every extent inside EOF")

    p = fresh(tmp, "overlap.dat")
    poke_row(p, ROW_HEAD, offset=0x0800)
    expect_only(p, "two extents overlapping", "no overlapping reservations")

    p = fresh(tmp, "orphan.dat")
    # The record that named row 18 now names row 19 twice: row 18 keeps its
    # USED|FIRST flags and loses its directory record, which is exactly the row
    # the client's reconcile pass DELETES by name at the next open.
    poke(p, ROWS[ROW_IDTABLE][0] + 2 * 8, struct.pack("<II", 0x1002, ROW_D))
    expect_only(p, "a USED|FIRST row with no record",
                "every USED|FIRST row >= 16 is named")

    p = fresh(tmp, "dangling.dat")
    # The released (0, 0) slot becomes a record naming an all-zero reserved row.
    poke(p, ROWS[ROW_IDTABLE][0] + 4 * 8, struct.pack("<II", 0x1004, 7))
    expect_only(p, "a record naming a non-USED row",
                "every file-id record names a USED row")

    p = fresh(tmp, "lowrow.dat")
    # Four bytes in row 7's crc field, and nothing else. Its flags stay clear so
    # the row is not USED and the extent items cannot see it -- writing 24 bytes
    # of 0x11 sets FLAG_ENTRY_USED and trips the alignment and EOF items too,
    # which is a broader sabotage than the item being isolated.
    poke(p, MFT_OFF + 7 * ENTRY_SIZE + 0x14, struct.pack("<I", 0x11223344))
    expect_only(p, "a reserved row below 16 written",
                "no row below index 16 touched")

    # A PARTNER losing USED is corruption: nothing but `alloc.nextStream` reaches
    # it, so the file-id record item cannot see it and this is the only item that
    # can. It must still go red, alone.
    p = fresh(tmp, "unused.dat")
    poke_row(p, ROW_PARTNER, flags=0x0000)
    expect_only(p, "a referenced partner left USED-clear",
                "no USED-clear row that something points at")

    # THE CONTROL, and the reason this item was rewritten on 2026-08-13: a row that
    # NOTHING points at is a SPARE, and refusing it refused ArenaNet's own shipped
    # archive. The owner's install carries exactly one (row 35301, which `datplan`
    # already records the client CLAIMING when it wanted a slot) and pre-flight
    # answered REFUSE, 9 of 10, on a file the retail client opens every day. A gate
    # that reddens on the real target is not a gate, it is a tool nobody can run.
    #
    # It is the SAME ROW in the SAME state as the sabotage above -- USED clear, on
    # row 20 -- and the only difference is that the head no longer points at it. So
    # this pair isolates the reference and nothing else: if the item ever goes back
    # to reading the flag alone, exactly one of these two goes the wrong way.
    p = fresh(tmp, "spare.dat")
    poke_row(p, ROW_PARTNER, flags=0x0000)
    poke_row(p, ROW_HEAD, nxt=0)
    got, _facts = datcheck.preflight(p)
    bad = [c.name for c in got if not c.ok]
    check(not bad, "CONTROL: the same row, unreferenced, is a SPARE and not a fault",
          "red: %s" % (bad or "none -- as on the owner's own install"))
    item = [c for c in got
            if c.name == "no USED-clear row that something points at"][0]
    check("spare" in item.detail and str(ROW_PARTNER) in item.detail,
          "and the spare is REPORTED rather than dropped", item.detail[:78])

    print("\n2. the baseline check compares the reserved rows byte for byte")
    base = fresh(tmp, "base.dat")
    snap = datcheck.snapshot(base)
    label = "reserved rows 1, 4..15 identical to the baseline"

    # Row 1's nextStream: a field the structural item does not look at, on a row
    # nothing should ever touch. This is the gap the baseline exists to close.
    moved = fresh(tmp, "moved.dat")
    poke_row(moved, ROW_HEADER, nxt=0x1234)
    v = {c.name: c.ok for c in datcheck.preflight(moved, baseline=snap)[0]}
    check(label in v, "a baseline adds the exact reserved-rows item")
    check(v.get(label) is False,
          "a changed reserved row is caught by the baseline",
          "row 1's nextStream moved and the structural item cannot see it")
    check(v.get("no row below index 16 touched") is True,
          "and the structural item alone would have passed it",
          "which is why the baseline item exists")

    # ...and a container row moving must NOT redden it. `datwrite.py` rewrites
    # row 3's self-crc after every --replace, so an item that went red on that
    # would be red after every legitimate write and would stop being read.
    flushed = fresh(tmp, "flushed.dat")
    poke_row(flushed, ROW_SELF, crc=0x99999999)
    poke(flushed, MFT_OFF + 0x04, struct.pack("<I", 8))
    v = {c.name: c.ok for c in datcheck.preflight(flushed, baseline=snap)[0]}
    check(v.get(label) is True,
          "but rows 0/2/3 moving does not redden it -- they move on any write",
          "the containers are reported beside the verdict instead")

    print("\n3. the detector classifies what the checksums cannot see")
    before_path = fresh(tmp, "before.dat")
    before = datcheck.snapshot(before_path)

    same = datcheck.diff(before, path=before_path)
    check(same["unchanged"] and not same["changes"],
          "an untouched archive diffs to no change", f"{same['counts']}")

    p = fresh(tmp, "reloc.dat")
    poke_row(p, ROW_A, offset=0x1000, size=310, crc=0xAABBCCDD)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_A) == datcheck.RELOCATED,
          "a new extent on a stable identity is a RELOCATION", f"{kinds}")
    check(not d["unchanged"] and d["counts"].get(datcheck.RELOCATED) == 1,
          "and it is the only change reported", f"{d['counts']}")

    p = fresh(tmp, "recycle.dat")
    poke_row(p, ROW_B, flags=0x0C01, offset=0x1000, crc=0x1)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_B) == datcheck.RECYCLED,
          "a changed +0x0E/+0x0F is a RECYCLED row", f"{kinds}")

    p = fresh(tmp, "delete.dat")
    poke(p, MFT_OFF + ROW_D * ENTRY_SIZE, b"\x00" * ENTRY_SIZE)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_D) == datcheck.DELETED,
          "an all-zero row is a DELETE", f"{kinds}")

    p = fresh(tmp, "relink.dat")
    poke_row(p, ROW_A, nxt=ROW_PARTNER)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_A) == datcheck.RELINKED,
          "a lone +0x10 change is a sibling RELINK", f"{kinds}")

    p = fresh(tmp, "weird.dat")
    poke_row(p, ROW_A, offset=0x1000, nxt=ROW_PARTNER)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_A) == datcheck.UNCLASSIFIED,
          "a shape the table does not name is reported, not dropped", f"{kinds}")

    p = fresh(tmp, "counter.dat")
    poke(p, MFT_OFF + 0x04, struct.pack("<I", 8))
    d = datcheck.diff(before, path=p)
    check("descriptor_counter" in d["tier0"] and not d["changes"],
          "TIER 0: the descriptor counter alone is a change signal",
          f"{d['tier0']}")

    p = fresh(tmp, "dir.dat")
    poke(p, ROWS[ROW_IDTABLE][0], struct.pack("<II", 0x9999, ROW_A))
    d = datcheck.diff(before, path=p)
    check("file_id_sha256" in d["tier2"],
          "TIER 2: a rewritten directory is caught by its digest",
          f"{sorted(d['tier2'])}")
    check(not d["changes"] and not d["tier0"],
          "and it is invisible to TIER 0 and TIER 1", f"{d['counts']}")

    # Rows 0, 2 and 3 change on every flush. They must be separated out rather
    # than counted, or every post-flight would report three findings it cannot
    # act on.
    p = fresh(tmp, "flush.dat")
    poke_row(p, ROW_SELF, crc=0x55555555)
    d = datcheck.diff(before, path=p)
    check(not d["changes"] and [r["row"] for r in d["corroboration"]] == [ROW_SELF],
          "rows 0/2/3 are corroboration, not findings",
          f"changes={d['counts']} corroboration={[r['row'] for r in d['corroboration']]}")
    check(not d["unchanged"],
          "but a corroboration-only diff is still not 'unchanged'")

    print("\n3b. the OUTPUT a human reads, which nothing was checking")
    # THE HALF THAT PREVENTS THE MISTAKE IS THE HALF THAT GETS PRINTED, and it
    # had zero checks on it. `row_identity` was pinned in §0b, `label_row` too,
    # and `format_diff` -- which is the only thing an operator ever sees -- was
    # referenced by no test in the tree. MEASURED: a sabotage that reverted
    # `format_diff` and the `--preflight` banner to the exact pre-fix bare
    # output (no convention line, no NOT IDENTIFIED banner, `row %-7d`, a bare
    # `[0, 2, 3]` corroboration list) left this file at 75/75 and
    # `test_archive.py` at 29/29, both exit 0. A straight revert of the fix was
    # green in both directions, which means the fix was documentation.
    p = fresh(tmp, "fmt.dat")
    poke_row(p, ROW_HEAD, offset=0x1600, size=6012, crc=0xAABBCCDD)
    poke_row(p, ROW_SELF, crc=0x55555555)          # a corroboration row too
    text = datcheck.format_diff(datcheck.diff(before, path=p))
    check(datcheck.ROW_CONVENTION in text,
          "--diff names the row convention above its numbers",
          text.splitlines()[1][:72] + "...")
    # The changed row must arrive WEARING its identity. `ROW_HEAD` is the
    # fixture's map head and 0x1002 is its file id -- the two tokens `deploy.py`
    # prints on its own first line, which is what makes the two outputs
    # matchable at all.
    check(f"row {ROW_HEAD} [file id 0x1002; stream head]" in text,
          "and the changed row carries its file id and role, not a bare number",
          [ln.strip() for ln in text.splitlines()
           if str(ROW_HEAD) in ln][:1])
    # ...and NO row line anywhere in the output may be bare. Asserted over every
    # `row N` line rather than over the one row this fixture changed, because
    # the pre-fix formatter printed `   row 18      relocated` -- which contains
    # the substring `row 18` and would satisfy a check written the obvious way.
    # A label is a claim about identity; a padded integer is the thing that cost
    # the afternoon.
    row_lines = [ln for ln in text.splitlines()
                 if re.match(r"^\s+row \d+", ln)]
    check(len(row_lines) >= 2 and all("[" in ln for ln in row_lines),
          f"and EVERY row line in the output is labelled ({len(row_lines)} "
          f"lines, changed and corroboration alike) -- none is the bare padded "
          f"integer the pre-fix formatter printed",
          [ln.strip() for ln in row_lines if "[" not in ln][:2])
    check(f"row {datcheck.MFT_SELF_ROW} [" in text
          and "[0, 2, 3]" not in text and "[3]" not in text,
          "and the corroboration rows are labelled too, not printed as a list "
          "of integers")
    check("NOT IDENTIFIED" not in text,
          "a diff taken against a live archive does NOT wear the banner")

    # THE TWO-SNAPSHOT CASE, which is the one that has no archive behind it.
    two = datcheck.diff(before, after=datcheck.snapshot(p))
    two_text = datcheck.format_diff(two)
    check(not two["identified"] and "NOT IDENTIFIED" in two_text
          and f"row {ROW_HEAD} [" not in two_text,
          "two snapshots compared: NOT IDENTIFIED, and no row invents an "
          "identity it does not have", f"identified={two['identified']}")

    # THE TRAP THE FIX INTRODUCED. `diff(before, path=X, after=<snapshot of Y>)`
    # took its ROWS from Y and its IDENTITY from X and reported identified=True.
    # On a measured pair of vault archives 308 of 343 labels named a file the
    # after-image does not hold -- the exact "a label that names the wrong file
    # reads as identification" failure this whole change exists to prevent. No
    # shipped caller reaches it, which is why it survived review.
    #
    # The guard is the MFT ITSELF, byte for byte, so the POSITIVE CONTROL is not
    # optional: `other` is a DIFFERENT archive, and `p` is the SAME one, and the
    # gate has to tell them apart from the bytes rather than from the path.
    other = fresh(tmp, "fmt-other.dat")
    poke_row(other, ROW_A, offset=0x1000, size=310, crc=0x11223344)
    crossed = datcheck.diff(before, path=p, after=datcheck.snapshot(other))
    check(not crossed["identified"] and crossed["identity_note"]
          and "NOT IDENTIFIED" in datcheck.format_diff(crossed)
          and not any("file id" in r["label"] for r in crossed["changes"]),
          "an `after` from a DIFFERENT archive than `path` is refused a label, "
          "and the banner says which archive disagreed",
          (crossed["identity_note"] or "")[:60] + "...")
    same_again = datcheck.diff(before, path=p, after=datcheck.snapshot(p))
    check(same_again["identified"] and same_again["identity_note"] is None
          and any("file id 0x1002" in r["label"]
                  for r in same_again["changes"]),
          "and the SAME archive passed both ways still labels -- a gate that "
          "refused every explicit `after` would protect nothing")

    print("\n4. the snapshot is a real record, and it refuses a stale one")
    snap = datcheck.snapshot(before_path)
    mft = datcheck._snapshot_mft(snap)
    check(len(mft) == MFT_SIZE and mft[:4] == MFT_MAGIC,
          "TIER 1 holds the whole table, all 24 bytes of every row",
          f"{len(mft)} B, {snap['tier1']['rows']} rows")
    check(snap["tier0"]["descriptor_counter"] == 7
          and snap["tier0"]["mft_offset"] == MFT_OFF,
          "TIER 0 holds the counter and the MFT's location", f"{snap['tier0']}")
    stale = dict(snap)
    stale["snapshot_version"] = 999
    stale_path = os.path.join(tmp, "stale.json")
    with open(stale_path, "w", encoding="utf-8") as fh:
        json.dump(stale, fh)
    try:
        datcheck.load_snapshot(stale_path)
        refused = False
    except ValueError:
        refused = True
    check(refused, "a snapshot from another version is refused, not read")

    torn = json.loads(json.dumps(snap))
    torn["tier1"]["mft_sha256"] = "0" * 64
    try:
        datcheck._snapshot_mft(torn)
        caught = False
    except ValueError:
        caught = True
    check(caught, "a snapshot whose MFT does not match its own digest is refused")

    print("\n5. the MFT is located from a header read in the same call")
    # The MFT moves. A reader that seeks to a remembered offset reads the wrong
    # table and diffs it against itself; this is the one property of the whole
    # module that a wrong answer looks identical to a right one.
    p = fresh(tmp, "moved-mft.dat")
    with open(p, "r+b") as fh:
        fh.seek(MFT_OFF)
        table = fh.read(MFT_SIZE)
        fh.seek(0x1000)
        fh.write(table)
        fh.seek(MFT_OFF)
        fh.write(b"\xEE" * MFT_SIZE)
        fh.seek(0x10)
        fh.write(struct.pack("<Q", 0x1000))
    poke_row(p, ROW_SELF, offset=0x1000)
    hdr = datcheck.read_header(p)
    check(hdr["mft_offset"] == 0x1000,
          "the header is re-read, so a moved MFT is found where it now is")
    moved_mft = datcheck.read_mft(p)
    check(moved_mft[:4] == MFT_MAGIC and len(moved_mft) == MFT_SIZE,
          "and the table read from the new location is the table")
    d = datcheck.diff(before, path=p)
    check(d["tier0"].get("mft_offset", {}).get("after") == 0x1000,
          "TIER 0 reports the move", f"{sorted(d['tier0'])}")

    print("\n6. archive.py honours RURIK_DAT")
    saved = os.environ.get("RURIK_DAT")
    try:
        os.environ.pop("RURIK_DAT", None)
        mod = importlib.reload(archive_mod)
        check(mod.DEFAULT_DAT.lower().endswith("dat_study\\gw.dat")
              or mod.DEFAULT_DAT.lower().endswith("dat_study/gw.dat"),
              "with the variable unset, DEFAULT_DAT is the study copy",
              mod.DEFAULT_DAT)
        os.environ["RURIK_DAT"] = before_path
        mod = importlib.reload(archive_mod)
        check(mod.DEFAULT_DAT == before_path,
              "with it set, DEFAULT_DAT follows it", mod.DEFAULT_DAT)
        with mod.Archive() as ar:
            check(ar.entry_count == ENTRY_COUNT and ar.path == before_path,
                  "and Archive() with NO path opens that archive",
                  f"{ar.entry_count} entries from {os.path.basename(ar.path)}")
        # The lever has to be a lever, not a constant nobody reads: point it at
        # a file that is not an archive and the default open must fail there.
        notdat = os.path.join(tmp, "not-an-archive.bin")
        with open(notdat, "wb") as fh:
            fh.write(b"nope" * 16)
        os.environ["RURIK_DAT"] = notdat
        mod = importlib.reload(archive_mod)
        try:
            mod.Archive().close()
            refused = False
        except ValueError:
            refused = True
        check(refused, "and a bad RURIK_DAT fails at the override, not silently "
                       "at the old default")
    finally:
        if saved is None:
            os.environ.pop("RURIK_DAT", None)
        else:
            os.environ["RURIK_DAT"] = saved
        importlib.reload(archive_mod)

    print("\n7. the three exit codes stay apart")
    # `--diff` exits 1 to mean "the archive CHANGED", which is a result. If an
    # archive this tool cannot read exited 1 as well, anything reading the code
    # would report a crash as that result -- so unreadable is its own code, and
    # the run sheet's "exit 1 means something changed" only holds because of it.

    clean = fresh(tmp, "exit-clean.dat")
    snap_path = os.path.join(tmp, "exit.json")
    datcheck.write_snapshot(clean, snap_path)

    # BOTH VERBS, THROUGH THE REAL CLI. §3b checks `format_diff` as a function;
    # this is the only place the `--preflight` banner is reached at all, and it
    # is a separate `print` in `_main` that the function-level checks cannot
    # see -- the revert sabotage deleted it and §3b's six reds did not include
    # it. A convention line nobody prints is a convention line nobody reads.
    banner_dat = fresh(tmp, "exit-banner.dat")
    poke_row(banner_dat, ROW_A, offset=0x1000)
    pre_out = run_cli("--dat", clean, "--preflight").stdout
    diff_out = run_cli("--dat", banner_dat, "--diff", snap_path).stdout
    check(datcheck.ROW_CONVENTION in pre_out
          and datcheck.ROW_CONVENTION in diff_out,
          "both verbs print the row convention through the real CLI, not just "
          "through format_diff()",
          f"preflight={datcheck.ROW_CONVENTION in pre_out} "
          f"diff={datcheck.ROW_CONVENTION in diff_out}")

    check(cli("--dat", clean, "--preflight") == 0,
          "a clean archive exits 0", "--preflight")
    check(cli("--dat", clean, "--diff", snap_path) == 0,
          "an unchanged archive exits 0", "--diff")
    changed = fresh(tmp, "exit-changed.dat")
    poke_row(changed, ROW_A, offset=0x1000)
    check(cli("--dat", changed, "--diff", snap_path) == 1,
          "a changed archive exits 1 -- a RESULT, not an error", "--diff")
    broken = fresh(tmp, "exit-broken.dat")
    poke(broken, MFT_OFF, b"XXXX")           # no MFT where the header says
    check(cli("--dat", broken, "--preflight") == 2,
          "an archive that cannot be read exits 2, not 1", "--preflight")
    check(cli("--dat", broken, "--diff", snap_path) == 2,
          "and 2 from --diff too, so a crash is never read as 'it changed'",
          "--diff")

    section_generations(tmp)
    section_crc_sweep(tmp)
    section_growth(tmp)
    section_mft_offset_width(tmp)
    section_launch_gate(tmp)
    section_gate_documents(tmp)


if __name__ == "__main__":
    sys.exit(main())
