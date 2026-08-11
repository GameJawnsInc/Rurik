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
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vaultpath                                              # noqa: E402

BUILD = 38797
SIZE = 10_483_904
STAMP = "2026-07-29_221c13772c7a"

# MEASURED 2026-08-06. The directory stamp is the pristine file's own hash
# prefix, which is why the patched copy sitting under the same stamp is easy to
# miss: the name is right and the bytes are not.
PRISTINE_SHA256 = "221c13772c7a4fd1f3efd6769694614ed608909706d60a9d2b7190ba10119a75"
PATCHED_SHA256 = "fa9563f1851014e80117195a1b66850c913433c4aba584ec6309b97e46bbf7e6"

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


def identify(path):
    """('pristine' | 'patched' | 'unknown', human-readable detail)."""
    if not os.path.isfile(path):
        return "unknown", "no such file"
    size = os.path.getsize(path)
    if size != SIZE:
        return "unknown", f"{size:,} bytes, not build {BUILD}'s {SIZE:,}"
    digest = sha256(path)
    if digest == PRISTINE_SHA256:
        return "pristine", f"build {BUILD}, as ArenaNet shipped it"
    if digest == PATCHED_SHA256:
        return "patched", (f"build {BUILD}, OUR patched copy -- 9 bytes of .text "
                           f"differ from the shipped client")
    return "unknown", f"build {BUILD}'s size but sha256 {digest[:16]}..., neither copy"


def find():
    """(path, why). Pristine first, then our patched copy, then the live install.

    Never silently either -- `why` is meant to be printed. A tool that says
    which file it read lets a surprising result be diagnosed in one line
    instead of being argued about.
    """
    for kind, label in (("client", "pinned pristine client"),
                        ("run", "pinned PATCHED copy (pristine not in the vault)")):
        p = vaultpath.vault_path(kind, STAMP, "Gw.exe")
        if os.path.isfile(p):
            return p, label
    if os.path.isfile(LIVE_INSTALL):
        return LIVE_INSTALL, "live install -- auto-updates, so it may not be 38797"
    raise SystemExit(
        f"no client to read.\n"
        f"  looked in {vaultpath.vault_root()} ({vaultpath.vault_why()})\n"
        f"  for client/{STAMP}/Gw.exe and run/{STAMP}/Gw.exe\n"
        f"  and for {LIVE_INSTALL}\n"
        f"  Set RURIK_VAULT, or see RUNBOOK.md.")


def patches_touch(va, span=1):
    """Do our patched .text bytes overlap [va, va+span)? The reason this list exists."""
    return [why for lo, hi, why in PATCHED_TEXT
            if not (va + span - 1 < lo or va > hi)]


def main():
    print(f"build {BUILD}, {SIZE:,} bytes, vault stamp {STAMP}")
    print(f"vault: {vaultpath.vault_root()} ({vaultpath.vault_why()})\n")
    for kind in ("client", "run"):
        p = vaultpath.vault_path(kind, STAMP, "Gw.exe")
        what, detail = identify(p)
        print(f"  {kind + '/':8} {what:8} {detail}")
        print(f"           {p}")
    what, detail = identify(LIVE_INSTALL)
    print(f"  {'live':8} {what:8} {detail}")
    path, why = find()
    print(f"\ndefault for static analysis: {path}\n  ({why})")
    print("\nour patch changes these .text bytes; an address landing here is ours:")
    for lo, hi, w in PATCHED_TEXT:
        print(f"  0x{lo:08X}..0x{hi:08X}  {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
