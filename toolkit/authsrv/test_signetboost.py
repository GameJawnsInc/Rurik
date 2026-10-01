r"""test_signetboost -- the player's own Resurrection Signet raises (single use), and a
boss's death is the party's morale boost that recharges it (RESSIG-P / RESSIG-B,
2026-10-01; PLAN-LOG "RESSIG-P and RESSIG-B").

WHAT IT IS REALLY CHECKING. RESSIG (SLICE-F53) made a body's signet single-use and left
two things open. (P) the PLAYER's press of skill 2 at a party corpse ran its 3 s, sent
E5 [.., 0] and E6, and raised nobody -- resurrect_target was reached from a body's
landing only. Retail's observer raised twice on tape: [58], (the [20] visual), E7 [me,
2, 0], E3, [8, me, 0], then the rise, no E5. (B) nothing refreshed a spent signet but a
zone. WIKI (GWW "Morale Boost"): a boss's death is a 2% boost to the party and it
recharges skills, the signet's one refresh. No boss dies on tape: the boost's wire is
RECONSTRUCTION, the shapes a morale change already has.

  1  the REAL press + cast_tick at a dead hero: [58], E7 [me, 2, 0], E3, [8 -> 0], the
     rise, in that order; no E5, no E6 ever; the signet spent.
  2  a second press while spent: the bare release (E2), nothing begins.
  3  a corpse that already stands at the landing: the cast STOPS ([59], E2), nothing is
     spent, and a later press raises.
  4  the KNOWN-BAD arm (--no-player-resurrection): E5 [.., 0], E6, the corpse stays down.
  5  the REAL kill_agent on a BOSS: the player's morale +2 (0x009C [me, 102]), the hero's
     +2, the spent signets come back (E6 [me, 2, 0], E6 [hero, 2, 0], the hero's slot
     ready), each E6 right behind an E5 [.., 0] that repaints the icon (the E6 alone left
     it grey on 20261001T112625; --boost-e6-only is that arm); a death penalty is
     countered (+2 on the kill's own tick) and the cap holds (110).
  6  a NON-boss kill boosts nothing; the KNOWN-BAD arm (--no-boss-boost) boosts nothing.
  7  the wiring: the spawn marks a glow row as a boss; both switches.
  8  RESSIG-T: a press at NOBODY (target 0) with a corpse in reach is refused at once,
     #1966 and the release -- retail's 'Invalid Target', the owner's reading
     2026-10-01 -- nothing begins and no corpse is auto-picked; the KNOWN-BAD arm
     (--no-resurrect-target-gate) casts its 3 s.
"""
import math
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

# Floor from the BARE-MACHINE green run of 2026-10-01 (RURIK_VAULT at an empty
# directory): 20, and 20 with the vault -- nothing here reads it (skill 2's timing and
# cost are pinned in main(), its [skill_effect.2] row is the repo's). PLAYER_RESURRECTION,
# BOSS_MORALE_BOOST and BOOST_REPAINT False in the source redden 15; BOOST_REPAINT alone 2.
# 20 -> 25 for section 8 (RESSIG-T), bare and vault alike; RESURRECT_TARGET_GATE
# False in the source reddens 3.
LEDGER = checks.Ledger("signet and boost", floor=25)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
HERO, BOSS, GRUNT = 200, 110, 111
RES = 2
E2, E3, E5, E6, E7 = 0x00E2, 0x00E3, 0x00E5, 0x00E6, 0x00E7
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
STATUS = authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
MORALE = authsrv.GAME_SMSG_AGENT_MORALE


class Wire:
    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals)))

    def take(self):
        out, self.sent = self.sent, []
        return out


def _hero(dead=True, **over):
    row = {"name": "Academy Monk", "dead": dead, "died_at": time.time() - 3.0,
           "health": 0.0 if dead else 480.0, "max_health": 480.0, "base_max_health": 480.0,
           "base_max_energy": 30.0, "max_energy": 30.0, "last_hit": 0.0,
           "pos": (0.0, 100.0), "plane": 0, "allegiance": agents.ALLEGIANCE_PLAYER,
           "effects": 0, "attack_speed": 1.75, "attacks_back": False,
           "skills": ((RES, 3.0, 0.0),), "skill_ready": [0.0], "hero": 3,
           "npc": {"profession": 3, "level": 20}, "party_slot": 0,
           "energy_profession": 3}
    row.update(over)
    return row


