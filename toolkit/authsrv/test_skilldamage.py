"""Skill damage: the client's own numbers, at the player's own rank.

Step 8 of studies/combat/PLAN.md. What it replaced was
`ENEMY_SKILL_FRACTION = 0.25` -- a flat quarter of the player's maximum for
every skill on the bar, admitted invention -- with the skill's own scale
endpoints interpolated by the client's own formula.

THE PART THAT MATTERS MOST HERE IS THE PART THAT REFUSES. The client's table
gives a magnitude and does NOT say what it means: `scale0/scale15` is
"+ Damage" on Power Attack and "Healing" on Restore Condition, and `type_code`
does not discriminate (a Spell can heal or harm). Three of the four skills on
our own enemy's bar are not damage. So a decode that read endpoints and dealt
them would have had the enemy "damaging" the player with a heal for 10-70 and
an enchantment for 40-200 -- an invention wearing a measurement's clothes, and
worse than the flat fraction it replaced because it would look principled.

The meaning therefore comes from GWW's own `{{Skill progression}}` variable
names, quoted verbatim into content/world.toml with a citation per skill, and
the server models only the labels it names in SCALE_MEANS_DAMAGE. Section 3 is
the one that would catch a regression there.

Section 5 pins the rounding tie-break, which is UNRESOLVED in the client
(studies/combat 8c: its CRT helper adjusts by +/-1.0, not the textbook +/-0.5,
and half-up vs half-even was not settled). We chose half-up. That choice cannot
currently bite, and this file proves it rather than assuming it: no skill the
server resolves lands on a .5 at any rank 0..15.
"""

import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "schema"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import effects  # noqa: E402

# FLOOR 25, counted from a green run on 2026-08-15 rather than guessed -- and
# the guard caught the guess: this said 26 first and the run reported
# "ONLY 25 OF A DECLARED FLOOR OF 26 CHECKS RAN". 4 endpoints (S1) + 3 shape
# (S2) + 8 meaning (S3: 3 modelled, 5 refused) + 4 bitfield (S4) + 1 tie-break
# (S5) + 3 rank chain (S6) + 2 wire (S7). Nothing here is conditional: every
# section reads content rows that ship in the repo plus the vault overlay, so
# a short run means a section stopped rather than passed.
# SKILLS-HN +4 (44), SKILLS-FA +13 (57: 7 model + 6 corpus), each from its
# green run. Section 12 needs the live corpus and declares a skip without it.
LEDGER = checks.Ledger("skill damage", floor=97)  # 2026-09-27 the D6 review's repair +5 (sec.11c: the death batch order re-pinned, the payoff killing its own wearer (M5), the payoff killing the adjacent foe (M6), a second 179 arming no second payoff (R34-4); sec.11d: the dead target (R34-2); sec.12c rewritten per tape with the confirming-copy arm (EV-3, +1 there and the two exact pins re-scored on the witness)): MEASURED from the green run, 109 checks with the overlay = 104 + 5, floor 92 -> 97; 2026-09-27 SKILLS-HX +18 (sec.11c Incendiary Bonds 9, sec.11d Mind Burn 6, sec.12c the hexjoin lock 3): MEASURED from the green run, 104 checks with the overlay = 86 + 18, floor 74 -> 92; 2026-09-23 SKILLS-OB +6 (sec.11b: whose connection it is, four bare; sec.12: the JARIN player, the pair onto it); 2026-09-23 SKILLS-LT +1 (sec.3: Hamstring inflicts through the bonus slot); 2026-09-17 SKILLS-LR +4 (the location roll: three unit, one corpus); 2026-09-16 RUN-SKILLS-RB +2 (section 13, the converted word); 2026-09-16 SLICE-F47 +1 (the penalty split in whole points); 2026-09-14 HEAL-INT +1, ZEROWORD +1;   # MANTID-S +1: the player-side control beside the foe-side refusal
check = LEDGER.ok


