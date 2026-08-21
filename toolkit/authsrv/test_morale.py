"""Morale and the death penalty: the arithmetic, the gate, and the wire tick.

WHAT IS ACTUALLY AT RISK HERE, because "a check that cannot fail is not a check"
and three of the sections below exist to catch a specific way of being wrong:

  * **The base-versus-total scale.** Morale scales the character's BASE health
    and energy, not the totals, and on the one observation this rung has that is
    the difference between 22 and 21.25. A future simplification to
    `total * morale / 100` reads cleaner, passes any test written around health
    (where base == total for our character), and is wrong. Section 1 pins the
    ENERGY number, which is the one that discriminates, and asserts the naive
    reading's answer is NOT what we produce.
  * **The gate.** Every map this server ships is pre-Searing, where retail
    charges nothing for a death. A default that fires would look like a working
    feature and would be a fabrication. Section 4 asserts the silence, and
    asserts the switch that breaks it.
  * **The revive.** The penalty lives in the maxima, and the single easiest way
    to delete the whole mechanic is to restore `PLAYER_HEALTH` when the player
    stands back up -- which is what that code did until 2026-08-20 and what it
    will do again the moment someone "fixes" the revive without knowing why.
    Section 5 puts a player back on their feet and reads the maximum.

The evidence for every number: studies/morale/FINDINGS.md, over
`vault/captures/live/20260817T183756` -- one player death, fully instrumented.
The one thing this file cannot check is what the CLIENT does with any of it;
that is MORALE-P1..P4 and it needs a screen.

standard library only, no vault, no socket.

    python toolkit/authsrv/test_morale.py
"""
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agents  # noqa: E402
import checks  # noqa: E402
import morale  # noqa: E402
from codec import Codec  # noqa: E402

# 48 on a green run with the shipped `REVIVE_REFILL_DEFER`; 47 with
# `RURIK_REVIVE_DEFER=0`, because section 6's revive branch checks one thing
# when the refill is immediate and two when it is deferred. The floor is the
# smaller of the two REAL runs rather than the larger, since a floor above what
# a healthy run produces is a test that fails for being configured differently.
LEDGER = checks.Ledger("morale and death penalty", floor=47)

# THE OBSERVATION, pinned as literals so this file states what it is testing
# against rather than deriving it from the code under test. Capture
# 20260817T183756, connection 10.0.0.210:52294->54.80.22.158:80, agent 27,
# t=78.813 -- a level-2 character with 120 maximum health and 25 maximum energy
# dies once and comes out at 102 and 22 with morale 85.
OBS_LEVEL = 2
OBS_TOTAL_HEALTH = 120
OBS_TOTAL_ENERGY = 25
OBS_MORALE = 85
OBS_MAX_HEALTH = 102
OBS_MAX_ENERGY = 22
OBS_DELTA_DWORD = 0xFFFFFFF1        # what -15 looked like on ArenaNet's wire
OBS_REGEN_BEFORE = 0.0528           # property 43 at 25 energy
OBS_REGEN_AFTER = 0.06              # ...and at 22, same absolute rate


def collect(fn, *a, **kw):
    """Run a server function with a recording `send`, return what it sent."""
    sent = []
    fn(lambda op, vals, why="": sent.append((op, vals, why)), *a, **kw)
    return sent


