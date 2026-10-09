r"""test_pendskill -- a hero's cast opens the client's pending record with 0x00E4, and
every way it ends closes that record exactly once (PENDSKILL, 2026-09-30; PLAN-LOG
"PENDSKILL").

WHAT IT IS REALLY CHECKING. The client keeps a ledger of casts in flight. OBSERVED
from the slice client's bytes (build 38797): the receive table's entries are
[descriptor, field count, handler]. E2 and E3 share 0x0091F650 -> 0x00823090, which
drops one reference from the record keyed (skill << 16) | copy and logs 'Pending skill
%u copy %d not found' when there is none. E4 goes to 0x0091F670 -> 0x008148F0, which
ADDS one for any agent but the observer; the observer's own press adds its record
client-side. JARIN sent a hero's E5 and E3 and never retail's E4, so every hero E3
missed (495 of 495 on the harness since 2026-09-14). This file replays what the
server sends through THAT rule and counts the misses and the records left open. The
rule is a model of the client, so it is checked against retail first (section 6): a
model that retail's own stream breaks proves nothing about ours.

  1  a hero's spell (Resurrection Signet, 2, at a dead body): the E4 [hero, 2, 0] is
     the first message naming the hero at the start; the landing sends E5 then E3;
     the ledger closes with 0 misses and 0 open.
  2  the drops, each closing once: a knock-down mid-cast ([59] then E2), a death
     mid-cast (the status, [59], E2 ahead of the 0x00D0, the flags byte last --
     retail's 609.252 order), an interrupt (its E2, now counted), a transition (the
     net's E2); a second cast after each opens and closes cleanly -- its E3 at the
     aftercast's end since SKILLS-AC8 (2026-10-09). (f)-(h), SKILLS-AC8: a spell's E3
     is QUEUED for the aftercast's end (HERO_E3_AFTERCAST), so the record stays open
     across it: a DEATH in the window closes it with [57, hero, 0] + E2 and never sends
     the E3 (the observer's CONFPASS-F1b shape, RECONSTRUCTION for a hero), and
     --no-hero-e3-aftercast's death finds nothing to close; a KNOCK-DOWN or an
     INTERRUPT in the window sends nothing and the E3 still closes it on time; a
     TRANSITION's net sends the E2 alone. Orison's 0.75 is stubbed from the vault's own
     row (orison_aftercast) so a bare machine takes the same path.
  3  a HENCHMAN (no hero index): no E4, no E-family at all -- 0 of 532 retail
     henchman casts carry any.
  4  the KNOWN-BAD arm (--no-hero-cast-e4): no E4, so the landing's E3 is a MISS on
     the model -- this is the red this file exists for -- and a death mid-cast sends
     no [59] and no E2.
  5  the switch's wiring: the default, the flag, main()'s handling.
  6  the model against RETAIL: over every live connection, the observer's press and
     another agent's E4 add, E2 / E3 drop -- 0 misses, and the party bodies' E4s
     equal their closes (50 = 48 E3 + 2 E2 on 20260914T005758). Skipped without the
     captures.
  7  the model against the BINARY: the table rows for E1..E5 in the slice client,
     E2 and E3 on one handler, E4 on another, and the log string pushed where the
     comment says. Skipped without the vault's client.
"""
import collections
import os
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
import vaultpath                                               # noqa: E402

# Floor from the BARE-MACHINE green run of 2026-09-30 (RURIK_VAULT at an empty
# directory): 19 -- sections 1-5; 6 (the captures) and 7 (the slice client) each
# declare a skip. 26 with the vault. With HERO_CAST_OPENS_E4 = False in the source,
# 11 of them go red (the pre-fix tree's shape, 2026-09-30).
# 2026-10-09, SKILLS-AC8: + 6, section 2 (f)-(h), the record across the hero's
# aftercast = 25 bare (MEASURED with RURIK_VAULT at an empty directory and at a
# nonexistent path), 32 with the vault (MEASURED). Two mutants go red: the aftercast
# drop made a no-op (3 checks) and a death that sends the queued E3 instead (1).
LEDGER = checks.Ledger("pending skill", floor=25)
check = checks.adopt(LEDGER)

