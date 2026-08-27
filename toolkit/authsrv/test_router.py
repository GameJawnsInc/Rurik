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
# streak counting, the true-hole refusal).
LEDGER = checks.Ledger("router wiring", floor=68)
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

    def __call__(self, opcode, payload, label=""):
        self.sent.append((opcode, payload, label))


class StubPM:
    """A mesh with one wall: x in (100, 200) is unwalkable. Routes that
    cross it detour through (150.0, 500.0); everything else is a straight
    line. plane 3 everywhere."""

    def __init__(self, route_result="auto", route_planes=None):
        self.route_result = route_result
        self.route_planes = route_planes
        self.last_planes = None

    def walkable(self, x, y):
        return not (100.0 < x < 200.0) or y > 400.0

    def containing(self, x, y):
        return [1] if self.walkable(x, y) else []

    def plane_at(self, x, y, prefer=None):
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
          src.count("stop = pm.clip(origin[0], origin[1], dx, dy,\n"
                    "                       step=A2_LEAD_CLIP_STEP)") == 1)
    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
