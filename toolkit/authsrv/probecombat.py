"""Damage, death, kill, attack animation, allegiance, monster-class agents.

The combat arm of the probe family, lifted verbatim from `probes.py` on
2026-09-11: the damage arm and the enemy-damage arm, the superseded 0x002D arm
kept because its negative is load-bearing, the three allegiance FourCCs and the
four allegiance arms including the 0x00AA/0x002F split, the monster-class NPC
arm, the attack-animation arm, the EFFECTS bitfield and its death bit, the
death, health-property, moving-die and kill arms with the superseded v1 kill arm
kept for its record, and the thirteen registry entries that fire them.

It is leaf shaped by the same rule `probebase.py` is -- standard library plus
`agents` and `probebase` -- and it MUST NOT import `probes`: `probes.py` runs as
`__main__` under `python toolkit/authsrv/probes.py`, so a leaf importing it back
would load a SECOND copy of that module, with its own `PROBES` dict and its own
flags.

`EFFECT_DEAD` ARRIVES TWICE AND THE ORDER IS LOAD-BEARING. It is imported from
`agents` with the rest of the surface below and then REBOUND, further down, by
the assignment that carries the disassembly banner for it. The two values agree,
so a reconstruction that dropped the rebind would be only accidentally correct
-- and it is the rebind, not the import, that the banner is evidence for. Both
are kept, in the order they were in.

`ALLEGIANCE` IS A DERIVATION-REGISTER ROW. Two of its three tokens are MEASURED
from gw-preservation's agent table and the third is ours; `PLAN.md` section 6.1
carries the row, and it was re-aimed at THIS file before the constants moved,
because `derivlint.py` keys on the upstream rather than on the module and would
have stayed green while pointing at a file the constants had left. That row also
says `probes.py` re-exports them, which it does.

WHERE THE REFERENTS WENT. Every "above" and "below" in the comments that travel
with this code points INSIDE one step list or one registry note, with one
exception in each direction: `_die_0x2d_steps`' docstring and the `die_0x2d`
registry note both say the negative is load-bearing for "the `death` probe
below". That names a PROBE, not a source line -- `death` was already ABOVE
`die_0x2d` in the registry it was written in -- and both entries are in this
file's `PROBES` and still run as `--probe death` and `--probe die_0x2d`.

`PROBES` here holds only the thirteen combat entries. `probes.py` opens its own
dict, merges this one in with a duplicate-key raise, and keeps `get`, `names`,
`describe` and `check_encodable` -- so `probes.get("allegiance", ...)` answers
exactly as it did, and `names()` is still `sorted(PROBES)` and still returns the
same 97 names in the same order. Every name this module binds except `PROBES` is
also re-exported by `probes.py`, at the three sites they were cut from, so
`vars(probes)` still answers for all of them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import (                                        # noqa: E402
    AGENT_KIND_NPC, AGENT_KIND_PLAYER, AGENT_TYPE_LIVING, APPEARANCE_WARRIOR,
    CHAR_CLASS_MONSTER_BASE, CHAR_CLASS_PLAYER_BASE, DEFAULT_RUN_SPEED,
    EFFECT_DEAD, HATCHER, INF, create_agent)
from probebase import (                                     # noqa: E402
    PROBE_DEFINITION, Probe, Step, _f32)


def _allegiance_split_steps(agent_id, origin):
    """WHICH message flips allegiance -- 0x00AA, 0x002F, or only the pair?

    THE PRIOR RUN (harness 20260818T165525, `allegiance_pair`) MEASURED A FLIP
    and refuted its own stated prediction: a body created 'mons' rendered a RED
    compass dot, and ~1.5 s after receiving 0x00AA + 0x002F it rendered GREEN at
    the same compass position, while an untouched 'mons' control kept a
    pixel-identical red dot 6 px away. The compass changed at exactly two
    moments in that whole run -- the create, and the pair -- and at no other
    frame pair in 37. So SOMETHING in that pair updates displayed allegiance
    post-construction, which the static reading (+0x1B5 write-once, two
    constructor writers) says is impossible for the RENDERED surface.

    WHAT THAT RUN COULD NOT SAY, and it is exactly the CONTESTED question:
    the two messages went out 1.0 s apart against a 2 s frame cadence, so no
    frame separates them. `studies/enemy/PLAN.md` tested 0x002F ALONE and saw
    nothing; `studies/newopcodes` argues the pass therefore tested half a
    mechanism. This probe tests all four cells at once, one body each:

        agent 10  EAST   0x00AA alone
        agent 11  WEST   0x002F alone      <- the old experiment, re-run clean
        agent 12  NORTH  both, in retail's order   <- positive control
        agent 13  SOUTH  nothing at all             <- negative control

    Every body is created 'mons' (renders red), so every arm has the same
    starting state and the readout is one bit per body: did its dot go green.
    Arms are 10 s apart -- five frames at the 2 s cadence -- so attribution is
    never a straddled frame again, which is the one defect of the prior run.
    Bodies sit at +/-400 rather than +/-300 to spread the compass marks: the
    prior run's marks touched and merged into one blob, and only connected
    components pulled them apart.

    CONFOUND THE PRIOR RUN HIT, named so this one is read correctly: the client
    auto-targeted the first hostile it saw and drew a yellow ring around that
    dot, which merged with a neighbour. The ring vanished when the flip
    happened -- consistent with dropping a target that stopped being hostile,
    but it means "ring gone" and "dot turned green" were not independent there.
    Here the four bodies are far apart, so a ring can be attributed to one.

    PREDICTIONS, one per outcome, all four distinguishable:
      - only 12 flips  -> the PAIR is required; 0x00AA's record must exist
        before 0x002F's write means anything. Retail's order is the mechanism.
      - 11 flips       -> 0x002F alone suffices, and enemy/PLAN.md's null was
        an artifact of what it watched (it watched attack initiation, not the
        compass) rather than of sending half a mechanism.
      - 10 flips       -> 0x00AA carries it and 0x002F is bookkeeping, which
        would make upstream's AGENT_UPDATE_ALLEGIANCE name land on the wrong
        opcode of the two.
      - 13 flips       -> the readout is not measuring what we think; discard
        the run and the prior one with it.
    """
    ox, oy, plane = origin
    h = HATCHER
    model = CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION
    play, mons = 0x706C6179, 0x6D6F6E73
    spots = {10: (ox + 400, oy), 11: (ox - 400, oy),
             12: (ox, oy + 400), 13: (ox, oy - 400)}
    labels = {10: "EAST  -- 0x00AA ALONE", 11: "WEST  -- 0x002F ALONE",
              12: "NORTH -- BOTH (positive control)",
              13: "SOUTH -- NOTHING (negative control)"}
    steps = [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}", "nothing yet."),
    ]
    for aid in (10, 11, 12, 13):
        x, y = spots[aid]
        steps.append(Step(
            2.0, 0x0020,
            create_agent(aid, model, AGENT_KIND_NPC, x, y, plane,
                         allegiance=mons),
            f"agent {aid} {labels[aid]}, created 'mons'",
            "a RED dot on the compass at this bearing. All four must be red "
            "before any arm runs -- that is this run's baseline, and an arm "
            "whose body is not red first measures nothing."))
    steps += [
        Step(10.0, 0x00AA, [10, play, model],
             "ARM A: 0x00AA ALONE at agent 10 (EAST)",
             "does EAST go green with no 0x002F ever sent? Five frames follow "
             "before anything else moves."),
        Step(10.0, 0x002F, [11, play],
             "ARM B: 0x002F ALONE at agent 11 (WEST) -- enemy/PLAN.md's "
             "experiment, re-run against the compass",
             "does WEST go green with no 0x00AA ever sent? This is the cell "
             "the old null result actually tested."),
        Step(10.0, 0x00AA, [12, play, model],
             "ARM C part 1: 0x00AA at agent 12 (NORTH)",
             "nothing predicted yet -- ARM A's frames already say what 0x00AA "
             "alone does."),
        Step(1.0, 0x002F, [12, play],
             "ARM C part 2: 0x002F at agent 12 -- the pair, retail's order",
             "the prior run's flip should reproduce HERE. If NORTH goes green "
             "and neither EAST nor WEST did, the pair is the mechanism and "
             "each message alone is insufficient."),
        Step(10.0, 0x0000, [],
             "END: 10 s of quiet frames -- SOUTH (agent 13) must still be red",
             "the negative control's last word. A green SOUTH invalidates the "
             "whole run.", sends=False),
    ]
    return steps


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


def _allegiance_pair_steps(agent_id, origin):
    """Does retail's 0x00AA-then-0x002F pair CHANGE an existing agent's
    allegiance? The one CONTESTED row in studies/newopcodes/FINDINGS.md.

    THE CONTEST. Two upstream lineages at delta 0 (ldufr, maintained GWCA) call
    0x002F AGENT_UPDATE_ALLEGIANCE. Our own client says: its handler
    (0x005FDD70) stamps field 2 into +0xE8 of the per-agent AgMsg sync/async
    message-channel records -- plumbing, not the rendered allegiance (the
    agent's displayed teamToken also sits at +0xE8, of a DIFFERENT struct; the
    equal offset is a coincidence that has already misled once) -- and the
    attackability byte (+0x1B5) is write-once at construction, two writers in
    the whole image, both constructors (studies/enemy/PLAN.md 6p). "Sending it
    changed nothing" (enemy PLAN 6o) was measured on 0x002F ALONE. Retail NEVER
    sends it alone: both corpus sightings follow an 0x00AA for the same agent
    within the same burst, the pair carrying 'play' at agents created 'nonc'
    (newopcodes, capture 20260817T180610, agents 0x0F/0x11). This probe sends
    the PAIR -- the half of the mechanism no test has exercised.

    WHY RETAIL'S OWN TRANSITION IS INVISIBLE, AND THE DESIGN AROUND IT: 'nonc'
    and 'play' both render GREEN (npc_allegiance, 2026-08-06), so replaying
    nonc->play faithfully cannot show a verdict on any colour surface. The
    discriminating arm runs the SAME pair at a body created 'mons' (red).
    Field 2 still carries 'play' -- the only value ever seen in either message
    on retail -- so the invention is the body's starting colour, not the
    token, and the readout becomes a red->green FLIP: a shape change, per the
    make-the-signal-unmistakable rule, not a hue judgment. Three bodies, one
    definition, POSITION is the label:

        LEFT  (agent 4, 'nonc') -- retail-faithful arm
        RIGHT (agent 5, 'mons') -- the discriminator
        BACK  (agent 6, 'mons') -- control, never messaged after create

    RUN IT EXPLORABLE. 0x00AA's handler has a second step gated on
    MissionCliGetMap() == MISSION_MAP_GAME: field 2 becomes a roster KEY and
    every agent registered under the same token is enumerated and linked
    (newopcodes: 0x0091EF10 -> 0x00813560 -> 0x0084DD20). Every retail
    sighting is an outpost capture, so that enumeration has never fired
    anywhere, retail included. Pass --explorable or the run tests less than
    it could.

    CRASH NOTES, so a death is a diagnosis and not a mystery: 0x002F field 1
    is a bounds-checked index into the AgMsg sync/async arrays; a missing
    entry asserts syncPtr AgMsg.cpp(655) / asyncPtr AgMsg.cpp(660). That
    would itself be a finding -- our created agents lack a record retail's
    have -- and enemy PLAN 6o's 0x002F-alone send NOT crashing says the
    record does exist for bodies like these.
    """
    ox, oy, plane = origin
    h = HATCHER
    model = CHAR_CLASS_MONSTER_BASE | PROBE_DEFINITION
    play, nonc, mons = 0x706C6179, 0x6E6F6E63, 0x6D6F6E73
    return [
        Step(2.0, 0x0056,
             [PROBE_DEFINITION, h["file_id"], 0, h["scale"], 0, h["flags"],
              h["profession"], h["level"], h["enc_name"]],
             f"NPC_UPDATE_PROPERTIES def {PROBE_DEFINITION} (Hatcher, known good)",
             "nothing yet."),
        Step(1.0, 0x0057, [PROBE_DEFINITION, [h["model_id"]]],
             f"NPC_UPDATE_MODEL def {PROBE_DEFINITION}",
             "nothing yet. All three bodies share this definition -- position, "
             "not name, is the label."),
        Step(2.0, 0x0020,
             create_agent(4, model, AGENT_KIND_NPC, ox - 300, oy, plane,
                          allegiance=nonc),
             "agent 4 LEFT, created 'nonc' -- retail's precondition",
             "a Hatcher on the LEFT with a GREEN nameplate and dot (nonc is "
             "one of the client's two literal non-combatant values)."),
        Step(2.0, 0x0020,
             create_agent(5, model, AGENT_KIND_NPC, ox + 300, oy, plane,
                          allegiance=mons),
             "agent 5 RIGHT, created 'mons' -- the discriminator's start state",
             "a Hatcher on the RIGHT reading RED (unrecognised token falls "
             "through to hostile). If it is not red the discriminator is dead "
             "on arrival -- say so and read no further arm as a verdict."),
        Step(2.0, 0x0020,
             create_agent(6, model, AGENT_KIND_NPC, ox, oy - 300, plane,
                          allegiance=mons),
             "agent 6 BACK, created 'mons' -- the control, never messaged again",
             "a RED Hatcher behind the player. It must still be red in the "
             "final frame, or the whole run measured something else."),
        Step(12.0, 0x00AA, [4, play, model],
             "0x00AA agent 4: 'play' + its own model -- retail's preamble, "
             "faithful arm",
             "nothing predicted by either side at this instant; the pair is "
             "judged after 0x002F lands."),
        Step(1.0, 0x002F, [4, play],
             "0x002F agent 4: 'play' -- retail's nonc->play pair, complete",
             "the LEFT Hatcher: both readings predict green stays green here "
             "(saturation), so colour is NOT the signal in this arm -- watch "
             "instead for ANY new artifact: party/roster rows, compass "
             "changes, chat, a nameplate rewrite."),
        Step(12.0, 0x00AA, [5, play, model],
             "0x00AA agent 5: 'play' + its own model -- the discriminator's "
             "preamble",
             "nothing yet; the flip, if it comes, is allowed to come here or "
             "at the next step -- note WHICH."),
        Step(1.0, 0x002F, [5, play],
             "0x002F agent 5: 'play' at a RED body -- THE TEST",
             "if the pair updates displayed allegiance, the RIGHT Hatcher "
             "flips red->green -- nameplate AND compass dot -- while the "
             "control behind stays red. If nothing moves in 20 seconds, the "
             "static reading holds and upstream's name fails on every "
             "rendered surface. A crash naming AgMsg.cpp(655/660) is the "
             "third outcome and is a finding, not a failure."),
    ]


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


PROBES = {
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
    "allegiance_pair": lambda a, o: Probe(
        question="Does retail's 0x00AA-then-0x002F pair change an EXISTING "
                 "agent's allegiance -- the one CONTESTED row left in "
                 "studies/newopcodes/FINDINGS.md?",
        predicts="The static reading says NO VISIBLE CHANGE in either arm: "
                 "0x002F writes AgMsg message plumbing, the attackability "
                 "byte is write-once at construction, and no post-construction "
                 "writer of the displayed teamToken is known -- so the RIGHT "
                 "Hatcher stays red and upstream's AGENT_UPDATE_ALLEGIANCE "
                 "name fails for every rendered surface. Upstream predicts "
                 "the opposite shape: RIGHT flips red->green on nameplate and "
                 "compass dot while the BACK control stays red. Either "
                 "outcome settles the contest for pixels; a crash naming "
                 "AgMsg.cpp(655/660) is the third outcome and localises the "
                 "sync/async record instead.",
        steps=_allegiance_pair_steps(a, o),
        note="Run with --explorable: 0x00AA's second step -- field 2 as a "
             "roster KEY, enumerating same-token agents -- is gated on "
             "MISSION_MAP_GAME and has never fired ANYWHERE, retail included "
             "(both corpus sightings are outpost captures). Field 2 carries "
             "'play' in every send because it is the only value either "
             "message has ever been seen to carry; the discriminator is the "
             "BODY's starting colour, not an invented token. Position is the "
             "label: LEFT nonc (faithful), RIGHT mons (discriminator), BACK "
             "mons (control). Frames bracket each send via the gamesrv log's "
             "timestamps; compass dots are the fixed-position readout, "
             "nameplates the confirming one (hold ALT via --walk 'alt:').",
    ),
    "allegiance_split": lambda a, o: Probe(
        question="WHICH message flips a body's displayed allegiance -- "
                 "0x00AA alone, 0x002F alone, or only the pair? The prior "
                 "run measured the flip but sent both 1 s apart against a "
                 "2 s frame cadence, so no frame separates them.",
        predicts="Leading expectation: only agent 12 (BOTH) flips, because "
                 "0x00AA creates the per-agent record 0x002F then writes "
                 "into, and a write with no record is the no-op "
                 "studies/enemy/PLAN.md measured. If agent 11 (0x002F "
                 "ALONE) flips, that null was about what it WATCHED -- "
                 "attack initiation, not the compass -- rather than about a "
                 "half-sent mechanism. If agent 10 (0x00AA ALONE) flips, "
                 "upstream's AGENT_UPDATE_ALLEGIANCE names the wrong opcode "
                 "of the two. Agent 13 must stay red in every frame; a green "
                 "13 discards this run AND the prior one.",
        steps=_allegiance_split_steps(a, o),
        note="The attribution half of allegiance_pair (harness "
             "20260818T165525), which measured a red->green flip on a 'mons' "
             "body given the pair while an untouched 'mons' control stayed "
             "pixel-identically red -- refuting this repo's static reading "
             "(+0x1B5 write-once) for the RENDERED surface. Run "
             "--explorable: 0x00AA's roster-key step is MISSION_MAP_GAME-"
             "gated, it was live in the run that flipped, and it has never "
             "fired in any retail capture (both sightings are outposts), so "
             "an outpost re-run is a different experiment. Arms are 10 s "
             "apart and bodies are +/-400 so marks neither straddle a frame "
             "nor merge into one blob -- both defects of the prior run.",
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
}
