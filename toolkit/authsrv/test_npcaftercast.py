r"""test_npcaftercast -- a body's completed cast holds its NEXT action for the table's
aftercast (DESKWORK-D5 "NPC aftercast proper", studies/skills 65, SKILLS-AC; 2026-10-07).

    python toolkit/authsrv/test_npcaftercast.py

WHAT IT IS REALLY CHECKING. authsrv.NPC_AFTERCAST (--no-npc-aftercast): land_skill
stamps `aftercast_until` = the landing + skill_timing's aftercast on a COMPLETED
non-attack, non-instant cast, and enemy_attack_tick / ally_cast_tick / ally_attack_tick
hold the body's next cast or swing until it passes -- an instant skill is let through.
The retail evidence is npcaftercast.py's (P1: 1,477 of 1,477 next starts at or after
0.704 s); the known-bad arm is our own server, which chains two ready spells a tick
apart.

  1  the READER's pure half on literal wire (bare machine): a targeted and an
     un-targeted start, a recycled id, a stopped cast that is not a completion, an
     instant inside the window that is not a start, the P1 / P2 / P3 arithmetic at its
     edges, P6's strict / own-batch split, the E5 -> E3 join.
  2  the SERVER on carried rows (both machines -- the rows are the vault's own,
     section 4 holds them to it): (a) a hostile with two ready 0.75-aftercast spells
     (253 then 289): the second [60] announces at or after the first [58] + 0.75, inside
     two ticks of it; (b) its swing waits too; (c) the KNOWN-BAD arm, --no-npc-aftercast:
     the next start is ONE tick after the [58], and the start ticks equal 642d8957's own
     (the literal below, recorded by driving THIS fixture through a `git archive
     642d8957` export); (d) a hero with two ready spells (281 then 289) waits the same
     -- and its E3 rides its E5 in the same tick, unmoved; (e) the controls: an
     interrupted cast stamps nothing; an instant stance (1037, whose TABLE says 0.75)
     and an attack skill (397, whose table says 1.0) stamp nothing; an aftercast-0
     skill (the preparation 433) gates nothing; an instant goes INSIDE the window, a
     hostile's and a hero's (retail: stance 11 strictly inside, n = 2); an attack
     skill is HELD, a hostile's and a hero's (retail: 17, min 0.735); a party body's
     swing (ally_attack_tick) waits too; a RESSIG [59] stop stamps nothing (a planted
     row, the real one's aftercast being 0); (f) a harness-free replay of (a)'s and
     (c)'s output through npcaftercast: P1 HOLDS on the default arm and FAILS on the
     known-bad one.
  3  source checks: the flag in serverargs and flipped in main(), ON at import, the
     parsed attribute; the hold called from the three ticks and never from pick_skill;
     in the hostile loop after the reach gate and before the pay gate (world gates
     before clock gates, RV-1), and ahead of the plain swing's interval gate; in
     ally_cast_tick ahead of the energy block (a held body is never charged); the
     stamp once, in land_skill.
  4  the vault (skips only on an absent vault DIRECTORY): the carried rows against the
     vault's own, column for column; the reader over the live corpus -- P1, P2, P3 hold,
     P4 (our 20260928T002701 capture fails P1), P5 undecidable, P6 refuted.
"""
import ast
import contextlib
import io
import json
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
import npcaftercast                                            # noqa: E402
import vaultpath                                               # noqa: E402

# Floors from the green runs of 2026-10-07, decided on the vault's DIRECTORIES and never
# on what loaded (test_agentlife's rule): FLOOR_BARE = 42, MEASURED with RURIK_VAULT at an
# empty directory AND at a nonexistent path (sections 1-3; section 4 declares its two
# skips); + 1 with vault/content (the carried rows against the vault's own); + 8 with
# vault/captures/live (the reader over the corpus, --json's stdout among them); + 1 with
# OUR capture for P4 = 52, MEASURED with the vault. (38 / 47 until the review pass the
# same day added P6's split, the hero's instant, the attack-skill hold, the party hold's
# place ahead of the debit and --json's one-document stdout.)
OURS_P4 = os.path.join(vaultpath.vault_path("captures"), "gamesrv",
                       "authsrv-20260928T002701-c1.jsonl")
HAVE_VAULT_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
HAVE_LIVE = os.path.isdir(vaultpath.vault_path("captures", "live"))
FLOOR_BARE = 42
LEDGER = checks.Ledger("NPC aftercast",
                       floor=FLOOR_BARE + (1 if HAVE_VAULT_CONTENT else 0)
                       + ((8 + (1 if os.path.isfile(OURS_P4) else 0)) if HAVE_LIVE else 0))
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
E3, E5 = 0x00E3, 0x00E5
HOSTILE, HERO, FOE, DOWNED = 10, 200, 20, 30
SCOURGE, VITAL, ORISON = 253, 289, 281          # spells, table aftercast 0.75
KINDLE = 433                                    # a preparation, table aftercast 0
DARK_ESCAPE = 1037                              # a STANCE whose table says 0.75 (castmech 9)
SAVAGE = 397                                    # a bow ATTACK whose table says 1.0 (castmech 9)
FLAIL = 10                                      # a stance, table 0
TICK = 0.05
T0 = 1_000_000.0
AFTERCAST = 0.75

# THE CARRIED ROWS. Copied from the vault's LOADED skills rows (skilltable.py, build
# 38974) -- measured numbers, CLAUDE.md's gate. They REPLACE the skills table for the
# driven sections (`carried`), so a vault run takes the bare path and cannot pass on a
# row a bare machine lacks; section 4 holds them to the vault's own, column for column.
RECORD_BUILD = 38974
SKILL_COLUMNS = ("activation", "aftercast", "recharge", "energy", "adrenaline",
                 "adrenaline_units", "attribute", "profession", "type_code", "target",
                 "combo", "combo_req", "weapon_req", "aoe_range", "skill_arguments",
                 "duration0", "duration15", "scale0", "scale15", "bonus_scale0",
                 "bonus_scale15", "projectile", "impact_visual", "touch_range",
                 "half_range")
