"""agtrack_guard.py -- the derived pre-emit grant rule (MOVECODE-1z-s,
HANDOFF SS-D' item 0).

THE RULE, DERIVED -- NOT TUNED.  Every constant below is either a decoded
client constant or one arithmetic step from two of them; nothing here was
fitted to a metric (the arc's derive-don't-iterate direction).  The decoded
machinery (FINDINGS SS-1z-q/1z-r) forces a three-zone structure on the
sync copy's separation from the player's rendered path:

  GREEN  -- q within 100 u of the current-leg tube: the reprieve test
            MATCHES and a match jumps clean over all three gates.  Nothing
            can snap.  This is where retail lived (its stop-acks answered
            the client's own reported point at p50 34 ms).
  YELLOW -- out of tube but separation < 299.33 u with the sync copy
            on-mesh: evaluations run the gates; gates 1 and 2 pass; gate 3
            (other agents' personal space) is the residual risk.  A grant
            aimed back along the player's path recovers the tube at
            288 u/s.
  RED    -- separation >= 299.332591 u, or the sync copy off-mesh: ANY
            evaluation snaps, INCLUDING the one triggered by the very
            grant that tries to fix it (the bake's tail dispatch runs the
            test with q = the settled position, which the grant did not
            move -- no 0x0029 can recover from red).  The only exit is
            0x002C, whose handler calls AgTrack::Clear FIRST, so no test
            runs behind it (p5-resync-disarm SS-1: measured on the owner's
            machine, both copies land on the message's point, +0x48 -> 0).

Three clauses follow, each forced by the zones:

  1. VETO + REPLACE.  A grant whose own delivery-evaluation predicts a
     snap is never sent.  If a fresh accepted report exists, the re-pin
     (0x002C at the client's own reported position -- invisible, the body
     is already there) goes first; the held grant may follow immediately,
     because after a 0x002C the fence is CLOSED and a grant APPENDS to the
     chain instead of testing (dispatcher fence 0x00606002; round 5's
     "client only is REFUTED").  The composition is safe by the decode,
     not by testing.
  2. PROACTIVE ARRIVAL CHECK.  Evaluations the server does not trigger are
     the sync copy's own ARRIVALS (teleport primitive tail -> dispatch),
     and the mirror KNOWS every arrival tick (it computed it at the bake).
     Before an arrival matures, predict the evaluation at q = the
     destination; a predicted snap re-pins first, on the server's own
     clock.  This closes p5-resync-disarm HOLE A (the report-driven sender
     could never reach an arrival inside a report gap).
  3. TUBE-KEEPING IS AUDITED, NOT ASSUMED.  In shadow mode the guard
     predicts every emitted grant's delivery verdict and counts them, so
     "the router keeps the tube" is a number in every capture rather than
     a belief.

WHAT THIS MODULE DOES NOT DO.  It sends nothing and mutates no server
state -- it returns verdicts.  The active wiring lives in `authsrv.py`.

CORRECTED 2026-09-05 (MOVECODE-1z-bh, studies/review/MOVEMENT-2026-09-04.md
sec.4).  This paragraph used to continue "The active wiring (actually
vetoing sends, actually firing the re-pin) is a behaviour change that ships
OFF by default; the shadow feed is telemetry-only".  That has been false
since MOVECODE-1z-s.5: `AGTRACK_SHADOW` and `AGTRACK_REPIN` are BOTH True
in `authsrv.py`, so the veto and the re-pin are the shipped default and
this module's verdicts really do move the wire (72 live fires across 30
captures; `--no-agtrack-shadow` / `--no-agtrack-repin` are the reverts).
Read the sentence as scoping THIS FILE -- it is pure and returns verdicts
-- and not as a statement about what ships.  The re-pin's own
preconditions (report freshness,
the refused-report hole, rate) inherit _resync_verdict's derivations and
are re-derived here from decoded constants; the test pins this module's
values against authsrv's so they cannot drift apart.

Pure stdlib.  Time in float seconds at the API (server clock); the mirror
runs on integer ms with a per-session epoch.
"""

import math

import agtrack_mirror as am

# ---------------------------------------------------------------------------
# Derived constants.  Each is a decoded client constant or one arithmetic
# step from two of them; the citation is the derivation.
# ---------------------------------------------------------------------------

