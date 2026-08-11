"""Rurik AuthSrv — Stage B of the Guild Wars login.

Completes the Diffie-Hellman key exchange with a patched client, brings up the
ARC4 channel, and then records every decrypted message the client sends.

The recording is the point. Everything past the handshake is encrypted on the
wire, so a passive capture of the real service yields ciphertext. Here we hold the
key, which makes this the first place in the project where CtoS traffic can be
read in plaintext. It writes both the raw ciphertext and the decrypted bytes: the
ciphertext because HANDOFF.md's rule is record raw and parse later, the plaintext
because it is what makes the vault immediately useful.

Handshake, as observed from build 38797 and confirmed against two independent
public implementations:

    client -> AUTH_CMSG_VERSION   u32 header 0x000C0400, u32 build, u32 1, u32 4
    client -> MSG_CLIENT_SEED     u16 header 0x4200, 64 bytes A = g^a mod p
    server -> MSG_SERVER_SEED     u16 header 0x1601, 20 bytes master_secret XOR shared
    both   -> ARC4, key = arc4_hash(master_secret), separate state per direction

What this does NOT do yet: answer anything after the handshake. The client will
ask to log in with its portal token and expect a character list. Those replies are
the next piece of work; until then it will connect, key up, talk, and time out —
and we will have its words written down, which is the prerequisite for answering.
"""

import argparse
import binascii
import itertools
import json
import math
import os
import secrets
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema"))
from gwcrypto import ARC4, arc4_hash, compute_shared, make_server_seed  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'portal'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from codec import Codec  # noqa: E402
from sessionstore import SessionStore, wire_to_uuid  # noqa: E402
from vaultpath import vault_path  # noqa: E402
import probes  # noqa: E402
import labelrun  # noqa: E402
import agents  # noqa: E402
import origin  # noqa: E402


def _f32(x):
    """A float as the dword the codec will put on the wire.

    The schema types these fields `dword` because the client's own format
    tables do -- a float and a dword are the same four bytes to its generic
    deserializer, and only the handler knows which it is. So every float we
    send goes out through here.
    """
    return struct.unpack("<I", struct.pack("<f", x))[0]


AUTH_CMSG_VERSION_HEADER = 0x000C0400
# 0x000C0700 came from the reference sources. 0x000C0500 is what build 38797
# actually sends to a game server -- measured on the wire 2026-08-05, from a raw
# listener that assumed nothing about the protocol. Accept both; the sources have
# been wrong about this build before.
GAME_CMSG_VERSION_HEADER = 0x000C0700
GAME_CMSG_VERSION_HEADER_38797 = 0x000C0500
GAME_VERSION_HEADERS = (GAME_CMSG_VERSION_HEADER, GAME_CMSG_VERSION_HEADER_38797)
CMSG_CLIENT_SEED_HEADER = 0x4200
SMSG_SERVER_SEED_HEADER = 0x1601

# Client-to-auth opcodes carry a high bit; the schema indexes them without it.
AUTH_CMSG_MASK = 0x8000
AUTH_CMSG_SEND_COMPUTER_INFO = 0x0001
AUTH_CMSG_SEND_COMPUTER_HASH = 0x0002
AUTH_SMSG_SESSION_INFO = 0x0001

AUTH_CMSG_HEARTBEAT = 0x0000
AUTH_CMSG_UNKNOWN_8023 = 0x0023
AUTH_CMSG_ACCEPT_EULA = 0x0026
AUTH_CMSG_PORTAL_ACCOUNT_LOGIN = 0x0038
AUTH_SMSG_HEARTBEAT = 0x0000
AUTH_SMSG_REQUEST_RESPONSE = 0x0003
AUTH_SMSG_CHARACTER_INFO = 0x0007
AUTH_SMSG_ACCOUNT_INFO = 0x0011
AUTH_SMSG_FRIEND_STREAM_END = 0x0014
AUTH_SMSG_ACCOUNT_SETTINGS = 0x0016

# ---- R2: the handoff to the game server ---------------------------------
# Pressing Play walks this path:
#   SET_PLAYER_STATUS  -> recorded, no reply
#   CHANGE_PLAY_CHARACTER -> REQUEST_RESPONSE(req_id, 0)
#   REQUEST_GAME_INSTANCE -> GAME_SERVER_INFO, then REQUEST_RESPONSE(req_id, 0)
# after which the client opens a SECOND connection, to the address we hand it,
# and repeats the version/DH/ARC4 handshake on a different message catalog.
AUTH_CMSG_CHANGE_PLAY_CHARACTER = 0x000A
AUTH_CMSG_SETTING_UPDATE_CONTENT = 0x0020
AUTH_CMSG_SETTING_UPDATE_SIZE = 0x0021
AUTH_CMSG_SET_PLAYER_STATUS = 0x000E
AUTH_CMSG_REQUEST_GAME_INSTANCE = 0x0029
AUTH_CMSG_ASK_SERVER_RESPONSE = 0x0035
AUTH_SMSG_GAME_SERVER_INFO = 0x0009

# The instance bring-up a real game server sends unprompted once the channel is
# up. Order is OpenTyria's GameSrv_SendInitialPackets for a main town. The client
# does NOT ask for these -- it sends its computer-info pair (GAME_CMSG 0x000A and
# 0x000B, which no reference implementation handles) and then waits for the server
# to start talking. Answering the computer info is not what unblocks it.
GAME_SMSG_INSTANCE_LOAD_HEAD = 0x017C
GAME_SMSG_INSTANCE_LOAD_PLAYER_NAME = 0x017D
GAME_SMSG_INSTANCE_PLAYER_DATA_START = 0x0186
GAME_SMSG_INSTANCE_PLAYER_DATA_DONE = 0x018A
GAME_SMSG_INSTANCE_LOAD_INFO = 0x0199
GAME_SMSG_MAP_UPDATE_CURRENT = 0x0099
GAME_SMSG_ITEM_STREAM_CREATE = 0x0144
GAME_SMSG_INSTANCE_LOAD_SPAWN_POINT = 0x0195
GAME_SMSG_READY_FOR_MAP_SPAWN = 0x01AB
GAME_SMSG_ITEM_WEAPON_SET = 0x0147
GAME_SMSG_ITEM_SET_ACTIVE_WEAPON_SET = 0x0148
GAME_SMSG_CREATE_NAMED_ITEM = 0x0161
GAME_SMSG_INVENTORY_CREATE_BAG = 0x013F
GAME_SMSG_ITEM_MOVED_TO_LOCATION = 0x013E
# The equipped-items bag: type 2, model 21, nine slots, weapon in slot 0.
# CORROBORATED across ldufr (GmInventory.c:21-27, GmInventory.h:6-10) and
# gw-preservation (item/item.go:139-152).
BAG_TYPE_EQUIPPED = 2
BAG_MODEL_EQUIPPED = 21
EQUIPPED_BAG_ID = 1
EQUIPPED_SLOT_WEAPON = 0
EQUIPPED_SLOT_COUNT = 9
# agent_id + NINE item ids. The message that puts equipment on a BODY, as
# opposed to CREATE_NAMED_ITEM which only declares an item's bytes and
# ITEM_WEAPON_SET which fills the weapon-swap UI.
GAME_SMSG_UPDATE_AGENT_VISUAL_EQUIPMENT = 0x006E
# agent_id + two ids. CONTESTED as of 2026-08-10, and the comment that used to
# sit here said "WEAPON TYPES rather than item ids" while the call site 2,900
# lines below said the opposite -- studies/smsg's naming pass proposed renaming
# it on that basis and its own refutation pass rejected the rename, because the
# repo had already settled the question OBSERVED on 2026-08-06 by crashing a real
# client on the assert in question (studies/enemy/PLAN.md). What IS established:
# 291/291 of its non-zero values in a tape were declared by an earlier
# 0x015E/0x0161 in that same tape, so whatever the ids mean, they are not free
# -- a server must declare before it references. The noun stays unsettled; see
# studies/smsg/FINDINGS.md section 2.
GAME_SMSG_NPC_UPDATE_WEAPONS = 0x006D
# agent_id + allegiance byte. The field that decides whether a click is an
# attack or a conversation; the team token only decides colour.
GAME_SMSG_AGENT_UPDATE_ALLEGIANCE = 0x002F
# agent_id + float base + float modifier. The ONLY way to give an agent an
# attack speed: without it the client's AvChar keeps the 0.0 its constructor
# wrote and asserts m_attackInterval the moment a swing would animate. Unnamed
# in every reconstruction we hold; the name is ours, from the client's own
# AvChar::SetAttackSpeed argument names. See agents.ATTACK_SPEED and
# studies/enemy/PLAN.md 6q.
GAME_SMSG_AGENT_UPDATE_ATTACK_SPEED = 0x0035

# The item id we hand the starter hammer. Any nonzero value the client has not
# already seen would do; 1 is the first because the inventory is otherwise
# empty. It is what goes in the weapon set's leadhand slot.
WEAPON_ITEM_ID = 1
# Give the character a weapon at all. --no-weapon turns it off so the "naked
# character cannot attack" reading can be re-tested rather than remembered.
EQUIP_WEAPON = True
# Seconds between swings for the weapon we actually hand out, which is a
# hammer. WIKI (GWW, "Attack speed"), and the client agrees -- see
# agents.ATTACK_SPEED for the six-for-six cross-check. This is the value that
# goes on the wire AND the interval the server swings on, deliberately the same
# constant: two numbers that must match and used to be 1.33 and nothing.
WEAPON_ATTACK_SPEED = agents.ATTACK_SPEED["hammer"]
GAME_SMSG_UPDATE_GOLD_STORAGE = 0x0141
GAME_SMSG_CHARACTER_UPDATE_INFO = 0x0030
GAME_SMSG_INSTANCE_MANIFEST_PHASE = 0x0198
GAME_SMSG_INSTANCE_MANIFEST_DONE = 0x0197
GAME_SMSG_INSTANCE_LOAD_FINISH = 0x018E

# Nothing we sent ever put a body in the world. The client asks for everything it
# knows to ask for, we answer all of it, and it stops at 100% because there is no
# agent to spawn. These are the messages a real server volunteers unprompted --
# GameSrv_HandleInstanceLoadRequestPlayers sends roughly twenty; this is the
# subset that creates the player and hands them control of it.
# The one message upstream broadcasts on EVERY world tick, unconditionally, and
# the only thing its tick sends at all (GmAgent.c:261-268, :440). Payload is a
# single uint32 of elapsed milliseconds. We had never sent it once.
GAME_SMSG_WORLD_SIMULATION_TICK = 0x001E
GAME_SMSG_WORLD_UPDATE_LOAD_TIME = 0x001F
GAME_SMSG_WORLD_CREATE_AGENT = 0x0020

# The counterpart, and until 2026-08-07 we could create an agent and never destroy
# one. 6 bytes: header + the agent id to remove.
#
# OBSERVED from the first live capture (studies/divergence/FINDINGS.md D1):
# ArenaNet sent it 416 times across four in-world instances; our server has sent
# it 0 times in 271,449 recorded s2c messages. The dword is a previously-created
# agent id in 416 of 416 cases keyed on WORLD_CREATE_AGENT's field 0, and in only
# 3 of 416 keyed on field 1 -- a split no framing accident produces. Forcing other
# sizes breaks the stream: at 2 bytes only 54,411 of 190,544 GAME_SMSG bytes
# frame, at 10 bytes 63,911, at the catalogued 6 all 190,544.
#
# CORROBORATED by the client's own binary rather than by our schema alone:
# `msgshape` reads the RECV table at 0x00a52d70 as opcode 0x0021 -> handler
# 0x005FD2F0, one u32 field, 6 bytes on the wire, and `asserts.py --at 0x005fd2f0`
# names `Array:587 "index < m_count"` -- the client bounds-checks the dword as an
# index into its agent array, then walks every object bound to that agent and
# clears the bindings. That is a teardown handler, read out of the client, not
# inferred from a name.
#
# WHY IT MATTERS BEYOND TIDINESS: ArenaNet REUSES agent ids, and removal is the
# prerequisite. OBSERVED: 301 of 301 id re-creations in the live capture are
# preceded by a removal of that same id, and 0 of 416 removals target a
# never-created id or double-remove without an intervening create.
GAME_SMSG_WORLD_REMOVE_AGENT = 0x0021
GAME_SMSG_WORLD_UPDATE_CONTROLLED_AGENT = 0x0022
GAME_SMSG_PLAYER_INFO = 0x0059
GAME_SMSG_PLAYER_UPDATE_PROFESSION = 0x00B7

# The 15-dword player attribute set. OBSERVED 2026-08-05: sending this with
# field 9 = 15 moved the Hero window to Level 15 and it stayed there, so field 9
# is the per-PLAYER level on this build. That resolves a claim four lineages
# disagreed about, using the only source that can settle it.
#
# Do not confuse this with the per-AGENT level, which is int property 36 on
# 0x009F and drives the nameplate. They are unrelated channels, and probing one
# while watching the other is how the first attempt read as a false negative.
#
# Field map (studies/character/FINDINGS.md): 0 xp, 1-6 factions, 7-8 unknown,
# 9 level, 10 morale, 11-12 balthazar, 13-14 skill points. Only field 9 is
# confirmed by us; the rest are corroborated-but-unobserved, so they go out as
# zeros rather than as invented values.
GAME_SMSG_CHARACTER_UPDATE_FACTIONS = 0x00E9
PLAYER_ATTR_COUNT = 15
PLAYER_ATTR_XP = 0
PLAYER_ATTR_LEVEL = 9
PLAYER_ATTR_MORALE = 10
# Level 1 rather than 20: the character-select blob already says level 1, and
# two places disagreeing about the same character is a bug we would rather not
# introduce while we are still learning what reads what.
START_LEVEL = 1
GAME_SMSG_INSTANCE_LOADED = 0x00F2

# Appearance is a 32-bit bitfield (GmChar.h): sex:1, height:4, skin:5, hair:5,
# face:5, primary_profession:4, hair_style:6, race:2, packed low bits first. A
# Warrior is profession 1, so it lands at bits 20-23.
PROF_WARRIOR = 1
APPEARANCE = PROF_WARRIOR << 20

PLAYER_AGENT_ID = 1        # what INSTANCE_LOAD_INFO already claims
DEFAULT_RUN_SPEED = 288.0  # Guild Wars' base movement speed
# How often the server reports where the agent got to. The client SNAPS to each
# position we send rather than interpolating between them, so this rate is
# visible directly as motion smoothness: at 0.25 the character jolted forward a
# few times a second. A real server ticks slowly and lets the client animate
# toward the destination; until we work out what makes it do that (probably
# AGENT_UPDATE_DESTINATION rather than MOVE_TO_POINT), a fast tick buys
# smoothness cheaply -- this is loopback, and 20 Hz of one small message is free.
TICK_SECONDS = 0.05
# How far the client's own idea of where it stopped may differ from ours before
# we overrule it. Upstream's figure (OpenTyria GmAgent.c:4) and, like every other
# constant in that file, its own invention rather than a measurement.
MAXIMUM_ALLOWED_CORRECTION = 100.0
INF = float("inf")

# Collision. The navmesh comes out of Gw.dat -- see toolkit/mapdata/pathmap.py,
# which documents both the layout and how much of it is checked rather than
# believed. This is the first thing the server does that is grounded in the
# game's own data instead of in someone's reconstruction of a server.
#
# It is OPTIONAL on purpose. The archive is 5 GB of the player's own install and
# is not in the repository; without it the server runs exactly as it did before,
# which is to say it lets you walk through walls.
COLLISION_STEP = 16.0      # sampling interval along a leg, ~1/20s at run speed
# NOTHING CLIPPED EVER GOES ON THE WIRE. The navmesh bounds the server's own
# idea of where the character is, and that is all it does.
#
# A destination we invent is wrong in one of two ways and this project shipped
# both, alternately, over five attempts. Past a wall: the client walks through
# it, since a granted destination is not re-collided. At or behind the player:
# it walks backwards, because against a wall clip(pos, pos + heading) returns
# approximately pos. There is no safe value in between, only a narrower band of
# wrongness -- a guard that refuses short legs merely swaps a warp for a click
# that does nothing.
#
# The way out was not a better number. Keyboard movement should never have named
# a point at all (see GAME_SMSG_AGENT_MOVE_DIRECTION), and a click should be
# granted exactly as the player made it.
try:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mapdata"))
    from pathmap import PathingMap                            # noqa: E402
except Exception as _exc:                                     # noqa: BLE001
    PathingMap = None
    _PATHMAP_IMPORT_ERROR = _exc

# GmAgent.h. model_id is not a free-form number: the top nibble is a class tag,
# so a player agent is 0x30000000 | player number. player_team_token is a literal
# player_team_token was 0xBAADF00D here, copied from OpenTyria (GameSrv.c:1233)
# on the reasoning that an eye-catching constant was deliberate and should not be
# tidied away. It was deliberate -- it is a debug fill, and upstream is the only
# lineage that sends it. Three others send 0x706C6179, ASCII 'play'
# (studies/character/FINDINGS.md). One witness against three, and the three agree
# on a value that reads as meaningful rather than as a placeholder.
#
# Changed at BOTH send sites at once, deliberately: every lineage keeps the two
# equal, and a token that means "this team" is exactly the kind of thing that
# would fail confusingly if the client saw two different values for it.
# UNVERIFIED against our own client -- see the probe queue.
# Non-player agents. Shapes agree with the client's own message-format tables
# (studies/msgtable); what each field MEANS is in studies/enemy/PLAN.md.
GAME_SMSG_NPC_UPDATE_PROPERTIES = 0x0056
GAME_SMSG_MONSTER_COMPOSITE = 0x0057
GAME_SMSG_AGENT_PROPERTY_UPDATE_INT = 0x009F
GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET = 0x00A3
# The int-with-target variant. Same field shape as 0x00A3 (prop, target, cause,
# value) but the value is a plain int rather than IEEE bits. GWCA calls this
# family GenericValueTarget. INFERRED from the shape match; not yet observed.
GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET = 0x00A0
GAME_SMSG_AGENT_UPDATE_STATUS = 0x00F1
# The create-time sibling of 0x00F1, and D2 in the divergence register: 472 messages
# in the live capture, the highest count of anything ArenaNet sends that we never did.
# OBSERVED as [agent_id, dword] carrying the effect bitfield an agent is born with --
# 0x1000 on 151 of 151 Plague Worm creates and 0 on the ordinary ones in the same tape.
GAME_SMSG_AGENT_INITIAL_STATUS = 0x00F0
# Deliberately NOT given a meaningful name. It carries [agent_id, byte] and the whole
# corpus holds two values: 9, on every one of 140 worm creates, and 8, exactly once --
# on the Wolf at the instant it died, alongside EFFECT_DEAD. Two values with one of them
# seen a single time is a shape, not a semantic, and this project's rule is to refuse
# the guess. Note also that GAME_CMSG 0x0026 is ATTACK: 0x26 is the one value ArenaNet
# sends on BOTH channels, and they are different messages. Do not reuse either name.
GAME_SMSG_AGENT_UPDATE_FLAGS = 0x0026
BURROW_TAIL_0026_VALUE = 9        # what every observed worm create carried

GAME_SMSG_AGENT_UPDATE_ATTRIBUTE_POINTS = 0x0037
GAME_SMSG_AGENT_UPDATE_ATTRIBUTES = 0x003A

# GmAttributes.h: Attribute_Count. UPSTREAM-ONLY -- the comment is accurate about
# where 42 comes from, and that source stands alone. The claim this comment used
# to make, that the array's LENGTH is what tells the client how many attribute
# slots exist, is supported by NO source; it was our inference stated as fact.
# Whether a 42-zero array is even well-formed is open: one lineage reads this as
# triplets, and another never sends this message at all.
ATTRIBUTE_COUNT = 42
# UPSTREAM, and an uncited literal at that (GmPlayer.c:125). Two other lineages
# send 0/0 here, and whether the two bytes mean used/max or max/used is contested.
ATTRIBUTE_POINTS = 50

# ---------------------------------------------------------------- skills ----
# The server owns WHICH and WHEN; the client owns WHAT. A skill's name, icon,
# energy cost, cast time and recharge all live in a 164-byte row compiled into
# Gw.exe and indexed by the bare id we send here -- nothing about any of them
# crosses the wire. studies/skills/FINDINGS.md is the long version;
# studies/datwrite/FINDINGS.md located that table in OUR binary (.rdata file
# offset 0x00587ED0, 3,443 rows) and the ids below were read out of it.
#
# Shapes confirmed against schema/messages.json, which matches what the study
# describes: 218 is {agent_id, array32[8] skills, array32[8] pvp_masks, byte},
# 79 declared and 75 on the wire at 8/8 because the packer writes array counts
# as u16. 29 and 219 are both {array32[128]}.
#
# CAVEAT, and it is the one most likely to bite: messages.json carries
# "validated_against_build": null. These three opcode NUMBERS have never been
# checked against our own client, and there is a dated renumbering in this range
# in the wider corpus. If the bar stays empty, doubt the numbers before the shape.
GAME_SMSG_PVP_UPDATE_UNLOCKED_SKILLS = 0x001D   # 29
GAME_SMSG_SKILLBAR_UPDATE = 0x00DA              # 218
GAME_SMSG_UPDATE_UNLOCKED_SKILLS = 0x00DB       # 219

SKILLBAR_SLOTS = 8
# 128 dwords = 4,096 bits, comfortably covering the 0..3442 id space this build
# actually has. Blanket-unlocking everything is deliberate: whether the client
# REFUSES to draw a bar skill that is not unlocked is NOT FOUND in every source
# we have, so we remove the variable rather than guess at it. The Go server does
# the same thing.
UNLOCK_WORDS = 128
UNLOCK_ALL_WORD = 0xFFFFFFFF
# Bit n of word n/32 means skill n is unlocked. UPSTREAM describes the layout;
# OpenTyria's own bit helpers are too broken to copy (its set_bit assigns instead
# of OR-ing, destroying 31 bits at a time), so this is written from the
# description rather than from its code.
# The message carries 4096 bits and build 38797's skill table holds 3443 rows,
# so 653 of those bits name skills that do not exist. Setting them CRASHES the
# client -- MEASURED, twice:
#
#     Assertion: *skill
#     P:\Code\Gw\Char\Cli\ChCliSkill.cpp(1022)
#
# The Skills and Attributes panel walks the unlocked ids and dereferences each
# one, so a bit past the end of the table is a null deref. The crash was first
# blamed on a corrupt texture we had planted in the same session; it reproduced
# with a clean archive and a stock binary, and disappeared the moment the bitmap
# was clamped. "all" therefore means all REAL skills, not all bits.
#
# MEASURED against build 38797. A different build has a different row count, and
# this number is not read from the binary -- if the client starts asserting in
# ChCliSkill.cpp again, re-derive it with repoint_skill.py --show.
SKILL_TABLE_ROWS = 3443


