"""agtrack_mirror.py -- a server-side mirror of the client's AgTrack history
chain and its reprieve test (MOVECODE-1z-q step 1).

WHAT THIS IS. The client decides whether to snap (whole-roster reseed -- the
warp) by asking one question when a movement message lands: is the SYNC copy's
own dead-reckoned position within 100 u of a segment of its recent HISTORY
chain?  A match is a reprieve -- no snap, no gates.  A miss runs three fallback
gates, and any gate failing snaps every async agent (studies/movement/
FINDINGS.md:3103-3141, the dispatcher + fallback pseudocode; studies/movecode/
FINDINGS.md section 1z-q, the chain decoded whole).  Everything the chain's
contents depend on is either server-known (our own grants) or server-observed
(the client's c2s command stream), so this module maintains the same structure
the client maintains and answers the same question BEFORE a grant is emitted --
or, in replay (agtrack_replay.py, step 2), AFTER the fact against a capture.

EVERY RULE HERE IS A TRANSCRIPTION, NOT A DESIGN.  Each carries the citation it
was transcribed from.  Where the record is silent, the choice is labelled
MODEL-CHOICE with the reasoning; where the record marks something unresolved,
that mark is carried here rather than papered over.  The three known
un-mirrorable pieces, stated up front:

  * gate 3 (0x005FEF70, "can I take a first step") tests obstruction by OTHER
    AGENTS' personal space -- server-side we do not model other agents' async
    positions, so gate 3 always passes here.  A miss that real gate 3 converts
    to a snap is a false-negative this mirror CANNOT see.  A MATCH is
    unaffected: a match jumps clean over all three gates
    (0x0060574C jmp 0x60582b, studies/movement/FINDINGS.md:3090).
  * the client's world clocks run ~1.36% slow vs ours; over the 2.5 s node
    cadence at 288 u/s that is ~10 u against a 100 u band -- an order of
    magnitude inside tolerance (studies/movecode/FINDINGS.md 1z-q.5,
    RECONSTRUCTION -- and the replay is how it gets checked).
  * `facing == 9` with an armed arrival tick is a no-snap early-out whose
    meaning is NOT FOUND (studies/movement/FINDINGS.md:2701,2934).  Not
    modelled; if it fires in the wild the mirror over-predicts a test that the
    client skipped.

Pure stdlib, no imports outside this file's own directory tree.  The navmesh
conjunct is injected (a PathingMap-shaped adapter or None); with None the
walkable half of the dual test and gate 2 degrade to labelled approximations
(see MeshAdapter below) rather than silently passing.

Time is INTEGER MILLISECONDS throughout, like the client's world clock.
"""

import math

# ---------------------------------------------------------------------------
# Constants, each read from the image (build 38797) and cited.
# ---------------------------------------------------------------------------

R_MATCH = 100.0            # f32 @0x00946560 -- the reprieve radius
                           # (studies/movement/FINDINGS.md:2694)
R_MATCH_SQ = R_MATCH * R_MATCH   # conjunct 1 compares SQUARED, STRICT (>)
LERP_CUTOFF = 0.99         # f64 @0x00A53BF8 -- t >= 0.99 takes b verbatim
                           # (studies/movement/FINDINGS.md:2739)
GATE1_SNAP_DISTSQ = 89600.0  # snap iff distSq >= 89600.0f: the LUT-sqrt makes
                           # the effective true threshold 299.332591 u, and a
                           # true 300.0 u SNAPS (studies/movement/
                           # FINDINGS.md:3145-3158). We compare the SQUARE
                           # against 89600.0 directly, which reproduces the
                           # client's decision exactly without its sqrt.
PUSH_RESAMPLE_MS = 2500    # 0x0060593A cmp eax,0x9c4 -- forced re-sample when
                           # the head is older (studies/movecode/FINDINGS.md
                           # 1z-q.3)
SWEEP_STALE_MS = 3333      # 0x00604AAE cmp eax,0xd05 -- the per-tick update
                           # loop calls the recorder when the head is stale
                           # (studies/movecode/FINDINGS.md 1z-q.3)
DEFAULT_MAX_SPEED = 288.0  # agent+0x5C typical (studies/movement/
                           # FINDINGS.md:1413)
DEFAULT_MOVE_SPEED = 1.0   # agent+0x60 typical (same citation)
ZERO_DIST_SQ = 1.0         # the bake's short-circuit: distSq <= 1.0 writes
                           # +0x78 = D directly (studies/movement/
                           # FINDINGS.md:3736)

