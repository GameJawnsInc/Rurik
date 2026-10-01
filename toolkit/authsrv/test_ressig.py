r"""test_ressig -- Resurrection Signet is single-use, refreshed by a morale boost
(RESSIG, 2026-09-30; PLAN-LOG "RESSIG").

WHAT IT IS REALLY CHECKING. The client's table gives skill 2 a recharge of 0, and that
is what this server used, so on 20260930T202753 two heroes raised each other 66 times.
The owner's rule and WIKI (GWW "Resurrection Signet") say the signet recharges only on
a morale boost or a zone change. Retail agrees: over the live corpus 44 casters
completed a raise and none completed a second on one connection; every repeat start was
stopped with [59] because another caster's raise landed first, and a stopped cast did
not spend the signet. A completed raise is [58], E7 [caster, 2, 0], E3, then the rise,
with no E5 (3 of 3). The row says so with `recharge_on = "morale_boost"`.

  1  a hero's completed raise through ally_cast_tick: [58], then E7 [hero, 2, 0], then
     E3, then the corpse's status -- no E5 -- and the slot spent (skill_ready +inf).
  2  SINGLE USE: the corpse killed again and twenty seconds of ticks -- no second cast
     of skill 2 by the spent hero.
  3  TWO CASTERS on one corpse in one tick: the first raises (E7, E3), the second is
     STOPPED at its landing ([59], E2), raises nobody and is NOT spent -- it raises
     the next death; the PENDSKILL ledger closes every record, 0 misses.
  4  a HENCHMAN caster: single use too, and no E-family on the wire.
  5  the KNOWN-BAD arm (--no-resurrection-single-use): E5 [hero, 2, 0, 0] + E3 ahead
     of the [58], no E7, and the same hero raises the same corpse twice -- the loop.
  6  the content row and the switch's wiring; the zone and wipe paths (source).
  7  RETAIL (vault): completed raises per caster per connection never exceed one
     (>= 40 casters), every completed raise by the observer or a hero carries E7 then
     E3 in its stamp and no E5. Skipped without the captures.
"""
import collections
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

# Floor from the BARE-MACHINE green run of 2026-09-30 (RURIK_VAULT at an empty
# directory): 20 -- sections 1-6; section 7 (the captures) declares a skip. 22 with
# the vault. RESURRECTION_SINGLE_USE = False in the source reddens 11.
LEDGER = checks.Ledger("resurrection signet", floor=20)
check = checks.adopt(LEDGER)

E2, E3, E4, E5, E7 = 0x00E2, 0x00E3, 0x00E4, 0x00E5, 0x00E7
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
STATUS = authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
P = authsrv.PLAYER_AGENT_ID
CORPSE, A, B = 30, 200, 201
RES = 2


class Wire:
    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals)))

    def take(self):
        out, self.sent = self.sent, []
        return out


def client_ledger(sent, observer=P):
    """PENDSKILL's rule: E4 adds a record for anyone but the observer, E2/E3 drop one."""
    held = collections.Counter()
    misses = []
    for op, v in sent:
        if op not in (E2, E3, E4) or v[0] == observer:
            continue
        key = (v[0], v[1], v[2])
        if op == E4:
            held[key] += 1
        elif held[key] > 0:
            held[key] -= 1
        else:
            misses.append(key)
    return misses, +held


def _body(name, pos, slot, hero=None, **over):
    row = {"name": name, "dead": False, "died_at": 0.0, "health": 100.0,
           "max_health": 100.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0,
           "attack_speed": authsrv.ENEMY_ATTACK_SPEED, "attacks_back": False,
           "skills": (), "skill_ready": [],
           "npc": {"profession": 3, "level": 5}, "party_slot": slot}
    if hero is not None:
        row["hero"] = hero
    row.update(over)
    return row


def _caster(name, pos, slot, hero):
    return _body(name, pos, slot, hero=hero, skills=((RES, 3.0, 0.0),), skill_ready=[0.0])


