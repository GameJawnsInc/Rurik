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
  * RANGERPRE-S18 (QUESTFLOW-A1), THE QUEST-LOG WORDS. 0x0049's flags are a
    per-quest constant, 0 or 32 (0 on 5 of 20260929T150923's 12 accepts),
    and its home is the accepting map; every 0x0050 replay repeats both, the
    home included when the load is on another map (27 of that tape's 37
    replays). Ours sent 32 always and replayed the LOADED map until S18;
    --no-retail-quest-log is that, kept as the KNOWN-BAD arm. The rule
    (log_words_hold) reads the tape's positions, never our constants.
      §6 (bare): accept_quest / _replay_quests for the shipped errand and a
         flags-0 copy, the missing-home fallback, the known-bad arm, the
         rule's near misses, questdefs.log_flags' refusals and load's, the
         flag and main()'s flip.
      §7 (vault-gated on 20260929T150923): the 12 accepts pinned with their
         flags, home = the connection's map 12 of 12, the 37 replays (36
         exact, q79's 34 the one with bit 1), the rule on all 8 replayed
         quests; OURS vs TAPE 12 of 12 accepts and 36 of 37 replays, the
         known-bad arm 7 and 3.
      §8 (vault-gated, the live corpus): at least 30 accepts, flags only 0 /
         32, one value per quest, home = the accepting map on every accept,
         and every replay of an accepted quest carrying its flags and home.
  * RANGERPRE-S18 (QUESTFLOW-A3), THE ACCEPT-TIME GRANTS. A quest may hand
    over items and skills when it is accepted, and retail sends them BEFORE
    the 0x0049 (2 of 2 grant-carrying accepts in the live corpus; q75's
    sword and three skills on 20260929T150923 :56064 921.1613). Ours granted
    nothing at an accept until S18; --no-accept-rewards is that, kept as the
    KNOWN-BAD arm. The rule (grants_before_add) is the tape's order.
      §9 (bare): accept_quest with accept_items / accept_skills reduces to
         the tape's order; grant_item's id, cell and registration; a full
         backpack; a known skill's missing 0x001C; the known-bad arm; the
         rule's near misses; questdefs' refusals; a granted item's cell never
         persisted by _item_moves_commit; the flag and main()'s flip.
      §10 (vault-gated): q75's batch reduced exactly, the item declared then
         placed, OURS vs TAPE equal on every kind, skill id and bar slot,
         the known-bad arm and a sabotaged tape red; the corpus's every
         grant-carrying accept granting first.
  * RANGERPRE-S18 (QUESTFLOW-A2), THE ACCEPT MARKER. Retail's 0x0049 marks
    the OBJECTIVE -- an NPC's exact create spot and plane (5 of
    20260929T150923's 12), or the exit toward the objective's map labelled
    with that map (5 of 12) -- never the player. Ours marked the player's
    own position until S18; --quest-marker-at-player is that, kept as the
    KNOWN-BAD arm. The rule (marker_placed) is the tape's.
      §11 (bare): the errand marks the scout, the bandits the corridor exit
         labelled 168; the live body's plane; portal_route's first hop and
         final label; the placeholder's three causes; the probe binding and
         the giver fallback; the known-bad arm; the rule's near misses; the
         flag and main()'s flip.
      §12 (vault-gated on 20260929T150923): the 12 markers' three kinds, the
         rule on the five create-spot markers (plane 26 included), the
         cross-map markers within 387 u of the player's last position before
         the transfer to that map, and :53880's one exit for three labels.

  * RANGERPRE-S20 (QUESTFLOW-H4), THE HAND-IN'S ITEMS. A hand-in takes its
    quest item back (0x014D) and grants its reward item (0x0161 then
    0x013E) into the cell the quest item vacated, all BEFORE the first
    0x0052 -- retail's q62 (20260929T150923 :53880 727.4875), the corpus's
    only hand-in with a 0x014D, and q440 (20260819T132414 :52606, a reward
    item with no quest item). The screens draw a shield's line after the
    reward, byte-identical to q62's. Ours sent none of it until S20;
    --no-quest-items is that, kept as the KNOWN-BAD arm. The rules
    (items_before_remove, vacated_refilled) are the tape's.
      §13 (bare): turn_in_quest for a quest item back and a shield out, the
         bytes and the cell (the vacated one, not the lowest); the item not
         held; a dressed item with the same key never taken; grant_item's
         named-cell fallback; the known-bad arm; the rules' near misses;
         _quest_prose's shield line and its refused weapon line;
         reward_item_run's and questdefs' refusals; the flag and main().
      §14 (vault-gated): q62's batch reduced exactly, 3359's cell refilled
         by 1607; our reward_item_run fed 1607's own name and 572 argument
         EQUAL to the screen's and the 0x004C's tail (armour + 1 unequal);
         OURS vs TAPE; sabotaged tapes red; q440; the corpus's every
         item-bearing hand-in.

  * RANGERLOOP-F6, THE ACCOUNT'S UNLOCK GATE. A granted skill's 0x001C rides
    its 0x00DC only when the skill is outside the ACCOUNT's library -- the
    load's 0x001D, plus every 0x001C since. OBSERVED on 19 of 19 retail
    grants (7 captures). Ours tested the per-connection skills_known, empty
    at every connect, so every first grant toasted, a held skill included;
    --no-account-unlock-gate is that, kept as the KNOWN-BAD arm. Every
    fixture here that grants a skill now names the account it models
    (`held`, laid into authsrv.UNLOCKED -- the --unlocks bitmap, every
    skill by default), and the fakes of skills_known are gone.
      §15 (bare): 0x001C iff outside the bitmap, both arms exercised;
         skills_known joins it; a stored list wins over the flag and an
         absent one falls back to it; the served table bounds it; the
         known-bad arm sends the old toast and the rule goes red; the flag
         and main()'s flip.
      §16 (vault-gated, the live corpus): every retail 0x00DC joined to the
         library in force on its capture's clock -- 19 of 19 agree (floor
         19), 7 outside, 12 inside, one of them (384 at :53756 1191.028)
         by :56064's 0x001C at 921.161; the 0x001D only grows and holds
         every skill a 0x001C unlocked before it; the known-bad rule
         disagrees on 12 and a sabotaged tape is red. §10 now runs q75 on
         the tape's own 38-skill library.
  * RANGERLOOP-F5, THE LOG HEADING'S REGION. 0x0049 / 0x0050's FIRST
    string slot is the heading's argument (static: 0x0091DB70 -> 0x0080F0A0
    -> record+8 -> 0x0080DB40 -> arm 3 at 0x0057DD77, string 1125), and
    retail's is ONE region unit on 137 of 137 log rows, never equal to the
    second, a function of the home map. Ours sent the name in all three;
    --no-quest-region is that, kept as the KNOWN-BAD arm.
      §17 (bare): log_strings and both send sites (accept_quest,
         _replay_quests) put the row's enc_region in s1 and the name in s2
         and s3; the rule (region_first) holds on ours and goes red on the
         known-bad arm and on a row with no enc_region; region_units'
         refusals and load's; the shipped rows; the flag and main()'s flip.
      §18 (vault-gated): the corpus census (floor 137), the shipped rows'
         word equal to the corpus's for their home (148), the loader's rule
         accepting every retail s1 and refusing every retail s2; the static
         read's bytes on the pinned 38797 client, and a swapped-arm control.

§5, §8, §10, §14, §16 and §18 share ONE decode of the corpus (corpus()); §7
and on share one of 20260929T150923 (tape_s18()). Nothing binds a port,
launches a client, or touches vault/state.
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

# Floor 77 from the bare-machine green run (RURIK_VAULT at an empty dir,
# 2026-10-07): §1's nine checks, §3's six, §6's eleven, §9's twelve, §11's
# ten, §13's thirteen, §15's seven and §17's nine. §2 adds 15 with the four
# captures present, §4 7, §5 3, §7 7, §8 3, §10 9, §12 4, §14 8, §16 4 and
# §18 6 (143 in all), each declaring a LEDGER.skip for what is absent. Set
# from the run, never above it. (61 and 115 until RANGERLOOP-F5 / F6.)
led = checks.Ledger("quest accept and hand-in shapes (QUESTFLOW)", floor=77)

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


def account_words(held):
    """The --unlocks bitmap for an account holding exactly `held` -- what a
    fixture lays into authsrv.UNLOCKED, whose default (every skill) would
    make every grant a held one once RANGERLOOP-F6 gates the 0x001C on it."""
    return authsrv.skillunlock.words_from_ids(sorted(int(s) for s in held),
                                              "test_questflow account")


def ours(row, after_gold=True, turn_in=False, known=(), held=()):
    """OUR batch for `row` on an empty bar, reduced; flags restored. `held`
    is the ACCOUNT's library (authsrv.UNLOCKED; empty unless named), `known`
    this connection's skills_known."""
    saved = (authsrv.QUEST_SKILLS_AFTER_GOLD, authsrv.REWARD_IN_FRAME,
             list(authsrv.SKILLBAR), authsrv.UNLOCKED)
    authsrv.QUEST_SKILLS_AFTER_GOLD = after_gold
    authsrv.REWARD_IN_FRAME = True
    authsrv.SKILLBAR[:] = [0] * authsrv.SKILLBAR_SLOTS
    authsrv.UNLOCKED = account_words(held)
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
        authsrv.UNLOCKED = saved[3]
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
    # RE-AIMED for RANGERLOOP-F6: "the account knows" is the account's
    # library (held), not a faked skills_known -- the gate reads the former.
    red_xp, _ = ours({"reward_experience": 2000, "reward_skills": [2]},
                     held=(2,))
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
        # skills (the tape carries no 0x001C). RE-AIMED for RANGERLOOP-F6:
        # held, the account's library -- the tape's own 0x001D (:59969
        # 157.127) holds both, §16 -- not a faked skills_known.
        row = {"reward_experience": 500, "reward_gold": 25,
               "reward_skills": [394, 446]}
        red_ours, _ = ours(row, turn_in=True, held=(394, 446))
        led.ok(red_ours == collapse_remove(red),
               "OURS vs TAPE :55934: turn_in_quest for {500 xp, 25 gold, "
               "skills 394, 446} equals the retail batch on every reduced kind, "
               "skill id and bar slot (the tape's doubled 0x0052 collapsed)",
               f"ours {red_ours} tape {red}")
        red_bad, _ = ours(row, after_gold=False, turn_in=True,
                          held=(394, 446))
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


ACCEPT = authsrv.GAME_SMSG_QUEST_ADD                   # 0x0049
REPLAY = authsrv.GAME_SMSG_QUEST_ADD_NO_MARKER         # 0x0050
_CORPUS = None


def corpus():
    """ONE walk of the live corpus for every corpus section (§5 and on), or
    None when the vault holds no live captures. Each connection is decoded
    once; what the sections read is kept, the decoded streams are not:
    'handins' [(capture, file, t, qid, own, batch)], 'accepts' [(capture,
    port, t, values, conn map, batch)] and 'replays' [(capture, port, t,
    values, conn map)] -- values as decoded, header field in front; the conn
    map is read only on a connection holding an accept (None elsewhere).
    RANGERLOOP-F6's join adds 'libs' [(capture, port, t, ids)] -- every
    0x001D, the account library -- 'learns' [(capture, port, t, skill)] --
    every 0x00DC -- and 'unlocks' [(capture, port, t, skill)] -- every
    0x001C; t is the capture's own clock (wire.jsonl), shared by its
    connections."""
    global _CORPUS
    if _CORPUS is not None:
        return _CORPUS or None
    import livewire
    import tape
    root = vaultpath.vault_path("captures", "live")
    aside = []
    conns = (list(livewire.live_connections(set_aside=aside))
             if os.path.isdir(root) else [])
    if not conns:
        _CORPUS = {}
        return None
    out = {"root": root, "conns": conns, "aside": aside, "decoded": 0,
           "handins": [], "accepts": [], "replays": [],
           "libs": [], "learns": [], "unlocks": []}
    for capdir, gf in conns:
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        out["decoded"] += 1 if ok else 0
        cap = os.path.basename(capdir)
        port = gf.split("_")[1].split("-")[0]
        cmap = None
        # The connection's map, read only where an accept needs it (the read
        # walks wire.jsonl; 127 of them cost half a minute). None fails §8's
        # home checks by name, never silently.
        if any(d == "s2c" and op == ACCEPT for _t, d, op, _v in merged):
            try:
                cmap = tape.client_version(capdir, conn)["map_id"]
            except tape.TapeError:
                cmap = None
        for t, qid, own, batch in handins(merged):
            out["handins"].append((cap, gf, t, qid, own, batch))
        by_t = {}
        for t, d, op, v in merged:
            if d == "s2c":
                by_t.setdefault(t, []).append((op, v))
        for t, d, op, v in merged:
            if d == "s2c" and op == ACCEPT:
                out["accepts"].append((cap, port, round(t, 4), v, cmap,
                                       by_t[t]))
            elif d == "s2c" and op == REPLAY:
                out["replays"].append((cap, port, round(t, 4), v, cmap))
            elif d == "s2c" and op == ACCT_LIB:
                out["libs"].append((cap, port, round(t, 4),
                                    frozenset(lib_ids(v[-1]))))
            elif d == "s2c" and op == SKC:
                out["learns"].append((cap, port, round(t, 4), v[-2]))
            elif d == "s2c" and op == SKU:
                out["unlocks"].append((cap, port, round(t, 4), v[-2]))
    _CORPUS = out
    return out


