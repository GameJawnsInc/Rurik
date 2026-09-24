"""The carried purse -- DESKWORK-D9 (pass 1 and its fix pass). purse.py, the
load credit, the quest gold, the hand-in ORDER, the merchant's buy/sell moves,
and persistence across a zone.

WHAT THIS CHECKS, beyond round-trips:
  * purse.py's arithmetic and the load-credit builder (skip on 0 -- retail's
    own rule, 55 of 96 live loads -- and a positive credit keyed by the
    inventory stream key), with a known-bad and a vacuity guard.
  * grant_quest_reward pays reward_gold as 0x0140 AFTER the experience 0x00EE
    as a DELTA (the reward amount, not the new balance), with the known-bad
    arms the task names: gold missing (flag off) and a balance sent where a
    delta belongs.
  * turn_in_quest puts the reward BETWEEN 0x0052 and 0x004A -- retail's
    relative order on 10 of 10 hand-ins -- and --no-reward-in-frame is the
    MUTANT that reddens the same predicate (the pass-1 order, reward after
    0x004A, which no tape shows).
  * the load's arm as a helper (load_purse_messages): [0x0140 [1, N]] for a
    positive purse and `purse_synced` set, [] for 0, [] under --no-load-purse,
    the stored purse reaching it under --persist through the LAZY store lookup
    (the fix pass: pass 1 read 0 under --persist --no-item-moves and the next
    hand-in overwrote the stored balance), and a source lock on its POSITION
    in the burst (after the weapon sets, before UPDATE_GOLD_STORAGE).
  * the merchant's buy debits and sell credits the purse through purse.py (the
    wire already moves it via 0x014F/0x0140), an unaffordable buy against a
    SERVER-CREDITED balance sends NOTHING (the client greys Buy at zero funds
    -- 20260818T235130; retail's server reply is NOT FOUND), authsrv's
    wrappers write the temp store under --persist, and a probe's own gold
    message clears the sync.
  * --no-quest-gold also drops the offer screen's gold line (a promise the
    flag would otherwise leave unpaid).
  * persistence across a zone on a TEMP store (never the real vault), that the
    optional `purse` field did NOT bump STORE_VERSION, and that a refused
    (stale) save is reported, not swallowed.
  * (vault-gated, and it FAILS rather than skips once the capture is on disk)
    the tape itself: 20260914T180058's five loads credit [own key, 60/60/60/
    60/85] right after the last 0x0147; the :56301 hand-in batch (same
    timestamp as the 0x0140 [2, 25]) has 0x0052 < 0x00EE [0, 250] <
    0x0140 < 0x004A with 0x004A the last quest-family message; OUR
    turn_in_quest batch has the same relative order and the pass-1 order does
    not; a sabotaged tape (gold before xp) reddens the tape predicate; and
    20260807T143055's 0-purse load (:60935, no credit, +10 at the hand-in,
    :62994 loads [k, 10]) -- the OBSERVED half of "skip at 0".

Everything bare runs against temp stores and in-memory state; nothing binds a
port, launches a client, or touches vault/state.
"""

import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks       # noqa: E402
import purse        # noqa: E402
import charstore    # noqa: E402
import merchant     # noqa: E402
import questdefs    # noqa: E402
import authsrv      # noqa: E402
import vaultpath    # noqa: E402

# Floor 45 from the bare-machine green run (RURIK_VAULT at an empty dir),
# sections 1-4; section 5 (the tape) adds 13 when the vault is present (58) and
# declares two LEDGER.skips on a bare machine. Set from the run, never above it.
led = checks.Ledger("the carried purse (DESKWORK-D9)", floor=45)

UUID = "22222222222222222222222222222222"
KEY = authsrv.PLAYER_INVENTORY_KEY
GOLD = merchant.GAME_SMSG_GOLD_CREDIT      # 0x0140
DEBIT = merchant.GAME_SMSG_GOLD_DEBIT      # 0x014F
XP = authsrv.GAME_SMSG_AGENT_KILL_REWARD   # 0x00EE
REMOVE = authsrv.GAME_SMSG_QUEST_REMOVE                # 0x0052
UNLIST = authsrv.GAME_SMSG_QUEST_REMOVE_AND_UNLIST     # 0x004A
QUEST_FAMILY = {0x0049, 0x004A, 0x004C, 0x004D, 0x0050, 0x0051, 0x0052,
                0x0053, 0x0054}

