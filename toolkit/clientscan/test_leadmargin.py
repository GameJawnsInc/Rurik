"""Checks for leadmargin.py -- the keyboard lead's LENGTH argument
(MOVECODE-1z-ab, FINDINGS sec.1z-ab).

Sections 1-3 are BARE-MACHINE, over synthetic gamesrv and agenttap rows in a
temp dir: the cruise-chord extractor's every rule (same heading, same type,
a stop breaks the pair, the heartbeat gap and the teleport speed bar both
exclude, a malformed row is skipped), the census's split of the tail into
late reports and silent walks, the per-leg reading on a tap (the live rule
with its clamp, a walking leg's distance-to-go, a matured leg's park, a
short leg dropped, `until` cutting the tail), and the bounds -- which are
checked against the SERVER'S OWN constants, so a floor or a lead moved
without this argument goes red here.  The one inequality that does not
hold is pinned as not holding: the hold's same-family residual (2 x 288 x
0.55 s = 316.8 u against gate 1's 299.33) is a recorded residual, and a
constant change that silently made it hold or made the cross-family one
fail would move sec.1z-ab's arithmetic without moving its prose.
Section 4 reproduces the corpus figures when the vault is present.
"""

import json
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import checks                                                  # noqa: E402
import leadmargin                                              # noqa: E402

# Floor from the bare-machine green run (sections 1-3); section 4 is
# vault-gated and skips, which lowers nothing.
LEDGER = checks.Ledger("leadmargin: the keyboard lead's length", floor=24)
check = checks.adopt_named(LEDGER)

T0 = 1_000_000_000.0


def rep(t, x, y, vec=(766.8, 0.0), mt=1, op=0x3D):
    v = [32829, [x, y], 0, list(vec), mt] if op == 0x3D else [32839, [x, y], 0]
    return {"kind": "decoded", "opcode": op, "values": v, "t": t,
            "wall_unix": T0 + t}


def sync_copy(ox, oy, tx, ty, updated, v=(288.0, 0.0), stop=0,
              seg=(math.inf, math.inf)):
    return {"x": ox, "y": oy, "vx": v[0], "vy": v[1], "updated": updated,
            "stop": stop, "segx": seg[0], "segy": seg[1], "tx": tx, "ty": ty,
            "maxspeed": 288.0, "movespeed": 1.0}


def body_copy(x, y, updated, v=(288.0, 0.0)):
    """The drawn copy's fields as the tap records them: `x, y` is the
    position at clock `updated`, so the live rule dead-reckons nothing when
    the sample clock equals it."""
    return {"x": x, "y": y, "vx": v[0], "vy": v[1], "updated": updated, "stop": 0,
            "segx": math.inf, "segy": math.inf, "tx": x, "ty": y}