ACCT_LIB = authsrv.GAME_SMSG_PVP_UPDATE_UNLOCKED_SKILLS  # 0x001D


def lib_ids(words):
    """A decoded 0x001D bitmap (its word list) -> the skill ids it sets."""
    return authsrv.skillunlock.ids_from_words(list(words))


def tape_library(conns, before):
    """(ids, 'port t') of the LAST s2c 0x001D strictly before `before` on
    any of one capture's connections (tape_s18's), on the capture's own
    clock -- the account library the client held then -- or (None, None)."""
    best = None
    for port, _cmap, merged, _ok in conns:
        for t, d, op, v in merged:
            if d == "s2c" and op == ACCT_LIB and t < before \
                    and (best is None or t > best[0]):
                best = (t, port, frozenset(lib_ids(v[-1])))
    if best is None:
        return None, None
    return best[2], f":{best[1]} {best[0]:.3f}"


def section_5():
    print("\n5. RANGERPRE-S8 (QUESTFLOW-H3): the live CORPUS -- every hand-in")
    import livewire
    import capgaps
    c = corpus()
    if c is None:
        led.skip("section 5, the live corpus", "no live captures under "
                 f"{vaultpath.vault_path('captures', 'live')}")
        return
    conns, aside = c["conns"], c["aside"]
    n, n_own, bad = 0, 0, []
    for cap, gf, t, qid, own, batch in c["handins"]:
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
            bad.append((cap, gf, round(t, 4), qid, own, nxt))
    led.ok(c["decoded"] == len(conns),
           f"every live connection its manifest does not declare gapped decoded "
           f"({c['decoded']} of {len(conns)}, {len(aside)} set aside)")
    gap_ok, gap_detail = capgaps.audit(
        aside, [d for d, _w in livewire.live_captures()], livewire.refuses)
    led.ok(gap_ok, "and the connections set aside are EXACTLY the known "
           "declared gaps, each still refused", gap_detail)
    led.ok(n >= 22 and n_own >= 20 and not bad,
           f"CORPUS: 0x009F [20, x, 7] right after the last 0x004A on {n - len(bad)} "
           f"of {n} hand-ins (floor 22), x = the batch's 0x009C agent on "
           f"{n_own} (floor 20)", f"{bad}")


# ---------------------------------------------------------------- S18 / A1
TAPE_S18 = "20260929T150923"
ERRAND, BANDITS = 1463, 1464
# The tape's 12 accepts (client port, batch t, qid, log flags), OBSERVED with
# livewire.decode_conn: every s2c 0x0049 on the 11 game connections.
ACCEPTS_S18 = {("53880", 745.6235, 79, 32), ("53880", 772.5859, 90, 0),
               ("55934", 231.7225, 86, 32), ("55934", 302.7059, 54, 32),
               ("55934", 628.7834, 62, 32), ("55934", 632.0561, 52, 0),
               ("56025", 782.1410, 68, 0), ("56064", 921.1613, 75, 0),
               ("59427", 1244.8489, 89, 32), ("59969", 184.4414, 80, 0),
               ("59969", 186.0757, 1462, 32), ("59969", 208.5508, 222, 32)}
_TAPE18 = None


def tape_s18():
    """[(port, conn map, merged, ok)] for the 11 connections of TAPE_S18,
    decoded once for §7 on; None on a bare machine."""
    global _TAPE18
    if _TAPE18 is not None:
        return _TAPE18 or None
    import livewire
    import tape
    capdir = vaultpath.vault_path("captures", "live", TAPE_S18)
    if not os.path.isdir(capdir):
        _TAPE18 = []
        return None
    out = []
    for gf in livewire.connections(capdir):
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        out.append((gf.split("_")[1].split("-")[0],
                    tape.client_version(capdir, conn)["map_id"], merged, ok))
    _TAPE18 = out
    return out


def log_words_hold(accept, accept_map, replays):
    """The tape's rule for one quest's log words: the accept's home is the
    map it was accepted on, and every replay carries the accept's flags (bit
    1 aside -- the one the quest's 0x004D adds) and the accept's home. Values
    read from the END, so the tape's header field and our bare list both fit:
    0x0049 [.., flags, s1, s2, s3, home], 0x0050 [.., flags, s1, s2, s3,
    home]. Vacuous without a replay: False."""
    flags, home = accept[-5], accept[-1]
    if home != accept_map or not replays:
        return False
    return all((r[-5] & ~2) == flags and r[-1] == home for r in replays)


def rows_with(overrides):
    """The shipped quest rows with {qid: {column: value}} laid over copies."""
    import questdefs
    rows = {q: dict(r) for q, r in questdefs.load().items()}
    for qid, cols in overrides.items():
        base = dict(rows.get(qid) or rows[ERRAND])
        for k in ("giver_spawn", "objective_spawn", "objective_kill",
                  "giver_agent", "objective_agent"):
            if qid not in rows:
                base.pop(k, None)       # a synthetic quest binds no NPC
        base.update(cols, quest_id=qid)
        rows[qid] = base
    return rows


def drive(rows, steps, retail=True, bar=None, held=(), **flags):
    """Run accept_quest / _replay_quests against `rows` (patched in as the
    server's quest table) with QUEST_LOG_RETAIL = `retail`, the skill bar
    `bar` (an empty bar when None), the ACCOUNT's library `held` (laid into
    authsrv.UNLOCKED; empty unless named -- RANGERLOOP-F6) and any other
    authsrv flag in `flags`; restores all of it. `steps` is [(kind, qid or
    held, map_id, state overrides)]; one progress carrier is shared across
    the steps, as bind_progress shares it across connections. Returns
    [[(op, values)] per step]; the last step's state is left in
    drive.state."""
    saved_rows = authsrv._QUEST_ROWS
    saved_flags = {k: getattr(authsrv, k)
                   for k in ["QUEST_LOG_RETAIL", "UNLOCKED"] + list(flags)}
    saved_bar = list(authsrv.SKILLBAR)
    authsrv._QUEST_ROWS = rows
    authsrv.QUEST_LOG_RETAIL = retail
    authsrv.UNLOCKED = account_words(held)
    authsrv.SKILLBAR[:] = list(bar) if bar is not None else [0] * authsrv.SKILLBAR_SLOTS
    for k, v in flags.items():
        setattr(authsrv, k, v)
    carrier = {"quests": set(), "objectives_done": set(),
               "quests_completed": set(), "quest_home": {}}
    out = []
    try:
        for kind, what, map_id, extra in steps:
            sent, send = collect()
            st = dict(carrier, map_id=map_id, pos=(9826.0, 8077.0),
                      interacting=99, agents={}, char_uuid="u1")
            st.update(extra)
            if kind == "accept":
                authsrv.accept_quest(send, st, what, rows[what], 0)
            else:
                st["quests"] = set(what)
                authsrv._replay_quests(send, st)
            for k in carrier:           # the carrier is the character's
                if k in st and k != "quests":
                    carrier[k] = st[k]
            if kind == "accept":
                carrier["quests"] = st["quests"]
            out.append(sent)
            drive.state = st
    finally:
        authsrv._QUEST_ROWS = saved_rows
        for k, v in saved_flags.items():
            setattr(authsrv, k, v)
        authsrv.SKILLBAR[:] = saved_bar
    return out


def first(seq, op):
    return next((v for o, v in seq if o == op), None)


def section_6():
    print("\n6. RANGERPRE-S18 (QUESTFLOW-A1): OURS -- the accept's log flags "
          "and home, and the replay's")
    import questdefs
    rows = questdefs.load()
    nm = questdefs.enc_string(rows[ERRAND]["enc_name"])
    # RE-AIMED for RANGERLOOP-F5: s1 is the row's region now, not the name
    # (§17 holds the slots themselves); this section is about flags and home.
    reg = questdefs.enc_string(rows[ERRAND]["enc_region"])
    acc, = drive(rows, [("accept", ERRAND, 148, {})])
    add = first(acc, ACCEPT)
    led.ok(add is not None and add[4] == 32 and add[8] == 148
           and add[5:8] == [reg, nm, nm],
           "the errand's 0x0049 carries log flags 32 (a row that says nothing: "
           "QUEST_LOG_FLAGS_DEFAULT, what ours always sent) and home 148, the "
           "accepting map", f"{add}")
    rows0 = rows_with({ERRAND: {"quest_log_flags": 0}})
    acc0, rep0 = drive(rows0, [("accept", ERRAND, 148, {}),
                               ("replay", [ERRAND], 168, {})])
    add0, re0 = first(acc0, ACCEPT), first(rep0, REPLAY)
    led.ok(add0 is not None and add0[4] == 0 and add0[8] == 148,
           "a row with quest_log_flags = 0 accepts with flags 0 (retail's value "
           "on 5 of the tape's 12 accepts)", f"{add0}")
    led.ok(re0 == [ERRAND, 0, reg, nm, nm, 148],
           "and its 0x0050 on the NEXT map (168) carries flags 0 and home 148 "
           "-- the accepting map, not the one being loaded", f"{re0}")
    led.ok(log_words_hold(add0, 148, [re0]),
           "and the tape's rule (log_words_hold) holds on ours", f"{add0} {re0}")
    # A quest held with no recorded home: the loaded map, as before S18.
    rep_nohome, = drive(rows0, [("replay", [ERRAND], 168, {})])
    led.ok(first(rep_nohome, REPLAY) == [ERRAND, 0, reg, nm, nm, 168],
           "a held quest with NO recorded home replays the loaded map (the "
           "pre-S18 value) with the row's flags", f"{first(rep_nohome, REPLAY)}")
    # KNOWN-BAD: --no-retail-quest-log.
    b_acc, b_rep = drive(rows0, [("accept", ERRAND, 148, {}),
                                 ("replay", [ERRAND], 168, {})], retail=False)
    b_add, b_re = first(b_acc, ACCEPT), first(b_rep, REPLAY)
    led.ok(b_add is not None and b_add[4] == 32 and b_re is not None
           and b_re[1] == 32 and b_re[5] == 168,
           "KNOWN-BAD arm (--no-retail-quest-log): the flags-0 row accepts AND "
           "replays with 32, and the replay's home is the loaded 168 -- every "
           "run before S18", f"{b_add[4] if b_add else None} {b_re}")
    led.ok(not log_words_hold(b_add, 148, [b_re]),
           "and the tape's rule goes RED on it", f"{b_re}")
    # VACUITY: the rule refuses each near miss.
    a = [ERRAND, (0.0, 0.0), 0, 148, 0, nm, nm, nm, 148]
    r = [ERRAND, 0, nm, nm, nm, 148]
    misses = {"no replay": (a, 148, []),
              "accept home not the accepting map": (a, 146, [r]),
              "replay flags 32": (a, 148, [[ERRAND, 32, nm, nm, nm, 148]]),
              "replay home the loaded map": (a, 148, [[ERRAND, 0, nm, nm, nm, 168]])}
    red = {k: log_words_hold(*m) for k, m in misses.items()}
    led.ok(not any(red.values()) and log_words_hold(a, 148, [r])
           and log_words_hold(a, 148, [[ERRAND, 2, nm, nm, nm, 148]]),
           "VACUITY: the rule refuses each near miss and accepts the exact "
           "shape, bit 1 on the replay included (the tape's q79 34)", f"{red}")
    # log_flags: the row's word, and what it refuses.
    bad_vals = [1, 2, 3, 34, -1, 2 ** 32, True, "32", 32.0]
    refused = []
    for v in bad_vals:
        try:
            questdefs.log_flags({"quest_log_flags": v})
        except ValueError:
            refused.append(v)
    led.ok(refused == bad_vals
           and questdefs.log_flags({}) == questdefs.QUEST_LOG_FLAGS_DEFAULT == 32
           and questdefs.log_flags({"quest_log_flags": 0}) == 0
           and questdefs.log_flags({"quest_log_flags": 0x40}) == 0x40,
           "questdefs.log_flags: absent is 32; 0, 32 and 0x40 pass; bit 0 or 1 "
           "(1, 2, 3, 34), a negative, past a u32, a bool, a str and a float "
           "are REFUSED", f"refused {refused}")

    class _World:
        def __init__(self, rows_):
            self._r = rows_

        def rows(self, kind):
            return self._r if kind == "quest" else {}
    try:
        questdefs.load(_World({"q": {"quest_id": 7, "quest_log_flags": 2}}))
        load_refused = ""
    except ValueError as exc:
        load_refused = str(exc)
    led.ok("'q'" in load_refused and "bit 0 or 1" in load_refused
           and all(questdefs.log_flags(r) == 32 for r in rows.values()),
           "questdefs.load refuses a row with flags 2 at STARTUP, naming it; "
           "every shipped row loads at 32", load_refused)
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.no_retail_quest_log:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--no-retail-quest-log"]).no_retail_quest_log
           and not ap.parse_args([]).no_retail_quest_log
           and authsrv.QUEST_LOG_RETAIL is True
           and "global QUEST_LOG_RETAIL\n" in window
           and "QUEST_LOG_RETAIL = False\n" in window,
           "--no-retail-quest-log parses, the default is the row's words, and "
           "main() sets QUEST_LOG_RETAIL = False under it",
           f"window found={at >= 0}")