# A stock row in named_item()'s field order (from test_purchase), value 5.
STOCK = [40, 0x8000005B, 7, 19, 11, 0, 0, 0x20001006, 5, 2440, 1, "x", []]
BUY = [0x804D, 1, 40, [], b"", 0, [40], b"\x01"]


class Rec:
    def event(self, kind, **kw):
        pass


def collect():
    sent = []
    return sent, (lambda op, values, label="", **kw: sent.append((op, list(values))))


def reward_kinds(seq):
    """A batch reduced to the four kinds the order claim is about:
    ("remove", "xp", "gold", "unlist"), in sequence. `seq` is [(op, values)]
    with values either the sent list ([key, n]) or the decoded tape list
    ([header, key, n]) -- the xp test reads the LAST two fields so both fit."""
    out = []
    for op, v in seq:
        if op == REMOVE:
            out.append("remove")
        elif op == XP and len(v) >= 2 and v[-2] == 0 and v[-1] > 0:
            out.append("xp")
        elif op == GOLD:
            out.append("gold")
        elif op == UNLIST:
            out.append("unlist")
    return out


def retail_order(kinds):
    """The tape's rule on all 10 hand-ins: the first 0x0052 precedes the xp,
    the xp precedes the gold, and the gold precedes the closing 0x004A."""
    if not {"remove", "xp", "gold", "unlist"} <= set(kinds):
        return False
    return (kinds.index("remove") < kinds.index("xp") < kinds.index("gold")
            < len(kinds) - 1 - kinds[::-1].index("unlist"))


def fresh_state(**kw):
    st = {"quests": set(), "objectives_done": set(), "quests_completed": set(),
          "agents": {}, "char_uuid": UUID}
    st.update(kw)
    return st


