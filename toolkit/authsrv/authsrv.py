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
import bisect
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


def _f32_of(dword):
    """`_f32` backwards: the float a `dword` field the client sent us is carrying.

    THE SAME TRAP, from the receive side, and it has now cost this project three
    times (GAME_SMSG 0x002E's "cos, sin", GAME_CMSG 0x0027's field order, and
    GAME_CMSG 0x0040 sitting unnamed for days). A dword-typed field is four
    bytes; whether they are an integer or a float is a fact about the MESSAGE,
    not about the marshalling, and reading one as the other never errors -- it
    hands back a confident wrong number. 0x0040's +inf sentinel reads as
    2,139,095,040 if you take `values[1]` at face value.

    Out-of-range input is masked rather than raised on. The codec only ever
    produces 0..2^32-1 here, so the mask is unreachable in practice; what it
    buys is that a future caller cannot turn a malformed field into a
    struct.error that tears down a live session inside the read loop.
    """
    return struct.unpack("<f", struct.pack("<I", int(dword) & 0xFFFFFFFF))[0]


def _fraction(x, prop, what):
    """A pool fraction for the 0x00A3 float channel, refused loudly if out of range.

    THE CRASH THIS EXISTS FOR, and it is the first client assert this project has
    captured from a real fight. OBSERVED 2026-08-11: two seconds after the Hatcher
    died, the client went down on

        Assertion: fraction <= 1.0f    P:\\Code\\Gw\\Char\\CharPool.cpp(84)

    and the crash trace carries our own message three frames below the assert --
    `Arg:00000022 0000000a 0000000a 42c80000`, which is property 34, agent 10,
    agent 10, and 42c80000 = 100.0f. That is `revive_due`'s "refill bar" send,
    which passed `max_health` where the client wanted a FRACTION of it.

    WHY EVERY EARLIER MEASUREMENT MISSED IT. The assert is `<=`, so it can only
    fire in the POSITIVE direction, and every value we had ever put on this channel
    was damage: `-HIT_FRACTION`, and the `-50.0` that `GV_HEALTH`'s comment is
    built on. A negative number passes `fraction <= 1.0f` no matter how absurd, so
    the whole damage side of the arc tested this bound VACUOUSLY. It took a kill
    and a revive -- the first positive value ever sent -- to reach it.

    Refusing here rather than clamping is deliberate: a clamp would turn a wrong
    number into a plausible one, and the next caller would never learn.
    """
    if not -1.0 <= x <= 1.0:
        raise ValueError(
            f"refusing to send {x!r} as property {prop} ({what}) on the 0x00A3 "
            f"float channel: values there are FRACTIONS of a pool, and the client "
            f"asserts `fraction <= 1.0f` at CharPool.cpp:84 -- it does not clamp, "
            f"it dies, two seconds later and with no server-side symptom.")
    return _f32(x)


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
# The three-message round trip that drives the client's net graph. Server sends
# 0x000C (empty), client replies 0x0009 (its own perf state), server sends
# 0x000D carrying the elapsed milliseconds. studies/smsg `0x000C`/`0x000D`,
# both read out of the client's own handler table rather than guessed:
# handler 0x000C = 0x00491E50, handler 0x000D = 0x00491ED0.
#
# NAMES. The client-side reading is CLIENT_PERF_REQUEST -- the handler's only
# effect is to compose and send a performance report, and the reply carries a
# frame interval and a frame-system flag rather than echoing anything we sent.
# The server-side reading (studies/divergence D4) is PING, because we time the
# round trip and hand the result back. studies/smsg says to record both, so the
# constants take the client's name and this comment carries ours: it is not a
# liveness ping, and treating it as one would hide that the reply has real
# content a future server has to make sense of.
GAME_SMSG_CLIENT_PERF_REQUEST = 0x000C
GAME_SMSG_LATENCY_REPORT = 0x000D
GAME_CMSG_CLIENT_PERF_REPORT = 0x0009
# One byte of UI-overlay flags, read out of the client rather than guessed
# (studies/smsg, the s_netGraph section). Handler 0x0084E090 clears 0xFFFFFFF2
# from the flags word at [TLS+0x44]+0x2A8 and then maps THIS byte onto it:
#   bit 0 (0x01) -> flags bit 0
#   bit 1 (0x02) -> flags bit 2
#   bit 2 (0x04) -> flags bit 3  <-- the net graph's LATENCY widget
# Only flags bit 3 is understood; it is the one the predicate at 0x0084DF00
# tests (`shr 3 / and 1`) before building the object at 0xC06FE8, which is what
# wraps the client's use of the round trip we send in 0x000D. Nothing in the
# image sets that bit any other way, so this message is the ONLY route to it.
GAME_SMSG_UI_OVERLAY_FLAGS = 0x016E
UI_OVERLAY_FLAG_NETGRAPH_LATENCY = 0x04
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
GAME_SMSG_PLAYER_PARTY_SIZE = 0x00B0
GAME_SMSG_PLAYER_SET_PARTY = 0x00B1
# Three bits in the player record, (value, mask). See agents.player_flags for the
# 423-send census that fixes the shape and picks 4 as the lone-player value.
GAME_SMSG_PLAYER_FLAGS = 0x003C
# 0x00B6, the client's own OnProfessionSecondaryBits: which professions this
# agent may take as a SECONDARY. MUST be sent AFTER that agent's 0x00B7 -- the
# handler looks the record up and drops the message silently if it is not there
# yet (studies/profession/RUNS.md §13). Default 0, which is what ArenaNet's own
# server sends for a character with nothing unlocked: 11 of 11 samples in our
# live corpus carry mask 0.
GAME_SMSG_PLAYER_UPDATE_SECONDARY_BITS = 0x00B6
SECONDARY_BITS = 0

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
APPEARANCE_PROFESSION_SHIFT = 20
APPEARANCE = PROF_WARRIOR << APPEARANCE_PROFESSION_SHIFT


def appearance_for(profession):
    """The 0x0059 appearance dword, with the nibble following an IN-BAND id only.

    THE NIBBLE IS DIFFERENT STORAGE AND IS BOUND-CHECKED. It is 4 bits at 20-23
    and the client asserts it `< 0xB` at load, which is why
    `--spawn-profession 12` deliberately leaves this alone: the custom id
    rides the byte carriers and the nibble keeps a legal placeholder
    (studies/profession/MODDABLE.md, and RUNS.md §12 where 12 on 0x00A6 ran a
    whole session with the nibble still at Warrior).

    But for an id the client DOES ship, the nibble must follow, or the
    character is a Warrior everywhere the appearance dword is read while
    being profession N everywhere the byte carriers are read -- a split that
    would make a reskin experiment uninterpretable, since the two halves
    would disagree about which profession is on screen.
    """
    if 1 <= profession <= agents.CHAR_PROFESSIONS - 1:
        return profession << APPEARANCE_PROFESSION_SHIFT
    return APPEARANCE


def char_settings_for(profession, settings=None):
    """The character-select blob with its appearance field agreeing with 0x0059.

    Same field, second carrier: the roster screen reads this blob while the
    in-world avatar reads 0x0059's dword. They were independent constants, so
    `--spawn-profession 8` produced a Ritualist in the world and a Warrior on
    the character-select screen. Bytes 8..11, little-endian.
    """
    blob = bytearray(TEST_CHAR_SETTINGS if settings is None else settings)
    blob[8:12] = appearance_for(profession).to_bytes(4, "little")
    return bytes(blob)

# What the SPAWN BURST's 0x00B7 carries as the primary profession. Rebound by
# --spawn-profession, and the point of that flag is RUNS.md section 8: a
# mid-session profession change needs the skill state re-delivered, and a
# mid-session SKILLBAR_UPDATE followed by opening the skills panel asserts the
# client even at a LEGAL profession -- so the only clean delivery of a custom
# profession is the burst itself, where bar, unlocks and attributes all arrive
# AFTER the profession and nothing is ever re-sent. The APPEARANCE nibble above
# deliberately does NOT follow this value: it is different storage
# (studies/profession/MODDABLE.md), bound-checked `< 0xB` with an assert at
# load, so a custom id must never go there -- and a mismatch (nibble 1, byte N)
# is exactly the condition run 2 already measured as survivable.
SPAWN_PROFESSION = PROF_WARRIOR


def spawn_profession_values(profession=None):
    """The 0x00B7 payload for the spawn burst, built THROUGH the guard.

    agents.agent_set_profession is the server's own bound check; building the
    burst payload from it rather than beside it is the same rule the probes
    follow -- custom=True is derived here, not defaulted, so an out-of-band
    spawn profession still traverses the u8 ceiling and the 0-refusal.
    """
    p = SPAWN_PROFESSION if profession is None else profession
    return agents.agent_set_profession(
        PLAYER_AGENT_ID, p, 0,
        custom=p > agents.CHAR_PROFESSIONS - 1) + [0]


