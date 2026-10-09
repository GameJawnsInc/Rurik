r"""test_heroqueue -- a HERO's 0x00E4 opens at its PICK, and its cast starts when the body
is free (HERO QUEUE, studies/skills 65.9; 2026-10-09).

    python toolkit/authsrv/test_heroqueue.py

WHAT IT IS REALLY CHECKING. authsrv.HERO_QUEUE (--no-hero-queue): ally_cast_tick, for a
HERO body, COMMITS a pick its two clock holds hold -- the NPC_AFTERCAST hold, and an attack
skill's swing clock once the running swing has landed -- by sending the pick's E4 at once
and keeping its slot and target; the release starts it with no second E4. The landing's
own tick picks too and never starts. Every way a committed pick dies before its start
closes it with [45, hero, 0] + E2. The retail evidence is heroqueue.py's (69 hero E4s:
45 ride their start, 4 wait an aftercast, 10 a swing, 8 a walk, 1 dropped); the known-bad
arm is the same server with the flag, whose E4 always rides the start.

  1  the READER's pure half on literal wire (bare machine): each class (with-start,
     aftercast, swing with its hit, walk, dropped with its [45], other), the observer
     never read, and the score's edges (SAME_S, the swing window, an E4 before the hit).
  2  the SERVER on carried rows (the vault's own, section 4 holds them to it):
     (a) a hero with 281 then 289 ready: 289's E4 in 281's [58] tick, behind it; no start
     there; the release tick carries E3, then 289's [60] with NO E4; the ledger closes;
     every start tick is --no-hero-queue's, whose E4 rides its [60] in the release tick;
     a completion's tick never starts a cast (--no-npc-aftercast: the next [60] the tick
     after the [58], 642d8957's cadence);
     (b) the [62] debit rides the START, not the leading E4 (ENERGY on);
     (c) a hero swinging at a foe with 322 coming ready mid-swing: the E4 after the
     swing's hit and before its [50], and none before the hit; --no-hero-queue's at
     the [50];
     (d) the drops, each [45] + E2 and a closed ledger: the target dies, the skill is
     suppressed, a knock-down, an interrupt, a transition, a death (behind the
     aftercast's [57] + E2); (e) a henchman queues nothing; (f) the fixtures' wire
     through heroqueue.rows_of: aftercast and swing rows on the default arm, none on
     the known-bad arm.
  3  source checks: the flag parsed and flipped in main() (EXECUTED), ON at import, in
     the capture header; ally_cast_tick commits at both holds, checks the queue before
     the dead-first pick, never starts on a landing tick, and opens the start's E4 only
     without a queue; the drops wired into the death, the knock-down, the interrupt and
     the net.
  4  the vault (skips only on an absent vault DIRECTORY): the carried rows against the
     vault's own; the reader over the live corpus -- Q1-Q6 hold, the class floors.
"""
import argparse
import ast
import contextlib
import io
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
import heroqueue                                               # noqa: E402
import vaultpath                                               # noqa: E402

HAVE_VAULT_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
HAVE_LIVE = os.path.isdir(vaultpath.vault_path("captures", "live"))
# Floors from the green runs of 2026-10-09, decided on the vault's DIRECTORIES (the
# test_npcaftercast rule): 24 bare, MEASURED with RURIK_VAULT at an empty directory AND at
# a nonexistent path (sections 1-3; section 4 declares its two skips); + 1 with
# vault/content (the carried rows) + 2 with vault/captures/live (the corpus) = 27, MEASURED.
# Four source mutants go red here (scratch hq_mutants.py): the landing-tick guard removed
# (1), the start's E4 sent even after a queue (3), a commit before the swing's hit (1), no
# commit at all (11).
FLOOR_BARE = 24
LEDGER = checks.Ledger("hero queue",
                       floor=FLOOR_BARE + (1 if HAVE_VAULT_CONTENT else 0)
                       + (2 if HAVE_LIVE else 0))
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
FLT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
E2, E3, E4, E5 = 0x00E2, 0x00E3, 0x00E4, 0x00E5
HERO, HENCH, FOE = 200, 210, 20
ORISON, VITAL, GASH = 281, 289, 322          # spells (table aftercast 0.75); an attack skill
TICK = 0.05
T0 = 1_000_000.0

