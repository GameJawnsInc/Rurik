"""test_healthregen -- the server's half of SKILLS-RG (studies/skills/FINDINGS.md 64): the
SIGNED pip sum with one clamp, the positive rate on property 44, the gain integrated, the
player's natural ramp, and property 32 at full health. Every number is retail's, re-derived by
regenjoin.py off the live corpus (test_regenjoin.py holds those checks).

    python toolkit/authsrv/test_healthregen.py

Runs anywhere: the skills rows it reads (446, 288 for the regeneration; 108, 160, 230 for the
casts it drives through the real enemy_attack_tick, land_skill and cast_tick) are CARRIED --
the client's own record, build 38974 (skilltable.py; test_mechanics carries the last three
too) -- and section 0 holds them to the vault's rows when the vault has a content DIRECTORY
(a declared skip otherwise; rows that disagree are a FAIL). The hand rows (content/world.toml)
are tracked; the degeneration hex is Suffering 108 (its row carries its endpoints).

  1. net_pips signed, one clamp: regeneration rows subtract, the raw conditions sum before
     the clamp; --no-health-regen is the old cap-then-add degeneration-only server. The
     rowless reader: a regeneration row with no client record counts 0 and says so ONCE; a
     hex row with none still raises, under both arms (642d8957's behaviour, the review's EV-8).
  2. property 44 goes positive through the real apply path (446 via `opens_episode`, 288 by
     type), and a positive rate ending on a full agent is [32], not [44] 0 -- a body too
     (--no-max-hp-reached the known-bad arm); below the maximum the [44] zero.
  3. degen_tick integrates the gain: capped at the maximum (the player's and a body's), never
     a kill, never on the dead.
  4. the natural ramp: 0 until 5.0 s, +1 per 2.0 s, capped at 7. RESET by a health fall (a
     hit; degeneration tick by tick at the server's own TICK_SECONDS, so a Bleeding's END is
     the anchor -- retail's NEGEND, 16 of 40 binders), by a foe's ACTIVATION at the player
     (the real enemy_attack_tick), by a cast LANDING on it (the real land_skill), by the
     player's own strike (the real hit_enemy -- not an area tick, not an arrow's arrival),
     ranged release (the real launch_player_projectile) and cast completion at a foe (the real
     cast_tick; not at itself). NOT reset by a Deep Wound or a morale RISE. HELD at 0, anchor
     untouched, by a FRIENDLY cast in flight at the player and by nothing hostile. Zero while
     the effects are a loss and running while they are not; [32] when it fills the bar;
     nothing while dead, the death batch's [44] the zero (with an effect and without), and
     the clock restarting at the death; --no-natural-regen.
  5. the source: the flags parse (default off), main()'s blocks flip their bools (lifted by
     AST and run), the reset sites (each naming PLAYER_AGENT_ID, under its guard) and the
     body sites that must not reset.
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
import episodemods                                             # noqa: E402
import vaultpath                                               # noqa: E402

HAVE_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
# Floors from the green runs of 2026-10-07: 38 bare (RURIK_VAULT at an empty directory and at
# a nonexistent path; section 0 a declared skip), 40 with the vault (section 0: 2). The review
# fix the same day (EV-2..EV-8, CD-1..CD-3): 53 bare, and section 0 holds 5 carried rows -- 58
# with the vault. Both from green runs.
FLOOR_BARE = 53
LEDGER = checks.Ledger("health regeneration on the server",
                       floor=FLOOR_BARE + (5 if HAVE_CONTENT else 0))
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
HERO = 20
FOE = 30
TROLL, BREEZE, SUFFER, WINDBORNE, JAVELIN = 446, 288, 108, 160, 230
FAINT = 135
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
    # the casts section 4 drives (test_mechanics' copies of the same record)
    "108": (1.0, 0.75, 10, 15, 0, 0, 7, 4, 4, 16, 0, 0, 0, 240.0, 1, 6, 30, 0, 3, 0, 0, 2077, 2077, False, False),
    "160": (0.75, 0.75, 5, 10, 0, 0, 8, 6, 6, 3, 0, 0, 0, 0.0, 1, 5, 13, 33, 33, 0, 0, 2077, 2077, False, False),
    "230": (1.0, 0.75, 5, 5, 0, 0, 8, 6, 5, 5, 0, 0, 0, 100.0, 2, 0, 0, 15, 50, 1, 10, 405, 404, False, False),
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


@contextlib.contextmanager
def rowless(*ids):
    """WORLD's skills table WITHOUT these ids for the block (a vault machine has them)."""
    tables = agents.WORLD.tables
    had = "skills" in tables
    kept = dict(tables.get("skills", {}))
    tables["skills"] = {k: v for k, v in kept.items() if k not in {str(i) for i in ids}}
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


