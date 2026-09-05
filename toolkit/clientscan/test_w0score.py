"""Checks for w0score.py -- the MOVECODE-1z-t scorer and its ENSLAVEMENT
DETECTOR (MOVECODE-1z-u.5 item c, FINDINGS sec.1z-x).

The detector answers the question the scorer's own number cannot: does the
drawn body follow world-0, or world-0 the body? Sections 1-4 are BARE-MACHINE
-- synthetic tap and gamesrv rows written to a temp dir, no vault -- and drive
every rule: the grant classification from the client's own last click and
report (decoded from the row's plaintext bytes, never the label), the
to-the-unit join with its causality (a grant sent AFTER the sample cannot be
the one it follows), the three verdicts and their bars, and the per-leg table.
Section 5 runs the two real controls when the vault is present: the zero-lead
baseline must read FREE and RUN-1zT's registered arm ENSLAVED from 18.65 s --
a detector that cannot find the known contamination cannot clear a new run.

Section 7 (MOVECODE-1z-bh, 2026-09-05; studies/review/MOVEMENT-2026-09-04.md
sec.1.1) is the MOVING-ONLY line. THE NUMBER is an all-sample p50, and on the
shipped lead-OFF default the stop echo parks world-0 on the body at every stop,
so the parked majority drags the median to ~0 while the copy runs a full report
chord behind whenever the body walks -- the registered sec.1z-t.8 verdict
printed CONFIRMED over exactly such a tape. The section builds that tape (20
walking samples 500 u behind, 30 parked samples on the body) and asserts the
all-sample p50 under the CONFIRM bar, the moving-only p50 over 400 u, and the
line actually printed beside THE NUMBER. Its control is a walk-only tape where
the two statistics must AGREE, so a green cell above is the parked majority and
not two differently-computed numbers.
"""

import json
import math
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/

import checks                                                  # noqa: E402
import w0score                                                 # noqa: E402

# Floor from the BARE-MACHINE green run, because a skip does not lower a floor
# (checks.py: `self.ran < self.floor` counts executed checks and nothing else),
# so the floor has to be the count the WEAKEST healthy configuration produces.
# Measured 2026-09-05 in this worktree: 50 checks with the vault present, 47
# with `RURIK_VAULT` pointed at an empty directory -- section 5's three real
# controls are the difference and declare a skip. Floor 47.
#
# The old floor of 44 was one the bare-machine run could not reach: 42 before
# section 7, because section 6's seven checks landed and the floor never moved.
# This file would have gone red on any machine without a vault -- the standing
# bare-machine defect class -- and the number was moving anyway, so it is
# corrected here. +5 2026-09-05 MOVECODE-1z-bh (section 7, the moving-only
# line and its no-parked-samples control).
LEDGER = checks.Ledger("w0score enslavement detector", floor=47)
check = checks.adopt_named(LEDGER)

T0 = 1_000_000_000.0          # a wall epoch no real capture overlaps


def grant_row(t, x, y, aid=1, label="KBD LEAD"):
    plain = struct.pack("<HIffHH", 0x29, aid, x, y, 0, 0).hex()
    return {"kind": "sent", "opcode": 0x29, "plain": plain, "label": label,
            "t": t, "wall_unix": T0 + t}


def report_row(t, x, y, op=0x3D):
    return {"kind": "decoded", "opcode": op, "values": [32829, [x, y], 0],
            "t": t, "wall_unix": T0 + t}


def click_row(t, x, y):
    return {"kind": "decoded", "opcode": 0x3E, "values": [32830, [x, y], 0],
            "t": t, "wall_unix": T0 + t}


def copy(x, y, tx, ty, vx=0.0, vy=0.0):
    return {"x": x, "y": y, "segx": x, "segy": y, "tx": tx, "ty": ty,
            "vx": vx, "vy": vy, "updated": 0, "stop": 0}


