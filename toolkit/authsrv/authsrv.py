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
from codec import Codec  # noqa: E402
from sessionstore import SessionStore, wire_to_uuid  # noqa: E402
import probes  # noqa: E402

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
GAME_SMSG_WORLD_UPDATE_CONTROLLED_AGENT = 0x0022
GAME_SMSG_PLAYER_CREATE = 0x0059
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

# OpenTyria's GmMapsConfig.c, verbatim: map_id -> (map_file_id, (x, y), plane).
# map_file_id is what the client opens out of Gw.dat. Sending 0 killed it on
#   Assertion: fileId
#   P:\Code\Base\Rtl\File.cpp(367)
# Only six maps are configured upstream, and Ascalon City Pre-Searing (148) --
# the one this account's character actually stands in -- is not among them.
MAP_STATIC_CONFIG = {
    449: (0x345CC, (-9067.0, 13218.0), 0),   # Kamadan, Jewel of Istan (outpost)
    194: (0x265F7, (0.0, 0.0), 0),           # Kaineng Center (outpost)
    55:  (352808, (0.0, 0.0), 0),            # Lion's Arch (outpost)
    474: (219215, (0.0, 0.0), 0),            # Domain of Anguish
    558: (287493, (0.0, 0.0), 0),            # Sparkfly Swamp
    90:  (46594, (0.0, 0.0), 0),             # Lornar's Pass
}
# Kamadan is the substitute because it is the only entry upstream gives a real
# spawn point for. Loading it under another map's id is knowingly inconsistent;
# it answers "is the file id the last blocker?" without first having to recover
# Ascalon's id from Gw.dat.
FALLBACK_MAP_ID = 449

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
# What is borrowed is the SEMANTICS -- that keyboard movement belongs on this
# message. That rests on GWLP-R alone, and is UNVERIFIED against our client
# until a playtest says the walking looks right.
GAME_SMSG_AGENT_MOVE_DIRECTION = 0x0025

GAME_SRV_HOST = "127.0.0.1"
# How GAME_SERVER_INFO fills its 24-byte host field. "sockaddr" is what both
# reference implementations do; "string" is the competing reading. Switchable
# because the client demonstrably ignores what we send and dials the portal
# host on port 80 instead.
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

VAULT_DEFAULT = r"C:\gd\Rurik\vault\captures\authsrv"


# Set from --probe. Read by the spawn path; None means the server behaves
# exactly as it does in a normal session.
PROBE_NAME = None

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


