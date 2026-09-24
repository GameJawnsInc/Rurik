"""The carried purse -- DESKWORK-D9. purse.py, the load credit, the quest gold,
the merchant's buy/sell moves, and persistence across a zone.

WHAT THIS CHECKS, beyond round-trips:
  * purse.py's arithmetic and the load-credit builder (skip on 0, a positive
    credit keyed by the inventory stream key), with a known-bad and a vacuity
    guard.
  * grant_quest_reward pays reward_gold as 0x0140 AFTER the experience 0x00EE
    -- the tape's order -- as a DELTA (the reward amount, not the new balance),
    with the known-bad arms the task names: gold missing (flag off), gold before
    the xp, and a balance sent where a delta belongs.
  * the merchant's buy debits and sell credits the purse (the wire already moves
    it via 0x014F/0x0140; the server tracks the balance), and an unaffordable
    buy sends NOTHING (the client gates locally; retail's refusal is NOT FOUND).
  * persistence across a zone on a TEMP store (never the real vault), and that
    the optional `purse` field did NOT bump STORE_VERSION.
  * (vault-gated) the tape itself: on 20260914T180058 the load's 0x0140 follows
    the last 0x0147 and the hand-in's 0x0140 follows the xp 0x00EE.

Everything bare runs against temp stores and in-memory state; nothing binds a
port, launches a client, or touches vault/state.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks       # noqa: E402
import purse        # noqa: E402
import charstore    # noqa: E402
import merchant     # noqa: E402
import authsrv      # noqa: E402
import vaultpath    # noqa: E402

# Floor 24 from the bare-machine green run (RURIK_VAULT at an empty dir): the
# arithmetic, the grant, the merchant and the temp-store persistence. The tape
# section (section 5) adds 6 more when the vault is present and LEDGER.skips on
# a bare machine, so 24 is the count a healthy run cannot fall below.
led = checks.Ledger("the carried purse (DESKWORK-D9)", floor=24)

UUID = "22222222222222222222222222222222"
KEY = authsrv.PLAYER_INVENTORY_KEY
GOLD = merchant.GAME_SMSG_GOLD_CREDIT      # 0x0140
DEBIT = merchant.GAME_SMSG_GOLD_DEBIT      # 0x014F
XP = authsrv.GAME_SMSG_AGENT_KILL_REWARD   # 0x00EE

# A stock row in named_item()'s field order (from test_purchase), value 5.
STOCK = [40, 0x8000005B, 7, 19, 11, 0, 0, 0x20001006, 5, 2440, 1, "x", []]
BUY = [0x804D, 1, 40, [], b"", 0, [40], b"\x01"]


class Rec:
    def event(self, kind, **kw):
        pass


def collect():
    sent = []
    return sent, (lambda op, values, label="", **kw: sent.append((op, list(values))))


def main():
    # -- 1. purse.py arithmetic and the load-credit builder ---------------
    led.ok(purse.STARTING_PURSE == 0 and purse.start() == 0,
           "a character with no stored purse starts at 0 (RECONSTRUCTION: no "
           "capture shows a new character's first purse)")
    led.ok(purse.load_credit(KEY, 0) is None,
           "load_credit SKIPS a 0 purse -- no gameplay load in the corpus "
           "carried a 0-gold credit, and add-0 is a no-op on the client's 0 purse")
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

    def grant(row, persist=False, store=None):
        sent, send = collect()
        st = {"quests": set(), "objectives_done": set(),
              "quests_completed": set(), "agents": {}, "char_uuid": UUID}
        if store is not None:
            st["charstore_game"] = store
        authsrv.PERSIST = persist
        try:
            paid = authsrv.grant_quest_reward(send, st, 1463, row, 0)
        finally:
            authsrv.PERSIST = _saved_persist
        return paid, sent, st

    _, sent, st = grant({"reward_experience": 100, "reward_gold": 10})
    ops = [op for op, _v in sent]
    gold = [v for op, v in sent if op == GOLD]
    led.ok(gold == [[KEY, 10]] and st.get("purse") == 10,
           "reward_gold=10 pays 0x0140 [key, 10] and the purse holds 10",
           f"gold={gold} purse={st.get('purse')}")
    led.ok(GOLD in ops and XP in ops and ops.index(GOLD) > ops.index(XP),
           "the gold 0x0140 comes AFTER the experience 0x00EE -- the tape's "
           "order", f"{[hex(o) for o in ops]}")
    # KNOWN-BAD (gold before the xp): the same predicate on a REVERSED op list
    # must fail, or it is not really testing the order.
    _rev = list(reversed(ops))
    led.ok(not (_rev.index(GOLD) > _rev.index(XP)),
           "KNOWN-BAD: the order predicate FAILS on a reversed batch (gold "
           "before xp) -- it distinguishes the two")
    # KNOWN-BAD (a balance where a delta belongs): the credit is the DELTA
    # (reward_gold), never the resulting balance. Start with a purse so the two
    # differ.
    _, sent2, st2 = grant({"reward_experience": 5, "reward_gold": 10})
    # give it a starting purse first
    sent3, send3 = collect()
    st3 = {"quests": set(), "agents": {}, "char_uuid": UUID, "purse": 25}
    authsrv.PERSIST = False
    authsrv.grant_quest_reward(send3, st3, 1463,
                               {"reward_experience": 5, "reward_gold": 10}, 0)
    authsrv.PERSIST = _saved_persist
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

    # -- 4. charstore: the optional purse field, no version bump ----------
    led.ok(charstore.STORE_VERSION == 1,
           "the purse is an OPTIONAL field -- STORE_VERSION stayed 1, no "
           "migration (an absent purse reads as the starting purse)")
    base = tempfile.mkdtemp(prefix="purse-test-")
    try:
        stt = charstore.Store.open("purse@rurik.invalid", base=base)
        stt.ensure_character(UUID, "Purse Tester")
        stt.save()
        led.ok(stt.character_purse(UUID, default=0) == 0
               and stt.character_purse(UUID, default=99) == 99,
               "an absent purse reads back as the caller's default, never a "
               "silent 0", f"{stt.character_purse(UUID, default=99)}")
        stt.set_character_purse(UUID, 85)
        # reopen: the write survives (persistence across a zone/relaunch)
        st2 = charstore.Store.open("purse@rurik.invalid", base=base)
        led.ok(st2.character_purse(UUID) == 85,
               "set_character_purse persists across a reopen (a zone or a "
               "relaunch) -- the whole point of the field")
        # a full grant under --persist writes the purse through the store
        st2.character_by_uuid(UUID)["purse"] = 60
        st2.save()
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
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)

    # -- 5. the TAPE (vault-gated) ----------------------------------------
    tape_purse_check()

    return led.verdict()


def tape_purse_check():
    """The witness on disk: 20260914T180058 -- the load's 0x0140 follows the
    last 0x0147, and the hand-in's 0x0140 follows the xp 0x00EE."""
    root = vaultpath.vault_path("captures", "live")
    capdir = os.path.join(root, "20260914T180058")
    if not os.path.isdir(capdir):
        led.skip("the tape load 0x0140", f"no {capdir} (bare machine)")
        led.skip("the tape hand-in 0x0140", f"no {capdir} (bare machine)")
        return
    import livewire
    seen_load = seen_handin = False
    for gf in livewire.connections(capdir):
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        s2c = [(op, v) for _t, d, op, v in merged if d == "s2c"]
        ops = [op for op, _v in s2c]
        # THE LOAD: the first 0x0140 follows the last 0x0147 before it.
        if 0x0140 in ops:
            i140 = ops.index(0x0140)
            prior_147 = [i for i, op in enumerate(ops[:i140]) if op == 0x0147]
            if prior_147 and i140 == prior_147[-1] + 1:
                key, pu = s2c[i140][1][1], s2c[i140][1][2]
                led.ok(pu > 0 and purse.load_credit(authsrv.PLAYER_INVENTORY_KEY, pu)
                       == [authsrv.PLAYER_INVENTORY_KEY, pu],
                       "TAPE: the load's 0x0140 follows the last 0x0147 and "
                       "carries [stream key, purse] -- our load_credit builds "
                       "the same shape on our key",
                       f"tape [{key}, {pu}] at load")
                seen_load = True
        # THE HAND-IN: a 0x0140 gold credit whose prior 0x00EE is the xp delta.
        # Decoded values carry the msg header as v[0], so 0x00EE is
        # [238, field1, field2] and the xp delta is field1==0, field2>0; the
        # gold 0x0140 is [320, key, amount].
        for i, (op, v) in enumerate(s2c):
            if op != 0x0140 or i == 0:
                continue
            xp_ee = [j for j in range(i) if s2c[j][0] == 0x00EE
                     and len(s2c[j][1]) >= 3 and s2c[j][1][1] == 0
                     and s2c[j][1][2] > 0]
            if not xp_ee:
                continue
            near = any(s2c[k][0] == 0x004A for k in range(i, min(i + 8, len(s2c))))
            if near and v[2] > 0:
                led.ok(s2c[xp_ee[-1]][1][2] > 0 and v[2] > 0
                       and xp_ee[-1] < i,
                       "TAPE: the hand-in's gold 0x0140 [key, amount] follows "
                       "the experience 0x00EE [0, xp] and precedes 0x004A -- the "
                       "order grant_quest_reward now matches",
                       f"xp {s2c[xp_ee[-1]][1][2]}, gold {v[2]}")
                seen_handin = True
                break
    if not seen_load:
        led.skip("the tape load 0x0140", "no load-purse credit decoded")
    if not seen_handin:
        led.skip("the tape hand-in 0x0140", "no hand-in credit decoded")


if __name__ == "__main__":
    sys.exit(main())
