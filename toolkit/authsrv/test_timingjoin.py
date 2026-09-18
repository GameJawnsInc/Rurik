"""test_timingjoin.py -- the side-by-side timing census (timingjoin.py).

Section 1 is a SYNTHETIC wire with every row's answer known by construction, so a
join that drifts (a window, a field index, the plain / boosted split) fails with no
vault. Section 2 is the vault: RUN-DAGGERS-2 must still read the numbers SLICE-F49,
F50 and F51 were built on, and one of OUR recorder captures must decode through the
same codec into the same rows. Both halves of section 2 SKIP, printed, on a bare
machine.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import timingjoin as tj  # noqa: E402

LEDGER = checks.Ledger("timingjoin: every timed quantity, retail beside ours", floor=15)   # the BARE-MACHINE number: 15 without the vault (section 2 skips three times), 22 with it; from green runs
check = LEDGER.ok

ME, FOE, FRENZY, LEAD = 7, 9, 346, 782


def f32(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def wire():
    """A tiny connection whose every timed quantity is a round number."""
    s = [(0.0, tj.PINT, [0x9F, 41, ME, 25])]
    start = lambda t: s.append((t, tj.PINT_T, [0xA0, 4, ME, FOE, 0]))
    word = lambda t, p=16: s.append((t, tj.PFLOAT_T, [0xA3, p, FOE, ME, f32(-0.05)]))
    # three plain swings; the second crits; the third DOUBLES 0.5 s on, so it
    # opens an eighth of the interval early (DAGGERS-F20: 1.1664 for 1.333)
    third = 2.333 + 1.333 * 7 / 8
    for i, t in enumerate((1.0, 2.333, third)):
        start(t)
        word(t + 0.565, 17 if i == 1 else 16)
    s.append((third + 0.565 + 0.5, tj.PINT, [0x9F, 2, ME, 0]))
    word(third + 0.565 + 0.5)
    # a lead: debit, E5 0.15 s on with E3 beside it, recharge 2, chain set then cleared
    s.append((6.0, tj.PFLOAT, [0xA2, 62, ME, f32(-0.2)]))
    s.append((6.15, tj.E5, [0xE5, ME, LEAD, 0, 2]))
    s.append((6.15, tj.COMBO, [0x5C, ME, FOE, 1]))
    word(6.15)
    s.append((6.15, tj.E3, [0xE3, ME, LEAD, 0]))
    start(6.15 + 0.7665)
    word(6.15 + 0.7665 + 0.565)
    s.append((8.15, tj.E6, [0xE6, ME, LEAD, 0]))
    s.append((21.15, tj.COMBO, [0x5C, ME, FOE, 0]))
    # Frenzy for 8 s: two boosted swings 0.891 apart, the hit 0.346 in
    s.append((30.0, tj.E5, [0xE5, ME, FRENZY, 0, 4]))
    s.append((30.0, tj.APPLY, [0x42, ME, FRENZY, 0, 3, f32(8.0)]))
    for t in (31.0, 31.891):
        start(t)
        word(t + 0.346)
    s.append((38.0, tj.REMOVE, [0x44, ME, 3]))
    s.append((34.0, tj.E6, [0xE6, ME, FRENZY, 0]))
    # somebody else's swing must never be read as the observer's
    s.append((2.0, tj.PINT_T, [0xA0, 4, 55, ME, 0]))
    s.sort(key=lambda r: r[0])
    return s


def ranged_wire():
    """A bow: three shots 2.475 s apart, released at 1.1375 s, 0.4 s in the air; then a
    bow ATTACK SKILL whose launch must not be read as a swing's."""
    s = [(0.0, tj.PINT, [0x9F, 41, ME, 25])]
    for n, t in enumerate((1.0, 3.475, 5.95)):
        s.append((t, tj.PINT_T, [0xA0, 4, ME, FOE, 0]))
        s.append((t + 1.1375, tj.LAUNCH, [0xA4, ME, (1.0, 2.0), 0, f32(0.4), 143, n + 1, 1]))
        s.append((t + 1.5375, tj.ARRIVE, [0xA7, ME, n + 1, 1]))
        s.append((t + 1.5385, tj.PFLOAT_T, [0xA3, 16, FOE, ME, f32(-0.05)]))
    s.append((20.0, tj.PINT_T, [0xA0, 4, ME, FOE, 0]))
    s.append((20.1, tj.E4, [0xE4, ME, 394, 0]))
    s.append((21.0, tj.LAUNCH, [0xA4, ME, (1.0, 2.0), 0, f32(0.3), 343, 9, 0]))
    s.append((2.0, tj.LAUNCH, [0xA4, 55, (1.0, 2.0), 0, f32(0.3), 143, 1, 1]))   # somebody else's
    return sorted(s, key=lambda r: r[0])


