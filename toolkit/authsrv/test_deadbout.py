r"""test_deadbout -- a hostile's bout ends with its last target: once everybody it could
fight is dead it stands a beat and walks home (MONSTERAI-W, 2026-09-30; PLAN-LOG
"MONSTERAI-W").

WHAT IT IS REALLY CHECKING. On 20260930T231034 the owner watched the Bandit Raider hold
aggro through the whole 10 s respawn countdown: it stood ~570 u from its anchor over the
corpses and walked home only when the shrine rise moved its target out of range (the
log: "GIVES UP: the player 2326 u from its anchor -- its target left the area"), three
wipes of three. Nothing ended a bout whose targets were all dead: hostile_target found
nobody, the dead pick went back to the follow, and the follow halted and returned every
tick. Retail (studies/monsterai/FINDINGS.md sec.20): every hostile fighting away from
home sent its first order 0.49-3.00 s after the wipe, before the rise; one fighting at
home stood. The fixture is the run's raider, anchor (1301,3850), standing at
(1349,3282) over a dead player and two dead heroes, through the REAL enemy_move_tick.

  1  the first tick after the wipe sends nothing and starts the beat.
  2  just short of DEAD_BOUT_GIVE_UP_AFTER: still nothing.
  3  past it: ONE 0x0029 RETURN leg toward the anchor, no 0x0028 / 0x002B / 0x002A, the
     give-up printed with the MONSTERAI-W reason; the walk ends AT the anchor well
     inside the countdown.
  4  AT HOME (fought within LEASH_HOME_RADIUS of its anchor): it stands -- nothing sent.
  5  the bout goes on while somebody lives: a live hero in range is re-picked; a target
     raised inside the beat clears the clock; a live body beyond AGGRO_RANGE does not
     hold the raider (it walks home -- RECONSTRUCTION).
  6  the KNOWN-BAD arm (--dead-target-holds): thirty seconds over the corpses, nothing --
     the owner's report.
  7  the switch's wiring.
  8  RETAIL (vault): the wipe census re-derived from the live corpus. Skipped without
     the captures.
"""
import contextlib
import io
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
# directory): 13 -- sections 1-7; section 8 (the captures) declares a skip. 17 with the
# vault. DEAD_TARGET_ENDS_BOUT = False in the source reddens 6.
LEDGER = checks.Ledger("dead bout", floor=13)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
RAIDER, H1, H2 = 110, 200, 201
POINT = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
FOLLOW = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
HALT = authsrv.GAME_SMSG_AGENT_STOP_MOVING
SPEED = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED
ANCHOR = (1301.0, 3850.0)          # the run's raider: its create point
STOOD = (1349.0, 3282.0)           # where it stood over the corpses (570 u out)
CORPSE = (1348.0, 3202.0)          # the player's body, 80 u away


class Wire:
    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals), label))


def _hero(aid, pos, dead=True):
    return {"name": "Academy Monk", "dead": dead, "died_at": time.time() - 5.0,
            "health": 0.0 if dead else 480.0, "max_health": 480.0, "last_hit": 0.0,
            "pos": pos, "plane": 0, "allegiance": agents.ALLEGIANCE_PLAYER,
            "effects": 0, "attacks_back": False, "skills": (), "skill_ready": [],
            "npc": {"level": 20, "profession": 3}}


def _wiped(stood=STOOD, anchor=ANCHOR):
    """The run's third wipe: the player and both heroes dead, the raider standing
    where it fought, its last pick the player."""
    now = time.time()
    raider = {"name": "Bandit Raider", "dead": False, "died_at": 0.0, "health": 2900.0,
              "max_health": 3000.0, "last_hit": 0.0, "pos": stood, "plane": 0,
              "anchor": anchor, "allegiance": agents.ALLEGIANCE_HOSTILE, "effects": 0,
              "attacks_back": True, "attack_speed": 1.75, "skills": (), "skill_ready": [],
              "npc": {"level": 10, "profession": 1}, "follow": None, "moving": False,
              "moved_at": now, "target": P, "target_was": P, "target_locked": False}
    return {"agents": {RAIDER: raider,
                       H1: _hero(H1, (1404.0, 3150.0)), H2: _hero(H2, (1290.0, 3150.0))},
            "pos": CORPSE, "plane": 0, "player_dead": True,
            "player_died_at": now - 0.2, "player_health": 0.0}


