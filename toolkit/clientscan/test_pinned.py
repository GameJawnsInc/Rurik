"""Which client a tool reads, and that the guard on it can actually go red.

    python toolkit/clientscan/test_pinned.py

WHY THIS FILE EXISTS. `pinned.py` is the module twelve static-analysis tools ask
"which `Gw.exe`", and until 2026-08-12 it answered without checking. `find()`
tested `os.path.isfile` and returned; `identify()` -- the only function here that
hashes anything -- was reachable from `main()` and two unrelated tests and from
nothing on the path any tool takes. The last fallback was the auto-updating
install at `C:\\gw`, handed back with the string "may not be 38797" and no
refusal. Every caller downstream computes with addresses measured on one build,
so reading the wrong one does not raise, it returns a confident wrong number.
That is `studies/crossbuild/PLAN.md` §5, and this file is its negative control.

WHAT IT IS BUILT TO CATCH, and each of these was broken on purpose to check that
it reddens:

  * a file of the RIGHT SIZE and the wrong bytes. This is the founding defect of
    the module -- the vault holds two copies of 38797 at the same length, 144
    bytes apart -- so a size gate is exactly the check that cannot see it.
  * `find()` falling through to the live install. Section 3 gives it an empty
    vault and a live install that EXISTS, which is the configuration where the
    old code silently returned the wrong build.
  * `verify=False` being what makes section 3 pass. The same planted file is run
    both ways and must be refused once and returned once; without the positive
    half, "it refused" is satisfied by a `find()` that refuses everything, and a
    guard that refuses everything protects nothing because the tool never runs.
  * a build that is honestly a DIFFERENT build. `identify()` scoped to a build
    must call the older client `unknown`, even though that file is a perfectly
    good pristine client -- of the other build. "Genuine" is not the question.

WHAT IT DELIBERATELY DOES NOT DO. It never launches anything and never reads the
live install's contents; `LIVE_INSTALL` is monkeypatched to a temp path so both
branches are exercised on every machine rather than only on one with `C:\\gw`.

SECTIONS 5 AND 6 ARE THE PROBE GATE -- `studies/crossbuild/FINDINGS.md` §2.1.
`itemprobe.py` and `agentprobe.py` hold three raw RVAs and did not import this
module at all; they read a LIVE client at `module_base + RVA`, so on another
build they do not compute a wrong answer, they dereference whatever else is
mapped there and print it as an agent array. §5 pins that `assert_build()`
refuses -- including refusing the OTHER vaulted client, which is a real ArenaNet
build and still the wrong one, a case that caught a genuine defect in the gate
while it was being written. §6 is the ordering, asked on the SYNTAX TREE because
"gates before it reads" is invisible to a grep: a file with both names in the
wrong order greps identically. Its control is a reversed probe that must be
REJECTED, plus a correct one that must be accepted, or the check is decoration.

SECTIONS 7 AND 8 ARE THE DIGEST SET -- added 2026-08-19, and the defect they
cover is a gate that had gone INVERTED. "Our patched copy" was ONE hand-typed
sha256 of ONE whole file, and a whole-file hash of a patched binary goes stale
the moment the patcher changes. It did: the key-tap added three sites, so the
gate refused the freshly patched client at `vault/run/<stamp>/` -- the one we
launch and the one `movetap.py`:438 gates -- while ACCEPTING the two superseded
copies at `-c2/` and `-probe/`. Build 38833 had no patched hash at all. §7 runs
the whole registration cycle against a FAKE vault (the real one is never
written): the refusal fires on an unregistered right-sized file FIRST, the same
file is then registered and accepted, and the reason names which source vouched
for it. Its controls are the ways the new write path could have widened the gate
-- registering the pristine image, a wrong size, a file 200 runs from pristine --
each refused, each with a positive half, because a `register_patched` that
refuses everything puts the staleness back by another route. §8 asks the SYNTAX
TREE whether the patcher actually calls it, and calls it AFTER it writes: both
files had no such call at all until this round, and "registers after writing"
greps identically to "registers before writing".

SECTION 9 IS THE ADVERSARIAL PASS OVER SECTION 7's OWN CHANGE, added the same
day and after it. Appending a digest set stopped the gate refusing the client we
launch; it also made "register" a verb the gate honours, and four ways of saying
it about the wrong bytes were then MEASURED and are reproduced here as tests:
10,483,904 bytes of `os.urandom` accepted under `strict=True` because the
pristine image was absent and the sanity bound was skipped rather than refused;
ArenaNet's own pristine 38833 image filed as our patched 38797, since only the
SELECTED build's pristine was compared and the two builds are the same length; a
registration whose write FAILED honoured by the gate for the rest of the process,
because the row was appended to the cached list before the write was attempted;
and a hand-edited registry row whose `build` and `stamp` name two different
builds vouching under both. Each has a positive half in the same block -- the
deliberate `strict=False` path, a file that is nobody's pristine, the same call
with the write unblocked, a well-formed row -- because a `register_patched` that
refuses everything puts the staleness back by another route. Section 8 gained
the two call-site halves of the same pass: the build handed to `register_patched`
must not be one the patcher chose (it was `build=tag`, a regex over the source
exe's FILENAME), and the `import pinned` must sit inside the same try/except as
the call, since both patchers call the registration "NON-FATAL, deliberately" in
a comment and neither enforced it.

Without a vault, section 4 skips and the run scores 109 against a floor of 130,
so it goes RED -- MEASURED with `RURIK_VAULT` pointed at an empty directory, and
the floor MEASURED against a minimal legitimate one, neither derived by
subtraction (see the floor's own comment: the subtracted number was five too low
to fire). That is deliberate: the other sections prove the refusals fire, and
only section 4 puts them against ArenaNet's real bytes, which is what tells a
working verifier from one that refuses everything. ~6 s.
"""
import ast
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                                # noqa: E402
import pinned                                                # noqa: E402
import vaultpath                                             # noqa: E402

# THE FLOOR IS MEASURED ON A MINIMAL LEGITIMATE VAULT, and the reason to say that
# is that until 2026-08-19 it was not. 104 was arrived at by subtracting the
# optional checks from a FULL vault's total (114 minus eight), and the arithmetic
# was wrong twice over: the comment said "of the 112" for a 114-check run, and,
# far worse, an EMPTY vault scored 109 -- five ABOVE the floor -- so the docstring
# above promising a red run without a vault was describing something that did not
# happen. A floor derived by subtraction is a guess about a configuration nobody
# ran.
#
# MEASURED 2026-08-19, with `RURIK_VAULT` pointed at a vault holding only
# `client/<stamp>/Gw.exe` for all three builds -- a machine that snapshotted its
# install and never patched a client, which is the mandatory core: 130 checks, 1
# declared skip (the reskin experiment copy). The full vault here scores 143, and
# the 13 extra all ride on copies a legitimate vault need not hold: `run/<stamp>`,
# `-c2`, `-probe` and the patched 38833 copy at 2 checks each, the two
# `run-live/<stamp>/` copies at 1 each, and the patch-bound and reskin
# measurements at 3 between them. An empty vault scores 109 and now goes RED,
# which is the whole point of declaring one.
#
# 129 -> 130 the same evening: §4 gained the cross-build distance check, which
# needs only the pristine images and so lands in the mandatory core rather than
# in the 13.
LEDGER = checks.Ledger("pinned client selection", floor=130)
check = checks.adopt(LEDGER)


