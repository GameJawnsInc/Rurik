"""test_condhit -- an ATTACK skill's own condition rides the HIT: a strike that misses or is
blocked inflicts nothing (RANGERPRE-S22, 2026-10-07; studies/presearing/RANGERPRE.md
section 5, found by S14's reviewer).

    python toolkit/authsrv/test_condhit.py

WHAT RETAIL SENDS (OBSERVED, one miss and three controls on one connection). On the Isle
capture 20260917T224104, connection :62557 (build 38888, map 280, observer 25), the observer
sits under a live Blind (479) episode from 347.485 to 356.488 and presses Jagged Strike (782,
"If Jagged Strike hits, your target suffers from Bleeding") at agent 117, whose status word
carries no bleeding bit. The completion batch at 349.147 is exactly E5, [46, 25, 0],
[38, 117, 25, 3], E3 -- the miss word and NOTHING naming 117: no word, no 0x005C chain step,
no [6, 117, 23], no 0x00F1, no [44]. The same skill on the same foe once the Blind is gone
(357.240, 395.754, 442.328) lands its word with [6, 117, 23], 0x00F1 [117, 0x83] (the bleeding
bit newly set) and [44, 117, ..], 3 of 3. Section 1 re-derives every literal from the bytes.
THE BLOCK has no retail witness (no attack skill is blocked on any live tape) and rests on
WIKI: GWW "Hit" rev 2721374, "Any time an attack is blocked or misses, there is no hit".

Ours, until 2026-10-07, applied the skill's condition at all four attack-skill sites whatever
the strike did -- the knock-down and the random condition were landed-gated, the condition
was not -- so a Blind-missed or blocked Sever Artery still bled the foe. Section 2 is the
server against retail's literals (the Blinded player's Jagged Strike batch, verbatim), 3 the
player's melee strike (Sever Artery: the triage's repro, and Gash after it), 4 the controls
that must NOT move (a spell's and a non-attack's condition under Blind and a block), 5 the
player's skill shot, 6 a body's melee attack skill and 7 a body's skill shot. 8 is the
known-bad arm, --no-condition-needs-hit, at every site; 9 the flag and the four sites in the
source.

Section 1 needs the vault's captures (a declared skip on a machine with no captures/live; a
vault with captures but not this one dies loudly in require_dir). Sections 2-8 need the
vault's `skills` rows (VAULT-ONLY, skilltable.py --emit-content: without them no skill is an
attack skill and the gate has nothing to gate) and declare a skip on a machine with no
vault/content DIRECTORY; a content directory that does not give 382, 392 and 782 their
attack type is a FAIL, not a skip. Section 9 runs anywhere.
"""
import argparse
import ast
import contextlib
import io
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

# Floor from the green run of 2026-10-07 on a machine with NO vault (RURIK_VAULT at an empty
# directory; sections 1-8 declared skips): 4. With the vault: 28.
LEDGER = checks.Ledger("an attack skill's condition rides the hit", floor=4)
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
FOE = 10
BLEED, BLIND, CRIPPLE, DEEP, CRACKED, BURN = 478, 479, 481, 482, 2077, 480
SEVER, GASH, PIN_DOWN, JAGGED = 382, 384, 392, 782
SPELL, NONATTACK = 2059, 424            # a tracked hand-row spell (Cracked Armor) and a
                                        # non-attack (Blind) -- 424's row is vault content
FLESHY_FILE = 141274                    # test_condimmune's fleshy model file
OP_E5, OP_E3, OP_CHAIN, OP_STATUS = 0x00E5, 0x00E3, 0x005C, 0x00F1
OP_INT, OP_INT_T, OP_FLOAT, OP_FLOAT_T, OP_APPLY = 0x009F, 0x00A0, 0x00A2, 0x00A3, 0x0042

