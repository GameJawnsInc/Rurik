#!/usr/bin/env python3
"""Check the Cli/Srv source-tree finding, and the `-mock` closeout, against bytes.

    python toolkit/clientscan/test_srctree.py

The load-bearing claim in `studies/srvtree/FINDINGS.md` is a NEGATIVE one: no
server-side translation unit is linked into the shipped client. A negative result
is exactly the kind a broken instrument reports for free, and this one nearly
did -- the first version of the detector had a lone backslash in a pattern and
raised instead of matching, which from one step back looks identical to "no
hits". So section 1 runs the detector against a FABRICATED path list containing
server-side paths and requires it to catch every one. If section 1 goes red,
section 2's zeroes mean nothing and the test says so rather than passing.

The rest can each fail for a real reason:

  * Section 2 runs the census over BOTH vaulted builds, four months apart. A
    finding that holds on one image could be an artifact of that image; the same
    twelve Cli/Srv subsystems on two independently-patched builds is not.
  * Section 3 pins the two paths that DO contain "Srv" and requires both to sit
    under a client tree. Without this the negative result could be a filter that
    is simply too narrow to see anything.
  * Section 4 is the `-mock` closeout. `studies/handshake/PLAN.md` carried
    `-mock` as possibly "a developer mock mode ... extraordinarily valuable" for
    two revisions. It is a mock graphics device. The test pins the whole string
    set, so a future build that adds a real mock server goes red here -- which
    is the outcome we would most want to be told about.
  * Section 5 requires the shared trees to contain no `Cli` directory at all.
    That is what makes them shared rather than merely large.
"""

import os
import re
import sys
import time

START = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                                # noqa: E402
import pinned                                                # noqa: E402
import srctree as st                                         # noqa: E402
import vaultpath                                             # noqa: E402

SEP = st.SEP

# Both vaulted builds. The finding must hold on both, not just the pinned one.
#
# The STAMPS are no longer spelled here -- they come from `pinned.BUILDS`, which
# is the vault's build registry (`studies/crossbuild/PLAN.md` §5). This is the
# only cross-ArenaNet-build test in the tree, so a build added to the registry
# and missed here would leave the registry claiming a coverage nothing provides.
# The path COUNT stays here: it is a build-specific expectation, and a new build
# turning this red is the correct outcome rather than a defect.
EXPECT_PATHS = {
    "2026-04-30_b174de1f2d8d": 936,
    "2026-07-29_221c13772c7a": 937,
    # 38833, MEASURED 2026-08-14 by running this test's own `st.source_paths`
    # over the image: 937, zero server-side translation units, and the same two
    # client-side `Srv`-named files. The census is unchanged across the 15-day
    # patch, which is consistent with everything else measured about that gap
    # (studies/crossbuild/FINDINGS.md §7.2).
    "2026-08-13_64fae3b1369b": 937,
}
BUILDS = [(b.stamp, EXPECT_PATHS.get(b.stamp)) for b in pinned.BUILDS]

# The twelve subsystems whose client half shipped, so whose server half exists
# and is the missing work. MEASURED on both builds.
SPLIT_SUBSYSTEMS = {
    "Account", "Char", "Cinematic", "Comm", "Gadget", "Guild",
    "Item", "Main", "Mission", "Net", "Party", "Trade",
}

# The only two paths containing "Srv", both client-side objects for a server.
SRV_NAMED_CLIENT_PATHS = {
    st.PREFIX + SEP.join(["Gw", "Net", "Cli", "GcSrv.cpp"]),
    st.PREFIX + SEP.join(["Net", "FileCli", "FcSrv.cpp"]),
}

# Trees with no Cli/Srv split: both build targets compiled these.
SHARED = ["Base", "Engine", "Net", "Gw" + SEP + "Const"]

# Every string in the image containing "mock", as (encoding, text).
MOCK_STRINGS = {("ascii", "mockDevice"), ("utf16", "mock"), ("utf16", "MockDevice")}

# The floor counts a measured green run of 2026-08-14: 39 checks. That is 2 for the
# detector self-test in section 1, then 9 per vaulted build (5 census + 4 shared
# trees) across the THREE builds = 27, then 5 for the srctree/asserts containment in
# 3b, 4 for the assert-scan blind-spot disclosure in 3c, and 1 for the -mock
# closeout. Nothing here is optional: every fixture arrives through
# `vaultpath.require_dir`, which raises rather than yielding an empty scan, so a run
# that reaches the banner having done fewer than 39 checks has lost a section --
# most likely one of the per-build loops -- rather than found less data.
#
# It was 30 over two builds until 2026-08-14, when 38833 was registered; the
# per-build term is why registering a build moves this number by 9 rather than
# by 1, and re-deriving it here beats bumping the constant.
LEDGER = checks.Ledger("srctree", floor=39)
check = checks.adopt(LEDGER)