def _world(*casters):
    corpse = _body("corpse", (0.0, 110.0), 0, dead=True, health=0.0, died_at=time.time())
    ags = {CORPSE: corpse}
    for aid, row in casters:
        ags[aid] = row
    return {"agents": ags, "pos": (0.0, 0.0), "player_health": 100.0}


def _tick(st, wire):
    authsrv.ally_cast_tick(wire, st, 1)
    return wire.take()


def _land_all(st, wire):
    for aid, row in st["agents"].items():
        if row.get("cast_lands_at") is not None:
            row["cast_lands_at"] = time.time() - 0.01
    return _tick(st, wire)


def _elapse(st, seconds=10.0):
    """Let `seconds` pass for every body's slot clock (a finite skill_ready moves
    back; a SPENT slot's +inf stays +inf). Without it the start's own anchor (the
    3 s activation) keeps the slot busy and a 'no second cast' check passes for the
    wrong reason -- the first draft of this file did exactly that."""
    for row in st["agents"].values():
        row["skill_ready"] = [r - seconds if r != math.inf else r
                              for r in (row.get("skill_ready") or [])]


def _kill(st, wire, aid=CORPSE):
    row = st["agents"][aid]
    row["health"] = 0.0
    authsrv.kill_agent(wire, st, aid, row, 1, time.time(), reward=False)
    return wire.take()


def _starts(sent, caster):
    return [v for op, v in sent if op == INT_T and v[:2] == [60, caster] and v[3:4] == [RES]]


def _idx(sent, pred):
    return next((i for i, (op, v) in enumerate(sent) if pred(op, v)), None)


def section_raise():
    print("== 1. a hero's completed raise: [58], E7, E3, the rise -- no E5 ==")
    st, wire = _world((A, _caster("hero A", (0.0, 60.0), 1, 3))), Wire()
    start = _tick(st, wire)
    check(_starts(start, A) == [[60, A, CORPSE, RES]],
          "the hero starts Resurrection Signet at the corpse", f"{start}")
    land = _land_all(st, wire)
    i58 = _idx(land, lambda op, v: op == INT and v[:2] == [authsrv.agents.GV_SKILL_FINISHED, A])
    i7 = _idx(land, lambda op, v: op == E7 and v == [A, RES, 0])
    i3 = _idx(land, lambda op, v: op == E3 and v == [A, RES, 0])
    iup = _idx(land, lambda op, v: op == STATUS and v[0] == CORPSE)
    check(None not in (i58, i7, i3, iup) and i58 < i7 < i3 < iup,
          "the landing is [58], E7 [hero, 2, 0], E3, then the corpse's status -- retail's "
          "order, 3 of 3", f"58@{i58} E7@{i7} E3@{i3} rise@{iup}: {land}")
    check(not [1 for op, v in land if op == E5],
          "and NO E5 (retail sends none on a completed signet)", f"{land}")
    row = st["agents"][A]
    check(row["skill_ready"][0] == math.inf and RES in row.get("boost_spent", ()),
          "the slot is SPENT: skill_ready +inf, the skill in boost_spent",
          f"{row['skill_ready']} {row.get('boost_spent')}")
    check(not st["agents"][CORPSE]["dead"], "and the corpse stands", "")
    misses, held = client_ledger(start + land)
    check(misses == [] and not held, "the PENDSKILL ledger: 0 misses, 0 open",
          f"{misses} {dict(held)}")
    return st, wire


def section_single_use(st, wire):
    print("== 2. single use: the same corpse dies again, the spent hero casts nothing ==")
    _kill(st, wire)
    _elapse(st)
    casts = []
    for _ in range(40):
        casts += _starts(_tick(st, wire), A)
        for row in st["agents"].values():
            if row.get("cast_lands_at") is not None:
                row["cast_lands_at"] = time.time() - 0.01
    check(casts == [] and st["agents"][CORPSE]["dead"],
          "forty ticks with the corpse down and the hero's only skill spent: no second "
          "cast, the corpse stays down (the loop of 20260930T202753 is gone)",
          f"casts {casts}")


