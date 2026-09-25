r"""test_instantannounce -- the INSTANT skill's announce and the shout batch order, as
retail sends them (DESKWORK-D5, SKILLS-IA, 2026-09-25; studies/skills 56.9).

WHAT IT IS REALLY CHECKING. Until today every cast this server announced rode
`cast_anim_msg`'s property 60 (a spell's) or 50 (an attack's), and skills 56.2 had
already found that retail announces a shout with NEITHER: `instantjoin.py` reads the
live corpus and finds 133 announces of a Stance, a Shout or a type-16 skill, every one
`0x009F [48, caster, skill]`, 0 of 133 on property 60, every one followed by the
caster's `[21]` visual (the table's +0x78), every SHOUT's followed by a speech bubble
`0x00A5 [caster, one coded string id]` (67 of 67; 0 of 66 stances / type-16), then the
applies, then (the observer, a hero) the E3, then the speed words -- the applies and
the words each in ASCENDING AGENT ID (39 of 39 multi-word batches; the 6 two-apply
batches). The server now sends that batch at the completion, for the player, a hero
and a body, and a party-wide shout's batch is every apply then every speed word, behind
`--no-instant-announce` and `--per-wearer-batch-order`.

THE LITERALS ARE THE TAPE'S: [48, caster, 364] / [21, caster, 622] / 0x00A5 word
0x6658 (= id 25944) from the 56 casts of 364 on seven captures; [48, 30, 348] /
[21, 30, 596] / word 0x6637 (= 25911) from the hero's 7 casts of 348 on
20260914T005758; [48, c, 346] / [21, c, 601] from 43 casts of Frenzy. THE KNOWN-BAD
ARM'S LITERALS ARE b50da5c8's OWN, recorded from a `git archive b50da5c8` export
driven through this file's fixture (the review pass, 2026-09-25: the first cut
compared the arm against the new tree's own output and so pinned a `[21]` b50da5c8
never sent). Sections 1-3 and 4's driven half need the vault's skills table (the rows
for 346 / 364 / 348: type, activation 0, the client's aoe_range) and declare a skip
without it; section 5's spell literals and the flags' source checks run on a bare
machine; section 6 reads the live corpus through `instantjoin.census(cutoff=...)` and
is declared a skip without it.

  1  the PLAYER: a stance (346) and a shout (364) through handle_skill_press +
     cast_tick -- no property 60 at the press; at the completion E5, [48], [21], (the
     bubble), the applies (the player's, then the hero's at 500 u), THEN the speed
     words (the player's, the hero's, the henchman's -- ascending, and the player IS
     agent 1); the bubble's bytes through the real codec; no [58].
  2  a HERO: a shout (348), a stance (346) and "Charge!" (364) through land_skill --
     E5, [48], [21], (the bubble), the applies ASCENDING (the player's 1 before the
     caster's own 30, the tape's 6 of 6), the words ascending, and the E3 LAST;
     and the target-dead exit keeps the E3 (b50da5c8 sent it; the first cut dropped it).
  3  a BODY (a hostile): a stance through land_skill -- [48], [21] and nothing else;
     THE START SITES through the real ticks (enemy_attack_tick, ally_cast_tick, a
     queued press's begin_cast): no property 60 at any start, [48] [21] at the landing;
     THE WINDOW: a begun instant cast is not cancelled by a movement mark, not
     interrupted at the player or at a body, while a QUEUED one is still un-queued.
  4  the KNOWN-BAD ARMS: with both flags flipped every fixture equals b50da5c8's
     recorded literal (the press's 60, the [58], the hero's E3 beside its E5, no
     bubble, NO [21] for the seven rows marked since = SKILLS-IA, the start sites'
     60, the cancellable window, the interleave); --no-instant-announce alone keeps
     retail's apply/speed order; --per-wearer-batch-order alone interleaves.
  5  a NON-instant spell (42, targeted and not) and an attack skill (394, the weapon
     gate off, the damage roll seeded) press + two ticks are byte-identical to
     b50da5c8's literals, and identical under both flag arms; a hero's SPELL through
     land_skill is identical under both arms.
  6  the corpus through instantjoin: the counts above, the order counts by caster
     kind, the ids.
"""
import os
import random
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
import content                                                 # noqa: E402
from clientscan import codedstr                                # noqa: E402
sys.path.insert(0, os.path.join(PARENT, "schema"))
from codec import Codec                                        # noqa: E402

