"""Kill experience: what one hostile's death pays, per foe (RANGERPRE-S6, KILLXP-a).

    python toolkit/authsrv/test_killxp.py

WHAT CHANGED AND WHY THIS FILE EXISTS. Until 2026-09-29 every hostile death
sent `0x00EE [0, 26]`, on a comment that read three 26s as evidence the value
does not vary. The Reforged pre-Searing capture 20260929T150923 (:55934, wire
t 477.1186) pays `[0, 176]` for one level-5 foe, and all 49 own-kill awards in
the live corpus are GWW's "Experience per foe" table, split by the party and
times the Reforged Mode effect's +5% where that effect (0x0041 skill 3434) was
on the connection -- zero free parameters. `killxp.py` is the arithmetic,
content/world.toml [player.experience] the numbers, `authsrv.kill_experience`
the inputs, and `kill_agent` the send.

THE ORACLE IS THE WIRE, pinned. Section 2's rows are the corpus scan's 49
awards (12 distinct inputs, every one cited to capture, connection and wire
t) -- literals, so this file runs on a machine with no vault; re-deriving them
from the tapes on every run is a deferred corpus section (RANGERPRE.md section
4). Two KNOWN-BAD ARMS are scored on the same rows and must fall short: the old
constant (5 of 49) and the rule without the +5% (32 of 49). So is the
UNSCOPED +5% (17 of 49), which is why the stand-in is scoped to the maps the
effect was observed on and never to the character's Reforged flag: the 17
level-0 kills on map 212 and the 6 on map 430 are Reforged-flagged characters
outside the effect's zone, paid 100%.

Section 3 drives OUR kill_agent -- the frame, the zero share, the fixture
fallback, the party split, the stand-in's scope, the store and the morale bank
fed the same number the wire carried -- and runs the revert arm
(--kill-xp-constant), whose [0, 26] the level-1 predicate must refuse.
Section 4 pins the two flags. What the kill frame's `0x009C` + `0x00EE [10, 0]`
lines are (the 75-XP tick) is RANGERPRE-S7's, not this file's.

NO VAULT, NO SOCKET, NO CLIENT.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import agents  # noqa: E402
import killxp  # noqa: E402

# FLOOR 30: the green run's count (2026-09-29, RANGERPRE-S6), measured both with
# the vault and with RURIK_VAULT at a nonexistent path -- nothing here reads it.
LEDGER = checks.Ledger("kill experience", floor=30)
check = LEDGER.ok

# OBSERVED (the corpus scan of 2026-09-29, every input re-derived from its own
# connection): foe level (0x0056), player level (0x00E9 + 0x00EE [9, d]),
# party (1 + 0x01BF + 0x01C2 rows), 3434 on the connection, the map, the award
# 0x00EE [0, x] in the segment of 0x0026 [foe, 8], how many, and where.
WITNESSES = (
    (2, 1, 1, True, 146, 126, 2,
     "20260807T143055 :64103 251.917 (def 1346); 20260929T150923 :55934 536.737"),
    (0, 1, 1, True, 146, 26, 5,
     "20260807T143055 :62994 86.020; 20260810T235916 :61624 99.549 and :49163 "
     "294.908; 20260929T150923 :55934 264.333 and 383.573"),
    (20, 20, 4, False, 311, 25, 1, "20260817T231139 :50527 546.593 (a PvP arena)"),
    (2, 2, 4, False, 238, 25, 2, "20260819T132414 :52606 184.301, 196.007"),
    (1, 2, 4, False, 238, 20, 1, "20260819T132414 :52606 205.943"),
    (3, 2, 4, False, 238, 30, 5, "20260819T132414 :52606 238.115 .. 265.223"),
    (0, 1, 1, False, 212, 25, 17, "20260913T210901 :60877 343.221 .. 723.410"),
    (1, 3, 2, False, 430, 32, 6, "20260914T005758 :56011 184.341 .. 534.478"),
    (1, 1, 1, True, 146, 105, 4,
     "20260915T155656 :51922 412.523; 20260929T150923 :55934 361.137, 429.284, "
     "580.539"),
    (5, 1, 1, True, 146, 176, 1, "20260929T150923 :55934 477.119 (def 1397)"),
    (1, 2, 1, True, 160, 84, 4,
     "20260929T150923 :53756 1060.488, 1107.883, 1117.822, 1140.933"),
    (3, 2, 1, True, 146, 126, 1, "20260929T150923 :56025 861.965 (def 1438)"),
)


def _fit(fn):
    """How many of the 49 awards `fn(foe, me, party, eff, map)` reproduces."""
    return sum(n for foe, me, party, eff, mp, x, n, _w in WITNESSES
               if fn(foe, me, party, eff, mp) == x)


def _state(me, party, mp, **extra):
    """A connection state carrying the inputs kill_experience reads: the
    player's level, a party padded with hired henchmen, the map."""
    st = {"level": me, "map_id": mp,
          "party_henchmen": {9000 + i: {} for i in range(party - 1)}}
    st.update(extra)
    return st


