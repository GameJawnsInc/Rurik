"""The generic-value switches: derived from the image, on every vaulted build.

    python toolkit/clientscan/test_genericvalue.py

WHY. `genericvalue.py` recovers which of the client's property-id switches acts
on each id, and its docstring claimed "a build that moves them fails loudly
instead of returning a stale map that still looks plausible". That was true of
the compare chains and false of everything else: the five table switches stored
addresses and checked none of them. Two rounds of work followed, and the second
is what this file now tests.

ROUND ONE (2026-08-12) made the failure LOUD. The jump-table addresses stopped
being stored and came out of the `movzx`/`jmp` pair instead, and the remaining
sites were gated so a build that moved them refused. 32 hardcoded addresses
became 27, and every one of the 27 was fail-closed.

ROUND TWO (2026-08-14) made it unnecessary, because build 38833 arrived and
proved that loud was not enough: this module REFUSED the new build outright and
took `avevents.py`'s property map down with it. Being right about not knowing
beats being confidently wrong, but it is still not being able to read the
client. The 27 are now ZERO -- nothing in `genericvalue.py` is looked up by
address. `studies/crossbuild/FINDINGS.md` §7.1 and §8.

  * §1 IS THE LOAD-BEARING SECTION. The derivation must reproduce, on build
    38797, every address that used to be typed into the module -- dispatchers,
    switch sites, defaults, chain case bodies and both gates. Those literals
    live HERE now, and the taxonomy is the reason: under
    `studies/crossbuild/PLAN.md` §6 a hand-measured address is class (a), the
    per-build liability, for exactly as long as the TOOL computes with it, and
    class (c), a wanted expectation, once its only reader is a test. Leaving
    them in the module would have kept `buildpins` counting 25 live constants in
    a file that no longer looks anything up.
  * §3 IS THE CLAIM ROUND ONE COULD NOT MAKE, and it is this file's inversion.
    It used to assert that the older build REFUSES; refusing was the best the
    pinned module could do. Now every vaulted build must be READ, and all of
    them must agree on the semantics -- 47 int ids, 14 float, exactly {40}
    untouched, main switches disjoint -- while every address differs. Agreement
    on the answer with disagreement on the addresses is what a derivation looks
    like and what a lookup cannot fake.
  * §4 is the negative control, in two kinds. A doctored SITE must be refused by
    the framing check; and each "exactly N" guard inside `locate()` must
    actually fire, because a search that silently takes the first plausible hit
    is the defect this whole arc exists to remove.

Needs the vault for every section: every claim is about ArenaNet's bytes, and a
run that has seen none of them cannot refute anything. Floor 39, ~20 s.
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

# Floor MEASURED from a real green run 2026-08-14: 39. It was 33
# before round two; the sections that grew are §3 (now every vaulted
# build rather than one) and §4 (four count guards that did not exist).
# Written down from the run, not from counting `check(` calls -- the
# first draft of this file declared 62 from a guess and reported "ONLY
# 39 OF A DECLARED FLOOR OF 62", which is the vacuity guard catching
# its author rather than a lost section.
LEDGER = checks.Ledger("generic-value switches", floor=39)
check = checks.adopt(LEDGER)

# EVERY ADDRESS `genericvalue.py` USED TO CARRY, measured by hand on build
# 38797. This is the witness the derivation is scored against, and moving it out
# of the module is what took that file's class-(a) count from 27 to 0.
EXPECT_ADDRS = {
    "int-main": dict(dispatch=0x008128F0, at=0x008129CC, default=0x00812EC7),
    "float-main": dict(dispatch=0x00813040, at=0x008130DB, default=0x00813249),
    "int-pre": dict(dispatch=0x008128F0, at=0x0081298B, default=0x008129B0),
    "int-agentview": dict(dispatch=0x0081BC60, at=0x0081BC78, default=0x0081BD29),
    "float-store": dict(dispatch=0x00818210, at=0x0081822E, default=0x0081838B),
    "int-store": dict(dispatch=0x00818170, at=0x00818182,
                      ids={32: 0x008181E5, 41: 0x008181B0, 42: 0x00818191}),
    "float-agentview": dict(dispatch=0x0081BD80, at=0x0081BD86,
                            ids={5: 0x0081BD95, 51: 0x0081BD95, 61: 0x0081BD95}),
    "gates": (0x008129B6, 0x008130C2),
}

# The id range each switch covers, read out of its `cmp`/`ja` guard.
EXPECT_SPANS = {"int-main": (0, 66), "float-main": (0x10, 0x3F),
                "int-pre": (4, 64), "int-agentview": (4, 60),
                "float-store": (0x10, 0x3E)}

# The two tables each switch site names, MEASURED on 38797. These were the
# module's `jt=`/`bt=` literals before round one removed them.
EXPECT_TABLES = {
    "int-main":       (0x00812F20, 0x00812FE0),
    "float-main":     (0x00813250, 0x0081328C),
    "int-pre":        (0x00812ED0, 0x00812EE0),
    "int-agentview":  (0x0081BD30, 0x0081BD44),
    "float-store":    (0x00818394, 0x008183B8),
}

# MEASURED 2026-08-12 from a green run of the tool, and REPRODUCED on all three
# vaulted builds 2026-08-14 -- which is §3.
EXPECT_INT_HANDLED = 47
EXPECT_FLOAT_HANDLED = 14
EXPECT_NOTHING_AT_ALL = [40]
EXPECT_TABLE_NAMES = ["int-agentview", "int-pre", "int-main",
                      "float-store", "float-main"]
EXPECT_CHAIN_NAMES = ["int-store", "float-agentview"]


def raises(fn, *a, **kw):
    """True if the call raised ValueError -- the module's refusal."""
    try:
        fn(*a, **kw)
    except ValueError:
        return True
    except Exception:                                        # noqa: BLE001
        return False
    return False