def spawn_probe_warning(probe, spawn_set, spawn_out_of_band=False):
    """profession_spawn without --spawn-profession measures the wrong thing.

    The probe's question is what the skills panel does when a custom
    profession arrived IN the burst; without the flag the session spawns at
    the default (profession 1), which run 2 already measured. A warning, not
    a refusal -- and it must NOT fire when the flag is given, because a
    warning that fires either way is noise (same rule as the enemy warning).
    """
    if probe == "profession_spawn" and not spawn_set:
        return ("WARNING: --probe profession_spawn without --spawn-profession: "
                f"this session spawns at the default profession {PROF_WARRIOR}, "
                "which run 2 already measured. The probe's question needs "
                "--spawn-profession 12, with a control session at "
                "--spawn-profession 3 first (studies/profession/RUNS.md s8).")
    # profession_panel exists BECAUSE 0x00B7 cannot carry a custom id. Pairing
    # it with an out-of-band --spawn-profession puts exactly that message in
    # the burst, so the client dies at map load ~3.4 s in and the probe's own
    # steps never run -- a whole session spent re-measuring a result we have
    # twice. Refused rather than warned: there is no reading of that pair that
    # answers the probe's question.
    if probe == "profession_panel" and spawn_out_of_band:
        raise SystemExit(
            "--probe profession_panel with an out-of-band --spawn-profession "
            "is refused. The burst's 0x00B7 would carry the custom id and the "
            "client asserts `profession < arrsize(s_profChapter)` "
            "(ConstChar.cpp:1296) ON ARRIVAL -- MEASURED twice, at +3.42 s and "
            "+3.39 s, both dead before any UI action. This probe delivers the "
            "custom id on 0x00A6 itself, which lands silently; run it with no "
            "--spawn-profession at all (studies/profession/RUNS.md s10.5).")
    return None


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
# MEASURED, not chosen: ArenaNet's cadence is 5.000 s, 75 of 76 gaps inside
# 100 ms across three tapes (studies/smsg, and studies/divergence D4). 0x000C
# and 0x000D are the ONLY periodic messages in the whole corpus -- the
# next-lowest inter-arrival CV of any other opcode is 0.586 -- so this is the
# one interval in this file that copying exactly is the right thing to do.
#
# `--ping-seconds` OVERRIDES IT, and there is exactly one reason to. The client's
# reply to this request is the only PROOF OF LIFE the server has: a Guild Wars
# assert leaves the process alive behind a modal dialog with its socket open, so
# the connection says nothing about when the client stopped (2026-08-12: last
# reply t=17.16, ConnectionResetError t=48.77, 31.6 s apart). The opcode sweep
# therefore localises a crash to the gap between two replies, and at 5.000 s
# against a 0.4 s dwell that gap is twelve opcodes wide. Raising the rate for a
# sweep run narrows it to one or two. Do NOT raise it for anything else: 5.000 s
# is ArenaNet's measured cadence, and this is the one interval worth copying.
PING_SECONDS = 5.0
# The client THROWS AWAY a latency above this: its handler at 0x0048DA40 opens
# `cmp esi,0x1388 / ja skip` (0x1388 = 5000) before touching the shift
# register. So an over-large value is not clamped for us, it is silently
# dropped -- the net graph simply never moves, which looks like a dead feature
# rather than a bad number. We refuse to send one instead.
LATENCY_MAX_MS = 5000
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
# OBSERVED: every 0x0037 ArenaNet sent in the vault's two live captures carries
# [0, 0] -- 8 of 8 connections, once each at load, naming the player agent (e.g.
# 20260807T143055 conn :64103 t=0.722 hex 37001f0000000000). The 50 this used to
# be was UPSTREAM and uncited (GmPlayer.c:125), contradicted by all eight.
# STATE-CONDITIONAL, not universal: all eight samples are characters in unknown
# spend state, so what a character with genuinely unspent points gets is open --
# capture shopping-list item 1, studies/combat/PLAN.md section 3. Whether the two
# bytes mean used/max or max/used is still CONTESTED, and moot only at zero.
ATTRIBUTE_POINTS = 0

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
    """Every real skill id -- 1..SKILL_TABLE_ROWS-1. NOT id 0, and that is the
    whole of studies/profession's six-session crash.

    THE BIT THAT COST SIX CLIENT SESSIONS. This used to be
    `range(SKILL_TABLE_ROWS)`, starting at 0, so every 0x00DB this server ever
    sent carried bit 0 -- 242 of 242 sends across every capture in the vault,
    all beginning `db 00 80 00 ff ff ff ff`. Skill id 0 is not a skill.

    WHAT THE CLIENT DOES WITH IT (OBSERVED, build 38797, disassembly):
    0x00DB's handler routes the payload to a bitmap container at
    ctx[0x2c]+0x710, and the Skills-and-Attributes panel enumerates that
    container with a find-next-set-bit iterator (0x00821790). The iterator
    forms `id = (word << 5) + bit` and asserts the id is NON-ZERO --
    `*skill`, ChCliSkill.cpp:1022. Bit 0 set means the first id enumerated is
    0, so the panel asserts the instant it opens. Nothing is null: the assert
    is a ZERO VALUE test, which is why studies/profession/RUNS.md's "null
    lookup" reading was wrong for four documents.

    The walk is PROFESSION-BLIND -- no profession value branches anything
    between the panel's entry and the assert -- so this fired at every
    profession we ever tried, and the arc's "profession 3 opens" premise was
    an artifact of a misattributed crash. Six sessions were spent inventing
    and refuting profession stories for a crash with no profession in it.

    The explicit-list arm of build_unlock_bitmap has skipped id 0 since it was
    written (`if sid <= 0: continue`); only this arm did not. Pinned by
    test_agentlife.py's unlock-bitmap section, which reproduces the old
    version as a negative control.
    """
    words = [0] * UNLOCK_WORDS
    for sid in range(1, SKILL_TABLE_ROWS):
        words[sid // 32] |= 1 << (sid % 32)
    return words


UNLOCKED = unlock_all_words()
UNLOCK_LABEL = "all"


def unlock_corpus_words():
    """Only the ids the client will draw a skill ICON for.

    RUNS.md §11: with all 3,442 rows unlocked the panel gets past the skill
    walk and then asserts `fileId` at File.cpp:367 loading an icon. Only
    **1,333** of those rows are player-usable skills (`equip_family == 1`,
    PvP flag clear -- the rule SKILL_EXTRACTION.md §4 established); the rest
    are weapon modifiers and other non-player definitions that share the
    table and have no skill icon.

    DERIVED AT RUN TIME FROM THE OWNER'S OWN CLIENT, never committed. That is
    the pattern `mapbuild.py` already proves for FINDINGS 14's constants: the
    extractor is in this repo (`skilltable.py`), the build is recorded in the
    label this returns, and no ArenaNet bytes enter the tree. Reading it costs
    one pass over the table at startup.

    Imported INSIDE the function on purpose: the default `--unlocks all` path
    must keep working on a machine with no vault and no client, which is the
    bare-machine rule the fixed-byte-pattern tools live under.
    """
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "clientscan"))
    import pinned                                              # noqa: E402
    import skilltable                                          # noqa: E402

    try:
        path, why = pinned.find()
    except SystemExit as ex:
        raise SystemExit(
            f"{ex}\n"
            f"  --unlocks corpus derives the player-usable skill ids from the "
            f"client itself, so it needs one to read.\n"
            f"  With no client: `--unlocks bar` sends exactly the --skills ids "
            f"and is what the panel was first opened with.\n"
            f"  `--unlocks all` is REFUSED in spirit but not in code -- it "
            f"asserts fileId (File.cpp:367) the moment the Skills panel opens.")
    data = open(path, "rb").read()
    base, count, _score = skilltable.locate_table(data)
    rows = [skilltable.parse_record(data, base, i) for i in range(count)]
    ids = [i for i in skilltable.player_corpus(rows) if i > 0]
    words = [0] * UNLOCK_WORDS
    for sid in ids:
        if sid < UNLOCK_WORDS * 32:
            words[sid // 32] |= 1 << (sid % 32)
    return words, (f"corpus ({len(ids)} player-usable of {count} rows, "
                   f"build {pinned.BUILD}, {why})")


def refuse_skill_zero(words, spec):
    """Bit 0 set means the client asserts the moment the Skills panel opens.

    A HARD REFUSAL AT STARTUP, because the alternative is a crash twelve
    seconds into a client session that costs a launch, a login and a map load
    to observe -- and it has already cost seven of them (RUNS.md §10). The
    client's panel enumerates this bitmap with a find-next-set-bit iterator,
    forms `id = (word << 5) + bit`, and asserts the id NON-ZERO at
    ChCliSkill.cpp:1022. Skill id 0 is not a skill, so bit 0 is never
    legitimate on this wire.

    It refuses rather than silently clearing the bit: a server that quietly
    repaired its own payload would hide a regression in whatever produced it,
    and the point is to make the next one impossible to ship unnoticed.
    """
    if words and words[0] & 1:
        raise SystemExit(
            f"--unlocks {spec!r} produced a bitmap with BIT 0 SET (skill id 0). "
            f"Refusing to send it: the client's Skills panel enumerates this "
            f"bitmap and asserts `*skill` at ChCliSkill.cpp:1022 on a zero id, "
            f"so the session would die the moment the panel opens. Skill ids "
            f"start at 1. See studies/profession/RUNS.md §10.")
    return words


def build_unlock_bitmap(spec):
    """--unlocks: 'all', 'none', 'bar', or an explicit comma-separated id list."""
    if spec == "corpus":
        words, label = unlock_corpus_words()
        return refuse_skill_zero(words, spec), label
    if spec == "all":
        return (refuse_skill_zero(unlock_all_words(), spec),
                f"all ({SKILL_TABLE_ROWS - 1} real skills, ids 1..{SKILL_TABLE_ROWS - 1})")
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
    return refuse_skill_zero(words, spec), ",".join(str(i) for i in ids)

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

    WHEN this runs is load-bearing, which is why `prewarm_pathmap` exists. Its
    other call site is instance bring-up -- i.e. after a client has connected --
    and a RUNNING Guild Wars client holds its own `Gw.dat` open exclusively, so
    on a run where the server and the client share one archive this read fails
    with EACCES and collision silently turns off.
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
        except PermissionError as exc:
            # Name the cause. "Permission denied" on a file this process owns
            # reads as a broken install or a stray antivirus; it is the CLIENT
            # holding the archive, and the fix is to have read it earlier.
            print(f"[map] no navmesh for 0x{map_file_id:X}: {exc}")
            print("[map] that is the CLIENT holding this archive open -- the "
                  "read came too late; see prewarm_pathmap()")
            print("[map] collision is OFF; the character can walk through walls")
            pm = None
        except Exception as exc:                              # noqa: BLE001
            print(f"[map] no navmesh for 0x{map_file_id:X}: {exc}")
            print("[map] collision is OFF; the character can walk through walls")
            pm = None
        _PATHMAPS[map_file_id] = pm
        return pm


def prewarm_pathmap(map_id):
    """Read the navmesh at STARTUP, before any client can lock the archive.

    MEASURED 2026-08-13, and it corrects a claim this repo made the other way
    round. `load_pathmap`'s other call site is instance bring-up -- the client
    is up by then -- and on the authoring loop the server and the client read
    the SAME archive, so that read hit a client-held exclusive lock, returned
    EACCES, and left the character with no collision at all while the harness
    still reported PASS.

    Before that it was worse in a quieter way. With the server defaulted to
    `vault/dat_study/Gw.dat` while the authored map was installed into a run
    copy, the read SUCCEEDED and handed back ArenaNet's geometry for the same
    map id. Over a 4,096-point grid on the sculpt map the two meshes' walkable
    sets are DISJOINT -- 49 points ours, 435 theirs, 0 shared -- and the
    authored spawn is not on ArenaNet's mesh at all, so the server suspended
    collision on arrival. 16 runs in the vault carry that line.

    Startup is the only moment both halves hold: the archive contains whatever
    was installed, and nothing has opened it yet. This cannot rescue a run whose
    head was just armed to zero -- there is no compiled mesh to read, by design,
    and that run is the one that PRODUCES it. Serving an authored mesh is
    inherently two runs; this makes the second one work rather than letting the
    first pretend.
    """
    cfg = MAP_STATIC_CONFIG.get(map_id)
    if cfg is None:
        print(f"[map] map {map_id} has no static config, so its navmesh cannot "
              f"be pre-warmed; it will be read at instance load, which is late "
              f"-- see prewarm_pathmap()")
        return None
    pm = load_pathmap(cfg[0])
    if pm is None:
        print(f"[map] PRE-WARM FAILED for map {map_id} (file id 0x{cfg[0]:X}); "
              f"this run serves NO collision")
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
# is [agent_id, byte] -- SEVEN bytes, not ten: schema/overrides.json gives
# GAME_CMSG 38 as [msg_header, agent_id, byte] with declared_unpack_size 7, and
# the capture above framed clean at values=[32806, 10, 0]. A dword there would
# have desynced the stream. The target was agent 10, ours.
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
#
# AND THE CLIENT HAS NOT SENT ONE SINCE 2026-08-06. MEASURED 2026-08-13 over
# every `vault/captures/gamesrv/*.jsonl` -- 425 connections, 17,770 framed c2s
# messages -- 0x0033 occurs ZERO times. Its 206 recorded occurrences all sit in
# `vault/captures/authsrv/`, the older capture tree, and the last one is stamped
# 2026-08-06T19:04:40Z. ArenaNet's own two live sessions carry none either
# (0 of 919 c2s). The arm below is kept anyway, on purpose: WE DO NOT KNOW WHY
# IT STOPPED. The paragraph above is the reasoning that put it there and it was
# not wrong when written; deleting the constant would delete the evidence that
# the reasoning has since been overtaken, and a future session would rediscover
# arm 1 from scratch. What changed around that date is unidentified -- the arm-0
# finding of 2026-08-11 (see GAME_CMSG_ATTACK_AGENT) is the leading candidate
# and is not proof, because it explains 0x0026 appearing and not 0x0033 ceasing.
GAME_CMSG_INTERACT_PLAYER = 0x0033

# Arm 2 of that same six-arm world-action switch, and the one the client
# ACTUALLY sends: 29 of 919 c2s messages (3.2%) across ArenaNet's own two live
# sessions, against zero 0x0033. `schema/overrides.json` names it INTERACT from
# that traffic -- sent when the operator clicked and then talked to a friendly
# NPC, always carrying that NPC's agent id, and never produced by clicking
# another PLAYER.
#
# IT IS NOT AN ATTACK, and that is why it gets its own arm below rather than
# joining 0x0026/0x0033. The separation is falsifiable and was measured on
# ArenaNet's wire (overrides.json, GAME_CMSG 38): 4 of 5 distinct 0x0026 targets
# enter a GAME_SMSG 0x00A0 kind-4 auto-attack exchange, 0 of 10 distinct 0x0039
# targets ever do, and streams carrying 0x0039 with no 0x0026 contain no combat
# at all. Folding it into the attack arm would make this server start swinging
# at every quest giver the player talks to -- inventing a behaviour ArenaNet's
# own server demonstrably does not have.
GAME_CMSG_INTERACT_AGENT = 0x0039

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

# THE THREE PURE-INBOUND ONES. Each is fully named in `schema/overrides.json`
# with the client-side evidence beside it, each is among the largest single
# drops on our own wire, and each costs one dict assignment to stop dropping.
# Nothing below them SENDS anything or acts on what it stores: the point is that
# a measured fact the client hands us stops going on the floor, not that this
# server grows missions, targeting or a facing model. Storing is the whole
# handler; the day one of these drives behaviour it needs its own study.
#
# 0x0092 MISSION_MASK_REPORT -- a 112-byte progress bitmask, one bit per mission
#   id, bounded by the client's own MsCliMsg.cpp:181 assert
#   `missionMaskBytes <= MISSION_MASK_BYTES`. MEASURED 2026-08-13 over the whole
#   loopback tree: 803 samples, 803 of them exactly 112 bytes, and 747 of 803
#   entirely zero -- because nothing this server sends ever sets a bit. The 56
#   non-zero ones are the interesting minority and were invisible until now.
GAME_CMSG_MISSION_MASK_REPORT = 0x0092
# 0x0079 -- the ONLY c2s reply any GAME_SMSG opcode in the sweep ledger provokes.
#   334 rows, 3 REPLIED, and two of them (0x0166 and 0x0167) name opcode 121 as
#   what came back; the third is the ping. Its layout is a `msg_header` and
#   NOTHING ELSE -- declared_unpack_size 2, no fields -- so the message carries no
#   information beyond its own arrival, and an arm can only record that it came.
#   That is worth doing anyway: it is the one place where a message WE chose to
#   send makes the retail client answer, so it is the shortest closed loop
#   available to this server, and until now our side of it fell off the end of
#   the dispatch chain into D9(a)'s counter.
#   NOT NAMED on purpose. Two stimuli reaching one reply does not say what the
#   reply MEANS, and 0x0166/0x0167's own names are unknown -- naming this
#   `ACK_SOMETHING` would be the invention this repo keeps refusing. The arm
#   records arrivals so the loop is visible; the name waits for evidence.
GAME_CMSG_UNNAMED_ACK_0079 = 0x0079
# 0x00C1 TARGET_SELECT -- [effective_selection, auto_selection]. Field 1 is what
#   every subsequent target-bearing message names (53 of 53 on ArenaNet's wire);
#   0 clears the selection. FREE CORROBORATION, and the reason this one is worth
#   writing down rather than merely handling: the override entry was written
#   from 75 live sends and says `field1 == field2 nonzero occurs 0 of 75`, which
#   the client's own `je -> xor ebx,ebx` branch predicts. Our loopback tree now
#   holds 363 of them, a 4.8x larger sample from a different server, and field 2
#   is 0 in 363 of 363 with 0 collisions. Nothing was arranged to make that come
#   out; the messages were being decoded and discarded the entire time.
GAME_CMSG_TARGET_SELECT = 0x00C1
# 0x0040 ROTATE_PLAYER -- [angle, turn_amount], and THE TRAP IS THE TYPING. Both
#   payload fields are marshalled `dword` and hold IEEE-754 float32 VALUES; the
#   client's own SEND table says u32, so the catalog is correct and must not be
#   "fixed" to float (test_rotate.py exists to make that edit go red). Reading
#   values[1] as a number rather than as bits gives 2139095040 where the answer
#   is +inf. MEASURED 2026-08-13 over the loopback tree, 108 samples: 64 finite
#   angles, every one inside +/-pi (max 3.0183), 28 exactly +inf and 16 exactly
#   -inf -- the two .rdata sentinels the override entry names, meaning "turning
#   continuously, sign gives the direction". The raw dword is kept beside the
#   float so nothing is lost to the reinterpretation.
GAME_CMSG_ROTATE_PLAYER = 0x0040

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

# Set from --player-flags. The VALUE half of GAME_SMSG 0x003C's (value, mask)
# pair; the mask is always 7 (423 of 423 live sends). None means send nothing,
# which is this server's behaviour up to 2026-08-13 and is therefore the control
# arm rather than a disabled feature.
PLAYER_FLAGS = None

# Set from --netgraph. One byte of UI-overlay flags sent once, after the
# instance loads, as GAME_SMSG_UI_OVERLAY_FLAGS. None means send nothing at
# all, which is deliberately distinct from sending 0: the handler CLEARS three
# bits before it sets any, so a 0 byte is an instruction to turn all three off
# and is a different experiment from staying silent.
NETGRAPH_FLAGS = None

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
# The burrow re-create skips the NPC definition (measured per-instance, 10.8).
# This is the way back, and it has to be READ FROM THE ROW to exist at all:
# `burrow_tick` reads entry.get("resend_definition"), `entry` is a closed literal
# built in spawn_enemy, and content fields reach it only by being named here. The
# comment promising this hatch shipped before the wire did, so the documented
# mitigation for a silent client assert was unreachable.
ENEMY_RESEND_DEFINITION = bool(_ENEMY.get("resend_definition", False))
# Whether this spawn fights back. Default TRUE -- the point of the rung -- but a
# row may turn it off, and it is read here rather than assumed so that a probe
# session can put a passive body in the world without editing code. Same wiring
# rule as above: `entry` is a closed literal, so a key reaches it only by being
# named here and in spawn_enemy.
ENEMY_ATTACKS_BACK = bool(_ENEMY.get("attacks_back", True))
ENEMY_MAX_HEALTH = _ENEMY["max_health"]
# Allegiance BY NAME, so a content row can say what a body is without carrying a
# FourCC. The three values are the client's own constants (agents.py, read out
# of the image); "hostile" is any unrecognised value, which is why it is the
# default here and why a typo in a row reads as an enemy rather than as nothing.
ALLEGIANCE_BY_NAME = {
    "hostile": agents.ALLEGIANCE_HOSTILE,
    "player": agents.ALLEGIANCE_PLAYER,
    "noncombatant": agents.ALLEGIANCE_NONCOMBATANT,
}
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

# THE OTHER HALF OF R4a: something swings back. Until 2026-08-11 every combat
# message this server sent flowed one way -- the player hit things and nothing
# could hit the player, which is the half PLAN.md 3's R4a row has named as missing
# since 2026-08-06 ("an ettin swings at you and you die").
#
# THE MECHANISM IS ALREADY PROVEN, and by an accident rather than by a design. Read
# hit_enemy's comment on GV_ATTACK_STARTED: an early version put the ENEMY in slot
# 1, and the client animated the enemy and then asserted on m_attackInterval -- it
# could only assert on an agent whose attack speed was zero. So slot 1 is the
# swinger, and a non-player agent in it swings, PROVIDED it has been given an
# attack speed. Our Hatcher has one (0x0035, ENEMY_ATTACK_SPEED). This code is that
# accident aimed on purpose.
#
# WHAT IS OURS RATHER THAN MEASURED: both numbers below, and the proximity rule.
# Real Guild Wars aggro is a leash with a pull radius and a give-up distance, and
# an NPC walks to its target; ours stands still and swings when the player is
# close enough. Nothing here is a claim about retail.
AGGRO_RANGE = 1200.0       # units. Ours. Inside ATTACK_RANGE so a fight is mutual.
ENEMY_HIT_FRACTION = 0.10  # of the PLAYER's maximum, so ~10 swings to drop them
# ONE TICK between the death bit clearing and the two pool refills, and the value is
# MEASURED rather than chosen. The client checks
# `min(f32 @ +0x130, +0x134) == 0.0` when a character is resurrected and logs
# `Health non-zero on resurrect` when it is not; sending the three messages in one
# burst failed that check on EVERY revive. Three runs of the same length, differing
# only in this constant (studies/agentprops 1f):
#
#     0.00s (burst)   13 revives, 13 complaints
#     0.05s (1 tick)  11 revives,  0 complaints
#     0.25s (5 ticks) 13 revives,  0 complaints
#
# So the check runs after our clear is processed and before the next tick's messages,
# and one tick is enough. Expressed as TICK_SECONDS rather than 0.05 so it stays one
# tick if the rate moves. RURIK_REVIVE_DEFER overrides it; 0 restores the old burst,
# which is what makes the control reproducible.
REVIVE_REFILL_DEFER = float(os.environ.get("RURIK_REVIVE_DEFER", "") or TICK_SECONDS)

PLAYER_REVIVE_AFTER = 10.0 # seconds face-down. Longer than an agent's 8.0 on
                           # purpose: this one interrupts a person.

# A SWING IS NOT INSTANT, and the first version of this code made it one.
# OBSERVED 2026-08-11 from ArenaNet's own traffic (studies/enemy/PLAN.md 11.1,
# capture 20260807T143055 connection :64103): a Plague Worm's swing is
# ATTACK_STARTED, then 0.880-0.919 s of nothing, then the landing. Six complete
# swings, mean 0.899. We sent all three messages in the same instant, so the
# damage number appeared on the same frame the animation began.
#
# AND THAT CONSTANT IS REFUTED, 2026-08-11, by the OTHER live capture -- which was
# already in the vault on the day it was adopted. See studies/monsterai/FINDINGS.md
# 3.5 and 10. The comment that stood here said "all six swings came from ONE agent
# at ONE declared attack speed (2.00 s), so whether the windup scales with the
# weapon or is fixed cannot be told from this corpus. Taking the constant is the
# smaller claim." Every clause of that is true and the conclusion still does not
# follow, because a constant is only the smaller claim when it is applied at the
# speed it was measured at, and our Hatcher declares 1.33.
#
# Re-measured over BOTH captures, pairing conservatively (a start pairs only with a
# landing preceding that attacker's next start, so a truncated swing is DROPPED):
#
#     declared 2.00 s   n=18   agents 40, 48 (mon1)   0.880 - 0.920 s
#     declared 1.75 s   n=24   agents 46, 47 (band)   0.746 - 0.794 s
#
# The two windup clusters DO NOT OVERLAP -- an 86 ms gap, about twice either
# cluster's own width -- while the two RATIO bands do. In seconds the creatures
# disagree; as a fraction of each creature's own declared attack base they agree.
# Pooled: mean 0.4458, sd 0.0073, range [0.4263, 0.4600], n=42.
#
# So the fixed model is dead, and 0.899 was worse than merely fixed: paired with our
# declared 1.33 it implies a ratio of 0.6759, which is 47% ABOVE the largest ratio
# ever observed. It lost to both surviving models, not just to this one.
#
# TWO CONFOUNDS, stated because a ratio read off two speeds is not a law:
#   * two declared speeds across two creature pairs cannot separate "scales with
#     declared speed" from "is per-creature and happens to track speed";
#   * the 1.75 group carries the `band` token, so the comparison crosses an
#     allegiance class as well as a speed. The `mon1` cluster ALONE still refutes
#     0.899-at-1.33, so the correction stands either way -- but a third speed
#     inside one class is what would close it, and the corpus has no third: one
#     agent declares 2.475 and never lands a paired swing.
SWING_WINDUP_RATIO = 0.4458   # of the attacker's OWN declared attack base
SWING_WINDUP_MIN = 0.4263     # the observed band, used only by the test
SWING_WINDUP_MAX = 0.4600


def swing_windup(attack_speed):
    """Seconds between ATTACK_STARTED and the landing, for a given attack base.

    A FRACTION of the attacker's own declared speed rather than a constant. Our
    Hatcher declares 1.33, so this returns 0.593 s where the old constant returned
    0.899 -- a value no observation supports under either surviving model.
    """
    return SWING_WINDUP_RATIO * float(attack_speed)

# IT WALKS NOW. Until this, `AGGRO_RANGE` was doing two jobs -- deciding both when
# a hostile notices the player and when it can reach them -- so a Hatcher rooted to
# its spawn point swung at anything within 1200 units, hitting people across a
# courtyard it never crossed. The two are separated here: AGGRO_RANGE is the notice
# and the leash, ENEMY_MELEE_RANGE is the reach.
#
# ALL THREE NUMBERS ARE OURS. Nothing measured them, and the wiki's aggro-bubble
# figures are about a mechanic (a moving circle, a leash back to a spawn anchor,
# a call-to-arms radius) that none of this implements.
ENEMY_MELEE_RANGE = 150.0  # close enough to swing. Ours.
ENEMY_MOVE_RATE = 0.75     # fraction of the 288 u/s reference, so 216 u/s -- slower
                           # than the player on purpose, so you can walk away
ENEMY_DEST_RESEND = 120.0  # how far the player must move before the destination is
                           # re-announced. Every tick would be 20 messages a second
                           # at a client that only needs the endpoint.

# AND IT TURNS TO FACE YOU. GAME_SMSG_AGENT_UPDATE_ROTATION (0x002E) has been
# defined and documented in this file for days and never once sent: an absolute
# facing angle in radians and a turn rate, both marshalled u32 and both holding
# float32 -- the ROTATE_PLAYER trap, and reading them raw is what made an earlier
# draft of test_smsgnames compare garbage against pi.
#
# EVERY NUMBER BELOW EXCEPT THE EPSILON IS ARENANET'S.
#   * The angle convention is atan2(y, x). Not assumed: test_rotate.py scores the
#     client's own 0x0040 sends against atan2 of a nearby 0x003D DIRECTION vector
#     and beats a null model built from the same corpus. (Its first version paired
#     against the POSITION vec2 instead and scored 0 of 163 -- a position has a
#     perfectly plausible atan2 too, which is why that failure was silent.)
#   * The angle is absolute and lives in [-pi, pi]; +/-inf are the client's own
#     free-spin sentinels (test_smsgnames, every finite sample in range).
#   * The turn rate is bounded, quantised, and PER-CREATURE rather than
#     per-message. 2*pi/3 is the largest ArenaNet was seen to use, to the bit.
#
# WHAT IS NOT ESTABLISHED, and this code does not depend on it: which SIGN is a
# left turn. test_rotate.py refuses to pin that on 121/189 and 106/169, which is
# real and far too weak to write down. An absolute facing needs no such claim.
ENEMY_TURN_RATE = 2.0943951023931953   # 2*pi/3 rad/s, ArenaNet's own maximum
ENEMY_FACING_EPSILON = 0.15            # radians (~8.6 deg) before re-announcing.
                                       # Ours. Every tick is 20 messages a second.

# AND IT CASTS. OBSERVED 2026-08-11, and the corpus answer was NOT the one this
# server would have guessed: ArenaNet does not announce an NPC's skill on 0x00E3.
# Every 0x00E3 in the whole live corpus -- 6 of 6 -- names the PLAYER, because
# 0x00E3 is the confirmation of a cast the CLIENT initiated and the client says so
# in its own log when the echo is wrong ("Pending skill %u copy %d not found").
# An NPC's cast is not client-initiated and has nothing to confirm.
#
# What the corpus does carry is ONE NPC skill activation, on the int channel:
#
#     0x009F [value 60 = GV_SKILL_ACTIVATED, agent 36, skill 83]
#
# n=1, in 20260807T143055 connection :62994 (the stamp read 20260810T235916 here
# until 2026-08-11 -- the connection was always right and the capture was not),
# and n=1 is thin enough that it is written down here rather than dressed up. It
# is still the only evidence there is, and it beats inventing a message.
#
# AND THE SHAPE DIFFERS BY ACTOR, which is the actionable half and was not written
# down anywhere until studies/monsterai/FINDINGS.md 10. All FIVE activations in the
# corpus carry value 60, and they do not share a message:
#
#     NPC     x1   0x009F  [60, agent, skill]           <- no target slot
#     player  x4   0x00A0  [60, caster, target, skill]
#
# We send the 0x009F form, so this code is right -- but it was right without that
# being recorded, which is the same as being right by luck. (A near miss worth
# recording so nobody
# re-finds it: 0x00A0 value 20 GV_EFFECT_ON_TARGET looks NPC-exclusive on a census
# keyed by slot 2, and is not -- in context the player casts, then value 20 lands
# with the player's TARGET in that slot. Different value ids put different roles
# in the same slot, which is the trap hit_enemy's own comment is about.)
#
# THE SKILL AND ITS TIMINGS ARE ARENANET'S, from the client's own table via
# toolkit/clientscan/skilltable.py. 276 is chosen because its profession matches
# the one this server already declares for the Hatcher (3, sent as 0x00A6 at
# spawn) -- not picked from nowhere. Its activation and recharge are the table's,
# not ours, which is why they are odd numbers.
#
# NOT THE PLAYER'S CAST PATH. The skill-dispatch arm below carries a standing note
# that skill COMPLETION is being built on another branch and not to add to it.
# This does not: it is an NPC announcing its own cast, and it touches nothing the
# player's 0x0046/0x0027 handling uses.
# THE BAR. Four skills rather than one, each with its OWN recharge.
#
# A TESTING FIXTURE, AND THE POLICY THAT USES IT IS TOO. Owner's ruling
# 2026-08-11: we are not deciding casting AI by whatever is convenient here, and a
# deeper dive into monster AI comes first. The bar exists so the MECHANISM can be
# exercised and tested -- the message shape, per-slot recharge, the activation
# window, the reachability of every slot. Which skills, in what order, on what
# selection policy, are all placeholders and are marked as such in pick_skill.
#
# WHOSE BAR THIS IS, and the answer is: OURS, and it has to be said plainly.
# studies/presearing/MANIFEST.md 7 read three Pre-Searing creature pages in full
# and found NO base skill bar on any of them -- the Restless Corpse's is
# explicitly "None", the Grawl's turned out to be INVENTED by an earlier pass, and
# the region's only non-Charr boss has no Skills section at all. Our Hatcher is a
# Lakeside creature. So this is a test fixture that exercises the mechanism, NOT a
# claim about what a Hatcher does in retail, and a content row is the place to put
# a real bar the day one is sourced.
#
# WHAT IS ARENANET'S: every id, activation and recharge below, out of the client's
# own table via toolkit/clientscan/skilltable.py on build 38797. All four are
# profession 3 -- the profession this server already declares for the Hatcher at
# spawn (0x00A6) -- campaign 1, and each has a different type_code, so the bar is
# four different kinds of thing rather than one skill four times.
#
# CORRECTION 2026-08-11: this comment used to say "campaign 1, non-elite". SKILL
# 276 IS ELITE -- its flags word carries FLAG_ELITE (bit 2), which the table's own
# decoder reports as elite=True, and bit 2 is set on 391 of 3,443 rows so it is a
# real field rather than a one-row artifact. A monster with an elite skill is not
# absurd (retail bosses have them), but the claim was made without checking and
# nothing checked it, which is the point: see section 7c below, added in the same
# commit, which reads the live table and would have caught it.
#
# WHAT IS OURS: the selection of these four, the priority order, and the damage.
# Recharges of 2, 5, 8 and 2 are the table's and are what makes the order
# observable: the 8 s skill fires once and the 2 s ones cycle.
#
# WHAT IS MODELLED AND WHAT IS NOT. The table also gives each of these four an
# AFTERCAST of 0.75 s and an energy cost (5, 5, 5, 10). Neither is modelled --
# aftercast is wirable from the same read and is not wired; energy is a pool the
# client never sees (PLAN.md 1.7). studies/monsterai/FINDINGS.md 8.2.
#
#                  id  activation  recharge   type_code
ENEMY_SKILL_BAR = ((276, 0.75, 2.0),   # 5
                   (253, 1.00, 5.0),   # 4
                   (312, 0.75, 8.0),   # 10
                   (289, 0.75, 2.0))   # 6
ENEMY_SKILL_FRACTION = 0.25   # of the player's maximum, for EVERY skill on the
                              # bar. OURS, and flat on purpose: per-skill effects
                              # are not modelled and giving each one a different
                              # number would be four inventions instead of one.
                              # The client carries every real number and we do not
                              # read it yet (studies/skills/FINDINGS.md)

# The bar this spawn fights with. A content row may give `skills = [[id, act,
# recharge], ...]`, and an EMPTY list leaves the agent on plain swings. Named here
# for the same reason attacks_back and resend_definition are: `entry` is a closed
# literal and a content key reaches it only by being copied. It lives HERE rather
# than beside the other two _ENEMY reads because it defaults to a constant defined
# in this block -- module order is not something test_srclint checks, and the
# first version of the single-skill form raised NameError at import, which only
# running the test could show.
ENEMY_SKILLS = tuple(tuple(row) for row in
                     _ENEMY.get("skills", ENEMY_SKILL_BAR))


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


def ping_tick(send, state, conn_id):
    """Send `0x000C` every PING_SECONDS. Called from the world tick.

    First leg of the three-message round trip: server `0x000C` (empty) ->
    client `0x0009` (its perf state) -> server `0x000D[elapsed_ms]`, which the
    client plots on its net graph. studies/smsg established the whole exchange
    from the client's own handler table; the parts that constrain THIS function
    are that the cadence is 5.000 s and that the message carries nothing at all
    -- 2 bytes, header only, per `schema/messages.json`.

    ONE OUTSTANDING PING AT A TIME. The corpus is 79/79 requests answered
    inside their own 5 s window and 0/79 replies unprompted, so the client
    never queues these. We stamp `ping_sent` and do NOT overwrite it while a
    reply is outstanding: if the client is late or silent, sending a second
    request would move the start time and make the eventual round trip read
    SHORTER than it was. A latency meter that under-reports when the link is
    bad is worse than one that reports nothing.

    TAPE-SAFE BY CONSTRUCTION, and worth stating because it is not local: this
    runs only inside `world_tick`, and `world_tick` is started only when
    `TAPE_EVENTS is None`. Its partner is safe the same way -- under a tape the
    game c2s chain `continue`s before any arm, so nothing of ours answers the
    client's `0x0009` either. That matters more than it looks: a tape run
    requires ZERO messages of our own on the channel, and PLAN.md §3.4 records
    a run whose client assert was un-attributable precisely because our 20 Hz
    ticker was talking over ArenaNet's recording. A 5 s timer would have been a
    slower, subtler version of the same contamination.
    """
    now = time.perf_counter()
    last = state.get("ping_at")
    if last is not None and now - last < PING_SECONDS:
        return
    state["ping_at"] = now
    if state.get("ping_sent") is None:
        # No reply outstanding: this is a fresh round trip, so start the clock.
        state["ping_sent"] = now
    else:
        # Previous request never answered. Keep the ORIGINAL start time so the
        # eventual 0x000D tells the truth, and count the miss for the operator.
        state["ping_missed"] = state.get("ping_missed", 0) + 1
    send(GAME_SMSG_CLIENT_PERF_REQUEST, [], "CLIENT_PERF_REQUEST", quiet=True)


def handle_perf_report(values, send, state, conn_id):
    """Answer the client's `0x0009` with `0x000D[elapsed_ms]`.

    The reply's two dwords are the client's own GrPerf frame interval and an
    FrApi flag; they carry nothing from our request and we do not yet know what
    to do with them, so they are recorded and not acted on. What we owe back is
    the elapsed time since OUR `0x000C`, which is what the client graphs.

    UNPROMPTED REPLIES ARE DROPPED. 0 of 79 in the corpus lacked a request
    within 1.0 s before them, so a reply with no outstanding request is not a
    thing this protocol does -- inventing an elapsed time for one would put a
    fabricated number on the net graph, which is the one place an operator
    would read it as measured.
    """
    sent_at = state.get("ping_sent")
    if sent_at is None:
        print(f"[c{conn_id}] CLIENT_PERF_REPORT with no request outstanding -- "
              f"dropped rather than answered with an invented latency",
              flush=True)
        return
    state["ping_sent"] = None
    elapsed_ms = int(round((time.perf_counter() - sent_at) * 1000))
    # Negative is impossible from perf_counter, but a clamp at 0 costs nothing
    # and the field is an unsigned dword on the wire.
    elapsed_ms = max(0, elapsed_ms)
    state["ping_last_ms"] = elapsed_ms
    if elapsed_ms > LATENCY_MAX_MS:
        # Above the client's own cutoff this message is dropped on arrival, so
        # sending it would be a no-op that LOOKS like a working feature here.
        print(f"[c{conn_id}] round trip {elapsed_ms} ms exceeds the client's "
              f"{LATENCY_MAX_MS} ms cutoff -- not sending LATENCY_REPORT, the "
              f"client would discard it", flush=True)
        return
    send(GAME_SMSG_LATENCY_REPORT, [elapsed_ms],
         f"LATENCY_REPORT({elapsed_ms} ms)", quiet=True)


def attack_tick(send, state, conn_id):
    """Keep swinging at whatever the player last clicked."""
    if state.get("player_dead"):
        # A dead player does not keep hitting things. Cheap, but it is the
        # difference between a death and a pause in the animation.
        return
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

    # THE GUARD RUNS BEFORE ANY EFFECT -- before the timer is consumed, before
    # the health is bookkept, before the first send. Until 2026-08-14 the
    # _fraction call sat inline in the damage send below, which meant a refused
    # value left GV_ATTACK_STARTED alone on the wire (an attack with no damage
    # and no close), a health pool bookkept to a kill nothing was told about,
    # and a swing timer eaten by a swing that never happened -- measured, not
    # reasoned: test_guards.py section 1 went red on exactly those three
    # counts against the pre-guard tree. Dormant while HIT_FRACTION is a
    # constant; load-bearing the day step 8 computes it (studies/combat).
    frac = _fraction(-HIT_FRACTION, agents.PROP_DAMAGE, "one swing")
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
         [agents.PROP_DAMAGE, target_id, PLAYER_AGENT_ID, frac],
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


def handle_skill_press(values, send, state, conn_id, opcode):
    """One skill press, either half (0x0046 USE_SKILL or 0x0027 ATTACK_SKILL).

    Extracted from the dispatch chain 2026-08-14 so the connection-thread
    combat path is testable without a socket -- the same reason
    `frame_pending` and `handle_perf_report` exist. The dispatch arm keeps the
    opcode condition (test_cmsgnames section 6 pins it) and the dead-player
    guard; everything the press DOES lives here.
    """
    # Confirm the cast by echoing the key the client is waiting on. If the
    # echo is wrong the client says so in its own log -- 'Pending skill %u
    # copy %d not found' -- which makes this one of the few things in the
    # project that reports its own failure.
    which = ("USE_SKILL" if opcode == GAME_CMSG_USE_SKILL
             else "ATTACK_SKILL")
    skill_id, copy, target = values[1], values[2], values[3]
    send(GAME_SMSG_SKILL_ACTIVATED,
         [PLAYER_AGENT_ID, skill_id, copy],
         f"SKILL_ACTIVATED(skill {skill_id}, copy {copy}"
         f" via {which})")
    print(f"[c{conn_id}] skill {skill_id} (copy {copy}) at "
          f"agent {target or 'nothing'}", flush=True)
    # TRIED AND IT DID NOT WORK, recorded so it is not retried blind: sending
    # generic values 60 (skill_activated) then 58 (skill_finished) here left
    # the cast exactly as stalled as before. They may still be part of the
    # answer -- they were never going to be all of it -- but on their own they
    # change nothing visible, so they are out rather than sitting in the code
    # looking like they work. agents.py keeps the ids.
    #
    # (Until 2026-08-14 this comment deferred to a skill-completion branch
    # that a full ref scan shows never existed. The lifecycle work is
    # studies/combat/PLAN.md step 3.)
    # A skill aimed at something hostile does what a click does. Whether a
    # skill should damage at all, and by how much, is OURS -- the client
    # carries every real number (studies/skills/FINDINGS.md) and we do not
    # read it yet.
    #
    # THE SAME ValueError CONTRACT world_tick has, because this runs on the
    # CONNECTION thread: handle's except tuple is ConnectionError /
    # socket.timeout / OSError only, so an escaping refusal would run the
    # finally, close the socket, and disconnect the client over a number that
    # was -- by design -- never sent. The world tick logs and keeps ticking
    # (its except at the tick body); a skill press logs and keeps the
    # connection. Refusing the VALUE must never cost more than the value.
    if target:
        try:
            hit_enemy(send, state, target, conn_id)
        except ValueError as ex:
            print(f"[c{conn_id}] skill press REFUSED a value: {ex}",
                  flush=True)


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
        # ONE TICK before the refills, the same as the player path. The client's
        # resurrect check is on the CHARACTER and does not care whose it is: 2 of the
        # vault's 49 `Health non-zero on resurrect` lines name `Corpse of Hatcher
        # [Collector]` rather than the player.
        #
        # MEASURED 2026-08-13, unattended, on the same standard as the player path:
        # two runs identical but for this constant, 21 player hits and 3 agent deaths
        # each, 3 of 3 complaints on the burst and 0 of 3 with one tick between.
        #
        # Reaching it needed TWO things that took four runs to find, and neither was
        # the input everyone reached for first: `--practice-target`, because with the
        # hostile fighting back the player loses the race (25 into 100 HP is four
        # hits; killing it takes seven) and never lands one; and `--explorable`,
        # because an OUTPOST forbids attacking -- in one the client selects a target
        # (0x00C1 goes out on every press) and no attack ever follows.
        if REVIVE_REFILL_DEFER > 0.0:
            agent["refill_due_at"] = now + REVIVE_REFILL_DEFER
            print(f"[c{conn_id}] agent {agent_id} is back up "
                  f"(refill deferred {REVIVE_REFILL_DEFER:.2f}s)", flush=True)
            continue
        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
             [agents.PROP_HEALTH_MAX, agent_id, int(agent["max_health"])],
             f"restore max health on agent {agent_id}")
        # Re-asserting the SAME maximum refills nothing, which is why a revived
        # body stood up with an empty bar while our own bookkeeping said full --
        # so it still took a full seven swings to drop, and the bar never moved.
        # OBSERVED 2026-08-06.
        #
        # Property 34 is a FRACTION of the pool, and sending `max_health` here
        # CRASHED THE CLIENT -- CharPool.cpp:84, `fraction <= 1.0f`, two seconds
        # after the first kill this server ever drove to a revive (see `_fraction`,
        # which now refuses the whole class). 1.0 is a full pool.
        #
        # PROPERTY 34 IS A SETTER: it sets the pool to `fraction x maximum`. So 1.0
        # here does not ADD a full bar, it SETS the bar full, which is exactly what
        # a revive wants and is why this works from a pool the death path zeroed.
        # OBSERVED 2026-08-11 twice over -- the post-revive frame shows a full bar
        # against a mid-fight frame showing a drained one, and the `pool_fraction`
        # probe pinned the semantics directly (studies/agentprops/FINDINGS.md 1e:
        # the orb went 100 -> 90 on property 16 at -0.10, then to the floor of 1 on
        # property 34 at -0.50, where a delta predicts 40).
        #
        # It is also why the client asserts `fraction <= 1.0f`: a setter cannot
        # exceed the maximum, so `max_health` here was never merely too large, it
        # was the wrong KIND of number.
        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
             [agents.GV_HEALTH, agent_id, agent_id,
              _fraction(1.0, agents.GV_HEALTH, "refill to a full pool")],
             f"refill bar on agent {agent_id}")
        print(f"[c{conn_id}] agent {agent_id} ({agent['name']}) is back up",
              flush=True)


