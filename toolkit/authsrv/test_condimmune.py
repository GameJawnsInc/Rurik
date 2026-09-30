"""test_condimmune -- a NON-FLESHY creature takes no Bleeding, Disease or Poison, and the
player who inflicted it is told #1957 (RANGERPRE-S14, the IMMUNE item's first half,
2026-09-29).

    python toolkit/authsrv/test_condimmune.py

WHAT RETAIL SENDS (OBSERVED, Bleeding, n = 1). On the Reforged capture 20260929T150923,
connection :53756 (build 38888, observer 9), the player's Sever Artery (382) completes on
agent 22 -- definition 1414, model file 17253 -- at t=1057.415, and behind the damage word
the batch is exactly 0x005D #1957 (target_immune_bleeding), 0x005E [1, 7], 0x00E3: no
[6, 22, 23], no 0x00F1, no [44] -- nothing names 22 again until its death word. The same
skill on file 141274 draws [6, T, 23], 0x00F1 [T, 3], [44, T, -0.09375], 3 of 3. Gash (384)
on 22 at t=1058.906 is a plain hit (its requires_condition gate reads the target's LIVE
conditions and an immune target holds none), where on a bleeding foe it sets 0x23. WIKI
(GWW "Fleshy" rev 2611793): non-fleshy creatures are immune to Bleeding, Disease and
Poison. Ours put Bleeding on everything, sent no sentence, and Gash fired its Deep Wound.

WHO IS NON-FLESHY is content: content/npcs.toml's `creature_trait.file_17253` (fleshy =
false), keyed by model file, and `npc.stone_elemental` -- definition 1414 as npcdefs.py
compiles it -- so a spawn can name the creature. Section 1 re-derives both rows from the
bytes (npcdefs is re-run and must agree field for field). Section 2 is the server,
offline, against section 1's literals: the real content, the real apply_condition, and the
player's own press -> cast_tick for Sever Artery and Gash end to end. Section 3 is the
known-bad arm, --no-condition-immunity, which must fail the literals retail passes.

Section 1 needs the vault (declared a skip on a machine with no captures/live; a vault that
has captures but not this one dies loudly in require_dir). Sections 2 and 3 need none.
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
import chatdefs                                                # noqa: E402
import codedstr                                                # noqa: E402
import content                                                 # noqa: E402
import effects                                                 # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-29 on a machine with NO captures (RURIK_VAULT at an
# empty directory; section 1 a declared skip): 11. With the vault: 18.
LEDGER = checks.Ledger("condition immunity", floor=11)
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
OP_CORE, OP_SERVER, OP_DONE = 0x005D, 0x005E, 0x00E3
OP_AURA, OP_STATUS, OP_REGEN, OP_WORD = 0x009F, 0x00F1, 0x00A2, 0x00A3
BLEED, BURN, CRIPPLE, DEEP, DISEASE, POISON, WEAK = 478, 480, 481, 482, 483, 484, 486
SEVER, GASH = 382, 384
IMMUNE_FILE, FLESHY_FILE = 17253, 141274           # definitions 1414 and 1437 on the tape
REFORGED = ("20260929T150923", "10.0.0.210:53756->34.196.135.145:80")
OBSERVER = 9
BATCH_S = 0.005

# ---- retail's literals (OBSERVED; section 1 re-derives every one from the bytes) ------
# What follows the inflicter's damage word in the completion batch, through its 0x00E3.
IMMUNE_AFTER = [("SENTENCE", 1957), ("CHANNEL", (1, 7)), ("DONE", SEVER)]
FLESHY_AFTER = [("ADD", 23), ("STATUS", 0x03), ("REGEN", 0xBDC00000), ("DONE", SEVER)]
GASH_PLAIN = [("DONE", GASH)]
GASH_BLEEDING = [("STATUS", 0x23), ("REGEN", 0xBDEC4EC5), ("DONE", GASH)]   # -6 / 52
SEVER_TAPE = [(1057.415, 22, IMMUNE_AFTER), (1113.410, 30, FLESHY_AFTER),
              (1132.708, 27, FLESHY_AFTER), (1140.683, 27, FLESHY_AFTER)]
# 27's Bleeding expired at 1137.703, 0.32 s before this Gash landed: plain.
GASH_TAPE = [(1058.906, 22, GASH_PLAIN), (1116.049, 30, GASH_BLEEDING),
             (1138.025, 27, GASH_PLAIN)]
DEFINITION = 1414
AGENT_22_MODEL_WORD = 0x20000586                   # 0x0020's tagged model: class 2, 1414


def token(op, fields, target):
    """What one message contributes to a completion's tail on `target`, or None. `fields`
    are the message's values without the tape's header byte (what our send carries).
    A sentence and its channel belong to whoever reads the panel, so they are not
    filtered by target."""
    if op == OP_CORE:
        return ("SENTENCE", codedstr.decode_id([ord(c) for c in fields[0]])[0])
    if op == OP_SERVER:
        return ("CHANNEL", tuple(fields[:2]))
    if op == OP_DONE:
        return ("DONE", fields[1])
    if op == OP_AURA and fields[0] in (agents.PROP_AURA_ON, agents.PROP_AURA_OFF) \
            and fields[1] == target:
        return ("ADD" if fields[0] == agents.PROP_AURA_ON else "REMOVE", fields[2])
    if op == OP_STATUS and fields[0] == target:
        return ("STATUS", fields[1])
    if op == OP_REGEN and fields[0] == agents.GV_CHANGE_HEALTH_REGEN and fields[1] == target:
        return ("REGEN", fields[2])
    return None


def tokens(msgs, target):
    return [x for x in (token(op, v, target) for op, v in msgs) if x]


def after_word(msgs, inflicter):
    """(target, the tokens behind the inflicter's damage word) in one batch, or None."""
    k = next((n for n, (op, f) in enumerate(msgs)
              if op == OP_WORD and f[0] in (16, 17) and f[2] == inflicter), None)
    if k is None:
        return None
    tgt = msgs[k][1][1]
    return tgt, tokens(msgs[k + 1:], tgt)


# ---------------------------------------------------------------------------------------
def section_tape():
    print("\n1. retail's bytes: the immune completion, the fleshy control, Gash, and the rows")
    try:
        vaultpath.require_dir("captures", "live", why="the condition-immunity witness")
    except SystemExit as exc:
        LEDGER.skip("1. retail's bytes", str(exc).splitlines()[0])
        return
    import bufflog
    import deepwoundjoin
    import npcdefs
    import spellhitjoin
    import tape
    codec = bufflog.Codec()
    stamp, conn = REFORGED
    cap = vaultpath.require_dir("captures", "live", stamp, why="the Reforged capture")
    seq = deepwoundjoin.sequence(cap, conn, codec)
    check(tape.client_version(cap, conn)["build"] == 38888
          and spellhitjoin.observer_of(seq, [])[0] == OBSERVER,
          f"fixture: {stamp} {conn} is build 38888 and its observer is agent {OBSERVER}")

    def batch_of(t):
        return [(op, v[1:]) for _i, tb, op, v in seq if abs(tb - t) <= BATCH_S]

    def completions(skill):
        out = []
        for _i, t, op, v in seq:
            if op == OP_DONE and v[1] == OBSERVER and v[2] == skill:
                hit = after_word(batch_of(t), OBSERVER)
                if hit is not None:
                    out.append((round(t, 3), hit[0], hit[1]))
        return out

    got = completions(SEVER)
    check(got == SEVER_TAPE,
          "1a. every Sever Artery completion behind its damage word: on 22 (file 17253) "
          "#1957, [1, 7], the 0x00E3 and NOTHING naming 22; on the three fleshy foes "
          "[6, T, 23], 0x00F1 [T, 3], [44, T, 0xBDC00000], the 0x00E3", got)
    got = completions(GASH)
    check(got == GASH_TAPE,
          "1b. every Gash completion: plain on the immune 22 (1058.906) and on 27 after its "
          "Bleeding expired (1138.025); 0x00F1 [30, 0x23] + [44, 30, -6/52] on the bleeding "
          "30 (1116.049) -- the gate reads the target's live conditions", got)

    t_sever = SEVER_TAPE[0][0]
    named = [(round(t, 3), tok) for _i, t, op, v in seq if t > t_sever + BATCH_S
             for tok in [token(op, v[1:], 22)] if tok and tok[0] in ("ADD", "STATUS", "REGEN")]
    check(named[:1] == [(1060.488, ("STATUS", 0x10))],
          "1c. after the refused completion nothing names 22 -- no [6], no 0x00F1, no [44] -- "
          "until its death word 0x00F1 [22, 16] at 1060.488", named[:3])

    said = [codedstr.decode_id([ord(c) for c in v[1]])[0] for _i, _t, op, v in seq
            if op == OP_CORE]
    immune = [s for s in said if s in chatdefs.REFUSE_IMMUNE.values()]
    check(immune == [1957],
          "1d. the connection's immunity sentences: #1957 once, #1958 and #1959 never "
          "(NOT FOUND -- they stay RECONSTRUCTION)", immune)

    # 1e. the rows are the bytes: the definition, its file, and the agent that carried it
    declared = [v[1:] for _i, _t, op, v in seq if op == 0x0056 and v[1] == DEFINITION]
    creates = [(round(t, 3), v[2]) for _i, t, op, v in seq if op == 0x0020 and v[1] == 22]
    at_sever = [w for t, w in creates if t <= t_sever][-1:]
    trait = content.load(vault_dir="").rows("creature_trait").get("file_17253") or {}
    check(declared and all(d[1] == IMMUNE_FILE for d in declared)
          and at_sever == [AGENT_22_MODEL_WORD]
          and AGENT_22_MODEL_WORD & npcdefs.DEFINITION_MASK == DEFINITION
          and trait.get("file_id") == IMMUNE_FILE and trait.get("fleshy") is False,
          "1e. 0x0056 declares 1414 on file 17253, the create in effect for 22 at the refusal "
          "is 0x20000586 (1414), and the tracked creature_trait row names that file, "
          "fleshy = false", (declared[:1], creates, dict(trait)))
    defs, _iv = npcdefs.read([cap])
    want = defs[DEFINITION].row()
    row = dict(content.load(vault_dir="").get("npc", "stone_elemental"))
    prov = content.load(vault_dir="").get("npc", "stone_elemental").provenance
    check(row == want and prov.get("build") == npcdefs.capture_build(cap)
          and prov.get("mode") == npcdefs.capture_mode(cap) == "reforged"
          and prov.get("extractor") == "toolkit/authsrv/npcdefs.py"
          and prov.get("capture") == stamp,
          "1f. npc.stone_elemental IS the extractor's row: npcdefs.read over this capture "
          "gives definition 1414 field for field, and the row names the capture, its build "
          "and mode (reforged, from the manifest) and npcdefs.py",
          (row, want, dict(prov)))


# ---------------------------------------------------------------------------------------
def body(file_id, **kw):
    b = {"name": "foe", "dead": False, "died_at": 0.0, "health": 64.0, "max_health": 64.0,
         "last_hit": 0.0, "pos": (50.0, 0.0), "plane": 0, "armor_rating": 3.0,
         "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
         "effects": 0, "attacks_back": False, "skills": (), "skill_ready": [],
         "npc": {"file_id": file_id, "profession": 6, "level": 1}}
    b.update(kw)
    return b


def world(**bodies):
    st = {"agents": {int(k[1:]): v for k, v in bodies.items()}, "pos": (0.0, 0.0),
          "player_health": 140.0}
    authsrv.effect_table(st)
    return st


def collector():
    sent = []
    return sent, lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))


