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

import struct

# Agent int-property ids (GmAgentProperties.h via studies/character/FINDINGS.md).
PROP_LEVEL = 36

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


def _team_token_steps(agent_id):
    # Not a packet probe: the token now goes out at spawn. This exists so the
    # run is recorded with a question attached rather than being assumed fine.
    return []


PROBES = {
    "level": lambda a: Probe(
        question="Is agent int-property 36 on 0x009F the character's level?",
        predicts="The nameplate reads 1, then 15, then 20. If it never changes, "
                 "either the property id is wrong or level is not sent this way.",
        steps=_level_steps(a),
        note="Corroborated by ldufr and gw-preservation, never observed by us. "
             "This is the highest-value packet in the queue: it converts the "
             "study's best-supported claim into an observation and explains why "
             "the character is level 0.",
    ),
    "attributes": lambda a: Probe(
        question="Is a 42-zero attribute array well-formed?",
        predicts="If ATTRIBUTE_COUNT = 42 is right, all three lengths are "
                 "accepted. If the client reads triplets, 42 misbehaves where 3 "
                 "does not.",
        steps=_attribute_steps(a),
        note="A null result is inconclusive -- one lineage never sends 0x003A at "
             "all, and one parser is documented to bail without a skillbar first.",
    ),
    "armor": lambda a: Probe(
        question="What are the two dwords in 0x006F, and does it dress the agent?",
        predicts="One of the three argument orders produces visible chest armour. "
                 "If none does, 0x006F is not the visual-equip message on this "
                 "build and the 0x006D/6E/6F mapping needs revisiting.",
        steps=_armor_steps(a),
        note="EXPLORATORY. The study calls this mapping disputed; we are trying "
             "readings, not confirming a known one.",
    ),
    "player_attrs": lambda a: Probe(
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
    "attr_sweep": lambda a: Probe(
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
    "attr_legend": lambda a: Probe(
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
    "damage": lambda a: Probe(
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
    "spawn": lambda a: Probe(
        question="Does the character still spawn correctly with team token 'play'?",
        predicts="Identical behaviour to 0xBAADF00D. A regression here means the "
                 "three-lineage value is wrong for this build and we revert.",
        steps=_team_token_steps(a),
        note="No extra packets: the change is already in the spawn burst. Just "
             "confirm the character appears and moves as before.",
    ),
}


def get(name, agent_id):
    factory = PROBES.get(name)
    if factory is None:
        return None
    return factory(agent_id)


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