# Floor from the BARE-MACHINE green run of 2026-09-25 (the review pass; RURIK_VAULT
# pointed at an empty directory): 6 -- section 4's two source checks, section 5's two
# spell literals, the arms agreeing and the hero's spell. Sections 1-3 and 4's driven
# half need the vault's skills table, section 5's attack literal the 394 row, section
# 6 the captures; each declares its skip. 67 checks with the vault.
LEDGER = checks.Ledger("instant announce", floor=6)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
APPLY = authsrv.GAME_SMSG_EFFECT_APPLY
SPEED = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE
SPEECH = authsrv.GAME_SMSG_AGENT_SPEECH_BUBBLE
E2, E3, E4, E5 = 0x00E2, 0x00E3, 0x00E4, 0x00E5
FRENZY, CHARGE, WATCH = 346, 364, 348
HERO, HENCH, FOE = 30, 31, 40
# THE TAPE'S LITERALS (instantjoin.py, 2026-09-25).
VIS = {FRENZY: 601, CHARGE: 622, WATCH: 596}
WORD = {CHARGE: 0x6658, WATCH: 0x6637}       # the one coded word on the bubble
SID = {CHARGE: 25944, WATCH: 25911}          # what it decodes to
CUTOFF = "20260925T235959"
SEED = 20260925                              # the attack's damage roll, seeded

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
                               skills=[(WATCH, 0.0, 4), (FRENZY, 0.0, 4), (42, 2.0, 20),
                                       (CHARGE, 0.0, 20)])
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


def _land(agent_id, slot, target=None, kill=None):
    sent, send, st = _fake()
    ag = st["agents"][agent_id]
    ag["casting"] = slot
    ag["cast_target"] = target
    if kill is not None:
        st["agents"][kill]["dead"] = True
    authsrv.land_skill(send, st, agent_id, ag, 0)
    return list(sent)


def _npc(agent_id, bar, allegiance, health, pos):
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 100.0, "player_dead": False}
    authsrv.effect_table(st)
    st["agents"][agent_id] = {
        "name": "caster", "dead": False, "died_at": 0.0, "health": health,
        "max_health": 100.0, "last_hit": 0.0, "pos": pos, "plane": 0,
        "allegiance": allegiance, "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
        "effects": 0, "attacks_back": allegiance == agents.ALLEGIANCE_HOSTILE,
        "skills": bar, "skill_ready": [0.0] * len(bar),
        "last_swing": time.time() - 100.0}
    return st


def _ticks(tick_fn, st, n=4):
    """Run the real tick n times, 20 ms apart; the non-empty sends per tick."""
    sent = []
    send = lambda op, vals, why="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    out = []
    for _ in range(n):
        del sent[:]
        tick_fn(send, st, 0)
        if sent:
            out.append(list(sent))
        time.sleep(0.02)
    return out


def _hostile_stance():
    """A hostile with Frenzy on a one-slot bar, in reach: enemy_attack_tick's start
    (test_recharge's fixture) and its landing on the next tick."""
    return _ticks(authsrv.enemy_attack_tick,
                  _npc(10, ((FRENZY, 0.0, 4.0),), agents.ALLEGIANCE_HOSTILE, 50.0, (85.0, 0.0)))


def _party_stance():
    """A hurt hero (10 of 100: below HERO_HEAL_AT, so the self-kind pick fires) with
    Frenzy: ally_cast_tick's start and its landing."""
    return _ticks(authsrv.ally_cast_tick,
                  _npc(20, [(FRENZY, 0.0, 4.0)], agents.ALLEGIANCE_PLAYER, 10.0, (5.0, 0.0)))


def _queued_instant():
    """A spell (42, 2.0 s) then Frenzy pressed while busy -- the instant skill QUEUES
    and begins through begin_cast at the spell's aftercast end; every tick's sends."""
    sent, send, st = _fake()
    _press(send, st, 42)
    _press(send, st, FRENZY)
    out = [list(sent)]
    del sent[:]
    for s in (2.0, 0.8, 0.1):
        _rewind(st, s)
        authsrv.cast_tick(send, st, 0)
        out.append(list(sent))
        del sent[:]
    return out


