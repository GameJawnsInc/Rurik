"""test_agtrack_mirror.py -- the AgTrack mirror's transcription, rule by rule.

Every check here pins one decoded behaviour from the record (each cited in
agtrack_mirror.py at the code it tests): the bake equations, the dead-reckoner
and its missing clamp, the arrival teleport, the recorder's push rule and both
timers, the walk's oldest-match-wins + truncation, the exact gate-1 threshold
(89600.0f -- a true 300.0 u snaps), the fences, and the reset semantics (Clear
zeroes flag+head only; re-arm is edge-triggered and keeps the seed).

Synthetic throughout -- no vault, no client, bare machine.  The corpus replay
(the arc's step 2) is agtrack_replay.py's job, not this file's.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                    # noqa: E402
import agtrack_mirror as am      # noqa: E402

# Floor from the 2026-08-30 green run: 64 checks, all unconditional.
LEDGER = checks.Ledger("agtrack mirror transcription", floor=68)
check = checks.adopt_named(LEDGER)


class FailPathMesh(object):
    """A mesh whose walkable-path conjunct always FAILS -- distinguishes the
    degenerate arm (which must never consult it) from the non-degenerate."""
    calls = 0

    def start_walkable(self, x, y):
        return True

    def path_len_ok(self, *a, **k):
        FailPathMesh.calls += 1
        return False


class OffMeshStart(object):
    """Gate 2's failure: the sync position is off the navmesh."""

    def start_walkable(self, x, y):
        return False

    def path_len_ok(self, *a, **k):
        return True