def rates(sent):
    return [rate_of(v) for op, v in words(sent) if op == OP_FLOAT]


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


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


def body(allegiance, health=100.0, **more):
    row = {"name": "b", "dead": False, "died_at": 0.0, "health": health, "max_health": 100.0,
           "last_hit": 0.0, "armor_rating": 60, "pos": (50.0, 0.0), "allegiance": allegiance,
           "attacks_back": True}
    row.update(more)
    return row


def section_carried():
    print("== 0. the carried rows against the vault's own ==")
    if not HAVE_CONTENT:
        LEDGER.skip(f"0. carried rows vs vault rows ({len(RECORD)} checks)", "no vault/content directory")
        return
    for k, cols in sorted(RECORD.items()):
        row = agents.WORLD.get("skills", k)
        got = tuple(row.get(c) for c in SKILL_COLUMNS)
        check(got == cols and row.provenance.get("build") == RECORD_BUILD,
              f"skills row {k} carried here is the vault's, column for column, build {RECORD_BUILD}",
              f"vault {got} build {row.provenance.get('build')}")


def section_net_pips():
    print("== 1. net_pips: signed, ONE clamp; the rowless reader ==")
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
    # THE ROWLESS READER (the review's EV-8 / CD-3): regen_pips degrades, hex_pips raises.
    st = fresh()
    ep(st, TROLL, type_code=10)
    episodemods._HEX_DEGEN_UNREADABLE.discard((episodemods.REGEN_MEANS, TROLL))
    out = io.StringIO()
    with rowless(TROLL), contextlib.redirect_stdout(out):
        try:
            got = (authsrv.regen_pips(st, PLAYER), authsrv.regen_pips(st, PLAYER))
        except Exception as ex:                                         # noqa: BLE001
            got = type(ex).__name__                 # a raise is this check's FAIL, not a crash
    said = [ln for ln in out.getvalue().splitlines() if f"{TROLL} names a health regeneration" in ln]
    check(got == (0.0, 0.0) and len(said) == 1 and "no client record" in said[0],
          "a `Health regeneration` row whose skill has NO client record counts 0 -- the "
          "degeneration-only server for that skill -- and says so ONCE across two reads",
          f"{got} {said}")
    st = fresh()
    ep(st, FAINT, rank=11, type_code=4)
    raised = {}
    for arm in (True, False):
        with rowless(FAINT), flags(HEALTH_REGEN=arm), contextlib.redirect_stdout(io.StringIO()):
            try:
                authsrv.net_pips(st, PLAYER)
                raised[arm] = None
            except Exception as ex:                                     # noqa: BLE001
                raised[arm] = type(ex).__name__
    check(raised == {True: "ContentError", False: "ContentError"},
          "a `Health degeneration` HEX row (Faintheartedness 135, slot-read) with no client record "
          "still RAISES, with the flag on and under --no-health-regen -- 642d8957's behaviour; the "
          "widened catch is the regeneration reader's alone", f"{raised}")