E2, E3, E4, E5 = 0x00E2, 0x00E3, 0x00E4, 0x00E5
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
STATUS = authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
FLAGS = authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS
CLEAR = authsrv.AGENT_ADRENALINE_CLEAR
P = authsrv.PLAYER_AGENT_ID
HERO, DOWNED, FOE = 200, 30, 10
RES_SIGNET, ORISON = 2, 281


def client_ledger(sent, observer=P):
    """The client's rule, for everyone but the observer (whose record its own press
    adds): E4 adds a reference, E2 and E3 drop one, and a drop with none is the
    logged line. Returns (misses, still_open)."""
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


def _world(hero_index=3):
    """The player at the origin, a DEAD party body at 110 u, and a caster whose bar
    is Orison of Healing then Resurrection Signet -- the dead first (SLICE-H3)."""
    downed = _body("downed", (0.0, 110.0), 0, dead=True, health=0.0, died_at=time.time())
    caster = _body("caster", (0.0, 60.0), 1, hero=hero_index,
                   skills=((ORISON, 1.0, 2.0), (RES_SIGNET, 3.0, 0.0)),
                   skill_ready=[0.0, 0.0])
    return {"agents": {DOWNED: downed, HERO: caster}, "pos": (0.0, 0.0),
            "player_health": 50.0}


class Wire:
    """A send() that records (op, values) in order."""

    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals)))

    def take(self):
        out, self.sent = self.sent, []
        return out


def _start(st, wire):
    authsrv.ally_cast_tick(wire, st, 1)
    return wire.take()


def _land(st, wire):
    st["agents"][HERO]["cast_lands_at"] = time.time() - 0.01
    authsrv.ally_cast_tick(wire, st, 1)
    return wire.take()


def _naming(sent, aid):
    return [(op, v) for op, v in sent if aid in v[:3]]


class orison_aftercast:
    """SKILLS-AC8: Orison of Healing's table aftercast, 0.75 s -- the vault's own row
    (281 at build 38974, test_npcaftercast's RECORD) -- for the block on EITHER machine:
    a bare one reads a rowless 281 as 0 and would queue no E3, so a check about the
    aftercast window would pass by having no window. Only 281's middle column is
    stubbed; every other skill reads the real skill_timing."""

    def __enter__(self):
        self.real = authsrv.skill_timing
        real = self.real
        authsrv.skill_timing = (lambda sid, *a, **k: (1.0, 0.75, 2.0) if int(sid) == ORISON
                                else real(sid, *a, **k))
        return self

    def __exit__(self, *exc):
        authsrv.skill_timing = self.real
        return False


def _release(st, wire):
    """SKILLS-AC8: the hero's queued E3s fall due (their aftercast run out) and the tick
    sends them. Returns what went out."""
    row = st["agents"][HERO]
    row["hero_e3_due"] = [(time.time() - 0.01, sid) for _at, sid in row.get("hero_e3_due", ())]
    authsrv.ally_cast_tick(wire, st, 1)
    return wire.take()


