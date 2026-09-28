r"""test_interruptshots -- CASTAI-ZF21: the damage clauses of the Zaishen tape's two
interrupters (2026-09-28; studies/monsterai FINDINGS 18.2).

    python toolkit/authsrv/test_interruptshots.py

WHAT IT IS REALLY CHECKING. The Degeneration Ranger (agent 6, 20260928T103123) shot
Distracting Shot 399 and Savage Shot 426. Its damage words, turned into points by the
victim's maximum, say:
  * 399 deals ONE amount, 8, on every hit whose maximum is known -- on a warrior, on
    a monk henchman twice and on a critical. That is GWW's "deals only 1...16", whose
    variable is "Armor-ignoring damage". ATTACK_FIXED_DAMAGE: an attack skill with that
    scale deals exactly the row's amount in place of its weapon's number.
  * 426's "+13...28" lands only on a target activating a spell (WIKI; the henchman's
    words sit above the Ranger's plain shots, and the observer's signet took a plain
    shot doubled by Healing Signet's -40). BONUS_REQUIRES_SPELL: the row's
    `bonus_requires = "spell"`, judged at the hit.

  1  the rules on the carried rows: the two scales, attack_fixed_damage,
     activating_spell and strike_bonus_at_hit, each flag's revert.
  2  body -> player (land_swing), the observer's two cases: 399 is 8 through Healing
     Signet's -40 while a plain shot doubles; 426's bonus on a spell and not on a
     signet; the known-bad arms.
  3  body -> body (land_swing_on_body): 399 is 8 at two armour ratings; 426 on a spell.
  4  player -> hostile (hit_enemy): 399 is the row's amount at two armour ratings,
     and a forced critical sends property 17 carrying the same amount.
  5  the arrow's ARRIVAL decides (land_body_skill_shot): one strike, two targets.
  6  end to end: a hostile archer's 399 through enemy_attack_tick and
     body_projectile_tick lands 8 on the player mid-cast, then the interrupt.
  7  source and content: both flags default on, plumbed, and the two rows.
  8  the vault: the carried rows against the table, and the tape's witnesses in
     points. Skips ONLY when the vault's skills table or the capture is absent.

The skill rows are carried (skilltable.py's record, build 38797 -- measured numbers,
CLAUDE.md's gate) and REPLACE the table for the driven sections, so a vault run takes
exactly the bare path (test_bodywindup's pattern).
"""
import contextlib
import io
import os
import random
import struct
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
import vaultpath                                               # noqa: E402

# Floor from the BARE-MACHINE green run (RURIK_VAULT at an empty directory), 2026-09-28,
# MEASURED: 19 -- sections 1-7 (5 + 5 + 2 + 3 + 1 + 1 + 2), section 8
# skipping by name. The first cut declared 21 from a guess and the run said 19. The
# vault adds section 8's five: 24.
LEDGER = checks.Ledger("the two interrupters' damage clauses (CASTAI-ZF21)", floor=19)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
FLT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
DISTRACT, SAVAGE, SIGNET, SKILL2, BREEZE = 399, 426, 1, 2, 288
EXPERTISE, MARKSMANSHIP = 23, 25
RANK = 7                              # 399 at rank 7 is the tape's 8; 426 is +20 there
HOSTILE, HENCH, FOE = 10, 8, 104
CAPTURE = "20260928T103123"


def _record(activation, aftercast, recharge, energy, attribute, profession, type_code,
            target, skill_arguments, scale, bonus_scale, duration, weapon_req,
            projectile, impact_visual):
    return {"activation": activation, "aftercast": aftercast, "recharge": recharge,
            "energy": energy, "adrenaline": 0, "adrenaline_units": 0,
            "attribute": attribute, "profession": profession, "type_code": type_code,
            "target": target, "combo": 0, "combo_req": 0, "weapon_req": weapon_req,
            "aoe_range": 0.0, "skill_arguments": skill_arguments,
            "duration0": duration[0], "duration15": duration[1],
            "scale0": scale[0], "scale15": scale[1], "bonus_scale0": bonus_scale[0],
            "bonus_scale15": bonus_scale[1], "projectile": projectile,
            "impact_visual": impact_visual, "touch_range": False, "half_range": False}


