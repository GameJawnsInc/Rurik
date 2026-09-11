"""Profession, attributes, morale, title track, faction, level, the character panel.

The character arm of the probe family, lifted verbatim from `probes.py` on
2026-09-11: the level arm and the henchman level arm, the six profession arms,
the attribute panel and its three sweeps, the two morale arms, the regeneration
channel, property 54, the faction maximum, the title track, and the twenty-one
registry entries that fire them. Three of the nine profession entries re-fire
`_profession_steps` with a different id and a different question, and
`profession_spawn` builds nothing at all -- `steps=[]`, an arm read off a
session configured with `--spawn-profession`, which is why `authsrv.py` warns
when it is run without one.

It is leaf shaped by the same rule `probebase.py` is -- standard library plus
`questdefs`, `agents` and `probebase` -- and it MUST NOT import `probes`:
`probes.py` runs as `__main__` under `python toolkit/authsrv/probes.py`, so a
leaf importing it back would load a SECOND copy of that module, with its own
`PROBES` dict and its own flags.

`import questdefs` IS NOT OPTIONAL AND ITS ABSENCE WOULD BE SILENT.
`_title_track_steps` calls `questdefs.coded_literal` four times while it builds
its steps, and `check_encodable` wraps the whole build in `except Exception`
and reports what it catches as a printed SKIP -- so a missing import here would
come back as a skipped probe and a GREEN `test_agentlife.py`, whose four call
sites compare the failure count to 0. The pre-split skip set was measured EMPTY
and is asserted empty after the split for exactly this reason.

WHERE THE REFERENTS WENT. Every "above" and "below" in the comments that travel
with this code points INSIDE one step list or one registry note. The one
outward pointer is `HENCHMAN_AGENT_ID`'s comment, which says "probes.py is a
data module with no view of the session and does not import the server": that
sentence is about the probe family and is exactly as true of this file, which
mirrors the server's constant the same way and imports no server either. It is
kept verbatim and this paragraph is the pointer, the way `probebase.py`'s header
already does for `PROBE_PLAYER_NUMBER`.

`PROBES` here holds only the twenty-one character entries. `probes.py` opens its
own dict, merges this one in with a duplicate-key raise, and keeps `get`,
`names`, `describe` and `check_encodable` -- so `probes.get("title_track", ...)`
answers exactly as it did, and `names()` is still `sorted(PROBES)` and still
returns the same 97 names in the same order. Every name this module binds except
`PROBES` is also re-exported by `probes.py`, at the two sites they were cut
from, so `vars(probes)` still answers for all of them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import questdefs                                            # noqa: E402
from agents import (                                        # noqa: E402
    agent_set_profession, agent_set_secondary_bits)
from probebase import (                                     # noqa: E402
    PROBE_BAR_SKILL, PROP_LEVEL, Probe, Step, _f32)


def _level_steps(agent_id):
    return [
        Step(2.0, 0x009F, [PROP_LEVEL, agent_id, 1], "level -> 1",
             "the nameplate above the character. Does it read 1?"),
        Step(6.0, 0x009F, [PROP_LEVEL, agent_id, 15], "level -> 15",
             "the nameplate again. 15?"),
        Step(6.0, 0x009F, [PROP_LEVEL, agent_id, 20], "level -> 20",
             "20? If all three tracked, property 36 is level and this is settled."),
    ]


# authsrv.py's HENCHMAN_AGENT_ID, mirrored the way PROBE_PLAYER_NUMBER mirrors
# PLAYER_AGENT_ID -- probes.py is a data module with no view of the session and
# does not import the server.
HENCHMAN_AGENT_ID = 30


def _henchman_level_steps():
    return [
        Step(2.0, 0x009F, [PROP_LEVEL, HENCHMAN_AGENT_ID, 1],
             "henchman level -> 1",
             "the HENCHMAN'S party-roster row, top right. Before this step it "
             "shows the body's spawn state (the control); does it read 1 now? "
             "The player's own row is the in-frame control and must NOT move."),
        Step(6.0, 0x009F, [PROP_LEVEL, HENCHMAN_AGENT_ID, 15],
             "henchman level -> 15",
             "the same roster row. 15?"),
        Step(6.0, 0x009F, [PROP_LEVEL, HENCHMAN_AGENT_ID, 20],
             "henchman level -> 20",
             "20? All three tracking settles Q3's substance: the prop-36 store "
             "is read back for agents other than the local player."),
    ]


def _attribute_steps(agent_id):
    """L6's attributability check: does the PANEL show the ranks we sent?

    REWRITTEN 2026-08-15. This probe used to ask whether a 42-zero array is
    well-formed, and that question is ANSWERED -- by the client's own bytes,
    not by a run: the handler divides the wire count by three, so 42 zeros were
    fourteen (0,0,0) triples all along, accepted in silence
    (studies/profession/ATTRIBUTES.md 1.2, studies/combat/PLAN.md 8a). Asking
    it again would spend a client session re-deriving a settled fact.

    The live question is the one L6 actually turns on, and it is the one thing
    static analysis could NOT close: the write chain reaches the per-agent
    record, and the panel's read chain comes back out of the same record
    through AttribBtns.cpp (section 8b) -- but whether the control is bound to
    the local player's agent id at the moment the panel is open is a runtime
    value. This probe reads it off the screen.

    THE RANKS ARE DISTINCT ON PURPOSE (12/9/6/3/1, content/world.toml). If the
    payload's COLUMNS were mis-ordered the panel would show the right numbers
    against the WRONG names, and distinct values are what makes that visible;
    a uniform spread would hide it. Step 3 is the discriminator. (A column
    layout mis-built as interleaved triples does not get this far -- it
    asserts the client dead at CharData:202; studies/combat/PLAN.md 14.)
    """
    from authsrv import attribute_columns
    warrior = ((17, 12), (18, 9), (19, 6), (20, 3), (21, 1))
    return [
        Step(2.0, 0x003A, [agent_id, []], "attributes: empty",
             "open the Hero window's attribute panel. Note what every "
             "Warrior attribute reads BEFORE anything is sent -- this is the "
             "control, and 'they were already right' is the failure this "
             "catches."),
        Step(6.0, 0x003A, [agent_id, list(attribute_columns(warrior))],
             "attributes: Strength 12, Axe 9, Hammer 6, Sword 3, Tactics 1",
             "the SAME panel. Read each of the five names and its number "
             "aloud. All five correct is L6's criterion met."),
        Step(6.0, 0x003A, [agent_id, list(attribute_columns(
                 ((17, 1), (18, 3), (19, 6), (20, 9), (21, 12))))],
             "attributes: the same five ranks REVERSED across the names",
             "same panel. Strength must now read 1 and Tactics 12. If the "
             "panel did not move, it is not reading what this message "
             "writes -- and step 2 passing would have been a coincidence."),
    ]


def _profession_steps(agent_id, custom_id):
    """Does the client accept a profession id it does not ship?

    THE CENTRAL CLAIM OF studies/profession/MODDABLE.md, and the first thing in
    that arc a client can refute. Four documents of static analysis say 256
    professions are reachable; not one packet has ever been sent to check.

    The claim rests on the profession value living in TWO places that are not
    the same storage: the `0x0059` appearance dword packs it into a 4-bit
    nibble at bits 20-23 (16 values, bound-checked `< 0xB` with an assert), and
    the Agent object holds it as a plain byte at `+0x10E`/`+0x10F` written by
    the setter at `0x007F7330` -- which contains NO comparison instruction in
    its whole body. So the design sends a legal placeholder in the dword and
    the custom id on the byte carriers. This probe sends only the byte carriers.

    ONE OUT-OF-BAND VALUE PER RUN, and that is the whole design. Every profession
    bound check in the image ends the session: the assert reporter at
    `0x00488210` is noreturn, so a failed check leaves a live process behind a
    modal dialog with its message pump stopped. There is no second question
    after the first one kills it. So the run spends its single out-of-band
    value deliberately, and everything around it is control.

    WHY 12 AND NOT 11. Eleven is the client's own reserved/none sentinel -- all
    nine reserved attribute rows carry profession 11. Probing with 11 would
    test the sentinel, and an anomaly would be unattributable between "custom
    id refused" and "sentinel handled specially". `profession_sentinel` exists
    to ask that as its own question, on its own run.

    STEP 4 IS THE POINT. A recovery to the control value is the only
    unambiguous proof the client survived: it is the client's own rendering,
    not our socket. A `ConnectionResetError` appears on a clean teardown too,
    and the crash dialog leaves the socket open -- so neither says anything.
    If step 4 renders, the byte carriers tolerated an id the client does not
    ship, and MODDABLE.md's premise holds for this surface.
    """
    # Built through agent_set_profession rather than as raw value lists, so the
    # server's own guard sees every packet this probe sends. That is what makes
    # `custom=True` mean something: it is an opt-in written at the call site,
    # visible in a diff, and it still refuses a primary of 0, a secondary equal
    # to the primary, and anything past the u8 the wire actually carries. A
    # probe that bypassed the guard could send a payload the server would never
    # send, and then the run would measure our bug instead of the client.
    control = 3
    return [
        Step(2.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"CONTROL: profession {control}, which ships",
             "the party window and the hero panel. The profession must CHANGE. "
             "If it does not, stop the run and fix the carrier -- nothing after "
             "this step means anything without it."),
        Step(10.0, 0x00A6, agent_set_profession(agent_id, custom_id, 0, custom=True),
             f"THE EXPERIMENT: profession {custom_id}, which does not ship",
             "nothing, for a moment. Prediction: the packet lands silently, "
             "because the setter has no comparison in it. THEN open the party "
             "window, and say out loud which action you took last -- if the "
             "client dies, the last action names the first profession-keyed "
             "table that reads out of bounds, and that is the finding."),
        # 0x00B7 is 0x00A6's three fields plus the trailing is_pvp byte, so it
        # is built FROM the validated payload rather than beside it -- the two
        # carriers cannot drift apart, and the bound checks apply to both.
        Step(12.0, 0x00B7,
             agent_set_profession(agent_id, custom_id, 0, custom=True) + [0],
             f"the player-specific carrier, also {custom_id}",
             "the hero panel and your own nameplate. 0x00B7 is the message the "
             "real server sends 29 times across 11 live connections, so this is "
             "the shape retail uses, carrying a value retail never carries."),
        Step(12.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"RECOVERY: back to {control}",
             "the party window. If the profession returns to the control value, "
             "the client SURVIVED an out-of-band id on both byte carriers and "
             "the session is still healthy -- which is the result this probe "
             "exists to get. If nothing changes, the client is already behind a "
             "crash dialog and the run ended at whichever step you noted."),
    ]


def _profession_ab_steps(agent_id, custom_id):
    """The SAME operator action, twice, either side of one changed byte.

    RUN 1 (2026-08-12) got the headline and missed the attribution. Profession 12
    rode 0x00A6 and the client kept sending c2s for 5.1 s -- so the packet is
    not what kills it. Then the operator opened the skills menu and the session
    ended. That is a lead with n=1 and NO CONTROL: nobody had opened the skills
    menu while the profession was legal, so "the skills panel reads a
    profession-keyed table out of bounds" and "the skills panel was going to
    fail in this session anyway" are both consistent with what was seen.

    Our loopback world is thin -- no party, no roster, no unlocks -- so a panel
    refusing to open proves nothing on its own. The A/B is what separates the
    two, and it is the whole design of this probe: open the panel, close it,
    change ONE byte, open the SAME panel again.

    THE DELAYS ARE LONG ON PURPOSE. Run 1's steps were 10-12 s apart and the
    operator was still deciding what to click when the next one landed. Twenty
    seconds is enough to open a panel, look at it, and close it without racing.
    """
    control = 3
    return [
        Step(2.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"A: control, profession {control}",
             "nothing yet. Wait for the next line before touching anything."),
        Step(6.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"A: still {control} -- NOW open the skills menu (K)",
             "open the skills and attributes panel with K. Does it open? Look at "
             "it, then CLOSE it. You have about 20 seconds. This is the control "
             "arm: if the panel does not open even at a legal profession, then "
             "run 1's crash was never about profession 12 and this probe has "
             "already answered its question."),
        Step(20.0, 0x00A6, agent_set_profession(agent_id, custom_id, 0, custom=True),
             f"B: the ONE changed byte -- profession {custom_id}",
             "wait about five seconds and do NOTHING. Run 1 shows the client "
             "lives ~5 s on this value while moving normally, so a death during "
             "this wait would mean the packet is lethal on its own, which run 1 "
             "says it is not."),
        Step(8.0, 0x00A6, agent_set_profession(agent_id, custom_id, 0, custom=True),
             f"B: still {custom_id} -- NOW open the skills menu AGAIN",
             "the SAME key, the SAME panel, one byte different. If it opened in "
             "arm A and kills the client here, the skills panel is the first "
             "profession-keyed table to read out of bounds -- and that is the "
             "ordering four documents of static analysis could not produce."),
        Step(20.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"RECOVERY: back to {control}",
             "if you are reading this in the client's world and not on a "
             "Connecting screen, the client SURVIVED both arms -- and the skills "
             "panel is NOT the killer. Say so; a negative here is as useful as "
             "the positive and it sends us to the next panel."),
    ]


def _profession_skillbar_steps(agent_id, custom_id):
    """Does POPULATING skill state clear the skills-panel assert at 12?

    THE LOAD-BEARING QUESTION RUN 2 CREATED (studies/profession/RUNS.md
    section 6). The panel's death is a NULL POINTER -- `*skill`,
    ChCliSkill.cpp:1022 -- not a bound check: the client did not object to the
    id, it objected to finding nothing behind it. If that null is on state a
    packet can populate, the mechanism is population and most of
    ATTRIBUTES.md's 191 edits leave the critical path. If it is on the
    compiled per-profession table, no packet can reach it, and R1's five-byte
    neuter is the only route to the surface ordering.

    WHAT IS ACTUALLY NEW HERE. Every run so far delivered the skillbar in the
    SPAWN BURST, while the profession was still the server's own default --
    the bar has always predated the profession change. This probe delivers the
    SAME eight ids again AFTER the change to 12, so if skill state is keyed to
    the profession current at delivery time, this run registers it under 12
    where run 2 never could.

    THE RE-SEND HAPPENS IN BOTH ARMS. Arm A re-sends the bar at the control
    profession before opening the panel, so "a mid-session skillbar re-send"
    is held constant and the arms still differ by ONE byte. Without it, a
    death in arm B is unattributable between "12 still kills the panel" and
    "re-sending a bar mid-session kills" -- and no run has ever re-sent one
    mid-session either, so the second reading would have no control.
    """
    control = 3
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"A: control, profession {control}",
             "nothing yet. Wait for the next line before touching anything."),
        Step(4.0, 0x00DA, [agent_id, bar, [0] * 8, 1],
             "A: the skillbar again, at the control profession",
             "the bar. It should NOT change -- these are the same eight ids "
             "the spawn burst already sent. This is the control half of the "
             "re-send, so the arms differ by one byte and nothing else."),
        Step(4.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"A: still {control} -- NOW open the skills menu (K)",
             "open the skills and attributes panel with K, look at it, then "
             "CLOSE it. You have about 20 seconds. If it does not open here, "
             "stop: arm B means nothing without this."),
        Step(20.0, 0x00A6, agent_set_profession(agent_id, custom_id, 0,
                                                custom=True),
             f"B: the ONE changed byte -- profession {custom_id}",
             "wait about five seconds and do NOTHING. Run 1 shows the client "
             "lives on this value while playing normally, so a death during "
             "this wait would mean the packet is lethal on its own, which "
             "run 1 says it is not."),
        Step(8.0, 0x00DA, [agent_id, bar, [0] * 8, 1],
             f"B: THE EXPERIMENT -- the same skillbar, delivered at {custom_id}",
             "the bar. If the icons survive, the client accepted skill state "
             "while its profession is one it does not ship. Do not open "
             "anything yet."),
        Step(4.0, 0x00A6, agent_set_profession(agent_id, custom_id, 0,
                                               custom=True),
             f"B: still {custom_id} -- NOW open the skills menu AGAIN",
             "the SAME key, the SAME panel. If it OPENS, the null was "
             "populatable state and the mechanism is population, not bounds "
             "-- say so out loud. If it ASSERTS like run 2 (*skill, "
             "ChCliSkill.cpp:1022), a bar re-send does not reach what the "
             "panel reads, and R1 is the route. Either answer decides the "
             "next rung."),
        Step(20.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"RECOVERY: back to {control}",
             "if you are reading this in the client's world, the client "
             "survived arm B with a populated bar -- which run 2's client did "
             "not. That difference IS the finding."),
    ]


def _profession_trigger_steps(agent_id):
    """Is the 0x00A6 HANDLER what builds the panel's skill state?

    THE ONE SESSION THAT EVER OPENED the skills panel (run 2 arm A) is the
    one session where 0x00A6 arrived before K. Six sessions without it died
    on the same *skill null -- including the PURE DEFAULT world (run 4,
    discriminator 1), so this is not about custom professions at all. Our
    burst sends only 0x00B7 for the player; retail sends 0x00A6 routinely --
    136 across 4 tapes, field 3 cross-matching the player-create byte
    130/130 -- and its handler notifies exactly the attributes panel, the
    party roster and the hero commander via event 0x1000001d
    (studies/smsg/FINDINGS.md, whose 'for our server' list already
    recommended sending it per agent).

    This probe mirrors run 2A EXCEPT the value: profession 1, the same value
    the burst already declared on 0x00B7. No profession change, no new
    information -- just the message. That isolates 'the handler ran' from
    'the profession changed', which run 2A conflated.
    """
    control = 1
    return [
        Step(2.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"0x00A6, profession {control} -- the value the burst already "
             f"declared",
             "nothing yet. This is the message run 2A had and every crashed "
             "session lacked, carrying a value that changes nothing."),
        Step(6.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"still {control} -- NOW open the skills menu (K)",
             "the panel. If it OPENS, the 0x00A6 handler builds the state "
             "the panel reads, and the default world's crash is OUR missing "
             "message -- the fix is to send it at spawn, which is what "
             "retail does. If it CRASHES (*skill, ChCliSkill.cpp:1022), "
             "arrival alone is not enough and the next question is the "
             "CHANGE -- run 2A's value was 3."),
        Step(20.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             "closing marker, same value again",
             "nothing -- this send marks the tape. If you are still "
             "in-world, say out loud whether the panel showed a Warrior "
             "skill list."),
    ]


def _profession_panel_steps(agent_id, custom_id):
    """Does the SKILLS PANEL open at a custom profession? The arc's question.

    THE FIRST SESSION IN THIS ARC THAT MEASURES A PROFESSION. Every earlier
    one measured a bug of ours: the panel asserted on a zero skill id (our
    unlock bit 0, RUNS.md §10) and then on a missing icon (our non-player
    rows, §11). With both fixed the panel opens and lists 1,333 skills, so a
    profession-keyed failure now has somewhere to show.

    0x00A6 ONLY, AND THAT IS THE WHOLE DESIGN. The two byte carriers are NOT
    equivalent and it is measured twice: 0x00B7 carrying 12 asserts
    `profession < arrsize(s_profChapter)` (ConstChar.cpp:1296) ON ARRIVAL --
    run 4b at +3.42 s and again 2026-08-13 at +3.39 s, both dead before any
    UI action -- because its handler feeds the primary to a bound-checked
    11-entry table. 0x00A6's handler writes two agent bytes and fires an event
    the deck builder does not listen to, so it lands silently. This probe
    therefore never sends 0x00B7, and must not be combined with
    --spawn-profession, which does.

    PREDICTION (studies/profession/RUNS.md §10): the panel OPENS. The skill
    walk reads no profession and nothing on the path branches on one, so a
    custom id cannot decide whether it opens. What it CANNOT do is display
    the profession: the panel's record at ctx[0x2c]+0x6BC has exactly one
    writer, reached only from 0x00B7's handler, so with 0x00A6 alone the
    getters stay at their default of 11 and the drop-down should read blank
    or none rather than 12.
    """
    control = 3
    return [
        Step(2.0, 0x00A6, agent_set_profession(agent_id, custom_id, 0,
                                               custom=True),
             f"0x00A6 ONLY -- profession {custom_id}, the agent carrier",
             "nothing, and wait. Run 1 measured the client living on this "
             "value while playing normally. If the session dies HERE, the "
             "agent carrier is lethal after all and that refutes runs 1 and "
             "2 -- say so, because it would be new."),
        Step(8.0, 0x00A6, agent_set_profession(agent_id, custom_id, 0,
                                               custom=True),
             f"still {custom_id} -- NOW open the skills menu (K)",
             "the panel. PREDICTION: it OPENS and lists the skills, because "
             "the walk is profession-blind. Read the PROFESSION DROP-DOWN and "
             "say what it shows -- blank/none is predicted, since 0x00A6 does "
             "not write the record the panel displays from. Then look at the "
             "ATTRIBUTES box: whatever it lists for an id the client does not "
             "ship is the finding. If the client ASSERTS, name the assert -- a "
             "profession-keyed surface finally failed for a profession reason."),
        Step(25.0, 0x00A6, agent_set_profession(agent_id, control, 0),
             f"RECOVERY: back to {control}",
             "the panel, if it is still open. Does the drop-down or the "
             "attribute list change back? A live client here means the whole "
             "sequence was survivable on the agent carrier."),
    ]


def _profession_secondary_steps(agent_id):
    """0x00B6: does the mask really drive the secondary-profession drop-down?

    RUNS.md §13 found the message by walking backwards from the drop-down:
    handler 0x0091F090 -> 0x00813AC0 -> 0x0081FD00 writes field +0xC of the
    per-agent record at ctx[0x2c]+0x6BC, and the builder tests that field bit
    by bit (`shl 1,cl / test edx,eax`, 0x00502414) over ids 0..10. The client's
    own format string at 0xA95A70 names the message and both of its fields.

    WHAT NO CAPTURE CAN SETTLE, which is why this probe exists: all 11 live
    samples of 0x00B6 carry mask 0, because both captured characters are
    early-Prophecies with no secondary unlocked. The bit layout therefore rests
    on the read site alone. Two shots settle it.

    THIS PROBE DELIBERATELY SENDS NO 0x00B7, and that is a correction rather
    than an omission. The obvious opening move -- 0x00B7 {primary 0,
    secondary 0} to "create the record" -- makes the pair EQUAL, and the
    builder asserts `agentPrimaryProf != agentSecondaryProf`
    (GmDeckBuilder:2321, site 0x005024E9) at the end of every run. In an arena
    map with the panel open that crashes the client before the mask is ever
    read, and the honest reading of such a run would be "0x00B6 crashed it".
    The spawn burst has already created the record with an UNEQUAL pair
    (primary 1, secondary 0), so nothing needs creating.

    RUN IT IN AN ARENA MAP. The builder self-gates on a 15-map whitelist --
    796 Codex Arena and 823-836 -- and outside them panel init zeroes the gate
    and the builder returns immediately. `--map 796`.
    """
    all_but_warrior = agent_set_secondary_bits(agent_id, 0x07FE)
    two_only = agent_set_secondary_bits(agent_id, 0x0044)
    return [
        Step(2.0, 0x00B6, all_but_warrior,
             "mask 0x07FE -- every profession 1..10 offerable",
             "nothing yet. The record already exists from the spawn burst's "
             "0x00B7; this only sets the mask."),
        Step(6.0, 0x00B6, all_but_warrior,
             "still 0x07FE -- NOW open the skills menu (K)",
             "the PROFESSION drop-down at the top of the panel. PREDICTION: it "
             "is SELECTABLE (not greyed) and holds TEN entries -- None plus "
             "the nine professions that are not Warrior. Warrior is absent "
             "because the builder skips the primary. Open the list and COUNT "
             "it, and say whether it greys or opens."),
        Step(25.0, 0x00B6, two_only,
             "mask 0x0044 -- ONLY Ranger (2) and Elementalist (6)",
             "the SAME drop-down, reopened. PREDICTION: exactly THREE entries "
             "-- None, Ranger, Elementalist. THIS IS THE MEASUREMENT: a "
             "length-only or count-only reading of the field gives the same "
             "list as the last step, and a wrong bit base gives Monk and "
             "Assassin instead. One shot could not tell those apart."),
        Step(25.0, 0x00B6, agent_set_secondary_bits(agent_id, 0),
             "mask 0 -- the CONTROL, back to nothing unlocked",
             "the drop-down. PREDICTION: back to ONE entry (None) and GREYED, "
             "which is what every session before this one showed. That proves "
             "the ungreying came from the mask and not from being in an arena "
             "map."),
    ]


def _player_attrs_steps(agent_id):
    """The 15-dword player attribute set, 0x00E9.

    Written after the `level` probe came back apparently negative. It was not
    negative -- it was aimed at the wrong channel. The study says outright that
    two unrelated channels carry a level: int property 36 on 0x009F drives the
    per-AGENT level (the nameplate), and field 9 of this message drives the
    per-PLAYER level (the Hero window). We sent the first and read the second,
    and the second is a message we have never sent at all.

    This probe is better than the one it replaces because the Hero window shows
    five fields of this same message at once -- level, xp, skill points and the
    Balthazar bar -- plus, very likely, the "-100%" indicator in the top-left
    corner, which is what max death penalty looks like and which we have never
    given a morale value. Distinct values per field turn one packet into several
    independent checkpoints, the same trick that caught the WORLD_CREATE_AGENT
    field alignment.
    """
    def attrs(xp=0, level=0, morale=0, balth=(0, 0), sp=(0, 0)):
        v = [0] * 15
        v[0] = xp
        v[9] = level
        v[10] = morale
        v[11], v[12] = balth
        v[13], v[14] = sp
        return v

    return [
        Step(2.0, 0x00E9,
             attrs(xp=4242, level=5, balth=(300, 900), sp=(7, 0)),
             "attrs: xp 4242, level 5, balthazar 300/900, sp 7",
             "the Hero window. Level 5? '4242 xp'? Skill Points 7? Balthazar "
             "300/900? Also check the -100% top-left -- did it clear?"),
        Step(8.0, 0x00E9,
             attrs(xp=999999, level=15, balth=(1000, 2000), sp=(12, 0)),
             "attrs: xp 999999, level 15, balthazar 1000/2000, sp 12",
             "same panel. If every field tracked BOTH times, the 15-dword field "
             "map is confirmed against our own client."),
    ]


def _attr_sweep_steps(agent_id):
    """Map every remaining field of 0x00E9 in one packet.

    OBSERVED so far (2026-08-05): field 0 is xp, 9 is level, 13 is skill points,
    11 is the Balthazar numerator. Two surprises worth chasing:

      - Field 12 is NOT the Balthazar denominator. We sent 2000 and the bar read
        "1000/0". The study's "11-12 balthazar" is half right.
      - Field 10 sent as 0 left the top-left indicator reading -100%. GW morale
        runs -60% to +10%, so -100% is not a legal morale -- it looks exactly
        like a display of (0 - 100). If the field is a percentage with 100 as
        baseline, 100 should read 0%. That is what step 2 tests.

    Step 1 gives every unmapped field its own recognisable number so the panel
    can be read like a legend. 1000 + index is deliberate: any value showing up
    anywhere names its own field.
    """
    def sweep():
        v = [1000 + i for i in range(15)]
        v[0] = 424242        # xp, already known, kept distinct
        v[9] = 17            # level: must stay a legal level (blob caps at 31)
        v[10] = 100          # morale: the baseline-100 hypothesis
        return v

    def morale(value, level=17):
        v = [0] * 15
        v[9] = level
        v[10] = value
        v[11] = 1000
        return v

    return [
        Step(2.0, 0x00E9, sweep(),
             "sweep: field i = 1000+i, xp 424242, level 17, morale 100",
             "the whole Hero window. Which numbers appear where? Look for 1012 "
             "and 1014 especially -- one of them may be the Balthazar "
             "denominator. And is the top-left now 0% instead of -100%?"),
        Step(8.0, 0x00E9, morale(110),
             "morale 110 (predicts +10%)",
             "top-left indicator. +10% would confirm morale = value - 100."),
        Step(8.0, 0x00E9, morale(40),
             "morale 40 (predicts -60%, max death penalty)",
             "top-left indicator. -60% is GW's maximum death penalty, so this "
             "value landing there confirms the encoding at both ends."),
    ]


def _attr_legend_steps(agent_id):
    """ONE packet. Every field distinct. Nothing after it to wipe the evidence.

    This exists because attr_sweep was built wrong. Its later steps constructed a
    fresh array with only a few fields set, which zeroed the 1000+i legend the
    first step had painted -- so by the time a person read the panel it showed
    the last step's state, not the sweep's. The observation was destroyed by the
    probe that was meant to produce it, and the person watching had no way to
    know that.

    Rule this encodes: a probe whose result is read at rest must leave the
    client in the state being measured. Multi-step probes are only safe when
    every step is observed as it lands, or when later steps preserve earlier
    fields.

    Known from previous runs: 0 xp, 1-6 factions, 9 level, 11 balthazar current,
    13 skill points. Unmapped: 7, 8, 12, 14. Field 10 is NOT the top-left
    indicator -- 100, 110 and 40 all left it at -100%.
    """
    v = [1000 + i for i in range(15)]
    v[0] = 424242     # xp -- known, kept distinctive
    v[9] = 17         # level must stay legal (the char-select blob caps at 31)
    return [
        Step(3.0, 0x00E9, v,
             "legend: every field = 1000+index (xp 424242, level 17)",
             "read the whole Hero window at leisure -- nothing follows this. "
             "Each number names its own field: 1007 means field 7, 1012 means "
             "field 12. Check the Faction tab's four rows and both sides of "
             "every bar, and note which numbers you CANNOT find anywhere."),
    ]


def _faction_max_steps(agent_id):
    """The four one-dword faction-maxima messages, 0x00EA-0x00ED.

    studies/character/STORAGE.md §2: the attr_legend run proved the client
    ignores fields 2/4/6/12 of 0x00E9 for the bar denominators (four bars,
    identical behaviour -- a rule, not a glitch), and every lineage names those
    fields total_earned_*, a different stat. The caps have messages of their
    own: CHARACTER_FACTION_MAX_KURZICK/LUXON/BALTHAZAR/IMPERIAL, header + one
    dword, shapes confirmed by the client's own 38797 tables. Headquarter's
    handlers store the dword straight into player_hero.{faction}.max.
    UPDATE 2026-08-18: retail sends all four -- 132 sightings across six live
    captures, values 10000/10000/10000/20000 (STORAGE.md §2) -- so what is
    left for this probe is the per-opcode->bar mapping (three identical
    10000s discriminate nothing; our distinct values do) and whether a cap
    moves mid-session.

    Step 1 re-sends the attr_legend vector so every numerator is a number that
    names its own field; the maxima then get four DISTINCT values so a swapped
    opcode->faction mapping names itself too (the EC/ED order -- Balthazar
    before Imperial -- is ldufr's naming, not a measurement). The last step
    moves one cap after the fact: "set once at load" and "updatable any time"
    are different servers to build.
    """
    v = [1000 + i for i in range(15)]
    v[0] = 424242     # xp -- known, kept distinctive
    v[9] = 17         # level must stay legal (the char-select blob caps at 31)
    return [
        Step(3.0, 0x00E9, v,
             "numerators: the attr_legend vector (field i = 1000+i)",
             "nothing new yet -- this paints the numerators the maxima need: "
             "Kurzick 1001, Luxon 1003, Imperial 1005, Balthazar 1011."),
        Step(6.0, 0x00EA, [21000], "0x00EA = 21000 (named MAX_KURZICK)",
             "nothing yet; the panel does not live-refresh."),
        Step(1.0, 0x00EB, [22000], "0x00EB = 22000 (named MAX_LUXON)",
             "nothing yet."),
        Step(1.0, 0x00EC, [23000], "0x00EC = 23000 (named MAX_BALTHAZAR)",
             "nothing yet."),
        Step(1.0, 0x00ED, [24000], "0x00ED = 24000 (named MAX_IMPERIAL)",
             "NOW close and reopen the Hero window and read the Faction tab. "
             "PREDICTION: the denominators that have always read '/ 0' are "
             "filled -- Kurzick 1001/21000, Luxon 1003/22000, Balthazar "
             "1011/23000, Imperial 1005/24000. Each cap value names its own "
             "opcode, so if Imperial reads 23000 the EC/ED naming is swapped "
             "and we have measured that too. All four still '/ 0' refutes the "
             "whole cluster reading."),
        Step(12.0, 0x00EA, [31000], "0x00EA again = 31000",
             "reopen the panel once more. Kurzick 1001/31000 means a cap can "
             "move mid-session; still 21000 means the client latched the "
             "first value and a server must send caps before the panel is "
             "first opened."),
    ]


def _morale_steps(agent_id):
    """Which channel draws the death-penalty indicator, and who computes the maxima.

    THE WIRE IS ALREADY SETTLED, off ArenaNet's own one player death
    (studies/morale/FINDINGS.md): morale is 100-neutral, a death is -15, it
    arrives twice in one tick -- `0x009C [agent, 85]` absolute and
    `0x00EE [10, -15]` as a delta -- and the server then pushes recomputed
    maxima on properties 41 and 42. What no capture can answer is what the
    CLIENT does with any of it, because retail sent all of it at once. Two
    questions survive, and they are separable by leaving things OUT:

      MORALE-Q1  which message draws the top-left indicator? The 15-dword
                 `0x00E9` provably does not: attr_legend sent field 10 as 0,
                 40, 100 and 110 and the indicator never moved. That refuted
                 the DISPLAY, not the field -- and left two candidates.
      MORALE-Q2  does the client derive the pool maxima from morale itself, or
                 only show what the server sends? Retail never had to reveal
                 this. If our morale-without-maxima steps shrink the globes,
                 it is the client's arithmetic; if they do not, the maxima are
                 ours to compute and a server that forgets them ships a death
                 penalty that costs nothing.

    THE ORDER IS THE EXPERIMENT. Each candidate goes out ALONE first, with no
    property update anywhere near it, so a moving indicator names its own
    channel. The maxima come last, together, which is also the state a player
    would actually be in -- so the run ends on the readable configuration
    rather than on a diagnostic one. attr_legend's lesson, applied: a later
    step must not wipe the evidence of an earlier one, and here nothing does,
    because every step moves morale FURTHER rather than resetting it.

    Fixed-position HUD throughout: the top-left indicator, the two globes. No
    aiming, no world-anchored click, so this is agent-pilotable under the
    2026-08-17 boundary -- but it still launches a client, which is the
    owner's call.
    """
    HEALTH_MAX, ENERGY_MAX = 42, 41

    return [
        # MORALE-P1
        Step(3.0, 0x00EE, [10, 0xFFFFFFF1],
             "0x00EE [attr 10, -15] ALONE -- the delta channel",
             "the TOP-LEFT corner. A red -15% there means the delta message "
             "draws the indicator and 0x00E9's refutation was about the "
             "full-set message only. Nothing means the display is elsewhere -- "
             "step 2 is the other candidate. Also watch the two globes: if "
             "they shrink with no property update behind them, the client "
             "computes the maxima itself (MORALE-Q2) and that is the bigger "
             "finding of the two."),
        # MORALE-P2
        Step(10.0, 0x009C, [agent_id, 70],
             "0x009C [player, 70] ALONE -- the absolute, per-agent channel",
             "the same corner. -30% appearing HERE rather than at step 1 makes "
             "0x009C the display channel -- which is the reading the corpus "
             "leans toward, because 0x009C names an agent and a party window "
             "has to show a party member's penalty too. If BOTH steps moved "
             "it, the client accepts either and our server is right to send "
             "both."),
        # MORALE-P3 -- the maxima, at last, and only now
        Step(10.0, 0x009F, [ENERGY_MAX, agent_id, 14],
             "property 41: maximum energy 25 -> 14 (-30% of base 20 is -6; 14 "
             "is deliberately LOWER so a client-side value would disagree)",
             "the energy globe. 14 means the server's number wins outright. A "
             "globe reading 19 -- what -30% of base 20 actually gives -- means "
             "the client had already computed its own and IGNORED ours, which "
             "would be the day this mechanic stops being the server's job."),
        Step(2.0, 0x009F, [HEALTH_MAX, agent_id, 70],
             "property 42: maximum health 100 -> 70, matching -30%",
             "the health globe, and the party window. This is the configuration "
             "a real -30% player is in; read the whole HUD and screenshot it."),
        # MORALE-P4 -- the other end of the range
        Step(10.0, 0x009C, [agent_id, 110],
             "0x009C [player, 110] -- a +10% MORALE BOOST, the ceiling",
             "the indicator's other face. GW draws a boost with a different "
             "icon from a penalty (blue/gold rather than red), so the icon "
             "swapping is what confirms 110 is read as +10 rather than as a "
             "large penalty. The corpus has never carried a boost at all -- "
             "zero sightings in fourteen captures -- so this step is the only "
             "evidence this project can get for the top half of the range."),
        Step(6.0, 0x00EE, [10, 0],
             "0x00EE [attr 10, 0] -- retail's own no-op, for the control",
             "nothing should change. This exact message appears 39 times in "
             "the live corpus riding experience awards, so a client that "
             "reacts to it would mean the burst finding in "
             "studies/combat/PLAN.md 13 has a second reading."),
    ]


def _morale_store_steps(agent_id):
    """MORALE-Q7: does `0x00EE`'s delta write the client's stored morale?

    `--probe morale` answered what reaches the SCREEN -- `0x009C` draws the
    death-penalty indicator, the delta draws nothing -- and could not answer
    whether the delta is IGNORED or merely silent. A message that updates a
    value without repainting it looks identical from a screenshot, and the two
    readings say different things about what a server must send.

    So this probe is not read with eyes at all. It walks the attribute store
    through three distinct values that only we could have chosen, which lets
    `toolkit/clientscan/moralestore.py` find the store in the client's own
    memory WITHOUT anybody's offsets -- an address that follows 77, then 88,
    then 66 is the store; an address that holds 77 by coincidence is not. Then
    the delta lands, and the store either moves or does not.

    THE DWELLS ARE THE DESIGN. Step 1 gets 25 s because the locating scan is a
    full sweep of the client's committed memory and has to finish before the
    value changes under it; everything after gets 12 s, which is 24 samples at
    the watcher's 2 Hz. And every value stays inside the game's own 40..110
    range, so a clamp cannot be mistaken for a refusal.

    THE POSITIVE DIRECTION IS IN HERE TOO (step 6). A store that ignores -13
    and also ignores +7 is ignoring the message; a store that takes one and not
    the other is doing something stranger, and that difference is worth one
    step.
    """
    def attrs(morale):
        v = [0] * 15
        v[0] = 424242          # xp -- the attr_legend trick: every field its
        v[9] = 17              # level     own recognisable number, so the
        v[10] = morale         # morale    memory dump can be read as a legend
        v[13] = 13             # skill points
        return v

    return [
        Step(3.0, 0x00E9, attrs(77),
             "0x00E9 field 10 = 77 -- LOCATE",
             "nothing on screen. moralestore.py scans for every dword == 77."),
        Step(25.0, 0x00E9, attrs(88),
             "0x00E9 field 10 = 88 -- FILTER 1",
             "the watcher: candidates that did not follow 77 -> 88 are out."),
        Step(12.0, 0x00E9, attrs(66),
             "0x00E9 field 10 = 66 -- FILTER 2",
             "three values in a row identifies the store beyond coincidence."),
        Step(12.0, 0x00EE, [10, 0xFFFFFFF3],
             "0x00EE [attr 10, -13] -- THE QUESTION",
             "the watched address. 53 means the delta writes the store and "
             "only the REPAINT was missing; 66 means the client ignores this "
             "message on this build."),
        Step(12.0, 0x009C, [agent_id, 41],
             "0x009C [player, 41] -- the OTHER store",
             "does the per-agent channel write the same address as the "
             "per-player one, or a different one? The indicator should read "
             "-59% either way."),
        Step(12.0, 0x00EE, [10, 7],
             "0x00EE [attr 10, +7] -- the positive direction",
             "same address. A store that ignores both deltas is ignoring the "
             "message rather than refusing a negative."),
        Step(12.0, 0x00E9, attrs(100),
             "0x00E9 field 10 = 100 -- restore, and a last positive control",
             "the store must follow this one whatever the deltas did. If it "
             "does not, the address was never the store and every reading "
             "above is void."),
        Step(4.0, 0x009C, [agent_id, 100],
             "0x009C [player, 100] -- put the indicator back",
             "the corner should clear."),
    ]


def _regen_channel_steps(agent_id):
    """MORALE-Q3: does property 43 on 0x00A3 write the same regen store as 0x00A2?

    WHAT IS ALREADY KNOWN, and why this probe still runs. Statically, 0x00A2 and
    0x00A3 funnel to one dispatcher (0x00818210, case 3 for property 43 --
    studies/agentprops FINDINGS 1d/3), so the channels should be equivalent. And
    Run 3 arm A's own frames (20260822T140922, read 2026-08-22) show the client
    INTEGRATING at the A3-sent rate: after the first revive the energy readout
    climbed 10 -> 13 -> 17 -> 20 at 0.99/s, exactly the 0.045 x 22 this server
    had sent on 0x00A3, with three regen arrows drawn for a 3-pip rate it only
    ever heard on 0x00A3. But that consumption was observed inside a death
    batch; per the house rule the trigger context is part of the claim, so this
    probe asks the same question with no death anywhere near it, one variable
    at a time, with the flat state as its own control.

    THE SIGNAL IS A SLOPE, not a pixel: the readout either climbs ~2 energy per
    second (unmistakable across 2 s frames) or sits flat. Change of shape, not
    of timing. Fixed-position HUD only -- agent-pilotable.

    THE DRAIN COMES FIRST, then the rate games, so every climb starts from a
    nearly empty bar and has ~11 s of visible travel. Values are chosen to be
    nothing the session already shows: 6 pips (0.0792) is double the spawn rate
    and no armour row; the drain leaves ~3 energy, a number the pool never
    otherwise holds here.
    """
    REGEN, SPEND = 43, 62

    return [
        # Q3-P1 -- the plain channel can zero the rate (also the A2 control)
        Step(4.0, 0x00A2, [REGEN, agent_id, _f32(0.0)],
             "property 43 = 0.0 on 0x00A2 -- kill the rate on the PLAIN channel",
             "the three regen arrows right of the energy number. They should "
             "vanish. This is the A2 half of the control pair: the plain "
             "channel demonstrably reaches the store."),
        # the drain, so a climb has somewhere to go
        Step(6.0, 0x00A2, [SPEND, agent_id, _f32(-0.88)],
             "property 62 = -0.88 -- spend 22 of the 25 pool",
             "the energy readout drops to ~3. With the rate at zero it must "
             "then sit FLAT: two consecutive frames at ~3 are the null "
             "baseline every later step is read against."),
        # Q3-P2 -- flat across the wait; nothing sent here
        Step(10.0, 0x00A3, [REGEN, agent_id, agent_id, _f32(0.0792)],
             "property 43 = 0.0792 (6 pips over 25) on 0x00A3 -- THE QUESTION",
             "the readout and the arrows. If the TARGET channel writes the "
             "same store, the number starts climbing at ~2.0/s -- roughly +4 "
             "per 2 s frame, from ~3 toward 25 -- and the arrow count jumps. "
             "If the client ignores property 43 on 0x00A3, nothing moves for "
             "the next 12 s and the pre-merge server was feeding a dead "
             "channel, which arm A's frames already argue against."),
        # Q3-P4 -- the plain channel can stop what the target channel started
        Step(12.0, 0x00A2, [REGEN, agent_id, _f32(0.0)],
             "property 43 = 0.0 on 0x00A2 -- stop the climb from the OTHER channel",
             "the climb freezes and the arrows vanish again. One store, both "
             "channels writing it, is the reading that makes retail's A2 and "
             "our historical A3 interchangeable in fact."),
        Step(8.0, 0x00A2, [REGEN, agent_id, _f32(0.0396)],
             "property 43 = 0.0396 -- restore the shipped 3-pip rate",
             "three arrows return and the bar walks back to full at ~1/s. The "
             "client is left in the state the server believes it is in."),
    ]


def _prop54_steps(agent_id):
    """MORALE-Q4: what does int property 54 -- retail's revive rider -- do?

    THE ONE SIGHTING is `0x009F [54, 27, 22]` in the 20260817T183756 revive
    batch, value equal to the (penalised) maximum energy the same batch
    restores. The obvious reading -- "another max-energy channel" -- is
    statically DEAD on this build: the int path's pool dispatch (0x00818170)
    returns for everything but 32/41/42, and property 54's real arm
    (0x00812E57, third dispatch) writes no store at all. It queues AgentView
    EFFECT event kind 0x0D, whose drain (0x007FA42B -> 0x007EBD30) posts UI
    event 0x1000000F carrying the value -- behind three gates (a global, an
    FP screen-space check, `byte [char+0x71] > 1`). Property 54 is a
    NOTIFICATION, not state, and the notification's face is what this probe
    is for.

    VALUES ARE CHOSEN TO BE NOTHING ON SCREEN: 13 and 5 match no pool, no
    maximum, no level. If any transient renders a number, the number names its
    own source. Each value goes out twice ~8 s apart because a callout can
    live shorter than the 2 s frame cadence -- and the player-body mask trap
    (screenshot scorer) does not apply: these frames are read by eye, whole.

    THE CONTROL IS PROPERTY 41 at the end: the same opcode, same agent, must
    move the energy maximum 25 -> 19 -> back, or the whole run measured a
    dead channel rather than a silent property.
    """
    P54, ENERGY_MAX = 54, 41

    return [
        Step(4.0, 0x009F, [P54, agent_id, 13],
             "int property 54 = 13 on 0x009F -- retail's revive rider, alone",
             "everything: both bars and their numbers, the corner, chat, and "
             "any TRANSIENT over the character or the HUD. Statically this "
             "posts UI event 0x1000000F with the 13; whether that draws a "
             "floating number, flashes the orb, or is swallowed by a gate is "
             "exactly what a frame can say."),
        Step(8.0, 0x009F, [P54, agent_id, 13],
             "int property 54 = 13 again -- a transient needs two chances",
             "same watch. A callout shorter than the frame cadence gets a "
             "second shot at landing inside one."),
        Step(8.0, 0x009F, [P54, agent_id, 5],
             "int property 54 = 5 -- a different value",
             "if anything rendered for 13, it must now render 5. A readout "
             "that tracks our value is measurement; one that does not is "
             "coincidence."),
        Step(8.0, 0x009F, [P54, agent_id, 5],
             "int property 54 = 5 again",
             "same watch."),
        # the instrument control -- same opcode, same agent, known-live property
        Step(8.0, 0x009F, [ENERGY_MAX, agent_id, 19],
             "property 41 = 19 -- POSITIVE CONTROL on the same channel",
             "the energy maximum must read 19. If it does not, nothing above "
             "counts as a null: the channel itself was dead."),
        Step(6.0, 0x009F, [ENERGY_MAX, agent_id, 25],
             "property 41 = 25 -- restore",
             "the maximum back at 25, the state the server believes."),
    ]


def _title_track_steps(agent_id):
    """The title cluster 0x00F3-0x00F6, on our client for the first time.

    REVISED 2026-08-18. The first version aimed to settle a field-naming
    dispute between mirror lineages; retail settled it first. The 08-17
    Factions captures carry the whole cluster (0x00F3 x170, 0x00F4 x215,
    0x00F5 x5, 0x00F6 x7 -- studies/character/STORAGE.md §3), and
    studies/newopcodes/FINDINGS.md measured 0x00F6's handler byte-by-byte:
    field 2 is FLAGS (bit 0 = display value / 10), fields 4/7 are RANK IDS
    into the 0x00F3 table at ctx+0x82C, fields 5/8 duplicate those ranks'
    values on the wire (retail invariant, checked in every sighted channel),
    the strings are printf-style TEMPLATES, and 0x00F5 patches only
    current-points -- and is inert unless a prior 0x00F6 set the description
    pointer (entry+0x28), which is why 0x00F6 must precede it.

    So this probe no longer asks what the fields mean. It asks the loopback
    question retail cannot: does OUR server driving this cluster render in
    OUR client's Titles tab -- the replicate-one-piece step -- plus the two
    things retail traffic left open: whose text reaches the screen (the row
    NAME should resolve from the compiled 48-row s_titleClientData; our
    5-char literals ride the template strings), and what an UNSEEDED rank id
    does (retail always ships 0x00F3 first; AttribTitles:114
    codedNextTierName is the named assert candidate).

    Steps mirror retail's own shape: two 0x00F3 rank records, then a 0x00F6
    whose fields 4/5 and 7/8 reference them value-for-value, then the 0x00F5
    patch, then 0x00F4 (retail usage measured: binds a PLAYER NUMBER to a
    rank id, 215 sightings in towns -- ours is 1 either way). The unseeded-
    rank stress step stays LAST so a crash costs no earlier reading.
    """
    # RUN 2026-08-18 (harness 20260818T...) -- the client HUNG UP, Code=007,
    # the instant the original step 1 landed: 0x00F3 [1, 1, 1000, <8-unit
    # template literal>]. No assert, no crash dialog -- the clean-refusal
    # shape. So the opening is now a one-variable-per-step ladder, verbatim
    # first: retail's own bytes, then our ids with retail's string, then our
    # string SHORTENED -- because the original literal sat exactly at the
    # string16(8) cap, and an off-by-one bound check (`<` where `<=` fits)
    # rejects exactly-at-cap while retail's longest observed is 5 units.
    # Whichever rung hangs up names its variable.
    retail_str = questdefs.coded_literal("ā", framing="bare", limit=8)
    label = questdefs.coded_literal("Pts", limit=7)
    rank1 = questdefs.coded_literal("Ruri", limit=7)
    rank2 = questdefs.coded_literal("Eld", limit=7)
    return [
        Step(3.0, 0x00F3, [0, 0, 0, retail_str],
             "0x00F3 VERBATIM RETAIL: [0, 0, 0, string-id 0x0101] "
             "(capture 20260810T235916, record 0)",
             "nothing visible, predicted -- and no hangup: these are "
             "ArenaNet's own bytes. A Code=007 HERE means the problem is not "
             "our values at all (build drift 38833-capture vs 38797-client "
             "becomes the suspect)."),
        Step(2.0, 0x00F3, [1, 0, 1000, retail_str],
             "0x00F3 our ids, retail's string: [1, 0, 1000, 0x0101]",
             "changes ONE thing from step 1: rank_id/value. A hangup here "
             "names the numbers, not the string."),
        Step(2.0, 0x00F3, [1, 0, 1000, rank1],
             "0x00F3 our 7-UNIT literal: [1, 0, 1000, 'Ruri']",
             "changes ONE thing from step 2: the string, now UNDER the "
             "8-unit cap the first run sat exactly on. A hangup here, after "
             "steps 1-2 passed, points at the template literal itself; "
             "acceptance convicts the at-cap length."),
        Step(2.0, 0x00F3, [2, 0, 8400, rank2],
             "0x00F3 rank record 2: value 8400, name 'Eld'",
             "the second rank the track needs."),
        Step(6.0, 0x00F6, [7, 0, 4200, 1, 1000, 0, 2, 8400, 2, 2,
                           label, rank1],
             "0x00F6 track: title 7, points 4200, current rank 1 (min 1000), "
             "next rank 2 (min 8400)",
             "open the Hero window's TITLES tab (close it first if it was "
             "open). PREDICTION: a track row at 4200 progressing toward 8400, "
             "next tier named 'Elder'. Note the row's NAME: a real title "
             "resolved from the client's own 48-row table (title id 7), or "
             "our text? Retail's field map says the id wins and our strings "
             "are the points/mouseover templates."),
        Step(10.0, 0x00F5, [7, 6000],
             "0x00F5 update: title 7 -> 6000 points",
             "reopen the tab. PREDICTION: the same row reads 6000 -- retail "
             "moves title 2 this way five times (1->8->9->10->12->13), and "
             "the handler posts UI message 0x10000065 on receipt. This works "
             "only because the 0x00F6 step set the description pointer -- "
             "the guard newopcodes measured at entry+0x28."),
        Step(10.0, 0x00F4, [agent_id, 1],
             "0x00F4 display: player 1 wears rank 1",
             "under YOUR OWN nameplate (target yourself). Retail sends this "
             "215 times in towns binding OTHER players (word field = player "
             "number, values <= ~90) to rank records. PREDICTION: 'Ruri' "
             "under the name in this outpost. Our player number and agent id "
             "are both 1, so this step cannot tell those apart."),
        # THE STRESS STEP IS RETIRED -- ANSWERED 2026-08-18, run 2 (harness
        # 20260818T113658). A 0x00F6 whose rank ids reference no 0x00F3
        # record is accepted SILENTLY on receive and kills the client at
        # RENDER time: the first Hero-window open after it landed died on
        #     Assertion: index < m_count   Array.h(587)   build 38797
        # with the dump stack rebasing into the AttribTitles render path and
        # the ctx+0x81C accessor neighborhood newopcodes measured. So the
        # rank-id fields are unchecked until drawn, and a server must never
        # ship a track referencing ranks it has not sent -- same class as
        # the buffId constraint (reconstruction 2.9.5). The step is gone
        # because a registered probe with a guaranteed crash at its tail is
        # a hazard, not an experiment: the question has no remainder.
    ]


PROBES = {
    "level": lambda a, o: Probe(
        question="Is agent int-property 36 on 0x009F the character's level?",
        predicts="The nameplate reads 1, then 15, then 20. If it never changes, "
                 "either the property id is wrong or level is not sent this way.",
        steps=_level_steps(a),
        note="Corroborated by ldufr and gw-preservation, never observed by us. "
             "This is the highest-value packet in the queue: it converts the "
             "study's best-supported claim into an observation and explains why "
             "the character is level 0.",
    ),
    "henchman_level": lambda a, o: Probe(
        question="Does a SECOND agent's level surface read the same per-agent "
                 "prop-36 store the player's row does? The WRITE half is "
                 "SOURCED -- int-main case 0x00812D6E stores the value in a "
                 "per-agent record keyed by whatever agent id the message "
                 "names (studies/unitsetup/FINDINGS.md 8 Q4) -- but the only "
                 "readout ever OBSERVED is the player's own roster row "
                 "(studies/profession/RESKIN.md 18.4, W1/W15/W20).",
        predicts="The henchman's roster row tracks 1 -> 15 -> 20 exactly as "
                 "the player's did, because the store is agent-keyed and the "
                 "roster label builder reads the AGENT "
                 "(studies/heroes/FINDINGS.md 11.2, three arms). The player's "
                 "row, in the same frames, must not move. If the henchman's "
                 "row never changes, the roster reads member levels through "
                 "some other channel and unitsetup Q3 reopens wider.",
        steps=_henchman_level_steps(),
        note="REQUIRES --henchman hatcher --henchman-body (refused at parse "
             "without them): with no world body the row is a container "
             "reading Lvl 255 and the probe measures nothing. Party window "
             "OPEN across every step -- actions '0:play 4:key:P' -- and the "
             "roster draws at the TOP RIGHT (RESKIN 18.3's lesson: aim the "
             "instrument at the right rectangle). The body's create carries "
             "no prop 36, so the pre-step-1 frame is the control reading. "
             "ANSWERED 2026-08-17 (harness 20260817T142147): Mo1 -> Mo15 -> "
             "Mo20, player row frozen at W0. The store is per-agent both "
             "ways. studies/unitsetup/FINDINGS.md 8 Q3.",
    ),
    "profession_custom": lambda a, o: Probe(
        question="Does the client accept a primary profession of 12 -- an id it "
                 "does not ship -- on the byte-wide carriers?",
        predicts="ACCEPTED AND STORED SILENTLY, then survives, because the "
                 "setter at 0x007F7330 has no comparison instruction in its "
                 "whole body and the appearance nibble is different storage we "
                 "are not touching. The recovery step in particular should "
                 "render. If instead the session dies, it dies at a UI action "
                 "rather than at the packet, and WHICH action names the first "
                 "of the 13 profession-keyed tables to read out of bounds -- "
                 "which is the ordering studies/profession/ has no way to get "
                 "statically.",
        steps=_profession_steps(a, 12),
        note="THE FIRST PACKET EVER SENT AT studies/profession/. Four documents "
             "of static analysis stand behind this one value. Twelve, not "
             "eleven, because 11 is the client's own reserved sentinel -- see "
             "profession_sentinel. Expect ONE out-of-band answer per run: every "
             "profession bound check ends the session, so there is nothing "
             "after the first failure.",
    ),
    "profession_ab": lambda a, o: Probe(
        question="Does the SKILLS panel specifically kill a client whose "
                 "profession is out of band -- or was run 1's crash unrelated?",
        predicts="The panel OPENS at profession 3 and the client DIES when the "
                 "same key is pressed at profession 12. Mechanism if so: the "
                 "skills panel filters by profession, GmSkTome is one of the 29 "
                 "bound-check sites, and GmDeckBuilder asserts on the profession "
                 "pair. The informative alternative is that the panel does not "
                 "open in arm A either -- our loopback world has no unlocks -- "
                 "in which case run 1's crash is unattributed and the skills "
                 "menu was never implicated.",
        steps=_profession_ab_steps(a, 12),
        note="Run 1 measured the headline (profession 12 rides 0x00A6 and the "
             "client lives 5.1 s) and could not attribute the death, because "
             "nobody opened the skills menu while the profession was legal. "
             "This is that missing control. Same action, same key, one byte "
             "different.",
    ),
    "profession_skillbar": lambda a, o: Probe(
        question="Does populating skill state clear the skills-panel null at "
                 "profession 12 -- is the mechanism population, not bounds?",
        predicts="DECIDED EITHER WAY, and the fork is stated in advance. If "
                 "the null at ChCliSkill.cpp:1022 is on per-profession state "
                 "the wire can reach, the panel OPENS in arm B and most of "
                 "ATTRIBUTES.md's 191 edits leave the critical path. If it is "
                 "on the compiled table -- which no packet can populate -- the "
                 "SAME assert fires despite the bar, and R1's five-byte neuter "
                 "is the only route to the surface ordering. A THIRD outcome, "
                 "an assert on the bar re-send itself, would be new: no run "
                 "has delivered a skillbar to an out-of-band profession.",
        steps=_profession_skillbar_steps(a, 12),
        note="RAN 2026-08-12 AND THE CONTROL ARM REDDENED (RUNS.md section "
             "8): the mid-session re-send followed by K asserts at "
             "profession 3 -- the same *skill null, no out-of-band byte "
             "anywhere -- so this instrument cannot answer the stated fork "
             "and the question is UNANSWERED, not negative. Kept for the "
             "record; do not re-run expecting the prediction's branches. "
             "Original design: every prior run delivered the bar in the "
             "spawn burst BEFORE the profession changed; this delivers the "
             "same eight ids after, re-sent in arm A too so the re-send "
             "itself is held constant across arms -- which is the control "
             "that caught it. Custom id 12, not 11 -- 11 is the client's "
             "reserved sentinel (profession_sentinel asks that question on "
             "its own run).",
    ),
    "profession_spawn": lambda a, o: Probe(
        question="With the custom profession delivered IN the spawn burst -- "
                 "bar, unlocks and attributes all arriving after it, zero "
                 "mid-session sends -- does the skills panel open?",
        predicts="The population fork of RUNS.md section 8, asked with the "
                 "poisoned instrument removed. If the panel's null is on "
                 "per-profession state built at DELIVERY time, everything this "
                 "session delivers was keyed under 12 from the first packet "
                 "and the panel may OPEN. If the lookup is against the "
                 "compiled table, the same *skill assert fires "
                 "(ChCliSkill.cpp:1022) with the cleanest provocation yet: "
                 "K as the session's first UI action. WIKI (GWW, 'Skills and "
                 "Attributes Panel'): the panel carries a drop-down of "
                 "unlocked SECONDARY professions, so it enumerates "
                 "professions and a per-profession walk is a plausible frame "
                 "for the null -- INFERRED, the handler is unread.",
        steps=[],
        note="RAN 2026-08-12, BOTH SESSIONS CRASHED, EACH A FINDING (RUNS.md "
             "section 9): 3 died on K with the same *skill null on run 2's "
             "exact frame chain -- a SHIPPING profession -- and 12 died on "
             "the ARRIVAL of the burst's own 0x00B7, at profession < "
             "arrsize(s_profChapter), ConstChar.cpp:1296, the first bound "
             "check of the 29-family seen live. So the byte carriers are not "
             "equivalent, and the live lead is the BAR: skills 316-323 are "
             "all Warrior (client table), and every K result in the arc fits "
             "'the panel nulls when the bar's profession does not match the "
             "profession in effect at skill delivery'. Re-run this probe "
             "with the section-9 discriminator flags (pure default; "
             "--spawn-profession 3 --skills ''; --spawn-profession 3 "
             "--skills 276), K as the first action each time. "
             "OBSERVATION ONLY -- no packets; the design is that nothing is "
             "sent after the burst. The server refuses invalid flag values "
             "at startup and announces an out-of-band id loudly.",
    ),
    "profession_trigger": lambda a, o: Probe(
        question="Does an 0x00A6 arrival -- value unchanged -- make the "
                 "skills panel openable in our world?",
        predicts="OPENS. Retail sends 0x00A6 routinely (136 across 4 tapes) "
                 "and its handler notifies exactly the attributes panel "
                 "(event 0x1000001d, studies/smsg); our burst never sends "
                 "the player's. Every session without one died on K -- "
                 "including the pure default -- and the one session with one "
                 "opened. If it CRASHES instead, the trigger is the "
                 "profession CHANGE (run 2A sent 3, a change from the "
                 "burst's 1), which the next probe would isolate.",
        steps=_profession_trigger_steps(a),
        note="RAN 2026-08-12 AND CRASHED -- same *skill assert with both "
             "sends landed, so the arrival-trigger story is REFUTED (RUNS.md "
             "section 9, T1). Third dead prediction of the evening; the next "
             "rung is the STATIC DIVE of the panel's open path, and no "
             "client run until it is done. The disassembly so far: the "
             "setter 0x007F7330 notifies unconditionally, and the 1022 "
             "assert sits inside a find-next-set-bit bitmap walk. Original "
             "design: profession_ab arm A is the n=1 that opened; this "
             "replayed it with the one change that removes the change.",
    ),
    "profession_panel": lambda a, o: Probe(
        question="Does the Skills panel OPEN at profession 12, now that the "
                 "panel works at all -- and what does it display?",
        predicts="IT OPENS. The skill walk reads no profession and nothing "
                 "between the panel's entry and its enumeration branches on "
                 "one, so a custom id cannot decide whether it opens (RUNS.md "
                 "§10.4). The DISPLAY is the other half: the panel's "
                 "profession record has exactly one writer, reached only from "
                 "0x00B7, so with 0x00A6 alone the getters stay at their "
                 "default of 11 and the drop-down should read blank/none "
                 "rather than 12. A crash instead would be the FIRST "
                 "profession-keyed failure in this arc that is not a bug of "
                 "ours -- name the assert.",
        steps=_profession_panel_steps(a, 12),
        note="THE ARC'S QUESTION, ASKABLE FOR THE FIRST TIME. Everything "
             "before this measured our own defects: the panel asserted on a "
             "zero skill id (our unlock bit 0) and then on a missing icon "
             "(our non-player rows). Both fixed, panel lists 1,333 skills. "
             "0x00A6 ONLY -- do NOT pass --spawn-profession, which sends "
             "0x00B7, measured lethal on arrival at ConstChar.cpp:1296 in two "
             "separate sessions. Run with the default --unlocks corpus.",
    ),
    "profession_secondary": lambda a, o: Probe(
        question="Is 0x00B6's payload a per-profession BITMASK driving the "
                 "secondary-profession drop-down, one bit per id?",
        predicts="Mask 0x07FE gives TEN entries (None + every profession but "
                 "the Warrior primary) and the control UNGREYS; mask 0x0044 "
                 "gives exactly THREE (None, Ranger, Elementalist); mask 0 "
                 "gives ONE and greys again. The two-shot design is the point "
                 "-- a count-only or length-only reading of the field gives "
                 "the same list twice, and a wrong bit base gives Monk and "
                 "Assassin. All 11 live samples of this opcode carry mask 0, "
                 "so no capture can settle the layout and only this can.",
        steps=_profession_secondary_steps(a),
        note="RAN 2026-08-13 AND ALL THREE SHOTS HIT EXACTLY (RUNS.md §14): "
             "0x07FE gave ten entries and ungreyed, 0x0044 gave exactly three "
             "(None, Ranger, Elementalist), 0 locked it again -- so the bit "
             "index IS the profession id, OBSERVED. Kept as the regression "
             "run for the mechanic. "
             "MUST RUN IN AN ARENA MAP -- pass --map 796 (Codex Arena) or one "
             "of 823-836. The builder self-gates on that 15-map whitelist and "
             "outside it panel init zeroes the gate, so a null result "
             "elsewhere says nothing about 0x00B6. Sends NO 0x00B7 on "
             "purpose: an opening 0x00B7 with primary == secondary asserts "
             "GmDeckBuilder:2321 at the end of every builder run and would "
             "crash the client before the mask is read. The spawn burst has "
             "already created the record with an unequal pair. If the list "
             "populates but stays grey, the suspect is the mission-map field "
             "(0x0084D9B0 must read 0), not the mask.",
    ),
    "profession_sentinel": lambda a, o: Probe(
        question="Is profession 11 handled specially, being the client's own "
                 "reserved/none marker rather than merely out of range?",
        predicts="DIFFERENT from 12, in some visible way -- a blank profession, "
                 "a default icon, or a distinct failure. All nine reserved "
                 "attribute rows carry profession 11, so the client has a "
                 "meaning for it. If 11 and 12 behave identically, then 11 is "
                 "not special on this surface and the custom range could start "
                 "there after all.",
        steps=_profession_steps(a, 11),
        note="Run this ONLY after profession_custom, and compare. Running it "
             "first makes any anomaly unattributable between 'custom id "
             "refused' and 'sentinel handled specially', which is exactly the "
             "confusion MODDABLE.md warns about.",
    ),
    "profession_max": lambda a, o: Probe(
        question="Does the byte carrier really hold 255, or does something "
                 "downstream mask it to a nibble?",
        predicts="If the appearance dword's PACKER (0x0091D430) is reached by "
                 "any path we have not found, 255 masks to 255 mod 16 = 15 and "
                 "the client shows profession 15 rather than failing -- a "
                 "SILENT wrong value, which is the one failure mode this arc "
                 "has no other way to detect. If nothing packs client-side, "
                 "255 behaves like any other out-of-band id.",
        steps=_profession_steps(a, 255),
        note="This is the silent-failure check, and it is the reason the ceiling "
             "is stated as a conditional (256 if nothing packs client-side, 16 "
             "if something does). Cheapest test of that conditional.",
    ),
    "attributes": lambda a, o: Probe(
        question="Does the attribute panel show the ranks 0x003A carries -- "
                 "i.e. is the panel bound to the agent whose record we write?",
        predicts="Step 2 draws Strength 12, Axe Mastery 9, Hammer Mastery 6, "
                 "Swordsmanship 3, Tactics 1, each against its own name. Step 3 "
                 "reverses them and the panel follows. If step 2 lands and step "
                 "3 does not, the panel is showing something cached or "
                 "something else's; if the numbers appear against the WRONG "
                 "names, the triple's slot order is wrong -- and 8a's reading "
                 "of slot 2 as baseValue is what that would refute.",
        steps=_attribute_steps(a),
        note="This is L6's attributability criterion, and the ONLY part of it "
             "static analysis could not close: the write chain and the panel's "
             "read chain provably share one record and one locator (section "
             "8b), but the control's runtime agent binding is not a byte "
             "pattern. Distinct ranks are the design -- they make a slot-order "
             "error visible instead of plausible.",
    ),
    "player_attrs": lambda a, o: Probe(
        question="Does 0x00E9 field 9 drive the Hero window's level, and does "
                 "field 0 drive its xp?",
        predicts="The Hero window reads Level 5 and 4242 xp, then Level 15 and "
                 "999999 xp. Skill Points show 7 then 12, and the Balthazar bar "
                 "moves. If the -100% indicator top-left also clears, field 10 "
                 "is morale and we have simply never sent it.",
        steps=_player_attrs_steps(a),
        note="Replaces what the `level` probe was trying to do. That probe was "
             "not wrong, it was aimed at the other channel: property 36 on "
             "0x009F is the per-AGENT level shown on the nameplate, which was "
             "switched off, while the Hero window is the per-PLAYER set here. "
             "Shape corroborated by four lineages; field 9's effect CONTESTED, "
             "which is exactly what this settles.",
    ),
    "attr_sweep": lambda a, o: Probe(
        question="What are the remaining fields of 0x00E9, and is field 10 a "
                 "morale percentage offset by 100?",
        predicts="Each unmapped field shows its own 1000+i value somewhere in "
                 "the Hero window, naming itself. The top-left indicator reads "
                 "0%, then +10%, then -60% -- and -60% is GW's maximum death "
                 "penalty, so hitting it exactly would confirm the encoding at "
                 "both ends rather than just shifting a number.",
        steps=_attr_sweep_steps(a),
        note="Follows the player_attrs probe, which confirmed fields 0, 9, 11 "
             "and 13 and refuted the study's claim that field 12 is the "
             "Balthazar denominator -- we sent 2000 and the bar read 1000/0.",
    ),
    "attr_legend": lambda a, o: Probe(
        question="Which field of 0x00E9 drives which readout? One packet, "
                 "every field labelled with its own index.",
        predicts="The Faction tab's four rows and the level/xp/skill-point "
                 "readouts between them account for most of 1001-1014. Numbers "
                 "that appear NOWHERE are as informative as the ones that do: "
                 "fields 7, 8, 12 and 14 are the current suspects for having no "
                 "visible effect at all.",
        steps=_attr_legend_steps(a),
        note="Replaces attr_sweep, which destroyed its own evidence -- its "
             "later steps rebuilt the array from zeros and wiped the legend "
             "before anyone could read it. This one is a single packet and "
             "leaves the client in the state being measured.",
    ),
    "morale_store": lambda a, o: Probe(
        question="MORALE-Q7: does 0x00EE [attr 10, delta] write the client's "
                 "stored morale without repainting it, or is it ignored?",
        predicts="The store is found by our own three values (77, 88, 66) and "
                 "nobody's offsets. Then: if the address reads 53 after the "
                 "-13, the delta writes and only the repaint was missing -- "
                 "which would mean our server is right to send both channels "
                 "and the Hero window may show what the corner does not. If it "
                 "stays 66, the client ignores this message on build 38797 and "
                 "0x009C is the whole mechanic client-side. Step 7 is the "
                 "control that keeps either reading honest: the store MUST "
                 "follow a fresh 0x00E9 whatever the deltas did.",
        steps=_morale_store_steps(a),
        note="ANSWERED 2026-08-20 (harness 20260820T224356, "
             "studies/morale/RUNS.md Run 2): THE DELTA WRITES. The attribute "
             "slot went 66 -> 53 on the -13 and 53 -> 60 on the +7, each "
             "within one 0.5 s sample, while 0x009C [player, 41] moved it not "
             "at all -- so 0x00EE and 0x009C are two stores for one number, "
             "and only 0x009C repaints. The block came free: our values landed "
             "at attr_id x 8 from the experience field, each stored TWICE, "
             "which checks GWCA's dupe-pair layout against numbers of ours. "
             "Read with toolkit/clientscan/moralestore.py, never with a "
             "screenshot -- the corner already said all it has to say. Values "
             "stay inside 40..110 so a clamp cannot read as a refusal. Needs "
             "~110s: pass --hold 130.",
    ),
    "morale": lambda a, o: Probe(
        question="Which message draws the death-penalty indicator -- the "
                 "0x00EE delta or the per-agent 0x009C -- and does the client "
                 "compute the reduced maxima itself or only display ours?",
        predicts="MORALE-P1/P2: exactly one of the first two steps puts a red "
                 "percentage in the top-left corner. 0x009C is the favourite: "
                 "it names an agent, and a party window has to show a party "
                 "member's penalty. MORALE-P3: the globes do NOT move until "
                 "properties 41/42 arrive, and then they read 14 and 70 -- the "
                 "server's numbers, not the -30%-of-base arithmetic, which is "
                 "why 14 was chosen to disagree with 19. MORALE-P4: 110 draws "
                 "a BOOST icon rather than a penalty one. Every step is a "
                 "fixed-position HUD readout.",
        steps=_morale_steps(a),
        note="ANSWERED 2026-08-20, agent-piloted, all six steps verified "
             "in the gamesrv log before a pixel was read (harness "
             "20260820T220732; studies/morale/RUNS.md Run 1). 0x009C DRAWS "
             "the indicator -- red chevron, -30% -- and 0x00EE's delta drew "
             "nothing over three frames and 9.2 s; 110 flipped the chevron up "
             "and teal at +10%; and the pools did NOT move until properties "
             "41/42 landed, then showed the 14 we sent rather than the 19 the "
             "client's own arithmetic would give. So the maxima are the "
             "SERVER's job. Kept runnable: it is also the calibration for the "
             "corner, which sits at (10,32)-(60,82) and which a crop starting "
             "at y=100 misses entirely. The HUD repaints on a ~1-4 s delay, "
             "so leave >=5 s between a send and its screenshot.",
    ),
    "regen_channel": lambda a, o: Probe(
        question="MORALE-Q3: does property 43 on 0x00A3 (float-target) write "
                 "the same regeneration store as retail's 0x00A2, outside a "
                 "death batch?",
        predicts="Q3-P1: zeroing the rate on 0x00A2 clears the regen arrows. "
                 "Q3-P2: with the rate at zero a drained bar sits FLAT at ~3 "
                 "across consecutive frames. Q3-P3, the question: 6 pips sent "
                 "on 0x00A3 restarts the climb at ~2.0/s with the arrow count "
                 "jumping -- favoured, because the two opcodes share dispatcher "
                 "0x00818210 case 3 and because Run 3 arm A's frames already "
                 "show a climb at an A3-sent rate. Q3-P4: a 0x00A2 zero stops "
                 "the A3-started climb -- one store, two doors. A flat line at "
                 "step 3 instead refutes the equivalence and makes the energy "
                 "arc's channel move load-bearing after all.",
        steps=_regen_channel_steps(a),
        note="Runs with no enemy and no deaths on purpose: arm A's A3 "
             "consumption was observed inside a death batch, and the context "
             "is part of the claim. ~40 s of steps; pass --hold 70 --shots 2. "
             "Read the energy readout as a SLOPE across frames, never as one "
             "pixel.",
    ),
    "prop54": lambda a, o: Probe(
        question="MORALE-Q4: int property 54, retail's revive rider (= 22, "
                 "the restored maximum, in its one sighting) -- state or "
                 "notification, and does anything draw?",
        predicts="No store moves: the bars and maxima hold through four "
                 "property-54 sends, because the int path's pool dispatch "
                 "ignores 54 and its real arm only posts UI event 0x1000000F "
                 "(AgentView EFFECT kind 0x0D) with the value. If the gates "
                 "pass, some transient draws 13 and then 5 -- a floating "
                 "number or orb flash naming its own trigger; if nothing "
                 "draws, the UI arm is gated (byte [char+0x71] or the "
                 "screen-space check) and 54 stays display-only with an "
                 "unwitnessed face. Property 41 at the tail MUST move the "
                 "maximum or the run is void.",
        steps=_prop54_steps(a),
        note="Statically walked 2026-08-22 on the pinned 38797: 0x00812E57 -> "
             "0x007E0290 -> 0x007F7770 queues EFFECT kind 0x0D {which=0, "
             "value}; drain case 0x0D at 0x007FA42B calls 0x007EBD30, which "
             "posts UI event 0x1000000F -- and writes NOTHING. avevents.py "
             "--id 54 reproduces the kind. ~42 s of steps; pass --hold 70 "
             "--shots 2 and read the frames whole, by eye -- a transient can "
             "die inside the shot cadence.",
    ),
    "faction_max": lambda a, o: Probe(
        question="Do the four one-dword messages 0x00EA-0x00ED set the "
                 "faction bar denominators that 0x00E9 provably does not?",
        predicts="After the burst and a Hero-window reopen, the Faction tab's "
                 "denominators -- '/ 0' on every run so far -- read 21000 "
                 "Kurzick, 22000 Luxon, 23000 Balthazar, 24000 Imperial "
                 "against the legend numerators 1001/1003/1011/1005. Distinct "
                 "caps mean a swapped opcode->faction mapping names itself. "
                 "The final step predicts Kurzick moving to 31000, settling "
                 "whether a cap can change mid-session. All four bars still "
                 "'/ 0' refutes the cluster reading outright.",
        steps=_faction_max_steps(a),
        note="ANSWERED 2026-08-18, agent-piloted (harness 20260818T112259, "
             "studies/character/RUNS.md §Run 1): all four bars filled, "
             "mapping = ldufr's naming exactly (EA Kurzick, EB Luxon, EC "
             "Balthazar, ED Imperial), and the step-6 re-send moved Kurzick "
             "to 31000 -- caps update mid-session. Retail corroborates from "
             "the other side: 132 sightings over six live captures at "
             "10000/10000/10000/20000 (STORAGE.md §2). Kept runnable as the "
             "faction-panel calibration. The Hero window does not "
             "live-refresh -- close and reopen it after each read point.",
    ),
    "title_track": lambda a, o: Probe(
        question="Does OUR server driving 0x00F3-0x00F6 render in OUR "
                 "client's Titles tab?",
        predicts="A track row at 6000 of 8400. The row's name: the ANSWERED "
                 "surprise is that it is the current rank's 0x00F3 string -- "
                 "ours -- not a compiled-table entry, so titles are fully "
                 "wire-authorable, display text included. 0x00F4's "
                 "under-nameplate render is the one prediction still "
                 "unverified: it needs a real self-target, which a scripted "
                 "center-click does not produce (it becomes a move order).",
        steps=_title_track_steps(a),
        note="ANSWERED 2026-08-18 over three runs (RUNS.md §Run 2; captures "
             "20260818T113252/113658/114312) except 0x00F4's nameplate "
             "half. Two constraints found on the way, both load-bearing for "
             "any server: string16(8) admits AT MOST 7 units on receive -- "
             "an at-cap literal is an instant Code=007 hangup, convicted by "
             "a one-variable ladder against verbatim-accepted retail bytes "
             "-- and a 0x00F6 referencing unseeded rank ids is silent on "
             "receive and FATAL on first render (Array.h(587), dump in the "
             "capture). The stress step that found the second is retired; "
             "its record is in _title_track_steps' tail comment. Field map "
             "per studies/newopcodes; retail sightings per STORAGE.md §3. "
             "Run in an outpost; reopen the Hero window at every read "
             "point.",
    ),
}