def _foe(level=1):
    npc = dict(agents.HATCHER)
    if level is None:
        npc.pop("level", None)
    else:
        npc["level"] = level
    return {"name": "t", "dead": False, "npc": npc, "pos": (0.0, 0.0),
            "health": 1.0, "max_health": 10.0}


def _kill(authsrv, state, foe):
    """Drive kill_agent on `foe` as agent 10; the (op, values) it sent."""
    sent = []
    state.setdefault("agents", {})[10] = foe
    authsrv.kill_agent(lambda op, v, label="", quiet=False:
                       sent.append((op, list(v))),
                       state, 10, foe, 0, 0.0)
    return sent


def _awards(authsrv, sent):
    return [v for op, v in sent if op == authsrv.GAME_SMSG_AGENT_KILL_REWARD
            and v[0] == authsrv.KILL_REWARD_ATTR]


def section_rule():
    print("\n1. the rule: the wiki's two tables, the party split, the effect")
    row = agents.WORLD.get("player", "experience")
    prov = row.provenance
    check(prov.get("source") == "wiki" and "rev 2740292" in prov.get("page", "")
          and "rev 2722562" in prov.get("page", "") and "3434" in prov.get("page", ""),
          "the [player.experience] row loads with source 'wiki' and names both "
          "pages and their revisions", prov.get("page", ""))
    check(len(killxp.BY_DIFFERENCE) == 18 and killxp.DIFFERENCE_MIN == -6
          and killxp.DIFFERENCE_MAX == 11 and killxp.LEVEL_ZERO_FOE == (25, 20, 15, 10, 5),
          "the table runs -6 (0) to +11 (280), the level-0 table L1..L5",
          f"{killxp.BY_DIFFERENCE} {killxp.DIFFERENCE_MIN}..{killxp.DIFFERENCE_MAX} "
          f"{killxp.LEVEL_ZERO_FOE}")
    rows = [((1, 1), 100), ((2, 1), 120), ((1, 2), 80), ((0, 1), 25), ((0, 5), 5),
            ((0, 6), 0), ((1, 7), 0), ((2, 7), 16), ((12, 1), 280), ((21, 1), 280)]
    got = [(a, killxp.share(*a), want) for a, want in rows]
    check(all(g == w for _a, g, w in got),
          "share against the wiki's rows: same level 100, +1 120, -1 80, a level-0 "
          "foe 25 at L1 and 5 at L5, 0 at L6 (RECONSTRUCTION past the table), six "
          "below 0, five below 16, +11 and +20 both the cap 280",
          str([(a, g) for a, g, w in got if g != w]))
    check(killxp.share(12, 1, 2) == 140 and killxp.share(2, 7, 2) == 8,
          "a party of 2 halves 280 to 140 and 16 to 8 -- the wiki's own third column")
    reforged = [((0, 1), 26), ((5, 1), 176), ((1, 1), 105), ((1, 2), 84), ((2, 1), 126)]
    got = [(a, killxp.share(*a, reforged=True), want) for a, want in reforged]
    check(all(g == w for _a, g, w in got),
          "under the effect: 26, 176, 105, 84, 126 -- the five values on the wire",
          str([(a, g) for a, g, w in got if g != w]))
    check(killxp.share(1, 1, 0) == 100 and killxp.share(1, 1, -3) == 100,
          "a party below 1 reads as the player alone -- no divide by zero on the "
          "kill path")
    check(killxp.reforged_map(146) and killxp.reforged_map(160)
          and not killxp.reforged_map(148) and not killxp.reforged_map(212)
          and not killxp.reforged_map(430) and not killxp.reforged_map(None),
          "the effect's scope: the two pre-Searing explorables it was observed on, "
          "not the town (148), not a Factions or Nightfall map (212, 430), not "
          "'no map yet'", str(sorted(killxp.REFORGED_EFFECT_MAPS)))


