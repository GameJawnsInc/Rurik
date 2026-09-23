"""The c2s send-site census, pinned against two builds.

    python toolkit/clientscan/test_sendsites.py

WHAT THIS PINS, and why each section can go red.

  * §1: the two framers are found by the MASKED PROLOGUE SIGNATURE, not by a
    hardcoded VA -- exactly two on each build, and on 38797/38888 they are the
    known VAs. The order of the two VAs swapped between the builds, which is the
    reason a census that hardcoded 'the second framer' would have censused the
    wrong channel on the newer client.
  * §2: 214 call sites, 40 + 174 across the two framers, reproduced on both
    builds -- the count the D1 survey put at 214 and the reason a single-framer
    census (which would find 174) is not enough.
  * §3: THE FIVE ANCHORS, pinned per build. Each of 0x0040, 0x0016, 0x00B1,
    0x001E, 0x001F resolves to exactly ONE game-channel wrapper, at the VA
    measured here. 38888 moved every address, so the same opcode lands at a
    different VA -- the anchor is the OPCODE-to-wrapper binding, found by the
    census on each build, and the per-build VA is the regression pin. This
    section also carries the route CORRECTION: the D1 survey put 0x0016's 38797
    wrapper at 0x0091FD60, which in fact stores opcode 0x17; the true 0x0016
    wrapper is 0x0091FD00 (0x0091FD60 is the 0x0017 sender).
  * §4: THE KNOWN-BAD ARM. A wrong framer VA yields zero sites. A census whose
    failure mode is a silent empty result is the one that reads as a green 'no
    c2s opcodes' the day the signature drifts, so this feeds a bogus VA and
    requires nothing back.
  * §5: the AUTH homonyms do NOT pollute the anchors -- AUTH_CMSG 0x16/0x1e sit
    on the other framer and `anchors()` scopes to the game framer, so a wrong
    scoping would nominate three wrappers for 0x0016 instead of one.

Needs the vault (two client snapshots). Floor 35, ~6 s.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
import checks                                                # noqa: E402
import vaultpath                                             # noqa: E402
import sendsites                                             # noqa: E402
from gwpe import PE                                          # noqa: E402

LEDGER = checks.Ledger("c2s send-site census", floor=35)

# The two builds this test pins, and everything MEASURED on them 2026-09-22.
# Framers: (game_framer_va, auth_framer_va) -- the busier is the game channel.
BUILDS = {
    "2026-07-29_221c13772c7a": {
        "build": 38797,
        "framers": {0x007DCB10, 0x007DCF00},
        "game": 0x007DCF00,
        "anchors": {0x0040: 0x009207B0, 0x0016: 0x0091FD00, 0x00B1: 0x0085C280,
                    0x001E: 0x0091FF00, 0x001F: 0x0091FF30},
    },
    "2026-09-01_44fbd68767a8": {
        "build": 38888,
        "framers": {0x007DCF70, 0x007DD360},
        "game": 0x007DD360,
        "anchors": {0x0040: 0x00921130, 0x0016: 0x00920680, 0x00B1: 0x0085C7C0,
                    0x001E: 0x00920880, 0x001F: 0x009208B0},
    },
}


def _exe(stamp):
    root = vaultpath.require_dir("client")
    return os.path.join(root, stamp, "Gw.exe")


try:
    EXES = {stamp: _exe(stamp) for stamp in BUILDS}
    MISSING = [s for s, p in EXES.items() if not os.path.exists(p)]
except Exception as exc:                                     # noqa: BLE001
    LEDGER.skip("every section", f"vault/client unavailable: {exc}")
    sys.exit(LEDGER.verdict())

if MISSING:
    LEDGER.skip("every section",
                f"missing client snapshot(s): {', '.join(MISSING)}")
    sys.exit(LEDGER.verdict())


for stamp, want in BUILDS.items():
    pe = PE(EXES[stamp])
    b = want["build"]

    # -- §1 the framers, by signature --------------------------------------
    fr = set(sendsites.find_framers(pe))
    LEDGER.ok(len(fr) == 2,
              f"[{b}] the masked prologue signature finds exactly two framers",
              f"found {['0x%08X' % x for x in sorted(fr)]}")
    LEDGER.ok(fr == want["framers"],
              f"[{b}] and they are the known VAs",
              f"{sorted('0x%08X' % x for x in fr)} != "
              f"{sorted('0x%08X' % x for x in want['framers'])}")

    rows = sendsites.census(pe)
    cov = sendsites.coverage(rows)

    # -- §2 the site count -------------------------------------------------
    LEDGER.ok(cov["sites"] == 214,
              f"[{b}] 214 call sites across both framers",
              f"got {cov['sites']}")
    per = cov["per_framer"]
    LEDGER.ok(sorted(per.values()) == [40, 174],
              f"[{b}] 40 + 174, one framer per channel",
              f"got {sorted(per.values())}")
    LEDGER.ok(sendsites.game_framer(rows) == want["game"],
              f"[{b}] the game framer is the busier one",
              f"got 0x%08X" % (sendsites.game_framer(rows) or 0))

    # -- §3 the five anchors, pinned per build -----------------------------
    an = sendsites.anchors(rows)
    for op, va in want["anchors"].items():
        got = an.get(op) or []
        LEDGER.ok(got == [va],
                  f"[{b}] 0x{op:04X} -> one wrapper at 0x{va:08X}",
                  f"got {['0x%08X' % x for x in got]}")
        # The wrapper is a real function: it opens with a prologue.
        off = pe.rva_to_off(va - pe.image_base)
        head = pe.data[off:off + 3] if off is not None else b""
        LEDGER.ok(head == b"\x55\x8b\xec",
                  f"[{b}] 0x{op:04X}'s wrapper 0x{va:08X} is a real prologue",
                  f"head {head.hex()}")

    # -- §5 the AUTH homonyms are scoped out -------------------------------
    # Without game-framer scoping, 0x0016 would nominate the AUTH-channel
    # List/GcAuthCmd wrappers too. Prove they exist on the OTHER framer, so the
    # scoping in §3 is doing real work rather than being vacuous.
    auth_16 = [r for r in rows if r["opcode"] == 0x0016
               and r["framer_va"] != want["game"] and r["confident"]]
    LEDGER.ok(len(auth_16) >= 1,
              f"[{b}] the AUTH channel also carries a 0x16 sender (the homonym "
              f"the anchor scoping excludes)",
              f"found {len(auth_16)}")


# -- §4 the known-bad arm (build-independent) ------------------------------
pe97 = PE(EXES["2026-07-29_221c13772c7a"])
bad = sendsites.census(pe97, framers=[0xDEADBEEF])
LEDGER.ok(bad == [],
          "a wrong framer VA yields zero rows -- the census cannot silently "
          "find nothing and read as a clean 'no c2s opcodes'")
bad_an = sendsites.anchors(bad)
LEDGER.ok(all(not v for v in bad_an.values()),
          "and its anchors are all empty rather than defaulting to a VA")

# -- vacuity guard ---------------------------------------------------------
full = sendsites.census(pe97)
LEDGER.ok(len(full) > 200 and sendsites.coverage(full)["confident"] > 150,
          "the census is non-empty and mostly confident -- a run that measured "
          "nothing is a failure, not a pass")

sys.exit(LEDGER.verdict())