# ---- retail's literals (OBSERVED; section 1 re-derives every one) ----------------------
WITNESS = ("20260917T224104", "10.0.0.210:62557->44.217.41.117:80")
OBSERVER, VICTIM = 25, 117
MISS_AT = 349.147                       # the E5 batch of the Blind-missed Jagged Strike
MISS_BATCH = [("E5", JAGGED), ("CLOSE46",), ("FAIL", 3), ("E3", JAGGED)]
COND_TOKENS = [("ADD", 23), ("BLEEDBIT",), ("REGEN",)]          # what a landed one adds
# Every Jagged Strike E5 batch on 117: (t, tokens). The three after the miss land and bleed.
JAGGED_ON_117 = [
    (349.147, MISS_BATCH),
    (357.240, [("E5", JAGGED), ("CLOSE46",), ("CHAIN",), ("VISUAL",), ("WORD",),
               ("ADD", 23), ("BLEEDBIT",), ("REGEN",), ("E3", JAGGED)]),
    (395.754, [("E5", JAGGED), ("CLOSE46",), ("CHAIN",), ("WORD",),
               ("ADD", 23), ("BLEEDBIT",), ("REGEN",), ("E3", JAGGED)]),
    (442.328, [("E5", JAGGED), ("CLOSE46",), ("CHAIN",), ("WORD",),
               ("ADD", 23), ("BLEEDBIT",), ("REGEN",), ("E3", JAGGED)]),
]                                       # (only 357.240 carries a [42, 117, 480] visual)
BATCH_S = 0.005


def token(op, f, attacker, target):
    """What one message contributes to an attack skill's completion on `target` by
    `attacker`, or None. `f` are the message's fields without the tape's header byte (what
    our send carries). The status word is reduced to whether it carries the bleeding bit
    (0x01): 117's 0x80 is an unrelated bit retail had set before the fight."""
    if op == OP_E5 and f[0] == attacker:
        return ("E5", f[1])
    if op == OP_E3 and f[0] == attacker:
        return ("E3", f[1])
    if op == OP_INT and f[0] == agents.GV_ATTACK_SKILL_FINISHED and f[1] == attacker:
        return ("CLOSE46",)
    if op == OP_INT_T and f[0] == agents.GV_ATTACK_FAIL and f[1] == target \
            and f[2] == attacker:
        return ("FAIL", f[3])
    if op == OP_FLOAT_T and f[0] in (16, 17) and f[1] == target and f[2] == attacker:
        return ("WORD",)
    if op == OP_CHAIN and f[0] == attacker and f[1] == target:
        return ("CHAIN",)
    if op == OP_INT and f[0] == 42 and f[1] == target:
        return ("VISUAL",)
    if op == OP_INT and f[0] == agents.PROP_AURA_ON and f[1] == target:
        return ("ADD", f[2])
    if op == OP_STATUS and f[0] == target:
        return ("BLEEDBIT",) if f[1] & 0x01 else ("STATUS-NO-BLEED",)
    if op == OP_FLOAT and f[0] == agents.GV_CHANGE_HEALTH_REGEN and f[1] == target:
        return ("REGEN",)
    if op == OP_APPLY and f[0] == target:
        return ("APPLY", f[1])
    return None


def tokens(msgs, attacker, target):
    return [x for x in (token(op, f, attacker, target) for op, f in msgs) if x]


def conditionish(toks):
    """The tokens that are a CONDITION on the target -- the four ways one can show."""
    return [x for x in toks if x[0] in ("ADD", "BLEEDBIT", "REGEN", "APPLY")]


