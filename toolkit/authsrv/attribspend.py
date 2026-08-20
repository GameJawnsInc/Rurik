"""The attribute spend model: ranks, points, and the client's own refusal rules.

WHY THIS EXISTS. Until 2026-08-20 this server had no mutable attribute state at
all. Ranks came from a content row and never moved; the point budget was one
constant sent for BOTH fields of `0x0037`. The client, meanwhile, has always
been able to spend: `studies/pvpui/FINDINGS.md` 32 reads the whole protocol out
of the binary and a live capture -- the attribute panel PREDICTS a spend
locally, sends `0x000E`/`0x000F` with a sequence, and waits for the server to
retire that prediction with `0x0036` and then state the truth with `0x0038` and
`0x003B`. `studies/review` had flagged the gap years earlier: "you sat there
spending attribute points and the server had nowhere to put them."

THE RULES ARE THE CLIENT'S, NOT OURS, and every one of them is a measurement
rather than a preference -- see pvpui 32.4, which reads `0x00818E40`, the
function that recomputes an attribute's costs after every change:

  * A rank costs `s_attribPoints[rank]` to REACH and refunds the same number
    when you leave it (`toolkit/clientscan/attribpoints.py`, content table
    `attribute_cost`). Nine live rank transitions in capture 20260818T132739
    price out against it exactly, in both directions, with no free parameter.
  * `s_attribPoints[12] = -1` is the rank cap, and the client refuses rank 13
    with the SAME test that refuses an attribute you do not own.
  * An attribute is refused outright when its profession is 0, when the
    character does not have that profession, or when it is some profession's
    PRIMARY attribute and that profession is not the character's primary. The
    last is the game's "you cannot raise Strength as a secondary Warrior" rule,
    living in the client as one flag test over `s_attrib` (content table
    `attribute`, `is_primary`).

This module is pure: no sockets, no content loading, no globals. It is handed
the two tables and the character's professions and answers questions. That is
what makes it testable without a client, a server or a vault.
"""

from __future__ import annotations


class AttributeRules:
    """The cost curve and the attribute table, as the client holds them."""

    def __init__(self, costs, attributes):
        # costs: {rank: points_to_reach_it}, ranks 1..N contiguous from 1.
        self.costs = {int(r): int(p) for r, p in dict(costs).items()}
        if not self.costs:
            raise ValueError("no attribute cost rows -- refusing to invent a "
                             "cost curve. Run clientscan/attribpoints.py "
                             "--emit-content.")
        ranks = sorted(self.costs)
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError(f"attribute cost ranks are not 1..N contiguous: "
                             f"{ranks}. A gap would silently price a rank at 0.")
        # attributes: {attr_id: {"profession": int, "is_primary": bool}}
        self.attributes = {int(k): v for k, v in dict(attributes).items()}
        if not self.attributes:
            raise ValueError("no attribute rows -- refusing to validate spends "
                             "against an empty table, which would accept every "
                             "attribute id including ones the client asserts on.")
        self.rank_max = max(ranks)

    def cost_to_reach(self, rank):
        """Points to move from `rank-1` to `rank`. Rank 0 is free and absent."""
        return self.costs.get(int(rank), 0)

    def spent_on(self, rank):
        """Total points sunk into holding `rank` -- the cumulative sum."""
        return sum(self.costs[r] for r in range(1, int(rank) + 1)
                   if r in self.costs)

    def total_spent(self, ranks):
        return sum(self.spent_on(r) for r in dict(ranks).values())


def seed_ranks(content_ranks, stored_ranks):
    """Which ranks a session starts from: the store's, when it has any.

    ONE PLACE, ON PURPOSE. Until 2026-08-20 the spawn burst answered this
    question for `0x003A` by reading the persisted row while the point balance
    in `0x0037` was computed from the content row -- two sources that agreed
    only because nothing had ever written the store. Persisting a spend is
    precisely what pulls them apart, so the precedence lives here, is used by
    both, and is tested.

    An EMPTY stored list means "this character has never spent", not "this
    character has no attributes": `charstore.ensure_character` seeds the field
    to [] and the burst has to fall through to the content defaults, or a
    fresh character would spawn with no ranks at all.
    """
    if stored_ranks:
        return {int(a): int(r) for a, r in stored_ranks}
    return {int(a): int(r) for a, r in (content_ranks or [])}


