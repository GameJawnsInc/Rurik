"""REALFIX-A2's --d1-lead bundle: the formula, the edge, the cells, the locks.

The bundle's whole verdict lives in an owner run this file cannot perform
(the registered predictions are REALFIX.md sec.0.9 and the startup banner --
P-1's zero-snap warp-recipe A/B above all). What this file CAN refuse to let
rot: the D1 endpoint formula's exactness and its refuse-don't-clamp fallback,
the family-rate edge trigger's whole truth table (including the stop-reset
transition the A1 probe never needed), the composition cells that keep the
run unconfoundable, and the source locks on every site the bundle touches --
the heading-arm gate and slot, the dest swap, the verdict row's arm key, and
the stop-repin's position inside the 0x0047 handler.

What this file deliberately does NOT claim: that the lead is safe (that is
P-1..P-5's job), or that retail's D2 clip is modelled (it is not -- Q7 open,
the lead ships UNCLIPPED by design).
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import authsrv     # noqa: E402
import checks      # noqa: E402

# MEASURED from the real green run on 2026-08-26: 37 checks, no fixture, no
# vault, no client. Set AT the run per the house rule -- zero headroom.
# (History: the author declared 34 from a head-count before running, the run
# said 36 -- the same defect test_familyrate's and test_pcspoof's headers
# record, three for three now. Count from the run, never the head. The
# review pass then added the MUT-7 stop-order pin -> 37; the sec.0.11
# matched-words armer-kill added its truth table and four locks -> 42,
# each re-read off its own green run.)
LEDGER = checks.Ledger("the REALFIX-A2 d1-lead bundle", floor=42)
check = checks.adopt(LEDGER)


class FakeSend:
    """Captures (opcode, values, label) the way the wire would see them."""

    def __init__(self):
        self.sent = []

    def __call__(self, opcode, values, label, quiet=False):
        self.sent.append((opcode, list(values), label))


def main():
    # ---------------------------------------------------------------- 1
    print("1. d1_lead_dest: the formula exactly, and refuse-don't-clamp")
    f = authsrv.d1_lead_dest
    check(f([100.0, 200.0], [766.0, 0.0]) == ([866.5, 200.0], "d1"),
          "axis-aligned: dest = reported + vec2 + 0.5*unit -- the 0.5 term "
          "lands whole on the axis",
          "the +0.5*unit term is the D1 signature the live corpus verified "
          "to 0.0001u; dropping it is invisible to any coarser check")
    d, src = f([0.0, 0.0], [420.0, 560.0])
    check(src == "d1" and abs(d[0] - 420.3) < 1e-9
          and abs(d[1] - 560.4) < 1e-9,
          "diagonal at the band floor exactly: |(420,560)| = 700.0 "
          "(inclusive), unit = (0.6,0.8), dest = (420.3, 560.4)",
          "a wrong normalization (0.5*vec2 instead of 0.5*unit) reads "
          "plausibly on axis-aligned vectors and only a diagonal catches "
          "it; the same row pins the floor boundary as >= not >")
    check(f([100.0, 200.0], [0.0, 0.0]) == ([100.0, 200.0], "fallback"),
          "a zero vec2 falls back to the zero-lead point",
          "unit() of a near-zero vector amplifies noise into a direction; "
          "the degenerate case must refuse, not invent a heading")
    check(f([100.0, 200.0], [-1.9969178438186646, 0.0])
          == ([100.0, 200.0], "fallback"),
          "the corpus's ONE mid-magnitude outlier (|v|=1.997, 1 of 15,285 "
          "c2s rows -- the 2026-08-26 review's census) falls back",
          "the D1 formula is bit-verified only on the 765-768 proposal "
          "band; a mid-magnitude 'd1' row would be a short lead nobody "
          "registered wearing the registered label (REV-1)")
    check(f([100.0, 200.0], [699.99, 0.0])[1] == "fallback"
          and f([100.0, 200.0], [769.0, 0.0])[1] == "d1"
          and f([100.0, 200.0], [769.01, 0.0])[1] == "fallback",
          "the band is [700.0, 769.0], both edges pinned: just-under "
          "falls back, the inclusive ceiling leads, just-over falls back",
          "a vec2 outside the verified band is refused; CLAMPING it would "
          "still send a wrong destination -- the fallback sends the "
          "zero-lead point instead, and the row records which")
    check(f([100.0, 200.0], [float("nan"), 0.0])[1] == "fallback",
          "a NaN component falls back",
          "hypot(nan) is nan, every comparison is False, and without the "
          "isfinite gate the nan would ride into struct.pack")
    check(f([100.0, 200.0], None)[1] == "fallback"
          and f([100.0, 200.0], [1.0])[1] == "fallback",
          "a malformed vec2 (None, wrong arity) falls back instead of "
          "raising",
          "the helper runs inside the connection handler; a TypeError "
          "there kills the session for one bad report")
    check(authsrv.D1_LEAD is False,
          "D1_LEAD ships False (off)",
          "an experiment lever that defaults on is a policy nobody ruled")

    # ---------------------------------------------------------------- 2
    print("\n2. the family edge: send on change, hold on same, reset on stop")
    snd, state = FakeSend(), {}
    authsrv._a2_family_rate(snd, state, 1)
    check(len(snd.sent) == 1 and snd.sent[0][1][1:] == [1.0, 1]
          and snd.sent[0][2].startswith("A2 FAMILY-RATE"),
          "first family sends [1.0, 1] under the A2 label, not the A1 "
          "probe label",
          "a capture whose 0x002B rows say FAMILY-RATE PROBE while the "
          "banner says A2 is the unattributable-capture defect")
    authsrv._a2_family_rate(snd, state, 1)
    check(len(snd.sent) == 1,
          "same family again sends NOTHING -- the edge holds",
          "A1 proved the store persists; a same-family re-send is dose "
          "without information, and retail's own 0x002B is a change "
          "signal (97.6% of change bursts vs 11.5% same-family)")
    authsrv._a2_family_rate(snd, state, 4)
    check(len(snd.sent) == 2 and snd.sent[1][1][1:] == [0.66, 4],
          "a family change sends the new float",
          "the edge is the policy; a missed change leaves the copy "
          "reckoning at the old family's speed for the whole leg")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv._a2_family_rate(snd, state, 9)
    check(len(snd.sent) == 2 and "UNKNOWN movementType" in buf.getvalue(),
          "an unknown mt sends nothing and prints (the sender's own loud "
          "skip)",
          "mt 9 is retail's SERVER-only stop sentinel; a client report "
          "carrying it is a census-breaking event, not a table row to "
          "guess")
    authsrv._a2_family_rate(snd, state, 4)
    check(len(snd.sent) == 2,
          "and the unknown mt did NOT advance the edge -- family 4 is "
          "still the last SENT family, so no re-send",
          "advancing the edge on a skipped send would silently drop the "
          "next real family's float")
    state["a2_family_sent"] = None
    authsrv._a2_family_rate(snd, state, 4)
    check(len(snd.sent) == 3 and snd.sent[2][1][1:] == [0.66, 4],
          "after the stop-reset (a2_family_sent = None) the SAME family "
          "re-sends",
          "the stop-repin's [1.0, 9] overwrites sync +0x60, so the next "
          "leg must re-assert its family even unchanged -- the one "
          "transition the A1 probe never needed, and the reason the "
          "stop arm writes None")
    check(authsrv.a2_matched_field4(22, 22) == (22, False)
          and authsrv.a2_matched_field4(22, 0) == (22, True)
          and authsrv.a2_matched_field4(0, 26) == (0, True),
          "the matched-words override (sec.0.11's armer-kill): equal "
          "words pass through unmarked, a differing carry is REPLACED by "
          "the ground plane and marked",
          "plane-carry's stale word across a seam is stage 1 of the "
          "input lock (the drawn body snaps onto the stale-stamped copy "
          "and the fence shuts); retail's nonzero pairs are bit-identical "
          "222/222, so matched IS the retail contract")

    # ---------------------------------------------------------------- 3
    print("\n3. composition cells: the lattice around the bundle")
    comp = authsrv.zero_lead_composition
    for kw, frag in [
            (dict(cancel_answer="suppress"), "--d1-lead and --cancel-answer"),
            (dict(family_rate_probe=True), "--d1-lead and --family-rate-probe"),
            (dict(checksum_probe="model"), "--d1-lead and --checksum-probe"),
            (dict(pc_spoof=26), "--d1-lead and --pc-spoof"),
            (dict(stop_answer="ack"), "--d1-lead and --stop-answer"),
            # arrival_carry rides with plane_carry=False: with BOTH carries
            # on, the older plane-vs-arrival cell fires first (correctly --
            # that pair is refused on its own ground), so the d1 cell's own
            # text is reachable only when plane_carry is off.
            (dict(arrival_carry=True, plane_carry=False),
             "--d1-lead and --arrival-carry"),
            (dict(click_sweep=True), "--d1-lead and --click-sweep")]:
        kw.setdefault("plane_carry", True)
        r, _ = comp(zero_lead=True, d1_lead=True, **kw)
        check(r is not None and frag in r,
              f"refused pairwise: {frag}",
              "each pair is either two policies for one wire field/site or "
              "a diagnostic inside a policy run -- the cell text carries "
              "the specific ground")
    r, _ = comp(zero_lead=False, d1_lead=True)
    check(r is not None and "--d1-lead requires --zero-lead" in r,
          "requires zero-lead (the modifier has no site without it)",
          "the inert-flag defect: an on-looking log over a server running "
          "the shipped default")
    r, _ = comp(zero_lead=True, plane_carry=False, d1_lead=True)
    check(r is not None and "--d1-lead requires --plane-carry" in r,
          "requires plane-carry (plane truth is term 3 of the bundle)",
          "running the lead without it re-creates the fake-label hazard "
          "sec.0.5-0.8 decoded")
    r, _ = comp(zero_lead=False, d1_lead=True, cancel_answer="suppress")
    check(r is not None and "--d1-lead and --cancel-answer" in r,
          "with both violations pending, the pairwise cell outranks the "
          "requires cell",
          "the family-rate precedent: 'you passed two levers' is the more "
          "useful refusal, and ordering is what mutations flip silently")
    r, notes = comp(zero_lead=True, plane_carry=True, d1_lead=True)
    check(r is None and any("--d1-lead" in n and "BUNDLE" in n
                            for n in notes),
          "the registered shape itself is ALLOWED, with the note naming "
          "the bundle and the stop-repin's era-audit ground",
          "the gamesrv header carries no argv; the note plus the verdict "
          "rows' lead_src are how a later session attributes the run")

    # ---------------------------------------------------------------- 4
    print("\n4. source locks: every site the bundle touches, position-pinned")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    check(src.count("D1_LEAD = False") == 1
          and src.count("D1_LEAD = True") == 1
          and "d1_lead=a.d1_lead" in src,
          "the global defaults False, main() rebinds exactly once, and the "
          "flag is threaded into the composition matrix",
          "the unpinned-rebind lesson, third time as precedent")
    check(src.count("if D1_LEAD and zero_ok:") == 1,
          "ONE speed-truth gate on the zero-lead verdict",
          "a second gate doubles the dose; an ungated call puts a 0x002B "
          "outside every witnessed burst shape")
    a1_gate = src.index("if FAMILY_RATE_PROBE and zero_ok:")
    a2_gate = src.index("if D1_LEAD and zero_ok:")
    # .find, not .index: a relocated gate must FAIL this check, not crash
    # the suite with a ValueError (the review's MUT-4 robustness note --
    # a crash is still red, but a [FAIL] names the broken thing).
    hg_after = src.find("if HEADING_GRANT:", a2_gate)
    check(a1_gate < a2_gate and hg_after != -1 and a2_gate < hg_after,
          "the A2 gate sits in the SAME witnessed burst slot -- after the "
          "A1 gate, before the first grant block",
          "relocated below the 0x0029 the wire shows 0x0029-then-0x002B, "
          "a shape with zero retail witnesses, and every count stays "
          "green")
    check("_a2_family_rate(send, state, moving)" in src,
          "and the edge call passes the report's own movementType verbatim",
          "hardcoded, every send is [1.0, 1] -- the click-confound "
          "signature -- and no count reddens")
    check(src.count("a2_dest, a2_src = d1_lead_dest(") == 1,
          "ONE dest-computation site routes through d1_lead_dest",
          "a second computation site is two formulas for one wire point")
    i_spoof = src.index("zl_plane_cur, pcs_fired = pc_spoof_field4(")
    i_d1 = src.index("a2_dest, a2_src = d1_lead_dest(")
    i_verdict = src.index('rec.event("grant_verdict"', i_d1)
    check(i_spoof < i_d1 < i_verdict,
          "computed after the plane policy resolves and BEFORE the verdict "
          "row, so the row records the point that goes out",
          "below the verdict, the row logs reported while the wire "
          "carries the lead -- the unattributable-capture defect")
    check("lead_src=(a2_src if zero_ok" in src,
          "the verdict row carries lead_src (d1/fallback/null)",
          "the census key for P-1..P-5's scoring; null on a refusal like "
          "every field-4 fact")
    check(src.count("a2_matched_field4(") == 3,
          "the matched-words helper has exactly its def and TWO call "
          "sites -- the heading arm and the stop-repin",
          "a third caller would rewrite another arm's field 4 under a "
          "flag whose charter is the d1 bundle; a missing caller leaves "
          "one of the two send paths carrying the stale word the lock "
          "needs")
    i_match = src.index("zl_plane_cur, a2_matched = (")
    check(i_spoof < i_match < i_d1 < i_verdict,
          "the heading-arm override sits AFTER the carry/spoof "
          "resolution, BEFORE the dest compute and the verdict row -- "
          "the row records the matched word that actually goes out",
          "above the carry it would be overwritten back to stale; below "
          "the row, plane_cur would log the stale word while the wire "
          "carried the match -- the unattributable-capture defect")
    check("pc_matched=(a2_matched" in src,
          "and the row carries pc_matched, sec.0.11's verification key",
          "the V-8 run's exposure floor counts these rows; without the "
          "key, exposure is reconstructed from a policy someone assumes "
          "was running")
    check('+ (" matched" if a2_stop_matched else "")' in src,
          "the stop-repin label marks its own overrides",
          "the repin's stale word was the lock's perfect DETECTOR "
          "(28/28); the marker preserves that detector's trace under "
          "the fix")
    check("zl_point = (a2_dest" in src
          and "plane, zl_plane_cur]," in src,
          "the ONE 0x0029 send consumes a2_dest through zl_point and its "
          "field 4 still reads zl_plane_cur verbatim",
          "a second 0x0029 send site is the two-arms-one-clock defect; a "
          "private field-4 expression at the send strands the plane "
          "policy inert")
    check(src.count("A2 STOP-REPIN (") == 1 and src.count("[a2-stop]") == 1,
          "ONE stop-repin site, ONE stop speed-send, labelled (the bare "
          "phrase also appears in the banner's READOUT line, which is why "
          "the lock counts the send's own f-string prefix)",
          "the stop arm is a grant on the shared clock; a second site "
          "doubles the ack invisibly")
    i_cw_stop = src.index("CANCELWALK STOP (")
    i_a2_stop = src.index("A2 STOP-REPIN")
    i_r6 = src.index('if STOP_ANSWER == "ack":', i_a2_stop)
    check(i_cw_stop < i_a2_stop < i_r6,
          "the stop-repin sits between CANCEL_STOP's scoped re-pin and the "
          "R6 bare-ack inside the 0x0047 handler",
          "position is what distinguishes 'generalizes the scoped shape' "
          "from 'a new send in an unaudited slot'; the composition matrix "
          "refuses cancel-answer and stop-answer beside it, so at most "
          "one stop reply is live in any run")
    a2_stop_block = src[i_a2_stop:i_r6]
    check('state["a2_family_sent"] = None' in a2_stop_block,
          "and the stop arm resets the family edge inside its own block",
          "the [1.0, 9] it just sent overwrote sync +0x60; without the "
          "reset the next leg's same-family float is never re-asserted "
          "and the copy walks a whole leg at 1.0")
    # The review's MUT-7: the one mutation that survived every lock was
    # swapping the stop-repin's two sends. Retail's grammar is 0x0029
    # ALWAYS LAST (3,023 of 3,071 bursts) and the stop census shows the
    # 0x002B companion FIRST at 131/131 echoes -- so the order is part of
    # the registration, and it gets its own pin.
    i_stop_spd = src.find("[a2-stop]")
    i_stop_pin = src.find("A2 STOP-REPIN (")
    check(i_stop_spd != -1 and i_stop_pin != -1
          and i_cw_stop < i_stop_spd < i_stop_pin < i_r6,
          "the stop arm's 0x002B goes out BEFORE its 0x0029 -- the "
          "[a2-stop] speed send precedes the A2 STOP-REPIN grant inside "
          "the block",
          "swapped, the wire shows a stop burst retail has zero witnesses "
          "for (0x0029 then 0x002B), the client bakes the re-pin BEFORE "
          "the [1.0,9] lands in +0x60, and every count stays green -- the "
          "review's one surviving mutation")

    LEDGER.verdict()


if __name__ == "__main__":
    main()