# ---------------------------------------------------------------------------------------
def section_tape():
    print("\n1. retail's bytes: the Blind-missed Jagged Strike and its three controls")
    try:
        vaultpath.require_dir("captures", "live", why="the condition-needs-hit witness")
    except SystemExit as exc:
        LEDGER.skip("1. retail's bytes", str(exc).splitlines()[0])
        return
    import bufflog
    import deepwoundjoin
    import missjoin
    import spellhitjoin
    import tape
    codec = bufflog.Codec()
    stamp, conn = WITNESS
    cap = vaultpath.require_dir("captures", "live", stamp, why="the Isle capture")
    seq = deepwoundjoin.sequence(cap, conn, codec)
    files = {ch["connection"]: ch["file"] for ch in tape.channel_files(cap)}
    info = tape.client_version(cap, conn)
    me = spellhitjoin.observer_of(seq, spellhitjoin.c2s_of(cap, files[conn]))[0]
    check(info["build"] == 38888 and info["map_id"] == 280 and me == OBSERVER,
          f"fixture: {stamp} {conn} is build 38888 on map 280 and its observer is agent "
          f"{OBSERVER} (property 41 cross-checked against the answered presses)",
          (info, me))

    def batch_at(t):
        return [(op, v[1:]) for _i, tb, op, v in seq if abs(tb - t) <= BATCH_S]

    got = []
    for _i, t, op, v in seq:
        if op == OP_E5 and v[1] == OBSERVER and v[2] == JAGGED:
            toks = tokens(batch_at(t), OBSERVER, VICTIM)
            if any(x[0] in ("FAIL", "WORD") for x in toks):
                got.append((round(t, 3), toks))
    check(got == JAGGED_ON_117,
          "1a. every Jagged Strike completion on 117, by tokens: at 349.147 E5, [46], "
          "[38, 117, 25, 3], E3 and NOTHING else naming 117 -- no word, no chain step, no "
          "[6, 117, 23], no status word, no [44]; at 357.240, 395.754 and 442.328 the word "
          "with [6, 117, 23], the bleeding bit and [44] -- the condition rides the hit",
          got)

    windows = missjoin.blind_windows(cap, conn, codec)
    blind_at = [missjoin.under_blind(windows, OBSERVER, t) for t, _toks in got]
    check(blind_at == [True, False, False, False],
          "1b. the miss is BLIND's: the observer sits under a live 479 episode at the miss "
          "(bufflog's apply..close) and under none at the three hits", (blind_at, windows))

    status = 0
    for _i, t, op, v in seq:
        if t >= MISS_AT - BATCH_S:
            break
        if op == OP_STATUS and v[1] == VICTIM:
            status = v[2]
    after = [tok for _i, t, op, v in seq if MISS_AT - BATCH_S <= t <= MISS_AT + 1.0
             for tok in [token(op, v[1:], OBSERVER, VICTIM)] if tok]
    check(not status & 0x01 and conditionish(after) == [],
          "1c. the absence can be SEEN: 117's status word before the miss carries no "
          "bleeding bit (a Bleeding would have set it, as at 357.240), and in the second "
          "after the miss nothing puts a condition on 117", (hex(status), after))


# ---------------------------------------------------------------------------------------
def body(file_id=FLESHY_FILE, **kw):
    b = {"name": "foe", "dead": False, "died_at": 0.0, "health": 640.0, "max_health": 640.0,
         "last_hit": 0.0, "pos": (50.0, 0.0), "plane": 0, "armor_rating": 3.0,
         "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
         "effects": 0, "attacks_back": False, "skills": (), "skill_ready": [],
         "npc": {"file_id": file_id, "profession": 6, "level": 1}}
    b.update(kw)
    return b


def world(**bodies):
    st = {"agents": {int(k[1:]): v for k, v in bodies.items()}, "pos": (0.0, 0.0),
          "player_health": 480.0, "player_dead": False, "level": 20}
    authsrv.effect_table(st)
    authsrv.player_pools(st)
    return st


def collector():
    sent = []
    return sent, lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))


def conditions_on(st, agent_id):
    return sorted(ep["skill"] for ep in authsrv.effect_table(st).on_agent(agent_id))


