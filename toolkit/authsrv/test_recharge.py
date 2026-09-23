"""test_recharge -- an NPC's per-slot recharge runs from the cast's COMPLETION, not its
start (DESKWORK-D5 step 4, 2026-09-23). The server change locked on the real cast tick;
the anchor read off the live corpus through rechargeprobe.

WHAT IT IS REALLY CHECKING. Both NPC cast sites armed `skill_ready[slot] = now +
recharge` at the cast's START, on a RECONSTRUCTION written when "no NPC in the corpus
casts twice". `rechargeprobe.py` reads the 36-capture corpus: six spells re-cast at
recharge + activation from the start -- the recharge runs from the cast's completion
(the 0x009F [58], at start + activation). The server now arms `skill_ready = now +
activation + recharge`; `--no-npc-recharge-from-completion` is the start-anchored arm.

  Section 1 (the sender, fixture-less) drives the REAL `enemy_attack_tick` and
  `ally_cast_tick` and reads `skill_ready[slot]` back -- the operand, not the
  predicate -- against both flag arms; a hostile with a two-slot bar so the arm is
  not the round-robin default. The known-bad arm is `--no-npc-recharge-from-completion`.
  Section 2 (the corpus, declared a skip without the vault) is `rechargeprobe`'s own
  verdict: the floor, the six completion-anchored skills, the 229 divergence named, the
  re-create split, the build coverage.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-23: section 1 (the sender, 8). Section 2 is a
# declared skip without the vault.
LEDGER = checks.Ledger("NPC recharge from completion", floor=8)
check = checks.adopt(LEDGER)

INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
# Two spells so the arm is a real pick, not slot 0 by default; activation != recharge
# and both > 0 so the two anchors are separable. (id, activation, recharge)
SPELL_A = (185, 1.0, 5.0)     # Lightning Strike: completion anchor 6.0, start 5.0
SPELL_B = (186, 1.5, 7.0)     # Lightning Surge


def _hostile(bar):
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 100.0,
          "player_dead": False}
    authsrv.effect_table(st)
    st["agents"][10] = {
        "name": "caster", "dead": False, "died_at": 0.0,
        "health": 50.0, "max_health": 100.0, "last_hit": 0.0,
        "pos": (85.0, 0.0), "plane": 0,
        "allegiance": agents.ALLEGIANCE_HOSTILE,
        "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
        "effects": 0, "attacks_back": True,
        "skills": bar, "skill_ready": [0.0] * len(bar),
        "last_swing": time.time() - 100.0}
    return st


def _party(bar):
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 100.0,
          "player_dead": False}
    authsrv.effect_table(st)
    st["agents"][20] = {
        "name": "a hero", "dead": False, "died_at": 0.0,
        "health": 50.0, "max_health": 100.0, "last_hit": 0.0,
        "pos": (5.0, 0.0), "plane": 0,
        "allegiance": agents.ALLEGIANCE_PLAYER,
        "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
        "effects": 0, "attacks_back": False,
        "skills": bar, "skill_ready": [0.0] * len(bar),
        "last_swing": time.time() - 100.0}
    # a hostile for the hero to cast at (its heal/attack needs a target)
    st["agents"][10] = {
        "name": "foe", "dead": False, "died_at": 0.0, "health": 50.0,
        "max_health": 100.0, "last_hit": 0.0, "pos": (12.0, 0.0), "plane": 0,
        "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
        "effects": 0, "attacks_back": True, "skills": ((1, 0.0, 0.0),),
        "skill_ready": [0.0], "last_swing": time.time() - 100.0}
    return st


def _drive(tick_fn, st, agent_id):
    """Run the tick until the agent starts a cast (casting is set); return
    (slot, skill, activation, recharge, skill_ready, now) or None."""
    sent = []
    send = lambda op, vals, why="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    for _ in range(6):
        now = time.time()
        tick_fn(send, st, 0)
        ag = st["agents"][agent_id]
        if ag.get("casting") is not None:
            slot = ag["casting"]
            sid, act, rec = ag["skills"][slot]
            return slot, sid, act, rec, ag["skill_ready"][slot], now
        time.sleep(0.01)
    return None


def section_sender():
    print("\n1. the sender: the arm lands at completion (now + activation + recharge)")
    saved = authsrv.NPC_RECHARGE_FROM_COMPLETION
    try:
        # the unit: npc_recharge_anchor
        authsrv.NPC_RECHARGE_FROM_COMPLETION = True
        check(authsrv.npc_recharge_anchor(1.5) == 1.5 and authsrv.npc_recharge_anchor(0.0) == 0.0,
              "npc_recharge_anchor returns the activation under the completion anchor",
              f"{authsrv.npc_recharge_anchor(1.5)}")
        authsrv.NPC_RECHARGE_FROM_COMPLETION = False
        check(authsrv.npc_recharge_anchor(1.5) == 0.0,
              "KNOWN-BAD ARM: npc_recharge_anchor returns 0 under --no-... (start anchor)",
              f"{authsrv.npc_recharge_anchor(1.5)}")
        # the operand, HOSTILE site, flag ON
        authsrv.NPC_RECHARGE_FROM_COMPLETION = True
        st = _hostile((SPELL_A, SPELL_B))
        got = _drive(authsrv.enemy_attack_tick, st, 10)
        check(got is not None, "the hostile started a cast within a few ticks",
              f"{got}")
        if got:
            slot, sid, act, rec, ready, now = got
            check(abs(ready - (now + act + rec)) < 0.05
                  and abs(ready - (now + rec)) > act - 0.05,
                  f"HOSTILE: skill_ready = now + activation({act}) + recharge({rec}) = "
                  f"completion + recharge, not now + recharge",
                  f"ready-now {ready - now:.3f}, expected {act + rec:.3f}")
        # the operand, HOSTILE site, flag OFF (the known-bad arm)
        authsrv.NPC_RECHARGE_FROM_COMPLETION = False
        st = _hostile((SPELL_A, SPELL_B))
        got = _drive(authsrv.enemy_attack_tick, st, 10)
        if got:
            slot, sid, act, rec, ready, now = got
            check(abs(ready - (now + rec)) < 0.05,
                  "KNOWN-BAD ARM: --no-npc-recharge-from-completion arms at the START "
                  "(now + recharge), the pre-2026-09-23 cadence",
                  f"ready-now {ready - now:.3f}, expected {rec:.3f}")
        else:
            check(False, "the hostile started a cast (known-bad arm)", f"{got}")
        # the operand, PARTY site, flag ON
        authsrv.NPC_RECHARGE_FROM_COMPLETION = True
        st = _party((SPELL_A, SPELL_B))
        got = _drive(authsrv.ally_cast_tick, st, 20)
        check(got is not None, "the party body started a cast within a few ticks", f"{got}")
        if got:
            slot, sid, act, rec, ready, now = got
            check(abs(ready - (now + act + rec)) < 0.05
                  and abs(ready - (now + rec)) > act - 0.05,
                  f"PARTY: skill_ready = now + activation({act}) + recharge({rec}), the "
                  f"same completion anchor as the hostile site",
                  f"ready-now {ready - now:.3f}, expected {act + rec:.3f}")
        # the operand, PARTY site, flag OFF
        authsrv.NPC_RECHARGE_FROM_COMPLETION = False
        st = _party((SPELL_A, SPELL_B))
        got = _drive(authsrv.ally_cast_tick, st, 20)
        if got:
            slot, sid, act, rec, ready, now = got
            check(abs(ready - (now + rec)) < 0.05,
                  "KNOWN-BAD ARM: the party site arms at the START under the flag",
                  f"ready-now {ready - now:.3f}, expected {rec:.3f}")
        else:
            check(False, "the party body started a cast (known-bad arm)", f"{got}")
    finally:
        authsrv.NPC_RECHARGE_FROM_COMPLETION = saved


def section_corpus():
    print("\n2. the corpus: rechargeprobe's verdict, the anchor and the 229 divergence")
    try:
        vaultpath.require_dir("captures", "live", why="the recharge anchor")
        vaultpath.require_dir("client", why="the per-build skill tables")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        LEDGER.skip("2. the corpus", str(exc))
        return
    import rechargeprobe
    c = rechargeprobe.census(split=True)
    sc = rechargeprobe.score(c)
    check(sc["p1"] and len(sc["skills_at_floor"]) >= 4,
          f"the floor holds: >= 4 skills with >= 5 completed pairs ({len(sc['skills_at_floor'])})",
          f"{sc['skills_at_floor']}")
    six = {185, 186, 179, 286, 222, 230}
    on_comp = {int(str(k).split("@")[0]) for k in sc["on_completion"]}
    check(six <= on_comp,
          "the six spells (185, 186, 179, 286, 222, 230) are COMPLETION-anchored: their "
          "min start-to-start sits at recharge + activation and min completion-to-next at "
          "the recharge",
          f"completion-anchored: {sorted(on_comp)}")
    check(sc["p2_completion_majority"],
          "COMPLETION is the majority anchor of the discriminating skills",
          f"{len(sc['on_completion'])} completion vs {len(sc['on_start'])} start "
          f"({sc['discriminating']})")
    check(229 in {int(str(k).split("@")[0]) for k in sc["on_start"]}
          and 229 in {int(k) for k in sc["sub_recharge"]},
          "229 (Lightning Orb) is the named divergence: it shows a sub-recharge "
          "completion-to-next gap (one clear at ~3.25 s), consistent with a staff HSR proc "
          "or a start-anchor for that skill alone -- OBSERVED, small n, not fitted away",
          f"on_start {sorted(sc['on_start'])}, sub_recharge {sc['sub_recharge']}")
    # the re-create split: pooling recycled ids does not manufacture a start-to-start
    # gap that the split removes below the recharge for any of the six.
    pooled = rechargeprobe.score(rechargeprobe.census(split=False))
    check(sc["recycled_creates"] > 0 and pooled["recycled_creates"] == sc["recycled_creates"],
          "the corpus recycles agent ids (the split is not a no-op), and the count is the "
          "same whether or not the keys are split",
          f"recycled creates {sc['recycled_creates']}")
    check(six <= {int(str(k).split("@")[0]) for k in pooled["on_completion"]},
          "the six stay completion-anchored with recycled ids pooled too -- their anchor "
          "is not an artifact of the split",
          f"pooled completion: {sorted(int(str(k).split('@')[0]) for k in pooled['on_completion'])}")
    check(sc["excluded_no_table"] == 0 and len(sc["connections_by_build"]) >= 2,
          "every connection's build has a table in the vault (no connection scored against "
          "the wrong build's numbers), over >= 2 builds",
          f"builds {sc['connections_by_build']}, excluded for no table {sc['excluded_no_table']}")


def main():
    print("test_recharge -- NPC recharge from the cast's completion (DESKWORK-D5 step 4)")
    section_sender()
    section_corpus()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
