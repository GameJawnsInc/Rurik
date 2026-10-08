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
 10  the tape (captures + content DIRs): the join test_pools uses re-finds the six
     spends on 20260914T005758, bit for bit, at Expertise 1 from the tape's own 0x003A.
 11  Divine Favor's number (bare): round(3.2 x rank), Healing Touch doubled; the
     rounding argument is PRINTED here and decided on the tape in 16.
 12  its scope (bare, carried rows).
 13  the server's word (bare, carried rows): the REAL ally_cast_tick -> land_skill for a
     hero, the REAL handle_skill_press -> cast_tick for the player, and the direct call.
 14  its switch and its two call sites, each the statement right after resolve_heal.
 15  the tape (captures + content DIRs): the level-20 Monks' 42 on 20260817T231139.
 16  the tape (captures + content DIRs): the Smiting Monks' 3 on 20260929T100038, and
     the rounding decided by the two constants read over maxima the wire sends.
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

# The floor is VAULT-CONDITIONAL (test_agentlife's precedent), decided on
# DIRECTORIES and never on what loaded: vault/content (section 8, 2 checks),
# vault/client (section 9, 2 checks), and vault/captures/live AND vault/content
# together (sections 10, 15 and 16, 2 + 2 + 2 checks -- the tape sections price
# what they find through the vault's skills table, so a vault with captures and no
# content skips them -- found at review, 2026-10-07). FLOOR_BARE is sections 1-7 and 11-14,
# MEASURED on the bare-machine green run of 2026-10-07 after review (RURIK_VAULT at
# an empty directory, and at one holding only captures/): 39 checks, 5 declared
# skips. The vault run the same day: 49 checks, 0 skips. (Stage 1, Expertise alone,
# measured 25 / 31; stage 2 before review 39 / 47.)
FLOOR_BARE = 39
FLOOR_PER_DIRS = (((("content",),), 2), ((("client",),), 2),
                  ((("captures", "live"), ("content",)), 6))


def _floor():
    n = FLOOR_BARE
    for dirs, k in FLOOR_PER_DIRS:
        if all(os.path.isdir(vaultpath.vault_path(*parts)) for parts in dirs):
            n += k
    return n


def _need(*dirs, what):
    """require_dir for every directory a section reads; the first one absent is a
    declared LEDGER.skip naming the section's checks, and the section returns None."""
    out = []
    for parts in dirs:
        try:
            out.append(vaultpath.require_dir(*parts, why=what))
        except SystemExit as exc:
            LEDGER.skip(what, str(exc).splitlines()[0])
            return None
    return out


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
# property-62 word's f32 bits.) t is the CONNECTION clock (tape.load_tape's: 0 =
# its first s2c segment), which section 10 decodes; the capture clock that
# livewire.decode_conn and deepwoundjoin.sequence read puts the same six 86.47 s
# later (510.09 ... 615.03), and sections 15-16 read that one. The 11 spends of
# 322 and 17 of 346 on the same connection are the HERO's, Koss at Expertise 0,
# and witness nothing here.
TAPE = (
    (423.622, 433, 5, 22, 0xBE68BA2F),
    (428.099, 394, 10, 22, 0xBEE8BA2F),
    (431.089, 392, 15, 22, 0xBF22E8BA),
    (435.758, 446, 5, 22, 0xBE68BA2F),
    (446.429, 394, 10, 22, 0xBEE8BA2F),
    (528.554, 455, 10, 19, 0xBF06BCA2),
)
TAPE_RANK = 1

# DIVINE FAVOR's tape (OBSERVED; re-derived 2026-10-07 with healjoin.batches over
# deepwoundjoin.sequence): the connection of 20260817T231139 whose two Monk casters
# -- agent 12, the party's level-20 Monk henchman by its own 0x01BF, and agent 7, a
# second Monk the tape does not name -- put a 42-point word (Divine Favor at rank 13
# under round(3.2 r), the rank INFERRED) behind every Monk spell they cast on an
# ally. Counts pinned from the run (section 15).
DF_CAPTURE, DF_CONN, DF_CASTERS, DF_RANK = "20260817T231139", "54071", (7, 12), 13
DF_TAPE = {"eligible": 52, "outside": 2, "cut": 2, "with_base": 43}
# The Smiting Monks of 20260929T100038 (agents 3-6 on every connection of it): the
# OTHER constant, 3, and the only one that refutes ceil (ceil(3.2 r) is never 3).
# Read over the RECIPIENT's own on-wire maxima (555 / 483 / 421 / 569), so it is
# OBSERVED, where the town caster's 58 is a reading. Counts pinned from the run.
SMITE_CAPTURE, SMITE_CASTERS, SMITE_RANK = "20260929T100038", (3, 4, 5, 6), 1
SMITE_TAPE = {"eligible": 259, "readable": 212, "outside": 14, "signet": 11}
RES_SIGNET = 2      # profession 0, a signet on a dead ally (four of its completions
                    # were once miscounted as empty Monk-spell batches, studies/skills 66.4)