def section_wire():
    print("== 2. property 44 goes positive; [32] ends it at full ==")
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

    def close_on(st, agent):
        sent, send = collector()
        authsrv.push_regen(send, st, agent, 0)
        sent.clear()
        for x in list(st["effects"].live.values()):
            x["expires_at"] = 0.0
        authsrv.effect_tick(send, st, 0)
        return sent

    st = fresh(100.0)
    ep(st, TROLL, type_code=10)
    w = words(close_on(st, PLAYER))
    check(w == [(OP_INT, [FULL, PLAYER, 0])],
          "446 closing on a FULL player sends 0x009F [32, me, 0] and NO [44] -- retail's regen "
          "closes, 6 of 6 at full; the client's handler zeroes its own rate", f"{w}")
    with flags(MAX_HP_REACHED=False):
        st = fresh(100.0)
        ep(st, TROLL, type_code=10)
        w = words(close_on(st, PLAYER))
        check(w == [(OP_FLOAT, [REGEN, PLAYER, 0])],
              "KNOWN-BAD ARM, --no-max-hp-reached: the same close sends the [44] +0.0", f"{w}")
    st = fresh(100.0)
    st["agents"][FOE] = body(agents.ALLEGIANCE_HOSTILE, 100.0)
    ep(st, TROLL, agent=FOE, type_code=10)
    w = words(close_on(st, FOE))
    check(w == [(OP_INT, [FULL, FOE, 0])],
          "and on a FULL BODY: 446 closing on a hostile at 100 / 100 sends [32, it, 0], no [44] "
          "(agent_at_full reads the body's row; retail's [32]s are 50 hostile of 113)", f"{w}")
    st = fresh(60.0)
    ep(st, TROLL, type_code=10)
    with flags(NATURAL_REGEN=False):
        w = words(close_on(st, PLAYER))
    check(w == [(OP_FLOAT, [REGEN, PLAYER, 0])],
          "BELOW the maximum the close is the [44] +0.0 -- [32] would set the client's bar full "
          "(0x009215F0 with 1.0), so it never goes to a hurt agent", f"{w}")
    st = fresh(100.0)
    ep(st, BLEED, type_code=8)
    check([v for _op, v in words(close_on(st, PLAYER))] == [[REGEN, PLAYER, 0]],
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
    st["agents"][FOE] = body(agents.ALLEGIANCE_HOSTILE, 40.0)
    ep(st, TROLL, agent=FOE, type_code=10)
    st["degen_at"] = time.time() - 2.0
    sent, send = collector()
    authsrv.degen_tick(send, st, 0)
    check(abs(st["agents"][FOE]["health"] - 52.0) < 0.05 and not st["agents"][FOE]["dead"] and not sent,
          "a BODY's regeneration episode heals the body the same way, silently (40 -> 52)")
    st = fresh(100.0)
    st["agents"][FOE] = body(agents.ALLEGIANCE_HOSTILE, 99.0)
    ep(st, TROLL, agent=FOE, type_code=10)
    st["degen_at"] = time.time() - 2.0
    authsrv.degen_tick(send, st, 0)
    check(st["agents"][FOE]["health"] == 100.0,
          "and a BODY's gain stops AT its maximum too (99 + 12 reads 100, not 111)",
          f"{st['agents'][FOE]['health']}")
    st = fresh(100.0)
    st["agents"][FOE] = body(agents.ALLEGIANCE_HOSTILE, -5.0)
    ep(st, TROLL, agent=FOE, type_code=10)
    st["degen_at"] = time.time() - 0.5
    authsrv.degen_tick(send, st, 0)
    check(not st["agents"][FOE]["dead"],
          "a GAIN never kills: a body whose book sits below zero (a Deep Wound's signed shrink) "
          "climbs, it is not sent to kill_agent", f"{st['agents'][FOE]}")


def _ramp(st, ago):
    """The player's ramp row as if its last reset were `ago` seconds back, the book current."""
    st.setdefault("natural_regen", {})[PLAYER] = {
        "anchor": time.time() - ago, "level": 0, "health": float(st["player_health"]),
        "max": authsrv.player_max_health(st)}


def _row(st):
    return st["natural_regen"][PLAYER]


def section_natural():
    print("== 4. the natural ramp ==")
    nop = lambda *a, **k: None                                          # noqa: E731
    got = {}
    for ago in (4.9, 5.05, 7.05, 9.05, 100.0):
        st = fresh(50.0)
        _ramp(st, ago)
        sent, send = collector()
        authsrv.natural_tick(send, st, 0)
        got[ago] = (authsrv.natural_level(st, PLAYER), rates(sent))
    check(got == {4.9: (0, []), 5.05: (1, [0.02]), 7.05: (2, [0.04]), 9.05: (3, [0.06]),
                  100.0: (7, [0.14])},
          "0 before 5.0 s; +1 at 5.0 (the word +1 x 2 / 100), +2 at 7.0, +3 at 9.0; capped at +7 "
          "(retail: P2 19 of 19, P3 45 of 45; the cap OBSERVED on five hostile runs, the player's "
          "by the same law)", f"{got}")
    with flags(NATURAL_DELAY=3.0):
        st = fresh(50.0)
        _ramp(st, 4.0)
        authsrv.natural_tick(nop, st, 0)
        early = authsrv.natural_level(st, PLAYER)
    check(early == 1, "the delay is the constant's (a 3 s delay would step at 4 s -- the arm "
          "test_regenjoin scores red on the corpus)", f"{early}")
    # ---- what resets, and what does not
    st = fresh(50.0)
    _ramp(st, 6.0)
    sent, send = collector()
    authsrv.natural_tick(send, st, 0)
    st["player_health"] -= 10.0                     # a hit between ticks
    sent.clear()
    authsrv.natural_tick(send, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 0 and rates(sent) == [0.0],
          "a hit (health falls between ticks) resets the ramp to 0 and the [44] zero goes "
          "out (below the maximum: retail's resets ride a 0 word)", f"{words(sent)}")
    # CD-2: DEGENERATION at the server's own tick, then its END -- retail's NEGEND anchor.
    st = fresh(60.0)
    _ramp(st, 30.0)
    sent, send = collector()
    authsrv.natural_tick(send, st, 0)
    up = authsrv.natural_level(st, PLAYER)
    ep(st, BLEED, type_code=8)
    authsrv.push_regen(send, st, PLAYER, 0)
    for _k in range(20):                            # 1 s of Bleeding at TICK_SECONDS
        st["degen_at"] = time.time() - authsrv.TICK_SECONDS
        authsrv.degen_tick(send, st, 0)
    sent.clear()
    for x in list(st["effects"].live.values()):
        x["expires_at"] = 0.0
    authsrv.effect_tick(send, st, 0)                # the Bleeding ends
    for _k in range(3):
        st["degen_at"] = time.time() - authsrv.TICK_SECONDS
        authsrv.degen_tick(send, st, 0)
    at_close = (authsrv.natural_level(st, PLAYER), rates(sent))
    end = _row(st)["anchor"]
    sent.clear()
    authsrv.natural_tick(send, st, 0, end + 4.9)
    held = authsrv.natural_level(st, PLAYER)
    authsrv.natural_tick(send, st, 0, end + 5.05)
    check(up == 7 and at_close == (0, [0.0]) and held == 0
          and authsrv.natural_level(st, PLAYER) == 1 and rates(sent) == [0.02]
          and abs(end - time.time()) < 1.0,
          "a Bleeding over a +7 ramp, ticked at the server's own 0.05 s: every tick's spend is a "
          "LOSS, so its END is the anchor -- the close sends only the [44] zero (no ramp comes "
          "back), 0 at 4.9 s after it, +1 at 5.05 (retail's NEGEND, 16 of 40 on-time binders)",
          f"up {up}, at the close {at_close}, held {held}, then {rates(sent)}")
    st = fresh(50.0)
    _ramp(st, 6.0)
    authsrv.natural_tick(nop, st, 0)
    quiet(authsrv.deep_wound_open, nop, st, PLAYER, 0)
    authsrv.natural_tick(nop, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 1,
          "a Deep Wound (maximum and health down together) is NOT a loss -- RECONSTRUCTION for a "
          "hurt player (studies/isle 8.4 saw no fresh ramp on a full one)",
          f"{authsrv.natural_level(st, PLAYER)}")
    st = fresh(42.5)
    st["morale"] = 85
    _ramp(st, 100.0)
    authsrv.natural_tick(nop, st, 0)
    was_max = authsrv.player_max_health(st)
    quiet(authsrv.push_morale, nop, st, 0, 86, "a 75-XP death-penalty tick")
    authsrv.natural_tick(nop, st, 0)
    check(authsrv.player_max_health(st) > was_max and authsrv.natural_level(st, PLAYER) == 7,
          "a MORALE RISE (the maximum up, health unmoved) is NOT a loss: the +7 ramp holds -- the "
          "deficit grows but nothing was lost (the review's EV-4; the client adds the 42 delta "
          "itself)", f"max {was_max} -> {authsrv.player_max_health(st)}, level "
          f"{authsrv.natural_level(st, PLAYER)}")
    # EV-2: a FRIENDLY cast in flight HOLDS the level, its anchor untouched; a hostile's does not
    for allegiance, name in ((agents.ALLEGIANCE_PLAYER, "FRIENDLY"), (agents.ALLEGIANCE_HOSTILE, "HOSTILE")):
        st = fresh(50.0)
        _ramp(st, 100.0)
        sent, send = collector()
        authsrv.natural_tick(send, st, 0)
        anchor = _row(st)["anchor"]
        st["agents"][HERO] = body(allegiance, casting=0, cast_target=PLAYER)
        sent.clear()
        authsrv.natural_tick(send, st, 0)
        in_flight = authsrv.natural_level(st, PLAYER)
        st["agents"][HERO]["casting"] = None        # interrupted
        authsrv.natural_tick(send, st, 0)
        shape = (in_flight, authsrv.natural_level(st, PLAYER), _row(st)["anchor"] == anchor, rates(sent))
        if name == "FRIENDLY":
            check(shape == (0, 7, True, [0.0, 0.14]),
                  "a FRIENDLY body's cast in flight at the player HOLDS the level at 0 (the zero "
                  "rides the activation, 090355 2 of 2) without moving the anchor, so an "
                  "INTERRUPTED one gives the +7 back (:50061's interrupted ally cast kept the "
                  "timer, n=1)", f"{shape}")
        else:
            check(shape == (7, 7, True, []),
                  "a HOSTILE body's cast in flight holds NOTHING: a foe's reset is its activation "
                  "(the event below), so the poll is the friendly hold alone", f"{shape}")
    # EV-2: a FOE's ACTIVATION at the player, through the real enemy_attack_tick
    st = fresh(50.0)
    _ramp(st, 100.0)
    authsrv.natural_tick(nop, st, 0)
    st["agents"][10] = body(agents.ALLEGIANCE_HOSTILE, pos=(80.0, 0.0), skills=[[JAVELIN, 1.0, 5.0]],
                            skill_ready=[0.0], npc={"profession": 6}, cast_range=1200.0,
                            target=PLAYER, target_locked=True)
    sent, send = collector()
    t0 = time.time()
    quiet(authsrv.enemy_attack_tick, send, st, 0)
    anchor = _row(st)["anchor"]
    sent.clear()
    authsrv.natural_tick(send, st, 0)
    shape = (st["agents"][10].get("casting"), st["agents"][10].get("cast_target"),
             abs(anchor - t0) < 0.5, authsrv.natural_level(st, PLAYER), rates(sent))
    authsrv.natural_tick(send, st, 0, anchor + 4.9)
    low = authsrv.natural_level(st, PLAYER)
    authsrv.natural_tick(send, st, 0, anchor + 5.05)
    check(shape == (0, PLAYER, True, 0, [0.0]) and low == 0 and authsrv.natural_level(st, PLAYER) == 1,
          "a HOSTILE's activation at the player (the real enemy_attack_tick, Lightning Javelin) "
          "restarts the ramp FROM THE ACTIVATION: the [44] zero, 0 at 4.9 s, +1 at 5.05 -- landed "
          "or not (20260824T074002 hostile 29, 2 of 2)", f"{shape} then {low}")
    # EV-2: a cast LANDING on the player, through the real land_skill -- and one on a hero
    landed = {}
    for target in (PLAYER, HERO + 1):
        st = fresh(50.0)
        st["agents"][HERO + 1] = body(agents.ALLEGIANCE_PLAYER)
        _ramp(st, 100.0)
        authsrv.natural_tick(nop, st, 0)
        st["agents"][HERO] = body(agents.ALLEGIANCE_PLAYER, skills=[[WINDBORNE, 0.75, 5.0]],
                                  skill_ready=[0.0], casting=0, cast_target=target, cast_lands_at=0.0)
        t0 = time.time()
        quiet(authsrv.land_skill, nop, st, HERO, st["agents"][HERO], 0)
        authsrv.natural_tick(nop, st, 0)
        landed[target] = (abs(_row(st)["anchor"] - t0) < 0.5, authsrv.natural_level(st, PLAYER),
                          [e["skill"] for e in st["effects"].on_agent(target)])
    check(landed == {PLAYER: (True, 0, [WINDBORNE]), HERO + 1: (False, 7, [WINDBORNE])},
          "a FRIENDLY Windborne Speed LANDING on the player (the real land_skill) restarts its "
          "ramp at the landing (retail's four witnesses, each step 5.00 s after the [20]); the "
          "same landing on a HERO leaves the player's +7 alone", f"{landed}")
    # CD-1 / EV-3: the player's own strike, through the real hit_enemy -- and what is NOT one
    moved = {}
    for name, kw in (("strike", {"armed": True}),
                     ("attack skill", {"skill_strike": True}),
                     ("area tick", {"exact": 5.0, "swing": False, "armed": True}),
                     ("arrow", {"armed": True, "projectile": True})):
        st = fresh(50.0)
        st["agents"][FOE] = body(agents.ALLEGIANCE_HOSTILE)
        _ramp(st, 100.0)
        quiet(authsrv.hit_enemy, nop, st, FOE, 0, label=name, **kw)
        moved[name] = time.time() - _row(st)["anchor"] < 1.0
    check(moved == {"strike": True, "attack skill": True, "area tick": False, "arrow": False},
          "the player's own STRIKE resets (a swing, an attack skill: retail's OWN_HIT); an AREA "
          "TICK it caused does not (swing False -- the review's EV-3; retail's caused damage, "
          "DEALT, is no anchor), nor an arrow's ARRIVAL", f"{moved}")
    st = fresh(50.0)
    st["agents"][FOE] = body(agents.ALLEGIANCE_HOSTILE, pos=(500.0, 0.0))
    _ramp(st, 100.0)
    shot = quiet(authsrv.launch_player_projectile, nop, st, 0, {"target": FOE},
                 {"speed": 1250.0, "damage_type": 0, "projectile": 1, "arrow": 0})
    check(shot is not None and time.time() - _row(st)["anchor"] < 1.0
          and _row(st).get("why") == "its own ranged release",
          "the player's ranged RELEASE (the real launch_player_projectile) resets its ramp -- "
          "retail's 0x00A4 (hostile 54: 5.00 s after its launch, 4.40 after its hit)",
          f"{_row(st)}")
    cast = {}
    for sid, target in ((SUFFER, FOE), (BREEZE, PLAYER)):
        st = fresh(50.0)
        st["agents"][FOE] = body(agents.ALLEGIANCE_HOSTILE)
        _ramp(st, 100.0)
        saved = (authsrv.skill_cost, authsrv.weapon_satisfies)
        authsrv.skill_cost = lambda sid: (0, 0)
        authsrv.weapon_satisfies = lambda sid: True
        try:
            quiet(authsrv.handle_skill_press, [0, sid, 0, target], nop, st, 0,
                  authsrv.GAME_CMSG_USE_SKILL)
            pending = list(st.get("pending_casts") or ())
            for c in pending:
                for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                    c[k] -= 30.0
            quiet(authsrv.cast_tick, nop, st, 0)
        finally:
            authsrv.skill_cost, authsrv.weapon_satisfies = saved
        cast[sid] = (len(pending), time.time() - _row(st)["anchor"] < 1.0, _row(st).get("why"))
    check(cast == {SUFFER: (1, True, "its own cast at a foe"), BREEZE: (1, False, None)},
          "the player's cast COMPLETING at a foe (the real cast_tick, Suffering at a hostile) "
          "resets its ramp -- RECONSTRUCTION by analogy with the swing; one at ITSELF (Healing "
          "Breeze) does not (OBSERVED: a self heal never reset a ramp)", f"{cast}")
    # ---- the natural term against the effects
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
    authsrv.natural_tick(nop, st, 0)
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
    # ---- death
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
          "a corpse flagged dead between ticks: the level drops to 0 and the [44] zero goes out "
          "once (not [32]: a corpse is not full)", f"{words(sent)}")
    death = {}
    for name, with_446 in (("446 and the ramp", True), ("the ramp alone", False)):
        st = fresh(50.0)
        if with_446:
            ep(st, TROLL, type_code=10)
        _ramp(st, 9.05)
        sent, send = collector()
        authsrv.natural_tick(send, st, 0)
        authsrv.push_regen(send, st, PLAYER, 0)
        before = rates(sent)[-1]
        sent.clear()
        st["player_health"] = 0.0
        quiet(authsrv.kill_player, send, st, 0, "test")
        death[name] = (before, rates(sent))
    check(death == {"446 and the ramp": (0.12, [0.0]), "the ramp alone": (0.06, [0.0])},
          "a KILL on a positive rate: the death batch itself carries the [44] ZERO and never a "
          "positive rate -- through the strip with 446 live, and with the ramp alone (retail's "
          "20260929T100038 572.167, the death entered on a positive rate, n=1; the review's EV-5)",
          f"{death}")
    st = fresh(50.0)
    _ramp(st, 100.0)
    authsrv.natural_tick(nop, st, 0)
    t0 = time.time()
    st["player_dead"], st["player_health"] = True, 0.0
    for k in range(3):
        authsrv.natural_tick(nop, st, 0, t0 + 0.05 * k)
    st["player_dead"], st["player_health"] = False, 50.0          # resurrected at half
    revived = []
    for dt in (0.15, 4.9, 5.25):
        authsrv.natural_tick(nop, st, 0, t0 + dt)
        revived.append(authsrv.natural_level(st, PLAYER))
    check(revived == [0, 0, 1],
          "the clock restarts at the death: resurrected after a +7 ramp, the player reads 0 on "
          "the first tick and at 4.9 s past its last dead tick, +1 at 5.15 -- RECONSTRUCTION "
          "(no timed ramp after a resurrection on the corpus)", f"{revived}")
    # ---- the flags
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
        authsrv.natural_tick(nop, st, 0)
        check(authsrv.natural_level(st, PLAYER) == 0,
              "--no-health-regen turns the ramp off too (no positive rate can be sent)")
    st = fresh(50.0)
    _ramp(st, 6.0)
    authsrv.natural_reset(st, PLAYER, "test")
    authsrv.natural_reset(st, FOE, "test")
    authsrv.natural_tick(nop, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 0 and FOE not in st["natural_regen"],
          "natural_reset restarts the player's ramp and is a no-op for any other agent "
          "(heroes', henchmen's and hostiles' ramps are measured, not shipped)")
    st = fresh(50.0)
    authsrv.natural_tick(nop, st, 0)
    st["natural_regen"][PLAYER]["anchor"] -= 5.05
    st["degen_at"] = time.time() - 1.0
    sent, send = collector()
    authsrv.degen_tick(send, st, 0)
    check(authsrv.natural_level(st, PLAYER) == 1 and abs(st["player_health"] - 52.0) < 0.1
          and rates(sent) == [0.02],
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

    def resets(fn, name="natural_reset"):
        return [n for n in ast.walk(funcs[fn]) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == name]

    def guard_of(fn):
        """The innermost `if` test whose BODY holds fn's natural_reset call, unparsed."""
        calls = {id(c) for c in resets(fn)}
        best = None
        for n in ast.walk(funcs[fn]):
            if isinstance(n, ast.If) and any(id(c) in calls for s in n.body for c in ast.walk(s)):
                if best is None or n.lineno > best.lineno:
                    best = n
        return ast.unparse(best.test) if best is not None else None

    hooks = ("attack_tick", "hit_enemy", "launch_player_projectile", "cast_tick",
             "enemy_attack_tick", "land_skill")
    sites = {fn: len(resets(fn)) for fn in hooks + ("ally_cast_tick", "launch_body_projectile")}
    named = {fn: [ast.unparse(c.args[1]) for c in resets(fn)] for fn in hooks}
    check(sites == {"attack_tick": 1, "hit_enemy": 1, "launch_player_projectile": 1,
                    "cast_tick": 1, "enemy_attack_tick": 1, "land_skill": 1,
                    "ally_cast_tick": 0, "launch_body_projectile": 0}
          and named == {fn: ["PLAYER_AGENT_ID"] for fn in hooks},
          "six reset sites, one call each, every one naming PLAYER_AGENT_ID (natural_reset "
          "ignores any other agent, so a call naming the target is no reset at all -- the "
          "review's CD-1): the player's swing start, strike, ranged release and cast at a foe; "
          "a foe's activation at the player; a landing on it. A FRIENDLY activation "
          "(ally_cast_tick) and a body's shot never call it", f"{sites} {named}")
    guards = {fn: guard_of(fn) for fn in ("hit_enemy", "enemy_attack_tick", "land_skill")}
    check(guards == {"hit_enemy": "(swing or skill_strike) and (not projectile)",
                     "enemy_attack_tick": "cast_target == PLAYER_AGENT_ID",
                     "land_skill": "agent.get('cast_target') == PLAYER_AGENT_ID and agent_id != PLAYER_AGENT_ID"},
          "the guards: hit_enemy's is a swing or an attack skill and not a projectile (an area "
          "tick, a hex payoff and an arrow's arrival are not strikes); the foe's activation and "
          "the landing are AT the player", f"{guards}")
    ct = guard_of("cast_tick")
    check(ct is not None and ct.endswith("== agents.ALLEGIANCE_HOSTILE") and "!=" not in ct,
          "cast_tick's reset sits under `== agents.ALLEGIANCE_HOSTILE`: a cast at a FOE, never at "
          "itself or an ally (P2(c)'s refuted reading)", f"{ct}")
    check(len(resets("degen_tick", "natural_tick")) == 1
          and len(resets("net_pips", "regen_pips")) == 1 and len(resets("net_pips", "natural_level")) == 1,
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