def _window():
    """The press of a shout, then a movement mark before the completion tick; a
    hostile's armed stance interrupted; a queued instant cast under a movement mark."""
    sent, send, st = _fake()
    _press(send, st, CHARGE)
    press = list(sent)
    del sent[:]
    marked = authsrv._mark_cancelled(st, "movement", time.time(), True)
    authsrv.cast_tick(send, st, 0)
    after = list(sent)
    # the player's window under an interrupt
    sent2, send2, st2 = _fake()
    _press(send2, st2, CHARGE)
    del sent2[:]
    saved = authsrv.INTERRUPTS
    authsrv.INTERRUPTS = True
    try:
        r_player = authsrv.interrupt_player(send2, st2, 0, 57, FOE, mode="action")
        # a hostile's armed stance
        st3 = _npc(10, [(FRENZY, 0.0, 4.0)], agents.ALLEGIANCE_HOSTILE, 50.0, (85.0, 0.0))
        foe = st3["agents"][10]
        foe["casting"], foe["cast_lands_at"] = 0, time.time() + 0.05
        sent3 = []
        send3 = lambda op, vals, why="", quiet=False: sent3.append((op, list(vals)))   # noqa: E731
        r_body = authsrv.interrupt_body(send3, st3, 10, foe, 0, 57, P, mode="action")
    finally:
        authsrv.INTERRUPTS = saved
    # a QUEUED instant cast is still un-queued by movement
    sent4, send4, st4 = _fake()
    _press(send4, st4, 42)
    _press(send4, st4, FRENZY)
    marked_q = authsrv._mark_cancelled(st4, "movement", time.time(), True)
    queued = [c for c in st4["pending_casts"] if c["skill_id"] == FRENZY]
    return {"press": press, "marked": marked, "after": after, "r_player": r_player,
            "sent_player": list(sent2), "r_body": r_body, "sent_body": sent3,
            "marked_q": marked_q, "queued_cancelled": bool(queued and queued[0].get("cancelled"))}


def _props(msgs, prop):
    return [v for o, v in msgs if o in (INT, INT_T) and v and v[0] == prop]


def _fmt(msgs):
    return [(hex(o), [([hex(ord(c)) for c in x] if isinstance(x, str) else x) for x in v])
            for o, v in msgs]


def _have_rows():
    try:
        for sid in (FRENZY, CHARGE, WATCH):
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
              "0x00A5 [1, 0x6658] -- the batch of the observer's 34 Charge!s (21 on the "
              "arena), the bubble's one coded word", f"{_fmt(tick[:5])}")
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
        check(speeds == sorted(speeds) and speeds[0] == P,
              "and the words ASCEND by agent id (39 of 39 multi-word batches on tape) -- "
              "the player is agent 1, so its own word leads as the observer's did in 16 "
              "of 16, where the observer was the lowest id every time", f"{speeds}")
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
    print("\n== 2. a hero: E5, [48], [21], the bubble, the applies ASCENDING, the E3 LAST ==")
    why = _have_rows()
    if why:
        LEDGER.skip("section 2 (the hero, 7 checks): no skills rows", why)
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
        # THE HERO'S CHARGE! with the player and a henchman in earshot -- the order
        # the tape puts a non-lowest caster's batch in (the review's EV-2).
        out = _land(HERO, 3)
        ops = [o for o, _v in out]
        applies = [v[0] for o, v in out if o == APPLY]
        speeds = [v[0] for o, v in out if o == SPEED]
        check(out[:4] == [(E5, [HERO, CHARGE, 0, 20]), (INT, [48, HERO, CHARGE]),
                          (INT, [21, HERO, VIS[CHARGE]]), (SPEECH, [HERO, chr(WORD[CHARGE])])]
              and applies == [P, HERO] and speeds == [P, HERO, HENCH]
              and max(i for i, o in enumerate(ops) if o == APPLY)
              < min(i for i, o in enumerate(ops) if o == SPEED)
              and ops[-1] == E3 and out[-1][1] == [HERO, CHARGE, 0],
              "the hero's Charge!: E5, [48], [21], the bubble, the applies ASCENDING -- the "
              "player's 1 BEFORE the caster's own 30 (the tape's 6 two-apply batches: the "
              "observer's 29 ahead of the hero's 30, 6 of 6) -- then the words 1, 30, 31 "
              "(39 of 39 multi-word batches ascending; the caster's first 0 of 22 when it "
              "is not the lowest id), then the E3 last",
              f"applies {applies} speeds {speeds} {_fmt(out)}")
        # THE TARGET-DEAD EXIT keeps the deferred E3 (b50da5c8: E5, E3, [58]; the
        # first cut: E5, [58] and no E3 -- the review's EV-4 / CD-4). The [48] in
        # the [58]'s place is RECONSTRUCTION (no targeted instant skill on tape).
        out = _land(HERO, 3, target=HENCH, kill=HENCH)
        check(out == [(E5, [HERO, CHARGE, 0, 20]), (INT, [48, HERO, CHARGE]),
                      (E3, [HERO, CHARGE, 0])],
              "the hero's Charge! whose cast_target died: E5, [48], E3 -- the E3 is kept on "
              "the early exit (b50da5c8 sent E5, E3, [58] there), nothing lands",
              f"{_fmt(out)}")
        out = _land(HERO, 2, target=P)
        check(out[:2] == [(E5, [HERO, 42, 0, 20]), (E3, [HERO, 42, 0])] and not _props(out, 48),
              "control: a hero's SPELL (42) through land_skill keeps its E3 beside the E5 and "
              "no [48]", f"{_fmt(out)}")
    finally:
        _restore(saved)