def section_spell():
    print("== 1. a hero's Resurrection Signet: E4 at the start, E5 + E3 at the landing ==")
    st, wire = _world(), Wire()
    start = _start(st, wire)
    mine = _naming(start, HERO)
    check(st["agents"][HERO].get("casting") == 1 and mine
          and mine[0] == (E4, [HERO, RES_SIGNET, 0]),
          "the start's first message naming the hero is 0x00E4 [hero, 2, 0] -- retail "
          "opens every hero cast with it, first in the segment (50 of 50)",
          f"{mine[:4]}")
    ops = [op for op, _v in start]
    check(E4 in ops and INT_T in ops and ops.index(E4) < ops.index(INT_T)
          and any(op == INT_T and v[:2] == [60, HERO] for op, v in start),
          "and the E4 is ahead of the cast's [60] announce", f"{start}")
    land = _land(st, wire)
    ops = [op for op, v in land if v[:1] == [HERO]]
    # RESSIG (2026-09-30): a completed Resurrection Signet closes with E7 (the
    # indefinite recharge) then E3, retail's 3 of 3 -- every other spell keeps
    # JARIN's E5 then E3. Either way the E3 is what closes the E4's record.
    check(ops[:2] == ([0x00E7, E3] if authsrv.RESURRECTION_SINGLE_USE else [E5, E3]),
          "the landing sends E7 then E3 on the hero (RESSIG; E5 then E3 under "
          "--no-resurrection-single-use)", f"{land[:4]}")
    misses, held = client_ledger(start + land)
    check(misses == [] and not held,
          "the client's ledger over start + landing: 0 misses, 0 records left open",
          f"misses {misses}, open {dict(held)}")
    check(not st["agents"][HERO].get("hero_e4_open"),
          "and the row's own count is back to nothing", f"{st['agents'][HERO].get('hero_e4_open')}")


def _cast_orison(st, wire):
    """Start Orison of Healing on the hurt player (nobody dead to raise)."""
    st["agents"][DOWNED]["dead"] = False
    st["agents"][DOWNED]["health"] = 100.0
    st["agents"][HERO]["skill_ready"] = [0.0, 0.0]
    st["agents"][HERO]["casting"] = None
    st["agents"][HERO]["cast_lands_at"] = None
    return _start(st, wire)


