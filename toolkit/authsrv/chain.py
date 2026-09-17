"""chain.py -- the Assassin's attack chain: what a skill counts as, what it
must follow, and the per-target state the server keeps for ONE attacker.

studies/daggers/FINDINGS.md. A stdlib-only leaf: it imports nothing of ours
and never its origin, so authsrv and the tests can both load it cold.

THE GRAMMAR IS THE CLIENT'S OWN, off the skill record (skilltable.py):

    combo      (+0x30)  what the skill COUNTS AS: 1 lead, 2 off-hand, 3 dual
    combo_req  (+0x14)  a BITMASK of what it must FOLLOW: 0x01 a dual,
                        0x02 a lead, 0x04 an off-hand -- NOT 1 << (combo - 1)

CORROBORATED against 37 wiki pages joined by skill id (test_skilltable 9).

THE STATE IS THE WIRE'S. s2c 0x005C [attacker, target, state] is the icon the
client draws on the target's health bar, for the attacker only (the handler is
a no-op unless field 1 is the addressed player -- studies/newopcodes). On
retail it is set to a chain skill's `combo` in the batch of that skill's HIT
and cleared with 0 in the instant the target dies (6 of 6, 20260819T132414) or
15 s after the LAST chain hit. RUN-DAGGERS-1 (20260917T160915, the owner's PvP
Assassin on the Isle) settled the rest, OBSERVED:

  * the message goes out only when the state CHANGES -- a second and a third
    lead on a target already at 1 sent nothing (404.246, 412.539);
  * every chain hit RESTARTS the clock all the same -- that target's 0 came
    15.000 s after the THIRD lead, 31.4 s after the set;
  * a dual sets 3, and 3 lasts the same 15.000 s (2 of 2); an off-hand that
    follows a dual puts the state back to 2.
"""

LEAD, OFF_HAND, DUAL = 1, 2, 3
STATE_NAMES = {0: "none", LEAD: "lead", OFF_HAND: "off-hand", DUAL: "dual"}

# combo_req bit -> the state the target must be in.
REQ_FOLLOWS = {0x01: DUAL, 0x02: LEAD, 0x04: OFF_HAND}
REQ_MASK = 0x07
# 0x10 sits on one row (1636) and is UNVERIFIED -- its page has no "must
# follow" clause, so it is not a CHAIN requirement and is not judged here.

# How long the state lasts after the LAST chain hit. OBSERVED at 15.000 s,
# 3 of 3 on RUN-DAGGERS-1 (370.321, 427.539, 511.858), to the millisecond --
# WIKI's "about 15s". (The 15.66 s the August tape showed was read set-to-
# clear, and a silent re-lead in between is what that reading cannot see.)
CHAIN_SECONDS = 15.0


def requirement_met(combo_req, state):
    """May a skill with this `combo_req` land on a target in this `state`?

    No chain bit set -> no chain requirement. Several bits set would mean "any
    of these" -- no row carries two, so that reading is untested and harmless.
    """
    req = int(combo_req) & REQ_MASK
    if not req:
        return True
    return any(req & bit and int(state) == need
               for bit, need in REQ_FOLLOWS.items())


def requirement_name(combo_req):
    req = int(combo_req) & REQ_MASK
    article = {LEAD: "a lead", OFF_HAND: "an off-hand", DUAL: "a dual"}
    names = [article[need] for bit, need in REQ_FOLLOWS.items() if req & bit]
    return " or ".join(names) if names else "nothing"


class ChainTable:
    """One attacker's chain state, per target. Plain data; the caller sends."""

    def __init__(self):
        self.rows = {}          # target -> {"state": n, "until": t}

    def state_on(self, target, now):
        row = self.rows.get(target)
        if row is None or now >= row["until"]:
            return 0
        return row["state"]

    def advance(self, target, combo, now):
        """A chain skill HIT `target`: the clock restarts, always. Returns the
        state to put on the wire, or None when there is nothing to send -- the
        skill is not a chain skill, or the target already shows that state
        (retail re-sends nothing for a re-lead)."""
        combo = int(combo)
        if combo not in (LEAD, OFF_HAND, DUAL):
            return None
        was = self.state_on(target, now)
        self.rows[target] = {"state": combo, "until": now + CHAIN_SECONDS}
        return combo if combo != was else None

    def clear(self, target):
        """Drop a target's row. True if there was a live icon to take down."""
        return self.rows.pop(target, None) is not None

    def expired(self, now):
        """Targets whose clock ran out -- each wants a state-0 message."""
        return sorted(t for t, row in self.rows.items() if now >= row["until"])
