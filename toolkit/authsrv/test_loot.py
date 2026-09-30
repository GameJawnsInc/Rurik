"""test_loot -- a kill's gold drop, the pickup walk and its arrival, the purse credit,
and the view range (RANGERPRE-S15, LOOT slice 1, 2026-09-30).

    python toolkit/authsrv/test_loot.py

WHAT RETAIL SENDS (capture 20260929T150923, build 38888; section 6 re-reads every literal
below from the bytes, by byte offset inside each TCP segment):

  * the kill frame, 4 of 4 drops: 0x00F1 status, then 0x0162 (the gold declare), 0x0168
    [ground agent, dying agent], the ground agent's 0x0020 (field 3 = 4, kind 0, speed
    0.0, field 11 0x34000000, token 0), THEN the reward block (0x009C, 0x00EE ...) and the
    0x0026 flags last (:55934 383.5733, offsets 29823 .. 30032);
  * the pickup: c2s 0x00C1 + 0x003F [ground agent, 0] (3 of 3), a straight 0x002A [me,
    the item's own point, 0, 0, ground agent] ~40 ms later, and the arrival frame 0x009F
    [8, me, 1], 0x009F [39, me, 0], 0x0159 [item, me], 0x0140 [key, n], 0x005D (the gold
    line), 0x005E [1, 10], 0x0028 [me], 0x0021 [ground agent] (:55934 395.546, :53756
    1125.5645), the hold released 0x009F [8, me, 0] ~1.0 s later;
  * an unpicked drop leaves by a bare 0x0021 and comes back by a bare 0x0020 (view range).

Ours sent none of it: no kill dropped, and 0x003F was test_dispatch's DROPPED_ON_PURPOSE.

SECTIONS. 1 the leaf and the builders against retail's literals (bare); 2 OUR kill_agent
under --drop-table, the known-bad arm (--no-drops) and the default (no table: the pre-S15
frame); 3 the pickup through handle_pickup / pickup_tick / serve_pickup; 4 the view range;
5 the source (the drop's slot in kill_agent AHEAD of the morale tick -- the critic's C1 --
the world tick, the dispatch arm, the flags); 6 THE TAPE, which skips ONLY when the
capture's directory is absent: ours re-encoded with retail's ids must be byte-identical
to the plaintext, and a sabotaged tape must fail the same comparator; 7 the pickup beside a
standing NPC (RANGERLOOP-F8): the real AgTrack guard and avoidance pass at Run A's and Run
A''s coordinates -- the halt must not cancel the pickup, the known-bad arm must, and 1z-dj's
park must still take everything that is not a pickup walk; 8 the revive's life-state byte
(RANGERLOOP-F10): 0x0026 [agent, 9] behind the status, the byte whose absence left section
7's revived Hatcher non-colliding in the client. Sections 1-5, 7 and 8 need no vault, no
socket and no client.
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import chatdefs                                                # noqa: E402
import content                                                 # noqa: E402
import loot                                                    # noqa: E402
import merchant                                                # noqa: E402
import vaultpath                                               # noqa: E402
from codec import Codec                                        # noqa: E402  (authsrv put schema/ on the path)

# Floor 35, from the green run of 2026-09-30 with RURIK_VAULT at an EMPTY directory
# (section 6 a declared skip). Section 6 adds 9 when the capture is present (44).
# The review round adds two fixture-free checks (3j, 3k: the pickup/world-tick race),
# so both move by 2, each read off a real green run: 37 bare (1 declared skip), 46
# with the capture. Section 7 (RANGERLOOP-F8, fixture-free) adds 8: 45 bare, 54 with
# the capture, both from the green runs of 2026-09-30. Section 8 (RANGERLOOP-F10, the
# revive's life-state byte, fixture-free) adds 4: 49 bare, 58 with the capture.
LEDGER = checks.Ledger("drops and pickups (LOOT)", floor=49)
check = checks.adopt(LEDGER)

STAMP = "20260929T150923"
PLAYER = authsrv.PLAYER_AGENT_ID
KEY = authsrv.PLAYER_INVENTORY_KEY
INF = float("inf")
OP_STATUS, OP_DECLARE, OP_SOURCE, OP_CREATE = 0x00F1, 0x0162, 0x0168, 0x0020
OP_TICK, OP_REWARD, OP_FLAGS = 0x009C, 0x00EE, 0x0026
OP_WALK, OP_INT, OP_PICKED, OP_GOLD = 0x002A, 0x009F, 0x0159, 0x0140
OP_CORE, OP_SERVER, OP_HALT, OP_REMOVE = 0x005D, 0x005E, 0x0028, 0x0021

# Retail's literals (section 6 reads each from the bytes; these are the values it finds).
GOLD_NAME = "".join(chr(w) for w in (0x2520, 0xA92A, 0xCDF4, 0x3A6A))
RETAIL_DECLARE = [472, 97552, 20, 0, 0, 0, 0, 0x20080001, 6, 2511, 6, GOLD_NAME, []]
RETAIL_POINT = (-113.0234375, 1611.6650390625)
RETAIL_CREATE = [57, 472, 4, 0, RETAIL_POINT, 0, (1.0, 0.0), 1, 0.0, 1.0, 0x34000000, 0,
                 0, 0, 0, 0, 0, (0.0, 0.0), (INF, INF), 0, 0, (INF, INF), 0]
RETAIL_LINE = {6: [0x07DF, 0xC868, 0xCA88, 0x54A4, 0x010A, 0x0AC2, 0x0101, 0x0106, 0x0001],
               7: [0x07DF, 0xC868, 0xCA88, 0x54A4, 0x010A, 0x0AC2, 0x0101, 0x0107, 0x0001]}


def norm(v):
    """Tuples and lists compare alike (the codec decodes a vec2 as a list)."""
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    return v


def words(s):
    return [ord(c) for c in s]


class Stub:
    """An rng for loot.roll / loot.scatter: fixed draws."""

    def __init__(self, r=0.0, angle=0.0):
        self.r, self.angle = r, angle

    def random(self):
        return self.r

    def randint(self, lo, hi):
        return lo

    def uniform(self, a, b):
        return self.angle


class Flags:
    """Set authsrv's two loot globals for a block, and put them back."""

    def __init__(self, table, enabled=True):
        self.want = (table, enabled)

    def __enter__(self):
        self.saved = (authsrv.DROP_TABLE, authsrv.LOOT_ENABLED)
        authsrv.DROP_TABLE, authsrv.LOOT_ENABLED = self.want

    def __exit__(self, *exc):
        authsrv.DROP_TABLE, authsrv.LOOT_ENABLED = self.saved
        return False


def collect():
    sent = []
    return sent, (lambda op, v, label="", quiet=False: sent.append((op, list(v))))


def ops(sent):
    return [op for op, _v in sent]


def foe_entry(pos=(100.0, 0.0)):
    npc = dict(agents.HATCHER)
    npc["level"] = 1
    return {"name": "t", "dead": False, "npc": npc, "pos": pos, "plane": 0,
            "health": 1.0, "max_health": 10.0}


def fresh(**kw):
    # xp_since_load 74: the kill's award crosses 75, so the frame carries the tick
    # (0x009C) the drop must precede.
    st = {"level": 1, "map_id": 146, "pos": (0.0, 0.0), "plane": 0, "xp_since_load": 74}
    st.update(kw)
    return st


def kill(st, foe, table, enabled=True, reward=True, scatter_to=None):
    """kill_agent on `foe` as agent 10 under the given loot flags; the sends."""
    sent, send = collect()
    st.setdefault("agents", {})[10] = foe
    saved = loot.scatter
    if scatter_to is not None:
        loot.scatter = lambda x, y, rng: scatter_to
    try:
        with Flags(table, enabled):
            authsrv.kill_agent(send, st, 10, foe, 0, 0.0, reward=reward)
    finally:
        loot.scatter = saved
    return sent


def first(sent, op):
    """The values of the first `op` in `sent`, or None -- so a missing message is a
    FAIL naming it, never a StopIteration that takes the rest of the run down."""
    return next((v for o, v in sent if o == op), None)