def section_body():
    print("\n== 3. a hostile body, the start sites through the real ticks, the window ==")
    why = _have_rows()
    if why:
        LEDGER.skip("section 3 (the body, the start sites, the window: 11 checks): no "
                    "skills rows", why)
        return
    saved = _arm()
    try:
        out = _land(FOE, 0)
        check(out == [(INT, [48, FOE, FRENZY]), (INT, [21, FOE, VIS[FRENZY]])],
              "a hostile's Frenzy lands as [48, 40, 346], [21, 40, 601] -- the tape's 27 foe "
              "instant casts ([48] [21], the bubble for a shout); no 0x0042 (its list is "
              "not on the wire), no 58, no 60", f"{_fmt(out)}")
        # THE START SITES, driven through the REAL ticks (the review's CD-2: the
        # first cut drove land_skill with `casting` set by hand, so putting the 60
        # back at any start left it green).
        ticks = _hostile_stance()
        flat = [m for t in ticks for m in t]
        check(len(ticks) >= 2 and not _props(flat, 60)
              and [m for m in flat if m[0] in (INT, INT_T) and m[1][0] in (48, 21)]
              == [(INT, [48, 10, FRENZY]), (INT, [21, 10, VIS[FRENZY]])],
              "enemy_attack_tick: a hostile's Frenzy STARTS with no property 60 (retail's 27 "
              "foe instant casts open with nothing; b50da5c8 sent [60, 10, 1, 346] there) "
              "and LANDS on the next tick as [48, 10, 346], [21, 10, 601]",
              f"{[_fmt(t) for t in ticks]}")
        ticks = _party_stance()
        flat = [m for t in ticks for m in t]
        check(ticks and not _props(flat, 60)
              and [m for m in flat if m[0] in (INT, INT_T) and m[1][0] in (48, 21)]
              == [(INT, [48, 20, FRENZY]), (INT, [21, 20, VIS[FRENZY]])],
              "ally_cast_tick: a hurt party body's Frenzy starts with no property 60 "
              "(b50da5c8 sent [60, 20, 20, 346]) and lands as [48, 20, 346], [21, 20, 601]",
              f"{[_fmt(t) for t in ticks]}")
        ticks = _queued_instant()
        flat = [m for t in ticks for m in t]
        check([m for m in flat if m[0] == INT and m[1][:2] == [60, P]] == [(INT, [60, P, 42])]
              and [m for m in flat if m[0] == INT and m[1][0] == 48] == [(INT, [48, P, FRENZY])],
              "begin_cast: Frenzy pressed behind a 2 s spell QUEUES, begins at the spell's "
              "aftercast end with no [60, 1, 346] (b50da5c8 sent one) and completes with "
              "[48, 1, 346]; the spell's own [60, 1, 42] still goes out (control)",
              f"{[_fmt(t) for t in ticks]}")
        # THE WINDOW (the review's CD-5): a begun instant cast has no window on retail
        # (E4, E5, [48] at one stamp, 62 of 62) -- so ours is not cancellable in the
        # tick before its completion; a QUEUED one still is.
        w = _window()
        check(w["marked"] == 0 and [v for o, v in w["after"] if o == INT and v[0] == 48]
              == [[48, P, CHARGE]] and not _props(w["after"], 59)
              and E2 not in [o for o, _v in w["after"]],
              "a movement mark between the shout's press and its completion tick marks "
              "NOTHING and the completion goes out whole -- no [59], no E2 (b50da5c8: "
              "[8 -> 0], [59, 1, 0], E2 for a cast the client never saw start)",
              f"marked {w['marked']} {_fmt(w['after'])}")
        check(w["r_player"] is None and not w["sent_player"],
              "interrupt_player inside that window: nothing to interrupt, nothing sent",
              f"{w['r_player']} {_fmt(w['sent_player'])}")
        check(w["r_body"] is None and not w["sent_body"],
              "interrupt_body on a hostile whose Frenzy is armed for the next tick: nothing "
              "to interrupt, nothing sent (b50da5c8: [59, 10, 0], [35, 10, 0])",
              f"{w['r_body']} {_fmt(w['sent_body'])}")
        check(w["marked_q"] == 2 and w["queued_cancelled"],
              "control: a QUEUED Frenzy behind a spell is still un-queued by the movement "
              "mark (2 marked: the spell and the queued instant)",
              f"marked {w['marked_q']} cancelled {w['queued_cancelled']}")
    finally:
        _restore(saved)