def player_pools(state):
    """The player's live health, lazily. Nothing tracked it before this rung.

    The client was told PLAYER_HEALTH once at spawn and the server then forgot the
    number, which was fine while nothing could damage the player and is exactly the
    gap that made "you cannot die" a property of the code rather than a decision.
    """
    state.setdefault("player_health", float(agents.PLAYER_HEALTH))
    state.setdefault("player_dead", False)
    state.setdefault("player_died_at", 0.0)
    return state


def enemy_attack_tick(send, state, conn_id):
    """Hostile agents swing at the player. The other half of R4a.

    A SNAPSHOT, for the reason revive_due takes one: this runs on the world-tick
    daemon thread and burrow_tick can remove an agent in the same tick. Walking the
    live dict raises "dictionary changed size during iteration" INSIDE the tick,
    which stops the world for the rest of the session with a traceback nowhere near
    the cause.
    """
    player_pools(state)
    if state["player_dead"]:
        # Nothing swings at a corpse. Without this the player is re-killed every
        # interval while face-down and the revive never gets a clean window.
        return
    px, py = state.get("pos", (0.0, 0.0))
    now = time.time()
    for agent_id, agent in list(state.get("agents", {}).items()):
        if agent_id not in state.get("agents", {}):
            continue
        if agent["dead"] or not agent.get("attacks_back"):
            # A corpse does not land the swing it was mid-way through. ArenaNet's
            # own 7th swing in the Lakeside tape was truncated exactly this way,
            # 0.24 s in, when the player killed the worm.
            agent["swing_lands_at"] = None
            agent["cast_lands_at"] = None
            agent["casting"] = None
            continue
        if agent.get("allegiance") != agents.ALLEGIANCE_HOSTILE:
            continue
        # A body mid-burrow is half in the world and must not swing out of it. The
        # hidden ones are not in state["agents"] at all, so this covers only the
        # 2.00 s transitions either side.
        if agent.get("effects", 0) & agents.EFFECT_TRANSITION:
            continue
        ax, ay = agent["pos"]
        # REACH, not notice. This read AGGRO_RANGE until the chase existed, which
        # let a rooted agent hit the player from 1200 units away.
        if math.hypot(ax - px, ay - py) > ENEMY_MELEE_RANGE:
            agent["swinging"] = False
            agent["swing_lands_at"] = None
            agent["cast_lands_at"] = None
            agent["casting"] = None
            continue
        # Its OWN weapon speed, not the player's. The client was told this agent's
        # attack speed at spawn (0x0035) and animates to it; swinging faster than we
        # declared is how the animation and the damage numbers come apart.
        # `or` rather than a default, and the zero case is the point: an agent
        # whose declared attack speed is 0 is exactly what took the client down on
        # m_attackInterval (hit_enemy's comment). Falling back to a real interval
        # keeps a mis-declared agent from swinging every tick forever.
        interval = agent.get("attack_speed") or ENEMY_ATTACK_SPEED
        if not agent.get("swinging"):
            agent["swinging"] = True
            # Swing on arrival rather than after a full interval -- the same call
            # begin_attack makes for the player. A fight that opens with a second
            # and a half of nothing reads as a fight that did not start.
            agent["last_swing"] = 0.0
            print(f"[c{conn_id}] agent {agent_id} ({agent['name']}) attacks the "
                  f"player", flush=True)
        # A CAST IN FLIGHT BEATS EVERYTHING, and is resolved before a swing can
        # start -- otherwise a slow tick lets an agent cast and swing at once.
        cast_due = agent.get("cast_lands_at")
        if cast_due is not None:
            if now >= cast_due:
                agent["cast_lands_at"] = None
                land_skill(send, state, agent_id, agent, conn_id)
            continue

        # TWO PHASES, because a swing takes time. A landing that is due is always
        # resolved before a new swing is started, so a slow tick cannot make an
        # agent start twice and land once.
        due = agent.get("swing_lands_at")
        if due is not None:
            if now >= due:
                agent["swing_lands_at"] = None
                land_swing(send, state, agent_id, agent, conn_id)
            continue

        # A SKILL GOES FIRST when the bar has one ready. WHICH one is pick_skill's
        # business and is a TESTING FIXTURE -- read its docstring before changing
        # anything here. This comment used to say "first ready in bar order, which
        # makes the bar a priority list -- roughly what a Guild Wars monster does";
        # the selector became round robin two commits later and the claim was never
        # true anyway. studies/monsterai/FINDINGS.md is the dive that went looking:
        # a monster's skill-selection policy is not in the client, is not on the
        # wire, and needs a capture campaign (its 7.6, tier 2).
        #
        # A recharge runs from the START of the cast, which is what the client's
        # table means by one. That is a RECONSTRUCTION from the table's semantics,
        # not an observation: no NPC in the corpus casts twice, so there is no
        # recharge cycle anywhere to tell start-triggered from finish-triggered.
        slot = pick_skill(agent, now)
        if slot is not None:
            skill_id, activation, recharge = agent["skills"][slot]
            agent["skill_ready"][slot] = now + recharge
            agent["last_slot"] = slot          # the round-robin cursor
            agent["casting"] = slot
            agent["last_swing"] = now      # a cast is not a free swing
            face_player(send, state, agent_id, agent, conn_id)
            send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                 [agents.GV_SKILL_ACTIVATED, agent_id, skill_id],
                 f"agent {agent_id} casts skill {skill_id}")
            agent["cast_lands_at"] = now + activation
            print(f"[c{conn_id}] agent {agent_id} ({agent['name']}) casts skill "
                  f"{skill_id} (slot {slot + 1} of "
                  f"{len(agent['skills'])})", flush=True)
            continue

        if now - agent.get("last_swing", 0.0) < interval:
            continue
        agent["last_swing"] = now
        # Turn first, then swing. An agent that lands a hit with its back to you
        # is the one thing here a person would call broken without being told.
        #
        # NOT forced, and the first version was: force bypasses the epsilon, so a
        # stationary fight re-sent the SAME angle once per swing -- 15 of the 16
        # rotations in the first live run were byte-identical to the one before.
        # The epsilon already guarantees the facing is within 8.6 degrees, and in
        # melee this is the ONLY call site (the chase does not run inside reach),
        # so it is also what keeps the facing current when the player walks around
        # the agent. Gating it here is what makes that tracking cost one message
        # instead of one per swing.
        face_player(send, state, agent_id, agent, conn_id)
        start_swing(send, agent_id, conn_id)
        # `interval` is this agent's own declared attack base -- the same number it
        # was told to the client in 0x0035. The windup is a fraction OF THAT, not a
        # constant, so an agent that declares a slower weapon also winds up longer.
        agent["swing_lands_at"] = now + swing_windup(interval)


