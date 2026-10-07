r"""test_attribpassive -- the primary attributes' passive rules: Expertise's energy
discount on every caster, ROUNDED, and the ten-attribute table read against the
client's own descriptions (SKILLS-EX, studies/skills/FINDINGS.md section 66).

WHAT IT IS REALLY CHECKING. Until 2026-10-07 no cast was cheapened by Expertise:
the press, the hostile's gate and debit and the hero's all priced a cast at the
client's table cost. Retail did not -- the Ranger at Expertise 1 on
20260914T005758 :56011 paid 14 for skill 392's 15. test_pools carried that one
spend BY NAME with the comment "floored", and the floor is wrong: the same
connection's 394 (10, twice), 455 (10), 433 (5) and 446 (5) paid their full
cost, where floor charges 9 and 4. ROUND is the only one of the three
roundings that predicts all six.

  1  the rule (bare): the six carried spends through attribpassive.expertise_cost
     -- the wire word, f32 bits, 6 of 6 -- and the KNOWN-BAD arms: floor 1 of 6,
     ceil 5 of 6 (misses 392 only), no Expertise 5 of 6 (misses 392 only); rank 12
     turns 10 into 5, a 1 at rank 15 is 0.
  2  the scope (bare): attacks of any profession and Ranger skills of any type;
     a Warrior stance, a Monk spell and a Monk TOUCH skill are not (the touch
     clause of the client's sentence is OPEN, section 66).
  3  the server's player price (bare, carried rows): energy_cost_for at the live
     Expertise rank gives the six paid costs; Weakness takes the rank down one;
     a cost discounted to 0 is FREE (0, no glyph episode); --no-expertise prices
     every row at the table cost, exactly what the server charged before.
  4  the bodies (bare, carried rows): body_skill_cost == the player's price at
     the same rank, and a body's Weakness cuts its own rank.
  5  the hero (bare, carried rows): the REAL ally_cast_tick -- a Ranger hero at
     Expertise 1 casting 392 sends E4 then [62, hero, -14/max]; the known-bad arm
     -15/max; a 1-energy attack at rank 15 casts on an EMPTY pool with no [62].
  6  the hostile (bare, carried rows): the REAL enemy_attack_tick -- a hostile
     archer at Expertise 1 pays 14 for 392 and 15 under the known-bad arm.
  7  the wiring (bare): EXPERTISE ships ON; --no-expertise parses; main()'s own
     block, executed, flips the MODULE's flag; the three body sites read
     body_skill_cost and energy_cost_for reads the discount; pick_skill does not.
  8  the vault's tables (content DIR): the carried rows are the vault's own, and
     no skills row is both a spell (the glyph's scope) and in Expertise's.
  9  the client (client DIR): s_attrib's ten primaries carry the description ids
     attribpassive commits, and each resolved description CONTAINS every numeral
     we typed for it (the text is read at run time and never printed).
 10  the tape (captures DIR): the join test_pools uses re-finds the six spends on
     20260914T005758, bit for bit, at Expertise 1 from the tape's own 0x003A.
"""
import argparse
import ast
import contextlib
import io
import os
import re
import struct
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
import attribpassive                                           # noqa: E402
import content                                                 # noqa: E402
import effects                                                 # noqa: E402
import pools                                                   # noqa: E402
import vaultpath                                               # noqa: E402

# The floor is VAULT-CONDITIONAL (test_agentlife's precedent), decided on three
# DIRECTORIES and never on what loaded: vault/content (section 8, 2 checks),
# vault/client (section 9, 2 checks) and vault/captures/live (section 10, 2
# checks). FLOOR_BARE is sections 1-7, MEASURED on the bare-machine green run of
# 2026-10-07 (RURIK_VAULT at an empty directory): 25 checks, 3 declared skips. The
# vault run the same day: 31 checks, 0 skips.
FLOOR_BARE = 25
FLOOR_PER_DIR = {("content",): 2, ("client",): 2, ("captures", "live"): 2}


def _floor():
    n = FLOOR_BARE
    for parts, k in FLOOR_PER_DIR.items():
        if os.path.isdir(vaultpath.vault_path(*parts)):
            n += k
    return n