def unlock_all_words():
    """Every bit up to SKILL_TABLE_ROWS, and not one past it."""
    words = [0] * UNLOCK_WORDS
    for sid in range(SKILL_TABLE_ROWS):
        words[sid // 32] |= 1 << (sid % 32)
    return words


UNLOCKED = unlock_all_words()
UNLOCK_LABEL = "all"


def build_unlock_bitmap(spec):
    """--unlocks: 'all', 'none', 'bar', or an explicit comma-separated id list."""
    if spec == "all":
        return unlock_all_words(), f"all ({SKILL_TABLE_ROWS} real skills)"
    words = [0] * UNLOCK_WORDS
    if spec == "none":
        return words, "none"
    ids = SKILLBAR if spec == "bar" else [int(s, 0) for s in spec.split(",")
                                          if s.strip() != ""]
    for sid in ids:
        if sid <= 0:
            continue
        w, b = divmod(sid, 32)
        if w >= UNLOCK_WORDS:
            raise SystemExit(f"skill id {sid} needs word {w}, past the "
                             f"{UNLOCK_WORDS}-word message")
        if sid >= SKILL_TABLE_ROWS:
            raise SystemExit(
                f"skill id {sid} is past the end of this build's skill table "
                f"({SKILL_TABLE_ROWS} rows). Unlocking it asserts in the "
                f"client's ChCliSkill.cpp the moment the Skills panel opens.")
        words[w] |= 1 << b
    return words, ",".join(str(i) for i in ids)

# Eight real Warrior skills (profession byte 1 at row+0x28), read from this
# build's own table, each with both icon file ids present and name/description
# string ids consecutive. Our test character is a Warrior, so a Warrior bar is
# the case least likely to be refused for a reason we would then misattribute.
TEST_SKILLBAR = [316, 317, 318, 319, 320, 321, 322, 323]
# What actually goes out. Rebindable from --skills so the ids can be changed
# between launches without editing this file -- which matters because the whole
# point of the exercise is varying them and watching what the client draws.
SKILLBAR = list(TEST_SKILLBAR)
# Upstream declares 8 pvp_masks and never writes them, so eight zeros go out
# from its memset. We send the same thing, and what it is for is NOT FOUND.
SKILLBAR_PVP_MASKS = [0] * SKILLBAR_SLOTS
# Trailing byte. Upstream sets it to 1 with no citation anywhere.
SKILLBAR_TRAILER = 1

CHAR_CLASS_PLAYER_BASE = 0x30000000
AGENT_TYPE_LIVING = 1
PLAYER_TEAM_TOKEN = 0x706C6179   # 'play'
# The in-instance player number, which is what PLAYER_CREATE and model_id use --
# NOT the 32-bit player_id the client puts in its version frame. Those are
# different namespaces and conflating them is an easy way to build an agent
# nobody can address.
PLAYER_NUMBER = 1

# OpenTyria's ManifestPhase enum (GmMap.h) is ZERO based. Sending the literals
# 1 and 2 as "phase 1, phase 2" put Done in a PHASE slot, and the client died on
#   Assertion: Invalid manifest phase
#   P:\Code\Gw\Mission\Cli\MsCliMan.cpp(472)
# with edi=00000002 -- our own second argument, named in the register dump.
MANIFEST_PHASE1 = 0
MANIFEST_PHASE2 = 1
MANIFEST_DONE = 2
# The sentinel OpenTyria passes as map_id on the first DONE: one past the last
# real map (876), meaning "no map" rather than any actual destination.
MAP_ID_COUNT = 877

# Where the world's facts live: content/maps.toml, loaded through toolkit/content.py.
#
# This was a 60-line literal with its evidence in comments no tool could read. Every id,
# every spawn point and every reason is now a row carrying its own provenance -- which
# upstream it came from, what we checked it against, and what is still unknown. The
# loader refuses a row citing an unlicensed upstream that does not say what we verified.
#
# `map_file_id` is what the client opens out of Gw.dat. Sending 0 kills it on
#   Assertion: fileId   P:\Code\Base\Rtl\File.cpp(367)
#
# The shape is deliberately unchanged -- id -> (file_id, (x, y), plane, explorable) --
# so this commit moves data and touches no consumer. Run
# `python toolkit/content.py --explain 148` for a row's full reasoning.
MAP_STATIC_CONFIG = agents.WORLD.map_static_config()
# The fallback for maps we have no entry for. It used to catch map 148 as well,
# which meant the character stood in Kamadan's geometry under Ascalon City's
# name -- knowingly inconsistent, and accepted at the time because Ascalon's
# file id could not be recovered. It can now, so 148 is a real entry above and
# this is back to being what it says it is: a substitute for the unknown.
FALLBACK_MAP_ID = 449


def map_explorable(map_id):
    """Is this map a field rather than a town?

    Guild Wars forbids attacking in a town, so this decides whether combat is
    possible at all. CLIENT-DATA: AreaInfo's type field is 2 for the Pre-Searing
    explorables (145, 146, 147) and 10 for its outposts (148, 164), which is the
    client's own answer and agrees exactly with gw-preservation's Explorable
    column. Maps we have not configured default to False, because a town is the
    safer wrong answer -- it fails to allow combat rather than allowing it
    somewhere the client will not.
    """
    cfg = MAP_STATIC_CONFIG.get(map_id)
    return bool(cfg[3]) if cfg and len(cfg) > 3 else False

# Parsed navmeshes, keyed by map_file_id. Loading one costs about a second,
# nearly all of it decompressing the map out of the archive, so it is worth
# keeping -- but only worth doing once, at instance load, off the wire path.
_PATHMAPS = {}
_PATHMAP_LOCK = threading.Lock()


def load_pathmap(map_file_id):
    """The walkable geometry for a map, or None if we cannot get it.

    None is a normal outcome, not an error: no archive on this machine, or a map
    whose file id we do not have. The caller falls back to no collision.
    """
    if PathingMap is None:
        return None
    with _PATHMAP_LOCK:
        if map_file_id in _PATHMAPS:
            return _PATHMAPS[map_file_id]
        try:
            pm = PathingMap.load(map_file_id)
            print(f"[map] navmesh 0x{map_file_id:X}: {len(pm.planes)} planes, "
                  f"{len(pm.trapezoids)} trapezoids")
        except Exception as exc:                              # noqa: BLE001
            print(f"[map] no navmesh for 0x{map_file_id:X}: {exc}")
            print("[map] collision is OFF; the character can walk through walls")
            pm = None
        _PATHMAPS[map_file_id] = pm
        return pm


# How far the client's reported position may be from ours before we stop
# believing it. Reports arrive every ~250-340 ms and run speed is 288 u/s, so a
# legitimate gap is ~100 units; 900 is deliberately loose because the cost of
# refusing a real report is the drift this exists to prevent, while the cost of
# accepting a wrong one is one bad leg that the next report corrects. It is a
# sanity bound against a garbage decode, not an anti-cheat -- this server is
# loopback only and the client is the one telling the truth here.
CLIENT_POSITION_TRUST_RADIUS = 900.0


def _adopt_client_position(state, reported):
    """Should we take the client's word for where it is standing?"""
    px, py = state["pos"]
    jump = math.hypot(reported[0] - px, reported[1] - py)
    if jump <= CLIENT_POSITION_TRUST_RADIUS:
        return True
    print(f"[map] ignoring a {jump:.0f}u jump in the client's reported "
          f"position -- ours ({px:.0f}, {py:.0f}), theirs "
          f"({reported[0]:.0f}, {reported[1]:.0f})", flush=True)
    return False


def clip_to_walkable(state, dest):
    """Trim a destination to where the navmesh says a character can get.

    Returns (destination, blocked). `blocked` means the leg was cut short.

    Standing OUTSIDE the navmesh disables the check rather than freezing the
    character in place. That case is not hypothetical -- our spawn points come
    from upstream's static config and only one of the six has ever been checked
    against real geometry, so a map we know less about can easily drop a player
    somewhere the mesh does not cover. Refusing every move from there would look
    like a hang, and a hang is a much worse failure than the wall-clipping this
    replaces.
    """
    pm = state.get("pathmap")
    dest = (float(dest[0]), float(dest[1]))
    if pm is None:
        return dest, False
    px, py = state["pos"]
    if not pm.walkable(px, py):
        if not state.get("off_mesh_warned"):
            state["off_mesh_warned"] = True
            print(f"[map] standing at ({px:.0f}, {py:.0f}), which the navmesh "
                  f"does not cover -- collision suspended for this character")
        return dest, False
    state["off_mesh_warned"] = False
    stopped = pm.clip(px, py, dest[0], dest[1], step=COLLISION_STEP)
    return stopped, stopped != dest

# The reply to CHAR_CREATION_REQUEST_ARMORS. The name is a red herring: nothing is
# being created and no armour is sent. OpenTyria (GameSrv.c:1557) answers it with
# account-wide unlock state, which is what the client is really asking for.
GAME_SMSG_ACCOUNT_FEATURE = 0x000F
GAME_SMSG_PVP_UPDATE_UNLOCKED_HEROES = 0x0018
GAME_SMSG_PVP_ITEM_STREAM_END = 0x001B
GAME_SMSG_PVP_UPDATE_UNLOCKED_SKILLS = 0x001D

# OpenTyria's GameSrv_SendAccountFeatures table, verbatim.
ACCOUNT_FEATURES = ((1, 10, 0), (99, 3, 0), (100, 5, 0), (101, 5, 5),
                    (102, 2, 2), (111, 1, 0), (124, 1, 0), (125, 1, 0),
                    (131, 1, 0))

# What the client asks for, in the order it asks. OpenTyria answers REQUEST_ITEMS
# with a dozen messages (inventory, weapon sets, gold, factions, quests...). We
# send only the ones that drive the state machine, so that a stall names a missing
# message rather than hiding inside a burst of guesses.
GAME_CMSG_INSTANCE_LOAD_REQUEST_SPAWN = 0x0088
GAME_CMSG_INSTANCE_LOAD_REQUEST_PLAYERS = 0x0090
GAME_CMSG_INSTANCE_LOAD_REQUEST_ITEMS = 0x0091
# Sent by this build during an ordinary map load, not during character creation.
# The Py4GW argument this comment used to make was CIRCULAR: Py4GW's table is
# OpenTyria's verbatim, so "a second catalog agrees" was one witness twice, and
# Py4GW ships the off-by-one table too. The real support is GWLP-R and
# gw-preservation agreeing on internal order, plus the client dumps -- and now
# the client's own tables, which measure delta = 0 against our numbering.
GAME_CMSG_CHAR_CREATION_REQUEST_ARMORS = 0x008A

# Both of these exist on this build and they are NOT the same order:
#   0x003D  position + heading  -> turn to face. Handled entirely client-side;
#           answering it is unnecessary, and answering it with a move is worse.
#   0x003E  destination + plane -> actually go there. Upstream's value, despite
#           PLAN.md recording a 0x003C -> 0x003E drift across builds.
# Keying movement on 0x003D was the reason the character turned to face every
# input and never took a step: we were answering the turn and ignoring the move.
# THE REAL ATTACK ORDER, and as of 2026-08-11 the client SENDS IT TO US.
# OBSERVED (studies/enemy/PLAN.md 10.7, the `worldaction` labelled run): four of
# these at our own Hatcher across three separate steps -- one on a single
# left-click, two on a double-click -- and ZERO 0x0033 in the same run. Payload
# is [agent_id, dword]; the target was agent 10, ours.
#
# For a year this opcode was defined by its absence and 0x0033 was pressed into
# service as "the only attack intent we have ever seen the client express". That
# sentence was true when written and is now false, and what changed was not a
# code change: 0x00514840 is a six-arm switch, 0x0026 is arm 0 and 0x0033 is arm
# 1, and given a correctly-stated agent the client picks arm 0 by itself.
GAME_CMSG_ATTACK_AGENT = 0x0026

# What the client sends when the player clicks an agent meaning to do something
# to it. MEASURED: it arrives at a hostile agent 11 times in one session and 32
# in another, in a TOWN, while this server answered none of them
# (studies/enemy/PLAN.md 7.3a).
#
# Driving combat from this message rather than from 0x0026 is deliberate, and it
# is what makes a fight possible in an outpost at all: Guild Wars forbids
# attacking in a town, so the client will not issue an attack there, but it will
# still say "I clicked that". What we do about it is our decision, not the
# client's.
GAME_CMSG_INTERACT_PLAYER = 0x0033

# The client asks to use a skill and then WAITS to be told it worked. Pressing a
# skill plays the bar animation and never casts, which is the same shape as every
# other bug this project has had: the client asks, we say nothing.
#
# Payload, from our schema and the one capture we have: dword skill_id, dword
# copy, agent_id target, byte. Both observed sends carried a target of 0 because
# nothing was selected at the time.
GAME_CMSG_USE_SKILL = 0x0046

# THE OTHER HALF, and without it the entire physical side of the game is unhandled.
# OBSERVED 2026-08-11 (studies/cmsg/FINDINGS.md C14): a whole narrated live session
# of a Ranger casting Power Shot sent ZERO 0x0046. Attack skills leave on 0x0027
# instead, and the server answers both with the same GAME_SMSG 0x00E3 -- which is
# what makes them two halves of one thing rather than unrelated messages.
#
#   Necromancer session:  4x 0x0046, 0x 0x0027    skills 105, 153 -- type_code 5
#   Ranger session:       0x 0x0046, 3x 0x0027    skill 394       -- type_code 14
#
# The client's own s_skill table types 394 as profession 2 (Ranger), 10 energy,
# 3 s recharge -- Power Shot -- and 311 of its 3443 rows carry type_code 14.
#
# THE DISCRIMINATOR IS INFERRED, not proven: three distinct skills over two
# sessions is thin, and what is actually established is that the two casters used
# different opcodes and their skills differ by type_code. "type_code 14 goes on
# 0x0027" is the reading that fits; a rival that fits equally well on this evidence
# is "the PROFESSION decides", and only a session mixing skill types on one
# character separates them. Nothing below depends on which is right.
#
# FIELD MEANINGS ARE POSITIONAL AND MATCH 0x0046, which the catalog's TYPES hide:
# 0x0046 is [dword, dword, agent_id, byte] and 0x0027 is [agent_id, dword, dword,
# byte], but both are 15 bytes and the VALUES line up slot for slot -- field 1 is
# the skill (394 constant across all three sends), field 3 the target (276/278,
# both of which 0x0026 ATTACK also targeted in the same fight). agent_id and dword
# are the same four bytes on the wire; the marshalling type is not the meaning.
# This is the ROTATE_PLAYER trap and it is the third time it has come up.
GAME_CMSG_ATTACK_SKILL = 0x0027

# The reply, and its field meanings are the CLIENT'S OWN WORDS. 0x00823090 builds
# a lookup key from the two payload fields and, when it misses, logs
#
#     'Pending skill %u copy %d not found'
#
# with the word field as %u and the dword as %d. So the message is
# (agent_id, skill_id, copy), the client is matching it against a PENDING entry
# it created when it sent USE_SKILL, and both fields have to be echoed back
# unchanged for the match to land.
#
# 0x00E3 rather than 0x00E4, and that is measured too: 0x00E4's handler compares
# the agent against your own and RETURNS EARLY when they match, so it is how you
# see other people cast. 0x00E3 has no such check.
GAME_SMSG_SKILL_ACTIVATED = 0x00E3

GAME_CMSG_TURN_TO_DIRECTION = 0x003D
GAME_CMSG_MOVE_TO_COORD = 0x003E
GAME_CMSG_LAST_POS_BEFORE_MOVE_CANCELED = 0x0047

GAME_SMSG_AGENT_MOVE_TO_POINT = 0x0029
GAME_SMSG_AGENT_UPDATE_POSITION = 0x002C
# Keyboard movement is answered with a DIRECTION, not a destination.
#
# This is the message the whole rubber-banding fight was about not having.
# GWLP-R -- a working server emulator, and a different lineage from OpenTyria --
# answers a keyboard move with AgentMoveDirection and reserves MoveToPoint for
# click-to-move. Sending an absolute destination for WASD has two failure modes
# and we hit both: a point past a wall makes the client walk through it, because
# a granted destination is not re-collided, and a point at or behind the player
# makes it walk backwards. A direction has neither. The client keeps applying
# its own collision the entire time it is moving that way.
#
# The opcode is identified rather than guessed. GWLP-R's numbering runs 11 below
# ours, consistently across five messages whose field shapes all match this
# repository's schema -- and that schema was recovered from build 38797's own
# tables, so the shapes are confirmed independently of GWLP-R:
#
#   P026 MoveDirection -> 0x0025  dword, vec2, byte    agent, direction, type
#   P028 MovementSpeed -> 0x0027  dword, float         agent, speed
#   P030 MoveToPoint   -> 0x0029  dword, vec2, 2x word agent, point, planes
#   P032 SpeedModifier -> 0x002B  dword, float, byte   agent, modifier, type
#   P035 AgentRotate   -> 0x002E  dword, dword, dword  agent, cos, sin
#
# THREE OF THOSE GLOSSES ARE NOW REFUTED from the client's own binary and the
# live corpus (2026-08-10, studies/smsg/FINDINGS.md):
#   0x002B is NOT a "SpeedModifier": the client asserts the float into
#     [AGENT_MIN_MOVE_SPEED, AGENT_MAX_MOVE_SPEED] = [0.01, 1.0] and 163/163 wire
#     samples obey it, so a movement buff has nowhere to ride. Its byte is
#     `facing` (AgAgent.cpp:2368 "!(facing & ~AGENT_FACING_MASK)"), not a "type".
#   0x002E is NOT "cos, sin": sin^2+cos^2 over the corpus ranges 1.23..4.87 and
#     is never 1. Field 2 is an absolute angle (55/55 finite values inside +/-pi,
#     the only non-finite ones being the two +/-inf sentinels) and field 3 is a
#     turn rate in rad/s. This gloss is why 0x002E went unsent for weeks.
#   0x0029's "planes" is not from the binary and remains UNVERIFIED.
# The typing stays dword for 0x002E's two fields -- the VALUES are floats, the
# MARSHALLING is not, exactly as for GAME_CMSG 0x0040 ROTATE_PLAYER.
#
# What is borrowed is the SEMANTICS -- that keyboard movement belongs on this
# message. That rests on GWLP-R alone, and is UNVERIFIED against our client
# until a playtest says the walking looks right.
GAME_SMSG_AGENT_MOVE_DIRECTION = 0x0025

# The four this server could not send until 2026-08-11, all named on 2026-08-10
# from the client's own asserts joined to two live captures. Builders and the
# bounds the client asserts on itself are in agents.py; studies/smsg/FINDINGS.md
# carries the evidence for each.
#
# 0x002B is the one to understand first. It is a NORMALISED movement rate --
# 1.0 == 288 units/s -- and it drives the client's walk-cycle playback rate.
#
# DO NOT repeat the attribution this comment originally carried. It said this
# explained a "smooth movement, janky animation" report from 2026-08-11, and
# that was wrong twice over: the report came from a TAPE REPLAY, and in tape
# mode this server sends nothing of its own -- the tape is the whole channel,
# and ArenaNet's own tapes carry 163 of these. The client was receiving movement
# rates throughout. A second hypothesis (Windows sleep granularity smearing the
# replay) was also measured and refuted: play_tape schedules against an absolute
# t0 so drift cannot accumulate, and sleep overshoot on this machine is
# 0.1-0.7 ms. What 0x002B is actually worth is stated above and is about OUR
# server's own sessions, where it is now sent and where the walk cycle was
# confirmed by eye on 2026-08-11.
GAME_SMSG_AGENT_UPDATE_SPEED = 0x002B
# Absolute facing angle in radians + a turn rate in rad/s, BOTH marshalled u32.
# Upstream called them rotation_cos/rotation_sin; sin^2+cos^2 over the live
# corpus ranges 1.23-4.87 and is never 1, so that reading is refuted.
GAME_SMSG_AGENT_UPDATE_ROTATION = 0x002E
# ArenaNet sends this after EVERY 0x006E, 366 of 366 across both captures. Zero
# makes the client skip a guild lookup on an id we never populated.
GAME_SMSG_AGENT_SET_TABARD_VISIBLE = 0x0048
# The profession pair. The client's own invariant is primary != secondary, and
# across 387 live samples the primary is 1..6 and NEVER 0.
GAME_SMSG_AGENT_SET_PROFESSION = 0x00A6

GAME_SRV_HOST = "127.0.0.1"
# How GAME_SERVER_INFO fills its 24-byte host field. "sockaddr" is what both
# reference implementations do; "string" is the competing reading, kept only
# because the switch already exists. OBSERVED 2026-08-06 (handshake PLAN §10):
# under the sockaddr encoding the client dials the HOST we put here, at
# hardcoded port 6112 -- the PORT field below goes out on the wire but the
# client never dials it.
HOST_FIELD_ENCODING = "sockaddr"
GAME_SRV_PORT = 6113

PLAYER_STATUS = {0: "Offline", 1: "Online", 2: "DND", 3: "Away", 4: "Blank"}

GM_ERROR_NETWORK = 2
GM_ERROR_AUTH = 11

# One test character, defined once. The same uuid appears in CHARACTER_INFO and in
# ACCOUNT_INFO's "current character" slot; if those two ever drift apart the client
# silently fails to pre-highlight a roster entry, with no error to notice.
TEST_CHAR_UUID = bytes.fromhex("11111111111111111111111111111111")
TEST_CHAR_NAME = "Test Warrior"
TEST_CHAR_SETTINGS = bytes.fromhex(
    "0600"              # version 6
    "9400"              # last_outpost 148, Ascalon City (pre-Searing)  [medium]
    "00000000"          # last_time_played
    "00001000"          # appearance: profession Warrior at bit 20
    + "00" * 16 +       # last_guild_hall_id: none
    "11400000"          # campaign Prophecies, level 1, helm shown
    "00"                # number_of_pieces: no equipment  [medium]
    "00000000")         # trailing dword, believed unread  [medium]
assert len(TEST_CHAR_SETTINGS) == 37, len(TEST_CHAR_SETTINGS)

AUTH_CMSG_NAMES = {
    0x0000: "HEARTBEAT", 0x0001: "SEND_COMPUTER_INFO", 0x0002: "SEND_COMPUTER_HASH",
    0x0023: "UNKNOWN_8023",
    0x0003: "ACCOUNT_CREATE", 0x0004: "ACCOUNT_LOGIN", 0x0007: "DELETE_CHARACTER",
    0x0009: "UPDATE_CHARACTER_SETTINGS", 0x000A: "CHANGE_PLAY_CHARACTER",
    0x000D: "DISCONNECT", 0x000E: "SET_PLAYER_STATUS", 0x001A: "FRIEND_ADD",
    0x001C: "ADD_ACCESS_KEY", 0x0020: "SETTING_UPDATE_CONTENT",
    0x0021: "SETTING_UPDATE_SIZE", 0x0025: "REQUEST_GUILD_HALL",
    0x0026: "ACCEPT_EULA", 0x0029: "REQUEST_GAME_INSTANCE",
    0x0035: "ASK_SERVER_RESPONSE", 0x0038: "PORTAL_ACCOUNT_LOGIN",
}

codec = Codec()

VAULT_DEFAULT = vault_path("captures", "authsrv")


# Set from --probe. Read by the spawn path; None means the server behaves
# exactly as it does in a normal session.
PROBE_NAME = None

# Set from --tape. When armed, the GAME channel's whole load sequence is replaced
# by a recording of ArenaNet's -- see play_tape. None means the ordinary map load.
TAPE_EVENTS = None
TAPE_INFO = None
TAPE_SPEED = 1.0

# Set from --labelrun to the chosen script (a list of labelrun.Step), None otherwise.
# Walks the operator through a numbered script, marking each
# step into the capture so a c2s message can be attributed to a named human action.
# See labelrun.py: 194 GAME_CMSG opcodes have layouts in the schema and names in
# neither it nor here, and this is how that gets fixed.
LABEL_RUN = None

# Set from --click-sweep. Cycles the two 16-bit fields of MOVE_TO_POINT through
# every plausible assignment, one per click, so the CLIENT decides which is
# right instead of us arguing from two sources that contradict each other.
#
# We have spent this whole investigation inferring these two fields. OpenTyria
# says (destination, current); GWLP-R says (current, next); both orders were
# shipped and neither fixed the player walking through walls and falling through
# staircases. The setup for a real experiment is finally clean: keyboard
# movement works, so the transport and the client are known good, and clicking
# is one message with exactly two unknown fields.
#
# Variants are ordered so the two we have already tried come first, which makes
# the run its own control: if 1 and 2 misbehave exactly as they did in normal
# play, the harness is measuring the right thing.
# Set from --explorable. Tells the client this instance is a field rather than a
# town. See the INSTANCE_LOAD_INFO send site for why it is worth a flag.
EXPLORABLE = False

# Send the client somewhere other than the map it asked for. The character
# record names 148, so without this every session lands in Ascalon City. A
# server overriding the destination is not a hack -- it is what map travel is.
MAP_OVERRIDE = None

# The one thing standing in the world besides the player, and where it stands:
# content/world.toml's `spawn.test_enemy`. Its row is labelled `invented`, because
# nothing has ever observed a body 300 units east of an arrival point in any real
# Guild Wars map -- it exists so a hostile agent can be hit, killed and revived on
# demand. R4c's real spawns are server-only data nobody has captured yet.
_ENEMY = agents.WORLD.get("spawn", "test_enemy")

# Whether the world contains anything besides the player. On by default: an
# enemy standing in the map is the point of the exercise, and every packet it
# takes is proven (studies/enemy/PLAN.md). --no-enemy gives back an empty world
# for probes that want one.
SPAWN_ENEMY = _ENEMY["enabled"]

CLICK_SWEEP = False
CLICK_SWEEP_VARIANTS = (
    ("dest,cur   (OpenTyria order, shipped)", lambda c, d: (d, c)),
    ("cur,dest   (GWLP-R order, shipped)",    lambda c, d: (c, d)),
    ("0,0        (both zero)",                lambda c, d: (0, 0)),
    ("cur,0",                                 lambda c, d: (c, 0)),
    ("0,cur",                                 lambda c, d: (0, c)),
    ("dest,dest",                             lambda c, d: (d, d)),
    ("cur,cur",                               lambda c, d: (c, c)),
)


# The first thing in this world that is not the player.
#
# Ids are deliberately clear of the probes, which use agents 2..7 and definition
# 2, so a --probe session and the standing enemy cannot collide. That collision
# is not cosmetic: an agent id reused for a second body would leave the client
# with one agent's state under another's name.
ENEMY_AGENT_ID = _ENEMY["agent_id"]
ENEMY_DEFINITION = _ENEMY["definition"]
ENEMY_MAX_HEALTH = _ENEMY["max_health"]
ENEMY_OFFSET = (_ENEMY["offset_x"], _ENEMY["offset_y"])
# A PLACEHOLDER, and it has to be non-zero rather than right. WIKI (GWW,
# "Attack speed") says a creature that wields no weapon takes its rate from its
# creature type, and we do not know a Hatcher's -- it is a collector that has
# never swung at anything. This is the axe/sword/dagger figure because that is
# a real number from the table rather than one we made up, and the only thing
# the client demands of it is that it is not 0. A capture of a real fight would
# replace it; nothing here is a claim about what a Hatcher does in retail.
ENEMY_ATTACK_SPEED = agents.ATTACK_SPEED["axe"]
# Burrowing, off unless the content row turns it on. A Hatcher standing in for a Plague
# Worm exercises the CYCLE without transcribing an ArenaNet creature into tracked
# content -- see the row's own note. The two durations here are INVENTED and the row
# says so; the two that are measured are protocol timing and live beside the opcodes.
ENEMY_BURROWS = bool(_ENEMY.get("burrow", False))
ENEMY_BURROW_OUT = float(_ENEMY.get("burrow_out_seconds", 5.0))
ENEMY_BURROW_HIDDEN = float(_ENEMY.get("burrow_hidden_seconds", 4.0))


# ---- the combat loop -----------------------------------------------------
#
# EVERY PACKET BELOW IS PROVEN; EVERY NUMBER BELOW IS INVENTED. That split is
# the whole point of this block, so keep it visible. The damage message, the
# death bit and the two-step revive were each measured against our own client
# and are cited where they are sent. How hard a click hits, how often it may
# hit, and how long a body stays down are OURS -- they are not claims about
# retail Guild Wars, and nothing here should ever be cited as one.
#
# Retail numbers exist and we do not have them: the wiki documents attack rates
# and weapon damage, and a captured fight would give the real thing. Until then
# these are placeholders chosen to make a fight legible to a person watching.
HIT_FRACTION = 0.15        # of maximum health, so ~7 clicks to kill
REVIVE_AFTER = 8.0         # seconds face-down before it gets back up
# HIT_COOLDOWN was here and is gone: it dated from when a click dealt a hit
# directly, and nothing has read it since the swing moved onto ATTACK_INTERVAL.
# A second, unused rate constant sitting beside the real one is exactly the
# thing someone tunes for an hour before noticing it is not wired to anything.

# SERVER-DRIVEN ATTACKING, and it is a workaround rather than the mechanism.
#
# READ THE DATE ON EVERYTHING BELOW. As of 2026-08-11 THE CLIENT SENDS US
# ATTACK_AGENT (0x0026) -- four of them at our own Hatcher in one labelled run,
# one on a plain left-click, and zero 0x0033 in the same run
# (studies/enemy/PLAN.md 10.7). The block described in the rest of this comment
# is GONE, and it died to work already landed rather than to any fix aimed at
# it. What survives is the workaround itself: begin_attack and ATTACK_INTERVAL
# still drive the swinging from our tick, and that is still not the mechanism.
# The history is kept because three sections of a study doc were spent on it.
#
# WHAT WAS TRUE UNTIL 2026-08-11, and no longer is:
# The client had never once sent ATTACK_AGENT to us -- not on click, not on
# space, armed or unarmed, in an outpost or an explorable, with the target red
# and damageable. It answered a click on our enemy with INTERACT_PLAYER (0x0033)
# and nothing else, 206 times to 0.
#
# The opcode is registered in this build's own send table with two fields, so
# the capability was never in doubt; what stopped the client choosing it was
# NOT FOUND after testing the weapon (item and body), energy and health pools,
# the explorable flag, the hostile team token and 0x002F -- and the answer, per
# 10.6/10.7, is that 0x0033 was never a refusal at all. It is arm 1 of a
# six-arm world-action switch and 0x0026 is arm 0. The client picks the arm.
#
# AND IT STOPS 0x0027 TOO, which is the same refusal reaching a second opcode.
# OBSERVED 2026-08-11: with the attack-skill arm newly in place, the harness
# clicked our enemy (TARGET_SELECT went out, so the target WAS taken) and pressed
# skill slots 5, 6 and 7 -- which our own bar fills with skills 320-323, all
# type_code 14 Warrior attack skills, the same class as the Ranger's Power Shot
# that revealed 0x0027. Not one message left the client.
#
# THE "VISIBLE REFUSAL" WAS A BUTTON. Section 10 was founded on a small icon at
# the end of the target's health bar, which I read as a prohibited marker and
# called proof that "the refusal is a decision, and decisions have code". It is
# the control that CLEARS THE SELECTED TARGET (SOURCED 2026-08-11, owner), it is
# on every target frame, and it never meant anything. The chain below was read
# correctly and answered a question nothing had asked. studies/enemy/PLAN.md
# section 10 has it; the
# two facts that change what to try next are:
#
#   1. The available-actions builder (GmCoreAction, 0x005144F0) switches on an
#      ALLEGIANCE ENUM and accepts only 1..6 -- which is exactly the
#      ALLEGIANCE_* enum agents.py already carries, and five readers compare the
#      byte against 3, ALLEGIANCE_ENEMY. The getter returns **7 on a lookup
#      miss**, and 7 fails the range check. So an agent that renders, has a
#      nameplate and can be TARGETED can still offer no attack action: visible
#      and attackable are two different registrations, off two different lists.
#
#   2. The allegiance byte (+0x1B5) has exactly TWO writers in the whole image
#      and both are constructors. **Nothing updates it afterwards.** That is why
#      0x002F was tested and did nothing, and it retires that whole line: there
#      is no post-construction setter to reach, so allegiance is decided when the
#      agent is CREATED and no later message can correct it.
#
# AND THE READ SAYS BOTH GATES PASS (agentprobe.py, 2026-08-11): our Hatcher
# carries +0x9C == 0xDB (a CHARACTER) and +0x1B5 == 3 (ALLEGIANCE_ENEMY), with
# the skip flag clear. So the client HAS resolved our agent to an enemy and runs
# the switch's enemy arm. That refutes the chain above as the blocker -- and it
# closes the whole family of attempts aimed at convincing the client our agent is
# hostile (the team token, 0x002F, section 6e): it already is, measured rather
# than assumed. The block is downstream of the action mask.
#
# WALK BACK ONE CLAIM OF MINE: the prohibited marker on the target's health bar
# is NOT known to mean "cannot attack". I read a small icon and asserted a
# meaning. The client considers this agent an attackable-class enemy, so the
# marker is something else -- range, line of sight, or another thing entirely.
#
# NOR IS IT OUR WEAPON, AND THAT ONE WAS MEASURED (studies/enemy/PLAN.md 10.3,
# refuted by 10.4). The chain read out of the binary was right about what the
# client CHECKS: GmCoreAction:997's classifier sends allegiance 3 (ENEMY) to an
# arm whose entire test is 0x005147F0, and that function never looks at the
# target -- it fetches OUR equipment slot 0 and returns BIT 25 of the item
# record's +0xC. It was wrong about the answer. itemprobe.py read a live client
# on 2026-08-11: slot 0 of the bag holds our hammer and its gate dword is
# 0x22201000, bit 25 SET. The gate PASSES, so 0x004E22D5 adopts the agent as a
# target rather than skipping it.
#
# ArenaNet sets the same bit -- every equipped weapon in both live captures has
# it, and the Ranger's bow carries 0x22201000, byte-identical to the hammer we
# send. test_smsgnames.py pins that against the corpus so it cannot rot.
#
# The lesson, now three for three (10.1, 10.2, 10.4): a decision tree read out of
# the disassembly tells you what the client TESTS and never what the answer is on
# our data. Derive the chain, then probe the values -- agentprobe.py for agents,
# itemprobe.py for items, both read-only, each one killing a hypothesis that had
# already survived a session of reasoning.
#
# Withdrawn with it: 10.3's claim that bit 25 explains the m_attackInterval
# assert at EQUIP_WEAPON below. That assert is still unexplained, and section 6p
# -- the field living on the view-layer AvChar rather than on the agent -- is now
# the only surviving lead.
#
# Ruled out on the way, so it is not re-tried: the allegiance FourCC. We send
# 'mons' where ArenaNet sends 'mon1', the only create field that differs from an
# agent the client DOES attack -- and neither token appears anywhere in the
# image, so the client cannot be recognising either.
#
# So a click now STARTS an attack instead of being one, and the server swings
# on a timer. That is closer to how Guild Wars actually works -- combat is
# server-authoritative and the client renders what it is told -- but the client
# initiating is still the real thing and this is not it. Do not read a working
# fight on screen as evidence that attacking is solved.
# Seconds between swings, and this one is NO LONGER OURS. It used to be 1.33
# with a comment admitting that was the axe/sword/dagger figure and a hammer is
# slower. It is now the hammer's real 1.75 -- WIKI (GWW, "Attack speed", whose
# table states outright that these are the exact values the game uses), and the
# client's own arithmetic agrees to four decimals across three weapon classes
# (agents.ATTACK_SPEED). It is deliberately the SAME constant we put on the
# wire in ATTACK_SPEED, because the rate the server swings at and the rate the
# client animates at are one number, and they were two.
ATTACK_INTERVAL = WEAPON_ATTACK_SPEED
ATTACK_RANGE = 1500.0      # units. Ours entirely; nothing measured it.


def begin_attack(send, state, target_id, conn_id):
    """A click on a hostile agent starts an attack that the tick keeps up.

    Previously this dealt one hit per click, which is where "press to deal
    damage" came from. Clicking an enemy in Guild Wars orders an attack; it does
    not BE one.
    """
    agent = state.get("agents", {}).get(target_id)
    if agent is None or agent["dead"]:
        # Clicking anything else -- scenery, a corpse -- stops the swing rather
        # than leaving the player hitting a thing that is no longer there.
        state["attacking"] = None
        return
    if state.get("attacking") != target_id:
        state["attacking"] = target_id
        # Swing immediately on the first click, then let the tick keep time.
        # Waiting a full interval makes the click feel ignored.
        agent["last_hit"] = 0.0
        print(f"[c{conn_id}] attacking agent {target_id} ({agent['name']})",
              flush=True)


def attack_tick(send, state, conn_id):
    """Keep swinging at whatever the player last clicked."""
    target_id = state.get("attacking")
    if not target_id:
        return
    agent = state.get("agents", {}).get(target_id)
    if agent is None or agent["dead"]:
        state["attacking"] = None
        return
    px, py = state.get("pos", (0.0, 0.0))
    ax, ay = agent["pos"]
    if math.hypot(ax - px, ay - py) > ATTACK_RANGE:
        # Out of range. Real Guild Wars would walk the player into range; we do
        # not move the player, so the swing simply stops and resumes when they
        # walk back. Keep the target so it picks up again without re-clicking.
        return
    hit_enemy(send, state, target_id, conn_id)


def hit_enemy(send, state, target_id, conn_id):
    """Land one swing on a hostile agent, if the swing timer allows it."""
    agent = state.get("agents", {}).get(target_id)
    if agent is None or agent["dead"]:
        return
    now = time.time()
    if now - agent.get("last_hit", 0.0) < ATTACK_INTERVAL:
        return
    agent["last_hit"] = now

    # A swing is two events, and sending only the second is why the first
    # attempt produced damage with no animation: 1 is melee_attack_FINISHED,
    # the end of a swing. 4 is attack_started.
    #
    # THE FIRST SLOT IS THE ATTACKER, and it used to hold the enemy here --
    # so every swing this server ordered was telling the client to animate the
    # ENEMY, not the player. OBSERVED, from a run that made the point without
    # anyone watching the screen: the only agent with an attack speed was the
    # player, the packet named the Hatcher in slot 1 and the player in slot 2,
    # and the client died on m_attackInterval. It could only assert on an agent
    # whose attack speed was zero, and the player's was 1.75 -- so the body
    # being animated was the one in slot 1.
    #
    # That CONTRADICTS GWCA's note on this id ("caster_id is victim, target_id
    # is attacker"), which is what the old order was built on. Ours is the
    # measurement; theirs is a comment. Note it does NOT contradict section 6f:
    # 0x00A3's first slot is the agent damaged, and 0x00A0 value 4's first slot
    # is the agent swinging. Same shape, different roles per value id, which is
    # exactly what GWCA's per-id note was trying to warn about.
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
         [agents.GV_ATTACK_STARTED, PLAYER_AGENT_ID, target_id, 0],
         f"attack_started: player swings at {target_id}")

    dealt = agent["max_health"] * HIT_FRACTION
    agent["health"] = max(0.0, agent["health"] - dealt)

    # Property 16 on 0x00A3: prop, TARGET, cause, value -- target before cause,
    # and the value is a FRACTION of the target's maximum health. Both were
    # measured (studies/enemy/PLAN.md 6b, 6f), and the fmul that makes it a
    # fraction is at 0x0081823C in the client.
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
         [agents.PROP_DAMAGE, target_id, PLAYER_AGENT_ID,
          _f32(-HIT_FRACTION)],
         f"damage {dealt:.0f} to agent {target_id}")
    # And close the swing. Harmless if the client ignores it; without it the
    # attack has a beginning and no end.
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
         [agents.GV_MELEE_ATTACK_FINISHED, PLAYER_AGENT_ID, 0],
         "melee_attack_finished")
    print(f"[c{conn_id}] hit agent {target_id}: "
          f"{agent['health']:.0f}/{agent['max_health']:.0f}", flush=True)

    if agent["health"] <= 0.0:
        # Death is bit 4 of the effects word, not a message. Seven guesses at a
        # death message failed before this was read out of the client
        # (studies/agentprops/FINDINGS.md 1c).
        agent["dead"], agent["died_at"] = True, now
        send(GAME_SMSG_AGENT_UPDATE_STATUS, [target_id, agents.EFFECT_DEAD],
             f"KILL agent {target_id}")
        print(f"[c{conn_id}] agent {target_id} ({agent['name']}) is dead; "
              f"back up in {REVIVE_AFTER:.0f}s", flush=True)


