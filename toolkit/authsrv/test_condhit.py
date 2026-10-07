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
The event is not new to the repo: studies/daggers/FINDINGS.md DAGGERS-F16 (RUN-DAGGERS-2,
2026-09-17) read the same batch and its three controls for the CHAIN (a missed lead sets
nothing); what S22 reads in it is the other half, that no Bleeding followed.
WHAT THAT WITNESS COVERS: the player's MELEE attack skill under Blind, n = 1. No live tape
shows an attack skill blocked, a skill SHOT missed, or a body's attack skill missed (every
attack-fail word joined to an attack-skill activation, 24, is the observer's own melee dagger
skill), so THE BLOCK at every site and the miss at the arrow's arrival and the
two body sites rest on WIKI: GWW "Hit" rev 2721374, "Any time an attack is blocked or misses,
there is no hit".

Ours, until 2026-10-07, applied the skill's condition at all four attack-skill sites whatever
the strike did -- the knock-down and the random condition were landed-gated, the condition
was not -- so a Blind-missed or blocked Sever Artery still bled the foe. Section 2 is the
server against retail's literals (the Blinded player's Jagged Strike batch, verbatim), 3 the
player's melee strike (Sever Artery: the triage's repro, and Gash after it), 4 the controls
that must NOT move (a spell's and a non-attack's condition under Blind and a block), 5 the
player's skill shot, 6 a body's melee attack skill and 7 a body's skill shot. 8 is the
known-bad arm, --no-condition-needs-hit, at every site; 9 the flag and the four sites in the
source.

RANGERPRE-S23 and S24 (2026-10-07, the two defects S22 found in passing; the banner at
authsrv.BLIND_MISS_SKILL_CLOSE). S23: a BODY's Blind-missed attack skill closed with the
plain swing's [1, body, 0]; retail's close follows the ACTION -- on the witness connection
the observer's two attack-skill misses (349.147 Jagged Strike, 443.448 the 775 dual) close
[46] and its two plain-swing misses (433.145, 434.310) close [1] (1d re-derives it). The
body's [46] is RECONSTRUCTION: both misses are the player's. S24: a Blinded body's attack
skill on another BODY never rolled the miss (WIKI 'Blind' rev 2667383, 'Hit' rev 2721374).
Section 10 is the fix at both sites and in both directions, 11 the two known-bad arms
(--no-blind-miss-skill-close, --no-body-skill-blind) as differentials, 12 the flags, main()'s
wiring and the two call sites in the source. Every check in 10-12 is red on the server
before S23 / S24 (ab39c182).

Section 1 needs the vault's captures (a declared skip on a machine with no captures/live; a
vault with captures but not this one dies loudly in require_dir). Sections 2-8 need the
vault's `skills` rows (VAULT-ONLY, skilltable.py --emit-content: without them no skill is an
attack skill and the gate has nothing to gate) and declare a skip on a machine with no
vault/content DIRECTORY; a content directory that does not give 382, 392 and 782 their
attack type is a FAIL, not a skip. Sections 10-11 need the same rows. Sections 9 and 12 run
anywhere.
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
# directory; sections 1-8 declared skips): 4. With the vault: 28. RANGERPRE-S23 / S24, the
# same day: bare 7 (sections 9 and 12), with the vault 38.
LEDGER = checks.Ledger("an attack skill's condition rides the hit", floor=7)
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
# 357.240's ("MAXHP",) is 0x009F [42, 117, 480], MAXHP-1 / RANGERPRE-S10: the body's maximum
# declared immediately before the observer's FIRST landed word on it (117 was created at
# 332.484 and the 349.147 strike missed); it is the only property 42 on 117 on the tape.
HIT_357 = [("E5", JAGGED), ("CLOSE46",), ("CHAIN",), ("MAXHP",), ("WORD",),
           ("ADD", 23), ("BLEEDBIT",), ("REGEN",), ("E3", JAGGED)]