def blind(st, agent_id):
    """A REAL Blind episode on the swinger -- blinded() reads it off the effect table."""
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.apply_condition(collector()[1], st, agent_id, BLIND, 60.0, 0, 1, 1)
    if BLIND not in conditions_on(st, agent_id):
        raise SystemExit(f"fixture: no Blind episode opened on agent {agent_id}")


@contextlib.contextmanager
def arm(blinded_roll=False, blocker=None, needs_hit=True):
    """The roll forced, the shape real: BLIND_MISS_CHANCE 1.0 (a blinded swinger misses
    every time -- the Blind itself is a real episode), a `block_chance` of 1.0 on
    `blocker` and 0 elsewhere, and the gate's flag."""
    saved = (authsrv.BLIND_MISS_CHANCE, authsrv.block_chance, authsrv.CONDITION_NEEDS_HIT)
    real_bc = authsrv.block_chance
    try:
        if blinded_roll:
            authsrv.BLIND_MISS_CHANCE = 1.0
        if blocker is not None:
            authsrv.block_chance = lambda s, a: 1.0 if a == blocker else real_bc(s, a)
        authsrv.CONDITION_NEEDS_HIT = needs_hit
        yield
    finally:
        authsrv.BLIND_MISS_CHANCE, authsrv.block_chance, authsrv.CONDITION_NEEDS_HIT = saved


def press(st, skill, target):
    """The player's own press -> cast_tick (the E5 brought forward, test_condimmune's
    recipe) -> projectile_tick (an arrow brought to its arrival): what it all sent."""
    sent, send = collector()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_skill_press([0, skill, 0, target], send, st, 1,
                                   authsrv.GAME_CMSG_USE_SKILL)
        sent.clear()
        for cast in st.get("pending_casts", ()):
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        for _ in range(3):
            authsrv.cast_tick(send, st, 1)
        for shot in st.get("player_projectiles") or ():
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
    return sent


def body_cast(st):
    """A hostile's land_skill (its cast completing), then its arrow's arrival."""
    sent, send = collector()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        for shot in st.get("body_projectiles") or ():
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
    return sent


def hostile_world(skill, weapon, pos):
    foe = {"name": "foe", "dead": False, "died_at": 0.0, "health": 600.0,
           "max_health": 600.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": 1.75,
           "effects": 0, "attacks_back": True, "skills": [[skill, 0.0, 3.0]],
           "skill_ready": [0.0], "casting": 0, "cast_target": PLAYER,
           "last_swing": time.time(), "weapon_item": weapon,
           "npc": {"profession": 1, "level": 10}}
    st = {"agents": {FOE: foe}, "pos": (0.0, 0.0), "player_health": 480.0,
          "player_dead": False}
    authsrv.effect_table(st)
    authsrv.player_pools(st)
    return st


def words(sent, attacker, target):
    return [v for op, v in sent if op == OP_FLOAT_T and v[0] in (16, 17)
            and v[1] == target and v[2] == attacker]


def fails(sent, attacker, target):
    return [v for op, v in sent if op == OP_INT_T and v[0] == agents.GV_ATTACK_FAIL
            and v[1] == target and v[2] == attacker]


def character(weapon=None):
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.apply_party_character(agents.WORLD.get("party", "slice"))
        if weapon:
            authsrv.apply_party_character({"player_weapon": weapon})


def section_player_witness():
    print("\n2. the server against retail's literals: the Blinded player's Jagged Strike")
    character("starter_daggers")
    st = world(a117=body())
    blind(st, PLAYER)
    with arm(blinded_roll=True):
        missed = tokens(press(st, JAGGED, 117), PLAYER, 117)
    check(missed == MISS_BATCH and conditions_on(st, 117) == [],
          "2a. VERBATIM: our Blinded player's Jagged Strike completes E5, [46], "
          "[38, 117, 1, 3], E3 and nothing else naming 117 -- retail's 349.147 batch token "
          "for token -- and 117 carries no condition", (missed, conditions_on(st, 117)))
    st = world(a117=body())
    hit = tokens(press(st, JAGGED, 117), PLAYER, 117)
    check(conditionish(hit) == COND_TOKENS and ("WORD",) in hit
          and conditions_on(st, 117) == [BLEED],
          "2b. CONTROL, the same press unblinded: the word, then [6, 117, 23], the bleeding "
          "bit and [44] -- retail's 357.240 condition tokens -- and Bleeding on 117",
          (hit, conditions_on(st, 117)))


