#!/usr/bin/env python3
"""THE SUPPRESSION COUNTERFACTUAL, and the four ways a counterfactual lies.

    python toolkit/clientscan/test_grantsuppress.py

WHAT THIS IS REALLY CHECKING. `grantsuppress.py` answers "what would refusing
the grant have done?" against captures already on disk, BEFORE the owner plays
the reproduction again. That question has four failure modes this arc has
already paid for, and each has a section here.

  1. A CONTROL THAT JUDGES ZERO ROWS. Tonight's two control captures carry
     ZERO grants, so "the rule suppressed nothing there" is a fact about the
     server -- it answered no click -- and not a fact about the rule. §7 pins
     that the tool REFUSES the 0/0 share by name, and §8 puts the real control
     on a population with a denominator: the five CLICKS in `20260820T182934`,
     of which the rule must call zero keyboard-driving. §9 is the mutation that
     proves that check can fail -- delete the stop term and it goes 0/5 -> 1/5.
  2. A NUMBER THAT IS TRUE AND FREE. "4 of 5 jumps had a grant inside 0.5 s" is
     nearly guaranteed when grants arrive every 0.150 s. §11 pins the baseline
     over the SAME population (63% of the reproduction's own report instants),
     §12 pins the rotation control, and §13 pins that the default-build capture
     -- where the baseline is 10% -- is the one where the time arm carries
     information. A statistic that survives its own shuffle is measuring the
     procedure.
  3. A PRIVATE COPY OF SOMEBODY ELSE'S BAR. §3 asserts the jump population is
     `movesync.hard_steps` BY IDENTITY, not by value, because a fix scored on a
     friendlier bar than the defect is how this arc already shipped one wrong
     number (`movesync` header, defect 2).
  4. A LOOKUP THAT MISSES ANSWERING `False`. §6 pins the fourth bucket:
     a causal grant time absent from the suppression table lands in UNKNOWN and
     never in KEPT. `movesync.state_fields` refusing to return 0 for a field it
     could not read is the same rule, and this file's four buckets are asserted
     to PARTITION on every capture rather than merely to be counted.

AND ONE THING THAT IS NOT ABOUT THIS FILE. §10 checks the rule's only free
parameter against the client's own report cadence: a straight keyboard hold in
`20260820T182554` reports every 1.80-1.82 s, so a window of 1.0 s -- which is
`authsrv.py`'s own `fresh` constant and the number a reviewer reaches for --
leaves 10 of that capture's 15 intra-hold intervals uncovered. That is
grant-shaped leakage in exactly the posture (run straight, spam-click) the
owner is most likely to try next, and it is the actionable half of the
parameter.

AND THE CAVEAT §14 PUTS UNDER ITS OWN HEADLINE. On the reproduction the rule
suppresses ALL 140 grants, so "every grant in the causal set would have been
suppressed" is true of any causal set that is not empty and the per-jump
counterfactual cannot come out differently. §14 asserts the tool prints that
under the 5-of-5, and asserts it does NOT print it for `20260819T145717`, where
10 grants survive the rule and the number is therefore a measurement. A caveat
printed everywhere is a caveat nobody reads.

Sections 1-6 are pure logic and run on a bare machine. 7-15 replay
`captures/gamesrv` and declare one shared `LEDGER.skip`.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks         # noqa: E402
import grantsuppress as G  # noqa: E402
import movesync       # noqa: E402
import vaultpath      # noqa: E402

# MEASURED from two real green runs on 2026-08-20: 85 checks with the vault
# present, 29 with `RURIK_VAULT` pointed at an empty directory (1 declared
# skip). 29 is the bare-machine subset and is the floor -- read off the run,
# never off a count in anybody's head, which is the slip `test_movesync`
# records against itself. The first draft of this line guessed 30 and the
# bare-machine run went red on the guess, which is the guard working.
LEDGER = checks.Ledger("grant suppression, priced against captures we have",
                       floor=29)
check = checks.adopt(LEDGER)


# --- fixtures ----------------------------------------------------------------
def cs(heads, stops=(), clicks=()):
    """One control stream, by hand. `heads` is [(t, movementType)]."""
    return {"heads": sorted(heads), "stops": sorted(stops),
            "clicks": sorted(clicks), "malformed": 0,
            "mt_zero": sum(1 for _t, m in heads if not m),
            "mt_values": sorted({m for _t, m in heads})}


def jump(t0, t, p, dist=1000.0, window_ts=(), nearest=None, control=None):
    """One `attribute_jumps` row, by hand."""
    return {"t0": t0, "t": t, "dist": dist, "dt": t - t0,
            "speed": dist / (t - t0), "in_window": len(window_ts),
            "window_ts": list(window_ts), "grant_age": None,
            "nearest": nearest, "control": control}


def main():
    print("=" * 78)
    print("GRANT SUPPRESSION -- the counterfactual, and its controls")
    print("=" * 78)

    # --- 1 ------------------------------------------------------------------
    print("\n1. the classifier: RECENCY is the parameter and it decides")
    s = cs([(10.0, 1)])
    check(G.keyboard_driving(s, 10.5, 2.0)[0],
          "a heading 0.5s ago, W=2.0 -> driving")
    check(not G.keyboard_driving(s, 13.0, 2.0)[0],
          "the same heading 3.0s ago, W=2.0 -> NOT driving",
          "the window is the only term that moves with W")
    check(G.keyboard_driving(s, 13.0, 5.0)[0],
          "...and W=5.0 takes the same instant the other way")
    check(G.keyboard_driving(s, 13.0, 2.0)[1] == "stale-heading",
          "and it names the term that decided (`stale-heading`)")
    check(not G.keyboard_driving(s, 9.0, 2.0)[0]
          and G.keyboard_driving(s, 9.0, 2.0)[1] == "no-heading-yet",
          "before the first heading -> NOT driving, named `no-heading-yet`",
          "an empty prefix must refuse rather than index [-1] into nothing")

    # --- 2 ------------------------------------------------------------------
    print("\n2. the classifier: THE STOP TERM, which is the other one that can "
          "decide")
    s2 = cs([(10.0, 1)], stops=[10.2])
    check(not G.keyboard_driving(s2, 10.5, 2.0)[0],
          "a 0x0047 between the heading and t -> NOT driving")
    check(G.keyboard_driving(s2, 10.5, 2.0)[1] == "stopped-since",
          "...named `stopped-since`, so the term is countable")
    check(G.keyboard_driving(cs([(10.0, 1)], stops=[9.5]), 10.5, 2.0)[0],
          "a stop BEFORE the heading does not fire -- the interval is (h, t]",
          "a stop that predates the heading has already been superseded by it")
    check(G.keyboard_driving(cs([(10.0, 1)], stops=[10.6]), 10.5, 2.0)[0],
          "and a stop AFTER t does not reach back")
    check(not G.keyboard_driving(cs([(10.0, 0)]), 10.5, 2.0)[0],
          "movementType 0 -> NOT driving",
          "the term is INERT on real data (0 never appears in 7,988 records) "
          "and is tested here so its absence in the field is a fact about the "
          "client, not about this code")

    # --- 3 ------------------------------------------------------------------
    print("\n3. the jump population is movesync's, BY IDENTITY")
    check(G.movesync is movesync,
          "grantsuppress imports the same movesync module object")
    src = open(os.path.join(HERE, "grantsuppress.py"), encoding="utf-8").read()
    check("def hard_step" not in src and "HARD_JUMP_SPEED =" not in src
          and "HARD_JUMP_UNITS =" not in src,
          "and defines no hard-jump bar of its own",
          "a private copy of the bar is how a fix gets scored on a friendlier "
          "one than the defect")
    # THE PROSE MENTIONS `authsrv.py` REPEATEDLY AND MUST, so the check is on
    # the IMPORT and not on the substring: a naive `"authsrv" not in src` was
    # red for the docstring, which is a check failing for a reason that has
    # nothing to do with what it is guarding.
    check(not any(ln.strip().startswith(("import authsrv", "from authsrv"))
                  for ln in src.splitlines()),
          "and never imports the server it is pricing a change to",
          "the docstring names authsrv.py a dozen times; the check is on the "
          "import statement")
    check("authsrv" not in sys.modules,
          "...and importing grantsuppress did not pull the server in "
          "transitively")
    check(G.OP_MOVE_TO_POINT is movesync.OP_MOVE_TO_POINT
          and G.OP_SET_HEADING is movesync.OP_SET_HEADING
          and G.OP_CANCEL_REPORT is movesync.OP_CANCEL_REPORT,
          "and takes its opcodes from movesync rather than re-spelling them")

    # --- 4 ------------------------------------------------------------------
    print("\n4. suppression tallies: every count sums to its own denominator")
    grants = [(10.5, "click"), (13.0, "click"), (10.6, "heading")]
    sup = G.suppression(cs([(10.0, 1)]), sorted(grants), 2.0)
    check(sup["n"] == 3 and sup["suppressed"] + sup["kept"] == sup["n"],
          f"n = {sup['n']}, suppressed + kept = n")
    check(sum(a["n"] for a in sup["by_arm"].values()) == sup["n"],
          "the per-arm denominators sum to n")
    check(sum(a["suppressed"] for a in sup["by_arm"].values())
          == sup["suppressed"],
          "and the per-arm numerators sum to the total")
    check(sum(sup["by_reason"].values()) == sup["n"],
          "and every grant lands in exactly one reason bucket")
    check(sup["suppressed"] == 2 and sup["by_arm"]["click"]["suppressed"] == 1,
          "2 of 3 suppressed, 1 of the 2 clicks -- the 13.0 one is stale",
          "an arithmetic identity that holds at every value is not a check; "
          "this pins the actual answer")

    # --- 5 ------------------------------------------------------------------
    print("\n5. the density null and the rotation control, where the answer is "
          "known")
    reps = [(float(i) * 0.25, [0.0, 0.0]) for i in range(41)]   # 0.00 .. 10.00
    gr = [(t, [0.0, 0.0]) for t in (1.0, 1.1, 1.2, 1.3)]
    null = G.density_null(reps, gr, 0.5)
    check(null["n"] == 40, f"the null's denominator is every interval ({null['n']})")
    check(null["hits"] == 4,
          f"4 of 40 report instants have a grant inside 0.5s ({null['hits']})",
          "t = 1.00, 1.25, 1.50, 1.75 and no others: 0.75's window [0.25,0.75] "
          "holds no grant and 2.00's [1.50,2.00] holds none either. "
          "Hand-counted -- and the first hand count said 6 and was wrong, "
          "which is why this line pins a number instead of an inequality")
    dense = [(0.05 * i, [0.0, 0.0]) for i in range(200)]
    check(G.density_null(reps, dense, 0.5)["share"] > 0.9,
          "and a dense grant train drives the baseline over 90% -- which is "
          "why the baseline has to be printed beside the count")
    rot = G.rotation_control(reps, gr, [{"t0": 1.0, "t": 1.2, "dist": 1.0,
                                         "dt": 0.2, "speed": 5.0}], 0.5)
    check(len(rot["rows"]) == len(G.ROTATIONS),
          f"the rotation control judges {len(rot['rows'])} offsets")
    check(all(r["judged"] + 0 <= 1 for r in rot["rows"])
          and sum(r["judged"] for r in rot["rows"]) > 0,
          "and judges a non-zero number of rows",
          "a control that silently drops every row is the defect it exists to "
          "catch")

    # --- 6 ------------------------------------------------------------------
    print("\n6. the four buckets PARTITION, and a missing key never scores as "
          "`kept`")
    rep = {"jumps": [jump(1.0, 1.2, None, window_ts=[0.9]),
                     jump(2.0, 2.2, None, window_ts=[]),
                     jump(3.0, 3.2, None, window_ts=[2.9]),
                     jump(4.0, 4.2, None, window_ts=[99.0])],
           "suppression": {"rows": [{"t": 0.9, "suppressed": True},
                                    {"t": 2.9, "suppressed": False}]}}
    rm, kp, un, unk = G.removed_by_rule(rep, G.ATTRIB_NARROW)
    check(len(rm) + len(kp) + len(un) + len(unk) == len(rep["jumps"]),
          "removed + kept + unattributed + unknown = n")
    check(len(rm) == 1 and len(kp) == 1 and len(un) == 1 and len(unk) == 1,
          "one of each, from four jumps built to land in four buckets")
    check(len(unk) == 1,
          "a causal grant time absent from the suppression table -> UNKNOWN",
          "`sup_at.get(t, False)` would have called this one KEPT, which reads "
          "as 'the rule does not help here' when the truth is 'this code could "
          "not tell'")
    j_narrow = jump(1.0, 1.2, None, nearest={"dist": 40.0, "t": 0.5, "age": 0.7,
                                             "point": [0, 0]}, control=10.0)
    check(G.causal_set(j_narrow, G.ATTRIB_NARROW) == [0.5]
          and G.causal_set(j_narrow, G.ATTRIB_WIDE) == [],
          "NARROW and WIDE disagree on a landing 40 u from a grant and 10 u "
          "from where the client had stood",
          "which is why the counterfactual is printed as a bracket")

    # --- the vault sections -------------------------------------------------
    try:
        vaultpath.require_dir("captures", "gamesrv")
        paths = {s: G.capture_path(s) for s in G.ARC_STAMPS}
    except (SystemExit, OSError, G.Refused) as exc:
        LEDGER.skip("sections 7-14 (the six arc captures)",
                    f"cannot reach the corpus: {exc}")
        return LEDGER.verdict()

    reps_ = {s: G.replay(p) for s, p in paths.items()}
    R = reps_[G.REPRO]
    CK = reps_[G.CONTROL_CLICK]
    KB = reps_[G.CONTROL_KBD]
    D = reps_["20260819T145717"]

    # --- 7 ------------------------------------------------------------------
    print("\n7. the two control captures carry ZERO grants, and the tool "
          "REFUSES the 0/0")
    check(CK["suppression"]["n"] == 0 and KB["suppression"]["n"] == 0,
          "20260820T182934 and 20260820T182554 hold 0 player 0x0029 each",
          "so any suppression SHARE over them is 0/0")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = G.print_replay(CK)
    out = buf.getvalue()
    check("REFUSED: 0 grants" in out,
          "the click-only capture prints `REFUSED: 0 grants` by name")
    check(rc == 1, "...and print_replay returns non-zero for it",
          "a refusal that does not reach the exit code is a footnote")
    check("0 of 5 click(s)" in out,
          "while still printing the population it CAN judge (5 clicks)")

    # --- 8 ------------------------------------------------------------------
    print("\n8. THE CONTROL WITH A DENOMINATOR: 5 clicks, 0 of them driving")
    check(CK["clicks"]["n"] == 5,
          f"20260820T182934 holds {CK['clicks']['n']} clicks -- a non-zero "
          f"population to be wrong about")
    check(CK["clicks"]["driving"] == 0,
          f"the rule calls {CK['clicks']['driving']} of 5 keyboard-driving",
          "the owner stopped before every click in that capture, so the rule "
          "must suppress nothing there -- and it CAN come out the other way")
    check(all(G.click_specificity(CK["cs"], w)["driving"] == 0
              for w in G.WINDOW_SWEEP),
          "and 0 of 5 at every W in the sweep "
          f"({G.WINDOW_SWEEP[0]}-{G.WINDOW_SWEEP[-1]}s)",
          "so the specificity is not an artifact of one parameter value")
    check(R["clicks"]["driving"] == R["clicks"]["n"] == 196,
          f"against {R['clicks']['driving']} of {R['clicks']['n']} in the "
          f"reproduction -- the same classifier, the opposite answer")

    # --- 9 ------------------------------------------------------------------
    print("\n9. THE MUTATION: the stop term is load-bearing, measured")
    nostop = dict(CK["cs"])
    nostop["stops"] = []
    check(G.click_specificity(nostop, 1.0)["driving"] == 1,
          "delete the stops from 20260820T182934 and 1 of 5 clicks flips to "
          "driving at W=1.0",
          "the click at t=15.445 sits 0.916s after a heading, INSIDE W=1.0, "
          "and is refused only because a 0x0047 at 14.578 lies between")
    check(G.click_specificity(nostop, G.SHIPPED_LOCAL_WINDOW)["driving"] == 2,
          f"at the SHIPPED W = {G.SHIPPED_LOCAL_WINDOW} the same mutation "
          f"flips 2 of 5",
          "the click at t=106.071 sits 2.39s after a heading, which is inside "
          "3.0s and outside 1.0s -- so the longer the window, the more work "
          "the stop term is doing")
    stopped = sum(1 for r in CK["clicks"]["rows"] if r["why"] == "stopped-since")
    check(stopped == 2,
          f"...and the unmutated run attributes exactly those "
          f"{stopped} to `stopped-since`",
          "the mutation count and the reason tally are two views of one fact "
          "and must agree")
    check(D["suppression"]["by_reason"].get("stopped-since", 0) == 10,
          f"on 20260819T145717 the stop term keeps "
          f"{D['suppression']['by_reason'].get('stopped-since', 0)} of 40 "
          f"grants",
          "so the term is not a one-row curiosity")

    # --- 10 -----------------------------------------------------------------
    print("\n10. THE WINDOW, priced against the client's own straight-hold "
          "cadence")
    g = KB["gaps"]
    check(len(g) == 15, f"20260820T182554 gives {len(g)} intra-hold heading "
                        f"intervals")
    check(1.75 <= G._p(g, 0.5) <= 1.85,
          f"whose p50 is {G._p(g, 0.5):.3f}s -- the client's straight-line "
          f"report mode",
          "the client emits 0x003D on a 1.80s cadence when the heading does "
          "not change, so a shorter window cannot cover a straight hold")
    check(sum(1 for x in g if x > 1.0) == 10,
          f"at W = 1.0 (authsrv's own `fresh` constant) "
          f"{sum(1 for x in g if x > 1.0)} of 15 intervals are UNCOVERED",
          "grant-shaped leakage in exactly the posture the owner is most "
          "likely to try next")
    check(sum(1 for x in g if x > G.MEASURED_WINDOW) == 0,
          f"at this file's own W = {G.MEASURED_WINDOW} it is 0 of 15")
    check(sum(1 for x in g if x > G.SHIPPED_LOCAL_WINDOW) == 0,
          f"and at the SHIPPED W = {G.SHIPPED_LOCAL_WINDOW} it is 0 of 15")
    check(KB["duty"]["share"] >= 0.80,
          f"and the classifier calls {100 * KB['duty']['share']:.0f}% of that "
          f"capture's span DRIVING -- the POSITIVE control",
          "three ~8s W-holds in a 26s span; a classifier that scored this low "
          "would be reading something other than the keyboard")
    check(CK["duty"]["share"] < KB["duty"]["share"],
          f"against {100 * CK['duty']['share']:.0f}% on the click-only "
          f"capture -- the NEGATIVE control, and the two differ")

    # --- 11 -----------------------------------------------------------------
    print("\n11. THE REPRODUCTION: what the rule suppresses, and what it costs")
    check(R["suppression"]["n"] == 140,
          f"20260820T183311 holds {R['suppression']['n']} player grants")
    check(R["suppression"]["suppressed"] == 140,
          f"the rule suppresses {R['suppression']['suppressed']} of 140",
          "the owner held S through the whole click storm, so every grant went "
          "out while the client drove itself")
    check(R["suppression"]["by_arm"]["click"]["n"] == 140,
          "all 140 came from the CLICK arm (the label says so; the agent "
          "filter is the wire bytes)")
    check(all(G.suppression(R["cs"], R["grant_arms"], w)["suppressed"] == 140
              for w in G.WINDOW_SWEEP),
          f"and 140 of 140 at every W in {G.WINDOW_SWEEP}",
          "the headline does not depend on the one free parameter")
    check(len(R["hard"]) == 5,
          f"movesync scores {len(R['hard'])} hard jumps in it")
    inwin = sum(1 for j in R["jumps"] if j["in_window"] > 0)
    check(inwin == 4, f"{inwin} of 5 have a grant inside 0.50s before landing")

    # --- 12 -----------------------------------------------------------------
    print("\n12. ...AND THE BASELINE THAT NUMBER HAS TO BEAT")
    null = R["null"]
    check(null["n"] == 132 and 0.60 <= null["share"] <= 0.66,
          f"{null['hits']} of {null['n']} of the capture's OWN report instants "
          f"({100 * null['share']:.0f}%) also have a grant inside 0.50s",
          "grants arrive every 0.150s in that storm, so the 4-of-5 is very "
          "nearly free")
    check(4.0 / 5.0 - null["share"] < 0.25,
          f"the jumps beat it by only "
          f"{100 * (4.0 / 5.0 - null['share']):.0f} points over n = 5",
          "which is not a result; the SPACE arm below is what discriminates")
    rot = R["rotation"]
    check(sum(r["judged"] for r in rot["rows"]) > 0,
          f"the rotation control judges "
          f"{sum(r['judged'] for r in rot['rows'])} rotated jump-row(s)",
          "a control over zero rows passes by construction and proves nothing")
    hits = sum(r["hits"] for r in rot["rows"])
    judged = sum(r["judged"] for r in rot["rows"])
    check(hits / judged >= 0.55,
          f"and jumps moved to WRONG times still score {hits}/{judged} = "
          f"{100.0 * hits / judged:.0f}%",
          "so on this capture the time arm is grant DENSITY, and this file "
          "asserts that rather than the comfortable reading")

    # --- 13 -----------------------------------------------------------------
    print("\n13. THE SPACE ARM, and the fifth jump")
    fifth = [j for j in R["jumps"] if j["in_window"] == 0]
    check(len(fifth) == 1, "exactly one of the five has NO grant inside 0.50s")
    f = fifth[0]
    check(f["grant_age"] is not None and 5.0 < f["grant_age"] < 5.2,
          f"its nearest grant precedes it by {f['grant_age']:.2f}s")
    check(f["nearest"]["dist"] == 0.0,
          f"and its landing is {f['nearest']['dist']:.3f} u from a point we "
          f"GRANTED {f['nearest']['age']:.2f}s earlier -- bit-identical",
          "so it is not unexplained: it is the +0x48 arrival maturing, which "
          "a 0.50s lookback cannot see by construction")
    check(f["control"] > 1000.0,
          f"against a control (nearest place the client had already stood) of "
          f"{f['control']:.0f} u",
          "the granted point beats that control by ~1,100 u, which the time "
          "arm never could")
    onpoint = [j for j in R["jumps"]
               if j["nearest"] and j["nearest"]["dist"] == 0.0]
    check(len(onpoint) == 2,
          f"{len(onpoint)} of the 5 landings are bit-identical to a granted "
          f"point")

    # --- 14 -----------------------------------------------------------------
    print("\n14. THE COUNTERFACTUAL, bracketed -- and the capture where it is "
          "NOT 100%")
    for stamp, rp in reps_.items():
        if not rp["hard"]:
            continue
        for att in (G.ATTRIB_NARROW, G.ATTRIB_WIDE):
            rm, kp, un, unk = G.removed_by_rule(rp, att)
            if not check(len(rm) + len(kp) + len(un) + len(unk)
                         == len(rp["jumps"]),
                         f"{stamp} / {att}: the four buckets partition "
                         f"{len(rp['jumps'])} jump(s)"):
                break
    rmN = len(G.removed_by_rule(R, G.ATTRIB_NARROW)[0])
    rmW = len(G.removed_by_rule(R, G.ATTRIB_WIDE)[0])
    check(rmN == rmW == 5,
          f"the reproduction: {rmN}-{rmW} of 5 removed under both attributions",
          "every grant in every jump's causal set went out while the client "
          "drove itself")
    dN = G.removed_by_rule(D, G.ATTRIB_NARROW)
    dW = G.removed_by_rule(D, G.ATTRIB_WIDE)
    check(len(dN[0]) == 2 and len(dW[0]) == 3,
          f"the DEFAULT BUILD capture 20260819T145717: {len(dN[0])}-"
          f"{len(dW[0])} of {len(D['jumps'])} removed",
          "THE LOAD-BEARING ROW. The configuration we actually ship keeps most "
          "of its hard jumps under this rule, so 5-of-5 on the reproduction is "
          "a statement about THAT SESSION and not about the build")
    check(len(dN[1]) == 2 and len(dW[1]) == 2,
          f"with {len(dN[1])} plausibly KEPT -- a causal grant survives the "
          f"rule",
          "a counterfactual that removes everything everywhere is not being "
          "asked a question it can fail")
    check(len(dN[2]) >= 2,
          f"and {len(dN[2])} UNATTRIBUTED: no grant in the causal set at all, "
          f"so the rule says nothing about them")
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        G.print_replay(R)
    o2 = buf2.getvalue()
    check("CANNOT COME OUT ANY OTHER WAY HERE" in o2,
          "the reproduction's 5-of-5 is printed WITH the caveat that it cannot "
          "come out otherwise",
          "the rule suppresses all 140 of that capture's grants, so every "
          "non-empty causal set is covered by construction; the caveat belongs "
          "under the number and not in a footnote")
    buf3 = io.StringIO()
    with contextlib.redirect_stdout(buf3):
        G.print_replay(D)
    check("CANNOT COME OUT ANY OTHER WAY HERE" not in buf3.getvalue(),
          "...and 20260819T145717, where 10 grants SURVIVE the rule, does not "
          "carry it",
          "that capture is the one where the counterfactual is a measurement, "
          "and a caveat printed everywhere is a caveat nobody reads")

    # --- 15 -----------------------------------------------------------------
    print("\n15. THE TWO ARMS, MARGINALLY -- and the mirror of the server's "
          "own constants")
    sh = R["shipped"]
    if "unreadable" in sh or "GRANT_LOCAL_WINDOW" not in sh:
        LEDGER.skip("the shipped-constant mirror",
                    f"authsrv.py declares no GRANT_LOCAL_WINDOW ({sh}); the "
                    f"flag is not in this tree, so there is nothing to pin")
    else:
        check(sh["GRANT_LOCAL_WINDOW"] == repr(G.SHIPPED_LOCAL_WINDOW),
              f"authsrv.GRANT_LOCAL_WINDOW = {sh['GRANT_LOCAL_WINDOW']} matches "
              f"the mirror {G.SHIPPED_LOCAL_WINDOW}",
              "if the server retunes, this goes red and whoever retuned "
              "re-runs the replay -- every number in it is a number FOR THESE "
              "VALUES")
        check(sh["GRANT_MIN_INTERVAL"] == repr(G.SHIPPED_MIN_INTERVAL),
              f"authsrv.GRANT_MIN_INTERVAL = {sh['GRANT_MIN_INTERVAL']} matches "
              f"the mirror {G.SHIPPED_MIN_INTERVAL}")
        check(sh.get("GRANT_SUPPRESS") == "False",
              f"and GRANT_SUPPRESS = {sh.get('GRANT_SUPPRESS')} -- the flag is "
              f"OFF by default, so this replay describes an OPT-IN",
              "a counterfactual for a change already shipped on is a "
              "different document")
    m = R["marginals"]
    check(m[G.ARM_KEYBOARD]["suppressed"] == 140,
          f"reproduction, KEYBOARD arm alone: "
          f"{m[G.ARM_KEYBOARD]['suppressed']} of 140")
    check(m[G.ARM_RATE]["suppressed"] == 102 and m[G.ARM_RATE]["kept"] == 38,
          f"reproduction, RATE arm alone: {m[G.ARM_RATE]['suppressed']} of 140 "
          f"suppressed, {m[G.ARM_RATE]['kept']} left on the wire",
          "THE MARGINAL IS THE POINT: behind the keyboard arm the rate limit "
          "removes nothing MORE, which reads as 'it does nothing' and would "
          "get it deleted. Alone it takes 140 to 38.")
    check(m[G.ARM_BOTH]["suppressed"] >= m[G.ARM_KEYBOARD]["suppressed"],
          f"and BOTH ({m[G.ARM_BOTH]['suppressed']}) is never below the "
          f"keyboard arm alone")
    seq = G.suppression(R["cs"], R["grant_arms"], G.SHIPPED_LOCAL_WINDOW,
                        G.SHIPPED_MIN_INTERVAL, G.ARM_RATE)
    gt = [t for t, _a in R["grant_arms"]]
    pairwise = sum(1 for i in range(1, len(gt))
                   if gt[i] - gt[i - 1] < G.SHIPPED_MIN_INTERVAL)
    check(seq["suppressed"] != pairwise,
          f"the rate arm is a STATE MACHINE, not a pairwise filter: "
          f"{seq['suppressed']} vs {pairwise} over the same timestamps",
          "a suppressed grant does not reset the floor, and the one-liner a "
          "reader would write gives the other number")
    kb = G.suppression(R["cs"], R["grant_arms"], G.MEASURED_WINDOW, None,
                       G.ARM_KEYBOARD)
    check(kb["suppressed"] == m[G.ARM_KEYBOARD]["suppressed"],
          f"and the headline is identical at this file's independently derived "
          f"W = {G.MEASURED_WINDOW} ({kb['suppressed']} of 140)",
          "two windows sized from two different corpus filters, same answer")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
