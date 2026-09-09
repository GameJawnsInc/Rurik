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

import os
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
LEDGER = checks.Ledger("skill damage", floor=44)   # SKILLS-HN +4, from the green run
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
                                  (253, "Duration", "Scourge Sacrifice"),
                                  (318, "+ Maximum health", "Defy Pain"),
                                  (320, "Crippled duration", "Hamstring")):
        row = agents.WORLD.get("skill_effect", str(skill_id))
        check(authsrv.skill_damage(skill_id, 15) is None
              and row["scale_means"] == means,
              f"{name} deals NO damage -- its scale is {means!r}",
              "returning None rather than 0, so a caller must decide what an "
              "unmodelled skill means instead of silently dealing nothing")

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
    check(authsrv.player_rank_for_skill(322) == 12
          and authsrv.player_rank_for_skill(323) == 1,
          "Power Attack reads Strength (12), Desperation Blow reads Tactics (1)",
          "same scale endpoints, different attributes -- so the ranks are what "
          "separate them")
    pa = authsrv.skill_damage(322, authsrv.player_rank_for_skill(322))
    db = authsrv.skill_damage(323, authsrv.player_rank_for_skill(323))
    check(pa[0] == 34 and db[0] == 12,
          "so Power Attack adds 34 and Desperation Blow adds 12",
          f"{pa} vs {db} -- identical 10->40 tables, 22 points apart because "
          f"the ranks differ. This is what 'the server models no attribute "
          f"ranks' cost us")
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
          and sent[0][0] == effects.OP_EFFECT_APPLY
          and sent[0][1][1] == 478,
          "and it goes out as an ordinary 0x0042 naming the CONDITION's id",
          f"{sent[0][1] if sent else sent} -- not the inflicting skill's. "
          f"That is what retail carries: the corpus's six condition applies "
          f"name 480 and 481, never the skill that caused them")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
