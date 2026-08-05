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

# What the client asks for, in the order it asks. OpenTyria answers REQUEST_ITEMS
# with a dozen messages (inventory, weapon sets, gold, factions, quests...). We
# send only the ones that drive the state machine, so that a stall names a missing
# message rather than hiding inside a burst of guesses.
GAME_CMSG_INSTANCE_LOAD_REQUEST_SPAWN = 0x0088
GAME_CMSG_INSTANCE_LOAD_REQUEST_PLAYERS = 0x0090
GAME_CMSG_INSTANCE_LOAD_REQUEST_ITEMS = 0x0091

GAME_SRV_HOST = "127.0.0.1"
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

        def send(opcode, values, label):
            blob = codec.encode(smsg, opcode, values)
            sock.sendall(s2c.crypt(blob))
            print(f"[c{conn_id}] s2c {label} (0x{opcode:04x}, {len(blob)}B)", flush=True)
            rec.event("sent", opcode=opcode, label=label,
                      plain=binascii.hexlify(blob).decode())

        if kind == "game":
            # 0x31 | Prophecies(2) | Factions(4) | Nightfall(8) = 0x3F, straight
            # from OpenTyria. Unlocking everything is wrong for a level 1 pre-Searing
            # character but is the permissive choice while we are still learning
            # which of these the client validates.
            send(GAME_SMSG_INSTANCE_LOAD_HEAD, [0x3F, 0x3F, 0, 0],
                 "INSTANCE_LOAD_HEAD")
            send(GAME_SMSG_INSTANCE_PLAYER_DATA_START, [], "PLAYER_DATA_START")
            send(GAME_SMSG_INSTANCE_LOAD_PLAYER_NAME, [TEST_CHAR_NAME],
                 "INSTANCE_LOAD_PLAYER_NAME")
            send(GAME_SMSG_INSTANCE_LOAD_INFO,
                 [1,          # agent_id -- the player's own agent, 1 for the first
                  map_id,     # echoed from the version frame, not guessed
                  0,          # is_explorable: Ascalon City is an outpost
                  0,          # district
                  0,          # language
                  0],         # is_observer
                 "INSTANCE_LOAD_INFO")

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
                        send(GAME_SMSG_ITEM_STREAM_CREATE, [0, 0],
                             "ITEM_STREAM_CREATE")
                        send(GAME_SMSG_MAP_UPDATE_CURRENT, [state["map_id"], 0],
                             "MAP_UPDATE_CURRENT")
                        send(GAME_SMSG_READY_FOR_MAP_SPAWN, [0],
                             "READY_FOR_MAP_SPAWN")
                    elif opcode == GAME_CMSG_INSTANCE_LOAD_REQUEST_PLAYERS:
                        send(GAME_SMSG_INSTANCE_PLAYER_DATA_DONE, [],
                             "PLAYER_DATA_DONE")
                    elif opcode == GAME_CMSG_INSTANCE_LOAD_REQUEST_SPAWN:
                        # map_file_id 0 is a placeholder: the real one comes from
                        # the map's static config, which we do not have yet. If the
                        # client refuses to spawn, this is the first thing to doubt.
                        send(GAME_SMSG_INSTANCE_LOAD_SPAWN_POINT,
                             [0, (0.0, 0.0), 0, 0, 0, b"\x00" * 8],
                             "INSTANCE_LOAD_SPAWN_POINT")
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
    global GAME_SRV_HOST, GAME_SRV_PORT

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=6112)
    ap.add_argument("--keys")
    ap.add_argument("--vault", default=VAULT_DEFAULT)
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
    ap.add_argument("--allow-any-session", action="store_true",
                    help="Accept a login with no matching session record. A debugging "
                         "escape hatch so a stale sessions.json cannot be mistaken for a "
                         "wire bug. Never the default: the rejection path has to stay exercised.")
    a = ap.parse_args()

    GAME_SRV_HOST, GAME_SRV_PORT = a.game_host, a.game_port

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