# skilltable.py's record, build 38797 (the vault's content/skills.toml; section 8
# checks each row against it). 399 / 426 bow attacks; 1 / 2 signets; 288 a spell.
RECORD = {
    "399": _record(0.5, 1.5, 10, 5, EXPERTISE, 2, 14, 5, 2, (1, 16), (20, 20), (0, 0), 2, 728, 729),
    "426": _record(0.5, 1.5, 5, 10, MARKSMANSHIP, 2, 14, 5, 2, (13, 28), (0, 0), (0, 0), 2, 2077, 2077),
    "1": _record(2.0, 0.75, 4, 0, 21, 1, 7, 0, 2, (82, 172), (0, 0), (0, 0), 0, 2077, 2077),
    "2": _record(3.0, 0.0, 0, 0, 51, 0, 7, 6, 6, (100, 100), (25, 25), (0, 0), 0, 2077, 2077),
    "288": _record(1.0, 0.75, 5, 10, 13, 3, 6, 3, 2, (4, 9), (0, 0), (15, 15), 0, 2077, 505),
}

FLAGS = ("ATTACK_FIXED_DAMAGE", "BONUS_REQUIRES_SPELL", "INTERRUPTS", "ENERGY",
         "NPC_FOLLOW", "EFFECTS", "NPC_ATTACK_SKILL_SWINGS", "INSTANT_ANNOUNCE",
         "CASTING_ARMOUR")


@contextlib.contextmanager
def arm(**flags):
    """The carried rows as the skills table and the named flags, all restored after;
    stdout captured (the landings narrate every hit)."""
    saved = {k: getattr(authsrv, k) for k in FLAGS}
    tables = agents.WORLD.tables
    had, kept = "skills" in tables, tables.get("skills")
    base = {"ATTACK_FIXED_DAMAGE": True, "BONUS_REQUIRES_SPELL": True, "INTERRUPTS": True,
            "ENERGY": False, "NPC_FOLLOW": False, "EFFECTS": True,
            "NPC_ATTACK_SKILL_SWINGS": True, "INSTANT_ANNOUNCE": True,
            "CASTING_ARMOUR": True}
    base.update(flags)
    for k, v in base.items():
        setattr(authsrv, k, v)
    tables["skills"] = {k: dict(v) for k, v in RECORD.items()}
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


def _f32(dw):
    return struct.unpack("<f", struct.pack("<I", int(dw) & 0xFFFFFFFF))[0]


def _archer(allegiance=None, pos=(300.0, 0.0), skills=()):
    return {"name": "an archer", "dead": False, "died_at": 0.0, "health": 1e6,
            "max_health": 1e6, "last_hit": 0.0, "pos": pos, "plane": 0,
            "allegiance": allegiance or agents.ALLEGIANCE_HOSTILE, "attack_speed": 2.475,
            "effects": 0, "attacks_back": True, "weapon_item": "hostile_bow",
            "npc": {"profession": 2, "level": 20},
            "attributes": {EXPERTISE: RANK, MARKSMANSHIP: RANK},
            "skills": skills, "skill_ready": [0.0] * len(skills)}


def _cast(skill_id, now, attack=False):
    """A player entry IN ACTIVATION (test_interrupt's _cast shape)."""
    return {"skill_id": skill_id, "copy": 0, "begun": True, "cost": 0, "units": 0,
            "target": None, "begin_at": now, "attack": attack, "e5_at": now + 1.0,
            "e3_at": now + 1.75, "e6_at": now + 5.0, "recharge": 4, "e5_sent": False,
            "e3_sent": False, "approach": None, "activation": 2.0, "aftercast": 0.75,
            "recharge_s": 4.0}