RUN_SPEED = 288.0
# The client's own effective gate-1 cut: snap iff distSq >= 89600.0f, true
# separation 299.332591 u (studies/movement/FINDINGS.md:3145-3158).
GATE1_RED = 299.332591
# The client's world clock runs ~1.36% slow; over the 2.5 s node cadence at
# 288 u/s that is ~10 u of irreducible position uncertainty in the mirror
# (FINDINGS 1z-q.5).
CLOCK_SKEW_U = 10.0
# The rendered copy can be up to RUN_SPEED * report_age past its last
# accepted report -- corroborated as a real ceiling, not just arithmetic
# (authsrv RESYNC_MAX_REPORT_AGE block: p99 walking steps sit exactly at
# speed*age).  The guard adds this term live, per report age.
#
# Re-pin preconditions, re-derived from the same two decoded constants
# authsrv derives them from (the test pins equality so they cannot drift):
# max harm of a re-pin = RUN_SPEED * age, chosen == the client's own 100 u
# "close enough" radius; min interval = the shortest time separation can
# grow 0 -> GATE1_RED at closing speed 2*RUN_SPEED, rounded down.
REPIN_MAX_REPORT_AGE = am.R_MATCH / RUN_SPEED          # 0.347222 s
REPIN_MIN_INTERVAL = 0.5                                # < 299.33/576 s

# THE FRESHNESS GATE STANDS ON AGE ALONE (MOVECODE-1z-bt).  Three switches
# used to sit here -- STATIONARY_WAIVER (1z-ah), WAIVER_WALKSTART_ENDS_STILL
# (1z-bn) and WAIVER_NEWEST_MUST_BE_STOP (1z-bs) -- and the owner deleted the
# waiver on 2026-09-05 (PLAN.md sec.7 Q15).  Their record is FINDINGS
# sec.1z-ah through sec.1z-bt.  What stays is the derivation the waiver
# argued against, because it is the bound this gate enforces:
#
# WHY THE GATE CANNOT BE OPENED ON A STALE REPORT.  A 0x002C is not
# sync-only: its handler 0x005FDA50 Clears the record first, then
# SetPositions the sync twin (AgMsg.cpp 579) AND the async twin (AgMsg.cpp
# 584) -- BOTH copies land on the same point (studies/movement/FINDINGS.md
# :3246).  So re-pinning a SILENTLY WALKING body back to a stale report
# drags the drawn body with it.  An earlier build of this server sent five,
# "three were arrivals, carrying the client 630, 189 and 765 units", and
# they were removed as THE WARP THE PLAYER DESCRIBED.  RUN_SPEED * age is
# exactly the bound that prevents it, and on age alone it stands.
#
# WHAT THE WAIVER CLAIMED, AND WHAT THE CORPUS SAID.  It argued that two
# coincident accepted reports MEASURE a still body, so the bound is the
# client's zero-distance radius and the gate has nothing to protect.  Every
# re-pin it ever carried -- 25 of 85 across 1,311 captures -- sat on a
# {0x0047 stop -> 0x003D walk-start} pair: a leg's opening report on the
# previous stop at 0.000 u because the body had not moved YET, and it rewound
# a walking body p50 366.6 u (RUN-1zBL: three at 298-433 u).  Its founding
# specimen was that pair too, ~394 u downrange when it was called "parked".
# The branch left after 1z-bn and 1z-bs, {walk-start -> stop}, was followed
# by a still body in 151 of 151 windows and never once met a re-pin want; on
# every capture held, keeping it and deleting it were the same object.  So it
# went.  WHAT THAT COSTS: a maturing lead over a stale report is not
# pre-empted -- the arrival matures and the client's own test decides.
# RUN-1zBM measured that route lead-off (7 of 7 legs walked) and RUN-1zBO
# lead-on under the equivalent clause (0 of 7 rewound, separation 13.0 u).
# No revert flag: the code is gone, and a run wanting the old behaviour
# reads it off the captures of that era (their flags rows name the arm).

# Verdicts
PASS = "pass"                # predicted MATCH -- nothing can snap
PASS_GATES = "pass-gates"    # predicted miss, gates pass with margin
VETO = "veto"                # predicted snap (or inside the error margin)
NOT_READY = "not-ready"      # unseeded / fence closed / no q -- no opinion

REPIN_NONE = "none"          # no re-pin needed
REPIN_DUE = "due"            # needed and preconditions met
REPIN_BLOCKED = "blocked"    # needed but no fresh accepted report / rate


class GuardVerdict(object):
    __slots__ = ("code", "why", "predicted", "sep_budget", "repin")

    def __init__(self, code, why="", predicted=None, sep_budget=None,
                 repin=REPIN_NONE):
        self.code = code
        self.why = why
        self.predicted = predicted      # the underlying mirror Verdict
        self.sep_budget = sep_budget    # sep + staleness + skew, if computed
        self.repin = repin

    def __repr__(self):
        return "GuardVerdict(%s, %s, repin=%s)" % (self.code, self.why,
                                                   self.repin)