def section_player_melee():
    print("\n3. the player's melee attack skill (Sever Artery, the slice's sword) -- "
          "the triage's repro")
    character()
    st = world(a22=body())
    sent = press(st, SEVER, 22)
    check(conditions_on(st, 22) == [BLEED] and len(words(sent, PLAYER, 22)) == 1
          and not fails(sent, PLAYER, 22),
          "3a. CONTROL: a landed Sever Artery -- one damage word, no fail word, Bleeding "
          "on the foe", (conditions_on(st, 22), sent))
    st = world(a22=body())
    blind(st, PLAYER)
    with arm(blinded_roll=True):
        sent = press(st, SEVER, 22)
    check(fails(sent, PLAYER, 22) == [[agents.GV_ATTACK_FAIL, 22, PLAYER, 3]]
          and not words(sent, PLAYER, 22) and conditions_on(st, 22) == []
          and conditionish(tokens(sent, PLAYER, 22)) == [],
          "3b. a BLIND miss: [38, 22, 1, 3], no damage word, and NO Bleeding -- no "
          "[6, 22, 23], no status word, no [44] (until 2026-10-07: Bleeding 478)",
          (conditions_on(st, 22), sent))
    st = world(a22=body())
    with arm(blocker=22):
        sent = press(st, SEVER, 22)
    check(fails(sent, PLAYER, 22) == [[agents.GV_ATTACK_FAIL, 22, PLAYER, 0]]
          and not words(sent, PLAYER, 22) and conditions_on(st, 22) == []
          and conditionish(tokens(sent, PLAYER, 22)) == [],
          "3c. a BLOCK: [38, 22, 1, 0], no damage word, and NO Bleeding (WIKI 'Hit': a "
          "blocked attack is no hit; until 2026-10-07: Bleeding 478)",
          (conditions_on(st, 22), sent))
    # 3d. what the defect did downstream: Gash reads the target's LIVE Bleeding
    with arm(blocker=22):
        press(st, SEVER, 22)
    gash = press(st, GASH, 22)
    check(len(words(gash, PLAYER, 22)) == 1 and conditions_on(st, 22) == [],
          "3d. Gash after the blocked Sever Artery lands PLAIN -- no Deep Wound, since "
          "the block left no Bleeding to gate it on (before: the phantom Bleeding fired "
          "Gash's Deep Wound)", (conditions_on(st, 22), gash))


def section_unmoved():
    print("\n4. what must NOT move: a spell's and a non-attack's condition under Blind and "
          "a block")
    character()
    for sid, cond, what in ((SPELL, CRACKED, "a SPELL with a word (2059, Cracked Armor)"),
                            (NONATTACK, BLIND, "a NON-attack, non-spell (424, Blind)")):
        if authsrv._is_attack_skill(sid) or authsrv.skill_condition(sid, 12) is None \
                or authsrv.skill_condition(sid, 12)[0] != cond:
            check(False, f"4. fixture: {sid} is a non-attack inflicting {cond}",
                  (authsrv._is_attack_skill(sid), authsrv.skill_condition(sid, 12)))
            continue
        st = world(a22=body())
        blind(st, PLAYER)
        with arm(blinded_roll=True, blocker=22):
            sent = press(st, sid, 22)
        check(conditions_on(st, 22) == [cond] and not fails(sent, PLAYER, 22)
              and (sid != SPELL or len(words(sent, PLAYER, 22)) == 1),
              f"4. {what}, cast by a BLINDED player at a foe that blocks every attack: no "
              f"fail word{', its word lands' if sid == SPELL else ''} and the condition "
              f"lands -- Blind and a block reach attacks, not spells (WIKI 'Block')",
              (conditions_on(st, 22), sent))


