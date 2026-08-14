"""Which `Gw.exe` a static-analysis tool is reading, said once and checked.

    python toolkit/clientscan/pinned.py            # what is in the vault, and what it is

WHY THIS EXISTS, and it is a defect rather than tidiness. The vault holds TWO
copies of build 38797, and they are **not the same file**:

    vault/client/2026-07-29_221c13772c7a/Gw.exe   pristine, as ArenaNet shipped it
    vault/run/2026-07-29_221c13772c7a/Gw.exe      our PATCHED copy, what we launch

They are byte-for-byte identical in length -- 10,483,904 -- and differ in 144
bytes: the DH modulus, a `-Window` string, and **nine bytes in `.text`** where
the version check and one `sete al` are patched out. So a guard that checks the
file SIZE, which is what `test_skillcast.py` and `test_catalog.py` did, cannot
tell the two apart, and every one of them would pass against either.

Nothing was actually measured wrong -- both test suites reproduce identically
against either copy, checked -- but the guard could not have caught it, and the
tools did not agree on which copy they wanted. There were eight spellings of
"the pinned client" across `toolkit/clientscan/`: the live install at `C:\\gw`,
two hardcoded absolute vault paths, `("run", ...)` in three places, and
`("client", ...)` in `srctree.py` alone.

FINISHED 2026-08-10, and it was half done for four days. Writing this module
converted five call sites and left eleven behind, so the defect it describes
was still live in most of the directory: `asserts.py`, `avevents.py`,
`genericvalue.py`, `msghandler.py`, `msgshape.py`, `skilltable.py`,
`test_skilltable.py`, `argtable.py` and `protoscan.py` still defaulted to the
live install at `C:\\gw\\Gw.exe`, which auto-updates and is therefore not
necessarily build 38797 at all -- and `areatable.py` and `textrec.py` named an
absolute path into `vault/run/`, our PATCHED copy, hardcoding `C:\\gd\\Rurik\\vault`
past `vaultpath.py` so that a moved vault or a git worktree resolved to nothing.
All eleven now call `find()`, and every one of them prints the path and the
`why` before it reads a byte. A tool that silently picks its own client is how
a provenance misreport happens, and the fix is only worth anything applied
everywhere: one straggler is enough to produce a study that cites the wrong
binary.

WHAT STILL NAMES ITS OWN CLIENT, on purpose. `dump_dh_params.py` defaults to
`C:\\gw\\Gw.exe` because its job is reading the Diffie-Hellman struct out of
whichever client you point it at -- including the live install, which is the
one whose parameters rotate. `make_custom_client.py`, `repoint_skill.py` and
`datwrite.py` mention `C:\\gw` only as a refusal guard: never write into the
owner's install. Neither is a spelling of "the pinned client" and neither
should route through here.

WHICH COPY IS CANONICAL: the **pristine** one. A study of the shipped client
that reads our own patch is reading us, not ArenaNet, and provenance is the one
thing this repository cannot retrofit. `run/` is accepted as a fallback because
it is the copy a session is most likely to have, but `find()` NAMES which one it
returned and `identify()` reports what a file actually is. The patched bytes are
listed below so a claim landing on one is visible rather than silent.

READ ONLY, standard library only. Every tool here can `--exe` past it; this
sets the default and makes the default checkable.

TWO THINGS CHANGED 2026-08-12, both from `studies/crossbuild/PLAN.md` §5.

**`find()` now verifies, and it no longer fails open.** It used to test
`os.path.isfile` and return, so `identify()` -- the only thing here that
actually checks a file is what it claims -- was reachable from `main()` and two
tests and from nothing on the path any analysis tool takes. Worse, the last
fallback was the live install at `C:\\gw`, which auto-updates, handed back with
the string "may not be 38797" and no refusal. Twelve tools in this directory
resolve their client through here and every one of them computes with addresses
measured on one build, so the only thing between that and a published number was
a human reading a line of output. A rule nothing checks is a wish. The live
install is now opt-in (`allow_live=True`) and a build whose bytes do not match
what we recorded is REFUSED rather than named.

**This module knows there is more than one build.** It described a single pin,
so `test_srctree.py` -- the only genuine cross-ArenaNet-build test in the tree --
had to carry its own list of stamps, and any other test wanting both builds would
have carried a second copy of it. `BUILDS` is now that list, and `find(build=...)`
takes a build number or a vault stamp.
"""

