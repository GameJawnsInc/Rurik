"""The generic-value switches, and that a moved build cannot be read as a map.

    python toolkit/clientscan/test_genericvalue.py

WHY. `genericvalue.py` recovers which of the client's property-id switches acts
on each id, and its docstring claimed "a build that moves them fails loudly
instead of returning a stale map that still looks plausible". That was true of
`CHAINS`, whose entries carry a `verify` byte string, and false of everything
else in the file: the five table switches stored a jump-table and index-table
address each and checked neither, and `read_switch` verified only that an index
landed inside the table it had just read -- internal consistency, which catches
a corrupt read and not a moved one. `MAIN_SWITCH_GATE` printed
"MOVED -- results are suspect" and carried on. 32 of the 68 addresses in
`studies/crossbuild/FINDINGS.md` §2's census were in this one file.

WHAT CHANGED, and what this file pins. The table addresses are no longer stored.
They are read out of the `movzx`/`jmp` pair that jumps through them, so the map
is derived from the instruction rather than remembered beside it, and the opcode
framing is what makes the site refutable. That removed 10 hardcoded addresses
(32 -> 27) and gates the rest.

  * §1 is the one that matters: the derivation must reproduce, on build 38797,
    the exact table addresses that used to be hardcoded. Those literals live
    HERE now, as class-(c) expectations under `studies/crossbuild/PLAN.md` §6 --
    going red on a new build is what they are for.
  * §3 is the half that cannot be faked by a lookup: on the older vaulted build
    every switch must REFUSE. Before this change the same call returned a
    confident map read from whatever sits at 38797's addresses.
  * §4 doctors a site to point at bytes that are not the pair and requires a
    refusal, with a positive control on the real site -- a checker that refuses
    everything would pass §3 on its own and protect nothing.

Needs the vault for every section: every claim is about ArenaNet's bytes, and a
run that has seen none of them cannot refute anything. Floor 33, ~4 s.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                                # noqa: E402
import genericvalue as G                                     # noqa: E402
import pinned                                                # noqa: E402
import vaultpath                                             # noqa: E402

LEDGER = checks.Ledger("generic-value switches", floor=33)
check = checks.adopt(LEDGER)

# MEASURED on build 38797, and these are exactly the literals `genericvalue.py`
# used to carry as `jt=` and `bt=`. Keeping them here rather than there is the
# point: the module DERIVES them, this file asserts the derivation lands on the
# recorded answer, and on a new build this goes red while the module refuses.
EXPECT_TABLES = {
    "int-main":       (0x00812F20, 0x00812FE0),
    "float-main":     (0x00813250, 0x0081328C),
    "int-pre":        (0x00812ED0, 0x00812EE0),
    "int-agentview":  (0x0081BD30, 0x0081BD44),
    "float-store":    (0x00818394, 0x008183B8),
}

# MEASURED 2026-08-12 from a green run of the tool itself.
EXPECT_INT_HANDLED = 47
EXPECT_FLOAT_HANDLED = 14
EXPECT_NO_MAIN_CASE = [5, 8, 40, 51]
EXPECT_NOTHING_AT_ALL = [40]


def raises(fn, *a, **kw):
    """True if the call raised ValueError -- the module's refusal."""
    try:
        fn(*a, **kw)
    except ValueError:
        return True
    except Exception:
        return False
    return False


try:
    NEW = os.path.join(vaultpath.require_dir(
        "client", pinned.PINNED.stamp, why="generic-value switches"), "Gw.exe")
    OLD = os.path.join(vaultpath.require_dir(
        "client", pinned.BUILDS[0].stamp, why="generic-value switches"), "Gw.exe")
except BaseException as exc:                                 # noqa: BLE001
    # require_dir raises SystemExit, a BaseException, which `except Exception`
    # would sail straight past.
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")
    NEW = OLD = None

