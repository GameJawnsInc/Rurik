"""purse.py -- the player's carried gold, DESKWORK-D9.

A leaf: the pure arithmetic and wire-value builders for the carried purse, so a
test can drive them with no server, no vault and no client. The thin arms live
in authsrv.py (the load credit and grant_quest_reward's pay line) and
merchant.py (buy/sell move the balance); everything decided here is stdlib +
integers.

WHERE EVERY NUMBER COMES FROM (`livewire.decode_conn` / `codec.decode_stream_at`
over every origin=LIVE game connection; reproduced by test_purse.py section 2):

  * THE LOAD CREDIT. Every one of the 96 origin=LIVE game connections is a
    gameplay-instance load (all 96 carry 0x0144 and the four 0x0147 weapon
    sets). On 41 of them the server sends `0x0140 [the connection's own 0x0144
    stream key, purse]` as the message IMMEDIATELY AFTER the last `0x0147` and
    before the first quest message (0x0050) or 0x00EA -- purses 10 / 22 / 38 /
    60 / 85 / 108 / 164 / 500, keyed by the per-connection stream key (141 / 2 /
    156 / 117 / 40 / 4 / 159 / 183, the key differing per connection for one
    character). The other 55 send NO 0x0140 at load, and they are 0-PURSE
    GAMEPLAY LOADS, not portal or char-select connections (pass 1 said so and
    both reviews refuted it): 48 of them load a named character with the full
    inventory family and play, and two are chain-proven -- 20260807T143055
    :60935 and 20260810T235916 :61193 load with no credit, earn 0x0140 [k, 10]
    at a quest hand-in, and the NEXT connection (:62994 / :61624) loads exactly
    [k, 10]. So retail's rule is OBSERVED in both halves: credit a positive
    purse, send nothing for 0. No load-position 0x0140 in the corpus carries 0.
  * IT IS A CREDIT, NOT A SET. Handler 0x00846120 resolves the inventory by the
    key (asserting `inventory`, ItCliApi.cpp:1955, on an unregistered id) and
    calls 0x00849FE0, whose body is `add [inventory+0x90], amount` -- an
    accumulate (studies/newopcodes/FINDINGS.md, the 0x0140 correction; a SINGLE
    assert as the evidence). The client's carried purse starts at 0 on a fresh
    instance, so a load credit onto 0 EQUALS the balance. CORROBORATED beyond
    n=1: the cross-connection chain `next_load = prev_load + credits` closes on
    every capture (the one exception is a character switch, 20260919T103604,
    85 then 500 -- two characters whose balances match their own other tapes).
    No chain closes over a DEBIT: the one 0x014F in the corpus follows its
    capture's last load; its sign is read from the binary (0x00846730 negates
    before the same add).
  * THE STARTING PURSE is 0, OBSERVED: the two chain-proven characters above
    start at 0 (no credit at load, +10 at their first hand-in, 10 on the next
    load), and 20260817T231139's 14 connections play one character at 0 all
    session. An ABSENT stored purse means "not authored" and reads as this
    starting value, which keeps every pre-existing --persist store
    byte-identical.

The load credit is SKIPPED for a 0 purse because that is what retail does (55 of
96 loads), and `add 0` would be a no-op on a client purse that is already 0
anyway -- we do not send what retail never did.
"""

# OBSERVED: a character's chain starts at 0 (20260807T143055 :60935 and
# 20260810T235916 :61193 load with no credit and earn their first 10 at a
# hand-in; the next load credits exactly 10). 0 means the load sends no 0x0140.
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
