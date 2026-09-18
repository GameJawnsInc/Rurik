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
sys.path.insert(0, os.path.dirname(HERE))
from skilltable import (NO_PROJECTILE, CONTENT_FIELDS,   # noqa: E402
    RECORD_SIZE, build_of, decode_energy, displayed_adrenaline, emit_content,
    locate_table, parse_record, player_corpus,
)
import checks  # noqa: E402
import pinned  # noqa: E402

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool in
# this directory, and names the copy it returned. This module used to spell it
# `C:\gw\Gw.exe` -- the owner's live install, which auto-updates and is
# therefore not necessarily the build every address below is measured against.
find_exe = pinned.find

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

# WIKI (GWW), crawled 2026-08-14 via the browser (action=raw wikitext), for
# the scaling window +0x44..+0x68. The THIRD witness for these values: the
# wiki shares no author, code or ancestry with either the client binary or
# Tyria-Extractor's spec, so wiki + client agreeing is real corroboration
# rather than one lineage wearing two hats. Each skill's
# `{{Skill progression}}` template, verbatim:
#
#   318 Defy Pain      var1 "+ Maximum health" 90->300, var2 "Damage
#                      reduction" 1->10. Duration is NOT a progression var --
#                      the description says a flat "For 20 seconds".
#   322 Power Attack   var1 "+ Damage" 10->40.
#   316 "To the Limit!" var1 "Max foes" 1->6, var2 "Duration" 10->20,
#                      var3 "+ Max health" 10->60.
#   319 Rush           var1 "Duration" 8->20. Nothing else scales: the
#                      description's "move 25% faster" is a CONSTANT, and the
#                      client's scale slot holds exactly 25 with its bit
#                      clear -- which is why the bitfield is consulted and not
#                      just the endpoints.
#
# Stored as (duration0, duration15, scale0, scale15, bonus0, bonus15) against
# our decode's field order, with None where the wiki lists no progression var
# for that set. A pinned crawl, not a live fetch: the suite must run on a bare
# machine with no network.
WIKI_PROGRESSION = {
    318: (None, None, 90, 300, 1, 10),
    322: (None, None, 10,  40, None, None),
    316: (10, 20, 10, 60, 1, 6),
    319: (8, 20, None, None, None, None),
}

