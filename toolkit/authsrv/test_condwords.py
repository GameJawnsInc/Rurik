"""test_condwords -- a condition's visual words on its wearer, [6, T, id] at the apply and
[7, T, id] at the close, and the (wearer, buff) aura book they need (RANGERPRE-S13, the
IMMUNE item's 2b half, 2026-09-29).

    python toolkit/authsrv/test_condwords.py

WHAT RETAIL SENDS (OBSERVED). Every FRESH condition apply on the live corpus carries its
own visual id in a 0x009F [6, T, id] behind the 0x0042 and ahead of the wearer's 0x00F1
(effects.CONDITION_EFFECT_IDS: Bleeding 23, Blind 24, Burning 25, Disease 26, Poison 27,
Dazed 28, Weakness and Cracked Armor 29; Crippled and Deep Wound none), and its close
takes it off with [7, T, id] ahead of the 0x00F1. A foe's 0x0042 is never sent (MANTID)
and its [6] still is: on the Reforged capture 20260929T150923 :53756 the player's Sever
Artery lands [6, T, 23], 0x00F1 [T, 3], [44, T, -0.09375] on three bleeding foes, and
the one live expiry is [7, 27, 23], 0x00F1 [27, 0], [44, 27, +0.0]. Ours sent the status
word and the rate alone -- no condition ever reached aura_on.

WHY THE BOOK IS RE-KEYED IN THE SAME CHANGE. auras_by_buff was keyed by the buff id alone,
and a buff id is RECYCLED the moment EffectTable.strip_agent frees it. At a death,
strip_effects runs a hex's payoff (Incendiary Bonds' Burning on the foe beside the corpse)
BETWEEN the strip and the REMOVE loop, so the neighbour's Burning takes the corpse's freed
id; once that Burning carries an aura, the corpse's REMOVE popped the NEIGHBOUR'S record --
[7, 11, 25] went out in place of the corpse's [7, 10, 1] [7, 10, 4]. Section 2g drives that
exact interleaving through the real strip_effects with the payoff stubbed at its seam (the
real payoff needs the vault's skill records; test_skilldamage 11c (d) drives it end to
end with them).

Section 1 reads retail's bytes (declared a skip on a machine with no captures/live; a
vault that has it but lacks one of the four connections dies loudly in require_dir).
Section 2 is the server, offline, against section 1's literals. The immunity half of the
item (non-fleshy creatures, #1957) is RANGERPRE-S14's and is not here.
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
import effects                                                 # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-29 on a machine with NO captures (RURIK_VAULT at an
# empty directory; section 1 a declared skip): 12. With the vault: 19.
LEDGER = checks.Ledger("condition visual words", floor=12)
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
OP_AURA, OP_STATUS, OP_REGEN = 0x009F, 0x00F1, 0x00A2
OP_APPLY, OP_REMOVE, OP_WORD = authsrv.GAME_SMSG_EFFECT_APPLY, authsrv.GAME_SMSG_EFFECT_REMOVE, 0x00A3
BLEED, BLIND, BURN, CRIPPLE, DEEP, DISEASE, POISON, DAZED, WEAK, CRACKED = (
    478, 479, 480, 481, 482, 483, 484, 485, 486, 2077)
EMPATHY = 26                   # content/world.toml skill_effect.26: auras = [1, 4]

# ---- retail's literals (OBSERVED; section 1 re-derives every one from the bytes) ------
RETAIL_IDS = {BLEED: 23, BLIND: 24, BURN: 25, DISEASE: 26, POISON: 27, DAZED: 28,
              WEAK: 29, CRACKED: 29}
RETAIL_NONE = {CRIPPLE, DEEP}
FLESHY_TAIL = [("ADD", 23), ("STATUS", 0x03), ("REGEN", 0xBDC00000)]   # -(3 x 2)/64
EXPIRY_TAIL = [("REMOVE", 23), ("STATUS", 0x00), ("REGEN", 0x00000000)]
REFORGED = ("20260929T150923", "10.0.0.210:53756->34.196.135.145:80")
SEVER = 382
# every Sever Artery completion on the connection: (wire t, target, the target's tail
# behind the damage word). Agent 22 is the non-fleshy creature (IMMUNE-1, S14's witness):
# nothing on it names it.
SEVER_TAILS = [(1057.415, 22, []), (1113.410, 30, FLESHY_TAIL),
               (1132.708, 27, FLESHY_TAIL), (1140.683, 27, FLESHY_TAIL)]
EXPIRIES = [(1137.703, 27, EXPIRY_TAIL)]
# every condition 0x0042 on three connections that between them carry all ten
# conditions, joined to the [6, same agent, x] in its batch; "re" is a re-application
# while the same (agent, condition) is still live by buff.
WITNESS = {
    ("20260821T152147", "10.0.0.210:63150->52.55.104.238:80"): {
        (BLEED, "fresh", (23,)): 1, (BLIND, "fresh", (24,)): 1, (BURN, "fresh", (25,)): 2,
        (CRIPPLE, "fresh", ()): 1, (DISEASE, "fresh", (26,)): 1, (POISON, "fresh", (27,)): 1,
        (DAZED, "fresh", (28,)): 1, (WEAK, "fresh", (29,)): 1},
    ("20260821T155022", "10.0.0.210:59491->3.233.201.47:80"): {
        (DEEP, "fresh", ()): 2, (CRACKED, "fresh", (29,)): 2},
    ("20260817T231139", "10.0.0.210:54071->54.198.7.73:80"): {
        (BURN, "fresh", (25,)): 3, (BURN, "re", ()): 2},
}
BATCH_S = 0.005


def token(op, fields, target):
    """What one message contributes to a condition's tail on `target`, or None. `fields`
    are the message's values without the tape's header byte (what our send carries)."""
    if op == OP_AURA and fields[0] in (agents.PROP_AURA_ON, agents.PROP_AURA_OFF) \
            and fields[1] == target:
        return ("ADD" if fields[0] == agents.PROP_AURA_ON else "REMOVE", fields[2])
    if op == OP_STATUS and fields[0] == target:
        return ("STATUS", fields[1])
    if op == OP_REGEN and fields[0] == agents.GV_CHANGE_HEALTH_REGEN and fields[1] == target:
        return ("REGEN", fields[2])
    return None


def tail(sent, target):
    return [x for x in (token(op, v, target) for op, v in sent) if x]


# ---------------------------------------------------------------------------------------
def section_tape():
    print("\n1. retail's bytes: the Reforged capture's tails, and the ids on three connections")
    try:
        live = vaultpath.require_dir("captures", "live", why="the condition visual words")
    except SystemExit as exc:
        LEDGER.skip("1. retail's bytes", str(exc).splitlines()[0])
        return
    import bufflog
    import deepwoundjoin
    import spellhitjoin
    import tape
    codec = bufflog.Codec()
    stamp, conn = REFORGED
    cap = vaultpath.require_dir("captures", "live", stamp, why="the Reforged capture")
    seq = deepwoundjoin.sequence(cap, conn, codec)
    check(tape.client_version(cap, conn)["build"] == 38888
          and spellhitjoin.observer_of(seq, [])[0] == 9,
          f"fixture: {stamp} {conn} is build 38888 and its observer is agent 9")

    def batch_of(t):
        return [(op, v[1:]) for _i, tb, op, v in seq if abs(tb - t) <= BATCH_S]

    got = []
    for _i, t, op, v in seq:
        if op == 0x00E3 and v[1] == 9 and v[2] == SEVER:
            b = batch_of(t)
            k = next((n for n, (o, f) in enumerate(b)
                      if o == OP_WORD and f[0] in (16, 17) and f[2] == 9), None)
            if k is not None:
                tgt = b[k][1][1]
                got.append((round(t, 3), tgt, tail(b[k + 1:], tgt)))
    check(got == SEVER_TAILS,
          "every Sever Artery completion's tail behind its damage word: [6, T, 23], 0x00F1 "
          "[T, 3], [44, T, 0xBDC00000] on the three bleeding foes (1113.410 / 1132.708 / "
          "1140.683), nothing naming the non-fleshy 22 -- the literals section 2 holds ours to",
          got)
    got = []
    for _i, t, op, v in seq:
        if op == OP_AURA and v[1] == agents.PROP_AURA_OFF and v[3] == 23:
            b = batch_of(t)
            if any(o == OP_STATUS and f[0] == v[2] and f[1] & effects.STATUS_DEAD for o, f in b):
                continue                        # a death batch, not an expiry
            k = b.index((OP_AURA, v[1:]))
            got.append((round(t, 3), v[2], tail(b[k:], v[2])))
    check(got == EXPIRIES,
          "the one live Bleeding expiry: [7, 27, 23], 0x00F1 [27, 0], [44, 27, 0x00000000] "
          "(5.0 s after 1132.708) -- the [7] first", got)

    census, order_ok = {}, True
    for (wstamp, wconn), want in WITNESS.items():
        wcap = vaultpath.require_dir("captures", "live", wstamp, why="a condition-id witness")
        wseq = deepwoundjoin.sequence(wcap, wconn, codec)
        live_eps, rows = {}, {}
        for idx, (_i, t, op, v) in enumerate(wseq):
            if op == OP_APPLY:
                agent, skill, buff = v[1], v[2], v[4]
                again = (agent, skill) in live_eps.values()
                live_eps[buff] = (agent, skill)
                if skill not in effects.CONDITION_SKILLS:
                    continue
                six = [(k, w[3][3]) for k, w in enumerate(wseq)
                       if abs(w[1] - t) <= BATCH_S and w[2] == OP_AURA
                       and w[3][1] == agents.PROP_AURA_ON and w[3][2] == agent]
                order_ok = order_ok and all(k > idx for k, _x in six)
                key = (skill, "re" if again else "fresh", tuple(x for _k, x in six))
                rows[key] = rows.get(key, 0) + 1
            elif op == OP_REMOVE:
                live_eps.pop(v[2], None)
        census[wstamp] = rows
        check(rows == want,
              f"{wstamp} {wconn.split('->')[0]}: every condition 0x0042 joined to its [6] "
              f"exactly as pinned", rows)
    fresh = {}
    for rows in census.values():
        for (skill, kind, ids), _n in rows.items():
            if kind == "fresh":
                fresh.setdefault(skill, set()).add(ids)
    derived = {s: next(iter(v))[0] for s, v in fresh.items() if len(v) == 1 and next(iter(v))}
    check(order_ok and derived == RETAIL_IDS
          and {s for s, v in fresh.items() if v == {()}} == RETAIL_NONE
          and set(fresh) == set(effects.CONDITION_SKILLS)
          and all(ids == () for rows in census.values() for (_s, kind, ids) in rows if kind == "re"),
          "DERIVED from the bytes: every fresh apply of each of the ten conditions carries ONE id "
          "(the 0x0042 first) and they are RETAIL_IDS; Crippled and Deep Wound carry none; a "
          "re-application while live carries none (Burning x2)", (derived, order_ok))


# ---------------------------------------------------------------------------------------
def foe(**kw):
    b = {"name": "foe", "dead": False, "died_at": 0.0, "health": 64.0, "max_health": 64.0,
         "last_hit": 0.0, "pos": (0.0, 0.0), "plane": 0, "armor_rating": 3.0,
         "allegiance": agents.ALLEGIANCE_HOSTILE, "effects": 0}
    b.update(kw)
    return b


def world(*ids):
    st = {"agents": {a: foe(pos=(100.0 * n, 0.0)) for n, a in enumerate(ids)},
          "pos": (0.0, 0.0), "player_health": 100.0}
    authsrv.effect_table(st)
    return st


def collector():
    sent = []
    return sent, lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))


def expire_all(st, send):
    for ep in authsrv.effect_table(st).live.values():
        ep["expires_at"] = time.time() - 0.01
    authsrv.effect_tick(send, st, 0)


def bleed_on_foe():
    """Sever Artery's Bleeding (5.0 s) on a foe at 64, then its expiry: (apply, expiry)."""
    st = world(30)
    sent, send = collector()
    authsrv.apply_condition(send, st, 30, BLEED, 5.0, 0, 0, SEVER, by_agent=PLAYER)
    applied = list(sent)
    st["suppressed_at_apply"] = st.get("effect_list_suppressed")
    sent.clear()
    expire_all(st, send)
    return applied, list(sent), st


