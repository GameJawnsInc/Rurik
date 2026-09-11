"""Checks for ROUTER-B2 -- the `--router` click policy in authsrv.py.

studies/movement/ROUTER.md sec.4 is the spec; routerbench (and its own
test) is the offline validation of the pathfinder against retail's
contract. THIS file checks the wiring: the answer function's five verdicts
(verbatim / routed / clip-fallback / refused / kbd-drop) on a stub mesh,
the chain scheduler's cadence arithmetic and terminal handling, the
abandon rules, the retail wire grammar (speed ONCE per chain, matched
plane pairs, per-waypoint planes), and the source locks that keep the
recv-loop attach points, the handler branch, and the composition refusals
from drifting. Bare-machine: no vault, no client, no sockets.

Section 5 (MOVECODE-1z-v, 2026-09-03): the router is the DEFAULT, and the
two conditions 1z-u named ship with it -- (a) the click-leg record is
re-armed to the routed leg (chain legs included), so PRESS ENDS THE WALK
re-pins the body on the leg it walks and not on the raw click chord; (b)
the one-leg verbatim answer's field 4 is the mesh's plane under the
modelled sync copy. Both known-bad arms are driven, and a press or a
follow now abandons a live chain.

Section 6 (MOVECODE-1z-w, 2026-09-03): the routing ORIGIN's own plane word
(the mesh under the body model, the report's plane where offered or
unknowable) feeds route()'s start preference, the clip-fallback's stop
carry and every router_route row; and a cast that begins abandons a live
chain, the third opcode of ROUTER-Q8.

The kbd-drop pair in section 1 grew a REVERT ARM on 2026-09-05
(MOVECODE-1z-bh, studies/review/MOVEMENT-2026-09-04.md sec.1.7). The drop is
OURS, not retail's, and until 1z-bh `--answer-kbd-click` was read only by
`_grant_verdict` -- the legacy path `router_answer_click` bypasses -- so under
the shipped ROUTER = True a shipped behaviour had no arm that could convict
it. Both arms are now driven off the same click: flag OFF is the kbd-drop row,
flag ON routes it and logs a `kbd-answered` PASS-THROUGH row (marked `arm` and
`pass_through`) ahead of the real verdict row, and the global is restored.
"""

import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/

import checks                                                  # noqa: E402
import authsrv                                                 # noqa: E402

# Floor from the 2026-08-26 green run: 68 checks, all unconditional
# (51 at the B2 landing; +6 review round: the sampling-gate pair, two new
# composition refusals, two fine-step source locks; +7 ROUTER-B4: planes
# through route(), corridor planes on the grants, the tour cap and its
# SLACK control; +4 ROUTER-B5: the origin snap answered-not-refused, the
# streak counting, the true-hole refusal; +5 2026-08-30: the
# a2_matched_field4 gating pattern and its contract line, after a second
# analysis read the three unconditional call sites as a leak and proposed
# gating them -- which was measured to turn this file's corridor-plane
# checks red).
# +30 2026-09-03 MOVECODE-1z-v (section 5: the default, both conditions,
# the press/follow abandons); +11 MOVECODE-1z-w (section 6: the origin's
# plane word, the cast abandon). 114 on the green run.
# +7 section 6, MOVECODE-1z-bb; +5 MOVECODE-1z-bh (the kbd-drop's revert arm:
# `--answer-kbd-click` now reaches router_answer_click, and the drop it reverts
# is OURS rather than retail's -- review sec.1.7). 126 on the green run.
LEDGER = checks.Ledger("router wiring", floor=126)
check = checks.adopt_named(LEDGER)

SPEED_OP = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED
MOVE_OP = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT


class FakeRec:
    def __init__(self):
        self.rows = []

    def event(self, kind, **kw):
        kw["kind"] = kind
        self.rows.append(kw)


class FakeSend:
    def __init__(self):
        self.sent = []

    def __call__(self, opcode, payload, label="", quiet=False):
        self.sent.append((opcode, payload, label))


class StubPM:
    """A mesh with one wall: x in (100, 200) is unwalkable. Routes that
    cross it detour through (150.0, 500.0); everything else is a straight
    line. plane 3 everywhere."""

    def __init__(self, route_result="auto", route_planes=None,
                 plane_fn=None, seam_stop=None):
        self.route_result = route_result
        self.route_planes = route_planes
        self.last_planes = None
        self.plane_fn = plane_fn      # (x, y, prefer) -> plane or None
        self.seam_stop = seam_stop    # x of a BLIND seam the seam-aware ray stops at

    def walkable(self, x, y):
        return not (100.0 < x < 200.0) or y > 400.0

    def containing(self, x, y):
        return [1] if self.walkable(x, y) else []

    def plane_at(self, x, y, prefer=None):
        if self.plane_fn is not None:
            return self.plane_fn(x, y, prefer)
        return 3

    def clip(self, x0, y0, x1, y1, step=16.0):
        d = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(d / step))
        best = (x0, y0)
        for i in range(1, n + 1):
            f = i / n
            p = (x0 + f * (x1 - x0), y0 + f * (y1 - y0))
            if not self.walkable(p[0], p[1]):
                return best
            best = p
        return (x1, y1)

    def seam_clip(self, x0, y0, x1, y1, plane, step=2.0):
        """pathmap.seam_clip's contract on the stub: clip(), then stop short at
        a fake blind seam at x = seam_stop if the ray crosses it (MOVECODE-1z-bb)."""
        p = self.clip(x0, y0, x1, y1, step=step)
        xs = self.seam_stop
        if xs is not None and x1 != x0 and min(x0, p[0]) < xs < max(x0, p[0]):
            f = (xs - x0) / (x1 - x0)
            return (xs, y0 + f * (y1 - y0))
        return p

    def nearest_walkable(self, x, y, radius):
        if self.walkable(x, y):
            return (x, y, 0.0)
        if 100.0 < x < 200.0 and y <= 400.0:
            d = min(x - 100.0, 200.0 - x)
            if d <= radius:
                edge = 100.0 if x - 100.0 <= 200.0 - x else 200.0
                return (edge, y, d)
        return None

    def route(self, x0, y0, x1, y1, start_plane=None, goal_plane=None,
              with_planes=False):
        self.last_planes = (start_plane, goal_plane)
        pts = self._route(x0, y0, x1, y1)
        if pts is None:
            return None
        if with_planes:
            planes = (self.route_planes if self.route_planes is not None
                      else [3] * len(pts))
            return pts, planes
        return pts

    def _route(self, x0, y0, x1, y1):
        if self.route_result != "auto":
            return self.route_result
        if not self.walkable(x0, y0) or not self.walkable(x1, y1):
            return None
        if self.clip(x0, y0, x1, y1) == (x1, y1):
            return [(x0, y0), (x1, y1)]
        # A genuinely clean detour over this mesh: up the x<=100 side,
        # across the y>400 shelf, down past the wall.
        return [(x0, y0), (100.0, 500.0), (200.0, 500.0), (x1, y1)]


