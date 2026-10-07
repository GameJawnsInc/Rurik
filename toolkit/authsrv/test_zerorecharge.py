r"""test_zerorecharge -- a skill whose recharge is 0 completes with NO 0x00E5, and the
player's with no 0x00E6 either (SLICE-F52 52.8, ZERO_RECHARGE_SKIPS_E5, 2026-10-07;
studies/slice/FINDINGS.md 52.8).

WHAT IT IS REALLY CHECKING. Over every live connection, 56 of 56 completions of a
recharge-0 skill through the E5 path carry no E5 (the observer's 382 / 384 / 385 x44, the
hero's 382 / 385 x12; skill 2's three raises are E7, RESSIG's rule, and are set aside) and
291 of 291 completions with a recharge carry one. 348, ADRENAL with a recharge of 4, is
among the 291: adrenaline does not suppress the E5. What the tape does NOT separate is
"recharge 0" from "recharge 0 AND adrenal" -- every one of the 56 is adrenal, and the only
non-adrenal recharge-0 evidence is CASTAI-ZF17's single interrupt -- so the 40
non-adrenal recharge-0 rows are RECONSTRUCTION (studies/slice 52.9). This server sent
E5 [.., 0] at every such completion (and the player's E6 behind it), and E5's worker
zeroes both adrenaline halves on the client (studies/skills 26.12).
`authsrv.completion_sends_e5` is the one predicate the four completion sites read; this
file drives each site and replays the predicate over retail.

  1  THE PLAYER, through the real press and cast_tick: Sever Artery 382 and Final Thrust
     385 complete [46] .. E3 with no E5 and no E6, the entry gone; --zero-recharge-e5
     restores the old batch EXACTLY (E5 [me, skill, 0, 0] + the same batch + E6); a
     recharge-4 attack skill is byte-identical in both arms; the press is untouched.
     The non-boost resurrection site (skill 2 under --no-resurrection-single-use) the
     same.
  2  THE HERO, through ally_cast_tick: E4 at the start, the E3 at the landing with no E5,
     no E6 ever, the client's pending-record ledger closed (PENDSKILL's rule); the revert
     puts E5 [hero, skill, 0, 0] back ahead of the E3; a recharge-3 skill unchanged.
  3  THE HERO'S INTERRUPT MIRROR (RECONSTRUCTION, CASTAI-ZF17's rule on the player): no
     full-recharge E5(0) ahead of the stop; the +20 disable E5 still goes; EITHER revert
     flag restores the E5(0).
  4  NOT THIS RULE, still sent: RESSIG-B's boost repaint E5 [.., 0] ahead of each boost
     E6, and DAGGERS-B5's failed-chain second E5(0) behind a real first E5. And the one
     table-0 chain row's corner (976's shape): no first E5, the failed step's E5(0) still
     sent -- unchanged by this rule, said so.
  5  THE FLAG: ships ON, --zero-recharge-e5 parses, and main()'s own block (lifted out
     of the source and run) turns it off -- and leaves it on without the flag; the block
     is a direct statement of main(), ahead of srv.listen, so main() really reaches it.
  6  RETAIL (vault): `completion_sends_e5` over every observer and hero completion of a
     skill the world table knows agrees with the wire 100 %; the REVERT arm of the same
     predicate disagrees on every recharge-0 completion; the completions set aside for
     their E7 are skill 2's alone; 348 says adrenaline does not suppress the E5; no E6
     ever names 382 / 384 / 385. Skipped ONLY on an absent vault directory (the live
     captures, or the vault's content); a decoder that will not import is a traceback and
     a content directory without 382's row is a FAIL.

Sections 1-5 need no vault: every timing, cost and attack-ness they lean on is stubbed.
"""
import ast
import collections
import contextlib
import io
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
SCHEMA = os.path.join(PARENT, "schema")
if SCHEMA not in sys.path:
    sys.path.insert(0, SCHEMA)

import checks                                                  # noqa: E402
import content                                                 # noqa: E402
import vaultpath                                               # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
# section 6's decoders, imported HERE and not inside a try: both are in-repo and stdlib,
# so a bare machine imports them, and a load failure must be a traceback, never a skip
# (the fix pass of 2026-10-07, EV-1 / CD-1)
import livewire                                                # noqa: E402
import henchjoin                                               # noqa: E402