def section_7():
    print(f"\n7. RANGERPRE-S18 (QUESTFLOW-A1): the TAPE {TAPE_S18} -- its 12 "
          "accepts and 37 replays")
    conns = tape_s18()
    if conns is None:
        led.skip(f"the tape {TAPE_S18}", "no capture directory (bare machine)")
        return
    accepts, replays = [], []
    for port, cmap, merged, ok in conns:
        for t, d, op, v in merged:
            if d == "s2c" and op == ACCEPT:
                accepts.append((port, round(t, 4), v[1], v, cmap))
            elif d == "s2c" and op == REPLAY:
                replays.append((port, round(t, 4), v[1], v, cmap))
    led.ok(all(ok for _p, _m, _s, ok in conns) and len(conns) == 11,
           f"TAPE {TAPE_S18}: all 11 game connections decode", f"{len(conns)}")
    got = {(p, t, q, v[-5]) for p, t, q, v, _m in accepts}
    led.ok(got == ACCEPTS_S18 and len(accepts) == 12,
           "TAPE: exactly the 12 accepts, pinned by port, batch t, qid and log "
           "flags -- 0 on q80 q90 q52 q68 q75, 32 on the other seven",
           f"{sorted(got ^ ACCEPTS_S18)}")
    led.ok(all(v[-1] == m for _p, _t, _q, v, m in accepts),
           "TAPE: every accept's home is the accepting connection's own map "
           "(tape.client_version), 12 of 12",
           f"{[(p, q, v[-1], m) for p, _t, q, v, m in accepts if v[-1] != m]}")
    acc = {q: (v, m) for _p, _t, q, v, m in accepts}
    exact = [(p, t, q) for p, t, q, v, _m in replays if v[-5] == acc[q][0][-5]]
    odd = [(p, t, q, v[-5]) for p, t, q, v, _m in replays
           if v[-5] != acc[q][0][-5]]
    led.ok(len(replays) == 37 and all(q in acc for _p, _t, q, _v, _m in replays)
           and len(exact) == 36 and odd == [("59427", 1216.7834, 79, 34)],
           "TAPE: 37 replays, every one of a quest accepted on this tape; 36 "
           "repeat the accept's flags exactly and the 37th is q79 on :59427 at "
           "34 = 32 | 2 (after its 0x004D, :53756 1192.658)", f"{odd}")
    by_q = {}
    for _p, _t, q, v, _m in replays:
        by_q.setdefault(q, []).append(v)
    held = {q: log_words_hold(acc[q][0], acc[q][1], by_q[q]) for q in by_q}
    cross = sum(1 for _p, _t, _q, v, m in replays if v[-1] != m)
    led.ok(all(held.values()) and len(held) == 8 and cross == 27,
           "TAPE: log_words_hold on all 8 replayed quests -- 27 of the 37 "
           "replays carry a home that is NOT the map being loaded", f"{held} "
           f"cross={cross}")
    # OURS vs TAPE: each quest accepted on its accepting map with a row
    # carrying the tape's flags, then each connection's load replayed on its
    # own map -- (flags, home) compared per replay.
    rows = rows_with({q: {"quest_log_flags": v[-5]} for q, (v, _m) in acc.items()})
    steps = [("accept", q, m, {}) for q, (v, m) in sorted(acc.items())]
    loads = {}
    for p, t, q, v, m in replays:
        loads.setdefault((p, t, m), []).append((q, v))
    order = sorted(loads)
    steps += [("replay", [q for q, _v in loads[k]], k[2], {}) for k in order]

    def score(retail):
        outs = drive(rows, steps, retail=retail)
        n_acc = sum(1 for (q, (v, m)), o in zip(sorted(acc.items()),
                                                 outs[:len(acc)])
                    if (first(o, ACCEPT)[4], first(o, ACCEPT)[8])
                    == (v[-5], v[-1]))
        eq, ne = 0, []
        for k, o in zip(order, outs[len(acc):]):
            ours = {v[0]: (v[1], v[5]) for op, v in o if op == REPLAY}
            for q, v in loads[k]:
                if ours.get(q) == (v[-5], v[-1]):
                    eq += 1
                else:
                    ne.append((k[0], k[1], q, ours.get(q), (v[-5], v[-1])))
        return n_acc, eq, ne
    n_acc, eq, ne = score(True)
    led.ok(n_acc == 12 and eq == 36
           and [(p, t, q) for p, t, q, _o, _t2 in ne] == [("59427", 1216.7834, 79)]
           and ne[0][3] == (32, 148) and ne[0][4] == (34, 148),
           "OURS vs TAPE: our 12 accepts carry the tape's (flags, home) and our "
           "replays equal 36 of the 37 -- the odd one q79's 34, bit 1 of a "
           "0x004D we do not send", f"accepts {n_acc}, replays {eq}, {ne}")
    b_acc, b_eq, _b_ne = score(False)
    led.ok(b_acc == 7 and b_eq == 3,
           "KNOWN-BAD: --no-retail-quest-log matches only the 7 flag-32 "
           "accepts and 3 of 37 replays (flag 32 AND home = the loaded map)",
           f"accepts {b_acc}, replays {b_eq}")


def section_8():
    print("\n8. RANGERPRE-S18 (QUESTFLOW-A1): the live CORPUS -- every accept "
          "and replay")
    c = corpus()
    if c is None:
        led.skip("section 8, the live corpus", "no live captures")
        return
    acc = c["accepts"]
    flags = [v[-5] for _c, _p, _t, v, _m, _b in acc]
    per_q = {}
    for _c, _p, _t, v, _m, _b in acc:
        per_q.setdefault(v[1], set()).add(v[-5])
    led.ok(len(acc) >= 30 and set(flags) <= {0, 32} and flags.count(0) >= 11
           and all(len(s) == 1 for s in per_q.values()),
           f"CORPUS: {len(acc)} accepts (floor 30), flags only 0 or 32 "
           f"({flags.count(0)} zeros, floor 11), each quest ONE value across "
           f"every capture ({len(per_q)} quests)",
           f"{ {q: sorted(s) for q, s in per_q.items() if len(s) > 1} }")
    led.ok(all(v[-1] == m for _c, _p, _t, v, m, _b in acc),
           f"CORPUS: every accept's home is the accepting connection's map "
           f"({len(acc)} of {len(acc)})",
           f"{[(cc, p, t, v[-1], m) for cc, p, t, v, m, _b in acc if v[-1] != m]}")
    home = {v[1]: (v[-5], v[-1]) for _c, _p, _t, v, _m, _b in acc}
    rep = [(cc, p, t, v) for cc, p, t, v, _m in c["replays"] if v[1] in home]
    exact = sum(1 for *_x, v in rep if v[-5] == home[v[1]][0])
    bad = [(cc, p, t, v[1], v[-5], v[-1]) for cc, p, t, v in rep
           if (v[-5] & ~2) != home[v[1]][0] or v[-1] != home[v[1]][1]]
    led.ok(len(rep) >= 90 and exact >= 87 and not bad,
           f"CORPUS: {len(rep)} replays of an accepted quest (floor 90) carry "
           f"its flags ({exact} exactly, floor 87; the rest add only bit 1) and "
           f"its home, every one", f"{bad}")


# ---------------------------------------------------------------- S18 / A3
ITEM = authsrv.GAME_SMSG_CREATE_NAMED_ITEM             # 0x0161
IADD = authsrv.GAME_SMSG_ITEM_MOVED_TO_LOCATION        # 0x013E
SHOW = authsrv.GAME_SMSG_NPC_DIALOG_SHOW               # 0x0081
GRANT_KINDS = ("ITEM", "IADD") + SK_KINDS
# q75's accept batch, :56064 921.1613, reduced (OBSERVED): the sword, then
# skills 382 and 384 (0x001C for 384 alone) and 1 into bar slots 2, 3, 4.
Q75_ACCEPT = ["ITEM", "IADD", "SKC:382", "SKB:2:382", "SKC:384", "SKB:3:384",
              "SKU:384", "SKC:1", "SKB:4:1", "ADD", "SHOW"]


def reduce_accept(seq):
    """An accept batch reduced to the grants, the 0x0049 and the 0x0081, in
    sequence -- the skill lines as reduce_batch spells them (id, bar slot)."""
    out = []
    for op, v in seq:
        if op == ITEM:
            out.append("ITEM")
        elif op == IADD:
            out.append("IADD")
        elif op == ACCEPT:
            out.append("ADD")
        elif op == SHOW:
            out.append("SHOW")
        elif op in (SKC, SKB, SKU):
            out += reduce_batch([(op, v)])
    return out


def grants_before_add(red):
    """The tape's rule, 2 of 2: one 0x0049; at least one grant; every grant
    line BEFORE the 0x0049; and each 0x013E preceded by at least as many
    0x0161 (an item declared before it is placed)."""
    kinds = [r.split(":")[0] for r in red]
    if kinds.count("ADD") != 1:
        return False
    at = kinds.index("ADD")
    grants = [i for i, k in enumerate(kinds) if k in GRANT_KINDS]
    if not grants or max(grants) > at:
        return False
    return all(kinds[:i].count("ITEM") > kinds[:i].count("IADD")
               for i, k in enumerate(kinds) if k == "IADD")


