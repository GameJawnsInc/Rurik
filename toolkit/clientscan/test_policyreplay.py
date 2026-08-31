"""policyreplay.py: the offline policy bench, its fidelity gate, and the
gate's own ability to fail.

The bench exists because one offline counterfactual (the sec.0.16 literal
candidate: 2 of 24 fires survive) was worth more than every live refutation
that week cost. What this file refuses to let rot: the ENGINE's cell
semantics (fire / rate-hold / expiry / late-fire-on-stop / 0x003D void /
newest-wins overwrite / the geometry dest-clear pairing), the FIDELITY GATE
passing on a synthetic log authored to the shipped semantics AND on both
real 2026-08-26 logs under the policies they actually shipped with, the
gate FAILING when a constant is perturbed (a gate that cannot go red is not
a gate -- grantsim's C3 lesson), and the negative control: the refuted
bare-hold candidate must still suppress 22 of 24 on the 113824 log, the
number that killed it.

The synthetic section runs on a bare machine; the real-log sections skip
loudly without the vault. Floor from the green run, per the house rule.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))

import checks          # noqa: E402
import policyreplay    # noqa: E402

# MEASURED from the real green run on 2026-08-26: 14 checks (10 synthetic +
# 4 against the two vault logs). Set AT the run -- zero headroom. (History:
# the author first declared 16 from a head-count before running; the run
# said 14 -- the same defect test_d1lead's header records, now this file's
# too. Count from the run, never the head.)
LEDGER = checks.Ledger("policyreplay: the offline policy bench", floor=14)
check = checks.adopt(LEDGER)


def _row(**kw):
    return json.dumps(kw)


def synthetic_log(path):
    """A log authored to the sec015 shipped semantics, one cell each:
    A fires clean; B rate-holds then expires; C fires over the shared
    clock (a zero-lead fire at t=4); D rate-holds then is VOIDED by an
    0x003D; E fires; F rate-holds and is OVERWRITTEN by G; G fires LATE
    off the flush at the t=8.1 batch (the 7.6 stop cleared the
    outstanding flag without voiding); H fires with a geometry
    click_verdict row between its decode and its verdict (the dest-clear
    pairing)."""
    rows = [
        _row(kind="position_report", accepted=True, source="0x003D",
             reported=[0.0, 0.0], t=1.0),
        _row(kind="decoded", opcode=62, t=2.0),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=True, reason="grant", dest=[100.0, 0.0], t=2.0),
        _row(kind="decoded", opcode=62, t=2.2),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=False, reason="rate-limited", dest=[200.0, 0.0], t=2.2),
        _row(kind="grant_verdict", deferred=True, fired=False,
             reason="pending-expired", dest=[200.0, 0.0], t=3.2),
        _row(kind="grant_verdict", arm="zero-lead", fired=True,
             reason="zero-lead", dest=[50.0, 50.0], t=4.0),
        _row(kind="decoded", opcode=62, t=5.0),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=True, reason="grant", dest=[300.0, 0.0], t=5.0),
        _row(kind="decoded", opcode=62, t=5.3),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=False, reason="rate-limited", dest=[400.0, 0.0], t=5.3),
        _row(kind="position_report", accepted=True, source="0x003D",
             reported=[10.0, 0.0], t=5.6),
        _row(kind="grant_verdict", deferred=True, fired=False,
             reason="voided-by-report", arm="click-d1",
             dest=[400.0, 0.0], t=5.6),
        _row(kind="decoded", opcode=62, t=7.0),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=True, reason="grant", dest=[500.0, 0.0], t=7.0),
        _row(kind="decoded", opcode=62, t=7.2),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=False, reason="rate-limited", dest=[600.0, 0.0], t=7.2),
        _row(kind="decoded", opcode=62, t=7.4),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=False, reason="rate-limited", dest=[700.0, 0.0], t=7.4),
        _row(kind="position_report", accepted=True, source="0x0047",
             reported=[20.0, 0.0], t=7.6),
        _row(kind="grant_verdict", deferred=True, fired=True,
             reason="deferred-grant", dest=[700.0, 0.0], t=8.1),
        _row(kind="position_report", accepted=True, source="0x0047",
             reported=[30.0, 0.0], t=8.1),
        _row(kind="decoded", opcode=62, t=12.0),
        _row(kind="click_verdict", fired=False, reason="geo-stale",
             dest=[800.0, 0.0], d1_passthrough=True, t=12.0),
        _row(kind="grant_verdict", arm="click-d1", deferred=False,
             fired=True, reason="grant", dest=[800.0, 0.0], t=12.0),
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")


def main():
    print("1. the engine's cells, on the authored log (no vault)")
    td = tempfile.mkdtemp()
    log = os.path.join(td, "synthetic.jsonl")
    synthetic_log(log)
    streams = policyreplay.build_streams(policyreplay.load_log(log))
    check(len(streams["pairs"]) == 8
          and [g["reason"] for _c, g, _geo in streams["pairs"]]
          == ["grant", "rate-limited", "grant", "rate-limited", "grant",
              "rate-limited", "rate-limited", "grant"],
          "eight decoded clicks pair 1:1 with immediate verdict rows, "
          "reasons in authored order",
          "a mispairing dates one click's decision with another's row -- "
          "every downstream count inherits it")
    geos = [geo for _c, _g, geo in streams["pairs"]]
    check(geos == [False] * 7 + [True],
          "the geometry flag pairs ONLY the click with a click_verdict "
          "row between decode and verdict",
          "the geometry branch clears state['dest'] before falling "
          "through (authsrv :15853) -- the P-17 log was irreproducible "
          "until this was modelled; a wrong pairing re-hides it")
    out = policyreplay.replay(streams, policyreplay.POLICIES["sec015"])
    check(len(out["fired"]) == 4
          and [round(t) for t, _d in out["fired"]] == [2, 5, 7, 12],
          "A, C, E, H fire immediately (C over the shared clock a "
          "zero-lead fire advanced at t=4)",
          "the shared grant clock is the two-arms-one-floor bound; a "
          "private clock here would let the replay fire pairs the real "
          "server never could")
    check(len(out["fired_late"]) == 1
          and abs(out["fired_late"][0][1] - 8.1) < 0.2,
          "G fires LATE off the flush at the 8.1 batch -- the 7.6 stop "
          "cleared the outstanding flag WITHOUT voiding",
          "the 0x0047-clears-0x003D-voids asymmetry is the whole "
          "wins-late branch; collapsing them kills every late fire")
    check(len(out["expired"]) == 1
          and abs(out["expired"][0][1] - 3.2) < 0.05,
          "B expires at held+1.0s exactly",
          "the expiry is retail's goes-unanswered branch; its clock is "
          "the pending age, not the poll instant")
    check(len(out["voided"]) == 1 and len(out["overwritten"]) == 1,
          "D is voided by the 0x003D; F is overwritten by G, newest-wins",
          "the void is F-A's surviving core and the overwrite is the "
          "coalescing half of Rule 2 -- each cell exactly once in the "
          "authored log, so a count drift names its cell")

    print("\n2. the fidelity gate -- and its ability to go red")
    ok, detail = policyreplay.fidelity(streams, out)
    check(ok is True,
          "FIDELITY PASS: the shipped policy reproduces the authored "
          "log's own record 1:1",
          "the gate is the tool's standing to predict anything; the "
          "authored log IS the shipped semantics, so a fail here is an "
          "engine bug")
    cf = policyreplay.counterfactual(streams, out)
    check(len(cf["survive"]) == 5 and not cf["suppressed"] and not cf["new"],
          "counterfactual against itself: 5 survive, none suppressed, "
          "none new",
          "survive must count late fires too -- G is a real fire the "
          "log records as deferred")
    old = policyreplay.GRANT_MIN
    try:
        policyreplay.GRANT_MIN = 0.1
        out2 = policyreplay.replay(streams,
                                   policyreplay.POLICIES["sec015"])
        ok2, _ = policyreplay.fidelity(streams, out2)
        check(ok2 is False,
              "perturbing the rate floor turns the gate RED (B fires "
              "under a 0.1s floor and the replay diverges from the "
              "record)",
              "a gate that cannot fail is not a gate -- grantsim's C3 "
              "anti-paraphrase discipline; this cell proves the replay "
              "runs the constant, not a story about it")
    finally:
        policyreplay.GRANT_MIN = old
    out3 = policyreplay.replay(streams, policyreplay.POLICIES["bare-hold"])
    ok3, _ = policyreplay.fidelity(streams, out3)
    check(ok3 is False,
          "the refuted bare-hold candidate diverges from the sec015 "
          "record on the same log",
          "two policies agreeing on every log would mean the replay "
          "cannot distinguish policies at all")

    print("\n3. the real logs (skips loudly without the vault)")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE))))
    import vaultpath   # noqa: E402
    g1 = vaultpath.vault_path("captures", "gamesrv",
                              "authsrv-20260826T113824-c1.jsonl")
    g2 = vaultpath.vault_path("captures", "gamesrv",
                              "authsrv-20260826T143111-c1.jsonl")
    if not os.path.exists(g1):
        # Two arguments, not one. This read `LEDGER.skip("real log %s missing")`
        # until 2026-08-31 and `Ledger.skip` takes (label, why), so the first
        # machine to reach it -- any machine with no vault -- got a TypeError
        # instead of the declared skip, and the file died with a traceback
        # rather than the verdict this branch exists to produce. Same defect,
        # same day, in test_castcycle.py's two skips.
        LEDGER.skip("3a. the sec015 real log",
                    "missing %s -- the capture corpus is vault-only, so this "
                    "section measures nothing on this machine" % g1)
    else:
        s1 = policyreplay.build_streams(policyreplay.load_log(g1))
        o1 = policyreplay.replay(s1, policyreplay.POLICIES["sec015"])
        ok1, d1 = policyreplay.fidelity(s1, o1)
        check(ok1 is True and len(o1["fired"]) == 24
              and len(o1["expired"]) == 7,
              "113824 under its own sec015 policy: FIDELITY PASS, "
              "24 fires, 7 expiries",
          "the wall-phase run's click record, reproduced by the "
              "committed engine -- the scratchpad original's own "
              "cross-check, now standing")
        ob = policyreplay.replay(s1, policyreplay.POLICIES["bare-hold"])
        cfb = policyreplay.counterfactual(s1, ob)
        check(len(cfb["survive"]) == 2 and len(cfb["suppressed"]) == 22,
              "the negative control stands: bare-hold suppresses 22 of "
              "24 on 113824 -- the number that killed the sec.0.16 "
              "literal candidate offline",
              "if this drifts, either the engine changed or the corpus "
              "did; the corpus is frozen, so it names an engine change")
    if not os.path.exists(g2):
        LEDGER.skip("3b. the sec017 real log",
                    "missing %s -- the capture corpus is vault-only, so this "
                    "section measures nothing on this machine" % g2)
    else:
        s2 = policyreplay.build_streams(policyreplay.load_log(g2))
        o2 = policyreplay.replay(s2, policyreplay.POLICIES["sec017"])
        ok2r, d2 = policyreplay.fidelity(s2, o2)
        check(ok2r is True and len(o2["fired"]) == 64
              and len(o2["expired"]) == 9,
              "143111 under its own sec017 policy: FIDELITY PASS, "
              "64 fires, 9 expiries -- and this PASS required modelling "
              "the geometry branch's dest-clear",
              "the gate DISCOVERED that clear (sec.0.19): without it the "
              "replay suppressed 48 of 64 real fires. The pin keeps the "
              "discovery from un-happening")
        n_geo = sum(1 for _c, _g, geo in s2["pairs"] if geo)
        check(len(s2["pairs"]) == 179 and n_geo == 126,
              "the P-17 log pairs 179 clicks, 126 geometry-flagged "
              "(87/87 in the first 496s -- the cells the owner played)",
              "the geometry branch's dest-clear voided the sec.0.17 leg "
              "bound on every flagged click; the 53 clean clicks the "
              "grown log adds fired with the modelled leg already "
              "expired -- both facts ride this pin, and the fidelity "
              "PASS above is what proves the engine reproduces them")

    return LEDGER.verdict()


# `sys.exit(main())`, not a bare `main()`, and `main` RETURNS the verdict:
# both halves were missing until 2026-08-31, so this file printed its FAIL
# banner and exited 0. run_suite.py catches that as SUSPECT (exit 0 with no
# ALL CHECKS PASSED line), which is the backstop working -- but a developer
# running the file directly saw a clean exit code on a red run, and
# CLAUDE.md's rule is that a test exits non-zero.
if __name__ == "__main__":
    sys.exit(main())
