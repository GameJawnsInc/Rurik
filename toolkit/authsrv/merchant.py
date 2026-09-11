"""Buy and sell: the purchase recipe and the gold/inventory messages it produces.

Two arms and the constants they need. `handle_item_purchase` answers GAME_CMSG
0x004D with pay-mint-place-confirm, `handle_item_sale` answers 0x004A with
remove-pay-confirm, and the banner below records the byte offsets both orders
were read off. Split out of `authsrv.py` 2026-09-11; the code, the banner and
every comment came across verbatim.

WHAT STAYED BEHIND, and why, because the banner below talks about both of them:

  * `GAME_CMSG_ITEM_PURCHASE = 0x004D` and `GAME_CMSG_ITEM_SELL = 0x004A` are
    still module-level int literals in `authsrv.py`, next to a pointer at this
    file. They have to be: `test_dispatch.py`'s GAME_CMSG census
    (`int_constants`, an AST walk for `NAME = <int Constant>`) reads a
    re-exported name as an `ast.Attribute` and drops it, so both arms would
    leave the census silently while `len(game) >= 16` stayed green at 29.
  * `PLAYER_INVENTORY_KEY`, `GAME_SMSG_CREATE_NAMED_ITEM` and
    `GAME_SMSG_ITEM_MOVED_TO_LOCATION` stay in `authsrv.py` with the rest of the
    inventory family and arrive here as trailing parameters, with NO defaults --
    a default is evaluated at `def` time and would freeze a value the server can
    still change.

WHAT THIS COST, stated rather than discovered later: `handle_item_purchase` is
no longer a module-level `FunctionDef` in `authsrv.py`'s own tree, so
`test_dispatch._state_writing_helpers` no longer sees it store into `state[...]`
and arm 0x004D loses its state-writing credit. Nothing asserts that arm -- the
check requires {0x0039, 0x0092, 0x00C1, 0x0040} -- so the census narrows without
reddening. Do not paper over it by putting a cosmetic `state[...] =` into the
forwarding wrapper.

Standard library only, and nothing is imported at all: the two handlers take
`send` and `rec` as arguments and reach no module. That is deliberate -- it is
what lets `test_purchase.py` exercise the whole buy/sell recipe with no vault,
no client and no socket.
"""


# ------------------------------------------------- buying from a merchant
#
# GAME_CMSG 0x004D is the client asking to buy, and until 2026-08-19 this
# server had never RECEIVED one: the client refuses a purchase it has nowhere
# to put, refuses it LOCALLY, and costs no wire message doing it. Nine bags in
# the login burst fixed that (PLAYER_BAGS), and the request arrived twice.
#
# THE REQUEST, ours and ArenaNet's, identical in shape:
#
#   ours    0x4D [1, 10, [], b'', 0, [40],   b'\x01']
#   retail  0x4D [1, 40, [], b'', 0, [2474], b'\x01']
#
# field 1 the transaction KIND (1 = buy; the sell message 0x004A carries 11 and
# 0x00CC echoes whichever it was, 9 of 9), field 2 the QUOTED price -- ours
# said 10 for a row we declared at value 5, which is the `displayed = value x 2`
# rule the panel already showed -- field 6 the item ids, field 7 one quantity
# byte per id.
#
# THE REPLY IS FOUR MESSAGES, and their ORDER is retail's rather than ours.
# Read off the single purchase in the live corpus (20260819T132414, conn 55414,
# +0.04 s after the request, extractor toolkit/authsrv/cmsgstream.py, build
# 38833), BY BYTE OFFSET in the decrypted stream:
#
#   36392  0x014F [183, 40]              the DEBIT, before the item exists
#   36400  0x0161 [4130, ...]            DECLARE the minted copy
#   36452  0x013E [183, 4130, 570, 1]    move it into bag 570 -- the BACKPACK
#   36463  0x00CC [1]                    transaction done, LAST, echoing the kind
#
# Pay, mint, place, confirm. Note that the bought item gets a NEW id
# (2474 -> 4130): merchant stock is a catalogue, and buying MINTS a copy rather
# than handing over the listed row.
#
# THE FIRST VERSION OF THIS ARM SENT THAT BACKWARDS AND KILLED THE CLIENT
# (`Assertion: item`, ItCliApi.cpp(1883) -- site 0x00845FB3, whose sibling
# asserts at :1886 `bag` and :1889 `inventory` identify the routine as 0x013E's
# own argument check, failing on its FIRST lookup because the item was not
# declared yet). The bad order was not misread from the bytes, it was
# MANUFACTURED by the tool that read them: a timeline script sorted whole
# tuples, and with all four messages sharing one segment timestamp the sort
# fell through to comparing the OPCODE NUMBER -- 0x00CC < 0x013E < 0x014F <
# 0x0161. Ascending opcodes wearing the costume of a finding. Offsets are the
# only ordering evidence a single frame can give; ask for them explicitly.
#
# 0x014F IS OBSERVED ONCE. One purchase was ever made in front of a capture, so
# n = 1 -- a strong single observation (right moment, right amount, right
# container, exact mirror of 0x0140's 31-sighting credit) and NOT corroborated.
# The way to promote it is this arm plus a client whose funds fall by the quote.
# studies/newopcodes/FINDINGS.md, the purchase-recipe section.
GAME_SMSG_TRANSACTION_DONE = 0x00CC
GAME_SMSG_GOLD_DEBIT = 0x014F
GAME_SMSG_ITEM_REMOVED = 0x014D
# The credit, and the debit's exact mirror: same field 1 (the
# inventory key), same `add` shape in the client -- handler
# 0x00846120 -> 0x00849FE0, `add [ecx+0x90], eax`. 31 sightings in
# the live corpus against 0x014F's one.
GAME_SMSG_GOLD_CREDIT = 0x0140
TRANSACTION_KIND_BUY = 1
# 11, and it is a CONSTANT rather than a count: it rides `0x004A`'s field 1 on
# all 8 sales in the corpus and comes back on `0x00CC` all 8 times, in windows
# whose stock size it never tracks.
TRANSACTION_KIND_SELL = 11
# Where a purchase lands. PLAYER_BAGS gives the backpack this id; retail put
# its bought item in the backpack too (bag 570 of nine, the type-1 container).
BACKPACK_BAG_ID = 2
BACKPACK_SLOT_COUNT = 20
# New ids for minted copies. Clear of the probe stock (40..50), the starter
# hammer (1) and the drain items -- an id collision would silently overwrite a
# declaration rather than error.
PURCHASED_ITEM_ID_BASE = 5000