JAGGED_ON_117 = [
    (349.147, MISS_BATCH),
    (357.240, HIT_357),
    (395.754, [("E5", JAGGED), ("CLOSE46",), ("CHAIN",), ("WORD",),
               ("ADD", 23), ("BLEEDBIT",), ("REGEN",), ("E3", JAGGED)]),
    (442.328, [("E5", JAGGED), ("CLOSE46",), ("CHAIN",), ("WORD",),
               ("ADD", 23), ("BLEEDBIT",), ("REGEN",), ("E3", JAGGED)]),
]                                       # (only the first landed word carries MAXHP-1's 42)
BATCH_S = 0.005
# RANGERPRE-S23: every Blind miss ([38, T, 25, 3]) by the observer on the witness connection,
# as (t, the skills of the observer's E5s in its batch or None, the observer's closes in its
# batch) -- the close is the ACTION's: [46] beside an attack skill, [1] beside a plain swing.
MISS_CLOSES = [(349.147, [JAGGED], [46]), (433.145, None, [1]), (434.31, None, [1]),
               (443.448, [775], [46])]
ALLY = 30                               # a party body (RANGERPRE-S24's victim or caster)


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
    if op == OP_INT and f[0] == agents.PROP_HEALTH_MAX and f[1] == target:
        return ("MAXHP",)                     # MAXHP-1: the maximum, before a first word
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

    misses = [(round(r["t"], 3),
               [v[2] for _i, tb, op, v in seq if op == OP_E5 and v[1] == OBSERVER
                and abs(tb - r["t"]) <= BATCH_S] or None, r["closes"])
              for r in missjoin.fails(seq, windows, OBSERVER)
              if r["attacker"] == OBSERVER and r["reason"] == 3]
    check(misses == MISS_CLOSES,
          "1d. RANGERPRE-S23's evidence: the observer's every Blind miss on this connection "
          "rides its own close, and the close is the ACTION's -- [46] beside the two attack "
          "skills' E5s (782 at 349.147, the 775 dual at 443.448), [1] beside the two plain "
          "swings (433.145, 434.310) -- never the outcome's", misses)


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
def arm(blinded_roll=False, blocker=None, needs_hit=True, skill_close=True,
        body_blind=True):
    """The roll forced, the shape real: BLIND_MISS_CHANCE 1.0 (a blinded swinger misses
    every time -- the Blind itself is a real episode), a `block_chance` of 1.0 on
    `blocker` and 0 elsewhere, and the gates' flags (S22's CONDITION_NEEDS_HIT, S23's
    BLIND_MISS_SKILL_CLOSE, S24's BODY_SKILL_BLIND).

    Each flag is read through getattr and put back exactly as found (removed again if the
    module had none), so this file run against a server WITHOUT a gate -- 1a678280 for
    S22, ab39c182 for S23 / S24 -- still reaches the server sections and goes red on their
    checks rather than dying on an AttributeError at the first press; sections 9 and 12
    are where a missing bool and flag are named."""
    missing = object()
    saved = (authsrv.BLIND_MISS_CHANCE, authsrv.block_chance)
    gates = {"CONDITION_NEEDS_HIT": needs_hit, "BLIND_MISS_SKILL_CLOSE": skill_close,
             "BODY_SKILL_BLIND": body_blind}
    saved_gates = {k: getattr(authsrv, k, missing) for k in gates}
    real_bc = authsrv.block_chance
    try:
        if blinded_roll:
            authsrv.BLIND_MISS_CHANCE = 1.0
        if blocker is not None:
            authsrv.block_chance = lambda s, a: 1.0 if a == blocker else real_bc(s, a)
        for k, v in gates.items():
            setattr(authsrv, k, v)
        yield
    finally:
        authsrv.BLIND_MISS_CHANCE, authsrv.block_chance = saved
        for k, v in saved_gates.items():
            if v is missing:
                authsrv.__dict__.pop(k, None)
            else:
                setattr(authsrv, k, v)


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


def body_cast(st, caster=FOE):
    """A body's land_skill (its cast completing), then its arrow's arrival."""
    sent, send = collector()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.land_skill(send, st, caster, st["agents"][caster], 1)
        for shot in st.get("body_projectiles") or ():
            shot["arrives_at"] -= 30.0
        authsrv.projectile_tick(send, st, 1)
    return sent