def place_drop(st, pos=(500.0, 0.0)):
    """A 6-gold ground item at exactly `pos`, put down by loot_on_kill itself (the
    probe row, the scatter stubbed) -- sections 3 and 4 need a drop to exist, and
    kill_agent's call of it is section 2's subject, not theirs. -> the ground agent."""
    saved = loot.scatter
    loot.scatter = lambda x, y, rng: pos
    try:
        with Flags("probe_gold"):
            return authsrv.loot_on_kill(lambda op, v, label="": None, st, 10,
                                        foe_entry((pos[0] - 30.0, pos[1])), 0)
    finally:
        loot.scatter = saved


def drop_order(seq):
    """Retail's kill-frame predicate over an opcode list: the status word, then the
    declare / source / create trio contiguous, then the tick, the reward and the flags
    last -- True only if all of them are there in that order."""
    try:
        i_st = seq.index(OP_STATUS)
        i_dec = seq.index(OP_DECLARE)
        i_tick = seq.index(OP_TICK)
        i_rew = seq.index(OP_REWARD)
        i_fl = len(seq) - 1 - seq[::-1].index(OP_FLAGS)
    except ValueError:
        return False
    return (i_st < i_dec and seq[i_dec:i_dec + 3] == [OP_DECLARE, OP_SOURCE, OP_CREATE]
            and i_dec + 3 <= i_tick < i_rew < i_fl)


def arrival_list(item, drop, n, me=PLAYER, key=KEY):
    """Retail's arrival frame for a gold pickup, as (op, values)."""
    return [(OP_INT, [8, me, 1]), (OP_INT, [agents.GV_PICKUP, me, 0]),
            (OP_PICKED, [item, me]), (OP_GOLD, [key, n]),
            (OP_CORE, [chatdefs.gold_pickup_body(n)]),
            (OP_SERVER, [authsrv.PLAYER_NUMBER, chatdefs.CHANNEL_NOTIFY]),
            (OP_HALT, [me]), (OP_REMOVE, [drop])]


# --------------------------------------------------------------------------- 1
def section_leaf(codec):
    print("\n1. the leaf and the builders, against retail's literals")
    check(norm(loot.ground_item_create(57, 472, *RETAIL_POINT, 0)) == norm(RETAIL_CREATE),
          "1a. ground_item_create(57, 472, retail's point, 0) is retail's 0x0020 field for "
          "field -- 4, kind 0, speed 0.0, 0x34000000, token 0")
    gold = loot.gold_record(agents.item_template("gold_coins"), 6)
    check(norm(agents.named_item(472, gold)) == norm(RETAIL_DECLARE),
          "1b. named_item(472, the gold row at 6) is retail's 0x0162: file 97552, type 20, "
          "flags 0x20080001, value 6, model 2511, quantity 6, the name ids, no modifiers")
    check(words(chatdefs.gold_pickup_body(6)) == RETAIL_LINE[6]
          and words(chatdefs.gold_pickup_body(7)) == RETAIL_LINE[7],
          "1c. the gold pickup line for 6 and 7 is retail's words (the amount word 0x0106 / "
          "0x0107 before the terminator)")
    sizes = (len(codec.encode("GAME_SMSG", OP_DECLARE, agents.named_item(472, gold))),
             len(codec.encode("GAME_SMSG", OP_SOURCE, loot.drop_source(57, 46))),
             len(codec.encode("GAME_SMSG", OP_CREATE,
                              loot.ground_item_create(57, 472, *RETAIL_POINT, 0))))
    check(sizes == (44, 6, 99),
          "1d. encoded, the three are 44, 6 and 99 bytes -- retail's widths", f"{sizes}")
    living = agents.create_agent(57, 472, 0, *RETAIL_POINT, 0)
    diff = [i for i, (a, b) in enumerate(zip(norm(living), norm(RETAIL_CREATE))) if a != b]
    check(norm(living) != norm(RETAIL_CREATE) and diff == [2, 8, 10, 11],
          "1e. KNOWN-BAD: the living body's builder (create_agent) is NOT a ground item -- "
          "it differs from retail's in fields 2, 8, 10 and 11 (type, speed, word, token), "
          "so the comparator in 1a can fail", f"differs at {diff}")
    rows = content.load(vault_dir="").rows("drop")
    good = all(loot.validate_table(k, r) is r for k, r in rows.items())
    bad = [{"chance": 1.5, "gold": [2, 7]}, {"chance": "x", "gold": [2, 7]},
           {"chance": 0.5, "gold": [0, 3]}, {"chance": 0.5, "gold": [5, 2]},
           {"chance": 0.5, "gold": [1]}, {"chance": 0.5, "gold": [2, 7],
                                          "items": [["starter_sword", 1]]},
           {"chance": 0.5}]
    refused = 0
    for r in bad:
        try:
            loot.validate_table("t", r)
        except loot.LootError:
            refused += 1
    check(good and len(rows) == 2 and refused == len(bad),
          "1f. both tracked tables validate; a chance outside [0, 1] or not a number, a "
          "gold range with lo < 1, lo > hi or not two ints, a slice-2 `items` list and a "
          "table with no gold are each REFUSED", f"{sorted(rows)}, {refused}/{len(bad)}")
    prob = {"chance": 0.33, "gold": [2, 7]}
    check(loot.roll(prob, Stub(r=0.5)) is None and loot.roll(prob, Stub(r=0.1)) == ("gold", 2)
          and loot.roll({"chance": 0.0, "gold": [1, 1]}, Stub(r=0.0)) is None
          and loot.roll({"chance": 1.0, "gold": [6, 6]}, Stub(r=0.999)) == ("gold", 6),
          "1g. roll: a draw at or past the chance drops nothing, one under it drops "
          "randint(lo, hi); chance 0 never drops, chance 1 always does")
    dists = [math.hypot(*(a - b for a, b in zip(loot.scatter(10.0, -4.0, Stub(angle=t)),
                                                 (10.0, -4.0))))
             for t in (0.0, 1.0, 2.5, 4.0, 6.0)]
    check(all(abs(d - loot.DROP_SCATTER) < 1e-9 for d in dists),
          f"1h. scatter lands DROP_SCATTER ({loot.DROP_SCATTER:.0f} u) from the corpse at "
          f"any angle", f"{[round(d, 6) for d in dists]}")
    st = {}
    a = loot.mint_item_id(st, merchant.PURCHASED_ITEM_ID_BASE)
    st2 = {"next_purchased_item": 5003}
    b = loot.mint_item_id(st2, merchant.PURCHASED_ITEM_ID_BASE)
    check(a == merchant.PURCHASED_ITEM_ID_BASE and st["next_purchased_item"] == a + 1
          and b == 5003 and st2["next_purchased_item"] == 5004
          and loot.next_drop_agent({400, 401, 403}) == 402
          and loot.next_drop_agent(set()) == loot.DROP_AGENT_ID_BASE,
          "1i. a dropped item's id comes off the MERCHANT's counter (a bought item and a "
          "drop never share one), and a ground agent is the lowest free id from 400")
    check(loot.in_view((0.0, 0.0), (4999.0, 0.0)) and loot.in_view((0.0, 0.0), (0.0, 5000.0))
          and not loot.in_view((0.0, 0.0), (3600.0, 3600.0)),
          "1j. the view radius: 4999 and 5000 u in view, 5091 u out")
    w = content.load(vault_dir="")
    gp = w.get("item", "gold_coins").provenance
    check(gp.get("source") == "capture" and gp.get("capture") == STAMP
          and gp.get("origin") == "live"
          and all(r.provenance.get("source") == "invented" for r in w.rows("drop").values()),
          "1k. the tracked content: [item.gold_coins] is a capture row (20260929T150923, "
          "live); EVERY drop table is source 'invented'")