# THE CARRIED ROWS, copied from the vault's LOADED skills rows (skilltable.py, build 38974)
# -- measured numbers, CLAUDE.md's gate; section 4 holds them to the vault's own.
RECORD_BUILD = 38974
SKILL_COLUMNS = ("activation", "aftercast", "recharge", "energy", "adrenaline",
                 "adrenaline_units", "attribute", "profession", "type_code", "target",
                 "combo", "combo_req", "weapon_req", "aoe_range", "skill_arguments",
                 "duration0", "duration15", "scale0", "scale15", "bonus_scale0",
                 "bonus_scale15", "projectile", "impact_visual", "touch_range",
                 "half_range")
RECORD = {
    "281": (1.0, 0.75, 2, 5, 0, 0, 13, 3, 5, 3, 0, 0, 0, 0.0, 2, 0, 0, 30, 80, 0, 0, 2077, 2077, False, False),
    "289": (0.75, 0.75, 2, 10, 0, 0, 15, 3, 6, 3, 0, 0, 0, 0.0, 2, 131072, 131072, 40, 200, 0, 0, 2077, 2077, False, False),
    "322": (0.0, 0.0, 3, 5, 0, 0, 17, 1, 14, 5, 0, 0, 185, 0.0, 2, 0, 0, 10, 40, 0, 0, 2077, 2077, False, False),
}


def _row(key):
    return content.Row(dict(zip(SKILL_COLUMNS, RECORD[key])), "skills", key,
                       {"source": "client-table", "extractor": "toolkit/clientscan/skilltable.py",
                        "build": RECORD_BUILD})


@contextlib.contextmanager
def carried():
    tables = agents.WORLD.tables
    kept = tables.get("skills")
    tables["skills"] = {k: _row(k) for k in RECORD}
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


FLAGS = ("HERO_QUEUE", "NPC_AFTERCAST", "HERO_E3_AFTERCAST", "ENERGY", "NPC_FOLLOW",
         "SKIP_LIVE_EFFECT", "INSTANT_ANNOUNCE")


@contextlib.contextmanager
def arm(queue=True, **flags):
    """A fake clock and the named flags, then restore. ENERGY and NPC_FOLLOW off unless
    asked (the cadence is the subject, not the pool or the chase)."""
    A = authsrv
    saved = {k: getattr(A, k) for k in FLAGS}
    saved_time = A.time
    base = {"HERO_QUEUE": queue, "ENERGY": False, "NPC_FOLLOW": False}
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


def body(bar, allegiance, pos, hero=None, **over):
    row = {"name": "body", "dead": False, "died_at": 0.0, "health": 100.0,
           "max_health": 100.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": allegiance, "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
           "effects": 0, "attacks_back": allegiance == agents.ALLEGIANCE_HOSTILE,
           "skills": tuple(tuple(s) for s in bar), "skill_ready": [0.0] * len(bar),
           "party_slot": 0, "npc": {"profession": 3, "level": 20}}
    if hero is not None:
        row["hero"] = hero
    row.update(over)
    return row


def world(player_health=40.0):
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": player_health,
          "player_dead": False}
    authsrv.effect_table(st)
    return st


def drive(st, secs, ticks=("effect_tick", "ally_cast_tick"), keep_health=40.0, at=None):
    """Drive the real ticks on the fake clock. `at` = {tick: fn(state)} runs before that
    tick's sweeps. Returns [(tick, t, op, vals)]."""
    sends = []
    n = [0]

    def send(op, vals, label="", quiet=False):
        sends.append((n[0], authsrv.time.t, op, list(vals)))

    with contextlib.redirect_stdout(io.StringIO()):
        for i in range(int(round(secs / TICK))):
            n[0] = i
            if keep_health is not None:
                st["player_health"] = keep_health
            if at and i in at:
                at[i](st, send)
            for name in ticks:
                getattr(authsrv, name)(send, st, 0)
            authsrv.time.t += TICK
    return sends


