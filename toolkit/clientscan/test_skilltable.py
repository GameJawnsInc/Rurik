"""Check the skill-table reader against the client binary and against the wiki.

    python toolkit/clientscan/test_skilltable.py
    python toolkit/clientscan/test_skilltable.py --exe <path>

Two of the sections here are much stronger than the others, and it is worth
knowing which is which before trusting a green run.

Sections 1 and 2 are **structural**: they check that the located table declares
itself consistently and that corpus rows are well-formed. These can fail for the
right reason -- if the locator drifts onto a lookalike run of bytes, row 1 stops
being id 1, description ids stop trailing name ids by exactly one, and the
equip/PvP invariants collapse. But they are still our decoder agreeing with the
shape our decoder went looking for. Treat them as necessary, not sufficient.

Section 3 is the one with no circularity in it. The expected values come from
`wiki.guildwars.com` -- a source with no author, no code and no ancestry in
common with either the client binary or the extraction spec we worked from.
Nothing in this repo forces those numbers to match. `ceil(units/25)` over the
raw bytes either reproduces 115 independently documented displayed costs, or it
does not; the encoded energy byte either maps 11 to every skill the wiki shows
at 15 energy, or it does not. That is the check that earns the CORROBORATED
label in studies/skills/FINDINGS.md, and it is the reason this file exists.

Section 4 pins build-specific counts. A change there is a *finding* -- ArenaNet
still ships GW1 balance updates -- not necessarily a defect. Read the message.

READ-ONLY. This opens the client binary and never writes to it, never patches
it, and never launches it.
"""

import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from skilltable import (  # noqa: E402
    RECORD_SIZE, decode_energy, displayed_adrenaline, locate_table,
    parse_record, player_corpus,
)

DEFAULT_EXE = r"C:\gw\Gw.exe"

# MEASURED 2026-08-06 against Gw.exe (10,483,904 bytes). Build-specific: a new
# client build legitimately changes these. Tyria-Extractor independently reports
# the same 1,333 from its own Rust implementation of the same structural search.
EXPECTED_RECORD_COUNT = 3443
EXPECTED_CORPUS = 1333

# WIKI (GWW), crawled 2026-08-06 via the MediaWiki API: skill id -> the
# adrenaline cost the wiki says the client displays. Community documentation of
# observed retail behaviour -- see .claude/skills/browse-gw-wiki/references/
# labeling.md for why this counts as an independent witness. Wiki TEXT and
# game facts only; no client bytes live in this repo.
WIKI_ADRENALINE = {
    355: 7, 358: 9, 335: 4, 317: 4, 354: 8, 318: 5, 907: 8, 1142: 1, 869: 4,
    1696: 7, 1415: 6, 334: 5, 337: 5, 340: 6, 357: 4, 1403: 6, 342: 5, 905: 5,
    1416: 6, 380: 8, 373: 5, 345: 5, 2197: 7, 3204: 5, 366: 4, 338: 8, 889: 5,
    1697: 8, 336: 8, 1404: 4, 331: 6, 359: 5, 849: 5, 1136: 5, 339: 5, 384: 6,
    351: 7, 850: 6, 906: 6, 1407: 4, 383: 8, 2009: 3, 2010: 5, 996: 6, 892: 5,
    329: 6, 888: 4, 1144: 8, 382: 4, 348: 4, 1137: 6, 360: 4, 851: 8, 319: 4,
    1702: 8, 387: 4, 2107: 6, 2008: 4, 2195: 4, 2858: 4, 1548: 6, 1568: 2,
    1554: 4, 1559: 6, 1558: 4, 1565: 4, 1569: 3, 1600: 2, 1546: 6, 3026: 4,
    3148: 6, 1571: 8, 1782: 4, 1570: 3, 1567: 8, 1770: 3, 1563: 6, 1603: 6,
    1547: 2, 2238: 3, 2209: 4, 3442: 2, 1602: 8, 1550: 4, 1552: 3, 1605: 7,
    1539: 6, 1762: 4, 2147: 6, 2070: 4, 3366: 4, 1532: 5, 1767: 7, 1486: 5,
    1753: 6, 1487: 7, 1491: 5, 1545: 5, 2012: 6, 3265: 5, 3264: 7, 1537: 6,
    2215: 7, 2340: 10, 3295: 3, 3296: 6, 2761: 3, 3383: 4, 3382: 8, 2354: 4,
    2213: 4, 2685: 10, 2732: 8, 2214: 6, 2759: 4,
}

# WIKI (GWW), same crawl: every skill the wiki shows at 15 and at 25 energy.
# The client is claimed to store these as the encoded bytes 11 and 12.
WIKI_ENERGY_15 = {
    474, 435, 434, 392, 467, 2108, 2142, 1472, 1213, 287, 303, 272, 943, 3232,
    1263, 270, 273, 255, 262, 151, 114, 84, 142, 123, 106, 103, 834, 1260, 128,
    110, 1077, 1075, 156, 108, 88, 3058, 28, 859, 65, 75, 45, 1056, 76, 5, 56,
    48, 3194, 1340, 188, 844, 217, 205, 166, 190, 212, 211, 196, 1093, 884,
    1372, 171, 3021, 2807, 176, 239, 177, 2806, 572, 925, 988, 1218, 1252,
    1235, 1249, 923, 1745, 2655, 3010, 3015, 789, 1237, 1748, 1222, 871, 3006,
    3025, 911, 1266, 3005, 1774, 2876, 1560, 3032, 2112, 2109, 1516, 1505,
    2884, 3378, 2414, 3238, 2760, 3073, 3241,
}
WIKI_ENERGY_25 = {
    408, 457, 1721, 475, 304, 2895, 144, 863, 94, 1086, 170, 167, 234, 865,
    192, 215, 3396, 218, 189, 921, 3023, 3017, 3014, 2691, 981, 982, 3016,
    3013, 3009, 1592,
}