def main():
    # -- 1. purse.py arithmetic and the load-credit builder ---------------
    led.ok(purse.STARTING_PURSE == 0 and purse.start() == 0,
           "a character with no stored purse starts at 0 (OBSERVED: two "
           "characters' chains start at 0 -- no credit at load, +10 at the "
           "first hand-in, 10 on the next load)")
    led.ok(purse.load_credit(KEY, 0) is None,
           "load_credit SKIPS a 0 purse -- retail's rule (55 of 96 live loads "
           "carry no 0x0140, and none credits 0)")
    led.ok(purse.load_credit(KEY, 60) == [KEY, 60],
           "load_credit(60) is [inventory key, 60] -- retail's shape",
           f"{purse.load_credit(KEY, 60)}")
    # KNOWN-BAD: a builder that sent the credit for a 0 purse would return a
    # value here instead of None.
    led.ok(purse.load_credit(KEY, 0) != [KEY, 0],
           "KNOWN-BAD: sending [key, 0] at load is refused (None, not [key, 0])")
    led.ok(purse.can_afford(50, 40) and not purse.can_afford(30, 40)
           and purse.can_afford(None, 40),
           "can_afford gates on the balance, and a None (unmodelled) purse "
           "always affords -- the bare merchant recipe keeps working")
    led.ok(purse.after_buy(100, 40) == 60 and purse.after_sell(60, 25) == 85
           and purse.after_credit(60, 25) == 85,
           "buy debits, sell/credit accumulate", )
    # VACUITY: a negative purse is a bug, not a value.
    try:
        purse.after_buy(10, 40)
        led.ok(False, "a purse driven negative RAISES")
    except ValueError:
        led.ok(True, "a purse driven negative RAISES (the caller checks "
                     "can_afford first, so reaching it is a bug)")

    # -- 2. grant_quest_reward pays gold AFTER the xp, as a DELTA ----------
    _saved_persist = authsrv.PERSIST
    _saved_flag = authsrv.QUEST_GOLD_ENABLED
    _saved_frame = authsrv.REWARD_IN_FRAME

    def grant(row, persist=False, store=None, state=None):
        sent, send = collect()
        st = state if state is not None else fresh_state()
        if store is not None:
            st["charstore_game"] = store
        _entry = authsrv.PERSIST      # restore what the CALLER had, not the
        authsrv.PERSIST = persist     # module default (section 4b runs under
        try:                          # PERSIST=True and calls this)
            paid = authsrv.grant_quest_reward(send, st, 1463, row, 0)
        finally:
            authsrv.PERSIST = _entry
        return paid, sent, st

    _, sent, st = grant({"reward_experience": 100, "reward_gold": 10})
    ops = [op for op, _v in sent]
    gold = [v for op, v in sent if op == GOLD]
    led.ok(gold == [[KEY, 10]] and st.get("purse") == 10,
           "reward_gold=10 pays 0x0140 [key, 10] and the purse holds 10",
           f"gold={gold} purse={st.get('purse')}")
    led.ok(GOLD in ops and XP in ops and ops.index(GOLD) > ops.index(XP),
           "the gold 0x0140 comes AFTER the experience 0x00EE -- the tape's "
           "order, 10 of 10", f"{[hex(o) for o in ops]}")
    # KNOWN-BAD (a balance where a delta belongs): the credit is the DELTA
    # (reward_gold), never the resulting balance. Start with a purse so the two
    # differ.
    _, sent3, st3 = grant({"reward_experience": 5, "reward_gold": 10},
                          state=fresh_state(purse=25))
    g3 = [v for op, v in sent3 if op == GOLD]
    led.ok(g3 == [[KEY, 10]] and st3["purse"] == 35,
           "the credit is the DELTA (10), NOT the new balance (35) -- a balance "
           "on the wire would desync the client's own accumulate",
           f"credit={g3} purse={st3['purse']}")
    # the revert flag
    authsrv.QUEST_GOLD_ENABLED = False
    try:
        _, sent, st = grant({"reward_experience": 100, "reward_gold": 10})
    finally:
        authsrv.QUEST_GOLD_ENABLED = _saved_flag
    led.ok(GOLD not in [op for op, _v in sent] and st.get("purse") is None,
           "--no-quest-gold reverts: no 0x0140 and no purse move")
    # gold-only reward still pays
    _, sent, st = grant({"reward_gold": 7})
    led.ok([v for op, v in sent if op == GOLD] == [[KEY, 7]]
           and st.get("purse") == 7,
           "a gold-only reward pays although there is no experience")

    # -- 2b. turn_in_quest: the reward BETWEEN 0x0052 and 0x004A -----------
    ROW = {"reward_experience": 250, "reward_gold": 25}

    def turn_in(frame):
        sent, send = collect()
        st = fresh_state(quests={1463})
        authsrv.REWARD_IN_FRAME = frame
        try:
            authsrv.turn_in_quest(send, st, 1463, ROW, 0)
        finally:
            authsrv.REWARD_IN_FRAME = _saved_frame
        return sent, st

    ours, st = turn_in(True)
    kinds = reward_kinds(ours)
    led.ok(kinds == ["remove", "xp", "gold", "unlist"],
           "turn_in_quest sends 0x0052, the xp 0x00EE, the gold 0x0140, then "
           "0x004A -- the tape's relative order on 10 of 10 hand-ins",
           f"{kinds} from {[hex(o) for o, _v in ours]}")
    led.ok(retail_order(kinds), "and the retail-order predicate accepts it")
    led.ok(1463 not in st["quests"] and 1463 in st["quests_completed"]
           and st.get("purse") == 25,
           "the quest leaves the log, is marked completed, and the purse holds "
           "the 25", f"quests={st['quests']} purse={st.get('purse')}")
    # THE MUTANT is the revert flag: pass 1's order, reward after 0x004A.
    bad, _ = turn_in(False)
    kinds_bad = reward_kinds(bad)
    led.ok(kinds_bad == ["remove", "unlist", "xp", "gold"]
           and not retail_order(kinds_bad),
           "KNOWN-BAD: --no-reward-in-frame sends the reward AFTER 0x004A "
           "(pass 1's order, which no tape shows) and the SAME predicate "
           "reddens on it", f"{kinds_bad}")
    led.ok([op for op, _v in bad if op in (REMOVE, UNLIST, XP, GOLD)].count(GOLD) == 1
           and len(bad) == len(ours),
           "the flag moves the reward, it does not duplicate or drop it",
           f"{len(bad)} vs {len(ours)} messages")

    # -- 2c. --no-quest-gold drops the offer screen's gold line -------------
    prose_row = {"reward_experience": 100, "reward_gold": 10,
                 "wire_framing": "template"}
    with_b = authsrv._quest_prose(prose_row, "x")
    authsrv.QUEST_GOLD_ENABLED = False
    try:
        without_b = authsrv._quest_prose(prose_row, "x")
    finally:
        authsrv.QUEST_GOLD_ENABLED = _saved_flag

    def has_slot(s, slot):
        u = [ord(c) for c in s]
        return any(tuple(u[i:i + len(slot)]) == slot
                   for i in range(len(u) - len(slot) + 1))

    led.ok(has_slot(with_b, questdefs.REWARD_SLOT_A)
           and has_slot(with_b, questdefs.REWARD_SLOT_B),
           "the offer screen draws both reward lines (xp, gold) by default")
    led.ok(has_slot(without_b, questdefs.REWARD_SLOT_A)
           and not has_slot(without_b, questdefs.REWARD_SLOT_B),
           "--no-quest-gold drops slot B from the screen too -- the flag does "
           "not leave a promise the server refuses to pay")

    # -- 3. the merchant moves the purse ----------------------------------
    def buy(state, price=40):
        sent, send = collect()
        state.setdefault("declared_items", {STOCK[0]: list(STOCK)})
        merchant.handle_item_purchase(
            [0x804D, 1, price, [], b"", 0, [40], b"\x01"], send, state, 1,
            Rec(), KEY, authsrv.GAME_SMSG_CREATE_NAMED_ITEM,
            authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION)
        return sent

    st = {"purse": 100, "purse_synced": True}
    sent = buy(st, price=40)
    led.ok(st["purse"] == 60 and any(op == DEBIT for op, _v in sent),
           "a buy debits the purse (100 - 40) and still sends 0x014F",
           f"purse={st['purse']}")
    # insufficient funds, SYNCED (the server credited the balance): nothing sent
    st = {"purse": 5, "purse_synced": True}
    sent = buy(st, price=40)
    led.ok(st["purse"] == 5 and sent == [],
           "an unaffordable buy against a SERVER-CREDITED balance sends NOTHING "
           "and leaves the purse -- retail's insufficient-funds reply is NOT FOUND",
           f"purse={st['purse']} sent={sent}")
    # insufficient funds, UNSYNCED (a probe funded the client out-of-band): the
    # gate is inert, the item is delivered, the purse is left (not driven negative)
    st = {"purse": 5}
    sent = buy(st, price=40)
    led.ok(st["purse"] == 5 and any(op == DEBIT for op, _v in sent),
           "an unaffordable buy against an UNSYNCED purse completes (the client "
           "was funded out-of-band; the probe must keep working) and the purse "
           "is not driven negative", f"purse={st['purse']}")
    # VACUITY: no purse in state -> no gate, old behaviour (the bare recipe)
    st = {}
    sent = buy(st, price=40)
    led.ok("purse" not in st and any(op == DEBIT for op, _v in sent),
           "with NO purse modelled the buy is unchanged (the bare recipe) -- the "
           "gate is inert when there is nothing to gate")
    # sell credits
    st = {"purse": 60, "backpack": {0: 5000}}
    sent, send = collect()
    merchant.handle_item_sale([0x804A, 11, 0, [5000], 25, []], send, st, 1,
                              Rec(), KEY)
    led.ok(st["purse"] == 85 and any(op == GOLD for op, _v in sent),
           "a sell credits the purse (60 + 25) and sends 0x0140",
           f"purse={st['purse']}")
    # the persist callback is called with the moved state
    calls = []
    st = {"purse": 100, "declared_items": {STOCK[0]: list(STOCK)}}
    sent, send = collect()
    merchant.handle_item_purchase(
        list(BUY), send, st, 1, Rec(), KEY,
        authsrv.GAME_SMSG_CREATE_NAMED_ITEM,
        authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION,
        purse_persist=lambda s: calls.append(s["purse"]))
    led.ok(calls == [60],
           "the buy calls purse_persist with the moved balance (so --persist "
           "writes it)", f"{calls}")
    # a probe's own gold message clears the sync (ENG-8)
    st = {"purse": 60, "purse_synced": True}
    r1 = authsrv.desync_purse_for_probe(st, 0x0020, 0)
    led.ok(r1 is False and st["purse_synced"] is True,
           "a probe's non-gold message leaves the sync alone")
    r2 = authsrv.desync_purse_for_probe(st, GOLD, 0)
    led.ok(r2 is True and st["purse_synced"] is False and st["purse"] == 60,
           "a probe's own 0x0140 clears purse_synced (the server no longer "
           "knows the client's number) and leaves the purse -- so probemerchant's "
           "+2000 is never refused by the gate", f"{st}")
    st = {"purse": 5, "purse_synced": False}
    sent = buy(st, price=40)
    led.ok(any(op == DEBIT for op, _v in sent),
           "and after the desync an over-priced buy completes, as for any "
           "unsynced client")

    # -- 4. charstore: the optional purse field, no version bump ----------
    led.ok(charstore.STORE_VERSION == 1,
           "the purse is an OPTIONAL field -- STORE_VERSION stayed 1, no "
           "migration (an absent purse reads as the starting purse)")
    base = tempfile.mkdtemp(prefix="purse-test-")
    _saved_find = authsrv.charstore.find_character
    try:
        stt = charstore.Store.open("purse@rurik.invalid", base=base)
        stt.ensure_character(UUID, "Purse Tester")
        stt.save()
        led.ok(stt.character_purse(UUID, default=0) == 0
               and stt.character_purse(UUID, default=99) == 99,
               "an absent purse reads back as the caller's default, never a "
               "silent 0", f"{stt.character_purse(UUID, default=99)}")
        led.ok(stt.set_character_purse(UUID, 85) == 85,
               "set_character_purse returns the stored int on a clean save")
        # reopen: the write survives (persistence across a zone/relaunch)
        st2 = charstore.Store.open("purse@rurik.invalid", base=base)
        led.ok(st2.character_purse(UUID) == 85,
               "set_character_purse persists across a reopen (a zone or a "
               "relaunch) -- the whole point of the field")
        # a STALE write is reported as False, not swallowed (ENG-11): `stt`
        # last wrote 85, `st2` then writes 60 under it, so stt's next save is
        # stale.
        st2.set_character_purse(UUID, 60)
        stale = stt.set_character_purse(UUID, 70)
        led.ok(stale is False
               and charstore.Store.open("purse@rurik.invalid", base=base)
               .character_purse(UUID) == 60,
               "a stale set_character_purse returns False and the disk keeps "
               "the other writer's 60", f"returned {stale!r}")
        st2 = charstore.Store.open("purse@rurik.invalid", base=base)
        # a full grant under --persist writes the purse through the store
        _, sent, gst = grant({"reward_experience": 5, "reward_gold": 25},
                             persist=True, store=st2)
        reread = charstore.Store.open("purse@rurik.invalid", base=base)
        led.ok(reread.character_purse(UUID) == 85,
               "a quest hand-in under --persist writes the new purse (60 + 25) "
               "to disk", f"{reread.character_purse(UUID)}")
        # validation refuses a negative purse
        st2.character_by_uuid(UUID)["purse"] = -1
        try:
            st2.save()
            led.ok(False, "a negative purse is refused at save")
        except ValueError as exc:
            led.ok("purse" in str(exc),
                   "a negative purse is refused at validation, naming the field")
        st2.character_by_uuid(UUID)["purse"] = 85

        # -- 4b. player_purse's LAZY store lookup (the fix pass, R2/ENG-1) --
        disk = charstore.Store.open("purse@rurik.invalid", base=base)
        authsrv.charstore.find_character = \
            lambda uuid, base=None: (disk, disk.character_by_uuid(uuid))
        authsrv.PERSIST = True
        try:
            bare = fresh_state()          # NO charstore_game: REQUEST_ITEMS' state
            p = authsrv.player_purse(bare)
            led.ok(p == 85 and bare.get("charstore_game") is disk,
                   "player_purse with no cached store under --persist looks the "
                   "character up (find_character) and caches the store -- the "
                   "REQUEST_ITEMS-before-REQUEST_PLAYERS ordering cannot zero it",
                   f"purse={p} cached={bare.get('charstore_game') is disk}")
            # the regression both reviews reproduced: pass 1 read 0 here and the
            # next hand-in wrote 0 + 10 over the stored 85.
            _, sent, gst = grant({"reward_gold": 10}, persist=True, state=bare)
            after = charstore.Store.open("purse@rurik.invalid", base=base) \
                .character_purse(UUID)
            led.ok(after == 95 and gst["purse"] == 95,
                   "and a hand-in right after the load ACCUMULATES onto the "
                   "stored 85 (-> 95), not onto a cached 0 (-> 10, the pass-1 "
                   "defect under --persist --no-item-moves)", f"stored {after}")
            # KNOWN-BAD arm: with nothing to find, the starting purse (0) --
            # what a genuinely new character reads.
            authsrv.charstore.find_character = lambda uuid, base=None: (None, None)
            led.ok(authsrv.player_purse(fresh_state()) == 0,
                   "a character no store knows reads the starting purse, 0")
            # -- 4c. load_purse_messages: the burst's arm as a helper -------
            authsrv.charstore.find_character = \
                lambda uuid, base=None: (disk, disk.character_by_uuid(uuid))
            lst = fresh_state()
            msgs = authsrv.load_purse_messages(lst)
            led.ok([(op, v) for op, v, _l in msgs] == [(GOLD, [KEY, 95])]
                   and lst.get("purse_synced") is True,
                   "the load's arm sends 0x0140 [1, stored purse] from the store "
                   "under --persist and marks purse_synced",
                   f"{[(hex(op), v) for op, v, _l in msgs]}")
        finally:
            authsrv.PERSIST = _saved_persist
            authsrv.charstore.find_character = _saved_find
        z = fresh_state(purse=0)
        led.ok(authsrv.load_purse_messages(z) == [] and "purse_synced" not in z,
               "a 0 purse sends NOTHING at load (retail: 55 of 96) and stays "
               "unsynced")
        _saved_load = authsrv.LOAD_PURSE_ENABLED
        authsrv.LOAD_PURSE_ENABLED = False
        try:
            f = fresh_state(purse=60)
            off = authsrv.load_purse_messages(f)
        finally:
            authsrv.LOAD_PURSE_ENABLED = _saved_load
        led.ok(off == [] and "purse_synced" not in f,
               "--no-load-purse sends nothing for a positive purse and does "
               "not mark the sync (the pre-arc load)")
        led.ok([(op, v) for op, v, _l in
                authsrv.load_purse_messages(fresh_state(purse=60))]
               == [(GOLD, [KEY, 60])],
               "and a cached positive purse credits itself with no store at all")
        # the POSITION, as a source lock: after the weapon-set loop, before
        # UPDATE_GOLD_STORAGE, inside the REQUEST_ITEMS burst.
        src = open(authsrv.__file__, encoding="utf-8").read()
        i_call = src.index("in load_purse_messages(state):")
        i_ws = src.rindex('f"WEAPON_SET[{slot}]"', 0, i_call)
        i_ugs = src.index('"UPDATE_GOLD_STORAGE")', i_call)
        led.ok(i_ws < i_call < i_ugs and i_ugs - i_call < 1500,
               "SOURCE LOCK: the load sends the purse right after the weapon-set "
               "loop and before UPDATE_GOLD_STORAGE -- the tape's slot (after the "
               "last 0x0147)", f"ws@{i_ws} call@{i_call} ugs@{i_ugs}")

        # -- 4d. authsrv's wrappers persist a buy and a sell -------------------
        authsrv.PERSIST = True
        try:
            wst = {"purse": 60, "purse_synced": True, "backpack": {0: 5000},
                   "char_uuid": UUID, "charstore_game": disk}
            sent, send = collect()
            authsrv.handle_item_sale([0x804A, 11, 0, [5000], 25, []], send,
                                     wst, 1, Rec())
            on_disk = charstore.Store.open("purse@rurik.invalid", base=base) \
                .character_purse(UUID)
            led.ok(wst["purse"] == 85 and on_disk == 85,
                   "authsrv.handle_item_sale under --persist writes the credited "
                   "purse (60 + 25) to the store", f"state {wst['purse']} disk {on_disk}")
            wst["declared_items"] = {STOCK[0]: list(STOCK)}
            sent, send = collect()
            authsrv.handle_item_purchase(list(BUY), send, wst, 1, Rec())
            on_disk = charstore.Store.open("purse@rurik.invalid", base=base) \
                .character_purse(UUID)
            led.ok(wst["purse"] == 45 and on_disk == 45
                   and any(op == DEBIT for op, _v in sent),
                   "authsrv.handle_item_purchase under --persist writes the "
                   "debited purse (85 - 40) to the store and sends 0x014F",
                   f"state {wst['purse']} disk {on_disk}")
        finally:
            authsrv.PERSIST = _saved_persist
    finally:
        authsrv.charstore.find_character = _saved_find
        shutil.rmtree(base, ignore_errors=True)

    # -- 5. the TAPE (vault-gated; FAILS, not skips, once the tape is here) -
    tape_purse_check()

    return led.verdict()


