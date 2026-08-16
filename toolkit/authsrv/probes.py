"""Scripted one-packet experiments, fired at our own client after it spawns.

studies/character/FINDINGS.md ends with a probe queue: a set of questions where
all read-only research is exhausted and only the client can settle them. Reading
more mirrors cannot help, because for several of these every mirror is the same
witness wearing different clothes. The client is the last court.

Each probe is a short sequence of packets with a stated question, a stated
prediction, and an instruction about what to look at. The prediction matters: a
probe that does not say in advance what it expects can be rationalised after the
fact into agreeing with whatever happened, which is how we ended up with three
comments in authsrv.py stating inference as fact.

Usage, once the character is standing in the map:

    python toolkit/authsrv/authsrv.py --probe level
    python toolkit/authsrv/authsrv.py --list-probes

The server runs the sequence after the spawn burst, prints what to watch for
before each step, and records every packet to the capture as usual. Nothing here
touches anything but our own loopback client.

WHY DELAYS. The steps are spaced so a person can see one result before the next
arrives. A probe that fires three packets in 50 ms tells you only what the last
one did.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import questdefs                                            # noqa: E402
from agents import (                                        # noqa: E402
    AGENT_KIND_NPC, AGENT_KIND_PLAYER, AGENT_TYPE_LIVING, APPEARANCE_WARRIOR,
    CHAR_CLASS_MONSTER_BASE, CHAR_CLASS_PLAYER_BASE, DEFAULT_RUN_SPEED,
    ALLEGIANCE_HOSTILE, EFFECT_DEAD, EFFECT_TRANSITION, HATCHER, INF, WORLD,
    agent_set_profession, agent_set_secondary_bits, create_agent, npc_model,
    npc_properties, npc_template)

# The hostile the normal map load spawns. Read from content, the same row
# authsrv.py reads, so the removal probe cannot drift from what is in the world.
_ENEMY_ROW = WORLD.get("spawn", "test_enemy")
ENEMY_AGENT_ID = _ENEMY_ROW["agent_id"]
ENEMY_DEFINITION = _ENEMY_ROW["definition"]
# Clear of the probe agents (2..7) and the standing enemy, so the control body
# cannot collide with either -- the same reasoning authsrv.py:776 gives for the
# enemy id itself. An id reused for a second body leaves the client with one
# agent's state under another's name.
FRESH_AGENT_ID = 12

# How far from the player a probe puts a body it wants LOOKED AT.
#
# Owner's instruction, 2026-08-10, given twice: 150, not 550 and not 300. A probe
# body is evidence only if the operator can see it without turning the camera or
# walking -- a spawn far enough to need hunting for reads as "nothing appeared",
# which is the exact failure this probe family is trying to distinguish from a
# real negative. Probes that place several bodies should step by this, not scatter
# them further apart to keep them separate.
PROBE_SPAWN_NEAR = 150.0

# GAME_SMSG 0x003C's first field is a PLAYER NUMBER, not an agent id -- and this
# module is only ever handed an agent id (`probes.get(name, PLAYER_AGENT_ID, ...)`).
# On this server both are 1, which is exactly the conflation the party dive flagged
# as making every possible mis-join invisible, so the constant is named for what the
# FIELD is rather than reused from `a`. If PLAYER_AGENT_ID is ever changed to differ
# from PLAYER_NUMBER -- which is the recommendation -- this must NOT follow it.
PROBE_PLAYER_NUMBER = 1

# Agent int-property ids (GmAgentProperties.h via studies/character/FINDINGS.md).
PROP_LEVEL = 36
# Property 60. SOURCED three ways: GWLP-R (2013) and GWCA both name it
# CastSkill/skill_activated, and on build 38797 the client's own generic-value
# dispatcher gives 4, 50 and 60 -- and only those three -- one shared case body
# that reaches AvApi and queues an AgentView event carrying the skill id.
# studies/skillcast/FINDINGS.md section 6.
PROP_CAST_SKILL = 60

# Property 61 is a FLOAT property, so it rides 0x00A2/0x00A3 and NOT 0x009F.
# MEASURED (studies/skillcast section 15.1): the two dispatchers' main switches
# are disjoint, and a property sent on the wrong message type is discarded in
# silence -- no error, no log line. Sending 61 on 0x009F would look exactly like
# the probe's hypothesis being wrong.
PROP_CAST_TIME = 61

# Properties 65 and 66 write two BYTES of the same per-agent appearance record,
# at +5 and +7 (studies/skillcast section 16.4). 65 is OpenTyria's `PvPTeam`;
# 66 is past the end of its enum and unnamed in every source we hold. 65's
# setter compares before writing and then calls a refresh; 66's writes
# unconditionally and calls nothing, which is why the sweep below borrows 65 to
# force a redraw.
PROP_APPEARANCE_65 = 65
PROP_APPEARANCE_66 = 66

# The skill ids authsrv.py puts on the bar. Kept in step with authsrv's
# TEST_SKILLBAR rather than imported, because a probe has to keep working when
# the bar is rebound from --skills and the probe's own point is the slot, not
# the id. If they drift, the skill probes below say so instead of silently
# addressing a slot that holds something else.
PROBE_BAR_SLOT = 0
PROBE_BAR_SKILL = 316

# The five Prophecies warrior armour pieces: file_id and model_id, corroborated
# across two independent sources in the character study.
WARRIOR_ARMOR = [
    ("body",  0x5B,  823),
    ("legs",  0x5E, 2440),
    ("head",  0x5A,  355),
    ("hands", 0x5C, 1598),
    ("feet",  0x5D, 6136),
]


class Step:
    """One packet, plus what a human should look at after it lands.

    `sends` is False for a REFUSAL step -- one whose whole purpose is to carry a
    message to the operator and send nothing. `smsgsweep_steps` returns one when the
    plan is empty, deliberately, because a probe that sends nothing and prints
    "complete" is the shape of a green run that measured nothing.

    It is a DECLARED flag rather than a shape test, and that distinction cost a red
    suite on 2026-08-13. The refusal was built as `Step(0.0, 0x0000, [], ...)` and
    `check_encodable` encoded it like any other step: 0x0000 is a real opcode wanting
    one value, so the refusal reported itself as a BROKEN PROBE. Nothing was broken --
    the all-zero sweep had simply finished, `remaining` went to 0, and the plan emptied
    for the best possible reason. Inferring "this is a refusal" from an empty `values`
    list would be worse than the bug it fixes: a genuinely malformed step with no
    values is precisely what that check exists to catch, and the two are
    indistinguishable by shape.
    """

    def __init__(self, delay, opcode, values, label, watch, sends=True):
        self.delay = delay
        self.opcode = opcode
        self.values = values
        self.label = label
        self.watch = watch
        self.sends = sends


class Probe:
    def __init__(self, question, predicts, steps, note=""):
        self.question = question
        self.predicts = predicts
        self.steps = steps
        self.note = note


def _agent_removal_steps(agent_id, origin):
    """WORLD_REMOVE_AGENT (0x0021), and then the id reuse it is supposed to unlock.

    The hostile is spawned by the normal map load, so this probe removes THAT
    agent rather than making one: the interesting question is what the client does
    with an object it is already drawing, tracking and possibly targeting.

    THE FIRST VERSION OF STEP 2 WAS BROKEN AND ITS NEGATIVE MEANT NOTHING.
    RUN 2026-08-10: step 1 vanished cleanly and step 2 drew nothing, which read
    like "id reuse is impossible". It was not. That step sent a BARE 0x0020, and
    three things were wrong with it: no NPC_UPDATE_PROPERTIES and no
    NPC_UPDATE_MODEL first (npc_properties' own docstring says the definition
    "must precede any agent using it" -- the definition index is a raw array
    index); `npc_model(...)` was passed where a model_id belongs, and it returns a
    MESSAGE PAYLOAD, not an id; and the plane was hardcoded 0 instead of the
    player's. A malformed create drawing nothing is not evidence about the id.
    The re-created agent was also missing the hostile allegiance the real spawn
    sets, so even a success would have measured a different body.

    So step 2 now sends the SAME three-message burst spawn_enemy does, and a
    CONTROL follows it. That control is the whole design: the same burst at a
    FRESH id nothing has ever used.

        step 2 fails, step 3 works  -> the id really is poisoned by removal
        both fail                   -> our burst is wrong, and the id is innocent
        both work                   -> reuse is fine and the first run measured a
                                       bug in this file, nothing more
    """
    ox, oy, plane = origin if origin else (0.0, 0.0, 0)
    reuse = (ox + PROBE_SPAWN_NEAR, oy)
    fresh = (ox + 2 * PROBE_SPAWN_NEAR, oy)
    model_id = CHAR_CLASS_MONSTER_BASE | ENEMY_DEFINITION
    return [
        Step(3.0, 0x0021, [ENEMY_AGENT_ID], "REMOVE the hostile",
             "the hostile. Does it vanish cleanly -- no corpse, no nameplate, no "
             "health bar? If you had it TARGETED, does the target frame clear or "
             "does the UI keep a dead reference?"),
        # --- step 2: the FULL burst, at the SAME id -----------------------------
        Step(6.0, 0x0056, npc_properties(ENEMY_DEFINITION, HATCHER),
             "redefine the NPC type",
             "nothing yet -- this defines the type the next create refers to."),
        Step(0.5, 0x0057, npc_model(ENEMY_DEFINITION, HATCHER),
             "and its model", "still nothing yet."),
        Step(0.5, 0x0020,
             create_agent(ENEMY_AGENT_ID, model_id, AGENT_KIND_NPC,
                          reuse[0], reuse[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"RE-CREATE at the SAME id ({ENEMY_AGENT_ID})",
             f"{PROBE_SPAWN_NEAR:.0f} units east. Does a fresh hostile appear? "
             "This is the id reuse "
             "removal is supposed to make safe -- 301 of 301 live re-creations "
             "were preceded by a removal of that id."),
        # --- step 3: the CONTROL, same burst at an id never used ---------------
        Step(6.0, 0x0020,
             create_agent(FRESH_AGENT_ID, model_id, AGENT_KIND_NPC,
                          fresh[0], fresh[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"CONTROL: the SAME create at a FRESH id ({FRESH_AGENT_ID})",
             f"{2 * PROBE_SPAWN_NEAR:.0f} units east. If THIS one appears and the "
             "one before it did not, "
             "the removed id is genuinely poisoned. If neither appears, the burst "
             "is wrong and the id was never the problem."),
    ]


def _health_max_steps(agent_id):
    """Does int property 42 refill only when the MAXIMUM actually changes?

    RESKIN.md 18.12: with the bar at a quarter, int property 42 = 100 did nothing
    -- row stayed 24.0%, HUD kept reading 25, nine frames. The "assigns
    health_max = value AND health = 1.f" reading is ldufr/Headquarter's, which is
    UPSTREAM rather than a retail observation. Our player's maximum is ALREADY
    100, so that run could not tell a same-value no-op from a wrong reading.

    200 separates them, and the HUD's own NUMBER is the discriminator rather than
    the bar, because three outcomes are distinguishable and only one of them is
    "nothing happened":

      HUD 200, bar full  -> the refill is real and fires on a CHANGE of maximum.
      HUD  50, bar 25%   -> the maximum moved and the FRACTION was preserved:
                            0.25 * 200 = 50. Upstream's health_max half is right
                            and its `health = 1.f` half is wrong.
      HUD  25, bar 25%   -> property 42 does not carry the maximum either, and
                            2026-08-06's "raised a health bar reading 100" was
                            something else establishing it.

    Step 3 puts it back to 100 -- if step 2 moved anything, a return is the
    cheapest check that we are driving a live value rather than watching a
    one-way latch.
    """
    a = agent_id
    return [
        Step(4.0, 0x00A3, [16, a, a, _f32(-0.75)],
             "damage -0.75 -- take the bar to a quarter",
             "the party row and the HUD must both read a quarter (bar ~25%, "
             "HUD number 25). This is setup, and it is the step already "
             "measured twice, so it doubles as the run's own control."),
        Step(7.0, 0x009F, [42, a, 200],
             "int property 42 = 200 -- a DIFFERENT maximum",
             "READ THE HUD NUMBER, not just the bar. 200 means refill-on-change; "
             "50 means the maximum moved and the fraction survived; 25 means "
             "property 42 does not carry the maximum at all."),
        Step(7.0, 0x009F, [42, a, 100],
             "int property 42 = 100 -- put it back",
             "whatever step 2 moved should move back. If step 2 changed nothing "
             "this changes nothing either, and the run's answer is the third "
             "outcome above."),
    ]


def _party_health_steps(agent_id):
    """Is the party row's red bar THIS player's health, or a constant?

    RESKIN.md 18.10: the row `W0 Test Warrior` draws on a full-width red bar, and
    the red is not a fault -- WIKI (GWW, "User interface" section Party window,
    rev. 2026-07-15): "The red bars represent the allies' or party members'
    health. A disconnected player will have its health bar greyed out." So the row
    is correct, and the bar is a live per-member readout this server has never
    deliberately driven.

    Property 16 is DAMAGE and is a FRACTION of the agent's maximum health -- it
    multiplies by `[esi+0x24]`, which is why -0.5 takes a full bar to half rather
    than removing half a point. Two cuts rather than one, because a single step
    cannot tell a bar that TRACKS health from one that merely reacts once: after
    -0.5 then -0.25 the bar must be at roughly a quarter, not back at a half and
    not empty.

    The recovery step matters as much as the cuts. Damage floors at 1 (it cannot
    kill), so a bar that empties and STAYS empty would mean the row stopped
    tracking rather than that the character died -- and healing back is the only
    way to tell those apart from outside.
    """
    a = agent_id
    return [
        Step(4.0, 0x00A3, [16, a, a, _f32(-0.5)],
             "damage -0.5 on the PLAYER (half of maximum)",
             "the PARTY ROW's red bar, not the HUD bar at the bottom. It must "
             "shorten to about half its width with the name still in place."),
        Step(7.0, 0x00A3, [16, a, a, _f32(-0.25)],
             "damage -0.25 more (quarter of maximum)",
             "about a quarter of the original width. If it went back to half, "
             "the bar is reacting to the message rather than tracking health."),
        # RECOVERY, and the first version of this step KILLED THE CLIENT.
        # `0x00A3 [16, a, a, +0.75]` -- damage as a signed health delta -- is
        # refused fatally: `Assertion: damage.amount <= 0`, AvChar.cpp:5893,
        # OBSERVED 2026-08-13 (harness 20260813T212610, crash dialog captured).
        # Property 16 is DAMAGE, not health, and the client asserts the sign.
        # Int property 42 is the documented refill instead: it assigns
        # health_max = value AND health = 1.0, which this repo has observed
        # since 2026-08-06.
        Step(7.0, 0x009F, [42, a, 100],
             "RECOVERY: int property 42 = 100 (sets max AND refills)",
             "the bar must grow back to full width. A bar that never returns was "
             "not tracking health -- damage floors at 1 and cannot have killed "
             "the character. RUN 2026-08-13 and it DOES NOT REFILL: the row "
             "stayed at 24.0% and the HUD kept reading 25 for nine frames. The "
             "'assigns health_max AND health = 1.f' reading is ldufr/Headquarter's "
             "-- UPSTREAM, not a retail observation -- and this is the run that "
             "shows it does not reproduce when the value EQUALS the existing "
             "maximum. Try 200 to separate a same-value no-op from a wrong "
             "reading; see RESKIN.md 18.12."),
    ]


def _player_flags_steps(agent_id):
    """GAME_SMSG 0x003C -- the player-record flag word this server has never sent.

    MEASURED 2026-08-13 over ArenaNet's own captures, read whole with
    `tape.decode_all` (the per-event idiom loses and invents messages): **12 of 12
    live game connections carry it**, at t=0.23-0.73s, i.e. inside the instance
    load. Our server has sent it ZERO times in 190 played captures.

    The SHAPE is the part worth writing down, because the party dive reported it as
    "(player_number, set=4, clear=7)" and the corpus says otherwise. Censused over
    all 423 sends in those 12 connections:

        mask (the second dword) is 7 in 423 of 423
        value (the first) is 4 x287, 5 x60, 0 x48, 7 x12, 6 x12, 1 x4

    Every value lies inside the mask and the mask never varies. That is a
    (value, mask) pair, not (set, clear): three bits, cleared then written, which
    matches the handler doing an `and` at 0x0080EC26 and an `or` at 0x0080EC48 into
    `[playerRec+0x34]` -- the same ctx+0x80C stride-0x50 array 0x00B0/0x00B1 write.
    UPSTREAM for the two addresses (the party dive); OBSERVED for the wire values.

    A solo player is (player, 4, 7) in every single-connection capture, so bit 2 is
    the one a lone character carries. This sweeps all three bits rather than sending
    only retail's value, because a null on 4 alone would not say whether the message
    does nothing or whether 4 is simply what we already look like.
    """
    p = PROBE_PLAYER_NUMBER
    return [
        Step(2.0, 0x003C, [p, 4, 7], "flags -> 4 (retail's own solo value)",
             "anything at all: the party row, the nameplate, the chat, the "
             "compass. Retail sends exactly this for a lone player."),
        Step(6.0, 0x003C, [p, 0, 7], "flags -> 0 (all three bits CLEAR)",
             "if step 1 changed nothing, does REMOVING the bits change "
             "something? We may already look like 4 by default."),
        Step(6.0, 0x003C, [p, 7, 7], "flags -> 7 (all three bits SET)",
             "bits 0 and 1, which no solo capture carries. If nothing has "
             "moved by here, 0x003C is invisible in a one-player instance."),
    ]


def _level_steps(agent_id):
    return [
        Step(2.0, 0x009F, [PROP_LEVEL, agent_id, 1], "level -> 1",
             "the nameplate above the character. Does it read 1?"),
        Step(6.0, 0x009F, [PROP_LEVEL, agent_id, 15], "level -> 15",
             "the nameplate again. 15?"),
        Step(6.0, 0x009F, [PROP_LEVEL, agent_id, 20], "level -> 20",
             "20? If all three tracked, property 36 is level and this is settled."),
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


def _armor_steps(agent_id):
    # EXPLORATORY, and labelled as such. 0x006F is {agent_id, dword, dword} and
    # which dword is the slot and which the model is NOT established -- the
    # study calls the 0x006D/6E/6F mapping disputed. So try both orders on one
    # piece before doing anything with the rest.
    name, file_id, model_id = WARRIOR_ARMOR[0]
    return [
        Step(2.0, 0x006F, [agent_id, 0, model_id],
             f"equip {name}: (slot 0, model {model_id})",
             "the character. Any chest armour? Any change at all?"),
        Step(6.0, 0x006F, [agent_id, model_id, 0],
             f"equip {name}: (model {model_id}, slot 0)",
             "the character. Did the reversed argument order do something?"),
        Step(6.0, 0x006F, [agent_id, file_id, model_id],
             f"equip {name}: (file 0x{file_id:X}, model {model_id})",
             "the character. Third reading of the same two fields."),
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


def _f32(x):
    """A float, as the dword our schema says this field is.

    Not a workaround. The client's own message table types this field as
    "unsigned int, 4 wire bytes widened to a 4-byte slot" (studies/msgtable
    FINDINGS.md §2.2 type 4), i.e. a straight copy -- the generic deserializer
    never interprets it, and the per-opcode HANDLER is what reads the bits as a
    float. So the schema is right that it is four opaque bytes, and the caller is
    responsible for what those bytes mean.
    """
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _damage_steps(agent_id):
    """Is damage an agent property, and is it absolute or a fraction?

    THERE IS NO DAMAGE MESSAGE. Damage arrives as a property on
    AGENT_PROPERTY_UPDATE_FLOAT_TARGET (0x00A3) and is ADDED to the target's
    health -- so damage is a negative number. The handler is four lines in
    ldufr/Headquarter (code/client/agent.c:823-867):

        case AG_ATTR_DAMAGE:            // 16
        case AG_ATTR_CRITICAL_DAMAGE:   // 17
        case AG_ATTR_ARMOR_IGNORING:    // 55
            target->health = clampf(target->health + value, 0.f, health_max);

    Field order is prop_id, TARGET, CAUSE, value -- target before cause, which is
    the opposite of the natural reading, and getting it backwards would damage
    the attacker.

    WHAT THIS PROBE IS ACTUALLY FOR. The same file makes the units contradictory,
    and no source on disk resolves it. Setting health (int property 42) assigns
    `health_max = value` and `health = 1.f` -- a FRACTION -- and then the damage
    path clamps that fraction against health_max as though it were absolute.
    GWCA independently comments the live client's AgentLiving.hp as a percentage
    (PLAN.md §1.7). One of those readings is wrong and the client is the only
    thing that can say which.

    So the two hypotheses are separated by MAGNITUDE, and each step is chosen so
    that exactly one hypothesis predicts a visible change:

        -0.25   fraction: a quarter of the bar.  absolute: 0.25 of 100, invisible.
        -25.0   fraction: 2500%, instant death.  absolute: a quarter of the bar.

    NEEDS NO NPC. This tests the whole combat delivery mechanism against the body
    we already spawn, so a failure localises to health state we have never sent
    rather than to anything about enemies.

    NOT TESTED HERE, deliberately: whether damage works with no health state at
    all. Health cannot be un-set once sent, so that question needs its own run,
    and asking it first risks an assert that would cost the rest of this one.
    """
    return [
        Step(2.0, 0x009F, [42, agent_id, 100],
             "health -> 100 (int property 42)",
             "the health bar / orb. Did one appear, or change? Any number on it? "
             "Nothing we send today carries health, so this is the first time "
             "the client has been told the character has any."),
        Step(6.0, 0x00A3, [16, agent_id, agent_id, _f32(-0.25)],
             "damage -0.25 (property 16, target and cause both us)",
             "the health bar. A quarter gone means health is a FRACTION and the "
             "0..1 reading wins. No visible change means it is ABSOLUTE and 0.25 "
             "of 100 was simply too small to see -- which step 3 then confirms."),
        Step(6.0, 0x00A3, [16, agent_id, agent_id, _f32(-25.0)],
             "damage -25.0",
             "the health bar. A quarter gone here means ABSOLUTE. Instant death "
             "means FRACTIONAL and this was 2500% of the bar -- in which case "
             "watch what death looks like, because we have never seen it."),
        # THERE IS NO FOURTH STEP, and this is the finding rather than an
        # omission. It used to send +25.0 as a control on "the value is added".
        # ANSWERED 2026-08-06, by the client, with its own assertion:
        #
        #   Assertion: damage.amount <= 0
        #   P:\Code\Gw\AgentView\AvChar.cpp(5893)
        #
        # A positive value on this property is ILLEGAL and takes the client down.
        # That is ArenaNet's own text, so it is the strongest class of evidence
        # we get: the channel is damage-only, the sign convention is fixed at the
        # client, and the field is literally named `damage.amount` in their
        # source. Healing must travel some other way -- unknown, and NOT to be
        # guessed at by flipping this sign again.
        #
        # Re-running this probe is safe and repeatable as it now stands. Adding
        # the positive step back is not.
    ]


def _die_0x2d_steps(agent_id):
    """SUPERSEDED, and kept because the negative is worth reading.

    This asked whether 0x002D kills. It does not -- not an NPC, not the player.
    Its handler's body is gated on a moving-agent flag and zeroes a velocity
    (studies/enemy/PLAN.md 6h), and ldufr's name AGENT_PLAYER_DIE is not
    supported by the code. Death turned out to be a BIT, not a message: see the
    `death` probe below.

    Does 0x002D kill, when damage demonstrably cannot?

    The `damage` probe established that health CLAMPS AT 1: 2500 damage against
    75 left the character standing, with no death animation and no state change.
    So an enemy that only deals damage can never finish a kill, and something
    else has to end it. AGENT_PLAYER_DIE (0x002D, agent_id and nothing else) is
    the candidate -- one dword, and the only message in the catalogue whose name
    says death.

    Steps 1 and 2 are not filler. They re-run the damage measurement, which makes
    this probe its own control: if -25.0 does not land the bar on 1 exactly as it
    did before, the session is not comparable and step 3 proves nothing.

    Ends on the death deliberately. Nothing follows it, so the state can be read
    at rest -- the lesson attr_sweep taught by destroying its own evidence.
    """
    return [
        Step(2.0, 0x009F, [42, agent_id, 100],
             "health -> 100 (int property 42)",
             "the health bar reads 100. Same as the damage probe's step 1."),
        Step(6.0, 0x00A3, [16, agent_id, agent_id, _f32(-25.0)],
             "damage -25.0 (down to the floor)",
             "the health bar should read 1, and the character should still be "
             "standing. If it reads anything else, stop -- this session does not "
             "reproduce the damage probe and step 3 is uninterpretable."),
        Step(6.0, 0x002D, [agent_id],
             "AGENT_PLAYER_DIE",
             "EVERYTHING. Death animation? Ragdoll? A greyed screen, a resurrect "
             "prompt, a death-penalty change in the top-left, a party-window "
             "state? Or nothing at all, in which case death needs more than this "
             "one dword and we have narrowed it rather than found it. Nothing "
             "follows this step -- take your time."),
    ]


# The three allegiance FourCCs, in the order they go out. Two are MEASURED from
# gw-preservation's agent table ('play' for party-allied NPCs, 'nonc' for
# non-combatant townsfolk, studies/enemy/PLAN.md section 4); 'mons' is OUR
# INFERENCE from the pattern and appears in no source on disk.
#
# Order is load-bearing. The invented one goes LAST so that if the client
# rejects an unknown token, the two measured agents are already on screen and
# the run still returns its main result.
ALLEGIANCE = [
    ("play", 0x706C6179, "MEASURED -- gw-preservation's party-allied NPCs"),
    ("nonc", 0x6E6F6E63, "MEASURED -- its merchants, collectors and guards"),
    ("mons", 0x6D6F6E73, "INFERRED by us. In no source anywhere."),
]



def _allegiance_steps(agent_id, origin):
    """Three bodies, side by side, differing in one dword. Which one is an enemy?

    THIS IS THE ENEMY QUESTION, and it costs six packets and no server code.
    Field 12 of WORLD_CREATE_AGENT is an allegiance FourCC -- we already send
    'play' in it for the player's own body without ever having asked what it
    does. If hostility lives there, an enemy is one dword away from a friend.

    Player-class agents rather than NPCs on purpose. It reuses the exact
    WORLD_CREATE_AGENT the player's own body is built from, so the only thing
    that differs between the three is the token under test and the position.
    Bringing NPC models into it would add a model file id we do not have and a
    second reason for a body to fail to appear.

    Each carries its token as its NAME, so the nameplates are the legend: no
    correlating by position, and a screenshot read later still says which is
    which. Same trick that mapped the 15-dword attribute set.

    WHAT TO LOOK FOR, in order of how much it would settle:
      - nameplate COLOUR differing between the three
      - whether clicking one targets it, and whether the attack command is
        offered on any of them
      - whether the compass shows them in different colours
    """
    ox, oy, plane = origin
    out = []
    # A triangle around the spawn rather than a line, because the camera starts
    # behind the character and a row in front would put the far ones off screen.
    spots = [(ox + 250, oy), (ox, oy + 250), (ox - 250, oy)]
    for i, ((tag, token, provenance), (x, y)) in enumerate(zip(ALLEGIANCE, spots)):
        num = i + 2                      # 1 is the player
        name = f"Token {tag}"
        # PLAYER_CREATE first: SendWorldAgents sends it before the agent for
        # every player-class body, and it is what carries the name.
        out.append(Step(
            3.0 if i else 2.0, 0x0059,
            [num, num, APPEARANCE_WARRIOR, 0, 0, 0, name],
            f"PLAYER_CREATE agent {num}: {name!r}",
            "nothing yet -- the body arrives with the next packet."))
        out.append(Step(
            1.0, 0x0020,
            [num,                                   # agent_id
             CHAR_CLASS_PLAYER_BASE | num,          # model_id
             AGENT_TYPE_LIVING,
             AGENT_KIND_PLAYER,                     # h000B
             (float(x), float(y)),                  # position
             plane,
             (1.0, 0.0),                            # direction
             1,                                     # h001E
             DEFAULT_RUN_SPEED,
             1.0,                                   # h0023
             0x41400000,                            # h0027
             token,                                 # <-- THE VARIABLE
             0, 0, 0, 0, 0,
             (0.0, 0.0),
             (INF, INF),
             0, 0,
             (INF, INF),
             0],
            f"WORLD_CREATE_AGENT {num} @ ({x:.0f}, {y:.0f}) token '{tag}'",
            f"a second body should appear. Its nameplate names its own token. "
            f"{provenance}. Compare its nameplate colour against the others, and "
            f"try to click and attack it."))
    return out



# One real NPC definition, transcribed from gw-preservation's agent table as a
# PROBE INPUT and nothing else. That repo carries no license, so these numbers
# are a lead to be tested rather than data to import -- if the NPC renders, the
# id gets re-derived and recorded as our own observation, and if it does not,
# nothing was adopted. See studies/enemy/PLAN.md section 5 on the licensing.
#
# `hatcher_collector`, an Ascalon collector. Its file id 116228 is the strongest
# id available anywhere: GWLP-R's mock NPC used the same number in 2013, which is
# two lineages thirteen years apart agreeing on one value.
# Our handle for the Hatcher type within a probe run. Deliberately 2, which is
# clear of the server's standing enemy at definition 3 -- the definition index
# is a raw array index on the client and reusing one would put two types in
# one slot.
PROBE_DEFINITION = 2


def _npc_agent_steps(agent_id, origin):
    """Will the client render a monster-class agent, and does it need a definition?

    The allegiance probe proved the client happily spawns extra bodies, but it
    spawned PLAYERS -- model class 0x3, a preceding PLAYER_CREATE, agent-kind 5 --
    and the client treated them as players in every respect that was checked.
    Everything about an ENEMY starts one step earlier than that: class 0x2.

    Two questions, in one run, ordered so the valuable one cannot be lost:

      1. Does a monster-class agent with a real NPC definition render a body?
         This is E2 in studies/enemy/PLAN.md, and it turns on whether file id
         116228 still addresses a model in build 38797's archive. It is a 2013
         number that an unrelated project was still using in 2026, which is why
         it is worth one packet before anyone goes model-hunting in Gw.dat.

      2. Are the definition messages REQUIRED? Step 4 creates a monster-class
         agent whose definition index was never defined. If it renders anyway,
         properties are decoration; if it renders nothing, they are mandatory;
         if it asserts, that is the loudest answer of the three.

    Question 2 goes last on purpose. An undefined model is exactly the kind of
    thing that takes a client down -- a missing file id already killed this
    project's map load once with `Assertion: fileId` -- and if it does, the
    answer to question 1 is already on screen.

    NO PLAYER_CREATE anywhere here. That message is what made the last probe's
    bodies read as players, and sending it for an NPC would repeat the confound.
    """
    ox, oy, plane = origin
    h = HATCHER
    return [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}: "
             f"file {h['file_id']}, prof {h['profession']}, level {h['level']}",
             "nothing yet. This defines a TYPE, not a body."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION} -> model {h['model_id']}",
             "still nothing. One more packet before anything can appear."),
        Step(1.0, 0x0020,
             create_agent(2, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                           AGENT_KIND_NPC, ox + 250, oy, plane),
             "WORLD_CREATE_AGENT 2, monster class, defined",
             "THE QUESTION. Is there a body? What does its nameplate look like "
             "-- colour, name, level? Is there a Trade button, or something "
             "else, or nothing? Compare it against the light-blue player bodies "
             "the last probe made: anything that differs is the class nibble "
             "doing work."),
        Step(8.0, 0x0020,
             create_agent(3, CHAR_CLASS_MONSTER_BASE | 99,
                           AGENT_KIND_NPC, ox - 250, oy, plane),
             "WORLD_CREATE_AGENT 3, monster class, definition 99 NEVER DEFINED",
             "the control. Nothing, a placeholder, or a crash -- all three are "
             "answers. If the client is still up when you read this, note "
             "whether a second body appeared."),
    ]


def _npc_allegiance_steps(agent_id, origin):
    """Is the team token an IDENTITY compared between agents, not a magic word?

    The first allegiance probe guessed at magic values and was confounded by
    spawning player-class bodies. This one is built on a reading of the client
    binary instead, and it changes the question.

    MEASURED in Gw.exe (build 38797, static, file never executed):

      - 'play' -- the token this server has always sent, and which three
        lineages agree on -- appears NOWHERE in the image as a dword constant.
        Not once. The client cannot be comparing the field against it.
      - The only allegiance-shaped constants in the whole binary are 'nonc' and
        'nonn', and they occur in exactly one function, which is four
        instructions long:

            0x1AB130   mov  eax, [ebp+8]
                       cmp  eax, 'nonc'  ; 0x6E6F6E63
                       je   yes
                       cmp  eax, 'nonn'  ; 0x6E6F6E6E
                       je   yes
                       xor  eax, eax     ; return 0
            yes:       mov  eax, 1

    So the field is an opaque team IDENTITY, and 'play' works for the player not
    because the client knows the word but because the player's own agent carries
    the same value -- equality makes them allies. On top of that, the client
    special-cases exactly two values, and 'non-combatant' is the obvious reading
    of both.

    THE HYPOTHESIS: same token as the player = ally; 'nonc'/'nonn' = neutral and
    unattackable whatever the player's token is; anything else = a different
    team, and therefore an enemy.

    That predicts step 6 is the hostile one -- not because 'mons' is a magic
    word, but precisely because it is NOT one. Any unrecognised value should do,
    and if the hypothesis is right the specific bytes are irrelevant.

    Agents arrive ONE AT A TIME, eight seconds apart, because they share a
    definition and therefore a name -- there is no way to label them on screen
    the way the player-class probe labelled its bodies, so order in time is the
    label. Watch each one appear.
    """
    ox, oy, plane = origin
    h = HATCHER
    tokens = [
        (0x706C6179, "'play' -- the player's own token",
         "an ALLY. Same team as you, so equality should make it friendly."),
        (0x6E6F6E63, "'nonc' -- the client's own constant",
         "NEUTRAL. This is one of the two values that function accepts."),
        (0x6E6F6E6E, "'nonn' -- the client's other constant",
         "also neutral. Any difference from the last one is the whole reason "
         "the client bothers to distinguish them."),
        (0x6D6F6E73, "'mons' -- a value the client has never seen",
         "THE TEST. Under the hypothesis this is an ENEMY: red nameplate, red "
         "compass dot, and targetable as a foe. The bytes themselves should not "
         "matter -- being unrecognised is the whole point."),
    ]
    spots = [(ox + 300, oy), (ox, oy + 300), (ox - 300, oy), (ox, oy - 300)]
    steps = [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION} (Hatcher, known good)",
             "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}",
             "nothing yet. All four bodies below share this one definition, so "
             "they will all look like Hatcher and all carry his name."),
    ]
    for i, ((token, label, expect), (x, y)) in enumerate(zip(tokens, spots)):
        steps.append(Step(
            8.0, 0x0020,
            create_agent(4 + i, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                          AGENT_KIND_NPC, x, y, plane, allegiance=token),
            f"agent {4 + i}, token {label}",
            f"a Hatcher appears. Expected: {expect} Note its NAMEPLATE COLOUR "
            f"and its COMPASS DOT COLOUR, and try clicking it. This is an "
            f"outpost so attacking may be refused whatever the answer -- colour "
            f"is the signal that still works here."))
    return steps


def _enemy_damage_steps(agent_id, origin):
    """Can the client show an ENEMY taking damage? And which slot is the target?

    Everything so far damaged the player. This aims the same channel at a
    hostile body, which is the first thing in the project that would look like a
    fight, and it does it WITHOUT needing the server to react to anything -- the
    steps are on a timer, so no interaction logic has to be invented first.

    IT ALSO SETTLES A FIELD ORDER THAT SECTION 6b COULD NOT. That probe sent
    target and cause as the same agent, so the two slots were indistinguishable
    and the order rested on ldufr's struct alone. Here they differ: target is the
    NPC, cause is the player. If the NPC's bar drops, the order is confirmed
    against our own client. If the PLAYER's bar drops instead, it is reversed and
    every damage packet this project would have sent was aimed backwards.

    The last step asks the death question on a disposable body rather than on the
    player -- a better place to ask it, since 6b showed the player's health floors
    at 1 and never dies.
    """
    ox, oy, plane = origin
    h = HATCHER
    ENEMY = 7
    return [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0020,
             create_agent(ENEMY, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                           AGENT_KIND_NPC, ox + 300, oy, plane, allegiance=0x6D6F6E73),
             f"WORLD_CREATE_AGENT {ENEMY}, token 'mons' -- a hostile Hatcher",
             "a RED Hatcher. Click it to target it, and leave it targeted for "
             "the rest of the probe so its health bar stays on screen."),
        Step(6.0, 0x009F, [42, ENEMY, 100],
             f"health 100 on agent {ENEMY}",
             "the TARGET's health bar, in the target window at the top. Does it "
             "read 100?"),
        Step(6.0, 0x00A3, [16, ENEMY, agent_id, _f32(-0.25)],
             f"damage -0.25  target={ENEMY} (enemy)  cause={agent_id} (you)",
             "THE TEST. A floating damage number over the enemy, and its bar to "
             "75? Then the channel works on other agents and the field order is "
             "right. IF YOUR OWN HEALTH DROPS INSTEAD, the two agent slots are "
             "reversed -- that is a bigger finding than the one being looked "
             "for, so check your own bar too."),
        Step(6.0, 0x00A3, [16, ENEMY, agent_id, _f32(-0.5)],
             f"damage -0.5 on agent {ENEMY}",
             "the enemy's bar should be near 25. Confirms it accumulates rather "
             "than being a one-off."),
        Step(8.0, 0x002D, [ENEMY],
             f"AGENT_PLAYER_DIE on agent {ENEMY}",
             "EVERYTHING. Does the enemy die -- animation, ragdoll, corpse, does "
             "it vanish? Section 6b proved damage alone floors at 1 and cannot "
             "kill, so if anything dies here, this is the message that does it. "
             "Nothing follows; take your time."),
    ]


def _attack_anim_steps(agent_id, origin):
    """Does an EQUIPPED weapon give the player a weapon_attack_speed?

    THE ONE QUESTION THIS ASKS, and the reason it is worth a launch. The client
    refuses to animate a melee swing unless both `[esi+0xEC]`
    (weapon_attack_speed) and `[esi+0xF0]` are non-zero -- SOURCED, read at
    0x007F82C0, where a zero at +0xEC pushes line 0x12b7 (4791) into the assert
    call. Ours were zero, so `attack_started` took the client down on
    `Assertion: m_attackInterval / P:\\Code\\Gw\\AgentView\\AvChar.cpp(4791)`.

    Nothing in the image WRITES either offset by displacement, so what sets
    them is NOT FOUND. GWCA calls +0xEC "the base attack speed of the last
    attack's weapon", which reads as the client computing it from the equipped
    weapon rather than being told -- and until 2026-08-06 our hammer was drawn
    on the body (0x006E) with no bag behind it, which renders a weapon without
    equipping one. It now goes into a real equipped-items bag at login.
    studies/enemy/PLAN.md 6o, "Where to go next", item 1.

    WHY A PROBE AND NOT A CLICK. The shipped path already sends this packet on
    every swing, but only once a click has ordered an attack, and a click has
    to land on the enemy's body on screen. This asks the same question with no
    aiming and no interaction logic in the way: one packet, on a timer.

    THE CRASHING STEP IS LAST, ON PURPOSE. One branch of the prediction ends
    the session, so nothing may depend on running after it. The crash is the
    documented outcome rather than an accident -- the cage keeps the dump local
    (studies/enemy/PLAN.md 6b) and `toolkit/harness/read_error_dialog.py` reads
    the assert text without pressing "Send report to ArenaNet".
    """
    ox, oy, plane = origin
    h = HATCHER
    ENEMY = 7
    # +150, with the standing enemy at +300 -- the owner's placement, and it is
    # better than either of the two this probe tried first. Both bodies end up
    # on screen, at different distances, so they can be told apart by eye
    # without turning the standing enemy off and changing what is being tested.
    #
    #   +300 (first try) -> lands EXACTLY on the standing enemy, which
    #     enemy_spot puts at +300 whenever that is walkable. Two Hatchers in
    #     one spot, z-fighting, nameplates stacked, and an animation whose
    #     performer could not be told from its neighbour.
    #   +600 (second try) -> clear of it, and out of sight behind a wall. The
    #     only Hatcher on screen was then the STANDING one, which neither
    #     packet ever names -- so "the Hatcher did not swing" meant nothing.
    #
    # enemy_spot only ever offsets by +/-300, so +150 can never collide with it.
    ex, ey = ox + 150, oy
    return [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0020,
             create_agent(ENEMY, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                          AGENT_KIND_NPC, ex, ey, plane,
                          allegiance=0x6D6F6E73),
             f"WORLD_CREATE_AGENT {ENEMY}, token 'mons' -- a hostile Hatcher",
             "TWO red Hatchers, one behind the other. The NEAR one is this "
             "probe's and is the only one the packets below ever name; the FAR "
             "one is the server's standing enemy and should never move. If "
             "they are on top of each other, stop -- the placement is wrong "
             "again and nothing below can be read."),
        # Spawned rather than reusing the standing enemy at agent 10 so the
        # probe still runs under --no-enemy, and so it cannot be confused by
        # the combat loop hitting the same body on a timer.
        #
        # THIS AGENT NEEDS AN ATTACK SPEED TOO, and the first run of this probe
        # is why. The player had one and the client still died on
        # m_attackInterval -- because the assert does not fire on the packet.
        # attack_started QUEUES a request at AvChar+0xCC and the per-frame tick
        # processes it a frame later, so the AvChar that asserts is whichever
        # one the request was queued on, and the two agent slots of this
        # message are victim and attacker in an order we have not established.
        # Every living agent gets one; that is what the client requires anyway,
        # since AvChar's constructor writes 0.0 to both fields.
        Step(1.0, 0x0035, [ENEMY, _f32(1.33), _f32(1.0)],
             f"ATTACK_SPEED(agent {ENEMY}: base 1.33s, modifier 1.0)",
             "nothing visible. 1.33 is a real number from the wiki's table "
             "rather than an invented one, but a Hatcher's true rate is "
             "unknown -- the client only demands that it is not zero."),
        # A/B ON THE SLOT ORDER, which is now the open question and which the
        # first run could not answer because both bodies were in one place.
        #
        # GWCA's note on generic value 4 reads "caster_id is victim, target_id
        # is attacker" -- i.e. this id INVERTS the usual roles. Our two agent
        # slots are named target-then-cause after 0x00A3, where section 6f
        # MEASURED the first slot as the one damaged. If both were true, the
        # first slot here would be the victim. The first run says otherwise:
        # sent first=the Hatcher, and a HATCHER swung.
        #
        # Ten seconds apart, on two bodies that are now hundreds of units
        # apart, so "which one moved" is answerable by looking.
        Step(8.0, 0x00A0, [4, ENEMY, agent_id, 0],
             f"attack_started  slot1={ENEMY} (NEAR Hatcher)  slot2={agent_id} (you)",
             "STEP A -- WATCH THE NEAR HATCHER. PREDICTION: it swings and you "
             "do not. If YOUR character swings instead, the slots are "
             "victim-then-attacker and GWCA's note is right.\n"
             "      Either way the client must NOT crash. It did, in every "
             "session before the attack speed was sent."),
        Step(12.0, 0x00A0, [4, agent_id, ENEMY, 0],
             f"attack_started  slot1={agent_id} (you)  slot2={ENEMY} (NEAR Hatcher)",
             "STEP B -- THE SAME PACKET, SLOTS SWAPPED. WATCH YOURSELF. "
             "PREDICTION: now YOUR character swings the hammer and the Hatcher "
             "does not.\n"
             "      A and B together are the whole experiment: if each step "
             "moves the body named in slot 1, slot 1 is the attacker. If the "
             "SAME body moves both times, slot 1 is not what selects it and "
             "the answer is somewhere else."),
    ]


# The agent EFFECTS bitfield, carried by 0x00F0 and 0x00F1. Bit 4 is death.
#
# SOURCED, and corroborated by two independent uses in the client binary:
#
#   0x008183F0   mov  [ebx+0x30], eax     ; the effects word, stored on the record
#                test al, 0x10            ; bit 4
#                je   skip
#                fldz ... call 0x9215F0   ; zero the health pool -- the SAME
#                fldz ... call 0x921780   ; callee property 34 uses
#                (and again for two further sub-structures)
#
#   0x00818191   mov  eax, [edi+0x30]     ; the health path reads the same word
#                shr  eax, 4              ; and computes !((effects >> 4) & 1),
#                not  eax                 ; i.e. "is this agent NOT dead",
#                and  eax, 1              ; passing it to the health setter
#
# The second explains a result this project has had for days without
# understanding it: int property 42 always REFILLED the health bar, because the
# client only refills an agent it does not believe is dead.
EFFECT_DEAD = 0x10


def _death_steps(agent_id, origin):
    """Kill something, then bring it back.

    Seven mechanisms failed before this: AGENT_PLAYER_DIE at an NPC and at the
    player, AGENT_ALLY_DESTROY, float health zero, int health zero, damage past
    its floor, and an absolute health modifier past zero. All seven were guesses
    at a MESSAGE. Death is not a message -- it is a bit in the agent's effects
    word, and the two places the binary uses that bit agree with each other.

    The last step is the one that matters. A bit that kills should also un-kill,
    and if the body gets up again the mechanism is not merely correlated with
    death, it IS death. A one-way result would be much weaker: plenty of things
    can break an agent once.
    """
    ox, oy, plane = origin
    h = HATCHER
    E = 7
    return [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0020,
             create_agent(E, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                           AGENT_KIND_NPC, ox + 300, oy, plane, allegiance=0x6D6F6E73),
             f"WORLD_CREATE_AGENT {E}, hostile Hatcher",
             "a red Hatcher. TARGET IT and keep it targeted."),
        Step(4.0, 0x009F, [42, E, 100], f"health 100 on agent {E}",
             "target bar reads 100."),
        Step(5.0, 0x00A3, [16, E, agent_id, _f32(-0.5)],
             "control: damage -0.5",
             "50 damage, bar to 50 -- the session reproduces, so what follows "
             "means something."),
        Step(7.0, 0x00F1, [E, EFFECT_DEAD],
             f"AGENT_UPDATE_EFFECTS on agent {E}, effects = 0x10 (the DEAD bit)",
             "THE ANSWER, IF IT IS ONE. Does it die? Death animation, ragdoll, a "
             "corpse on the ground, the nameplate greying or vanishing, the bar "
             "emptying on its own? Anything a live body would not do."),
        Step(8.0, 0x00F1, [E, 0],
             f"AGENT_UPDATE_EFFECTS on agent {E}, effects = 0 (clear the bit)",
             "THE CONTROL, and the more important half. Does it get back up? A "
             "bit that kills should un-kill. If the body revives, this is death "
             "rather than something merely correlated with it."),
    ]


def _health_props_steps(agent_id, origin):
    """The health properties the client dispatches and we have never sent.

    Five death candidates failed. Then the float-property jump table came out of
    the binary (studies/agentprops/FINDINGS.md) and named the properties the
    client actually acts on -- and three of them are HEALTH properties this
    project has never once sent: 34, 55 and 56. We had been sending 16 (damage)
    and 42 (max health) and nothing else.

    Reading the two cases side by side shows they are not the same kind of thing:

      prop 16, DAMAGE          fld [esi+0x24]      ; the agent's max health
      prop 55, ARMOR_IGNORING  fmul [ebp+0xc]      ; x the value we send
                               -> a FRACTION, and byte-identical between the two

      prop 34, HealthModifier1 fld [ebp+0xc]       ; the value, RAW
                               -> ABSOLUTE, and a different callee entirely

    So 34 is the only health property that takes a real quantity rather than a
    proportion, which makes it the one that can name zero exactly. Damage cannot:
    it floors at 1 however hard it is hit (section 6b).

    Ordered cheapest-to-interpret first. Every step is on a disposable NPC, so
    nothing here can cost the session.
    """
    ox, oy, plane = origin
    h = HATCHER
    E = 7
    return [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0020,
             create_agent(E, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                           AGENT_KIND_NPC, ox + 300, oy, plane, allegiance=0x6D6F6E73),
             f"WORLD_CREATE_AGENT {E}, hostile Hatcher",
             "a red Hatcher. TARGET IT and keep it targeted."),
        Step(4.0, 0x009F, [42, E, 100], f"health 100 on agent {E}",
             "target bar reads 100."),
        Step(5.0, 0x00A3, [16, E, agent_id, _f32(-0.5)],
             "control: damage -0.5 (property 16, a FRACTION)",
             "50 damage, bar to 50. Reproduces section 6f; if it does not, "
             "nothing below is interpretable."),
        Step(7.0, 0x00A3, [34, E, agent_id, _f32(-50.0)],
             "property 34 HealthModifier1 = -50.0, sent as an ABSOLUTE",
             "THE ASYMMETRY TEST. 34 does not multiply by maximum health, so if "
             "the bar drops by 50 the value is absolute and the two health "
             "channels genuinely differ. If it drops by 5000-worth, it is a "
             "fraction after all and the disassembly was misread."),
        Step(7.0, 0x00A3, [34, E, agent_id, _f32(-1000.0)],
             "property 34 = -1000.0 -- far past zero",
             "THE DEATH TEST. Damage floors at 1 no matter how hard it is hit. "
             "If an absolute health modifier can push past that floor, this is "
             "where something finally dies. Animation? Corpse? Or a bar at 1 "
             "again?"),
        Step(7.0, 0x00A3, [55, E, agent_id, _f32(-1.0)],
             "property 55 ARMOR_IGNORING = -1.0 (a fraction, so exactly 100%)",
             "the last health property we hold. -1.0 of maximum is exactly the "
             "whole bar, which damage can only approach from above. Nothing "
             "follows this step."),
    ]


def _moving_die_steps(agent_id):
    """0x002D does nothing to a STANDING agent. Read out of the client, not guessed.

    Its handler resolves the agent's syncPtr and calls 0x006025F0, whose entire
    body sits behind one test:

        test dword ptr [esi+0x20], 0x20000
        je   return              <-- flag clear: the function does NOTHING

    Every agent we ever aimed this message at was standing still, so all three
    null results are explained by state rather than by the message being inert.

    And what the body does is not death. It zeroes a float PAIR at +0xC8/+0xCC
    and clears +0x4C -- a velocity or a facing, not a corpse -- and the handler
    shares its entire opening with AGENT_STOP_MOVING (0x0028): same context
    fetch, same bounds check, same Array.h assert.

    So: RUN THE WHOLE TIME. Both messages fire twice, alternating, while the
    character is moving. If 0x002D stops you the way 0x0028 does, it is a
    movement cancel, ldufr's name for it is wrong, and death is somewhere else.
    """
    return [
        Step(6.0, 0x002D, [agent_id],
             "0x002D (ldufr calls this AGENT_PLAYER_DIE) -- while RUNNING",
             "KEEP RUNNING. Did you stop dead? Stutter? Nothing? You must be "
             "moving when this lands or the test is void -- the flag it needs "
             "is only set on a moving agent."),
        Step(8.0, 0x0028, [agent_id],
             "0x0028 AGENT_STOP_MOVING -- the known-meaning comparison",
             "still running? Whatever this one does to you is the baseline. If "
             "the previous step felt identical, the two messages are the same "
             "family and 0x002D is not death."),
        Step(8.0, 0x002D, [agent_id],
             "0x002D again -- while RUNNING",
             "confirm the first result. Once is an anecdote."),
        Step(8.0, 0x0028, [agent_id],
             "0x0028 again -- while RUNNING",
             "confirm the baseline. If these two are indistinguishable across "
             "both pairs, that is the answer."),
    ]


def _kill_steps(agent_id, origin):
    """The one death candidate the last run could not reach.

    RUN 2026-08-06 tried four. Three are dead and are not re-sent here:

        float property 42 = 0.0      nothing
        AGENT_ALLY_DESTROY 0x003E    nothing
        int property 42 = 0          refilled the bar to FULL, then killed the
                                     client on `Assertion: range > 0`,
                                     P:\\Code\\Gw\\Char\\CharPool.cpp(98)

    The fourth never ran: it was scheduled seven seconds after that crash and
    went into a socket nobody was reading. So AGENT_PLAYER_DIE aimed at the
    PLAYER -- the one agent its name claims it is for -- is still untested, and
    it is three packets to find out.

    No NPC here. The question is about the player, the enemy was only ever
    context, and a probe that cannot crash is one that can be re-run.

    Why the third candidate refilling matters for this probe's setup: property
    42 is max-health-AND-heal, not current health, so the only way to stand at
    partial health is to set the max and damage down. Step 2 does exactly that.
    """
    return [
        Step(2.0, 0x009F, [42, agent_id, 100],
             "health 100 on YOUR agent",
             "your own health bar reads 100."),
        Step(5.0, 0x00A3, [16, agent_id, agent_id, _f32(-0.9)],
             "damage -0.9 on yourself (90 damage, leaving 10)",
             "90 damage, bar at 10. Section 6b says it floors at 1 and cannot "
             "kill you however hard it is hit, so this is as close to death as "
             "damage alone can bring you."),
        Step(7.0, 0x002D, [agent_id],
             "AGENT_PLAYER_DIE on YOUR OWN agent",
             "THE QUESTION. Death animation, a greyed screen, a resurrect "
             "prompt, a death penalty appearing top-left? Or nothing? The "
             "client's handler for this message is real -- it resolves two "
             "per-agent pointers and calls into them -- so 'nothing' would mean "
             "it needs state we have never sent, not that the message is inert."),
    ]


def _kill_steps_v1_unused(agent_id, origin):
    """What actually kills an agent? Four candidates, one packet each.

    We know what does NOT: damage floors at 1 (section 6b) and
    AGENT_PLAYER_DIE on an NPC does nothing at all (section 6f). So death is
    neither of the two obvious things, and the catalogue offers exactly four
    more candidates worth a packet. Each is sent alone, on the same disposable
    red Hatcher, so whichever works is identified without ambiguity.

      float property 42 = 0.0   Health is a FRACTION -- section 6b proved it by
                                measurement. Nothing has ever tried setting that
                                fraction directly, and the float channel is the
                                one that would carry it. This is the best
                                candidate and it goes first.
      AGENT_ALLY_DESTROY 0x003E One agent id, and the only other message in the
                                catalogue whose name means an agent ceasing to
                                exist. UPSTREAM name, never sent by anyone.
      int property 42 = 0       Sets health_max, which Headquarter shows also
                                refills health. Zero max is either death or a
                                divide-by-zero -- RISKY, so it goes late.
      AGENT_PLAYER_DIE on the   Its name says PLAYER. It did nothing to an NPC;
      PLAYER                    the honest test of the name is to aim it at the
                                one agent it claims to be for. LAST, because a
                                dead player may take the UI somewhere the rest
                                of the probe cannot be read from.
    """
    ox, oy, plane = origin
    h = HATCHER
    E = 7
    return [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0020,
             create_agent(E, CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION,
                           AGENT_KIND_NPC, ox + 300, oy, plane, allegiance=0x6D6F6E73),
             f"WORLD_CREATE_AGENT {E}, hostile Hatcher",
             "a red Hatcher. TARGET IT and keep it targeted -- its health bar is "
             "the instrument for the whole probe."),
        Step(4.0, 0x009F, [42, E, 100], f"health 100 on agent {E}",
             "target bar reads 100."),
        Step(5.0, 0x00A3, [16, E, agent_id, _f32(-0.5)],
             f"damage -0.5 on agent {E}",
             "50 damage, bar to 50. This is the control -- it reproduces section "
             "6f. If it does not, nothing below is interpretable."),
        Step(7.0, 0x00A2, [42, E, _f32(0.0)],
             f"FLOAT property 42 = 0.0 on agent {E}  (health fraction -> zero)",
             "THE BEST CANDIDATE. Health is a fraction, and this sets it to "
             "nothing. Death animation? Corpse? Bar to 0? Or no change at all?"),
        Step(7.0, 0x003E, [E],
             f"AGENT_ALLY_DESTROY on agent {E}",
             "does the body vanish, die, or ignore it? 'Destroy' is not "
             "necessarily 'die' -- a body that disappears cleanly is a REMOVE, "
             "and a corpse is a death. The difference matters for what an enemy "
             "should send."),
        Step(7.0, 0x009F, [42, E, 0],
             f"INT property 42 = 0 on agent {E}  (maximum health -> zero)",
             "RISKY -- zero maximum health is either death or a divide by zero. "
             "If the client is still running, did anything happen?"),
        Step(7.0, 0x002D, [agent_id],
             "AGENT_PLAYER_DIE on YOUR OWN agent",
             "the message did nothing to an NPC, and its name says PLAYER. Does "
             "it kill you? Death screen, resurrect prompt, a death penalty in "
             "the top-left? This is last because a dead player may take the UI "
             "somewhere nothing else can be read from."),
    ]


def _team_token_steps(agent_id):
    # Not a packet probe: the token now goes out at spawn. This exists so the
    # run is recorded with a question attached rather than being assumed fine.
    return []


def _skill_copy_steps(agent_id):
    """Does the lifecycle's third dword have to match the skillbar's 2nd array?

    studies/skillcast/FINDINGS.md section 3: the client walks its eight bar
    slots and acts only on the one where BOTH slot+0x0C == field 2 and
    slot+0x10 == field 3, and slot+0x10 is filled straight out of
    SKILLBAR_UPDATE's second array -- the one every catalogue calls
    `pvp_masks`. If that reading is right, a recharge addressed to the wrong
    copy finds no slot and does nothing at all, silently.

    This is the whole point of the probe: the failure mode is silence, so it
    has to be run against a bar whose copies are deliberately NOT zero.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1],
             "skillbar with copy = 0 in every slot",
             "the bar. Eight icons, as usual."),
        Step(6.0, 0x00E5, [agent_id, bar[0], 0, 10],
             "recharge (skill, copy=0) for 10s",
             "slot 1. The cooldown sweep should start and count down 10s."),
        Step(14.0, 0x00DA, [agent_id, bar, [7] * 8, 1],
             "same skillbar, copy = 7 in every slot",
             "the bar. Eight icons still -- copy is not the id, so nothing "
             "should look different."),
        Step(6.0, 0x00E5, [agent_id, bar[0], 0, 10],
             "recharge (skill, copy=0) -- now the WRONG copy",
             "slot 1. PREDICTION: nothing happens. If it greys out anyway, "
             "field 3 is not matched against the bar and section 3 is wrong."),
        Step(6.0, 0x00E5, [agent_id, bar[0], 7, 10],
             "recharge (skill, copy=7) -- the right copy",
             "slot 1. PREDICTION: NOW it greys out and counts 10s."),
    ]


