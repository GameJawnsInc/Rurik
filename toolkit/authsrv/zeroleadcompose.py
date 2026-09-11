"""The movement-flag composition matrix -- which arms refuse each other, and why.

ONE PURE FUNCTION AND THE TABLE IT READS. Nothing here opens a socket, sends a
message or knows an opcode. `authsrv.py`'s `main()` calls it once with the flags
it parsed out of argv and raises `SystemExit` on the refusal it hands back; that
call site is the half the matrix cannot reach, and `test_position_trust.py` pins
it, because a refusal nobody RAISES is the same wish as a refusal nobody has
seen fire.

WHY A MODULE. 684 lines of `authsrv.py` were this one decision -- a 667-line
function whose own docstring is 87 of them. Every cell carries the run it came
out of, the arm it refutes and the date the owner ruled, which is why it is long
and why none of it may be reflowed: `test_cancelwalk.py`, `test_d1lead.py`,
`test_familyrate.py`, `test_pcspoof.py`, `test_planerepair.py` and
`test_position_trust.py` assert the refusal strings verbatim, and
`test_router.py` reads the nine `if router and ...` gates out of THIS file's
source text.

WHAT STAYED IN `authsrv.py`, because a moved comment's referent does not move
with it:

  * The flag globals -- `ZERO_LEAD`, `D1_LEAD`, `RESYNC`, `CAST_STOP` and the
    rest. `main()` rebinds them through `global` AFTER this function has ruled,
    and several are pinned as literal `NAME = value` lines.

  * The four shipped constants the refusal text quotes: `GRANT_MIN_INTERVAL`,
    `PC_SPOOF_GAP`, `PLANE_REPAIR_HOLD` and `RESYNC_SEPARATION`. They arrive as
    REQUIRED keyword-only parameters spelled in their own upper case, so the
    body below reads exactly as it did in `authsrv.py`, and the wrapper there
    reads them AT THE CALL. They have no defaults on purpose: a default is
    evaluated at `def` time, and `--resync-separation` rebinds
    `RESYNC_SEPARATION` inside `main()`, so an import-time default would freeze
    the very lever whose refusal this function writes.

  * The three refuted send sites the table cites by line -- `authsrv.py:1049`
    (heading grant), `:1090` (client endpoint) and `:1004` (stop echo). None of
    them moved, so those citations still resolve.

Standard library only, and NO import of the server: `authsrv.py` imports this
file, never the other way round -- it runs as `__main__`, so an import back
would load a second copy whose flags `main()` never set.
"""
import math


# The OTHER arms that put a player 0x0029 on the wire off the movement path.
# Each row is (flag, the trigger it answers, the line its refutation is
# recorded at, what it grants). The refusal below is built FROM this table, so
# a message about one flag cites that flag's own line -- an earlier version
# hard-coded ":1049 and :1090" and said "all of them" whatever was passed, so a
# refusal about --client-endpoint alone offered --heading-grant's line as its
# ground.
ZERO_LEAD_REFUSED_ARMS = (
    ("--heading-grant", "0x003D", "1049",
     "the client's own endpoint through OUR clip, 766 u ahead"),
    ("--client-endpoint", "0x003D", "1090",
     "the client's own endpoint unclipped, 766 u ahead"),
    ("--stop-echo", "0x0047", "1004",
     "a zero-distance echo on a move-cancel"),
)