def _world(player_casting=None):
    """The player (casting `player_casting`, if any) and a hostile archer."""
    st = {"agents": {HOSTILE: _archer()}, "pos": (0.0, 0.0), "action_hold": 1,
          "player_dead": False}
    authsrv.player_pools(st)
    st["player_health"] = float(authsrv.player_max_health(st))
    authsrv.effect_table(st)
    if player_casting is not None:
        st["pending_casts"] = [_cast(player_casting, authsrv.time.time())]
    return st


def _body(skill_id=None, armour=60):
    """A party henchman (555 max, the tape's), casting `skill_id` if given."""
    now = authsrv.time.time()
    row = {"name": "a henchman", "dead": False, "died_at": 0.0, "health": 555.0,
           "max_health": 555.0, "last_hit": 0.0, "pos": (10.0, 0.0), "plane": 0,
           "allegiance": agents.ALLEGIANCE_PLAYER, "armor_rating": armour, "effects": 0,
           "attacks_back": False, "skills": ((skill_id or BREEZE, 1.0, 5.0),),
           "skill_ready": [0.0], "casting": None, "cast_lands_at": None}
    if skill_id is not None:
        row.update(casting=0, cast_lands_at=now + 1.0)
    return row


def _word(sent, victim, cause):
    """(property, points-as-fraction) of the first damage word at `victim` by `cause`."""
    for op, v in sent:
        if op == FLT_T and len(v) > 3 and v[0] in (16, 17) and v[1] == victim and v[2] == cause:
            return v[0], -_f32(v[3])
    return None, None


def _sender():
    sent = []
    return sent, (lambda op, vals, why="", quiet=False: sent.append((op, list(vals))))


def body_at_player(skill_id, bonus, casting, seed=7):
    """land_swing: the hostile archer's `skill_id` at the player activating `casting`.
    Returns (points, property, sent)."""
    random.seed(seed)
    st = _world(casting)
    sent, send = _sender()
    authsrv.land_swing(send, st, HOSTILE, st["agents"][HOSTILE], 0, bonus=bonus,
                       skill_id=skill_id)
    prop, frac = _word(sent, P, HOSTILE)
    pts = None if frac is None else round(frac * authsrv.player_max_health(st), 3)
    return pts, prop, sent


def body_at_body(skill_id, bonus, casting, armour=60, seed=7):
    """land_swing_on_body: the hostile archer's `skill_id` at a henchman."""
    random.seed(seed)
    st = _world()
    st["agents"][HENCH] = _body(casting, armour)
    sent, send = _sender()
    authsrv.land_swing_on_body(send, st, HOSTILE, st["agents"][HOSTILE], HENCH, 0,
                               bonus=bonus, skill_id=skill_id)
    prop, frac = _word(sent, HENCH, HOSTILE)
    return (None if frac is None else round(frac * 555.0, 3)), prop, sent


def player_at_foe(skill_id, bonus, casting, armour=60, seed=7):
    """hit_enemy: the player's `skill_id` strike at a hostile (1000 max)."""
    random.seed(seed)
    st = _world()
    foe = _body(casting, armour)
    foe.update(allegiance=agents.ALLEGIANCE_HOSTILE, health=1000.0, max_health=1000.0)
    st["agents"][FOE] = foe
    sent, send = _sender()
    authsrv.hit_enemy(send, st, FOE, 0, bonus_damage=bonus, skill_strike=True,
                      skill_id=skill_id)
    prop, frac = _word(sent, FOE, P)
    return (None if frac is None else round(frac * 1000.0, 3)), prop, sent