def _skill_disable_steps(agent_id):
    """Is unnamed opcode 231 'skill disabled'?"""
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(5.0, 0x00E5, [agent_id, bar[1], 0, 30], "229: recharge slot 2, 30s",
             "slot 2 starts a 30-second sweep."),
        Step(6.0, 0x00E7, [agent_id, bar[1], 0], "231 on the same slot",
             "slot 2. PREDICTION: the sweep stops counting down and the icon "
             "stays dark indefinitely -- 231 writes recharge = 0xFFFFFFFF, "
             "which the client's own getter turns into INT_MAX remaining."),
        Step(10.0, 0x00E6, [agent_id, bar[1], 0], "230: recharged",
             "slot 2. PREDICTION: instantly ready again, well before 30s have "
             "passed. 230 writes recharge = 0 with no arithmetic."),
    ]


def _skill_partial_steps(agent_id):
    """Opcode 232 carries a float. Is it 'remaining', with field 4 the total?

    The handler multiplies field 5 by 1000.0 and adds the skill timer, so
    field 5 is seconds and it is what sets the clock. Field 4 is converted to
    a float and handed to the UI alongside it, and never touched otherwise.
    The obvious reading is remaining-vs-total; the sweep's ANGLE is what would
    show it, because a quarter-full arc means the client knows about a 40s
    total it was not given anywhere else.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(5.0, 0x00E8, [agent_id, bar[2], 0, 40, _f32(10.0)],
             "232 on slot 3: field4 = 40, field5 = 10.0f",
             "slot 3. PREDICTION: it counts down TEN seconds, not forty. "
             "Then look at the sweep's starting angle: about a quarter dark "
             "means field 4 is the total; a full dark disc means field 4 is "
             "something else and the UI ignores it."),
        Step(14.0, 0x00E8, [agent_id, bar[3], 0, 0, _f32(2.5)],
             "232 on slot 4: field4 = 0, field5 = 2.5f",
             "slot 4. PREDICTION: a 2.5-second sweep -- fractional, which 229 "
             "cannot express. If it is instead instant or 2 seconds flat, "
             "field 5 is not a float and the fld we read is doing something "
             "else."),
    ]


def _cast_anim_steps(agent_id):
    """What makes a body play the cast animation -- 228, or property 60?

    The headline question of studies/skills section 8, and the static answer
    is unambiguous enough to be worth stating hard: the opcode 228 handler
    touches only a bookkeeping array and a UI notification, it never reaches
    AgentView, AND it returns immediately without doing even that when the
    message names the local player. Property 60 is the one that reaches
    AvApi and queues the animation event.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(5.0, 0x00E4, [agent_id, bar[4], 0], "228 SKILL_ACTIVATE on us",
             "the CHARACTER's body, and slot 5. PREDICTION: absolutely "
             "nothing, in both places. The handler compares the message's "
             "agent id against the local player's and returns."),
        Step(8.0, 0x009F, [PROP_CAST_SKILL, agent_id, bar[4]],
             "property 60 = the same skill id",
             "the character's body. PREDICTION: THIS is the one that plays "
             "the casting animation. If it does, the cast animation is a "
             "property update and 228 is bookkeeping."),
        Step(8.0, 0x00E3, [agent_id, bar[4], 0], "227 to close the cast",
             "nothing should visibly change; the client is releasing a "
             "pending entry it never created for us. Watch Gw.log for "
             "'Pending skill 320 copy 0 not found' -- that message is the "
             "client telling us in words what field 3 is called."),
    ]


