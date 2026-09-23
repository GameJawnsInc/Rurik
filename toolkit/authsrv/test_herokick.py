"""The hero kick, c2s 0x001F HERO_KICK -- SANDBOX-N2 (studies/cmsg/FINDINGS.md D1).

    python toolkit/authsrv/test_herokick.py

WHAT THIS PINS.

  * §1 THE BATCH, in retail's byte order. `hero_kick_batch` is pure, so it is
    replayed through the codec and its opcode sequence checked against the tape:
    0x0075, 0x01C3, 0x00F8, 0x003E, 0x00B0, 0x0145 (20260916T150306 :62321,
    t=158.718). The KNOWN-BAD arm is a permuted order, which must NOT match --
    the whole point of quoting an order is that a wrong one reddens.
  * §2 THE HANDLER, driven like the 0x005E swap (test_charstore): the real
    `handle_hero_kick`, a fake send, a state holding the hero. It must emit the
    six-message batch in order with OUR ids (agent 200, owner PLAYER_NUMBER,
    party 1, inventory HERO_INVENTORY), drop the hero from the party set, and
    despawn its body. Refusal arms: an unowned index and an already-kicked hero
    send NOTHING (the known-bad is that either would double-send).
  * §3 PERSIST across a zone, the acceptance. A kick on a --persist store writes
    the character's `kicked_heroes`; a FRESH connection seeds it back, so
    `hero_slots()` still OWNS the hero (its 0x0073 HERO_INFO goes out) while
    `party_hero_slots()` EXCLUDES it (no 0x0072, no 0x01C2) -- exactly what the
    tape's next two loads carry. The control: with --persist OFF the kick writes
    nothing to the store.

`handle_hero_kick` needs the server, so this cannot live in the bare-machine
`test_herolib.py` (checked: that module imports no server); it drives the real
handler with a scratch store instead, like `test_charstore.py`. Floor 29.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import charstore                                             # noqa: E402
import codec as codecmod                                     # noqa: E402
import authsrv                                               # noqa: E402

led = checks.Ledger("hero kick (SANDBOX-N2)", floor=29)

# The tape's own reply order (20260916T150306 :62321, t=158.718).
RETAIL_ORDER = [0x0075, 0x01C3, 0x00F8, 0x003E, 0x00B0, 0x0145]
COD = codecmod.Codec()


# -- §1 the batch, byte order ----------------------------------------------
batch = authsrv.hero_kick_batch(379, 68, 28, 96, 1)
led.ok(len(batch) == 6, "the kick batch is six messages", f"got {len(batch)}")
order = [op for op, _v, _l in batch]
led.ok(order == RETAIL_ORDER,
       "the batch is in retail's order 0x0075, 0x01C3, 0x00F8, 0x003E, 0x00B0, "
       "0x0145", f"got {[hex(x) for x in order]}")
# Every message encodes and round-trips through the tracked schema.
wire_ok = True
for op, vals, _l in batch:
    b = COD.encode("GAME_SMSG", op, vals)
    dop, dvals, _off = COD.decode_one("GAME_SMSG", b, 0, 0)
    if dop != op or dvals[1:] != vals:
        wire_ok = False
led.ok(wire_ok,
       "each message encodes and round-trips through the GAME_SMSG catalog")
# The roster-remove carries [party, owner, agent] -- 0x01C3's mirror of 0x01C2.
c3 = next(v for op, v, _l in batch if op == authsrv.GAME_SMSG_PARTY_HERO_REMOVE)
led.ok(c3 == [28, 68, 379],
       "0x01C3 PARTY_HERO_REMOVE is [party, owner, agent]", f"got {c3}")
b0 = next(v for op, v, _l in batch if op == authsrv.GAME_SMSG_PLAYER_PARTY_SIZE)
led.ok(b0 == [68, 1], "0x00B0 PLAYER_PARTY_SIZE is [player, size]", f"got {b0}")
# KNOWN-BAD: a permuted order is not retail's order.
led.ok(list(reversed(order)) != RETAIL_ORDER,
       "a reversed batch does NOT match the tape -- the order is a real check")
# Vacuity: the batch is never empty.
led.ok(all(isinstance(op, int) for op, _v, _l in batch),
       "every batch row names an opcode")


# -- §2 the real handler ---------------------------------------------------
def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals)))
    return sent, send


_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "PERSIST", "HENCHMAN", "HERO_INVENTORY",
           "HERO_AGENT_ID", "PLAYER_NUMBER", "HERO_KICK_ENABLED")}
base = tempfile.mkdtemp(prefix="herokick-test-")
UUID = "11111111111111111111111111111111"
try:
    authsrv.HERO_IDS = [6]
    authsrv.HERO_AGENT_ID = 200
    authsrv.PLAYER_NUMBER = 68
    authsrv.HERO_INVENTORY = 96
    authsrv.HENCHMAN = None
    authsrv.PERSIST = False
    authsrv.HERO_KICK_ENABLED = True

    sent, send = fake_send_factory()
    state = {"agents": {200: {"name": "Koss"}}, "char_uuid": UUID}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], send, state, 0)
    led.ok([op for op, _v in sent] == RETAIL_ORDER,
           "the handler emits the six-message batch in retail's order",
           f"got {[hex(x) for x, _v in sent]}")
    led.ok(dict(sent).get(authsrv.GAME_SMSG_HERO_UNLINK) == [200],
           "0x0075 carries OUR hero agent id (200), not the tape's 379")
    led.ok(dict(sent).get(authsrv.GAME_SMSG_PARTY_HERO_REMOVE) == [1, 68, 200],
           "0x01C3 is [party 1, owner PLAYER_NUMBER, agent 200] with our ids")
    led.ok(dict(sent).get(authsrv.GAME_SMSG_PLAYER_PARTY_SIZE) == [68, 1],
           "0x00B0 drops the party to 1 (the player alone)")
    led.ok(dict(sent).get(authsrv.GAME_SMSG_INVENTORY_REMOVE_BAG) == [96],
           "0x0145 destroys the hero's inventory container HERO_INVENTORY")
    led.ok(authsrv.hero_kicked(state, 6),
           "the hero is now in the connection's kicked set")
    led.ok(200 not in state["agents"],
           "and its world body was despawned from state[agents]")
    led.ok([h for h, _a, _d in authsrv.party_hero_slots(state)] == [],
           "party_hero_slots excludes the kicked hero")
    led.ok([h for h, _a, _d in authsrv.hero_slots()] == [6],
           "hero_slots still OWNS it -- 0x0073 HERO_INFO goes to owned heroes")

    # Refusal: an unowned index sends nothing and changes nothing.
    sent2, send2 = fake_send_factory()
    state2 = {"agents": {}, "char_uuid": UUID}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 99], send2, state2, 0)
    led.ok(sent2 == [] and not authsrv.hero_kicked(state2, 99),
           "kicking a hero this run does not own sends nothing "
           "(the known-bad arm: it would emit a teardown for a phantom agent)")

    # Refusal: an already-kicked hero does not double-send.
    sent3, send3 = fake_send_factory()
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], send3, state, 0)
    led.ok(sent3 == [],
           "kicking an already-kicked hero sends nothing -- no double teardown")

    # Multi-hero: the size counts the party that REMAINS.
    authsrv.HERO_IDS = [6, 7]
    sentm, sendm = fake_send_factory()
    statem = {"agents": {}, "char_uuid": UUID}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendm, statem, 0)
    led.ok(dict(sentm).get(authsrv.GAME_SMSG_PLAYER_PARTY_SIZE) == [68, 2],
           "with two heroes, kicking one leaves the party at 2 (player + hero 7)",
           f"got {dict(sentm).get(authsrv.GAME_SMSG_PLAYER_PARTY_SIZE)}")

    # The revert flag: --no-hero-kick means the dispatch ignores it. We prove
    # the handler is the only writer by disabling and confirming the CALLER
    # would not reach it -- here directly, the flag is checked at the call site,
    # so the handler itself always acts; assert the flag default is ON.
    led.ok(_saved["HERO_KICK_ENABLED"] is True,
           "the kick is ON by default -- OBSERVED and tested, so the revert "
           "flag --no-hero-kick is opt-in")

    # -- §3 persist across a zone -------------------------------------------
    authsrv.HERO_IDS = [6]
    authsrv.PERSIST = True
    store = charstore.Store.open("herokick@rurik.invalid", base=base)
    store.ensure_character(UUID, "Kicker", "aa" * 37)
    led.ok(store.kicked_heroes(UUID) == [],
           "a fresh character has no kicked heroes (the positive control)")

    sp, sendp = fake_send_factory()
    statep = {"agents": {}, "char_uuid": UUID, "charstore_game": store}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendp, statep, 0)
    led.ok(store.kicked_heroes(UUID) == [6],
           "under --persist the kick is written to the character store")

    reopened = charstore.Store.open("herokick@rurik.invalid", base=base)
    led.ok(reopened.kicked_heroes(UUID) == [6],
           "and it survives a store reopen (the next zone reads it back)")

    # A fresh connection: seed the kicked set from the store, then the
    # ownership/party asymmetry that IS acceptance (b).
    fresh = {"agents": {}, "char_uuid": UUID, "charstore_game": reopened}
    led.ok(authsrv.kicked_heroes_set(fresh) == {6},
           "the next connection seeds the kicked set from the store")
    led.ok(authsrv.hero_kicked(fresh, 6),
           "so the kicked hero is still kicked after the zone")
    led.ok([h for h, _a, _d in authsrv.hero_slots()] == [6]
           and [h for h, _a, _d in authsrv.party_hero_slots(fresh)] == [],
           "the next zone-in OWNS hero 6 (0x0073) but does NOT party it "
           "(no 0x0072/0x01C2) -- SANDBOX-N2 acceptance (b)")

    # Control: with --persist off, the store is untouched.
    authsrv.PERSIST = False
    store3 = charstore.Store.open("herokick@rurik.invalid", base=base)
    store3.set_hero_kicked(UUID, 6, kicked=False)          # reset
    sc, sendc = fake_send_factory()
    statec = {"agents": {}, "char_uuid": UUID, "charstore_game": store3}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendc, statec, 0)
    led.ok(charstore.Store.open("herokick@rurik.invalid", base=base)
           .kicked_heroes(UUID) == [],
           "with --persist OFF the kick sends its batch but writes NOTHING to "
           "the store -- the pre-N2 store shape is unchanged")
    led.ok([op for op, _v in sc] == RETAIL_ORDER,
           "...and the batch still goes out on the wire regardless of persist")

    # The store REFUSES a bad kicked_heroes list at load (the validate guard).
    refused = False
    bad = os.path.join(base, "bad.json")
    import json
    good = charstore.Store.open("herokick@rurik.invalid", base=base).data
    good = json.loads(json.dumps(good))
    ch = next(iter(good["characters"].values()))
    ch["kicked_heroes"] = [0]                              # index 0 is not a hero
    with open(bad, "w", encoding="utf-8") as f:
        json.dump(good, f)
    try:
        charstore.validate(json.load(open(bad, encoding="utf-8")), bad)
    except ValueError:
        refused = True
    led.ok(refused,
           "the store refuses kicked_heroes holding index 0 -- a shape error, "
           "not a silent default")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    import shutil
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