def refused(fn, *a, **kw):
    """True if the call raised SystemExit. Anything else is not a refusal."""
    try:
        fn(*a, **kw)
    except SystemExit:
        return True
    except Exception:
        return False
    return False


class FakeVault:
    """Stands in for `vaultpath`, so `find()` can be given a vault we control."""

    def __init__(self, root):
        self.root = root

    def vault_path(self, *parts):
        return os.path.join(self.root, *parts)

    def vault_root(self):
        return self.root

    def vault_why(self):
        return "a temp directory built by test_pinned.py"


print("\n0. the build registry describes itself honestly  (no vault)")

check(pinned.PINNED in pinned.BUILDS, "the pin is one of the registered builds")
check(len(pinned.BUILDS) >= 2,
      "the registry holds more than one build",
      f"{len(pinned.BUILDS)}: " + ", ".join(pinned.name_of(b) for b in pinned.BUILDS))

# The vault stamp IS the pristine file's own sha256 prefix. That is the
# convention `snapshot_client.py` writes, and asserting it here means a
# mistyped hash cannot sit in the registry looking plausible -- the two fields
# would stop agreeing.
for b in pinned.BUILDS:
    check(b.pristine.startswith(b.stamp.split("_", 1)[1]),
          f"build {pinned.name_of(b)}: the stamp is its pristine sha256 prefix",
          f"{b.stamp.split('_', 1)[1]} vs {b.pristine[:12]}")

check(pinned.BUILD == pinned.PINNED.number and pinned.SIZE == pinned.PINNED.size
      and pinned.STAMP == pinned.PINNED.stamp
      and pinned.PRISTINE_SHA256 == pinned.PINNED.pristine
      and pinned.PATCHED_SHA256S == tuple(p.sha256 for p in pinned.PINNED.patched),
      "the named constants are the pinned row and nothing else")
check(not hasattr(pinned, "PATCHED_SHA256"),
      "and the singular PATCHED_SHA256 is GONE rather than kept as an alias",
      "it named one hash, which is the assumption that inverted the gate")

# REWRITTEN 2026-08-14, and the old assertion is why. It read
#   "the two builds differ in SIZE, so size separates them"
# and it went RED the day build 38833 was registered, because 38833 is
# byte-for-byte the same LENGTH as 38797 -- 10,483,904 -- while being a
# different build. The red was correct and the CLAIM was what had to change:
# size never separated the two copies WITHIN a build (this module's founding
# defect), and as of the third build it does not separate builds either.
#
# So the invariant is inverted into the one that actually holds and that the
# module's behaviour depends on: SHA256 IS THE DISCRIMINATOR, ALWAYS. A size
# collision must be tolerated by `identify()`, which is asserted directly below
# rather than left as a property of the registry's current contents.
sizes = [b.size for b in pinned.BUILDS]
digests = [b.pristine for b in pinned.BUILDS]
check(len(set(digests)) == len(digests),
      "every build has a DISTINCT pristine sha256 -- the real discriminator",
      f"{[d[:12] for d in digests]} -- two builds sharing a hash is impossible")

collisions = len(sizes) - len(set(sizes))
if collisions:
    print(f"     note: {collisions} size collision(s) in the registry "
          f"({sizes}) -- MEASURED, not a defect: 38797 and 38833 ship at the "
          f"same length. Any build check written on size alone is now a bug.")

# The collision is only safe because identify() considers EVERY same-size
# candidate instead of assuming one. Proven, not asserted: ask it about each
# build's own pristine image and require it to name that build.
for b in pinned.BUILDS:
    try:
        path, _why = pinned.find(b.stamp)
    except SystemExit:
        LEDGER.skip(f"identify {b.stamp}", "not in the vault")
        continue
    what, detail = pinned.identify(path)
    check(what == "pristine" and pinned.name_of(b) in detail,
          f"identify() names build {pinned.name_of(b)} from a same-size field",
          f"got {what!r}: {detail}")

# THE PATCHED SIDE IS A SET, and section 7 is where its mechanism is proved.
# These are the registry-shape invariants: they exist because the field was a
# single string until 2026-08-19, and a string is what went stale and inverted
# the gate. A `patched="..."` typed back in would now fail here rather than three
# weeks later against a client nobody could read.
for b in pinned.BUILDS:
    check(isinstance(b.patched, tuple),
          f"build {pinned.name_of(b)}: `patched` is a TUPLE of accepted digests",
          f"{type(b.patched).__name__} -- one hash is the shape that went stale")
    check(all(isinstance(p, pinned.PatchedCopy) and len(p.sha256) == 64
              and p.how for p in b.patched),
          f"-- each row is a PatchedCopy with a full sha256 and a description",
          f"{len(b.patched)} row(s)")

all_patched = [p.sha256 for b in pinned.BUILDS for p in b.patched]
check(len(set(all_patched)) == len(all_patched),
      "no patched digest is claimed by two builds",
      f"{len(all_patched)} digest(s) across the registry")
pristines = {b.pristine for b in pinned.BUILDS}
check(not (set(all_patched) & pristines),
      "and no patched digest is also a PRISTINE digest",
      "a pristine hash mistyped into the patched set would relabel "
      "ArenaNet's own file as ours")
check(pinned.PATCHED_SHA256S == tuple(p.sha256 for p in pinned.PINNED.patched)
      and len(pinned.PATCHED_SHA256S) > 1,
      "the pin's named constant is PLURAL and is its committed set",
      f"{len(pinned.PATCHED_SHA256S)} digest(s)")

numbered = [b for b in pinned.BUILDS if b.number is not None]
check(len({b.number for b in numbered}) == len(numbered),
      "no two builds claim the same number")

# Every build in the registry now HAS a number, and none of them is typed in --
# `buildid.py` reads them out of the images and `test_buildid.py` asserts both
# against a fresh read. This check used to be `older.number is None`, which was a
# measurement while nothing could read one; `studies/crossbuild/FINDINGS.md` §3
# is what changed it.
older = pinned.BUILDS[0]
check(older.number == 38519,
      "the older build has a number now, and it is derived",
      "was None while nothing in the tree could read one out of a binary")
check(all(b.number for b in pinned.BUILDS),
      "every registered build carries one")
check(pinned.name_of(pinned.PINNED) == "38797",
      "and a build prints as its number")
check("number unknown" not in pinned.name_of(older),
      "with nothing left printing 'number unknown'", pinned.name_of(older))


print("\n1. select() resolves what was asked for, or refuses  (no vault)")

check(pinned.select() is pinned.PINNED, "no argument means the pin")
check(pinned.select(38797) is pinned.PINNED, "a build number resolves")
check(pinned.select(pinned.STAMP) is pinned.PINNED, "a vault stamp resolves")
check(pinned.select(older) is older, "a Build passes through")
check(pinned.select(older.stamp) is older,
      "the numberless build is reachable by stamp",
      "which is the only handle it has")

check(refused(pinned.select, 99999), "an unknown build NUMBER is refused")
check(refused(pinned.select, "2020-01-01_deadbeefcafe"),
      "an unknown vault STAMP is refused")