def _unlock_211_steps(agent_id):
    """Opcode 211 is unnamed everywhere and shaped like both unlock messages.

    Statically it writes a second skill bitmap into ChCliSkill's context, at
    the member BEFORE the one 219 writes, and -- unlike 219 -- broadcasts no
    UI notification. Its write path has exactly one caller, its own handler,
    and nothing in the image reads the array it fills. So the prediction is
    that it does nothing observable, and the value of running it is that a
    NULL result here is informative rather than a dead end.
    """
    empty = [0] * 128
    ours = [0] * 128
    for sid in range(PROBE_BAR_SKILL, PROBE_BAR_SKILL + 8):
        ours[sid // 32] |= 1 << (sid % 32)
    return [
        Step(2.0, 0x00DB, [empty], "219: character skills -> none",
             "the Skills and Attributes panel (K). Note what is listed."),
        Step(8.0, 0x00D3, [ours], "211: our eight bar skills",
             "the same panel, and the skill picker. PREDICTION: no change "
             "anywhere. If something DOES change, 211 has a reader we did "
             "not find and section 5 needs reopening."),
        Step(8.0, 0x00DB, [ours], "219: the same eight, via 219 this time",
             "the same panel. PREDICTION: this one does change it -- 219 is "
             "the bitmap the client bit-tests before answering 'how many "
             "copies of this skill do you own'."),
    ]


def _buff_type_steps(agent_id):
    """Opcode 66 field 3: Headquarter's `effect_type` or GWCA's `attribute_level`?

    studies/skillcast section 14: the client stores field 3 at buff record
    +0x04 and does not interpret it in ChCliBuff at all, so static analysis
    runs out here. The two readings predict visibly different things, which is
    what makes this worth a probe rather than an argument.

    KEEP buffId SMALL. GmEffect:3030 asserts
    `buffId < (CTL_EFFECT_UPKEEP_TERM - CTL_EFFECT_UPKEEP_FIRST)` -- the id
    indexes a UI frame-code range, so a large one asserts in the client the way
    an out-of-range unlock bit does.
    """
    skill = PROBE_BAR_SKILL
    return [
        Step(2.0, 0x0042, [agent_id, skill, 0, 1, _f32(30.0)],
             "66: field3 = 0 (Headquarter: condition/shout)",
             "the effect area above the skill bar. Note WHERE the icon "
             "appears and what its tooltip says."),
        Step(7.0, 0x0044, [agent_id, 1], "68: remove it", "the icon goes."),
        Step(4.0, 0x0042, [agent_id, skill, 14, 2, _f32(30.0)],
             "66: field3 = 14 (Headquarter: enchantment)",
             "PREDICTION A (effect_type): the icon lands in a DIFFERENT "
             "place or draws a different border from the first one. "
             "PREDICTION B (attribute_level): it looks identical and only "
             "the numbers in the tooltip change."),
        Step(7.0, 0x0044, [agent_id, 2], "68: remove it", "the icon goes."),
        Step(4.0, 0x0042, [agent_id, skill, 12, 3, _f32(30.0)],
             "66: field3 = 12 (a plausible attribute rank, not a "
             "Headquarter type code)",
             "if 12 renders as happily as 0 and 14 did, the field is not a "
             "four-value enum and Headquarter's effect_type reading is in "
             "trouble."),
        Step(7.0, 0x0044, [agent_id, 3], "68: remove it", "clean up."),
    ]


def _buff_side_steps(agent_id):
    """Do 63 and 65 file the same buff under two different agents?

    The client keeps TWO lists per agent -- a source list at BuffState+0x04
    and a target list at +0x14 -- and 63/64 touch the first while 65/66/67/68
    touch the second. A maintained enchantment should therefore need BOTH 63
    and 65 with the same buffId: one to say 'you are maintaining this' and one
    to say 'this is on them'.
    """
    skill = PROBE_BAR_SKILL
    return [
        Step(2.0, 0x0041, [agent_id, agent_id, skill, 0, 4],
             "65 BuffTargetAdd: source and target both us",
             "the effect area. An icon with NO countdown -- opcode 65 stores "
             "duration 0.0f, so it should sit there indefinitely."),
        Step(8.0, 0x003F, [agent_id, agent_id, skill, 0, 4],
             "63 BuffSourceAdd: the same buffId, the source side",
             "PREDICTION: a SECOND indicator appears, in the maintained-"
             "enchantment upkeep row rather than the effects row. If nothing "
             "changes, the two lists do not both drive UI and section 14's "
             "source/target split matters less than it looks."),
        Step(8.0, 0x0040, [agent_id, 4], "64 BuffSourceRemove",
             "PREDICTION: the upkeep indicator goes and the effect icon "
             "stays -- they are separate records keyed by the same buffId."),
        Step(6.0, 0x0044, [agent_id, 4], "68 BuffTargetRemove",
             "now the effect icon goes too."),
    ]


def _cast_modifier_order_steps(agent_id):
    """Must the cast-time modifier arrive AFTER the cast-start property?

    studies/skillcast section 16.2, and this probe exists because that section
    makes a claim no other reading can check. Three properties -- 5, 51 and 61
    -- write one float at the agent object's +0x124, and the cast-start
    properties 4, 50 and 60 END their case body by ZEROING it:

        0x0081BCE1   fldz
        0x0081BCE3   fstp dword ptr [esi+0x124]

    So a modifier sent before the cast it was meant to modify is wiped by that
    cast. That is the opposite ordering from property 10 before the damage
    property, and from 23-27 before the animation that consumes them -- three
    sticky-parameter mechanisms in one dispatcher, two wanting the parameter
    first and one wanting it second. Getting it backwards would mean every cast
    this server ever speeds up or slows down silently plays at normal speed.

    DEPENDS ON THE `cast_anim` PROBE. Everything here assumes property 60 plays
    the animation, which is section 6's static answer and has never been
    observed. Step 2 is therefore the self-control: if a bare property 60 does
    not visibly cast, steps 3-5 are uninterpretable and the run should stop --
    the same rule `die_0x2d` follows by re-running the damage measurement first.

    UNITS ARE UNKNOWN and this probe does not try to settle them. Nothing in the
    image names +0x124 or says whether it is a multiplier, a scale or an added
    time, so two magnitudes go out on the correct ordering: if 2.0 does nothing
    and 0.25 does, the field is a multiplier being clamped at the top end rather
    than the ordering being wrong.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    skill = bar[4]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(6.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "BASELINE: property 60 alone, no modifier",
             "the character's body. Time the cast animation, roughly -- this is "
             "the length everything below is compared against. IF NOTHING CASTS "
             "AT ALL, stop here: the `cast_anim` probe has not been run and this "
             "one cannot be read."),
        Step(10.0, 0x00A2, [PROP_CAST_TIME, agent_id, _f32(2.0)],
             "modifier FIRST: property 61 = 2.0 (float channel, 0x00A2)",
             "nothing yet -- 61 on its own has no animation to modify. Note "
             "whether anything happens anyway, which would itself be news."),
        Step(2.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "... then property 60",
             "PREDICTION: a cast the SAME length as the baseline, because 60's "
             "own case body zeroed the modifier before the animation started. "
             "If this one is visibly different, the zeroing does not do what "
             "section 16.2 says and that claim needs withdrawing."),
        Step(10.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "modifier SECOND: property 60 first ...",
             "a cast starts. Keep watching -- the next packet lands during it."),
        Step(1.0, 0x00A2, [PROP_CAST_TIME, agent_id, _f32(2.0)],
             "... then property 61 = 2.0, one second into the cast",
             "PREDICTION: THIS is the one that looks different -- the animation "
             "speeding up or slowing down mid-cast. If steps 4 and 6 are "
             "indistinguishable, either the ordering does not matter or +0x124 "
             "is not a cast-time modifier, and this probe cannot separate those "
             "two. Step 7 is the tiebreak on magnitude."),
        Step(10.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "again, with a small modifier: property 60 ...",
             "a cast starts."),
        Step(1.0, 0x00A2, [PROP_CAST_TIME, agent_id, _f32(0.25)],
             "... then property 61 = 0.25",
             "the last step. If 2.0 did nothing and 0.25 does, the field is a "
             "multiplier and 2.0 was out of range rather than out of order. "
             "Nothing follows this -- take your time."),
    ]


def _pool_fraction_steps(agent_id, origin):
    """Is property 34 an ABSOLUTE amount or a FRACTION of the pool?

    THE TWO WITNESSES DISAGREE, and that is why this exists.

    SECTION 1b (OBSERVED 2026-08-06) says absolute: property 34 = -50.0 against a
    100-max agent took the bar from 50 to ~0, and 1b reads that as "it arrived as
    exactly 50". THE DISASSEMBLY (OBSERVED 2026-08-11, section 1d) says the client
    calls it a fraction: arm 2 at 0x0081828D passes our value through with NO fmul
    into 0x009215F0, whose line 84 asserts `fraction <= 1.0f` -- which is how the
    revive crash was found.

    1b'S STEP COULD NOT HAVE REFUTED THE FRACTION READING, and that is the flaw
    rather than a quibble. The bar was ALREADY at 50 when -50.0 landed. Absolute
    predicts 50 - 50 = 0. Fraction predicts 50 - (50 x 100) = 0. Both predict an
    empty bar, and 1b's own next row records that the follow-up did nothing
    because "the bar was already at the floor". A measurement whose two rival
    hypotheses make the same prediction is not evidence for either.

    1b's OTHER rows are unaffected and are the calibration this probe leans on:
    property 16 = -0.5 gave exactly 50 damage on a 100 bar, and property 55 = -1.0
    gave exactly 100. Both are the fraction reading landing on the nose, and both
    were read off a FULL bar, which is what makes them refutable.

    SO: the discriminator is -0.5 on property 34 against a FULL bar, which nobody
    has ever sent. The two readings differ by a factor of 100 there.

        step 2 (control, property 16 = -0.10)  ->  10 off, a known fraction
        step 3 (the question, property 34 = -0.50):
              FRACTION -> ~50 off, the bar drops to about half
              ABSOLUTE -> 0.5 off, the bar does not visibly move
        step 4 (the same again) separates fraction-of-MAX (bar empties) from
              fraction-of-CURRENT (bar halves again)

    PREDICTION, stated before the run: FRACTION. The client's own assert names the
    parameter, and a function that meant "absolute health" has no reason to bound
    its argument at 1.0. If the bar instead does not move, the disassembly is
    right about the arithmetic and wrong about the meaning, section 1d needs its
    headline changed, and `_fraction`'s range check is guarding the wrong thing.

    NOT SENT HERE: a positive value larger than 1.0. That is the CharPool.cpp:84
    crash, it is already OBSERVED, and re-running a known client-killer to watch it
    kill the client again buys nothing.
    """
    return [
        Step(2.0, 0x009F, [42, agent_id, 100],
             "max health -> 100 on the PLAYER (int property 42)",
             "the PLAYER's health orb, bottom centre -- it shows a NUMBER, which is a better readout than any bar. It should be 100. Every reading below "
             "is against this baseline, so if it is not full, stop -- the rest of "
             "the run measures nothing."),
        Step(5.0, 0x00A3, [16, agent_id, agent_id, _f32(-0.10)],
             "CONTROL: property 16 = -0.10, a known fraction",
             "the orb number and the floating number. 1b measured this channel at "
             "exactly fraction x max, so this should read 10 and leave the orb at "
             "90. This is the ruler for step 3 -- without it, 'about half' is an "
             "impression rather than a measurement."),
        Step(6.0, 0x00A3, [34, agent_id, agent_id, _f32(-0.50)],
             "THE QUESTION: property 34 = -0.50",
             "the bar, and ONLY the bar -- 1b established 34 is silent, so expect "
             "no floating number either way. Bar drops to about HALF => FRACTION. "
             "Bar stays at 90% => ABSOLUTE, and 0.5 of 100 was too small to see."),
        Step(6.0, 0x00A3, [34, agent_id, agent_id, _f32(-0.50)],
             "the same value again",
             "the bar. EMPTY means the fraction is of MAXIMUM (another 50 off a "
             "bar holding 40). About HALF OF WHAT WAS LEFT means it is of CURRENT. "
             "Still 90% means step 3 was absolute after all and this is 0.5 more."),
    ]


def _burrow_steps(agent_id, origin):
    """Does an NPC definition survive a removal, and does 0x1000 do anything?

    THE QUESTION THIS EXISTS FOR, and it is the one thing burrowing needs that no
    offline test can reach. ArenaNet sends the NPC definition (0x0056) exactly ONCE
    for 140 re-creates of the same Plague Worm, so their client evidently keeps a
    definition across a removal. Ours has never been asked: `agent_removal`'s step 2
    resends 0x0056 and 0x0057 every single time -- deliberately, because the FIRST
    version of that probe omitted them along with two other things and produced a
    negative that meant nothing. So its success tells us the id is reusable and says
    nothing whatever about the definition.

    That matters because the failure mode is asymmetric. `npc_properties`' own
    docstring: an agent whose definition was never sent takes the client down on
    `index < m_count` in Base\\rtl\\Array.h. If definitions do NOT survive, a burrow
    that stops resending crashes the client on the first re-emergence. So the server
    resends today and this probe is what would let it stop.

    THE CONTROL IS THE DESIGN, same as D1's. Step 3 re-creates at the SAME id with no
    definition; step 4 does it at a FRESH id, also with no definition.

        3 works, 4 works  -> a definition is per-INSTANCE and outlives its agents.
                             Burrowing can stop resending; ArenaNet's 1-for-140 is
                             explained.
        3 fails, 4 works  -> the id is the problem, not the definition, and that
                             contradicts agent_removal's positive result -- look at
                             this file before believing it.
        both fail         -> definitions are bound to the agent that used them. Keep
                             resending, and ArenaNet must be doing something else we
                             have not seen.

    WHAT IS DELIBERATELY NOT HERE. The clean negative control -- create an agent
    referring to a definition that was NEVER sent, and confirm the client asserts --
    is the experiment that would nail this down, and it is exactly the crash the
    docstring above describes. Taking the client down to prove it goes down is not
    worth the run; the asymmetry is recorded instead.

    Steps 1-2 are cheap and ride along: EFFECT_TRANSITION (0x1000) is the bit
    ArenaNet sets on 140 of 140 worm creates and clears 2.00 s later -- and the two
    windows have different n, because a capture starts and ends mid-cycle: emerge
    n=137 in [1.976, 2.021], submerge n=132 in [1.973, 2.037]. What the
    client DOES with it is UNVERIFIED -- we know only its timing. Property 66, which
    also appears in the worm burst, is NOT probed here: `prop66_sweep` already owns
    that question and section 16.4 has already bounded it to one byte at AvChar+0x113.
    """
    ox, oy, plane = origin if origin else (0.0, 0.0, 0)
    same = (ox + PROBE_SPAWN_NEAR, oy)
    fresh = (ox + 2 * PROBE_SPAWN_NEAR, oy)
    model_id = CHAR_CLASS_MONSTER_BASE | ENEMY_DEFINITION
    return [
        Step(3.0, 0x00F1, [ENEMY_AGENT_ID, EFFECT_TRANSITION],
             "set the TRANSITION bit (0x1000) on the hostile",
             "the hostile. Does anything change at all -- an animation, a fade, the "
             "nameplate, whether you can still click it? ArenaNet sets this bit for "
             "exactly 2.00 s as a worm comes up and again for 2.00 s as it goes down. "
             "If nothing visible happens, the bit is bookkeeping and our burrow does "
             "not need it."),
        Step(4.0, 0x00F1, [ENEMY_AGENT_ID, 0],
             "clear it again",
             "whether whatever step 1 did reverses. If step 1 made it untargetable, "
             "this should give it back."),
        Step(3.0, 0x0021, [ENEMY_AGENT_ID],
             "REMOVE the hostile",
             "a clean vanish, as agent_removal already established. TARGET IT FIRST "
             "-- the target frame is where a stale reference shows."),
        # --- step 3: the same id, and NO definition resend ----------------------
        Step(4.0, 0x0020,
             create_agent(ENEMY_AGENT_ID, model_id, AGENT_KIND_NPC,
                          same[0], same[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"RE-CREATE at the SAME id ({ENEMY_AGENT_ID}) with NO 0x0056/0x0057",
             f"{PROBE_SPAWN_NEAR:.0f} units out. Does the body appear, and does it "
             "look RIGHT -- a collector, correctly named -- or is it a default/blank "
             "model? A wrong-looking body is as informative as no body: it would mean "
             "the definition slot survived but its contents did not."),
        # --- step 4: the CONTROL, a fresh id, also with no definition -----------
        Step(6.0, 0x0020,
             create_agent(FRESH_AGENT_ID, model_id, AGENT_KIND_NPC,
                          fresh[0], fresh[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"CONTROL: a FRESH id ({FRESH_AGENT_ID}), still no definition",
             f"{2 * PROBE_SPAWN_NEAR:.0f} units out. If this one appears and step 3 "
             "did not, the id is the problem rather than the definition -- which "
             "would contradict agent_removal and means this file is wrong before the "
             "protocol is."),
    ]


def _prop66_sweep_steps(agent_id):
    """What is property 66? Walk the byte and watch the character.

    Section 16.4 bounded this one without naming it. The chain is short and
    every step of it is MEASURED:

        0x00812EBD  case 66  ->  AvApi 0x007E0550   (assert(agent), AvApi:1474)
        0x007E0550  resolve  ->  0x007F7C40 if the agent has an AvChar,
                                 0x007F7C60 if it does not
        0x007F7C40  av->m108->byte7 = (uint8)value ; av->byte113 = (uint8)value

    Three things follow, and they are what make this probe cheap:

      * THE VALUE IS ONE BYTE. Everything above bit 7 is discarded silently, so
        a server sending a large int loses it without a word.
      * IT IS AN APPEARANCE ATTRIBUTE, NOT AN EVENT. The else-branch writes the
        same byte into a global agent-indexed table for agents that have no
        AgentView object yet, which only makes sense for something applied when
        a body is next built.
      * IT IS PROPERTY 65'S NEIGHBOUR. 65 writes byte +5 of the same record and
        66 writes byte +7. OpenTyria names 65 `PvPTeam`; 66 is past the end of
        its enum and unnamed everywhere.

    WHY 65 IS IN THIS PROBE AT ALL. 65's setter compares the old byte against
    the new one and calls a refresh (0x007F3BC0) when it changed; 66's writes
    unconditionally and calls nothing. So 66's byte may sit in the record doing
    nothing visible until something else rebuilds the character -- and toggling
    65 is the cheapest way we know to force that rebuild. Every value of 66
    below is therefore followed by a 65 toggle.

    WHICH MAKES STEP 1 THE CONTROL, and it is not optional: a 65 toggle may well
    change the character by itself, so what a BARE toggle looks like has to be
    established before any of it can be attributed to 66.

    NOT A FULL SWEEP, deliberately. A byte has 256 values and the `attr_legend`
    lesson says a result read at rest shows only the last state, so this walks
    six spaced values with the observer watching each one land. 255 goes last:
    it is outside any plausible enum, so if the earlier values do nothing and
    255 does something ugly, that is still an answer.
    """
    def toggle(delay):
        return [
            Step(delay, 0x009F, [PROP_APPEARANCE_65, agent_id, 1],
                 "  65 -> 1 (force a refresh)", "watch the character."),
            Step(2.0, 0x009F, [PROP_APPEARANCE_65, agent_id, 0],
                 "  65 -> 0 (and back)", "watch the character."),
        ]

    steps = [
        Step(2.0, 0x009F, [PROP_APPEARANCE_66, agent_id, 0],
             "CONTROL: property 66 = 0, then a bare 65 toggle",
             "the character. 66 = 0 should be whatever it already was."),
    ]
    steps += toggle(3.0)
    steps[-1] = Step(2.0, 0x009F, [PROP_APPEARANCE_65, agent_id, 0],
                     "  65 -> 0 (and back)",
                     "THE CONTROL. Whatever changed across these two packets is "
                     "65's doing, not 66's, and must be discounted below. If the "
                     "character flickered, changed colour, changed nameplate or "
                     "moved at all, write down exactly what.")
    for value in (1, 3, 8, 255):
        steps.append(Step(
            8.0, 0x009F, [PROP_APPEARANCE_66, agent_id, value],
            f"property 66 = {value}",
            f"the character, immediately. Anything at all? "
            f"{'255 is outside any plausible enum, so ugly is informative. ' if value == 255 else ''}"
            f"Then the refresh pair lands."))
        steps += toggle(4.0)
    steps[-1] = Step(2.0, 0x009F, [PROP_APPEARANCE_65, agent_id, 0],
                     "  65 -> 0 (and back)",
                     "the last packet. Read the character at leisure -- nothing "
                     "follows. It is standing at 66 = 255, 65 = 0. If nothing "
                     "differed from the control at ANY value, 66 needs a "
                     "rebuild this probe cannot trigger, and the next move is "
                     "finding what reads AvChar+0x113 rather than sending a "
                     "seventh value.")
    return steps


def _smsgsweep_steps(a, o, dwell=0.4):
    """One step per planned opcode: the loopback half of the never-seen sweep.

    Unlike every other probe here the steps are NOT seconds apart for a human to watch.
    The readout is the capture, not the screen -- `smsgsweep.analyse` attributes each
    c2s reply by IDENTITY, so the dwell only has to exceed the client's reaction time,
    not a person's. 0.4 s over 324 opcodes is about two minutes.

    THE FIRST STEP'S DELAY IS THE EXPERIMENT'S CONTROL, and it is why this probe waits
    ten seconds before doing anything. The pilot of 2026-08-12 fired its first packet
    3.66 s in, 0.2 s after the client's own load traffic stopped arriving
    (INSTANCE_LOAD_REQUEST_SPAWN_POINT, MISSION_MASK_REPORT, TARGET_SELECT) -- and a c2s
    0x0000 landing 5 ms later was scored as a reply to that first send. It may be one.
    That run had no way to tell. So: `settle` seconds of nothing for the load to finish,
    then `control` seconds of nothing that the analyser MEASURES -- whatever the client
    says in that window it said unprompted, and a "reply" on one of those opcodes is
    downgraded to CONTESTED rather than counted as a binding.

    The plan owns both numbers, so the analyser reads back exactly what the run used.
    Passing them separately is how a control window silently moves off the quiet part.

    An empty plan is a REFUSAL rather than an empty run: a probe that sends nothing and
    prints "complete" is exactly the shape of a green run that measured nothing.
    """
    import smsgsweep
    p = smsgsweep.load_plan()
    if not p or not p.get("rows"):
        return [Step(0.0, 0x0000, [], "NO PLAN -- run smsgsweep.py --plan first",
                     "nothing was sent; this run measures nothing", sends=False)]
    codec = _sweep_codec()
    dwell = float(p.get("dwell", dwell))
    quiet = (float(p.get("settle", smsgsweep.SETTLE))
             + float(p.get("control", smsgsweep.CONTROL)))
    steps = []
    for i, row in enumerate(p["rows"], 1):
        opcode = row["opcode"]
        # THE OVERRIDES ARE PER ROW, and reading them off `p` is not a near miss -- it is
        # silent. `plan()` resolves `--set 5=1` and `--set 0x0083:2=1` against EACH opcode
        # (sets_for) and writes the result into THAT ROW.
        #
        # It also wrote a top-level copy for about an hour on 2026-08-12 -- which is the
        # whole story. `p.get("set")` was correct when --set shipped (280a29b, 10:59) and
        # became a no-op when the qualified `0x0083:2=1` form replaced the top-level key
        # with sets_for (fdb63e6, 12:00). This line was not updated, so from then on every
        # --set run put the DEGENERATE payload on the wire while reporting the experiment.
        # Nothing downstream could catch it: the plan file is right, the capture is right,
        # and `record` scores the capture -- so the run reads as a measurement of a payload
        # that was never sent, and five of studies/smsgsweep/FINDINGS.md 5c's experiments
        # were retracted for it. Keys are strings because the plan is JSON.
        try:
            values = smsgsweep.apply_set(smsgsweep.degenerate(codec, opcode,
                                        encstring=p.get("encstring")),
                                        {int(k): v for k, v in
                                         (row.get("set") or {}).items()})
        except ValueError:
            continue                       # recorded in the plan's `refused` already
        steps.append(Step(quiet if i == 1 else dwell, opcode, values,
                          f"[{i}/{len(p['rows'])}] 0x{opcode:04X} "
                          f"({row.get('predicted', '?')})",
                          "any c2s the control window did not also produce is a reply"))
    return steps


def _sweep_codec():
    from codec import Codec
    return Codec()


# ------------------------------------------------------- minimap / compass --
#
# PLAN C4. Every value below is computed from a measurement rather than chosen,
# and the two that could not be computed are REPLAYED VERBATIM from ArenaNet.
#
# KNOTS (0x0091). Two SIGNED int16 packed in one dword, LOW half = x, in
# ABSOLUTE world units divided by 96.0 -- the terrain cell pitch
# (studies/minimap/FINDINGS.md §4.1, closed against the one live 0x002B and
# three rival readings). The compass hit-test bounds a click at exactly 4500.0
# world units, so a knot must sit beside the player to be inside the disc at
# all; map 148's spawn is (9826, 8077), i.e. cell (102, 84).
COMPASS_CELL = 96.0
_SPAWN_CELL = (102, 84)                    # 9826/96, 8077/96, round-away-from-zero


def _knot(cx, cy):
    """Pack one knot the way CompassCanvas does: low half x, high half y."""
    return ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)


# THE FOG INIT PAIR IS ARENANET'S OWN, NOT OURS, AND THAT IS THE POINT.
# The RLE stream is 16-row bands, u16 band length, 0xFF-continuation runs of
# alternating colour (rung S8, re-derived and closed 8/8 on live payloads).
# Building one by hand is the single most likely way for this arm to fail for a
# reason that has nothing to do with the opcodes, so it replays a REAL pair
# instead: capture 20260807T143055, connection :64102, the largest of the eight.
# Its declared byteCount is 38 and its band chain closes at EXACTLY 38 --
# lengths (0, 22, 0, 0, 0, 0, 0, 0) over 128/16 = 8 bands -- which is the same
# arithmetic S8 used and is re-checked in test_probes.py rather than trusted.
# Only the two trailing 0xCCCC padding dwords beyond the declared count are ours
# to ignore; everything inside the count is verbatim ArenaNet.
FOG_INIT_DIMS = (64, 128)                  # continent 1's block grid, 64 % 32 == 0
FOG_INIT_BYTES = 38
FOG_INIT_PAYLOAD = [1441792, 973218303, 956578308, 889600005, 939930889,
                    1006778885, 41474, 0, 0, 3435921408]

# The mark, in CONTINENT-ABSOLUTE blocks (footprint cells >> 5), not map-local.
# Map 148's footprint is (768, 512)-(1184, 1024) cells = blocks x 24..36,
# y 16..31, and the init pair declares a 64x128 grid, so (30, 24) is inside both
# and satisfies ChCliApi:201 `x + markSpanCount <= mapDims.x` (30 + 1 <= 64).
# Field 3 is the HALF-SPAN, so 1 reveals a 3x3 block window.
FOG_MARK = (30, 24, 1)

# ...AND THE ONE ABOVE IS A NO-OP, WHICH IS WHY THERE ARE TWO.
# The 2026-08-15 isolation run diffed init-only against init+mark and got a
# BYTE-IDENTICAL world map -- 0 pixels of 2,013,440. The mark was not refused:
# block (30, 24) was ALREADY SET by the replayed init payload, so writing it
# again changes nothing. Decoding that payload's band 1 (the only non-empty
# band, rows 16..31) settles it -- and the band chain consumes exactly its
# declared 38 bytes, independently reproducing rung S8.
#
# `FOG_MARK_UNSET` is a block the SAME decode says is CLEAR, inside map 148's
# footprint (blocks x 24..36, y 16..31) and beside revealed neighbours so a
# 3x3 reveal lands against known terrain rather than in empty space. 68 of the
# footprint's blocks are clear; this is one of them. Keeping both marks means
# the null and the positive are the same experiment with one coordinate
# changed, which is what makes the null interpretable.
FOG_MARK_UNSET = (26, 22, 1)


def _compass_draw_steps():
    ping = _knot(*_SPAWN_CELL)
    line = [_knot(_SPAWN_CELL[0] + dx, _SPAWN_CELL[1] + dy)
            for dx, dy in ((0, 0), (2, 0), (4, 1), (6, 2), (8, 2))]
    return [
        Step(3.0, 0x0091, [7, 1, [ping]],
             "0x0091 PING: knotCount=1, owner=7 (NON-zero), at the player's cell",
             "a red ping ripple ON THE COMPASS at the player's own position. "
             "knotCount==1 takes the ripple path at 0x008BE6B3 and needs no "
             "0x0092 at all. Owner is 7 rather than 0 on purpose: 0 is the "
             "LOCAL client's own tag, and a zero echo makes the client merge "
             "the broadcast into its own line."),
        Step(6.0, 0x0091, [7, 2, line],
             "0x0091 POLYLINE: knotCount=5, a short stroke beside the player",
             "a red line on the compass. CompassCanvas:1372 needs knotCount >= 2 "
             "to render a polyline, so this is the arm the ping cannot test."),
        Step(6.0, 0x008B, [FOG_INIT_DIMS[0], FOG_INIT_DIMS[1], FOG_INIT_BYTES],
             "0x008B fog INIT DECLARE (64 x 128 blocks, 38 bytes to follow)",
             "NOTHING, and that is the prediction rather than a caution: the "
             "init path posts no frame message at all, so no repaint is due "
             "until the mark lands."),
        Step(1.0, 0x008A, [FOG_INIT_PAYLOAD],
             "0x008A fog INIT PAYLOAD -- ArenaNet's own RLE, replayed verbatim",
             "still nothing visible. This allocates and fills mapBits; until it "
             "has run, 0x008C returns immediately at 0x00811BEE and measures "
             "nothing, which is why smsgsweep's 108 prior sends of 0x008C were "
             "inert."),
        Step(6.0, 0x008C, list(FOG_MARK),
             "0x008C fog MARK at continent block (30, 24), half-span 1",
             "THE REPAINT. This is the only message of the three that posts "
             "0x10000090, whose subscribers are Compass.cpp, GmMapWorld.cpp and "
             "GmMapWindow.cpp. Watch the COMPASS first, then press M: whether "
             "the compass GROUND IMAGE is fog-masked is an open question "
             "(CompassMarker tests the bits, CompassMap's blit does not, "
             "GmMapView does), so a change on the world map with none on the "
             "compass is a REAL result and not a failure."),
    ]


def _fog_pair_steps():
    """The init pair alone -- the NO-MARK half of C4's isolation arm."""
    return [
        Step(3.0, 0x008B, [FOG_INIT_DIMS[0], FOG_INIT_DIMS[1], FOG_INIT_BYTES],
             "0x008B fog INIT DECLARE (no mark will follow)",
             "nothing yet; the init posts no frame message."),
        Step(1.0, 0x008A, [FOG_INIT_PAYLOAD],
             "0x008A fog INIT PAYLOAD -- ArenaNet's own RLE, replayed verbatim",
             "still nothing on the compass. The world map should now OPEN "
             "rather than assert, which is the 6f.2 result; what it must NOT "
             "show is whatever the 0x008C mark adds."),
    ]


def _fog_mark_steps():
    """The same pair PLUS the mark. Identical timing, one extra message."""
    return _fog_pair_steps() + [
        Step(6.0, 0x008C, list(FOG_MARK),
             "0x008C fog MARK at continent block (30, 24), half-span 1",
             "the only difference from compass_fog_nomark. Any world-map pixel "
             "that differs between the two runs is THIS message's doing."),
    ]


# QUEST MARKER AND THE NULL CONTROL (PLAN C4's two untouched arms).
# 0x0049's vec2 is in ABSOLUTE WORLD UNITS -- unlike the compass knots, which
# are world/96 -- so it takes the spawn coordinate verbatim from
# content/maps.toml rather than the cell pair the draw arm uses. Getting that
# wrong would put the marker 96x too far out and read as "nothing drew".
_SPAWN_WORLD = (9826.0, 8077.0)

# ONE code unit, 0x3D64 -- the WIRE WORD, not the archive string id. textrec
# takes the id, which is 0x3D64 - 0x100 = 15460 and resolves to 'Ascalon'; the
# two differ by exactly the coded-string bias, and conflating them is the trap
# studies/quests/FINDINGS.md 3.5 names (15716 resolves to None). Built with
# chr() rather than a literal glyph because that is the sender form 3.5
# documents -- codec.py takes a str, not a list of code units -- and because a
# CJK character in a source literal does not survive every editor intact.
_ENC_ASCALON = chr(0x3D64)


def _compass_quest_steps():
    return [
        Step(3.0, 0x008D, [1, _SPAWN_WORLD, 0, 0, 0, 0, ""],
             "0x008D indexed marker record -- THE NULL CONTROL",
             "NOTHING, predicted before the run. 0x008D writes a 40-byte record "
             "into charContext+0x7EC and posts 0x10000091, so it is not inert "
             "in the client -- the prediction is that it is a static catalogue "
             "entry with no compass glyph of its own. If something DOES draw "
             "here, the null control is the finding and 0x0049's arm below is "
             "confounded by it."),
        Step(8.0, 0x0049, [1, _SPAWN_WORLD, 0, 148, 32,
                           _ENC_ASCALON, _ENC_ASCALON, _ENC_ASCALON, 148],
             "0x0049 QUEST_ADD carrying ArenaNet's own string id 0x3D64 in all "
             "three slots, with plane/flags/home_map moved inside ArenaNet's "
             "observed distribution",
             "THE QUEST LOG READS 'Ascalon' RATHER THAN '?'. 0x3D64 is the word "
             "ArenaNet itself puts in slot 0 of every quest add in the live "
             "corpus (10 of 10); textrec.py resolves it as string id 15460 -> "
             "'Ascalon', a PLAIN record needing no key, while the rival "
             "raw-word reading gives 15716 -> None. One literal therefore tests "
             "the whole chain -- wire code unit, the client's own id->text seam "
             "at 0x007C93F0, rendered glyph. A '?' or a blank means our coded "
             "string is wrong ON THE WIRE even though it re-encodes "
             "byte-identically offline (66 of 66 against ArenaNet's own words), "
             "and every authored string downstream is suspect.\n"
             "SECOND ARM, a free rider on the same run: 6f.5 recorded 'no "
             "compass starburst' as NOT FOUND, but the run that produced it "
             "sent plane=148 and home_map=0 -- values ArenaNet NEVER sends "
             "(observed n=10: plane in {0,26}, home_map in {146,148}, flags=32 "
             "in 8 of 10). Corrected here. If a starburst now draws, 6f.5's "
             "NOT FOUND was a malformed probe rather than an unknown protocol, "
             "and CompassQuestEffect.cpp does not need disassembling."),
    ]


# Q0 from studies/quests/AUTHORING.md, isolated from the compass question.
#
# WHY THIS IS A SEPARATE PROBE RATHER THAN A FLAG ON compass_quest. That probe
# is a MARKER experiment on map 148 and its vec2 is that map's spawn in
# absolute world units -- its own note says MAP 148 ONLY, and changing its
# coordinates would silently invalidate the 6f.5 result it is the control for.
# Map 148 is unrunnable today for a reason that has nothing to do with quests:
# contentids.py refuses the launch because no client archive in the vault binds
# 0x1B97D the way the server's does -- four run dirs hold it only under the
# bit-31 mid-replacement spelling, and the 38833 copy binds it to a rewritten
# file 8 bytes larger than the server's.
#
# So this probe asks the ONE Q0 question that does not need map 148 -- does a
# string id WE choose come back as rendered text -- and it takes its position
# from the LIVE origin, so the payload is coherent on whatever map loads. What
# it deliberately does NOT measure is the compass starburst: that needs 148's
# own coordinates, and answering it here would be answering a question this
# run cannot ask.
_QUEST_NAME_MAP = 449          # Kamadan -- both archives agree on it today


def _quest_name_steps(origin):
    x, y, plane = origin
    return [
        Step(8.0, 0x0049,
             [1, (x, y), int(plane), _QUEST_NAME_MAP, 32,
              _ENC_ASCALON, _ENC_ASCALON, _ENC_ASCALON, _QUEST_NAME_MAP],
             "0x0049 QUEST_ADD carrying string id 0x3D64 in all three string "
             "slots, at the live map's own spawn",
             "THE QUEST TRACKER READS 'Ascalon' RATHER THAN '?'. The run that "
             "produced 6f.5's '?' sent three EMPTY strings deliberately, "
             "because the marker was what was under test. This sends the one "
             "word ArenaNet itself puts in slot 0 of every quest add in the "
             "live corpus (10 of 10). textrec.py resolves 0x3D64 as string id "
             "15460 -> 'Ascalon', a PLAIN record needing no key; the rival "
             "raw-word reading gives 15716 -> None. One literal therefore "
             "tests the whole chain -- our wire code unit, the client's own "
             "id->text seam at 0x007C93F0, a rendered glyph. A '?' or a blank "
             "means our coded-string construction is wrong ON THE WIRE even "
             "though it re-encodes byte-identically offline against "
             "ArenaNet's own words (66 of 66), and every authored string "
             "downstream is suspect."),
    ]


def _quest_description_steps(origin):
    """Q3: add two quests that differ ONLY in how their prose is framed.

    The server answers each GAME_CMSG 0x0012 from its content row, so the two
    0x004C bodies come back with `bare` and `template` framing respectively.
    Adding both in ONE run is what makes them comparable -- two runs would
    differ in session, camera and frame timing as well as in the variable.
    """
    x, y, plane = origin
    return [
        Step(6.0, 0x0049,
             [1463, (x, y), int(plane), _QUEST_NAME_MAP, 32,
              _ENC_ASCALON, _ENC_ASCALON, _ENC_ASCALON, _QUEST_NAME_MAP],
             "0x0049 QUEST_ADD for quest 1463, whose description our server "
             "will answer with TEMPLATE framing",
             "the interesting message is not this one -- it is the 0x0012 the "
             "client sends back within ~30 ms, and the 0x004C the server "
             "answers it with, built from content/quests.toml. OPEN THE QUEST "
             "LOG: the tracker shows the NAME (Q0 already proved that path), "
             "the DESCRIPTION PANE is what this probe is about."),
    ]


# The standing test NPC's agent id (content/world.toml, spawn.test_enemy). It is
# placed 300 units from the player's arrival point on whatever map loads, which
# is why this probe needs no per-map coordinates -- and why it needs --enemy,
# since the harness defaults a probe run to an empty world.
_TEST_NPC_AGENT = 10


def _npc_dialog_steps():
    """Q4: does the 0x0080/0x0081 pair open an NPC dialog window?

    Sends the pair UNSOLICITED rather than waiting for a click. The window is
    what is under test, and making it depend on the harness landing a mouse
    click on a body 300 units away would confound "the messages do not work"
    with "the click missed" -- two failures with one appearance.
    """
    line = questdefs.coded_literal(
        "Well met, traveller. This window is ours.",
        limit=questdefs.DIALOG_UNITS)
    return [
        Step(6.0, 0x0080, [line],
             "0x0080 NPC_DIALOG_TEXT -- one line into the accumulator",
             "NOTHING YET, predicted. 0x0080's body appends into a buffer at "
             "charContext+0x2C and posts no frame message, so a window here "
             "would refute the accumulator reading outright."),
        Step(10.0, 0x0081, [_TEST_NPC_AGENT],
             f"0x0081 NPC_DIALOG_SHOW -- flush, attributed to agent "
             f"{_TEST_NPC_AGENT}",
             "A DIALOG WINDOW OPENS carrying the line above, attributed to the "
             "standing NPC. 0x0081's body builds {1, agent_id, text_ptr} over "
             "that same buffer, posts UI frame 0x100000A6 -- whose ONE "
             "subscriber is at 0x004ECEAF -- and zeroes the count. If nothing "
             "opens, the pair is not the dialog mechanism and 2.5's naming is "
             "wrong; if a window opens but names the wrong speaker, the agent "
             "field is not the speaker."),
    ]


# ArenaNet's OWN dialog line from vault/captures/live/20260807T143055 at
# t=26.816 -- the one whose window the player clicked to produce
# `0x003B quest=80 code=0x03`. Ten code units, transcribed as MEASUREMENT: these
# are string IDS and markers, not text. We cannot read what it says and do not
# need to -- 44 of 44 name slots in the corpus resolve to encrypted archive
# records whose key is NOT FOUND, which is exactly why transcribing this is
# permitted and transcribing their prose is not.
#
# WHY REPLAY IT AT ALL. Q5 needs the client to send 0x003B, and the client only
# sends it when the player clicks an OPTION. Our own Q4 window had text and no
# option, so the markup that makes one is unrecovered. There is no server
# message between INTERACT and that click naming quest 80, so the quest id must
# be IN this string. Replaying it asks the client where: if it comes back as
# `0x003B quest=80`, the id is in these ten words and the client has told us so.
_ARENANET_OFFER_LINE = [0x2AE6, 0xF9CB, 0xE939, 0x5DD2, 0x010A,
                        0x3377, 0xDF18, 0xF3B0, 0x201F, 0x0001]


# The definitions the three live quest givers actually carried, MEASURED off
# WORLD_CREATE_AGENT in vault/captures/live/20260807T143055 by the interval join
# (the create in effect when the agent SPOKE, not its last create):
#
#   agent 99  t=20.140  model 0x200005C8  def 1480  allegiance 'play'  kind 9
#   agent 40  t=17.941  model 0x200005B3  def 1459  allegiance 'nonc'  kind 9
#   agent 36  t=66.737  model 0x200005C1  def 1473  allegiance 'nonc'  kind 9
#
# All three are CHAR_CLASS_MONSTER_BASE | def with AGENT_KIND_NPC -- the same
# class and kind our own spawns already use -- so the definition NUMBER is the
# only thing that differs, which is what makes this a one-variable test. Note
# the allegiances differ between givers ('play' against 'nonc'), so allegiance
# is not what marks a giver.
#
# THE DEFINITION MUST BE PUSHED FIRST, and this comment is here because the
# first version of this probe did not and TOOK THE CLIENT DOWN:
#
#     Assertion: index < m_count
#     P:\Code\Base\rtl\Array.h(587)                          build 38833
#
# which is exactly what `agents.npc_properties` already documents -- "the
# definition index is a raw array index on the client, and creating an agent
# whose definition was never sent takes the client down". The mistake was not
# the missing push, it was a BAD NUMBER: 536872392 was read as 0x20000188 and
# so as definition 392, when it is 0x200005C8 and definition 1480. 392 was
# never defined by anyone, so the create indexed past the end. Slot 1480 is in
# vault/content/npcs.toml already, extracted from this same capture, and
# npcdefs' own docstring cites it.
GIVER_DEFINITION = 1480         # agent 99's, the one whose line we replay
_GIVER_AGENT = 99
# npc_template, NOT WORLD.rows(...) -- the raw row's `enc_name` is a LIST of
# string ids and the codec wants an encoded str. Reaching for the row directly
# gives `string of 26 code units exceeds cap 8`, which is the error
# npc_template's own docstring exists to prevent. Hit it anyway on the first try.
GIVER_NPC = npc_template("def_1480")


def _quest_giver_def_steps(origin):
    ox, oy, plane = origin
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, GIVER_NPC),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION} -- the live "
             f"giver's own type, from vault/content/npcs.toml",
             "nothing yet. This defines a TYPE, not a body -- and it is NOT "
             "optional: without it the create indexes past the end of the "
             "definition array and the client dies on Array.h:587."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, GIVER_NPC),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION} -> model "
             f"{GIVER_NPC['model_id']}",
             "still nothing. One more message before a body can appear."),
        Step(4.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT}) with the LIVE GIVER's "
             f"definition {GIVER_DEFINITION}, 150u from the player",
             "a body appears, carrying the same type ArenaNet's own quest giver "
             "carried. The definition is the ONLY thing changed from the "
             "quest_offer run, which used the hatcher's."),
        Step(8.0, 0x0080, [questdefs.enc_string(_ARENANET_OFFER_LINE)],
             "0x0080 carrying the same captured greeting as quest_offer",
             "nothing yet -- 0x0080 accumulates."),
        Step(12.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "THE WHOLE QUESTION: does a CLICKABLE OPTION appear now that the "
             "speaker carries a real giver's definition? quest_offer sent this "
             "identical line at a hatcher (definition 3) and got text with no "
             "option and no 0x003B. If an option renders here, the client reads "
             "what a dialog offers from the AGENT, and definition 1480 is enough "
             "to arm it. If it still does not, the definition is not the "
             "discriminator either and the remaining candidates are a message "
             "earlier in the session, or the 43-unit OFFER line rather than "
             "this greeting."),
    ]