def of(sends, who):
    """The hero's own wire, [(tick, kind, detail)]: E4/E2/E3/E5 by skill, [60]/[50]/[58]
    /[45]/[57]/[59]/[46], and the [62] debit."""
    out = []
    for i, _t, op, v in sends:
        if op in (E2, E3, E4, E5) and v and v[0] == who:
            out.append((i, {E2: "E2", E3: "E3", E4: "E4", E5: "E5"}[op], v[1]))
        elif op in (INT, INT_T) and len(v) > 1 and v[1] == who and v[0] in (60, 50, 58, 45, 57, 59, 46):
            out.append((i, f"[{v[0]}]", v[-1] if v[0] in (60, 50) else None))
        elif op == FLT and len(v) > 1 and v[:2] == [62, who]:
            out.append((i, "[62]", None))
    return out


def ledger(sends, who):
    """The client's pending-record rule (test_pendskill's): E4 adds, E2/E3 drop. (misses,
    still open)."""
    held, miss = {}, 0
    for _i, _t, op, v in sends:
        if op not in (E2, E3, E4) or not v or v[0] != who:
            continue
        k = v[1]
        if op == E4:
            held[k] = held.get(k, 0) + 1
        elif held.get(k, 0) > 0:
            held[k] -= 1
        else:
            miss += 1
    return miss, {k: n for k, n in held.items() if n}


def as_seq(sends):
    return [(k, t, op, [op] + list(v)) for k, (_i, t, op, v) in enumerate(sends)]


# ---------------------------------------------------------------------------------
def section_reader():
    print("== 1. the reader's pure half, on literal wire ==")
    I, IT, F = heroqueue.OP_INT, heroqueue.OP_INT_TARGET, heroqueue.OP_FLOAT
    seq = [
        # agent 7: free -> with-start (E4, [62], [60] in one instant)
        (0, 1.0, E4, [E4, 7, 281, 0]), (1, 1.0, F, [F, 62, 7, 0]),
        (2, 1.0, IT, [IT, 60, 7, 1, 281]), (3, 2.0, E5, [E5, 7, 281, 0, 2]),
        (4, 2.0, I, [I, 58, 7, 0]),
        # ... and the next pick AT that [58]: aftercast (start 0.75 later, its E3 batch)
        (5, 2.0, E4, [E4, 7, 289, 0]), (6, 2.75, E3, [E3, 7, 281, 0]),
        (7, 2.75, F, [F, 62, 7, 0]), (8, 2.75, IT, [IT, 60, 7, 1, 289]),
        (9, 3.5, E3, [E3, 7, 289, 0]),
        # agent 8: a swing at 10.0, its hit at 10.35, the attack skill picked at 10.45 and
        # started at 10.89 -- swing
        (10, 10.0, IT, [IT, 4, 8, 9, 0]), (11, 10.35, I, [I, 1, 8, 0]),
        (12, 10.45, E4, [E4, 8, 322, 0]), (13, 10.89, F, [F, 62, 8, 0]),
        (14, 10.89, IT, [IT, 50, 8, 9, 322]), (15, 11.2, E3, [E3, 8, 322, 0]),
        # agent 8 again: picked, walks, starts 2.5 s on -- walk
        (16, 20.0, E4, [E4, 8, 322, 0]), (17, 20.5, heroqueue.OP_WALK, [heroqueue.OP_WALK, 8, 0]),
        (18, 22.5, IT, [IT, 50, 8, 9, 322]), (19, 22.9, E3, [E3, 8, 322, 0]),
        # agent 8: a pick dropped in its instant -- E4, [45], E2
        (20, 30.0, E4, [E4, 8, 385, 0]), (21, 30.0, I, [I, 45, 8, 0]),
        (22, 30.0, E2, [E2, 8, 385, 0]),
        # the observer (1): never read
        (23, 40.0, E4, [E4, 1, 281, 0]), (24, 41.0, IT, [IT, 60, 1, 1, 281]),
    ]
    rows = heroqueue.rows_of(seq, 1)
    cls = [(r["agent"], r["skill"], r["cls"]) for r in rows]
    check(cls == [(7, 281, "with-start"), (7, 289, "aftercast"), (8, 322, "swing"),
                  (8, 322, "walk"), (8, 385, "dropped")],
          "the five classes on literal wire, per agent, and the observer never read",
          f"{cls}")
    sc = heroqueue.score(rows)
    check(sc["q1"] and sc["q2"] and sc["q3"] and sc["q4"] and sc["q5"]
          and sc["aftercast_leads"] == [0.75] and sc["swing_gaps"] == [0.89]
          and sc["q6"] == [(30.0, 385)] and sc["queued"] == 2,
          "the score: the aftercast lead 0.75, the swing's start -> [50] 0.89 with the E4 "
          "after the hit, the walk past 1 s, every [62] at its start, the one drop",
          f"{sc}")
    # the edges: an E4 BEFORE the swing's hit fails Q3; a swing gap outside 0.85-0.95 fails
    early = [dict(rows[2], prev=(0.30, 4), hit=0.35)]
    wide = [dict(rows[2], prev=(0.10, 4), start=(0.70, 50, 322))]
    check(not heroqueue.score(early)["q3"] and not heroqueue.score(wide)["q3"]
          and heroqueue.classify(dict(rows[0], start=(0.05, 60, 281))) == "with-start"
          and heroqueue.classify(dict(rows[0], start=(0.051, 60, 281), prev=None, walks=0))
          == "other",
          "Q3 fails on an E4 before the hit and on a gap outside 0.85-0.95; SAME_S is 0.05 "
          "inclusive")
    # a [62] riding the leading E4 instead of the start fails Q5
    lead62 = [dict(rows[1], spend=0.0)]
    check(not heroqueue.score(lead62)["q5"],
          "Q5 fails on a [62] that rides the leading E4")