RECORD = {
    "2": (3.0, 0.0, 0, 0, 0, 0, 51, 0, 7, 6, 0, 0, 0, 0.0, 6, 0, 0, 100, 100, 25, 25, 2077, 2077, False, False),
    "253": (1.0, 0.75, 5, 5, 0, 0, 14, 3, 4, 5, 0, 0, 0, 156.0, 1, 8, 20, 100, 100, 0, 0, 2077, 463, False, False),
    "289": (0.75, 0.75, 2, 10, 0, 0, 15, 3, 6, 3, 0, 0, 0, 0.0, 2, 131072, 131072, 40, 200, 0, 0, 2077, 2077, False, False),
    "281": (1.0, 0.75, 2, 5, 0, 0, 13, 3, 5, 3, 0, 0, 0, 0.0, 2, 0, 0, 30, 80, 0, 0, 2077, 2077, False, False),
    "433": (2.0, 0.0, 12, 5, 0, 0, 24, 2, 19, 0, 0, 0, 0, 0.0, 2, 24, 24, 3, 24, 0, 0, 343, 344, False, False),
    "1037": (0.0, 0.75, 30, 5, 0, 0, 31, 7, 3, 0, 0, 0, 0, 0.0, 1, 5, 15, 25, 25, 50, 50, 2077, 2077, False, False),
    "397": (0.5, 1.0, 1, 5, 0, 0, 51, 2, 14, 5, 0, 0, 2, 0.0, 0, 0, 0, 0, 0, 0, 0, 680, 2077, False, False),
    "10": (0.0, 0.0, 15, 5, 0, 0, 2, 5, 3, 0, 0, 0, 0, 0.0, 3, 5, 80, 10, 46, 0, 0, 2077, 22, False, False),
}
# (tick index, kind, skill) of every START the fixtures' hostile and hero make under
# --no-npc-aftercast, recorded 2026-10-07 by driving `_hostile_fight` / `_hero_fight`
# through a `git archive 642d8957 toolkit content schema` export on the carried rows
# (scratch impl-desk-aftercast/record_642.py): the arm must be THAT server's cadence,
# not merely "fast". (The same run found the two fixtures' 63 sends byte-identical to
# the export's, sha256 daf7a421...; only the starts are pinned here, so a sibling
# change to what a landing SENDS does not red a test about WHEN the next one starts.)
START_642 = [(0, "S60", 253), (21, "S60", 289), (48, "S4", 0), (75, "S4", 0),
             (88, "S60", 289), (115, "S4", 0), (142, "S4", 0), (155, "S60", 289),
             (182, "S4", 0), (209, "S4", 0), (222, "S60", 289)]
HERO_642 = [(0, "S60", 281), (21, "S60", 289), (60, "S60", 281), (81, "S60", 289)]


def _carried_skill(key):
    return content.Row(
        dict(zip(SKILL_COLUMNS, RECORD[key])), "skills", key,
        {"source": "client-table", "extractor": "toolkit/clientscan/skilltable.py",
         "build": RECORD_BUILD})


@contextlib.contextmanager
def carried(A=authsrv):
    """WORLD's skills table REPLACED by exactly RECORD for the block, then put back."""
    tables = agents.WORLD.tables
    kept = tables.get("skills")
    tables["skills"] = {k: _carried_skill(k) for k in RECORD}
    try:
        yield
    finally:
        if kept is not None:
            tables["skills"] = kept
        else:
            tables.pop("skills", None)


class Clock:
    def __init__(self, t):
        self.t = t

    def time(self):
        return self.t

    def __getattr__(self, name):
        import time as _real
        return getattr(_real, name)


FLAGS = ("NPC_AFTERCAST", "ENERGY", "NPC_FOLLOW", "SKIP_LIVE_EFFECT", "INSTANT_ANNOUNCE")


@contextlib.contextmanager
def arm(A=authsrv, aftercast=True, **flags):
    """A fake clock and the named flags for the block, then restore. ENERGY off and
    NPC_FOLLOW off, as test_castgate's fixture: the subject is the cadence, not the pool
    or the chase. NPC_AFTERCAST is set only where the module has it (642d8957 had not)."""
    saved = {k: getattr(A, k) for k in FLAGS if hasattr(A, k)}
    saved_time = A.time
    base = {"ENERGY": False, "NPC_FOLLOW": False}
    if hasattr(A, "NPC_AFTERCAST"):
        base["NPC_AFTERCAST"] = aftercast
    base.update(flags)
    for k, v in base.items():
        setattr(A, k, v)
    A.time = Clock(T0)
    try:
        yield A.time
    finally:
        for k, v in saved.items():
            setattr(A, k, v)
        A.time = saved_time


def body(A, bar, allegiance, pos=(85.0, 0.0), health=100.0, attack_speed=None, **over):
    row = {"name": "caster", "dead": False, "died_at": 0.0, "health": health,
           "max_health": 100.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": allegiance,
           "attack_speed": attack_speed if attack_speed is not None else A.ENEMY_ATTACK_SPEED,
           "effects": 0, "attacks_back": allegiance == agents.ALLEGIANCE_HOSTILE,
           "skills": tuple(tuple(s) for s in bar), "skill_ready": [0.0] * len(bar)}
    row.update(over)
    return row


def world(A, player_health=1e9):
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": player_health,
          "player_dead": False}
    A.effect_table(st)
    return st


def fight(A, st, secs, ticks=("effect_tick", "enemy_attack_tick", "ally_cast_tick"),
          keep_health=1e9):
    """Drive the real ticks on the fake clock, the player's health reset to
    `keep_health` every tick (None: left alone). Returns [(tick, t, op, vals)], the log."""
    sends = []
    n = [0]

    def send(op, vals, label="", quiet=False):
        sends.append((n[0], A.time.t, op, list(vals)))

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for i in range(int(round(secs / TICK))):
            n[0] = i
            if keep_health is not None:
                st["player_health"] = keep_health
            for name in ticks:
                getattr(A, name)(send, st, 0)
            A.time.t += TICK
    return sends, out.getvalue()


def starts(sends, who):
    """[(tick, kind, skill)] of every START by `who`: [60] / [50] on either channel, a
    swing [4], and an instant's [48] (a start for the cadence's purpose here)."""
    out = []
    for i, _t, op, v in sends:
        if op == INT_T and len(v) >= 4 and v[0] in (60, 50, 4) and v[1] == who:
            out.append((i, "S%d" % v[0], v[3] if v[0] != 4 else 0))
        elif op == INT and len(v) >= 3 and v[0] in (60, 50, 48) and v[1] == who:
            out.append((i, ("I48" if v[0] == 48 else "S%d" % v[0]), v[2]))
    return out


def completions(sends, who):
    return [i for i, _t, op, v in sends if op == INT and v[:2] == [58, who]]


