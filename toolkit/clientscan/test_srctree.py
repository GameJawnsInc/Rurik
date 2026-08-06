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

import srctree as st                                         # noqa: E402
import vaultpath                                             # noqa: E402

SEP = st.SEP

# Both vaulted builds. The finding must hold on both, not just the pinned one.
BUILDS = [
    ("2026-04-30_b174de1f2d8d", 936),
    ("2026-07-29_221c13772c7a", 937),
]

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

fails = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           "" if not detail else "  -- " + detail))
    if not ok:
        fails.append(label)
    return ok


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
if fails:
    print("[FAIL] %d check(s) failed: %s" % (len(fails), "; ".join(fails)))
    raise SystemExit(1)
print("[PASS] all checks passed (%.1fs)" % (time.time() - START))
