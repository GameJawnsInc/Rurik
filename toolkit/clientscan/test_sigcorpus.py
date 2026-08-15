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
    must be DIFFERENT on at least one build pair. If they were the same
    everywhere, the corpus would be evidence of nothing -- shapes surviving is
    only interesting because the addresses did not.

WHAT IT MUST NOT BE READ AS SAYING. Not "signatures are stable". The claim is:
address anchoring failed where the code moved, shape anchoring survived every
sample.

UPDATED 2026-08-14, BUILD 38833, AND §2/§3 BOTH HAD TO CHANGE SHAPE. Both were
written for exactly two builds -- `(_sa, pa), (_sb, pb) = sorted(PES.items())`,
a ValueError on three -- and both demanded that addresses DIFFER across "the two
builds". 38833 refutes that as a universal: it is a 15-day bugfix that left
`Gw.exe` the same length, and SIG_KEYS and SIG_MUTEX resolve to the SAME address
on 38797 and 38833 while SIG_DOWNLOAD moved 144 bytes. Requiring every pair to
differ would fail correct anchors because the client did not move. Both sections
are now pairwise: hit counts asserted on EVERY build, disjointness required of
at least one PAIR, and pairs that agree printed as the measurement they are.
See `studies/crossbuild/FINDINGS.md` §7.2.

Needs the vault. Floor 35, ~4 s.
"""
import itertools
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

# floor re-measured 2026-08-14 from a real green run: 34 -> 35, build 38833 joining pinned.BUILDS.
LEDGER = checks.Ledger("signature corpus", floor=35)
check = checks.adopt(LEDGER)

try:
    EXES = {b.stamp: os.path.join(vaultpath.require_dir(
        "client", b.stamp, why="signature corpus"), "Gw.exe")
        for b in pinned.BUILDS}
except BaseException as exc:                                 # noqa: BLE001
    EXES = {}
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")

PES = {s: PE(p) for s, p in EXES.items()}


def vas_at(pe, sig):
    """Every VA `sig` resolves to in `pe`. One spelling, used by §2 and §3."""
    return {pe.image_base + pe.off_to_rva(h) for h in pe.find(sig.pattern, ".text")}


def vas_a_eq(pes, stamp_a, stamp_b, sig):
    """Does `sig` land on exactly the same addresses in these two builds?"""
    return vas_at(pes[stamp_a], sig) == vas_at(pes[stamp_b], sig)


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
# GENERALISED FROM TWO BUILDS TO N, 2026-08-14, and the old form is the lesson.
# It read `(_sa, pa), (_sb, pb) = sorted(PES.items())` -- a ValueError the moment
# a third build was registered -- and demanded that every signature resolve to
# DISJOINT addresses across "both builds". Build 38833 breaks that claim without
# breaking rule 2: it is a 15-day patch that left most of `.text` in place, so
# several signatures resolve to the SAME addresses on 38797 and 38833. Requiring
# disjointness on every pair would fail correct anchors for the crime of the
# client not having moved.
#
# The argument only ever needed ONE disjoint pair: if the identical byte string
# matches at unrelated addresses on two builds, it cannot contain build-varying
# bytes. So the hit count is asserted on EVERY build (the strong per-build
# claim), and disjointness is asserted over the pairs that can carry it.
if len(PES) >= 2:
    items = sorted(PES.items())
    for s in SC.SIGNATURES:
        vas = {}
        counts_ok = True
        for stamp, pe in items:
            hits = pe.find(s.pattern, ".text")
            counts_ok = counts_ok and len(hits) == s.hits
            vas[stamp] = {pe.image_base + pe.off_to_rva(h) for h in hits}

        disjoint = [(a, b) for (a, _), (b, _) in
                    itertools.combinations(items, 2) if not (vas[a] & vas[b])]
        check(counts_ok and disjoint,
              f"{s.name}: one byte string, {len(items)} builds at {s.hits} hit(s), "
              f"{len(disjoint)} pair(s) fully disjoint",
              "so it carries no build-varying bytes -- which is rule 2. A "
              "signature with NO disjoint pair is unproven, not disproven: "
              "re-check it against a build gap that actually moved this code")

        # The narrow scan that IS sound: a signature must not embed an address it
        # itself resolves to on any build. That would be a real defect and is
        # not something coincidence produces.
        windows = {int.from_bytes(s.pattern[i:i + 4], "little")
                   for i in range(len(s.pattern) - 3)}
        every = set().union(*vas.values()) if vas else set()
        check(not (windows & every),
              f"{s.name}: and does not embed an address it resolves to")

check(all(len(s.pattern) >= 3 for s in SC.SIGNATURES),
      "and none is shorter than 3 bytes",
      "the shortest is COLOUR_STRIDE at 3, carried as a durability sample "
      "rather than as a locator for exactly that reason")


print("\n3. the addresses moved -- which is why the shapes matter")

# ALSO GENERALISED 2026-08-14, and this section is where the point actually bit.
# Its heading is "the addresses moved" -- and across 38797 -> 38833 they did NOT.
# That gap is a 15-day bugfix which left `Gw.exe` the same length and left the
# build getter, the assert callee, the DH struct and RegisterMsgs at identical
# addresses (studies/crossbuild/FINDINGS.md §7.2). The section's claim is true of
# the 90-day gap and false of the 15-day one, so it is now stated per PAIR and
# the requirement is that a signature moves SOMEWHERE -- which is all that is
# needed for "the shapes matter", and all the evidence supports.
if len(PES) >= 2:
    items = sorted(PES.items())
    for s in SC.SIGNATURES:
        vas = {stamp: {pe.image_base + pe.off_to_rva(h)
                       for h in pe.find(s.pattern, ".text")}
               for stamp, pe in items}
        distinct = {frozenset(v) for v in vas.values()}
        check(all(vas.values()) and len(distinct) > 1,
              f"{s.name}: resolves to different addresses on at least one build "
              f"pair ({len(distinct)} distinct address sets over {len(items)} builds)",
              f"{ {k: sorted(hex(x) for x in v) for k, v in vas.items()} } -- if "
              f"every build agrees, this signature has never been shown to "
              f"survive a move and is a durability sample of nothing")
    for (a, _), (b, _) in itertools.combinations(items, 2):
        same = [s.name for s in SC.SIGNATURES if vas_a_eq(PES, a, b, s)]
        if same:
            print(f"     note: {a} vs {b} -- {len(same)} of "
                  f"{len(SC.SIGNATURES)} signature(s) at the SAME address(es): "
                  f"{', '.join(same)}. That gap did not move this code.")


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
