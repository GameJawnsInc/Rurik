"""The geometry and bookkeeping of one granted leg -- where it starts, where it
points, and whether its plane matched.

Pure functions and five constants, lifted verbatim out of `authsrv.py`
(REFACTOR-A11). Nothing here sends, reads a flag, opens a socket or knows an
opcode: each of these is handed what it needs and returns a value or a record.
`math` is the whole dependency, which is why this file carries no `sys.path`
header -- there is nothing local to resolve (`fogrle.py` is the precedent).

WHOSE EVIDENCE THIS IS, AND WHERE THE OTHER HALF LIVES. The fourteen names here
came out of eleven fragments spanning some 7,100 lines of `authsrv.py`, and
they belong to five arcs. In every case the FLAG stayed behind with the banner
that justifies it and the geometry came here, so each arc's evidence now sits
in two files. The pointers, both ways -- `authsrv.py` line numbers as of this
commit, with the symbol as the durable anchor:

  * --pc-spoof       `PC_SPOOF` and its cell banner, authsrv.py:5519.
                     Here: `PC_SPOOF_GAP`, `pc_spoof_field4`.
  * --d1-lead        `D1_LEAD` and its bundle banner, authsrv.py:5567.
                     Here: `D1_VEC2_CEILING`, `D1_VEC2_FLOOR`, `d1_lead_dest`.
  * the A2 watchdog  `_a2_watchdog`, the check-and-fire half, authsrv.py:7129;
                     and `a2_leg_note`, authsrv.py:7089, which stayed because
                     it reads FAMILY_RATE. Here: `A2_WATCHDOG_SPEED_FLOOR`,
                     `A2_WATCHDOG_SLACK`, `a2_leg_position`, `a2_watchdog_due`
                     and the field-3/field-4 reconciler.
  * the click leg    `_click_leg_arm`, authsrv.py:12391, which stayed because
                     it reads DEFAULT_RUN_SPEED and otherwise does nothing but
                     call into here. Here: `_click_leg_source`,
                     `_click_leg_start`, `_leg_record`.
  * the heading hold `heading_hold_tick`, authsrv.py:6335, which consumes what
                     the note builds. Here: `heading_hold_note`.

WHY THERE ARE NO WRAPPERS. The other leaves in this arc take their flags as
threaded parameters, because the flag each reads is `global`-rebound in
`main()`. This one takes none: the five constants above are the only
module-level names these functions read, not one of them is `global`-declared
anywhere, no test assigns any of them, and all five travelled. `authsrv.py`
re-exports all fourteen names at the sites the code left, so every bare-name
call site and every `authsrv.<name>` read in the suite still resolves.

ONE SOURCE LOCK MOVED WITH THE CODE, and it is worth knowing which.
`test_router.py` pins the click leg's own-start read -- that the lerp measures
from the leg's own grant instant and not from the click's stamp -- by looking
for that expression in the source TEXT. The expression is in this file now, so
that check reads this file. It is the only test text this move touched besides
`test_d1lead.py`'s census of the reconciler's call sites, which dropped by one
when its `def` line left `authsrv.py`.

Standard library only, and NO import of the server: `authsrv.py` runs as
`__main__`, so a leaf importing it back would load a second copy whose flags
`main()` never set.
"""
import math


# The --pc-spoof flag itself, and the cell banner that justifies it, stayed
# behind in authsrv.py at line 5519.
#
# The park threshold. A1's fired-grant gaps during continuous play top out
# at 3.054 s (leg cadence with ~1 s releases, measured in
# authsrv-20260825T202330-c1); the cell's parks are >= 6 s by recipe. 4.0
# sits above the one and below the other with margin on both sides. A
# constant rather than a flag: the cell has one registered shape.
PC_SPOOF_GAP = 4.0


def pc_spoof_field4(spoof, since_last, carried):
    """Field 4 for one FIRED zero-lead grant: (value, spoofed).

    Pure -- the trigger derives entirely from `since_last` (the same gap the
    verdict row records: seconds since the previous FIRED grant), so refused
    evaluations consume nothing and the spoof re-arms exactly when a park
    does. `spoof is None` is the flag off; `since_last is None` is the first
    grant of a connection, which is a park by definition (the copy spawned
    parked).
    """
    if spoof is None:
        return carried, False
    if since_last is None or since_last >= PC_SPOOF_GAP:
        return int(spoof), True
    return carried, False


