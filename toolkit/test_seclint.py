"""Prove `seclint.py` catches an append collision and stays quiet on the house style.

WHAT THIS IS GUARDING, stated as the failure it exists to prevent. Two sessions append
to one study document, both take "the next section number", and every later `§N`
citation is ambiguous. It happened twice in `studies/skills/FINDINGS.md` -- §26 first
(resolved as §26.12/§26.13) and §32 on 2026-08-21 (`## 32.` for the silent-extend probe
AND for E10, with `PLAN.md` §8's adrenaline entry citing "§32" and meaning E10). Neither
was caught by anything; the second was found by a human reading PLAN.md.

THE TWO CONTROLS ARE THE POINT OF THIS FILE.

  * The POSITIVE control (section 3) rebuilds the real 2026-08-21 defect out of TODAY'S
    `studies/skills/FINDINGS.md` -- it renames the §36 heading back to `## 32.` in
    memory and asserts the checker reddens. A frozen fixture would drift away from the
    document; this cannot. `CLAUDE.md`: a checker that finds nothing is
    indistinguishable from a clean tree.
  * The NEGATIVE controls (section 2) are the ones that decide whether anybody can
    leave this switched on. The naive "no number twice in a file" rule reports 74
    duplicates in this tree and nearly all are correct house style -- dated passes that
    restart at §1 under their own `#` divider, and `### N.` lists under different `##`
    parents. Those must stay green or the checker gets deleted, which is the lesson
    `provlint.py` records from having been too strict first.

WHY THE KNOWN LIST IS NOT A FIX LIST. Six same-scope collisions exist in the tree today
and this file names every one with a reason. They are NOT being renumbered:
`studies/idents/HANDOFF.md`'s star box rules that a mass rename of existing tokens is
out of scope, because section numbers are load-bearing in commit messages (`Skills
32.8`, `Isle 8.6`, `§27.4` are all commit subjects) and in the owner's own index of what
happened. This is a tripwire against ACCUMULATION: a seventh goes red, and so does a
third heading appearing under a token already known to have two.

Run: python toolkit/test_seclint.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import checks  # noqa: E402
import seclint  # noqa: E402

LEDGER = checks.Ledger("seclint", floor=26)


def _say(text):
    """print(), but a cp1252 console that cannot encode a glyph never kills the run.

    Same five lines as `checks._say` and `provlint._say`, and local for the same
    reason they are: the summary below prints section tokens and heading text read
    out of the tree, and `test_textrec.py` died on exactly that in 2026-08-06.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Every same-scope collision in the tree on 2026-08-22, with the reason it is recorded
# rather than renumbered. Key is (path, token, level); value is (count, why).
#
# A collision NOT in this list fails the run and names itself. An entry here that the
# scanner no longer finds ALSO fails -- a stale line reads as coverage while covering
# nothing, which is the defect `test_srclint.py` §7 checks in both directions too.
KNOWN = {
    ("PLAN.md", "8.0", 3): (
        2, "two `### 8.0 Next, as of 2026-08-11` headings, L5334 annotated as a FROZEN "
           "snapshot and L5492 not. PLAN.md is the status authority and its §3/§8 are "
           "cited from everywhere; renumbering is the owner's call, not a lint's."),
    ("studies/heroes/FINDINGS.md", "23", 2): (
        2, "append collision: `A FULL AUTHORED PARTY` and `The scan trigger, named` "
           "both took 23. The heroes arc is closed (PLAN.md §3), so nothing new cites "
           "either."),
    ("studies/heroes/FINDINGS.md", "35.2", 3): (
        2, "NOT an append collision and must not be 'fixed': L2499 is a deliberate "
           "SUPERSEDED-BY banner placed six lines above the original L2505 heading it "
           "supersedes, keeping the n=2 text visible rather than deleting it."),
    ("studies/minimap/FINDINGS.md", "6f", 2): (
        2, "append collision across two live-client sessions, `C2 and C3` then `C4`."),
    ("studies/models/FINDINGS.md", "7", 2): (
        2, "append collision: `What is still unknown` and `Provenance`."),
    ("studies/profession/RESKIN.md", "7", 2): (
        2, "append collision: `Open` and `The animation layer reads profession`."),
}


def scan(text):
    """Collisions in one document, as a set of (token, level, occurrence count)."""
    return {(c.token, c.level, len(c.occurrences)) for c in seclint.scan_text(text)}


