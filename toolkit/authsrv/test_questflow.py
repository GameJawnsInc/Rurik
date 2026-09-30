"""Quest accept and hand-in shapes -- QUESTFLOW (studies/presearing/RANGERPRE.md).

One section per landed part; the parts land one step at a time.

WHAT THIS CHECKS:
  * RANGERPRE-S5 (QUESTFLOW-H1), THE SKILLS COME LAST. A hand-in's
    reward_skills (0x00DC, 0x00D9, and 0x001C for a skill new to the account)
    go out AFTER the xp 0x00EE [0, xp] and the gold 0x0140, and before the
    closing 0x004A. OBSERVED on every retail hand-in that grants skills -- 4
    of the 22 hand-ins in the live corpus (2026-09-29), all four pinned below.
    Ours sent them FIRST until S5; --quest-skills-first is that order, kept as
    the KNOWN-BAD arm that reddens the same predicate.
      §1 (bare): grant_quest_reward and turn_in_quest reduce to the tape's
         order; a skills-only row still grants (the early return does not
         swallow them); the flag parses and main() flips it.
      §2 (vault-gated per capture, and it FAILS rather than skips once a
         capture is on disk): the four witnesses satisfy the predicate; OURS
         for :55934's own row equals that batch op for op on the reduced kinds
         (skill ids and bar slots included, the tape's doubled 0x0052
         collapsed); a sabotaged tape reddens the predicate.
  * RANGERPRE-S8 (QUESTFLOW-H3), THE QUEST-COMPLETE VISUAL. The message right
    after a hand-in's closing 0x004A is 0x009F [20, the player's own agent, 7]
    -- OBSERVED on 22 of 22 hand-ins in the live corpus (2026-09-29). Ours sent
    nothing there until S8; --no-quest-complete-visual is that, kept as the
    KNOWN-BAD arm. The predicate spells 0x009F, 20 and 7 as the tape's own
    numbers, not as our constants, so a wrong constant reddens it too.
      §3 (bare): turn_in_quest ends 0x004A, 0x009F [20, PLAYER_AGENT_ID, 7]
         under both --no-reward-in-frame arms; the flag off sends no such line
         and fails the predicate; the predicate refuses the near misses; the
         flag parses and main() flips it.
      §4 (vault-gated on 20260929T150923): its 9 hand-ins, pinned by qid,
         satisfy the predicate with own = the batch's 0x009C agent; no [20,
         own, 7] reaches the own agent outside a hand-in; OURS vs TAPE for
         :55934 q86's tail; sabotaged tapes (the line dropped, or moved ahead
         of the 0x004A) are red.
      §5 (vault-gated, the live corpus): at least 22 hand-ins and 20 with a
         0x009C, the predicate on every one; every connection not declared
         gapped decodes, and the set-aside is capgaps.KNOWN_GAPPED.

Nothing binds a port, launches a client, or touches vault/state.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks       # noqa: E402
import authsrv      # noqa: E402
import serverargs   # noqa: E402
import vaultpath    # noqa: E402

# Floor 15 from the bare-machine green run (RURIK_VAULT at an empty dir): §1's
# nine checks and §3's six. §2 adds 15 with the four captures present, §4 7 and
# §5 3 (40 in all), each declaring a LEDGER.skip for what is absent. Set from
# the run, never above it.
led = checks.Ledger("quest accept and hand-in shapes (QUESTFLOW)", floor=15)

REMOVE = authsrv.GAME_SMSG_QUEST_REMOVE                # 0x0052
UNLIST = authsrv.GAME_SMSG_QUEST_REMOVE_AND_UNLIST     # 0x004A
XP = authsrv.GAME_SMSG_AGENT_KILL_REWARD               # 0x00EE
GOLD = authsrv.merchant.GAME_SMSG_GOLD_CREDIT          # 0x0140
SKC = authsrv.GAME_SMSG_SKILL_SET_COPIES               # 0x00DC
SKB = authsrv.GAME_SMSG_SKILLBAR_UPDATE_SKILL          # 0x00D9
SKU = authsrv.GAME_SMSG_SKILL_UNLOCKED                 # 0x001C
SK_KINDS = ("SKC", "SKB", "SKU")

# The four skill-granting hand-ins (capture, client port, batch t, qid, the
# reduced batch). OBSERVED, decoded with livewire.decode_conn: each is the s2c
# batch sharing the timestamp of the first 0x0052 [qid] after a c2s 0x003B.
WITNESSES = [
    ("20260929T150923", "55934", 293.8090, 86,
     ["RM", "EE0", "GOLD", "SKC:394", "SKB:0:394", "SKC:446", "SKB:1:446",
      "RM", "UNL"]),
    ("20260807T143055", "62994", 92.7916, 82,
     ["RM", "EE0", "GOLD", "SKC:153", "SKB:0:153", "SKC:105", "SKB:1:105",
      "RM", "UNL"]),
    ("20260810T235916", "61624", 126.9171, 86,
     ["RM", "EE0", "GOLD", "SKC:394", "SKB:0:394", "SKC:446", "SKB:1:446",
      "RM", "UNL"]),
    ("20260913T210901", "60877", 736.1848, 347,
     ["RM", "EE0", "SKC:2", "SKB:2:2", "RM", "UNL"]),
]


def reduce_batch(seq):
    """A batch reduced to the kinds the order claim is about, in sequence.
    `seq` is [(op, values)] with values either the sent list or the decoded
    tape list (a header field in front) -- every field is read from the END,
    so both fit: 0x00EE [.., 0, xp] is EE0 (the other 0x00EE attrs -- morale
    10, the level-up 14/13/9 -- are not this claim's), 0x00DC [.., skill, 1],
    0x00D9 [.., agent, slot, skill, 0]."""
    out = []
    for op, v in seq:
        if op == REMOVE:
            out.append("RM")
        elif op == UNLIST:
            out.append("UNL")
        elif op == XP and len(v) >= 2 and v[-2] == 0 and v[-1] > 0:
            out.append("EE0")
        elif op == GOLD:
            out.append("GOLD")
        elif op == SKC:
            out.append(f"SKC:{v[-2]}")
        elif op == SKB:
            out.append(f"SKB:{v[-3]}:{v[-2]}")
        elif op == SKU:
            out.append(f"SKU:{v[-2]}")
    return out


def skills_after_reward(red):
    """The tape's rule, 4 of 4: at least one skill line; the xp or the gold
    present; every skill line after the LAST xp and the LAST gold; and every
    skill line before the closing 0x004A when the batch carries one."""
    kinds = [r.split(":")[0] for r in red]
    sk = [i for i, k in enumerate(kinds) if k in SK_KINDS]
    paid = [i for i, k in enumerate(kinds) if k in ("EE0", "GOLD")]
    if not sk or not paid:
        return False
    if min(sk) < max(paid):
        return False
    unl = [i for i, k in enumerate(kinds) if k == "UNL"]
    return not unl or max(sk) < unl[-1]


def collapse_remove(red):
    """The tape's doubled 0x0052 collapses to one: ours sends ONE on purpose
    (turn_in_quest's party-broadcast experiment), the recorded difference."""
    out = []
    for r in red:
        if not (r == "RM" and "RM" in out):
            out.append(r)
    return out


def collect():
    sent = []
    return sent, (lambda op, values, label="", **kw: sent.append((op, list(values))))


def fresh_state(**kw):
    st = {"quests": set(), "objectives_done": set(), "quests_completed": set(),
          "agents": {}, "char_uuid": "u1"}
    st.update(kw)
    return st


def ours(row, after_gold=True, turn_in=False, known=()):
    """OUR batch for `row` on an empty bar, reduced; flags restored."""
    saved = (authsrv.QUEST_SKILLS_AFTER_GOLD, authsrv.REWARD_IN_FRAME,
             list(authsrv.SKILLBAR))
    authsrv.QUEST_SKILLS_AFTER_GOLD = after_gold
    authsrv.REWARD_IN_FRAME = True
    authsrv.SKILLBAR[:] = [0] * authsrv.SKILLBAR_SLOTS
    sent, send = collect()
    st = fresh_state(quests={1463}, skills_known=set(known))
    try:
        if turn_in:
            authsrv.turn_in_quest(send, st, 1463, row, 0)
            paid = None
        else:
            paid = authsrv.grant_quest_reward(send, st, 1463, row, 0)
    finally:
        (authsrv.QUEST_SKILLS_AFTER_GOLD, authsrv.REWARD_IN_FRAME) = saved[:2]
        authsrv.SKILLBAR[:] = saved[2]
    return reduce_batch(sent), paid


def section_1():
    print("\n1. RANGERPRE-S5 (QUESTFLOW-H1): OURS -- the reward skills after "
          "the xp and the gold")
    row = {"reward_experience": 250, "reward_gold": 25, "reward_skills": [394]}
    red, paid = ours(row)
    led.ok(red == ["EE0", "GOLD", "SKC:394", "SKB:0:394", "SKU:394"]
           and paid == 250,
           "grant_quest_reward: 0x00EE [0, 250], 0x0140, THEN 0x00DC / 0x00D9 "
           "/ 0x001C for 394 -- the tape's order (a skill new to the account "
           "carries its 0x001C)", f"{red} paid={paid}")
    led.ok(skills_after_reward(red),
           "and the predicate holds on it", f"{red}")
    red_tin, _ = ours(row, turn_in=True)
    led.ok(red_tin == ["RM", "EE0", "GOLD", "SKC:394", "SKB:0:394", "SKU:394",
                       "UNL"] and skills_after_reward(red_tin),
           "turn_in_quest: 0x0052, xp, gold, skills, 0x004A -- the skills "
           "inside the frame, before the closing 0x004A", f"{red_tin}")
    red_xp, _ = ours({"reward_experience": 2000, "reward_skills": [2]},
                     known=(2,))
    led.ok(red_xp == ["EE0", "SKC:2", "SKB:0:2"] and skills_after_reward(red_xp),
           "no gold: the skills follow the xp (MANTID q347's shape), and a "
           "skill the account knows sends no 0x001C", f"{red_xp}")
    red_only, paid_only = ours({"reward_skills": [394]})
    led.ok(red_only == ["SKC:394", "SKB:0:394", "SKU:394"] and paid_only == 0,
           "a skills-only row still grants them -- the early return (no xp, "
           "no gold) comes AFTER the skills", f"{red_only} paid={paid_only}")
    # KNOWN-BAD: the pre-S5 order.
    red_bad, _ = ours(row, after_gold=False)
    led.ok(red_bad == ["SKC:394", "SKB:0:394", "SKU:394", "EE0", "GOLD"],
           "KNOWN-BAD arm (--quest-skills-first): the skills go FIRST, as "
           "every run before S5", f"{red_bad}")
    led.ok(not skills_after_reward(red_bad),
           "and the predicate goes RED on it -- it can fail", f"{red_bad}")
    # VACUITY: a batch with no skill line is not "skills after the reward".
    led.ok(not skills_after_reward(["RM", "EE0", "GOLD", "UNL"])
           and not skills_after_reward(["SKC:1", "SKB:0:1"]),
           "VACUITY: no skill line, or no xp and no gold, fails the predicate")
    # The revert arm is reachable: the flag parses, and main() flips it.
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.quest_skills_first:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--quest-skills-first"]).quest_skills_first
           and not ap.parse_args([]).quest_skills_first
           and authsrv.QUEST_SKILLS_AFTER_GOLD is True
           and "global QUEST_SKILLS_AFTER_GOLD\n" in window
           and "QUEST_SKILLS_AFTER_GOLD = False\n" in window,
           "--quest-skills-first parses, the default is after-the-gold, and "
           "main() sets QUEST_SKILLS_AFTER_GOLD = False under it",
           f"window found={at >= 0}")


def section_2():
    print("\n2. RANGERPRE-S5 (QUESTFLOW-H1): the TAPE -- the four skill-granting "
          "hand-ins")
    import livewire
    for cap, port, t_batch, qid, want in WITNESSES:
        capdir = vaultpath.vault_path("captures", "live", cap)
        if not os.path.isdir(capdir):
            led.skip(f"the tape {cap} :{port}", f"no {capdir} (bare machine)")
            continue
        files = [g for g in livewire.connections(capdir)
                 if f"_{port}-to-" in g]
        led.ok(len(files) == 1, f"TAPE {cap}: one game connection on :{port}",
               f"{files}")
        if len(files) != 1:
            continue
        _conn, merged, ok = livewire.decode_conn(capdir, files[0])
        batch_t = next((t for t, d, op, v in merged
                        if d == "s2c" and op == REMOVE and v[-1] == qid
                        and abs(t - t_batch) < 0.001), None)
        batch = [(op, v) for t, d, op, v in merged
                 if d == "s2c" and batch_t is not None and t == batch_t]
        red = reduce_batch(batch)
        led.ok(ok and red == want,
               f"TAPE {cap} :{port} {t_batch:.4f} q{qid}: the batch reduces to "
               f"{' '.join(want)} (decoded to the last byte)",
               f"ok={ok} {red}")
        led.ok(skills_after_reward(red),
               f"TAPE {cap} :{port}: the skills come after the xp"
               + (" and the gold" if "GOLD" in want else " (no gold)")
               + ", before the closing 0x004A", f"{red}")
        if port != "55934":
            continue
        # OURS for that batch's own row, the account already holding both
        # skills (the tape carries no 0x001C).
        row = {"reward_experience": 500, "reward_gold": 25,
               "reward_skills": [394, 446]}
        red_ours, _ = ours(row, turn_in=True, known=(394, 446))
        led.ok(red_ours == collapse_remove(red),
               "OURS vs TAPE :55934: turn_in_quest for {500 xp, 25 gold, "
               "skills 394, 446} equals the retail batch on every reduced kind, "
               "skill id and bar slot (the tape's doubled 0x0052 collapsed)",
               f"ours {red_ours} tape {red}")
        red_bad, _ = ours(row, after_gold=False, turn_in=True,
                          known=(394, 446))
        led.ok(red_bad != collapse_remove(red),
               "KNOWN-BAD: --quest-skills-first does NOT equal the tape",
               f"{red_bad}")
        # SABOTAGE: the tape with its first skill line moved ahead of the xp.
        sab = list(batch)
        si = next(k for k, (op, _v) in enumerate(sab) if op == SKC)
        xi = next(k for k, (op, v) in enumerate(sab)
                  if op == XP and v[-2] == 0 and v[-1] > 0)
        sab.insert(xi, sab.pop(si))
        led.ok(not skills_after_reward(reduce_batch(sab)),
               "KNOWN-BAD: a sabotaged tape (a 0x00DC ahead of the xp) FAILS "
               "the predicate", f"{reduce_batch(sab)}")


VIS = authsrv.GAME_SMSG_AGENT_GENERIC_VALUE             # 0x009F
# The hand-ins of 20260929T150923 (client port, batch t, qid), OBSERVED with
# livewire.decode_conn: every s2c batch holding both a 0x0052 and a 0x004A.
TAPE_S8 = "20260929T150923"
HANDINS_S8 = {("53756", 1190.2370, 75), ("53880", 727.4875, 62),
              ("55934", 231.0014, 222), ("55934", 293.8090, 86),
              ("55934", 627.3734, 54), ("59427", 1244.1502, 79),
              ("59427", 1250.0757, 89), ("59427", 1279.4083, 1462),
              ("59969", 207.6762, 80)}


def visual_after_unlist(seq, own):
    """The tape's rule, 22 of 22: the message right after the LAST 0x004A is
    0x009F [20, own, 7]. `seq` is [(op, values)], the values read from the END
    (the tape's carry a header field in front). The numbers are the tape's --
    0x009F, 20, 7 -- never our constants, so this can refute them."""
    ops = [op for op, _v in seq]
    if UNLIST not in ops:
        return False
    k = max(i for i, op in enumerate(ops) if op == UNLIST)
    if k + 1 >= len(seq):
        return False
    op, v = seq[k + 1]
    return op == 0x009F and len(v) >= 3 and list(v[-3:]) == [20, own, 7]


def is_v7(op, v):
    return op == 0x009F and len(v) >= 3 and v[-3] == 20 and v[-1] == 7


def ours_seq(row, visual=True, frame=True):
    """OUR raw turn_in_quest batch [(op, values)]; flags restored."""
    saved = (authsrv.QUEST_COMPLETE_VISUAL, authsrv.REWARD_IN_FRAME,
             list(authsrv.SKILLBAR))
    authsrv.QUEST_COMPLETE_VISUAL = visual
    authsrv.REWARD_IN_FRAME = frame
    authsrv.SKILLBAR[:] = [0] * authsrv.SKILLBAR_SLOTS
    sent, send = collect()
    try:
        authsrv.turn_in_quest(send, fresh_state(quests={1463}), 1463, row, 0)
    finally:
        (authsrv.QUEST_COMPLETE_VISUAL, authsrv.REWARD_IN_FRAME) = saved[:2]
        authsrv.SKILLBAR[:] = saved[2]
    return sent


def handins(merged):
    """[(t, qid, own, batch)] -- each s2c batch holding a 0x0052 and a 0x004A,
    batch = [(op, values)] in wire order, own = its 0x009C agent (the 75-XP
    tick names the player) or None."""
    by_t = {}
    for t, d, op, v in merged:
        if d == "s2c":
            by_t.setdefault(t, []).append((op, v))
    out = []
    for t, batch in sorted(by_t.items()):
        ops = [op for op, _v in batch]
        if REMOVE in ops and UNLIST in ops:
            own = next((v[-2] for op, v in batch if op == 0x009C), None)
            qid = [v for op, v in batch if op == UNLIST][-1][-1]
            out.append((t, qid, own, batch))
    return out


def section_3():
    print("\n3. RANGERPRE-S8 (QUESTFLOW-H3): OURS -- 0x009F [20, own, 7] right "
          "after the 0x004A")
    row = {"reward_experience": 250, "reward_gold": 25}
    own = authsrv.PLAYER_AGENT_ID
    seq = ours_seq(row)
    led.ok(seq[-2:] == [(UNLIST, [1463]), (0x009F, [20, own, 7])]
           and sum(is_v7(op, v) for op, v in seq) == 1,
           "turn_in_quest ends 0x004A [1463], 0x009F [20, PLAYER_AGENT_ID, 7] "
           "-- one visual line, the batch's last", f"{seq}")
    led.ok(visual_after_unlist(seq, own),
           "and the predicate holds on it", f"{seq[-2:]}")
    seq_p1 = ours_seq(row, frame=False)
    kinds_p1 = [op for op, _v in seq_p1]
    led.ok(visual_after_unlist(seq_p1, own)
           and kinds_p1.index(UNLIST) < kinds_p1.index(XP),
           "--no-reward-in-frame (the reward after the 0x004A) keeps the "
           "visual IMMEDIATELY after the 0x004A, ahead of the reward",
           f"{[hex(o) for o in kinds_p1]}")
    # KNOWN-BAD: the pre-S8 batch.
    bad = ours_seq(row, visual=False)
    led.ok(not any(is_v7(op, v) for op, v in bad) and bad[-1][0] == UNLIST
           and not visual_after_unlist(bad, own),
           "KNOWN-BAD arm (--no-quest-complete-visual): no [20, x, 7] at all, "
           "the batch ends on the 0x004A as before S8, and the predicate goes "
           "RED", f"{[hex(o) for o, _v in bad]}")
    # VACUITY: the predicate refuses each near miss.
    tail = [(REMOVE, [1]), (UNLIST, [1])]
    misses = {
        "no 0x004A": [(REMOVE, [1]), (0x009F, [20, own, 7])],
        "nothing after it": tail,
        "another agent": tail + [(0x009F, [20, own + 1, 7])],
        "another visual": tail + [(0x009F, [20, own, 6])],
        "another value id": tail + [(0x009F, [21, own, 7])],
        "the 0x00A0 op": tail + [(0x00A0, [20, own, 7])],
        "ahead of the 0x004A": [(REMOVE, [1]), (0x009F, [20, own, 7]),
                                (UNLIST, [1])],
    }
    red = {k: visual_after_unlist(s, own) for k, s in misses.items()}
    led.ok(not any(red.values())
           and visual_after_unlist(tail + [(0x009F, [20, own, 7])], own),
           "VACUITY: the predicate refuses every near miss (no 0x004A, nothing "
           "after it, another agent / visual / value id / op, the line ahead "
           "of the 0x004A) and accepts the exact shape", f"{red}")
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.no_quest_complete_visual:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--no-quest-complete-visual"]).no_quest_complete_visual
           and not ap.parse_args([]).no_quest_complete_visual
           and authsrv.QUEST_COMPLETE_VISUAL is True
           and "global QUEST_COMPLETE_VISUAL\n" in window
           and "QUEST_COMPLETE_VISUAL = False\n" in window,
           "--no-quest-complete-visual parses, the default sends the visual, "
           "and main() sets QUEST_COMPLETE_VISUAL = False under it",
           f"window found={at >= 0}")