def main():
    import authsrv

    codec = Codec()

    # ---- 1. the arithmetic reproduces ArenaNet's own two numbers -------------
    print("1. the one observed death, recomputed")
    health = morale.effective_max(OBS_TOTAL_HEALTH,
                                  morale.base_health(OBS_LEVEL), OBS_MORALE)
    energy = morale.effective_max(OBS_TOTAL_ENERGY, morale.BASE_ENERGY,
                                  OBS_MORALE)
    LEDGER.ok(morale.base_health(OBS_LEVEL) == OBS_TOTAL_HEALTH,
              "a level-2 character's base health is the 120 the tape carried",
              f"{morale.base_health(OBS_LEVEL)} from 100 + 20 x (level - 1)")
    LEDGER.ok(health == OBS_MAX_HEALTH,
              f"and one death takes it to {OBS_MAX_HEALTH}", f"got {health}")
    LEDGER.ok(energy == OBS_MAX_ENERGY,
              f"maximum energy goes 25 -> {OBS_MAX_ENERGY}", f"got {energy}")
    naive = round(OBS_TOTAL_ENERGY * OBS_MORALE / 100.0)
    LEDGER.ok(naive != OBS_MAX_ENERGY,
              "and scaling the TOTAL instead of the base does not reach it",
              f"25 x 0.85 = 21.25, rounds to {naive}, observed "
              f"{OBS_MAX_ENERGY} -- this is the check that discriminates, and "
              f"it is why `base` is an argument rather than an assumption")
    LEDGER.ok(morale.base_health(1) == 100 and morale.base_health(20) == 480,
              "the level curve hits both of the wiki's published endpoints",
              f"level 1 -> {morale.base_health(1)}, "
              f"level 20 -> {morale.base_health(20)}")
    LEDGER.ok(morale.effective_max(OBS_TOTAL_HEALTH, OBS_TOTAL_HEALTH,
                                   morale.BASELINE) == OBS_TOTAL_HEALTH,
              "neutral morale changes nothing at all", "100 is the identity")
    LEDGER.ok(morale.effective_max(100, 100, morale.CEILING) == 110,
              "and a +10% boost is the same arithmetic upward", "110 of 100")

    # ---- 2. the bounds are the mechanic, not decoration ----------------------
    print("\n2. -60% is a floor and it is reachable in exactly four deaths")
    chain, value = [], morale.BASELINE
    for _ in range(6):
        value = morale.after_death(value)
        chain.append(value)
    LEDGER.ok(chain[:4] == [85, 70, 55, 40],
              "four deaths walk 100 -> 85 -> 70 -> 55 -> 40", str(chain[:4]))
    LEDGER.ok(chain[4] == morale.FLOOR and chain[5] == morale.FLOOR,
              "and the fifth and sixth cost nothing more",
              f"{chain[4]}, {chain[5]} against the {morale.FLOOR} floor")
    LEDGER.ok(morale.clamp(200) == morale.CEILING
              and morale.clamp(-5) == morale.FLOOR,
              "clamp holds both ends", "GWCA annotates the same 40..110 range")
    LEDGER.ok(morale.effective_max(1, 100, morale.FLOOR) >= 1,
              "and a pool can never be driven to zero",
              "GWW: a decrease 'will never reduce current health below 1'")
    try:
        morale.base_health(0)
        refused = False
    except ValueError:
        refused = True
    LEDGER.ok(refused, "a level of 0 is refused rather than answered",
              "base health is a function OF the level; 0 is not one")

    # ---- 3. experience buys it back, 1% at a time ---------------------------
    print("\n3. the PvE counter: 75 experience removes 1%")
    value, bank, got = morale.experience_credit(85, 0, 26)
    LEDGER.ok((value, bank, got) == (85, 26, 0),
              "one 26-XP kill moves nothing and banks the 26", str((value, bank, got)))
    value, bank, got = morale.experience_credit(value, bank, 26)
    LEDGER.ok((value, bank, got) == (85, 52, 0),
              "two kills still move nothing", str((value, bank, got)))
    value, bank, got = morale.experience_credit(value, bank, 26)
    LEDGER.ok((value, got) == (86, 1) and bank == 78 - morale.XP_PER_PERCENT,
              "the third crosses 75 and gives 1% back, banking the remainder",
              str((value, bank, got)))
    value, bank, got = morale.experience_credit(85, 0, 75 * 40)
    LEDGER.ok(value == morale.BASELINE and got == 15,
              "a big award clears the whole penalty and stops at neutral",
              f"{value} after {75 * 40} XP -- never a boost")
    LEDGER.ok(bank == 0,
              "and the leftover does NOT hoard against the next death",
              f"bank {bank}: GWW's counter removes penalty, it does not bank "
              f"morale, and a hoard would make the second death cheaper")
    LEDGER.ok(morale.experience_credit(morale.BASELINE, 0, 10_000)
              == (morale.BASELINE, 0, 0),
              "experience at neutral morale does nothing whatsoever",
              "which is every session in which nobody has died")

    # ---- 4. the gate: our own world charges nothing, and says why ------------
    print("\n4. pre-Searing charges nothing for a death")
    rules = agents.WORLD.rows("map_rule")
    maps = agents.WORLD.rows("map")
    LEDGER.ok(bool(rules), "the map_rule table exists", f"{len(rules)} row(s)")
    orphans = [k for k in rules if k not in maps]
    LEDGER.ok(not orphans,
              "every map_rule key names a map row that exists",
              f"orphans: {orphans} -- two tables keyed by map id drift the day "
              f"one of them is edited alone")
    LEDGER.ok(authsrv.map_death_penalty(146) is False
              and authsrv.map_death_penalty(148) is False,
              "Lakeside County and Ascalon City charge nothing",
              "GWW: 'Deaths in pre-Searing Ascalon' never incur DP -- and 146 "
              "is the map every combat run of this project has used")
    LEDGER.ok(authsrv.map_death_penalty(90) is True,
              "a post-Searing explorable does charge",
              "Lornar's Pass, map_rule.90 -- so the falses above are a "
              "decision rather than the only shape this table has")
    LEDGER.ok(authsrv.map_death_penalty(999_999) is False,
              "and a map nobody has ruled on gets the safer wrong answer",
              "the map_explorable argument: fail to apply, never invent")

    state = {"map_id": 146, "level": 1}
    authsrv.player_pools(state)
    sent = collect(authsrv.kill_player, state, 1, "test")
    ops = [op for op, _v, _w in sent]
    LEDGER.ok(authsrv.GAME_SMSG_AGENT_MORALE not in ops
              and authsrv.GAME_SMSG_PLAYER_ATTR_UPDATE not in ops,
              "a death in Lakeside County puts no morale on the wire",
              f"{[hex(o) for o in ops]}")
    LEDGER.ok(state["morale"] == morale.BASELINE,
              "and leaves morale neutral", str(state["morale"]))

    # ---- 5. ...and with the switch on, it is ArenaNet's own tick -------------
    print("\n5. the death tick, in the order the capture carries it")
    authsrv.DEATH_PENALTY_FORCED = True
    try:
        # THE SHIPPED CHARACTER, not the capture's, and the difference is
        # worth a paragraph. Section 1 checks the ARITHMETIC against ArenaNet's
        # own two numbers; this section checks the WIRE, and the wire has to
        # carry the character this server actually serves -- level 1, 100 total
        # health, 25 total energy. Forcing the capture's level 2 into our own
        # content makes a level-2 character with 100 total health, which retail
        # could never send, and every number downstream of it would be
        # self-consistent nonsense. The energy figure survives the swap intact
        # (both characters carry 25 over base 20), so 22 below IS the capture's.
        ours_health = morale.effective_max(agents.PLAYER_HEALTH,
                                           morale.base_health(1), OBS_MORALE)
        ours_energy = morale.effective_max(agents.PLAYER_ENERGY,
                                           morale.BASE_ENERGY, OBS_MORALE)
        state = {"map_id": 146, "level": 1}
        authsrv.player_pools(state)
        sent = collect(authsrv.kill_player, state, 1, "test")
        ops = [op for op, _v, _w in sent]
        LEDGER.ok(state["morale"] == OBS_MORALE,
                  f"one death leaves morale at {OBS_MORALE}",
                  str(state["morale"]))
        LEDGER.ok(ops[0] == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS,
                  "the death bit goes first", f"{[hex(o) for o in ops]}")
        LEDGER.ok(ops[1] == authsrv.GAME_SMSG_AGENT_MORALE,
                  "then the absolute morale, per agent (0x009C)",
                  f"{[hex(o) for o in ops]}")
        LEDGER.ok(ops[2] == authsrv.GAME_SMSG_PLAYER_ATTR_UPDATE,
                  "then the delta, per player (0x00EE)",
                  f"{[hex(o) for o in ops]}")
        LEDGER.ok(ops[3:6] == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                               authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
                               authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT],
                  "then energy max, energy regen, health max",
                  f"{[hex(o) for o in ops]}")
        by_op = {}
        for op, vals, _why in sent:
            by_op.setdefault(op, []).append(vals)
        LEDGER.ok(by_op[authsrv.GAME_SMSG_AGENT_MORALE][0]
                  == [authsrv.PLAYER_AGENT_ID, OBS_MORALE],
                  "0x009C carries [player, 85]",
                  str(by_op[authsrv.GAME_SMSG_AGENT_MORALE][0]))
        attr = by_op[authsrv.GAME_SMSG_PLAYER_ATTR_UPDATE][0]
        LEDGER.ok(attr == [authsrv.PLAYER_ATTR_MORALE_ID, OBS_DELTA_DWORD],
                  "and 0x00EE carries attr 10 with the wire's own 0xFFFFFFF1",
                  f"{[hex(v) for v in attr]} -- -15 two's-complement, read off "
                  f"the capture rather than computed from a sign convention")
        ints = by_op[authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
        maxima = {v[0]: v[2] for v in ints}
        LEDGER.ok(maxima.get(agents.PROP_HEALTH_MAX) == ours_health,
                  f"the new maximum health is {ours_health}",
                  f"{maxima} -- 100 total over base 100 at level 1, less 15%")
        LEDGER.ok(maxima.get(agents.PROP_ENERGY_MAX)
                  == ours_energy == OBS_MAX_ENERGY,
                  f"the new maximum energy is the capture's own "
                  f"{OBS_MAX_ENERGY}",
                  f"{maxima} -- our character carries the same 25 total over "
                  f"the same base 20, so this number IS ArenaNet's")
        regen = [v for v in by_op[
            authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
            if v[0] == agents.PROP_ENERGY_REGEN]
        rate = struct.unpack("<f", struct.pack("<I", regen[0][3]))[0]
        rescaled = morale.regen_fraction(OBS_REGEN_BEFORE, OBS_TOTAL_ENERGY,
                                         OBS_MAX_ENERGY)
        LEDGER.ok(abs(rescaled - OBS_REGEN_AFTER) < 1e-6,
                  "the rescale reproduces the capture's own 0.0528f -> 0.06f",
                  f"{rescaled:.6f} -- 1.32 energy/s on either side of the "
                  f"death, which is what named property 43 at all")
        LEDGER.ok(abs(rate * ours_energy
                      - agents.PLAYER_FLOAT_43 * agents.PLAYER_ENERGY) < 1e-6,
                  "and our own resend keeps the ABSOLUTE rate unchanged",
                  f"{rate:.6f} x {ours_energy} = "
                  f"{rate * ours_energy:.4f}/s -- the property is a fraction "
                  f"OF the pool, so a silent 15% slowdown is what not resending "
                  f"it would cost")

        # every message the tick produced has to survive the codec, because a
        # field this server has never sent before is exactly where an encode
        # blows up at runtime, on the burst thread, mid-death.
        bad = []
        for op, vals, _why in sent:
            try:
                codec.encode("GAME_SMSG", op, vals)
            except Exception as exc:                   # noqa: BLE001
                bad.append((hex(op), str(exc)))
        LEDGER.ok(not bad, "and every message of it encodes on the wire",
                  f"refused: {bad}")

        # ---- 6. the revive does not hand the penalty back -------------------
        print("\n6. standing back up restores the pools, not the maxima")
        state["player_died_at"] = 0.0          # long enough ago to be due
        sent = collect(authsrv.player_revive_due, state, 1)
        health_max = [v[2] for op, v, _w in sent
                      if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                      and v[0] == agents.PROP_HEALTH_MAX]
        deferred = state.get("player_refill_due_at")
        if health_max:
            LEDGER.ok(health_max[0] == ours_health,
                      "the revive re-sends the REDUCED maximum",
                      f"{health_max} -- restoring PLAYER_HEALTH here deletes "
                      f"the mechanic from the least obvious place")
        else:
            LEDGER.ok(deferred is not None,
                      "the revive deferred its refill (REVIVE_REFILL_DEFER)",
                      "the maximum rides the deferred half; checked next")
            state["player_refill_due_at"] = time.time() - 1.0
            sent = collect(authsrv.player_refill_due, state, 1)
            health_max = [v[2] for op, v, _w in sent
                          if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                          and v[0] == agents.PROP_HEALTH_MAX]
            LEDGER.ok(health_max and health_max[0] == ours_health,
                      "and the deferred refill re-sends the REDUCED maximum",
                      f"{health_max}")
        LEDGER.ok(state["player_dead"] is False,
                  "the player is alive again", str(state["player_dead"]))
        LEDGER.ok(state["morale"] == OBS_MORALE,
                  "with the death penalty still on them",
                  f"morale {state['morale']} -- retail's own revive left the "
                  f"reduced maxima standing")
        LEDGER.ok(state["player_health"] == float(ours_health),
                  "and their health topped up to the penalised maximum",
                  str(state["player_health"]))

        # ---- 7. and experience walks it back -------------------------------
        print("\n7. kills buy the penalty back at the wiki's rate")
        before = state["morale"]
        for _ in range(2):
            collect(authsrv.morale_experience, state, 1,
                    authsrv.KILL_REWARD_VALUE)
        LEDGER.ok(state["morale"] == before,
                  "two 26-XP kills are not a percent yet", str(state["morale"]))
        sent = collect(authsrv.morale_experience, state, 1,
                       authsrv.KILL_REWARD_VALUE)
        LEDGER.ok(state["morale"] == before + 1,
                  "the third one is", str(state["morale"]))
        LEDGER.ok(any(op == authsrv.GAME_SMSG_AGENT_MORALE for op, _v, _w in sent),
                  "and it goes out on the same two channels the death used",
                  f"{[hex(op) for op, _v, _w in sent]}")
        collect(authsrv.morale_experience, state, 1, 75 * 100)
        LEDGER.ok(state["morale"] == morale.BASELINE,
                  "enough of them clear it entirely, and stop at neutral",
                  f"{state['morale']} -- never a morale BOOST from experience")
    finally:
        authsrv.DEATH_PENALTY_FORCED = False

    # ---- 8. the shipped world is unchanged ---------------------------------
    print("\n8. nothing above moved the default world")
    LEDGER.ok(authsrv.DEATH_PENALTY_FORCED is False,
              "the force switch is off again", "a test that leaks a global "
              "into the next test in the same process is a haunted suite")
    LEDGER.ok(authsrv.map_death_penalty(146) is False,
              "and Lakeside County is back to charging nothing",
              "which is what retail does there")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