# --------------------------------------------------------------------------- 2
def section_kill():
    print("\n2. OUR kill frame under --drop-table, the known-bad arm, the default")
    st = fresh()
    sent = kill(st, foe_entry(), "probe_gold")
    seq = ops(sent)
    check(drop_order(seq) and seq[0] == OP_STATUS and seq[1:4] == [OP_DECLARE, OP_SOURCE,
                                                                   OP_CREATE],
          "2a. HEADLINE: the drop is in the death's own frame, right behind the status word "
          "and AHEAD of the 75-XP tick, the reward and the flags -- retail's 383.5733 order",
          f"{[hex(o) for o in seq]}")
    dec, src, cre = first(sent, OP_DECLARE), first(sent, OP_SOURCE), first(sent, OP_CREATE)
    ok = None not in (dec, src, cre)
    g = (st.get("ground_items") or {}).get(src[0]) if ok else None
    d = math.hypot(cre[4][0] - 100.0, cre[4][1] - 0.0) if ok else -1.0
    check(ok and src == [cre[0], 10] and cre[1] == dec[0] and cre[2] == 4 and cre[3] == 0
          and cre[8] == 0.0 and cre[10] == 0x34000000 and cre[11] == 0
          and dec[8] == dec[10] == 6 and abs(d - loot.DROP_SCATTER) < 1e-6
          and g is not None and g["gold"] == 6 and g["item"] == dec[0] and g["shown"]
          and cre[0] >= loot.DROP_AGENT_ID_BASE and dec[0] >= merchant.PURCHASED_ITEM_ID_BASE,
          "2b. 0x0168 names [the ground agent, the dying agent]; the ground agent's 0x0020 "
          "carries the declared item, 4 / 0 / speed 0 / 0x34000000 / token 0; 6 gold (the "
          "probe row); 30 u from the corpse; the server holds it as a ground item",
          f"dec {dec}, src {src}, create {cre[:4] if cre else None}, {d:.3f} u, {g}")
    sent2 = kill(st, foe_entry(), "probe_gold")
    dec2, src2 = first(sent2, OP_DECLARE), first(sent2, OP_SOURCE)
    check(ok and None not in (dec2, src2) and dec2[0] == dec[0] + 1
          and src2[0] == src[0] + 1 and len(st.get("ground_items") or {}) == 2,
          "2c. a second kill mints a fresh item id and a fresh ground agent")
    base = kill(fresh(), foe_entry(), None)
    bad = kill(fresh(), foe_entry(), "probe_gold", enabled=False)
    check(ops(base) == [OP_STATUS, OP_TICK, OP_REWARD, OP_REWARD, OP_FLAGS]
          and bad == base and not drop_order(ops(bad)),
          "2d. the DEFAULT (no --drop-table) is the pre-S15 frame, status / tick / reward / "
          "flags; and the KNOWN-BAD arm (--no-drops under --drop-table) sends that same "
          "frame -- no 0x0162, no 0x0168, no ground agent -- which retail's 383.5733 refutes",
          f"{[hex(o) for o in ops(base)]}")
    party = kill(fresh(), foe_entry(), "probe_gold", reward=False)
    check(not any(op in (OP_DECLARE, OP_SOURCE) for op in ops(party)),
          "2e. a PARTY body's death (reward=False) never drops, under any table")
    st3, sent3 = fresh(), []
    with Flags("presearing_gold"):
        miss = authsrv.loot_on_kill(lambda op, v, label="": sent3.append(op), st3, 10,
                                    foe_entry(), 0, rng=Stub(r=0.5))
        hit = authsrv.loot_on_kill(lambda op, v, label="": sent3.append(op), st3, 10,
                                   foe_entry(), 0, rng=Stub(r=0.1))
    check(miss is None and hit is not None and sent3 == [OP_DECLARE, OP_SOURCE, OP_CREATE]
          and (st3.get("ground_items") or {}).get(hit, {}).get("gold") == 2,
          "2f. the INVENTED 0.33 table: a draw past the chance drops nothing and sends "
          "nothing; one under it drops randint's low end (2 gold)")

    class NoGround:
        def walkable(self, x, y):
            return False

    class RightOnly:
        def walkable(self, x, y):
            return x >= 125.0

    st4 = fresh(pathmap=NoGround())
    s4 = kill(st4, foe_entry(), "probe_gold", scatter_to=(90.0, 0.0))
    c4 = first(s4, OP_CREATE)
    st5 = fresh(pathmap=RightOnly())
    s5 = kill(st5, foe_entry(), "probe_gold", scatter_to=(120.0, 0.0))
    c5 = first(s5, OP_CREATE)
    check(None not in (c4, c5) and tuple(c4[4]) == (100.0, 0.0) and c5[4][0] >= 125.0,
          "2g. the scatter point is moved onto the navmesh (place_on_mesh), and where "
          "nothing near is ground the drop lies on the corpse's own point",
          f"{c4 and c4[4]} {c5 and c5[4]}")


