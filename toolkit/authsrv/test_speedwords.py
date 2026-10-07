r"""Movement speed on retail's wire, pinned: speedwords.py's predictions over the corpus.

    python toolkit/authsrv/test_speedwords.py

Reads the vault (every live capture); the corpus sections skip, loudly, on an absent
vault/captures/live DIRECTORY -- never on a load failure, which raises. The floors are
FLOORS on exposure -- a corpus that gained captures may raise them, one that lost its
witnesses goes red here rather than letting `push_speed`'s numbers drift away from
what retail sent. P1-P6 from the first green run (2026-09-16, 501 speed words over 17
captures); P7-P10 from SLICE-F48b's (2026-10-07, 831 words over 26 captures).

Section 4 runs on EVERY machine: the scorer itself on three synthetic tapes built
through the real `speed_rows` / `boost_events` -- retail's override shape, and the
multiplicative and additive worlds the corpus refutes -- so the P8 / P10 arms are
shown to go red on the wire a wrong rule would have produced, not only green on the
one retail did.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import capgaps          # noqa: E402
import checks           # noqa: E402
import speedwords       # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

# Per machine, decided on the live-captures DIRECTORY, never on what loaded.
HAVE_LIVE = os.path.isdir(vaultpath.vault_path("captures", "live"))
FLOOR_BARE = 5     # 2026-10-07 (SLICE-F48b): MEASURED -- section 4 alone (the synthetic tapes), RURIK_VAULT at a nonexistent path; sections 1-3 one declared skip
FLOOR_VAULT = 27   # 2026-10-07 (SLICE-F48b): MEASURED -- 12 (2026-09-16, P1-P6 and the controls) + the gapped connection's audit + P7, P7a, P8, P8b, P8c, P9, P10, P10m, P10a + section 4's 5
LEDGER = checks.Ledger("speed words on retail's wire",
                       floor=FLOOR_VAULT if HAVE_LIVE else FLOOR_BARE)
check = checks.adopt(LEDGER)


def corpus():
    print("== 1. the census ==")
    events, set_aside = [], []
    rows = speedwords.census(events=events, set_aside=set_aside)
    caps = len(set(r["capture"] for r in rows))
    check(len(rows) >= 831, f"{len(rows)} speed words (floor 831)")
    check(caps >= 26, f"over {caps} captures (floor 26)")
    check(all(r["val"] >= 0.0 for r in rows), "no negative speed word")
    live = vaultpath.require_dir("captures", "live", why="test_speedwords")
    capdirs = [os.path.join(live, s) for s in sorted(os.listdir(live))
               if os.path.isdir(os.path.join(live, s))]
    ok, detail = capgaps.audit(set_aside, capdirs, tape.refuses)
    check(ok, "the census set aside EXACTLY the manifest-declared gapped connections "
              "(capgaps.KNOWN_GAPPED), each still refused -- by name, not by an except",
          detail)

    print("\n== 2. the predictions ==")
    s = speedwords.score(rows, events)
    hit, miss, _ = s["P1 boost x1.33"]
    check(hit >= 80 and miss == 0,
          f"P1: a 33% boost applied with nothing open is x1.33 ({hit} / {miss}, floor 80 / 0)")
    hit, miss, _ = s["P2 crippled x0.5"]
    check(hit >= 2 and miss == 0,
          f"P2: Crippled applied with nothing open is x0.5 ({hit} / {miss}, floor 2 / 0)")
    hit, miss, _ = s["P3 crippled x boost = x0.665"]
    check(hit >= 1 and miss == 0,
          f"P3: Crippled over a boost is x0.665, MULTIPLICATIVE ({hit} / {miss}, floor 1 / 0)")
    n665, n083, _ = s["P3b additive 0.83 never seen"]
    check(n665 >= 21 and n083 == 0,
          f"P3b: {n665} rows read x0.665 and {n083} read the additive x0.83 (floor 21 / 0)")
    hit, miss, _ = s["P4 second boost = x1.34 cap"]
    check(hit >= 8 and miss == 0,
          f"P4: a second 33% boost over an open one is x1.34, the cap ({hit} / {miss}, floor 8 / 0)")
    hit, miss, _ = s["P5 cure batch has 2 words"]
    check(hit >= 1 and miss == 0,
          f"P5: the Charge! cure batch carries two speed words ({hit} / {miss}, floor 1 / 0)")
    n288, n300, _ = s["P6 bases"]
    check(n288 >= 300 and n300 >= 150,
          f"P6: bases are 288 ({n288} words) and 300 ({n300} words); floors 300 / 150")
    # SLICE-F48b (2026-10-07): the over-cap snare over a boost.
    hit, miss, _ = s["P7 75% snare = x0.25 exactly"]
    check(hit >= 14 and miss == 0,
          f"P7: every word in (0, 0.3) of its base, and 493's own apply's, is base x 0.25 "
          f"exactly -- 72.0 on 288, 75.0 on 300 ({hit} / {miss}, floor 14 / 0)")
    hit, miss, _ = s["P7a 493's own apply joined at x0.25"]
    check(hit >= 1 and miss == 0,
          f"P7a: skill 493's 0x0042 is joined in its batch by a 0x0027 at x0.25 "
          f"({hit} / {miss}, floor 1 / 0)")
    hit, miss, _ = s["P8 boost under an over-cap snare is silent"]
    check(hit >= 2 and miss == 0,
          f"P8: a Charge! applied to, and ending on, an observer whose last word is x0.25 "
          f"sends NO 0x0027 for it ({hit} silent / {miss} worded, floor 2 / 0)")
    hit, miss, _ = s["P8b control: the same batch words another agent"]
    check(hit >= 2 and miss == 0,
          f"P8b: and each of those batches words an UNSNARED party member -- the boost "
          f"reached the wire ({hit} / {miss}, floor 2 / 0)")
    hit, miss, _ = s["P8c control: a boost on an unslowed agent is worded"]
    check(hit >= 100 and miss == 0,
          f"P8c: the same walker sees the word when there is one -- a 160/364 apply on an "
          f"unslowed observer is worded ({hit} / {miss}, floor 100 / 0)")
    hit, miss, _ = s["P9 the snare's end restores the boost"]
    check(hit >= 2 and miss == 0,
          f"P9: a boosted body's over-cap snare ends back on its pre-snare boosted word "
          f"(399 -> 75 -> 399; {hit} / {miss}, floor 2 / 0)")
    agree, dis, _ = s["P10 OVERRIDE (shipped): an over-cap snare drops the boosts"]
    check(agree >= 4 and dis == 0,
          f"P10: the OVERRIDE rule agrees with every exposed row ({agree} / {dis}, floor 4 / 0)")
    agree, dis, _ = s["P10m MULTIPLICATIVE b x s (REFUTED)"]
    check(agree == 0 and dis >= 4,
          f"P10m: the multiplicative rule (GWW 'Effect stacking', shipped until 2026-10-07) "
          f"agrees with NONE of them ({agree} of {agree + dis}; it says 99.75 where retail "
          f"sent 75.0, and a word where retail sent none)")
    agree, dis, _ = s["P10a ADDITIVE b - (1 - s) (REFUTED)"]
    check(agree == 0 and dis >= 4,
          f"P10a: the additive rule agrees with none either ({agree} of {agree + dis}; "
          f"174.0 where retail sent 75.0)")

    print("\n== 3. the controls ==")
    ratios = set(r["ratio"] for r in rows if r["ratio"] is not None)
    check(1.77 not in ratios and 1.66 not in ratios,
          "no uncapped double boost (x1.66 / x1.77) anywhere in the corpus")
    check(all(r["ratio"] in (1.33, 1.34) for r in rows
              if any(s in speedwords.BOOST_SKILLS for s in r["apply"])
              and r["ratio"] is not None
              and not (r["prev"] is not None and r["prev"] < r["base"])),
          "every 160/364 apply not over a snare reads x1.33 or x1.34 -- nothing else")


def synthetic(world):
    """One synthetic connection: the observer 7 (base 288) and two bodies, 9 and 10
    (base 300), in the shape of 20260928T103123 :50295 -- a plain Charge! (worded), the
    75% snare, a Charge! applied and ending under it, a boosted body snared and
    restored. `world` picks what the snared rows read: retail's override, or the rule
    the corpus refutes."""
    f = speedwords.OP_SPEED

    def w(t, agent, val):
        return (t, f, [39, agent, float(val)])
    boost_on = {"override": [], "multiplicative": [w(20.0, 7, 95.76)],
                "additive": [w(20.0, 7, 167.04)]}[world]
    boost_off = {"override": [], "multiplicative": [w(26.0, 7, 72.0)],
                 "additive": [w(26.0, 7, 72.0)]}[world]
    onset = {"override": 75.0, "multiplicative": 99.75, "additive": 174.0}[world]
    msgs = ([w(1.0, 7, 288.0), w(1.0, 9, 300.0), w(1.0, 10, 300.0),
             (2.0, speedwords.OP_APPLY, [66, 7, 364, 1, 50, 6.0]),
             w(2.0, 7, 383.04), w(2.0, 9, 399.0),
             (8.0, speedwords.OP_REMOVE, [68, 7, 50]), w(8.0, 7, 288.0), w(8.0, 9, 300.0),
             (10.0, speedwords.OP_APPLY, [66, 7, 493, 0, 63, 5.0]), w(10.0, 7, 72.0),
             (20.0, speedwords.OP_APPLY, [66, 7, 364, 1, 56, 6.0])] + boost_on
            + [w(20.0, 9, 399.0),
               (26.0, speedwords.OP_REMOVE, [68, 7, 56])] + boost_off
            + [w(26.0, 9, 300.0),
               w(31.0, 10, 399.0), w(40.0, 10, onset), w(47.0, 10, 399.0),
               (60.0, speedwords.OP_REMOVE, [68, 7, 63]), w(60.0, 7, 288.0)])
    rows = speedwords.with_bases(speedwords.speed_rows(msgs))
    for r in rows:
        r.update(capture="synthetic", connection=world)
    return speedwords.score(rows, speedwords.boost_events(msgs, rows))


def scorer():
    print("\n== 4. the scorer on synthetic tapes (every machine): the arms can go red ==")
    good = synthetic("override")
    pick = ("P7 75% snare = x0.25 exactly", "P8 boost under an over-cap snare is silent",
            "P8b control: the same batch words another agent",
            "P8c control: a boost on an unslowed agent is worded",
            "P9 the snare's end restores the boost",
            "P10 OVERRIDE (shipped): an over-cap snare drops the boosts",
            "P10m MULTIPLICATIVE b x s (REFUTED)", "P10a ADDITIVE b - (1 - s) (REFUTED)")
    got = {k: good[k][:2] for k in pick}
    check(got == {pick[0]: (2, 0), pick[1]: (2, 0), pick[2]: (2, 0), pick[3]: (1, 0),
                  pick[4]: (1, 0), pick[5]: (3, 0), pick[6]: (0, 3), pick[7]: (0, 3)},
          "retail's shape: P7 2/0, P8 2/0 with its two controls, P9 1/0, OVERRIDE 3/0, "
          "both refuted arms 0/3 -- through the real speed_rows and boost_events", str(got))
    # The multiplicative world: the boosted onset reads 99.75 (x0.3325, still under
    # x0.5, so it is an onset) and the observer is worded 95.76 / 72.0.
    bad = synthetic("multiplicative")
    check(bad[pick[1]][:2] == (0, 2) and bad[pick[5]][:2] == (0, 3)
          and bad[pick[6]][:2] == (3, 0) and bad[pick[7]][:2] == (0, 3),
          "KNOWN-BAD: a multiplicative wire (99.75 at the boosted onset, 95.76 / 72.0 at the "
          "boost's apply and end) turns P8 to 0/2, OVERRIDE to 0/3 and its own arm to 3/0 -- "
          "the scorer discriminates", str({k: bad[k][:2] for k in pick}))
    check(bad[pick[4]][:2] == (1, 0),
          "and P9 does NOT discriminate there (every rule restores the boost at the snare's "
          "end): what it pins is that the boost is suppressed, not cancelled")
    # The additive world: 174.0 and 167.04 are x0.58, ABOVE x0.5, so the parser sees
    # neither the boosted onset nor the boost's END as "under an over-cap snare" (a limit
    # of the reader, stated: on the corpus the onsets read 0.25, so the arm is scored
    # there); the boost's apply over 72.0 is still exposed, and refutes it.
    bad = synthetic("additive")
    check(bad[pick[1]][:2] == (0, 1) and bad[pick[5]][:2] == (0, 1)
          and bad[pick[7]][:2] == (1, 0) and bad[pick[6]][:2] == (0, 1)
          and bad[pick[4]][:2] == (0, 0),
          "KNOWN-BAD: an additive wire (167.04 at the boost's apply over 72.0) turns P8 to "
          "0/1, OVERRIDE to 0/1 and its own arm to 1/0 while the multiplicative arm stays 0/1 "
          "-- the event half checks the VALUE, not only that a word went",
          str({k: bad[k][:2] for k in pick}))
    # P7 can fail: a quarter that is not exact.
    msgs = [(1.0, speedwords.OP_SPEED, [39, 7, 288.0]),
            (10.0, speedwords.OP_APPLY, [66, 7, 493, 0, 63, 5.0]),
            (10.0, speedwords.OP_SPEED, [39, 7, 72.5]),
            (20.0, speedwords.OP_SPEED, [39, 7, 288.0])]
    rows = speedwords.with_bases(speedwords.speed_rows(msgs))
    check(speedwords.score(rows)["P7 75% snare = x0.25 exactly"][:2] == (0, 1),
          "KNOWN-BAD: a 493 apply joined by 72.5 (not 288 x 0.25) is a P7 miss")


def main():
    if HAVE_LIVE:
        corpus()
    else:
        LEDGER.skip("sections 1-3, the live corpus",
                    f"no {vaultpath.vault_path('captures', 'live')} directory on this machine")
    scorer()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
