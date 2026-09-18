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
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import weaponcensus as wc  # noqa: E402

LEDGER = checks.Ledger("weaponcensus: held weapon types, swings and shots", floor=15)   # the BARE-MACHINE number: 15 without the vault (section 2 skips), 28 with it; from green runs
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
            s.append((t0 + windup + flight, wc.ARRIVE, [wc.ARRIVE, agent, handle[0], 1]))
        s.append((t0 + windup + flight, wc.PFLOAT_T,
                  [wc.PFLOAT_T, 16, target, agent, f32(-0.05)]))

    for t0 in (1.0, 3.475, 5.95, 8.425):                     # the player's bow, 2.475 s
        shot(ME, t0, 1.1375, 0.4, 143, 1)
    # a bow ATTACK SKILL: activation, then its own launch -- never a weapon shot
    s.append((20.0, wc.PINT_T, [wc.PINT_T, wc.START, ME, FOE, 0]))
    s.append((20.1, wc.E4, [wc.E4, ME, 343, 0]))
    s.append((21.0, wc.LAUNCH, [wc.LAUNCH, ME, (1.0, 2.0), 0, f32(0.3), 343, 99, 0]))
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


def section_vault():
    print("\n2. the vault: the live corpus, floors and signatures")
    try:
        c = wc.corpus()
    except Exception as exc:                                    # noqa: BLE001
        c = None
        print(f"   (corpus unreadable: {exc!r})")
    if not c or not c["shooters"]:
        LEDGER.skip("section 2", "no live corpus -- 13 checks")
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
    bare = [r for r in sho if r["w617"] is None and r["type"] in (5, 28)]
    arrows = [r for r in bare if set(r["field5"]) == {143}]
    check(len(bare) >= 20 and len(arrows) >= 0.9 * len(bare),
          "and a bow with NO 617 word shoots 143", f"{len(arrows)} of {len(bare)}")
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


def main():
    section_synthetic()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