def face_player(send, state, agent_id, agent, conn_id, force=False):
    """Turn an agent to look at the player, if it is not looking there already.

    Gated on a change rather than sent per tick: at 20 ticks a second an ungated
    version is 20 rotation messages a second for an agent that is already facing
    the right way. `force` is for the moment a swing opens, where being turned the
    wrong way is the whole thing anyone would notice.
    """
    px, py = state.get("pos", (0.0, 0.0))
    ax, ay = agent["pos"]
    dx, dy = px - ax, py - ay
    if not dx and not dy:
        # Standing exactly on the player has no direction. atan2(0, 0) is 0.0
        # rather than an error, so this would silently mean "face east".
        return
    # PLUS PI, AND THE PLUS PI IS MEASURED RATHER THAN DERIVED. atan2(dy, dx) is
    # the angle FROM the agent TO the player, and it is the right angle by every
    # derivation available: test_rotate.py scores the client's own 0x0040 sends
    # against atan2 of a 0x003D DIRECTION vector and beats a null model. Sending
    # it turned the agent to face AWAY -- OBSERVED 2026-08-11 by the owner watching
    # the screen, which is the only instrument that can see this. CONFIRMED the
    # same day, same way: with the offset applied the agent faces the player.
    #
    # So the client's 0x002E facing is NOT the same convention as the heading it
    # reports in 0x003D, and WHY is not established: it could be the zero
    # direction, the sign, or the model's own forward axis. What is established is
    # the offset, from the one observation that could refute it. A derivation that
    # produced a correct-looking number and a backwards agent is exactly the trap
    # this arc keeps hitting -- the disassembly tells you what the client TESTS,
    # never what the answer looks like on screen.
    angle = math.atan2(dy, dx) + math.pi
    if angle > math.pi:
        angle -= 2.0 * math.pi          # back into the [-pi, pi] the client uses
    told = agent.get("facing_told")
    if not force and told is not None:
        # Shortest way round: a turn from +3.1 to -3.1 is 0.08 radians, not 6.2,
        # and without the wrap an agent near due west re-announces every tick.
        delta = (angle - told + math.pi) % (2.0 * math.pi) - math.pi
        if abs(delta) < ENEMY_FACING_EPSILON:
            return
    agent["facing_told"] = angle
    send(GAME_SMSG_AGENT_UPDATE_ROTATION,
         [agent_id, _f32(angle), _f32(ENEMY_TURN_RATE)],
         f"agent {agent_id} faces {math.degrees(angle):.0f} deg "
         f"at {ENEMY_TURN_RATE:.3f} rad/s")