# ---------------------------------------------------------------------------------
def section_rules():
    print("== 1. the rules on the carried rows ==")
    with arm():
        sd = [authsrv.skill_damage(DISTRACT, r) for r in (0, RANK, 15)]
        ss = [authsrv.skill_damage(SAVAGE, r) for r in (0, RANK, 15)]
        check(sd == [(1, "standalone"), (8, "standalone"), (16, "standalone")]
              and ss == [(13, "additive"), (20, "additive"), (28, "additive")],
              "399's scale is 'Armor-ignoring damage' 1..16 (8 at rank 7, the tape's number); "
              "426's is '+ Damage' 13..28", f"{sd} {ss}")
        archer = _archer()
        saved = agents.PLAYER_ATTRIBUTE_RANKS
        try:
            agents.PLAYER_ATTRIBUTE_RANKS = ((EXPERTISE, RANK),)
            fx = [authsrv.attack_fixed_damage({}, HOSTILE, archer, DISTRACT),
                  authsrv.attack_fixed_damage({}, P, None, DISTRACT),
                  authsrv.attack_fixed_damage({}, HOSTILE, archer, SAVAGE),
                  authsrv.attack_fixed_damage({}, HOSTILE, archer, BREEZE),
                  authsrv.attack_fixed_damage({}, HOSTILE, archer, None)]
        finally:
            agents.PLAYER_ATTRIBUTE_RANKS = saved
        check(fx == [8.0, 8.0, None, None, None],
              "attack_fixed_damage: 399 at the attacker's own rank 7 is 8 (a body's "
              "attributes, the player's ranks); a '+ Damage' attack, a spell and no skill "
              "have none", f"{fx}")
    with arm(ATTACK_FIXED_DAMAGE=False):
        off = authsrv.attack_fixed_damage({}, HOSTILE, _archer(), DISTRACT)
    check(off is None, "  --no-attack-fixed-damage: none (the weapon's number lands)", f"{off}")
    with arm():
        spells = [authsrv.activating_spell(_world(s), P) for s in (BREEZE, SIGNET, SKILL2, None)]
        st = _world()
        st["pending_casts"] = [_cast(DISTRACT, authsrv.time.time(), attack=True)]
        spells.append(authsrv.activating_spell(st, P))
        st = _world()
        for k, row in ((HENCH, _body(BREEZE)), (HENCH + 1, _body(SKILL2)), (HENCH + 2, _body())):
            st["agents"][k] = row
        spells += [authsrv.activating_spell(st, k) for k in (HENCH, HENCH + 1, HENCH + 2)]
    check(spells == [BREEZE, None, None, None, None, BREEZE, None, None],
          "activating_spell: the player's open Healing Breeze (a spell) is one; Healing "
          "Signet, skill 2 (signets), no cast and an attack skill are not; a body casting "
          "288 is, casting skill 2 is not, idle is not", f"{spells}")
    with arm():
        g = [authsrv.strike_bonus_at_hit(_world(BREEZE), SAVAGE, P, 20.0, 0, "t"),
             authsrv.strike_bonus_at_hit(_world(SIGNET), SAVAGE, P, 20.0, 0, "t"),
             authsrv.strike_bonus_at_hit(_world(), SAVAGE, P, 20.0, 0, "t"),
             authsrv.strike_bonus_at_hit(_world(), DISTRACT, P, 5.0, 0, "t")]
    with arm(BONUS_REQUIRES_SPELL=False):
        g.append(authsrv.strike_bonus_at_hit(_world(SIGNET), SAVAGE, P, 20.0, 0, "t"))
    check(g == [20.0, 0.0, 0.0, 5.0, 20.0],
          "strike_bonus_at_hit: 426's +20 on a spell, none on a signet or an idle target; "
          "a row with no `bonus_requires` is untouched; --no-bonus-requires-spell lands it "
          "on the signet", f"{g}")