# GENERIC_VALUE 0x009F is [property_id, agent_id, value]. Property 11 is the
# QUEST MARKER, MEASURED across both keyed sessions -- it lands on 5 of 68
# created agents in :60935 and 9 of 88 in :62994, covers every dialog speaker in
# both, and takes only two values. The trace that fixes their meaning:
#
#   17.941  PROP11 agent 40 = 5                       map load, no interaction yet
#   28.179  QUEST_ADD 80        + PROP11 agent 40 = 4  accepted; 40 becomes turn-in
#   46.797  QUEST_REMOVE 80     + PROP11 agent 40 = 5  turned in at 40; back to 5
#   66.737  PROP11 agent 36 = 4                        quest 218 held, turned in at 36
#
# So 5 = "has a quest to OFFER" and 4 = "turn one in HERE" -- the green '!' and
# green '?' every Guild Wars player knows. Agent 99 holds 5 throughout, being an
# offerer the whole time. RECONSTRUCTION for the two English words; OBSERVED for
# the transitions, which flip with the quest lifecycle 2 of 2 in each direction.
GENERIC_VALUE = 0x009F
PROP_QUEST_MARKER = 11
QUEST_MARKER_OFFER = 5
QUEST_MARKER_TURN_IN = 4


def _quest_giver_mark_steps(origin):
    ox, oy, plane = origin
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, GIVER_NPC),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}",
             "nothing yet -- and mandatory before the create, or Array.h:587."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, GIVER_NPC),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}",
             "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT}), the giver's own definition",
             "a body with the guard's nameplate, as quest_giver_def already "
             "showed. No marker over its head yet."),
        Step(2.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             f"GENERIC_VALUE property {PROP_QUEST_MARKER} = "
             f"{QUEST_MARKER_OFFER} on agent {_GIVER_AGENT} -- THE MARKER",
             "A GREEN '!' OVER THE NPC'S HEAD. This is the message ArenaNet "
             "sends at map load for every quest giver, and the one this arc "
             "missed twice by searching only between INTERACT and the click. "
             "If the exclamation appears, property 11 is named."),
        Step(4.0, 0x0080, [questdefs.enc_string(_ARENANET_OFFER_LINE)],
             "0x0080, the same captured greeting as the two runs before",
             "nothing yet -- 0x0080 accumulates."),
        Step(8.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "THE QUESTION: is the last line CLICKABLE NOW? Two runs sent this "
             "identical greeting -- one at a hatcher, one at this very "
             "definition -- and both rendered plain text with no option and no "
             "0x003B. The marker is the only thing added. If an option renders, "
             "the client arms a dialog's quest options from property 11 and "
             "candidate 2 is confirmed. If it still does not, the marker is "
             "only the overhead glyph and the option needs the quest id from "
             "somewhere this arc has still not found."),
    ]


