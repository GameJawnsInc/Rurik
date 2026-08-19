r"""Answering the merchant: BUY (0x004D) and SELL (0x004A), in ArenaNet's order.

    python toolkit/authsrv/test_purchase.py

WHY THE ORDER IS ASSERTED AND NOT JUST THE CONTENTS. Retail's reply is four
messages in one frame and the client cares which comes first: **pay, mint,
place, confirm** -- `0x014F` debit, `0x0161` declare, `0x013E` move, `0x00CC`
done. The first version of this arm sent that nearly backwards and the client
died on `Assertion: item`, `ItCliApi.cpp(1883)`, which is `0x013E`'s own
argument check failing on its first lookup because the item did not exist yet.

AND THE BAD ORDER WAS MANUFACTURED BY THE TOOL THAT READ IT, which is the part
worth keeping: all four messages share one segment timestamp, and the timeline
script sorted whole tuples, so the tie fell through to comparing the OPCODE
NUMBER -- 0x00CC < 0x013E < 0x014F < 0x0161. Ascending opcodes wearing the
costume of a finding, and it survived into a study document and a commit
message before the client refuted it. **Within a single frame, byte offset is
the only ordering evidence there is.** The literals below are offsets for that
reason.

WHAT IT IS CHECKED AGAINST. Two real requests, written into this file as
literals so a change to the handler cannot quietly redefine what a request is:

    ours    0x4D [1, 10, [], b'', 0, [40],   b'\x01']   20260819T160503
    retail  0x4D [1, 40, [], b'', 0, [2474], b'\x01']   20260819T132414

Same shape from both sides. Field 1 is the transaction KIND (1 = buy; the sell
message carries 11), field 2 the QUOTED price, field 6 the item ids, field 7 one
quantity byte each.

THE REFUSALS ARE HALF THE FILE, and each has a positive control beside it. The
client has already decided locally that it can afford the item and has room for
it, so anything we cannot answer is a disagreement between its model and ours --
the case where a plausible-looking reply is worse than none. `n = 1` is stated
where it applies: `0x014F` has exactly one sighting in the whole live corpus,
because one purchase was ever made in front of a capture.

Standard library only. No vault, no socket, no client.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import authsrv  # noqa: E402
import checks  # noqa: E402

LEDGER = checks.Ledger("answering a transaction", floor=27)

# The two requests, verbatim. values[0] is the header, as everywhere in the
# dispatch chain.
OURS = [0x804D, 1, 10, [], b"", 0, [40], b"\x01"]
RETAIL = [0x804D, 1, 40, [], b"", 0, [2474], b"\x01"]
# A stock row in named_item()'s field order: id, file, type, tint, colors,
# materials, unk1, flags, value, model, quantity, name, modifiers.
STOCK = [40, 0x8000005B, 7, 19, 11, 0, 0, 0x20001006, 5, 2440, 1, "x", []]


class Rec:
    def __init__(self):
        self.events = []

    def event(self, kind, **kw):
        self.events.append((kind, kw))


def run(request, declared=None, state=None, fn=None):
    """(sent, state, rec) for one request. `sent` is [(opcode, values)]."""
    sent = []
    state = state if state is not None else {}
    state.setdefault("declared_items",
                     dict(declared if declared is not None
                          else {STOCK[0]: list(STOCK)}))
    rec = Rec()
    (fn or authsrv.handle_item_purchase)(
        request, lambda op, values, label, quiet=False: sent.append(
            (op, list(values))), state, 1, rec)
    return sent, state, rec


def main():
    # ---- 1. the happy path, both requests ------------------------------
    for who, req in (("ours", OURS), ("retail-shaped", RETAIL)):
        stock = dict(STOCK_FOR(req))
        sent, state, rec = run(req, declared=stock)
        ops = [op for op, _v in sent]
        LEDGER.ok(ops == [authsrv.GAME_SMSG_GOLD_DEBIT,
                          authsrv.GAME_SMSG_CREATE_NAMED_ITEM,
                          authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION,
                          authsrv.GAME_SMSG_TRANSACTION_DONE],
                  f"{who}: four messages -- pay, mint, place, confirm",
                  f"{[hex(o) for o in ops]}, retail's order at offsets 36392 / "
                  f"36400 / 36452 / 36463. DECLARE BEFORE MOVE: the reverse "
                  f"killed the client on ItCliApi.cpp(1883), 0x013E's own "
                  f"first argument check")
        by = dict(sent)
        LEDGER.ok(by[authsrv.GAME_SMSG_TRANSACTION_DONE] == [req[1]],
                  f"{who}: 0x00CC echoes the transaction kind",
                  f"{by[authsrv.GAME_SMSG_TRANSACTION_DONE]} for kind "
                  f"{req[1]}. The sell path carries 11 and gets 11 back, 9/9 "
                  f"in the corpus")
        LEDGER.ok(by[authsrv.GAME_SMSG_GOLD_DEBIT] ==
                  [authsrv.PLAYER_INVENTORY_KEY, req[2]],
                  f"{who}: 0x014F debits the QUOTED price, on the inventory key",
                  f"{by[authsrv.GAME_SMSG_GOLD_DEBIT]}. n = 1 in the corpus -- "
                  f"one purchase was ever captured -- so this is OBSERVED-once "
                  f"and the mirror of 0x0140's credit, not corroborated")
        moved = by[authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION]
        minted = by[authsrv.GAME_SMSG_CREATE_NAMED_ITEM]
        LEDGER.ok(moved[1] == minted[0] and moved[1] != req[6][0],
                  f"{who}: buying MINTS a new id, and the move names it",
                  f"stock {req[6][0]} -> item {minted[0]}. Retail did the same "
                  f"(2474 -> 4130): merchant stock is a catalogue, not the "
                  f"goods")
        LEDGER.ok(moved[2] == authsrv.BACKPACK_BAG_ID and moved[3] == 0,
                  f"{who}: it lands in the BACKPACK, first free slot",
                  f"bag {moved[2]} slot {moved[3]}. Retail put its bought item "
                  f"in the backpack too, and a client with no backpack refuses "
                  f"the purchase locally without sending anything")
        LEDGER.ok(minted[1:10] == list(STOCK_FOR(req)[req[6][0]])[1:10],
                  f"{who}: the copy keeps every declared field but the id",
                  "file id, type, dyes, flags, value and model all survive; a "
                  "copy that dropped them would render as a different item")

    # ---- 2. quantity comes off the wire --------------------------------
    req = list(OURS)
    req[7] = b"\x05"
    sent, _s, _r = run(req)
    minted = dict(sent)[authsrv.GAME_SMSG_CREATE_NAMED_ITEM]
    LEDGER.ok(minted[10] == 5,
              "the quantity byte is read, not assumed",
              f"quantity {minted[10]} from b'\\x05'. One byte per item id; "
              f"assuming 1 would silently short a stack purchase")

    # ---- 3. slots advance --------------------------------------------
    state = {}
    run(OURS, state=state)
    sent2, state, _r = run(OURS, state=state)
    LEDGER.ok(dict(sent2)[authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION][3] == 1,
              "a second purchase takes the NEXT slot",
              "two items in one slot is one item; the slot cursor is per "
              "connection state")
    LEDGER.ok(dict(sent2)[authsrv.GAME_SMSG_CREATE_NAMED_ITEM][0]
              != authsrv.PURCHASED_ITEM_ID_BASE,
              "and a fresh id, not a reused one",
              "reusing an id would overwrite the first item's declaration "
              "rather than error")

    # ---- 4. refusals, each with the control beside it -------------------
    LEDGER.ok(run(OURS)[0], "CONTROL: the fixture DOES produce a purchase",
              "without this every refusal below could pass because the "
              "fixture is broken rather than because the guard works")
    LEDGER.ok(not run(OURS, declared={})[0],
              "an UNDECLARED item is refused",
              "the client may only buy what this session declared; anything "
              "else is a disagreement about what exists")
    bad_kind = list(OURS)
    bad_kind[1] = 11
    LEDGER.ok(not run(bad_kind)[0],
              "the SELL kind (11) is refused on this message",
              "selling has its own opcode (0x004A) and its own reply; "
              "answering it here would ADD an item and take money for it")
    empty = list(OURS)
    empty[6] = []
    LEDGER.ok(not run(empty)[0],
              "a request naming no item is refused",
              "rather than raising IndexError -- a handler that dies takes "
              "the connection with it, which is how one loop variable cost "
              "two runs on 2026-08-19")
    LEDGER.ok(not run(OURS[:3])[0],
              "and a TRUNCATED request is refused, not indexed into",
              "same lesson, from the other side")
    full = {"backpack": {i: 900 + i
                         for i in range(authsrv.BACKPACK_SLOT_COUNT)}}
    LEDGER.ok(not run(OURS, state=full)[0],
              "a full backpack is refused",
              f"{authsrv.BACKPACK_SLOT_COUNT} slots is the type-1 bag's own "
              f"capacity, measured 49/49 in the live corpus")


    # ---- 6. SELL: remove, pay, confirm ----------------------------------
    # Retail's, all 8 identical: 0x004A [11, 0, [item], price, []] answered by
    # 0x014D -> 0x0140 -> 0x00CC [11], read BY BYTE OFFSET. Different shape AND
    # different price index from the buy message, which is the trap this
    # section exists to hold shut.
    SELL = [0x804A, 11, 0, [5000], 7, []]
    state = {}
    run(OURS, state=state)                       # buy something to sell
    sent, state, rec = run(SELL, state=state, fn=authsrv.handle_item_sale)
    ops = [op for op, _v in sent]
    LEDGER.ok(ops == [authsrv.GAME_SMSG_ITEM_REMOVED,
                      authsrv.GAME_SMSG_GOLD_CREDIT,
                      authsrv.GAME_SMSG_TRANSACTION_DONE],
              "SELL answers with three messages -- remove, pay, confirm",
              f"{[hex(o) for o in ops]}, 8 of 8 in the corpus. NO 0x013E and no "
              f"re-declaration: nothing moves because the item ceases to exist")
    by = dict(sent)
    LEDGER.ok(by[authsrv.GAME_SMSG_ITEM_REMOVED] ==
              [authsrv.PLAYER_INVENTORY_KEY, 5000],
              "0x014D names the item that leaves",
              f"{by[authsrv.GAME_SMSG_ITEM_REMOVED]}")
    LEDGER.ok(by[authsrv.GAME_SMSG_GOLD_CREDIT] ==
              [authsrv.PLAYER_INVENTORY_KEY, 7],
              "0x0140 credits the price from FIELD 4, not field 2",
              "the buy message carries its price at index 2 and the sell "
              "message at index 4; reading the buy's index here would credit "
              "0 every time, silently. Retail's field 4 matched the following "
              "credit 8 of 8")
    LEDGER.ok(by[authsrv.GAME_SMSG_TRANSACTION_DONE] == [11],
              "and 0x00CC echoes the SELL kind, 11",
              "the buy path echoes 1; the same message carries both")
    LEDGER.ok(state["backpack"] == {},
              "the slot is FREED, so the bag is a map and not a cursor",
              f"backpack {state['backpack']}. A monotonic cursor would call a "
              f"20-slot bag full after twenty transactions on an empty one")
    sent2, state, _r = run(OURS, state=state)
    LEDGER.ok(dict(sent2)[authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION][3] == 0,
              "and the next purchase REUSES it",
              "slot 0 again -- the freed slot is the lowest free one")
    LEDGER.ok(not run(SELL, state={}, fn=authsrv.handle_item_sale)[0],
              "selling an item the player does not hold is REFUSED",
              "the client can name any id; only what we put in the bag is "
              "sellable, or a server pays for goods it never delivered")
    buy_kind = list(SELL)
    buy_kind[1] = authsrv.TRANSACTION_KIND_BUY
    st = {}
    run(OURS, state=st)
    LEDGER.ok(not run(buy_kind, state=st, fn=authsrv.handle_item_sale)[0],
              "and the BUY kind (1) is refused on the sell message",
              "the two kinds share 0x00CC, so a handler that ignored kind "
              "would answer a buy with a credit")
    LEDGER.ok([k for k, _kw in rec.events] == ["sale"],
              "the sale is recorded exactly once",
              f"{rec.events[0][1] if rec.events else 'nothing'}")

    # ---- 5. the record ---------------------------------------------------
    _sent, _state, rec = run(OURS)
    LEDGER.ok([k for k, _kw in rec.events] == ["purchase"],
              "the purchase is recorded exactly once",
              f"{rec.events[0][1] if rec.events else 'nothing'} -- the capture "
              f"is what a later session reads instead of re-running the game")
    return LEDGER.verdict()


def STOCK_FOR(req):
    """The declared-items table a given request expects to find."""
    row = list(STOCK)
    row[0] = req[6][0]
    return {req[6][0]: row}


if __name__ == "__main__":
    sys.exit(main())
