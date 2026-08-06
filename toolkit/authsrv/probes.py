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
from agents import (                                        # noqa: E402
    AGENT_KIND_NPC, AGENT_KIND_PLAYER, AGENT_TYPE_LIVING, APPEARANCE_WARRIOR,
    CHAR_CLASS_MONSTER_BASE, CHAR_CLASS_PLAYER_BASE, DEFAULT_RUN_SPEED,
    EFFECT_DEAD, HATCHER, INF, create_agent, npc_model, npc_properties)

# Agent int-property ids (GmAgentProperties.h via studies/character/FINDINGS.md).
PROP_LEVEL = 36
# Property 60. SOURCED three ways: GWLP-R (2013) and GWCA both name it
# CastSkill/skill_activated, and on build 38797 the client's own generic-value
# dispatcher gives 4, 50 and 60 -- and only those three -- one shared case body
# that reaches AvApi and queues an AgentView event carrying the skill id.
# studies/skillcast/FINDINGS.md section 6.
PROP_CAST_SKILL = 60

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
    """One packet, plus what a human should look at after it lands."""

    def __init__(self, delay, opcode, values, label, watch):
        self.delay = delay
        self.opcode = opcode
        self.values = values
        self.label = label
        self.watch = watch


class Probe:
    def __init__(self, question, predicts, steps, note=""):
        self.question = question
        self.predicts = predicts
        self.steps = steps
        self.note = note


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
    # The question is whether a 42-zero array is even well-formed. One lineage
    # reads this payload as triplets; another never sends the message at all.
    # If 42 is right, all three should be accepted. If the client reads
    # triplets, 42 (not divisible by 3) is the one that should misbehave.
    return [
        Step(2.0, 0x003A, [agent_id, []], "attributes: empty",
             "the attribute panel (open the Hero window). Anything odd?"),
        Step(6.0, 0x003A, [agent_id, [0, 0, 0]], "attributes: 3 zeros",
             "same panel. Still fine?"),
        Step(6.0, 0x003A, [agent_id, [0] * 42], "attributes: 42 zeros",
             "same panel. If this one breaks and 3 did not, our 42 is wrong."),
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


PROBES = {
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
    "attributes": lambda a, o: Probe(
        question="Is a 42-zero attribute array well-formed?",
        predicts="If ATTRIBUTE_COUNT = 42 is right, all three lengths are "
                 "accepted. If the client reads triplets, 42 misbehaves where 3 "
                 "does not.",
        steps=_attribute_steps(a),
        note="A null result is inconclusive -- one lineage never sends 0x003A at "
             "all, and one parser is documented to bail without a skillbar first.",
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


def check_encodable():
    """Encode every step of every probe. Run this before spending a client run.

    A probe that fails to encode wastes a whole session -- the client has to be
    launched, logged in and walked into a map before the first packet fires, and
    the failure would not surface until then.
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
            print(f"  [ -- ] {name}: no packets, observation only")
            continue
        for step in probe.steps:
            try:
                blob = codec.encode("GAME_SMSG", step.opcode, step.values)
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
