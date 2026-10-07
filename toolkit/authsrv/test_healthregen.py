"""test_healthregen -- the server's half of SKILLS-RG (studies/skills/FINDINGS.md 64): the
SIGNED pip sum with one clamp, the positive rate on property 44, the gain integrated, the
player's natural ramp, and property 32 at full health. Every number is retail's, re-derived by
regenjoin.py off the live corpus (test_regenjoin.py holds those checks).

    python toolkit/authsrv/test_healthregen.py

Runs anywhere: the two skills rows it opens episodes of (446, 288) are CARRIED -- the
client's own record, build 38974 (skilltable.py; identical on 38797 and 38888) -- and section
0 holds them to the vault's rows when the vault has a content DIRECTORY (a declared skip
otherwise; rows that disagree are a FAIL). The hand rows (content/world.toml) are tracked;
the degeneration hex is Suffering 108 (its row carries its endpoints, no skills row read).

  1. net_pips signed, one clamp: regeneration rows subtract, the raw conditions sum before
     the clamp; --no-health-regen is the old cap-then-add degeneration-only server.
  2. property 44 goes positive through the real apply path (446 via `opens_episode`, 288 by
     type), and a positive rate ending on a full agent is [32], not [44] 0
     (--no-max-hp-reached the known-bad arm), below the maximum the [44] zero.
  3. degen_tick integrates the gain: capped at the maximum, never a kill, never on the dead,
     a body too.
  4. the natural ramp: 0 until 5.0 s, +1 per 2.0 s, capped at 7; reset by a growing deficit
     (a hit, degeneration), NOT by a Deep Wound; held by a body casting at the player; zero
     while the effects are a loss and running while they are not; [32] when it fills the
     bar; nothing while dead; --no-natural-regen.
  5. the source: the flags parse (default off), main()'s blocks flip their bools (lifted by
     AST and run), the player's own attack and cast sites call natural_reset, the arrow's
     ARRIVAL does not.
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
import content                                                 # noqa: E402
import effects                                                 # noqa: E402
import vaultpath                                               # noqa: E402

HAVE_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
# Floors from the green runs of 2026-10-07: 38 bare (RURIK_VAULT at an empty directory and at
# a nonexistent path; section 0 a declared skip), 40 with the vault (section 0: 2).
FLOOR_BARE = 38
LEDGER = checks.Ledger("health regeneration on the server",
                       floor=FLOOR_BARE + (2 if HAVE_CONTENT else 0))
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
HERO = 20
FOE = 30
TROLL, BREEZE, SUFFER = 446, 288, 108
BLEED, BURN, POISON = 478, 480, 484
OP_FLOAT, OP_INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
REGEN = agents.GV_CHANGE_HEALTH_REGEN
FULL = agents.GV_MAX_HP_REACHED

# ---- the carried skills rows (skilltable.py, build 38974; section 0 holds them to the vault's)
SKILL_COLUMNS = ("activation", "aftercast", "recharge", "energy", "adrenaline",
                 "adrenaline_units", "attribute", "profession", "type_code", "target",
                 "combo", "combo_req", "weapon_req", "aoe_range", "skill_arguments",
                 "duration0", "duration15", "scale0", "scale15", "bonus_scale0",
                 "bonus_scale15", "projectile", "impact_visual", "touch_range", "half_range")
RECORD_BUILD = 38974
RECORD = {
    "446": (3.0, 0.75, 10, 5, 0, 0, 24, 2, 10, 0, 0, 0, 0, 0.0, 2, 13, 13, 3, 10, 0, 0, 2077, 2077, False, False),
    "288": (1.0, 0.75, 5, 10, 0, 0, 13, 3, 6, 3, 0, 0, 0, 0.0, 2, 15, 15, 4, 9, 0, 0, 2077, 505, False, False),
}


@contextlib.contextmanager
def carried():
    """WORLD's skills table with RECORD's rows laid OVER it for the block, then put back."""
    tables = agents.WORLD.tables
    had = "skills" in tables
    kept = dict(tables.get("skills", {}))
    table = dict(kept)
    for k, cols in RECORD.items():
        table[k] = content.Row(dict(zip(SKILL_COLUMNS, cols)), "skills", k,
                               {"source": "client-table",
                                "extractor": "toolkit/clientscan/skilltable.py",
                                "build": RECORD_BUILD})
    tables["skills"] = table
    try:
        yield
    finally:
        if had:
            tables["skills"] = kept
        else:
            tables.pop("skills", None)


def collector():
    sent = []
    return sent, lambda op, vals, label="", quiet=False: sent.append((op, list(vals), label))


def fresh(health=100.0):
    state = {"agents": {}, "pos": (0.0, 0.0), "player_health": health, "player_dead": False}
    authsrv.effect_table(state)
    return state


def ep(state, skill, rank=0, agent=PLAYER, type_code=6, seconds=15.0):
    return state["effects"].apply(agent, skill, rank, seconds, time.time(), type_code=type_code)


def words(sent):
    return [(op, v) for op, v, _l in sent if (op == OP_FLOAT and v[0] == REGEN)
            or (op == OP_INT and v[0] == FULL)]


def rate_of(v):
    return round(authsrv._f32_of(v[2]), 6)


@contextlib.contextmanager
def flags(**values):
    saved = {k: getattr(authsrv, k) for k in values}
    try:
        for k, v in values.items():
            setattr(authsrv, k, v)
        yield
    finally:
        for k, v in saved.items():
            setattr(authsrv, k, v)


def section_carried():
    print("== 0. the carried rows against the vault's own ==")
    if not HAVE_CONTENT:
        LEDGER.skip("0. carried rows vs vault rows (2 checks)", "no vault/content directory")
        return
    for k, cols in sorted(RECORD.items()):
        row = agents.WORLD.get("skills", k)
        got = tuple(row.get(c) for c in SKILL_COLUMNS)
        check(got == cols and row.provenance.get("build") == RECORD_BUILD,
              f"skills row {k} carried here is the vault's, column for column, build {RECORD_BUILD}",
              f"vault {got} build {row.provenance.get('build')}")


def section_net_pips():
    print("== 1. net_pips: signed, ONE clamp ==")
    st = fresh()
    for s in (BURN, BLEED, POISON):
        ep(st, s, type_code=8)
    check(authsrv.net_pips(st, PLAYER) == 10.0, "Burning + Bleeding + Poison = 14 reads 10")
    ep(st, BREEZE, rank=13)
    check(authsrv.net_pips(st, PLAYER) == 6.0,
          "and with 288 at rank 13 (+8) the net is 14 - 8 = 6: the clamp comes AFTER the sum "
          "(retail's 288 on :50061, -13 + 8 = -5) -- a cap-then-add would read 10 - 8 = 2",
          f"{authsrv.net_pips(st, PLAYER)}")
    with flags(HEALTH_REGEN=False):
        check(authsrv.net_pips(st, PLAYER) == 10.0,
              "KNOWN-BAD ARM, --no-health-regen: the regeneration counts nothing (10)")
    st = fresh()
    ep(st, TROLL, type_code=10)
    check(authsrv.net_pips(st, PLAYER) == -3.0 and authsrv.regen_pips(st, PLAYER) == 3.0,
          "446 alone at rank 0 is -3 net pips (a GAIN of 3): interp(3, 10, 0), retail's +3 3 of 3")
    ep(st, BREEZE, rank=15)
    check(authsrv.net_pips(st, PLAYER) == -10.0,
          "446 (+3) and 288 at rank 15 (+9) clamp at -10, not -12 (the positive side clamps too)")
    st = fresh()
    ep(st, SUFFER, rank=15, type_code=4)
    check(authsrv.net_pips(st, PLAYER) == 3.0 and authsrv.hex_pips(st, PLAYER) == 3.0,
          "Suffering 108 at rank 15 (its row's explicit 0..3) degenerates 3")
    ep(st, BREEZE, rank=13)
    check(authsrv.net_pips(st, PLAYER) == -5.0,
          "108 (-3) under 288 at 13 (+8) nets a gain of 5 -- a hex and the regeneration share "
          "the one sum (retail's :50061 at 201.197: +2 -> -3 with hex 31, 135 and 44)")
    check(effects.pips_from([{"skill": BURN}, {"skill": BLEED}, {"skill": POISON}]) == 10.0
          and effects.pips_from([{"skill": BURN}, {"skill": BLEED}, {"skill": POISON}], cap=False) == 14.0,
          "effects.pips_from keeps its cap by default; cap=False is the raw 14 net_pips sums")


def section_wire():
    print("== 2. property 44 goes positive; [32] ends it at full ==")
    with carried():
        sent, send = collector()
        st = fresh(100.0)
        e = authsrv.apply_effect(send, st, PLAYER, TROLL, 0, PLAYER, 0)
        w = words(sent)
        check(e is not None and e["type_code"] == 10 and abs(e["expires_at"] - e["applied_at"] - 13.0) < 0.01
              and w == [(OP_FLOAT, [REGEN, PLAYER, authsrv._f32(0.06)])],
              "446 opens a 13 s episode through its row's `opens_episode` door and its apply sends "
              "[44, me, +0.06] -- +3 pips x 2 / 100, retail's 446 apply word",
              f"{e and (e['type_code'], e['expires_at'] - e['applied_at'])} {w}")
        sent.clear()
        st["agents"][HERO] = {"name": "monk", "dead": False, "health": 480.0, "max_health": 480.0,
                              "allegiance": agents.ALLEGIANCE_PLAYER, "pos": (0.0, 0.0)}
        e2 = authsrv.apply_effect(send, st, HERO, BREEZE, 13, PLAYER, 0)
        w = words(sent)
        check(e2 is not None and e2["agent"] == PLAYER
              and [rate_of(v) for _op, v in w] == [0.2],
              "a hero's 288 at rank 13 on the player under 446: +3 + 8 = 11 clamps to +10, the "
              "word +10 x 2 / 100 = +0.20", f"{w}")
    st = fresh(100.0)
    sent, send = collector()
    ep(st, TROLL, type_code=10)
    authsrv.push_regen(send, st, PLAYER, 0)
    sent.clear()
    for x in list(st["effects"].live.values()):
        x["expires_at"] = 0.0
    authsrv.effect_tick(send, st, 0)
    w = words(sent)
    check(w == [(OP_INT, [FULL, PLAYER, 0])],
          "446 closing on a FULL player sends 0x009F [32, me, 0] and NO [44] -- retail's regen "
          "closes, 6 of 6 at full; the client's handler zeroes its own rate", f"{w}")
    with flags(MAX_HP_REACHED=False):
        st = fresh(100.0)
        sent, send = collector()
        ep(st, TROLL, type_code=10)
        authsrv.push_regen(send, st, PLAYER, 0)
        sent.clear()
        for x in list(st["effects"].live.values()):
            x["expires_at"] = 0.0
        authsrv.effect_tick(send, st, 0)
        w = words(sent)
        check(w == [(OP_FLOAT, [REGEN, PLAYER, 0])],
              "KNOWN-BAD ARM, --no-max-hp-reached: the same close sends the [44] +0.0", f"{w}")
    st = fresh(60.0)
    sent, send = collector()
    ep(st, TROLL, type_code=10)
    authsrv.push_regen(send, st, PLAYER, 0)
    sent.clear()
    for x in list(st["effects"].live.values()):
        x["expires_at"] = 0.0
    with flags(NATURAL_REGEN=False):
        authsrv.effect_tick(send, st, 0)
    w = words(sent)
    check(w == [(OP_FLOAT, [REGEN, PLAYER, 0])],
          "BELOW the maximum the close is the [44] +0.0 -- [32] would set the client's bar full "
          "(0x009215F0 with 1.0), so it never goes to a hurt agent", f"{w}")
    st = fresh(100.0)
    sent, send = collector()
    ep(st, BLEED, type_code=8)
    authsrv.push_regen(send, st, PLAYER, 0)
    sent.clear()
    for x in list(st["effects"].live.values()):
        x["expires_at"] = 0.0
    authsrv.effect_tick(send, st, 0)
    check([v for _op, v in words(sent)] == [[REGEN, PLAYER, 0]],
          "a DEGENERATION ending sends the [44] zero even on a full pool: [32] ends only a "
          "positive rate (113 of 113 on the corpus follow a positive word)")


def section_integrate():
    print("== 3. degen_tick integrates the gain ==")
    st = fresh(50.0)
    ep(st, TROLL, type_code=10)
    st["degen_at"] = time.time() - 2.0
    sent, send = collector()
    with flags(NATURAL_REGEN=False):
        authsrv.degen_tick(send, st, 0)
    check(abs(st["player_health"] - 62.0) < 0.05 and not sent,
          "446 (+3 pips) for 2 s raises 50 to 62 -- 3 x 2 x 2 -- and sends nothing (the rate "
          "went out once; the client animates it)", f"{st['player_health']} {sent}")
    st["player_health"] = 99.0
    st["degen_at"] = time.time() - 2.0
    with flags(NATURAL_REGEN=False):
        authsrv.degen_tick(send, st, 0)
    check(st["player_health"] == authsrv.player_max_health(st) == 100.0,
          "a gain stops AT the maximum (99 + 12 reads 100)")
    st = fresh(50.0)
    st["player_dead"] = True
    ep(st, TROLL, type_code=10)
    st["degen_at"] = time.time() - 2.0
    authsrv.degen_tick(send, st, 0)
    check(st["player_health"] == 50.0, "a dead player regenerates nothing")
    st = fresh(100.0)
    st["agents"][FOE] = {"name": "troll", "dead": False, "health": 40.0, "max_health": 100.0,
                         "allegiance": agents.ALLEGIANCE_HOSTILE, "pos": (0.0, 0.0)}
    ep(st, TROLL, agent=FOE, type_code=10)
    st["degen_at"] = time.time() - 2.0
    sent, send = collector()
    authsrv.degen_tick(send, st, 0)
    check(abs(st["agents"][FOE]["health"] - 52.0) < 0.05 and not st["agents"][FOE]["dead"] and not sent,
          "a BODY's regeneration episode heals the body the same way, silently (40 -> 52)")
    st = fresh(100.0)
    st["agents"][FOE] = {"name": "troll", "dead": False, "health": -5.0, "max_health": 100.0,
                         "allegiance": agents.ALLEGIANCE_HOSTILE, "pos": (0.0, 0.0)}
    ep(st, TROLL, agent=FOE, type_code=10)
    st["degen_at"] = time.time() - 0.5
    authsrv.degen_tick(send, st, 0)
    check(not st["agents"][FOE]["dead"],
          "a GAIN never kills: a body whose book sits below zero (a Deep Wound's signed shrink) "
          "climbs, it is not sent to kill_agent", f"{st['agents'][FOE]}")


def _ramp(st, ago):
    st.setdefault("natural_regen", {})[PLAYER] = {"anchor": time.time() - ago, "level": 0,
                                                 "deficit": authsrv.player_max_health(st) - st["player_health"]}


def section_natural():
    print("== 4. the natural ramp ==")
    got = {}
    for ago in (4.9, 5.05, 7.05, 9.05, 100.0):
        st = fresh(50.0)
        _ramp(st, ago)
        sent, send = collector()
        authsrv.natural_tick(send, st, 0)
        got[ago] = (authsrv.natural_level(st, PLAYER), [rate_of(v) for _op, v in words(sent)])
    check(got == {4.9: (0, []), 5.05: (1, [0.02]), 7.05: (2, [0.04]), 9.05: (3, [0.06]),
                  100.0: (7, [0.14])},
          "0 before 5.0 s; +1 at 5.0 (the word +1 x 2 / 100), +2 at 7.0, +3 at 9.0; capped at +7 "
          "(retail: P2 19 of 19, P3 45 of 45, the cap on five hostile runs)", f"{got}")
    with flags(NATURAL_DELAY=3.0):
        st = fresh(50.0)
        _ramp(st, 4.0)
        authsrv.natural_tick(lambda *a, **k: None, st, 0)
        early = authsrv.natural_level(st, PLAYER)
    check(early == 1, "the delay is the constant's (a 3 s delay would step at 4 s -- the arm "
          "test_regenjoin scores red on the corpus)", f"{early}")
    st = fresh(50.0)
    _ramp(st, 6.0)
    sent, send = collector()
    authsrv.natural_tick(send, st, 0)
    st["player_health"] -= 10.0                     # a hit between ticks
    sent.clear()
    authsrv.natural_tick(send, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 0 and [rate_of(v) for _op, v in words(sent)] == [0.0],
          "a hit (the deficit grows between ticks) resets the ramp to 0 and the [44] zero goes "
          "out (below the maximum: retail's resets ride a 0 word, 4 of 4)", f"{words(sent)}")
    st = fresh(50.0)
    _ramp(st, 6.0)
    authsrv.natural_tick(lambda *a, **k: None, st, 0)
    authsrv.deep_wound_open(lambda *a, **k: None, st, PLAYER, 0)
    authsrv.natural_tick(lambda *a, **k: None, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 1,
          "a Deep Wound (maximum and health down together) is NOT a loss -- the deficit is "
          "unchanged (studies/isle 8.4 saw no fresh ramp from one)", f"{authsrv.natural_level(st, PLAYER)}")
    st = fresh(50.0)
    _ramp(st, 6.0)
    st["agents"][FOE] = {"name": "caster", "dead": False, "health": 100.0, "max_health": 100.0,
                         "allegiance": agents.ALLEGIANCE_HOSTILE, "pos": (0.0, 0.0),
                         "casting": 0, "cast_target": PLAYER}
    authsrv.natural_tick(lambda *a, **k: None, st, 0)
    held = authsrv.natural_level(st, PLAYER)
    st["agents"][FOE]["cast_target"] = HERO
    _ramp(st, 6.0)
    authsrv.natural_tick(lambda *a, **k: None, st, 0)
    check(held == 0 and authsrv.natural_level(st, PLAYER) == 1,
          "a body casting AT the player holds the ramp at 0 (retail's resets at the activation "
          "and the landing, 4 of 4 witnesses); a cast at somebody else does not")
    st = fresh(50.0)
    _ramp(st, 9.05)
    ep(st, BLEED, type_code=8)
    sent, send = collector()
    authsrv.natural_tick(send, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 3 and authsrv.net_pips(st, PLAYER) == 3.0,
          "P5: under a Bleeding the net is the Bleeding's 3 -- the natural +3 is ZERO while the "
          "effects are a loss (retail: a degeneration onto a ramp reads the effects alone, 6 of 6)")
    st = fresh(50.0)
    _ramp(st, 7.05)
    ep(st, SUFFER, rank=15, type_code=4)
    ep(st, BREEZE, rank=13)
    authsrv.natural_tick(lambda *a, **k: None, st, 0)
    check(authsrv.net_pips(st, PLAYER) == -7.0,
          "and with the effects a GAIN (108's -3 under 288's +8 = +5) the natural +2 adds: -7 "
          "(retail's :50061 ran +3 -> +4 -> +5 with hex 31 live)", f"{authsrv.net_pips(st, PLAYER)}")
    st = fresh(99.0)
    _ramp(st, 5.05)
    sent, send = collector()
    authsrv.natural_tick(send, st, 0)
    st["degen_at"] = time.time() - 1.0
    authsrv.degen_tick(send, st, 0)                 # +1 pip for 1 s: 99 -> 100, full
    sent.clear()
    authsrv.natural_tick(send, st, 0)
    check(st["player_health"] == 100.0 and words(sent) == [(OP_INT, [FULL, PLAYER, 0])]
          and authsrv.natural_level(st, PLAYER) == 0,
          "the ramp filling the bar ends in [32, me, 0], no [44] (retail's 39 observer [32]s "
          "after a natural word with nothing else in the batch)", f"{words(sent)}")
    st = fresh(50.0)
    st["player_dead"] = True
    _ramp(st, 100.0)
    sent, send = collector()
    authsrv.natural_tick(send, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 0 and not sent,
          "a dead player has no natural term, and with none running nothing is sent")
    st = fresh(50.0)
    _ramp(st, 9.05)
    sent, send = collector()
    authsrv.natural_tick(send, st, 0)
    st["player_dead"], st["player_health"] = True, 0.0
    sent.clear()
    authsrv.natural_tick(send, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 0 and words(sent) == [(OP_FLOAT, [REGEN, PLAYER, 0])],
          "a killing blow on a running ramp: the level drops to 0 and the [44] zero goes out once "
          "(not [32]: a corpse is not full) -- retail's reset rides the hit; ours the next tick, "
          "strip_effects' push_regen at a death the precedent", f"{words(sent)}")
    with flags(NATURAL_REGEN=False):
        st = fresh(50.0)
        _ramp(st, 100.0)
        sent, send = collector()
        authsrv.natural_tick(send, st, 0)
        st["degen_at"] = time.time() - 2.0
        authsrv.degen_tick(send, st, 0)
        check(authsrv.natural_level(st, PLAYER) == 0 and st["player_health"] == 50.0 and not sent,
              "KNOWN-BAD ARM, --no-natural-regen: no ramp, no word, health stays at 50 -- the "
              "server before 2026-10-07")
    with flags(HEALTH_REGEN=False):
        st = fresh(50.0)
        _ramp(st, 100.0)
        authsrv.natural_tick(lambda *a, **k: None, st, 0)
        check(authsrv.natural_level(st, PLAYER) == 0,
              "--no-health-regen turns the ramp off too (no positive rate can be sent)")
    st = fresh(50.0)
    _ramp(st, 6.0)
    authsrv.natural_reset(st, PLAYER, "test")
    authsrv.natural_reset(st, FOE, "test")
    authsrv.natural_tick(lambda *a, **k: None, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 0 and FOE not in st["natural_regen"],
          "natural_reset restarts the player's ramp and is a no-op for any other agent "
          "(heroes', henchmen's and hostiles' ramps are measured, not shipped)")
    st = fresh(50.0)
    authsrv.natural_tick(lambda *a, **k: None, st, 0)
    st["natural_regen"][PLAYER]["anchor"] -= 5.05
    st["degen_at"] = time.time() - 1.0
    sent, send = collector()
    authsrv.degen_tick(send, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 1 and abs(st["player_health"] - 52.0) < 0.1
          and [rate_of(v) for _op, v in words(sent)] == [0.02],
          "degen_tick steps the ramp itself and spends it on an effect-less state: +1 pip for "
          "1 s is +2 health, the word sent once", f"{st['player_health']} {words(sent)}")


def section_source():
    print("== 5. the flags, main()'s wiring, and the hook sites ==")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    want = {"no_health_regen": "HEALTH_REGEN", "no_natural_regen": "NATURAL_REGEN",
            "no_max_hp_reached": "MAX_HP_REACHED"}
    parsed = {}
    for dest in want:
        opt = "--" + dest.replace("_", "-")
        parsed[dest] = (getattr(ap.parse_args([]), dest), getattr(ap.parse_args([opt]), dest))
    check(parsed == {d: (False, True) for d in want}
          and all(getattr(authsrv, b) is True for b in want.values()),
          "--no-health-regen, --no-natural-regen and --no-max-hp-reached parse (default off), "
          "and all three behaviours ship ON", f"{parsed}")
    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    flipped = {}
    for dest, name in want.items():
        wiring = [n for n in ast.walk(funcs["main"]) if isinstance(n, ast.If)
                  and isinstance(n.test, ast.Attribute) and n.test.attr == dest]
        for flag in (True, False):
            saved = getattr(authsrv, name)
            try:
                mod = ast.Module(body=wiring, type_ignores=[])
                ast.fix_missing_locations(mod)
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(mod, authsrv.__file__, "exec"),            # noqa: S102
                         authsrv.__dict__, {"a": argparse.Namespace(**{dest: flag})})
                flipped[(dest, flag, len(wiring))] = getattr(authsrv, name)
            finally:
                setattr(authsrv, name, saved)
    check(flipped == {(d, f, 1): (not f) for d in want for f in (True, False)},
          "main()'s three blocks, lifted out of the source and RUN against authsrv's globals, "
          "each flip their own bool (a block without its `global` would not) and leave it "
          "alone without the flag", f"{flipped}")

    def calls(fn, name="natural_reset"):
        return sum(1 for n in ast.walk(funcs[fn]) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == name)
    sites = {fn: calls(fn) for fn in ("attack_tick", "hit_enemy", "launch_player_projectile",
                                      "cast_tick", "launch_body_projectile", "land_skill")}
    check(sites == {"attack_tick": 1, "hit_enemy": 1, "launch_player_projectile": 1,
                    "cast_tick": 1, "launch_body_projectile": 0, "land_skill": 0},
          "the player's swing start, strike, ranged release and cast completion each reset "
          "its ramp once; a BODY's sites never call it (a body's cast at the player is polled "
          "in natural_tick)", f"{sites}")
    guard = [n for n in ast.walk(funcs["hit_enemy"]) if isinstance(n, ast.If)
             and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                     and c.func.id == "natural_reset" for c in ast.walk(n))]
    check(len(guard) == 1 and ast.unparse(guard[0].test) == "not projectile",
          "hit_enemy's reset sits under `not projectile`: an arrow's ARRIVAL is no reset "
          "(retail's hostile 54 ramped 4.40 s after its hit, 5.00 after its launch)")
    check(calls("degen_tick", "natural_tick") == 1
          and calls("net_pips", "regen_pips") == 1 and calls("net_pips", "natural_level") == 1,
          "degen_tick steps the ramp; net_pips reads the regeneration rows and the natural "
          "level once each")


def main():
    print("test_healthregen -- the server's signed pips, natural ramp and property 32 (SKILLS-RG)")
    t0 = time.time()
    section_carried()
    with carried():
        section_net_pips()
        section_integrate()
        section_natural()
        section_wire()
    section_source()
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