# GAME_SMSG 0x007E IS THE DIALOG OPTION. [u8 kind, string16(128) label,
# u32 tag, u32 0xFFFFFFFF], from the client's own RECV descriptor and
# schema/messages.json, which agree.
#
# The tag is the DWORD THE CLIENT WILL SEND BACK in GAME_CMSG 0x003B if the
# player clicks that line -- the same 0x800000 | (quest_id << 8) | code the
# accept arm already decodes. MEASURED, and the check could have failed:
# **22 of 22 clicks across both keyed sessions were announced by a prior 0x007E
# on the same connection, with zero counterexamples.** t=26.816 announces
# 0x805003 and the player sends exactly that at t=27.679; t=28.479 announces
# 0x85B603 and the player sends it at t=28.780.
#
# This is what two earlier runs were missing, and it was never in the dialog
# string, the agent's definition or the quest marker. It arrives beside the
# 0x0080/0x0081 pair and nothing had looked at it.
#
# field1 takes 15,16,17,18,21,22,23 in the corpus -- an option KIND or icon,
# unnamed. 18 is what the quest offers used. field4 is 0xFFFFFFFF in 37 of 37.
DIALOG_OPTION = 0x007E
OPTION_KIND_QUEST = 18
OPTION_NO_ICON = 0xFFFFFFFF