# ...and the same crawl's costs and timings, which the window sections do not
# cover: (energy, adrenaline, recharge). None where the infobox omits the key
# (a skill carries only the cost keys that apply to it).
WIKI_COSTS = {
    318: (None, 5, None),
    322: (5, None, 3),
    316: (5, None, 10),
    319: (None, 4, None),
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

# WIKI (GWW), fetched 2026-09-17 through the MediaWiki API and joined by the
# infobox's own `id` -- studies/daggers/FINDINGS.md F1-F2. The concise
# description's "Must follow a(n) ... attack" clause, as the BIT the client is
# claimed to store at +0x14. Ids only; no skill name is carried here.
WIKI_MUST_FOLLOW = {
    0x01: (781, 1033, 1643),                                   # ... a dual
    0x02: (780, 975, 988, 1021, 1022, 1987, 1988),             # ... a lead
    0x04: (775, 776, 777, 976, 986, 1019, 1020, 1634, 1986, 2135),  # off-hand
}
# Chain skills whose page carries NO such clause: nine leads, and four off-hands
# conditioned on a knockdown or an enchantment instead. (1636 is left out: its
# word is 0x10, one row, UNVERIFIED.)
WIKI_NO_CHAIN_CLAUSE = (779, 782, 783, 948, 1023, 1024, 1025, 1026, 1637,
                        778, 989, 1635, 1990)
# The infobox `type` (Lead / Off-Hand / Dual Attack) as the claimed +0x30 value,
# plus the four NON-attacks whose description says "counts as a lead / an
# off-hand attack" -- the refutable part, since nothing else marks them.
WIKI_COMBO = {1: (779, 782, 783, 948, 1023, 1024, 1025, 1026, 1637),
              2: (778, 780, 781, 976, 988, 989, 1021, 1022, 1635, 1636,
                  1987, 1988, 1990),
              3: (775, 776, 777, 975, 986, 1019, 1020, 1634, 1986, 2135)}
WIKI_COUNTS_AS = {786: 1, 2116: 1, 974: 2, 1045: 2}
PROF_ASSASSIN = 7
WEAPON_DAGGERS = 0x08
# attribute id -> the weapon bit its attack skills must carry. The attribute
# column is the witness: it is decoded independently of +0x24.
MASTERY_BIT = {18: 0x01, 25: 0x02, 29: 0x08, 19: 0x10, 41: 0x20, 37: 0x40,
               20: 0x80}

# FLOOR 57 = every check this file executes on a real client binary, counted
# from a green run on 2026-08-14 against Gw.exe: 3 structural (§1) + 4 corpus
# (§2) + 5 wiki joins (§3: two adrenaline, one rival-rule refutation, and the
# 15/25-energy pair) + 4 text-resolution (§4) + 2 build counts (§5) + 8
# content-emitter checks (§6, added with --emit-content) + 8 scaling-window
# checks (§7: 4 endpoint reproductions + 4 green-render-rule) + 12 wiki
# third-witness checks (§8: 4 endpoint joins, 4 no-unlisted-green, 4 costs)
# + 10 chain-and-weapon checks (§9, 2026-09-17, floor 46 -> 56) + 1 AoE-radius
# check (DAGGERS-B8, 56 -> 57). None of them is
# conditional once the binary opens, so a run that reports fewer has lost a
# section rather than passed -- which is exactly the failure §3 would hide,
# since dropping the wiki join is what turns this file back into our decoder
# agreeing with itself.
LEDGER = checks.Ledger("skill table", floor=63)   # + 6 projectile / impact checks (section 10, WEAPONS-C10, 2026-09-18, 57 -> 63)
check = checks.adopt(LEDGER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None)
    args = ap.parse_args()

    args.exe = args.exe or find_exe()[0]
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

    print("\n4. the string ids resolve to the names the client renders")
    try:
        import textrec
    except ImportError:                                     # noqa: BLE001
        check(False, "textrec is importable")
    else:
        with textrec.TextIndex(args.exe) as ix:
            named = [r for r in rows if r["name_id"] and ix.get(r["name_id"])]
            check(len(named) >= EXPECTED_RECORD_COUNT - 8,
                  f"{len(named)} of {len(rows)} skill names resolve to text")
            # These two identities were established in studies/skills by
            # DRIVING A LIVE CLIENT and reading what it drew, long before any
            # offline decoder existed. Reproducing them from Gw.dat is the
            # decoder agreeing with the game rather than with itself.
            for sid, want in ((322, "Power Attack"), (318, "Defy Pain")):
                got = ix.get(by_id[sid]["name_id"]) if sid in by_id else None
                check(got == want,
                      f"skill {sid} decodes to {want!r}, which is what the "
                      f"live client drew (got {got!r})")
            trail = [r for r in rows
                     if r["description_id"] == r["name_id"] + 1
                     and ix.get(r["name_id"]) and ix.get(r["description_id"])]
            check(len(trail) > 3000,
                  f"name and description both resolve on {len(trail)} of the "
                  f"rows where the ids are adjacent")

    print("\n5. build-specific counts (a change here is a finding, not a bug)")
    check(count == EXPECTED_RECORD_COUNT,
          f"{EXPECTED_RECORD_COUNT} rows (got {count}) -- if this moved, the "
          f"client was updated; re-run the wiki join before trusting old numbers")
    check(len(corpus) == EXPECTED_CORPUS,
          f"{EXPECTED_CORPUS} player-corpus rows (got {len(corpus)}) -- this is "
          f"also Tyria-Extractor's independent count")

    print("\n6. the content emitter: server rows, stamped from the bytes")
    import tempfile
    import tomllib
    build = build_of(data)
    check(build == 38797,
          f"the build stamp is DERIVED from the image's sha256 (got {build}) "
          f"-- never typed in, so a wrong exe cannot stamp a plausible row")
    check(build_of(b"not a client image") is None,
          "an image matching no pristine build stamps nothing",
          "the emitter refuses instead -- a row with a guessed build survives "
          "every later audit, which is worse than no row")
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "skills.toml")
        n = emit_content(rows, sorted(corpus), build, args.exe, out)
        with open(out, "rb") as fh:
            doc = tomllib.load(fh)
        skills = doc["skills"]
        check(n == len(corpus) and len(skills) == n,
              f"one TOML table per corpus skill ({n})")
        # The three skills ArenaNet's own wire corroborated
        # (studies/reconstruction/FINDINGS.md 2.9.2: the 0x00E5 field matched
        # +0x4C on exactly 1 of 41 columns; activation/aftercast sit beside
        # it). Pinned as LITERALS -- wire and table must both move for these
        # to change.
        for sid, act, aft, rech in (("153", 1.0, 0.75, 8),
                                    ("105", 2.0, 0.75, 6),
                                    ("394", 0.0, 0.0, 3)):
            r = skills[sid]
            check((r["activation"], r["aftercast"], r["recharge"])
                  == (act, aft, rech),
                  f"skill {sid} emits ({act}, {aft}, {rech}) -- the "
                  f"live-corroborated trio",
                  f"got ({r['activation']}, {r['aftercast']}, {r['recharge']})")
        prov = skills["153"]["provenance"]
        check(prov["source"] == "client-table"
              and prov["extractor"] == "toolkit/clientscan/skilltable.py"
              and prov["build"] == 38797,
              "every row carries the gate's two conditions: extractor named, "
              "build recorded")
        # And the gate itself agrees: the row loads through content.py's
        # provenance check rather than merely looking like it would.
        sys.path.insert(0, os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "..", ".."))
        sys.path.insert(0, os.path.join(os.path.dirname(
            os.path.abspath(__file__)), ".."))
        import content
        row = dict(skills["153"])
        content._check_provenance("skills", "153", row)
        check(True, "content.py's client-table gate accepts an emitted row")

    print("\n7. the rank-0/rank-15 scaling window reproduces the anecdote")
    # studies/skills/FINDINGS.md section 4, the only in-repo ground truth for
    # +0x44..+0x68: four skills the owner read off the live client, endpoint
    # for endpoint. Pinned as LITERALS -- these are what the client draws, and
    # a decode that drifts must go red against them, not move with them.
    # (id: args, dur0, dur15, scale0, scale15, bonus0, bonus15)
    ANECDOTE = {
        318: (7, 20, 20, 90, 300, 1, 10),   # Defy Pain
        322: (2,  0,  0, 10,  40, 0,  0),   # its clone (scale set only)
        316: (7, 10, 20, 10,  60, 1,  6),   # "To the Limit!"
        319: (1,  8, 20, 25,  25, 0,  0),   # Rush (duration set only)
    }
    for sid, want in ANECDOTE.items():
        r = by_id[sid]
        got = (r["skill_arguments"], r["duration0"], r["duration15"],
               r["scale0"], r["scale15"], r["bonus_scale0"], r["bonus_scale15"])
        check(got == want,
              f"skill {sid} window == the owner's live reading",
              f"got {got}, want {want}")
    # The green-render rule the anecdote establishes, as an assertion rather
    # than prose: a set renders green when its bit is set AND its endpoints
    # differ. Defy Pain's duration bit is set but 20==20, so exactly its
    # scale and bonus render -- two greens, which is the whole thing the
    # owner noticed was missing on the clone.
    def greens(r):
        bits = r["skill_arguments"]
        n = 0
        n += bool(bits & 1) and r["duration0"] != r["duration15"]
        n += bool(bits & 2) and r["scale0"] != r["scale15"]
        n += bool(bits & 4) and r["bonus_scale0"] != r["bonus_scale15"]
        return n
    for sid, want_green in ((318, 2), (322, 1), (316, 3), (319, 1)):
        check(greens(by_id[sid]) == want_green,
              f"skill {sid} renders {want_green} green value(s) by the "
              f"enabled-and-differing rule",
              f"got {greens(by_id[sid])}")

    print("\n8. the wiki, the third witness for the scaling window")
    # This is section 3's argument applied to the window: the anecdote above
    # and the client are OUR reading of OUR artifact. GWW is twenty years of
    # players reading the game screen, with no ancestry in our code, our
    # captures, or Tyria-Extractor's spec -- so agreement here is
    # CORROBORATION and disagreement is a real finding.
    for sid, want in WIKI_PROGRESSION.items():
        r = by_id[sid]
        got = (r["duration0"], r["duration15"], r["scale0"], r["scale15"],
               r["bonus_scale0"], r["bonus_scale15"])
        # Compare only the sets the wiki actually lists a progression var
        # for; a None means "the wiki says this does not scale", which the
        # bitfield check below is what tests.
        pairs = [(g, w) for g, w in zip(got, want) if w is not None]
        check(all(g == w for g, w in pairs) and len(pairs) >= 2,
              f"skill {sid}: every endpoint the wiki lists matches the "
              f"client's window ({len(pairs)} value(s))",
              f"client {got} vs wiki {want}")
        # And the other direction: a set the wiki does NOT list must have its
        # bit clear or its endpoints equal -- otherwise we would be decoding
        # a green the game does not draw. Rush is the sharp case: its scale
        # slot holds 25 ("move 25% faster") with the bit clear.
        bits = r["skill_arguments"]
        unlisted_render = []
        for (bit, lo, hi, nm) in ((1, "duration0", "duration15", "duration"),
                                  (2, "scale0", "scale15", "scale"),
                                  (4, "bonus_scale0", "bonus_scale15",
                                   "bonus")):
            idx = {"duration": 0, "scale": 2, "bonus": 4}[nm]
            if want[idx] is None and (bits & bit) and r[lo] != r[hi]:
                unlisted_render.append(nm)
        check(not unlisted_render,
              f"skill {sid}: no set renders green that the wiki does not list",
              f"would render {unlisted_render} -- args={bits}, "
              f"window={got}")

    for sid, (energy, adrenaline, recharge) in WIKI_COSTS.items():
        r = by_id[sid]
        wrong = []
        if energy is not None and r["energy"] != energy:
            wrong.append(f"energy {r['energy']} vs {energy}")
        if adrenaline is not None and r["adrenaline"] != adrenaline:
            wrong.append(f"adrenaline {r['adrenaline']} vs {adrenaline}")
        if recharge is not None and r["recharge"] != recharge:
            wrong.append(f"recharge {r['recharge']} vs {recharge}")
        check(not wrong,
              f"skill {sid}: the wiki's costs and recharge match the table",
              "; ".join(wrong) if wrong else
              f"energy={r['energy']}, adrenaline={r['adrenaline']}, "
              f"recharge={r['recharge']}")

    print("\n9. the chain and the weapon mask (studies/daggers F1-F3)")
    inc = [by_id[i] for i in corpus]
    bad = [(bit, i, by_id[i]["combo_req"]) for bit, ids in WIKI_MUST_FOLLOW.items()
           for i in ids if by_id[i]["combo_req"] != bit]
    n = sum(len(v) for v in WIKI_MUST_FOLLOW.values())
    check(not bad, f"+0x14 carries exactly the wiki's must-follow bit on all {n} rows",
          f"MISMATCHES {bad[:5]}" if bad else "0x01 dual, 0x02 lead, 0x04 off-hand")
    bad = [(i, by_id[i]["combo_req"]) for i in WIKI_NO_CHAIN_CLAUSE
           if by_id[i]["combo_req"]]
    check(not bad, f"and is 0 on the {len(WIKI_NO_CHAIN_CLAUSE)} chain skills "
                   f"whose page has no such clause", str(bad[:5]) if bad else "")
    # The obvious rival -- the bit is 1 << (required combo - 1) -- must be
    # refutable, or the first check only proves we can read a u32.
    need = {0x01: 3, 0x02: 1, 0x04: 2}
    rival = [i for bit, ids in WIKI_MUST_FOLLOW.items() for i in ids
             if by_id[i]["combo_req"] != 1 << (need[bit] - 1)]
    check(len(rival) >= 10, "the rival rule 1 << (combo - 1) is refuted",
          f"by {len(rival)} of {n} rows: dual is bit 0, not bit 2")
    bad = [(i, by_id[i]["combo"], want) for want, ids in WIKI_COMBO.items()
           for i in ids if by_id[i]["combo"] != want]
    check(not bad, f"+0x30 is the wiki's Lead / Off-Hand / Dual type on all "
                   f"{sum(len(v) for v in WIKI_COMBO.values())} attack rows",
          str(bad[:5]) if bad else "")
    bad = [(i, by_id[i]["combo"], want) for i, want in WIKI_COUNTS_AS.items()
           if by_id[i]["combo"] != want]
    check(not bad, "and the four NON-attacks the wiki says 'count as' a lead or "
                   "an off-hand carry that value", str(bad) if bad else "")
    stray = sorted(r["id"] for r in inc if r["combo"]
                   and r["profession"] != PROF_ASSASSIN)
    check(stray == [2116], "outside the Assassin the corpus holds exactly one "
                           "chain row, the one the wiki names", str(stray))
    stray = sorted(r["id"] for r in inc if r["combo_req"]
                   and r["profession"] != PROF_ASSASSIN)
    check(not stray, "and no must-follow word at all", str(stray[:5]))
    # The first draft said "every chain attack" and went RED on 2116: the one
    # lead attack outside the profession takes ANY melee weapon (0xB9), so a
    # chain can be opened with a sword. The claim is the Assassin's own rows.
    sin = [r for r in inc if r["combo"] and r["type_code"] == 14
           and r["profession"] == PROF_ASSASSIN]
    bad = sorted(r["id"] for r in sin if r["weapon_req"] != WEAPON_DAGGERS)
    check(not bad and len(sin) >= 30,
          f"every Assassin chain ATTACK wants daggers and nothing else "
          f"(+0x24 == 0x08 on {len(sin)} rows)", str(bad[:5]))
    # DAGGERS-B8: +0x6C is the area-of-effect radius. The value SET is what
    # could refute it -- a wrong offset has no reason to land on the game's
    # four named radii -- and 775's 156 is the one the dagger tape exercised.
    import collections as _collections
    radii = _collections.Counter(r["aoe_range"] for r in inc if r["aoe_range"])
    top4 = {k for k, _n in radii.most_common(4)}
    check(top4 == {156.0, 240.0, 312.0, 1000.0} and by_id[775]["aoe_range"] == 156.0,
          "+0x6C is the AoE radius: its four commonest values are adjacent "
          "156, nearby 240, in the area 312 and earshot 1000, and Death "
          "Blossom's is 156", f"{radii.most_common(6)}, 775 -> "
          f"{by_id[775]['aoe_range']}")
    check(by_id[2116]["weapon_req"] == 0xB9,
          "and the lone outsider opens a chain with any melee weapon",
          f"2116 +0x24 = {by_id[2116]['weapon_req']:#x}")
    bad = sorted((r["id"], r["attribute"], r["weapon_req"]) for r in inc
                 if r["weapon_req"] and r["attribute"] in MASTERY_BIT
                 and not r["weapon_req"] & MASTERY_BIT[r["attribute"]])
    held = sum(1 for r in inc if r["weapon_req"] and r["attribute"] in MASTERY_BIT)
    check(not bad and held >= 100,
          f"a weapon-mastery skill's mask always holds its own weapon's bit "
          f"({held} rows over {len(MASTERY_BIT)} masteries)", str(bad[:5]))

    print("\n10. the projectile and its impact (+0x88, +0x84; WEAPONS-C10)")
    # Named by the WIRE: the live corpus's skill shots (weaponcensus.py
    # --skill-shots, 151 launches) name the projectile every skill launched,
    # and exactly this dword reproduces them. Pinned as LITERALS -- the wire
    # and the table must both move for these to change.
    check(all(by_id[sid]["projectile"] == 680 for sid in (392, 394, 396, 402)),
          "+0x88 reads 680 on Pin Down, Power Shot, Dual Shot and Determined Shot -- "
          "the projectile each launched on the wire (12 of 12 launches)",
          str({sid: by_id[sid]["projectile"] for sid in (392, 394, 396, 402)}))
    check(by_id[404]["projectile"] == NO_PROJECTILE == 2077
          and by_id[1197]["projectile"] == NO_PROJECTILE,
          "and 2077 -- the visual pair's own 'none' -- on Poison Arrow and Needling Shot, "
          "whose launches carried the held bow's arrow (143, or 343 under Kindle Arrows)")
    check(by_id[858]["projectile"] == 854 and by_id[186]["projectile"] == 343
          and by_id[229]["projectile"] == 403 and by_id[230]["projectile"] == 405,
          "the spells agree too: Dancing Daggers 854, Fireball 343, Lightning Orb 403, "
          "Lightning Javelin 405 -- each the 0x00A4 field 5 its caster launched")
    check(by_id[433]["projectile"] == 343 and by_id[433]["impact_visual"] == 344
          and by_id[186]["impact_visual"] == 344 and by_id[229]["impact_visual"] == 404
          and by_id[858]["impact_visual"] == 855
          and all(by_id[sid]["impact_visual"] == NO_PROJECTILE for sid in (392, 394, 404)),
          "+0x84 is the IMPACT visual: 344 behind Kindle Arrows' and Fireball's 343 (the "
          "[20, target, caster, 344] retail sends at every arrival), 404 behind the Lightning "
          "pair, 855 behind 854, and none on the bow attacks; a preparation carries the arrow "
          "it SUBSTITUTES (Kindle Arrows 343)")
    with_proj = [r["id"] for r in inc if r["projectile"] != NO_PROJECTILE]
    n_attack = sum(1 for r in inc if r["projectile"] != NO_PROJECTILE and r["type_code"] == 14)
    check(30 <= len(with_proj) <= 400 and n_attack >= 4,
          f"{len(with_proj)} corpus skills name a projectile of their own, {n_attack} of them "
          f"attack skills -- a value SET a wrong offset has no reason to land on (build-specific; "
          f"a change here is a finding)")
    check("projectile" in CONTENT_FIELDS and "impact_visual" in CONTENT_FIELDS,
          "the emitter carries both `projectile` and `impact_visual` to the server's rows "
          "(W2c reads the first, W2e the second)")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