def as_seq(sends):
    """The fixture's sends in the reader's shape: [(index, t, op, [op] + vals)]."""
    return [(k, t, op, [op] + list(v)) for k, (_i, t, op, v) in enumerate(sends)]


def table_of(ids=RECORD):
    return {int(k): (RECORD[k][0], RECORD[k][1], RECORD[k][2], RECORD[k][8]) for k in ids}


def _hostile_fight(A, aftercast, secs=12.0, bar=((SCOURGE, 1.0, 5.0), (VITAL, 0.75, 2.0))):
    with arm(A, aftercast=aftercast):
        st = world(A)
        st["agents"][HOSTILE] = body(A, bar, agents.ALLEGIANCE_HOSTILE)
        sends, log = fight(A, st, secs)
    return sends, log, st


def _hero_fight(A, aftercast, secs=6.0):
    with arm(A, aftercast=aftercast):
        st = world(A, player_health=40.0)
        st["agents"][HERO] = body(A, ((ORISON, 1.0, 2.0), (VITAL, 0.75, 2.0)),
                                  agents.ALLEGIANCE_PLAYER, pos=(50.0, 0.0), hero=3,
                                  attacks_back=False, party_slot=0,
                                  npc={"profession": 3, "level": 5})
        # the player held HURT, so both of the hero's ally spells always have a target
        sends, log = fight(A, st, secs, keep_health=40.0)
    return sends, log, st


def gaps_after(sends, who):
    """[(58 tick, next start tick, kind)] -- each completion to the body's next start."""
    st = starts(sends, who)
    out = []
    for c in completions(sends, who):
        nxt = next(((i, k) for i, k, _s in st if i > c or (i == c and False)), None)
        if nxt is not None:
            out.append((c, nxt[0], nxt[1]))
    return out


# ---------------------------------------------------------------------------------
def section_reader():
    print("== 1. the reader's pure half, on literal wire ==")
    A, A9 = npcaftercast.OP_INT_TARGET, npcaftercast.OP_INT
    seq = [
        (0, 0.0, A, [A, 60, 7, 1, 253]),        # targeted start, 253
        (1, 1.0, A9, [A9, 58, 7, 0]),           # its completion
        (2, 1.75, A9, [A9, 60, 7, 289]),        # UN-targeted start 0.75 later
        (3, 2.5, A9, [A9, 58, 7, 0]),
        (4, 2.6, A9, [A9, 48, 7, 10]),          # an instant inside the window: not a start
        (5, 3.4, A, [A, 4, 7, 1, 0]),           # a swing 0.90 after the 58
        (6, 4.0, A, [A, 60, 7, 1, 433]),        # aftercast-0 skill
        (7, 6.0, A9, [A9, 58, 7, 0]),
        (8, 6.1, A, [A, 60, 7, 1, 253]),        # 0.10 after an aftercast-0 completion
        (9, 6.5, A9, [A9, 59, 7, 0]),           # STOPPED: no completion
        (10, 6.6, A, [A, 60, 7, 1, 289]),
        (11, 7.35, A9, [A9, 58, 7, 0]),
        (12, 7.40, 0x0020, [0x0020, 7]),        # id 7 RE-CREATED: a new body
        (13, 7.45, A, [A, 60, 7, 1, 253]),      # must not pair with the old body's 58
        (14, 7.5, A, [A, 60, 1, 7, 253]),       # the observer: never read
        (15, 10.0, A, [A, 60, 8, 1, 253]),      # agent 8: a cast STOPPED ...
        (16, 10.2, A9, [A9, 59, 8, 0]),
        (17, 10.5, A9, [A9, 58, 8, 0]),         # ... then an ORPHAN 58 with no start of
        (18, 10.6, A, [A, 60, 8, 1, 289]),      # its own: not 253's (the survey's walk)
    ]
    acts = npcaftercast.actions_of(seq, 1)
    check(set(acts) == {(7, 0), (7, 1), (8, 0)} and all(a != 1 for a, _i in acts),
          "actions are keyed per INCARNATION (the 0x0020 splits id 7) and the observer is "
          "never read", f"{sorted(acts)}")
    rows = npcaftercast.completion_rows(acts)
    got = [(r["skill"], r["gap"], r["next"], r["instant_gap"]) for r in rows]
    check(got == [(253, 0.75, "S60", None), (289, 0.9, "S4", 0.1), (433, 0.1, "S60", None)],
          "completion rows: 253 -> the UN-targeted 289 at 0.75; 289 -> the swing at 0.90 "
          "with the instant at 0.10 recorded beside it (not a start); 433 -> 253 at 0.10; "
          "the stopped 289, the re-created body's start and agent 8's ORPHAN 58 behind a "
          "[59] pair with nothing (the walk back stops at a close)",
          f"{got}")
    tab = {253: (1.0, 0.75, 5.0, 4), 289: (0.75, 0.75, 2.0, 6), 433: (2.0, 0.0, 12.0, 19)}
    sc = npcaftercast.score(rows, tab)
    check(sc["n"] == 2 and sc["min"] == 0.75 and sc["p1"] and sc["mass"] == 1
          and sc["control_n"] == 1 and sc["control_under"] == 1 and sc["p3"],
          "score: P1 over the two 0.75 rows (min 0.75), P2's mass counts [0.70, 0.80), "
          "P3's control is the 433 row under 0.70", f"{sc}")
    check(sc["instants"] == (1, 0.1) and sc["by_next"] == {"cast": (1, 0.75), "swing": (1, 0.9)},
          "the instant inside the window is read separately, the next starts split by kind",
          f"{sc['instants']} {sc['by_next']}")
    edge = [dict(r, gap=g) for r, g in zip(rows[:2], (0.70, 0.699))]
    check(npcaftercast.score(edge[:1], tab)["p1"]
          and not npcaftercast.score(edge, tab)["p1"],
          "P1's edge: a gap of exactly 0.70 holds, 0.699 fails")
    check(npcaftercast.p6_split([0.501, 0.0, 0.9, 0.499, 0.70]) == ([0.499, 0.501], 1),
          "P6's split: an instant STRICTLY inside (0, 0.70) scores, one in the [58]'s own "
          "batch (0.000) is counted apart, 0.70 and past it are outside",
          f"{npcaftercast.p6_split([0.501, 0.0, 0.9, 0.499, 0.70])}")
    check(not npcaftercast.score(rows[:2], tab)["p3"]
          and not npcaftercast.score([dict(rows[0], gap=0.85)] * 4, tab)["p2"]
          and npcaftercast.score([dict(rows[0], gap=0.79)] + [dict(rows[0], gap=0.85)] * 2,
                                 tab)["p2"],
          "P3 needs a control row; P2 fails with no gap inside [0.70, 0.80) and holds at "
          "one in three")
    e3 = npcaftercast.hero_e3([
        (0, 1.0, E5, [E5, 30, 281, 0, 2]), (1, 1.0, E3, [E3, 30, 281, 0]),
        (2, 2.0, E5, [E5, 30, 289, 0, 2]), (3, 2.75, E3, [E3, 30, 289, 0]),
        (4, 3.0, E5, [E5, 1, 281, 0, 2]), (5, 3.75, E3, [E3, 1, 281, 0])], 1)
    check(e3 == [(30, 281, 0.0), (30, 289, 0.75)],
          "the E5 -> E3 join pairs per (agent, skill), never the observer's",
          f"{e3}")
    n, z, _by, _all = npcaftercast.score_e3(e3, {281: (1.0, 0.75, 2.0, 5),
                                                 289: (0.75, 0.75, 2.0, 6)})
    n0, _z0, _b0, _a0 = npcaftercast.score_e3(e3, {281: (0.0, 0.0, 3.0, 14),
                                                   289: (0.0, 0.0, 4.0, 3)})
    check((n, z, n0) == (2, 1, 0),
          "P5 scores only spell rows with a table aftercast: an attack and a stance (the "
          "survey's 322 / 346 shape) score NOTHING", f"{(n, z, n0)}")