def handle_item_purchase(values, send, state, conn_id, rec,
                         PLAYER_INVENTORY_KEY, GAME_SMSG_CREATE_NAMED_ITEM,
                         GAME_SMSG_ITEM_MOVED_TO_LOCATION):
    """Answer one GAME_CMSG 0x004D: mint the item, place it, take the money.

    REFUSALS ARE LOUD AND COST NOTHING, which matters more here than usual: the
    client has already decided locally that it can afford this and has room for
    it, so anything we cannot answer is a disagreement between its model and
    ours -- exactly the thing that must not be papered over with a plausible
    reply. An unknown item id, a missing declaration or a malformed request is
    printed and dropped, and the client simply sees no transaction.
    """
    kind = values[1] if len(values) > 1 else None
    price = values[2] if len(values) > 2 else 0
    items = values[6] if len(values) > 6 else []
    counts = values[7] if len(values) > 7 else b""
    if not isinstance(items, (list, tuple)) or not items:
        print(f"[c{conn_id}] BUY refused: no item in the request {values[1:]!r}",
              flush=True)
        return
    if kind != TRANSACTION_KIND_BUY:
        # 11 is the SELL kind and has its own message (0x004A). Anything else
        # is a transaction type nothing here has ever seen.
        print(f"[c{conn_id}] BUY refused: transaction kind {kind}, "
              f"expected {TRANSACTION_KIND_BUY}", flush=True)
        return
    declared = state.setdefault("declared_items", {})
    stock_id = items[0]
    row = declared.get(stock_id)
    if row is None:
        print(f"[c{conn_id}] BUY refused: item {stock_id} was never declared "
              f"by this session ({len(declared)} on file)", flush=True)
        return
    # A MAP, not a cursor: a sale frees its slot and the next purchase must be
    # able to take it. A monotonic cursor would call a bag full after twenty
    # transactions on an empty backpack.
    held = state.setdefault("backpack", {})
    slot = next((s for s in range(BACKPACK_SLOT_COUNT) if s not in held), None)
    if slot is None:
        print(f"[c{conn_id}] BUY refused: backpack full "
              f"({len(held)}/{BACKPACK_SLOT_COUNT} slots)", flush=True)
        return
    # array8 decodes to a str of code points, the same shape the settings blob
    # arrives in; one byte per item id, so the first is this item's quantity.
    try:
        quantity = (counts[0] if isinstance(counts, (bytes, bytearray))
                    else ord(counts[0]))
    except (IndexError, TypeError):
        quantity = 1
    new_id = state.get("next_purchased_item", PURCHASED_ITEM_ID_BASE)
    state["next_purchased_item"] = new_id + 1
    held[slot] = new_id
    minted = list(row)
    minted[0] = new_id
    if len(minted) > 10:
        minted[10] = quantity

    # Pay, mint, place, confirm -- retail's own order, by byte offset.
    send(GAME_SMSG_GOLD_DEBIT, [PLAYER_INVENTORY_KEY, price],
         f"GOLD_DEBIT({price})")
    send(GAME_SMSG_CREATE_NAMED_ITEM, minted,
         f"CREATE_NAMED_ITEM(bought copy {new_id} of stock {stock_id})")
    send(GAME_SMSG_ITEM_MOVED_TO_LOCATION,
         [PLAYER_INVENTORY_KEY, new_id, BACKPACK_BAG_ID, slot],
         f"ITEM_MOVED_TO_LOCATION(bought {new_id} -> backpack slot {slot})")
    send(GAME_SMSG_TRANSACTION_DONE, [kind],
         f"TRANSACTION_DONE(kind {kind})")
    rec.event("purchase", stock_id=stock_id, new_id=new_id, price=price,
              quantity=quantity, bag=BACKPACK_BAG_ID, slot=slot)
    print(f"[c{conn_id}] BUY: stock {stock_id} -> item {new_id} x{quantity} "
          f"into backpack slot {slot}, {price} gold debited", flush=True)