# --------------------------------------------------------------------------- 3
def section_pickup():
    print("\n3. the pickup: the walk, the arrival frame, the hold, the refusals")

    ground = place_drop
    st = fresh()
    drop = ground(st)
    item = st["ground_items"][drop]["item"]
    sent, send = collect()
    t0 = time.time()
    authsrv.handle_pickup([0x803F, drop, 0], send, st, 0)
    pk = st.get("pickup") or {}
    check(sent == [(OP_WALK, [PLAYER, (500.0, 0.0), 0, 0, drop])]
          and st.get("approach") is None and pk.get("agent") == drop
          and st.get("dest") == (500.0, 0.0)
          and abs((pk.get("eta", 0) - t0) - 500.0 / authsrv.DEFAULT_RUN_SPEED) < 0.05,
          "3a. 0x003F answers with ONE message, retail's straight 0x002A [me, the item's "
          "own point, 0, 0, the ground agent]; the walk is the pickup's (state['pickup']), "
          "not an approach, and it ends AT the item at run speed",
          f"{sent} pickup {pk} dest {st.get('dest')}")
    sent, send = collect()
    authsrv.attack_tick(send, st, 0)
    check(st.get("pickup") is not None and st.get("dest") == (500.0, 0.0),
          "3b. attack_tick with no target leaves the pickup's walk alone (an approach "
          "record would have been abandoned and its dest cleared)",
          f"{st.get('pickup')} {st.get('dest')}")
    sent, send = collect()
    authsrv.pickup_tick(send, st, 0, now=pk["eta"] - 0.05)
    check(sent == [] and st.get("pickup") is not None,
          "3c. before the leg's eta the tick sends nothing and keeps the pickup")
    sent, send = collect()
    authsrv.pickup_tick(send, st, 0, now=pk["eta"] + 0.001)
    check(sent == arrival_list(item, drop, 6)
          and st.get("purse") == 6 and drop not in st["ground_items"]
          and st.get("pickup") is None and st.get("pos") == (500.0, 0.0)
          and st.get("dest") is None,
          "3d. at the eta: EXACTLY retail's arrival frame -- [8, me, 1], [39, me, 0], "
          "0x0159 [item, me], 0x0140 [key, 6], the gold line, 0x005E [1, 10], 0x0028 [me], "
          "0x0021 [ground agent] -- the purse 0 -> 6, the item gone, the body at it",
          f"{[(hex(o), v) for o, v in sent]}")
    swapped = arrival_list(item, drop, 6)
    swapped[2], swapped[3] = swapped[3], swapped[2]
    check(swapped != arrival_list(item, drop, 6) and sent != swapped,
          "3e. MUTANT: the credit ahead of 0x0159 is a different frame -- the swapped "
          "literal differs from retail's (3d's comparator can see the swap) AND the frame "
          "we sent is not the swapped one (so this reads OUR order too, and reddens with "
          "3d when serve_pickup sends 0x0140 first)")
    at = pk["eta"] + 0.001
    s1, send1 = collect()
    authsrv.pickup_tick(send1, st, 0, now=at + 0.99)
    s2, send2 = collect()
    authsrv.pickup_tick(send2, st, 0, now=at + 1.0)
    s3, send3 = collect()
    authsrv.pickup_tick(send3, st, 0, now=at + 2.0)
    check(s1 == [] and s2 == [(OP_INT, [8, PLAYER, 0])] and s3 == [],
          "3f. the hold releases ONCE, 1.0 s after the arrival (retail 0.981-1.000, 6 of 6)")

    st = fresh()
    drop = ground(st)
    sent, send = collect()
    authsrv.handle_pickup([0x803F, drop, 0], send, st, 0)
    s_again, send_again = collect()
    authsrv.handle_pickup([0x803F, drop, 0], send_again, st, 0)
    s_unk, send_unk = collect()
    authsrv.handle_pickup([0x803F, 9999, 0], send_unk, st, 0)
    dead = fresh(player_dead=True)
    d2 = ground(dead)
    s_dead, send_dead = collect()
    authsrv.handle_pickup([0x803F, d2, 0], send_dead, dead, 0)
    check(s_again == [] and s_unk == [] and s_dead == [] and dead.get("pickup") is None,
          "3g. REFUSED with nothing sent: a second press on the item being walked to, an "
          "agent that is no ground item (the pre-S15 answer to every 0x003F), a dead player")
    cancels = []
    for name, spoil in (("a click re-stamps the latch",
                         lambda s: s.__setitem__("click_moving_at", time.time() + 5.0)),
                        ("another destination",
                         lambda s: s.__setitem__("dest", (1.0, 1.0))),
                        ("an attack order",
                         lambda s: s.__setitem__("attacking", 10)),
                        ("a report stops the body short",
                         lambda s: s.__setitem__("dest", None))):
        s = fresh()
        dr = ground(s)
        _x, sd = collect()
        authsrv.handle_pickup([0x803F, dr, 0], sd, s, 0)
        spoil(s)
        out, so = collect()
        authsrv.pickup_tick(so, s, 0, now=s["pickup"]["eta"] + 1.0)
        cancels.append((name, out == [] and s.get("pickup") is None
                        and dr in s["ground_items"]))
    check(all(ok for _n, ok in cancels),
          "3h. CANCELLED with nothing sent, the item left on the ground, when the walk is "
          "replaced: a click, another destination, an attack order, or a stop short of it",
          f"{cancels}")
    s = fresh()
    dr = ground(s)
    _x, sd = collect()
    authsrv.handle_pickup([0x803F, dr, 0], sd, s, 0)
    s["pos"], s["dest"] = (500.0, 0.0), None          # the integrator arrived
    out, so = collect()
    authsrv.pickup_tick(so, s, 0, now=s["pickup"]["eta"] - 0.2)
    near = fresh(pos=(499.0, 0.0))
    dn = ground(near)
    out2, so2 = collect()
    authsrv.handle_pickup([0x803F, dn, 0], so2, near, 0)
    check(ops(out) == [op for op, _v in arrival_list(0, 0, 6)]
          and OP_WALK not in ops(out2) and ops(out2) == [op for op, _v in arrival_list(0, 0, 6)],
          "3i. the other two arrivals: the copy standing on the item with its dest spent "
          "is served before the eta, and a body already within reach is served at the "
          "press with no walk at all")

    # THE REVIEW'S RACE, made deterministic. handle_pickup runs on the CONNECTION
    # thread and attack_tick on the WORLD tick; with no attack target attack_tick
    # abandons any approach on record, dest and all. The first cut published the
    # pickup's leg in state["approach"] and moved it out only after _approach_send
    # returned (past a flushed print, which releases the GIL): a tick landing there
    # left {dest: None} and the next pickup_tick CANCELLED a walk the 0x002A had
    # already started -- 1 of 400 at the tick's cadence, 71 of 400 with a tight
    # tick (the reviewer's probe). Here the tick lands at exactly that instant.
    real_send = authsrv._approach_send

    def raced(send, state, *a, **k):
        out = real_send(send, state, *a, **k)
        authsrv.attack_tick(lambda *x, **y: None, state, 0)   # the world tick, HERE
        return out

    def raced_pickup(seed):
        s = fresh()
        dr = ground(s)
        it = s["ground_items"][dr]["item"]
        seed(s)
        _x, sd = collect()
        authsrv._approach_send = raced
        try:
            authsrv.handle_pickup([0x803F, dr, 0], sd, s, 0)
        finally:
            authsrv._approach_send = real_send
        pk = dict(s.get("pickup") or {})
        out, so = collect()
        served = authsrv.pickup_tick(so, s, 0, now=pk.get("eta", 0.0) + 0.001)
        # SERVED, not the frame's order -- that is 3d's, so a reordered arrival
        # reddens 3d and not these two
        return (pk.get("dest") == (500.0, 0.0) and served is True
                and first(out, OP_PICKED) == [it, PLAYER] and s.get("purse") == 6
                and dr not in s["ground_items"]), pk, [hex(o) for o, _v in out]

    ok, pk, got = raced_pickup(lambda s: None)
    check(ok,
          "3j. RACE: a world tick landing right after the pickup's _approach_send returns "
          "(attack_tick, no attack target) leaves the walk whole -- the pickup keeps dest "
          "= the item's point and is SERVED at its eta (the leg is never published in "
          "state['approach'], so there is nothing for the tick to abandon)",
          f"pickup {pk} arrival {got}")

    def follow_on_record(s):
        # a follow the attack order was still walking when the pickup was pressed,
        # its click latch already spent (so _press_supersedes leaves it alone)
        s["attacking"] = 10
        s["approach"] = {"target": 10, "t0": 1.0, "told": (100.0, 0.0),
                         "sent_at": 1.0, "eta": 2.0}
        s["dest"], s["click_moving_at"] = (80.0, 0.0), None

    ok, pk, got = raced_pickup(follow_on_record)
    check(ok,
          "3k. RACE, with a follow still on record: handle_pickup abandons it BEFORE the "
          "pickup's dest is written, so the same tick cannot take the pickup's dest with "
          "the follow's -- served at the eta, as 3j",
          f"pickup {pk} arrival {got}")


# --------------------------------------------------------------------------- 4
def section_view():
    print("\n4. the view range")
    st = fresh()
    drop = place_drop(st, (1000.0, 0.0))
    g = st["ground_items"][drop]
    st["pos"] = (-4001.0, 0.0)                          # 5001 u away
    out1, s1 = collect()
    authsrv.ground_items_tick(s1, st, 0)
    out2, s2 = collect()
    authsrv.ground_items_tick(s2, st, 0)
    check(out1 == [(OP_REMOVE, [drop])] and out2 == [] and g["shown"] is False,
          "4a. past 5000 u the ground item leaves by ONE bare 0x0021, and stays gone")
    out3, s3 = collect()
    authsrv.handle_pickup([0x803F, drop, 0], s3, st, 0)
    st["pos"] = (-3999.0, 0.0)
    out4, s4 = collect()
    authsrv.ground_items_tick(s4, st, 0)
    check(out3 == [] and out4 == [(OP_CREATE, loot.ground_item_create(drop, g["item"],
                                                                      1000.0, 0.0, 0))]
          and g["shown"] is True,
          "4b. a pickup of an out-of-view item is refused; back inside 5000 u it returns "
          "by a BARE 0x0020 -- no re-declare, no 0x0168 (retail's re-creates, 4 of 4)",
          f"{out4}")
    s = fresh()
    dr = place_drop(s, (500.0, 0.0))
    _x, sd = collect()
    authsrv.handle_pickup([0x803F, dr, 0], sd, s, 0)
    s["pos"] = (-5000.0, 0.0)
    _y, sv = collect()
    authsrv.ground_items_tick(sv, s, 0)
    out5, so = collect()
    authsrv.pickup_tick(so, s, 0, now=s["pickup"]["eta"] + 1.0)
    check(out5 == [] and s.get("pickup") is None,
          "4c. a pickup whose item leaves view is cancelled, nothing sent")