def main():
    tmp = tempfile.mkdtemp(prefix="leadmargin-")

    print("\n1. the cruise-chord extractor and the census")
    rows = [
        rep(0.00, 0.0, 0.0), rep(1.78, 513.0, 0.0), rep(3.56, 1026.0, 0.0),
        # a late report: 540 u in 1.90 s (a frame hitch)
        rep(5.46, 1566.0, 0.0),
        # a silent walk: 3.0 triggers in 5.33 s at cruise speed
        rep(10.79, 3102.0, 0.0),
        # a teleport: 3000 u in 0.5 s -- not a chord
        rep(11.29, 6102.0, 0.0),
        # a heading change on the next pair -- not a chord
        rep(13.07, 6102.0, 513.0, vec=(0.0, 766.8)),
        # a stop breaks the pair: 0x0047 then a report 513 u on
        rep(13.10, 6102.0, 513.0, op=0x47), rep(14.90, 6102.0, 1026.0, vec=(0.0, 766.8)),
        # a heartbeat pair: 144 u in 0.5 s -- under the gap floor
        rep(15.40, 6102.0, 1170.0, vec=(0.0, 766.8)),
        # backpedal pair, type 4: 513 u in 2.70 s
        rep(20.00, 0.0, 0.0, vec=(-766.8, 0.0), mt=4),
        rep(22.70, -513.0, 0.0, vec=(-766.8, 0.0), mt=4),
        # a malformed row is skipped, and the pair around it survives
        {"kind": "decoded", "opcode": 0x3D, "values": [1], "t": 22.8},
        rep(25.40, -1026.0, 0.0, vec=(-766.8, 0.0), mt=4),
        # a type-0 (idle) pair is not a chord
        rep(30.0, 0.0, 0.0, mt=0), rep(31.8, 513.0, 0.0, mt=0),
    ]
    gpath = os.path.join(tmp, "authsrv-synthetic-c1.jsonl")
    with open(gpath, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    ch = leadmargin.cruise_chords([gpath])
    ds = sorted(round(c["d"], 1) for c in ch)
    check("six chords survive the five exclusions",
          ds == [513.0, 513.0, 513.0, 513.0, 540.0, 1536.0], f"got {ds}")
    check("the teleport, the turn, the stopped pair, the heartbeat pair and "
          "the idle pair are not chords",
          all(c["d"] < 3000 for c in ch) and not any(
              abs(c["d"] - 144.0) < 1 for c in ch)
          and all(c["mt"] != 0 for c in ch))
    check("the backpedal pair counts under its own type with its own speed",
          sum(1 for c in ch if c["mt"] == 4) == 2
          and all(abs(c["speed"] - 190.0) < 1.0 for c in ch if c["mt"] == 4))
    c = leadmargin.chord_census(ch)
    check("in band: the four 513 u chords, ceiling 513, excess bin +1",
          c["in_band"] == 4 and abs(c["ceiling"] - 513.0) < 1e-9
          and c["hist"] == {1: 4}, f"{c['in_band']} {c['ceiling']} {c['hist']}")
    check("the tail splits: one late report (540 u, 1.05 triggers), one "
          "silent walk (1536 u, 3.0 triggers)",
          [round(h["d"]) for h in c["hitch"]] == [540]
          and [round(h["ratio"], 2) for h in c["silent"]] == [3.0])
    check("per-type stats name both types with their counts",
          c["per_type"][1]["n"] == 4 and c["per_type"][4]["n"] == 2
          and c["below"] == 0)
    check("an empty corpus is a census with no ceiling, not a crash",
          leadmargin.chord_census([])["ceiling"] is None
          and leadmargin.chord_census([])["n"] == 0)

    print("\n2. the per-leg reading on a tap: the live rule, a walking leg, "
          "a matured leg")
    samples = []
    hz = 30.0
    n = int(4.5 * hz)
    for k in range(n + 1):
        t = k / hz
        clock = int(round(t * 1000))
        if t < 1.77:
            # leg 1: origin (0,0) at clock 0, dest (520,0), copy walking
            s = sync_copy(0.0, 0.0, 520.0, 0.0, 0)
            live = 288.0 * t
        elif t < 3.90:
            # leg 2: origin (520,0) at clock 1800, dest (1040,0); the copy
            # arrives at 1800 + 520/288 s = 3606 ms and is CLAMPED there
            s = sync_copy(520.0, 0.0, 1040.0, 0.0, 1800, stop=3606,
                          seg=(1040.0, 0.0))
            live = min(520.0 + 288.0 * (t - 1.8), 1040.0)
        elif t < 4.0:
            # a 100 u zero-lead leg: dropped by min_len
            s = sync_copy(1040.0, 0.0, 1140.0, 0.0, 3900)
            live = 1040.0 + 288.0 * (t - 3.9)
        else:
            # leg 4, after the cut
            s = sync_copy(1140.0, 0.0, 2000.0, 0.0, 4000)
            live = 1140.0 + 288.0 * (t - 4.0)
        body = body_copy(live + 20.0, 0.0, clock)
        samples.append({"kind": "sample", "t": t, "controlled": 1,
                        "clock0": clock, "clock1": clock,
                        "agents": {"1": {"sync": s, "async": body}}})
    tpath = os.path.join(tmp, "agenttap-synthetic.jsonl")
    with open(tpath, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "head", "pid": 1, "agents": [1],
                             "t0": T0, "hz": hz}) + "\n")
        for s in samples:
            fh.write(json.dumps(s) + "\n")
    legs = leadmargin.lead_legs(tpath, until=3.95)
    check("two legs of the four survive: the 100 u stub is dropped and the "
          "leg after the cut is not read",
          len(legs) == 2 and [round(l["len"]) for l in legs] == [520, 520],
          f"{[(round(l['len']), l['t0']) for l in legs]}")
    l1, l2 = legs
    check("leg 1 is WALKING at its re-aim, with the distance still to go "
          "read from the dead-reckoned live point, not the +0x78 origin",
          not l1["matured"] and 8.0 < l1["left"] < 14.0 and l1["park_s"] == 0.0,
          f"left {l1['left']:.1f}")
    check("leg 2 MATURED: the clamp puts the live copy on its point and "
          "the park is the time it sat there before the next grant",
          l2["matured"] and 0.25 <= l2["park_s"] <= 0.30
          and l2["left"] < 1e-6 and l2["at_dest_samples"] >= 8,
          f"park {l2['park_s']:.3f} s, {l2['at_dest_samples']} samples")
    check("the live separation from the drawn body is read live-vs-live "
          "(a constant 20 u shadow reads as 20, not as the origin gap)",
          all(abs(l["sep_p50"] - 20.0) < 0.5 and abs(l["sep_max"] - 20.0) < 0.5
              for l in legs), f"{[(l['sep_p50'], l['sep_max']) for l in legs]}")
    check("the speed families are read off the client's own velocity fields",
          l1["v0"] == {288: len([s for s in samples if s['t'] < 1.77])}
          and set(l1["vbody"]) == {288})
    s = leadmargin.legs_summary(legs)
    check("the summary: 2 legs, 1 matured, longest park, min left",
          s["n"] == 2 and s["matured"] == 1 and 0.25 <= s["park_max_s"] <= 0.30
          and s["left_min"] < 1e-6)
    check("no cut reads all four-minus-the-stub: three legs",
          len(leadmargin.lead_legs(tpath)) == 3)

    print("\n3. the bounds, against the server's own constants")
    import authsrv                                             # noqa: E402
    import agtrack_guard                                       # noqa: E402
    import agtrack_mirror                                      # noqa: E402
    check("the module's decoded constants are the server's: run speed, "
          "gate 1, the reprieve radius",
          leadmargin.RUN == authsrv.DEFAULT_RUN_SPEED
          and leadmargin.GATE1 == agtrack_guard.GATE1_RED
          and leadmargin.R_MATCH == agtrack_mirror.R_MATCH)
    b = leadmargin.bounds(authsrv.KBD_SYNC_LEAD, authsrv.GRANT_MIN_INTERVAL,
                          authsrv.TICK_SECONDS)
    check("the hold window is the floor plus one tick (0.55 s)",
          abs(b["hold_window_s"] - 0.55) < 1e-9, f"{b['hold_window_s']}")
    check("the shipped lead cannot mature inside a hold window "
          "(520 > 288 x 0.55 = 158.4)",
          b["no_mature_in_hold"][2] and abs(b["no_mature_in_hold"][1] - 158.4) < 1e-6)
    check("the shipped lead outlasts the client's 512 u trigger",
          b["outlasts_trigger"][2] and b["outlasts_trigger"][1] == 512.0)
    check("the hold's cross-family residual is under gate 1 "
          "((288 + 190) x 0.55 = 262.9 < 299.33)",
          b["hold_residual_cross"][2]
          and abs(b["hold_residual_cross"][0] - 262.9) < 0.1)
    check("the hold's SAME-FAMILY residual is NOT under gate 1 "
          "(2 x 288 x 0.55 = 316.8 >= 299.33) -- sec.1z-ab's recorded residual; "
          "a floor or tick that changes this must change the prose too",
          not b["hold_residual_same"][2]
          and abs(b["hold_residual_same"][0] - 316.8) < 0.1)
    check("the order-walk cost is the lead itself, so it is monotone: "
          "766 costs 246 u more than 520 in the mode the gates exist to prevent",
          leadmargin.bounds(766.0)["order_walk_u"] - b["order_walk_u"] == 246.0)
    check("a measured ceiling enters as its own inequality",
          leadmargin.bounds(520.0, ceiling=517.5)["outlasts_ceiling"] == (520.0, 517.5, True)
          and not leadmargin.bounds(516.0, ceiling=517.5)["outlasts_ceiling"][2])
    check("KNOWN-BAD ARMS: a 400 u lead fails the trigger, a 100 u lead "
          "matures inside the hold window",
          not leadmargin.bounds(400.0)["outlasts_trigger"][2]
          and not leadmargin.bounds(100.0)["no_mature_in_hold"][2])
    check("the shipped lead is 520 (the argument's subject; move it with "
          "sec.1z-ab, not alone)", authsrv.KBD_SYNC_LEAD == 520.0)

    print("\n4. the corpus reproduction (vault-gated)")
    try:
        import vaultpath
        vaultpath.require_dir("captures", "gamesrv")
        have = True
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        have = False
        LEDGER.skip("corpus reproduction", f"no vault: {exc}")
    if have:
        rc = leadmargin.check_corpus(authsrv.KBD_SYNC_LEAD)
        check("leadmargin --check reproduces sec.1z-ab's figures (rc 0)",
              rc == 0, f"rc={rc}")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