import collections
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vaultpath                                              # noqa: E402

Build = collections.namedtuple("Build", "stamp number size pristine patched")

# Every ArenaNet build in the vault, oldest first. MEASURED 2026-08-06 and
# 2026-08-12. The stamp is the PRISTINE file's own sha256 prefix -- the
# convention `snapshot_client.py` writes -- which is why the patched copy filed
# under the same stamp is easy to miss: the name is right and the bytes are not.
#
# `number` is the client's own build id, READ OUT OF THE BINARY by
# `buildid.py` -- it is not typed in here, and `test_buildid.py` asserts both of
# these against a fresh read of the image.
#
# SUPERSEDED 2026-08-13, and the history matters because this comment used to
# say the opposite. Until `buildid.py` existed the older build's number was
# `None`, and that was a MEASUREMENT rather than a gap: nothing here could read a
# build number, and the obvious place does not work -- the version resource is
# `FileVersion '1, 0, 0, 1'` on BOTH builds, identical, and identical again to
# four sibling DLLs that never changed. What changed is not the rule but the
# instrument: the client compiles its build as a whole function, `mov eax,
# <build>; ret`, and exactly one such getter on each build carries a five-digit
# value. So 38519 here is derived, not guessed, and the older build finally has
# a number. `studies/crossbuild/FINDINGS.md` §3.
BUILDS = (
    Build(stamp="2026-04-30_b174de1f2d8d", number=38519, size=10_404_032,
          pristine="b174de1f2d8dd4b5239e22714a96478af94ab5ad6b7bf308120562d5b49633a1",
          patched=None),
    Build(stamp="2026-07-29_221c13772c7a", number=38797, size=10_483_904,
          pristine="221c13772c7a4fd1f3efd6769694614ed608909706d60a9d2b7190ba10119a75",
          patched="fa9563f1851014e80117195a1b66850c913433c4aba584ec6309b97e46bbf7e6"),
)

# The current pin. Everything below defaults to it, so a caller that does not
# care which build it reads keeps reading the one every address in `studies/`
# was measured against.
PINNED = BUILDS[-1]

# Named individually because callers spell them that way and have since before
# `BUILDS` existed. They are the pinned row and nothing else.
BUILD = PINNED.number
SIZE = PINNED.size
STAMP = PINNED.stamp
PRISTINE_SHA256 = PINNED.pristine
PATCHED_SHA256 = PINNED.patched

# The nine `.text` bytes our patch changes, as virtual addresses. MEASURED by
# diffing the two copies. Listed so that a study pinning an address can be
# checked against them -- `patches_touch()` does exactly that. No address in
# studies/skillcast, studies/agentprops or studies/enemy lands in either range.
PATCHED_TEXT = [
    (0x0047E65F, 0x0047E665, "the build/version check"),
    (0x00833ECA, 0x00833ECC, "a `sete al` result, forced"),
]
# .rdata, for completeness: 0x0093F7AB a `-Window` flag string, and
# 0x00A910E1..0x00A9115F the Diffie-Hellman modulus RUNBOOK.md says rotates
# with every client build.

LIVE_INSTALL = r"C:\gw\Gw.exe"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def name_of(build):
    """How to print a build. The older one has no number and must not pretend to."""
    return str(build.number) if build.number else f"{build.stamp} (number unknown)"


