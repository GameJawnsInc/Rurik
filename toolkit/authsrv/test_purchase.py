r"""Answering GAME_CMSG 0x004D: the four messages, in ArenaNet's order.

    python toolkit/authsrv/test_purchase.py

WHY THE ORDER IS ASSERTED AND NOT JUST THE CONTENTS. Retail's reply to the one
purchase in the corpus puts `0x013E ITEM_MOVED` **before** the `0x0161` that
declares the item it moves, in the same frame. That reads like a transcription
slip and is not one -- it is what the bytes say -- so this file pins the whole
sequence rather than the set. A reordering "for tidiness" would be the kind of
change that looks harmless in review and is not verbatim.

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

LEDGER = checks.Ledger("answering a purchase", floor=18)

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


def run(request, declared=None, state=None):
    """(sent, state, rec) for one request. `sent` is [(opcode, values)]."""
    sent = []
    state = state if state is not None else {}
    state.setdefault("declared_items",
                     dict(declared if declared is not None
                          else {STOCK[0]: list(STOCK)}))
    rec = Rec()
    authsrv.handle_item_purchase(
        request, lambda op, values, label, quiet=False: sent.append(
            (op, list(values))), state, 1, rec)
    return sent, state, rec


def main():
    # ---- 1. the happy path, both requests ------------------------------
    for who, req in (("ours", OURS), ("retail-shaped", RETAIL)):
        stock = dict(STOCK_FOR(req))
        sent, state, rec = run(req, declared=stock)
        ops = [op for op, _v in sent]
        LEDGER.ok(ops == [authsrv.GAME_SMSG_TRANSACTION_DONE,
                          authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION,
                          authsrv.GAME_SMSG_GOLD_DEBIT,
                          authsrv.GAME_SMSG_CREATE_NAMED_ITEM],
                  f"{who}: four messages, in retail's own order",
                  f"{[hex(o) for o in ops]} -- 0x013E before the 0x0161 that "
                  f"declares what it moves, which is what the wire says")
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
    full = {"backpack_next_slot": authsrv.BACKPACK_SLOT_COUNT}
    LEDGER.ok(not run(OURS, state=full)[0],
              "a full backpack is refused",
              f"{authsrv.BACKPACK_SLOT_COUNT} slots is the type-1 bag's own "
              f"capacity, measured 49/49 in the live corpus")

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