# Floor from the BARE-MACHINE green run of 2026-10-07 (RURIK_VAULT at an empty
# directory): 23 -- sections 1-5; section 6 declares a skip. 29 with the vault.
# The fix pass (same day) adds CD-2's main()-reaches-the-block check to section 5 and
# EV-3's raises set-aside check to section 6: 24 bare, 31 with the vault.
LEDGER = checks.Ledger("zero-recharge completions", floor=24)
check = checks.adopt(LEDGER)

E2, E3, E4, E5, E6, E7 = 0x00E2, 0x00E3, 0x00E4, 0x00E5, 0x00E6, 0x00E7
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
P = authsrv.PLAYER_AGENT_ID
FOE, HERO, DOWNED = 10, 200, 30
SEVER, FINAL_THRUST, POWER_ATTACK, RES = 382, 384 + 1, 322, 2
ZERO = (382, 384, 385)
CHOP, SAVAGE = 340, 426                     # content/world.toml: +20 disable / none


class Wire:
    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals)))

    def take(self):
        out, self.sent = self.sent, []
        return out


def _foe(pos=(50.0, 0.0)):
    return {"name": "suit", "dead": False, "died_at": 0.0, "health": 4000.0,
            "max_health": 4000.0, "last_hit": 0.0, "pos": pos, "plane": 0,
            "armor_rating": 60.0, "allegiance": agents.ALLEGIANCE_HOSTILE,
            "attack_speed": authsrv.ENEMY_ATTACK_SPEED, "effects": 0,
            "attacks_back": False, "skills": (), "skill_ready": [],
            "npc": {"profession": 1, "level": 20}}


def _hero(skills, **over):
    row = {"name": "hero", "dead": False, "died_at": 0.0, "health": 480.0,
           "max_health": 480.0, "last_hit": 0.0, "pos": (0.0, 60.0), "plane": 0,
           "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0,
           "attack_speed": authsrv.ENEMY_ATTACK_SPEED, "attacks_back": False,
           "skills": tuple(skills), "skill_ready": [0.0] * len(skills),
           "npc": {"profession": 1, "level": 20}, "party_slot": 1, "hero": 3}
    row.update(over)
    return row


@contextlib.contextmanager
def _stubs(timing=None, attack=ZERO + (POWER_ATTACK,), chain=None):
    """Pin every content read the sections lean on, so a bare machine runs the same
    cycle: the timing per skill, no cost, the named ids are attack skills the held
    weapon satisfies, and (optionally) the chain fields."""
    saved = (authsrv.skill_timing, authsrv.skill_cost, authsrv._is_attack_skill,
             authsrv.weapon_satisfies, authsrv.skill_chain_fields, authsrv.skill_target_kind,
             authsrv.ZERO_RECHARGE_SKIPS_E5, authsrv.INTERRUPT_SKIPS_ZERO_E5)
    timing = timing or {}
    _k = authsrv.skill_target_kind
    authsrv.skill_timing = lambda sid: timing.get(int(sid), (0.0, 0.0, 0.0))
    authsrv.skill_cost = lambda sid: (0, 0)
    authsrv._is_attack_skill = lambda sid: int(sid) in attack
    # an attack skill aims at a FOE (the client's byte 5): a bare machine has no row
    # to say so, and a hero's pick would aim it at whoever is hurt instead
    authsrv.skill_target_kind = lambda sid: "foe" if int(sid) in attack else _k(sid)
    authsrv.weapon_satisfies = lambda sid: True
    if chain is not None:
        authsrv.skill_chain_fields = lambda sid: chain.get(int(sid), (0, 0, 0))
    try:
        yield
    finally:
        (authsrv.skill_timing, authsrv.skill_cost, authsrv._is_attack_skill,
         authsrv.weapon_satisfies, authsrv.skill_chain_fields, authsrv.skill_target_kind,
         authsrv.ZERO_RECHARGE_SKIPS_E5, authsrv.INTERRUPT_SKIPS_ZERO_E5) = saved