# Verdict codes returned by AgTrackMirror.on_* event methods.
NOT_TESTED = "not-tested"      # fence closed / recorded instead / q invalid
MATCH = "match"                # reprieve -- no snap, chain truncated
NOMATCH_PASS = "nomatch-pass"  # walk missed, all modelled gates passed
SNAP = "snap"                  # walk missed AND a modelled gate failed


class Verdict(object):
    """One evaluation's outcome, with everything needed to audit it."""

    __slots__ = ("t", "code", "q", "chain_len", "matched_age_ms", "gate1",
                 "gate2", "gate1_sep", "event", "recorded", "matched")

    def __init__(self, t, code, q=None, chain_len=0, matched_age_ms=None,
                 gate1=None, gate2=None, gate1_sep=None, event="",
                 recorded=False, matched=None):
        self.t = t
        self.code = code
        self.q = q
        self.chain_len = chain_len
        self.matched_age_ms = matched_age_ms
        self.gate1 = gate1          # True = passed, False = failed, None = n/a
        self.gate2 = gate2
        self.gate1_sep = gate1_sep  # straight-line separation (float), if run
        self.event = event
        self.recorded = recorded
        self.matched = matched      # (node_xyplane, prev_xyplane, sig) on MATCH

    def __repr__(self):
        return ("Verdict(t=%s, %s, event=%s, chain=%d)"
                % (self.t, self.code, self.event, self.chain_len))


# ---------------------------------------------------------------------------
# The mesh adapter -- the walkable conjunct and gate 2, injectable.
# ---------------------------------------------------------------------------

# GATE 2 ON-MESH TOLERANCE (MOVECODE-1z-bf, 2026-09-04).  DERIVED from the
# corpus and from two hooked runs, and it is the whole of the "guard fix"
# sec.1z-be.6 filed.
#
# WHAT WAS WRONG.  Gate 2 was modelled as pathmap.walkable(a) -- EXACT
# containment of the modelled sync copy in a trapezoid, on any plane.  Every
# gate2-offmesh re-pin the server ever sent (17 fired, 19 predicted, 1,123
# harness runs) was raised with that copy standing on a point walkable()
# rejects by <= 0.5 u: the previous accepted REPORT, i.e. where the client's
# own body stood and said so.  The client lays keyboard waypoints along
# trapezoid edges (sec.1z-bd.2: 0.01-0.03 u outside the plane by our decode),
# so its positions live on our edges' rounding.  On both runs with the
# movehook attached (RUN-1zBD) the client's snap test ran on the very grant we
# vetoed -- and did not reseed.  The prediction was false, the 0x002C it
# licensed landed on a drawn body walking at 205 u/s and halted it, and the
# held key never re-dispatched (sec.1z-be.4).
#
# THE FIX.  Gate 2 asks pathmap.on_mesh(a, GATE2_SEAM_TOL): inside a
# trapezoid OR within 1 u of one -- the mesh as the client resolves it at its
# edges.  The tolerance is pathmap.SEAM_TOL, the constant portal_at() already
# uses to see zero-height portal lines; it is not a new number.  It is the
# SMALLEST tolerance the evidence needs (all 17 at <= 0.5 u); the client's own
# gate 2 is looser still (a query 32 u off its declared plane returned a path
# in RUN-1zBD run 2), and that looseness is deliberately NOT modelled here --
# widening the mesh by tens of units would be a guess from n = 1, and the
# failure direction of a too-narrow gate 2 is a false veto, which this repo
# has now measured the cost of once.  0.0 reverts to exact containment
# (authsrv --agtrack-gate2-exact).
GATE2_SEAM_TOL = 1.0