# The --d1-lead flag itself, and the bundle banner that justifies it, stayed
# behind in authsrv.py at line 5567.
#
# The d1 band: |vec2| measured 765.0175..768.0000 in every live 0x003D
# across 21 stamps -- and the formula's bit-exact verification covers ONLY
# that regime. 769.0 is the ceiling plus slack; 700.0 is the floor, far
# below the proposal band and far above the one mid-magnitude outlier our
# own corpus has ever produced (1 of 15,285 c2s rows, |v|=1.997 -- the
# 2026-08-26 review's census). A vec2 outside the band is refused
# (fallback, recorded), never clamped: a clamped wrong vector is still a
# wrong destination, and a short lead nobody registered is still a policy
# nobody registered.
D1_VEC2_CEILING = 769.0
D1_VEC2_FLOOR = 700.0


def d1_lead_dest(reported, vec2):
    """REALFIX-A2's D1 endpoint: (dest, src) for one heading report.

    dest = reported + vec2 + 0.5*unit(vec2) -- retail's formula verbatim
    (FINDINGS' D1 adjudication; re-verified 2026-08-26 to 0.0001 u). Pure.
    src is "d1" when |vec2| sits in the verified proposal band
    [D1_VEC2_FLOOR, D1_VEC2_CEILING]; anything else -- degenerate, mid-
    magnitude, non-finite, over-ceiling, malformed -- is "fallback": the
    grant carries the zero-lead point, the verdict row records which, and
    nothing is guessed.
    """
    try:
        vx, vy = float(vec2[0]), float(vec2[1])
    except (TypeError, ValueError, IndexError):
        return [float(reported[0]), float(reported[1])], "fallback"
    mag = math.hypot(vx, vy)
    if (not math.isfinite(mag) or mag < D1_VEC2_FLOOR
            or mag > D1_VEC2_CEILING):
        return [float(reported[0]), float(reported[1])], "fallback"
    return ([float(reported[0]) + vx + 0.5 * vx / mag,
             float(reported[1]) + vy + 0.5 * vy / mag], "d1")


def heading_hold_note(reported, point, plane, plane_cur, moving, a2_src,
                      lead_clipped, clip_why, dir_src, now, ray=None,
                      report_plane=None):
    """The held heading grant: everything the send would have used, as it
    was at refusal. Pure constructor. 1z-cl: `ray` (the unclipped lead
    destination) and `report_plane` ride along for the chain and the words."""
    return {"at": now,
            "reported": (float(reported[0]), float(reported[1])),
            "point": [float(point[0]), float(point[1])],
            "plane": plane, "plane_cur": plane_cur, "moving": moving,
            "a2_src": a2_src, "lead_clipped": bool(lead_clipped),
            "clip_why": clip_why, "dir_src": dir_src,
            "ray": (None if ray is None else (float(ray[0]), float(ray[1]))),
            "report_plane": (plane if report_plane is None else report_plane)}


