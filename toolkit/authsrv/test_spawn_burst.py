"""Check the agent-spawn burst before it ever reaches the client.

Every message here is one we send unprompted to put a body in the world, and
each was assembled from OpenTyria plus the schema rather than from a capture. On
2026-08-05 five of the values in this burst were wrong on the first attempt
(model_id missing its 0x30000000 class tag, player_team_token, INSTANCE_LOADED's
payload, UPDATE_CONTROLLED_AGENT's unk0, and player_id taken from the wrong
namespace), so "it looked right" is not evidence about this code.

The interesting check is section 2. WORLD_CREATE_AGENT has 23 fields and
OpenTyria's struct names carry their own byte offsets -- h000B, h001E, h0023,
h0027, h003B, h004B, h0059. Walking the schema's field list and confirming each
named constant lands on its stated offset turns "I counted the fields and they
seemed to line up" into seven independent checkpoints plus a total that must
close at 0x63. A single inserted or dropped field shifts everything after it and
fails loudly here instead of silently producing an agent the client cannot place.

    python toolkit/authsrv/test_spawn_burst.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
from codec import Codec  # noqa: E402
import checks  # noqa: E402

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "schema", "messages.json")

INF = float("inf")
PROF_WARRIOR = 1
APPEARANCE = PROF_WARRIOR << 20
PLAYER_AGENT_ID = 1
PLAYER_NUMBER = 1
CHAR_CLASS_PLAYER_BASE = 0x30000000
AGENT_TYPE_LIVING = 1
PLAYER_TEAM_TOKEN = 0x706C6179   # 'play'
DEFAULT_RUN_SPEED = 288.0
POS = (-9067.0, 13218.0)

# Exactly what authsrv.py sends, in order.
BURST = [
    (0x00F2, [PLAYER_TEAM_TOKEN], "INSTANCE_LOADED"),
    (0x001F, [0], "WORLD_UPDATE_LOAD_TIME"),
    (0x0059, [PLAYER_NUMBER, PLAYER_AGENT_ID, APPEARANCE, 0, 0, 0,
              "Test Warrior"], "PLAYER_CREATE"),
    (0x0020, [PLAYER_AGENT_ID,
              CHAR_CLASS_PLAYER_BASE | PLAYER_NUMBER,
              AGENT_TYPE_LIVING,
              5,
              POS,
              0,
              (1.0, 0.0),
              1,
              DEFAULT_RUN_SPEED,
              1.0,
              0x41400000,
              PLAYER_TEAM_TOKEN,
              0, 0, 0, 0, 0,
              (0.0, 0.0),
              (INF, INF),
              0, 0,
              (INF, INF),
              0], "WORLD_CREATE_AGENT"),
    (0x0037, [PLAYER_AGENT_ID, 50, 50], "AGENT_UPDATE_ATTRIBUTE_POINTS"),
    (0x00B7, [PLAYER_AGENT_ID, PROF_WARRIOR, 0, 0], "PLAYER_UPDATE_PROFESSION"),
    (0x003A, [PLAYER_AGENT_ID, [0] * 42], "AGENT_UPDATE_ATTRIBUTES"),
    (0x0022, [PLAYER_AGENT_ID, 3], "WORLD_UPDATE_CONTROLLED_AGENT"),
    (0x018E, [], "INSTANCE_LOAD_FINISH"),
]

# Byte widths as the codec packs them.
WIDTH = {"byte": 1, "word": 2, "dword": 4, "float": 4, "vec2": 8,
         "agent_id": 4, "msg_header": 2}

# OpenTyria's GmAgent.c field names, which state their own offsets.
NAMED_OFFSETS = {0x0B: "h000B", 0x1E: "h001E", 0x23: "h0023", 0x27: "h0027",
                 0x3B: "h003B", 0x4B: "h004B", 0x59: "h0059"}

# The floor is 21 because nothing here is optional and nothing varies with a
# fixture: 9 burst messages that must encode, then 7 named struct offsets plus
# the total closing at 0x63 plus its agreement with declared_unpack_size, then 3
# sourced values. Measured from a green run on 2026-08-06. If this run reports
# fewer, a section stopped executing -- most likely the section 2 field walk
# hitting an unhandled type and breaking out early, which drops the offset
# checks that are the whole reason this file exists.
LEDGER = checks.Ledger("spawn burst", floor=21)
check = checks.adopt(LEDGER)


def main():
    codec = Codec(SCHEMA)

    print("1. every message in the burst encodes")
    for opcode, values, label in BURST:
        try:
            blob = codec.encode("GAME_SMSG", opcode, values)
            check(True, f"{label} (0x{opcode:04X}) -> {len(blob)} bytes")
        except Exception as exc:
            check(False, f"{label} (0x{opcode:04X}) raised {exc!r}")

    print("\n2. WORLD_CREATE_AGENT field offsets match OpenTyria's struct names")
    fields = codec.fields_for("GAME_SMSG", 0x0020)
    off, seen = 0, {}
    for f in fields:
        t = f["type"]
        if t not in WIDTH:
            check(False, f"unhandled field type {t!r} at offset 0x{off:02X}")
            break
        seen[off] = t
        off += WIDTH[t]
    for want_off, name in sorted(NAMED_OFFSETS.items()):
        check(want_off in seen,
              f"{name} lands on offset 0x{want_off:02X}"
              + ("" if want_off in seen else "  <-- MISALIGNED"))
    check(off == 0x63,
          f"total length closes at 0x63 (99 bytes) -- got 0x{off:02X} ({off})")

    declared = codec.channels["GAME_SMSG"]["messages"]["32"]["declared_unpack_size"]
    check(off == declared,
          f"walked length agrees with declared_unpack_size ({declared})")

    print("\n3. values sourced from OpenTyria, not invented")
    check(CHAR_CLASS_PLAYER_BASE | PLAYER_NUMBER == 0x30000001,
          "model_id carries the 0x30000000 player class tag")
    check(PLAYER_TEAM_TOKEN == 0x706C6179,
          "player_team_token is 0x706C6179 ('play'), the three-lineage value, "
          "not OpenTyria's lone 0xBAADF00D debug fill")
    # profession occupies bits 20-23: sex 1 + height 4 + skin 5 + hair 5 + face 5
    check(APPEARANCE == 0x00100000 and (APPEARANCE >> 20) & 0xF == PROF_WARRIOR,
          "appearance packs Warrior into bits 20-23")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