def enemy_move_tick(send, state, conn_id):
    """Hostile agents walk toward the player until they are close enough to swing.

    TWO CLOCKS HAVE TO AGREE. The client is told a DESTINATION and animates its own
    way there; the server advances `agent["pos"]` itself at the same rate, because
    that is what every range check in here reads. If they drift, the agent swings
    from where the server thinks it is while the player watches it swing from
    somewhere else -- so the step below is deliberately the same arithmetic the
    player's own movement uses, and the destination is re-announced whenever the
    player has moved far enough for the client's version to be wrong.

    THERE IS NO PATHFINDING. `pathmap.route` is an A* and it is NOT wired in here:
    this walks a straight line and uses `pathmap.clip` to stop at the first thing
    it cannot cross, so an agent meets a wall and waits rather than sliding through
    it. That is honest but it is not clever -- a hostile on the far side of a
    building will stand against the wall for as long as you stay there.
    """
    player_pools(state)
    px, py = state.get("pos", (0.0, 0.0))
    now = time.time()
    pm = state.get("pathmap")
    for agent_id, agent in list(state.get("agents", {}).items()):
        if agent_id not in state.get("agents", {}):
            continue
        if agent["dead"] or not agent.get("attacks_back"):
            agent["moving"] = False
            continue
        if agent.get("allegiance") != agents.ALLEGIANCE_HOSTILE:
            continue
        if agent.get("effects", 0) & agents.EFFECT_TRANSITION:
            continue
        ax, ay = agent["pos"]
        dist = math.hypot(px - ax, py - ay)
        chasing = (not state["player_dead"]
                   and ENEMY_MELEE_RANGE < dist <= AGGRO_RANGE)
        if not chasing:
            if agent.get("moving"):
                # STOPPING IS AN ARRIVAL, not a zero rate. agent_update_speed
                # refuses anything under AGENT_MIN_MOVE_SPEED (0.01, the client's
                # own assert at AgAgent.cpp:2366), so "speed 0" is not available
                # to say this with -- and on the world tick that refusal would be
                # a ValueError the tick has to swallow.
                agent["moving"] = False
                agent["dest_told"] = None
                send(GAME_SMSG_AGENT_MOVE_TO_POINT,
                     [agent_id, [ax, ay], agent.get("plane", 0),
                      agent.get("plane", 0)],
                     f"agent {agent_id} stops at ({ax:.0f},{ay:.0f})")
            agent["moved_at"] = now
            continue

        if not agent.get("moving"):
            agent["moving"] = True
            agent["moved_at"] = now
            send(GAME_SMSG_AGENT_UPDATE_SPEED,
                 agents.agent_update_speed(agent_id, ENEMY_MOVE_RATE),
                 f"agent {agent_id} speed {ENEMY_MOVE_RATE} "
                 f"({ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED:.0f} u/s)")
            print(f"[c{conn_id}] agent {agent_id} ({agent['name']}) is coming for "
                  f"the player, {dist:.0f} units out", flush=True)
            face_player(send, state, agent_id, agent, conn_id)

        told = agent.get("dest_told")
        if told is None or math.hypot(px - told[0], py - told[1]) > ENEMY_DEST_RESEND:
            agent["dest_told"] = (px, py)
            send(GAME_SMSG_AGENT_MOVE_TO_POINT,
                 [agent_id, [px, py], agent.get("plane", 0), agent.get("plane", 0)],
                 f"agent {agent_id} walks to ({px:.0f},{py:.0f})")

        # EVERY CHASING TICK, not only when the destination is re-announced. This
        # was nested under the re-announce, which meant the facing could not change
        # until the player had moved ENEMY_DEST_RESEND (120) units -- so the 0.15
        # rad epsilon inside face_player was decorative, and an agent tracking a
        # player who circles it at a constant distance never turned at all. It also
        # made the seam-wrap untestable, because the branch was unreachable.
        # face_player has its own gate; this is where it is supposed to do the work.
        face_player(send, state, agent_id, agent, conn_id)

        # Advance our own copy. Cap the step at the distance that still leaves the
        # agent at its melee range, so it stops beside the player rather than
        # walking through them.
        elapsed = max(0.0, now - agent.get("moved_at", now))
        agent["moved_at"] = now
        step = min(ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED * elapsed,
                   dist - ENEMY_MELEE_RANGE)
        if step <= 0.0:
            continue
        nx = ax + (px - ax) / dist * step
        ny = ay + (py - ay) / dist * step
        if pm is not None:
            # Sampling, not solving -- clip returns the last walkable point along
            # the way, so a wall stops the agent instead of being walked through.
            nx, ny = pm.clip(ax, ay, nx, ny)
        agent["pos"] = (nx, ny)


def start_swing(send, agent_id, conn_id):
    """The opening half of an agent's swing: the animation, and nothing else.

    SLOT 1 IS THE AGENT SWINGING. hit_enemy's comment records how that was found
    -- an early version put the enemy there by mistake, the client animated the
    enemy and then asserted on m_attackInterval -- and ArenaNet's own traffic now
    confirms it independently and far more strongly: across the whole live corpus
    the set of agents that ever receive an attack-speed declaration is EXACTLY the
    set that ever appears in slot 1 of ATTACK_STARTED, 11 to 0 against the rival
    reading (studies/enemy/PLAN.md 11.1).
    """
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
         [agents.GV_ATTACK_STARTED, agent_id, PLAYER_AGENT_ID, 0],
         f"attack_started: agent {agent_id} swings at the player")


def land_swing(send, state, agent_id, agent, conn_id):
    """The closing half: the swing connects, `swing_windup(interval)` seconds later.

    THE ORDER IS ARENANET'S, and it is the opposite of hit_enemy's. OBSERVED in
    the Lakeside tape: the landing is GV_MELEE_ATTACK_FINISHED and then the
    damage, adjacent in the same TCP payload, 6 of 6 swings, checked by byte
    offset rather than by timestamp. hit_enemy sends damage first and is
    deliberately NOT changed here -- the corresponding claim about how ArenaNet
    marks the CONTROLLED agent's own landings was refuted under review, so the
    player's swing has no verified model to copy and guessing at one would be
    trading a known shape for an unverified one.
    """
    # Its own lazy init rather than the caller's: this runs on the world-tick
    # daemon thread and a KeyError here would stop the world for the rest of the
    # session with a traceback nowhere near the cause.
    player_pools(state)
    # Guard before effect: validate the fraction before the FIRST send, so a
    # refusal leaves no half-swing on the wire (test_guards section 3). The
    # WIRE ORDER below is untouched -- finished then damage is ArenaNet's own,
    # 6 of 6 swings in the Lakeside tape (docstring above); only the
    # validation moved up.
    frac = _fraction(-ENEMY_HIT_FRACTION, agents.PROP_DAMAGE, "an enemy swing")
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
         [agents.GV_MELEE_ATTACK_FINISHED, agent_id, 0],
         "melee_attack_finished")

    dealt = float(agents.PLAYER_HEALTH) * ENEMY_HIT_FRACTION
    state["player_health"] = max(0.0, state["player_health"] - dealt)
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
         [agents.PROP_DAMAGE, PLAYER_AGENT_ID, agent_id, frac],
         f"damage {dealt:.0f} to the player")
    print(f"[c{conn_id}] player hit by {agent_id}: "
          f"{state['player_health']:.0f}/{agents.PLAYER_HEALTH}", flush=True)

    if state["player_health"] <= 0.0:
        # PROPERTY 16 CANNOT DO THIS PART. It floors at 1 and cannot kill
        # (agents.PROP_DAMAGE), which is a fact about the client rather than a
        # choice of ours -- so damage drives the bar down to a sliver and the last
        # step has to be the effects bit, exactly as it is for an agent. Our own
        # bookkeeping decides; the fractions only make the bar agree with it.
        state["player_dead"], state["player_died_at"] = True, time.time()
        state["attacking"] = None      # a corpse stops swinging back
        send(GAME_SMSG_AGENT_UPDATE_STATUS,
             [PLAYER_AGENT_ID, agents.EFFECT_DEAD], "KILL the player")
        print(f"[c{conn_id}] THE PLAYER IS DEAD -- back up in "
              f"{PLAYER_REVIVE_AFTER:.0f}s", flush=True)


def pick_skill(agent, now):
    """The next ready slot on the bar, round robin from the last one cast.

    THIS IS A TESTING FUNCTION, NOT A DECISION ABOUT AI. Owner's ruling
    2026-08-11: casting AI is not settled here and will not be settled by
    whichever policy happens to be in this function. What this exists for is to
    exercise the bar mechanism -- the message, the per-slot recharge, the
    activation window -- so that the parts which ARE evidenced can be tested. When
    the AI study lands, this gets replaced rather than extended, and nothing
    downstream should read the current policy as a claim.

    ROUND ROBIN, and the version before it was FIRST-READY-IN-BAR-ORDER, which
    left slot 4 unreachable. OBSERVED (11.5): a run produced
    {276: 6, 253: 3, 312: 3, 289: 0} -- skill 289 never fired once. That was not a
    selector bug but a property of a strict priority list, because slot 1 recharges
    every 2.0 s and reaching slot 4 needs 2 + 5 + 8 seconds of everything above it
    being busy, which never happens. A four-slot bar was really a three-slot bar.

    Starting the scan AFTER the last slot cast fixes it without any new numbers:
    every ready slot gets a turn before any slot gets a second one. The wrap is
    what makes it a cycle rather than a sweep that stalls at the end.

    STILL NOT MEASURED, and this is the honest part: nothing in this project knows
    how a Guild Wars monster actually chooses. Round robin, least-recently-used
    and priority order are all inventions; this one is the invention that reaches
    every slot, which is the property that was actually wanted.

    `last_slot` is written by the CAST SITE, not here, so this stays a pure read
    and a test can drive the cursor by hand.
    """
    skills = agent.get("skills") or ()
    n = len(skills)
    if not n:
        return None
    start = (agent.get("last_slot", -1) + 1) % n
    for i in range(n):
        slot = (start + i) % n
        if now >= agent["skill_ready"][slot]:
            return slot
    return None


def land_skill(send, state, agent_id, agent, conn_id):
    """An agent's skill connecting, ENEMY_SKILL_ACTIVATION seconds after the cast.

    The damage half is the SAME property-16 channel an ordinary swing uses -- the
    corpus is unambiguous that a skill's damage is not a different mechanism, and
    ArenaNet's own player casts in the Lakeside tape land on property 16 and 55
    like anything else. What is different is the announcement and the size.

    No MELEE_ATTACK_FINISHED here: that value names the end of a SWING, and 40 of
    the 42 in the live corpus are immediately followed by a property-16 damage from
    the same agent. A cast is not a swing.

    SINGLE TARGET, ALWAYS, and this is the flag that was missing. Every skill on
    the bar lands on PLAYER_AGENT_ID and on nothing else -- there is no area of
    effect, no splash, no secondary target, and no line of sight. That is not a
    reading of any evidence; it is the only shape this function has ever had, and
    until 2026-08-11 it was the one simplification in the combat block with no
    comment saying so while every equally-implied neighbour had one. GWW documents
    a whole mechanic keyed to the absent one (scatter: foes run from the epicenter
    of an area damage-OVER-TIME skill, and single-packet AoE does not trigger it) --
    studies/monsterai/FINDINGS.md 4.4. Nothing here can express any of that.
    """
    player_pools(state)
    slot = agent.get("casting")
    skills = agent.get("skills") or ()
    skill_id = skills[slot][0] if slot is not None and slot < len(skills) else 0
    # Tidiness, and NOTHING TODAY CAN OBSERVE IT -- said here rather than left to
    # look load-bearing. `casting` is read only from this function, which runs only
    # when `cast_lands_at` fires, which is only ever set alongside a fresh
    # `casting`. Removing this line breaks no check, and that was verified by
    # removing it. It stays because a stale slot index is a bad thing to leave
    # lying around for the next person who reads `casting` from somewhere else.
    agent["casting"] = None
    dealt = float(agents.PLAYER_HEALTH) * ENEMY_SKILL_FRACTION
    state["player_health"] = max(0.0, state["player_health"] - dealt)
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
         [agents.PROP_DAMAGE, PLAYER_AGENT_ID, agent_id,
          _fraction(-ENEMY_SKILL_FRACTION, agents.PROP_DAMAGE,
                    f"skill {skill_id}")],
         f"skill {skill_id} deals {dealt:.0f} to the player")
    print(f"[c{conn_id}] player hit by skill {skill_id}: "
          f"{state['player_health']:.0f}/{agents.PLAYER_HEALTH}", flush=True)

    if state["player_health"] <= 0.0:
        state["player_dead"], state["player_died_at"] = True, time.time()
        state["attacking"] = None
        send(GAME_SMSG_AGENT_UPDATE_STATUS,
             [PLAYER_AGENT_ID, agents.EFFECT_DEAD], "KILL the player")
        print(f"[c{conn_id}] THE PLAYER IS DEAD -- back up in "
              f"{PLAYER_REVIVE_AFTER:.0f}s", flush=True)


def player_revive_due(send, state, conn_id):
    """Stand the player back up, on the same two operations an agent needs.

    UNVERIFIED, and shipped that way on purpose: no PLAYER death was found in
    either live capture, so this is our agent-death path pointed at
    PLAYER_AGENT_ID rather than a replication of ArenaNet's. What retail does on
    death -- a defeated overlay, a party wipe, a walk back from a resurrection
    shrine -- is not modelled here at all. Getting back up on a timer is the least
    wrong thing that keeps a session usable, and it is a placeholder.
    """
    player_pools(state)
    if not state["player_dead"]:
        return
    if time.time() - state["player_died_at"] < PLAYER_REVIVE_AFTER:
        return
    # NOTHING RESETS THE AGENTS' `facing_told` HERE, and that is deliberate rather
    # than forgotten. The stale value is still the correct one: a dead player
    # cannot move and nothing chases or turns toward a corpse, so the geometry at
    # revive is the geometry at death. OBSERVED 2026-08-11 (owner): the agent still
    # faces the player after a revive. The day a dead player CAN be moved -- a
    # resurrection-shrine walk is exactly that -- this stops being true and the
    # reset has to go in.
    state["player_dead"] = False
    state["player_health"] = float(agents.PLAYER_HEALTH)
    send(GAME_SMSG_AGENT_UPDATE_STATUS, [PLAYER_AGENT_ID, 0], "revive the player")
    # THE EXPERIMENT of studies/agentprops 1f, off by default. The client logs
    # `Health non-zero on resurrect` on every revive we send -- 49 times across the
    # vault -- because at the moment the death bit clears it requires
    # min(f32 @ +0x130, +0x134) == 0.0, and our three messages leave in one burst.
    # Two readings survive the log alone (deferred check vs. a pool never zeroed) and
    # `Gw.log` has no timestamps to separate them, so this defers the two refills by
    # `REVIVE_REFILL_DEFER` seconds and the complaint's presence is the answer.
    # A SWITCH rather than a reorder: the fix is only known once the two runs differ,
    # and 1f says in as many words not to reorder on the strength of the reading.
    if REVIVE_REFILL_DEFER > 0.0:
        state["player_refill_due_at"] = time.time() + REVIVE_REFILL_DEFER
        print(f"[c{conn_id}] the player is back up "
              f"(refill deferred {REVIVE_REFILL_DEFER:.2f}s)", flush=True)
        return
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
         [agents.PROP_HEALTH_MAX, PLAYER_AGENT_ID, agents.PLAYER_HEALTH],
         "restore the player's maximum")
    # Property 34 SETS the pool to fraction x maximum (studies/agentprops 1e), so
    # 1.0 is a full bar and not a doubled one. The client's own death path zeroes
    # the pools, so clearing the bit alone returns a body at nothing.
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
         [agents.GV_HEALTH, PLAYER_AGENT_ID, PLAYER_AGENT_ID,
          _fraction(1.0, agents.GV_HEALTH, "refill the player to a full pool")],
         "refill the player's bar")
    print(f"[c{conn_id}] the player is back up", flush=True)


def agent_refill_due(send, state, conn_id):
    """The deferred half of the AGENT revive -- see revive_due and player_refill_due."""
    now = time.time()
    for agent_id, agent in list(state.get("agents", {}).items()):
        if agent_id not in state.get("agents", {}):
            continue
        due = agent.get("refill_due_at")
        if not due or now < due:
            continue
        agent["refill_due_at"] = None
        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
             [agents.PROP_HEALTH_MAX, agent_id, int(agent["max_health"])],
             f"restore max health on agent {agent_id} (deferred)")
        send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
             [agents.GV_HEALTH, agent_id, agent_id,
              _fraction(1.0, agents.GV_HEALTH, f"refill agent {agent_id}")],
             f"refill agent {agent_id}'s bar (deferred)")