def _player_cast(sid, on, st=None):
    """The real press at FOE (50 u, in reach), then the real tick past every phase.
    Returns (the press batch, the completion batch, the state). Seeded, so the two arms
    roll the same damage."""
    authsrv.ZERO_RECHARGE_SKIPS_E5 = on
    random.seed(52)
    st = st or {"agents": {FOE: _foe()}, "pos": (0.0, 0.0), "player_health": 140.0}
    w = Wire()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_skill_press([0, sid, 0, FOE], w, st, 1, authsrv.GAME_CMSG_ATTACK_SKILL)
        press = w.take()
        for cast in st.get("pending_casts", ()):
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        st["cast_busy_until"] = 0.0
        for _ in range(3):
            authsrv.cast_tick(w, st, 1)
    return press, w.take(), st


def section_player():
    print("== 1. the player: no E5 and no E6 for a recharge-0 completion ==")
    timing = {SEVER: (0.0, 0.0, 0.0), FINAL_THRUST: (0.0, 0.0, 0.0),
              POWER_ATTACK: (0.0, 0.0, 4.0)}
    with _stubs(timing):
        for sid in (SEVER, FINAL_THRUST):
            press, done, st = _player_cast(sid, True)
            ops = [op for op, _v in done]
            check(E5 not in ops and E6 not in ops and done
                  and done[0] == (INT, [agents.GV_ATTACK_SKILL_FINISHED, P, 0])
                  and done[-1] == (E3, [P, sid, 0]) and not st.get("pending_casts"),
                  f"skill {sid}'s completion: [46] .. E3 and NO E5 / E6, the entry gone -- "
                  f"retail's observer, 44 of 44 (382 x23, 384 x14, 385 x7)",
                  f"{[(hex(op), v) for op, v in done]}")
            press_r, old, st_r = _player_cast(sid, False)
            check(press_r == press and old[:1] == [(E5, [P, sid, 0, 0])]
                  and old[-1:] == [(E6, [P, sid, 0])] and old[1:-1] == done
                  and not st_r.get("pending_casts"),
                  f"KNOWN-BAD ARM --zero-recharge-e5 on {sid}: E5 [me, {sid}, 0, 0] + the SAME "
                  f"batch + E6 -- the bytes until 2026-10-07; the press identical",
                  f"{[(hex(op), v) for op, v in old]}")
        press, done, _st = _player_cast(POWER_ATTACK, True)
        press_r, old, _st_r = _player_cast(POWER_ATTACK, False)
        check(done == old and press == press_r and done[:1] == [(E5, [P, POWER_ATTACK, 0, 4])]
              and done[-1:] == [(E6, [P, POWER_ATTACK, 0])],
              "a recharge-4 attack skill: E5 [me, 322, 0, 4] .. E3 .. E6, BYTE-IDENTICAL in both "
              "arms (the flag touches no recharge > 0)", f"{[(hex(op), v) for op, v in done]}")
    # the non-boost resurrection site: skill 2 under --no-resurrection-single-use
    saved = (authsrv.RESURRECTION_SINGLE_USE, authsrv.PLAYER_RESURRECTION)
    authsrv.RESURRECTION_SINGLE_USE, authsrv.PLAYER_RESURRECTION = False, True
    try:
        with _stubs({RES: (3.0, 0.0, 0.0)}, attack=()):
            batches = []
            for on in (True, False):
                corpse = _hero(((RES, 3.0, 0.0),), dead=True, health=0.0,
                               died_at=time.time() - 3.0, pos=(0.0, 100.0))
                st = {"agents": {HERO: corpse}, "pos": (0.0, 0.0), "player_health": 140.0,
                      "player_dead": False}
                authsrv.ZERO_RECHARGE_SKIPS_E5 = on
                w = Wire()
                with contextlib.redirect_stdout(io.StringIO()):
                    authsrv.handle_skill_press([0, RES, 0, HERO], w, st, 1,
                                               authsrv.GAME_CMSG_USE_SKILL)
                    w.take()
                    for cast in st.get("pending_casts", ()):
                        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                            cast[k] -= 30.0
                    for _ in range(3):
                        authsrv.cast_tick(w, st, 1)
                batches.append((w.take(), st))
        (new, st_n), (old, st_o) = batches
        mine = lambda b: [(op, v) for op, v in b if op in (E3, E5, E6, E7) and v[:1] == [P]]  # noqa: E731
        check(mine(new) == [(E3, [P, RES, 0])] and not st_n["agents"][HERO]["dead"]
              and not st_n.get("pending_casts"),
              "the non-boost resurrection (skill 2, --no-resurrection-single-use): the raise "
              "lands, E3 and no E5 / E6 / E7 (RECONSTRUCTION, the same rule)", f"{mine(new)}")
        check(mine(old) == [(E5, [P, RES, 0, 0]), (E3, [P, RES, 0]), (E6, [P, RES, 0])]
              and not st_o["agents"][HERO]["dead"],
              "and with --zero-recharge-e5 the old E5 [me, 2, 0, 0] .. E3 .. E6", f"{mine(old)}")
    finally:
        authsrv.RESURRECTION_SINGLE_USE, authsrv.PLAYER_RESURRECTION = saved


