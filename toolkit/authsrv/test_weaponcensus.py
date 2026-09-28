"""test_weaponcensus.py -- what every body holds, and how it attacks with it.

Section 1 is a SYNTHETIC wire with every answer known by construction, including the
things the census must NOT do: count a skill's projectile as a weapon shot, score a gap
that straddles a weapon swap, read a modifier word the client's own walker skips, or
call a wrong projectile a match. Section 2 is the vault: the numbers
studies/weapons/PLAN.md section 3 was written from, pinned as floors and signatures
(never exact corpus counts -- those redden on confirming evidence). Section 2 SKIPS,
printed, on a bare machine.
"""
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import weaponcensus as wc  # noqa: E402

LEDGER = checks.Ledger("weaponcensus: held weapon types, swings and shots", floor=20)   # the BARE-MACHINE number: 20 without the vault (section 2 skips), 46 with it; from green runs (WEAPONS-W2c: 16 -> 20; CASTAI-Z1 2026-09-28: 38 -> 46 with the vault, the pin-scoped literals plus their signatures)
check = LEDGER.ok

ME, WANDER, ARCHER, LIAR, FOE = 7, 51, 50, 52, 9
BOW, WAND, SWORD, NPC_BOW = 100, 101, 102, 103


def f32(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def word(ident, arg=0, arg2=0, skipped=False):
    return (ident << 20) | (1 << 19) | ((1 << 18) if skipped else 0) | (arg << 8) | arg2


def item(item_id, typ, words):
    return (0.1, wc.ITEM, [wc.ITEM, item_id, 9000 + item_id, typ, 0, 0, 0, 0, 0, 0,
                           7000 + item_id, 1, "", [[w] for w in words]])


def wire():
    s = [item(BOW, 5, [word(633, 25, 9), word(609, 3), word(617, 0, 143),
                       word(584, 28, 15), word(587, 1), word(617, 0, 77, skipped=True)]),
         item(WAND, 22, [word(617, 0, 2), word(587, 5)]),
         item(SWORD, 27, [word(633, 20, 9), word(587, 2)]),
         item(NPC_BOW, 28, [word(609, 0), word(587, 1)]),
         (0.2, wc.PLAYER_HANDS, [wc.PLAYER_HANDS, ME, BOW, 0, 1, 2, 3, 4, 5]),
         (0.2, wc.HANDS, [wc.HANDS, WANDER, WAND, 0]),
         (0.2, wc.HANDS, [wc.HANDS, ARCHER, NPC_BOW, 0]),
         (0.2, wc.HANDS, [wc.HANDS, LIAR, WAND, 0]),
         (50.0, wc.PLAYER_HANDS, [wc.PLAYER_HANDS, ME, SWORD, 0, 1, 2, 3, 4, 5]),
         (1.0, wc.SPEED, [wc.SPEED, ME, f32(2.475), f32(1.0)]),
         (50.5, wc.SPEED, [wc.SPEED, ME, f32(1.33), f32(0.67)]),
         (1.0, wc.SPEED, [wc.SPEED, 999, f32(2.0), f32(1.0)])]
    handle = [0]

    def shot(agent, t0, windup, flight, f5, f7, target=FOE, arrive=True):
        handle[0] += 1
        s.append((t0, wc.PINT_T, [wc.PINT_T, wc.START, agent, target, 0]))
        s.append((t0 + windup, wc.LAUNCH, [wc.LAUNCH, agent, (1.0, 2.0), 0, f32(flight),
                                           f5, handle[0], f7]))
        if arrive:
            s.append((t0 + windup + flight, wc.ARRIVE,
                      [wc.ARRIVE, agent, handle[0], 1 if f7 else 5]))
        s.append((t0 + windup + flight, wc.PFLOAT_T,
                  [wc.PFLOAT_T, 16, target, agent, f32(-0.05)]))

    for t0 in (1.0, 3.475, 5.95, 8.425):                     # the player's bow, 2.475 s
        shot(ME, t0, 1.1375, 0.4, 143, 1)
    # a bow ATTACK SKILL: activation, then its own launch -- never a weapon shot
    s.append((20.0, wc.PINT_T, [wc.PINT_T, wc.START, ME, FOE, 0]))
    s.append((20.1, wc.E4, [wc.E4, ME, 343, 0]))
    s.append((21.0, wc.LAUNCH, [wc.LAUNCH, ME, (1.0, 2.0), 0, f32(0.3), 343, 99, 0]))
    # WEAPONS-W2c: a player's Power Shot -- E5, launch, E3 in ONE instant -- and a
    # body's announced one, its launch a bow windup later; neither carries a 46
    s.append((30.0, wc.E5, [wc.E5, ME, 394, 0, 3]))
    s.append((30.0, wc.LAUNCH, [wc.LAUNCH, ME, (1.0, 2.0), 0, f32(0.25), 680, 1, 1]))
    s.append((30.0, wc.E3, [wc.E3, ME, 394, 0]))
    s.append((30.25, wc.ARRIVE, [wc.ARRIVE, ME, 1, 1]))
    s.append((30.25, wc.PFLOAT_T, [wc.PFLOAT_T, 16, FOE, ME, f32(-0.05)]))
    s.append((40.0, wc.PINT_T, [wc.PINT_T, 50, ARCHER, ME, 394]))
    s.append((41.1375, wc.LAUNCH, [wc.LAUNCH, ARCHER, (1.0, 2.0), 0, f32(0.3), 680, 1, 1]))
    s.append((41.4375, wc.ARRIVE, [wc.ARRIVE, ARCHER, 1, 1]))
    s.append((41.4375, wc.PFLOAT_T, [wc.PFLOAT_T, 16, ME, ARCHER, f32(-0.05)]))
    # a swing either side of the swap: the gap is neither weapon's
    s.append((49.5, wc.PINT_T, [wc.PINT_T, wc.START, ME, FOE, 0]))
    for t0 in (50.5, 51.833, 53.166, 54.499):                # the sword, 1.333 s
        s.append((t0, wc.PINT_T, [wc.PINT_T, wc.START, ME, FOE, 0]))
    for t0 in (1.0, 2.75, 4.65, 6.40, 8.15):                 # a wand: 1.75, 1.90, 1.75, 1.75
        shot(WANDER, t0, 0.775, 0.2, 2, 0, target=ME)
    for t0 in (1.0, 2.75, 4.5):                              # a hostile bow with NO 617
        shot(ARCHER, t0, 0.775, 0.3, 143, 1, target=ME)
    shot(LIAR, 1.0, 0.775, 0.2, 5, 0, target=ME, arrive=False)   # holds 2, shoots 5
    s.sort(key=lambda r: r[0])
    return s


def near(a, b, tol=1e-6):
    return a is not None and abs(a - b) < tol


def section_synthetic():
    print("\n1. a synthetic wire, every answer known by construction")
    s2c = wire()
    items = wc.items_of(s2c)
    check(items[BOW]["type"] == 5 and items[BOW]["model"] == 7000 + BOW
          and wc.word_of(items, BOW, 633) == (25, 9) and wc.word_of(items, BOW, 609) == (3, 0),
          "an item's type, model and words: 633 is (attribute, rank), 609 rides arg")
    check(wc.word_of(items, BOW, 617) == (0, 143) and len(items[BOW]["words"]) == 5,
          "a word with bit 18 set is SKIPPED, as the client's own walker skips it -- "
          "the bow's projectile is 143, not the decoy 77", str(items[BOW]["words"]))
    check(wc.word_fields(0xC0000000) is None and wc.word_fields(word(584, 28, 15)) == (584, 28, 15),
          "and so is a word with bits 31-30 set (the terminator's shape)")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
        import itemmods                                         # noqa: PLC0415
        d = itemmods.decode(0xA4880503)
        check(wc.word_fields(0xA4880503) == (d["identifier"], d["arg"], d["arg2"]) == (584, 5, 3),
              "the local decode agrees with clientscan/itemmods on the hammer's own word")
    except Exception as exc:                                    # noqa: BLE001
        LEDGER.skip("itemmods agreement", f"clientscan/itemmods not importable: {exc!r} -- 1 check")

    hands = wc.hands_timeline(s2c)
    check(wc.held_at(hands, ME, 10.0) == (BOW, 0) and wc.held_at(hands, ME, 60.0) == (SWORD, 0)
          and wc.held_at(hands, WANDER, 0.0) == (WAND, 0) and wc.held_at(hands, 999, 1.0) is None,
          "hands are a TIMELINE: a player's 0x006E and an NPC's 0x006D, the swap honoured, "
          "a body the tape never names is None")
    lead, off, words = wc.types_census(s2c)
    check(lead == {5: 1, 27: 1, 22: 2, 28: 1} and off == {0: 5} and 617 in words[22]
          and 617 not in words[28],
          "types in hands, one count per HOLDING", f"{dict(lead)} {dict(off)}")

    spd = {(r["agent"], r["type"]): (r["base"], r["modifier"], r["w609"])
           for r in wc.speeds(s2c)}
    check(spd == {(ME, 5): (2.475, 1.0, 3), (ME, 27): (1.33, 0.67, None),
                  (999, None): (2.0, 1.0, None)},
          "0x0035's base and modifier, joined to the type held WHEN IT WAS SENT -- the "
          "bow's with its 609, the sword's after the swap, an unnamed body's as None",
          str(spd))
    att = {(r["agent"], r["lead"]): r for r in wc.attackers(s2c)}
    check(set(att) == {(ME, BOW), (ME, SWORD), (WANDER, WAND)},
          "attackers are (body, weapon) pairs; two swings are not three gaps",
          str(sorted(att)))
    check(near(att[(ME, BOW)]["mode"], 2.475) and len(att[(ME, BOW)]["gaps"]) == 3
          and att[(ME, BOW)]["type"] == 5,
          "the bow's interval -- the gap a SKILL sits in is left out")
    check(near(att[(ME, SWORD)]["mode"], 1.333) and len(att[(ME, SWORD)]["gaps"]) == 3,
          "the sword's -- and the gap that STRADDLES the swap is neither weapon's",
          str(att[(ME, SWORD)]["gaps"]))
    check(near(att[(WANDER, WAND)]["mode"], 1.75) and att[(WANDER, WAND)]["n_mode"] == 3
          and len(att[(WANDER, WAND)]["gaps"]) == 4,
          "a hostile's gaps are a MIXTURE: the mode is the densest cluster, 1.75 x3, "
          "not the mean that the 1.90 drags")

    sho = {r["agent"]: r for r in wc.shooters(s2c)}
    me = sho[ME]
    check(me["shots"] == 4 and set(me["field5"]) == {143}
          and all(near(x, 1.1375) for x in me["start_to_launch"]),
          "a weapon shot is a launch behind a SWING start; the skill's 343 is not one",
          f"shots {me['shots']} field5 {dict(me['field5'])}")
    check(me["closed"] == 4 and len(me["word_error"]) == 4
          and all(abs(e) < 1e-6 for e in me["word_error"]),
          "each launch closed by its 0x00A7 handle, and launch + flight IS the word")
    check([wc.projectile_verdict(sho[a]) for a in (ME, WANDER, ARCHER, LIAR)]
          == ["field 5 == 617", "field 5 == 617", "weapon has no 617", "MISMATCH"],
          "0x00A4 field 5 against the held weapon's 617 -- and the check CAN fail: a body "
          "holding projectile 2 and shooting 5 is a MISMATCH",
          str([wc.projectile_verdict(sho[a]) for a in (ME, WANDER, ARCHER, LIAR)]))
    check(sho[LIAR]["closed"] == 0 and sho[ARCHER]["field7"] == {1: 3} and sho[WANDER]["field7"] == {0: 5},
          "an unclosed launch is counted unclosed; field 7 rides beside field 5")
    check([wc.arrival_verdict(sho[a]) for a in (ME, WANDER, ARCHER)]
          == ["kind == 587", "kind == 587", "kind == 587"]
          and wc.arrival_verdict(dict(sho[WANDER], arrival_kind={9: 5})) == "MISMATCH",
          "0x00A7's third field against the held weapon's 587 damage type (the bow's 1, "
          "the wand's 5) -- and a wand answering 9 is a MISMATCH")


def section_skill_shots():
    print("\n1b. WEAPONS-W2c: skill shots on the synthetic wire")
    rows = wc.skill_shots(wire())
    by = {(r["agent"], r["skill"]): r for r in rows}
    check(len(rows) == 3 and set(by) == {(ME, 343), (ME, 394), (ARCHER, 394)},
          "three SKILL shots and no weapon shot among them: the player's E4-then-launch "
          "(343), the player's Power Shot in its E5 batch and the archer's announced one",
          str(sorted(by)))
    me = by[(ME, 394)]
    check(me["player"] and me["event"] == "E5" and near(me["event_to_launch"], 0.0)
          and me["projectile"] == 680 and me["arrow"] == 1 and me["kind"] == 1
          and me["closed"] and near(me["word_error"], 0.0) and not me["close46"]
          and me["type"] == 5 and me["w617"] == 143,
          "the player's: E5->launch 0, projectile 680 with the BOW's flag 1 and kind 1, "
          "closed, the word at launch + flight, no 46, the held type and its own 617 beside")
    ar = by[(ARCHER, 394)]
    check(not ar["player"] and ar["event"] == "announce50"
          and near(ar["event_to_launch"], 1.1375) and ar["projectile"] == 680
          and ar["closed"] and not ar["close46"] and ar["type"] == 28,
          "the archer's: announced by [50], launched one 2.475 s windup later, closed, no 46")
    check(all(r["agent"] != ARCHER or r["skill"] == 394 for r in rows)
          and len([r for r in wc.shooters(wire()) if r["agent"] == ARCHER]) == 1
          and sum(r["shots"] for r in wc.shooters(wire()) if r["agent"] == ARCHER) == 3,
          "and the archer's three plain shots stay WEAPON shots in shooters(): the two "
          "censuses partition its launches")


def section_vault():
    print("\n2. the vault: the live corpus, floors and signatures")
    try:
        c = wc.corpus()
    except Exception as exc:                                    # noqa: BLE001
        c = None
        print(f"   (corpus unreadable: {exc!r})")
    if not c or not c["shooters"]:
        LEDGER.skip("section 2", "no live corpus -- 26 checks")
        return
    check({2, 5, 15, 22, 26, 27, 32, 35, 36}.issubset(c["lead"]) and {1, 28}.issubset(c["lead"])
          and {12, 24}.issubset(c["off"]),
          "nine player weapon types and the two hostile-only ones sit in leadhands; "
          "shields and foci in offhands", str(sorted(c["lead"], key=str)))
    check(633 not in c["words"][28] and 633 not in c["words"][1]
          and all(633 in c["words"][t] for t in (2, 5, 15, 22, 26, 27, 32)),
          "every player weapon type carries a 633 requirement somewhere; types 1 and 28 never")
    attr = {t: {a for (a, _r) in c["words"][t][633]} for t in (2, 5, 15, 27, 32)}
    check(attr == {2: {18}, 5: {25}, 15: {19}, 27: {20}, 32: {29}},
          "and 633's attribute is ONE per martial type: axe 18, bow 25, hammer 19, "
          "sword 20, daggers 29", str(attr))
    check(set(c["words"][5][609]) >= {(1, 0), (3, 0)} and len(c["words"][5][609]) == 5,
          "bows carry a five-valued 609", str(sorted(c["words"][5][609])))
    import agents                                               # noqa: PLC0415
    want = {27: "sword", 2: "axe", 32: "daggers", 15: "hammer", 26: "staff", 22: "wand"}
    got = {t: set(b for (typ, _w), bases in c["speeds"].items() if typ == t for b in bases)
           for t in want}
    check(all(got[t] == {agents.ATTACK_SPEED[k]} for t, k in want.items()),
          "two measurements, no literal: retail's 0x0035 base for each held type IS this "
          "server's [attack_speed.rates] row -- sword, axe, daggers, hammer, staff, wand",
          str(got))
    bows = {w: set(b) for (typ, w), b in c["speeds"].items() if typ == 5}
    check(bows and all(b == {agents.ATTACK_SPEED["longbow"]} for b in bows.values())
          and set(bows) <= {1, 3},
          "and every bow that attacked is a 2.475 -- 609 classes 1 and 3, so those two "
          "are the longbow and the recurve in some order", str(bows))
    sho = c["shooters"]
    shots = sum(r["shots"] for r in sho)
    check(len(sho) >= 60 and shots >= 450, "60+ ranged attackers, 450+ weapon shots",
          f"{len(sho)} / {shots}")
    verdicts = [wc.projectile_verdict(r) for r in sho]
    match, miss = verdicts.count("field 5 == 617"), verdicts.count("MISMATCH")
    check(match >= 35 and miss <= 0.05 * (match + miss),
          "WEAPONS-C3: 0x00A4 field 5 is the held weapon's own 617 argument",
          f"{match} match, {miss} mismatch")
    kinds = [wc.arrival_verdict(r) for r in sho]
    k_ok, k_bad = kinds.count("kind == 587"), kinds.count("MISMATCH")
    check(k_ok >= 50 and k_bad <= 0.05 * (k_ok + k_bad),
          "WEAPONS-C9: 0x00A7's third field is the held weapon's 587 damage type",
          f"{k_ok} match, {k_bad} mismatch")
    # RE-SCOPED 2026-09-28 (CASTAI-Z1), not loosened: the Zaishen capture's two bow
    # bodies shoot 742 and 343 under their PREPARATIONS (Apply Poison 435's own +0x88
    # and Kindle Arrows 433's), which a 90 % share cannot tell from a wrong arrow. The
    # 90 % stays exact on the captures it was pinned on; `_arrow_signature` below says
    # what every OTHER arrow is, launch by launch, over the whole corpus.
    bare = [r for r in sho if r["w617"] is None and r["type"] in (5, 28)
            and r["capture"] < PIN]
    arrows = [r for r in bare if set(r["field5"]) == {143}]
    check(len(bare) >= 20 and len(arrows) >= 0.9 * len(bare),
          f"and a bow with NO 617 word shoots 143 (the captures at the pin, before {PIN})",
          f"{len(arrows)} of {len(bare)}")
    short = [x for r in sho for x in r["start_to_launch"] if x < 1.0]
    long_ = [x for r in sho for x in r["start_to_launch"] if x >= 1.0]
    check(len(short) >= 400 and abs(wc._p50(short) - 0.775) < 0.005,
          "WEAPONS-C1: a 1.75 s weapon releases at swing_windup(1.75) = 0.775 s",
          f"n {len(short)} p50 {wc._p50(short):.4f}")
    check(len(long_) >= 25 and abs(wc._p50(long_) - 1.1375) < 0.005,
          "and a 2.475 s bow at swing_windup(2.475) = 1.1375 s",
          f"n {len(long_)} p50 {wc._p50(long_):.4f}")
    errs = [abs(e) for r in sho for e in r["word_error"]]
    check(len(errs) >= 400 and wc._p50(errs) < 0.015
          and sum(r["closed"] for r in sho) >= 0.98 * shots,
          "launch + flight predicts the word, and every launch is closed by its 0x00A7",
          f"n {len(errs)} p50 {wc._p50(errs) * 1000:.1f} ms, closed "
          f"{sum(r['closed'] for r in sho)} of {shots}")
    players = [r for r in c["attackers"] if r["type"] == 27 and len(r["gaps"]) >= 200]
    bows = [r for r in c["attackers"] if r["type"] == 5]
    check(len(players) >= 2 and all(abs(r["mode"] - 1.33) < 0.005 for r in players)
          and len(bows) >= 2 and all(abs(r["mode"] - 2.476) < 0.01 for r in bows),
          "WEAPONS-Q8: players join through 0x006E -- the sword tapes read type 27 at "
          "1.330, and both bow attackers 2.476",
          f"{len(players)} sword players, bows {[round(r['mode'], 3) for r in bows]}")
    d = _launch_detail()
    _gapped(d)                                               # the corpus's one gapped connection
    _arrow_signature(d)                                      # CASTAI-Z1: the preparation's arrow
    _skill_shot_pins(c, d)                                   # WEAPONS-W2c / C10


# THE PIN (2026-09-28, CASTAI-Z1). Every literal in section 2 was measured on the captures
# stamped before the owner's Zaishen Challenge capture; where that capture moved one, the
# literal is asserted on the captures before it and the claim is carried over the whole
# corpus by a SIGNATURE (a rule every launch must meet), never by a new corpus total.
PIN = "20260928T103123"
ZAISHEN = PIN


def _skills():
    import agents                                               # noqa: PLC0415
    return agents.WORLD.rows("skills")


def _port(gf):
    """'game-10.0.0.210_50061-to-54.198.7.73_80.jsonl' -> '50061'."""
    return gf.split("_", 2)[1].split("-")[0]


def _prep_type():
    import effects                                              # noqa: PLC0415
    return next(k for k, v in effects.EFFECT_TYPES.items() if v == "preparation")


def _prep_arrows():
    """{arrow: {impact visual}} over every PREPARATION row (effects.EFFECT_TYPES) whose
    +0x88 names a projectile -- the arrow that preparation substitutes, and the +0x84
    impact visual retail sends as [20, target, shooter, id] at that arrow's arrival
    (WEAPONS-C10): Kindle Arrows 433 -> 343 / 344, Apply Poison 435 -> 742 / 743."""
    prep = _prep_type()
    out = {}
    for row in _skills().values():
        if int(row.get("type_code", -1)) == prep and int(row.get("projectile", 2077)) != 2077:
            out.setdefault(int(row["projectile"]), set()).add(int(row.get("impact_visual", -1)))
    return out


def _announced(s2c):
    """{agent: [(t, preparation)]} -- the 0x009F [60, agent, P] a body or the player
    announces a self-cast by, P a preparation. Informative only (the witness below): a
    preparation cast before the observer saw the shooter's create is not on the wire."""
    rows, prep = _skills(), _prep_type()
    out = {}
    for t, op, v in s2c:
        if op == wc.PINT and len(v) > 3 and v[1] == 60:
            row = rows.get(str(v[3]))
            if row is not None and int(row.get("type_code", -1)) == prep:
                out.setdefault(v[2], []).append((t, v[3]))
    return out


def _launch_detail():
    """One more pass over the corpus for what corpus() aggregates away: every WEAPON shot
    and every SKILL shot with its launch time, the impact visuals at its arrival, the
    shooter's announced preparations, and the body's latest 0x0035 (base, modifier)."""
    import livewire                                             # noqa: PLC0415
    listed = [(os.path.basename(cd), gf) for cd, gf in livewire.live_connections()]
    out = {"listed": listed, "yielded": [], "empty": [], "weapon": [], "skill": []}
    for name, gf, s2c in wc.connections():
        out["yielded"].append((name, gf))
        if not s2c:
            out["empty"].append((name, gf))
            continue
        items, hands = wc.items_of(s2c), wc.hands_timeline(s2c)
        starts, skills, launches, _arr, _w = wc._events(s2c)
        announced = _announced(s2c)
        visual = {}                                         # shooter -> [(t, impact id)]
        for t, op, v in s2c:
            if op == wc.PINT_T and len(v) > 4 and v[1] == 20:
                visual.setdefault(v[3], []).append((t, v[4]))
        speed = {}
        for t, op, v in s2c:
            if op == wc.SPEED and len(v) > 3:
                speed.setdefault(v[1], []).append((t, wc._f32(v[2]), wc._f32(v[3])))

        def arrival(agent, t, flight):
            """the impact visuals at this launch's arrival: shooter's, inside the
            window corpus() closes a launch by (launch + flight + 0.25 s)"""
            return {i for tv, i in visual.get(agent, ()) if t <= tv < t + flight + 0.25}

        def held(agent, t):
            h = wc.held_at(hands, agent, t)
            lead = h[0] if h else None
            typ = None if lead is None else wc.held_type(items, lead)
            w617 = ((wc.word_of(items, lead, wc.PROJECTILE) or (None, None))[1]
                    if lead is not None else None)
            return typ, w617

        for agent, shots in launches.items():                 # shooters()' own filter
            ts, sk = starts.get(agent, ()), skills.get(agent, ())
            for t, v in shots:
                before = [s for s in ts if 0.0 <= t - s < wc.SHOT_WINDOW]
                if not before or any(before[-1] < k <= t for k in sk):
                    continue
                typ, w617 = held(agent, t)
                out["weapon"].append({"capture": name, "conn": gf, "agent": agent, "t": t,
                                      "projectile": v[5], "type": typ, "w617": w617,
                                      "impacts": arrival(agent, t, wc._f32(v[4])),
                                      "announced": announced.get(agent, [])})
        ss = wc.skill_shots(s2c)                                # rows come in launch order
        k = 0
        for t, op, v in s2c:
            if op != wc.LAUNCH or len(v) < 8 or k >= len(ss):
                continue
            r = ss[k]
            if (r["agent"], r["handle"], r["flight"]) != (v[1], v[6], wc._f32(v[4])):
                continue
            k += 1
            sp = [s for s in speed.get(v[1], ()) if s[0] <= t]
            out["skill"].append(dict(r, capture=name, conn=gf, t=t,
                                     impacts=arrival(v[1], t, r["flight"]),
                                     announced=announced.get(v[1], []),
                                     speed=(sp[-1][1], sp[-1][2]) if sp else None))
        if k != len(ss):
            raise AssertionError(f"{name} {gf}: {k} of {len(ss)} skill shots re-paired to "
                                 f"their launch -- the join below would score a subset")
    return out


def _gapped(d):
    """R4: the connections this census reads no s2c from are exactly the ones their
    capture's own manifest declares gapped -- printed by name, the refusal kept."""
    import livewire                                             # noqa: PLC0415
    root = livewire.captures_root()
    declared = {(cap, gf) for cap, gf in d["yielded"]
                if livewire.conn_name(gf) in livewire.declared_gaps(os.path.join(root, cap))}
    for cap, gf in sorted(declared):
        print(f"   set aside BY ITS MANIFEST: {cap} {livewire.conn_name(gf)} "
              f"{livewire.declared_gaps(os.path.join(root, cap))[livewire.conn_name(gf)]}")
    refused = {(cap, gf): livewire.decode_conn(os.path.join(root, cap), gf)[2]
               for cap, gf in declared}
    check(sorted(d["listed"]) == sorted(d["yielded"])
          and set(d["empty"]) == declared
          and declared == {(ZAISHEN, "game-10.0.0.210_65009-to-98.95.137.136_80.jsonl")}
          and not any(refused.values()),
          "every live game connection reaches the census (none dropped by its except), and "
          "the ones it reads NO s2c from are exactly those their capture's manifest declares "
          "gapped: CASTAI-Z1's match 2, still refused by decode_conn",
          f"listed {len(d['listed'])}, yielded {len(d['yielded'])}, empty {d['empty']}, "
          f"declared {sorted(declared)}, decode ok {refused}")


def _substituted(r, prep):
    """The preparation arrows this launch may carry: those whose row's impact visual
    rides its arrival -- two fields of ONE table row met on the wire, no timing window."""
    return {a for a, imps in prep.items() if imps & r["impacts"]}


def _arrow_signature(d):
    """CASTAI-Z1: what a bare bow's arrow is, launch by launch, over the whole corpus."""
    prep = _prep_arrows()
    bare = [r for r in d["weapon"] if r["w617"] is None and r["type"] in (5, 28)]
    bad = [r for r in bare if r["projectile"] != 143
           and r["projectile"] not in _substituted(r, prep)]
    subst = [r for r in bare if r["projectile"] != 143]
    plain = [r for r in bare if r["projectile"] == 143 and _substituted(r, prep)]
    # floors: the captures at the pin hold 102 such shots, 4 of them substituted
    check(len(bare) >= 102 and not bad and not plain and len(subst) >= 4
          and {343: {344}, 742: {743}}.items() <= prep.items(),
          f"SIGNATURE (whole corpus): a bow with NO 617 word shoots 143, or a PREPARATION's "
          f"arrow whose arrival carries that same row's impact visual -- every one of "
          f"{len(bare)} weapon shots; {len(subst)} substituted (343 / 344 Kindle Arrows, "
          f"742 / 743 Apply Poison), and no 143 arrives with a preparation's visual",
          "; ".join(f"{r['capture']} {r['conn'][-26:]} agent {r['agent']} t={r['t']:.3f} "
                    f"shoots {r['projectile']}, arrival visuals {sorted(r['impacts'])}"
                    for r in (bad + plain)[:6]) or f"preparation arrows {prep}")
    # The new fact, on its own witness: the Degeneration Ranger's Apply Poison.
    z = [r for r in d["weapon"] + d["skill"] if r["capture"] == ZAISHEN
         and r["projectile"] == 742]
    kinds = sorted((_port(r["conn"]), "skill" if "skill" in r else "weapon",
                    r.get("skill") or 0) for r in z)
    row = _skills().get("435") or {}
    span = float(row.get("activation", 0)) + max(float(row.get("duration0", 0)),
                                                 float(row.get("duration15", 0)))
    seen = sorted((_port(r["conn"]), round(r["t"], 3)) for r in z
                  if any(s == 435 and ta <= r["t"] <= ta + span for ta, s in r["announced"]))
    unseen = sorted((_port(r["conn"]), round(r["t"], 3)) for r in z
                    if (_port(r["conn"]), round(r["t"], 3)) not in seen)
    check(len(z) == 9 and {r["agent"] for r in z} == {6}
          and all(r["impacts"] == {743} for r in z)
          and kinds == [("50061", "skill", 426), ("50061", "weapon", 0),
                        ("50061", "weapon", 0), ("58544", "skill", 393),
                        ("58544", "skill", 393), ("58544", "skill", 426),
                        ("58544", "skill", 426), ("58544", "weapon", 0),
                        ("58544", "weapon", 0)]
          and int(row.get("projectile", 0)) == 742 and int(row.get("impact_visual", 0)) == 743
          and int(row.get("type_code", 0)) == _prep_type()
          and len(seen) == 7 and unseen == [("58544", 593.777), ("58544", 596.407)],
          f"NEW (OBSERVED, {ZAISHEN}): agent 6's 9 launches of 742 -- 4 weapon shots and 5 "
          f"skill shots (393 x2, 426 x3) -- each arrive with 743, and 435's table row is a "
          f"preparation whose +0x88 / +0x84 are 742 / 743: Apply Poison's arrow, the shape "
          f"Kindle Arrows 433 -> 343 / 344 already had. 7 sit inside a visible [60, 6, 435] "
          f"(activation + duration); the 2 before :58544's only one follow agent 6's create "
          f"there at 581.842 -- a cast the observer never saw (RECONSTRUCTION)",
          f"{kinds}; outside a visible window {unseen}")


def _skill_shot_pins(c, d):
    """WEAPONS-W2c / C10: the corpus's skill shots against the skill table."""
    ss = c["skill_shots"]
    bows = [r for r in ss if r["type"] == 5]
    check(len(ss) >= 151 and all(r["closed"] for r in ss) and not any(r["close46"] for r in ss),
          f"{len(ss)} skill shots (floor 151), every one closed by its 0x00A7 and NONE with "
          f"a 46 within 50 ms of the launch -- the attack trio's close rides no ranged skill")
    proj = {}
    for r in bows:
        proj.setdefault(r["skill"], set()).add(r["projectile"])
    check(proj.get(392) == {680} and proj.get(394) == {680} and proj.get(396) == {680}
          and proj.get(402) == {680} and proj.get(404) == {143, 343} and proj.get(1197) == {143},
          "bow attack skills launch ONE projectile each: Pin Down, Power Shot, Dual Shot and "
          "Determined Shot 680; Poison Arrow and Needling Shot the held bow's own arrow "
          "(143, or 343 under Kindle Arrows)", str({k: sorted(v) for k, v in proj.items()}))
    table = _skills()
    # RE-SCOPED 2026-09-28 (CASTAI-Z1). The literal rule -- 2077 accepts 143 or 343 -- is
    # a NAME LIST from the tapes it was written on, and the Zaishen capture brought two
    # arrows it never named: 742 under Apply Poison and a staff's own 617 behind an
    # instant skill. So the rule as written stays exact on the captures at the pin, and
    # the SIGNATURE below says what 2077 means on every launch. The blanket `except`
    # that skipped a skill with no table row is gone: an absent row is a stated rule now.
    pinned_ss = [r for r in ss if r["capture"] < PIN]
    absent_pinned = sorted({r["skill"] for r in pinned_ss if str(r["skill"]) not in table})
    agree, disagree = 0, []
    for r in pinned_ss:
        if str(r["skill"]) not in table:
            continue
        own = int(table[str(r["skill"])].get("projectile", -1))
        if own == r["projectile"] or (own == 2077 and r["projectile"] in (143, 343)):
            agree += 1
        else:
            disagree.append((r["skill"], own, r["projectile"]))
    check(agree >= 140 and not disagree and not absent_pinned,
          f"WEAPONS-C10, two instruments: the skill table's +0x88 names the launched projectile "
          f"on {agree} skill shots (2077 = the weapon's arrow), disagreeing on none (the "
          f"captures at the pin, every skill with a table row)",
          f"{disagree[:5]}; absent {absent_pinned}")
    rows, prep = d["skill"], _prep_arrows()
    absent = [r for r in rows if str(r["skill"]) not in table]
    agree, disagree = 0, []
    for r in rows:
        if str(r["skill"]) not in table:
            continue
        own = int(table[str(r["skill"])].get("projectile", -1))
        if own != 2077:
            ok = own == r["projectile"]
        else:                          # the held weapon's own arrow, or a preparation's
            mine = ({r["w617"]} if r["w617"] is not None
                    else {143} if r["type"] in (5, 28) else set())
            ok = r["projectile"] in mine | _substituted(r, prep)
        if ok:
            agree += 1
        else:
            disagree.append((r["capture"], r["agent"], r["skill"], own, r["projectile"],
                             r["type"], r["w617"], sorted(r["impacts"])))
    check(len(rows) == len(ss) and agree >= 151 and not disagree,
          f"SIGNATURE (whole corpus): +0x88 names the launched projectile on {agree} skill "
          f"shots, and 2077 names the WEAPON's -- its 617 word, else a bow's 143 -- or a "
          f"preparation's arrow arriving with that row's impact visual; disagreeing on none",
          f"{disagree[:5]}")
    _absent_rows(absent)
    e5 = [r["event_to_launch"] for r in ss if r["player"] and r["type"] == 5]
    ann = [r["event_to_launch"] for r in bows if not r["player"]
           and r["skill"] in (392, 394, 396, 402, 404) and r["capture"] < PIN]
    check(len(e5) >= 5 and max(e5) < 0.02 and len(ann) >= 40
          and abs(statistics.median(ann) - 1.1375) < 0.01 and min(ann) > 1.10 and max(ann) < 1.16,
          f"a player's bow skill launches IN its E5 batch ({len(e5)} of {len(e5)} within 20 ms); a "
          f"body's one windup after its announcement (median {statistics.median(ann):.4f} of "
          f"{len(ann)}, swing_windup(2.475) = 1.1375; the body half on the captures at the pin)")
    _windup_signature(d)


def _absent_rows(absent):
    """R8: a skill shot whose skill has NO table row. The stated rule: vault/content/
    skills.toml is skilltable.player_corpus -- equip_family 1, PvP-only excluded -- so an
    absent id must be one the pinned client's OWN record puts outside that corpus."""
    ids = sorted({r["skill"] for r in absent})
    z = sorted((_port(r["conn"]), r["agent"], r["player"], r["skill"]) for r in absent
               if r["capture"] == ZAISHEN)
    check(ids == sorted({r["skill"] for r in absent if r["capture"] >= PIN})
          and z == [("50295", 7, True, 2858)] * 3,
          f"a skill with no table row appears only after the pin: {ids} -- on {ZAISHEN}, "
          f"exactly the observer's three launches behind 2858 (a PvP id; the Zaishen "
          f"Challenge fields PvP skills)",
          f"{z}")
    cscan = os.path.join(os.path.dirname(HERE), "clientscan")
    if cscan not in sys.path:
        sys.path.insert(0, cscan)
    import pinned                                               # noqa: PLC0415
    import skilltable                                           # noqa: PLC0415
    try:
        exe, _why = pinned.find()
    except SystemExit as exc:
        LEDGER.skip("why the absent ids are absent", f"no pinned client: {str(exc)[:60]}")
        return
    with open(exe, "rb") as fh:
        data = fh.read()
    base = skilltable.locate_table(data)[0]
    recs = {i: skilltable.parse_record(data, base, i) for i in ids}
    builds = {int(r.provenance.get("build", 0)) for r in _skills().values()}
    check(ids and skilltable.build_of(data) in builds
          and all(r["equip_family"] != 1 or r["pvp_only"] for r in recs.values())
          and not set(ids) & set(skilltable.player_corpus(list(recs.values()))),
          "and each is absent BY THE EXTRACTOR'S RULE: the pinned client's own record puts it "
          "outside the player corpus (equip_family != 1 or PvP-only), and the table's rows "
          "were emitted from that build (among others)",
          f"{ {i: (r['equip_family'], r['pvp_only']) for i, r in recs.items()} }, table "
          f"builds {builds}, client {skilltable.build_of(data)}")


def _windup_signature(d):
    """A body's bow skill launches one windup of its CURRENT attack duration after its
    announcement: swing_windup(base x modifier) of the body's latest 0x0035."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import authsrv                                              # noqa: PLC0415
    rows = [r for r in d["skill"] if not r["player"] and r["type"] == 5
            and r["skill"] in (392, 394, 396, 402, 404)]
    res = [(r, r["event_to_launch"] - authsrv.swing_windup(r["speed"][0] * r["speed"][1]))
           for r in rows if r["speed"] is not None]
    slowed = [(r, e) for r, e in res if abs(r["speed"][1] - 1.0) > 1e-6]
    # THE PINNED BAND ON EVERY ROW (1.10 .. 1.16 around 1.1375 is a residual of
    # -0.0375 .. +0.0225, each row against its OWN swing_windup(base x modifier)),
    # modifier 1.0 included. The only rows outside it are the two witnessed Zaishen
    # shots (finding: cause UNVERIFIED), held as positive controls and asserted as
    # EXACTLY the out-of-band set -- so a third, on any capture, reddens this check
    # and gets classified rather than being averaged into the median.
    outband = sorted((r["capture"], _port(r["conn"]), round(r["t"], 3))
                     for r, e in res if not -0.0375 < e < 0.0225)
    witnessed = [(ZAISHEN, "50061", 217.821), (ZAISHEN, "50295", 476.727)]
    check(len(res) == len(rows) >= 44 and abs(statistics.median(e for _r, e in res)) < 0.01
          and slowed and all(-0.0375 < e < 0.0225 for _r, e in slowed)
          and outband == witnessed,
          f"SIGNATURE (whole corpus): a body's bow skill launches swing_windup(base x modifier) "
          f"of its latest 0x0035 after the announcement -- median residual "
          f"{statistics.median(e for _r, e in res) * 1000:+.1f} ms over {len(res)}; EVERY row "
          f"inside the pinned band (1.10 .. 1.16 around 1.1375, carried to its own windup), "
          f"the {len(slowed)} under a modifier among them, except exactly the two witnessed "
          f"Zaishen shots {[(p, t) for _c, p, t in witnessed]}",
          f"{len(rows)} rows, {len(res)} with a 0x0035; out of band {outband}; slowed "
          f"{[(round(r['t'], 3), r['speed'], round(e, 4)) for r, e in slowed]}")
    z = [(r, e) for r, e in res if r["capture"] == ZAISHEN]
    zs = sorted((_port(r["conn"]), round(r["t"], 3)) for r, e in z
                if abs(r["speed"][1] - 1.5) < 1e-6)
    out = sorted((_port(r["conn"]), round(r["t"], 3), round(r["event_to_launch"], 4))
                 for r, e in z if abs(r["speed"][1] - 1.0) < 1e-6 and not -0.0375 < e < 0.0225)
    check(len(z) == 64 and {r["agent"] for r, _e in z} == {10}
          and len(zs) == 10 and {p for p, _t in zs} == {"50061", "58544"}
          and out == [("50061", 217.821, 1.0948), ("50295", 476.727, 1.2242)],
          f"NEW (OBSERVED, {ZAISHEN}): the Zaishen Archer's (agent 10) 64 body bow skill shots "
          f"-- 10 under a 0x0035 modifier of 1.5 (Dual Shot's two arrows count two) launch at swing_windup(2.475 x 1.5) = 1.75625 "
          f"(each window opens ~1-4 s after a [60, 4, 10, 135] -- 135 is a Necromancer hex); "
          f"and exactly 2 at modifier 1.0 fall outside the pinned band, cause UNVERIFIED",
          f"slowed {zs}; outside {out}")


def main():
    section_synthetic()
    section_skill_shots()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