def base_state(pm=None, pos=(0.0, 0.0)):
    return {"pathmap": pm if pm is not None else StubPM(),
            "pos": list(pos), "plane": 3, "kbd_moving_at": None,
            "grant_pending": {"stale": True}}


def answer(state, dest, dest_plane=3, cur_plane=3):
    send, rec = FakeSend(), FakeRec()
    handled = authsrv.router_answer_click(
        send, state, 1, rec, dest, dest_plane, cur_plane,
        dest_plane, cur_plane)
    return handled, send.sent, rec.rows


def main():
    print("== 1: the five click verdicts ==")

    # verbatim: straight line clear -> one leg, wire-identical shape.
    st = base_state()
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("clear line is handled", handled)
    check("verbatim sends speed then the move",
          [op for op, _p, _l in sent] == [SPEED_OP, MOVE_OP])
    check("verbatim grants the exact click point",
          sent[1][1][1] == [50.0, 50.0])
    check("verbatim leaves no chain", st.get("router_chain") is None)
    check("verbatim row emitted",
          any(r["kind"] == "router_route" and r["verdict"] == "verbatim"
              for r in rows))
    check("the answered click supersedes any held click",
          st["grant_pending"] is None)
    check("our integrator walks the granted leg",
          st["dest"] == (50.0, 50.0) and st["clipped"] is False)

    # routed: wall in the way -> first leg now, chain armed.
    st = base_state()
    handled, sent, rows = answer(st, (300.0, 0.0))
    check("blocked line is handled", handled)
    check("routed sends speed ONCE then the first leg only",
          [op for op, _p, _l in sent] == [SPEED_OP, MOVE_OP]
          and sent[1][1][1] == [100.0, 500.0])
    chain = st.get("router_chain")
    check("the chain is armed with the remaining legs",
          chain is not None
          and chain["queue"] == [(200.0, 500.0), (300.0, 0.0)]
          and chain["i"] == 1 and chain["n"] == 3)
    check("routed row names the leg count",
          any(r["kind"] == "router_route" and r["verdict"] == "routed"
              and r["n_wp"] == 3 for r in rows))
    check("first leg's planes are matched (field4 == field3)",
          sent[1][1][2] == sent[1][1][3] == 3)

    # THE SAMPLING GATE (review F1): a route whose leg crosses the wall --
    # as route()'s 16u gate could pass over a sub-sample sliver -- must
    # NOT be granted; the 2.0u pre-send re-clip demotes it to no-route
    # and the clip-fallback answers instead.
    st = base_state(StubPM(route_result=[(0.0, 0.0), (150.0, 300.0),
                                         (300.0, 0.0)]))
    handled, sent, rows = answer(st, (300.0, 0.0))
    check("a wall-crossing route is refused by the pre-send re-clip",
          handled
          and any(r["kind"] == "router_route"
                  and r["verdict"] == "clip-fallback"
                  and r["reason"] == "no-path-or-gate" for r in rows))
    check("what fires instead is the fallback's own clean stop",
          sent[-1][1][1][0] <= 100.0 + 1e-6
          and st.get("router_chain") is None)

    print("== 1b: ROUTER-B4 -- planes through, tours capped ==")

    # The click's planes reach route(): the wiring must pass the
    # player's plane and the clicked surface's plane (run 2's twelve-
    # waypoint island tour was plane-blind endpoint selection).
    st = base_state()
    pm = st["pathmap"]
    answer(st, (50.0, 50.0), dest_plane=7, cur_plane=3)
    check("route() receives start_plane and goal_plane",
          pm.last_planes == (3, 7))

    # Corridor-true planes ride the grants: a multi-leg route whose
    # corridor names planes [3, 5, 9, 7] must send 5 on leg 1, 9 on leg
    # 2, and the CLIENT's named plane on the terminal.
    pm = StubPM(route_result=[(0.0, 0.0), (50.0, 500.0), (250.0, 500.0),
                              (300.0, 0.0)],
                route_planes=[3, 5, 9, 7])
    st = base_state(pm)
    handled, sent, rows = answer(st, (300.0, 0.0), dest_plane=8)
    check("first leg carries the corridor's plane, matched",
          sent[-1][1][2] == 5 and sent[-1][1][3] == 5)
    chain = st.get("router_chain")
    check("the chain queues the corridor planes",
          chain is not None and chain["planes"] == [9, 7])
    send2, rec2 = FakeSend(), FakeRec()
    authsrv.router_chain_tick(send2, st, 1, rec2, now=time.time() + 999.0)
    authsrv.router_chain_tick(send2, st, 1, rec2, now=time.time() + 9999.0)
    mids = [p for _op, p, _l in send2.sent]
    check("interior leg sends its corridor plane, terminal the client's",
          len(mids) == 2 and mids[0][2] == 9 and mids[1][2] == 8)

    # The tour cap: a route 4x+800u longer than the straight line is not
    # an answer, it is the run-2 island tour (11.8x and 7.7x observed);
    # it demotes to the clip-fallback with its own named reason.
    tour = [(0.0, 0.0), (0.0, 3000.0), (300.0, 3000.0), (300.0, 0.0)]
    st = base_state(StubPM(route_result=tour))
    handled, sent, rows = answer(st, (300.0, 0.0))
    check("an island tour is refused as a route",
          any(r["kind"] == "router_route"
              and r.get("reason") == "tour-capped" for r in rows))
    check("the capped click gets the fallback's stop, not the tour",
          st.get("router_chain") is None
          and sent and sent[-1][1][1][0] <= 100.0 + 1e-6)
    # ...and a legitimate short-range corner detour does NOT trip the
    # cap: ratio ~4.9x on a 112u click, but the excess (~440u) sits
    # under the SLACK term, which exists exactly so close-range
    # cornering is never mistaken for an island tour.
    st = base_state(StubPM(route_result=[(0.0, 0.0), (0.0, 250.0),
                                         (100.0, 250.0), (100.0, 50.0)]))
    handled, sent, rows = answer(st, (100.0, 50.0))
    check("a short corner detour survives the cap",
          any(r["kind"] == "router_route" and r.get("verdict") == "routed"
              for r in rows)
          and not any(r.get("reason") == "tour-capped" for r in rows))

    print("== 1c: ROUTER-B5 -- the origin snap and the refusal streak ==")

    # An origin 8u inside the wall (run 3's measured penetration class)
    # snaps to the edge and the click is ANSWERED, not refused -- the
    # refusal lock-in that armed the 3.2km reconcile snap cannot start
    # from an edge-penetrated stand.
    st = base_state(pos=(108.0, 0.0))
    handled, sent, rows = answer(st, (50.0, 0.0))
    row = next(r for r in rows if r["kind"] == "router_route")
    check("an edge-penetrated origin is snapped and answered",
          row["verdict"] == "verbatim" and row.get("snapped") == 8.0)
    check("the answered click resets the refusal streak",
          st.get("router_refusal_streak") == 0)

    # A stand deeper than the radius still refuses -- and the streak
    # counts, so the run-3 silence is at least LOUD now.
    st = base_state(pos=(150.0, 0.0))
    _h, _s, rows1 = answer(st, (50.0, 0.0))
    _h, _s, rows2 = answer(st, (60.0, 0.0))
    r1 = next(r for r in rows1 if r["kind"] == "router_route")
    r2 = next(r for r in rows2 if r["kind"] == "router_route")
    check("a true hole still refuses with the reason named",
          r1["verdict"] == "refused" and r1["reason"] == "origin-off-mesh")
    check("consecutive refusals count a streak on every row",
          r1.get("streak") == 1 and r2.get("streak") == 2)

    # kbd-drop: active keyboard authority.
    st = base_state()
    st["kbd_moving_at"] = authsrv.time.time()
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("keyboard-shadowed click is dropped, nothing sent",
          handled and sent == [])
    check("kbd-drop row emitted",
          any(r["kind"] == "router_route" and r["verdict"] == "kbd-drop"
              for r in rows))

    # ...and the drop's REVERT ARM (MOVECODE-1z-bh, review sec.1.7). The drop
    # is OURS -- REALFIX sec.0.15 is a rapid-PAIR rule and sec.0.14's
    # V-RETAIL-2 measured retail answering 7 of 7 single mid-keyboard clicks
    # -- and until 1z-bh `--answer-kbd-click` was read only by
    # `_grant_verdict`, which this handler bypasses, so under the shipped
    # ROUTER = True the flag was inert and a shipped behaviour had no arm that
    # could convict it. Same click, flag on: routed like any other.
    check("the drop is the shipped path -- ANSWER_KBD_CLICK defaults False",
          authsrv.ANSWER_KBD_CLICK is False)
    _saved_akc = authsrv.ANSWER_KBD_CLICK
    try:
        authsrv.ANSWER_KBD_CLICK = True
        st = base_state()
        st["kbd_moving_at"] = authsrv.time.time()
        handled, sent, rows = answer(st, (50.0, 50.0))
        check("with the flag the same click is ANSWERED, and a grant is sent",
              handled and [op for op, _p, _l in sent] == [SPEED_OP, MOVE_OP]
              and sent[1][1][1] == [50.0, 50.0])
        verdicts = [r["verdict"] for r in rows if r["kind"] == "router_route"]
        check("no kbd-drop row survives the flag; the real verdict follows",
              "kbd-drop" not in verdicts and "verbatim" in verdicts)
        check("the pass-through row names its arm, so a click census can "
              "filter it out of the verdict rows",
              any(r["kind"] == "router_route"
                  and r["verdict"] == "kbd-answered"
                  and r.get("arm") == "answer-kbd-click"
                  and r.get("pass_through") is True for r in rows))
    finally:
        authsrv.ANSWER_KBD_CLICK = _saved_akc
    check("the module global is restored for every later section",
          authsrv.ANSWER_KBD_CLICK is False)

    # refused: origin off-mesh (the P-17 wall-press door, CLOSED).
    st = base_state(pos=(150.0, 0.0))
    handled, sent, rows = answer(st, (300.0, 0.0))
    check("origin-off-mesh refuses, nothing sent",
          handled and sent == [])
    check("the refusal names its reason",
          any(r["kind"] == "router_route" and r["verdict"] == "refused"
              and r["reason"] == "origin-off-mesh" for r in rows))
    check("a refusal drops our own destination",
          st["dest"] is None and st["clipped"] is True)

    # clip-fallback: no route (stub forced), straight line moves partway.
    st = base_state(StubPM(route_result=None))
    handled, sent, rows = answer(st, (300.0, 0.0))
    check("unroutable click falls back to the clip's own stop",
          handled and [op for op, _p, _l in sent] == [SPEED_OP, MOVE_OP])
    stop = sent[1][1][1]
    check("the fallback leg stops short of the wall, never past it",
          stop[0] <= 100.0 + 1e-6 and stop != [300.0, 0.0])
    check("clip-fallback row names the route refusal reason",
          any(r["kind"] == "router_route" and r["verdict"] == "clip-fallback"
              and r["reason"] == "no-path-or-gate" for r in rows))

    # dest off-mesh with no movement possible -> refused, not granted.
    st = base_state(StubPM(route_result=None), pos=(99.0, 0.0))
    handled, sent, rows = answer(st, (150.0, 0.0))
    check("dest-off-mesh with a stuck clip refuses",
          handled and sent == []
          and any(r.get("reason") == "dest-off-mesh" for r in rows))

    # fallthrough: no mesh -> the shipped path decides.
    st = base_state()
    st["pathmap"] = None
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("no mesh falls through to the shipped path",
          not handled and sent == [] and rows == [])

    # a new click abandons the previous chain first.
    st = base_state()
    answer(st, (300.0, 0.0))                       # arms a chain
    _h, _s, rows = answer(st, (50.0, 50.0))        # verbatim, new click
    check("a new click abandons the live chain with the cause named",
          any(r["kind"] == "router_leg" and r["act"] == "abandon"
              and r["cause"] == "new-click" for r in rows)
          and st.get("router_chain") is None)

    print("== 2: the chain scheduler ==")
    st = base_state()
    send, rec = FakeSend(), FakeRec()
    # hand-built chain: walking origin->(288,0), then two more legs.
    st["router_chain"] = {"queue": [(288.0, 100.0), (500.0, 100.0)],
                          "prev": (0.0, 0.0), "cur": (288.0, 0.0),
                          "granted_at": 1000.0, "carry": 3,
                          "click_plane": 7, "i": 1, "n": 3}
    check("next due is the leg's completion at run speed",
          abs(authsrv.router_next_due(st) - 1001.0) < 1e-9)
    authsrv.router_chain_tick(send, st, 1, rec, now=1000.5)
    check("mid-leg the scheduler grants nothing", send.sent == [])
    authsrv.router_chain_tick(send, st, 1, rec, now=1001.05)
    check("at completion the next leg is granted, bare (no speed row)",
          [op for op, _p, _l in send.sent] == [MOVE_OP]
          and send.sent[0][1][1] == [288.0, 100.0])
    check("the chain advances", st["router_chain"]["i"] == 2
          and st["router_chain"]["cur"] == (288.0, 100.0))
    check("interior leg planes are matched via plane_at",
          send.sent[0][1][2] == send.sent[0][1][3] == 3)
    # the last leg: terminal carries the CLICK's own plane.
    send2 = FakeSend()
    authsrv.router_chain_tick(send2, st, 1, rec, now=1004.0)
    check("the terminal grant fires and the chain clears",
          st.get("router_chain") is None
          and send2.sent[0][1][1] == [500.0, 100.0])
    check("the terminal grant carries the client-named dest plane",
          send2.sent[0][1][2] == 7)
    check("the terminal row is marked",
          any(r["kind"] == "router_leg" and r.get("terminal")
              for r in rec.rows))
    # A LATE poll grants exactly ONE leg: the client has been PARKED at
    # the current waypoint since the leg completed (it cannot walk a leg
    # nobody granted), so cadence restarts from the grant instant --
    # draining the queue in one tick would stack grants the client never
    # walked and cut the corners they encode.
    st2 = base_state()
    send3, rec3 = FakeSend(), FakeRec()
    st2["router_chain"] = {"queue": [(2.0, 0.0), (3.0, 0.0)],
                           "prev": (0.0, 0.0), "cur": (1.0, 0.0),
                           "granted_at": 1000.0, "carry": 3,
                           "click_plane": 3, "i": 1, "n": 3}
    authsrv.router_chain_tick(send3, st2, 1, rec3, now=1010.0)
    check("a late poll grants one leg, not the whole queue",
          len(send3.sent) == 1 and send3.sent[0][1][1] == [2.0, 0.0]
          and st2["router_chain"]["granted_at"] == 1010.0)
    authsrv.router_chain_tick(send3, st2, 1, rec3, now=1010.004)
    check("the next leg follows at its own completion",
          len(send3.sent) == 2 and st2.get("router_chain") is None)

    print("== 3: abandon ==")
    st = base_state()
    st["router_chain"] = {"queue": [(1.0, 1.0)], "prev": (0.0, 0.0),
                          "cur": (0.5, 0.5), "granted_at": 0.0,
                          "carry": 3, "click_plane": 3, "i": 1, "n": 2}
    rec = FakeRec()
    authsrv.router_abandon(st, rec, "0x003D")
    check("abandon pops the chain and logs the cause",
          st.get("router_chain") is None
          and rec.rows[0]["cause"] == "0x003D"
          and rec.rows[0]["left"] == 1)
    check("abandon with no chain is silent",
          (authsrv.router_abandon(st, rec, "0x0047"),
           len(rec.rows))[1] == 1)
    check("next due with no chain is None",
          authsrv.router_next_due(st) is None)

    print("== 4: source locks on the wiring ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    check("the click handler branches to the router exactly once",
          src.count("if ROUTER and router_answer_click(") == 1)
    check("the router branch sits BEFORE the freshness gate",
          src.index("if ROUTER and router_answer_click(")
          < src.index('fresh = (time.time() - state.get("pos_seen"'))
    check("both recv-loop attach points exist, game-gated",
          src.count('if ROUTER and kind == "game":') == 2
          and src.count('if ROUTER and kind == "game" and msgs:') == 1)
    check("the dynamic timeout clamps to [0.05, 1.0]",
          "max(0.05, min(1.0," in src)
    check("both report handlers abandon the chain",
          src.count('router_abandon(state, rec, "0x003D")') == 1
          and src.count('router_abandon(state, rec, "0x0047")') == 1)
    check("the keyboard drop reads the latch directly, not the verdict",
          'kbd_at = state.get("kbd_moving_at")' in src
          and "kage <= GRANT_LOCAL_WINDOW" in src)
    check("the unclipped pass-through door stays closed: no router send "
          "of the raw dest on the no-route path",
          src.count("ROUTER clip-fallback") == 1)
    check("chain grants ride DEFAULT_RUN_SPEED, no second constant",
          src.count("/ DEFAULT_RUN_SPEED") >= 1
          and "ROUTER_SPEED" not in src)
    for pair in ("click_sweep", "arrival_carry", "cancel_answer",
                 "stop_answer", "family_rate_probe", "checksum_probe",
                 "interact_walk", "move_speed_effects"):
        check(f"composition refuses --router with {pair.replace('_', '-')}",
              f"if router and {pair}" in src)
    check("composition refuses --router with pc-spoof",
          "if router and pc_spoof is not None" in src)
    check("the pre-send re-clip exists at the fine step, once",
          src.count("step=A2_LEAD_CLIP_STEP) == (b[0], b[1])") == 1)
    check("the clip-fallback samples at the fine step too",
          src.count("stop = _router_clip(pm, origin[0], origin[1], dx, dy, cur_plane,\n"
                    "                            step=A2_LEAD_CLIP_STEP)") == 1)

    # ---- the a2_matched_field4 gating pattern, and WHY it is asymmetric ----
    # TWO SEPARATE ANALYSES have read the three unconditional router call
    # sites as a leak ("a --d1-lead-only helper running with D1_LEAD False")
    # and proposed gating them. That proposal is a REGRESSION: it reopens the
    # P-17 phasing door on every routed leg, and the two behavioural checks
    # above ("first leg carries the corridor's plane, matched" / "interior leg
    # planes are matched via plane_at") go red -- measured by actually doing
    # it, not assumed. The asymmetry is the point: where field 3 is a plane WE
    # computed, field 4 must match it unconditionally; where field 3 is the
    # client's own plane passed through verbatim, the override is gated so the
    # echo stays byte-identical outside the lead. These locks make a future
    # "fix" fail HERE, next to the reason, instead of in a live run.
    calls = src.count("a2_matched_field4(")
    gated = src.count("if D1_LEAD:\n            ps, _m = a2_matched_field4(")
    check("router still calls a2_matched_field4 on the paths where WE "
          "compute field 3",
          "ps, _matched = a2_matched_field4(pf, chain[\"carry\"])" in src
          and "pf = _router_plane(pm, stop, cur_plane)\n"
              "            ps, _m = a2_matched_field4(pf, cur_plane)" in src
          and "pf = leg_planes[0]\n"
              "    ps, _m = a2_matched_field4(pf, cur_plane)" in src,
          "these three are UNGATED BY DESIGN -- gating them turns the two "
          "corridor-plane checks in this file red. See the function's "
          "docstring and FINDINGS 1z-o.6 before changing them.")
    check("the one-leg VERBATIM echo keeps its override gated",
          gated == 1,
          "the verbatim echo must stay wire-identical to the shipped "
          "clear-line fire, planes included, outside --d1-lead")
    check("the gating census is exactly 3 ungated + 1 gated in the router",
          calls >= 4 and gated == 1,
          f"a2_matched_field4( appears {calls}x, gated {gated}x -- if this "
          f"drifts, re-read the docstring's RULE block rather than "
          f"normalising the call sites")
    # The SUMMARY LINE is the contract a reader acts on, so lock that and not
    # the whole source -- the body deliberately QUOTES the old wording inside
    # its correction block, and a naive substring check fires on the quote.
    doc = (authsrv.a2_matched_field4.__doc__ or "").splitlines()
    check("the helper's contract line no longer says --d1-lead-only",
          bool(doc) and "--d1-lead" not in doc[0],
          f"summary line is {doc[0]!r} -- it read 'for one --d1-lead send' "
          f"until 2026-08-30, which was wrong the day it was written "
          f"(6651c91 created the helper, d3a5936 added four router sites the "
          f"same day) and is what both mis-readings started from")
    check("and the docstring states the rule that replaces it",
          "THIS DOCSTRING SAID" in (authsrv.a2_matched_field4.__doc__ or "")
          and "test_router.py" in (authsrv.a2_matched_field4.__doc__ or ""),
          "the correction block must name this file, so the next reader who "
          "wants to gate the call sites finds the locks that say why not")

    print("== 5: MOVECODE-1z-v -- the router is the DEFAULT, with two conditions ==")
    check("the router is the default click policy, both conditions on",
          authsrv.ROUTER is True and authsrv.ROUTER_LEG_REARM is True
          and authsrv.ROUTER_SYNC_PLANE is True)
    check("--no-router is the revert, --router still parses as a no-op",
          '"--no-router"' in src and '"--router"' in src
          and "ROUTER = not a.no_router" in src
          and "router=not a.no_router," in src)
    check("each condition has its own revert flag",
          '"--router-raw-leg"' in src and '"--router-report-plane"' in src
          and "ROUTER_LEG_REARM = ROUTER and not a.router_raw_leg" in src
          and "ROUTER_SYNC_PLANE = ROUTER and not a.router_report_plane" in src)
    check("the pairwise refusals carry the default-flip hint",
          "pass --no-router to run this arm" in src)

    # ---- (a) the click-leg record follows the ROUTED leg -------------------
    # The 0x003E arm arms the record on the raw click chord BEFORE the router
    # runs (its order of operations); the body walks the routed leg. Every
    # reader of the record -- the press re-pin, the approach snap guard, the
    # swing gate's ETA -- must see the routed leg.
    st = base_state()
    st["client_pos"] = (0.0, 0.0)
    t_click = time.time()
    st["click_moving_at"] = t_click
    raw = authsrv._click_leg_arm(st, (300.0, 0.0), t_click, silent=False)
    check("before the router runs the record is the raw chord",
          raw is not None and raw["dest"] == (300.0, 0.0))
    handled, sent, rows = answer(st, (300.0, 0.0))
    leg = st.get("click_leg")
    check("a routed click re-arms the record to waypoint 1",
          leg is not None and leg["dest"] == (100.0, 500.0)
          and leg["p0"] == (0.0, 0.0))
    check("the record keeps the click's own stamp as its identity",
          leg is not None and leg["t0"] == t_click and "start" in leg)
    check("its ETA is the routed leg's own travel time at the declared speed",
          leg is not None and abs((leg["eta"] - leg["start"])
                                  - math.hypot(100.0, 500.0) / 288.0) < 1e-6)
    mid = authsrv._click_leg_start(st, leg["start"] + 0.5, silent=True)
    check("mid-leg the modelled body lies on the routed leg, not the chord",
          mid is not None and mid[1] > 100.0 and mid[0] <= 100.0 + 1e-6,
          f"model {mid}; the chord's point would be (144, 0)")
    check("the swing gate reads the body as moving on the routed ETA",
          authsrv._player_body_moving(st) is True)
    send2, rec2 = FakeSend(), FakeRec()
    t_leg2 = time.time() + 999.0
    authsrv.router_chain_tick(send2, st, 1, rec2, now=t_leg2)
    leg2 = st.get("click_leg")
    check("a chain leg re-arms the record FROM the waypoint the body reached",
          leg2 is not None and leg2["p0"] == (100.0, 500.0)
          and leg2["dest"] == (200.0, 500.0) and leg2["start"] == t_leg2
          and leg2["t0"] == t_click)
    mid2 = authsrv._click_leg_start(st, t_leg2 + 0.1, silent=True)
    check("and its lerp runs from the leg's OWN start, not the click's",
          mid2 is not None and abs(mid2[0] - 128.8) < 1e-3
          and abs(mid2[1] - 500.0) < 1e-9)
    authsrv.ROUTER_LEG_REARM = False
    try:
        st = base_state()
        st["client_pos"] = (0.0, 0.0)
        st["click_moving_at"] = t_click
        authsrv._click_leg_arm(st, (300.0, 0.0), t_click, silent=False)
        answer(st, (300.0, 0.0))
        check("KNOWN-BAD ARM (--router-raw-leg): the record stays on the chord",
              st["click_leg"]["dest"] == (300.0, 0.0))
    finally:
        authsrv.ROUTER_LEG_REARM = True
    st = base_state(StubPM(route_result=None))
    st["client_pos"] = (0.0, 0.0)
    st["click_moving_at"] = t_click
    authsrv._click_leg_arm(st, (300.0, 0.0), t_click, silent=False)
    handled, sent, rows = answer(st, (300.0, 0.0))
    stop = sent[-1][1][1]
    check("the clip-fallback re-arms the record to its own stop",
          st["click_leg"]["dest"] == (stop[0], stop[1]))
    st = base_state()
    st["client_pos"] = (0.0, 0.0)
    st["click_moving_at"] = t_click
    authsrv._click_leg_arm(st, (50.0, 50.0), t_click, silent=False)
    answer(st, (50.0, 50.0))
    check("a verbatim answer leaves the record alone -- its leg IS the chord",
          st["click_leg"]["dest"] == (50.0, 50.0)
          and "start" not in st["click_leg"])
    st = base_state()
    st["click_leg"] = None
    authsrv._router_rearm_leg(st, (1.0, 1.0), time.time())
    check("a record that was never armed stays unarmed",
          st["click_leg"] is None)

    # ---- the press and the follow end the ROUTE ---------------------------
    st = base_state()
    st["client_pos"] = (0.0, 0.0)
    t_click = time.time() - 0.5
    st["click_moving_at"] = t_click
    authsrv._click_leg_arm(st, (300.0, 0.0), t_click, silent=False)
    handled, sent, rows = answer(st, (300.0, 0.0))
    st["click_leg"]["start"] -= 0.5           # the press lands mid-leg
    st["approach"] = None
    send3, rec3 = FakeSend(), FakeRec()
    authsrv._press_supersedes(send3, st, 1, 77, rec=rec3)
    pins = [p for op, p, _l in send3.sent
            if op == authsrv.GAME_SMSG_AGENT_UPDATE_POSITION]
    check("a press mid-chain abandons the chain, cause named",
          st.get("router_chain") is None
          and any(r["kind"] == "router_leg" and r["act"] == "abandon"
                  and r["cause"] == "press" for r in rec3.rows))
    check("and PRESS ENDS THE WALK re-pins the body ON THE ROUTED LEG",
          len(pins) == 1 and pins[0][1][1] > 100.0
          and pins[0][1][0] <= 100.0 + 1e-6,
          f"re-pin {pins}; on the raw chord it would be (144, 0)")
    st = base_state()
    st["client_pos"] = (0.0, 0.0)
    st["sync_from"] = (0.0, 0.0)
    st["click_moving_at"] = time.time()
    authsrv._click_leg_arm(st, (300.0, 0.0), st["click_moving_at"],
                           silent=False)
    answer(st, (300.0, 0.0))
    send4, rec4 = FakeSend(), FakeRec()
    authsrv._approach_send(send4, st, 1, 77,
                           {"pos": (1000.0, 0.0), "name": "hatcher"},
                           time.time(), rec=rec4)
    check("a follow abandons the chain too, cause named",
          st.get("router_chain") is None
          and any(r["kind"] == "router_leg" and r["act"] == "abandon"
                  and r["cause"] == "approach" for r in rec4.rows))

    # ---- (b) the verbatim answer's field 4 --------------------------------
    def planes_fn(x, y, prefer):
        offered = {5} if x < 0.0 else {3}
        if prefer in offered:
            return prefer
        return next(iter(offered))
    pm = StubPM(plane_fn=planes_fn)
    st = base_state(pm)
    st["sync_from"] = (-50.0, 0.0)
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("verbatim field 4 is the mesh's plane under the SYNC COPY when the "
          "report's plane is not offered there",
          sent[-1][1][2] == 3 and sent[-1][1][3] == 5)
    row = next(r for r in rows if r["kind"] == "router_route")
    check("the row carries both words",
          row.get("plane4") == 5 and row.get("plane4_report") == 3)
    st = base_state(pm)
    st["sync_from"] = (10.0, 0.0)
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("where the mesh offers the report's plane under the copy, the wire "
          "is unchanged", sent[-1][1][3] == 3)
    st = base_state(StubPM(plane_fn=lambda x, y, prefer: None))
    st["sync_from"] = (-50.0, 0.0)
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("where the mesh cannot say, the report's plane is carried "
          "(refuse to guess)", sent[-1][1][3] == 3)
    st = base_state(pm)
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("an unseeded sync model carries the report's plane",
          sent[-1][1][3] == 3)
    st = base_state(pm)
    st["sync_from"], st["sync_to"] = (-400.0, 0.0), (400.0, 0.0)
    st["sync_at"] = time.time() - 1.0
    handled, sent, rows = answer(st, (50.0, 50.0))
    check("the sync copy is modelled MID-LEG (1 s into an 800 u leg it still "
          "stands on plane 5's ground)", sent[-1][1][3] == 5)
    authsrv.ROUTER_SYNC_PLANE = False
    try:
        st = base_state(pm)
        st["sync_from"] = (-50.0, 0.0)
        handled, sent, rows = answer(st, (50.0, 50.0))
        check("KNOWN-BAD ARM (--router-report-plane): field 4 is the frozen "
              "report plane", sent[-1][1][3] == 3)
    finally:
        authsrv.ROUTER_SYNC_PLANE = True

    # ---- source locks for 1z-v ---------------------------------------------
    check("chain grants, the routed first leg and the fallback all re-arm "
          "the record",
          src.count('_router_rearm_leg(state, nxt, now, p0=chain["cur"])') == 1
          and src.count("_router_rearm_leg(state, first_wp, now)") == 1
          and src.count("_router_rearm_leg(state, (float(stop[0]), "
                        "float(stop[1])), now)") == 1)
    check("the press and the follow abandon the chain, once each",
          src.count('router_abandon(state, rec, "press", now)') == 1
          and src.count('router_abandon(state, rec, "approach", now)') == 1)
    check("the verbatim field 4 goes through the sync-plane helper BEFORE "
          "the gated match",
          src.index("ps = _router_sync_plane(state, pm, plane_second, now)")
          < src.index("if D1_LEAD:\n            ps, _m = a2_matched_field4("))
    # REFACTOR-A11 moved `_click_leg_start` to `leadgeom.py`, so this pin
    # reads THAT file now. Same expression and same reason -- the model must
    # measure from the leg's own grant instant (a chain leg's re-arm) and not
    # from the click's stamp, which stays the leg's identity -- one file over.
    leadgeom_src = open(os.path.join(HERE, "leadgeom.py"),
                        encoding="utf-8").read()
    check("the leg model lerps from the leg's own start",
          'leg.get("start", leg["t0"])' in leadgeom_src)

    print("== 6: MOVECODE-1z-w -- the origin's plane word, and a cast ends the route ==")
    check("the origin word ships, reverted by (b)'s own flag",
          authsrv.ROUTER_ORIGIN_PLANE is True
          and "ROUTER_ORIGIN_PLANE = ROUTER and not a.router_report_plane"
          in src)

    def stacked_fn(x, y, prefer):
        offered = {5} if x < 0.0 else ({3, 5} if x < 50.0 else {3})
        if prefer in offered:
            return prefer
        return next(iter(offered)) if len(offered) == 1 else None
    # The body stands on single-plane ground (5) while the frozen report
    # still says 3: route() must be told the ground's own plane.
    pm = StubPM(plane_fn=stacked_fn)
    st = base_state(pm, pos=(-50.0, 0.0))
    handled, sent, rows = answer(st, (-20.0, 40.0), dest_plane=3, cur_plane=3)
    check("route() receives the ORIGIN's mesh plane as its start preference",
          pm.last_planes == (5, 3), f"last_planes {pm.last_planes}")
    row = next(r for r in rows if r["kind"] == "router_route")
    check("every row carries plane_origin beside plane_report",
          row.get("plane_origin") == 5 and row.get("plane_report") == 3)
    # THE ONE WIRE EFFECT: a clip-fallback whose stop lands on STACKED
    # ground {3, 5}, reached from plane-5 ground, takes the origin's deck.
    st = base_state(StubPM(route_result=None, plane_fn=stacked_fn),
                    pos=(-50.0, 0.0))
    handled, sent, rows = answer(st, (40.0, 0.0), dest_plane=3, cur_plane=3)
    check("a clip-fallback onto stacked ground carries the origin's deck, "
          "matched",
          sent[-1][0] == MOVE_OP and sent[-1][1][2] == 5
          and sent[-1][1][3] == 5, f"sent {sent[-1]}")
    # Where the mesh offers the report's plane at the origin, the word IS
    # the report's -- the wire is unchanged on ordinary ground.
    st = base_state(pm, pos=(10.0, 0.0))
    handled, sent, rows = answer(st, (30.0, 40.0), dest_plane=3, cur_plane=3)
    check("where the mesh offers the report's plane at the origin the word "
          "is the report's", pm.last_planes == (3, 3))
    pm_none = StubPM(plane_fn=lambda x, y, prefer: None)
    st = base_state(pm_none, pos=(0.0, 0.0))
    handled, sent, rows = answer(st, (50.0, 50.0), dest_plane=3, cur_plane=3)
    check("where the mesh cannot say, the report's plane is carried",
          pm_none.last_planes == (3, 3))
    authsrv.ROUTER_ORIGIN_PLANE = False
    try:
        pm_bad = StubPM(route_result=None, plane_fn=stacked_fn)
        st = base_state(pm_bad, pos=(-50.0, 0.0))
        handled, sent, rows = answer(st, (40.0, 0.0), dest_plane=3,
                                     cur_plane=3)
        check("KNOWN-BAD ARM (--router-report-plane): the fallback carries "
              "the frozen report plane and route() is told it too",
              sent[-1][1][2] == 3 and pm_bad.last_planes == (3, 3))
    finally:
        authsrv.ROUTER_ORIGIN_PLANE = True

    # ---- a cast that begins ends the route ----------------------------------
    import contextlib
    import io
    st = base_state()
    st["client_pos"] = (0.0, 0.0)
    st["click_moving_at"] = time.time()
    authsrv._click_leg_arm(st, (300.0, 0.0), st["click_moving_at"],
                           silent=False)
    answer(st, (300.0, 0.0))                       # a live chain
    st["agents"] = {}
    send6, rec6 = FakeSend(), FakeRec()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_skill_press([0, 42, 7, 0], send6, st, 1,
                                   authsrv.GAME_CMSG_USE_SKILL, rec=rec6)
    check("a cast that begins abandons the chain, cause named",
          st.get("router_chain") is None
          and any(r["kind"] == "router_leg" and r["act"] == "abandon"
                  and r["cause"] == "cast" for r in rec6.rows),
          f"chain {st.get('router_chain')}; rows {rec6.rows[:2]}")
    check("the cast abandons once, at the begin instant, BEFORE the "
          "cast-stop block",
          src.count('router_abandon(state, rec, "cast", time.time())') == 1
          and src.index('router_abandon(state, rec, "cast", time.time())')
          < src.index("if CAST_STOP and not is_attack:"))
    check("the skill-press arm hands the recorder to handle_skill_press",
          "handle_skill_press(values, send, state, conn_id, opcode,\n"
          + " " * 43 + "rec=rec)" in src)
    check("the origin word is derived once, after the snap, before route()",
          src.count("cur_plane = _router_plane(pm, origin, report_plane)") == 1
          and src.index("cur_plane = _router_plane(pm, origin, report_plane)")
          < src.index("_routed = pm.route(origin[0], origin[1], dx, dy,"))

    print("== 6: the seam-aware rays (MOVECODE-1z-bb) ==")
    # RUN-1zBA's specimen: a click over the bridge railing landed off-mesh,
    # the fallback clipped the straight line PLANE-BLIND off the deck at its
    # tenth unit and granted 2 km; the drawn body parked at the edge for 7 s
    # and was teleported. Both of the router's rays -- the pre-send leg gate
    # and the clip fallback -- now come through _router_clip, which walks the
    # body's plane and stops where it ends without a portal. On the stub the
    # seam is a vertical line at x = seam_stop, short of the wall at 100.
    check("ROUTER_SEAM_CLIP is the default", authsrv.ROUTER_SEAM_CLIP is True)
    body = src[src.index("def router_answer_click("):]
    body = body[:body.index("\ndef ", 1)]
    check("both rays come through _router_clip and nowhere else",
          src.count("_router_clip(") == 3
          and body.count("_router_clip(") == 2 and "pm.clip(" not in body,
          f"{body.count('_router_clip(')} helper calls, "
          f"{body.count('pm.clip(')} bare pm.clip in router_answer_click")
    # the fallback: seam-aware stops at the seam, plane-blind at the wall
    st = base_state(StubPM(route_result=None, seam_stop=50.0))
    handled, sent, rows = answer(st, (300.0, 0.0))
    stop = sent[-1][1][1]
    check("the clip fallback stops at the BLIND SEAM, not the wall",
          handled and [op for op, _p, _l in sent] == [SPEED_OP, MOVE_OP]
          and abs(stop[0] - 50.0) < 1e-6
          and any(r.get("verdict") == "clip-fallback" for r in rows),
          f"stop {stop}")
    authsrv.ROUTER_SEAM_CLIP = False
    try:
        st = base_state(StubPM(route_result=None, seam_stop=50.0))
        handled, sent, rows = answer(st, (300.0, 0.0))
        stop = sent[-1][1][1]
        check("KNOWN-BAD ARM (--router-blind-clip): the fallback walks through "
              "the seam to the wall -- RUN-1zBA's grant",
              50.0 < stop[0] <= 100.0 + 1e-6, f"stop {stop}")
    finally:
        authsrv.ROUTER_SEAM_CLIP = True
    # the leg gate: a route whose leg crosses the seam is no route
    st = base_state(StubPM(route_result=[(0.0, 0.0), (80.0, 0.0)],
                           route_planes=[3, 3], seam_stop=50.0))
    handled, sent, rows = answer(st, (80.0, 0.0))
    stop = sent[-1][1][1]
    check("a routed leg that crosses a blind seam is demoted to the fallback, "
          "which itself stops at the seam",
          handled and abs(stop[0] - 50.0) < 1e-6
          and any(r.get("verdict") == "clip-fallback" for r in rows),
          f"stop {stop}, verdicts {[r.get('verdict') for r in rows]}")
    authsrv.ROUTER_SEAM_CLIP = False
    try:
        st = base_state(StubPM(route_result=[(0.0, 0.0), (80.0, 0.0)],
                               route_planes=[3, 3], seam_stop=50.0))
        handled, sent, rows = answer(st, (80.0, 0.0))
        check("KNOWN-BAD ARM: the same leg is granted verbatim across the seam",
              handled and sent[-1][1][1] == [80.0, 0.0]
              and any(r.get("verdict") == "verbatim" for r in rows))
    finally:
        authsrv.ROUTER_SEAM_CLIP = True
    check("one flag, both rays: the revert arm exists and sets pathmap's own "
          "switch, so route()'s pull and gate cannot disagree with the fallback",
          '"--router-blind-clip"' in src
          and "ROUTER_SEAM_CLIP = ROUTER and not a.router_blind_clip" in src
          and "_pathmap_mod.SEAM_AWARE_ROUTE = ROUTER_SEAM_CLIP" in src)
    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