def _ledger(sent):
    """PENDSKILL's client rule (test_pendskill): E4 adds a record for a non-observer,
    E2 / E3 drop one; a drop with none is the client's logged miss."""
    held, misses = collections.Counter(), []
    for op, v in sent:
        if op not in (E2, E3, E4) or v[0] == P:
            continue
        key = tuple(v[:3])
        if op == E4:
            held[key] += 1
        elif held[key] > 0:
            held[key] -= 1
        else:
            misses.append(key)
    return misses, +held


def _hero_cast(sid, recharge, on):
    authsrv.ZERO_RECHARGE_SKIPS_E5 = on
    random.seed(52)
    st = {"agents": {FOE: _foe((40.0, 60.0)), HERO: _hero(((sid, 0.0, recharge),))},
          "pos": (0.0, 0.0), "player_health": 140.0}
    w = Wire()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.ally_cast_tick(w, st, 1)
        start = w.take()
        row = st["agents"][HERO]
        if row.get("cast_lands_at") is not None:
            row["cast_lands_at"] = time.time() - 0.01
        authsrv.ally_cast_tick(w, st, 1)
        land = w.take()
        for k in list(row.get("hero_recharged_due") or {}):
            row["hero_recharged_due"][k] -= 60.0
        authsrv.hero_recharged_tick(w, st, 1)
    return start, land, w.take(), row


def section_hero():
    print("== 2. the hero: E4 .. E3 and no E5 for a recharge-0 cast ==")
    with _stubs():
        for sid in (SEVER, FINAL_THRUST):
            start, land, after, row = _hero_cast(sid, 0.0, True)
            first = [(op, v) for op, v in start if HERO in v[:3]][:1]
            fam = [(op, v) for op, v in land if op in (E3, E5, E6) and v[:1] == [HERO]]
            misses, held = _ledger(start + land + after)
            check(first == [(E4, [HERO, sid, 0])] and fam == [(E3, [HERO, sid, 0])]
                  and after == [] and not misses and not held
                  and not row.get("hero_recharged_due"),
                  f"hero skill {sid}: E4 at the start, the E3 alone at the landing (no E5), "
                  f"no E6 ever, the client's pending ledger closed -- retail's hero, 12 of 12 "
                  f"(382 x7, 385 x5)", f"{fam} after {after} misses {misses} open {dict(held)}")
            start_r, old, after_r, _row = _hero_cast(sid, 0.0, False)
            check(start_r == start and old[:1] == [(E5, [HERO, sid, 0, 0])] and old[1:] == land
                  and after_r == [],
                  f"KNOWN-BAD ARM --zero-recharge-e5: E5 [hero, {sid}, 0, 0] back ahead of the "
                  f"same landing; the start identical", f"{old[:3]}")
        start, land, after, _row = _hero_cast(POWER_ATTACK, 3.0, True)
        _s, land_r, after_r, _r = _hero_cast(POWER_ATTACK, 3.0, False)
        check(land[:2] == [(E5, [HERO, POWER_ATTACK, 0, 3]), (E3, [HERO, POWER_ATTACK, 0])]
              and after == [(E6, [HERO, POWER_ATTACK, 0])] and land == land_r and after == after_r,
              "a recharge-3 hero skill: E5 [hero, 322, 0, 3], E3, and its E6 -- identical in "
              "both arms", f"{land[:2]} {after}")
        # the instant batch's call (e3=False): nothing at all for recharge 0
        for on, want in ((True, []), (False, [(E5, [HERO, SEVER, 0, 0])])):
            authsrv.ZERO_RECHARGE_SKIPS_E5 = on
            w = Wire()
            row = _hero(((SEVER, 0.0, 0.0),))
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.hero_skill_messages(w, {}, HERO, row, SEVER, 0, time.time(), e3=False)
            check(w.take() == want and not row.get("hero_recharged_due"),
                  f"hero_skill_messages(e3=False), recharge 0, flag {'on' if on else 'off'}: "
                  f"{want or 'nothing'}")