# ---------------------------------------------------------------------------------
def _hero_spells(queue, energy=False, secs=4.0):
    """A hero with 281 then 289 ready, the player held at 1 health -- so a landed heal
    leaves it under HERO_HEAL_AT (0.9) and the next spell has a target at the [58]."""
    with carried(), arm(queue=queue, ENERGY=energy):
        st = world()
        st["agents"][HERO] = body(((ORISON, 1.0, 2.0), (VITAL, 0.75, 2.0)),
                                  agents.ALLEGIANCE_PLAYER, (50.0, 0.0), hero=3,
                                  attacks_back=False)
        sends = drive(st, secs, keep_health=1.0)
    return sends, st


def section_aftercast():
    print("== 2. (a) (b) the aftercast queue ==")
    on, st_on = _hero_spells(True)
    off, _st = _hero_spells(False)
    w_on, w_off = of(on, HERO), of(off, HERO)
    f58 = [i for i, k, _d in w_on if k == "[58]"]
    e4 = [(i, d) for i, k, d in w_on if k == "E4"]
    st60 = [(i, d) for i, k, d in w_on if k == "[60]"]
    tick58 = [x for x in w_on if f58 and x[0] == f58[0]]
    check(f58 and (f58[0], VITAL) in e4
          and [k for _i, k, _d in tick58] == ["E5", "[58]", "E4"]
          and not [1 for i, d in st60 if i == f58[0]],
          "(a) 289's E4 in 281's [58] tick, BEHIND the [58] (retail: the [58]'s batch, 3 "
          "of 4), and no start there",
          f"the [58] tick {tick58}; E4s {e4}; starts {st60}")
    rel = next((i for i, d in st60 if d == VITAL), None)
    reltick = [k for i, k, _d in w_on if i == rel]
    check(rel is not None and reltick == ["E3", "[60]"],
          "    the release tick: 281's E3, then 289's [60] -- with NO E4 (the pick's opened "
          "0.75 s earlier)", f"tick {rel}: {reltick}")
    s_on = [(i, d) for i, k, d in w_on if k in ("[60]", "[50]")]
    s_off = [(i, d) for i, k, d in w_off if k in ("[60]", "[50]")]
    off_rel = [k for i, k, _d in w_off if s_off[1:] and i == s_off[1][0]]
    check(s_on == s_off and len(s_on) >= 3 and off_rel == ["E3", "E4", "[60]"],
          "    every start tick equals --no-hero-queue's (the queue moves no start); that "
          "arm's E4 rides its [60] in the release tick, E3, E4, [60]",
          f"on {s_on} off {s_off}; off's release tick {off_rel}")
    # the landing tick picks but never STARTS: with the aftercast hold off the next cast
    # starts on the tick after the [58] (642d8957's cadence) on both queue arms
    with carried(), arm(queue=True, NPC_AFTERCAST=False):
        st = world()
        st["agents"][HERO] = body(((ORISON, 1.0, 2.0), (VITAL, 0.75, 2.0)),
                                  agents.ALLEGIANCE_PLAYER, (50.0, 0.0), hero=3,
                                  attacks_back=False)
        nq = drive(st, 2.0, keep_health=1.0)
    w_nq = of(nq, HERO)
    f58n = next((i for i, k, _d in w_nq if k == "[58]"), None)
    nxt = next((i for i, k, d in w_nq if k == "[60]" and d == VITAL), None)
    check(f58n is not None and nxt == f58n + 1
          and not [1 for i, k, _d in w_nq if i == f58n and k in ("[60]", "E4")],
          "    a completion's tick never STARTS a cast: with --no-npc-aftercast the next "
          "[60] is the tick after the [58], its E4 with it (no hold, no queue)",
          f"[58] tick {f58n}, 289's [60] tick {nxt}; {[x for x in w_nq if x[0] in (f58n, nxt)]}")
    m_on, open_on = ledger(on, HERO)
    check(m_on == 0 and set(open_on) <= {VITAL, ORISON} and sum(open_on.values()) <= 1,
          "    the client's ledger: 0 misses, at most the cast in flight at the end open",
          f"misses {m_on} open {open_on}")
    # (b) the debit rides the START
    en, _st = _hero_spells(True, energy=True)
    w_en = of(en, HERO)
    rel_en = next((i for i, k, d in w_en if k == "[60]" and d == VITAL), None)
    f58e = next((i for i, k, _d in w_en if k == "[58]"), None)
    check(rel_en is not None and [k for i, k, _d in w_en if i == rel_en] == ["E3", "[62]", "[60]"]
          and "[62]" not in [k for i, k, _d in w_en if i == f58e],
          "(b) with ENERGY on, the queued cast's [62] rides its START -- E3, [62], [60] at "
          "the release -- and none rides the leading E4 (retail: 47 of 47 at the start)",
          f"[58] tick {[x for x in w_en if x[0] == f58e]}; release {[x for x in w_en if x[0] == rel_en]}")
    return on, off


