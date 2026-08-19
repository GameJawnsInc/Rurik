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
    # [0, 0] is what ArenaNet sent on all 8 live connections (state-conditional
    # -- see the constant's comment in authsrv.py). This row is a hand-copy like
    # every other row here, so it binds nothing by itself; the check that
    # actually reddens on an ATTRIBUTE_POINTS edit is in section 3.
    (0x0037, [PLAYER_AGENT_ID, 0, 0], "AGENT_UPDATE_ATTRIBUTE_POINTS"),
    (0x00B7, [PLAYER_AGENT_ID, PROF_WARRIOR, 0, 0], "AGENT_PROFESSIONS"),
    # THREE COLUMNS, not five triples: every id, then every rank, then the
    # third column. The client slices ONE flat array at n and 2n (handler
    # 0x0091D920), so `(id, rank, rank)` apiece is a different message -- and
    # for one day on 2026-08-15 it was what we sent, which killed the client
    # on CharData:202. Section 4 binds this to the module rather than leaving
    # it a hand-copy, and reproduces the fatal layout as its own control.
    # The ids are the client's own s_attrib indices for profession 1
    # (Warrior); the ranks are invented and distinct on purpose.
    (0x003A, [PLAYER_AGENT_ID,
              [17, 18, 19, 20, 21, 12, 9, 6, 3, 1, 12, 9, 6, 3, 1]],
     "AGENT_UPDATE_ATTRIBUTES"),
    (0x0022, [PLAYER_AGENT_ID, 3], "WORLD_UPDATE_CONTROLLED_AGENT"),
    (0x018E, [], "INSTANCE_LOAD_FINISH"),
]

# Byte widths as the codec packs them.
WIDTH = {"byte": 1, "word": 2, "dword": 4, "float": 4, "vec2": 8,
         "agent_id": 4, "msg_header": 2}

# OpenTyria's GmAgent.c field names, which state their own offsets.
NAMED_OFFSETS = {0x0B: "h000B", 0x1E: "h001E", 0x23: "h0023", 0x27: "h0027",
                 0x3B: "h003B", 0x4B: "h004B", 0x59: "h0059"}

