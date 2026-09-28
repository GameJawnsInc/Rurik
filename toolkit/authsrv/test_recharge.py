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
  It also proves the re-create SPLIT on a synthetic sequence (the route's acceptance
  (c)): one id, a cast, a remove, a re-create, the same skill 1 s later -- pooled reads
  a sub-recharge pair, split reads none. Section 2 (the corpus, declared a skip without
  the vault) is `rechargeprobe`'s own verdict: the floor, the six completion-anchored
  skills, the 229 divergence named, P2 and P3 AS WRITTEN recorded FAILED (the
  re-statement is what the anchor rests on), the split changing the corpus's pair count
  (and nothing else), the build coverage.

THE ZAISHEN CAPTURE (2026-09-28, CASTAI-Z1, 20260928T103123) turned three corpus checks red
without a line of the server moving: the Zaishen Mage casts Fireball 186 at 1.005 s (a [61]
cast-time word ahead of the announce, commit 974f8748's mechanism) so 186's as-written
minimum left the completion-anchored set, and skill 102 brought a second sub-recharge gap.
Every exact number is now scored on the corpus AS OF THE PIN (captures before that stamp:
`rechargeprobe.upto`), where it reproduces exactly (227 / 233 pairs, the six, {229}); the
whole corpus carries the re-statement (each pair against its cast's own time), the
signature (the split and pooled arms agree on every sub-recharge gap) and the new fact
with its own exact per-tape witness. The gapped connection of that capture is set aside by
name from its manifest and asserted still refused.

THE FIX PASS (2026-09-23, D5B-R3 / ENG-2): the first cut's "the split is not a no-op"
check compared `recycled_creates` across the two arms -- a counter the split does not
touch -- and stayed green with the split disabled. Replaced by the synthetic sequence
above and by the pair-count difference (227 split vs 233 pooled), either of which reddens
when `gaps_of` ignores `split`.
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

# Floor from the green run of 2026-09-23 (fix pass): section 1 (the sender, 8, plus
# the synthetic split, 2 = 10). Section 2 is a declared skip without the vault.
LEDGER = checks.Ledger("NPC recharge from completion", floor=10)
check = checks.adopt(LEDGER)

INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
# Two spells so the arm is a real pick, not slot 0 by default; activation != recharge
# and both > 0 so the two anchors are separable. (id, activation, recharge) -- the
# table rows of two corpus spells (185: 1.0 / 5, completion anchor 6.0, start 5.0;
# 186: 1.5 / 7). Named by id only: the first cut's name comments were wrong (D5B-R7).
SPELL_A = (185, 1.0, 5.0)
SPELL_B = (186, 1.5, 7.0)


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
    # THE SPLIT ON A SYNTHETIC RE-CREATED ID (the route's acceptance (c); no vault):
    # agent 7 is created, casts skill 186 (act 1.5 / rec 7), completes it, is removed,
    # is re-created under the same id and casts 186 again 1 s after the first cast's
    # completion. Pooled, that reads as one body's 2.5 s cycle against a 7 s recharge;
    # split at the create, the two casts are two bodies and no pair exists.
    import rechargeprobe
    A0 = rechargeprobe.OP_INT_TARGET
    A1 = rechargeprobe.OP_INT
    seq = [(0, 10.0, rechargeprobe.OP_CREATE, [0x20, 7, 0, 0]),
           (1, 12.0, A0, [0xA0, 60, 7, 1, 186]),          # cast 186 at the player (1)
           (2, 13.5, A1, [0x9F, 58, 7, 0]),               # its completion
           (3, 13.6, rechargeprobe.OP_REMOVE, [0x21, 7]),
           (4, 14.0, rechargeprobe.OP_CREATE, [0x20, 7, 0, 0]),   # a NEW body, same id
           (5, 14.5, A0, [0xA0, 60, 7, 1, 186]),          # 1.0 s after the completion
           (6, 16.0, A1, [0x9F, 58, 7, 0])]
    pooled, rec_p, n_p = rechargeprobe.gaps_of(seq, player=1, split=False)
    split, rec_s, n_s = rechargeprobe.gaps_of(seq, player=1, split=True)
    p_pairs = pooled.get((7, 186), [])
    check(n_p == 2 and rec_p == 1 and len(p_pairs) == 1
          and p_pairs[0]["done"] is not None and p_pairs[0]["done"] < 7.0 - rechargeprobe.TOL
          and abs(p_pairs[0]["gap"] - 2.5) < 1e-6,
          "KNOWN-BAD ARM (pooled): a re-created id's two casts read as ONE body's 2.5 s "
          "cycle -- a completion-to-next gap of 1.0 s against a 7 s recharge, the "
          "sub-recharge pair a recycled id manufactures",
          f"pairs {p_pairs}, recycled {rec_p}, announcements {n_p}")
    check(n_s == 2 and rec_s == 1 and split.get((7, 186), []) == [],
          "the SPLIT at the create: the two casts are two bodies, no pair -- the "
          "manufactured gap is gone (the split works; on the live corpus it moves six "
          "pairs and no minimum, and 229's short gaps are on singly-created bodies)",
          f"pairs {split.get((7, 186))}, recycled {rec_s}, announcements {n_s}")


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
    # THE PIN (2026-09-28, CASTAI-Z1): every exact number below was pinned on the corpus as
    # it stood before 20260928T103123 (the Zaishen Challenge). It is scored THERE, exactly as
    # written; the whole corpus carries the floors, the signatures and the re-statement.
    PIN = "20260928T103123"
    scp = rechargeprobe.score(rechargeprobe.upto(c, PIN))
    ids = lambda keys: {int(str(k).split("@")[0]) for k in keys}   # noqa: E731
    check(sc["p1"] and len(sc["skills_at_floor"]) >= 4,
          f"the floor holds: >= 4 skills with >= 5 completed pairs ({len(sc['skills_at_floor'])})",
          f"{sc['skills_at_floor']}")
    # R4: the first gapped live connection is set aside BY NAME from its capture's own
    # manifest, and still refuses; nothing else in the corpus fails to frame
    GAPPED = [(PIN, "10.0.0.210:65009->98.95.137.136:80")]
    check([e[:2] for e in c["set_aside"]] == GAPPED and not c["declared_not_refused"]
          and not c["excluded"],
          "the one connection the manifests declare gapped (20260928T103123 :65009, CASTAI-Z1's "
          "match 2) is set aside BY NAME and still refused; no other connection is excluded "
          "(a new gap or an unframed tape reddens this -- it is seen, never absorbed)",
          f"set aside {c['set_aside']}, declared but whole {c['declared_not_refused']}, "
          f"excluded {c['excluded']}")
    six = {185, 186, 179, 286, 222, 230}
    on_comp = ids(scp["on_completion"])
    check(six <= on_comp,
          "the six spells (185, 186, 179, 286, 222, 230) are COMPLETION-anchored: their "
          "min start-to-start sits at recharge + activation and min completion-to-next at "
          "the recharge (AS WRITTEN, on the corpus as it stood at the pin -- 227 completed "
          "pairs split / 233 pooled, the numbers the fix pass pinned)",
          f"completion-anchored: {sorted(on_comp)}, pairs {scp['pairs']}")
    # CASTAI-Z1 (20260928T103123): the Zaishen Mage (agent 9) casts Fireball 186 at 1.005 s
    # (a [61] word ahead of the announce) against the record's 1.5, so AS WRITTEN 186's
    # start-to-start minimum on the whole corpus is 7.999 = 7 + 1.005 and 186 reads "neither".
    # The re-statement reads each pair against ITS cast's own time (no free parameter; the
    # as-written reading wherever no [61] was sent) and the six hold on the whole corpus.
    on_comp_r = ids(sc["on_completion_r"])
    new186 = sorted((r["port"], r["caster"], len(r["gaps"]), len(r["ct_pairs"]),
                     min(r["gaps"]), min(r["net"]))
                    for r in c["rows"] if r["capture"] == PIN and r["skill"] == 186)
    check(six <= on_comp_r and 186 not in ids(sc["on_completion"])
          and 186 in ids(sc["neither"])
          and new186 == [("50061", 9, 9, 8, 8.424, 7.419), ("50295", 9, 6, 4, 7.999, 6.994)]
          and sc["cast_time_pairs"].get(186) == (12, [1.005])
          and scp["cast_time_pairs"].get(186) is None,
          "RE-STATED on the whole corpus with each cast's own time (the [61] seconds when "
          "sent, else the activation): the six stay COMPLETION-anchored; AS WRITTEN 186 "
          "FAILS there (reads 'neither') on 20260928T103123's shortened casts (exact, per "
          "tape: agent 9's 186 on 50061 9 completed pairs, 8 with [61] 1.005, and on 50295 "
          "6, 4 with it; the minimum 7.999 at 489.932 carried 1.005 -> 6.994 against 7) -- "
          "a seventh or eighth skill (277, 2809) joining is confirming evidence, a subset "
          "cannot redden on it",
          f"re-stated completion-anchored {sorted(on_comp_r)}; as written "
          f"{sorted(ids(sc['on_completion']))}; the tape's 186 {new186}; [61] pairs "
          f"{sc['cast_time_pairs']}")
    check(sc["p2_completion_majority"],
          "RE-STATED P2: COMPLETION is the majority anchor of the discriminating skills",
          f"{len(sc['on_completion'])} completion vs {len(sc['on_start'])} start "
          f"({sc['discriminating']})")
    check(sc["p2_as_written"] is False and len(sc["neither"]) >= 1,
          "P2 AS WRITTEN is recorded FAILED on this corpus (229 start-like, four skills "
          "above both anchors) -- the verdict rests on the disclosed re-statement, not on "
          "the registered wording (goes red the day every skill lines up, which would "
          "retire the re-statement)",
          f"p2_as_written {sc['p2_as_written']}, neither {sorted(sc['neither'])}")
    check(229 in {int(str(k).split("@")[0]) for k in sc["on_start"]}
          and 229 in {int(k) for k in sc["sub_recharge"]},
          "229 (Lightning Orb) is the named divergence: it shows a sub-recharge "
          "completion-to-next gap (one clear at ~3.25 s), consistent with a staff HSR proc "
          "or a start-anchor for that skill alone -- OBSERVED, small n, not fitted away",
          f"on_start {sorted(sc['on_start'])}, sub_recharge {sc['sub_recharge']}")
    # THE RE-CREATE SPLIT ON THE CORPUS (fix pass): the split CHANGES the pair count
    # (it drops the pairs that cross a create -- 227 split vs 233 pooled) and nothing
    # else -- P3 as written FAILED on both arms: both read 229's two sub-recharge gaps,
    # so the survey's recycled-id explanation of 229 is refuted, and the six's anchor
    # is not an artifact of the split. `gaps_of` ignoring `split` reddens the first.
    cpool = rechargeprobe.census(split=False)
    pooled = rechargeprobe.score(cpool)
    pooledp = rechargeprobe.score(rechargeprobe.upto(cpool, PIN))
    check(sc["recycled_creates"] > 0 and pooled["pairs"] > sc["pairs"],
          "the split drops the pairs that cross a re-create: fewer completed pairs split "
          "than pooled (the corpus recycles ids; a `gaps_of` that ignores `split` reddens this)",
          f"pairs split {sc['pairs']} vs pooled {pooled['pairs']}, recycled creates "
          f"{sc['recycled_creates']}")
    check(scp["pairs"] == 227 and pooledp["pairs"] == 233,
          "the corpus AS OF THE PIN reproduces the fix pass's pinned pair counts exactly: 227 "
          "split vs 233 pooled (the scorer did not drift; the new capture is the whole change)",
          f"at the pin: split {scp['pairs']} pooled {pooledp['pairs']}; whole corpus: split "
          f"{sc['pairs']} pooled {pooled['pairs']}")
    check(scp["p3_as_written"] is False
          and scp["sub_recharge"] == pooledp["sub_recharge"] and set(scp["sub_recharge"]) == {229},
          "P3 AS WRITTEN is recorded FAILED: 229's two sub-recharge gaps survive the split "
          "(its half fails) and the pooled arm shows exactly the same two, so the arms do not "
          "DIFFER as P3 required -- 229's are on singly-created bodies, not recycled ids (the "
          "survey's explanation of 229 refuted) (on the corpus as it stood at the pin)",
          f"split {scp['sub_recharge']} pooled {pooledp['sub_recharge']}")
    # CASTAI-Z1: a second skill with a sub-recharge gap. 102 (recharge 15, activation 2.0),
    # agent 4 on 20260928T103123 :58544: cast at 591.381, completed, cast again 10.749 s later
    # -- completion-to-next 8.739. No [61] on either cast, and the pooled arm shows the same
    # gap (not a recycled id). OBSERVED, n = 1, cause unmeasured: a finding, not fitted.
    new102 = [(r["port"], r["caster"], [(p["t"], p["gap"], p["done"], p["ct"]) for p in r["pairs"]])
              for r in c["rows"] if r["capture"] == PIN and r["skill"] == 102
              and any(d < r["recharge"] - rechargeprobe.TOL for d in r["done"])]
    check(sc["p3_as_written"] is False and sc["sub_recharge"] == pooled["sub_recharge"]
          and sc["sub_recharge"].get(229) == [4.497, 3.251]
          and new102 == [("58544", 4, [(591.381, 10.749, 8.739, None), (602.13, 17.496, 15.507, None)])],
          "and on the whole corpus the arms still AGREE on every sub-recharge gap (the "
          "signature: no sub-recharge gap is a recycled id's), 229's two unmoved (exact); the "
          "new one is 102's 8.739 against 15 -- agent 4 on 20260928T103123 :58544 at 591.381, "
          "no [61] word (exact, per tape) -- a second named divergence, OBSERVED n = 1",
          f"split {sc['sub_recharge']} pooled {pooled['sub_recharge']}; 102 on the tape {new102}")
    check(six <= ids(pooledp["on_completion"]) and six <= ids(pooled["on_completion_r"]),
          "the six stay completion-anchored with recycled ids pooled too -- their anchor "
          "is not an artifact of the split (as written at the pin; re-stated on the whole "
          "corpus)",
          f"pooled completion at the pin: {sorted(ids(pooledp['on_completion']))}; whole "
          f"corpus re-stated: {sorted(ids(pooled['on_completion_r']))}")
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