# THE CARRIED ROWS: the vault's `skills` rows (skilltable.py, build 38974), every
# column, so sections 3-6 and 12-13 run on a bare machine; section 8 holds them to
# the vault's own, column for column. The Ranger and Warrior rows are the tape's;
# the Monk rows are Divine Favor's scope witnesses (studies/skills 66.4) and the
# hero's Orison. SYN is SYNTHETIC -- a 1-energy Ranger bow attack no table holds,
# for the free-at-rank-15 path; it is never compared to anything.
SKILL_COLUMNS = ("activation", "aftercast", "recharge", "energy", "adrenaline",
                 "adrenaline_units", "attribute", "profession", "type_code", "target",
                 "combo", "combo_req", "weapon_req", "aoe_range", "skill_arguments",
                 "duration0", "duration15", "scale0", "scale15", "bonus_scale0",
                 "bonus_scale15", "projectile", "impact_visual", "touch_range",
                 "half_range")
RECORD_BUILD = 38974
RECORD = {
    "392": (0.0, 0.0, 8, 15, 0, 0, 25, 2, 14, 5, 0, 0, 2, 0.0, 4, 0, 0, 0, 0, 3, 15, 680, 2077, False, False),
    "394": (0.0, 0.0, 3, 10, 0, 0, 25, 2, 14, 5, 0, 0, 2, 0.0, 2, 0, 0, 25, 50, 0, 0, 680, 2077, False, False),
    "433": (2.0, 0.0, 12, 5, 0, 0, 24, 2, 19, 0, 0, 0, 0, 0.0, 2, 24, 24, 3, 24, 0, 0, 343, 344, False, False),
    "446": (3.0, 0.75, 10, 5, 0, 0, 24, 2, 10, 0, 0, 0, 0, 0.0, 2, 13, 13, 3, 10, 0, 0, 2077, 2077, False, False),
    "455": (0.0, 0.0, 20, 10, 0, 0, 24, 2, 3, 0, 0, 0, 0, 0.0, 3, 8, 20, 1, 5, 25, 25, 2077, 2077, False, False),
    "322": (0.0, 0.0, 3, 5, 0, 0, 17, 1, 14, 5, 0, 0, 185, 0.0, 2, 0, 0, 10, 40, 0, 0, 2077, 2077, False, False),
    "346": (0.0, 0.0, 4, 5, 0, 0, 17, 1, 3, 0, 0, 0, 0, 0.0, 0, 8, 8, 33, 33, 175, 125, 2077, 2077, False, False),
    "281": (1.0, 0.75, 2, 5, 0, 0, 13, 3, 5, 3, 0, 0, 0, 0.0, 2, 0, 0, 30, 80, 0, 0, 2077, 2077, False, False),
    "312": (0.75, 0.75, 8, 5, 0, 0, 14, 3, 10, 5, 0, 0, 0, 0.0, 6, 0, 0, 10, 55, 10, 55, 2077, 2077, True, False),
    "1": (2.0, 0.75, 4, 0, 0, 0, 21, 1, 7, 0, 0, 0, 0, 0.0, 2, 0, 0, 82, 172, 0, 0, 2077, 2077, False, False),
    "251": (2.0, 0.75, 5, 10, 0, 0, 14, 3, 4, 5, 0, 0, 0, 0.0, 2, 30, 30, 15, 80, 0, 0, 2077, 2077, False, False),
    "252": (1.0, 0.75, 10, 5, 0, 0, 14, 3, 5, 5, 0, 0, 0, 0.0, 2, 0, 0, 20, 65, 0, 0, 2077, 2077, False, False),
    "271": (0.25, 0.75, 30, 10, 0, 0, 14, 3, 6, 0, 0, 0, 0, 156.0, 7, 60, 60, 5, 35, 1, 1, 2077, 2077, False, False),
    "276": (0.75, 0.75, 2, 5, 0, 0, 15, 3, 5, 4, 0, 0, 0, 0.0, 2, 0, 0, 10, 70, 0, 0, 2077, 2077, False, False),
    "280": (1.0, 0.75, 5, 10, 0, 0, 13, 3, 5, 0, 0, 0, 0, 156.0, 2, 0, 0, 30, 180, 0, 0, 2077, 2077, False, False),
    "286": (0.75, 0.75, 3, 10, 0, 0, 13, 3, 5, 4, 0, 0, 0, 0.0, 2, 0, 0, 35, 180, 0, 0, 2077, 2077, False, False),
    "288": (1.0, 0.75, 5, 10, 0, 0, 13, 3, 6, 3, 0, 0, 0, 0.0, 2, 15, 15, 4, 9, 0, 0, 2077, 505, False, False),
    "293": (2.0, 0.75, 5, 0, 0, 0, 16, 3, 7, 3, 0, 0, 0, 0.0, 2, 0, 0, 20, 120, 0, 0, 2077, 2077, False, False),
    "307": (0.25, 0.75, 2, 5, 0, 0, 15, 3, 6, 3, 0, 0, 0, 0.0, 2, 8, 8, 15, 80, 0, 0, 2077, 2077, False, False),
    "313": (0.75, 0.75, 5, 5, 0, 0, 13, 3, 5, 3, 0, 0, 0, 0.0, 2, 0, 0, 20, 80, 2, 2, 2077, 2077, True, False),
    "314": (4.0, 0.75, 8, 10, 0, 0, 13, 3, 5, 6, 0, 0, 0, 0.0, 6, 0, 0, 20, 65, 42, 90, 2077, 2077, True, False),
}
SYN = 99001
SYN_ROW = (0.0, 0.0, 8, 1, 0, 0, 25, 2, 14, 5, 0, 0, 2, 0.0, 4, 0, 0, 0, 0, 0, 0,
           680, 2077, False, False)