def section_drops():
    print("== 2. every drop closes the record once ==")
    # (a) a knock-down mid-cast
    st, wire = _world(), Wire()
    start = _cast_orison(st, wire)
    check(_naming(start, HERO)[:1] == [(E4, [HERO, ORISON, 0])],
          "Orison opens with its E4", f"{_naming(start, HERO)[:3]}")
    authsrv.knock_down(wire, st, HERO, 1, "the test's knock-down", 2.0)
    kd = wire.take()
    stop = [i for i, (op, v) in enumerate(kd) if op == INT and v[:2] == [59, HERO]]
    e2 = [i for i, (op, v) in enumerate(kd) if op == E2 and v == [HERO, ORISON, 0]]
    check(len(stop) == 1 and len(e2) == 1 and stop[0] < e2[0],
          "a KNOCK-DOWN mid-cast: [59, hero, 0] then E2 [hero, 281, 0] -- the player's "
          "release, RECONSTRUCTION", f"{kd}")
    misses, held = client_ledger(start + kd)
    check(misses == [] and not held and st["agents"][HERO].get("casting") is None,
          "and the ledger closes: 0 misses, 0 open, the cast cleared",
          f"misses {misses}, open {dict(held)}")

    # (b) a death mid-cast -- the order of 609.252
    st, wire = _world(), Wire()
    start = _cast_orison(st, wire)
    row = st["agents"][HERO]
    row["health"] = 0.0
    authsrv.kill_agent(wire, st, HERO, row, 1, time.time(), reward=False)
    death = wire.take()
    i_status = next((i for i, (op, v) in enumerate(death) if op == STATUS and v[0] == HERO), None)
    i_stop = next((i for i, (op, v) in enumerate(death) if op == INT and v[:2] == [59, HERO]), None)
    i_e2 = next((i for i, (op, v) in enumerate(death) if op == E2 and v == [HERO, ORISON, 0]), None)
    i_clear = next((i for i, (op, v) in enumerate(death) if op == CLEAR and v[:1] == [HERO]), None)
    i_flags = next((i for i, (op, v) in enumerate(death) if op == FLAGS and v[:1] == [HERO]), None)
    check(None not in (i_status, i_stop, i_e2, i_flags)
          and i_status < i_stop < i_e2 < i_flags
          and (i_clear is None or i_e2 < i_clear),
          "a DEATH mid-cast: the status, [59, hero, 0], E2 [hero, 281, 0] (ahead of "
          "any 0x00D0), the flags byte last -- retail's 609.252 segment, OBSERVED 1 of 1",
          f"status {i_status} stop {i_stop} E2 {i_e2} clear {i_clear} flags {i_flags}: "
          f"{death}")
    misses, held = client_ledger(start + death)
    check(misses == [] and not held and row.get("casting") is None,
          "and the ledger closes: 0 misses, 0 open, the cast cleared",
          f"misses {misses}, open {dict(held)}")
    authsrv.ally_cast_tick(wire, st, 1)
    after = wire.take()
    check(not [1 for op, v in after if op in (E2, E3)],
          "the corpse's next tick sends no second close (the net finds nothing open)",
          f"{after}")

    # (c) an interrupt: its E2 was already sent; now it is counted
    st, wire = _world(), Wire()
    start = _cast_orison(st, wire)
    got = authsrv.interrupt_body(wire, st, HERO, st["agents"][HERO], 1, 57, FOE,
                                 mode="action")
    intr = wire.take()
    misses, held = client_ledger(start + intr)
    check(got == "cast" and [op for op, v in intr].count(E2) == 1 and misses == []
          and not held and not st["agents"][HERO].get("hero_e4_open"),
          "an INTERRUPT mid-cast: its one E2 closes the record -- 0 misses, 0 open, "
          "the row's count cleared", f"{got} {intr} misses {misses} open {dict(held)}")

    # (d) a transition: the net closes it
    st, wire = _world(), Wire()
    start = _cast_orison(st, wire)
    st["agents"][HERO]["effects"] |= agents.EFFECT_TRANSITION
    authsrv.ally_cast_tick(wire, st, 1)
    tr = wire.take()
    misses, held = client_ledger(start + tr)
    check(tr.count((E2, [HERO, ORISON, 0])) == 1 and misses == [] and not held,
          "a TRANSITION mid-cast: the tick's drop sends the E2 -- 0 misses, 0 open",
          f"{tr} misses {misses} open {dict(held)}")

    # (e) the next cast after a drop opens and closes cleanly. RE-AIMED 2026-10-09
    # (SKILLS-AC8): Orison's E3 is no longer in its landing's tick but at the aftercast's
    # end, so the record closes on the release (_release), not on the landing.
    st["agents"][HERO]["effects"] &= ~agents.EFFECT_TRANSITION
    with orison_aftercast():
        again = _cast_orison(st, wire) + _land(st, wire)
        open_at_land = client_ledger(start + tr + again)[1]
        again += _release(st, wire)
    misses, held = client_ledger(start + tr + again)
    check(misses == [] and not held and again.count((E4, [HERO, ORISON, 0])) == 1
          and again.count((E3, [HERO, ORISON, 0])) == 1
          and dict(open_at_land) == {(HERO, ORISON, 0): 1},
          "and the next cast after it opens with its own E4 and closes: 0 misses, 0 open "
          "-- its record open across the aftercast and closed by the E3 at its end "
          "(SKILLS-AC8)",
          f"misses {misses}, open {dict(held)}; open at the landing {dict(open_at_land)}")
    section_aftercast_drops()


def _orison_landed(hero_e3=True):
    """A fresh world whose hero has just COMPLETED Orison: E4 at the start, E5 at the
    landing, the E3 queued for the aftercast's end (or, hero_e3=False, the pre-AC8
    landing). Returns (state, wire, start + landing)."""
    st, wire = _world(), Wire()
    saved = authsrv.HERO_E3_AFTERCAST
    authsrv.HERO_E3_AFTERCAST = hero_e3
    try:
        sent = _cast_orison(st, wire) + _land(st, wire)
    finally:
        authsrv.HERO_E3_AFTERCAST = saved
    return st, wire, sent