if NEW:
    img = G.Image(NEW)

    print("\n1. the tables are DERIVED, and land on the recorded addresses")

    for spec in G.TABLE_SWITCHES:
        jt, bt = G.switch_tables(img, spec)
        want = EXPECT_TABLES[spec["name"]]
        check((jt, bt) == want,
              f"{spec['name']}: derived tables are "
              f"0x{want[0]:08X} / 0x{want[1]:08X}",
              f"got 0x{jt:08X} / 0x{bt:08X}")
    check(not any("jt" in s or "bt" in s for s in G.TABLE_SWITCHES),
          "and the module stores neither table address any more",
          "they come out of the instruction that jumps through them")

    print("\n2. the map it reads is the one the study was written from")

    ints = G.handled(img, G.INT_SWITCH)
    floats = G.handled(img, G.FLOAT_SWITCH)
    check(len(ints) == EXPECT_INT_HANDLED,
          f"the int main switch handles {EXPECT_INT_HANDLED} ids", str(len(ints)))
    check(len(floats) == EXPECT_FLOAT_HANDLED,
          f"the float main switch handles {EXPECT_FLOAT_HANDLED}", str(len(floats)))
    check(not (ints & floats), "and the two main switches are disjoint",
          f"shared: {sorted(ints & floats)}")
    check(G.handled_by_nothing(img) == EXPECT_NOTHING_AT_ALL,
          f"exactly {EXPECT_NOTHING_AT_ALL} is acted on by no switch at all",
          str(G.handled_by_nothing(img)))
    check(all(ok for _va, ok in G.gate_bytes(img)),
          "both main-switch gates are where they were recorded")

    for spec in G.CHAINS:
        ids = G.chain_ids(img, spec)
        check(ids == spec["ids"],
              f"{spec['name']}: the compare chain still encodes its ids",
              str(sorted(ids)))

if OLD:
    print("\n3. the older build REFUSES -- it does not return a stale map")

    old = G.Image(OLD)
    for spec in G.TABLE_SWITCHES:
        check(raises(G.switch_tables, old, spec),
              f"{spec['name']}: switch_tables refuses on the older build")
        check(raises(G.read_switch, old, spec),
              f"{spec['name']}: and so does read_switch")
    for spec in G.CHAINS:
        check(raises(G.chain_ids, old, spec),
              f"{spec['name']}: the compare chain refuses too")
    check(raises(G.gate_bytes, old),
          "and the main-switch gate refuses rather than warning",
          "it used to print `MOVED -- results are suspect` and carry on")

    # Through the CLI, because a refusal that reads as a crash gets debugged as
    # one. Exit 2 = this build moved something; 0 = the map was read.
    r = subprocess.run([sys.executable, os.path.join(HERE, "genericvalue.py"),
                        "--exe", OLD], capture_output=True, text=True, timeout=300)
    check(r.returncode == 2, "the CLI exits 2 on the older build", f"rc={r.returncode}")
    check("CANNOT READ THIS BUILD" in r.stderr,
          "and says so as a finding rather than a traceback")
    check("Traceback" not in r.stderr, "-- with no traceback at all")

if NEW:
    r = subprocess.run([sys.executable, os.path.join(HERE, "genericvalue.py"),
                        "--exe", NEW], capture_output=True, text=True, timeout=300)
    check(r.returncode == 0, "while build 38797 still exits 0", f"rc={r.returncode}")

if NEW:
    print("\n4. the framing check is what refuses, not the address")

    # A site pointed at bytes that are not the pair. If this passed, §3 would be
    # satisfied by anything that happens to differ between the two builds.
    doctored = dict(G.INT_SWITCH, at=G.INT_SWITCH["at"] + 1)
    check(raises(G.switch_tables, img, doctored),
          "a site off by ONE byte is refused",
          "the opcode framing is checked, not merely the address's existence")

    doctored = dict(G.INT_SWITCH, at=G.FLOAT_SWITCH["at"])
    jt, bt = G.switch_tables(img, doctored)
    check((jt, bt) == EXPECT_TABLES["float-main"],
          "and a site pointed at ANOTHER switch reads that switch's tables",
          "which is why the site is the thing pinned, and why it is verified")

    # POSITIVE CONTROL. The real site still resolves -- so section 4 is the
    # framing refusing, not a checker that refuses everything.
    jt, bt = G.switch_tables(img, G.INT_SWITCH)
    check((jt, bt) == EXPECT_TABLES["int-main"],
          "while the real site still resolves",
          f"0x{jt:08X} / 0x{bt:08X}")

sys.exit(LEDGER.verdict())