def run_probe(name, send, conn_id, stop):
    """Fire a scripted experiment at the client, on its own thread.

    On its own thread because the steps are deliberately seconds apart -- a
    person has to see one result before the next arrives -- and the receive loop
    must keep running throughout or the client times out mid-probe.

    Failures are printed and swallowed. A probe is an experiment; a packet the
    client rejects is a result, not a crash, and it must not take the session
    down with it or we lose the rest of the sequence.
    """
    probe = probes.get(name, PLAYER_AGENT_ID)
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

    def event(self, kind, **kw):
        kw["kind"] = kind
        kw["t"] = round(time.perf_counter() - self.t0, 6)
        kw["wall"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.meta.write(json.dumps(kw) + "\n")
        self.meta.flush()

    def frame(self, direction, cipher: bytes, plain: bytes):
        # Length-prefixed so the file stays parseable when the parser is rewritten.
        self.raw.write(struct.pack("<BId", 0 if direction == "c2s" else 1,
                                   len(cipher), time.perf_counter() - self.t0))
        self.raw.write(cipher)
        self.raw.flush()
        self.event("frame", direction=direction, n=len(cipher),
                   cipher=binascii.hexlify(cipher[:512]).decode(),
                   plain=binascii.hexlify(plain[:512]).decode())

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
        24,                                       # EULA revision — NOT a bool
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

        def send(opcode, values, label, quiet=False):
            blob = codec.encode(smsg, opcode, values)
            with send_lock:
                sock.sendall(s2c.crypt(blob))
            # quiet is for the 20 Hz position tick only: it would bury every
            # other line in the console. It still goes into the capture, because
            # "did we actually send position updates" is exactly the question a
            # movement bug needs answered.
            if not quiet:
                print(f"[c{conn_id}] s2c {label} (0x{opcode:04x}, {len(blob)}B)",
                      flush=True)
            rec.event("sent", opcode=opcode, label=label,
                      plain=binascii.hexlify(blob).decode())

        if kind == "game":
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
            send(GAME_SMSG_INSTANCE_LOAD_INFO,
                 [1,          # agent_id -- the player's own agent, 1 for the first
                  map_id,     # echoed from the version frame, not guessed
                  0,          # is_explorable: Ascalon City is an outpost
                  0,          # district
                  0,          # language
                  0],         # is_observer
                 "INSTANCE_LOAD_INFO")

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

            threading.Thread(target=world_tick, daemon=True).start()

        sock.settimeout(1.0)
        total = 0
        pending = b""          # decrypted bytes not yet framed into whole messages
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
            msgs, consumed, err = codec.decode_stream(
                cmsg, pending, mask=AUTH_CMSG_MASK)
            pending = pending[consumed:]

            for opcode, values in msgs:
                # No semantic names exist for GAME_CMSG in this repo yet; the
                # schema knows shapes only. Printing "?" is the honest answer
                # rather than borrowing an auth name that means something else.
                name = AUTH_CMSG_NAMES.get(opcode, "?") if kind == "auth" else "?"
                print(f"[c{conn_id}] c2s 0x{opcode | AUTH_CMSG_MASK:04x} {name}",
                      flush=True)
                rec.event("decoded", opcode=opcode, name=name,
                          values=[v.hex() if isinstance(v, bytes) else v
                                  for v in values])

                if kind == "game":
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
                        send(GAME_SMSG_ITEM_SET_ACTIVE_WEAPON_SET, [1, 0],
                             "SET_ACTIVE_WEAPON_SET")
                        for slot in range(4):
                            send(GAME_SMSG_ITEM_WEAPON_SET, [1, slot, 0, 0],
                                 f"WEAPON_SET[{slot}]")
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
                        send(GAME_SMSG_PLAYER_CREATE,
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
                        # unk0 is a literal 3 upstream (GmAgent.c:246).
                        send(GAME_SMSG_WORLD_UPDATE_CONTROLLED_AGENT,
                             [PLAYER_AGENT_ID, 3], "UPDATE_CONTROLLED_AGENT")
                        # Upstream sends this at the END of REQUEST_PLAYERS, not
                        # after spawn where we had it.
                        send(GAME_SMSG_INSTANCE_LOAD_FINISH, [],
                             "INSTANCE_LOAD_FINISH")
                        if PROBE_NAME:
                            run_probe(PROBE_NAME, send, conn_id, stop)
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
                        file_id, pos, plane = cfg
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

            if err and "incomplete" not in err:
                # Unknown opcode: we cannot frame past it and must not guess,
                # because there is no length prefix to resynchronise against.
                print(f"[c{conn_id}] {err}", flush=True)
                print(f"[c{conn_id}] {len(pending)}B undecodable — "
                      f"first bytes {binascii.hexlify(pending[:16]).decode()}", flush=True)
                rec.event("undecodable", error=err,
                          head=binascii.hexlify(pending[:64]).decode())
                pending = b""

        print(f"[c{conn_id}] done, {total} encrypted bytes recorded", flush=True)
        rec.event("disconnect", total_bytes=total)
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
    kd = r"C:\gd\Rurik\vault\keys"
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
    global GAME_SRV_HOST, GAME_SRV_PORT, HOST_FIELD_ENCODING

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=6112)
    ap.add_argument("--keys")
    ap.add_argument("--vault", default=VAULT_DEFAULT)
    ap.add_argument("--host-encoding", choices=["sockaddr", "string"],
                    default=HOST_FIELD_ENCODING,
                    help="How to fill GAME_SERVER_INFO's 24-byte host field.")
    ap.add_argument("--game-host", default=GAME_SRV_HOST,
                    help="Address handed to the client in GAME_SERVER_INFO.")
    ap.add_argument("--game-port", type=int, default=GAME_SRV_PORT,
                    help="Port handed to the client in GAME_SERVER_INFO. Movable "
                         "because the client stops dialling an address that has "
                         "refused it, and a fresh port is the cheapest way to tell "
                         "'the client gave up on that endpoint' apart from 'the "
                         "client never acts on our message'.")
    ap.add_argument("--sessions",
                    help="Session store path. The self-test passes its own so it "
                         "cannot overwrite the token record a real client "
                         "established — the two used to share one file, and a "
                         "test run silently clobbered live state.")
    ap.add_argument("--once", action="store_true", help="exit after one connection")
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

    GAME_SRV_HOST, GAME_SRV_PORT = a.game_host, a.game_port
    HOST_FIELD_ENCODING = a.host_encoding

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
    try:
        srv.bind(("127.0.0.1", a.port))  # loopback only, deliberately
    except OSError as ex:
        raise SystemExit(
            f"Could not bind 127.0.0.1:{a.port} — {ex.strerror}.\n"
            f"Another AuthSrv is almost certainly still running. Find it with\n"
            f"  netstat -ano | findstr :{a.port}\n"
            f"and stop it before starting this one.")
    srv.listen(8)
    print(f"Rurik AuthSrv on 127.0.0.1:{a.port}  (loopback only)")
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