def _s2c_batches(merged):
    """(t, [(idx, op, values)]) for every same-timestamp s2c batch."""
    out = {}
    for i, (t, d, op, v) in enumerate(merged):
        if d == "s2c":
            out.setdefault(round(t, 6), []).append((i, op, v))
    return out


def tape_purse_check():
    """The witnesses on disk. 20260914T180058: five loads credit
    [own key, 60/60/60/60/85] right after the last 0x0147; the :56301 hand-in
    batch has the retail order and OUR turn_in_quest matches it.
    20260807T143055: a 0-purse gameplay load, chain-closed. With the capture
    directory present every predicate is led.ok (a mismatch is a FAIL); only a
    missing capture is a skip."""
    root = vaultpath.vault_path("captures", "live")
    capdir = os.path.join(root, "20260914T180058")
    if not os.path.isdir(capdir):
        led.skip("the tape 20260914T180058", f"no {capdir} (bare machine)")
    else:
        import livewire
        conns = []
        for gf in livewire.connections(capdir):
            conn, merged, ok = livewire.decode_conn(capdir, gf)
            conns.append((merged[0][0] if merged else 1e9, conn, merged, ok))
        conns.sort(key=lambda c: c[0])
        led.ok(len(conns) == 5 and all(ok for _t, _c, _m, ok in conns),
               "TAPE: 20260914T180058 has 5 game connections and every one "
               "decodes to the last byte", f"{[(c, ok) for _t, c, _m, ok in conns]}")
        loads = []
        for _t0, conn, merged, _ok in conns:
            s2c = [(i, op, v) for i, (t, d, op, v) in enumerate(merged) if d == "s2c"]
            key44 = next((v[1] for _i, op, v in s2c if op == 0x0144), None)
            last47 = max((i for i, op, _v in s2c if op == 0x0147), default=None)
            nxt = merged[last47 + 1] if last47 is not None else None
            if nxt is not None and nxt[1] == "s2c" and nxt[2] == 0x0140:
                loads.append((conn, nxt[3][1], nxt[3][2], nxt[3][1] == key44))
            else:
                loads.append((conn, None, None, False))
        led.ok([l[2] for l in loads] == [60, 60, 60, 60, 85]
               and all(l[3] for l in loads),
               "TAPE: every load's message right after the last 0x0147 is "
               "0x0140 [that connection's own 0x0144 key, purse], purses "
               "60/60/60/60/85 in wall-clock order (60 + 25 = 85 across the zone)",
               f"{loads}")
        led.ok(all(purse.load_credit(KEY, l[2]) == [KEY, l[2]] for l in loads),
               "and load_credit builds the same shape for each on our key")
        # THE HAND-IN on :56301: the batch that shares a timestamp with the
        # 0x0140 whose preceding c2s is 0x003B.
        handin = None
        for _t0, conn, merged, _ok in conns:
            for i, (t, d, op, v) in enumerate(merged):
                if d != "s2c" or op != 0x0140:
                    continue
                j = i
                while j > 0 and merged[j][1] != "c2s":
                    j -= 1
                if merged[j][1] == "c2s" and merged[j][2] == 0x003B:
                    batch = _s2c_batches(merged)[round(t, 6)]
                    handin = (conn, t, v, [(op2, v2) for _k, op2, v2 in batch])
        led.ok(handin is not None and handin[0].startswith("10.0.0.210:56301")
               and handin[2][1:] == [2, 25],
               "TAPE: the one 0x003B-preceded 0x0140 is [2, 25] on :56301",
               f"{None if handin is None else (handin[0], handin[1], handin[2])}")
        if handin is not None:
            tape_ops = handin[3]
            kinds = reward_kinds(tape_ops)
            xps = [v[-1] for op, v in tape_ops if op == XP and v[-2] == 0]
            led.ok(kinds == ["remove", "xp", "gold", "remove", "unlist"]
                   and xps == [250] and retail_order(kinds),
                   "TAPE: the hand-in batch is 0x0052 · 0x00EE [0, 250] · "
                   "0x0140 [2, 25] · 0x0052 · 0x004A in that order (the second "
                   "0x0052 is the doubling our single-remove experiment omits)",
                   f"{kinds} xp={xps}")
            qfam = [op for op, _v in tape_ops if op in QUEST_FAMILY]
            led.ok(qfam and qfam[-1] == UNLIST and qfam.count(UNLIST) == 1,
                   "TAPE: 0x004A is the LAST quest-family message of the batch "
                   "(the 0x009F/0x0080/0x007E dialog lines after it are not the "
                   "quest family)", f"{[hex(o) for o in qfam]}")
            led.ok(any(op == XP and v[-2:] == [10, 0] for op, v in tape_ops),
                   "TAPE: the batch also carries 0x00EE [10, 0], which stays "
                   "UNREAD and is not sent by us")
            # OURS against the TAPE: the four kinds in the same relative order.
            sent, send = collect()
            st = fresh_state(quests={1463})
            saved = authsrv.REWARD_IN_FRAME
            authsrv.REWARD_IN_FRAME = True
            try:
                authsrv.turn_in_quest(send, st, 1463,
                                      {"reward_experience": 250,
                                       "reward_gold": 25}, 0)
            finally:
                authsrv.REWARD_IN_FRAME = saved
            ours = reward_kinds(sent)

            def dedupe(k):
                # the tape's doubled 0x0052 collapses to one for the comparison;
                # the doubling is the recorded, deferred difference.
                out = []
                for x in k:
                    if not (x == "remove" and out and "remove" in out):
                        out.append(x)
                return out

            led.ok(dedupe(kinds) == ours == ["remove", "xp", "gold", "unlist"],
                   "OURS vs TAPE: turn_in_quest's remove/xp/gold/unlist order "
                   "equals the tape's (with the tape's doubled 0x0052 collapsed "
                   "-- the one recorded difference)", f"tape {kinds} ours {ours}")
            gold_ours = [v for op, v in sent if op == GOLD]
            led.ok(gold_ours == [[KEY, 25]] and [v for op, v in tape_ops if op == GOLD][0][1:] == [2, 25],
                   "OURS vs TAPE: the same amount on the wire (25), ours on key 1, "
                   "the tape's on its connection's key 2")
            # KNOWN-BAD 1: pass 1's order (the flag off) does NOT match the tape.
            sent_bad, send_bad = collect()
            authsrv.REWARD_IN_FRAME = False
            try:
                authsrv.turn_in_quest(send_bad, fresh_state(quests={1463}), 1463,
                                      {"reward_experience": 250, "reward_gold": 25}, 0)
            finally:
                authsrv.REWARD_IN_FRAME = saved
            led.ok(dedupe(kinds) != reward_kinds(sent_bad),
                   "KNOWN-BAD: the pass-1 order (--no-reward-in-frame) does NOT "
                   "equal the tape's -- the comparison can go red",
                   f"{reward_kinds(sent_bad)}")
            # KNOWN-BAD 2: a SABOTAGED tape (gold moved before the xp) reddens
            # the tape predicate itself.
            sab = list(tape_ops)
            gi = next(k for k, (op, _v) in enumerate(sab) if op == GOLD)
            xi = next(k for k, (op, v) in enumerate(sab) if op == XP and v[-2] == 0)
            sab.insert(xi, sab.pop(gi))
            led.ok(not retail_order(reward_kinds(sab)),
                   "KNOWN-BAD: a sabotaged tape with the gold before the xp FAILS "
                   "the retail-order predicate", f"{reward_kinds(sab)}")
    # THE 0-PURSE LOAD, chain-closed: 20260807T143055.
    capdir0 = os.path.join(root, "20260807T143055")
    if not os.path.isdir(capdir0):
        led.skip("the tape 20260807T143055 (0-purse load)", f"no {capdir0}")
    else:
        import livewire
        rows = {}
        for gf in livewire.connections(capdir0):
            conn, merged, _ok = livewire.decode_conn(capdir0, gf)
            port = conn.split("->")[0].split(":")[-1]
            s2c = [(i, op, v) for i, (t, d, op, v) in enumerate(merged) if d == "s2c"]
            has_family = any(op == 0x0144 for _i, op, _v in s2c) \
                and sum(1 for _i, op, _v in s2c if op == 0x0147) == 4
            last47 = max((i for i, op, _v in s2c if op == 0x0147), default=None)
            nxt = merged[last47 + 1] if last47 is not None else None
            load = nxt[3][2] if nxt is not None and nxt[1] == "s2c" and nxt[2] == 0x0140 else None
            credits = []
            for i, (t, d, op, v) in enumerate(merged):
                if d == "s2c" and op == 0x0140 and not (last47 is not None and i == last47 + 1):
                    j = i
                    while j > 0 and merged[j][1] != "c2s":
                        j -= 1
                    credits.append((hex(merged[j][2]), v[2]))
            rows[port] = (has_family, load, credits)
        r0, r1 = rows.get("60935"), rows.get("62994")
        led.ok(r0 is not None and r0[0] and r0[1] is None and ("0x3b", 10) in r0[2],
               "TAPE: :60935 loads the full inventory family with NO 0x0140 "
               "(a 0-purse gameplay load) and earns 0x0140 [k, 10] at a 0x003B "
               "hand-in", f"{r0}")
        led.ok(r1 is not None and r1[0] and r1[1] == 10,
               "TAPE: the next connection :62994 loads 0x0140 [k, 10] -- the "
               "chain closes from 0, so skip-at-0 and a 0 starting purse are "
               "OBSERVED, not reasoned", f"{r1}")


if __name__ == "__main__":
    sys.exit(main())
