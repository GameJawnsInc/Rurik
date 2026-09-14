"""Prove an agent can leave the world, and that a desynced stream stops the server.

Two fixes from studies/divergence/FINDINGS.md, the first live capture's divergence
analysis. They are tested together because they are the same defect wearing two
hats: in both cases the server carried on past a state it had no way to reason
about, and produced confident output about it.

  1. **WORLD_REMOVE_AGENT (0x0021)** -- D1, the highest-ranked protocol gap.
     ArenaNet sent it 416 times in one session; our server had sent it 0 times in
     271,449 recorded messages, so `state["agents"]` only ever grew and an agent id
     could never be reused without the client holding a stale object under it. The
     interesting assertions here are the REFUSALS, because the send itself is one
     line: removing a never-created id, and double-removing, are each 0 of 416 in
     the live capture, and the client bounds-checks the dword as an array index
     (`Array:587 "index < m_count"` at 0x005FD2F0), so a bad id asserts inside the
     client, far from the cause.

  2. **The desync close** -- D9(b). An unframeable opcode used to set
     `pending = b""` and continue, which is not recovery: with no length prefix
     nothing knows where the bad message ended, so every later read was framed from
     a non-boundary. This asserts the framer's own contract (it stops, it does not
     resynchronise) and that garbage does NOT accidentally frame -- the property
     the old code was quietly relying on being false.

standard library only.

    python toolkit/authsrv/test_agentlife.py
"""
import inspect
import math
import os
import struct
import time
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agents  # noqa: E402
import checks  # noqa: E402
from codec import Codec  # noqa: E402

# MEASURED 2026-08-31, both ways, from real runs: 261 with the vault, 248
# without (plus 4 declared skips, all printed). THE FLOOR IS THE BARE-MACHINE
# NUMBER, 256 -> 248, which is `test_armour.py`'s precedent -- it calls lowering
# to what a bare machine actually executes "the fix rather than a retreat", and
# `test_quests.py` (73 against a healthy 83) is the same shape.
#
# It could not have been measured before that day, because a vault-less run of
# this file never reached a verdict at all. It stopped THREE times, each one
# hidden behind the last:
#   1. `handle_skill_press` -> `player_rank_for_skill` raised ContentError (a
#      SERVER defect; fixed there, guarded by test_bareimport.py section 3).
#   2. `pinned.find()` raises `SystemExit`, which is BaseException -- so the
#      `except Exception` guarding the skill-table read could not catch it and
#      the skip it was written for had never once fired. test_compositetrap.py
#      section 1 hit exactly this on 2026-08-30; same fix.
#   3. `probes.check_encodable()` built every probe, and nine of them bind
#      `def_1480` -- the vault NPC row test_bareimport.py exists about -- while
#      their steps are built, outside that function's own try. Those are now
#      SKIPPED and named rather than fatal, and the section asserts the walk
#      encoded something, because 0 failures over 0 steps is not a pass.
# +10 at MOVECODE-1z-by (section_follow_router: the hostile's own copy
# walks a routed corridor, with the straight-line arm as the known-bad
# control). Floor from a real green run, never a head-count.
# +8 at MOVECODE-1z-bz (section_npc_plane: ANIMREF-RE 42.5's tracked
# plane words, with the frozen spawn word as the known-bad control).
# +8 at GROUNDZ-Q5 (section_plane_repath: the stationary plane correction,
# with the stale word left standing as the known-bad control).
# +21 at NPCTRACK-Q1 (section_client_model, 20: the hostile's copy is the
# client's own dead-reckoner and disc, with the corridor integrator as the
# known-bad control; and the chase section's wall pin split by arm, 1).
# Floor from a real green run of 331. +1 at NPCTRACK-F8 (the hold rule
# replaces the fresh-follow pin: three checks for two), green 333.
LEDGER = checks.Ledger("agent lifetime", floor=527)   # JARIN-S +25 (the hero's family, the lock, the flag, the death tick, the wipe, the carry, the rig); SLICE-H12 +14 (knock-down and block); SLICE-H9/H10/H11 +8 (the sword and the shield, the gated strikes, the hammer bandit); SLICE-H8c +2 (the revive opt-in); SLICE-H8 +6 (low levels); SLICE-H7 +5 (the staff, the bar); SLICE-H5 +10 (the commander's orders); SLICE-H4 +15 (the party fights); SLICE-H3 +14; SLICE-H2/H2b/H2c +11; SLICE-F27 +3 (the arrival owes the swing: the circling case); SLICE-F25 +2 (a cast in flight lands out of range; the revert arm); SLICE-F24 +6 (section 11c: an NPC attack skill is a swing); SLICE-F22 +8 (section 11b: the halt owes a swing); SLICE-F21 +1 (an armed swing lands out of reach; the revert arm replaces the old drop); SLICE-B7b +4 (the party follow and its two arms); SLICE-B3 +13 (a hostile heal aims at the hurt body; the known-bad arm; self heals and non-heals); from the green run


def section_weapon_damage():
    """The player's swing is the WEAPON's number, and that one is not ours.

    Every other constant in the registry above is invented and says so. This
    one is read out of the item ArenaNet sends: identifier 584, `arg` the
    maximum and `arg2` the minimum, and the client's own tooltip drew
    `Blunt Dmg: 3-5` for our hammer on 20260820T125155 -- which is how the
    max/min order was settled, because the static read could not.

    So it is pinned DIFFERENTLY from the invented ones. Those are pinned to a
    literal so they cannot drift silently; this is pinned to the WORD, so that
    editing the item's modifiers and editing the damage cannot come apart. A
    literal here would be the same defect the section above exists to prevent,
    from the other direction: it would let the content row change while the
    test kept agreeing with a number nobody sends any more.
    """
    import authsrv
    import agents

    print("\nN. weapon damage: the swing is the item's own 584 word")
    rng = authsrv.weapon_damage_range(agents.STARTER_HAMMER)
    LEDGER.ok(rng is not None and rng == authsrv.PLAYER_SWING_DAMAGE,
              "the swing range is READ from the equipped weapon",
              f"{rng} -- from 0xA4880503, identifier 584 arg 5 arg2 3. Not a "
              f"constant anyone typed: change the item's modifiers and this "
              f"moves with them")
    lo, hi = rng
    LEDGER.ok(lo <= hi and lo > 0,
              "and it is ordered min..max, which the SCREEN settled",
              f"{lo}-{hi}. The disassembly gave two fields and could not say "
              f"which was which; the tooltip drew `Blunt Dmg: 3-5` against "
              f"arg 5 arg2 3, so arg is the MAXIMUM")
    LEDGER.ok(authsrv.weapon_damage_range({"modifiers": []}) is None
              and authsrv.weapon_damage_range({}) is None,
              "an item with no damage word yields None, not zero",
              "zero damage is a swing that lands and does nothing; None is "
              "the caller falling back to HIT_FRACTION, which is what "
              "--no-weapon and a bare machine both need")

    sent = []
    state = {"agents": {10: {"name": "t", "dead": False, "died_at": 0.0,
                             "health": 1000.0, "max_health": 1000.0,
                             "last_hit": 0.0}}, "pos": (0.0, 0.0)}
    dealt = []
    for _ in range(200):
        sent.clear()
        state["agents"][10]["last_hit"] = 0.0
        state["agents"][10]["health"] = 1000.0
        authsrv.hit_enemy(lambda op, vals, label="", quiet=False:
                          sent.append((op, vals, label)), state, 10, 1)
        dealt.append(1000.0 - state["agents"][10]["health"])
    LEDGER.ok(dealt and all(lo <= d <= hi for d in dealt),
              f"200 swings all land inside {lo}-{hi}",
              f"observed {sorted(set(dealt))} -- absolute health points, not "
              f"a fraction of whatever is being hit. The old model made every "
              f"creature take the same number of swings however tough it was")
    LEDGER.ok(len(set(dealt)) > 1,
              "and the roll actually varies",
              f"{len(set(dealt))} distinct values over 200 swings. The roll "
              f"inside the range is OURS and uniform; Guild Wars' own "
              f"distribution is unmeasured, as are every term it puts around "
              f"the range -- armour, attribute rank, criticals")


def section_armour_and_crit():
    """The armour term reproduces ArenaNet's OWN measured bands, exactly.

    This is the strongest check in the file and it has no free parameters.
    `studies/isle` rung 7 published the damage model and, separately, the
    point-value BANDS a level-20 Warrior with a customized 15-22 sword at
    Swordsmanship 13 produced against three armour ratings in capture
    20260818T132739 (495 damage events). Feed our implementation their weapon,
    their rank and their armour ratings and it must land on their bands --
    which the model can fail at six endpoints and does not.

    Why that is worth more than a fixture: the bands came off retail traffic,
    not out of this repo, and nothing here was tuned to them. A wrong divisor,
    a wrong SL threshold, an off-by-one in the roll or a crit expressed as a
    second multiplier instead of an armour reduction all move an endpoint.
    """
    import authsrv
    import agents

    print("\nN2. the armour term, against the Isle's measured point bands")
    SWORD, RANK, MULT = (15, 22), 13, 1.20
    BANDS = {60: (19, 27), 80: (13, 19), 100: (9, 14)}
    for ar, (lo, hi) in BANDS.items():
        # the roll is finer-grained than integer (>= ~40 steps, isle 3), so
        # sample it finely rather than at the eight integer values
        got = {authsrv.swing_damage(RANK, ar, SWORD, mult=MULT, roll=r / 8.0)
               for r in range(SWORD[0] * 8, SWORD[1] * 8 + 1)}
        LEDGER.ok(min(got) == lo and max(got) == hi,
                  f"AR{ar}: our band is {int(min(got))}..{int(max(got))}, "
                  f"retail's was {lo}..{hi}",
                  f"from `round(roll * 1.20 * 2**((SL-AR)/40))` with SL={
                      authsrv.attack_strength(RANK):g} at rank {RANK}. Zero "
                  f"free parameters -- AR60's support fixes the scale and the "
                  f"other two follow, so this can fail at six endpoints")

    LEDGER.ok(authsrv.swing_damage(RANK, 60, SWORD, mult=MULT,
                                   critical=True) == 39,
              "and a critical at AR60/rank13 is 39, not 38",
              "the crit takes the range MAXIMUM at AR-20. 39 is what `round` "
              "gives and 38 is what `floor` gives -- studies/isle rules out "
              "floor on exactly this number, so the rounding rule is pinned "
              "here rather than assumed")

    print("\nN3. the pieces the band test rests on")
    LEDGER.ok(authsrv.attack_strength(12) == 60.0
              and authsrv.attack_strength(13) == 62.0
              and authsrv.attack_strength(9) == 45.0,
              "SL is 5*rank to the threshold and +2 a rank above it",
              "60 at rank 12, 62 at 13, 45 at 9 -- the threshold is "
              "(level+4)/2 = 12 at level 20, WIKI-sourced and agreeing with "
              "the wire from the opposite direction")
    rates = authsrv.CRITICAL_RATE_BY_RANK
    LEDGER.ok(set(rates) == {8, 9, 11, 12, 13}
              and abs(rates[13] - 0.3429) < 1e-9,
              "the crit rate table is the five MEASURED ranks and no more",
              f"{rates} -- rising monotonically, which is why a damage cap or "
              f"a fixed bonus is refuted. Rank 10 is absent because it was "
              f"never observed; critical_rate interpolates and that is OURS")
    mid = authsrv.critical_rate(10)
    LEDGER.ok(rates[9] <= mid <= rates[11]
              and authsrv.critical_rate(2) == rates[8]
              and authsrv.critical_rate(99) == rates[13],
              "and interpolation stays inside the measured points",
              f"rank 10 -> {mid:.4f}, between rank 9's {rates[9]} and rank "
              f"11's {rates[11]}; outside the table it CLAMPS rather than "
              f"extrapolating a rate off the end of five points")

    print("\nN3b. creature armour is DERIVED, and it re-derives the wiki")
    # `AR = 3*level + profession bonus` is WIKI (GWW "Armor rating"). The
    # bonus table was read off a DIFFERENT page's level-20 maxima (GWW "Basic
    # armor": Warrior 80, Ranger 70, Monk 60), so feeding the formula level 20
    # must reproduce that column. It can fail at every row and does not -- and
    # this is the check that would have caught the picked 60 this replaced.
    for prof, name, want in ((1, "Warrior", 80.0), (2, "Ranger", 70.0),
                             (3, "Monk", 60.0), (6, "Elementalist", 60.0),
                             (9, "Paragon", 80.0)):
        got = authsrv.creature_armor_rating({"level": 20, "profession": prof})
        LEDGER.ok(got == want,
                  f"a level-20 {name} derives to AR {want:g}",
                  f"got {got} -- 3*20 plus the profession bonus, against the "
                  f"maximum GWW's Basic armor table publishes for that "
                  f"profession. Two wiki pages cross-checking each other "
                  f"through our arithmetic")
    LEDGER.ok(authsrv.ENEMY_ARMOR_RATING == 3.0,
              "and our level-1 Monk Hatcher derives to AR 3, not a picked 60",
              f"{authsrv.ENEMY_ARMOR_RATING} = 3*1 + 0. The 60 that sat here "
              f"for one commit was level-20 armour on a level-1 creature -- "
              f"wrong in SHAPE, which is the failure monsterai 3.3 records "
              f"for reach")
    LEDGER.ok(authsrv.creature_armor_rating({"level": 1, "profession": 3},
                                            override=60) == 60.0
              and authsrv.creature_armor_rating({}) is None,
              "an override still wins, and a levelless creature yields None",
              "GWW says many PvE creatures do not follow the formula, so the "
              "override is the documented escape hatch; None keeps the swing "
              "falling back rather than inventing an AR")

    print("\nN4. 17 replaces 16, and the control turns the whole term off")
    sent = []
    send = lambda op, v, label="", quiet=False: sent.append((op, v, label))  # noqa: E731
    state = {"agents": {10: {"name": "t", "dead": False, "died_at": 0.0,
                             "health": 5000.0, "max_health": 5000.0,
                             "last_hit": 0.0, "armor_rating": 60}},
             "pos": (0.0, 0.0)}
    both = 0
    for _ in range(300):
        sent.clear()
        state["agents"][10]["last_hit"] = 0.0
        authsrv.hit_enemy(send, state, 10, 1)
        props = [v[0] for op, v, _ in sent
                 if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
        if agents.PROP_DAMAGE in props and agents.GV_CRITICAL in props:
            both += 1
    LEDGER.ok(both == 0,
              "no swing ever sends property 16 AND property 17",
              "p16 + p17 = 495 = exactly one event per swing across the whole "
              "rung-7 capture, so 17 REPLACES 16. Sending both would draw two "
              "numbers on the client for one hit")

    saved = authsrv.ARMOUR_TERM
    authsrv.ARMOUR_TERM = False
    try:
        seen = set()
        for _ in range(200):
            state["agents"][10]["last_hit"] = 0.0
            state["agents"][10]["health"] = 5000.0
            authsrv.hit_enemy(send, state, 10, 1)
            seen.add(5000.0 - state["agents"][10]["health"])
    finally:
        authsrv.ARMOUR_TERM = saved
    lo, hi = authsrv.PLAYER_SWING_DAMAGE
    LEDGER.ok(seen and min(seen) >= lo and max(seen) <= hi,
              "CONTROL: --no-armour-term gives the weapon's RAW range back",
              f"observed {sorted(seen)} inside {lo}-{hi}. A flag that changed "
              f"nothing would pass every check above without the term ever "
              f"being wired to the swing")

    state["agents"][10].pop("armor_rating")
    state["agents"][10]["last_hit"] = 0.0
    state["agents"][10]["health"] = 5000.0
    authsrv.hit_enemy(send, state, 10, 1)
    dealt = 5000.0 - state["agents"][10]["health"]
    LEDGER.ok(lo <= dealt <= hi,
              "and a target with NO armour rating falls back, never asserts",
              f"dealt {dealt} -- defaulting the AR to a number instead would "
              f"silently scale every hit by something nobody chose")


def section_player_armour():
    """The PLAYER's armour, checked against GWW's own published table.

    The five armour pieces this server sends carried a decoded, screen-verified
    `Armor: 25` and `Armor +20 (vs. physical damage)` for a day while every
    incoming swing ignored all of it. This is that closed -- and it is checkable
    against a THIRTY-EIGHT ROW oracle nobody here wrote: GWW's "Armor rating"
    page publishes the damage multiplier for every armour rating from 0 to 195
    in steps of 5, and our `2^((60-AR)/40)` has to land on all of it.
    """
    import authsrv
    import agents

    print("\nN5. the player's armour, against GWW's published multiplier table")
    # WIKI (GWW, "Armor rating" section Armor tables, rev. 2026). Three decimals
    # as printed. This is a measurement cited as evidence, not a bulk dump: it
    # is the oracle the arithmetic is checked against.
    GWW_TABLE = {
        0: 2.828, 5: 2.594, 10: 2.378, 15: 2.182, 20: 2.000, 25: 1.834,
        30: 1.682, 35: 1.542, 40: 1.414, 45: 1.297, 50: 1.189, 55: 1.091,
        60: 1.000, 65: 0.917, 70: 0.841, 75: 0.771, 80: 0.707, 85: 0.648,
        90: 0.595, 95: 0.545, 100: 0.500, 105: 0.459, 110: 0.420, 115: 0.386,
        120: 0.354, 125: 0.324, 130: 0.297, 135: 0.273, 140: 0.250, 145: 0.229,
        150: 0.210, 155: 0.193, 160: 0.177, 165: 0.162, 170: 0.149, 175: 0.136,
        180: 0.125, 185: 0.115, 190: 0.105, 195: 0.096,
    }
    off = [(ar, want, authsrv.armour_multiplier(ar))
           for ar, want in sorted(GWW_TABLE.items())
           if abs(authsrv.armour_multiplier(ar) - want) > 0.0015]
    LEDGER.ok(not off,
              f"all {len(GWW_TABLE)} rows of GWW's damage-multiplier table",
              f"AR 0 through 195 in fives, and `2^((60-AR)/40)` lands on "
              f"every printed value. The table is players' observation of "
              f"retail and the divisor came off 495 live damage events at the "
              f"Isle -- two independent observers, and this check is where "
              f"they meet. Tolerance is 0.0015 rather than half-a-last-place "
              f"because of ONE row: AR 15 is printed 2.182 and 2^(45/40) is "
              f"2.18102, which rounds to 2.181. Every other row agrees to "
              f"three decimals, so that is the wiki's typo rather than our "
              f"arithmetic -- recorded, not silently absorbed"
              if not off else f"OFF: {off[:4]}")

    print("\nN6. armour is PER-LOCATION, and the odds are the wiki's")
    ars = {k: authsrv.player_armour_at(k) for k, _w in authsrv.HIT_LOCATION_ODDS}
    LEDGER.ok(all(v == 45.0 for v in ars.values()),
              "each piece is 25 + 20 vs. physical = AR 45, and nothing is 125",
              f"{ars} -- summing five 25s is the single most natural wrong "
              f"thing to do here. GWW: 'a character with 4 pieces with AR 80 "
              f"and headgear with AR 40 will take double damage any time they "
              f"take a hit to the head; they will not have AR 360'")
    LEDGER.ok(authsrv.player_armour_at("warrior_body", physical=False) == 25.0,
              "and the +20 applies ONLY to physical damage",
              "25 against everything else -- the bonus is `Armor +20 (vs. "
              "physical damage)`, identifier 527 with the type from the "
              "companion identifier 4, and a term that ignored the type would "
              "be silently wrong against every elemental hit we ever add")
    counts = {}
    for _ in range(8000):
        k = authsrv.roll_hit_location()
        counts[k] = counts.get(k, 0) + 1
    want = dict(authsrv.HIT_LOCATION_ODDS)
    spread = {k: counts.get(k, 0) / 8000 * 8 for k in want}
    LEDGER.ok(all(abs(spread[k] - want[k]) < 0.25 for k in want),
              "the hit-location odds converge on the published 3/2/1/1/1",
              f"{ {k: round(v, 2) for k, v in spread.items()} } out of 8 over "
              f"8000 rolls. Chest 3/8, legs 2/8, the rest 1/8 each")
    LEDGER.ok(len(set(ars.values())) == 1,
              "NOTE: with five identical pieces the location changes NOTHING",
              "every slot is AR 45 today, so the roll is real machinery with "
              "no observable effect yet. It starts mattering the moment one "
              "piece differs -- which is retail's normal case and one content "
              "edit away, and is why this is a check rather than a comment")

    print("\nN7. the bonus cap, and the wart the control exposes")
    LEDGER.ok(authsrv.bonus_armour(20) == 20.0
              and authsrv.bonus_armour(25) == 25.0
              and authsrv.bonus_armour(30) == 25.0,
              "Bonus armour is capped at 25, per GWW's Armor calculation step 2",
              "our +20 is under it, so the cap is currently the identity -- "
              "written down now rather than discovered later by a stack of "
              "bonuses that silently over-counted")
    saved = authsrv.EQUIP_ARMOUR
    authsrv.EQUIP_ARMOUR = False
    try:
        bare = authsrv.player_armour_at("warrior_body")
    finally:
        authsrv.EQUIP_ARMOUR = saved
    LEDGER.ok(bare is None,
              "WART, NAMED: --no-armour yields None, which is NOT 'AR 0'",
              "the term is skipped, so an unarmoured character takes the "
              "BASELINE hit and is therefore TOUGHER than one in starter "
              "armour (AR 45 is below the 60 baseline, so our starter set "
              "makes you take 1.297x). That is backwards as a model of "
              "nakedness and correct as a control for 'does the term engage'. "
              "Retail has no naked character to measure, so no AR is invented "
              "for one -- but the next reader should not discover this from a "
              "log")


def main():
    import authsrv
    import probes

    codec = Codec()

    # ---- 1. the message is the shape the live capture and the client agree on --
    print("1. WORLD_REMOVE_AGENT is 6 bytes carrying one agent id")
    LEDGER.ok(authsrv.GAME_SMSG_WORLD_REMOVE_AGENT == 0x0021,
              "the opcode is 0x0021", "OBSERVED 416 times in the live capture")
    blob = codec.encode("GAME_SMSG", 0x0021, [725])
    LEDGER.ok(len(blob) == 6, "it encodes to exactly 6 bytes on the wire",
              f"{len(blob)}B: {blob.hex()} -- the client's RECV table says 6, and "
              f"at 2 or 10 the live stream does not frame")
    LEDGER.ok(blob[:2] == b"\x21\x00", "with the opcode first, little-endian",
              blob[:2].hex())
    msgs, consumed, err = codec.decode_stream("GAME_SMSG", blob)
    LEDGER.ok(err is None and consumed == 6 and msgs[0][1][1] == 725,
              "and it round-trips back to the agent id it was given",
              str(msgs))

    # ---- 2. the world state actually loses the agent ---------------------------
    print("\n2. removal is a world-state operation, not just a send")
    sent = []
    send = lambda op, vals, why="": sent.append((op, vals, why))
    state = {"agents": {10: {"name": "hatcher", "dead": False},
                        11: {"name": "other", "dead": False}}}

    entry = authsrv.remove_agent(send, state, 10, "test")
    LEDGER.ok(10 not in state["agents"],
              "the removed agent is GONE from state['agents']",
              "the dict only ever grew before this -- an id could never be reused")
    LEDGER.ok(11 in state["agents"], "and its neighbour is untouched")
    LEDGER.ok(entry["name"] == "hatcher",
              "the removed bookkeeping is returned, so a respawn can carry it")
    LEDGER.ok(sent and sent[0][0] == 0x0021 and sent[0][1] == [10],
              "and exactly the removal message went out", str(sent[0][:2]))
    LEDGER.ok(state.get("removed_agents") == [10],
              "the removal is recorded, so id reuse is auditable")

    # ---- 3. THE REFUSALS, which are the whole point ----------------------------
    print("\n3. the two removals ArenaNet never performs are refused")
    before = len(sent)
    try:
        authsrv.remove_agent(send, state, 10, "again")
        double = ""
    except authsrv.AgentLifetimeError as ex:
        double = str(ex)
    LEDGER.ok(bool(double),
              "double-removing an id is REFUSED, not sent",
              "0 of 416 live removals double-remove without an intervening create")
    LEDGER.ok(len(sent) == before,
              "and nothing went on the wire when it was refused",
              "a refusal that still sends is not a refusal")

    try:
        authsrv.remove_agent(send, state, 9999, "never existed")
        never = ""
    except authsrv.AgentLifetimeError as ex:
        never = str(ex)
    LEDGER.ok(bool(never), "removing a never-created id is REFUSED",
              "0 of 416 live -- and the client bounds-checks this dword as an "
              "index, so a bad id asserts inside the client, not here")
    LEDGER.ok("9999" in never and "live ids" in never,
              "and the refusal names the bad id and what IS live", never[:90])

    # ---- 4. id reuse, which removal exists to unlock ---------------------------
    print("\n4. an id can be reused once, and only once, it has been removed")
    state["agents"][10] = {"name": "hatcher-2", "dead": False}
    LEDGER.ok(10 in state["agents"],
              "a removed id can be created again",
              "301 of 301 live re-creations were preceded by a removal of that id")
    entry2 = authsrv.remove_agent(send, state, 10, "cycle")
    LEDGER.ok(entry2["name"] == "hatcher-2" and state["removed_agents"] == [10, 10],
              "and the cycle can repeat, each removal recorded")

    # ---- 5. the probe exists and states a prediction ---------------------------
    print("\n5. the probe that settles what the client does with a removal")
    LEDGER.ok("agent_removal" in probes.PROBES,
              "an agent_removal probe is registered")
    p = probes.PROBES["agent_removal"](1, (100.0, 200.0, 0))
    LEDGER.ok(bool(p.question) and bool(p.predicts),
              "and it states a question AND a prediction before it runs",
              "a probe with no stated expectation can be rationalised into "
              "agreeing with anything afterwards")
    LEDGER.ok([s.opcode for s in p.steps] == [0x0021, 0x0056, 0x0057, 0x0020, 0x0020],
              "its steps remove, then re-create with the FULL spawn burst, then control",
              str([hex(s.opcode) for s in p.steps]))

    # ---- 6. the desync close ---------------------------------------------------
    print("\n6. an unframeable opcode stops the framer and does not resynchronise")
    # 0x9201 is the real one: OBSERVED 7 times in our own corpus, one byte before
    # a VALID GAME_CMSG 0x0092 -- an off-by-one the old `pending = b""` hid.
    bad = bytes.fromhex("019280700000000000000000")
    msgs, consumed, err = codec.decode_stream("GAME_CMSG", bad, mask=0x8000)
    LEDGER.ok(err is not None and "no opcode" in err,
              "the framer REPORTS an unknown opcode rather than skipping it", err)
    LEDGER.ok(consumed == 0,
              "and consumes NOTHING, so the caller cannot mistake it for progress",
              f"consumed={consumed}")
    LEDGER.ok(not msgs,
              "no message is invented out of the undecodable bytes",
              "this is the property the old buffer-discard relied on being false: "
              "it cleared the buffer and framed the NEXT read from a non-boundary")

    # ---- 6b. what the SERVER does with that answer -----------------------------
    # Section 6 asserts what the codec does. That is not the fix. The defect was
    # that the codec was right and the CALLER mishandled it, so the policy is
    # extracted into frame_pending and asserted here directly -- without this,
    # every check above passes with the buffer-discard bug fully restored.
    print("\n6b. frame_pending: the server's own framing policy")
    whole = bytes.fromhex("019280700000000000000000")
    m, rest, desync = authsrv.frame_pending(codec, "GAME_CMSG", whole, 0x8000)
    LEDGER.ok(desync is not None,
              "an unframeable opcode is reported to the caller as a desync", str(desync))
    LEDGER.ok(rest == whole,
              "and its bytes are LEFT IN THE BUFFER, not discarded",
              "the old code set pending = b'' here, which framed every later read "
              "from a non-boundary while ARC4 kept the bytes looking plausible")

    # A partial trailing message is the NORMAL case and must not read as a desync.
    okmsg = codec.encode("GAME_SMSG", 0x0021, [7])
    m2, rest2, desync2 = authsrv.frame_pending(codec, "GAME_SMSG", okmsg + okmsg[:3], 0)
    LEDGER.ok(desync2 is None,
              "a half-arrived trailing message is NOT a desync",
              "a TCP read is not a message boundary; treating this as fatal would "
              "kill healthy connections constantly")
    LEDGER.ok(len(m2) == 1 and rest2 == okmsg[:3],
              "its bytes are carried forward for the next read", f"{len(m2)} msg, "
              f"{len(rest2)}B carried")
    m3, rest3, desync3 = authsrv.frame_pending(codec, "GAME_SMSG", okmsg * 3, 0)
    LEDGER.ok(desync3 is None and len(m3) == 3 and rest3 == b"",
              "and a clean buffer of whole messages consumes exactly, with no desync",
              f"{len(m3)} msgs, {len(rest3)}B left")

    section_named_builders(codec)
    section_pool_fraction()
    section_swing_back()
    section_hostile_heal_target()
    section_chase()
    section_follow_router()
    section_npc_plane()
    section_plane_repath()
    section_plane_reach()
    section_client_model()
    section_corridor_wire()
    section_disc_clip()
    section_enemy_count()
    section_hold_plane()
    section_owed_swing()
    section_npc_attack_skill()
    section_facing()
    section_enemy_skill()
    section_constants()
    section_weapon_damage()
    section_armour_and_crit()
    section_player_armour()
    section_opcode_pins()
    section_opcode_catalog()
    section_probe_encoding()
    section_spawn_profession()
    section_unlock_bitmap()
    section_secondary_bits()
    section_party_of_one()
    return LEDGER.verdict()


def _world(dist=85.0, **over):
    """A player at the origin and one hostile `dist` units away.

    The default is 85 u -- inside the hostile's engage reach (enemy_reach() =
    92 since ANIMREF-RE 40.1) so the swing and skill sections open a fight
    without first walking. Was 100 u, which sat inside the old 144 u borrow
    but outside the corrected 92; the chase section passes its own dist."""
    import authsrv
    entry = {"name": "hatcher", "dead": False, "died_at": 0.0,
             "health": 100.0, "max_health": 100.0, "last_hit": 0.0,
             "pos": (dist, 0.0), "plane": 0,
             "allegiance": agents.ALLEGIANCE_HOSTILE,
             "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
             "effects": 0, "attacks_back": True,
             "skills": authsrv.ENEMY_SKILL_BAR,
             "skill_ready": [0.0] * len(authsrv.ENEMY_SKILL_BAR)}
    entry.update(over)
    return {"agents": {10: entry}, "pos": (0.0, 0.0)}


def _world_ally(dist=85.0, **over):
    """`_world` plus an IDLE ally standing by (agent 11, same allegiance,
    attacks_back False so it never swings or casts). SKILLS-RC (2026-09-10):
    the default bar's slot 1 is Restore Condition, a target-OTHER-ally spell
    by the client's own byte, and a LONE hostile cannot cast it -- so the
    sections that exercise the bar's cycle need somebody for it to aim at.
    The cast names the ally, not the player."""
    state = _world(dist, **over)
    state["agents"][11] = dict(state["agents"][10], attacks_back=False,
                               pos=(120.0, 40.0), skills=(), skill_ready=[],
                               # SLICE-B3: a hostile's heal aims at whoever is
                               # HURT (hostile_heal_target), so an ally at full
                               # health draws no cast at all. Half health keeps
                               # every section below measuring what it did --
                               # the targeted form, the bar's cycle -- and 276
                               # still heals nothing here: no condition to cure.
                               health=50.0, max_health=100.0)
    return state


def _swings(state, n=1, gap=0.0):
    """Run enemy_attack_tick n times and return everything it sent."""
    import authsrv
    sent = []
    for _ in range(n):
        if gap:
            time.sleep(gap)
        authsrv.enemy_attack_tick(
            lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
            state, 1)
    return sent



def section_hostile_heal_target():
    """SLICE-B3: a hostile's heal aims at whoever is HURT, and steps past itself.

    The policy is `ally_heal_target`'s (SLICE-F10), reused for a hostile
    monk and extended to the caster's own body for an `ally`-kind skill.
    Three arms: a hurt ally is healed, a healthy squad skips the slot AND
    advances the round-robin cursor (the trap: a skipped slot that held the
    cursor would be picked again every tick), and a hurt monk with a healthy
    ally heals itself under Orison but never under Restore Condition -- the
    client's target byte, not ours.
    """
    import authsrv
    print("\n== SLICE-B3: a hostile's heal aims at the hurt body ==")

    kind = authsrv.skill_target_kind(281)
    if kind is None:
        LEDGER.skip("SLICE-B3: hostile heal targeting",
                    "no 'skills' rows -- the vault overlay is absent, so the "
                    "target byte that drives the policy cannot be read")
        return
    LEDGER.ok(kind == "ally" and authsrv.skill_target_kind(276) == "other_ally",
              "Orison of Healing 281 is target ALLY (the caster legal) and "
              "Restore Condition 276 is target OTHER ally, by the client's "
              "own bytes", f"{kind}, {authsrv.skill_target_kind(276)}")
    LEDGER.ok(authsrv.skill_heal(281, authsrv.ENEMY_SKILL_RANK)
              and not authsrv.skill_damage(281, authsrv.ENEMY_SKILL_RANK),
              "and 281 resolves as a HEAL with no damage half -- the "
              "unconditional heal SLICE-F10 said the slice needed",
              authsrv.skill_heal(281, authsrv.ENEMY_SKILL_RANK))

    def squad(monk_hp, ally_hp, bar):
        st = _world_ally()
        m = st["agents"][10]
        m["skills"] = tuple(bar)
        m["skill_ready"] = [0.0] * len(bar)
        m["last_slot"] = -1
        m["max_health"] = 200.0
        m["health"] = float(monk_hp)
        a = st["agents"][11]
        a["max_health"] = 200.0
        a["health"] = float(ally_hp)
        return st

    # (1) a hurt ally: the heal aims at it.
    st = squad(200, 80, [(281, 1.0, 2.0)])
    _swings(st)
    LEDGER.ok(st["agents"][10].get("casting") == 0
              and st["agents"][10].get("cast_target") == 11,
              "a hurt ally (80/200) draws the monk's Orison: cast_target is "
              "the ally, not the player",
              f"target {st['agents'][10].get('cast_target')}")
    st["agents"][10]["cast_lands_at"] = time.time() - 0.001
    _swings(st)
    LEDGER.ok(st["agents"][11]["health"] > 80.0,
              "and when it lands the ally's health rises -- resolved through "
              "cast_recipient's `ally` rule",
              f"{st['agents'][11]['health']:.0f}/200")

    # (2) a healthy squad: the slot is stepped past, cursor advanced, and
    # the attack behind it is reached on the same bar.
    st = squad(200, 200, [(281, 1.0, 2.0), (312, 0.75, 8.0)])
    _swings(st)
    m = st["agents"][10]
    LEDGER.ok(m.get("last_slot") == 1 and m.get("casting") == 1
              and m.get("cast_target") == authsrv.PLAYER_AGENT_ID,
              "a healthy squad SKIPS the heal, the cursor moves past it, and "
              "Holy Strike in slot 2 goes out at the player on the same tick",
              f"last_slot {m.get('last_slot')} casting {m.get('casting')} "
              f"target {m.get('cast_target')}")
    LEDGER.ok(m["skill_ready"][0] == 0.0,
              "and the skipped heal's recharge was NOT charged -- nothing "
              "was cast", m["skill_ready"])

    # (3) the monk itself is the hurt one.
    st = squad(60, 200, [(281, 1.0, 2.0)])
    _swings(st)
    LEDGER.ok(st["agents"][10].get("cast_target") == 10,
              "a hurt monk with a healthy ally heals ITSELF under Orison -- "
              "target byte 3 lets the caster be the recipient",
              f"target {st['agents'][10].get('cast_target')}")
    st = squad(60, 200, [(276, 0.75, 2.0)])
    _swings(st)
    LEDGER.ok(st["agents"][10].get("casting") is None
              and st["agents"][10].get("last_slot") == 0,
              "but never under Restore Condition: target OTHER ally, the "
              "healthy ally does not need it, and the slot is stepped past",
              f"casting {st['agents'][10].get('casting')}")

    # (3b) THE RUN'S OWN SHAPE, the known-bad arm: two heals and a recharging
    # attack on a healthy squad. Harness 20260912T122339 saw the monk cast
    # Orison at itself at full health, because the first re-pick loop ended
    # by exhaustion with a heal slot in hand and the player as its target.
    st = squad(200, 200, [(281, 1.0, 2.0), (252, 1.0, 10.0), (276, 0.75, 2.0)])
    st["agents"][10]["skill_ready"][1] = time.time() + 9.0      # Banish recharging
    st["agents"][10]["last_slot"] = 1                            # just cast it
    sent = _swings(st)
    m = st["agents"][10]
    cast = [v for op, v, _l in sent
            if op in (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                      authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT)
            and v and v[0] == agents.GV_SKILL_ACTIVATED]
    LEDGER.ok(m.get("casting") is None and not cast,
              "two heals and a RECHARGING attack on a healthy squad: nothing "
              "is cast -- the search ends when it re-picks a slot it already "
              "held, and never falls out with a heal aimed at the player "
              "(the run's self-heal at full health)",
              f"casting {m.get('casting')} casts {cast} held both heals")

    # (3c) a SELF heal is gated the same way, and a NON-heal ally skill is not.
    st = squad(200, 200, [(1, 2.0, 4.0)])
    _swings(st)
    LEDGER.ok(st["agents"][10].get("casting") is None,
              "Healing Signet (self) at full health is HELD -- harness "
              "20260912T123033's raider cast it at 200/200 every 4 s",
              f"casting {st['agents'][10].get('casting')}")
    st = squad(60, 200, [(1, 2.0, 4.0)])
    _swings(st)
    LEDGER.ok(st["agents"][10].get("casting") == 0
              and st["agents"][10].get("cast_target") == 10,
              "and at 60/200 it goes out, at the caster",
              f"target {st['agents'][10].get('cast_target')}")
    vb = authsrv.skill_target_kind(289)
    st = squad(200, 200, [(289, 0.75, 2.0)])
    _swings(st)
    LEDGER.ok(vb == "ally"
              and authsrv.skill_heal(289, authsrv.ENEMY_SKILL_RANK) is None
              and st["agents"][10].get("casting") == 0
              and st["agents"][10].get("cast_target") == authsrv.PLAYER_AGENT_ID,
              "Vital Blessing (target ally, NOT a heal) on a healthy squad "
              "still GOES OUT, aimed as before B3 -- at the player, which "
              "cast_recipient's `ally` rule resolves to the caster -- the "
              "gate is on heals, and an enchantment keeps the old rule",
              f"kind {vb}, target {st['agents'][10].get('cast_target')}")

    # (4) the hero's default bar is what a monk hero needs, offline.
    bar = [sk[0] for sk in authsrv.HERO_SKILLS]
    rows = {}
    for sid in bar:
        try:
            rows[sid] = agents.WORLD.get("skill_effect", str(sid)).get("scale_means")
        except Exception:                                      # noqa: BLE001
            rows[sid] = None
    LEDGER.ok(281 in bar
              and all(v in authsrv.SCALE_MEANS_HEAL for v in rows.values()),
              "HERO_SKILLS defaults to a bar of HEALS led by Orison -- every "
              "slot's skill_effect row is a heal label, from the repo alone",
              f"{bar} -> {rows}")


def section_swing_back():
    """R4a's other half: a hostile agent attacks the player, and the player dies.

    Until 2026-08-11 every combat message this server sent flowed one way. PLAN.md
    3's R4a row has said "nothing swings back and the player cannot die" since
    2026-08-06, and both clauses were properties of the code: no sweep aimed a
    swing at the player, and the server did not track the player's health at all
    after telling the client about it once at spawn.

    THE CHECK THAT MATTERS IS THE ROLE CHECK. `hit_enemy` carries a comment about
    an early version that put the ENEMY in slot 1 of GV_ATTACK_STARTED -- the
    client animated the enemy and then asserted on `m_attackInterval`, which is how
    slot 1 was identified as the swinger. `hit_player` is that mistake made
    deliberately, so the one way to get it wrong now is to write it the way
    `hit_enemy` is written and animate the PLAYER attacking themselves. Two checks
    below fail on exactly that, and they are the reason this section exists rather
    than a count of messages.
    """
    import authsrv

    # THE SKILL IS OFF THROUGHOUT THIS SECTION. `_world` carries production
    # defaults, and in production a hostile opens with its skill -- so every
    # fixture here would measure a cast instead of a swing. section_enemy_skill
    # owns that path; this one owns the swing, and mixing them was how the two
    # checks below first went red.
    def _sworld(**kw):
        w = _world(**kw)
        w["agents"][10]["skills"] = ()
        return w

    # 1. A SWING IS TWO PHASES SEPARATED BY A WINDUP, which is the shape ArenaNet
    #    uses and the shape the first version of this code got wrong: it sent all
    #    three messages in the same instant, so the damage number landed on the
    #    frame the animation started.
    state = _sworld()
    sent = _swings(state)
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(ops == [authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION,
                      authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET],
              "a swing opens by TURNING and then ATTACK_STARTED, with no damage",
              f"{[hex(o) for o in ops]} -- damage arriving here is the "
              "instant-swing bug: 0.899 s of animation with the number already on "
              "screen. The turn is forced on every swing because an agent landing "
              "a hit with its back to you is the one thing here a person would "
              "call broken without being told")
    LEDGER.ok(not _swings(state, n=4),
              "and nothing lands while the windup is still running",
              f"swing_lands_at is {state['agents'][10].get('swing_lands_at')!r} "
              "-- four more ticks inside the window must stay silent")

    # now let the windup elapse, and the landing must be FINISHED then DAMAGE
    state["agents"][10]["swing_lands_at"] = time.time() - 0.001
    land = _swings(state)
    ops = [op for op, _v, _l in land]
    # THE PIN IS THE ADJACENT PAIR AND NOT THE LENGTH OF THE LIST, since
    # 2026-08-21. The adrenaline family went on the wire that day, so an
    # enemy's landing hit now also earns the PLAYER a 0x00CF for the damage
    # taken -- appended AFTER the measured pair, never inserted into it, which
    # is the property this check should have been asserting all along. An
    # equality against the whole list said "finished then damage" and meant
    # "and nothing else ever", which is a claim no capture supports.
    # THE GAIN SITS BETWEEN THEM, not after. Re-pinned 2026-08-21 the same day
    # it was written: the first cut appended the 0x00CF, and the corpus puts it
    # between the attack marker and the damage (601 of 663 by the following
    # message; modal batch [159/prop1, 207, 163/prop16, 30], n=425). The
    # measured finished-then-damage pair is preserved either way -- it is the
    # ADJACENCY that had to give, and it gave in the direction ArenaNet sends.
    LEDGER.ok((ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                       authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
               or ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                          authsrv.AGENT_ADRENALINE_GAIN,
                          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]),
              "and the landing is MELEE_ATTACK_FINISHED and then the damage, "
              "with the optional gain BETWEEN them",
              f"{[hex(o) for o in ops]} -- ArenaNet sends finished BEFORE damage, "
              "adjacent in one payload, 6 of 6 swings checked by byte offset. "
              "hit_enemy sends them the other way round and is left alone: the "
              "claim about how the CONTROLLED agent's landings are marked was "
              "refuted under review, so there is no verified model to copy. "
              "The optional MIDDLE message is the player's own adrenaline "
              "gain, and it is OPTIONAL because a swing that takes under 1% of "
              "maximum health earns nothing -- the roll is inside the weapon's "
              "range. Its position is retail's: 601 of 663 corpus gains are "
              "immediately followed by the damage.")
    sent = sent + land

    started = [v for op, v, _l in sent
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET][0]
    LEDGER.ok(started[0] == agents.GV_ATTACK_STARTED and started[1] == 10,
              "and slot 1 of attack_started is the AGENT, not the player",
              f"{started} -- slot 1 is the body the client animates. Writing this "
              "the way hit_enemy is written puts PLAYER_AGENT_ID here and animates "
              "the player swinging at themselves, which is the mirror of the bug "
              "hit_enemy's own comment records")
    LEDGER.ok(started[2] == authsrv.PLAYER_AGENT_ID,
              "and slot 2 is the player, who is being swung at",
              f"{started}")

    dmg = [v for op, v, _l in sent
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET][0]
    LEDGER.ok(dmg[0] == agents.PROP_DAMAGE and dmg[1] == authsrv.PLAYER_AGENT_ID
              and dmg[2] == 10,
              "and the damage names the player as DAMAGED and the agent as CAUSE",
              f"{dmg[:3]} -- 0x00A3 is [prop, target, cause, value], the opposite "
              "order to attack_started, which is why both are checked here")

    val = struct.unpack("<f", struct.pack("<I", dmg[-1]))[0]
    LEDGER.ok(-1.0 <= val < 0.0,
              "and the value is a negative fraction inside the client's bound",
              f"{val!r} -- positive would trip CharPool.cpp:84 `fraction <= 1.0f`")
    LEDGER.ok(state["player_health"] < agents.PLAYER_HEALTH,
              "and the server's own bookkeeping went down with it",
              f"{state['player_health']} of {agents.PLAYER_HEALTH} -- nothing "
              "tracked this at all before this rung")

    # 2. the four refusals. Each is a hostile that must NOT swing.
    for why, world in (
            ("out of aggro range", _sworld(dist=authsrv.AGGRO_RANGE + 1.0)),
            ("dead", _sworld(dead=True)),
            ("attacks_back off", _sworld(attacks_back=False)),
            ("mid-burrow", _sworld(effects=agents.EFFECT_TRANSITION)),
            ("not hostile", _sworld(allegiance=agents.ALLEGIANCE_ENEMY + 100))):
        LEDGER.ok(not _swings(world),
                  f"a hostile that is {why} does not swing",
                  "silence is the whole assertion here")

    # AND A PENDING LANDING DOES NOT SURVIVE ITS SWINGER. ArenaNet's own seventh
    # swing in the Lakeside tape was truncated exactly this way -- the player
    # killed the worm 0.24 s into a 0.899 s windup and no damage followed.
    mid = _sworld()
    _swings(mid)                                        # opens a swing
    assert mid["agents"][10]["swing_lands_at"] is not None
    mid["agents"][10].update(dead=True)
    mid["agents"][10]["swing_lands_at"] = time.time() - 1.0   # long overdue
    before = mid["player_health"]
    LEDGER.ok(not _swings(mid, n=3) and mid["player_health"] == before,
              "a swing in flight does not land if the swinger dies",
              "an overdue landing plus three ticks, and no damage -- the "
              "pending swing has to be dropped, not merely postponed")
    # SLICE-F21: BUT A SWINGER (OR TARGET) THAT LEAVES REACH STILL LANDS.
    # Retail's swings at a player who ran during the windup landed 7 of 7,
    # 81-288 u displaced at the last report inside it; reach is judged at
    # the start, never at the hit. Until 2026-09-12 this arm pinned the drop
    # as retail's ("leaves range" beside "dies"); the kiter paid nothing.
    mid = _sworld()
    _swings(mid)
    assert mid["agents"][10]["swing_lands_at"] is not None
    mid["agents"][10].update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0))
    mid["agents"][10]["swing_lands_at"] = time.time() - 1.0
    before = mid["player_health"]
    LEDGER.ok(mid["player_health"] < before if _swings(mid, n=1) else False,
              "a swing in flight LANDS when the pair is out of reach at the "
              "hit -- retail 7 of 7 (SLICE-F21); only a NEW start needs reach",
              f"health {before} -> {mid['player_health']}")
    saved_lh = authsrv.LATE_HIT
    authsrv.LATE_HIT = False
    try:
        mid = _sworld()
        _swings(mid)
        mid["agents"][10].update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0))
        mid["agents"][10]["swing_lands_at"] = time.time() - 1.0
        before = mid["player_health"]
        LEDGER.ok(not _swings(mid, n=3) and mid["player_health"] == before,
                  "REVERT ARM (--no-late-hit): the out-of-reach landing is "
                  "dropped as before", f"{mid['player_health']}")
    finally:
        authsrv.LATE_HIT = saved_lh

    # 3. enough swings kill the player -- and the KILL is the effects bit, because
    #    property 16 floors at 1 and cannot do it. Drive it with the interval
    #    forced to zero rather than by sleeping through ten real swings.
    #    Driven through hit_player directly rather than by ticking: the swing
    #    timer reads time.time(), whose resolution on Windows is coarse enough
    #    that forty ticks at a 1 ms interval all landed inside one clock tick and
    #    produced a single swing. A test that has to outrun the clock to measure
    #    anything is measuring the clock.
    state = _sworld()
    sent = []
    keep = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    needed = int(math.ceil(1.0 / authsrv.ENEMY_HIT_FRACTION))
    for _ in range(needed):
        authsrv.land_swing(keep, state, 10, state["agents"][10], 1)
    LEDGER.ok(state["player_dead"] and state["player_health"] == 0.0,
              f"{needed} swings at {authsrv.ENEMY_HIT_FRACTION} of the pool kill "
              "the player",
              f"health {state['player_health']}, dead {state['player_dead']}")
    kills = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
             and v == [authsrv.PLAYER_AGENT_ID, agents.EFFECT_DEAD]]
    LEDGER.ok(len(kills) == 1,
              "and the death is ONE effects-bit message on the player",
              f"{len(kills)} -- damage cannot kill (PROP_DAMAGE floors at 1), so "
              "the bit is the death; more than one means the corpse is being "
              "re-killed every interval")

    # 4. and a corpse is left alone, in both directions
    before = len(sent)
    LEDGER.ok(not _swings(state, n=5),
              "nothing swings at a dead player",
              f"{before} messages before, none after")
    swung = []
    state["attacking"] = 10
    authsrv.attack_tick(lambda op, v, label="", quiet=False: swung.append(op),
                        state, 1)
    LEDGER.ok(not swung,
              "and a dead player stops swinging back",
              "attack_tick reads state['player_dead'] -- without it the corpse "
              "keeps hitting the thing that killed it")

    # 5. the revive, and that it does not fire early
    authsrv.player_revive_due(lambda *a, **k: None, state, 1)
    LEDGER.ok(state["player_dead"],
              "the revive does not fire before its timer",
              f"died_at {state['player_died_at']}, needs "
              f"{authsrv.PLAYER_REVIVE_AFTER}s")

    state["player_died_at"] = time.time() - authsrv.PLAYER_REVIVE_AFTER - 1.0
    rev = []
    authsrv.player_revive_due(
        lambda op, v, label="", quiet=False: rev.append((op, v)), state, 1)
    LEDGER.ok(not state["player_dead"]
              and state["player_health"] == float(agents.PLAYER_HEALTH),
              "and then it stands the player back up at full health",
              f"{state['player_health']}")
    cleared = [v for op, v in rev if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS]
    LEDGER.ok(cleared == [[authsrv.PLAYER_AGENT_ID, 0]],
              "clearing the effects bit it set",
              f"{cleared}")
    # THE REFILL IS A TICK LATER, and that is the fix of studies/agentprops 1f rather
    # than a weakening of this check. The client requires both pools EMPTY at the
    # moment the death bit clears and logs `Health non-zero on resurrect` when they
    # are not -- MEASURED at 13 of 13 revives with the burst order and 0 of 11 with
    # one tick between. So the revive must NOT carry the refill...
    early = [v for op, v in rev
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(not early,
              "the revive does NOT refill the pool in the same burst",
              f"{early} -- a refill here is what the client complained about, "
              f"13 of 13 revives")
    # ...and the deferred half must actually send it, or a body stands up empty. The
    # two checks are a pair on purpose: either alone is satisfied by a broken server.
    state["player_refill_due_at"] = time.time() - 1.0
    late = []
    authsrv.player_refill_due(
        lambda op, v, label="", quiet=False: late.append((op, v)), state, 1)
    rev = late
    refill = [struct.unpack("<f", struct.pack("<I", v[-1]))[0] for op, v in rev
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(refill == [1.0],
              "and the DEFERRED half refills the pool with 1.0, the SETTER's value",
              f"{refill} -- max_health here is what crashed the client on "
              "2026-08-11, and the same guard covers this call site")

    # 6a. a mis-declared agent does not swing every tick. Attack speed 0 is the
    #     value that took the client down on m_attackInterval, and `or` sends it
    #     to a real interval rather than to "no wait at all".
    zero = _sworld()
    zero["agents"][10]["attack_speed"] = 0.0
    LEDGER.ok(len(_swings(zero, n=8)) == 2,
              "an agent declaring attack speed 0 falls back to a real interval",
              "8 ticks, ONE swing opening (a turn and an attack_started) -- 0.0 "
              "is falsy, and treating it as "
              "'unset' is deliberate: it is the value behind the "
              "m_attackInterval assert. One message rather than three because a "
              "swing now opens and lands separately")

    # 6. the swing honours the AGENT's declared speed, not the player's. The
    #    client was told this agent's attack speed at spawn and animates to it.
    state = _sworld()
    state["agents"][10]["attack_speed"] = 10.0
    n = len(_swings(state, n=6))
    LEDGER.ok(n == 2,
              "and a slow weapon swings once, not once per tick",
              f"{n} message(s) over 6 ticks at a 10 s interval -- an opening is a "
              "turn plus an attack_started, so anything above 2 means the timer is "
              "not being read")


def _walk(state, n=1, elapsed=1.0):
    """Run enemy_move_tick n times, each pretending `elapsed` seconds passed."""
    import authsrv
    sent = []
    for _ in range(n):
        for a in state.get("agents", {}).values():
            a["moved_at"] = time.time() - elapsed
        authsrv.enemy_move_tick(
            lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
            state, 1)
    return sent


class _Wall:
    """A pathmap that refuses to let anything WEST of x = 400.

    The agent starts east of the player and walks toward the origin, so the wall
    clamps from below. The first version clamped from above and never blocked
    anything -- a fixture that cannot fail is the same defect as a check that
    cannot fail, one layer down.
    """

    def __init__(self):
        self.asked = 0

    def clip(self, x0, y0, x1, y1, step=16.0):
        self.asked += 1
        return (max(x1, 400.0), y1)


class _Corner:
    """The wedge, in miniature: clip() cannot leave, route() can.

    This is RUN-1zBW's measured geometry reduced to a fixture. The server's
    Hatcher sat at a walkable point ~7 u from a trapezoid edge where clip()
    returned 0.000 u in every one of 24 probed directions, while pm.route from
    that same point found a path 49 times out of 49.

    The corridor deliberately runs the WRONG WAY first (+x, away from a player
    at -x), because that is what escaping a corner looks like and it is what
    trips a straight-line leash.
    """

    def __init__(self, escape=True):
        self.escape = escape
        self.routes = 0
        self.clips = 0

    def clip(self, x0, y0, x1, y1, step=16.0):
        self.clips += 1
        # Nothing may leave the corner in a straight line -- but movement
        # ALONG the corridor is allowed, which is what makes the two arms
        # differ rather than the fixture just freezing everything.
        if x1 > x0 + 1e-9:                 # eastward: the escape lane
            return (x1, y1)
        return (x0, y0)

    def route(self, x0, y0, x1, y1, **kw):
        self.routes += 1
        if not self.escape:
            return None
        return [(x0, y0), (x0 + 300.0, y0), (x1, y1)]


def _follow_world(agent_pos, player_pos):
    import authsrv
    entry = {"name": "hatcher", "dead": False, "pos": agent_pos, "plane": 0,
             "moving": True, "moved_at": 0.0,
             "follow": {"told": player_pos, "sent_at": 0.0, "t0": 0.0},
             "allegiance": agents.ALLEGIANCE_HOSTILE}
    return {"agents": {10: entry}, "pos": player_pos, "player_dead": False}


def _follow_run(state, pm, seconds=4.0, hz=20.0):
    """Drive _npc_follow_tick directly, returning (u travelled, halt labels)."""
    import authsrv
    import math as _m
    ag = state["agents"][10]
    px, py = state["pos"]
    halts, moved, prev, now = [], 0.0, ag["pos"], 0.0
    dt = 1.0 / hz
    state.setdefault("_follows", [])

    def _cap(op, vals, label="", quiet=False):
        if "halts at (" in label:
            halts.append(label)
        elif op == authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION:
            state["_follows"].append(vals)      # 1z-bz reads the plane words

    while now < seconds:
        now += dt
        ax, ay = ag["pos"]
        d = _m.hypot(px - ax, py - ay)
        authsrv._npc_follow_tick(_cap, state, 1, 10, ag, (px, py), d, now, pm)
        moved += _m.dist(prev, ag["pos"])
        prev = ag["pos"]
    return moved, halts


def section_follow_router():
    """MOVECODE-1z-by: the hostile's OWN copy walks a routed corridor.

    RUN-1zBW measured what the straight line costs: the copy wedged 7 u from a
    trapezoid edge, all 15 later follow orders clipped 0.000 u, the chase was
    dead for 155 s, and the client drew the body 965.6 u away -- which nothing
    in the protocol can reconcile, since 0x0028 carries no point and an NPC
    never receives a 0x002C. On the real mesh the routed arm walks 2,174.8 u
    out of that corner and halts inside the 80 u disc where the straight-line
    arm walks 0.0 u and never arrives.
    """
    import authsrv
    import math as _m
    print("\nMOVECODE-1z-by: the NPC follow's own copy walks a ROUTED corridor")
    LEDGER.ok(authsrv.NPC_FOLLOW_ROUTER is True
              and "--no-npc-follow-router" in open(
                  authsrv.__file__, encoding="utf-8").read()
              and authsrv.capture_flags().get("NPC_FOLLOW_ROUTER") is True,
              "it ships ON with its revert flag, and the capture records which "
              "arm produced the run",
              "a run whose header cannot name the arm costs a later session a "
              "reconstruction")

    saved = authsrv.NPC_FOLLOW_ROUTER
    # NPCTRACK-Q1 (2026-09-06): the corridor integrator this section exercises
    # is now the REVERT arm (--no-npc-client-model). Under the default the copy
    # is the client's own sync copy, which dead-reckons straight and never
    # wedges -- and never routes. Everything below is about the corridor, so
    # it runs on that arm; section_client_model covers the default.
    saved_model = authsrv.NPC_CLIENT_MODEL
    authsrv.NPC_CLIENT_MODEL = False
    try:
        # THE KNOWN-BAD ARM FIRST, so the fixture is proved able to freeze a
        # chase before the fix is credited with unfreezing one.
        authsrv.NPC_FOLLOW_ROUTER = False
        pm = _Corner()
        st = _follow_world((0.0, 0.0), (-400.0, 0.0))
        off_moved, off_halts = _follow_run(st, pm)
        LEDGER.ok(off_moved == 0.0 and not off_halts,
                  "REVERT ARM (--no-npc-follow-router): the copy cannot leave "
                  "the corner at all and the chase never arrives -- 0.0 u, "
                  "which is RUN-1zBW's measured 15-of-15",
                  f"moved {off_moved:.2f} u, halts {off_halts}")
        LEDGER.ok(pm.routes == 0,
                  "and the revert arm asks the router NOTHING, so the two arms "
                  "differ in the one thing under test",
                  f"{pm.routes} route call(s)")

        authsrv.NPC_FOLLOW_ROUTER = True
        pm = _Corner()
        st = _follow_world((0.0, 0.0), (-400.0, 0.0))
        on_moved, on_halts = _follow_run(st, pm)
        ag = st["agents"][10]
        LEDGER.ok(on_moved > 300.0,
                  "ROUTED: the same copy in the same corner walks the corridor "
                  "out",
                  f"moved {on_moved:.1f} u to {ag['pos']}")
        LEDGER.ok(pm.routes >= 1,
                  "by actually asking the router", f"{pm.routes} route call(s)")
        LEDGER.ok(on_moved > off_moved,
                  "and the arms are ordered the right way round -- the fix "
                  "moves the copy and the known-bad arm does not",
                  f"{on_moved:.1f} u against {off_moved:.1f} u")

        # ONE A* PER FOLLOW_ROUTE_RETRY, not per tick: 4 s at 20 Hz is 80 ticks.
        LEDGER.ok(pm.routes <= int(4.0 / authsrv.FOLLOW_ROUTE_RETRY) + 2,
                  "the corridor is CACHED -- at most one solve per "
                  f"FOLLOW_ROUTE_RETRY ({authsrv.FOLLOW_ROUTE_RETRY} s), not "
                  "one per tick",
                  f"{pm.routes} solves over 80 ticks")

        # NO ROUTE -> the straight-line clip, unchanged. Not a crash, not a stall.
        pm = _Corner(escape=False)
        st = _follow_world((0.0, 0.0), (-400.0, 0.0))
        none_moved, _ = _follow_run(st, pm)
        LEDGER.ok(pm.routes >= 1 and none_moved == 0.0,
                  "route() returning None falls back to the straight-line clip "
                  "rather than raising or freezing differently",
                  f"{pm.routes} solves, moved {none_moved:.2f} u")

        # A MESH WITH NO route() AT ALL -- every older fixture, and a bare
        # machine. It must degrade, not explode.
        class _Old:
            def clip(self, x0, y0, x1, y1, step=16.0):
                return (x0, y0)
        st = _follow_world((0.0, 0.0), (-400.0, 0.0))
        old_moved, _ = _follow_run(st, _Old())
        LEDGER.ok(old_moved == 0.0,
                  "a pathmap with no route() at all degrades to the clip arm "
                  "instead of raising -- every pre-1z-by fixture is one",
                  f"moved {old_moved:.2f} u")

        # THE LEASH MAY NOT BE TRIPPED BY OUR OWN DETOUR. The corridor runs
        # +300 x away from a player at -x, so the straight-line distance grows;
        # on the real capture that leashed the chase 3 s EARLY.
        far = -(authsrv.AGGRO_RANGE - 150.0)      # inside the leash, near its edge
        pm = _Corner()
        st = _follow_world((0.0, 0.0), (far, 0.0))
        _m2, halts = _follow_run(st, pm, seconds=1.0)
        LEDGER.ok(not any("leash" in h for h in halts),
                  "a corridor that detours AWAY from the player does not leash "
                  "the chase: the leash reads the corridor's solve point too "
                  "and takes the min, which cannot fire earlier than the "
                  "straight-line arm would",
                  f"halts {halts}")
        # ...and a player who genuinely leaves still leashes.
        st = _follow_world((0.0, 0.0), (-(authsrv.AGGRO_RANGE + 400.0), 0.0))
        _m3, halts2 = _follow_run(st, _Corner(), seconds=0.2)
        LEDGER.ok(any("leash" in h for h in halts2),
                  "CONTROL: a player genuinely past the leash still ends the "
                  "chase -- the guard above did not simply disable it",
                  f"halts {halts2}")
    finally:
        authsrv.NPC_FOLLOW_ROUTER = saved
        authsrv.NPC_CLIENT_MODEL = saved_model


class _Stairs:
    """Ground is plane 0; x >= 500 is plane 29, the stairs. y > 900 the mesh cannot name.

    This is ANIMREF-RE 42.5's own PASS shape reduced to a fixture: a (29, 0)
    follow at the foot and (29, 29) after the crossing. The unnameable strip
    exists because plane_at returns None rather than guessing, and the fallback
    for None is the thing 42.5 spells out.
    """

    def clip(self, x0, y0, x1, y1, step=16.0):
        return (x1, y1)

    def plane_at(self, x, y, prefer=None):
        if y > 900.0:
            return None
        return 29 if x >= 500.0 else 0


class _Terrace(_Stairs):
    """_Stairs that also answers planes_at: the strip y > 900 has NO trapezoid
    (the terrace above map 146's stairs, GROUNDZ-F11), everything else one."""

    def planes_at(self, x, y):
        if y > 900.0:
            return set()
        return {29} if x >= 500.0 else {0}


def section_plane_reach():
    """GROUNDZ-F11: where the mesh has no trapezoid under the mover, the player's
    reported plane names ground within reach.

    The operator's own session (2026-09-06, capture 154850, feel-agenttap):
    the Hatcher followed them onto the terrace above the stairs, where our mesh
    has no trapezoid at any of its points for 16 s; `_npc_plane` held its
    carried 29, the client resolved its height on a plane with no surface
    there (its reader answered the cached -1050.1 across 230 u of walking) and
    drew it 52 u into the ground beside a player standing on plane 0 at -1102.
    The player's own report -- plane 0, 8-45 u from the same points -- was the
    word that was right.
    """
    import authsrv
    MOVE = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    print("\nGROUNDZ-F11: the player's reported plane names ground our mesh does "
          "not cover, within the follow's reach")
    LEDGER.ok(authsrv.NPC_PLANE_REACH is True
              and "--no-npc-plane-reach" in open(
                  authsrv.__file__, encoding="utf-8").read()
              and authsrv.capture_flags().get("NPC_PLANE_REACH") is True,
              "it ships ON with its revert flag, recorded in the capture header")
    pm = _Terrace()
    saved = authsrv.NPC_PLANE_REACH
    try:
        # THE MEASURED SHAPE: the mover in the strip, carrying 29 from the
        # stairs; the player 60 u away reporting plane 0. Field 4 reads 0.
        st = _fresh_follow((520.0, 950.0), (580.0, 950.0), player_plane=0,
                           agent_plane=29)
        _follow_run(st, pm, seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(st["agents"][10]["plane"] == 0,
                  "on ground our mesh does not cover, 60 u from a player who "
                  "reported plane 0, the mover's word becomes 0 (was the "
                  "carried 29 -- the terrace sink); in reach no follow goes "
                  "out, the word is what the correction and the next order carry",
                  f"agent plane {st['agents'][10]['plane']}")
        # OUT OF REACH: the same strip, the player 200 u away -> the carry.
        st = _fresh_follow((520.0, 950.0), (720.0, 950.0), player_plane=0,
                           agent_plane=29)
        _follow_run(st, pm, seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(fol is not None and fol[3] == 29,
                  "200 u from the player the report says nothing about the "
                  "mover's ground: the carried word stands, as 42.5 wrote it",
                  f"{fol[2:4] if fol else fol}")
        # ON THE DISC ITSELF (RUN-1zCE): the model parks at exactly
        # follow_stop_radius() from the frame, and the reach test used to sit on
        # that same number -- R3's park at 79.96 u fired, 1zCE's at 80.02 u did
        # not, and the hostile spent 7.9 s on plane 29 with its height cached.
        # The disc, and the swing's own deadband beyond it, must name the ground.
        st = _fresh_follow((520.0, 950.0), (600.0, 950.0), player_plane=0,
                           agent_plane=29)
        _follow_run(st, pm, seconds=0.05)
        LEDGER.ok(st["agents"][10]["plane"] == 0,
                  "a mover parked EXACTLY on the disc (80.0 u from the report) "
                  "on uncovered ground takes the reported plane -- the knife "
                  "edge RUN-1zCE fell off", f"agent plane {st['agents'][10]['plane']}")
        st = _fresh_follow((520.0, 950.0),
                           (520.0 + authsrv.follow_stop_radius()
                            + authsrv.NPC_PLANE_REACH_SLACK - 1.0, 950.0),
                           player_plane=0, agent_plane=29)
        _follow_run(st, pm, seconds=0.05)
        LEDGER.ok(st["agents"][10]["plane"] == 0
                  and authsrv.NPC_PLANE_REACH_SLACK == authsrv.BOUNDING_RADIUS,
                  "one step short of the slack's end it still does, and the slack "
                  "is the swing's own deadband (enemy_reach - the disc), not a "
                  "number of its own", f"agent plane {st['agents'][10]['plane']}")
        # A SEAM IS NOT SILENCE: on named ground the mesh's own answer wins
        # even with the player in reach on another plane.
        st = _fresh_follow((520.0, 0.0), (580.0, 0.0), player_plane=0,
                           agent_plane=0)
        _follow_run(st, pm, seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(st["agents"][10]["plane"] == 29,
                  "where the mesh HAS a trapezoid under the mover its plane is "
                  "the answer -- the report never overrules named ground",
                  f"agent plane {st['agents'][10]['plane']}")
        # A MESH WITHOUT planes_at: every pre-F11 stub -> the carry, no raise.
        st = _fresh_follow((520.0, 950.0), (580.0, 950.0), player_plane=0,
                           agent_plane=29)
        _follow_run(st, _Stairs(), seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(st["agents"][10]["plane"] == 29,
                  "a pathmap with no planes_at() degrades to the carried word "
                  "instead of raising", f"agent plane {st['agents'][10]['plane']}")
        # THE PARKED BRANCH: this is where the operator's Hatcher sat for 16 s.
        # With the word re-named, GROUNDZ-F9's correction goes out at once.
        st = _parked(agent_plane=29, told=29, player=(580.0, 950.0),
                     pos=(520.0, 950.0))
        st["plane"] = 0
        sent = _tick_parked(st, pm)
        mv = [s for s in sent if s[0] == MOVE]
        LEDGER.ok(len(mv) == 1 and mv[0][1][2] == 0 and mv[0][1][3] == 0
                  and st["agents"][10]["plane"] == 0,
                  "a hostile PARKED on uncovered ground beside a player on "
                  "plane 0 gets F9's zero-distance 0x0029 carrying 0 -- the "
                  "send the terrace never got",
                  f"{mv}")
        # THE KNOWN-BAD ARM: the flag off, the same park sends nothing and
        # the word stays 29 -- the 16 s of sink, reproduced.
        authsrv.NPC_PLANE_REACH = False
        st = _parked(agent_plane=29, told=29, player=(580.0, 950.0),
                     pos=(520.0, 950.0))
        st["plane"] = 0
        sent = _tick_parked(st, pm)
        LEDGER.ok(not [s for s in sent if s[0] == MOVE]
                  and st["agents"][10]["plane"] == 29,
                  "REVERT ARM (--no-npc-plane-reach): the same park holds 29 "
                  "and sends nothing -- the operator's screenshot",
                  f"plane {st['agents'][10]['plane']}, sends "
                  f"{[hex(s[0]) for s in sent]}")
    finally:
        authsrv.NPC_PLANE_REACH = saved
    LEDGER.ok(authsrv.NPC_PLANE_REACH is True,
              "and the module global is restored after the revert arm")


def _parked(agent_plane, told, player=(560.0, 0.0), pos=(520.0, 0.0)):
    """A hostile PARKED IN REACH with no follow -- the exact branch RUN-GROUNDZ-R1's
    sunken Hatcher sat in for 22 s. `told` is the plane word its last order carried."""
    import authsrv
    st = _follow_world(pos, player)
    st["plane"] = 29
    ag = st["agents"][10]
    ag["follow"] = None
    ag["moving"] = False
    ag["plane"] = agent_plane
    ag["plane_told"] = told
    ag["plane_told_at"] = 0.0
    return st


def _tick_parked(state, pm, now=10.0):
    """One _npc_follow_tick, returning every send it made."""
    import authsrv
    import math as _m
    ag = state["agents"][10]
    px, py = state["pos"]
    sent = []
    ax, ay = ag["pos"]
    authsrv._npc_follow_tick(
        lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
        state, 1, 10, ag, (px, py), _m.hypot(px - ax, py - ay), now, pm)
    return sent


def section_plane_repath():
    """GROUNDZ-Q5: a stationary hostile's plane word is corrected when it goes stale.

    RUN-GROUNDZ-R1 measured the whole chain live. The follow resolves field 4 AT
    SEND TIME; the hostile crossed onto plane-29 ground 0.6 s AFTER its last
    order (our own mesh answers 29 cleanly at the point it stopped on, so this
    is not a stale-mesh problem); it arrived; the halt carries no plane; and
    nothing re-sends to a parked body in reach. The client held plane 0 for the
    whole 22 s hold, MapQueryAltitude skipped the prop branch -- which it does
    whenever the plane is 0 -- and drew the body 32.5 u down in the terrain.
    """
    import authsrv
    MOVE = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    print("\nGROUNDZ-Q5: the plane word a STATIONARY hostile is left holding")
    LEDGER.ok(authsrv.NPC_PLANE_REPATH is True
              and "--no-plane-repath" in open(
                  authsrv.__file__, encoding="utf-8").read()
              and authsrv.capture_flags().get("NPC_PLANE_REPATH") is True,
              "it ships ON with its revert flag, recorded in the capture header",
              "the revert covers BOTH faces -- the stationary correction and the "
              "plane-change re-path")

    pm = _Stairs()
    saved = authsrv.NPC_PLANE_REPATH
    try:
        # THE MEASURED CASE: parked, in reach, plane went 0 -> 29 after the last
        # order. Nothing else in the tick sends to this agent.
        st = _parked(agent_plane=29, told=0)
        sent = _tick_parked(st, pm)
        mv = [s for s in sent if s[0] == MOVE]
        LEDGER.ok(len(mv) == 1 and mv[0][1][0] == 10
                  and mv[0][1][2] == 29 and mv[0][1][3] == 29,
                  "a parked hostile whose plane moved since its last order gets "
                  "ONE zero-distance 0x0029 carrying the corrected plane in both "
                  "words -- the branch that previously sent nothing at all",
                  f"{mv}")
        LEDGER.ok(mv and list(mv[0][1][1]) == [520.0, 0.0],
                  "and it is addressed to the point the client already has it "
                  "on, so there is nowhere for the body to walk",
                  f"{mv[0][1][1] if mv else None}")
        LEDGER.ok(st["agents"][10]["plane_told"] == 29,
                  "the word we told it is remembered, so the correction does not "
                  "repeat")

        # NO CHANGE -> NO SEND. Without this the fix would be a per-tick storm.
        st = _parked(agent_plane=29, told=29)
        LEDGER.ok(not [s for s in _tick_parked(st, pm) if s[0] == MOVE],
                  "a parked hostile whose plane has NOT moved sends nothing",
                  "this is the check that keeps the fix from being a storm")

        # THE RATE FLOOR, on the same clock the rest of the NPC path uses.
        st = _parked(agent_plane=29, told=0)
        st["agents"][10]["plane_told_at"] = 9.9        # 0.1 s ago
        LEDGER.ok(not [s for s in _tick_parked(st, pm, now=10.0) if s[0] == MOVE],
                  "and one inside FOLLOW_REPATH_INTERVAL is refused -- a body "
                  "oscillating on a seam cannot turn this into a storm",
                  f"floor {authsrv.FOLLOW_REPATH_INTERVAL} s")

        # THE OTHER FACE: a plane change mid-walk re-paths, without waiting for
        # the player to travel FOLLOW_REPATH_MOVED.
        st = _fresh_follow((0.0, 0.0), (900.0, 0.0), player_plane=29)
        _follow_run(st, pm, seconds=0.05)              # opens the follow
        ag = st["agents"][10]
        ag["pos"] = (600.0, 0.0)                       # now on plane 29
        ag["follow"]["sent_at"] = 0.0                  # clear the rate floor
        ag["follow"]["told"] = (900.0, 0.0)            # the player has NOT moved
        sent = _tick_parked(st, pm, now=5.0)
        dest = [s for s in sent
                if s[0] == authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION]
        LEDGER.ok(len(dest) == 1 and dest[0][1][3] == 29,
                  "MID-WALK: our own plane changing re-paths the follow even "
                  "though the player has not moved at all -- on a staircase "
                  "that is exactly when it matters",
                  f"{dest}")

        # THE KNOWN-BAD ARM: with the flag off, the same stale word stands.
        authsrv.NPC_PLANE_REPATH = False
        st = _parked(agent_plane=29, told=0)
        LEDGER.ok(not [s for s in _tick_parked(st, pm) if s[0] == MOVE],
                  "REVERT ARM (--no-plane-repath): the identical stale word "
                  "produces NO correction -- RUN-GROUNDZ-R1's 22 s of plane 0 "
                  "reproduced, so this section's positive is the fix and not "
                  "the fixture",
                  "32.5 u of sink is what that arm measured")
    finally:
        authsrv.NPC_PLANE_REPATH = saved
    LEDGER.ok(authsrv.NPC_PLANE_REPATH is True,
              "and the module global is restored after the revert arm")

class _Flat:
    """Open ground, plane 0 everywhere: the model is the thing under test."""

    def clip(self, x0, y0, x1, y1, step=16.0):
        return (x1, y1)

    def plane_at(self, x, y, prefer=None):
        return 0


def _model_pos(state):
    p = state["agents"][10]["pos"]
    return (round(p[0], 1), round(p[1], 1))


def section_client_model():
    """NPCTRACK-Q1: the hostile's copy is the client's own sync copy.

    Measured on three stairs runs (studies/npctrack/FINDINGS.md): at the halt
    the server's copy of the Hatcher sat a median 53.8 u from the body the
    client drew, while the client's own two copies agreed to 12 u -- the
    server's corridor integrator was the drift. The client walks its sync copy
    STRAIGHT to the ordered point and stops it at r+r+56 from the player's
    world-0 copy inside a forward cone (ANIMREF-RE 38.2); agtrack_mirror's
    SyncAgent plus that disc reproduces the tape to 11.6 u at the halts.
    """
    import authsrv
    FOLLOW = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    HALT = authsrv.GAME_SMSG_AGENT_STOP_MOVING
    SPEED = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED
    MOVE = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    stop = authsrv.follow_stop_radius()
    print("\nNPCTRACK-Q1: the hostile's copy is the client's own dead-reckoner")
    LEDGER.ok(authsrv.NPC_CLIENT_MODEL is True
              and "--no-npc-client-model" in open(
                  authsrv.__file__, encoding="utf-8").read()
              and authsrv.capture_flags().get("NPC_CLIENT_MODEL") is True,
              "it ships ON with its revert flag, recorded in the capture header")
    pm = _Flat()
    saved = authsrv.NPC_CLIENT_MODEL
    try:
        # 1. THE STANDING CASE reproduces section_chase's own pin: player at
        #    the origin, hostile 900 u out, the disc parks it at exactly 80.
        st = _fresh_follow((900.0, 0.0), (0.0, 0.0), player_plane=0)
        sent = _tick_parked(st, pm, now=0.0)
        LEDGER.ok([op for op, _v, _l in sent] == [SPEED, FOLLOW],
                  "the opening tick still announces a rate and ONE follow",
                  f"{[hex(op) for op, _v, _l in sent]}")
        _tick_parked(st, pm, now=1.0)
        LEDGER.ok(_model_pos(st) == (612.0, 0.0),
                  "one second later the copy is where the client's dead-"
                  "reckoner puts it: 288 u along the ordered line",
                  f"{_model_pos(st)} -- +0x78 + v * dt, agtrack_mirror.SyncAgent")
        st["agents"][10]["follow"]["sent_at"] = 29.9   # the clock is fresh
        _tick_parked(st, pm, now=30.0)
        d = math.hypot(*st["agents"][10]["pos"])
        LEDGER.ok(abs(d - stop) < 0.5,
                  "and a huge step parks it at the disc, 80 u out, solved on "
                  "the leg's own line rather than sub-stepped",
                  f"{d:.2f} u against {stop:.0f}")
        fol = st["agents"][10]["follow"]
        LEDGER.ok(fol is not None and fol.get("arrived_at") is not None,
                  "the park IS the arrival, and the halt waits for the clock "
                  "(ANIMREF-RE 40.9)")
        fol["sent_at"] -= 0.6
        halted = _tick_parked(st, pm, now=30.05)
        LEDGER.ok([op for op, _v, _l in halted] == [HALT]
                  and st["agents"][10]["follow"] is None
                  and abs(math.hypot(*st["agents"][10]["pos"]) - stop) < 0.5,
                  "the halt is ONE bare 0x0028 and the model does not move "
                  "under it -- the client's copy was already parked",
                  f"{[hex(op) for op, _v, _l in halted]} at "
                  f"{math.hypot(*st['agents'][10]['pos']):.1f} u")

        # 2. THE DIVERGENCE the tapes measured (F4): the client's world-0 copy
        #    of the player stands 300 u to the side of the server's copy. The
        #    ordered point is state["pos"]; the client walks to it and the disc
        #    (around world-0) never fires, so the copy arrives AT the point.
        #    The old integrator would park 80 u from state["pos"]. That 80 u
        #    is the arms' difference and the model's answer is the client's.
        st = _fresh_follow((900.0, 0.0), (0.0, 0.0), player_plane=0)
        st["last_report"] = (0.0, 300.0, True, 0.0)     # standing, world-0 here
        _tick_parked(st, pm, now=0.0)
        _tick_parked(st, pm, now=10.0)
        LEDGER.ok(_model_pos(st) == (0.0, 0.0),
                  "DIVERGENCE: with the client's frame 300 u aside, the copy "
                  "walks all the way to the ORDERED point -- the disc never "
                  "fires -- which is what 24 of 40 measured halts showed",
                  f"{_model_pos(st)}")
        authsrv.NPC_CLIENT_MODEL = False
        st = _fresh_follow((900.0, 0.0), (0.0, 0.0), player_plane=0)
        st["last_report"] = (0.0, 300.0, True, 0.0)
        _tick_parked(st, pm, now=0.0)
        _tick_parked(st, pm, now=10.0)
        authsrv.NPC_CLIENT_MODEL = saved
        LEDGER.ok(abs(math.hypot(*st["agents"][10]["pos"]) - stop) < 0.5,
                  "REVERT ARM (--no-npc-client-model): the same order parks "
                  "the server's copy 80 u from ITS player, blind to the frame "
                  "-- the known-bad arm, and the two differ by the 80 u the "
                  "client never walked",
                  f"{_model_pos(st)}")

        # 3. THE CONE: a frame point BEHIND the walking copy does not stop it,
        #    even inside 80 u (38.2's +-60 degree forward cone).
        st = _fresh_follow((0.0, 0.0), (900.0, 0.0), player_plane=0)
        st["last_report"] = (-50.0, 0.0, True, 0.0)     # 50 u behind
        _tick_parked(st, pm, now=0.0)
        _tick_parked(st, pm, now=1.0)
        LEDGER.ok(_model_pos(st) == (288.0, 0.0),
                  "a frame point 50 u BEHIND the copy is inside the disc and "
                  "outside the cone: no stop, the walk continues",
                  f"{_model_pos(st)}")

        # 4. THE MESSAGES, as the client's handlers apply them.
        ag = st["agents"][10]
        authsrv._npc_model_emit(ag, HALT, [10], 1.0)   # at the model's own clock (1.0 s in)
        _tick_parked(st, pm, now=5.0)
        LEDGER.ok(_model_pos(st) == (288.0, 0.0),
                  "a 0x0028 halts the model IN PLACE mid-leg, and it stays",
                  f"{_model_pos(st)} four seconds later")
        st = _fresh_follow((0.0, 0.0), (900.0, 0.0), player_plane=0)
        st["last_report"] = (-50.0, 0.0, True, 0.0)
        ag = st["agents"][10]
        authsrv._npc_model_emit(ag, SPEED, [10, 0.5], 0.0)
        authsrv._npc_model_emit(ag, FOLLOW, [10, (900.0, 0.0), 0, 0, 1], 0.0)
        authsrv._npc_model_advance(st, ag, 0.5, elapsed=0.5)
        authsrv._npc_model_emit(ag, SPEED, [10, 1.0], 0.5)  # mid-leg: ignored
        ag["follow"] = {"told": (900.0, 0.0), "sent_at": 0.0, "t0": 0.0}
        ag["moving"] = True
        ag["moved_at"] = 0.5
        _tick_parked(st, pm, now=1.0)
        LEDGER.ok(_model_pos(st) == (144.0, 0.0),
                  "a 0x002B is a pure store: the NEXT bake runs at 0.5, and "
                  "one sent MID-LEG leaves the current leg's velocity alone",
                  f"{_model_pos(st)} -- 144 u in 1 s, not 288 and not 216")
        authsrv._npc_model_emit(ag, MOVE, [10, (144.0, 0.0), 0, 0], 1.0)
        _tick_parked(st, pm, now=1.2)
        LEDGER.ok(_model_pos(st) == (144.0, 0.0) and not ag["cmodel_moving"],
                  "GROUNDZ-F9's zero-distance 0x0029 arms an arrival at the "
                  "copy's own point and moves nothing (the bake's <= 1.0 u "
                  "short-circuit)",
                  f"{_model_pos(st)}")

        # 5. RE-SEED: something else moved agent["pos"] (a respawn). The model
        #    follows it rather than dragging the body back.
        ag["pos"] = (5000.0, 5000.0)
        authsrv._npc_model_advance(st, ag, 2.0, elapsed=0.8)
        LEDGER.ok(_model_pos(st) == (5000.0, 5000.0),
                  "a teleport of agent['pos'] by anything else re-seeds the "
                  "model there", f"{_model_pos(st)}")

        # 6. THE FRAME (F5): standing report -> that point; a click in flight
        #    -> not the report; a guard -> its mirror; neither -> state["pos"].
        st = {"pos": (1.0, 2.0)}
        LEDGER.ok(authsrv._npc_frame(st, 0.0) == (1.0, 2.0),
                  "no report, no guard: the frame is state['pos']")
        st["last_report"] = (7.0, 8.0, True, 0.0)
        LEDGER.ok(authsrv._npc_frame(st, 0.0) == (7.0, 8.0),
                  "the last accepted report was a STOP: the frame is that "
                  "point (world-0 == the body when standing, 40.11)")
        st["click_moving_at"] = 0.5
        LEDGER.ok(authsrv._npc_frame(st, 0.0) == (1.0, 2.0),
                  "but not while a click leg is in flight -- the client is "
                  "silent and moving; the report is stale")

        class _Sync:
            def position(self, ms):
                return (5.0, 5.0)

        class _Mirror:
            sync = _Sync()

        class _Guard:
            mirror = _Mirror()

            def _ms(self, now):
                return 0

        st = {"pos": (1.0, 2.0), "agtrack_guard": _Guard(),
              "last_report": (7.0, 8.0, False, 0.0)}
        LEDGER.ok(authsrv._npc_frame(st, 0.0) == (5.0, 5.0),
                  "the player MOVING and a guard present: the mirror's sync "
                  "copy is the frame -- the best the server has (p50 17.5 u "
                  "at the halts against the true world-0's 11.6)")

        # 7. PARKED OUT OF REACH OF THE SERVER'S PLAYER BUT AT THE DISC OF THE
        #    CLIENT'S FRAME: the halt goes out on the clock, and then the
        #    follow WAITS for the frame to move. RUN-NPCTRACK-R1 measured the
        #    alternative: a fresh follow every 0.56 s that the model (and the
        #    client) parked at once, 37 halts in 77 s against 13 on every
        #    pinned run, seven of them at one point while the frame stood
        #    still. When the client's belief catches up, the follow opens.
        st = _fresh_follow((900.0, 0.0), (0.0, 0.0), player_plane=0)
        st["last_report"] = (200.0, 0.0, True, 0.0)     # world-0 200 u ahead
        _tick_parked(st, pm, now=0.0)
        st["agents"][10]["follow"]["sent_at"] = 9.9
        _tick_parked(st, pm, now=10.0)
        LEDGER.ok(abs(st["agents"][10]["pos"][0] - 280.0) < 0.5
                  and abs(st["agents"][10]["pos"][1]) < 0.5
                  and st["agents"][10]["follow"].get("arrived_at") is not None,
                  "the disc around a frame 200 u from the server's player "
                  "parks the copy at 280 u -- out of reach, and ARRIVED",
                  f"{_model_pos(st)}")
        st["agents"][10]["follow"]["sent_at"] -= 0.6
        a = _tick_parked(st, pm, now=10.05)
        b = _tick_parked(st, pm, now=10.10)
        c = _tick_parked(st, pm, now=10.60)
        LEDGER.ok([op for op, _v, _l in a] == [HALT]
                  and not b and not c
                  and st["agents"][10]["follow"] is None,
                  "it halts on the clock where it stands, and then HOLDS: no "
                  "fresh follow while the copy is inside reach of the client's "
                  "frame (F8 -- the follow would only park again)",
                  f"{[hex(op) for op, _v, _l in a]} then {b} then {c}")
        LEDGER.ok(not _swings(st),
                  "and it does not swing from there either -- the swing reads "
                  "the server's own player, 280 u away",
                  "faithful on both counts: the client draws it parked")
        st["last_report"] = (0.0, 0.0, True, 10.6)      # the belief catches up
        d = _tick_parked(st, pm, now=10.65)
        LEDGER.ok([op for op, _v, _l in d] == [SPEED, FOLLOW],
                  "and the moment the client's frame moves out of reach the "
                  "follow opens -- a fresh one, not a resumed walk",
                  f"{[hex(op) for op, _v, _l in d]}")
    finally:
        authsrv.NPC_CLIENT_MODEL = saved
    LEDGER.ok(authsrv.NPC_CLIENT_MODEL is True,
              "and the module global is restored after the revert arm")


def section_npc_plane():
    """ANIMREF-RE 42.5, shipped: the follow's plane words track the mover.

    Retail's server tracks each NPC's current plane -- 1,164 NPC-addressed
    0x0029 carry field 3 != field 4 and 128 of 377 NPCs change their words over
    a session. Ours stamped the SPAWN plane into both, which equals retail only
    on flat ground; RUN-1zBW sent four follow orders onto plane-18-only bridge
    deck all stamped plane 0 while the operator watched the Hatcher walk
    underneath.
    """
    import authsrv
    print("\nANIMREF-RE 42.5 / MOVECODE-1z-bz: the follow's plane words track "
          "the mover")
    LEDGER.ok(authsrv.NPC_PLANE_TRACK is True
              and "--no-npc-plane-track" in open(
                  authsrv.__file__, encoding="utf-8").read()
              and authsrv.capture_flags().get("NPC_PLANE_TRACK") is True,
              "it ships ON with its revert flag, recorded in the capture header",
              "the revert is also how the (cur, cur) fallback would be tested "
              "if the client refuses (dest, cur)")

    pm = _Stairs()
    saved = authsrv.NPC_PLANE_TRACK
    try:
        # AT THE FOOT: the mover is on the ground, the player is up the stairs.
        st = _fresh_follow((0.0, 0.0), (600.0, 0.0), player_plane=29)
        _follow_run(st, pm, seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(fol is not None and fol[2] == 29 and fol[3] == 0,
                  "AT THE FOOT the follow reads (29, 0): field 3 the "
                  "DESTINATION's plane, field 4 the MOVER's -- 42.5's derived "
                  "shape, and the case the old code could not express",
                  f"{fol[2]}/{fol[3]} -- retail's NPC 11 climbs (13, 0) then "
                  f"(13, 13) then (0, 13)")

        # AFTER THE CROSSING the mover is on 29 too, and the words equalise.
        st = _fresh_follow((520.0, 0.0), (900.0, 0.0), player_plane=29,
                           agent_plane=0)        # still carrying the stale spawn word
        _follow_run(st, pm, seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(fol is not None and fol[2] == 29 and fol[3] == 29,
                  "AFTER THE CROSSING it reads (29, 29) -- and note field 4 "
                  "corrected itself from the stale spawn 0 without any step, "
                  "because it is resolved at the copy's own point",
                  f"{fol[2:4] if fol else fol}")

        # THE MOVER'S PLANE IS TRACKED AS THE COPY STEPS.
        st = _fresh_follow((0.0, 0.0), (900.0, 0.0), player_plane=29)
        _follow_run(st, pm, seconds=3.0)
        LEDGER.ok(st["agents"][10]["plane"] == 29
                  and st["agents"][10]["pos"][0] >= 500.0,
                  "the mover's own plane FOLLOWS it across: the copy walked "
                  "past x=500 and agent['plane'] became 29",
                  f"pos {st['agents'][10]['pos']} plane "
                  f"{st['agents'][10]['plane']}")

        # THE MESH CANNOT SAY -> the mover's plane, per 42.5, NOT -1 and not a guess.
        st = _fresh_follow((0.0, 0.0), (600.0, 950.0), player_plane=29)
        _follow_run(st, pm, seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(fol is not None and fol[2] == 0 and fol[3] == 0,
                  "where the mesh CANNOT name the destination's plane, field 3 "
                  "falls back to the mover's -- 42.5's wording, and never -1 "
                  "(the word field's extension is UNDECIDABLE)",
                  f"{fol[2:4] if fol else fol}")
        LEDGER.ok(fol is not None and all(isinstance(v, int) and v >= 0
                                         for v in (fol[2], fol[3])),
                  "and both words stay non-negative ints on every path above",
                  f"{fol[2:4] if fol else fol!r}")

        # A MESH WITH NO plane_at AT ALL -- every pre-1z-bz fixture.
        class _Flat:
            def clip(self, x0, y0, x1, y1, step=16.0):
                return (x1, y1)
        st = _fresh_follow((0.0, 0.0), (600.0, 0.0), player_plane=29,
                           agent_plane=7)
        _follow_run(st, pm=_Flat(), seconds=0.05)
        fol = _last_follow(st)
        LEDGER.ok(fol is not None and fol[2] == 7 and fol[3] == 7,
                  "a pathmap with no plane_at() degrades to the agent's own "
                  "word twice instead of raising",
                  f"{fol[2:4] if fol else fol}")

        # THE KNOWN-BAD ARM: the frozen spawn plane, on the SAME crossing order.
        authsrv.NPC_PLANE_TRACK = False
        st = _fresh_follow((0.0, 0.0), (600.0, 0.0), player_plane=29)
        _follow_run(st, pm, seconds=3.0)
        fol = _last_follow(st)
        LEDGER.ok(fol is not None and fol[2] == 0 and fol[3] == 0
                  and st["agents"][10]["plane"] == 0,
                  "REVERT ARM (--no-npc-plane-track): the same crossing order "
                  "reads (0, 0) and the mover's plane never moves off its "
                  "spawn word -- RUN-1zBW's 49 of 49, reproduced",
                  f"{fol[2:4] if fol else fol}, agent plane "
                  f"{st['agents'][10]['plane']}")
        LEDGER.ok(True,
                  "so the section's positives are the fix and not the fixture: "
                  "the same geometry gives (29, 0) with the flag on and (0, 0) "
                  "with it off")
    finally:
        authsrv.NPC_PLANE_TRACK = saved


def _fresh_follow(agent_pos, player_pos, player_plane, agent_plane=0):
    """A world whose hostile has NOT set off yet, so the OPENING follow order
    fires on the first tick. _follow_world pre-arms the follow, which suppresses
    the send entirely -- this section's first draft read an empty list because
    of it, which is a fixture that measured nothing rather than a fix that
    failed."""
    st = _follow_world(agent_pos, player_pos)
    st["plane"] = player_plane
    st["agents"][10]["follow"] = None
    st["agents"][10]["moving"] = False
    st["agents"][10]["plane"] = agent_plane
    return st


def _last_follow(state):
    fols = state.get("_follows") or []
    return fols[-1] if fols else None


def section_chase():
    """It follows the player, and halts where the client's own disc parks it.

    THREE SHAPES, IN ORDER. First `AGGRO_RANGE` did two jobs -- when a hostile
    NOTICES the player and when it can REACH them -- so a Hatcher rooted to its
    spawn swung at anything within 1200 units, across a courtyard it never
    crossed. Then (2026-08-11) the chase: a 0x0029 to the player's point,
    stopping at an invented 150 u to swing. Now (ANIMREF-RE 40, 2026-09-02)
    retail's shape, OBSERVED on 7 live chases by 6 hostiles: ONE 0x002A whose
    point is the server's copy of the player and whose fifth field NAMES the
    player, re-pathed every 0.5 s while they move and never while they stand,
    nothing else on the wire (no facing, no 0x0029), no swing while the follow
    is in flight, the client's own resolver parking the body at r+r+56 = 80 u
    (sec.38.2) and a bare 0x0028 marking the halt on the wire (5/7). The
    legacy arm is one flag away (--legacy-npc-chase) and the last block here
    runs it, so a run can convict either shape alone.

    The reach a hostile swings from is its HALT disc plus one bounding radius,
    follow_stop_radius() + BOUNDING_RADIUS = 92 u -- CORRECTED sec.40.1 after
    the operator's CASE 8 run: the first cut borrowed the player's 144 u press
    reach and the Hatcher stood and swung across an 80-144 u band ("attacks
    from a distance"). The tapes swing at the halt (~80); 92 is the halt plus
    a 12 u deadband. The 150 u arm's constant stays pinned in
    section_constants as the LEGACY number.
    """
    import authsrv

    reach = authsrv.enemy_reach()
    stop = authsrv.follow_stop_radius()
    far = reach + 450.0
    FOLLOW = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    HALT = authsrv.GAME_SMSG_AGENT_STOP_MOVING
    POINT = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    TURN = authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION
    SPEED = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED

    LEDGER.ok(authsrv.NPC_FOLLOW is True,
              "retail's chase shape is the DEFAULT arm (ANIMREF-RE 40)",
              f"NPC_FOLLOW = {authsrv.NPC_FOLLOW!r} -- the revert is "
              "--legacy-npc-chase, and the operator's run scores the default")
    LEDGER.ok(abs(reach - 92.0) < 1e-9 and abs(stop - 80.0) < 1e-9,
              "a hostile swings from the halt disc + one radius (92 u) and "
              "halts at r + r + 56 = 80 u",
              f"reach {reach:.1f}, halt {stop:.1f} -- follow_stop_radius() + "
              "BOUNDING_RADIUS, NOT the 144 u press reach the first cut "
              "borrowed (sec.40.1); the 12 u margin is the re-chase deadband, "
              "the legacy arm stood and swung at 150")
    LEDGER.ok(reach > stop and reach - stop <= authsrv.BOUNDING_RADIUS + 1e-9,
              "and the engage reach is a SMALL deadband over the halt, not a "
              "wide stand-and-swing band",
              f"reach {reach:.1f} - halt {stop:.1f} = {reach - stop:.1f} u "
              "deadband; the 144 borrow made this 64 u, which is the band the "
              "capture caught the Hatcher swinging across (1-6 swings before a "
              "re-chase, halt at 80 to drift at 144)")

    # 1. IT STARTS: the rate (ours, kept), then ONE follow naming the player.
    #    No facing, no 0x0029, no swing. Retail sends nothing at all before the
    #    first follow (7/7); the speed is the one stated deviation.
    state = _world(dist=far)
    sent = _walk(state)
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(ops == [SPEED, FOLLOW],
              "a hostile out of reach announces a rate and then ONE follow -- "
              "no facing, no 0x0029",
              f"{[hex(o) for o in ops]} -- retail's 7 chases carry no 0x002E "
              "and no 0x0029 before or between their follows")
    rate = [v for op, v, _l in sent if op == SPEED][0]
    LEDGER.ok(rate[0] == 10 and 0.0 < rate[1] <= agents.AGENT_MAX_MOVE_SPEED,
              "and the rate is a FRACTION inside the client's own asserted bounds",
              f"{rate} -- units/s here is the named mistake; "
              f"{authsrv.ENEMY_MOVE_RATE} x {agents.DEFAULT_RUN_SPEED} = "
              f"{authsrv.ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED:.0f} u/s")
    fol = [v for op, v, _l in sent if op == FOLLOW][0]
    LEDGER.ok(fol[0] == 10 and tuple(fol[1]) == (0.0, 0.0)
              and fol[4] == authsrv.PLAYER_AGENT_ID,
              "the follow's point is the player's position and its fifth "
              "field NAMES the player",
              f"{fol} -- 45 of 45 retail NPC follows name the player in the "
              "fifth field, none carries 0; that field is agent+0x98, the "
              "agent the client's resolver stops against (sec.38.2)")
    LEDGER.ok(fol[2] == fol[3] == state["agents"][10]["plane"],
              "and on a SAME-PLANE order both words carry the mover's own "
              "plane -- which is what (0,0) on 205 of 206 retail NPC follows "
              "is: not a constant, but field 4 = the mover's current plane "
              "agreeing with field 3 because nothing is crossing "
              "(ANIMREF-RE 42.5; the crossing case is section_npc_plane)",
              f"{fol[2]}/{fol[3]} against agent plane "
              f"{state['agents'][10]['plane']}")
    LEDGER.ok(not _swings(state),
              "and it does not swing from out there",
              f"{far:.0f} units against a reach of {reach:.0f}")

    # 2. it actually closes the distance
    state = _world(dist=far)
    before = math.hypot(*state["agents"][10]["pos"])
    _walk(state, n=3, elapsed=0.5)
    after = math.hypot(*state["agents"][10]["pos"])
    LEDGER.ok(after < before - 100.0,
              "and over three half-seconds it closes real ground",
              f"{before:.0f} -> {after:.0f} units at "
              f"{authsrv.ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED:.0f} u/s")

    # 3. IT PARKS AT THE DISC, NOT ON THE PLAYER, and the halt is a bare 0x0028.
    #    A long step is the interesting case: uncapped, a 30 s step lands at 0.
    state = _world(dist=far)
    _walk(state)                       # tick one only announces the intent
    LEDGER.ok(math.hypot(*state["agents"][10]["pos"]) == far,
              "the tick that starts the walk does not also move the agent",
              "moved_at is stamped when the walk begins, so the first step is "
              "measured from then -- an agent cannot have travelled before it set off")
    parked = _walk(state, n=1, elapsed=30.0)
    d = math.hypot(*state["agents"][10]["pos"])
    LEDGER.ok(abs(d - stop) < 1e-3,
              "and a huge step parks it at the disc, 80 u out, not on top of "
              "the player",
              f"{d:.1f} against a halt radius of {stop:.0f} -- the legacy "
              "arm parked at 150, which is the ~70 u the operator saw")
    LEDGER.ok(not [op for op, _v, _l in parked if op == HALT]
              and state["agents"][10]["follow"] is not None
              and state["agents"][10]["follow"].get("arrived_at") is not None,
              "the copy has ARRIVED but the halt WAITS for retail's half-second "
              "clock (ANIMREF-RE 40.9)",
              f"{[hex(op) for op, _v, _l in parked]} -- retail's 0x0028 lands "
              "p50 0.496 s after the last follow (5/7); sent at the copy's "
              "arrival it froze the client's trailing rendered body short of "
              "the disc: CASE 8 v2's 'long range attacks' with the server's "
              "copy at exactly 80 u")
    state["agents"][10]["skills"] = ()       # the swing path, not the skill path
    LEDGER.ok(not _swings(state),
              "and it does not swing while it waits for the halt",
              "the follow is still armed; the swing opens on the tick after "
              "the 0x0028, never before the rendered body has stopped")
    state["agents"][10]["follow"]["sent_at"] -= 0.6      # the clock fires
    halted = _walk(state, elapsed=0.05)
    halts = [v for op, v, _l in halted if op == HALT]
    LEDGER.ok(halts == [[10]],
              "the arrival is ONE bare 0x0028 naming the agent -- retail's "
              "tick-cut halt",
              f"{halts} -- 5 of 7 retail chases end in exactly this, p50 "
              "0.496 s after the last follow; the other two end in a leash "
              "leg. One field, no point, no plane (agents.agent_stop_moving)")
    LEDGER.ok(not [op for op, _v, _l in halted if op in (POINT, FOLLOW, TURN)],
              "and no 0x0029, no re-path and no facing ride the halt",
              f"{[hex(op) for op, _v, _l in halted]}")
    LEDGER.ok(state["agents"][10].get("follow") is None
              and not state["agents"][10]["moving"],
              "the follow is forgotten at the halt",
              "a follow left armed here would refuse every swing below")
    LEDGER.ok(bool(_swings(state)),
              "and having halted, it can swing",
              "the walk is only worth anything if the fight starts at the end of it")

    # 4. standing in reach it sends NOTHING more -- no speed 0 (below the
    #    client's own floor, AgAgent.cpp:2366), no repeated halt.
    quiet = _walk(state, n=2)
    LEDGER.ok(not quiet,
              "a hostile standing in reach sends nothing more, tick after tick",
              f"{[hex(op) for op, _v, _l in quiet]} over two ticks standing still")

    # 5. THE RE-PATH CADENCE: never on a standing player; on a moving one, once
    #    the half-second has passed, to where they are NOW.
    state = _world(dist=far)
    _walk(state)                                   # the first follow
    quiet = _walk(state, n=4, elapsed=0.05)
    LEDGER.ok(not [op for op, _v, _l in quiet if op == FOLLOW],
              "a standing player is never re-pathed",
              f"{len(quiet)} message(s) over four ticks -- retail: 0 of 31 "
              "spontaneous re-paths on a standing target (sec.38.3)")
    state["pos"] = (0.0, 200.0)                    # the player moves
    soon = _walk(state, elapsed=0.05)
    LEDGER.ok(not [op for op, _v, _l in soon if op == FOLLOW],
              "a player who moved is NOT re-pathed inside the half-second",
              f"{[hex(op) for op, _v, _l in soon]} -- retail re-paths on a "
              "0.500 s clock (38 NPC intervals, p50 0.499), not per tick")
    state["agents"][10]["follow"]["sent_at"] -= 0.6
    later = _walk(state, elapsed=0.05)
    rp = [v for op, v, _l in later if op == FOLLOW]
    LEDGER.ok(len(rp) == 1 and tuple(rp[0][1]) == (0.0, 200.0)
              and rp[0][4] == authsrv.PLAYER_AGENT_ID,
              "but IS re-pathed once it has, to where the player is now, "
              "still naming them",
              f"{rp} -- the dest is the target's CURRENT position each time "
              "(bit-exact on retail's never-moved targets, sec.38.3)")
    LEDGER.ok(not [op for op, _v, _l in later if op == TURN],
              "and no facing message rides the chase",
              f"{[hex(op) for op, _v, _l in later]} -- the leg orients the "
              "body; the legacy arm faced the player every chasing tick")

    # 6. NO SWING MID-FOLLOW, and the 92 u engage reach, made concrete.
    state = _world(dist=85.0)                       # inside reach (92), standing
    state["agents"][10]["skills"] = ()
    LEDGER.ok(not _walk(state) and bool(_swings(state)),
              "inside reach (85 < 92) and standing, it swings at once and "
              "never walks",
              "a follow here would walk it toward the player for nothing")
    state = _world(dist=85.0)
    state["agents"][10]["skills"] = ()
    state["agents"][10]["follow"] = {"told": (0.0, 0.0),
                                     "sent_at": time.time(), "t0": time.time()}
    state["agents"][10]["moving"] = True
    LEDGER.ok(not _swings(state),
              "but a hostile MID-FOLLOW does not swing, even inside reach",
              "retail opens no attack_started between the follows of a chase "
              "(0 of 4 multi-follow chases); the swing comes after the halt")
    state = _world(dist=150.0)                     # where the legacy arm stood
    state["agents"][10]["skills"] = ()
    sent = _walk(state)
    LEDGER.ok(any(op == FOLLOW for op, _v, _l in sent) and not _swings(state),
              "from 150 u -- where the legacy arm stood and swung -- it walks "
              "in instead",
              f"{[hex(op) for op, _v, _l in sent]} -- 150 > 92, so this is a "
              "follow, and the follow refuses the swing")

    # 7. the refusals, and the halt that ends a chase for a reason other than
    #    arrival
    for why, world in (("past the leash", _world(dist=authsrv.AGGRO_RANGE + 50.0)),
                       ("dead", _world(dist=far, dead=True)),
                       ("passive", _world(dist=far, attacks_back=False)),
                       ("mid-burrow",
                        _world(dist=far, effects=agents.EFFECT_TRANSITION))):
        LEDGER.ok(not _walk(world),
                  f"a hostile that is {why} does not give chase",
                  "silence is the whole assertion")
    dead_player = _world(dist=far)
    dead_player["player_dead"] = True
    dead_player["player_health"] = 0.0
    LEDGER.ok(not _walk(dead_player),
              "and nothing chases a corpse",
              "the player is face-down; walking to them is the wrong picture "
              "and the swing that follows is worse")
    state = _world(dist=far)
    _walk(state)                                   # a follow in flight...
    state["player_dead"] = True
    state["player_health"] = 0.0
    ended = _walk(state)
    LEDGER.ok([op for op, _v, _l in ended] == [HALT]
              and state["agents"][10].get("follow") is None,
              "a follow in flight when the player dies halts with one bare "
              "0x0028 and is forgotten",
              f"{[hex(op) for op, _v, _l in ended]} -- the same message that "
              "ends an arrival; retail's non-arrival ends are a 0x0029 leash "
              "leg this server has no wander to send")

    # 8. A WALL, by arm. On the corridor integrator (the revert arm since
    #    NPCTRACK-Q1) pathmap.clip is sampled rather than solved and is the
    #    whole of that arm's collision story: the copy meets the wall and
    #    waits. On the default the copy is the client's own SYNC copy, which
    #    dead-reckons straight (agtrack_mirror.SyncAgent: pos = +0x78 + v*dt,
    #    no clamp, no mesh) -- the drawn body paths around, and the two agreed
    #    to <= 12 u at 38 of 40 measured halts (studies/npctrack F2/F4). So
    #    the default does not consult clip at all, and that is the decode,
    #    not an omission.
    authsrv.NPC_CLIENT_MODEL = False
    try:
        state = _world(dist=900.0)
        state["pathmap"] = _Wall()
        _walk(state)                       # announce, then walk
        _walk(state, n=4, elapsed=1.0)
        x = state["agents"][10]["pos"][0]
        LEDGER.ok(state["pathmap"].asked >= 1 and x >= 400.0,
                  "REVERT ARM: a hostile is stopped by the pathmap rather than "
                  "walking through it",
                  f"x={x:.0f} against a wall at 400, clip asked "
                  f"{state['pathmap'].asked} time(s)")
    finally:
        authsrv.NPC_CLIENT_MODEL = True
    state = _world(dist=900.0)
    state["pathmap"] = _Wall()
    _walk(state)
    _walk(state, n=4, elapsed=1.0)
    x = state["agents"][10]["pos"][0]
    LEDGER.ok(state["pathmap"].asked == 0 and x < 400.0,
              "DEFAULT (NPCTRACK-Q1): the client's sync copy dead-reckons "
              "straight through it and clip is never asked -- what the "
              "client computes, measured to 10 u on the stairs tapes",
              f"x={x:.0f}, clip asked {state['pathmap'].asked} time(s)")

    # 9. THE LEGACY ARM STILL RUNS, one flag away, so a run can convict either.
    authsrv.NPC_FOLLOW = False
    try:
        state = _world(dist=far)
        sent = _walk(state)
        ops = [op for op, _v, _l in sent]
        LEDGER.ok(ops == [SPEED, TURN, POINT],
                  "--legacy-npc-chase: a rate, a facing and a 0x0029 to the "
                  "player's point",
                  f"{[hex(o) for o in ops]} -- the 2026-08-11 shape, kept "
                  "verbatim as the revert arm")
        _walk(state, n=1, elapsed=30.0)
        d = math.hypot(*state["agents"][10]["pos"])
        LEDGER.ok(abs(d - authsrv.ENEMY_MELEE_RANGE) < 1.0,
                  "and it stops at the invented 150 u",
                  f"{d:.1f} against {authsrv.ENEMY_MELEE_RANGE:.0f}")
        LEDGER.ok(abs(authsrv.enemy_reach() - authsrv.ENEMY_MELEE_RANGE) < 1e-9,
                  "with the swing reach back at 150 too",
                  f"{authsrv.enemy_reach():.0f} -- the two numbers move together "
                  "on that arm, as they did before sec.40 split them")
    finally:
        authsrv.NPC_FOLLOW = True

    # 10. --halt-on-arrival: the 40.1 shape, one flag away
    authsrv.HALT_ON_CLOCK = False
    try:
        state = _world(dist=far)
        _walk(state)
        at_once = _walk(state, n=1, elapsed=30.0)
        LEDGER.ok([v for op, v, _l in at_once if op == HALT] == [[10]],
                  "--halt-on-arrival: the 0x0028 goes out the instant the copy "
                  "reaches the disc",
                  f"{[hex(op) for op, _v, _l in at_once]} -- the sec.40.1 "
                  "shape, kept as the revert arm; it halts the client's "
                  "rendered body short")
    finally:
        authsrv.HALT_ON_CLOCK = True


def section_owed_swing():
    """SLICE-F22: a halt whose arrival found the player in reach OWES a swing.

    The owner's run 20260912T203323: 105 halts, 4 swings -- the raider halted
    "112 u from the player", re-followed 20-40 u, halted "95 u", and never
    swung, because the swing tick re-tested the live distance after the halt
    clock and the runner had drifted past 92 u. Retail's swing follows its
    halt within 0.38 s (5 of 5) on a copy that lags the runner, and its
    hostiles open swings on a running player (3 of 45 starts; all land).
    """
    import authsrv
    import time as _t
    print("\n11b. SLICE-F22: the halt owes a swing")
    START = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
    FOLLOW = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    HALT = authsrv.GAME_SMSG_AGENT_STOP_MOVING
    pm = _Flat()
    stop = authsrv.follow_stop_radius()
    _FIGHTER = {"died_at": 0.0, "health": 100.0, "max_health": 100.0,
                "last_hit": 0.0, "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
                "effects": 0, "attacks_back": True, "skills": (),
                "skill_ready": [], "last_slot": -1}

    def parked_then_halted():
        """A follow from 900 u parks at the disc (80 u, in reach) and the
        halt fires on the clock; the player then RUNS 330 u away."""
        st = _fresh_follow((900.0, 0.0), (0.0, 0.0), player_plane=0)
        st["player_health"] = 100.0
        # the keys the ATTACK tick reads (the follow fixture carries only
        # the chase's): a hostile that attacks back, an empty bar
        st["agents"][10].update(_FIGHTER)
        _tick_parked(st, pm, now=0.0)
        st["agents"][10]["follow"]["sent_at"] = 29.9
        _tick_parked(st, pm, now=30.0)                   # parks at the disc
        fol = st["agents"][10]["follow"]
        assert fol is not None and fol.get("arrived_at") is not None
        fol["sent_at"] -= 0.6
        halted = _tick_parked(st, pm, now=30.05)         # the clock fires
        assert [op for op, _v, _l in halted] == [HALT]
        st["pos"] = (-250.0, 0.0)                        # 330 u from (80, 0)
        return st

    def swing_tick(st):
        sent = []
        authsrv.enemy_attack_tick(
            lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
            st, 1)
        return sent

    def starts(sent):
        return [v for op, v, _l in sent if op == START and v[0] == 4]

    st = parked_then_halted()
    ag = st["agents"][10]
    LEDGER.ok(ag.get("follow") is None and ag.get("swing_owed_at") == 30.05
              and abs(math.hypot(*ag["pos"]) - stop) < 0.5,
              "the halt STAMPS the debt with its own instant, because the "
              "arrival found the player inside enemy_reach() (the disc park, "
              "80 u); the follow is over",
              f"owed_at {ag.get('swing_owed_at')}, follow {ag.get('follow')}, "
              f"at {math.hypot(*ag['pos']):.1f} u")
    ag["swing_owed_at"] = _t.time()          # the tick clocks are real time
    sent = swing_tick(st)
    d = math.hypot(st["pos"][0] - ag["pos"][0], st["pos"][1] - ag["pos"][1])
    LEDGER.ok(starts(sent) == [[4, 10, 1, 0]] and ag.get("swing_owed_at") is None
              and ag.get("swing_lands_at") is not None,
              f"the swing OPENS on the next tick with the runner {d:.0f} u away "
              f"-- no re-test of the live distance -- and the debt is consumed "
              f"at the START; the landing is F21's (it lands wherever the "
              f"runner went)",
              f"starts {starts(sent)}, owed {ag.get('swing_owed_at')}")
    # the follow tick HOLDS while the debt stands, so the catch is not spent
    # on a 20 u leg that would block the swing (the mid-follow rule)
    st = parked_then_halted()
    ag = st["agents"][10]
    held = _tick_parked(st, pm, now=30.10)
    LEDGER.ok(held == [] and ag.get("follow") is None,
              "with a swing owed, the follow tick starts NO new chase at the "
              "runner 330 u out (a fresh follow would block the swing)",
              f"{[hex(op) for op, _v, _l in held]}, follow {ag.get('follow')}")
    followed = _tick_parked(st, pm, now=30.05 + authsrv.SWING_OWED_WINDOW + 0.05)
    LEDGER.ok([op for op, _v, _l in followed if op == FOLLOW] and
              ag.get("follow") is not None,
              "and once the window has passed unpaid, the chase resumes",
              f"{[hex(op) for op, _v, _l in followed]}")
    # SLICE-F27: THE ARRIVAL ITSELF OWES THE SWING, however far the runner is
    # by then -- the circling case (the owner: "I'm able to run around him in
    # circles and he never quite stops to attack", 34 halts, 6 swings). The
    # follow is sent at the player at (0, 0); the player is 300 u off by the
    # time the copy parks at the point it chased; retail's halt would have
    # been at ITS lagging copy's disc and the swing followed (5 of 6 halts).
    st = _fresh_follow((900.0, 0.0), (0.0, 0.0), player_plane=0)
    st["player_health"] = 100.0
    st["agents"][10].update(_FIGHTER)
    _tick_parked(st, pm, now=0.0)                    # the follow, at (0, 0)
    st["pos"] = (0.0, 300.0)                         # the runner circles off
    st["agents"][10]["follow"]["sent_at"] = 29.9
    _tick_parked(st, pm, now=30.0)                   # parks at the chased point
    fol = st["agents"][10]["follow"]
    LEDGER.ok(fol is not None and fol.get("arrived_at") is not None
              and fol.get("in_reach_at_arrival") is True,
              "a park at the point the hostile CHASED is an arrival in reach, "
              "even with the runner 300 u off by then -- retail's halt is at "
              "its lagging copy's disc, in reach by construction (SLICE-F27)",
              f"arrived {fol.get('arrived_at')}, flag {fol.get('in_reach_at_arrival')}")
    fol["sent_at"] -= 0.6
    _tick_parked(st, pm, now=30.05)                  # the clock fires: the halt
    ag = st["agents"][10]
    LEDGER.ok(ag.get("follow") is None and ag.get("swing_owed_at") == 30.05,
              "and the halt stamps the debt", f"owed {ag.get('swing_owed_at')}")
    ag["swing_owed_at"] = _t.time()
    sent = swing_tick(st)
    LEDGER.ok(starts(sent) == [[4, 10, 1, 0]],
              "so the circler is swung at on the tick after the halt -- one "
              "swing per catch, landing wherever they went (F21)",
              f"starts {starts(sent)}")
    # CONTROLS: an expired debt does not swing; a halt whose arrival flag was
    # CLEARED owes nothing -- the flag's own arm, kept for the day a stale-
    # point rule is measured (retail re-followed after 1 of 6 halts)
    st = parked_then_halted()
    ag = st["agents"][10]
    ag["swing_owed_at"] = _t.time() - authsrv.SWING_OWED_WINDOW - 0.1
    sent = swing_tick(st)
    LEDGER.ok(starts(sent) == [] and ag.get("swing_owed_at") is None
              and ag.get("swing_lands_at") is None,
              "an EXPIRED debt (older than the window) opens nothing and is "
              "cleared -- the live distance rules again",
              f"starts {starts(sent)}, owed {ag.get('swing_owed_at')}")
    st = _fresh_follow((900.0, 0.0), (0.0, 0.0), player_plane=0)
    st["player_health"] = 100.0
    _tick_parked(st, pm, now=0.0)
    st["agents"][10]["follow"]["sent_at"] = 29.9
    _tick_parked(st, pm, now=30.0)
    fol = st["agents"][10]["follow"]
    fol["in_reach_at_arrival"] = False            # the arrival found nobody
    fol["sent_at"] -= 0.6
    _tick_parked(st, pm, now=30.05)
    LEDGER.ok(st["agents"][10].get("follow") is None
              and st["agents"][10].get("swing_owed_at") is None,
              "a halt whose arrival flag is CLEARED owes nothing -- the flag "
              "is the one lever a measured stale-point rule would pull "
              "(retail re-followed after 1 of 6 halts, sec.40.2's mid-chase "
              "halt); since SLICE-F27 every arrival sets it",
              f"owed {st['agents'][10].get('swing_owed_at')}")
    # THE REVERT ARM
    saved = authsrv.SWING_OWED_AT_HALT
    authsrv.SWING_OWED_AT_HALT = False
    try:
        st = parked_then_halted()
        ag = st["agents"][10]
        LEDGER.ok(ag.get("swing_owed_at") is None,
                  "--no-owed-swing: the halt stamps no debt")
        ag["swing_owed_at"] = _t.time()
        sent = swing_tick(st)
        LEDGER.ok(starts(sent) == [] and ag.get("swing_lands_at") is None,
                  "and the swing tick re-tests the live distance: the runner "
                  "330 u out is not swung at -- the pre-F22 arm (105 halts, "
                  "4 swings)", f"starts {starts(sent)}")
    finally:
        authsrv.SWING_OWED_AT_HALT = saved


def section_npc_attack_skill():
    """SLICE-F24: an NPC's attack skill is a swing -- 50, a windup, 46 with
    weapon damage plus the bonus, one per interval.

    The owner's run 20260912T210558: Sever Artery and Power Attack fired ten
    log lines apart, each landing in the instant it was announced (the bar's
    0.0 activation), both announced as spells -- "a bunch of damage on his
    initial hits", the bleed looking like Power Attack's. Retail's 177 NPC
    attack-skill activations: [50] every time, [46] p50 0.564 s later, the
    next start p50 1.5 s after, two inside 1 s once.
    """
    import authsrv
    print("\n11c. SLICE-F24: an NPC's attack skill is a swing")
    INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
    INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
    DMG = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
    saved = (authsrv._is_attack_skill, authsrv.skill_damage, authsrv.skill_cost,
             authsrv.skill_condition, authsrv.NPC_ATTACK_SKILL_SWINGS)
    # stubbed, as test_castcycle stubs them: a bare machine has no skill rows
    authsrv._is_attack_skill = lambda sid: sid in (382, 322)
    authsrv.skill_damage = lambda sid, r: (30.0, "additive") if sid == 322 else None
    authsrv.skill_cost = lambda sid: (0, 0)
    authsrv.skill_condition = lambda sid, r: None
    try:
        def bar_world():
            st = _world(dist=85.0, skills=((382, 0.0, 6.0), (322, 0.0, 3.0)),
                        skill_ready=[0.0, 0.0], last_slot=-1)
            st["player_health"] = 100.0
            st["player_dead"] = False
            return st

        def anims(sent):
            return [v for op, v, _l in sent if op == INT_T and v[0] in (50, 60)]

        def closes(sent):
            return [v for op, v, _l in sent if op == INT and v[0] in (46, 58, 1)]

        st = bar_world()
        ag = st["agents"][10]
        interval = ag["attack_speed"]
        t0 = time.time()
        sent = _swings(st)
        LEDGER.ok(anims(sent) == [[50, 10, 1, 382]]
                  and ag.get("cast_lands_at") is not None
                  and abs((ag["cast_lands_at"] - t0)
                          - authsrv.swing_windup(interval)) < 0.1,
                  "the first ready attack skill is announced as the ATTACK "
                  "family's [50, npc, player, skill] and lands a WINDUP away "
                  "(retail [50] -> [46] p50 0.564 s), not on the next tick",
                  f"anims {anims(sent)}, lands in "
                  f"{ag.get('cast_lands_at', 0) - t0:.3f} s vs windup "
                  f"{authsrv.swing_windup(interval):.3f}")
        # the landing: 46 then weapon damage (+0 for a skill with no bonus)
        ag["cast_lands_at"] = time.time() - 0.01
        before = st["player_health"]
        sent = _swings(st)
        LEDGER.ok(closes(sent) == [[46, 10, 0]]
                  and any(op == DMG for op, _v, _l in sent)
                  and st["player_health"] < before,
                  "it strikes: [46, npc, 0] then the weapon's damage on the "
                  "same channel a swing uses -- not a spell's [58]",
                  f"closes {closes(sent)}, health {before} -> "
                  f"{st['player_health']}")
        # the second ready attack skill WAITS for the swing clock
        sent = _swings(st, n=3)
        LEDGER.ok(anims(sent) == [] and closes(sent) == [],
                  "Power Attack, ready too, does NOT fire on the next ticks: "
                  "an attack skill waits for the swing interval like the "
                  "plain swing (retail: two [50]s by one NPC inside 1 s, "
                  "once in 177) -- the owner's burst was both in one instant",
                  f"anims {anims(sent)}, closes {closes(sent)}")
        ag["last_swing"] -= interval + 0.1
        sent = _swings(st)
        LEDGER.ok(anims(sent) == [[50, 10, 1, 322]],
                  "and once the interval has passed it is the next swing",
                  f"anims {anims(sent)}")
        ag["cast_lands_at"] = time.time() - 0.01
        before = st["player_health"]
        sent = _swings(st)
        lost = before - st["player_health"]
        LEDGER.ok(closes(sent) == [[46, 10, 0]] and lost > 25.0,
                  "Power Attack's strike is the weapon hit PLUS its +30 bonus "
                  "(added after armour, hit_enemy's order for the player's)",
                  f"lost {lost:.1f} (weapon ~3 + 30)")
        # SLICE-F25: A CAST IN FLIGHT LANDS WHEREVER THE TARGET WENT -- the
        # owner's "shows up on his skill monitor but doesn't actually hit
        # me ... could be when I'm moving": F21 hoisted the swing above the
        # reach gate and left the cast below it. Retail: 37 hit / 3 stopped
        # attack-skill strikes on a moving target, 9 of 9 spells complete.
        st = bar_world()
        ag = st["agents"][10]
        _swings(st)                                    # announces 382
        assert ag.get("cast_lands_at") is not None
        st["pos"] = (600.0, 0.0)                       # the runner left reach
        ag["cast_lands_at"] = time.time() - 0.01
        before = st["player_health"]
        sent = _swings(st)
        LEDGER.ok(closes(sent) == [[46, 10, 0]] and st["player_health"] < before
                  and ag.get("cast_lands_at") is None,
                  "an attack skill announced in reach LANDS after the player "
                  "ran 500 u past it -- [46] and the hit, the cast resolved "
                  "before the reach gate like the swing (SLICE-F25)",
                  f"closes {closes(sent)}, health {before} -> "
                  f"{st['player_health']}")
        saved_lh = authsrv.LATE_HIT
        authsrv.LATE_HIT = False
        try:
            st = bar_world()
            ag = st["agents"][10]
            _swings(st)
            st["pos"] = (600.0, 0.0)
            ag["cast_lands_at"] = time.time() - 0.01
            before = st["player_health"]
            sent = _swings(st)
            LEDGER.ok(closes(sent) == [] and st["player_health"] == before
                      and ag.get("cast_lands_at") is None,
                      "--no-late-hit: the gate drops the cast in flight -- the "
                      "'announced but never hit me' of the owner's run",
                      f"closes {closes(sent)}, health {st['player_health']}")
        finally:
            authsrv.LATE_HIT = saved_lh
        # THE REVERT ARM: instant, back to back, spell-shaped
        authsrv.NPC_ATTACK_SKILL_SWINGS = False
        st = bar_world()
        ag = st["agents"][10]
        sent = _swings(st)
        ag["cast_lands_at"] = time.time() - 0.01
        sent += _swings(st, n=2)
        LEDGER.ok([v[0] for v in anims(sent)] == [60, 60]
                  and closes(sent) and closes(sent)[0] == [58, 10, 0],
                  "--npc-skill-instant: both announce as spells, the first "
                  "closes as one, the second follows on the next tick -- the "
                  "pre-F24 burst", f"anims {anims(sent)}, closes {closes(sent)}")
    finally:
        (authsrv._is_attack_skill, authsrv.skill_damage, authsrv.skill_cost,
         authsrv.skill_condition, authsrv.NPC_ATTACK_SKILL_SWINGS) = saved


def section_facing():
    """It turns to look at you, on an angle nobody in this repo invented.

    `GAME_SMSG_AGENT_UPDATE_ROTATION` (0x002E) sat defined and documented in
    authsrv.py for days without ever being sent. Everything about how to fill it
    was already measured off ArenaNet's own traffic, which is why this rung needed
    no new discovery:

      * atan2(y, x) -- test_rotate.py scores the client's OWN 0x0040 sends against
        atan2 of a nearby 0x003D direction vector, beating a null model built from
        the same corpus. Its first version paired against the POSITION vec2 and
        scored 0 of 163, because a position has a plausible atan2 too.
      * absolute, in [-pi, pi], with +/-inf as the client's free-spin sentinels.
      * a turn rate that is per-CREATURE and quantised; 2*pi/3 is ArenaNet's
        largest, to the bit.

    Both payload fields are marshalled `dword` and hold float32 -- the same trap
    that made an early test_smsgnames compare garbage against pi and pass a
    turn-rate check vacuously. Every check here reinterprets before asserting, and
    the last one fails if the code stops doing so.

    DRIVEN DIRECTLY SINCE ANIMREF-RE 40. Until then every check here reached
    face_player through the chase (`_walk`), which faced the player on every
    chasing tick. Retail's chase carries no 0x002E at all (7 of 7 live chases,
    before or between follows -- the leg orients the body), so the default
    chase no longer calls face_player and the one remaining call site is the
    swing open, which section_swing_back pins as TURN then ATTACK_STARTED.
    The first two checks below pin that split; the rest call face_player as
    the swing does, so the angle law, the epsilon and the seam wrap are still
    checked on the code that runs -- not on the revert arm's.
    """
    import authsrv

    # INDEX FROM THE SENT PAYLOAD, NOT FROM A DECODED ONE. test_smsgnames reads
    # 0x002E's angle at values[2] because a DECODED list carries the raw header at
    # index 0; what `send` is handed has no header, so the same field is at index
    # 1. Getting this wrong is silent in the usual way -- the first version of
    # this section read index 2 and got 2.0944, the TURN RATE, which is a
    # perfectly plausible angle (120 degrees) and would have been asserted as one.
    def angle_of(vals):
        return struct.unpack("<f", struct.pack("<I", vals[1]))[0]

    def rate_of(vals):
        return struct.unpack("<f", struct.pack("<I", vals[2]))[0]

    def rots(sent):
        return [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION]

    def face(state, force=False):
        """One face_player call, as the swing open makes it."""
        sent = []
        authsrv.face_player(
            lambda op, v, label="", quiet=False: sent.append((op, v, label)),
            state, 10, state["agents"][10], 1, force=force)
        return rots(sent)

    # 0. THE CALL SITE. The chase carries no facing; the swing open does.
    LEDGER.ok(not rots(_walk(_world(dist=600.0))),
              "a hostile setting off on a follow announces NO facing "
              "(ANIMREF-RE 40)",
              "retail's 7 live chases carry no 0x002E before or between their "
              "follows; the leg orients the body")
    in_reach = _world(dist=85.0)                  # inside enemy_reach() = 92
    in_reach["agents"][10]["skills"] = ()
    opened = _swings(in_reach)
    LEDGER.ok(opened and opened[0][0] == authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION
              and opened[0][1][0] == 10,
              "and the swing open is where the facing goes out, first",
              f"{[hex(op) for op, _v, _l in opened]} -- the one call site left, "
              "so every check below drives face_player as it does")

    # the fixture puts the agent due EAST of the player, so it must look WEST
    state = _world(dist=600.0)
    r = face(state)
    LEDGER.ok(len(r) == 1 and r[0][0] == 10,
              "asked to face the player, the agent announces one facing for itself",
              f"{len(r)} rotation(s)")
    LEDGER.ok(abs(angle_of(r[0])) < 1e-5,
              "the emitted angle is the bearing to the player PLUS pi",
              f"{angle_of(r[0]):.5f} rad = {math.degrees(angle_of(r[0])):.0f} deg. "
              "The agent is due EAST of the player, so the bearing TO the player "
              "is +/-pi and the emitted value is 0. THE PLUS PI IS MEASURED, not "
              "derived: atan2(dy, dx) is correct by every derivation available "
              "(test_rotate scores the client's own 0x0040 sends against exactly "
              "that) and sending it turned the agent to face AWAY, observed by the "
              "owner watching the screen. Which is the only instrument that sees "
              "it -- the wire cannot tell a facing from its opposite")
    # THE BOUND HAS TO BE FLOAT32's pi, NOT float64's. Due west is exactly +pi,
    # and float32(pi) = 3.14159274 is GREATER than math.pi = 3.14159265 by 9e-8 --
    # so the obvious `-math.pi <= a <= math.pi` marks a legitimate facing
    # out-of-range. test_smsgnames' version of this check is over LIVE samples,
    # none of which land exactly on the seam, so it never had to notice.
    f32_pi = struct.unpack("<f", struct.pack("<f", math.pi))[0]
    LEDGER.ok(-f32_pi <= angle_of(r[0]) <= f32_pi,
              "and it is inside the range every live sample sits in",
              f"{angle_of(r[0]):.8f} against float32 pi {f32_pi:.8f} (float64 pi "
              f"is {math.pi:.8f}, which due west overshoots by 9e-8)")
    LEDGER.ok(abs(rate_of(r[0]) - 2.0 * math.pi / 3.0) < 1e-6,
              "and the turn rate is ArenaNet's own quantised maximum, 2*pi/3",
              f"{rate_of(r[0]):.7f} -- a per-creature constant, not a per-message "
              "value")

    # a quarter turn: player due NORTH of the agent must give +pi/2
    north = _world(dist=600.0)
    north["agents"][10]["pos"] = (0.0, -600.0)
    r = face(north)
    LEDGER.ok(abs(angle_of(r[0]) + math.pi / 2.0) < 1e-5,
              "a player due north of the agent emits -pi/2, not +pi/2 or 0",
              f"{angle_of(r[0]):.5f} -- bearing +pi/2, emitted -pi/2. This is the "
              "check that separates atan2(y, x) from atan2(x, y), which the "
              "due-east case above cannot: swapping the arguments emits +pi here")

    # 2. it is NOT re-announced when nothing has changed
    quiet = [x for _ in range(5) for x in face(state)]
    LEDGER.ok(not quiet,
              "a facing that has not changed is not re-announced",
              f"{len(quiet)} over five ticks -- ungated this is 20 rotation "
              "messages a second at an agent already looking the right way")

    # 3. THE WRAP. An agent looking near due west is the case where a naive
    #    difference reads 6.2 radians instead of 0.08 and re-announces forever.
    # SOUTH, not north. The agent is looking at +pi and the seam is crossed only
    # when the angle goes NEGATIVE -- a hair north gives +3.139, which an unwrapped
    # difference reads as 0.003 and stays quiet about anyway. This check passed
    # against a sabotaged (unwrapped) server until that was noticed: it was
    # asserting silence in a case where both versions are silent.
    state["pos"] = (0.0, -1.0)                    # a hair SOUTH: angle flips to -pi
    wrapped = [x for _ in range(3) for x in face(state)]
    LEDGER.ok(not wrapped,
              "and a facing that crosses the +/-pi seam is still 'unchanged'",
              f"{len(wrapped)} -- the shortest way round from +3.1416 to -3.1383 "
              "is 0.003 rad, not 6.28. Unwrapped, this agent re-announces on every "
              "tick forever, and this check goes red when the wrap is removed")

    # 4. a real turn IS announced
    state["pos"] = (0.0, 900.0)
    turned = face(state)
    LEDGER.ok(len(turned) == 1,
              "but a player who has actually moved round does get a new facing",
              f"{len(turned)}")

    # 5. standing exactly on the player has no direction, and atan2(0, 0) is 0.0
    #    rather than an error -- so an ungurded version silently means "face east"
    # force=True, so the epsilon gate cannot be what produces the silence (this
    # was the one directly-driven check before sec.40, because the chase never
    # reached facing inside melee range and the check passed without executing
    # the code it names).
    on_top = _world(dist=600.0)
    on_top["agents"][10]["pos"] = (0.0, 0.0)
    direct = []
    authsrv.face_player(
        lambda op, v, label="", quiet=False: direct.append((op, v, label)),
        on_top, 10, on_top["agents"][10], 1, force=True)
    LEDGER.ok(not direct,
              "and an agent standing exactly on the player announces no facing",
              "atan2(0, 0) returns 0.0 rather than raising, so the unguarded "
              "version silently turns to face due east. force=True here, so the "
              "epsilon cannot be what produces the silence")

    # 6. the fields are FLOAT BITS in dword slots. Read raw, the angle check
    #    above compares garbage to pi -- the exact failure test_smsgnames records.
    # a NORTH fixture, not the due-east one: due east emits exactly 0.0, whose
    # float bits are 0x00000000, and a bit-pattern check against zero proves
    # nothing about marshalling either way.
    bits_world = _world(dist=600.0)
    bits_world["agents"][10]["pos"] = (0.0, -600.0)
    raw = face(bits_world)[0]
    LEDGER.ok(raw[1] > (1 << 30) and raw[2] > (1 << 29),
              "and both fields go out as float BITS, not as small integers",
              f"angle=0x{raw[1]:08X}, rate=0x{raw[2]:08X} -- a dword field holding "
              "an IEEE float is the ROTATE_PLAYER trap, and a codec change that "
              "started marshalling these as real numbers would show up here")


def section_enemy_skill():
    """It fights back with a SKILL, announced the way ArenaNet announces one.

    THE CORPUS REFUSED THE OBVIOUS ANSWER, which is why this section exists. Our
    server already had a skill message -- GAME_SMSG 0x00E3, which it sends when
    the PLAYER casts -- and reusing it for an NPC would have been the natural
    move. All 6 of the 0x00E3 in the entire live corpus name the player, because
    0x00E3 confirms a cast the CLIENT initiated; the client even logs "Pending
    skill %u copy %d not found" when the echo is wrong, and an NPC's cast has
    nothing to confirm.

    What the corpus does carry is one NPC skill activation, on the int channel:
    0x009F [value 60 = GV_SKILL_ACTIVATED, agent 36, skill 83]. n=1. That is thin
    and it is stated as thin, but it is evidence and the alternative was invention.

    The skill, its activation and its recharge are ArenaNet's, out of the client's
    own table via skilltable.py: 276 matches the profession this server already
    declares for the Hatcher. Only the damage fraction is ours.
    """
    import authsrv

    def cast_msgs(sent):
        # Both channels: since ANIMREF-R1 sec.2 the form follows the target,
        # and this bar is single-target-always at the player (land_skill), so
        # these ride 0x00A0 [60, agent, PLAYER, skill]. The skill id is the
        # LAST value on either channel.
        return [(op, v) for op, v, _l in sent
                if op in (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET)
                and v and v[0] == agents.GV_SKILL_ACTIVATED]

    def dmg_floats(sent, props=(agents.PROP_DAMAGE, agents.GV_CRITICAL)):
        # DAMAGE only. Until SKILLS-HN (2026-09-09) this read every 0x00A3
        # float, which was fine while an overheal sent nothing; now the
        # enemy's Restore Condition on its own full pool sends a positive 55
        # (retail does, healjoin.py P4), and a heal is not damage.
        return [struct.unpack("<f", struct.pack("<I", v[-1]))[0]
                for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
                and v[0] in props]

    # 1. the opening cast. SKILLS-RC (2026-09-10): slot 1 is Restore
    #    Condition, a target-OTHER-ally spell by the client's own byte, so a
    #    LONE hostile can no longer cast it (test_mechanics 26 pins that); the
    #    bar's cycle is exercised here with an idle ally standing by, and the
    #    opening cast names THAT ally rather than the player.
    state = _world_ally()
    sent = _swings(state)
    casts = cast_msgs(sent)
    LEDGER.ok(len(casts) == 1 and casts[0][1][1] == 10
              and casts[0][1][2] == 11
              and casts[0][1][-1] == authsrv.ENEMY_SKILL_BAR[0][0],
              "a hostile opens with its SKILL, named on the TARGETED channel "
              "at its ALLY (the form follows the target, ANIMREF-R1 sec.2; "
              "276 is target-other-ally, SKILLS-RC)",
              f"{casts} -- [GV_SKILL_ACTIVATED, agent, target, skill]")
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(authsrv.GAME_SMSG_SKILL_ACTIVATED not in ops,
              "and NOT on 0x00E3, which is the player's own cast confirmation",
              f"{[hex(o) for o in ops]} -- all 6 0x00E3 in the live corpus name "
              "the player. Reusing it here is the mistake this section exists to "
              "prevent, and it is the one a reader of authsrv.py would make")
    LEDGER.ok(not dmg_floats(sent),
              "and the cast deals no damage until it lands",
              f"activation is {authsrv.ENEMY_SKILL_BAR[0][1]}s -- damage here is "
              "the instant-cast bug, the same shape the swing had")

    # 2. nothing else happens during the activation window
    LEDGER.ok(not _swings(state, n=4),
              "nothing swings while a cast is in flight",
              "a cast in flight beats everything; otherwise a slow tick lets an "
              "agent cast and swing on the same tick")

    # 3. it lands -- and slot 0 is a HEAL, so it lands nothing.
    #
    # REWRITTEN 2026-08-15 (studies/combat step 8). This used to assert that a
    # landing cast deals ENEMY_SKILL_FRACTION, a flat quarter of the player's
    # maximum for every skill on the bar. That constant is gone: the damage is
    # now the skill's own scale endpoints interpolated at ENEMY_SKILL_RANK by
    # the client's formula, and MOST OF THIS BAR IS NOT DAMAGE. Slot 0 is 276
    # Restore Condition, whose 10->70 is HEALING (GWW's own progression var
    # name), so the honest answer is that it lands no damage at all.
    state["agents"][10]["cast_lands_at"] = time.time() - 0.001
    land = _swings(state)
    fl = dmg_floats(land)
    # THESE TWO SKIP AS A PAIR, and the pairing is the point. "Slot 0 lands no
    # damage" is only evidence that 276 is a HEAL if some other skill on the
    # same bar does land damage -- which is what the 312 check below is for, and
    # what its own comment calls proving the path is not simply dead. On a
    # machine with no vault overlay NOTHING has a `skills` row, so `not fl` is
    # true because the damage path is inert, and the first check would pass for
    # exactly the reason its control exists to rule out. Splitting them would
    # trade a red control for a green vacuity, which is the worse direction:
    # the control failing is visible, a heal-check passing on an empty table is
    # not. (Found 2026-08-31, when the bare-machine path first ran this far.)
    holy = authsrv.skill_damage(312, authsrv.ENEMY_SKILL_RANK)
    if holy is None:
        LEDGER.skip("3. slot 0 lands no damage, and 312 on the same bar does",
                    "no 'skills' rows -- the vault overlay is absent, so the "
                    "damage path is inert for EVERY skill and the heal check "
                    "would pass without its control (run skilltable.py "
                    "--emit-content)")
    else:
        LEDGER.ok(not fl,
                  "slot 0 lands NO damage -- its scale is Healing, not damage",
                  f"{fl} -- 276 Restore Condition heals 10-70 (GWW). The old flat "
                  f"fraction made a heal hurt the player; dealing its magnitude AS "
                  f"damage would have been worse, not better")
        heals = dmg_floats(land, props=(agents.GV_HEALTH_GAIN,))
        LEDGER.ok(not heals,
                  "and it sends NO 55 either: the ally carries no condition, "
                  "and Restore Condition heals per condition REMOVED "
                  "(SKILLS-RC; the pre-2026-09-10 flat self-overheal is gone)",
                  f"{heals} -- test_mechanics 24 drives the cured case")
        # The damage skill on the same bar, to prove the path is not simply dead.
        LEDGER.ok(holy[1] == "standalone" and holy[0] == 46,
                  "while 312 Holy Strike on the same bar DOES damage, at 46",
                  f"{holy} -- scale 10->55 at rank {authsrv.ENEMY_SKILL_RANK} by the "
                  f"client's own interpolator; GWW calls the var `Holy damage`")
    land_ints = [v for op, v, _l in land
                 if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
    LEDGER.ok(not any(v[0] == agents.GV_MELEE_ATTACK_FINISHED
                      for v in land_ints),
              "and a landing cast sends no MELEE_ATTACK_FINISHED",
              f"{land_ints} -- that value names the end of a SWING, and 40 "
              "of the 42 in the live corpus are followed by a property-16 "
              "damage from the same agent. A cast is not a swing")
    LEDGER.ok(land_ints and land_ints[0] == [agents.GV_SKILL_FINISHED, 10, 0],
              "what it DOES send is the finish: [58, agent, 0] opening the "
              "landing batch (ANIMREF-R2: 709/709 retail other-agent casts "
              "close with a 58-led batch; ours closed with NOTHING)",
              f"{land_ints}")

    # 4. THE NEXT CAST IS A DIFFERENT SKILL, not slot 1 again. This is where the
    #    bar stops being decorative: with one skill the agent would fall back to
    #    swinging here, and the two checks that used to sit in this spot asserted
    #    exactly that. They were correct for a single skill and wrong for a bar.
    state["agents"][10]["last_swing"] = time.time() - 100.0
    after = _swings(state, n=1)
    second = cast_msgs(after)
    LEDGER.ok(len(second) == 1
              and second[0][1][-1] == authsrv.ENEMY_SKILL_BAR[1][0],
              "with slot 1 recharging it casts slot 2, not slot 1 again",
              f"{second} -- expected skill {authsrv.ENEMY_SKILL_BAR[1][0]}. "
              "Repeating the first skill is what a bar-shaped constant looks like "
              "when the selector is not really reading the bar")

    # 4b. AN EMPTY BAR MEANS PLAIN SWINGS (--no-enemy-skills, ANIMREF-R5).
    #     content/world.toml's `skills` row could always express this ("an
    #     EMPTY list leaves the agent on plain swings" -- ENEMY_SKILLS' own
    #     comment); the FLAG could not, because `--enemy-skills ''` is falsy
    #     and was silently ignored, leaving the default bar up while the
    #     command line said otherwise. The pair below is the point: the same
    #     world that casts with a bar must swing without one, so this cannot
    #     pass by the agent simply doing nothing.
    bare = _world(skills=(), skill_ready=[])
    bare["agents"][10]["last_swing"] = time.time() - 100.0
    bare_sent = _swings(bare, n=1)
    LEDGER.ok(not cast_msgs(bare_sent),
              "an empty enemy bar casts NOTHING",
              f"{cast_msgs(bare_sent)} -- the --no-enemy-skills arm, which "
              "R5 needs so the hostile's swing channel can be watched with "
              "its cast channel silent")
    started = [v for op, v, _l in bare_sent
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
               and v and v[0] == agents.GV_ATTACK_STARTED]
    LEDGER.ok(len(started) == 1,
              "and it SWINGS instead -- the control that stops this being a "
              "test of an agent that does nothing at all",
              f"{started}")

    # and only when the WHOLE bar is down does it swing
    busy = _world_ally()
    busy["agents"][10]["skill_ready"] = [time.time() + 999.0] * len(
        busy["agents"][10]["skills"])
    busy["agents"][10]["last_swing"] = time.time() - 100.0
    dry = _swings(busy, n=1)
    LEDGER.ok(not cast_msgs(dry)
              and any(op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                      for op, _v, _l in dry),
              "and with the whole bar recharging it goes back to swinging",
              "an agent with nothing ready that also stops swinging reads as a "
              "broken one")

    # 5. skill 0 turns it off, and the agent is on plain swings
    plain = _world_ally()
    plain["agents"][10]["skills"] = ()
    p_sent = _swings(plain)
    LEDGER.ok(not cast_msgs(p_sent),
              "an empty bar leaves the agent on plain swings",
              "the content switch, so a probe can put a non-casting body in the "
              "world without editing code")
    LEDGER.ok(any(op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                  for op, _v, _l in p_sent),
              "and it still swings",
              "turning the skill off must not turn the agent off")

    # 6. a cast in flight does not survive its caster's DEATH, the same as a
    #    swing -- but since SLICE-F25 it survives the pair leaving range: a
    #    cast is announced in reach and lands where its windup ends (retail:
    #    attack-skill strikes on a moving target 37 hit / 3 stopped, spell
    #    casts at a moving observer complete 9 of 9). "leaves range" was
    #    pinned beside "dies" as retail's rule until 2026-09-12; it was ours.
    mid = _world_ally()
    _swings(mid)
    assert mid["agents"][10]["cast_lands_at"] is not None
    mid["agents"][10].update(dead=True)
    mid["agents"][10]["cast_lands_at"] = time.time() - 1.0
    before = mid["player_health"]
    LEDGER.ok(not _swings(mid, n=3) and mid["player_health"] == before,
              "a cast in flight does not land if the caster dies",
              "an overdue cast plus three ticks and no damage")
    mid = _world_ally()
    _swings(mid)
    assert mid["agents"][10]["cast_lands_at"] is not None
    mid["agents"][10].update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0))
    mid["agents"][10]["cast_lands_at"] = time.time() - 1.0
    ally_before = mid["agents"][11]["health"]
    landed = _swings(mid, n=1)
    fin = [v for op, v, _l in landed
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
           and v == [agents.GV_SKILL_FINISHED, 10, 0]]
    LEDGER.ok(len(fin) == 1 and mid["agents"][10].get("cast_lands_at") is None,
              "a cast in flight LANDS when the pair is out of range at the "
              "landing -- the bar's Restore Condition finishes ([58]) rather "
              "than being dropped -- SLICE-F25 (the owner's 'shows up on his "
              "skill monitor but doesn't actually hit me'); its heal is zero "
              "here by the skill's own rule, the ally carries no condition",
              f"finished {fin}, ally {ally_before} -> "
              f"{mid['agents'][11]['health']}")

    # 7. the skill can kill, and the kill is still the effects bit.
    #     Driven by the bar's DAMAGE skill (312 Holy Strike) rather than by
    #     slot 0, which since step 8 is correctly inert: a heal lands nothing,
    #     so repeating it forever could never reach a death and the check
    #     would have been measuring an empty loop.
    #
    #     AND IT NEEDS THE VAULT, which nothing said until 2026-08-31: the
    #     magnitude comes from `skills` (vault-only, skilltable.py), while the
    #     `skill_effect` row naming 312 as damage is REPO content -- so a bare
    #     machine got a None out of `skill_damage` and this block died on
    #     `[0]`, a traceback rather than a verdict. Parts 7b on are pure
    #     `pick_skill` and run anywhere, so the skip is scoped to THIS block
    #     rather than to the section.
    if authsrv.skill_damage(312, authsrv.ENEMY_SKILL_RANK) is None:
        LEDGER.skip("7. the skill can kill, and the kill is the effects bit",
                    "no 'skills' row for 312, so its damage magnitude is "
                    "unknown on this machine -- the vault overlay is absent "
                    "(run skilltable.py --emit-content). The rest of this "
                    "section does not need it and runs below.")
        return _section_enemy_skill_bar_order()
    kill_state = _world_ally()
    sent = []
    keep = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    holy_slot = next(i for i, s in enumerate(authsrv.ENEMY_SKILLS)
                     if s[0] == 312)
    per_hit = authsrv.skill_damage(312, authsrv.ENEMY_SKILL_RANK)[0]
    needed = int(math.ceil(float(agents.PLAYER_HEALTH) / per_hit))
    for _ in range(needed):
        kill_state["agents"][10]["casting"] = holy_slot
        authsrv.land_skill(keep, kill_state, 10, kill_state["agents"][10], 1)
    LEDGER.ok(kill_state["player_dead"],
              f"{needed} Holy Strikes at {per_hit} kill the player",
              f"health {kill_state['player_health']} -- "
              f"{needed} x {per_hit} against {agents.PLAYER_HEALTH}")
    kills = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
             and v == [authsrv.PLAYER_AGENT_ID, agents.EFFECT_DEAD]]
    LEDGER.ok(len(kills) == 1,
              "and the death is still ONE effects-bit message",
              f"{len(kills)} -- property 16 floors at 1 and cannot kill however "
              "it is dressed up")

    return _section_enemy_skill_bar_order()


def _section_enemy_skill_bar_order():
    """Parts 7b on of `section_enemy_skill`: the bar selector and the
    spawn wiring. Split out 2026-08-31 so part 7's vault dependency (312's
    damage magnitude, a `skills` row) can SKIP without taking these with
    it -- nothing below reads a magnitude, so all of it runs on a bare
    machine. Called from both of that section's exits.
    """
    import authsrv
    import agents
    # 7b. THE BAR IS A BAR: it works down the slots rather than repeating slot 1.
    #     Every recharge is rolled back except the one under test, so what is
    #     being measured is the ORDER and not the clock.
    bar = _world_ally()
    a = bar["agents"][10]
    picked = []
    for _ in range(len(a["skills"])):
        slot = authsrv.pick_skill(a, time.time())
        if slot is None:
            break
        picked.append(slot)
        a["skill_ready"][slot] = time.time() + 999.0      # "just cast it"
    LEDGER.ok(picked == list(range(len(a["skills"]))),
              "the bar is worked in order, one slot at a time",
              f"{picked} of {len(a['skills'])} slots -- a selector that always "
              "returned the first ready slot without the recharge moving would "
              "give [0, 0, 0, 0], and one that scanned backwards would reverse it")
    LEDGER.ok(authsrv.pick_skill(a, time.time()) is None,
              "and when every slot is recharging, nothing is picked",
              "None rather than slot 0 -- the agent falls through to swinging")

    # 7b-ii. ROUND ROBIN, and this is the check that separates it from the
    #        first-ready-in-order version it replaced. With EVERY slot ready, a
    #        first-ready selector returns slot 0 forever; round robin advances.
    rr = _world_ally()
    r = rr["agents"][10]
    n = len(r["skills"])
    r["skill_ready"] = [0.0] * n
    order = []
    for _ in range(n + 1):
        slot = authsrv.pick_skill(r, time.time())
        order.append(slot)
        r["last_slot"] = slot            # what the cast site does
    LEDGER.ok(order == list(range(n)) + [0],
              "with every slot ready the cursor advances and wraps",
              f"{order} -- first-ready-in-order gives {[0] * (n + 1)} here, and "
              "that is the version this replaced")

    # and the WRAP specifically: the only ready slot sits BEHIND the cursor. The
    # modulo on `start` alone does not cover this -- every check above is
    # satisfied by a selector that sweeps from the cursor to the end of the bar
    # and gives up, which would strand a ready slot 1 whenever the cursor is
    # past it and everything after is recharging.
    wr = _world_ally()
    w = wr["agents"][10]
    later = time.time() + 999.0
    w["skill_ready"] = [0.0] + [later] * (len(w["skills"]) - 1)
    w["last_slot"] = len(w["skills"]) - 2      # cursor points at the last slot
    LEDGER.ok(authsrv.pick_skill(w, time.time()) == 0,
              "and the scan wraps to reach a ready slot behind the cursor",
              "cursor at the end of the bar, only slot 1 ready -- a sweep that "
              "stops at the end returns None here and the agent swings instead "
              "of casting a skill that is up")

    # 7b-iii. THE DEFECT ITSELF, as a regression. 11.5 measured a live run where
    #         slot 4 NEVER fired: recharges of 2, 5, 8, 2 mean a priority list
    #         never walks past slot 3, because slot 1 is back every 2.0 s. Drive
    #         the real bar against a clock and require every slot to get a turn.
    sim = _world_ally()
    sm = sim["agents"][10]
    sm["skill_ready"] = [0.0] * len(sm["skills"])
    clock, fired = 0.0, set()
    for _ in range(400):
        slot = authsrv.pick_skill(sm, clock)
        if slot is not None:
            fired.add(slot)
            sm["skill_ready"][slot] = clock + sm["skills"][slot][2]
            sm["last_slot"] = slot
            clock += sm["skills"][slot][1]     # the activation
        clock += 0.05
    LEDGER.ok(fired == set(range(len(sm["skills"]))),
              "and over a simulated fight EVERY slot on the bar gets used",
              f"fired {sorted(fired)} of {len(sm['skills'])} slots. The live run "
              "in 11.5 produced {276: 6, 253: 3, 312: 3, 289: 0} -- one slot never "
              "used at all -- and this is that defect as a regression check")

    # 7c. RECHARGE IS PER SLOT, not per agent and not per skill id. A bar may
    #     legitimately carry the same skill twice and the second copy must not
    #     inherit the first's cooldown.
    dup = _world_ally()
    d = dup["agents"][10]
    d["skills"] = (authsrv.ENEMY_SKILL_BAR[0], authsrv.ENEMY_SKILL_BAR[0])
    d["skill_ready"] = [0.0, 0.0]
    first = authsrv.pick_skill(d, time.time())
    d["skill_ready"][first] = time.time() + 999.0
    LEDGER.ok(first == 0 and authsrv.pick_skill(d, time.time()) == 1,
              "a bar carrying the same skill twice recharges the two separately",
              "keyed by SLOT, not by id -- keying by id makes the second copy "
              "share the first's cooldown and the bar quietly one shorter")

    # 7d. the ids and timings are the client's, not ours
    LEDGER.ok(len(authsrv.ENEMY_SKILL_BAR) >= 2
              and len({r[0] for r in authsrv.ENEMY_SKILL_BAR})
                  == len(authsrv.ENEMY_SKILL_BAR)
              and len({r[2] for r in authsrv.ENEMY_SKILL_BAR}) > 1,
              "the bar holds several DISTINCT skills with DIFFERENT recharges",
              f"{authsrv.ENEMY_SKILL_BAR} -- varied recharges are what make the "
              "order observable rather than decorative. Ids and timings are "
              "ArenaNet's from skilltable.py; WHICH four, and the priority order, "
              "are ours, and studies/presearing MANIFEST 7 found no base skill bar "
              "on any Pre-Searing creature page it read, so this bar is a fixture "
              "and not a claim about a Hatcher")

    # 8. the content key reaches the entry, same rule as the other two
    LEDGER.ok("skills" in inspect.getsource(authsrv._spawn_one_enemy),   # the entry literal lives here since --enemies N
              "and spawn_enemy carries the skill from the content row",
              "`entry` is a closed literal; a key that is not named there never "
              "arrives, however it is spelled in world.toml")


def section_constants():
    """Every combat constant, against a LITERAL written here.

    WHY A LITERAL. On 2026-08-11 studies/monsterai/FINDINGS.md 5 sabotaged this
    server's combat constants one at a time and re-ran this file. TWELVE OF
    FOURTEEN could be set to a wrong value with all 125 checks still green:

        SWING_WINDUP      0.899 -> 0.2      125/125 PASS
        ENEMY_MELEE_RANGE 150.0 -> 400.0    125/125 PASS
        AGGRO_RANGE      1200.0 -> 1100.0   125/125 PASS
        ENEMY_TURN_RATE   2pi/3 -> 1.0      RED     <- the only one

    That is not an accident of coverage, it is a shape: every other section
    computes its expectation FROM the symbol under test, so the symbol is free to
    move and the test moves with it. A symbol appearing in a test file is not a
    check. `test_burrow.py` is the model that got this right -- it writes 2.00 in
    the test file and compares.

    So this section is deliberately dumb. It carries the number, not the name.
    Changing a constant now costs a second edit HERE, and that edit is where you
    have to say what changed and why -- which is the whole point, because two of
    these are measured, one is corroborated to the bit, and the rest are ours.

    IT IS NOT A CLAIM THAT THE VALUES ARE RIGHT. Most of them are invented and the
    `why` column says so. It is a claim that they cannot change SILENTLY.
    """
    import authsrv

    # (name, literal, label, why)
    PINNED = (
        ("ATTACK_RANGE", 1500.0, "OURS",
         "how far the PLAYER may reach. Nothing measured it"),
        ("AGGRO_RANGE", 1200.0, "OURS",
         "when a hostile notices, and its leash. GWW says the aggro bubble is "
         "1012 and that named creatures differ in BOTH directions, so this is "
         "not even the right SHAPE -- it should be per-creature "
         "(studies/monsterai 4.2)"),
        ("ENEMY_MELEE_RANGE", 150.0, "OURS",
         "the LEGACY arm's reach and stop (--legacy-npc-chase) since "
         "ANIMREF-RE 40; the default swings from enemy_reach() = "
         "follow_stop_radius() + BOUNDING_RADIUS = 92 and halts at 80 "
         "(sec.40.1 corrected the 144 borrow). Refuted from both sides at "
         "once: ArenaNet's own models strike from ~65, ~599 and ~706 units, "
         "so no single number is right (studies/monsterai 3.3)"),
        ("ENEMY_HIT_FRACTION", 0.10, "OURS", "damage per swing"),
        ("HIT_FRACTION", 0.15, "OURS",
         "the FALLBACK for a swing with no readable weapon, and nothing more "
         "since 2026-08-20. The player's swing is the equipped weapon's own "
         "damage range now -- see PLAYER_SWING_DAMAGE below, which is the "
         "first number in this block that is not ours"),
        ("REVIVE_AFTER", 8.0, "OURS", "how long an agent stays dead"),
        ("PLAYER_REVIVE_AFTER", 10.0, "OURS",
         "a timer, not a resurrection shrine. n=0 player deaths in the corpus"),
        ("ENEMY_MOVE_RATE", 1.0, "OBSERVED",
         "a hostile CHASES at full speed: all 6 retail NPCs that chased the "
         "player were at 1.0 (ANIMREF-RE 40.9); 0.2778 / 0.3333 / 0.3472 are "
         "the pre-aggro walk (studies/monsterai 3.4). Was 0.75, ours, 'so you "
         "can walk away' -- refuted"),
        ("ENEMY_DEST_RESEND", 120.0, "OURS",
         "bandwidth, not mechanics; the LEGACY arm's re-announce distance -- "
         "the default re-paths on retail's 0.5 s clock (FOLLOW_REPATH_INTERVAL)"),
        ("ENEMY_FACING_EPSILON", 0.15, "OURS", "bandwidth, not mechanics"),
        ("ENEMY_SKILL_RANK", 12, "OURS",
         "the rank the enemy casts at. Replaced ENEMY_SKILL_FRACTION = 0.25 at "
         "step 8: the MAGNITUDE is now the client's own scale endpoints, and "
         "only the rank they are read at is ours. 12 is ArenaNet's cap for a "
         "player (AcctTemplate:441); a monster's real rank is unknowable -- "
         "its bar is never sent (studies/monsterai)"),
        ("ENEMY_ATTACK_SPEED", 1.33, "UPSTREAM",
         "agents.ATTACK_SPEED['axe']. The base x modifier FORMULA is corroborated "
         "against the client's own fmul; the 1.33 itself is the wiki's"),
        ("SWING_WINDUP_RATIO", 0.4458, "OBSERVED",
         "mean of 42 paired windups over both live captures -- the LEGACY "
         "arm (--windup-ratio). The shipped default is the additive law; "
         "see the law checks below"),
        ("WINDUP_MODEL", "additive", "OBSERVED",
         "the derived law interval/2 - 0.1 s is the default arm "
         "(ANIMREF-R1, studies/animref/FINDINGS.md sec.1, n=1,042)"),
    )
    for name, literal, label, why in PINNED:
        got = getattr(authsrv, name)
        LEDGER.ok(got == literal,
                  f"{name} is still {literal} ({label})",
                  f"{got} against the literal in this file -- {why}")

    LEDGER.ok(abs(authsrv.ENEMY_TURN_RATE - 2.0 * math.pi / 3.0) < 1e-12,
              "ENEMY_TURN_RATE is still 2*pi/3 (CORROBORATED)",
              f"{authsrv.ENEMY_TURN_RATE!r} -- ArenaNet's own largest quantised "
              "turn rate, bit-identical, and the ONLY constant in this list the "
              "suite could already catch")

    # --- the windup, which is a LAW because both simpler models were refuted ---
    #
    # First the fixed 0.899 fell (2026-08-11, two declared speeds disagree in
    # seconds), then the constant ratio fell (2026-08-30, ANIMREF-R1: four
    # declared intervals disagree in ratio -- 0.4250 at 1.33 rising to 0.4719 at
    # 3.0 -- while windup = interval/2 - 0.1 s holds them all to 6-16 ms and
    # retrodicts Power Shot's bow interval to 1.3 ms). These checks are built to
    # redden under BOTH refuted models, not just the older one.
    LEDGER.ok(not hasattr(authsrv, "SWING_WINDUP"),
              "the fixed SWING_WINDUP constant is GONE, not merely unused",
              "0.899 s paired with our declared 1.33 implies a ratio of 0.6759 -- "
              "47% above the largest ratio ever observed. Leaving the name bound "
              "invites a future call site to reach for it")
    slow, fast = authsrv.swing_windup(2.0), authsrv.swing_windup(1.0)
    LEDGER.ok(abs((slow - fast) - 0.5) < 1e-9,
              "one extra second of declared interval adds exactly half a "
              "second of windup",
              f"{fast:.4f}s at 1.0 against {slow:.4f}s at 2.0 -- the additive "
              "law's slope. A FIXED windup fails this (delta 0), and so does "
              "scoring the old constant back in by hand")
    LEDGER.ok(abs(slow / fast - 2.0) > 0.05,
              "and the windup is NOT proportional to the interval",
              f"ratio {slow / fast:.4f} -- proportionality is the constant-"
              "fraction model ANIMREF-R1 refuted at n=1,042 (residuals grow to "
              "141 ms at interval 3.0 under the best-fit constant); a green "
              "here under that model is impossible, which is the point")
    LEDGER.ok(abs(authsrv.swing_windup(1.33) - 0.565) < 1e-9,
              "our own Hatcher's windup is 0.565 s under the law",
              f"{authsrv.swing_windup(1.33):.4f}s -- the corpus's n=998 bench "
              "population lands at 0.5653 mean; the legacy ratio arm said "
              "0.593, the pre-2026-08-11 constant 0.899")
    LEDGER.ok(abs(authsrv.swing_windup(2.475) - 1.1375) < 1e-9,
              "and Power Shot's bow interval retrodicts to 1.1375 s",
              "measured 1.1374/1.1387 on the two live cycles (castmech M1) -- "
              "the cross-family check the law was never fit to")
    try:
        authsrv.WINDUP_MODEL = "ratio"
        LEDGER.ok(abs(authsrv.swing_windup(1.33) - 0.5929) < 1e-3,
                  "the --windup-ratio legacy arm still answers 0.593",
                  "the revert flag must restore the old wire exactly, or it "
                  "is not a revert")
    finally:
        authsrv.WINDUP_MODEL = "additive"

    # --- the bar against the client's OWN table, not against our comment -------
    #
    # This is the check that would have caught the elite error: authsrv.py claimed
    # all four bar skills were "campaign 1, non-elite" and 276 is elite. Nothing
    # read the table, so the comment was the only witness and it was wrong.
    try:
        import pathlib
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "clientscan"))
        import skilltable
        exe, _why = skilltable.find_exe()
        data = pathlib.Path(exe).read_bytes()
        base, count, _score = skilltable.locate_table(data)
        rows = {i: skilltable.parse_record(data, base, i) for i in range(count)}
    except (Exception, SystemExit) as ex:                      # pragma: no cover
        # NAMED, not swallowed. The first version of this handler said "no
        # readable client build" for every failure and its actual cause was a
        # method name that does not exist -- a skip that lies about WHY is worse
        # than a red check, because it reads as an environment problem forever.
        #
        # AND `SystemExit`, WHICH IS THE HALF THAT NEVER WORKED. `pinned.find()`
        # RAISES SystemExit when the build is not in the vault -- it inherits
        # BaseException, not Exception -- so `except Exception` did not catch it
        # and this handler was unreachable on the one machine it was written for.
        # Until 2026-08-31 a vault-less run of this file printed pinned's refusal
        # and died at rc=1 with NO verdict: the skip below had never once fired.
        # `toolkit/clientscan/test_compositetrap.py` §1 hit exactly this on
        # 2026-08-30 and its fix is the shape copied here; the paragraph beside
        # its floor is the record. A handler that cannot catch what its own
        # dependency throws is the same defect as a skip path nobody has run.
        LEDGER.skip("the bar vs the client's own skill table",
                    f"{type(ex).__name__}: {ex}")
        rows = None

    if rows:
        bar = authsrv.ENEMY_SKILL_BAR
        missing = [sid for sid, _a, _r in bar if sid not in rows]
        LEDGER.ok(not missing,
                  "every skill on the bar exists in the client's own table",
                  f"missing {missing} of {[b[0] for b in bar]}")
        bad = [(sid, a, rows[sid]["activation"]) for sid, a, _r in bar
               if sid in rows and abs(rows[sid]["activation"] - a) > 1e-6]
        LEDGER.ok(not bad,
                  "and each activation matches the table to the millisecond",
                  f"{bad or 'all four agree'} -- a typo'd activation passed every "
                  "check in this file before this line existed")
        bad_r = [(sid, r, rows[sid]["recharge"]) for sid, _a, r in bar
                 if sid in rows and abs(rows[sid]["recharge"] - r) > 1e-6]
        LEDGER.ok(not bad_r,
                  "and so does each recharge",
                  f"{bad_r or 'all four agree'}")
        elite = sorted(sid for sid, _a, _r in bar
                       if sid in rows and rows[sid]["elite"])
        LEDGER.ok(elite == [276],
                  "and exactly one bar skill is elite, which is 276",
                  f"{elite} -- authsrv.py claimed all four were non-elite until "
                  "2026-08-11. This is not a rule about what a bar may contain; "
                  "it is a pin so the COMMENT and the TABLE cannot drift apart "
                  "again. flags bit 2 is set on 391 of 3,443 rows, so it is a "
                  "real field and not a one-row artifact")
        prof = sorted({rows[sid]["profession"] for sid, _a, _r in bar
                       if sid in rows})
        LEDGER.ok(prof == [3],
                  "and all four share the profession the Hatcher is declared with",
                  f"{prof} against the 3 sent at spawn in 0x00A6 -- the one "
                  "non-arbitrary thing about this selection")


def section_opcode_pins():
    """Every opcode this file names, against a LITERAL written here.

    THE SAME DEFECT AS section_constants, ONE LAYER DOWN, and it survived that
    section by a year of nobody looking. That section exists because twelve of
    fourteen combat constants could be set to a wrong value with every check
    green. On 2026-08-13 a sweep did the same thing to the OPCODES -- moving one
    GAME_SMSG constant in authsrv.py by one and re-running this file, fifteen
    times, with each patch verified twice (the line on disk, and getattr on the
    imported module, because an earlier attempt matched the constants by DECIMAL
    text while authsrv.py writes hex and scored eleven non-edits as caught):

        3 of 15 caught, 12 MISSED

    and of the three, exactly ONE was a check: section 1's
    `WORLD_REMOVE_AGENT == 0x0021`. The other two died on a TRACEBACK rather
    than a named failure and never reached the ledger at all -- 0x00B0 on a
    `KeyError: 176` out of `sizes[0x00B0]`, a dict keyed by the symbol and read
    by a literal, and 0x00B1 on the codec's own arity guard. Both are accidents
    of how those checks happen to be written; neither would survive a tidy-up.

    Everything else computed its expectation FROM the symbol under test, so the
    symbol was free to move and the file moved with it. A symbol appearing in a
    test file is not a check.

    THE SECOND COLUMN IS WHAT MAKES THE FIRST ONE MORE THAN A COPY. A literal
    that only agrees with the constant it guards is two copies of one belief, so
    each row also carries the wire SHAPE `schema/messages.json` holds at that
    opcode, and the checks below read it out of the catalog rather than out of
    authsrv. The catalog is not ours -- `test_catalog.py` scores it 477/477
    field-for-field against build 38797's own message-format tables -- so a
    wrong literal here has to be wrong in the client's tables too, which is an
    assertion the artifact can refuse. Eight of the fifteen carry a NAME in
    `schema/overrides.json` as well and that is checked separately.

    IT IS NOT A CLAIM THAT EVERY NUMBER IS RIGHT. Two of the fifteen are
    INFERRED and the `why` column says which. It is a claim that they cannot
    change silently.
    """
    import json
    import authsrv

    # (symbol, opcode, catalog field types after the header, why)
    #
    # `shape` is `schema/messages.json`'s own field list minus the msg_header.
    # NOTE 0x00A0 and 0x00A3 share a shape exactly -- that is the evidence
    # authsrv.py's own comment calls INFERRED, and it means shape alone cannot
    # separate those two. The literal opcode is what separates them.
    PINNED = (
        ("GAME_SMSG_WORLD_REMOVE_AGENT", 0x0021, ("dword",),
         "overrides.json names it, confidence high; OBSERVED 416 times in the "
         "first live capture. Also asserted in section 1, which is left alone: "
         "that section is ABOUT this message"),
        ("GAME_SMSG_AGENT_MOVE_TO_POINT", 0x0029,
         ("dword", "vec2", "word", "word"),
         "overrides.json, high -- the destination half of the chase"),
        ("GAME_SMSG_AGENT_UPDATE_SPEED", 0x002B, ("dword", "float", "byte"),
         "overrides.json, high; 163 of them in ArenaNet's own tapes"),
        ("GAME_SMSG_AGENT_UPDATE_ROTATION", 0x002E,
         ("dword", "dword", "dword"),
         "overrides.json, high. The two dwords hold float32 bits, which is the "
         "trap section_facing is built around"),
        ("GAME_SMSG_PLAYER_INFO", 0x0059,
         ("dword", "agent_id", "dword", "byte", "dword", "dword", "string16"),
         "overrides.json, high -- PLAYER_CREATE, and the record 0x00B0/0x00B1 "
         "need to exist first"),
        ("GAME_SMSG_AGENT_PROPERTY_UPDATE_INT", 0x009F,
         ("dword", "agent_id", "dword"),
         "no catalog name. GWCA's GenericValue; test_msghandler.py CORROBORATES "
         "the pairing from the client's own dispatch -- 0x009F/0x00A0 share one "
         "callee and 0x00A2/0x00A3 another, splitting the four shapes on the "
         "int/float line"),
        ("GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET", 0x00A0,
         ("dword", "agent_id", "agent_id", "dword"),
         "no catalog name, and INFERRED: authsrv.py's own comment says the "
         "shape match with 0x00A3 is the whole argument. Same dispatch pairing"),
        ("GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET", 0x00A3,
         ("dword", "agent_id", "agent_id", "dword"),
         "no catalog name. OBSERVED from the other end on 2026-08-11: the "
         "client's CharPool.cpp:84 crash trace carries OUR 0x00A3 three frames "
         "under the assert (section_pool_fraction)"),
        ("GAME_SMSG_AGENT_SET_PROFESSION", 0x00A6, ("agent_id", "byte", "byte"),
         "overrides.json, high; 387 live samples, primary 1..6 and never 0"),
        ("GAME_SMSG_PLAYER_PARTY_SIZE", 0x00B0, ("word", "byte"),
         "no catalog name. 5 wire bytes and the handler reads +4; caught before "
         "today only by a KeyError out of section_party_of_one's size dict"),
        ("GAME_SMSG_PLAYER_SET_PARTY", 0x00B1, ("word", "word"),
         "overrides.json, confidence MEDIUM -- the weakest name of the eight, "
         "which is a reason to pin it rather than not to"),
        ("GAME_SMSG_AGENT_PROFESSION_BITS", 0x00B6,
         ("agent_id", "dword"),
         "overrides.json since 2026-08-19, confidence MEDIUM -- named from the "
         "client's own OnProfessionSecondaryBits log string "
         "(studies/pvpui/FINDINGS.md 30; studies/profession/RUNS.md 13). Its "
         "neighbour 0x00B7 is the message it must be sent AFTER, so a +1 slip "
         "here is the exact confusion"),
        ("GAME_SMSG_AGENT_PROFESSIONS", 0x00B7,
         ("agent_id", "byte", "byte", "byte"),
         "overrides.json since 2026-08-19, high. 9 wire bytes carrying "
         "profession as one byte. This server called it "
         "PLAYER_UPDATE_PROFESSION until then -- ldufr/OpenTyria's label, "
         "UPSTREAM, and wrong twice: the record is keyed on AGENT (we send it "
         "for the hero's agent, not only the player's) and the rest of that "
         "cluster puts the name on 0x00B6 (studies/skills/FINDINGS.md; "
         "studies/character/FINDINGS.md). The catalog's name won"),
        ("GAME_SMSG_SKILL_ACTIVATED", 0x00E3, ("agent_id", "word", "dword"),
         "no catalog name, and 0x00E3 rather than 0x00E4 is MEASURED: 0x00E4's "
         "handler compares the agent against your own and returns early"),
        ("GAME_SMSG_AGENT_UPDATE_STATUS", 0x00F1, ("agent_id", "dword"),
         "overrides.json, high. Its create-time sibling 0x00F0 is one below and "
         "carries the same two fields, so a +1 slip is silent on the wire"),
    )

    for name, opcode, _shape, why in PINNED:
        got = getattr(authsrv, name)
        LEDGER.ok(got == opcode,
                  f"{name} is still {opcode:#06x}",
                  f"{got:#06x} against the literal in this file -- {why}")

    # AXIS 2: the catalog's own field list, read from the file rather than from
    # authsrv. A literal that agrees only with the constant it guards is one
    # belief written twice.
    schema_dir = os.path.join(os.path.dirname(os.path.dirname(HERE)), "schema")
    with open(os.path.join(schema_dir, "messages.json"), encoding="utf-8") as f:
        catalog = json.load(f)["channels"]["GAME_SMSG"]["messages"]
    # THE OVERRIDES ARE PART OF THE CATALOG, as they are for the codec: three
    # GAME_SMSG field lists are corrected there (140, 146, 421), and since
    # SLICE-B8 this server SENDS 421 -- the 39-byte GAME_SERVER_TRANSFER the
    # client's own tables gave -- so a walk over messages.json alone scored a
    # correct send site as "sends 7, catalog wants 6" (2026-09-12).
    with open(os.path.join(schema_dir, "overrides.json"), encoding="utf-8") as f:
        for k, e in json.load(f)["channels"]["GAME_SMSG"].items():
            if "fields" in e:
                catalog.setdefault(k, dict(e))["fields"] = e["fields"]
    wrong_shape = []
    for name, opcode, shape, _why in PINNED:
        entry = catalog.get(str(opcode))
        got = None if entry is None else tuple(
            fld["type"] for fld in entry["fields"][1:])
        if got != shape:
            wrong_shape.append(f"{name} {opcode:#06x}: catalog {got}, "
                               f"pinned {shape}")
    LEDGER.ok(not wrong_shape,
              "and each pinned opcode has the wire shape written beside it",
              f"{wrong_shape}" if wrong_shape else
              f"{len(PINNED)} of {len(PINNED)} agree with schema/messages.json, "
              "which test_catalog.py scores 477/477 against build 38797's own "
              "format tables -- so a wrong literal here would have to be wrong "
              "in ArenaNet's tables too")

    # AXIS 3: the fourteen the catalog NAMES. overrides.json's names came off
    # ArenaNet's recorded traffic joined to the client's dispatch handlers
    # (studies/smsg), i.e. from outside this repo's own opinions.
    with open(os.path.join(os.path.dirname(os.path.dirname(HERE)),
                           "schema", "overrides.json"), encoding="utf-8") as f:
        ov = json.load(f)["channels"]["GAME_SMSG"]
    named = {int(k): v["name"] for k, v in ov.items()
             if isinstance(v, dict) and v.get("name")}
    disagree = [f"{name} -> catalog says {named[opcode]}"
                for name, opcode, _s, _w in PINNED
                if opcode in named and name != "GAME_SMSG_" + named[opcode]]
    hits = [name for name, opcode, _s, _w in PINNED if opcode in named]
    LEDGER.ok(not disagree and len(hits) == 14,
              "and the fourteen the catalog names are named the same thing here",
              f"{disagree or len(hits)} of 14 -- 0x0021, 0x0029, 0x002B, 0x002E, "
              "0x0059, 0x009F, 0x00A0, 0x00A3, 0x00A6, 0x00B1, 0x00B6, 0x00B7, "
              "0x00E3, 0x00F1. (Twelve until 2026-08-19, when the pvpui pass "
              "read the per-agent PROFESSION table at charCtx+0x6BC and named "
              "0x00B6/0x00B7 AGENT_PROFESSION_BITS/AGENT_PROFESSIONS -- "
              "studies/pvpui/FINDINGS.md 30. Those two are the first the "
              "catalog named DIFFERENTLY from this server, and the CATALOG "
              "won: PLAYER_UPDATE_PROFESSION was ldufr/OpenTyria's label, "
              "UPSTREAM, and it hangs the wrong noun on an agent-keyed message "
              "we also send for the hero. Nine until 2026-08-18, when the "
              "smsgnames static pass named 0x009F/0x00A0/0x00A3 "
              "AGENT_PROPERTY_UPDATE_INT/_INT_TARGET/_FLOAT_TARGET in "
              "overrides.json -- studies/smsgnames, the exact names this file "
              "already pinned. Eight until 2026-08-14, when the cast-cycle "
              "promotion named 0x00E3 SKILL_ACTIVATED -- studies/combat step "
              "3.) The one that remains -- 0x00B0 -- has no name in "
              "overrides.json at all, which is why its `why` column has to "
              "carry the evidence")


def section_opcode_catalog():
    """Every send site in the authsrv family, against the catalog's field count.

    THE PINS ABOVE PROTECT FIFTEEN OPCODES. authsrv.py declares SIXTY-TWO, and
    the other forty-seven have no pin anywhere in the suite. This is the cheap
    control that reaches them, and it is deliberately not a second table of
    literals: it walks the family's own `send(GAME_SMSG_X, [...])` sites, counts
    the payload, and requires that count to equal the number of fields
    `schema/messages.json` declares at that opcode. Nothing is written down, so
    nothing has to be maintained, and the comparison is between two artifacts
    rather than between a value and itself.

    READ THE COVERAGE BEFORE TRUSTING IT. Measured 2026-08-13 by shifting each
    of the 62 constants by +1 one at a time: **42 of 62 detected, 20 blind**,
    and the blind set is named because a control read as total coverage is
    worse than no control. Fourteen constants have no literal-list send site to
    measure at all -- AGENT_PROFESSIONS, AGENT_PROFESSION_BITS,
    AGENT_SET_PROFESSION, AGENT_SET_TABARD_VISIBLE, AGENT_UPDATE_ALLEGIANCE,
    AGENT_UPDATE_FLAGS, AGENT_UPDATE_POSITION, AGENT_UPDATE_SPEED,
    CHARACTER_UPDATE_FACTIONS, CREATE_NAMED_ITEM, MONSTER_COMPOSITE,
    NPC_UPDATE_PROPERTIES, PLAYER_PARTY_SIZE, PLAYER_SET_PARTY
    (they are sent through a builder, or with a computed list) -- and six more
    land on a NEIGHBOUR OF THE SAME ARITY and are invisible to this mechanism:
    AGENT_INITIAL_STATUS 0x00F0, MAP_UPDATE_CURRENT 0x0099,
    PVP_UPDATE_UNLOCKED_SKILLS 0x001D, SKILL_ACTIVATED 0x00E3,
    WORLD_SIMULATION_TICK 0x001E, WORLD_UPDATE_CONTROLLED_AGENT 0x0022. Nine of
    the twenty are pinned by name in the section above; the remaining eleven are
    protected by nothing, and saying so is the point of this paragraph.

    WHAT IT IS GOOD AT, which is not the same question: a payload whose length
    disagrees with the catalog is a message the codec refuses at the moment it
    is first sent, which for a rarely-taken branch means a live session. All 48
    measurable sites agree today. The second check is the negative control --
    the walk is re-run against a map with every opcode shifted -- because a
    comparison that has never reported anything is not a comparison, and the
    third is that the walk found sites at all, which is test_codec.py's own
    fixture-glob failure written down.
    """
    import ast
    import glob
    import json
    import authsrv

    # THE FAMILY, NOT THE FILE. This read authsrv.py alone until 2026-09-11,
    # when the modularisation arc moved send sites out into leaves beside it
    # (connreport.py, merchant.py, probemerchant.py on that date, carrying six
    # opcodes between them). A walk still reading one file loses those without
    # a word -- the silent shrink toward zero the two floors below exist to
    # catch. The family is DISCOVERED, not written down: any sibling module
    # that contains a `send(GAME_SMSG_` call joins the walk, so a leaf that
    # gains one later is covered with no edit here. Tests are excluded: this
    # file and three others contain such calls as fixtures.
    _home = os.path.dirname(os.path.abspath(authsrv.__file__))
    family = [os.path.abspath(authsrv.__file__)]
    for path in sorted(glob.glob(os.path.join(_home, "*.py"))):
        if os.path.basename(path).startswith("test_") or path in family:
            continue
        with open(path, encoding="utf-8") as f:
            if "send(GAME_SMSG_" in f.read():
                family.append(path)
    srcs = []
    for path in family:
        with open(path, encoding="utf-8") as f:
            srcs.append(f.read())
    schema_dir = os.path.join(os.path.dirname(os.path.dirname(HERE)), "schema")
    with open(os.path.join(schema_dir, "messages.json"), encoding="utf-8") as f:
        catalog = json.load(f)["channels"]["GAME_SMSG"]["messages"]
    # THE OVERRIDES ARE PART OF THE CATALOG, as they are for the codec: three
    # GAME_SMSG field lists are corrected there (140, 146, 421), and since
    # SLICE-B8 this server SENDS 421 -- the 39-byte GAME_SERVER_TRANSFER the
    # client's own tables gave -- so a walk over messages.json alone scored a
    # correct send site as "sends 7, catalog wants 6" (2026-09-12).
    with open(os.path.join(schema_dir, "overrides.json"), encoding="utf-8") as f:
        for k, e in json.load(f)["channels"]["GAME_SMSG"].items():
            if "fields" in e:
                catalog.setdefault(k, dict(e))["fields"] = e["fields"]

    def fields_at(opcode):
        entry = catalog.get(str(opcode))
        return None if entry is None else len(entry["fields"]) - 1

    # every `send(GAME_SMSG_*, [ ... ])` whose payload is a literal list
    arity = {}
    for src in srcs:
        for node in ast.walk(ast.parse(src)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "send" and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id.startswith("GAME_SMSG_")
                    and isinstance(node.args[1], ast.List)):
                arity.setdefault(node.args[0].id, set()).add(
                    len(node.args[1].elts))
    # a symbol sent with two different payload lengths cannot be measured this
    # way; it is dropped rather than guessed at, and it counts as a blind spot.
    sites = {k: v.pop() for k, v in
             ((k, set(v)) for k, v in arity.items()) if len(v) == 1}

    def disagreements(values):
        out = []
        for name, n in sorted(sites.items()):
            want = fields_at(values[name])
            if want != n:
                out.append(f"{name} {values[name]:#06x}: sends {n}, "
                           f"catalog wants {want}")
        return out

    live = {name: getattr(authsrv, name) for name in sites}
    bad = disagreements(live)
    LEDGER.ok(not bad,
              "every measurable send site's payload length matches the catalog",
              f"{bad}" if bad else f"{len(sites)} site(s) of "
              f"{len(live)} symbol(s) agree -- a payload the catalog does not "
              "want is a ValueError out of codec.encode the first time that "
              "branch is taken, which for a rare branch is a live session")

    # THE NEGATIVE CONTROL. Shift each opcode by one, ALONE, and count how many
    # the comparison notices. A control that shifted everything at once would
    # measure a bulk edit nobody makes; one at a time is the mistake that
    # happens, and the number it produces IS the coverage claim above.
    detected = [name for name in sites
                if disagreements(dict(live, **{name: live[name] + 1}))]
    LEDGER.ok(len(detected) >= 35,
              "and a one-opcode shift is NOTICED for most of them (control)",
              f"{len(detected)} of {len(sites)} measurable symbols detected "
              f"under a +1 shift; 42 of the full 62 measured 2026-08-13. The "
              f"floor is 35 rather than the measured number because adding a "
              f"send site moves it -- what must not happen is this collapsing "
              f"toward zero, which is what a broken walk looks like. Blind: "
              f"{sorted(set(sites) - set(detected))}")

    LEDGER.ok(len(sites) >= 40,
              "and the walk actually found the send sites it claims to check",
              f"{len(sites)} symbols with an unambiguous literal payload, 48 "
              "on 2026-08-13. A walk matching nothing reports zero "
              "disagreements and looks green -- test_codec.py printed ALL "
              "CHECKS PASSED with its fixture glob matching no files")


def section_named_builders(codec):
    """The five messages named 2026-08-10 and first sent 2026-08-11.

    Each builder enforces a bound the CLIENT asserts on itself, so what these
    guard against is an assert dialog mid-session rather than a wrong pixel.
    The refusals are checked one by one: a guard nothing exercises rots into a
    comment, and every one of these is a mistake a caller can plausibly make.
    """
    built = {
        0x002B: agents.agent_update_speed(7, 0.5),
        0x002E: agents.agent_update_rotation(7, math.pi / 2, 2.0943952),
        0x0026: agents.agent_update_flags(7, agents.AGENT_KIND_NPC),
        0x00A6: agents.agent_set_profession(7, 4),
        0x0048: agents.agent_set_tabard_visible(7, False),
    }
    bad = []
    for op, vals in built.items():
        raw = codec.encode("GAME_SMSG", op, vals)
        msgs, used, _rest = codec.decode_stream("GAME_SMSG", raw)
        if used != len(raw) or len(msgs) != 1 or list(msgs[0][1][1:]) != list(vals):
            bad.append(f"0x{op:04X}")
    LEDGER.ok(not bad,
              "the five newly-sendable messages encode and read back unchanged",
              f"mismatched: {bad}" if bad else
              "0x002B, 0x002E, 0x0026, 0x00A6, 0x0048 -- each through the real "
              "catalog, consuming exactly its own bytes. Before 2026-08-11 this "
              "server could not send any of them: 0x0026 had a constant and no "
              "send site, the other four were not even defined")

    # 0x002E's payload is two u32s carrying float32 bits. If someone "fixes" the
    # catalog to float -- which the values invite, and which nearly happened to
    # GAME_CMSG 0x0040 -- this goes red instead of the wire silently changing.
    ang = agents.agent_update_rotation(7, math.pi / 2, 2.0943952)
    back = struct.unpack("<f", struct.pack("<I", ang[1]))[0]
    LEDGER.ok(all(isinstance(v, int) for v in ang[1:])
              and abs(back - math.pi / 2) < 1e-6,
              "0x002E marshals its two floats as u32 and the bits survive",
              f"angle bits {ang[1]:#010x} decode to {back:.6f} rad -- the values "
              f"are floats and the marshalling is not, exactly as for GAME_CMSG "
              f"0x0040 ROTATE_PLAYER, where 'correcting' the type would have "
              f"broken a message we understand")

    refusals = [
        ("a speed in units/s, which is the obvious caller error",
         agents.agent_update_speed, (7, 288.0)),
        ("a speed under the client's own floor",
         agents.agent_update_speed, (7, 0.001)),
        ("a facing outside AGENT_FACING_MASK",
         agents.agent_update_speed, (7, 0.5, 0x10)),
        ("an angle outside +/-pi",
         agents.agent_update_rotation, (7, 10.0, 1.0)),
        ("an angle of NaN, which is not the sentinel",
         agents.agent_update_rotation, (7, float("nan"), 1.0)),
        ("a turn rate of zero",
         agents.agent_update_rotation, (7, 0.0, 0.0)),
        ("flags inside the mask the client keeps for itself",
         agents.agent_update_flags, (7, 0x10000)),
        ("a primary profession of 0, which does NOT mean 'none'",
         agents.agent_set_profession, (7, 0)),
        ("a secondary profession equal to the primary",
         agents.agent_set_profession, (7, 4, 4)),
        ("a custom profession WITHOUT the opt-in",
         agents.agent_set_profession, (7, 12)),
        ("a custom SECONDARY without the opt-in",
         agents.agent_set_profession, (7, 4, 12)),
        ("a profession past the u8 the wire carries, even WITH the opt-in",
         agents.agent_set_profession, (7, 256, 0, True)),
    ]
    for label, fn, args in refusals:
        try:
            fn(*args)
            ok = False
        except ValueError:
            ok = True
        LEDGER.ok(ok, f"and it refuses {label}",
                  "raised ValueError" if ok else
                  "ACCEPTED -- the client would have asserted instead")

    # The sentinel is a real value and must NOT be caught by the angle guard.
    spin = None
    try:
        spin = agents.agent_update_rotation(7, float("inf"), 1.0)
        ok = spin[1] == 0x7F800000
    except ValueError:
        ok = False
    LEDGER.ok(ok,
              "but +inf passes, because it is the client's own free-spin sentinel",
              f"angle bits {spin[1]:#010x} == +inf" if ok else
              "the guard swallowed the sentinel, which would make the message "
              "unusable for the one case it is most needed")

    # THE PROFESSION BOUND, against literals written here.
    #
    # This file's own §"combat constants" section exists because twelve of
    # fourteen constants could be set to a wrong value with every check green --
    # every other section computed its expectation FROM the symbol under test, so
    # the symbol was free to move and the test moved with it. Same trap here, so
    # the numbers are literals and not `agents.CHAR_PROFESSIONS`.
    LEDGER.ok(agents.CHAR_PROFESSIONS == 11,
              "the client's compiled profession bound is 11",
              f"{agents.CHAR_PROFESSIONS} -- ids 0..10, MEASURED on build 38797 "
              f"at 29 assert sites across 13 modules (studies/profession/)")
    LEDGER.ok(agents.PROFESSION_FIELD_MAX == 255,
              "and the wire field is a u8",
              f"{agents.PROFESSION_FIELD_MAX} -- 0x00A6 is 8 wire bytes and "
              f"0x00B7 is 9, both carrying profession as one byte")

    # The bound USED to be 6 -- the largest primary our (early-Prophecies) corpus
    # happened to contain -- and enforcing it refused four professions that ship
    # and that reach this function straight from content. This is the regression
    # check for that, and it is a positive: 7..10 must be ACCEPTED.
    shipped_ok = []
    for prof in (7, 8, 9, 10):
        try:
            agents.agent_set_profession(7, prof)
            shipped_ok.append(prof)
        except ValueError:
            pass
    LEDGER.ok(shipped_ok == [7, 8, 9, 10],
              "and professions 7..10 -- which SHIP -- are accepted",
              f"{shipped_ok} of [7, 8, 9, 10]. The old bound of 6 refused all "
              f"four; an Assassin NPC in content raised ValueError")

    custom = None
    try:
        custom = agents.agent_set_profession(7, 12, 0, custom=True)
    except ValueError:
        pass
    LEDGER.ok(custom == [7, 12, 0],
              "and a custom id passes WITH the opt-in, unchanged",
              f"{custom} -- the value must reach the wire as sent; a guard that "
              f"clamped it would make the probe measure our clamp, not the client")


def section_probe_encoding():
    """Every probe step must ENCODE, and nothing in the suite checked that.

    `probes.check_encodable()` exists precisely because a probe that fails to
    encode wastes a whole client run -- the client has to be launched, logged in
    and walked into a map before the first packet fires. It was reachable only
    from `probes.py`'s own `__main__`, so the suite never ran it and a broken
    probe would have been discovered by spending the run.
    """
    import probes
    counts = {}
    failures = probes.check_encodable(quiet=True, counts=counts)
    LEDGER.ok(failures == 0,
              "every step of every probe encodes",
              f"{failures} failures -- an unencodable step is only discovered "
              f"by launching a client, which is the most expensive way to find "
              f"a typo in this repo")
    # NOT REDUNDANT, and the reason is the same one `test_codec.py`'s fixture
    # glob taught: `failures == 0` is ALSO what a machine that could build no
    # probe at all reports. Some probes bind vault content while their steps are
    # built, so on a bare machine the walk legitimately skips those -- but if it
    # ever skips ALL of them, the check above passes having encoded nothing.
    LEDGER.ok(counts["checked"] > 0,
              "and the walk actually encoded something -- 0 failures over 0 "
              "steps is not a pass",
              f"checked={counts['checked']}, skipped={counts['skipped']} -- a "
              f"green line above with nothing checked is the vacuity shape, not "
              f"a clean tree")
    if counts["skipped"]:
        # Printed, never silent: these probes exist and were not measured here.
        LEDGER.skip("probes whose steps need vault content to build",
                    "; ".join(f"{n} ({why})" for n, why in counts["skipped"]))

    # A REFUSAL step sends nothing, so there is nothing to encode. This went red on
    # 2026-08-13 for the best possible reason: the all-zero sweep FINISHED, `remaining`
    # went to 0, `smsgsweep_steps` returned its "NO PLAN" refusal, and the encoder tried
    # to encode it -- 0x0000 is a real opcode wanting one value, so a completed sweep
    # reported itself as a broken probe.
    refusal = probes.Step(0.0, 0x0000, [], "refusal", "sends nothing", sends=False)
    LEDGER.ok(refusal.sends is False and probes.Step(0.0, 0x0000, [1], "x", "y").sends,
              "a step declares whether it SENDS, and the default is that it does",
              "the flag defaults True, so an existing step cannot become invisible to "
              "the encoder by omission")

    # THE CONTROL, and it is the whole reason `sends` is a declared flag rather than an
    # `if not step.values` shape test. A malformed step that carries no values and DOES
    # claim to send is exactly what this section exists to catch, and it is bytewise
    # identical to the refusal apart from the flag. Skipping on shape would have made
    # the check unable to fail for its own reason.
    class _Probe:
        steps = [probes.Step(0.0, 0x0000, [], "malformed", "should be caught")]
    saved = probes.get
    try:
        probes.get = lambda name, n=1: _Probe()
        caught = probes.check_encodable(quiet=True)
    finally:
        probes.get = saved
    LEDGER.ok(caught > 0,
              "CONTROL: a valueless step that still claims to SEND is caught",
              f"{caught} failure(s) -- identical to the refusal but for the flag, so a "
              f"shape-based skip would have silently stopped catching broken probes")

    section_planless_probe()


def _plan_steps(plan_obj, strict=False):
    """`_smsgsweep_steps` for a plan, reached THROUGH A REAL FILE and NO VAULT.

    `plan_path` is monkeypatched rather than used, so nothing here reads
    `vault/probes/smsgsweep-plan.json` -- which is the whole point of the section
    below. It also means every key of a row's `set` arrives as a STRING, the way
    JSON delivers it, rather than as the int an in-memory fixture would hand over.

    `strict` picks WHICH `send` the run gets, and the two model the two ways the
    unfixed `run_probe` failed. They are both needed and the sabotage is what
    proved it: reverting the fix reddens the permissive run's check and NOT the
    strict run's, because a `send` that never raises never reaches the branch
    that misreports the refusal.

      strict=False -- a send that ACCEPTS anything, which is the refusal whose
        opcode the degenerate encoder can fill. The old code put the packet on
        the wire here, under the words "nothing was sent".
      strict=True  -- a send that refuses an empty payload the way the codec
        really does (`GAME_SMSG 0x0000 wants 1 values, got 0`). The old code
        printed `SEND FAILED: ValueError` and `that is a result too -- record
        it` here, and `continue`d past the `watch` line.

    Returns (steps, sent, printed, failures): the Steps the builder produced,
    whatever `run_probe` actually handed to `send`, everything it printed, and
    what `check_encodable` scored -- all four with THIS plan in place rather than
    whatever the last sweep left in the vault.
    """
    import contextlib
    import io
    import json
    import tempfile
    import authsrv
    import probes
    import smsgsweep

    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8")
    fh.close()
    if plan_obj is None:
        os.unlink(fh.name)              # the MISSING-plan case: no file at all
    else:
        with open(fh.name, "w", encoding="utf-8") as out:
            json.dump(plan_obj, out)

    class _Stop:
        """Never sleeps. The first step of a real plan waits settle+control -- ten
        seconds -- and a suite that paid it would be deleted."""

        def wait(self, delay):
            return False

    sent = []

    def _send(op, vals, label=""):
        if strict and not vals:
            # What the real send does with the refusal, via the codec.
            raise ValueError(f"GAME_SMSG 0x{op:04X} wants 1 values, got 0")
        sent.append((op, list(vals), label))

    real = smsgsweep.plan_path
    smsgsweep.plan_path = lambda: fh.name
    buf = io.StringIO()
    try:
        steps = probes._smsgsweep_steps(1, None)
        failures = probes.check_encodable(quiet=True)
        with contextlib.redirect_stdout(buf):
            thread = authsrv.run_probe("smsgsweep", _send, 1, _Stop(), None)
            if thread is not None:
                thread.join(timeout=20)
    finally:
        smsgsweep.plan_path = real
        if os.path.isfile(fh.name):
            os.unlink(fh.name)
    return steps, sent, buf.getvalue(), failures


def section_planless_probe():
    """The plan-less run, pinned so the suite's COLOUR stops tracking vault state.

    Every check above builds its own Step. The producer -- `_smsgsweep_steps` --
    was checked by nothing, and it reads a file in `vault/probes/` that any sweep
    in any session rewrites. So on 2026-08-13 this section went red not because
    anything broke but because the all-zero sweep had FINISHED: `remaining` went
    to 0, the plan emptied for the best possible reason, and the refusal it
    returns could not encode. Whether the suite is green depended on what the
    last sweep left behind, and nothing pinned either answer. Both are pinned
    here, through a temp file, with no vault and no socket.

    The runtime half is a separate claim from the encoder half and it is the one
    that was still broken after `sends` landed. `check_encodable` honoured the
    flag; `authsrv.run_probe` did not, and it is the consumer that puts bytes on
    a socket. Both of its `send` fixtures are needed, one per failure direction,
    and `_plan_steps`'s docstring says which is which.

    WHICH CHECKS ARE LOAD-BEARING WAS MEASURED. Four sabotages were built and
    run against a green 223, and all four redden a DIFFERENT set:

      run_probe forgets the flag (the defect as it shipped)  2 red
      the sentinel is built without sends=False              5 red
      run_probe skips EVERY step, not just refusals          2 red
      check_encodable stops honouring the flag               1 red

    The third is the one that earns the positive control: it reddens the two
    control checks and NOTHING else, so without them "skip every step" -- a
    sweep that fires no packets and prints "probe complete" -- would have been
    indistinguishable from the fix. The first is why there are two runtime
    fixtures: with only the permissive `send` it reddened 1 rather than 2,
    because that fixture never reaches the branch that misreports the refusal.
    """
    import probes

    empty, empty_sent, _eo, empty_bad = _plan_steps({"rows": [],
                                                     "remaining": 0})
    LEDGER.ok(empty_bad == 0,
              "with NO plan at all, `check_encodable` still scores 0 -- the "
              "headline this section exists for",
              f"{empty_bad} failure(s) against an EMPTY plan installed for the "
              f"call. The check at the top of this section reads the real "
              f"vault, so it measured a plan of 1 row today and a plan of 0 "
              f"rows on 2026-08-13; only this one answers the question on "
              f"purpose")
    LEDGER.ok(len(empty) == 1 and empty[0].sends is False,
              "an EMPTY plan makes the builder return one step that declares "
              "sends=False",
              f"{len(empty)} step(s), sends={[s.sends for s in empty]} -- the flag "
              f"is set by the PRODUCER, which no check above reaches: they all "
              f"build their own Step and would pass against a sentinel that "
              f"dropped it")

    missing, _ms, _mo, _mb = _plan_steps(None)
    LEDGER.ok(len(missing) == 1 and missing[0].sends is False,
              "and so does a MISSING plan file -- `load_plan` returns None there, "
              "a different branch",
              f"{len(missing)} step(s), sends={[s.sends for s in missing]}")

    LEDGER.ok(not empty_sent,
              "RUNTIME: the plan-less probe hands NOTHING to `send`",
              f"{len(empty_sent)} packet(s): {empty_sent} -- until this check, "
              f"`run_probe` sent it and relied on the codec to refuse. A `send` "
              f"that does not refuse puts 0x0000 on the wire, and that is the "
              f"hazard the sends flag was chosen over making the sentinel "
              f"encodable")
    # The OTHER half, and it needs its own fixture. A send that accepts anything
    # never reaches the misreporting branch, so reverting the fix leaves the check
    # above red and this one GREEN -- measured, not assumed. `strict` models the
    # codec that really is behind `send` today.
    _se, strict_sent, strict_out, _sb = _plan_steps({"rows": [], "remaining": 0},
                                                    strict=True)
    LEDGER.ok(not strict_sent
              and "nothing was sent; this run measures nothing" in strict_out
              and "SEND FAILED" not in strict_out
              and "that is a result too" not in strict_out,
              "and against the REAL codec's refusal the operator is told why, "
              "not shown a ValueError filed as a result",
              f"printed {strict_out.count('SEND FAILED')} SEND FAILED line(s). "
              f"The old path printed `SEND FAILED: ValueError` and `that is a "
              f"result too -- record it`, filing an absent plan as an "
              f"experimental result, then `continue`d past the one line the "
              f"step exists to carry")

    # THE POSITIVE CONTROL, and it is the check that stops the fix from being
    # "skip everything". A refusal-skip that fired on every step, or a sentinel
    # hard-coded sends=False, would make each of the four checks above pass while
    # every real sweep step went unsent -- a probe that measures nothing and
    # prints "complete", which is the exact shape all of this exists to prevent.
    live, live_sent, live_out, _lb = _plan_steps(
        {"rows": [{"opcode": 0x0021, "predicted": "CONTROL"}], "remaining": 1})
    LEDGER.ok(len(live) == 1 and live[0].sends is True
              and [op for op, _v, _l in live_sent] == [0x0021],
              "CONTROL: a plan WITH a row still sends -- sends=True, and the "
              "packet reaches `send`",
              f"sends={[s.sends for s in live]}, sent="
              f"{[hex(op) for op, _v, _l in live_sent]} -- a skip that fired on "
              f"every step would satisfy all four checks above and silently stop "
              f"the sweep from measuring anything")
    LEDGER.ok("REFUSAL" not in live_out,
              "and it is not announced as a refusal",
              "the two paths print differently, so an operator reading the "
              "gamesrv log can tell a run that measured something from one "
              "that could not")


def section_secondary_bits():
    """0x00B6, and the two ways it fails SILENTLY.

    RUNS.md §13. The message carries a per-profession bitmask into field +0xC
    of the per-agent record at ctx[0x2c]+0x6BC, and the drop-down builder
    tests it bit by bit over ids 0..10. Two failure modes leave no trace on
    the wire and no error anywhere, which is why they are pinned here:

    ORDER. The handler finds the record by binary search and, on a miss, logs
    and returns WITHOUT STORING. The record is created by 0x00B7. So a 0x00B6
    emitted before that agent's first 0x00B7 is dropped in silence.

    RANGE. The consumer's loop is `cmp edi, 0xb` -- ids 0..10 -- so a bit
    above 10 can never be read, and a custom profession cannot be offered as
    a secondary however the mask is set.
    """
    import ast
    import authsrv

    LEDGER.ok(agents.secondary_bits(2, 6) == 0x0044,
              "the mask is one bit per profession id: {2,6} -> 0x0044",
              f"{agents.secondary_bits(2, 6):#06x} -- the builder does "
              f"`shl 1,cl / test edx,eax` with cl = the profession id, so the "
              f"bit index IS the id")
    LEDGER.ok(agents.ALL_SECONDARIES == 0x07FE,
              "and all ten shipping professions are 0x07FE",
              f"{agents.ALL_SECONDARIES:#06x} -- bits 1..10, bit 0 unset "
              f"because id 0 is skipped by the builder")
    refused = []
    for bad in (0, 11, 12, 255):
        try:
            agents.secondary_bits(bad)
        except ValueError:
            refused.append(bad)
    LEDGER.ok(refused == [0, 11, 12, 255],
              "and ids 0, 11, 12 and 255 are all REFUSED",
              f"refused {refused} -- 11 and 12 are past the consumer's own "
              f"`cmp edi, 0xb`, so a mask carrying them is a lie the client "
              f"cannot read; 0 is skipped by the builder")
    LEDGER.ok(agents.agent_set_secondary_bits(7, 0x07FE) == [7, 0x07FE],
              "the payload is [agent_id, mask] and reaches the wire as sent",
              "10 bytes: u16 opcode, u32 agent, u32 mask")

    # ORDER, on the SYNTAX TREE. A grep cannot tell which send comes first,
    # and reversing them costs nothing on the wire and everything in effect.
    with open(authsrv.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    prof_line = sec_line = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "send" and node.args
                and isinstance(node.args[0], ast.Name)):
            name = node.args[0].id
            if name == "GAME_SMSG_AGENT_PROFESSIONS" and prof_line is None:
                prof_line = node.lineno
            if name == "GAME_SMSG_AGENT_PROFESSION_BITS":
                sec_line = node.lineno
    LEDGER.ok(prof_line is not None and sec_line is not None
              and prof_line < sec_line,
              "the burst sends 0x00B7 BEFORE 0x00B6 (syntax tree)",
              f"0x00B7 at line {prof_line}, 0x00B6 at line {sec_line} -- "
              f"reversed, the client logs 'Agent not found in sort array' and "
              f"drops the mask with no wire error and no visible effect")
    LEDGER.ok(authsrv.SECONDARY_BITS == 0,
              "and the default is 0 -- not sent at all",
              f"{authsrv.SECONDARY_BITS} -- ArenaNet's own server sends mask 0 "
              f"in 11 of 11 live samples, so an unlocked-by-default character "
              f"would be us inventing state retail does not send")


def section_party_of_one():
    """The party pair, and the player's own AGENT profession.

    Both are messages the real server sends and ours never did. The party pair
    (0x00B0 size, 0x00B1 leader) writes the per-PLAYER array at ChCliApi
    ctx+0x80C that PLAYER_CREATE already makes; 0x00A6 for the player's own
    agent is the SOLE write path to the agent's profession bytes, which is what
    the party/roster label builder reads -- so the profession ABBREVIATION had
    nothing to draw from and has never appeared in any session.

    The ORDER is the measured part and the reason this has a section: 0x00B0
    fires no event for a fresh entry while 0x00B1 fires only on a LEADER
    CHANGE. Leader-first makes the change a no-op against the default and
    nothing is notified, so the pair must go size-then-leader.
    """
    import ast
    import authsrv

    LEDGER.ok(agents.player_party_size(3, 1) == [3, 1]
              and agents.player_set_party(3, 3) == [3, 3],
              "the party-of-one payloads are [player, 1] and [player, player]",
              "a solo player is their own leader; both fields are the player's "
              "own number, which is what makes the self-link a party")
    refused = None
    try:
        agents.player_party_size(3, 0)
    except ValueError as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None,
              "and a party size of 0 is REFUSED",
              f"{refused!r} -- the local player is always a member of their own "
              f"party, so 0 is not a state the client is ever sent")

    codec = _codec()
    # The dict is keyed by the SYMBOL and read by a LITERAL, which is the shape
    # that makes this the only thing in the file that used to notice 0x00B0 or
    # 0x00B1 moving -- and it noticed by CRASHING (`KeyError: 176`, or the
    # codec's arity guard), so the run died here and the sections after it never
    # executed. section_opcode_pins now names the constant properly; this is
    # kept, because the wire SIZE is a separate claim from the opcode, and the
    # encode is wrapped so a moved constant leaves a red check and a verdict
    # rather than a traceback.
    sizes = {}
    for op, vals in ((authsrv.GAME_SMSG_PLAYER_PARTY_SIZE,
                      agents.player_party_size(1, 1)),
                     (authsrv.GAME_SMSG_PLAYER_SET_PARTY,
                      agents.player_set_party(1, 1))):
        try:
            sizes[op] = len(codec.encode("GAME_SMSG", op, vals))
        except ValueError as ex:                               # pragma: no cover
            sizes[op] = f"REFUSED: {ex}"
    LEDGER.ok(sizes.get(0x00B0) == 5 and sizes.get(0x00B1) == 6,
              "and they encode to the 5 and 6 bytes their handlers read",
              f"{sizes} -- the handlers read fields at +4 and +8; a wrong width "
              f"would desync the next message rather than error")

    # THE ORDER, on the syntax tree. A comment cannot enforce it and a grep
    # cannot tell which send comes first.
    with open(authsrv.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    order = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "send" and node.args
                and isinstance(node.args[0], ast.Name)):
            name = node.args[0].id
            if name in ("GAME_SMSG_PLAYER_INFO", "GAME_SMSG_PLAYER_PARTY_SIZE",
                        "GAME_SMSG_PLAYER_SET_PARTY"):
                order.append((node.lineno, name))
    order.sort()
    names = [n for _, n in order]
    LEDGER.ok(names == ["GAME_SMSG_PLAYER_INFO", "GAME_SMSG_PLAYER_PARTY_SIZE",
                        "GAME_SMSG_PLAYER_SET_PARTY"],
              "PLAYER_CREATE, then SIZE, then LEADER (syntax tree)",
              f"{names} -- leader-first is a no-op against the default, and "
              f"both need the player record PLAYER_CREATE makes")

    # And the player's own agent must get 0x00A6, which is what the roster reads.
    sends = [n.args[0].id for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "send" and n.args
             and isinstance(n.args[0], ast.Name)]
    LEDGER.ok(sends.count("GAME_SMSG_AGENT_SET_PROFESSION") >= 2,
              "and the player's OWN agent gets 0x00A6, not just NPCs",
              f"{sends.count('GAME_SMSG_AGENT_SET_PROFESSION')} send site(s) -- "
              f"0x00A6's setter is the sole write path to the agent's "
              f"profession bytes, which the roster label builder reads")


def _codec():
    import os
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "schema"))
    from codec import Codec
    return Codec()


def section_unlock_bitmap():
    """Bit 0 of the unlock bitmap, which is the whole profession-arc crash.

    OBSERVED (build 38797): 0x00DB's payload becomes a bitmap at
    ctx[0x2c]+0x710, and the skills panel enumerates it with a
    find-next-set-bit iterator that forms `id = (word << 5) + bit` and asserts
    the id NON-ZERO -- `*skill`, ChCliSkill.cpp:1022. So a set bit 0 asserts
    the client the instant the panel opens, at ANY profession: the walk reads
    no profession, and no profession value branches anything on the path.

    OBSERVED (our own vault): 242 of 242 0x00DB sends across every capture we
    have ever taken carry bit 0 -- `db 00 80 00 ff ff ff ff`. Six client
    sessions were spent building and refuting profession stories for it.

    THE NEGATIVE CONTROL IS THE POINT. `range(1, N)` and `range(N)` differ by
    one character, and a test that only reads the current output would pass
    against either if it computed its expectation from the function under test
    -- this file's own combat-constants section exists because twelve of
    fourteen constants could be set wrong with every check green. So the OLD
    version is rebuilt here and required to DIFFER, and the bit count is
    asserted against a literal.
    """
    import authsrv

    words = authsrv.unlock_all_words()
    LEDGER.ok(not (words[0] & 1),
              "bit 0 is CLEAR in the unlock bitmap -- skill id 0 is not a skill",
              "a set bit 0 makes the client's own panel iterator enumerate id "
              "0 and assert *skill (ChCliSkill.cpp:1022) the moment the "
              "Skills panel opens, at every profession")
    n_set = sum(bin(w).count("1") for w in words)
    LEDGER.ok(n_set == 3442,
              "and exactly 3442 ids are unlocked, ids 1..3442",
              f"{n_set} -- literal, not computed from SKILL_TABLE_ROWS, so "
              f"the count cannot move silently with the constant")
    ids = [s for s in range(len(words) * 32)
           if words[s // 32] >> (s % 32) & 1]
    LEDGER.ok(ids[0] == 1 and ids[-1] == authsrv.SKILL_TABLE_ROWS - 1,
              "the lowest unlocked id is 1 and the highest is the last table row",
              f"{ids[0]}..{ids[-1]} against 1..{authsrv.SKILL_TABLE_ROWS - 1}")

    # The old version, rebuilt. It must DIFFER, and differ in exactly bit 0 --
    # a check that merely reproduced the current output would pass against the
    # defect it exists to catch.
    old = [0] * authsrv.UNLOCK_WORDS
    for sid in range(authsrv.SKILL_TABLE_ROWS):
        old[sid // 32] |= 1 << (sid % 32)
    LEDGER.ok(old != words and (old[0] & 1) and old[0] ^ words[0] == 1,
              "NEGATIVE CONTROL: the pre-fix version sets bit 0 and this one "
              "does not, differing in exactly that bit",
              f"old word0 {old[0]:#010x} vs {words[0]:#010x} -- if these ever "
              f"match, the fix has been reverted and every session is back to "
              f"asserting on panel open")

    # The explicit-list arm has ALWAYS skipped id 0; the regression is that
    # the two arms disagreed, so both are checked from here on.
    explicit, _ = authsrv.build_unlock_bitmap("0,1,316")
    LEDGER.ok(not (explicit[0] & 1) and (explicit[0] >> 1 & 1),
              "and the explicit-list arm still drops id 0 while keeping id 1",
              f"word0 {explicit[0]:#010x} -- this arm's `sid <= 0` guard was "
              f"correct all along; only the 'all' arm was wrong")
    _, label = authsrv.build_unlock_bitmap("all")
    LEDGER.ok("3442" in label,
              "and the banner reports 3442, so an operator reading the log "
              "sees the real count",
              f"{label!r} -- it said 3443 while sending a bit that is not a "
              f"skill")

    # THE STARTUP REFUSAL. A regression here costs a launch, a login and a map
    # load to observe, so it must die before the socket opens -- and it must
    # die rather than silently repair, or the next bad producer ships unseen.
    refused = None
    try:
        authsrv.refuse_skill_zero(old, "all")
    except SystemExit as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None and "1022" in refused,
              "a bitmap with bit 0 set is REFUSED at startup, naming the "
              "client assert it would cause",
              f"{refused!r} -- without this the failure surfaces as a client "
              f"crash twelve seconds into a session, which is how it survived "
              f"seven of them")
    # POSITIVE CONTROL: a guard that refuses everything protects nothing,
    # because the server never starts.
    passed = authsrv.refuse_skill_zero(list(words), "all")
    empty = authsrv.refuse_skill_zero([0] * authsrv.UNLOCK_WORDS, "none")
    LEDGER.ok(passed == words and empty[0] == 0,
              "while the real bitmap and an empty one pass untouched",
              "the guard must not clear the bit or reject legitimate input -- "
              "it reports, it does not repair")
    # --unlocks corpus: only ids the client draws an icon for. Needs the
    # owner's client, so it SKIPS rather than failing on a bare machine --
    # and skipping is printed, never silent.
    try:
        corpus, clabel = authsrv.build_unlock_bitmap("corpus")
    except SystemExit as ex:
        corpus, clabel = None, str(ex)
    if corpus is None:
        LEDGER.skip("the --unlocks corpus derivation",
                    f"no client to read: {clabel.splitlines()[0]}")
    else:
        cids = {s for s in range(len(corpus) * 32)
                if corpus[s // 32] >> (s % 32) & 1}
        allids = {s for s in range(len(words) * 32)
                  if words[s // 32] >> (s % 32) & 1}
        LEDGER.ok(not (corpus[0] & 1) and cids < allids,
                  "the corpus set is a STRICT SUBSET of all, and clears bit 0",
                  f"{len(cids)} of {len(allids)} -- it must remove rows, not "
                  f"add them; a derivation that returned everything would "
                  f"reproduce the fileId assert it exists to avoid")
        LEDGER.ok(len(cids) == 1333,
                  "and it is 1333 player-usable skills on build 38797",
                  f"{len(cids)} -- literal, so a change in the extraction rule "
                  f"or the build has to be looked at rather than absorbed")
        bar = set(authsrv.TEST_SKILLBAR)
        LEDGER.ok(bar <= cids,
                  "and every skill on the test bar is inside it",
                  f"missing {sorted(bar - cids)} -- a corpus that dropped a bar "
                  f"skill would leave the bar undrawable, which is the failure "
                  f"--unlocks exists to investigate")
        LEDGER.ok("38797" in clabel and "player-usable" in clabel,
                  "and the label records the build it was derived from",
                  f"{clabel!r} -- the ids are read from the owner's client at "
                  f"run time and committed nowhere, so the log line is the "
                  f"only provenance record the run leaves")

    # THE DEFAULT, on the syntax tree. `all` is measured to crash the client's
    # own Skills panel (fileId, File.cpp:367 -- it unlocks 2,109 rows with no
    # icon), so it must not be what a session gets by not choosing.
    import ast
    default = None
    ARGS_SRC = os.path.join(
        os.path.dirname(os.path.abspath(authsrv.__file__)), "serverargs.py")
    for _p in (authsrv.__file__, ARGS_SRC):
        with open(_p, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "attr", "") == "add_argument"
                    and node.args
                    and getattr(node.args[0], "value", None) == "--unlocks"):
                for kw in node.keywords:
                    if kw.arg == "default":
                        default = kw.value.value
    LEDGER.ok(default == "corpus",
              "--unlocks DEFAULTS to corpus, not all (syntax tree)",
              f"{default!r} -- `all` asserts fileId the moment a player presses "
              f"K, and a default that breaks the game is not a default")

    both_arms = 0
    for spec in ("all", "bar", "none", "316,317"):
        w, _ = authsrv.build_unlock_bitmap(spec)
        both_arms += 0 if (w[0] & 1) else 1
    LEDGER.ok(both_arms == 4,
              "and every --unlocks arm routes through the guard clean",
              f"{both_arms}/4 -- 'all' and the explicit arm are separate code "
              f"paths and only one of them was ever wrong")


def section_spawn_profession():
    """--spawn-profession: the burst's 0x00B7, built through the guard.

    RUNS.md section 8: a mid-session SKILLBAR_UPDATE followed by opening the
    skills panel asserts the client at a LEGAL profession, so the only clean
    delivery of a custom profession is the spawn burst itself. This section
    pins the payload builder, the pairing warning, and -- on the syntax tree --
    that the burst's send site actually calls the builder, because a literal
    list restored there would silently disconnect the flag while every other
    check stayed green.
    """
    import ast
    import authsrv

    LEDGER.ok(authsrv.spawn_profession_values() == [1, 1, 0, 0],
              "the default burst payload is unchanged: profession 1, agent 1",
              f"{authsrv.spawn_profession_values()} -- [agent_id, primary, "
              f"secondary, is_pvp]; the flag must not move the default path")
    LEDGER.ok(authsrv.spawn_profession_values(3) == [1, 3, 0, 0],
              "an in-band override threads through unchanged",
              f"{authsrv.spawn_profession_values(3)}")
    LEDGER.ok(authsrv.spawn_profession_values(12) == [1, 12, 0, 0],
              "and an out-of-band id passes -- custom is DERIVED, not defaulted",
              f"{authsrv.spawn_profession_values(12)} -- the builder computes "
              f"custom from the value, so 12 traverses the guard's u8 ceiling "
              f"rather than bypassing the guard")
    refused = None
    try:
        authsrv.spawn_profession_values(0)
    except ValueError as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None,
              "a primary of 0 is still refused THROUGH the builder",
              f"{refused!r} -- 0 never occurs in the corpus and does not mean "
              f"'none'; a builder that bypassed the guard would send it")

    # The pairing warning, in both directions -- a warning that fires either
    # way is noise (the enemy warning's rule).
    warn = authsrv.spawn_probe_warning("profession_spawn", False)
    LEDGER.ok(warn is not None and "--spawn-profession" in warn,
              "profession_spawn without the flag WARNS",
              f"{warn!r} -- without it the session measures the default "
              f"profession, which run 2 already covered")
    LEDGER.ok(authsrv.spawn_probe_warning("profession_spawn", True) is None
              and authsrv.spawn_probe_warning("profession_ab", False) is None,
              "and the warning is silent when paired, and for other probes",
              "a warning that fires on a correctly-invoked run trains the "
              "operator to ignore it")

    # profession_panel + out-of-band --spawn-profession is REFUSED, not warned:
    # the burst's 0x00B7 kills the client at map load (ConstChar.cpp:1296,
    # measured twice) and the probe's own steps never run.
    lethal = None
    try:
        authsrv.spawn_probe_warning("profession_panel", True, True)
    except SystemExit as ex:
        lethal = str(ex)
    LEDGER.ok(lethal is not None and "1296" in lethal,
              "profession_panel with an out-of-band spawn profession is "
              "REFUSED, naming the on-arrival assert",
              f"{lethal!r} -- that pair spends a whole session re-measuring a "
              f"result we have twice, and answers the probe's question not at all")
    LEDGER.ok(authsrv.spawn_probe_warning("profession_panel", False, False) is None
              and authsrv.spawn_probe_warning("profession_panel", True, False) is None,
              "while profession_panel alone, and with an IN-BAND spawn "
              "profession, are both allowed",
              "an in-band id rides 0x00B7 safely -- the refusal is about the "
              "custom range, not about the flag")

    # THE APPEARANCE NIBBLE, which is DIFFERENT STORAGE from the byte carriers
    # and is bound-checked `< 0xB` at load. It must follow an in-band spawn
    # profession (or the roster and the avatar disagree about who you are, and
    # a reskin experiment becomes uninterpretable) and must NOT follow an
    # out-of-band one (12 rides the byte carriers; the nibble keeps a legal
    # placeholder -- RUNS.md §12 ran a whole session that way).
    LEDGER.ok(authsrv.appearance_for(1) == 1 << 20
              and authsrv.appearance_for(8) == 8 << 20,
              "the appearance nibble FOLLOWS an in-band spawn profession",
              f"prof 8 -> {authsrv.appearance_for(8):#010x}; a Ritualist by byte "
              f"carrier and a Warrior by appearance is two answers to one question")
    LEDGER.ok(authsrv.appearance_for(12) == authsrv.APPEARANCE
              and authsrv.appearance_for(11) == authsrv.APPEARANCE,
              "and REFUSES an out-of-band one, keeping the legal placeholder",
              f"prof 12 -> {authsrv.appearance_for(12):#010x} -- the nibble is 4 "
              f"bits asserted < 0xB at load, so a custom id there is a crash, "
              f"not an experiment")
    LEDGER.ok(authsrv.char_settings_for(8)[8:12] == (8 << 20).to_bytes(4, "little")
              and authsrv.char_settings_for(1) == authsrv.TEST_CHAR_SETTINGS,
              "and the character-select blob carries the SAME value",
              f"{authsrv.char_settings_for(8)[8:12].hex()} -- the roster screen "
              f"reads this blob while the avatar reads 0x0059's dword; they were "
              f"independent constants and disagreed")
    LEDGER.ok(len(authsrv.char_settings_for(8)) == len(authsrv.TEST_CHAR_SETTINGS),
              "without changing the blob's length",
              f"{len(authsrv.char_settings_for(8))} vs "
              f"{len(authsrv.TEST_CHAR_SETTINGS)} -- the field is in place, and a "
              f"length change would desync every field after it")

    # The send site, on the SYNTAX TREE: the call that sends 0x00B7 in the
    # spawn burst must take its values from spawn_profession_values(), not
    # from a literal list. A grep cannot tell a call site from this comment.
    with open(authsrv.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    # EVERY send site, not just the last. This used to REASSIGN `wired` per
    # match, so with two 0x00B7 sites it graded only whichever came last in the
    # file -- a second site could bypass the builder and stay green. 2026-08-16
    # added the hero's own 0x00B7 (agent-keyed, studies/heroes/FINDINGS.md 14.1)
    # and turned that latent hole into a real one, in the safe direction: the
    # new site was last, so it failed loudly instead of hiding. `all()` over a
    # counted list is strictly stronger and still requires at least one site.
    sites = [node for node in ast.walk(tree)
             if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                 and node.func.id == "send" and node.args
                 and isinstance(node.args[0], ast.Name)
                 and node.args[0].id == "GAME_SMSG_AGENT_PROFESSIONS")]
    wired = bool(sites) and all(
        any(isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "spawn_profession_values"
            for inner in ast.walk(node.args[1]))
        for node in sites)
    LEDGER.ok(wired,
              "EVERY 0x00B7 send site calls the builder (syntax tree)",
              "a literal list restored at the send site would disconnect "
              "--spawn-profession while the builder's own checks stay green")


def section_pool_fraction():
    """The 0x00A3 float channel, and the crash that hid behind a `<=`.

    OBSERVED 2026-08-11: the client asserted `fraction <= 1.0f` at
    `CharPool.cpp:84` two seconds after the first kill this server drove all the
    way to a revive. `revive_due` had sent property 34 with `max_health` --
    100.0 -- where the client wanted a FRACTION of a pool. The crash trace
    carries our own message three frames under the assert.

    WHY NOTHING CAUGHT IT, and it is the reason this section is worth its
    checks: the client's bound is `<=`, so it can only fire on a POSITIVE value,
    and every number this server had ever put on that channel was damage --
    `-HIT_FRACTION`, and the -50.0 behind `GV_HEALTH`'s comment. A negative
    passes `fraction <= 1.0f` however absurd it is. Twenty sessions of damage
    testing exercised that bound VACUOUSLY. So the checks below deliberately
    push on the positive side, which is the side no earlier test could reach.

    The last two are the ones that would have caught it: they drive the REAL
    `revive_due` and `hit_enemy` and read the float back off the wire, rather
    than asking `_fraction` about itself. Putting `max_health` back where 1.0
    now sits turns them red.
    """
    import authsrv

    # 1. the exact value that crashed the client, and its neighbours
    for bad in (100.0, 1.5, -1.0001, float("inf")):
        try:
            authsrv._fraction(bad, agents.GV_HEALTH, "test")
            refused = None
        except ValueError as ex:
            refused = str(ex)
        LEDGER.ok(refused is not None and "CharPool" in refused,
                  f"{bad!r} on the float channel is REFUSED, and the refusal "
                  f"names the client assert",
                  refused.split(":")[0] if refused else
                  "ACCEPTED -- this is the shape that took the client down")

    # 2. and the legitimate range still passes, unchanged. A guard that CLAMPED
    #    would also stop the crash and would be worse: it turns a wrong number
    #    into a plausible one and the next caller never learns. So the accepted
    #    values must come back as the same bits _f32 would give.
    for good in (1.0, 0.0, -authsrv.HIT_FRACTION, -1.0):
        LEDGER.ok(authsrv._fraction(good, agents.GV_HEALTH, "t") ==
                  authsrv._f32(good),
                  f"{good!r} passes through with its bits untouched",
                  f"0x{authsrv._f32(good):08X} -- a guard, not a transform")

    # 3. THE CHECK THAT WOULD HAVE CAUGHT IT. Drive the real revive and read the
    #    emitted float back off the wire.
    sent = []
    state = {"agents": {10: {"name": "hatcher", "dead": True, "died_at": 0.0,
                             "health": 0.0, "max_health": 100.0,
                             "last_hit": 0.0}}}
    authsrv.revive_due(lambda op, vals, label="": sent.append((op, vals, label)),
                       state, 1)
    # THE REFILL IS A TICK LATER on this path too (studies/agentprops 1f): the client
    # wants both pools EMPTY at the moment the death bit clears, and 2 of the vault's
    # 49 complaints name an NPC. So the value this section reads off the wire now
    # comes from the deferred half -- which must still be driven, or a revived body
    # stands up empty and this check would pass by measuring nothing.
    early = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(not early,
              "the agent revive does NOT refill in the same burst",
              f"{early} -- the burst is what the client complained about")
    state["agents"][10]["refill_due_at"] = time.time() - 1.0
    authsrv.agent_refill_due(
        lambda op, vals, label="": sent.append((op, vals, label)), state, 1)
    floats = [struct.unpack("<f", struct.pack("<I", v[-1]))[0]
              for op, v, _l in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(bool(floats),
              "a real revive puts a value on the 0x00A3 float channel",
              f"{len(sent)} message(s): "
              f"{[hex(op) for op, _v, _l in sent]}")
    LEDGER.ok(floats and all(-1.0 <= f <= 1.0 for f in floats),
              "and every one of them satisfies the client's own bound",
              f"{floats} -- this read 100.0 until 2026-08-11 and crashed the "
              f"client on CharPool.cpp:84. max_health here is 100.0 on purpose, "
              f"so restoring the old code makes this red rather than merely "
              f"different")

    # 4. the damage side too -- same channel, and the side that was always safe.
    #    Worth a check anyway: it is the one that pinned HIT_FRACTION as a
    #    fraction in the first place, and it now shares the guard.
    sent2 = []
    state2 = {"agents": {10: {"name": "hatcher", "dead": False, "died_at": 0.0,
                              "health": 100.0, "max_health": 100.0,
                              "last_hit": 0.0}}}
    authsrv.hit_enemy(lambda op, vals, label="": sent2.append((op, vals, label)),
                      state2, 10, 1)
    dmg = [struct.unpack("<f", struct.pack("<I", v[-1]))[0]
           for op, v, _l in sent2
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(dmg and all(-1.0 <= f <= 1.0 for f in dmg),
              "and so does the damage a real swing sends",
              f"{dmg} against HIT_FRACTION={authsrv.HIT_FRACTION}")


class _WallMesh:
    """NPCTRACK-Q9's hole in miniature. A wall stands on x = -100 between a
    hostile at the origin and a player at (-400, 0); it is open south of
    y = -150. route() goes round by the corner (0, -200) while the start stands
    north of the opening, and answers the corner on plane 29 when asked with
    with_planes; clip() refuses the straight line through the wall."""

    def __init__(self, listonly=False, raise_=False):
        self.routes = 0
        self.listonly = listonly
        self.raise_ = raise_

    def clip(self, x0, y0, x1, y1, step=16.0):
        if x1 < -100.0 <= x0 and y0 > -150.0:
            return (x0, y0)
        return (x1, y1)

    def walkable(self, x, y):
        return not (x < -100.0 - 1e-9 and y > -150.0 and x > -100.0 - 12.0)   # a 12 u seam west of the wall

    def nearest_walkable(self, x, y, r):
        if self.walkable(x, y):
            return (x, y)
        return (-100.0, y) if r >= 12.0 else None

    def route(self, x0, y0, x1, y1, **kw):
        self.routes += 1
        if self.raise_:
            raise RuntimeError("a mesh gap")
        if not self.walkable(x0, y0):
            return None                                   # route() refuses an off-mesh origin
        if y0 > -150.0 and x1 < -100.0 <= x0:
            path = [(x0, y0), (0.0, -200.0), (x1, y1)]
            planes = [0, 29, 0]
        else:
            path = [(x0, y0), (x1, y1)]
            planes = [0, 0]
        if kw.get("with_planes") and not self.listonly:
            return path, planes
        return path


def _corridor_world(agent_pos, player_pos):
    st = _follow_world(agent_pos, player_pos)
    ag = st["agents"][10]
    ag["follow"] = None          # the follow has not STARTED: the first order is under test
    ag["moving"] = False
    return st


def _corridor_run(state, pm, seconds=4.0, hz=20.0):
    """Drive the follow from a standing start; every send, and the copy's trail."""
    import authsrv
    import math as _m
    ag = state["agents"][10]
    px, py = state["pos"]
    sends, trail, now = [], [], 0.0
    dt = 1.0 / hz

    def _cap(op, vals, label="", quiet=False):
        sends.append((op, vals, label, now))

    while now < seconds:
        now += dt
        ax, ay = ag["pos"]
        authsrv._npc_follow_tick(_cap, state, 1, 10, ag, (px, py),
                                 _m.hypot(px - ax, py - ay), now, pm)
        trail.append(ag["pos"])
    return sends, trail



def section_disc_clip():
    """MOVECODE-1z-co: an in-disc corridor is CLIPPED, not discarded.

    sec.1z-ci made _follow_leg refuse a corridor whose first vertex sits inside the
    player's disc, because the client halts a copy whose target that disc covers
    (F14). The rule is right; its fallback was not -- the caller then sent the
    bare 0x002A, which the client dead-reckons STRAIGHT, and when the corner being
    rounded is itself within the stop radius (a player standing just around the
    flank corner) that straight line goes through the wall. 1z-cn measured 2 of
    the corpus's 6 bad chords as this, one 21.5 u off our mesh.
    """
    import authsrv
    import math as _m
    print("\nMOVECODE-1z-co: the in-disc corridor is clipped to the disc, not thrown away")
    R = authsrv.follow_stop_radius()
    LEDGER.ok(authsrv.NPC_LEG_DISC_CLIP is True
              and "--no-npc-leg-disc-clip" in open(
                  authsrv.__file__, encoding="utf-8").read(),
              "it ships ON with its revert flag",
              "a default with no revert arm is an assertion, not a fix")

    class _AllWalkable:
        def walkable(self, x, y):
            return True

    pm = _AllWalkable()
    P = (1000.0, 1000.0)                      # the player
    # The hostile 300 u out; the corridor's first vertex 30 u from the player,
    # deep inside the 80 u disc -- the geometry 1z-ci refuses.
    A = (1300.0, 1000.0)
    Vx, Vy = 1030.0, 1000.0
    got = authsrv._disc_clip_leg(pm, A[0], A[1], Vx, Vy, P[0], P[1])
    LEDGER.ok(got is not None, "a vertex inside the disc yields a clipped leg, not None",
              f"got {got}")
    if got:
        d = _m.hypot(got[0] - P[0], got[1] - P[1])
        LEDGER.ok(abs(d - (R + authsrv.NPC_LEG_DISC_MARGIN)) < 1e-6,
                  f"and it lands exactly one margin OUTSIDE the disc ({R} + "
                  f"{authsrv.NPC_LEG_DISC_MARGIN} u)",
                  f"{d:.4f} u from the player")
        cross = abs((got[0] - A[0]) * (Vy - A[1]) - (got[1] - A[1]) * (Vx - A[0]))
        LEDGER.ok(cross < 1e-6 and _m.hypot(got[0] - A[0], got[1] - A[1]) > 0.0,
                  "on the corridor's own segment, so the leg still rounds the corner",
                  f"cross {cross:.6f}")
        LEDGER.ok(d < _m.hypot(A[0] - P[0], A[1] - P[1]),
                  "and it is progress: closer to the player than the copy was")
    # THE None BRANCHES, each for its own reason.
    LEDGER.ok(authsrv._disc_clip_leg(pm, 1040.0, 1000.0, Vx, Vy, P[0], P[1]) is None,
              "an origin ALREADY inside the disc sends nothing -- the hostile is at "
              "its stop radius and the agent-addressed follow is the right message")
    near = authsrv._disc_clip_leg(pm, R + authsrv.NPC_LEG_DISC_MARGIN + 1000.0 + 2.0,
                                  1000.0, Vx, Vy, P[0], P[1])
    LEDGER.ok(near is None,
              "a clipped leg shorter than an arrival (NPC_LEG_DONE) is not a leg",
              f"got {near}")

    class _NoneWalkable:
        def walkable(self, x, y):
            return False

    LEDGER.ok(authsrv._disc_clip_leg(_NoneWalkable(), A[0], A[1], Vx, Vy,
                                     P[0], P[1]) is None,
              "and a clipped point our own mesh refuses is never granted")
    # AND THROUGH _follow_leg ITSELF, on a stub route: the clipped leg is sent, and
    # the corridor still OWES the vertex it stopped short of -- one more remaining
    # than the unclipped case. Only the record reads that count, and a later session
    # reads the record to reconstruct the walk.
    class _StubPM:
        """A 3-point corridor whose first vertex sits inside the player's disc."""
        def walkable(self, x, y):
            return True

        def nearest_walkable(self, x, y, r):
            return (x, y, 0.0)

        def route(self, x0, y0, x1, y1, start_plane=None, goal_plane=None,
                  with_planes=False):
            path = [(x0, y0), (Vx, Vy), (x1, y1)]
            return (path, [0, 0, 0]) if with_planes else path

    stub = _StubPM()
    leg_clipped = authsrv._follow_leg(stub, A[0], A[1], P[0], P[1], 0, 0)
    LEDGER.ok(leg_clipped is not None
              and abs(_m.hypot(leg_clipped[0] - P[0], leg_clipped[1] - P[1])
                      - (R + authsrv.NPC_LEG_DISC_MARGIN)) < 1e-6,
              "_follow_leg returns the CLIPPED leg where it used to return None",
              f"got {leg_clipped}")
    LEDGER.ok(leg_clipped is not None and leg_clipped[3] == 2,
              "and reports 2 vertices still owed -- the vertex it stopped short of, "
              "plus the player -- against 1 for an unclipped leg",
              f"more={None if not leg_clipped else leg_clipped[3]}")
    saved_clip = authsrv.NPC_LEG_DISC_CLIP
    try:
        authsrv.NPC_LEG_DISC_CLIP = False
        LEDGER.ok(authsrv._follow_leg(stub, A[0], A[1], P[0], P[1], 0, 0) is None,
                  "REVERT ARM (--no-npc-leg-disc-clip): the corridor is discarded again "
                  "and the caller sends the bare follow through the wall")
    finally:
        authsrv.NPC_LEG_DISC_CLIP = saved_clip

    # THE KNOWN-BAD ARM: with the flag off, _follow_leg must go back to
    # discarding the corridor, which is what sent the straight follow.
    saved = authsrv.NPC_LEG_DISC_CLIP
    try:
        authsrv.NPC_LEG_DISC_CLIP = False
        off = authsrv._disc_clip_leg(pm, A[0], A[1], Vx, Vy, P[0], P[1])
        LEDGER.ok(off is not None,
                  "the helper itself is flag-free; the flag is read at the call site",
                  "keeping the geometry testable independently of the switch")
    finally:
        authsrv.NPC_LEG_DISC_CLIP = saved


def section_corridor_wire():
    """NPCTRACK-Q9: the follow's corridor goes ON THE WIRE.

    The owner's stairs session (GROUNDZ-F12.5): the Hatcher's sync copy and its
    drawn body identical on every sample as it cut through the hole above the
    stairs, 45 u from any trapezoid, parked 8.4 u inside the wall. The client
    walks a hostile's 0x002A dead straight and our wire carried no corridor.
    Retail's does (F16): 0x0029 legs to points while geometry intervenes, the
    0x002A naming the player once the line is clear.
    """
    import authsrv
    import math as _m
    MOVE = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    DEST = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    print("\nNPCTRACK-Q9: the corridor on the wire -- 0x0029 legs round a wall, "
          "0x002A once the line is clear")
    LEDGER.ok(authsrv.NPC_FOLLOW_CORRIDOR is True
              and "--no-npc-corridor" in open(
                  authsrv.__file__, encoding="utf-8").read()
              and authsrv.capture_flags().get("NPC_FOLLOW_CORRIDOR") is True,
              "it ships ON with its revert flag, and the capture records which "
              "arm produced the run",
              "a run whose header cannot name the arm costs a later session a "
              "reconstruction")
    saved = authsrv.NPC_FOLLOW_CORRIDOR
    CORNER = (0.0, -200.0)
    try:
        # THE KNOWN-BAD ARM FIRST: the shape every stairs tape recorded.
        authsrv.NPC_FOLLOW_CORRIDOR = False
        pm = _WallMesh()
        st = _corridor_world((0.0, 0.0), (-400.0, 0.0))
        sends, trail = _corridor_run(st, pm)
        moves = [s for s in sends if s[0] in (MOVE, DEST)]
        LEDGER.ok(moves and moves[0][0] == DEST and moves[0][1][4] == authsrv.PLAYER_AGENT_ID
                  and not any(s[0] == MOVE for s in sends),
                  "REVERT ARM (--no-npc-corridor): the first order names the "
                  "player and no 0x0029 leg is ever sent",
                  f"ops {[hex(s[0]) for s in moves]}")
        LEDGER.ok(min(_m.hypot(p[0] - CORNER[0], p[1] - CORNER[1]) for p in trail) > 100.0
                  and pm.routes == 0,
                  "and the copy walks the straight line, never near the corner, "
                  "having asked the router nothing -- the Hatcher through the hole",
                  f"nearest {min(_m.hypot(p[0] - CORNER[0], p[1] - CORNER[1]) for p in trail):.0f} u, "
                  f"{pm.routes} route call(s)")

        authsrv.NPC_FOLLOW_CORRIDOR = True
        pm = _WallMesh()
        st = _corridor_world((0.0, 0.0), (-400.0, 0.0))
        sends, trail = _corridor_run(st, pm)
        moves = [s for s in sends if s[0] in (MOVE, DEST)]
        first = moves[0] if moves else None
        LEDGER.ok(first is not None and first[0] == MOVE
                  and tuple(first[1][1]) == CORNER,
                  "THE FIX: the first order is a 0x0029 to the corridor's first "
                  "vertex, not the player",
                  f"first {None if first is None else (hex(first[0]), first[1])}")
        LEDGER.ok(first is not None and first[0] == MOVE
                  and first[1][2] == 29 and first[1][3] == 0,
                  "carrying 1z-bz's plane words -- field 3 the plane the corridor "
                  "names for the vertex (29), field 4 the mover's own (0)",
                  f"planes {None if first is None else first[1][2:4]}")
        after = [s for s in moves if s[3] > (first[3] if first else 0.0)]
        nxt = after[0] if after else None
        LEDGER.ok(nxt is not None and nxt[0] == DEST
                  and nxt[1][4] == authsrv.PLAYER_AGENT_ID
                  and 0.6 <= nxt[3] - first[3] <= 1.0,
                  "the copy arrives at the vertex (200 u at 288 u/s = 0.69 s) and "
                  "the NEXT order is the 0x002A naming the player, the line now "
                  "clear -- retail's handover",
                  f"next {None if nxt is None else (hex(nxt[0]), round(nxt[3] - first[3], 2))}")
        LEDGER.ok(min(_m.hypot(p[0] - CORNER[0], p[1] - CORNER[1]) for p in trail) <= 5.0,
                  "and the copy every range check reads went ROUND, through the "
                  "corner",
                  f"nearest {min(_m.hypot(p[0] - CORNER[0], p[1] - CORNER[1]) for p in trail):.1f} u")
        halts = [s for s in sends if "halts at (" in s[2]]
        ag = st["agents"][10]
        LEDGER.ok(halts and _m.hypot(ag["pos"][0] + 400.0, ag["pos"][1]) <= authsrv.follow_stop_radius() + 5.0,
                  "the chase still ARRIVES: a halt at the disc, 80 u from the player",
                  f"halts {len(halts)}, parked {_m.hypot(ag['pos'][0] + 400.0, ag['pos'][1]):.1f} u out")
        LEDGER.ok(pm.routes <= 3,
                  "one route per ORDER (the start, the leg's end), never per tick",
                  f"{pm.routes} route call(s) over 80 ticks")

        # THE SEAM (RUN-1zCG): a copy standing 6 u off the mesh in the seam is
        # stepped onto it before routing; the corridor still goes out.
        pm = _WallMesh()
        st = _corridor_world((-106.0, 0.0), (-400.0, 0.0))
        sends, _ = _corridor_run(st, pm, seconds=1.0)
        moves = [s for s in sends if s[0] in (MOVE, DEST)]
        LEDGER.ok(moves and moves[0][0] == MOVE and tuple(moves[0][1][1]) == CORNER,
                  "an OFF-MESH copy (6 u into a seam, where route() refuses the origin) "
                  "is stepped onto the mesh and still gets its corridor leg -- RUN-1zCG's "
                  "bare follows through the stairs' flank and the hole",
                  f"ops {[hex(s[0]) for s in moves]}")

        # THE PLAYER AT THE CORNER (RUN-1zCG session 2, 82.9 s): a corridor whose
        # first vertex lies inside the player's disc is a bare follow -- the
        # client halts the copy on a target the player's disc covers (F14).
        pm = _WallMesh()
        st = _corridor_world((0.0, 0.0), (-60.0, -200.0))     # the player 60 u from the corner (0, -200)
        sends, _ = _corridor_run(st, pm, seconds=1.0)
        moves = [s for s in sends if s[0] in (MOVE, DEST)]
        LEDGER.ok(moves and moves[0][0] == DEST and not any(s[0] == MOVE for s in sends),
                  "a corridor vertex inside the PLAYER's 80 u disc is not sent: the follow "
                  "names the player instead (the client would halt the copy on the vertex)",
                  f"ops {[hex(s[0]) for s in moves]}")

        # THE OPEN: a start south of the opening has a clear line -- byte for
        # byte the follow RUN-FEEL / RUN-1zCE / RUN-1zCA confirmed.
        pm = _WallMesh()
        st = _corridor_world((0.0, -300.0), (-400.0, 0.0))
        sends, trail = _corridor_run(st, pm, seconds=2.0)
        moves = [s for s in sends if s[0] in (MOVE, DEST)]
        LEDGER.ok(moves and moves[0][0] == DEST and not any(s[0] == MOVE for s in sends),
                  "in the OPEN nothing changes: the first order is the 0x002A "
                  "naming the player and no leg is sent",
                  f"ops {[hex(s[0]) for s in moves]}")

        # FALLBACKS: a route() that raises, and one that answers a bare list.
        pm = _WallMesh(raise_=True)
        st = _corridor_world((0.0, 0.0), (-400.0, 0.0))
        sends, _ = _corridor_run(st, pm, seconds=1.0)
        moves = [s for s in sends if s[0] in (MOVE, DEST)]
        LEDGER.ok(moves and moves[0][0] == DEST,
                  "a route() that raises falls back to the agent-addressed "
                  "follow -- a mesh gap is not a crash",
                  f"ops {[hex(s[0]) for s in moves]}")
        pm = _WallMesh(listonly=True)
        st = _corridor_world((0.0, 0.0), (-400.0, 0.0))
        sends, _ = _corridor_run(st, pm, seconds=1.0)
        moves = [s for s in sends if s[0] in (MOVE, DEST)]
        LEDGER.ok(moves and moves[0][0] == MOVE and tuple(moves[0][1][1]) == CORNER
                  and moves[0][1][2] == 0,
                  "a route() with no plane column still legs to the vertex, "
                  "field 3 falling back to the mover's plane",
                  f"first {None if not moves else (hex(moves[0][0]), moves[0][1])}")
    finally:
        authsrv.NPC_FOLLOW_CORRIDOR = saved


def section_enemy_count():
    """NPCTRACK-Q10 groundwork: --enemies N spawns N hostiles, ids 10..10+N-1,
    one shared definition, distinct walkable spots; N == 1 is byte for byte
    today's spawn."""
    import authsrv
    print("\nNPCTRACK-Q10 groundwork: --enemies N")

    class _Send:
        def __init__(self):
            self.sent = []

        def __call__(self, op, vals, label="", quiet=False):
            self.sent.append((op, list(vals), label))

    class _Mesh:
        """Walkable everywhere but due east of the origin at the offset."""
        def walkable(self, x, y):
            return not (abs(x - (1000.0 + authsrv.ENEMY_OFFSET[0])) < 1.0 and abs(y - 1000.0) < 1.0)

        def planes_at(self, x, y):
            return {0} if self.walkable(x, y) else set()

    saved = authsrv.ENEMY_COUNT
    try:
        authsrv.ENEMY_COUNT = 1
        st = {"pathmap": _Mesh()}
        authsrv.spawn_enemy(_Send(), st, (1000.0, 1000.0, 0), 1)
        ids = sorted(st["agents"])
        LEDGER.ok(ids == [authsrv.ENEMY_AGENT_ID],
                  "N == 1: one hostile, the standing enemy's own id", f"{ids}")
        one = st["agents"][authsrv.ENEMY_AGENT_ID]
        LEDGER.ok(one["pos"] != (1000.0 + authsrv.ENEMY_OFFSET[0], 1000.0),
                  "and its spot skips the one point the mesh refuses (enemy_spot's "
                  "own rule, unchanged)", f"{one['pos']}")

        authsrv.ENEMY_COUNT = 3
        st = {"pathmap": _Mesh()}
        send = _Send()
        authsrv.spawn_enemy(send, st, (1000.0, 1000.0, 0), 1)
        ids = sorted(st["agents"])
        LEDGER.ok(ids == [10, 11, 12],
                  "N == 3: three hostiles under 10, 11, 12 -- the unallocated block "
                  "(probes 2..7, world NPCs 20..22, henchman 30)", f"{ids}")
        spots = [st["agents"][i]["pos"] for i in ids]
        LEDGER.ok(len(set(spots)) == 3 and all(st["pathmap"].walkable(*p) for p in spots),
                  "at three DISTINCT spots the mesh accepts", f"{spots}")
        LEDGER.ok(len({st["agents"][i]["definition"] for i in ids}) == 1
                  and all(st["agents"][i]["allegiance"] == agents.ALLEGIANCE_HOSTILE for i in ids)
                  and all(st["agents"][i]["npc"] is agents.HATCHER for i in ids),
                  "one shared definition (per template, as sculpt_hostile already "
                  "shares with the watcher), every one hostile, every one a hatcher", "")
        creates = [v for op, v, _l in send.sent if op == authsrv.GAME_SMSG_AGENT_CREATE] \
            if hasattr(authsrv, "GAME_SMSG_AGENT_CREATE") else None
        LEDGER.ok(creates is None or len(creates) == 3,
                  "and three bodies went out on the wire",
                  "" if creates is None else f"{len(creates)} create(s)")

        authsrv.ENEMY_COUNT = 2
        st = {}                                    # no navmesh: the plain offsets
        authsrv.spawn_enemy(_Send(), st, (0.0, 0.0, 0), 1)
        LEDGER.ok(sorted(st["agents"]) == [10, 11]
                  and st["agents"][10]["pos"] == (authsrv.ENEMY_OFFSET[0], 0.0)
                  and st["agents"][11]["pos"] == (0.0, authsrv.ENEMY_OFFSET[0]),
                  "without a navmesh the spots are the compass ring at the plain "
                  "offset, east then north", f"{[st['agents'][i]['pos'] for i in (10, 11)]}")
        LEDGER.ok("--enemies" in open(authsrv.__file__, encoding="utf-8").read()
                  and "global ENEMY_COUNT" in open(authsrv.__file__, encoding="utf-8").read()
                  and authsrv.ENEMY_COUNT_MAX == 8,
                  "the flag exists, rebinds through a declared global, and is capped "
                  "at 8 (ids 10..17; 20 is the first world NPC)", "")
    finally:
        authsrv.ENEMY_COUNT = saved


def section_hold_plane():
    """RUN-1zCG (2026-09-07): the plane correction fires from the HOLD branch too.

    The owner: "the Hatcher terrain walks for a second entering the stairs".
    The tape: a copy parked in the CLIENT's frame at the stairs' foot (out of
    reach of the server's player, in reach of the frame -- F8's hold) kept the
    plane 0 it climbed in on for 1.0 s, because Q5's correction ran only in
    the in-reach-of-the-server branch. Same send, same rate floor, this branch.
    """
    import authsrv
    MOVE = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    print("\nRUN-1zCG: the plane correction from the hold branch")
    saved = authsrv.NPC_CLIENT_MODEL
    authsrv.NPC_CLIENT_MODEL = True
    try:
        st = _parked(29, 0, player=(760.0, 0.0), pos=(520.0, 0.0))   # 240 u: out of the server's reach
        st["last_report"] = (560.0, 0.0, True)                        # the frame 40 u ahead: in reach, in the cone
        st["click_moving_at"] = None
        sent = _tick_parked(st, pm=_Stairs() if "_Stairs" in globals() else None)
        corr = [v for op, v, lab in sent if op == MOVE and "PLANE CORRECT" in lab]
        LEDGER.ok(len(corr) == 1 and corr[0][2] == 29 and corr[0][3] == 29
                  and not any(op == authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION for op, _v, _l in sent),
                  "HELD in the client's frame with a stale word: ONE zero-distance 0x0029 "
                  "carrying the copy's own plane 29, and no follow opens (the hold holds)",
                  f"sends {[(hex(op), v[2:4]) for op, v, _l in sent]}")
        st = _parked(29, 29, player=(760.0, 0.0), pos=(520.0, 0.0))
        st["last_report"] = (560.0, 0.0, True)
        st["click_moving_at"] = None
        sent = _tick_parked(st, pm=None)
        LEDGER.ok(not any(op == MOVE for op, _v, _l in sent),
                  "and a word already right sends nothing from the hold",
                  f"sends {[hex(op) for op, _v, _l in sent]}")
    finally:
        authsrv.NPC_CLIENT_MODEL = saved

    # ---- SLICE-B7b: the PARTY body follows ------------------------------------
    #
    # Every check here is paired with the arm that makes it mean something. A
    # party body walking proves nothing on its own -- it has to walk WHERE a
    # hostile would not, and stand still when the flag is off, or the section is
    # just watching `_npc_follow_tick` work, which four sections above already do.
    print("\nSLICE-B7b / SLICE-H2: a party body walks to its SLOT beside the "
          "leader by 0x0029 point leads (F28), with --party-follow-agent, "
          "--no-hero-follow and a hostile at the same distance as its arms")
    FOLLOW = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    LEAD = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    SPEED = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED
    _saved_hf = authsrv.HERO_FOLLOW
    _saved_sl = authsrv.PARTY_SLOT_LEADS
    try:
        def _party(pos, **over):
            """`_world`'s hostile turned into a hero body at `pos`: the
            allegiance, `attacks_back` and the slot the creation site sets."""
            st = _world(dist=0.0)
            st["agents"][10].update(allegiance=agents.ALLEGIANCE_PLAYER,
                                    attacks_back=False, skills=(),
                                    skill_ready=[], pos=pos, party_slot=0)
            st.update(over)
            return st

        past = authsrv.AGGRO_RANGE + 500.0

        # SLICE-H2: the slot. Retail's standing party bodies sit ABEAM of the
        # leader (along 0, |across| 99 u p50 -- henchjoin.py, F28); slot 0
        # is 110 u to the leader's left, and the spawn faces +x.
        slot0 = authsrv.party_slot_point({"pos": (0.0, 0.0)}, 0)
        LEDGER.ok(slot0 == (0.0, 110.0),
                  "slot 0 stands 110 u to the leader's LEFT of a +x heading "
                  "(F28: standing bodies sit abeam, |across| 99 u p50)",
                  f"slot0 {slot0}")
        turned = authsrv.party_slot_point({"pos": (0.0, 0.0),
                                           "heading": (0.0, 1.0)}, 0)
        LEDGER.ok(turned == (-110.0, 0.0),
                  "and the slot turns with the leader's heading: facing +y, "
                  "the left is -x", f"turned {turned}")
        held = {"pos": (0.0, 0.0), "heading": (0.0, 1.0)}
        authsrv.party_slot_point(held, 0)
        held["heading"] = None                    # the stop clears the heading
        kept = authsrv.party_slot_point(held, 0)
        LEDGER.ok(kept == (-110.0, 0.0),
                  "a stop clears state['heading'] and the slot KEEPS the last "
                  "moving heading -- else every pause would walk the party "
                  "round to the spawn's facing", f"kept {kept}")

        sent = _walk(_party((0.0, -300.0)))        # 410 u from its slot
        ops = [op for op, _v, _l in sent]
        end = tuple(sent[1][1][1]) if len(sent) > 1 else None
        LEDGER.ok(ops == [SPEED, LEAD] and end == slot0,
                  "a party body away from its slot announces a rate and ONE "
                  "0x0029 POINT lead whose end IS the slot -- retail's shape "
                  "(F28: 750 of 750 leads while the leader moved were 0x0029, "
                  "never a 0x002A naming the leader)",
                  f"{[hex(o) for o in ops]} end {end}")

        ops = [op for op, _v, _l in _walk(_party((0.0, 100.0)))]   # 10 u off
        LEDGER.ok(ops == [],
                  f"and within {authsrv.PARTY_SLOT_STOP:.0f} u of the slot it "
                  "stands, so the slot is a real bound and not decoration",
                  f"{[hex(o) for o in ops]}")

        # ARM 0: --party-follow-agent, the SLICE-B7b shape -- a 0x002A naming
        # the player, parked at HERO_FOLLOW_STOP. The known-bad arm for the
        # formation: retail sent no such follow for a party body.
        authsrv.PARTY_SLOT_LEADS = False
        out = authsrv.HERO_FOLLOW_STOP + 160.0
        ops = [op for op, _v, _l in _walk(_party((out, 0.0)))]
        near = [op for op, _v, _l in _walk(_party((authsrv.HERO_FOLLOW_STOP
                                                     - 40.0, 0.0)))]
        LEDGER.ok(ops == [SPEED, FOLLOW] and near == [],
                  "--party-follow-agent: outside HERO_FOLLOW_STOP a rate and "
                  "ONE 0x002A follow naming the player, inside it nothing -- "
                  "the B7b shape, kept as the revert arm",
                  f"out {[hex(o) for o in ops]}, near {[hex(o) for o in near]}")
        authsrv.PARTY_SLOT_LEADS = True

        # ARM 1: the flag. Without this the section cannot tell "the follow moved
        # it" from "something else in the tick moved it".
        authsrv.HERO_FOLLOW = False
        ops = [op for op, _v, _l in _walk(_party((0.0, -300.0)))]
        LEDGER.ok(ops == [],
                  "--no-hero-follow: the body stands where it spawned, which is "
                  "every hero run before 2026-09-12 (the known-bad arm)",
                  f"{[hex(o) for o in ops]}")
        authsrv.HERO_FOLLOW = True

        # ARM 2: the leash, which is the one number an ally really changes. The
        # comparison is against a HOSTILE at the same distance, not against a
        # remembered figure -- two measurements, never a literal.
        ally_far = [op for op, _v, _l in _walk(_party((past, 0.0)))]
        host_far = [op for op, _v, _l in _walk(_world(dist=past))]
        LEDGER.ok(ally_far == [SPEED, LEAD] and host_far == [],
                  f"at {past:.0f} u -- past the {authsrv.AGGRO_RANGE:.0f} u "
                  "hostile leash -- the ALLY still walks and the HOSTILE has "
                  "given up. Same tick, same distance, opposite answers",
                  f"ally {[hex(o) for o in ally_far]}, "
                  f"hostile {[hex(o) for o in host_far]}")
    finally:
        authsrv.HERO_FOLLOW = _saved_hf
        authsrv.PARTY_SLOT_LEADS = _saved_sl

    # ---- SLICE-H2: the party as CONTENT ---------------------------------------
    # `--party KEY` is translated into the --hero* flags at the top of main(),
    # BEFORE the hero block reads them -- the order is the whole mechanism, and
    # only the text can lock it (main() binds sockets). The row itself is
    # validated the way main() validates it: the body row exists, the hero
    # index passes the client's own bounds (party_hero_add / mercenary_info).
    print("\nSLICE-H2: [party.slice] loads, its body row exists, its hero index "
          "passes the client's bounds, and --party is applied before --hero")
    _prow = agents.WORLD.get("party", "slice")
    _pbody = agents.npc_template(_prow["body"])
    LEDGER.ok(int(_prow["hero"]) in range(1, 40) and "file_id" in _pbody
              and list(_prow["skills"]),
              "[party.slice]: hero index in 1..39, a body row with a file_id "
              "(the commander's appearance pair, pvpui 28.13), a non-empty bar",
              f"hero {_prow['hero']}, body {_prow['body']} file {_pbody['file_id']}"
              f"/{_pbody.get('model_id')}, bar {list(_prow['skills'])}")
    try:
        agents.party_hero_add(1, 1, authsrv.HERO_AGENT_ID, int(_prow["hero"]))
        agents.mercenary_info(int(_prow["hero"]))
        _ok = True
    except Exception as exc:              # the same refusal main() would raise
        _ok = f"{type(exc).__name__}: {exc}"
    LEDGER.ok(_ok is True, "and the row's hero index builds 0x01C2 and 0x0074 "
              "(the validations main() runs at startup)", f"{_ok}")
    _src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    LEDGER.ok(_src.count("    if a.party:\n") == 1
              and _src.index("    if a.party:\n")
              < _src.index("    if a.hero is not None:\n")
              and _src.index("    if a.party:\n") < _src.index("    if a.hero_skills:\n")
              and "a.hero_pipeline_first = True" in _src,
              "--party is applied BEFORE the --hero block and the --hero-skills "
              "block read `a`, and it turns the commander rig on (pipeline-first, "
              "heroes 38)", "order in main()")

    # SLICE-H2b: the hero's BODY is a field thing. The owner, on the H2 run:
    # "in the outpost her model should be hidden. only show in explorable
    # areas." Map 148 is the slice's outpost, 168 its corridor (maps.toml).
    print("\nSLICE-H2b: the party's world bodies are withheld in a town, sent in "
          "a field, and --party-body-in-outpost is the revert arm")
    _saved_bio = authsrv.PARTY_BODY_IN_OUTPOST
    try:
        authsrv.PARTY_BODY_IN_OUTPOST = False
        town = authsrv.party_bodies_here({"map_id": 148})
        field = authsrv.party_bodies_here({"map_id": 168})
        LEDGER.ok(town is False and field is True,
                  "map 148 (an outpost) gets no party body; map 168 (the "
                  "corridor, explorable) does -- content/maps.toml's own flag",
                  f"town {town}, field {field}")
        authsrv.PARTY_BODY_IN_OUTPOST = True
        LEDGER.ok(authsrv.party_bodies_here({"map_id": 148}) is True,
                  "--party-body-in-outpost: the body stands in the town too -- "
                  "every hero rig before SLICE-H2b, the known-bad arm",
                  "revert arm")
    finally:
        authsrv.PARTY_BODY_IN_OUTPOST = _saved_bio
    LEDGER.ok(_src.count("party_bodies_here(state)") == 6     # the def + 4 sites + zone_carry_apply (JARIN)
              and _src.count("if HERO_BODY and party_bodies_here(state) else ()") == 1
              and "HENCHMAN_BODY and party_bodies_here(state)" in _src,
              "both party body sites in the load path -- the hero loop and the "
              "henchman's -- are gated on party_bodies_here; the roster/"
              "activation/level/vitals sends are not (the panel opens bodiless, "
              "pvpui 28.3)", f"{_src.count('party_bodies_here(state)')} sites")
    # SLICE-H2c: the bodiless row's profession. 0x00A6's handler writes the
    # per-agent summary record when the agent has no view (0x7dffc0's
    # no-body arm -> 0x7f73a0), which is the record the roster label reads
    # bodiless -- so a town sends the pair for the hero agent, BEFORE its
    # level (retail: 0x00A6 -> 0x009F, 130 of 130).
    _pro = _src.index("AGENT_SET_PROFESSION(hero agent")
    LEDGER.ok(_src.count("AGENT_SET_PROFESSION(hero agent") == 1
              and _src.index("if HERO_BODY and not party_bodies_here(state)",
                             _pro - 800) < _pro
              and _pro < _src.index("level {HERO_LEVEL} on hero agent"),
              "a town sends 0x00A6 for the bodiless hero agent, gated on "
              "party_bodies_here being False, ahead of its prop-36 level "
              "(the pair's retail order)", "site order in the load path")

    # ---- SLICE-H3: hostiles fight the party -----------------------------------
    # F29: retail's hostiles named a henchman 162 times to the observer's 13;
    # their pick was the lowest base-armour class alive (51 of 58 opening
    # starts), the nearest within it (41). Every check below has the arm that
    # makes it mean something: the Warrior nearer than the Monk, a same-class
    # pair, the pick's owner dying, and the --hostile-target-player revert.
    print("\nSLICE-H3: a hostile picks the softest party body alive in range and "
          "the nearest within the class, keeps it while it lives; the chase names "
          "it, the swing lands on it, it dies and waits for a signet; the hero "
          "raises it, and the player")
    FLOAT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
    INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
    STATUS = authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
    FOLLOW = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    PLAYER = authsrv.PLAYER_AGENT_ID
    _saved_htp = authsrv.HOSTILE_TARGETS_PARTY
    try:
        def _body(name, pos, prof, slot):
            return {"name": name, "dead": False, "died_at": 0.0, "health": 100.0,
                    "max_health": 100.0, "last_hit": 0.0, "pos": pos, "plane": 0,
                    "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0,
                    "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
                    "attacks_back": False, "skills": (), "skill_ready": [],
                    "npc": {"profession": prof, "level": 5}, "party_slot": slot}

        def _party_world(hostile_pos, monk_pos, warrior_pos=None):
            st = _world(dist=0.0)
            # an EMPTY bar: a ready skill goes first and would cast at the body
            # instead of swinging, which is the cast path's business (below)
            st["agents"][10].update(pos=hostile_pos, skills=(), skill_ready=[])
            st["agents"][30] = _body("monk", monk_pos, 3, 0)
            if warrior_pos is not None:
                st["agents"][31] = _body("warrior", warrior_pos, 1, 1)
            return st

        now = time.time()
        # 1. the class first: the player (a Warrior, AR 80) stands 200 u off,
        # the Monk body (AR 60) 500 u off -- the Monk is picked.
        st = _party_world((200.0, 0.0), (-300.0, 0.0))
        tid = authsrv.hostile_target(st, 10, st["agents"][10], now)
        LEDGER.ok(tid == 30,
                  "the softest class first: the Monk body 500 u off over the "
                  "Warrior player 200 u off (retail: the Monk at 380-500 u over "
                  "nearer warriors, F29)", f"target {tid}")
        # 2. within a class, the nearest: a Warrior body 50 u off over the
        # Warrior player 200 u off, the Monk out of aggro range.
        st2 = _party_world((200.0, 0.0), (-3000.0, 0.0), warrior_pos=(250.0, 0.0))
        tid2 = authsrv.hostile_target(st2, 10, st2["agents"][10], now)
        LEDGER.ok(tid2 == 31,
                  "and within a class the nearest: the Warrior body 50 u off "
                  "over the Warrior player 200 u off; a Monk 3200 u off is "
                  "past AGGRO_RANGE and not a candidate", f"target {tid2}")
        # 3. the pick is PROVISIONAL until the bout opens (retail's rule is
        # read off opening starts), LOCKED from the first start while the
        # target lives, and re-made when it dies.
        st2["agents"][30]["pos"] = (-300.0, 0.0)     # the Monk walks into range
        moved = authsrv.hostile_target(st2, 10, st2["agents"][10], now)
        LEDGER.ok(moved == 30,
                  "an UNLOCKED pick moves to a softer body that walks into range "
                  "-- harness 20260913T102921: a raider that noticed the player "
                  "600 u out kept them though the Monk arrived a moment later",
                  f"target {moved}")
        st["agents"][10]["target_locked"] = True      # the first swing opened
        st["pos"] = (210.0, 0.0)                     # the player now 10 u off
        st["agents"][30]["pos"] = (-900.0, 0.0)      # the Monk 1100 u off
        kept = authsrv.hostile_target(st, 10, st["agents"][10], now)
        st["agents"][30]["dead"] = True
        after = authsrv.hostile_target(st, 10, st["agents"][10], now)
        LEDGER.ok(kept == 30 and after == PLAYER
                  and not st["agents"][10].get("target_locked"),
                  "a LOCKED pick is kept while it lives (the player at 10 u does "
                  "not steal it), re-made at its death, and the lock drops",
                  f"kept {kept}, after the death {after}")
        # 4. the chase names the party body in the 0x002A's target field.
        st = _party_world((200.0, 0.0), (-300.0, 0.0))
        sent = _walk(st)
        fol = [v for op, v, _l in sent if op == FOLLOW]
        LEDGER.ok(len(fol) == 1 and fol[0][-1] == 30
                  and tuple(fol[0][1]) == (-300.0, 0.0),
                  "the chase is a 0x002A naming the MONK BODY at its position, "
                  "not the player", f"follows {fol}")
        # 5. the swing opens on the body and lands on it: [4, hostile, body, 0],
        # then [1, hostile, 0] and property 16 [16, body, hostile, fraction].
        st = _party_world((200.0, 0.0), (285.0, 0.0))       # the Monk 85 u off
        authsrv.hostile_target(st, 10, st["agents"][10], now)
        sent = _swings(st)
        started = [v for op, v, _l in sent if op == INT_T and v[0] == 4]
        LEDGER.ok(started == [[4, 10, 30, 0]] and st["agents"][10].get("target_locked"),
                  "the swing OPENS on the party body: attack_started names it "
                  "as the target, and the bout LOCKS the pick", f"starts {started}")
        st["agents"][10]["swing_lands_at"] = time.time() - 0.01
        sent = _swings(st)
        dmg = [v for op, v, _l in sent if op == FLOAT_T and v[0] == 16]
        LEDGER.ok(len(dmg) == 1 and dmg[0][1] == 30 and dmg[0][2] == 10
                  and st["agents"][30]["health"] < 100.0,
                  "and LANDS on it: property 16 [16, BODY, hostile, fraction] "
                  "and the body's health drops", f"damage {dmg}, health "
                  f"{st['agents'][30]['health']:.1f}")
        # 6. the body dies through kill_agent with NO kill reward, and
        # revive_due does not stand it up on the hostile's timer.
        st["agents"][30]["health"] = 0.5
        st["agents"][10]["swing_lands_at"] = time.time() - 0.01
        sent = _swings(st)
        died = [v for op, v, _l in sent if op == STATUS and v[0] == 30]
        rewards = [op for op, _v, _l in sent
                   if op == authsrv.GAME_SMSG_AGENT_KILL_REWARD]
        LEDGER.ok(st["agents"][30]["dead"] and died == [[30, agents.EFFECT_DEAD]]
                  and rewards == [],
                  "a killing swing puts the body DOWN (status dead bit) and pays "
                  "NO kill reward -- nobody is paid for a party death",
                  f"dead {st['agents'][30]['dead']}, status {died}, rewards {rewards}")
        st["agents"][30]["died_at"] = time.time() - 1000.0
        sent = []
        authsrv.revive_due(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                           st, 1)
        LEDGER.ok(st["agents"][30]["dead"] and sent == [],
                  "and revive_due leaves a party body DEAD however long it lies "
                  "there -- retail's henchman was raised by a signet five times, "
                  "never by a timer (F28)", f"dead {st['agents'][30]['dead']}, "
                  f"sent {sent}")
        # 7. the hero raises it: a dead ally and a ready Resurrection Signet on
        # the bar is the cast, ahead of any heal; 3 s later the body stands.
        hero = _body("hero", (0.0, 110.0), 3, 0)
        hero.update(skills=((281, 1.0, 2.0), (276, 0.75, 2.0), (2, 3.0, 0.0)),
                    skill_ready=[0.0, 0.0, 0.0])
        st["agents"][200] = hero
        st["player_health"] = 50.0                   # a hurt player, too
        sent = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        casts = [v for op, v in sent if op == INT_T and v[0] == 60]
        LEDGER.ok(casts == [[60, 200, 30, 2]] and hero.get("cast_target") == 30
                  and hero.get("casting") == 2,
                  "the hero casts Resurrection Signet (2) at the DEAD body ahead "
                  "of Orison at the hurt player -- the dead first",
                  f"casts {casts}, target {hero.get('cast_target')}")
        hero["cast_lands_at"] = time.time() - 0.01
        sent = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        up = [v for op, v in sent if op == STATUS and v[0] == 30]
        LEDGER.ok(up == [[30, 0]] and not st["agents"][30]["dead"]
                  and st["agents"][30]["health"] == 100.0,
                  "and when it lands the body STANDS: status [body, 0], full "
                  "health (retail: [60] -> 3.0 s -> [id, 0], F28)",
                  f"status {up}, dead {st['agents'][30]['dead']}, "
                  f"health {st['agents'][30]['health']}")
        # 7b. nobody dead: the signet slot is HELD, round robin steps past it.
        hero["skill_ready"] = [0.0, 0.0, 0.0]
        hero["last_slot"] = 1                        # next in the round is the signet
        hero["cast_lands_at"] = None
        hero["casting"] = None
        sent = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        casts = [v for op, v in sent if op == INT_T and v[0] == 60]
        LEDGER.ok(casts and casts[0][3] != 2,
                  "with nobody dead the signet slot is held: the round robin "
                  "steps past it to a heal", f"casts {casts}")
        # 8. the dead PLAYER is raised by the hero's signet through the revive
        # path, without waiting for the timer.
        hero["skill_ready"] = [0.0, 0.0, 0.0]
        hero["cast_lands_at"] = None
        hero["casting"] = None
        st["player_dead"], st["player_died_at"] = True, time.time()
        sent = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        casts = [v for op, v in sent if op == INT_T and v[0] == 60]
        hero["cast_lands_at"] = time.time() - 0.01
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        up = [v for op, v in sent if op == STATUS and v[0] == PLAYER]
        LEDGER.ok(casts == [[60, 200, PLAYER, 2]] and up == [[PLAYER, 0]]
                  and not st["player_dead"],
                  "the dead PLAYER is raised the same way: the signet at the "
                  "player, then the revive path stands them up at once (retail "
                  "raised the observer twice, F28)",
                  f"casts {casts}, status {up}, dead {st['player_dead']}")
        # 9. the revert arm: --hostile-target-player, every run before H3.
        authsrv.HOSTILE_TARGETS_PARTY = False
        st = _party_world((85.0, 0.0), (85.0, 40.0))        # both in reach
        st["agents"][10]["target"] = 30                       # a stale pick
        sent = _swings(st)
        started = [v for op, v, _l in sent if op == INT_T and v[0] == 4]
        LEDGER.ok(started == [[4, 10, PLAYER, 0]],
                  "--hostile-target-player: the swing opens on the PLAYER whatever "
                  "the party looks like -- the known-bad arm",
                  f"starts {started}")
    finally:
        authsrv.HOSTILE_TARGETS_PARTY = _saved_htp

    # ---- SLICE-H4: the party fights ---------------------------------------------
    # F30: 77 of 89 retail party opening starts followed the leader's own start
    # or press on the target inside 6 s (80 of 89 on the leader's selected
    # target); the Monk swung from 378 u p50, the Warrior chased by a 0x002A
    # naming its foe; a plain swing landed 0.038 of the target's maximum
    # (level-20 Monk); the bout ended in the target's death 60 of 89.
    print("\nSLICE-H4: a party body fights the leader's target when the leader "
          "starts or presses, a caster from range and a melee body by a chase; "
          "its swing lands PARTY_HIT_FRACTION at the foe's armour, its kill pays "
          "the reward, a foe skill goes at the foe, and the fight ends at the "
          "foe's death")
    _saved_pf = authsrv.PARTY_FIGHTS
    try:
        def _pbody(name, pos, prof, slot=0, **over):
            row = {"name": name, "dead": False, "died_at": 0.0, "health": 100.0,
                   "max_health": 100.0, "last_hit": 0.0, "pos": pos, "plane": 0,
                   "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0,
                   "attack_speed": authsrv.party_attack_speed({"profession": prof}),
                   "attacks_back": False, "skills": (), "skill_ready": [],
                   "npc": {"profession": prof, "level": 5}, "party_slot": slot}
            row.update(over)
            return row

        def _fight_world(hostile_pos, monk_pos, **hostile_over):
            st = _world(dist=0.0)
            st["agents"][10].update(pos=hostile_pos, skills=(), skill_ready=[],
                                    max_health=200.0, health=200.0,
                                    npc={"profession": 1, "level": 5},
                                    **hostile_over)
            st["agents"][200] = _pbody("monk", monk_pos, 3)
            st["player_dead"] = False
            return st

        def _attacks(state, n=1):
            sent = []
            for _ in range(n):
                authsrv.ally_attack_tick(
                    lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
                    state, 1)
            return sent

        now = time.time()
        # 1. nobody engaged: the body stands down -- no target, no swing.
        # (SLICE-H5: under Fight a foe inside the hero's AGGRO_RANGE is
        # attacked on sight, WIKI -- so this idle foe stands 1500 u off.)
        st = _fight_world((1500.0, 0.0), (0.0, 110.0))
        t0 = authsrv.party_fight_target(st, 200, st["agents"][200], now)
        sent = _attacks(st)
        LEDGER.ok(t0 is None and sent == [],
                  "with no leader engagement, no hostile on the party and no "
                  "foe in the hero's aggro range, a party body fights NOBODY "
                  "(F30's 12 unexplained retail opens are not modelled)",
                  f"target {t0}, sent {sent}")
        # 2. the leader's swing stamps the engagement; the caster opens on the
        # leader's target from its slot: [4, 200, 10, 0], facing first.
        st = _fight_world((300.0, 0.0), (0.0, 110.0))
        authsrv.leader_engaged(st, 10, now, "swing")
        t1 = authsrv.party_fight_target(st, 200, st["agents"][200], now)
        sent = _attacks(st)
        started = [v for op, v, _l in sent if op == INT_T and v[0] == 4]
        ops = [op for op, _v, _l in sent]
        LEDGER.ok(t1 == 10 and started == [[4, 200, 10, 0]]
                  and ops.index(authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION)
                  < ops.index(INT_T),
                  "the leader's start engages the party on its target: the Monk "
                  "opens [4, body, foe, 0] from 320 u (retail: 77 of 89 followed "
                  "the leader inside 6 s, the Monk from 378 u p50), turning first",
                  f"target {t1}, starts {started}, ops {[hex(o) for o in ops]}")
        # 3. the landing: [1, body, 0] then [16, foe, body, frac]; the foe's
        # health drops by PARTY_HIT_FRACTION at its armour; no last_hit on it.
        st["agents"][200]["swing_lands_at"] = time.time() - 0.01
        sent = _attacks(st)
        ops = [op for op, _v, _l in sent]
        fin = [v for op, v, _l in sent if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
               and v[0] == agents.GV_MELEE_ATTACK_FINISHED]
        dmg = [v for op, v, _l in sent if op == FLOAT_T and v[0] == 16]
        _hp = st["agents"][10]["health"]
        # the foe's own armour: a level-5 Warrior creature, 3*5+20 = 35
        _want = 200.0 * authsrv.PARTY_HIT_FRACTION * authsrv.armour_multiplier(35.0)
        LEDGER.ok(fin == [[1, 200, 0]] and len(dmg) == 1 and dmg[0][1] == 10
                  and dmg[0][2] == 200 and abs((200.0 - _hp) - _want) < 1e-6
                  and st["agents"][10]["last_hit"] == 0.0,
                  "and it LANDS in retail's other-agent order -- finished, then "
                  "[16, FOE, body, fraction] -- for PARTY_HIT_FRACTION of the "
                  "foe's maximum at its armour, without touching the foe's "
                  "`last_hit` (the player's own swing timer)",
                  f"finished {fin}, damage {dmg}, health {_hp:.1f} (want "
                  f"{_want:.1f} off at AR 35)")
        # 4. a killing swing pays the REWARD -- the party's kill is the party's.
        st["agents"][10]["health"] = 0.5
        st["agents"][200]["last_swing"] = 0.0
        st["agents"][200]["swing_lands_at"] = time.time() - 0.01
        sent = _attacks(st)
        ops = [op for op, _v, _l in sent]
        LEDGER.ok(st["agents"][10]["dead"]
                  and authsrv.GAME_SMSG_AGENT_KILL_REWARD in ops
                  and [v for op, v, _l in sent if op == STATUS] == [[10, agents.EFFECT_DEAD]],
                  "a killing swing by the party puts the foe down WITH the kill "
                  "reward (status, reward, flags) -- a hostile's swing on a party "
                  "body pays nobody (H3), the party's on a hostile pays the player",
                  f"dead {st['agents'][10]['dead']}, ops {[hex(o) for o in ops]}")
        # 5. the foe's death ends the fight: the body stands down.
        t5 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        sent = _attacks(st)
        LEDGER.ok(t5 is None and sent == [] and st["agents"][200].get("fight") is None,
                  "the foe's death ends the bout (retail: 60 of 89 bouts ended in "
                  "the target's death) -- no target, no swing",
                  f"target {t5}, sent {sent}")
        # 6. out of casting range: engaged, but no swing from 1500 u.
        st = _fight_world((1500.0, 0.0), (0.0, 0.0))
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        sent = _attacks(st)
        LEDGER.ok(st["agents"][200].get("fight") == 10
                  and [v for op, v, _l in sent if op == INT_T] == [],
                  "a caster 1500 u from its foe is ENGAGED but does not swing: "
                  "PARTY_RANGED_REACH is casting range, 1248 u (WIKI, GWW "
                  "\"Range\": also the range of all caster weapons)",
                  f"fight {st['agents'][200].get('fight')}, sent {sent}")
        # 7. the engagement expires: 7 s after the leader's last start, with
        # the foe not fighting the party and never the body's own foe, the
        # body stands down; but a body ALREADY on that foe keeps it.
        st = _fight_world((1500.0, 0.0), (0.0, 110.0))
        authsrv.leader_engaged(st, 10, time.time() - 7.0, "swing")
        t7 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        st2 = _fight_world((1500.0, 0.0), (0.0, 110.0))
        authsrv.leader_engaged(st2, 10, time.time(), "swing")
        authsrv.party_fight_target(st2, 200, st2["agents"][200], time.time())
        st2["leader_engaged"]["at"] = time.time() - 7.0
        t7b = authsrv.party_fight_target(st2, 200, st2["agents"][200], time.time())
        LEDGER.ok(t7 is None and t7b == 10,
                  "the leader's engagement is a 6 s window for OPENING a bout; "
                  "a body already on that foe keeps it while it lives and the "
                  "leader's last engagement is still on it",
                  f"fresh body {t7}, engaged body {t7b}")
        # 8. a hostile that opened on the party engages the body without the
        # leader (retail: 5 of 89): its H3 pick locked on a party member.
        st = _fight_world((1500.0, 0.0), (0.0, 110.0))
        st["agents"][10]["target"], st["agents"][10]["target_locked"] = 200, True
        t8 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        st["agents"][10]["target_locked"] = False
        st["agents"][200]["fight"] = None
        t8b = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        LEDGER.ok(t8 == 10 and t8b is None,
                  "a hostile whose pick is LOCKED on a party member engages the "
                  "body with no leader start (retail: 5 of 89 followed a "
                  "hostile's start on the party); a provisional pick does not",
                  f"locked {t8}, provisional {t8b}")
        # 9. a MELEE body chases: the move tick issues a 0x002A naming the foe
        # (not a slot lead), no swing mid-follow; parked in reach, it swings.
        st = _fight_world((500.0, 0.0), (0.0, 110.0))
        st["agents"][200]["npc"]["profession"] = 1
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        sent = _walk(st)
        fol = [v for op, v, _l in sent if op == FOLLOW and v[0] == 200]
        leads = [v for op, v, _l in sent
                 if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT and v[0] == 200]
        mid = _attacks(st)
        LEDGER.ok(len(fol) == 1 and fol[0][0] == 200 and fol[0][-1] == 10
                  and leads == [] and [v for op, v, _l in mid if op == INT_T] == [],
                  "a MELEE party body (Warrior) chases its foe by a 0x002A naming "
                  "it, not a slot lead (retail's Warrior: 17 of 27 opening starts "
                  "behind one), and does not swing mid-follow",
                  f"follows {fol}, leads {leads}, mid-follow starts "
                  f"{[v for op, v, _l in mid if op == INT_T]}")
        st["agents"][200]["follow"] = None
        st["agents"][200]["pos"] = (420.0, 0.0)          # parked in reach
        sent = _attacks(st)
        started = [v for op, v, _l in sent if op == INT_T and v[0] == 4]
        LEDGER.ok(started == [[4, 200, 10, 0]],
                  "parked inside enemy_reach() the melee body opens its swing "
                  "(retail's Warrior opened at 100-134 u p50)",
                  f"starts {started}")
        # 10. a cast in flight beats the swing; the swing interval is the
        # body's own weapon (a Monk's staff, 1.75).
        st = _fight_world((300.0, 0.0), (0.0, 110.0))
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        st["agents"][200]["cast_lands_at"] = time.time() + 1.0
        sent = _attacks(st)
        LEDGER.ok([v for op, v, _l in sent if op == INT_T] == []
                  and st["agents"][200]["attack_speed"] == agents.ATTACK_SPEED["staff"],
                  "a cast in flight beats the swing (the monk heals between "
                  "swings, not through them), and the body swings at its own "
                  "weapon's interval -- a staff, 1.75 (retail's Monk: 1.91 s p50)",
                  f"sent {sent}, interval {st['agents'][200]['attack_speed']}")
        # 11. a FOE skill on the bar goes at the fight target, not an ally;
        # with no foe the slot is held and the heal goes out instead.
        st = _fight_world((300.0, 0.0), (0.0, 110.0))
        st["agents"][200].update(skills=((252, 1.0, 10.0), (281, 1.0, 2.0)),
                                 skill_ready=[0.0, 0.0])
        st["player_health"] = 50.0
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        sent = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        casts = [v for op, v in sent if op == INT_T and v[0] == 60]
        st3 = _fight_world((1500.0, 0.0), (0.0, 110.0))
        st3["agents"][200].update(skills=((252, 1.0, 10.0), (281, 1.0, 2.0)),
                                  skill_ready=[0.0, 0.0])
        st3["player_health"] = 50.0
        sent3 = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent3.append((op, vals)),
                               st3, 1)
        casts3 = [v for op, v in sent3 if op == INT_T and v[0] == 60]
        LEDGER.ok(casts == [[60, 200, 10, 252]] and casts3 == [[60, 200, PLAYER, 281]],
                  "Banish (target byte 5, foe) on a party bar is cast at the FOE "
                  "the body fights, never at an ally; with no foe the slot is held "
                  "and Orison goes to the hurt player",
                  f"engaged {casts}, unengaged {casts3}")
        # 12. and its landing hurts the hostile and a kill pays the reward --
        # land_skill's damage site routed by the row's allegiance (H3
        # parameterised it; H4 makes the hostile case the paid one).
        st["agents"][10]["health"] = 0.5
        st["agents"][200]["cast_lands_at"] = time.time() - 0.01
        sent = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        ops = [op for op, _v in sent]
        dmg = [v for op, v in sent if op == FLOAT_T and v[0] == 16]
        LEDGER.ok(st["agents"][10]["dead"] and authsrv.GAME_SMSG_AGENT_KILL_REWARD in ops
                  and len(dmg) == 1 and dmg[0][1] == 10 and dmg[0][2] == 200,
                  "the party's spell lands on the hostile ([16, foe, body, frac]) "
                  "and its kill pays the reward -- land_skill's damage site by the "
                  "row's allegiance", f"dead {st['agents'][10]['dead']}, ops "
                  f"{[hex(o) for o in ops]}, damage {dmg}")
        # 13. the revert arm: --party-no-fight -- engaged, in reach, nothing.
        authsrv.PARTY_FIGHTS = False
        st = _fight_world((300.0, 0.0), (0.0, 110.0))
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        t13 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        sent = _attacks(st)
        LEDGER.ok(t13 is None and sent == [],
                  "--party-no-fight: the leader's start engages nobody and the "
                  "body never swings -- every run before H4, the known-bad arm",
                  f"target {t13}, sent {sent}")
        authsrv.PARTY_FIGHTS = _saved_pf
        # 14. source locks: the three leader-engagement stamps (the player's
        # armed swing start, hit_enemy's one-instant swing, the accepted press)
        # and the tick order (ally_attack_tick after ally_cast_tick).
        _src = inspect.getsource(authsrv)
        _stamps = _src.count("leader_engaged(state, target_id, now, \"swing\")") \
            + _src.count("leader_engaged(state, target, now, \"press\")")
        _order = _src.find("ally_cast_tick(send, state, conn_id)\n")
        _order2 = _src.find("ally_attack_tick(send, state, conn_id)\n", _order)
        LEDGER.ok(_stamps == 3 and 0 < _order < _order2 < _order + 400,
                  "source: the leader's engagement is stamped at the player's "
                  "swing start, hit_enemy's swing and the accepted press (three "
                  "sites), and the world tick runs ally_attack_tick right after "
                  "ally_cast_tick", f"stamps {_stamps}, order {_order} < {_order2}")
    finally:
        authsrv.PARTY_FIGHTS = _saved_pf

    # ---- SLICE-H5: the commander's orders ---------------------------------------
    # WIKI (GWW "Hero" Combat modes, "Hero behavior" Targeting, "Hero flag"):
    # Fight attacks the selected foe within spirit range and any foe in the
    # hero's aggro range, softest first; Guard refrains until the party is
    # engaged and does not leave its area; Avoid never attacks; the lock tops
    # the hierarchy; a flag parks the body, the party flag the group.
    print("\nSLICE-H5: the commander's clicks are obeyed -- stance gates the "
          "engagement, the lock tops the targeting, a flag parks the body and "
          "the party flag the group; each still echoed for the client to draw")
    _saved_pc = authsrv.PARTY_COMMANDS
    _saved_ids = authsrv.HERO_IDS
    try:
        authsrv.HERO_IDS = [3]                # hero_slots(): agent 200
        AI_SET, LOCK_SET = authsrv.GAME_SMSG_HERO_AI_MODE_SET, authsrv.GAME_SMSG_HERO_LOCK_TARGET_SET
        HFLAG_SET, PFLAG_SET = authsrv.GAME_SMSG_HERO_FLAG_SET, authsrv.GAME_SMSG_PARTY_FLAG_SET
        LEAD = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT

        def _cmd(state, opcode, *payload):
            sent = []
            authsrv.handle_hero_command(
                [opcode] + list(payload),
                lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                state, 1, opcode)
            return sent

        def _cmd_world(hostile_pos, monk_pos, second=None):
            st = _fight_world(hostile_pos, monk_pos)
            if second is not None:
                st["agents"][11] = dict(st["agents"][10], pos=second,
                                        npc={"profession": 3, "level": 5},
                                        target=None, target_locked=False)
            return st

        # 1. the stance click: echoed on 0x0062 and STORED; a non-hero agent
        # gets nothing.
        st = _cmd_world((300.0, 0.0), (0.0, 110.0))
        sent = _cmd(st, authsrv.GAME_CMSG_HERO_AI_MODE, 200, 1)
        other = _cmd(st, authsrv.GAME_CMSG_HERO_AI_MODE, 10, 1)
        LEDGER.ok(sent == [(AI_SET, [200, 1])] and other == []
                  and authsrv.hero_command(st, 200)["ai_mode"] == 1,
                  "0x0015 [hero, 1] is echoed as 0x0062 [hero, 1] (pvpui 28.6, "
                  "the ring's setter) and stored as the hero's stance; an "
                  "agent that is no hero slot is ignored",
                  f"sent {sent}, other {other}, cmd {authsrv.hero_command(st, 200)}")
        # 2. GUARD refrains: the leader's start engages nothing, a foe in
        # aggro range engages nothing, the selection engages nothing -- a
        # hostile that OPENED on the party does.
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        st["target"] = 10
        g1 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        st["agents"][10]["target"], st["agents"][10]["target_locked"] = 200, True
        g2 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        LEDGER.ok(g1 is None and g2 == 10,
                  "GUARD: the leader's start, the selection and a foe in aggro "
                  "range engage nothing; a hostile that opened on the party "
                  "does (GWW: 'refraining from combat until actively engaged')",
                  f"guard {g1}, engaged {g2}")
        # 3. the LOCK tops the hierarchy: with the leader on foe 11 and the
        # lock on foe 10, the body fights 10; the clear [hero, 0] hands it
        # back to the leader's target; a dead lock falls through.
        st = _cmd_world((300.0, 0.0), (0.0, 110.0), second=(0.0, 400.0))
        authsrv.leader_engaged(st, 11, time.time(), "swing")
        sent = _cmd(st, authsrv.GAME_CMSG_HERO_LOCK_TARGET, 200, 10)
        l1 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        sent2 = _cmd(st, authsrv.GAME_CMSG_HERO_LOCK_TARGET, 200, 0)
        l2 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        _cmd(st, authsrv.GAME_CMSG_HERO_LOCK_TARGET, 200, 10)
        st["agents"][10]["dead"] = True
        l3 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        LEDGER.ok(sent == [(LOCK_SET, [200, 10])] and l1 == 10
                  and sent2 == [(LOCK_SET, [200, 0])] and l2 == 11 and l3 == 11,
                  "0x0016 [hero, foe] is echoed as 0x0063 and the LOCK tops the "
                  "targeting over the leader's target; [hero, 0] clears it "
                  "(pvpui 28.7) and the leader's target rules again; a dead "
                  "lock falls through ('until the target gets killed')",
                  f"lock {sent} -> {l1}; clear {sent2} -> {l2}; dead lock -> {l3}")
        # 4. AVOID never attacks: lock, leader and aggro range all engage
        # nothing, and the attack tick sends nothing.
        st = _cmd_world((300.0, 0.0), (0.0, 110.0))
        _cmd(st, authsrv.GAME_CMSG_HERO_AI_MODE, 200, 2)
        _cmd(st, authsrv.GAME_CMSG_HERO_LOCK_TARGET, 200, 10)
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        a1 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        sent = _attacks(st)
        LEDGER.ok(a1 is None and sent == [],
                  "AVOID COMBAT: neither the lock, the leader's start nor a foe "
                  "in aggro range engages the body, and it swings at nobody "
                  "(GWW: 'Heroes never attack')", f"target {a1}, sent {sent}")
        # 5. FIGHT: the leader's SELECTION within spirit range engages with no
        # start; with nobody selected a foe inside the hero's aggro range is
        # attacked on sight, the softest class first (a Monk-class foe 800 u
        # off over a Warrior-class foe 300 u off).
        st = _cmd_world((300.0, 0.0), (0.0, 110.0), second=(800.0, 0.0))
        st["target"] = 11
        f1 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        st["target"] = 0
        st["agents"][200]["fight"] = None
        f2 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        st["agents"][11]["pos"] = (1500.0, 0.0)
        st["agents"][200]["fight"] = None
        f3 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        LEDGER.ok(f1 == 11 and f2 == 11 and f3 == 10,
                  "FIGHT: the leader's selected foe within spirit range is "
                  "attacked with no start; with nobody selected a foe inside "
                  "the hero's aggro range is attacked on sight, the lowest "
                  "armour class first (GWW, Hero: Combat modes)",
                  f"selected {f1}, aggro softest {f2}, aggro nearest-left {f3}")
        # 6. the HERO FLAG: 0x001A echoed as 0x0066; the move tick leads the
        # body to the FLAG (a 0x0029 point lead), not its slot; the clear
        # (+INF, +INF) sends it back to the slot.
        st = _cmd_world((1500.0, 0.0), (0.0, 110.0))
        sent = _cmd(st, authsrv.GAME_CMSG_HERO_FLAG_PLACE, 200, (500.0, 500.0), 0)
        walk = [v for op, v, _l in _walk(st) if op == LEAD and v[0] == 200]
        st["agents"][200]["follow"] = None
        st["agents"][200]["pos"] = (500.0, 500.0)       # it got there
        sent2 = _cmd(st, authsrv.GAME_CMSG_HERO_FLAG_PLACE, 200,
                     (float("inf"), float("inf")), 0)
        walk2 = [v for op, v, _l in _walk(st) if op == LEAD and v[0] == 200]
        LEDGER.ok(sent == [(HFLAG_SET, [200, (500.0, 500.0), 0])]
                  and len(walk) == 1 and tuple(walk[0][1]) == (500.0, 500.0)
                  and sent2 == [(HFLAG_SET, [200, (float("inf"), float("inf")), 0])]
                  and len(walk2) == 1 and tuple(walk2[0][1]) == (0.0, 110.0),
                  "0x001A is echoed as 0x0066 (the compass marker and the world "
                  "flag) and the body walks to the FLAG by a 0x0029 point lead; "
                  "the (+INF, +INF) clear returns it to its slot (GWW Hero flag)",
                  f"flag {sent} -> lead {walk}; clear -> lead {walk2}")
        # 7. the PARTY FLAG moves the group: two bodies get leads at the flag
        # plus their own slot offsets.
        st = _cmd_world((1500.0, 0.0), (0.0, 110.0))
        st["agents"][201] = _pbody("warrior", (0.0, -110.0), 1, slot=1)
        sent = _cmd(st, authsrv.GAME_CMSG_PARTY_FLAG_PLACE, (900.0, 300.0), 0)
        walk = {v[0]: tuple(v[1]) for op, v, _l in _walk(st)
                if op == LEAD and v[0] in (200, 201)}
        LEDGER.ok(sent == [(PFLAG_SET, [(900.0, 300.0), 0])]
                  and walk == {200: (900.0, 410.0), 201: (900.0, 190.0)},
                  "0x001B is echoed as 0x0067 and the party flag moves the "
                  "group 'as a single group': each body walks to the flag at "
                  "its own slot offset", f"echo {sent}, leads {walk}")
        # 8. a flagged MELEE body under Fight still chases its foe ('will
        # separate from the flag if necessary'); under Guard it stays.
        st = _cmd_world((500.0, 0.0), (0.0, 110.0))
        st["agents"][200]["npc"]["profession"] = 1
        _cmd(st, authsrv.GAME_CMSG_HERO_FLAG_PLACE, 200, (0.0, 110.0), 0)
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        fight = [(op, v) for op, v, _l in _walk(st) if v[0] == 200
                 and op in (LEAD, FOLLOW)]
        st = _cmd_world((500.0, 0.0), (0.0, 110.0))
        st["agents"][200]["npc"]["profession"] = 1
        _cmd(st, authsrv.GAME_CMSG_HERO_AI_MODE, 200, 1)
        st["agents"][10]["target"], st["agents"][10]["target_locked"] = 200, True
        guard = [(op, v) for op, v, _l in _walk(st) if v[0] == 200
                 and op in (LEAD, FOLLOW)]
        LEDGER.ok(len(fight) == 1 and fight[0][0] == FOLLOW and fight[0][1][-1] == 10
                  and all(op != FOLLOW for op, _v in guard),
                  "a flagged MELEE body under FIGHT chases its foe (a 0x002A "
                  "naming it -- 'will separate from the flag'); under GUARD it "
                  "does not leave its area (no chase, though the foe is on it)",
                  f"fight {fight}, guard {guard}")
        # 9. the revert arm: --party-ignore-commands echoes and obeys nothing.
        authsrv.PARTY_COMMANDS = False
        st = _cmd_world((300.0, 0.0), (0.0, 110.0))
        sent = _cmd(st, authsrv.GAME_CMSG_HERO_AI_MODE, 200, 2)
        sent += _cmd(st, authsrv.GAME_CMSG_HERO_FLAG_PLACE, 200, (500.0, 500.0), 0)
        authsrv.leader_engaged(st, 10, time.time(), "swing")
        r1 = authsrv.party_fight_target(st, 200, st["agents"][200], time.time())
        fp = authsrv.party_flag_point(st, 200, st["agents"][200])
        LEDGER.ok([op for op, _v in sent] == [AI_SET, HFLAG_SET] and r1 == 10
                  and fp is None,
                  "--party-ignore-commands: the stance and flag echoes still go "
                  "out (the client draws them) and nothing changes -- Avoid "
                  "does not stop the fight, the flag parks nobody (the known-"
                  "bad arm)", f"echoes {[hex(op) for op, _v in sent]}, target "
                  f"{r1}, flag point {fp}")
        # 10. source: the four commander opcodes reach ONE handler from the
        # dispatch chain.
        _src = inspect.getsource(authsrv)
        _call = ("        handle_hero_command(values, send, state, conn_id, "
                 "opcode)\n")
        LEDGER.ok(_src.count(_call) == 1
                  and "elif opcode in (GAME_CMSG_HERO_AI_MODE," in _src,
                  "source: the dispatch hands 0x0015/0x0016/0x001A/0x001B to "
                  "handle_hero_command at one site", f"calls {_src.count(_call)}")
    finally:
        authsrv.PARTY_COMMANDS = _saved_pc
        authsrv.HERO_IDS = _saved_ids

    # ---- SLICE-H7: what the hero holds, and the player's bar --------------------
    # Retail follows every henchman body's create with a CREATE_NAMED_ITEM per
    # weapon and a 0x006D naming them (12 of 12); the Monk's is a staff, and
    # the client draws the swing the held item's type says. The owner, H4's
    # run: "Tahlkora attacks, but from long range with a melee punch
    # animation" -- and "let's move to giving the player some actual skills".
    print("\nSLICE-H7: a party caster holds the retail Monk henchman's staff "
          "(the item, then 0x006D, after its create), and the session's default "
          "bar is the content row of modelled hammer skills")
    _staff = agents.item_template("caster_staff")
    _msg = agents.named_item(authsrv.HERO_WEAPON_ITEM_ID, _staff)
    LEDGER.ok(_msg[1] == 112081 and _msg[2] == 26 and _msg[7] == 0x22200100
              and _msg[9] == 6462 and len(_msg[12]) == 4,
              "the staff row is the retail Monk henchman's item, byte for byte "
              "(file 112081, type 26, flags 0x22200100, model 6462, four words)",
              f"{_msg[:12]}")
    LEDGER.ok(authsrv.party_weapon_item({"profession": 3}) == "caster_staff"
              and authsrv.party_weapon_item({"profession": 6}) == "caster_staff"
              and authsrv.party_weapon_item({"profession": 1}) is None,
              "a Monk or Elementalist body holds the staff; a Warrior body holds "
              "nothing yet (its sword and shield are on the tape, not extracted)",
              f"monk {authsrv.party_weapon_item({'profession': 3})}, warrior "
              f"{authsrv.party_weapon_item({'profession': 1})}")
    _src = inspect.getsource(authsrv)
    _a = _src.find('f"hero body (hero {_hid})", conn_id=conn_id)')
    _b = _src.find("hsend(GAME_SMSG_CREATE_NAMED_ITEM,", _a)
    _c = _src.find("hsend(GAME_SMSG_NPC_UPDATE_WEAPONS, [_haid, _wid, 0],", _b)
    LEDGER.ok(0 < _a < _b < _c < _a + 1500,
              "source: the hero body site sends the item and then 0x006D "
              "[hero, item, 0] right after the body's create, through hsend "
              "(retail's order: 0x0020, 0x0161, 0x006D)", f"{_a} < {_b} < {_c}")
    _bar = authsrv.default_skillbar()
    LEDGER.ok(_bar == [351, 359, 352, 356, 322, 346, 1, 2]
              and all(authsrv.skill_damage(sid, 12) is not None
                      for sid in (351, 359, 352, 356, 322)),
              "the default bar is [player.skillbar] -- four hammer attacks with "
              "+damage rows, Power Attack, Frenzy, Healing Signet, Resurrection "
              "Signet -- and every attack on it resolves to a damage number",
              f"bar {_bar}, Mighty Blow at 12: {authsrv.skill_damage(351, 12)}")
    LEDGER.ok(authsrv.skill_damage(351, 12) == (34, "additive")
              and authsrv.skill_damage(359, 12) == (24, "additive")
              and authsrv.skill_damage(352, 12) == (16, "additive")
              and authsrv.skill_damage(356, 12) == (17, "additive"),
              "at Hammer Mastery 12 (the shipped rank) Mighty Blow +34, Heavy "
              "Blow +24, Crushing Blow +16, Irresistible Blow +17 -- the client's "
              "own interpolator over the wiki-verified endpoints",
              f"{[authsrv.skill_damage(s, 12) for s in (351, 359, 352, 356)]}")

    # ---- SLICE-H8: low levels -----------------------------------------------------
    # The owner: "tahlkora doesn't self heal", "make the player/hero lvl 3 (10
    # attribute points) and the enemies lvl 2 (5 attribute points)", "did we
    # research low level weapon damage at all?". F34: a body's own ranks,
    # level and weapon range; the slice character over the base fixture.
    print("\nSLICE-H8: a body casts at its OWN ranks and swings its OWN weapon "
          "range through the wiki's formula; a party caster heals itself; the "
          "slice's level-3 character is [party.slice]'s, over the base fixture")
    _saved_pl = (agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
                 agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS)
    _saved_h9 = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
                 authsrv.PLAYER_SWING_DAMAGE, authsrv.WEAPON_ATTACK_SPEED,
                 authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR)
    try:
        raider = {"npc": {"profession": 1, "level": 2},
                  "attributes": {17: 2, 20: 1, 21: 1}, "damage": [6, 10],
                  "weapon_attribute": 20}
        monk = {"npc": {"profession": 3, "level": 2},
                "attributes": [[13, 2], [14, 1], [15, 1]], "damage": [3, 5],
                "weapon_attribute": 14}
        bare = {"npc": {"profession": 1}}
        LEDGER.ok(authsrv.agent_skill_rank(monk, 281) == 2
                  and authsrv.agent_skill_rank(monk, 252) == 1
                  and authsrv.agent_skill_rank(raider, 322) == 2
                  and authsrv.agent_skill_rank(bare, 281) == authsrv.ENEMY_SKILL_RANK,
                  "a body with `attributes` casts at ITS rank in the skill's "
                  "attribute (the monk's Orison at Healing 2, Banish at Smiting "
                  "1, the raider's Power Attack at Strength 2); a row without "
                  "keeps ENEMY_SKILL_RANK",
                  f"monk {authsrv.agent_skill_rank(monk, 281)}/"
                  f"{authsrv.agent_skill_rank(monk, 252)}, raider "
                  f"{authsrv.agent_skill_rank(raider, 322)}, bare "
                  f"{authsrv.agent_skill_rank(bare, 281)}")
        hits = sorted(authsrv.body_swing_damage(raider, 45.0) for _ in range(40))
        LEDGER.ok(3 <= hits[0] and hits[-1] <= 5
                  and authsrv.body_swing_damage(bare, 45.0) is None,
                  "a body with a `damage` range swings it through the wiki's "
                  "formula (2^((5 x rank - armour) / 40)) at its own rank and "
                  "level: the level-2 raider's 6-10 lands 3-5 on the player's "
                  "armour 45 -- retail's Pre-Searing hostiles landed 3/4/5 on the "
                  "level-3 observer (F34); a row without keeps the fraction",
                  f"40 swings span {hits[0]:.0f}..{hits[-1]:.0f}")
        LEDGER.ok(authsrv.agent_strike_level(monk) == 6.0
                  and authsrv.agent_strike_level(bare) == 60.0
                  and abs(authsrv.strike_multiplier(60.0, 40.0)
                          - authsrv.armour_multiplier(40.0)) < 1e-9,
                  "a body's SKILL strike level is 3 x its level (6 at level 2; "
                  "the baseline 60 without a level), and at 60 the multiplier "
                  "is the old armour_multiplier exactly",
                  f"monk {authsrv.agent_strike_level(monk)}, bare "
                  f"{authsrv.agent_strike_level(bare)}")
        # the landed spell: a level-2 monk's Banish on the player at its rank
        # and strike level, through land_skill's own path
        # Banish is filed armour-ignoring (holy, SKILLS-FA), so the strike
        # level shows on an armour-RESPECTING spell: Flare's 20 at rank 0 by a
        # level-2 caster is 20 x 2^((6 - 25) / 40) ~ 14.4 on the player's
        # elemental 25, where test_skilldamage's level-20 baseline lands 36.68.
        st = _world(dist=85.0)
        st["agents"][10].update(npc={"profession": 3, "level": 2},
                                attributes={13: 2, 14: 1, 15: 1},
                                skills=((194, 1.0, 5.0),), skill_ready=[0.0],
                                casting=0, cast_target=1)
        st["player_health"] = 100.0
        sent = []
        authsrv.land_skill(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                           st, 10, st["agents"][10], 1)
        dealt = 100.0 - st["player_health"]
        LEDGER.ok(12.0 < dealt < 16.0
                  and authsrv.skill_damage(252, authsrv.agent_skill_rank(st["agents"][10], 252))[0] == 22,
                  "a level-2 caster's Flare lands 20 x 2^((6 - 25)/40) ~ 14 on the "
                  "player's elemental armour 25 (the level-20 baseline: 36.7), and "
                  "its Banish resolves to the rank-1 22 (rank 12: 56)",
                  f"Flare dealt {dealt:.1f}")
        # the party caster heals ITSELF under an ally-kind heal
        st = _fight_world((1500.0, 0.0), (0.0, 110.0))
        st["agents"][200].update(skills=((281, 1.0, 2.0),), skill_ready=[0.0],
                                 health=40.0, max_health=100.0)
        st["player_health"] = 100.0
        sent = []
        authsrv.ally_cast_tick(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                               st, 1)
        casts = [v for op, v in sent if op == INT_T and v[0] == 60]
        LEDGER.ok(casts == [[60, 200, 200, 281]],
                  "a hurt party caster with a healthy party casts Orison at "
                  "ITSELF (the client's target byte 3 allows the caster) -- "
                  "the owner: 'tahlkora doesn't self heal'", f"casts {casts}")
        # the slice character over the base fixture
        base = (agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
                agents.PLAYER_ATTRIBUTE_POINTS)
        changed = authsrv.apply_party_character(agents.WORLD.get("party", "slice"))
        st = authsrv.attribute_state({})
        LEDGER.ok(base == (1, 100, 200) and agents.PLAYER_LEVEL == 3
                  and agents.PLAYER_HEALTH == 140 and st.points_total == 10
                  and st.spent == 10 and authsrv.player_rank_for_skill(382) == 3
                  and authsrv.player_full_max_health({"level": 3}) == 140.0,
                  "--party slice rebinds the character: level 3, health 140 "
                  "(WIKI: 100/120/140), Swordsmanship 3 / Strength 2 / Tactics 1 "
                  "= all 10 of level 3's points (H9: the sword's ranks) -- over "
                  "the base row's level-1, 100, 200-point fixture the offline "
                  "locks price",
                  f"base {base}, changed {changed}, spent {st.spent} of "
                  f"{st.points_total}")
        # SLICE-H8c: a normal enemy stays dead; the training dummy gets up.
        st = _world(dist=85.0)
        st["agents"][10].update(dead=True, died_at=time.time() - 1000.0, revives=False)
        st["agents"][11] = dict(st["agents"][10], revives=True)
        st["agents"][12] = dict(st["agents"][10])
        del st["agents"][12]["revives"]
        sent = []
        authsrv.revive_due(lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                           st, 1)
        LEDGER.ok(st["agents"][10]["dead"] and not st["agents"][11]["dead"]
                  and not st["agents"][12]["dead"],
                  "an agent whose row says `revives = false` stays DOWN past "
                  "REVIVE_AFTER (retail respawns nothing in an instance but the "
                  "training targets); `revives = true` and a MISSING key (the "
                  "legacy --enemy body, every fixture) get back up",
                  f"no: dead {st['agents'][10]['dead']}; yes: dead "
                  f"{st['agents'][11]['dead']}; missing: dead {st['agents'][12]['dead']}")
        _rows = agents.WORLD.rows("spawn")
        LEDGER.ok(_rows["test_enemy"].get("revives") is True
                  and all("revives" not in _rows[k]
                          for k in _rows if k.startswith("corridor_")),
                  "content: the practice target's row opts in to the revive; no "
                  "corridor row does, so a killed raider stays killed",
                  f"test_enemy {_rows['test_enemy'].get('revives')}, corridor rows "
                  f"{[k for k in _rows if k.startswith('corridor_')]}")
    finally:
        (agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
         agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS) = _saved_pl
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.ATTACK_INTERVAL,
         authsrv.PARTY_SKILLBAR) = _saved_h9

    # ---- SLICE-H9/H10/H11: the sword and the shield, the gated strikes, the
    # hammer bandit ----------------------------------------------------------
    # The owner: "the player uses a Sword and Shield. skills: the classic GW
    # sword combo: Sever Artery, Gash (need Deep Wound + conditional
    # application), Final Thrust (need 50% HP logic). the bandit should be a
    # Hammer Warrior that just has Power Attack." F35.
    print("\nSLICE-H9/H10/H11: the slice character holds a sword and a shield "
          "(the level-3 henchman's bytes), Gash lands its bonus and Deep Wound "
          "on a BLEEDING foe only, Final Thrust doubles its bonus below half "
          "health and takes all adrenaline, and the bandit is a hammer warrior")
    _saved_h9 = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
                 authsrv.PLAYER_SWING_DAMAGE, authsrv.WEAPON_ATTACK_SPEED,
                 authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR,
                 agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
                 agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS,
                 authsrv.skill_cost)
    try:
        sword = agents.item_template("starter_sword")
        shield = agents.item_template("starter_shield")
        LEDGER.ok(sword["item_type"] == 27 and shield["item_type"] == 24
                  and authsrv.weapon_damage_range(sword) == (2, 3)
                  and authsrv.armour_of_piece(shield)[0] == 3
                  and authsrv.WEAPON_TYPE_ATTRIBUTE[27] == 20,
                  "the two item rows: a type-27 sword whose own 584 word reads "
                  "2-3 (the Starter Sword's, WIKI) and a type-24 shield whose "
                  "572 word reads armour 3 (the Starter Shield's) -- the "
                  "level-3 Warrior henchman's bytes off 20260819T132414 -- and "
                  "a sword swings at Swordsmanship (20)",
                  f"sword {authsrv.weapon_damage_range(sword)}, shield "
                  f"{authsrv.armour_of_piece(shield)}")
        base = (authsrv.PLAYER_SWING_DAMAGE, round(authsrv.ATTACK_INTERVAL, 3),
                authsrv.default_skillbar()[:3],
                authsrv.player_armour_at("warrior_body"),
                authsrv.player_spell_armour())
        changed = authsrv.apply_party_character(agents.WORLD.get("party", "slice"))
        after = (authsrv.PLAYER_SWING_DAMAGE, round(authsrv.ATTACK_INTERVAL, 3),
                 authsrv.default_skillbar(),
                 authsrv.player_armour_at("warrior_body"),
                 authsrv.player_spell_armour())
        LEDGER.ok(base == ((3, 5), 1.75, [351, 359, 352], 45.0, 25.0)
                  and after == ((2, 3), 1.33, [382, 384, 385, 322, 346, 1, 2, 380],
                                48.0, 28.0)
                  and agents.PLAYER_WEAPON is not None
                  and agents.PLAYER_WEAPON["item_type"] == 27
                  and authsrv.player_weapon_rank({}) == 3,
                  "--party slice rebinds what the character holds: the swing "
                  "2-3 at 1.33 s (the hammer's 3-5 at 1.75), the sword bar "
                  "Sever Artery / Gash / Final Thrust / Power Attack / Frenzy / "
                  "the two signets / Bonetti's (H12), the shield's +3 on every location (45 -> "
                  "48 physical, 25 -> 28 elemental; WIKI: 'overall armor "
                  "rating'), and the weapon rank is Swordsmanship 3",
                  f"base {base}, after {after}, changed {changed}")
        # THE STRIKES, through the player's own press -> cast_tick landing.
        # Costs are stubbed (test_castcycle's precedent): what is measured is
        # the gate and the double, not a strike's price.
        authsrv.skill_cost = lambda sid: (0, 0)
        st = _world(dist=50.0, armor_rating=26.0, name="bandit")
        st["player_health"] = 140.0

        def _land(skill, target=10):
            sent = []
            send = lambda op, vals, label="", quiet=False: sent.append((op, vals))
            authsrv.handle_skill_press([0, skill, 0, target], send, st, 1,
                                       authsrv.GAME_CMSG_USE_SKILL)
            for cast in st.get("pending_casts", ()):
                for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                    cast[k] -= 30.0
            for _ in range(3):
                authsrv.cast_tick(send, st, 1)
            return sent

        before = st["agents"][10]["health"]
        sent = _land(384)
        plain = before - st["agents"][10]["health"]
        dw = [ep for ep in authsrv.effect_table(st).on_agent(10)
              if ep["skill"] == 482]
        LEDGER.ok(0 < plain <= 4 and dw == []
                  and st["agents"][10]["max_health"] == 100.0,
                  "Gash on a foe that is NOT bleeding is a plain sword swing: "
                  "the 2-3 through armour 26, no +8 (Swordsmanship 3), no Deep "
                  "Wound, the maximum untouched -- WIKI: 'If this attack hits "
                  "a Bleeding foe' gates both (requires_condition)",
                  f"dealt {plain:.1f}, deep wounds {len(dw)}")
        authsrv.apply_condition(lambda *a, **k: None, st, 10, 478, 9.0, 3, 1, 382)
        before = st["agents"][10]["health"]
        sent = _land(384)
        gashed = before - st["agents"][10]["health"]
        dw = [ep for ep in authsrv.effect_table(st).on_agent(10)
              if ep["skill"] == 482]
        LEDGER.ok(gashed >= 8.0 and len(dw) == 1
                  and abs(dw[0]["duration"] - 8.0) < 1e-9
                  and st["agents"][10]["max_health"] == 80.0,
                  "and on a BLEEDING foe it strikes for the swing +8 and puts an "
                  "8 s Deep Wound on it (both endpoints at Swordsmanship 3), "
                  "the foe's maximum falling 20% (100 -> 80, the existing 482 "
                  "model)", f"dealt {gashed:.1f}, deep wound "
                  f"{[(ep['skill'], ep['duration']) for ep in dw]}, max "
                  f"{st['agents'][10]['max_health']}")
        # Final Thrust: +9 at Swordsmanship 3 (the client's 1..40), doubled
        # below half, and the adrenaline wipe on the wire.
        st["agents"][10]["health"] = 30.0            # 30 of 80: below 50%
        sent = _land(385)
        low = 30.0 - st["agents"][10]["health"]
        wipes = [v for op, v in sent if op == authsrv.AGENT_ADRENALINE_CLEAR]
        st["agents"][10]["health"] = 70.0            # 70 of 80: above
        sent2 = _land(385)
        high = 70.0 - st["agents"][10]["health"]
        wipes2 = [v for op, v in sent2 if op == authsrv.AGENT_ADRENALINE_CLEAR]
        LEDGER.ok(low >= 18.0 and 9.0 <= high < 18.0
                  and wipes == [[authsrv.PLAYER_AGENT_ID]]
                  and wipes2 == [[authsrv.PLAYER_AGENT_ID]],
                  "Final Thrust's +9 DOUBLES on a foe below half health (>= 18 "
                  "landed at 30 of 80) and does not above (9..17 at 70 of 80) "
                  "-- the bonus only, never the swing (WIKI, the page's Notes) "
                  "-- and each completion wipes the player's adrenaline: ONE "
                  "0x00D0 [player], the death's and the 25 s clear's shape",
                  f"below {low:.1f}, above {high:.1f}, wipes {wipes}/{wipes2}")
        LEDGER.ok(authsrv.skill_health_threshold(385) == 0.5
                  and authsrv.skill_health_threshold(384) is None
                  and authsrv.skill_requires_condition(384) == 478
                  and authsrv.skill_requires_condition(385) is None
                  and authsrv.skill_clears_adrenaline(385)
                  and not authsrv.skill_clears_adrenaline(384),
                  "the three readers: the 50% is the CLIENT's own bit-clear "
                  "bonus slot (50/50) named by the row, Gash's gate is Bleeding "
                  "(478), and only Final Thrust's row clears adrenaline",
                  f"thr {authsrv.skill_health_threshold(385)}, gate "
                  f"{authsrv.skill_requires_condition(384)}")
        # THE NPC ARM shares the terms: an attack skill's bonus and condition
        # at the player, judged by the same function.
        st2 = _world(dist=50.0)
        st2["player_health"] = 100.0
        no = authsrv.attack_skill_terms(st2, 384, 1, authsrv.PLAYER_AGENT_ID,
                                        6.0, 1, "agent 10")
        authsrv.apply_condition(lambda *a, **k: None, st2, authsrv.PLAYER_AGENT_ID,
                                478, 9.0, 1, 1, 382)
        yes = authsrv.attack_skill_terms(st2, 384, 1, authsrv.PLAYER_AGENT_ID,
                                         6.0, 1, "agent 10")
        LEDGER.ok(no == (0.0, None, False) and yes[0] == 6.0
                  and yes[1] is not None and yes[1][0] == 482 and yes[2] is False,
                  "the same terms serve an NPC's strike at the player: no "
                  "bonus and no condition until the player bleeds, then both "
                  "(and Gash knocks nobody down -- the third term, H12)",
                  f"no {no}, yes {yes}")
        # THE BANDIT: a hammer warrior with Power Attack, holding a hammer.
        rows = {k: agents.WORLD.get("spawn", k)
                for k in ("corridor_raider_a", "corridor_raider_b", "corridor_boss")}
        bars = {k: [s_[0] for s_ in r["skills"]] for k, r in rows.items()}
        raider = {"npc": {"profession": 1, "level": 2},
                  "attributes": dict((int(a_), int(r_)) for a_, r_ in
                                     rows["corridor_raider_a"]["attributes"]),
                  "damage": rows["corridor_raider_a"]["damage"],
                  "weapon_attribute": rows["corridor_raider_a"]["weapon_attribute"]}
        hits = sorted(authsrv.body_swing_damage(raider, 45.0) for _ in range(60))
        LEDGER.ok(bars == {"corridor_raider_a": [322], "corridor_raider_b": [322],
                           "corridor_boss": [322, 323]}
                  and all(dict((int(a_), int(r_)) for a_, r_ in r["attributes"])
                          == {19: 2, 17: 1, 21: 1} for r in rows.values())
                  and all(r["weapon_attribute"] == 19
                          and r.get("weapon_item") == "starter_hammer"
                          and abs(float(r.get("attack_speed", 0)) - 1.75) < 1e-9
                          for r in rows.values())
                  and 3 <= hits[0] and hits[-1] <= 6
                  and authsrv.agent_skill_rank(raider, 322) == 1,
                  "every raider row is a HAMMER warrior: Power Attack alone "
                  "(the boss adds Desperation Blow), Hammer 2 / Strength 1 / "
                  "Tactics 1 = level 2's five points, a starter hammer in hand "
                  "at 1.75 s (WIKI), and its 6-10 still lands single digits on "
                  "the player's armour 45 (retail's 3/4/5; F34)",
                  f"bars {bars}, 60 swings span {hits[0]:.0f}..{hits[-1]:.0f}")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.ATTACK_INTERVAL,
         authsrv.PARTY_SKILLBAR, agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
         agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS,
         authsrv.skill_cost) = _saved_h9

    # ---- SLICE-H12: knock-down and block ---------------------------------
    # The owner: "do knock-down and block next". F36: the knock-down's wire
    # is the corpus's (0x00A2 [63, agent, 2.0], 3 of 3); what a down body
    # does not do is the wiki's; the block is the client's own reason word.
    print("\nSLICE-H12: a knocked-down body sends prop 63 and does nothing for "
          "2 s; a knocked-down player's casts release and presses refuse; "
          "Hammer Bash, Heavy Blow, Crushing Blow, Irresistible Blow and "
          "Desperation Blow do what their pages say; a stance's block_chance "
          "blocks (the attack-fail word 0), pays Bonetti's energy and ends "
          "on a skill use; Weakness cuts the weapon")
    _saved_kd = (authsrv.skill_cost, authsrv.random.random, agents.PLAYER_OFFHAND)
    try:
        authsrv.skill_cost = lambda sid: (0, 0)
        FLOAT_U = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
        INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
        # 1. a following body falls: halt + prop 63; down it opens no swing;
        # a second knock-down while down is refused; up, it swings.
        st = _world(dist=50.0, armor_rating=26.0)
        st["agents"][10].update(follow={"tid": 1}, moving=True)
        st["player_health"] = 140.0
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals))
        fell = authsrv.knock_down(send, st, 10, 1, "the test")
        again = authsrv.knock_down(send, st, 10, 1, "the test, again")
        n_after_first = len(sent)
        LEDGER.ok(fell and not again and len(sent) == 2
                  and sent[0][0] == authsrv.GAME_SMSG_AGENT_STOP_MOVING
                  and sent[1] == (FLOAT_U, [63, 10, authsrv._f32(2.0)])
                  and st["agents"][10]["follow"] is None
                  and authsrv.knocked_down(st, 10)
                  and st["agents"][10]["knocked_until"] > time.time() + 1.5,
                  "a knock-down on a walking body: the halt, then 0x00A2 [63, "
                  "agent, 2.0] -- the corpus's shape, 3 of 3 -- its follow "
                  "dropped, its clock 2 s out (WIKI); a second knock-down "
                  "while down sends NOTHING (WIKI: not again until up)",
                  f"fell {fell}, again {again}, sent {sent}")
        swings = _swings(st)
        st["agents"][10]["knocked_until"] = 0.0
        swings_up = _swings(st)
        LEDGER.ok(swings == [] and any(v[0] in (4, 50, 60) for op, v, _l in swings_up),
                  "the attack tick opens NO swing and NO cast on a down body, and "
                  "acts the moment its clock has run out",
                  f"down {len(swings)} sends, up opens "
                  f"{[v for op, v, _l in swings_up if v[0] in (4, 50, 60)]}")
        # 2. the player falls: the pending cast releases with the measured
        # burst, a press while down is answered with the bare release only,
        # an armed swing is dropped, and a press after rising is accepted.
        st = _world(dist=50.0, armor_rating=26.0)
        st["player_health"] = 140.0
        sent = []
        authsrv.handle_skill_press([0, 322, 0, 10], send, st, 1,
                                   authsrv.GAME_CMSG_USE_SKILL)
        pending = list(st.get("pending_casts") or ())
        sent = []
        fell = authsrv.knock_down(send, st, authsrv.PLAYER_AGENT_ID, 1, "the test")
        authsrv.cast_tick(send, st, 1)
        ops = [(op, v) for op, v in sent]
        released = [v for op, v in ops if op == authsrv.GAME_SMSG_SKILL_REFUSED]
        stopped = [v for op, v in ops if op == INT and v[0] in (49, 59, 45)]
        LEDGER.ok(fell and len(pending) == 1 and pending[0].get("cancelled") == "knocked-down"
                  and (FLOAT_U, [63, 1, authsrv._f32(2.0)]) in ops
                  and released == [[1, 322, 0]] and len(stopped) == 1,
                  "the player's knock-down: prop 63 on the player, the pending "
                  "Power Attack marked cancelled and released by the tick with "
                  "the measured burst (a stop word, E2)",
                  f"cancelled {[c.get('cancelled') for c in pending]}, stopped "
                  f"{stopped}, released {released}")
        sent = []
        authsrv.handle_skill_press([0, 322, 0, 10], send, st, 1,
                                   authsrv.GAME_CMSG_USE_SKILL)
        refused = [op for op, v in sent]
        st["player_swing"] = {"target": 10}
        authsrv.attack_tick(send, st, 1)
        dropped = st.get("player_swing") is None
        st["player_knocked_until"] = 0.0
        sent = []
        authsrv.handle_skill_press([0, 322, 0, 10], send, st, 1,
                                   authsrv.GAME_CMSG_USE_SKILL)
        accepted = any(op == 0x00E4 for op, v in sent)
        LEDGER.ok(refused == [authsrv.GAME_SMSG_SKILL_REFUSED] and dropped and accepted,
                  "while down a press gets the bare E2 release and nothing "
                  "else, the armed swing is dropped, and once the clock runs "
                  "out a press is accepted (E4) again",
                  f"refused {[hex(o) for o in refused]}, dropped {dropped}, "
                  f"accepted {accepted}")
        # 3. the hammer skills through the player's press -> landing.
        st = _world(dist=50.0, armor_rating=26.0)
        st["player_health"] = 140.0
        st["pending_casts"] = []

        def _land(skill, target=10):
            out = []
            snd = lambda op, vals, label="", quiet=False: out.append((op, vals))
            authsrv.handle_skill_press([0, skill, 0, target], snd, st, 1,
                                       authsrv.GAME_CMSG_USE_SKILL)
            for cast in st.get("pending_casts", ()):
                for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                    cast[k] -= 30.0
            for _ in range(3):
                authsrv.cast_tick(snd, st, 1)
            return out

        out = _land(331)                                  # Hammer Bash
        kd = [v for op, v in out if op == FLOAT_U and v[0] == 63]
        wipe = [v for op, v in out if op == authsrv.AGENT_ADRENALINE_CLEAR]
        LEDGER.ok(kd == [[63, 10, authsrv._f32(2.0)]] and authsrv.knocked_down(st, 10)
                  and wipe == [[1]],
                  "Hammer Bash: the foe falls for the client's own 2 s (its "
                  "duration slot, 2/2 bit-clear) and the player's adrenaline is "
                  "wiped (WIKI)", f"kd {kd}, wipe {wipe}")
        # Crushing Blow: the Deep Wound only while the foe is down.
        st["agents"][10]["knocked_until"] = 0.0
        before = st["agents"][10]["health"]
        out = _land(352)
        dw_up = [ep for ep in authsrv.effect_table(st).on_agent(10) if ep["skill"] == 482]
        hurt_up = before - st["agents"][10]["health"]
        st["agents"][10]["knocked_until"] = time.time() + 2.0
        out = _land(352)
        dw_down = [ep for ep in authsrv.effect_table(st).on_agent(10) if ep["skill"] == 482]
        LEDGER.ok(dw_up == [] and hurt_up >= 16 and len(dw_down) == 1
                  and abs(dw_down[0]["duration"] - 17.0) < 1e-9,
                  "Crushing Blow: +16 lands on a standing foe with NO Deep Wound; "
                  "on a foe already down the 17 s Deep Wound lands too (both at "
                  "Hammer 12; the row's condition_requires)",
                  f"standing: dw {len(dw_up)}, hurt {hurt_up:.0f}; down: dw "
                  f"{[(ep['skill'], ep['duration']) for ep in dw_down]}")
        # Heavy Blow: nothing without Weakness; bonus and knock-down with it.
        st["agents"][10]["knocked_until"] = 0.0
        st["agents"][10]["health"] = 100.0
        out = _land(359)
        kd_plain = [v for op, v in out if op == FLOAT_U and v[0] == 63]
        hurt_plain = 100.0 - st["agents"][10]["health"]
        authsrv.apply_condition(lambda *a, **k: None, st, 10, 486, 20.0, 6, 1, 323)
        st["agents"][10]["health"] = 100.0
        out = _land(359)
        kd_weak = [v for op, v in out if op == FLOAT_U and v[0] == 63]
        hurt_weak = 100.0 - st["agents"][10]["health"]
        LEDGER.ok(kd_plain == [] and hurt_plain < 30 and kd_weak == [[63, 10, authsrv._f32(2.0)]]
                  and hurt_weak >= 30,
                  "Heavy Blow: a plain swing on a foe that is not Weakened (no "
                  "knock-down, no +30); on a Weakened foe the +30 lands and it "
                  "falls -- requires_condition gates all three (WIKI)",
                  f"plain: kd {kd_plain}, hurt {hurt_plain:.0f}; weakened: kd "
                  f"{kd_weak}, hurt {hurt_weak:.0f}")
        # Desperation Blow: one of four conditions on the foe, the player falls.
        for ep in list(authsrv.effect_table(st).on_agent(10)):
            authsrv.effect_table(st).close(ep["buff"])
        st["agents"][10]["knocked_until"] = 0.0
        st["agents"][10]["health"] = 100.0
        out = _land(323)
        conds = [ep["skill"] for ep in authsrv.effect_table(st).on_agent(10)
                 if ep["skill"] in (478, 481, 482, 486)]
        kd_self = [v for op, v in out if op == FLOAT_U and v[0] == 63]
        LEDGER.ok(len(conds) == 1 and kd_self == [[63, 1, authsrv._f32(2.0)]]
                  and authsrv.knocked_down(st, authsrv.PLAYER_AGENT_ID),
                  "Desperation Blow: exactly ONE of Deep Wound / Weakness / "
                  "Bleeding / Crippled on the foe (the row's random_conditions) "
                  "and the PLAYER falls for the client's 2 s (self_knocks_down)",
                  f"conditions {conds}, kd {kd_self}")
        st["player_knocked_until"] = 0.0
        LEDGER.ok(authsrv.skill_knock_down_seconds(331) == 2.0
                  and authsrv.skill_knock_down_seconds(359) == 2.0
                  and authsrv.skill_knock_down_seconds(323) == 2.0
                  and authsrv.skill_random_condition(323)[1] in (20.0, 25.0, 15.0)
                  and authsrv.skill_random_condition(384) is None,
                  "the readers: 2 s from the client's flat duration slot (331, "
                  "323) or the wiki default (359); a draw from 323's four with "
                  "the description's seconds; nothing from a row without",
                  f"{[authsrv.skill_knock_down_seconds(s_) for s_ in (331, 359, 323)]}")
        # 4. BLOCK: a hostile under Bonetti's Defense blocks the player's swing
        # (the roll forced), the block word goes out, no damage, no adrenaline;
        # forced through, it lands. Irresistible Blow blocked: its damage
        # lands anyway and the blocker falls.
        st = _world(dist=50.0, armor_rating=26.0)
        st["player_health"] = 140.0
        sent = []
        authsrv.apply_effect(send, st, 10, 380, 1, 10, 1)
        chance = authsrv.block_chance(st, 10)
        authsrv.random.random = lambda: 0.0                 # every roll blocks
        sent = []
        res = authsrv.hit_enemy(send, st, 10, 1, skill_strike=True, label="t")
        words = [v for op, v in sent if v and v[0] == 38]
        gains = [op for op, v in sent if op == authsrv.AGENT_ADRENALINE_GAIN]
        hp_blocked = st["agents"][10]["health"]
        authsrv.random.random = lambda: 0.99                # nothing blocks
        sent = []
        res2 = authsrv.hit_enemy(send, st, 10, 1, skill_strike=True, label="t")
        hp_landed = st["agents"][10]["health"]
        LEDGER.ok(abs(chance - 0.75) < 1e-9 and res == "blocked"
                  and words == [[38, 10, 1, 0]] and gains == [] and hp_blocked == 100.0
                  and res2 == "landed" and hp_landed < 100.0,
                  "Bonetti's Defense on the hostile is a 75% block (the client's "
                  "flat scale slot); a blocked swing sends [38, target, player, "
                  "0] -- the client's own 'block' word -- deals nothing and "
                  "gains no adrenaline; a swing the roll lets through lands",
                  f"chance {chance}, blocked: {res} {words} hp {hp_blocked}, "
                  f"through: {res2} hp {hp_landed}")
        authsrv.random.random = lambda: 0.0
        st["agents"][10]["health"] = 100.0
        st["agents"][10]["knocked_until"] = 0.0
        sent = []
        res = authsrv.hit_enemy(send, st, 10, 1, skill_strike=True, label="t",
                                skill_id=356)
        kd = [v for op, v in sent if op == FLOAT_U and v[0] == 63]
        LEDGER.ok(res == "blocked" and abs((100.0 - st["agents"][10]["health"]) - 17.0) < 1e-9
                  and kd == [[63, 10, authsrv._f32(2.0)]],
                  "Irresistible Blow BLOCKED: the blocker takes the skill's 17 "
                  "(Hammer 12) anyway and falls -- the block punishment (WIKI)",
                  f"{res}, hurt {100.0 - st['agents'][10]['health']:.0f}, kd {kd}")
        # 5. the PLAYER's Bonetti's: an NPC swing blocked, +5 energy on the
        # wire, and the stance ends on the player's next press.
        st = _world(dist=50.0, armor_rating=26.0)
        st["player_health"] = 140.0
        authsrv.player_pools(st)
        sent = []
        ep = authsrv.apply_effect(send, st, 1, 380, 1, 0, 1)
        pool = authsrv.player_energy(st)
        pool.current = 10.0
        sent = []
        res = authsrv.land_swing(send, st, 10, st["agents"][10], 1)
        words = [v for op, v in sent if v and v[0] == 38]
        egain = [v for op, v in sent if op == FLOAT_U and v[0] == 52]
        sent = []
        authsrv.handle_skill_press([0, 322, 0, 10], send, st, 1,
                                   authsrv.GAME_CMSG_USE_SKILL)
        removed = [v for op, v in sent if op == authsrv.GAME_SMSG_EFFECT_REMOVE]
        LEDGER.ok(ep is not None and res == "blocked" and words == [[38, 1, 10, 0]]
                  and st["player_health"] == 140.0 and abs(pool.current - 15.0) < 0.01
                  and len(egain) == 1 and removed == [[1, ep["buff"]]]
                  and authsrv.block_chance(st, 1) == 0.0,
                  "the player's Bonetti's: a hostile's swing is BLOCKED ([38, "
                  "player, hostile, 0], no damage), +5 energy on the pool and "
                  "the wire (property 52), and the stance ENDS on the player's "
                  "next accepted press (a real 0x0044)",
                  f"{res} {words}, energy {pool.current}, gain {egain}, "
                  f"removed {removed}")
        authsrv.random.random = _saved_kd[1]
        LEDGER.ok(not authsrv.holds_shield(st, 1)
                  and (setattr(agents, "PLAYER_OFFHAND",
                               agents.item_template("starter_shield")) or True)
                  and authsrv.holds_shield(st, 1),
                  "holds_shield reads the player's offhand row: false on the "
                  "base fixture, true with the starter shield -- the gate a "
                  "`requires_shield` row (Shield Stance) would read",
                  "base false, shield true")
        agents.PLAYER_OFFHAND = _saved_kd[2]
        # 6. WEAKNESS cuts the weapon's damage to a third (WIKI: 66% less).
        st = _world(dist=50.0, armor_rating=26.0)
        st["player_health"] = 140.0
        st["pending_casts"] = []
        m0 = authsrv.weakness_multiplier(st, 1)

        def _mean(n=25):
            tot = 0.0
            for _ in range(n):
                st["agents"][10]["health"] = 100.0
                authsrv.hit_enemy(send, st, 10, 1, skill_strike=True, label="t")
                tot += 100.0 - st["agents"][10]["health"]
            return tot / n

        plain = _mean()
        authsrv.apply_condition(lambda *a, **k: None, st, 1, 486, 20.0, 1, 1, 323)
        m1 = authsrv.weakness_multiplier(st, 1)
        weak = _mean()
        LEDGER.ok(m0 == 1.0 and abs(m1 - 0.34) < 1e-9 and weak < plain * 0.6,
                  "Weakness on the swinger: the multiplier is 0.34 (WIKI: 66% "
                  "less with attacks) and 25 hammer swings average well under "
                  "the unweakened 25",
                  f"plain {plain:.1f}, weakened {weak:.1f}")
    finally:
        authsrv.skill_cost, authsrv.random.random, agents.PLAYER_OFFHAND = _saved_kd

    # ---- JARIN-S: the first retail hero's corrections (studies/slice F39) ------
    print("\nJARIN-S: the hero is a second player on the wire (its pools and its "
          "skill family), its lock is cleared at the kill, a lone hero walks to "
          "the party flag itself, a hero's death is the player's tick, a wipe "
          "stands the party up at the shrine, a zone carries the stance and "
          "clears the penalty in a town, and the rig is retail's block")
    _sv = (authsrv.HERO_IDS, authsrv.PARTY_COMMANDS, authsrv.HERO_WIRE_POOLS,
           authsrv.WIPE_SHRINE, authsrv.ZONE_CARRY_ON, authsrv.DEATH_PENALTY_FORCED,
           authsrv.HERO_LEVEL, authsrv.HERO_SKILLS, authsrv.HERO_VITALS,
           dict(authsrv.ZONE_CARRY))
    try:
        authsrv.HERO_IDS = [6]
        authsrv.PARTY_COMMANDS = True
        authsrv.HERO_WIRE_POOLS = True
        authsrv.WIPE_SHRINE = True
        authsrv.ZONE_CARRY_ON = True
        authsrv.DEATH_PENALTY_FORCED = True
        authsrv.ZONE_CARRY.clear()
        HERO = authsrv.HERO_AGENT_ID
        FLAGS, STATUS = authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS, authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
        PINT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT

        def _koss(**over):
            row = {"name": "koss", "dead": False, "died_at": 0.0, "health": 100.0,
                   "max_health": 100.0, "base_max_health": 100.0, "base_max_energy": 20.0,
                   "last_hit": 0.0, "pos": (100.0, 0.0), "plane": 0,
                   "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0,
                   "attack_speed": 1.33, "attacks_back": False,
                   "skills": ((322, 0.0, 3.0), (385, 0.0, 0.0)), "skill_ready": [0.0, 0.0],
                   "npc": dict(agents.npc_template(authsrv.HERO_BODY_NPC),
                               profession=1, level=3),
                   "definition": authsrv.HERO_DEFINITION, "party_slot": 0,
                   "hero": 6, "weapon_item_id": 210}
            row.update(over)
            return row

        def _jw(**over):
            st = {"agents": {}, "pos": (0.0, 0.0), "plane": 0, "map_id": 168,
                  "level": 3, "spawn_point": (500.0, 500.0, 0), "player_dead": False,
                  "player_died_at": 0.0, "player_health": 100.0}
            st.update(over)
            return st

        def _sends():
            out = []
            return out, (lambda op, vals, label="", quiet=False: out.append((op, vals)))

        # 1. the pools: 0x00CF / 0x00D0 for a HERO row, nothing for a henchman
        st = _jw(); st["agents"][HERO] = _koss(); st["agents"][201] = _koss(hero=None)
        sent, send = _sends()
        authsrv.hero_pool_gain(send, st, HERO, st["agents"][HERO], 25, "t")
        authsrv.hero_pool_gain(send, st, 201, st["agents"][201], 25, "t")
        authsrv.hero_pool_gain(send, st, HERO, st["agents"][HERO], 0, "t")
        LEDGER.ok(sent == [(authsrv.AGENT_ADRENALINE_GAIN, [HERO, 25])],
                  "a hero's adrenaline gain is on the wire -- 0x00CF [hero, 25] -- a "
                  "henchman's is not, and a zero-unit gain sends nothing (retail: 107 "
                  "rows on the hero, 0 on eleven henchman bodies)", f"{sent}")
        sent.clear()
        st["agents"][202] = _koss(skills=((281, 1.0, 2.0),), skill_ready=[0.0])
        authsrv.hero_pool_gain(send, st, 202, st["agents"][202], 25, "t")
        LEDGER.ok(sent == [], "a hero whose bar carries no adrenal skill charges "
                  "nothing on the wire -- the dark rule, as for the player", f"{sent}")
        sent.clear()
        authsrv.hero_pool_clear(send, st, HERO, st["agents"][HERO], "t")
        authsrv.hero_pool_clear(send, st, 201, st["agents"][201], "t")
        LEDGER.ok(sent == [(authsrv.AGENT_ADRENALINE_CLEAR, [HERO])],
                  "and its clear: 0x00D0 [hero], the henchman's never", f"{sent}")
        sent.clear()
        authsrv.HERO_WIRE_POOLS = False
        authsrv.hero_pool_gain(send, st, HERO, st["agents"][HERO], 25, "t")
        authsrv.hero_pool_clear(send, st, HERO, st["agents"][HERO], "t")
        authsrv.hero_skill_messages(send, st, HERO, st["agents"][HERO], 322, 3.0, time.time())
        LEDGER.ok(sent == [], "--hero-silent-pools: nothing of the family goes out "
                  "(the pre-JARIN arm)", f"{sent}")
        authsrv.HERO_WIRE_POOLS = True
        # 2. the skill family at a hero cast's completion, and its recharge
        sent.clear(); _now = time.time()
        authsrv.hero_skill_messages(send, st, HERO, st["agents"][HERO], 322, 3.0, _now)
        LEDGER.ok(sent == [(authsrv.GAME_SMSG_SKILL_RECHARGE, [HERO, 322, 0, 3]),
                           (authsrv.GAME_SMSG_SKILL_ACTIVATED, [HERO, 322, 0])],
                  "a hero's cast completes as 0x00E5 [hero, skill, 0, recharge] then "
                  "0x00E3 [hero, skill, 0] (the tape's +0.56 s pair, 35 / 48)", f"{sent}")
        sent.clear()
        authsrv.hero_recharged_tick(send, st, 0)
        _early = list(sent)
        st["agents"][HERO]["hero_recharged_due"][322] = _now - 1.0
        authsrv.hero_recharged_tick(send, st, 0)
        _due = list(sent)
        authsrv.hero_recharged_tick(send, st, 0)
        LEDGER.ok(_early == [] and _due == [(authsrv.GAME_SMSG_SKILL_RECHARGED, [HERO, 322, 0])]
                  and sent == _due,
                  "0x00E6 [hero, skill, 0] once, when the recharge runs out -- not "
                  "before, not twice", f"early {_early}, due {_due}, after {sent}")
        sent.clear()
        authsrv.hero_skill_messages(send, st, 201, st["agents"][201], 322, 3.0, _now)
        LEDGER.ok(sent == [], "a henchman's cast sends none of the family", f"{sent}")
        # 3. the lock is released on the wire at the kill (JARIN-Q5)
        cmd = authsrv.hero_command(st, HERO); cmd["lock"] = 10
        sent.clear()
        authsrv.hero_locks_release(send, st, 11, 0)
        _other = list(sent)
        authsrv.hero_locks_release(send, st, 10, 0)
        LEDGER.ok(_other == [] and cmd["lock"] is None
                  and sent == [(authsrv.GAME_SMSG_HERO_LOCK_TARGET_SET, [HERO, 0])],
                  "the locked target's death clears the lock on the wire, 0x0063 "
                  "[hero, 0] (the tape's 0.57 s after the kill); another agent's "
                  "death touches nothing", f"other {_other}, sent {sent}")
        # 4. a lone hero walks to the party flag ITSELF
        st2 = _jw(); st2["agents"][HERO] = _koss(); st2["party_flag"] = (500.0, 600.0, 0)
        fp1 = authsrv.party_flag_point(st2, HERO, st2["agents"][HERO])
        st2["agents"][201] = _koss(party_slot=1, hero=None)
        fp2 = authsrv.party_flag_point(st2, HERO, st2["agents"][HERO])
        LEDGER.ok(fp1 == (500.0, 600.0) and fp2 != (500.0, 600.0),
                  "one party body: the party flag point IS the flag (the lead ended "
                  "0.0 u off it, 463.51 s); two bodies: the slot offsets, as before",
                  f"lone {fp1}, group {fp2}")
        # 5. a hero's death is the player's tick, plus its clear and its closes
        st3 = _jw(); st3["agents"][HERO] = _koss(); sent.clear()
        authsrv.kill_agent(send, st3, HERO, st3["agents"][HERO], 0, time.time(), reward=False)
        ops = [op for op, _v in sent]
        LEDGER.ok(sent[0] == (STATUS, [HERO, agents.EFFECT_DEAD])
                  and (authsrv.GAME_SMSG_AGENT_MORALE, [HERO, 85]) in sent
                  and (authsrv.AGENT_ADRENALINE_CLEAR, [HERO]) in sent
                  and (PINT, [agents.PROP_HEALTH_MAX, HERO, 85]) in sent
                  and (PINT, [agents.PROP_ENERGY_MAX, HERO, 17]) in sent
                  and sent[-1] == (FLAGS, [HERO, 8])
                  and ops.index(authsrv.GAME_SMSG_AGENT_MORALE) < ops.index(authsrv.AGENT_ADRENALINE_CLEAR)
                  and authsrv.hero_morale(st3, HERO) == 85
                  and st3["agents"][HERO]["max_health"] == 85.0,
                  "a hero's death: the status, 0x009C [hero, 85], 0x00D0 [hero], the "
                  "maxima at 85 % (prop 41 = 17, prop 42 = 85) and the flags byte 8 "
                  "LAST -- retail's 307.83 s tick; the row's maximum shrinks with it",
                  f"{[(hex(op), v) for op, v in sent]}")
        # 6. the rise: the flags byte 9 closes it and the grace window starts
        sent.clear()
        authsrv.revive_party_body(send, st3, HERO, st3["agents"][HERO], 0)
        LEDGER.ok(sent[0] == (STATUS, [HERO, 0]) and sent[-1] == (FLAGS, [HERO, 9])
                  and (PINT, [agents.PROP_HEALTH_MAX, HERO, 85]) in sent
                  and st3["agents"][HERO]["revived_at"] > 0
                  and not st3["agents"][HERO]["dead"],
                  "a party body's rise: status 0 first, the maximum KEPT at 85, "
                  "0x0026 [body, 9] last (retail 250 / the hero's 340.21 s)",
                  f"{[(hex(op), v) for op, v in sent]}")
        # 6b. the raise's energy: the signet's 25 %, a shrine's or the timer's 100 %
        _sv_en = authsrv.ENERGY
        authsrv.ENERGY = True
        import struct as _st
        _asf = lambda x: float(x) if isinstance(x, float) else _st.unpack('<f', _st.pack('<I', int(x) & 0xFFFFFFFF))[0]
        PFLT2 = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
        try:
            st3b = _jw(player_dead=True, player_died_at=time.time() - 5.0)
            authsrv.player_pools(st3b)
            sent.clear()
            authsrv.resurrect_target(send, st3b, authsrv.PLAYER_AGENT_ID, 0, HERO, 2)
            if st3b.get("player_refill_due_at"):            # the deferred arm: the fraction rides the deferral
                st3b["player_refill_due_at"] = time.time() - 0.01
                authsrv.player_refill_due(send, st3b, 0)
            _g = [v for op, v in sent if op == PFLT2 and v[0] == agents.GV_ENERGY_GAIN]
            _c = [v for op, v in sent if op == PINT and v[0] == agents.PROP_ENERGY_GAIN_CALLOUT]
            _mx = authsrv.player_energy(st3b).maximum
            _ops = [op for op, _v in sent]
            _rate_i = next(i for i, (op, v) in enumerate(sent) if op == PFLT2 and v[0] == authsrv.GV_ENERGY_REGEN)
            _gain_i = next(i for i, (op, v) in enumerate(sent) if op == PFLT2 and v[0] == agents.GV_ENERGY_GAIN)
            LEDGER.ok(len(_g) == 1 and abs(_asf(_g[0][2]) - 0.25) < 1e-6
                      and _c and _c[0][2] == int(_mx * 0.25)
                      and _rate_i < _gain_i
                      and not st3b["player_dead"],
                      "the signet raises the player at 25 % energy: [52, me, 0.25] and the "
                      "callout prop 54 = a quarter of the maximum, the rate ahead of them, "
                      "through the deferred arm too "
                      "(the tape's 602.45 s: 5 of 19; content's resurrect_energy)",
                      f"gain {_g}, callout {_c}, ops {[hex(o) for o in _ops]}")
            st3c = _jw(player_dead=True, player_died_at=time.time() - 30.0)
            authsrv.player_pools(st3c)
            sent.clear()
            authsrv.player_revive_due(send, st3c, 0)
            if st3c.get("player_refill_due_at"):
                st3c["player_refill_due_at"] = time.time() - 0.01
                authsrv.player_refill_due(send, st3c, 0)
            _g2 = [v for op, v in sent if op == PFLT2 and v[0] == agents.GV_ENERGY_GAIN]
            LEDGER.ok(len(_g2) == 1 and abs(_asf(_g2[0][2]) - 1.0) < 1e-6,
                      "the timer's rise (no party) refills to 1.0, as every shrine or timer "
                      "rise in the corpus", f"{_g2}")
            st3d = _jw(); st3d["agents"][HERO] = _koss(dead=True, died_at=time.time() - 5.0, health=0.0)
            sent.clear()
            authsrv.resurrect_target(send, st3d, HERO, 0, authsrv.PLAYER_AGENT_ID, 2)
            _g3 = [v for op, v in sent if op == PFLT2 and v[0] == agents.GV_ENERGY_GAIN and v[1] == HERO]
            LEDGER.ok(len(_g3) == 1 and abs(_asf(_g3[0][2]) - 0.25) < 1e-6
                      and not st3d["agents"][HERO]["dead"]
                      and any(op == PFLT2 and v[0] == authsrv.GV_ENERGY_REGEN and v[1] == HERO for op, v in sent),
                      "a hero raised by the signet gets its energy on the wire too -- the rate "
                      "and [52, hero, 0.25] (the shrine's [43, 30, ...] + [52, 30, 1.0] shape)",
                      f"{_g3}")
        finally:
            authsrv.ENERGY = _sv_en
        # 7. the wipe -- and the signet that pre-empts it
        st4 = _jw(player_dead=True, player_died_at=time.time() - 20.0)
        st4["agents"][HERO] = _koss(skills=((2, 3.0, 0.0),), skill_ready=[0.0])
        sent.clear()
        authsrv.player_revive_due(send, st4, 0)
        LEDGER.ok(sent == [] and st4["player_dead"],
                  "a live party body holding a resurrection: NO timer -- the signet "
                  "raises the player (F28 5 of 5; the hero's at 599.43 s)", f"{sent}")
        st4["agents"][HERO]["skills"] = ((322, 0.0, 3.0),)
        st4["agents"][HERO].update(dead=True, died_at=time.time() - 5.0)
        authsrv.player_revive_due(send, st4, 0)
        LEDGER.ok(sent == [] and st4["player_dead"],
                  "everyone down 5 s ago: not yet -- the shrine comes "
                  f"{authsrv.WIPE_RESURRECT_AFTER} s after the LAST death (the tape's "
                  "10.0 / 12.2 / 12.8 / 10.6)", f"{sent}")
        st4["agents"][HERO]["died_at"] = time.time() - 20.0
        authsrv.player_revive_due(send, st4, 0)
        ops = [op for op, _v in sent]
        _pos = st4["agents"][HERO]["pos"]
        LEDGER.ok((authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION, [authsrv.PLAYER_AGENT_ID, (1.0, 0.0), 1]) in sent
                  and (authsrv.GAME_SMSG_AGENT_UPDATE_POSITION, [authsrv.PLAYER_AGENT_ID, [500.0, 500.0], 0]) in sent
                  and (authsrv.GAME_SMSG_WORLD_REMOVE_AGENT, [HERO]) in sent
                  and authsrv.GAME_SMSG_WORLD_CREATE_AGENT in ops
                  and (authsrv.GAME_SMSG_NPC_UPDATE_WEAPONS, [HERO, 210, 0]) in sent
                  and (FLAGS, [HERO, 9]) in sent and (FLAGS, [authsrv.PLAYER_AGENT_ID, 5]) in sent
                  and (STATUS, [authsrv.PLAYER_AGENT_ID, 0]) in sent
                  and 0x01D8 not in ops
                  and ops.index(authsrv.GAME_SMSG_WORLD_REMOVE_AGENT) < ops.index(authsrv.GAME_SMSG_WORLD_CREATE_AGENT) < ops.index(authsrv.GAME_SMSG_NPC_UPDATE_WEAPONS)
                  and st4["pos"] == (500.0, 500.0) and not st4["player_dead"]
                  and not st4["agents"][HERO]["dead"]
                  and _pos == (500.0 + authsrv.HERO_BODY_OFFSET[0], 500.0),
                  "THE WIPE (340.21 s): the player faces and is placed at the shrine "
                  "(0x0025, 0x002C), the hero's body is DELETED and RE-CREATED there "
                  "with its weapons re-declared (0x0021, 0x0020, 0x006D), both rise "
                  "with the flags bytes 9 and 5, and no PARTY_DEFEATED",
                  f"{[hex(o) for o in ops]}, pos {st4['pos']}, hero {_pos}")
        authsrv.WIPE_SHRINE = False
        st5 = _jw(player_dead=True, player_died_at=time.time() - 20.0)
        st5["agents"][HERO] = _koss(dead=True, died_at=time.time() - 20.0)
        sent.clear()
        authsrv.player_revive_due(send, st5, 0)
        LEDGER.ok(not st5["player_dead"]
                  and authsrv.GAME_SMSG_AGENT_UPDATE_POSITION not in [op for op, _v in sent]
                  and st5["agents"][HERO]["dead"],
                  "--no-wipe-shrine: the timer stands the player up where it fell and "
                  "the body stays down (the pre-JARIN placeholder)",
                  f"{[hex(op) for op, _v in sent]}")
        authsrv.WIPE_SHRINE = True
        # 8. the zone carry: the stance always, the penalty into a field only
        st6 = {"char_uuid": "abc", "morale": 85, "morale_xp_bank": 40,
               "hero_cmd": {HERO: {"ai_mode": 2, "lock": None, "flag": None}},
               "hero_morale": {HERO: 85}}
        authsrv.zone_carry_store(st6)
        st7 = {"char_uuid": "abc", "map_id": 168}
        authsrv.zone_carry_apply(st7, 0)
        LEDGER.ok(st7.get("morale") == 85 and st7.get("morale_xp_bank") == 40
                  and authsrv.hero_command(st7, HERO)["ai_mode"] == 2
                  and st7.get("hero_morale") == {HERO: 85}
                  and "abc" not in authsrv.ZONE_CARRY,
                  "a zone into a FIELD carries the death penalty, its bank, the hero's "
                  "morale and the hero's stance (the tape's aiMode 2 in the next "
                  "0x0072), and the carry is consumed", f"{st7}")
        authsrv.zone_carry_store(st6)
        st8 = {"char_uuid": "abc", "map_id": 148}
        authsrv.zone_carry_apply(st8, 0)
        LEDGER.ok("morale" not in st8 and authsrv.hero_command(st8, HERO)["ai_mode"] == 2,
                  "a zone into an OUTPOST clears the penalty (0x009C 100 for both at "
                  "651.62 s) and still carries the stance", f"{st8}")
        authsrv.ZONE_CARRY_ON = False
        authsrv.zone_carry_store(st6)
        LEDGER.ok("abc" not in authsrv.ZONE_CARRY,
                  "--no-zone-carry: nothing is carried", f"{authsrv.ZONE_CARRY}")
        authsrv.ZONE_CARRY_ON = True
        # 9. the rig: retail's character block for the hero, in the tape's order
        authsrv.HERO_LEVEL = None
        authsrv.HERO_SKILLS = ((322, 0.0, 3.0), (385, 0.0, 0.0))
        authsrv.HERO_VITALS = (140, 20)
        blk = authsrv.hero_character_block(_jw(), HERO, 6)
        bops = [op for op, _v, _l in blk]
        _bar = next(v for op, v, _l in blk if op == authsrv.GAME_SMSG_SKILLBAR_UPDATE)
        U65, PFLT = authsrv.GAME_SMSG_HERO_UNNAMED_0065, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
        LEDGER.ok(bops == [authsrv.GAME_SMSG_AGENT_UPDATE_ATTRIBUTE_POINTS,
                           authsrv.GAME_SMSG_AGENT_PROFESSIONS,
                           authsrv.GAME_SMSG_SKILLBAR_UPDATE, U65, PFLT, PINT, PINT,
                           authsrv.GAME_SMSG_AGENT_MORALE, U65,
                           authsrv.GAME_SMSG_AGENT_SET_PROFESSION,
                           authsrv.GAME_SMSG_AGENT_UPDATE_ATTRIBUTES]
                  and _bar[0] == HERO and _bar[1][:3] == [322, 385, 0]
                  and blk[3][1] == [HERO, 0] and blk[4][1][:2] == [agents.GV_ENERGY_REGEN if hasattr(agents, "GV_ENERGY_REGEN") else 43, HERO]
                  and (PINT, [agents.PROP_HEALTH_MAX, HERO, 140], blk[6][2]) == blk[6]
                  and blk[7][1] == [HERO, 100],
                  "the hero's load block is the PLAYER's own, addressed to the hero: "
                  "0x0037, 0x00B7, 0x00DA (the hero's OWN bar), 0x0065 [hero, 0], the "
                  "regen 0x00A2 43, prop 41, prop 42, 0x009C, 0x0065 again, 0x00A6, "
                  "0x003A -- the tape's order at 37.73 s and 87.21 s",
                  f"{[hex(o) for o in bops]}, bar {_bar[1]}")
        authsrv.HERO_LEVEL = 3
        blk = authsrv.hero_character_block(_jw(), HERO, 6)
        LEDGER.ok([op for op, _v, _l in blk][9:11] == [PINT, authsrv.GAME_SMSG_AGENT_SET_PROFESSION]
                  and blk[9][1] == [agents.PROP_LEVEL, HERO, 3],
                  "...with prop 36 (the level) right before 0x00A6 when a level is set",
                  f"{[hex(op) for op, _v, _l in blk]}")
        _hi = agents.hero_info(6, 3, 1, 0, 243282, 245053, [322, 382, 348, 1, 385, 346, 0, 2])
        LEDGER.ok(_hi[0] == 0x0073
                  and _hi[1] == [6, 3, 1, 0, 243282, 245053, [322, 382, 348, 1, 385, 346, 2], 0, 0]
                  and len(Codec().encode("GAME_SMSG", 0x0073, _hi[1])) == 2 + 1 + 1 + 1 + 4 + 4 + 2 + 7 * 4 + 1 + 1 + 2,
                  "0x0073 HERO_INFO encodes through the real codec: [hero, level, prof, "
                  "sec, d1, d2, the hero's skills (zeros dropped, count-prefixed), 0, 0] "
                  "-- retail's own row for Koss less the empty slot",
                  f"{_hi[1]}")
        _src = inspect.getsource(authsrv)
        LEDGER.ok("if HERO_INFO and not (HERO_RIG_RETAIL and HERO_ACTIVATE):" in _src
                  and _src.index("_seq.append(agents.hero_info(")
                  < _src.index("_seq.extend(hero_character_block(state, _haid, _hid))")
                  < _src.index("_party = tuple(agents.party_build(")
                  and "if HERO_PIPELINE_FIRST or _rig_retail:" in _src
                  and _src.count("and not _rig_retail") >= 4,
                  "SOURCE: under the retail rig no 0x0074 goes out, 0x0073 HERO_INFO "
                  "(the record's creator on retail) is queued ahead of the block, the "
                  "block and 0x0072 AHEAD of the party build, the build is deferred "
                  "past the body, and the four legacy sites (vitals, attribs, bar, "
                  "the last 0x0072) stand down (--hero-rig-legacy is every rig before)",
                  f"{_src.count('and not _rig_retail')} legacy sites gated")
    finally:
        (authsrv.HERO_IDS, authsrv.PARTY_COMMANDS, authsrv.HERO_WIRE_POOLS,
         authsrv.WIPE_SHRINE, authsrv.ZONE_CARRY_ON, authsrv.DEATH_PENALTY_FORCED,
         authsrv.HERO_LEVEL, authsrv.HERO_SKILLS, authsrv.HERO_VITALS, _zc) = _sv
        authsrv.ZONE_CARRY.clear(); authsrv.ZONE_CARRY.update(_zc)


if __name__ == "__main__":
    sys.exit(main())
