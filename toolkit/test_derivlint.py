#!/usr/bin/env python3
"""Check the second gate's checker, by rebuilding the defect that earned it.

    python toolkit/test_derivlint.py

WHAT EARNS THIS FILE. `PLAN.md` section 6.1 opens with `gwdat.py` landing as a
port of an unlicensed repository the day after the plan forbade exactly that,
and ends the paragraph "The rule was in the plan; nothing was checking." On
2026-08-17 the same shape turned up again: Fournux/Tyria-Extractor, MIT,
supplying a rule `textrec.py`'s own docstring says was NOT re-derived by us, with
no section 6.1 row and no notice -- four days after two studies flagged it.
`derivlint.py` is the check. This is what makes the check refutable.

EVERY SABOTAGE RUNS AGAINST A SYNTHETIC REPO ROOT, not the real one. A test that
only asserts "the tree is clean today" passes just as well when the scanner has
stopped finding anything, which is the vacuity `toolkit/checks.py` exists to
refuse -- and it is the exact failure `test_provlint.py` guards with its "the
detector still finds the citations it is measuring" check. So section 2 plants a
module that names an upstream, removes the row, and requires the audit to SAY SO.

THE SHARPEST CHECK IS SECTION 3 and it is not hypothetical. `PLAN.md:33` is the
prior-art LANDSCAPE table -- a list of what exists, granting nothing -- and it
sits 1,030 lines above the derivation register. A recon lane read a Fournux
mention there as "Fournux has a register row" and recorded that as fact;
`studies/quests/AUTHORING.md` section 7 has it in its killed-answers table. A
`"Fournux" in open("PLAN.md").read()` check makes the identical mistake and
would have scored the tree clean on the day the row was missing. Section 3
builds precisely that file -- landscape row present, register row absent -- and
requires UNACCOUNTED.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import checks     # noqa: E402
import derivlint  # noqa: E402

# MEASURED: 20 on the first green run. The floor is 17, not 20, and the
# derivation is the point -- checks.py wants the MANDATORY CORE, not today's
# total. Sections 1-4 are 17 checks and are independent of how many rows
# NO_DERIVATION holds; section 5 adds one per row, and there are three. So a
# tree where every upstream had earned a real 6.1 row -- the direction this
# is supposed to move -- would legitimately run 17, and pinning 20 would turn
# that improvement into a red suite. Nothing here needs the vault, a client
# or a socket, so nothing can skip.
LEDGER = checks.Ledger("derivlint: the second gate's checker", floor=17)
check = checks.adopt(LEDGER)

_TMP = []

REGISTER_HEAD = "### 6.1 The derivation register\n\n| Module | Derived from |\n"
LANDSCAPE = ("| [Fournux/Tyria-Extractor](https://github.com/Fournux/Tyria-Extractor) "
             "| `Gw.dat` -> skills | **MIT**, Rust |\n")


def synth_root(module_text, register_rows="", notices="", plan_head=""):
    """A throwaway repo root: toolkit/probe.py, PLAN.md, THIRD-PARTY-NOTICES.md."""
    root = tempfile.mkdtemp(prefix="derivlint_")
    _TMP.append(root)
    os.makedirs(os.path.join(root, "toolkit"))
    with open(os.path.join(root, "toolkit", "probe.py"), "w", encoding="utf-8") as fh:
        fh.write(module_text)
    with open(os.path.join(root, "PLAN.md"), "w", encoding="utf-8") as fh:
        # plan_head stands in for everything ABOVE the register, which is where
        # the landscape table lives.
        fh.write(plan_head + REGISTER_HEAD + register_rows + "\n## 7. Open questions\n")
    with open(os.path.join(root, "THIRD-PARTY-NOTICES.md"), "w", encoding="utf-8") as fh:
        fh.write(notices)
    return root


def main():
    print("1. the real tree is accounted for, and the scan is not vacuous")
    unaccounted, stale, orphan, missing = derivlint.audit()
    check(not unaccounted,
          "every upstream named in toolkit/ has a row, a notice or a NO_DERIVATION entry",
          f"UNACCOUNTED: {unaccounted} -- an upstream reached the tree and nobody "
          f"decided anything about it, which is the Fournux defect verbatim")
    check(not stale, "and no NO_DERIVATION row names an upstream that HAS a 6.1 row",
          f"stale {stale} -- inert today, and the day the row is removed it "
          f"silently re-permits the omission")
    check(not orphan, "and none names an upstream nothing in toolkit/ mentions",
          f"orphan {orphan} -- answers a question nobody asked and inflates the "
          f"list until nobody reads it")
    check(not missing,
          "and every attribution-required upstream with a 6.1 row carries its notice",
          f"MISSING NOTICE: {missing} -- this half is a licence obligation, not "
          f"a tidiness one")

    hits = derivlint.named_in_code()
    check(len(hits) >= 10,
          "the scan finds upstreams at all",
          f"{len(hits)} -- a drop toward zero means the patterns rotted, not "
          f"that the tree got cleaner; same failure test_provlint.py guards")
    four = hits.get("Fournux/Tyria-Extractor", [])
    check("toolkit/clientscan/textrec.py" in four
          and "toolkit/clientscan/skilltable.py" in four,
          "and finds Fournux in BOTH modules that derive from it",
          f"{four} -- these two are the reason the row exists; if the scan stops "
          f"seeing them the green above means nothing")

    print("\n2. the defect, rebuilt: an upstream named with nothing recorded")
    body = '"""Layout per Fournux/Tyria-Extractor doc/SKILL_EXTRACTION.md."""\n'
    r = synth_root(body)
    un, _s, _o, _m = derivlint.audit(r, no_derivation={})
    check(un == ["Fournux/Tyria-Extractor"],
          "a module naming an upstream with no row and no notice is UNACCOUNTED",
          f"{un} -- this is the 2026-08-17 state of the real tree, reproduced")

    r = synth_root(body, register_rows="| `toolkit/clientscan/textrec.py` | "
                                       "Fournux/Tyria-Extractor | MIT | ok |\n")
    un, _s, _o, missing = derivlint.audit(r, no_derivation={})
    check(un == [], "adding the 6.1 row clears UNACCOUNTED", f"{un}")
    check(missing == ["Fournux/Tyria-Extractor"],
          "but MIT still owes a notice, and the audit says so separately",
          f"{missing} -- the two obligations are scored apart because the row "
          f"is ours and the notice is the licence's")

    r = synth_root(body,
                   register_rows="| `x` | Fournux/Tyria-Extractor | MIT | ok |\n",
                   notices="## Tyria-Extractor - Fournux\nMIT text here\n")
    real_nd = derivlint.audit(r)[2]
    check(sorted(real_nd) == sorted(derivlint.NO_DERIVATION),
          "and the REAL allowlist is all orphans against a synthetic root",
          f"{real_nd} -- which is why audit() takes no_derivation. Reading the "
          f"module constant here would tie every synthetic check to the real "
          f"tree and make the orphan check meaningless")
    check(derivlint.audit(r, no_derivation={}) == ([], [], [], []),
          "row plus notice is fully clean",
          "the positive control -- without it the checks above could be passing "
          "for the wrong reason")

    print("\n3. PLAN.md:33 is the LANDSCAPE table and must not be read as a row")
    r = synth_root(body, plan_head="## 1. What changed\n" + LANDSCAPE)
    un, _s, _o, _m = derivlint.audit(r, no_derivation={})
    check(un == ["Fournux/Tyria-Extractor"],
          "a landscape mention ABOVE the register does not account for anything",
          f"{un} -- a recon lane made this exact mistake and recorded it as fact "
          f"(studies/quests/AUTHORING.md section 7 killed it). A whole-file "
          f"substring check scores the tree clean here, which is worse than no "
          f"check because it is confidently wrong")
    txt = derivlint.register_text(r)
    check("Fournux" not in txt and "6.1 The derivation register" in txt,
          "and register_text() returns the section, not the file",
          f"{len(txt)} chars, landscape row excluded")
    check("## 7. Open questions" not in txt,
          "and stops at the next top-level heading rather than running to EOF",
          "a register that swallowed the rest of PLAN.md would match almost any "
          "upstream name and never report anything again")

    print("\n4. the skip list is load-bearing, not cosmetic")
    check("toolkit/mirror_priorart.py" in derivlint.SKIP,
          "the fetch manifest is skipped")
    wide = derivlint.named_in_code(skip=set())
    check(len(wide) > len(hits),
          "and leaving it in scope inflates the census",
          f"{len(wide)} upstreams with it, {len(hits)} without -- it names every "
          f"mirror by construction, so including it turns this check into a "
          f"census of that one list rather than of what the code uses")
    check("toolkit/derivlint.py" in derivlint.SKIP
          and "toolkit/test_derivlint.py" in derivlint.SKIP,
          "and the checker and its test cannot trigger themselves",
          "both enumerate upstreams in NO_DERIVATION; unskipped, every row here "
          "would count as a module naming that upstream")

    print("\n5. the NO_DERIVATION rows say WHY, and name where")
    for slug, why in sorted(derivlint.NO_DERIVATION.items()):
        check(len(why) > 120 and (".py:" in why or "areatable" in why),
              f"{slug}'s row cites a site rather than asserting a verdict",
              f"{why[:80]}... -- a bare 'nothing taken' is the silent skip this "
              f"list exists to replace")

    for p in _TMP:
        shutil.rmtree(p, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