def _hero_swing(queue, secs=3.0):
    real = authsrv.party_fight_target
    authsrv.party_fight_target = lambda state, aid, agent, now: FOE
    try:
        with carried(), arm(queue=queue):
            st = world()
            st["agents"][FOE] = body((), agents.ALLEGIANCE_HOSTILE, (60.0, 0.0),
                                     attacks_back=False, health=1e6, max_health=1e6)
            hero = body(((GASH, 0.0, 3.0),), agents.ALLEGIANCE_PLAYER, (50.0, 0.0), hero=3,
                        attacks_back=False, attack_speed=1.33, npc={"profession": 1, "level": 20})
            hero["skill_ready"] = [T0 + 0.30]          # comes ready mid-swing
            st["agents"][HERO] = hero
            sends = drive(st, secs, ticks=("effect_tick", "ally_cast_tick", "ally_attack_tick"))
    finally:
        authsrv.party_fight_target = real
    return sends


def section_swing():
    print("== 2. (c) the swing queue ==")
    on, off = _hero_swing(True), _hero_swing(False)

    def marks(sends):
        sw = [i for i, _t, op, v in sends if op == INT_T and v[:2] == [4, HERO]]
        hit = [i for i, _t, op, v in sends if op == INT and v[:2] == [1, HERO]]
        e4 = [i for i, _t, op, v in sends if op == E4 and v[:2] == [HERO, GASH]]
        s50 = [i for i, _t, op, v in sends if op == INT_T and v[:2] == [50, HERO]]
        return sw, hit, e4, s50
    sw, hit, e4, s50 = marks(on)
    check(sw and hit and e4 and s50 and sw[0] < hit[0] <= e4[0] < s50[0]
          and not [i for i in e4 if i < hit[0]],
          "(c) GASH comes ready mid-swing: its E4 after that swing's hit and before its "
          "[50], none before the hit (retail: 10 of 10 after the hit)",
          f"swing {sw[:2]} hit {hit[:2]} E4 {e4[:2]} [50] {s50[:2]}")
    sw0, hit0, e40, s500 = marks(off)
    check(s500 == s50[:len(s500)] and e40 and s500 and e40[0] == s500[0],
          "    --no-hero-queue: the same [50] tick, its E4 in it", f"E4 {e40[:2]} [50] {s500[:2]}")


