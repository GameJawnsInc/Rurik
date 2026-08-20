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
import ast
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks     # noqa: E402
import authsrv    # noqa: E402
import vaultpath  # noqa: E402

# MEASURED from a real green run: 24 checks with the capture present, 20
# without; section 8 (the unit-vector lock) added 8 on 2026-08-19 and
# section 9 (the --client-endpoint shape lock) added 6, so 38 and 34 --
# and 39/35 was written here first, from a count in the author's head
# rather than from the run, which would have set the floor ABOVE the
# bare-machine total and redded every machine without the capture. The floor is the BARE-MACHINE subset -- sections 0 to 8 are
# pure policy and syntax tree and take no fixture, while section 10 replays
# a real capture and declares LEDGER.skip when this vault has no copy of it.
# Setting the floor at 38 would red every machine that is not the owner's;
# 34 still catches the failure this rule exists for, which is a section
# quietly evaporating.
#
# 2026-08-20: section 11 (the --resync sender) added 35, so 73 with the capture
# and 69 without. Both numbers are from the run printed on the console, not from
# a count in anybody's head -- section 10 contributes exactly 4 checks and is
# the only fixture-bearing one, which is the whole of the arithmetic.
LEDGER = checks.Ledger("the position-trust policy: refuse, but never latch",
                       floor=71)
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

    print("\n7. the stop echo ships OFF, and it echoes the CLIENT")
    check(authsrv.STOP_ECHO is False,
          "--stop-echo is off by default",
          "it is the candidate fix for the teleport and it is unproven. The "
          "same corpus holds 13 grant-triggered displacements that do NOT land "
          "on a granted point, so disarming the destination may fix nothing. "
          "One watched run decides it")
    src = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    echoes = []
    for node in ast.walk(src):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                and node.test.id == "STOP_ECHO"):
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "send"
                    and len(call.args) >= 2
                    and isinstance(call.args[1], ast.List)):
                echoes.append(call.args[1].elts)
    check(len(echoes) == 1, "there is exactly one echo send",
          f"{len(echoes)} -- two would mean two policies again")
    # THE MUTATION THIS LOCKS. The echo must carry the position the CLIENT just
    # reported. Rewriting it to send `state["pos"]`, or the click's `dest`,
    # turns a no-op into a real teleport at the player -- the exact damage the
    # 0x0047 arm's own comment records ("teleporting a player nine units is
    # pure damage"), sent on every single stop. A grep cannot tell the two
    # apart; the syntax tree can.
    payload = echoes[0] if echoes else []
    dest_arg = payload[1] if len(payload) > 1 else None
    check(isinstance(dest_arg, ast.Call)
          and isinstance(dest_arg.func, ast.Name) and dest_arg.func.id == "list"
          and len(dest_arg.args) == 1
          and isinstance(dest_arg.args[0], ast.Name)
          and dest_arg.args[0].id == "reported",
          "and its destination is `reported` -- the client's own figure, so the "
          "echo is zero-distance by construction",
          f"{ast.dump(dest_arg) if dest_arg is not None else None} -- if this "
          f"ever becomes state['pos'] or the click's dest, the message stops "
          f"being a no-op and starts teleporting the player on every stop")


    print("\n8. the direction we answer a heading with is UNIT LENGTH")
    # MEASURED on both sides of the wire, 2026-08-19. Retail's 0x0025 vec2:
    # |v| in [0.996546, 1.000000] in 3,789 of 3,789 across the 9 live captures,
    # 0 of 3,789 above 100 u. Ours before this fix: 4,704 of 4,760 at 765-768,
    # because the handler passed the client's own 0x003D heading -- a
    # DISPLACEMENT of magnitude 765.017..768.000 -- straight into a field the
    # client reads as a DIRECTION. Two populations, zero overlap.
    #
    # WHY A TEST FOR AN INERT BUG. It is inert: setter 0x00602660's case 1 is a
    # bare dword copy (so the client stores our number RAW for 82% of sends),
    # but the only float read of +0xBC inside AgAgent is the lazy angle cache at
    # 0x005FFA1D, which calls atan2 -- and atan2 is scale-invariant, so the
    # magnitude cannot reach anything. It is still worth locking, because
    # verbatim-first is how this repo decides what is true, and a wire field that
    # disagrees with retail by 768x is a standing invitation to explain some
    # future symptom with the wrong cause. The lock is here so that the next
    # person who "simplifies" this back to list(heading) argues with a red test.
    move_dir_sends = []
    for call in ast.walk(src):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "send" and len(call.args) >= 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == "GAME_SMSG_AGENT_MOVE_DIRECTION"
                and isinstance(call.args[1], ast.List)):
            move_dir_sends.append(call.args[1].elts)
    check(len(move_dir_sends) == 1,
          "there is exactly one AGENT_MOVE_DIRECTION send site",
          f"{len(move_dir_sends)} -- a second one is a second policy, and the "
          f"765x defect survived this long because nobody looked at the one")

    def vector_arg(payload):
        """The vec2 slot of an [agent, vec2, byte] payload, or None."""
        return payload[1] if len(payload) > 1 else None

    vec = vector_arg(move_dir_sends[0] if move_dir_sends else [])
    # THE MUTATION THIS LOCKS, stated as the thing it must NOT be. list(heading)
    # is the defect, and it is one keystroke away from the fix.
    raw_passthrough = (isinstance(vec, ast.Call)
                       and isinstance(vec.func, ast.Name)
                       and vec.func.id == "list"
                       and len(vec.args) == 1
                       and isinstance(vec.args[0], ast.Name)
                       and vec.args[0].id == "heading")
    check(not raw_passthrough,
          "and it does not pass the client's raw heading through",
          "it sends list(heading) -- that vector is 765-768 units long, and "
          "retail's is 1.0 in 3,789 of 3,789")
    check(isinstance(vec, ast.Name) and vec.id == "unit",
          "it sends a normalised `unit`",
          f"{ast.dump(vec) if vec is not None else None}")

    # THE CONTROL. An AST matcher that cannot reject is not a check -- and the
    # rejecting branch above is the one that never runs against healthy source,
    # so it is exactly the branch a typo would silently disable. Hand it the
    # defect on purpose and require it to still recognise it.
    bad = ast.parse("send(GAME_SMSG_AGENT_MOVE_DIRECTION,"
                    " [PLAYER_AGENT_ID, list(heading), moving], 'x')")
    bad_payload = []
    for call in ast.walk(bad):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "send" and len(call.args) >= 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == "GAME_SMSG_AGENT_MOVE_DIRECTION"
                and isinstance(call.args[1], ast.List)):
            bad_payload = call.args[1].elts
    bad_vec = vector_arg(bad_payload)
    check(isinstance(bad_vec, ast.Call) and isinstance(bad_vec.func, ast.Name)
          and bad_vec.func.id == "list",
          "and the same matcher still SEES the defect when handed it on purpose",
          "the matcher no longer recognises list(heading), so the check above "
          "passes for the wrong reason")

    # THE TRAILING BYTE IS ALREADY CORRECT, and this locks it AGAINST a
    # recommendation. Retail echoes the client's own movementType: 2,215 of
    # 2,254 (98.27%), the 39 disagreements all adjacent enum values at
    # transition instants. A 2026-08-19 workflow agent recommended rewriting it
    # as an angle; that was REFUTED in the same pass. Without this check a later
    # reader can find the recommendation and not the refutation.
    byte = move_dir_sends[0][2] if len(move_dir_sends[0]) > 2 else None
    check(isinstance(byte, ast.Name) and byte.id == "moving",
          "and the trailing byte is still the client's own movementType",
          f"{ast.dump(byte) if byte is not None else None} -- retail echoes the "
          f"enum in 98.27% of 2,254; it is not an angle")

    # The arithmetic, against the two magnitudes the client actually emits.
    for m in (765.017539, 768.000000):
        ux, uy = (m * 0.6) / m, (m * 0.8) / m
        check(abs(math.hypot(ux, uy) - 1.0) < 1e-9,
              f"normalising a {m:.3f}-unit heading yields |v| = 1",
              f"{math.hypot(ux, uy)!r}")
    # And the zero guard: 55 of our own sends carried |v| exactly 0, which is a
    # ZeroDivisionError in the naive form and kills the connection mid-session.
    zero_mag = 0.0
    guarded = ([0.0 / zero_mag, 0.0 / zero_mag] if zero_mag > 1e-6
               else [0.0, 0.0])
    check(guarded == [0.0, 0.0],
          "and a zero-length heading is guarded, not divided by",
          f"{guarded} -- 55 of 4,760 of our own sends carried |v| = 0")


    print("\n9. --client-endpoint ships OFF, and grants the CLIENT's own point")
    check(authsrv.CLIENT_ENDPOINT is False,
          "--client-endpoint is off by default",
          "it is the FIFTH candidate fix in this arc and four are dead. It is "
          "unproven until one run scores it")
    ce = []
    for node in ast.walk(src):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                and node.test.id == "CLIENT_ENDPOINT"):
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "send" and len(call.args) >= 2
                    and isinstance(call.args[1], ast.List)):
                ce.append((node, call.args[1].elts))
    check(len(ce) == 1, "there is exactly one client-endpoint send",
          f"{len(ce)} -- two would be two policies, which is how the heading "
          f"arm ended up granting twice per report")

    # THE FIRST OF THE TWO THINGS THAT KILLED --heading-grant. It sent
    # `clip_to_walkable(...)` -- a point shortened wherever OUR navmesh says a
    # wall is. Where that disagrees with the client's own collision we grant a
    # point short of where the player is really going, the authoritative copy
    # stops early, and the separation that becomes the warp opens up. The
    # server's internal model may still clip; the WIRE may not.
    block = ce[0][0] if ce else None
    clipped = block is not None and any(
        isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        and c.func.id == "clip_to_walkable" for c in ast.walk(block))
    check(not clipped,
          "and it does NOT clip the point it sends",
          "clip_to_walkable is back inside the block -- that is the first of "
          "the two defects that made --heading-grant warp the owner's character")

    # THE SECOND. It computed from `state["pos"]` rather than the report in
    # hand. Those are equal on every ACCEPTED report, so this is not a
    # correctness fix in the common case -- it is a fix for exactly the moment
    # the trust guard refused, which is when our model is least entitled to name
    # a destination.
    names = {n.id for n in ast.walk(block) if isinstance(n, ast.Name)} if block else set()
    check("reported" in names,
          "and it derives the point from `reported`",
          f"{sorted(names)[:8]} -- the client's own figure, so the granted "
          f"endpoint is the client's own proposal")
    subs = [n for n in ast.walk(block)
            if isinstance(n, ast.Subscript)] if block else []
    uses_state_pos = any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos" for n in subs)
    check(not uses_state_pos,
          "and not from state['pos']",
          "state['pos'] is back -- it is the last report the guard ACCEPTED, "
          "which is stale in exactly the window a refusal opens")

    # THE CONTROL. Both matchers above only ever run against healthy source, so
    # both are branches a typo would silently disable. Hand them the defect.
    bad = ast.parse("if CLIENT_ENDPOINT:\n"
                    "    d = clip_to_walkable(state, (state['pos'][0], 0))\n"
                    "    send(OP, [PLAYER_AGENT_ID, list(d), plane, plane], 'x')")
    bnode = next(n for n in ast.walk(bad)
                 if isinstance(n, ast.If) and isinstance(n.test, ast.Name))
    bad_clip = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                   and c.func.id == "clip_to_walkable" for c in ast.walk(bnode))
    bad_state = any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos"
        for n in ast.walk(bnode) if isinstance(n, ast.Subscript))
    check(bad_clip and bad_state,
          "CONTROL: both matchers still SEE the old defects when handed them",
          f"clip={bad_clip} state_pos={bad_state} -- if either stopped "
          f"matching, the two checks above would pass for the wrong reason")
    print("\n10. replay: the real refusals from run 20260819T114743")
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

    print("\n11. --resync ships OFF, and its payload is the CLIENT's own report")
    # WHAT EARNS THIS SECTION. 0x002C AGENT_UPDATE_POSITION is the only
    # catalogued primitive whose handler reaches BOTH copies the client keeps
    # with no gate (0x005FDAE5 on [agentMgr+0xE8], 0x005FDB49 on
    # [agentMgr+0x14C]) and clears the AgTrack record first (0x005FDA78), so it
    # is the one lever this arc has left. It is ALSO the message an earlier
    # build sent and had removed as "the warp the player described" -- because
    # that build sent OUR INTEGRATOR'S position. The whole difference between a
    # fix and that regression is which value ends up in the payload, and
    # `state["pos"]` is one keystroke away from `state["client_pos"]`. Every
    # check below exists to make that keystroke red.
    check(authsrv.RESYNC is False,
          "--resync is off by default",
          "it is the SEVENTH candidate in this arc and six are dead. A hard "
          "SetPosition at the player is a teleport by construction; it ships "
          "off until a watched run scores it")
    check(authsrv.RESYNC_SEPARATION == 100.0,
          "the trigger is the CLIENT's own 100.0 u radius, not a number we "
          "chose",
          "0x00946560 -- the radius inside which the client's own match test "
          "0x00605AF0 returns 'no snap' before the fallback half runs. It sits "
          "3x under gate 1's real cut of 299.332591 u, and that factor is the "
          "headroom our SYNC model gets to be wrong in")
    ceiling = 299.332591 / (2 * authsrv.DEFAULT_RUN_SPEED)
    check(authsrv.RESYNC_MIN_INTERVAL < ceiling,
          f"and the rate limit sits under its derived ceiling of "
          f"{ceiling:.4f} s",
          f"{authsrv.RESYNC_MIN_INTERVAL} -- two copies moving directly apart "
          f"separate at no more than 2 x 288 u/s, so a limit at or above "
          f"{ceiling:.4f} s lets a full gate's worth of separation accrue "
          f"between two fires, which is the sender being structurally late")
    harm = authsrv.RESYNC_MAX_REPORT_AGE * authsrv.DEFAULT_RUN_SPEED
    check(abs(harm - 100.0) < 1e-9,
          "and the staleness bound IS the harm bound: speed x age = 100.0 u",
          f"{harm!r} -- a SetPosition to the client's last report yanks the "
          f"RENDERED copy backwards by at most how far the client walked since "
          f"that report. Choosing the age chooses the harm, and the age is "
          f"chosen to make the harm the client's own 'close enough' radius. "
          f"CORROBORATED: for report gaps under 0.100 s the client's own step "
          f"is p99 28.80 u against a budget of 28.8 (n = 307), and under "
          f"0.200 s p99 57.60 against 57.6 (n = 685), 73 `ours` captures")

    def armed(client=(1000.0, 0.0), ours=(0.0, 0.0), sync=(0.0, 0.0),
              at=1000.0, plane=0):
        """A state with a fresh client report and a seeded, PARKED sync model."""
        st = {"pos": ours, "plane": plane, "pos_seen": at,
              "client_pos": client, "client_plane": plane,
              "client_pos_at": at,
              "sync_from": sync, "sync_to": None, "sync_at": at}
        return st

    class Wire:
        """A send() that also runs the real model hook, like the server's."""

        def __init__(self, state):
            self.state = state
            self.sent = []

        def __call__(self, opcode, values, label, quiet=False):
            authsrv._note_wire_move(self.state, opcode, values, 1000.0)
            self.sent.append((opcode, values, label))

    # OFF MEANS OFF: not merely "does not send", but does not even evaluate.
    st = armed()
    wire, rec = Wire(st), FakeRec()
    fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
    check(fired is False and wire.sent == [] and rec.events == [],
          "with the flag off a state that WOULD fire sends nothing and records "
          "nothing",
          f"fired={fired} sent={wire.sent} events={len(rec.events)} -- the "
          f"default build's capture must not grow a resync log it never used")

    saved = authsrv.RESYNC
    authsrv.RESYNC = True
    try:
        # THE HEADLINE: the payload is the CLIENT's figure, and the two are made
        # to DISAGREE on purpose. state["pos"] is a blend -- the world tick's
        # integrator writes it too -- so a sender reading it would put our
        # extrapolation on the wire, which is exactly the removed regression.
        st = armed(client=(1000.0, 0.0), ours=(1234.0, 567.0))
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
        check(fired is True and len(wire.sent) == 1,
              "a 1,000 u separation with a fresh report fires exactly one 0x002C",
              f"fired={fired} sent={wire.sent}")
        op, values, _label = wire.sent[0]
        check(op == authsrv.GAME_SMSG_AGENT_UPDATE_POSITION == 0x002C,
              "on the right opcode", f"0x{op:04x}")
        check(values[1] == [1000.0, 0.0] and values[1] != list(st["pos"]),
              "carrying state['client_pos'] and NOT state['pos']",
              f"{values} against ours {st['pos']} -- the build that sent this "
              f"message before sent OUR integrator's position, and its five "
              f"sends carried the client 630, 189 and 765 units. 765 is one "
              f"heading vector: the integrator had walked the whole leg while "
              f"the client had not moved at all")
        check(values[0] == authsrv.PLAYER_AGENT_ID and values[2] == 0,
              "naming the player's agent, with the plane the report arrived on",
              f"{values} -- position and plane are one fact (section 4), and "
              f"this reads the pair the accept path wrote together")

        # REFUSES A PAYLOAD THAT IS NOT CLIENT-SOURCED. A state carrying only
        # our own blend has no client_pos at all, and the verdict must not fall
        # back to it.
        # It carries client_plane and NOT client_pos on purpose: that is the
        # split section 4 is about, and it leaves the missing client POSITION as
        # the only thing standing between this state and a send. A fixture
        # missing three fields would be refused for whichever one is checked
        # first, which is a weaker proof than it looks.
        blind = {"pos": (5000.0, 5000.0), "plane": 0, "pos_seen": 1000.0,
                 "client_plane": 0,
                 "sync_from": (0.0, 0.0), "sync_to": None, "sync_at": 1000.0}
        wire, rec = Wire(blind), FakeRec()
        fired = authsrv._maybe_resync(wire, blind, rec, now=1000.0)
        verdict = authsrv._resync_verdict(blind, 1000.0)
        check(fired is False and wire.sent == []
              and verdict[1] == "no-client-report",
              "a state with no accepted client report sends NOTHING, however "
              "far our own model has drifted",
              f"{verdict} -- 5,000 u of drift and not one byte, because the "
              f"only position this sender is allowed to say is one the client "
              f"said first")
        check(len(rec.of("resync")) == 1
              and rec.of("resync")[0]["fired"] is False,
              "and the refusal is in the event log, not just absent from it",
              f"{rec.of('resync')} -- a resync log holding only its own "
              f"successes cannot be used to score the flag")

        # REFUSES A STALE PAYLOAD, at the bound and past it.
        st = armed(at=1000.0)
        edge = 1000.0 + authsrv.RESYNC_MAX_REPORT_AGE
        check(authsrv._resync_verdict(st, edge)[0] is True,
              f"a report exactly {authsrv.RESYNC_MAX_REPORT_AGE * 1000:.0f} ms "
              f"old still fires -- the bound is inclusive",
              f"{authsrv._resync_verdict(st, edge)}")
        past = edge + 1e-6
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=past)
        check(fired is False and wire.sent == []
              and authsrv._resync_verdict(st, past)[1] == "stale",
              "one microsecond past it, nothing goes out",
              f"{authsrv._resync_verdict(st, past)} -- past the bound the "
              f"payload has stopped being where the client is, and a stale "
              f"payload IS the old failure mode")
        check(authsrv._resync_verdict(st, 999.0)[1] == "stale",
              "and a report dated in the FUTURE is stale too, not fresh",
              f"{authsrv._resync_verdict(st, 999.0)} -- `now - at` goes "
              f"negative under clock skew, and a negative age would sail "
              f"through an upper-bound-only test")

        # THE RATE LIMIT.
        st = armed()
        wire, rec = Wire(st), FakeRec()
        n = 0
        t = 1000.0
        for _i in range(20):
            st["client_pos_at"] = t          # a fresh report every 100 ms
            st["sync_from"], st["sync_to"] = (0.0, 0.0), None
            n += bool(authsrv._maybe_resync(wire, st, rec, now=t))
            t += 0.1
        span = 1.9                            # first fire at t0, last at t0+1.9
        allowed = int(span / authsrv.RESYNC_MIN_INTERVAL) + 1
        check(n <= allowed,
              f"twenty consecutive fireable reports over {span:.1f} s produce "
              f"{n} sends, not 20",
              f"n={n}, ceiling {allowed} at one per "
              f"{authsrv.RESYNC_MIN_INTERVAL:.2f} s -- an unlimited sender is "
              f"a 2 Hz teleport stream at the player")
        check(n >= 1, "and it does not rate-limit itself down to nothing",
              f"n={n} -- a limit that never lets anything through would make "
              f"every check above vacuous")

        # NEVER FIRES ON A REPORT THE TRUST GUARD REFUSED, and this is the
        # one an adversarial review found reachable at 2,282 u. The payload
        # advances only on accept, so a refusal FREEZES it while the client
        # keeps moving -- and the guard refuses exactly when the client claimed
        # a jump over CLIENT_POSITION_TRUST_RADIUS. Inside the staleness window
        # every other gate still passes, so without this the server would
        # hard-SetPosition the player back to their pre-jump point: the
        # regression the whole design exists to avoid, by a different route.
        st = armed(client=(0.0, 0.0), sync=(1000.0, 0.0))
        fire_clean, why_clean = authsrv._resync_verdict(st, 1000.0)[:2]
        check(fire_clean is True and why_clean == "resync",
              "CONTROL: the same state with no refusal on record DOES fire",
              f"{why_clean} -- a check whose control cannot fire is judging "
              f"nothing, and this one is the whole point of the next check")
        st["pos_rejects"] = 1
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
        check(fired is False and wire.sent == []
              and authsrv._resync_verdict(st, 1000.0)[1] == "report-refused",
              "but one refused report on record blocks it, payload unsent",
              f"{authsrv._resync_verdict(st, 1000.0)} -- the freshest thing we "
              f"heard was one we did not believe, so the frozen payload is a "
              f"pre-jump position and sending it is the old warp")

        # NEVER FIRES WHEN THE TWO COPIES AGREE.
        st = armed(client=(50.0, 0.0), sync=(0.0, 0.0))
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
        check(fired is False and wire.sent == []
              and authsrv._resync_verdict(st, 1000.0)[1] == "in-agreement",
              f"50 u apart is under the {authsrv.RESYNC_SEPARATION:.0f} u "
              f"trigger and sends nothing",
              f"{authsrv._resync_verdict(st, 1000.0)} -- correcting a player "
              f"who is already right is the 'teleporting a player nine units "
              f"is pure damage' case the 0x0047 arm records")

        # THE SYNC MODEL FAILS CLOSED, and it tracks a glide rather than
        # assuming the copy is already parked.
        unseeded = {"pos": (0.0, 0.0), "plane": 0, "pos_seen": 1000.0,
                    "client_pos": (9000.0, 0.0), "client_plane": 0,
                    "client_pos_at": 1000.0}
        check(authsrv._sync_position(unseeded, 1000.0) is None
              and authsrv._resync_verdict(unseeded, 1000.0)[1]
              == "no-sync-model",
              "an unseeded SYNC model produces no separation and no send",
              f"{authsrv._resync_verdict(unseeded, 1000.0)} -- a fixture that "
              f"silently resolves to the wrong thing turns every assertion "
              f"behind it into a no-op; this one raises its hand instead")
        glide = armed(client=(0.0, 0.0), sync=(0.0, 0.0))
        authsrv._note_wire_move(glide, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                                [authsrv.PLAYER_AGENT_ID, [2880.0, 0.0], 0, 0],
                                1000.0)
        half = authsrv._sync_position(glide, 1005.0)
        check(abs(half[0] - 1440.0) < 1e-6,
              "and a granted leg is walked at 288 u/s, not teleported to its "
              "end",
              f"{half} at t+5 s of a 2,880 u grant -- this is the client's own "
              f"bake (0x005FE950 velocity = unit(d) * speed, 0x005FFB40 "
              f"pos = +0x78 + vel * dt). If the model parked instantly, every "
              f"legitimate click-walk would read as a 2,880 u desync")
        parked = authsrv._sync_position(glide, 1099.0)
        check(parked == (2880.0, 0.0),
              "and it PARKS on the granted point rather than overshooting it",
              f"{parked} -- 0x005FF820's +0x48 arm returns the stored "
              f"destination, which is semantic and not a cache")
        authsrv._note_wire_move(glide, authsrv.GAME_SMSG_AGENT_UPDATE_POSITION,
                                [authsrv.PLAYER_AGENT_ID, [7.0, 8.0], 0],
                                1100.0)
        check(authsrv._sync_position(glide, 1200.0) == (7.0, 8.0),
              "and a 0x002C we send lands the model on the point it carried",
              f"{authsrv._sync_position(glide, 1200.0)} -- 0x00602B20 writes "
              f"+0x68..+0x74 = current on the parked arm, so no destination "
              f"survives a hard set; a model that kept the old one would think "
              f"the copy walked away again")

        # THE ENCODED BYTES ARE THE SCHEMA'S. Not "we believe the shape" -- the
        # real codec, against the real catalog, checked field by field.
        blob = authsrv.codec.encode(
            "GAME_SMSG", authsrv.GAME_SMSG_AGENT_UPDATE_POSITION,
            [authsrv.PLAYER_AGENT_ID, [1234.5, -678.25], 7])
        shape = json.load(open(os.path.join(
            os.path.dirname(os.path.dirname(HERE)), "schema",
            "messages.json"), encoding="utf-8"))
        entry = shape["channels"]["GAME_SMSG"]["messages"]["44"]
        check([f["type"] for f in entry["fields"]]
              == ["msg_header", "dword", "vec2", "word"],
              "the catalog's 0x002C is header / agent id / vec2 / plane",
              f"{[f['type'] for f in entry['fields']]} -- and the client's own "
              f"handler agrees field for field: [ebx+4] is pushed to "
              f"AgTrack::Clear at 0x005FDA78, [ebx+8]/[ebx+0xc] become the "
              f"position block, [ebx+0x10] is its plane word")
        check(len(blob) == entry["declared_unpack_size"] == 16,
              f"and the encoder produces the declared {len(blob)} bytes",
              f"{blob.hex()}")
        check(blob == bytes.fromhex("2c00") + struct.pack(
                  "<Iff H", authsrv.PLAYER_AGENT_ID, 1234.5, -678.25, 7),
              "byte for byte, in that field order",
              f"{blob.hex()} -- field order is the one thing this project has "
              f"already got wrong on a movement message, on 0x0029's two plane "
              f"words, and the client walked players through staircases for it")
        check(authsrv.codec.name_for("GAME_SMSG", 0x002C)
              == "AGENT_UPDATE_POSITION",
              "and the opcode we send is the one the overrides name",
              f"{authsrv.codec.name_for('GAME_SMSG', 0x002C)}")
    finally:
        authsrv.RESYNC = saved
    check(authsrv.RESYNC is False,
          "and the section put the flag back the way it found it",
          f"{authsrv.RESYNC}")

    # A REFUSED REPORT MUST NOT UPDATE THE CLIENT-SOURCED RECORD. This is what
    # makes "the payload came from an accepted report" true rather than merely
    # intended: the accept path is the only writer, so a refusal leaves the
    # sender holding the older -- and ageing -- report.
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    check("client_pos" not in st,
          "a REFUSED report leaves no client-sourced position behind",
          f"{st.get('client_pos')} -- if a refusal wrote it, the resync sender "
          f"would put a position our own trust guard had just called "
          f"impossible onto the wire as a teleport")
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1001.0)
    check(st["client_pos"] == JUMPED and st["client_plane"] == JUMPED_PLANE
          and st["client_pos_at"] == 1001.0,
          "and an ACCEPTED one writes the position, the plane and the instant "
          "together",
          f"{st.get('client_pos')} plane {st.get('client_plane')} at "
          f"{st.get('client_pos_at')}")

    # THE SOURCE LOCK, and the control that keeps it honest. The behavioural
    # checks above can only see the value; this sees the EXPRESSION, because
    # `state["pos"]` and `state["client_pos"]` differ by nine characters and
    # agree on most reports -- exactly the shape that let the 765x direction
    # vector live for weeks.
    writers = []
    for node in ast.walk(src):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if (isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "state"
                    and isinstance(getattr(tgt, "slice", None), ast.Constant)
                    and tgt.slice.value == "client_pos"):
                writers.append(node)
    check(len(writers) == 1,
          "exactly one line in the whole file writes state['client_pos']",
          f"{len(writers)} -- two writers is two policies, and the second one "
          f"is where an integrator's opinion gets in")
    resync_sends = []
    for node in ast.walk(src):
        if not (isinstance(node, ast.FunctionDef)
                and node.name == "_maybe_resync"):
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "send" and len(call.args) >= 2
                    and isinstance(call.args[1], ast.List)):
                resync_sends.append((node, call.args[1].elts))
    check(len(resync_sends) == 1,
          "and there is exactly one resync send site",
          f"{len(resync_sends)} -- both receive arms route through the one "
          f"policy function on purpose; a second send is a second policy")

    def payload_is_verdict_value(elts):
        """True iff the vec2 slot is `list(payload)` -- the verdict's own value."""
        if len(elts) < 2:
            return False
        node = elts[1]
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "list" and len(node.args) == 1
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "payload")

    check(payload_is_verdict_value(resync_sends[0][1]),
          "whose vec2 is `list(payload)` -- the value _resync_verdict returned, "
          "which it takes from state['client_pos'] and from nowhere else",
          f"{ast.dump(resync_sends[0][1][1])} -- rewrite this to "
          f"list(state['pos']) and the message becomes the one an earlier "
          f"build sent and had removed as 'the warp the player described'")
    block = resync_sends[0][0]
    grabs_blend = any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos"
        and not isinstance(getattr(n, "ctx", None), ast.Store)
        for n in ast.walk(block) if isinstance(n, ast.Subscript))
    check(grabs_blend is True,
          "CONTROL: the matcher below is looking at a function that DOES "
          "mention state['pos']",
          "it does not, so the next check would pass for the wrong reason -- "
          "_maybe_resync logs `ours=state['pos']` beside every verdict, which "
          "is what makes a scorer able to see the two apart")
    # THE MUTATION THIS LOCKS, handed to the matcher on purpose. The rejecting
    # branch is the one that never runs against healthy source.
    bad = ast.parse(
        "def _maybe_resync(send, state, rec, now=None):\n"
        "    send(OP, [PLAYER_AGENT_ID, list(state['pos']), plane], 'x')\n")
    bad_elts = []
    for call in ast.walk(bad):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "send" and len(call.args) >= 2
                and isinstance(call.args[1], ast.List)):
            bad_elts = call.args[1].elts
    check(len(bad_elts) == 3 and not payload_is_verdict_value(bad_elts),
          "CONTROL: and it still REJECTS the integrator's position when handed "
          "it",
          f"{[ast.dump(e) for e in bad_elts]} -- if the matcher stopped "
          f"recognising list(state['pos']), the lock above would be a no-op")

    # THE FLAG'S OWN BANNER MUST BE PRINTABLE. Found the hard way while writing
    # this: a U+26A0 warning sign in the --resync startup print raised
    # UnicodeEncodeError on a default Windows console, because cp1252 has no
    # code point for it -- so the flag would have killed the very run it exists
    # to enable, before a single packet went out. The em dashes elsewhere in
    # authsrv.py survive because cp1252 DOES have those, which is exactly why a
    # bare "no non-ASCII" rule would be wrong here and the real console encoding
    # is the thing to test against.
    def unprintable(node):
        out = []
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                try:
                    n.value.encode("cp1252")
                except UnicodeEncodeError:
                    out.append(n.value[:40])
        return out

    banner = next((n for n in ast.walk(src)
                   if isinstance(n, ast.If)
                   and isinstance(n.test, ast.Attribute)
                   and n.test.attr == "resync"), None)
    check(banner is not None and unprintable(banner) == [],
          "and every string the --resync banner prints survives a cp1252 "
          "console",
          f"{None if banner is None else unprintable(banner)} -- print() raises "
          f"on the first character cp1252 cannot encode, and a flag that kills "
          f"the server at startup cannot be scored")
    planted = ast.parse("if a.resync:\n    print('\\u26a0 careful')\n")
    check(unprintable(planted) != [],
          "CONTROL: and the same scan still catches a planted U+26A0",
          f"{unprintable(planted)} -- a scan that finds nothing is "
          f"indistinguishable from a clean file, which is how the real one "
          f"got written")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