def caster_row(skill, weapon, pos, allegiance, target):
    return {"name": "foe", "dead": False, "died_at": 0.0, "health": 600.0,
            "max_health": 600.0, "last_hit": 0.0, "pos": pos, "plane": 0,
            "allegiance": allegiance, "attack_speed": 1.75,
            "effects": 0, "attacks_back": True, "skills": [[skill, 0.0, 3.0]],
            "skill_ready": [0.0], "casting": 0, "cast_target": target,
            "last_swing": time.time(), "weapon_item": weapon,
            "npc": {"profession": 1, "level": 10}}


def hostile_world(skill, weapon, pos):
    st = {"agents": {FOE: caster_row(skill, weapon, pos, agents.ALLEGIANCE_HOSTILE,
                                     PLAYER)},
          "pos": (0.0, 0.0), "player_health": 480.0, "player_dead": False}
    authsrv.effect_table(st)
    authsrv.player_pools(st)
    return st


def body_world(skill, weapon, pos, party_caster=False):
    """RANGERPRE-S24: a caster aiming `skill` at a fleshy BODY, neither of them the player
    -- the hostile FOE at the party body ALLY, or (party_caster) ALLY at FOE. Returns
    (state, caster, victim)."""
    caster, victim = (ALLY, FOE) if party_caster else (FOE, ALLY)
    side = agents.ALLEGIANCE_PLAYER if party_caster else agents.ALLEGIANCE_HOSTILE
    other = agents.ALLEGIANCE_HOSTILE if party_caster else agents.ALLEGIANCE_PLAYER
    st = {"agents": {caster: caster_row(skill, weapon, pos, side, victim),
                     victim: body(pos=(0.0, 60.0), allegiance=other)},
          "pos": (0.0, 0.0), "player_health": 480.0, "player_dead": False}
    authsrv.effect_table(st)
    authsrv.player_pools(st)
    return st, caster, victim


def plain_swing(st, attacker, target):
    """A body's PLAIN swing landing (land_swing, skill_id None) -- the S23 control."""
    sent, send = collector()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.land_swing(send, st, attacker, st["agents"][attacker], 1, target_id=target)
    return sent


def closes(sent, attacker):
    """The attacker's own swing closes in `sent`, wire order: 1 (a plain swing's) and 46
    (an attack skill's)."""
    return [v[0] for op, v in sent if op == OP_INT and v[1] == attacker
            and v[0] in (agents.GV_MELEE_ATTACK_FINISHED, agents.GV_ATTACK_SKILL_FINISHED)]


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
    # The body's maximum not yet declared to the client (MAXHP-1's tracker stale, as
    # retail's 117 was before the observer's first landed word on it).
    st = world(a117=body(max_declared_on_hit=None))
    hit = tokens(press(st, JAGGED, 117), PLAYER, 117)
    check(hit == HIT_357 and conditions_on(st, 117) == [BLEED],
          "2b. CONTROL, VERBATIM too: the same press unblinded, on a body whose maximum the "
          "client has not been told, completes with retail's 357.240 batch token for token "
          "-- E5, [46], the chain step, MAXHP-1's [42], the word, then [6, 117, 23], the "
          "bleeding bit and [44], E3 -- and Bleeding on 117",
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
              f"lands -- Blind's 90% miss and a block reach attacks only (WIKI 'Blind' rev "
              f"2667383: a projectile spell may stray, unmodelled; 'Block' rev 2740767: no "
              f"effect against spells)",
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
    """Every name the gate adds is read through getattr / a parse that cannot raise, so a
    server without the gate (1a678280) reports 9a-9d RED rather than dying here."""
    print("\n9. the flag, main()'s wiring and the four sites in the source")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parsed = (ap.parse_args([]).no_condition_needs_hit,
                      ap.parse_args(["--no-condition-needs-hit"]).no_condition_needs_hit)
    except (SystemExit, AttributeError) as exc:     # an unknown flag: argparse exits 2
        parsed = ("refused", repr(exc))
    gate = getattr(authsrv, "CONDITION_NEEDS_HIT", "absent")
    check(parsed == (False, True) and gate is True,
          "9a. --no-condition-needs-hit parses (default off) and the gate ships ON",
          (parsed, gate))

    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    wiring = [n for n in ast.walk(funcs["main"]) if isinstance(n, ast.If)
              and isinstance(n.test, ast.Attribute) and n.test.attr == "no_condition_needs_hit"]
    flipped = {}
    missing = object()
    for flag in (True, False):
        saved = getattr(authsrv, "CONDITION_NEEDS_HIT", missing)
        try:
            mod = ast.Module(body=wiring, type_ignores=[])
            ast.fix_missing_locations(mod)
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(mod, authsrv.__file__, "exec"),            # noqa: S102
                     authsrv.__dict__, {"a": argparse.Namespace(no_condition_needs_hit=flag)})
            flipped[flag] = getattr(authsrv, "CONDITION_NEEDS_HIT", "absent")
        finally:
            if saved is missing:
                authsrv.__dict__.pop("CONDITION_NEEDS_HIT", None)
            else:
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
    rule_fn = getattr(authsrv, "attack_condition_lands", None)
    with contextlib.redirect_stdout(io.StringIO()):
        rule = {r: rule_fn(r, 1, 2, 0, "t")
                for r in ("landed", "missed", "blocked", None, "failed")} if rule_fn else None
    check(rule == {"landed": True, "missed": False, "blocked": False, None: False,
                   "failed": False},
          "9d. the rule: only 'landed' lets the condition follow; 'missed' and 'blocked' do "
          "not (the evidence), and neither do a None -- a dead target, or "
          "--legacy-attack-finish's interval-gated strike that never happened -- and "
          "'failed' (RECONSTRUCTION: no strike read as no hit)",
          rule)