def _hero_casting(sid, recharge):
    row = _hero(((sid, 0.0, recharge),), casting=0, cast_lands_at=time.time() + 5.0,
                cast_recharge=recharge, cast_target=FOE)
    return {"agents": {FOE: _foe((40.0, 60.0)), HERO: row}, "pos": (0.0, 0.0),
            "player_health": 140.0}, row


def section_interrupt():
    print("== 3. the hero's interrupt mirror (RECONSTRUCTION) ==")
    with _stubs():
        runs = {}
        for key, zero_on, int_on, by in (("default", True, True, SAVAGE),
                                         ("zero-off", False, True, SAVAGE),
                                         ("int-off", True, False, SAVAGE),
                                         ("chop", True, True, CHOP)):
            authsrv.ZERO_RECHARGE_SKIPS_E5, authsrv.INTERRUPT_SKIPS_ZERO_E5 = zero_on, int_on
            st, row = _hero_casting(SEVER, 0.0)
            w = Wire()
            with contextlib.redirect_stdout(io.StringIO()):
                res = authsrv.interrupt_body(w, st, HERO, row, 1, by, FOE)
            runs[key] = (res, w.take(), dict(row.get("hero_recharged_due") or {}))
        res, sent, due = runs["default"]
        check(res == "cast" and sent == [(INT, [agents.GV_ATTACK_SKILL_STOPPED, HERO, 0]),
                                         (E2, [HERO, SEVER, 0]),
                                         (INT, [agents.GV_INTERRUPTED, HERO, 0])]
              and not due,
              "426 on a hero mid-382: [49] E2 [35] and NO full-recharge E5(0), no E6 owed -- "
              "the player's ZF17 rule on the mirror", f"{res} {sent} due {due}")
        check(all(runs[k][1][:1] == [(E5, [HERO, SEVER, 0, 0])] and runs[k][1][1:] == sent
                  for k in ("zero-off", "int-off")),
              "EITHER revert (--zero-recharge-e5, --interrupt-zero-e5) puts E5 [hero, 382, 0, 0] "
              "back first, the rest the same", f"{runs['zero-off'][1][:2]} / {runs['int-off'][1][:2]}")
        res, chop, due = runs["chop"]
        check(chop[:3] == sent and chop[3:] == [(E5, [HERO, SEVER, 0, 20])]
              and abs(due.get(SEVER, 0.0) - (time.time() + 20.0)) < 1.0,
              "340 (+20 disable): the same three, then the disable E5 [hero, 382, 0, 20], the "
              "E6 owed at +20 -- the disable is not this rule", f"{chop} due {due}")