LEDGER = checks.Ledger("primary attributes (SKILLS-EX)", floor=_floor())
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
EXPERTISE = attribpassive.EXPERTISE_ATTRIBUTE
FLOAT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
E4 = 0x00E4
CAPTURE, CONN, RANGER = "20260914T005758", "56011", 29

# THE TAPE (OBSERVED; re-derived 2026-10-07 with test_pools._scan_connection over
# the whole live corpus, gapped :65009 set aside): the ONLY paid spends by an agent
# at a nonzero Expertise rank in 288 joined -- the Ranger (agent 29, 0x003A
# [23, 25 | 1, 2 | 1, 2]) on :56011. (t, skill, table cost, its 41 maximum, the
# property-62 word's f32 bits.) The 11 spends of 322 and 17 of 346 on the same
# connection are the HERO's, Koss at Expertise 0, and witness nothing here.
TAPE = (
    (423.622, 433, 5, 22, 0xBE68BA2F),
    (428.099, 394, 10, 22, 0xBEE8BA2F),
    (431.089, 392, 15, 22, 0xBF22E8BA),
    (435.758, 446, 5, 22, 0xBE68BA2F),
    (446.429, 394, 10, 22, 0xBEE8BA2F),
    (528.554, 455, 10, 19, 0xBF06BCA2),
)
TAPE_RANK = 1

# THE CARRIED ROWS: the vault's `skills` rows (skilltable.py, build 38974) for the
# columns the cost path reads, so sections 3-6 run on a bare machine; section 8
# holds them to the vault's own. SYN is SYNTHETIC -- a 1-energy Ranger bow attack
# no table holds, for the free-at-rank-15 path; it is never compared to anything.
SKILL_COLUMNS = ("energy", "adrenaline_units", "type_code", "profession", "attribute",
                 "target", "activation", "aftercast", "recharge", "weapon_req",
                 "touch_range")
RECORD_BUILD = 38974
RECORD = {
    "392": (15, 0, 14, 2, 25, 5, 0.0, 0.0, 8, 2, False),
    "394": (10, 0, 14, 2, 25, 5, 0.0, 0.0, 3, 2, False),
    "433": (5, 0, 19, 2, 24, 0, 2.0, 0.0, 12, 0, False),
    "446": (5, 0, 10, 2, 24, 0, 3.0, 0.75, 10, 0, False),
    "455": (10, 0, 3, 2, 24, 0, 0.0, 0.0, 20, 0, False),
    "322": (5, 0, 14, 1, 17, 5, 0.0, 0.0, 3, 185, False),
    "346": (5, 0, 3, 1, 17, 0, 0.0, 0.0, 4, 0, False),
    "281": (5, 0, 5, 3, 13, 3, 1.0, 0.75, 2, 0, False),
    "312": (5, 0, 10, 3, 14, 5, 0.75, 0.75, 8, 0, True),
}
SYN = 99001
SYN_ROW = (1, 0, 14, 2, 25, 5, 0.0, 0.0, 8, 2, False)


def _row(key, vals):
    return content.Row(dict(zip(SKILL_COLUMNS, vals)), "skills", key,
                       {"source": "client-table",
                        "extractor": "toolkit/clientscan/skilltable.py",
                        "build": RECORD_BUILD})


@contextlib.contextmanager
def carried(**flags):
    """WORLD's skills table REPLACED by the carried rows (and SYN) for the block,
    the named authsrv flags set, all restored after; stdout captured."""
    tables = agents.WORLD.tables
    had, kept = "skills" in tables, tables.get("skills")
    saved = {k: getattr(authsrv, k) for k in flags}
    rows = {k: _row(k, v) for k, v in RECORD.items()}
    rows[str(SYN)] = _row(str(SYN), SYN_ROW)
    tables["skills"] = rows
    for k, v in flags.items():
        setattr(authsrv, k, v)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            yield
    finally:
        for k, v in saved.items():
            setattr(authsrv, k, v)
        if had:
            tables["skills"] = kept
        else:
            del tables["skills"]


class Ranks:
    """A stand-in for the live attribute state: player_rank_of reads
    `effective_of`, and nothing else is asked of it here."""

    def __init__(self, ranks):
        self.ranks = dict(ranks)

    def effective_of(self, attribute):
        return int(self.ranks.get(int(attribute), 0))


