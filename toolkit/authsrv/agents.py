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


# ---------------------------------------------------------------- items
#
# A character with no weapon cannot attack and cannot use a weapon skill, and
# until 2026-08-06 ours had none: we sent four ITEM_WEAPON_SET slots of zeros
# and never created an item. The visible symptoms were that ATTACK_AGENT was
# never sent by the client at all -- not on click, not on space, in an outpost
# or in an explorable -- and that weapon skills would not even begin to cast.
#
# ItemType, from OpenTyria's GmItem.h enum. UPSTREAM.
ITEM_TYPE_HAMMER = 15

# The Prophecies warrior's starting weapon, verbatim from OpenTyria's
# GmDefaultArmors.c:80-93 (the sixth and last entry of
# g_DefWarriorPropheciesPveEquipments -- that array is 5 armour pieces plus one
# ItemType_Hammer). UPSTREAM: it is one lineage's hand-written table, and no
# capture of ours has ever carried these bytes. The two things worth watching
# if the client refuses it are file_id and flags.
#
# The name words are pre-encoded GW string ids, not text -- the same class of
# value as the NPC EncStrings. They can be copied and cannot be invented.
STARTER_HAMMER = dict(
    file_id=0x80009B60,
    item_type=ITEM_TYPE_HAMMER,
    dye_tint=6,
    dye_colors=0,          # DyeColor_None, GmColors.h:4
    materials=0,
    unk1=0,
    flags=0x22201000,
    value=0,
    model_id=1699,
    quantity=1,
    enc_name="".join(chr(w) for w in (0x2455, 0xB7FB, 0xCA41, 0x458F)),
    # Armour rating lives in these words for armour, and nobody in this repo has
    # decoded a single one of them -- see studies/character/FINDINGS.md, "The
    # modifier words: NOT DONE". Whatever a weapon's damage range is, it is in
    # here. They go out verbatim because they came from the same table row.
    modifiers=[0x24B80000, 0xA4880503],
)


def named_item(item_id, item):
    """GAME_SMSG 0x0161 CREATE_NAMED_ITEM -- declares an item's bytes.

    Declares only. Nothing is placed in a bag and nothing is worn: those are
    ITEM_MOVED_TO_LOCATION and the equipment messages respectively. See
    studies/character/FINDINGS.md section 2.

    The trailing modifier list is the client's field type 12, whose element
    layout is the schema tail and whose wire count is ONE byte -- so each
    modifier is passed as a single-element row.
    """
    return [item_id, item["file_id"], item["item_type"], item["dye_tint"],
            item["dye_colors"], item["materials"], item["unk1"], item["flags"],
            item["value"], item["model_id"], item["quantity"], item["enc_name"],
            [[m] for m in item["modifiers"]]]


# ------------------------------------------------- generic values (combat)
#
# The agent-property channel does not only carry health. Py4GW calls these
# GENERIC_VALUE_IDS (Py4GWCoreLib/PacketSniffer.py:263-277) and they are how the
# server drives combat animation on the client.
#
# UPSTREAM for the NAMES -- that is Py4GW's vocabulary, one lineage, no capture
# of ours carries them. CORROBORATED for the GROUPING, and by our own bytes:
# studies/agentprops/FINDINGS.md section 3b measured the int channel's second
# dispatch and found properties {4, 50, 60} sharing a single case. Py4GW
# independently names 50 attack_skill_activated and 60 skill_activated. Two
# lineages putting the same two ids in the same bucket is worth more than
# either alone -- but it is still not a wire OBSERVATION, and until one of
# these visibly changes the client these stay UPSTREAM.
GV_MELEE_ATTACK_FINISHED = 1
GV_ATTACK_STOPPED = 3
GV_DISABLED = 8
GV_SKILL_DAMAGE = 10
GV_MAX_HP_REACHED = 32
GV_INTERRUPTED = 35
GV_ATTACK_SKILL_FINISHED = 46
GV_INSTANT_SKILL_ACTIVATED = 48
GV_ATTACK_SKILL_STOPPED = 49
GV_ATTACK_SKILL_ACTIVATED = 50
GV_SKILL_FINISHED = 58
GV_SKILL_STOPPED = 59
GV_SKILL_ACTIVATED = 60


# ------------------------------------------------- the player's own pools
#
# We gave the ENEMY a health pool on the day it was spawned and never gave the
# player one. Not health, not energy, in any session. Every skill on the default
# bar costs 5 energy or 4-5 adrenaline, so an empty pool refuses all eight, which
# is exactly the observed symptom: the press animation plays and the cast never
# starts.
#
# Property 41 = energy, 42 = health, both on the int channel. CORROBORATED:
# gw-preservation's working server sends exactly these two in
# gameservice/player.go:268-269 with a comment naming each, and our own binary
# read of the int-record dispatch found cases for {32, 41, 42} and nothing else
# (studies/agentprops/FINDINGS.md section 3b). We had already MEASURED 42 as
# maximum health. 41 is the only remaining slot in that dispatch, and the one
# upstream calls energy.
PROP_ENERGY_MAX = 41

