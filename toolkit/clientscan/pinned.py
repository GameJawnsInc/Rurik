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

(**"144 bytes" is the 2026-08-10 measurement and is now one of several.** The
vault holds four distinct patched copies of the pin, 57 to 187 bytes apart from
pristine, because the patcher has gained sites since -- see "OUR PATCHED COPY IS
A SET" below. The paragraph above is kept as written because the DEFECT it
describes is unchanged: size cannot separate any of them.)

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

"OUR PATCHED COPY" IS A SET, NOT A HASH -- 2026-08-19, and the gate it fixes was
INVERTED. `Build.patched` was one sha256 of one whole file, typed in by hand, and
a whole-file hash of a patched binary goes stale the moment the patcher changes.
It had: the recorded `fa9563f1...` is the pre-key-tap patcher's output, and the
current patcher writes three more sites (file 0x508E2, 0x50905, 0x3DB4CE -- the
key-tap's tap, its cave and its slot). So on 2026-08-19 the gate REFUSED the
freshly patched client at `vault/run/2026-07-29_221c13772c7a/` -- the one we
actually launch and the one `movetap.py`:438 gates -- while ACCEPTING the two
stale copies at `-c2/` and `-probe/`. It was refusing the right file and passing
the old ones. Build 38833 had no patched hash at all, so the newest build could
not be gated at all, and the only way past either was `--any-build`, which does
not fix a gate, it turns it off.

Two things changed, and the second is the one that stops the staleness:

  1. `Build.patched` is a TUPLE of `PatchedCopy(sha256, how)` -- every whole-file
     digest we accept as a copy WE made of that build, each carrying what it is
     and what it cost in bytes. sha256 is still exact, so a tampered file is
     still refused; there is simply more than one right answer.
  2. THE PATCHER APPENDS ITS OWN DIGEST. `make_custom_client.py` (which writes
     the patched exe) and `make_run_dir.py` (which lands it at the path
     `find()` returns) both call `register_patched()` after their own
     verification passes, into `vault/client-patched/patched_digests.json`.
     Registration is a step in building the client rather than a chore to
     remember afterwards, which is why the old single hash went stale: nothing
     was ever going to update a source literal by hand on patcher-change day.

WHY NOT VERIFY STRUCTURALLY -- same size as pristine, every differing byte inside
a registered site allowlist -- which was the other candidate. Three reasons, in
the order they decided it. (a) It is WEAKER where it matters most: an allowlist
accepts ANY bytes at an allowed site, and the most safety-critical bytes in this
file are exactly at one -- the Diffie-Hellman modulus, whose value decides which
server a build may be pointed at (`CLAUDE.md`, `dhbuild.py`). A whole-file sha256
refuses a modulus swap; an allowlist waves it through. (b) The patcher has no
site registry to export: it finds every site by BYTE SIGNATURE at patch time
(`SIG_MUTEX`, `SIG_DOWNLOAD`, `keytap_patch.plant`), and the sites move per build
-- the updater patch is at file 0x4332CA on 38797 and 0x43335A on 38833 -- so
"the allowlist" would be a hand-maintained per-build table, i.e. the same staleness
one level down. (c) It needs the pristine IMAGE on disk, not just its hash, and
costs a 10 MB byte-compare per call in the twelve tools that ask.

The structural comparison is kept where it is cheap and honest instead: as
EVIDENCE recorded at registration time (`diff_against_pristine`, whose numbers are
written into each `how` string), as a sanity refusal on registering something
wildly unlike a patch, and in the refusal message, where "differs in 682 bytes
across 211 runs" tells an operator at a glance that they are holding the reskin
experiment and not the patched client.

FOUR WAYS THE NEW WRITE PATH FAILED OPEN, closed 2026-08-19 by an adversarial
read of the change above, and every one of them was MEASURED against this file
rather than reasoned about. Appending a digest set stopped the gate refusing the
client we launch; it also made "register" a verb the gate honours, and each of
these was a way to say it about the wrong bytes.

  1. NO PRISTINE IMAGE ON DISK WAS A SKIPPED GUARD, NOT A REFUSAL. When
     `vault/client/<stamp>/Gw.exe` is absent `diff_against_pristine` answers
     `(None, None, why)`, and the sanity bound read `if nruns is not None and
     nruns > MAX_PATCH_RUNS and strict` -- so the whole check evaporated in
     exactly the configuration where nothing else can tell a patch from a
     stranger of the same length. MEASURED: 10,483,904 bytes of `os.urandom`
     registered under `strict=True`, and `assert_build` then called them
     `patched`. Under `strict` the absence is now a REFUSAL that names the
     missing image and the two deliberate ways past it. It has to be, because
     `find()` documents "pristine not in the vault" as a SUPPORTED configuration
     and `make_run_dir.py` registers on every single run -- so this is a
     reachable state, not a hypothetical.
  2. ANOTHER BUILD'S PRISTINE COULD BE FILED AS OUR PATCHED COPY. The refusal
     compared `digest == b.pristine` for the SELECTED build only. MEASURED: the
     real pristine 38833 image registered under `build=38797` with
     `strict=False`, after which `assert_build(<that file>, 38797)` answered
     `patched`. The digest is now refused if it equals ANY known build's
     pristine, and that refusal has no `--force`: there is no legitimate reason
     to file ArenaNet's own image as something we made.
  3. A FAILED WRITE WAS STILL HONOURED BY THE GATE. `rows.append(...)` mutated
     the list held in the `_registry` cache BEFORE the write was attempted, and
     the `OSError` path returned `refused` without invalidating it. MEASURED:
     `action='refused'`, no file on disk, `accepted_patched` 3 -> 4, and
     `assert_build` answered `patched` for the rest of the process. The row is
     now built into a NEW list and the cache is dropped on the error path, so
     the docstring's "fails closed" is what the code does.
  4. THE PATCHER NAMED THE BUILD FROM A FILENAME. `make_run_dir.py` passed
     `build=tag`, where `tag` is a regex over the SOURCE EXE'S NAME, and an
     explicit `build` outranks both the source hash and inference here. 38797
     and 38833 are the same length, so size cannot catch a mis-named source and
     the only guard that could is the one item 1 describes. It now infers from
     the bytes and treats the filename as a CROSS-CHECK that must agree.

REGISTRY ROWS ARE VALIDATED ON READ for the same reason: this is hand-editable
JSON in a vault a dozen worktrees share, and a row is evidence the gate acts on.
A truncated digest, or a row whose `build` and `stamp` name two different builds
-- which `accepted_patched` matches on EITHER, so one such row vouches under BOTH
-- is dropped and COUNTED in `why`, never silently honoured. See `row_problem`.

WHAT "PRISTINE" MEANS HERE, and it is not what the word suggests. ArenaNet
publishes no hash for `Gw.exe`. Every `pristine` digest below is the sha256 of
OUR OWN SNAPSHOT of the owner's install, taken by `snapshot_client.py`, which
re-hashes its copy and records `verified_against_source: true` in
`vault/client/<stamp>/MANIFEST.json`. That is a claim about our copying being
faithful, NOT a vendor check that the install was unmodified -- true equally of
the pin and of 38833, so it is stated once, in `pristine_via`, and `assert_build`
prints it rather than letting the word carry it.
"""

import argparse
import collections
import hashlib
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vaultpath                                              # noqa: E402

Build = collections.namedtuple(
    "Build", "stamp number size pristine pristine_via patched")

# One whole-file digest we accept as a copy WE made of a build, and what it is.
# `how` is printed by `identify()` and by the refusal, so it has to say enough to
# tell two of our own configurations apart -- the loopback build and the
# live-capture build differ ONLY in the 127 bytes of Diffie-Hellman modulus, and
# which one you are holding decides which server it may be pointed at.
PatchedCopy = collections.namedtuple("PatchedCopy", "sha256 how")

# What `accepted_patched()` hands back: a digest, what it is, and WHO VOUCHES for
# it -- committed in this file, or written into the vault registry by the patcher
# on this machine and not yet committed. The distinction is printed rather than
# flattened, because "the vault says so" and "the repository says so" are
# different amounts of evidence and the second is the auditable one.
Accepted = collections.namedtuple("Accepted", "sha256 how source")

# Said once, because it is true of every row and the word does not carry it.
VIA_SNAPSHOT = ("our own snapshot of the owner's install -- snapshot_client.py, "
                "MANIFEST.json verified_against_source. ArenaNet publishes no "
                "hash, so this is a claim about our COPY being faithful, not a "
                "vendor check that the install was unmodified")

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
#
# 38833 added 2026-08-14, the day it shipped. It is the FIRST build this project
# received while the cross-build tooling existed, so it is the first
# out-of-sample test of it -- `studies/crossbuild/FINDINGS.md` §7.
#
# THE PATCHED DIGESTS BELOW WERE MEASURED 2026-08-19 by hashing every `Gw.exe`
# in the vault and byte-diffing each against the pristine image OF ITS OWN
# STAMP. The byte/run counts in each `how` are that diff, and they are the
# evidence for calling a digest ours: our patcher writes four kinds of site
# (mutex guard + mutex name, updater kill switch, DH struct, key-tap) and lands
# in 6-9 runs. For scale, `vault/run/reskin-roster/Gw.exe` -- a real experiment
# copy of the same build -- is 682 bytes in 211 runs, and the OTHER build at the
# same length is 2,613,239 bytes in 152,735 runs.
#
# THAT LAST FIGURE READ 2,613,791 / 152,944 UNTIL 2026-08-19 EVENING, and the
# correction is small but it is the kind this module exists to make. 152,944 is
# `run/reskin-roster/Gw.exe` measured against 38833's pristine -- an outlier copy
# against the wrong build -- while the sentence claims a property of the two
# BUILDS. Pristine against pristine is 2,613,239 bytes in 152,735 runs, which is
# what the sentence now says and what `test_pinned.py` §4 re-measures. Every
# cross-build pair in the vault, patched copies included, lands in
# 152,735-152,944 runs (n=9), so nothing that rests on the figure moves: the
# separation from our 6-9 runs is four orders of magnitude either way.
BUILDS = (
    Build(stamp="2026-04-30_b174de1f2d8d", number=38519, size=10_404_032,
          pristine="b174de1f2d8dd4b5239e22714a96478af94ab5ad6b7bf308120562d5b49633a1",
          pristine_via=VIA_SNAPSHOT,
          # Nothing was ever patched from this build; the vault holds the
          # pristine snapshot alone. An empty tuple, not None: "we hold no
          # patched copy" and "this field was never filled in" are different
          # statements and only one of them is true here.
          patched=()),
    Build(stamp="2026-07-29_221c13772c7a", number=38797, size=10_483_904,
          pristine="221c13772c7a4fd1f3efd6769694614ed608909706d60a9d2b7190ba10119a75",
          pristine_via=VIA_SNAPSHOT,
          patched=(
              PatchedCopy(
                  "104c938b6f081c5a099ec040a82608875dadf16bdd1278f652cc59c3735aa521",
                  "loopback build -- OUR DH, updater off, multi-instance, key-tap. "
                  "187 B in 9 runs vs pristine. This is what the CURRENT patcher "
                  "writes, and it is the copy at vault/run/<stamp>/ that we launch "
                  "and that movetap.py gates; the gate refused it until 2026-08-19"),
              PatchedCopy(
                  "fa9563f1851014e80117195a1b66850c913433c4aba584ec6309b97e46bbf7e6",
                  "loopback build WITHOUT the key-tap -- the pre-key-tap patcher. "
                  "144 B in 6 runs. The copies at vault/run/<stamp>-c2/ and "
                  "-probe/. This was the module's ONLY `patched` hash until "
                  "2026-08-19, which is how the gate came to be inverted"),
              PatchedCopy(
                  "f0c042280a7419c37321a4bffb07ec6415685d75df46480c0877cefe7255eace",
                  "LIVE-CAPTURE build -- ArenaNet's DH left in place, updater off, "
                  "multi-instance, key-tap. 57 B in 7 runs. vault/run-live/<stamp>/ "
                  "and vault/client-patched-live/. Same build and same offsets, so "
                  "the static tools may read it; where it may be POINTED is decided "
                  "by dhbuild/cage from the DH struct and never from here"),
          )),
    Build(stamp="2026-08-13_64fae3b1369b", number=38833, size=10_483_904,
          pristine="64fae3b1369b9e2f6a6f0c315a95941f7e8db6b3412b9324418a293b614a13c6",
          pristine_via=VIA_SNAPSHOT,
          patched=(
              PatchedCopy(
                  "e06ada3bbf93e29a917be2d3bc339a4de141ef8fbc2e9bc80316152dfb8b59ab",
                  "loopback build -- OUR DH, updater off, multi-instance, no "
                  "key-tap. 145 B in 6 runs vs pristine. vault/run/<stamp>/ and "
                  "vault/client-patched/. Until 2026-08-19 this build had no "
                  "patched digest at all, so the newest client was unrepresentable"),
              PatchedCopy(
                  "7237b62054e80df74a03737bc3d62c756627114618e7c127d0ad8085a0653f57",
                  "LIVE-CAPTURE build -- stock DH, updater off, multi-instance, "
                  "key-tap. 57 B in 7 runs. vault/run-live/<stamp>/ and "
                  "vault/client-patched-live/"),
          )),
    # ArenaNet updated mid-run 2026-08-20; the skills arc rebuilt on 38849 and
    # closed the build gap (identical ghost behaviour, studies/skills 32.7,
    # commit d21ac05), but the pinned row lagged, so test_handshake's build-vs-
    # keyfile check reddened -- 38849 exe against a keyfile no BUILDS row named.
    # Snapshotted here 2026-08-22 (snapshot_client.py, MANIFEST verified byte-
    # identical). The PIN stays 38797 (below); this row only lets the newest
    # patched client be recognised rather than rejected.
    Build(stamp="2026-08-20_21511009c460", number=38849, size=10_483_904,
          pristine="21511009c460a2a9d9ddb84a63c1f0d0dba0e5fb6e120b550633ed4fdf15ac56",
          pristine_via=VIA_SNAPSHOT,
          patched=(
              PatchedCopy(
                  "4cc5bc989aeff8d42e13bad323b899e41a6c3b937edb7107a1cfd7fbd7c23d67",
                  "loopback build -- OUR DH, updater off, multi-instance, key-tap. "
                  "145 B vs pristine, dhbuild classifies `ours`. vault/run/<stamp>/ "
                  "and vault/client-patched/; this is the copy test_handshake "
                  "selects as the newest server-keyed client"),
              PatchedCopy(
                  "2ff730c7de42052a5f8971e3a8b89d9a7b3d49d39eae1e9fc52f1faccc185c98",
                  "LIVE-CAPTURE build -- stock DH, updater off, multi-instance, "
                  "key-tap. 57 B vs pristine, dhbuild classifies `stock`. "
                  "vault/run-live/<stamp>/ and vault/client-patched-live/"),
          )),
)

# THE PIN DOES NOT FOLLOW THE NEWEST BUILD, and this line used to read
# `BUILDS[-1]`, which would have moved it silently on 2026-08-14.
#
# Everything below defaults to the pin, so a caller that does not care which
# build it reads keeps reading the one every address in `studies/` was measured
# against -- and that is still 38797. Moving the pin is not a registration step;
# it is a re-measurement arc, because `genericvalue.py` REFUSES to read 38833
# (its int-main switch at 0x008129CC is restructured) and `avevents.py`'s
# property map depends on it. Repointing the default would turn that honest
# refusal into a wall of red in tests whose subject is not the pin at all.
#
# 38833 is the FIRST build where size is not a discriminator: it is byte-for-byte
# the same LENGTH as 38797, 10,483,904. `identify()` already loops over every
# same-size candidate rather than assuming one, so this is safe -- but a size
# check written anywhere else is now a bug, and `pinned.py`:54's "two copies of
# 38797 at the same size" caution now has a third file in it.
# (Spelled as a lookup rather than `select(38797)` because `select()` is defined
# below this line; a NameError at import time would take every tool with it.)
PINNED, = [b for b in BUILDS if b.number == 38797]

# Named individually because callers spell them that way and have since before
# `BUILDS` existed. They are the pinned row and nothing else.
BUILD = PINNED.number
SIZE = PINNED.size
STAMP = PINNED.stamp
PRISTINE_SHA256 = PINNED.pristine
# PLURAL since 2026-08-19, and the rename is the point rather than a tidy-up:
# `PATCHED_SHA256` named one hash, which is the assumption that went stale. A
# caller wanting the live answer -- committed digests plus whatever the patcher
# has registered on this machine -- wants `accepted_patched()`, not this.
PATCHED_SHA256S = tuple(p.sha256 for p in PINNED.patched)

# The `.text` bytes our patch changes ON THE PIN, as virtual addresses. MEASURED
# by diffing the vault's patched copies against the pristine image and mapping
# each run through the PE section table (`gwpe.PE.off_to_rva`), 2026-08-19.
# Listed so that a study pinning an address can be checked against them --
# `patches_touch()` does exactly that. No address in studies/skillcast,
# studies/agentprops or studies/enemy lands in any of these ranges.
#
# THE LAST TWO WERE MISSING UNTIL 2026-08-19 and that is the same defect as the
# stale patched hash, seen from the other side: the key-tap has written .text
# since it was added, `patches_touch()` said no for both of its sites, and this
# comment still opened "the nine .text bytes". Sites are per build -- the updater
# patch is at file 0x4332CA on 38797 and 0x43335A on 38833 -- and these are the
# pin's. The pre-key-tap copies (`fa9563f1...`) carry only the first two.
PATCHED_TEXT = [
    (0x0047E65F, 0x0047E665, "the build/version check"),
    (0x00833ECA, 0x00833ECC, "a `sete al` result, forced"),
    (0x004514E2, 0x00451507, "the key-tap CAVE -- 38 bytes of ours in dead space"),
    (0x007DC0CE, 0x007DC0D3, "the key-tap JUMP, 6 bytes over the master_secret site"),
]
# .rdata, for completeness: 0x0093F7AB a `-Window` flag string, and
# 0x00A910E1..0x00A9115F the Diffie-Hellman modulus RUNBOOK.md says rotates
# with every client build. The key-tap's SLOT is in .data and is zero on disk
# both before and after, so it is not a differing byte and not listed.

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


# ------------------------------------------------------- the patch registry --
# Digests the PATCHER recorded on this machine, beside the binaries they
# describe. In the VAULT rather than in the repository, and the reason is the
# house's own worktree rule (`CLAUDE.md`, "Working in this repo"): a dozen
# worktrees share ONE vault, so a digest registered from any tree is visible from
# every tree at once, while a file committed in one tree is invisible in the
# others until it is merged -- which would rebuild the staleness this registry
# exists to remove. The committed half is `Build.patched`: a digest earns its
# place there once it is worth auditing, and `main()` prints which registered
# digests have not made that trip yet so the drift is visible rather than silent.
REGISTRY = ("client-patched", "patched_digests.json")

# Refuse to register something that looks nothing like one of our patched
# clients. MEASURED 2026-08-19 over every patched copy in the vault: our four
# patch kinds land in 6 to 9 differing runs. `vault/run/reskin-roster/Gw.exe`, a
# real experiment copy of the pin, is 211 runs; the other build at the same
# length is 152,735 (pristine against pristine; 152,735-152,944 over the vault's
# nine cross-build pairs). 32 is ~3.5x the largest real patch and nowhere near either
# of those, and it is a SANITY bound on the registering step, not the gate --
# `register_patched(..., strict=False)` and `--force` pass anything the operator
# is willing to name.
MAX_PATCH_RUNS = 32

_registry = None                        # (rows, why), read once per process

HEXDIGITS = set("0123456789abcdef")


def registry_path():
    return vaultpath.vault_path(*REGISTRY)


def known_build(spec):
    """The Build a registry row's `build`/`stamp` field names, or None. Never raises.

    `select()` with a shrug, for reading untrusted rows: the same lookup, but an
    unknown spec is an answer rather than a `SystemExit` taken by twelve tools.
    """
    for b in BUILDS:
        if spec == b.number or spec == b.stamp:
            return b
    return None


def row_problem(r):
    """Why a registry row cannot vouch for anything, or None if it is well formed.

    CHEAP, AND ON THE READ PATH, because this is hand-editable JSON living in a
    vault a dozen worktrees share and a row is EVIDENCE: `accepted_patched` hands
    it to `identify()`, and `identify()` is the gate. The shape check was
    `isinstance(r, dict) and r.get("sha256")`, which accepts a truncated digest
    (it can never match, but it is counted and printed as though it vouched for
    something) and, worse, accepts a row whose `build` and `stamp` name TWO
    DIFFERENT builds -- `accepted_patched` matches a row on stamp OR number, so
    one such row vouches under both. A half-written or hand-edited row is dropped
    here and COUNTED in `why`, rather than quietly honoured.
    """
    if not isinstance(r, dict):
        return f"not an object ({type(r).__name__})"
    d = r.get("sha256")
    if not isinstance(d, str) or len(d) != 64 or set(d.lower()) - HEXDIGITS:
        return f"sha256 is not 64 hex characters: {d!r}"
    by_number, by_stamp = known_build(r.get("build")), known_build(r.get("stamp"))
    if by_number is None or by_stamp is None:
        return (f"names no build in pinned.BUILDS (build={r.get('build')!r}, "
                f"stamp={r.get('stamp')!r}) -- both are required and both must "
                f"resolve, or the row cannot be filed under any build")
    if by_number is not by_stamp:
        return (f"build {r.get('build')!r} and stamp {r.get('stamp')!r} are "
                f"DIFFERENT builds, so the row would vouch under both")
    return None


def load_registry(force=False):
    """(rows, why) from the vault registry. NEVER raises -- twelve tools import this.

    A missing registry is the ordinary case (nothing patched on this machine, or
    no vault in reach) and is not an error. An UNREADABLE one yields no rows,
    which fails closed, and says so in `why` -- which `main()` prints and every
    refusal quotes, because a corrupt registry silently behaving like an empty
    one is how a gate stops gating without anybody noticing.

    Rows that `row_problem` rejects are dropped, counted and named in `why` for
    the same reason. They are also not written back: a row the reader will not
    honour has no business sitting in the file looking like evidence.
    """
    global _registry
    if _registry is not None and not force:
        return _registry
    p = registry_path()
    try:
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
        rows, bad = [], []
        for r in doc.get("rows", []):
            trouble = row_problem(r)
            if trouble:
                bad.append(trouble)
                continue
            r = dict(r)
            # hashlib writes lowercase; a hand-typed uppercase digest would pass
            # every check here and then match nothing at all.
            r["sha256"] = r["sha256"].lower()
            rows.append(r)
        why = f"{len(rows)} row(s) from {p}"
        if bad:
            why += (f"; {len(bad)} row(s) REJECTED as malformed and dropped -- "
                    + "; ".join(bad[:3]) + ("; ..." if len(bad) > 3 else ""))
    except FileNotFoundError:
        rows, why = [], (f"no registry at {p} -- nothing has been patched on this "
                         f"machine since the patcher started recording, or the "
                         f"vault is elsewhere")
    except (OSError, ValueError, TypeError) as exc:
        # TypeError because `rows` need not be a list: `{"rows": 3}` is valid
        # JSON, and iterating it is a TypeError that would otherwise escape a
        # function twelve tools import and whose contract is "never raises".
        rows, why = [], f"UNREADABLE registry at {p}: {exc}"
    _registry = (rows, why)
    return _registry


def accepted_patched(build=None):
    """Every digest accepted as OUR patched copy of `build`: committed, then vault.

    Committed first so the auditable answer is the one a reader sees first, and
    de-duplicated on sha256 so a digest that has been promoted into `BUILDS`
    reports as committed rather than twice.
    """
    b = select(build)
    out, seen = [], set()
    for pc in b.patched:
        out.append(Accepted(pc.sha256, pc.how, "committed in pinned.BUILDS"))
        seen.add(pc.sha256)
    rows, _why = load_registry()
    for r in rows:
        if r["sha256"] in seen:
            continue
        if r.get("stamp") != b.stamp and r.get("build") != b.number:
            continue
        seen.add(r["sha256"])
        out.append(Accepted(
            r["sha256"], r.get("how") or "no description recorded",
            f"vault registry -- {r.get('tool', 'unknown tool')} "
            f"{r.get('utc', 'undated')}, NOT yet committed to pinned.BUILDS"))
    return out


def diff_against_pristine(path, build=None):
    """(differing bytes, differing runs, why) vs the vaulted pristine image.

    (None, None, why) when there is nothing to compare against. This is EVIDENCE,
    never the gate: `identify()` decides on sha256 alone, because an allowlist of
    sites accepts any bytes at those sites and the most consequential bytes in
    this file -- the Diffie-Hellman modulus -- sit at one of them. What a run
    count is good for is telling an operator apart from a wall: "6 runs" is our
    patch we forgot to register, "211" is the reskin experiment, "152,735" is the
    other build at the same length.
    """
    b = select(build)
    ref = vaultpath.vault_path("client", b.stamp, "Gw.exe")
    if not os.path.isfile(ref):
        return None, None, f"no pristine image on disk at {ref}"
    nbytes = nruns = 0
    in_run = False
    try:
        with open(ref, "rb") as fa, open(path, "rb") as fb:
            while True:
                x, y = fa.read(1 << 16), fb.read(1 << 16)
                if not x and not y:
                    break
                if len(x) != len(y):
                    return None, None, "the files are different lengths"
                if x == y:
                    in_run = False
                    continue
                for p, q in zip(x, y):
                    if p != q:
                        nbytes += 1
                        if not in_run:
                            nruns += 1
                            in_run = True
                    else:
                        in_run = False
    except OSError as exc:
        return None, None, f"could not read: {exc}"
    return nbytes, nruns, f"vs vault/client/{b.stamp}/Gw.exe"


def infer_build(path):
    """(Build, why) or (None, why): which build a patched copy is a patch OF.

    ASKED RATHER THAN ASSUMED, because the obvious default is wrong in the one
    case that matters. `register_patched` used to fall through to `select(None)`
    -- the pin -- and 38833 ships at exactly 38797's length, so a hand
    registration of a patched 38833 would have been filed under 38797 without a
    word. The discriminant needs no tuning: a patch of the right build is 6-9
    differing runs and the same file against the WRONG build of the same length
    is 152,735-152,944 (n=9 cross-build pairs in the vault), so `MAX_PATCH_RUNS`
    separates them by four orders of magnitude.
    """
    if not os.path.isfile(path):
        return None, "no such file"
    size = os.path.getsize(path)
    sized = [b for b in BUILDS if b.size == size]
    if not sized:
        have = ", ".join(f"{b.size:,} ({name_of(b)})" for b in BUILDS)
        return None, f"{size:,} bytes is no build we hold -- have {have}"
    scored = []
    for b in sized:
        nbytes, nruns, _why = diff_against_pristine(path, b)
        if nruns is not None:
            scored.append((nruns, nbytes, b))
    if not scored:
        if len(sized) == 1:
            return sized[0], (f"the only build at {size:,} bytes; no pristine image "
                              f"on disk, so this is by SIZE alone")
        which = " and ".join(name_of(b) for b in sized)
        return None, (f"{which} are both {size:,} bytes and neither pristine image "
                      f"is on disk, so there is nothing to tell them apart. Pass "
                      f"--build.")
    scored.sort(key=lambda r: r[0])
    near = [r for r in scored if r[0] <= MAX_PATCH_RUNS]
    shape = ", ".join(f"{name_of(b)}: {n:,} runs" for n, _nb, b in scored)
    if len(near) == 1:
        return near[0][2], f"closest to {name_of(near[0][2])} ({shape})"
    if not near:
        return None, (f"not within {MAX_PATCH_RUNS} differing runs of any pristine "
                      f"image ({shape}) -- pass --build to say what it is")
    return None, f"within the patch bound of more than one build ({shape})"


def register_patched(path, build=None, source_sha256=None, how="", tool="",
                     strict=True):
    """Record `path`'s sha256 as a copy of `build` that WE made. (digest, action, detail).

    `action` is one of `added` / `already` / `refused` / `no-vault`, and this
    function raises nothing: it is called from the tail of a patcher run that has
    already written and verified a binary, and refusing to finish that run over a
    bookkeeping file would be the wrong trade. The caller PRINTS the action --
    loudly on anything but `added`/`already` -- because an unregistered patched
    copy is not dangerous, it is merely refused later, and `--register` recovers.

    WHICH BUILD, in order: an explicit `build`; else `source_sha256`, the hash of
    the file the patcher READ, which anchors the row to a pristine digest we hold
    rather than to whatever the directory was called; else `infer_build`. Never a
    default -- 38797 and 38833 are the same length, so falling through to the pin
    would have filed a patched 38833 under 38797 in silence. A source hash we do
    not recognise is refused rather than guessed at: that is a new ArenaNet
    build, and it needs a snapshot and a `BUILDS` row first.

    WHAT IS REFUSED, and which refusals `strict=False` may not argue with. Items
    1-3 of the module docstring's "four ways the new write path failed open" are
    all here:

      * a digest equal to ANY known build's PRISTINE image. No override, not
        even `--force`: filing ArenaNet's own file as one we made is the one
        registration that has no legitimate reading, and checking only the
        SELECTED build's pristine let the real 38833 image be filed as our
        patched 38797.
      * a file with no pristine image to compare against, under `strict`. That
        comparison is the only instrument that separates our 6-9 run patch from
        a stranger of the same length, and when it was merely skipped, 10 MB of
        random bytes registered and passed the gate. `strict=False`/`--force`
        is the deliberate way past, and it wants a `how`.
      * a file further than `MAX_PATCH_RUNS` from pristine, under `strict` --
        the original sanity bound, unchanged.

    Nothing is written unless all of them pass, and a write that FAILS leaves the
    process-wide cache exactly as it found it: `action='refused'` used to be
    honoured by the gate for the rest of the run, because the row had already
    been appended to the cached list.
    """
    global _registry
    if build is not None:
        try:
            b = select(build)
        except SystemExit as exc:
            return None, "refused", str(exc)
    elif source_sha256:
        match = [x for x in BUILDS if x.pristine == source_sha256]
        if not match:
            return None, "refused", (
                f"the source image sha256 {source_sha256[:16]}... is no build in "
                f"pinned.BUILDS, so there is no row to file a patched copy under. "
                f"Snapshot it (toolkit/snapshot_client.py) and add the row first.")
        b = match[0]
    else:
        b, iwhy = infer_build(path)
        if b is None:
            return None, "refused", f"cannot tell which build this is: {iwhy}"

    if not os.path.isfile(path):
        return None, "refused", f"no such file: {path}"
    size = os.path.getsize(path)
    if size != b.size:
        return None, "refused", (
            f"{size:,} bytes, but build {name_of(b)} is {b.size:,}")
    digest = sha256(path)
    # ANY build's pristine, not just the selected one's, and no --force past it.
    # MEASURED 2026-08-19: with only `digest == b.pristine` checked, the real
    # pristine 38833 image registered under `build=38797` with `strict=False`,
    # and `assert_build(<it>, 38797)` then answered "patched" -- the gate
    # vouching for ArenaNet's own shipped binary as a copy we made. The two
    # builds are the same LENGTH, so nothing else here would have caught it.
    shipped = [x for x in BUILDS if x.pristine == digest]
    if shipped:
        elsewhere = ("" if shipped[0] is b else
                     f" It was offered as a patched copy of {name_of(b)}, which "
                     f"is a different build of the same length.")
        return digest, "refused", (
            f"that is the PRISTINE image of build {name_of(shipped[0])}, byte "
            f"for byte -- ArenaNet's file, not a copy we made.{elsewhere} "
            f"Registering it would make 'pristine' and 'our patched copy' the "
            f"same answer, and there is no --force for this one.")

    nbytes, nruns, dwhy = diff_against_pristine(path, b)
    # THE ABSENCE IS THE REFUSAL, since 2026-08-19. This used to fall through to
    # `nruns is not None`, so with no pristine image on disk the sanity bound did
    # not run at all -- and 10,483,904 bytes of os.urandom registered under
    # strict=True and passed `assert_build`. `find()` names "pristine not in the
    # vault" as a supported configuration and `make_run_dir.py` registers on
    # every run, so this state is reachable rather than hypothetical: it has to
    # refuse loudly and say how to proceed on purpose.
    if nbytes is None and strict:
        sharing = [x for x in BUILDS if x.size == b.size]
        crowd = ("" if len(sharing) < 2 else
                 f" -- and {b.size:,} bytes is "
                 f"{' and '.join(name_of(x) for x in sharing)}, so the size says "
                 f"nothing either")
        return digest, "refused", (
            f"there is nothing to compare it against: {dwhy}. The pristine image "
            f"is the ONLY thing that separates our 6-9 run patch from a stranger "
            f"of the same length{crowd}. With it absent this registration would "
            f"be taking the file's word for what it is. Restore "
            f"vault/client/{b.stamp}/Gw.exe (see toolkit/snapshot_client.py), "
            f"or -- deliberately -- pass strict=False (--force) and say in `how` "
            f"what this file is.")
    if nbytes == 0:
        return digest, "refused", f"identical to the pristine image ({dwhy})"
    if nruns is not None and nruns > MAX_PATCH_RUNS and strict:
        return digest, "refused", (
            f"{nbytes:,} differing bytes in {nruns:,} runs {dwhy} -- our patcher "
            f"lands in 6-9 runs and the bound is {MAX_PATCH_RUNS}. This looks "
            f"like a different image rather than a patched one. Pass "
            f"strict=False (or --force) to register it anyway, and say in `how` "
            f"what it is.")
    structural = (dwhy if nbytes is None
                  else f"{nbytes:,} differing bytes in {nruns:,} runs {dwhy}")

    for acc in accepted_patched(b):
        if acc.sha256 == digest:
            return digest, "already", f"{acc.source}: {acc.how}"

    root = vaultpath.vault_root()
    if not os.path.isdir(root):
        return digest, "no-vault", (
            f"the vault is not at {root} ({vaultpath.vault_why()}), so there is "
            f"nowhere to record this. Set RURIK_VAULT, then re-register with "
            f"  python toolkit/clientscan/pinned.py --register {path}")

    # A NEW LIST, never `rows.append(...)`. `load_registry` caches the list it
    # returns in `_registry`, so appending to it published the row to every
    # caller in this process BEFORE the write was attempted -- and the OSError
    # path below returned "refused" without taking it back. MEASURED
    # 2026-08-19: action='refused', no file on disk, `accepted_patched` 3 -> 4,
    # `assert_build` "patched". A module whose docstring says it fails closed
    # was failing open on the one path where the operator had been told no.
    cached, _why = load_registry(force=True)
    rows = list(cached) + [{
        "sha256": digest,
        "build": b.number,
        "stamp": b.stamp,
        "how": how or "no description recorded",
        "tool": tool or "pinned.register_patched",
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "path": os.path.abspath(path),
        "structural": structural,
    }]
    target = registry_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    doc = {
        "note": ("Whole-file sha256 of every patched client written on this "
                 "machine, appended by the patcher. Read by "
                 "toolkit/clientscan/pinned.py. Measured facts only -- a hash, a "
                 "build and a path; no ArenaNet bytes."),
        "rows": rows,
    }
    # Written through a temp file in the same directory and renamed: a registry
    # truncated by an interrupted write reads as UNREADABLE, which fails closed
    # and refuses every patched copy on the machine.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        os.replace(tmp, target)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        # Belt and braces with the `list(cached)` above: the cache is dropped so
        # the next reader re-reads what is actually ON DISK, which is the only
        # thing that vouched for anything. A refusal the gate then honours is
        # worse than a crash, because it prints the word "refused".
        _registry = None
        return digest, "refused", f"could not write {target}: {exc}"
    _registry = None
    return digest, "added", f"{target} now holds {len(rows)} row(s); {structural}"


def identify_build(path, build=None):
    """('pristine' | 'patched' | 'unknown', the Build matched or None, detail).

    With no `build`, EVERY build in `BUILDS` is considered, so the older vaulted
    client identifies as itself rather than as "not 38797's size". Pass a number
    or a stamp to ask about one build specifically -- which is what `find()`
    does, because there the question is "is this the build I asked for", and a
    file that is honestly some OTHER build is still the wrong answer.

    RETURNS THE MATCHED ROW, and that is why this function exists rather than
    just `identify()`. Until 2026-08-17 the only answer available here was the
    STRING "pristine", which names a category and not a build -- so a caller
    that had identified a file and wanted to print or record which build it was
    had nowhere to get the number and reached for `BUILD`, the constant. Four
    of them did: `framebus.py` labelled every image "the pinned build 38797",
    and `worldmap.py`, `consttable.py` and `heroes_table.py` stamped 38797 onto
    extracted content rows. All four were reading whatever `--exe` named.
    `worldmap.image_build` is the one worth reading, because its own docstring
    says "Never a constant" and it emitted `build: 38797` beside
    `image: "pristine: build 38833"` -- the contradiction was already in the
    row and nothing looked at it. See `studies/crossbuild/FINDINGS.md` §9,
    whose §9.5 is the part worth reading: five test sections covered these four
    tools and every one was green, because every check ran against the pin --
    where the constant is correct.
    """
    if not os.path.isfile(path):
        return "unknown", None, "no such file"
    size = os.path.getsize(path)
    candidates = [select(build)] if build is not None else list(BUILDS)
    sized = [b for b in candidates if b.size == size]
    if not sized:
        want = ", ".join(f"{b.size:,} (build {name_of(b)})" for b in candidates)
        return "unknown", None, f"{size:,} bytes, which is no build we hold -- have {want}"
    digest = sha256(path)
    for b in sized:
        if digest == b.pristine:
            return "pristine", b, (f"build {name_of(b)}, PRISTINE -- our snapshot "
                                   f"of the shipped client, unmodified by us")
        # A SET since 2026-08-19. One hash of one patched file went stale the day
        # the patcher gained the key-tap, and the gate then refused the client we
        # launch while accepting two superseded copies. See the module docstring.
        for acc in accepted_patched(b):
            if digest == acc.sha256:
                return "patched", b, (f"build {name_of(b)}, OUR patched copy -- "
                                      f"{acc.how} [{acc.source}]")
    # NAMES EVERY same-size candidate, not `sized[0]`. This said "the size of
    # build {sized[0]}" until 2026-08-14, which was unambiguous only while size
    # was a discriminator -- and 38833 ships at 10,483,904 bytes, exactly 38797's
    # length (see the BUILDS comment above). MEASURED that day: the patched 38833
    # run directory identified as "the size of build 38797 but sha256 e06ada3b...",
    # pointing a reader diagnosing it at the wrong build entirely. The loop above
    # already considers every candidate; only the refusal message did not.
    which = " or ".join(name_of(b) for b in sized)
    plural = "s" if len(sized) > 1 else ""
    return "unknown", None, (f"the size of build{plural} {which} but sha256 "
                             f"{digest[:16]}..., which is no copy we hold of "
                             f"{'either' if len(sized) > 1 else 'it'}")


def identify(path, build=None):
    """('pristine' | 'patched' | 'unknown', detail). `identify_build` without the row.

    Kept because a dozen callers only ever wanted the category and the sentence.
    A caller that wants the BUILD must use `identify_build` -- or better,
    `buildid.of_image`, which also reads a build we have never seen.
    """
    kind, _b, detail = identify_build(path, build)
    return kind, detail


def find(build=None, *, verify=True, allow_live=False):
    """(path, why). Pristine first, then our patched copy. VERIFIED by default.

    Never silently either -- `why` is meant to be printed. A tool that says
    which file it read lets a surprising result be diagnosed in one line
    instead of being argued about.

    `verify` hashes what it is about to return and REFUSES a file whose bytes
    are not the pristine image or one of the patched digests we accept for that
    build (`accepted_patched`). This used to be the one thing `find()` did not
    do, and `identify()` sat here reachable only from `main()` and two tests.

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
                f"  explicit --exe if you meant to read this file.\n"
                f"  If it IS a copy we patched but never registered:\n"
                f"      python toolkit/clientscan/pinned.py --register {p}")
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

    # SAYS WHAT IS AND IS NOT VERIFIED, since 2026-08-19. The old message named
    # the file and stopped, so the only fact an operator could act on was
    # `--any-build` -- and on the day the patcher changed, this refusal was
    # firing on the correct, freshly patched client. Two things make it
    # actionable instead: the accepted digests, with who vouches for each, and
    # the structural distance from the pristine image, which separates "ours,
    # unregistered" from "not this build at all" at a glance.
    acc = accepted_patched(b)
    _rows, reg_why = load_registry()
    committed = sum(1 for a in acc if a.source.startswith("committed"))
    nbytes, nruns, dwhy = diff_against_pristine(path, b)
    if nbytes is None:
        shape = f"  could not compare it against the pristine image: {dwhy}"
    else:
        shape = (f"  it differs from the pristine image in {nbytes:,} bytes across\n"
                 f"  {nruns:,} runs ({dwhy}). Ours land in 6-9 runs; the reskin\n"
                 f"  experiment copy is 211, and the other build of the same length\n"
                 f"  is 152,735-152,944.")
    msg = (f"REFUSING {why}: {path}\n"
           f"  is not a copy of build {name_of(b)} that we recorded --\n"
           f"      {detail}\n"
           f"  WHAT WE VERIFY, and what we do not:\n"
           f"    pristine   ONE sha256, {b.pristine[:16]}..., and it is\n"
           f"               {b.pristine_via}\n"
           f"    patched    {len(acc)} accepted digest(s): {committed} committed in\n"
           f"               pinned.BUILDS, {len(acc) - committed} from the vault "
           f"registry\n"
           f"               ({reg_why})\n"
           f"{shape}\n"
           f"  The offsets this tool uses were MEASURED on that build. Against\n"
           f"  another one they do not return a wrong number, they read whatever\n"
           f"  else is mapped at that address and print it as data.\n"
           f"  If this IS a copy we made -- the patcher registers its own output\n"
           f"  now, so this means it predates that or was assembled by hand:\n"
           f"      python toolkit/clientscan/pinned.py --register {path}\n"
           f"  Otherwise re-derive them, or pass --any-build if you accept that.")
    if allow_any:
        return what
    raise WrongBuild(msg)


