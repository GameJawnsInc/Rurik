"""What a cast does to a walk -- CANCELWALK's pure policy.

Six functions, every one of them labelled `Pure:` in its own docstring and
none of them knowing an opcode, a socket or a state write. They lifted out of
`authsrv.py` verbatim on 2026-09-11; what follows is the same text, and the
history in it is load-bearing:

  * the three PARSERS (`parse_cast_stop`, `parse_stop_answer`,
    `parse_cancel_answer`) all hold the same contract -- a mistyped arm
    refuses LOUDLY rather than running the shipped default while the
    operator's log says an experiment was on -- and each refusal carries the
    ruling that shaped its arm, because a refusal is where a cold session
    trips over the decision.
  * `resolve_cast_stop_default` is the shipped-on-by-default resolver (owner's
    ruling 2026-08-25, `studies/movement/CANCELWALK.md` 8.3g) and its `why` is
    the provenance printed at startup.
  * `cast_stop_reckon` is R10's dead reckoning, carrying CANCELWALK-F31's
    warp-by-staleness, F34's 167.6 u parked-body warp and the whole
    pin-or-nothing consequence, plus the four corrections of the 2026-08-25
    review (B1's click-walk door, B2's census-family rate, R1's plane resolved
    AT the extrapolated point, R2's refusal to ship an unclipped ray).
  * `cancelwalk_lead_dest` is F2's confirmed retail expression.

WHAT STAYED BEHIND, and every one of these comments points at it:

  * `CAST_STOP` -- the module global, still `None` in `authsrv.py`; main()'s
    argparse layer arms it. The pure surface here is unchanged, which is the
    whole reason the global did not move with the policy.
  * `COLLISION_STEP` (16.0) -- `authsrv.py` has eight other readers of it and
    `studies/movecode/review/modelleg.py` reads it off the module, so it stays
    there and arrives here as `cast_stop_reckon`'s `step`, read at call time.
  * the PathingMap import and every send site. `cast_stop_reckon` calls
    `pm.clip(...)` / `pm.plane_at(...)` on an object arriving IN the state
    dict; this file must never grow a `pathmap` import, because the
    try/except in `authsrv.py` is what keeps bare machines working.

Standard library only, and no import of the server -- `test_cancelwalk.py`
exercises all six with no vault, no client and no socket.
"""
import math


def parse_cast_stop(text):
    """Pure: a --cast-stop argument -> (mode, refusal).

    Same contract as parse_stop_answer, for the same reason: a mistyped
    arm must refuse loudly rather than run the shipped default while the
    operator's log says an experiment was on. Bare --cast-stop parses as
    'halt' (argparse const): R8's measured form, kept as R10's control.
    """
    if text is None:
        return None, None
    if text in ("halt", "pin"):
        return text, None
    return None, (
        f"--cast-stop={text!r} names no arm. The arms are 'halt' (bare "
        f"--cast-stop; CANCELWALK-R8's measured cast-start 0x0028, which "
        f"WARPS by the copy's staleness, F31, and is REFUSED as a ship by "
        f"owner ruling 2026-08-25) and 'pin' (CANCELWALK-R10: a "
        f"dead-reckoned 0x002C re-pin, then the 0x0028 -- the SHIPPED "
        f"DEFAULT since 2026-08-25, so bare startup already runs it and "
        f"--no-cast-stop turns it off) -- "
        f"studies/movement/CANCELWALK.md sec.8.")


