"""Every byte-shape anchor in the repo, counted on both vaulted builds.

    python toolkit/clientscan/test_sigcorpus.py

WHY. `studies/crossbuild/FINDINGS.md` §2 ends with every build-coupled address
converted to a byte shape or gated. That leaves the shapes themselves as the
assumption underneath the whole arc, and until this file nothing counted them.

`studies/profession/WORKAROUNDS.md` §3.5 reported six signatures reproducing
their exact hit counts across the ~90-day gap and recorded the numbers in prose;
two of the six -- the attribute accessors and the `imul`-stride colour tables --
were derived there and never written into code, so nothing could re-check them.
`studies/crossbuild/PLAN.md` §7.2 asked for them. They are in `sigcorpus.py` now,
with `REGISTER_SIG` and `ASSERT_SIG` derived since, making the corpus **eight**.

THE THREE CHECKS THAT EARN THE FILE:

  * §1 counts all eight on BOTH builds. Exact counts, not "at least one" -- a
    signature that has quietly become ambiguous still resolves and still returns
    an answer, which is the failure mode rule 1 exists for.
  * §2 is rule 2 -- **no pattern may carry a build-specific address** -- checked
    the way the evidence actually supports. The obvious version ("no 4-byte
    window lands in the image range") was written, run, and REFUTED by its own
    output: it flags SIG_KEYS and ASSERT_SIG on windows that straddle instruction
    boundaries, in signatures that match BOTH builds. The sound argument is that
    one byte string matching two images whose addresses all moved cannot contain
    a build-varying byte, so §2 asserts exactly that per signature, plus the
    narrow scan that IS sound: no signature embeds an address it resolves to.
  * §3 is the point of the whole exercise: the addresses these shapes resolve to
    must be DIFFERENT on the two builds. If they were the same, the corpus would
    be evidence of nothing -- shapes surviving is only interesting because the
    addresses did not.

WHAT IT MUST NOT BE READ AS SAYING. Not "signatures are stable". n=2 over one
build gap, and the plan says so twice. The claim is: address anchoring failed on
both samples, shape anchoring survived both.

Needs the vault. Floor 34, ~4 s.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                                # noqa: E402
import pinned                                                # noqa: E402
import sigcorpus as SC                                       # noqa: E402
import vaultpath                                             # noqa: E402
from gwpe import PE                                          # noqa: E402

LEDGER = checks.Ledger("signature corpus", floor=34)
check = checks.adopt(LEDGER)

try:
    EXES = {b.stamp: os.path.join(vaultpath.require_dir(
        "client", b.stamp, why="signature corpus"), "Gw.exe")
        for b in pinned.BUILDS}
except BaseException as exc:                                 # noqa: BLE001
    EXES = {}
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")

PES = {s: PE(p) for s, p in EXES.items()}


print("\n1. all eight resolve, at their exact counts, on both builds")

check(len(SC.SIGNATURES) == 8, "the corpus holds eight signatures",
      f"{len(SC.SIGNATURES)}")

for stamp, pe in sorted(PES.items()):
    bad = [(s.name, hits, s.hits) for s, hits, ok in SC.verify(pe) if not ok]
    check(not bad, f"{pinned.select(stamp) and stamp}: all eight at their "
                   f"expected counts",
          "; ".join(f"{n}: {h} != {w}" for n, h, w in bad))

# Named individually, because "all eight" hides which one moved and the two the
# plan asked for are the ones with no consumer to notice.
for want in ("ATTR_ACCESSOR", "COLOUR_STRIDE"):
    sig = next(s for s in SC.SIGNATURES if s.name == want)
    counts = {stamp: len(pe.find(sig.pattern, ".text")) for stamp, pe in PES.items()}
    check(set(counts.values()) == {sig.hits},
          f"{want} is {sig.hits} on every vaulted build  "
          f"(PLAN.md §7.2, derived in WORKAROUNDS §3.5 and never landed)",
          str(counts))


print("\n2. rule 2: no signature carries a build-specific address")

# HOW THIS IS CHECKED, and the first version was wrong in a way worth recording.
#
# The obvious mechanical test is "no 4-byte window of the pattern lands in the
# client's image range". It was written, run, and REFUTED by its own evidence:
# it flags SIG_KEYS (`0xc70845`, `0x8800c7`) and ASSERT_SIG (`0xe8e04d`), which
# are windows straddling instruction boundaries in signatures that demonstrably
# match BOTH builds. A byte run cannot both contain a build-specific address and
# match two images whose addresses all moved, so the scanner was reporting
# coincidences and would have made this file cry wolf on two correct anchors.
#
# The sound check is the one the evidence already supports: the SAME byte string
# matches on both builds AND resolves to disjoint addresses. That is only
# possible if the pattern contains nothing build-varying, which is rule 2. It is
# asserted per signature below rather than argued in a comment.
if len(PES) >= 2:
    (_sa, pa), (_sb, pb) = sorted(PES.items())
    for s in SC.SIGNATURES:
        ha = pa.find(s.pattern, ".text")
        hb = pb.find(s.pattern, ".text")
        va_a = {pa.image_base + pa.off_to_rva(h) for h in ha}
        va_b = {pb.image_base + pb.off_to_rva(h) for h in hb}
        check(len(ha) == len(hb) == s.hits and not (va_a & va_b),
              f"{s.name}: one byte string, both builds, disjoint addresses",
              "so it carries no build-varying bytes -- which is rule 2")

        # The narrow scan that IS sound: a signature must not embed an address it
        # itself resolves to on either build. That would be a real defect and is
        # not something coincidence produces.
        windows = {int.from_bytes(s.pattern[i:i + 4], "little")
                   for i in range(len(s.pattern) - 3)}
        check(not (windows & (va_a | va_b)),
              f"{s.name}: and does not embed an address it resolves to")

check(all(len(s.pattern) >= 3 for s in SC.SIGNATURES),
      "and none is shorter than 3 bytes",
      "the shortest is COLOUR_STRIDE at 3, carried as a durability sample "
      "rather than as a locator for exactly that reason")


print("\n3. the addresses moved -- which is why the shapes matter")

if len(PES) >= 2:
    (sa, pa), (sb, pb) = sorted(PES.items())
    for s in SC.SIGNATURES:
        va_a = {pa.image_base + pa.off_to_rva(h) for h in pa.find(s.pattern, ".text")}
        va_b = {pb.image_base + pb.off_to_rva(h) for h in pb.find(s.pattern, ".text")}
        check(va_a and va_b and not (va_a & va_b),
              f"{s.name}: resolves to different addresses on the two builds",
              f"{sorted(hex(v) for v in va_a)} vs {sorted(hex(v) for v in va_b)}")


print("\n4. a signature that does not resolve is reported, not smoothed over")

if PES:
    pe = next(iter(PES.values()))
    real = SC.SIGNATURES
    try:
        SC.SIGNATURES = (SC.Sig("MADE_UP", bytes.fromhex("d0d0d0d0d0d0d0d0"), 1,
                                "nothing", "test"),)
        bad = [r for r in SC.verify(pe) if not r[2]]
        check(len(bad) == 1 and bad[0][1] == 0,
              "a pattern that is not in the image is reported as 0 hits, not ok")
        rc = SC.main(["--exe", EXES[pinned.PINNED.stamp]])
        check(rc == 1, "and the CLI exits non-zero on a changed count", f"rc={rc}")

        SC.SIGNATURES = (SC.Sig("WRONG_COUNT", real[0].pattern, 99,
                                "nothing", "test"),)
        bad = [r for r in SC.verify(pe) if not r[2]]
        check(len(bad) == 1,
              "and a real pattern with the wrong expected count is reported too",
              "an exact count is the check; 'at least one' would pass here")
    finally:
        SC.SIGNATURES = real

    # POSITIVE CONTROL: the real corpus still passes, so section 4 is the
    # mismatch being caught rather than a verifier that fails everything.
    check(SC.main(["--exe", EXES[pinned.PINNED.stamp]]) == 0,
          "while the real corpus exits 0")

sys.exit(LEDGER.verdict())
