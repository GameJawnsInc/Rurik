#!/usr/bin/env python3
"""The position-trust policy: it may refuse, but it may never LATCH.

    python toolkit/authsrv/test_position_trust.py

WHAT EARNS THIS FILE. `_adopt_client_position` refused any client-reported
position more than `CLIENT_POSITION_TRUST_RADIUS` = 900 u from the server's own
model. The radius was measured from `state["pos"]` -- the value the refusal was
preventing from being corrected -- so once the model was more than 900 u wrong,
every true report was also more than 900 u away and was refused in its turn. Run
20260819T113049 refused 50 reports, 36 of them consecutively, 21% of everything
the client said. Nothing in the suite could see it: `position_report` was emitted
from the 0x0047 arm only and carried a literal `accepted=True`, so the flagship
capture's JSONL held 5 of 62 reports and none of the four refusals.

AND THE GUARD NEVER EARNED ITS KEEP. Scored over the 72 refusals the four
harness runs actually printed -- 7 + 11 + 50 + 4, counted from the servers' own
"[map] ignoring a Nu jump" lines, not from a replay -- by asking whether the
client's NEXT report is reachable from the point we refused or from the point we
preferred, at 478 u/s (the most generous speed in Guild Wars, Junundu Tunnel at
+66%, and far above our 288): client right 71, guard right 0, undecidable 1.

TWO NUMBERS THIS FILE DELIBERATELY DOES NOT USE. An earlier replay of the same
question reported 85 refusals and a largest true-but-refused drift of 18,647 u.
Both are artifacts: the servers printed 72, and the largest drift anywhere in the
harness tree is 4,116 u. A test pinned to 18,647 would have gone red forever
against a number no server ever produced, which is why every count below is
re-derived from a capture on disk or asserted as an invariant with no fixture at
all.

THE SHAPE OF THE FIX, and therefore of this file. The budget is
`max(RADIUS, RATE * seconds since the last report we BELIEVED)`, so it is never
smaller than the old flat 900 -- section 1 asserts that as an invariant, because
a tightening was designed, costed at 8 newly-refused true reports, and thrown
away. On top of it, the Nth consecutive refusal is adopted regardless, which is
what makes 36-in-a-row unreachable for any constants. Section 2 is the headline.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks     # noqa: E402
import authsrv    # noqa: E402
import vaultpath  # noqa: E402

# MEASURED from the first green run: 21 checks with the capture present, 17
# without. The floor is the BARE-MACHINE subset -- sections 0 to 6 are pure
# policy and take no fixture, while section 7 replays a real capture and
# declares LEDGER.skip when this vault has no copy of it. Setting the floor at
# 21 would red every machine that is not the owner's; setting it at 17 still
# catches the failure this rule exists for, which is a section quietly
# evaporating.
LEDGER = checks.Ledger("the position-trust policy: refuse, but never latch",
                       floor=17)
check = checks.adopt(LEDGER)

# The two real reports from run 20260819T114743, bit-exact from the capture.
# t=50.549817, the last position the old guard accepted before it latched:
ANCHOR = (9463.3544921875, 7945.9384765625)
# t=54.320344, 2,844 u away in 3.77 s and refused three times running. It is
# bit-identical to the click destination the server had granted 11.594 s
# earlier, and the client's own next report is reachable from it at 285 u/s.
JUMPED = (10995.26953125, 5549.82470703125)
JUMPED_PLANE = 18
CAPTURE = "authsrv-20260819T114759-c1.jsonl"


class FakeRec:
    """Records what the real Recorder would have written to the JSONL."""

    def __init__(self):
        self.events = []

    def event(self, kind, **fields):
        self.events.append(dict(fields, kind=kind))

    def of(self, kind):
        return [e for e in self.events if e["kind"] == kind]


def fresh(pos=ANCHOR, plane=0, seen=1000.0):
    return {"pos": pos, "plane": plane, "pos_seen": seen}


def main():
    print("0. the constants carry their derivation")
    check(authsrv.CLIENT_POSITION_TRUST_RADIUS == 900.0,
          "the old radius survives, unchanged, as a FLOOR",
          "not retuned: no measurement supports any other value, and every "
          "value has the same latching defect at a different scale")
    check(authsrv.CLIENT_POSITION_TRUST_RATE == 580.0,
          "the growth rate is 288 + 292, two measured ceilings summed",
          "our integrator's own constant plus a ceiling over the client's "
          "fastest measured cruise step (291.20 u/s, n=184). Nothing fitted -- "
          "the house rule is to prefer the check with no free parameter, and a "
          "decay constant tau would have been one")
    check(authsrv.CLIENT_POSITION_REJECT_STREAK == 2,
          "and the escape hatch is the second consecutive refusal",
          "the 0-for-72 record argues for 1; 2 is the smallest value that "
          "still buys a single-frame refusal of a garbage decode")

    print("\n1. INVARIANT: the fix is a strict LOOSENING, at every dt")
    worst = None
    for i in range(0, 2001):
        dt = i * 0.01
        st = fresh(seen=1000.0 - dt)
        _a, _r, _j, budget = authsrv._position_verdict(st, (0.0, 0.0), 1000.0)
        if budget < authsrv.CLIENT_POSITION_TRUST_RADIUS:
            worst = (dt, budget)
            break
    check(worst is None,
          "over 20 s of silence in 10 ms steps, the budget never drops below "
          "the old 900 u",
          f"{worst} -- so no report today's code accepts can be refused by the "
          f"new one. This is the property that killed the tighter design: "
          f"BASE 120 + RATE*dt would newly refuse 8 corpus reports the flat 900 "
          f"accepts, all 8 in the run whose displacements have no established "
          f"cause")
    st = fresh(seen=1000.0)
    _a, _r, _j, b0 = authsrv._position_verdict(st, (0.0, 0.0), 1000.0)
    check(b0 == 900.0, "and at dt = 0 it IS the old 900 exactly", f"{b0}")

    print("\n2. THE HEADLINE: a refusal streak cannot outlive the streak limit")
    st, rec = fresh(), FakeRec()
    took = []
    now = 1000.0
    for i in range(12):
        now += 0.5
        took.append(authsrv._take_client_position(
            st, JUMPED, JUMPED_PLANE, rec, "0x003D", now=now))
    run = best = 0
    for t in took:
        run = 0 if t else run + 1
        best = max(best, run)
    check(best <= authsrv.CLIENT_POSITION_REJECT_STREAK,
          f"twelve presentations of a 2,844 u jump never refuse more than "
          f"{authsrv.CLIENT_POSITION_REJECT_STREAK} in a row",
          f"longest refusal run was {best}. The old code refused all twelve, "
          f"and refused 36 in a row in run 20260819T113049 -- for as long as "
          f"the player kept walking, the model could never come back")
    check(took[1] is True,
          "specifically, the SECOND presentation is adopted",
          f"{took[:3]} -- the first refusal is the single-frame guard, the "
          f"second is the server admitting it is the one that is lost")

    print("\n3. silence widens the budget, because our claim gets weaker")
    st = fresh(seen=1000.0 - 12.874)   # the measured maximum silence in the run
    accept, reason, jump, budget = authsrv._position_verdict(st, JUMPED, 1000.0)
    check(accept is True and reason == "in-budget",
          "after the measured 12.874 s silence a 2,844 u report is taken at "
          "once, with no refusal at all",
          f"{reason}, budget {budget:.0f}u vs drift {jump:.0f}u -- we had 12.9 "
          f"s of no information, and 900 u was never a defensible bound over "
          f"that interval")
    st = fresh(seen=1000.0 - 0.5)      # the modal report interval
    accept, reason, _j, budget = authsrv._position_verdict(st, JUMPED, 1000.0)
    check(accept is False and reason == "reject",
          "while at the modal 0.5 s cadence the same report is still refused "
          "once",
          f"{reason}, budget {budget:.0f}u -- the guard still exists; it just "
          f"cannot hold the line forever")

    print("\n4. position and plane are ONE fact")
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    check(st["plane"] == 0,
          "a REFUSED report does not leave its plane behind",
          f"plane {st['plane']} -- the 0x003D arm used to write the plane "
          f"unconditionally 28 lines above the position guard, so run "
          f"20260819T114743 held plane 18 against (9463, 7946), a point our own "
          f"navmesh puts on plane 0. The click arm reads that plane to decide "
          f"whether it can place the player at all")
    check(st["pos"] == ANCHOR, "and does not move the position either",
          f"{st['pos']}")
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1001.0)
    check(st["plane"] == JUMPED_PLANE and st["pos"] == JUMPED,
          "and when it is adopted, both land together",
          f"{st['pos']} plane {st['plane']}")

    print("\n5. a refusal does NOT refresh the anchor")
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    check(st["pos_seen"] == 1000.0,
          "pos_seen still points at the last report we BELIEVED",
          f"{st['pos_seen']} -- if a refusal refreshed it the budget would stop "
          f"growing exactly when the model is most wrong, which is the latch "
          f"wearing a formula")

    print("\n6. the telemetry can go both ways, and names its source")
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    recs = rec.of("position_report")
    check(len(recs) == 1 and recs[0]["accepted"] is False,
          "a refused report emits a record saying so",
          f"{recs} -- `accepted` was a LITERAL True until 2026-08-19, and the "
          f"record was emitted from the stop arm only, so no run could produce "
          f"accepted=False and the JSONL carried 5 of 62 reports. A check that "
          f"cannot fail is not a check, and this was one in our own telemetry")
    check(recs[0]["reason"] == "reject" and recs[0]["source"] == "0x003D",
          "carrying the reason and the arm it came from",
          f"{recs[0].get('reason')} / {recs[0].get('source')}")
    st, rec = fresh(), FakeRec()
    ok = authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x0047",
                                       now=1000.5, stop=True)
    recs = rec.of("position_report")
    check(ok is True and recs[0]["reason"] == "stop-report",
          "and the stop arm DECLARES that it takes any distance",
          f"{recs[0].get('reason')} -- it accepted the 2,837 u correction that "
          f"rescued the model in run 20260819T114743, 1.24 s after the guarded "
          f"arm called the same coordinates impossible. Keeping it is measured "
          f"(ArenaNet echoes the client's stated stopping point verbatim in 70 "
          f"of 88 move-cancel windows); what is new is that it says so")
    check(st["pos"] == JUMPED and st["plane"] == JUMPED_PLANE,
          "and it moves both halves too", f"{st['pos']} plane {st['plane']}")

    print("\n7. replay: the real refusals from run 20260819T114743")
    path = os.path.join(vaultpath.vault_path("captures", "gamesrv"), CAPTURE)
    if not os.path.exists(path):
        LEDGER.skip("capture replay",
                    f"{CAPTURE} is not in this vault; the policy sections "
                    f"above are fixture-free and still ran")
    else:
        rows = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("kind") == "decoded" and o.get("opcode") in (61, 71):
                    rows.append((o["t"], tuple(o["values"][1]), o["values"][2],
                                 o["opcode"]))
        check(len(rows) >= 60,
              f"the capture still carries its {len(rows)} position reports",
              "62 when this was written: 57 on 0x003D and 5 on 0x0047")
        st = fresh(pos=rows[0][1], plane=rows[0][2], seen=rows[0][0])
        rec = FakeRec()
        refused = best = run = 0
        for t, pos, plane, op in rows[1:]:
            took = authsrv._take_client_position(
                st, pos, plane, rec, "0x0047" if op == 71 else "0x003D",
                now=t, stop=(op == 71))
            run = 0 if took else run + 1
            best = max(best, run)
            refused += (not took)
        check(best <= authsrv.CLIENT_POSITION_REJECT_STREAK,
              f"replaying all {len(rows)} of them, the longest refusal run is "
              f"{best}",
              f"the server printed 4 refusals for this run, 3 of them "
              f"consecutive, and only recovered because the player stopped "
              f"walking and sent a 0x0047")
        check(st["pos"] == rows[-1][1],
              "and the model ends the run where the client says it is",
              f"{st['pos']} vs {rows[-1][1]}")
        check(len(rec.of("position_report")) == len(rows) - 1,
              f"with one telemetry record per report ({len(rows) - 1}), not "
              f"per stop",
              f"{len(rec.of('position_report'))} -- the capture on disk holds 5 "
              f"because the old code only recorded stops")
        print(f"     refused {refused} of {len(rows) - 1}, "
              f"longest run {best}")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