check(refused(pinned.select, "38797"),
      "and a number spelled as a string is refused rather than coerced",
      "silently accepting it would make the registry's keys ambiguous")

# THE ARGV BOUNDARY, and this was a live defect the first time `--register` was
# run: argparse can only hand back text, so `--build 38797` reached `select()` as
# the STRING the check above refuses, and the CLI answered "no such build in the
# vault: '38797'" while listing 38797 in the same sentence. The lookup keeps
# refusing; the coercion belongs where the text comes in.
check(pinned.build_arg("38797") == 38797 and pinned.select(pinned.build_arg("38797"))
      is pinned.PINNED,
      "build_arg() turns a typed-in number into the NUMBER",
      "so --build 38797 resolves without loosening select()")
check(pinned.build_arg(pinned.STAMP) == pinned.STAMP,
      "-- and leaves a stamp alone", pinned.STAMP)


print("\n2. identify() is not a size check  (no vault)")

tmp = tempfile.mkdtemp(prefix="rurik_pinned_")
try:
    missing = os.path.join(tmp, "nope", "Gw.exe")
    what, _ = pinned.identify(missing)
    check(what == "unknown", "a file that does not exist is unknown")

    wrong_size = os.path.join(tmp, "small.exe")
    with open(wrong_size, "wb") as fh:
        fh.write(b"\0" * 1024)
    what, detail = pinned.identify(wrong_size)
    check(what == "unknown", "a file of no known size is unknown", detail)

    # THE control. Right length, wrong bytes -- what a size gate cannot see.
    right_size = os.path.join(tmp, "impostor.exe")
    with open(right_size, "wb") as fh:
        fh.truncate(pinned.PINNED.size)
    check(os.path.getsize(right_size) == pinned.PINNED.size,
          "planted a file of build 38797's exact size",
          f"{pinned.PINNED.size:,} bytes")
    what, detail = pinned.identify(right_size)
    check(what == "unknown",
          "a file of the RIGHT SIZE and wrong bytes is still unknown",
          detail)
    check("sha256" in detail,
          "and the reason names the hash, not the size",
          "a size-only guard is the defect this module was written for")

    # Scoping. Asked about ONE build, a file of a DIFFERENT known size is not
    # that build -- however genuine it is in its own right.
    other_size = os.path.join(tmp, "otherbuild.exe")
    with open(other_size, "wb") as fh:
        fh.truncate(older.size)
    what, _ = pinned.identify(other_size, build=38797)
    check(what == "unknown", "scoped to 38797, another build's size is unknown")
finally:
    shutil.rmtree(tmp, ignore_errors=True)


print("\n3. find() fails CLOSED  (no vault -- a fake one, and a fake live install)")

tmp = tempfile.mkdtemp(prefix="rurik_pinned_")
real_vaultpath, real_live = pinned.vaultpath, pinned.LIVE_INSTALL
try:
    empty = os.path.join(tmp, "vault")
    os.makedirs(empty)
    pinned.vaultpath = FakeVault(empty)

    # (a) nothing anywhere: a plain refusal.
    pinned.LIVE_INSTALL = os.path.join(tmp, "no-such-install", "Gw.exe")
    check(refused(pinned.find), "an empty vault and no live install is refused")

    # (b) the configuration the old code got wrong: the vault lacks the build,
    #     and a live install EXISTS. The old find() returned it.
    fake_live = os.path.join(tmp, "live", "Gw.exe")
    os.makedirs(os.path.dirname(fake_live))
    with open(fake_live, "wb") as fh:
        fh.write(b"\0" * 4096)
    pinned.LIVE_INSTALL = fake_live
    check(refused(pinned.find),
          "an empty vault does NOT fall through to the live install",
          "it auto-updates, so substituting it is silent and build-specific")

    # (c) and the opt-in still works, or the refusal would just be a wall.
    try:
        path, why = pinned.find(allow_live=True)
        check(path == fake_live, "allow_live=True returns the live install", why)
        check("may not be" in why,
              "and says it may not be the build that was asked for")
    except SystemExit:
        check(False, "allow_live=True returns the live install", "it refused")

    # (d) a planted file under the RIGHT stamp with the wrong bytes. This is the
    #     one that separates "verifies" from "checks the path exists".
    planted = os.path.join(empty, "client", pinned.STAMP, "Gw.exe")
    os.makedirs(os.path.dirname(planted))
    with open(planted, "wb") as fh:
        fh.truncate(pinned.PINNED.size)
    check(refused(pinned.find),
          "a file filed under the right stamp with the wrong bytes is REFUSED",
          "right name, wrong file -- the exact shape of the two-copies defect")

    # (e) POSITIVE CONTROL. The same file, verification off, comes back. Without
    #     this, (d) is satisfied by a find() that refuses everything -- and a
    #     guard that refuses everything protects nothing.
    try:
        path, why = pinned.find(verify=False)
        check(path == planted, "the SAME file is returned with verify=False",
              "so (d) is the verification refusing, not something else")
        check("UNVERIFIED" in why, "and the reason says UNVERIFIED out loud", why)
    except SystemExit:
        check(False, "the SAME file is returned with verify=False", "it refused")

    check(refused(pinned.find, 99999),
          "and an unknown build is refused before any file is touched")
finally:
    pinned.vaultpath, pinned.LIVE_INSTALL = real_vaultpath, real_live
    shutil.rmtree(tmp, ignore_errors=True)


print("\n4. against the real vault  (needs vault/client)")

try:
    root = vaultpath.require_dir("client", why="pinned client selection")
except BaseException as exc:                                 # noqa: BLE001
    # `require_dir` raises SystemExit, which is a BaseException and would sail
    # straight past `except Exception` -- the bug that made another test in this
    # tree print a verdict nobody had ever seen.
    LEDGER.skip("the real vault", f"vault/client unavailable: {exc}")
    root = None

