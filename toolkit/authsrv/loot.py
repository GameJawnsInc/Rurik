"""Ground drops and the pickup -- RANGERPRE-S15 (LOOT slice 1: a gold drop).

THE VALUES ONLY, like `purse.py` and `killxp.py`. Nothing here sends a message
or reads a connection: the sends are `authsrv.loot_on_kill` (the kill frame),
`authsrv.serve_pickup` (the arrival frame) and `authsrv.ground_items_tick` (the
view range); the drop TABLES are content (`content/drops.toml`, every row
INVENTED and labelled so); the gold RECORD is content too (`[item.gold_coins]`,
a capture row). Standard library only, no import of the server, so
`test_loot.py` drives every function here with no vault and no socket.

WHAT RETAIL SENDS (capture 20260929T150923, build 38888; decoded by byte
offset inside each TCP segment, never by a sort):

  * THE KILL FRAME, OBSERVED 4 of 4 drops. A gold drop rides the death's own
    segment between the dying body's 0x00F1 status word and the kill's reward
    block: 0x0162 [item, 97552, 20, 0,0,0,0, 0x20080001, n, 2511, n, name, []]
    declares the gold, 0x0168 [ground agent, dying agent] names its source,
    and 0x0020 creates the ground agent -- field 3 = 4, kind 0, speed 0.0,
    field 11 = 0x34000000, token 0 (:55934 383.5733 at plaintext offsets
    29823 / 29833 / 29877 / 29889, then 0x009C at 29988; :55934 429.2836;
    :53756 1107.8834). Re-encoded with retail's ids, ours is byte-identical
    (test_loot section 6).
  * THE PICKUP, OBSERVED 3 of 3: c2s 0x00C1 + 0x003F [ground agent, 0] in one
    segment, answered by a STRAIGHT 0x002A [player, (the item's own point),
    plane, plane, ground agent] (:55934 392.5485, :53756 1124.0474), no client
    report during the walk, and the arrival frame about the straight-line
    walk time later (+2.998 s and +1.517 s after the 0x002A).
  * THE ARRIVAL, OBSERVED 2 of 2 gold: 0x009F [8, me, 1], 0x009F [39, me, 0],
    0x0159 [item, me], 0x0140 [key, n], 0x005D (the gold line), 0x005E
    [1, 10], 0x0028 [me], 0x0021 [ground agent] (:55934 395.546, :53756
    1125.5645); the hold's release 0x009F [8, me, 0] 0.981-1.000 s later
    (6 of 6 across the corpus).
  * UNPICKED DROPS LEAVE BY VIEW RANGE, OBSERVED: 11 of 11 removals of an
    unpicked ground item on the three connections are a bare 0x0021 with the
    player about 5,000 u from the item or further (the next player position on
    the wire after each -- a report, or 2 of 11 a server move point -- reads
    5,012-6,147 u; one removal, :53756 1142.6357, came 14 ms after a report at
    4,993 u), and a re-entry is a bare 0x0020 re-create
    (4 of 4: :53756 1128.6181, 1148.0107, 1150.1861; :55934 642.2125), every
    create at 4,960 u or nearer. No despawn timer is on any tape (UNVERIFIED
    either way). The distances are a census of 2026-09-30 against the player's
    own reports and move orders on those connections (not committed); the
    bare shape of both -- 11 removals, 4 re-creates -- is test_loot's 6i.

WHAT IS OURS, and says so: the drop TABLES (INVENTED, content), the scatter
distance and the agent-id range (RECONSTRUCTION, below), the reach at which a
walk counts as arrived (RECONSTRUCTION), the 5,000 u view radius as one number
with no hysteresis (RECONSTRUCTION on the census above).
"""
import math
import struct

# 0x0020 on a GROUND ITEM, field by field against retail's four kill drops and
# every other kind-4 create on the tape (15 of 15): field 3 is 4 where a living
# body carries 1 (agents.AGENT_TYPE_LIVING), the kind byte is 0 (agents.py:
# "0 item, 5 player, 9 NPC"), the speed 0.0, field 11 0x34000000 where a body
# carries 0x41400000, and the allegiance token 0 ("0000 216 every kind-0 item",
# agents.py's token census).
AGENT_DEF_ITEM = 4
AGENT_KIND_ITEM = 0
ITEM_AGENT_WORD = 0x34000000
ITEM_TYPE_GOLD = 20
INF = float("inf")

# 0x009F [8, me, 0] 0.981-1.000 s after every arrival frame, 6 of 6 across four
# captures: the pickup's own action hold. OBSERVED.
PICKUP_HOLD_SECONDS = 1.0
# How close the server's copy of the body must stand to the item for a walk that
# ended some other way than our own eta to count as arrived. Retail's one report
# after an arrival put the body 1.6 u from the item (:55934 396.8). RECONSTRUCTION.
PICKUP_REACH = 2.0
# How far from the corpse a drop falls. Retail's gold fell 26.4 u from a
# never-moved foe and 28 / 35 u from the others' last destinations (n = 3).
# RECONSTRUCTION: one radius, a uniform angle.
DROP_SCATTER = 30.0
# The ground-item view radius (the census above). RECONSTRUCTION as a single
# number with no hysteresis: the creates sit inside it and the removals at or
# past it, and the client's reports are too sparse to place the edge closer than
# a few tens of units.
DROP_VIEW_RANGE = 5000.0
# Ground agents are OURS to number. Clear of the player (1), the test enemy (10+),
# the henchman (30), area rows (<= 99), the sandbox (110+) and the heroes
# (200..206). RECONSTRUCTION: retail's own ground agents on this tape run 17..184.
DROP_AGENT_ID_BASE = 400