# b50da5c8's OWN bytes for every fixture above, recorded on 2026-09-25 from a
# `git archive b50da5c8` export driven through this file's fixture (the lane's
# scratch fix_record.py / rec_b50.json). Section 4 compares the known-bad arm
# against THESE, never against the new tree's own output.
B50 = {
    "player_364": {
        "press": [(E4, [1, 364, 7]), (0x00A2, [62, 1, 3192704205]), (INT, [60, 1, 364]),
                  (INT, [8, 1, 1])],
        "tick": [(E5, [1, 364, 7, 20]), (INT, [58, 1, 0]),
                 (APPLY, [1, 364, 6, 1, 1090519040]), (SPEED, [1, 383.04]),
                 (APPLY, [30, 364, 6, 2, 1090519040]), (SPEED, [30, 383.04]),
                 (SPEED, [31, 383.04]), (INT, [8, 1, 0]), (INT, [8, 1, 1]),
                 (E3, [1, 364, 7])],
    },
    "player_346": {
        "press": [(E4, [1, 346, 7]), (0x00A2, [62, 1, 3192704205]), (INT, [60, 1, 346]),
                  (INT, [8, 1, 1])],
        "tick": [(E5, [1, 346, 7, 4]), (INT, [58, 1, 0]), (INT, [21, 1, 601]),
                 (APPLY, [1, 346, 0, 1, 1090519040]), (INT, [8, 1, 0]), (INT, [8, 1, 1]),
                 (E3, [1, 346, 7])],
    },
    "hero_348": [(E5, [30, 348, 0, 4]), (E3, [30, 348, 0]), (INT, [58, 30, 0])],
    "hero_346": [(E5, [30, 346, 0, 4]), (E3, [30, 346, 0]), (INT, [58, 30, 0]),
                 (INT, [21, 30, 601]), (APPLY, [30, 346, 12, 1, 1090519040])],
    "hero_364": [(E5, [30, 364, 0, 20]), (E3, [30, 364, 0]), (INT, [58, 30, 0]),
                 (APPLY, [30, 364, 12, 1, 1093664768]), (SPEED, [30, 383.04]),
                 (APPLY, [1, 364, 12, 2, 1093664768]), (SPEED, [1, 383.04]),
                 (SPEED, [31, 383.04])],
    "hero_364_dead_target": [(E5, [30, 364, 0, 20]), (E3, [30, 364, 0]), (INT, [58, 30, 0])],
    "foe_346": [(INT, [58, 40, 0]), (INT, [21, 40, 601])],
    "hostile_start_60": (INT_T, [60, 10, 1, 346]),
    "party_start_60": (INT_T, [60, 20, 20, 346]),
    "begin_cast_60": (INT, [60, 1, 346]),
    "window_after": [(INT, [8, 1, 0]), (INT, [59, 1, 0]), (E2, [1, 364, 7])],
    "window_body": [(INT, [59, 10, 0]), (INT, [35, 10, 0])],
}


