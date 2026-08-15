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

Without a vault, section 4 skips and the run scores 43 against a floor of 55, so
it goes RED -- MEASURED with `RURIK_VAULT` pointed at an empty directory, not
derived by subtraction. That is deliberate: the other sections prove the refusals
fire, and only section 4 puts them against ArenaNet's real bytes, which is what
tells a working verifier from one that refuses everything. ~2 s.
"""
import ast
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

# floor re-measured 2026-08-14 from a real green run: 55 -> 61. Build 38833 adds
# a stamp check and an identify() call, and the rewritten size invariant (see
# below) contributes one assertion plus one per registered build.
LEDGER = checks.Ledger("pinned client selection", floor=61)
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
      and pinned.PATCHED_SHA256 == pinned.PINNED.patched,
      "the named constants are the pinned row and nothing else")

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

sys.exit(LEDGER.verdict())