class MeshAdapter(object):
    """Wraps a toolkit/mapdata/pathmap.PathingMap for the two navmesh queries.

    The client's `map_path_len(q, c, limit=r, straight_only=False)`
    (0x00709990 with push 0, studies/movement/FINDINGS.md:2742) is a walkable
    path length; its plane-mismatch route is a real navmesh pathfind whose
    failure returns range+1 (REALFIX.md via studies/movement/
    FINDINGS.md:2756-2765).  We reproduce it as:
      - same plane and the straight line is walkable end-to-end (clip reaches
        c): path length == straight distance;
      - otherwise: route() with plane preference; None -> fail; else the
        polyline length.
    Gate 2's `pathCount == 0` means THE START POINT (the sync position we
    granted) is off the navmesh -- narrower than "no path" (studies/movement/
    FINDINGS.md:3176).  We reproduce it as on_mesh(A, GATE2_SEAM_TOL): exact
    containment was measured false at the client's own positions along
    trapezoid edges (the block above the class).

    MODEL-CHOICE: our PathingMap is our own reconstruction of the same
    trapezoid data the client queries -- pinned per capture by the in-band
    file id (planecensus).  Divergence between the two IS a finding, and the
    replay is where it would show.
    """

    def __init__(self, pathing_map):
        self.pm = pathing_map

    def start_walkable(self, x, y):
        if GATE2_SEAM_TOL > 0.0 and hasattr(self.pm, "on_mesh"):
            return self.pm.on_mesh(x, y, GATE2_SEAM_TOL)
        return self.pm.walkable(x, y)

    def path_len_ok(self, qx, qy, qplane, cx, cy, cplane, limit):
        d = math.hypot(cx - qx, cy - qy)
        if d > limit:
            # The path can never be shorter than the straight line.
            return False
        same_plane = (qplane is None or cplane is None or qplane == cplane)
        if same_plane:
            end = self.pm.clip(qx, qy, cx, cy)
            if (abs(end[0] - cx) < 1e-6 and abs(end[1] - cy) < 1e-6):
                return True     # clear straight walk; length == d <= limit
        path = self.pm.route(qx, qy, cx, cy,
                             start_plane=qplane, goal_plane=cplane)
        if not path:
            return False
        total = 0.0
        for i in range(1, len(path)):
            total += math.hypot(path[i][0] - path[i - 1][0],
                                path[i][1] - path[i - 1][1])
        return total <= limit


class NoMesh(object):
    """Straight-line-only degradation, for meshless replay.

    The walkable conjunct can only turn a would-be MATCH into a MISS (it is an
    AND), so with no mesh this adapter reports the conjunct as passed --
    making the mirror's MATCH an UPPER BOUND on the client's.  Any consumer
    scoring the killing cell ("client snapped but mirror said MATCH") must
    treat a meshless MATCH as 'match-straightline-only' -- the replay does.
    Gate 2 degrades to 'pass' (never snaps), which UNDER-predicts snaps.
    """

    straightline_only = True

    def start_walkable(self, x, y):
        return True

    def path_len_ok(self, qx, qy, qplane, cx, cy, cplane, limit):
        return math.hypot(cx - qx, cy - qy) <= limit


# ---------------------------------------------------------------------------
# The sync agent -- the authoritative copy our grants drive.
# ---------------------------------------------------------------------------