def section_flags():
    print("\n== 4. the known-bad arms: b50da5c8's own recorded bytes ==")
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
        LEDGER.skip("section 4's driven half (14 checks): no skills rows", why)
        return
    # BOTH FLAGS FLIPPED = the server until 2026-09-25, byte for byte.
    saved = _arm(INSTANT_ANNOUNCE=False, PER_WEARER_BATCH_ORDER=True)
    try:
        press, tick = _player_cast(CHARGE)
        check(press == B50["player_364"]["press"],
              "both flags: the shout's press is b50da5c8's -- E4, the debit, [60, 1, 364], "
              "[8 -> 1]", f"{_fmt(press)}")
        check(tick == B50["player_364"]["tick"],
              "  and its completion is b50da5c8's -- E5, [58, 1, 0], apply / speed / apply / "
              "speed / speed interleaved, the hold pair, E3; NO [21, 1, 622] (the 364 row is "
              "marked since = SKILLS-IA and b50da5c8 had none) and no bubble",
              f"{_fmt(tick)}")
        press, tick = _player_cast(FRENZY)
        check(press == B50["player_346"]["press"] and tick == B50["player_346"]["tick"],
              "  Frenzy's press and completion are b50da5c8's -- and its [21, 1, 601] STILL "
              "goes out (346's row predates the lane and is unmarked)", f"{_fmt(tick)}")
        check(_land(HERO, 0) == B50["hero_348"],
              "  the hero's 348: E5, E3 beside it, [58, 30, 0] and nothing else -- no [21, "
              "30, 596], no bubble (b50da5c8)", f"{_fmt(_land(HERO, 0))}")
        check(_land(HERO, 1) == B50["hero_346"],
              "  the hero's 346: E5, E3, [58], [21, 30, 601], the apply (b50da5c8)",
              f"{_fmt(_land(HERO, 1))}")
        check(_land(HERO, 3) == B50["hero_364"],
              "  the hero's 364: E5, E3, [58], then apply 30 / speed 30 / apply 1 / speed 1 / "
              "speed 31 -- the caster's wearer first, interleaved (b50da5c8)",
              f"{_fmt(_land(HERO, 3))}")
        check(_land(HERO, 3, target=HENCH, kill=HENCH) == B50["hero_364_dead_target"],
              "  the hero's 364 on a dead target: E5, E3, [58] (b50da5c8)",
              f"{_fmt(_land(HERO, 3, target=HENCH, kill=HENCH))}")
        check(_land(FOE, 0) == B50["foe_346"],
              "  the hostile's 346: [58, 40, 0], [21, 40, 601] (b50da5c8)",
              f"{_fmt(_land(FOE, 0))}")
        flat = [m for t in _hostile_stance() for m in t]
        check(B50["hostile_start_60"] in flat and not _props(flat, 48),
              "  enemy_attack_tick's start carries [60, 10, 1, 346] again and nothing "
              "carries a [48] (b50da5c8)", f"{_fmt(flat)}")
        flat = [m for t in _party_stance() for m in t]
        check(B50["party_start_60"] in flat and not _props(flat, 48),
              "  ally_cast_tick's start carries [60, 20, 20, 346] again (b50da5c8)",
              f"{_fmt(flat)}")
        flat = [m for t in _queued_instant() for m in t]
        check(B50["begin_cast_60"] in flat and not _props(flat, 48),
              "  begin_cast sends [60, 1, 346] for the queued Frenzy again (b50da5c8)",
              f"{_fmt(flat)}")
        w = _window()
        check(w["marked"] == 1 and w["after"] == B50["window_after"]
              and w["r_body"] == "cast" and w["sent_body"] == B50["window_body"],
              "  the window is cancellable again: the movement mark marks the shout and the "
              "tick sends [8 -> 0], [59, 1, 0], E2; the hostile's armed stance is "
              "interrupted with [59, 10, 0], [35, 10, 0] (b50da5c8)",
              f"marked {w['marked']} {_fmt(w['after'])} {w['r_body']} {_fmt(w['sent_body'])}")
    finally:
        _restore(saved)
    # --no-instant-announce ALONE keeps retail's apply-then-speed order (the
    # runsheet's A2 arm; the review's CD-7).
    saved = _arm(INSTANT_ANNOUNCE=False)
    try:
        press, tick = _player_cast(CHARGE)
        ops = [o for o, _v in tick]
        check(press[2][1] == [60, P, CHARGE] and tick[:2] == [(E5, [P, CHARGE, 7, 20]),
                                                             (INT, [58, P, 0])]
              and not _props(tick, 21) and SPEECH not in ops
              and max(i for i, o in enumerate(ops) if o == APPLY)
              < min(i for i, o in enumerate(ops) if o == SPEED),
              "--no-instant-announce alone: [60] at the press, E5 then [58] at the "
              "completion, no [21] (the marked row), no bubble -- and the applies still "
              "precede every speed word (the order is the other flag's)", f"{_fmt(tick)}")
    finally:
        _restore(saved)
    saved = _arm(PER_WEARER_BATCH_ORDER=True)
    try:
        press, tick = _player_cast(CHARGE)
        seq = [(o, v[0]) for o, v in tick if o in (APPLY, SPEED)]
        check(seq == [(APPLY, P), (SPEED, P), (APPLY, HERO), (SPEED, HERO), (SPEED, HENCH)],
              "--per-wearer-batch-order alone: apply, speed, apply, speed, speed -- "
              "interleaved per wearer, the server until 2026-09-25 (the known-bad arm)",
              f"{[(hex(o), a) for o, a in seq]}")
        ops = [o for o, _v in tick]
        check(max(i for i, o in enumerate(ops) if o == APPLY)
              > min(i for i, o in enumerate(ops) if o == SPEED),
              "  which puts a 0x0027 before the last 0x0042 -- the shape retail never "
              "sends (0 of 43)", f"{_fmt(tick)}")
    finally:
        _restore(saved)