def section_witnesses(authsrv):
    print("\n2. the corpus's 49 awards, pinned, and the arms that miss them")
    total = sum(w[6] for w in WITNESSES)
    check(total == 49 and sum(w[6] for w in WITNESSES if w[3]) == 17,
          "49 awards, 17 of them under the effect", f"{total}")
    fit = _fit(lambda foe, me, party, eff, mp: killxp.share(foe, me, party, eff))
    check(fit == 49, "killxp.share reproduces 49 of 49 with nothing fitted",
          f"{fit}/49")

    saved = authsrv.REFORGED_XP
    try:
        authsrv.REFORGED_XP = False
        fit = _fit(lambda foe, me, party, eff, mp: authsrv.kill_experience(
            _state(me, party, mp, reforged_effect=eff), {"npc": {"level": foe}}))
        check(fit == 49, "kill_experience on the tape's own inputs (level, a padded "
              "party, the effect as the load would set it) reproduces 49 of 49",
              f"{fit}/49")
        authsrv.REFORGED_XP = True
        fit = _fit(lambda foe, me, party, eff, mp: authsrv.kill_experience(
            _state(me, party, mp), {"npc": {"level": foe}}))
        check(fit == 49, "--reforged-xp's stand-in, scoped by map alone, also "
              "reproduces 49 of 49: it pays the 17 on 146/160 and not the 32 "
              "elsewhere", f"{fit}/49")
        authsrv.REFORGED_XP = False
        fit = _fit(lambda foe, me, party, eff, mp: authsrv.kill_experience(
            _state(me, party, mp), {"npc": {"level": foe}}))
        check(fit == 32, "the DEFAULT (no effect served, stand-in off) pays 100% "
              "everywhere: 32 of 49, short exactly the 17 effect kills", f"{fit}/49")
    finally:
        authsrv.REFORGED_XP = saved

    const = _fit(lambda *a: authsrv.KILL_REWARD_VALUE)
    check(const == 5, "KNOWN-BAD ARM: the old constant 26 fits 5 of 49 (the "
          "level-0 kills at L1 under the effect) -- and no more", f"{const}/49")
    base = _fit(lambda foe, me, party, eff, mp: killxp.share(foe, me, party, False))
    check(base == 32, "KNOWN-BAD ARM: the rule without the +5% fits 32 of 49",
          f"{base}/49")
    unscoped = _fit(lambda foe, me, party, eff, mp: killxp.share(foe, me, party, True))
    check(unscoped == 17, "KNOWN-BAD ARM: the +5% on every kill (no zone scope -- "
          "what a character-flag rule pays a Reforged character on maps 212 and "
          "430) fits 17 of 49, missing all 32 no-effect kills", f"{unscoped}/49")