def player_refill_due(send, state, conn_id):
    """The deferred half of 1f's experiment: the two pool refills, a tick later.

    Only ever armed when REVIVE_REFILL_DEFER > 0, so the shipped path is byte-for-byte
    what it was and a run with the switch off is a real control rather than a rebuild
    of the same code.
    """
    due = state.get("player_refill_due_at")
    if not due or time.time() < due:
        return
    state["player_refill_due_at"] = None
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
         [agents.PROP_HEALTH_MAX, PLAYER_AGENT_ID, agents.PLAYER_HEALTH],
         "restore the player's maximum (deferred)")
    send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
         [agents.GV_HEALTH, PLAYER_AGENT_ID, PLAYER_AGENT_ID,
          _fraction(1.0, agents.GV_HEALTH, "refill the player to a full pool")],
         "refill the player's bar (deferred)")
    print(f"[c{conn_id}] deferred refill sent", flush=True)


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

    `send_definition` is SETTLED as of 2026-08-11, and by our own client rather than by
    inference. ArenaNet sends the NPC definition (0x0056) exactly ONCE for 140 re-creates
    of the same worm; that told us THEIR client keeps it, and ours had never been asked,
    because the D1 probe re-sent the definition every time and so its success said
    nothing. The `burrow` probe asked: after a WORLD_REMOVE_AGENT, it re-created at the
    SAME id and then at a FRESH id, both with NO 0x0056/0x0057, and BOTH drew a correct
    collector (studies/enemy/PLAN.md 10.8, capture authsrv-20260811T135809). A definition
    is per-INSTANCE and outlives the agents using it.

    This still defaults to TRUE and should: the first create of an agent must declare it.
    What the probe unlocked is the RE-create -- `burrow_tick` no longer resends.
    `agents.npc_properties` warns that an agent whose definition was never sent takes the
    client down on `index < m_count`, and that asymmetry has not changed: declare once
    per instance, then re-create freely, and never skip the first one.
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
# independent Lakeside visits, 140 worm re-creations across 13 worm ids, one burst
# shape and no exceptions. (This read 151 until 2026-08-11. The instrument that
# produces the number is test_burrow.py section 2 and it says 140; three files
# carried three different counts, which is what a number nothing re-derives does.)
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
        # NO DEFINITION RESEND, measured 2026-08-11 (10.8). The `burrow` probe removed
        # our Hatcher and re-created it twice with no 0x0056/0x0057 -- once at the same
        # id, once at a fresh one -- and both drew a correct collector. So a definition
        # is per-INSTANCE, the declaration at map load covers every later create, and
        # this matches what ArenaNet does: 1 declaration to 140 worm creates.
        #
        # The escape hatch: `resend_definition = true` under [spawn.test_enemy] in
        # content/world.toml restores the old behaviour. It is carried into `entry` by
        # spawn_enemy via ENEMY_RESEND_DEFINITION -- without that line the key would
        # load silently, never reach `entry`, and this .get would stay False while the
        # operator believed otherwise. The hatch exists because the failure mode is
        # asymmetric: resending costs 2 messages, and being wrong the other way is a
        # client assert on Array.h's `index < m_count`, with no log line either side.
        create_agent_world(send, state, agent_id, entry, "emerging from burrow",
                           conn_id=conn_id,
                           send_definition=entry.get("resend_definition", False))


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


# ------------------------------------------------------- the area population

# Set by --area. None means the legacy world: one global test enemy placed by
# offset, exactly as before, which is what every probe and every earlier rung
# expects.
AREA_NAME = None

# How far from its declared spot a body may be nudged to find ground, and how
# fine the search is. A NUDGE IS REPORTED, NEVER SILENT: an author who wrote a
# coordinate deserves to know it was not usable, and "it appeared 400 units
# from where I put it" is otherwise indistinguishable from a placement bug.
PLACE_SEARCH_RADIUS = 480.0
PLACE_SEARCH_STEP = 48.0


class PopulationError(Exception):
    """An area's declared population cannot be placed as written."""


def area_population(area):
    """The spawn rows bound to one area, checked AS A SET rather than one by one.

    The set checks are the point. An agent id reused for a second body leaves
    the client holding one agent's state under another's name and nothing on the
    wire says so -- `create_agent_world` already refuses that at spawn time, but
    by then half the population is in the world and the run is wasted. A
    definition index collision is worse and quieter: definitions are a raw array
    on the client, so two rows sharing one index means the second body silently
    wears the first's model.

    Rows with no `area` are the legacy global spawn and are never returned here.
    """
    rows = []
    for key, row in sorted(agents.WORLD.rows("spawn").items()):
        if row.get("area") != area:
            continue
        if not row.get("enabled", True):
            continue
        rows.append((key, row))

    for field in ("agent_id", "definition"):
        for key, row in rows:
            if row.get(field) is None:
                raise PopulationError(
                    f"spawn row {key!r} in area {area!r} has no {field}. Ids are "
                    f"allocator choices and this server does not invent them -- "
                    f"write one, or the client gets a body it was never told about")

    seen = {}
    for key, row in rows:
        v = row["agent_id"]
        if v in seen:
            raise PopulationError(
                f"spawn rows {seen[v]!r} and {key!r} in area {area!r} share "
                f"agent_id {v}. Two bodies under one id leaves the client "
                f"holding one agent's state under another's name, and nothing "
                f"on the wire would say so")
        seen[v] = key

    # DEFINITIONS MAY BE SHARED -- but only by rows naming the SAME npc. A
    # definition is per-instance and outlives the agents using it (measured:
    # ArenaNet sends one 0x0056 for 140 re-creates of the same worm), so ten
    # identical hatchers legitimately share an index and demanding ten would be
    # inventing a rule retail does not follow. Two DIFFERENT templates sharing
    # one index is the real fault: the definition array is raw, so the second
    # row silently overwrites the first and a body wears the wrong model.
    seen = {}
    for key, row in rows:
        v, npc = row["definition"], row["npc"]
        if v in seen and seen[v][1] != npc:
            raise PopulationError(
                f"spawn rows {seen[v][0]!r} ({seen[v][1]}) and {key!r} ({npc}) "
                f"in area {area!r} share definition {v} while naming DIFFERENT "
                f"npc templates. The definition array is a raw index on the "
                f"client, so one would silently wear the other's model")
        seen[v] = (key, npc)
    return rows


def place_on_mesh(pm, x, y, what):
    """The nearest spot the navmesh calls ground, or None, and how far it moved.

    Returns `(x, y, moved)`. This exists because of rung (I): until 2026-08-13
    the server on an authored map held either ArenaNet's geometry for the same
    map id or no mesh at all, so a placement check here would have been
    measuring the wrong map or nothing. With the mesh actually loaded, an
    authored area can be sparse -- the sculpt map is 1.2% walkable by area --
    and a coordinate an author picked off a Blender screenshot very often is
    not standable.

    None means REFUSE. A body placed off-mesh stands somewhere the server's own
    collision says does not exist, and everything downstream reasons about it
    wrongly; a missing NPC is a smaller lie than a present one nobody can reach.
    """
    if pm is None:
        return x, y, 0.0                       # no mesh: nothing to check against
    if pm.walkable(x, y):
        return x, y, 0.0
    step = PLACE_SEARCH_STEP
    r = step
    while r <= PLACE_SEARCH_RADIUS:
        n = max(8, int(2 * math.pi * r / step))
        for i in range(n):
            a = 2.0 * math.pi * i / n
            cx, cy = x + r * math.cos(a), y + r * math.sin(a)
            if pm.walkable(cx, cy):
                return cx, cy, r
        r += step
    return None


def spawn_population(send, state, origin, conn_id, area=None):
    """Everything that lives in an authored area, from `content/world.toml`.

    R5's criterion is "a new zone in TOML, hot-reloaded, walked", and until now
    the toolkit could author the GROUND of a zone and nothing that stands on it.
    An area with a tree in it and nothing alive is a diorama.

    Nothing here is new protocol: each body goes out through `create_agent_world`,
    the same call `spawn_enemy` has used since the enemy rung, so every message
    is one already proven against our own client. What is new is that the set of
    bodies, their positions, their allegiances and their health come from content
    rows rather than from module constants.
    """
    area = area or AREA_NAME
    ox, oy, plane = origin
    rows = area_population(area)
    if not rows:
        print(f"[c{conn_id}] area {area!r}: no population rows; the world is "
              f"the player and the geometry", flush=True)
        return 0

    pm = state.get("pathmap")
    if pm is None:
        print(f"[c{conn_id}] area {area!r}: NO NAVMESH, so no placement can be "
              f"checked -- every body below is placed on trust", flush=True)

    placed = 0
    for key, row in rows:
        # npc_template, NOT WORLD.get: the raw row carries `enc_name` as a
        # list of string ids and the codec refuses the message built from it.
        npc = agents.npc_template(row["npc"])
        # Absolute if the row says so, else the legacy offset-from-the-player.
        if row.get("x") is not None and row.get("y") is not None:
            wx, wy = float(row["x"]), float(row["y"])
            how = "absolute"
        else:
            wx, wy = ox + float(row.get("offset_x", 0.0)), \
                     oy + float(row.get("offset_y", 0.0))
            how = "offset from the player"

        spot = place_on_mesh(pm, wx, wy, key)
        if spot is None:
            print(f"[c{conn_id}] REFUSED {key!r}: ({wx:.0f}, {wy:.0f}) is not on "
                  f"the navmesh and nothing within {PLACE_SEARCH_RADIUS:.0f} "
                  f"units is either. Not placing a body the server's own "
                  f"collision says is nowhere.", flush=True)
            continue
        x, y, moved = spot

        allegiance = ALLEGIANCE_BY_NAME[row.get("allegiance", "hostile")]
        hp = float(row.get("max_health", ENEMY_MAX_HEALTH))
        entry = {
            "pos": (x, y), "plane": plane,
            "health": hp, "max_health": hp,
            "dead": False,
            "name": npc["name"],
            "npc": npc,
            "definition": int(row["definition"]),
            "allegiance": allegiance,
            "attack_speed": ENEMY_ATTACK_SPEED,
            "effects": 0,
            "resend_definition": bool(row.get("resend_definition", False)),
            "attacks_back": bool(row.get("attacks_back", False)),
            "skills": ENEMY_SKILLS,
            "skill_ready": [0.0] * len(ENEMY_SKILLS),
        }
        create_agent_world(send, state, int(row["agent_id"]), entry, key,
                           conn_id=conn_id)
        placed += 1
        note = (f" (MOVED {moved:.0f} units to reach ground)" if moved else "")
        print(f"[c{conn_id}] {key!r}: {npc['name']} at ({x:.0f}, {y:.0f}) "
              f"{how}, {row.get('allegiance', 'hostile')}, {hp:.0f} hp{note}",
              flush=True)
    print(f"[c{conn_id}] area {area!r}: {placed} of {len(rows)} placed",
          flush=True)
    return placed


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
        "resend_definition": ENEMY_RESEND_DEFINITION,
        "attacks_back": ENEMY_ATTACKS_BACK,
        "skills": ENEMY_SKILLS,
        # Per-SLOT rather than per-id: a bar may legitimately carry the same skill
        # twice, and keying recharge by id would make the second copy share the
        # first's cooldown.
        "skill_ready": [0.0] * len(ENEMY_SKILLS),
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
        # Frame the tape ONCE, then group each message under the event its FIRST byte
        # falls in. This used to decode each event on its own, which is wrong in the one
        # place a wrong answer costs the most: a tape event is a TCP segment, a message
        # can straddle two, and the event after a straddle begins mid-message -- so its
        # leading bytes framed as whatever opcode they happened to spell. This readout
        # exists to name the bytes that killed the client, and naming an opcode the wire
        # never carried is worse than naming none. Corpus-wide the old idiom lost 19% of
        # messages and invented 117; `tape.decode_all` carries the measurement.
        ends, at = [], 0
        for _t, b in events:
            at += len(b)
            ends.append(at)
        per_event, framed_to = {}, 0
        try:
            framed, framed_to, _e = codec.decode_stream_at(
                "GAME_SMSG", b"".join(b for _t, b in events))
        except Exception:
            framed = []
        for off, op, _v in framed:
            per_event.setdefault(bisect.bisect_right(ends, off), []).append(op)

        for j in range(lo, min(sent + 2, len(events))):
            et, eb = events[j]
            here = per_event.get(j, [])
            ops = " ".join(f"0x{op:04x}" for op in here[:10])
            more = "..." if len(here) > 10 else ""
            if not here:
                # An event with no message of its own has two possible causes and they
                # are not the same news, so do not print one label for both. Either it
                # holds only the tail of a message that began earlier, or the stream
                # stopped framing before reaching it -- and the second is a finding.
                # MEASURED 2026-08-11: the first case happens in NONE of the ten
                # recorded tapes, because it needs a message longer than a whole
                # segment and these do not have one. The branch is for a tape whose
                # segmentation is not ArenaNet's, not for the ordinary case.
                ops = eb[:12].hex(" ")
                more = (" (continues the previous event)"
                        if ends[j] <= framed_to else
                        f" (UNFRAMED -- the tape stopped framing at byte {framed_to:,})")
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

    A step that declares `sends=False` is a REFUSAL and is not sent. That flag was
    added for `probes.check_encodable` on 2026-08-13 and this loop -- the one that
    puts bytes on a socket -- was not taught about it for the rest of the day, which
    fails in BOTH directions. When the codec raises (the empty smsgsweep plan's
    refusal is `0x0000` with no values, and 0x0000 wants one) the swallow above
    prints `SEND FAILED ... that is a result too -- record it`, filing "there was no
    plan" as an experimental result and `continue`ing PAST the `watch` line that
    says what actually happened -- so the one message the step exists to carry is
    the one thing the operator does not see. And when the codec does NOT raise -- a
    refusal built on any opcode whose fields the degenerate encoder can fill -- the
    packet goes on the wire underneath the words "nothing was sent". The second is
    worse: it is a lie printed beside the bytes that contradict it.

    Returns the Thread so a caller can join it. The live call site does not; the
    suite does, because the alternative is a test that sleeps and hopes.
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
            if not getattr(step, "sends", True):
                # Declared refusal -- see this function's docstring. It is a DECLARED
                # flag and never `if not step.values`, because a malformed step with
                # no values is exactly what the encoder check exists to catch and the
                # two are indistinguishable by shape (probes.Step's docstring).
                #
                # Without this arm the refusal reached `send(0x0000, [])`, which raises
                # and lands in the handler below as "SEND FAILED" -- the correct outcome
                # (nothing went on the wire) reported as a malfunction, with the one
                # sentence the operator needed buried under a traceback name. The
                # alternative considered and rejected was returning NO steps, which the
                # runner already prints as "observation only": silent in the wrong
                # direction, since a probe that measures nothing because its plan ran
                # out would then look identical to one designed to send nothing.
                #
                # (Two sessions fixed this independently on 2026-08-13 and reached the
                # same arm. This comment is the union of both; the print text is the
                # one `test_agentlife` asserts on.)
                print(f"      REFUSAL -- no packet sent. {step.watch}", flush=True)
                continue
            try:
                send(step.opcode, step.values, f"PROBE[{name}] {step.label}")
            except Exception as exc:
                print(f"      SEND FAILED: {type(exc).__name__}: {exc}",
                      flush=True)
                print(f"      (that is a result too -- record it)", flush=True)
                continue
            print(f"      WATCH: {step.watch}", flush=True)
        print(f"\n  probe complete. What did you see?\n{bar}\n", flush=True)

    thread = threading.Thread(target=body, daemon=True)
    thread.start()
    return thread


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
         [req_id, TEST_CHAR_UUID, 0, TEST_CHAR_NAME,
          char_settings_for(SPAWN_PROFESSION)],
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