# ---------------------------------------------------------------------------------
def section_server():
    print("== 2. the server, on carried rows ==")
    with carried():
        on, log_on, st_on = _hostile_fight(authsrv, True)
        off, _log_off, _st_off = _hostile_fight(authsrv, False)
        h_on, _hl, hst = _hero_fight(authsrv, True)
        h_off, _hl0, _hst0 = _hero_fight(authsrv, False)

    # (a) the hostile's chain 253 -> 289
    s_on = starts(on, HOSTILE)
    c_on = completions(on, HOSTILE)
    first = (c_on[0], next(((i, k, s) for i, k, s in s_on if i > c_on[0]), None)) if c_on else None
    ac_ticks = int(round(AFTERCAST / TICK))
    check(s_on[:1] == [(0, "S60", SCOURGE)] and first is not None
          and first[1][1:] == ("S60", VITAL)
          and ac_ticks <= first[1][0] - first[0] <= ac_ticks + 2,
          "(a) a hostile with 253 and 289 ready: 253's [58], then 289's [60] at or after "
          "the 58 + 0.75 s and inside two ticks of it",
          f"58 at tick {first and first[0]}, next {first and first[1]} "
          f"(0.75 s = {ac_ticks} ticks)")
    gaps = gaps_after(on, HOSTILE)
    check(len(gaps) >= 3 and all(n - c >= ac_ticks for c, n, _k in gaps),
          "    and EVERY completion's next start waits it out -- casts and swings alike",
          f"(58 tick, next tick, kind) {gaps}")
    # (b) the swing waits: 289 lands with nothing ready; the axe's interval from the
    # cast's start would open the swing BEFORE the aftercast ends
    sw = [(c, n) for c, n, k in gaps if k == "S4"]
    sw_off = [(c, n) for c, n, k in gaps_after(off, HOSTILE) if k == "S4"]
    check(sw and all(n - c >= ac_ticks for c, n in sw)
          and sw_off and any(n - c < ac_ticks for c, n in sw_off),
          "(b) its SWING waits too: every swing after a 58 starts at or after +0.75 s "
          "(retail: 352 swings, min 0.704); the known-bad arm swings inside it",
          f"on {sw} off {sw_off}")
    # (c) the known-bad arm
    g_off = gaps_after(off, HOSTILE)
    check(g_off and g_off[0][1] - g_off[0][0] == 1 and g_off[0][2] == "S60",
          "(c) KNOWN-BAD, --no-npc-aftercast: 289's [60] rides the tick after 253's "
          "[58] -- the 0.025 s chain of capture authsrv-20260928T002701-c1",
          f"{g_off[:3]}")
    check(starts(off, HOSTILE) == START_642,
          "    and every start tick equals 642d8957's own, recorded through this fixture "
          "(the revert is that server's cadence, not merely a fast one)",
          f"{starts(off, HOSTILE)}")
    check("aftercast_until" in st_on["agents"][HOSTILE]
          and "aftercast_until" not in _st_off["agents"][HOSTILE],
          "    the stamp is on the row under the default and absent under the flag")
    # (d) the hero
    hs = starts(h_on, HERO)
    hc = completions(h_on, HERO)
    hg = gaps_after(h_on, HERO)
    hg_off = gaps_after(h_off, HERO)
    check(hs[:1] == [(0, "S60", ORISON)] and hg and hg[0][2] == "S60"
          and ac_ticks <= hg[0][1] - hg[0][0] <= ac_ticks + 2
          and all(n - c >= ac_ticks for c, n, _k in hg),
          "(d) a HERO with 281 and 289 ready (ally_cast_tick): the second [60] waits the "
          "aftercast too (RECONSTRUCTION: no hero completes an aftercast > 0 spell on tape)",
          f"starts {hs[:4]} completions {hc[:3]} gaps {hg}")
    check(hg_off and hg_off[0][1] - hg_off[0][0] == 1 and starts(h_off, HERO) == HERO_642,
          "    its known-bad arm chains them a tick apart, every start tick 642d8957's own",
          f"{hg_off[:2]} {starts(h_off, HERO)}")
    e5 = [(i, v[1]) for i, _t, op, v in h_on if op == E5 and v[0] == HERO]
    e3 = [(i, v[1]) for i, _t, op, v in h_on if op == E3 and v[0] == HERO]
    seq = [(op, v[:2]) for _i, _t, op, v in h_on if op in (E5, E3) and v[0] == HERO]
    check(e5 and e3 == e5 and all(seq[k][0] == E5 and seq[k + 1][0] == E3
                                  for k in range(0, len(seq), 2)),
          "    and its E3 rides its E5, the SAME tick, directly behind it -- the gate holds "
          "the next action, never the E3 (hero_skill_messages unmoved)",
          f"E5 {e5} E3 {e3}")
    section_controls()
    # (f) the replay through the reader
    tab = table_of()
    sc_on = npcaftercast.score(npcaftercast.completion_rows(
        npcaftercast.actions_of(as_seq(on + h_on), P)), tab)
    sc_off = npcaftercast.score(npcaftercast.completion_rows(
        npcaftercast.actions_of(as_seq(off + h_off), P)), tab)
    check(sc_on["n"] >= 4 and sc_on["p1"] and sc_off["n"] >= 4 and not sc_off["p1"],
          "(f) the fixtures' own wire through npcaftercast: P1 HOLDS on the default arm "
          "and FAILS on --no-npc-aftercast",
          f"on n={sc_on['n']} min={sc_on['min']}; off n={sc_off['n']} min={sc_off['min']}")
    return on