# --------------------------------------------------------------------------- 5
def section_source():
    print("\n5. the source: the kill slot, the world tick, the arm, the flags")
    src = open(authsrv.__file__, encoding="utf-8").read()
    i_kill = src.index("\ndef kill_agent(")
    i_end = src.index("\ndef ", i_kill + 1)
    i_kword = src.find("    send(GAME_SMSG_AGENT_UPDATE_STATUS, [target_id, _word],", i_kill)
    i_party = src.find("    if not reward:", i_kill)
    i_loot = src.find("    loot_on_kill(send, state, target_id, agent, conn_id)\n", i_kill)
    i_morale = src.find("morale_experience(send, state, conn_id, _xp)", i_kill)
    i_krew = src.find("    send(GAME_SMSG_AGENT_KILL_REWARD,", i_kill)
    check(0 < i_kill < i_kword < i_party < i_loot < i_morale < i_krew < i_end
          and src.count("loot_on_kill(send, state, target_id, agent, conn_id)\n") == 1,
          "5a. kill_agent calls loot_on_kill ONCE, after the status word and the party "
          "return and AHEAD of the morale_experience( tick -- not merely ahead of the "
          "reward send (the critic's C1: a drop between the tick and the award would "
          "pass that weaker lock)",
          f"{(i_kword, i_party, i_loot, i_morale, i_krew, i_end)}")
    i_int = src.find("                        interact_pending_tick(send, state, conn_id)\n")
    i_pt = src.find("                        pickup_tick(send, state, conn_id)\n", i_int)
    i_gt = src.find("                        ground_items_tick(send, state, conn_id)\n", i_int)
    i_cast = src.find("                        cast_tick(send, state, conn_id)\n", i_int)
    check(0 < i_int < i_pt < i_gt < i_cast,
          "5b. the world tick polls pickup_tick and ground_items_tick right behind the held "
          "interact, ahead of the casts")
    import test_dispatch as td
    import ast
    arms = td.dispatch_arms(ast.parse(src))
    i_arm = src.find("elif opcode == GAME_CMSG_PICKUP:")
    check(authsrv.GAME_CMSG_PICKUP == 0x003F and arms is not None
          and arms["GAME_CMSG"].get(0x003F) == "GAME_CMSG_PICKUP"
          and 0x003F not in td.DROPPED_ON_PURPOSE
          and "handle_pickup(values, send, state, conn_id, rec=rec)" in src[i_arm:i_arm + 600],
          "5c. 0x003F is an arm of the game dispatch chain (test_dispatch's own harvester), "
          "it calls handle_pickup, and its DROPPED_ON_PURPOSE row is gone")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    d = ap.parse_args([])
    f = ap.parse_args(["--drop-table", "probe_gold", "--no-drops"])
    i_main = src.find("\ndef main():")
    i_dt = src.find("    if a.drop_table is not None:", i_main)
    i_nd = src.find("    if a.no_drops:", i_main)
    check(d.drop_table is None and d.no_drops is False
          and f.drop_table == "probe_gold" and f.no_drops is True
          and 0 < i_main < i_dt and 0 < i_nd
          and "drop_table_row(a.drop_table)" in src[i_dt:i_dt + 400]
          and 'loot.gold_record(agents.item_template("gold_coins")' in src[i_dt:i_dt + 500]
          and "DROP_TABLE = a.drop_table" in src[i_dt:i_dt + 700]
          and "LOOT_ENABLED = False" in src[i_nd:i_nd + 120]
          and authsrv.DROP_TABLE is None and authsrv.LOOT_ENABLED is True,
          "5d. the flags: --drop-table defaults to none (NO kill drops -- the owner's "
          "default) and main() validates it -- the table AND the gold_coins row every "
          "hit declares -- before binding it; --no-drops flips LOOT_ENABLED off (the "
          "known-bad arm)")
    refused = []
    for key in ("no_such_table",):
        try:
            authsrv.drop_table_row(key)
        except content.ContentError:
            refused.append(key)
    check(refused == ["no_such_table"],
          "5e. a --drop-table the store does not carry is refused (main() exits on it)")


# --------------------------------------------------------------------------- 6
def _s2c(capdir, codec, port):
    """(conn, rows, blob): every s2c message of the connection on client port `port`,
    as dicts {seg, w, off, op, v}, in stream order (byte offsets, never a sort)."""
    import bisect
    import tape
    conn = [c["connection"] for c in tape.channel_files(capdir)
            if c["connection"].split("->")[0].endswith(":" + port)][0]
    info, events = tape.load_tape(capdir, conn)
    blob = b"".join(b for _t, b in events)
    starts, times, off = [], [], 0
    for t, b in events:
        starts.append(off)
        times.append(t)
        off += len(b)
    msgs, consumed, err = codec.decode_stream_at("GAME_SMSG", blob, 0)
    if err is not None or consumed != len(blob):
        raise RuntimeError(f"{conn}: the stream did not decode to its last byte ({err})")
    rows = []
    for at, op, v in msgs:
        i = bisect.bisect_right(starts, at) - 1
        rows.append({"seg": i, "w": round(info["t0"] + times[i], 4), "off": at,
                     "op": op, "v": list(v)})
    for k, r in enumerate(rows):
        r["end"] = rows[k + 1]["off"] if k + 1 < len(rows) else len(blob)
    return conn, rows, blob


def _seg(rows, w):
    return [r for r in rows if abs(r["w"] - w) < 0.0006 and r["op"] != 0x001E]