def section_not_this_rule():
    print("== 4. not this rule: the boost repaint and the failed chain step ==")
    with _stubs():
        authsrv.ZERO_RECHARGE_SKIPS_E5 = True
        spent = _hero(((RES, 3.0, 0.0),), boost_spent={RES}, skill_ready=[math.inf],
                      hero_recharged_due={})
        st = {"agents": {HERO: spent}, "pos": (0.0, 0.0), "player_health": 140.0,
              "boost_spent": {RES: 0}}
        w = Wire()
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.recharge_party_skills(w, st, 1, "the test's boost")
        got = [(op, v) for op, v in w.take() if op in (E5, E6)]
        check(got == [(E5, [P, RES, 0, 0]), (E6, [P, RES, 0]),
                      (E5, [HERO, RES, 0, 0]), (E6, [HERO, RES, 0])],
              "RESSIG-B's boost repaint still rides an E5 [.., 0] ahead of each E6, the player's "
              "and the hero's (the slot WAS spent; the E5 is the UI's repaint)", f"{got}")
    lead_req = (authsrv.chain.OFF_HAND, 0x02, 0)        # an off-hand that must follow a lead
    for sid, recharge, want_first in ((780, 3.0, True), (976, 0.0, False)):
        with _stubs({sid: (0.0, 0.0, recharge)}, attack=(sid,), chain={sid: lead_req}):
            _p, done, _st = _player_cast(sid, True)
        e5s = [v for op, v in done if op == E5]
        fail = [v for op, v in done if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                and v[0] == agents.GV_ATTACK_FAIL]
        want = ([[P, sid, 0, int(recharge)]] if want_first else []) + [[P, sid, 0, 0]]
        check(e5s == want and len(fail) == 1 and E6 not in [op for op, _v in done],
              (f"DAGGERS-B5's failed chain step on {sid} (recharge 3): E5 [me, {sid}, 0, 3], the "
               f"fail word, the SECOND E5 [.., 0] -- retail's, unchanged"
               if want_first else
               f"the corner, 976's shape (a table-0 chain row): no first E5, the failed step's "
               f"E5 [me, {sid}, 0, 0] still sent -- unchanged by this rule, unwitnessed"),
              f"E5s {e5s} fail {fail}")