def select(spec=None):
    """The Build a caller means: None is the pin, else a build number or a stamp.

    Refuses an unknown spec rather than falling back to the pin. Silently
    reading a different build than the one asked for is the whole failure this
    module exists to prevent.
    """
    if spec is None:
        return PINNED
    if isinstance(spec, Build):
        return spec
    for b in BUILDS:
        if spec == b.number or spec == b.stamp:
            return b
    known = ", ".join(f"{b.stamp} = {name_of(b)}" for b in BUILDS)
    raise SystemExit(f"no such build in the vault: {spec!r}\n  known: {known}")


def identify(path, build=None):
    """('pristine' | 'patched' | 'unknown', human-readable detail).

    With no `build`, EVERY build in `BUILDS` is considered, so the older vaulted
    client identifies as itself rather than as "not 38797's size". Pass a number
    or a stamp to ask about one build specifically -- which is what `find()`
    does, because there the question is "is this the build I asked for", and a
    file that is honestly some OTHER build is still the wrong answer.
    """
    if not os.path.isfile(path):
        return "unknown", "no such file"
    size = os.path.getsize(path)
    candidates = [select(build)] if build is not None else list(BUILDS)
    sized = [b for b in candidates if b.size == size]
    if not sized:
        want = ", ".join(f"{b.size:,} (build {name_of(b)})" for b in candidates)
        return "unknown", f"{size:,} bytes, which is no build we hold -- have {want}"
    digest = sha256(path)
    for b in sized:
        if digest == b.pristine:
            return "pristine", f"build {name_of(b)}, as ArenaNet shipped it"
        if b.patched and digest == b.patched:
            return "patched", (f"build {name_of(b)}, OUR patched copy -- 9 bytes of "
                               f".text differ from the shipped client")
    return "unknown", (f"the size of build {name_of(sized[0])} but sha256 "
                       f"{digest[:16]}..., which is neither copy we hold")


def find(build=None, *, verify=True, allow_live=False):
    """(path, why). Pristine first, then our patched copy. VERIFIED by default.

    Never silently either -- `why` is meant to be printed. A tool that says
    which file it read lets a surprising result be diagnosed in one line
    instead of being argued about.

    `verify` hashes what it is about to return and REFUSES a file whose bytes
    are not one of the two copies we recorded for that build. This used to be
    the one thing `find()` did not do, and `identify()` sat here reachable only
    from `main()` and two tests.

    `allow_live` opts in to the auto-updating install at `C:\\gw`. It is off by
    default because every caller in `toolkit/clientscan/` computes with
    addresses measured on one build: reading an unknown build does not produce
    an error there, it produces a confident wrong number.
    """
    b = select(build)
    for kind, how in (("client", "pinned pristine client"),
                      ("run", "pinned PATCHED copy (pristine not in the vault)")):
        p = vaultpath.vault_path(kind, b.stamp, "Gw.exe")
        if not os.path.isfile(p):
            continue
        why = f"{how}, build {name_of(b)}"
        if not verify:
            return p, f"{why} -- UNVERIFIED, the caller passed verify=False"
        what, detail = identify(p, build=b)
        if what == "unknown":
            raise SystemExit(
                f"REFUSING to read {p}\n"
                f"  it is filed as build {name_of(b)} and its bytes are not:\n"
                f"      {detail}\n"
                f"  Every address a caller of this function uses was measured on a\n"
                f"  particular build, so reading another one returns a confident\n"
                f"  wrong number rather than an error. Re-snapshot, or pass an\n"
                f"  explicit --exe if you meant to read this file.")
        return p, f"{why}; verified {what} -- {detail}"

    if os.path.isfile(LIVE_INSTALL):
        if allow_live:
            what, detail = identify(LIVE_INSTALL)
            return LIVE_INSTALL, (f"live install -- auto-updates, so it may not be "
                                  f"build {name_of(b)}; sha256 says {what}: {detail}")
        raise SystemExit(
            f"build {name_of(b)} is not in the vault, and this call will NOT fall\n"
            f"  through to {LIVE_INSTALL}.\n"
            f"  looked in {vaultpath.vault_root()} ({vaultpath.vault_why()})\n"
            f"  for client/{b.stamp}/Gw.exe and run/{b.stamp}/Gw.exe\n"
            f"  The live install auto-updates, so it is not a stand-in for a pinned\n"
            f"  build -- that substitution is silent and every address downstream is\n"
            f"  build-specific. Pass allow_live=True if you genuinely want whatever\n"
            f"  is installed today, or set RURIK_VAULT. See RUNBOOK.md.")

    raise SystemExit(
        f"no client to read for build {name_of(b)}.\n"
        f"  looked in {vaultpath.vault_root()} ({vaultpath.vault_why()})\n"
        f"  for client/{b.stamp}/Gw.exe and run/{b.stamp}/Gw.exe\n"
        f"  and there is no live install at {LIVE_INSTALL} either.\n"
        f"  Set RURIK_VAULT, or see RUNBOOK.md.")