def revive_due(send, state, conn_id):
    """Stand the dead back up. Called from the world tick.

    TWO operations, and that is not tidiness. The client's death path zeroes the
    health and energy pools, so clearing the bit alone returns a body at ~0-1
    health that dies to the next scratch -- OBSERVED, and the reason is visible
    at 0x008183F0 where the effects setter does `fldz` into the pools.
    """
    now = time.time()
    # Iterate a SNAPSHOT. This walked the live dict, which was safe only while
    # nothing could ever remove an agent -- and remove_agent now can. This runs on
    # the world-tick thread, so a removal from any other thread mid-walk would
    # raise "dictionary changed size during iteration" inside the tick, killing the
    # world loop for the rest of the session with a traceback nowhere near the
    # cause. The snapshot costs one list of a handful of agents per tick.
    for agent_id, agent in list(state.get("agents", {}).items()):
        # And re-check membership: an agent removed after the snapshot was taken
        # must not be revived back into a world it has already left.
        if agent_id not in state.get("agents", {}):
            continue
        if not agent["dead"] or now - agent["died_at"] < REVIVE_AFTER:
            continue
        agent["dead"] = False
        agent["health"] = agent["max_health"]
        agent["last_hit"] = 0.0
        send(GAME_SMSG_AGENT_UPDATE_STATUS, [agent_id, 0],
             f"revive agent {agent_id}")
        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
             [agents.PROP_HEALTH_MAX, agent_id, int(agent["max_health"])],
             f"restore max health on agent {agent_id}")
        # Re-asserting the SAME maximum refills nothing, which is why a revived
        # body stood up with an empty bar while our own bookkeeping said full --
        # so it still took a full seven swings to drop, and the bar never moved.
        # OBSERVED 2026-08-06.
        #
        # Property 34 is a DELTA on the health pool, not a setter: we measured
        # -50.0 taking exactly 50 health off (studies/agentprops/FINDINGS.md 1b),
        # and GWCA independently calls it `health`. A full maximum in the
        # positive direction fills a bar the death path had zeroed.
        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
             [agents.GV_HEALTH, agent_id, agent_id,
              _f32(agent["max_health"])],
             f"refill bar on agent {agent_id}")
        print(f"[c{conn_id}] agent {agent_id} ({agent['name']}) is back up",
              flush=True)


def frame_pending(codec_obj, channel, pending, mask):
    """(messages, remaining, desync) for one buffer. `desync` is None or the reason.

    Extracted from the receive loop so the POLICY is testable without a socket, a
    handshake or a client. It was inline, which meant the fix below had no test
    covering it: the suite asserted what codec.decode_stream does, not what this
    server does with the answer, and those are different questions -- the whole
    defect was that the answer was correct and the caller mishandled it.

    THE CONTRACT, and each clause is a thing the old code got wrong:

      * whole messages are returned and their bytes consumed;
      * an INCOMPLETE trailing message is not an error. It is the normal case --
        a TCP read is not a message boundary -- and its bytes stay in `remaining`
        to be completed by the next read;
      * an UNFRAMEABLE message sets `desync` and leaves its bytes in `remaining`
        UNTOUCHED. The old code set `pending = b""` here, which reads like
        recovery and is not: with no length prefix nothing knows where the bad
        message ended, so every later read was framed from a non-boundary while
        ARC4 kept decrypting correctly and the bytes kept looking plausible.
        Returning them unconsumed is what lets the caller report exactly what it
        choked on instead of guessing past it.
    """
    msgs, consumed, err = codec_obj.decode_stream(channel, pending, mask=mask)
    remaining = pending[consumed:]
    if err and "incomplete" not in err:
        return msgs, remaining, err
    return msgs, remaining, None


class AgentLifetimeError(Exception):
    """A removal that the live capture proves ArenaNet never performs."""


def remove_agent(send, state, agent_id, why, conn_id=None):
    """Take an agent out of the world, and free its id for reuse.

    The world state is the point, not the send. `state["agents"]` was a dict that
    only ever grew: entries were added at spawn and nothing removed them, so the
    server had no concept of an agent ceasing to exist and an id could never be
    reused without the client holding a stale object under it.

    TWO REFUSALS, both taken from what the live capture shows ArenaNet never does
    (studies/divergence/FINDINGS.md D1) rather than from taste:

      * removing an id that was never created -- 0 of 416 live;
      * removing an id that is already removed, with no create in between --
        0 of 416 live.

    Both raise rather than sending. The client bounds-checks the dword as an index
    into its agent array (`Array:587 "index < m_count"` at 0x005FD2F0), so a bad id
    is an assert on the client, in its own process, thirty seconds later and
    nowhere near the cause. Refusing here keeps the failure where the bug is.

    Returns the removed bookkeeping entry, so a caller respawning the same id can
    carry forward what it needs.
    """
    live = state.setdefault("agents", {})
    if agent_id not in live:
        raise AgentLifetimeError(
            f"refusing to remove agent {agent_id}: it is not in the world. "
            f"live ids: {sorted(live)}. ArenaNet removed a never-created id "
            f"0 times in 416 -- and the client bounds-checks this dword.")
    entry = live.pop(agent_id)
    # An append-only audit trail, and burrowing is what makes its bound matter. Nothing
    # reads this except test_agentlife, and until now removals happened a handful of
    # times per session; a burrowing worm removes itself roughly every ten seconds --
    # ArenaNet's ran 140 times in 186 s. An unbounded list fed by the world tick is a
    # leak, so it keeps the most recent REMOVED_AGENTS_KEPT and says so here rather
    # than being quietly trimmed somewhere a reader would not look for it.
    log = state.setdefault("removed_agents", [])
    log.append(agent_id)
    if len(log) > REMOVED_AGENTS_KEPT:
        del log[:-REMOVED_AGENTS_KEPT]
    send(GAME_SMSG_WORLD_REMOVE_AGENT, [agent_id],
         f"WORLD_REMOVE_AGENT({agent_id}) — {why}")
    if conn_id is not None:
        print(f"[c{conn_id}] removed agent {agent_id} "
              f"({entry.get('name', '?')}) — {why}", flush=True)
    return entry


def create_agent_world(send, state, agent_id, entry, why,
                       conn_id=None, send_definition=True):
    """Put an agent into the world AND into `state["agents"]`, as one operation.

    THE ASYMMETRY THIS EXISTS TO CLOSE. `remove_agent` guards its side: it refuses an
    id that is not live and an id already removed, and it pops the entry. The create
    side had no counterpart -- `spawn_enemy` writes `state["agents"][id] = {...}` as a
    bare dict assignment with nothing checking it. That was harmless while creates
    happened once, at map load, on the connection thread.

    Burrowing makes it dangerous. A re-create that emits the wire messages and forgets
    the state write leaves the world model believing the agent is gone, so the NEXT
    submerge raises AgentLifetimeError -- inside the world-tick daemon thread, which
    takes the whole tick down for the rest of the session with a traceback nowhere near
    the cause. That is the same failure `revive_due`'s snapshot comment was written
    about, from the other direction.

    `send_definition` is the question we cannot answer offline. ArenaNet sends the NPC
    definition (0x0056) exactly ONCE for 140 re-creates of the same worm, so their
    client evidently keeps it across a removal. Ours has never been asked: the D1 probe
    re-sent the definition every time, so its success says nothing about whether the
    definition survives. `agents.npc_properties` warns that an agent whose definition
    was never sent takes the client down on `index < m_count`. Until the `burrow` probe
    settles it, this defaults to TRUE -- resending is what we have evidence is safe, and
    the cost of being wrong in the other direction is a client assert.
    """
    live = state.setdefault("agents", {})
    if agent_id in live:
        raise AgentLifetimeError(
            f"refusing to create agent {agent_id}: it is already in the world. "
            f"live ids: {sorted(live)}. Creating over a live id leaves the client "
            f"holding one agent's state under another's name, and nothing on the "
            f"wire would say so.")

    npc = entry["npc"]
    definition = entry["definition"]
    x, y = entry["pos"]
    plane = entry["plane"]
    if send_definition:
        send(GAME_SMSG_NPC_UPDATE_PROPERTIES,
             agents.npc_properties(definition, npc),
             f"NPC_UPDATE_PROPERTIES(def {definition})")
        # A definition need not have a model row. ArenaNet declares 8 of the 44
        # definitions in capture 20260807T143055 with 0x0056 and NO 0x0057 at
        # all, and the Lakeside worm is one of them -- so a content row may
        # honestly lack `model_id`, and sending one anyway would mean inventing
        # it. That guess is what made the first agent_removal run's negative
        # meaningless. OBSERVED; studies/smsg/FINDINGS.md.
        if npc.get("model_id") is not None:
            send(GAME_SMSG_MONSTER_COMPOSITE, agents.npc_model(definition, npc),
                 f"NPC_UPDATE_MODEL(def {definition})")

    # The effects an agent is BORN with, which is what 0x00F0 is for. This is the one
    # message of ArenaNet's five-message worm create burst that we can send honestly:
    # the value is measured (0x1000 on 151 of 151) and the field shape is in the
    # catalog. The other three are NOT here on purpose --
    #
    #   0x009F [66, agent, 0]   property 66 appears nowhere else in this repo and its
    #                           meaning is NOT FOUND. Sending an unknown property is a
    #                           probe, not a default.
    #   0x006D [agent, item, 0] carries an ITEM id we do not have and would have to
    #                           invent.
    #   0x0026 [agent, 9]       two observed values, one of them seen exactly once.
    #
    # They are steps in the `burrow` probe instead, each with what to watch. Reproducing
    # a burst by filling its unknown fields with guesses would make every later
    # observation un-attributable -- which is the whole lesson of the first agent_removal
    # probe, whose bare 0x0020 produced a negative that meant nothing.
    if entry.get("effects"):
        send(GAME_SMSG_AGENT_INITIAL_STATUS, [agent_id, int(entry["effects"])],
             f"AGENT_INITIAL_EFFECTS({agent_id}, 0x{int(entry['effects']):04X})")

    send(GAME_SMSG_WORLD_CREATE_AGENT,
         agents.create_agent(agent_id,
                             agents.CHAR_CLASS_MONSTER_BASE | definition,
                             agents.AGENT_KIND_NPC, x, y, plane,
                             allegiance=entry["allegiance"]),
         f"WORLD_CREATE_AGENT({agent_id}) — {why}")
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
         [agents.PROP_HEALTH_MAX, agent_id, int(entry["max_health"])],
         f"health {int(entry['max_health'])} on agent {agent_id}")

    # --- three of the four named on 2026-08-10, sent here for the first time ---
    #
    # The profession pair. Ours have always rendered with no profession at all,
    # because we never sent this: no icon on the nameplate, nothing in the
    # roster. The content row carries it, and agents.py refuses a primary of 0
    # because 0 never occurs in 387 live samples and does NOT mean "none".
    # `npc` is already bound at the top of this function.
    if npc.get("profession"):
        send(GAME_SMSG_AGENT_SET_PROFESSION,
             agents.agent_set_profession(agent_id, int(npc["profession"])),
             f"AGENT_SET_PROFESSION({agent_id}, {npc['profession']})")

    # The create burst's tail. OBSERVED: this message's field 2 mirrors the
    # create's kind byte -- (9, 9) in 153 of 155 samples, (9, 8) in 2 -- so the
    # value is the agent kind and not a guess. It is a MERGE, and agents.py
    # refuses anything inside the mask the client keeps for itself.
    send(GAME_SMSG_AGENT_UPDATE_FLAGS,
         agents.agent_update_flags(agent_id, agents.AGENT_KIND_NPC),
         f"AGENT_UPDATE_FLAGS({agent_id}, kind {agents.AGENT_KIND_NPC})")

    send_attack_speed(send, agent_id, entry["attack_speed"], entry.get("name", "npc"))

    live[agent_id] = entry
    if conn_id is not None:
        print(f"[c{conn_id}] created agent {agent_id} ({entry.get('name', '?')}) "
              f"— {why}", flush=True)
    return entry