def _f32_bits(x):
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


def _word_bits(cost, mx):
    return _f32_bits(pools.spend_fraction(cost, mx))


def _floor_arm(base, rank):
    return max(0, int(base * (100 - 4 * rank) // 100))


def _ceil_arm(base, rank):
    return max(0, -(-base * (100 - 4 * rank) // 100))


def _score(fn, rank=TAPE_RANK):
    hits = [s for _t, s, c, mx, bits in TAPE if _word_bits(fn(c, rank), mx) == bits]
    misses = sorted({s for _t, s, c, mx, bits in TAPE if _word_bits(fn(c, rank), mx) != bits})
    return len(hits), misses


# ---------------------------------------------------------------------------------
def section_rule():
    print("== 1. the rule against the tape's six spends ==")
    n, miss = _score(attribpassive.expertise_cost)
    check(n == len(TAPE) == 6 and not miss,
          "ROUND: the six property-62 words of the Ranger at Expertise 1, bit for bit "
          "(392 15 -> 14; 394 and 455 10 -> 10; 433 and 446 5 -> 5)", f"{n} of {len(TAPE)}, misses {miss}")
    n, miss = _score(_floor_arm)
    check(n == 1 and miss == [394, 433, 446, 455],
          "KNOWN-BAD floor (test_pools' old 'floored'): 1 of 6 -- it charges "
          "9 for a 10 and 4 for a 5", f"{n} of 6, misses {miss}")
    n, miss = _score(_ceil_arm)
    check(n == 5 and miss == [392],
          "KNOWN-BAD ceil (equivalently 'floor the discount'): 5 of 6, missing 392", f"{n}, {miss}")
    n, miss = _score(lambda c, r: c)
    check(n == 5 and miss == [392],
          "KNOWN-BAD no Expertise (--no-expertise's prices): 5 of 6 -- 392 is the one "
          "spend on disk that shows a discount at all", f"{n}, {miss}")
    ec = attribpassive.expertise_cost
    check(ec(10, 12) == 5 and ec(15, 12) == 8 and ec(25, 12) == 13,
          "rank 12 (48 % off): 10 -> 5 (5.2), 15 -> 8 (7.8), 25 -> 13 (13.0)",
          f"{ec(10, 12)}, {ec(15, 12)}, {ec(25, 12)}")
    check(ec(1, 15) == 0 and ec(5, 25) == 0 and ec(5, 40) == 0,
          "a 1 at rank 15 is 0 (0.4), and 25 ranks or more price anything at 0 -- never "
          "negative", f"{ec(1, 15)}, {ec(5, 25)}, {ec(5, 40)}")
    check(ec(15, 0) == 15 and ec(0, 12) == 0 and ec(15, -1) == 15 and ec(15, None) == 15,
          "rank 0, a free row, a negative rank and no rank: the table cost unchanged")


def section_scope():
    print("== 2. the scope: attack skills and Ranger skills ==")
    rows = {k: dict(zip(SKILL_COLUMNS, v)) for k, v in RECORD.items()}
    ins = [k for k in ("392", "394", "433", "446", "455", "322")
           if attribpassive.expertise_applies(rows[k])]
    check(ins == ["392", "394", "433", "446", "455", "322"],
          "in scope: Ranger bow attacks 392 / 394, a Ranger preparation 433, a type-10 "
          "Ranger skill 446, a Ranger stance 455 -- and a WARRIOR's attack 322", f"{ins}")
    outs = [k for k in ("346", "281", "312") if attribpassive.expertise_applies(rows[k])]
    check(not outs and not attribpassive.expertise_applies({})
          and not attribpassive.expertise_applies(None)
          and not attribpassive.expertise_applies({"type_code": "x", "profession": 2}),
          "out of scope: a Warrior stance 346, a Monk spell 281 and a Monk TOUCH skill 312 "
          "(the client's 'touch skills' clause is OPEN, section 66); a row that cannot say "
          "is charged its table cost", f"{outs}")


def _state(ranks=None, agents_rows=None):
    st = {"agents": dict(agents_rows or {}), "pos": (0.0, 0.0), "player_health": 1000.0,
          "player_dead": False, "attributes": Ranks(ranks or {})}
    authsrv.effect_table(st)
    return st


def _weaken(st, agent_id):
    weak = effects.CONDITION_BY_NAME["Weakness"]
    st["effects"].apply(agent_id, weak, 0, 20.0, time.time(), type_code=8)


def section_player():
    print("== 3. the server's price for the player (energy_cost_for) ==")
    with carried(EXPERTISE=True):
        st = _state({EXPERTISE: TAPE_RANK})
        got = [(s, authsrv.energy_cost_for(st, P, s, 0)) for _t, s, c, mx, b in TAPE]
        st12 = _state({EXPERTISE: 12})
        c12 = authsrv.energy_cost_for(st12, P, 455, 0)[0]
        _weaken(st12, P)
        w12 = authsrv.energy_cost_for(st12, P, 455, 0)[0]
        st1 = _state({EXPERTISE: 1})
        _weaken(st1, P)
        w1 = authsrv.energy_cost_for(st1, P, 392, 0)[0]
        free = authsrv.energy_cost_for(_state({EXPERTISE: 15}), P, SYN, 0)
        out = [authsrv.energy_cost_for(_state({EXPERTISE: 12}), P, s, 0)[0]
               for s in (346, 281, 312)]
    with carried(EXPERTISE=False):
        off = [authsrv.energy_cost_for(_state({EXPERTISE: 12}), P, int(k), 0)[0]
               for k in sorted(RECORD, key=int)] +               [authsrv.energy_cost_for(_state({EXPERTISE: 15}), P, SYN, 0)[0]]
    words = sum(1 for (_t, s, c, mx, bits), (_s, cf) in zip(TAPE, got)
                if _word_bits(cf[0], mx) == bits)
    check(words == 6 and all(cf[1] is None and cf[2] == 0 for _s, cf in got),
          "the player at Expertise 1: energy_cost_for prices the six as the tape paid "
          "them, 6 of 6 words, no glyph in play", f"{got}")
    check(c12 == 5 and w12 == 6 and w1 == 15,
          "rank 12 turns 455's 10 into 5; under Weakness the rank is 11 (10 -> 6) and "
          "Expertise 1 is rank 0 (392 back to 15) -- SKILLS-WK at this read too",
          f"12: {c12}, weakened 12: {w12}, weakened 1: {w1}")
    check(free == (0, None, 0),
          "a 1-energy attack at rank 15 is FREE: (0, no glyph episode, 0) -- the "
          "press then sends no [62] and refuses nothing (cost > 0 gates both)", f"{free}")
    check(out == [5, 5, 5],
          "rank 12 takes nothing off a Warrior stance, a Monk spell or a Monk touch "
          "skill", f"{out}")
    want = [RECORD[k][0] for k in sorted(RECORD, key=int)] + [1]
    check(off == want,
          "KNOWN-BAD --no-expertise: every row at rank 12 (and SYN at 15) costs its "
          "table energy -- byte for byte what the server charged before", f"{off} vs {want}")


def _body(aid, ranks, skills=(), hero=None, prof=2, emax=25.0, pos=(0.0, 0.0),
          allegiance=None, health=480.0):
    row = {"name": "a ranger", "dead": False, "died_at": 0.0, "health": health,
           "max_health": 480.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": allegiance or agents.ALLEGIANCE_PLAYER, "effects": 0,
           "attacks_back": False, "attack_speed": 2.475,
           "skills": authsrv.bar_triples(skills), "skill_ready": [0.0] * len(skills),
           "npc": {"profession": prof, "level": 20}, "attributes": dict(ranks),
           "party_slot": 0, "base_max_energy": emax}
    if hero is not None:
        row.update(hero=hero, max_energy=emax, energy_profession=prof)
    return row


def section_bodies():
    print("== 4. a body pays what the player would (body_skill_cost) ==")
    with carried(EXPERTISE=True):
        diffs = []
        for rank in (0, 1, 12):
            st = _state({EXPERTISE: rank}, {200: _body(200, {EXPERTISE: rank})})
            for k in RECORD:
                pl = authsrv.energy_cost_for(st, P, int(k), 0)[0]
                bd = authsrv.body_skill_cost(st, 200, int(k))
                if (bd[0], bd[1]) != (pl, 0):
                    diffs.append((rank, k, pl, bd))
        st = _state({}, {200: _body(200, {EXPERTISE: 12}), 201: _body(201, {EXPERTISE: 12})})
        _weaken(st, 200)
        a, b = authsrv.body_skill_cost(st, 200, 455)[0], authsrv.body_skill_cost(st, 201, 455)[0]
        none = authsrv.body_skill_cost(_state({}, {202: _body(202, {})}), 202, 392)[0]
    check(not diffs,
          "at ranks 0, 1 and 12 a body's (cost, units) equals the player's price for "
          "every carried row -- one rule for every caster", f"{diffs}")
    check(a == 6 and b == 5 and none == 15,
          "a body's Weakness cuts ITS rank (12 -> 11: 6) and not its neighbour's (5); "
          "a body with no Expertise pays the table cost", f"{a}, {b}, {none}")


def _hero_world(rank, skill, pool_current=None):
    hero = _body(200, {EXPERTISE: rank}, skills=(skill,), hero=6, emax=25.0)
    foe = {"name": "Bandit Raider", "dead": False, "health": 3000.0, "max_health": 3000.0,
           "pos": (300.0, 0.0), "plane": 0, "allegiance": agents.ALLEGIANCE_HOSTILE,
           "effects": 0, "attacks_back": True, "skills": (), "skill_ready": [],
           "npc": {"level": 10, "profession": 1}, "last_hit": 0.0, "died_at": 0.0}
    st = {"agents": {200: hero, 110: foe}, "pos": (0.0, 60.0), "player_health": 1000.0,
          "player_dead": False}
    authsrv.effect_table(st)
    if pool_current is not None:
        pool = authsrv.agent_energy(hero)
        pool.current = float(pool_current)
    return st


def _hero_cast(st):
    sent = []

    def send(op, vals, label="", quiet=False):
        sent.append((op, list(vals)))
    saved = authsrv.party_fight_target
    authsrv.party_fight_target = lambda state, aid, agent, now: 110
    try:
        authsrv.ally_cast_tick(send, st, 1)
    finally:
        authsrv.party_fight_target = saved
    i4 = next((i for i, (op, v) in enumerate(sent) if op == E4 and v[0] == 200), None)
    spends = [v for op, v in sent if op == FLOAT and v[0] == agents.GV_ENERGY_SPENT
              and v[1] == 200]
    return i4, sent, spends


def section_hero():
    print("== 5. the hero's [62] carries the discounted cost (the real ally_cast_tick) ==")
    flags = dict(ENERGY=True, HERO_SPEND_WORD=True, HERO_WIRE_POOLS=True,
                 NPC_ATTACK_SKILL_SWINGS=True)
    with carried(EXPERTISE=True, **flags):
        st = _hero_world(1, 392)
        mx = authsrv.agent_energy(st["agents"][200]).maximum
        before = authsrv.agent_energy(st["agents"][200]).current
        i4, sent, _spends = _hero_cast(st)
        after = authsrv.agent_energy(st["agents"][200]).current
        want = authsrv._fraction(pools.spend_fraction(14, mx), agents.GV_ENERGY_SPENT, "t")
        nxt = sent[i4 + 1] if i4 is not None and i4 + 1 < len(sent) else None
        st = _hero_world(15, SYN, pool_current=0.0)
        f4, _sent, fspends = _hero_cast(st)
    with carried(EXPERTISE=False, **flags):
        st = _hero_world(1, 392)
        mx0 = authsrv.agent_energy(st["agents"][200]).maximum
        _i4, _sent, spends0 = _hero_cast(st)
        want0 = authsrv._fraction(pools.spend_fraction(15, mx0), agents.GV_ENERGY_SPENT, "t")
    check(nxt == (FLOAT, [agents.GV_ENERGY_SPENT, 200, want]) and abs((before - after) - 14) < 0.2,
          "a Ranger hero at Expertise 1 casts 392: E4, then [62, hero, -14/max] right "
          "behind it, and its pool pays 14 -- HEROENERGY's word with the discount",
          f"E4 at {i4}, next {nxt}, want {want}; pool {before:.2f} -> {after:.2f}")
    check(f4 is not None and not fspends,
          "a 1-energy attack at Expertise 15 casts on an EMPTY pool and sends no [62] "
          "-- discounted to 0 is free, no gate and no word", f"E4 at {f4}, spends {fspends}")
    check(spends0 == [[agents.GV_ENERGY_SPENT, 200, want0]],
          "KNOWN-BAD --no-expertise: the same cast sends -15/max, the table cost",
          f"{spends0}, want {want0}")


def _archer(rank, skills):
    return {"name": "an archer", "dead": False, "died_at": 0.0, "health": 1e6,
            "max_health": 1e6, "last_hit": 0.0, "pos": (300.0, 0.0), "plane": 0,
            "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": 2.475,
            "effects": 0, "attacks_back": True, "weapon_item": "hostile_bow",
            "npc": {"profession": 2, "level": 20}, "attributes": {EXPERTISE: rank},
            "skills": authsrv.bar_triples(skills), "skill_ready": [0.0] * len(skills)}


def _hostile_pays(rank):
    """The REAL enemy_attack_tick on a fake clock until the archer casts 392; its
    pool's drop (0 if it never cast)."""
    import time as _real

    class Clock:
        def __init__(self, t):
            self.t = t

        def time(self):
            return self.t

        def __getattr__(self, name):
            return getattr(_real, name)

    saved_time = authsrv.time
    t0 = 1_000_000.0
    try:
        authsrv.time = Clock(t0)
        st = {"agents": {10: _archer(rank, (392,))}, "pos": (0.0, 0.0), "action_hold": 1,
              "player_dead": False}
        authsrv.player_pools(st)
        st["player_health"] = float(authsrv.player_max_health(st))
        authsrv.effect_table(st)
        pool = authsrv.agent_energy(st["agents"][10])
        pool.tick(t0)
        before = pool.current
        cast = False
        for i in range(400):
            authsrv.time.t = t0 + i * 0.005
            authsrv.enemy_attack_tick(lambda op, vals, why="", quiet=False: None, st, 0)
            if st["agents"][10].get("casting") is not None:
                cast = True
                break
        # the pool has regenerated for at most i x 5 ms by now; read the drop off the
        # book without ticking it again
        return cast, before - pool.current
    finally:
        authsrv.time = saved_time


def section_hostile():
    print("== 6. the hostile pays the discounted cost (the real enemy_attack_tick) ==")
    flags = dict(ENERGY=True, NPC_FOLLOW=False, NPC_ATTACK_SKILL_SWINGS=True,
                 INSTANT_ANNOUNCE=True)
    with carried(EXPERTISE=True, **flags):
        cast1, paid1 = _hostile_pays(1)
    with carried(EXPERTISE=False, **flags):
        cast0, paid0 = _hostile_pays(1)
    check(cast1 and abs(paid1 - 14) < 0.2,
          "a hostile archer at Expertise 1 casts 392 and its pool pays 14",
          f"cast {cast1}, paid {paid1:.3f}")
    check(cast0 and abs(paid0 - 15) < 0.2,
          "KNOWN-BAD --no-expertise: the same archer pays 15", f"cast {cast0}, paid {paid0:.3f}")


def _func(tree, name):
    return next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _calls(fn, name):
    return [n for n in ast.walk(fn) if isinstance(n, ast.Call)
            and getattr(n.func, "id", getattr(n.func, "attr", None)) == name]


def section_wiring():
    print("== 7. the switch and the sites ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    check(authsrv.EXPERTISE is True
          and src.count("\nEXPERTISE = True ") == 1
          and getattr(ap.parse_args([]), "no_expertise", None) is False
          and getattr(ap.parse_known_args(["--no-expertise"])[0], "no_expertise", None) is True,
          "EXPERTISE ships ON as a column-0 module bool, and --no-expertise parses")
    # main()'s own block, lifted out and RUN in authsrv's namespace: without its
    # `global` the assignment binds a local and the flag parses and does nothing.
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_expertise:", i_main)
    i_end = src.find("\n    if a.", i_flip + 1)
    flipped = None
    if 0 < i_main < i_flip < i_end:
        body = "\n".join(line[4:] if line.startswith("    ") else line
                         for line in src[i_flip:i_end].splitlines())
        code = "def _ex_flip(a):\n" + "\n".join("    " + ln for ln in body.splitlines())
        saved = authsrv.EXPERTISE
        try:
            exec(compile(code, "<main:no_expertise>", "exec"), authsrv.__dict__)
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.__dict__["_ex_flip"](argparse.Namespace(no_expertise=True))
            flipped = authsrv.EXPERTISE
        finally:
            authsrv.EXPERTISE = saved
            authsrv.__dict__.pop("_ex_flip", None)
    check(flipped is False and authsrv.capture_flags().get("EXPERTISE") is True,
          "main()'s --no-expertise block, executed, sets the MODULE's EXPERTISE to False; "
          "the capture header records the arm", f"main {i_main} flip {i_flip} -> {flipped}")
    eat, act = _func(tree, "enemy_attack_tick"), _func(tree, "ally_cast_tick")
    ecf, pick = _func(tree, "energy_cost_for"), _func(tree, "pick_skill")
    check(len(_calls(eat, "body_skill_cost")) == 2 and not _calls(eat, "skill_cost")
          and len(_calls(act, "body_skill_cost")) == 1
          and len(_calls(ecf, "expertise_energy_cost")) == 1
          and not _calls(pick, "body_skill_cost") and not _calls(pick, "expertise_energy_cost"),
          "the hostile's gate and debit and the hero's debit read body_skill_cost, "
          "energy_cost_for reads the discount, and pick_skill reads neither (Q19)",
          f"eat {len(_calls(eat, 'body_skill_cost'))}/{len(_calls(eat, 'skill_cost'))}, "
          f"act {len(_calls(act, 'body_skill_cost'))}, ecf {len(_calls(ecf, 'expertise_energy_cost'))}")
    leaf = open(os.path.join(HERE, "attribpassive.py"), encoding="utf-8").read()
    imports = {a.name for n in ast.walk(ast.parse(leaf)) if isinstance(n, ast.Import)
               for a in n.names} | {n.module for n in ast.walk(ast.parse(leaf))
                                    if isinstance(n, ast.ImportFrom)}
    check(not imports and "sys.path" not in leaf,
          "attribpassive is a stdlib-only leaf that imports NOTHING -- never its origin, "
          "and no sys.path header (CLAUDE.md 'Leaf modules')", f"{imports}")


def section_vault_tables():
    print("== 8. the vault's tables ==")
    try:
        vaultpath.require_dir("content", why="the vault's skills table RECORD copies")
    except SystemExit as exc:
        LEDGER.skip("the carried rows against the vault's own, and the glyph overlap "
                    "(2 checks)", str(exc).splitlines()[0])
        return
    loaded = agents.WORLD.rows("skills")
    off = {}
    for k, vals in RECORD.items():
        got = loaded.get(k)
        if got is None:
            off[k] = "absent"
            continue
        cols = [c for c, v in zip(SKILL_COLUMNS, vals) if got.get(c) != v]
        if cols:
            off[k] = cols
    check(not off and str(SYN) not in loaded,
          f"the {len(RECORD)} carried rows are the vault's own, column for column (and "
          f"SYN {SYN} is no real row)", f"off={off}")
    both = [k for k, r in loaded.items()
            if int(r.get("type_code", -1)) in authsrv.SPELL_TYPE_CODES
            and attribpassive.expertise_applies(r)]
    scope = sum(1 for r in loaded.values()
                if attribpassive.expertise_applies(r) and int(r.get("energy", 0) or 0) > 0)
    check(len(loaded) > 1000 and not both,
          f"none of the {len(loaded)} skills rows is both a spell (the glyph's scope) and "
          f"in Expertise's -- the order energy_cost_for takes them in is moot today; "
          f"{scope} paid rows are in Expertise's scope", f"both {both[:10]}")


def section_client():
    print("== 9. the client's own descriptions (s_attrib + textrec, at run time) ==")
    try:
        vaultpath.require_dir("client", why="the pinned exe's s_attrib table and the archive")
    except SystemExit as exc:
        LEDGER.skip("the ten primaries against the client's descriptions (2 checks)",
                    str(exc).splitlines()[0])
        return
    clientscan = os.path.join(PARENT, "clientscan")
    if clientscan not in sys.path:
        sys.path.insert(0, clientscan)
    import attribtable
    import pinned
    import textrec
    exe = pinned.find()[0]
    data = open(exe, "rb").read()
    base, _count = attribtable.locate_table(data)
    rows = [attribtable.parse_record(data, base, i) for i in range(attribtable.EXPECTED_COUNT)]
    prim = {r["id"]: r["description_id"] for r in rows if r["is_primary"]}
    check(prim == attribpassive.PRIMARY_DESCRIPTION_IDS,
          f"s_attrib's ten primaries carry exactly the description ids attribpassive "
          f"commits (build {attribtable.build_of(data)})",
          f"{sorted(prim.items())} vs {sorted(attribpassive.PRIMARY_DESCRIPTION_IDS.items())}")
    missing = {}
    with textrec.TextIndex(exe) as ix:
        for attr, sid in sorted(attribpassive.PRIMARY_DESCRIPTION_IDS.items()):
            text = ix.get(sid) or ""
            tokens = set(re.findall(r"\d+(?:\.\d+)?", text))
            lack = [n for n in attribpassive.PRIMARY_DESCRIPTION_NUMERALS[attr]
                    if n not in tokens]
            if lack or not text:
                missing[attr] = lack or "no text"
    check(not missing,
          "each resolved description CONTAINS every numeral attribpassive types for it "
          "(Expertise's 4, Divine Favor's 3.2, Energy Storage's 3, ...) -- the text is read "
          "here and never printed", f"missing {missing}")


def section_tape():
    print("== 10. the tape: the six spends re-found by test_pools' own join ==")
    try:
        live = vaultpath.require_dir("captures", "live", why="the JARIN tape")
    except SystemExit as exc:
        LEDGER.skip("the six spends on the tape (2 checks)", str(exc).splitlines()[0])
        return
    import tape
    import test_pools
    from codec import Codec
    cap = os.path.join(live, CAPTURE)
    conns = [c for c in tape.channel_files(cap) if CONN in c["connection"]]
    found, rank = [], None
    for conn in conns:
        _info, events = tape.load_tape(cap, conn["connection"])
        msgs, _ = tape.decode_all(events, Codec(), "GAME_SMSG", 0)
        for t, op, v in msgs:
            if op == 0x003A and v[1] == RANGER and isinstance(v[2], list):
                n = len(v[2]) // 3
                rank = dict(zip(v[2][:n], v[2][2 * n:])).get(EXPERTISE, 0)
        totals = test_pools._new_totals()
        regen, spends, gains, casts = [], [], [], []
        test_pools._scan_connection(msgs, CAPTURE, conn["connection"],
                                    test_pools._capture_build(cap, conn["path"]),
                                    totals, regen, spends, gains, casts)
        found += [(s["skill"], s["max"], _f32_bits(s["value"]))
                  for s in spends if s["agent"] == RANGER]
    carried_rows = [(s, mx, bits) for _t, s, _c, mx, bits in TAPE]
    check(len(conns) == 1 and rank == TAPE_RANK and found == carried_rows,
          f"{CAPTURE} :{CONN}: the Ranger's 0x003A says Expertise {rank}, and the corpus "
          f"oracle's join finds its {len(found)} spends equal to the carried six, bit for bit",
          f"{found} vs {carried_rows}")
    world = content.load()
    pred = []
    for s, mx, bits in found:
        cost = int(test_pools.skill_row(world, s, None)["energy"])
        pred.append(_word_bits(attribpassive.expertise_cost(cost, rank), mx) == bits)
    check(pred and all(pred),
          "and the shipped rule predicts every one of them from the client's own cost "
          "column at the tape's own rank", f"{pred}")


def main():
    section_rule()
    section_scope()
    section_player()
    section_bodies()
    section_hero()
    section_hostile()
    section_wiring()
    section_vault_tables()
    section_client()
    section_tape()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