def section_flag():
    print("== 5. the flag ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check(src.count("\nZERO_RECHARGE_SKIPS_E5 = True\n") == 1 and authsrv.ZERO_RECHARGE_SKIPS_E5
          and '"--zero-recharge-e5"' in args,
          "ZERO_RECHARGE_SKIPS_E5 ships ON, and --zero-recharge-e5 is registered")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    # main()'s own `if a.zero_recharge_e5:` block, lifted out of the source and run
    # against the module's globals -- the `global` inside it is what makes the flip
    # real; a block that parsed and never rebound the name would leave it True.
    tree = ast.parse(src)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    block = next((n for n in ast.walk(main) if isinstance(n, ast.If)
                  and isinstance(n.test, ast.Attribute) and n.test.attr == "zero_recharge_e5"),
                 None)
    if block is None:
        check(False, "main() carries an `if a.zero_recharge_e5:` block")
        return
    # ...and main() REACHES it before the first connection: a block nested under another
    # test, or one placed after the listener, would still flip below and change nothing a
    # client sees (the fix pass of 2026-10-07, CD-2; test_labelconsumers §5's
    # `i_main < bind < i_listen`, as an AST walk)
    listen = next((n for n in ast.walk(main) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute) and n.func.attr == "listen"
                   and isinstance(n.func.value, ast.Name) and n.func.value.id == "srv"), None)
    check(block in main.body and listen is not None and block.lineno < listen.lineno,
          "main() reaches the block: a DIRECT statement of main() (nested under nothing), "
          "ahead of srv.listen -- the flag is set before the first connection",
          f"direct={block in main.body}, block line {block.lineno}, "
          f"srv.listen line {getattr(listen, 'lineno', None)}")
    fn = ast.Module(body=[ast.FunctionDef(
        name="_flip", args=ast.arguments(posonlyargs=[], args=[ast.arg("a")], vararg=None,
                                         kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
        body=[block], decorator_list=[], returns=None, type_params=[])], type_ignores=[])
    ast.fix_missing_locations(fn)
    ns = {}
    exec(compile(fn, authsrv.__file__, "exec"), authsrv.__dict__, ns)   # noqa: S102
    saved = authsrv.ZERO_RECHARGE_SKIPS_E5
    try:
        results = []
        for argv in ([], ["--zero-recharge-e5"]):
            authsrv.ZERO_RECHARGE_SKIPS_E5 = True
            a = ap.parse_args(argv)
            with contextlib.redirect_stdout(io.StringIO()):
                ns["_flip"](a)
            results.append((a.zero_recharge_e5, authsrv.ZERO_RECHARGE_SKIPS_E5))
        check(results == [(False, True), (True, False)],
              "main()'s block, run: no flag leaves ZERO_RECHARGE_SKIPS_E5 ON; --zero-recharge-e5 "
              "parses and turns it OFF", f"{results}")
    finally:
        authsrv.ZERO_RECHARGE_SKIPS_E5 = saved
    check(all(name in src for name in ("if completion_sends_e5(cast[\"recharge\"]):",
                                       "zero = not boost and not completion_sends_e5(",
                                       "    if completion_sends_e5(recharge):\n",
                                       "completion_sends_e5(recharge) or not INTERRUPT_SKIPS_ZERO_E5")),
          "all four completion sites read the one predicate (cast_tick, the resurrection's, "
          "hero_skill_messages, the hero's interrupt mirror)")


def _completions(merged):
    """(t, agent, skill, e5 recharge or None, e7 seen) per 0x00E3 completion: the E5 is the
    same agent's and skill's, back to the cast's own E4 (<= 8 s) or 0.3 s ahead; the E7 the
    same agent's and skill's within 0.3 s of the E3 (a raise's E7 shares its stamp)."""
    s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
    out = []
    for i, (t, op, v) in enumerate(s2c):
        if op != E3 or len(v) < 3:
            continue
        ag, sk = int(v[1]), int(v[2])
        e5 = None
        for j in range(i - 1, -1, -1):
            tj, oj, vj = s2c[j]
            if t - tj > 8.0 or (oj == E4 and int(vj[1]) == ag and int(vj[2]) == sk):
                break
            if oj == E5 and len(vj) > 4 and int(vj[1]) == ag and int(vj[2]) == sk:
                e5 = int(vj[4])
                break
        if e5 is None:
            for tj, oj, vj in s2c[i + 1:]:
                if tj - t > 0.3:
                    break
                if oj == E5 and len(vj) > 4 and int(vj[1]) == ag and int(vj[2]) == sk:
                    e5 = int(vj[4])
                    break
        e7 = any(oj == E7 and abs(tj - t) <= 0.3 and len(vj) > 2 and int(vj[1]) == ag
                 and int(vj[2]) == sk for tj, oj, vj in s2c[max(0, i - 40):i + 40])
        out.append((t, ag, sk, e5, e7))
    return out


def section_retail():
    print("== 6. retail: the predicate against every completion on the live corpus ==")
    # Skips on an absent vault DIRECTORY and on nothing else (the fix pass of 2026-10-07,
    # EV-1 / CD-1: this section used to turn ANY exception -- a decoder that would not
    # import, a table that would not load -- into a declared skip, and floor 23 could not
    # notice six checks vanishing). The decoders are imported at the top; a content
    # directory that is THERE but lacks 382's row is a FAIL, not a skip.
    root = livewire.captures_root()
    if not os.path.isdir(root):
        LEDGER.skip("section 6 (retail)", f"no live captures on this machine ({root}) -- 7 checks")
        return
    cdir = vaultpath.vault_path("content")
    if not os.path.isdir(cdir):
        LEDGER.skip("section 6 (retail)", f"the vault's content directory is absent ({cdir}): "
                    "the table recharge is the key -- 7 checks")
        return
    try:
        agents.WORLD.get("skills", str(SEVER))
    except content.ContentError as exc:
        check(False, "the vault's content directory is present, so the world's skills table "
              "carries 382's row", f"{exc}"[:200])
        return

    def table(sid):
        # a skill the table does not know is not classed (and is counted, below); only the
        # table's own "no such row" is caught
        try:
            row = agents.WORLD.get("skills", str(sid))
        except content.ContentError:
            return None, None
        return float(row["recharge"]), int(row.get("adrenaline_units") or 0) > 0

    saved = authsrv.ZERO_RECHARGE_SKIPS_E5
    agree = collections.Counter()
    wrong_new, wrong_old, sep, e6_zero, conns = [], [], collections.Counter(), [], 0
    raised, unknown, nonadren_zero = collections.Counter(), collections.Counter(), []
    try:
        for capdir, gf in livewire.live_connections():
            _c, merged, _ok = livewire.decode_conn(capdir, gf)
            if not merged:
                continue
            conns += 1
            me = henchjoin.whose_agent(merged)
            heroes = {int(v[3]) for _t, d, op, v in merged
                      if d == "s2c" and op == 0x01C2 and len(v) > 3}
            for t, ag, sk, e5, e7 in _completions(merged):
                who = "observer" if ag == me else ("hero" if ag in heroes else "other")
                tr, adren = table(sk)
                if tr is None:
                    unknown[sk] += 1
                    continue
                if e7:
                    # a raise: E7 (indefinite) and E3, RESSIG's boost path -- the server
                    # never consults completion_sends_e5 for it under the defaults, so it is
                    # not this rule's evidence either way (EV-3); which skills these are is
                    # checked below, so the set-aside cannot swallow a witness unseen
                    raised[sk] += 1
                    continue
                sent = e5 is not None
                if tr == 0 and not adren:
                    nonadren_zero.append((os.path.basename(capdir), round(t, 3), ag, sk, e5))
                authsrv.ZERO_RECHARGE_SKIPS_E5 = True
                ours = authsrv.completion_sends_e5(tr)
                authsrv.ZERO_RECHARGE_SKIPS_E5 = False
                old = authsrv.completion_sends_e5(tr)
                agree[(who, "recharge" if tr > 0 else "zero", sent)] += 1
                where = (os.path.basename(capdir), round(t, 3), ag, sk, e5)
                if ours != sent:
                    wrong_new.append(where)
                if old != sent:
                    wrong_old.append(where)
                if adren and tr > 0:
                    sep[sent] += 1
            for _t, d, op, v in merged:
                if d == "s2c" and op == E6 and len(v) > 2 and int(v[2]) in ZERO:
                    e6_zero.append((os.path.basename(capdir), int(v[1]), int(v[2])))
    finally:
        authsrv.ZERO_RECHARGE_SKIPS_E5 = saved
    zero = sum(n for (w, z, s), n in agree.items() if z == "zero")
    rech = sum(n for (w, z, s), n in agree.items() if z == "recharge")
    print(f"  census: {conns} connections; {dict(sorted(agree.items()))}")
    print(f"  set aside: raises (E7) {dict(raised)}; skills the table does not know "
          f"{sum(unknown.values())} completions {dict(unknown)}")
    # informational, NOT a check (a count that reddens on good news is not one): a
    # non-adrenal recharge-0 completion through the E5 path is the witness the tape lacks
    # -- 0 on 2026-10-07, which is why those 40 table rows are RECONSTRUCTION (52.9)
    print(f"  non-adrenal recharge-0 completions outside the raises: {len(nonadren_zero)} "
          f"{nonadren_zero[:4]}")
    check(conns >= 120 and zero >= 56 and rech >= 291,
          "the corpus is the one the lane measured (>= 120 connections, >= 56 recharge-0 and "
          ">= 291 recharge completions outside the raises; floors, not equalities)",
          f"{conns} connections, {zero} recharge-0, {rech} with a recharge")
    check(set(raised) == {RES} and raised[RES] >= 3,
          "the completions set aside for their E7 are skill 2's raises and no other skill's "
          "(>= 3): RESSIG's boost path, not this rule's evidence -- so the set-aside cannot "
          "swallow a witness unseen", f"{dict(raised)}")
    check(not wrong_new,
          "completion_sends_e5 (the shipped arm) agrees with the wire on EVERY completion: an "
          "E5 exactly when the table recharge is > 0", f"{wrong_new[:6]}")
    check(len(wrong_old) == zero and all(w[4] is None for w in wrong_old),
          "KNOWN-BAD ARM: the same predicate with --zero-recharge-e5 is wrong on EVERY "
          "recharge-0 completion and on nothing else", f"{len(wrong_old)} of {zero}")
    check(sum(n for (w, z, s), n in agree.items() if z == "zero" and w == "observer") >= 44
          and sum(n for (w, z, s), n in agree.items() if z == "zero" and w == "hero") >= 12,
          "both caster kinds witness it: the observer's recharge-0 completions (>= 44) and the "
          "hero's (>= 12)", f"{dict(agree)}")
    check(sep.get(True, 0) >= 8 and not sep.get(False, 0),
          "an ADRENAL skill with a table recharge (348's 4 s) carries its E5 every time: "
          "adrenaline does not suppress the E5. (It does not separate 'recharge 0' from "
          "'recharge 0 and adrenal': every recharge-0 witness is adrenal -- 52.9)",
          f"{dict(sep)}")
    check(not e6_zero,
          "no 0x00E6 names 382 / 384 / 385 anywhere on the corpus", f"{e6_zero[:5]}")


def main():
    section_player()
    section_hero()
    section_interrupt()
    section_not_this_rule()
    section_flag()
    section_retail()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