def _foe(boss):
    return {"name": "Bandit Raider", "dead": False, "died_at": 0.0, "health": 0.0,
            "max_health": 60.0, "last_hit": 0.0, "pos": (500.0, 500.0), "plane": 0,
            "allegiance": agents.ALLEGIANCE_HOSTILE, "effects": 0, "attacks_back": True,
            "skills": (), "skill_ready": [], "boss": boss,
            "npc": {"level": 1, "profession": 1}}


def _world(**over):
    st = {"agents": {HERO: _hero()}, "pos": (0.0, 0.0), "player_health": 140.0,
          "player_dead": False}
    st.update(over)
    return st


def _press(st, wire, target=HERO):
    authsrv.handle_skill_press([0, RES, 0, target], wire, st, 1,
                               authsrv.GAME_CMSG_USE_SKILL)


def _land(st, wire, passes=3):
    for cast in st.get("pending_casts", ()):
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            cast[k] -= 30.0
    for _ in range(passes):
        authsrv.cast_tick(wire, st, 1)


def _idx(sent, pred):
    return next((i for i, (op, v) in enumerate(sent) if pred(op, v)), None)


def section_raise():
    print("== 1. the player's signet raises, in retail's order ==")
    st, w = _world(), Wire()
    _press(st, w)
    press = w.take()
    _land(st, w)
    land = w.take()
    i58 = _idx(land, lambda op, v: op == INT and v[:2] == [agents.GV_SKILL_FINISHED, P])
    i7 = _idx(land, lambda op, v: op == E7 and v == [P, RES, 0])
    i3 = _idx(land, lambda op, v: op == E3 and v == [P, RES, 0])
    i8 = _idx(land, lambda op, v: op == INT and v[:3] == [agents.GV_ACTION_HOLD, P, 0]) \
        if hasattr(agents, "GV_ACTION_HOLD") else _idx(land, lambda op, v: op == INT and v[:3] == [8, P, 0])
    iup = _idx(land, lambda op, v: op == STATUS and v[0] == HERO)
    check(None not in (i58, i7, i3, i8, iup) and i58 < i7 < i3 < i8 < iup,
          "the completion is [58], E7 [me, 2, 0], E3, [8 -> 0], then the hero's status -- "
          "the observer's raise on retail, 2 of 2",
          f"58@{i58} E7@{i7} E3@{i3} 8@{i8} rise@{iup}: {land}")
    check(not [1 for op, v in press + land if op == E5 and v[:2] == [P, RES]],
          "and NO E5 for the signet (retail: none on a completed raise)", f"{land}")
    check(not st["agents"][HERO]["dead"], "the hero stands", "")
    _land(st, w)
    more = w.take()
    check(st.get("boost_spent") == {RES: 0} and not [1 for op, v in more if op == E6]
          and not st.get("pending_casts"),
          "the signet is SPENT (boost_spent), the cycle closed with no E6 -- the slot "
          "stays painted +inf", f"spent {st.get('boost_spent')}, later {more}")
    return st


def section_spent_press(st):
    print("== 2. a press while spent is released, nothing begins ==")
    st["agents"][HERO] = _hero()
    w = Wire()
    _press(st, w)
    sent = w.take()
    check((E2, [P, RES, 0]) in sent and not st.get("pending_casts")
          and not [1 for op, v in sent if op == 0x00E4],
          "the bare release (E2 [me, 2, 0]) and no cast entry", f"{sent}")


def section_stop():
    print("== 3. a corpse already standing: the cast stops, nothing is spent ==")
    st, w = _world(), Wire()
    _press(st, w)
    st["agents"][HERO].update(dead=False, health=480.0)    # someone else raised it
    w.take()
    _land(st, w)
    land = w.take()
    check((INT, [agents.GV_SKILL_STOPPED, P, 0]) in land and (E2, [P, RES, 0]) in land
          and not [1 for op, v in land if op in (E7, E5, E3)],
          "the landing finds the hero standing: [59] and E2, no E7 / E5 / E3", f"{land}")
    check(not st.get("boost_spent"), "and the signet is NOT spent", f"{st.get('boost_spent')}")
    st["agents"][HERO] = _hero()
    _press(st, w)
    _land(st, w)
    later = w.take()
    check((E7, [P, RES, 0]) in later and not st["agents"][HERO]["dead"],
          "the next death: the unspent signet raises", f"{later}")