def section_server():
    print("\n2. the server against retail's literals (offline)")
    applied, expired, st = bleed_on_foe()
    check(tail(applied, 30) == FLESHY_TAIL
          and [op for op, _v in applied] == [OP_AURA, OP_STATUS, OP_REGEN]
          and st["suppressed_at_apply"] == 1,
          "2a. Bleeding on a foe at 64: [6, 30, 23], 0x00F1 [30, 3], [44, 30, 0xBDC00000] -- "
          "retail's tail, and nothing else (its 0x0042 counted as suppressed, MANTID)",
          [(hex(op), v) for op, v in applied])
    check(tail(expired, 30) == EXPIRY_TAIL
          and [op for op, _v in expired] == [OP_AURA, OP_STATUS, OP_REGEN],
          "2b. its expiry: [7, 30, 23], 0x00F1 [30, 0], [44, 30, 0x00000000] -- retail's, "
          "the [7] first", [(hex(op), v) for op, v in expired])

    # 2c. every condition, on a fresh foe and on the player
    on_foe, on_me, order = {}, {}, []
    for cid in effects.CONDITION_SKILLS:
        for who, book in ((30, on_foe), (PLAYER, on_me)):
            st = world(30)
            sent, send = collector()
            authsrv.apply_condition(send, st, who, cid, 8.0, 0, 0, 1, by_agent=10)
            book[cid] = [v[2] for op, v in sent if op == OP_AURA and v[0] == agents.PROP_AURA_ON]
            ops = [op for op, v in sent if op in (OP_APPLY, OP_STATUS)
                   or (op == OP_AURA and v[0] in (agents.PROP_AURA_ON, agents.PROP_AURA_OFF))]
            order.append((who, cid, ops))
    want = {c: ([RETAIL_IDS[c]] if c in RETAIL_IDS else []) for c in effects.CONDITION_SKILLS}
    check(on_foe == want and on_me == want,
          "2c. each of the ten conditions draws exactly its retail id on a foe AND on the "
          "player -- 23 24 25 26 27 28 29 29, none for Crippled and Deep Wound",
          (on_foe, on_me))
    bad = [(w, c, ops) for w, c, ops in order
           if ops != ([OP_APPLY] if w == PLAYER else [])
           + ([OP_AURA] if c in RETAIL_IDS else []) + [OP_STATUS]]
    check(not bad,
          "2c'. the order: the player's 0x0042, THEN the [6], THEN the 0x00F1 (retail: the "
          "0x0042 first 54/54, the [6] ahead of the 0x00F1 48/48); a foe's [6] then its 0x00F1",
          bad)

    # 2d. Weakness and Cracked Armor share 29 (RECONSTRUCTION: the hex base id's count)
    st = world(31)
    sent, send = collector()
    w = authsrv.apply_condition(send, st, 31, WEAK, 8.0, 0, 0, 1)
    authsrv.apply_condition(send, st, 31, CRACKED, 8.0, 0, 0, 1)
    adds = [v for op, v in sent if op == OP_AURA and v[0] == agents.PROP_AURA_ON]
    sent.clear()
    authsrv.effect_table(st).close(w["buff"])
    authsrv.effect_list_send(send, st, OP_REMOVE, [31, w["buff"]], "Weakness closes")
    first = [v for op, v in sent if op == OP_AURA]
    sent.clear()
    expire_all(st, send)
    last = [v for op, v in sent if op == OP_AURA]
    check(adds == [[6, 31, 29]] and first == [] and last == [[7, 31, 29]],
          "2d. Weakness then Cracked Armor on one foe: ONE [6, 31, 29]; Weakness closing "
          "sends no [7] while Cracked Armor holds it; the last close sends [7, 31, 29] "
          "(RECONSTRUCTION -- no overlap of the two is on tape)", (adds, first, last))

    # 2e. an EXTENSION keeps the visual up: no [7] / [6] at the re-application
    st = world()
    sent, send = collector()
    authsrv.apply_condition(send, st, PLAYER, BLEED, 5.0, 0, 0, SEVER, by_agent=10)
    sent.clear()
    authsrv.apply_condition(send, st, PLAYER, BLEED, 3.0, 0, 0, SEVER, by_agent=10)
    shorter = list(sent)
    authsrv.apply_condition(send, st, PLAYER, BLEED, 9.0, 0, 0, SEVER, by_agent=10)
    ext = [op for op, _v in sent]
    live = authsrv.effect_table(st).on_agent(PLAYER)
    book = dict(st.get("auras_by_buff") or {})
    sent.clear()
    expire_all(st, send)
    closes = [v for op, v in sent if op == OP_AURA]
    check(shorter == [] and ext == [OP_REMOVE, OP_APPLY] and len(live) == 1
          and book == {(PLAYER, live[0]["buff"]): (PLAYER, (23,))}
          and closes == [[7, PLAYER, 23]],
          "2e. the player's Bleeding re-applied: a shorter one sends nothing; a longer one is "
          "0x0044 + 0x0042 with NO [7] and NO [6] (retail's re-application draws none, 5/5) "
          "and the book re-files the visual under the new buff, so its expiry sends [7, me, "
          "23] once", (shorter, ext, book, closes))

    # 2f. a bleeding foe killed: its [7] rides the death batch
    st = world(27)
    sent, send = collector()
    authsrv.apply_condition(send, st, 27, BLEED, 5.0, 0, 0, SEVER, by_agent=PLAYER)
    st["agents"][27]["health"] = 1.0
    sent.clear()
    authsrv.hit_enemy(send, st, 27, 0, exact=5.0, swing=False, armed=True, label="a killing blow")
    i_dead = next((i for i, (op, v) in enumerate(sent)
                   if op == OP_STATUS and v[0] == 27 and v[1] & effects.STATUS_DEAD), None)
    i_7 = [i for i, (op, v) in enumerate(sent) if op == OP_AURA and v[0] == agents.PROP_AURA_OFF]
    i_step = next((i for i, (op, v) in enumerate(sent)
                   if op == OP_STATUS and v == [27, effects.STATUS_DEAD]), None)
    check(st["agents"][27]["dead"] and [sent[i][1] for i in i_7] == [[7, 27, 23]]
          and None not in (i_dead, i_step) and i_dead < i_7[0] < i_step,
          "2f. a bleeding foe killed: [7, 27, 23] once, behind the death word and ahead of "
          "the step-down 0x00F1 [27, 0x10] (retail 1140.933: [7, 27, 23] then 0x00F1 [27, "
          "16]; the death word ahead of it is our older 'ONE step' deviation, unchanged)",
          [(hex(op), v) for op, v in sent])

    # 2g. THE RECYCLED BUFF ID AT A DEATH: why the book is keyed by (wearer, buff)
    st = world(10, 11)
    tab = authsrv.effect_table(st)
    sent, send = collector()
    hexed = tab.apply(10, EMPATHY, 0, 10.0, time.time(), type_code=authsrv.HEX_TYPE_CODE)
    authsrv.aura_on(send, st, hexed, 0)
    worn = [v for op, v in sent if op == OP_AURA]
    burned = {}

    def payoff(send_, state, conn_id, ep, why):   # hex_end_burst's seam: the payoff Burns 11
        burned["ep"] = authsrv.apply_condition(send_, state, 11, BURN, 3.0, 0, conn_id, 179)
        return [11]

    saved = authsrv.hex_end_burst
    authsrv.hex_end_burst = payoff
    try:
        st["agents"][10]["dead"] = True
        sent.clear()
        authsrv.strip_effects(send, st, 10, 0, "the wearer died")
    finally:
        authsrv.hex_end_burst = saved
    death = [v for op, v in sent if op == OP_AURA and v[0] in (6, 7)]
    sent.clear()
    expire_all(st, send)
    later = [v for op, v in sent if op == OP_AURA and v[0] in (6, 7)]
    check(worn == [[6, 10, 1], [6, 10, 4]]
          and burned.get("ep") is not None and burned["ep"]["buff"] == hexed["buff"],
          "2g. the premise: Empathy's [6, 10, 1] [6, 10, 4] on 10; at 10's death the payoff's "
          "Burning on 11 takes the id the strip just freed -- the collision is exercised, "
          "not assumed", (worn, burned.get("ep")))
    check(death == [[6, 11, 25], [7, 10, 1], [7, 10, 4]] and later == [[7, 11, 25]],
          "2g'. keyed by (wearer, buff): the corpse's REMOVE sends ITS [7, 10, 1] [7, 10, 4] "
          "(not the neighbour's [7, 11, 25]), and the neighbour's Burning keeps its visual "
          "until its own expiry sends [7, 11, 25]", (death, later))

    # 2h. KNOWN-BAD ARM: --no-condition-effect-words is the pre-S13 wire
    saved = authsrv.CONDITION_EFFECT_WORDS
    try:
        authsrv.CONDITION_EFFECT_WORDS = False
        applied, expired, st = bleed_on_foe()
        sent, send = collector()
        authsrv.apply_condition(send, world(), PLAYER, DAZED, 8.0, 12, 0, 1, by_agent=10)
        dazed = [op for op, _v in sent]
    finally:
        authsrv.CONDITION_EFFECT_WORDS = saved
    check(tail(applied, 30) == FLESHY_TAIL[1:] and tail(expired, 30) == EXPIRY_TAIL[1:]
          and dazed == [OP_APPLY, OP_STATUS] and not st.get("auras_by_buff"),
          "2h. KNOWN-BAD ARM, --no-condition-effect-words: the status word and the rate alone "
          "on the foe (no [6] / [7]) and the player's Dazed is 0x0042 + 0x00F1 -- retail's "
          "tails fail against it", (tail(applied, 30), tail(expired, 30), dazed))

    # 2i. the table and the source
    check(effects.CONDITION_EFFECT_IDS == RETAIL_IDS
          and not RETAIL_NONE & set(effects.CONDITION_EFFECT_IDS)
          and set(RETAIL_IDS) | RETAIL_NONE == set(effects.CONDITION_SKILLS),
          "2i. effects.CONDITION_EFFECT_IDS is RETAIL_IDS, and with Crippled and Deep Wound "
          "covers the ten conditions exactly")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    src = open(authsrv.__file__, encoding="utf-8").read()
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_condition_effect_words:", i_main)
    i_ac = src.find("\ndef apply_condition(")
    i_ext = src.find('_held = state.get("auras_by_buff", {}).pop((target_id, old_ep["buff"]), None)', i_ac)
    i_rem = src.find("effect_list_send(send, state, GAME_SMSG_EFFECT_REMOVE, [target_id, "
                     'old_ep["buff"]],', i_ac)
    i_app = src.find("effect_list_send(send, state, GAME_SMSG_EFFECT_APPLY,", i_ac)
    i_on = src.find("            aura_on(send, state, ep, conn_id)\n", i_ac)
    i_st = src.find('    push_status(send, state, ep["agent"], conn_id)', i_ac)
    i_off = src.find("\ndef aura_off(send, state, agent_id, buff):")
    check(ap.parse_args([]).no_condition_effect_words is False
          and ap.parse_args(["--no-condition-effect-words"]).no_condition_effect_words is True
          and 0 < i_main < i_flip and "CONDITION_EFFECT_WORDS = False" in src[i_flip:i_flip + 120]
          and 0 < i_ac < i_ext < i_rem < i_app < i_on < i_st
          and 0 < i_off and '.pop((agent_id, buff), None)' in src[i_off:i_off + 1200]
          and src.count("aura_off(send, state, agent_id, values[1])") == 2
          and "aura_off(send, state, values[1])" not in src,
          "2j. the source: the flag parses (default off) and main() flips it; in "
          "apply_condition the visual is lifted before the extension's REMOVE and aura_on "
          "sits between the 0x0042 and push_status; aura_off pops (wearer, buff), and both "
          "effect_list_send sites pass the wearer")


def main():
    print("test_condwords -- a condition's [6] / [7] words and the (wearer, buff) aura book "
          "(RANGERPRE-S13)")
    section_tape()
    section_server()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
