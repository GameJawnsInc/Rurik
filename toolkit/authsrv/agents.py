"""Agents other than the player: what the client must be told to render one.

Extracted so the server and the probes cannot drift apart. Every constant and
every field order here was proven against our own client before it was moved
into this file -- see studies/enemy/PLAN.md for the run that established each,
and studies/agentprops/FINDINGS.md for the ones read out of the binary.

Nothing here invents anything. The one thing that is somebody else's data is
HATCHER's file and model ids, and the licence question that raises is recorded
at studies/enemy/PLAN.md section 5 rather than settled here.
"""

INF = float("inf")

# GmAgent.h: the top nibble of model_id is a class tag. OBSERVED both ways --
# a player-class body renders as another player, complete with a Trade button,
# and a monster-class body renders as an NPC (studies/enemy/PLAN.md 6c, 6d).
CHAR_CLASS_PLAYER_BASE = 0x30000000
CHAR_CLASS_MONSTER_BASE = 0x20000000

AGENT_TYPE_LIVING = 1
AGENT_KIND_PLAYER = 5          # WORLD_CREATE_AGENT's h000B byte
AGENT_KIND_NPC = 9             # 0 item, 5 player, 9 NPC

DEFAULT_RUN_SPEED = 288.0
APPEARANCE_WARRIOR = 1 << 20

# Field 12 of WORLD_CREATE_AGENT is an allegiance FourCC, and it is an opaque
# team IDENTITY rather than a vocabulary the client looks up: 'play' appears
# NOWHERE in Gw.exe as a dword constant, and the only allegiance-shaped
# constants in the image are 'nonc' and 'nonn', inside one four-instruction
# predicate. OBSERVED: an agent carrying the player's own token reads green, the
# two client constants read green, and an unrecognised token reads RED.
# See studies/enemy/PLAN.md section 6e.
ALLEGIANCE_PLAYER = 0x706C6179        # 'play'  -- same team as the player
ALLEGIANCE_NONCOMBATANT = 0x6E6F6E63  # 'nonc'  -- the client's own constant
ALLEGIANCE_HOSTILE = 0x6D6F6E73       # 'mons'  -- any UNRECOGNISED value is an
                                      # enemy; these particular bytes are not
                                      # special and nothing in the client knows
                                      # them.

# Agent property ids (float channel, GAME_SMSG 0x00A3 -- prop_id, target, cause,
# value). Which ones the client acts on is SOURCED from its own jump tables;
# see studies/agentprops/FINDINGS.md.
PROP_DAMAGE = 16          # a FRACTION of maximum health. Floors at 1: cannot kill.
PROP_HEALTH_ABSOLUTE = 34 # an ABSOLUTE quantity, and SILENT -- no damage number.
PROP_HEALTH_MAX = 42      # int channel (0x009F). Sets the maximum AND refills.

# The agent effects bitfield, carried by GAME_SMSG 0x00F1. Bit 4 is death:
# setting it kills, clearing it revives. OBSERVED both directions.
#
# Reviving is TWO operations. The client's death path zeroes the health and
# energy pools, so clearing the bit alone returns a body at ~0-1 health that
# dies to any scratch. Clear the bit, then set health.
EFFECT_DEAD = 0x10

# One NPC definition, transcribed from gw-preservation's agent table as a lead
# and then CONFIRMED against our own client: 'Hatcher [Collector]' rendered with
# a collector's body and its real localised name. File id 116228 also appears in
# GWLP-R's mock NPC from 2013, so it is two lineages thirteen years apart.
#
# enc_name is an EncString -- references into the client's own localised text
# resources, not characters. It cannot be invented; this one was copied whole
# and the client resolved it to English.
HATCHER = dict(
    name="Hatcher [Collector]",
    file_id=116228,
    model_id=116703,
    profession=3,
    level=1,
    enc_name="".join(chr(w) for w in (0x328A, 0xE3B9, 0xAA36, 0x2E69)),
    scale=0x64000000,      # hue 0, saturation 0, lightness 0, scale 100%
    flags=0x20C,
)


def npc_properties(definition, npc, level=None):
    """GAME_SMSG 0x0056 -- defines an NPC TYPE. Must precede any agent using it.

    Not optional and not decoration: the definition index is a raw array index
    on the client, and creating an agent whose definition was never sent takes
    the client down on `index < m_count` in Base\\rtl\\Array.h. OBSERVED.
    """
    return [definition, npc["file_id"], 0, npc["scale"], 0, npc["flags"],
            npc["profession"], npc["level"] if level is None else level,
            npc["enc_name"]]


def npc_model(definition, npc):
    """GAME_SMSG 0x0057 -- the model files for an NPC type."""
    return [definition, [npc["model_id"]]]


def create_agent(agent_id, model_id, kind, x, y, plane,
                 allegiance=ALLEGIANCE_PLAYER, speed=DEFAULT_RUN_SPEED):
    """GAME_SMSG 0x0020, 23 fields, 99 bytes on the wire.

    The field order is the one the player's own body has always used and which
    the client's message-format table confirms; the offset-named fields are
    unknowns carried verbatim rather than guessed at. See
    studies/character/FINDINGS.md section d for what is and is not known here.
    """
    return [agent_id, model_id, AGENT_TYPE_LIVING, kind,
            (float(x), float(y)), plane, (1.0, 0.0), 1,
            speed, 1.0, 0x41400000, allegiance,
            0, 0, 0, 0, 0, (0.0, 0.0), (INF, INF), 0, 0, (INF, INF), 0]