def section_our_frame(authsrv):
    print("\n3. our kill_agent: the award, and every consumer of it")
    ops = lambda sent: [op for op, _v in sent]
    frame = [authsrv.GAME_SMSG_AGENT_UPDATE_STATUS, authsrv.GAME_SMSG_AGENT_KILL_REWARD,
             authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS]

    def level1_ok(sent):
        return ops(sent) == frame and _awards(authsrv, sent) == [[0, 100]]

    sent = _kill(authsrv, _state(1, 1, 146), _foe(1))
    check(level1_ok(sent), "a level-1 foe at player level 1: status, [0, 100], "
          "flags -- three messages, retail's order",
          str([(hex(op), v) for op, v in sent]))
    sent = _kill(authsrv, _state(3, 1, 146), _foe(1))
    check(_awards(authsrv, sent) == [[0, 64]],
          "the same foe at the slice's level 3 pays 64 (two below)",
          str(_awards(authsrv, sent)))
    sent = _kill(authsrv, _state(3, 1, 146), _foe(0))
    check(_awards(authsrv, sent) == [[0, 15]],
          "a level-0 foe (the worm) at level 3 pays 15, the wiki's level-0 row",
          str(_awards(authsrv, sent)))
    sent = _kill(authsrv, _state(1, 2, 146), _foe(1))
    check(_awards(authsrv, sent) == [[0, 50]],
          "one hired henchman in the party halves it to 50 (party_member_count)",
          str(_awards(authsrv, sent)))
    sent = _kill(authsrv, _state(7, 1, 146), _foe(1))
    check(ops(sent) == [authsrv.GAME_SMSG_AGENT_UPDATE_STATUS,
                        authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS],
          "a foe six levels below pays 0 and sends NO 0x00EE (the corpus's unpaid "
          "deaths carry none; [0, 0] is UNVERIFIED) -- the death itself still goes out",
          str([(hex(op), v) for op, v in sent]))
    sent = _kill(authsrv, _state(1, 1, 146), _foe(None))
    check(_awards(authsrv, sent) == [[0, authsrv.KILL_REWARD_VALUE]],
          "a body whose row has no level (a fixture) is paid the pre-KILLXP "
          "constant", str(_awards(authsrv, sent)))

    saved = authsrv.REFORGED_XP
    try:
        authsrv.REFORGED_XP = False
        a = _awards(authsrv, _kill(authsrv, _state(1, 1, 146), _foe(1)))
        check(a == [[0, 100]], "stand-in OFF (the default) on 146: 100, the base",
              str(a))
        authsrv.REFORGED_XP = True
        got = {mp: _awards(authsrv, _kill(authsrv, _state(1, 1, mp), _foe(1)))
               for mp in (146, 160, 212, 148, 474, 280)}
        check(got == {146: [[0, 105]], 160: [[0, 105]], 212: [[0, 100]],
                      148: [[0, 100]], 474: [[0, 100]], 280: [[0, 100]]},
              "--reforged-xp pays 105 on 146 and 160 and 100 elsewhere -- 212 (a "
              "Reforged character, no effect), the town 148, and two SERVED "
              "explorables outside Prophecies (474, 280), which an 'any explorable' "
              "stand-in would pay 105", str(got))
        a = _awards(authsrv, _kill(authsrv, _state(1, 1, 146, reforged_effect=False),
                                   _foe(1)))
        check(a == [[0, 100]], "a load's own reforged_effect=False overrides the "
              "stand-in", str(a))
        authsrv.REFORGED_XP = False
        a = _awards(authsrv, _kill(authsrv, _state(1, 1, 212, reforged_effect=True),
                                   _foe(1)))
        check(a == [[0, 105]], "...and reforged_effect=True is the answer wherever "
              "the load set it (REFORGEDFX's seam)", str(a))
    finally:
        authsrv.REFORGED_XP = saved

    # The store gains what the wire carried.
    class _Store:
        def __init__(self):
            self.row, self.saves = {"xp": 1000}, 0

        def character_by_uuid(self, _u):
            return self.row

        def account(self):
            return {"factions": {}}

        def save(self):
            self.saves += 1

    store, saved = _Store(), authsrv.PERSIST
    try:
        authsrv.PERSIST = True
        sent = _kill(authsrv, _state(1, 1, 146, charstore_game=store, char_uuid="u"),
                     _foe(1))
    finally:
        authsrv.PERSIST = saved
    check(store.row["xp"] == 1100 and _awards(authsrv, sent) == [[0, 100]]
          and store.saves == 1,
          "under --persist the store accrues the 100 the wire carried, not 26",
          f"xp {store.row['xp']}, saves {store.saves}")

    # ...and so does the death-penalty bank.
    st = _state(1, 1, 146, morale=85)
    _kill(authsrv, st, _foe(1))
    check(st["morale"] == 86,
          "a penalised player's first level-1 kill buys back 1%: the bank was fed "
          "the 100 paid (a 26 took three kills)", f"morale {st['morale']}")

    # THE REVERT ARM, and the predicate must refuse it.
    saved = authsrv.KILL_XP_RULE
    try:
        authsrv.KILL_XP_RULE = False
        sent = _kill(authsrv, _state(1, 1, 146), _foe(1))
    finally:
        authsrv.KILL_XP_RULE = saved
    check(_awards(authsrv, sent) == [[0, authsrv.KILL_REWARD_VALUE]]
          and not level1_ok(sent),
          "KNOWN-BAD ARM (--kill-xp-constant): [0, 26] for the level-1 foe, and the "
          "level-1 predicate above refuses it", str(_awards(authsrv, sent)))


def section_flags(authsrv):
    print("\n4. the two flags: the revert arm and the stand-in, default off")
    check(authsrv.KILL_XP_RULE is True and authsrv.REFORGED_XP is False,
          "at import the rule is on and the +5% stand-in is off")
    args = io.open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    src = io.open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    i_main = src.index("\ndef main():")
    i_k = src.index("    if a.kill_xp_constant:\n", i_main)
    i_r = src.index("    if a.reforged_xp:\n", i_main)
    check('ap.add_argument("--kill-xp-constant", action="store_true"' in args
          and 'ap.add_argument("--reforged-xp", action="store_true"' in args
          and "KILL_XP_RULE = False" in src[i_k:i_k + 120]
          and "REFORGED_XP = True" in src[i_r:i_r + 120]
          and "if a.kill_xp_constant and a.reforged_xp:" in src[i_main:],
          "serverargs registers both; main() flips each and refuses the pair")


def main():
    import authsrv
    section_rule()
    section_witnesses(authsrv)
    section_our_frame(authsrv)
    section_flags(authsrv)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
