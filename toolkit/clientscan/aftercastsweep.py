#!/usr/bin/env python3
"""CASTMECH-P4: sweep `+0x40` (aftercast) against type_code and profession.

    python toolkit/clientscan/aftercastsweep.py
    python toolkit/clientscan/aftercastsweep.py --out <path>   # also save the report text

Python 3 standard library only. Read-only: opens the client binary via
`toolkit/clientscan/pinned.find()` (the pinned pristine build, 38797 by
default) and never writes to it, never launches it. Reuses
`toolkit/clientscan/skilltable.py`'s locator and row decoder rather than
re-deriving the table layout.

WHAT THIS CLOSES. `studies/castmech/FINDINGS.md` §7, CASTMECH-P4: "`+0x40`
sweep vs the Aftercast page's exception lists (Dolyak 0? Ranger interrupts
0.75? Factions preparations 0.75?) -- offline, next `skilltable.py`
regeneration; pure client-table read with WIKI as the cross-witness." §3 of
the same file already established, from a live wire capture (n=6, two
professions), that `+0x40` is exactly the E5->E3 aftercast gap: 0.75s for two
Necromancer spells and 0.000s for a Ranger attack skill, discriminating
against a rival "fixed 0.75 constant" reading. This tool is the offline half
of that: read `+0x40` for the WHOLE table (3,443 rows, not six samples) and
see whether "spell family -> 0.75, everything else -> 0" actually holds, or
whether the client carries per-skill exceptions the six-row sample could not
have shown.

PREDICTION, stated before the numbers were read (studies/skills/FINDINGS.md
§35.3's type-code table names the words; CASTMECH §3's wire result sets the
baseline):

  * type_code 5 (Spell), 4 (Hex Spell), 6 (Enchantment Spell), 7 (Signet),
    9 (Well Spell), 11 (Ward Spell), 24 (Item Spell), 25 (Weapon Spell) --
    modal aftercast 0.75, per the wire result and the general "casting"
    shape of the Aftercast wiki page.
  * type_code 3 (Stance), 8 (Condition), 12 (Glyph)+19 (Preparation, but see
    below), 15 (Shout), 20 (Pet Attack), 21 (Trap), 14 (Attack, weapon-named)
    -- modal aftercast 0.000, per the wire result for the Ranger attack skill
    and the general "instant" shape of the same wiki page.
  * NAMED EXCEPTIONS TO WATCH FOR (this is what the sweep is FOR -- a modal
    rule that holds everywhere would make this script pointless):
      - "Dolyak Signet" -- the wiki's Aftercast page is read here as claiming
        a Signet with aftercast 0 against the type's own 0.75 modal. UNKNOWN
        id from this table alone (ids do not carry names in this repo,
        CLAUDE.md's authored-text rule) -- the exception list below is
        exactly the join that would find it: a type-7 row whose aftercast is
        0 while the type's modal is 0.75.
      - "Ranger interrupts" (e.g. a Distracting/Savage-family attack) at
        0.75 against type 14's own 0.000 modal -- a type-14 row NOT matching
        its modal is the same shape.
      - "Factions preparations" at 0.75 against a possible type-19 modal of
        0 -- if Preparation's own modal reads 0, its outliers show here; if
        it reads 0.75 the wiki's claim is instead "preparations generally
        0.75" and this table already agrees, which is itself worth knowing.
  * type_code 0 (no type -- non-skill rows structurally present in the same
    array; see skilltable.py's own note that the table is broader than the
    player corpus) is not expected to carry a meaningful aftercast at all and
    is reported separately rather than folded into the histogram's headline.

WHAT COUNTS AS A ROW. Every row the locator returns with a nonzero name_id
(skilltable.py's own definition of "live" -- see test_skilltable.py section
1). This build's table (38797) turns out to have name_id set on all 3,443
rows, so "live" here is the whole table; a future build where that is not
true will narrow automatically.

TWO POPULATIONS, AND THE EXCEPTION LIST USES THE NARROWER ONE. A first pass
over all 3,443 live rows found the modal table buried under noise: 2,110 live
rows sit OUTSIDE `skilltable.player_corpus()` (equip_family 1, PvP flag
clear) -- MEASURED here, not asserted -- and a large share of those carry
profession 0 / activation 0.0 / recharge 0.0 simultaneously (68 of type 5's
122 "exceptions" alone), which is the signature of an unused table slot or a
monster-only definition, not a played skill with an interesting aftercast.
The wiki's Aftercast exception list is about skills a player presses, so the
EXCEPTION LIST below is restricted to `player_corpus()` rows; the full-table
histogram and modal table are printed first, unrestricted, so the excluded
noise stays visible rather than silently dropped.

NO SKILL NAMES ARE EMITTED. Only ids, type_code, profession, activation,
recharge and aftercast -- all MEASURED numbers, all CLIENT-DATA per
studies/skills/FINDINGS.md section 1. The type_code and profession WORDS
printed alongside the numbers (Spell, Warrior, ...) are short proper-noun
labels already published in this repo (studies/skills/FINDINGS.md section
35.3's own table, and toolkit/clientscan/attribtable.py's PROFESSION_NAMES)
-- not authored bodies of text, and not re-derived here; they exist purely to
make this report legible to a human reader and nothing downstream parses
them back out.

This is a report script, not a test: it prints findings for a human (and, on
--out, saves them to a file) rather than asserting pass/fail through
toolkit/checks.py. Nothing here is a regression gate.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinned  # noqa: E402
from skilltable import locate_table, parse_record, player_corpus  # noqa: E402

find_exe = pinned.find

# OURS, for reading the dump -- studies/skills/FINDINGS.md section 35.3 (the
# client's own switch, walked and cross-checked against ten independently
# known codes at bias 0). Not re-derived here; carried as a label only. Codes
# absent from this dict print as "?" rather than guessing a word.
TYPE_WORDS = {
    0: "(no type)",
    1: "Blessing",
    2: "Party Bonus",
    3: "Stance",
    4: "Hex Spell",
    5: "Spell",
    6: "Enchantment Spell",
    7: "Signet",
    8: "Condition",
    9: "Well Spell",
    10: "Skill",
    11: "Ward Spell",
    12: "Glyph",
    13: "Title",
    14: "Attack (weapon-named)",
    15: "Shout",
    16: "Skill",  # same word as 10, different string record -- FINDINGS 35.4
    17: "(unnamed by client)",
    18: "(unnamed by client)",
    19: "Preparation",
    20: "Pet Attack",
    21: "Trap",
    22: "(profession/title-conditioned)",
    23: "Environment Effect",
    24: "Item Spell",
    25: "Weapon Spell",
    26: "Form",
    27: "Chant",
    28: "Echo",
    29: "Disguise",
}

# OURS, for reading the dump -- same convention as
# toolkit/clientscan/attribtable.py's PROFESSION_NAMES. 0 is "no profession"
# here (this table's own encoding; attribtable.py's attribute table instead
# uses 11 for that -- two different fields, not a contradiction).
PROFESSION_NAMES = {
    0: "(none)", 1: "Warrior", 2: "Ranger", 3: "Monk", 4: "Necromancer",
    5: "Mesmer", 6: "Elementalist", 7: "Assassin", 8: "Ritualist",
    9: "Paragon", 10: "Dervish",
}


def sweep(rows: list[dict]) -> dict:
    """Bucket every live row by type_code, and find the modal aftercast."""
    by_type: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_type[r["type_code"]].append(r)

    modal_by_type: dict[int, float] = {}
    for t, trows in by_type.items():
        counts = Counter(r["aftercast"] for r in trows)
        # Counter.most_common is stable on insertion order for ties; break
        # ties on the value itself so the modal pick does not depend on row
        # order, which is an accident of table layout rather than a fact.
        best = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
        modal_by_type[t] = best[0]

    exceptions = []
    for t, trows in by_type.items():
        modal = modal_by_type[t]
        for r in trows:
            if r["aftercast"] != modal:
                exceptions.append({**r, "type_modal": modal})

    return {
        "by_type": by_type,
        "modal_by_type": modal_by_type,
        "exceptions": exceptions,
    }


def format_report(rows: list[dict], corpus: set[int], meta: dict) -> str:
    out = []
    w = out.append

    w(f"client: {meta['exe']}")
    w(f"        ({meta['why']})")
    w(f"table: {meta['record_count']} rows, {len(rows)} live "
      f"(name_id != 0), build {meta['build']}")
    corpus_rows = [r for r in rows if r["id"] in corpus]
    noncorpus_rows = [r for r in rows if r["id"] not in corpus]
    w(f"of those, {len(corpus_rows)} are in the player corpus "
      f"(skilltable.player_corpus: equip_family 1, PvP-only excluded) and "
      f"{len(noncorpus_rows)} are not")
    w("")

    w("=" * 72)
    w("PREDICTION (stated before these numbers, see this file's docstring):")
    w("  spells/signets/well/ward/item/weapon-spells -> modal 0.75")
    w("  attacks/stances/conditions/shouts/pet attacks/traps -> modal 0.000")
    w("  watching specifically for: a Signet at 0 (Dolyak?), an Attack at")
    w("  0.75 (a Ranger interrupt?), Preparations' own modal either way")
    w("=" * 72)
    w("")

    w("HISTOGRAM -- distinct aftercast values, ALL live rows (MEASURED)")
    hist = Counter(r["aftercast"] for r in rows)
    for val, n in sorted(hist.items(), key=lambda kv: -kv[1]):
        bar = "#" * min(60, n // 10 or (1 if n else 0))
        w(f"  {val:>7.4f}s  {n:>5}  {bar}")
    w(f"  ({len(hist)} distinct values, {len(rows)} rows)")
    w("")

    w("HISTOGRAM -- distinct aftercast values, PLAYER CORPUS ONLY (MEASURED)")
    chist = Counter(r["aftercast"] for r in corpus_rows)
    for val, n in sorted(chist.items(), key=lambda kv: -kv[1]):
        bar = "#" * min(60, n // 10 or (1 if n else 0))
        w(f"  {val:>7.4f}s  {n:>5}  {bar}")
    w(f"  ({len(chist)} distinct values, {len(corpus_rows)} rows)")
    w("")

    result = sweep(rows)
    by_type = result["by_type"]
    modal_by_type = result["modal_by_type"]

    cresult = sweep(corpus_rows)
    cby_type = cresult["by_type"]
    cmodal_by_type = cresult["modal_by_type"]
    exceptions = cresult["exceptions"]  # corpus-only, see docstring

    w("PER-TYPE MODAL TABLE -- ALL live rows (MEASURED: type_code, word[OURS")
    w("label], row count, modal aftercast, rows matching, rows not matching)")
    w("-" * 72)
    for t in sorted(by_type):
        trows = by_type[t]
        modal = modal_by_type[t]
        n_match = sum(1 for r in trows if r["aftercast"] == modal)
        n_exc = len(trows) - n_match
        word = TYPE_WORDS.get(t, "?")
        w(f"  type {t:>2} {word:<24} n={len(trows):>4}  "
          f"modal={modal:>6.3f}s  match={n_match:>4}  exceptions={n_exc:>3}")
    w("")

    w("PER-TYPE MODAL TABLE -- PLAYER CORPUS ONLY (MEASURED). This is the")
    w("table the exception list below and NOTES.md's wiki-check list are")
    w("built from.")
    w("-" * 72)
    for t in sorted(cby_type):
        trows = cby_type[t]
        modal = cmodal_by_type[t]
        n_match = sum(1 for r in trows if r["aftercast"] == modal)
        n_exc = len(trows) - n_match
        word = TYPE_WORDS.get(t, "?")
        w(f"  type {t:>2} {word:<24} n={len(trows):>4}  "
          f"modal={modal:>6.3f}s  match={n_match:>4}  exceptions={n_exc:>3}")
    w("")

    w(f"EXCEPTION LIST -- {len(exceptions)} PLAYER-CORPUS rows whose")
    w("aftercast is NOT the modal value for their type_code (MEASURED, ids")
    w("only, no skill names)")
    w("-" * 100)
    w(f"  {'id':>5} {'type':>4} {'type_word':<24} {'prof':>4} "
      f"{'prof_word':<13} {'activation':>10} {'recharge':>8} "
      f"{'aftercast':>9} {'type_modal':>10}")
    for r in sorted(exceptions, key=lambda r: (r["type_code"], r["id"])):
        w(f"  {r['id']:>5} {r['type_code']:>4} "
          f"{TYPE_WORDS.get(r['type_code'], '?'):<24} "
          f"{r['profession']:>4} "
          f"{PROFESSION_NAMES.get(r['profession'], '?'):<13} "
          f"{r['activation']:>10.4f} {r['recharge']:>8} "
          f"{r['aftercast']:>9.4f} {r['type_modal']:>10.4f}")
    w("")

    w("CROSS-TAB -- player-corpus exception rows by (type_code, profession)")
    w("(MEASURED)")
    w("-" * 72)
    cross = Counter((r["type_code"], r["profession"]) for r in exceptions)
    for (t, p), n in sorted(cross.items()):
        w(f"  type {t:>2} {TYPE_WORDS.get(t, '?'):<24} "
          f"x profession {p:>2} {PROFESSION_NAMES.get(p, '?'):<13} -> {n}")
    if not cross:
        w("  (no exceptions)")
    w("")

    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", default=None,
                   help="client binary to read (read-only); defaults to the "
                        "pinned pristine build")
    p.add_argument("--out", help="also save the report text here")
    a = p.parse_args(argv)

    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    data = Path(a.exe).read_bytes()
    base, count, score = locate_table(data)
    rows = [parse_record(data, base, i) for i in range(count)]
    live = [r for r in rows if r["name_id"]]
    corpus = set(player_corpus(rows))

    from skilltable import build_of
    meta = {
        "exe": str(a.exe),
        "why": why,
        "record_count": count,
        "build": build_of(data),
    }

    report = format_report(live, corpus, meta)
    print(report)

    if a.out:
        Path(a.out).write_text(report, encoding="utf-8")
        print(f"\nwrote {a.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
