"""Every byte-shape anchor this repo uses, and whether it still resolves.

    python toolkit/clientscan/sigcorpus.py            # the pinned client
    python toolkit/clientscan/sigcorpus.py --all      # every vaulted build
    python toolkit/clientscan/sigcorpus.py --exe <path>

WHY. `studies/crossbuild/FINDINGS.md` §2 ends with every build-coupled address
either converted to a byte shape or gated. This is the other half of that claim:
the shapes themselves are an assumption until something counts them, and "the
signature still resolves" is precisely the line `PLAN.md` §11's post-update
command has to print.

It is also where `studies/crossbuild/PLAN.md` §7.2's two derived signatures
live. `studies/profession/WORKAROUNDS.md` §3.5 derived them from scratch --
the attribute accessors at 4 hits and the `imul`-stride colour tables at 2 --
and recorded the counts without ever putting the patterns in code, so nothing
could re-check them. They are here, and they are checked.

WHAT §3.5 CLAIMED AND WHAT THIS NOW MEASURES. That pass reported SIX signatures
reproducing their exact hit counts across the ~90-day gap. Two more were derived
since -- `REGISTER_SIG` for the message tables and `ASSERT_SIG` for the assert
callee, both 2026-08-12 -- so the corpus is **eight**, and all eight reproduce:

    SIG_KEYS       1/1     SIG_MUTEX      1/1     SIG_DOWNLOAD   1/1
    TAP_SIG        1/1     REGISTER_SIG   1/1     ASSERT_SIG     1/1
    ATTR_ACCESSOR  4/4     COLOUR_STRIDE  2/2

while every address they resolve to moved -- the two new profession signatures
by exactly 0x2350 (9,040) bytes, which is the figure §3.5 recorded.

WHAT THIS DOES NOT ESTABLISH, and the plan says it twice for a reason: **do not
report "signatures are stable".** This is n=2 over one build gap. The supportable
claim is that address anchoring failed on both samples and shape anchoring
survived both, and the value of this module is that the next build turns the
sentence into a measurement instead of an argument.

STANDARD LIBRARY ONLY. READ ONLY.
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
from gwpe import PE                                          # noqa: E402
import asserts                                              # noqa: E402
import dhbuild                                              # noqa: E402
import keytap_patch                                         # noqa: E402
import msgshape                                             # noqa: E402
import pinned                                               # noqa: E402

Sig = collections.namedtuple("Sig", "name pattern hits anchors owner")

# `hits` is what a healthy build produces, MEASURED on both vaulted builds
# 2026-08-12/13. It is a class-(c) expectation under `studies/crossbuild/PLAN.md`
# §6: a new build changing one of these is a real finding, and this going red is
# how it gets noticed rather than discovered later by a tool returning nonsense.
#
# The patterns are IMPORTED, never re-typed. Three modules once spelled SIG_KEYS
# out separately and drifted into three different policies on a second match.
SIGNATURES = (
    Sig("SIG_KEYS", dhbuild.SIG_KEYS, 1,
        "the Diffie-Hellman parameter struct accessor",
        "clientpatch/dhbuild.py"),
    Sig("SIG_MUTEX", dhbuild.SIG_MUTEX, 1,
        "the single-instance mutex guard",
        "clientpatch/dhbuild.py"),
    Sig("SIG_DOWNLOAD", dhbuild.SIG_DOWNLOAD, 1,
        "the updater's downloader gate",
        "clientpatch/dhbuild.py"),
    Sig("TAP_SIG", keytap_patch.TAP_SIG, 1,
        "the session-key tap site",
        "clientpatch/keytap_patch.py"),
    Sig("REGISTER_SIG", msgshape.REGISTER_SIG, 1,
        "MsgChannel::RegisterMsgs, which installs the message tables",
        "clientscan/msgshape.py"),
    Sig("ASSERT_SIG", asserts.ASSERT_SIG, 1,
        "the routine every assert site calls",
        "clientscan/asserts.py"),

    # studies/crossbuild/PLAN.md §7.2, from studies/profession/WORKAROUNDS.md
    # §3.5. Derived there, counted there, and never put in code until now.
    #
    # The attribute accessors are the four `ConstAttrib` getters
    # (studies/profession/ATTRIBUTES.md:301-304) -- description id, primary
    # flag, name id, owning profession. The shape is their shared bound check,
    # `cmp esi, 0x33` (51 attributes) followed by the branch and the push of the
    # assert line. It stops before the push's OPERAND and before the two
    # absolute VAs that follow, because those are the build-specific part.
    Sig("ATTR_ACCESSOR", bytes.fromhex("83fe33721468"), 4,
        "the four ConstAttrib accessors' shared 51-attribute bound check",
        "not yet consumed -- a durability sample, see this module's docstring"),

    # `imul edx, esi, 0x0b` -- the stride-11 index into the two colour tables
    # studies/profession/FINDINGS.md:67 names, at 0x005A8E7D and 0x005A8F1D on
    # 38797. Three bytes is thin for a signature, which is why it is carried as
    # a DURABILITY SAMPLE and not as a locator: nothing patches through it, and
    # its job is to have its count checked.
    Sig("COLOUR_STRIDE", bytes.fromhex("6bd60b"), 2,
        "the stride-11 index into s_colorInfo's two tables",
        "not yet consumed -- a durability sample, see this module's docstring"),
)


def verify(pe):
    """[(Sig, hits, ok)] for one image."""
    return [(s, len(pe.find(s.pattern, ".text")),
             len(pe.find(s.pattern, ".text")) == s.hits) for s in SIGNATURES]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", help="client to check; defaults to the pinned one")
    ap.add_argument("--all", action="store_true",
                    help="every build in pinned.BUILDS")
    a = ap.parse_args(argv)

    targets = []
    if a.all:
        for b in pinned.BUILDS:
            try:
                targets.append((pinned.name_of(b), pinned.find(b.stamp)[0]))
            except SystemExit as exc:
                print(f"{pinned.name_of(b)}: {exc}")
    elif a.exe:
        targets.append(("given on the command line", a.exe))
    else:
        p, why = pinned.find()
        targets.append((why, p))

    rc = 0
    for label, exe in targets:
        print(f"\n{exe}\n  ({label})")
        pe = PE(exe)
        for s, hits, ok in verify(pe):
            mark = "ok " if ok else "!! "
            print(f"  {mark}{s.name:14s} {hits:3d} hit(s), expected {s.hits:3d}"
                  f"   {s.anchors}")
            if not ok:
                rc = 1
        if rc:
            print("\n  A CHANGED COUNT IS A FINDING, not a tool failure. The shape "
                  "moved or the\n  routine was recompiled; re-derive it before "
                  "trusting the tool that owns it.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