def section_4():
    print(f"\n4. RANGERPRE-S8 (QUESTFLOW-H3): the TAPE {TAPE_S8} -- its nine "
          "hand-ins")
    import livewire
    capdir = vaultpath.vault_path("captures", "live", TAPE_S8)
    if not os.path.isdir(capdir):
        led.skip(f"the tape {TAPE_S8}", f"no {capdir} (bare machine)")
        return
    files = livewire.connections(capdir)
    found, v7, all_ok = [], [], True
    for gf in files:
        port = gf.split("_")[1].split("-")[0]
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        all_ok = all_ok and ok
        for t, qid, own, batch in handins(merged):
            found.append((port, round(t, 4), qid, own, batch))
        v7 += [(port, round(t, 4), v[-2]) for t, d, op, v in merged
               if d == "s2c" and is_v7(op, v)]
    led.ok(all_ok and len(files) == 11,
           f"TAPE {TAPE_S8}: all 11 game connections decode to the last byte",
           f"{len(files)} files, ok={all_ok}")
    got = {(p, t, q) for p, t, q, _o, _b in found}
    led.ok(got == HANDINS_S8 and len(found) == 9,
           "TAPE: exactly the nine hand-ins, pinned by port, batch t and qid "
           "(q80 222 86 54 62 75 79 89 1462)", f"{sorted(got ^ HANDINS_S8)}")
    good = [(p, t, q) for p, t, q, own, b in found
            if own is not None and visual_after_unlist(b, own)]
    led.ok(len(good) == 9,
           "TAPE: 9 of 9 -- the message right after the last 0x004A is 0x009F "
           "[20, own, 7], own being the batch's own 0x009C agent",
           f"{len(good)} of {len(found)}: "
           f"{[(p, t, q, o) for p, t, q, o, _b in found if (p, t, q) not in good]}")
    own_of = {(p, t): o for p, t, _q, o, _b in found}
    on_own = {(p, t) for p, t, a in v7 if own_of.get((p, t)) == a}
    strangers = sorted((p, t, a) for p, t, a in v7 if (p, t) not in on_own)
    led.ok(len(v7) == 11 and on_own == set(own_of)
           and strangers == [("59427", 1251.088, 265), ("59427", 1278.0374, 285)],
           "TAPE: 11 [20, x, 7] in all -- the 9 hand-ins' own lines and 2 on "
           "OTHER players' agents (:59427 265, 285); none reaches the own agent "
           "outside a hand-in", f"{v7}")
    # OURS vs TAPE: :55934 q86, the tail from the closing 0x004A (the agent is
    # each side's own, so it is compared as "own", not as a number).
    tape_own, tape_b = next(((o, b) for p, t, q, o, b in found
                             if (p, q) == ("55934", 86)), (None, None))
    if tape_b is None:
        led.ok(False, "TAPE: :55934 q86's hand-in batch is on the tape",
               f"{sorted(got)}")
        return

    def tail(seq, own):
        ops = [op for op, _v in seq]
        k = max(i for i, op in enumerate(ops) if op == UNLIST)
        return [(op, ["own" if x == own else x for x in v[-3:]])
                for op, v in seq[k:k + 2]]
    row = {"reward_experience": 500, "reward_gold": 25,
           "reward_skills": [394, 446]}
    t_tape = tail(tape_b, tape_own)
    t_ours = tail(ours_seq(row), authsrv.PLAYER_AGENT_ID)
    t_bad = tail(ours_seq(row, visual=False), authsrv.PLAYER_AGENT_ID)
    led.ok([(op, v[-1:]) for op, v in t_tape[:1]] == [(UNLIST, [86])]
           and t_ours[1:] == t_tape[1:] == [(0x009F, [20, "own", 7])],
           "OURS vs TAPE :55934 293.809 q86: after the 0x004A both send 0x009F "
           "[20, own, 7]", f"ours {t_ours} tape {t_tape}")
    led.ok(t_bad[1:] != t_tape[1:],
           "KNOWN-BAD: --no-quest-complete-visual does NOT equal the tape",
           f"{t_bad}")
    # SABOTAGE: the line dropped, and the line moved ahead of the 0x004A.
    vi = next(i for i, (op, v) in enumerate(tape_b) if is_v7(op, v))
    ui = max(i for i, (op, _v) in enumerate(tape_b) if op == UNLIST)
    dropped = tape_b[:vi] + tape_b[vi + 1:]
    moved = list(tape_b)
    moved.insert(ui, moved.pop(vi))
    led.ok(not visual_after_unlist(dropped, tape_own)
           and not visual_after_unlist(moved, tape_own),
           "KNOWN-BAD: a sabotaged tape -- the line dropped, or moved ahead of "
           "the 0x004A -- FAILS the predicate")