class SyncAgent(object):
    """The server-authoritative copy of the player, simulated by the client's
    own decoded equations.  Field names follow the client offsets they mirror.

      x78, y78      +0x78/+0x7C  the leg-start / epoch position
      plane         +0x80        the agent's current plane word
      dest          +0x88..+0x94 (x, y, plane) or None for the +inf sentinel
      t_epoch       +0x58        epoch time (ms) of the current leg
      t_arrive      +0x48        arrival tick (ms); 0 = none armed
      vx, vy        +0xB0/+0xB4  baked velocity (u/s)
      max_speed     +0x5C        (written by 0x0027, read as S)
      move_speed    +0x60        (written by 0x002B, read as S)

    The dead-reckoner (0x005FFB40) is exactly
        pos(t) = (x78, y78) + (vx, vy) * ((t - t_epoch) * 0.001)
    with NO clamp at the destination -- overshoot is prevented only by the
    arrival-tick check switching the resolver's arm (studies/movement/
    FINDINGS.md:2416-2422, 1391-1408).
    """

    def __init__(self):
        self.x78 = None      # None until the first position-bearing event
        self.y78 = None
        self.plane = None
        self.dest = None     # (x, y, plane) or None (the +inf sentinel)
        self.t_epoch = 0
        self.t_arrive = 0    # 0 = no arrival armed
        self.vx = 0.0
        self.vy = 0.0
        self.max_speed = DEFAULT_MAX_SPEED
        self.move_speed = DEFAULT_MOVE_SPEED

    # -- the resolver 0x005FF820: arrived -> dest verbatim; else dead-reckon
    def position(self, now_ms):
        if self.x78 is None:
            return None
        if self.t_arrive != 0 and now_ms >= self.t_arrive:
            if self.dest is not None:
                return (self.dest[0], self.dest[1])
            # +0x48 armed with an invalid target would trip ArenaNet's own
            # assert (AgAgent.cpp 2090, cited studies/movement/
            # FINDINGS.md:3677); consume_arrival() keeps us out of this state.
            return (self.x78, self.y78)
        dt = (now_ms - self.t_epoch) * 0.001
        return (self.x78 + self.vx * dt, self.y78 + self.vy * dt)

    # -- the settle 0x005FF880: dead-reckon +0x78 in place, on the world clock
    #    (studies/movement/FINDINGS.md:2783-2786)
    def settle(self, now_ms):
        p = self.position(now_ms)
        if p is not None:
            self.x78, self.y78 = p
            self.t_epoch = now_ms

    # -- arrival consumption -> the teleport primitive 0x006020B0: +0x78 <-
    #    the destination, velocity zeroed, both target blocks invalidated
    #    (+inf), and +0x48 cleared to keep AgAgent.cpp(2090)'s invariant
    #    (studies/movecode/FINDINGS.md:555-577; clearing +0x48 is
    #    MODEL-CHOICE forced by that assert -- see position() above).
    def consume_arrival(self, now_ms):
        """Returns True if an arrival was consumed (a dispatch fires then)."""
        if self.t_arrive == 0 or now_ms < self.t_arrive:
            return False
        if self.dest is not None:
            self.x78, self.y78 = self.dest[0], self.dest[1]
        self.vx = self.vy = 0.0
        self.dest = None
        self.t_arrive = 0
        self.t_epoch = now_ms
        return True

    # -- the 0x0029/0x002A setter (0x00602A40) + bake (0x005FE950)
    def bake_grant(self, x, y, plane_first, plane_second, now_ms):
        """Apply one movement grant exactly as the client's handler does.

        Setter: destination <- the wire point with plane_first (the
        DESTINATION's plane); agent plane +0x80 <- plane_second (the wire's
        second word, the AGENT's current plane) (studies/movement/
        FINDINGS.md:849-867).  Bake: settle +0x78, measure d FROM +0x78 --
        never from the player (studies/movement/FINDINGS.md:3724-3736).
        """
        if self.x78 is None:
            # First grant ever seen: the agent's spawn placement predates our
            # window.  Seed +0x78 at the destination (the zero-distance arm's
            # own behaviour), so the sim starts defined.  MODEL-CHOICE.
            self.x78, self.y78 = float(x), float(y)
        self.dest = (float(x), float(y), plane_first)
        if plane_second is not None:
            self.plane = plane_second
        self.settle(now_ms)
        dx, dy = float(x) - self.x78, float(y) - self.y78
        d2 = dx * dx + dy * dy
        if d2 <= ZERO_DIST_SQ:
            # 0x005FEA85: writes +0x78 = D directly, zeroes velocity, arms
            # +0x48 = max(now+1, 1) (studies/movement/FINDINGS.md:3736).
            self.x78, self.y78 = float(x), float(y)
            self.vx = self.vy = 0.0
            self.t_epoch = now_ms
            self.t_arrive = max(now_ms + 1, 1)
            return
        s = self.max_speed * self.move_speed
        if s <= 0.0:
            self.vx = self.vy = 0.0
            self.t_arrive = 0
            return
        dist = math.sqrt(d2)
        self.vx, self.vy = dx / dist * s, dy / dist * s
        self.t_epoch = now_ms
        self.t_arrive = now_ms + max(int(dist * 1000.0 / s), 1)

    # -- 0x002C's SetPosition (0x00602B20): position, velocity, both target
    #    blocks written; the handler Clears AgTrack FIRST (caller's job).
    def set_position(self, x, y, plane, now_ms):
        self.x78, self.y78 = float(x), float(y)
        if plane is not None:
            self.plane = plane
        self.vx = self.vy = 0.0
        self.dest = None
        self.t_arrive = 0
        self.t_epoch = now_ms


# ---------------------------------------------------------------------------
# History chain node.
# ---------------------------------------------------------------------------

class Node(object):
    """One 0x2C history node (studies/movecode/FINDINGS.md 1z-q.1).

    position (+0x08..+0x14) is what 0x005FF820 resolved at push time;
    `sig` stands in for the velocity/speed/speed/facing block (+0x18..+0x28)
    -- the recorder compares those four against the head node to detect a
    command change, and equality of a compact signature reproduces that
    compare without needing the client's exact floats.  MODEL-CHOICE, load-
    bearing only for push CADENCE, not for geometry: a sig that differs when
    the client's floats differ pushes at the same instants.
    """

    __slots__ = ("t", "x", "y", "plane", "sig", "nxt")

    def __init__(self, t, x, y, plane, sig, nxt=None):
        self.t = t
        self.x = x
        self.y = y
        self.plane = plane
        self.sig = sig
        self.nxt = nxt


# ---------------------------------------------------------------------------
# The geometry -- seg_match, transcribed from 0x00605AF0.
# ---------------------------------------------------------------------------

def _closest_pt(qx, qy, ax, ay, bx, by):
    """0x0046DE80: squared distance to segment + clamped parameter t."""
    abx, aby = bx - ax, by - ay
    den = abx * abx + aby * aby
    if den <= 0.0:
        dx, dy = ax - qx, ay - qy
        return dx * dx + dy * dy, 0.0
    t = ((qx - ax) * abx + (qy - ay) * aby) / den
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    cx, cy = ax + t * abx, ay + t * aby
    dx, dy = cx - qx, cy - qy
    return dx * dx + dy * dy, t


