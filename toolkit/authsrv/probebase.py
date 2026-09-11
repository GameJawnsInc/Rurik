"""`Step`, `Probe`, `_f32`, the reserved agent ids and the probe item-id band.

The pieces every probe in this family is assembled out of, lifted verbatim from
`probes.py` on 2026-09-11 so the six subject modules beside it can each import
them without importing one another. Nothing here fires a packet or knows a
probe: a `Step` is one packet plus what a human should look at after it lands, a
`Probe` is a question with a prediction and a list of steps, and the rest is the
small set of numbers a probe must not collide with -- the reserved agent ids,
the definition index, and the 40s band the probe items live in.

WHY THIS ONE MOVED FIRST. `probes.py` was 7,800 lines covering seven subjects,
and every one of them referenced these names, so nothing else could move until
they had a home that imports nothing but `agents`. It is deliberately leaf
shaped -- standard library plus `agents` -- and it MUST NOT import `probes`:
`probes.py` runs as `__main__` under `python toolkit/authsrv/probes.py`, so a
leaf importing it back would load a SECOND copy of that module, with its own
`PROBES` dict and its own flags.

WHERE THE REFERENTS WENT. Several comments below travel verbatim and point at
things that stayed behind, and they are not reworded -- this paragraph is the
pointer instead. `PROBE_PLAYER_NUMBER`'s comment says "this module is only ever
handed an agent id (`probes.get(name, PLAYER_AGENT_ID, ...)`)": `get` is still
in `probes.py` and the sentence is about the probe family, not about this file.
`PROBE_BAR_SLOT`/`PROBE_BAR_SKILL`'s "the skill probes below say so" means the
skill probes, which are in `probeskills.py`. `Step`'s docstring names
`smsgsweep_steps`, which is `probes._smsgsweep_steps` and stayed there. The
armour-slot arm the item-id banner is about is `probeunitsetup._armor_slots_steps`
and the accum-drain probe is `probemerchant.PROBES["accum_drains"]`; both left
`probes.py` later the same day, which is why this paragraph said they had not.

`_ENEMY_ROW` still binds a content row AT IMPORT, exactly as it did in
`probes.py`: the same row, `content/world.toml`'s `[spawn.test_enemy]`, which
resolves on a machine with no vault. `test_bareimport.py` section 2 scans this
directory on disk, so it finds the bind here now instead of there and rules on
it the same way. The only thing that changed is that a `ContentError` out of it
is one frame deeper in the traceback.

Every name this module binds is re-exported by `probes.py`, at the site each one
was cut from, so `probes.<NAME>` still answers for all of them and no call site
moved. `import struct` is the one exception: `_f32` was its only user anywhere in
`probes.py`, so the import came here with it.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import (                                        # noqa: E402
    AGENT_KIND_NPC, AGENT_KIND_PLAYER, AGENT_TYPE_LIVING, APPEARANCE_WARRIOR,
    CHAR_CLASS_MONSTER_BASE, CHAR_CLASS_PLAYER_BASE, DEFAULT_RUN_SPEED,
    ALLEGIANCE_HOSTILE, EFFECT_DEAD, EFFECT_TRANSITION, HATCHER, INF, WORLD,
    agent_set_profession, agent_set_secondary_bits, agent_set_tabard_visible,
    create_agent, item_template, named_item, npc_model,
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


# Item ids for the armor-slot arm, declared by the probe itself via 0x0161.
#
# THESE WERE 2 AND 3 UNTIL 2026-08-27 AND BOTH COLLIDED WITH LIVE SERVER ITEMS.
# 2 is `authsrv.BACKPACK_ITEM_ID` and 3 is STARTER_ARMOUR's `warrior_body`, so
# this arm re-declared the player's backpack and chest onto the same client, on
# every run. Nothing failed: a second `0x0161` for an id the server already
# declared does not error, it overwrites the client's record, so any reading
# taken through this arm was measuring two writers at one slot.
#
# 43/44 AND NOT 10/11, which is the free pair immediately after the server's
# block. Probe items live in the 40s here already -- `_DRAIN_ITEM_A/B/C` are
# 40/41/42 -- and keeping the band means a probe id is visibly a probe id
# instead of sitting flush against ids the server mints. The server's own
# range is 1..9 plus purchases from `PURCHASED_ITEM_ID_BASE` (5000).
#
# `test_armour.py` §2 now scores every `_*_ITEM*` constant in this module
# against the server's minted set and reddens on any overlap. It did not read
# this module at all before, which is why the collision survived: the reserved
# check existed and was pointed one way only.
#
# CORRECTION 2026-09-11, appended rather than written over the sentence above,
# which records what the check WAS on the day the collision was found: "in this
# module" is no longer the scope. `probes.py` is being split into
# `probebase.py` and its siblings, all five `_*_ITEM` ids move to
# `probebase.py` together under this banner, and `probes.py` re-exports them.
# `test_armour.py` §2 now walks `probes` AND every `probe*.py` beside it,
# discovered on disk -- because a scan of `probes` alone would have gone on
# passing on five re-exported ids while a sixth minted in a sibling was
# invisible, which is the same one-way guard this banner is already about.
_ARMOR_LEGS_ITEM = 43
_ARMOR_BOOTS_ITEM = 44


# Item ids for the accum-drain probe, clear of the armor probe's 2/3 and the
# hammer. The declarations create them; the ids only need to be unclaimed.
_DRAIN_ITEM_A = 40
_DRAIN_ITEM_B = 41
_DRAIN_ITEM_C = 42


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
