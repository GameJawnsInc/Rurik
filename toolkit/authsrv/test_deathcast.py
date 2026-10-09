"""A death closes the corpse's cast in flight: [59, me, 0] + E2 in the death batch, no E5.

CONFPASS-F1 (studies/deskwork/CONFIRM-2026-10-08.md §3). On the loopback runs CT-2 and
CT-2x the player pressed Backfire 28 (3.00 s), bled out partway, and the cast completed
AFTER the death batch: SKILL_RECHARGE(28), `skill_finished: skill 28 completes`, the hex
on agent 10, the aftercast's hold and E3 -- a hex from a corpse. `kill_player` dropped the
swing, the walk and the leads and never touched `pending_casts`; the cancel helper had
three callers (movement, the cancel action, a knock-down) and death was not one.

RETAIL, OBSERVED (deathcastjoin.py, prediction first): 29 observer deaths on the live
corpus, 6 with the observer's own cast open, and all 6 close it in the death batch with
[59, me, 0] immediately followed by E2 [me, skill, copy]; behind the status and the morale
pair (on the 4 that charged), ahead of the 0x00D0, the strips and the 0x002D; no [8, me, *]
in the batch; no E5 or E3 for the skill afterwards. Section 8 re-runs that census when the
vault is present and holds it as the positive control.

What this file pins, one change (DEATH_DROPS_CAST, `--no-death-drops-cast` reverts):
  1  a death mid-cast: the stop and the E2 after the status, no hold word, and the tick
     silent forever after (no E5, E3, E6, [58]) -- the entry removed;
  2  the slot on a map that charges morale: status, 0x009C, 0x00EE, then [59] and E2;
  3  THE KNOWN-BAD ARM: the flag off, the corpse completes -- E5 and [58] after the death;
  4  a cast QUEUED behind the dying one drops with [45] + E2 (RECONSTRUCTION at a death:
     release_cancelled_cast's never-began shape);
  5  a begun ATTACK skill drops with [49] + E2 (RECONSTRUCTION: the cancel family's form);
  6  CONTROL: a cast whose E5 is out (the aftercast) is not this rule's -- nothing for it
     in the batch (retail's one aftercast death is CONFPASS-F1b, open);
  7  a cast a knock-down marked and the tick has not yet released closes in the death
     batch, with no [8, me, 0] and nothing from the tick after;
  8  retail's census, the positive control (skips by name without the live corpus);
  9  the wiring: the flag ships on and the capture header says so, its revert parses,
     main()'s block executed really flips the module's flag, kill_player calls the helper.

NO SOCKET, NO CLIENT. Sections 1-7 and 9 stub `skill_timing` and read only the cancel wire,
so they run on a bare machine; section 8 needs the vault's live captures.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import checks  # noqa: E402

# FLOOR 21, the bare run's count (2026-10-09, RURIK_VAULT at an empty directory: 21 checks
# and section 8's declared skip). With the vault the same run executes 26 -- section 8's
# five on retail's census -- and a vault run that loses them says so by name, never by
# a shortfall. Measured both ways, not guessed.
LEDGER = checks.Ledger("death closes the cast", floor=21)
check = LEDGER.ok

PLAYER = 1   # authsrv.PLAYER_AGENT_ID, restated so a drift reddens something
FOE = 40     # an attack skill names a foe (the attack-target gate refuses target 0)


def _rec():
    sent = []
    return sent, (lambda op, vals, label="", quiet=False: sent.append((op, list(vals))))


def _press(authsrv, send, state, skill=42, copy=7, target=0):
    authsrv.handle_skill_press([0, skill, copy, target], send, state, 0,
                               authsrv.GAME_CMSG_USE_SKILL)


def _rewind(state, seconds):
    for cast in state.get("pending_casts", ()):
        for k in ("e5_at", "e3_at", "e6_at", "begin_at"):
            cast[k] -= seconds


def _idx(batch, op, vals=None, head=None):
    """Indices in `batch` of `op` whose values equal `vals` (or start with `head`)."""
    return [i for i, (o, v) in enumerate(batch)
            if o == op and (vals is None or v == vals)
            and (head is None or v[:len(head)] == head)]


class _Flags:
    """Set module flags for one block and put them back."""

    def __init__(self, mod, **kw):
        self.mod, self.kw, self.saved = mod, kw, {}

    def __enter__(self):
        for k, v in self.kw.items():
            self.saved[k] = getattr(self.mod, k)
            setattr(self.mod, k, v)

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(self.mod, k, v)


def _die_mid_cast(authsrv, on=True, into=0.5, state=None, timing=(2.0, 0.75, 8.0)):
    """Press skill 42 (copy 7), let `into` seconds of its activation pass, kill the player.
    Returns (state, the death batch, the send recorder for what follows)."""
    sent, send = _rec()
    state = state if state is not None else {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: timing
    try:
        _press(authsrv, send, state)
        _rewind(state, into)
        authsrv.cast_tick(send, state, 0)          # mid-activation: nothing is due
        sent.clear()
        with _Flags(authsrv, DEATH_DROPS_CAST=on):
            authsrv.kill_player(send, state, 0, "a test death")
        batch = list(sent)
        sent.clear()
    finally:
        authsrv.skill_timing = saved
    return state, batch, sent, send


def section_death_mid_cast(authsrv, agents):
    print("1. a death mid-cast: [59] + E2 in the death batch, and silence after")
    INT, E2 = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.GAME_SMSG_SKILL_REFUSED
    st, batch, sent, send = _die_mid_cast(authsrv)
    status = _idx(batch, authsrv.GAME_SMSG_AGENT_UPDATE_STATUS)
    stop = _idx(batch, INT, [agents.GV_SKILL_STOPPED, PLAYER, 0])
    e2 = _idx(batch, E2, [PLAYER, 42, 7])
    check(status[:1] == [0] and len(stop) == 1 and e2 == [stop[0] + 1] and stop[0] > 0,
          "1a. the KILL status first, then [59, me, 0] and E2 [me, 42, 7], adjacent -- "
          "retail 6 of 6 (deathcastjoin P2)",
          f"status {status} stop {stop} e2 {e2} batch {[hex(o) for o, _v in batch]}")
    tail = (_idx(batch, authsrv.GAME_SMSG_AGENT_MOVE_CANCEL)
            + _idx(batch, authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS))
    check(stop and e2 and tail and min(tail) > e2[0],
          "1b. ahead of the 0x002D and the flags word that close the batch (retail P3)",
          f"stop {stop} e2 {e2} tail {tail}")
    holds = _idx(batch, INT, head=[agents.GV_DISABLED, PLAYER])
    check(holds == [] and st.get("action_hold") == 1,
          "1c. no [8, me, *] in the batch: the cast's own hold already holds the corpse "
          "(retail P4, 6 of 6) -- no release, no repeat",
          f"holds {[batch[i] for i in holds]} action_hold {st.get('action_hold')}")
    check(st.get("cast_busy_until", 1e18) <= time.time(),
          "1d. the busy window rolls back: a press after the rise is not queued behind "
          "a cast that will never complete",
          f"busy in {st.get('cast_busy_until', 0) - time.time():.2f}s")
    authsrv.cast_tick(send, st, 0)
    check(sent == [] and not st.get("pending_casts"),
          "1e. the next tick sends nothing and removes the entry", f"{sent}")
    _rewind(st, 60.0)
    authsrv.cast_tick(send, st, 0)
    check(sent == [],
          "1f. and nothing ever after: no E5 (no recharge), no [58], no E3, no E6 -- "
          "retail P1, 6 of 6", f"{[(hex(o), v) for o, v in sent]}")


def section_slot_with_morale(authsrv, agents):
    print("\n2. the slot on a map that charges: status, 0x009C, 0x00EE, then [59] + E2")
    st = {"agents": {}, "map_id": 146, "level": 1}
    authsrv.player_pools(st)
    _s, _send = _rec()                  # a condition up, so the batch carries a strip
    authsrv.apply_condition(_send, st, PLAYER, authsrv.effects.CONDITION_BY_NAME["Bleeding"],
                            10.0, 0, 0, None)
    with _Flags(authsrv, DEATH_PENALTY_FORCED=True):
        st, batch, _sent, _send = _die_mid_cast(authsrv, state=st)
    status = _idx(batch, authsrv.GAME_SMSG_AGENT_UPDATE_STATUS)
    mor = _idx(batch, authsrv.GAME_SMSG_AGENT_MORALE)
    attr = _idx(batch, authsrv.GAME_SMSG_PLAYER_ATTR_UPDATE)
    stop = _idx(batch, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                [agents.GV_SKILL_STOPPED, PLAYER, 0])
    e2 = _idx(batch, authsrv.GAME_SMSG_SKILL_REFUSED, [PLAYER, 42, 7])
    check(mor and attr and stop and e2
          and status[0] < mor[0] < attr[0] < stop[0] < e2[0] == stop[0] + 1,
          "2a. the morale pair goes first and the close rides behind it -- retail's order "
          "on all 4 charged deaths with a cast open (20260928T103123 624.116, three on "
          "20260929T100038)",
          f"status {status} 9C {mor} EE {attr} stop {stop} e2 {e2}")
    strips = _idx(batch, authsrv.GAME_SMSG_EFFECT_REMOVE)
    check(stop and e2 and strips and all(i > e2[0] for i in strips)
          and not _idx(batch, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                       head=[agents.GV_DISABLED, PLAYER]),
          "2b. the Bleeding's strip rides behind the E2 (retail P3: every strip behind it), "
          "and still no hold word", f"strips {strips} e2 {e2} batch {[hex(o) for o, _v in batch]}")


def section_known_bad(authsrv, agents):
    print("\n3. KNOWN-BAD ARM (--no-death-drops-cast): the corpse completes its cast")
    st, batch, sent, send = _die_mid_cast(authsrv, on=False)
    INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
    check(not _idx(batch, INT, [agents.GV_SKILL_STOPPED, PLAYER, 0])
          and not _idx(batch, authsrv.GAME_SMSG_SKILL_REFUSED),
          "3a. the death batch says nothing about the cast", f"{[hex(o) for o, _v in batch]}")
    with _Flags(authsrv, DEATH_DROPS_CAST=False):
        _rewind(st, 2.0)
        authsrv.cast_tick(send, st, 0)
    check(_idx(sent, authsrv.GAME_SMSG_SKILL_RECHARGE, [PLAYER, 42, 7, 8])
          and _idx(sent, INT, [agents.GV_SKILL_FINISHED, PLAYER, 0]),
          "3b. and after it the tick completes the cast on the corpse: E5 [me, 42, 7, 8] "
          "and [58, me, 0] -- CT-2 / CT-2x's SKILL_RECHARGE(28) and 'skill 28 completes'",
          f"{[(hex(o), v) for o, v in sent]}")


def section_queued(authsrv, agents):
    print("\n4. a cast queued behind the dying one drops with [45] + E2 (RECONSTRUCTION)")
    sent, send = _rec()
    st = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        _press(authsrv, send, st, skill=105)          # activating
        _press(authsrv, send, st, skill=42)           # QUEUED behind it
        queued = [c.get("begun", True) for c in st["pending_casts"]]
        sent.clear()
        authsrv.kill_player(send, st, 0, "a test death")
        batch = list(sent)
        sent.clear()
        INT, E2 = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.GAME_SMSG_SKILL_REFUSED
        s59 = _idx(batch, INT, [agents.GV_SKILL_STOPPED, PLAYER, 0])
        s45 = _idx(batch, INT, [agents.GV_CAST_DROPPED, PLAYER, 0])
        e2a = _idx(batch, E2, [PLAYER, 105, 7])
        e2b = _idx(batch, E2, [PLAYER, 42, 7])
        check(queued == [True, False] and s59 and e2a == [s59[0] + 1]
              and s45 and e2b == [s45[0] + 1],
              "4a. the begun spell closes with [59] + E2, the queued one with [45] + E2 -- "
              "release_cancelled_cast's never-began marker (4 of 4 pre-begin drops), at a "
              "death unwitnessed",
              f"begun {queued} 59 {s59} E2(105) {e2a} 45 {s45} E2(42) {e2b}")
        _rewind(st, 60.0)
        authsrv.cast_tick(send, st, 0)
        check(sent == [] and not st["pending_casts"],
              "4b. and the queued cast never begins on the corpse: no debit, no animation, "
              "no E5", f"{[(hex(o), v) for o, v in sent]}")
    finally:
        authsrv.skill_timing = saved


def section_attack_skill(authsrv, agents):
    print("\n5. a begun attack skill drops with [49] + E2 (RECONSTRUCTION)")
    saved_a = authsrv._is_attack_skill
    authsrv._is_attack_skill = lambda sid: True
    try:
        sent, send = _rec()
        st = {"agents": {}}
        saved_t = authsrv.skill_timing
        authsrv.skill_timing = lambda sid: (1.0, 0.0, 3.0)
        try:
            _press(authsrv, send, st, skill=394, target=FOE)
            begun = [c.get("begun", True) and c.get("attack") for c in st["pending_casts"]]
            sent.clear()
            authsrv.kill_player(send, st, 0, "a test death")
            batch = list(sent)
            sent.clear()
            s49 = _idx(batch, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                       [agents.GV_ATTACK_SKILL_STOPPED, PLAYER, 0])
            e2 = _idx(batch, authsrv.GAME_SMSG_SKILL_REFUSED, [PLAYER, 394, 7])
            check(begun == [True] and s49 and e2 == [s49[0] + 1]
                  and not _idx(batch, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                               [agents.GV_SKILL_STOPPED, PLAYER, 0]),
                  "5a. the attack trio's stop [49], not the spell's [59] -- the cancel "
                  "family's form (2 of 2 begun attack-skill cancels); at a death unwitnessed",
                  f"begun {begun} 49 {s49} e2 {e2}")
            _rewind(st, 60.0)
            authsrv.cast_tick(send, st, 0)
            check(sent == [], "5b. and the strike never lands: nothing after",
                  f"{[(hex(o), v) for o, v in sent]}")
        finally:
            authsrv.skill_timing = saved_t
    finally:
        authsrv._is_attack_skill = saved_a


def section_aftercast_control(authsrv, agents):
    print("\n6. CONTROL: a cast whose E5 is out is not this rule's")
    sent, send = _rec()
    st = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, send, st)
        _rewind(st, 1.0)
        authsrv.cast_tick(send, st, 0)                # E5: the aftercast begins
        e5 = bool(_idx(sent, authsrv.GAME_SMSG_SKILL_RECHARGE))
        sent.clear()
        authsrv.kill_player(send, st, 0, "a test death")
        batch = list(sent)
        check(e5 and not _idx(batch, authsrv.GAME_SMSG_SKILL_REFUSED)
              and not _idx(batch, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                           [agents.GV_SKILL_STOPPED, PLAYER, 0])
              and st["pending_casts"] and not st["pending_casts"][0].get("cancelled"),
              "6a. the death leaves a completed cast alone -- the predicate is 'no E5', "
              "and retail's one aftercast death ([57] + E2, 20260929T100038 :51090 "
              "423.923) is CONFPASS-F1b, open, not shipped on n = 1",
              f"e5 {e5} batch {[hex(o) for o, _v in batch]}")
    finally:
        authsrv.skill_timing = saved


def section_knocked_then_dead(authsrv, agents):
    print("\n7. a knock-down's mark the tick has not yet released closes in the death batch")
    sent, send = _rec()
    st = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        with _Flags(authsrv, KNOCK_DOWN=True):
            _press(authsrv, send, st)
            authsrv.knock_down(send, st, PLAYER, 0, "a test hammer")
        marked = [c.get("cancelled") for c in st["pending_casts"]]
        sent.clear()
        authsrv.kill_player(send, st, 0, "a test death")
        batch = list(sent)
        sent.clear()
        INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
        stop = _idx(batch, INT, [agents.GV_SKILL_STOPPED, PLAYER, 0])
        e2 = _idx(batch, authsrv.GAME_SMSG_SKILL_REFUSED, [PLAYER, 42, 7])
        check(marked == ["knocked-down"] and stop and e2 == [stop[0] + 1]
              and not _idx(batch, INT, [agents.GV_DISABLED, PLAYER, 0]),
              "7a. [59] + E2 in the death batch and no hold release -- where the tick's "
              "release a tick later would have sent [8, me, 0] to a corpse",
              f"marked {marked} stop {stop} e2 {e2}")
        authsrv.cast_tick(send, st, 0)
        check(sent == [] and not st["pending_casts"],
              "7b. and the tick only removes it", f"{[(hex(o), v) for o, v in sent]}")
    finally:
        authsrv.skill_timing = saved


def section_retail():
    print("\n8. retail's census, the positive control (deathcastjoin.py)")
    try:
        import livewire
        import deathcastjoin
        have = bool(livewire.live_captures())
    except Exception as exc:                                  # noqa: BLE001
        have, why = False, f"{type(exc).__name__}: {exc}"
    else:
        why = f"no live captures under {livewire.captures_root()}"
    if not have:
        LEDGER.skip("8. retail's death batches", why)
        return
    tot, _rows = deathcastjoin.census()
    n = tot["open"]
    check(n >= 6, "8a. the corpus holds at least the 6 deaths with the observer's cast "
          "open (a FLOOR: a new tape may add one)", f"{n} of {tot['deaths']} deaths")
    for p, what in (("P1", "no E5 / E3 for the cut skill afterwards"),
                    ("P2", "[59, me, 0] then E2 [me, skill, copy], adjacent"),
                    ("P3", "behind the status + morale pair, ahead of 0x00D0 / strips / 0x002D"),
                    ("P4", "no [8, me, *] in the batch")):
        check(n and tot[p] == n, f"8{'bcde'[int(p[1]) - 1]}. retail {p}: {what} -- every one",
              f"{tot[p]} of {n}")


def section_wiring(authsrv):
    print("\n9. the wiring")
    import argparse
    import contextlib
    import io
    import serverargs
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    check(authsrv.DEATH_DROPS_CAST is True
          and authsrv.capture_flags().get("DEATH_DROPS_CAST") is True,
          "9a. the flag ships on, and the capture header records which arm ran")
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    check(getattr(ap.parse_args([]), "no_death_drops_cast", None) is False
          and getattr(ap.parse_known_args(["--no-death-drops-cast"])[0],
                      "no_death_drops_cast", None) is True,
          "9b. --no-death-drops-cast parses, default off")
    # main()'s own block, lifted out of the source and RUN in authsrv's namespace
    # (test_agtrack_guard 16l's pattern): without its `global` the assignment binds a
    # local, and the flag parses and never takes effect -- which a text match cannot see.
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_death_drops_cast:", i_main)
    i_end = src.find("\n    if a.", i_flip + 1)
    flipped = None
    if 0 < i_main < i_flip < i_end:
        body = "\n".join(line[4:] if line.startswith("    ") else line
                         for line in src[i_flip:i_end].splitlines())
        code = "def _dc_flip(a):\n" + "\n".join("    " + ln for ln in body.splitlines())
        try:
            exec(compile(code, "<main:no_death_drops_cast>", "exec"), authsrv.__dict__)
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.__dict__["_dc_flip"](argparse.Namespace(no_death_drops_cast=True))
            flipped = authsrv.DEATH_DROPS_CAST
        finally:
            authsrv.DEATH_DROPS_CAST = True
            authsrv.__dict__.pop("_dc_flip", None)
    check(flipped is False,
          "9c. main()'s --no-death-drops-cast block, executed, really sets the MODULE's "
          "DEATH_DROPS_CAST to False", f"main {i_main} flip {i_flip} end {i_end} -> {flipped}")
    kp = src.split("\ndef kill_player(", 1)[-1].split("\ndef ", 1)[0]
    check("death_drops_casts(send, state, conn_id, why)" in kp,
          "9d. kill_player calls the helper (the defect's site)")


def main():
    import authsrv
    import agents
    authsrv.WEAPON_GATE = False      # section 5's bow skill with the fixture's hammer: not
                                     # what is measured here (test_castcancel's convention)
    section_death_mid_cast(authsrv, agents)
    section_slot_with_morale(authsrv, agents)
    section_known_bad(authsrv, agents)
    section_queued(authsrv, agents)
    section_attack_skill(authsrv, agents)
    section_aftercast_control(authsrv, agents)
    section_knocked_then_dead(authsrv, agents)
    section_retail()
    section_wiring(authsrv)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