def section_player_shot():
    print("\n5. the player's skill shot (Pin Down, a bow): the strike at the arrival")
    character("starter_bow")
    st = world(a22=body(pos=(800.0, 0.0)))
    sent = press(st, PIN_DOWN, 22)
    check(conditions_on(st, 22) == [CRIPPLE] and len(words(sent, PLAYER, 22)) == 1
          and [op for op, _v in sent].count(0x00A7) == 1,
          "5a. CONTROL: the arrow arrives (0x00A7), its word lands and the foe is Crippled",
          (conditions_on(st, 22), sent))
    st = world(a22=body(pos=(800.0, 0.0)))
    blind(st, PLAYER)
    with arm(blinded_roll=True):
        sent = press(st, PIN_DOWN, 22)
    check(fails(sent, PLAYER, 22) == [[agents.GV_ATTACK_FAIL, 22, PLAYER, 3]]
          and not words(sent, PLAYER, 22) and conditions_on(st, 22) == [],
          "5b. a BLIND miss at the arrival: [38, 22, 1, 3] and NO Crippled "
          "(land_player_skill_shot; until 2026-10-07: Crippled 481)",
          (conditions_on(st, 22), sent))
    st = world(a22=body(pos=(800.0, 0.0)))
    with arm(blocker=22):
        sent = press(st, PIN_DOWN, 22)
    check(fails(sent, PLAYER, 22) == [[agents.GV_ATTACK_FAIL, 22, PLAYER, 0]]
          and not words(sent, PLAYER, 22) and conditions_on(st, 22) == [],
          "5c. a BLOCK at the arrival: [38, 22, 1, 0] and NO Crippled",
          (conditions_on(st, 22), sent))


def section_body_melee():
    print("\n6. a body's melee attack skill (land_skill: a hostile's Sever Artery at the "
          "player)")
    st = hostile_world(SEVER, "starter_sword", (60.0, 0.0))
    sent = body_cast(st)
    check(conditions_on(st, PLAYER) == [BLEED] and len(words(sent, FOE, PLAYER)) == 1,
          "6a. CONTROL: the hostile's strike lands its word and the player bleeds",
          (conditions_on(st, PLAYER), sent))
    st = hostile_world(SEVER, "starter_sword", (60.0, 0.0))
    blind(st, FOE)
    with arm(blinded_roll=True):
        sent = body_cast(st)
    check(fails(sent, FOE, PLAYER) == [[agents.GV_ATTACK_FAIL, PLAYER, FOE, 3]]
          and not words(sent, FOE, PLAYER) and conditions_on(st, PLAYER) == []
          and not [v for op, v in sent if op == OP_APPLY],
          "6b. the BLINDED hostile misses: [38, 1, 10, 3], no word, no 0x0042 and no "
          "Bleeding on the player (until 2026-10-07: Bleeding 478)",
          (conditions_on(st, PLAYER), sent))
    st = hostile_world(SEVER, "starter_sword", (60.0, 0.0))
    with arm(blocker=PLAYER):
        sent = body_cast(st)
    check(fails(sent, FOE, PLAYER) == [[agents.GV_ATTACK_FAIL, PLAYER, FOE, 0]]
          and not words(sent, FOE, PLAYER) and conditions_on(st, PLAYER) == []
          and not [v for op, v in sent if op == OP_APPLY],
          "6c. the player BLOCKS it: [38, 1, 10, 0] and no Bleeding",
          (conditions_on(st, PLAYER), sent))


