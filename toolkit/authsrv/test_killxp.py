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
fallback, the party split, the stand-in's scope, the store and the death
penalty fed the same number the wire carried -- and runs the revert arm
(--kill-xp-constant), whose [0, 26] the level-1 predicate must refuse.
Section 4 pins the two flags.

SECTION 5 IS RANGERPRE-S7 (KILLXP-b): the kill frame's `0x009C [player, m]` +
`0x00EE [10, d]` lines. They are the 75-XP death-penalty tick: they ride every
award whose experience crosses a multiple of 75 SINCE THE INSTANCE LOADED, at
neutral morale too ([player, 100] + [10, 0]), AHEAD of the award's own
`0x00EE [0, x]`. The oracle is again the wire, pinned: the 68 PvE awards of
seventeen connections in eight captures, each marked tick or no tick with the
tick's own values, and the deaths between them (TICK_TAPES). The since-load
counter predicts 68 of 68; two KNOWN-BAD ARMS fall short -- the character's
total experience (58) and the pre-S7 bank that started at the death and was
silent at neutral (morale.experience_credit, 20). Then OUR server replays each
connection through morale_experience and must put retail's (m, d) on the wire
for all 43 ticks and nothing on the other 25; then kill_agent's and
grant_quest_reward's frames, the maxima riding a tick only when they moved,
and the heroes' ticks behind the award.

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

# FLOOR 44: the green run's count (2026-09-29, RANGERPRE-S7: S6's 30 + section
# 5's 14), measured both with the vault and with RURIK_VAULT at a nonexistent
# path -- nothing here reads it.
LEDGER = checks.Ledger("kill experience", floor=44)
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


# OBSERVED (RANGERPRE-S7's scan of 2026-09-29, every PvE 0x00EE [0, x] on the
# connection, in wire order): (citation, map, the load's experience -- 0x00E9
# field 0 --, the awards). A token `x` is an award whose segment carries no
# tick; `x^m/d` one whose segment carries 0x009C [player, m] and 0x00EE [10, d]
# ahead of it; `dM` a death between awards (0x009C [player, M] with 0x00EE
# [10, -15], no award). Kill and quest awards alike: the counter is fed by both.
TICK_TAPES = (
    ("20260807T143055 :60935 46.797", 148, 0, "100^100/0"),
    ("20260807T143055 :64103 251.917 (the Wolf)", 146, 876, "126^100/0"),
    ("20260807T143055 :62994 70.441 .. 92.792", 146, 100,
     "250^100/0 26 500^100/0"),
    ("20260810T235916 :61193 45.208", 148, 0, "100^100/0"),
    ("20260810T235916 :61624 68.073 .. 126.917", 146, 100,
     "250^100/0 26 500^100/0"),
    ("20260810T235916 :49163 294.908", 146, 876, "26"),
    ("20260819T132414 :52606 145.487 .. 276.817", 238, 2625,
     "1000^100/0 25 25^100/0 20 100^100/0 30^100/0 30 30 30^100/0 30 1000^100/0"),
    ("20260913T210901 :60877 343.221 .. 736.185", 212, 0,
     "25 25 d85 25^86/1 25 25 25^87/1 25 25 25^88/1 25 25 25^89/1 25 25 "
     "25^90/1 25 25 2000^100/10"),
    ("20260914T005758 :56011 184.341 .. 534.477", 430, 6575,
     "32 32 32^100/0 d85 32 32^86/1 32"),
    ("20260914T180058 :56301 292.643", 146, 928, "250^100/0"),
    ("20260915T155656 :51922 412.523", 146, 1178, "105^100/0"),
    ("20260929T150923 :55934 231.001 .. 627.373", 146, 100,
     "250^100/0 26 500^100/0 105^100/0 26^100/0 105^100/0 176^100/0 126^100/0 "
     "105^100/0 250^100/0"),
    ("20260929T150923 :59427 1244.150 .. 1279.408", 148, 2731,
     "250^100/0 100^100/0 500^100/0"),
    ("20260929T150923 :53880 727.487", 148, 1769, "250^100/0"),
    ("20260929T150923 :59969 207.676", 148, 0, "100^100/0"),
    ("20260929T150923 :53756 1060.488 .. 1190.237", 160, 2145,
     "84^100/0 84^100/0 84^100/0 84^100/0 250^100/0"),
    ("20260929T150923 :56025 861.965", 146, 2019, "126^100/0"),
)