def resolve_cast_stop_default(explicit, no_flag, zero_lead, cancel_answer,
                              stop_answer, arrival_carry, resync):
    """Pure: what mode does the cast-stop actually run in? -> (mode, why, refusal).

    SHIPPED ON BY DEFAULT since 2026-08-25 -- owner's ruling on 8.3f's
    framed decision ("pin it", CANCELWALK.md 8.3g) after two clean
    owner runs -- following --zero-lead's own 2026-08-22 precedent: the
    argparse layer arms it, --no-cast-stop reverts, the module global
    stays None so the pure surface is unchanged.

    `why` is the resolution's provenance, printed at startup so the log
    always says WHY the arm is on or off: 'explicit' (the operator
    named a mode -- the composition matrix rules it, exactly as
    before), 'off' (--no-cast-stop), 'no-zero-lead' (the default
    follows the zero-lead regime it modifies -- without this,
    --no-zero-lead alone would strand the operator on the
    requires-zero-lead refusal), 'lever:<flag>' (the default YIELDS to
    an explicitly armed experiment lever so that run keeps ONE variable
    -- "one change per run" applied to a shipped default; an EXPLICIT
    --cast-stop with that lever still refuses through the matrix), or
    'default' (pin). `refusal` fires on the one contradiction:
    --no-cast-stop alongside an explicit --cast-stop.
    """
    if explicit is not None and no_flag:
        return None, None, (
            "--no-cast-stop and --cast-stop=" + str(explicit) + " contradict "
            "each other. Drop one: bare startup runs the shipped default "
            "(pin, owner's ruling 2026-08-25, CANCELWALK.md 8.3g); "
            "--no-cast-stop runs without any cast-stop; an explicit "
            "--cast-stop names its arm.")
    if explicit is not None:
        return explicit, "explicit", None
    if no_flag:
        return None, "off", None
    if not zero_lead:
        return None, "no-zero-lead", None
    for lever, name in ((cancel_answer, "--cancel-answer"),
                        (stop_answer, "--stop-answer"),
                        (arrival_carry, "--arrival-carry"),
                        (resync, "--resync")):
        if lever:
            return None, "lever:" + name, None
    return "pin", "default", None