def _tick(st):
    w = Wire()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        authsrv.enemy_move_tick(w, st, 1)
    return w.sent, out.getvalue()


def _elapse(st, seconds):
    """Move the raider's beat clock `seconds` into the past (the tick reads the wall
    clock, so the clock under test is moved instead)."""
    r = st["agents"][RAIDER]
    if r.get("tdead_since") is not None:
        r["tdead_since"] -= seconds


def section_beat():
    print("== 1-2. the wipe: nothing at once, nothing inside the beat ==")
    st = _wiped()
    sent, _log = _tick(st)
    r = st["agents"][RAIDER]
    check(sent == [] and r.get("tdead_since") is not None and r.get("leash_return") is None,
          "the first tick after the wipe sends nothing and starts the beat (retail's "
          "first order came 0.49-3.00 s after the last death, never at it)",
          f"sent {[hex(op) for op, _v, _l in sent]}, since {r.get('tdead_since')}")
    _elapse(st, authsrv.DEAD_BOUT_GIVE_UP_AFTER - 0.3)
    sent, _log = _tick(st)
    check(sent == [] and r.get("leash_return") is None,
          f"0.3 s short of the {authsrv.DEAD_BOUT_GIVE_UP_AFTER:.1f} s beat: still "
          f"standing over the corpses", f"sent {[hex(op) for op, _v, _l in sent]}")
    return st


def section_give_up(st):
    print("== 3. past the beat: it walks home ==")
    _elapse(st, 0.4)
    sent, log = _tick(st)
    r = st["agents"][RAIDER]
    ops = [op for op, _v, _l in sent]
    leg = sent[0][1][1] if ops == [POINT] else None
    on_line = False
    if leg is not None:
        dx, dy = ANCHOR[0] - STOOD[0], ANCHOR[1] - STOOD[1]
        n = math.hypot(dx, dy)
        lx, ly = leg[0] - STOOD[0], leg[1] - STOOD[1]
        along = (lx * dx + ly * dy) / n
        across = abs(-lx * dy + ly * dx) / n
        on_line = 0.0 < along <= authsrv.RETURN_LEG_LENGTH + 1e-6 and across < 1.0
    check(ops == [POINT] and on_line and "RETURN" in sent[0][2]
          and r.get("leash_return") is not None and r.get("tdead_since") is None,
          "ONE 0x0029 RETURN leg on the copy->anchor line, at most RETURN_LEG_LENGTH -- "
          "no 0x0028, no 0x002B, no 0x002A (retail: none in any post-wipe window)",
          f"sent {[(hex(op), v) for op, v, _l in sent]}")
    check("GIVES UP" in log and "MONSTERAI-W" in log and "nobody alive" in log,
          "and the log names why: the give-up with the MONSTERAI-W reason",
          log.strip()[:240])
    # The walk home, on a fake clock from the give-up: the return's own tick.
    t0 = r["moved_at"]
    legs, t = [], t0
    w = Wire()
    with contextlib.redirect_stdout(io.StringIO()):
        while authsrv.leash_returning(r) and t < t0 + 10.0:
            t += 0.05
            authsrv._leash_return_tick(w, st, 1, RAIDER, r, t, None)
    legs = [v[1] for op, v, _l in w.sent if op == POINT]
    home = math.hypot(r["pos"][0] - ANCHOR[0], r["pos"][1] - ANCHOR[1])
    check(not authsrv.leash_returning(r) and home < 1.0 and legs
          and tuple(legs[-1]) == ANCHOR and t - t0 < 3.0
          and not [1 for op, _v, _l in w.sent if op in (HALT, SPEED)],
          "the walk ends AT the anchor in under 3 s -- long before the 10 s countdown "
          "(retail's stander-shaped agent 38 stood 43 u from its create 6.3 s after "
          "the wipe)", f"{len(legs) + 1} legs, home {home:.0f} u, {t - t0:.2f} s")


def section_home():
    print("== 4. at home it stands ==")
    st = _wiped(stood=(ANCHOR[0] + 40.0, ANCHOR[1] - 50.0))
    st["pos"] = (ANCHOR[0] + 40.0, ANCHOR[1] - 130.0)
    _tick(st)
    _elapse(st, 30.0)
    sent, _log = _tick(st)
    r = st["agents"][RAIDER]
    check(sent == [] and r.get("leash_return") is None,
          "a raider that fought 64 u from its anchor sends nothing thirty seconds on -- "
          "home already (retail: 7 of 7 wipes where the hostile fought at its create "
          "point, 0 orders)", f"sent {[hex(op) for op, _v, _l in sent]}")