# The floor is 38 because nothing here is optional and nothing varies with a
# fixture: 9 burst messages that must encode, then 7 named struct offsets plus
# the total closing at 0x63 plus its agreement with declared_unpack_size, then 3
# sourced values, then the ATTRIBUTE_POINTS binding, then section 4's 10 shape
# checks, its CONTROL, and 5 refusals. Measured from a green run on 2026-08-15
# (was 34 before section 4 learned to slice the payload the client's way). If
# this run reports fewer, a section stopped executing -- most likely the section
# 2 field walk hitting an unhandled type and breaking out early, which drops the
# offset checks that are the whole reason this file exists.
LEDGER = checks.Ledger("spawn burst", floor=38)
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

    # The 0x0037 payload, bound to the MODULE rather than to this file's
    # hand-copied table: ArenaNet sent [0, 0] on 8 of 8 live connections
    # (both captures, once per connection at load -- the constant's comment
    # in authsrv.py carries the hex and the state-conditional caveat).
    # Editing ATTRIBUTE_POINTS goes red here until the new value cites its
    # own wire evidence.
    import authsrv
    check(authsrv.ATTRIBUTE_POINTS == 0,
          "ATTRIBUTE_POINTS is 0, the 8-of-8 live-capture value, not "
          "OpenTyria's uncited 50")

    print("\n4. 0x003A is COLUMN-MAJOR, and refuses what the client would")
    import agents
    payload = authsrv.attribute_columns()
    # Bound to the MODULE, so the hand-copied BURST row above cannot drift
    # away from what the server actually sends.
    want_ids = [a for a, _ in agents.PLAYER_ATTRIBUTE_RANKS]
    want_ranks = [r for _, r in agents.PLAYER_ATTRIBUTE_RANKS]
    want = want_ids + want_ranks + want_ranks
    # By OPCODE, not by position: the burst's order is exactly the kind of
    # thing that changes, and a positional index would then compare against
    # whatever moved into the slot instead of failing honestly.
    row = next(v for op, v, _ in BURST if op == 0x003A)
    check(payload == want and payload == row[1],
          "the emitted payload is the content row's ranks, column-major",
          f"{payload}")
    check(len(payload) % 3 == 0,
          f"its length is divisible by 3 ({len(payload)}) -- the client's "
          f"handler divides the wire count by three (ATTRIBUTES.md 1.2), so a "
          f"length that is not is a different message than we think")
    check(len(payload) // 3 <= authsrv.ATTRIBUTE_COLUMN_MAX,
          f"{len(payload) // 3} attributes, within the array32's declared 48 "
          f"elements = {authsrv.ATTRIBUTE_COLUMN_MAX} per column")

    # THE CLIENT'S OWN SLICING, reproduced. 0x0091D920 computes n = count/3
    # and hands the loop three pointers -- payload+0xc, +0xc+4n, +0xc+8n --
    # so this is what the writer 0x00819270 actually receives, not what our
    # builder thinks it wrote. Every check below reads these, never `payload`
    # at a stride, because a stride-3 read of a column-major array is exactly
    # the mistake under test and would agree with itself.
    n = len(payload) // 3
    ids, ranks, third = payload[:n], payload[n:2 * n], payload[2 * n:]
    check(ids == want_ids,
          f"column 1 decodes to the attribute ids ({ids})")
    check(all(0 <= i < authsrv.CHAR_ATTRIBS for i in ids),
          f"every id is inside the client's s_attrib table ({ids})")
    check(len(set(ids)) == len(ids), "and no attribute is written twice")
    check(ranks == want_ranks,
          f"column 2 decodes to the ranks ({ranks})")
    check(len(set(ranks)) == len(ranks),
          f"the ranks are DISTINCT ({ranks}) -- which is what makes a "
          f"column-order error visible on the panel rather than plausible")
    check(third == ranks,
          "column 3 carries the same value, reproducing the invariant the "
          "client's own pending-change apply maintains (both take the "
          "identical delta; studies/combat/PLAN.md 8a)")
    # The bound the crash was about. Column 2 goes into s_attribPoints[rank],
    # whose arrsize is 13 -- read out of the client's own `cmp esi, 0Dh` by
    # toolkit/clientscan/attribpoints.py, not typed in here.
    check(all(0 <= r <= authsrv.ATTRIBUTE_RANK_MAX for r in ranks),
          f"every value the client will index s_attribPoints with is "
          f"0..{authsrv.ATTRIBUTE_RANK_MAX} ({ranks})")

    # THE CONTROL, because the six checks above are ours agreeing with
    # ourselves and would all pass on any self-consistent layout. This
    # rebuilds the interleaved form that shipped on 2026-08-15, slices it the
    # CLIENT's way, and requires it to produce an out-of-range rank. If this
    # goes green the checks above are not discriminating and mean nothing.
    fatal = [x for a, r in agents.PLAYER_ATTRIBUTE_RANKS for x in (a, r, r)]
    bad = [r for r in fatal[n:2 * n] if not 0 <= r <= authsrv.ATTRIBUTE_RANK_MAX]
    check(bool(bad),
          f"CONTROL: the interleaved layout puts {bad} in column 2, past "
          f"arrsize(s_attribPoints) -- so these checks can go red, and did",
          f"interleaved={fatal} -> column2={fatal[n:2 * n]}")

    # The refusals. Each is a bound the CLIENT asserts, so a clamp here would
    # hide a caller bug behind a valid-looking message.
    for bad, why in ((((51, 1),), "an id past the s_attrib table"),
                     (((17, 13),), "a rank above ArenaNet's cap of 12"),
                     (((17, -1),), "a negative rank"),
                     (((17, 1), (17, 2)), "the same attribute twice"),
                     (tuple((i, 1) for i in range(17)), "17 attributes")):
        raised = False
        try:
            authsrv.attribute_columns(bad)
        except ValueError:
            raised = True
        check(raised, f"REFUSES {why}")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