def section_controls():
    print("== 2. (e) the controls ==")
    with carried():
        # an interrupted cast stamps nothing: 253 mid-cast, interrupted, 289 next tick
        with arm(authsrv) as clock:
            st = world(authsrv)
            ag = body(authsrv, ((SCOURGE, 1.0, 5.0), (VITAL, 0.75, 2.0)),
                      agents.ALLEGIANCE_HOSTILE)
            st["agents"][HOSTILE] = ag
            sends, _log = fight(authsrv, st, 3 * TICK)
            mid = ag.get("casting") == 0 and ag.get("cast_lands_at") is not None
            with contextlib.redirect_stdout(io.StringIO()):
                how = authsrv.interrupt_body(lambda *a, **k: None, st, HOSTILE, ag, 0,
                                             0, P, mode="action")
            stamped = "aftercast_until" in ag
            more, _l2 = fight(authsrv, st, 2 * TICK)
        nxt = starts(more, HOSTILE)
        check(mid and how == "cast" and not stamped and nxt[:1] == [(0, "S60", VITAL)],
              "an INTERRUPTED cast stamps nothing: the next ready spell starts on the very "
              "next tick (RECONSTRUCTION: a [59] is no completion)",
              f"mid {mid} how {how} stamped {stamped} next {nxt[:2]}")
        # instants and attack skills stamp nothing, whatever the table's column says
        with arm(authsrv):
            vals = {sid: authsrv.npc_aftercast(sid)
                    for sid in (SCOURGE, VITAL, ORISON, KINDLE, DARK_ESCAPE, SAVAGE, FLAIL)}
        check(vals == {SCOURGE: 0.75, VITAL: 0.75, ORISON: 0.75, KINDLE: 0.0,
                       DARK_ESCAPE: 0.0, SAVAGE: 0.0, FLAIL: 0.0},
              "npc_aftercast: the three spells 0.75; the preparation 0 (its table); the "
              "stance 1037 (table 0.75) and the bow attack 397 (table 1.0) 0 -- the wiki's "
              "two classes, the table's rows CONTESTED (castmech 9)", f"{vals}")
        with arm(authsrv, aftercast=False):
            vals_off = {sid: authsrv.npc_aftercast(sid) for sid in (SCOURGE, VITAL)}
        check(vals_off == {SCOURGE: 0.0, VITAL: 0.0},
              "  and 0 for every skill under --no-npc-aftercast", f"{vals_off}")
        # a driven attack skill and a driven instant stamp nothing
        for sid, why in ((SAVAGE, "the bow attack 397"), (DARK_ESCAPE, "the stance 1037")):
            with arm(authsrv):
                st = world(authsrv)
                ag = body(authsrv, ((sid, RECORD[str(sid)][0], RECORD[str(sid)][2]),),
                          agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
                st["agents"][HOSTILE] = ag
                sends, _log = fight(authsrv, st, 1.0)
            landed = any(v[:2] in ([46, HOSTILE], [48, HOSTILE]) for _i, _t, op, v in sends
                         if op == INT)
            check(landed and "aftercast_until" not in ag,
                  f"{why}, cast and landed through the real tick, stamps nothing",
                  f"landed {landed} row keys {sorted(k for k in ag if 'after' in k)}")
        # an aftercast-0 spell gates nothing: 433 lands, 253 the next tick
        with arm(authsrv):
            st = world(authsrv)
            st["agents"][HOSTILE] = body(authsrv, ((KINDLE, 2.0, 12.0), (SCOURGE, 1.0, 5.0)),
                                         agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
            sends, _log = fight(authsrv, st, 3.0)
        g = gaps_after(sends, HOSTILE)
        check(g and g[0][2] == "S60" and g[0][1] - g[0][0] == 1,
              "an AFTERCAST-0 skill (the preparation 433) gates nothing: 253 starts the "
              "tick after its [58] (retail's control: 49 of 95 under 0.70 s, every one a "
              "signet or a preparation)", f"{g[:2]}")
        # an instant goes INSIDE the window: 253 lands, the stance 1037 next tick
        with arm(authsrv):
            st = world(authsrv)
            ag = body(authsrv, ((SCOURGE, 1.0, 5.0), (DARK_ESCAPE, 0.0, 30.0)),
                      agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
            st["agents"][HOSTILE] = ag
            sends, _log = fight(authsrv, st, 3.0)
            until = ag.get("aftercast_until")
        s = starts(sends, HOSTILE)
        c = completions(sends, HOSTILE)
        inst = [i for i, k, sid in s if k == "I48" and sid == DARK_ESCAPE]
        check(c and inst and c[0] < inst[0] < c[0] + int(round(AFTERCAST / TICK))
              and until is not None and abs(until - (T0 + c[0] * TICK + AFTERCAST)) < 1e-6,
              "an INSTANT is not held: the stance's [48] lands INSIDE 253's window (retail: "
              "stance 11 strictly inside, n = 2) and leaves 253's stamp where it was",
              f"58 at {c[:1]}, [48] at {inst[:1]}, until-T0 {until and round(until - T0, 3)}")
        # ... and through the PARTY's call site (ally_cast_tick passes the picked slot):
        # a hurt hero's 281 lands, then its stance 1037 goes inside the window. Added
        # after review (CD-2): the hostile check above proves the shared predicate, but
        # a party call site that held an instant (a whole-body stop) stayed green.
        # RECONSTRUCTION: party bodies take the hostile's rule.
        with arm(authsrv):
            st = world(authsrv, player_health=40.0)
            ag = body(authsrv, ((ORISON, 1.0, 2.0), (DARK_ESCAPE, 0.0, 30.0)),
                      agents.ALLEGIANCE_PLAYER, pos=(50.0, 0.0), hero=3, health=40.0,
                      attacks_back=False, party_slot=0, npc={"profession": 3, "level": 5})
            st["agents"][HERO] = ag
            sends, _log = fight(authsrv, st, 3.0, keep_health=40.0)
            until = ag.get("aftercast_until")
        c = completions(sends, HERO)
        inst = [i for i, k, sid in starts(sends, HERO) if k == "I48" and sid == DARK_ESCAPE]
        check(c and inst and c[0] < inst[0] < c[0] + int(round(AFTERCAST / TICK))
              and until is not None and abs(until - (T0 + c[0] * TICK + AFTERCAST)) < 1e-6,
              "  and a HERO's instant too (ally_cast_tick): its stance's [48] lands inside "
              "its 281's window, the stamp unmoved (RECONSTRUCTION, the hostile's rule)",
              f"58 at {c[:1]}, [48] at {inst[:1]}, until-T0 {until and round(until - T0, 3)}")
        # an ATTACK SKILL IS held -- the OBSERVED arm (P1's 17 attack-skill next starts,
        # min 0.735): 253 lands, the bow attack 397 is ready, the swing clock never binds
        # (attack_speed 0.2). Added after review (CD-1): letting attack skills through
        # the window, as instants are, left every test green. Hostile and party sites.
        ac_ticks = int(round(AFTERCAST / TICK))
        atk = {}
        real_pft = authsrv.party_fight_target
        authsrv.party_fight_target = lambda state, aid, agent, now: FOE
        try:
            for ac in (True, False):
                with arm(authsrv, aftercast=ac):
                    st = world(authsrv)
                    st["agents"][HOSTILE] = body(
                        authsrv, ((SCOURGE, 1.0, 5.0), (SAVAGE, 0.5, 1.0)),
                        agents.ALLEGIANCE_HOSTILE, attack_speed=0.2)
                    sends, _log = fight(authsrv, st, 3.0)
                c = completions(sends, HOSTILE)
                s50 = [i for i, k, sid in starts(sends, HOSTILE) if k == "S50" and sid == SAVAGE]
                with arm(authsrv, aftercast=ac):
                    st = world(authsrv, player_health=40.0)
                    st["agents"][FOE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE,
                                             pos=(60.0, 0.0), attacks_back=False)
                    st["agents"][HERO] = body(
                        authsrv, ((ORISON, 1.0, 2.0), (SAVAGE, 0.5, 1.0)),
                        agents.ALLEGIANCE_PLAYER, pos=(50.0, 0.0), hero=3, attack_speed=0.2,
                        attacks_back=False, party_slot=0, npc={"profession": 2, "level": 5})
                    sends, _log = fight(authsrv, st, 3.0, keep_health=40.0,
                                        ticks=("effect_tick", "ally_cast_tick"))
                hc = completions(sends, HERO)
                h50 = [i for i, k, sid in starts(sends, HERO) if k == "S50" and sid == SAVAGE]
                atk[ac] = ((c[:1], s50[:1]), (hc[:1], h50[:1]))
        finally:
            authsrv.party_fight_target = real_pft

        def _gap(pair):
            (cc, ss) = pair
            return ss[0] - cc[0] if cc and ss else None
        on_g = [_gap(p) for p in atk[True]]
        off_g = [_gap(p) for p in atk[False]]
        check(all(g is not None and ac_ticks <= g <= ac_ticks + 2 for g in on_g)
              and off_g == [1, 1],
              "an ATTACK SKILL waits the aftercast (retail: 17 attack-skill starts, min "
              "0.735): the bow attack 397's [50] opens at the 253 / 281 [58] + 0.75 s, inside "
              "two ticks, for a hostile AND a hero; --no-npc-aftercast opens it the tick after",
              f"default (hostile, hero) gaps {on_g}, off {off_g} (0.75 s = {ac_ticks} ticks); "
              f"{atk}")
        # the PARTY's swing (ally_attack_tick) waits its aftercast too. The fight target
        # is STUBBED -- this is about when the swing opens, not whom it picks
        # (party_fight_target's rule is SLICE-H4's and has its own tests).
        gaps = {}
        real_pft = authsrv.party_fight_target
        authsrv.party_fight_target = lambda state, aid, agent, now: FOE
        try:
            for ac in (True, False):
                with arm(authsrv, aftercast=ac):
                    st = world(authsrv)
                    st["agents"][FOE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE,
                                             pos=(60.0, 0.0), attacks_back=False)
                    st["agents"][HERO] = body(authsrv, ((ORISON, 1.0, 2.0),),
                                              agents.ALLEGIANCE_PLAYER, pos=(50.0, 0.0),
                                              hero=3, attacks_back=False, party_slot=0,
                                              npc={"profession": 1, "level": 5})
                    sends, _log = fight(authsrv, st, 2.5, keep_health=40.0,
                                        ticks=("effect_tick", "ally_cast_tick",
                                               "ally_attack_tick"))
                c = completions(sends, HERO)
                sw = [i for i, k, _s in starts(sends, HERO) if k == "S4"]
                gaps[ac] = (c[:1], sw[:1])
        finally:
            authsrv.party_fight_target = real_pft
        (c_on, s_on), (c_off, s_off) = gaps[True], gaps[False]
        check(c_on and s_on and s_on[0] - c_on[0] >= int(round(AFTERCAST / TICK))
              and c_off and s_off and s_off[0] == c_off[0],
              "a party body's SWING waits its spell's aftercast (ally_attack_tick); the "
              "known-bad arm swings in the [58]'s own tick -- our capture "
              "authsrv-20261001T100807-c1 (heroes 200 / 201: 90 of 90 under 0.70 s, 44 in "
              "the [58]'s own batch, max 0.562)",
              f"default 58 {c_on} swing {s_on}; off 58 {c_off} swing {s_off}")
        # a RESSIG stop ([59]: the raise's target already stands) is no completion. Skill
        # 2's real aftercast is 0, so the take-back is unobservable on every real row; a
        # PLANTED row 2 with 0.75 makes it so (a fixture, never compared to the vault).
        planted = dict(zip(SKILL_COLUMNS, RECORD["2"]), aftercast=0.75)
        stamped = {}
        for target_dead in (False, True):
            agents.WORLD.tables["skills"]["2"] = content.Row(
                dict(planted), "skills", "2",
                {"source": "client-table", "extractor": "toolkit/clientscan/skilltable.py",
                 "build": RECORD_BUILD})
            try:
                with arm(authsrv):
                    st = world(authsrv)
                    st["agents"][DOWNED] = body(authsrv, (), agents.ALLEGIANCE_PLAYER,
                                                pos=(0.0, 110.0), dead=target_dead,
                                                health=0.0 if target_dead else 100.0,
                                                attacks_back=False, party_slot=1)
                    ag = body(authsrv, ((2, 3.0, 0.0),), agents.ALLEGIANCE_PLAYER,
                              pos=(0.0, 60.0), hero=3, attacks_back=False, party_slot=0,
                              npc={"profession": 3, "level": 5}, casting=0,
                              cast_target=DOWNED)
                    st["agents"][HERO] = ag
                    sent = []
                    with contextlib.redirect_stdout(io.StringIO()):
                        authsrv.land_skill(lambda op, v, *a, **k: sent.append((op, list(v))),
                                           st, HERO, ag, 0)
                    stamped[target_dead] = ("aftercast_until" in ag,
                                            any(op == INT and v[:2] == [59, HERO]
                                                for op, v in sent))
            finally:
                agents.WORLD.tables["skills"]["2"] = _carried_skill("2")
        check(stamped.get(False) == (False, True) and stamped.get(True, (None,))[0] is True,
              "a RESSIG STOP ([59], the target already stands) stamps nothing; the same "
              "planted row completing on a corpse stamps (the take-back is what differs)",
              f"{stamped}")


# ---------------------------------------------------------------------------------
def _func(tree, name):
    return next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _calls(fn, name):
    return [n for n in ast.walk(fn) if isinstance(n, ast.Call)
            and getattr(n.func, "id", getattr(n.func, "attr", None)) == name]


def _flips(main_fn, attr, glob):
    for n in ast.walk(main_fn):
        if (isinstance(n, ast.If) and isinstance(n.test, ast.Attribute)
                and n.test.attr == attr):
            for s in n.body:
                if (isinstance(s, ast.Assign) and any(getattr(t, "id", None) == glob
                                                       for t in s.targets)
                        and isinstance(s.value, ast.Constant) and s.value.value is False):
                    return True
    return False


def section_source():
    print("== 3. source checks ==")
    import serverargs
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    main_fn = _func(tree, "main")
    globs = [n for n in ast.walk(main_fn) if isinstance(n, ast.Global)
             and "NPC_AFTERCAST" in n.names]
    check(_flips(main_fn, "no_npc_aftercast", "NPC_AFTERCAST") and globs,
          "main() sets NPC_AFTERCAST = False under --no-npc-aftercast, through a `global`")
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    parsed = (getattr(ap.parse_known_args(["--no-npc-aftercast"])[0], "no_npc_aftercast", None),
              getattr(ap.parse_args([]), "no_npc_aftercast", None))
    check(parsed == (True, False),
          "serverargs parses --no-npc-aftercast, default off", f"{parsed}")
    # main()'s own block, lifted out of the source and RUN in authsrv's namespace (the
    # test_agtrack_guard precedent): without its `global` the assignment would bind a
    # local and the flag would parse and never take effect.
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_npc_aftercast:", i_main)
    i_end = src.find("\n    if a.", i_flip + 1)
    flipped = None
    if 0 < i_main < i_flip < i_end:
        import argparse
        block = src[i_flip:i_end]
        body_src = "\n".join(line[4:] if line.startswith("    ") else line
                             for line in block.splitlines())
        code = "def _ac_flip(a):\n" + "\n".join("    " + ln for ln in body_src.splitlines())
        saved = authsrv.NPC_AFTERCAST
        try:
            exec(compile(code, "<main:no_npc_aftercast>", "exec"), authsrv.__dict__)
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.__dict__["_ac_flip"](argparse.Namespace(no_npc_aftercast=True))
            flipped = authsrv.NPC_AFTERCAST
        finally:
            authsrv.NPC_AFTERCAST = saved
            authsrv.__dict__.pop("_ac_flip", None)
    check(flipped is False,
          "main()'s --no-npc-aftercast block, EXECUTED, sets the MODULE's NPC_AFTERCAST to "
          "False", f"main {i_main} flip {i_flip} end {i_end} -> {flipped}")
    check(authsrv.capture_flags().get("NPC_AFTERCAST") is True,
          "and a capture header records which arm ran (capture_flags discovers it)")
    check(authsrv.NPC_AFTERCAST is True
          and any(isinstance(n, ast.Assign) and n.col_offset == 0
                  and getattr(n.targets[0], "id", None) == "NPC_AFTERCAST"
                  and isinstance(n.value, ast.Constant) and n.value.value is True
                  for n in tree.body),
          "NPC_AFTERCAST is a column-0 module bool, ON at import")
    for fn, n in (("enemy_attack_tick", 2), ("ally_cast_tick", 1), ("ally_attack_tick", 1)):
        got = len(_calls(_func(tree, fn), "npc_aftercast_holds"))
        check(got == n, f"{fn} asks npc_aftercast_holds {n} time(s)", f"{got}")
    ps = _func(tree, "pick_skill")
    check(not _calls(ps, "npc_aftercast_holds") and "aftercast" not in
          ast.get_source_segment(src, ps),
          "and pick_skill never does: the selector stays the testing fixture (Q19)")
    check(len(_calls(_func(tree, "land_skill"), "npc_aftercast")) == 1
          and len(_calls(tree, "npc_aftercast")) == 1,
          "the stamp is land_skill's, once -- the landing IS the completion")
    seg = ast.get_source_segment(src, _func(tree, "enemy_attack_tick"))
    i_reach = seg.find("_caster_skill_reach(agent, _sid)")
    i_ac = seg.find("npc_aftercast_holds(agent, _sid, now)")
    i_pay = seg.find("_pool.can_pay(_cost)")
    i_sw_ac = seg.find("npc_aftercast_holds(agent, None, now)")
    i_sw = seg.find('if now - agent.get("last_swing", 0.0) < interval:\n            continue')
    check(0 <= i_reach < i_ac < i_pay and 0 <= i_sw_ac < i_sw,
          "in the hostile loop the hold sits after the reach gate and before the pay gate "
          "(a CLOCK gate after the WORLD gates, RV-1), and ahead of the plain swing's "
          "interval gate", f"reach {i_reach} hold {i_ac} pay {i_pay}; swing hold {i_sw_ac} "
          f"interval {i_sw}")
    # The PARTY's hold ahead of the energy block (added after review, CD-3): below the
    # debit a held hero is charged on every tick it waits out the aftercast --
    # HEROENERGY's own defect class (its swing-clock gate sat after the debit until
    # 2026-10-01), and every driven fixture here runs with ENERGY off.
    seg = ast.get_source_segment(src, _func(tree, "ally_cast_tick"))
    i_unpack = seg.find("skill_id, activation, recharge = skills[slot]")
    i_hold = seg.find("npc_aftercast_holds(agent, skill_id, now)")
    i_cost = seg.find("cost, units = skill_cost(skill_id)")
    i_spend = seg.find("pool.spend(cost)")
    check(0 <= i_unpack < i_hold < i_cost < i_spend,
          "in ally_cast_tick the hold sits after the slot unpacks and AHEAD of the energy "
          "block (skill_cost .. pool.spend): a body held by its aftercast pays nothing",
          f"unpack {i_unpack} hold {i_hold} cost {i_cost} spend {i_spend}")


# ---------------------------------------------------------------------------------
def section_vault():
    print("== 4. the vault: the carried rows, and the reader over the live corpus ==")
    try:
        vaultpath.require_dir("content", why="the vault's skills table, which RECORD copies")
    except SystemExit as exc:
        LEDGER.skip("the carried rows against the vault's own (1 check)",
                    str(exc).splitlines()[0])
    else:
        loaded = agents.WORLD.rows("skills")
        off = {}
        for k, vals in RECORD.items():
            got = loaded.get(k)
            if got is None:
                off[k] = "absent"
                continue
            row = dict(zip(SKILL_COLUMNS, vals))
            cols = sorted(c for c in SKILL_COLUMNS if got.get(c, "absent") != row[c])
            if cols or getattr(got, "provenance", {}).get("build") != RECORD_BUILD:
                off[k] = (cols, getattr(got, "provenance", {}).get("build"))
        check(not off,
              f"every one of the {len(RECORD)} carried skills rows is the vault's own, column "
              f"for column, at build {RECORD_BUILD}", f"off={off}")
    try:
        vaultpath.require_dir("captures", "live", why="npcaftercast reads live captures")
    except SystemExit as exc:
        LEDGER.skip("the reader over the live corpus (9 checks)", str(exc).splitlines()[0])
        return
    out, err = io.StringIO(), io.StringIO()
    ours = OURS_P4
    argv = ["--json"] + (["--ours", ours] if os.path.isfile(ours) else [])
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        res = npcaftercast.main(argv)
    r = res["retail"]
    # --json's stdout is ONE JSON document (added after review, EV-7: capgaps' SET ASIDE
    # line used to lead it, and json.load refused the file); the census's lines go to
    # stderr.
    try:
        doc = json.loads(out.getvalue())
    except ValueError as exc:
        doc = exc
    check(isinstance(doc, dict) and doc.get("connections") == res["connections"]
          and "SET ASIDE" in err.getvalue(),
          "--json's stdout parses as one JSON document; the SET ASIDE line went to stderr",
          f"{type(doc).__name__}: {str(doc)[:120]} | stdout starts {out.getvalue()[:60]!r}")
    # floors, never exact counts: a new capture adds rows (counts redden on good news)
    check(r["n"] >= 1477 and r["min"] is not None and r["min"] >= 0.70 and r["p1"],
          "P1: >= 1,477 completions of a table-aftercast-0.75 spell, the next start never "
          "under 0.70 s (2026-10-07: min 0.704)", f"n={r['n']} min={r['min']}")
    check(r["p2"] and r["mass"] >= 527,
          "P2: at least 30 % of them inside [0.70, 0.80) (2026-10-07: 527 = 35.7 %)",
          f"{r['mass']} = {r['mass_share']:.1%}")
    check(r["p3"] and r["control_n"] >= 95 and set(r["control_skills"]) >= {2, 432, 433, 435},
          "P3: the aftercast-0 control re-starts under 0.70 s at least 25 % of the time "
          "(2026-10-07: 49 of 95, five skills)",
          f"{r['control_under']} of {r['control_n']} {r['control_skills']}")
    check(r["by_next"].get("swing", (0, 0))[0] >= 352
          and r["by_next"].get("swing", (0, 0))[1] >= 0.70,
          "the swings floor too (2026-10-07: 352, min 0.704)", f"{r['by_next']}")
    check(res["set_aside"] and all(s["capture"] == "20260928T103123" for s in res["set_aside"]),
          "the manifest-declared gapped connection is set aside by name, and only it",
          f"{[(s['capture'], s['connection']) for s in res['set_aside']]}")
    check(res["p5"] == "UNDECIDABLE" and res["e3_scored"] == 0 and res["e3_rows"] >= 35,
          "P5 UNDECIDABLE: the survey's 35 hero E5 -> E3 rows are all table-aftercast-0 "
          "skills, none scoreable", f"{res['p5']} scored {res['e3_scored']} of "
          f"{res['e3_rows']}: {res['e3_by_skill']}")
    # Re-aimed after review (EV-3): a [48] in the [58]'s OWN batch (gap 0.000) is no
    # evidence of order -- the same connection carries [48] before [58] in one batch and
    # after it in another -- so P6 scores only instants STRICTLY inside the window and
    # prints the co-batched one apart. The check holds the split: an instrument that
    # counted the 0.000 again would put it back in `p6_refuted_by` and redden here.
    check(len(res["p6_refuted_by"]) >= 2 and min(res["p6_refuted_by"]) > 0.0
          and res["p6_cobatched"] >= 1,
          "P6 REFUTED: an instant's [48] falls STRICTLY inside the window (2026-10-07: "
          "0.499 / 0.501, stance 11, n = 2), the [58]'s own-batch one printed apart (1) "
          "-- why the gate lets an instant through",
          f"strict {res['p6_refuted_by']} co-batched {res['p6_cobatched']}")
    if "ours" in res:
        o = res["ours"]
        check(not o["p1"] and o["min"] is not None and o["min"] < TICK,
              "P4: our own pre-aftercast capture authsrv-20260928T002701-c1 FAILS P1, "
              "inside one tick (2026-10-07: min 0.025)", f"n={o['n']} min={o['min']}")
    else:
        LEDGER.skip("P4 (1 check)", f"no {ours}")


def main():
    section_reader()
    section_server()
    section_source()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