def section_two_casters():
    print("== 3. two casters on one corpse: one raises, one is STOPPED and not spent ==")
    st, wire = _world((A, _caster("hero A", (0.0, 60.0), 1, 3)),
                      (B, _caster("hero B", (40.0, 60.0), 2, 7))), Wire()
    start = _tick(st, wire)
    check(_starts(start, A) and _starts(start, B),
          "both heroes start on the corpse in one tick", f"{start}")
    land = _land_all(st, wire)
    raised_by = [v[0] for op, v in land if op == E7]
    stopped = [v[1] for op, v in land if op == INT and v[0] == agents.GV_SKILL_STOPPED]
    check(len(raised_by) == 1 and len(stopped) == 1 and raised_by[0] != stopped[0],
          "one E7 (the raise) and one [59] (the stop) -- retail's same-stamp pair "
          "(13/14 -> 12 at 624.85; 4/5/6 -> 3 at 615.62)", f"E7 {raised_by} [59] {stopped}")
    first = raised_by[0] if raised_by else None
    second = stopped[0] if stopped else None
    check(second is not None and (E2, [second, RES, 0]) in land
          and (E3, [second, RES, 0]) not in land,
          "the stopped hero's record closes with E2, not E3", f"{land}")
    check(second is not None and st["agents"][second]["skill_ready"][0] <= time.time()
          and RES not in st["agents"][second].get("boost_spent", ()),
          "and its signet is NOT spent", f"{st['agents'].get(second, {}).get('skill_ready')}")
    misses, held = client_ledger(start + land)
    check(misses == [] and not held, "the ledger over both: 0 misses, 0 open",
          f"{misses} {dict(held)}")
    _kill(st, wire)
    _elapse(st)
    nxt = _tick(st, wire)
    check(second is not None and _starts(nxt, second) and not _starts(nxt, first),
          "the corpse dies again: the STOPPED hero raises it, the spent one does not",
          f"{nxt}")


def section_henchman():
    print("== 4. a henchman: single use, no E-family ==")
    st, wire = _world((A, _caster("henchman", (0.0, 60.0), 1, None))), Wire()
    sent = _tick(st, wire) + _land_all(st, wire)
    check(not [1 for op, _v in sent if op in (E2, E3, E4, E5, E7)]
          and st["agents"][A]["skill_ready"][0] == math.inf
          and not st["agents"][CORPSE]["dead"],
          "a henchman's raise lands with no E-family and spends its signet", f"{sent}")
    _kill(st, wire)
    _elapse(st)
    again = _tick(st, wire)
    check(not _starts(again, A), "and it does not cast it again", f"{again}")


def section_known_bad():
    print("== 5. the known-bad arm: --no-resurrection-single-use ==")
    saved = authsrv.RESURRECTION_SINGLE_USE
    authsrv.RESURRECTION_SINGLE_USE = False
    try:
        st, wire = _world((A, _caster("hero A", (0.0, 60.0), 1, 3))), Wire()
        _tick(st, wire)
        land = _land_all(st, wire)
        i5 = _idx(land, lambda op, v: op == E5 and v[:2] == [A, RES])
        i58 = _idx(land, lambda op, v: op == INT and v[:2] == [agents.GV_SKILL_FINISHED, A])
        check(i5 is not None and i58 is not None and i5 < i58
              and not [1 for op, _v in land if op == E7],
              "E5 [hero, 2, 0, 0] + E3 ahead of the [58], no E7 -- the pre-fix segment",
              f"{land}")
        _kill(st, wire)
        _elapse(st)
        again = _tick(st, wire)
        check(_starts(again, A) == [[60, A, CORPSE, RES]],
              "and the same hero raises the same corpse again: the loop", f"{again}")
    finally:
        authsrv.RESURRECTION_SINGLE_USE = saved