def a2_matched_field4(plane, carried):
    """(field4, matched): field 4 MATCHES field 3. TWO ARMS USE THIS, NOT ONE.

    The 2026-08-26 input-lock decode (REALFIX.md sec.0.11): plane-carry's
    one-grant lag leaves the SYNC copy stamped with the OLD plane across a
    seam, and a mid-flight crossing grant with pd != pc snaps the drawn body
    onto that stale copy at ~15 u AND shuts the AgTrack fence -- which the
    lead's click-walk regime then keeps shut (no 0x0047, no walk-start, no
    re-arm: the self-sustaining input lock the owner reproduced). Retail
    never creates the cross-plane state at all: its nonzero plane pairs are
    bit-identical 222/222 (the sec.0.9 census). So the carry's value is
    OVERRIDDEN to match whenever it differs -- the sync copy's plane word
    reconciles AT the crossing. Pure; `matched` marks the rows where the
    override actually changed the wire (the census key for sec.0.11's
    verification run).

    ⚠ **THIS DOCSTRING SAID "for one --d1-lead send" UNTIL 2026-08-30 AND THAT
    WAS WRONG THE DAY IT WAS WRITTEN.** `6651c91` created the function for
    --d1-lead; `d3a5936` (ROUTER-B2, SAME DAY) added four more call sites and
    never revised the contract line. A reader who greps `D1_LEAD` then finds
    three router sites calling this unconditionally concludes they leak, and
    that conclusion is WRONG -- it was reached twice, by two separate analyses,
    which is why this block exists. **Do not "fix" it by gating them.**

    THE RULE, and it is about WHOSE plane field 3 is:

      * Field 3 is a plane WE computed (the route's corridor plane, or
        `_router_plane()`): field 4 MUST match it, UNGATED, on every arm. That
        is the P-17 phasing door -- a routed leg with pd != pc snaps the body.
        The three unconditional call sites are exactly these, and
        `test_router.py` PINS them ("first leg carries the corridor's plane,
        matched"; "interior leg planes are matched via plane_at"). Gating them
        turns that test red -- measured, not assumed. And `test_d1lead.py` has
        pinned the same fact since ROUTER-B2 landed: its call-site census names
        the router's four and says outright that they "were added deliberately
        (ROUTER.md sec.4 item 4: matched pairs everywhere, sec.0.11's own
        protection)". THREE places said so before this docstring did.
      * Field 3 is the CLIENT'S OWN named plane passed straight through (the
        one-leg verbatim echo, "wire-identical to the shipped clear-line fire,
        planes included"): the override is gated behind `if D1_LEAD:` so the
        echo stays byte-verbatim outside the lead. That is the one gated site.

    ⚠ **AND THE PREMISE HAS A MEASURED COUNTEREXAMPLE (FINDINGS 1z-o.6).** In
    R7 the one-leg router path called this with plane=0, carried=37, and it
    returned 0 -- overriding the carry off the body's TRUE plane 37 to the
    route's first waypoint plane, before the body had crossed. (Written out
    rather than shown as a call, because `test_d1lead.py` censuses this
    helper's call sites by counting its name in the source, and an example
    in a docstring reads as a tenth caller.) The SYNC copy took the 0,
    the client's own snap gate 2 then queried from a plane-0 point it could not
    resolve, returned `pathCount == 0`, and reseeded. Matching field 4 trades a
    phasing snap for a plane the body is not yet on, and that trade is not free
    on a route that crosses a seam. Not a bug to patch blind -- an open
    question with one observation behind it. Do not change the rule without
    reading 1z-o.6 and re-running R7's geometry.
    """
    if carried != plane:
        return plane, True
    return carried, False


# The watchdog's speed floor: the SLOWEST family the client walks a lead at
# (0.66 x 288 = 190.08 u/s, the backpedal float A1 proved wire-steerable), so
# an ETA computed with it can only be LATE, never early -- a watchdog that
# fires mid-leg would supersede a walk the client is legitimately making.
A2_WATCHDOG_SPEED_FLOOR = 0.66 * 288.0
A2_WATCHDOG_SLACK = 1.0


def a2_leg_position(leg, now):
    """(x, y, plane) the model puts the player at, mid- or post-lead-leg.

    The client walks a granted lead like a click, key state ignored, and
    reports NOTHING until its next key edge (sec.0.11) -- so during and
    after such a leg the report-staleness clock measures our own grant's
    known effect, not ignorance. Position = along-leg interpolation at the
    leg's own family speed, CLAMPED at the dest (after arrival the client
    parks there -- the incident's recovery-click case: 7.15 s "stale" with
    the player standing exactly where the model said). Pure; returns None
    only for a missing leg.
    """
    if not leg:
        return None
    dx = leg["dest"][0] - leg["x0"]
    dy = leg["dest"][1] - leg["y0"]
    dist = math.hypot(dx, dy)
    if dist <= 1.0:
        return leg["dest"][0], leg["dest"][1], leg["plane"]
    frac = min(1.0, max(0.0, (now - leg["t0"]) * leg["speed"] / dist))
    return (leg["x0"] + dx * frac, leg["y0"] + dy * frac, leg["plane"])