def load(name):
    p = vaultpath.require_dir("client", name, why="pinned client snapshot")
    with open(os.path.join(p, "Gw.exe"), "rb") as f:
        return f.read()


# --- 1. the detector can actually fire ---------------------------------------
print()
print("1. the server-side detector, against fabricated server-side paths")
FAKE = [
    st.PREFIX + SEP.join(["Gw", "Char", "Srv", "ChSrvApi.cpp"]),
    st.PREFIX + SEP.join(["Gw", "Item", "Srv", "ItSrvDrop.cpp"]),
    st.PREFIX + SEP.join(["Gw", "Main", "SrvMain.cpp"]),
    st.PREFIX + SEP.join(["Net", "GameSrv.cpp"]),
    st.PREFIX + SEP.join(["Gw", "Sim", "SimAgent.cpp"]),
    st.PREFIX + SEP.join(["Server", "Main.cpp"]),
]
caught = set()
for label, hit in st.srv_hits(FAKE):
    caught.update(hit)
missed = [p for p in FAKE if p not in caught]
check(not missed, "all %d fabricated server paths are caught" % len(FAKE),
      "missed: %s" % missed if missed else "the negative result below can fail")
# and it must not fire on the real client tree
clean = [st.PREFIX + SEP.join(["Gw", "Char", "Cli", "ChCliApi.cpp"]),
         st.PREFIX + SEP.join(["Engine", "Agent", "AgAgent.cpp"])]
false_pos = set()
for label, hit in st.srv_hits(clean):
    false_pos.update(hit)
check(not false_pos, "the detector does not fire on client-side paths",
      "false positives: %s" % sorted(false_pos) if false_pos else "")

# --- 2 & 3. the census, on both builds ---------------------------------------
for name, expect_paths in BUILDS:
    print()
    print("2. build %s" % name)
    if expect_paths is None:
        # A build reached `pinned.BUILDS` and nobody gave this test a number for
        # it. Failing beats skipping: the registry is what other tools consult
        # to answer "which builds do we cover", and an unmeasured build sitting
        # in it silently is the coverage gap this wiring exists to close.
        check(False, "build %s has no expected path count in EXPECT_PATHS" % name,
              "add one, measured from a real run -- never from a guess")
        continue
    blob = load(name)
    paths = st.source_paths(blob)
    check(len(paths) == expect_paths,
          "%d distinct P:%sCode source paths" % (len(paths), SEP),
          "expected %d" % expect_paths if len(paths) != expect_paths else "")

    total = sum(len(h) for _, h in st.srv_hits(paths))
    check(total == 0, "no server-side translation unit in the image",
          "found: %s" % [p for _, h in st.srv_hits(paths) for p in h] if total else
          "6 spellings checked, all empty")

    got = set(p for p in paths if "Srv" in p)
    check(got == SRV_NAMED_CLIENT_PATHS,
          "the only 'Srv' paths are the two client-side ones",
          "got %s" % sorted(got) if got != SRV_NAMED_CLIENT_PATHS else "")

    split = set(k for k, r in st.cli_split(paths).items() if r["cli"])
    check(split == SPLIT_SUBSYSTEMS,
          "%d subsystems ship a Cli half" % len(split),
          "differs: %s" % sorted(split ^ SPLIT_SUBSYSTEMS)
          if split != SPLIT_SUBSYSTEMS else "")

    pdbs = st.pdb_paths(paths)
    target = st.segments(pdbs[0])[2] if pdbs else None
    check(len(pdbs) == 1 and target == "Gw",
          "the linker's PDB path names build target 'Gw'",
          pdbs[0] if pdbs else "no PDB path found")

    print()
    print("5. shared trees carry no Cli directory (build %s)" % name)
    for tree in SHARED:
        owned = [p for p in paths if p.startswith(st.PREFIX + tree + SEP)]
        with_cli = [p for p in owned if "Cli" in st.segments(p)]
        check(owned and not with_cli,
              "%s%s: %d files, 0 under Cli%s" % (st.PREFIX, tree, len(owned), SEP),
              "has Cli dirs: %s" % with_cli if with_cli else "")