def seg_match(qx, qy, qplane, ax, ay, aplane, bx, by, bplane, mesh):
    """The dual 100 u test, 0x00605AF0 (studies/movement/FINDINGS.md:2732-2743).

    a = the node's position, b = `prev` (the seed for segment 0, else the
    next-newer node).  Degenerate segment (a == b): straight-line squared
    strict test ONLY -- no plane word read, no pathfind (:2733-2735, and the
    2026-08-26 live exercise :2766-2772).  Non-degenerate: straight-line
    squared strict AND walkable path to the closest point, linear inclusive.
    c = b VERBATIM when t >= 0.99 (b's plane, :2739 + the +0x14 note :2853),
    else the lerp with THE NODE's plane (a.plane, 0x00605BD5).
    """
    if ax == bx and ay == by:
        dx, dy = ax - qx, ay - qy
        return R_MATCH_SQ > dx * dx + dy * dy
    d2, t = _closest_pt(qx, qy, ax, ay, bx, by)
    if not (R_MATCH_SQ > d2):
        return False
    if t >= LERP_CUTOFF:
        cx, cy, cplane = bx, by, bplane
    else:
        cx, cy = ax + t * (bx - ax), ay + t * (by - ay)
        cplane = aplane
    return mesh.path_len_ok(qx, qy, qplane, cx, cy, cplane, R_MATCH)


# ---------------------------------------------------------------------------
# The mirror proper.
# ---------------------------------------------------------------------------