def _quest_option_steps(origin):
    ox, oy, plane = origin
    row = questdefs.load()[1463]
    tag = questdefs.encode_service_select(1463, questdefs.SERVICE_ACCEPT)
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, GIVER_NPC),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, GIVER_NPC),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT})", "a body with a nameplate."),
        Step(2.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             f"GENERIC_VALUE property {PROP_QUEST_MARKER} = "
             f"{QUEST_MARKER_OFFER} -- the green '!'",
             "the exclamation mark, already confirmed by quest_giver_mark."),
        Step(3.0, 0x0080,
             [questdefs.coded_literal(row["giver_dialogue"],
                                      row.get("wire_framing", "template"),
                                      limit=questdefs.DIALOG_UNITS)],
             "0x0080 carrying OUR OWN giver line from content/quests.toml",
             "nothing yet -- 0x0080 accumulates. Note this is our prose, not "
             "ArenaNet's replayed greeting: the two earlier runs borrowed their "
             "line because ours had never been tested in a dialog."),
        # ORDER MATTERS AND THE FIRST ATTEMPT HAD IT BACKWARDS. ArenaNet's own
        # t=26.816 burst is 0x0080, then 0x0081, THEN the two 0x007E options,
        # then the marker. Sending the option before the flush put it into a
        # text buffer that 0x0081 then zeroed, and the window opened with our
        # prose and no clickable line -- which looked exactly like "0x007E does
        # not work" and was really "0x0081 opens the window; options are
        # appended to an open one".
        Step(6.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "the window opens with OUR prose. The option arrives next."),
        Step(1.0, DIALOG_OPTION,
             [OPTION_KIND_QUEST,
              questdefs.coded_literal("Accept: A First Errand",
                                      "template", limit=128),
              tag, OPTION_NO_ICON],
             f"0x007E DIALOG OPTION -- our label, tag 0x{tag:06X} "
             f"(quest 1463, code 0x{questdefs.SERVICE_ACCEPT:02X} ACCEPT)",
             "THE WHOLE LOOP: a CLICKABLE LINE appended to the open window. "
             f"Clicking it must send `c2s 0x003B 0x{tag:06X}`, which our accept "
             "arm decodes to quest 1463 code 1 and answers with 0x0049 built "
             "from the content row -- so the quest appears in the log named "
             "'Ascalon'. Red at any link: no option drawn, no 0x003B, a "
             "different dword, or a 0x0049 that draws no log entry."),
    ]


def _quest_offer_steps():
    return [
        Step(6.0, 0x0080, [questdefs.enc_string(_ARENANET_OFFER_LINE)],
             "0x0080 carrying ArenaNet's own captured offer line, verbatim",
             "nothing yet -- 0x0080 accumulates."),
        Step(10.0, 0x0081, [_TEST_NPC_AGENT],
             f"0x0081 flush at agent {_TEST_NPC_AGENT}",
             "A WINDOW WITH A CLICKABLE OPTION, unlike Q4's, which had text "
             "and no option. THE MEASUREMENT IS WHAT THE CLICK SENDS: if "
             "`c2s 0x003B quest=80` appears in the log, the quest id lives in "
             "those ten words and the client has just told us where. Our server "
             "will then answer 'quest 80 NOT IN content/quests.toml', which is "
             "the correct refusal and not a failure of this probe."),
    ]