def section_9():
    print("\n9. RANGERPRE-S18 (QUESTFLOW-A3): OURS -- the accept's item and "
          "skill grants, before the 0x0049")
    import questdefs
    grant = {"accept_items": ["starter_sword"], "accept_skills": [382, 384]}
    rows = rows_with({ERRAND: grant})
    items = {}
    acc, = drive(rows, [("accept", ERRAND, 148, {"items": items})])
    st = drive.state
    red = reduce_accept(acc)
    led.ok(red == ["ITEM", "IADD", "SKC:382", "SKB:0:382", "SKU:382",
                   "SKC:384", "SKB:1:384", "SKU:384", "ADD", "SHOW"],
           "accept_quest for {accept_items [starter_sword], accept_skills "
           "[382, 384]}: the sword 0x0161 + 0x013E, then 0x00DC / 0x00D9 / "
           "0x001C per skill, THEN the 0x0049, then the 0x0081 -- q75's order",
           f"{red}")
    led.ok(grants_before_add(red), "and the tape's rule holds on it", f"{red}")
    base = authsrv.merchant.PURCHASED_ITEM_ID_BASE
    tmpl = authsrv.agents.item_template("starter_sword")
    led.ok(first(acc, ITEM) == authsrv.agents.named_item(base, tmpl)
           and first(acc, IADD) == [authsrv.PLAYER_INVENTORY_KEY, base,
                                    authsrv.BACKPACK_BAG_ID, 0]
           and st["backpack"] == {0: base} and st["next_purchased_item"] == base + 1
           and items.get(base) == {"bag": authsrv.BACKPACK_BAG_ID, "slot": 0,
                                   "key": "starter_sword", "kind": "reward",
                                   "item_type": 27},
           "grant_item: the sword row declared as item "
           f"{base} (the purchase counter), placed in backpack slot 0, and "
           "registered in the merchant's map and the item store as kind "
           "'reward' under its content key",
           f"{first(acc, IADD)} backpack={st.get('backpack')} {items.get(base)}")
    # The cell: clear of the item store and the merchant's map.
    bp = authsrv.BACKPACK_BAG_ID
    items2 = {7: {"bag": bp, "slot": 0, "key": None, "kind": None, "item_type": 24},
              8: {"bag": bp, "slot": 1, "key": None, "kind": None, "item_type": 27}}
    acc2, = drive(rows, [("accept", ERRAND, 148,
                          {"items": items2, "backpack": {2: 4999},
                           "next_purchased_item": 6000})])
    led.ok(first(acc2, IADD) == [authsrv.PLAYER_INVENTORY_KEY, 6000, bp, 3],
           "the cell is the lowest one free of the item store (slots 0, 1) "
           "and the merchant's map (slot 2): slot 3, id 6000",
           f"{first(acc2, IADD)}")
    size = authsrv.player_bags()[bp]
    full = {100 + s: {"bag": bp, "slot": s, "key": None, "kind": None,
                      "item_type": 24} for s in range(size)}
    acc3, = drive(rows, [("accept", ERRAND, 148, {"items": full})])
    red3 = reduce_accept(acc3)
    led.ok(red3 == ["SKC:382", "SKB:0:382", "SKU:382", "SKC:384", "SKB:1:384",
                    "SKU:384", "ADD", "SHOW"],
           f"a FULL backpack ({size} slots): no 0x0161 / 0x013E, the skills "
           "and the accept still go", f"{red3}")
    # RE-AIMED for RANGERLOOP-F6: the account's library (held), not a faked
    # skills_known; §15 covers the connection's own earlier grant.
    acc4, = drive(rows, [("accept", ERRAND, 148, {})], held={382})
    led.ok(reduce_accept(acc4)[2:5] == ["SKC:382", "SKB:0:382", "SKC:384"],
           "a skill the account already holds sends no 0x001C",
           f"{reduce_accept(acc4)}")
    # A skill past the served table is REFUSED by grant_skill (nothing sent,
    # nothing stored): the grants summary -- a run-sheet readout -- must not
    # name it, and a row whose only grant is refused prints no summary.
    import contextlib
    import io
    past = authsrv.SKILL_TABLE_ROWS
    lines = {}
    for tag, sids in (("mixed", [382, past]), ("only", [past])):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got, = drive(rows_with({ERRAND: {"accept_skills": sids}}),
                         [("accept", ERRAND, 148, {})])
        said = buf.getvalue().splitlines()
        lines[tag] = (reduce_accept(got),
                      [s for s in said if "accept grants, BEFORE" in s],
                      sum(f"grant of skill {past} REFUSED" in s for s in said))
    mixed, only = lines["mixed"], lines["only"]
    led.ok(mixed[0] == ["SKC:382", "SKB:0:382", "SKU:382", "ADD", "SHOW"]
           and len(mixed[1]) == 1 and mixed[1][0].endswith(
               "BEFORE the 0x0049: skill 382 (RANGERPRE-S18, QUESTFLOW-A3)")
           and mixed[2] == 1
           and only[0] == ["ADD", "SHOW"] and only[1] == [] and only[2] == 1,
           f"a skill past the served table ({past}) is refused and the grants "
           "summary does NOT name it: [382, it] says 'skill 382' alone, [it] "
           "prints no summary; each says REFUSED once", f"{lines}")
    # KNOWN-BAD: --no-accept-rewards.
    bad, = drive(rows, [("accept", ERRAND, 148, {})], ACCEPT_REWARDS=False)
    led.ok(reduce_accept(bad) == ["ADD", "SHOW"] and not grants_before_add(
        reduce_accept(bad)),
           "KNOWN-BAD arm (--no-accept-rewards): no grant at all -- the "
           "pre-S18 accept -- and the rule goes RED", f"{reduce_accept(bad)}")
    misses = {"no grant": ["ADD", "SHOW"],
              "a skill after the 0x0049": ["ITEM", "IADD", "ADD", "SKC:1", "SKB:0:1"],
              "placed before declared": ["IADD", "ITEM", "ADD"],
              "two 0x0049": ["SKC:1", "SKB:0:1", "ADD", "ADD"]}
    rmiss = {k: grants_before_add(m) for k, m in misses.items()}
    led.ok(not any(rmiss.values()) and grants_before_add(Q75_ACCEPT),
           "VACUITY: the rule refuses each near miss and accepts q75's batch",
           f"{rmiss}")
    # The loader refuses what the accept could not grant.
    world_items = {"starter_sword": {}}
    refused = []
    for bad_row in ({"accept_items": ["no_such_item"]},
                    {"accept_items": "starter_sword"},
                    {"accept_skills": [True]}, {"accept_skills": [-1]},
                    {"accept_skills": 382}):
        try:
            questdefs.check_accept_grants(bad_row, world_items)
        except ValueError:
            refused.append(bad_row)

    class _World:
        def rows(self, kind):
            return ({"q": {"quest_id": 7, "accept_items": ["nope"]}}
                    if kind == "quest" else world_items)
    try:
        questdefs.load(_World())
        load_msg = ""
    except ValueError as exc:
        load_msg = str(exc)
    led.ok(len(refused) == 5 and "'q'" in load_msg and "'nope'" in load_msg,
           "questdefs refuses an unknown item key, a bare string, a bool / "
           "negative skill and a bare int; load names the row at startup",
           f"refused {len(refused)}; {load_msg}")
    # A granted item's cell is per-session: _item_moves_commit persists a
    # plain item's move and NOT a reward's.
    wrote = []

    class _Store:
        def set_item_location(self, uuid_hex, iid, bag, slot):
            wrote.append(int(iid))
    cells = {base: {"bag": bp, "slot": 0, "key": "starter_sword",
                    "kind": "reward", "item_type": 27},
             101: {"bag": bp, "slot": 1, "key": None, "kind": None,
                   "item_type": 24}}
    saved_persist = authsrv.PERSIST
    authsrv.PERSIST = True
    try:
        authsrv._item_moves_commit(
            lambda *a, **k: None,
            {"items": cells, "backpack": {0: base}, "charstore_game": _Store(),
             "char_uuid": "u1"}, 0, [], [(base, bp, 5), (101, bp, 6)],
            "S18 test move")
    finally:
        authsrv.PERSIST = saved_persist
    led.ok(wrote == [101] and cells[base]["slot"] == 5,
           "_item_moves_commit under --persist writes the plain item's new "
           "cell and NOT the reward's (both moved)", f"wrote {wrote}")
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.no_accept_rewards:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--no-accept-rewards"]).no_accept_rewards
           and not ap.parse_args([]).no_accept_rewards
           and authsrv.ACCEPT_REWARDS is True
           and "global ACCEPT_REWARDS\n" in window
           and "ACCEPT_REWARDS = False\n" in window,
           "--no-accept-rewards parses, the default grants, and main() sets "
           "ACCEPT_REWARDS = False under it", f"window found={at >= 0}")


def section_10():
    print(f"\n10. RANGERPRE-S18 (QUESTFLOW-A3): the TAPE {TAPE_S18} :56064 q75 "
          "and the corpus's grant-carrying accepts")
    conns = tape_s18()
    if conns is None:
        led.skip(f"the tape {TAPE_S18}", "no capture directory (bare machine)")
    else:
        merged = next((m for p, _mp, m, _ok in conns if p == "56064"), [])
        t_acc = next((t for t, d, op, v in merged if d == "s2c" and op == ACCEPT
                      and v[1] == 75 and abs(t - 921.1613) < 0.001), None)
        batch = [(op, v) for t, d, op, v in merged
                 if d == "s2c" and t_acc is not None and t == t_acc]
        red = reduce_accept(batch)
        led.ok(red == Q75_ACCEPT,
               "TAPE :56064 921.1613 q75: the accept batch reduces to "
               + " ".join(Q75_ACCEPT), f"{red}")
        led.ok(grants_before_add(red),
               "TAPE: every grant before the 0x0049, the item declared before "
               "it is placed", f"{red}")
        it, ia = first(batch, ITEM), first(batch, IADD)
        led.ok(it is not None and ia is not None and it[1] == ia[-3]
               and it[3] == 27,
               "TAPE: the 0x013E places the item the 0x0161 declared (id "
               f"{it[1] if it else None}, type 27 -- a sword)", f"{it} {ia}")
        # OURS vs TAPE: q75's own grants, the bar holding two skills, and the
        # ACCOUNT the tape's own -- RE-AIMED for RANGERLOOP-F6. This used to
        # fake skills_known = {382, 1} to reproduce the lone 0x001C (384's),
        # because ours gated the toast on that per-connection set; the gate
        # now reads the account's library, so the fixture hands it the
        # library this account's client was holding: the tape's last 0x001D
        # before the accept (tape_library).
        lib, lib_at = tape_library(conns, 921.1613)
        led.ok(lib is not None and len(lib) == 38 and {382, 1} <= lib
               and 384 not in lib,
               "TAPE: the account library in force at q75's accept is the "
               f"0x001D at {lib_at} -- 38 skills, 382 and 1 among them, 384 "
               "not", f"{None if lib is None else len(lib)} {lib_at}")
        rows = rows_with({ERRAND: {"accept_items": ["starter_sword"],
                                   "accept_skills": [382, 384, 1]}})
        bar = [331, 332] + [0] * (authsrv.SKILLBAR_SLOTS - 2)
        held = lib or ()
        ours_b, = drive(rows, [("accept", ERRAND, 160, {})], bar=bar,
                        held=held)
        bad_b, = drive(rows, [("accept", ERRAND, 160, {})], bar=bar,
                       held=held, ACCEPT_REWARDS=False)
        led.ok(reduce_accept(ours_b) == red,
               "OURS vs TAPE: accept_quest for q75's grants, on the tape's own "
               "account library and NO skills_known, equals the tape on every "
               "reduced kind, skill id and bar slot -- the lone 0x001C 384's",
               f"ours {reduce_accept(ours_b)} tape {red}")
        led.ok(reduce_accept(bad_b) != red,
               "KNOWN-BAD: --no-accept-rewards does NOT equal the tape",
               f"{reduce_accept(bad_b)}")
        gate_b, = drive(rows, [("accept", ERRAND, 160, {})], bar=bar,
                        held=held, ACCOUNT_UNLOCK_GATE=False)
        led.ok([k for k in reduce_accept(gate_b) if k.startswith("SKU")]
               == ["SKU:382", "SKU:384", "SKU:1"],
               "KNOWN-BAD: --no-account-unlock-gate on the same library sends "
               "0x001C for 382 and 1 too -- the toast RANGERLOOP-F6 saw -- and "
               "does NOT equal the tape", f"{reduce_accept(gate_b)}")
        sab = list(batch)
        ai = next(i for i, (op, _v) in enumerate(sab) if op == ACCEPT)
        si = next(i for i, (op, _v) in enumerate(sab) if op == SKC)
        sab.insert(si, sab.pop(ai))
        led.ok(not grants_before_add(reduce_accept(sab)),
               "KNOWN-BAD: a sabotaged tape (the 0x0049 moved ahead of the "
               "first skill) FAILS the rule", f"{reduce_accept(sab)}")
    c = corpus()
    if c is None:
        led.skip("section 10's corpus half", "no live captures")
        return
    carrying = [(cc, p, t, v[1], reduce_accept(b)) for cc, p, t, v, _m, b
                in c["accepts"]
                if any(k.split(":")[0] in GRANT_KINDS for k in reduce_accept(b))]
    led.ok(len(carrying) >= 2 and all(grants_before_add(r) for *_x, r in carrying),
           f"CORPUS: every grant-carrying accept ({len(carrying)}, floor 2 -- "
           "q75 here and q270 on 20260819T132414 :52606) grants BEFORE its "
           "0x0049, none after",
           f"{[(cc, p, t, q) for cc, p, t, q, r in carrying if not grants_before_add(r)]}")


# ---------------------------------------------------------------- S18 / A2
MOVE_MARKER = authsrv.GAME_SMSG_QUEST_MOVE_MARKER      # 0x0051
TRANSFER = 0x01A5                                      # the tape's handoff
# The tape's 12 accept markers by where they sit (OBSERVED, livewire):
# exactly on an NPC's 0x0020 create spot with its plane; naming a map other
# than the accepting one; neither.
ON_SPOT_S18 = {79, 86, 54, 80, 89}
CROSS_MAP_S18 = {90, 62, 68, 1462, 222}
OTHER_S18 = {52, 75}


def marker_of(add):
    """(pos, plane, map) of a 0x0049, read from the END: [.., qid, pos,
    plane, map, flags, s1, s2, s3, home]."""
    return tuple(add[-8]), add[-7], add[-6]


def marker_placed(add, here, spots, exits):
    """The tape's rule for 10 of its 12 accepts: a marker on THIS map sits
    exactly on an objective body's (x, y, plane); one naming ANOTHER map sits
    on an exit of this map, plane 0. `spots` {(x, y, plane)}, `exits` {(x, y)}."""
    (x, y), plane, mmap = marker_of(add)
    if mmap == here:
        return (float(x), float(y), plane) in spots
    return plane == 0 and (float(x), float(y)) in exits