def section_tape(codec):
    print("\n6. THE TAPE (20260929T150923): ours against retail's bytes")
    capdir = vaultpath.vault_path("captures", "live", STAMP)
    if not os.path.isdir(capdir):
        LEDGER.skip("the tape 20260929T150923", f"no {capdir} (bare machine)")
        return
    import cmsgstream
    tapes = {port: _s2c(capdir, codec, port) for port in ("55934", "56025", "53756")}
    deaths, drops = 0, []
    for port, (_c, rows, _b) in tapes.items():
        segs = {}
        for r in rows:
            segs.setdefault(r["seg"], []).append(r)
        for sg, ms in segs.items():
            if any(r["op"] == OP_FLAGS and r["v"][2] == 8 for r in ms):
                deaths += 1
                if any(r["op"] == OP_CREATE and r["v"][3] == 4 for r in ms):
                    drops.append((port, ms))
    c2s = [(round(t, 4), c, list(v)) for t, c, op, v in cmsgstream.timed(STAMP, "c2s", "game")
           if op == 0x003F]
    check(deaths == 12 and len(drops) == 4 and len(c2s) == 3
          and all(v[2] == 0 for _t, _c, v in c2s),
          "6a. the tape as the census read it: 12 death frames on the three connections, 4 "
          "of them with a ground-item create, 3 c2s 0x003F [agent, 0]",
          f"deaths {deaths}, drops {len(drops)}, c2s {c2s}")
    order_ok = []
    for port, ms in drops:
        seq = [r["op"] for r in ms if r["op"] != 0x001E]
        i_st = seq.index(OP_STATUS)
        i_dec = next(i for i, o in enumerate(seq) if o in (OP_DECLARE, 0x0161))
        i_src, i_cre = seq.index(OP_SOURCE), seq.index(OP_CREATE)
        order_ok.append(i_st < i_dec < i_src < i_cre < seq.index(OP_TICK)
                        < seq.index(OP_REWARD) < len(seq) - 1 - seq[::-1].index(OP_FLAGS))
    ours = ops(kill(fresh(), foe_entry(), "probe_gold"))
    check(all(order_ok) and len(order_ok) == 4 and drop_order(ours),
          "6b. all 4 retail drop frames put the declare, 0x0168 and the create between the "
          "status word and the tick, the reward and the flags -- and OURS passes the same "
          "predicate", f"{order_ok}")
    # (c) the kill-frame trio, BYTE-IDENTICAL with retail's ids
    _c, rows, blob = tapes["55934"]
    seg = _seg(rows, 383.5733)
    tape_trio = [r for r in seg if r["op"] in (OP_DECLARE, OP_SOURCE, OP_CREATE)]
    st = fresh(next_purchased_item=472)
    base, saved_scatter = loot.DROP_AGENT_ID_BASE, loot.scatter
    loot.DROP_AGENT_ID_BASE = 57
    loot.scatter = lambda x, y, rng: RETAIL_POINT
    try:
        foe = foe_entry((-100.0, 1600.0))
        sent, send = collect()
        st.setdefault("agents", {})[46] = foe
        with Flags("probe_gold"):
            authsrv.kill_agent(send, st, 46, foe, 0, 0.0)
    finally:
        loot.DROP_AGENT_ID_BASE, loot.scatter = base, saved_scatter
    ours_trio = [(op, v) for op, v in sent if op in (OP_DECLARE, OP_SOURCE, OP_CREATE)]
    same = (len(tape_trio) == 3 and len(ours_trio) == 3
            and [r["op"] for r in tape_trio] == [op for op, _v in ours_trio]
            and all(codec.encode("GAME_SMSG", op, v) == blob[r["off"]:r["end"]]
                    for (op, v), r in zip(ours_trio, tape_trio)))
    check(same and [r["off"] for r in tape_trio] == [29833, 29877, 29889],
          "6c. OURS == RETAIL: with item 472, ground agent 57, foe 46 and retail's point, "
          "our 0x0162, 0x0168 and 0x0020 are byte-identical to :55934's plaintext at "
          "offsets 29833, 29877 and 29889",
          f"{[(hex(r['op']), r['off'], r['end'] - r['off']) for r in tape_trio]}")
    # (d) the arrival frames, byte-identical with the ids substituted
    arrivals_ok = []
    sabotage_caught = None
    for port, w, drop_id, item_id, n in (("55934", 395.546, 57, 472, 6),
                                         ("53756", 1125.5645, 39, 9, 7)):
        _c, rows, blob = tapes[port]
        seg = _seg(rows, w)
        k = next(i for i, r in enumerate(seg) if r["op"] == OP_INT and r["v"][1] == 8)
        run = seg[k:k + 8]
        me = run[0]["v"][2]
        key = next(r["v"][1] for r in run if r["op"] == OP_GOLD)
        s = fresh()
        s["ground_items"] = {drop_id: {"item": item_id, "gold": n, "pos": (0.0, 0.0),
                                       "plane": 0, "source": 0, "shown": True}}
        s["pickup"] = {"agent": drop_id, "t0": None, "eta": 0.0, "dest": None}
        sent, send = collect()
        authsrv.serve_pickup(send, s, 0, now=0.0)
        subst = []
        for op, v in sent:
            v = list(v)
            if op in (OP_INT, OP_PICKED):        # [prop, me, value] / [item, me]
                v[1] = me
            if op == OP_HALT:
                v[0] = me
            if op == OP_GOLD:
                v[0] = key
            subst.append((op, v))

        def same_bytes(ours_list, tape_rows):
            return (len(ours_list) == len(tape_rows)
                    and all(codec.encode("GAME_SMSG", op, v) == blob[r["off"]:r["end"]]
                            for (op, v), r in zip(ours_list, tape_rows)))

        arrivals_ok.append(same_bytes(subst, run))
        if sabotage_caught is None:
            # the ORACLE is the tape's own decode: it must re-encode to the tape
            # exactly, and must NOT match a sabotaged copy -- a control on the
            # comparator itself, independent of what serve_pickup sends
            oracle = [(r["op"], r["v"][1:]) for r in run]
            bad = list(run)
            bad[2], bad[3] = bad[3], bad[2]
            sabotage_caught = same_bytes(oracle, run) and not same_bytes(oracle, bad)
    check(arrivals_ok == [True, True],
          "6d. OURS == RETAIL: serve_pickup's frame with the ids substituted (me 31 / 9, "
          "key 2) is byte-identical to both gold arrivals, :55934 395.546 and :53756 "
          "1125.5645 -- eight messages each", f"{arrivals_ok}")
    check(sabotage_caught is True,
          "6e. SABOTAGE: the tape's own decode re-encodes to its bytes exactly, and FAILS the "
          "same comparator against the tape with 0x0159 and 0x0140 swapped")
    # (f) every 0x0162 is the gold row, value == quantity; prop 39 only in arrivals
    gold = agents.item_template("gold_coins")
    decl, p39 = [], []
    for port, (_c, rows, _b) in tapes.items():
        for r in rows:
            if r["op"] == OP_DECLARE:
                decl.append(r["v"][1:])
            if r["op"] == OP_INT and r["v"][1] == agents.GV_PICKUP:
                p39.append((port, r["w"]))
    check(len(decl) == 4 and all(
        v[1] == gold["file_id"] and v[2] == gold["item_type"] and v[7] == gold["flags"]
        and v[9] == gold["model_id"] and v[11] == gold["enc_name"] and v[8] == v[10]
        and v[12] == [] for v in decl),
          "6f. every 0x0162 on the three connections (4) is the gold row with value == "
          "quantity", f"{[(v[0], v[8], v[10]) for v in decl]}")
    check(sorted(p39) == sorted([("55934", 395.546), ("56025", 865.9126),
                                 ("53756", 1125.5645)]),
          "6g. property 39 appears only in the three arrival frames", f"{p39}")
    # (h) the hold's release ~1.0 s after each gold arrival; the straight 0x002A
    rel, walks = [], []
    for port, w, me, drop_id, t_press in (("55934", 395.546, 31, 57, 392.5101),
                                           ("53756", 1125.5645, 9, 39, 1124.0176)):
        _c, rows, blob = tapes[port]
        nxt = next(r["w"] for r in rows if r["w"] > w and r["op"] == OP_INT
                   and r["v"][1:] == [8, me, 0])
        rel.append(round(nxt - w, 4))
        walk = next(r for r in rows if r["w"] >= t_press and r["op"] == OP_WALK
                    and r["v"][1] == me)
        cre = next(r for r in rows if r["op"] == OP_CREATE and r["v"][1] == drop_id
                   and r["v"][3] == 4 and r["w"] < t_press)
        s = fresh(pos=(0.0, 0.0))
        s["ground_items"] = {drop_id: {"item": 0, "gold": 1, "pos": tuple(cre["v"][5]),
                                       "plane": 0, "source": 0, "shown": True}}
        sent, send = collect()
        authsrv.handle_pickup([0x803F, drop_id, 0], send, s, 0)
        ours = [(op, [me] + list(v[1:])) for op, v in sent]
        walks.append(len(ours) == 1 and walk["w"] - t_press < 0.05
                     and codec.encode("GAME_SMSG", *ours[0]) == blob[walk["off"]:walk["end"]])
    check(all(abs(r - loot.PICKUP_HOLD_SECONDS) <= 0.02 for r in rel)
          and walks == [True, True],
          "6h. the hold releases 1.0 s after each gold arrival (retail +0.9985, +0.9940), "
          "and our 0x002A to the item is byte-identical to retail's straight replies "
          "(within 50 ms of the press)", f"release {rel}, walks {walks}")
    # (i) the view range's SHAPE: an unpicked ground item leaves by a bare 0x0021 (no
    # 0x0159 / 0x0140 in its frame) and comes back by a bare 0x0020 (no declare, no
    # 0x0168). Ground agents are tracked per id, because an id is re-used by bodies.
    removed, recreated, picked = [], [], 0
    for port, (_c, rows, _b) in tapes.items():
        segs = {}
        for r in rows:
            segs.setdefault(r["seg"], []).append(r["op"])
        live, seen = {}, set()
        for r in rows:
            if r["op"] == OP_CREATE:
                aid = r["v"][1]
                if r["v"][3] == 4:
                    if (aid, r["v"][2]) in seen:
                        recreated.append(not ({0x0161, OP_DECLARE, OP_SOURCE}
                                              & set(segs[r["seg"]])))
                    seen.add((aid, r["v"][2]))
                    live[aid] = r["v"][2]
                else:
                    live.pop(aid, None)
            elif r["op"] == OP_REMOVE and r["v"][1] in live:
                live.pop(r["v"][1])
                if OP_PICKED in segs[r["seg"]]:
                    picked += 1
                else:
                    removed.append(not ({OP_PICKED, OP_GOLD} & set(segs[r["seg"]])))
    check(len(removed) == 11 and all(removed) and len(recreated) == 4 and all(recreated)
          and picked == 3,
          "6i. the view range's shape: 11 unpicked ground items leave by a bare 0x0021 and "
          "4 come back by a bare 0x0020 (no declare, no 0x0168) -- ground_items_tick's two "
          "sends; the other 3 removals are the pickups",
          f"removed {removed}, recreated {recreated}, picked {picked}")