def section_wiring():
    print("== 6. the row, the switch, the zone and the wipe ==")
    row = agents.WORLD.get("skill_effect", "2")
    others = [k for k in agents.WORLD.keys("skill_effect")
              if agents.WORLD.get("skill_effect", k).get("recharge_on")] \
        if hasattr(agents.WORLD, "keys") else ["2"]
    check(row.get("recharge_on") == "morale_boost" and others == ["2"],
          "content's [skill_effect.2] says recharge_on = morale_boost, and no other row does",
          f"{row.get('recharge_on')} {others}")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check(authsrv.RESURRECTION_SINGLE_USE is True
          and '"--no-resurrection-single-use"' in args
          and "if a.no_resurrection_single_use:" in src,
          "RESURRECTION_SINGLE_USE ships ON and --no-resurrection-single-use reverts it", "")
    create = src[src.index("def hero_body_create("):]
    create = create[:create.index("\ndef ")]
    wipe = src[src.index("def wipe_to_shrine("):]
    wipe = wipe[:wipe.index("\ndef ")]
    check('"skill_ready": [0.0] * len(hero_cast_bar(state, _hid))' in create
          and "skill_ready" not in wipe,
          "a ZONE refreshes it (hero_body_create builds the bar's clock fresh); the "
          "shrine re-create after a wipe does not touch it (no zone, no boost)", "")


def section_retail():
    print("== 7. retail: never two completed raises by one caster on one connection ==")
    try:
        import livewire
        import henchjoin
        root = livewire.captures_root()
    except Exception as exc:                                    # pragma: no cover
        LEDGER.skip("the retail census", f"livewire unavailable: {exc}")
        return
    if not root or not os.path.isdir(root):
        LEDGER.skip("the retail census", "no live captures on this machine")
        return
    casters = repeats = stops = e7_ok = e7_seen = e5_bad = 0
    for capdir, _who in livewire.live_captures():
        for cf in livewire.connections(capdir):
            c, merged, _ok = livewire.decode_conn(capdir, cf)
            if c is None or not merged:
                continue
            done = collections.Counter()
            for i, (t, d, op, v) in enumerate(merged):
                if not (d == "s2c" and op == 0x00A0 and len(v) > 4 and int(v[1]) == 60
                        and int(v[4]) == RES):
                    continue
                a, tgt = int(v[2]), int(v[3])
                end = None
                for (t2, d2, op2, v2) in merged[i + 1:]:
                    if t2 > t + 4.5:
                        break
                    if (d2 == "s2c" and op2 == 0x009F and len(v2) > 3 and int(v2[2]) == a
                            and int(v2[1]) in (58, 59)):
                        end = (t2, int(v2[1]))
                        break
                if end is None:
                    continue
                if end[1] == 59:
                    stops += 1
                    continue
                stamp = [(op2, v2) for (t2, d2, op2, v2) in merged
                         if d2 == "s2c" and abs(t2 - end[0]) <= 0.01]
                rose = any(op2 == 0x00F1 and int(v2[1]) == tgt and not (int(v2[2]) & 0x10)
                           for op2, v2 in stamp)
                if not rose:
                    continue
                done[a] += 1
                fam = [op2 for op2, v2 in stamp if op2 in (E3, E5, E7) and int(v2[1]) == a
                       and len(v2) > 2 and int(v2[2]) == RES]
                if fam:
                    e7_seen += 1
                    e7_ok += fam[:2] == [E7, E3]
                    e5_bad += E5 in fam
            casters += len(done)
            repeats += sum(1 for n in done.values() if n > 1)
    check(casters >= 40 and repeats == 0,
          "every caster on every connection completes AT MOST ONE raise (44 casters "
          "on the census)", f"{casters} casters, {repeats} with a second raise, "
          f"{stops} stopped starts")
    check(e7_seen >= 3 and e7_ok == e7_seen and e5_bad == 0,
          "every completed raise that carries the family is E7 then E3, with no E5",
          f"{e7_ok} of {e7_seen}, E5 in {e5_bad}")


def main():
    st, wire = section_raise()
    section_single_use(st, wire)
    section_two_casters()
    section_henchman()
    section_known_bad()
    section_wiring()
    section_retail()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