class WrongBuild(SystemExit):
    """Refusing to use build-specific offsets against a client that is not it."""


def assert_build(path, build=None, why="this measurement", allow_any=False):
    """Refuse unless `path` is a copy of `build` we recorded. Returns the kind.

    THE GATE for anything holding a hardcoded RVA, and it exists for the two
    tools where being wrong is worst: `itemprobe.py` and `agentprobe.py` read a
    LIVE client by `module_base + RVA`, so on a build those RVAs were not
    measured on they do not compute a wrong answer -- they dereference whatever
    else happens to be mapped there and print it as an agent array. Neither
    imported this module at all until 2026-08-12
    (`studies/crossbuild/FINDINGS.md` §2.1).

    `allow_any` is the deliberate escape hatch, because a gate that makes the
    tool unusable the day a build ships is a gate somebody deletes. It does not
    silence anything: the caller is expected to print what `WrongBuild` would
    have said.
    """
    # SCOPED, and this is the whole gate. `identify()` with no build considers
    # every build in the registry, so an unscoped call here would hand back
    # "pristine" for the OLDER vaulted client -- a real ArenaNet build, and the
    # wrong one for these offsets. Caught by test_pinned.py §5 while this
    # function was being written, which is the failure the section is for.
    b = select(build)
    what, detail = identify(path, build=b)
    if what in ("pristine", "patched"):
        return what
    msg = (f"REFUSING {why}: {path}\n"
           f"  is not a copy of build {name_of(b)} that we recorded --\n"
           f"      {detail}\n"
           f"  The offsets this tool uses were MEASURED on that build. Against\n"
           f"  another one they do not return a wrong number, they read whatever\n"
           f"  else is mapped at that address and print it as data.\n"
           f"  Re-derive them, or pass --any-build if you accept that.")
    if allow_any:
        return what
    raise WrongBuild(msg)


def patches_touch(va, span=1):
    """Do our patched .text bytes overlap [va, va+span)? The reason this list exists."""
    return [why for lo, hi, why in PATCHED_TEXT
            if not (va + span - 1 < lo or va > hi)]


def main():
    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})")
    for b in BUILDS:
        pin = "  <- the pin" if b is PINNED else ""
        print(f"\nbuild {name_of(b)}, {b.size:,} bytes, stamp {b.stamp}{pin}")
        for kind in ("client", "run"):
            p = vaultpath.vault_path(kind, b.stamp, "Gw.exe")
            what, detail = identify(p, build=b)
            print(f"  {kind + '/':8} {what:8} {detail}")
            print(f"           {p}")
    what, detail = identify(LIVE_INSTALL)
    print(f"\n  {'live':8} {what:8} {detail}")
    print(f"           {LIVE_INSTALL}")
    path, why = find()
    print(f"\ndefault for static analysis: {path}\n  ({why})")
    print("\nour patch changes these .text bytes; an address landing here is ours:")
    for lo, hi, w in PATCHED_TEXT:
        print(f"  0x{lo:08X}..0x{hi:08X}  {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