def cast_stop_reckon(state, now, step):
    """Pure: where is the player RIGHT NOW, by dead reckoning? -> (point, plane, why).

    Returns (None, None, why) when there is nothing to reckon -- the body
    is believed parked, or nothing trustworthy is in hand. The caller
    sends the pin pair WHOLE OR NOT AT ALL (pin-or-nothing): on a point,
    0x002C then 0x0028; on any refusal, NOTHING, with the why on the
    console line. (Until 2026-08-25 the 0x0028 went out alone on a
    refusal as a safety net -- "a wrong parked belief degrades to a
    snap, never a glide" -- and R10's own run refuted its no-op claim,
    CANCELWALK-F34: at a stop-then-cast the handler answered for the
    still-converging SYNC COPY and warped a genuinely parked body
    167.6 u backward onto it. Q10 prices the trade the other way.)

    THE BELIEFS, each with its owner named:
    - click_moving_at: the click-in-flight latch (CANCELWALK-B1, review
      2026-08-25), armed by the 0x003E arm on EVERY click -- answered or
      refused alike, the client paths it itself either way -- and cleared
      by the next report of either kind (the 0x003D and 0x0047 arms).
      READ here, never written.
    - client_pos/client_pos_at/client_plane: the last ACCEPTED report
      (_take_client_position). Advance only on the accept path, so the
      refused-report hole _resync_verdict documents applies here too and
      gets the same guard: pos_rejects > 0 refuses the reckon -- a
      hard-set computed from a pre-refusal point is "the warp the player
      described" through a new door.
    - kbd_moving_at: the locally-driving latch, armed by the 0x003D arm
      and cleared by the 0x0047 arm, touched in no third place -- READ
      here, never written.
    - heading/heading_mt: the last report's vec2 and movementType.
    - cast_stop_pin: OUR OWN note, written at each pin send. A pin newer
      than the last report means WE parked the body and the client has
      said nothing since (the halt is never reported, R8) -- reckoning
      from the stale pre-pin report would extrapolate a leg the body
      never walked, which is exactly R8's second-cast trap.
    """
    # COLLISION_STEP stays in authsrv.py -- eight other readers there, and
    # studies/movecode/review/modelleg.py reads it off the module. It arrives
    # as `step`, read at call time by the wrapper (never defaulted at def
    # time), and is named back here so the clip call below stays verbatim.
    COLLISION_STEP = step
    # B1's door, FIRST -- ahead even of "no-report". Under pin-or-nothing
    # (F34) every refusal now suppresses the whole cast-stop, so the
    # precedence no longer changes what goes on the wire -- but it still
    # changes what the capture SAYS: a click-walk cast must score
    # "click-walk", the regime where the body is provably moving and
    # unplaceable (the client paths it and reports NO position -- 37 s of
    # measured silence; under --grant-suppress its sync copy sits parked
    # at the click leg's start, corpus separation p50 1,164 u, max
    # 3,648 u), never "no-report" or "parked". The live send site also
    # consults the same latch before EITHER arm -- the halt arm has no
    # reckon, so the site check is what protects it -- and never reaches
    # this door; it exists so an offline replay of the pure policy
    # scores a click-walk cast the way the wire behaved.
    if state.get("click_moving_at") is not None:
        return None, None, "click-walk"
    pos, at = state.get("client_pos"), state.get("client_pos_at")
    plane = state.get("client_plane")
    if pos is None or at is None or not isinstance(plane, int):
        return None, None, "no-report"
    if state.get("pos_rejects", 0) > 0:
        return None, None, "report-refused"
    pin = state.get("cast_stop_pin")
    if pin is not None and pin[0] >= at:
        return None, None, "pinned-parked"
    if state.get("kbd_moving_at") is None:
        return None, None, "parked"
    heading = state.get("heading")
    if heading is None:
        return None, None, "no-heading"
    mag = math.hypot(heading[0], heading[1])
    if mag <= 0.0:
        return None, None, "degenerate-heading"
    dt = now - at
    if dt < 0.0:
        return None, None, "future-report"
    # B2 (review 2026-08-25): the rate is the CENSUS FAMILY's, not mt 4's
    # alone. Forward {1,2,3} 284.96 u/s and backward {4,5,6} 187.89 are
    # OBSERVED (movement FINDINGS.md, n=184 and n=114; R8's own mt=4
    # tape read 190.1 at the walk onset, corroborating 0.652 x 288 =
    # 187.8); side {7,8} ~215 u/s is the census's weak row (n=48) and
    # 0.75 is LABELLED, not OBSERVED. The table this replaces -- mt 4 =
    # 0.66, everything else 1.0 -- reckoned a kiting or strafing cast at
    # 288 and hard-set the body FORWARD past the registered 35 u bar
    # (overshoot ~45 u typical, 130-180 u at the straight-leg report-gap
    # mode), and the registered forward-teleport signature would have
    # blamed a stale belief for a fresh rate error. An mt outside the
    # census's 1..8 has NO observed rate and refuses instead of guessing
    # -- the census says 0 and 9 never appear over 7,988 records, so
    # this door is about a future build, not this one.
    mt = state.get("heading_mt")
    if mt in (1, 2, 3):
        rate = 1.0
    elif mt in (4, 5, 6):
        rate = 0.652
    elif mt in (7, 8):
        rate = 0.75
    else:
        return None, None, "unverified-rate"
    dist = rate * 288.0 * dt
    est = (pos[0] + heading[0] / mag * dist,
           pos[1] + heading[1] / mag * dist)
    # Clip the EXTRAPOLATED segment, from the reported point, against our
    # navmesh -- clip_to_walkable clips from state["pos"] (the blend) and
    # this leg starts at the report, so the primitive is used directly.
    #
    # R2 (review 2026-08-25): a wire consumer gets NO standing-outside
    # suspension. clip_to_walkable may keep integrating when the start is
    # off the mesh because its output feeds only state["dest"], the
    # server's private model; here the same suspension would ship a raw
    # unclipped ray -- up to ~3.7 k u -- into a hard-set of BOTH copies,
    # from exactly the positions (5.5% of stops, mesh edges) where our
    # trapezoids are known-wrong. The honest degradation for a hard-set
    # is refusal: no mesh in hand, or a reported point the mesh cannot
    # vouch for, sends no 0x002C.
    pm = state.get("pathmap")
    if pm is None:
        return None, None, "no-mesh"
    if not pm.walkable(pos[0], pos[1]):
        return None, None, "off-mesh"
    why = "reckoned"
    if dist > 0.0:
        clipped = pm.clip(pos[0], pos[1], est[0], est[1],
                          step=COLLISION_STEP)
        if clipped != est:
            est, why = clipped, "reckoned:clipped"
    # R1 (review 2026-08-25): the plane is resolved AT the extrapolated
    # point, never copied from the report. The 0x002C's slot 2 becomes
    # the client's own current plane (agent+0x80), and pairing a reckoned
    # position with the plane of a point up to a report-gap behind it
    # splits a "position and plane are one fact" invariant that --resync
    # never breaks (its payload is the report itself); the click arm
    # documents a stale value in that slot as active corruption, with
    # fall-through-under-stairs as the symptom. plane_at prefers the
    # reported plane where the trapezoids allow it (189 of 198 reports
    # agree with the geometry) and returns None where it cannot say --
    # which refuses, like every other door.
    resolved = pm.plane_at(est[0], est[1], prefer=plane)
    if resolved is None:
        return None, None, "no-plane"
    return est, resolved, why


