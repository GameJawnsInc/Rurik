r"""test_instantannounce -- the INSTANT skill's announce and the shout batch order, as
retail sends them (DESKWORK-D5, SKILLS-IA, 2026-09-25; studies/skills 56.9).

WHAT IT IS REALLY CHECKING. Until today every cast this server announced rode
`cast_anim_msg`'s property 60 (a spell's) or 50 (an attack's), and skills 56.2 had
already found that retail announces a shout with NEITHER: `instantjoin.py` reads the
live corpus and finds 133 announces of a Stance, a Shout or a type-16 skill, every one
`0x009F [48, caster, skill]`, 0 of 133 on property 60, every one followed by the
caster's `[21]` visual (the table's +0x78), every SHOUT's followed by a speech bubble
`0x00A5 [caster, one coded string id]` (67 of 67; 0 of 66 stances / type-16), then the
applies, then (the observer, a hero) the E3, then the speed words -- the wearer's
first. The server now sends that batch at the completion, for the player, a hero and a
body, and a party-wide shout's batch is every apply then every speed word, behind
`--no-instant-announce` and `--per-wearer-batch-order`.

THE LITERALS ARE THE TAPE'S: [48, caster, 364] / [21, caster, 622] / 0x00A5 word
0x6658 (= id 25944) from the arena's 56 casts of 364; [48, 30, 348] / [21, 30, 596] /
word 0x6637 (= 25911) from the hero's 7 casts of 348 on 20260914T005758; [48, c, 346] /
[21, c, 601] from 43 casts of Frenzy. Section 1 needs the vault's skills table (the
rows for 346 and 364: type, activation 0, the client's aoe_range) and declares a skip
without it. Section 5 (the non-instant spell and the attack skill byte-identical to
b50da5c8) and section 4's flag arms run on a bare machine; section 6 reads the live
corpus through `instantjoin.census(cutoff=...)` and is declared a skip without it.

  1  the PLAYER: a stance (346) and a shout (364) through handle_skill_press +
     cast_tick -- no property 60 at the press; at the completion E5, [48], [21], (the
     bubble), the applies (the player's, then the hero's at 500 u), THEN the speed
     words (the player's first, the hero's, the henchman's); the bubble's bytes
     through the real codec; no [58].
  2  a HERO: a shout (348) and a stance (346) through land_skill -- E5, [48], [21],
     (the bubble), (the apply), and the E3 LAST, behind them.
  3  a BODY (a hostile): a stance through land_skill -- [48], [21] and nothing else
     (its effect list is not on the wire; no bubble for a stance).
  4  the KNOWN-BAD ARMS: --no-instant-announce restores property 60 at the press,
     [58] at the completion, the hero's E3 beside its E5 and no bubble;
     --per-wearer-batch-order interleaves apply / speed per wearer.
  5  a NON-instant spell (42, targeted and not) and an attack skill press + tick are
     byte-identical to b50da5c8's literals, and identical under both flag arms; a
     hero's SPELL through land_skill is identical under both arms.
  6  the corpus through instantjoin: the counts above, the order counts, the ids.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import content                                                 # noqa: E402
from clientscan import codedstr                                # noqa: E402
sys.path.insert(0, os.path.join(PARENT, "schema"))
from codec import Codec                                        # noqa: E402

# Floor from the BARE-MACHINE green run of 2026-09-25 (RURIK_VAULT pointed at an empty
# directory): 6 -- section 4's two source checks, section 5's two spell literals, the
# arms agreeing and the hero's spell. Sections 1-3 and 4's driven half need the
# vault's skills table, section 5's attack literal the 394 row, section 6 the captures;
# each declares its skip. 45 checks with the vault.
LEDGER = checks.Ledger("instant announce", floor=6)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
APPLY = authsrv.GAME_SMSG_EFFECT_APPLY
SPEED = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE
SPEECH = authsrv.GAME_SMSG_AGENT_SPEECH_BUBBLE
E3, E4, E5 = 0x00E3, 0x00E4, 0x00E5
FRENZY, CHARGE, WATCH = 346, 364, 348
HERO, HENCH, FOE = 30, 31, 40
# THE TAPE'S LITERALS (instantjoin.py, 2026-09-25).
VIS = {FRENZY: 601, CHARGE: 622, WATCH: 596}
WORD = {CHARGE: 0x6658, WATCH: 0x6637}       # the one coded word on the bubble
SID = {CHARGE: 25944, WATCH: 25911}          # what it decodes to
CUTOFF = "20260925T235959"

FLAGS = ("INSTANT_ANNOUNCE", "PER_WEARER_BATCH_ORDER", "PARTY_WIDE_SHOUTS", "EFFECTS",
         "MOVE_SPEED_EFFECTS", "EFFECT_LIST_SELF_ONLY", "SKILL_VISUALS")


def _arm(**kw):
    saved = {k: getattr(authsrv, k) for k in FLAGS}
    for k in FLAGS:
        setattr(authsrv, k, kw.get(k, True if k not in ("PER_WEARER_BATCH_ORDER",) else False))
    return saved


def _restore(saved):
    for k, v in saved.items():
        setattr(authsrv, k, v)


def _body(pos, hero=None, dead=False, allegiance=agents.ALLEGIANCE_PLAYER, skills=()):
    row = {"name": "a body", "dead": dead, "died_at": 0.0, "health": 400.0,
           "max_health": 400.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": allegiance, "attacks_back": False, "skills": list(skills),
           "skill_ready": [0.0] * len(skills), "last_swing": 0.0}
    if hero is not None:
        row["hero"] = hero
    return row


def _fake():
    sent = []
    send = lambda op, vals, why="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": float(agents.PLAYER_HEALTH)}
    authsrv.player_pools(st)
    authsrv.effect_table(st)
    st["agents"][HERO] = _body((500.0, 0.0), hero=6,
                               skills=[(WATCH, 0.0, 4), (FRENZY, 0.0, 4), (42, 2.0, 20)])
    st["agents"][HENCH] = _body((300.0, 0.0))
    st["agents"][FOE] = _body((200.0, 0.0), allegiance=agents.ALLEGIANCE_HOSTILE,
                              skills=[(FRENZY, 0.0, 4)])
    return sent, send, st


def _press(send, st, skill, target=0):
    authsrv.handle_skill_press([0, skill, 7, target], send, st, 0,
                               authsrv.GAME_CMSG_USE_SKILL)


def _rewind(st, s):
    for cast in st.get("pending_casts", ()):
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            cast[k] -= s


def _player_cast(skill):
    """(press, tick): the (op, vals) lists of the press and of the completion tick."""
    sent, send, st = _fake()
    _press(send, st, skill)
    press = list(sent)
    del sent[:]
    _rewind(st, 0.001)
    authsrv.cast_tick(send, st, 0)
    return press, list(sent)


def _land(agent_id, slot):
    sent, send, st = _fake()
    ag = st["agents"][agent_id]
    ag["casting"] = slot
    ag["cast_target"] = None if agent_id != HERO or ag["skills"][slot][0] != 42 else P
    authsrv.land_skill(send, st, agent_id, ag, 0)
    return list(sent)


def _props(msgs, prop):
    return [v for o, v in msgs if o in (INT, INT_T) and v and v[0] == prop]


def _fmt(msgs):
    return [(hex(o), [([hex(ord(c)) for c in x] if isinstance(x, str) else x) for x in v])
            for o, v in msgs]


def _have_rows():
    try:
        for sid in (FRENZY, CHARGE):
            row = agents.WORLD.get("skills", str(sid))
            if float(row["activation"]) != 0.0:
                return f"the vault's row for {sid} has activation {row['activation']}"
        return None
    except content.ContentError as exc:
        return f"{exc}"


def section_player():
    print("== 1. the player: a stance and a shout, no 60 at the press, retail's batch at "
          "the completion ==")
    why = _have_rows()
    if why:
        LEDGER.skip("section 1 (the player, 16 checks): no skills rows for 346 / 364 -- "
                    "the vault's content table is not loaded", why)
        return
    saved = _arm()
    try:
        # THE STANCE.
        press, tick = _player_cast(FRENZY)
        check([o for o, _v in press] == [E4, 0x00A2, INT] and press[2][1] == [8, P, 1]
              and not _props(press, 60),
              "the stance's press is E4, the energy debit, [8 -> 1] -- NO property 60 "
              "(retail: 0 of 62 observer instant casts carry a 60)", f"{_fmt(press)}")
        check(tick[:4] == [(E5, [P, FRENZY, 7, 4]), (INT, [48, P, FRENZY]),
                           (INT, [21, P, VIS[FRENZY]]),
                           (APPLY, tick[3][1])] and tick[3][1][:2] == [P, FRENZY],
              "the completion opens E5 [1, 346, 7, 4], [48, 1, 346], [21, 1, 601], then the "
              "0x0042 on the player -- the tape's own batch for Frenzy (43 casts), the "
              "visual the table's +0x78", f"{_fmt(tick)}")
        check(not _props(tick, 58) and not [o for o, _v in tick if o == SPEECH],
              "no [58] (0 of 62 on the tape) and no speech bubble for a stance (0 of 64)",
              f"{_fmt(tick)}")
        check([o for o, _v in tick].count(E3) == 1
              and [o for o, _v in tick].index(E3) > [o for o, _v in tick].index(APPLY),
              "the E3 closes the tick behind the apply (retail: 0x0042 < E3, 86 of 86)",
              f"{_fmt(tick)}")

        # THE SHOUT, with a hero at 500 u and a henchman at 300 u in earshot.
        press, tick = _player_cast(CHARGE)
        check([o for o, _v in press] == [E4, 0x00A2, INT] and not _props(press, 60),
              "the shout's press: E4, the debit, [8 -> 1], no property 60", f"{_fmt(press)}")
        check(tick[:4] == [(E5, [P, CHARGE, 7, 20]), (INT, [48, P, CHARGE]),
                           (INT, [21, P, VIS[CHARGE]]), (SPEECH, [P, chr(WORD[CHARGE])])],
              "the completion opens E5 [1, 364, 7, 20], [48, 1, 364], [21, 1, 622], then "
              "0x00A5 [1, 0x6658] -- the arena's batch for the observer's 35 Charge!s, "
              "the bubble's one coded word", f"{_fmt(tick[:5])}")
        check(codedstr.parse_coded([WORD[CHARGE]]) == [("id", SID[CHARGE])]
              and codedstr.encode_id(SID[CHARGE]) == [WORD[CHARGE]],
              "0x6658 is the coded form of string id 25944 and nothing else -- the id "
              "content/world.toml's skill_speech row commits, no marker, no text",
              f"{codedstr.parse_coded([WORD[CHARGE]])}")
        wire = Codec().encode("GAME_SMSG", SPEECH, [P, chr(WORD[CHARGE])])
        check(wire == bytes.fromhex("a5000100000001005866"),
              "through the real codec the bubble is a5 00 | 01 00 00 00 | 01 00 | 58 66 -- "
              "header, agent 1, ONE code unit, the word little-endian", f"{wire.hex()}")
        ops = [o for o, _v in tick]
        applies = [v[0] for o, v in tick if o == APPLY]
        speeds = [v[0] for o, v in tick if o == SPEED]
        check(applies == [P, HERO] and speeds == [P, HERO, HENCH],
              "the applies are the player's then the hero's (the henchman's list is not on "
              "the wire), the speed words the player's, the hero's, the henchman's",
              f"applies {applies} speeds {speeds}")
        last_apply = max(i for i, o in enumerate(ops) if o == APPLY)
        first_speed = min(i for i, o in enumerate(ops) if o == SPEED)
        check(last_apply < first_speed,
              "RETAIL'S BATCH ORDER: every 0x0042 before the first 0x0027 (43 of 43 "
              "apply+speed batches on tape; the applies adjacent 6 of 6)", f"{_fmt(tick)}")
        check(speeds[0] == P,
              "and the wearer's own speed word leads the words (16 of 16 multi-word "
              "batches)", f"{speeds}")
        check(ops.index(SPEECH) < ops.index(APPLY) and ops.index(INT) < ops.index(SPEECH),
              "[48] < [21] < 0x00A5 < 0x0042 (133 / 67 / 59 of each on tape)", f"{_fmt(tick)}")
        check(not _props(tick, 58) and not _props(tick, 60),
              "no [58] and no property 60 anywhere in the completion", f"{_fmt(tick)}")
        # THE PROPERTY-48 FORM: 0x009F, three fields, the SKILL in the value slot.
        p48 = [(o, v) for o, v in tick if v and v[0] == 48]
        check(p48 == [(INT, [48, P, CHARGE])],
              "exactly one [48], on 0x009F (0 of 133 ride 0x00A0), the value the skill id",
              f"{p48}")
        # The 8 hold pair and the E3-before-speed slot are the cast cycle's residuals
        # (56.9), named rather than pinned: this batch carries them either way.
        check(ops.count(E3) == 1 and ops.index(E3) > last_apply,
              "the E3 is behind the applies (the tape's 86 of 86); its slot relative to "
              "the speed words is the cast cycle's, a named residual", f"{_fmt(tick)}")
        check(sum(1 for o in ops if o == SPEECH) == 1,
              "one bubble per shout", f"{_fmt(tick)}")
    finally:
        _restore(saved)


def section_hero():
    print("\n== 2. a hero: E5, [48], [21], the bubble, the apply, the E3 LAST ==")
    why = _have_rows()
    if why:
        LEDGER.skip("section 2 (the hero, 4 checks): no skills rows", why)
        return
    saved = _arm()
    try:
        out = _land(HERO, 0)
        check(out == [(E5, [HERO, WATCH, 0, 4]), (INT, [48, HERO, WATCH]),
                      (INT, [21, HERO, VIS[WATCH]]), (SPEECH, [HERO, chr(WORD[WATCH])]),
                      (E3, [HERO, WATCH, 0])],
              "the hero's Watch Yourself!: E5 [30, 348, 0, 4], [48, 30, 348], [21, 30, 596], "
              "0x00A5 [30, 0x6637], E3 [30, 348, 0] -- 20260914T005758's batch for the "
              "hero's 7 casts, the E3 behind the announce (no 0x0042: 348 has no "
              "skill_effect row, 56.7's open item)", f"{_fmt(out)}")
        check(codedstr.parse_coded([WORD[WATCH]]) == [("id", SID[WATCH])],
              "0x6637 decodes to 25911, the id the 348 row commits", "")
        out = _land(HERO, 1)
        ops = [o for o, _v in out]
        check(out[:3] == [(E5, [HERO, FRENZY, 0, 4]), (INT, [48, HERO, FRENZY]),
                          (INT, [21, HERO, VIS[FRENZY]])]
              and ops[3] == APPLY and out[3][1][:2] == [HERO, FRENZY]
              and ops[-1] == E3 and out[-1][1] == [HERO, FRENZY, 0] and SPEECH not in ops,
              "the hero's Frenzy: E5, [48, 30, 346], [21, 30, 601], the 0x0042 on the hero, "
              "E3 last -- the tape's 17 hero stances; no bubble", f"{_fmt(out)}")
        check(not _props(out, 58) and not _props(out, 60),
              "no [58] and no 60 for the hero's instant skill", f"{_fmt(out)}")
    finally:
        _restore(saved)


def section_body():
    print("\n== 3. a hostile body: [48], [21] and nothing else ==")
    why = _have_rows()
    if why:
        LEDGER.skip("section 3 (the body, 1 check): no skills rows", why)
        return
    saved = _arm()
    try:
        out = _land(FOE, 0)
        check(out == [(INT, [48, FOE, FRENZY]), (INT, [21, FOE, VIS[FRENZY]])],
              "a hostile's Frenzy lands as [48, 40, 346], [21, 40, 601] -- the tape's 27 foe "
              "instant casts ([48] [21], the bubble for a shout); no 0x0042 (its list is "
              "not on the wire), no 58, no 60", f"{_fmt(out)}")
    finally:
        _restore(saved)


def section_flags():
    print("\n== 4. the known-bad arms ==")
    # THE BARE HALF: the flag globals exist, default as documented, and main()
    # wires each through a `global` (a flag that parses and never takes effect
    # is the defect this check exists for).
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    i_main = src.index("\ndef main():")
    i_a = src.index("    if a.no_instant_announce:", i_main)
    i_b = src.index("    if a.per_wearer_batch_order:", i_main)
    check(authsrv.INSTANT_ANNOUNCE is True and authsrv.PER_WEARER_BATCH_ORDER is False
          and src.index("global INSTANT_ANNOUNCE", i_a) - i_a < 80
          and src.index("global PER_WEARER_BATCH_ORDER", i_b) - i_b < 80,
          "INSTANT_ANNOUNCE defaults on, PER_WEARER_BATCH_ORDER off, and main() flips "
          "each through a `global` right under its flag", "")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    a0 = ap.parse_args([])
    a1 = ap.parse_args(["--no-instant-announce", "--per-wearer-batch-order"])
    check(a0.no_instant_announce is False and a0.per_wearer_batch_order is False
          and a1.no_instant_announce is True and a1.per_wearer_batch_order is True,
          "--no-instant-announce and --per-wearer-batch-order parse and default off", "")
    why = _have_rows()
    if why:
        LEDGER.skip("section 4's driven half (5 checks): no skills rows", why)
        return
    saved = _arm(INSTANT_ANNOUNCE=False)
    try:
        press, tick = _player_cast(CHARGE)
        check([o for o, _v in press] == [E4, 0x00A2, INT, INT]
              and press[2][1] == [60, P, CHARGE] and press[3][1] == [8, P, 1],
              "--no-instant-announce: the press carries [60, 1, 364] again (the server "
              "until 2026-09-25)", f"{_fmt(press)}")
        check(tick[:3] == [(E5, [P, CHARGE, 7, 20]), (INT, [58, P, 0]),
                           (INT, [21, P, VIS[CHARGE]])]
              and not _props(tick, 48) and SPEECH not in [o for o, _v in tick],
              "  and the completion carries [58, 1, 0] behind the E5, no [48], no bubble",
              f"{_fmt(tick)}")
        out = _land(HERO, 0)
        check(out == [(E5, [HERO, WATCH, 0, 4]), (E3, [HERO, WATCH, 0]),
                      (INT, [58, HERO, 0]), (INT, [21, HERO, VIS[WATCH]])],
              "  the hero's shout: E5, E3 beside it, [58, 30, 0], [21] -- today's bytes",
              f"{_fmt(out)}")
    finally:
        _restore(saved)
    saved = _arm(PER_WEARER_BATCH_ORDER=True)
    try:
        press, tick = _player_cast(CHARGE)
        seq = [(o, v[0]) for o, v in tick if o in (APPLY, SPEED)]
        check(seq == [(APPLY, P), (SPEED, P), (APPLY, HERO), (SPEED, HERO), (SPEED, HENCH)],
              "--per-wearer-batch-order: apply, speed, apply, speed, speed -- interleaved "
              "per wearer, the server until 2026-09-25 (the known-bad arm)",
              f"{[(hex(o), a) for o, a in seq]}")
        ops = [o for o, _v in tick]
        check(max(i for i, o in enumerate(ops) if o == APPLY)
              > min(i for i, o in enumerate(ops) if o == SPEED),
              "  which puts a 0x0027 before the last 0x0042 -- the shape retail never "
              "sends (0 of 43)", f"{_fmt(tick)}")
    finally:
        _restore(saved)


# b50da5c8's own bytes for a non-instant spell and an attack skill, recorded from
# the unmodified tree on 2026-09-25 (the lane's scratch baseline_b50da5c8.json)
# with test_castcycle's stubs: skill_timing (1.0, 0.75, 8.0), skill_cost (10, 0),
# _is_attack_skill forced for the attack. The refusal on the attack is the
# fixture's (no weapon for 394); the literal is the point.
BASELINE = {
    "spell_42_at_40": {
        "press": [(0x00E4, [1, 42, 7]), (0x00A2, [62, 1, 3201092813]),
                  (0x00A0, [60, 1, 40, 42]), (0x009F, [8, 1, 1])],
        "tick1": [(0x00E5, [1, 42, 7, 8]), (0x009F, [58, 1, 0]), (0x009F, [8, 1, 0]),
                  (0x009F, [8, 1, 1])],
        "tick2": [(0x00E3, [1, 42, 7]), (0x00E6, [1, 42, 7])],
    },
    "spell_42_untargeted": {
        "press": [(0x00E4, [1, 42, 7]), (0x00A2, [62, 1, 3201092813]),
                  (0x009F, [60, 1, 42]), (0x009F, [8, 1, 1])],
        "tick1": [(0x00E5, [1, 42, 7, 8]), (0x009F, [58, 1, 0]), (0x009F, [8, 1, 0]),
                  (0x009F, [8, 1, 1])],
        "tick2": [(0x00E3, [1, 42, 7]), (0x00E6, [1, 42, 7])],
    },
    "attack_394_at_40": {
        "press": [(0x00E2, [1, 394, 7])], "tick1": [], "tick2": [],
    },
}


def _stubbed_cast(skill, target, attack):
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    state = {"agents": {}}
    saved = (authsrv.skill_timing, authsrv.skill_cost, authsrv._is_attack_skill)
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    authsrv.skill_cost = lambda sid: (10, 0)
    if attack:
        authsrv._is_attack_skill = lambda sid: True
    try:
        _press(send, state, skill, target)
        press = list(sent)
        del sent[:]
        _rewind(state, 1.0)
        authsrv.cast_tick(send, state, 0)
        tick1 = list(sent)
        del sent[:]
        _rewind(state, 8.0)
        authsrv.cast_tick(send, state, 0)
        tick2 = list(sent)
    finally:
        authsrv.skill_timing, authsrv.skill_cost, authsrv._is_attack_skill = saved
    return {"press": press, "tick1": tick1, "tick2": tick2}


def section_unchanged():
    print("\n== 5. a non-instant spell and an attack skill: byte-identical to b50da5c8 ==")
    runs = {}
    for arm in (True, False):
        saved = _arm(INSTANT_ANNOUNCE=arm)
        try:
            runs[arm] = {"spell_42_at_40": _stubbed_cast(42, 40, False),
                         "spell_42_untargeted": _stubbed_cast(42, 0, False),
                         "attack_394_at_40": _stubbed_cast(394, 40, True)}
        finally:
            _restore(saved)
    for name, want in BASELINE.items():
        if name.startswith("attack") and _have_rows():
            # The attack literal is the WEAPON GATE's refusal (DAGGERS-B4 reads the
            # 394 row's weapon_req against the hammer), which a bare machine cannot
            # reproduce -- there the press is accepted and the burst differs. The
            # arms-agree check below still covers the attack path there.
            LEDGER.skip(f"{name}: b50da5c8's literal is the weapon gate's refusal",
                        "no skills row for 394 on this machine")
            continue
        check(runs[True][name] == want,
              f"{name}: press / tick / tick under the default arm == b50da5c8's literal "
              f"(property 60 at the press, [58] at the completion, untouched)",
              f"{ {k: _fmt(v) for k, v in runs[True][name].items()} }")
    check(runs[True] == runs[False],
          "and the two arms of --no-instant-announce agree on every non-instant message",
          "")
    # A HERO'S SPELL through land_skill: the same under both arms (needs the 42 row for
    # its type; the bare machine sees no row, which _is_instant_skill answers False).
    outs = {}
    for arm in (True, False):
        saved = _arm(INSTANT_ANNOUNCE=arm)
        try:
            outs[arm] = _land(HERO, 2)
        finally:
            _restore(saved)
    check(outs[True] == outs[False] and outs[True][:2] == [(E5, [HERO, 42, 0, 20]),
                                                            (E3, [HERO, 42, 0])]
          and not _props(outs[True], 48),
          "a hero's spell (42) through land_skill: E5, E3 beside it, then the 58 batch -- "
          "the same bytes under both arms, no [48]", f"{_fmt(outs[True])}")


def section_corpus():
    print("\n== 6. the corpus: instantjoin's census ==")
    try:
        import instantjoin
        import vaultpath
        vaultpath.require_dir("captures", "live", why="test_instantannounce section 6")
    except (Exception, SystemExit) as exc:                      # noqa: BLE001
        LEDGER.skip("section 6 (the corpus, 12 checks): no live captures",
                    f"{type(exc).__name__}: {exc}")
        return
    c = instantjoin.census(cutoff=CUTOFF)
    s = instantjoin.score(c)
    check(s["connections"] == 95 and s["refused"] == 1 and s["announces"] == 133
          and s["by_type"] == {"15": 67, "16": 2, "3": 64},
          "95 connections with one observer, 1 refused; 133 [48] announces: Shout 67, "
          "Stance 64, type 16 2 (56.2's census reproduced)",
          f"{s['connections']} / {s['refused']} / {s['announces']} {s['by_type']}")
    check(s["by_type_kind"] == {"15/ally": 17, "15/foe": 8, "15/hero": 7, "15/observer": 35,
                                "16/foe": 2, "3/ally": 3, "3/foe": 17, "3/hero": 17,
                                "3/observer": 27},
          "by caster: the observer 62, a hero 24, a team-mate 20, a foe 27 -- no henchman "
          "casts an instant skill on any tape", f"{s['by_type_kind']}")
    check(s["controls"]["prop60_instant"] == 0 and s["controls"]["prop48_on_int_target"] == 0
          and s["prop60_in_batch"] == 10,
          "property 60 for an instant-type id: 0 (the 10 sixties inside announce batches "
          "are other agents' spells); [48] on 0x00A0: 0",
          f"{s['controls']} in-batch {s['prop60_in_batch']}")
    check(s["speech_by_type"] == {"15/A5": 67, "16/noA5": 2, "3/noA5": 64},
          "0x00A5 beside every shout announce (67 of 67) and beside no stance / type-16 "
          "(0 of 66)", f"{s['speech_by_type']}")
    check(s["speech_ids_by_skill"] == {"364": {"(('id', 25944),)": 56},
                                       "348": {"(('id', 25911),)": 11}}
          and not s["speech_not_coded"],
          "the bubble is ONE coded id: 25944 for 364 (56 of 56), 25911 for 348 (11 of "
          "11), every string16 a coded string", f"{s['speech_ids_by_skill']}")
    check(s["vis21_by_skill"] == {"10/(21,)": 12, "1217/(1083,)": 2, "346/(601,)": 43,
                                  "348/(596,)": 11, "349/(598,)": 3, "364/(622,)": 56,
                                  "379/(638,)": 5, "455/(767,)": 1},
          "the caster's [21] beside every announce, 133 of 133, one id per skill -- the "
          "eight content/world.toml skill_visual rows", f"{s['vis21_by_skill']}")
    check(s["own"] == 62 and s["own_e4_dt"] == {"0.0": 62} and s["own_e5_dt"] == {"0.0": 62}
          and s["own_e3_dt"] == {"0.0": 62} and s["own_no_prop8"] == 62,
          "the observer's 62 own casts: E4, E5 and E3 all at dt = 0 from the [48]; no "
          "property 8 in any", f"{s['own']} {s['own_e4_dt']} {s['own_e3_dt']} {s['own_no_prop8']}")
    rel = s["rel"]
    check(rel["48<21"] == {"True": 133} and rel["21<A5"].get("True") == 67
          and rel["48<A5"].get("True") == 67 and rel["A5<apply"].get("True") == 59
          and rel["48<apply"].get("True") == 103 and rel["E5<48"].get("True") == 93
          and all(rel[k].get("False", 0) == 0 for k in rel),
          "the order: [48] < [21] (133), [21] < 0x00A5 (67), 0x00A5 < 0x0042 (59), "
          "[48] < 0x0042 (103), E5 < [48] (93); no batch inverts any part", f"{rel}")
    check(rel["apply<E3"].get("True") == 86 and rel["E3<speed"].get("True") == 29
          and rel["status<E3"].get("True") == 8,
          "the E3 sits between the applies and the speed words (86 / 29; the status word "
          "ahead of it 8 of 8) -- the cast cycle's residual, named", f"{rel}")
    check(s["applies_before_speeds"] == {"None": 90, "True": 43}
          and len(s["multi_apply"]) == 6 and s["multi_apply_adjacent"] == 6
          and s["multi_apply_with_speed"] == 0,
          "THE BATCH ORDER: every speed word after the last apply, 43 of 43; the 6 "
          "two-apply batches (the hero's 348) adjacent 6 of 6 and none with a speed word "
          "-- the composed rule is two OBSERVED halves", f"{s['applies_before_speeds']} "
          f"{len(s['multi_apply'])} {s['multi_apply_adjacent']} {s['multi_apply_with_speed']}")
    check(s["own_multi_speed"] == 17 and s["own_multi_speed_with_word"] == 16
          and s["own_multi_speed_wearer_first"] == 16,
          "the wearer's own speed word leads, 16 of 16 (the 17th multi-word batch is a "
          "re-cast over an open shout with no own word, 56.5)",
          f"{s['own_multi_speed']} {s['own_multi_speed_with_word']} "
          f"{s['own_multi_speed_wearer_first']}")
    check(s["controls"]["speech_total"] == 207 and s["controls"]["speech_beside_48"] == 67
          and len(s["speech_elsewhere"]) == 140,
          "207 bubbles in the corpus: 67 beside a [48], 140 elsewhere (NPC lines, unread)",
          f"{s['controls']}")


def main():
    section_player()
    section_hero()
    section_body()
    section_flags()
    section_unchanged()
    section_corpus()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
