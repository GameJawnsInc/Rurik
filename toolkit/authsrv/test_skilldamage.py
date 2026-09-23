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
LEDGER = checks.Ledger("skill damage", floor=68)  # 2026-09-23 SKILLS-LT +1 (sec.3: Hamstring inflicts through the bonus slot); 2026-09-17 SKILLS-LR +4 (the location roll: three unit, one corpus); 2026-09-16 RUN-SKILLS-RB +2 (section 13, the converted word); 2026-09-16 SLICE-F47 +1 (the penalty split in whole points); 2026-09-14 HEAL-INT +1, ZEROWORD +1;   # MANTID-S +1: the player-side control beside the foe-side refusal
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
        cm.player_armour_at = lambda key, physical, *_a: lopsided.get(key)
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
    st_z, dmg_z = _cast(194, spell_armour_for=lambda _sid: 300.0)
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

    print("\n12. the corpus: one caster, one skill, one target is ONE value "
          "(spellhitjoin)")
    # P1-P4 in spellhitjoin's own words. A location roll on a set whose
    # pieces differ would put a second bucket on some pair; none has one.
    # FLOORS, not exact values -- the live corpus grows.
    try:
        import spellhitjoin
        sc = spellhitjoin.score(spellhitjoin.census())
    except Exception as exc:                              # noqa: BLE001
        LEDGER.skip("12. the corpus (spellhitjoin)",
                    f"no live corpus to read on this machine: {exc!r}")
        return LEDGER.verdict()
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
    lb = spellhitjoin.location_buckets(spellhitjoin.census())
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
    if "187" not in lab or "784" not in lab:
        LEDGER.skip("14. the label tier (5 checks)",
                    "skill_labels.toml not loaded -- `python toolkit/clientscan/"
                    "skilldesc.py --emit-labels` regenerates it into vault/content/")
    else:
        check(authsrv.skill_damage(187, 0) == (7, "standalone")
              and authsrv.skill_damage(187, 15) == (112, "standalone"),
              "a label-tier fire spell (187: scale 7..112 at str1, a Spell aimed at "
              "the burst's byte 16) resolves through skill_damage at both ends of "
              "the ladder -- the record's own numbers",
              (authsrv.skill_damage(187, 0), authsrv.skill_damage(187, 15)))
        check(authsrv.skill_condition(784, 0) == (484, 5.0)
              and authsrv.skill_condition(784, 15) == (484, 20.0),
              "a label-tier Poison (784: scale 5..20 at str1, a foe Spell) resolves "
              "through skill_condition's second slot: 484 for 5 s at rank 0, 20 s "
              "at rank 15",
              (authsrv.skill_condition(784, 0), authsrv.skill_condition(784, 15)))
        check(lab["187"]["tier"] == "label" and "AREA_BURST" in lab["187"]["tier_detail"]
              and lab["187"].provenance["source"] == "client-table"
              and lab["187"].provenance["build"] == 38797
              and lab["784"]["tier_detail"] == ["TARGET_FOE"],
              "the rows say what they are: tier label, 187's area is spell_burst's "
              "(AREA_BURST), 784 reaches its one target; client-table provenance, "
              "build 38797", (dict(lab["187"]), dict(lab["784"])))
        gone = agents.WORLD.drop_tier("skill_effect", "label")
        try:
            check(authsrv.skill_damage(187, 15) is None
                  and authsrv.skill_condition(784, 15) is None and len(gone) >= 50,
                  f"with the tier DROPPED (--no-skill-labels) both resolve to nothing "
                  f"-- the server before 2026-09-23; {len(gone)} rows gone",
                  (authsrv.skill_damage(187, 15), authsrv.skill_condition(784, 15)))
            check(authsrv.skill_damage(312, 15) is not None
                  and authsrv.skill_condition(382, 15) is not None,
                  "and the hand rows are untouched by the drop: Holy Strike and Sever "
                  "Artery still resolve")
        finally:
            agents.WORLD.tables["skill_effect"].update(gone)
        check(authsrv.skill_damage(187, 15) == (112, "standalone"),
              "restored: the label row resolves again (the drop is a removal, not a "
              "rewrite)")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