def section_aftercast_drops():
    print("== 2. (f)-(h) the record across the AFTERCAST (SKILLS-AC8) ==")
    with orison_aftercast():
        # (f) a DEATH in the aftercast: the observer's CONFPASS-F1b shape, [57] + E2
        st, wire, sent = _orison_landed()
        row = st["agents"][HERO]
        queued = [sid for _at, sid in row.get("hero_e3_due", ())]
        check(queued == [ORISON] and (E5, [HERO, ORISON, 0, 2]) in sent
              and (E3, [HERO, ORISON, 0]) not in sent,
              "Orison's landing sends its E5 and QUEUES its E3 for the aftercast's end "
              "(retail's Koss: E3 at E5 + 0.732-0.762, 19 of 19)",
              f"queued {queued}; landing {_naming(sent, HERO)}")
        row["health"] = 0.0
        authsrv.kill_agent(wire, st, HERO, row, 1, time.time(), reward=False)
        death = wire.take()
        i_status = next((i for i, (op, v) in enumerate(death) if op == STATUS and v[0] == HERO), None)
        i_57 = next((i for i, (op, v) in enumerate(death) if op == INT and v == [57, HERO, 0]), None)
        i_e2 = next((i for i, (op, v) in enumerate(death) if op == E2 and v == [HERO, ORISON, 0]), None)
        i_flags = next((i for i, (op, v) in enumerate(death) if op == FLAGS and v[:1] == [HERO]), None)
        check(None not in (i_status, i_57, i_e2, i_flags)
              and i_status < i_57 < i_e2 < i_flags and i_e2 == i_57 + 1
              and not [1 for op, v in death if op == E3 or (op == INT and v[:2] == [59, HERO])],
              "a DEATH in the aftercast: the status, [57, hero, 0], E2 [hero, 281, 0] "
              "directly behind it, the flags byte last -- and no E3, no [59] (the cast is "
              "done). The observer's shape, CONFPASS-F1b (n = 1); RECONSTRUCTION for a hero",
              f"status {i_status} [57] {i_57} E2 {i_e2} flags {i_flags}: {death}")
        later = _release(st, wire)
        misses, held = client_ledger(sent + death + later)
        check(not row.get("hero_e3_due") and not [1 for op, v in later if op in (E2, E3)]
              and misses == [] and not held,
              "  and the corpse never sends the E3 when its aftercast would have ended, nor "
              "a second E2: the ledger closes, 0 misses, 0 open",
              f"after {later}; misses {misses}, open {dict(held)}")
        # the pre-AC8 arm: the E3 went out at the landing, so the death finds nothing
        st, wire, sent = _orison_landed(hero_e3=False)
        row = st["agents"][HERO]
        row["health"] = 0.0
        authsrv.kill_agent(wire, st, HERO, row, 1, time.time(), reward=False)
        death = wire.take()
        check((E3, [HERO, ORISON, 0]) in sent
              and not [1 for op, v in death if op in (E2, E3) or (op == INT and v[:2] == [57, HERO])],
              "  KNOWN-BAD arm, --no-hero-e3-aftercast: the E3 rode the landing, so a death "
              "0.75 s later has no record to close -- no [57], no E2 (the pre-AC8 segment)",
              f"landing {_naming(sent, HERO)}; death {death}")

        # (g) a KNOCK-DOWN and an INTERRUPT in the aftercast touch nothing: the skill is
        # done, and the E3 still closes the record at the aftercast's end
        st, wire, sent = _orison_landed()
        authsrv.knock_down(wire, st, HERO, 1, "the test's knock-down", 2.0)
        got = authsrv.interrupt_body(wire, st, HERO, st["agents"][HERO], 1, 57, FOE,
                                     mode="action")
        kd = wire.take()
        rel = _release(st, wire)
        misses, held = client_ledger(sent + kd + rel)
        check(got is None and not [1 for op, v in kd if op in (E2, E3)
                                   or (op == INT and v[:2] in ([59, HERO], [57, HERO]))]
              and rel.count((E3, [HERO, ORISON, 0])) == 1
              and authsrv.knocked_down(st, HERO, time.time())
              and misses == [] and not held,
              "a KNOCK-DOWN and an INTERRUPT in the aftercast send no stop word and no E2 "
              "(nothing is in flight), and the E3 still goes at the aftercast's end -- "
              "while the hero is down -- closing the record: 0 misses, 0 open "
              "(RECONSTRUCTION, the player's rule: _mark_cancelled spares a cast past its E5)",
              f"interrupt {got}; kd {kd}; release {rel}; misses {misses}, open {dict(held)}")

        # (h) a TRANSITION in the aftercast: the net's E2, no [57]
        st, wire, sent = _orison_landed()
        st["agents"][HERO]["effects"] |= agents.EFFECT_TRANSITION
        authsrv.ally_cast_tick(wire, st, 1)
        tr = wire.take()
        later = _release(st, wire)
        misses, held = client_ledger(sent + tr + later)
        check(tr.count((E2, [HERO, ORISON, 0])) == 1
              and not [1 for op, v in tr + later if op == E3 or (op == INT and v[:2] == [57, HERO])]
              and misses == [] and not held,
              "a TRANSITION in the aftercast: the tick's net sends the E2 alone and the E3 "
              "never follows -- 0 misses, 0 open (RECONSTRUCTION, the mid-cast net's form)",
              f"{tr} then {later}; misses {misses}, open {dict(held)}")


