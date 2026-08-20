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
  * §5: `of_image` -- the shared answer to "which build is THIS file" -- must
    never be able to reply with a constant. Added 2026-08-17 for a defect with
    four instances and one shape: a tool identified a file correctly and then
    labelled it 38797 anyway, because `identify()` returned the category
    ("pristine") and not the row, so the number had to come from somewhere and
    `pinned.BUILD` was the only thing to hand. `framebus.py` printed it over
    the 38833 client; `worldmap.py`, `consttable.py` and `heroes_table.py`
    stamped it onto extracted content rows, where condition 2 of the owner's
    ruling says the build is what makes a row re-derivable. The checks are
    written to fail against that code, not merely to pass against this one.

WHAT IT DOES NOT ESTABLISH. That the range 30000..99999 is right in general --
it is an assumption, stated in `buildid.py`'s docstring as its weakest link, and
§3 is the only thing testing it from outside. n=3 builds.

Needs the vault. Floor 39, ~8 s.
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

# floor re-measured 2026-08-14 from a real green run: 23 -> 29, the third
# vaulted build (38833) adding 6.
# re-measured 2026-08-17 from a real green run: 29 -> 39. §5 adds 12 with the
# whole vault present, and the floor is 39 rather than 41 because TWO of them
# need `vault/run/2026-08-13_64fae3b1369b/Gw.exe` -- our patched 38833 copy,
# which is optional in a way the pristine snapshots are not. That pair declares
# a skip; the floor stays at the mandatory core, per checks.py's own advice.
# 2026-08-19: that optional pair is now an optional TRIPLE riding on
# `vault/run/reskin-roster/Gw.exe` instead (see §5's fallback, which had to be
# repointed when the 38833 copy became a registered digest). A full vault scores
# 42; the mandatory core is unchanged, so the floor stays 39.
LEDGER = checks.Ledger("client build id", floor=39)
check = checks.adopt(LEDGER)

REPO = os.path.dirname(os.path.dirname(HERE))

# MEASURED 2026-08-13. Class-(c) expectations: a NEW build must move these.
EXPECT = {
    "2026-07-29_221c13772c7a": dict(number=38797, va=0x004729E0, shapes=54),
    "2026-04-30_b174de1f2d8d": dict(number=38519, va=0x004728A0, shapes=56),
    # 38833, MEASURED 2026-08-14. The getter VA is the SAME as 38797's and the
    # shape count is the same 54 -- only the immediate the getter returns moved.
    # Worth stating because this file's §1 argument is "the shape is common and
    # the VALUE is the filter": here that is the ONLY thing separating the two
    # images, and the read still lands on exactly one in-range candidate.
    "2026-08-13_64fae3b1369b": dict(number=38833, va=0x004729E0, shapes=54),
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
          f"all {len(EXES)} builds report DIFFERENT numbers", str(sorted(nums)))
    # Dates come from the vault stamp, so this compares the reader against the
    # calendar rather than against itself. Written as a sort so a fourth build
    # needs no edit here -- the two-build spelling had to be corrected when the
    # third arrived, which is the same maintenance this arc exists to remove.
    by_date = [EXPECT[s]["number"] for s in sorted(EXPECT) if s in EXES]
    check(by_date == sorted(by_date),
          "and build numbers ascend with the snapshot dates",
          f"{by_date} -- which is NOT the direction the dates say")


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


print("\n5. of_image answers about the FILE, and cannot answer with a constant")

# THE REGRESSION THIS SECTION EXISTS FOR, found 2026-08-17. Four tools took a
# build number from `pinned.BUILD` after merely CHECKING that the file was some
# recorded build: `framebus.py` printed "the pinned build 38797" over the 38833
# client, and `worldmap.py`, `consttable.py` and `heroes_table.py` stamped 38797
# onto rows extracted from it. Every check below is written to go red against
# that code -- an implementation that returns the pin fails the `!= pinned.BUILD`
# checks, and one that returns None for anything unrecognised fails the getter
# fallback. `pinned.identify_build`'s docstring has the whole history.

for b in pinned.BUILDS:
    if b.stamp not in EXES:
        continue
    kind, row, _detail = pinned.identify_build(EXES[b.stamp])
    check(kind == "pristine" and row is b,
          f"{b.stamp}: identify_build hands back the ROW it matched",
          f"{kind}, {row} -- returning only the string 'pristine' is what left "
          f"four callers with no way to name the build they had just identified")

    number, why = BI.of_image(EXES[b.stamp])
    check(number == b.number,
          f"{b.stamp}: of_image reads {b.number} from the file itself",
          f"{number} -- {why}")
    if b.number != pinned.BUILD:
        check(number != pinned.BUILD,
              f"{b.stamp}: and does NOT answer {pinned.BUILD} for it",
              f"{number} -- this is the check the old code fails: it identified "
              f"this file correctly and then reported the constant")

# THE FALLBACK, and it is the case the registry cannot serve: a real client of a
# build we hold, sitting at a path that is in NO registry row, so `identify()`
# answers "unknown" and only the client's own getter can say anything at all.
# `vault/run/reskin-roster/Gw.exe` is that file -- a reskin experiment copy of
# the pin, 682 differing bytes in 211 runs from the pristine image, which is why
# `register_patched`'s sanity bound refuses it and why nothing has ever filed it.
#
# IT NAMED `vault/run/2026-08-13_64fae3b1369b/Gw.exe` UNTIL 2026-08-19, our
# patched 38833 copy, on the strength of "`patched` is None for that build". That
# was true when this section was written on 2026-08-17 and stopped being true two
# days later, when `pinned.BUILDS` gained a patched digest set and that file's
# `e06ada3b...` was committed into it: `identify_build` now answers
# ('patched', 38833) and the section went red against a fixture that had merely
# become registered. The CASE is unchanged; only the file that still fits it
# moved, so this is a repoint rather than a recolour.
#
# WHAT THIS FILE CANNOT PIN, said out loud: reskin-roster IS build 38797, so the
# NUMBER cannot separate "read from the image" from "answered with the constant"
# here -- 38797 is both. The third check is the one that does the separating: the
# `why` must name the image's own getter and must NOT claim a registry row, which
# is exactly what an implementation returning `pinned.BUILD` could not say.
_unregistered = os.path.join(vaultpath.vault_root(), "run",
                             "reskin-roster", "Gw.exe")
if os.path.isfile(_unregistered):
    kind, row, detail = pinned.identify_build(_unregistered)
    number, why = BI.of_image(_unregistered)
    check(kind == "unknown" and row is None,
          "a real client that is in no registry row identifies as unknown",
          f"{kind}/{row} -- {detail}")
    check(number == 38797,
          "and of_image still answers, because the image carries its own number",
          f"{number} -- {why}")
    check("build getter" in why and "sha256 matches the registry" not in why,
          "-- from that getter, and it says so rather than citing a row it has not got",
          f"{why} -- this is the check a tool answering with pinned.BUILD fails")
else:
    LEDGER.skip("the unregistered-image fallback",
                f"{_unregistered} is not here")

# Two ways to have no answer. Both must be None rather than the pin: `worldmap`
# emits `build: None` on such a row on purpose, so a reader can act on it.
check(BI.of_image(os.path.join(HERE, "no_such_client.exe")) == (None,
      f"no such file: {os.path.join(HERE, 'no_such_client.exe')}"),
      "a missing file is (None, why), not the pin")
check(BI.of_image(os.path.join(HERE, "buildid.py"))[0] is None,
      "and so is a file that is not a PE at all",
      "None is a usable answer; 38797 is not")

sys.exit(LEDGER.verdict())