def blinded_cast(build):
    """`build()` -> (state, caster, victim); the caster Blinded (a real episode, the roll
    forced) and its cast landed. Returns (sent, state, caster, victim)."""
    st, who, tid = build()
    blind(st, who)
    sent = body_cast(st, who)
    return sent, st, who, tid


def section_body_close():
    print("\n10. RANGERPRE-S23 / S24: a BODY's attack skill under Blind -- the close is the "
          "action's, and a body's skill on a body rolls the miss")
    # 10a. S23 at the player: land_skill -> land_swing's player branch.
    with arm(blinded_roll=True):
        skill, st, _w, _t = blinded_cast(
            lambda: (hostile_world(SEVER, "starter_sword", (60.0, 0.0)), FOE, PLAYER))
        st2 = hostile_world(SEVER, "starter_sword", (60.0, 0.0))
        blind(st2, FOE)
        plain = plain_swing(st2, FOE, PLAYER)
    check(tokens(skill, FOE, PLAYER) == MISS_BATCH[1:3] and closes(skill, FOE) == [46]
          and closes(plain, FOE) == [1]
          and fails(plain, FOE, PLAYER) == [[agents.GV_ATTACK_FAIL, PLAYER, FOE, 3]],
          "10a. S23 at the player: the Blinded hostile's Sever Artery closes [46, 10, 0] "
          "then [38, 1, 10, 3] -- retail's 349.147 tokens less the observer's own E5 / E3 "
          "(1d: the close is the action's) -- and its PLAIN swing, the control, still "
          "closes [1] then [38, 1, 10, 3] (until 2026-10-07 the skill closed [1] too)",
          (tokens(skill, FOE, PLAYER), closes(skill, FOE), plain))
    # 10b / 10c. S24 (and S23 at land_swing_on_body): a body's melee attack skill on a body.
    for tag, party in (("10b", False), ("10c", True)):
        def build(party=party):
            return body_world(SEVER, "starter_sword", (60.0, 0.0), party_caster=party)
        with arm(blinded_roll=True):
            missed, st, who, tid = blinded_cast(build)
        miss_conds = conditions_on(st, tid)
        st, who, tid = build()
        landed = body_cast(st, who)
        check(tokens(missed, who, tid) == MISS_BATCH[1:3] and not words(missed, who, tid)
              and miss_conds == [] and conditionish(tokens(missed, who, tid)) == []
              and closes(landed, who) == [46] and len(words(landed, who, tid)) == 1
              and conditions_on(st, tid) == [BLEED],
              f"{tag}. S24: the Blinded {'party body' if party else 'hostile'} {who}'s Sever "
              f"Artery at the {'hostile' if party else 'party body'} {tid} MISSES -- "
              f"[46, {who}, 0] (S23's close) then [38, {tid}, {who}, 3], no word and no "
              f"Bleeding -- where the unblinded control closes [46], lands its word and "
              f"bleeds {tid} (until 2026-10-07 the Blinded strike always landed: "
              f"land_swing_on_body rolled for a plain swing only)",
              (tokens(missed, who, tid), miss_conds, closes(landed, who),
               conditions_on(st, tid)))
    # 10d. S24 on a body's SKILL SHOT at a body: the arrival rolls; no close either way.
    with arm(blinded_roll=True):
        missed, st, who, tid = blinded_cast(
            lambda: body_world(PIN_DOWN, "hostile_bow", (600.0, 0.0)))
    miss_conds = conditions_on(st, tid)
    st, who, tid = body_world(PIN_DOWN, "hostile_bow", (600.0, 0.0))
    landed = body_cast(st, who)
    check(fails(missed, who, tid) == [[agents.GV_ATTACK_FAIL, tid, who, 3]]
          and not words(missed, who, tid) and miss_conds == []
          and [op for op, _v in missed].count(0x00A7) == 1 and closes(missed, who) == []
          and len(words(landed, who, tid)) == 1 and conditions_on(st, tid) == [CRIPPLE]
          and closes(landed, who) == [],
          f"10d. S24 at the arrow: the Blinded hostile archer's Pin Down at the party body "
          f"arrives (0x00A7) and misses -- [38, {tid}, {who}, 3], no word, no Crippled, and "
          f"no close of either kind (a body skill shot carries none, 0 of 129) -- where the "
          f"unblinded control's arrow lands and cripples (until 2026-10-07: always landed)",
          (missed, miss_conds, conditions_on(st, tid)))