# --- 3b. this scan and asserts.py must agree where they overlap --------------
# Two modules extract `P:\Code\...` paths from the same image by methods that
# share nothing: this one regex-scans the raw file for the string, `asserts.py`
# decodes the four-instruction assert idiom in .text and takes the path out of
# the `mov edx` operand. Neither is a superset of the other by construction --
# but it must be one by RESULT, because every path an assert names is also a
# string in the image. So the assert files are contained in the srctree paths,
# and the remainder is real: files some other macro named, plus the linker's own
# PDB path. If containment ever breaks, one of the two scans is broken, and the
# direction of the break says which.
print()
print("3b. the assert scan's paths are contained in this one's")
sys.path.insert(0, HERE)
from asserts import Asserts                                  # noqa: E402
import pinned as _P                                          # noqa: E402

_st = set(st.source_paths(load(BUILDS[-1][0])))
_az = {a.file for a in Asserts(_P.find()[0]).items}
check(len(_st) == 937, "srctree finds 937 paths", "%d" % len(_st))
check(len(_az) == 865, "asserts names 865 of them", "%d" % len(_az))
check(not (_az - _st), "every assert path is one srctree found",
      "missing %s" % sorted(_az - _st)[:3] if (_az - _st) else "")
check(len(_st - _az) == 72, "and 72 paths no assert references",
      "%d" % len(_st - _az))
check(any(p.lower().endswith(".pdb") for p in _st - _az),
      "including the linker's PDB path, which names the build target")

# --- 3c. and asserts.py must keep DISCLOSING what its pattern scan misses ----
# Added 2026-08-11 (studies/enemy/PLAN.md 10.6). The tool self-reported 19,758
# readable sites plus 3 it named unreadable, and an independent `call rel32`
# sweep of .text finds 20,131 -- so it was short by 370 it did not know about,
# because all three shapes are contiguous byte patterns and the compiler
# schedules other instructions into them. `AgAgent:2366` at 0x006029BC carries
# an `fstp st(0)` and is invisible while its twin :2367 three instructions later
# IS read, which is exactly why nobody noticed for two weeks.
#
# The NUMBER is not what this pins -- another build would move it. What it pins
# is that the DISCLOSURE survives: every "no assert names X" answer from this
# tool is a floor, and `codescan.py --in <module>` takes its bounds from here.
# An edit that dropped the shortfall line would quietly restore the false
# census, and nothing else in the suite would notice.
print()
print("3c. asserts.py discloses its own blind spot")
_azo = Asserts(_P.find()[0])
_cov = _azo.coverage()
check(_cov["call_sites"] > _cov["total"] + _cov["unreadable"],
      "the independent call sweep exceeds what the pattern scan read",
      "%d call sites vs %d read + %d named unreadable"
      % (_cov["call_sites"], _cov["total"], _cov["unreadable"]))
check(_cov["missed"] == _cov["call_sites"] - _cov["total"] - _cov["unreadable"],
      "and `missed` is that difference, not the tool's own estimate",
      "missed=%d -- the old `unreadable` counted only the misses the scan can "
      "SEE, and said 3" % _cov["missed"])
check(any("SHORT BY" in ln for ln in _azo.coverage_lines()),
      "and every query prints the shortfall rather than a bare count",
      "the line that stops a floor being read as a census")
check(not _azo.grep("AGENT_MIN_MOVE_SPEED"),
      "worked example: AgAgent:2366 is provably there and unreadable",
      "0 sites for an assert whose twin :2367 at 0x006029D4 IS read -- a "
      "demonstrated miss, not a hypothetical one")

# --- 4. -mock is a graphics device, not a mock server ------------------------
print()
print("4. -mock closeout, on the pinned build")
blob = load(BUILDS[-1][0])
found = set()
for m in re.finditer(rb"[\x20-\x7e]{3,80}", blob):
    s = m.group().decode()
    if "mock" in s.lower():
        found.add(("ascii", s))
for m in re.finditer(rb"(?:[\x20-\x7e]\x00){3,80}", blob):
    s = m.group().decode("utf-16-le")
    if "mock" in s.lower():
        found.add(("utf16", s))
check(found == MOCK_STRINGS,
      "exactly 3 'mock' strings, all naming a device",
      "got %s" % sorted(found) if found != MOCK_STRINGS else
      "no mock server, no offline mode")

print()
print("scanned both builds in %.1fs" % (time.time() - START))
sys.exit(LEDGER.verdict())