def section_body_player():
    print("== 2. body -> player (land_swing): the observer's two cases ==")
    with arm():
        d2, p2, sent2 = body_at_player(DISTRACT, 0.0, SKILL2)
        plain2, _p, _s = body_at_player(SAVAGE, 0.0, SKILL2)
        plain1, _p, _s = body_at_player(SAVAGE, 0.0, SIGNET)
        # over 20 seeds: our hostile_bow lands 1..4 on the player, so one pair is
        # rounding noise and the control is the sum (measured 59 -> 113, x 1.92)
        seeds = range(1, 21)
        d_all = {body_at_player(DISTRACT, 0.0, c, seed=s)[0] for s in seeds
                 for c in (SKILL2, SIGNET)}
        sum2 = sum(body_at_player(SAVAGE, 0.0, SKILL2, seed=s)[0] for s in seeds)
        sum1 = sum(body_at_player(SAVAGE, 0.0, SIGNET, seed=s)[0] for s in seeds)
    i_w = next((i for i, (op, v) in enumerate(sent2) if op == FLT_T and v[1] == P), None)
    i35 = next((i for i, (op, v) in enumerate(sent2) if op == INT and v[:2] == [35, P]), None)
    check(d2 == 8.0 and p2 == 16 and i_w is not None and i35 is not None and i_w < i35,
          "399 at the player mid-cast of skill 2 (621.054's shape): the word is exactly 8, "
          "then the interrupt's [35]", f"{d2} prop {p2}")
    check(d_all == {8.0} and sum2 and 1.7 < sum1 / sum2 < 2.2,
          "  and 8 on all 20 seeds, on skill 2 and through Healing Signet's -40 alike, "
          "where the same plain shot's total doubles (the armour term is live; 399 "
          "ignores it)", f"399 {sorted(d_all)}; plain totals {sum2} -> {sum1}")
    with arm():
        s_spell, _p, _s = body_at_player(SAVAGE, 20.0, BREEZE)
        s_sig2, _p, _s = body_at_player(SAVAGE, 20.0, SKILL2)
        s_zero2, _p, _s = body_at_player(SAVAGE, 0.0, BREEZE)
        s_sig1, _p, _s = body_at_player(SAVAGE, 20.0, SIGNET)
    check(s_spell - s_zero2 == 20.0 and s_sig2 == plain2,
          "426 +20 on the player activating a spell (Healing Breeze); none on skill 2",
          f"spell {s_spell} vs bonus-less {s_zero2}; skill 2 {s_sig2} vs plain {plain2}")
    check(s_sig1 == plain1,
          "  and none on Healing Signet (197.153's shape): the plain shot doubled by the "
          "signet's -40 and nothing on top", f"{s_sig1} vs {plain1}")
    with arm(ATTACK_FIXED_DAMAGE=False):
        bad_d, _p, _s = body_at_player(DISTRACT, 0.0, SKILL2)
    with arm(BONUS_REQUIRES_SPELL=False):
        bad_s, _p, _s = body_at_player(SAVAGE, 20.0, SKILL2)
    check(bad_d == plain2 and bad_d != 8.0 and bad_s == plain2 + 20.0,
          "  KNOWN-BAD ARMS: --no-attack-fixed-damage lands 399 as the weapon's shot; "
          "--no-bonus-requires-spell puts 426's +20 on a signet",
          f"399 {bad_d}, 426 {bad_s} (plain {plain2})")


def section_body_body():
    print("== 3. body -> body (land_swing_on_body) ==")
    with arm():
        d60, _p, _s = body_at_body(DISTRACT, 0.0, SKILL2, armour=60)
        d100, _p, _s = body_at_body(DISTRACT, 0.0, SKILL2, armour=100)
        p60, _p, _s = body_at_body(SAVAGE, 0.0, SKILL2, armour=60)
        p100, _p, _s = body_at_body(SAVAGE, 0.0, SKILL2, armour=100)
        sp, _p, sent = body_at_body(SAVAGE, 20.0, BREEZE)
        z, _p, _s = body_at_body(SAVAGE, 0.0, BREEZE)
        sg, _p, _s = body_at_body(SAVAGE, 20.0, SKILL2)
    check(d60 == 8.0 and d100 == 8.0 and p60 != p100,
          "399 on a henchman is 8 at armour 60 and at 100, where the plain shot is not the "
          "same number twice", f"399 {d60} / {d100}; plain {p60} / {p100}")
    i35 = next((i for i, (op, v) in enumerate(sent) if op == INT and v[:2] == [35, HENCH]), None)
    check(sp - z == 20.0 and sg == p60 and i35 is not None,
          "426 on a henchman activating 288: +20, then its [59] [35]; on skill 2: none",
          f"{sp} vs {z}; skill 2 {sg} vs {p60}")


