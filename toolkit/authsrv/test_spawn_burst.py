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
    # (available, points_total) -- TWO numbers from the character's own state,
    # not one constant twice. This row was [0, 0] until 2026-08-20, on the
    # reading that every 0x0037 ArenaNet sent carried [0, 0] -- 8 of 8 live
    # connections. The corpus is 13 captures and 48 sightings now and says the
    # eight were simply eight low-level characters: field 3 is what is LEFT and
    # field 4 is the LIFETIME total (studies/pvpui/FINDINGS.md 32.5). The
    # numbers below are this content row's -- 200 lifetime, 173 sunk into the
    # five ranks, 27 unspent. A hand-copy like every other row here, so it binds
    # nothing by itself; section 4 is what reddens when the state moves.
    (0x0037, [PLAYER_AGENT_ID, 27, 200], "AGENT_UPDATE_ATTRIBUTE_POINTS"),
    (0x00B7, [PLAYER_AGENT_ID, PROF_WARRIOR, 0, 0], "AGENT_PROFESSIONS"),
    # THREE COLUMNS, not five triples: every id, then every rank, then the
    # third column. The client slices ONE flat array at n and 2n (handler
    # 0x0091D920), so `(id, rank, rank)` apiece is a different message -- and
    # for one day on 2026-08-15 it was what we sent, which killed the client
    # on CharData:202. Section 5 binds this to the module rather than leaving
    # it a hand-copy, and reproduces the fatal layout as its own control.
    # The ids are the client's own s_attrib indices for profession 1
    # (Warrior); the ranks are invented and distinct on purpose.
    #
    # COLUMN 3 IS NOT COLUMN 2, and the 7 below is the whole reason. It is the
    # EFFECTIVE rank -- base plus what the character is WEARING -- and this
    # server equips the starter hammer, whose content row carries
    # `attribute_bonus = [[19, 1]]`. Hammer Mastery is attribute 19, so its
    # base 6 goes out as an effective 7, which is what the client drew on the
    # attribute panel in capture 20260820T113942. Every other gap is 0.
    (0x003A, [PLAYER_AGENT_ID,
              [17, 18, 19, 20, 21, 12, 9, 6, 3, 1, 12, 9, 7, 3, 1]],
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

# The floor is 48 because nothing here is optional and nothing varies with a
# fixture -- no vault, no capture, no client: 9 burst messages that must encode,
# then 7 named struct offsets plus the total closing at 0x63 plus its agreement
# with declared_unpack_size, then 3 sourced values, then section 4's 8
# point-balance checks plus its CONTROL plus the burst-row binding, then section
# 5's 11 shape checks, its CONTROL, and 5 refusals. Measured from a green run on
# 2026-08-21 (38 before the ATTRIBUTE_POINTS constant became per-character state
# and section 4 replaced it; 34 before section 5 learned to slice the payload the
# client's way). If this run reports fewer, a section stopped executing -- most
# likely the section 2 field walk hitting an unhandled type and breaking out
# early, which drops the offset checks that are the whole reason this file
# exists.
LEDGER = checks.Ledger("spawn burst", floor=48)
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

    print("\n4. 0x0037 carries the LIVE point balance, not a constant")
    # THE CONSTANT IS GONE and this section is what replaced it. Until
    # 2026-08-20 authsrv held ATTRIBUTE_POINTS = 0 and sent it in BOTH fields,
    # and this file checked that constant. The number is per-character state
    # now -- attribspend.AttributeState computes it from the ranks and the
    # client's own cost curve, so it moves when the player spends -- and the
    # only honest way to bind the burst is to ask the same object the burst
    # asks. studies/pvpui/FINDINGS.md 32.5 for the field meanings.
    import authsrv
    import agents
    # A bare connection state. No socket and no store: PERSIST is off by
    # default, so persisted_attribute_row returns None and the ranks fall
    # through to content. This is also the DEFAULT spawn -- EQUIP_WEAPON on --
    # which is what puts the hammer's bonus in section 5's third column.
    st = authsrv.attribute_state({})

    check(not hasattr(authsrv, "ATTRIBUTE_POINTS"),
          "there is no ATTRIBUTE_POINTS constant to send twice -- the "
          "supersession is a tripwire, because reintroducing one is exactly "
          "how both fields become the same number again")
    check(sorted(st.ranks.items()) == sorted(agents.PLAYER_ATTRIBUTE_RANKS),
          f"with no store the state seeds from the CONTENT row "
          f"({sorted(st.ranks.items())}), so the numbers below are the "
          f"content's rather than a second source's")
    check(st.points_total == 200,
          f"points_total is the lifetime budget ({st.points_total}) -- the "
          f"level-20 maximum, which 0x0037's field 4 reads in 34 of the "
          f"corpus's 48 sightings")
    # Priced from the cost table rather than typed in: the cumulative sum of
    # s_attribPoints[1..rank] for each rank held. No free parameter -- the
    # curve is the client's own (clientscan/attribpoints.py -> attribute_cost).
    want_spent = sum(sum(st.rules.costs[r] for r in range(1, rank + 1))
                     for rank in st.ranks.values())
    check(st.spent == want_spent == 173,
          f"the five ranks price out at {st.spent} on the client's cost curve "
          f"(97+48+21+6+1)")
    check(st.available == st.points_total - st.spent == 27,
          f"and the balance closes: {st.available} unspent")
    check(st.available >= 0,
          f"the content row's ranks are AFFORDABLE -- {st.spent} of "
          f"{st.points_total}. A negative balance is a spread no character "
          f"could hold, and until the spend model existed this server had no "
          f"way to ask (content/world.toml said so itself)")
    check(st.available != st.points_total,
          f"the two fields are DIFFERENT numbers ({st.available} and "
          f"{st.points_total}) -- one value in both slots told the client "
          f"every point was unspent while handing it ranks that had cost some")
    # The field ORDER, CONTESTED until 2026-08-19 (used/max or max/used).
    # field3 <= field4 holds in 48 of 48 sightings and a swap breaks it on the
    # first [1, 5]; ours is [27, 200], so a swap is visible here too.
    check(st.available <= st.points_total,
          f"field 3 ({st.available}) <= field 4 ({st.points_total}), the "
          f"48-of-48 corpus invariant")
    check(not st.points_total <= st.available,
          f"CONTROL: the swapped order puts {st.points_total} in field 3 "
          f"against {st.available} in field 4 and breaks that invariant -- so "
          f"the check above discriminates ORDER, which it could not do while "
          f"one constant filled both fields and the two were equal")
    # By OPCODE, not by position: the burst's order is exactly the kind of
    # thing that changes, and a positional index would then compare against
    # whatever moved into the slot instead of failing honestly.
    row = next(v for op, v, _ in BURST if op == 0x0037)
    check(row[1:] == [st.available, st.points_total],
          f"the hand-copied burst row carries the module's own "
          f"(available, points_total) = {row[1:]}")

    print("\n5. 0x003A is COLUMN-MAJOR, and refuses what the client would")
    # THE BURST'S OWN CALL, not attribute_columns()'s convenience default.
    # This section read the no-arg form until 2026-08-21 and was green while
    # the server sent something else: the burst passes the LIVE ranks and the
    # equipped BONUSES, and the bonus is the only thing that makes column 3
    # differ from column 2. A binding that calls a different overload than the
    # caller under test binds nothing -- which is how the +1 below went
    # unmeasured here for a day.
    _ranks = sorted(st.ranks.items())
    payload = authsrv.attribute_columns(_ranks, st.bonuses)
    want_ids = [a for a, _ in _ranks]
    want_ranks = [r for _, r in _ranks]
    want_effective = [st.effective_of(a) for a, _ in _ranks]
    want = want_ids + want_ranks + want_effective
    row = next(v for op, v, _ in BURST if op == 0x003A)
    check(payload == want and payload == row[1],
          "the emitted payload is the live state's ranks, column-major",
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
    # Column 3 is EFFECTIVE rank: base plus equipped bonuses. It is
    # deliberately NOT bound-checked against ATTRIBUTE_RANK_MAX -- retail sent
    # effective 13 against a spend cap of 12 in 26 of 26 sightings, so the cap
    # belongs to column 2 alone and a check here would refuse what ArenaNet's
    # own server sends.
    gaps = [t - r for t, r in zip(third, ranks)]
    check(third == want_effective and all(g in (0, 1) for g in gaps),
          f"column 3 is base PLUS the equipped bonus ({third}), every gap 0 "
          f"or +1 -- the shape retail held across 94 (attribute, sighting) "
          f"pairs")
    check(any(g == 1 for g in gaps),
          f"and at least one gap IS +1 ({gaps}) -- the starter hammer's "
          f"Hammer Mastery, drawn by the client as 7 over a base of 6 "
          f"(capture 20260820T113942). This is the check that discriminates "
          f"the burst's call from the no-arg one: with the columns equal, the "
          f"two are indistinguishable and this section measured neither",
          f"bonuses={st.bonuses}")
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
    fatal = [x for a, r in _ranks for x in (a, r, r)]
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