PROBES = {
    "quest_option": lambda a, o: Probe(
        question="Can a player accept OUR quest, from OUR dialog, by clicking "
                 "an option we sent -- the whole Q5 loop end to end?",
        predicts="A WINDOW WITH OUR TEXT AND A CLICKABLE LINE, and clicking it "
                 "sends `c2s 0x003B 0x85B701` (quest 1463, code 1), which the "
                 "accept arm answers with 0x0049 from content/quests.toml so "
                 "the quest appears in the log. 0x007E is the option message "
                 "and the confidence is high for one reason: 22 of 22 clicks "
                 "in both keyed sessions were announced by a prior 0x007E "
                 "carrying the exact dword, zero counterexamples. Four things "
                 "can still go red independently -- no option drawn, no 0x003B, "
                 "a dword we did not predict, or a 0x0049 that draws no log "
                 "entry -- and each names a different broken link.",
        steps=_quest_option_steps(o),
        note="RUN ON --map 449. Click the option line in the window, around "
             "(0.491, 0.541) at 1936x1040. This is the first probe in the arc "
             "whose dialog text is OURS rather than ArenaNet's replayed line.",
    ),
    "quest_giver_mark": lambda a, o: Probe(
        question="Does GENERIC_VALUE property 11 -- the quest marker -- arm the "
                 "clickable option that two earlier runs could not produce?",
        predicts="A GREEN '!' OVER THE NPC, and the greeting's last line "
                 "becomes CLICKABLE, sending 0x003B. Property 11 was found by "
                 "widening the corpus scan from the INTERACT-to-click window to "
                 "the whole session, which is where it was hiding: ArenaNet "
                 "writes it AT MAP LOAD, 4 of 4 speakers covered, on 5 of 68 "
                 "created agents, with exactly two values whose transitions "
                 "track the quest lifecycle (5 -> 4 on accept, 4 -> 5 on turn "
                 "in, 2 of 2 each way). The marker alone may still not carry "
                 "WHICH quest, in which case the '!' appears and no option "
                 "does -- and that separates the glyph from the option "
                 "cleanly, which no run so far has done.",
        steps=_quest_giver_mark_steps(o),
        note="RUN ON --map 449. One variable against quest_giver_def: the "
             "0x009F property-11 write. Click the window's last line around "
             "(0.491, 0.541) at 1936x1040. Watch the NPC's HEAD as well as the "
             "window -- the glyph and the option are two separate outcomes and "
             "this run can produce either without the other.",
    ),
    "quest_giver_def": lambda a, o: Probe(
        question="Does the clickable quest option come from the AGENT rather "
                 "than the dialog string -- specifically, from its definition?",
        predicts="A CLICKABLE OPTION APPEARS, where quest_offer's identical "
                 "line at a hatcher produced text and none. quest_offer "
                 "refuted 'the option is in the string' by replaying "
                 "ArenaNet's own ten words verbatim and getting no option and "
                 "no 0x003B; the surviving difference is the speaker. Theirs "
                 "was definition 392 and ours was 3. A SECOND prediction, "
                 "cheaper and independent: the body renders at all WITHOUT a "
                 "0x0056/0x0057 pair, because ArenaNet never defines 392 in the "
                 "capture -- if it does render, these types live in the "
                 "client's own data, which is a fact worth having whatever the "
                 "option does.",
        steps=_quest_giver_def_steps(o),
        note="RUN ON --map 449 and CLICK THE LINE the window's text ends with, "
             "around (0.491, 0.541) at 1936x1040 -- that is where quest_offer's "
             "greeting put it. One variable against quest_offer: the definition. "
             "Everything else, including the replayed line, is identical.",
    ),
    "quest_offer": lambda a, o: Probe(
        question="Where does the clickable quest option come from -- and is the "
                 "quest id inside the dialog string itself?",
        predicts="A CLICKABLE OPTION RENDERS, and clicking it sends "
                 "`0x003B quest=80 code=0x03`. The corpus shows no server "
                 "message between INTERACT and that click naming quest 80, and "
                 "the two captured offer lines differ ONLY in one varint group "
                 "(3377 DF18 F3B0 201F against 3375 FE11 D56F 2195) while "
                 "sharing the prefix 2AE6 F9CB E939 5DD2 010A -- so that group "
                 "is where the quest lives. If NO option renders, the option is "
                 "not carried by the string and something else in the corpus "
                 "arms it. If an option renders but the click reports a "
                 "DIFFERENT quest id, the mapping is client-side and the string "
                 "is only a label.",
        steps=_quest_offer_steps(),
        note="RUN WITH --enemy --practice-target --map 449, and CLICK THE "
             "OPTION -- an --actions `click:` step lands during the hold, since "
             "the action script runs on the client's clock rather than after "
             "the probe. The line is ArenaNet's own bytes replayed verbatim: "
             "string ids and markers, never text, and we could not read the "
             "text if we wanted to.",
    ),
    "npc_dialog": lambda a, o: Probe(
        question="Is GAME_SMSG 0x0080 + 0x0081 the NPC dialog window -- the "
                 "reply to INTERACT that test_dispatch called this server's "
                 "missing gate?",
        predicts="THE PAIR OPENS A DIALOG WINDOW, and the order matters: the "
                 "0x0080 alone shows NOTHING and the 0x0081 is what displays "
                 "it. Named in FINDINGS 2.5 from the two handler bodies plus a "
                 "correlation on ArenaNet's wire (0x0080 precedes 11 of 11 "
                 "quest selects per session against a 0.13% background rate, "
                 "0x0081 names the interacted agent 23 of 23), and the "
                 "clincher: a 0x0080 string at t=27.719 is byte-identical for "
                 "22 code units to the 0x004C description that follows it. But "
                 "NEITHER HAS EVER BEEN SENT TO A CLIENT -- the whole naming is "
                 "read-side, and this is the first time either goes out.",
        steps=_npc_dialog_steps(),
        note="RUN WITH --enemy --practice-target --map 449. The NPC only needs "
             "to EXIST for 0x0081 to name it; nothing here requires the player "
             "to reach or click it. Without --enemy the world is empty, agent "
             "10 does not exist, and a window naming a missing agent is a "
             "different experiment than the one intended.\n"
             "The line is framed, because a bare literal starting below 0x100 "
             "crashes the client on TextApi.cpp:585 -- MEASURED on 2026-08-15, "
             "and questdefs refuses to build one now.",
    ),
    "quest_description": lambda a, o: Probe(
        question="Does OUR OWN PROSE render in a real client's quest log -- and "
                 "does a literal have to carry ArenaNet's framing to do it?",
        predicts="THE DESCRIPTION PANE READS 'Speak to the gate guard, then "
                 "return to me.' -- our sentence, our words, chosen by us.\n"
                 "THE CONTROL HALF OF THIS PROBE HAS ALREADY RUN AND IS NOT "
                 "REPEATED. On 2026-08-15 the same probe sent a second quest "
                 "whose description was the same sentence with NO framing, and "
                 "it did not merely fail to render -- it killed the client on "
                 "its own bound check, `(codedString[0] & ~WORD_BIT_MORE) >= "
                 "WORD_VALUE_BASE`, TextApi.cpp:585, with our sentence sitting "
                 "verbatim as UTF-16 in the crash stack. So the marker/varint "
                 "rule is confirmed by ArenaNet's own assert and the bare arm "
                 "is settled; questdefs now REFUSES to build one. Re-running it "
                 "would buy a second crash and no second finding.\n"
                 "IF THE PANE IS EMPTY, the framing is necessary but not "
                 "sufficient and the next suspect is the 0x0107 marker rather "
                 "than the 0x0BA9 template id. IF THE CLIENT ASSERTS AGAIN, our "
                 "framing constants are wrong and the crash names which.",
        steps=_quest_description_steps(o),
        note="RUN WITH --map 449, and OPEN THE QUEST LOG once both quests are "
             "in. The tracker shows the NAME; the description pane is what this "
             "probe is about, and it is behind the log. Q0 already proved the "
             "name path, so a tracker reading 'Ascalon' twice is the setup "
             "working, not the result.\n"
             "WATCH THE ORDER TRAP: 0x004C sets flag bit 0 "
             "(CHAR_CHALLENGE_FLAG_DESC_FILLED) and 0x0054's body returns "
             "immediately when that bit is clear, so objectives sent before the "
             "description are a SILENT no-op. This probe sends no 0x0054 at all "
             "for exactly that reason -- one variable.",
    ),
    "quest_name": lambda a, o: Probe(
        question="Does a quest name we chose render as text in a real client, "
                 "or is 'commit the id, resolve the string at run time' "
                 "something this project has only ever done in one direction?",
        predicts="THE QUEST TRACKER READS 'Ascalon'. Everything the quests arc "
                 "established about coded strings is DECODE-side: we have "
                 "parsed ArenaNet's and re-encoded them byte-identically, but "
                 "no string we built has ever been sent to a client -- "
                 "compass_quest sent three empty ones on purpose. If this "
                 "renders, the naming half of quest authoring is done and the "
                 "problem reduces to 'which string id'. If it renders '?' or "
                 "blank, an offline round trip agreeing with itself was never "
                 "evidence and the string16 encoding becomes rung 1.",
        steps=_quest_name_steps(o),
        note="RUN WITH --map 449. The map is not incidental: map 148, which "
             "the sibling compass_quest probe uses, cannot load at all right "
             "now because no client archive in the vault binds its file id the "
             "way the server's does (contentids.py refuses the launch, and it "
             "is right to). 449 is one of the eight rows both archives agree "
             "on. The quest tracker is map-independent, so nothing about this "
             "question is weakened by the substitution -- but the COMPASS arm "
             "is not measured here and must not be read out of this run.",
    ),
    "compass_fog_nomark": lambda a, o: Probe(
        question="PLAN C4 isolation, half 1 of 2: what does the fog INIT PAIR "
                 "alone reveal, with no 0x008C mark?",
        predicts="The world map OPENS rather than asserting (6f.2), and shows "
                 "whatever ArenaNet's own replayed payload encodes -- which is "
                 "most of what 6f.2's screenshot showed. This run exists to "
                 "prove that, so that the mark's own contribution can be "
                 "measured as a DIFFERENCE rather than assumed from a single "
                 "picture that contained both.",
        steps=_fog_pair_steps(),
        note="Run this and compass_fog_mark back to back with identical flags, "
             "then diff the two world-map frames. 6f.4 records that C4's first "
             "pass could not separate them because one run sent both.",
    ),
    "compass_fog_mark": lambda a, o: Probe(
        question="PLAN C4 isolation, half 2 of 2: what does the 0x008C MARK add "
                 "on top of the init pair?",
        predicts="A 3x3-block patch revealed at continent block (30, 24) that "
                 "compass_fog_nomark does not have. If the two world maps are "
                 "pixel-identical, the mark did nothing -- and the per-map "
                 "explorable mask from Engine\\Map\\Map.cpp, which nothing has "
                 "read, is the first suspect rather than the opcode.",
        steps=_fog_mark_steps(),
        note="Identical to compass_fog_nomark except for the trailing 0x008C, "
             "so the world-map difference is attributable to one message.",
    ),
    "compass_fog_mark_unset": lambda a, o: Probe(
        question="PLAN C4 isolation, the RETRY: does 0x008C reveal a block the "
                 "init payload left CLEAR?",
        predicts="A 3x3 patch appears on the world map at continent block "
                 "(26, 22) that compass_fog_nomark does not have. The first "
                 "attempt marked (30, 24), which decoding the payload shows was "
                 "ALREADY SET -- so its byte-identical result measured nothing "
                 "about the opcode. If THIS one is also identical, the mark is "
                 "genuinely inert and the per-map explorable mask "
                 "(0x0070A120 -> 0x00721D00, unread) is the first suspect.",
        steps=_fog_pair_steps() + [
            Step(6.0, 0x008C, list(FOG_MARK_UNSET),
                 "0x008C fog MARK at continent block (26, 22) -- a CLEAR block",
                 "the world map, diffed against compass_fog_nomark. This is the "
                 "same experiment as compass_fog_mark with one coordinate "
                 "changed, which is what makes either outcome interpretable."),
        ],
        note="Diff against compass_fog_nomark, not against compass_fog_mark.",
    ),
    "compass_quest": lambda a, o: Probe(
        question="PLAN C4's two untouched arms: does 0x0049 draw a quest marker "
                 "on the compass, and is 0x008D really the null it is predicted "
                 "to be?",
        predicts="0x008D draws NOTHING and 0x0049 draws a GREEN STARBURST at "
                 "the player's own position, plus a quest-log entry. The order "
                 "matters and is deliberate: the control goes FIRST, so that if "
                 "a glyph appears after 0x0049 there is already a clean frame "
                 "proving 0x008D did not put it there.",
        steps=_compass_quest_steps(),
        note="MAP 148 ONLY -- the vec2 is that map's spawn in ABSOLUTE world "
             "units. Note the unit differs from the compass draw arm, whose "
             "knots are world/96; using the cell pair here would place the "
             "marker 96x too close to the origin and look like a null.",
    ),
    "compass_draw": lambda a, o: Probe(
        question="PLAN C4. Does the compass draw/ping pair render from the wire, "
                 "and can the three-message fog sequence unfog a block on our "
                 "own server?",
        predicts="THE PING AND THE POLYLINE RENDER. Both ends of the draw pair "
                 "are named from the client's own asserts and the handler's "
                 "unpack loop is the exact inverse of the sender's pack, so a "
                 "well-formed 0x0091 beside the player should draw. A null "
                 "there would mean the broadcast needs party state we do not "
                 "have. THE FOG SEQUENCE IS THE HARD ARM and its first two "
                 "steps are predicted to show NOTHING -- the init posts no "
                 "frame message -- with the repaint arriving only on the "
                 "0x008C. Two things can defeat it for reasons unrelated to the "
                 "opcodes, both named in advance: 0x008C's bit writes are gated "
                 "by a per-map explorable mask from Engine\\Map\\Map.cpp that "
                 "nothing in this repo has read, and if the compass ground is "
                 "not fog-masked the reveal is visible only on the world map.",
        steps=_compass_draw_steps(),
        note="RUN ON MAP 148 (the default) -- every coordinate here is computed "
             "for it and is wrong anywhere else: the knots are absolute world "
             "units/96 around ITS spawn, and the mark is in continent-1 blocks "
             "inside ITS footprint. The fog init pair is ArenaNet's own bytes "
             "replayed verbatim rather than a payload we built, because a "
             "hand-rolled RLE stream failing would look exactly like the client "
             "refusing the opcode. Give the run --keep-open and enough hold to "
             "see all five steps, and press M after the last one.",
    ),
    "smsgsweep": lambda a, o: Probe(
        question="Of the GAME_SMSG opcodes ArenaNet has never sent us, which ones does "
                 "the client visibly act on -- and which of those answer back?",
        predicts="EVERY planned opcode reaches a handler: all 477 receive-table entries "
                 "carry a non-null dispatch pointer (msghandler.py --classify), so a "
                 "silent row is a fact about the all-zero payload or the readout, NEVER "
                 "about reachability. Most will be silent for exactly that reason -- a "
                 "handler that early-outs on a zero id looks identical to one that does "
                 "nothing. The result worth having is a REPLY: the client sending a c2s "
                 "message names the request a panel makes, which is the binding a live "
                 "session would otherwise have to go and discover. A channel teardown is "
                 "also a result -- but it is NOT a crash until the session report's "
                 "endpoint table says the client stopped: 0x000B tore the game channel "
                 "down in the pilot and the client was alive on a loading screen 42 s "
                 "later, with no assert in Gw.log and no fatal-error dialog.",
        steps=_smsgsweep_steps(a, o),
        note="NEEDS A PLAN: run `smsgsweep.py --plan` first, or this probe sends "
             "nothing and the run measures nothing -- it says so as a step marked "
             "`sends=False`, which carries the warning to the operator without "
             "having to survive the codec. "
             "Loopback only -- both endpoints ours, ours-DH client, cage verified. "
             "Score with `smsgsweep.py --from-report <the run's report.json> --record`. "
             "Attribution is by opcode identity, against this run's OWN control window "
             "-- the quiet seconds before the first send -- and not by timing."),
    "agent_removal": lambda a, o: Probe(
        question="Does GAME_SMSG 0x0021 remove an agent the client is already "
                 "drawing, and is its id then safe to reuse?",
        predicts="The hostile vanishes cleanly on step 1 -- no corpse, no "
                 "nameplate -- because 0x005FD2F0 walks the agent's bound objects "
                 "and clears them rather than just hiding a model. Step 2 then "
                 "shows a fresh healthy hostile at the SAME id. The informative "
                 "failure is step 1 leaving a ghost (nameplate, health bar or a "
                 "target frame that will not clear), which would mean removal is "
                 "necessary but not sufficient and something else must precede "
                 "it. If step 2 asserts or draws nothing, id reuse needs more "
                 "than a removal and our respawn cannot use it.",
        steps=_agent_removal_steps(a, o),
        note="RUN 2026-08-10. POSITIVE, both halves. Step 1: 0x0021 removes an "
             "agent the client is already DRAWING -- clean vanish, no corpse, no "
             "nameplate, no stale target frame, exactly what reading the handler "
             "at 0x005FD2F0 predicted. Steps 2-3: the removed id was RE-CREATED "
             "successfully and the fresh-id control also appeared, so a removed "
             "id is NOT poisoned and reuse needs nothing beyond the ordinary "
             "spawn burst. This is what unblocks remove-then-recreate for "
             "respawn, which is what ArenaNet does (301 of 301 live re-creations "
             "preceded by a removal of that id). AN EARLIER RUN OF THIS PROBE "
             "REPORTED THE OPPOSITE and was wrong: step 2 sent a bare 0x0020 with "
             "no NPC definition, a message payload where a model_id belongs, and "
             "the wrong plane, so it measured a bug in this file. The control at "
             "a fresh id is what separated the two, and is why it is there. "
             "Implements studies/divergence/FINDINGS.md D1, the highest-"
             "ranked protocol gap from the first live capture: ArenaNet sent "
             "0x0021 416 times, we have sent it 0 times in 271,449 messages, and "
             "301 of 301 live id re-creations were preceded by a removal of that "
             "id. TARGET THE HOSTILE BEFORE RUNNING and watch the target frame -- "
             "that is the case most likely to expose a stale reference, and it is "
             "not visible if you only watch the model. This probe deliberately "
             "does NOT touch the death/revive path: that behaviour is measured "
             "and works, and swapping it for remove-then-recreate is a separate "
             "decision that needs this probe's answer first.",
    ),
    "cast_modifier_order": lambda a, o: Probe(
        question="Must the cast-time modifier (property 61) be sent AFTER the "
                 "cast-start property (60) rather than before it?",
        predicts="61-then-60 casts at the SAME speed as a bare 60, because 60's "
                 "own case body zeroes the modifier field before the animation "
                 "starts. 60-then-61 casts visibly differently. If the two "
                 "orderings are indistinguishable, either the ordering does not "
                 "matter or +0x124 is not the cast-time modifier -- this probe "
                 "cannot separate those, and says so.",
        steps=_cast_modifier_order_steps(a),
        note="Tests a claim studies/skillcast section 16.2 makes and nothing "
             "else can check: 4, 50 and 60 end with `fldz; fstp [esi+0x124]` at "
             "0x0081BCE1, zeroing the float that 5, 51 and 61 write. UNRUN. "
             "Depends on the `cast_anim` probe -- step 2 is the self-control and "
             "the run should stop there if a bare property 60 does not cast. "
             "Note 61 goes out on 0x00A2, the FLOAT channel: on 0x009F it would "
             "be discarded in silence and look like a negative result.",
    ),
    "pool_fraction": lambda a, o: Probe(
        question="Is agent property 34 an ABSOLUTE amount or a FRACTION of the "
                 "pool? Section 1b says absolute; the client's own assert calls it "
                 "a fraction.",
        predicts="FRACTION -- the bar drops to about half on step 3. The client "
                 "asserts `fraction <= 1.0f` on this exact argument "
                 "(CharPool.cpp:84, reached from arm 2 at 0x0081828D), and a "
                 "function meaning 'absolute health' has no reason to bound its "
                 "input at 1.0. The rival prediction is a bar that does not "
                 "visibly move, which would mean section 1d is right about the "
                 "arithmetic and wrong about the meaning. Step 2 is a known-good "
                 "fraction on property 16 and exists so that 'about half' is read "
                 "against a measured 10% rather than guessed.",
        steps=_pool_fraction_steps(a, o),
        note="RUN 2026-08-11, AND BOTH EARLIER READINGS ARE WRONG -- including the prediction above, which is left standing because it was. Observed on the player orb: 100 -> (property 16 = -0.10) -> 90 -> (property 34 = -0.50) -> 1 -> (again) -> 1. A DELTA of 0.5 x 100 from 90 predicts 40; the prediction above said 'about half'; the floor is what happened. "
             "PROPERTY 34 IS A SETTER: it sets the pool to fraction x maximum. -0.5 sets it to -50, which clamps to the floor of 1, and does so again on a second send because a setter is idempotent. That is also why revive's 1.0 refilled a bar sitting at zero all the way to full, and why the client asserts fraction <= 1.0f -- a setter cannot exceed the maximum. studies/agentprops/FINDINGS.md 1e. "
             "Section 1b's own step for this question could not have refuted the "
             "fraction reading: it sent -50.0 at a bar ALREADY down to 50, where "
             "absolute predicts 0 and fraction predicts 0. This sends -0.5 at a "
             "FULL bar, where the two readings differ by a factor of 100. Watch "
             "the HOSTILE's floating bar, not the player's orb. Nothing here can "
             "crash the client: every value is inside the asserted range, and the "
             "one known killer (a positive value above 1.0) is deliberately "
             "absent.",
    ),
    "burrow": lambda a, o: Probe(
        question="Does an NPC definition survive WORLD_REMOVE_AGENT, and does the "
                 "0x1000 effect bit do anything the player can see?",
        predicts="Steps 3 AND 4 both draw a correct-looking collector, because "
                 "ArenaNet sends one 0x0056 for 140 re-creates of the same worm and "
                 "the only reading of that is a definition table which outlives the "
                 "agents using it. If BOTH fail, definitions are bound to their agent "
                 "and our burrow must keep resending -- which is what it does today, "
                 "so a negative costs nothing but a resend. Steps 1-2: no prediction "
                 "worth the name. The bit's TIMING is measured (2.00 s each way, "
                 "n=132) and its EFFECT is unverified; the honest expectation is that "
                 "nothing visible happens, because a client that hid an agent on this "
                 "bit would not also need the removal ArenaNet sends 2.00 s later.",
        steps=_burrow_steps(a, o),
        note="RUN 2026-08-11, and BOTH re-creates drew a correct collector -- same id "
             "and fresh id, neither given a 0x0056/0x0057. A definition is per-INSTANCE; "
             "burrow_tick now passes send_definition=False (studies/enemy/PLAN.md 10.8, "
             "capture authsrv-20260811T135809). THE STEPS-1-2 PREDICTION WAS REFUTED and "
             "that is the better half: 0x1000 is an ANIMATION, not bookkeeping. Set it "
             "and the agent falls prone, clear it and it gets up; it stays rendered and "
             "keeps its nameplate throughout. The reasoning behind 'nothing visible "
             "happens' -- that a client hiding an agent on this bit would not need the "
             "removal 2.00 s later -- was sound, and the answer is that the bit animates "
             "while the REMOVAL hides. Re-running is still useful; the note below stands. "
             "Do NOT add the clean negative control (an agent citing a "
             "definition never sent) -- that is the `index < m_count` client assert "
             "npc_properties warns about, and crashing the client to confirm it "
             "crashes is not worth a run. TARGET THE HOSTILE BEFORE STEP 1 and keep "
             "watching the target frame through step 3. Grounded on "
             "vault/captures/live/20260807T143055 conn :64103, where 140 worm "
             "re-creations are one five-message burst with no exceptions "
             "(toolkit/authsrv/test_burrow.py re-measures it every run).",
    ),
    "prop66_sweep": lambda a, o: Probe(
        question="What is agent property 66, the one id past the end of "
                 "OpenTyria's enum that no source anywhere names?",
        predicts="Uncertain by construction, which is the point -- static "
                 "analysis bounded this one and could not name it. Something "
                 "visible should change for at least one value, because the "
                 "byte is stored per agent even for agents with no AgentView "
                 "object yet, which is what an appearance attribute looks like. "
                 "If nothing changes at any value, 66 needs a character rebuild "
                 "the 65 toggle does not trigger.",
        steps=_prop66_sweep_steps(a),
        note="MEASURED (section 16.4): 66 writes ONE BYTE to AvChar+0x113 and "
             "to +7 of the record at AvChar+0x108, where property 65 -- "
             "OpenTyria's PvPTeam -- writes +5. Anything above bit 7 of the "
             "value is discarded silently. UNRUN. The 65 toggles are there "
             "because 66's setter calls no refresh and 65's does; step 1 "
             "establishes what a bare toggle does so it can be discounted.",
    ),
    "buff_type_field": lambda a, o: Probe(
        question="Is opcode 66's third field Headquarter's `effect_type` or "
                 "GWCA's `attribute_level`?",
        predicts="If effect_type, 0 and 14 render as visibly different KINDS "
                 "of effect and an out-of-enum 12 misbehaves. If "
                 "attribute_level, all three render identically and only the "
                 "tooltip numbers move. The binary cannot separate these: it "
                 "stores the field at buff record +0x04 and never reads it in "
                 "ChCliBuff.",
        steps=_buff_type_steps(a),
        note="The one CONTESTED field name in the effect family. Keep buffId "
             "small -- GmEffect:3030 bounds it against a UI frame-code range.",
    ),
    "buff_side": lambda a, o: Probe(
        question="Do opcodes 63 and 65 file the same buff under two different "
                 "agents, in two different lists?",
        predicts="65 alone gives one effect icon with no countdown. Adding 63 "
                 "with the same buffId gives a SECOND, separate indicator "
                 "(the upkeep row). Removing one leaves the other.",
        steps=_buff_side_steps(a),
        note="SOURCED: BuffState keeps a source list at +0x04 and a target "
             "list at +0x14, and the client's own log strings are "
             "BuffSourceAdd/BuffSourceRemove for 63/64 and "
             "BuffTargetAdd/ExtendTimed/Remove for 65/66/67/68.",
    ),
    "use_skill_capture": lambda a, o: Probe(
        question="What does the client SEND when a skill key is pressed, and "
                 "does the message number depend on the skill's TYPE?",
        predicts="Two different opcodes from the same eight keys. Keys 1-4 "
                 "(To the Limit!, Battle Rage, Defy Pain, Rush -- types 15, 3, "
                 "16, 3) send GAME_CMSG 70 / 0x0046. Keys 5-8 (Hamstring, Wild "
                 "Blow, Power Attack, Desperation Blow -- all type 14, attack "
                 "skills) send GAME_CMSG 39 / 0x0027 instead. Both are 15 "
                 "bytes. In 70 the fields are {skill id, skill copy, target "
                 "agent id, u8}; in 39 the same four values go out in the same "
                 "order against a differently typed table. Skill copy will be "
                 "0 unless the skillbar was sent with a non-zero second array.",
        steps=[],
        note="No packets from us -- press the keys and read the capture. It "
             "settles USE_SKILL's field NAMES (unnamed in every source; "
             "Headquarter guesses field 2 is `flags`, apoguita guesses `type`, "
             "and the client's own builder says it is the skill copy) and the "
             "existence of a second, unnamed cast message at the same time. "
             "The type split is SOURCED from ChCliApiUseSkill at VA 0x00816660 "
             "branching on skill record +0x0C; the type-14 = attack-skill "
             "reading is from this build's own skill table. If BOTH halves of "
             "the bar send 70, that branch is not on skill type and the "
             "reading is wrong.",
    ),
    "skill_copy": lambda a, o: Probe(
        question="Is the lifecycle messages' third dword the bar slot's "
                 "`skillCopy`, delivered by SKILLBAR_UPDATE's second array?",
        predicts="With copies set to 7, a recharge addressed to copy 0 does "
                 "NOTHING and the same recharge addressed to copy 7 works. If "
                 "both work, the client is not matching on field 3; if neither "
                 "works, the second array of 218 is not what fills the slot.",
        steps=_skill_copy_steps(a),
        note="The decisive experiment for the field GWCA calls skill_instance "
             "and every other lineage records as NOT FOUND. Cheapest and most "
             "informative probe in this group; run it first. Note the failure "
             "mode is SILENCE, which is why the run alternates right and wrong "
             "copies rather than testing one.",
    ),
    "skill_disable": lambda a, o: Probe(
        question="Is unnamed opcode 231 the 'skill disabled' message?",
        predicts="231 freezes an in-progress cooldown permanently dark, and a "
                 "subsequent 230 clears it instantly. If 231 instead behaves "
                 "like 230, the -1 we read is being treated as ready.",
        steps=_skill_disable_steps(a),
        note="231 writes recharge = 0xFFFFFFFF where 229 explicitly SKIPS both "
             "0 and -1 when computing a timestamp; those are two reserved "
             "values and this asks what the second one looks like.",
    ),
    "skill_partial": lambda a, o: Probe(
        question="Does unnamed opcode 232 carry a fractional recharge, and is "
                 "its fourth field the total the UI draws the sweep against?",
        predicts="Field 5 is seconds as an IEEE float: 10.0f counts ten "
                 "seconds and 2.5f counts two and a half. Field 4 = 40 with "
                 "field 5 = 10.0f starts the sweep about a quarter dark.",
        steps=_skill_partial_steps(a),
        note="The remaining/total reading is INFERRED, not sourced -- the "
             "binary shows only that field 5 sets the clock and field 4 is "
             "reported to the UI beside it. The sweep angle is the only thing "
             "that can separate the two readings.",
    ),
    "cast_anim": lambda a, o: Probe(
        question="What triggers the cast animation -- opcode 228, or agent "
                 "property 60?",
        predicts="228 does nothing visible at all when addressed to the local "
                 "player. Property 60 with a skill id plays the animation. If "
                 "228 animates anything, the read of its handler is wrong.",
        steps=_cast_anim_steps(a),
        note="Open question in studies/skills section 8, and the static answer "
             "is strong enough to be worth trying to break. Watch Gw.log as "
             "well as the screen: step 4 should produce the client's own "
             "'Pending skill %u copy %d not found'.",
    ),
    "unlock_211": lambda a, o: Probe(
        question="What is opcode 211, the third unlock-list-shaped message?",
        predicts="Nothing observable. It writes a bitmap nothing in the image "
                 "reads and broadcasts no UI event, unlike 219.",
        steps=_unlock_211_steps(a),
        note="A NULL result is the expected result and is worth having: it "
             "would let the server stop worrying about a message it has never "
             "sent. Any visible effect refutes the read and is more "
             "interesting still.",
    ),
    "health_max": lambda a, o: Probe(
        question="Does int property 42 refill only when the MAXIMUM actually "
                 "changes -- or does it not carry the maximum at all?",
        predicts="THE FRACTION SURVIVES: HUD reads 50 with the bar still at a "
                 "quarter. Reasoning: the damage handler clamps against "
                 "health_max and the client stores health as a fraction "
                 "(0.25 * 200 = 50), so moving the maximum should rescale the "
                 "displayed number without touching the fraction. That makes "
                 "upstream's health_max half right and its `health = 1.f` half "
                 "wrong. A refill to 200 refutes this and vindicates upstream "
                 "on a change of value; a flat 25 says property 42 is not the "
                 "maximum either.",
        steps=_health_max_steps(a),
        note="ANSWERED 2026-08-13, and it is NONE of the three outcomes above -- "
             "the HUD read 125. `health += (new_max - old_max)`: 25 + (200-100) "
             "= 125, bar 62.5% predicted against 61.7% and 62.3% measured on two "
             "independent bars, and putting the maximum back returns exactly 25. "
             "A maximum-health increase GRANTS that health, as a rune does. So "
             "upstream's `health = 1.f` refill is REFUTED for retail, and so is "
             "this probe's own fraction prediction. Kept runnable: it is the "
             "calibration for maximum health the way `damage` is for current. "
             "Press P first; the HUD NUMBER is the measurement, not the bar.",
    ),
    "party_health": lambda a, o: Probe(
        question="Is the party row's red bar this player's HEALTH, or a constant "
                 "the row draws whatever we send?",
        predicts="It SHRINKS. WIKI (GWW, 'User interface' section Party window) "
                 "says the party window's red bars are party members' health, and "
                 "property 16 is a fraction of maximum -- so -0.5 then -0.25 must "
                 "leave the bar at about half then about a quarter of its width, "
                 "horizontally, with the name in place and the colour unchanged. "
                 "The party region must move well above the 0.007% within-arm "
                 "floor measured in RESKIN.md 18.9. A bar that stays FULL is the "
                 "more interesting result: the row would be drawing a constant "
                 "rather than this member's health.",
        steps=_party_health_steps(a),
        note="ANSWERED 2026-08-13 -- IT IS HEALTH, and to within half a percent: "
             "the bar measured 100.0%, then 49.7%, then 24.0% of its own detected "
             "extent against a prediction of 100/50/25. Kept because the third "
             "step is still UNRUN: the original recovery sent damage +0.75 and "
             "killed the client on `damage.amount <= 0` (AvChar.cpp:5893), which "
             "is a bound worth knowing and was a design error -- property 16 is "
             "DAMAGE, not a signed health delta. Press P first; with no roster on "
             "screen this measures nothing. Watch the PARTY ROW, not the HUD bar "
             "at the bottom -- both are red, both track health, and the HUD one "
             "is not what is being asked about.",
    ),
    "player_flags": lambda a, o: Probe(
        question="What does GAME_SMSG 0x003C do? It is in 12 of 12 live ArenaNet "
                 "connections, 423 sends, and this server has never sent it once "
                 "in 190 played captures.",
        predicts="NOTHING VISIBLE in a one-player instance, and that is the "
                 "honest prediction rather than a hedge: the handler's two "
                 "writes land in the same ctx+0x80C player array 0x00B0/0x00B1 "
                 "already populate, and the party roster ALREADY draws its row "
                 "without it. If something does move, the three bits are worth "
                 "far more than the message -- watch the party row first, since "
                 "that array is what a row resolves a member through.",
        steps=_player_flags_steps(a),
        note="Run this with the roster OPEN (press P first) -- a change to the "
             "player record with no window showing it is a null we could not "
             "attribute. The sweep is 4 -> 0 -> 7 rather than retail's 4 alone, "
             "because a null on 4 cannot tell 'the message does nothing' from "
             "'we already look like 4'.",
    ),
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
    "armor": lambda a, o: Probe(
        question="What are the two dwords in 0x006F, and does it dress the agent?",
        predicts="One of the three argument orders produces visible chest armour. "
                 "If none does, 0x006F is not the visual-equip message on this "
                 "build and the 0x006D/6E/6F mapping needs revisiting.",
        steps=_armor_steps(a),
        note="EXPLORATORY. The study calls this mapping disputed; we are trying "
             "readings, not confirming a known one.",
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
    "damage": lambda a, o: Probe(
        question="Does damage arrive as agent property 16 on 0x00A3, and is the "
                 "value absolute health or a fraction of maximum?",
        predicts="The property channel works -- we have already OBSERVED the "
                 "client accept 0x009F without complaint. The units are a real "
                 "coin-flip: Headquarter's own client contradicts itself, "
                 "setting health to 1.0 and then clamping it against a maximum. "
                 "-0.25 moving the bar a quarter says FRACTION; -25.0 moving it "
                 "a quarter says ABSOLUTE. Exactly one of the two should be "
                 "visible.",
        steps=_damage_steps(a),
        note="ANSWERED 2026-08-06 -- FRACTION. Int property 42 raised a health "
             "bar reading 100; -0.25 took it to 75; -25.0 was dealt as 2500 and "
             "left it at 1. Kept runnable because it is the calibration for "
             "every combat number that follows, and because it turned up two "
             "things nobody asked it: health CLAMPS AT 1 rather than 0, so a "
             "damage packet cannot kill, and a positive value crashes the "
             "client on ArenaNet's own `damage.amount <= 0`. See "
             "studies/enemy/PLAN.md.",
    ),
    "death": lambda a, o: Probe(
        question="Is death bit 0x10 of the agent effects word, carried by "
                 "AGENT_UPDATE_EFFECTS (0x00F1)?",
        predicts="The hostile Hatcher dies when the bit is set and gets back up "
                 "when it is cleared. Two places in the client agree on the bit: "
                 "the effects setter zeroes the health and energy pools when it "
                 "is present, and the health path refuses to refill an agent "
                 "whose effects word carries it. If the body dies but does not "
                 "revive, the bit is a one-way state and something else resets "
                 "it.",
        steps=_death_steps(a, o),
        note="ANSWERED 2026-08-06, BOTH DIRECTIONS. 0x10 killed the Hatcher -- "
             "body down, nameplate and target gone -- and 0 brought it back at "
             "~0-1 health. Two things to carry into any server built on this: "
             "death DROPS the client's target, and reviving is TWO operations, "
             "because the death path zeroes the pools, so clearing the bit alone "
             "returns a body that dies to any scratch. Clear the bit, then set "
             "health. Seven guesses at a death MESSAGE failed before this; death "
             "is not a message.",
    ),
    "health_props": lambda a, o: Probe(
        question="Do the health properties we have never sent -- 34 and 55 -- "
                 "behave differently from damage, and can either one kill?",
        predicts="34 is ABSOLUTE and 55 is a FRACTION, from their disassembly: "
                 "55 multiplies the value by the agent's maximum health exactly "
                 "as damage does, and 34 passes it raw to a different callee. If "
                 "that holds, -50.0 on property 34 takes a 100-point bar to 50 "
                 "while -1.0 on property 55 empties it. Death is the open "
                 "question: damage floors at 1, and an absolute modifier is the "
                 "only thing we hold that can name zero.",
        steps=_health_props_steps(a, o),
        note="Came out of the client rather than out of a guess -- the float "
             "jump table in studies/agentprops/FINDINGS.md named the eight "
             "properties the client acts on, and three of them are health "
             "properties this project had never sent. Five earlier death "
             "candidates were guesses; this one is a reading.",
    ),
    "moving_die": lambda a, o: Probe(
        question="Does 0x002D do anything to a MOVING agent, and is it really "
                 "death or just a movement cancel?",
        predicts="It stops the character, indistinguishably from 0x0028 "
                 "AGENT_STOP_MOVING. The two handlers share their entire "
                 "opening, and 0x002D's body zeroes a float pair and clears a "
                 "state word -- a velocity, not a corpse. If that is what "
                 "happens, ldufr's AGENT_PLAYER_DIE is a misnomer and death is "
                 "somewhere else in the catalogue.",
        steps=_moving_die_steps(a),
        note="THE PLAYER MUST BE RUNNING for every step or the run is void: the "
             "handler's whole body is behind `test [agent+0x20], 0x20000`, which "
             "a standing agent does not satisfy. That single instruction "
             "explains all three of the null results this probe replaces.",
    ),
    "kill": lambda a, o: Probe(
        question="Does AGENT_PLAYER_DIE kill the PLAYER? It is the one death "
                 "candidate the last run could not reach.",
        predicts="A death animation and a resurrect prompt. The message's name "
                 "says player, its handler is real code rather than a stub, and "
                 "it did nothing when aimed at an NPC -- 'player-only' is the "
                 "reading that fits all three. If it does nothing here either, "
                 "death needs state we have never sent, and the next move is "
                 "reading P:\\Code\\Engine\\Agent\\AgMsg.cpp's handler properly "
                 "rather than sending a fifth guess.",
        steps=_kill_steps(a, o),
        note="Three candidates died in the 2026-08-06 run and are not re-sent: "
             "float property 42 = 0.0 (nothing), AGENT_ALLY_DESTROY (nothing), "
             "and int property 42 = 0, which refilled the bar and then crashed "
             "the client on CharPool.cpp's `range > 0`. That crash is why the "
             "fourth candidate never ran. This version cannot crash and can be "
             "re-run freely.",
    ),
    "attack_anim": lambda a, o: Probe(
        question="Which agent slot of generic value 4 names the ATTACKER -- "
                 "the one that plays the swing animation?",
        predicts="The FIRST slot. Sending slot1=the Hatcher makes the HATCHER "
                 "swing; swapping to slot1=you makes YOUR character swing. If "
                 "the same body moves both times, the second slot is "
                 "decorative and the first still names the attacker.",
        steps=_attack_anim_steps(a, o),
        note="This probe used to ask whether the equipped-items bag supplies "
             "the attack speed. It does not -- that was answered NO and the "
             "real answer is GAME_SMSG 0x0035 (studies/enemy/PLAN.md 6q), "
             "which the server now sends to every living agent. The probe kept "
             "its name and became the next question. It no longer expects to "
             "crash: if m_attackInterval fires again, an agent somewhere is "
             "missing its attack speed and THAT is the finding. Run with the "
             "weapon ON -- --no-weapon makes this meaningless.",
    ),
    "enemy_damage": lambda a, o: Probe(
        question="Does the client render an ENEMY taking damage, and is the "
                 "first agent slot of 0x00A3 really the target?",
        predicts="A floating damage number over the red Hatcher and its target "
                 "bar dropping 100 -> 75 -> 25. Section 6b established the "
                 "channel and the units but could not test the field order, "
                 "because it sent target and cause as the same agent. If the "
                 "PLAYER's bar drops instead, the slots are reversed and every "
                 "damage packet we would have written was aimed backwards.",
        steps=_enemy_damage_steps(a, o),
        note="Needs no interaction handling: the steps are on a timer, so "
             "nothing has to be invented about what a click means. Ends by "
             "asking the death question on a disposable body rather than on the "
             "player, who floors at 1 and never dies.",
    ),
    "npc_allegiance": lambda a, o: Probe(
        question="Is the team token an opaque identity compared between agents, "
                 "rather than a magic value the client recognises?",
        predicts="Agents 4 and 5 and 6 read as friendly or neutral; agent 7, "
                 "carrying a token the client has never seen, reads as an ENEMY "
                 "-- red nameplate, red compass dot. If all four look identical, "
                 "the token is not what decides hostility and the next candidate "
                 "is AGENT_UPDATE_ALLEGIANCE (0x002F), which no reference server "
                 "on disk ever sends.",
        steps=_npc_allegiance_steps(a, o),
        note="Built on a reading of Gw.exe rather than a guess: 'play' appears "
             "NOWHERE in the image as a dword constant, and the only "
             "allegiance-shaped constants anywhere are 'nonc' and 'nonn', "
             "sitting in one four-instruction predicate at 0x1AB130. So the "
             "field cannot be a word the client looks up -- it is an identity, "
             "with two special cases. Monster-class bodies this time, so the "
             "player-class confound that ruined the first attempt is gone.",
    ),
    "npc_agent": lambda a, o: Probe(
        question="Does a monster-class agent render, and does it need an NPC "
                 "definition to do it?",
        predicts="A body appears at +250 that does NOT read as another player -- "
                 "different nameplate colour, no Trade button -- because the "
                 "class nibble is 0x2 and there is no PLAYER_CREATE. Whether it "
                 "wears the right MODEL rests on file id 116228 surviving from "
                 "2013 to build 38797, which is a genuine coin-flip. The "
                 "undefined control at -250 should render nothing, or assert.",
        steps=_npc_agent_steps(a, o),
        note="RUN 2026-08-06. BOTH ANSWERED, first attempt. 'Hatcher "
             "[Collector]' rendered with a collector's body and a GOLD "
             "nameplate, plainly not a player -- so file id 116228 survives from "
             "2013 to build 38797, and the EncString resolved to real English "
             "text out of the client's own resources. The control crashed on "
             "`Assertion: index < m_count` at Base\\rtl\\Array.h(587) with our 99 "
             "in the trace: the definition index is a raw ARRAY INDEX, so "
             "creating an agent before defining its type is a crash, not a "
             "missing model. STEP 4 IS THE KNOWN CRASH -- it has done its job "
             "and re-running it only costs a session. Delete it before using "
             "this probe as a spawn template. See studies/enemy/PLAN.md 6d.",
    ),
    "die_0x2d": lambda a, o: Probe(
        question="Does AGENT_PLAYER_DIE (0x002D) kill, when damage cannot?",
        predicts="A death animation and a resurrect prompt. The `damage` probe "
                 "proved health clamps at 1 and the character keeps standing, so "
                 "SOMETHING has to end a life and this is the only message named "
                 "for it. A null result is still worth having: it would mean "
                 "death needs state we have never sent, and would move the "
                 "question to what allocates it.",
        steps=_die_0x2d_steps(a),
        note="ANSWERED, NEGATIVE. 0x002D does not kill, and its handler explains "
             "why (studies/enemy/PLAN.md 6h). Kept runnable because the negative "
             "is load-bearing for the `death` probe below. Steps 1-2 re-run the "
             "damage measurement so the probe controls itself.",
    ),
    "allegiance": lambda a, o: Probe(
        question="Is field 12 of WORLD_CREATE_AGENT what makes an agent hostile?",
        predicts="Three bodies appear, named for their tokens. 'play' and 'nonc' "
                 "are MEASURED values from an independent server and should read "
                 "as friendly. If 'mons' -- which is our guess and appears in no "
                 "source -- renders a red nameplate or an attackable target, the "
                 "enemy question is answered by one dword. If all three look "
                 "identical, hostility is NOT in this field and the next "
                 "candidate is AGENT_UPDATE_ALLEGIANCE (0x002F).",
        steps=_allegiance_steps(a, o),
        note="RUN 2026-08-06. NEGATIVE, and CONFOUNDED -- read the result as "
             "'field 12 does not make a PLAYER-class agent hostile', not as "
             "'field 12 is not allegiance'. All three rendered as other players: "
             "light-blue nameplates, light-blue compass dots, a Trade button. "
             "Player-class agents are players by construction -- model_id "
             "0x30000000 and a preceding PLAYER_CREATE both say so before the "
             "client reaches field 12 -- and the outpost forbids attacking "
             "anyway, so the targetability half measured nothing. The re-run "
             "needs monster-class agents in an explorable. "
             "What it DID prove, for free: the client renders agents it was not "
             "told to control, from six packets and no server code. That is E1 "
             "in studies/enemy/PLAN.md, done.",
    ),
    "spawn": lambda a, o: Probe(
        question="Does the character still spawn correctly with team token 'play'?",
        predicts="Identical behaviour to 0xBAADF00D. A regression here means the "
                 "three-lineage value is wrong for this build and we revert.",
        steps=_team_token_steps(a),
        note="No extra packets: the change is already in the spawn burst. Just "
             "confirm the character appears and moves as before.",
    ),
}


# Where the character stands when a probe fires, as (x, y, plane).
#
# Only used by probes that place something in the world, and only meaningful
# because a probe fires seconds after the spawn burst, before anyone has walked
# anywhere. The default is Kamadan's spawn point -- the map every session
# actually loads, via MAP_STATIC_CONFIG's fallback -- so that --list-probes and
# the encode self-test work with no server running. A live run passes the real
# one.
DEFAULT_ORIGIN = (-9067.0, 13218.0, 0)


def get(name, agent_id, origin=None):
    factory = PROBES.get(name)
    if factory is None:
        return None
    return factory(agent_id, origin or DEFAULT_ORIGIN)


def names():
    return sorted(PROBES)


def check_encodable(quiet=False):
    """Encode every step of every probe. Run this before spending a client run.

    A probe that fails to encode wastes a whole session -- the client has to be
    launched, logged in and walked into a map before the first packet fires, and
    the failure would not surface until then.

    `quiet` suppresses the per-step lines so the suite can call this as one
    check. It was reachable only from `__main__` until 2026-08-12, which meant
    the guard against wasting a client run was itself never run by the suite.
    """
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "schema"))
    from codec import Codec

    codec = Codec()
    bad = 0
    for name in names():
        probe = get(name, 1)
        if not probe.steps:
            if not quiet:
                print(f"  [ -- ] {name}: no packets, observation only")
            continue
        for step in probe.steps:
            if not getattr(step, "sends", True):
                # A declared refusal. It carries a message and no packet, so there is
                # nothing to encode and an encode attempt reports it as a broken probe
                # -- which is what happened on 2026-08-13 when the all-zero sweep
                # finished and the plan emptied. See Step's docstring for why this is a
                # flag and not an `if not step.values` test.
                if not quiet:
                    print(f"  [ -- ] {name}: {step.label} -> refusal, sends nothing")
                continue
            try:
                blob = codec.encode("GAME_SMSG", step.opcode, step.values)
                if not quiet:
                    print(f"  [PASS] {name}: {step.label} -> "
                          f"0x{step.opcode:04X}, {len(blob)}B")
            except Exception as exc:
                bad += 1
                print(f"  [FAIL] {name}: {step.label} -> "
                      f"{type(exc).__name__}: {exc}")
    return bad


def describe(name):
    p = get(name, 1)
    if p is None:
        return f"no probe named {name!r}"
    out = [f"  {name}", f"    Q: {p.question}", f"    predicts: {p.predicts}"]
    if p.note:
        out.append(f"    note: {p.note}")
    for i, s in enumerate(p.steps, 1):
        out.append(f"    {i}. +{s.delay:.0f}s  {s.label}")
    if not p.steps:
        out.append("    (no packets -- observation only)")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    print("Encoding every probe step against the live schema.\n")
    failures = check_encodable()
    print("\n" + ("ALL PROBES ENCODE" if not failures
                  else f"{failures} STEP(S) FAILED TO ENCODE"))
    sys.exit(1 if failures else 0)