def patches_touch(va, span=1):
    """Do our patched .text bytes overlap [va, va+span)? The reason this list exists."""
    return [why for lo, hi, why in PATCHED_TEXT
            if not (va + span - 1 < lo or va > hi)]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="what is in the vault, and what it is",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--register", metavar="EXE",
                   help="record this file's sha256 as a patched copy WE made. The "
                        "patcher does this itself; use it for a copy that predates "
                        "that, or one assembled by hand.")
    ap.add_argument("--build", help="build number or vault stamp for --register "
                                    "(default: inferred from the file's size and "
                                    "its distance from each pristine image)")
    ap.add_argument("--how", default="", help="what this copy is, for the record")
    ap.add_argument("--force", action="store_true",
                   help="register even though the file is far from any pristine "
                        "image. Say what it is in --how.")
    a = ap.parse_args(argv)

    if a.register:
        return _register_cli(a)

    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})")
    rows, reg_why = load_registry()
    print(f"patch registry: {reg_why}")
    for b in BUILDS:
        pin = "  <- the pin" if b is PINNED else ""
        print(f"\nbuild {name_of(b)}, {b.size:,} bytes, stamp {b.stamp}{pin}")
        for kind in ("client", "run", "run-live"):
            p = vaultpath.vault_path(kind, b.stamp, "Gw.exe")
            what, detail = identify(p, build=b)
            print(f"  {kind + '/':10} {what:8} {detail}")
            print(f"             {p}")
        acc = accepted_patched(b)
        print(f"  accepted as OUR patched copy: {len(acc)}")
        for x in acc:
            print(f"    {x.sha256[:16]}...  {x.source}")
            print(f"      {x.how}")
        # NAMED, not summed. A digest the patcher recorded here but that nobody
        # has committed is the drift this registry can accumulate, and the whole
        # reason the previous design went stale was that its drift was invisible.
        loose = [x for x in acc if not x.source.startswith("committed")]
        if loose:
            print(f"  ** {len(loose)} digest(s) live only in the vault registry. "
                  f"Promote them into pinned.BUILDS to make them auditable.")
    what, detail = identify(LIVE_INSTALL)
    print(f"\n  {'live':10} {what:8} {detail}")
    print(f"             {LIVE_INSTALL}")
    path, why = find()
    print(f"\ndefault for static analysis: {path}\n  ({why})")
    print("\nour patch changes these bytes ON THE PIN; an address landing here is ours:")
    for lo, hi, w in PATCHED_TEXT:
        print(f"  0x{lo:08X}..0x{hi:08X}  {w}")
    return 0


def build_arg(spec):
    """argv is text, so a bare number typed on the command line means the NUMBER.

    `select()` refuses the STRING "38797" on purpose -- accepting it would make
    the registry's keys ambiguous, and `test_pinned.py` §1 pins that refusal. But
    argparse can only hand back text, so `--build 38797` would have been refused
    as an unknown build while naming 38797 in its own error. The coercion belongs
    at the argv boundary, which is here, and not in the lookup.
    """
    if isinstance(spec, str) and spec.isdigit():
        return int(spec)
    return spec


def _register_cli(a):
    """`--register`. Prints the verdict and returns an exit code -- 0 only if filed."""
    digest, action, detail = register_patched(
        a.register, build=build_arg(a.build), how=a.how or "registered by hand",
        tool="pinned.py --register", strict=not a.force)
    print(f"{a.register}\n  sha256 {digest}\n  {action.upper()}: {detail}")
    return 0 if action in ("added", "already") else 1


if __name__ == "__main__":
    sys.exit(main())
