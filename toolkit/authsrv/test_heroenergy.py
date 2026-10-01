r"""test_heroenergy -- a hero's energy is its own and its panel is told it: the armour
rule's pips and maximum, and a spend word behind every paid cast (HEROENERGY,
2026-10-01; PLAN-LOG "HEROENERGY").

WHAT IT IS REALLY CHECKING. The owner, watching the healer rig's hero panels: "heroes
don't actually spend energy when casting, and Monks are supposed to have 4 pips of
energy regen, not 2. i think the extra regen comes from armor". Both were true. The
cast path debited a hero's pool and sent nothing, so the panel sat at 30; the hero's
property 43 was the PLAYER's rate scaled to the hero's maximum (2 pips, the player
being a Warrior) while the server's pool was the HOSTILE default (30, 5 pips). Retail
(20260914T005758): Koss's 5-energy skill 346 was E4, [62, Koss, -cost/max], E5 -- 17
of 17 -- and his 43 was 2 pips over his own 20. The page (GWW "Energy") gives the
armour rule: 20 and 2 pips innate, the basic armour the rest; a Monk 30 / 4.

  1  the armour rule (pools.PROFESSION_ENERGY): Monk 30 / 4, Warrior 20 / 2, Ranger
     25 / 3, Assassin 25 / 4, Paragon 30 / 2 -- and the sandbox's table IS it.
  2  a hero body's pool: its own maximum, its profession's pips, the wire's rate; a
     henchman keeps the hostile pool; the KNOWN-BAD arm gives the hero 30 / 5.
  3  the load block's property 43 for a Monk hero is 4 pips over its 30 -- the pool's
     own rate; the known-bad arm sends the player's.
  4  the REAL ally_cast_tick: a Monk hero's Orison sends [62, hero, -5/30] right
     behind its E4 and the pool pays 5; a henchman's cast sends no [62]; the
     known-bad arm (--no-hero-spend-word) sends none.
  5  a party body's paid ATTACK skill held by its swing clock pays nothing (the debit
     sat ahead of the gate and charged every tick it waited).
  6  the switches' wiring.
  7  RETAIL (vault): Koss's [62] after each 346 is -5 over his [41], 17 of 17; the
     observer's modal pips per profession match the rule (W 2, R 3, Me 4, A 4).
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
import pools                                                   # noqa: E402

# Floor from the BARE-MACHINE green run of 2026-10-01 (RURIK_VAULT at an empty
# directory): 7 -- sections 1, 2 and 6; sections 3-5 need the vault's attribute and
# skill tables and section 7 its captures, and each declares a skip. 16 with the
# vault. Both switches off in the source redden 5; the swing-clock gate moved back
# behind the debit reddens section 5's one.
LEDGER = checks.Ledger("hero energy", floor=7)
check = checks.adopt(LEDGER)

E4 = 0x00E4
FLOAT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
ORISON, GASH = 281, 322
MONK, WARRIOR = 3, 1


class Wire:
    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals), label))


def _body(aid, hero=None, prof=MONK, emax=30.0, skills=(), pos=(0.0, 0.0), health=480.0):
    row = {"name": "Academy Monk", "dead": False, "died_at": 0.0, "health": health,
           "max_health": 480.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0, "attacks_back": False,
           "attack_speed": 1.75, "skills": authsrv.bar_triples(skills),
           "skill_ready": [0.0] * len(skills), "npc": {"profession": prof, "level": 20},
           "attributes": {13: 12, 17: 12}, "party_slot": 0, "base_max_energy": emax}
    if hero is not None:
        row.update(hero=hero, max_energy=emax, energy_profession=prof)
    return row


def _skills_known():
    """Does this machine's skill table carry the two skills' cost and timing?"""
    try:
        return all(agents.WORLD.get("skills", str(k)).get("energy") for k in (ORISON, GASH))
    except Exception:                                            # noqa: BLE001
        return False


def _f(u):
    return struct.unpack("<f", struct.pack("<I", int(u) & 0xFFFFFFFF))[0] \
        if isinstance(u, int) else float(u)


def section_rule():
    print("== 1. the armour rule ==")
    pe = pools.PROFESSION_ENERGY
    check(pe[3] == (30, 4) and pe[1] == (20, 2) and pe[2] == (25, 3) and pe[7] == (25, 4)
          and pe[9] == (30, 2) and pe[10] == (25, 4)
          and all(pe[p] == (30, 4) for p in (4, 5, 6, 8)),
          "20 energy and 2 pips innate plus the basic armour's (GWW \"Energy\"): a Monk "
          "30 / 4, a Warrior 20 / 2, a Ranger 25 / 3, an Assassin 25 / 4, a Paragon 30 / 2",
          f"{pe}")
    try:
        sys.path.insert(0, os.path.join(PARENT, "harness"))
        import sandbox
        same = sandbox.ENERGY_BY_PROFESSION == dict(pe)
    except Exception as exc:                                     # noqa: BLE001
        same = f"sandbox did not import: {exc}"
    check(same is True,
          "and the sandbox's defaults are that table -- one source (its Paragon read "
          "25 / 3 from memory until the page was read)", f"{same}")


def section_pool():
    print("== 2. a hero body's pool ==")
    monk = _body(200, hero=3, prof=MONK, emax=30.0)
    pool = authsrv.agent_energy(monk)
    check(pool.maximum == 30.0 and pool.pips == 4
          and pool.rate == pools.wire_regen_rate(4, 30.0),
          "a Monk hero's pool fills to its own 30 at 4 pips, at the wire's own rate",
          f"max {pool.maximum}, pips {pool.pips}, rate {pool.rate}")
    war = _body(201, hero=6, prof=WARRIOR, emax=17.0)
    wp = authsrv.agent_energy(war)
    check(wp.maximum == 17.0 and wp.pips == 2,
          "a Warrior hero at a 17 maximum (morale) runs 2 pips -- Koss's own 43 on retail",
          f"max {wp.maximum}, pips {wp.pips}")
    hench = _body(202, hero=None, prof=MONK)
    hp = authsrv.agent_energy(hench)
    check(hp.maximum == authsrv.ENEMY_ENERGY and hp.pips == authsrv.ENEMY_ENERGY_PIPS,
          "a HENCHMAN keeps the server's NPC pool -- its pools are never on the wire",
          f"max {hp.maximum}, pips {hp.pips}")
    saved = authsrv.HERO_ENERGY_BY_PROFESSION
    authsrv.HERO_ENERGY_BY_PROFESSION = False
    try:
        bad = authsrv.agent_energy(_body(203, hero=3, prof=MONK, emax=30.0))
        check(bad.pips == authsrv.ENEMY_ENERGY_PIPS,
              "KNOWN-BAD (--hero-energy-enemy-pool): the Monk hero regenerates at the "
              "hostile 5 pips -- the server's half of the three-way disagreement",
              f"pips {bad.pips}")
    finally:
        authsrv.HERO_ENERGY_BY_PROFESSION = saved


def _block_43(state, hid=3):
    blk = authsrv.hero_character_block(state, 200, hid)
    w43 = [v for op, v, _l in blk if op == FLOAT and v[0] == authsrv.GV_ENERGY_REGEN]
    w41 = [v for op, v, _l in blk if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
           and v[0] == agents.PROP_ENERGY_MAX]
    return w43, w41


def section_load_word():
    print("== 3. the load block's property 43 ==")
    if not agents.WORLD.rows("attribute"):
        # The block builds the hero's attribute state, whose cost curve is the
        # vault's extraction (attribpoints.py --emit-content); refused, not faked.
        LEDGER.skip("the hero load block's 43", "no attribute cost rows on this machine")
        return
    saved = {k: getattr(authsrv, k) for k in ("hero_profession", "hero_vitals", "HERO_IDS",
                                              "HERO_ENERGY_BY_PROFESSION")}
    try:
        authsrv.hero_profession = lambda hid: MONK
        authsrv.hero_vitals = lambda hid: (480, 30)
        authsrv.HERO_IDS = [3]
        w43, w41 = _block_43({"agents": {}})
        want = authsrv._f32(pools.wire_regen_rate(4, 30.0))
        check(len(w43) == 1 and w43[0][2] == want and w41 and w41[0][2] == 30,
              "a Monk hero's block says energy max 30 and regeneration 4 pips over it -- "
              "the pool's own rate (the panel's >>>>)",
              f"43 {w43}, 41 {w41}, want {want} ({_f(want):.5f})")
        authsrv.HERO_ENERGY_BY_PROFESSION = False
        b43, _b41 = _block_43({"agents": {}})
        check(len(b43) == 1 and b43[0][2] != want,
              "KNOWN-BAD: the player's rate scaled to the hero's 30 -- the 2 pips the "
              "owner's panel showed", f"43 {b43}")
    finally:
        for k, v in saved.items():
            setattr(authsrv, k, v)


def _cast_world(hero=3):
    caster = _body(200, hero=hero, prof=MONK, emax=30.0, skills=(ORISON,))
    hurt = _body(201, hero=None, pos=(120.0, 0.0), health=200.0)
    return {"agents": {200: caster, 201: hurt}, "pos": (0.0, 60.0),
            "player_health": 1000.0, "player_dead": False}


def section_spend():
    print("== 4. the spend word, through the real ally_cast_tick ==")
    if not _skills_known():
        LEDGER.skip("the hero spend word", "the skill table has no cost row for 281 / 322 here")
        return
    st = _cast_world()
    w = Wire()
    before = authsrv.agent_energy(st["agents"][200]).current
    authsrv.ally_cast_tick(w, st, 1)
    ops = [(op, v) for op, v, _l in w.sent]
    i4 = next((i for i, (op, v) in enumerate(ops) if op == E4 and v[:2] == [200, ORISON]), None)
    want = authsrv._fraction(pools.spend_fraction(5, 30.0), agents.GV_ENERGY_SPENT, "test")
    nxt = ops[i4 + 1] if i4 is not None and i4 + 1 < len(ops) else None
    check(nxt is not None and nxt[0] == FLOAT and nxt[1] == [agents.GV_ENERGY_SPENT, 200, want],
          "a Monk hero's Orison: E4, then [62, hero, -5/30] right behind it -- retail's "
          "[E4, 62, E5] (Koss, 17 of 17)",
          f"E4 at {i4}, next {nxt}, want {want} ({_f(want):.4f})")
    after = authsrv.agent_energy(st["agents"][200]).current
    check(abs((before - after) - 5.0) < 0.2,
          "and the server's pool paid the same 5 -- the word and the book agree",
          f"{before:.2f} -> {after:.2f}")
    st = _cast_world(hero=None)
    w = Wire()
    authsrv.ally_cast_tick(w, st, 1)
    casts = [v for op, v, _l in w.sent if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
             and v[0] == agents.GV_SKILL_ACTIVATED]
    check(casts and not [1 for op, v, _l in w.sent if op == FLOAT and v[0] == agents.GV_ENERGY_SPENT],
          "a HENCHMAN's Orison casts and sends no [62] (0 on any henchman in the corpus)",
          f"casts {casts}")
    saved = authsrv.HERO_SPEND_WORD
    authsrv.HERO_SPEND_WORD = False
    try:
        st = _cast_world()
        w = Wire()
        authsrv.ally_cast_tick(w, st, 1)
        check([1 for op, v, _l in w.sent if op == E4]
              and not [1 for op, v, _l in w.sent if op == FLOAT and v[0] == agents.GV_ENERGY_SPENT],
              "KNOWN-BAD (--no-hero-spend-word): the cast goes out and the panel is never "
              "told -- the owner's \"heroes don't actually spend energy\"", "")
    finally:
        authsrv.HERO_SPEND_WORD = saved


def section_attack_clock():
    print("== 5. an attack skill held by the swing clock pays nothing ==")
    if not _skills_known():
        LEDGER.skip("the attack skill's clock", "the skill table has no cost row for 281 / 322 here")
        return
    foe = {"name": "Bandit Raider", "dead": False, "health": 3000.0, "max_health": 3000.0,
           "pos": (60.0, 0.0), "plane": 0, "allegiance": agents.ALLEGIANCE_HOSTILE,
           "effects": 0, "attacks_back": True, "skills": (), "skill_ready": [],
           "npc": {"level": 10, "profession": 1}, "last_hit": 0.0, "died_at": 0.0}
    war = _body(200, hero=6, prof=WARRIOR, emax=20.0, skills=(GASH,))
    war["last_swing"] = time.time()                 # the clock holds the next swing
    st = {"agents": {200: war, 110: foe}, "pos": (0.0, 60.0), "player_health": 1000.0,
          "player_dead": False}
    saved = authsrv.party_fight_target
    authsrv.party_fight_target = lambda state, aid, agent, now: 110
    try:
        before = authsrv.agent_energy(war).current
        for _ in range(5):
            authsrv.ally_cast_tick(Wire(), st, 1)
        after = authsrv.agent_energy(war).current
    finally:
        authsrv.party_fight_target = saved
    check(authsrv._is_attack_skill(GASH) and after >= before - 1e-6,
          "five ticks of a 5-energy attack skill waiting on the swing clock cost the "
          "hero nothing -- it pays when the swing goes ahead, once",
          f"{before:.2f} -> {after:.2f}")


def section_wiring():
    print("== 6. the switches ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check(authsrv.HERO_SPEND_WORD is True and authsrv.HERO_ENERGY_BY_PROFESSION is True
          and '"--no-hero-spend-word"' in args and '"--hero-energy-enemy-pool"' in args
          and "if a.no_hero_spend_word:" in src and "if a.hero_energy_enemy_pool:" in src,
          "both ship ON; --no-hero-spend-word and --hero-energy-enemy-pool revert them", "")


def section_retail():
    print("== 7. retail: Koss's spends, and the observer's pips ==")
    try:
        import livewire
        import henchjoin
        root = livewire.captures_root()
    except Exception as exc:                                    # pragma: no cover
        LEDGER.skip("the retail energy census", f"livewire unavailable: {exc}")
        return
    if not root or not os.path.isdir(root):
        LEDGER.skip("the retail energy census", "no live captures on this machine")
        return
    spends, bad, pips = 0, [], collections.defaultdict(collections.Counter)
    for capdir, gf in livewire.live_connections():
        _c, merged, _ok = livewire.decode_conn(capdir, gf)
        if not merged:
            continue
        me = henchjoin.whose_agent(merged)
        heroes = {int(v[3]) for t, d, op, v in merged if d == "s2c" and op == 0x01C2 and len(v) > 3}
        prof, mx = {}, {}
        for i, (t, d, op, v) in enumerate(merged):
            if d != "s2c" or len(v) < 3:
                continue
            if op == 0x00A6:
                prof[int(v[1])] = int(v[2])
            elif op == 0x009F and int(v[1]) == 41 and len(v) > 3:
                mx[int(v[2])] = int(v[3])
            elif op == 0x00A2 and int(v[1]) == 43 and len(v) > 3 and v[2] == me \
                    and me in mx and me in prof and _f(v[3]) > 0:
                pips[prof[me]][round(_f(v[3]) * mx[me] / pools.PIP_ENERGY_PER_SECOND)] += 1
            elif op == E4 and v[1] in heroes and int(v[2]) == 346:
                stamp = [(o2, w2) for (t2, d2, o2, w2) in merged[i + 1:i + 6]
                         if d2 == "s2c" and abs(t2 - t) <= 0.003]
                got = next((w2 for o2, w2 in stamp if o2 == 0x00A2 and w2[1] == 62
                            and w2[2] == v[1]), None)
                exp = pools.f32(pools.spend_fraction(5, mx.get(int(v[1]), 0) or 1))
                if got is not None and abs(_f(got[3]) - exp) < 1e-6 \
                        and stamp and stamp[0][0] == 0x00A2:
                    spends += 1
                else:
                    bad.append((os.path.basename(capdir), round(t, 2), got, exp))
    check(spends >= 17 and not bad,
          "Koss's 346: the E4 is followed AT ONCE by [62, Koss, -5 / his 41], 17 of 17 "
          "-- the word this fix sends, its value and its place",
          f"{spends} good, bad {bad[:3]}")
    modal = {p: c.most_common(1)[0][0] for p, c in pips.items() if c}
    want = {p: pools.PROFESSION_ENERGY[p][1] for p in modal}
    check(len(modal) >= 4 and modal == want,
          "the observer's modal pips per profession are the armour rule's "
          "(W 2, R 3, Me 4, A 4 on the corpus)", f"modal {modal}, rule {want}, all {dict(pips)}")


def main():
    section_rule()
    section_pool()
    section_load_word()
    section_spend()
    section_attack_clock()
    section_wiring()
    section_retail()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