def _queued(st_fn):
    """A hero with 281 then 289 ready, driven to just past 281's [58]: 289 queued. Then
    `st_fn(state, send)` and a further 2 s."""
    with carried(), arm(queue=True):
        st = world()
        st["agents"][HERO] = body(((ORISON, 1.0, 2.0), (VITAL, 0.75, 2.0)),
                                  agents.ALLEGIANCE_PLAYER, (50.0, 0.0), hero=3,
                                  attacks_back=False)
        first = drive(st, 1.10)
        q = dict(st["agents"][HERO].get("queued_cast") or {})
        later = drive(st, 2.0, at={0: st_fn})
    return first, later, q, st


def section_drops():
    print("== 2. (d) the drops: [45] + E2, the ledger closed ==")
    cases = []

    def kill_target(st, send):
        st["player_dead"] = True
        st["player_health"] = 0.0

    def suppress(st, send):
        st["agents"][HERO]["skill_disabled_ids"] = [VITAL]

    def kd(st, send):
        authsrv.knock_down(send, st, HERO, 0, "the test's knock-down", 2.0)

    def interrupt(st, send):
        authsrv.interrupt_body(send, st, HERO, st["agents"][HERO], 0, 57, FOE, mode="action")

    def transition(st, send):
        st["agents"][HERO]["effects"] |= agents.EFFECT_TRANSITION

    def die(st, send):
        row = st["agents"][HERO]
        row["health"] = 0.0
        authsrv.kill_agent(send, st, HERO, row, 0, authsrv.time.time(), reward=False)

    for name, fn, keep in (("its target dies", kill_target, None),
                           ("its skill is suppressed", suppress, 1.0),
                           ("a knock-down", kd, 1.0), ("an interrupt", interrupt, 1.0),
                           ("a transition", transition, 1.0), ("the hero's death", die, 1.0)):
        with carried(), arm(queue=True):
            st = world()
            st["agents"][HERO] = body(((ORISON, 1.0, 2.0), (VITAL, 0.75, 2.0)),
                                      agents.ALLEGIANCE_PLAYER, (50.0, 0.0), hero=3,
                                      attacks_back=False)
            first = drive(st, 1.10, keep_health=1.0)
            q = dict(st["agents"][HERO].get("queued_cast") or {})
            later = drive(st, 2.0, at={0: fn}, keep_health=keep)
            row = st["agents"].get(HERO) or {}
            sk = row.get("skills") or ()
            inflight = set()
            if row.get("casting") is not None and row.get("cast_lands_at") is not None:
                inflight.add(sk[row["casting"]][0])
            if row.get("queued_cast"):
                inflight.add(row["queued_cast"]["skill_id"])
            inflight |= {sid for _at, sid in row.get("hero_e3_due", ())}
        w = of(later, HERO)
        w0 = [x for x in w if x[0] == 0]
        i45 = next((k for k, x in enumerate(w0) if x[1] == "[45]"), None)
        ok45 = (i45 is not None and i45 + 1 < len(w0) and w0[i45 + 1][1:] == ("E2", VITAL))
        no_start = not [1 for _i, k, d in w if k == "[60]" and d == VITAL]
        miss, open_ = ledger(first + later, HERO)
        cases.append((name, q.get("skill_id"), ok45, no_start, miss,
                      {k: n for k, n in open_.items() if k not in inflight}, w0))
    for name, qsk, ok45, no_start, miss, open_, w0 in cases:
        if name == "an interrupt":
            # GWW un-queues; the AI may pick again at once (RECONSTRUCTION): a fresh E4
            no_start = True
        extra = ""
        if name == "the hero's death":
            ks = [k for _i, k, _d in w0]
            ok45 = ok45 and "[57]" in ks and ks.index("[57]") < ks.index("[45]")
            extra = " -- behind the completed cast's [57] + E2 (SKILLS-AC8's close)"
        check(qsk == VITAL and ok45 and no_start and miss == 0 and not open_,
              f"(d) {name} with 289 queued: [45, hero, 0] then its E2"
              + (", and the AI may pick it again" if name == "an interrupt"
                 else ", 289 never starts")
              + f"; the ledger closes (0 misses, nothing open but a cast in flight){extra}",
              f"queued {qsk}; that tick {w0}; misses {miss} open {open_}")