if root:
    have = [b for b in pinned.BUILDS
            if os.path.isfile(os.path.join(root, b.stamp, "Gw.exe"))]
    check(len(have) == len(pinned.BUILDS),
          "every registered build is actually in the vault",
          ", ".join(pinned.name_of(b) for b in have))

    for b in have:
        p = os.path.join(root, b.stamp, "Gw.exe")
        what, detail = pinned.identify(p, build=b)
        check(what == "pristine",
              f"build {pinned.name_of(b)}: the vaulted client verifies as pristine",
              detail)

    if len(have) >= 2:
        # Honestly a real client, honestly the WRONG one. The point of scoping.
        p_old = os.path.join(root, older.stamp, "Gw.exe")
        what, detail = pinned.identify(p_old, build=38797)
        check(what == "unknown",
              "the older client, asked about as 38797, is unknown",
              "a genuine pristine client of the other build is still not this one")
        what, _ = pinned.identify(p_old)
        check(what == "pristine",
              "while unscoped it identifies as itself",
              "so the refusal above is the scoping, not a broken hash")

        path, why = pinned.find(build=older.stamp)
        check(os.path.normcase(path) == os.path.normcase(p_old),
              "find() can be pointed at the older build by stamp", why)
        check("verified pristine" in why, "and reports it verified", why)

    path, why = pinned.find()
    check(os.path.isfile(path), "the default resolves to a real file", path)
    check("verified" in why, "and says it verified the bytes it returned", why)

    # THE REGRESSION THIS ROUND FIXED, against the real files. The gate was
    # INVERTED: `Build.patched` held the pre-key-tap patcher's hash, so the
    # freshly patched client at vault/run/<stamp>/ -- the one we launch and the
    # one movetap.py:438 gates -- was REFUSED, while the superseded copies at
    # `-c2/` and `-probe/` passed. Both directions are asserted, because fixing
    # it by dropping the old digest would have inverted it the other way and the
    # `-c2` copy is a legitimate client too.
    for b in pinned.BUILDS:
        for sub in (b.stamp, b.stamp + "-c2", b.stamp + "-probe"):
            p = vaultpath.vault_path("run", sub, "Gw.exe")
            if not os.path.isfile(p):
                continue
            what, detail = pinned.identify(p, build=b)
            check(what == "patched",
                  f"run/{sub}/Gw.exe verifies as OUR patched copy of "
                  f"{pinned.name_of(b)}", detail)
            # THE NAMED SOURCE MUST BE THE LIST THE DIGEST IS REALLY IN, and
            # that is a different check from the one this was until 2026-08-19.
            # It read `"committed in pinned.BUILDS" in detail or "vault registry"
            # in detail`, which cannot fail underneath its own `what == "patched"`
            # guard: every patched detail ends `[{acc.source}]` and `acc.source`
            # always begins with one of exactly those two strings. So it asserted
            # the formatting of a string the same function had just built. What
            # is worth pinning is the ATTRIBUTION -- "the repository says so" and
            # "this machine's vault says so" are different amounts of evidence,
            # and a detail that swapped them would be lying about which.
            digest = pinned.sha256(p)
            is_committed = digest in [pc.sha256 for pc in b.patched]
            says_committed = "committed in pinned.BUILDS" in detail
            says_registry = "vault registry" in detail
            check(says_committed == is_committed
                  and says_registry == (not is_committed),
                  "-- and it names the list the digest is ACTUALLY in",
                  f"committed={is_committed}, detail says "
                  f"committed={says_committed}/registry={says_registry}")
        p = vaultpath.vault_path("run-live", b.stamp, "Gw.exe")
        if os.path.isfile(p):
            what, detail = pinned.identify(p, build=b)
            check(what == "patched",
                  f"run-live/{b.stamp}/Gw.exe verifies too -- same build, same "
                  f"offsets", detail)

    # And the structural evidence the refusal message quotes is real rather than
    # copied out of the comment. Ours are 6-9 runs; the reskin experiment copy of
    # the same build is 211, which is what tells an operator the two apart.
    p = vaultpath.vault_path("run", pinned.STAMP, "Gw.exe")
    if os.path.isfile(p):
        nbytes, nruns, dwhy = pinned.diff_against_pristine(p, pinned.PINNED)
        check(nbytes is not None and 1 <= nruns <= pinned.MAX_PATCH_RUNS,
              "the patched client is within the patch bound of its pristine image",
              f"{nbytes:,} bytes in {nruns:,} runs {dwhy}"
              if nbytes is not None else dwhy)
    p = vaultpath.vault_path("run", "reskin-roster", "Gw.exe")
    if os.path.isfile(p):
        nbytes, nruns, _dwhy = pinned.diff_against_pristine(p, pinned.PINNED)
        check(nbytes is not None and nruns > pinned.MAX_PATCH_RUNS,
              "while the reskin experiment copy is far outside it",
              f"{nbytes:,} bytes in {nruns:,} runs -- registering this as "
              f"'our patched client' is what the bound refuses")
        check(pinned.identify(p, build=pinned.PINNED)[0] == "unknown",
              "-- and it is still unknown, because it was never registered",
              "the bound is a sanity check on registering, not the gate")
    else:
        LEDGER.skip("the reskin experiment copy", f"not at {p}")

    # AND THE THIRD NUMBER IN THAT REFUSAL, re-measured here rather than quoted.
    # "the other build of the same length is ..." is what tells an operator
    # "ours, unregistered" from "not this build at all", and it read **152,944**
    # until this was checked -- which is `run/reskin-roster/Gw.exe` measured
    # against 38833's pristine: an outlier copy against the wrong build, printed
    # as a property of the two BUILDS. Pristine against pristine is 2,613,239
    # bytes in 152,735 runs. Nothing that rests on the figure moves (every
    # cross-build pair in the vault is 152,735-152,944, four orders of magnitude
    # from our 6-9 either way) -- but a number a refusal quotes and nothing
    # re-measures is the same wish as a rule nothing checks, and this is the one
    # number in that message that is not computed from the file in hand.
    same_size = [b for b in have if b.size == pinned.SIZE]
    if len(same_size) >= 2:
        first, second = same_size[0], same_size[1]
        nbytes, nruns, dwhy = pinned.diff_against_pristine(
            os.path.join(root, first.stamp, "Gw.exe"), second)
        check(nbytes == 2_613_239 and nruns == 152_735,
              f"the two pristine images at {pinned.SIZE:,} bytes are the "
              f"cross-build distance the refusal quotes",
              f"{pinned.name_of(first)} vs {pinned.name_of(second)}: "
              f"{nbytes:,} bytes in {nruns:,} runs {dwhy}"
              if nbytes is not None else dwhy)
    else:
        LEDGER.skip("the cross-build distance",
                    f"fewer than two builds at {pinned.SIZE:,} bytes are in the "
                    f"vault, so there is no same-length pair to measure")

print("\n5. assert_build() refuses a client that is not the build  (no vault)")

tmp = tempfile.mkdtemp(prefix="rurik_pinned_")
try:
    impostor = os.path.join(tmp, "Gw.exe")
    with open(impostor, "wb") as fh:
        fh.truncate(pinned.PINNED.size)
    check(refused(pinned.assert_build, impostor),
          "a right-sized, wrong-bytes client is REFUSED")
    try:
        what = pinned.assert_build(impostor, allow_any=True)
        check(what == "unknown",
              "and allow_any=True returns the verdict instead of raising",
              f"{what!r} -- so the caller can print its own warning")
    except SystemExit:
        check(False, "allow_any=True returns instead of raising", "it refused")

    if root:
        good = os.path.join(root, pinned.PINNED.stamp, "Gw.exe")
        check(pinned.assert_build(good) == "pristine",
              "while the real pinned client passes the gate",
              "the refusal above is the hash, not a gate that refuses everything")
        old = os.path.join(root, older.stamp, "Gw.exe")
        check(refused(pinned.assert_build, old),
              "and the OTHER real client is refused",
              "a genuine ArenaNet build is still the wrong one for these offsets")
        check(pinned.assert_build(old, build=older.stamp) == "pristine",
              "-- but passes when that is the build asked for")
finally:
    shutil.rmtree(tmp, ignore_errors=True)


print("\n6. the probes gate BEFORE they read  (syntax tree, no client)")


def first_line(fn_node, names):
    """Line of the first call to any of `names` inside `fn_node`, or None."""
    best = None
    for n in ast.walk(fn_node):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        name = (f.attr if isinstance(f, ast.Attribute)
                else f.id if isinstance(f, ast.Name) else None)
        if name in names:
            best = n.lineno if best is None else min(best, n.lineno)
    return best