def section_body_known_bad():
    print("\n11. KNOWN-BAD ARMS: --no-blind-miss-skill-close, --no-body-skill-blind, each "
          "against its own fix")
    got = {}
    for close in (True, False):
        with arm(blinded_roll=True, skill_close=close):
            at_player, _s, _w, _t = blinded_cast(
                lambda: (hostile_world(SEVER, "starter_sword", (60.0, 0.0)), FOE, PLAYER))
            at_body, _s, who, tid = blinded_cast(
                lambda: body_world(SEVER, "starter_sword", (60.0, 0.0)))
        got[close] = (closes(at_player, FOE), fails(at_player, FOE, PLAYER),
                      closes(at_body, who), fails(at_body, who, tid))
    check(got == {True: ([46], [[agents.GV_ATTACK_FAIL, PLAYER, FOE, 3]],
                         [46], [[agents.GV_ATTACK_FAIL, ALLY, FOE, 3]]),
                  False: ([1], [[agents.GV_ATTACK_FAIL, PLAYER, FOE, 3]],
                          [1], [[agents.GV_ATTACK_FAIL, ALLY, FOE, 3]])},
          "11a. --no-blind-miss-skill-close is the WHOLE difference: on, the Blinded "
          "hostile's Sever Artery closes [46] at the player and at a body; off, [1] at both "
          "-- the pre-2026-10-07 bytes at the player -- and the miss word is the same "
          "[38, T, 10, 3] either way", got)
    got = {}
    for roll in (True, False):
        with arm(blinded_roll=True, body_blind=roll):
            skill, st, who, tid = blinded_cast(
                lambda: body_world(SEVER, "starter_sword", (60.0, 0.0)))
            skill_res = (bool(fails(skill, who, tid)), len(words(skill, who, tid)),
                         conditions_on(st, tid))
            st = body_world(SEVER, "starter_sword", (60.0, 0.0))[0]
            blind(st, FOE)
            plain = plain_swing(st, FOE, ALLY)
            at_player, _s, _w, _t = blinded_cast(
                lambda: (hostile_world(SEVER, "starter_sword", (60.0, 0.0)), FOE, PLAYER))
        got[roll] = (skill_res, bool(fails(plain, FOE, ALLY)),
                     bool(fails(at_player, FOE, PLAYER)))
    check(got == {True: ((True, 0, []), True, True),
                  False: ((False, 1, [BLEED]), True, True)},
          "11b. --no-body-skill-blind reaches ONLY a body's attack skill on a body: on, "
          "the Blinded hostile's Sever Artery at the party body misses and inflicts "
          "nothing; off, it lands its word and bleeds the body -- the pre-2026-10-07 bytes "
          "-- while its plain swing at the body and its skill at the player miss under "
          "both", got)