def _col(key, column):
    return RECORD[key][SKILL_COLUMNS.index(column)]


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
    want = [_col(k, "energy") for k in sorted(RECORD, key=int)] + [1]
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
    got = _need(("captures", "live"), ("content",),
                what="the six spends on the tape, priced by the vault's skills table (2 checks)")
    if got is None:
        return
    live = got[0]
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



# ---------------------------------------------------------------------------------
# DIVINE FAVOR (SKILLS-EX6, studies/skills 66.4 / 66.7)
DF = attribpassive.DIVINE_FAVOR_ATTRIBUTE
HEAL = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
ORISON, HEAL_AREA, TOUCH, BANISH, HEAL_OTHER = 281, 280, 313, 252, 286


def _f(bits):
    return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]


def _heals(sent, caster, recipient=None):
    """[(recipient, fraction)] of every 55 by `caster`, in wire order."""
    out = []
    for op, v in sent:
        if op == HEAL and v[0] == agents.GV_HEALTH_GAIN and v[2] == caster \
                and (recipient is None or v[1] == recipient):
            out.append((v[1], _f(v[3])))
    return out


def section_df_rule():
    print("== 11. Divine Favor's number: round(3.2 x rank), Healing Touch doubled ==")
    b = attribpassive.divine_favor_bonus
    got = [b(r) for r in (0, 1, 2, 13, 18)]
    check(got == [0, 3, 6, 42, 58] and b(-1) == 0 and b(None) == 0,
          "rank 1 -> 3 and rank 13 -> 42 (retail's two constants over on-wire maxima), "
          "18 -> 58 (a town caster's 116 halved -- its maximum never on the wire, a "
          "RECONSTRUCTION), 2 -> 6 (the slice's Tahlkora); nothing at rank 0", f"{got}")
    check(b(13, TOUCH) == 84 and b(18, TOUCH) == 116 and b(13, ORISON) == 42,
          "Healing Touch (313) is doubled -- 84 is retail's word over a 555 the wire sends; "
          "the shipped ORDER (2 x the rounded bonus) is RECONSTRUCTION; Orison is not "
          "doubled", f"{b(13, TOUCH)}, {b(18, TOUCH)}")
    # PRINTED, NOT CHECKED (re-aimed at review, 2026-10-07): these were two checks of
    # arithmetic on typed numbers, which cannot redden under any change to the
    # product -- a check that cannot fail is not a check. Which rounding the tape picks is
    # checked in section 16, from the constants read off the tape; this prints the
    # argument and the live rival to the doubling's order.
    ranks = range(0, 41)
    rnd = {(32 * r + 5) // 10 for r in ranks}
    flo = {(32 * r) // 10 for r in ranks}
    cei = {-(-32 * r // 10) for r in ranks}
    apart = [r for r in range(0, 21) if 2 * ((32 * r + 5) // 10) != -(-64 * r // 10)]
    print(f"   note: round(3.2 r) holds 3 and 42 {3 in rnd and 42 in rnd}; floor holds 42 "
          f"{42 in flo}; ceil holds 3 {3 in cei}. Healing Touch: round(6.4 r) makes 84 / "
          f"116 {bool({84, 116} & {(64 * r + 5) // 10 for r in ranks})}, ceil(6.4 r) makes "
          f"both {({84, 116} <= {-(-64 * r // 10) for r in ranks})} -- the live rival, apart "
          f"from 2 x round(3.2 r) at ranks {apart}")


def section_df_scope():
    print("== 12. Divine Favor's scope: a Monk spell cast on an ally ==")
    rows = {k: dict(zip(SKILL_COLUMNS, v)) for k, v in RECORD.items()}
    ins = [k for k in ("281", "286", "288", "307", "313", "276", "271")
           if attribpassive.divine_favor_applies(rows[k])]
    check(ins == ["281", "286", "288", "307", "313", "276", "271"],
          "in: spells and enchantments on an ally (byte 3) or another ally (byte 4) -- "
          "the witnesses 281 / 286 / 288 / 307 / 313 and the served 276 -- and a "
          "self-cast enchantment (271, byte 0)", f"{ins}")
    outs = [k for k in ("280", "251", "252", "314", "293", "1", "392", "312")
            if attribpassive.divine_favor_applies(rows[k])]
    check(not outs and not attribpassive.divine_favor_applies({})
          and not attribpassive.divine_favor_applies({"profession": 3, "type_code": 5}),
          "out: an area spell round the caster (280, byte 0 -- the n = 1 negative), a hex "
          "and a spell on a FOE (251, 252), a resurrection (314, byte 6), a Monk SIGNET "
          "(293), a Warrior signet, a Ranger attack, a Monk touch skill on a foe; a row "
          "that cannot say", f"{outs}")


class _Clock:
    def __init__(self, t, real):
        self.t, self._real = t, real

    def time(self):
        return self.t

    def __getattr__(self, name):
        return getattr(self._real, name)


def _hero_heal(df_rank, weaken=False):
    """The REAL ally_cast_tick on a fake clock: a Monk hero (Healing Prayers 3,
    Divine Favor `df_rank`) casts Orison at a hurt party body; every message out
    until its heal lands."""
    import time as _real
    saved = authsrv.time
    t0 = 2_000_000.0
    sent = []

    def send(op, vals, why="", quiet=False):
        sent.append((op, list(vals)))
    try:
        authsrv.time = _Clock(t0, _real)
        hero = _body(200, {13: 3, DF: df_rank, 15: 1}, skills=(ORISON,), hero=3,
                     prof=3, emax=30.0)
        hurt = _body(201, {}, pos=(120.0, 0.0), health=200.0)
        st = {"agents": {200: hero, 201: hurt}, "pos": (0.0, 60.0),
              "player_dead": False}
        authsrv.player_pools(st)
        st["player_health"] = float(authsrv.player_max_health(st))
        authsrv.effect_table(st)
        if weaken:
            st["effects"].apply(200, effects.CONDITION_BY_NAME["Weakness"], 0, 60.0,
                                t0, type_code=8)
        for i in range(400):
            authsrv.time.t = t0 + i * 0.01
            authsrv.ally_cast_tick(send, st, 1)
            if _heals(sent, 200):
                break
    finally:
        authsrv.time = saved
    return sent, st


def _player_heal():
    """The PLAYER's path, end to end: the REAL handle_skill_press (Healing Prayers 3,
    Divine Favor 13, Orison at a hurt party body 201), the pending cast's clocks moved
    30 s into the past, then ONE REAL cast_tick -- its E5 branch is the player's
    resolve_heal and divine_favor_word. [(recipient, caster, points)] of every 55, in
    wire order (points over 201's 480, or the player's own maximum)."""
    st = _state({13: 3, DF: 13}, {201: _body(201, {}, pos=(100.0, 0.0), health=200.0)})
    sent = []

    def send(op, vals, why="", quiet=False):
        sent.append((op, list(vals)))
    authsrv.handle_skill_press([0, ORISON, 0, 201], send, st, 0, authsrv.GAME_CMSG_USE_SKILL)
    queued = len(st.get("pending_casts") or ())
    for cast in st.get("pending_casts") or ():
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            if cast.get(k) is not None:
                cast[k] -= 30.0
    authsrv.cast_tick(send, st, 0)
    pmax = float(authsrv.player_max_health(st))
    return queued, [(v[1], v[2], round(_f(v[3]) * (480.0 if v[1] == 201 else pmax), 3))
                    for op, v in sent if op == HEAL and v[0] == agents.GV_HEALTH_GAIN]


def _direct(ranks, skill, caster=None, body=None, deep_wound=False):
    """divine_favor_word called directly: (points on 201's 480 max, in wire order)."""
    st = _state(ranks, {201: body or _body(201, {}, health=100.0)})
    if deep_wound:
        st["deep_wound"] = {201: True}
    out = []
    authsrv.divine_favor_word(lambda op, v, why="", quiet=False: out.append((op, list(v))),
                              st, skill, P if caster is None else caster, 201, 1)
    return [round(f * 480.0, 3) for _tg, f in _heals(out, P if caster is None else caster)]


def section_df_server():
    print("== 13. the server's Divine Favor word (the real ally_cast_tick / land_skill) ==")
    with carried(ENERGY=False, DIVINE_FAVOR=True, EFFECTS=True):
        sent, st = _hero_heal(2)
        mx = float(st["agents"][201]["max_health"])
        h2 = [(tg, round(f * mx, 3)) for tg, f in _heals(sent, 200)]
        wsent, _ = _hero_heal(2, weaken=True)
        hw = [(tg, round(f * mx, 3)) for tg, f in _heals(wsent, 200)]
        direct = {"orison": _direct({DF: 13}, ORISON), "touch": _direct({DF: 13}, TOUCH),
                  "banish": _direct({DF: 13}, BANISH), "rank0": _direct({DF: 0}, ORISON)}
        dw = _direct({DF: 13}, ORISON, deep_wound=True)
        dead_other = _direct({DF: 13}, HEAL_OTHER, body=dict(_body(201, {}), dead=True))
        dead_self = _direct({DF: 13}, ORISON, body=dict(_body(201, {}), dead=True))
        pq, press = _player_heal()
    with carried(ENERGY=False, DIVINE_FAVOR=False, EFFECTS=True):
        osent, _ = _hero_heal(2)
        h0 = [(tg, round(f * mx, 3)) for tg, f in _heals(osent, 200)]
        pq0, press0 = _player_heal()
    check(len(h2) == 2 and h2[0][0] == 201 and h2[1] == (201, 6.0) and h2[0][1] > 6.0,
          "a Monk hero at Divine Favor 2 casts Orison on a hurt ally: the spell's own heal, "
          "THEN [55, ally, hero, 6 / max] -- retail's order, 147 of 147", f"{h2}")
    check(len(h0) == 1 and h0[0] == h2[0],
          "KNOWN-BAD --no-divine-favor: the same cast sends the spell's heal alone, the "
          "server before this", f"{h0}")
    check(len(hw) == 2 and hw[1] == (201, 3.0),
          "a Weakened caster's Divine Favor is one rank lower: 2 -> 1, the word 3 "
          "(SKILLS-WK)", f"{hw}")
    check(direct == {"orison": [42.0], "touch": [84.0], "banish": [], "rank0": []},
          "divine_favor_word called directly for the player at Divine Favor 13: Orison on "
          "an ally +42, Healing Touch +84, a spell on a foe nothing; at rank 0 nothing",
          f"{direct}")
    base = press[0][2] if press else None
    check(pq == 1 and len(press) == 2 and press[0][:2] == (201, P) and base > 0
          and base != 42.0 and press[1] == (201, P, 42.0),
          "THE PLAYER'S PATH (the real press, then cast_tick's E5): Orison at Divine "
          "Favor 13 sends its own heal on the ally, THEN [55, ally, player, 42 / max] -- "
          "on the ALLY, not on the caster", f"queued {pq}: {press}")
    check(pq0 == 1 and press0 == press[:1],
          "KNOWN-BAD --no-divine-favor on the player's path: the same press sends the "
          "spell's heal alone", f"queued {pq0}: {press0}")
    check(len(dw) == 1 and 0 < dw[0] < 42,
          "a Deep-Wounded recipient's word is cut (heal_agent's -20 %: 33 here, where "
          "retail rounds to 34 -- studies/skills 66.6)", f"cut {dw}")
    pmax = float(authsrv.player_max_health(_state({})))
    check(dead_other == [] and dead_self == [round(42 / pmax * 480, 3)],
          "the word follows the spell's OWN recipient (cast_recipient, resolve_heal's "
          "verdict): Heal Other at a dead ally lands on nobody, Orison at one lands on the "
          "caster (42 points over the player's own maximum)",
          f"other {dead_other}, self {dead_self} (player max {pmax})")


def section_df_wiring():
    print("== 14. Divine Favor's switch and its two call sites ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_divine_favor:", i_main)
    i_end = src.find("\n    if a.", i_flip + 1)
    flipped = None
    if 0 < i_main < i_flip < i_end:
        body = "\n".join(line[4:] if line.startswith("    ") else line
                         for line in src[i_flip:i_end].splitlines())
        code = "def _df_flip(a):\n" + "\n".join("    " + ln for ln in body.splitlines())
        saved = authsrv.DIVINE_FAVOR
        try:
            exec(compile(code, "<main:no_divine_favor>", "exec"), authsrv.__dict__)
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.__dict__["_df_flip"](argparse.Namespace(no_divine_favor=True))
            flipped = authsrv.DIVINE_FAVOR
        finally:
            authsrv.DIVINE_FAVOR = saved
            authsrv.__dict__.pop("_df_flip", None)
    check(authsrv.DIVINE_FAVOR is True and src.count("\nDIVINE_FAVOR = True ") == 1
          and getattr(ap.parse_args([]), "no_divine_favor", None) is False
          and getattr(ap.parse_known_args(["--no-divine-favor"])[0], "no_divine_favor",
                      None) is True
          and flipped is False,
          "DIVINE_FAVOR ships ON, --no-divine-favor parses, and main()'s block, executed, "
          "sets the MODULE's bool to False", f"flip {i_flip} -> {flipped}")

    def _after_heal(name):
        """Each divine_favor_word call in `name` is a statement of its own whose
        IMMEDIATELY preceding statement in the same block calls resolve_heal --
        anchored on the statement, not on the first `resolve_heal(` in the text
        (land_skill has two: its attack arm's comes first and is not the spell's)."""
        fn = _func(tree, name)
        verdicts = []
        for node in ast.walk(fn):
            for field in ("body", "orelse", "finalbody"):
                block = getattr(node, field, None)
                if not isinstance(block, list):
                    continue
                for i, stmt in enumerate(block):
                    val = getattr(stmt, "value", None)
                    if not (isinstance(stmt, (ast.Expr, ast.Assign)) and isinstance(val, ast.Call)
                            and getattr(val.func, "id", None) == "divine_favor_word"):
                        continue
                    verdicts.append(i > 0 and bool(_calls(block[i - 1], "resolve_heal")))
        return verdicts == [True] and len(_calls(fn, "divine_favor_word")) == 1
    check(_after_heal("cast_tick") and _after_heal("land_skill")
          and not _calls(_func(tree, "pick_skill"), "divine_favor_word"),
          "one call each in cast_tick (the player) and land_skill (every body), each the "
          "statement right after a resolve_heal; pick_skill none",
          f"cast_tick {_after_heal('cast_tick')}, land_skill {_after_heal('land_skill')}")


def _completions(cap, connection):
    """Every [58] on one connection, as (caster, skill, [(recipient, f)], maxima):
    the skill is the caster's LAST [60] BEFORE the [58] in wire order -- a [58] that
    shares its instant with the caster's next [60] closes the PREVIOUS cast (four
    Resurrection Signet completions on the Smiting tape were once credited to the
    Monk spell begun in the same instant, and read as empty batches); the words are
    the caster's positive property-55 words in the [58]'s batch (healjoin.batches,
    the 50 ms shoulder, over deepwoundjoin.sequence); `maxima` is every property-42
    value each agent is sent on the connection."""
    import bufflog
    import deepwoundjoin
    import healjoin
    seq = deepwoundjoin.sequence(cap, connection, bufflog.Codec())
    maxima = {}
    for _i, _t, op, v in seq:
        if op == 0x009F and v[1] == 42:
            maxima.setdefault(v[2], set()).add(v[3])
    ann = {}
    for batch in healjoin.batches(seq):
        words, closed = [], []
        for _i, _t, op, v in batch:
            if op == 0x009F and v[1] == 58:
                closed.append((v[2], ann.get(v[2])))
            elif op == 0x00A0 and v[1] == 60:
                ann[v[2]] = v[4]
            elif op == 0x009F and v[1] == 60:
                ann[v[2]] = v[3]
            elif op == 0x00A3 and v[1] == 55 and _f(v[4]) > 0:
                words.append((v[2], v[3], _f(v[4])))
        for caster, skill in closed:
            yield caster, skill, [(tg, f) for tg, cs, f in words if cs == caster], maxima


def _readable(mine, maxima):
    """The whole-point values of a completion's words, each read over a maximum its
    OWN recipient is sent on the wire -- or None when any word is whole over none of
    them (a pool that moved where the observer did not see it: unreadable, set aside)."""
    out = set()
    for tg, f in mine:
        vals = {int(round(f * m)) for m in maxima.get(tg, ()) if abs(f * m - round(f * m)) < 1e-3}
        if not vals:
            return None
        out |= vals
    return out


def section_df_tape():
    print("== 15. the tape: the level-20 Monks' +42 on " + DF_CAPTURE + " :" + DF_CONN + " ==")
    got = _need(("captures", "live"), ("content",),
                what="Divine Favor on the henchman tape, priced by the vault's skills table "
                     "(2 checks)")
    if got is None:
        return None
    import deepwoundjoin
    cap = os.path.join(got[0], DF_CAPTURE)
    chans = [c for c in deepwoundjoin.whole_s2c(cap, None) if DF_CONN in c["connection"]]
    rows = content.load().rows("skills")
    tally = {"eligible": 0, "carries": 0, "outside": 0, "outside_carries": 0,
             "with_base": 0, "df_last": 0, "cut": 0}
    values = {}

    for ch in chans:
        conn_max = set()

        def pts(f, want):
            # over a maximum THIS connection sends (its own 0x009F [42] words: the
            # henchmen's 555, the 455 under the cut -- Deep Wound's by
            # RECONSTRUCTION, studies/skills 66.4 -- the observer's 480). Any
            # maximum the connection sends, at any time: Healing Touch's 67 at
            # 687.55 reads whole over a 455 sent 1.18 s after it (a reading).
            return any(abs(f * m - want) < 1e-3 for m in conn_max)
        for caster, skill, mine, maxima in _completions(cap, ch["connection"]):
            conn_max = {m for ms in maxima.values() for m in ms if m >= 100}
            row = rows.get(str(skill))
            if caster not in DF_CASTERS or row is None or int(row.get("profession", -1)) != 3:
                continue
            c = attribpassive.divine_favor_bonus(DF_RANK, skill)
            hit = [k for k, (_tg, f) in enumerate(mine)
                   if pts(f, c) or pts(f, round(0.8 * c))]
            inside = attribpassive.divine_favor_applies(row)
            tally["eligible" if inside else "outside"] += 1
            if inside and skill not in attribpassive.DIVINE_FAVOR_MULTIPLIER:
                for x in _readable(mine, maxima) or ():
                    values[x] = values.get(x, 0) + 1
            if not hit:
                continue
            tally["carries" if inside else "outside_carries"] += 1
            tg = mine[hit[0]][0]
            same = [k for k, (t2, _f2) in enumerate(mine) if t2 == tg]
            if len(same) > 1:
                tally["with_base"] += 1
                tally["df_last"] += int(hit[0] == same[-1])
            tally["cut"] += int(any(pts(f, round(0.8 * c)) and not pts(f, c)
                                    for _tg, f in mine))
    check(tally["eligible"] == DF_TAPE["eligible"] and tally["carries"] == tally["eligible"]
          and tally["outside"] == DF_TAPE["outside"] and tally["outside_carries"] == 0
          and tally["cut"] == DF_TAPE["cut"],
          f"every one of the two Monks' {tally['eligible']} Monk spells cast on an ally "
          f"carries the word attribpassive prices at rank {DF_RANK} (42; Healing Touch's "
          f"84; {tally['cut']} under the 0.8 cut); their {tally['outside']} resurrections "
          f"carry none", f"{tally}")
    check(tally["with_base"] >= DF_TAPE["with_base"] and tally["df_last"] == tally["with_base"],
          "where the spell has its own heal on the same recipient, the Divine Favor word "
          "comes LAST, every time", f"{tally['df_last']} of {tally['with_base']}")
    # The constant MEASURED, for section 16: the whole-point value the most readable
    # completions share, each word over its own recipient's on-wire maxima.
    return max(values, key=lambda x: (values[x], -x)) if values else None


def section_df_smite(c_hench):
    print("== 16. the tape: the Smiting Monks' +3 on " + SMITE_CAPTURE
          + ", and the rounding the two constants decide ==")
    got = _need(("captures", "live"), ("content",),
                what="Divine Favor on the Smiting tape, and the rounding (2 checks)")
    if got is None:
        return
    import deepwoundjoin
    cap = os.path.join(got[0], SMITE_CAPTURE)
    rows = content.load().rows("skills")
    tally = {"eligible": 0, "readable": 0, "carries": 0, "outside": 0, "outside_words": 0,
             "signet": 0, "signet_words": 0}
    values = {}
    c = attribpassive.divine_favor_bonus(SMITE_RANK)
    for ch in deepwoundjoin.whole_s2c(cap, None):
        for caster, skill, mine, maxima in _completions(cap, ch["connection"]):
            if caster not in SMITE_CASTERS:
                continue
            if skill == RES_SIGNET:
                tally["signet"] += 1
                tally["signet_words"] += len(mine)
                continue
            row = rows.get(str(skill))
            if row is None or int(row.get("profession", -1)) != 3:
                continue
            if not attribpassive.divine_favor_applies(row):
                tally["outside"] += 1
                tally["outside_words"] += len(mine)
                continue
            tally["eligible"] += 1
            vals = _readable(mine, maxima) if mine else None
            if vals is None:
                continue
            tally["readable"] += 1
            tally["carries"] += int(attribpassive.divine_favor_bonus(SMITE_RANK, skill) in vals)
            if skill not in attribpassive.DIVINE_FAVOR_MULTIPLIER:
                for x in vals:
                    values[x] = values.get(x, 0) + 1
    c_smite = max(values, key=lambda x: (values[x], -x)) if values else None
    check(tally["eligible"] == SMITE_TAPE["eligible"] and tally["readable"] == SMITE_TAPE["readable"]
          and tally["carries"] == tally["readable"] and c_smite == c
          and tally["outside"] == SMITE_TAPE["outside"] and tally["outside_words"] == 0
          and tally["signet"] == SMITE_TAPE["signet"] and tally["signet_words"] == 0,
          f"the four Smiting Monks' {tally['eligible']} Monk spells on an ally: every one of "
          f"the {tally['readable']} whose words read whole over their recipients' on-wire "
          f"maxima carries {c} -- attribpassive's word at rank {SMITE_RANK}, and the value "
          f"those completions share most ({c_smite}); their {tally['outside']} foe hexes and "
          f"{tally['signet']} Resurrection Signets carry no word", f"{tally}, shared {c_smite}")
    image = {attribpassive.divine_favor_bonus(r) for r in range(0, 41)}
    ceil_image = {-(-32 * r // 10) for r in range(0, 41)}
    floor_image = {(32 * r) // 10 for r in range(0, 41)}
    check(c_smite is not None and c_hench is not None
          and {c_smite, c_hench} <= image and c_smite not in ceil_image
          and c_hench not in floor_image,
          f"THE ROUNDING, from the two constants read off the tape: {c_smite} (here) and "
          f"{c_hench} (section 15) are both in the shipped rule's image; KNOWN-BAD ceil(3.2 r) "
          f"never makes {c_smite} and KNOWN-BAD floor(3.2 r) never makes {c_hench}",
          f"smite {c_smite} hench {c_hench}; ceil has it {c_smite in ceil_image}, floor has "
          f"it {c_hench in floor_image}")


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
    section_df_rule()
    section_df_scope()
    section_df_server()
    section_df_wiring()
    c_hench = section_df_tape()
    section_df_smite(c_hench)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
