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

LEDGER = checks.Ledger("agent lifetime", floor=256)


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
    section_chase()
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


def _world(dist=100.0, **over):
    """A player at the origin and one hostile `dist` units away."""
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
    for why, kill in (("dies", lambda a: a.update(dead=True)),
                      ("leaves range",
                       lambda a: a.update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0)))):
        mid = _sworld()
        _swings(mid)                                    # opens a swing
        assert mid["agents"][10]["swing_lands_at"] is not None
        kill(mid["agents"][10])
        mid["agents"][10]["swing_lands_at"] = time.time() - 1.0   # long overdue
        before = mid["player_health"]
        LEDGER.ok(not _swings(mid, n=3) and mid["player_health"] == before,
                  f"a swing in flight does not land if the swinger {why}",
                  "an overdue landing plus three ticks, and no damage -- the "
                  "pending swing has to be dropped, not merely postponed")

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


def section_chase():
    """It walks toward the player, and stops where it can reach them.

    THE BUG THIS RUNG FIXES IS ONE OF OURS. `AGGRO_RANGE` was doing two jobs --
    when a hostile NOTICES the player and when it can REACH them -- so a Hatcher
    rooted to its spawn point swung at anything within 1200 units. It hit people
    across a courtyard it never crossed. Splitting reach from notice is what makes
    the chase necessary rather than decorative: without the walk, raising the reach
    to a melee distance would simply mean nothing could ever hit anybody.

    All three constants are ours and the docstring at the call site says so.
    """
    import authsrv

    far = authsrv.ENEMY_MELEE_RANGE + 450.0

    # 1. it starts moving, announces a rate and a destination, and does NOT swing
    state = _world(dist=far)
    sent = _walk(state)
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(ops == [authsrv.GAME_SMSG_AGENT_UPDATE_SPEED,
                      authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION,
                      authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT],
              "a hostile out of reach announces a rate, a facing and a destination",
              f"{[hex(o) for o in ops]}")
    rate = [v for op, v, _l in sent
            if op == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED][0]
    LEDGER.ok(rate[0] == 10 and 0.0 < rate[1] <= agents.AGENT_MAX_MOVE_SPEED,
              "and the rate is a FRACTION inside the client's own asserted bounds",
              f"{rate} -- units/s here is the named mistake; "
              f"{authsrv.ENEMY_MOVE_RATE} x {agents.DEFAULT_RUN_SPEED} = "
              f"{authsrv.ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED:.0f} u/s")
    dest = [v for op, v, _l in sent
            if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT][0]
    LEDGER.ok(dest[0] == 10 and dest[1] == [0.0, 0.0],
              "and the destination is where the player is standing",
              f"{dest}")
    LEDGER.ok(not _swings(state),
              "and it does not swing from out there",
              f"{far:.0f} units, reach is {authsrv.ENEMY_MELEE_RANGE:.0f} -- this "
              "is the courtyard bug, and it read AGGRO_RANGE until today")

    # 2. it actually closes the distance
    state = _world(dist=far)
    before = math.hypot(*state["agents"][10]["pos"])
    _walk(state, n=3, elapsed=0.5)
    after = math.hypot(*state["agents"][10]["pos"])
    LEDGER.ok(after < before - 100.0,
              "and over three half-seconds it closes real ground",
              f"{before:.0f} -> {after:.0f} units at "
              f"{authsrv.ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED:.0f} u/s")

    # 3. IT STOPS AT REACH RATHER THAN WALKING THROUGH THE PLAYER. A long step is
    #    the interesting case: without the cap the agent overshoots to distance 0
    #    and stands inside them.
    state = _world(dist=far)
    _walk(state)                       # tick one only announces the intent
    LEDGER.ok(math.hypot(*state["agents"][10]["pos"]) == far,
              "the tick that starts the walk does not also move the agent",
              "moved_at is stamped when the walk begins, so the first step is "
              "measured from then -- an agent cannot have travelled before it set off")
    _walk(state, n=1, elapsed=30.0)
    d = math.hypot(*state["agents"][10]["pos"])
    LEDGER.ok(abs(d - authsrv.ENEMY_MELEE_RANGE) < 1.0,
              "and a huge step stops it exactly at reach, not on top of the player",
              f"{d:.1f} against a reach of {authsrv.ENEMY_MELEE_RANGE:.0f} -- "
              "uncapped, a 30 s step lands at 0 and the agent stands inside them")
    state["agents"][10]["skills"] = ()       # the swing path, not the skill path
    LEDGER.ok(bool(_swings(state)),
              "and having arrived, it can swing",
              "the walk is only worth anything if the fight starts at the end of it")

    # 4. the stop is an ARRIVAL, never a zero rate -- agent_update_speed refuses
    #    anything under AGENT_MIN_MOVE_SPEED and that refusal is a ValueError on
    #    the world tick.
    stop = _walk(state, n=2)
    stop_ops = [op for op, _v, _l in stop]
    LEDGER.ok(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED not in stop_ops,
              "stopping never sends a speed message",
              f"{[hex(o) for o in stop_ops]} -- speed 0.0 is below the client's own "
              f"floor of {agents.AGENT_MIN_MOVE_SPEED} (AgAgent.cpp:2366) and "
              "agent_update_speed raises on it")
    LEDGER.ok(len([o for o in stop_ops
                   if o == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT]) == 1,
              "and it announces its arrival exactly once, not every tick",
              f"{len(stop_ops)} message(s) over two ticks standing still")

    # 5. the destination is not re-announced every tick while chasing
    state = _world(dist=far)
    _walk(state)                                   # first announcement
    quiet = _walk(state, n=4, elapsed=0.05)
    LEDGER.ok(not [op for op, _v, _l in quiet
                   if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT],
              "a stationary player is not re-announced on every tick",
              f"{len(quiet)} message(s) over four ticks -- 20 a second is what "
              "'tell the client where to go' becomes if this is not gated")
    state["pos"] = (0.0, authsrv.ENEMY_DEST_RESEND + 50.0)
    moved = _walk(state, elapsed=0.05)
    LEDGER.ok(bool([op for op, _v, _l in moved
                    if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT]),
              "but a player who has walked far enough IS re-announced",
              f"moved {authsrv.ENEMY_DEST_RESEND + 50.0:.0f} units, threshold is "
              f"{authsrv.ENEMY_DEST_RESEND:.0f}")

    # 6. the refusals
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

    # 7. A WALL STOPS IT. pathmap.clip is sampled rather than solved, and it is
    #    the whole of our collision story -- pathmap.route is an A* and is NOT
    #    wired in, so an agent meets a wall and waits there.
    state = _world(dist=900.0)
    state["pathmap"] = _Wall()
    _walk(state)                       # announce, then walk
    _walk(state, n=4, elapsed=1.0)
    x = state["agents"][10]["pos"][0]
    LEDGER.ok(state["pathmap"].asked >= 1 and x >= 400.0,
              "a hostile is stopped by the pathmap rather than walking through it",
              f"x={x:.0f} against a wall at 400, clip asked "
              f"{state['pathmap'].asked} time(s)")


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

    # the fixture puts the agent due EAST of the player, so it must look WEST
    state = _world(dist=600.0)
    r = rots(_walk(state))
    LEDGER.ok(len(r) == 1 and r[0][0] == 10,
              "setting off, the agent announces a facing for itself",
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
    r = rots(_walk(north))
    LEDGER.ok(abs(angle_of(r[0]) + math.pi / 2.0) < 1e-5,
              "a player due north of the agent emits -pi/2, not +pi/2 or 0",
              f"{angle_of(r[0]):.5f} -- bearing +pi/2, emitted -pi/2. This is the "
              "check that separates atan2(y, x) from atan2(x, y), which the "
              "due-east case above cannot: swapping the arguments emits +pi here")

    # 2. it is NOT re-announced when nothing has changed
    quiet = rots(_walk(state, n=5, elapsed=0.02))
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
    wrapped = rots(_walk(state, n=3, elapsed=0.02))
    LEDGER.ok(not wrapped,
              "and a facing that crosses the +/-pi seam is still 'unchanged'",
              f"{len(wrapped)} -- the shortest way round from +3.1416 to -3.1383 "
              "is 0.003 rad, not 6.28. Unwrapped, this agent re-announces on every "
              "tick forever, and this check goes red when the wrap is removed")

    # 4. a real turn IS announced
    state["pos"] = (0.0, 900.0)
    turned = rots(_walk(state, n=1, elapsed=0.02))
    LEDGER.ok(len(turned) == 1,
              "but a player who has actually moved round does get a new facing",
              f"{len(turned)}")

    # 5. standing exactly on the player has no direction, and atan2(0, 0) is 0.0
    #    rather than an error -- so an ungurded version silently means "face east"
    # CALLED DIRECTLY, because enemy_move_tick never gets there: an agent standing
    # on the player is inside melee range, so the chase returns before facing is
    # considered and the check passed without executing the code it names.
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
    raw = rots(_walk(bits_world))[0]
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

    def dmg_floats(sent):
        return [struct.unpack("<f", struct.pack("<I", v[-1]))[0]
                for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]

    # 1. the opening cast
    state = _world()
    sent = _swings(state)
    casts = cast_msgs(sent)
    LEDGER.ok(len(casts) == 1 and casts[0][1][1] == 10
              and casts[0][1][2] == authsrv.PLAYER_AGENT_ID
              and casts[0][1][-1] == authsrv.ENEMY_SKILL_BAR[0][0],
              "a hostile opens with its SKILL, named on the TARGETED channel "
              "at the player (the form follows the target, ANIMREF-R1 sec.2)",
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
    LEDGER.ok(not fl,
              "slot 0 lands NO damage -- its scale is Healing, not damage",
              f"{fl} -- 276 Restore Condition heals 10-70 (GWW). The old flat "
              f"fraction made a heal hurt the player; dealing its magnitude AS "
              f"damage would have been worse, not better")
    # The damage skill on the same bar, to prove the path is not simply dead.
    holy = authsrv.skill_damage(312, authsrv.ENEMY_SKILL_RANK)
    LEDGER.ok(holy is not None and holy[1] == "standalone"
              and holy[0] == 46,
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
    busy = _world()
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
    plain = _world()
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

    # 6. a cast in flight does not survive its caster, the same as a swing
    for why, kill in (("dies", lambda a: a.update(dead=True)),
                      ("leaves range",
                       lambda a: a.update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0)))):
        mid = _world()
        _swings(mid)
        assert mid["agents"][10]["cast_lands_at"] is not None
        kill(mid["agents"][10])
        mid["agents"][10]["cast_lands_at"] = time.time() - 1.0
        before = mid["player_health"]
        LEDGER.ok(not _swings(mid, n=3) and mid["player_health"] == before,
                  f"a cast in flight does not land if the caster {why}",
                  "an overdue cast plus three ticks and no damage")

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
    kill_state = _world()
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
    bar = _world()
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
    rr = _world()
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
    wr = _world()
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
    sim = _world()
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
    dup = _world()
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
    LEDGER.ok("skills" in inspect.getsource(authsrv.spawn_enemy),
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
         "reach. Refuted from both sides at once: ArenaNet's own models strike "
         "from ~65, ~599 and ~706 units, so no single number is right "
         "(studies/monsterai 3.3)"),
        ("ENEMY_HIT_FRACTION", 0.10, "OURS", "damage per swing"),
        ("HIT_FRACTION", 0.15, "OURS",
         "the FALLBACK for a swing with no readable weapon, and nothing more "
         "since 2026-08-20. The player's swing is the equipped weapon's own "
         "damage range now -- see PLAYER_SWING_DAMAGE below, which is the "
         "first number in this block that is not ours"),
        ("REVIVE_AFTER", 8.0, "OURS", "how long an agent stays dead"),
        ("PLAYER_REVIVE_AFTER", 10.0, "OURS",
         "a timer, not a resurrection shrine. n=0 player deaths in the corpus"),
        ("ENEMY_MOVE_RATE", 0.75, "OURS",
         "216 u/s. NEVER sent to a hostile in the corpus -- ArenaNet's hostiles "
         "take 0.2778, 0.3333, 0.3472 and 1.0 (studies/monsterai 3.4)"),
        ("ENEMY_DEST_RESEND", 120.0, "OURS", "bandwidth, not mechanics"),
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
    except Exception as ex:                                    # pragma: no cover
        # NAMED, not swallowed. The first version of this handler said "no
        # readable client build" for every failure and its actual cause was a
        # method name that does not exist -- a skip that lies about WHY is worse
        # than a red check, because it reads as an environment problem forever.
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
    with open(os.path.join(os.path.dirname(os.path.dirname(HERE)),
                           "schema", "messages.json"), encoding="utf-8") as f:
        catalog = json.load(f)["channels"]["GAME_SMSG"]["messages"]
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
    """Every send site in authsrv.py, against the catalog's field count.

    THE PINS ABOVE PROTECT FIFTEEN OPCODES. authsrv.py declares SIXTY-TWO, and
    the other forty-seven have no pin anywhere in the suite. This is the cheap
    control that reaches them, and it is deliberately not a second table of
    literals: it walks authsrv.py's own `send(GAME_SMSG_X, [...])` sites, counts
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
    import json
    import authsrv

    with open(authsrv.__file__, encoding="utf-8") as f:
        src = f.read()
    with open(os.path.join(os.path.dirname(os.path.dirname(HERE)),
                           "schema", "messages.json"), encoding="utf-8") as f:
        catalog = json.load(f)["channels"]["GAME_SMSG"]["messages"]

    def fields_at(opcode):
        entry = catalog.get(str(opcode))
        return None if entry is None else len(entry["fields"]) - 1

    # every `send(GAME_SMSG_*, [ ... ])` whose payload is a literal list
    arity = {}
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "send" and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id.startswith("GAME_SMSG_")
                and isinstance(node.args[1], ast.List)):
            arity.setdefault(node.args[0].id, set()).add(len(node.args[1].elts))
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
    failures = probes.check_encodable(quiet=True)
    LEDGER.ok(failures == 0,
              "every step of every probe encodes",
              f"{failures} failures -- an unencodable step is only discovered "
              f"by launching a client, which is the most expensive way to find "
              f"a typo in this repo")

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
    with open(authsrv.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    default = None
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


if __name__ == "__main__":
    sys.exit(main())