try:
    EXES = {b.stamp: os.path.join(vaultpath.require_dir(
        "client", b.stamp, why="generic-value switches"), "Gw.exe")
        for b in pinned.BUILDS}
    NEW = EXES[pinned.PINNED.stamp]
except BaseException as exc:                                 # noqa: BLE001
    # require_dir raises SystemExit, a BaseException, which `except Exception`
    # would sail straight past.
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")
    EXES, NEW = {}, None


if NEW:
    img = G.Image(NEW)

    print("\n1. the derivation reproduces every address 38797 measured by hand")

    bad = G.cross_check(img, EXPECT_ADDRS, EXPECT_SPANS)
    check(not bad,
          f"all {len(EXPECT_ADDRS)} recorded sites derive to their measured "
          f"addresses",
          "; ".join(f"{w}: got {g} want {e}" for w, g, e in bad))

    # Named individually too, because "all of them agree" hides WHICH one moved,
    # and saying that in one line is the whole point of keeping the witness.
    for name in EXPECT_TABLE_NAMES:
        want, got = EXPECT_ADDRS[name], img.switches[name]
        check(got["at"] == want["at"] and got["default"] == want["default"],
              f"{name}: site 0x{want['at']:08X}, default 0x{want['default']:08X}",
              f"got 0x{got['at']:08X} / 0x{got['default']:08X}")

    check(list(img.switches) == EXPECT_TABLE_NAMES,
          "the five table switches are found, in the order each runs",
          str(list(img.switches)))
    check(sorted(img.chains) == sorted(EXPECT_CHAIN_NAMES),
          "and both compare chains", str(sorted(img.chains)))

    for name, spec in img.switches.items():
        jt, bt = G.switch_tables(img, spec)
        want = EXPECT_TABLES[name]
        check((jt, bt) == want,
              f"{name}: the site names tables 0x{want[0]:08X} / 0x{want[1]:08X}",
              f"got 0x{jt:08X} / 0x{bt:08X}")

    # THE CLAIM THAT MAKES THIS A DERIVATION: the module computes with NO
    # build-coupled address at all. Asked of `buildpins`, the repo's own census,
    # rather than by grepping the source -- and the first draft of this check DID
    # grep, forbidding every one of these literals anywhere in the file. It went
    # red on the module's own docstring, which names the seven switches and their
    # 38797 addresses. That is class (b), a CITATION, and `studies/crossbuild/
    # PLAN.md` §6 is explicit that those are wanted and that scrubbing them is the
    # error: "Add build ids; do not remove addresses." A session already rewrote
    # 46 citations at maximum strictness and reverted all 46. The distinction the
    # check has to make is live-constant versus prose, which is exactly what
    # `buildpins` classifies on the syntax tree.
    sys.path.insert(0, os.path.dirname(HERE))
    import buildpins as BP                                   # noqa: PLC0415
    rows, _problems, _skipped = BP.scan(os.path.dirname(HERE))
    mine = [r for r in rows if r["klass"] == BP.LIVE
            and r["file"].endswith("genericvalue.py")]
    check(not mine,
          "genericvalue.py computes with ZERO build-coupled addresses (was 27)",
          f"{len(mine)} live constant(s) remain: "
          f"{[(r.get('symbol'), hex(r['value'])) for r in mine]}")
    cited = [r for r in rows if r["klass"] == BP.CITATION
             and r["file"].endswith("genericvalue.py")]
    check(cited,
          f"while its {len(cited)} prose citations are KEPT -- provenance, not "
          f"liability",
          "a module that names no address cannot be audited against the client")

    print("\n2. the map it reads is the one the study was written from")

    ints = G.handled(img, img.switches["int-main"])
    floats = G.handled(img, img.switches["float-main"])
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
          "both main-switch gates read as the gate")

    for name, spec in img.chains.items():
        ids = G.chain_ids(img, spec)
        check(ids == EXPECT_ADDRS[name]["ids"],
              f"{name}: the compare chain still encodes its ids and bodies",
              str({k: hex(v) for k, v in sorted(ids.items())}))