def section_body_shot():
    print("\n7. a body's skill shot (land_body_skill_shot: a hostile archer's Pin Down at "
          "the player)")
    st = hostile_world(PIN_DOWN, "hostile_bow", (600.0, 0.0))
    sent = body_cast(st)
    check(conditions_on(st, PLAYER) == [CRIPPLE] and len(words(sent, FOE, PLAYER)) == 1
          and [op for op, _v in sent].count(0x00A7) == 1,
          "7a. CONTROL: the arrow arrives, its word lands and the player is Crippled",
          (conditions_on(st, PLAYER), sent))
    st = hostile_world(PIN_DOWN, "hostile_bow", (600.0, 0.0))
    blind(st, FOE)
    with arm(blinded_roll=True):
        sent = body_cast(st)
    check(fails(sent, FOE, PLAYER) == [[agents.GV_ATTACK_FAIL, PLAYER, FOE, 3]]
          and not words(sent, FOE, PLAYER) and conditions_on(st, PLAYER) == [],
          "7b. the BLINDED archer's arrow misses: [38, 1, 10, 3] and no Crippled "
          "(until 2026-10-07: Crippled 481)", (conditions_on(st, PLAYER), sent))
    st = hostile_world(PIN_DOWN, "hostile_bow", (600.0, 0.0))
    with arm(blocker=PLAYER):
        sent = body_cast(st)
    check(fails(sent, FOE, PLAYER) == [[agents.GV_ATTACK_FAIL, PLAYER, FOE, 0]]
          and not words(sent, FOE, PLAYER) and conditions_on(st, PLAYER) == [],
          "7c. the player BLOCKS the arrow: [38, 1, 10, 0] and no Crippled",
          (conditions_on(st, PLAYER), sent))


def section_known_bad():
    print("\n8. KNOWN-BAD ARM: --no-condition-needs-hit, at every site")
    character("starter_daggers")
    st = world(a117=body())
    blind(st, PLAYER)
    with arm(blinded_roll=True, needs_hit=False):
        missed = tokens(press(st, JAGGED, 117), PLAYER, 117)
    check(missed[:3] == MISS_BATCH[:3] and conditionish(missed) == COND_TOKENS
          and missed != MISS_BATCH and conditions_on(st, 117) == [BLEED],
          "8a. the flag off: the Blinded Jagged Strike's batch carries the miss word AND "
          "[6, 117, 23], the bleeding bit and [44] -- the pre-fix server, which retail's "
          "349.147 refutes", missed)
    got = {}
    character()
    st = world(a22=body())
    with arm(blocker=22, needs_hit=False):
        press(st, SEVER, 22)
    got["melee blocked"] = conditions_on(st, 22)
    character("starter_bow")
    st = world(a22=body(pos=(800.0, 0.0)))
    blind(st, PLAYER)
    with arm(blinded_roll=True, needs_hit=False):
        press(st, PIN_DOWN, 22)
    got["player shot missed"] = conditions_on(st, 22)
    st = hostile_world(SEVER, "starter_sword", (60.0, 0.0))
    with arm(blocker=PLAYER, needs_hit=False):
        body_cast(st)
    got["body melee blocked"] = conditions_on(st, PLAYER)
    st = hostile_world(PIN_DOWN, "hostile_bow", (600.0, 0.0))
    blind(st, FOE)
    with arm(blinded_roll=True, needs_hit=False):
        body_cast(st)
    got["body shot missed"] = conditions_on(st, PLAYER)
    check(got == {"melee blocked": [BLEED], "player shot missed": [CRIPPLE],
                  "body melee blocked": [BLEED], "body shot missed": [CRIPPLE]},
          "8b. and each of the other three sites reproduces the defect under the flag: a "
          "blocked Sever Artery bleeds, a missed Pin Down cripples, a body's blocked strike "
          "and its missed arrow both land their condition on the player", got)