def section_alive():
    print("== 5. the bout goes on while somebody lives ==")
    st = _wiped()
    st["agents"][H2] = _hero(H2, (1290.0, 3150.0), dead=False)
    _tick(st)
    _elapse(st, 30.0)
    sent, _log = _tick(st)
    r = st["agents"][RAIDER]
    check(r.get("target") == H2 and r.get("leash_return") is None
          and not [1 for _op, _v, l in sent if "RETURN" in l],
          "a live hero 145 u away is re-picked and the raider fights on -- no give-up",
          f"target {r.get('target')}, sent {[(hex(op), l[:40]) for op, _v, l in sent]}")

    st = _wiped()
    _tick(st)
    _elapse(st, authsrv.DEAD_BOUT_GIVE_UP_AFTER - 0.5)
    st["player_dead"] = False                     # a raise in place, inside the beat
    st["player_health"] = 100.0
    sent, _log = _tick(st)
    r = st["agents"][RAIDER]
    _elapse(st, 30.0)                              # a stale clock would fire now
    sent2, _log = _tick(st)
    check(r.get("tdead_since") is None and r.get("leash_return") is None
          and not [1 for _op, _v, l in sent + sent2 if "RETURN" in l],
          "a target raised INSIDE the beat clears the clock and the bout goes on",
          f"since {r.get('tdead_since')}, sent {[(hex(op), l[:40]) for op, _v, l in sent + sent2]}")

    st = _wiped()
    st["agents"][H2] = _hero(H2, (STOOD[0] + 1500.0, STOOD[1]), dead=False)
    _tick(st)
    _elapse(st, authsrv.DEAD_BOUT_GIVE_UP_AFTER + 0.1)
    sent, _log = _tick(st)
    r = st["agents"][RAIDER]
    check(r.get("leash_return") is not None and [op for op, _v, _l in sent] == [POINT],
          "a live hero 1,500 u away (beyond AGGRO_RANGE) does not hold the raider over "
          "the corpses: it walks home (RECONSTRUCTION -- the corpus has wipes only)",
          f"sent {[hex(op) for op, _v, _l in sent]}")


def section_known_bad():
    print("== 6. the known-bad arm: --dead-target-holds ==")
    saved = authsrv.DEAD_TARGET_ENDS_BOUT
    authsrv.DEAD_TARGET_ENDS_BOUT = False
    try:
        st = _wiped()
        sent = []
        for _i in range(3):
            s, _log = _tick(st)
            sent += s
            _elapse(st, 10.0)
            st["agents"][RAIDER]["tdead_since"] = time.time() - 30.0
        r = st["agents"][RAIDER]
        check(sent == [] and r.get("leash_return") is None
              and tuple(r["pos"]) == STOOD,
              "the raider stands at (1349,3282), 570 u from home, over the corpses -- "
              "the owner's report, reproduced", f"sent {[hex(op) for op, _v, _l in sent]}")
        st["player_dead"] = False                  # the rise, at the shrine
        st["pos"] = (1536.0, 1536.0)
        s, log = _tick(st)
        check([op for op, _v, _l in s] == [POINT] and "left the area" in log,
              "and walks home only at the rise, by EV-2's lost contact -- the run's "
              "\"its target left the area\"", log.strip()[:200])
    finally:
        authsrv.DEAD_TARGET_ENDS_BOUT = saved