def sample(t, body, target, v=(288.0, 0.0), sync=None):
    a = {"async": copy(body[0], body[1], target[0], target[1], v[0], v[1]),
         "sync": sync or copy(body[0], body[1], target[0], target[1],
                              v[0], v[1])}
    return {"kind": "sample", "t": t, "clock0": 0, "clock1": 0,
            "agents": {"1": a}}


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def main():
    tmp = tempfile.mkdtemp(prefix="w0score-")

    print("== 1: grant classification, from the client's own last click and report ==")
    rows = [report_row(1.0, 100.0, 100.0),
            grant_row(1.1, 100.0, 100.0, label="zero-lead at the report"),
            grant_row(1.2, 620.0, 100.0, label="KBD LEAD"),
            click_row(2.0, 900.0, 300.0),
            grant_row(2.1, 900.0, 300.0, label="ROUTER one leg"),
            grant_row(2.2, 700.0, 250.0, label="ROUTER leg 1/3"),
            grant_row(2.3, 700.0, 250.0, aid=10, label="an NPC, not the player"),
            report_row(3.0, 400.0, 100.0, op=0x47),
            grant_row(3.1, 440.0, 100.0, label="49.9 u from the stop report")]
    G = w0score.grants(rows)
    kinds = [g["kind"] for g in G]
    check("a grant at the reported point is at-report",
          kinds[0] == "at-report" and G[0]["lead"] < 1e-6)
    check("a grant 520 u from the report is server-chosen",
          kinds[1] == "server-chosen" and abs(G[1]["lead"] - 520.0) < 1e-6)
    check("a verbatim echo of the client's own click is own-click",
          kinds[2] == "own-click")
    check("a routed waypoint the client did not propose is server-chosen",
          kinds[3] == "server-chosen")
    check("NPC grants are not the player's", len(G) == 5)
    check("the LEAD_MIN band: 49.9 u from a STOP report is still at-report",
          kinds[4] == "at-report")
    check("the point is decoded from the plaintext bytes, to the unit",
          G[1]["dest"] == (620.0, 100.0) and G[2]["dest"] == (900.0, 300.0))
    check("the wall stamp rides each grant", G[1]["w"] == T0 + 1.2)

    print("== 2: the join -- to the unit, causal, own points excepted ==")
    head = {"kind": "head", "t0": T0, "agents": [1], "hz": 10.0}
    lead = (620.0, 100.0)
    G = w0score.grants([report_row(1.0, 100.0, 100.0),
                        grant_row(1.2, lead[0], lead[1]),
                        click_row(5.0, 900.0, 300.0),
                        grant_row(5.1, 900.0, 300.0, label="ROUTER one leg"),
                        report_row(7.0, 900.0, 300.0),
                        grant_row(7.1, 900.0, 300.0, label="zero-lead")])
    samples = [
        sample(0.5, (100.0, 100.0), (620.0, 100.0)),      # BEFORE the lead
        sample(1.5, (130.0, 100.0), (620.0, 100.0)),      # following the lead
        sample(2.0, (160.0, 100.0), (620.4, 100.0)),      # inside the band
        sample(2.5, (190.0, 100.0), (621.5, 100.0)),      # outside the band
        sample(3.0, (220.0, 100.0), (300.0, 100.0)),      # its own heading
        sample(3.5, (250.0, 100.0), (620.0, 100.0), v=(0.0, 0.0)),  # parked
        sample(5.5, (500.0, 200.0), (900.0, 300.0)),      # its own click
        sample(7.5, (900.0, 300.0), (900.0, 300.0)),      # zero-lead point
    ]
    per, e = w0score.enslavement(head, samples, G)
    hits = [p["hit"] is not None and p["hit"]["kind"] == "server-chosen"
            for p in per]
    check("a sample BEFORE the grant cannot be following it (causality)",
          hits[0] is False)
    check("a moving sample whose target is the lead, to the unit, is enslaved",
          hits[1] is True)
    check("0.4 u off is still the same point", hits[2] is True)
    check("1.5 u off is another point", hits[3] is False)
    check("the body's own heading target is free", hits[4] is False)
    check("a parked body is not a trial (moving samples only)",
          e["moving"] == 7)
    check("following the client's OWN click is not enslavement",
          hits[6] is False and e["own"] >= 1)
    check("following a zero-lead grant at the report is not enslavement",
          hits[7] is False and e["own"] == 2)
    check("the summary counts 2 of 7 moving samples enslaved",
          e["enslaved"] == 2 and abs(e["frac"] - 2.0 / 7.0) < 1e-9)
    check("first_any_t is the first enslaved sample; first_t needs a "
          "SUSTAINED run (3) and two in a row is not one",
          e["first_any_t"] == 1.5 and e["first_t"] is None)
    check("2 of 7 moving (29%) is over the 25% bar: ENSLAVED",
          e["verdict"] == "ENSLAVED")

    print("== 3: the three verdicts and their bars ==")
    G1 = w0score.grants([report_row(1.0, 0.0, 0.0), grant_row(1.1, 520.0, 0.0)])
    free = [sample(2.0 + 0.1 * i, (10.0 * i, 0.0), (5000.0, 0.0))
            for i in range(20)]
    _per, ef = w0score.enslavement(head, free, G1)
    check("a body walking its own target the whole run is FREE",
          ef["verdict"] == "FREE" and ef["enslaved"] == 0 and ef["first_t"] is None)
    mixed = free[:17] + [sample(4.0 + 0.1 * i, (600.0, 0.0), (520.0, 0.0))
                         for i in range(3)]
    _per, em = w0score.enslavement(head, mixed, G1)
    check("3 of 20 (15%) is MIXED, not ENSLAVED",
          em["verdict"] == "MIXED" and em["enslaved"] == 3)
    ens = free[:14] + [sample(4.0 + 0.1 * i, (600.0, 0.0), (520.0, 0.0))
                       for i in range(6)]
    _per, ee = w0score.enslavement(head, ens, G1)
    check("6 of 20 (30%) crosses the 25% bar: ENSLAVED",
          ee["verdict"] == "ENSLAVED")
    check("the onset is the first sample of the sustained run",
          abs(ee["first_t"] - 4.0) < 1e-9 and ee["first_any_t"] == ee["first_t"])
    _per, e0 = w0score.enslavement(head, [], G1)
    check("no samples: FREE with zero trials, never a crash",
          e0["verdict"] == "FREE" and e0["moving"] == 0)
    _per, eg = w0score.enslavement(head, ens, [])
    check("no grants at all: nothing can be followed -> FREE",
          eg["verdict"] == "FREE" and eg["grants"] == 0)

    print("== 4: per leg ==")
    G2 = w0score.grants([report_row(1.0, 0.0, 0.0), grant_row(1.1, 520.0, 0.0),
                         report_row(10.0, 520.0, 0.0),
                         grant_row(10.1, 1040.0, 0.0)])
    legs = [sample(2.0 + 0.5 * i, (100.0 * i, 0.0), (5000.0, 0.0))
            for i in range(6)]                                  # 2.0..4.5 free
    legs += [sample(10.5 + 0.5 * i, (520.0 + 100.0 * i, 0.0), (1040.0, 0.0))
             for i in range(6)]                                 # 10.5..13.0 enslaved
    legs += [sample(20.0, (1040.0, 0.0), (1040.0, 0.0), v=(0.0, 0.0))]
    per, _e = w0score.enslavement(head, legs, G2)
    walk = [{"kind": "key", "key": "W", "started_unix": T0 + 2.0,
             "ended_unix": T0 + 5.0},
            {"kind": "key", "key": "S", "started_unix": T0 + 10.0,
             "ended_unix": T0 + 14.0},
            {"kind": "wait", "key": "", "started_unix": T0 + 19.0,
             "ended_unix": T0 + 21.0},
            {"kind": "key", "key": "W", "started_unix": T0 + 19.5,
             "ended_unix": T0 + 24.5},                    # held, parked
            {"kind": "key", "key": "Q"}]                        # no stamps
    lv = w0score.leg_verdicts(per, walk)
    check("a leg with no stamps is skipped", len(lv) == 4)
    check("the free leg reads FREE with its body travel",
          lv[0]["verdict"] == "FREE" and abs(lv[0]["travel"] - 500.0) < 1e-6
          and lv[0]["enslaved"] == 0)
    check("the free-walk expectation is the median speed times the hold",
          abs(lv[0]["expected"] - 288.0 * 3.0) < 1e-6)
    check("the enslaved leg reads ENSLAVED at 100% of its moving samples",
          lv[1]["verdict"] == "ENSLAVED" and lv[1]["frac"] == 1.0
          and lv[1]["moving"] == 6)
    check("a leg with no moving samples has no verdict",
          lv[2]["verdict"] == "-" and lv[2]["moving"] == 0)
    check("a HELD KEY that moved the body nothing is flagged parked (the "
          "third W of RUN-1zT: 2.9 u for 5.0 s)",
          lv[3]["parked"] is True and lv[3]["verdict"] == "-"
          and lv[2]["parked"] is False and lv[0]["parked"] is False)
    check("each leg carries its start stamp -- two W legs stay two rows",
          lv[0]["start"] == T0 + 2.0 and lv[3]["start"] == T0 + 19.5)

    print("== 4b: find_gamesrv and the scorer's plumbing ==")
    tap = os.path.join(tmp, "agenttap-synthetic.jsonl")
    write_jsonl(tap, [head] + ens)
    gs = os.path.join(tmp, "authsrv-synthetic-c1.jsonl")
    write_jsonl(gs, [report_row(1.0, 0.0, 0.0), grant_row(1.1, 520.0, 0.0)])
    h, rws = w0score.load(tap)
    check("a synthetic tap overlaps no vault capture: find_gamesrv is None",
          w0score.find_gamesrv(h, rws) is None)
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = w0score.score(tap, grants_path=gs)
    out = buf.getvalue()
    check("score() joins an explicit --grants capture and reports the verdict",
          r["enslavement"] is not None and r["enslavement"]["verdict"] == "ENSLAVED"
          and "ENSLAVED" in out and r["grants_path"] == gs)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r2 = w0score.score(tap)
    check("with nothing to join, the section says NOT MEASURED and the "
          "summary carries None",
          r2["enslavement"] is None and "NOT MEASURED" in buf.getvalue())

    print("== 5: the real controls (vault) ==")
    try:
        import vaultpath
        d = vaultpath.vault_path("research", "animref")
        cf = os.path.join(d, w0score.CONTROL_FREE + ".jsonl")
        ce = os.path.join(d, w0score.CONTROL_ENSLAVED + ".jsonl")
    except Exception as exc:                                   # noqa: BLE001
        cf = ce = None
        LEDGER.skip("5. the real controls", f"no vault: {exc}")
    if cf and os.path.exists(cf) and os.path.exists(ce):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rf = w0score.score(cf)
            re_ = w0score.score(ce)
        ef, ee = rf["enslavement"], re_["enslavement"]
        check("the zero-lead baseline joins its gamesrv capture and reads FREE",
              ef is not None and ef["verdict"] == "FREE" and ef["enslaved"] == 0
              and ef["server_chosen"] == 0,
              f"{ef}")
        check("RUN-1zT's registered arm reads ENSLAVED from 17.77 s on the "
              "tap's clock (18.65 s on the gamesrv clock, sec.1z-u.3), the "
              "majority of its moving samples",
              ee is not None and ee["verdict"] == "ENSLAVED"
              and ee["first_t"] is not None
              and abs(ee["first_t"] - w0score.CONTROL_ENSLAVED_FIRST_T) < 0.3
              and ee["frac"] > 0.5,
              f"{ee}")
        check("and its own scorer number still reproduces (p50 0.0) -- the "
              "contamination is in WHO FOLLOWS WHOM, not in the number",
              re_["live"][0] < 1.0)
    elif cf:
        LEDGER.skip("5. the real controls", f"missing {cf} or {ce}")

    print("== 6: MOVECODE-1z-ac, the bit-identity discriminator (the "
          "co-directional-lead confound) ==")
    # A LEAD run's grant sits ~0.5 u from the client's OWN co-directional
    # target, because the lead length was derived from the client's own report
    # chord. Only the DRAWN copy carrying the grant is enslavement.
    G = [report_row(0.5, 0.0, 0.0), grant_row(0.6, 520.0, 0.0, label="KBD LEAD")]
    gp = os.path.join(tmp, "authsrv-1zac-c1.jsonl")
    write_jsonl(gp, G)
    grants6 = w0score.grants(w0score.load_gamesrv(gp))
    check("the fixture's lead is classified server-chosen",
          len(grants6) == 1 and grants6[0]["kind"] == "server-chosen")

    def cap(name, sync_tgt):
        """One moving body walking toward (520,0); `sync_tgt` is world-0's."""
        rows = [{"kind": "head", "pid": 1, "agents": [1], "t0": T0, "hz": 10.0}]
        for k in range(6):
            t = 1.0 + 0.1 * k
            a = {"async": copy(10.0 * k, 0.0, 519.5, 0.0, 288.0, 0.0),
                 "sync": copy(10.0 * k, 0.0, sync_tgt, 0.0, 288.0, 0.0)}
            rows.append({"kind": "sample", "t": t, "clock0": 0, "clock1": 0,
                         "agents": {"1": a}})
        p = os.path.join(tmp, name)
        write_jsonl(p, rows)
        h, r = w0score.load(p)
        return w0score.enslavement(h, r, grants6)

    # (a) the CONFOUND: the body's own target is 0.5 u from our grant -- inside
    #     GRANT_EPS -- but world-0 carries the grant and the body does not.
    _per, free = cap("agenttap-confound.jsonl", 520.0)
    check("CO-DIRECTIONAL CONFOUND: the body's own target within 1 u of a "
          "server-chosen grant is NOT enslavement while the drawn copy keeps "
          "its own target",
          free["enslaved"] == 0 and free["verdict"] == "FREE"
          and free["moving"] == 6, f"{free}")
    check("and the loose join still counts it, so the report can name what "
          "the discriminator removed",
          free["loose"] == 6 and free["confound"] == 6, f"{free}")
    # (b) REAL enslavement: the grant was written into the drawn copy too, so
    #     both world targets are bit-identical.
    _per, ens = cap("agenttap-enslaved.jsonl", 519.5)
    check("REAL ENSLAVEMENT: both world copies bit-identical on the grant "
          "reads ENSLAVED, with an onset",
          ens["enslaved"] == 6 and ens["verdict"] == "ENSLAVED"
          and ens["confound"] == 0 and ens["first_t"] is not None, f"{ens}")
    # (c) the threshold sits between float identity and the measured confound
    check("the threshold is below the confound's measured 0.53 u floor and "
          "above float identity",
          0.0 < w0score.TGT_SAME < 0.5, f"TGT_SAME={w0score.TGT_SAME}")
    _per, edge = cap("agenttap-edge.jsonl", 519.5 + w0score.TGT_SAME * 2)
    check("KNOWN-BAD ARM: a drawn copy whose target is merely NEAR world-0's "
          "(twice the threshold) is not enslaved -- the test is identity, not "
          "proximity", edge["enslaved"] == 0, f"{edge}")
    # (d) a parked world-0 (infinite target) cannot enslave anything
    _per, inf = cap("agenttap-inf.jsonl", float("inf"))
    check("a world-0 with no leg armed (infinite target) enslaves nothing",
          inf["enslaved"] == 0, f"{inf}")

    print("== 7: MOVECODE-1z-bh, the MOVING-ONLY line (review sec.1.1) ==")
    # The shipped lead-OFF default in miniature: the body walks at 288 with
    # world-0 a full report chord (500 u) behind, then stops and the stop echo
    # parks the copy ON it. The parked samples outnumber the walking ones --
    # they do on every real tape too -- so the ALL-SAMPLE median reads ~0 while
    # the copy was 500 u behind for the whole walk. That is exactly the tape
    # the sec.1z-t.8 verdict printed CONFIRMED over.
    rows7 = [{"kind": "head", "pid": 1, "agents": [1], "t0": T0, "hz": 10.0}]
    for k in range(20):                       # WALKING: copy 500 u behind
        bx = 1000.0 + 100.0 * k
        rows7.append({"kind": "sample", "t": 1.0 + 0.1 * k,
                      "clock0": 0, "clock1": 0,
                      "agents": {"1": {
                          "async": copy(bx, 0.0, bx + 520.0, 0.0, 288.0, 0.0),
                          "sync": copy(bx - 500.0, 0.0, bx, 0.0, 288.0, 0.0)}}})
    endx = 1000.0 + 100.0 * 19
    for k in range(30):                       # PARKED: the stop echo, sep 0
        rows7.append({"kind": "sample", "t": 3.1 + 0.1 * k,
                      "clock0": 0, "clock1": 0,
                      "agents": {"1": {
                          "async": copy(endx, 0.0, endx, 0.0, 0.0, 0.0),
                          "sync": copy(endx, 0.0, endx, 0.0, 0.0, 0.0)}}})
    tap7 = os.path.join(tmp, "agenttap-1zbh.jsonl")
    write_jsonl(tap7, rows7)
    gs7 = os.path.join(tmp, "authsrv-1zbh-c1.jsonl")
    write_jsonl(gs7, [report_row(1.0, 1000.0, 0.0),
                      grant_row(1.05, 1000.0, 0.0, label="zero-lead")])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r7 = w0score.score(tap7, grants_path=gs7)
    out7 = buf.getvalue()
    check("THE NUMBER, all-sample, reads under the CONFIRM bar on a tape "
          "whose every walking sample was 500 u behind",
          r7["live"][0] < w0score.CONFIRM_P50, f"p50 {r7['live'][0]:.1f}")
    check("the MOVING-ONLY p50 reads the separation law instead",
          r7["live_moving"][0] > 400.0 and r7["moving_n"] == 20,
          f"p50 {r7['live_moving'][0]:.1f} over {r7['moving_n']} samples")
    check("and the headline PRINTS it, beside THE NUMBER and not instead",
          f"moving only (v > {w0score.MOVING_V:.0f} u/s)" in out7
          and "<-- THE NUMBER" in out7)
    check("the cut is the body's speed, not world-0's: 20 walking samples of "
          "50, and the parked majority is what drags the all-sample median",
          r7["moving_n"] == 20 and r7["live"][3] > 400.0,
          f"max {r7['live'][3]:.1f}")
    # KNOWN-BAD ARM: a tape with NO parked samples cannot show the divergence,
    # so a green section 7 must be the parked majority doing the work rather
    # than the two statistics being computed differently.
    tap7b = os.path.join(tmp, "agenttap-1zbh-walkonly.jsonl")
    write_jsonl(tap7b, [rows7[0]] + rows7[1:21])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r7b = w0score.score(tap7b, grants_path=gs7)
    check("CONTROL: with no parked samples the two statistics agree, so the "
          "gap in the cell above is the stop echo and not the arithmetic",
          abs(r7b["live"][0] - r7b["live_moving"][0]) < 1e-6
          and r7b["live_moving"][0] > 400.0,
          f"all {r7b['live'][0]:.1f} vs moving {r7b['live_moving'][0]:.1f}")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
