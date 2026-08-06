#!/usr/bin/env python3
"""Self-test for browse-gw-wiki. Prints [PASS]/[FAIL], exits non-zero on failure.

Follows the house convention: a red test names the broken thing.

The parser tests run against `fixtures/`, which holds real wikitext captured
from GWW via the browser on 2026-08-06. That keeps them meaningful without the
network -- GWW 403s scripted clients, so a test that needed the API would just
skip forever and prove nothing.

The network tests are attempted and reported as skipped when the edge blocks
us, which is the normal case from an agent host.
"""

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FIXTURES = HERE.parent / "fixtures"

from gwwiki import (  # noqa: E402
    WikiBlocked, get_wikitext, infobox_from_wikitext,
)

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


# -- parser, against real GWW wikitext -----------------------------------
# Expected values are what GWW displays; the raw column is what the client's
# 164-byte skill record holds at +0x38. A mismatch is a finding, not
# necessarily a test bug -- read the failure before editing the expectation.
CASES = [
    # fixture,          id,    displayed adrenaline, client raw, progression vars
    ("gww_Battle_Rage",  "317", "4", 80,  1),
    ("gww_Defy_Pain",    "318", "5", 120, 2),
]

for stem, want_id, want_adren, raw, want_vars in CASES:
    path = FIXTURES / f"{stem}.wikitext"
    if not path.exists():
        check(f"fixture {stem} present", False, f"missing {path}")
        continue
    box = infobox_from_wikitext(path.read_text(encoding="utf-8"))
    f = box["fields"]
    name = f.get("name", stem)

    check(f"{name}: skill id == {want_id}", f.get("id") == want_id, f"got {f.get('id')!r}")
    check(f"{name}: adrenaline == {want_adren}",
          f.get("adrenaline") == want_adren, f"got {f.get('adrenaline')!r}")
    # GWW spells it `concise description`; the parser normalises the space.
    check(f"{name}: concise_description normalised",
          "concise_description" in f)
    # Progression is a sibling {{Skill progression}} template on GWW, not
    # infobox fields -- if this is 0 the sibling lookup regressed.
    got_vars = len([k for k in box["progression"] if k.endswith("_at0")])
    check(f"{name}: {want_vars} progression var(s) found",
          got_vars == want_vars, f"got {got_vars}")
    # Nav templates must not be mistaken for the skill box.
    check(f"{name}: skill box not a {{{{skill icon}}}} decoy",
          f.get("name") not in ("Berserker Stance", "Rush"))
    # The rule under test.
    check(f"{name}: ceil({raw}/25) == displayed {want_adren}",
          str(math.ceil(raw / 25)) == want_adren)

# floor(raw/25)+1 must fail somewhere, or it was never actually excluded.
counter = [p for p in (25, 100, 125, 150, 200) if (p // 25) + 1 != math.ceil(p / 25)]
check("floor(raw/25)+1 is refutable", bool(counter), f"differs at {counter}")

# -- network, best effort -------------------------------------------------
try:
    wt = get_wikitext("Adrenaline")
    check("live GWW fetch", len(wt) > 1000, f"{len(wt)} chars")
    check("live GWW states 25 units per hit", "25 units of adrenaline" in wt)
except WikiBlocked:
    print("[SKIP] live GWW fetch -- edge blocks scripted clients (expected). "
          "Use the browser MCP; see references/access.md.")

print()
if fails:
    print(f"{len(fails)} FAILED: {', '.join(fails)}")
    sys.exit(1)
print("all checks passed")