def section_henchman_and_replay(on, off):
    print("== 2. (e) (f) a henchman; the replay through the reader ==")
    with carried(), arm(queue=True):
        st = world()
        st["agents"][HENCH] = body(((ORISON, 1.0, 2.0), (VITAL, 0.75, 2.0)),
                                   agents.ALLEGIANCE_PLAYER, (50.0, 0.0), attacks_back=False)
        sends = drive(st, 4.0)
        seen = st["agents"][HENCH].get("queued_cast")
    check(seen is None and not [1 for _i, _t, op, v in sends if op in (E2, E3, E4, E5)]
          and [1 for _i, _t, op, v in sends if op == INT_T and v[:2] == [60, HENCH]],
          "(e) a HENCHMAN casts, sends no E-family and queues nothing (its re-pick unchanged)")
    r_on = heroqueue.score(heroqueue.rows_of(as_seq(on), P))
    r_off = heroqueue.score(heroqueue.rows_of(as_seq(off), P))
    check(r_on["classes"].get("aftercast", 0) >= 1 and r_on["q2"]
          and r_off["classes"].get("aftercast", 0) == 0 and r_off["queued"] == 0,
          "(f) the fixture's wire through heroqueue.rows_of: aftercast rows (Q2 HOLDS) on "
          "the default arm, none on --no-hero-queue", f"on {r_on['classes']} off {r_off['classes']}")