def parse_stop_answer(text):
    """Pure: an --stop-answer argument -> (mode, refusal).

    Returns (mode, refusal): mode None or "ack"; refusal None or the
    SystemExit text. Same contract as parse_cancel_answer, for the same
    reason: a mistyped arm must refuse loudly rather than run the shipped
    default while the operator's log says an experiment was on.
    """
    if text is None:
        return None, None
    if text == "ack":
        return "ack", None
    if text == "repin":
        return None, (
            "--stop-answer=repin is DELIBERATELY UNBUILT. Answering ordinary "
            "stops with 0x002B [1.0, 9] + a zero-distance 0x0029 is the "
            "refuted --stop-echo's wire effect (a stop-arm 0x0029, "
            "authsrv.py's ZERO_LEAD_REFUSED_ARMS) wearing R6's name -- R4's "
            "`,stop` was licensed by scoping to an in-flight cancel leg, and "
            "an ordinary pre-cast stop cannot be scoped that way. Run "
            "--stop-answer=ack first (CANCELWALK-R6's registered arm); if it "
            "freezes and the repin form is still wanted, it needs its own "
            "licensing paragraph in studies/movement/CANCELWALK.md before "
            "any code.")
    return None, (
        f"--stop-answer={text!r} names no arm. The one built arm is 'ack' "
        f"(CANCELWALK-R6: s2c 0x0028 [agent] answering every player 0x0047) "
        f"-- studies/movement/CANCELWALK.md sec.7.4.")


def parse_cancel_answer(text):
    """Pure: an --cancel-answer argument -> (mode, lead, stop) or a refusal.

    Returns (mode, lead, stop, refusal): mode in (None, "suppress", "lead"),
    lead None or a positive float, stop bool (the `,stop` modifier), refusal
    None or the SystemExit text. Refusals are loud because a mistyped arm
    would otherwise run the shipped default while the operator's log said an
    experiment was on -- the exact defect zero_lead_composition() exists to
    refuse (an inert flag scored as a run).
    """
    if text is None:
        return None, None, False, None
    stop = False
    if text.endswith(",stop"):
        stop, text = True, text[:-5]
    if text == "suppress":
        if stop:
            return None, None, False, (
                "--cancel-answer=suppress,stop: the stop modifier answers a "
                "release DURING a granted cancel leg, and suppress grants no "
                "leg -- there is nothing for it to stop. Passed together it "
                "would be inert while the run log said R4 was on. Use "
                "'retail-lead,stop' or 'lead:<units>,stop'.")
        return "suppress", None, False, None
    if text == "retail-lead":
        return "lead", None, stop, None
    if text.startswith("lead:"):
        try:
            lead = float(text[5:])
        except ValueError:
            lead = None
        if lead is None or not (0.0 < lead <= 768.5):
            return None, None, False, (
                f"--cancel-answer={text}: the lead must be a number of units "
                f"in (0, 768.5] -- 768.5 is retail's own |vec2| + 0.5 ceiling "
                f"and 0 is the shipped zero-lead answer, which needs no flag.")
        return "lead", lead, stop, None
    return None, None, False, (
        f"--cancel-answer={text!r} names no arm. The arms are 'suppress', "
        f"'retail-lead' and 'lead:<units>', each lead form optionally "
        f"'+ ,stop' (R4) -- studies/movement/CANCELWALK.md 5.")


def cancelwalk_lead_dest(reported, heading, lead=None):
    """Pure: the cancel-instant destination for the lead arms.

    `reported` and `heading` are the client's own 0x003D slots 1 and 3;
    `lead` None means retail's expression -- the full vec2 plus 0.5 u along
    it, which is REALFIX's D1 confirmed at cancel instants 3 of 3
    (CANCELWALK-F2: granted y = reported y + vec2 y + 0.5*unit y, exact).
    A degenerate heading returns the reported point: a zero vector names no
    direction, and inventing one would put a fabricated leg on the wire.
    """
    mag = math.hypot(heading[0], heading[1])
    if mag <= 1e-6:
        return [float(reported[0]), float(reported[1])]
    ux, uy = heading[0] / mag, heading[1] / mag
    dist = (mag + 0.5) if lead is None else float(lead)
    return [float(reported[0]) + dist * ux, float(reported[1]) + dist * uy]