def section_11():
    print("\n11. RANGERPRE-S18 (QUESTFLOW-A2): OURS -- the accept marker on the "
          "objective, or on the exit toward it")
    import questdefs
    rows = questdefs.load()
    nm_e = questdefs.enc_string(rows[ERRAND]["enc_name"])
    nm_b = questdefs.enc_string(rows[BANDITS]["enc_name"])
    # RE-AIMED for RANGERLOOP-F5: s1 is the row's region (0x3D64) now, not
    # the name; this section is about the marker (§17 holds the slots).
    reg = questdefs.enc_string(rows[ERRAND]["enc_region"])
    scout = {"pos": (8933.0, 7752.0), "plane": 0}
    live = {"agents": {98: dict(scout)}}
    e, b = drive(rows, [("accept", ERRAND, 148, live),
                        ("accept", BANDITS, 148, live)])
    add_e, add_b = first(e, ACCEPT), first(b, ACCEPT)
    led.ok(add_e == [ERRAND, (8933.0, 7752.0), 0, 148, 32, reg, nm_e, nm_e, 148],
           "the errand's 0x0049 marks the scout (errand_scout, 8933, 7752) with "
           "its live plane on this map", f"{add_e}")
    led.ok(add_b == [BANDITS, (9326.0, 8077.0), 0, 168, 32, reg, nm_b, nm_b, 148],
           "the bandits' 0x0049 marks the exit ascalon_to_corridor (9326, 8077) "
           "on 148, plane 0, labelled 168 -- the kill target's map", f"{add_b}")
    spots = {(8933.0, 7752.0, 0)}
    exits = {(float(r["x"]), float(r["y"])) for _k, r in authsrv.portal_rows(148)}
    led.ok(marker_placed(add_e, 148, spots, exits)
           and marker_placed(add_b, 148, spots, exits),
           "and the tape's rule (marker_placed) holds on both",
           f"{marker_of(add_e)} {marker_of(add_b)}")
    st = {"map_id": 148, "pos": (9826.0, 8077.0)}
    m3 = authsrv.quest_accept_marker(dict(st, agents={98: {"pos": (8933.0, 7752.0),
                                                          "plane": 3}}),
                                     rows[ERRAND])
    m0 = authsrv.quest_accept_marker(dict(st, agents={}), rows[ERRAND])
    led.ok(m3[:3] == ((8933.0, 7752.0), 3, 148) and m0[:3] == ((8933.0, 7752.0), 0, 148)
           and "no live body" in m0[3],
           "the plane is the LIVE body's (3 here, as q80's 26 is agent 40's); "
           "a body not live marks plane 0 and says so", f"{m3} {m0}")
    syn = {148: [("a", {"to_map": 146, "x": 1.0, "y": 2.0}),
                 ("z", {"to_map": 999, "x": 9.0, "y": 9.0})],
           146: [("b", {"to_map": 168, "x": 3.0, "y": 4.0}),
                 ("c", {"to_map": 148, "x": 5.0, "y": 6.0})]}

    def rows_of(m):
        return syn.get(int(m), [])
    route = authsrv.portal_route(148, 168, rows_of)
    m2 = authsrv.quest_accept_marker(dict(st, agents={}), rows[BANDITS], rows_of)
    led.ok([k for k, _r in route or []] == ["a", "b"]
           and authsrv.portal_route(148, 148, rows_of) == []
           and authsrv.portal_route(148, 777, rows_of) is None
           and m2[:3] == ((1.0, 2.0), 0, 168) and "hop 1 of 2" in m2[3],
           "portal_route: a two-hop route 148 -> 146 -> 168 marks the FIRST "
           "exit and names the FINAL map (retail's (7311, 5438) exit for "
           "objectives on 146, 160 and 164); here is [], unreachable None",
           f"{route} {m2}")
    m_none = authsrv.quest_accept_marker(dict(st, agents={}), rows[BANDITS],
                                         lambda m: [])
    m_empty = authsrv.quest_accept_marker(dict(st, agents={}), {})
    m_typo = authsrv.quest_accept_marker(dict(st, agents={}),
                                         {"objective_kill": "no_such_row"})
    led.ok(all(m[:3] == ((9826.0, 8077.0), 0, 148)
               for m in (m_none, m_empty, m_typo))
           and "no portal route" in m_none[3]
           and "names no objective" in m_empty[3]
           and "'no_such_row'" in m_typo[3],
           "no route, no target, or a key naming no spawn row: the pre-S18 "
           "placeholder (the player, plane 0, this map), each saying why",
           f"{m_none[3]} | {m_empty[3]} | {m_typo[3]}")
    m_probe = authsrv.quest_accept_marker(
        dict(st, agents={98: {"pos": (100.0, 200.0), "plane": 5}}),
        {"objective_agent": 98})
    m_giver = authsrv.quest_accept_marker(dict(st, agents={}),
                                          {"giver_spawn": "errand_giver"})
    led.ok(m_probe[:3] == ((100.0, 200.0), 5, 148)
           and m_giver[:3] == ((10026.0, 8077.0), 0, 148),
           "the probe binding marks the live objective_agent's body and plane; "
           "a row with only a giver marks the giver (q79's shape, n = 1)",
           f"{m_probe} {m_giver}")
    # KNOWN-BAD: --quest-marker-at-player.
    be, bb = drive(rows, [("accept", ERRAND, 148, live),
                          ("accept", BANDITS, 148, live)],
                   QUEST_MARKER_AT_OBJECTIVE=False)
    bad_e, bad_b = first(be, ACCEPT), first(bb, ACCEPT)
    led.ok(marker_of(bad_e) == marker_of(bad_b) == ((9826.0, 8077.0), 0, 148)
           and not marker_placed(bad_e, 148, spots, exits)
           and not marker_placed(bad_b, 148, spots, exits),
           "KNOWN-BAD arm (--quest-marker-at-player): both markers at the "
           "player's own (9826, 8077) on 148 -- every run before S18 -- and "
           "the rule goes RED on both", f"{marker_of(bad_e)} {marker_of(bad_b)}")
    near = {"off the spot by 1 u": [1, (8934.0, 7752.0), 0, 148],
            "the spot on the wrong plane": [1, (8933.0, 7752.0), 2, 148],
            "cross-map off every exit": [1, (1.0, 1.0), 0, 168],
            "an exit on plane 3": [1, (9326.0, 8077.0), 3, 168]}
    rnear = {k: marker_placed(v + [32, "", "", "", 148], 148, spots, exits)
             for k, v in near.items()}
    led.ok(not any(rnear.values()),
           "VACUITY: the rule refuses each near miss", f"{rnear}")
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.quest_marker_at_player:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--quest-marker-at-player"]).quest_marker_at_player
           and not ap.parse_args([]).quest_marker_at_player
           and authsrv.QUEST_MARKER_AT_OBJECTIVE is True
           and "global QUEST_MARKER_AT_OBJECTIVE\n" in window
           and "QUEST_MARKER_AT_OBJECTIVE = False\n" in window,
           "--quest-marker-at-player parses, the default marks the objective, "
           "and main() sets QUEST_MARKER_AT_OBJECTIVE = False under it",
           f"window found={at >= 0}")


def section_12():
    print(f"\n12. RANGERPRE-S18 (QUESTFLOW-A2): the TAPE {TAPE_S18} -- where its "
          "12 accept markers sit")
    import math
    conns = tape_s18()
    if conns is None:
        led.skip(f"the tape {TAPE_S18}", "no capture directory (bare machine)")
        return
    cat = {"spot": set(), "cross": set(), "other": set()}
    placed, depart, multi = [], [], {}
    for port, cmap, merged, _ok in conns:
        creates = {(float(v[5][0]), float(v[5][1]), v[6])
                   for t, d, op, v in merged if d == "s2c" and op == 0x0020}
        accs = [(t, v) for t, d, op, v in merged if d == "s2c" and op == ACCEPT]
        for t, v in accs:
            (x, y), plane, mmap = marker_of(v)
            if mmap != cmap:
                cat["cross"].add(v[1])
            elif (float(x), float(y), plane) in creates:
                cat["spot"].add(v[1])
                placed.append((v[1], marker_placed(v, cmap, creates, set()),
                               plane))
            else:
                cat["other"].add(v[1])
        tr = [(t, v) for t, d, op, v in merged if d == "s2c" and op == TRANSFER]
        cross = [(t, v) for t, v in accs if marker_of(v)[2] != cmap]
        if tr and cross:
            t_tr, v_tr = tr[-1]
            pts = [v[1] for t, d, op, v in merged if d == "c2s" and op == 0x003D
                   and t < t_tr and isinstance(v[1], tuple)]
            for t, v in cross:
                (x, y), _pl, mmap = marker_of(v)
                if mmap != v_tr[4] or not pts:
                    continue    # left for another map: not this marker's exit
                depart.append((port, v[1], round(math.hypot(
                    pts[-1][0] - x, pts[-1][1] - y)), mmap))
        if port == "53880":
            for t, d, op, v in merged:
                if d == "s2c" and op == MOVE_MARKER and v[-1] != cmap \
                        and v[-3][0] != float("inf"):
                    multi.setdefault(tuple(v[-3]), set()).add(v[-1])
    led.ok(cat["spot"] == ON_SPOT_S18 and cat["cross"] == CROSS_MAP_S18
           and cat["other"] == OTHER_S18,
           "TAPE: 5 accept markers sit EXACTLY on an NPC's 0x0020 create spot "
           "(q79 86 54 80 89), 5 name another map (q90 62 68 1462 222), 2 "
           "neither (q52 75)", f"{cat}")
    led.ok(len(placed) == 5 and all(ok for _q, ok, _p in placed)
           and sorted(p for q, _ok, p in placed if q in (80, 89)) == [26, 26],
           "TAPE: the rule (marker_placed) holds on all five create-spot "
           "markers, the plane included -- q80 and q89 on agent 40's plane 26",
           f"{placed}")
    led.ok(sorted(depart) == [("53880", 90, 202, 146), ("55934", 62, 387, 164),
                              ("59969", 222, 168, 146), ("59969", 1462, 168, 146)],
           "TAPE: each cross-map marker whose connection then LEFT for the "
           "marker's map sits within 387 u of the player's last position before "
           "that transfer (168, 202, 387 u) -- the marker is the exit",
           f"{depart}")
    led.ok(multi == {(7311.0, 5438.0): {146, 160, 164}},
           "TAPE :53880 (map 148): every 0x0051 marker naming another map uses "
           "the ONE exit (7311, 5438), for objectives on 146, 160 and 164 -- the "
           "first hop's exit, the final map's label", f"{multi}")


# ---------------------------------------------------------------- S20 / H4
DEL = authsrv.merchant.GAME_SMSG_ITEM_REMOVED          # 0x014D
ITEM_KINDS = ("DEL", "ITEM", "IADD")
TAPE_S20 = "20260929T150923"
# q62's hand-in on :53880 (OBSERVED, livewire): 0x014D [92, 3359] -- the quest
# item the 700.7599 load placed at [92, 3359, 452, 0] -- then 0x0161 [1607, type
# 24] and 0x013E [92, 1607, 452, 0], then the doubled 0x0052 frame. Its
# turn-in screen is the 0x0080 at 726.6797.
Q62_PORT, Q62_T, Q62_LOAD_T, Q62_SCREEN_T = "53880", 727.4875, 700.7599, 726.6797
Q62_HANDIN = ["DEL", "ITEM", "IADD", "RM", "EE0", "GOLD", "RM", "UNL"]
# q440's hand-in, 20260819T132414 :52606 (OBSERVED): no quest item; a type-30
# item declared and placed at [4, 652, 8, 0] (bag 8 that connection's
# backpack, slot 0 its lowest free cell) before the first 0x0052.
Q440 = ("20260819T132414", "52606", 145.4870, 440)
Q440_HANDIN = ["ITEM", "IADD", "RM", "EE0", "GOLD", "RM", "UNL"]
# The in-test row: q62's own numbers, a quest item back and a shield out.
H4_ROW = {"reward_experience": 250, "reward_gold": 25,
          "handin_items": ["starter_sword"], "reward_items": ["starter_shield"]}


def reduce_handin(seq):
    """A hand-in batch reduced to its item lines and reduce_batch's kinds, in
    sequence: DEL (0x014D), ITEM (a 0x0161 whose id a 0x013E of the SAME
    batch places -- an NPC's gear declared in a hand-in batch, :55934
    293.809's 480 / 481, is not the player's), IADD (0x013E). Ids read from
    the END: 0x0161 [.., id, 12 fields], 0x013E [.., key, id, bag, slot]."""
    placed = {v[-3] for op, v in seq if op == IADD}
    out = []
    for op, v in seq:
        if op == DEL:
            out.append("DEL")
        elif op == ITEM and v[-13] in placed:
            out.append("ITEM")
        elif op == IADD:
            out.append("IADD")
        else:
            out += reduce_batch([(op, v)])
    return out


def items_before_remove(red):
    """The tape's rule, 2 of 2 item-bearing hand-ins: at least one item line;
    every item line BEFORE the first 0x0052; every 0x014D before every
    0x0161 (the quest item goes before the reward arrives); each 0x013E
    preceded by at least as many 0x0161 (declared before placed)."""
    kinds = [r.split(":")[0] for r in red]
    lines = [i for i, k in enumerate(kinds) if k in ITEM_KINDS]
    if not lines or "RM" not in kinds or max(lines) > kinds.index("RM"):
        return False
    dels = [i for i, k in enumerate(kinds) if k == "DEL"]
    items = [i for i, k in enumerate(kinds) if k == "ITEM"]
    if dels and items and max(dels) > min(items):
        return False
    return all(kinds[:i].count("ITEM") > kinds[:i].count("IADD")
               for i, k in enumerate(kinds) if k == "IADD")


def vacated_refilled(seq, cells):
    """The q62 cell rule: the first 0x013E puts its item into the (bag, slot)
    the first 0x014D's item held. `cells` {item id: (bag, slot)} before the
    batch. False without a 0x014D, a 0x013E, or a known cell."""
    gone = next((v[-1] for op, v in seq if op == DEL), None)
    add = next((v for op, v in seq if op == IADD), None)
    if gone is None or add is None or gone not in cells:
        return False
    return (add[-2], add[-1]) == tuple(cells[gone])


def h4_state(**kw):
    """A hand-in state whose backpack holds a plain item at slot 0 and the
    quest's granted sword (kind 'reward', id 5000) at slot 5 -- so the cell
    it vacates (5) is NOT the lowest free one (1)."""
    bp = authsrv.BACKPACK_BAG_ID
    items = {7: {"bag": bp, "slot": 0, "key": None, "kind": None,
                 "item_type": 24},
             5000: {"bag": bp, "slot": 5, "key": "starter_sword",
                    "kind": "reward", "item_type": 27}}
    st = fresh_state(quests={1463}, items=items, backpack={5: 5000},
                     next_purchased_item=5001)
    st.update(kw)
    return st


def ours_handin(row, state, **flags):
    """OUR raw turn_in_quest batch [(op, values)] for `row` on `state`, with
    any authsrv flag in `flags`; flags and the bar restored."""
    saved = {k: getattr(authsrv, k) for k in
             ["REWARD_IN_FRAME", "QUEST_ITEMS_ENABLED"] + list(flags)}
    saved_bar = list(authsrv.SKILLBAR)
    authsrv.REWARD_IN_FRAME = True
    authsrv.QUEST_ITEMS_ENABLED = True
    for k, v in flags.items():
        setattr(authsrv, k, v)
    authsrv.SKILLBAR[:] = [0] * authsrv.SKILLBAR_SLOTS
    sent, send = collect()
    try:
        authsrv.turn_in_quest(send, state, 1463, row, 0)
    finally:
        for k, v in saved.items():
            setattr(authsrv, k, v)
        authsrv.SKILLBAR[:] = saved_bar
    return sent