def near(xs, want, tol=1e-6):
    return xs is not None and len(xs) == len(want) and all(
        abs(a - b) < tol for a, b in zip(sorted(xs), sorted(want)))


def section_synthetic():
    print("\n1. a synthetic wire, every answer known by construction")
    s2c = wire()
    check(tj.observer_of(s2c) == ME, "the observer is the agent whose property 41 opens the wire")
    rows = tj.census(s2c, ME, {FRENZY})
    check(near(rows.get("swing start->start plain"), [1.333]),
          "plain swings: start to start, the pair split by a skill left out",
          str(rows.get("swing start->start plain")))
    check(near(rows.get("swing start->start plain, the next DOUBLES"), [1.333 * 7 / 8]),
          "and the interval INTO a doubling swing has its own row -- an eighth "
          "shorter on retail (DAGGERS-F20)",
          str(rows.get("swing start->start plain, the next DOUBLES")))
    check(near(rows.get("swing start->start boosted"), [0.891]),
          "and the boosted pair lands in its own row -- inside the 0x0042's episode",
          str(rows.get("swing start->start boosted")))
    check(near(rows.get("swing start->word plain"), [0.565] * 4)
          and near(rows.get("swing start->word boosted"), [0.346] * 2),
          "start to the damage word, both regimes")
    check(near(rows.get("double gap plain"), [0.5]),
          "the double strike's [2, me, 0] half a second behind its word")
    check(near(rows.get(f"debit->E5 {LEAD} plain"), [0.15])
          and near(rows.get(f"E5->E3 {LEAD} plain"), [0.0])
          and near(rows.get(f"E5->E6 {LEAD} (recharge 2)"), [2.0]),
          "a skill's clock: debit to landing, landing to E3, landing to the recharge's end")
    check(near(rows.get("E5->next swing plain"), [0.7665]),
          "the landing to the next plain swing (SLICE-F51's recovery)")
    check(near(rows.get("chain set->0"), [15.0]) and near(rows.get(f"effect {FRENZY}"), [8.0]),
          "the chain icon's 15 s and Frenzy's 8 s episode")
    check(not any(k.startswith(f"debit->E5 {FRENZY}") for k in rows),
          "an attack-speed STANCE is not scored as an attack skill's landing")
    sw = tj.swings(s2c, ME, {FRENZY})
    check(len(sw) == 6 and [r["critical"] for r in sw[:3]] == [False, True, False]
          and [r["doubled"] for r in sw[:3]] == [False, False, True],
          "one row per swing of the OBSERVER's, with its critical and its double",
          str([(r["critical"], r["doubled"]) for r in sw]))
    check(sw[3]["after_skill"] is not None and abs(sw[3]["after_skill"] - 0.7665) < 1e-6
          and sw[0]["after_skill"] is None and sw[4]["after_skill"] is None,
          "and how long after a SKILL's landing it opened -- a stance's E5 does not count")
    check(sw[4]["boosted"] and not sw[0]["boosted"], "boosted is the episode, not a constant")
    ranged = tj.census(ranged_wire(), ME, {FRENZY})
    check(near(ranged.get("swing start->launch plain"), [1.1375] * 3),
          "a RANGED swing: start to its 0x00A4 -- the skill's launch and another "
          "shooter's are left out (WEAPONS-C1)", str(ranged.get("swing start->launch plain")))
    check(near(ranged.get("launch->word - flight plain"), [0.001] * 3, tol=1e-4)
          and near(ranged.get("launch->arrival - flight plain"), [0.0] * 3, tol=1e-4),
          "launch + the message's own flight against the word and against the 0x00A7, signed",
          str(ranged.get("launch->word - flight plain")))


