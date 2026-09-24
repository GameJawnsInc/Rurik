"""purse.py -- the player's carried gold, DESKWORK-D9.

A leaf: the pure arithmetic and wire-value builders for the carried purse, so a
test can drive them with no server, no vault and no client. The thin arms live
in authsrv.py (the load credit and grant_quest_reward's pay line) and
merchant.py (buy/sell move the balance); everything decided here is stdlib +
integers.

WHERE EVERY NUMBER COMES FROM (`livewire.decode_conn` / `codec.decode_stream_at`
over every origin=LIVE game connection; reproduced by test_purse.py section 2):

  * THE LOAD CREDIT. On a gameplay-instance load (the one that carries the
    inventory family -- 0x0144 + bags + weapon sets) the server sends
    `0x0140 [the connection's own 0x0144 stream key, purse]` as the message
    IMMEDIATELY AFTER the last `0x0147` weapon set and before the first quest
    message (0x0050) or 0x00EA. OBSERVED on every such load; the purse read at
    load was 10 / 22 / 38 / 60 / 85 / 108 / 164 / 500 across the corpus, keyed
    by the per-connection stream key (141 / 2 / 156 / 117 / 40 / 4 / 159 / 183).
    55 of 96 connections send NO load 0x0140: those are the portal / char-select
    / pre connections (never a gameplay instance), so the minimum WITNESSED
    gameplay-load purse is 10 and a 0-gold load was never seen.
  * IT IS A CREDIT, NOT A SET. Handler 0x00846120 resolves the inventory by the
    key (asserting `inventory`, ItCliApi.cpp:1955, on an unregistered id) and
    calls 0x00849FE0, whose body is `add [inventory+0x90], amount` -- an
    accumulate (studies/newopcodes/FINDINGS.md, the 0x0140 correction; a SINGLE
    assert as the evidence). The client's carried purse starts at 0 on a fresh
    instance, so a load credit onto 0 EQUALS the balance. CORROBORATED beyond
    n=1: the cross-connection chain `next_load = prev_load + credits - debits`
    closes on every capture (the one exception is a character switch).
  * THE STARTING PURSE for a brand-new character is NOT FOUND -- no capture
    shows a fresh character's first purse -- so it is 0 (RECONSTRUCTION). An
    ABSENT stored purse means "not authored" and reads as this starting value,
    which keeps every pre-existing --persist store byte-identical.

The load credit is SKIPPED for a 0 purse: no gameplay load in the corpus carried
0, and `add 0` is a no-op on a client purse that is already 0, so sending it or
not is indistinguishable to the client -- we do not send what retail never did.
"""

# RECONSTRUCTION: no capture shows a new character's first purse (the corpus'
# smallest witnessed gameplay-load purse is 10, on an already-played character).
# 0 is the floor and means the load simply sends no extra 0x0140.
STARTING_PURSE = 0


def _as_int(purse):
    """A non-negative int, or a raise -- a purse is never a float or negative."""
    n = int(purse)
    if n < 0:
        raise ValueError(f"purse {purse!r} is negative; a carried purse floors at 0")
    return n


def start():
    """The purse a character with none stored carries."""
    return STARTING_PURSE


def load_credit(inv_key, purse):
    """The `0x0140 [inv_key, purse]` value list to send at load, or None.

    None when the purse is 0 (or falsy): no gameplay load in the corpus carried
    a 0-gold credit, and crediting 0 onto the client's already-0 purse is a
    no-op, so the caller skips the send. Sending it for a positive purse is
    retail's own behaviour, keyed by the registered inventory stream key.
    """
    n = _as_int(purse)
    if n == 0:
        return None
    return [int(inv_key), n]


def can_afford(purse, price):
    """Whether a purse of `purse` covers `price`.

    A None purse means the server is not modelling one (the bare merchant
    recipe, test_purchase): it does not gate, so it can always afford. A modelled
    purse gates on the balance.
    """
    if purse is None:
        return True
    return _as_int(purse) >= _as_int(price)


def after_buy(purse, price):
    """The purse after paying `price`. Raises if it would go negative -- the
    caller checks can_afford first, so reaching a negative here is a bug, not a
    refusal."""
    if purse is None:
        return None
    return _as_int(_as_int(purse) - _as_int(price))


def after_sell(purse, amount):
    """The purse after a sale's credit of `amount`."""
    if purse is None:
        return None
    return _as_int(purse) + _as_int(amount)


# A sale credit and a quest reward are the same operation on the purse: an
# accumulate. after_credit is the shared name so a reader sees they are one.
after_credit = after_sell