def section_13():
    print("\n13. RANGERPRE-S20 (QUESTFLOW-H4): OURS -- the quest item back, the "
          "reward item into its cell, the shield's line on the screen")
    import contextlib
    import io
    import questdefs
    bp, key = authsrv.BACKPACK_BAG_ID, authsrv.PLAYER_INVENTORY_KEY
    st = h4_state()
    seq = ours_handin(H4_ROW, st)
    red = reduce_handin(seq)
    led.ok(red == ["DEL", "ITEM", "IADD", "RM", "EE0", "GOLD", "UNL"]
           and items_before_remove(red),
           "turn_in_quest for {handin_items [starter_sword], reward_items "
           "[starter_shield], 250 xp, 25 gold}: 0x014D, 0x0161, 0x013E, THEN "
           "the 0x0052 frame -- q62's order (its doubled 0x0052 is ours as one), "
           "and the tape's rule holds", f"{red}")
    shield = authsrv.agents.item_template("starter_shield")
    led.ok(first(seq, DEL) == [key, 5000]
           and first(seq, ITEM) == authsrv.agents.named_item(5001, shield)
           and first(seq, IADD) == [key, 5001, bp, 5]
           and vacated_refilled(seq, {5000: (bp, 5)}),
           "the bytes: 0x014D [key, 5000] takes the granted sword; the shield "
           "is declared as item 5001 (the purchase counter) and placed at "
           "backpack slot 5 -- the cell the sword vacated, NOT the lowest free "
           "cell (1)", f"{seq[:3]}")
    led.ok(5000 not in st["items"] and st["backpack"] == {5: 5001}
           and st["items"].get(5001) == {"bag": bp, "slot": 5,
                                         "key": "starter_shield",
                                         "kind": "reward", "item_type": 24},
           "the store and the merchant's map lose the sword and hold the "
           "shield (kind 'reward', so it stays per-session like a purchase)",
           f"backpack {st['backpack']} items {st['items']}")
    # The quest item not held: nothing taken, the reward to the lowest cell.
    st2 = h4_state(backpack={})
    st2["items"].pop(5000)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        seq2 = ours_handin(H4_ROW, st2)
    red2 = reduce_handin(seq2)
    led.ok(red2 == ["ITEM", "IADD", "RM", "EE0", "GOLD", "UNL"]
           and first(seq2, IADD) == [key, 5001, bp, 1]
           and "QUEST ITEM 'starter_sword' (quest 1463 handed in) NOT taken"
           in buf.getvalue(),
           "no granted sword held: no 0x014D, the shield to the lowest free "
           "cell (1), and the log says the quest item was NOT taken",
           f"{red2} {first(seq2, IADD)}")
    # A DRESSED item with the same key is never the quest item.
    st3 = h4_state(backpack={})
    st3["items"][5000].update(kind="set 1 lead")
    seq3 = ours_handin(H4_ROW, st3)
    led.ok(DEL not in [op for op, _v in seq3] and 5000 in st3["items"],
           "a weapon set's backpack sword (same key, kind 'set 1 lead') is NOT "
           "taken -- only an item grant_item minted is a quest item",
           f"{reduce_handin(seq3)}")
    # grant_item's named cell falls back when it is not free.
    st4 = h4_state()
    sent4, send4 = collect()
    authsrv.grant_item(send4, st4, 0, "starter_shield", "S20 test", slot=0)
    led.ok(first(sent4, IADD) == [key, 5001, bp, 1],
           "grant_item: a named cell that is occupied (slot 0) falls back to the "
           "lowest free one (1)", f"{first(sent4, IADD)}")
    # KNOWN-BAD: --no-quest-items.
    st5 = h4_state()
    bad = reduce_handin(ours_handin(H4_ROW, st5, QUEST_ITEMS_ENABLED=False))
    led.ok(bad == ["RM", "EE0", "GOLD", "UNL"] and not items_before_remove(bad)
           and 5000 in st5["items"],
           "KNOWN-BAD arm (--no-quest-items): no 0x014D, 0x0161 or 0x013E -- "
           "the pre-S20 hand-in, the sword still held -- and the rule goes RED",
           f"{bad}")
    misses = {"no item line": ["RM", "EE0", "UNL"],
              "the item after the 0x0052": ["RM", "ITEM", "IADD", "UNL"],
              "the 0x014D after the 0x0161": ["ITEM", "DEL", "IADD", "RM"],
              "placed before declared": ["IADD", "ITEM", "RM"],
              "no 0x0052": ["DEL", "ITEM", "IADD"]}
    rmiss = {k: items_before_remove(m) for k, m in misses.items()}
    led.ok(not any(rmiss.values()) and items_before_remove(Q62_HANDIN)
           and items_before_remove(Q440_HANDIN)
           and not vacated_refilled([(DEL, [1, 9]), (IADD, [1, 8, 2, 3])],
                                    {9: (2, 4)}),
           "VACUITY: the rule refuses each near miss and accepts q62's and "
           "q440's batches; the cell rule refuses a placement one slot off",
           f"{rmiss}")
    # THE SCREEN: the shield's line after the reward, the weapon's refused.
    rows = questdefs.load()
    b = dict(rows[BANDITS], reward_items=["starter_shield"])
    text = b["turn_in_dialogue"]
    drawn = authsrv._quest_prose(b, text)
    run = questdefs.reward_item_run([0x2186], 3)
    led.ok(drawn.endswith(run)
           and drawn == questdefs.with_reward(text, 250, None,
                                              limit=questdefs.DIALOG_UNITS,
                                              items=[([0x2186], 3)])
           and [ord(c) for c in run] == [
               0x0002, 0x2AEF, 0xF690, 0xD06E, 0x4C53, 0x010A, 0x2186, 0x0001,
               0x010B, 0x0A86, 0x010A, 0x0A44, 0x0001, 0x0101, 0x0103, 0x0001],
           "_quest_prose for the bandits + reward_items [starter_shield]: the "
           "reward block then ref 10735, the shield's name (0x2186, its "
           "0x0161's), template 2438 with label 2372 and its 572 argument 3",
           f"{[hex(ord(c)) for c in drawn[-16:]]}")
    saved = authsrv.QUEST_ITEMS_ENABLED
    authsrv.QUEST_ITEMS_ENABLED = False
    try:
        off = authsrv._quest_prose(b, text)
    finally:
        authsrv.QUEST_ITEMS_ENABLED = saved
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sword = authsrv._quest_prose(dict(b, reward_items=["starter_sword"]), text)
    led.ok(off == sword == questdefs.with_reward(text, 250, None,
                                                 limit=questdefs.DIALOG_UNITS)
           and "reward item 'starter_sword' (type 27) is granted but NOT DRAWN"
           in buf.getvalue() and "587" in buf.getvalue(),
           "--no-quest-items draws no item line; a WEAPON reward draws none "
           "either and says why (587's damage-type string table NOT FOUND)",
           buf.getvalue().strip())
    refused = []
    for name, armour in (([], 3), ([0x0041], 3), ([0x2186], -1),
                         ([0x2186], 0xFF00), ([0x2186], True)):
        try:
            questdefs.reward_item_run(name, armour)
        except ValueError:
            refused.append((name, armour))
    over = False
    long_text = "x" * (questdefs.DIALOG_UNITS - 3 - 4 - 12)
    fits = questdefs.with_reward(long_text, 1, None,
                                 limit=questdefs.DIALOG_UNITS)
    try:
        questdefs.with_reward(long_text, 1, None, limit=questdefs.DIALOG_UNITS,
                              items=[([0x2186], 3)])
    except ValueError:
        over = True
    led.ok(len(refused) == 5 and len(fits) == questdefs.DIALOG_UNITS and over,
           "reward_item_run refuses an empty name, a marker unit, and an "
           "armour past the biased u16 (a bool included); with_reward counts "
           "the item line in the SAME length check (a string that fits bare "
           "overflows with it)", f"refused {len(refused)}")
    world_items = {"starter_shield": {}}
    bad_rows = [{"reward_items": ["no_such_item"]},
                {"reward_items": "starter_shield"},
                {"handin_items": [7]}, {"handin_items": ["nope"]}]
    nref = 0
    for r in bad_rows:
        try:
            questdefs.check_handin_items(r, world_items)
        except ValueError:
            nref += 1

    class _World:
        def rows(self, kind):
            return ({"q": {"quest_id": 7, "reward_items": ["nope"]}}
                    if kind == "quest" else world_items)
    try:
        questdefs.load(_World())
        load_msg = ""
    except ValueError as exc:
        load_msg = str(exc)
    led.ok(nref == 4 and "'q'" in load_msg and "'nope'" in load_msg
           and questdefs.check_handin_items(H4_ROW, {"starter_sword": {},
                                                     "starter_shield": {}})
           is None,
           "questdefs.check_handin_items refuses an unknown key, a bare string "
           "and a non-string in either column and passes the in-test row; load "
           "names the row at startup", f"refused {nref}; {load_msg}")
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.no_quest_items:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--no-quest-items"]).no_quest_items
           and not ap.parse_args([]).no_quest_items
           and authsrv.QUEST_ITEMS_ENABLED is True
           and "global QUEST_ITEMS_ENABLED\n" in window
           and "QUEST_ITEMS_ENABLED = False\n" in window,
           "--no-quest-items parses, the default takes and grants, and main() "
           "sets QUEST_ITEMS_ENABLED = False under it", f"window found={at >= 0}")


def section_14():
    import questdefs
    print(f"\n14. RANGERPRE-S20 (QUESTFLOW-H4): the TAPE {TAPE_S20} :{Q62_PORT} "
          "q62, 20260819T132414 q440, and the corpus's item-bearing hand-ins")
    conns = tape_s18()
    if conns is None:
        led.skip(f"the tape {TAPE_S20}", "no capture directory (bare machine)")
    else:
        merged = next((m for p, _mp, m, _ok in conns if p == Q62_PORT), [])
        batch = [(op, v) for t, d, op, v in merged
                 if d == "s2c" and abs(t - Q62_T) < 0.0005]
        red = reduce_handin(batch)
        led.ok(red == Q62_HANDIN and items_before_remove(red),
               f"TAPE :{Q62_PORT} {Q62_T} q62: the hand-in reduces to "
               + " ".join(Q62_HANDIN) + ", and the rule holds", f"{red}")
        load = {v[-3]: (v[-2], v[-1]) for t, d, op, v in merged
                if d == "s2c" and op == IADD and abs(t - Q62_LOAD_T) < 0.0005}
        it, ia, gone = first(batch, ITEM), first(batch, IADD), first(batch, DEL)
        led.ok(gone is not None and gone[-1] == 3359 and load.get(3359) == (452, 0)
               and it is not None and ia is not None and it[-13] == ia[-3] == 1607
               and it[-11] == 24 and vacated_refilled(batch, load),
               "TAPE: the 0x014D takes 3359, which the load put at (452, 0); the "
               "0x013E places the 0x0161's item (1607, type 24 -- a shield) at "
               "(452, 0) -- the cell 3359 vacated", f"{gone} {ia} {load.get(3359)}")
        # THE LINE, VERBATIM: our builder fed the delivered item's own name
        # units and 572 argument equals the screen's and the 0x004C's tail.
        name = [ord(c) for c in it[-2]]
        rating = next(((w >> 8) & 0x3FF for (w,) in it[-1]
                       if (w >> 20) & 0x3FF == 572), None)
        screen = next((v[-1] for t, d, op, v in merged if d == "s2c"
                       and op == 0x0080 and abs(t - Q62_SCREEN_T) < 0.0005), "")
        desc = next((v[-2] for op, v in batch if op == 0x004C and v[-3] == 62), "")

        def tail(s):
            u = [ord(c) for c in s]
            k = u.index(0x2AEF) if 0x2AEF in u else None
            return u[k - 1:] if k else None
        ours_run = [ord(c) for c in questdefs.reward_item_run(name, rating)]
        led.ok(rating == 4 and tail(screen) == ours_run == tail(desc),
               "TAPE: reward_item_run(1607's name units, its 572 argument 4) "
               "EQUALS the tail of the turn-in screen's 0x0080 (726.6797) and of "
               "the hand-in's q62 0x004C, from the 0x0002 before ref 10735 to "
               "the end", f"ours {ours_run} screen {tail(screen)}")
        bad_run = [ord(c) for c in questdefs.reward_item_run(name, rating + 1)]
        led.ok(bad_run != tail(screen),
               "KNOWN-BAD: armour 5 does NOT equal the screen", f"{bad_run}")
        ours = ours_handin(H4_ROW, h4_state())
        bad = ours_handin(H4_ROW, h4_state(), QUEST_ITEMS_ENABLED=False)
        led.ok(reduce_handin(ours) == collapse_remove(red)
               and vacated_refilled(ours, {5000: (authsrv.BACKPACK_BAG_ID, 5)})
               and reduce_handin(bad) != collapse_remove(red),
               "OURS vs TAPE: turn_in_quest for q62's shape equals the tape on "
               "every reduced kind (its doubled 0x0052 collapsed), and refills "
               "the vacated cell as it does; --no-quest-items does NOT equal it",
               f"ours {reduce_handin(ours)} tape {collapse_remove(red)}")
        late = list(batch)
        ai = next(i for i, (op, _v) in enumerate(late) if op == IADD)
        ri = next(i for i, (op, _v) in enumerate(late) if op == REMOVE)
        late.insert(ri, late.pop(ai))
        off = [(op, list(v[:-1]) + [v[-1] + 1] if op == IADD else v)
               for op, v in batch]
        led.ok(not items_before_remove(reduce_handin(late))
               and not vacated_refilled(off, load),
               "KNOWN-BAD: a sabotaged tape -- the 0x013E moved after the first "
               "0x0052, or placed one slot off -- FAILS the rule / the cell rule",
               f"{reduce_handin(late)}")
    import livewire
    cap, port, t440, qid = Q440
    capdir = vaultpath.vault_path("captures", "live", cap)
    if not os.path.isdir(capdir):
        led.skip(f"the tape {cap} :{port}", f"no {capdir} (bare machine)")
    else:
        gf = [g for g in livewire.connections(capdir) if f"_{port}-to-" in g]
        m440 = livewire.decode_conn(capdir, gf[0])[1] if len(gf) == 1 else []
        b440 = [(op, v) for t, d, op, v in m440
                if d == "s2c" and abs(t - t440) < 0.0005]
        led.ok(reduce_handin(b440) == Q440_HANDIN
               and items_before_remove(reduce_handin(b440))
               and first(b440, IADD)[-3:] == [652, 8, 0],
               f"TAPE {cap} :{port} {t440} q{qid}: no quest item, the reward "
               "item declared and placed at (8, 0) before the first 0x0052, "
               "and the rule holds", f"{reduce_handin(b440)}")
    c = corpus()
    if c is None:
        led.skip("section 14's corpus half", "no live captures")
        return
    bearing = [(cc, gf, round(t, 4), q, reduce_handin(b))
               for cc, gf, t, q, _o, b in c["handins"]
               if any(k in ITEM_KINDS for k in reduce_handin(b))]
    led.ok(len(bearing) >= 2
           and sum("DEL" in r for *_x, r in bearing) >= 1
           and all(items_before_remove(r) for *_x, r in bearing),
           f"CORPUS: every item-bearing hand-in ({len(bearing)}, floor 2 -- q62 "
           f"and q440; {sum('DEL' in r for *_x, r in bearing)} with a 0x014D, "
           "floor 1) takes and grants BEFORE its first 0x0052",
           f"{[(cc, t, q, r) for cc, _g, t, q, r in bearing if not items_before_remove(r)]}")