class AgTrackMirror(object):
    """The player agent's AgTrack state record + history chain + dispatcher.

    Fences and routing transcribed from agtrack_dispatch (0x00605FC0,
    studies/movement/FINDINGS.md:3103-3115):

        clientControlled == 0  -> RECORD (0x0060610B), never test
        source.world == 1      -> RECORD, never test
        world-0 + controlled   -> TEST; ok -> nothing; fail -> Clear + record
                                  + whole-roster reseed (the warp)

    Resets (studies/movecode/FINDINGS.md 1z-q.3): AgTrack::Clear zeroes
    clientControlled AND the history head; called by the 0x002C handler,
    every adjudicated MISS, and player-input re-arm -- where re-arm is a
    NO-OP on an already-armed record and NEVER clears the seed
    (studies/movement/FINDINGS.md:3681, :3701 -- the seed can be a
    server-written point that survives the re-arm).
    """

    def __init__(self, mesh=None, prune_ms=None):
        self.sync = SyncAgent()
        self.mesh = mesh if mesh is not None else NoMesh()
        self.client_controlled = False   # armed only by player input
        self.head = None                 # newest node
        self.seed = None                 # (x, y, plane) -- state+0x08..+0x14
        self.seed_t = 0                  # state+0x18
        self.chain_len = 0
        # READER 2 -- the by-time render query 0x00604ED0 in the update
        # loop, which prunes the chain identically to the match test
        # (returnedSegment.next = NULL, 0x006055C2; studies/movecode/
        # FINDINGS.md 1z-q.4).  Its query time and per-agent cadence are the
        # decode's own flagged unknowns (the sweep 0x00604880's cadence,
        # 1z-q's "not settled" list), so it is a PARAMETER here: at each
        # tick, nodes older than now - prune_ms are dropped, KEEPING one
        # older node (the returned segment needs its far end).  None = the
        # reader never runs (the long-chain model).  The replay adjudicates
        # the value against the corpus -- see agtrack_replay.py.
        self.prune_ms = prune_ms
        # counters for consumers
        self.n_push = 0
        self.n_clear = 0
        self.n_truncate = 0

    # ---- resets ----------------------------------------------------------

    def clear(self):
        """AgTrack::Clear 0x00605F70 -- zeroes state+0x00 and +0x04 ONLY
        (0x00605FA7/0x00605FAE); the seed at +0x08..+0x18 survives."""
        self.client_controlled = False
        self.head = None
        self.chain_len = 0
        self.n_clear += 1

    def re_arm(self):
        """0x00605F10, from player-command sites: a no-op when already armed
        (0x00605F3F/0x00605F43); on the 0->1 edge it arms and nulls the HEAD
        -- never the seed (studies/movement/FINDINGS.md:3681, :3701)."""
        if self.client_controlled:
            return
        self.client_controlled = True
        self.head = None
        self.chain_len = 0

    # ---- the recorder 0x00605840 ----------------------------------------

    def _record(self, now_ms, pos, plane, sig, dest, arrive_t):
        """Push rule (studies/movecode/FINDINGS.md 1z-q.3; studies/movement/
        FINDINGS.md:2811-2834): candidate seed = the DESTINATION with
        state.time = the arrival tick while one is armed (+0x48 != 0), else
        the position dead-reckoned to now with state.time = now
        (0x006058D6/0x00605909).  Push on a 7-field command change --
        candidate-position/plane vs the stored seed, sig vs the head -- OR
        when the head is older than 2500 ms.  Identical command inside
        2.5 s pushes NOTHING.  Seed is rewritten on push (0x00605A38-4D;
        the record leaves open whether the seed store also fires on the
        no-push arm -- MODEL-CHOICE: push-only, per the address ordering
        argument in the same section)."""
        if pos is None:
            return False
        if arrive_t and dest is not None:
            cand = (dest[0], dest[1], dest[2] if len(dest) > 2 else plane)
            cand_t = arrive_t
        else:
            cand = (pos[0], pos[1], plane)
            cand_t = now_ms
        changed = (self.seed is None or cand[0] != self.seed[0]
                   or cand[1] != self.seed[1] or cand[2] != self.seed[2]
                   or self.head is None or sig != self.head.sig)
        stale = (self.head is not None
                 and now_ms - self.head.t >= PUSH_RESAMPLE_MS)
        if not (changed or stale or self.head is None):
            return False
        self.head = Node(now_ms, pos[0], pos[1], plane, sig, self.head)
        self.chain_len += 1
        self.seed = cand
        self.seed_t = cand_t
        self.n_push += 1
        return True

    def record_sync(self, now_ms):
        """Record the SYNC copy (the sweep's push, and the fence-closed /
        post-miss appends).  Samples via the resolver, like 0x006058BF."""
        pos = self.sync.position(now_ms)
        sig = ("sync", round(self.sync.vx, 3), round(self.sync.vy, 3),
               self.sync.max_speed, self.sync.move_speed)
        return self._record(now_ms, pos, self.sync.plane, sig,
                            self.sync.dest, self.sync.t_arrive)

    def record_async(self, now_ms, pos, plane, sig, dest=None, arrive_t=0):
        """Record the ASYNC copy -- the player's own command events, which
        the server observes as c2s traffic (0x003E click / 0x003D heading /
        0x0047 stop).  `pos` is the async position at the event (the report's
        own [x, y], or the replay's interpolation), `dest` a click's
        destination if one is in flight."""
        return self._record(now_ms, pos, plane, sig, dest, arrive_t)

    # ---- the sweep (per-tick keep-alive) ---------------------------------

    def sweep(self, now_ms):
        """The update loop calls the recorder when the head is stale
        (0x00604AAE, >= 3333 ms) -- and it samples the SYNC copy
        (studies/movecode/FINDINGS.md 1z-q.2's bulk sampler, [ctx-0xE4]).
        MODEL-CHOICE on the empty-chain arm: treat an empty chain as stale
        (records immediately) -- post-0x002C the real client's SetPosition
        dispatches append within the same handler anyway."""
        if self.head is not None and now_ms - self.head.t < SWEEP_STALE_MS:
            return False
        return self.record_sync(now_ms)

    # ---- the walk + gates (agtrack_ok, 0x006055E0) -----------------------

    def _walk(self, qx, qy, qplane):
        """Newest -> oldest, prev seeded from state.position; guard tests
        PREV only; NO break -- the OLDEST matching node wins
        (studies/movement/FINDINGS.md:2707-2718).  The walk itself is pure;
        evaluate() applies the truncation.  Alias of _walk_pure so the
        prediction path and the live path cannot drift apart."""
        return self._walk_pure(qx, qy, qplane)

    def evaluate(self, now_ms, async_pos, event="", no_reset=False):
        """One dispatch on the world-0 (sync) copy: the reprieve test, then
        the gates on a miss.  `async_pos` is the rendered copy's position for
        gate 1 (the replay interpolates it from the report stream; live use
        would take the latest report).  Returns a Verdict; applies the
        consequence chain (truncate on match; Clear + record on snap).

        `no_reset=True` suppresses ONLY the miss-path Clear/record: the
        guard's TWIN mirror models the world where the client never reset
        on our predicted snaps (only 0x002C -- server-caused -- resets are
        real there).  Match truncation still applies: it is a real client
        behaviour in both worlds and only prunes the tail."""
        if not self.client_controlled:
            # fence 0x00606002: never tested; falls through to the appender
            # (0x0060610B -- studies/movement/FINDINGS.md:3701).
            rec = self.record_sync(now_ms)
            return Verdict(now_ms, NOT_TESTED, chain_len=self.chain_len,
                           event=event, recorded=rec)
        q = (self.sync.x78, self.sync.y78)
        if q[0] is None:
            return Verdict(now_ms, NOT_TESTED, chain_len=self.chain_len,
                           event=event)
        qplane = self.sync.plane
        m, m_prev = self._walk(q[0], q[1], qplane)
        if m is not None:
            if m.nxt is not None:
                m.nxt = None                    # 0x00605746 -- drop the tail
                # recount (chains are short; O(n) is fine)
                n, node = 0, self.head
                while node is not None:
                    n, node = n + 1, node.nxt
                self.chain_len = n
                self.n_truncate += 1
            return Verdict(now_ms, MATCH, q=q, chain_len=self.chain_len,
                           matched_age_ms=now_ms - m.t, event=event,
                           matched=((m.x, m.y, m.plane), m_prev, m.sig))
        # ---- fallback gates (studies/movement/FINDINGS.md:3117-3141) ----
        a = self.sync.position(now_ms)
        gate1 = None
        sep = None
        if async_pos is not None and a is not None:
            dx, dy = a[0] - async_pos[0], a[1] - async_pos[1]
            d2 = dx * dx + dy * dy
            sep = math.sqrt(d2)
            gate1 = d2 < GATE1_SNAP_DISTSQ      # snap iff distSq >= 89600.0f
        gate2 = None
        if a is not None and not getattr(self.mesh, "straightline_only",
                                         False):
            gate2 = self.mesh.start_walkable(a[0], a[1])
        # gate 3 unmodelled (other agents' personal space) -- always passes.
        failed = (gate1 is False) or (gate2 is False)
        if failed:
            if not no_reset:
                # MISS adjudicated: Clear, then append one fresh node
                # (0x00605F70 + 0x00605840, studies/movement/
                # FINDINGS.md:3109-10).
                self.clear()
                self.record_sync(now_ms)
            return Verdict(now_ms, SNAP, q=q, chain_len=self.chain_len,
                           gate1=gate1, gate2=gate2, gate1_sep=sep,
                           event=event)
        return Verdict(now_ms, NOMATCH_PASS, q=q, chain_len=self.chain_len,
                       gate1=gate1, gate2=gate2, gate1_sep=sep, event=event)

    # ---- wire events -----------------------------------------------------

    def on_grant(self, x, y, plane_first, plane_second, now_ms,
                 async_pos=None, opcode=0x29, no_reset=False):
        """A 0x0029/0x002A to the player: setter + bake, then the bake-tail
        dispatch (caller A, 0x005FEBEB) -- an EVALUATION when the fence is
        open, an append when it is closed."""
        self.sync.consume_arrival(now_ms)
        self.sync.bake_grant(x, y, plane_first, plane_second, now_ms)
        return self.evaluate(now_ms, async_pos,
                             event="grant-0x%04X" % opcode,
                             no_reset=no_reset)

    def on_update_position(self, x, y, plane, now_ms):
        """A 0x002C: AgTrack::Clear FIRST (0x005FDA78), then SetPosition on
        both copies; each SetPosition's dispatch lands on the record path
        because the fence is now closed (studies/movement/
        FINDINGS.md:2449-2452 via lane B; studies/movecode/FINDINGS.md
        1z-q.3)."""
        self.clear()
        self.sync.set_position(x, y, plane, now_ms)
        rec = self.record_sync(now_ms)
        return Verdict(now_ms, NOT_TESTED, chain_len=self.chain_len,
                       event="0x002C", recorded=rec)

    def on_speed(self, move_speed, now_ms):
        """0x002B: SYNC-only pure store of moveSpeed (+0x60) -- no tick, no
        velocity, no re-arm of +0x48 (studies/movement/FINDINGS.md:2410-15).
        The CURRENT leg keeps its baked velocity; only later bakes see it."""
        self.sync.move_speed = move_speed

    def on_player_command(self, now_ms, pos, plane, sig, dest=None,
                          arrive_t=0):
        """A player movement command (click 0x003E / heading 0x003D / stop
        0x0047 as the server observes it): re-arms the record on the 0->1
        edge (0x00605F10), then the async copy's own bake dispatches world-1
        -> the recorder (fence 0x00606013)."""
        self.re_arm()
        return self.record_async(now_ms, pos, plane, sig, dest, arrive_t)

    # ---- pure prediction (no mutation) -----------------------------------

    def predict(self, now_ms, async_pos, q=None, qplane=None):
        """The reprieve test + gates as a PURE function: no truncation on a
        match, no Clear on a miss, no record.  For the pre-emit guard --
        a prediction must not edit the chain it predicts about.

        Returns one of NOT_TESTED / MATCH / NOMATCH_PASS / SNAP with the same
        semantics as evaluate(); q defaults to the live sync copy's +0x78."""
        if not self.client_controlled:
            return Verdict(now_ms, NOT_TESTED, chain_len=self.chain_len,
                           event="predict")
        if q is None:
            q = (self.sync.x78, self.sync.y78)
            qplane = self.sync.plane
        if q[0] is None:
            return Verdict(now_ms, NOT_TESTED, chain_len=self.chain_len,
                           event="predict")
        m, m_prev = self._walk_pure(q[0], q[1], qplane)
        if m is not None:
            return Verdict(now_ms, MATCH, q=q, chain_len=self.chain_len,
                           matched_age_ms=now_ms - m.t, event="predict",
                           matched=((m.x, m.y, m.plane), m_prev, m.sig))
        a = self.sync.position(now_ms)
        gate1 = None
        sep = None
        if async_pos is not None and a is not None:
            dx, dy = a[0] - async_pos[0], a[1] - async_pos[1]
            d2 = dx * dx + dy * dy
            sep = math.sqrt(d2)
            gate1 = d2 < GATE1_SNAP_DISTSQ
        gate2 = None
        if a is not None and not getattr(self.mesh, "straightline_only",
                                         False):
            gate2 = self.mesh.start_walkable(a[0], a[1])
        code = SNAP if (gate1 is False or gate2 is False) else NOMATCH_PASS
        return Verdict(now_ms, code, q=q, chain_len=self.chain_len,
                       gate1=gate1, gate2=gate2, gate1_sep=sep,
                       event="predict")

    def predict_grant(self, x, y, plane_first, plane_second, now_ms,
                      async_pos):
        """What would delivering this 0x0029 do?  Bakes on a THROWAWAY copy
        of the sync agent (the bake settles +0x78 and re-aims, so q at the
        grant's own dispatch is the settled position), then runs the pure
        prediction with that q.  The live mirror is untouched."""
        s = SyncAgent()
        s.x78, s.y78 = self.sync.x78, self.sync.y78
        s.plane = self.sync.plane
        s.dest = self.sync.dest
        s.t_epoch = self.sync.t_epoch
        s.t_arrive = self.sync.t_arrive
        s.vx, s.vy = self.sync.vx, self.sync.vy
        s.max_speed = self.sync.max_speed
        s.move_speed = self.sync.move_speed
        s.consume_arrival(now_ms)
        s.bake_grant(x, y, plane_first, plane_second, now_ms)
        if s.x78 is None:
            return Verdict(now_ms, NOT_TESTED, chain_len=self.chain_len,
                           event="predict-grant")
        v = self.predict(now_ms, async_pos, q=(s.x78, s.y78), qplane=s.plane)
        v.event = "predict-grant"
        return v

    def _walk_pure(self, qx, qy, qplane):
        """The walk without the truncation side effect."""
        prev = self.seed
        node = self.head
        last_match = None
        last_prev = None
        while node is not None:
            if prev is not None:
                if seg_match(qx, qy, qplane, node.x, node.y, node.plane,
                             prev[0], prev[1], prev[2], self.mesh):
                    last_match = node
                    last_prev = prev
            prev = (node.x, node.y, node.plane)
            node = node.nxt
        return last_match, last_prev

    def render_prune(self, now_ms):
        """READER 2 (see __init__): drop nodes older than now - prune_ms,
        keeping one older node as the returned segment's far end."""
        if self.prune_ms is None or self.head is None:
            return
        cutoff = now_ms - self.prune_ms
        node = self.head
        kept = 1
        while node.nxt is not None:
            if node.t < cutoff:
                # `node` is the one kept-older far end; drop its tail.
                if node.nxt is not None:
                    node.nxt = None
                    self.n_truncate += 1
                break
            node = node.nxt
            kept += 1
        # recount
        n, node = 0, self.head
        while node is not None:
            n, node = n + 1, node.nxt
        self.chain_len = n

    def tick(self, now_ms, async_pos=None, no_reset=False):
        """Advance internal time: consume a due sync arrival (which fires a
        caller-B dispatch -> an EVALUATION, studies/movement/
        FINDINGS.md:3675), then the keep-alive sweep, then reader 2's
        prune."""
        v = None
        if self.sync.consume_arrival(now_ms):
            v = self.evaluate(now_ms, async_pos, event="arrival",
                              no_reset=no_reset)
        self.sweep(now_ms)
        self.render_prune(now_ms)
        return v