def section_wiring():
    print("== 7. the switch ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    fol = src[src.index("def _npc_follow_tick("):]
    fol = fol[:fol.index("\ndef ")]
    check(authsrv.DEAD_TARGET_ENDS_BOUT is True and '"--dead-target-holds"' in args
          and "if a.dead_target_holds:" in src
          and "elif _anchor is not None and DEAD_TARGET_ENDS_BOUT:" in fol,
          "DEAD_TARGET_ENDS_BOUT ships ON, --dead-target-holds reverts it, and the rule "
          "lives in the follow tick's dead-target branch", "")
    check(1.0 <= authsrv.DEAD_BOUT_GIVE_UP_AFTER <= 2.5
          and authsrv.DEAD_BOUT_GIVE_UP_AFTER < authsrv.LEASH_SECONDS,
          "the beat sits inside retail's 0.49-3.00 s at its median, and is shorter than "
          "the leash's own dwell", f"{authsrv.DEAD_BOUT_GIVE_UP_AFTER}")


def section_retail():
    print("== 8. retail: the wipe census ==")
    try:
        import livewire
        import henchjoin
        root = livewire.captures_root()
    except Exception as exc:                                    # pragma: no cover
        LEDGER.skip("the retail wipe census", f"livewire unavailable: {exc}")
        return
    if not root or not os.path.isdir(root):
        LEDGER.skip("the retail wipe census", "no live captures on this machine")
        return
    raised = away = home_wipes = 0
    late, chased, halted, home_moved = [], [], [], []
    for capdir, gf in livewire.live_connections():
        stamp = os.path.basename(capdir)
        _c, merged, _ok = livewire.decode_conn(capdir, gf)
        if not merged:
            continue
        me = henchjoin.whose_agent(merged)
        if me is None:
            continue
        members = {me} | set(henchjoin.party_of(merged))
        dead = {m: False for m in members}
        create, pos, starts = {}, {}, []
        wipe = None
        for i, (t, d, op, v) in enumerate(merged):
            if d != "s2c":
                continue
            if op == 0x0020 and len(v) > 5 and isinstance(v[5], (tuple, list)):
                create[int(v[1])] = pos[int(v[1])] = (float(v[5][0]), float(v[5][1]))
            elif op in (0x0029, 0x002A, 0x002C) and len(v) > 2 \
                    and isinstance(v[2], (tuple, list)):
                pos[int(v[1])] = (float(v[2][0]), float(v[2][1]))
            if op == 0x00A0 and len(v) > 3 and int(v[1]) in (4, 50, 60):
                starts.append((t, int(v[2]), int(v[3])))
            if not (op == 0x00F1 and len(v) > 2 and int(v[1]) in members):
                continue
            dead[int(v[1])] = bool(int(v[2]) & 0x10)
            if wipe is None and all(dead.values()):
                wipe = (t, i, dict(pos))          # where each body stood AT the wipe
            elif wipe is not None and int(v[1]) == me and not dead[me]:
                # A wipe the server raised from (the Zaishen matches end instead).
                raised += 1
                W, wi, at = wipe
                bout = {A for (ts, A, T) in starts
                        if W - 20.0 <= ts <= W and T in members and A not in members}
                orders = {}
                for (t2, d2, op2, v2) in merged[wi:i]:
                    if d2 == "s2c" and op2 in (0x0028, 0x0029, 0x002A) and len(v2) > 1 \
                            and int(v2[1]) in bout:
                        orders.setdefault(int(v2[1]), []).append((t2 - W, op2))
                athome = True
                for A in sorted(bout):
                    p, a = at.get(A), create.get(A)
                    if p is None or a is None:
                        continue
                    if math.hypot(p[0] - a[0], p[1] - a[1]) > authsrv.LEASH_HOME_RADIUS:
                        athome = False
                        away += 1
                        mine = orders.get(A, [])
                        first = min((dt for dt, op2 in mine if op2 == 0x0029), default=None)
                        if first is None or first > 3.5:
                            late.append((stamp, A, first))
                        if [1 for _dt, op2 in mine if op2 == 0x002A]:
                            chased.append((stamp, A))
                        if [1 for _dt, op2 in mine if op2 == 0x0028]:
                            halted.append((stamp, A))
                    elif orders.get(A):
                        home_moved.append((stamp, A, orders[A]))
                if bout and athome:
                    home_wipes += 1
                wipe = None
                for m in members:
                    dead[m] = False
    check(raised >= 14 and away >= 7,
          "the corpus holds the wipes the census was read from: >= 14 the server raised "
          "from, >= 7 hostiles fighting away from home at the wipe",
          f"{raised} raised wipes, {away} away hostiles")
    check(not late,
          "every one sent its first 0x0029 within 3.5 s of the last party death and "
          "before the rise -- none stood over the corpses until the countdown ran out",
          f"late or never: {late}")
    check(not chased and not halted,
          "and none sent a 0x002A (no chase of a corpse) or a 0x0028 in the window",
          f"chased {chased}, halted {halted}")
    check(home_wipes >= 7 and not home_moved,
          "a hostile that fought at its create point sent NO order through the countdown "
          "(>= 7 wipes) -- home already, it stands",
          f"{home_wipes} home wipes, moved {home_moved}")


def main():
    st = section_beat()
    section_give_up(st)
    section_home()
    section_alive()
    section_known_bad()
    section_wiring()
    section_retail()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