# ---------------------------------------------------------------- RANGERLOOP-F6
def grant_kinds(sid, held=(), known=(), store=None, gate=True):
    """grant_skill(sid) on an empty bar, the account holding `held` (laid
    into authsrv.UNLOCKED), this connection `known`, an optional store, the
    gate flag `gate`; -> (reduced kinds, state). Everything restored."""
    import contextlib
    import io
    saved = (authsrv.UNLOCKED, authsrv.ACCOUNT_UNLOCK_GATE,
             list(authsrv.SKILLBAR))
    authsrv.UNLOCKED = account_words(held)
    authsrv.ACCOUNT_UNLOCK_GATE = gate
    authsrv.SKILLBAR[:] = [0] * authsrv.SKILLBAR_SLOTS
    sent, send = collect()
    st = fresh_state(skills_known=set(known))
    if store is not None:
        st["charstore_game"] = store
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.grant_skill(send, st, sid, 0)
    finally:
        authsrv.UNLOCKED, authsrv.ACCOUNT_UNLOCK_GATE = saved[:2]
        authsrv.SKILLBAR[:] = saved[2]
    return reduce_batch(sent), st


def toast_iff_outside(results, held):
    """The tape's rule, 19 of 19: every grant carries its 0x00DC, and a
    0x001C exactly when the skill is outside the account's library. Vacuous
    unless both sides are exercised: False."""
    ins = [s for s in results if s in held]
    outs = [s for s in results if s not in held]
    if not ins or not outs:
        return False
    return all(f"SKC:{s}" in k and (f"SKU:{s}" in k) == (s not in held)
               for s, k in results.items())


class _AcctStore:
    """A charstore stand-in for grant_skill: an account list (None = never
    authored, the --unlocks flag answers) and no-op mutators."""

    def __init__(self, acct):
        self.acct = acct

    def account_unlocked_skills(self):
        return None if self.acct is None else list(self.acct)

    def learn_character_skill(self, uuid_hex, skill_id, seed=None):
        return True

    def unlock_account_skill(self, skill_id, seed=None):
        return False


def section_15():
    print("\n15. RANGERLOOP-F6: OURS -- a granted skill's 0x001C iff it is "
          "outside the ACCOUNT's library")
    held = {2, 382}
    sweep = (1, 2, 382, 384, 394)
    res = {s: grant_kinds(s, held=held)[0] for s in sweep}
    led.ok(toast_iff_outside(res, held)
           and res[2] == ["SKC:2", "SKB:0:2"]
           and res[384] == ["SKC:384", "SKB:0:384", "SKU:384"],
           "grant_skill with the account holding {2, 382} (authsrv.UNLOCKED, "
           "the --unlocks bitmap the load's 0x001D sends): 2 and 382 send "
           "0x00DC + 0x00D9 and NO 0x001C; 1, 384 and 394 add the 0x001C",
           f"{res}")
    k_known, _ = grant_kinds(384, held=(), known={384})
    k_new, st_new = grant_kinds(394, held=(), known={384})
    led.ok(k_known == ["SKC:384", "SKB:0:384"]
           and k_new == ["SKC:394", "SKB:0:394", "SKU:394"]
           and st_new["skills_known"] == {384, 394},
           "a skill this connection granted earlier (skills_known) is held: "
           "no second 0x001C; one new to both still toasts, and joins "
           "skills_known", f"{k_known} {k_new}")
    s_hold, _ = grant_kinds(384, held={2}, store=_AcctStore([384]))
    s_flag, _ = grant_kinds(2, held={2}, store=_AcctStore([384]))
    s_none, _ = grant_kinds(2, held={2}, store=_AcctStore(None))
    led.ok(s_hold == ["SKC:384", "SKB:0:384"]
           and s_flag == ["SKC:2", "SKB:0:2", "SKU:2"]
           and s_none == ["SKC:2", "SKB:0:2"],
           "under --persist a STORED account list is the library (384 held, "
           "2 -- set only in the flag's bitmap -- new), and a store with NO "
           "list falls back to the flag's bitmap (2 held), as the load's "
           "0x001D does (resolve_library)", f"{s_hold} {s_flag} {s_none}")
    words = [0] * len(authsrv.UNLOCKED)
    past = authsrv.SKILL_TABLE_ROWS
    for s in (382, past):
        words[s // 32] |= 1 << (s % 32)
    saved = authsrv.UNLOCKED
    authsrv.UNLOCKED = words
    try:
        got = authsrv.account_skills_held(fresh_state(skills_known={7}))
    finally:
        authsrv.UNLOCKED = saved
    led.ok(got == {382, 7},
           f"account_skills_held: the flag's bitmap bounded by the served "
           f"table (a bit at {past} dropped, as the seed is) plus "
           f"skills_known", f"{sorted(got)}")
    # KNOWN-BAD: the pre-F6 gate -- the empty per-connection set.
    bad = {s: grant_kinds(s, held=held, gate=False)[0] for s in sweep}
    led.ok(all(f"SKU:{s}" in k for s, k in bad.items())
           and not toast_iff_outside(bad, held),
           "KNOWN-BAD arm (--no-account-unlock-gate): every first grant "
           "toasts, 2 and 382 included -- RANGERLOOP-F6's toast -- and the "
           "rule goes RED", f"{bad}")
    led.ok(not toast_iff_outside({2: ["SKC:2", "SKB:0:2"]}, held)
           and not toast_iff_outside({2: ["SKC:2", "SKB:0:2", "SKU:2"],
                                      384: ["SKC:384", "SKB:0:384", "SKU:384"]},
                                     held)
           and not toast_iff_outside({2: ["SKB:0:2"],
                                      384: ["SKC:384", "SKU:384"]}, held),
           "VACUITY: the rule refuses one side unexercised, a held skill's "
           "toast, and a grant without its 0x00DC")
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.no_account_unlock_gate:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--no-account-unlock-gate"]).no_account_unlock_gate
           and not ap.parse_args([]).no_account_unlock_gate
           and authsrv.ACCOUNT_UNLOCK_GATE is True
           and "global ACCOUNT_UNLOCK_GATE\n" in window
           and "ACCOUNT_UNLOCK_GATE = False\n" in window,
           "--no-account-unlock-gate parses, the default gates on the account, "
           "and main() sets ACCOUNT_UNLOCK_GATE = False under it",
           f"window found={at >= 0}")


def library_join(libs, learns, unlocks):
    """Every 0x00DC joined to the account library IN FORCE at it: the last
    0x001D before it on the corpus's clock (capture, then t), plus every
    0x001C after that load and before this batch. -> [(capture, port, t,
    skill, toasted, by_load, by_unlock, lib_at)] -- toasted = a 0x001C for
    the skill in the same batch; lib_at None when no 0x001D precedes it."""
    ev = ([(c, t, 0, "LIB", ids, p) for c, p, t, ids in libs]
          + [(c, t, 1, "LEARN", s, p) for c, p, t, s in learns]
          + [(c, t, 2, "UNL", s, p) for c, p, t, s in unlocks])
    ev.sort(key=lambda e: (e[0], e[1], e[2]))
    toasts = {(c, p, t, s) for c, p, t, s in unlocks}
    lib, since, at, out = None, set(), None, []
    for cap, t, _o, kind, x, port in ev:
        if kind == "LIB":
            lib, since, at = set(x), set(), (cap, port, t)
        elif kind == "UNL":
            since.add(x)
        else:
            out.append((cap, port, t, x, (cap, port, t, x) in toasts,
                        lib is not None and x in lib,
                        x in since and not (lib is not None and x in lib), at))
    return out


def library_growth(libs, unlocks):
    """(drops, carried): every 0x001D against the previous one plus the
    0x001C since -- `drops` the loads that lost an id; `carried` [(skill,
    in the next load?)] for each 0x001C that a later load follows."""
    ev = sorted([(c, t, 0, ids) for c, _p, t, ids in libs]
                + [(c, t, 1, s) for c, _p, t, s in unlocks],
                key=lambda e: (e[0], e[1], e[2]))
    prev, since, drops, carried, pending = None, set(), [], [], []
    for cap, t, kind, x in ev:
        if kind == 1:
            since.add(x)
            pending.append(x)
            continue
        if prev is not None and not (prev - since) <= x:
            drops.append((cap, t, sorted(prev - x)))
        carried += [(s, s in x) for s in pending]
        prev, since, pending = set(x), set(), []
    return drops, carried


def section_16():
    print("\n16. RANGERLOOP-F6: the live CORPUS -- every retail 0x00DC against "
          "the account library in force")
    c = corpus()
    if c is None:
        led.skip("section 16, the live corpus", "no live captures")
        return
    joined = library_join(c["libs"], c["learns"], c["unlocks"])
    unjoined = [j[:4] for j in joined if j[7] is None]
    wrong = [j[:7] for j in joined
             if j[4] == (j[5] or j[6])]          # toasted a held one, or not a new one
    outside = [j for j in joined if not (j[5] or j[6])]
    by_load = [j for j in joined if j[5]]
    by_unl = [j[:4] for j in joined if j[6]]
    led.ok(len(joined) >= 19 and not unjoined and not wrong
           and len(outside) >= 7 and len(by_load) >= 11
           and ("20260929T150923", "53756", 1191.0277, 384) in by_unl,
           f"CORPUS: {len(joined)} retail 0x00DC (floor 19), each joined to the "
           f"library in force -- 0x001C on {len(outside)} outside it (floor 7) "
           f"and on none of {len(by_load) + len(by_unl)} inside it ({len(by_load)} "
           f"in the load's 0x001D, floor 11; {by_unl} by an earlier 0x001C on the "
           f"same clock)", f"unjoined {unjoined} wrong {wrong}")
    drops, carried = library_growth(c["libs"], c["unlocks"])
    led.ok(len(c["libs"]) >= 38 and not drops and len(carried) >= 6
           and all(ok for _s, ok in carried),
           f"CORPUS: the account library only grows -- {len(c['libs'])} 0x001D "
           f"(floor 38), none drops an id -- and every skill a 0x001C unlocked "
           f"is in the next load ({len(carried)} of {len(carried)}, floor 6): "
           f"0x001C is the ACCOUNT's unlock", f"drops {drops} {carried}")
    # KNOWN-BAD: the pre-F6 rule on the same events -- a toast for any skill
    # not granted earlier on the same CONNECTION.
    seen, agree = {}, 0
    for cap, port, t, s, toasted, _bl, _bu, _at in sorted(joined, key=lambda j: (j[0], j[2])):
        mine = seen.setdefault((cap, port), set())
        agree += toasted == (s not in mine)
        mine.add(s)
    led.ok(len(joined) - agree >= 12,
           f"KNOWN-BAD: the per-connection rule (--no-account-unlock-gate) "
           f"predicts a toast on every first grant and MISSES "
           f"{len(joined) - agree} of {len(joined)} (floor 12)", f"agree {agree}")
    sab = [u for u in c["unlocks"]
           if (u[0], u[1], u[2], u[3]) != ("20260929T150923", "56064", 921.1613, 384)]
    sjoin = library_join(c["libs"], c["learns"], sab)
    sbad = [j[:5] for j in sjoin if j[4] == (j[5] or j[6])]
    led.ok(len(sab) == len(c["unlocks"]) - 1 and sbad,
           "KNOWN-BAD: a sabotaged tape (q75's 0x001C for 384 dropped) FAILS "
           "the join", f"{sbad}")