# ---------------------------------------------------------------------------------
def _func(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def _calls(fn, name):
    return [n for n in ast.walk(fn) if isinstance(n, ast.Call)
            and getattr(n.func, "id", getattr(n.func, "attr", None)) == name]


def section_source():
    print("== 3. source checks ==")
    import serverargs
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    main_fn = _func(tree, "main")
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    parsed = (getattr(ap.parse_known_args(["--no-hero-queue"])[0], "no_hero_queue", None),
              getattr(ap.parse_args([]), "no_hero_queue", None))
    globs = [n for n in ast.walk(main_fn) if isinstance(n, ast.Global) and "HERO_QUEUE" in n.names]
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_hero_queue:", i_main)
    i_end = src.find("\n    if a.", i_flip + 1)
    flipped = None
    if 0 < i_main < i_flip < i_end:
        block = src[i_flip:i_end]
        body_src = "\n".join(ln[4:] if ln.startswith("    ") else ln for ln in block.splitlines())
        code = "def _hq_flip(a):\n" + "\n".join("    " + ln for ln in body_src.splitlines())
        saved = authsrv.HERO_QUEUE
        try:
            exec(compile(code, "<main:no_hero_queue>", "exec"), authsrv.__dict__)
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.__dict__["_hq_flip"](argparse.Namespace(no_hero_queue=True))
            flipped = authsrv.HERO_QUEUE
        finally:
            authsrv.HERO_QUEUE = saved
            authsrv.__dict__.pop("_hq_flip", None)
    check(parsed == (True, False) and globs and flipped is False,
          "--no-hero-queue parses (default off) and main()'s block, EXECUTED, sets the "
          "MODULE's HERO_QUEUE to False through a `global`",
          f"parsed {parsed} globals {len(globs)} -> {flipped}")
    check(authsrv.HERO_QUEUE is True and authsrv.capture_flags().get("HERO_QUEUE") is True
          and any(isinstance(n, ast.Assign) and n.col_offset == 0
                  and getattr(n.targets[0], "id", None) == "HERO_QUEUE"
                  and isinstance(n.value, ast.Constant) and n.value.value is True
                  for n in tree.body),
          "HERO_QUEUE is a column-0 module bool, ON at import, in the capture header")
    seg = ast.get_source_segment(src, _func(tree, "ally_cast_tick"))
    i_land = seg.find("land_skill(send, state, agent_id, agent, conn_id)")
    i_check = seg.find("_q = hero_queue_check(send, state, agent_id, agent)")
    i_dead = seg.find("_dead = party_dead_target(state, agent_id) if _q is None else None")
    i_hold = seg.find("npc_aftercast_holds(agent, skill_id, now)")
    i_c1 = seg.find('"its aftercast", conn_id)')
    i_sw = seg.find('if _atk and now - agent.get("last_swing", 0.0) < _interval:')
    i_c2 = seg.find('now, "its swing", conn_id)')
    i_landed = seg.find("        if _landed:\n            continue")
    i_debit = seg.find("_debit = None")
    i_e4 = seg.find('if _picked is None or _picked["skill_id"] != int(skill_id):')
    check(0 <= i_land < i_check < i_dead < i_hold < i_c1 < i_sw < i_c2 < i_landed < i_debit < i_e4
          and len(_calls(_func(tree, "ally_cast_tick"), "hero_queue_commit")) == 2,
          "ally_cast_tick: the landing, the queue check ahead of the dead-first pick, a "
          "commit at the aftercast hold and at the swing clock (2 calls), the landing tick "
          "never starting (ahead of the debit), the start's E4 only without a queue",
          f"{(i_land, i_check, i_dead, i_hold, i_c1, i_sw, i_c2, i_landed, i_debit, i_e4)}")
    wired = {fn: len(_calls(_func(tree, fn), "hero_queue_drop"))
             for fn in ("hero_death_tick", "knock_down", "interrupt_body", "ally_cast_tick",
                        "hero_queue_check")}
    check(all(n == 1 for n in wired.values()),
          "the drop is wired once each into the death, the knock-down, the interrupt, the "
          "net and the queue check", f"{wired}")


# ---------------------------------------------------------------------------------
def section_vault():
    print("== 4. the vault ==")
    try:
        vaultpath.require_dir("content", why="the vault's skills table, which RECORD copies")
    except SystemExit as exc:
        LEDGER.skip("the carried rows against the vault's own (1 check)", str(exc).splitlines()[0])
    else:
        loaded = agents.WORLD.rows("skills")
        off = {}
        for k, vals in RECORD.items():
            got = loaded.get(k)
            if got is None:
                off[k] = "absent"
                continue
            cols = [c for c, v in zip(SKILL_COLUMNS, vals) if got.get(c, "absent") != v]
            if cols or getattr(got, "provenance", {}).get("build") != RECORD_BUILD:
                off[k] = (cols, getattr(got, "provenance", {}).get("build"))
        check(not off, f"the {len(RECORD)} carried rows are the vault's own at build "
              f"{RECORD_BUILD}", f"off={off}")
    try:
        vaultpath.require_dir("captures", "live", why="heroqueue reads live captures")
    except SystemExit as exc:
        LEDGER.skip("the reader over the live corpus (2 checks)", str(exc).splitlines()[0])
        return
    with contextlib.redirect_stdout(io.StringIO()):
        rows = heroqueue.census()
    sc = heroqueue.score(rows)
    c = sc["classes"]
    # floors, never exact counts: a new hero tape adds rows (counts redden on good news)
    check(sc["n"] >= 69 and c.get("with-start", 0) >= 45 and c.get("aftercast", 0) >= 4
          and c.get("swing", 0) >= 10 and c.get("walk", 0) >= 8 and c.get("dropped", 0) >= 1,
          "the corpus's hero E4s: >= 69, with-start >= 45, aftercast >= 4, swing >= 10, "
          "walk >= 8, dropped >= 1 (2026-10-09)", f"n={sc['n']} {c}")
    check(sc["q1"] and sc["q2"] and sc["q3"] and sc["q4"] and sc["q5"]
          and (392.729, 385) in sc["q6"],
          "Q1-Q6 HOLD on retail: with-start at 0.000, the aftercast at 0.70-0.80, the swing's "
          "start -> [50] 0.85-0.95 with every E4 after the hit, the walks past 1 s, every "
          "[62] at its start, the 392.729 drop",
          f"aftercast {sc['aftercast_leads']} swing {sc['swing_gaps']} walk {sc['walk_leads']} "
          f"[62] {sc['spend_at_start']}/{sc['paid']} drops {sc['q6']}")


def main():
    section_reader()
    on, off = section_aftercast()
    section_swing()
    section_drops()
    section_henchman_and_replay(on, off)
    section_source()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
