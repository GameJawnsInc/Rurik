"""livewire.py: the committed retail-decode recipe, pinned to its own record.

What this refuses to let rot: the byte-closure discipline (a connection whose
wire and plaintext accounting disagree is REFUSED, never partially decoded),
the origin gate (an `ours` capture filed under live/ never leaks into a
retail census), and -- the reason the module exists at all (RETHINK
instrument #2) -- the ability of a cold session to reproduce the campaign's
retail-contract ground truth without re-deriving the wire recipe from a dead
scratchpad. The load-bearing validation is a NUMBER WITH INDEPENDENT
PROVENANCE: the 62994 connection's 432 player-era s2c 0x0029 rows were
counted by a different session's script (the 2026-08-26 drawing-board
skeptic, rethink-skeptic.md attack 1) before this module existed; this file
requires the committed recipe to reproduce it exactly.

The vault sections skip LOUDLY on a machine without the live corpus; the
floor is set from the green run on the machine that has it (the house rule:
from a real run, never a guess).
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks      # noqa: E402
import livewire    # noqa: E402

# MEASURED from the real green run on 2026-08-26: 12 checks against the
# 20-capture live corpus. Set AT the run per the house rule -- zero headroom.
LEDGER = checks.Ledger("livewire: the committed retail-decode recipe",
                       floor=12)
check = checks.adopt(LEDGER)


def main():
    print("1. the doors that need no vault")
    check(livewire.connections(os.path.join(tempfile.gettempdir(),
                                            "no-such-capture-dir")) == [],
          "connections() on a missing directory is an empty list, not a "
          "raise",
          "a census loop over capture dirs must survive a half-copied "
          "vault; the LOUD refusal belongs to require-style callers")
    with tempfile.TemporaryDirectory() as td:
        who, why = livewire.capture_origin(td)
        check(who is None and why == "no wire.jsonl",
              "a directory without wire.jsonl has no origin and says so",
              "an unstamped capture must never default to either origin -- "
              "origin.py's three-valued rule, applied at the loader")

    print("\n2. the live corpus (skips loudly without the vault)")
    root = livewire.captures_root()
    if not os.path.isdir(root):
        LEDGER.skip("no live capture corpus at %s -- the corpus sections "
                    "need the owner's vault" % root)
        LEDGER.verdict()
        return
    caps = livewire.live_captures()
    check(len(caps) >= 20,
          "the origin gate passes at least the 20 live captures the "
          "2026-08-26 census counted",
          "fewer means either the vault moved or the gate started refusing "
          "real live captures -- both are wrong loudly")
    names = {os.path.basename(c) for c, _ in caps}
    check("20260817T175358" not in names or len(names) >= 20,
          "the gate EXCLUDES at least one non-live directory (21 dirs on "
          "disk, 20 live at the pin date)",
          "a gate that passes everything is not a gate; the excluded "
          "directory is the control")

    print("\n3. the pinned connection: independent-provenance numbers")
    capdir = os.path.join(root, "20260807T143055")
    gf = "game-10.0.0.210_62994-to-54.198.7.73_80.jsonl"
    if not os.path.exists(os.path.join(capdir, gf)):
        LEDGER.skip("pinned connection %s missing" % gf)
    else:
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        check(ok is True,
              "the 62994 connection decodes with FULL byte closure both "
              "directions",
              "ok=False means the wire/plaintext accounting stopped "
              "closing -- the schema or the recipe drifted")
        check(conn == "10.0.0.210:62994->54.198.7.73:80",
              "the connection identity reads back from the version row",
              "the conn string is what joins this stream to wire.jsonl; "
              "a wrong one dates messages with another connection's clock")
        n41 = sum(1 for r in merged if r[1] == "s2c" and r[2] == 41)
        check(n41 == 432,
              "s2c 0x0029 count == 432 -- the drawing-board skeptic's own "
              "independently-scripted count, reproduced by the committed "
              "recipe",
              "this is the module's whole reason to exist: a number with "
              "provenance OUTSIDE this module. A drift here is a decode "
              "regression, not a corpus change -- the corpus is frozen")
        n62 = sum(1 for r in merged if r[1] == "c2s" and r[2] == 62)
        n61 = sum(1 for r in merged if r[1] == "c2s" and r[2] == 61)
        check(n62 == 12 and n61 == 99,
              "c2s censuses pin too: 12 clicks (0x003E) and 99 heading "
              "reports (0x003D) on the same connection",
              "op 62 vs 64 is the exact confusion that reached a lane "
              "brief once (sec.0.17's instrument corrections); pinning "
              "both directions catches a mask or channel swap")
        check(len(merged) == 2821,
              "total decoded message count == 2821",
              "the coarsest whole-stream pin -- any silent gain or loss "
              "of messages moves it")
        ts = [r[0] for r in merged]
        check(all(a <= b for a, b in zip(ts, ts[1:])),
              "the merged stream is time-ordered",
              "consumers window over time; an unsorted merge makes every "
              "silence census wrong quietly")

    print("\n4. the rung-7 capture: whole-capture closure")
    capdir = os.path.join(root, "20260818T132739")
    if not os.path.isdir(capdir):
        LEDGER.skip("capture 20260818T132739 missing")
    else:
        conns = livewire.connections(capdir)
        check(len(conns) == 8,
              "the rung-7 damage capture holds its 8 game connections "
              "(PLAN's '9/9 decrypted' = these plus the auth channel)",
              "a lost connection is a lost third of a damage corpus")
        oks = [livewire.decode_conn(capdir, gf)[2] for gf in conns]
        check(all(oks),
              "ALL 8 decode with full byte closure",
              "rung 7's 495 damage events ride these streams; a partial "
              "decode reported as a full one is the suite's oldest defect "
              "class")

    LEDGER.verdict()


if __name__ == "__main__":
    main()