print("\n3. EVERY vaulted build is READ, and they all agree on the answer")

# This section is the inversion. It used to require the older build to REFUSE.
seen = {}
for stamp, path in sorted(EXES.items()):
    build = pinned.name_of(next(b for b in pinned.BUILDS if b.stamp == stamp))
    other = G.Image(path)
    ints = G.handled(other, other.switches["int-main"])
    floats = G.handled(other, other.switches["float-main"])
    check(len(ints) == EXPECT_INT_HANDLED and len(floats) == EXPECT_FLOAT_HANDLED,
          f"build {build}: {EXPECT_INT_HANDLED} int / {EXPECT_FLOAT_HANDLED} "
          f"float ids handled",
          f"got {len(ints)} / {len(floats)}")
    check(not (ints & floats) and
          G.handled_by_nothing(other) == EXPECT_NOTHING_AT_ALL,
          f"build {build}: disjoint, and only {EXPECT_NOTHING_AT_ALL} untouched",
          f"shared {sorted(ints & floats)}, "
          f"untouched {G.handled_by_nothing(other)}")
    seen[build] = tuple(sorted(s["at"] for s in other.switches.values()))

if len(seen) >= 2:
    # The half a lookup cannot fake: same answers, DIFFERENT addresses.
    check(len(set(seen.values())) == len(seen),
          f"and all {len(seen)} builds put those switches at DIFFERENT addresses",
          f"{ {k: [hex(a) for a in v] for k, v in seen.items()} } -- identical "
          f"sites across builds would mean this was reading one image")

if EXES:
    # Through the CLI, because a refusal that reads as a crash gets debugged as
    # one. Exit 0 = the map was read; 2 = this build moved something.
    for stamp, path in sorted(EXES.items()):
        r = subprocess.run([sys.executable, os.path.join(HERE, "genericvalue.py"),
                            "--exe", path], capture_output=True, text=True,
                           timeout=300)
        check(r.returncode == 0, f"the CLI exits 0 on {stamp}", f"rc={r.returncode}")


if NEW:
    print("\n4. the guards still refuse -- counts and framing both")

    # (a) framing. A site pointed at bytes that are not the pair.
    real = img.switches["int-main"]
    check(raises(G.switch_tables, img, dict(real, at=real["at"] + 1)),
          "a site off by ONE byte is refused",
          "the opcode framing is checked, not merely the address's existence")
    jt, bt = G.switch_tables(img, dict(real, at=img.switches["float-main"]["at"]))
    check((jt, bt) == EXPECT_TABLES["float-main"],
          "and a site pointed at ANOTHER switch reads that switch's tables",
          "which is why the site must be LOCATED rather than assumed")

    # (b) the counts inside locate(). Each is broken on purpose, because a guard
    # nobody has watched refuse is the same class of thing as a green check that
    # asserts nothing. The module is restored in `finally` every time.
    def locate_fresh():
        fresh = G.Image(NEW)
        return G.locate(fresh)

    keep = G.CHAIN_VERIFY.copy()
    try:
        G.CHAIN_VERIFY["int-store"] = "deadbeefdeadbeef"
        check(raises(locate_fresh),
              "a compare chain whose bytes are not found is REFUSED",
              "the chain is what makes its parsed ids refutable")
    finally:
        G.CHAIN_VERIFY.clear()
        G.CHAIN_VERIFY.update(keep)

    keep_op = G.INT_OPCODE
    try:
        G.INT_OPCODE = 0xBEEF
        check(raises(locate_fresh),
              "an opcode the receive table does not carry is REFUSED",
              "the dispatchers are reached through the message table, so a "
              "missing handler means nothing below can be located")
    finally:
        G.INT_OPCODE = keep_op

    keep_sites = G._switch_sites
    try:
        G._switch_sites = lambda i, s, e: keep_sites(i, s, e) + [0xDEAD]
        check(raises(locate_fresh),
              "an EXTRA switch site in a dispatcher is REFUSED",
              "'exactly two' is asserted; taking the first two would be the "
              "defect this arc exists to remove")
    finally:
        G._switch_sites = keep_sites

    keep_calls = G._calls
    try:
        G._calls = lambda i, s, e: []
        check(raises(locate_fresh),
              "a forwarder with no call at all is REFUSED",
              "the handler's single callee IS the dispatcher")
    finally:
        G._calls = keep_calls

    # And the positive control: with nothing doctored it still resolves.
    check(locate_fresh()["dispatch"]["int"] == EXPECT_ADDRS["int-main"]["dispatch"],
          "while an untouched image still locates the int dispatcher",
          "a guard that refuses everything protects nothing")

sys.exit(LEDGER.verdict())