def note_unhandled(state, conn_id, channel, opcode, name, rec=None):
    """Record a c2s opcode the schema KNOWS and this server has no arm for.

    studies/divergence D9(a). Both dispatch chains used to end without an
    `else`, so a schema-known opcode with no handler was printed as received
    and then fell off the end of the chain: nothing sent, NOTHING LOGGED AS A
    MISS, socket healthy. Measured over our own corpus that is 19 distinct
    GAME_CMSG opcodes and 1,126 of 11,502 game-channel messages -- 9.8% --
    and against live-shaped traffic it is worse, since `0x8009` alone is 19.3%
    of live game c2s. The cost of the silence is not the missing feature; it
    is that the missing feature is INVISIBLE, so "the client did nothing" and
    "we ignored what the client did" look identical in the log.

    Deliberately NOT an error and NOT a disconnect. Unhandled-but-known is the
    normal state of most of the catalog today -- 194 layouts against nine
    handlers -- so treating it as a fault would make every session look broken
    and train the operator to ignore the loudest thing in the log. D9(b) is the
    one that ends connections, and it is a different case: an opcode the schema
    does not contain at all cannot be framed past safely.

    First occurrence per connection prints; the rest are counted and reported
    once at disconnect. That split is the point -- printing every one buries
    the log (0x8009 arrives every 5 s, and movement opcodes far faster than
    that), while printing none is the defect being fixed. A labelled run
    suppresses the echo for the same reason the decoded line does: the operator
    is reading a countdown in that terminal.
    """
    seen = state.setdefault("unhandled", {})
    key = (channel, opcode)
    first = key not in seen
    seen[key] = seen.get(key, 0) + 1
    if first:
        if not labelrun.ACTIVE:
            print(f"[c{conn_id}] UNHANDLED {channel} "
                  f"0x{opcode | AUTH_CMSG_MASK:04x} {name} -- schema knows it, "
                  f"this server has no arm for it (D9(a); first occurrence, "
                  f"further ones counted)", flush=True)
        if rec is not None:
            rec.event("unhandled", channel=channel, opcode=opcode, name=name)


def report_unhandled(state, conn_id, rec=None):
    """Print the D9(a) tally once, at disconnect. Silent when there is none."""
    seen = state.get("unhandled") or {}
    if not seen:
        return
    total = sum(seen.values())
    parts = ", ".join(
        f"0x{op | AUTH_CMSG_MASK:04x}x{n}"
        for (_ch, op), n in sorted(seen.items(), key=lambda kv: -kv[1]))
    print(f"[c{conn_id}] unhandled-but-known c2s this session: {total} messages "
          f"over {len(seen)} opcodes -- {parts}", flush=True)
    if rec is not None:
        rec.event("unhandled_summary", total=total, opcodes=len(seen),
                  counts={f"{ch}:0x{op:04x}": n for (ch, op), n in seen.items()})