fails = []


def check(cond, msg):
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        fails.append(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=DEFAULT_EXE)
    args = ap.parse_args()

    if not os.path.exists(args.exe):
        print(f"no client binary at {args.exe}")
        print("Pass --exe, or see RUNBOOK.md. This test reads the client "
              "read-only; it never patches or launches it.")
        return 1

    with open(args.exe, "rb") as fh:
        data = fh.read()
    print(f"client: {args.exe} ({len(data):,} bytes)")

    base, count, score = locate_table(data)
    rows = [parse_record(data, base, i) for i in range(count)]
    by_id = {r["id"]: r for r in rows}
    corpus = set(player_corpus(rows))
    print(f"table at file offset {base}, {count} rows, "
          f"{len(corpus)} in corpus, detection score {score}")

    print("\n1. the table declares itself consistently")
    # The locator required these to accept the candidate, so reaching here is
    # the check; restate them so a reader sees what was actually proven.
    check(rows[0]["linked_id"] == count,
          f"row 0 declares the record count at +0x2c ({count})")
    check(base + count * RECORD_SIZE <= len(data),
          "the whole table fits inside the image")
    live = [r for r in rows if r["name_id"]]
    trailing = [r for r in live if r["description_id"] == r["name_id"] + 1]
    check(len(trailing) > len(live) * 0.9,
          f"description id trails name id by 1 on {len(trailing)}/{len(live)} "
          f"live rows")

    print("\n2. corpus membership is well-formed")
    check(all(by_id[i]["equip_family"] == 1 for i in corpus),
          "every corpus row has equip/use-family 1")
    check(not any(by_id[i]["pvp_only"] for i in corpus),
          "no corpus row carries the PvP flag")
    # Our own decoder agreeing with itself -- weak, but it catches a refactor
    # that changes one path and not the other.
    check(all(r["adrenaline"] == displayed_adrenaline(r["adrenaline_units"])
              for r in rows),
          "displayed adrenaline is ceil(units/25) on every row")
    check(decode_energy(11) == 15 and decode_energy(12) == 25
          and decode_energy(7) == 7,
          "energy decode maps 11->15, 12->25, and leaves 7 literal")

    print("\n3. the client agrees with the wiki, which has no stake in our code")
    known = {i: v for i, v in WIKI_ADRENALINE.items() if i in by_id}
    bad = [(i, by_id[i]["adrenaline_units"], v, math.ceil(by_id[i]["adrenaline_units"] / 25))
           for i, v in known.items()
           if by_id[i]["adrenaline_units"]
           and math.ceil(by_id[i]["adrenaline_units"] / 25) != v]
    check(len(known) >= 100,
          f"{len(known)} of {len(WIKI_ADRENALINE)} wiki adrenaline ids present "
          f"in this build")
    check(not bad, f"ceil(units/25) reproduces every wiki cost"
                   + (f" -- MISMATCHES {bad[:5]}" if bad else ""))
    # The rival rule must still be refutable, or section 3 proves nothing about
    # which of the two we picked.
    rival = [i for i, v in known.items()
             if by_id[i]["adrenaline_units"]
             and (by_id[i]["adrenaline_units"] // 25) + 1 != v]
    check(len(rival) > 0,
          f"floor(units/25)+1 is refuted by {len(rival)} of these skills")

    for want_raw, want_energy, ids in ((11, 15, WIKI_ENERGY_15),
                                       (12, 25, WIKI_ENERGY_25)):
        present = [i for i in ids if i in by_id]
        wrong = [(i, by_id[i]["energy_raw"]) for i in present
                 if by_id[i]["energy_raw"] != want_raw]
        check(not wrong,
              f"all {len(present)} skills the wiki shows at {want_energy} "
              f"energy store the encoded byte {want_raw}"
              + (f" -- EXCEPTIONS {wrong[:5]}" if wrong else ""))

    print("\n4. build-specific counts (a change here is a finding, not a bug)")
    check(count == EXPECTED_RECORD_COUNT,
          f"{EXPECTED_RECORD_COUNT} rows (got {count}) -- if this moved, the "
          f"client was updated; re-run the wiki join before trusting old numbers")
    check(len(corpus) == EXPECTED_CORPUS,
          f"{EXPECTED_CORPUS} player-corpus rows (got {len(corpus)}) -- this is "
          f"also Tyria-Extractor's independent count")

    print("\n" + ("ALL CHECKS PASSED" if not fails
                  else f"{len(fails)} CHECK(S) FAILED"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