def a2_watchdog_due(state, now):
    """(due, why) -- should the ETA watchdog re-pin a silent client? Pure.

    Fires ONCE per leg, only when every clause holds: a d1 leg is armed;
    the leg's ETA at the SLOWEST family speed plus slack has passed (so the
    walk has surely completed -- a mid-leg re-pin would supersede a walk
    the client is making); no click has arrived since the leg was granted
    (a click-walking client is silent LEGITIMATELY, and a re-pin would
    stamp on its path -- the containment must never recreate the defect it
    contains). Refusal reasons are returned for the log, because a
    watchdog nobody can see not-firing is a wish.
    """
    leg = state.get("a2_leg")
    if not leg:
        return False, "no-leg"
    if leg["wd_fired"]:
        return False, "already-fired"
    # `or 0.0`, NOT a .get default: the click latch is cleared by ASSIGNMENT
    # to None (both report arms), so the key is present and holding None on
    # every ordinary connection -- .get's default never fires, and a bare
    # comparison TypeErrors past the recv loop's except clauses, killing the
    # session on its first quiet second. The 2026-08-26 containment review's
    # one REAL (REV-1), demonstrated before it ever ran live; the readers at
    # cast_stop_reckon already use this is-not-None discipline.
    if (state.get("click_moving_at") or 0.0) > leg["t0"]:
        return False, "click-in-flight"
    dist = math.hypot(leg["dest"][0] - leg["x0"], leg["dest"][1] - leg["y0"])
    eta = leg["t0"] + dist / A2_WATCHDOG_SPEED_FLOOR + A2_WATCHDOG_SLACK
    if now < eta:
        return False, "pre-eta"
    return True, "eta-passed"


def _click_leg_source(state, silent):
    """WHICH of `_click_leg_start`'s three sources answers -- by name.

    "leg" is OUR MODEL (a lerp along the click leg), "report" is the
    client's own last accepted position, "pos" is the blend, and None means
    nothing can place the body at all. `_click_leg_start` reads its branch
    from HERE rather than restating it, because a caller that puts the point
    on the WIRE has to know which one it got: a 0x002C at a "leg" point
    contradicts the last report and a 0x002C at the "report" point agrees
    with it, and the two answers are opposite (`_forget_client_position`,
    THE ASYMMETRY). A second copy of this condition would be a second place
    to disagree with it -- the same defect shape this file's source lock on
    state["client_pos"] exists to catch, one field over.
    """
    if silent and state.get("click_leg") is not None:
        return "leg"
    if state.get("client_pos") is not None:
        return "report"
    return "pos" if state.get("pos") is not None else None


def _click_leg_start(state, now, silent):
    """Where the body is when a click arrives, on the server's own model.

    Three sources, in the order the record trusts them: the previous click
    leg, interpolated to `now` and capped at its end, when the client has
    been SILENT since that click (`silent` -- the latch was still set when
    this click arrived, so no report has placed the body since; the client
    reports nothing while click-walking and nothing at arrival, so silence
    after a finished leg means the body is parked at its end); else the last
    accepted report; else the placement. Every position here is a model
    except the report itself, and the error is stated at _click_leg_arm.
    `_click_leg_source` names which of the three answered, for the callers
    that have to treat a model and a report differently.
    """
    src = _click_leg_source(state, silent)
    if src == "leg":
        leg = state["click_leg"]
        x0, y0 = leg["p0"]
        dx, dy = leg["dest"][0] - x0, leg["dest"][1] - y0
        # `start` is the leg's own grant instant (a router chain leg,
        # _router_rearm_leg); `t0` stays the click's stamp, the identity.
        t_start = leg.get("start", leg["t0"])
        span = leg["eta"] - t_start
        if span <= 0.0 or now >= leg["eta"]:
            return leg["dest"]
        f = max(now - t_start, 0.0) / span
        return (x0 + dx * f, y0 + dy * f)
    if src is None:
        return None
    pos = state["client_pos"] if src == "report" else state["pos"]
    return (float(pos[0]), float(pos[1]))


def _leg_record(p0, dest, now, speed):
    """One straight leg: start, end, and the instant it arrives. Shared by
    the click leg (_click_leg_arm) and the approach's follow leg
    (_approach_send) so the two are one model with one error statement."""
    p0 = (float(p0[0]), float(p0[1]))
    dist = math.hypot(float(dest[0]) - p0[0], float(dest[1]) - p0[1])
    return {"t0": now, "p0": p0,
            "dest": (float(dest[0]), float(dest[1])),
            "dist": dist, "speed": speed,
            "eta": now + (dist / speed if speed > 0.0 else 0.0)}