# --------------------------------------------------------------------------- 7
# RANGERLOOP-F8: the pickup beside a standing NPC. The practice Hatcher revives at
# (10126, 8077) standing 30 u from its own drops. On 20260930T133106 (Run A) the
# mirror's avoidance pass halted the player's copy at its 80 u disc on 3 of 3 pickups,
# 1z-dj's park cleared the walk's dest, and each pickup CANCELLED "short of the item"
# while the client's body reached the pile. The rig is rebuilt here with the REAL guard,
# the REAL pass and the REAL _npc_obstacles, fed through the send() choke point's own
# feed, at the runs' own coordinates.
HATCHER_AT = (10126.0, 8077.0)
RUN_A = ((10047.0, 8077.0), (10131.0, 8107.0))    # the approach's disc stop -> pile 401
RUN_A2 = ((10008.0, 8077.0), (10142.0, 8052.0))   # Run A' 400: 136 u out, the line 21.6 u off


class Rec:
    def __init__(self):
        self.rows = []

    def event(self, kind, **kw):
        self.rows.append(dict(kw, kind=kind))

    def acts(self, act):
        return [r for r in self.rows if r["kind"] == "kbd_leg" and r.get("act") == act]


class Globals:
    """Set authsrv's two avoid-halt switches for a block, and put them back."""

    def __init__(self, through=True, park=True):
        self.want = (through, park)

    def __enter__(self):
        self.saved = (authsrv.PICKUP_WALKS_THROUGH_AVOID_HALT,
                      authsrv.MODEL_PARKS_ON_AVOID_HALT)
        authsrv.PICKUP_WALKS_THROUGH_AVOID_HALT, authsrv.MODEL_PARKS_ON_AVOID_HALT = self.want

    def __exit__(self, *exc):
        authsrv.PICKUP_WALKS_THROUGH_AVOID_HALT, authsrv.MODEL_PARKS_ON_AVOID_HALT = self.saved


def beside(start, pile, hatcher_dead=False, park_in_send=None):
    """The rig: a seeded AgTrack guard, the Hatcher standing (or dead) at HATCHER_AT,
    the player at `start`, a 6-gold pile (ground agent 401) at `pile`. -> (st, sent,
    send). `send` feeds the guard exactly as the live choke point does, so the pickup's
    0x002A reaches the mirror; `park_in_send` (a Rec) also runs 1z-dj's park INSIDE the
    0x002A's send, before handle_pickup writes the walk's dest -- the recv/world-tick
    interleaving where the grant's own setter halts the copy."""
    foe = foe_entry(HATCHER_AT)
    foe["dead"] = hatcher_dead
    st = fresh(pos=start, agents={10: foe})
    authsrv._agtrack_guard_seed(st, start, 0, 0)
    st["ground_items"] = {401: {"item": 5001, "gold": 6, "pos": pile, "plane": 0,
                                "source": 10, "shown": True}}
    sent = []

    def send(op, v, label="", quiet=False):
        sent.append((op, list(v)))
        authsrv._agtrack_shadow_emit(st, op, list(v), None)
        if park_in_send is not None and op == OP_WALK:
            authsrv._model_park_on_avoid_halt(st, park_in_send, time.time())
    return st, sent, send


def walk_out(st, send, rec, press=True, step=0.05):
    """handle_pickup (unless `press` is False), then the world tick's halves on a
    virtual clock -- the guard's tick, 1z-dj's park, pickup_tick -- until the pickup
    resolves. -> (pickup_tick's result or None, the tick it resolved on, the record)."""
    t = time.time()
    if press:
        authsrv.handle_pickup([0x803F, 401, 0], send, st, 0)
    pk = dict(st.get("pickup") or {})
    end = pk.get("eta", t) + 0.5
    while t < end:
        t += step
        authsrv._agtrack_guard_call(st, "tick", t)
        authsrv._model_park_on_avoid_halt(st, rec, t)
        r = authsrv.pickup_tick(send, st, 0, now=t)
        if r is not None:
            return r, t, pk
    return None, t, pk


def halts(st):
    g = st.get("agtrack_guard")
    return -1 if g is None else int(g.mirror.sync.n_avoid_halt)


def section_beside():
    print("\n7. the pickup beside a standing NPC (RANGERLOOP-F8): the avoid halt does not "
          "cancel it")
    walk_msg = lambda pile: (OP_WALK, [PLAYER, pile, 0, 0, 401])   # noqa: E731

    rec = Rec()
    with Globals():
        st, sent, send = beside(*RUN_A)
        r, t, pk = walk_out(st, send, rec)
    check(halts(st) >= 1 and r is True and t >= pk.get("eta", INF)
          and sent == [walk_msg(RUN_A[1])] + arrival_list(5001, 401, 6)
          and st.get("purse") == 6 and st.get("pos") == RUN_A[1]
          and len(rec.acts("avoid-halt-pickup")) >= 1 and not rec.acts("avoid-halt"),
          "7a. HEADLINE, Run A's pile 401 from the approach's disc stop: the real pass "
          "halts the copy at the Hatcher's disc (the exposure -- no halt, no test), the "
          "halt is NOT parked, and at the leg's eta the pickup is served in retail's frame, "
          "purse 0 -> 6, the body at the pile",
          f"halts {halts(st)} result {r} purse {st.get('purse')} pos {st.get('pos')} "
          f"rows {rec.rows} sent {[(hex(o), v) for o, v in sent]}")

    rec = Rec()
    with Globals():
        st, sent, send = beside(*RUN_A2)
        r, t, pk = walk_out(st, send, rec)
    row = (rec.acts("avoid-halt-pickup") or [{}])[0]
    at = row.get("point") or [INF, INF]
    d_hatcher = math.hypot(at[0] - HATCHER_AT[0], at[1] - HATCHER_AT[1])
    check(halts(st) >= 1 and r is True and st.get("purse") == 6
          and st.get("pos") == RUN_A2[1] and 60.0 <= d_hatcher <= 80.5
          and (row.get("short") or 0) > 50.0,
          "7b. Run A' 400, 136 u out on a line passing 21.6 u from the Hatcher's centre: the "
          "pass halts the copy on the disc (60-80 u from its centre, over 50 u short of "
          "the pile) mid-walk, and the pickup is still served",
          f"halts {halts(st)} result {r} purse {st.get('purse')} row {row} "
          f"d {d_hatcher:.1f}")

    got = []
    for geo in (RUN_A, RUN_A2):
        rec = Rec()
        with Globals(through=False):
            st, sent, send = beside(*geo)
            r, t, pk = walk_out(st, send, rec)
        got.append((halts(st), r, st.get("purse"), st.get("pickup"), sent[1:],
                    len(rec.acts("avoid-halt"))))
    check(all(h >= 1 and r is False and purse is None and pk is None and rest == []
              and parks >= 1 for h, r, purse, pk, rest, parks in got),
          "7c. KNOWN-BAD ARM (--no-pickup-through-avoid-halt), both geometries: 1z-dj parks "
          "the model at the halt, the walk's dest is gone, and the pickup CANCELS with "
          "nothing sent -- Run A's 3 of 3, reproduced at the desk",
          f"{got}")

    rec = Rec()
    with Globals():
        st, sent, send = beside(RUN_A2[0], RUN_A2[1])
        st.pop("ground_items")
        lead = RUN_A2[1]
        send(0x0029, [PLAYER, lead, 0, 0])
        st["dest"] = lead
        t = time.time()
        for _ in range(12):
            t += 0.05
            authsrv._agtrack_guard_call(st, "tick", t)
            authsrv._model_park_on_avoid_halt(st, rec, t)
    parked = rec.acts("avoid-halt")
    pos = st.get("pos") or (INF, INF)
    check(halts(st) >= 1 and st.get("dest") is None and parked
          and math.hypot(pos[0] - parked[0]["point"][0], pos[1] - parked[0]["point"][1]) < 0.1
          and not rec.acts("avoid-halt-pickup"),
          "7d. SCOPE: a plain 0x0029 lead to the same point inside the disc, no pickup on "
          "record, is still parked by 1z-dj (pos at the halt, dest cleared) -- the "
          "exemption does not swallow the keyboard class the park was built for",
          f"halts {halts(st)} dest {st.get('dest')} pos {st.get('pos')} rows {rec.rows}")

    rec_in, rec = Rec(), Rec()
    with Globals():
        st, sent, send = beside(*RUN_A, park_in_send=rec_in)
        r, t, pk = walk_out(st, send, rec)
    check(halts(st) >= 1 and len(rec_in.acts("avoid-halt")) == 1
          and r is True and st.get("purse") == 6,
          "7e. THE THREADS: the grant's own setter halts the copy inside send() and a tick "
          "parks it there, before handle_pickup writes the walk's dest -- 1z-dj parks and "
          "clears a dest that _approach_send then overwrites, and the pickup is served",
          f"halts {halts(st)} in-send rows {rec_in.rows} result {r} purse {st.get('purse')}")

    # Run A's geometry halts at the grant's own setter, so the halt is pending the
    # moment handle_pickup returns; the park then runs on a dest another order wrote
    # (the world tick parks BEFORE pickup_tick, so this is the tick that sees it).
    rec = Rec()
    with Globals():
        st, sent, send = beside(*RUN_A)
        authsrv.handle_pickup([0x803F, 401, 0], send, st, 0)
        st["dest"] = (9000.0, 8077.0)     # another order took the model's dest
        parked_now = authsrv._model_park_on_avoid_halt(st, rec, time.time() + 0.05)
    check(halts(st) >= 1 and parked_now is True and st.get("dest") is None
          and rec.acts("avoid-halt") and not rec.acts("avoid-halt-pickup")
          and st.get("pickup") is not None,
          "7f. keyed on the DEST: with a pickup still on record but another order's dest "
          "in the model, the halt is parked as before (1z-dj) -- the exemption is the "
          "pickup's WALK, not the pickup's record",
          f"halts {halts(st)} parked {parked_now} dest {st.get('dest')} rows {rec.rows}")

    got = []
    for through in (True, False):
        rec = Rec()
        with Globals(through=through):
            st, sent, send = beside(*RUN_A, hatcher_dead=True)
            r, t, pk = walk_out(st, send, rec)
        got.append((halts(st), r, st.get("purse")))
    check(got == [(0, True, 6), (0, True, 6)],
          "7g. a CORPSE is no obstacle (_npc_obstacles skips the dead): with the Hatcher "
          "dead there is no halt and both arms serve -- which is why retail's three "
          "pickups (only corpses within 300 u of each pile) never exposed this, and why "
          "the practice target's revive did",
          f"{got}")

    src = open(authsrv.__file__, encoding="utf-8").read()
    import serverargs
    sa = open(serverargs.__file__, encoding="utf-8").read()
    i_main = src.find("\ndef main():")
    i_flag = src.find("    if a.no_pickup_through_avoid_halt:", i_main)
    i_park = src.find("\ndef _model_park_on_avoid_halt(")
    check(authsrv.PICKUP_WALKS_THROUGH_AVOID_HALT is True
          and authsrv.capture_flags().get("PICKUP_WALKS_THROUGH_AVOID_HALT") is True
          and '"--no-pickup-through-avoid-halt"' in sa
          and 0 < i_main < i_flag
          and "PICKUP_WALKS_THROUGH_AVOID_HALT = False" in src[i_flag:i_flag + 160]
          and "PICKUP_WALKS_THROUGH_AVOID_HALT and pk" in src[i_park:i_park + 2600],
          "7h. ships ON, on the capture's flags row, with its revert "
          "--no-pickup-through-avoid-halt wired in main() and read by the park")


