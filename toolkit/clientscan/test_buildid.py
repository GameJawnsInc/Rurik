"""The client's build number, read out of the binary.

    python toolkit/clientscan/test_buildid.py

WHY. `studies/crossbuild/PLAN.md` §8 recorded this as NOT FOUND -- nothing in
the repo derived a build number from a `Gw.exe`. `pinned.BUILD` was typed in,
and the older vaulted build's number appeared NOWHERE in the tree, so half the
corpus could not satisfy `HANDOFF.md`:237's day-one rule that every capture
manifest records the build id.

WHAT THIS PINS, and §3 is the one that makes the rest worth trusting.

  * §1: the shape is common and the VALUE is the filter. 54 functions on 38797
    and 56 on the older build are `mov eax, imm32; ret`; exactly one on each
    carries a five-digit build number. Both counts are asserted, because "one
    candidate" means nothing without knowing how many were rejected.
  * §2: the refusals. An empty range and an over-wide range are both driven by
    moving `BUILD_MIN`/`BUILD_MAX`, so the zero-candidate and many-candidate
    paths are exercised on real images, each with a positive control that the
    real range still resolves afterwards.
  * §3: THE INDEPENDENT WITNESS. For build 38797 the client tells us the same
    number over the NETWORK -- `schema/messages.json` carries
    `validated_against_build`, `authsrv.py` records it from the client's own
    VERSION frame, and the live `User-Agent: Gw/38797.0 (Win32)` has it in the
    clear. A value derived from the bytes and a value observed on the wire share
    no lineage at all, so their agreeing is a real check on the range assumption
    rather than a restatement of it.
  * §4: `pinned.BUILDS` must MATCH a fresh read. The registry's numbers are
    supposed to be derived, and a hand-edit that drifts from the binary is
    exactly what this arc is about.

WHAT IT DOES NOT ESTABLISH. That the range 30000..99999 is right in general --
it is an assumption, stated in `buildid.py`'s docstring as its weakest link, and
§3 is the only thing testing it from outside. n=2 builds.

Needs the vault. Floor 23, ~6 s.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import buildid as BI                                         # noqa: E402
import checks                                                # noqa: E402
import pinned                                                # noqa: E402
import vaultpath                                             # noqa: E402
from gwpe import PE                                          # noqa: E402

LEDGER = checks.Ledger("client build id", floor=23)
check = checks.adopt(LEDGER)

REPO = os.path.dirname(os.path.dirname(HERE))

# MEASURED 2026-08-13. Class-(c) expectations: a NEW build must move these.
EXPECT = {
    "2026-07-29_221c13772c7a": dict(number=38797, va=0x004729E0, shapes=54),
    "2026-04-30_b174de1f2d8d": dict(number=38519, va=0x004728A0, shapes=56),
}
EXPECT_CALLERS = 16


def refused(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except BI.NoBuildId:
        return True
    except Exception:
        return False
    return False


try:
    EXES = {b.stamp: os.path.join(vaultpath.require_dir(
        "client", b.stamp, why="client build id"), "Gw.exe")
        for b in pinned.BUILDS}
except BaseException as exc:                                 # noqa: BLE001
    EXES = {}
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")


print("\n1. the shape is common; the value is what identifies it")

for stamp, exe in EXES.items():
    want = EXPECT[stamp]
    all_c = BI.candidates(PE(exe))
    check(len(all_c) == want["shapes"],
          f"{stamp}: {want['shapes']} functions are `mov eax,imm32; ret`",
          f"{len(all_c)} -- the shape alone identifies nothing")
    inrange = [c for c in all_c if BI.BUILD_MIN <= c[1] <= BI.BUILD_MAX]
    check(len(inrange) == 1,
          f"{stamp}: exactly ONE of them is in the build range",
          f"{len(inrange)}")

    number, va, callers = BI.read(exe)
    check(number == want["number"],
          f"{stamp}: reads build {want['number']}", str(number))
    check(va == want["va"], f"{stamp}: from the getter at 0x{want['va']:08X}",
          f"0x{va:08X}")
    check(callers == EXPECT_CALLERS,
          f"{stamp}: which has {EXPECT_CALLERS} callers",
          f"{callers} -- corroboration only; the build is consulted all over")

if len(EXES) >= 2:
    nums = {BI.read(p)[0] for p in EXES.values()}
    check(len(nums) == len(EXES),
          "the two builds report DIFFERENT numbers", str(sorted(nums)))
    check(EXPECT["2026-04-30_b174de1f2d8d"]["number"]
          < EXPECT["2026-07-29_221c13772c7a"]["number"],
          "and the older build's is the lower one",
          "38519 < 38797, which is the direction the dates say")


print("\n2. it refuses rather than choosing")

if EXES:
    exe = EXES[pinned.PINNED.stamp]
    lo, hi = BI.BUILD_MIN, BI.BUILD_MAX
    try:
        # A range nothing lands in: the zero-candidate path, on a real image.
        BI.BUILD_MIN, BI.BUILD_MAX = 10**9, 10**9 + 1
        check(refused(BI.read, exe), "a range no candidate falls in is REFUSED",
              "not answered with the nearest value")

        # A range everything lands in: the many-candidate path.
        BI.BUILD_MIN, BI.BUILD_MAX = 0, 2**32 - 1
        check(refused(BI.read, exe),
              "and a range that admits many is REFUSED too",
              "taking the first would be the defect this whole arc is about")
    finally:
        BI.BUILD_MIN, BI.BUILD_MAX = lo, hi

    # POSITIVE CONTROL: the real range still resolves after both swaps, so §2 is
    # the range refusing and not a function that raises unconditionally.
    check(BI.read(exe)[0] == EXPECT[pinned.PINNED.stamp]["number"],
          "while the real range still resolves")

    check(refused(BI.read, os.path.join(HERE, "buildid.py")),
          "and a file that is not a PE is refused")


print("\n3. the wire says the same number, and it shares no lineage")

if EXES:
    number, _va, _c = BI.read(EXES[pinned.PINNED.stamp])

    p = os.path.join(REPO, "schema", "messages.json")
    with open(p, encoding="utf-8") as fh:
        schema = json.load(fh)
    # NESTED under `provenance`, not top-level -- a naive `schema.get(...)`
    # returns None, which is how the first version of this check "failed". The
    # location is asserted so a reader is not sent looking in the wrong place.
    check("validated_against_build" not in schema,
          "the schema's build stamp is NOT a top-level key",
          "it lives under `provenance`; reading the top level answers None")
    stamped = schema["provenance"].get("validated_against_build")
    check(stamped == number,
          "schema/messages.json's validated_against_build matches the binary",
          f"schema {stamped}, binary {number}")

    # The client's own User-Agent, as `webgate.py` reads it off the wire. The
    # literal lives in test_webgate.py's fixture; this asserts the FORM so the
    # two cannot drift apart silently.
    ua = f"Gw/{number}.0 (Win32)"
    p = os.path.join(REPO, "toolkit", "portal", "test_webgate.py")
    with open(p, encoding="utf-8") as fh:
        src = fh.read()
    check(ua in src,
          f"and the recorded live User-Agent is `{ua}`",
          "observed on the network; the binary was never consulted for it")

    check(pinned.BUILD == number,
          "pinned.BUILD agrees with the binary it names", str(pinned.BUILD))


print("\n4. pinned.BUILDS is derived, not typed in")

for b in pinned.BUILDS:
    if b.stamp not in EXES:
        continue
    number, _va, _c = BI.read(EXES[b.stamp])
    check(b.number == number,
          f"{b.stamp}: the registry's {b.number} matches a fresh read",
          f"binary says {number}")

check(all(b.number for b in pinned.BUILDS) or not EXES,
      "and no registered build is left without one")

sys.exit(LEDGER.verdict())
