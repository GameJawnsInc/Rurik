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

# Floor 9 from the bare-machine green run (RURIK_VAULT at an empty dir): §1's
# nine checks. §2 adds 15 with the four captures present (24) and declares one
# LEDGER.skip per absent capture. Set from the run, never above it.
led = checks.Ledger("quest accept and hand-in shapes (QUESTFLOW)", floor=9)

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


def main():
    section_1()
    section_2()
    return led.verdict()


if __name__ == "__main__":
    sys.exit(main())