class AttributeState:
    """One character's ranks and point budget, with the client's refusals.

    `refuse` returns a REASON STRING rather than a bool, and callers print it.
    A refusal here means the client and this server disagree about what is
    legal, and the client has already drawn the spend on screen -- so the one
    thing that must never happen is a silent drop. Same discipline as
    `handle_item_purchase`: refusals are loud and cost nothing.
    """

    def __init__(self, rules, ranks, points_total, primary, secondary=0):
        self.rules = rules
        self.ranks = {int(a): int(r) for a, r in dict(ranks).items()}
        self.points_total = int(points_total)
        self.primary = int(primary)
        self.secondary = int(secondary)

    # ---------------------------------------------------------------- state
    @property
    def spent(self):
        return self.rules.total_spent(self.ranks)

    @property
    def available(self):
        return self.points_total - self.spent

    def rank_of(self, attribute):
        return self.ranks.get(int(attribute), 0)

    def owns_profession(self, profession):
        profession = int(profession)
        return profession != 0 and profession in (self.primary, self.secondary)

    # ------------------------------------------------------------ refusals
    def _refuse_attribute(self, attribute):
        """The three client-side price-of--1 cases, in the client's own order."""
        row = self.rules.attributes.get(int(attribute))
        if row is None:
            return (f"attribute {attribute} is not in the client's s_attrib "
                    f"table (0..{max(self.rules.attributes)})")
        profession = int(row.get("profession", 0))
        if profession == 0:
            return f"attribute {attribute} has no profession"
        if not self.owns_profession(profession):
            return (f"attribute {attribute} belongs to profession "
                    f"{profession}; this character is {self.primary}/"
                    f"{self.secondary}")
        if bool(row.get("is_primary")) and profession != self.primary:
            return (f"attribute {attribute} is profession {profession}'s "
                    f"PRIMARY attribute and that is not this character's "
                    f"primary ({self.primary})")
        return None

    def refuse_increase(self, attribute):
        bad = self._refuse_attribute(attribute)
        if bad:
            return bad
        rank = self.rank_of(attribute)
        if rank >= self.rules.rank_max:
            return (f"attribute {attribute} is already at the rank cap "
                    f"{self.rules.rank_max}")
        price = self.rules.cost_to_reach(rank + 1)
        if self.available < price:
            return (f"rank {rank + 1} costs {price} and only "
                    f"{self.available} point(s) are unspent")
        return None

    def refuse_decrease(self, attribute):
        bad = self._refuse_attribute(attribute)
        if bad:
            return bad
        if self.rank_of(attribute) <= 0:
            return f"attribute {attribute} is already at rank 0"
        return None

    # -------------------------------------------------------------- moves
    def increase(self, attribute):
        """Raise by one rank. Caller must have checked `refuse_increase`."""
        attribute = int(attribute)
        self.ranks[attribute] = self.rank_of(attribute) + 1
        return self.ranks[attribute]

    def decrease(self, attribute):
        attribute = int(attribute)
        self.ranks[attribute] = self.rank_of(attribute) - 1
        if self.ranks[attribute] <= 0:
            self.ranks.pop(attribute, None)
            return 0
        return self.ranks[attribute]

    def refuse_load(self, pairs, column_max):
        """Validate a whole template spread before any of it is applied.

        ALL OR NOTHING, deliberately: `0x0010` carries no sequence and the
        client does NOT predict it (pvpui 32.7), so a half-applied spread would
        leave the panel showing a build nobody asked for with no prediction to
        retire. The cap is the client's own -- its framer clamps each array to
        64 while the buffer behind it holds 16 (pvpui 32.8), so a conformant
        server never invites more than 16.
        """
        pairs = [(int(a), int(r)) for a, r in pairs]
        if len(pairs) > column_max:
            return (f"{len(pairs)} attributes, and the client's own framer "
                    f"holds {column_max} per array")
        seen = set()
        for attribute, rank in pairs:
            if attribute in seen:
                return f"attribute {attribute} appears twice"
            seen.add(attribute)
            bad = self._refuse_attribute(attribute)
            if bad:
                return bad
            if rank < 0 or rank > self.rules.rank_max:
                return (f"attribute {attribute} at rank {rank}, outside "
                        f"0..{self.rules.rank_max}")
        cost = sum(self.rules.spent_on(r) for _a, r in pairs)
        if cost > self.points_total:
            return (f"the spread costs {cost} and this character has "
                    f"{self.points_total} point(s)")
        return None

    def load(self, pairs):
        self.ranks = {int(a): int(r) for a, r in pairs if int(r) > 0}
        return self.ranks