def report_ping(state, conn_id, rec=None):
    """Say how the round trip went, once, at disconnect. Silent if never used.

    `ping_missed` counts requests that were still outstanding when the next one
    fell due. Counting it and never printing it would be the D9(a) defect in
    miniature -- a number the server knows and the operator cannot see.
    """
    if state.get("ping_at") is None:
        return
    missed = state.get("ping_missed", 0)
    last = state.get("ping_last_ms")
    print(f"[c{conn_id}] net graph: last round trip "
          f"{'--' if last is None else str(last) + ' ms'}"
          f"{f', {missed} request(s) went unanswered' if missed else ''}",
          flush=True)
    if rec is not None:
        rec.event("ping_summary", last_ms=last, missed=missed)


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
    # Bound BEFORE the try so the end-of-connection summaries in `finally` can
    # always read it. It is re-bound below once the handshake completes; this
    # binding exists only so a connection that dies during the handshake does
    # not turn the summary into a NameError inside a finally block.
    state = {}
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
                        # Above the fight, because the net graph should keep
                        # moving whether or not anything is swinging -- and
                        # because a 5 s timer that only runs during combat
                        # would look like a working ping loop in exactly the
                        # sessions nobody is testing it in.
                        ping_tick(send, state, conn_id)
                        attack_tick(send, state, conn_id)
                        revive_due(send, state, conn_id)
                        agent_refill_due(send, state, conn_id)
                        # Both halves of the fight, and the order matters. The
                        # player's revive runs BEFORE the enemies swing, so a
                        # player whose timer expired this tick stands up and can
                        # be hit again in the same tick rather than getting one
                        # free interval; and enemy_attack_tick reads
                        # state["player_dead"], which player_revive_due is the
                        # only thing that clears.
                        player_revive_due(send, state, conn_id)
                        player_refill_due(send, state, conn_id)
                        # Walk BEFORE swinging, so an agent that arrives on this
                        # tick can open its swing on the same tick rather than
                        # standing in reach for one interval doing nothing.
                        enemy_move_tick(send, state, conn_id)
                        enemy_attack_tick(send, state, conn_id)
                        # The third sweep, and the first that mutates state["agents"]
                        # on a schedule rather than only when the player acts. Last,
                        # so a body that died this tick is seen dead by burrow_tick
                        # and stays put -- a dead agent does not burrow.
                        burrow_tick(send, state, conn_id)
                    except OSError:
                        return
                    except ValueError as ex:
                        # _fraction raises ValueError, and so does every
                        # validator in agents.py. The tick caught OSError and
                        # AgentLifetimeError only, so a single out-of-range
                        # fraction would stop the world for the rest of the
                        # session -- silently, on a daemon thread, with the
                        # traceback nowhere near the cause. Loud, and survivable,
                        # exactly as the case below.
                        print(f"[c{conn_id}] world tick REFUSED a value: {ex}",
                              flush=True)
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
                    elif (opcode in (GAME_CMSG_USE_SKILL,
                                     GAME_CMSG_ATTACK_SKILL)
                          and not state.get("player_dead")):
                        # THE SAME GUARD attack_tick got, and it was missed here.
                        # A dead player pressing a skill still damaged the thing
                        # that killed them -- the corpse could cast. Found by
                        # review rather than by the run, because a person watching
                        # the screen sees a body on the ground either way.
                        # ONE ARM FOR BOTH, deliberately. 0x0046 and 0x0027 are the
                        # caster and attack-skill halves of the same action: their
                        # payloads line up slot for slot and ArenaNet's own server
                        # answers both with GAME_SMSG 0x00E3 (see the constants).
                        # Two arms would drift, and until 2026-08-11 this server
                        # had only the caster half -- so every physical attack
                        # skill fell through to the silent-ignore path and got
                        # nothing back.
                        #
                        # That WAS written up as a correctness bug, citing
                        # studies/divergence D9(b)'s buffer discard. Wrong, and
                        # corrected 2026-08-11: 0x0027 is schema-KNOWN
                        # (GAME_CMSG_0039 in schema/messages.json), and landing on
                        # the silent-ignore path is what schema-known MEANS -- that
                        # is D9(a), which ignores and leaves the buffer alone.
                        # D9(b) covers opcodes the schema does not contain, and it
                        # no longer discards anything either. So this was a missing
                        # feature, which is reason enough to fix it.
                        #
                        # The body lives in handle_skill_press so the
                        # connection-thread combat path has tests that need no
                        # socket. The dead-player guard stays HERE: it gates
                        # whether the press means anything at all, and the arm
                        # condition above is pinned by test_cmsgnames section 6.
                        handle_skill_press(values, send, state, conn_id, opcode)
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
                        #
                        # 0x0033 IS NOW DEAD ON OUR WIRE and is kept anyway --
                        # see its constant for the 0-of-17,770 measurement and
                        # for why deleting it would destroy the evidence.
                        begin_attack(send, state, values[1], conn_id)
                    elif opcode == GAME_CMSG_INTERACT_AGENT:
                        # "I clicked that agent meaning to interact with it" --
                        # arm 2 of the same switch, and 3.2% of ArenaNet's own
                        # live c2s while this server dropped every one.
                        #
                        # DELIBERATELY NOT `begin_attack`. The constant carries
                        # the falsifiable separation this rests on; the short
                        # version is that 0 of 10 distinct 0x0039 targets on
                        # ArenaNet's wire ever enter an auto-attack exchange, so
                        # sharing the arm above would have this server swinging
                        # at NPCs the player is talking to. Recording the target
                        # is all we can honestly do until an NPC-service study
                        # says what an interaction should ANSWER -- and 0x003B
                        # NPC_SERVICE_SELECT, the message that carries what the
                        # player then picked, is still unhandled too.
                        #
                        # Layout is [msg_header, agent_id, byte], 7 bytes. The
                        # trailing byte is 0 in every sample we hold (4 of 4
                        # loopback) and is stored under its POSITION rather than
                        # under a name: nothing has established what it means,
                        # and `interact_kind` would be a reading nobody made.
                        #
                        # NO ARRIVAL COUNTER HERE, and that is deliberate. The
                        # obvious `state["interact_n"] += 1` would be a number
                        # this server knows and never shows anyone, which is what
                        # `report_ping`'s docstring calls D9(a) in miniature. The
                        # recorder already writes a `decoded` event per arrival
                        # with its values, so the count is in the capture; what
                        # belongs in `state` is the CURRENT interaction, not a
                        # statistic about how many there have been.
                        state["interacting"] = values[1]
                        state["interact_byte"] = values[2]
                    elif opcode == GAME_CMSG_TARGET_SELECT:
                        # The client TELLS us the selection; it does not ask.
                        # Measured on ArenaNet's wire: nothing target-shaped
                        # replies within 300 ms over 75 sends. So this arm sends
                        # nothing, and that silence is the correct behaviour
                        # rather than a gap waiting to be filled.
                        #
                        # Field 1 is the EFFECTIVE selection (manual if nonzero,
                        # else auto) and 0 clears it -- so `or None` would be
                        # wrong here in a way that matters: 0 is a real value
                        # meaning "nothing selected", not a missing one.
                        # Field 2 is the auto-selection and is 0 in 363 of 363
                        # of our own samples; it is stored because a corpus that
                        # has never seen a value is not evidence the value
                        # cannot occur.
                        state["target"] = values[1]
                        state["target_auto"] = values[2]
                    elif opcode == GAME_CMSG_ROTATE_PLAYER:
                        # THE DWORD/FLOAT TRAP -- read the constant before
                        # touching this. values[1] and values[2] are integers
                        # here and floats in meaning, and `_f32_of` is the only
                        # correct way to look at them.
                        #
                        # The raw dword is kept alongside because the +/-inf
                        # sentinels are the interesting case and a consumer that
                        # only ever sees `inf` cannot tell a sentinel from a
                        # decode that went wrong. Nothing reads these yet: the
                        # server owns facing (GAME_SMSG 0x002E) and adopting the
                        # client's angle here would be a movement change, which
                        # is a different piece of work with its own study.
                        state["rotate_raw"] = (values[1], values[2])
                        state["rotate_angle"] = _f32_of(values[1])
                        state["rotate_amount"] = _f32_of(values[2])
                    elif opcode == GAME_CMSG_MISSION_MASK_REPORT:
                        # 112 bytes of mission progress, one bit per mission id,
                        # bounded by the client's own MISSION_MASK_BYTES = 112.
                        # Stored whole: the bit MEANING is open (whether a set
                        # bit is "completed" or merely "the server named it") and
                        # a handler that reduced this to a summary would throw
                        # away the only artifact that can settle it.
                        #
                        # 747 of 803 samples are entirely zero because we set no
                        # bits. That is a fact about this server, not about the
                        # message, which is exactly why the non-zero minority is
                        # worth keeping instead of dropping all 803.
                        #
                        # Latest wins, and no arrival counter -- same reasoning
                        # as the INTERACT arm above. The mask is cumulative in
                        # the client, so the newest one supersedes rather than
                        # adds to its predecessor.
                        state["mission_mask"] = values[1]
                    elif opcode == GAME_CMSG_UNNAMED_ACK_0079:
                        # Payload-free, so arrival is the whole content and a
                        # COUNTER is the only thing there is to store. That is the
                        # opposite choice from the INTERACT and MISSION_MASK arms
                        # above, and deliberately: those carry a value that
                        # supersedes its predecessor, this one carries none, so
                        # latest-wins would store the same 0 forever and could not
                        # tell one arrival from a hundred.
                        #
                        # Counting is what makes the loop measurable: 0x0166 and
                        # 0x0167 are the only GAME_SMSG opcodes in 334 ledger rows
                        # that provoke a c2s reply, and "how many came back" is the
                        # question a send-then-count experiment asks.
                        state["ack_0079_count"] = state.get("ack_0079_count", 0) + 1
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
                             [PLAYER_NUMBER, PLAYER_AGENT_ID, appearance_for(SPAWN_PROFESSION),
                              0, 0, 0, TEST_CHAR_NAME], "PLAYER_CREATE")
                        # The party of one. Both write the per-PLAYER array at
                        # ChCliApi ctx+0x80C (stride 0x50) that PLAYER_CREATE
                        # just made, and touch no agent -- so they belong here
                        # rather than after the agent create.
                        #
                        # SIZE THEN LEADER, and the order is the measured part:
                        # 0x00B0 fires no event for a fresh entry while 0x00B1
                        # fires only on a LEADER CHANGE, so leader-first makes
                        # the change a no-op against the default and nothing is
                        # notified.
                        send(GAME_SMSG_PLAYER_PARTY_SIZE,
                             agents.player_party_size(PLAYER_NUMBER, 1),
                             "PLAYER_PARTY_SIZE(1)")
                        send(GAME_SMSG_PLAYER_SET_PARTY,
                             agents.player_set_party(PLAYER_NUMBER, PLAYER_NUMBER),
                             "PLAYER_SET_PARTY(self is leader)")
                        # ...and the party the WINDOW needs, which is a
                        # different structure entirely. RESKIN.md 17: the
                        # window's gate is PyCliGetMyPartyId (0x00856250)
                        # reading the party manager's own vector, not the
                        # per-player array above -- so P was discarded by the
                        # key router before its arm ever ran. Retail's own
                        # four-message sequence, in retail's own position,
                        # 8 of 8 live connections.
                        for op, vals, label in agents.party_build(
                                1, PLAYER_NUMBER):
                            send(op, vals, label)
                        # ...and the player-record flag word, in retail's own
                        # position: BEFORE the agent create, 423 sends over 12 of
                        # 12 live connections, all inside the instance load. OFF by
                        # default because it is being measured -- the control arm is
                        # this server's behaviour up to now, so a default-on flag
                        # would leave nothing to diff against. RESKIN.md 18.8 sent
                        # it LATE and measured a clean null; the open question this
                        # answers is whether bits read once at BUILD time differ.
                        if PLAYER_FLAGS is not None:
                            send(GAME_SMSG_PLAYER_FLAGS,
                                 agents.player_flags(PLAYER_NUMBER, PLAYER_FLAGS),
                                 f"PLAYER_FLAGS(value {PLAYER_FLAGS}, mask 7)")
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
                             spawn_profession_values(),
                             f"PLAYER_UPDATE_PROFESSION(prof {SPAWN_PROFESSION})")
                        # ...and the AGENT-side pair, which we had never sent
                        # for the player's own agent -- only for NPCs.
                        #
                        # 0x00B7 writes the per-PLAYER record the Skills panel
                        # displays from; 0x00A6's setter 0x007F7330 is the SOLE
                        # write path to the AGENT's own profession bytes at
                        # +0x10E/+0x10F (one caller, reached only from this
                        # opcode). The party/roster label builder reads the
                        # agent, not the player record, so without this the
                        # profession ABBREVIATION has nothing to draw from --
                        # which is why it has never appeared in any session.
                        # studies/profession/RESKIN.md s14.
                        send(GAME_SMSG_AGENT_SET_PROFESSION,
                             agents.agent_set_profession(
                                 PLAYER_AGENT_ID, SPAWN_PROFESSION, 0,
                                 custom=SPAWN_PROFESSION
                                 > agents.CHAR_PROFESSIONS - 1),
                             f"AGENT_SET_PROFESSION(player, {SPAWN_PROFESSION})")
                        # STRICTLY AFTER the 0x00B7 above, which CREATES the
                        # per-agent record 0x00B6 writes into. Reversed, the
                        # client drops it with no error (RUNS.md §13).
                        if SECONDARY_BITS:
                            send(GAME_SMSG_PLAYER_UPDATE_SECONDARY_BITS,
                                 agents.agent_set_secondary_bits(
                                     PLAYER_AGENT_ID, SECONDARY_BITS),
                                 f"PLAYER_UPDATE_SECONDARY_BITS"
                                 f"(0x{SECONDARY_BITS:04X})")
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
                        if NETGRAPH_FLAGS is not None:
                            # AFTER the load, not before: the widget this
                            # unlocks is built by a routine that reads the flag
                            # at construction time, so a byte that arrives
                            # before the UI exists sets a bit nothing is left
                            # to read. Sent once -- the handler is idempotent
                            # and re-sending would only re-clear the two bits
                            # we do not understand.
                            send(GAME_SMSG_UI_OVERLAY_FLAGS, [NETGRAPH_FLAGS],
                                 f"UI_OVERLAY_FLAGS(0x{NETGRAPH_FLAGS:02x}"
                                 + (", netgraph latency"
                                    if NETGRAPH_FLAGS
                                    & UI_OVERLAY_FLAG_NETGRAPH_LATENCY
                                    else "") + ")")
                        # An AREA brings its own population and replaces the
                        # single global enemy outright. Both would be wrong:
                        # the global one is placed by offset from the player,
                        # so it would appear in the middle of an authored zone
                        # that has its own idea of what stands where.
                        if AREA_NAME:
                            spawn_population(send, state,
                                             (pos[0], pos[1], cfg[2]), conn_id)
                        elif SPAWN_ENEMY:
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
                    elif opcode == GAME_CMSG_CLIENT_PERF_REPORT:
                        handle_perf_report(values, send, state, conn_id)
                    else:
                        # D9(a), game half. Sixteen opcodes over fourteen arms
                        # against 194 schema layouts, so this is still the common
                        # path and not an exception.
                        #
                        # MEASURED 2026-08-13 over the whole loopback tree (425
                        # connections, 17,770 framed c2s): this branch took 2,858
                        # messages, 16.1%, before the 2026-08-13 arms and 1,584,
                        # 8.9%, after them. The remainder is real -- 0x000A, 0x000B
                        # and 0x000D are the three largest -- and it is visible
                        # rather than silent, which is the whole point of D9(a).
                        # test_dispatch.py reports any opcode `overrides.json`
                        # has NAMED that lands here without an allowlist row.
                        note_unhandled(state, conn_id, "GAME_CMSG", opcode,
                                       name, rec)
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
                else:
                    # D9(a), auth half. Reached only when kind == "auth": the
                    # `if kind == "game"` arm above owns the whole game channel
                    # and ends in its own else.
                    #
                    # An `elif kind != "auth": pass` used to sit at the head of
                    # this chain, from before the game channel had a chain of its
                    # own. It was UNREACHABLE -- `kind` is two-valued
                    # (`"auth" if header == AUTH_CMSG_VERSION_HEADER else "game"`,
                    # one site), so game took the first arm and auth made the test
                    # false. Removed 2026-08-11: dead code that reads like a
                    # catch-all, sitting directly above a real catch-all, is worse
                    # than no code. Its one real insight is kept here, because it
                    # is why this else must not try to be clever: THE TWO CATALOGS
                    # COLLIDE NUMERICALLY -- GAME_CMSG 0x0002 is TRADE_ADD_ITEM,
                    # not SEND_COMPUTER_HASH -- so answering an opcode from the
                    # wrong catalog is worse than silence. Naming the channel in
                    # the log is the whole job here.
                    note_unhandled(state, conn_id, "AUTH_CMSG", opcode,
                                   name, rec)

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
        # THE SUMMARIES RUN IN `finally`, AND THAT IS THE WHOLE POINT.
        # They sat after the read loop inside the `try` for one day and never
        # once executed: the loop exits by ConnectionResetError, because the
        # harness kills the client, so control jumps to `except` and skips
        # them. MEASURED 2026-08-11 -- a 45 s loopback run recorded 7
        # `unhandled` events and 10 clean ping round trips and wrote ZERO
        # summary records. The tallies were correct, the reporting was
        # unreachable, and every offline test passed because it called these
        # functions directly rather than asking whether anything calls them.
        # That is the D9(a) defect exactly, one file over: a number the server
        # knows and the operator never sees.
        report_unhandled(state, conn_id, rec)
        report_ping(state, conn_id, rec)
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
    global UNLOCKED, UNLOCK_LABEL, SPAWN_PROFESSION, SECONDARY_BITS

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
    # DEFAULT CHANGED 2026-08-13, all -> corpus. `all` is MEASURED to crash the
    # client's own Skills panel: it unlocks 2,109 weapon modifiers and other
    # non-player rows that have no skill icon, and the loader asserts `fileId`
    # (File.cpp:367) building the list. `corpus` is the same run with membership
    # corrected and was observed listing 1,333 skills in 43 attribute groups with
    # the client answering every ping. A default that breaks the game the moment
    # a player presses K is not a default. studies/profession/RUNS.md §11.
    ap.add_argument("--unlocks", default="corpus",
                    help="Unlock bitmap sent as opcodes 29 and 219: 'all' "
                         "(ids 1..3442 -- NOT 0, see refuse_skill_zero), "
                         "'corpus' (only the 1,333 player-usable skills, "
                         "derived from the owner's own client at run time), "
                         "'none', 'bar' (exactly the --skills ids), or an "
                         "explicit comma-separated id list. Whether the client "
                         "REFUSES to draw a bar skill that is not unlocked is "
                         "NOT FOUND in every source we have; this flag exists "
                         "to settle it by experiment. 'all' is known to reach "
                         "a `fileId` assert (File.cpp:367) when the Skills "
                         "panel opens -- it unlocks 2,109 weapon modifiers and "
                         "other non-player rows that have no skill icon "
                         "(studies/profession/RUNS.md §11).")
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
    ap.add_argument("--netgraph", nargs="?", const="0x04", default=None,
                    metavar="BYTE",
                    help="Send GAME_SMSG 0x016E once after the instance loads, "
                         "carrying this byte of UI-overlay flags. Default 0x04, "
                         "which is the bit the client tests before building the "
                         "net graph's LATENCY widget -- the readout our 0x000D "
                         "round trip feeds. The graph FRAME is a separate "
                         "object toggled by a keypress, so this alone may set "
                         "a bit nothing draws. studies/smsg, s_netGraph.")
    ap.add_argument("--probe", metavar="NAME",
                    help="After the character spawns, fire a scripted experiment at "
                         "the client. See --list-probes. Only affects a session you "
                         "ask for it in; the default path is untouched.")
    ap.add_argument("--secondary-bits", default=None, metavar="MASK|all|ids",
                    help="Send GAME_SMSG 0x00B6 in the spawn burst: which "
                         "professions the character may take as a SECONDARY. "
                         "'all' = ids 1..10, or a comma-separated id list, or "
                         "an integer mask (0x.. accepted). Default: not sent "
                         "at all, which reproduces ArenaNet -- 11 of 11 live "
                         "samples carry mask 0 for characters with nothing "
                         "unlocked. THE DROP-DOWN THAT READS THIS ONLY EXISTS "
                         "IN 15 ARENA MAPS (796 Codex Arena, 823-836), so "
                         "expect no visible effect anywhere else "
                         "(studies/profession/RUNS.md §13).")
    ap.add_argument("--spawn-profession", type=int, default=None, metavar="N",
                    help="Primary profession the SPAWN BURST's 0x00B7 carries "
                         f"(default {PROF_WARRIOR}). The clean delivery for a "
                         "custom id: bar, unlocks and attributes all arrive "
                         "AFTER it in the same burst, nothing is re-sent "
                         "mid-session, and opening the skills panel is the "
                         "session's first provocation (RUNS.md s8 -- a "
                         "mid-session re-send asserts the client even at a "
                         "legal profession). Out-of-band ids (11..255) are the "
                         "experiment and are announced loudly; the appearance "
                         "nibble stays at the default on purpose, being "
                         "different bound-checked storage.")
    ap.add_argument("--list-probes", action="store_true",
                    help="Print the available probes, their questions and their "
                         "predictions, then exit.")
    ap.add_argument("--ping-seconds", type=float, default=None, metavar="S",
                    help="Override the 0x000C cadence (default 5.000, ArenaNet's own "
                         "measured value). Raise it ONLY for a run that needs the "
                         "client's reply as a liveness heartbeat -- the opcode sweep "
                         "localises a crash to the gap between two replies.")
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
    ap.add_argument("--area", metavar="NAME",
                    help="Serve the POPULATION of this authored area: the "
                         "`content/world.toml` spawn rows carrying "
                         "`area = NAME`, at their own coordinates, each checked "
                         "against the navmesh before a body goes out. Replaces "
                         "the single global test enemy rather than adding to "
                         "it, since that one is placed by offset from the "
                         "player and would land in the middle of a zone that "
                         "has its own idea of what stands where.")
    ap.add_argument("--practice-target", action="store_true",
                    help="The standing hostile neither chases nor attacks -- a "
                         "PRACTICE TARGET. WIKI (GWW, \"Practice target\", rev. "
                         "2014-02-07): practice targets are stationary NPCs, there "
                         "are allied and hostile ones, and 'They do not use any "
                         "skills'; a slain hostile one resurrects after 30 s at full "
                         "health. So this is a real Guild Wars creature's behaviour "
                         "rather than a test switch. It is what makes an agent "
                         "death REACHABLE unattended: with the hostile fighting back "
                         "the player loses the race (25 damage a hit into 100 HP, "
                         "four hits, against the seven the player needs) and never "
                         "lands one.")
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
    ap.add_argument("--player-flags", type=lambda s: int(s, 0), default=None,
                    metavar="VALUE",
                    help="Send GAME_SMSG 0x003C (player number, VALUE, mask 7) "
                         "immediately before WORLD_CREATE_AGENT, which is retail's "
                         "own position for it: 423 sends over 12 of 12 live "
                         "connections, all inside the instance load, and this "
                         "server has never sent it. A lone player is VALUE 4 in "
                         "every single-connection capture. Omit for the control "
                         "arm — sending it LATE was already measured as a clean "
                         "null (RESKIN.md 18.8), so what this asks is whether a "
                         "LOAD-time write behaves differently.")
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

    if a.ping_seconds is not None:
        if not 0.05 <= a.ping_seconds <= 60.0:
            raise SystemExit(f"--ping-seconds {a.ping_seconds} is outside 0.05..60. "
                             f"The tick is {TICK_SECONDS}s, so anything below it cannot "
                             f"be honoured and would misreport the cadence.")
        global PING_SECONDS
        PING_SECONDS = a.ping_seconds
        print(f"PING CADENCE: {PING_SECONDS}s instead of ArenaNet's measured 5.000s. "
              f"This is a LIVENESS instrument, not a fidelity setting -- the client's "
              f"reply is the only evidence its message pump is still running.")

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
        # RIGHT HERE, and not at instance load. We know which map this run will
        # serve, and nothing has opened the archive yet -- both halves are only
        # true at startup. See prewarm_pathmap() for what reading it late cost.
        prewarm_pathmap(a.map if known else FALLBACK_MAP_ID)

    if a.area:
        global AREA_NAME
        AREA_NAME = a.area
        # RESOLVE THE POPULATION NOW, not at instance load. The set checks --
        # duplicate agent ids, duplicate definition indices, a missing id -- are
        # exactly the ones whose cost is a wasted client run, and a run that
        # dies on the fourth of five bodies has already put three in the world.
        try:
            pop = area_population(a.area)
        except PopulationError as exc:
            raise SystemExit(f"--area {a.area}: {exc}")
        print(f"AREA: {a.area} -- {len(pop)} spawn row(s): "
              + (", ".join(k for k, _ in pop) or "none")
              + ". This REPLACES the standing test enemy.")

    if a.practice_target:
        global ENEMY_ATTACKS_BACK
        ENEMY_ATTACKS_BACK = False
        print("PRACTICE TARGET: the hostile stands still and does not attack. "
              "It can still be hit, killed and revived.")

    if a.no_enemy:
        global SPAWN_ENEMY
        SPAWN_ENEMY = False
        print("NO ENEMY: the world will contain the player and nothing else.")

    if a.no_weapon:
        global EQUIP_WEAPON
        EQUIP_WEAPON = False
        print("NO WEAPON: the character's four weapon slots stay empty.")

    if a.netgraph is not None:
        global NETGRAPH_FLAGS
        try:
            NETGRAPH_FLAGS = int(a.netgraph, 0) & 0xFF
        except ValueError:
            raise SystemExit(f"--netgraph {a.netgraph!r} is not a number. "
                             f"It is one byte of UI-overlay flags, e.g. 0x04.")
        bits = [n for b, n in ((0x01, "bit0"), (0x02, "bit1"),
                               (0x04, "NETGRAPH LATENCY"))
                if NETGRAPH_FLAGS & b]
        print(f"NETGRAPH: sending GAME_SMSG 0x016E = 0x{NETGRAPH_FLAGS:02x} "
              f"once after the instance loads"
              + (f" -- {', '.join(bits)}" if bits else
                 " -- no bits set, which CLEARS all three"))

    if a.player_flags is not None:
        global PLAYER_FLAGS
        # Validate HERE rather than at send time: a bad value would otherwise
        # raise on the burst thread, mid-instance-load, where the traceback lands
        # in a capture nobody reads and the client just fails to spawn.
        agents.player_flags(PLAYER_NUMBER, a.player_flags)
        PLAYER_FLAGS = a.player_flags
        print(f"PLAYER_FLAGS: sending 0x003C (player {PLAYER_NUMBER}, value "
              f"{a.player_flags}, mask 7) before WORLD_CREATE_AGENT")
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
    if a.spawn_profession is not None:
        try:
            spawn_profession_values(a.spawn_profession)
        except ValueError as ex:
            raise SystemExit(f"--spawn-profession: {ex}")
        SPAWN_PROFESSION = a.spawn_profession
        band = ("OUT OF BAND -- the client does not ship this id; "
                "this session is the experiment"
                if SPAWN_PROFESSION > agents.CHAR_PROFESSIONS - 1
                else "in band, non-default")
        print(f"SPAWN PROFESSION: {SPAWN_PROFESSION} ({band})")
    if a.secondary_bits is not None:
        spec = a.secondary_bits.strip()
        try:
            if spec == "all":
                SECONDARY_BITS = agents.ALL_SECONDARIES
            elif "," in spec or spec.isdigit() and len(spec) <= 2:
                SECONDARY_BITS = agents.secondary_bits(
                    *[int(s, 0) for s in spec.split(",") if s.strip()])
            else:
                SECONDARY_BITS = int(spec, 0)
                agents.agent_set_secondary_bits(PLAYER_AGENT_ID, SECONDARY_BITS)
        except ValueError as ex:
            raise SystemExit(f"--secondary-bits {spec!r}: {ex}")
        offered = [p for p in range(1, 32) if SECONDARY_BITS >> p & 1]
        print(f"SECONDARY BITS: 0x{SECONDARY_BITS:04X} -- offers professions "
              f"{offered} as secondaries. The drop-down that reads this exists "
              f"ONLY in maps 796 and 823-836; elsewhere it is not built at all.")

    warning = spawn_probe_warning(
        a.probe, a.spawn_profession is not None,
        a.spawn_profession is not None
        and a.spawn_profession > agents.CHAR_PROFESSIONS - 1)
    if warning:
        print(warning)
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
    # WHICH TREE IS SERVING THIS RUN. The harness spawns authsrv.py from its OWN
    # directory (session.py's TOOLKIT is derived from __file__), so launching a
    # different worktree's session.py silently runs THAT worktree's server. On
    # 2026-08-13 a run reported as testing a fix was served by a parallel
    # session's tree carrying the pre-fix code, and the only tell was a count in
    # this banner. Trees are not copies of each other -- CLAUDE.md opens on that
    # -- so the server now names the one it came from, in the log the diagnosis
    # actually reads.
    print(f"source:    {os.path.dirname(os.path.abspath(__file__))}")

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