class AgTrackGuard(object):
    """Per-connection: one mirror plus the derived policy over it.

    Feed it what the server already knows (placement, accepted/refused
    reports, clicks, every emitted movement message, a periodic tick);
    ask it pre_emit() before a grant and repin_state() any time.
    """

    def __init__(self, mesh=None, prune_ms=3000):
        # prune_ms=3000: reader 2's corpus-adjudicated stand-in
        # (FINDINGS 1z-r.3 item 1 -- the value that empties the killing
        # cell in the current regime).
        #
        # TWO MIRRORS BRACKET REALITY (1z-r.3: invisible resets cut both
        # ways, and the server is only CERTAIN of the Clears IT caused).
        # `mirror` applies every predicted miss-snap's Clear -- the
        # all-resets world.  `twin` applies a Clear ONLY on our own 0x002C
        # -- the no-resets world.  The client's true reset history lies
        # between the two, so the policy takes the conservative join:
        # a grant is vetoed if EITHER world predicts its delivery snaps.
        self.mirror = am.AgTrackMirror(mesh=mesh, prune_ms=prune_ms)
        self.twin = am.AgTrackMirror(mesh=mesh, prune_ms=prune_ms)
        self.epoch = None            # server-time origin for the ms clock
        self.seeded = False          # HOLE D: placement must seed us
        self.client_pos = None       # last ACCEPTED report (x, y)
        self.client_plane = None
        self.client_pos_at = None    # server time of that accept
        self.pos_rejects = 0         # refusals since the last accept
        self.last_repin_at = None
        # The async copy's own destination, if a click is in flight.  The
        # client reports NOTHING while pathing a click (measured silences
        # to 37 s), so a raw last-report belief goes badly stale exactly
        # then; the estimate below glides it toward the click dest at the
        # granted speed -- the client's own glide model applied to the
        # async copy, straight-line (the client paths around obstacles;
        # this is an estimate and says so).  Cleared by any report (the
        # client speaking again ends the silent leg).
        #
        # NOT the same contract as authsrv's click-in-flight latch (corrected
        # 1z-bs): state["click_moving_at"] has a second armer, _approach_send
        # (ATTACK_APPROACH ships on), which walks the body on a silent leg
        # and never calls on_click.  With the stationary waiver deleted
        # (1z-bt) no GATE branches on whether a click is in flight any more
        # (that branch was the waiver's); the field still shifts the
        # estimate that every veto and re-pin decision reads through
        # _async_est.  Over an approach leg it stays None, the estimate sits
        # at the last report and the budget term widens with its age, which
        # errs toward the veto.  RECONSTRUCTION -- 9 approach grants in 3 of
        # 1,311 captures, unmeasured.
        self.async_dest = None
        # shadow counters
        self.n_pass = 0
        self.n_pass_gates = 0
        self.n_veto = 0
        self.n_not_ready = 0

    # ---- clock -----------------------------------------------------------

    def _ms(self, now):
        if self.epoch is None:
            self.epoch = now
        return int(round((now - self.epoch) * 1000.0))

    # ---- feeds (no sends, no server-state mutation) ----------------------

    def on_placement(self, x, y, plane, now):
        """Seed everything from character placement -- the one event that
        defines where both copies start.  HOLE D's startup assertion lives
        in the caller: a session that placed a character and never called
        this leaves the guard permanently NOT_READY and it says so."""
        ms = self._ms(now)
        self.mirror.sync.set_position(x, y, plane, ms)
        self.twin.sync.set_position(x, y, plane, ms)
        self.client_pos = (float(x), float(y))
        self.client_plane = plane
        self.client_pos_at = now
        self.seeded = True

    def on_report(self, x, y, plane, sig, now, accepted=True):
        """An 0x003D/0x0047 report as adjudicated by the trust filter.
        Only ACCEPTED reports advance the async belief (the refused-report
        hole: a refusal means the freshest thing heard was disbelieved, and
        re-pinning to the pre-jump point would be the warp the player
        described).  Both kinds re-arm the record (player input)."""
        ms = self._ms(now)
        if accepted:
            self.client_pos = (float(x), float(y))
            self.client_plane = plane
            self.client_pos_at = now
            self.pos_rejects = 0
        else:
            self.pos_rejects += 1
        self.async_dest = None       # the client spoke: the silent leg ended
        self.mirror.on_player_command(ms, (float(x), float(y)), plane, sig)
        self.twin.on_player_command(ms, (float(x), float(y)), plane, sig)

    def on_click(self, x, y, dest_plane, now):
        """A 0x003E: the async copy's own destination changes; the chain's
        seed becomes the click dest (the recorder's moving arm)."""
        ms = self._ms(now)
        pos = self._async_est(now)
        if pos is None:
            pos = (float(x), float(y))
        self.async_dest = (float(x), float(y))
        speed = RUN_SPEED * self.mirror.sync.move_speed
        d = math.hypot(float(x) - pos[0], float(y) - pos[1])
        arrive = ms + max(int(d * 1000.0 / speed), 1) if speed > 0 else 0
        for m in (self.mirror, self.twin):
            m.on_player_command(
                ms, pos, self.client_plane,
                ("click", round(float(x), 1), round(float(y), 1)),
                dest=(float(x), float(y), dest_plane), arrive_t=arrive)

    def on_emit(self, opcode, x, y, plane_first, plane_second, now):
        """A movement message actually sent (the send() choke point).
        Applies it to the mirror -- 0x0029/0x002A bake + dispatch,
        0x002C clear + set + append -- and in shadow mode this is where
        every grant's predicted verdict was already counted by
        pre_emit()."""
        ms = self._ms(now)
        if opcode in (0x29, 0x2A):
            v = self.mirror.on_grant(x, y, plane_first, plane_second,
                                     ms, async_pos=self._async_est(now),
                                     opcode=opcode)
            self.twin.on_grant(x, y, plane_first, plane_second,
                               ms, async_pos=self._async_est(now),
                               opcode=opcode, no_reset=True)
            return v
        if opcode == 0x2C:
            self.last_repin_at = now
            self.twin.on_update_position(x, y, plane_first, ms)
            return self.mirror.on_update_position(x, y, plane_first, ms)
        return None

    def on_speed(self, move_speed, now):
        self.mirror.on_speed(move_speed, self._ms(now))
        self.twin.on_speed(move_speed, self._ms(now))

    def tick(self, now):
        """Advance arrivals + the sweep + reader 2 on the server's own
        clock.  Returns an arrival's evaluation verdict if one fired --
        clause 2's trigger runs through arrival_risk() BEFORE the tick that
        would mature it."""
        self.twin.tick(self._ms(now), self._async_est(now), no_reset=True)
        return self.mirror.tick(self._ms(now), self._async_est(now))

    # ---- the derived policy ---------------------------------------------

    def _async_est(self, now):
        """The rendered copy's estimated position: the last accepted
        report, glided toward a click-in-flight destination at the granted
        speed and capped there.  Straight-line -- an estimate, and the
        budget term still widens every gate decision by the report age."""
        if self.client_pos is None:
            return None
        if self.async_dest is None or self.client_pos_at is None:
            return self.client_pos
        dt = max(now - self.client_pos_at, 0.0)
        speed = RUN_SPEED * self.mirror.sync.move_speed
        dx = self.async_dest[0] - self.client_pos[0]
        dy = self.async_dest[1] - self.client_pos[1]
        d = math.hypot(dx, dy)
        if d <= 0.0 or speed <= 0.0:
            return self.client_pos
        f = min(speed * dt / d, 1.0)
        return (self.client_pos[0] + f * dx, self.client_pos[1] + f * dy)

    def _budget(self, sep, now):
        """The separation budget: modeled sep + how far the client may have
        walked since its last accepted report + clock skew.  Conservative
        by construction -- every term is a ceiling."""
        if sep is None:
            return None
        age = 0.0 if self.client_pos_at is None \
            else max(now - self.client_pos_at, 0.0)
        return sep + RUN_SPEED * age + CLOCK_SKEW_U

    def _judge(self, v, now):
        """One world's predicted verdict -> (code, why, budget)."""
        if v.code == am.NOT_TESTED:
            # In THAT world the fence is closed, so the grant appends and
            # no test runs -- safe there by the decode.  (The twin's fence
            # closes only on our own 0x002C, so a twin NOT_TESTED is the
            # certain case.)
            return PASS, "fence-closed (appends)", None
        if v.code == am.MATCH:
            return PASS, "match", None
        budget = self._budget(v.gate1_sep, now)
        if v.code == am.SNAP:
            return (VETO, "gate1-red" if v.gate1 is False
                    else "gate2-offmesh", budget)
        if budget is not None and budget >= GATE1_RED:
            return VETO, "budget-red", budget
        return PASS_GATES, "gates-pass", budget

    _SEVERITY = {PASS: 0, PASS_GATES: 1, VETO: 2}

    def pre_emit(self, x, y, plane_first, plane_second, now):
        """Clause 1's check: predict this grant's delivery evaluation in
        BOTH worlds and take the conservative join.  PASS = predicted MATCH
        (or a certainly-closed fence).  PASS_GATES = miss but the whole
        error budget stays under the red line.  VETO = either world
        predicts a snap, or a gates-pass whose budget crosses the red line
        (the model could be under-reading).  Counts itself for the shadow
        telemetry."""
        if not self.seeded:
            self.n_not_ready += 1
            return GuardVerdict(NOT_READY, "unseeded (HOLE D)")
        worst = None
        for m in (self.mirror, self.twin):
            v = m.predict_grant(x, y, plane_first, plane_second,
                                self._ms(now), self._async_est(now))
            code, why, budget = self._judge(v, now)
            if worst is None or (self._SEVERITY[code]
                                 > self._SEVERITY[worst[0]]):
                worst = (code, why, v, budget)
        code, why, v, budget = worst
        if code == VETO:
            self.n_veto += 1
            return GuardVerdict(VETO, why, v, budget,
                                repin=self._repin_code(now))
        if code == PASS_GATES:
            self.n_pass_gates += 1
        else:
            self.n_pass += 1
        return GuardVerdict(code, why, v, budget)

    def arrival_risk(self, now, horizon=0.5):
        """Clause 2: is a sync arrival maturing within `horizon` seconds
        whose evaluation at q = the destination predicts a snap in either
        world?  The server calls this from its periodic tick and re-pins
        before the arrival if so.  Returns (risky, verdict_or_None)."""
        s = self.mirror.sync           # both worlds share the sync sim
        if not self.seeded or s.t_arrive == 0 or s.dest is None:
            return False, None
        due_ms = s.t_arrive
        now_ms = self._ms(now)
        if due_ms - now_ms > horizon * 1000.0:
            return False, None
        for m in (self.mirror, self.twin):
            v = m.predict(due_ms, self._async_est(now),
                          q=(s.dest[0], s.dest[1]),
                          qplane=s.dest[2] if len(s.dest) > 2 else s.plane)
            if v.code == am.SNAP:
                return True, v
        return False, None

    def _repin_block(self, now):
        """WHICH precondition refuses a re-pin right now, or None.

        Named rather than boolean because 1z-ag had to replay a capture to
        find out: the row said `blocked` and nothing else, and two wrong
        explanations reached a merged document before the capture was asked
        directly (1z-ah).  A guard nobody can see not-firing is a wish."""
        if self.client_pos is None or self.client_pos_at is None:
            return "no-report"
        if self.pos_rejects > 0:
            return "rejects"
        if now - self.client_pos_at > REPIN_MAX_REPORT_AGE:
            return "stale-report"
        if (self.last_repin_at is not None
                and now - self.last_repin_at < REPIN_MIN_INTERVAL):
            return "rate"
        return None

    def repin_block_reason(self, now):
        """The block reason for the telemetry row: a name, or None when
        nothing is blocking.  Public -- authsrv writes it beside the code."""
        if not self.seeded:
            return "unseeded"
        return self._repin_block(now)

    def _repin_code(self, now):
        """The re-pin's preconditions, re-derived (see the constants):
        a fresh ACCEPTED report, nothing refused since, and the rate.  The
        stationary waiver that once sat between the first two is deleted
        (MOVECODE-1z-bt, PLAN sec.7 Q15)."""
        return REPIN_BLOCKED if self._repin_block(now) else REPIN_DUE

    def repin_state(self, now):
        """Standing answer to "should the server re-pin right now?" --
        clause 1's replace arm and clause 2's proactive arm share it.
        Returns (code, why): REPIN_DUE with the reason, REPIN_BLOCKED with
        what blocks it, or REPIN_NONE."""
        if not self.seeded:
            return REPIN_NONE, "unseeded"
        risky, _v = self.arrival_risk(now)
        if risky:
            return self._repin_code(now), "arrival-risk"
        last_code = None
        for m in (self.mirror, self.twin):
            v = m.predict(self._ms(now), self._async_est(now))
            code, why, _budget = self._judge(v, now)
            if code == VETO:
                return self._repin_code(now), why
            last_code = v.code if last_code is None else last_code
        return REPIN_NONE, last_code

    # ---- telemetry -------------------------------------------------------

    def snapshot(self):
        m = self.mirror
        return {"seeded": self.seeded,
                "fence_open": m.client_controlled,
                "chain": m.chain_len,
                "pass": self.n_pass, "pass_gates": self.n_pass_gates,
                "veto": self.n_veto, "not_ready": self.n_not_ready,
                "pushes": m.n_push, "clears": m.n_clear}