def main():
    # ---- 1. the bake --------------------------------------------------
    s = am.SyncAgent()
    s.x78, s.y78, s.plane = 0.0, 0.0, 0
    s.bake_grant(2880.0, 0.0, 0, 0, now_ms=10_000)
    check("bake: velocity = unit(d) * 288 (x)", abs(s.vx - 288.0) < 1e-9)
    check("bake: velocity y zero on the axis", s.vy == 0.0)
    check("bake: arrival = now + trunc(dist*1000/S)",
          s.t_arrive == 10_000 + 10_000)
    check("bake: epoch stamped now", s.t_epoch == 10_000)
    p = s.position(11_000)
    check("dead-reckon: +288 u after 1 s", abs(p[0] - 288.0) < 1e-9)
    # the resolver's arrived arm: dest verbatim at/after the tick
    p = s.position(20_000)
    check("resolver: arrived -> destination verbatim", p == (2880.0, 0.0))
    # NO clamp in the dead-reckoner itself: disarm the tick and overshoot
    s.t_arrive = 0
    p = s.position(30_000)
    check("dead-reckoner has no destination clamp (overshoots unbounded)",
          abs(p[0] - 288.0 * 20.0) < 1e-6)

    # ---- 2. the zero-distance short-circuit ---------------------------
    s = am.SyncAgent()
    s.x78, s.y78 = 100.0, 100.0
    s.bake_grant(100.5, 100.0, 0, 0, now_ms=5_000)
    check("short-circuit: +0x78 written to D directly", s.x78 == 100.5)
    check("short-circuit: velocity zeroed", s.vx == 0.0 and s.vy == 0.0)
    check("short-circuit: arrival armed at now+1", s.t_arrive == 5_001)

    # ---- 3. the settle: a re-grant measures d from the MOVED +0x78 ----
    s = am.SyncAgent()
    s.x78, s.y78, s.plane = 0.0, 0.0, 0
    s.bake_grant(2880.0, 0.0, 0, 0, now_ms=0)
    s.bake_grant(0.0, 1000.0, 0, 0, now_ms=1_000)   # mid-leg, at (288, 0)
    check("settle: second bake starts from the dead-reckoned +0x78",
          abs(s.x78 - 288.0) < 1e-9)
    check("settle: velocity re-aimed from there, not from origin",
          s.vx < 0.0 and s.vy > 0.0)

    # ---- 4. arrival consumption (the teleport primitive) --------------
    s = am.SyncAgent()
    s.x78, s.y78, s.plane = 0.0, 0.0, 0
    s.bake_grant(288.0, 0.0, 0, 0, now_ms=0)
    check("arrival not due early", s.consume_arrival(500) is False)
    check("arrival consumed at the tick", s.consume_arrival(1_000) is True)
    check("teleport: +0x78 <- destination", s.x78 == 288.0)
    check("teleport: velocity zeroed", s.vx == 0.0)
    check("teleport: target invalidated (+inf sentinel)", s.dest is None)
    check("teleport: +0x48 cleared (AgAgent.cpp 2090 invariant)",
          s.t_arrive == 0)

    # ---- 5. the recorder's push rule ----------------------------------
    m = am.AgTrackMirror()
    m.re_arm()
    ok = m.on_player_command(0, (0.0, 0.0), 0, ("kbd", 1, 0))
    check("push: first command pushes (empty chain)", ok and m.chain_len == 1)
    ok = m.on_player_command(1_000, (100.0, 0.0), 0, ("kbd", 1, 0))
    # position moved but the CANDIDATE SEED (parked arm: position) changed
    check("push: candidate-seed change pushes", ok and m.chain_len == 2)
    seed_before = m.seed
    ok = m.on_player_command(1_500, (100.0, 0.0), 0, ("kbd", 1, 0))
    check("push: identical command inside 2.5 s pushes NOTHING",
          not ok and m.chain_len == 2)
    check("push: no-push arm leaves the seed alone", m.seed == seed_before)
    ok = m.on_player_command(4_000, (100.0, 0.0), 0, ("kbd", 1, 0))
    check("push: forced re-sample at >= 2500 ms", ok and m.chain_len == 3)
    ok = m.on_player_command(4_100, (100.0, 0.0), 0, ("kbd", 0, 1))
    check("push: sig (velocity/facing block) change pushes",
          ok and m.chain_len == 4)
    # click arm: seed becomes the DESTINATION with the arrival tick
    m.on_player_command(4_200, (100.0, 0.0), 0, ("click",),
                        dest=(500.0, 0.0, 0), arrive_t=6_000)
    check("push: moving arm seeds the DESTINATION",
          m.seed == (500.0, 0.0, 0))
    check("push: moving arm stamps state.time = arrival tick",
          m.seed_t == 6_000)

    # ---- 6. the sweep --------------------------------------------------
    m = am.AgTrackMirror()
    m.re_arm()
    m.sync.x78, m.sync.y78, m.sync.plane = 0.0, 0.0, 0
    m.on_player_command(0, (0.0, 0.0), 0, ("kbd", 1, 0))
    check("sweep: fresh head -> no push", m.sweep(2_000) is False)
    check("sweep: stale head (>= 3333 ms) -> push", m.sweep(3_400) is True)
    check("sweep: samples the SYNC copy", m.head.sig[0] == "sync")

    # ---- 7. the walk ---------------------------------------------------
    # Chain (oldest..newest): nodes at x=0, x=300, x=600; seed at x=900.
    # q at (450, 50): within 100 u of BOTH the (600->900) segment (seg 0,
    # no -- that spans x 600..900, q is 150 away) -- build it explicitly:
    m = am.AgTrackMirror()
    m.re_arm()
    m.on_player_command(0, (0.0, 0.0), 0, ("a",))
    m.on_player_command(3_000, (300.0, 0.0), 0, ("b",))
    m.on_player_command(6_000, (600.0, 0.0), 0, ("c",))
    m.seed = (900.0, 0.0, 0)          # segment 0: (600,0)->(900,0)
    m.sync.x78, m.sync.y78, m.sync.plane = 450.0, 50.0, 0
    m.sync.t_epoch = 9_000
    v = m.evaluate(9_000, None, event="test")
    check("walk: q 50 u off a mid-chain segment MATCHES", v.code == am.MATCH)
    # q = (450, 50) is 50 u from segment (300->600) only: the (600->900)
    # seg-0 and the (0->300) segment both clamp to an end 158 u away.  So
    # the oldest MATCHING node is the one at x=300, and truncation drops
    # exactly the node at x=0 -- len 3 -> 2, tail = (600) -> (300).
    check("walk: oldest match wins, truncation drops exactly its tail",
          m.chain_len == 2 and m.head.x == 600.0
          and m.head.nxt.x == 300.0 and m.head.nxt.nxt is None)
    # Now put q near ONLY the newest segment: truncation must drop the tail.
    m2 = am.AgTrackMirror()
    m2.re_arm()
    m2.on_player_command(0, (0.0, 0.0), 0, ("a",))
    m2.on_player_command(3_000, (5_000.0, 0.0), 0, ("b",))
    m2.on_player_command(6_000, (5_000.0, 3_000.0), 0, ("c",))
    m2.seed = (5_000.0, 3_300.0, 0)
    m2.sync.x78, m2.sync.y78, m2.sync.plane = 5_050.0, 3_200.0, 0
    m2.sync.t_epoch = 9_000
    v = m2.evaluate(9_000, None)
    check("walk: match on the newest segment", v.code == am.MATCH)
    check("walk: truncation drops the older tail", m2.chain_len == 1)
    check("walk: the kept node is the matched one",
          m2.head.x == 5_000.0 and m2.head.y == 3_000.0)
    # seed None -> segment 0 skipped (guard tests PREV only)
    m3 = am.AgTrackMirror()
    m3.re_arm()
    m3.on_player_command(0, (0.0, 0.0), 0, ("a",))
    m3.seed = None
    m3.sync.x78, m3.sync.y78, m3.sync.plane = 0.0, 10.0, 0
    m3.sync.t_epoch = 100
    v = m3.evaluate(100, (0.0, 10.0))
    check("walk: unseeded segment 0 is skipped (falls to the gates)",
          v.code == am.NOMATCH_PASS)

    # ---- 8. seg_match geometry ----------------------------------------
    mesh = FailPathMesh()
    FailPathMesh.calls = 0
    hit = am.seg_match(0.0, 50.0, 0, 10.0, 10.0, 7, 10.0, 10.0, 7, mesh)
    check("degenerate arm: straight-line only, mesh never consulted",
          hit and FailPathMesh.calls == 0)
    hit = am.seg_match(0.0, 100.0, 0, 10.0, 0.0, 0, -10.0, 0.0, 0, mesh)
    check("degenerate-adjacent: exactly r on a segment FAILS (strict >)",
          not hit)
    hit = am.seg_match(0.0, 50.0, 0, -100.0, 0.0, 0, 100.0, 0.0, 0, mesh)
    check("non-degenerate arm consults the walkable conjunct (fails here)",
          not hit and FailPathMesh.calls >= 1)
    nomesh = am.NoMesh()
    hit = am.seg_match(0.0, 50.0, 0, -100.0, 0.0, 0, 100.0, 0.0, 0, nomesh)
    check("NoMesh: same segment passes straight-line-only", hit)
    # the t >= 0.99 arm hands b VERBATIM to the path test (b's plane)
    class PlaneSpy(object):
        seen = None
        def start_walkable(self, x, y):
            return True
        def path_len_ok(self, qx, qy, qp, cx, cy, cp, lim):
            PlaneSpy.seen = (cx, cy, cp)
            return True
    spy = PlaneSpy()
    am.seg_match(199.0, 10.0, 0, 0.0, 0.0, 3, 200.0, 0.0, 9, spy)
    check("t>=0.99 arm: c = b verbatim, b's plane",
          PlaneSpy.seen == (200.0, 0.0, 9))
    am.seg_match(100.0, 10.0, 0, 0.0, 0.0, 3, 200.0, 0.0, 9, spy)
    check("lerp arm: c carries THE NODE's plane (a.plane)",
          PlaneSpy.seen[2] == 3)

    # ---- 9. gate 1: the exact 89600.0f threshold ----------------------
    def gate1_only(sep_sq):
        mm = am.AgTrackMirror()
        mm.re_arm()
        mm.sync.x78, mm.sync.y78, mm.sync.plane = 0.0, 0.0, 0
        mm.sync.t_epoch = 0
        # empty walk (no seed, no chain beyond...) -- force: head None
        mm.head = None
        mm.seed = None
        return mm.evaluate(0, (sep_sq ** 0.5, 0.0))
    v = gate1_only(89_599.99)
    check("gate 1: distSq just under 89600 passes", v.code == am.NOMATCH_PASS)
    v = gate1_only(89_600.0)
    check("gate 1: distSq exactly 89600.0 SNAPS (true 300.0 u snaps)",
          v.code == am.SNAP and v.gate1 is False)
    v = gate1_only(90_000.0)
    check("gate 1: a true 300.0 u separation snaps", v.code == am.SNAP)

    # ---- 10. gate 2: off-mesh start -----------------------------------
    mm = am.AgTrackMirror(mesh=OffMeshStart())
    mm.re_arm()
    mm.sync.x78, mm.sync.y78, mm.sync.plane = 0.0, 0.0, 0
    v = mm.evaluate(0, (10.0, 0.0))
    check("gate 2: unwalkable sync position snaps",
          v.code == am.SNAP and v.gate2 is False)
    check("NoMesh never runs gate 2 (labelled degradation)",
          gate1_only(100.0).gate2 is None)

    # ---- 10b. gate 2 tolerates the mesh's edge rounding (MOVECODE-1z-bf) --
    # Every gate2-offmesh re-pin in the corpus (17 fired, 19 predicted) was a
    # false veto on a point <= 0.5 u outside our trapezoid edges where the
    # client's own body stood and its own snap test passed. MeshAdapter now
    # asks on_mesh(a, GATE2_SEAM_TOL); 0.0 is the revert arm.
    class SliverMesh(object):
        """walkable() says off, on_mesh() says on within the tolerance."""

        def walkable(self, x, y):
            return False

        def on_mesh(self, x, y, tol=1.0):
            return tol > 0.0

    class ExactOnlyMesh(object):
        """An older stub with no on_mesh(): the adapter must fall back."""

        def walkable(self, x, y):
            return True

    saved_tol = am.GATE2_SEAM_TOL
    try:
        am.GATE2_SEAM_TOL = 1.0
        check("gate 2 under the tolerance: a sub-unit sliver PASSES",
              am.MeshAdapter(SliverMesh()).start_walkable(0.0, 0.0) is True)
        am.GATE2_SEAM_TOL = 0.0
        check("gate 2 exact (the revert arm, --agtrack-gate2-exact): the same "
              "sliver FAILS -- the known-bad arm still reproduces the false veto",
              am.MeshAdapter(SliverMesh()).start_walkable(0.0, 0.0) is False)
        am.GATE2_SEAM_TOL = 1.0
        check("a mesh without on_mesh() falls back to walkable()",
              am.MeshAdapter(ExactOnlyMesh()).start_walkable(0.0, 0.0) is True)
    finally:
        am.GATE2_SEAM_TOL = saved_tol
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
    import pathmap as _pathmap
    check("GATE2_SEAM_TOL is pathmap.SEAM_TOL, ON by default -- one edge "
          "constant, not a new guess",
          am.GATE2_SEAM_TOL == _pathmap.SEAM_TOL and am.GATE2_SEAM_TOL > 0.0)

    # ---- 11. fences and resets ----------------------------------------
    m = am.AgTrackMirror()
    check("spawn state: fence closed", not m.client_controlled)
    m.sync.x78, m.sync.y78, m.sync.plane = 0.0, 0.0, 0
    v = m.on_grant(1_000.0, 0.0, 0, 0, now_ms=0)
    check("fence closed: a grant RECORDS instead of testing",
          v.code == am.NOT_TESTED and v.recorded and m.chain_len == 1)
    check("fence-closed append rewrote the seed (server-written point)",
          m.seed is not None and m.seed[0] == 1_000.0)
    seed_kept = m.seed
    m.re_arm()
    check("re-arm: 0->1 edge nulls the HEAD", m.head is None)
    check("re-arm: the seed SURVIVES", m.seed == seed_kept)
    m.on_player_command(100, (0.0, 0.0), 0, ("kbd", 1, 0))
    head_kept = m.head
    m.re_arm()
    check("re-arm: no-op on an already-armed record", m.head is head_kept)

    # ---- 12. 0x002C ----------------------------------------------------
    m = am.AgTrackMirror()
    m.re_arm()
    m.sync.x78, m.sync.y78, m.sync.plane = 0.0, 0.0, 0
    m.on_player_command(0, (0.0, 0.0), 0, ("kbd", 1, 0))
    m.on_player_command(3_000, (10.0, 0.0), 0, ("kbd", 2, 0))
    v = m.on_update_position(500.0, 500.0, 0, now_ms=4_000)
    check("0x002C: Clear wipes the chain, then one fresh append",
          m.chain_len == 1 and v.recorded)
    check("0x002C: fence closed until the next player command",
          not m.client_controlled)
    check("0x002C: sync copy hard-set", m.sync.x78 == 500.0)
    check("0x002C: fresh node samples the NEW position",
          m.head.x == 500.0 and m.head.y == 500.0)

    # ---- 13. a MATCH short-circuits the gates -------------------------
    m = am.AgTrackMirror(mesh=OffMeshStart())   # gate 2 would snap
    m.re_arm()
    m.on_player_command(0, (0.0, 0.0), 0, ("a",))
    m.seed = (300.0, 0.0, 0)
    m.sync.x78, m.sync.y78, m.sync.plane = 150.0, 10.0, 0
    m.sync.t_epoch = 1_000
    v = m.evaluate(1_000, (99_999.0, 0.0))      # separation enormous
    check("MATCH jumps clean over all three gates", v.code == am.MATCH)

    # ---- 14. the MISS consequence chain -------------------------------
    m = am.AgTrackMirror()
    m.re_arm()
    m.on_player_command(0, (0.0, 0.0), 0, ("a",))
    m.seed = (10.0, 0.0, 0)
    m.sync.x78, m.sync.y78, m.sync.plane = 5_000.0, 0.0, 0
    m.sync.t_epoch = 1_000
    v = m.evaluate(1_000, (0.0, 0.0))
    check("MISS + gate fail = SNAP", v.code == am.SNAP)
    check("snap Clears (fence closed)", not m.client_controlled)
    check("snap appends ONE fresh node after the Clear", m.chain_len == 1)

    # ---- 15. 0x002B leaves the current leg alone ----------------------
    m = am.AgTrackMirror()
    m.sync.x78, m.sync.y78, m.sync.plane = 0.0, 0.0, 0
    m.on_grant(2_880.0, 0.0, 0, 0, now_ms=0)
    vx_before = m.sync.vx
    m.on_speed(0.5, now_ms=1_000)
    check("0x002B: current leg's baked velocity unchanged",
          m.sync.vx == vx_before)
    m.on_grant(0.0, 2_880.0, 0, 0, now_ms=2_000)
    speed = (m.sync.vx ** 2 + m.sync.vy ** 2) ** 0.5
    check("0x002B: the NEXT bake's speed magnitude is 288 * 0.5",
          abs(speed - 144.0) < 1e-6)

    # ---- 16. reader 2's prune (parameterized -- cadence unresolved) ----
    m = am.AgTrackMirror(prune_ms=3_000)
    m.re_arm()
    m.sync.x78, m.sync.y78, m.sync.plane = 0.0, 0.0, 0
    m.on_player_command(0, (0.0, 0.0), 0, ("a",))
    m.on_player_command(2_600, (10.0, 0.0), 0, ("b",))
    m.on_player_command(5_200, (20.0, 0.0), 0, ("c",))
    m.on_player_command(7_800, (30.0, 0.0), 0, ("d",))
    m.tick(8_000)
    # cutoff 5000: nodes at 7800, 5200 are young; 2600 is the kept-older
    # far end; 0 is dropped.
    check("render_prune: drops beyond one node past the horizon",
          m.chain_len == 3 and m.head.t == 7_800
          and m.head.nxt.nxt.t == 2_600 and m.head.nxt.nxt.nxt is None)
    m2 = am.AgTrackMirror(prune_ms=None)
    m2.re_arm()
    m2.on_player_command(0, (0.0, 0.0), 0, ("a",))
    m2.on_player_command(2_600, (10.0, 0.0), 0, ("b",))
    m2.tick(60_000)
    check("render_prune: None = the reader never runs (long-chain model)",
          m2.chain_len >= 2)

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
