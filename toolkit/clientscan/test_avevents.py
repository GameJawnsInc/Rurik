"""The two AgentView event allocators, located by ArenaNet's asserts.

    python toolkit/clientscan/test_avevents.py

WHY. `avevents.py` held the last two unconverted addresses in
`studies/crossbuild/FINDINGS.md` §2's census -- the ACTION and EFFECT allocator
entry points, stored as literals and checked by nothing. Call targets were
matched against them, so on any other build every call site failed to match and
the tool reported that nothing allocates anything: a confident empty answer, not
an error.

WHAT REPLACED THEM is the module's own docstring argument, executed. Neither
allocator contains an assert, but each sits immediately beside a function that
does, and those functions are named by ArenaNet's file and line -- which survive
a rebuild where an address does not:

    ACTION  is the function immediately BEFORE the one asserting
            AvChar.cpp:1243 and :1251.
    EFFECT  is the function immediately AFTER the one asserting
            AvChar.cpp:2433 and :2438.

THE CHECK THAT EARNS THIS FILE is §2. Anchoring on AvChar:1243 ALONE resolves to
THREE distinct functions on both vaulted builds -- so a version that took the
first hit would be right on 38797 by luck and wrong elsewhere, which is exactly
the "take the first match" defect `studies/crossbuild/PLAN.md` §7 rule 1
forbids. The first draft of this derivation did precisely that and passed. It is
the PAIR of lines that resolves to one function, and §2 measures both numbers
rather than asserting the rule.

§3 is the half a lookup cannot fake: the older build must derive a DIFFERENT
pair of addresses and still reproduce the census -- 23 call sites, 23 resolved,
22 kinds -- which is the same answer about a different image.

The function-boundary walk is reimplemented here out of `int3` padding rather
than imported, so the test is a second witness to the module's own walk rather
than a second call to it.

Needs the vault; every claim is about ArenaNet's bytes. Floor 19, ~50 s (it
builds the assert corpus for both builds).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import asserts as AZ                                         # noqa: E402
import avevents as AV                                        # noqa: E402
import checks                                                # noqa: E402
import pinned                                                # noqa: E402
import vaultpath                                             # noqa: E402

LEDGER = checks.Ledger("AgentView event allocators", floor=19)
check = checks.adopt(LEDGER)

# MEASURED 2026-08-12. Class-(c) expectations: a new build SHOULD move these,
# and this file going red is how that gets noticed.
EXPECT = {
    "2026-07-29_221c13772c7a": {0x007F2E90: "action", 0x007F5340: "effect"},
    "2026-04-30_b174de1f2d8d": {0x007ECB90: "action", 0x007EF040: "effect"},
}
EXPECT_ACTION_SITES = 23
EXPECT_ACTION_KINDS = 22


def fn_entry(pe, off):
    """The function containing `off`, by MSVC's int3 padding. Written here so
    this test does not ask the module under test where its functions start."""
    d = pe.data
    while off > 0 and d[off - 1] != 0xCC:
        off -= 1
    return off


def raises(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except ValueError:
        return True
    except Exception:
        return False
    return False


try:
    EXES = {b.stamp: os.path.join(vaultpath.require_dir(
        "client", b.stamp, why="AgentView allocators"), "Gw.exe")
        for b in pinned.BUILDS}
except BaseException as exc:                                 # noqa: BLE001
    EXES = {}
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")

IMGS = {stamp: AV.Image(p) for stamp, p in EXES.items()}


print("\n1. the allocators derive to the recorded addresses on both builds")

for stamp, img in IMGS.items():
    got = img.allocators
    check(got == EXPECT[stamp],
          f"{stamp}: derives {', '.join(f'0x{v:08X} {n}' for v, n in sorted(EXPECT[stamp].items()))}",
          f"got {{{', '.join(f'0x{v:08X} {n}' for v, n in sorted(got.items()))}}}")
    check(len(set(got)) == 2, f"{stamp}: two distinct addresses", str(len(set(got))))

if len(IMGS) >= 2:
    a, b = [set(i.allocators) for i in IMGS.values()]
    check(not (a & b),
          "and NOT ONE allocator address is shared between the builds",
          "which is what makes this a derivation rather than a lookup")


print("\n2. one anchor line is AMBIGUOUS -- the pair is what resolves it")

for stamp, img in IMGS.items():
    pe = img.pe
    az = AZ.Asserts(EXES[stamp])
    byfn = {}
    for it in az.items:
        if it.file.endswith("AvChar.cpp") and it.line is not None:
            o = pe.rva_to_off(it.va - az.base)
            if o is not None:
                byfn.setdefault(fn_entry(pe, o), set()).add(it.line)

    solo = [e for e, lines in byfn.items() if 1243 in lines]
    check(len(solo) == 3,
          f"{stamp}: AvChar:1243 alone sits in 3 distinct functions",
          f"{len(solo)} -- so 'take the first hit' is right here by luck only")

    for lines, name in (({1243, 1251}, "action"), ({2433, 2438}, "effect")):
        both = [e for e, got in byfn.items() if lines <= got]
        check(len(both) == 1,
              f"{stamp}: but {sorted(lines)} together sit in exactly ONE",
              f"{len(both)} for {name}")


print("\n3. the census reproduces on the build the constants never knew")

for stamp, img in IMGS.items():
    kinds, unresolved = AV.census(img)
    action = kinds.get("action", {})
    n = sum(len(v) for v in action.values())
    bad = sum(1 for w, _ in unresolved if w == "action")
    check(n + bad == EXPECT_ACTION_SITES,
          f"{stamp}: the action allocator has {EXPECT_ACTION_SITES} call sites",
          str(n + bad))
    check(len(action) == EXPECT_ACTION_KINDS,
          f"{stamp}: resolving to {EXPECT_ACTION_KINDS} distinct kinds",
          str(len(action)))


print("\n4. an anchor that does not resolve is REFUSED")

if IMGS:
    img = IMGS[pinned.PINNED.stamp]
    real = AV.ANCHORS
    try:
        # A line ArenaNet never asserts: zero functions match, so there is no
        # allocator to name and the module must say so rather than pick one.
        AV.ANCHORS = (dict(name="action", file="AvChar.cpp",
                           lines=(999999, 999998), side="before"),)
        img._allocs = None
        check(raises(lambda: img.allocators),
              "an anchor matching NO function is refused")

        # And one that is ambiguous -- the single line §2 measured at three.
        AV.ANCHORS = (dict(name="action", file="AvChar.cpp",
                           lines=(1243,), side="before"),)
        img._allocs = None
        check(raises(lambda: img.allocators),
              "an anchor matching THREE functions is refused, not resolved",
              "this is the case the first draft of the derivation got wrong")
    finally:
        AV.ANCHORS = real
        img._allocs = None

    # POSITIVE CONTROL. Without it, both refusals are satisfied by a property
    # that raises unconditionally.
    check(img.allocators == EXPECT[pinned.PINNED.stamp],
          "while the real anchors still resolve after the swaps")

    check(AV.ACTION_38797 == 0x007F2E90 and AV.EFFECT_38797 == 0x007F5340,
          "the pinned pair is retained as a cross-check",
          "printed by --census when it disagrees; never used to find anything")

sys.exit(LEDGER.verdict())
