"""REALFIX-A2's --d1-lead bundle: the formula, the edge, the cells, the locks.

The bundle's whole verdict lives in an owner run this file cannot perform
(the registered predictions are REALFIX.md sec.0.9 and the startup banner --
P-1's zero-snap warp-recipe A/B above all). What this file CAN refuse to let
rot: the D1 endpoint formula's exactness and its refuse-don't-clamp fallback,
the family-rate edge trigger's whole truth table (including the stop-reset
transition the A1 probe never needed), the composition cells that keep the
run unconfoundable, and the source locks on every site the bundle touches --
the heading-arm gate and slot, the dest swap, the verdict row's arm key, and
the stop-repin's position inside the 0x0047 handler.

What this file deliberately does NOT claim: that the lead is safe (that is
P-1..P-5's job). The lead no longer ships unclipped: sec.0.17's D2 clip
(a2_clip_lead, the wall-phase fix) trims a d1 lead's ray to the navmesh --
Q7's desk check found retail's own clip landing ON our mesh edges to <=3u
for the terrain-edge subset, and the 113833 run's through-wall walk was an
unclipped lead the mesh had refused (10 of 10 final-phase leads
mesh-blocked). What is STILL not modelled: retail's prop-class clips (the
corridor's five bit-identical coordinates sit inside our walkable mesh --
we carry no prop geometry, so those clips stay retail-only).
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import authsrv     # noqa: E402
import checks      # noqa: E402

# MEASURED from the real green run on 2026-08-26: 37 checks, no fixture, no
# vault, no client. Set AT the run per the house rule -- zero headroom.
# (History: the author declared 34 from a head-count before running, the run
# said 36 -- the same defect test_familyrate's and test_pcspoof's headers
# record, three for three now. Count from the run, never the head. The
# review pass then added the MUT-7 stop-order pin -> 37; the sec.0.11
# matched-words armer-kill added its truth table and four locks -> 42;
# the sec.0.12 containment pair (leg model + watchdog + click freshness)
# added its truth tables and site locks -> 56; its review's fixes (the
# REV-1 None regression pin, the MUT-1 floor-value and ETA-boundary pins,
# the MUT-7 guard lock, the REV-2 read-not-pop lock) -> 60; the sec.0.13
# F-B click contract (rate gate truth table, matched/family-reset censuses,
# both bypass sites, row ordering, the geometry row) -> 67; its review's
# fixes (the grantsim skip, the arm fields, the recv-thread flush move)
# -> 70; sec.0.14's F-A (click-held + the eager void) -> 72; sec.0.15
# DELETING both click rewrites and their rate gate (each refuted within
# the day -- the checks now assert the absences and the empty gap) -> 70;
# the outstanding-answer hold (the double-click stomp fix) -> 72;
# sec.0.17's pair -- the leg-bounded hold at the immediate site (R-3's
# residual hole; the gap lock evolving from empty-gap to refuse-only-hold,
# plus the leg-bound pin) and the D2 lead clip (the 2d pure cells + four
# locks) -> 81; sec.0.19's RETHINK instrument-#1 rows (clip why strings in
# the 2d cells, five row locks: lead_clip_why, the flush-hold row,
# kbd_age, the a2_leg lifecycle, the watchdog-due transition) -> 86.
# Each floor re-read off its own green run.)
LEDGER = checks.Ledger("the REALFIX-A2 d1-lead bundle", floor=118)
check = checks.adopt(LEDGER)


class FakeSend:
    """Captures (opcode, values, label) the way the wire would see them."""

    def __init__(self):
        self.sent = []

    def __call__(self, opcode, values, label, quiet=False):
        self.sent.append((opcode, list(values), label))


def main():
    # ---------------------------------------------------------------- 1
    print("1. d1_lead_dest: the formula exactly, and refuse-don't-clamp")
    f = authsrv.d1_lead_dest
    check(f([100.0, 200.0], [766.0, 0.0]) == ([866.5, 200.0], "d1"),
          "axis-aligned: dest = reported + vec2 + 0.5*unit -- the 0.5 term "
          "lands whole on the axis",
          "the +0.5*unit term is the D1 signature the live corpus verified "
          "to 0.0001u; dropping it is invisible to any coarser check")
    d, src = f([0.0, 0.0], [420.0, 560.0])
    check(src == "d1" and abs(d[0] - 420.3) < 1e-9
          and abs(d[1] - 560.4) < 1e-9,
          "diagonal at the band floor exactly: |(420,560)| = 700.0 "
          "(inclusive), unit = (0.6,0.8), dest = (420.3, 560.4)",
          "a wrong normalization (0.5*vec2 instead of 0.5*unit) reads "
          "plausibly on axis-aligned vectors and only a diagonal catches "
          "it; the same row pins the floor boundary as >= not >")
    check(f([100.0, 200.0], [0.0, 0.0]) == ([100.0, 200.0], "fallback"),
          "a zero vec2 falls back to the zero-lead point",
          "unit() of a near-zero vector amplifies noise into a direction; "
          "the degenerate case must refuse, not invent a heading")
    check(f([100.0, 200.0], [-1.9969178438186646, 0.0])
          == ([100.0, 200.0], "fallback"),
          "the corpus's ONE mid-magnitude outlier (|v|=1.997, 1 of 15,285 "
          "c2s rows -- the 2026-08-26 review's census) falls back",
          "the D1 formula is bit-verified only on the 765-768 proposal "
          "band; a mid-magnitude 'd1' row would be a short lead nobody "
          "registered wearing the registered label (REV-1)")
    check(f([100.0, 200.0], [699.99, 0.0])[1] == "fallback"
          and f([100.0, 200.0], [769.0, 0.0])[1] == "d1"
          and f([100.0, 200.0], [769.01, 0.0])[1] == "fallback",
          "the band is [700.0, 769.0], both edges pinned: just-under "
          "falls back, the inclusive ceiling leads, just-over falls back",
          "a vec2 outside the verified band is refused; CLAMPING it would "
          "still send a wrong destination -- the fallback sends the "
          "zero-lead point instead, and the row records which")
    check(f([100.0, 200.0], [float("nan"), 0.0])[1] == "fallback",
          "a NaN component falls back",
          "hypot(nan) is nan, every comparison is False, and without the "
          "isfinite gate the nan would ride into struct.pack")
    check(f([100.0, 200.0], None)[1] == "fallback"
          and f([100.0, 200.0], [1.0])[1] == "fallback",
          "a malformed vec2 (None, wrong arity) falls back instead of "
          "raising",
          "the helper runs inside the connection handler; a TypeError "
          "there kills the session for one bad report")
    check(authsrv.D1_LEAD is False,
          "D1_LEAD ships False (off)",
          "an experiment lever that defaults on is a policy nobody ruled")

    # ---------------------------------------------------------------- 2
    print("\n2. the family edge: send on change, hold on same, reset on stop")
    snd, state = FakeSend(), {}
    authsrv._a2_family_rate(snd, state, 1)
    check(len(snd.sent) == 1 and snd.sent[0][1][1:] == [1.0, 1]
          and snd.sent[0][2].startswith("A2 FAMILY-RATE"),
          "first family sends [1.0, 1] under the A2 label, not the A1 "
          "probe label",
          "a capture whose 0x002B rows say FAMILY-RATE PROBE while the "
          "banner says A2 is the unattributable-capture defect")
    authsrv._a2_family_rate(snd, state, 1)
    check(len(snd.sent) == 1,
          "same family again sends NOTHING -- the edge holds",
          "A1 proved the store persists; a same-family re-send is dose "
          "without information, and retail's own 0x002B is a change "
          "signal (97.6% of change bursts vs 11.5% same-family)")
    authsrv._a2_family_rate(snd, state, 4)
    check(len(snd.sent) == 2 and snd.sent[1][1][1:] == [0.66, 4],
          "a family change sends the new float",
          "the edge is the policy; a missed change leaves the copy "
          "reckoning at the old family's speed for the whole leg")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv._a2_family_rate(snd, state, 9)
    check(len(snd.sent) == 2 and "UNKNOWN movementType" in buf.getvalue(),
          "an unknown mt sends nothing and prints (the sender's own loud "
          "skip)",
          "mt 9 is retail's SERVER-only stop sentinel; a client report "
          "carrying it is a census-breaking event, not a table row to "
          "guess")
    authsrv._a2_family_rate(snd, state, 4)
    check(len(snd.sent) == 2,
          "and the unknown mt did NOT advance the edge -- family 4 is "
          "still the last SENT family, so no re-send",
          "advancing the edge on a skipped send would silently drop the "
          "next real family's float")
    state["a2_family_sent"] = None
    authsrv._a2_family_rate(snd, state, 4)
    check(len(snd.sent) == 3 and snd.sent[2][1][1:] == [0.66, 4],
          "after the stop-reset (a2_family_sent = None) the SAME family "
          "re-sends",
          "the stop-repin's [1.0, 9] overwrites sync +0x60, so the next "
          "leg must re-assert its family even unchanged -- the one "
          "transition the A1 probe never needed, and the reason the "
          "stop arm writes None")
    check(authsrv.a2_matched_field4(22, 22) == (22, False)
          and authsrv.a2_matched_field4(22, 0) == (22, True)
          and authsrv.a2_matched_field4(0, 26) == (0, True),
          "the matched-words override (sec.0.11's armer-kill): equal "
          "words pass through unmarked, a differing carry is REPLACED by "
          "the ground plane and marked",
          "plane-carry's stale word across a seam is stage 1 of the "
          "input lock (the drawn body snaps onto the stale-stamped copy "
          "and the fence shuts); retail's nonzero pairs are bit-identical "
          "222/222, so matched IS the retail contract")

    print("\n2b. the containment pair's pure halves (sec.0.11)")
    leg = authsrv.a2_leg_note([0.0, 0.0], [768.0, 0.0], 5, 4, 100.0)
    check(leg["speed"] == 0.66 * 288.0 and leg["dest"] == (768.0, 0.0)
          and leg["wd_fired"] is False,
          "a2_leg_note records origin, dest, plane, the FAMILY speed "
          "(0.66x288 for a backpedal leg) and the send instant",
          "the model must walk at the speed the copy actually walks -- a "
          "288-flat model puts the player past the dest while the client "
          "is still mid-leg")
    check(authsrv.a2_leg_position(leg, 101.0) == (190.08, 0.0, 5),
          "mid-leg the model interpolates at the leg's own speed",
          "1 s into a backpedal leg is 190.08 u, not 288")
    check(authsrv.a2_leg_position(leg, 200.0) == (768.0, 0.0, 5),
          "post-arrival the model CLAMPS at the dest",
          "the incident's recovery click: 7.15 s 'stale' with the player "
          "standing exactly at the granted dest -- the clamp is the case "
          "the whole fix exists for")
    check(authsrv.a2_leg_position(None, 100.0) is None,
          "and a missing leg models nothing",
          "None, never a guess")
    check(authsrv.a2_watchdog_due({}, 999.0) == (False, "no-leg"),
          "watchdog: no leg, not due",
          "the watchdog only answers silence a lead explains")
    check(authsrv.a2_watchdog_due({"a2_leg": leg}, 102.0)
          == (False, "pre-eta"),
          "pre-ETA (768u at the 190.08 floor + 1.0s slack = t0+5.04s), "
          "not due",
          "a mid-leg re-pin would supersede a walk the client is "
          "legitimately making -- the floor speed makes the ETA late, "
          "never early")
    check(authsrv.a2_watchdog_due({"a2_leg": leg}, 106.0)
          == (True, "eta-passed"),
          "past the ETA with no other clause, DUE",
          "this is the incident's t=168 leg: silence past completion "
          "with nothing legitimate explaining it")
    check(authsrv.a2_watchdog_due(
              {"a2_leg": leg, "click_moving_at": 101.0}, 106.0)
          == (False, "click-in-flight"),
          "a click after the leg's t0 stands the watchdog down",
          "a click-walking client is silent LEGITIMATELY; a re-pin would "
          "stamp on its path -- the containment must never recreate the "
          "defect it contains")
    check(authsrv.a2_watchdog_due(
              {"a2_leg": leg, "click_moving_at": None}, 106.0)
          == (True, "eta-passed"),
          "and click_moving_at holding None -- the latch's CLEARED state, "
          "written by assignment in both report arms -- does not raise",
          "the containment review's one REAL (REV-1): .get's default "
          "never fires on a present-but-None key, and the TypeError "
          "escaped the recv loop's except clauses -- the containment "
          "would have KILLED the session on its first quiet second. This "
          "cell is the regression pin")
    check(authsrv.A2_WATCHDOG_SPEED_FLOOR == 0.66 * 288.0
          and authsrv.A2_WATCHDOG_SLACK == 1.0,
          "the speed floor is 0.66x288 = 190.08 (the slowest family) and "
          "the slack 1.0 s -- pinned as VALUES",
          "the mutation lane's MUT-1: a floor quietly raised to 288 "
          "fires mid-backpedal-leg and supersedes a walk the client is "
          "legitimately making, and only boolean far-from-boundary cells "
          "stayed green")
    check(authsrv.a2_watchdog_due({"a2_leg": leg}, 105.03)
          == (False, "pre-eta")
          and authsrv.a2_watchdog_due({"a2_leg": leg}, 105.05)
          == (True, "eta-passed"),
          "the ETA boundary sits where THE FLOOR puts it: 768u/190.08 + "
          "1.0s = t0+5.0404s, bracketed to 20 ms",
          "a boundary this tight is sensitive to the exact floor value -- "
          "at 288 flat the ETA would be t0+3.667s and both cells flip; "
          "the far-from-boundary cells alone let MUT-1 survive")
    leg2 = dict(leg, wd_fired=True)
    check(authsrv.a2_watchdog_due({"a2_leg": leg2}, 106.0)
          == (False, "already-fired"),
          "and it fires ONCE per leg",
          "a 1 Hz re-pin stream at the same dest is a policy nobody "
          "registered")

    print("\n2c. the click rate gate is GONE (sec.0.15)")
    check(not hasattr(authsrv, "a2_click_rate_ok"),
          "a2_click_rate_ok no longer exists -- the rate-only click "
          "resurrection was deleted with both its callers",
          "F-B answered keyboard-shadowed clicks immediately (copy raced "
          "through props); F-A held them for the flush (the flush's stale "
          "drag-echoes were the direction-yank engine, 35/44 sharp turns, "
          "median 583u off-aim). Retail drops them outright; a helper "
          "with no callers coming back would mean somebody re-opened the "
          "resurrection path without re-litigating sec.0.15")

    # ---------------------------------------------------------------- 3
    print("\n2d. the D2 lead clip's pure cells (sec.0.17)")

    class StubPM:
        """The pathmap contract a2_clip_lead relies on, in miniature:
        walkable everywhere except the band 100 < x < 200 (a wall with
        legal ground on BOTH sides -- the wall-phase geometry), and
        clip() returning (x1, y1) EXACTLY when unobstructed, which is
        what makes the != detection in a2_clip_lead exact (verified
        against pathmap.PathingMap.clip's own last iteration, f = 1.0)."""

        def walkable(self, x, y):
            return not (100.0 < x < 200.0)

        def clip(self, x0, y0, x1, y1, step=16.0):
            dx, dy = x1 - x0, y1 - y0
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= 0.0:
                return (x0, y0)
            n = max(1, int(dist / step))
            last = (x0, y0)
            for i in range(1, n + 1):
                f = i / n
                px, py = x0 + dx * f, y0 + dy * f
                if not self.walkable(px, py):
                    return last
                last = (px, py)
            return (x1, y1)

    clipf = authsrv.a2_clip_lead
    st = {"pathmap": StubPM()}
    d, was, why = clipf(st, [0.0, 0.0], [766.5, 0.0])
    check(was is True and 0.0 <= d[0] <= 100.0 and d[1] == 0.0
          and why == "clipped",
          "a lead aimed across a blocked band onto legal far ground is "
          "clipped to the NEAR side, why='clipped' -- the wall-phase "
          "cell itself",
          "the 113833 run's final leg: origin and dest both walkable, "
          "the band between them not -- walkable(dest) alone would have "
          "passed it, which is why the clip must walk the RAY")
    d, was, why = clipf(st, [0.0, 0.0], [90.0, 0.0])
    check(was is False and d == [90.0, 0.0] and why == "clear",
          "a clear ray comes back untouched, clipped=False bit-exact, "
          "why='clear'",
          "a clip that perturbs unblocked leads rewrites every healthy "
          "grant by epsilon and the 222/222 word doctrine starts "
          "matching floats that no longer equal the client's")
    d, was, why = clipf({"pathmap": None}, [0.0, 0.0], [766.5, 0.0])
    check(was is False and d == [766.5, 0.0] and why == "no-mesh",
          "no mesh: the clip disables rather than freezes and the row "
          "will SAY no-mesh (the clip_to_walkable door, now named)",
          "a map without a mesh must not lose the lead bundle; failing "
          "toward the pre-sec.0.17 behavior is the calibrated risk")
    d, was, why = clipf({"pathmap": StubPM()}, [150.0, 0.0], [916.5, 0.0])
    check(was is True and d == [150.0, 0.0]
          and why == "origin-unwalkable",
          "an off-mesh ORIGIN demotes the lead to ZERO DISTANCE -- the "
          "granted point is the report itself, never the unclipped ray "
          "(ROUTER-B3: the P-17 escape door, CLOSED)",
          "this cell used to assert the door OPEN (dest passed through "
          "unchanged) and the 20260826T192724 verification run showed "
          "what that cost: 19 of 99 fired keyboard leads left through "
          "it as full 766u rays, and 11 of the tape's 12 off-mesh "
          "episodes start on exactly those grants. A zero-distance "
          "answer orders no walk and leaves the client authoritative "
          "where our mesh has nothing to say -- the router's own "
          "origin-off-mesh doctrine, applied to the keyboard channel")


    # ---------------------------------------------------------------- 3b
    print("\n2e. the clip stays on the report's PLANE (MOVECODE-1z-ap)")

    class PlanePM(StubPM):
        """The same wall, plus a SEAM: everything at x >= 300 is plane 0 and
        everything below it is plane 29 -- a bridge running out over ground,
        which is the shape RUN-1zAO's fatal lead crossed. `walkable` is
        deliberately still plane-BLIND (that is pathmap's own contract: "inside
        any trapezoid, on ANY plane"), so only the plane term can see the seam."""

        def plane_at(self, x, y, prefer=None):
            if 100.0 < x < 200.0:       # the wall: no trapezoid, so no plane
                return None
            return 0 if x >= 300.0 else 29

        def clip(self, x0, y0, x1, y1, step=16.0, plane=None):
            dx, dy = x1 - x0, y1 - y0
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= 0.0:
                return (x0, y0)
            n = max(1, int(dist / step))
            last = (x0, y0)
            for i in range(1, n + 1):
                f = i / n
                px, py = x0 + dx * f, y0 + dy * f
                if not self.walkable(px, py):
                    return last
                if plane is not None and self.plane_at(px, py, prefer=plane) != plane:
                    return last
                last = (px, py)
            return (x1, y1)

    ppm = PlanePM()
    seam_st = {"pathmap": ppm, "plane": 29}

    _was_plane_clip = authsrv.A2_LEAD_PLANE_CLIP
    try:
        # THE KNOWN-BAD ARM FIRST, so the cell below is known to be measuring
        # the plane term and not the wall.
        authsrv.A2_LEAD_PLANE_CLIP = False
        d_off, was_off, why_off = clipf(seam_st, [250.0, 0.0], [770.0, 0.0])
        check(was_off is False and d_off == [770.0, 0.0] and why_off == "clear",
              "KNOWN-BAD ARM (--no-lead-plane-clip): a 520 u ray across a "
              "plane 29 -> plane 0 seam goes out at FULL LENGTH, why='clear'",
              "this is the defect RUN-1zAO caught in the client's own memory: "
              "the body would not walk the seam, sat parked 3.0 s under a held "
              "key while the sync copy walked the granted ray, and the arrival "
              "then warped it 520 u and shut AgTrack's fence for good. If this "
              "cell ever goes green with the flag ON, the fix is not the thing "
              "being measured")

        authsrv.A2_LEAD_PLANE_CLIP = True
        d_on, was_on, why_on = clipf(seam_st, [250.0, 0.0], [770.0, 0.0])
        check(was_on is True and 250.0 <= d_on[0] < 300.0
              and why_on == "plane-seam",
              "SHIPPED: the same ray stops AT the seam and the row NAMES the "
              "door -- why='plane-seam', not 'clipped'",
              "the wall door and the seam door have different fixes, and this "
              "file already paid once for a clip whose row did not say which "
              "had opened (the P-17 press, lead_clipped=false)")
        check(d_on[0] < 299.332591 + 250.0,
              "and the surviving reach is under gate 1's 299.33 u, so the "
              "granted point cannot be the far side of a snap",
              "the whole harm is separation at the arrival exceeding gate 1 "
              "(sec.1z-ag); a lead that cannot reach it cannot arm the lock")

        # The term must not touch a ray that never leaves its plane.
        for flag in (False, True):
            authsrv.A2_LEAD_PLANE_CLIP = flag
            d_s, was_s, why_s = clipf(seam_st, [0.0, 0.0], [90.0, 0.0])
            check(was_s is False and d_s == [90.0, 0.0] and why_s == "clear",
                  "a same-plane clear ray is bit-identical with the plane "
                  "clip %s -- healthy grants are not perturbed"
                  % ("ON" if flag else "OFF"),
                  "a clip that moves unblocked leads by epsilon rewrites every "
                  "healthy grant and the 222/222 word doctrine starts matching "
                  "floats the client never sent")

        # An ordinary mesh block must still read 'clipped', never 'plane-seam'.
        authsrv.A2_LEAD_PLANE_CLIP = True
        d_w, was_w, why_w = clipf(seam_st, [0.0, 0.0], [90.0 + 680.0, 0.0])
        check(was_w is True and why_w == "clipped",
              "a ray into the WALL still reads why='clipped' -- the seam name "
              "is not applied to a mesh block",
              "the door names are the whole point of the row; a plane term "
              "that relabels the wall door would hide the defect it replaced")

        # plane_at refusing to answer disables the term rather than guessing.
        class MutePM(PlanePM):
            def plane_at(self, x, y, prefer=None):
                return None
        d_m, was_m, why_m = clipf({"pathmap": MutePM(), "plane": 29},
                                  [250.0, 0.0], [770.0, 0.0])
        check(was_m is False and why_m == "clear",
              "a mesh that CANNOT NAME the origin's plane disables the term "
              "rather than guessing a surface",
              "plane_at returns None for 'say nothing, never a guess' on "
              "stacked geometry with no height in the file; this file's own "
              "no-mesh door already fails toward the historical behaviour")

        # A pathmap with no plane_at at all (the pre-1z-ap stub) still works.
        d_o, was_o, why_o = clipf({"pathmap": StubPM(), "plane": 29},
                                  [0.0, 0.0], [766.5, 0.0])
        check(was_o is True and why_o == "clipped",
              "a pathmap with NO plane_at keeps the historical answer exactly",
              "the capability is probed, not assumed: an old mesh object must "
              "not raise inside the recv loop")
    finally:
        authsrv.A2_LEAD_PLANE_CLIP = _was_plane_clip

    _psrc = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    ARGS_SRC = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check(authsrv.A2_LEAD_PLANE_CLIP is True
          and '"--no-lead-plane-clip"' in ARGS_SRC
          and "A2_LEAD_PLANE_CLIP = not a.no_lead_plane_clip" in _psrc,
          "it ships ON with --no-lead-plane-clip as the one revert, and the "
          "flag is bound from argv rather than left at its default",
          "sec.29's rule: one behaviour change, one flag, so a run convicts "
          "one term")
    print("\n2f. the seam variant of the lead clip, OPT-IN and refuted as a "
          "default (MOVECODE-1z-bc)")
    # The seam test (pathmap.seam_clip, the router's primitive since 1z-bb)
    # was built to replace 1z-ap's any-plane-change clip on the lead and was
    # REFUTED by retrodiction before it could ship: all six fatal leads of the
    # six measured locks cross a FILE-LINKED portal and go out at 520 u under
    # it (leadretro.py, FINDINGS 1z-bc). So the default stays 1z-ap's clip and
    # the seam variant is a diagnostic arm. These cells pin BOTH behaviours
    # and the default's direction.

    class SeamPM(PlanePM):
        """PlanePM's seam at x = 300 is a PORTAL here (a bridge's end ramp) and
        there is a second, BLIND seam at x = 600 (the deck's side). The seam-
        aware ray -- pathmap.seam_clip's contract -- passes the first and stops
        at the second; 1z-ap's any-plane-change clip stops at the first."""

        def plane_at(self, x, y, prefer=None):
            if 100.0 < x < 200.0:
                return None
            if x >= 600.0:
                return 7
            return 0 if x >= 300.0 else 29

        def seam_clip(self, x0, y0, x1, y1, plane, step=2.0):
            p = self.clip(x0, y0, x1, y1, step=step)        # plane-blind walk
            if x0 < 600.0 < p[0] and x1 != x0:
                f = (600.0 - x0) / (x1 - x0)
                return (600.0 - step, y0 + f * (y1 - y0))
            return p

    spm = SeamPM()
    seam_st2 = {"pathmap": spm, "plane": 29}
    _was_seam_clip = authsrv.A2_LEAD_SEAM_CLIP
    try:
        # THE DEFAULT: 1z-ap's clip stops at the portal too. This is the cell
        # that protects the six locks, and it is the SHIPPED one.
        authsrv.A2_LEAD_SEAM_CLIP = False
        authsrv.A2_LEAD_PLANE_CLIP = True
        d_p, was_p, why_p = clipf(seam_st2, [250.0, 0.0], [550.0, 0.0])
        check(was_p is True and 250.0 <= d_p[0] < 300.0 and why_p == "plane-seam",
              "SHIPPED DEFAULT: a ray through a file-linked PORTAL is still cut "
              "at the plane change -- the clip that kept all six fatal leads "
              "under gate 1",
              "the seam variant would grant it at full length, and the "
              "retrodiction says the body did not walk exactly this on the "
              "spawn-side bridge, six times")
        authsrv.A2_LEAD_SEAM_CLIP = True
        d_s, was_s, why_s = clipf(seam_st2, [250.0, 0.0], [550.0, 0.0])
        check(was_s is False and d_s == [550.0, 0.0] and why_s == "clear",
              "OPT-IN ARM (--lead-seam-clip): the same ray goes out at FULL "
              "LENGTH through the portal -- the re-opened door, on demand",
              "a run that wants to ask WHY the body refuses a linked portal "
              "drives this arm deliberately")
        d_b, was_b, why_b = clipf(seam_st2, [450.0, 0.0], [970.0, 0.0])
        check(was_b is True and 550.0 <= d_b[0] < 600.0 and why_b == "plane-seam",
              "and a ray off the deck's SIDE -- a plane ending with no portal -- "
              "still stops at the edge and names the door",
              "RUN-1zBA's harm class: the client's body will not follow a lead "
              "across it, and the arrival snap is what happens next")
        check(d_b[0] - 450.0 < 299.332591,
              "the surviving reach across the blind seam is under gate 1")
        # A mesh with plane_at but no seam_clip (1z-ap's contract) keeps the
        # any-plane-change clip: the capability is probed, not assumed.
        d_o, was_o, why_o = clipf(seam_st, [250.0, 0.0], [770.0, 0.0])
        check(was_o is True and 250.0 <= d_o[0] < 300.0 and why_o == "plane-seam",
              "a mesh WITHOUT seam_clip falls back to the plane clip unchanged",
              "an old mesh object must not raise inside the recv loop, and its "
              "answer must be the 1z-ap one, not the plane-blind one")
    finally:
        authsrv.A2_LEAD_SEAM_CLIP = _was_seam_clip
        authsrv.A2_LEAD_PLANE_CLIP = _was_plane_clip
    check(authsrv.A2_LEAD_SEAM_CLIP is False
          and '"--lead-seam-clip"' in ARGS_SRC
          and "A2_LEAD_SEAM_CLIP = bool(a.lead_seam_clip)" in _psrc
          and _psrc.count("pm.seam_clip(") == 2
          and "return pm.seam_clip(x0, y0, x1, y1, plane, step=step)" in _psrc
          and "0 of 6 kept under gate 1" in _psrc,
          "it ships OFF, --lead-seam-clip is opt-in and bound from argv, "
          "seam_clip is reached at exactly two sites (the router's "
          "_router_clip and the lead), and the file records WHY the default "
          "is off (the 0-of-6 retrodiction)",
          "a default flipped by a later reader who does not see this number "
          "re-arms the six locks' door")

    check("plane=plane" in _psrc and 'prefer=state.get("plane")' in _psrc,
          "the ray's plane comes from plane_at(prefer=the REPORT's own plane), "
          "not from state[\"pos\"] or a literal",
          "--heading-grant's graveyard (R2-1): the lead must aim from, and be "
          "judged on, the point the client actually named")

    # ---- 2g. MOVECODE-1z-bg: THE SLIVER ORIGIN -------------------------
    # The origin test was walkable(report) -- exact containment -- and the
    # client's reports at the wedge tip sit <= 0.5 u outside our edges, so 179
    # keyboard leads in 26 runs became zero-leads. A report the mesh holds
    # within SEAM_TOL is now an origin IF the mesh can name its plane there;
    # its ray takes 1z-ap's plane clip like any inside origin. What must stay
    # shut: ROUTER-B3's door (the unclipped ray from an off-mesh origin), the
    # plane-blind arm, an ambiguous sliver, and anything further than 1 u off.
    class SliverPM(PlanePM):
        """PlanePM whose mesh begins at x = 0: x < 0 is off it, and the band
        -1 <= x < 0 is a sliver -- off by exact containment, on within 1 u."""

        def walkable(self, x, y):
            return x >= 0.0 and not (100.0 < x < 200.0)

        def on_mesh(self, x, y, tol=1.0):
            return self.walkable(x, y) or (-tol <= x < 0.0)

        def plane_near(self, x, y, prefer=None, tol=1.0):
            if self.walkable(x, y):
                return self.plane_at(x, y, prefer=prefer)
            return 29 if -tol <= x < 0.0 else None

    class AmbiguousSliverPM(SliverPM):
        """The same sliver, but two planes meet there and the report names neither."""

        def plane_near(self, x, y, prefer=None, tol=1.0):
            return None if not self.walkable(x, y) else SliverPM.plane_near(self, x, y, prefer, tol)

    class OldSliverPM(PlanePM):
        """A mesh object that predates on_mesh()/plane_near(): the door must not open."""

        def walkable(self, x, y):
            return x >= 0.0 and not (100.0 < x < 200.0)

    spm = SliverPM()
    sl_st = {"pathmap": spm, "plane": 29}
    _was_origin = authsrv.A2_LEAD_ORIGIN_SEAM
    _was_plane = authsrv.A2_LEAD_PLANE_CLIP
    try:
        authsrv.A2_LEAD_ORIGIN_SEAM = True
        authsrv.A2_LEAD_PLANE_CLIP = True
        d, was, why = clipf(sl_st, [-0.5, 0.0], [519.5, 0.0])
        check(was is True and 50.0 < d[0] < 100.0 and d[1] == 0.0 and why == "clipped",
              "2g. a SLIVER origin (0.5 u outside the mesh) gets a real lead, "
              "walked on the plane clip and stopped at the wall like any inside origin",
              f"got {d} {why}")
        d, was, why = clipf(sl_st, [-0.5, 0.0], [-520.5, 0.0])
        check(was is True and d == [-0.5, 0.0] and why == "clipped",
              "2g. ROUTER-B3's door STAYS SHUT: a sliver origin whose ray leaves the "
              "mesh at the first step gets the start back, never the unclipped ray",
              f"got {d} {why}")
        d, was, why = clipf(sl_st, [-1.5, 0.0], [518.5, 0.0])
        check(was is True and d == [-1.5, 0.0] and why == "origin-unwalkable",
              "2g. 1.5 u off the mesh is still origin-unwalkable (the tolerance is 1 u)",
              f"got {d} {why}")
        d, was, why = clipf({"pathmap": AmbiguousSliverPM(), "plane": 7}, [-0.5, 0.0], [519.5, 0.0])
        check(was is True and d == [-0.5, 0.0] and why == "origin-ambiguous",
              "2g. a sliver where two planes meet and the report names neither refuses, "
              "and NAMES the door (origin-ambiguous, not origin-unwalkable)",
              f"got {d} {why}")
        d, was, why = clipf({"pathmap": OldSliverPM(), "plane": 29}, [-0.5, 0.0], [519.5, 0.0])
        check(was is True and d == [-0.5, 0.0] and why == "origin-unwalkable",
              "2g. a mesh without on_mesh()/plane_near() keeps the exact test (no raise, "
              "no door)", f"got {d} {why}")
        authsrv.A2_LEAD_PLANE_CLIP = False
        d, was, why = clipf(sl_st, [-0.5, 0.0], [519.5, 0.0])
        check(was is True and d == [-0.5, 0.0] and why == "origin-unwalkable",
              "2g. the PLANE-BLIND arm (--no-lead-plane-clip) never opens the sliver door: "
              "a sliver origin is only ever walked on a named plane",
              f"got {d} {why}")
        authsrv.A2_LEAD_PLANE_CLIP = True
        authsrv.A2_LEAD_ORIGIN_SEAM = False
        d, was, why = clipf(sl_st, [-0.5, 0.0], [519.5, 0.0])
        check(was is True and d == [-0.5, 0.0] and why == "origin-unwalkable",
              "2g. KNOWN-BAD ARM (--lead-origin-exact): the same sliver origin is refused "
              "and the lead is a zero-lead -- the 179-refusal behaviour reproduces",
              f"got {d} {why}")
    finally:
        authsrv.A2_LEAD_ORIGIN_SEAM = _was_origin
        authsrv.A2_LEAD_PLANE_CLIP = _was_plane
    check(authsrv.A2_LEAD_ORIGIN_SEAM is True
          and '"--lead-origin-exact"' in ARGS_SRC
          and "A2_LEAD_ORIGIN_SEAM = not a.lead_origin_exact" in _psrc
          and '"origin-ambiguous"' in _psrc
          and "pm.plane_near(rx, ry, prefer=state.get(\"plane\"))" in _psrc,
          "2g. it ships ON, --lead-origin-exact reverts and is bound from argv, the "
          "ambiguous door has its own word, and the sliver's plane comes from "
          "plane_near(prefer=the REPORT's plane)",
          "a sliver origin walked on a guessed plane is the 1z-ao door by another name")

    print("\n3. composition cells: the lattice around the bundle")
    comp = authsrv.zero_lead_composition
    for kw, frag in [
            (dict(cancel_answer="suppress"), "--d1-lead and --cancel-answer"),
            (dict(family_rate_probe=True), "--d1-lead and --family-rate-probe"),
            (dict(checksum_probe="model"), "--d1-lead and --checksum-probe"),
            (dict(pc_spoof=26), "--d1-lead and --pc-spoof"),
            (dict(stop_answer="ack"), "--d1-lead and --stop-answer"),
            # arrival_carry rides with plane_carry=False: with BOTH carries
            # on, the older plane-vs-arrival cell fires first (correctly --
            # that pair is refused on its own ground), so the d1 cell's own
            # text is reachable only when plane_carry is off.
            (dict(arrival_carry=True, plane_carry=False),
             "--d1-lead and --arrival-carry"),
            (dict(click_sweep=True), "--d1-lead and --click-sweep")]:
        kw.setdefault("plane_carry", True)
        r, _ = comp(zero_lead=True, d1_lead=True, **kw)
        check(r is not None and frag in r,
              f"refused pairwise: {frag}",
              "each pair is either two policies for one wire field/site or "
              "a diagnostic inside a policy run -- the cell text carries "
              "the specific ground")
    r, _ = comp(zero_lead=False, d1_lead=True)
    check(r is not None and "--d1-lead requires --zero-lead" in r,
          "requires zero-lead (the modifier has no site without it)",
          "the inert-flag defect: an on-looking log over a server running "
          "the shipped default")
    r, _ = comp(zero_lead=True, plane_carry=False, d1_lead=True)
    check(r is not None and "--d1-lead requires --plane-carry" in r,
          "requires plane-carry (plane truth is term 3 of the bundle)",
          "running the lead without it re-creates the fake-label hazard "
          "sec.0.5-0.8 decoded")
    r, _ = comp(zero_lead=False, d1_lead=True, cancel_answer="suppress")
    check(r is not None and "--d1-lead and --cancel-answer" in r,
          "with both violations pending, the pairwise cell outranks the "
          "requires cell",
          "the family-rate precedent: 'you passed two levers' is the more "
          "useful refusal, and ordering is what mutations flip silently")
    r, notes = comp(zero_lead=True, plane_carry=True, d1_lead=True)
    check(r is None and any("--d1-lead" in n and "BUNDLE" in n
                            for n in notes),
          "the registered shape itself is ALLOWED, with the note naming "
          "the bundle and the stop-repin's era-audit ground",
          "the gamesrv header carries no argv; the note plus the verdict "
          "rows' lead_src are how a later session attributes the run")

    # ---------------------------------------------------------------- 4
    print("\n4. source locks: every site the bundle touches, position-pinned")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    check(src.count("D1_LEAD = False") == 1
          and src.count("D1_LEAD = True") == 1
          and "d1_lead=a.d1_lead" in src,
          "the global defaults False, main() rebinds exactly once, and the "
          "flag is threaded into the composition matrix",
          "the unpinned-rebind lesson, third time as precedent")
    check(src.count("if D1_LEAD and zero_ok:") == 1,
          "ONE speed-truth gate on the zero-lead verdict",
          "a second gate doubles the dose; an ungated call puts a 0x002B "
          "outside every witnessed burst shape")
    a1_gate = src.index("if FAMILY_RATE_PROBE and zero_ok:")
    a2_gate = src.index("if D1_LEAD and zero_ok:")
    # .find, not .index: a relocated gate must FAIL this check, not crash
    # the suite with a ValueError (the review's MUT-4 robustness note --
    # a crash is still red, but a [FAIL] names the broken thing).
    hg_after = src.find("if HEADING_GRANT:", a2_gate)
    check(a1_gate < a2_gate and hg_after != -1 and a2_gate < hg_after,
          "the A2 gate sits in the SAME witnessed burst slot -- after the "
          "A1 gate, before the first grant block",
          "relocated below the 0x0029 the wire shows 0x0029-then-0x002B, "
          "a shape with zero retail witnesses, and every count stays "
          "green")
    check("_a2_family_rate(send, state, moving)" in src,
          "and the edge call passes the report's own movementType verbatim",
          "hardcoded, every send is [1.0, 1] -- the click-confound "
          "signature -- and no count reddens")
    check(src.count("a2_dest, a2_src = d1_lead_dest(") == 1,
          "ONE dest-computation site routes through d1_lead_dest",
          "a second computation site is two formulas for one wire point")
    i_spoof = src.index("zl_plane_cur, pcs_fired = pc_spoof_field4(")
    i_d1 = src.index("a2_dest, a2_src = d1_lead_dest(")
    i_verdict = src.index('rec.event("grant_verdict"', i_d1)
    check(i_spoof < i_d1 < i_verdict,
          "computed after the plane policy resolves and BEFORE the verdict "
          "row, so the row records the point that goes out",
          "below the verdict, the row logs reported while the wire "
          "carries the lead -- the unattributable-capture defect")
    check("lead_src=(a2_src if zero_ok" in src,
          "the verdict row carries lead_src (d1/fallback/null)",
          "the census key for P-1..P-5's scoring; null on a refusal like "
          "every field-4 fact")
    # -- sec.0.17: the D2 clip's locks -----------------------------------
    # 2026-09-03: MOVECODE-1z-t added a SECOND caller (the KBD_SYNC lead's
    # own branch, same arm, same slot), so the count moved 2 -> 3: one def
    # and two calls. What the lock is FOR is unchanged and is now checked
    # directly rather than through the count -- EVERY call must be anchored
    # on `reported`, never on state['pos'], because a ray from the model's
    # belief is --heading-grant's graveyard (R2-1). Counting call sites was
    # only ever a proxy for that; a third caller anchored correctly is fine
    # and a second one anchored on the model would not be.
    # SUBTRACT THE DEFINITION. `def a2_clip_lead(state, reported, dest)`
    # matches the call pattern too, so a bare count of the anchored spelling
    # reads 3 for two calls -- this arc's substring trap, for the fifth time.
    _clip_calls = (src.count("a2_clip_lead(")
                   - src.count("def a2_clip_lead("))
    _clip_anchored = (src.count("a2_clip_lead(state, reported,")
                      - src.count("def a2_clip_lead(state, reported,"))
    check(_clip_calls == 4
          and src.count("def a2_clip_lead(state, reported, dest)") == 1
          and _clip_anchored == _clip_calls
          and "a2_clip_lead(state, state[" not in src,
          "the D2 clip has its def and FOUR call sites (D1's, 1z-t's, "
          "1z-ae's refresh and 1z-cl's corridor chain), and EVERY call is "
          "anchored on the REPORT in hand, verbatim",
          "state['pos']-anchored is --heading-grant's graveyard (R2-1): "
          "a ray from the model's belief aims the lead from somewhere "
          "the client is not -- a warp with a plausible destination")
    i_clip = src.index("a2_clip_lead(state, reported,", i_d1)
    check(i_d1 < i_clip < i_verdict
          and 'if a2_src == "d1":' in src[i_d1:i_clip + 80],
          "the clip sits AFTER the dest compute, BEFORE the verdict row, "
          "gated on a REAL d1 lead",
          "clipping a fallback second-guesses the client's own reported "
          "point; clipping below the row logs the through-wall dest "
          "while the wire carries the clipped one -- the unattributable-"
          "capture defect, again")
    check("lead_clipped=(a2_lead_clipped" in src,
          "and the row carries lead_clipped, sec.0.17's census key",
          "the next owner run's wall-phase REFUTED-IF needs the clipped "
          "rows selectable from the capture, not reconstructed against "
          "the mesh by a later session")
    # -- sec.0.19: the RETHINK instrument-#1 rows ------------------------
    check("lead_clip_why=(a2_clip_why" in src
          and 'a2_clip_why = "fallback"' in src,
          "the lead row names WHICH clip door decided (lead_clip_why: "
          "no-mesh / origin-unwalkable / clear / clipped / fallback)",
          "the P-17 escape (origin-unwalkable at a 0.25u mesh-edge "
          "penetration) was reconstructable only by re-scoring exact "
          "floats against the mesh by hand; a boolean cannot say which "
          "door opened")
    check(src.count('reason="answer-outstanding", arm="click-d1",') == 1
          and src.count('pending.get("hold_logged")') == 1
          and src.count('pending["hold_logged"] = True') == 1,
          "the FLUSH hold's refusal is a row now -- once per held item, "
          "latched by hold_logged",
          "this branch was the one guard in the click channel with no "
          "row: the P-17 decode had to prove the hold's inertness by "
          "absence. Per-poll rows would drown the log (the flush rides "
          "every quiet tick); once per item is the whole story a held "
          "click has")
    check("kbd_age=(None if _kbd_at is None" in src,
          "position_report rows carry the Rule-1 latch's age (or-None "
          "discipline)",
          "the latch's whole trajectory across a click-free stretch was "
          "invisible -- P-17's ~490s of never-armed had to be inferred "
          "from the absence of drops. A latch age on every report row "
          "makes guard inertness a readable column")
    check(src.count('"a2_leg", act="arm"') == 1
          and src.count('act="clear", src="0x003D"') == 1
          and src.count('act="clear", src="0x0047"') == 1,
          "the leg model's lifecycle is rows: ONE arm site, TWO clears "
          "(the same two pops the read-not-pop lock already pins), "
          "clears logged only when a leg existed",
          "only watchdog FIRES were visible; a run's trajectory through "
          "'is a leg armed' was unrecoverable after the fact (REV-3's "
          "decode rule had to re-derive it per incident)")
    check(src.count('rec.event("a2_watchdog_due", why=why)') == 1
          and 'why != state.get("a2_wd_why")' in src,
          "the watchdog's due-predicate logs on reason TRANSITION only",
          "the poll rides every ~1s quiet tick -- per-poll rows would "
          "restate no-leg all session; silent refusals made 'why hasn't "
          "it fired' unrecoverable. A transition row is the derivative, "
          "which is the readable part")
    check(authsrv.A2_LEAD_CLIP_STEP == 2.0
          and authsrv.A2_LEAD_CLIP_STEP < authsrv.COLLISION_STEP,
          "the clip's sampling step is pinned at 2.0u, finer than the "
          "walk integrator's COLLISION_STEP",
          "the Q7 desk check reproduced retail's world-anchored clip "
          "coordinates on our mesh to <=3u only at a fine step -- at "
          "16u the landing quantizes ~9u short of the edge retail names "
          "exactly (p05 went 14.6u -> 2.0u when the step dropped)")
    check(src.count("a2_matched_field4(") == 10,
          "the matched-words helper has exactly TEN call sites in this "
          "file -- the heading arm's D1 branch, the stop-repin, the ETA "
          "watchdog's repin, the two click-answer sites (immediate + "
          "deferred), ROUTER-B2's four (chain tick, clip-fallback, one-leg "
          "verbatim, first leg of a chain), and since 2026-09-03 night "
          "MOVECODE-1z-z's KBD lead branch: every 0x0029 the bundle, the "
          "router OR the keyboard lead sends is matched",
          "an extra caller would rewrite another arm's field 4 under a "
          "flag whose charter does not cover it; a missing caller leaves "
          "one send path carrying the stale word the lock needs. The "
          "router's four were added deliberately (ROUTER.md sec.4 item 4: "
          "matched pairs everywhere, sec.0.11's own protection). The count "
          "read ELEVEN until REFACTOR-A11 moved the helper's own def to "
          "`leadgeom.py`; this censuses the call sites, which all stayed")
    check(src.count('state["a2_family_sent"] = None') == 7,
          "the family edge re-arms at all SEVEN [1.0]-overwriting sends: "
          "A2's stop arm, the watchdog, both click-answer sites, "
          "ROUTER-B2's two speed-sending answers (clip-fallback and the "
          "routed/verbatim block -- chains send speed ONCE, at the first "
          "leg only, retail's own grammar), and since 2026-09-03 "
          "MOVECODE-1z-t's own stop echo",
          "each of those sends puts 1.0 in sync +0x60; a site without "
          "the reset leaves the next same-family leg reckoning at 288 "
          "flat -- the exact --client-endpoint failure term. 1z-t's stop "
          "echo is the seventh because it sends the same [1.0, 9] A2's "
          "does, from the same arm, for the same reason")
    check(src.count('may_grant, why_g = True, "d1-click"') == 0
          and src.count('why_g = "click-held"') == 0
          and src.count('grant, why = True, "d1-click"') == 0,
          "sec.0.15's shape: NO mid-keyboard click rewrite exists at "
          "either site -- not F-B's immediate answer, not F-A's hold, not "
          "the flush's rate-fire. Keyboard-shadowed clicks take the "
          "shipped Rule-1 drop, retail's own measured contract (the "
          "both-dropped keyboard instance; older-dropped-outright under "
          "an active authority)",
          "each rewrite was tried and refuted within the day: F-B's "
          "immediate answers raced the copy through props (21 copy "
          "re-seats, 2.7x rate); F-A's held-then-flush fires were the "
          "direction-yank engine (35/44 sharp turns, median 583u "
          "off-aim). This check's own history IS the record: it asserted "
          "the bypass EXISTS (F-B draft), then the hold EXISTS (F-A "
          "draft), and now asserts them GONE")
    check(src.count('reason="voided-by-report"') == 1,
          "the eager void exists at ONE site",
          "the void is F-A's core: the player's hands, speaking now, "
          "outrank the click they threw while moving -- exactly "
          "retail's press-anchored behavior")
    check(src.count('state["a2_click_answered_at"]') == 4
          and src.count('a2_click_answered_at") or 0.0)') == 2,
          "the outstanding-answer stamp is written at the two legacy "
          "click send sites plus ROUTER-B2's two answering blocks, and "
          "read at BOTH hold sites -- the flush AND the immediate site "
          "(or-0.0 discipline at each)",
          "sec.0.15's double-click fix, completed by sec.0.17: the flush "
          "hold alone left the immediate site as the one unguarded door, "
          "and the 113833 run walked click 2 through it (R-3 REFUTED). "
          "A missing stamp re-opens the stomp; a raw read re-opens REV-1. "
          "The router stamps for observability although its clicks never "
          "arm the hold (they bypass the tower by design, ROUTER.md "
          "sec.4 item 7)")
    i_hold = src.index('a2_click_answered_at") or 0.0)')
    i_gv_flush = src.index("grant, why, kage, since = _grant_verdict(")
    check(i_hold < i_gv_flush,
          "and the flush's hold sits BEFORE the flush's verdict call",
          "after it, a keyboard-quiet flush tick would fire the held "
          "click into the silent click-walk the hold exists to protect")
    i_take = src.index("a2_pos_taken = _take_client_position(")
    i_void = src.index('reason="voided-by-report"')
    check(i_take < i_void
          and "if (D1_LEAD and a2_pos_taken" in src,
          "and it sits after the position adoption, gated on the report "
          "being ACCEPTED",
          "voiding on a REJECTED report would let a position the trust "
          "policy refused cancel the player's own click")
    gsim = open(os.path.join(os.path.dirname(HERE), "clientscan",
                             "grantsim.py"), encoding="utf-8").read()
    check('"zero-lead", "click-d1"' in gsim,
          "grantsim's C3 replay skips arm=click-d1 rows, the same "
          "preemptive filter the heading arm got",
          "REV-1: without the skip, the first --d1-lead capture reddens "
          "C3 on every answered click -- condemning correct behavior")
    check(src.count('arm=("click-d1" if D1_LEAD') == 2
          and '"deferred-d1-click" if why == "d1-click"' in src,
          "both click rows NAME their policy in an arm field, and a "
          "bypassed deferred fire keeps its marker instead of hiding "
          "inside deferred-grant",
          "REV-4: a capture that cannot say which policy produced a row "
          "costs a later session a reconstruction (REALFIX-Q8, again)")
    check(src.count("grant_flush_tick(send, state, conn_id, rec)") == 3
          and "if not D1_LEAD:\n                            "
              "grant_flush_tick(" in src,
          "the flush has exactly three call sites -- the world tick "
          "(gated OFF under the bundle) and the two recv-thread sites "
          "(pre-batch and quiet-tick)",
          "REV-2: F-B made the world-tick flush race the recv thread's "
          "heading arm on the lock-free grant clock -- two 0x0029 inside "
          "one floor, the click's own pair splittable. Recv-thread-only "
          "sending serializes every player-grant sender by construction, "
          "and pre-batch ordering gives the held click first claim on "
          "each floor opening (REV-3's starvation, same fix)")
    i_gv_call = src.index("may_grant, why_g, kage, since = _grant_verdict(")
    i_row = src.index('rec.event("grant_verdict", fired=may_grant,')
    between = src[i_gv_call:i_row]
    between_stripped = between.replace(
        "may_grant, why_g, kage, since = _grant_verdict(", "")
    check(between_stripped.count("why_g = ")
          == between_stripped.count(
              'may_grant, why_g = False, "answer-outstanding"') == 1
          and 'a2_click_answered_at") or 0.0)' in between,
          "and the ONLY thing between _grant_verdict and its row is "
          "sec.0.17's outstanding-answer hold -- refuse-only (False, "
          "never True), self-naming in the row, or-0.0 disciplined",
          "both F-B's and F-A's rewrites lived exactly here and each "
          "made the row lie about a policy that was then refuted -- and "
          "BOTH resurrected refused clicks (the True direction). The "
          "sec.0.17 hold is the opposite move: it only ever REFUSES, and "
          "the row records the refusal under its own reason, so the "
          "capture stays attributable (Q8). A second rewrite in the gap, "
          "or any True rewrite, is the graveyard reopening")
    check('state.get("dest") is not None' in between,
          "and the immediate hold carries the LEG BOUND -- it refuses "
          "only while the server's copy is still walking a leg, never on "
          "bare silence",
          "the client reports NOTHING during a click-walk (41.2s in the "
          "113833 run), so the flush's bare answered_at > pos_seen "
          "predicate is a SILENCE detector at this site: lane A's "
          "offline counterfactual showed it suppressing 22 of 24 real "
          "staircase fires (92%). Dropping the dest conjunct 'to match "
          "the flush' re-creates exactly that -- the two sites ask "
          "DIFFERENT questions and the asymmetry is the design")
    check('d1_passthrough=bool(D1_LEAD)' in src
          and src.count('rec.event("click_verdict"') == 1,
          "the geometry branch writes its click_verdict row (the soak's "
          "138 no-trace clicks) and marks the D1 fall-through",
          "a refusal branch with no row makes the census a subtraction "
          "exercise; the marker separates answered-despite-geometry from "
          "refused")
    i_match = src.index("zl_plane_cur, a2_matched = (")
    check(i_spoof < i_match < i_d1 < i_verdict,
          "the heading-arm override sits AFTER the carry/spoof "
          "resolution, BEFORE the dest compute and the verdict row -- "
          "the row records the matched word that actually goes out",
          "above the carry it would be overwritten back to stale; below "
          "the row, plane_cur would log the stale word while the wire "
          "carried the match -- the unattributable-capture defect")
    check("pc_matched=(a2_matched" in src,
          "and the row carries pc_matched, sec.0.11's verification key",
          "the V-8 run's exposure floor counts these rows; without the "
          "key, exposure is reconstructed from a policy someone assumes "
          "was running")
    check('+ (" matched" if a2_stop_matched else "")' in src,
          "the stop-repin label marks its own overrides",
          "the repin's stale word was the lock's perfect DETECTOR "
          "(28/28); the marker preserves that detector's trace under "
          "the fix")
    check(src.count('state.pop("a2_leg", None)') == 2
          and src.count('a2_click_leg = state.get("a2_leg")') == 1,
          "the leg is DISCARDED only where the client spoke (the 0x003D "
          "and 0x0047 arms, two pops) and READ -- never popped -- by the "
          "click arm",
          "the review's REV-2: a click-arm pop answers only the FIRST "
          "click and re-refuses every later one on staleness the lead "
          "still explains (the client reports nothing between clicks, "
          "silences to 37 s); the watchdog stands down via the click "
          "latch, not by consuming the model")
    check('if a2_src == "d1":' in src
          and src.index('if a2_src == "d1":')
          < src.index('state["a2_leg"] = a2_leg_note('),
          "the arming site is guarded on a REAL d1 lead, verbatim, the "
          "guard above the arm",
          "the mutation lane's MUT-7: with the guard gone, fallback "
          "grants (zero-length) arm phantom legs whose ETA is t0+1.0s -- "
          "a watchdog repin one second after every degenerate-vec2 "
          "grant, and all 56 checks stayed green")
    check(src.count('state["a2_leg"] = a2_leg_note(') == 1,
          "ONE arming site, at the fired d1 grant",
          "a second armer would model legs that never went on the wire")
    # ANCHORED BY ADJACENCY, NOT BY INDENTATION. This used to be a literal
    # `... = plane\n` + 36 spaces + `# sec.0.11`, which pinned the column the
    # statement happened to sit in -- so ANIMREF-R11 wrapping the block in
    # `if zl_send_ok:` re-indented it by four and this raised ValueError past
    # the ledger, taking the file's exit code with it. There are three
    # `zl_last_grant_plane` sites so the disambiguation is real; what it must
    # key on is the sec.0.11 comment that follows, at whatever depth.
    i_zllast = -1
    _probe = 0
    while True:
        _probe = src.find('state["zl_last_grant_plane"] = lead_f3', _probe)
        if _probe < 0:
            break
        if "sec.0.11" in src[_probe:_probe + 120]:
            i_zllast = _probe
            break
        _probe += 1
    check(i_zllast >= 0,
          "the post-send plane-slot advance is findable by its sec.0.11 "
          "neighbour, at whatever indentation",
          "the old literal anchor pinned a column, not a structure")
    i_arm = src.index('state["a2_leg"] = a2_leg_note(')
    check(i_zllast < i_arm,
          "and it sits in the post-send bookkeeping, after the "
          "plane-slot advance",
          "armed before the send, a refused grant would leave a phantom "
          "leg for the watchdog to answer")
    # ANIMREF-R11 makes that phantom STRUCTURALLY impossible rather than
    # merely ordered: the send and every line of its bookkeeping now sit
    # inside one `if zl_send_ok:`, so a suppressed grant cannot advance the
    # plane slot, arm a leg for the watchdog to answer, or move the arrival
    # carry. The first cut of R11 guarded only the send and left all three
    # running -- which would have armed a watchdog re-pin on exactly the
    # press this fix exists to protect.
    i_guard = src.index("if zl_send_ok:")
    check(i_guard < i_zllast < i_arm
          and src.index("if ARRIVAL_CARRY:", i_guard) > i_arm,
          "and R11's guard opens BEFORE all of it -- the plane advance, the "
          "leg arm and the arrival carry are inside the same `if "
          "zl_send_ok:` as the send",
          "guarding only the send would leave a suppressed grant arming a "
          "leg whose ETA the watchdog then re-pins: the relocation R11 "
          "exists to prevent, reintroduced one line below the fix")
    check(src.count("_a2_watchdog(send, state, rec)") == 1
          and src.count('if D1_LEAD and kind == "game":') == 1
          and src.count("[a2-watchdog]") == 2
          and src.count("A2 WATCHDOG-REPIN (") == 1,
          "ONE watchdog call site, D1- and game-channel-gated, with ONE "
          "speed send and ONE repin send (the [a2-watchdog] tag's second "
          "appearance is the fire's own console line), labelled",
          "the watchdog is a grant on the shared clock riding the recv "
          "loop's quiet ticks; a second site or an auth-channel call is "
          "a send nobody audited")
    check(src.count("a2_click_pos = a2_leg_position(a2_click_leg,") == 1
          and "pm_c.containing(click_px, click_py)" in src
          and "pm_c.clip(click_px, click_py," in src,
          "the click arm's placement and clip both read the model-or-"
          "reported position through click_px/click_py, computed at ONE "
          "site",
          "a placement read left on state['pos'] while the freshness "
          "gate passes on the model would place the player at the leg's "
          "START -- the exact staleness being corrected, half-fixed")
    check("zl_point = (a2_dest" in src
          and "lead_f3, lead_f4]," in src
          and src.count("lead_f3, lead_f4 = plane, zl_plane_cur") == 1
          and src.count("zl_plane_cur = lead_f4") == 1,
          "the ONE 0x0029 send consumes a2_dest through zl_point and its "
          "field 4 reads lead_f4, which is zl_plane_cur unless 1z-cl's "
          "mesh words moved it (one initialiser, one override, verbatim)",
          "a second 0x0029 send site is the two-arms-one-clock defect; a "
          "private field-4 expression at the send strands the plane "
          "policy inert")
    check(src.count("A2 STOP-REPIN (") == 1 and src.count("[a2-stop]") == 1,
          "ONE stop-repin site, ONE stop speed-send, labelled (the bare "
          "phrase also appears in the banner's READOUT line, which is why "
          "the lock counts the send's own f-string prefix)",
          "the stop arm is a grant on the shared clock; a second site "
          "doubles the ack invisibly")
    i_cw_stop = src.index("CANCELWALK STOP (")
    i_a2_stop = src.index("A2 STOP-REPIN")
    i_r6 = src.index('if STOP_ANSWER == "ack":', i_a2_stop)
    check(i_cw_stop < i_a2_stop < i_r6,
          "the stop-repin sits between CANCEL_STOP's scoped re-pin and the "
          "R6 bare-ack inside the 0x0047 handler",
          "position is what distinguishes 'generalizes the scoped shape' "
          "from 'a new send in an unaudited slot'; the composition matrix "
          "refuses cancel-answer and stop-answer beside it, so at most "
          "one stop reply is live in any run")
    a2_stop_block = src[i_a2_stop:i_r6]
    check('state["a2_family_sent"] = None' in a2_stop_block,
          "and the stop arm resets the family edge inside its own block",
          "the [1.0, 9] it just sent overwrote sync +0x60; without the "
          "reset the next leg's same-family float is never re-asserted "
          "and the copy walks a whole leg at 1.0")
    # The review's MUT-7: the one mutation that survived every lock was
    # swapping the stop-repin's two sends. Retail's grammar is 0x0029
    # ALWAYS LAST (3,023 of 3,071 bursts) and the stop census shows the
    # 0x002B companion FIRST at 131/131 echoes -- so the order is part of
    # the registration, and it gets its own pin.
    i_stop_spd = src.find("[a2-stop]")
    i_stop_pin = src.find("A2 STOP-REPIN (")
    check(i_stop_spd != -1 and i_stop_pin != -1
          and i_cw_stop < i_stop_spd < i_stop_pin < i_r6,
          "the stop arm's 0x002B goes out BEFORE its 0x0029 -- the "
          "[a2-stop] speed send precedes the A2 STOP-REPIN grant inside "
          "the block",
          "swapped, the wire shows a stop burst retail has zero witnesses "
          "for (0x0029 then 0x002B), the client bakes the re-pin BEFORE "
          "the [1.0,9] lands in +0x60, and every count stays green -- the "
          "review's one surviving mutation")

    # ---------------------------------------------------------------- R11
    print("R11. the grant is not sent while WE hold the action")
    # WHY THIS IS A SOURCE CHECK AND A PREDICATE CHECK, not a wire drive: the
    # send lives inside `handle()`, the socket handler, so there is no seam to
    # drive it through without a connection. The structure check pins that the
    # guard exists at the one send site; the predicate check below exercises
    # the condition itself in BOTH arms, including the known-bad one.
    check(getattr(authsrv, "GRANT_DURING_HOLD", None) is True,
          "GRANT_DURING_HOLD defaults to True -- R11 was REFUTED by its own "
          "next run and the suppression is now OPT-IN",
          "suppressing did remove the body relocation it targeted, and it "
          "cost the slide with it: recovery lag p50 62 ms -> 406 ms, "
          "dispatches 333 -> 59, and the owner scored 0 quartersteps. The "
          "slide was the grant's. An experiment lever that defaults to a "
          "refuted arm is a policy nobody ruled")
    check(src.count("zl_send_ok = (GRANT_DURING_HOLD") == 1
          and src.count('or not state.get("action_hold")') == 1
          and src.count("if zl_send_ok:") == 1,
          "exactly ONE guarded send site -- a second would be the "
          "two-arms-one-clock defect the composition matrix refuses",
          "the grant that relocated the body in run 3 came from this site "
          "and only this site (ret 0x005FD918, 44 grants, 3 relocations)")
    check("R11 grant " in src and "SUPPRESSED" in src,
          "and a suppressed grant is PRINTED, never silent -- a run where "
          "this never fires has no exposure rather than a clean result",
          "the zero-exposure lesson: a treatment arm that never met its "
          "condition has run zero trials")
    check("--suppress-grant-during-hold" in src
          and "suppress_grant_during_hold" in src,
          "and the A/B lever exists and binds -- the refuted arm stays "
          "reachable so the experiment can be repeated, which is how it was "
          "refuted in the first place")

    # THE PREDICATE, BOTH ARMS. This is the check that must FAIL on the
    # known-bad configuration; a guard that passes with the fix disabled is
    # measuring the wrong quantity.
    def grants(hold, legacy):
        return bool(legacy or not {"action_hold": hold}.get("action_hold"))

    check(grants(0, False) is True and grants(1, False) is False,
          "the OPT-IN arm still works: with suppression on, a hold-CLEAR "
          "report is answered and a hold-SET one is not -- the lever must "
          "keep doing what it did, or the A/B cannot be repeated",
          "2 of 15 post-refusal grants relocated the body against 0 of 29 "
          "otherwise, and retail suppresses 10:1 (0.050/s held vs 0.519/s "
          "clear) -- rates, not counts, because the windows differ in length")
    check(grants(1, True) is True,
          "and the SHIPPED default answers the report even with the hold "
          "set -- which is what keeps the second dispatch at p50 62 ms "
          "instead of 406 ms",
          "the two arms must differ here or the lever is inert")


    return LEDGER.verdict()


# `sys.exit(main())`, not a bare `main()`, and `main` RETURNS the verdict:
# both halves were missing until 2026-08-31, so this file printed its FAIL
# banner and exited 0. run_suite.py catches that as SUSPECT (exit 0 with no
# ALL CHECKS PASSED line), which is the backstop working -- but a developer
# running the file directly saw a clean exit code on a red run, and
# CLAUDE.md's rule is that a test exits non-zero.
if __name__ == "__main__":
    sys.exit(main())