def judge(found, known):
    """Compare a scan against a known list. Returns (new, grew, stale), all sorted.

    Pulled out of the assertions below so section 5 can run it against a DOCTORED
    known list and prove each verdict is reachable. A comparison that has only ever
    been run against a passing input is not known to be able to fail.
    """
    by_key = {c.key: c for c in found}
    new = sorted(k for k in by_key if k not in known)
    grew = sorted(k for k in by_key
                  if k in known and len(by_key[k].occurrences) > known[k][0])
    stale = sorted(k for k in known if k not in by_key)
    return new, grew, stale


def main():
    # ---- 1. the checker runs at all --------------------------------------------
    print("1. the checker parses and reports")
    LEDGER.ok(scan("# Title\n\nprose only, no headings that carry a number\n") == set(),
              "a document with no numbered headings reports nothing")
    LEDGER.ok(scan("# T\n\n## 1. One\n\n## 2. Two\n\n## 3. Three\n") == set(),
              "and an ordinary ascending run reports nothing")

    # ---- 2. THE HOUSE STYLE, which must stay green ------------------------------
    # These are not edge cases. The naive rule reports 74 duplicates in this tree and
    # these four shapes are ~all of them. If any of these goes red the checker is
    # unusable and should be deleted rather than worked around.
    print("\n2. the house style is NOT a collision")

    two_passes = ("# Desk pass\n\n## 1. Where data lives\n\n## 2. The protocol\n"
                  "\n# OBSERVED, 2026-08-05\n\n## 1. It was right\n\n## 2. The icon\n")
    LEDGER.ok(scan(two_passes) == set(),
              "a dated pass that RESTARTS the count under its own `#` divider",
              "studies/skills §1-§8 twice, studies/isle, studies/review, "
              "studies/character -- the standing ruling on these is a resolver")

    nested = ("# T\n\n## A. First topic\n\n### 1. Wrong\n\n### 2. Also wrong\n"
              "\n## B. Second topic\n\n### 1. The answer\n\n### 2. The framing\n")
    LEDGER.ok(scan(nested) == set(),
              "a `### N.` list nested under a DIFFERENT `##` parent",
              "studies/movement/FINDINGS.md has seven `### 1.` headings, all correct")

    levels = "# T\n\n## 7. Section seven\n\n### 7.1 A child\n\n#### 7.1.1 A grandchild\n"
    LEDGER.ok(scan(levels) == set(),
              "a parent and its children, whose tokens differ by depth")

    fenced = ("# T\n\n## 5. Real\n\n```bash\n# 5. not a heading\n## 5. also not\n```\n"
              "\nprose\n")
    LEDGER.ok(scan(fenced) == set(),
              "and `#` lines inside a fenced code block are not headings",
              "studies/ is full of shell blocks whose comments start with #")

    # ---- 3. POSITIVE CONTROL: the real 2026-08-21 defect, rebuilt from today's file
    print("\n3. THE CONTROL -- the defect this was written for, from the live document")
    live_path = os.path.join(ROOT, "studies", "skills", "FINDINGS.md")
    live = open(live_path, encoding="utf-8").read()

    silent = "## 36. The client runs its OWN expiry timer"
    e10 = "## 32. E10 — the recharge gate, read from the residue"
    LEDGER.ok(silent in live and e10 in live,
              "the two headings that collided are both still in the document",
              "if this fails the file was renumbered again and the control below is "
              "measuring nothing -- re-derive it, do not delete it")

    LEDGER.ok(scan(live) == set(),
              "and as it stands TODAY, studies/skills/FINDINGS.md is clean")

    # Put §36 back to the §32 it was committed as, and nothing else.
    broken = live.replace(silent, "## 32. The client runs its OWN expiry timer", 1)
    hits = scan(broken)
    LEDGER.ok(("32", 2, 2) in hits,
              "restore its old number and the collision is CAUGHT",
              "this is `## 32.` twice at 78baede -- the silent-extend probe and E10")
    LEDGER.ok(len(hits) == 1,
              "and that is the ONLY thing it reports about the file",
              "the §1-§8 pair in the same document stays green, which is the whole "
              "reason the rule is scoped")

    detail = [c for c in seclint.scan_text(broken, "x.md") if c.token == "32"][0]
    LEDGER.ok(len(detail.occurrences) == 2 and detail.level == 2,
              "reported at the right level, with both line numbers",
              f"L{detail.occurrences[0][0]} and L{detail.occurrences[1][0]}")

    # ---- 4. and the shapes an append collision actually takes -------------------
    print("\n4. the collision shapes, each planted deliberately")
    siblings = "# T\n\n## 30. E8\n\n## 31. E9\n\n## 32. A probe\n\n## 32. E10\n"
    LEDGER.ok(("32", 2, 2) in scan(siblings),
              "two `##` siblings under the same `#`")

    kids = "# T\n\n## 9. Parent\n\n### 9.1 One\n\n### 9.2 Two\n\n### 9.1 One again\n"
    LEDGER.ok(("9.1", 3, 2) in scan(kids),
              "two `###` children under the same `##` parent")

    third = "# T\n\n## 4. A\n\n## 4. B\n\n## 4. C\n"
    LEDGER.ok(("4", 2, 3) in scan(third),
              "and a THIRD claimant is counted, not merged",
              "so a known pair growing to a trio still goes red below")

    lettered = "# T\n\n## 6f. The lever\n\n## 6f. C4\n"
    LEDGER.ok(("6f", 2, 2) in scan(lettered),
              "tokens with a letter suffix collide too",
              "studies/minimap/FINDINGS.md §6f -- `6f` is what a prose §6f would say")

    # ---- 5. the tree, in both directions ----------------------------------------
    print("\n5. the tree as it stands, against the known list")
    found, files, headings = seclint.scan_tree(ROOT)

    # A scan that read nothing would pass every assertion below it. Refuse that first.
    LEDGER.ok(files >= 80,
              "the whole tree is scanned, not a sample",
              f"{files} markdown files, {headings} numbered headings")
    LEDGER.ok(headings >= 1800,
              "and it found the numbered headings it is supposed to be judging",
              "a glob matching nothing is how test_codec.py went green on zero frames")

    by_key = {c.key: c for c in found}
    new, grew, stale = judge(found, KNOWN)
    LEDGER.ok(not new,
              "no section number is claimed twice in the same scope, except as known",
              f"NEW: {new} -- two headings took the same number; give the second one "
              f"the next free number, or add it to KNOWN with a reason")
    LEDGER.ok(not grew,
              "and no known collision has gained a further claimant",
              f"GREW: {grew}")
    LEDGER.ok(not stale,
              "every entry in the known list is still real",
              f"STALE: {stale} -- fixed or moved; drop the line, or the list reads as "
              f"coverage while covering nothing")
    LEDGER.ok(len(found) == len(KNOWN),
              f"the tree carries exactly the {len(KNOWN)} recorded collisions",
              f"found {len(found)}")

    # CONTROLS. Each verdict above has only just been shown to be silent; show that
    # each one can also SPEAK, against the same real scan.
    dropped = {k: v for k, v in KNOWN.items() if k != ("PLAN.md", "8.0", 3)}
    LEDGER.ok(judge(found, dropped)[0] == [("PLAN.md", "8.0", 3)],
              "CONTROL: drop a known entry and NEW names exactly what it lost",
              "this is the verdict a genuinely new collision would trip")
    undercounted = dict(KNOWN)
    undercounted[("studies/models/FINDINGS.md", "7", 2)] = (1, "doctored")
    LEDGER.ok(judge(found, undercounted)[1] == [("studies/models/FINDINGS.md", "7", 2)],
              "CONTROL: understate a known count and GREW names it",
              "this is the verdict a known pair becoming a trio would trip")
    invented = dict(KNOWN)
    invented[("studies/nowhere/FINDINGS.md", "99", 2)] = (2, "doctored")
    LEDGER.ok(judge(found, invented)[2] == [("studies/nowhere/FINDINGS.md", "99", 2)],
              "CONTROL: invent a known entry and STALE names it",
              "this is the verdict a fixed-but-still-listed collision would trip")

    # ---- 6. and the checker cannot be quietly disarmed --------------------------
    print("\n6. what it refuses to do")
    LEDGER.ok(seclint.count_numbered("## 12. x\n```\n## 12. y\n```\n") == 1,
              "the denominator skips fenced blocks too",
              "otherwise a document could dilute its own rate with code samples")
    LEDGER.ok(scan("# T\n\n## Prose heading\n\n## Prose heading\n") == set(),
              "two identical PROSE headings are not this checker's business",
              "they cannot be addressed as §N, so they cannot make a §N ambiguous")

    print("\nrecorded collisions, and why each is not being renumbered:")
    for key in sorted(KNOWN):
        path, token, level = key
        count, why = KNOWN[key]
        lines = ", ".join(f"L{n}" for n, _ in by_key[key].occurrences) \
            if key in by_key else "MISSING"
        _say(f"  {path} §{token} x{count} ({lines})\n      {why}")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