def handle_item_sale(values, send, state, conn_id, rec, PLAYER_INVENTORY_KEY):
    """Answer one GAME_CMSG 0x004A: take the item, pay for it, confirm.

    THE REQUEST IS NOT THE PURCHASE MESSAGE'S SHAPE, and assuming it was would
    read the price out of the wrong field. Retail's, all 8 identical in layout:

        0x004A [11, 0, [3634], 2, []]     kind, ?, item ids, PRICE, ?
        0x004D [1, 40, [], b'', 0, [2474], b'\x01']

    Five fields against seven, and the price sits at index 4 here and index 2
    there. Field 2 is 0 on all 8 and field 5 empty on all 8; neither is read.

    THE REPLY IS THREE MESSAGES -- remove, pay, confirm -- read BY BYTE OFFSET
    from all eight sales (20260819T132414, both connections):

        0x014D [inv, item]      the item is gone
        0x0140 [inv, price]     the CREDIT, mirror of the buy's 0x014F debit
        0x00CC [11]             done, echoing the kind

    No `0x013E` and no re-declaration: nothing moves, because the item ceases
    to exist. `0x00CC` is LAST in all nine transactions in the corpus, buy and
    sell alike, which is the one ordering invariant this family has.

    THE PRICE IS THE CLIENT'S, AND THAT IS A DELIBERATE CHOICE HERE. Field 4
    matched the following credit 8 times out of 8, so retail's server either
    trusts it or computes the same number; we cannot tell which from the wire,
    and this arm trusts it. That is fine for a probe and wrong for a world --
    a client can name any price -- so it is written down rather than hidden.
    """
    kind = values[1] if len(values) > 1 else None
    items = values[3] if len(values) > 3 else []
    price = values[4] if len(values) > 4 else 0
    if kind != TRANSACTION_KIND_SELL:
        print(f"[c{conn_id}] SELL refused: transaction kind {kind}, expected "
              f"{TRANSACTION_KIND_SELL}", flush=True)
        return
    if not isinstance(items, (list, tuple)) or not items:
        print(f"[c{conn_id}] SELL refused: no item in the request "
              f"{values[1:]!r}", flush=True)
        return
    item_id = items[0]
    held = state.setdefault("backpack", {})
    slot = next((s for s, held_id in held.items() if held_id == item_id), None)
    if slot is None:
        # The client can name any id; only what we put in the bag is sellable.
        print(f"[c{conn_id}] SELL refused: item {item_id} is not in this "
              f"player's backpack ({sorted(held.values())})", flush=True)
        return
    del held[slot]

    send(GAME_SMSG_ITEM_REMOVED, [PLAYER_INVENTORY_KEY, item_id],
         f"ITEM_REMOVED(sold {item_id} from slot {slot})")
    send(GAME_SMSG_GOLD_CREDIT, [PLAYER_INVENTORY_KEY, price],
         f"GOLD_CREDIT({price})")
    send(GAME_SMSG_TRANSACTION_DONE, [kind],
         f"TRANSACTION_DONE(kind {kind})")
    rec.event("sale", item_id=item_id, price=price, slot=slot)
    print(f"[c{conn_id}] SELL: item {item_id} out of backpack slot {slot}, "
          f"{price} gold credited", flush=True)