# Burrowing. The measured cycle, from vault/captures/live/20260807T143055 -- two
# independent Lakeside visits, 151 worm re-creations, one burst shape and no exceptions.
#
# Only the two transition windows are fixed at 2.00 s. How long a worm stays OUT and how
# long it stays HIDDEN are not periods at all: out ran 0.48-7.48 s and hidden 1.6-6.9 s
# for the fast family, and two families sharing one model ran ~8-10 s and ~33 s cycles
# with player distance failing to explain the split. So those two numbers are ours and
# `content/world.toml` says so; these two are theirs.
BURROW_EMERGE_SECONDS = 2.00
BURROW_SUBMERGE_SECONDS = 2.00

# How much of the removal audit trail `remove_agent` keeps. Generous enough that no test
# or session inspection notices, bounded so a burrowing world cannot grow it forever.
REMOVED_AGENTS_KEPT = 512

BURROW_EMERGING = "emerging"   # created, transition bit set, animating up
BURROW_OUT = "out"             # bit cleared, targetable
BURROW_SUBMERGING = "submerging"  # bit set again, animating down
BURROW_HIDDEN = "hidden"       # removed from the world entirely


def burrow_tick(send, state, conn_id):
    """Advance every burrowing agent through emerge -> out -> submerge -> hidden.

    The third sweep in the world tick, and the first one that has to reason about an
    agent that EXISTS but is not in `state["agents"]` -- a hidden worm lives in
    `state["hidden"]`, holding the entry `remove_agent` handed back for exactly this.

    Copies `revive_due`'s two disciplines verbatim and for a stronger reason. That
    function iterates a snapshot and re-checks membership because `remove_agent` COULD
    mutate the dict mid-walk; after this one exists it WILL, several times a minute.

    A DEAD AGENT DOES NOT BURROW, and it is asserted rather than assumed. `hit_enemy`
    writes `dead`/`died_at` into the entry and `revive_due` only ever sees agents still
    in `state["agents"]` -- so a body that died while out and then submerged would be
    popped out of the dict with its revive timer still pending, and nothing would ever
    stand it back up. It would simply never return.
    """
    now = time.time()
    hidden = state.setdefault("hidden", {})

    for agent_id, entry in list(state.get("agents", {}).items()):
        if agent_id not in state.get("agents", {}):
            continue                      # removed after the snapshot was taken
        phase = entry.get("burrow_phase")
        if not phase or entry.get("dead"):
            continue                      # not a burrower, or dead -- see above
        if now < entry.get("burrow_at", 0.0):
            continue

        if phase == BURROW_EMERGING:
            entry["burrow_phase"] = BURROW_OUT
            entry["burrow_at"] = now + entry["burrow_out_seconds"]
            entry["effects"] = 0
            send(GAME_SMSG_AGENT_UPDATE_STATUS, [agent_id, 0],
                 f"agent {agent_id} is fully out")
        elif phase == BURROW_OUT:
            entry["burrow_phase"] = BURROW_SUBMERGING
            entry["burrow_at"] = now + BURROW_SUBMERGE_SECONDS
            entry["effects"] = agents.EFFECT_TRANSITION
            send(GAME_SMSG_AGENT_UPDATE_STATUS,
                 [agent_id, agents.EFFECT_TRANSITION],
                 f"agent {agent_id} is submerging")
        elif phase == BURROW_SUBMERGING:
            entry["burrow_phase"] = BURROW_HIDDEN
            entry["burrow_at"] = now + entry["burrow_hidden_seconds"]
            # remove_agent does the state write and the refusals; we keep what it
            # returns, which is the entry itself.
            hidden[agent_id] = remove_agent(send, state, agent_id,
                                            "burrowed", conn_id=conn_id)

    for agent_id, entry in list(hidden.items()):
        if now < entry.get("burrow_at", 0.0):
            continue
        hidden.pop(agent_id, None)
        entry["burrow_phase"] = BURROW_EMERGING
        entry["burrow_at"] = now + BURROW_EMERGE_SECONDS
        entry["effects"] = agents.EFFECT_TRANSITION
        # Re-emerge at byte-identical coordinates. OBSERVED: 13 of 13 worms in the
        # second Lakeside tape and 6 of 6 in the first carry exactly ONE distinct
        # (x, y) across every one of their creates, which the wiki independently
        # predicts -- a submerged worm cannot move.
        create_agent_world(send, state, agent_id, entry, "emerging from burrow",
                           conn_id=conn_id,
                           send_definition=entry.get("resend_definition", True))


def send_attack_speed(send, agent_id, base, what):
    """Give one agent an attack speed. EVERY living agent needs one.

    Not a nicety. The client's AvChar constructor writes 0.0 to both fields
    (0x007F1FD2) and the animation path asserts both non-zero on the way in
    (AvChar.cpp:4791/4792), so an agent the server never told cannot be
    animated attacking -- the client dies instead. GAME_SMSG 0x0035 is the only
    thing in the image that sets them. studies/enemy/PLAN.md 6q.

    The assert does NOT fire on the packet that starts the swing. That packet
    queues a request at AvChar+0xCC and the per-frame tick
    (AvApi 0x007DF280 -> AvManager) processes it a frame later, which is where
    it dies -- so the crash lands a moment after the send and blames whichever
    agent the request was queued on, not necessarily the one you aimed at.
    That is why this goes on every agent rather than only the attacker.
    """
    send(GAME_SMSG_AGENT_UPDATE_ATTACK_SPEED,
         [agent_id, _f32(base), _f32(agents.ATTACK_SPEED_UNMODIFIED)],
         f"ATTACK_SPEED({what} {agent_id}: base {base}s, modifier "
         f"{agents.ATTACK_SPEED_UNMODIFIED})")


def enemy_spot(state, ox, oy):
    """Somewhere near the player that the navmesh agrees is ground.

    The offset used to be a fixed 300 east, which was fine in Kamadan and is
    not fine anywhere else -- MEASURED on the Pre-Searing region, +300 east of
    one candidate spawn is off the mesh entirely. A body placed off-mesh is
    worse than a body in an odd spot: it is standing somewhere the server's own
    collision says does not exist, so everything downstream reasons about it
    wrongly.

    Falls back to the plain offset when there is no navmesh at all, which is a
    normal outcome -- the archive is the player's own install and is not
    required to be present.
    """
    pm = state.get("pathmap")
    if pm is None:
        return ox + ENEMY_OFFSET[0], oy + ENEMY_OFFSET[1]
    d = ENEMY_OFFSET[0]
    for dx, dy in ((d, 0), (0, d), (-d, 0), (0, -d),
                   (d, d), (-d, d), (d, -d), (-d, -d)):
        if pm.walkable(ox + dx, oy + dy):
            return ox + dx, oy + dy
    return ox + ENEMY_OFFSET[0], oy + ENEMY_OFFSET[1]


def spawn_enemy(send, state, origin, conn_id):
    """Put one hostile body in the map, using only packets we have proven.

    Every message here was established one at a time against our own client and
    is cited in studies/enemy/PLAN.md: the definition and model (6d), the
    monster class nibble and the allegiance FourCC that makes it read as an
    enemy (6e), and the maximum health (6g). Nothing in this function is new
    protocol -- it is the `death` probe's opening, moved onto the normal path.

    ORDER IS LOAD-BEARING. The definition must precede the agent that uses it:
    the definition index is a raw array index on the client, and an agent whose
    type was never defined crashes it outright. OBSERVED.

    The wire order is unchanged; what moved is the STATE WRITE. This used to end
    with `state["agents"][id] = {...}` as a bare assignment while `remove_agent`
    guarded its own side, and burrowing turns that asymmetry into a live hazard --
    see `create_agent_world`, which now owns both halves.
    """
    ox, oy, plane = origin
    x, y = enemy_spot(state, ox, oy)

    entry = {
        "pos": (x, y), "plane": plane,
        "health": float(ENEMY_MAX_HEALTH), "max_health": float(ENEMY_MAX_HEALTH),
        "dead": False,
        "name": agents.HATCHER["name"],
        # What create_agent_world needs to rebuild this agent from the entry alone,
        # which is exactly what a burrow re-create does.
        "npc": agents.HATCHER,
        "definition": ENEMY_DEFINITION,
        "allegiance": agents.ALLEGIANCE_HOSTILE,
        "attack_speed": ENEMY_ATTACK_SPEED,
        "effects": 0,
    }
    if ENEMY_BURROWS:
        entry.update({
            "burrow_phase": BURROW_EMERGING,
            "burrow_at": time.time() + BURROW_EMERGE_SECONDS,
            "burrow_out_seconds": ENEMY_BURROW_OUT,
            "burrow_hidden_seconds": ENEMY_BURROW_HIDDEN,
            "effects": agents.EFFECT_TRANSITION,
        })

    create_agent_world(send, state, ENEMY_AGENT_ID, entry,
                       "burrowing hostile" if ENEMY_BURROWS else "hostile",
                       conn_id=conn_id)
    # NOT SENT, and the reason is worth keeping. 0x002F is ldufr's
    # AGENT_UPDATE_ALLEGIANCE, and it looked like the way to set the byte GWCA
    # documents at AgentLiving+h01B1 -- the one whose values are named
    # "ally/non-attackable" and "enemy". It is not. Its handler at 0x005fdd70
    # hands field 2 to a setter at 0x00602e20 which writes [esi+0xE8], nowhere
    # near +0x1B1. SOURCED, read from this build. Sending it changed nothing
    # observable, which is consistent with it being some other field entirely.
    #
    # Nothing in this image writes +0x1B1 or +0x1B2 in any addressing form a
    # displacement scan finds, so either GWCA's offsets are for a different
    # build or the write is computed. Do not send 0x002F for this purpose again
    # without settling that first.
    #
    # The health and attack-speed sends that used to sit here moved into
    # create_agent_world, unchanged and in the same order, so that a burrow
    # re-create issues exactly what the first create did.
    print(f"[c{conn_id}] enemy {ENEMY_AGENT_ID} ({agents.HATCHER['name']}) "
          f"at ({x:.0f}, {y:.0f}) plane {plane}, {ENEMY_MAX_HEALTH} hp"
          + (f", burrowing ({ENEMY_BURROW_OUT:.1f}s out / "
             f"{ENEMY_BURROW_HIDDEN:.1f}s hidden)" if ENEMY_BURROWS else ""),
          flush=True)


def play_tape(send_raw, conn_id, stop, events, info, speed=1.0):
    """Play a recorded server's plaintext into a live session, at recorded timing.

    R1.5. Runs on its own thread for the same reason a probe does: the receive loop
    must keep running throughout or the client times out mid-tape, and the tape is
    48 seconds long.

    THE PREDICTION IS STATED HERE rather than in a commit message, because this is
    an experiment and the house rule is that a probe with no stated expectation can
    be rationalised into agreeing with whatever happened:

      * PREDICTED, and CONFIRMED 2026-08-10: the client loads the recorded map and
        draws its agents. It did far more than that -- 1,209 of 1,209 events with
        zero messages of ours on the channel, and the client skipped the cutscene,
        walked to each quest giver in order, spoke to them, accepted quests and
        walked to the zone exit. Chat arrived. RUN, POSITIVE.
      * THE INFORMATIVE FAILURE, which did NOT happen and is therefore the result:
        an assert naming a player-identity field. THE CLIENT DOES NOT CHECK. The tape
        names the RECORDED character -- an 11-character name in 0x017D and in the
        player's 0x0059 row, player number 26, agent 725, plus 40 other players --
        and the client logged in as ours. Whether it cross-checks the identity it
        SENT against the one it is TOLD about was UNVERIFIED; it is now OBSERVED
        that it does not. Nothing was renamed for the run, so this is the honest
        answer rather than one obtained by sneaking past a check.
      * NOT PREDICTED, and out of scope: control. The tape's 987 move messages
        answer the RECORDED operator's clicks, so the avatar walks the recorded path
        whatever the new operator does, and client-side prediction will fight it. A
        tape shows a load and a populated world; it cannot show control.
      * RUN 2, 2026-08-10, Lakeside County (`:64103`): 1,074/1,074, zero of ours on
        the channel, and IT RENDERED COMBAT -- the recorded operator's fight with a
        Wolf, Vampiric Gaze and Deathly Swarm, played back into a client that had no
        server behind it. Also OBSERVED there: the client drew map 146 while its own
        VERSION had asked for 148, so the identity result above generalises to the
        map id. studies/tape/FINDINGS.md is the log; read it before the next run,
        because two of its findings are about how to READ a run rather than what one
        found -- the recorded avatar stands still for the last 146 s of that tape and
        looks finished, and `--map` is inert here.

    Pacing is per WIRE SEGMENT, not per message, because that is the resolution the
    capture has -- 1,209 timing points for 3,981 messages on the Ascalon tape. Drift
    is corrected against a fixed origin rather than accumulated per sleep, so a slow
    send cannot stretch the whole tape.
    """
    bar = "=" * 62
    print(f"\n{bar}\nTAPE: {info['connection']}\n"
          f"  {info['events']:,} events, {info['bytes']:,} B, {info['seconds']:.1f}s"
          f"{'' if speed == 1.0 else f' at {speed}x'}\n"
          f"  from {info['capture']} ({info['origin']})\n"
          f"  PREDICTS: the client loads the recorded map and draws its agents.\n"
          f"  The informative failure is an assert naming a player-identity field --\n"
          f"  the tape names the RECORDED character, not the one that logged in.\n{bar}",
          flush=True)
    t0 = time.monotonic()
    sent = 0
    try:
        for i, (t, blob) in enumerate(events):
            if stop.is_set():
                print(f"[c{conn_id}] tape stopped at event {i}/{len(events)}", flush=True)
                return False
            due = t0 + (t / speed if speed else 0.0)
            now = time.monotonic()
            if due > now:
                time.sleep(due - now)
            send_raw(blob, f"tape[{i}]")
            sent += 1
            if i and i % 200 == 0:
                print(f"[c{conn_id}] tape {i}/{len(events)} "
                      f"({time.monotonic() - t0:.1f}s)", flush=True)
    except (ConnectionError, OSError) as ex:
        # The client dropped, or asserted and took the socket with it. That is THE
        # RESULT of this experiment, not a crash to swallow -- so say exactly what
        # was in flight when it happened. The client's own assert names a source
        # file and line; this names the bytes that provoked it, and the pair is
        # what turns a crash into a finding.
        #
        # OBSERVED 2026-08-10: the client died at event 739/1209, t=22.4s, and the
        # two events either side of that were the largest in the neighbourhood --
        # 229B and 209B carrying WORLD_CREATE_AGENT plus equipment and property
        # updates, i.e. another player zoning into the outpost. Without this
        # readout that had to be reconstructed afterwards from the tape by hand.
        print(f"\n[c{conn_id}] TAPE ENDED at event {sent}/{len(events)} "
              f"after {time.monotonic() - t0:.1f}s: {type(ex).__name__}: {ex}",
              flush=True)
        lo = max(0, sent - 3)
        # DO NOT CALL THIS A CLIENT ASSERT. This banner used to open "the client
        # asserts on one of these", and on 2026-08-10 it said that about a tape whose
        # client was in perfect health: the HARNESS had reached its verdict target and
        # torn the stack down 1.7s into a 396-second chain, so the socket died under a
        # tape that had barely started. Everything on screen read as crash-on-map-load,
        # and the only thing that contradicted it was the absence of an Assertion line
        # in the client's own log.
        #
        # This end of the socket cannot tell a client assert from a shutdown, so it
        # says both and names the one check that separates them.
        print(f"[c{conn_id}] the client's connection went away. That is EITHER a client "
              f"assert on one of the events below, OR the stack being shut down "
              f"(--keep-open / --hold, or a verdict target already reached).",
              flush=True)
        # CORRECTED 2026-08-11. This used to say "Gw.log decides it: an Assertion
        # line means the client; no Assertion line means the teardown." Gw.log
        # does NOT record asserts -- it is a perf/error log, and a run that
        # asserted at 01:10:56 that day has no Assertion line in it. So that
        # check could never fire, and a conclusion drawn from it on 2026-08-10
        # (that a tape's client was healthy) rested on nothing.
        print(f"[c{conn_id}] The client's ERROR DIALOG decides it, and nothing else "
              f"does: Gw.log carries no asserts, no dump file is written anywhere "
              f"findable, and a reset here happens on clean teardowns too. "
              f"session.py captures the dialog automatically into the run "
              f"directory as crash-dialog.txt; standalone, use "
              f"toolkit/harness/read_error_dialog.py.", flush=True)
        for j in range(lo, min(sent + 2, len(events))):
            et, eb = events[j]
            try:
                msgs, _c, _e = codec.decode_stream("GAME_SMSG", eb)
                ops = " ".join(f"0x{op:04x}" for op, _v in msgs[:10])
                more = "..." if len(msgs) > 10 else ""
            except Exception:
                ops, more = eb[:12].hex(" "), " (undecodable)"
            flag = "  <<< LAST SENT" if j == sent - 1 else ""
            print(f"[c{conn_id}]   ev{j} t={et:.2f}s {len(eb)}B  {ops}{more}{flag}",
                  flush=True)
        print(f"[c{conn_id}] re-run with --tape-speed 0.25 to spread these out, or "
              f"copy the client's Assertion line -- it names the source file.",
              flush=True)
        return False
    print(f"[c{conn_id}] tape complete: {sent}/{len(events)} events in "
          f"{time.monotonic() - t0:.1f}s", flush=True)
    return True


# A tape that ends in a handoff must end the CONNECTION too, and this is not tidiness.
#
# MEASURED in the recording: the server closes immediately after sending 0x01A5 --
# connection :62994 closes at t=213.70 and :64102 opens at t=213.84, a 0.140 s gap, and
# the same shape at every transition (0.137 s, 0.118 s). The recorded server hangs up.
# Our player did not: it ran out of events and sat on the socket.
#
# WHY THAT MATTERS, from the client's own code (build 38797). The 0x01A5 handler at
# 0x0084f290 branches on bit 0x20 of a flags dword at +0x190:
#
#     mov  eax, [esi + 0x190]
#     test al, 0x20
#     je   0x84f359          <- clear: call 0x850df0 and DIAL NOW
#     or   eax, 0x10         <- set:   stash the sockaddr, mark pending, RETURN
#
# and the connect function 0x850df0 SETS that bit itself (`or [ebx+0x190], 0x20` at
# 0x00850e56, same function body, no ret in between). So the FIRST game-channel
# transfer of a session dials immediately and every LATER one defers, waiting for the
# connection it already has to go away.
#
# OBSERVED 2026-08-10, and it is exactly that shape: hop 1 -> hop 2 dialled at once
# (hop 1's own connection came from the AUTH handoff, so bit 0x20 was still clear), and
# hop 2 -> hop 3 never dialled at all -- correct destination on screen, correct alias in
# the client's overlay, no SYN, auth channel still heartbeating. One transfer per
# session worked and the next hung, which is the signature of a deferred dial whose
# trigger never fired.
# How long to keep reading after our FIN before giving up on a clean two-way close.
# The client answers within milliseconds when it is healthy; this only bounds the
# case where it does not.
GRACEFUL_CLOSE_SECONDS = 2.0


def close_after_transfer(sock, events, codec_obj, conn_id):
    """Hang up if this tape ended by handing the client somewhere else.

    Returns True if the socket was closed. Deliberately keyed on the tape CONTAINING a
    transfer rather than on a flag: a tape that stays in its map (the last hop, or any
    --tape-no-transfer run) must NOT be hung up on, because the whole point of those is
    that the client keeps playing afterwards.
    """
    if tape_transfer_present(events, codec_obj) is None:
        return False
    print(f"[c{conn_id}] tape ended in a handoff -- closing the connection GRACEFULLY, "
          f"which is what the recorded server did (0.14s before the client re-dialled).",
          flush=True)
    # HOW we close decides whether the client reconnects, and the first version of this
    # got it wrong. The client's disconnect path branches on a reason code at [esi+0xc]:
    # reason 0 falls through to `call 0x850df0` at 0x008515b7 and RE-DIALS the stashed
    # address; reason >= 3 pops and returns, doing nothing; reason 7 is special-cased.
    # So a deferred transfer is only released by the disconnect the client considers
    # clean.
    #
    # shutdown(SHUT_RDWR) followed by close() is NOT that. With bytes still unread in the
    # receive buffer -- and there always are, the client keeps sending 0x8008/0x800c
    # after the tape ends -- Windows answers with an RST rather than a FIN. That is a
    # different reason code, and it is why hanging up twice released nothing.
    #
    # So: half-close (send FIN, keep reading), drain what the client is still sending
    # until it closes its half or a short deadline passes, and only then close. That is
    # an ordinary graceful shutdown and it is what the recording shows.
    try:
        sock.shutdown(socket.SHUT_WR)
    except OSError:
        pass
    drained, deadline = 0, time.monotonic() + GRACEFUL_CLOSE_SECONDS
    try:
        sock.settimeout(0.25)
        while time.monotonic() < deadline:
            chunk = sock.recv(4096)
            if not chunk:
                break               # the client closed its half: a clean FIN both ways
            drained += len(chunk)
    except (OSError, socket.timeout):
        pass
    try:
        sock.close()
    except OSError:
        pass
    print(f"[c{conn_id}] closed after draining {drained} B -- an unread receive buffer "
          f"turns close() into an RST, and the client only re-dials on the reason code "
          f"a clean shutdown produces.", flush=True)
    return True


def tape_transfer_present(events, codec_obj):
    """The handoff in this tape, or None. Thin wrapper so authsrv owns no tape logic."""
    import tape as tapemod
    try:
        return tapemod.transfer_of(events, codec_obj)
    except Exception:
        return None


def run_probe(name, send, conn_id, stop, origin=None):
    """Fire a scripted experiment at the client, on its own thread.

    On its own thread because the steps are deliberately seconds apart -- a
    person has to see one result before the next arrives -- and the receive loop
    must keep running throughout or the client times out mid-probe.

    Failures are printed and swallowed. A probe is an experiment; a packet the
    client rejects is a result, not a crash, and it must not take the session
    down with it or we lose the rest of the sequence.
    """
    # origin is where the character is standing. A probe that places something
    # in the world needs it, and can only have it from here -- probes.py is a
    # data module with no view of the session.
    probe = probes.get(name, PLAYER_AGENT_ID, origin)
    if probe is None:
        print(f"[c{conn_id}] no probe named {name!r}; "
              f"known: {', '.join(probes.names())}", flush=True)
        return

    def body():
        bar = "=" * 62
        print(f"\n{bar}\nPROBE: {name}\n  Q: {probe.question}\n"
              f"  predicts: {probe.predicts}", flush=True)
        if probe.note:
            print(f"  note: {probe.note}", flush=True)
        if not probe.steps:
            print(f"  (no packets -- observation only)\n{bar}\n", flush=True)
            return
        for i, step in enumerate(probe.steps, 1):
            if stop.wait(step.delay):
                return
            print(f"\n  --- step {i}/{len(probe.steps)}: {step.label}",
                  flush=True)
            try:
                send(step.opcode, step.values, f"PROBE[{name}] {step.label}")
            except Exception as exc:
                print(f"      SEND FAILED: {type(exc).__name__}: {exc}",
                      flush=True)
                print(f"      (that is a result too -- record it)", flush=True)
                continue
            print(f"      WATCH: {step.watch}", flush=True)
        print(f"\n  probe complete. What did you see?\n{bar}\n", flush=True)

    threading.Thread(target=body, daemon=True).start()