class LootError(ValueError):
    """A drop table that does not load. Refused at startup, never mid-kill."""


def f32_bits(x):
    """The u32 a float travels as (0x0135's reservation, a 0x0020 float field)."""
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


def ground_item_create(agent_id, item_id, x, y, plane):
    """GAME_SMSG 0x0020 for a ground item -- agents.create_agent's 23 fields with
    the four a ground item carries differently (AGENT_DEF_ITEM, the item kind,
    speed 0.0, ITEM_AGENT_WORD) and token 0. Retail's :55934 383.5733 create is
    this list with (57, 472, -113.0234375, 1611.6650390625, 0), byte for byte."""
    return [int(agent_id), int(item_id), AGENT_DEF_ITEM, AGENT_KIND_ITEM,
            (float(x), float(y)), int(plane), (1.0, 0.0), 1,
            0.0, 1.0, ITEM_AGENT_WORD, 0,
            0, 0, 0, 0, 0, (0.0, 0.0), (INF, INF), 0, 0, (INF, INF), 0]


def drop_source(agent_id, source_id):
    """GAME_SMSG 0x0168 [ground agent, the body it fell from] -- 4 of 4 kill
    drops name the dying agent (the schema's ITEM_AGENT_DROP_SOURCE)."""
    return [int(agent_id), int(source_id)]


def picked_up(item_id, picker):
    """GAME_SMSG 0x0159 [item, the agent that picked it up] (ITEM_PICKED_UP)."""
    return [int(item_id), int(picker)]


def gold_record(row, amount):
    """The gold content row for one drop: value AND quantity are the amount,
    9 of 9 corpus 0x0162s (and the pickup's 0x0140 equals it, 2 of 2)."""
    n = int(amount)
    if n < 1:
        raise LootError(f"a gold drop of {amount!r}: retail's smallest is 2")
    return dict(row, value=n, quantity=n)


def validate_table(key, row):
    """Refuse a drop table this slice cannot serve. -> the row, unchanged.

    `chance` in [0, 1]; `gold` = [lo, hi] with 1 <= lo <= hi. An `items` list is
    refused until LOOT slice 2 (the item drop) lands -- a table naming an item
    this server would silently never drop is a promise nobody keeps."""
    where = f"drop table {key!r}"
    try:
        chance = float(row.get("chance"))
    except (TypeError, ValueError):
        raise LootError(f"{where}: `chance` must be a number in [0, 1], "
                        f"got {row.get('chance')!r}") from None
    if not 0.0 <= chance <= 1.0:
        raise LootError(f"{where}: chance {chance} is outside [0, 1]")
    if row.get("items"):
        raise LootError(f"{where}: `items` is LOOT slice 2 (the item drop), which "
                        f"this server does not serve yet -- gold only")
    gold = row.get("gold")
    if not (isinstance(gold, (list, tuple)) and len(gold) == 2
            and all(isinstance(g, int) and not isinstance(g, bool) for g in gold)):
        raise LootError(f"{where}: `gold` must be [lo, hi], two integers; "
                        f"got {gold!r}")
    lo, hi = gold
    if not 1 <= lo <= hi:
        raise LootError(f"{where}: gold [{lo}, {hi}] needs 1 <= lo <= hi")
    return row


def roll(row, rng):
    """None, or ("gold", n) -- one draw on a validated table. `rng` is anything
    with random() and randint() (the random module, or a test's stub)."""
    if rng.random() >= float(row["chance"]):
        return None
    lo, hi = row["gold"]
    return ("gold", int(rng.randint(int(lo), int(hi))))


def scatter(x, y, rng):
    """A point DROP_SCATTER from (x, y) at a uniform angle. `rng.uniform`."""
    a = rng.uniform(0.0, 2.0 * math.pi)
    return (float(x) + DROP_SCATTER * math.cos(a),
            float(y) + DROP_SCATTER * math.sin(a))


def mint_item_id(state, base):
    """A fresh item id off the MERCHANT's counter (`next_purchased_item`, from
    `base` = merchant.PURCHASED_ITEM_ID_BASE), so a bought item and a dropped
    one can never share an id -- a second declaration under a live id would
    silently rewrite the first."""
    new_id = int(state.get("next_purchased_item", base))
    state["next_purchased_item"] = new_id + 1
    return new_id


def next_drop_agent(taken):
    """The lowest ground-agent id at or above DROP_AGENT_ID_BASE not in `taken`."""
    aid = DROP_AGENT_ID_BASE
    while aid in taken:
        aid += 1
    return aid


def in_view(player_pos, item_pos):
    """Is the item inside the view radius of the player? (the census above)"""
    return math.hypot(float(item_pos[0]) - float(player_pos[0]),
                      float(item_pos[1]) - float(player_pos[1])) <= DROP_VIEW_RANGE
