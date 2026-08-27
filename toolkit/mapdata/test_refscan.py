"""Check the tag-4 / tag-6 `value` reading against the whole map corpus.

`refscan.py` claims tag 6's `value` is a second index into the same prop array
that `prop` indexes, and tag 4's is not an index at all. The load-bearing part is
not the 10,647 of 10,647 — an inequality over small numbers can hold by accident
— so this file asserts the two things that make it a measurement:

  * §2 THE TIGHTNESS. The values must SATURATE the array. A median
    `max(value)/(len(props)-1)` near 1 says the whole index range is used; tag
    4's median of ~95 says its words are not indices at all. If tag 6's median
    ever fell toward tag 4's, the reading would be wrong and this goes red.

  * §3 THE SHUFFLE CONTROL, which is the one that can embarrass the claim.
    Re-score each map's values against a DIFFERENT map's prop count. A real
    per-map bound must BREAK; a universal small-number ceiling would survive.
    It breaks at ~32%. Asserting a floor on that percentage is what stops
    "value < len(props)" from being a fact about integers rather than about
    these maps.

  * §4 SEPARATION. The two tags must not converge. They are read by the same
    decoder from the same file, so if the numbers ever agreed, either the
    decoder stopped telling them apart or the reading was never real.

§5 pins the ten tag-6 SELF-REFERENCES. A 40-map sample reported zero of them,
which is how a rare row vanishes; they exist over 349 maps and any account of
what the relation means has to survive them.

NO VAULT, NO RUN: this reads the archive only, and declares a skip without one.

    python toolkit/mapdata/test_refscan.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import refscan  # noqa: E402

# Floor from the green run of 2026-08-27, which executes 17 checks. EVERY check
# here reads the archive, so unlike test_quests -- whose floor is deliberately
# its bare-machine count -- there is no useful lower number to fall back to:
# without an archive this file runs ZERO checks and declares one skip.
#
# THAT IS RED, ON PURPOSE, and the choice is worth stating because the two
# files land opposite ways. `test_quests` has real work that survives a missing
# vault, so its floor lets a bare machine pass. This file has none, and
# `CLAUDE.md`'s rule is that a run which measured nothing failed -- so a
# machine that cannot open the archive gets a NAMED skip and a red verdict
# rather than a green one earned by measuring nothing.
LEDGER = checks.Ledger("prop reference words", floor=17)
check = checks.adopt(LEDGER)

MIN_MAPS = 300


def main():
    try:
        rows = refscan.corpus()
    except (Exception, SystemExit) as exc:      # noqa: BLE001
        LEDGER.skip("the whole tag-4/tag-6 reading",
                    f"the archive is not readable ({type(exc).__name__}: "
                    f"{exc}), and every check here reads it")
        return LEDGER.verdict()

    print("1. the corpus, and both words of both tags")
    check(len(rows) >= MIN_MAPS, f"at least {MIN_MAPS} maps decode",
          f"{len(rows)} -- a shrunken corpus makes every ratio below easier "
          f"and must not pass quietly")
    t4 = refscan.score(rows, "refs4")
    t6 = refscan.score(rows, "refs6")

    for s in (t4, t6):
        check(s["prop_out_of_range"] == 0,
              f"tag {s['tag']}: every `prop` word indexes the prop array",
              f"{s['prop_in_range']} in range, {s['prop_out_of_range']} out. "
              f"This is the word already documented as an index; if it ever "
              f"failed, the decoder is misreading the pair and nothing else "
              f"in this file means anything")

    check(t6["value_out_of_range"] == 0,
          "tag 6: every `value` word ALSO indexes the prop array",
          f"{t6['value_in_range']} in range, {t6['value_out_of_range']} out")
    check(t4["value_out_of_range"] > t4["value_in_range"],
          "tag 4: its `value` word does NOT",
          f"{t4['value_in_range']} in range against "
          f"{t4['value_out_of_range']} out, max {t4['max_value']}")

    print("\n2. TIGHTNESS -- do the values saturate the array?")
    check(t6["tightness"]["median"] > 0.75,
          "tag 6's values fill most of the index range",
          f"median {t6['tightness']['median']}, p75 {t6['tightness']['p75']}, "
          f"max {t6['tightness']['max']}. Near 1 is what an index looks like; "
          f"a small fraction would mean the inequality holds by accident of "
          f"scale and section 1 proves nothing")
    check(t6["tightness"]["max"] <= 1.0,
          "and none exceeds the last index",
          f"max {t6['tightness']['max']} -- above 1.0 contradicts section 1")
    check(t6["tightness"]["above_0_9"] * 2 > t6["tightness"]["maps"],
          "on most maps individually, not just in aggregate",
          f"{t6['tightness']['above_0_9']} of {t6['tightness']['maps']} maps "
          f"over 0.9 -- a median can be carried by half the corpus")
    check(t6["tightness"]["exact_last_index"] > 0,
          "and some map's largest value IS the last prop index",
          f"{t6['tightness']['exact_last_index']} maps land exactly on "
          f"len(props)-1, which a bound with slack in it would never do")
    check(t4["tightness"]["median"] > 10.0,
          "tag 4's values are nowhere near an index range",
          f"median {t4['tightness']['median']} -- its words are about that "
          f"many times the prop count")

    print("\n3. THE SHUFFLE CONTROL -- is the bound about THIS map?")
    sh6 = t6["shuffle_control"]
    check(sh6["pct"] > 15.0,
          "tag 6's bound BREAKS against another map's prop count",
          f"{sh6['out_of_range']} of {sh6['rows']} ({sh6['pct']}%) fall out of "
          f"range when shuffled. If this were near zero the inequality would "
          f"be a fact about small integers, not about these maps, and the "
          f"whole reading would be vacuous")
    check(sh6["pct"] < 100.0,
          "but not completely, which is what a shared scale looks like",
          f"{sh6['pct']}% -- maps have comparable prop counts, so a real "
          f"per-map index survives some pairings. 100% would mean the counts "
          f"share no scale at all and the control proves less than it seems")

    print("\n4. the two tags SEPARATE, read by one decoder from one file")
    check(t6["value_out_of_range"] < t4["value_out_of_range"],
          "they disagree on the in-range question",
          f"tag 6 {t6['value_out_of_range']} out, tag 4 "
          f"{t4['value_out_of_range']} out")
    check(t4["tightness"]["median"] > 10 * t6["tightness"]["median"],
          "and on tightness by more than an order of magnitude",
          f"tag 4 {t4['tightness']['median']} against tag 6 "
          f"{t6['tightness']['median']}")
    check(t4["max_value"] > 10 * t6["max_value"],
          "and tag 4 reaches values an order of magnitude past tag 6's",
          f"{t4['max_value']} against {t6['max_value']} -- tag 4 runs to the "
          f"top of the u16 while tag 6 stays inside plausible prop counts")

    print("\n5. the self-references, which a sample missed")
    check(t6["self_references"] > 0,
          "tag 6 carries rows where value == prop",
          f"{t6['self_references']} of {t6['rows']}. A 40-map pass reported "
          f"ZERO and that is how a rare row disappears; any account of what "
          f"this relation means has to survive them")
    check(t4["self_references"] == 0,
          "and tag 4 carries none",
          f"{t4['self_references']} -- consistent with its word not indexing "
          f"the same array in the first place")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