def section_henchman():
    print("== 3. a henchman: no E4, no family ==")
    st, wire = _world(hero_index=None), Wire()
    sent = _start(st, wire) + _land(st, wire)
    fam = [(op, v) for op, v in sent if op in (E2, E3, E4, E5)]
    check(st["agents"][HERO].get("casting") is None and fam == []
          and any(op == INT_T and v[:2] == [60, HERO] for op, v in sent),
          "a henchman casts (its [60]) with no E4 / E5 / E3 -- 0 of 532 on retail",
          f"{fam}")


def section_known_bad():
    print("== 4. the known-bad arm: --no-hero-cast-e4 ==")
    saved = authsrv.HERO_CAST_OPENS_E4
    authsrv.HERO_CAST_OPENS_E4 = False
    try:
        st, wire = _world(), Wire()
        sent = _start(st, wire) + _land(st, wire)
        misses, held = client_ledger(sent)
        check(not [1 for op, _v in sent if op == E4]
              and misses == [(HERO, RES_SIGNET, 0)] and not held,
              "no E4, so the landing's E3 [hero, 2, 0] is a MISS on the client's ledger "
              "-- 'Pending skill 2 copy 0 not found', the party run's 69 of 69",
              f"misses {misses}")
        st, wire = _world(), Wire()
        _cast_orison(st, wire)
        row = st["agents"][HERO]
        row["health"] = 0.0
        authsrv.kill_agent(wire, st, HERO, row, 1, time.time(), reward=False)
        death = wire.take()
        check(not [1 for op, v in death if op == E2 or (op == INT and v[:2] == [59, HERO])],
              "and a death mid-cast sends no [59] and no E2 (the pre-fix segment)",
              f"{death}")
    finally:
        authsrv.HERO_CAST_OPENS_E4 = saved


def section_wiring():
    print("== 5. the switch ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check(authsrv.HERO_CAST_OPENS_E4 is True
          and "HERO_CAST_OPENS_E4 = True      # False (--no-hero-cast-e4)" in src,
          "HERO_CAST_OPENS_E4 ships ON", "")
    check('"--no-hero-cast-e4"' in args and "if a.no_hero_cast_e4:" in src
          and "HERO_CAST_OPENS_E4 = False" in src,
          "--no-hero-cast-e4 is parsed and main() flips the switch", "")