# b50da5c8's own bytes for a non-instant spell and an attack skill, recorded from
# the export on 2026-09-25 (rec_b50.json) with test_castcycle's stubs: skill_timing
# (1.0, 0.75, 8.0), skill_cost (10, 0), _is_attack_skill forced for the attack, the
# WEAPON GATE off for the attack (the first cut's literal was the gate's refusal,
# so the attack press was never reached -- the review's EV-3 / CD-3) and the
# damage roll seeded (SEED) before the press and each tick, so the 0x00A3's f32
# is a literal.
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
        "press": [(0x00E4, [1, 394, 7]), (0x00A2, [62, 1, 3201092813]),
                  (0x00A0, [50, 1, 40, 394]), (0x009F, [8, 1, 1])],
        "tick1": [(0x00E5, [1, 394, 7, 8]), (0x009F, [46, 1, 0]),
                  (0x00A3, [16, 40, 1, 3156465418])],
        "tick2": [(0x00E3, [1, 394, 7]), (0x00E6, [1, 394, 7])],
    },
}


def _stubbed_cast(skill, target, attack):
    sent, send, state = _fake()
    state["agents"][FOE]["pos"] = (10.0, 0.0)           # in reach of the strike
    saved = (authsrv.skill_timing, authsrv.skill_cost, authsrv._is_attack_skill,
             authsrv.WEAPON_GATE)
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    authsrv.skill_cost = lambda sid: (10, 0)
    if attack:
        authsrv._is_attack_skill = lambda sid: True
        authsrv.WEAPON_GATE = False
    try:
        random.seed(SEED)
        _press(send, state, skill, target)
        press = list(sent)
        del sent[:]
        _rewind(state, 1.0)
        random.seed(SEED)
        authsrv.cast_tick(send, state, 0)
        tick1 = list(sent)
        del sent[:]
        _rewind(state, 8.0)
        random.seed(SEED)
        authsrv.cast_tick(send, state, 0)
        tick2 = list(sent)
    finally:
        (authsrv.skill_timing, authsrv.skill_cost, authsrv._is_attack_skill,
         authsrv.WEAPON_GATE) = saved
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
            # The strike's terms read the 394 row (skill_damage, the location
            # roll's armour), which a bare machine has no table for; the
            # arms-agree check below still covers the attack path there.
            LEDGER.skip(f"{name}: b50da5c8's literal reads the 394 row",
                        "no skills row for 394 on this machine")
            continue
        check(runs[True][name] == want,
              f"{name}: press / tick / tick under the default arm == b50da5c8's literal "
              + ("(property 50 at the press, [46] then the seeded damage word at the "
                 "strike, E3 / E6 -- the attack path REACHED, untouched)"
                 if name.startswith("attack") else
                 "(property 60 at the press, [58] at the completion, untouched)"),
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
            outs[arm] = _land(HERO, 2, target=P)
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
        LEDGER.skip("section 6 (the corpus, 14 checks): no live captures",
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
    check(s["by_type_skill"].get("15/364") == 56 and s["by_type_skill"].get("15/348") == 11,
          "364 is announced 56 times (34 the observer's, 21 of those on the arena; 14 "
          "team-mates', 8 foes'), 348 eleven (7 the hero's, 3 a team-mate's, 1 the "
          "observer's)", f"{s['by_type_skill']}")
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
          and rel["48<apply"].get("True") == 103 and rel["E5<48"] == {"True": 86, "None": 47}
          and all(rel[k].get("False", 0) == 0 for k in rel),
          "the order: [48] < [21] (133), [21] < 0x00A5 (67), 0x00A5 < 0x0042 (59), "
          "[48] < 0x0042 (103), the caster's OWN E5 < [48] (86 = 62 observer + 24 hero; "
          "47 casters send no E5: 20 team-mates, 27 foes); no batch inverts any part",
          f"{rel}")
    check(rel["apply<E3"].get("True") == 86 and rel["E3<speed"].get("True") == 29
          and rel["status<E3"].get("True") == 8,
          "the E3 sits between the applies and the speed words (86 / 29; the status word "
          "ahead of it 8 of 8) -- the cast cycle's residual, named", f"{rel}")
    check(s["applies_before_speeds"] == {"None": 90, "True": 43}
          and len(s["multi_apply"]) == 6 and s["multi_apply_adjacent"] == 6
          and s["multi_apply_with_speed"] == 0
          and s["multi_apply_order"] == {"ascending": 6, "caster_first": 0},
          "THE BATCH ORDER: every speed word after the last apply, 43 of 43; the 6 "
          "two-apply batches (the hero's 348) adjacent 6 of 6, ASCENDING by agent id 6 of "
          "6 with the caster's own apply first 0 of 6, and none with a speed word -- the "
          "composed rule is two OBSERVED halves", f"{s['applies_before_speeds']} "
          f"{len(s['multi_apply'])} {s['multi_apply_adjacent']} {s['multi_apply_with_speed']} "
          f"{s['multi_apply_order']}")
    mw = s["multi_word_by_kind"]
    check(mw == {"ally": {"batches": 14, "ascending": 14, "own_word": 14, "caster_first": 0,
                          "caster_lowest": 0},
                 "foe": {"batches": 8, "ascending": 8, "own_word": 8, "caster_first": 0,
                         "caster_lowest": 0},
                 "observer": {"batches": 17, "ascending": 17, "own_word": 16,
                              "caster_first": 16, "caster_lowest": 16}},
          "THE WORDS ASCEND BY AGENT ID, 39 of 39 multi-word batches over every caster "
          "kind; the caster's own word is first ONLY when the caster is the lowest id -- "
          "the observer's 16 of 16 (lowest in every one), the team-mates' 0 of 14, the "
          "foes' 0 of 8 (the review's EV-2: the first cut read 'wearer first' off the "
          "observer's batches alone)", f"{mw}")
    check(s["own_multi_speed"] == 17 and s["own_multi_speed_with_word"] == 16
          and s["own_multi_speed_wearer_first"] == 16,
          "the observer's own word leads its 16 multi-word batches (the 17th is a re-cast "
          "over an open shout with no own word, 56.5) -- consistent with ascending id, "
          "not evidence for wearer-first", f"{s['own_multi_speed']} "
          f"{s['own_multi_speed_with_word']} {s['own_multi_speed_wearer_first']}")
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