def find_fn(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return n
    return None


GATES = {"assert_build", "gate"}
READS = {"read_at", "read_rva", "read_handle", "u32", "u8", "read"}


def gates_before_reads(src, fnname):
    """(ok, gate_line, read_line). ok is False if either is missing."""
    fn = find_fn(ast.parse(src), fnname)
    if fn is None:
        return None, None, None
    g, r = first_line(fn, GATES), first_line(fn, READS)
    if g is None or r is None:
        return False, g, r
    return g < r, g, r


# The real thing. `probe()` and `main()` are where the RVAs get dereferenced.
for path, fnname in ((os.path.join(HERE, "agentprobe.py"), "probe"),
                     (os.path.join(HERE, "itemprobe.py"), "main")):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    ok, g, r = gates_before_reads(src, fnname)
    check(ok, f"{os.path.basename(path)}:{fnname}() gates before its first read",
          f"gate at line {g}, first read at line {r}")

# THE CONTROL. "Before" is invisible to a grep -- a file with both names in the
# wrong order greps identically -- so the checker is required to REJECT a
# reversed version. Without this the check above is decoration.
REVERSED = '''
import keytap, pinned
def probe(pid):
    v = keytap.read_at(pid, 0x1000, 4)
    pinned.assert_build("Gw.exe")
    return v
'''
ok, g, r = gates_before_reads(REVERSED, "probe")
check(ok is False,
      "and the check REJECTS a probe that reads before it gates",
      f"gate at {g}, read at {r} -- both names present, wrong order")

MISSING = '''
import keytap
def probe(pid):
    return keytap.read_at(pid, 0x1000, 4)
'''
ok, g, r = gates_before_reads(MISSING, "probe")
check(ok is False, "and rejects one with no gate at all", f"gate line {g}")

ORDERED = '''
import keytap, pinned
def probe(pid):
    pinned.assert_build("Gw.exe")
    return keytap.read_at(pid, 0x1000, 4)
'''
ok, _g, _r = gates_before_reads(ORDERED, "probe")
check(ok is True, "while accepting the correct order",
      "so it is not simply rejecting everything")

# Both probes must expose the escape hatch, or the gate is one a session deletes
# the day a build ships rather than one it passes a flag to.
for path in (os.path.join(HERE, "agentprobe.py"), os.path.join(HERE, "itemprobe.py")):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    check("--any-build" in src,
          f"{os.path.basename(path)} offers --any-build as a deliberate override")
    check("allow_any" in src,
          f"-- and threads it through to the gate")

print("\n7. the patched digest SET and the patcher's registration  (a fake vault)")

# WHY THIS SECTION EXISTS. Until 2026-08-19 "our patched copy" was ONE hand-typed
# sha256 of ONE whole file, and a whole-file hash of a patched binary goes stale
# the moment the patcher changes. It did: the key-tap added three sites, and from
# that day the gate REFUSED the freshly patched client we launch while ACCEPTING
# the two superseded copies. Registering today's hash would fix today and rot the
# same way, so the fix is that the PATCHER records its own output -- and a
# mechanism no call site spends is a wish, which is why the call sites are
# asserted on the syntax tree below.
#
# Everything here runs against a FAKE vault: the registry is a real file written
# on disk and the real vault must not be touched by a test run.

tmp = tempfile.mkdtemp(prefix="rurik_pinned_")
real_vaultpath = pinned.vaultpath
try:
    fake_root = os.path.join(tmp, "vault")
    os.makedirs(fake_root)
    pinned.vaultpath = FakeVault(fake_root)
    pinned.load_registry(force=True)             # drop any cache from the real one

    # A pristine stand-in of the pin's exact size, and copies of it that differ
    # in a controlled number of RUNS. Sparse files, so this is cheap.
    pristine_dir = os.path.join(fake_root, "client", pinned.STAMP)
    os.makedirs(pristine_dir)
    fake_pristine = os.path.join(pristine_dir, "Gw.exe")
    with open(fake_pristine, "wb") as fh:
        fh.truncate(pinned.SIZE)

    def variant(name, edits):
        """A copy of the fake pristine with `edits` = [(offset, bytes)]."""
        p = os.path.join(tmp, name)
        shutil.copyfile(fake_pristine, p)
        with open(p, "r+b") as fh:
            for off, blob in edits:
                fh.seek(off)
                fh.write(blob)
        return p

    ours = variant("ours.exe", [(0x40000, b"\x01\x02\x03")])
    check(os.path.getsize(ours) == pinned.SIZE and os.path.getsize(ours) > 0,
          "planted a NON-EMPTY file of the pin's exact size, 3 bytes from pristine",
          f"{os.path.getsize(ours):,} bytes")

    # (a) THE REFUSAL CONTROL, before anything is registered. Right size, wrong
    #     bytes, unregistered -> refused. If this ever stops firing, everything
    #     below is measuring a gate that accepts anything.
    check(refused(pinned.assert_build, ours, pinned.PINNED),
          "an unregistered right-sized file is REFUSED",
          "the gate is real before the registration, or the acceptance proves nothing")

    # (b) REGISTERED THROUGH THE PATCHER'S OWN ENTRY POINT, then accepted.
    digest, action, detail = pinned.register_patched(
        ours, build=pinned.STAMP, how="a test fixture, not a client",
        tool="test_pinned.py")
    check(action == "added", "register_patched() files it", f"{action}: {detail}")
    check(digest == pinned.sha256(ours), "and records the file's real sha256")
    what, why = pinned.identify(ours, build=pinned.PINNED)
    check(what == "patched", "the SAME file is now accepted as ours", why)
    check(pinned.assert_build(ours, pinned.PINNED) == "patched",
          "-- and the gate that refused it in (a) now passes it")

    # (c) THE STALE-HASH SCENARIO, which is the defect itself. The build's
    #     committed digests do NOT include this file -- exactly as `fa9563f1...`
    #     did not include the key-tapped client -- and it is accepted anyway,
    #     because the digest SET does. The reason has to say which source
    #     vouched, or "accepted" is unattributable.
    check(digest not in [p.sha256 for p in pinned.PINNED.patched],
          "the accepted file is NOT one of the committed digests",
          "this is the stale-hash configuration reproduced")
    check("vault registry" in why
          and "committed in pinned.BUILDS" not in why,
          "so the reason names the vault registry, and does NOT claim the "
          "repository vouched", why)
    check("NOT yet committed" in why,
          "-- and says it has not been committed, so the drift is visible",
          "an invisible drift is how the single hash went stale unnoticed")

    d2, a2, _ = pinned.register_patched(ours, build=pinned.STAMP,
                                        tool="test_pinned.py")
    check(a2 == "already" and d2 == digest,
          "registering the same file twice is idempotent", a2)

    # (d) AN UNKNOWN BUILD STILL REFUSES, on both doors.
    check(refused(pinned.assert_build, ours, 99999),
          "assert_build against an unknown build is refused")
    _d, a3, why3 = pinned.register_patched(ours, build=99999)
    check(a3 == "refused", "and so is registering one under an unknown build", a3)
    check(refused(pinned.assert_build, fake_pristine, pinned.PINNED),
          "a file that is no recorded copy at all is still refused",
          "the fake pristine is 10 MB of zeros -- right size, no digest")

    # (e) REGISTRATION IS NOT A RUBBER STAMP. Each of these is a way the new
    #     write path could have widened the gate, and each is refused.
    _d, a4, why4 = pinned.register_patched(fake_pristine, build=pinned.STAMP)
    check(a4 == "refused" and "identical" in why4,
          "a file identical to the pristine image cannot be registered as patched",
          why4)

    small = os.path.join(tmp, "small.exe")
    with open(small, "wb") as fh:
        fh.write(b"\0" * 4096)
    _d, a5, why5 = pinned.register_patched(small, build=pinned.STAMP)
    check(a5 == "refused" and "bytes" in why5,
          "a file of the wrong size cannot be registered", why5)

    # 200 separate one-byte edits = 200 runs, far past MAX_PATCH_RUNS. This is
    # the shape of the reskin experiment copy (211 runs), which is a real client
    # of the right build that should NOT be filed as "our patched client".
    far = variant("far.exe", [(0x80000 + i * 512, b"\xAA") for i in range(200)])
    _d, a6, why6 = pinned.register_patched(far, build=pinned.STAMP)
    check(a6 == "refused" and "runs" in why6,
          f"a file {200} runs from pristine is refused by the sanity bound",
          why6)
    # THE POSITIVE HALF. Without it, (e) is satisfied by a register_patched that
    # refuses everything -- and then the patcher registers nothing and the gate
    # goes stale again by a different route.
    _d, a7, why7 = pinned.register_patched(far, build=pinned.STAMP, strict=False,
                                           how="deliberately far, named as such")
    check(a7 == "added", "-- and strict=False registers it anyway, deliberately",
          why7)

    # (f) INFERENCE REFUSES RATHER THAN GUESSING. 38797 and 38833 are the same
    #     LENGTH, so a registration with no --build and no source hash used to
    #     fall through to the pin and would have filed a patched 38833 under
    #     38797 in silence.
    b_inf, iwhy = pinned.infer_build(ours)
    check(b_inf is pinned.PINNED,
          "infer_build names the build a patched copy is closest to", iwhy)
    b_inf2, iwhy2 = pinned.infer_build(far)
    check(b_inf2 is None,
          "and refuses a file far from every pristine image rather than guessing",
          iwhy2)

    # (g) A CORRUPT REGISTRY FAILS CLOSED AND SAYS SO. It must not read as empty.
    with open(pinned.registry_path(), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    rows, rwhy = pinned.load_registry(force=True)
    check(rows == [] and "UNREADABLE" in rwhy,
          "a corrupt registry yields no rows and NAMES itself unreadable", rwhy)
    check(refused(pinned.assert_build, ours, pinned.PINNED),
          "-- so the file it vouched for is refused again, not silently accepted")
finally:
    pinned.vaultpath = real_vaultpath
    pinned.load_registry(force=True)
    shutil.rmtree(tmp, ignore_errors=True)


print("\n8. the PATCHER registers its own output  (syntax tree, nothing written)")

# The call-site half, asked of the tree for the same reason section 6 is: a
# correct mechanism that no call site spends is the failure mode this repo keeps
# hitting, and "registers after it writes" greps identically to "registers before
# it writes". WRITES is the moment the patched bytes land on disk.
REGISTERS = {"register_patched"}
WRITES = {"write", "copy2", "copyfile"}


def registers_after_write(src, fnname):
    """(ok, write_line, register_line). ok is False if either is missing."""
    fn = find_fn(ast.parse(src), fnname)
    if fn is None:
        return None, None, None
    w, r = first_line(fn, WRITES), first_line(fn, REGISTERS)
    if w is None or r is None:
        return False, w, r
    return w < r, w, r


def guarded_together(src, fnname, module, callee):
    """(ok, why): are `import <module>` AND a call to `callee` in ONE try/except?

    THE CHECK THIS REPLACES WAS `"pinned" in src`, which a comment satisfies --
    and both patchers carry a long comment about `pinned.py` directly above the
    call, so the string was there before the call was. Worse, the thing both
    files SAY in that comment is that the registration is "NON-FATAL,
    deliberately", and the import sat OUTSIDE the guard: an ImportError, or a
    vault path that moved, took down a patcher run that had already written and
    verified a 10 MB binary. A promise in a comment is a wish; this asks the
    syntax tree whether the call site keeps it.
    """
    fn = find_fn(ast.parse(src), fnname)
    if fn is None:
        return False, f"no {fnname}() in this file"
    for node in ast.walk(fn):
        if not isinstance(node, ast.Try) or not node.handlers:
            continue
        inner = [n for stmt in node.body for n in ast.walk(stmt)]
        imported = any(isinstance(n, ast.Import)
                       and any(al.name == module for al in n.names)
                       for n in inner)
        called = any(isinstance(n, ast.Call)
                     and (getattr(n.func, "attr", None) == callee
                          or getattr(n.func, "id", None) == callee)
                     for n in inner)
        if imported and called:
            return True, f"try/except at line {node.lineno} holds both"
    return False, (f"no try/except in {fnname}() holds both `import {module}` "
                   f"and a call to {callee}()")


def register_build_arg(src, fnname):
    """(found, source text of the `build=` argument) of the register_patched call.

    `CLAUDE.md`: never select a build by filename. `make_run_dir.py` passed
    `build=tag`, and `tag` is a regex over the SOURCE EXE'S NAME -- while
    `register_patched` prefers an explicit build over the source hash AND over
    its own inference, so the filename outranked the bytes. 38797 and 38833 are
    the same LENGTH, so the size check cannot catch a mis-named source; the only
    guard that could is the pristine comparison, which is the one section 9 (a)
    found failing open. `None` here means "the bytes decide".
    """
    fn = find_fn(ast.parse(src), fnname)
    if fn is None:
        return False, "no such function"
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call):
            continue
        if getattr(n.func, "attr", None) != "register_patched":
            continue
        for kw in n.keywords:
            if kw.arg == "build":
                return True, ast.unparse(kw.value)
        return True, "not passed at all"
    return False, "no register_patched call"


PATCHER = os.path.join(os.path.dirname(HERE), "clientpatch")
for name in ("make_custom_client.py", "make_run_dir.py"):
    path = os.path.join(PATCHER, name)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    found, arg = register_build_arg(src, "main")
    check(found and arg in ("None", "not passed at all"),
          f"{name} does NOT hand register_patched a build of its own choosing",
          f"build={arg} -- a filename is not a build; the hash and the "
          f"structural distance are")
    ok, w, r = registers_after_write(src, "main")
    check(ok, f"{name}:main() registers the digest AFTER it writes the file",
          f"write at line {w}, register at line {r}")
    ok, gwhy = guarded_together(src, "main", "pinned", "register_patched")
    check(ok, f"-- and {name} imports pinned INSIDE the same try as the call",
          f"{gwhy}; both files call this non-fatal in a comment, so the guard "
          f"has to be where the work is")

# THE CONTROLS for the guard check, both directions, because "in the same try"
# is exactly as invisible to a grep as "before it reads" was in section 6.
SPLIT = '''
import pinned
def main():
    open("out", "wb").write(b"x")
    try:
        pinned.register_patched("out")
    except Exception:
        pass
'''
ok, gwhy = guarded_together(SPLIT, "main", "pinned", "register_patched")
check(ok is False,
      "the checker REJECTS a module-level import with only the call guarded",
      f"{gwhy} -- an ImportError there kills a run that already wrote the binary")

BARE = '''
def main():
    open("out", "wb").write(b"x")
    import pinned
    pinned.register_patched("out")
'''
ok, gwhy = guarded_together(BARE, "main", "pinned", "register_patched")
check(ok is False, "and rejects one with no try/except at all", gwhy)

TOGETHER = '''
def main():
    open("out", "wb").write(b"x")
    try:
        import pinned
        pinned.register_patched("out")
    except Exception:
        pass
'''
ok, gwhy = guarded_together(TOGETHER, "main", "pinned", "register_patched")
check(ok is True, "while accepting both inside one try", gwhy)

# THE CONTROLS for the build argument, both directions. `build=tag` is the exact
# expression this file carried until 2026-08-19, and it greps identically to any
# other keyword argument.
BY_NAME = '''
import pinned
def main():
    tag = re.match(r"Gw\\.[^.]+\\.(.+)\\.exe$", name).group(1)
    pinned.register_patched(tgt, build=tag)
'''
found, arg = register_build_arg(BY_NAME, "main")
check(found and arg not in ("None", "not passed at all"),
      "the checker REJECTS a patcher that passes a build it took from a filename",
      f"build={arg} -- the expression make_run_dir.py carried until 2026-08-19")

BY_BYTES = '''
import pinned
def main():
    pinned.register_patched(tgt, build=None, tool="x")
'''
found, arg = register_build_arg(BY_BYTES, "main")
check(found and arg == "None", "while accepting build=None", f"build={arg}")

# AND THE CROSS-CHECK HAS TO EXIST, not just the absence of the bad argument:
# `make_run_dir.py` still knows the filename tag, and a tag that names a build
# other than the one the BYTES say must refuse the registration rather than be
# ignored. Asked as an ordering, like section 6: inference first, then the call.
with open(os.path.join(PATCHER, "make_run_dir.py"), encoding="utf-8") as fh:
    src = fh.read()
run_main = find_fn(ast.parse(src), "main")
inf = first_line(run_main, {"infer_build"})
reg = first_line(run_main, {"register_patched"})
check(inf is not None and reg is not None and inf < reg,
      "make_run_dir.py infers the build from the bytes BEFORE it registers",
      f"infer_build at line {inf}, register_patched at line {reg}")

# THE CONTROL, both directions. Without these the check above is decoration.
NO_REGISTER = '''
def main():
    open("out", "wb").write(b"x")
'''
ok, _w, _r = registers_after_write(NO_REGISTER, "main")
check(ok is False, "the checker REJECTS a patcher that registers nothing",
      "which is the state both files were in until 2026-08-19")

BEFORE = '''
import pinned
def main():
    pinned.register_patched("out")
    open("out", "wb").write(b"x")
'''
ok, w, r = registers_after_write(BEFORE, "main")
check(ok is False, "and rejects one that registers a file it has not written yet",
      f"write at {w}, register at {r} -- both names present, wrong order")

AFTER = '''
import pinned
def main():
    open("out", "wb").write(b"x")
    pinned.register_patched("out")
'''
ok, _w, _r = registers_after_write(AFTER, "main")
check(ok is True, "while accepting the correct order",
      "so it is not simply rejecting everything")


print("\n9. the four ways the write path failed OPEN  (a fake vault)")

# WHY THIS SECTION EXISTS, and it is not symmetry with section 7. Section 7 asks
# whether the digest SET works; this asks what else "register" now lets somebody
# say. Every check below is an attack that SUCCEEDED against the 2026-08-19
# morning code and was measured before it was fixed -- random bytes accepted
# under strict, ArenaNet's own image filed as ours, a registration the operator
# was told was REFUSED honoured by the gate for the rest of the process. Each has
# a positive half, because a `register_patched` that refuses everything puts the
# staleness back by another route, and each asserts its fixture is a real
# non-empty file first: an attack on an empty file proves nothing about a gate.

tmp = tempfile.mkdtemp(prefix="rurik_pinned_")
real_vaultpath = pinned.vaultpath
try:
    # (a) NO PRISTINE IMAGE ON DISK. `diff_against_pristine` answers
    #     (None, None, why) and the sanity bound read `if nruns is not None and
    #     nruns > MAX_PATCH_RUNS and strict`, so it did not run at all -- in the
    #     one configuration where nothing else can tell a patch from a stranger.
    #     MEASURED: 10,483,904 bytes of os.urandom registered under strict=True,
    #     and assert_build then answered "patched".
    bare = os.path.join(tmp, "bare-vault")
    os.makedirs(bare)
    pinned.vaultpath = FakeVault(bare)
    pinned.load_registry(force=True)

    rnd = os.path.join(tmp, "random.exe")
    with open(rnd, "wb") as fh:
        fh.write(os.urandom(pinned.SIZE))
    check(os.path.getsize(rnd) == pinned.SIZE > 0,
          "planted a NON-EMPTY file of RANDOM bytes at the pin's exact size",
          f"{os.path.getsize(rnd):,} bytes, no relation to any client")
    nb, nr, dwhy = pinned.diff_against_pristine(rnd, pinned.PINNED)
    check(nb is None and nr is None,
          "and this vault holds no pristine image to compare it against", dwhy)

    _d, a, why = pinned.register_patched(rnd, build=pinned.STAMP, strict=True,
                                         tool="test_pinned.py",
                                         how="RANDOM BYTES, the attack")
    check(a == "refused" and "nothing to compare it against" in why,
          "strict registration REFUSES what it cannot compare",
          f"{a}: {why}")
    check(refused(pinned.assert_build, rnd, pinned.PINNED),
          "-- so the gate still refuses 10 MB of noise",
          "it accepted it before 2026-08-19, and called it 'patched'")
    # THE POSITIVE HALF: the refusal is the missing image, not a dead function,
    # and the message's own escape hatch has to work or it is not one.
    _d, a2, why2 = pinned.register_patched(rnd, build=pinned.STAMP, strict=False,
                                           tool="test_pinned.py",
                                           how="deliberately unverifiable fixture")
    check(a2 == "added",
          "-- while strict=False registers it deliberately, as the refusal says",
          why2)

    # (b) ANOTHER BUILD'S PRISTINE, UNDER --force. The refusal compared the
    #     SELECTED build's pristine only. MEASURED: the real pristine 38833 image
    #     registered under build=38797 with strict=False, and
    #     assert_build(<it>, 38797) answered "patched" -- the gate vouching for
    #     ArenaNet's shipped binary as a copy we made. Still a bare vault, on
    #     purpose: this refusal must not depend on a comparison being possible.
    #     IT MUST BE A BUILD OF THE PIN'S OWN SIZE, or the attack never reaches
    #     the check: the size refusal fires first and the run goes green on the
    #     wrong sentence. 38833 is that build -- the same 10,483,904 bytes -- and
    #     the size collision is exactly why this hole mattered.
    other = [b for b in pinned.BUILDS if b is not pinned.PINNED]
    foreign = None
    for b in [x for x in other if x.size == pinned.SIZE]:
        p = os.path.join(real_vaultpath.vault_root(), "client", b.stamp, "Gw.exe")
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            foreign = (p, b)
            break
    if foreign is None:
        LEDGER.skip("another build's pristine, filed as ours",
                    f"the real vault holds no pristine image of a SECOND build at "
                    f"{pinned.SIZE:,} bytes, and a different size is refused by "
                    f"the size check before this one is reached")
    else:
        p, b_other = foreign
        check(os.path.getsize(p) == b_other.size > 0
              and pinned.sha256(p) == b_other.pristine,
              f"holding the REAL pristine image of build "
              f"{pinned.name_of(b_other)}",
              f"{os.path.getsize(p):,} bytes, sha256 {b_other.pristine[:16]}...")
        _d, a3, why3 = pinned.register_patched(
            p, build=pinned.STAMP, strict=False, tool="test_pinned.py",
            how="ArenaNet's own image, offered as ours")
        check(a3 == "refused" and "PRISTINE image of build" in why3,
              f"filing {pinned.name_of(b_other)}'s PRISTINE image as our patched "
              f"{pinned.BUILD} is refused even with strict=False",
              f"{a3}: {why3}")
        check(refused(pinned.assert_build, p, pinned.PINNED),
              "-- and the gate still refuses it",
              "there is no legitimate reading of ArenaNet's file as one we made")
        # THE POSITIVE HALF: strict=False is not simply inert in this vault.
        second = os.path.join(tmp, "random2.exe")
        with open(second, "wb") as fh:
            fh.write(os.urandom(pinned.SIZE))
        _d, a4, why4 = pinned.register_patched(
            second, build=pinned.STAMP, strict=False, tool="test_pinned.py",
            how="a second deliberate fixture")
        check(a4 == "added",
              "-- while a file that is nobody's pristine still registers under it",
              f"{a4}: so (b) is the pristine digest, not strict=False refusing all")

    # (c) A FAILED WRITE, HONOURED ANYWAY. `rows.append(...)` mutated the list
    #     cached in `_registry` BEFORE the write was attempted, and the OSError
    #     path returned "refused" without dropping it. MEASURED: action='refused',
    #     no file on disk, accepted_patched 3 -> 4, assert_build "patched".
    walled = os.path.join(tmp, "walled-vault")
    os.makedirs(os.path.join(walled, "client", pinned.STAMP))
    fake_pristine = os.path.join(walled, "client", pinned.STAMP, "Gw.exe")
    with open(fake_pristine, "wb") as fh:
        fh.truncate(pinned.SIZE)
    pinned.vaultpath = FakeVault(walled)
    pinned.load_registry(force=True)

    plausible = os.path.join(tmp, "plausible.exe")
    shutil.copyfile(fake_pristine, plausible)
    with open(plausible, "r+b") as fh:
        fh.seek(0x40000)
        fh.write(b"\x01\x02\x03")
    check(os.path.getsize(plausible) == pinned.SIZE > 0,
          "planted a NON-EMPTY file 3 bytes from this vault's pristine image",
          f"{os.path.getsize(plausible):,} bytes -- it would otherwise register")

    # The write fails because the registry PATH is a directory. Nothing else
    # about the call changes, which is what makes the write the variable.
    os.makedirs(pinned.registry_path())
    before = len(pinned.accepted_patched(pinned.PINNED))
    _d, a5, why5 = pinned.register_patched(plausible, build=pinned.STAMP,
                                           tool="test_pinned.py",
                                           how="a fixture whose write must fail")
    after = len(pinned.accepted_patched(pinned.PINNED))
    check(a5 == "refused" and "could not write" in why5,
          "a registration whose write fails reports REFUSED", f"{a5}: {why5}")
    check(not os.path.isfile(pinned.registry_path()),
          "-- with no registry file on disk", pinned.registry_path())
    check(after == before,
          "-- and the accepted set is UNCHANGED, in this process",
          f"{before} -> {after}; it went 3 -> 4 before 2026-08-19")
    check(refused(pinned.assert_build, plausible, pinned.PINNED),
          "-- so the gate refuses the file the operator was told was refused",
          "a refusal the gate then honours is worse than a crash")

    # THE POSITIVE HALF: remove the obstruction and the SAME call files it, so
    # (c) is the failed write and not a registration that stopped working.
    os.rmdir(pinned.registry_path())
    _d, a6, why6 = pinned.register_patched(plausible, build=pinned.STAMP,
                                           tool="test_pinned.py",
                                           how="the same fixture, write allowed")
    check(a6 == "added" and os.path.isfile(pinned.registry_path()),
          "-- while the same call with the write unblocked files it", why6)
    check(pinned.assert_build(plausible, pinned.PINNED) == "patched",
          "-- and only THEN does the gate accept it")

    # (d) A ROW THAT CANNOT VOUCH IS DROPPED ON READ. The shape check was
    #     `isinstance(r, dict) and r.get("sha256")`, which honours a truncated
    #     digest and -- the one that matters -- a row whose `build` and `stamp`
    #     name two DIFFERENT builds: `accepted_patched` matches on stamp OR
    #     number, so one such row vouched under both.
    other_build = other[0] if other else pinned.PINNED
    good = "a" * 64
    crossed = "b" * 64
    with open(pinned.registry_path(), "w", encoding="utf-8") as fh:
        json.dump({"rows": [
            {"sha256": good, "build": pinned.BUILD, "stamp": pinned.STAMP,
             "how": "well formed", "tool": "test_pinned.py"},
            {"sha256": "deadbeef", "build": pinned.BUILD, "stamp": pinned.STAMP,
             "how": "truncated digest", "tool": "test_pinned.py"},
            {"sha256": crossed, "build": pinned.BUILD, "stamp": other_build.stamp,
             "how": "build and stamp disagree", "tool": "test_pinned.py"},
        ]}, fh)
    rows, rwhy = pinned.load_registry(force=True)
    check(len(rows) == 1 and rows[0]["sha256"] == good,
          "a hand-edited registry keeps only the rows that are well formed",
          f"{len(rows)} of 3 kept -- {rwhy}")
    check("REJECTED" in rwhy and "2 row(s)" in rwhy,
          "-- and NAMES how many it dropped, rather than reading as merely short",
          rwhy)
    accepted = [x.sha256 for x in pinned.accepted_patched(pinned.PINNED)]
    check(good in accepted and crossed not in accepted,
          "the well-formed row still vouches; the crossed one vouches for nothing",
          f"{len(accepted)} accepted digest(s) for {pinned.BUILD}")
    if other:
        accepted_other = [x.sha256
                          for x in pinned.accepted_patched(other_build.stamp)]
        check(crossed not in accepted_other,
              f"-- and not for {pinned.name_of(other_build)} either, which is the "
              f"half that made it dangerous",
              "matched on stamp OR number, one row vouched under both builds")
finally:
    pinned.vaultpath = real_vaultpath
    pinned.load_registry(force=True)
    shutil.rmtree(tmp, ignore_errors=True)


sys.exit(LEDGER.verdict())