def section_player_foe():
    print("== 4. player -> hostile (hit_enemy) ==")
    saved = agents.PLAYER_ATTRIBUTE_RANKS
    real_rate, real_wrank = authsrv.critical_rate, authsrv.player_weapon_rank
    try:
        agents.PLAYER_ATTRIBUTE_RANKS = ((EXPERTISE, RANK), (MARKSMANSHIP, RANK))
        # the weapon's rank is what the critical is rolled on; a bare machine's weapon
        # row carries no attribute (None, and no roll), so it is rebound for both runs
        authsrv.player_weapon_rank = lambda state: 12
        with arm():
            a60, pr60, _s = player_at_foe(DISTRACT, 0.0, SKILL2, armour=60)
            a120, pr120, _s = player_at_foe(DISTRACT, 0.0, SKILL2, armour=120)
            authsrv.critical_rate = lambda rank: 1.0
            ac, prc, _s = player_at_foe(DISTRACT, 0.0, SKILL2)
            authsrv.critical_rate = real_rate
            sp, _p, _s = player_at_foe(SAVAGE, 20.0, BREEZE)
            z, _p, _s = player_at_foe(SAVAGE, 0.0, BREEZE)
            sg, _p, _s = player_at_foe(SAVAGE, 20.0, SKILL2)
            zg, _p, _s = player_at_foe(SAVAGE, 0.0, SKILL2)
    finally:
        agents.PLAYER_ATTRIBUTE_RANKS = saved
        authsrv.critical_rate, authsrv.player_weapon_rank = real_rate, real_wrank
    check(a60 == 8.0 and a120 == 8.0,
          "the player's 399 at rank 7 strikes a hostile for 8 at armour 60 and at 120",
          f"{a60} (prop {pr60}) / {a120} (prop {pr120})")
    check(ac == 8.0 and prc == 17,
          "  a forced critical sends property 17 carrying the same 8 (agent 10's shape on "
          "the tape: a critical, 8)", f"{ac} prop {prc}")
    check(sp - z == 20.0 and sg == zg,
          "the player's 426: +20 on a hostile activating a spell, none on skill 2",
          f"{sp} vs {z}; {sg} vs {zg}")


def section_arrival():
    print("== 5. the arrow's ARRIVAL decides (land_body_skill_shot) ==")
    strike = {"skill_id": SAVAGE, "rank": RANK, "bonus": 20.0, "inflicted": None,
              "knock_down": False, "mult": 1.0, "first": True}
    out = []
    with arm():
        for casting in (BREEZE, None):
            random.seed(7)
            st = _world(casting)
            sent, send = _sender()
            authsrv.land_body_skill_shot(send, st, 0, {"shooter": HOSTILE, "target": P},
                                         st["agents"][HOSTILE], dict(strike))
            _prop, frac = _word(sent, P, HOSTILE)
            out.append(round(frac * authsrv.player_max_health(st), 3))
    check(out[0] - out[1] == 20.0,
          "one strike released with +20: it lands on a player activating a spell at the "
          "ARRIVAL and not on one who is not -- judged at the hit, not at the release",
          f"{out}")


def section_end_to_end():
    print("== 6. end to end: a hostile archer's 399 through the real ticks ==")
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
    sends = []
    try:
        authsrv.time = Clock(t0)
        with arm():
            st = _world(SKILL2)
            st["pending_casts"][0].update(e5_at=t0 + 30.0, e3_at=t0 + 31.0, e6_at=t0 + 40.0)
            st["agents"][HOSTILE] = _archer(pos=(600.0, 0.0),
                                            skills=((DISTRACT, 0.5, 10.0),))

            def send(op, vals, why="", quiet=False):
                sends.append((op, list(vals)))
            for i in range(3001):
                authsrv.time.t = t0 + i * 0.001
                authsrv.enemy_attack_tick(send, st, 0)
                authsrv.body_projectile_tick(send, st, 0)
                if any(op == FLT_T and v[1] == P for op, v in sends):
                    break
            mx = authsrv.player_max_health(st)
    finally:
        authsrv.time = saved_time
    prop, frac = _word(sends, P, HOSTILE)
    pts = None if frac is None else round(frac * mx, 3)
    ann = any(op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
              and v[:4] == [agents.GV_ATTACK_SKILL_ACTIVATED, HOSTILE, P, DISTRACT]
              for op, v in sends)
    launched = any(op == authsrv.GAME_SMSG_AGENT_PROJECTILE_LAUNCHED for op, _v in sends)
    check(ann and launched and pts == 8.0,
          "enemy_attack_tick announces 399 at the player, the arrow launches, and "
          "body_projectile_tick lands exactly 8 on the player mid-cast (the tape's path)",
          f"announce {ann} launched {launched} points {pts} prop {prop}")


