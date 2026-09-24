"""henchparty.py -- the party family's henchman add, DESKWORK-D1 step 5.

A leaf: the PURE builders and rules for hiring an outpost henchman into the
party. The thin arm (`handle_henchman_add`) lives in authsrv.py; everything
here is stdlib + agents.py's own message builders, so a test can drive it
without a server.

WHAT THE TAPE SAYS (studies/cmsg/FINDINGS.md "The party family", capture
20260819T132414 connection :53419, an outpost, map 242, player 14):

  * SIX henchmen STAND in the outpost as ordinary kind-9 NPC bodies (agents
    1..6), each declared with 0x0056/0x0057, named 0x009B, professioned 0x00A6,
    and marked with `0x0071` -- a message the client's own handler
    (0x0091E220 -> 0x008113D0) BINARY-SEARCH-INSERTS the agent id into a sorted
    dword set at `[ctx+0x2c]+0x574` -- the same object 0x00B0's per-player
    array (+0x80C) lives in, NOT the party manager at [ctx+0x4c] that 0x01BF
    and 0x01B2 use. The set's enumerator 0x0080E200 is called from PtSearch
    (asserts PtSearch:365 `listFrame`, PtSearch:1116 `partySearchTab <
    LISTS`), which ties it to the party-search panel's lists from code.
    `0x0071` was sent for those six agents and NO other of the 44 kind-9 NPCs
    (38 others) on the connection, in both outpost connections and NEVER in
    the field -- so it is what marks an agent HIREABLE, i.e. what the party
    window's henchman list offers. OBSERVED (the correlation), the mechanism
    read from the handler. `hireable_mark` is that message.
  * Two more messages single the six out from every other kind-9 NPC: the
    displayed LEVEL, `0x009F [36, agent, level]` (agents.PROP_LEVEL -- 6 of 6
    henchmen carry it, 0 of 38 other kind-9 NPCs; players carry it too), and
    the proper name `0x009B`. Retail sends each henchman's pre-create burst
    TWICE per connection -- once at the load with the definitions, again as
    the body is created 5-9 s later -- in the order `0x009B, 0x009F [36],
    0x00A6, 0x0071, 0x00F0, 0x0020, 0x0161 (its weapon item), 0x006D`: the
    marker and the level come BEFORE the create. `hireable_bringup` is the
    level + marker pair; the server sends it once, before the create, and
    the rest of the burst is create_agent_world's own order (RECONSTRUCTION
    for the count and the surrounding order -- the 0x0071 handler looks no
    agent up and skips a duplicate, so neither can matter to the set).
  * c2s `0x009F` HENCHMAN_ADD carries ONE word -- the standing henchman's agent
    id (32927 -> [4], [2], [6]) -- and is answered 31-132 ms later by
    `0x00B0` PLAYER_PARTY_SIZE **then** the `0x01BF` roster row, in ONE plaintext
    chunk, 3 of 3. **Size before row** (the hero KICK answers row 0x01C3 then
    size, so the henchman is the size-then-row shape). `henchman_add_batch` is
    that pair, in that order.
  * The standing henchman is NOT destroyed by the add -- no 0x0021 follows, the
    NPC keeps standing in the outpost -- and the party grows by one, to a cap of
    the map's own `max_party` (242 reads 4 in the client's AreaInfo, and the
    three adds fill 1 player -> 4). `party_is_full` is that cap.
  * `0x01BF`'s two trailing bytes, NOT FOUND in agents.party_henchman_add's
    docstring, are settled here from the wire: byte4 == the agent's `0x00A6`
    profession (2/1/7 for the three, 3 of 3) and byte5 == its `0x0056` LEVEL
    (3, the Shing Jea level-3 henchmen), so they are PROFESSION and LEVEL,
    CORROBORATED. The proper NAME on `0x01BF` is the agent's `0x009B` name, NOT
    its definition's `0x0056` name (they differ on tape).
  * Their 0x0020 allegiance dword is 'play' (ALLEGIANCE_PLAYER), 6 of 6 on
    both outpost connections, where every other kind-9 NPC there is 'nonc'
    (43 of 43, 36 of 36). The server's rows spawn them `noncombatant` --
    RECONSTRUCTION, and a deliberate one: every party-body path in authsrv
    (party_bodies, the follow, the ally casts, the formation) keys on
    ALLEGIANCE_PLAYER, so a 'play' standing NPC would follow the player and
    fight; a `standing` gate on those paths is the next increment
    (content/world.toml's rows say so).

Read-only of the tape; the batch itself is what the server sends. authsrv.py
mirrors the two opcodes below as GAME_SMSG_PARTY_HENCHMAN_HIREABLE and
GAME_SMSG_PLAYER_PARTY_SIZE; test_henchparty locks the pairs equal.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import agents  # noqa: E402

# The message the client uses to mark an agent as a hireable henchman: its
# handler inserts the agent id into the party window's sorted set (see the
# module docstring). We SEND it; there is no reply.
HENCHMAN_HIREABLE = 0x0071
# 0x00B0 PLAYER_PARTY_SIZE -- agents.player_party_size builds the VALUES for it
# but not the opcode, so the batch names it here (the number is measured, not
# authored). authsrv's own GAME_SMSG_PLAYER_PARTY_SIZE is the same value.
PLAYER_PARTY_SIZE = 0x00B0
# 0x009F AGENT_PROPERTY_UPDATE_INT -- the int-property channel the displayed
# level (agents.PROP_LEVEL) rides; authsrv's GAME_SMSG_AGENT_PROPERTY_UPDATE_INT.
AGENT_PROPERTY_UPDATE_INT = 0x009F


def hireable_mark(agent_id):
    """(0x0071, [agent_id], label) -- add `agent_id` to the party window's
    hireable-henchman set, so the panel offers it. Retail sends it in each
    henchman's pre-create burst (before 0x0020), twice per connection, in an
    outpost only (0 of 85 field or non-hireable-outpost connections); the
    server sends it once, before the create (RECONSTRUCTION for the count --
    the handler skips a duplicate id, so once is the set retail ends with)."""
    if not isinstance(agent_id, int) or agent_id <= 0:
        raise ValueError(
            f"hireable agent_id {agent_id!r} must be a positive int -- it is the "
            f"agent whose body is about to be created")
    return (HENCHMAN_HIREABLE, [agent_id],
            f"PARTY_HENCHMAN_HIREABLE(agent {agent_id})")


def hireable_bringup(agent_id, level):
    """The two pre-create messages that single a hireable henchman out from
    every other kind-9 NPC on the tape, in retail's order: the displayed LEVEL
    (0x009F [36, agent, level] -- 6 of 6 henchmen, 0 of 38 other kind-9 NPCs)
    then the hireable MARK (0x0071). Each element is (op, vals, label); the
    caller sends them before create_agent_world."""
    if not isinstance(level, int) or level <= 0:
        raise ValueError(
            f"hireable level {level!r} must be a positive int -- it is the level "
            f"the party window shows beside the name (and 0x01BF's byte5)")
    return [
        (AGENT_PROPERTY_UPDATE_INT, [agents.PROP_LEVEL, int(agent_id), int(level)],
         f"level {level} on hireable agent {agent_id} (prop 36, before its create)"),
        hireable_mark(agent_id),
    ]


def henchman_add_batch(party_id, player_number, party_size, agent_id,
                       enc_name, profession, level):
    """The reply to c2s 0x009F HENCHMAN_ADD: [0x00B0 size, 0x01BF row], in the
    tape's order (SIZE BEFORE ROW, 3 of 3 on 20260819T132414).

    `enc_name` is the henchman's PROPER name as an encoded wire string (the
    agent's 0x009B name); `profession` and `level` are 0x01BF's two trailing
    bytes (OBSERVED == the agent's 0x00A6 profession and 0x0056 level). Both
    messages are agents.py's own tested builders, so the shapes are the client's
    descriptors, not this module's invention. Each element is (op, vals, label)."""
    return [
        (PLAYER_PARTY_SIZE,
         agents.player_party_size(player_number, party_size),
         f"PLAYER_PARTY_SIZE({party_size}) -- after the henchman add"),
        agents.party_henchman_add(party_id, agent_id, enc_name,
                                  profession, level),
    ]


def party_is_full(member_count, cap):
    """True when the party (player + heroes + henchmen already in it) is at or
    over the cap, so a further add -- henchman OR hero -- must be refused. The
    cap is the client's own AreaInfo max_party for the served map (242 -> 4);
    the server holds it as one constant today (authsrv.OUTPOST_PARTY_CAP)."""
    return int(member_count) >= int(cap)