# ---------------------------------------------------------------- RANGERLOOP-F5
def region_first(v):
    """The tape's rule for one 0x0049 / 0x0050, 137 of 137: s1 is ONE code
    unit and differs from s2. Read from the END ([.., s1, s2, s3, home]),
    so the tape's header field and our bare list both fit."""
    s1, s2 = v[-4], v[-3]
    return len(s1) == 1 and s1 != s2


def section_17():
    print("\n17. RANGERLOOP-F5: OURS -- the region in 0x0049 / 0x0050's first "
          "string slot, the name in the other two")
    import questdefs
    rows = questdefs.load()
    row = rows[ERRAND]
    nm = questdefs.enc_string(row["enc_name"])
    reg = questdefs.enc_string(row["enc_region"])
    led.ok(questdefs.log_strings(row) == (reg, nm, nm) == (chr(0x3D64), nm, nm)
           and questdefs.log_strings(row, region=False) == (nm, nm, nm),
           "questdefs.log_strings: (enc_region, name, name) -- s1 0x3D64 -- and "
           "(name, name, name) with region=False", f"{questdefs.log_strings(row)}")
    rows0 = rows_with({ERRAND: {"quest_log_flags": 0}})
    acc, rep = drive(rows0, [("accept", ERRAND, 148, {}),
                             ("replay", [ERRAND], 168, {})])
    add, re_ = first(acc, ACCEPT), first(rep, REPLAY)
    led.ok(add is not None and add[5:8] == [reg, nm, nm] and add[4] == 0
           and re_ == [ERRAND, 0, reg, nm, nm, 148],
           "BOTH send sites: accept_quest's 0x0049 and _replay_quests' 0x0050 "
           "for a flags-0 errand carry [region, name, name]", f"{add} {re_}")
    led.ok(region_first(add) and region_first(re_),
           "and the tape's rule (region_first) holds on both", f"{add[5:8]}")
    b_acc, b_rep = drive(rows0, [("accept", ERRAND, 148, {}),
                                 ("replay", [ERRAND], 168, {})],
                         QUEST_REGION_SLOT=False)
    b_add, b_re = first(b_acc, ACCEPT), first(b_rep, REPLAY)
    led.ok(b_add[5:8] == [nm, nm, nm] and b_re == [ERRAND, 0, nm, nm, nm, 148]
           and not region_first(b_add) and not region_first(b_re),
           "KNOWN-BAD arm (--no-quest-region): the name in all three slots at "
           "both sites -- every run before F5 -- and the rule goes RED",
           f"{b_add[5:8]} {b_re}")
    bare = dict(row)
    bare.pop("enc_region")
    rows_n = dict(rows0)
    rows_n[ERRAND] = dict(bare, quest_log_flags=0)
    n_acc, = drive(rows_n, [("accept", ERRAND, 148, {})])
    n_add = first(n_acc, ACCEPT)
    led.ok(questdefs.log_strings(bare) == (nm, nm, nm)
           and n_add[5:8] == [nm, nm, nm] and not region_first(n_add),
           "a row with NO enc_region sends the name in s1 under either arm "
           "(the pre-F5 shape, and red under the rule) -- the column is what "
           "carries the fix", f"{n_add[5:8]}")
    led.ok(region_first([1, 0, "㵤", "ab", "ab", 148])
           and not region_first([1, 0, "ab", "ab", "ab", 148])
           and not region_first([1, 0, "㵤ā", "ab", "ab", 148])
           and not region_first([1, 0, "ab", "ab", "cd", 148]),
           "VACUITY: the rule refuses s1 == s2, a two-unit s1, and the name "
           "in s1 with only s3 differing")
    bad = [[0x41], [0x8103], [0x3D64, 0x0CC8], [], 0x3D64, [True], ["x"],
           [0x10000], [0x00FF], (0x3D64, 1)]
    refused = []
    for v in bad:
        try:
            questdefs.region_units({"enc_region": v})
        except ValueError:
            refused.append(v)
    led.ok(refused == bad and questdefs.region_units({}) is None
           and questdefs.region_units({"enc_region": [0x3D64]}) == [0x3D64]
           and questdefs.region_units({"enc_region": (0x0100,)}) == [0x0100]
           and questdefs.region_units({"enc_region": [0x7FFF]}) == [0x7FFF],
           "questdefs.region_units: absent is None; one unit 0x0100..0x7FFF "
           "passes; a marker (0x41, 0xFF), a continuation word (0x8103), two "
           "units, none, a bare int, a bool, a str and past a u16 are REFUSED",
           f"refused {len(refused)} of {len(bad)}")

    class _World:
        def rows(self, kind):
            return ({"q": {"quest_id": 7, "enc_region": [0x8103, 0x0CC8]}}
                    if kind == "quest" else {})
    try:
        questdefs.load(_World())
        load_msg = ""
    except ValueError as exc:
        load_msg = str(exc)
    led.ok("'q'" in load_msg and "enc_region" in load_msg
           and all(r.get("enc_region") == [0x3D64] for r in rows.values())
           and len(rows) >= 2,
           "questdefs.load refuses a two-unit enc_region at STARTUP, naming the "
           "row; every shipped row carries [0x3D64]", load_msg)
    ap = serverargs.build_parser(
        doc="", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
        GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
        TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL,
        PROF_WARRIOR=authsrv.PROF_WARRIOR, VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    with open(authsrv.__file__, encoding="utf-8") as fh:
        src = fh.read()
    at = src.find("    if a.no_quest_region:\n")
    window = src[at:at + 200] if at >= 0 else ""
    led.ok(ap.parse_args(["--no-quest-region"]).no_quest_region
           and not ap.parse_args([]).no_quest_region
           and authsrv.QUEST_REGION_SLOT is True
           and "global QUEST_REGION_SLOT\n" in window
           and "QUEST_REGION_SLOT = False\n" in window,
           "--no-quest-region parses, the default sends the region, and main() "
           "sets QUEST_REGION_SLOT = False under it", f"window found={at >= 0}")


# The static read (build 38797, the pinned client), re-read as bytes by the
# stdlib PE reader: (VA, bytes, what the instruction is). OBSERVED with
# codescan --dis / --xrefs; studies/quests/FINDINGS.md §13 has the chain.
F5_SITES = [
    (0x0091DB9D, "8d421c50", "0x0049 dispatcher: lea eax, [edx+0x1c]; push eax -- s1 as the handler's [ebp+0x18]"),
    (0x0080F0E2, "ff7518", "0x0049 handler 0x0080F0A0: push [ebp+0x18] (s1)"),
    (0x0080F10E, "894608", "...mov [esi+8], eax -- s1 into record+0x08"),
    (0x0080F135, "ff751c", "...push [ebp+0x1c] (s2)"),
    (0x0080F161, "89460c", "...mov [esi+0xc], eax -- s2 into record+0x0C"),
    (0x0091DC81, "8d410c50", "0x0050 dispatcher: lea eax, [ecx+0xc]; push eax -- s1 as [ebp+0x10]"),
    (0x0080F4CB, "ff7510", "0x0050 handler 0x0080F470: push [ebp+0x10] (s1)"),
    (0x0080F4FA, "894608", "...mov [esi+8], eax -- s1 into record+0x08"),
    (0x0080DB8B, "8b4608", "0x0080DB40: mov eax, [esi+8] -- out[0] = record+0x08"),
    (0x0080DBB1, "8b4604894708", "...mov eax, [esi+4]; mov [edi+8], eax -- out[2] = the flags"),
    (0x0057DC70, "8d45f450ff7604e8", "heading 0x0057DC60: lea eax, [ebp-0xc]; push eax; push [esi+4]; call 0x0080DB40"),
    (0x0057DCD2, "be02000000a8407505be03000000", "...sort code 2 if flags & 0x40, else 3"),
    (0x0057DDA8, "13dd570046dd57005bdd570077dd5700", "...jump table: arms 0x57DD13, 0x57DD46, 0x57DD5B, 0x57DD77"),
    (0x0057DD46, "6864040000e8", "arm 1: push 0x464 (1124), no argument"),
    (0x0057DD77, "6a00ff75f46a0a6865040000e8", "arm 3: push 0; push [ebp-0xc]; push 0xa; push 0x465 (1125); call"),
]


def section_18():
    print("\n18. RANGERLOOP-F5: the live CORPUS -- every retail 0x0049 / 0x0050's "
          "first slot -- and the static read's bytes")
    import questdefs
    c = corpus()
    if c is None:
        led.skip("section 18's corpus half", "no live captures")
    else:
        rows = ([(cc, p, t, v) for cc, p, t, v, _m, _b in c["accepts"]]
                + [(cc, p, t, v) for cc, p, t, v, _m in c["replays"]])
        units = [(cc, p, t, v[1], v[-1], [[ord(ch) for ch in s] for s in v[-4:-1]])
                 for cc, p, t, v in rows]
        bad = [(cc, p, t, q) for cc, p, t, v in rows
               for q in [v[1]] if not region_first(v)]
        by_home = {}
        for *_x, home, s in units:
            by_home.setdefault(home, set()).add(tuple(s[0]))
        many = {h: sorted(v) for h, v in by_home.items() if len(v) > 1}
        pre = [s for *_x, home, s in units if home in (146, 148, 160)]
        led.ok(len(rows) >= 137 and not bad and not many
               and len(pre) >= 105 and all(s[0] == [0x3D64] for s in pre),
               f"CORPUS: {len(rows)} quest-log rows (floor 137): s1 is ONE unit "
               f"and differs from s2 on every one, and a function of the home "
               f"map ({len(by_home)} homes, one word each); the {len(pre)} rows "
               f"homed on 146 / 148 / 160 (floor 105) all carry 0x3D64",
               f"bad {bad[:5]} many {many}")
        shipped = questdefs.load()
        word148 = by_home.get(148)
        led.ok(word148 is not None and len(word148) == 1
               and all([tuple(r["enc_region"])] == sorted(word148)
                       for r in shipped.values()),
               "the shipped rows' enc_region EQUALS the corpus's s1 for home 148 "
               "-- their giver's map (content/world.toml errand_giver)",
               f"{word148}")
        ok_s1, ok_s2 = 0, 0
        for *_x, s in units:
            try:
                questdefs.region_units({"enc_region": s[0]})
                ok_s1 += 1
            except ValueError:
                pass
            try:
                questdefs.region_units({"enc_region": s[1]})
                ok_s2 += 1
            except ValueError:
                pass
        led.ok(ok_s1 == len(units) and ok_s2 == 0,
               f"the loader's rule is the tape's: region_units accepts all "
               f"{len(units)} retail s1 and refuses every retail s2 (4-5 units)",
               f"s1 accepted {ok_s1}, s2 accepted {ok_s2}")
        sab = [list(v[:-4]) + [v[-3]] + list(v[-3:])
               for _cc, _p, _t, v in rows[:5]]
        led.ok(sab and not any(region_first(v) for v in sab),
               "KNOWN-BAD: retail rows sabotaged to carry the name in s1 FAIL "
               "the rule", f"{len(sab)}")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "clientscan"))
    import framebus
    exe = vaultpath.vault_path("client", "2026-07-29_221c13772c7a", "Gw.exe")
    if not os.path.isdir(os.path.dirname(exe)):
        led.skip("section 18's static half", f"no pinned client at {exe}")
        return
    im = framebus.Image(exe)

    def at(va, n):
        o = im.offset(va)
        return im.blob[o:o + n].hex()
    miss = [(hex(va), at(va, len(b) // 2), b) for va, b, _w in F5_SITES
            if at(va, len(b) // 2) != b]
    led.ok(im.identity[0] == 38797 and not miss,
           f"STATIC, build 38797: all {len(F5_SITES)} sites of the chain read "
           "as recorded -- the 0x0049 / 0x0050 dispatchers hand s1 to the "
           "handlers, which store it at record+0x08; 0x0080DB40 returns it and "
           "the flags; the heading's arm 3 (flags with none of 0x10 / 0x20 / "
           "0x40) formats string 1125 with it", f"{im.identity} {miss}")
    arm2 = at(0x0057DD5B, 13)
    led.ok(arm2 != dict((va, b) for va, b, _w in F5_SITES)[0x0057DD77]
           and arm2.startswith("6a00ff75f46a0a68") and arm2[16:24] == "78160100",
           "CONTROL: arm 2 (0x0057DD5B, flags & 0x40) is the same shape with "
           "id 0x11678, NOT 1125 -- the arm is what names the heading string",
           arm2)


def main():
    section_1()
    section_2()
    section_3()
    section_4()
    section_5()
    section_6()
    section_7()
    section_8()
    section_9()
    section_10()
    section_11()
    section_12()
    section_13()
    section_14()
    section_15()
    section_16()
    section_17()
    section_18()
    return led.verdict()


if __name__ == "__main__":
    sys.exit(main())