# Property 43 on the FLOAT channel. gw-preservation sends 0.0396 and its own
# comment says "REVERSE THIS MORE", so nobody upstream knows what it is either;
# our float-record dispatch does have a real case for 43. Energy regeneration is
# the obvious reading and is a GUESS -- it is here because it travels with the
# pair above in a server that works, not because we know what it does.
PROP_UNKNOWN_FLOAT_43 = 43
PLAYER_ENERGY = 25
PLAYER_HEALTH = 100
PLAYER_FLOAT_43 = 0.0396


# ------------------------------------------------- what an agent WIELDS
#
# Two different questions, and we had only answered the first:
#   0x006E UPDATE_AGENT_VISUAL_EQUIPMENT -- what the weapon LOOKS like (item ids)
#   0x006D NPC_UPDATE_WEAPONS            -- what KIND of weapon the agent wields
#
# The second drives attack range, speed and animation. GWCA reads the field it
# sets as AgentLiving::weapon_type at +h01B2, a uint16 sitting immediately after
# allegiance at +h01B1 (GameEntities/Agent.h:222-223) -- the combat block of the
# agent struct.
#
# This enum is NOT ItemType. A hammer is ItemType 15 and weapon_type 3, and
# using one where the other belongs is the obvious way to get this wrong.
# UPSTREAM: GWCA's comment is the only source, and it lists no value for 0.
WEAPON_TYPE_BOW = 1
WEAPON_TYPE_AXE = 2
WEAPON_TYPE_HAMMER = 3
WEAPON_TYPE_DAGGERS = 4
WEAPON_TYPE_SCYTHE = 5
WEAPON_TYPE_SPEAR = 6
WEAPON_TYPE_SWORD = 7
WEAPON_TYPE_WAND = 10
WEAPON_TYPE_STAFF = 12


# ------------------------------------------------- attackable, or merely red
#
# Being RED and being ATTACKABLE turned out to be two different things, and we
# had only ever arranged the first. The FourCC team token in WORLD_CREATE_AGENT
# field 12 decides colour: ours says 'mons', the client does not recognise it,
# and an unrecognised token renders hostile. But clicking the result made the
# client send INTERACT_PLAYER (0x0033) and never ATTACK_AGENT (0x0026) --
# OBSERVED across every session so far -- which is what it does for an NPC you
# talk to, not one you fight. It did not help that we built the thing out of a
# Collector definition.
#
# The field that actually decides is AgentLiving::allegiance at +h01B1, a single
# byte. UPSTREAM: GWCA GameEntities/Agent.h:222 is the only source for the
# values, and it names 1 as "ally/non-attackable" and 3 as "enemy" outright.
# GAME_SMSG_AGENT_UPDATE_ALLEGIANCE 0x002F carries it: the handler at 0x005fdd70
# reads field 1 as an agent-array index (bounds-checked, asserts if out of
# range) and hands field 2 to a setter for that agent in two collections --
# SOURCED, read from this build.
ALLEGIANCE_ALLY_NONATTACKABLE = 1
ALLEGIANCE_NEUTRAL = 2
ALLEGIANCE_ENEMY = 3
ALLEGIANCE_SPIRIT_PET = 4
ALLEGIANCE_MINION = 5
ALLEGIANCE_NPC_MINIPET = 6


# ------------------------------------------------- the fuller generic-value table
#
# GWCA's GenericValueID namespace (Packets/StoC.h:36-70) is a second, richer
# lineage than the Py4GW list above, and it corrects one of our sends: 1 is
# melee_attack_FINISHED, the end of a swing, not the start. We sent it and got
# no animation, which is exactly right for an id that means "that one is over".
#
# It also corroborates three things we had already measured ourselves --
# 16 damage, 34 health, 55 armour-ignoring -- and it names 4 attack_started,
# which lands in the same client dispatch case as 50 and 60 that our own read
# of the int table found ({4, 50, 60}, studies/agentprops/FINDINGS.md 3b).
# Independent naming agreeing with our own bytes is the best support anything
# in this file has.
#
# GWCA also names the four message shapes these travel on:
#   GenericValue          int,   no target    -- 0x009F
#   GenericValueTarget    int,   with target  -- 0x00A0 (same shape as 0x00A3)
#   GenericFloat          float, no target    -- 0x00A2
#   GenericTargetModifier float, with target  -- 0x00A3
# The first and last are OBSERVED working. The middle two are INFERRED from the
# field shapes matching; nothing has confirmed them on the wire.
GV_ATTACK_STARTED = 4      # GenericValueTarget: caster is victim, target is attacker
GV_ADD_EFFECT = 6
GV_REMOVE_EFFECT = 7
GV_CRITICAL = 17
GV_EFFECT_ON_TARGET = 20
GV_EFFECT_ON_AGENT = 21
GV_ANIMATION = 22
GV_ANIMATION_SPECIAL = 23
GV_ANIMATION_LOOP = 28
GV_HEALTH = 34             # a DELTA, not a setter -- we measured -50.0 as -50 health
GV_CHANGE_HEALTH_REGEN = 44
GV_ENERGY_GAIN = 52
GV_ARMOR_IGNORING = 55
GV_CASTTIME = 61
GV_ENERGY_SPENT = 62
GV_KNOCKED_DOWN = 63