def section_retail():
    print("== 6. the model against retail: 0 misses over the live corpus ==")
    try:
        import livewire
        import henchjoin
        root = livewire.captures_root()
    except Exception as exc:                                    # pragma: no cover
        LEDGER.skip("the retail ledger", f"livewire unavailable: {exc}")
        return
    if not root or not os.path.isdir(root):
        LEDGER.skip("the retail ledger", "no live captures on this machine")
        return
    misses = collections.Counter()
    opened = closed = presses = conns = 0
    for capdir, _who in livewire.live_captures():
        for cf in livewire.connections(capdir):
            c, merged, _ok = livewire.decode_conn(capdir, cf)
            if c is None or not merged:
                continue
            me = henchjoin.whose_agent(merged)
            if me is None:
                continue
            conns += 1
            held = collections.Counter()
            for _t, d, op, v in merged:
                if d == "c2s" and op in (0x0046, 0x0027) and len(v) > 1:
                    held[(me, int(v[1]))] += 1
                    presses += 1
                    continue
                if d != "s2c" or op not in (E2, E3, E4) or len(v) < 4:
                    continue
                a, sk, cp = int(v[1]), int(v[2]), int(v[3])
                key = (a, sk) if a == me else (a, sk, cp)
                if op == E4:
                    if a != me:
                        held[key] += 1
                        opened += 1
                    continue
                if a != me:
                    closed += 1
                if held[key] > 0:
                    held[key] -= 1
                else:
                    misses[("observer" if a == me else "other", op)] += 1
    check(conns >= 100 and presses >= 400,
          "the corpus is the one the census read (>= 100 connections, >= 400 presses)",
          f"{conns} connections, {presses} presses")
    check(not misses,
          "retail's own stream never misses under the rule: 0 drops without a record",
          f"{dict(misses)}")
    check(opened >= 50 and opened == closed,
          "another agent's E4s equal its closes (50 = 48 E3 + 2 E2 on the hero tape)",
          f"opened {opened}, closed {closed}")


def section_binary():
    print("== 7. the model against the binary: the table rows and the log site ==")
    exe = vaultpath.vault_path("run", "slice", "Gw.exe")
    if not exe or not os.path.isfile(exe):
        LEDGER.skip("the receive table", f"no slice client at {exe}")
        return
    data = open(exe, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 52)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        vsize, va, rsize, raw = struct.unpack_from("<IIII", data, o + 8)
        secs.append((va, max(vsize, rsize), raw))

    def at(addr, n):
        rva = addr - base
        for va, size, raw in secs:
            if va <= rva < va + size:
                return data[raw + rva - va: raw + rva - va + n]
        return None

    rows = {}
    for addr in range(0x00BC9790, 0x00BC97C0 + 1, 12):
        blob = at(addr, 12)
        if blob is None:
            break
        desc, nf, handler = struct.unpack("<III", blob)
        op = at(desc, 4)
        rows[struct.unpack("<I", op)[0] if op else None] = (nf, handler)
    want = {0xE1: 2, 0xE2: 4, 0xE3: 4, 0xE4: 4, 0xE5: 5}
    check(all(rows.get(op, (None,))[0] == nf for op, nf in want.items()),
          "the rows at 0x00BC9790.. are [descriptor, field count, handler] for E1..E5 "
          "with the schema's field counts", f"{ {hex(k): v for k, v in rows.items() if k} }")
    h2, h3, h4 = (rows.get(op, (0, 0))[1] for op in (E2, E3, E4))
    check(h2 == h3 == 0x0091F650 and h4 == 0x0091F670,
          "E2 and E3 share one handler (0x0091F650, the drop), E4 has its own "
          "(0x0091F670, the add)", f"E2 {h2:#x} E3 {h3:#x} E4 {h4:#x}")
    s = at(0x00A95C94, 34)
    push = at(0x008230E2, 5)
    check(s == b"Pending skill %u copy %d not found" and push == b"\x68\x94\x5c\xa9\x00",
          "the log line is at 0x00A95C94 and 0x008230E2 pushes it (inside the drop, "
          "0x00823090)", f"{s!r} {push.hex() if push else None}")
    call = at(0x00814915, 5)
    check(call is not None and call[0] == 0xE8
          and 0x00814915 + 5 + struct.unpack("<i", call[1:])[0] == 0x00822B80,
          "the add's caller 0x008148F0 reaches 0x00822B80 (-> 0x00822F00, the add)",
          f"{call.hex() if call else None}")


def main():
    section_spell()
    section_drops()
    section_henchman()
    section_known_bad()
    section_wiring()
    section_retail()
    section_binary()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
