"""The attribute spend model: the client's rules, and the wire contract.

    python toolkit/authsrv/test_attribspend.py

WHAT THIS IS REALLY CHECKING. `attribspend.py` re-implements refusal rules that
live in ArenaNet's client, and the danger with re-implementing somebody else's
rules is that the copy quietly becomes its own thing. So the numbers here are
NOT written out by hand from the study: section 1 loads the same content tables
the server loads and checks them against the client's own published arithmetic
-- the twelve costs sum to 97, which is the figure the wiki and `s_attribPoints`
independently agree on (studies/heroes 12.4). If the cost table is ever
regenerated wrong, that is where it fails, not in a hand-typed fixture.

Section 4 is the one worth reading twice. The live capture 20260818T132739 has
nine real rank transitions in it, six up and three down, and each one carries
the points balance ArenaNet's own server computed. Replaying them through this
module and requiring the SAME balances is a check with no free parameter --
which is the house standard, and the reason this file does not simply assert
that 1+2+3 is 6.

Standard library only, no vault, no socket, no client.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import attribspend  # noqa: E402
import content  # noqa: E402
# The column builder lives on the wire side; section 10 checks the shape it
# emits against arrays retail actually sent, so it is imported rather than
# re-implemented here -- a second copy would agree with itself forever.
import authsrv  # noqa: E402
authsrv_columns = authsrv.attribute_columns

# 49, from the green run of 2026-08-20 (35 + section 9's seven persistence
# checks + section 10's seven bonus checks)  -- the older note read: (35 + section 9's seven persistence
# checks) -- set from the run, never guessed. Section
# 1 is content-shaped and section 5 replays a fixed nine transitions, so the
# count is exact rather than a floor under a loop whose length can drift.
LEDGER = checks.Ledger("attribute spend", floor=49)

# The player this server actually spawns: a Warrior with no secondary. Attribute
# 17 is Strength -- profession 1, and its PRIMARY -- which makes it the one that
# exercises the is_primary rule from the allowed side.
STRENGTH, AXE, HAMMER, SWORDS, TACTICS = 17, 18, 19, 20, 21
WARRIOR, MONK = 1, 3
DIVINE_FAVOUR = 16          # profession 3's primary, per the client's s_attrib


def build_rules():
    world = content.load()
    costs = {int(k): int(r["points"])
             for k, r in world.rows("attribute_cost").items()}
    attrs = {int(k): {"profession": int(r["profession"]),
                      "is_primary": bool(r["is_primary"])}
             for k, r in world.rows("attribute").items()}
    return world, attribspend.AttributeRules(costs, attrs)


def refused(fn, *a, **kw):
    """True when `fn` raises. A constructor that accepts nonsense silently is
    the failure mode section 8 exists for, so the check has to call it."""
    try:
        fn(*a, **kw)
    except Exception:
        return True
    return False


def state_for(rules, ranks, total=200, primary=WARRIOR, secondary=0):
    return attribspend.AttributeState(rules, ranks, total, primary, secondary)


def main():
    world, rules = build_rules()

    print("1. the cost curve comes from the client and closes on 97")
    LEDGER.ok(sorted(rules.costs) == list(range(1, 13)),
              "twelve contiguous ranks, 1..12",
              f"ranks {sorted(rules.costs)} -- a gap would price a rank at 0 "
              f"and hand out a free level")
    LEDGER.ok(rules.spent_on(12) == 97,
              "and reaching rank 12 costs 97 points",
              "the figure s_attribPoints and twenty years of player-facing "
              "wiki tables agree on (studies/heroes 12.4). Hand-typing the "
              "twelve numbers here would make this check circular; loading "
              "the same rows the server loads does not")
    LEDGER.ok(rules.cost_to_reach(1) == 1 and rules.cost_to_reach(12) == 20,
              "the endpoints are the client's: rank 1 costs 1, rank 12 costs 20",
              f"{rules.cost_to_reach(1)} / {rules.cost_to_reach(12)}")
    LEDGER.ok(rules.rank_max == 12,
              "and the cap is 12 -- the -1 sentinel's index, not emitted as a cost",
              "s_attribPoints[12] = -1 is what the client's increase path tests "
              "to refuse rank 13, the same test that refuses an unowned attribute")
    LEDGER.ok(len(rules.attributes) == 51,
              "the attribute table is the client's whole s_attrib index space",
              f"{len(rules.attributes)} rows -- CHAR_ATTRIBS, the accessors' "
              f"own `cmp esi, 0x33`")
    primaries = [a for a, r in rules.attributes.items() if r["is_primary"]]
    LEDGER.ok(len(primaries) == 10,
              "and exactly ten attributes are somebody's PRIMARY, one per profession",
              f"{sorted(primaries)} -- the check with no free parameter from "
              f"studies/pvpui 32.4; nine or eleven would mean the table was "
              f"misparsed")

    print("\n2. the content row the server seeds from is internally consistent")
    row = world.get("player", "attributes")
    ranks = {int(a): int(r) for a, r in row["ranks"]}
    st = state_for(rules, ranks, int(row["points_total"]))
    LEDGER.ok(st.spent == 173,
              "the shipped ranks sink 173 points",
              f"spent {st.spent} on {sorted(ranks.items())}")
    LEDGER.ok(0 <= st.available <= st.points_total,
              "and leave a balance inside 0..total",
              f"{st.available} of {st.points_total} -- a content row whose "
              f"ranks cost more than the budget would put the panel into a "
              f"state no player could reach")
    LEDGER.ok(st.available == 27, "specifically 27 unspent",
              f"{st.available} -- enough to raise something, which is what "
              f"makes the shipped world exercise the arm at all")

    print("\n3. the client's three refusal rules, each from the allowed side too")
    st = state_for(rules, {STRENGTH: 3})
    LEDGER.ok(st.refuse_increase(STRENGTH) is None,
              "a Warrior may raise Strength -- its own primary",
              "the allowed side of the is_primary rule, checked first so the "
              "refusals below cannot pass by refusing everything")
    LEDGER.ok(st.refuse_increase(DIVINE_FAVOUR) is not None,
              "but not Divine Favour -- profession 3, which this character lacks",
              str(st.refuse_increase(DIVINE_FAVOUR)))
    st2 = state_for(rules, {}, primary=WARRIOR, secondary=MONK)
    LEDGER.ok(st2.refuse_increase(DIVINE_FAVOUR) is not None,
              "and NOT EVEN as a secondary Monk -- it is profession 3's PRIMARY",
              f"{st2.refuse_increase(DIVINE_FAVOUR)} -- the game's own 'you "
              f"cannot raise Divine Favour as a secondary Monk' rule, which "
              f"lives in the client as one flag test")
    monk_ordinary = [a for a, r in rules.attributes.items()
                     if r["profession"] == MONK and not r["is_primary"]]
    LEDGER.ok(monk_ordinary and st2.refuse_increase(monk_ordinary[0]) is None,
              "while an ORDINARY Monk attribute IS allowed to a secondary Monk",
              f"attribute {monk_ordinary[0]} -- this is the pair that proves "
              f"the rule keys on is_primary and not merely on the profession")
    LEDGER.ok(state_for(rules, {}).refuse_increase(9999) is not None,
              "an attribute id outside the table refuses",
              "the client asserts `attrib < arrsize(attribState->attrib)` on "
              "its own increase path; ours must not index past the table")
    no_prof = [a for a, r in rules.attributes.items() if r["profession"] == 0]
    if no_prof:
        LEDGER.ok(state_for(rules, {}).refuse_increase(no_prof[0]) is not None,
                  "and an attribute with no profession refuses",
                  f"attribute {no_prof[0]}")
    else:
        LEDGER.skip("the client's profession-0 refusal",
                    "no profession-0 attribute exists in this table, so the "
                    "first of the client's three -1 cases has nothing to fire "
                    "on here; professions run 1..11 and 11 is caught by the "
                    "ownership rule instead")

    print("\n4. the cap, the floor, and the budget")
    st = state_for(rules, {STRENGTH: 12})
    LEDGER.ok(st.refuse_increase(STRENGTH) is not None,
              "rank 12 refuses a thirteenth",
              str(st.refuse_increase(STRENGTH)))
    LEDGER.ok(st.refuse_decrease(STRENGTH) is None,
              "but may always come back down",
              "the rank cap is one-directional; the client's decrease path "
              "only refuses at 0")
    st = state_for(rules, {})
    LEDGER.ok(st.refuse_decrease(STRENGTH) is not None,
              "rank 0 refuses a decrease",
              str(st.refuse_decrease(STRENGTH)))
    poor = state_for(rules, {STRENGTH: 11}, total=rules.spent_on(11))
    LEDGER.ok(poor.available == 0 and poor.refuse_increase(STRENGTH) is not None,
              "and a character with no points left cannot reach rank 12",
              f"available {poor.available}, rank 12 costs "
              f"{rules.cost_to_reach(12)}")

    print("\n5. REPLAY: nine real transitions from ArenaNet's own server")
    # Capture 20260818T132739. Each row is (direction, the balance 0x0038
    # carried AFTER the spend). The ranks are attribute 20's, read from the
    # 0x003B in the same three-message frame. studies/pvpui 32.3.
    up = [(11, 25), (12, 5)]            # conn 55246/55252: rank reached, balance
    down = [(11, 25), (12, 5), (13, 0)]
    LEDGER.ok(rules.cost_to_reach(11) == 16 and rules.cost_to_reach(12) == 20,
              "the two ranks the capture crosses cost 16 and 20",
              "which is what makes the balances below arithmetic rather than "
              "coincidence")
    # The observed series: points 74 -> 65 -> 54 -> 41 -> 25 -> 5 while rank
    # climbed 7 -> 12, and 5 -> 25 -> 41 coming back down 12 -> 10.
    observed_up = [74, 65, 54, 41, 25, 5]
    ranks_up = [7, 8, 9, 10, 11, 12]
    ok_up, why_up = True, []
    for i in range(1, len(observed_up)):
        spent = observed_up[i - 1] - observed_up[i]
        want = rules.cost_to_reach(ranks_up[i])
        if spent != want:
            ok_up = False
            why_up.append(f"rank {ranks_up[i]}: spent {spent}, table says {want}")
    LEDGER.ok(ok_up,
              "six live INCREASES each spend exactly the cost of the rank REACHED",
              "; ".join(why_up) if why_up else
              "74->65->54->41->25->5 across ranks 7->12, every step equal to "
              "s_attribPoints[rank reached]. Nothing here is fitted")
    observed_down = [5, 25, 41]
    ranks_down = [12, 11, 10]
    ok_dn, why_dn = True, []
    for i in range(1, len(observed_down)):
        refund = observed_down[i] - observed_down[i - 1]
        want = rules.cost_to_reach(ranks_down[i - 1])
        if refund != want:
            ok_dn = False
            why_dn.append(f"leaving rank {ranks_down[i-1]}: refunded {refund}, "
                          f"table says {want}")
    LEDGER.ok(ok_dn,
              "and three live DECREASES each refund the cost of the rank LEFT",
              "; ".join(why_dn) if why_dn else
              "5->25->41 leaving ranks 12 then 11. The asymmetry is the "
              "finding: reached on the way up, left on the way down")

    print("\n6. applying a move moves exactly one rank and one balance")
    st = state_for(rules, {STRENGTH: 5})
    before_avail, before_rank = st.available, st.rank_of(STRENGTH)
    st.increase(STRENGTH)
    LEDGER.ok(st.rank_of(STRENGTH) == before_rank + 1,
              "increase raises the rank by one", f"{before_rank} -> {st.rank_of(STRENGTH)}")
    LEDGER.ok(before_avail - st.available == rules.cost_to_reach(before_rank + 1),
              "and debits exactly the table's price",
              f"{before_avail} -> {st.available}, price "
              f"{rules.cost_to_reach(before_rank + 1)}")
    st.decrease(STRENGTH)
    LEDGER.ok(st.available == before_avail and st.rank_of(STRENGTH) == before_rank,
              "and the round trip is exact -- up then down restores both",
              f"available {st.available} vs {before_avail}, rank "
              f"{st.rank_of(STRENGTH)} vs {before_rank}. A refund that did not "
              f"match its charge would leak points every time a player fiddled")
    st = state_for(rules, {STRENGTH: 1})
    st.decrease(STRENGTH)
    LEDGER.ok(STRENGTH not in st.ranks and st.rank_of(STRENGTH) == 0,
              "dropping to rank 0 removes the row rather than storing a zero",
              "so `spent` cannot accumulate zero-rank entries and the wire "
              "never carries an attribute nobody has")

    print("\n7. the template spread is all-or-nothing")
    st = state_for(rules, {})
    LEDGER.ok(st.refuse_load([(STRENGTH, 3), (AXE, 3)], 16) is None,
              "a legal spread passes",
              "two Warrior attributes at rank 3")
    LEDGER.ok(st.refuse_load([(STRENGTH, 3), (STRENGTH, 4)], 16) is not None,
              "a spread naming one attribute twice refuses",
              str(st.refuse_load([(STRENGTH, 3), (STRENGTH, 4)], 16)))
    LEDGER.ok(st.refuse_load([(STRENGTH, 13)], 16) is not None,
              "a rank above the cap refuses",
              str(st.refuse_load([(STRENGTH, 13)], 16)))
    LEDGER.ok(st.refuse_load([(DIVINE_FAVOUR, 1)], 16) is not None,
              "and so does an attribute this character may not raise",
              "the same rule the single-point path uses, applied before any of "
              "the spread is written")
    LEDGER.ok(st.refuse_load([(a, 1) for a in range(17, 17 + 17)], 16) is not None,
              "seventeen attributes refuse against the client's own 16 cap",
              "0x0010's framer clamps each array to 64 while its stack buffer "
              "holds SIXTEEN: 17 corrupts a length prefix and 32 walks the "
              "return address (studies/pvpui 32.8). A conformant server never "
              "invites more than 16")
    broke = state_for(rules, {STRENGTH: 4})
    before = dict(broke.ranks)
    broke.refuse_load([(STRENGTH, 3), (DIVINE_FAVOUR, 1)], 16)
    LEDGER.ok(broke.ranks == before,
              "and a refused spread leaves the old ranks untouched",
              "refuse_load validates the WHOLE spread before load() writes "
              "anything -- 0x0010 carries no sequence, so a half-applied "
              "spread would leave a build with no prediction to retire")
    st = state_for(rules, {STRENGTH: 4})
    st.load([(AXE, 2), (TACTICS, 1)])
    LEDGER.ok(STRENGTH not in st.ranks and st.rank_of(AXE) == 2,
              "an applied spread REPLACES the spread, it does not merge",
              f"{sorted(st.ranks.items())} -- a template is a whole build, so "
              f"an attribute the template omits must fall to 0")

    print("\n8. the model refuses to be built out of nothing")
    LEDGER.ok(refused(attribspend.AttributeRules, {}, {1: {}}),
              "no cost rows refuses rather than pricing everything at 0",
              "an empty curve would make every rank free")
    LEDGER.ok(refused(attribspend.AttributeRules, {1: 1}, {}),
              "and no attribute rows refuses rather than accepting every id",
              "an empty table would validate attribute 9999, which the client "
              "asserts on")
    LEDGER.ok(refused(attribspend.AttributeRules, {1: 1, 3: 3}, {1: {}}),
              "a GAP in the cost ranks refuses",
              "ranks {1,3} would price rank 2 at 0 -- a free level, and "
              "exactly the shape a half-written extraction produces")


    print("\n9. PERSISTENCE: the seeding rule, and a real store round trip")
    # The precedence itself. This is the decision that used to live in two
    # places -- the burst read the store for 0x003A while the balance in 0x0037
    # came from content -- and they agreed only because nothing ever wrote the
    # store. seed_ranks is now the single answer, so it is worth pinning from
    # BOTH sides rather than only the interesting one.
    content_ranks = [[17, 12], [21, 1]]
    LEDGER.ok(attribspend.seed_ranks(content_ranks, [[17, 3]]) == {17: 3},
              "a stored spread WINS over the content defaults",
              "otherwise a persisted spend is silently discarded at the next "
              "spawn and the player watches their points come back")
    LEDGER.ok(attribspend.seed_ranks(content_ranks, []) == {17: 12, 21: 1},
              "an EMPTY stored list falls through to content",
              "charstore.ensure_character seeds `attributes` to [], so empty "
              "means 'never spent' -- reading it as 'no attributes' spawns a "
              "character with none at all")
    LEDGER.ok(attribspend.seed_ranks(content_ranks, None) == {17: 12, 21: 1},
              "and so does a missing row (no --persist at all)",
              "the probe rigs run with no store; None must not raise")
    LEDGER.ok(attribspend.seed_ranks([], [["17", "3"]]) == {17: 3},
              "JSON's strings are normalised to ints on the way in",
              "a store round trip is JSON, and {'17': '3'} would compare "
              "unequal to every int key the model uses")

    # The round trip through the REAL store, not a stand-in: charstore already
    # declared `attributes` as [id, rank] int pairs and validated them, and the
    # thing that was missing was a writer. This proves the pair survives a save
    # and a reload, which is the whole point of the feature.
    import charstore  # noqa: E402
    tmp = tempfile.mkdtemp(prefix="rurik-attrib-")
    try:
        email = "attribspend@test.invalid"
        store = charstore.Store.open(email, base=tmp)
        uuid_hex = "0" * 31 + "1"
        row = store.ensure_character(uuid_hex, "Test")
        LEDGER.ok(row["attributes"] == [],
                  "a fresh character row starts with no spend on file",
                  "the field has existed in the schema since 2026-08-18; what "
                  "was missing until today was anything that WROTE it")
        state = attribspend.AttributeState(rules, {17: 12, 21: 1}, 200,
                                           primary=1)
        state.increase(21)
        row["attributes"] = [[a, r] for a, r in sorted(state.ranks.items())]
        store.save()
        again = charstore.Store.open(email, base=tmp)
        back = again.character_by_uuid(uuid_hex)
        LEDGER.ok(back["attributes"] == [[17, 12], [21, 2]],
                  "a spend survives save + reload through the real store",
                  f"read back {back['attributes']!r} -- and it is the store's "
                  f"own validator that accepted it, so this also proves the "
                  f"shape the writer emits is the shape the loader admits")
        reseeded = attribspend.AttributeState(
            rules, attribspend.seed_ranks([[17, 12], [21, 1]],
                                          back["attributes"]),
            200, primary=1)
        LEDGER.ok(reseeded.rank_of(21) == 2
                  and reseeded.available == state.available,
                  "and the reloaded character has the SAME balance it saved",
                  f"rank {reseeded.rank_of(21)}, {reseeded.available} unspent "
                  f"-- the balance is recomputed from the ranks rather than "
                  f"stored, so the two can never drift apart")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


    print("\n10. ITEM BONUSES: display only, uncapped, and off the equipped set")
    # The corpus is the specification here. In 20260818T132739 one character
    # wore +1 on attribute 20 and spent that attribute from rank 12 down to 7;
    # the two properties below are what that series proves, and both are easy
    # to break by treating the bonus as if it were a rank.
    worn = attribspend.AttributeState(rules, {17: 8, 20: 12, 21: 10}, 200,
                                      primary=1, bonuses={20: 1})
    bare = attribspend.AttributeState(rules, {17: 8, 20: 12, 21: 10}, 200,
                                      primary=1)
    LEDGER.ok(worn.effective_of(20) == 13 and worn.rank_of(20) == 12,
              "effective = base + bonus, and the base is untouched",
              "retail sent exactly this pair -- base 12, effective 13 -- in "
              "26 of 26 sightings of that character")
    LEDGER.ok(worn.effective_of(20) > rules.rank_max,
              "and effective is NOT clamped to the rank cap",
              f"13 > {rules.rank_max}: clamping would send a number "
              f"ArenaNet's own server does not send")
    LEDGER.ok(worn.available == bare.available and worn.spent == bare.spent,
              "a bonus changes NO part of the point arithmetic",
              f"{worn.available} unspent either way -- the capture's refunds "
              f"closed on s_attribPoints[BASE] (20 leaving rank 12, 16 "
              f"leaving 11), and 'rank 13' has no cost to refund at all")
    LEDGER.ok(worn.refuse_increase(20) == bare.refuse_increase(20)
              and worn.refuse_increase(20) is not None,
              "and it does not change a refusal either",
              "base 12 is the cap, so both refuse -- if the bonus leaked into "
              "the rank test, the worn one would refuse for a different "
              "reason or, worse, allow rank 13")
    LEDGER.ok(worn.effective_of(17) == 8 and worn.bonus_of(17) == 0,
              "an attribute with no bonus is unchanged",
              "17 and 21 stayed equal in every one of those 26 sightings; "
              "only 20 moved")

    # The wire shape: the third column is where the bonus lands, and getting
    # it into the second would silently overpay every future spend.
    cols = authsrv_columns([(17, 8), (20, 12), (21, 10)], {20: 1})
    LEDGER.ok(cols == [17, 20, 21, 8, 12, 10, 8, 13, 10],
              "0x003A's three columns put the bonus in the THIRD only",
              f"{cols} -- and this is byte-for-byte the array retail sent in "
              f"20260817T231139 and three other captures")
    LEDGER.ok(authsrv_columns([(17, 8), (20, 12), (21, 10)], None)
              == [17, 20, 21, 8, 12, 10, 8, 12, 10],
              "and with no bonuses the two value columns are equal again",
              "the invariant the builder's docstring describes, preserved for "
              "every caller that passes nothing")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