def section_source():
    print("== 7. source and content ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    main_at = src.index("\ndef main():")

    def flips(flag, name):
        i = src.find(f"    if a.{flag}:", main_at)
        return i > 0 and f"{name} = False" in src[i:i + 200]
    check(src.count("\nATTACK_FIXED_DAMAGE = True\n") == 1
          and src.count("\nBONUS_REQUIRES_SPELL = True\n") == 1
          and flips("no_attack_fixed_damage", "ATTACK_FIXED_DAMAGE")
          and flips("no_bonus_requires_spell", "BONUS_REQUIRES_SPELL")
          and '"--no-attack-fixed-damage"' in args and '"--no-bonus-requires-spell"' in args
          and src.count("strike_bonus_at_hit(state, skill_id,")
          - src.count("def strike_bonus_at_hit(") == 3
          and src.count("attack_fixed_damage(state, ")
          - src.count("def attack_fixed_damage(") == 3,
          "both flags default ON, each reverted by its own switch in main(); the gate and "
          "the fixed amount are read in all three landings (hit_enemy, land_swing, "
          "land_swing_on_body)")
    r399, r426 = authsrv.skill_effect_row(DISTRACT), authsrv.skill_effect_row(SAVAGE)
    check(r399.get("scale_means") == "Armor-ignoring damage" and r399.get("interrupts") == "action"
          and r426.get("scale_means") == "+ Damage" and r426.get("bonus_requires") == "spell"
          and "Armor-ignoring damage" not in authsrv.ARMOUR_RESPECTING_MEANS,
          "content/world.toml: 399 'Armor-ignoring damage' (not armour-respecting), 426 "
          "'+ Damage' with bonus_requires = 'spell', both still interrupting",
          f"{r399.get('scale_means')} / {r426.get('scale_means')} {r426.get('bonus_requires')}")


def _tape_words(cap_dir, connection):
    import bufflog
    import deepwoundjoin
    seq = deepwoundjoin.sequence(cap_dir, connection, bufflog.Codec())
    words, maxes, ann = [], {}, []
    for _i, t, op, v in seq:
        vals = v[1:]
        if op == 0x00A3 and len(vals) > 3 and vals[0] in (16, 17, 55):
            words.append((round(t, 3), vals[0], vals[1], vals[2], vals[3] & 0xFFFFFFFF))
        elif op == 0x009F and len(vals) > 2 and vals[0] == 42:
            maxes.setdefault(vals[1], []).append((t, vals[2]))
        elif op == 0x00A0 and len(vals) > 3 and vals[0] == 60:
            ann.append((round(t, 3), vals[1], vals[3]))
        elif op == 0x009F and len(vals) > 2 and vals[0] == 60:
            ann.append((round(t, 3), vals[1], vals[2]))
    return words, maxes, ann


def _max_at(maxes, agent, t):
    got = [m for tt, m in maxes.get(agent, ()) if tt <= t]
    return got[-1] if got else None


def _unique_fit(fracs):
    """The maxima in 200..900 that close every fraction to an integer within 1e-3."""
    return [M for M in range(200, 901) if all(abs(f * M - round(f * M)) < 1e-3 for f in fracs)]


def section_vault():
    print("== 8. the vault: the carried rows, the tape's witnesses in points ==")
    try:
        table = agents.WORLD.rows("skills")
        live = vaultpath.require_dir("captures", "live", CAPTURE, why="the ZF21 witnesses")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        LEDGER.skip("8. the vault", str(exc).splitlines()[0])
        return
    if not all(k in table for k in RECORD):
        LEDGER.skip("8. the vault", "the vault's skills table lacks a carried row")
        return
    keys = ("activation", "recharge", "attribute", "type_code", "scale0", "scale15",
            "bonus_scale0", "bonus_scale15", "weapon_req", "skill_arguments")
    diff = {k: [f for f in keys if table[k].get(f) != RECORD[k][f]] for k in RECORD}
    check(all(not v for v in diff.values()),
          "the carried rows equal the vault's table on every field the landings read",
          f"{diff}")
    b = "10.0.0.210:58544->98.95.137.136:80"
    a = "10.0.0.210:50061->54.198.7.73:80"
    wb, mb, _ab = _tape_words(live, b)
    wa, ma, aa = _tape_words(live, a)
    frac = lambda bits: -_f32(bits)                            # noqa: E731
    obs = [w for w in wb if w[0] == 621.054 and w[2] == 7 and w[3] == 6]
    obs_pts = round(frac(obs[0][4]) * _max_at(mb, 7, 621.054), 3) if obs else None
    check(obs_pts == 8.0,
          "399 on the observer, :58544 621.054: the word times its declared maximum "
          "(prop 42, 480) is 8.000", f"{obs_pts}")
    h8 = [w for w in wb if w[2] == 8]
    fit = _unique_fit([abs(_f32(w[4])) for w in h8 if w[4] & 0x7FFFFFFF])
    pts8 = {w[0]: round(frac(w[4]) * 555, 3) for w in h8 if w[3] == 6}
    check(fit == [555] and pts8.get(597.314) == 8.0 and pts8.get(593.808) == 70.0
          and pts8.get(596.455) == 42.0,
          f"agent 8 on :58544: 555 is the ONE maximum closing all {len(h8)} of its words; "
          f"there 399 is 8, 426 on a spell 70, 393 (a plain-damage shot) 42",
          f"fit {fit}; {pts8}")
    crit = [w for w in wb if w[0] == 607.819 and w[2] == 10 and w[3] == 6]
    same = [w for w in wb if w[0] == 597.314 and w[2] == 8 and w[3] == 6]
    check(crit and same and crit[0][1] == 17 and crit[0][4] == same[0][4],
          "agent 10's 399 at 607.819 is a CRITICAL (prop 17) with the same bits as agent "
          "8's (-8/555): a critical does not move the amount",
          f"{crit} / {same}")
    signet = [x for x in aa if x[1] == 7 and x[2] == SIGNET and 196.0 < x[0] < 197.153]
    hit = [w for w in wa if w[0] == 197.153 and w[2] == 7 and w[3] == 6]
    plain = sorted(round(frac(w[4]) * _max_at(m, 7, w[0])) for ws, m in ((wa, ma), (wb, mb))
                   for w in ws if w[2] == 7 and w[3] == 6 and w[0] not in (197.153, 621.054))
    pts = round(frac(hit[0][4]) * _max_at(ma, 7, 197.153), 3) if hit else None
    check(signet and pts == 36.0 and plain and pts == 2 * max(plain)
          and pts < 2 * min(plain) + 13,
          "426 on the observer's Healing Signet (announced 196.949): 36 = 2 x 18, agent "
          "6's largest other word on the observer; a +13 or more on a doubled plain shot "
          "could not be under 2 x its smallest (12) + 13 -- no bonus on a signet",
          f"{pts}; the other words on the observer {plain}")


def main():
    print("test_interruptshots -- CASTAI-ZF21: 399's fixed amount, 426's spell bonus")
    section_rules()
    section_body_player()
    section_body_body()
    section_player_foe()
    section_arrival()
    section_end_to_end()
    section_source()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