def section_5():
    print("\n5. RANGERPRE-S8 (QUESTFLOW-H3): the live CORPUS -- every hand-in")
    import livewire
    import capgaps
    root = vaultpath.vault_path("captures", "live")
    aside = []
    conns = (list(livewire.live_connections(set_aside=aside))
             if os.path.isdir(root) else [])
    if not conns:
        led.skip("section 5, the live corpus", f"no live captures under {root}")
        return
    decoded, n, n_own, bad = 0, 0, 0, []
    for capdir, gf in conns:
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        decoded += 1 if ok else 0
        for t, qid, own, batch in handins(merged):
            n += 1
            ops = [op for op, _v in batch]
            k = max(i for i, op in enumerate(ops) if op == UNLIST)
            nxt = batch[k + 1] if k + 1 < len(batch) else None
            if own is not None:
                n_own += 1
                fine = visual_after_unlist(batch, own)
            else:       # no 0x009C to name own: the shape, whoever it lands on
                fine = nxt is not None and is_v7(*nxt)
            if not fine:
                bad.append((os.path.basename(capdir), gf, round(t, 4), qid,
                            own, nxt))
    led.ok(decoded == len(conns),
           f"every live connection its manifest does not declare gapped decoded "
           f"({decoded} of {len(conns)}, {len(aside)} set aside)")
    gap_ok, gap_detail = capgaps.audit(
        aside, [d for d, _w in livewire.live_captures()], livewire.refuses)
    led.ok(gap_ok, "and the connections set aside are EXACTLY the known "
           "declared gaps, each still refused", gap_detail)
    led.ok(n >= 22 and n_own >= 20 and not bad,
           f"CORPUS: 0x009F [20, x, 7] right after the last 0x004A on {n - len(bad)} "
           f"of {n} hand-ins (floor 22), x = the batch's 0x009C agent on "
           f"{n_own} (floor 20)", f"{bad}")


def main():
    section_1()
    section_2()
    section_3()
    section_4()
    section_5()
    return led.verdict()


if __name__ == "__main__":
    sys.exit(main())