def section_known_bad_raise():
    print("== 4. the known-bad arm: --no-player-resurrection ==")
    saved = authsrv.PLAYER_RESURRECTION
    authsrv.PLAYER_RESURRECTION = False
    try:
        st, w = _world(), Wire()
        _press(st, w)
        _land(st, w)
        sent = w.take()
        check((E5, [P, RES, 0, 0]) in sent and (E6, [P, RES, 0]) in sent
              and st["agents"][HERO]["dead"],
              "E5 [me, 2, 0, 0] and E6, and the hero stays down -- the pre-fix press",
              f"{sent}")
    finally:
        authsrv.PLAYER_RESURRECTION = saved


def _kill(st, aid):
    w = Wire()
    authsrv.kill_agent(w, st, aid, st["agents"][aid], 1, time.time(), reward=True)
    return w.take()


def _spent_world():
    hero = _hero(dead=False, skill_ready=[math.inf], boost_spent={RES},
                 hero_recharged_due={})
    st = _world(agents={HERO: hero, BOSS: _foe(True), GRUNT: _foe(False)},
                boost_spent={RES: 0}, morale=100)
    return st


def section_boost():
    print("== 5. a boss dies: the party's morale boost recharges the signets ==")
    st = _spent_world()
    sent = _kill(st, BOSS)
    check((MORALE, [P, 102]) in sent and (MORALE, [HERO, 102]) in sent,
          "the player and the hero gain 2% (0x009C [.., 102]) -- WIKI's boss boost",
          f"{[v for op, v in sent if op == MORALE]}")
    check((E6, [P, RES, 0]) in sent and (E6, [HERO, RES, 0]) in sent,
          "the spent signets come back on the wire: E6 [me, 2, 0], E6 [hero, 2, 0]",
          f"{[v for op, v in sent if op == E6]}")
    pairs = True
    for who in (P, HERO):
        i = next((k for k, m in enumerate(sent) if m == (E6, [who, RES, 0])), None)
        pairs = pairs and i is not None and i > 0 and sent[i - 1] == (E5, [who, RES, 0, 0])
    check(pairs,
          "each E6 rides right behind an E5 [.., 2, 0, 0] -- the repaint E6 alone never "
          "sends (its worker is the bare field write; the owner saw the icons stay grey)",
          f"{[(hex(op), v) for op, v in sent if op in (E5, E6)]}")
    hero = st["agents"][HERO]
    check(not st.get("boost_spent") and hero["skill_ready"][0] <= time.time()
          and not hero.get("boost_spent"),
          "and in the books: the player's spent set empty, the hero's slot ready",
          f"{st.get('boost_spent')} {hero['skill_ready']} {hero.get('boost_spent')}")
    st = _spent_world()
    st["morale"] = 85
    authsrv.hero_morale_apply(st, HERO, st["agents"][HERO], 85)
    sent = _kill(st, BOSS)
    words = {a: [v[1] for op, v in sent if op == MORALE and v[0] == a] for a in (P, HERO)}
    check(all(len(w) >= 2 and w[-1] == w[-2] + 2 and w[-1] < 100 for w in words.values()),
          "a death penalty is countered: the boost is +2 on top of the kill's own 75-XP "
          "tick (85 -> 86 -> 88), for both", f"{words}")
    st = _spent_world()
    st["morale"] = 110
    authsrv.hero_morale_apply(st, HERO, st["agents"][HERO], 110)
    sent = _kill(st, BOSS)
    check(authsrv.player_morale(st) == 110 and authsrv.hero_morale(st, HERO) == 110
          and (E6, [P, RES, 0]) in sent,
          "at the +10% cap the morale holds and the skills still recharge", f"{sent[:6]}")


def section_no_boost():
    print("== 6. no boss, no boost; and the known-bad arm ==")
    st = _spent_world()
    sent = _kill(st, GRUNT)
    check(not [1 for op, v in sent if op == E6] and st.get("boost_spent") == {RES: 0}
          and authsrv.player_morale(st) == 100,
          "a NON-boss kill boosts nobody and recharges nothing", f"{sent[:6]}")
    saved = authsrv.BOOST_REPAINT
    authsrv.BOOST_REPAINT = False
    try:
        st = _spent_world()
        sent = _kill(st, BOSS)
        check((E6, [P, RES, 0]) in sent and not [1 for op, v in sent if op == E5],
              "KNOWN-BAD (--boost-e6-only): the bare E6s -- usable, the icon left grey, "
              "as 20261001T112625 showed", f"{[(hex(op), v) for op, v in sent if op in (E5, E6)]}")
    finally:
        authsrv.BOOST_REPAINT = saved
    saved = authsrv.BOSS_MORALE_BOOST
    authsrv.BOSS_MORALE_BOOST = False
    try:
        st = _spent_world()
        sent = _kill(st, BOSS)
        check(not [1 for op, v in sent if op == E6] and st.get("boost_spent") == {RES: 0},
              "KNOWN-BAD (--no-boss-boost): the boss dies like anyone, the signet stays "
              "spent -- the owner's single use with no refresh", f"{sent[:6]}")
    finally:
        authsrv.BOSS_MORALE_BOOST = saved