def section_vault():
    print("\n2. the vault: RUN-DAGGERS-2, and one of our own captures")
    try:
        loaded = tj.load_retail("20260917T224104")
    except Exception as exc:                                    # noqa: BLE001
        loaded = []
        print(f"   (retail unreadable: {exc!r})")
    if not loaded:
        LEDGER.skip("section 2 retail", "no live tape 20260917T224104 -- 4 checks")
    else:
        rows = {}
        for _label, s2c, me in loaded:
            for k, xs in tj.census(s2c, me, tj.ias_skills() or {FRENZY}).items():
                rows.setdefault(k, []).extend(xs)
        p50 = lambda k: sorted(rows[k])[len(rows[k]) // 2] if rows.get(k) else None
        check(p50("debit->E5 782 plain") is not None and 0.14 < p50("debit->E5 782 plain") < 0.16,
              "retail lands Jagged Strike 0.15 s after the debit (SLICE-F51)",
              str(p50("debit->E5 782 plain")))
        check(p50("double gap boosted") is not None and 0.32 < p50("double gap boosted") < 0.345,
              "the double strike under Frenzy is a third of a second (DAGGERS-F19)",
              str(p50("double gap boosted")))
        check(len(rows.get("swing start->start boosted", ())) >= 20
              and abs(p50("swing start->start boosted") - 0.891) < 0.01,
              "and the boosted swing 0.891 s, n >= 20", str(p50("swing start->start boosted")))
        into = rows.get("swing start->start boosted, the next DOUBLES", [])
        check(len(into) >= 8 and abs(p50("swing start->start boosted, the next DOUBLES")
                                     - 0.891 * 7 / 8) < 0.015,
              "and the interval INTO a doubling swing is 7/8 of it (DAGGERS-F20)",
              f"n={len(into)} p50 {p50('swing start->start boosted, the next DOUBLES')}")
    try:
        bow = tj.load_retail("20260914T005758")
    except Exception as exc:                                    # noqa: BLE001
        bow = []
        print(f"   (retail bow tape unreadable: {exc!r})")
    if not bow:
        LEDGER.skip("section 2 retail bow", "no live tape 20260914T005758 -- 1 check")
    else:
        got = {}
        for _label, s2c, me in bow:
            for k, xs in tj.census(s2c, me, tj.ias_skills() or {FRENZY}).items():
                got.setdefault(k, []).extend(xs)
        s2l = sorted(got.get("swing start->launch plain", []))
        err = sorted(abs(e) for e in got.get("launch->word - flight plain", []))
        check(len(s2l) >= 8 and abs(s2l[len(s2l) // 2] - 1.1375) < 0.005
              and err and err[len(err) // 2] < 0.015,
              "retail's 2.475 s bow releases at 1.1375 s and the word lands at launch + "
              "flight (WEAPONS-C1)", f"n {len(s2l)} p50 {s2l[len(s2l) // 2] if s2l else None}")
    path = None
    try:
        path = tj.newest_ours()
    except Exception as exc:                                    # noqa: BLE001
        print(f"   (ours unreadable: {exc!r})")
    if not path:
        LEDGER.skip("section 2 ours", "no recorder capture of ours -- 2 checks")
        return
    label, s2c, me = tj.load_ours(path)
    check(me == tj.OUR_PLAYER and len(s2c) > 100,
          "one of OUR recorder captures decodes through the same codec",
          f"{label}: {len(s2c)} messages")
    check(isinstance(tj.census(s2c, me, tj.ias_skills()), dict),
          "and the same joins run over it without a special case")


def main():
    section_synthetic()
    section_vault()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
