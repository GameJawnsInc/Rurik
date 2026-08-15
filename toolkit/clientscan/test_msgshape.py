"""The message tables, derived from the image rather than remembered.

    python toolkit/clientscan/test_msgshape.py

WHY THIS FILE EXISTS, and it is the reason `studies/crossbuild/PLAN.md` put
`msgshape.py` first. `msgshape` is the tool that reads the client's own
message-format tables; `msghandler.py` and `test_catalog.py` are built on it,
and the 477/477 catalog agreement rests on it. It had no test and no runner, and
its 25 table addresses were measured on build 38797.

MEASURED 2026-08-12, before the fix, against `2026-04-30_b174de1f2d8d`:

    cmd slots 0, statically present 0, zero in file 0, recovered 0
      oracle 0x001E FAIL  (and 0x0020, 0x0029, 0x002C)
      descriptor invariant violations: 0
    EXIT=0

Three defects in four lines. The invariant line is VACUOUS -- zero descriptors
cannot violate anything, and it printed byte-identically to the healthy build's.
`CENSUS_38797` was never asserted against. And the process exited 0, so nothing
downstream could notice. 651 of the 751 table entries had died at one `continue`
in `_enumerate`; a `continue` is not a refusal. Meanwhile `msgshape.py 0x00E5`
answered "opcode 0x00e5 is in no table on this build" -- a statement about
ArenaNet's client, and false: the opcode is there, with the same shape, at that
build's own address.

WHAT THIS FILE PINS, and each of these was broken on purpose to check it reddens:

  * the anchor is UNIQUE, and the thing that looks like the obvious anchor is
    not. §0's negative control is the routine's own 7-byte prologue: 56 hits on
    38797, 57 on the older build. An implementation that searched on it and took
    the first hit would resolve the wrong routine in silence, which is exactly
    what rule 1 of PLAN §7 exists to forbid.
  * the derivation reproduces `TABLES_38797` EXACTLY on the build that constant
    was measured on -- and this is the weak half, because a function that simply
    returned the constant would pass it. §2 is the half that cannot be faked: the
    same code, no constant in reach, must recover 25 tables from a build whose
    every table address is different.
  * a run that measures nothing FAILS. §3 drives `measured_nothing()` with a
    doctored table set, and pairs it with the positive control on real builds --
    a predicate that answers True to everything would satisfy the first half
    alone.

Every section needs the vault; there is no useful vault-less half here, because
every claim is about ArenaNet's bytes and a run that has seen none of them
cannot refute anything. Floor 37, ~35 s.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                                # noqa: E402
import msgshape as MS                                        # noqa: E402
import pinned                                                # noqa: E402
import vaultpath                                             # noqa: E402
from gwpe import PE                                          # noqa: E402

# floor re-measured 2026-08-14 from a real green run: 37 -> 44, build 38833 joining pinned.BUILDS.
LEDGER = checks.Ledger("msgshape table derivation", floor=44)
check = checks.adopt(LEDGER)

# The routine's real entry prologue -- `push ebp / mov ebp,esp / sub esp,0x20 /
# mov eax,[disp32]`. Kept here as the NEGATIVE CONTROL, never used to find
# anything. See section 0.
GENERIC_PROLOGUE = bytes.fromhex("558bec83ec20a1")

EXPECT_ENTRY = {
    "2026-07-29_221c13772c7a": 0x007DE010,      # studies/msgtable/FINDINGS.md §3
    "2026-04-30_b174de1f2d8d": 0x007D7CE0,
    # 38833, MEASURED 2026-08-14: the SAME VA as 38797. That is the measurement,
    # not a copy-paste -- the 15-day patch did not move this function. The
    # derivation is still doing real work here: the anchor is found by byte
    # shape and the -0x22 delta verified against an int3 boundary, so an
    # unchanged answer is a re-derivation that agreed, not a lookup.
    "2026-08-13_64fae3b1369b": 0x007DE010,
}


def load(stamp):
    d = vaultpath.require_dir("client", stamp, why="msgshape table derivation")
    return os.path.join(d, "Gw.exe")


try:
    EXES = {b.stamp: load(b.stamp) for b in pinned.BUILDS}
except BaseException as exc:                                 # noqa: BLE001
    # `require_dir` raises SystemExit -- a BaseException, which sails straight
    # past `except Exception`. That exact hole once let a vault-less run die
    # before printing a verdict anybody had seen.
    EXES = {}
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")

PES = {stamp: PE(p) for stamp, p in EXES.items()}


print("\n0. the anchor is unique, and the obvious anchor is not")

for stamp, pe in PES.items():
    hits = pe.find(MS.REGISTER_SIG, ".text")
    check(len(hits) == 1,
          f"{stamp}: the RegisterMsgs anchor is unique in .text",
          f"{len(hits)} hit(s)")

    # THE negative control. If this were the anchor, "take the first hit" would
    # silently resolve some other function -- and the count is not close to 1.
    generic = pe.find(GENERIC_PROLOGUE, ".text")
    check(len(generic) > 10,
          f"{stamp}: the routine's own prologue is NOT unique",
          f"{len(generic)} hits -- which is why the -0x22 delta must be "
          f"VERIFIED after a match, never searched for")

for stamp, pe in PES.items():
    va, off = MS.find_register_msgs(pe)
    check(va == EXPECT_ENTRY[stamp],
          f"{stamp}: RegisterMsgs resolves to 0x{EXPECT_ENTRY[stamp]:08X}",
          f"got 0x{va:08X}")
    check(pe.data[off - 1] == 0xCC,
          f"{stamp}: and the entry is preceded by an int3 pad",
          "so the delta landed on a function boundary, not mid-instruction")

# Refusals. Driven by swapping the pattern, which is the only input that
# decides how many hits there are.
if PES:
    pe = next(iter(PES.values()))
    real = MS.REGISTER_SIG
    try:
        MS.REGISTER_SIG = bytes.fromhex("d0d0d0d0d0d0d0d0d0d0d0d0")
        try:
            MS.find_register_msgs(pe)
            check(False, "an anchor with ZERO hits is refused", "it returned")
        except MS.NoTables:
            check(True, "an anchor with ZERO hits is refused")
        except Exception as exc:                             # noqa: BLE001
            check(False, "an anchor with ZERO hits is refused",
                  f"raised {type(exc).__name__}, not NoTables")

        MS.REGISTER_SIG = GENERIC_PROLOGUE                   # 56/57 hits
        try:
            MS.find_register_msgs(pe)
            check(False, "an anchor with MANY hits is refused",
                  "it took one of them")
        except MS.NoTables:
            check(True, "an anchor with MANY hits is refused",
                  "refusing to guess beats resolving the wrong routine")
        except Exception as exc:                             # noqa: BLE001
            check(False, "an anchor with MANY hits is refused",
                  f"raised {type(exc).__name__}, not NoTables")
    finally:
        MS.REGISTER_SIG = real

    # POSITIVE CONTROL for the two refusals above: with the real pattern
    # restored, the same call on the same image succeeds. Without this, both
    # refusals are satisfied by a function that raises unconditionally.
    va, _ = MS.find_register_msgs(pe)
    check(va in EXPECT_ENTRY.values(),
          "and the real anchor still resolves after the swaps",
          f"0x{va:08X}")


print("\n1. the derivation reproduces the pinned constant  (the WEAK half)")

pinned_stamp = pinned.PINNED.stamp
if pinned_stamp in PES:
    derived = MS.derive_tables(PES[pinned_stamp])
    triples = sorted((r.va, r.count, r.direction) for r in derived)
    check(triples == sorted(MS.TABLES_38797),
          f"build {pinned.BUILD}: derived tables == TABLES_38797, exactly",
          f"{len(triples)} derived vs {len(MS.TABLES_38797)} pinned")
    check(len(derived) == 25, "which is 25 tables", str(len(derived)))
    check(sum(r.count for r in derived) == 751,
          "and 751 declared entries", str(sum(r.count for r in derived)))
    callers = {r.caller for r in derived}
    check(len(callers) == 14,
          "recovered from 14 call sites",
          "studies/msgtable/FINDINGS.md §3 found the same 14")


print("\n2. the SAME code on a build the constant knows nothing about")

old_stamp = pinned.BUILDS[0].stamp
if old_stamp in PES and pinned_stamp in PES:
    old = MS.derive_tables(PES[old_stamp])
    new = MS.derive_tables(PES[pinned_stamp])
    check(len(old) == 25, "the older build yields 25 tables too", str(len(old)))
    check(sum(r.count for r in old) == 751,
          "and the same 751 declared entries", str(sum(r.count for r in old)))
    check(len({r.caller for r in old}) == 14, "from 14 call sites")

    # The claim that makes this a derivation rather than a lookup: not one
    # address survived, and every count did.
    shared = {r.va for r in old} & {r.va for r in new}
    check(not shared,
          "and NOT ONE table address is shared with build 38797",
          f"{len(shared)} shared -- addresses moved, which is the whole point")
    check(sorted(r.count for r in old) == sorted(r.count for r in new),
          "while every entry COUNT is identical across the two builds",
          "the tables moved; the protocol did not")

    # And it decodes. This is what the older build could not do before.
    img = MS.Image(EXES[old_stamp])
    c = img.census()
    check(c["slots"] > 2000, "the older build now yields real cmd slots",
          f"{c['slots']} (was 0)")
    check(img.skipped_unmapped == 0,
          "with ZERO entries lost to the unmapped-cmds_va skip",
          "651 of 751 died there before")
    msgs, descs = img.invariant_coverage()
    check(msgs == 666 and descs > 1700,
          "666 messages, and the invariant check examined real descriptors",
          f"{msgs} messages, {descs} descriptors")
    check(not img.invariants(),
          "zero invariant violations -- and now that means something",
          f"over {descs} descriptors")
    oracles = img.oracle_check()
    check(all(ok for _, ok, _ in oracles),
          "and all four AgMsg oracles PASS on the older build",
          "against ITS AgMsg table, not 38797's")
    check(img.agmsg_table != 0x00A52D70,
          "resolved through its own AgMsg table",
          f"0x{img.agmsg_table:08X} -- the hardcoded 0x00A52D70 is 38797's")

if pinned_stamp in PES:
    img = MS.Image(EXES[pinned_stamp])
    check(img.census() == MS.CENSUS_38797,
          "and build 38797 still reproduces CENSUS_38797 bit for bit",
          str(img.census()))


print("\n3. a run that measures nothing FAILS")

if pinned_stamp in PES:
    # A table set that resolves nothing: the shape the older build used to have.
    junk = (MS.Registration(0xDEAD0000, 8, "RECV", 0, 0),)
    doctored = MS.Image(EXES[pinned_stamp], tables=junk)
    check(not doctored.slots, "a doctored table set yields no cmd slots")
    check(doctored.invariants() == [],
          "and reports ZERO invariant violations",
          "which is the vacuous line, printed exactly as a healthy run prints it")
    check(doctored.invariant_coverage() == (0, 0),
          "because it examined 0 descriptors in 0 messages",
          "the pair is what tells the two runs apart -- the count alone cannot")
    check(MS.measured_nothing(doctored) is True,
          "so measured_nothing() calls it out")

    # POSITIVE CONTROL. Without this the predicate could answer True to
    # everything and still pass the check above.
    for stamp, exe in EXES.items():
        check(MS.measured_nothing(MS.Image(exe)) is False,
              f"while a real run on {stamp} is not called vacuous")

    # End to end, through the CLI, because the exit code is the part that was
    # wrong and it lives in main().
    for stamp, exe in EXES.items():
        r = subprocess.run([sys.executable, os.path.join(HERE, "msgshape.py"),
                            "--census", "--exe", exe],
                           capture_output=True, text=True, timeout=600)
        check(r.returncode == 0,
              f"`--census --exe {stamp}` exits 0",
              f"rc={r.returncode}")
        check("descriptor invariant violations: 0  (over" in r.stdout,
              "and its invariant line states its own coverage",
              "a bare `violations: 0` is the line that lied")

sys.exit(LEDGER.verdict())