def section_body_source():
    """Read through getattr / a parse that cannot raise, so the server before S23 / S24
    (ab39c182) reports 12a-12c RED rather than dying here."""
    print("\n12. RANGERPRE-S23 / S24: the flags, main()'s wiring and the two sites in the "
          "source")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    flags = {"no_blind_miss_skill_close": "BLIND_MISS_SKILL_CLOSE",
             "no_body_skill_blind": "BODY_SKILL_BLIND"}
    parsed = {}
    for dest in flags:
        opt = "--" + dest.replace("_", "-")
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                parsed[dest] = (getattr(ap.parse_args([]), dest),
                                getattr(ap.parse_args([opt]), dest))
        except (SystemExit, AttributeError) as exc:     # an unknown flag: argparse exits 2
            parsed[dest] = ("refused", repr(exc))
    bools = {b: getattr(authsrv, b, "absent") for b in flags.values()}
    check(parsed == {d: (False, True) for d in flags}
          and bools == {b: True for b in flags.values()},
          "12a. --no-blind-miss-skill-close and --no-body-skill-blind parse (default off) "
          "and both gates ship ON", (parsed, bools))

    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    flipped = {}
    missing = object()
    for dest, name in flags.items():
        wiring = [n for n in ast.walk(funcs["main"]) if isinstance(n, ast.If)
                  and isinstance(n.test, ast.Attribute) and n.test.attr == dest]
        for flag in (True, False):
            saved = getattr(authsrv, name, missing)
            try:
                mod = ast.Module(body=wiring, type_ignores=[])
                ast.fix_missing_locations(mod)
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(mod, authsrv.__file__, "exec"),            # noqa: S102
                         authsrv.__dict__, {"a": argparse.Namespace(**{dest: flag})})
                flipped[(dest, flag, len(wiring))] = getattr(authsrv, name, "absent")
            finally:
                if saved is missing:
                    authsrv.__dict__.pop(name, None)
                else:
                    setattr(authsrv, name, saved)
    check(flipped == {(d, f, 1): (not f) for d in flags for f in (True, False)},
          "12b. main()'s `if a.no_blind_miss_skill_close:` and `if a.no_body_skill_blind:` "
          "blocks, lifted out of the source and RUN against authsrv's own globals, each flip "
          "their own bool -- a block without its `global` would leave it True -- and leave "
          "it alone when the flag is off", flipped)

    sites = {}
    for name in ("land_swing", "land_swing_on_body"):
        sites[name] = (
            sum(1 for n in ast.walk(funcs[name]) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == "blind_miss_close"),
            sum(1 for n in ast.walk(funcs[name]) if isinstance(n, ast.Name)
                and n.id == "BODY_SKILL_BLIND"))
    check(sites == {"land_swing": (1, 0), "land_swing_on_body": (1, 1)},
          "12c. both Blind arms close through blind_miss_close exactly once, and only "
          "land_swing_on_body's roll reads BODY_SKILL_BLIND (land_swing's player branch "
          "always rolled; sections 10 and 11 drive both)", sites)


def main():
    print("test_condhit -- an attack skill's condition rides the hit (RANGERPRE-S22); "
          "a body's attack skill under Blind (RANGERPRE-S23 / S24)")
    t0 = time.time()
    section_tape()
    try:
        vaultpath.require_dir("content", why="the skills rows that make 382 an attack")
        have_rows = True
    except SystemExit as exc:
        have_rows = False
        LEDGER.skip("2-8, 10-11. the server sections", str(exc).splitlines()[0])
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
            section_body_close()
            section_body_known_bad()
        finally:
            (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.PLAYER_SWING_DAMAGE,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR,
             agents.PLAYER_LEVEL, agents.PLAYER_HEALTH, agents.PLAYER_ATTRIBUTE_RANKS,
             agents.PLAYER_ATTRIBUTE_POINTS, authsrv.skill_cost) = saved_pc
    section_source()
    section_body_source()
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