def section_wiring():
    print("== 7. the wiring ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check('"boss": row.get("glow") is not None' in src,
          "a spawn row with a glow is a boss (the boss aura)", "")
    check(authsrv.PLAYER_RESURRECTION is True and authsrv.BOSS_MORALE_BOOST is True
          and authsrv.BOSS_BOOST_PERCENT == 2
          and authsrv.BOOST_REPAINT is True and '"--boost-e6-only"' in args
          and "if a.boost_e6_only:" in src
          and '"--no-player-resurrection"' in args and '"--no-boss-boost"' in args
          and "if a.no_player_resurrection:" in src and "if a.no_boss_boost:" in src,
          "both ship ON at 2%; --no-player-resurrection and --no-boss-boost revert", "")


def section_no_target():
    print("== 8. a press at NOBODY is refused at once: retail's 'Invalid Target' ==")
    import chatdefs                                            # noqa: PLC0415
    st, w = _world(), Wire()                      # a dead hero lies 100 u away
    _press(st, w, target=0)
    sent = w.take()
    core = (authsrv.GAME_SMSG_CHAT_MESSAGE_CORE, [chatdefs.refusal_body(1966)])
    i_core = sent.index(core) if core in sent else None
    i_e2 = sent.index((E2, [P, RES, 0])) if (E2, [P, RES, 0]) in sent else None
    check(chatdefs.REFUSE_INVALID_TARGET == 1966
          and None not in (i_core, i_e2) and i_core < i_e2
          and sent[i_core + 1][0] == authsrv.GAME_SMSG_CHAT_MESSAGE_SERVER,
          "target 0: #1966 on the warning panel, then the release -- before anything "
          "else, with a corpse in reach (the owner, retail, 2026-10-01)", f"{sent}")
    check(not [1 for op, v in sent if op == 0x00E4] and not st.get("pending_casts")
          and not st.get("boost_spent") and st["agents"][HERO]["dead"],
          "nothing begins: no E4, no cast entry, nothing spent, the corpse NOT auto-picked",
          f"pending {st.get('pending_casts')}, spent {st.get('boost_spent')}")
    _press(st, w)                                 # the same signet, aimed this time
    check([1 for op, v in w.take() if op == 0x00E4] and st.get("pending_casts"),
          "and the same signet pressed AT the corpse still casts", "")
    saved = authsrv.RESURRECT_TARGET_GATE
    authsrv.RESURRECT_TARGET_GATE = False
    try:
        st, w = _world(), Wire()
        _press(st, w, target=0)
        sent = w.take()
        check([1 for op, v in sent if op == 0x00E4] and st.get("pending_casts")
              and core not in sent,
              "KNOWN-BAD (--no-resurrect-target-gate): the press at nobody casts its 3 s "
              "-- every run before RESSIG-T", f"{sent[:4]}")
    finally:
        authsrv.RESURRECT_TARGET_GATE = saved
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check(authsrv.RESURRECT_TARGET_GATE is True and '"--no-resurrect-target-gate"' in args
          and "if a.no_resurrect_target_gate:" in src,
          "the gate ships ON; --no-resurrect-target-gate reverts", "")


def main():
    saved = (authsrv.skill_timing, authsrv.skill_cost)
    # Skill 2's own row, pinned so a bare machine runs the same cycle: 3.0 s, no
    # aftercast, recharge 0 (the client's table), no cost.
    _timing = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (3.0, 0.0, 0) if int(sid) == RES else _timing(sid)
    authsrv.skill_cost = lambda sid: (0, 0)
    try:
        st = section_raise()
        section_spent_press(st)
        section_stop()
        section_known_bad_raise()
        section_boost()
        section_no_boost()
        section_wiring()
        section_no_target()
    finally:
        authsrv.skill_timing, authsrv.skill_cost = saved
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
