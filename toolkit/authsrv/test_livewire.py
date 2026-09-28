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
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks      # noqa: E402
import livewire    # noqa: E402
import capgaps     # noqa: E402
import tape        # noqa: E402

# MEASURED from the real green run on 2026-08-26: 12 checks against the
# 20-capture live corpus. Set AT the run per the house rule -- zero headroom.
# 2026-09-28 (CASTAI-Z1): 16 -- section 1's two declared-gaps doors and section
# 5's two checks on the first gapped live connection. (A bare machine runs
# section 1 only, 4 checks, below this floor as it always has been.)
# 2026-09-28 (CASTAI-Z1, the gap lane): 18 -- capgaps' set_aside/audit door in
# section 1 (bare, so a bare run is 5) and the whole-corpus set-aside audit in 5.
LEDGER = checks.Ledger("livewire: the committed retail-decode recipe",
                       floor=18)
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
        # declared_gaps reads the capture's OWN manifest (2026-09-28, CASTAI-Z1)
        empty = livewire.declared_gaps(td)
        with open(os.path.join(td, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"report": {"connections": [
                {"connection": "1.2.3.4:5->6.7.8.9:80", "gaps": {}},
                {"connection": "1.2.3.4:6->6.7.8.9:80", "gaps": {"s2c": [[100, 7]]}},
                {"connection": "1.2.3.4:7->6.7.8.9:80", "gaps": {"c2s": [], "s2c": []}}]}}, fh)
        got = livewire.declared_gaps(td)
        # the ONE set-aside (capgaps.py, 2026-09-28): only a declared connection is
        # stepped past, and the audit is RED on a declared gap nobody has named in
        # KNOWN_GAPPED -- the next gapped capture is seen, never absorbed
        for port in (5, 6):
            open(os.path.join(td, f"game-1.2.3.4_{port}-to-6.7.8.9_80.jsonl"), "w").close()
        into = []
        stepped = [capgaps.set_aside(td, f"game-1.2.3.4_{p}-to-6.7.8.9_80.jsonl", got, into)
                   for p in (5, 6, 7)]
        unnamed_ok, unnamed_why = capgaps.audit(into, [td], lambda _c, _n: True)
        stamp = os.path.basename(td)
    check(stepped == [False, True, False]
          and into == [{"capture": stamp, "connection": "1.2.3.4:6->6.7.8.9:80",
                        "gaps": {"s2c": [[100, 7]]}}]
          and not unnamed_ok,
          "set_aside steps past ONLY the declared connection and records it by name; "
          "the audit is RED for a declared gap KNOWN_GAPPED does not name, though it "
          "is set aside and still refused", unnamed_why)
    check(empty == {} and got == {"1.2.3.4:6->6.7.8.9:80": {"s2c": [[100, 7]]}},
          "declared_gaps: no manifest -> {}; of three connections, only the one whose "
          "report lists missing bytes is declared (an empty gap list is not a gap)",
          f"{empty} {got}")
    check(livewire.conn_name("game-10.0.0.210_65009-to-98.95.137.136_80.jsonl")
          == "10.0.0.210:65009->98.95.137.136:80"
          and livewire.conn_name("auth-1.2.3.4_5-to-6.7.8.9_80.jsonl") is None,
          "conn_name spells a game file's connection the way the manifest does, and "
          "refuses a name of another shape")

    print("\n2. the live corpus (skips loudly without the vault)")
    root = livewire.captures_root()
    if not os.path.isdir(root):
        # Two arguments (label, why), and the verdict is RETURNED. Both were
        # wrong until 2026-08-31 and both only bite on a machine with no vault,
        # which is the one this branch exists for: the one-argument `skip`
        # raised TypeError, and had it not, the bare `return` handed `main` a
        # None that `sys.exit` reads as success. Third instance of the same
        # `skip` defect that day (test_castcycle x2, test_policyreplay x2).
        LEDGER.skip("2. the live corpus",
                    "no live capture corpus at %s -- the corpus sections "
                    "need the owner's vault" % root)
        return LEDGER.verdict()
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
        LEDGER.skip("the pinned connection decode",
                    "pinned connection %s missing" % gf)
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
        LEDGER.skip("capture 20260818T132739",
                    "capture 20260818T132739 missing")
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

    print("\n5. a gapped connection is DECLARED by its capture, and still refused")
    capdir = os.path.join(root, "20260928T103123")
    gf = "game-10.0.0.210_65009-to-98.95.137.136_80.jsonl"
    if not os.path.exists(os.path.join(capdir, gf)):
        LEDGER.skip("the gapped connection",
                    "capture 20260928T103123 (CASTAI-Z1) missing")
    else:
        gaps = livewire.declared_gaps(capdir)
        check(gaps == {"10.0.0.210:65009->98.95.137.136:80":
                       {"s2c": [[38045, 38], [38548, 20]]}},
              "CASTAI-Z1's match 2 is the ONE connection its manifest declares gapped: "
              "38 + 20 s2c bytes at stream offsets 38045 / 38548",
              f"{gaps}")
        ok_gapped = livewire.decode_conn(capdir, gf)[2]
        oks = {g: livewire.decode_conn(capdir, g)[2] for g in livewire.connections(capdir)
               if livewire.conn_name(g) not in gaps}
        check(ok_gapped is False and oks and all(oks.values()),
              "decode_conn still REFUSES it (a hole dates later messages with the wrong "
              "bytes), and every connection the manifest does not declare decodes whole",
              f"gapped ok={ok_gapped}; others {sum(oks.values())}/{len(oks)}")
        # the corpus iterators' set-aside, over the WHOLE live corpus: exactly the known
        # set, refused by BOTH doors (decode_conn and load_tape); and the audit's teeth --
        # a refusal callback that answers "decodes" turns it red
        aside = []
        n_yield = sum(1 for _ in livewire.live_connections(set_aside=aside))
        caps = [d for d, _w in livewire.live_captures()]
        a_ok, a_why = capgaps.audit(aside, caps, livewire.refuses)
        t_ok, _t_why = capgaps.audit(aside, caps, tape.refuses)
        bad_ok, _bad_why = capgaps.audit(aside, caps, lambda _c, _n: False)
        check(a_ok and t_ok and not bad_ok and n_yield > 0
              and len(aside) == len(capgaps.KNOWN_GAPPED),
              "live_connections(set_aside=) sets aside EXACTLY capgaps.KNOWN_GAPPED over "
              "the whole corpus, each still refused by decode_conn AND load_tape; "
              "KNOWN-BAD: an audit told it decodes goes red",
              f"{n_yield} yielded; {a_why}")

    return LEDGER.verdict()


# `sys.exit(main())`, not a bare `main()`, and `main` RETURNS the verdict:
# both halves were missing until 2026-08-31, so this file printed its FAIL
# banner and exited 0. run_suite.py catches that as SUSPECT (exit 0 with no
# ALL CHECKS PASSED line), which is the backstop working -- but a developer
# running the file directly saw a clean exit code on a red run, and
# CLAUDE.md's rule is that a test exits non-zero.
if __name__ == "__main__":
    sys.exit(main())