class Recorder:
    def __init__(self, vault, conn_id):
        os.makedirs(vault, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%S")
        base = os.path.join(vault, f"authsrv-{stamp}-c{conn_id}")
        self.meta = open(base + ".jsonl", "a", encoding="utf-8")
        self.raw = open(base + ".raw", "ab")
        self.t0 = time.perf_counter()
        self._frame_seq = itertools.count()
        # FIRST record in the file, before any frame. This server IS our server, so it
        # can only ever produce OURS -- but stamping it is what lets a reader tell this
        # apart from a capture of ArenaNet's, which is the one artifact the project
        # cannot reproduce. See toolkit/origin.py for why UNKNOWN is a third value
        # rather than a default.
        stamped = origin.record(
            "toolkit/authsrv/authsrv.py", origin.OURS,
            note="a Rurik listener; the peer is the client connecting to us")
        self.event(stamped.pop("kind"), **stamped)

    def event(self, kind, **kw):
        kw["kind"] = kind
        kw["t"] = round(time.perf_counter() - self.t0, 6)
        kw["wall"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.meta.write(json.dumps(kw) + "\n")
        self.meta.flush()

    def frame(self, direction, cipher: bytes, plain: bytes):
        # Numbered like the s2c `sent` events, but NOT because it has the same
        # defect. c2s has exactly ONE decrypt site -- the receive loop's
        # c2s.crypt -- on exactly one thread, which both decrypts and logs before
        # reading again, so decryption order and log order cannot come apart here
        # the way they can for s2c. Two things earn the number anyway: it makes
        # the .raw sidecar and the .jsonl joinable record-for-record (seq N is the
        # Nth .raw record, because seq is taken before the write) rather than by
        # position and hope; and if a second decrypt site is ever added, that
        # single-thread argument breaks silently, whereas a gap or a repeat in
        # this counter says so out loud.
        #
        # Not written into the .raw record itself: that format has no reader yet
        # and changing its layout would cost more than it buys.
        seq = next(self._frame_seq)
        # Length-prefixed so the file stays parseable when the parser is rewritten.
        self.raw.write(struct.pack("<BId", 0 if direction == "c2s" else 1,
                                   len(cipher), time.perf_counter() - self.t0))
        self.raw.write(cipher)
        self.raw.flush()
        self.event("frame", seq=seq, direction=direction, n=len(cipher),
                   cipher=binascii.hexlify(cipher[:512]).decode(),
                   plain=binascii.hexlify(plain[:512]).decode())

    @property
    def closed(self):
        """Has the connection this recorder belongs to already been torn down?

        Background threads (the tape player, a probe, the labelled run) outlive the
        connection handler that owns the recorder, so they can and do reach a closed
        file. Asking is better than catching: a thread that discovers this can say
        what it is skipping and why, instead of dying on `I/O operation on closed
        file` and stacking a confusing traceback on top of the real failure.
        """
        return self.meta.closed

    def close(self):
        self.meta.close()
        self.raw.close()


def sockaddr_in(host: str, port: int) -> bytes:
    """The 24-byte `host` blob in GAME_SERVER_INFO is a raw sockaddr, not a string.

    Byte order is mixed and that is not a mistake: the address family is
    little-endian, the port is big-endian (network order, as sockaddr_in has
    always stored it), and the four address bytes are already in network order
    from inet_aton. Getting the port endianness wrong sends the client to a
    plausible-looking port thousands away from ours, and the only symptom is a
    connection that never arrives.

    24 bytes is sizeof(struct sockaddr), padded; an IPv6 handoff would fill more
    of it. Both reference implementations size the field this way.
    """
    if HOST_FIELD_ENCODING == "string":
        # The competing reading: 24 bytes is a NUL-padded "host:port" string
        # rather than a sockaddr. Under the sockaddr reading the field starts
        # 02 00, which as a C string is EMPTY -- and an empty host would
        # explain the client falling back to the -portal address on the
        # default HTTP port, i.e. 127.0.0.1:80, which is exactly what it dials.
        text = f"{host}:{port}".encode("ascii")
        if len(text) > 24:
            raise ValueError(f"host string {text!r} does not fit in 24 bytes")
        return text.ljust(24, b"\x00")

    return (struct.pack("<H", socket.AF_INET)
            + struct.pack(">H", port)
            + socket.inet_aton(host)
            + b"\x00" * 16)


def handle_request_game_instance(values, send, conn_id, state, rec):
    """Answer REQUEST_GAME_INSTANCE by pointing the client at our game server.

    Wire order in is  req_id, map_type, map_id, region, district, language;
    wire order out is req_id, world_id, map_id, host[24], player_id.

    GAME_SERVER_INFO must precede REQUEST_RESPONSE, the same way every
    CHARACTER_INFO must precede it during login: REQUEST_RESPONSE is what
    advances the client's state machine, and anything sent after it arrives to a
    client that has already moved on.

    world_id and player_id are ours to choose -- the client only echoes them back
    to the game server, which uses them to match the connection to this handoff.
    They are recorded here so that server can check them.
    """
    _, req_id, map_type, map_id, region, district, language = values

    world_id = state.setdefault("world_id", secrets.randbits(31) or 1)
    player_id = secrets.randbits(31) or 1
    state["player_id"] = player_id
    state["map_id"] = map_id

    print(f"[c{conn_id}] play requested: map_id={map_id} map_type={map_type} "
          f"region={region} district={district} language={language}", flush=True)
    print(f"[c{conn_id}] handing off to {GAME_SRV_HOST}:{GAME_SRV_PORT} "
          f"world_id={world_id} player_id={player_id}", flush=True)
    rec.event("game_instance_request", req_id=req_id, map_id=map_id,
              map_type=map_type, region=region, district=district,
              language=language, world_id=world_id, player_id=player_id,
              host=GAME_SRV_HOST, port=GAME_SRV_PORT)

    send(AUTH_SMSG_GAME_SERVER_INFO,
         [req_id, world_id, map_id, sockaddr_in(GAME_SRV_HOST, GAME_SRV_PORT),
          player_id],
         "GAME_SERVER_INFO")
    send(AUTH_SMSG_REQUEST_RESPONSE, [req_id, 0], "REQUEST_RESPONSE(OK)")


def handle_portal_login(values, send, store, conn_id, allow_any, rec):
    """Answer PORTAL_ACCOUNT_LOGIN with the burst that produces character select.

    Order is load-bearing at both ends: every CHARACTER_INFO must precede
    REQUEST_RESPONSE, and REQUEST_RESPONSE must be last. It is the only message
    that advances the client's login state machine — the rest merely fill passive
    structures. Send them early and the client can flip to character select
    against an empty roster, which renders as "logged in, no characters" rather
    than as an error.
    """
    req_id, user_id_wire, token_wire = values[1], values[2], values[3]
    who = f"{wire_to_uuid(user_id_wire)} / token {wire_to_uuid(token_wire)}"

    session = store.lookup(user_id_wire, token_wire)
    if session is None and not allow_any:
        # Reject loudly rather than hang. An error on screen proves the whole
        # encrypted path works and narrows the fault to the session record.
        print(f"[c{conn_id}] login REJECTED — no session for {who}", flush=True)
        rec.event("login_rejected", who=who)
        send(AUTH_SMSG_REQUEST_RESPONSE, [req_id, GM_ERROR_AUTH],
             "REQUEST_RESPONSE(AUTH_ERROR)")
        return

    if session is None:
        print(f"[c{conn_id}] login accepted WITHOUT a session record "
              f"(--allow-any-session) — {who}", flush=True)
    else:
        print(f"[c{conn_id}] login OK — {session['email']}", flush=True)
    rec.event("login_ok", who=who, email=(session or {}).get("email"))

    send(AUTH_SMSG_CHARACTER_INFO,
         [req_id, TEST_CHAR_UUID, 0, TEST_CHAR_NAME, TEST_CHAR_SETTINGS],
         "CHARACTER_INFO")
    send(AUTH_SMSG_ACCOUNT_SETTINGS, [req_id, b""], "ACCOUNT_SETTINGS")
    send(AUTH_SMSG_FRIEND_STREAM_END, [req_id, req_id], "FRIEND_STREAM_END")
    send(AUTH_SMSG_ACCOUNT_INFO, [
        req_id,
        0,                                        # territory: America
        4,                                        # language
        bytes.fromhex("0100000000000000"),        # campaigns owned, bit0 Prophecies
        b"\x00" * 8,                              # unknown  [low confidence]
        bytes(user_id_wire),                      # account uuid, echoed back
        TEST_CHAR_UUID,                           # current character
        8,                                        # unknown  [low confidence]
        bytes.fromhex("0100040057000100"),        # feature/slot bits
        # The EULA revision this account has ALREADY ACCEPTED (not a bool, not the
        # current revision). The client shows its EULA dialog when this is below its own
        # current revision, and blocks entry to the world until the user clicks Accept.
        # OBSERVED: the client's current revision is 26 -- it sends ACCEPT_EULA [_, 26]
        # when a user accepts (captures 2026-08-05). We were sending 24, one bump stale
        # (the 2026-08-04 client update), so the dialog fired every launch. Sending 26 --
        # "this account is current on the EULA" -- is both the accurate value and what
        # lets an automated loopback run reach the map. On a live run the human accepts
        # ArenaNet's real EULA; this field is only our own server's answer.
        26,                                       # EULA revision accepted [OBSERVED: current is 26]
        3,                                        # unknown  [low confidence]
    ], "ACCOUNT_INFO")
    send(AUTH_SMSG_REQUEST_RESPONSE, [req_id, 0], "REQUEST_RESPONSE(OK)")


def recv_exact(sock, n, rec=None):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError(f"closed with {len(buf)}/{n} bytes")
        buf += chunk
    return buf


def handle(sock, addr, keys, vault, conn_id, stop, store, allow_any):
    rec = Recorder(vault, conn_id)
    print(f"[c{conn_id}] connect from {addr[0]}:{addr[1]}", flush=True)
    rec.event("connect", peer=f"{addr[0]}:{addr[1]}")
    try:
        sock.settimeout(30)

        # ---- 1. version -------------------------------------------------
        head = recv_exact(sock, 4)
        header, = struct.unpack("<I", head)
        if header not in (AUTH_CMSG_VERSION_HEADER,) + GAME_VERSION_HEADERS:
            rec.event("bad_version_header", header=hex(header))
            print(f"[c{conn_id}] unexpected first header 0x{header:08x}", flush=True)
            return
        kind = "auth" if header == AUTH_CMSG_VERSION_HEADER else "game"
        cmsg = "AUTH_CMSG" if kind == "auth" else "GAME_CMSG"

        if kind == "auth":
            body = recv_exact(sock, 12)
            build, h8, hC = struct.unpack("<3I", body)
            print(f"[c{conn_id}] auth version: build={build} h0008={h8} h000C={hC}",
                  flush=True)
            rec.event("version", channel="auth", build=build, h0008=h8, h000C=hC)
        else:
            # 60 more bytes, measured: build, unk1, world_id, map_id, player_id,
            # then the account uuid and the character uuid we handed this client in
            # CHARACTER_INFO -- the transfer's identity, echoed back so the game
            # server can match the connection to the handoff that created it.
            body = recv_exact(sock, 60)
            (build, unk1, world_id, map_id, player_id) = struct.unpack_from("<5I", body, 0)
            account_uuid = body[20:36]
            char_uuid = body[36:52]
            tail = body[52:60]
            hC = keys["generator"]      # not carried on this channel; keep the check quiet
            print(f"[c{conn_id}] GAME version: build={build} world_id={world_id} "
                  f"map_id={map_id} player_id={player_id}", flush=True)
            print(f"[c{conn_id}]   account {wire_to_uuid(account_uuid)}", flush=True)
            print(f"[c{conn_id}]   character {wire_to_uuid(char_uuid)}", flush=True)
            rec.event("version", channel="game", build=build, unk1=unk1,
                      world_id=world_id, map_id=map_id, player_id=player_id,
                      account_uuid=wire_to_uuid(account_uuid),
                      char_uuid=wire_to_uuid(char_uuid),
                      tail=binascii.hexlify(tail).decode(),
                      header=hex(header))
        if hC != keys["generator"]:
            print(f"[c{conn_id}] NOTE client generator {hC} != our {keys['generator']}",
                  flush=True)

        # ---- 2. client seed ---------------------------------------------
        hdr = struct.unpack("<H", recv_exact(sock, 2))[0]
        if hdr != CMSG_CLIENT_SEED_HEADER:
            rec.event("bad_seed_header", header=hex(hdr))
            print(f"[c{conn_id}] expected 0x4200, got 0x{hdr:04x}", flush=True)
            return
        client_public = recv_exact(sock, 64)
        rec.event("client_seed", a=binascii.hexlify(client_public).decode())

        shared = compute_shared(client_public, keys["server_private"], keys["prime"])
        master_secret = secrets.token_bytes(20)
        seed = make_server_seed(master_secret, shared)
        sock.sendall(struct.pack("<H", SMSG_SERVER_SEED_HEADER) + seed)
        rec.event("server_seed", sent=binascii.hexlify(seed).decode())

        derived = arc4_hash(master_secret)
        c2s = ARC4(derived)
        s2c = ARC4(derived)
        state = {}
        if kind == "game":
            if MAP_OVERRIDE is not None and MAP_OVERRIDE != map_id:
                if TAPE_EVENTS is not None:
                    # --map writes state["map_id"], and under a tape NOTHING reads
                    # it: the preamble that would is skipped entirely and the map
                    # the client draws comes from the tape's own 0x0195
                    # map_file_id. Saying "sending it to N instead" here would be a
                    # lie, and on 2026-08-10 it was read as one -- the client had
                    # asked for 148, the tape declared 146, and the disagreement
                    # was the finding (studies/tape/FINDINGS.md T2). A log line
                    # that claims an effect it does not have costs more than no
                    # log line at all.
                    print(f"[c{conn_id}] client asked for map {map_id}; --map "
                          f"{MAP_OVERRIDE} is INERT under a tape (the tape's own "
                          f"0x0195 decides what loads)", flush=True)
                else:
                    print(f"[c{conn_id}] client asked for map {map_id}; "
                          f"sending it to {MAP_OVERRIDE} instead", flush=True)
                    map_id = MAP_OVERRIDE
            state["map_id"] = map_id
            state["world_id"] = world_id
            state["player_id"] = player_id
        print(f"[c{conn_id}] key exchange OK — ARC4 key {derived.hex()[:16]}…", flush=True)
        rec.event("key_exchange_ok", arc4_key=derived.hex())

        # ---- 3. decode, answer, and record ------------------------------
        smsg = "AUTH_SMSG" if kind == "auth" else "GAME_SMSG"

        # The world ticker sends from its own thread, and ARC4 is a STATEFUL
        # stream cipher: two threads interleaving inside s2c.crypt would advance
        # one keystream across two messages and produce plaintext neither end
        # could read. The lock covers crypt and sendall together, not separately.
        send_lock = threading.Lock()

        # We never write s2c CIPHERTEXT anywhere: rec.frame is only ever called
        # with 'c2s', so the .raw sidecar holds one direction. The only way to
        # reconstruct what actually went out on the wire is to replay these
        # plaintexts through a fresh ARC4 -- and that replay is correct ONLY in
        # keystream order.
        #
        # The capture line is deliberately written OUTSIDE the lock: rec.event
        # does file I/O, and holding the send lock across a disk write would
        # serialise the 20 Hz position ticker against the filesystem. The cost of
        # that choice is that the line's ARRIVAL order is not the encryption
        # order -- three threads call send() on one connection (the receive loop,
        # world_tick, and a probe), and whichever wins the lock can still lose the
        # race to rec.event. Before this counter existed, the .jsonl recorded that
        # scrambled order as if it were the wire, and a replay built from it would
        # produce a byte stream the client never saw.
        #
        # So the number is taken next to the crypt call and under the same lock:
        # it orders messages by KEYSTREAM POSITION, and survives however the lines
        # land in the file. Sort `sent` events by seq, replay, and the result is
        # the wire.
        s2c_seq = itertools.count()

        def send(opcode, values, label, quiet=False):
            blob = codec.encode(smsg, opcode, values)
            with send_lock:
                seq = next(s2c_seq)
                sock.sendall(s2c.crypt(blob))
            # quiet is for the 20 Hz position tick only: it would bury every
            # other line in the console. It still goes into the capture, because
            # "did we actually send position updates" is exactly the question a
            # movement bug needs answered.
            if not quiet:
                print(f"[c{conn_id}] s2c {label} (0x{opcode:04x}, {len(blob)}B)",
                      flush=True)
            # A GAP in seq means crypt advanced the keystream for a message whose
            # plaintext never reached this file -- sendall raised in between. A
            # replay must stop at the gap rather than carry on emitting bytes that
            # diverge from here to the end of the session. That failure was
            # entirely invisible before; now it leaves a hole that names itself.
            rec.event("sent", seq=seq, opcode=opcode, label=label,
                      plain=binascii.hexlify(blob).decode())

        def send_raw(blob, label, quiet=True):
            """Write PRE-FORMED plaintext through this session's keystream.

            The tape player's only door into the socket. It shares send()'s lock and
            keystream counter deliberately: ARC4 is one continuous keystream per
            direction, so a tape event and an ordinary send interleaving without the
            lock would each get half the right bytes and the client would decrypt
            neither. It records under the same `sent` kind so a tape session's
            capture reads back through replay.py exactly like any other.

            opcode is read from the blob rather than passed, because a tape carries
            whole messages we never encoded and may not have a name for -- which is
            the point of a tape: it needs no semantics.
            """
            op = int.from_bytes(blob[:2], "little") if len(blob) >= 2 else -1
            with send_lock:
                seq = next(s2c_seq)
                sock.sendall(s2c.crypt(blob))
            if not quiet:
                print(f"[c{conn_id}] s2c {label} ({len(blob)}B)", flush=True)
            rec.event("sent", seq=seq, opcode=op, label=label,
                      plain=binascii.hexlify(blob).decode())

        if kind == "game" and TAPE_EVENTS is not None:
            # A TAPE IS THE WHOLE GAME CHANNEL, from the first byte after the
            # handshake. Not the load sequence minus our preamble, and not the
            # tape plus our world tick: the recording ALREADY CONTAINS its own
            # INSTANCE_LOAD_HEAD / PLAYER_DATA_START / INSTANCE_LOAD_PLAYER_NAME /
            # INSTANCE_LOAD_INFO and its own ticks, so anything we add is a second
            # server talking over the first.
            #
            # THIS WAS WRONG ON THE FIRST RUN AND IT INVALIDATED THE RESULT. The
            # c2s dispatch was gated but this setup burst and the world_tick thread
            # were not, so the 2026-08-10 run sent 378 messages of our own -- the
            # five-message load preamble at t=0.02s and 373 WORLD_SIMULATION_TICKs
            # from t=2.8s to t=21.6s -- interleaved into ArenaNet's recording. The
            # client then asserted on
            #     !m_timeStopMovement || ((int)(m_timeStopMovement - time) >= 0)
            #     AgAgent.cpp(978)
            # and that assert is about the MIXTURE. It cannot be attributed to
            # either server, which is exactly what the comment on the c2s gate
            # claimed this design prevented. Two servers' ticks arriving at one
            # client is a fine way to produce a movement time in the past.
            #
            # So: no preamble, no world tick, no probe. The tape starts here,
            # where our own first byte would have gone.
            print(f"[c{conn_id}] TAPE MODE: this server sends nothing of its own",
                  flush=True)

            def _tape_then_labels():
                # Sequential on ONE thread on purpose. A labelled run started
                # concurrently would prompt the operator while the recording still
                # moves their avatar, and every attribution would be against a
                # world neither of them controls. The tape has to be over first --
                # and note it is over 146 s AFTER it looks over on the Lakeside
                # tape (studies/tape/FINDINGS.md T7), which is exactly why this
                # waits on play_tape returning rather than on the operator's
                # judgement.
                if LABEL_RUN:
                    # Say this BEFORE the tape, not after. The operator's first
                    # question on 2026-08-10 was whether the client acting on its
                    # own meant something had gone wrong, and the honest answer --
                    # "that is the recording, sit still for three minutes" -- was
                    # only written down in the runbook. A thing the operator has to
                    # remember is a thing the tool failed to say.
                    print(f"\n[c{conn_id}] The tape plays FIRST: "
                          f"{TAPE_INFO['seconds']:.0f}s. Your character will move on "
                          f"its own -- that is the recording, not you.\n"
                          f"[c{conn_id}] DO NOTHING until this window says the "
                          f"labelled run has started. It will say so clearly.\n"
                          f"[c{conn_id}] NOTE the avatar stops moving well before the "
                          f"tape ends, and that is not the end.\n", flush=True)
                finished = play_tape(send_raw, conn_id, stop, TAPE_EVENTS,
                                     TAPE_INFO, TAPE_SPEED)
                # Hang up if the tape handed the client somewhere else. See
                # close_after_transfer: the client DEFERS a second transfer while it
                # still holds a game connection, so holding the socket open is what
                # left hop 3 on a loading screen with the right address on it.
                if finished and not LABEL_RUN and close_after_transfer(
                        sock, TAPE_EVENTS, codec, conn_id):
                    return
                if not LABEL_RUN or stop.is_set():
                    return
                if not finished:
                    # The tape ended early: the client dropped, asserted, or the
                    # session was torn down. Prompting a human through 18 steps
                    # against a dead socket produces a capture that LOOKS like a
                    # labelled run and contains nothing the operator did -- which
                    # is worse than no run, because it would be analysed.
                    print(f"[c{conn_id}] the tape did not finish, so the labelled "
                          f"run is NOT starting. Nothing to label: the client is "
                          f"gone.", flush=True)
                    return
                if rec.closed:
                    # Same defence one layer down. OBSERVED 2026-08-10: a NameError
                    # in session.py tore the stack down mid-run, the connection
                    # handler closed this recorder, and the label run then died on
                    # `I/O operation on closed file` -- a confusing second traceback
                    # stacked on top of the real one.
                    print(f"[c{conn_id}] the capture is closed, so the labelled run "
                          f"is NOT starting -- its marks would go nowhere.",
                          flush=True)
                    return
                labelrun.run(rec, conn_id, stop, steps=LABEL_RUN)

            threading.Thread(target=_tape_then_labels, daemon=True).start()

        elif kind == "game":
            # 0x31 | Prophecies(2) | Factions(4) | Nightfall(8) = 0x3F, straight
            # from OpenTyria. Unlocking everything is wrong for a level 1 pre-Searing
            # character but is the permissive choice while we are still learning
            # which of these the client validates.
            send(GAME_SMSG_INSTANCE_LOAD_HEAD, [0x3F, 0x3F, 0, 0],
                 "INSTANCE_LOAD_HEAD")
            # START and DONE are a matched pair bracketing one player's data.
            # Sending START at bring-up and DONE only in reply to REQUEST_PLAYERS
            # deadlocked: the client waits for the terminator before advancing,
            # and REQUEST_PLAYERS is how it advances. It sat for 39.8s and then
            # tore down both channels at once -- a timeout, not a rejection.
            send(GAME_SMSG_INSTANCE_PLAYER_DATA_START, [], "PLAYER_DATA_START")
            send(GAME_SMSG_INSTANCE_LOAD_PLAYER_NAME, [TEST_CHAR_NAME],
                 "INSTANCE_LOAD_PLAYER_NAME")
            send(GAME_SMSG_INSTANCE_PLAYER_DATA_DONE, [], "PLAYER_DATA_DONE")
            # is_explorable is the client's own town-versus-field switch, and
            # Guild Wars refuses to let you attack anything in a town. It is
            # cheaper to flip than to recover a real explorable's map file id,
            # which is what studies/enemy/PLAN.md section 7.3 would otherwise
            # require. Off by default because a town is what map 148 IS, and a
            # server that lies about its own map should do so only when asked.
            #
            # "This one field may be all that stands between us and testing
            # combat" used to end that paragraph. REFUTED 2026-08-11 by our own
            # wire (PLAN.md 10.6): TEN of the nineteen sessions in which the
            # client never sent ATTACK had is_explorable = 1 here, and together
            # they produced 80 x 0x0033 and zero 0x0026. The transmit gate this
            # field feeds -- 0x00816090, which refuses unless MissionCliGetMap()
            # == MISSION_MAP_GAME -- was OPEN in all ten and changed nothing, so
            # the client's world-action switch chose a non-attack arm on its own.
            # Still worth setting for any combat test, but only so a silent drop
            # at the send leaf cannot be confused with the switch's choice.
            send(GAME_SMSG_INSTANCE_LOAD_INFO,
                 [1,          # agent_id -- the player's own agent, 1 for the first
                  map_id,     # echoed from the version frame, not guessed
                  # The map's own kind, not a global switch. The client's
                  # AreaInfo type says which is which -- 2 explorable, 10
                  # outpost -- and MAP_STATIC_CONFIG carries that per map.
                  # --explorable still forces it on for maps we have not
                  # configured, which is what it was added for.
                  1 if (EXPLORABLE or map_explorable(state["map_id"])) else 0,
                  0,          # district
                  0,          # language
                  0],         # is_observer
                 "INSTANCE_LOAD_INFO"
                 + (" [is_explorable=1, FORCED]" if EXPLORABLE else ""))

            spawn = MAP_STATIC_CONFIG.get(state["map_id"],
                                          MAP_STATIC_CONFIG[FALLBACK_MAP_ID])
            state["pos"], state["plane"], state["dest"] = spawn[1], spawn[2], None
            # We placed the character here, so this position is known, not stale.
            state["pos_seen"] = time.time()
            state["pathmap"] = load_pathmap(spawn[0])

            def world_tick():
                """Walk the agent toward its destination and say where it got to.

                Guild Wars puts the server in charge of position: the client asks
                to go somewhere and then believes whatever it is told. With no
                tick it asked, waited about two seconds for a position that never
                arrived, cancelled, and reported itself back at the spawn point.
                """
                prev_tick = time.perf_counter()
                while not stop.is_set():
                    time.sleep(TICK_SECONDS)
                    # Advance the client's simulation clock FIRST, every tick,
                    # whether or not anyone is moving -- that is what upstream
                    # does, and it is unconditional there.
                    #
                    # Measured symptom this is aimed at (2026-08-05 capture): the
                    # client predicts a walk for about 125 units and then freezes
                    # at a fixed position while still sending input, jerking
                    # forward only when a teleport arrives. A client that cannot
                    # advance its own clock cannot animate past its first guess.
                    now = time.perf_counter()
                    delta_ms = int((now - prev_tick) * 1000)
                    if delta_ms > 0:
                        prev_tick = now
                        try:
                            # quiet: 20 of these a second would bury the log.
                            send(GAME_SMSG_WORLD_SIMULATION_TICK, [delta_ms],
                                 "WORLD_SIMULATION_TICK", quiet=True)
                        except OSError:
                            return
                    # Anything the world owes on a timer goes here. Bodies get
                    # back up whether or not the player is moving, so this must
                    # be above the destination check that skips the rest.
                    try:
                        attack_tick(send, state, conn_id)
                        revive_due(send, state, conn_id)
                        # The third sweep, and the first that mutates state["agents"]
                        # on a schedule rather than only when the player acts. Last,
                        # so a body that died this tick is seen dead by burrow_tick
                        # and stays put -- a dead agent does not burrow.
                        burrow_tick(send, state, conn_id)
                    except OSError:
                        return
                    except AgentLifetimeError as ex:
                        # Loud, and it does not kill the tick. This runs on a daemon
                        # thread: an escaping exception here silently stops the world
                        # for the rest of the session, and the client just goes still.
                        print(f"[c{conn_id}] WORLD TICK: {ex}", flush=True)

                    dest = state.get("dest")
                    if not dest:
                        continue
                    px, py = state["pos"]
                    dx, dy = dest[0] - px, dest[1] - py
                    dist = math.hypot(dx, dy)
                    step = DEFAULT_RUN_SPEED * TICK_SECONDS
                    arrived = dist <= step
                    if arrived:
                        state["pos"], state["dest"] = dest, None
                        # The leg is over, so the next keyboard report must issue
                        # a fresh MOVE_TO_POINT even if the player never turned.
                        state["walking"] = False
                    else:
                        state["pos"] = (px + dx / dist * step,
                                        py + dy / dist * step)
                    # NOTHING IS BROADCAST FROM HERE. This integrator is the
                    # server's own opinion about where the character is, and it
                    # is the weaker of the two opinions available.
                    #
                    # It used to announce arrivals. MEASURED on the wall-hugging
                    # session: five AGENT_UPDATE_POSITION went out and three were
                    # arrivals, carrying the client 630, 189 and 765 units. That
                    # last figure is exactly one heading vector -- our integrator
                    # had run the whole leg while the client had not moved at
                    # all, because the client's own collision stopped it
                    # somewhere our navmesh says is open. We then told it that
                    # our position was the truth.
                    #
                    # That is the warp the player described: not a snap, a WALK.
                    # A client sent to a position appears to path there in a
                    # straight line over a couple of seconds, straight over
                    # buildings, because a server-granted position is not
                    # something it re-collides against.
                    #
                    # Since we adopt the client's reported position four times a
                    # second, our arrival opinion is redundant even when right.
                    # Keep integrating -- the server needs a position model for
                    # everything that is not a player -- and stop arguing.

            # NOT under a tape: our 20 Hz ticker talking over ArenaNet's recording
            # is what made the first run's client assert un-attributable.
            if TAPE_EVENTS is None:
                threading.Thread(target=world_tick, daemon=True).start()

        sock.settimeout(1.0)
        total = 0
        pending = b""          # decrypted bytes not yet framed into whole messages
        desynced = False       # set when an unframeable opcode ends the connection
        last = time.time()
        while not stop.is_set():
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                if time.time() - last > 120:
                    break
                continue
            if not chunk:
                break
            last = time.time()
            plain = c2s.crypt(chunk)
            total += len(chunk)
            rec.frame("c2s", chunk, plain)

            # A TCP read is not a message boundary: a read may carry several
            # messages, or half of one. Carry the remainder forward rather than
            # decoding per-read, which would drop the tail of every split message.
            pending += plain
            # The client declares its own channel in the version header, so the
            # catalog self-selects: run a second instance on 6113 and it decodes
            # the game channel with no extra flag. GAME_CMSG_MASK is also 0x8000,
            # so the framing is identical -- only the catalog differs.
            msgs, pending, desync_err = frame_pending(
                codec, cmsg, pending, AUTH_CMSG_MASK)

            for opcode, values in msgs:
                # No semantic names exist for GAME_CMSG in this repo yet; the
                # schema knows shapes only. Printing "?" is the honest answer
                # rather than borrowing an auth name that means something else.
                # GAME_CMSG names now come from schema/overrides.json, where each one
                # sits beside the labelled run that earned it. Until 2026-08-10 this
                # printed "?" for every game-channel message because the catalog had
                # 194 layouts and no names -- which made every c2s log line in this
                # project unreadable, and is why the labelled run exists at all.
                # Anything still unnamed prints "?" rather than borrowing a name from
                # the auth catalog, where the numbers collide and mean other things.
                name = (AUTH_CMSG_NAMES.get(opcode, "?") if kind == "auth"
                        else codec.name_for("GAME_CMSG", opcode))
                if labelrun.ACTIVE:
                    # A labelled run owns this terminal: the operator is reading a
                    # countdown in it, and one movement step prints tens of lines a
                    # second straight through it. Count instead of print -- the
                    # count is better feedback anyway, because it tells them their
                    # key press actually reached the server. The message is still
                    # recorded below; only the echo is suppressed.
                    labelrun.SEEN[0] += 1
                else:
                    print(f"[c{conn_id}] c2s 0x{opcode | AUTH_CMSG_MASK:04x} {name}",
                          flush=True)
                rec.event("decoded", opcode=opcode, name=name,
                          values=[v.hex() if isinstance(v, bytes) else v
                                  for v in values])

                if kind == "game":
                    if TAPE_EVENTS is not None:
                        # The tape started at connection setup and IS the whole
                        # channel. Client c2s is still framed here -- so a desync
                        # still closes the connection -- and still recorded, but
                        # nothing of ours may answer it.
                        continue
                    if opcode == GAME_CMSG_INSTANCE_LOAD_REQUEST_ITEMS:
                        # OpenTyria's full REQUEST_ITEMS burst, in its order.
                        # Sending only the tail of it made the client accept every
                        # message and then reset without asking for players or
                        # spawn -- READY_FOR_MAP_SPAWN is the LAST of these, not a
                        # shortcut to the end.
                        # Skipped: inventory, max factions and hard mode. Those
                        # need player state we do not model yet; if the client
                        # stalls again they are the next candidates.
                        send(GAME_SMSG_ITEM_STREAM_CREATE, [1, 0],
                             "ITEM_STREAM_CREATE")
                        # The item has to exist before a weapon set can name it,
                        # and upstream sends inventory before the slots for that
                        # reason. CREATE_NAMED_ITEM only DECLARES the bytes --
                        # it puts nothing in a bag and nothing in a hand.
                        if EQUIP_WEAPON:
                            send(GAME_SMSG_CREATE_NAMED_ITEM,
                                 agents.named_item(WEAPON_ITEM_ID,
                                                   agents.STARTER_HAMMER),
                                 "CREATE_NAMED_ITEM(starter hammer)")
                            # Rendering a weapon and EQUIPPING one are not the
                            # same thing, and we had only done the first. The
                            # bag was skipped on purpose to answer an open
                            # question in studies/character/FINDINGS.md -- does
                            # 0x006E draw with no bag behind it? -- and the
                            # answer is yes, OBSERVED: the hammer appeared in
                            # hand with no bag at all.
                            #
                            # But the client then asserted on m_attackInterval
                            # the moment an attack was meant to animate, so the
                            # weapon it was drawing had no attack speed. An
                            # item that is in no bag and no slot is not worn by
                            # anything, which was the obvious candidate for why.
                            # Field order follows GmInventory.c:174-182 and
                            # :145-152 exactly.
                            #
                            # IT WAS NOT WHY, and this stays only because it is
                            # more correct than not sending it. TESTED
                            # 2026-08-06, probe `attack_anim`: with the hammer
                            # in the bag AND the slot AND the weapon set AND on
                            # the body, the client still died on the same
                            # assert at the same line -- m_attackInterval,
                            # AvChar.cpp(4791). Nothing we know how to equip
                            # sets +0xEC. The crash chain is nineteen frames of
                            # AgentView, so the field is plausibly on the
                            # client's view-layer AvChar rather than on the
                            # agent every search so far has scanned.
                            # studies/enemy/PLAN.md 6p.
                            send(GAME_SMSG_INVENTORY_CREATE_BAG,
                                 [1, BAG_TYPE_EQUIPPED, BAG_MODEL_EQUIPPED,
                                  EQUIPPED_BAG_ID, EQUIPPED_SLOT_COUNT, 0],
                                 "INVENTORY_CREATE_BAG(equipped)")
                            send(GAME_SMSG_ITEM_MOVED_TO_LOCATION,
                                 [1, WEAPON_ITEM_ID, EQUIPPED_BAG_ID,
                                  EQUIPPED_SLOT_WEAPON],
                                 "ITEM_MOVED_TO_LOCATION(hammer -> equipped 0)")
                        send(GAME_SMSG_ITEM_SET_ACTIVE_WEAPON_SET, [1, 0],
                             "SET_ACTIVE_WEAPON_SET")
                        for slot in range(4):
                            # Slot 0 is the active set (SET_ACTIVE_WEAPON_SET
                            # above selects it). leadhand is the main hand; a
                            # hammer is two-handed, so offhand stays empty.
                            lead = (WEAPON_ITEM_ID
                                    if EQUIP_WEAPON and slot == 0 else 0)
                            send(GAME_SMSG_ITEM_WEAPON_SET, [1, slot, lead, 0],
                                 f"WEAPON_SET[{slot}]"
                                 + (f" leadhand={lead}" if lead else ""))
                        send(GAME_SMSG_UPDATE_GOLD_STORAGE, [1, 0],
                             "UPDATE_GOLD_STORAGE")
                        send(GAME_SMSG_CHARACTER_UPDATE_INFO,
                             ["", 0, 0, 1000, 0, 0, 0], "CHARACTER_UPDATE_INFO")
                        send(GAME_SMSG_MAP_UPDATE_CURRENT, [state["map_id"], 0],
                             "MAP_UPDATE_CURRENT")
                        send(GAME_SMSG_READY_FOR_MAP_SPAWN, [0],
                             "READY_FOR_MAP_SPAWN")
                        # GameSrv_SendDownloadManifest: two PHASE messages then a
                        # DONE, twice. The DONE is not optional decoration -- it
                        # is what closes each pair, and omitting it left the
                        # client mid-manifest. First round carries the "no map"
                        # sentinel, second round the real destination.
                        for phase_arg, map_arg in ((MANIFEST_DONE, MAP_ID_COUNT),
                                                   (MANIFEST_PHASE1, state["map_id"])):
                            send(GAME_SMSG_INSTANCE_MANIFEST_PHASE,
                                 [MANIFEST_PHASE1], "MANIFEST_PHASE[Phase1]")
                            send(GAME_SMSG_INSTANCE_MANIFEST_PHASE,
                                 [MANIFEST_PHASE2], "MANIFEST_PHASE[Phase2]")
                            send(GAME_SMSG_INSTANCE_MANIFEST_DONE,
                                 [phase_arg, map_arg, 0],
                                 f"MANIFEST_DONE[{phase_arg}, map {map_arg}]")
                    elif opcode in (GAME_CMSG_USE_SKILL, GAME_CMSG_ATTACK_SKILL):
                        # ONE ARM FOR BOTH, deliberately. 0x0046 and 0x0027 are the
                        # caster and attack-skill halves of the same action: their
                        # payloads line up slot for slot and ArenaNet's own server
                        # answers both with GAME_SMSG 0x00E3 (see the constants).
                        # Two arms would drift, and until 2026-08-11 this server
                        # had only the caster half -- so every physical attack
                        # skill fell through to the silent-ignore path, where per
                        # studies/divergence D9(b) a schema-unknown c2s opcode also
                        # DISCARDS whatever shared its TCP read. That made it a
                        # correctness bug and not just a missing feature.
                        #
                        # Confirm the cast by echoing the key the client is
                        # waiting on. If the echo is wrong the client says so in
                        # its own log -- 'Pending skill %u copy %d not found' --
                        # which makes this one of the few things in the project
                        # that reports its own failure.
                        which = ("USE_SKILL" if opcode == GAME_CMSG_USE_SKILL
                                 else "ATTACK_SKILL")
                        skill_id, copy, target = values[1], values[2], values[3]
                        send(GAME_SMSG_SKILL_ACTIVATED,
                             [PLAYER_AGENT_ID, skill_id, copy],
                             f"SKILL_ACTIVATED(skill {skill_id}, copy {copy}"
                             f" via {which})")
                        print(f"[c{conn_id}] skill {skill_id} (copy {copy}) at "
                              f"agent {target or 'nothing'}", flush=True)
                        # TRIED AND IT DID NOT WORK, recorded so it is not
                        # retried blind: sending generic values 60
                        # (skill_activated) then 58 (skill_finished) here left
                        # the cast exactly as stalled as before. They may still
                        # be part of the answer -- they were never going to be
                        # all of it -- but on their own they change nothing
                        # visible, so they are out rather than sitting in the
                        # code looking like they work. agents.py keeps the ids.
                        #
                        # Skill completion is being worked on a separate branch.
                        # Do not build more of it here.
                        # A skill aimed at something hostile does what a click
                        # does. Whether a skill should damage at all, and by how
                        # much, is OURS -- the client carries every real number
                        # (studies/skills/FINDINGS.md) and we do not read it yet.
                        if target:
                            hit_enemy(send, state, target, conn_id)
                    elif opcode in (GAME_CMSG_ATTACK_AGENT,
                                    GAME_CMSG_INTERACT_PLAYER):
                        # The player clicked something. Clicking a hostile
                        # agent ORDERS an attack; the tick does the swinging.
                        # See ATTACK_INTERVAL for why this is server-driven and
                        # why that is a workaround, not the mechanism.
                        #
                        # ONE ARM FOR BOTH, and the two are NOT synonyms -- they
                        # are arms 0 and 1 of the client's own world-action
                        # switch, and which one arrives says what the client
                        # resolved the click to. Sharing an arm is honest only
                        # because our answer to both is currently the same one
                        # (swing at it); the day interaction means anything
                        # other than combat, 0x0033 has to split back out.
                        # values[1] is the target agent id in both layouts.
                        begin_attack(send, state, values[1], conn_id)
                    elif opcode == GAME_CMSG_TURN_TO_DIRECTION:
                        # Keyboard movement comes through here, not through
                        # MOVE_TO_COORD: WASD sends a HEADING from where you
                        # stand, while clicking sends an absolute destination.
                        # That is why click-to-move worked and WASD did not --
                        # we treated this as a pure turn and did nothing.
                        # values[4] is an ENUM, not a flag: measured values were 1
                        # and 4, never 0 (analyze_movement.py, 167 samples across
                        # two sessions). GWLP-R calls the field movementType.
                        # Testing it for truthiness happens to work because 0
                        # never appears, but do not read "moving" into it.
                        #
                        # values[3] is a fixed-magnitude direction -- |v| was
                        # 765-768 in every sample whichever way the player faced.
                        # So pos + heading is a leg about 2.6 seconds of running
                        # ahead, which is why this worked at all.
                        plane, heading = values[2], values[3]
                        moving = values[4] if len(values) > 4 else 0
                        state["plane"] = plane
                        # BELIEVE SLOT 1. The client reports where it actually is
                        # in the same packet as where it wants to go, four times
                        # a second, and MEASURED it advances at 211 units/sec
                        # over 120 samples -- it is a live position, not a stale
                        # echo. Read the pair as "I am here, and I want to go
                        # there"; computing the leg from OUR position was always
                        # the approximation.
                        #
                        # Why this matters more since collision landed: our
                        # integrator stops dead at a wall while the client slides
                        # along it, and measured drift at each stop went to a
                        # median of 538 units and a maximum of 1,429. Every leg
                        # we then issued was an ABSOLUTE destination computed
                        # from a position a third of a map behind the player, so
                        # the client walked backwards to reach it. That is the
                        # rubber-banding -- MOVE_TO_POINT carrying our error, not
                        # any teleport message. Suppressing AGENT_UPDATE_POSITION
                        # was correct and did not touch it.
                        #
                        # An early attempt at believing this slot pinned the
                        # character to spawn. That was a different situation, not
                        # a warning against this one: back then we sent no
                        # keyboard MOVE_TO_POINT at all, so the client never
                        # animated, reported spawn forever, and we copied it. The
                        # client moves itself now, which is precisely what makes
                        # its report worth having.
                        reported = tuple(values[1])
                        if _adopt_client_position(state, reported):
                            state["pos"] = reported
                            state["pos_seen"] = time.time()
                        if moving:
                            px, py = state["pos"]
                            # Answer with a DIRECTION. See the comment on
                            # GAME_SMSG_AGENT_MOVE_DIRECTION for why, and for how
                            # the opcode was identified.
                            #
                            # Everything the clip was doing on this path is gone
                            # with it. There is nothing to clip -- we are not
                            # naming a point, so we cannot name one past a wall
                            # or one behind the player. The client walks that way
                            # until it hits something, colliding for itself the
                            # whole time, which is what it was always going to do
                            # better than we can.
                            #
                            # Only on a real change of direction. This opcode
                            # arrives several times a second and GWLP-R sends
                            # ChangeDirection only when the direction changes; a
                            # heading that has not changed needs no restating.
                            prev = state.get("heading")
                            if prev is None:
                                turned = True
                            else:
                                dot = heading[0] * prev[0] + heading[1] * prev[1]
                                mags = (math.hypot(*heading) * math.hypot(*prev))
                                # cos(5 degrees); mags is never 0 here in practice
                                turned = mags <= 0 or dot < 0.996 * mags
                            state["heading"] = tuple(heading)
                            # Our own position model still walks a clipped leg, so
                            # the server keeps an opinion that respects walls. It
                            # goes nowhere near the wire.
                            model_dest, blocked = clip_to_walkable(
                                state, (px + heading[0], py + heading[1]))
                            state["dest"], state["clipped"] = model_dest, blocked
                            if turned or state.get("walking") is not True:
                                state["walking"] = True
                                send(GAME_SMSG_AGENT_MOVE_DIRECTION,
                                     [PLAYER_AGENT_ID, list(heading), moving],
                                     f"AGENT_MOVE_DIRECTION"
                                     f"({heading[0]:.0f},{heading[1]:.0f} "
                                     f"type {moving})")
                    elif opcode == GAME_CMSG_MOVE_TO_COORD:
                        # Granting the move is not the same as performing it.
                        # The server owns position: it walks the agent along and
                        # reports where it got to. Answering MOVE_TO_POINT and
                        # then never moving anyone is why the client cancelled
                        # after ~2s and reported itself still at the spawn point.
                        dest = values[1]
                        # Slot 2 is the DESTINATION's plane. The client works out
                        # which surface was clicked -- it rendered them -- and
                        # tells us.
                        #
                        # MEASURED over 195 clicks, by testing the two readings
                        # against each other rather than by analogy: 70 had slot
                        # 2 matching the destination's plane and NOT the player's,
                        # against 11 the other way round. The clear cases leave
                        # nothing to argue with -- player on plane 0 clicks a
                        # point whose only trapezoid plane is 5 and slot 2 is 5;
                        # player on 5 clicks a point on 0 and slot 2 is 0.
                        #
                        # An earlier version read this as the CURRENT plane,
                        # because slot 2 does hold the current plane in 0x003D and
                        # 0x0047. That analogy was weak exactly where it mattered:
                        # 112 of the 195 clicks were same-plane, where both
                        # readings agree and neither is tested.
                        #
                        # THIS IS THE STAIRS. Clicking a staircase sends the
                        # stairs' plane, and answering "you are staying on the
                        # plane you are on" walks the player along the ground
                        # underneath instead of up the steps -- reported from play
                        # as ending up inside the hollow under the stairs.
                        dest_plane = values[2]
                        # The second field overwrites the client's own current
                        # plane, so a stale value here corrupts the thing the
                        # client collides against. READ OUT OF Gw.exe:
                        #
                        #   handler 0x005fd890 builds {x, y, FIRST word, 0} and
                        #   calls 0x00602a40(agent, &pos, 0, SECOND word)
                        #   0x00602a40:  cmp eax, -1 / je / mov [ebx+0x80], eax
                        #
                        # and the agent's own position is {x @0x78, y @0x7c,
                        # plane @0x80} -- the function passes `lea esi, [ebx+
                        # 0x78]` to the movement starters. So field 2 IS the
                        # agent's current plane, as OpenTyria names it.
                        #
                        # -1 means "leave it alone" and we CANNOT say it: the
                        # field is msgtable type 4, "unsigned, widened to a
                        # 4-byte slot", so 0xFFFF arrives as 65535, not -1. Four
                        # of the eight internal callers of 0x00602a40 push -1;
                        # that idiom is not available over the wire.
                        #
                        # So it has to be right. Our tracked plane comes from
                        # 0x003D and 0x0047, and MEASURED, the client sends
                        # neither while click-moving -- which is precisely when
                        # this field is used. The navmesh is the better source,
                        # since its plane indices ARE the client's numbering
                        # (189 of 198 reports agree).
                        # The client's own reported plane, unmodified.
                        #
                        # This used to be second-guessed with pm.plane_at(), which
                        # was added when our position could be stale. It cannot be
                        # any more -- a click is only answered when a report is
                        # under a second old (below), and the messages that carry
                        # the position carry the plane with it. So the navmesh
                        # override now runs ONLY when the client has just told us
                        # the answer, and it can overrule a correct one.
                        #
                        # It overrules it in exactly the wrong place. plane_at
                        # falls back to the geometry when the reported plane is
                        # not among the trapezoids covering the point, and
                        # MEASURED, that is 9 of 198 reports, every one of them
                        # "client says 12, we find 0" -- a surface and the ground
                        # under it, in a file with no height. Stairs. Which is
                        # where the last of the warping was still being seen.
                        cur_plane = state["plane"]
                        # FIELD ORDER: destination plane FIRST, current plane
                        # SECOND. The two lineages disagree here and we had been
                        # following the wrong one.
                        #
                        #   OpenTyria GameMsg.h:538   uint16 plane          <- dest
                        #                             uint16 current_plane
                        #     and GmAgent.c fills them
                        #       msg->plane         = agent->destination.plane
                        #       msg->current_plane = agent->position.plane
                        #
                        #   GWLP-R P030               int currentPlane      <- first
                        #                             int nextPlane
                        #
                        # OpenTyria defines this message as 0x0029, the same
                        # opcode our build uses. GWLP-R's is 30, from a different
                        # build era, and its AgentMoveDirection semantics -- which
                        # ARE verified against our client -- do not make its field
                        # order here authoritative too.
                        #
                        # Sending them the wrong way round told the client it was
                        # standing on the plane it was trying to reach, and to
                        # walk to the plane it was standing on. Click a staircase
                        # and we sent (0, 12): "you are on the stairs, go to the
                        # ground". The player fell through the stairs to the floor
                        # below, which is what was reported from play. MEASURED
                        # that this fired constantly -- 55 of 55 clicks in one
                        # session announced a plane change, because planes are
                        # connected regions of walkable surface, not floors, and
                        # Kamadan has 39 of them.
                        #
                        # No zeroing. OpenTyria sends the destination's plane
                        # unconditionally; GWLP-R's "0 if the player stays in the
                        # same plane" belongs to its own field ordering and is not
                        # carried over.
                        plane_first, plane_second = dest_plane, cur_plane
                        sweep_note = ""
                        if CLICK_SWEEP:
                            i = state.get("click_n", 0)
                            state["click_n"] = i + 1
                            label, fn = CLICK_SWEEP_VARIANTS[
                                i % len(CLICK_SWEEP_VARIANTS)]
                            plane_first, plane_second = fn(cur_plane, dest_plane)
                            sweep_note = (f"  <<< CLICK #{i + 1} "
                                          f"variant {i % len(CLICK_SWEEP_VARIANTS) + 1}"
                                          f"/{len(CLICK_SWEEP_VARIANTS)}: {label} "
                                          f"-> sent ({plane_first}, {plane_second})")
                        # Deliberately NOT state["plane"] = dest_plane. Our idea
                        # of the player's plane comes from 0x003D and 0x0047,
                        # which report where the client IS. Recording a
                        # destination's plane as the player's own was a second bug
                        # stacked on the first.
                        # A click ends whatever keyboard leg was running, so drop
                        # the remembered heading: the next key press must be
                        # treated as a fresh direction, not compared against one
                        # from before the click.
                        state["walking"], state["heading"] = False, None
                        # Grant the click exactly as asked. Nothing here second
                        # guesses the player.
                        #
                        # Two inventions of ours lived here and both are gone: a
                        # destination clipped to the first wall, and a refusal to
                        # answer at all when there was little clear ground. Those
                        # produced "click past a wall and end up at some spot
                        # near where the navmesh stops", which is not how the
                        # game behaves. A real server ROUTES you around the
                        # obstacle. We cannot do that -- the pathfinding graph in
                        # the map file is not decoded -- and between two things
                        # we cannot do, the honest one is the one that does not
                        # invent a destination the player never chose.
                        #
                        # Whether this phases through walls is now an OPEN
                        # question rather than a settled one. The test that
                        # showed phasing when the clip came off had keyboard
                        # movement on MOVE_TO_POINT as well, so it could not
                        # separate the two paths. Keyboard is a direction now, so
                        # a playtest finally isolates clicking.
                        #
                        # Click is also where our position model is blindest:
                        # MEASURED, the client sends NO position while
                        # click-moving. 0x003E carries a destination and a plane
                        # and nothing else, and one capture ran 37 seconds
                        # without the client saying where it was.
                        # ANSWER ONLY WHEN THERE IS NOTHING TO OVERWRITE.
                        #
                        # THE CLIENT PATHS CLICKS BY ITSELF. Caught in play with
                        # screenshots: the player clicked a spot up a staircase,
                        # the character set off correctly towards the FOOT of the
                        # stairs -- a real route, around the railing -- and about
                        # a second later snapped onto a straight line aimed at the
                        # clicked point, straight through the railing. That is our
                        # MOVE_TO_POINT landing on top of a path the client had
                        # already worked out.
                        #
                        # So every click we answered replaced a correct path with
                        # a worse one, and the clip made it worse still, because a
                        # clipped point sits on the straight line the client was
                        # not going to take.
                        #
                        # A real server owns pathing and would send the legs of
                        # the route. We cannot: the pathfinding graph in the map
                        # file is decoded only as far as its sub-record sizes. The
                        # honest substitute is to stay out of the way when the
                        # client has real work to do, and confirm only the trivial
                        # case where the straight line IS the route.
                        # AND ONLY WHEN WE KNOW WHERE THE PLAYER IS.
                        #
                        # The second plane field is written straight into the
                        # agent's own current plane (agent+0x80, read out of
                        # Gw.exe), and we have to fill it because -1, the client's
                        # own "leave it alone" value, is unreachable from an
                        # unsigned wire field. So a stale answer there is not a
                        # missed opportunity, it is active corruption of the plane
                        # the client resolves its position against.
                        #
                        # And stale is the normal state during click-to-move:
                        # MEASURED, the client sends no position at all while
                        # click-moving, so after one deferred click our position
                        # is frozen wherever the player was standing when they
                        # clicked. Answering a later click from there asserts
                        # "your current plane is the plane of your starting
                        # point", which is a good description of the two symptoms
                        # still reported -- a warp near stairs, and being thrown
                        # back towards where the player set off from.
                        fresh = (time.time() - state.get("pos_seen", 0.0)) <= 1.0
                        pm_c = state.get("pathmap")
                        # And only when the geometry can actually place the
                        # player: on the mesh, on exactly one plane, and that
                        # plane the one the client just named. MEASURED over 532
                        # reports -- 93.8% clean, 5.5% not on our mesh at all,
                        # 0.8% on a single plane that is not the one the client
                        # named, and 0.0% genuinely ambiguous. The trapezoids do
                        # not overlap in 2D, so the earlier guess that stairs were
                        # an ambiguity problem was wrong; they are a disagreement
                        # problem.
                        #
                        # The off-mesh 5.5% closed a real hole. clip_to_walkable
                        # gives up when our position is not on the mesh and
                        # reports the line CLEAR, so the server was answering
                        # confidently from positions whose geometry it knew
                        # nothing about.
                        here = set()
                        if pm_c is not None:
                            here = {t.plane for t in
                                    pm_c.containing(state["pos"][0], state["pos"][1])}
                        placed = here == {cur_plane}
                        blocked = not (fresh and placed)
                        if fresh and placed:
                            stop_at = pm_c.clip(state["pos"][0], state["pos"][1],
                                                dest[0], dest[1],
                                                step=COLLISION_STEP)
                            blocked = (math.hypot(stop_at[0] - dest[0],
                                                  stop_at[1] - dest[1]) > COLLISION_STEP)
                        if blocked:
                            # Something is in the way, so the client is pathing
                            # around it and knows more than we do. Say nothing,
                            # and drop our own destination rather than integrate
                            # along a line the player is not walking.
                            state["dest"], state["clipped"] = None, True
                            if not fresh:
                                why = ("we last saw the player "
                                       f"{time.time() - state.get('pos_seen', 0.0):.1f}s ago")
                            elif not placed:
                                why = (f"cannot place them -- client says plane "
                                       f"{cur_plane}, geometry says "
                                       f"{sorted(here) if here else 'off-mesh'}")
                            else:
                                why = "not a straight shot"
                            print(f"[c{conn_id}] click to ({dest[0]:.0f}, "
                                  f"{dest[1]:.0f}): {why} -- leaving it to the "
                                  f"client's own pathing", flush=True)
                            continue
                        state["dest"], state["clipped"] = (float(dest[0]),
                                                           float(dest[1])), False
                        # ArenaNet pairs the rate with the MOVE, not with the
                        # spawn: 303 of 309 0x002B in the two live captures are
                        # immediately followed by 0x0029, and the median gap
                        # from an agent's own create is 574 messages. Only 13
                        # of 309 sit inside a create burst. This server sent it
                        # at spawn time for one evening and the client asserted
                        # on AgAgent.cpp:1198 !(m_flags & MOVEMENT_STALE) as the
                        # loading screen faded -- whether that was the cause is
                        # UNVERIFIED, but the placement was wrong either way and
                        # the corpus said so before a line of it was written.
                        send(GAME_SMSG_AGENT_UPDATE_SPEED,
                             agents.agent_update_speed(PLAYER_AGENT_ID, 1.0),
                             "AGENT_UPDATE_SPEED(player, 1.0 = 288 u/s)")
                        send(GAME_SMSG_AGENT_MOVE_TO_POINT,
                             [PLAYER_AGENT_ID, list(dest), plane_first, plane_second],
                             f"AGENT_MOVE_TO_POINT({dest[0]:.0f},{dest[1]:.0f}"
                             f" on plane {cur_plane}->{dest_plane}, clear line)")
                        if sweep_note:
                            print(sweep_note, flush=True)
                    elif opcode == GAME_CMSG_LAST_POS_BEFORE_MOVE_CANCELED:
                        # Stop where WE say it is, not where the client last
                        # believed. Echoing the client's figure back pinned it to
                        # the spawn point: it reported "still at spawn" because
                        # we had not moved it, and we confirmed that was correct.
                        # Believe the client, within a tolerance, and say nothing.
                        #
                        # This is a teleport, and a teleport cancels whatever the
                        # client is animating. Sending one on every stop is the
                        # rubber-banding on sudden stops and turns: our integrator
                        # runs at DEFAULT_RUN_SPEED while the client's own walk
                        # measured ~197 units/sec, so we arrive ahead of it and
                        # then yank it forward.
                        #
                        # An earlier attempt at this same change made things far
                        # worse -- the character was pinned at spawn. That version
                        # also believed the client's position on 0x003D, four
                        # times a second, which reset the integrator before it
                        # could accumulate anything. The old comment here warned
                        # about exactly that and I read it as history. It only
                        # applies when the client is not moving itself; now that
                        # it is, its figure is the better one.
                        reported, plane = tuple(values[1]), values[2]
                        state["dest"] = None
                        state["walking"], state["heading"] = False, None
                        was_clipped = state.get("clipped")
                        state["clipped"] = False
                        px, py = state["pos"]
                        drift = math.hypot(reported[0] - px, reported[1] - py)
                        pm = state.get("pathmap")
                        # A wall makes the two models diverge legitimately. We
                        # stop dead at the clip point; the client SLIDES along
                        # the wall, which is what Guild Wars does and what our
                        # straight-line clip cannot express. So the drift after a
                        # blocked leg is the client being right and us being
                        # coarse -- correcting it is a snap backwards along the
                        # wall, which is exactly the rubber-banding reported.
                        #
                        # Believe the client instead, on one condition: that
                        # where it says it is, is somewhere the navmesh agrees
                        # you can stand. That keeps this from becoming a blanket
                        # "trust the client" that would undo the collision fix.
                        #
                        # THE SERVER NO LONGER ARGUES. Take the position and the
                        # plane, record the disagreement, send nothing.
                        #
                        # Seven corrections went out in the session that settled
                        # this, and reading them back not one was defensible:
                        #
                        #   on plane 5;  11u from ours
                        #   on plane 5;  26u from ours
                        #   off the navmesh; 26u from ours
                        #   off the navmesh;  9u from ours
                        #
                        # Teleporting a player nine units is pure damage. The
                        # plane ones were not even disagreements: we only ever
                        # learned the plane from keyboard packets, and clicking
                        # sends none, so every plane change the client made
                        # looked like a lie to us. The off-mesh ones are gaps in
                        # OUR trapezoids -- the client stops against collision
                        # geometry we have never read, and where they differ at
                        # the edges the client is the one standing there.
                        #
                        # on_mesh is still recorded, and it is a real measurement:
                        # 57 of 61 stops landed on our mesh, so the mesh is
                        # broadly right and wrong in exactly the places worth
                        # studying. It is evidence about our map data, not
                        # grounds for moving the player.
                        on_mesh = (None if pm is None
                                   else pm.walkable(reported[0], reported[1]))
                        rec.event("position_report", drift=round(drift, 2),
                                  accepted=True, reported=list(reported),
                                  ours=[px, py], plane=plane,
                                  server_plane=state["plane"],
                                  clipped=was_clipped, on_mesh=on_mesh)
                        state["pos"] = reported
                        state["plane"] = plane
                        state["pos_seen"] = time.time()
                        if on_mesh is False:
                            # Worth knowing about, not worth acting on. Every
                            # one of these is a hole in our trapezoids at a spot
                            # the client is happily standing in, which is a lead
                            # on the map format rather than a misbehaving client.
                            print(f"[c{conn_id}] off-mesh stop at "
                                  f"({reported[0]:.0f}, {reported[1]:.0f}) "
                                  f"plane {plane} -- navmesh gap, not corrected",
                                  flush=True)
                    elif opcode == GAME_CMSG_CHAR_CREATION_REQUEST_ARMORS:
                        # The client sent this and REQUEST_ITEMS in the same
                        # breath; we answered only items, and it then waited 44s
                        # and dropped both channels.
                        #
                        # This comment used to read that as cause. It OVERCLAIMS.
                        # That capture is confounded: the manifest-phase bug was
                        # live and we were sending zero simulation ticks, and four
                        # fixes shipped together. Answering this is SUFFICIENT to
                        # get through the load; that it is NECESSARY is untested.
                        # Nothing is unlocked: correct for a level 1 character,
                        # and it keeps this from masking a later stall.
                        send(GAME_SMSG_PVP_UPDATE_UNLOCKED_SKILLS, [[0] * 128],
                             "PVP_UNLOCKED_SKILLS")
                        # Heroes are all-ones in OpenTyria; kept verbatim rather
                        # than second-guessed.
                        send(GAME_SMSG_PVP_UPDATE_UNLOCKED_HEROES,
                             [[0xFFFFFFFF] * 8], "PVP_UNLOCKED_HEROES")
                        send(GAME_SMSG_PVP_ITEM_STREAM_END, [],
                             "PVP_ITEM_STREAM_END")
                        for fid, p1, p2 in ACCOUNT_FEATURES:
                            send(GAME_SMSG_ACCOUNT_FEATURE, [fid, p1, p2],
                                 f"ACCOUNT_FEATURE[{fid}]")
                    elif opcode == GAME_CMSG_INSTANCE_LOAD_REQUEST_PLAYERS:
                        # A balanced empty block: no other players in the
                        # instance, but the client still needs the brackets.
                        send(GAME_SMSG_INSTANCE_PLAYER_DATA_START, [],
                             "PLAYER_DATA_START(players)")
                        send(GAME_SMSG_INSTANCE_PLAYER_DATA_DONE, [],
                             "PLAYER_DATA_DONE(players)")

                        cfg = MAP_STATIC_CONFIG.get(
                            state["map_id"], MAP_STATIC_CONFIG[FALLBACK_MAP_ID])
                        pos = cfg[1]

                        send(GAME_SMSG_INSTANCE_LOADED, [PLAYER_TEAM_TOKEN],
                             "INSTANCE_LOADED")
                        send(GAME_SMSG_WORLD_UPDATE_LOAD_TIME, [0],
                             "WORLD_UPDATE_LOAD_TIME")
                        send(GAME_SMSG_PLAYER_INFO,
                             [PLAYER_NUMBER, PLAYER_AGENT_ID, APPEARANCE,
                              0, 0, 0, TEST_CHAR_NAME], "PLAYER_CREATE")
                        # Field names carrying hex offsets (h000B, h001E, h0023,
                        # h0027, h003B, h004B, h0059) let the 23 schema fields be
                        # aligned to the struct by offset rather than by counting:
                        # each named constant below lands exactly on its offset,
                        # and the total closes at 0x63 = the declared 99 bytes.
                        send(GAME_SMSG_WORLD_CREATE_AGENT,
                             [PLAYER_AGENT_ID,   # agent_id
                              CHAR_CLASS_PLAYER_BASE | PLAYER_NUMBER,
                              AGENT_TYPE_LIVING,
                              5,                 # h000B
                              pos,               # position
                              cfg[2],            # plane
                              (1.0, 0.0),        # direction
                              1,                 # h001E
                              DEFAULT_RUN_SPEED, # speed_base
                              1.0,               # h0023
                              0x41400000,        # h0027
                              PLAYER_TEAM_TOKEN,
                              0, 0, 0, 0, 0,     # h003B and neighbours
                              (0.0, 0.0),
                              (INF, INF),        # h004B
                              0, 0,
                              (INF, INF),        # h0059
                              0],
                             "WORLD_CREATE_AGENT")
                        # Attribute state must exist BEFORE the profession
                        # update lands. Sending profession alone killed the
                        # client on
                        #   Assertion: attribState
                        #   P:\\Code\\Gw\\Char\\Cli\\ChCliAttrib.cpp(435)
                        # with 0xb7 -- this message -- named in the stack trace.
                        # Upstream's SendSkillsAndAttributes sends the points
                        # first and the profession second, in that order.
                        send(GAME_SMSG_AGENT_UPDATE_ATTRIBUTE_POINTS,
                             [PLAYER_AGENT_ID, ATTRIBUTE_POINTS,
                              ATTRIBUTE_POINTS], "AGENT_ATTRIBUTE_POINTS")
                        send(GAME_SMSG_PLAYER_UPDATE_PROFESSION,
                             [PLAYER_AGENT_ID, PROF_WARRIOR, 0, 0],
                             "PLAYER_UPDATE_PROFESSION")
                        # The skill block. Upstream's SendSkillsAndAttributes
                        # sends the bar (218) BEFORE the unlock list (219); we
                        # send the unlocks first, deliberately. Upstream never
                        # puts a real id on a bar -- it sends eight zeros -- so
                        # its ordering is not evidence about a POPULATED bar,
                        # and if the client gates drawing on unlock state then
                        # having that state already in hand is the ordering that
                        # can work. If the bar draws, try upstream's order too:
                        # a difference there is a real finding either way.
                        send(GAME_SMSG_PVP_UPDATE_UNLOCKED_SKILLS, [UNLOCKED],
                             f"PVP_UPDATE_UNLOCKED_SKILLS({UNLOCK_LABEL})")
                        send(GAME_SMSG_UPDATE_UNLOCKED_SKILLS, [UNLOCKED],
                             f"UPDATE_UNLOCKED_SKILLS({UNLOCK_LABEL})")
                        skills = list(SKILLBAR)[:SKILLBAR_SLOTS]
                        skills += [0] * (SKILLBAR_SLOTS - len(skills))
                        send(GAME_SMSG_SKILLBAR_UPDATE,
                             [PLAYER_AGENT_ID, skills, SKILLBAR_PVP_MASKS,
                              SKILLBAR_TRAILER],
                             f"SKILLBAR_UPDATE{skills}")
                        # Why the character used to read Level 0: we never sent
                        # this at all. Every other field stays zero -- only
                        # field 9's effect has actually been observed, and
                        # filling the rest with plausible numbers would be
                        # exactly the invention this project keeps having to
                        # walk back.
                        player_attrs = [0] * PLAYER_ATTR_COUNT
                        player_attrs[PLAYER_ATTR_LEVEL] = START_LEVEL
                        send(GAME_SMSG_CHARACTER_UPDATE_FACTIONS, player_attrs,
                             f"CHARACTER_UPDATE_FACTIONS(level {START_LEVEL})")
                        send(GAME_SMSG_AGENT_UPDATE_ATTRIBUTES,
                             [PLAYER_AGENT_ID, [0] * ATTRIBUTE_COUNT],
                             "AGENT_UPDATE_ATTRIBUTES")
                        # The player's own pools, which we had never sent. See
                        # agents.py: the enemy got a health pool the day it was
                        # spawned and the player never got one, so every skill
                        # on the bar was unaffordable. Order and values follow
                        # gw-preservation's sendPlayerAttributes, which is a
                        # server the real client accepts.
                        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                             [agents.PROP_ENERGY_MAX, PLAYER_AGENT_ID,
                              agents.PLAYER_ENERGY],
                             f"PLAYER energy = {agents.PLAYER_ENERGY}")
                        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                             [agents.PROP_HEALTH_MAX, PLAYER_AGENT_ID,
                              agents.PLAYER_HEALTH],
                             f"PLAYER health = {agents.PLAYER_HEALTH}")
                        # The value field is a dword carrying IEEE float bits,
                        # same as the damage path above.
                        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
                             [agents.PROP_UNKNOWN_FLOAT_43, PLAYER_AGENT_ID,
                              PLAYER_AGENT_ID,
                              _f32(agents.PLAYER_FLOAT_43)],
                             "PLAYER float 43 (purpose unknown upstream too)")
                        # Putting the weapon on the BODY is a different question
                        # from putting it in the weapon-set UI, and we had only
                        # done the latter. Upstream sources this message from the
                        # equipped-items bag, not from the weapon set
                        # (GmAgent.c:200-218), and slot 0 of that bag is the
                        # weapon -- so position 0 here is the weapon item id.
                        #
                        # Sending 0x006E with NO bag behind it is deliberate: it
                        # is exactly the experiment studies/character/FINDINGS.md
                        # left open ("Try 353 + 110 with no bag, then add 319 and
                        # 318, and see which is the minimum that draws"), and it
                        # is the smallest change that can answer it.
                        #
                        # Position order is bag order, which is 2 lineages
                        # against 1 -- and positions 3-6 are CONTESTED. They are
                        # all zero here, so this send does not depend on that
                        # dispute; the moment armour goes in it will.
                        if EQUIP_WEAPON:
                            send(GAME_SMSG_UPDATE_AGENT_VISUAL_EQUIPMENT,
                                 [PLAYER_AGENT_ID, WEAPON_ITEM_ID,
                                  0, 0, 0, 0, 0, 0, 0, 0],
                                 "UPDATE_AGENT_VISUAL_EQUIPMENT(weapon)")
                            # ArenaNet sends this after EVERY 0x006E, 366 of
                            # 366 across both live captures. Zero because we
                            # have never populated a guild id, and 0 is what
                            # makes the client skip the lookup rather than
                            # resolve one that does not exist.
                            send(GAME_SMSG_AGENT_SET_TABARD_VISIBLE,
                                 agents.agent_set_tabard_visible(
                                     PLAYER_AGENT_ID, False),
                                 "AGENT_SET_TABARD_VISIBLE(player, 0)")
                            # And separately, what the agent WIELDS.
                            #
                            # These are ITEM IDS, not weapon types, and the
                            # client said so itself. Sending weapon type 3 here
                            # -- on the theory that this message sets
                            # AgentLiving::weapon_type at +h01B2 -- took the
                            # client down on
                            #     Assertion: ptr
                            #     P:\Code\Gw\Item\Cli\ItCliApi.cpp(400)
                            # with `baseItem` in the strings beside it. It
                            # looked 3 up in the item table, got null and died.
                            # OBSERVED, 2026-08-06. The client presumably
                            # derives weapon_type from the item's own
                            # ItemType, the same way it derives the mesh from
                            # file_id.
                            send(GAME_SMSG_NPC_UPDATE_WEAPONS,
                                 [PLAYER_AGENT_ID, WEAPON_ITEM_ID, 0],
                                 "NPC_UPDATE_WEAPONS(leadhand = item "
                                 f"{WEAPON_ITEM_ID})")
                            # And how fast that weapon swings, which the client
                            # does NOT work out from any of the four messages
                            # above. Its AvChar is constructed with an attack
                            # speed of 0.0 and exactly one thing in the image
                            # ever changes it: this message. Until it arrives,
                            # telling the client to start a swing asserts
                            # m_attackInterval and takes it down -- which is
                            # what every session before this one did.
                            send_attack_speed(send, PLAYER_AGENT_ID,
                                              WEAPON_ATTACK_SPEED, "player")
                        # unk0 is a literal 3 upstream (GmAgent.c:246).
                        send(GAME_SMSG_WORLD_UPDATE_CONTROLLED_AGENT,
                             [PLAYER_AGENT_ID, 3], "UPDATE_CONTROLLED_AGENT")
                        # Upstream sends this at the END of REQUEST_PLAYERS, not
                        # after spawn where we had it.
                        send(GAME_SMSG_INSTANCE_LOAD_FINISH, [],
                             "INSTANCE_LOAD_FINISH")
                        if SPAWN_ENEMY:
                            spawn_enemy(send, state,
                                        (pos[0], pos[1], cfg[2]), conn_id)
                        if PROBE_NAME:
                            run_probe(PROBE_NAME, send, conn_id, stop,
                                      origin=(pos[0], pos[1], cfg[2]))
                        if LABEL_RUN:
                            # The no-tape path: label against our OWN world, which
                            # answers. That is a different experiment from labelling
                            # after a tape -- here a completed action is visible, but
                            # the world is one player and at most one enemy, so most
                            # of the script has nothing to point at. Both are worth
                            # having; neither substitutes for the other.
                            threading.Thread(
                                target=labelrun.run,
                                args=(rec, conn_id, stop),
                                kwargs={"steps": LABEL_RUN},
                                daemon=True).start()
                    elif opcode == GAME_CMSG_INSTANCE_LOAD_REQUEST_SPAWN:
                        # map_file_id 0 is a placeholder: the real one comes from
                        # the map's static config, which we do not have yet. If the
                        # client refuses to spawn, this is the first thing to doubt.
                        cfg = MAP_STATIC_CONFIG.get(state["map_id"])
                        if cfg is None:
                            cfg = MAP_STATIC_CONFIG[FALLBACK_MAP_ID]
                            print(f"[c{conn_id}] no static config for map "
                                  f"{state['map_id']}; substituting map "
                                  f"{FALLBACK_MAP_ID} geometry", flush=True)
                        file_id, pos, plane = cfg[0], cfg[1], cfg[2]
                        send(GAME_SMSG_INSTANCE_LOAD_SPAWN_POINT,
                             [file_id, pos, plane, 0, 0, b"\x00" * 8],
                             f"INSTANCE_LOAD_SPAWN_POINT(file {file_id})")
                        # The load bar reaches 100% without this and stops there.
                        send(GAME_SMSG_INSTANCE_LOAD_FINISH, [],
                             "INSTANCE_LOAD_FINISH")
                elif kind != "auth":
                    # Game channel: capture only. Every handler below is keyed to
                    # AUTH_CMSG opcodes, and the two catalogs collide numerically
                    # — GAME_CMSG 0x0002 is TRADE_ADD_ITEM, not SEND_COMPUTER_HASH.
                    # Answering one as the other would be worse than silence.
                    pass
                elif opcode == AUTH_CMSG_SEND_COMPUTER_INFO:
                    state["username"] = values[1]
                    state["pcname"] = values[2]
                elif opcode == AUTH_CMSG_SEND_COMPUTER_HASH:
                    # This is the message the client waits on. Until we answer it
                    # the login never proceeds past the key exchange.
                    state["salt"] = secrets.randbits(32)
                    send(AUTH_SMSG_SESSION_INFO, [state["salt"], 0], "SESSION_INFO")
                elif opcode == AUTH_CMSG_HEARTBEAT:
                    # Reply unconditionally and regardless of login state. The
                    # dword is a server tick nothing reads back; it does not echo
                    # the client's value.
                    send(AUTH_SMSG_HEARTBEAT, [16], "HEARTBEAT")
                elif opcode == AUTH_CMSG_ACCEPT_EULA:
                    # The EULA dialog is client-side UI. Accepting it sends this
                    # 3-byte message HERE, to loopback — not to ArenaNet. The
                    # reference server treats it as a no-op with no reply, and so
                    # do we; the client proceeds on its own.
                    print(f"[c{conn_id}] EULA accepted by the user (value={values[1]}) "
                          f"— recorded locally, nothing sent upstream", flush=True)
                    state["eula_accepted"] = values[1]
                elif opcode == AUTH_CMSG_UNKNOWN_8023:
                    # Intentional no-op, not an oversight. Unnamed in both C
                    # references; a third implementation identifies this exact
                    # opcode and also no-ops it. If it ever turns out to need a
                    # reply the client will stall at a reproducible point.
                    pass
                elif opcode == AUTH_CMSG_PORTAL_ACCOUNT_LOGIN:
                    handle_portal_login(values, send, store, conn_id,
                                        allow_any, rec)
                elif opcode == AUTH_CMSG_ASK_SERVER_RESPONSE:
                    # A bare request/response ping. We ignored this through all
                    # of R1 and the client still reached character select, which
                    # made it look optional -- but the request stays OPEN until
                    # answered, and pressing Play then stalled with req_id 2
                    # outstanding for eight minutes. Silence here is not a no-op.
                    send(AUTH_SMSG_REQUEST_RESPONSE, [values[1], 0],
                         f"REQUEST_RESPONSE(ask {values[1]})")
                elif opcode == AUTH_CMSG_SETTING_UPDATE_SIZE:
                    # The client uploads its account settings blob in two parts:
                    # this announces the total, then one or more CONTENT messages
                    # carry it. Both share a req_id and the pair is acknowledged
                    # once, after the last chunk.
                    #
                    # Neither message exists in OpenTyria -- no struct, no
                    # handler. Everything here is read off our own wire, so the
                    # chunking rule is inferred from the declared array8 cap of
                    # 512 bytes rather than from a reference implementation.
                    state["settings_req"] = values[1]
                    state["settings_total"] = values[2]
                    state["settings_buf"] = b""
                    print(f"[c{conn_id}] settings upload: req {values[1]}, "
                          f"{values[2]} bytes announced", flush=True)
                elif opcode == AUTH_CMSG_SETTING_UPDATE_CONTENT:
                    req_id, chunk = values[1], values[2]
                    state["settings_buf"] = state.get("settings_buf", b"") + chunk
                    got = len(state["settings_buf"])
                    total = state.get("settings_total", got)
                    print(f"[c{conn_id}] settings chunk: {len(chunk)}B, "
                          f"{got}/{total}", flush=True)
                    if got >= total:
                        rec.event("account_settings", req_id=req_id, size=got,
                                  blob=binascii.hexlify(
                                      state["settings_buf"]).decode())
                        send(AUTH_SMSG_REQUEST_RESPONSE, [req_id, 0],
                             f"REQUEST_RESPONSE(settings {req_id})")
                elif opcode == AUTH_CMSG_SET_PLAYER_STATUS:
                    # Deliberately no reply: the reference server records the
                    # status and returns. Sent on pressing Play, status 1.
                    state["player_status"] = values[1]
                    print(f"[c{conn_id}] player status -> {values[1]} "
                          f"({PLAYER_STATUS.get(values[1], '?')})", flush=True)
                elif opcode == AUTH_CMSG_CHANGE_PLAY_CHARACTER:
                    req_id, name = values[1], values[2]
                    known = (name == TEST_CHAR_NAME)
                    state["selected_character"] = name
                    print(f"[c{conn_id}] play character: {name!r}"
                          f"{'' if known else ' — NOT on our roster'}", flush=True)
                    send(AUTH_SMSG_REQUEST_RESPONSE,
                         [req_id, 0 if known else GM_ERROR_NETWORK],
                         f"REQUEST_RESPONSE({'OK' if known else 'unknown char'})")
                elif opcode == AUTH_CMSG_REQUEST_GAME_INSTANCE:
                    handle_request_game_instance(values, send, conn_id,
                                                 state, rec)

            if desync_err:
                # AN UNDECODABLE OPCODE ENDS THE CONNECTION. It used to do
                # `pending = b""` and carry on, which reads like recovery and is
                # not one: there is no length prefix, so nothing here knows where
                # the bad message ended, and every LATER read is then framed from
                # a byte that is not a message boundary. ARC4 keeps decrypting
                # correctly the whole time, so the bytes stay plausible and the
                # framer either emits a cascade of undecodables or -- the real
                # hazard -- accidentally frames garbage into well-formed messages
                # that this loop then ACTS on. codec.decode_stream already refuses
                # to resynchronise and says why; this caller was resynchronising
                # on its behalf, badly.
                #
                # OBSERVED in our own corpus, 25 events across 17 of 416 sessions,
                # and the evidence that the old path was hiding a real bug: seven
                # identical events carry head `01 92 80 70 ...`, in which `92 80`
                # is a VALID GAME_CMSG 0x0092 sitting one byte later. That is an
                # off-by-one in a preceding message's length, and swallowing the
                # buffer turned a framing bug into background noise for a day.
                #
                # 4% of sessions is rare enough that closing costs little, and a
                # closed connection is a signal the operator can act on. A
                # silently mis-framed one is not.
                raw = (int.from_bytes(pending[:2], "little")
                       if len(pending) >= 2 else None)
                which = (f" from opcode 0x{raw:04x} "
                         f"(masked 0x{raw & ~AUTH_CMSG_MASK:04x})"
                         if raw is not None else "")
                print(f"[c{conn_id}] {desync_err}", flush=True)
                print(f"[c{conn_id}] DESYNC: {len(pending)}B unframeable{which}",
                      flush=True)
                print(f"[c{conn_id}] first bytes "
                      f"{binascii.hexlify(pending[:16]).decode()}", flush=True)
                print(f"[c{conn_id}] closing: we cannot find the next message "
                      f"boundary, and framing on from here would invent messages.",
                      flush=True)
                rec.event("undecodable", error=desync_err,
                          head=binascii.hexlify(pending[:64]).decode(),
                          unframeable_bytes=len(pending), closing=True)
                desynced = True
                break

        # Say WHICH ending this was. A desync and a clean hangup produced the same
        # "done" line, so a session that died mid-stream looked like one the client
        # closed politely.
        print(f"[c{conn_id}] done, {total} encrypted bytes recorded"
              f"{' -- ENDED ON DESYNC, see above' if desynced else ''}", flush=True)
        rec.event("disconnect", total_bytes=total, desynced=desynced)
    except (ConnectionError, socket.timeout, OSError) as ex:
        print(f"[c{conn_id}] {type(ex).__name__}: {ex}", flush=True)
        rec.event("error", error=repr(ex))
    finally:
        rec.close()
        try:
            sock.close()
        except OSError:
            pass