def section_source():
    print("\n9. the flag, main()'s wiring and the four sites in the source")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    check(ap.parse_args([]).no_condition_needs_hit is False
          and ap.parse_args(["--no-condition-needs-hit"]).no_condition_needs_hit is True
          and authsrv.CONDITION_NEEDS_HIT is True,
          "9a. --no-condition-needs-hit parses (default off) and the gate ships ON")

    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    wiring = [n for n in ast.walk(funcs["main"]) if isinstance(n, ast.If)
              and isinstance(n.test, ast.Attribute) and n.test.attr == "no_condition_needs_hit"]
    flipped = {}
    for flag in (True, False):
        saved = authsrv.CONDITION_NEEDS_HIT
        try:
            mod = ast.Module(body=wiring, type_ignores=[])
            ast.fix_missing_locations(mod)
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(mod, authsrv.__file__, "exec"),            # noqa: S102
                     authsrv.__dict__, {"a": argparse.Namespace(no_condition_needs_hit=flag)})
            flipped[flag] = authsrv.CONDITION_NEEDS_HIT
        finally:
            authsrv.CONDITION_NEEDS_HIT = saved
    check(len(wiring) == 1 and flipped == {True: False, False: True},
          "9b. main()'s `if a.no_condition_needs_hit:` block, lifted out of the source and "
          "RUN against authsrv's own globals, flips the module bool -- a block without its "
          "`global` would leave it True -- and leaves it alone when the flag is off",
          (len(wiring), flipped))

    sites = {}
    for name in ("cast_tick", "land_player_skill_shot", "land_body_skill_shot", "land_skill"):
        sites[name] = sum(1 for n in ast.walk(funcs[name]) if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Name)
                          and n.func.id == "attack_condition_lands")
    check(sites == {"cast_tick": 1, "land_player_skill_shot": 1,
                    "land_body_skill_shot": 1, "land_skill": 1},
          "9c. each of the four attack-skill condition sites asks attack_condition_lands "
          "exactly once (sections 3, 5, 6 and 7 drive each of them)", sites)
    with contextlib.redirect_stdout(io.StringIO()):
        rule = {r: authsrv.attack_condition_lands(r, 1, 2, 0, "t")
                for r in ("landed", "missed", "blocked", None, "failed")}
    check(rule == {"landed": True, "missed": False, "blocked": False, None: False,
                   "failed": False},
          "9d. the rule: only 'landed' lets the condition follow; 'missed', 'blocked', a "
          "None (a dead target, the legacy interval-gated strike) and 'failed' do not",
          rule)


def main():
    print("test_condhit -- an attack skill's condition rides the hit (RANGERPRE-S22)")
    t0 = time.time()
    section_tape()
    try:
        vaultpath.require_dir("content", why="the skills rows that make 382 an attack")
        have_rows = True
    except SystemExit as exc:
        have_rows = False
        LEDGER.skip("2-8. the server sections", str(exc).splitlines()[0])
    if have_rows:
        types = {s: authsrv._is_attack_skill(s) for s in (SEVER, PIN_DOWN, JAGGED, GASH)}
        check(all(types.values()),
              "fixture: the vault's skills rows make 382, 384, 392 and 782 ATTACK skills",
              types)
        saved_pc = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.PLAYER_SWING_DAMAGE,
                    authsrv.WEAPON_ATTACK_SPEED, authsrv.ATTACK_INTERVAL,
                    authsrv.PARTY_SKILLBAR, agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
                    agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS,
                    authsrv.skill_cost)
        try:
            authsrv.skill_cost = lambda sid: (0, 0)            # the gate, not the price
            section_player_witness()
            section_player_melee()
            section_unmoved()
            section_player_shot()
            section_body_melee()
            section_body_shot()
            section_known_bad()
        finally:
            (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR,
             agents.PLAYER_LEVEL, agents.PLAYER_HEALTH, agents.PLAYER_ATTRIBUTE_RANKS,
             agents.PLAYER_ATTRIBUTE_POINTS, authsrv.skill_cost) = saved_pc
    section_source()
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