def conditions_on(st, agent_id):
    return sorted(ep["skill"] for ep in authsrv.effect_table(st).on_agent(agent_id))


def land(st, skill, target):
    """The player's own press -> cast_tick, the E5 brought forward (test_agentlife's
    SLICE-H10 recipe): what the completion sent."""
    sent, send = collector()
    authsrv.handle_skill_press([0, skill, 0, target], send, st, 1,
                               authsrv.GAME_CMSG_USE_SKILL)
    for cast in st.get("pending_casts", ()):
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            cast[k] -= 30.0
    for _ in range(3):
        authsrv.cast_tick(send, st, 1)
    return sent


def sword_duel(file_id):
    """Sever Artery then Gash from the slice's sword character on one body of `file_id`:
    (Sever's tokens behind the word, Gash's, the body's conditions after each)."""
    st = world(a22=body(file_id))
    sever = after_word(land(st, SEVER, 22), PLAYER)
    after_sever = conditions_on(st, 22)
    gash = after_word(land(st, GASH, 22), PLAYER)
    return sever, gash, after_sever, conditions_on(st, 22)


def section_server():
    print("\n2. the server against retail's literals (offline, the real content)")
    tracked = content.load(vault_dir="")
    check((tracked.rows("creature_trait").get("file_17253") or {}).get("fleshy") is False
          and agents.creature_fleshy(IMMUNE_FILE) is False
          and agents.creature_fleshy(FLESHY_FILE) is True
          and agents.creature_fleshy(None) is True
          and tracked.get("npc", "stone_elemental")["file_id"] == IMMUNE_FILE,
          "2a. the TRACKED content (vault switched off) carries creature_trait.file_17253 "
          "(fleshy = false) and npc.stone_elemental on that file; creature_fleshy reads it "
          "-- 17253 no, 141274 yes, an unknown or absent file yes")
    st = world(a22=body(IMMUNE_FILE))
    check(authsrv.agent_fleshy(st, PLAYER) and not authsrv.agent_fleshy(st, 22)
          and authsrv.agent_fleshy(world(a22=body(IMMUNE_FILE, npc=None)), 22)
          and authsrv.agent_fleshy(world(a22={"name": "bare"}), 22)
          and authsrv.agent_fleshy(st, 99),
          "2b. agent_fleshy: the player always; a body by its npc's file -- a body whose "
          "npc is None, a body with no npc and an agent id with no row read fleshy")

    # 2c. the apply on the immune body, inflicted by the player
    st = world(a22=body(IMMUNE_FILE), a30=body(FLESHY_FILE, pos=(150.0, 0.0)))
    sent, send = collector()
    ep = authsrv.apply_condition(send, st, 22, BLEED, 5.0, 0, 0, SEVER, by_agent=PLAYER)
    check(ep is None and tokens(sent, 22) == IMMUNE_AFTER[:2]
          and [op for op, _v in sent] == [OP_CORE, OP_SERVER]
          and sent[0][1] == [chatdefs.refusal_body(1957)]
          and conditions_on(st, 22) == [] and not st.get("effect_list_suppressed")
          and st["agents"][22]["effects"] == 0,
          "2c. Bleeding on the non-fleshy 22 by the player: 0x005D #1957 + 0x005E [1, 7] and "
          "nothing else -- no episode, no suppressed 0x0042 counted, no status word, no "
          "rate (retail 1057.415)", [(hex(op), v) for op, v in sent])
    sent.clear()
    ep = authsrv.apply_condition(send, st, 30, BLEED, 5.0, 0, 0, SEVER, by_agent=PLAYER)
    check(ep is not None and tokens(sent, 30) == FLESHY_AFTER[:3]
          and conditions_on(st, 30) == [BLEED],
          "2d. CONTROL, the same apply on the fleshy 30: [6, 30, 23], 0x00F1 [30, 3], "
          "[44, 30, 0xBDC00000] and the episode (retail 1113.410)",
          [(hex(op), v) for op, v in sent])

    # 2e. Disease and Poison: refused too, their sentences RECONSTRUCTION (flag-gated)
    got, flagged = {}, {}
    saved = authsrv.REFUSAL_REASON_IDS
    try:
        for cid in (DISEASE, POISON):
            for flag, book in ((False, got), (True, flagged)):
                authsrv.REFUSAL_REASON_IDS = flag
                s2 = world(a22=body(IMMUNE_FILE))
                sent, send = collector()
                r = authsrv.apply_condition(send, s2, 22, cid, 5.0, 0, 0, 1, by_agent=PLAYER)
                book[cid] = (r, tokens(sent, 22), conditions_on(s2, 22))
    finally:
        authsrv.REFUSAL_REASON_IDS = saved
    check(got == {DISEASE: (None, [], []), POISON: (None, [], [])}
          and flagged == {DISEASE: (None, [("SENTENCE", 1958), ("CHANNEL", (1, 7))], []),
                          POISON: (None, [("SENTENCE", 1959), ("CHANNEL", (1, 7))], [])},
          "2e. Disease and Poison on 22 are refused too (WIKI), in SILENCE by default -- "
          "#1958 / #1959 are on no wire -- and named only under --refusal-reasons",
          (got, flagged))

    # 2f. the rest of the ten land on it; a body or an unknown inflicter hears nothing
    landed = {}
    for cid in (BURN, CRIPPLE, DEEP, WEAK):
        s2 = world(a22=body(IMMUNE_FILE))
        authsrv.apply_condition(collector()[1], s2, 22, cid, 5.0, 0, 0, 1, by_agent=PLAYER)
        landed[cid] = conditions_on(s2, 22)
    quiet = []
    for who in (10, None):
        s2 = world(a22=body(IMMUNE_FILE))
        sent, send = collector()
        r = authsrv.apply_condition(send, s2, 22, BLEED, 5.0, 0, 0, SEVER, by_agent=who)
        quiet.append((who, r, sent, conditions_on(s2, 22)))
    check(landed == {BURN: [BURN], CRIPPLE: [CRIPPLE], DEEP: [DEEP], WEAK: [WEAK]}
          and quiet == [(10, None, [], []), (None, None, [], [])],
          "2f. only the fleshy three are refused (Burning, Crippled, Deep Wound, Weakness "
          "land on 22); inflicted by a body (10) or by an unnamed site, the refusal is "
          "silent -- the sentence goes to the player alone (UNVERIFIED for a party)",
          (landed, quiet))
    s2 = world()
    authsrv.player_pools(s2)
    ep = authsrv.apply_condition(collector()[1], s2, PLAYER, BLEED, 5.0, 0, 0, SEVER,
                                 by_agent=10)
    check(ep is not None and conditions_on(s2, PLAYER) == [BLEED],
          "2g. the player is fleshy: a foe's Bleeding on the player opens as before")

    # 2h. END TO END: the slice's sword character presses Sever Artery, then Gash
    saved_pc = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.PLAYER_SWING_DAMAGE,
                authsrv.WEAPON_ATTACK_SPEED, authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR,
                agents.PLAYER_LEVEL, agents.PLAYER_HEALTH, agents.PLAYER_ATTRIBUTE_RANKS,
                agents.PLAYER_ATTRIBUTE_POINTS, authsrv.skill_cost)
    try:
        authsrv.apply_party_character(agents.WORLD.get("party", "slice"))
        authsrv.skill_cost = lambda sid: (0, 0)          # the gate, not the price
        if authsrv.skill_condition(SEVER, 3) is None or \
                authsrv.skill_requires_condition(GASH) != BLEED:
            LEDGER.skip("2h / 3b. the sword duel",
                        "the skill rows give Sever Artery no condition or Gash no Bleeding gate")
            return None
        immune = sword_duel(IMMUNE_FILE)
        fleshy = sword_duel(FLESHY_FILE)
        check(immune == ((22, IMMUNE_AFTER), (22, GASH_PLAIN), [], [])
              and fleshy == ((22, FLESHY_AFTER), (22, GASH_BLEEDING), [BLEED], [BLEED, DEEP]),
              "2h. END TO END through the player's press: Sever Artery on the non-fleshy body "
              "is the word, #1957, [1, 7], the 0x00E3 -- retail's 1057.415 verbatim -- and "
              "Gash after it is plain; on the fleshy body Sever is retail's 1113.410 and Gash "
              "retail's 1116.049 (0x23, -6/52) with its Deep Wound", (immune, fleshy))
        saved_ci = authsrv.CONDITION_IMMUNITY
        try:
            authsrv.CONDITION_IMMUNITY = False
            bad = sword_duel(IMMUNE_FILE)
        finally:
            authsrv.CONDITION_IMMUNITY = saved_ci
        return bad
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.PLAYER_SWING_DAMAGE,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR,
         agents.PLAYER_LEVEL, agents.PLAYER_HEALTH, agents.PLAYER_ATTRIBUTE_RANKS,
         agents.PLAYER_ATTRIBUTE_POINTS, authsrv.skill_cost) = saved_pc