def load_keys(path):
    if path:
        return json.load(open(path))
    from vaultpath import require_dir
    kd = require_dir("keys", why="the DH private half; the server cannot decrypt without it")
    cands = sorted(f for f in os.listdir(kd) if f.startswith("rurik_dh_"))
    if not cands:
        raise SystemExit("No rurik_dh_*.json in vault/keys — run make_custom_client.py first.")
    p = os.path.join(kd, cands[-1])
    print(f"keys: {p}")
    return json.load(open(p))


def main():
    # Declared up front because argparse reads these as its defaults below, and a
    # `global` after any use of the name is a SyntaxError. Single-process server,
    # so rebinding the module constants is enough and keeps
    # handle_request_game_instance free of plumbing it would only ever use once.
    global GAME_SRV_HOST, GAME_SRV_PORT, HOST_FIELD_ENCODING, SKILLBAR
    global UNLOCKED, UNLOCK_LABEL

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=6112)
    ap.add_argument("--bind", default="127.0.0.1",
                    help="Loopback address to listen on. Any 127.x.y.z works "
                         "without setup on Windows; a second alias (127.0.0.2) "
                         "lets a probe show WHICH configured host the client "
                         "dials, since ports alone cannot when they collide. "
                         "Refuses anything outside 127/8 -- this server is "
                         "local-only by design.")
    ap.add_argument("--skills", default=",".join(str(s) for s in TEST_SKILLBAR),
                    help="Comma-separated skill ids for the bar, 0 for an empty "
                         "slot. Ids are row indices into the client's own skill "
                         "table, so they must exist in the build being launched "
                         "(0..3442 here). Fewer than 8 are padded with zeros.")
    ap.add_argument("--unlocks", default="all",
                    help="Unlock bitmap sent as opcodes 29 and 219: 'all' "
                         "(every bit set), 'none', 'bar' (exactly the --skills "
                         "ids), or an explicit comma-separated id list. Whether "
                         "the client REFUSES to draw a bar skill that is not "
                         "unlocked is NOT FOUND in every source we have; this "
                         "flag exists to settle it by experiment.")
    ap.add_argument("--keys")
    ap.add_argument("--vault", default=VAULT_DEFAULT)
    ap.add_argument("--host-encoding", choices=["sockaddr", "string"],
                    default=HOST_FIELD_ENCODING,
                    help="How to fill GAME_SERVER_INFO's 24-byte host field.")
    ap.add_argument("--game-host", default=GAME_SRV_HOST,
                    help="Address handed to the client in GAME_SERVER_INFO.")
    ap.add_argument("--game-port", type=int, default=GAME_SRV_PORT,
                    help="Port handed to the client in GAME_SERVER_INFO. "
                         "OBSERVED 2026-08-06 (handshake PLAN §10): the client "
                         "never dials it -- it dials --game-host at hardcoded "
                         "6112. Kept on the wire because retail put a real "
                         "value here and a probe may yet find what reads it.")
    ap.add_argument("--sessions",
                    help="Session store path. The self-test passes its own so it "
                         "cannot overwrite the token record a real client "
                         "established — the two used to share one file, and a "
                         "test run silently clobbered live state.")
    ap.add_argument("--once", action="store_true", help="exit after one connection")
    ap.add_argument("--tape", metavar="CAPTURE_DIR",
                    help="R1.5: replay a recorded LIVE session's server plaintext "
                         "on the game channel instead of our own map load, at the "
                         "timing the wire capture recorded. The auth channel stays "
                         "ours -- a verbatim auth replay answers the wrong request "
                         "ids. Refuses a capture that is not origin: live.")
    ap.add_argument("--tape-connection", metavar="CLIENT->SERVER", default=None,
                    help="which game channel of the capture to play; default is "
                         "the one with the most server plaintext.")
    ap.add_argument("--tape-no-transfer", action="store_true",
                    help="Stop the tape before the messages that hand the client to "
                         "another game server (0x01A5 + 0x0099 MAP_UPDATE_CURRENT), "
                         "so it stays in the map instead of dialling ArenaNet and "
                         "being refused by the cage. Implied by --labelrun, which "
                         "cannot survive the transfer.")
    ap.add_argument("--tape-rewrite-next", metavar="HOST[:PORT]", default=None,
                    help="R1.5 chaining: instead of stopping before the handoff, "
                         "repoint it at a loopback server we control, so the client "
                         "walks from this tape straight into the next one. 127/8 "
                         "only, and REFUSED otherwise -- a rewritten tape is "
                         "ArenaNet's own bytes with a destination of our choosing. "
                         "Mutually exclusive with --tape-no-transfer. Note the port "
                         "is probably decorative: the client is OBSERVED to dial "
                         "<host>:6112 regardless on the AUTH handoff, and whether "
                         "the GAME handoff behaves the same is UNVERIFIED, because "
                         "every recorded 0x01A5 advertises 6112 anyway. Passing an "
                         "explicit port is how that gets settled.")
    ap.add_argument("--tape-speed", type=float, default=1.0, metavar="X",
                    help="play faster or slower than recorded. 1.0 reproduces the "
                         "observed cadence; anything else changes the one property "
                         "the tape exists to reproduce, so say so when reporting.")
    ap.add_argument("--labelrun", nargs="?", const="combat", default=None,
                    choices=sorted(labelrun.SCRIPTS),
                    help="After the world is up (or after --tape finishes), walk "
                         "the operator through a numbered script printed to THIS "
                         "terminal, marking each step into the capture. Turns c2s "
                         "traffic into named human actions. THE SCRIPT MUST MATCH "
                         "THE WORLD THE TAPE LEAVES: `combat` (default) needs the "
                         "Lakeside tape, whose character has skills and whose map "
                         "has hostiles; `town` needs Ascalon City, which has NPCs, "
                         "merchants and 40 players but a skillbar of all zeros. "
                         "`labelrun.py --script NAME` prints one; "
                         "`labelrun.py --analyse` reads a result back.")
    ap.add_argument("--probe", metavar="NAME",
                    help="After the character spawns, fire a scripted experiment at "
                         "the client. See --list-probes. Only affects a session you "
                         "ask for it in; the default path is untouched.")
    ap.add_argument("--list-probes", action="store_true",
                    help="Print the available probes, their questions and their "
                         "predictions, then exit.")
    ap.add_argument("--click-sweep", action="store_true",
                    help="Cycle MOVE_TO_POINT's two plane fields through every "
                         "plausible assignment, one per click, and label each in "
                         "the log. Click the same wall or staircase repeatedly "
                         "and report which attempt numbers behaved; that "
                         "identifies the fields from the client instead of from "
                         "two sources that contradict each other.")
    ap.add_argument("--map", type=int, metavar="ID",
                    help="Put the character in this map instead of the one its "
                         "character record asks for. 146 is Lakeside County, "
                         "which is explorable and therefore the first place "
                         "combat can be tested; 148 is Ascalon City. INERT "
                         "under --tape: the tape's own 0x0195 decides what the "
                         "client loads, and it will happily draw a map it never "
                         "asked for.")
    ap.add_argument("--no-enemy", action="store_true",
                    help="Do not spawn the standing hostile NPC. The world is "
                         "then the player alone, which is what most probes "
                         "assume and what every session before 2026-08-06 was.")
    ap.add_argument("--no-weapon", action="store_true",
                    help="Log in with empty weapon slots, as every session before "
                         "2026-08-06 did. Attacking and weapon skills were both "
                         "unavailable then; this flag is what makes that "
                         "re-testable instead of merely remembered.")
    ap.add_argument("--explorable", action="store_true",
                    help="Tell the client this instance is explorable rather than "
                         "a town. Guild Wars forbids attacking in a town, so this "
                         "is the cheap way to find out whether combat is gated on "
                         "the map or on this one field — the alternative is "
                         "recovering a real explorable's file id out of Gw.dat.")
    ap.add_argument("--allow-any-session", action="store_true",
                    help="Accept a login with no matching session record. A debugging "
                         "escape hatch so a stale sessions.json cannot be mistaken for a "
                         "wire bug. Never the default: the rejection path has to stay exercised.")
    a = ap.parse_args()

    if a.list_probes:
        print("Probes -- scripted one-packet experiments against our own client.")
        print("Each states what it expects BEFORE it runs, so the result cannot be")
        print("rationalised afterwards into agreeing with whatever happened.")
        print()
        for n in probes.names():
            print(probes.describe(n))
            print()
        return
    if a.tape:
        import tape as tapemod
        global TAPE_EVENTS, TAPE_INFO, TAPE_SPEED
        try:
            TAPE_INFO, TAPE_EVENTS = tapemod.load_tape(a.tape, a.tape_connection)
        except tapemod.TapeError as ex:
            raise SystemExit(f"refusing to play this tape -- {ex}")
        TAPE_SPEED = a.tape_speed
        if a.tape_rewrite_next and (a.labelrun or a.tape_no_transfer):
            raise SystemExit(
                "--tape-rewrite-next and --tape-no-transfer/--labelrun ask for "
                "opposite things: one repoints the handoff at another server of "
                "ours, the other cuts the handoff out so the client stays put. "
                "Pick one.")
        if a.tape_rewrite_next:
            host, _, port = a.tape_rewrite_next.partition(":")
            try:
                TAPE_EVENTS, changed, why = tapemod.rewrite_transfer(
                    TAPE_EVENTS, codec, host,
                    int(port) if port else tapemod.TRANSFER_PORT)
            except (tapemod.TapeError, ValueError) as ex:
                raise SystemExit(f"refusing to rewrite this tape -- {ex}")
            # LOUD, and for a specific reason. Truncation is loud because it changes
            # what the tape is; a rewrite is louder because it changes where the
            # client GOES, and it removes the only signal that has ever caught this
            # going wrong. Before today an un-rewritten handoff failed CLOSED -- the
            # client dialled ArenaNet and the cage said Code=005. After a rewrite, a
            # wrong address is a dead connection and nothing says why. The banner and
            # rewrite_transfer's offline self-checks are what replace that.
            if changed:
                print(f"  TAPE REWRITTEN: {why}")
                print("  this tape is no longer verbatim. The client will dial US.")
                TAPE_INFO = dict(TAPE_INFO, rewritten=why)
            else:
                print(f"  tape needs no rewrite: {why}")
        if a.labelrun or a.tape_no_transfer:
            # A labelled run cannot survive its tape leaving the map, and three of
            # the four tapes in the 2026-08-07 capture end by doing exactly that --
            # the recorded operator walked into a gateway. OBSERVED 2026-08-10: the
            # Ascalon tape played 1,209/1,209, the client obeyed its 0x01A5 handoff,
            # dialled ArenaNet, the cage refused, and the connection died six seconds
            # into the labelled run. Truncating is the only way to keep the client in
            # the map, and it is LOUD because it changes what the tape is.
            TAPE_EVENTS, dropped, why = tapemod.stop_before_transfer(
                TAPE_EVENTS, codec)
            if dropped:
                print(f"  TAPE TRUNCATED: {why}")
                print(f"  the client will stay in this map instead of zoning out.")
                TAPE_INFO = dict(TAPE_INFO, events=len(TAPE_EVENTS),
                                 bytes=sum(len(b) for _t, b in TAPE_EVENTS),
                                 seconds=TAPE_EVENTS[-1][0] if TAPE_EVENTS else 0.0,
                                 truncated=dropped)
            else:
                print(f"  tape needs no truncation: {why}")
        print(f"tape armed: {TAPE_INFO['connection']} -- {TAPE_INFO['events']:,} "
              f"events, {TAPE_INFO['bytes']:,} B, {TAPE_INFO['seconds']:.1f}s "
              f"({TAPE_INFO['origin']})")
        print("  the GAME channel's load sequence is REPLACED by this recording; "
              "the auth channel is still ours.")
    if a.labelrun:
        global LABEL_RUN
        LABEL_RUN = labelrun.SCRIPTS[a.labelrun]
        total = sum(s.seconds for s in LABEL_RUN)
        print(f"labelled run armed: {a.labelrun} script, "
              f"{len(LABEL_RUN)} steps, {total:.0f}s"
              + (", starting when the tape finishes" if a.tape else ""))
        print("  WATCH THIS WINDOW. The client is -windowed so both fit on screen; "
              "the prompts appear here, not in the game.")

    if a.probe:
        if a.probe not in probes.names():
            raise SystemExit(f"no probe named {a.probe!r}. "
                             f"Known: {', '.join(probes.names())}")
        global PROBE_NAME
        PROBE_NAME = a.probe
        print(f"PROBE MODE: {a.probe} -- fires after the character spawns")

    if a.click_sweep:
        global CLICK_SWEEP
        CLICK_SWEEP = True
        print("CLICK SWEEP: every click sends MOVE_TO_POINT with a different")
        print("assignment of the two plane fields, in this order:")
        for i, (label, _) in enumerate(CLICK_SWEEP_VARIANTS, 1):
            print(f"   click {i}: {label}")
        print("Click the SAME spot each time -- a wall to walk through, or the")
        print("staircase -- and note which attempts behaved. The cycle repeats.")
        print()

    if a.map is not None:
        global MAP_OVERRIDE
        MAP_OVERRIDE = a.map
        known = MAP_STATIC_CONFIG.get(a.map)
        print(f"MAP OVERRIDE: {a.map}"
              + (f", explorable={bool(known[3])}" if known
                 else " -- NOT in MAP_STATIC_CONFIG, so geometry falls back "
                    f"to map {FALLBACK_MAP_ID} and it will not be explorable"))

    if a.no_enemy:
        global SPAWN_ENEMY
        SPAWN_ENEMY = False
        print("NO ENEMY: the world will contain the player and nothing else.")

    if a.no_weapon:
        global EQUIP_WEAPON
        EQUIP_WEAPON = False
        print("NO WEAPON: the character's four weapon slots stay empty.")

    if a.explorable:
        global EXPLORABLE
        EXPLORABLE = True
        print("EXPLORABLE: telling the client this instance is a field, not a "
              "town. The geometry is unchanged -- only the flag.")

    GAME_SRV_HOST, GAME_SRV_PORT = a.game_host, a.game_port
    HOST_FIELD_ENCODING = a.host_encoding

    try:
        SKILLBAR = [int(s, 0) for s in a.skills.split(",") if s.strip() != ""]
    except ValueError as ex:
        raise SystemExit(f"--skills must be a comma-separated list of ids: {ex}")
    if len(SKILLBAR) > SKILLBAR_SLOTS:
        raise SystemExit(f"--skills takes at most {SKILLBAR_SLOTS} ids, "
                         f"got {len(SKILLBAR)}")
    print(f"skillbar: {SKILLBAR}")
    UNLOCKED, UNLOCK_LABEL = build_unlock_bitmap(a.unlocks)
    set_bits = sum(bin(w).count("1") for w in UNLOCKED)
    print(f"unlocks:  {UNLOCK_LABEL}  ({set_bits} bit(s) set across "
          f"{UNLOCK_WORDS} words)")
    if a.unlocks != "all":
        drawn = [s for s in SKILLBAR
                 if s > 0 and UNLOCKED[s // 32] >> (s % 32) & 1]
        print(f"          of the bar, unlocked: {drawn or 'none'}")

    keys = load_keys(a.keys)
    if "server_private" not in keys:
        raise SystemExit("key file has no server_private — cannot decrypt.")
    print(f"build tag: {keys.get('build_tag', '?')}   generator {keys['generator']}, "
          f"prime {keys['prime'].bit_length()} bits")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Do NOT set SO_REUSEADDR here. On Windows it does not mean what it means on
    # Unix: it lets a second process BIND A PORT ALREADY IN USE, and the older
    # listener keeps taking the connections. That cost a real debugging session —
    # a stale server from a timed-out test silently shadowed a freshly-started
    # one, so the new code appeared to do nothing while an old build answered.
    # SO_EXCLUSIVEADDRUSE makes the second instance fail loudly instead.
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    parts = a.bind.split(".")
    if not (len(parts) == 4 and parts[0] == "127"
            and all(p.isdigit() and int(p) <= 255 for p in parts)):
        raise SystemExit(f"--bind {a.bind!r} is not a 127/8 loopback address. "
                         f"This server is local-only by design and will not "
                         f"listen anywhere a LAN could reach.")
    try:
        srv.bind((a.bind, a.port))  # loopback only, deliberately
    except OSError as ex:
        raise SystemExit(
            f"Could not bind {a.bind}:{a.port} — {ex.strerror}.\n"
            f"Another AuthSrv is almost certainly still running. Find it with\n"
            f"  netstat -ano | findstr :{a.port}\n"
            f"and stop it before starting this one.")
    srv.listen(8)
    print(f"Rurik AuthSrv on {a.bind}:{a.port}  (loopback only)")
    print("the client MUST be the patched copy — an unpatched one keys to "
          "ArenaNet's public value and we cannot read it\n")

    store = SessionStore(a.sessions) if a.sessions else SessionStore()
    stop = threading.Event()
    n = 0
    try:
        while True:
            sock, addr = srv.accept()
            n += 1
            t = threading.Thread(target=handle,
                                 args=(sock, addr, keys, a.vault, n, stop, store, a.allow_any_session),
                                 daemon=True)
            t.start()
            if a.once:
                t.join()
                break
    except KeyboardInterrupt:
        print("\nstopping")
        stop.set()
    finally:
        srv.close()


if __name__ == "__main__":
    main()