# --------------------------------------------------------------------------- 8
# RANGERLOOP-F10: why section 7's Hatcher was no obstacle to the client. The kill
# sends 0x0026 [agent, 8], and revive_due sent the 0x00F1 status ALONE, so the client
# kept the revived body at life-state 8 (agenttap, 20260930T151413: m_flags
# 0x00020009 -> 0x00020008 at the first kill, never back). Retail's in-place revive
# carries 0x0026 [agent, 9] in the status's own segment, the status first (62 of 63
# NPC revives, 16 connections, 6 captures; the census is authsrv's comment on
# REVIVE_SENDS_ALIVE_FLAGS).
OP_STAT, OP_FLAGS26, OP_MAXINT, OP_BAR = 0x00F1, 0x0026, 0x009F, 0x00A3


def revive_sends(defer, flags):
    """revive_due on a long-dead practice body (agent 10), under the two switches."""
    agent = foe_entry(HATCHER_AT)
    agent.update(dead=True, died_at=0.0, health=0.0)
    st = fresh(agents={10: agent})
    sent, send = collect()
    saved = (authsrv.REVIVE_REFILL_DEFER, authsrv.REVIVE_SENDS_ALIVE_FLAGS)
    authsrv.REVIVE_REFILL_DEFER, authsrv.REVIVE_SENDS_ALIVE_FLAGS = defer, flags
    try:
        authsrv.revive_due(send, st, 0)
    finally:
        authsrv.REVIVE_REFILL_DEFER, authsrv.REVIVE_SENDS_ALIVE_FLAGS = saved
    return sent, agent


def section_revive_flags():
    print("\n8. the revive's life-state byte (RANGERLOOP-F10): 0x0026 [agent, 9] behind "
          "the status")
    sent, agent = revive_sends(0.05, True)
    check(sent == [(OP_STAT, [10, 0]), (OP_FLAGS26, [10, authsrv.AGENT_FLAGS_BODY_ALIVE])]
          and authsrv.AGENT_FLAGS_BODY_ALIVE == 9 and agent["dead"] is False,
          "8a. HEADLINE, the shipped arm (the refill deferred a tick): the revive sends "
          "the status [10, 0] and then 0x0026 [10, 9], retail's in-place revive, status "
          "first, one tick -- the life-state byte back to alive",
          f"{[(hex(o), v) for o, v in sent]}")
    sent, _a = revive_sends(0.0, True)
    check([o for o, _v in sent] == [OP_STAT, OP_MAXINT, OP_BAR, OP_FLAGS26]
          and sent[-1] == (OP_FLAGS26, [10, 9]),
          "8b. the immediate arm: status, the max, the bar, and the flags byte LAST -- it "
          "closes what the tick sends, as it closes the player's and a party body's rise",
          f"{[(hex(o), v) for o, v in sent]}")
    got = [revive_sends(d, False)[0] for d in (0.05, 0.0)]
    check(got[0] == [(OP_STAT, [10, 0])]
          and OP_FLAGS26 not in [o for o, _v in got[1]],
          "8c. KNOWN-BAD ARM (--no-revive-flags): the status alone, no 0x0026 on either "
          "arm -- the wire that left 20260930T151413's Hatcher at life-state 8",
          f"{[[(hex(o), v) for o, v in s] for s in got]}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    import serverargs
    sa = open(serverargs.__file__, encoding="utf-8").read()
    i_main = src.find("\ndef main():")
    i_flag = src.find("    if a.no_revive_flags:", i_main)
    i_rev = src.find("\ndef revive_due(")
    i_end = src.find("\ndef ", i_rev + 1)
    check(authsrv.REVIVE_SENDS_ALIVE_FLAGS is True
          and authsrv.capture_flags().get("REVIVE_SENDS_ALIVE_FLAGS") is True
          and '"--no-revive-flags"' in sa and 0 < i_main < i_flag
          and "REVIVE_SENDS_ALIVE_FLAGS = False" in src[i_flag:i_flag + 120]
          and src[i_rev:i_end].count("if REVIVE_SENDS_ALIVE_FLAGS:") == 2,
          "8d. ships ON, on the capture's flags row, with its revert --no-revive-flags "
          "wired in main(), read by both of revive_due's arms")


def main():
    codec = Codec()
    section_leaf(codec)
    section_kill()
    section_pickup()
    section_view()
    section_source()
    section_tape(codec)
    section_beside()
    section_revive_flags()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