def main():
    import agents
    import authsrv

    print("1. the endpoints are the client's, exactly, at rank 0 and rank 15")
    # Both endpoints must reproduce or the interpolation is not the client's.
    # These four pairs are also the ones GWW independently lists, so a match is
    # two witnesses rather than our decoder agreeing with itself.
    for skill_id, lo, hi, name in ((312, 10, 55, "Holy Strike"),
                                   (322, 10, 40, "Power Attack"),
                                   (323, 10, 40, "Desperation Blow"),
                                   (276, 10, 70, "Restore Condition")):
        got0 = authsrv.skill_scale_value(skill_id, 0)
        got15 = authsrv.skill_scale_value(skill_id, 15)
        check(got0 == lo and got15 == hi,
              f"{name} ({skill_id}) scales {lo} -> {hi}",
              f"rank 0 = {got0}, rank 15 = {got15}")

    print("\n2. the shape between them is the client's formula")
    # value(rank) = max(0, round(lo + (hi-lo)*rank/15.0)), measured at
    # 0x005A8920 with the divisor a literal double 15.0 (studies/combat 8c).
    # Holy Strike's span is 45 over 15, so every rank is an exact integer and
    # the whole ladder is checkable without touching the tie-break.
    ladder = [authsrv.skill_scale_value(312, r) for r in range(16)]
    check(ladder == [10 + 3 * r for r in range(16)],
          "Holy Strike walks 10, 13, 16 ... 55 -- 3 per rank, exactly",
          f"{ladder}")
    # NO UPPER CLAMP: the client's interpolator never compares rank against 15,
    # so ranks above it extrapolate. Measured, and worth pinning because a
    # "sensible" clamp is exactly what someone would add.
    check(authsrv.skill_scale_value(312, 20) == 70,
          "and rank 20 EXTRAPOLATES to 70 rather than saturating at 55",
          "the interpolator has no upper bound on rank -- ranks above 15 are "
          "reachable in retail with runes and headgear")
    check(authsrv.skill_scale_value(312, 0) >= 0,
          "the floor at zero is ArenaNet's own assert, ConstSkill:3769")

    print("\n3. what a scale MEANS is sourced, and non-damage is refused")
    # The three the server models...
    for skill_id, mode, name in ((312, "standalone", "Holy Strike"),
                                 (322, "additive", "Power Attack"),
                                 (323, "additive", "Desperation Blow")):
        got = authsrv.skill_damage(skill_id, 15)
        check(got is not None and got[1] == mode,
              f"{name} is a {mode} damage skill",
              f"{got} -- GWW calls its progression var "
              f"{agents.WORLD.get('skill_effect', str(skill_id))['scale_means']!r}")
    # ...and the ones it must NOT, which is the whole point.
    for skill_id, means, name in ((276, "Healing", "Restore Condition"),
                                  (289, "+ Maximum health", "Vital Blessing"),
                                  (318, "+ Maximum health", "Defy Pain")):
        row = agents.WORLD.get("skill_effect", str(skill_id))
        check(authsrv.skill_damage(skill_id, 15) is None
              and row["scale_means"] == means,
              f"{name} deals NO damage -- its scale is {means!r}",
              "returning None rather than 0, so a caller must decide what an "
              "unmodelled skill means instead of silently dealing nothing")
    # SKILLS-LT (2026-09-23, studies/skills 54.5 / 55): the two `scale_means =
    # "Duration"` labels were INERT -- nothing compares a means against
    # "Duration"; an episode's duration is the skills table's -- and skilldesc
    # refereed Battle Rage's a CONFLICT (its flat 33 is the movement speed).
    # Both rows keep their wiki provenance and carry no label.
    for skill_id, name in ((253, "Scourge Sacrifice"), (317, "Battle Rage")):
        row = agents.WORLD.get("skill_effect", str(skill_id))
        check(authsrv.skill_damage(skill_id, 15) is None
              and "scale_means" not in row and "bonus_scale_means" not in row,
              f"{name} deals NO damage and its row carries no label at all -- "
              f"the inert 'Duration' is gone", dict(row))
    # And Hamstring's label moved to the slot the client numbers: args = 4
    # (bonus only), Crippled 3..15 in the BONUS slot, %str2% in the template.
    # Under "Crippled duration" on `scale_means` the server inflicted nothing.
    row = agents.WORLD.get("skill_effect", "320")
    check(authsrv.skill_damage(320, 15) is None and "scale_means" not in row
          and row.get("bonus_scale_means") == "Crippled"
          and authsrv.skill_condition(320, 0) == (481, 3.0)
          and authsrv.skill_condition(320, 15) == (481, 15.0),
          "Hamstring deals NO damage; its Crippled rides the BONUS slot, 3 s at "
          "rank 0 and 15 s at rank 15 (481 = Crippled)",
          (dict(row), authsrv.skill_condition(320, 0), authsrv.skill_condition(320, 15)))

    print("\n4. a disabled set is refused, not read")
    # Rush's scale slot holds 25 -- the "move 25% faster" in its description --
    # with its scale bit CLEAR. Reading endpoints without honouring
    # skill_arguments invents a progression the game never draws.
    for skill_id, name in ((319, "Rush"), (317, "Battle Rage"),
                           (253, "Scourge Sacrifice")):
        raised = False
        try:
            authsrv.skill_scale_value(skill_id, 10)
        except ValueError:
            raised = True
        check(raised, f"{name}'s scale set is disabled and REFUSES")
    check(agents.WORLD.get("skills", "319")["scale0"] == 25,
          "and Rush's slot really does hold 25 -- a constant, not a floor",
          "which is what makes it the discriminator: a decode ignoring the "
          "bitfield returns a plausible 25 here instead of refusing")

    print("\n5. the unresolved tie-break cannot bite what we ship")
    # studies/combat 8c left half-up vs half-even open. Prove it is moot for
    # every skill the server can resolve, rather than assuming it.
    ties = []
    for row_id in sorted(agents.WORLD.rows("skill_effect")):
        try:
            lo = int(agents.WORLD.get("skills", str(row_id))["scale0"])
            hi = int(agents.WORLD.get("skills", str(row_id))["scale15"])
        except Exception:                                      # noqa: BLE001
            continue
        for rank in range(16):
            exact = lo + (hi - lo) * rank / 15.0
            if abs(exact - int(exact) - 0.5) < 1e-9:
                ties.append((row_id, rank, exact))
    check(not ties,
          "no skill in the effect table lands on a .5 at any rank 0..15",
          f"{ties} -- so half-up vs half-even changes nothing we send, and the "
          f"client's +/-1.0 CRT adjustment stays an open question that costs "
          f"us nothing today")

    print("\n6. the player's rank drives the player's damage")
    # THE CHAIN STEP 7 AND STEP 8 EXIST TO JOIN: the skill record names its
    # attribute, the attribute is an s_attrib index, and the rank comes from
    # the same content row 0x003A is built from. Before this, `2 * rank` was 0.
    # SLICE-H7 (2026-09-13): the shipped ranks became a hammer warrior's --
    # Strength 9, Tactics 6 (Hammer Mastery 12). The two locks follow the
    # content row rather than a literal, so the claim they make -- the RANK is
    # what separates two identical tables -- survives the next re-spec too.
    _ranks = {int(a): int(r) for a, r in agents.WORLD.get("player", "attributes")["ranks"]}
    check(authsrv.player_rank_for_skill(322) == _ranks[17]
          and authsrv.player_rank_for_skill(323) == _ranks[21]
          and _ranks[17] != _ranks[21],
          f"Power Attack reads Strength ({_ranks[17]}), Desperation Blow reads "
          f"Tactics ({_ranks[21]})",
          "same scale endpoints, different attributes -- so the ranks are what "
          "separate them")
    pa = authsrv.skill_damage(322, authsrv.player_rank_for_skill(322))
    db = authsrv.skill_damage(323, authsrv.player_rank_for_skill(323))
    _want = lambda r: 10 + round(30 * r / 15)
    check(pa[0] == _want(_ranks[17]) and db[0] == _want(_ranks[21]),
          f"so Power Attack adds {_want(_ranks[17])} and Desperation Blow adds "
          f"{_want(_ranks[21])}",
          f"{pa} vs {db} -- identical 10->40 tables, apart because the ranks "
          f"differ. This is what 'the server models no attribute ranks' cost us")
    check(authsrv.player_rank_for_skill(312) == 0,
          "and a Warrior has rank 0 in Smiting Prayers -- correct, not missing",
          "Holy Strike is a Monk skill; the player has no rank in its attribute")

    print("\n7. the bonus reaches the wire as ONE damage number")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    agent = {"name": "t", "dead": False, "last_hit": 0.0,
             "max_health": 1000.0, "health": 1000.0, "pos": (0.0, 0.0)}
    state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
    authsrv.hit_enemy(send, state, 10, 0, bonus_damage=34.0)
    dmg = [v for op, v, _l in sent
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
           and v[0] == agents.PROP_DAMAGE]
    check(len(dmg) == 1,
          "a skill's '+ Damage' rides the swing as one message, not two",
          f"{len(dmg)} damage message(s) -- GWW writes Power Attack as "
          f"'+ Damage', a bonus on the attack it rides; two messages would "
          f"draw two numbers on screen for one swing")
    # RED FROM 2026-08-20 UNTIL THIS LINE CHANGED, and the reason is worth more
    # than the check. This used to read `base = 1000.0 * authsrv.HIT_FRACTION`
    # -- a flat 15% of the target's pool, which is what `hit_enemy` dealt when
    # this test was written. The weapon-damage arc replaced that with the
    # HAMMER'S OWN 3-5 range read off the item ArenaNet sends, so `HIT_FRACTION`
    # is now only the fallback for a swing with no weapon, and this check was
    # pinned to a constant the code it tests no longer reads. THE SAME DEFECT
    # WAS FOUND AND FIXED IN `test_guards` THE SAME DAY and this copy of it was
    # missed -- which is the argument for running the whole suite after a change
    # to a shared damage path, not the tests whose names sound related.
    #
    # A RANGE RATHER THAN A NUMBER, because the roll is real: `hit_enemy` draws
    # randint(3, 5) and nothing here seeds it. Asserting the range is what this
    # check is actually for -- that the bonus is added to the swing ONCE and
    # lands in the target's bookkeeping, not that the swing is any particular
    # number, which section 6 already pins from the other side.
    lo, hi = authsrv.PLAYER_SWING_DAMAGE
    dealt = 1000.0 - agent["health"]
    check(lo + 34.0 <= dealt <= hi + 34.0,
          f"and the bookkeeping is one swing ({lo}-{hi}) plus the bonus 34",
          f"health {agent['health']}, so {dealt:.0f} dealt against the "
          f"{lo + 34:.0f}-{hi + 34:.0f} this path can produce. The weapon's "
          f"range is the client's own tooltip number (identifier 584); the "
          f"roll inside it is ours")

    print("\n8. the OTHER two directions a cast can resolve (2026-08-20)")
    # HEALING, which this server had no way to express until the corpus was
    # asked which property carries it. agents.GV_HEALTH_GAIN holds the
    # measurement: on 0x00A3, property 16 is negative 1251 of 1251 and 17 is
    # negative 243 of 243, both self-directed 0 of 1501; property 55 is
    # POSITIVE 502 of 506 and SELF-DIRECTED 454 of 506.
    check(authsrv.skill_heal(1, 1) == 88,
          "Healing Signet heals 88 at Tactics 1, from GWW's `Heal` 82..172",
          f"{authsrv.skill_heal(1, 1)} -- the same interpolation the damage "
          f"side uses, on a label sourced per skill rather than guessed from "
          f"the type")
    check(authsrv.skill_damage(1, 1) is None,
          "and it deals no DAMAGE -- a heal is a direction, not a sign flip",
          "`Heal` is not in SCALE_MEANS_DAMAGE, so the damage path returns "
          "None rather than dealing 88 to the caster")
    check(authsrv.skill_heal(322, 12) is None,
          "CONTROL: Power Attack heals nothing",
          "its label is `+ Damage`; a heal that fired on every skill with a "
          "scale would pass the check above and fail this one")

    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"player_health": 40.0, "player_energy": 50.0, "agents": {}}
    landed = authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                                authsrv.PLAYER_AGENT_ID, 88, 0)
    heals = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
             and v[0] == agents.GV_HEALTH_GAIN]
    check(len(heals) == 1 and heals[0][1] == heals[0][2],
          "the heal goes out SELF-DIRECTED, target == cause",
          f"{heals[0][:3] if heals else heals} -- which is the shape 454 of "
          f"retail's 506 property-55 events have, and 0 of its 1501 damage "
          f"events do")
    check(authsrv._f32_of(heals[0][3]) > 0,
          "and POSITIVE, where damage on the same channel is negative",
          f"{authsrv._f32_of(heals[0][3]):+.4f} -- `_damage_fraction` sends "
          f"-frac, which is retail's convention 1251 times over")
    check(landed == 60.0 and state["player_health"] == 100.0,
          "an 88 heal on a 40/100 bar lands 60 -- CLAMPED, not overflowed",
          f"landed {landed}, health {state['player_health']}. The client "
          f"asserts `fraction <= 1.0f` at CharPool.cpp:84 and that assert only "
          f"fires in the POSITIVE direction, so this is the first thing this "
          f"server sends that can actually reach it")
    # HEAL-INT (2026-09-14): a fractional heal goes out and lands as WHOLE
    # points, truncated -- retail's property-55 words are 83 of 85 exact over
    # the taker's maximum, the same shape as its damage. 70.4 (an 88 under a
    # Deep Wound's x0.8) is 70 on the wire (f32(0.70) = 0x3F333333) and 70 in
    # the books; nothing rounds it to 71.
    sent_i = []
    send_i = lambda op, vals, label="", quiet=False: sent_i.append((op, vals, label))
    state_i = {"player_health": 10.0, "player_energy": 50.0, "agents": {}}
    landed_i = authsrv.heal_agent(send_i, state_i, authsrv.PLAYER_AGENT_ID,
                                  authsrv.PLAYER_AGENT_ID, 70.4, 0)
    heals_i = [v for op, v, _l in sent_i
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
               and v[0] == agents.GV_HEALTH_GAIN]
    check(len(heals_i) == 1 and heals_i[0][3] == 0x3F333333
          and landed_i == 70.0 and state_i["player_health"] == 80.0,
          "a 70.4 heal is 70 on the wire (f32(0.70) = 0x3F333333) and 70 in the "
          "books -- whole points, truncated (HEAL-INT)",
          f"wire {[hex(v[3]) for v in heals_i]}, landed {landed_i}, health "
          f"{state_i['player_health']}")
    # SKILLS-HN (studies/skills 42). This check used to pin the OPPOSITE --
    # "a heal on a FULL bar sends nothing at all ... overheal is silent in
    # retail too, no green number appears" -- and both halves were a
    # reconstruction: retail sends property 55 onto full pools (healjoin.py
    # P4, 46 witnesses), and the number is blue, drawn from the 55 alone.
    before = len(sent)
    check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                             authsrv.PLAYER_AGENT_ID, 50, 0) == 0.0
          and len(sent) == before + 1
          and abs(authsrv._f32_of(sent[-1][1][3]) - 0.5) < 1e-6
          and state["player_health"] == 100.0,
          "a heal on a FULL bar still goes out, carrying the skill's own "
          "amount (0.5 of the pool), lands 0 and moves the book nowhere",
          f"sent {len(sent) - before}, fraction "
          f"{authsrv._f32_of(sent[-1][1][3]) if len(sent) > before else None}, "
          f"health {state['player_health']} -- WIKI (GWW 'Heal'): the blue "
          f"number 'is shown even when no health are actually gained'")
    state["player_health"] = 70.0
    before = len(sent)
    check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                             authsrv.PLAYER_AGENT_ID, 50, 0) == 30.0
          and abs(authsrv._f32_of(sent[-1][1][3]) - 0.5) < 1e-6
          and state["player_health"] == 100.0,
          "a PARTIAL overheal (50 onto 70/100) sends 0.5 -- the amount, not "
          "the 30 that landed -- and the book clamps at the pool",
          f"fraction {authsrv._f32_of(sent[-1][1][3])}, health "
          f"{state['player_health']} (RECONSTRUCTION for the partial case: "
          f"the corpus cannot see a pool, only that full ones get the amount)")
    state["player_health"] = 40.0
    before = len(sent)
    check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                             authsrv.PLAYER_AGENT_ID, 250, 0) == 60.0
          and abs(authsrv._f32_of(sent[-1][1][3]) - 1.0) < 1e-6,
          "a heal bigger than the whole pool is capped at 1.0 on the wire",
          "`_fraction` refuses above 1.0 (CharPool.cpp:84) and retail's "
          "largest 55 is 0.652, so this branch has no witness either way")
    state["player_health"] = 100.0
    authsrv.OVERHEAL_NUMBER = False
    try:
        before = len(sent)
        check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                                 authsrv.PLAYER_AGENT_ID, 50, 0) == 0.0
              and len(sent) == before,
              "--no-overheal-number (the known-bad arm): a full bar sends "
              "nothing, as before 2026-09-09")
        state["player_health"] = 70.0
        check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                                 authsrv.PLAYER_AGENT_ID, 50, 0) == 30.0
              and abs(authsrv._f32_of(sent[-1][1][3]) - 0.3) < 1e-6,
              "and the partial case shrinks the wire to what landed (0.3)")
    finally:
        authsrv.OVERHEAL_NUMBER = True
        state["player_health"] = 100.0

    print("\n9. a SPELL does not swing a hammer, and its damage is its own")
    # BOTH HALVES WERE WRONG UNTIL 2026-08-20 and the run is what showed it
    # (`20260820T185518`): casting Faintheartedness produced
    # `attack_started: player swings at 10` and 5 points of hammer damage, and
    # Flare -- whose own 20 fire damage was decoded and sitting right there --
    # dealt the same 5, because cast_tick read only the "additive" mode.
    check(authsrv._is_attack_skill(322) and not authsrv._is_attack_skill(194)
          and not authsrv._is_attack_skill(135),
          "the type column says which skills ride a weapon swing",
          "Power Attack is type 14 and Flare and Faintheartedness are not. "
          "All 199 attacks in the corpus carry target byte 5, which is the "
          "same column agreeing")
    check(authsrv.skill_damage(194, 0) == (20, "standalone"),
          "Flare's own damage is 20 at rank 0, mode `standalone`",
          "GWW var1 `Fire damage` 20..65, client scale 20..65")

    sent = []
    ag = {"name": "t", "dead": False, "last_hit": 0.0, "max_health": 100.0,
          "health": 100.0, "pos": (0.0, 0.0), "armor_rating": 3.0}
    state = {"agents": {10: ag}, "pos": (0.0, 0.0)}
    authsrv.hit_enemy(send, state, 10, 0, exact=20.0, swing=False,
                      label="skill 194")
    check(ag["health"] == 80.0,
          "`exact` deals exactly that much -- no roll, no armour, no critical",
          f"{ag['health']}/100. The weapon path would have rolled 3-5 and "
          f"scaled it; a spell's number is the skill's own")
    starts = [v for op, v, _l in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
              and v[0] == agents.GV_ATTACK_STARTED]
    check(not starts and len(sent) == 1,
          "and it sends ONE message -- no attack_started, no melee_finished",
          f"{len(sent)} message(s). Those two name the beginning and end of a "
          f"SWING; a spell never began one")

    print("\n10. and a skill can inflict a CONDITION -- the join isle asked for")
    # studies/isle established that a condition's duration comes from the
    # INFLICTING skill (Burning's own endpoints are 3/3 and retail sends it at
    # 9.0). The other half was which condition and from where, and both are
    # per-skill data we already carry: GWW's variable NAMES it, the client's
    # bonus slot carries the seconds, and the bitfield picked the slot.
    got = authsrv.skill_condition(382, 3)
    check(got == (478, 9.0),
          "Sever Artery inflicts Bleeding (478) for 9 s at Swordsmanship 3",
          f"{got} -- GWW gives ONE variable, `Bleeding` 5..25, and the client "
          f"carries 5..25 in the BONUS slot with skill_arguments = 4. The "
          f"bitfield picked the slot before the wiki was read")
    check(effects.condition_id("Bleeding") == 478
          and effects.condition_id("Health degeneration") is None,
          "the label is the join key, and a non-condition label maps to None",
          "`Health degeneration` is a real progression variable (it is "
          "Faintheartedness's) and it is not a condition. Mapping it to the "
          "nearest one is exactly the guess this refuses")
    check(authsrv.skill_condition(135, 0) is None
          and authsrv.skill_condition(322, 12) is None,
          "CONTROL: a hex with a bonus slot and an attack with none inflict none",
          "Faintheartedness's bonus slot holds `Health degeneration` 0..3 with "
          "its bit SET -- a live slot whose label is not a condition, which is "
          "the case a label-blind reading would get wrong")

    sent = []
    state = {"agents": {10: dict(ag, health=100.0)}, "pos": (0.0, 0.0)}
    ep = authsrv.apply_condition(send, state, 10, 478, 9.0, 3, 0, 382)
    check(ep is not None and sent
          and not [1 for op, _v, _w in sent if op == effects.OP_EFFECT_APPLY]
          and sent[0][0] == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
          and state.get("effect_list_suppressed") == 1,
          "MANTID: on a FOE no 0x0042 goes out -- the status word carries the "
          "condition (retail: 0 of 369 effect-list messages name anyone but "
          "the player)", f"{[(hex(op), v) for op, v, _w in sent][:3]}")
    sent = []
    state = {"agents": {}, "pos": (0.0, 0.0), "player_health": 100.0}
    authsrv.player_pools(state)
    ep = authsrv.apply_condition(send, state, authsrv.PLAYER_AGENT_ID, 478,
                                 9.0, 3, 0, 382)
    check(ep is not None and sent
          and sent[0][0] == effects.OP_EFFECT_APPLY
          and sent[0][1][1] == 478,
          "and on the PLAYER it goes out as an ordinary 0x0042 naming the "
          "CONDITION's id",
          f"{sent[0][1] if sent else sent} -- not the inflicting skill's. "
          f"That is what retail carries: the corpus's six condition applies "
          f"name 480 and 481, never the skill that caused them")

    print("\n11. an INCOMING fire spell respects the player's armour: ONE rating, "
          "ELEMENTAL, no location roll (SKILLS-FA)")
    # 39.5 named this the one real gap in the enemy's skill path and 39.6 left
    # it unbuilt because GWW is ambiguous about WHICH rating a spell scales
    # against. studies/skills 43 settled the shape on retail's wire
    # (spellhitjoin.py, section 12 below): one caster + one skill + one
    # target is one value, every pair. The unit checks here are the model;
    # the corpus check is the evidence.
    elem = [authsrv.player_armour_at(k, physical=False)
            for k, _w in authsrv.HIT_LOCATION_ODDS]
    phys = [authsrv.player_armour_at(k, physical=True)
            for k, _w in authsrv.HIT_LOCATION_ODDS]
    check(len(set(elem)) == 1 and elem[0] == 25.0 and len(set(phys)) == 1
          and phys[0] == 45.0,
          "the five pieces read 25 elemental and 45 physical, all alike",
          f"elemental {elem}, physical {phys} -- identifier 572 is the rating "
          f"and 527 the `+20 vs. physical` (content/items.toml). Alike, so a "
          f"single rating and a location roll are byte-identical on the wire "
          f"today; what this section pins is WHICH number reaches a spell")
    check(authsrv.player_spell_armour() == 25.0,
          "and a spell resolves against the ELEMENTAL 25, not the physical 45",
          f"{authsrv.player_spell_armour()} -- the `+20 vs. physical damage` "
          f"is a physical bonus; GWW's own worked example counts the "
          f"Elementalist's `+10 vs. Elemental` for nothing against an attack")
    check(authsrv.spell_armour_for(194) == 25.0
          and authsrv.spell_armour_for(312) is None
          and authsrv.spell_armour_for(322) is None,
          "Flare's `Fire damage` respects it; Holy Strike's `Holy damage` and "
          "Power Attack's `+ Damage` do not",
          f"194 -> {authsrv.spell_armour_for(194)}, 312 -> "
          f"{authsrv.spell_armour_for(312)}, 322 -> "
          f"{authsrv.spell_armour_for(322)}. WIKI (GWW, \"Damage\" sec. "
          f"Properties): holy and untyped skill damage ignore armour, and "
          f"`+<number>` rides an armour-respecting swing -- 39.2's rule, "
          f"keyed on the LABEL and never on \"is it a skill\"")

    # SKILLS-LR (2026-09-17, studies/skills 50): the spell ROLLS A LOCATION.
    # A lopsided set -- chest and legs on, head hands and feet bare, the
    # owner's RB2 body -- through the real `spell_armour_for`, with the roll
    # and the pieces pinned.
    cm = authsrv.combatmath
    saved_lr = (cm.player_armour_at, cm.roll_hit_location,
                authsrv.SPELL_LOCATION_ROLL)
    lopsided = {"warrior_body": 25.0, "warrior_legs": 25.0}
    try:
        cm.player_armour_at = lambda key, physical, *_a, **_k: lopsided.get(key)   # **_k: B4's cracked=
        cm.roll_hit_location = lambda: "warrior_head"
        bare = authsrv.spell_armour_for(194)
        cm.roll_hit_location = lambda: "warrior_body"
        chest = authsrv.spell_armour_for(194)
        authsrv.SPELL_LOCATION_ROLL = False
        cm.roll_hit_location = lambda: "warrior_head"
        legacy = authsrv.spell_armour_for(194)
    finally:
        (cm.player_armour_at, cm.roll_hit_location,
         authsrv.SPELL_LOCATION_ROLL) = saved_lr
    check(bare == 0.0 and chest == 25.0,
          "a spell rolls a hit location: a roll onto a BARE piece resolves "
          "against 0, a roll onto the chest against the chest's rating",
          f"head (bare) -> {bare}, chest -> {chest} -- OBSERVED on retail "
          f"(RUN-SKILLS-RB2): one Lightning Orb, 101 armoured and 286 bare")
    check(abs(authsrv.armour_multiplier(0.0) / authsrv.armour_multiplier(60.0)
              - 2 ** 1.5) < 1e-9,
          "and a bare piece against the 60 baseline is x2^(60/40) = 2.83 -- "
          "the tape's 286 / 101 = 2.832",
          f"{authsrv.armour_multiplier(0.0) / authsrv.armour_multiplier(60.0):.4f}")
    check(legacy == 25.0,
          "`--no-spell-location-roll` restores the chest's rating whatever "
          "the roll (the revert arm, REFUTED as a claim about retail)",
          f"roll=head, flag off -> {legacy}")

    # The cast itself, at rank 0 so Flare's 20 scales to 36.68 and does not
    # kill the 100-pool player (at rank 12 the 56 becomes 102.7, an overkill
    # the wire would carry as 1.0 -- the wiki's "below 60 takes MORE").
    def _cast(skill_id, **flags):
        saved = {k: getattr(authsrv, k) for k in flags}
        saved_rank = authsrv.ENEMY_SKILL_RANK
        out = []
        st = {"agents": {}, "pos": (0.0, 0.0)}
        ag = {"name": "t", "dead": False, "last_hit": 0.0, "max_health": 100.0,
              "health": 100.0, "pos": (0.0, 0.0), "casting": 0,
              "skills": ((skill_id, 1.0, 0.0),), "skill_ready": [0.0]}
        st["agents"][10] = ag
        try:
            for k, v in flags.items():
                setattr(authsrv, k, v)
            authsrv.ENEMY_SKILL_RANK = 0
            _send = lambda op, vals, label="", quiet=False: out.append((op, vals, label))   # noqa: E731
            authsrv.land_skill(_send, st, 10, ag, 0)
            # studies/weapons 37 (2026-09-20): a projectile spell's word rides
            # the flight -- Flare's 343 leaves at the completion and lands a
            # flight later, its terms computed THEN, under the same flags.
            for _shot in st.get("body_projectiles") or ():
                _shot["arrives_at"] -= 30.0
            authsrv.projectile_tick(_send, st, 0)
        finally:
            for k, v in saved.items():
                setattr(authsrv, k, v)
            authsrv.ENEMY_SKILL_RANK = saved_rank
        # The float rides the wire as its f32 bit pattern (v[3] is a dword).
        dmg = [struct.unpack("<f", struct.pack("<I", v[3] & 0xFFFFFFFF))[0]
               for op, v, _l in out
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
               and v[0] == agents.PROP_DAMAGE]
        return st, dmg

    mult = authsrv.armour_multiplier(25.0)          # 2^((60-25)/40) = 1.834
    st, dmg = _cast(194)
    # ZEROWORD (2026-09-14): the same Flare into a rating of 300 -- 2^((60-300)/40)
    # = 1/64, so 20 becomes 0.31 and truncates to nothing -- still sends its
    # damage word, as -0.0, and the pool does not move. Retail's -0.0 words
    # are the witness (F46.7). Not "fully converted": no conversion is open.
    st_z, dmg_z = _cast(194, spell_armour_for=lambda _sid, *_a: 300.0)   # *_a: B4's state
    check(len(dmg_z) == 1 and dmg_z[0] == 0.0 and math.copysign(1.0, dmg_z[0]) < 0
          and st_z["player_health"] == 100.0,
          "Flare grazing to nothing still sends [16, player, caster, -0.0] and "
          "takes nothing off the pool",
          f"damage words {dmg_z}, health {st_z['player_health']}")
    want = math.floor(20.0 * mult)   # DAMAGE-INT: 36.68 goes out as 36 (truncated)
    check(len(dmg) == 1 and abs(dmg[0] + want / 100.0) < 1e-5   # f32 on the wire
          and abs(st["player_health"] - (100.0 - want)) < 1e-6,
          f"Flare's 20 lands as {want} ({20.0 * mult:.2f} truncated to whole "
          f"points, DAMAGE-INT) against AR 25 -- the wiki's own "
          f"multiplier, 2^((60-25)/40) = {mult:.4f}",
          f"sent {dmg}, health {st['player_health']}. Below the 60 baseline "
          f"the player takes MORE than the stated amount, which is what GWW "
          f"says happens to an under-armoured target and what this server "
          f"used to get backwards by dealing the stated 20")
    st, dmg = _cast(194, SPELL_ARMOUR=False)
    check(len(dmg) == 1 and abs(dmg[0] + 0.20) < 1e-6,
          "`--no-spell-armour` restores the stated 20 (the revert arm)",
          f"sent {dmg}")
    st, dmg = _cast(194, ARMOUR_TERM=False)
    check(len(dmg) == 1 and abs(dmg[0] + 0.20) < 1e-6,
          "and so does `--no-armour-term`, the general control",
          f"sent {dmg} -- a session that drops the swing's armour maths "
          f"drops the spell's with it")
    st, dmg = _cast(312)
    check(len(dmg) == 1 and abs(dmg[0] + 0.10) < 1e-6,
          "CONTROL: Holy Strike's 10 at rank 0 is still exactly 10 with the "
          "term ON",
          f"sent {dmg} -- armour-ignoring by type, untouched by this default")

    print("\n11b. whose connection it is: spellhitjoin.observer_of (bare "
          "machine, studies/skills 43.8)")
    # The JARIN hero tape's shape (20260914T005758 conn 56011): the player 29
    # is the kind-5 create, the hero 30 the kind-9 one, both get property 41,
    # and the hero's 0x00E3 comes FIRST. The first-0x00E3 rule named 30; every
    # consumer's "own" split (interruptjoin, missjoin, rechargeprobe, this
    # file's section 12) was scored on it.
    import spellhitjoin
    E3, E2, P9F = 0x00E3, 0x00E2, 0x009F
    jarin = [(0, 1.0, 0x0020, [0x20, 29, 0, 0, 5]),
             (1, 1.1, 0x0020, [0x20, 30, 0, 0, 9]),
             (2, 1.2, P9F, [P9F, 41, 29, 1]), (3, 1.3, P9F, [P9F, 41, 30, 1]),
             (4, 2.0, E3, [E3, 30, 346, 0]),          # the hero's, first
             (5, 3.03, E3, [E3, 29, 392, 0]),         # answers the press at 3.0
             (6, 4.0, E3, [E3, 30, 322, 0]),
             (7, 5.04, E2, [E2, 29, 394, 0])]         # answers the press at 5.0
    presses = [(3.0, 0x0046), (5.0, 0x0027)]
    first_e3 = next(v[1] for _i, _t, op, v in jarin if op == E3)
    got = spellhitjoin.observer_of(jarin, presses)
    check(first_e3 == 30 and got == (29, 29, None),
          "the player of a hero tape is the property-41 agent with the kind-5 "
          "create, and the agent answering the connection's own presses agrees "
          "-- NOT the agent of the first 0x00E3, which is the hero's (the "
          "known-bad arm, run on the same fixture)",
          f"first 0x00E3's agent {first_e3}; observer_of -> {got}")
    solo = [r for r in jarin if not (r[2] == P9F and r[3][2] == 30)]
    swapped = [(i, t, op, [v[0], 30] + v[2:] if op in (E3, E2) and v[1] == 29
                else ([v[0], 29] + v[2:] if op in (E3, E2) else v))
               for i, t, op, v in solo]
    got = spellhitjoin.observer_of(swapped, presses)
    check(got[0] is None and got[1] == 30
          and got[2].startswith("observer rules disagree")
          and "29" in got[2] and "30" in got[2],
          "the two rules DISAGREEING is refused -- no player named, the reason "
          "names both answers -- never settled by picking one",
          f"property 41 on 29 alone, the presses answered by 30: {got}")
    no41 = [r for r in jarin if r[2] != P9F]
    got_press = spellhitjoin.observer_of(no41, presses)
    got_none = spellhitjoin.observer_of(no41, ())
    check(got_press == (29, 29, None) and got_none[0] is None
          and got_none[2].startswith("no observer")
          and spellhitjoin.player_of(jarin) == 29,
          "the fallbacks: no property 41 -> the answered presses name the "
          "player; neither -> None, said so; property 41 alone (no c2s given) "
          "still names the player on a hero tape",
          f"no 41 + presses {got_press}; no 41, no presses {got_none}; "
          f"player_of(jarin) {spellhitjoin.player_of(jarin)}")
    late = [(i, t + (0.7 if op == E3 and v[1] == 29 else 0.0), op, v)
            for i, t, op, v in jarin if not (op == E2)]
    got = spellhitjoin.observer_of(late, presses)
    check(got == (29, None, None),
          f"an answer later than {spellhitjoin.PRESS_ANSWER_S} s casts no vote "
          "(a press that walks into range first); it does not refute property 41",
          f"the E3 0.73 s after its press: {got}")


    print("\n11c. Incendiary Bonds 179: the hex's END EFFECT -- at expiry, at the wearer's "
          "death, negated by a removal (studies/skills 61, hexjoin.py)")
    # The tape (28 completions): the completion lands the hex ALONE; its end strikes
    # every foe within 240 u of the wearer, per foe the word THEN the Burning, then the
    # hex's own end; the target's death fires it early on the foes standing; the
    # target's Remove Hex negates it. Driven here through the real press / E5,
    # effect_tick, a killing hit and a hostile's land_skill, against the vault's records.
    FOE, HERO, PLAYER = 10, 200, authsrv.PLAYER_AGENT_ID
    saved_b3 = (authsrv._is_attack_skill, authsrv.skill_timing, authsrv.skill_cost,
                authsrv.weapon_satisfies, agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
                authsrv.HEX_END_BURST, authsrv.SPELL_ENERGY_BONUS, authsrv.ENERGY_BONUS_PER_FOE,
                authsrv.AREA_DAMAGE, authsrv.skill_condition)
    STATUS, REGEN, WORD, APPLY, REMOVE = 0x00F1, 0x00A2, 0x00A3, 0x0042, 0x0044
    words = lambda batch: [v[:3] for op, v in batch if op == WORD and v[0] in (16, 17)]   # noqa: E731
    fracs = lambda batch: [v[3] for op, v in batch if op == WORD and v[0] in (16, 17)]    # noqa: E731
    fin58 = lambda batch: [v for op, v in batch if op == 0x009F and v[0] == 58]           # noqa: E731
    adds = lambda batch: [tuple(v) for op, v in batch if op == 0x009F and v[0] == agents.PROP_AURA_ON]    # noqa: E731
    removes = lambda batch: [tuple(v) for op, v in batch if op == 0x009F and v[0] == agents.PROP_AURA_OFF]  # noqa: E731
    status = lambda batch: [tuple(v) for op, v in batch if op == STATUS]                  # noqa: E731
    applies = lambda batch: [v for op, v in batch if op == APPLY]                         # noqa: E731
    ops = lambda batch: [op for op, _v in batch]                                          # noqa: E731

    def eps(st):
        return sorted((e["agent"], e["buff"], e["skill"], e["duration"])
                      for e in authsrv.effect_table(st).live.values())

    def expire(st, send):
        for e in authsrv.effect_table(st).live.values():
            e["expires_at"] -= 60.0
        authsrv.effect_tick(send, st, 1)

    def _world():
        entry = {"name": "suit", "dead": False, "died_at": 0.0, "health": 9000.0,
                 "max_health": 9000.0, "last_hit": 0.0, "pos": (100.0, 0.0), "plane": 0,
                 "armor_rating": 60.0, "allegiance": agents.ALLEGIANCE_HOSTILE,
                 "attack_speed": authsrv.ENEMY_ATTACK_SPEED, "effects": 0,
                 "attacks_back": False, "skills": (), "skill_ready": []}
        st = {"agents": {FOE: entry}, "pos": (0.0, 0.0), "player_health": 480.0}
        st["agents"][11] = dict(entry, pos=(200.0, 0.0))   # 100 u from the target: inside 156 / 240
        st["agents"][12] = dict(entry, pos=(600.0, 0.0))   # 500 u off: outside both
        return st

    def player_cast(sid, before=None, st=None):
        st, sent = (_world() if st is None else st), []
        st["cast_busy_until"] = 0.0
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.handle_skill_press([0, sid, 0, FOE], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
        sent.clear()
        for cast in st["pending_casts"]:
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        if before is not None:
            before(st)
        authsrv.cast_tick(send, st, 1)
        for cast in list(st["pending_casts"]):
            st["pending_casts"].remove(cast)
        return st, sent, send

    def _body_world(sid):
        foe = {"name": "archer", "dead": False, "died_at": 0.0, "health": 200.0,
               "max_health": 200.0, "last_hit": 0.0, "pos": (100.0, 0.0), "plane": 0,
               "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": 1.75, "effects": 0,
               "attacks_back": True, "skills": [[sid, 0.0, 20.0]], "skill_ready": [0.0],
               "npc": {"profession": 6, "level": 5}, "casting": 0, "cast_target": PLAYER}
        monk = {"name": "monk", "dead": False, "died_at": 0.0, "health": 100.0,
                "max_health": 100.0, "last_hit": 0.0, "pos": (0.0, 110.0), "plane": 0,
                "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0, "attack_speed": 1.75,
                "attacks_back": False, "skills": (), "skill_ready": [],
                "npc": {"profession": 3, "level": 5}, "party_slot": 0, "weapon_item": "caster_staff"}
        return {"agents": {FOE: foe, HERO: monk, 300: dict(monk, pos=(0.0, 400.0))},
                "pos": (0.0, 0.0), "player_health": 480.0, "player_dead": False}

    try:
        authsrv._is_attack_skill = lambda sid: False
        authsrv.skill_timing = lambda sid: (1.0, 0.75, 0.0)
        authsrv.skill_cost = lambda sid: (0, 0)
        authsrv.weapon_satisfies = lambda sid: True
        authsrv.apply_party_character({"player_weapon": "starter_wand"})
        r179 = agents.WORLD.get("skill_effect", "179")
        # (a) the readers, against the record: 72 at rank 13 is the tape's own payoff word
        # (0.12973 of a 555 pool, spellhitjoin 43.5), 3.0 s its Burning
        check(authsrv.hex_end_damage(179, 0) == (20, "standalone")
              and authsrv.hex_end_damage(179, 13) == (72, "standalone")
              and authsrv.hex_end_damage(185, 0) is None and authsrv.hex_end_damage(99999, 0) is None
              and authsrv.hex_cast_damage(179, 13) is None and authsrv.skill_damage(179, 13) is None
              and authsrv.skill_condition(179, 13) is None
              and authsrv._condition_terms(179, r179, 13) == (480, 3.0)
              and r179.get("on_end") == "burst" and r179.get("end_radius") == 240
              and authsrv.area_hex(179) is None and authsrv.spell_burst(179) is None,
              "the row: on_end = burst, end_radius 240; hex_end_damage reads the scale (20 at rank "
              "0, 72 at the tape caster's 13 -- retail's 0.12973 x 555), nothing hits at cast "
              "(hex_cast_damage / skill_damage None), skill_condition is None (the Burning is the "
              "payoff's: _condition_terms 3.0 s at 13), not an area hex, not a burst",
              (authsrv.hex_end_damage(179, 13), dict(r179)))
        # (b) the E5: the hex ALONE -- and the two visuals (EV-4: the skill_visual row)
        st, sent, send = player_cast(179)
        arm = next(iter(authsrv.effect_table(st).live.values())).get("end_burst")
        vis21 = [v for op, v in sent if op == 0x009F and v[0] == agents.GV_EFFECT_ON_AGENT]
        vis20 = [v for op, v in sent if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]
        i58 = next(i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 58)
        i21 = next(i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == agents.GV_EFFECT_ON_AGENT)
        i20 = next(i for i, (op, v) in enumerate(sent) if op == 0x00A0)
        i6 = next(i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 6)
        check(fin58(sent) == [[58, PLAYER, 0]] and not words(sent) and not applies(sent)
              and adds(sent) == [(6, FOE, 1), (6, FOE, 12)] and status(sent) == [(FOE, 0x800)]
              and vis21 == [[21, PLAYER, 347]] and vis20 == [[20, FOE, PLAYER, 348]]
              and i58 < i21 < i20 < i6
              and eps(st) == [(FOE, 1, 179, 3.0)]
              and arm == {"radius": 240.0, "hostile": False, "caster_row": None}
              and all(st["agents"][a]["health"] == 9000.0 for a in (FOE, 11, 12)),
              "the player's Incendiary Bonds at the E5: [58, me, 0], [21, me, 347], [20, 10, me, "
              "348] (the s_skill +0x78 / +0x7c pair, retail 28/28 -- the review's EV-4: the first "
              "cut had no skill_visual row and sent neither), [6, 10, 1], [6, 10, 12], 0x00F1 "
              "[10, 0x800] -- no word, no Burning, one 3.0 s episode on the target ARMED (240 u, "
              "the player's side), the foes beside it untouched",
              str([(hex(op), v) for op, v in sent]))
        # (c) the expiry: the payoff per foe, THEN the hex's own end
        sent.clear()
        expire(st, send)
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        i_7 = [i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 7]
        i_f = [i for i, (op, v) in enumerate(sent) if op == STATUS]
        i_r = [i for i, (op, v) in enumerate(sent) if op == REGEN]
        check(words(sent) == [[16, FOE, PLAYER], [16, 11, PLAYER]] and len(set(fracs(sent))) == 1
              and status(sent) == [(FOE, 0x802), (11, 0x002), (FOE, 0x002)]
              and [v[:2] for op, v in sent if op == REGEN] == [[44, FOE], [44, 11]]
              and i_w[0] < i_f[0] < i_r[0] < i_w[1] < i_f[1] < i_r[1] < i_7[0] < i_7[1] < i_f[2]
              and removes(sent) == [(7, FOE, 1), (7, FOE, 12)] and REMOVE not in ops(sent)
              and eps(st) == [(FOE, 2, 480, 1.0), (11, 3, 480, 1.0)]
              and st["agents"][FOE]["health"] == 8980.0 and st["agents"][11]["health"] == 8980.0
              and st["agents"][12]["health"] == 9000.0,
              "at +3 s the END EFFECT: per foe within 240 u (the target, the one 100 u beside "
              "it; not the one 500 u off) in id order the word [16, foe, me, 20] then its Burning "
              "(0x00F1 +0x02, [44] -- 1.0 s at rank 0; no 0x0042 on a foe), THEN the hex's own "
              "end [7, 10, 1] [7, 10, 12] 0x00F1 [10, 0x2]; no 0x0044 for a foe; no 58, no [20]",
              str([(hex(op), v) for op, v in sent]))
        # (d) the wearer's DEATH fires it early, once, on the foes still standing
        st, sent, send = player_cast(179)
        st["agents"][FOE]["health"] = 1.0
        sent.clear()
        authsrv.hit_enemy(send, st, FOE, 1, exact=5.0, swing=False, armed=True, label="a killing blow")
        dead_batch = list(sent)
        sent.clear()
        expire(st, send)
        d_ops = [(op, v) for op, v in dead_batch]
        i_kill = next(i for i, (op, v) in enumerate(d_ops) if op == STATUS and v == [FOE, 0x810])
        i_rew = next(i for i, (op, v) in enumerate(d_ops) if op == 0x00EE)
        i_pay = next(i for i, (op, v) in enumerate(d_ops) if op == WORD and v[1] == 11)
        i_7 = [i for i, (op, v) in enumerate(d_ops) if op == 0x009F and v[0] == 7]
        i_step = next(i for i, (op, v) in enumerate(d_ops) if op == STATUS and v == [FOE, 0x10])
        i_flags = next(i for i, (op, v) in enumerate(d_ops) if op == 0x0026)
        check(words(dead_batch) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and removes(dead_batch) == [(7, FOE, 1), (7, FOE, 12)]
              and status(dead_batch) == [(FOE, 0x810), (11, 0x002), (FOE, 0x10)]
              and i_kill < i_rew < i_pay < i_7[0] < i_7[1] < i_step < i_flags
              and st["agents"][FOE]["dead"] and st["agents"][11]["health"] == 8980.0
              and st["agents"][12]["health"] == 9000.0
              and eps(st) == [] and not words(sent) and not removes(sent),
              "the target killed at +0 s -- RETAIL'S DEATH BATCH ORDER (631.935 / 642.688, 2/2; "
              "the review's EV-1 / EV-2 / R34-1): the death word FIRST with the hex bit still up "
              "(0x810), the kill reward, THEN the payoff EARLY on the foe beside the corpse (20, "
              "Burning) and not on the corpse, THEN the corpse's [7, 10, 1] [7, 10, 12], the "
              "step-down 0x00F1 [10, 0x10], the flags byte LAST; the episode is gone and the tick "
              "that would have expired it fires NOTHING more (end_fired: once per hex)",
              (str([(hex(op), v) for op, v in dead_batch]), eps(st)))
        # (d') the review's M5: the payoff KILLS ITS OWN WEARER at expiry -- once
        st, sent, send = player_cast(179)
        st["agents"][FOE]["health"] = 5.0
        sent.clear()
        expire(st, send)
        check(words(sent) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and removes(sent) == [(7, FOE, 1), (7, FOE, 12)] and REMOVE not in ops(sent)
              and st["agents"][FOE]["dead"] and st["agents"][11]["health"] == 8980.0
              and [(e[0], e[2], e[3]) for e in eps(st)] == [(11, 480, 1.0)],
              "the payoff kills its own wearer at expiry: ONE word per foe, ONE [7] pair (the "
              "wearer's strip closed and worded the episode; end_fired keeps the strip from "
              "firing it again -- without the guard foe 11 took a third word), the adjacent "
              "foe's health down once", str([(hex(op), v) for op, v in sent]))
        # (d'') the review's M6: the payoff KILLS THE ADJACENT FOE -- no Burning on its corpse
        st, sent, send = player_cast(179)
        st["agents"][11]["health"] = 5.0
        sent.clear()
        expire(st, send)
        w11 = [v[1] for op, v in sent if op == STATUS and v[0] == 11]
        check(st["agents"][11]["dead"] and [e for e in eps(st) if e[0] == 11] == []
              and w11 and w11[0] & 0x10 and not any(w & 0x02 for w in w11)
              and eps(st) == [(FOE, 2, 480, 1.0)],
              "the payoff kills the adjacent foe: no Burning episode on its corpse and no status "
              "word of its carrying the condition bit after the death word (apply_condition "
              "refuses nothing -- the payoff's own corpse gate is what keeps it off)",
              (eps(st), w11))
        # (d''') the review's R34-4: a SECOND 179 on the same wearer arms no second payoff
        st, sent, send = player_cast(179)
        st, sent2, send = player_cast(179, st=st)
        armed = sorted((e["buff"], bool(e.get("end_burst"))) for e in authsrv.effect_table(st).live.values())
        sent2.clear()
        expire(st, send)
        st_d, sent_d, send_d = player_cast(179)
        st_d, sent_d, send_d = player_cast(179, st=st_d)
        st_d["agents"][FOE]["health"] = 1.0
        sent_d.clear()
        authsrv.hit_enemy(send_d, st_d, FOE, 1, exact=5.0, swing=False, armed=True, label="a killing blow")
        check(armed == [(1, True), (2, False)]
              and words(sent2) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and st["agents"][11]["health"] == 8980.0
              and words(sent_d) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and st_d["agents"][11]["health"] == 8980.0,
              "two Incendiary Bonds on one wearer: two episodes (retail's overlapping shape) but "
              "the second ARMS NOTHING while the first's end is live -- one payoff at expiry and "
              "one at the wearer's death, each foe struck once (RECONSTRUCTION: the client draws "
              "the first hex; no double 179 is on any tape)", (armed, words(sent2), words(sent_d)))
        # (e) a REMOVAL negates it -- and the known-bad arm shows the dead gate is what negates
        st, sent, send = player_cast(179)
        ep = next(iter(authsrv.effect_table(st).live.values()))
        sent.clear()
        authsrv.strip_effects(send, st, FOE, 1, "a cure")
        negated = (list(sent), eps(st), {a: st["agents"][a]["health"] for a in (FOE, 11)})
        sent.clear()
        authsrv.hex_end_burst(send, st, 1, ep, "a death-blind strip (the known-bad arm)")
        check(removes(negated[0]) == [(7, FOE, 1), (7, FOE, 12)] and not words(negated[0])
              and negated[1] == [] and negated[2] == {FOE: 9000.0, 11: 9000.0}
              and words(sent) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and st["agents"][FOE]["health"] == 8980.0,
              "a strip while ALIVE (a cure / Remove Hex): the [7]s and 0x00F1 0, no word on "
              "anybody, no Burning -- NEGATED (retail 4/4); KNOWN-BAD ARM: the same stripped "
              "episode handed to hex_end_burst as a death-blind strip would DETONATES on both "
              "foes -- so the `if dead:` gate in strip_effects is what negates",
              (str([(hex(op), v) for op, v in negated[0]]), str(words(sent))))
        # (f) known-bad: the Burning at the COMPLETION (skill_condition ungated)
        authsrv.skill_condition = lambda sid, r: authsrv._condition_terms(sid, authsrv.skill_effect_row(sid), r)
        try:
            st_b, sent_b, _s = player_cast(179)
        finally:
            authsrv.skill_condition = saved_b3[-1]
        st_g, sent_g, _s = player_cast(179)
        check(eps(st_b) == [(FOE, 1, 179, 3.0), (FOE, 2, 480, 1.0)] and status(sent_b)[-1] == (FOE, 0x802)
              and eps(st_g) == [(FOE, 1, 179, 3.0)],
              "KNOWN-BAD ARM: with skill_condition's on_end gate stubbed out the completion "
              "Burns the target at once (retail: 0 of 28); the gate keeps the Burning for the "
              "payoff", (eps(st_b), eps(st_g)))
        # (g) --no-hex-end-burst
        authsrv.HEX_END_BURST = False
        st_n, sent_n, send_n = player_cast(179)
        sent_n.clear()
        expire(st_n, send_n)
        authsrv.HEX_END_BURST = True
        check(not words(sent_n) and removes(sent_n) == [(7, FOE, 1), (7, FOE, 12)]
              and status(sent_n) == [(FOE, 0)] and eps(st_n) == []
              and all(st_n["agents"][a]["health"] == 9000.0 for a in (FOE, 11)),
              "--no-hex-end-burst: the hex expires with its [7]s and 0x00F1 0 and NOTHING fires "
              "-- this server's bytes until 2026-09-27",
              str([(hex(op), v) for op, v in sent_n]))
        # (h) a hostile's 179 at the player, the hero 110 u above, a party body 400 u off
        st = _body_world(179)
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        at_e5 = list(sent)
        sent.clear()
        expire(st, send)
        ar = authsrv.spell_armour_for(179)
        want = authsrv._whole_points(68.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar))
        i10 = next((i for i, (op, v) in enumerate(sent) if op == 0x009F and v[:3] == [10, PLAYER, 179]), None)
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        i_42 = [i for i, (op, v) in enumerate(sent) if op == APPLY]
        i_44 = [i for i, (op, v) in enumerate(sent) if op == REMOVE]
        i_7 = [i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 7]
        check(at_e5[0] == (0x009F, [58, FOE, 0])
              and applies(at_e5) == [[PLAYER, 179, 12, 1, authsrv._f32(3.0)]]
              and adds(at_e5) == [(6, PLAYER, 1), (6, PLAYER, 12)] and status(at_e5) == [(PLAYER, 0x800)]
              and not words(at_e5) and st["player_health"] == 480.0 - want
              and words(sent) == [[16, PLAYER, FOE], [16, HERO, FOE]]
              and i10 is not None and i10 + 1 == i_w[0]
              and applies(sent) == [[PLAYER, 480, 12, 2, authsrv._f32(3.0)]]
              and i_w[0] < i_42[0] < i_w[1] < i_44[0] < i_7[0] < i_7[1]
              and removes(sent) == [(7, PLAYER, 1), (7, PLAYER, 12)]
              and eps(st) == [(PLAYER, 2, 480, 3.0), (HERO, 3, 480, 3.0)]
              and st["agents"][HERO]["health"] < 100.0 and st["agents"][300]["health"] == 100.0,
              f"a hostile's Incendiary Bonds at the player: [58, it, 0], the player's 0x0042 [me, "
              f"179, 12, 1, 3.0], [6, me, 1], [6, me, 12], 0x00F1 0x800, NO word; at +3 s: [10, me, "
              f"179] then the player's word ({want} = 68 at rank 12 against the pieces' rating at "
              f"the caster's strike level), its Burning 0x0042 480 3.0 s (rank 12: 2.6 -> 3), then "
              f"the hero's word 110 u off and its Burning, THEN 0x0044 [me, 1], [7, me, 1], [7, me, "
              f"12]; the body 400 u off untouched -- the caster's row snapshotted at the apply",
              (str([(hex(op), v) for op, v in at_e5]), str([(hex(op), v) for op, v in sent])))
        # (i) SOURCE: where the hook sits, and that the flag flips inside main()
        src = open(authsrv.__file__, encoding="utf-8").read()
        i_tick = src.index("\ndef effect_tick(")
        i_fire = src.index('hex_end_burst(send, state, conn_id, ep, "it ran out")', i_tick)
        i_close = src.index('table.close(ep["buff"])', i_tick)
        i_strip = src.index("\ndef strip_effects(")
        i_dead = src.index("    if dead:\n", i_strip)
        i_sfire = src.index("hex_end_burst(send, state, conn_id, ep, why)", i_strip)
        i_srem = src.index("effect_list_send(send, state, GAME_SMSG_EFFECT_REMOVE, [ep[\"agent\"], ep[\"buff\"]],", i_strip)
        i_kill = src.index("\ndef kill_agent(")
        i_kword = src.index("    send(GAME_SMSG_AGENT_UPDATE_STATUS, [target_id, _word],", i_kill)
        i_krew = src.index("    send(GAME_SMSG_AGENT_KILL_REWARD,", i_kill)
        i_kstrip = src.index("    _strip_and_step_down()             # between the reward and the flags", i_kill)
        i_kflags = src.index("    send(GAME_SMSG_AGENT_UPDATE_FLAGS, [target_id, AGENT_FLAGS_KILLED],\n         f\"flags {AGENT_FLAGS_KILLED} on the dying agent", i_kill)
        i_main = src.index("\ndef main():")
        i_flag = src.index("    if a.no_hex_end_burst:", i_main)
        i_flag2 = src.index("    if a.no_spell_energy_bonus:", i_main)
        i_flag3 = src.index("    if a.energy_bonus_target_only:", i_main)
        check(i_tick < i_fire < i_close and i_strip < i_dead < i_sfire < i_srem
              and i_sfire - i_dead < 900
              and i_kill < i_kword < i_krew < i_kstrip < i_kflags
              and src.count("    hex_end_arm(state, ep, caster_id, row, erow)      # studies/skills 61") == 1
              and "HEX_END_BURST = False" in src[i_flag:i_flag + 160]
              and "SPELL_ENERGY_BONUS = False" in src[i_flag2:i_flag2 + 160]
              and "ENERGY_BONUS_PER_FOE = False" in src[i_flag3:i_flag3 + 160]
              and src.count("    if row.get(\"on_end\") or row.get(\"bonus_if\"):") == 1,
              "SOURCE LOCK: effect_tick fires the end effect BEFORE the close (the payoff ahead of "
              "the hex's own end), strip_effects fires it under `if dead:` only and AHEAD of the "
              "removal loop (the payoff, then the [7]s -- retail 2/2), kill_agent sends the death "
              "word, the reward, the strip, the flags in that order, the arm is set once at the "
              "apply, skill_condition gates on_end / bonus_if, main() flips HEX_END_BURST / "
              "SPELL_ENERGY_BONUS / ENERGY_BONUS_PER_FOE under their flags (the review's M10)")

        print("\n11d. Mind Burn 185: the base word on the target and the adjacent foes, the "
              "energy clause's twin and Burning decided PER FOE (studies/skills 61)")
        # 25 completions on the tape: [58] [20, T, c, 331] then per foe the word, and a second
        # identical word + Burning when the clause holds FOR THAT FOE -- 647.300 has the target
        # single and an adjacent foe twin, which one comparison against the target cannot make.
        r185 = agents.WORLD.get("skill_effect", "185")
        check(authsrv.skill_damage(185, 0) == (15, "standalone") and authsrv.skill_damage(185, 13) == (54, "standalone")
              and authsrv.spell_adjacent(185) == 156.0 and authsrv.spell_adjacent(179) is None
              and authsrv.spell_adjacent(194) is None and authsrv.spell_adjacent(99999) is None
              and authsrv.energy_bonus_row(185) and not authsrv.energy_bonus_row(179)
              and authsrv.skill_condition(185, 13) is None
              and authsrv._condition_terms(185, r185, 13) == (480, 9.0)
              and authsrv.spell_burst(185) is None and authsrv.area_over_time(185, 12) is None
              and authsrv.player_rank_for_skill(185) == 0,
              "the row: Fire damage 15..60 (54 at the tape caster's 13), adjacent_damage reaches "
              "156 u (a type-5 spell at a foe; a hex or a projectile spell reach nothing), the "
              "energy clause is the row's, skill_condition is None (the Burning is the twin's: "
              "9.0 s at 13 -- retail's 9.0 on the observer), not a burst, not an area; the "
              "player casts at rank 0", (authsrv.spell_adjacent(185), dict(r185)))

        def energies(mine, foe, other):
            def _set(s):
                authsrv.player_energy(s).current = float(mine)
                authsrv.agent_energy(s["agents"][FOE]).current = float(foe)
                authsrv.agent_energy(s["agents"][11]).current = float(other)
            return _set
        # (b) the player at 15: the target (10) takes the twin + Burning, the adjacent (20) one word
        st, sent, send = player_cast(185, before=energies(15, 10, 20))
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        i_f = [i for i, (op, v) in enumerate(sent) if op == STATUS]
        i_20 = [i for i, (op, v) in enumerate(sent) if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]
        check(fin58(sent) == [[58, PLAYER, 0]]
              and words(sent) == [[16, FOE, PLAYER], [16, FOE, PLAYER], [16, 11, PLAYER]]
              and len(set(fracs(sent))) == 1 and status(sent) == [(FOE, 0x002)]
              and i_w[1] < i_f[0] < i_w[2]
              and [v for op, v in sent if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]
              == [[20, FOE, PLAYER, 331]] and i_20[0] < i_w[0]
              and eps(st) == [(FOE, 1, 480, 1.0)]
              and st["agents"][FOE]["health"] == 8970.0 and st["agents"][11]["health"] == 8985.0
              and st["agents"][12]["health"] == 9000.0,
              "the player's Mind Burn (energy 15) on the target (10) with a foe 100 u beside it (20): "
              "[58], [20, 10, me, 331] on the TARGET alone (the s_skill +0x7c, retail 25/25 -- the "
              "review's EV-4; the first cut sent none and locked the absence), the target's word "
              "TWICE (identical, 15 at rank 0) then its Burning (0x00F1 +0x02, 1.0 s at rank 0), "
              "then the adjacent foe's ONE word; the foe 500 u off untouched; no [20] per foe",
              str([(hex(op), v) for op, v in sent]))
        # (b') the review's R34-2: a target DEAD at the E5 -- nothing on the foes beside it
        st_x, sent_x, _s = player_cast(185, before=lambda s: (energies(15, 10, 20)(s),
                                                             s["agents"][FOE].update(dead=True, health=0.0)))
        check(not words(sent_x) and eps(st_x) == [] and fin58(sent_x) == [[58, PLAYER, 0]]
              and st_x["agents"][11]["health"] == 9000.0,
              "Mind Burn at a target that died mid-cast: the 58 and NOTHING lands -- not on the "
              "corpse, not on the foe 100 u beside it (a targeted spell fails with its target; "
              "only an area at a LOCATION survives it, WIKI rev 2685457); the first cut struck "
              "the adjacent foe from the corpse", str([(hex(op), v) for op, v in sent_x]))
        # (c) 647.300's shape: the target single, the adjacent foe twin
        st, sent, send = player_cast(185, before=energies(15, 20, 5))
        shape_647 = (words(sent), eps(st))
        # (d) KNOWN-BAD: the wiki's one comparison against the target cannot produce it
        authsrv.ENERGY_BONUS_PER_FOE = False
        st_t, sent_t, _s = player_cast(185, before=energies(15, 20, 5))
        st_t2, sent_t2, _s = player_cast(185, before=energies(15, 10, 20))
        authsrv.ENERGY_BONUS_PER_FOE = True
        check(shape_647 == ([[16, FOE, PLAYER], [16, 11, PLAYER], [16, 11, PLAYER]], [(11, 1, 480, 1.0)])
              and words(sent_t) == [[16, FOE, PLAYER], [16, 11, PLAYER]] and eps(st_t) == []
              and words(sent_t2) == [[16, FOE, PLAYER], [16, FOE, PLAYER], [16, 11, PLAYER], [16, 11, PLAYER]]
              and eps(st_t2) == [(FOE, 1, 480, 1.0), (11, 2, 480, 1.0)],
              "647.300's shape (the target at 20, the adjacent at 5, the caster 15): the target "
              "SINGLE and the adjacent foe TWIN + Burning -- PER FOE; KNOWN-BAD ARM "
              "--energy-bonus-target-only (the wiki's wording): the same pools give two singles, "
              "and 15 vs (10, 20) gives two twins -- one comparison can never split them",
              (shape_647, words(sent_t), words(sent_t2)))
        # (e) the reverts
        authsrv.SPELL_ENERGY_BONUS = False
        st_e, sent_e, _s = player_cast(185, before=energies(15, 10, 20))
        authsrv.SPELL_ENERGY_BONUS = True
        authsrv.AREA_DAMAGE = False
        st_a, sent_a, _s = player_cast(185, before=energies(15, 10, 20))
        authsrv.AREA_DAMAGE = True
        check(words(sent_e) == [[16, FOE, PLAYER], [16, 11, PLAYER]] and eps(st_e) == []
              and words(sent_a) == [[16, FOE, PLAYER]] and eps(st_a) == []
              and st_a["agents"][11]["health"] == 9000.0,
              "--no-spell-energy-bonus: the base words alone, no Burning, whatever the pools; "
              "--no-area-damage: the target's ONE word (the pre-2026-09-27 shape), the adjacent "
              "foe untouched", (words(sent_e), words(sent_a)))
        # (f) a hostile's Mind Burn at the player (30 vs 20: the twin), the hero (30 vs 30: single)
        st = _body_world(185)
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.player_energy(st).current = 20.0
        authsrv.agent_energy(st["agents"][HERO]).current = 30.0
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        ar = authsrv.spell_armour_for(185)
        want = authsrv._whole_points(51.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar))
        i10 = [i for i, (op, v) in enumerate(sent) if op == 0x009F and v[:3] == [10, PLAYER, 185]]
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        check(sent[0] == (0x009F, [58, FOE, 0])
              and words(sent) == [[16, PLAYER, FOE], [16, PLAYER, FOE], [16, HERO, FOE]]
              and fracs(sent)[0] == fracs(sent)[1] and len(i10) == 2
              and i10[0] + 1 == i_w[0] and i10[1] + 1 == i_w[1]
              and applies(sent) == [[PLAYER, 480, 12, 1, authsrv._f32(8.0)]]
              and st["player_health"] == 480.0 - 2 * want
              and st["agents"][HERO]["health"] < 100.0 and st["agents"][300]["health"] == 100.0
              and eps(st) == [(PLAYER, 1, 480, 8.0)] and st["agents"][FOE]["casting"] is None
              and float(authsrv.agent_energy_now(st, FOE)) == 30.0,
              f"a hostile's Mind Burn (its pool is our ENEMY_ENERGY 30) at the player (20) with "
              f"the hero 110 u above (30): [58, it, 0], then [10, me, 185] + the player's word "
              f"TWICE ({want} each, identical -- retail's twin) and its Burning 0x0042 480 8.0 s "
              f"(rank 12: 8.2 -> 8), then the hero's ONE word (30 is not more than 30); the body "
              f"400 u off untouched; every foe's terms computed before the 58",
              str([(hex(op), v) for op, v in sent]))
        # (g) SOURCE: the adjacent arm sits inside the standalone arm, behind the area over time
        i_std = src.index('elif target and found and found[1] == "standalone":')
        i_aotl = src.index("                elif _aot is not None:", i_std)
        i_adjl = src.index("                elif _adj is not None and not target_dead(state, target):", i_std)
        i_std_hit = src.index("_st_res = hit_enemy(send, state, target, conn_id, exact=float(found[0]),", i_std)
        check(i_std < i_aotl < i_adjl < i_std_hit
              and src.count("                elif _adj is not None and not target_dead(state, target):") == 1
              and src.count("    if _adj_terms is not None:                                # studies/skills 61") == 1
              and src.count("    elif damage is not None and _spell_how is None and _carea is None and _adj is not None:") == 1
              and src.index("    if _adj_terms is not None:") > src.index("    if _burst_terms is not None:                              # studies/weapons 40"),
              "SOURCE LOCK: the player's adjacent arm sits inside the standalone arm behind the "
              "area over time and ahead of the one-target word, gated on a LIVE target (R34-2); "
              "a body's terms arm and its exit "
              "sit beside the burst's (the terms before the 58, the words behind it)")
    finally:
        (authsrv._is_attack_skill, authsrv.skill_timing, authsrv.skill_cost,
         authsrv.weapon_satisfies, agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
         authsrv.HEX_END_BURST, authsrv.SPELL_ENERGY_BONUS, authsrv.ENERGY_BONUS_PER_FOE,
         authsrv.AREA_DAMAGE, authsrv.skill_condition) = saved_b3

    print("\n12. the corpus: one caster, one skill, one target is ONE value "
          "(spellhitjoin)")
    # P1-P4 in spellhitjoin's own words. A location roll on a set whose
    # pieces differ would put a second bucket on some pair; none has one.
    # FLOORS, not exact values -- the live corpus grows.
    unnamed = []
    try:
        rows = spellhitjoin.census(unnamed=unnamed)
        sc = spellhitjoin.score(rows)
    except (Exception, SystemExit) as exc:                # noqa: BLE001  (require_dir exits)
        LEDGER.skip("12. the corpus (spellhitjoin)",
                    f"no live corpus to read on this machine: {exc!r}")
        return LEDGER.verdict()
    hero_tape = {r["player"] for r in rows if r["capture"] == "20260914T005758"
                 and r["connection"].split("->")[0].endswith(":56011")}
    refused = [u for u in unnamed if u[2].startswith("observer rules disagree")]
    check(hero_tape == {29} and not refused,
          "the census names the JARIN tape's player 29 (the kind-5 create whose "
          "acks answer every press), not the hero 30 whose ack comes first; no "
          "connection in the corpus has its two rules disagreeing",
          f"players on 20260914T005758 conn 56011: {hero_tape}; refused "
          f"{refused}; named by nobody {len(unnamed)} (the corpus's one is a "
          f"stub with no property 41 and no press)")
    check(sc["n_cast"] >= 100 and sc["announced"] >= 0.95 * sc["n_cast"],
          "P1 cast damage is announced by a property-60 from its cause",
          f"{sc['announced']} of {sc['n_cast']} inside 4 s (floor 100, 95%)")
    # JARIN (20260914T005758): the caster 54's skill 222 on the Ranger and on
    # the hero spans TWO death penalties each (the targets' maxima 140 -> 119
    # -> 99 / 101) and the hero's Frenzy doubled its intake -- the join keys
    # on the target, not on the target's current maximum, so those two pairs
    # are several values by construction. Named, not widened: a third pair
    # is a new fact.
    # SLICE-F47 (2026-09-16): the third pair came -- 20260916T150306,
    # caster 48's skill 222 onto 29, maximum 140 -> 119 -- and it is the
    # death-penalty split ALONE: 24 whole points at both maxima, 0.17143 x 3
    # then 0.20168. So that signature is a rule in spellhitjoin.score
    # (`penalty_split`: one value per maximum, several maxima) and the new
    # pair passes by it. JARIN's two do NOT pass it and stay named: the
    # Ranger's holds 23 AND 24 points at the one maximum of 140 (cause
    # unmeasured), the hero's 26 AND 51 at 122 (Frenzy, F44/F45).
    PENALTY_SPLIT = {"54 222 29", "54 222 30"}
    split = sc["penalty_split"]
    check(sc["pairs"] >= 10 and sc["pair_hits"] >= 60
          and set(sc["multi_valued"]) - set(split) <= PENALTY_SPLIT,
          "P2 every (caster, skill, target) pair with >= 3 hits is ONE value "
          "per target maximum (a death-penalty split passes by SIGNATURE; the "
          "two JARIN pairs that are several values INSIDE one maximum set "
          "aside by name)",
          f"{sc['pairs']} pairs over {sc['pair_hits']} hits, skills "
          f"{sc['skills']}, multi-valued {sc['multi_valued']}, of which split "
          f"by a penalty {split} -- a 1-in-8 head roll on any armour "
          f"difference leaves one bucket with probability (7/8)^n, 0.03% at "
          f"n = 60; DoT ticks set aside {sc['ticks_set_aside']}")
    points = {k: sorted({round(v * m) for m, vals in b.items() for v in vals})
              for k, b in split.items()}
    check(len(split) >= 1 and all(len(p) == 1 for p in points.values()),
          "and every penalty-split pair is ONE value in WHOLE POINTS across "
          "its maxima -- the fraction moved because the maximum did (F46)",
          f"{points} -- LAKESIDE (20260916T150306): 48's 222 onto 29 is 24 "
          f"points at a maximum of 140 (0.17143, 3 hits) and at 119 (0.20168)")
    two = sc["two_hit_two_valued"]
    check(len(two) <= 1 and all(k.startswith("10 186 12") for k in two),
          "and the pairs BELOW the floor with two values are the one named "
          "mixed batch, Fireball + Incendiary Bonds' payoff onto agent 12",
          f"{two} -- the hex-end payoff lands 3.000 s after a 1 s cast and "
          f"the projectile 0.4 s after its 58, in one batch (43.5). A second "
          f"such pair is a new fact, not noise: read it before raising this")
    check(len(sc["onto_player"]) >= 1
          and all(n >= 3 and (len(vals) == 1 or k in PENALTY_SPLIT
                              or k in split)
                  for k, (n, vals) in sc["onto_player"].items()),
          "and the pairs onto the connection's OWN player are one value too "
          "(the JARIN penalty-split pair set aside by name)",
          f"{sc['onto_player']} -- the player is the one body whose armour "
          f"this server models")
    # 2026-09-23 (skills 43.8): until the observer rule was corrected, the JARIN
    # pair "onto the player" was the HERO's (54 -> 30, Frenzy's 26 and 51 at
    # 122) and LAKESIDE's (48 -> 29) was on no player at all -- its connection
    # has no 0x00E3. Both pass the check above, so it could not see the swap.
    check("54 222 29" in sc["onto_player"] and "54 222 30" not in sc["onto_player"]
          and "48 222 29" in sc["onto_player"],
          "and the JARIN pair onto the connection's own player is the RANGER's "
          "(54 -> 29), not the hero's (54 -> 30); LAKESIDE's 48 -> 29 is the "
          "player's too",
          f"{sorted(sc['onto_player'])}")
    check(sc["swing_pairs"] >= 5 and sc["swing_pairs_3plus"] == sc["swing_pairs"],
          "P3 CONTROL: every swing pair with >= 10 hits shows >= 3 values",
          f"{sc['swing_pairs_3plus']} of {sc['swing_pairs']} (min distinct "
          f"{sc['swing_min_distinct']}) -- the instrument sees a weapon's "
          f"range where there is one")
    check(sc["mind_burn_twins"] >= 10,
          "P4 Mind Burn's conditional second packet is a twin 16 in one batch",
          f"{sc['mind_burn_twins']} -- WIKI (GWW, \"Mind Burn\"): an "
          f"additional 15..60 if the caster has more Energy; the wire carries "
          f"it as a second identical packet, not a doubled one")

    print("\n12b. the corpus: a spell's LOCATION ROLL (spellhitjoin."
          "location_buckets, RUN-SKILLS-RB2)")
    # One caster's projectile spell onto one target, in whole points. With
    # five equal pieces it is ONE bucket (P2's world); the RB2 tape took three
    # pieces off and the same Lightning Orb fills TWO, 2^(60/40) apart.
    lb = spellhitjoin.location_buckets(rows)
    witnesses = []
    for k, pts in lb.items():
        vals = sorted(pts)
        for lo in vals:
            for hi in vals:
                if hi > lo and pts[lo] >= 4 and pts[hi] >= 2 \
                        and abs(hi / lo - 2 ** 1.5) / 2 ** 1.5 <= 0.015:
                    witnesses.append((" ".join(map(str, k[:1] + k[2:])),
                                      lo, pts[lo], hi, pts[hi]))
    check(len(witnesses) >= 1,
          "SKILLS-LR a projectile spell from one caster onto one target lands "
          "in TWO whole-point buckets 2^(60/40) apart -- an armoured piece and "
          "a bare one; spells roll a hit location",
          f"{witnesses} of {len(lb)} projectile groups -- 20260917T090355, "
          f"Lightning Orb 229 from the Master of Lightning: 101 and 286. The "
          f"single rating SKILLS-FA shipped (studies/skills 43) is REFUTED; "
          f"43.4's caveat -- equal pieces cannot tell -- was the whole story")


    print("\n12c. the corpus: hexjoin -- Incendiary Bonds' end effect, Mind Burn's per-foe "
          "twin, how a hex lands on any body, the conditions (studies/skills 61)")
    # The committed port of the DESKWORK-D6 tape lane's join, its predictions as the lane
    # REGISTERED them: three FAILED as registered (I4, M2, C2) and the reader prints them so,
    # with the corrected readings beside them. This lock is the reader's own verdict plus the
    # witness tape's exact counts (per tape) and the corpus floors.
    import hexjoin
    hc = hexjoin.census()
    hs = hexjoin.score(hc)
    hv = hexjoin.verdicts(hs)
    check(all(hv.values()) and hs["refused"] == 0 and hs["connections"] >= 96
          and not hs["i4"] and not hs["m2"] and not hs["c2"] and hs["m3"] is None
          and hs["i4c"] and hs["m2c"] and hs["m3c"] and hs["c2c"],
          "hexjoin's reading HOLDS: every prediction as registered but I4 / M2 / C2 (FAILED as "
          "registered, printed so), their corrected readings hold, M3 is untestable (no Mind "
          "Burn onto the observer) and its M3c holds, the four post-hoc facts hold; 0 refused",
          str(hv))
    def _exact_179(s):
        return (s["i_per_port"] == hexjoin.EXPECT_179_PER_PORT and s["i_completed"] == 28
                and s["i_scheduled"] == 20 and s["i_scheduled_with_words"] == 18
                and len(s["i_payoff_tick"]) == 1 and s["i_payoff_tick"][0][:2] == ("54071", 689.819)
                and len(s["i_removed"]) == 4 and all(n == 0 for _p, _t, _d, n in s["i_removed"])
                and len(s["i_target_died"]) == 3 and sum(1 for x in s["i_target_died"] if x[3]) == 2
                and len(s["i_caster_died"]) == 1 and s["i_takers_hist"] == {1: 10, 2: 5, 3: 5, 4: 1}
                and s["i_takers_not_foe"] == 0 and s["i_observer_struck"] == 3
                and s["i_observer_prefix_ok"] == 3
                and [x[:2] for x in s["i_observer_burning"]] == [(3, 3.0)] * 3
                and len(s["i_payoff_mixed"]) == 2)

    def _exact_185(s):
        return (s["m_per_port"] == hexjoin.EXPECT_185_PER_PORT and s["m_completed"] == 25
                and s["m_twin"] == 22 and s["m_single"] == 3 and s["m_none"] == 0
                and len(s["m_mixed"]) == 4 and s["m_target_single_adjacent_twin"] == [("54071", 647.3)]
                and s["m_twin_no_burning"] == 0 and s["m_single_with_burning"] == 1
                and [x[:2] for x in s["m_observer_burning"]] == [(9, 9.0)] * 2 and s["m_rank_fits"]
                and s["l_adds"].get("179 [1, 12]") == 28 and s["l_adds"].get("1097 [1, 12]") == 5
                and s["l_adds"].get("1097 [12]") == 1 and s["l_adds"].get("26 [1, 4]") == 5
                and s["l_adds"].get("222 []") == 14 and len(s["l_snare"]) == 6
                and s["l_ascending"] == 24 and len(s["l_not_ascending"]) == 1
                and s["l_not_ascending"][0][:3] == (185, "54071", 640.689)
                and s["c_effect_ids_witness"] == {"Burning": {25: 3}}
                and s["c_observer_no_id"].get("Burning") == 2)

    check(_exact_179(hs) and hs["i_hex_applies"][0]["field3"] == 13
          and authsrv.hex_end_damage(179, 13) == (72, "standalone"),
          "179 on 20260817T231139 (exact, PER TAPE -- scored on the witness capture alone): 30 "
          "announces (19 / 4 / 4 / 3 per port), 28 completed; 20 scheduled ends at +3.0, 18 with "
          "the payoff and ONE (689.819) whose only word is the caster's Fire Storm tick -- a mixed "
          "instant, not a payoff (the review's EV-6) -- 4 REMOVED by Remove Hex with 0 payoff, 3 "
          "ended on the target's death (2 striking an adjacent foe), 1 in the caster's death "
          "batch; takers 1..4 (10 / 5 / 5 / 1), every one a foe; 2 mixed instants; the observer "
          "struck 3 times with the 0x00CF -> [10] -> word prefix and Burning (3, 3.0) each; the "
          "caster's rank 13 -- the server's hex_end_damage(179, 13) is the tape's 72 on the "
          "ASSUMPTION the taker's armour factor is 1 (CORROBORATED, the armour is off the wire)",
          str({k: hs[k] for k in ("i_per_port", "i_scheduled", "i_removed", "i_target_died",
                                  "i_takers_hist", "i_observer_burning", "i_payoff_tick")}))
    check(_exact_185(hs)
          and hs["h_42_elsewhere"] == 0 and hs["h_42_on_observer"] == 1
          and len(hs["c_dazed"]) >= 1 and len(hs["c_cracked"]) >= 2
          and hs["c_cast_applied"] >= 20 and hs["c_environmental"] >= 30
          and hs["c_observer_no_id_corpus"].get("Crippled", 0) >= 4 and hs["c_observer_no_id_corpus"].get("Deep Wound", 0) >= 4
          and set(hs["c_effect_ids"]["Burning"]) == {25} and hs["c_effect_ids"]["Burning"][25] >= 5
          and hs["c_effect_ids"]["Cracked Armor"].get(29, 0) >= 2 and hs["c_effect_ids"]["Weakness"].get(29, 0) >= 9,
          "185 on the same tape (exact, per tape): 27 announces (17 / 4 / 3 / 3), 25 completed, 22 "
          "twins / 3 singles on the target, 4 casts mixing twins and singles, 647.300 the one "
          "target-single adjacent-twin; no twin without a Burning signal, one single (780.235) "
          "with a new one; the observer's Burning (9, 9.0) twice, the caster's 13 predicting both "
          "3 and 9; the ONE hex 0x0042 in the corpus is on the observer; [6, T, ids] on their "
          "tapes: 179 [1, 12] x28, 1097 [1, 12] x5 + [12] x1, Empathy [1, 4] x5, Lightning Strike "
          "none x14; 6 snares; the order census 24 of 25 ascending, the one exception 640.689 "
          "(the review's M12 / EV-12); Burning's [6] id on the witness tape 25 x3 and TWO observer "
          "Burnings (Mind Burn's twin) carry NO [6] at all (and corpus-wide the observer's Crippled "
          "and Deep Wound applies carry none either -- an id is not every condition's); corpus FLOORS: Dazed >= 1, Cracked "
          "Armor >= 2, every Burning id 25 (>= 5), id 29 shared by Weakness and Cracked Armor "
          "(a class, not a per-condition id -- the review's R34-8)",
          str({k: hs[k] for k in ("m_per_port", "m_twin", "m_single", "m_mixed", "l_adds",
                                  "l_not_ascending", "c_effect_ids", "c_observer_no_id")}))
    # EV-3: a later capture holding the SAME casts again is confirming evidence and must
    # redden nothing -- append a copy of the witness's 54071 connection under a new stamp
    import copy as _copy
    _src = [c for c in hc["conns"] if c.stamp == hexjoin.EXPECT_CAPTURE and str(c.port) == "54071"]
    _dup = _copy.copy(_src[0])
    _dup.stamp = "SYNTHETIC-CONFIRMING"
    hs2 = hexjoin.score(dict(hc, conns=list(hc["conns"]) + [_dup]))
    hv2 = hexjoin.verdicts(hs2)
    check(all(hv2.values()) and _exact_179(hs2) and _exact_185(hs2)
          and hs2["i_completed_corpus"] == hs["i_completed_corpus"] + 18
          and hs2["m_completed_corpus"] == hs["m_completed_corpus"] + 16
          and hs2["c_effect_ids"]["Burning"][25] == hs["c_effect_ids"]["Burning"][25] + 3
          and hs2["l_adds_corpus"]["179 [1, 12]"] == 46,
          "the arm: the witness's busiest connection appended again under another stamp leaves "
          "the verdict HOLDING and every exact number above unmoved while the corpus floors grow "
          "(+18 / +16 completions, +3 Burning ids, 179's [1, 12] 28 -> 46) -- the counts are "
          "scored per tape and confirming evidence cannot redden them (the review's EV-3 flipped "
          "the first port to THE READING FAILS this way)",
          str((hv2, hs2["i_completed_corpus"], hs2["m_completed_corpus"], hs2["i_takers_hist"])))

    print("\n13. the corpus: the CONVERTED hit's word (healjoin P6, RUN-SKILLS-RB)")
    # RUN-SKILLS-RB (2026-09-16, 20260916T213125): ten hits taken under
    # Reversal of Fortune at a cap of 50 -- the first prevention heals in the
    # corpus (F46.8 had counted zero). The zero is +0.0, never the graze's
    # -0.0; the rest are negative remainders; the heal precedes the damage.
    import healjoin
    cv = healjoin.score_conversions(healjoin.conversions())
    check(cv["n"] >= 10 and cv["zero_words"] >= 7 and cv["remainders"] >= 3
          and cv["plus_zero"] == cv["zero_words"]
          and cv["minus_zero_anywhere"] == 0 and cv["positive_damage"] == 0,
          "P6 a fully converted hit's damage word is +0.0 (0x00000000) and a "
          "partly converted one's is the negative remainder -- never -0.0, "
          "on the conversions or on the coincident self-heals beside them",
          f"{cv} -- floors 10 / 7 / 3 from the RB tape (a conversion is the "
          f"row with the enchantment's 0x0044 on the tick; the coincident rows "
          f"are Healing Signets closing under fire); a -0.0 here would mean "
          f"retail spells the converted zero like the graze after all")
    check(cv["n"] >= 10 and cv["heal_first"] == cv["n"],
          "and the heal word precedes the damage word on every conversion tick",
          f"heal first {cv['heal_first']} of {cv['n']} (the coincident rows: "
          f"{cv['coincident_heal_first']} of {cv['coincident']}, which is not "
          f"a claim) -- WIKI (GWW, \"Reversal of Fortune\" Notes): healing "
          f"before damage")

    print("\n14. the LABEL tier through the SAME consumers (SKILLS-LT, DESKWORK-D4 step 4)")
    # vault/content/skill_labels.toml -- `python toolkit/clientscan/skilldesc.py
    # --emit-labels` -- carries a `tier = "label"` skill_effect row per plain
    # SERVED skill (studies/skills 55). No second path: skill_damage and
    # skill_condition read the row exactly as they read a hand row, and
    # `World.drop_tier` (what --no-skill-labels does at startup) leaves the
    # server as it was before 2026-09-23. Skipped where the overlay is not
    # loaded: a bare machine, or one that has not regenerated it.
    lab = {k: r for k, r in agents.WORLD.rows("skill_effect").items()
           if r.get("tier") == "label"}
    if "187" not in lab or "220" not in lab:
        LEDGER.skip("14. the label tier (12 checks)",
                    "skill_labels.toml not loaded -- `python toolkit/clientscan/"
                    "skilldesc.py --emit-labels` regenerates it into vault/content/")
    else:
        import contextlib
        import io
        check(authsrv.skill_damage(187, 0) == (7, "standalone")
              and authsrv.skill_damage(187, 15) == (112, "standalone"),
              "a label-tier fire spell (187: scale 7..112 at str1, a Spell aimed at "
              "the burst's byte 16) resolves through skill_damage at both ends of "
              "the ladder -- the record's own numbers",
              (authsrv.skill_damage(187, 0), authsrv.skill_damage(187, 15)))
        check(authsrv.skill_condition(220, 0) == (479, 3.0)
              and authsrv.skill_condition(220, 15) == (479, 8.0),
              "a label-tier Blind (220: bonus 3..8 at str2, a foe Spell) resolves "
              "through skill_condition's first slot: 479 for 3 s at rank 0, 8 s "
              "at rank 15 (784 was this example until the fix pass excluded it: "
              "its chain requirement has no gate on a Spell)",
              (authsrv.skill_condition(220, 0), authsrv.skill_condition(220, 15)))
        check(lab["187"]["tier"] == "label" and "AREA_BURST" in lab["187"]["tier_detail"]
              and lab["187"].provenance["source"] == "client-table"
              and lab["187"].provenance["build"] == 38797
              and lab["220"]["tier_detail"] == ["TARGET_FOE"],
              "the rows say what they are: tier label, 187's area is spell_burst's "
              "(AREA_BURST), 220 reaches its one target; client-table provenance, "
              "build 38797", (dict(lab["187"]), dict(lab["220"])))
        check(authsrv.skill_label_tier(187) == list(lab["187"]["tier_detail"])
              and authsrv.skill_label_tier(312) is None
              and authsrv.skill_label_tier(999999) is None,
              "skill_label_tier -- what the per-cast log prints -- returns the label row's "
              "detail, None for a hand row (Holy Strike) and None for no row")
        # ENG-5: the per-cast line itself, and its two call sites in the source.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv._label_tier_note(187, 7, "the player's")
            authsrv._label_tier_note(312, 7, "the player's")
        out = buf.getvalue()
        check(out.startswith("[c7] the player's skill 187 resolves through a LABEL-tier row (")
              and "AREA_BURST" in out and "not hand-verified" in out and "--no-skill-labels" in out
              and out.count("\n") == 1 and "312" not in out,
              "_label_tier_note prints ONE line for a label-tier skill naming the tier "
              "and its detail, and nothing for a hand row (Holy Strike)", out)
        src = open(authsrv.__file__, encoding="utf-8").read()
        check(src.count('_label_tier_note(cast["skill_id"], conn_id, "the player\'s")') == 1
              and src.count('_label_tier_note(skill_id, conn_id, f"agent {agent_id}\'s")') == 1,
              "SOURCE LOCK: the note is called at the player's E5 and at a body's landing, "
              "once each")
        # ENG-4 / LT-R11: the revert flag's WIRING -- it parses, and main() drops the
        # tier before the listener opens (an early WORLD read would otherwise see it).
        import serverargs
        ap = serverargs.build_parser(
            doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
            HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
            GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
            VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
        i_main = src.index("\ndef main():")
        i_flag = src.index("    if a.no_skill_labels:", i_main)
        i_drop = src.index('drop_tier("skill_effect", agents.content.LABEL_TIER)', i_flag)
        i_listen = src.index("srv.listen(", i_main)
        check(ap.parse_args([]).no_skill_labels is False
              and ap.parse_args(["--no-skill-labels"]).no_skill_labels is True
              and i_main < i_flag < i_drop < i_listen and i_drop - i_flag < 200
              and "SKILL_LABELS" not in src.replace("NO SKILL LABELS", ""),
              "--no-skill-labels parses (default off), and main()'s block calls "
              "World.drop_tier(skill_effect, LABEL_TIER) BEFORE srv.listen; no dead "
              "SKILL_LABELS global is left to look load-bearing")
        # ENG-2 / LT-R7: the AREA_BURST mark agrees with the server's OWN predicate,
        # row by row -- spell_burst's radius AND a standalone damage to burst with
        # (118's area Weakness has the radius and no damage: one target here).
        lab_ids = sorted(int(k) for k in lab)

        def _bursts(sid):
            d = authsrv.skill_damage(sid, 0)
            return authsrv.spell_burst(sid) is not None and bool(d) and d[1] == "standalone"
        disagree = [s for s in lab_ids if ("AREA_BURST" in lab[str(s)]["tier_detail"]) != _bursts(s)]
        # 2026-09-26 (DESKWORK-D6 step 2, studies/weapons 42): 192 and 197 are HAND rows now --
        # areas over TIME the server serves through area_over_time, its own predicate -- so
        # they are no longer in the label tier; spell_burst still refuses both (a duration).
        check(disagree == [] and authsrv.spell_burst(192) is None and authsrv.spell_burst(197) is None
              and authsrv.spell_burst(187) == 156.0 and "192" not in lab and "197" not in lab
              and authsrv.area_over_time(192, 0) is not None
              and authsrv.area_over_time(197, 0) is not None
              and agents.WORLD.get("skill_effect", "192").get("tier") is None,
              f"AREA_BURST agrees with spell_burst + a standalone damage on all {len(lab_ids)} "
              f"label rows; the areas over time 192 and 197 are refused by spell_burst (a "
              f"duration) and served by area_over_time from their HAND rows, which shadow the "
              f"label rows (ONE_TARGET + DURATION_UNMODELLED) since 2026-09-26", disagree)
        # LT-R4 / SKILLS-LU: a shipped non-attack with a chain requirement carries the
        # CHAIN_GATED mark -- the player's E5 judges it (NONATTACK_CHAIN_GATE) -- and
        # 784 (combo_req 2, a Spell) is such a row once the overlay is regenerated
        # (skills 59); on the 2026-09-23 overlay before that it is simply absent.
        chained = [s for s in lab_ids
                   if authsrv.skill_chain_fields(s)[1] and not authsrv._is_attack_skill(s)]
        unmarked = [s for s in chained if "CHAIN_GATED" not in lab[str(s)]["tier_detail"]]
        check(unmarked == [] and authsrv.skill_chain_fields(784)[1] == 2
              and not authsrv._is_attack_skill(784)
              and ("784" not in lab or "CHAIN_GATED" in lab["784"]["tier_detail"])
              and authsrv.NONATTACK_CHAIN_GATE is True,
              f"every label row that is a non-attack with combo_req ({len(chained)} loaded) "
              f"carries CHAIN_GATED, the mark of the E5's non-attack chain gate; 784 -- "
              f"combo_req 2, a Spell -- carries it when present", (chained, unmarked))
        gone = agents.WORLD.drop_tier("skill_effect", "label")
        try:
            check(authsrv.skill_damage(187, 15) is None
                  and authsrv.skill_condition(220, 15) is None and len(gone) >= 40,
                  f"with the tier DROPPED (--no-skill-labels) both resolve to nothing "
                  f"-- the hand rows alone; {len(gone)} rows gone",
                  (authsrv.skill_damage(187, 15), authsrv.skill_condition(220, 15)))
            check(authsrv.skill_damage(312, 15) is not None
                  and authsrv.skill_condition(382, 15) is not None
                  and authsrv.skill_condition(320, 15) == (481, 15.0),
                  "and the hand rows are untouched by the drop: Holy Strike, Sever "
                  "Artery and Hamstring's 54.8 fix (Crippled 15 s) still resolve -- the "
                  "flag reverts the TIER, not the hand fixes of the same day")
        finally:
            agents.WORLD.tables["skill_effect"].update(gone)
        check(authsrv.skill_damage(187, 15) == (112, "standalone"),
              "restored: the label row resolves again (the drop is a removal, not a "
              "rewrite)")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