# ---------------------------------------------------------------------------------------
def section_known_bad(bad_duel):
    print("\n3. KNOWN-BAD ARM: --no-condition-immunity (every creature fleshy), and the source")
    saved = authsrv.CONDITION_IMMUNITY
    try:
        authsrv.CONDITION_IMMUNITY = False
        st = world(a22=body(IMMUNE_FILE))
        sent, send = collector()
        ep = authsrv.apply_condition(send, st, 22, BLEED, 5.0, 0, 0, SEVER, by_agent=PLAYER)
    finally:
        authsrv.CONDITION_IMMUNITY = saved
    check(ep is not None and tokens(sent, 22) == FLESHY_AFTER[:3]
          and tokens(sent, 22) != IMMUNE_AFTER[:2],
          "3a. with the flag off the non-fleshy 22 bleeds -- [6, 22, 23], 0x00F1 [22, 3], "
          "[44] and no sentence: the pre-S14 server, which retail's 1057.415 refutes",
          [(hex(op), v) for op, v in sent])
    if bad_duel is not None:
        check(bad_duel == ((22, FLESHY_AFTER), (22, GASH_BLEEDING), [BLEED], [BLEED, DEEP]),
              "3b. and end to end the flag-off Sever Artery bleeds the non-fleshy body and "
              "Gash fires its +8 and Deep Wound -- retail's 1058.906 was a plain hit",
              bad_duel)

    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    src = open(authsrv.__file__, encoding="utf-8").read()
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_condition_immunity:", i_main)
    i_ac = src.find("\ndef apply_condition(")
    i_gate = src.find("    if (CONDITION_IMMUNITY and name in chatdefs.REFUSE_IMMUNE\n", i_ac)
    i_table = src.find("    table = effect_table(state)\n", i_ac)
    check(ap.parse_args([]).no_condition_immunity is False
          and ap.parse_args(["--no-condition-immunity"]).no_condition_immunity is True
          and 0 < i_main < i_flip and "CONDITION_IMMUNITY = False" in src[i_flip:i_flip + 120]
          and 0 < i_ac < i_gate < i_table
          and "condition_refused_immune(" in src[i_gate:i_table]
          and chatdefs.REFUSE_IMMUNE == {"Bleeding": 1957, "Disease": 1958, "Poison": 1959}
          and chatdefs.REFUSAL_OBSERVED & set(chatdefs.REFUSE_IMMUNE.values()) == {1957},
          "3c. the source: the flag parses (default off) and main() flips it; the gate sits "
          "in apply_condition AHEAD of the effect table, so a refusal opens nothing; the "
          "sentences are 1957 / 1958 / 1959 and only 1957 is OBSERVED")


def main():
    print("test_condimmune -- non-fleshy creatures refuse Bleeding, Disease and Poison, "
          "and #1957 (RANGERPRE-S14)")
    t0 = time.time()
    section_tape()
    bad = section_server()
    section_known_bad(bad)
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