def _tape(tokens):
    """[("died", M) | (x, (m, d) or None)] from one TICK_TAPES string."""
    out = []
    for tok in tokens.split():
        if tok.startswith("d"):
            out.append(("died", int(tok[1:])))
        elif "^" in tok:
            x, md = tok.split("^")
            m, d = md.split("/")
            out.append((int(x), (int(m), int(d))))
        else:
            out.append((int(tok), None))
    return out


def _s32(v):
    v = int(v) & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


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
    # RANGERPRE-S7: a first award of 100 crosses 75, so the frame carries the
    # tick -- 0x009C [player, 100], 0x00EE [10, 0] -- AHEAD of the award.
    frame = [(authsrv.GAME_SMSG_AGENT_UPDATE_STATUS, None),
             (authsrv.GAME_SMSG_AGENT_MORALE, [authsrv.PLAYER_AGENT_ID, 100]),
             (authsrv.GAME_SMSG_PLAYER_ATTR_UPDATE, [authsrv.PLAYER_ATTR_MORALE_ID, 0]),
             (authsrv.GAME_SMSG_AGENT_KILL_REWARD, [0, 100]),
             (authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS, None)]

    def level1_ok(sent):
        return (len(sent) == len(frame)
                and all(op == fo and (fv is None or v == fv)
                        for (op, v), (fo, fv) in zip(sent, frame)))

    sent = _kill(authsrv, _state(1, 1, 146), _foe(1))
    check(level1_ok(sent), "a level-1 foe at player level 1: status, the 75-XP "
          "tick 0x009C [player, 100] + 0x00EE [10, 0], [0, 100], flags -- retail's "
          "frame shape (RANGERPRE-S7; 20260929T150923 :55934 477.1186 for its 176)",
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

    # ...and so does the death penalty.
    st = _state(1, 1, 146, morale=85)
    _kill(authsrv, st, _foe(1))
    check(st["morale"] == 86,
          "a penalised player's first level-1 kill buys back 1%: the 75-XP "
          "counter was fed the 100 paid (a 26 took three kills)",
          f"morale {st['morale']}")

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


def section_tick(authsrv):
    import morale
    print("\n5. the 75-XP tick (RANGERPRE-S7): since the load, at neutral too, "
          "ahead of the award")
    P = authsrv.PLAYER_AGENT_ID
    MOR, ATTR = authsrv.GAME_SMSG_AGENT_MORALE, authsrv.GAME_SMSG_PLAYER_ATTR_UPDATE
    PINT, PFLT = (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT)
    STATUS, FLAGS = (authsrv.GAME_SMSG_AGENT_UPDATE_STATUS,
                     authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS)
    XP = authsrv.GAME_SMSG_AGENT_KILL_REWARD

    def shape(sent):
        """The frame as (op, values) with the status and flags values elided
        and the 0x00EE delta read signed; 0x00A2 [43] as (op, 43)."""
        out = []
        for op, v in sent:
            if op in (STATUS, FLAGS):
                out.append((op,))
            elif op == PFLT:
                out.append((op, v[0]))
            elif op == ATTR and v[0] == authsrv.PLAYER_ATTR_MORALE_ID:
                out.append((op, [v[0], _s32(v[1])]))
            else:
                out.append((op, list(v)))
        return out

    check(morale.crossings(0, 74) == 0 and morale.crossings(0, 75) == 1
          and morale.crossings(74, 1) == 1 and morale.crossings(1012, 176) == 2
          and morale.crossings(250, 26) == 0 and morale.crossings(881, 26) == 1
          and morale.crossings(425, 2000) == 27 and morale.crossings(10, -5) == 0,
          "crossings: multiples of 75 passed -- 881 -> 907 crosses one "
          "(:55934 383.573), 250 -> 276 none (264.333), 425 -> 2425 twenty-seven "
          "(:60877 736.185), a negative gain none")
    check(morale.recover(85, 1) == 86 and morale.recover(90, 27) == 100
          and morale.recover(100, 3) == 100 and morale.recover(105, 1) == 105
          and morale.recover(40, 0) == 40,
          "recover: +1 per crossing, capped at neutral (90 + 27 -> 100, the "
          "wire's [10, 10]); at or above neutral nothing moves")

    tapes = [(c, mp, lx, _tape(s)) for c, mp, lx, s in TICK_TAPES]
    awards = [(x, t) for _c, _m, _l, tp in tapes for x, t in tp if x != "died"]
    n_tick = sum(1 for _x, t in awards if t is not None)
    n_disc = sum(1 for x, _t in awards if x < 75)
    check(len(awards) == 68 and n_tick == 43 and n_disc == 36
          and len({c.split()[0] for c, *_ in TICK_TAPES}) == 8,
          "the pinned corpus: 68 PvE awards in 17 connections of 8 captures, 43 "
          "carrying the tick, 36 of them under 75 (the ones that discriminate)",
          f"{len(awards)} awards, {n_tick} ticks, {n_disc} under 75")

    def arm(rule):
        """How many of the 68 awards a counter rule reproduces (tick or not)."""
        hit = disc = 0
        for _c, _mp, lx, tp in tapes:
            since, total, bank, mor = 0, int(lx), 0, morale.BASELINE
            for x, t in tp:
                if x == "died":
                    mor = t
                    continue
                if rule == "since":
                    pred = morale.crossings(since, x) > 0
                elif rule == "total":
                    pred = morale.crossings(total, x) > 0
                else:
                    _m, bank, rec = morale.experience_credit(mor, bank, x)
                    pred = rec > 0
                hit += pred == (t is not None)
                disc += x < 75 and pred == (t is not None)
                since, total = since + x, total + x
                if t is not None:
                    mor = t[0]
        return hit, disc

    got, disc = arm("since")
    check(got == 68 and disc == 36,
          "the SINCE-LOAD counter (0 at the instance's load, fed by every award "
          "paid, not reset by a death) predicts tick-or-silence on 68 of 68, and "
          "36 of the 36 awards under 75", f"{got}/68, {disc}/36")
    got, _d = arm("total")
    check(got == 58,
          "KNOWN-BAD ARM: the character's TOTAL experience (0x00E9 field 0 at the "
          "load, plus the awards) fits 58 of 68 -- :55934 264.333's 350 -> 376 "
          "crosses 375 and retail sends no tick", f"{got}/68")
    got, _d = arm("bank")
    check(got == 20,
          "KNOWN-BAD ARM: the pre-S7 bank (morale.experience_credit: counts from "
          "the death, silent at neutral) fits 20 of 68", f"{got}/68")

    # OUR SERVER, replayed over the same awards: the deaths set morale from the
    # tape's own 0x009C, each award goes through morale_experience, and what
    # went on the wire must be retail's (m, d) -- or nothing.
    bad, ticks_ok = [], 0
    for cite, mp, _lx, tp in tapes:
        st = {"level": 1, "map_id": mp}
        for x, t in tp:
            if x == "died":
                st["morale"] = t
                continue
            sent = []
            authsrv.morale_experience(
                lambda op, v, label="", quiet=False: sent.append((op, list(v))),
                st, 0, x)
            m = [v[1] for op, v in sent if op == MOR and v[0] == P]
            d = [_s32(v[1]) for op, v in sent
                 if op == ATTR and v[0] == authsrv.PLAYER_ATTR_MORALE_ID]
            ours = (m[0], d[0]) if (len(m), len(d)) == (1, 1) else (
                None if not (m or d) else ("malformed", m, d))
            if ours != t:
                bad.append((cite, x, t, ours))
            elif t is not None:
                ticks_ok += 1
    check(not bad and ticks_ok == 43,
          "OUR morale_experience, replayed over each connection, puts retail's "
          "0x009C [player, m] + 0x00EE [10, d] on all 43 ticking awards (36 of "
          "them [100] + [10, 0] at neutral, +1 six times, +10 once) and nothing "
          "on the other 25", f"{ticks_ok}/43 ticks; misses {bad[:6]}")

    # kill_agent: three level-0 kills at L1, 25 each -- 25, 50, 75 (:60877's shape)
    st = _state(1, 1, 212)
    frames = [shape(_kill(authsrv, st, _foe(0))) for _ in range(3)]
    quiet = [(STATUS,), (XP, [0, 25]), (FLAGS,)]
    check(frames[0] == quiet and frames[1] == quiet
          and frames[2] == [(STATUS,), (MOR, [P, 100]), (ATTR, [10, 0]),
                            (XP, [0, 25]), (FLAGS,)],
          "three 25s: no tick, no tick, and the tick AHEAD of the third award "
          "(the counter reaches 75) -- a neutral tick carries no maxima",
          str(frames))

    # a recovery: 85 -> 86 moves health (86) and not energy (22), so the 42
    # rides the tick and 41 / 43 do not (:60877 634.715: 9C, EE10, 42, EE0)
    got = shape(_kill(authsrv, _state(1, 1, 146, morale=85), _foe(1)))
    check(got == [(STATUS,), (MOR, [P, 86]), (ATTR, [10, 1]),
                  (PINT, [agents.PROP_HEALTH_MAX, P, 86]), (XP, [0, 100]), (FLAGS,)],
          "a recovery from 85: 0x009C [player, 86], [10, 1], 0x009F [42, player, "
          "86], THEN the award -- no 41 / 43, the energy maximum did not move",
          str(got))
    got = shape(_kill(authsrv, _state(1, 1, 146, morale=87), _foe(1)))
    check(got == [(STATUS,), (MOR, [P, 88]), (ATTR, [10, 1]),
                  (PINT, [agents.PROP_ENERGY_MAX, P, 23]),
                  (PFLT, agents.PROP_ENERGY_REGEN),
                  (PINT, [agents.PROP_HEALTH_MAX, P, 88]), (XP, [0, 100]), (FLAGS,)],
          "87 -> 88 moves the energy maximum (22 -> 23): 41 and 0x00A2 43 ride "
          "the tick ahead of the 42 (:60877 675.898's order)", str(got))

    # heroes: after the award, on their own counter; a henchman never ticks
    H = authsrv.HERO_AGENT_ID

    def body(hero):
        return {"name": "h", "dead": False, "allegiance": agents.ALLEGIANCE_PLAYER,
                "hero": hero, "health": 100.0, "max_health": 100.0,
                "base_max_health": 100.0, "base_max_energy": 20.0,
                "pos": (100.0, 0.0)}

    st = _state(1, 1, 146, agents={H: body(6), 201: body(None)})
    got = shape(_kill(authsrv, st, _foe(1)))
    check(got == [(STATUS,), (MOR, [P, 100]), (ATTR, [10, 0]), (XP, [0, 100]),
                  (MOR, [H, 100]), (FLAGS,)],
          "a hero ticks BEHIND the award -- 0x009C [hero, 100] alone at neutral "
          "(20260914T005758 :56011 238.177) -- and the henchman beside it does not",
          str(got))
    st = _state(1, 1, 146, agents={H: body(6)}, hero_morale={H: 85})
    got = shape(_kill(authsrv, st, _foe(1)))
    check(got == [(STATUS,), (MOR, [P, 100]), (ATTR, [10, 0]), (XP, [0, 100]),
                  (MOR, [H, 86]), (PINT, [agents.PROP_HEALTH_MAX, H, 86]), (FLAGS,)],
          "a penalised hero: 0x009C [hero, 86] and its 0x009F [42, hero, 86] "
          "behind the award (:56011 410.841)", str(got))

    # the quest frame: the tick ahead of the xp, the gold behind it
    gold = authsrv.merchant.GAME_SMSG_GOLD_CREDIT
    sent = []
    authsrv.grant_quest_reward(
        lambda op, v, label="", quiet=False: sent.append((op, list(v))),
        {"quests": set(), "agents": {}}, 1463,
        {"reward_experience": 250, "reward_gold": 25}, 0)
    got = shape(sent)
    check(got == [(MOR, [P, 100]), (ATTR, [10, 0]), (XP, [0, 250]),
                  (gold, [authsrv.PLAYER_INVENTORY_KEY, 25])],
          "a hand-in: 0x009C [player, 100], [10, 0], [0, 250], then the gold -- "
          "the tick ahead of the xp on 20 of 20 retail hand-ins", str(got))
    sent = []
    authsrv.grant_quest_reward(
        lambda op, v, label="", quiet=False: sent.append((op, list(v))),
        {"quests": set(), "agents": {}, "morale": 90, "xp_since_load": 425},
        347, {"reward_experience": 2000}, 0)
    got = shape(sent)
    check(got == [(MOR, [P, 100]), (ATTR, [10, 10]),
                  (PINT, [agents.PROP_ENERGY_MAX, P, 25]),
                  (PFLT, agents.PROP_ENERGY_REGEN),
                  (PINT, [agents.PROP_HEALTH_MAX, P, 100]), (XP, [0, 2000])],
          "2000 from 90 with 425 since the load: [player, 100], [10, 10], the "
          "maxima, then [0, 2000] -- 20260913T210901 :60877 736.185's order",
          str(got))


def main():
    import authsrv
    section_rule()
    section_witnesses(authsrv)
    section_our_frame(authsrv)
    section_flags(authsrv)
    section_tick(authsrv)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