def zero_lead_composition(zero_lead=False, heading_grant=False,
                          client_endpoint=False, grant_suppress=False,
                          resync=False, stop_echo=False, click_sweep=False,
                          plane_carry=False, arrival_carry=False,
                          cancel_answer=None, stop_answer=None,
                          cast_stop=False, resync_separation=None,
                          family_rate_probe=False, checksum_probe=None,
                          pc_spoof=None, d1_lead=False, router=False,
                          interact_walk=False, move_speed_effects=False,
                          plane_repair=False, *,
                          GRANT_MIN_INTERVAL, PC_SPOOF_GAP,
                          PLANE_REPAIR_HOLD, RESYNC_SEPARATION):
    """Pure: may these movement flags run together, and what must be said?

    Returns (refusal, notes). `refusal` is None or the text main() raises as a
    SystemExit; `notes` are the startup lines for the combinations that ARE
    allowed. Pure and argv-free so the composition matrix is a test rather than
    a paragraph -- `--explorable`/`--outpost` refuse inline and nothing checks
    them, and a refusal nobody has seen fire is a wish.

    REFUSED: every flag in ZERO_LEAD_REFUSED_ARMS. The shared ground is not
    "the same opcode" but the same WIRE EFFECT: each of them answers the
    player's own movement with a player `0x0029` of its own, and every one of
    those stamps the ONE shared grant clock (`grant_at`, stamped inside send()
    for every player 0x0029 whatever sent it), so the client would hold two
    granted destinations and each arm would starve the other inside
    GRANT_MIN_INTERVAL. A run so configured could attribute its outcome to
    neither. All three are REFUTED besides.

    --stop-echo IS ON THAT LIST AND WAS MISSING FROM IT UNTIL 2026-08-21, which
    is the failure this whole function exists to prevent: an adversarial pass
    found `--zero-lead --stop-echo` allowed SILENTLY while REALFIX-P2's own
    spec block forbids it in capitals ("NO STOP-ARM GRANT. That is --stop-echo
    and it is REFUTED"). It answers 0x0047 rather than 0x003D, which is exactly
    why a refusal keyed on "the same 0x003D" did not see it.

    ALLOWED WITH A NOTE: --grant-suppress, because the arms are orthogonal --
    that flag governs CLICK grants and this one governs HEADING grants. They do
    share one rate-limit clock, so the note says the click arm will be quieter
    than it is alone rather than pretending the two are independent.

    ALLOWED WITH A NOTE: --resync, a different opcode (0x002C hard-sets BOTH
    copies) on a different trigger -- but a second uncontrolled variable in an
    A/B built for one, so the note says to prefer one arm at a time.

    ALLOWED WITH A NOTE: the plane repair (on by default) beside --resync or
    --cast-stop=pin. All three can put a 0x002C on the wire, and "one 0x002C
    policy per run" is the pin/resync refusal's ground -- but the repair fires
    only on the frozen-impossible-plane lock signature, a regime neither
    policy occupies (the pin needs a cast, the resync needs modelled
    separation, and a frozen client in agreement with its model has none),
    and its sends are labelled PLANE-REPAIR, so a hard-set in the capture
    still attributes to exactly one policy by its label. The note exists so
    a run reading its own capture knows a third labelled sender is armed.

    ALLOWED WITH A NOTE: --click-sweep, and it is allowed for the same reason
    --resync is rather than because it is harmless. It is a CLICK-arm
    diagnostic, not a refuted movement policy, so refusing it would be refusing
    a diagnostic; but it deliberately sends plane assignments it knows to be
    wrong, and a wrong plane writes a wrong map index into agent+0x80. On
    REALFIX-L1's own click-free protocol it is inert, and if it is NOT inert
    the run was not click-free. The note says both halves.

    REFUSED IN THE OTHER DIRECTION: --plane-carry WITHOUT --zero-lead.
    REALFIX-F1 is a MODIFIER on the zero-lead send site and has no send site of
    its own, so with --zero-lead off it changes nothing whatsoever -- and that
    is precisely why it refuses rather than shrugging. The choice was between
    "refuse it" and "document it as inert", and the grounds for refusing are
    this file's own history: `--zero-lead --stop-echo` was accepted SILENTLY
    for a day while the spec forbade it in capitals, and the lesson booked
    there was that a flag combination nobody refuses is a flag combination
    somebody runs. An inert --plane-carry is worse than that one, not better:
    the server would behave EXACTLY like the shipped default while the
    operator's run log said "F1 arm", so the run would be scored as a fix that
    was never applied and its null would be published against REALFIX-F1's
    prediction. A refusal costs one restart and names the missing flag; an
    inert flag costs a live session and a wrong entry in the record. The other
    direction is deliberately NOT symmetric -- --zero-lead alone is the P2 arm
    and is the control this fix is measured against, so it must keep running
    alone.

    REFUSED, AND THIS ONE IS SYMMETRIC: --plane-carry WITH --arrival-carry.
    REALFIX-F1 and REALFIX-F1b are two policies for ONE wire field (field 4,
    the plane written to agent+0x80 on the SYNC copy). Whichever the code ran,
    the other would be silently inert, and the run would be scored against
    whichever prediction the operator remembered -- the two flags print two
    DIFFERENT pre-registered banners, so a run carrying both prints two
    predictions and can satisfy neither honestly. F1b exists precisely because
    F1's own falsifier fired at 5 of 93, so the pair is also the A/B that
    matters most to keep clean. Refused before the --arrival-carry-needs-
    --zero-lead check below, because "you passed two field-4 policies" is the
    more useful thing to be told when someone passes all three.

    REFUSED IN THE OTHER DIRECTION, same as F1: --arrival-carry WITHOUT
    --zero-lead, for the identical reason and with the identical history behind
    it -- F1b is a MODIFIER on the zero-lead send site with no send site of its
    own, and an inert flag whose run log says "F1b arm" would publish a null
    against F1b's prediction that the fix never earned.
    """
    # cast_stop is a MODE STRING or off -- never the legacy bool. True (the
    # pre-R10 form) armed every shared refusal cell on truthiness while
    # matching neither mode: no startup note, and the pin-x-resync cell
    # dead -- an on-but-unnamed arm, the same defect this function refuses
    # everywhere else. main() cannot produce True (parse_cast_stop yields
    # only None/'halt'/'pin'); this guard is for every OTHER caller. Found
    # by the 2026-08-25 re-review's lattice sweep.
    if cast_stop not in (None, False, "halt", "pin"):
        raise ValueError(
            f"cast_stop={cast_stop!r}: pass 'halt', 'pin', or None/False. "
            f"A truthy non-mode value arms the shared refusal cells while "
            f"matching neither mode's note nor the pin-specific cell.")
    if plane_carry and arrival_carry:
        return ("--plane-carry and --arrival-carry cannot run together. They "
                "are TWO POLICIES FOR ONE WIRE FIELD -- field 4 of the "
                "zero-lead 0x0029, the plane the client writes to agent+0x80 "
                "on the SYNC copy. REALFIX-F1 carries the PREVIOUS GRANT'S "
                "plane; REALFIX-F1b carries the plane of the grant the copy "
                "has ARRIVED at. Whichever one the send site read, the other "
                "would be inert -- and both print their own pre-registered "
                "prediction at startup, so a server carrying both announces "
                "two predictions and can honestly satisfy neither. F1b exists "
                "BECAUSE F1's primary falsifier fired (5 of 93 grants still "
                "mismatched, every one of them F1's own named two-interval "
                "limit), so this is the one A/B in the arc that most needs to "
                "stay clean. Pass --zero-lead --plane-carry for the F1 arm, "
                "--zero-lead --arrival-carry for the F1b arm, or --zero-lead "
                "alone for the P2 control both are measured against."), []
    # The cast_stop pairwise cells sit ABOVE the requires-zero-lead checks,
    # like the plane/arrival pair and for its reason: "you passed two
    # levers" is the more useful thing to be told, and a requires-zero-lead
    # refusal here would hand out advice (--zero-lead --arrival-carry) that
    # the pairwise cell below would then refuse on the next restart -- an
    # adversarial pass caught exactly that with the arrival cell placed low.
    if cast_stop and cancel_answer:
        return ("--cast-stop and --cancel-answer cannot run together. R8's "
                "readout is the body's motion across the CAST START and the "
                "cancel arms change the answer at the CANCEL instant -- two "
                "levers in one run, and a halt (or a walk, or a freeze) "
                "could be attributed to neither. One change per run is this "
                "arc's own rule (CANCELWALK.md sec.5). Run --cast-stop "
                "alone."), []
    if cast_stop and stop_answer:
        return ("--cast-stop and --stop-answer cannot run together. Both "
                "send the SAME opcode (s2c 0x0028 AGENT_STOP_MOVING) on "
                "different triggers -- every free-caster non-attack cast "
                "start vs every player 0x0047 stop -- so the capture could "
                "not attribute any halt, or any freeze/walk change, to one "
                "lever. One change per run (CANCELWALK.md sec.5). Run them "
                "in separate sessions."), []
    if cast_stop and arrival_carry:
        return ("--cast-stop and --arrival-carry cannot run together. The "
                "cast-start 0x0028 halts BOTH world copies mid-leg when the "
                "body is in motion, so a grant the F1b queue modelled as "
                "arriving never arrives -- the queue would carry an arrival "
                "plane for a leg the halt cut short, and a snap it caused "
                "would be attributed to the wrong arm. One diagnostic at a "
                "time; R8/R10 are pre-registered against the shipped default "
                "(--zero-lead --plane-carry) and nothing else."), []
    if cast_stop == "pin" and resync:
        return ("--cast-stop=pin and --resync cannot run together. Both "
                "send the SAME opcode (s2c 0x002C AGENT_UPDATE_POSITION, "
                "the hard-set of both copies) under two different policies "
                "-- the pin's dead-reckoned cast-start re-pin vs the "
                "drift-triggered resync of the client's own report -- so "
                "any hard-set in the capture could be attributed to "
                "neither, and their position models would fight (the pin "
                "extrapolates PAST the last report; the resync teleports "
                "BACK to it). One 0x002C policy per run. --cast-stop=halt "
                "composes with --resync as before (different opcodes)."), []
    if arrival_carry and not zero_lead:
        return ("--arrival-carry requires --zero-lead. REALFIX-F1b is a "
                "MODIFIER on the zero-lead grant, not a policy of its own: it "
                "changes ONE field of the 0x0029 that the --zero-lead block "
                "sends (field 4, the plane written to agent+0x80 on the SYNC "
                "copy), and there is no other send site in this file that "
                "reads it. Passed alone it would change NOTHING, and a server "
                "behaving exactly like the shipped default while the run log "
                "says 'F1b arm' is how a fix gets credited with a null it "
                "never earned -- the same refusal --plane-carry already "
                "carries, for the same reason, after --zero-lead --stop-echo "
                "was once accepted SILENTLY. Pass --zero-lead --arrival-carry "
                "for the F1b arm, or --zero-lead alone for the P2 arm it is "
                "measured against."), []
    if plane_carry and not zero_lead:
        return ("--plane-carry requires --zero-lead. REALFIX-F1 is a MODIFIER "
                "on the zero-lead grant, not a policy of its own: it changes "
                "ONE field of the 0x0029 that the --zero-lead block sends "
                "(field 4, the plane written to agent+0x80 on the SYNC copy), "
                "and there is no other send site in this file that reads it. "
                "Passed alone it would change NOTHING, and a server behaving "
                "exactly like the shipped default while the run log says 'F1 "
                "arm' is how a fix gets credited with a null it never earned. "
                "Refused loudly rather than documented as inert, because "
                "--zero-lead --stop-echo was once accepted SILENTLY and that "
                "is the failure this function exists for. Pass "
                "--zero-lead --plane-carry for the F1 arm, or --zero-lead "
                "alone for the P2 arm it is measured against."), []
    if cancel_answer and arrival_carry:
        return ("--cancel-answer and --arrival-carry cannot run together. "
                "The lead arms send a 0x0029 whose point is NOT the reported "
                "position, while F1b's arrival queue models every zero-lead "
                "grant as bound for the reported point -- so the copy's "
                "modelled arrival would be a lie for exactly the instant the "
                "experiment exists to read, and the suppress arm starves the "
                "queue an entry it believes it armed. One diagnostic at a "
                "time; CANCELWALK's runs are pre-registered against the "
                "shipped default (--zero-lead --plane-carry) and nothing "
                "else."), []
    if stop_answer and cancel_answer:
        # Pairwise BEFORE either flag's requires-zero-lead check, for the
        # reason the plane/arrival pair's docstring states: "you passed two
        # experiment levers" is the more useful thing to be told when
        # someone passes all three.
        return ("--stop-answer and --cancel-answer cannot run together. "
                "R6 exists to test whether closing the PRE-CAST stop "
                "retail's way un-freezes the SHIPPED cancel-instant answer "
                "-- its prediction is registered against the shipped "
                "zero-lead cancel behaviour, and a run that also changes "
                "the cancel-instant answer could attribute a walk (or a "
                "freeze) to neither lever. One change per run is this "
                "arc's own rule (CANCELWALK.md sec.5). Run "
                "--stop-answer=ack alone."), []
    if family_rate_probe and cancel_answer:
        # Pairwise BEFORE the requires-zero-lead cells, per the plane/arrival
        # precedent: "you passed two levers" is the more useful refusal --
        # and test_familyrate.py sec.5 drives exactly this ordering, because
        # the first draft placed this cell below cancel-answer's requires
        # cell and the wrong refusal fired.
        return ("--family-rate-probe and --cancel-answer cannot run "
                "together. The cancel lead arms send their own 0x002B "
                "hardcoding [1.0, movementType] at the cancel instant, "
                "against the probe's FAMILY_RATE float on the same report "
                "stream -- TWO POLICIES FOR ONE CLIENT FIELD (sync +0x60), "
                "and a movetap row could attribute its movespeed to "
                "neither. The suppress arm sends no 0x002B but is one "
                "experiment lever too many for a probe run: one change per "
                "run (CANCELWALK.md sec.5). REALFIX-A1's protocol is the "
                "probe alone on shipped defaults."), []
    if family_rate_probe and checksum_probe:
        # The 2026-08-25 review's find: --checksum-probe was never in this
        # matrix (correct for a flag whose handler logs and returns 1), so
        # the pair ran unrefused and put an 0x0023 -- an opcode retail
        # sends ZERO times in 137 live files -- into the probe's burst,
        # breaking the witnessed-shape ground the slot was chosen for.
        return ("--family-rate-probe and --checksum-probe cannot run "
                "together. The checksum's 0x0023 rides the same report "
                "breath ungated on the zero-lead verdict, so the burst "
                "becomes 0x0023+0x0025+0x002B+0x0029 -- a shape retail "
                "has never produced (0x0023 appears zero times in 137 "
                "live files). It cannot touch the movespeed readout, but "
                "one diagnostic per run is the arc's own rule, and A1's "
                "burst-shape claim is part of its registration. Run them "
                "in separate sessions."), []
    if pc_spoof is not None and cancel_answer:
        # Pairwise BEFORE the requires-zero-lead cells, same precedent as the
        # family-rate pair above.
        return ("--pc-spoof and --cancel-answer cannot run together. The "
                "cancel lead arms ride the SAME single 0x0029 send site "
                "whose field 4 the spoof rewrites, so a lead grant fired "
                "past the park gap would go out with a spoofed plane AND a "
                "led point -- a two-variable instant in a cell registered "
                "for one (REALFIX sec.0.7: the press's own grant, a PARKED "
                "copy, one flipped word). Run the cell click-free and "
                "cancel-free."), []
    if d1_lead and cancel_answer:
        # A2's pairwise cells, all BEFORE the requires-zero-lead family,
        # per the ordering precedent test_familyrate sec.5 drives.
        return ("--d1-lead and --cancel-answer cannot run together. The "
                "cancel lead arms swap the point at the SAME single 0x0029 "
                "send site A2's lead patches, and the `,stop` modifier "
                "fires the SAME stop-repin shape at the SAME 0x0047 site "
                "A2 generalizes -- two policies for one destination and "
                "two for one stop reply. A2's protocol is cancel-free "
                "(REALFIX.md sec.0.9)."), []
    if d1_lead and family_rate_probe:
        return ("--d1-lead and --family-rate-probe cannot run together. "
                "A2 embeds the family-rate send as POLICY (edge-triggered, "
                "one 0x002B per family change) and the probe doses it on "
                "every granted report -- two dosing policies for one "
                "client field (sync +0x60), and a movetap row could "
                "attribute its movespeed to neither. A1's probe run is "
                "complete (Q6 CLOSED); run A2 alone."), []
    if d1_lead and checksum_probe:
        return ("--d1-lead and --checksum-probe cannot run together. The "
                "checksum's 0x0023 rides the report breath ungated and "
                "breaks the witnessed burst shape A2's registration "
                "depends on (0x0025 -> 0x002B -> 0x0029, 0x0029 last in "
                "3,023 of 3,071) -- the same burst-purity ground as the "
                "A1 pairwise cell. Separate sessions."), []
    if d1_lead and pc_spoof is not None:
        return ("--d1-lead and --pc-spoof cannot run together. The spoof "
                "is a field-4 EXPERIMENT (a deliberately wrong plane word "
                "once per park) inside the field-4 POLICY A2 ships "
                "(plane-carry, retail's own one-grant-lag pattern) -- a "
                "warp in such a run could attribute to either. The spoof's "
                "own cell record is REALFIX sec.0.8; run it alone."), []
    if d1_lead and stop_answer:
        return ("--d1-lead and --stop-answer cannot run together. Both "
                "answer the SAME 0x0047: A2 with retail's dominant reply "
                "(0x002B [1.0,9] + zero-distance 0x0029, 134/172 live "
                "stops), --stop-answer=ack with the minority bare 0x0028 "
                "(6.1%) that F34 measured warping a parked body 167.6 u "
                "mid-convergence -- exactly the copy-mid-leg state A2's "
                "lead creates more of. Two stop replies cannot share a "
                "run."), []
    if d1_lead and arrival_carry:
        return ("--d1-lead and --arrival-carry cannot run together. A2's "
                "plane-truth term IS --plane-carry (the 306-crossing "
                "census: retail's field 4 shows the one-grant lag, 79.7% "
                "dominant), and plane-carry and arrival-carry are already "
                "mutually exclusive -- they write the same wire field. "
                "The bundle chose F1; F1b stays a separate arm."), []
    if d1_lead and click_sweep:
        return ("--d1-lead and --click-sweep cannot run together. The "
                "sweep deliberately sends WRONG plane assignments and its "
                "click grants stamp the shared grant clock -- a wrong "
                "plane word inside A2's plane-truth run un-attributes any "
                "snap, and A2's protocol is click-free besides."), []
    if router and click_sweep:
        return ("--router and --click-sweep cannot run together. The sweep "
                "deliberately sends wrong plane words through the click "
                "channel the router now owns -- two plane policies for one "
                "send site, and the sweep's diagnostic question (which "
                "plane pair the client accepts) is unanswerable when a "
                "chain interleaves its own grants."), []
    if router and arrival_carry:
        return ("--router and --arrival-carry cannot run together. Both "
                "write wire field 4 on click answers -- arrival-carry from "
                "its arrival queue, the router from per-waypoint plane_at "
                "-- and a chain of grants would drain the carry queue "
                "against destinations it never modelled."), []
    if router and cancel_answer:
        return ("--router and --cancel-answer cannot run together. The "
                "cancel lead arms swap points at the one 0x0029 send site "
                "mid-experiment, and the router's chain grants add 0x0029s "
                "of their own -- a warp in such a run could attribute to "
                "either. Run the CANCELWALK arms click-free, as their own "
                "protocol already says."), []
    if router and stop_answer:
        return ("--router and --stop-answer cannot run together. The stop "
                "experiments are pre-registered against the SHIPPED click "
                "regime and a chain changes what a stop interrupts -- the "
                "readout would answer a question nobody registered."), []
    if router and family_rate_probe:
        return ("--router and --family-rate-probe cannot run together. The "
                "probe doses 0x002B on every granted report; the router's "
                "chain grammar is ONE 0x002B per chain (retail's own, "
                "ROUTER.md sec.1) -- two dosing policies for one client "
                "field (sync +0x60)."), []
    if router and checksum_probe:
        return ("--router and --checksum-probe cannot run together. The "
                "checksum's 0x0023 rides the report breath ungated and a "
                "chain's burst shape (one 0x002B, then bare 0x0029s at leg "
                "cadence) is the thing the router run exists to exhibit -- "
                "same burst-purity ground as the A1/A2 cells."), []
    if router and pc_spoof is not None:
        return ("--router and --pc-spoof cannot run together. The spoof is "
                "a field-4 EXPERIMENT inside what is now a field-4 POLICY "
                "(per-waypoint planes, matched) -- a warp in such a run "
                "could attribute to either. Run the spoof's cell alone, as "
                "its record already says."), []
    if router and interact_walk:
        return ("--router and --interact-walk cannot run together (review "
                "F2, 2026-08-26). An interact on an out-of-range NPC sends "
                "a 0x002A straight-line walk order while a live chain "
                "keeps granting 0x0029 legs at cadence -- two movement "
                "orders fighting for one body, the client re-aimed at the "
                "stale route within a second. The interact walk's own "
                "banner already calls it broken; a chain makes it a "
                "two-sender fight besides."), []
    if router and move_speed_effects:
        return ("--router and --move-speed-effects cannot run together "
                "(review F7, 2026-08-26). Chain ETAs are computed at "
                "DEFAULT_RUN_SPEED; an effect episode changes the client's "
                "real speed mid-chain, so a snared client receives leg n+1 "
                "MID-LEG and turns onto a straight line to the next "
                "waypoint that no clip ever sampled -- corner-cutting "
                "across unvetted ground, the F1 shape without the thin "
                "wall. A boosted client parks at every waypoint instead, "
                "which would read as the cadence model failing. Route or "
                "dose speed; not both."), []
    if cancel_answer and not zero_lead:
        return ("--cancel-answer requires --zero-lead. The CANCELWALK arms "
                "are MODIFIERS on the zero-lead answer to the one report "
                "whose cancel_on_move released a held action -- suppress "
                "withholds that answer, the lead arms change its point -- and "
                "with --zero-lead off there is no such answer to modify. "
                "Passed alone it would change NOTHING while the run log said "
                "a CANCELWALK arm was on, which is the inert-flag defect "
                "--plane-carry's refusal documents. Pass --zero-lead (or "
                "nothing: it is the default) with --cancel-answer."), []
    if stop_answer and not zero_lead:
        return ("--stop-answer requires --zero-lead. CANCELWALK-R6 is "
                "pre-registered against the SHIPPED configuration -- the "
                "freeze must reproduce for the readout to mean anything, "
                "and the freeze is a zero-lead measurement (F6). Under any "
                "other grant policy the run answers a question nobody "
                "registered. Pass --zero-lead (or nothing: it is the "
                "default) with --stop-answer."), []
    if cast_stop and not zero_lead:
        return ("--cast-stop requires --zero-lead. CANCELWALK-R8 is "
                "pre-registered against the SHIPPED configuration -- F28's "
                "float-forward was measured under it, and under any other "
                "grant policy the run answers a question nobody registered. "
                "Pass --zero-lead (or nothing: it is the default) with "
                "--cast-stop."), []
    if family_rate_probe and not zero_lead:
        return ("--family-rate-probe requires --zero-lead. The probe's send "
                "is gated on the zero-lead grant verdict so every 0x002B "
                "lands inside a witnessed retail burst shape (0x0029 last, "
                "3,023 of 3,071) -- with --no-zero-lead that verdict never "
                "fires and the probe would send NOTHING while the run log "
                "said REALFIX-A1 was armed, publishing a null the probe "
                "never earned: the inert-flag defect --plane-carry's "
                "refusal documents. Pass --zero-lead (or nothing: it is "
                "the default) with --family-rate-probe."), []
    if pc_spoof is not None and not zero_lead:
        return ("--pc-spoof requires --zero-lead. The spoof rides the "
                "zero-lead grant's own field 4 and its trigger reads that "
                "verdict's gap clock (since_last) -- with --no-zero-lead "
                "there is no send site and no clock, so the flag would "
                "change NOTHING while the run log said the cell was armed: "
                "the inert-flag defect --plane-carry's refusal documents. "
                "Pass --zero-lead (or nothing: it is the default) with "
                "--pc-spoof."), []
    if d1_lead and not zero_lead:
        return ("--d1-lead requires --zero-lead. A2 is a MODIFIER on the "
                "zero-lead heading arm -- its lead swaps the point at that "
                "arm's one send site, its speed truth rides that arm's "
                "burst slot, and its stop-repin generalizes that regime's "
                "stop handling. With --no-zero-lead there is no site, no "
                "slot and no verdict gate: the flag would change NOTHING "
                "while the run log said REALFIX-A2 was armed -- the "
                "inert-flag defect --plane-carry's refusal documents. Pass "
                "--zero-lead (or nothing: it is the default) with "
                "--d1-lead."), []
    if d1_lead and not plane_carry:
        return ("--d1-lead requires --plane-carry. Plane truth is term 3 "
                "of the bundle (REALFIX.md sec.0.9): the 306-crossing live "
                "census shows retail's field 4 IS the one-grant-lag "
                "pattern plane-carry ships, and running the lead without "
                "it re-creates the fake-label hazard sec.0.5-0.8 decoded "
                "(a stamped plane whose island does not contain the "
                "copy's ground kills the 100u veto mid-walk). plane-carry "
                "defaults ON with zero-lead; only an explicit "
                "--no-plane-carry lands here, and it should."), []
    if pc_spoof is not None and pc_spoof < 0:
        return (f"--pc-spoof {pc_spoof!r} is not a plane. Plane words are "
                f"non-negative dwords in every decoded report, and the "
                f"client stamps field 4 raw at +0x80 (0x00602A74, no "
                f"compare) -- a negative id puts the copy on ground no "
                f"chain node or navmesh island can name, which answers no "
                f"registered question. Pass the plane id to spoof: 26 while "
                f"standing on plane-0 ground is REALFIX sec.0.7's "
                f"registered cell."), []
    if resync_separation is not None and not resync:
        return ("--resync-separation requires --resync. It is a MODIFIER on "
                "the resync verdict's one distance dial (the modelled "
                "SYNC-vs-client separation at which a 0x002C fires) and has "
                "no send site of its own -- passed alone it changes NOTHING "
                "while the run log says a threshold arm was on, which is the "
                "inert-flag defect --plane-carry's refusal documents. Its "
                "registered use is P8 of studies/movement/followon-notes/"
                "p5-resync-disarm.md sec.8: --resync --resync-separation "
                "2000, the nothing-fires negative control whose job is to "
                "make the snap RETURN. Pass both."), []
    if resync_separation is not None and (
            not math.isfinite(resync_separation) or resync_separation <= 0.0):
        return (f"--resync-separation {resync_separation!r} is not a "
                f"separation. The dial is a distance in units compared >= "
                f"against the modelled SYNC-vs-client gap: zero or less "
                f"fires on EVERY accepted report (a 2 Hz 0x002C stream "
                f"nobody registered), and a non-finite value never fires "
                f"while the log says the flag was on. Pass a positive "
                f"number of units -- {RESYNC_SEPARATION:.1f} is the shipped "
                f"default, 2000.0 the registered P8 control."), []
    if not zero_lead:
        return None, []
    on_flags = {"--heading-grant": heading_grant,
                "--client-endpoint": client_endpoint,
                "--stop-echo": stop_echo}
    clash = [row for row in ZERO_LEAD_REFUSED_ARMS if on_flags[row[0]]]
    if clash:
        def _join(items):
            items = list(items)
            if len(items) < 3:
                return " and ".join(items)
            return ", ".join(items[:-1]) + " and " + items[-1]
        both = _join(row[0] for row in clash)
        lines = _join((f"authsrv.py:{row[2]}" if i == 0 else f":{row[2]}")
                      for i, row in enumerate(clash))
        detail = "; ".join(f"{row[0]} answers {row[1]} with {row[3]}"
                           for row in clash)
        tail = ""
        if any(row[0] == "--stop-echo" for row in clash):
            tail = (" REALFIX-P2's own spec block forbids --stop-echo by name: "
                    "'NO STOP-ARM GRANT.'")
        return (f"--zero-lead cannot be combined with {both}: each of them "
                f"answers the player's own movement with a player 0x0029 of "
                f"its own, and every one of those stamps the SAME grant clock, "
                f"so the client would hold two granted destinations and the "
                f"two arms would starve each other inside the "
                f"{GRANT_MIN_INTERVAL:.2f}s floor. The run would attribute its "
                f"result to neither. ({detail}.) "
                f"{both} {'are' if len(clash) > 1 else 'is'} already REFUTED "
                f"({lines}).{tail} Pass at most one."), []
    notes = []
    if plane_repair and (resync or cast_stop == "pin"):
        notes.append(
            "      + plane repair (default ON): a THIRD possible 0x002C "
            "sender is armed beside this run's 0x002C policy. It fires only "
            "on the frozen-impossible-plane lock signature (accepted 0x003D "
            "reports byte-identical for "
            f"{PLANE_REPAIR_HOLD:.0f}s claiming a plane the mesh does not "
            "offer at that point) -- a regime neither the pin nor the resync "
            "occupies -- and every send is labelled PLANE-REPAIR, so a "
            "hard-set in the capture attributes by label. In a healthy run "
            "it fires ZERO times; pass --no-plane-repair to run the pure "
            "one-policy configuration.")
    if grant_suppress:
        notes.append(
            "      + --grant-suppress: ALLOWED -- orthogonal arms. That flag "
            "governs CLICK grants and this one governs HEADING grants. They "
            "share ONE rate-limit clock (state['grant_at'] is stamped in "
            "send() for every 0x0029 whatever sent it), so between them they "
            f"still cannot exceed one grant per {GRANT_MIN_INTERVAL:.2f}s. "
            "Expect the click arm to be quieter than it is alone, and say "
            "which flags were on when you report the run.")
    if resync:
        notes.append(
            "      + --resync: ALLOWED -- a different opcode (0x002C, which "
            "HARD-SETS both copies) on a different trigger. But it is a second "
            "uncontrolled variable in an A/B built for one: a snap avoided "
            "cannot be attributed between them. Prefer one arm at a time for "
            "REALFIX-L1."
            + ("" if not arrival_carry else
               " WITH --arrival-carry it also INVALIDATES the arrival queue, "
               "which is wired rather than assumed: 0x00602B20's armed arm "
               "clears the arrival tick at 0x006021E6, so the outstanding "
               "grant never arrives and its entry would otherwise come due on "
               "a leg the client abandoned. _note_wire_move drops the queue "
               "and takes the hard set's own plane as the reached one.")
            + ("" if resync_separation is None else
               f" THRESHOLD OVERRIDDEN: this run fires at "
               f"{resync_separation:.1f} u, not the shipped "
               f"{RESYNC_SEPARATION:.1f} u. At 2000.0 this is P8, the "
               f"registered negative control (p5-resync-disarm.md sec.8): "
               f"nothing should fire, and the F35 snap should RETURN -- if "
               f"it does not, a treated arm's zero was never the resync's."))
    if family_rate_probe:
        notes.append(
            "      + --family-rate-probe: ALLOWED -- REALFIX-A1, a 0x002B "
            "[FAMILY_RATE[mt], mt] rides each granted report in retail's "
            "own burst slot. HAZARD, priced: the shipped CLICK grant sites "
            "also send a player 0x002B and hardcode [1.0, 1], overwriting "
            "the probe's float -- inert on A1's click-free protocol "
            "(--grant-suppress already refuses keyboard-mid clicks). "
            "Distinguish by LABEL, not payload: the probe's own forward "
            "sends carry [1.0, 1] too (mt 1 is keyboard-forward -- A1's "
            "run proved it on a click-free c2s census), so the click "
            "signature is a [1.0, 1] send WITHOUT the FAMILY-RATE PROBE "
            "label prefix; one of those between probe sends means the run "
            "was NOT click-free and its movespeed rows are confounded "
            "from that instant. The definitive check is the c2s census: "
            "zero 0x003E rows.")
    if pc_spoof is not None:
        notes.append(
            f"      + --pc-spoof {pc_spoof}: ALLOWED -- REALFIX sec.0.7 "
            f"cell 2's lever. The first fired grant after >= "
            f"{PC_SPOOF_GAP:.1f}s of grant silence sends field 4 = "
            f"{pc_spoof} instead of the carry value, once per park; the "
            f"verdict row marks it pc_spoofed and the wire label appends "
            f"PC-SPOOF. Stand on ground whose plane DIFFERS from the "
            f"spoof or the rep is void (plane_differs false -- the census "
            f"scores it out). One probe per run: prefer this WITHOUT "
            f"--family-rate-probe, so a snap, if one fires, attributes to "
            f"the plane word alone.")
    if d1_lead:
        notes.append(
            "      + --d1-lead: ALLOWED -- REALFIX-A2, THE BUNDLE (sec.0.9): "
            "D1 lead (reported + vec2 + 0.5*unit, the client's own proposed "
            "endpoint, D2-clipped to the navmesh along the report's ray "
            "since sec.0.17 -- the wall-phase fix), edge-triggered 0x002B "
            "speed truth, "
            "plane-carry plane truth, and the retail stop-repin (0x002B "
            "[1.0,9] + zero-distance 0x0029 at every 0x0047, floor-bypassed "
            "as an ack but stamping the one grant clock). Protocol is "
            "CLICK-FREE and CAST-FREE; the registered predictions and "
            "REFUTED-IF lines are in sec.0.9 and on the banner. The "
            "stop-repin is --stop-echo's wire shape rebuilt with its "
            "era-audit ground stated -- if this run warps at a stop, score "
            "it against that ground first.")
    if click_sweep:
        notes.append(
            "      + --click-sweep: ALLOWED -- a CLICK-arm diagnostic, not a "
            "refuted movement policy, so it is not on the refusal list. But it "
            "deliberately sends plane assignments it knows to be WRONG, and a "
            "wrong plane writes a wrong map index into agent+0x80: a snap it "
            "caused would be attributed to --zero-lead. Its click grants also "
            "stamp the shared grant clock and will starve the heading arm. "
            "REALFIX-L1 is CLICK-FREE by protocol, so this flag should be "
            "inert -- and if it is not inert, the run was not click-free.")
    if cancel_answer:
        notes.append(
            f"      + --cancel-answer={cancel_answer}: CANCELWALK arm, "
            f"DIAGNOSTIC ONLY. It changes the answer to the ONE report whose "
            f"cancel_on_move released a cast or stopped a swing; every other "
            f"report is answered exactly as --zero-lead ships. No outcome "
            f"ships from this flag directly -- a PASS licenses a candidate "
            f"for a separate audited step. Predictions and readout: "
            f"studies/movement/CANCELWALK.md 5.")
    if stop_answer:
        notes.append(
            f"      + --stop-answer={stop_answer}: CANCELWALK-R6 arm, "
            f"DIAGNOSTIC ONLY. Adds one s2c 0x0028 [player] answering every "
            f"player 0x0047 stop report -- retail's own bare stop-ack, NOT a "
            f"grant (no destination armed, no grant clock stamped), a no-op "
            f"on a body that already stopped itself ONLY while the sync "
            f"copy is parked too -- F34 (CANCELWALK.md 8.3d) measured "
            f"the same message warping a parked body 167.6 u onto a "
            f"still-converging copy, so this arm's warp exposure is "
            f"nonzero. The cancel-instant "
            f"answer stays exactly as --zero-lead ships. Predictions and "
            f"readout: studies/movement/CANCELWALK.md 7.4.")
    if cast_stop == "halt":
        notes.append(
            "      + --cast-stop=halt: CANCELWALK-R8 arm, DIAGNOSTIC ONLY "
            "and REFUSED AS A SHIP (owner ruling 2026-08-25: it WARPS -- "
            "F31, the halt lands the body on the sync copy, 110-207 u "
            "measured). Kept runnable as R10's control. Adds one s2c "
            "0x0028 [player] at a free-caster non-attack cast start -- "
            "EXCEPT during a click-walk, where the B1 latch suppresses "
            "the halt too (a click-walking body would out-warp F31; the "
            "console's pin:click-walk line is the record -- 8.3b). "
            "NOT a grant: no destination armed, no grant clock stamped. "
            "Predictions and results: studies/movement/CANCELWALK.md 8.")
    elif cast_stop == "pin":
        notes.append(
            "      + --cast-stop=pin: CANCELWALK-R10 arm, the SHIPPED DEFAULT "
            "since 2026-08-25 (owner's ruling, 8.3g; --no-cast-stop "
            "reverts). "
            "PIN-OR-NOTHING (F34, 8.3d): at a free-caster non-attack cast "
            "start, EITHER one s2c 0x002C hard-set at the DEAD-RECKONED "
            "player position (last report + unit(vec2) x census-family "
            "rate x 288 x dt, navmesh-clipped, plane resolved AT the "
            "point) followed by the 0x0028 halt on the now co-located "
            "copies -- OR nothing at all, when any door refuses "
            "(click-walk, parked, pinned, refused report, off-mesh, "
            "no mesh, unresolved plane, unverified rate, no report, "
            "no/degenerate heading, future report), with the reason on the "
            "console line. A bare 0x0028 never fires: its no-op claim "
            "held only when the SYNC COPY was parked too, and R10's run "
            "measured it warping a parked body 167.6 u onto a converging "
            "copy. The 0x002C stamps the sync model but NOT the grant "
            "clock. Predictions and readout: "
            "studies/movement/CANCELWALK.md 8.3e.")
    if router:
        notes.append(
            "      + --router: ROUTER-B2 (studies/movement/ROUTER.md). "
            "Clicks are answered by pathmap.route() -- first leg within "
            "the click's own handling, further legs at leg-completion "
            "cadence, abandon on any 0x003D/0x003E/0x0047 -- and BYPASS "
            "the click tower (no grant_pending, no rate floor; Rule 1's "
            "keyboard drop kept, read straight off the latch). The "
            "keyboard channel (zero-lead, D1 leads, clip, watchdog) is "
            "untouched; with --d1-lead the two compose as the live-run "
            "bundle. Falls back to the shipped click path only where "
            "there is no mesh or no position belief.")
    return None, notes
