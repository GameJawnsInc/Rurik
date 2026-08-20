"""Prove the identifier census counts definitions, ignores mentions, and can go red.

WHAT THIS GUARDS, and it is narrower than it looks. `studies/idents/HANDOFF.md`
decision 5 offered three shapes for enforcement: a hard gate refusing a new token with
no arc prefix, a tripwire that only reports GROWTH in the collision count, or nothing at
all. The middle one was recommended and the middle one is what this is, for the reason
the handoff gives in its own top box: eighty documents predate any convention, a hard
gate over them "will produce a red suite for reasons nobody wants to fix at 2am", and
the last time this repo read a rule literally across sixteen documents it rewrote 46
citations and reverted all 46 the same day.

So the posture is `toolkit/provlint.py`'s exactly: `identlint.py` counts and never
judges, the ceiling lives here, and the ceiling carries real headroom because ordinary
research mints identifiers and a tripwire that fires on ordinary work is one somebody
switches off. A collision is NOT a defect to be scrubbed. 53 of them are the tree's
current, ruled-on state. What is a defect is the 54th arriving unnoticed.

FIVE THINGS ARE TESTED AND THE LAST TWO ARE THE REAL ONES.

  1. Both defining shapes are recognised, including the annotated and struck forms
     `HANDOFF.md`'s own repair pattern produces (section 1).
  2. IT DOES NOT COUNT MENTIONS. Every study document is built out of references to
     other arcs' tokens, and a census that counts `see C8 above` as a definition
     reports a collision count made mostly of prose (section 2). `studies/idents/`
     itself is the sharpest case: its census tables CITE the tokens they describe, so
     the checker must be able to read the document that specifies it.
  3. The corpus is really read and the detector still fires (section 3). This is the
     `test_codec.py` failure -- ALL CHECKS PASSED over a fixture glob matching
     nothing -- and under a not-growing rule a dead detector reads as PROGRESS.
  4. The tree against the recorded baseline, with the growth arm proved on purpose:
     a synthetic rival definer is added to the REAL scan and the count must move
     (section 4). A tripwire nobody has seen trip is a wish.
  5. The resolver answers the sentence the arc opened with (section 5), asserted by
     document path and row CONTENT -- never against a pinned line number, because
     lines drift and an assertion that drifts gets deleted rather than fixed.

standard library only.

    python toolkit/test_identlint.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import identlint  # noqa: E402
import whichrung  # noqa: E402

# 26 is the MANDATORY CORE, from a real green run on 2026-08-20 (which executes 28:
# the core plus section 4's two growth arms, which declare skips in the unreachable
# case where no single-document control token exists -- per checks.py's own guidance,
# the floor covers the core and the optional pair declares its shortfall). Nothing
# here is fixture-dependent, so fewer than 26 means a section stopped running.
LEDGER = checks.Ledger("identlint", floor=26)

ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------------------
# THE BASELINE. Observed 2026-08-20, immediately after the token pattern widened to
# admit convention-form and ladder tokens (parent `42062ce`; the widening added
# exactly two sites, PLAN.md's R-IDENTS and R-ISLE rows), by `python toolkit/identlint.py`:
#
#     312 defining site(s) in 31 document(s); 152 distinct token(s);
#     53 of them collide across documents.
#
# The collision number is the one this file is armed on, because it is the defect
# `studies/idents/HANDOFF.md` 2.2(a) names -- one bare token, several definers, no way
# for a reader to tell which is meant. 53 is high and that is not news; the handoff was
# opened because it is high.
#
# THE CEILING IS 80, NOT 54. `test_provlint.py`'s comment on this exact question is the
# precedent and it was written after the mistake: a tripwire re-armed three short of its
# limit "fires on the next session's ordinary work", and the direction of error this
# repo records is over-refusal. 80 is 53 at the same ~1.5x headroom `provlint` used for
# 134 -> 200 and again for 280 -> 420, rather than a new rule. An arc that mints a
# colliding letter series -- which is what arcs currently do, since the convention is
# not written yet -- costs about nine collisions, so this buys roughly three arcs before
# somebody has to look. When it fires, RAISING IT IS A NORMAL EDIT, exactly as it is in
# `test_provlint.py`; what is not normal is a mass rename, which the handoff's top box
# refuses in advance.
COLLISION_CEILING = 80

# The other direction. A pattern that rots reports a clean tree, and under a
# not-growing rule that reads as progress -- so the floor is set BELOW the observed 312
# rather than at it, the same way `test_provlint.py` sets its corpus floor.
SITE_FLOOR = 250
DOC_FLOOR = 25


def tripped(n_collisions):
    """The judgement, factored out so section 4 can prove BOTH of its arms."""
    return n_collisions > COLLISION_CEILING


def sites(text, path="<test>"):
    return identlint.scan_text(text, path)


def main():
    # ---- 1. the two defining shapes --------------------------------------------
    print("1. a document introducing a token is recognised")
    LEDGER.ok(len(sites("| **C8** | Derive `point_invalid` | done |\n")) == 1,
              "a bolded table row defines its token",
              "studies/movement/PROBE-GATEFIRE.md's shape")
    LEDGER.ok(len(sites("### C8 -- Two more opcodes witnessed.\n")) == 1,
              "and so does a heading that opens with it",
              "studies/cmsg/FINDINGS.md's shape -- the SAME token, elsewhere")
    LEDGER.ok(len(sites("| R4c | AI + spawns + quests | an area populates |\n")) == 1,
              "an unadorned row is not missed for lack of bold")
    # `HANDOFF.md`'s repair pattern is to strike or annotate a superseded row IN PLACE
    # rather than delete it (2.3). A struck row still defines its token, and a census
    # that dropped it would under-report the tree the day somebody used the pattern.
    struck = sites("| ~~**R0**~~ | superseded by R0a/R0b | annotated 2026-08-20 |\n"
                   "| **R5m** | Modding surface | see PLAN 3 |\n")
    LEDGER.ok([s.token for s in struck] == ["R0", "R5m"],
              "a struck-through and an annotated row both still define",
              f"{[s.token for s in struck]}")
    # The convention's OWN shapes. Without these three arms the resolver was blind to
    # every token CONVENTION.md sec 1 mints -- including R-IDENTS, the rung this arc
    # landed under -- which made its two halves mutually exclusive: a well-formed new
    # token could not be resolved in one command. Caught in pre-merge review.
    LEDGER.ok([s.token for s in sites("| **GATEFIRE-C3** | a prefixed step | open |\n")]
              == ["GATEFIRE-C3"],
              "a convention-form token in a table row defines",
              "CONVENTION.md sec 1's own first example")
    LEDGER.ok([s.token for s in sites("### ITEMMODS-M1 -- the first milestone\n")]
              == ["ITEMMODS-M1"],
              "and in a heading",
              "the word is 4+ chars, the tail carries the digit")
    LEDGER.ok([s.token for s in sites("| **R-ISLE** | the isle as a range | rungs |\n")]
              == ["R-ISLE"],
              "and a hyphen-word LADDER rung defines too",
              "PLAN.md sec 3's own namespace -- R-ISLE, R-IDENTS")

    # ---- 2. AND IT DOES NOT COUNT MENTIONS -------------------------------------
    print("\n2. a document REFERRING to a token is not counted as defining it")
    # Every one of these appears in the tree constantly. Counting any of them turns
    # the collision number into a measure of how much the arcs cite each other, which
    # is not the defect and would make the tripwire meaningless.
    mentions = {
        "backticked census cell": "| `C-1`-`C-13` | archivewrite | a corrections ledger |\n",
        "prose sentence": "C-8 finished, looking into C-9 next.\n",
        "mid-heading reference": "## Answers to PLAN sec 7, Q1-Q5\n",
        "second cell of a row": "| the ladder | R4c is where spawns land | open |\n",
        "bullet reference": "- see `C8` above, and R4b for the skill substrate\n",
        "a link to a rung": "[PLAN.md:348](../../PLAN.md:348) carries R0a and R0b\n",
        "a backticked heading": "### `C8` -- cited in a heading, not defined\n",
        "an indented row": "  | C8 | a defining-shaped row, but indented |\n",
        "a word-word filename title": "# PROBE-GATEFIRE\n",
    }
    noisy = {k: [s.token for s in got]
             for k, v in mentions.items() if (got := sites(v))}
    LEDGER.ok(not noisy,
              f"none of {len(mentions)} reference forms is counted",
              "a census of mentions measures cross-citation, not ambiguity"
              + (f" -- COUNTED: {noisy}" if noisy else ""))

    # The document that SPECIFIES this tool is the hardest case in the tree: its
    # census tables are made of nothing but citations of other arcs' tokens. If the
    # checker cannot read that, it cannot be trusted with anything.
    tree_sites = identlint.scan_tree(ROOT)
    idents_own = [s for s in tree_sites if s.path.startswith("studies/idents/")]
    LEDGER.ok(not idents_own,
              "and studies/idents/ defines nothing, so it cannot pollute its own census",
              f"COUNTED: {idents_own}" if idents_own else
              "its 2.1 and 2.2 tables cite tokens in backticked cells")

    # ---- 3. hyphens, and the vacuity guards ------------------------------------
    print("\n3. the collision key, and the checker cannot be quietly disarmed")
    # 2.2: the hyphen "is a *weak* signal ... but it is not a rule and must not be
    # taught as one". So `C-8` and `C8` share a key, which is what makes them collide.
    LEDGER.ok(identlint.normalize("C-8") == identlint.normalize("C8") == "C8",
              "`C-8` and `C8` share one collision key, per 2.2's ruling on the hyphen")
    LEDGER.ok(identlint.normalize("R4c") != identlint.normalize("R4"),
              "while a trailing letter is part of the token, not decoration",
              "R0a/R0b/R4a/R4b/R4c are distinct rungs in PLAN.md 3")

    docs = {s.path for s in tree_sites}
    LEDGER.ok(len(tree_sites) >= SITE_FLOOR,
              f"the corpus is really read, not sampled ({SITE_FLOOR}+ sites)",
              f"{len(tree_sites)} sites")
    LEDGER.ok(len(docs) >= DOC_FLOOR,
              f"across {DOC_FLOOR}+ documents",
              f"{len(docs)} documents")
    # The other failure is reading the tree several times over: `.claude/` holds this
    # repo's worktrees, each a full checkout of the same documents, and `provlint.py`
    # records what that did to its number -- green inside a worktree, red on `main`
    # at the same commit. This module cannot repeat that STRUCTURALLY: the walk
    # enters only `studies/` plus three named root files, so a nested checkout is
    # unreachable rather than skipped (`SKIP_DIRS` prunes nothing today; it is
    # future-proofing). A check on the skip list would therefore be one that cannot
    # fail -- so the check is on the corpus scope itself, and it goes red the day
    # the walk reaches a document that DEFINES a token outside the scope (a nested
    # checkout's studies/, vault/, a venv). Widening to the four remaining root-level
    # .md files alone would not fire it: none of them defines a token today.
    stray = sorted(p for p in docs
                   if p not in identlint.ROOT_DOCS
                   and not p.startswith(identlint.STUDY_DIR + "/"))
    LEDGER.ok(not stray,
              "and every counted document is a root doc or under studies/",
              f"STRAY: {stray[:4]} ({len(stray)} total)" if stray
              else "a nested worktree, vault or venv is structurally unreachable")

    # ---- 4. THE TRIPWIRE, AND BOTH OF ITS ARMS ---------------------------------
    print("\n4. the collision count against the recorded baseline")
    coll = identlint.collisions(tree_sites)
    LEDGER.ok(not tripped(len(coll)),
              f"cross-document collisions are under the ceiling of {COLLISION_CEILING}",
              f"{len(coll)} colliding token(s) -- baseline 53 on 2026-08-20. "
              "If this went red: read the new colliding tokens in "
              "`python toolkit/identlint.py`, and RAISE the ceiling if they are "
              "ordinary work. A rename of existing tokens is refused by "
              "studies/idents/HANDOFF.md's top box.")
    LEDGER.ok(tripped(COLLISION_CEILING + 1),
              "and the same comparison goes RED one collision above it",
              "a tripwire nobody has seen trip is a wish, not a check")

    # Growth proved against the REAL scan rather than a fixture, because the thing
    # that must move is the number this file is armed on. The control token is chosen
    # at RUN TIME -- the first defined in exactly one document -- because a
    # hard-coded one turns into a mid-run abort the day some arc legitimately mints
    # its rival, and that event is the growth this file exists to notice, not a
    # stale fixture. Candidates are limited to the plain LETTERS+DIGITS shape so the
    # synthetic definer below round-trips through the scanner unmangled.
    solo = home = None
    index = identlint.by_token(tree_sites)
    for tok in sorted(index):
        hits = index[tok]
        tok_docs = {s.path for s in hits}
        if len(tok_docs) == 1 and re.fullmatch(r"[A-Z]{1,2}\d{1,3}", hits[0].token):
            solo, home = hits[0].token, next(iter(tok_docs))
            break
    LEDGER.ok(solo is not None,
              "a single-document control token exists, chosen at run time",
              f"{solo} -- defined only in {home}" if solo
              else "every token collides; the growth arm cannot be staged")
    if solo is None:
        LEDGER.skip("one new rival definer moves the count by exactly one",
                    "no single-document token to stage the growth with")
        LEDGER.skip("while a second definer in the SAME document does not",
                    "same shortfall")
    else:
        grown = tree_sites + sites(f"### {solo} -- a rival definer in a new arc\n",
                                   "studies/fictional/FINDINGS.md")
        grown_coll = identlint.collisions(grown)
        LEDGER.ok(len(grown_coll) == len(coll) + 1 and solo in grown_coll,
                  "one new rival definer moves the count by exactly one",
                  f"{len(coll)} -> {len(grown_coll)}, and {solo} now names "
                  f"{len(grown_coll.get(solo, []))} documents")
        # ...and the same event must NOT move it when the second site is in the SAME
        # document. An arc numbering its own table C1..C9 is one namespace working,
        # and counting its rows as collisions would bury the cross-document signal.
        same_doc = tree_sites + sites(
            f"### {solo} -- restated later in its own document\n", home)
        LEDGER.ok(len(identlint.collisions(same_doc)) == len(coll),
                  "while a second definer in the SAME document does not",
                  "2.2(a) is about a token that names different things in different "
                  "documents; one arc numbering its own table is not that")

    LEDGER.ok(len(coll) > 0,
              "and the detector still finds the collisions it is measuring",
              f"{len(coll)} -- a drop to 0 with no convention landed and no rename "
              "commit means the pattern rotted, not that the tree got tidier")

    # ---- 5. THE RESOLVER, which is the deliverable ------------------------------
    print("\n5. whichrung answers the sentence the arc opened with")
    # 4: "For C8 it returns two hits ... which demonstrates the problem and solves it
    # in the same line." Asserted by document and by row CONTENT. NOT by line number:
    # every one of these documents is edited weekly, and a pinned line is an assertion
    # that goes red for a reason nobody wants to fix and gets deleted instead.
    found = whichrung.resolve(ROOT, "C8")
    got = {s.path: s for s in found}
    cmsg = "studies/cmsg/FINDINGS.md"
    gate = "studies/movement/PROBE-GATEFIRE.md"
    LEDGER.ok(cmsg in got and gate in got,
              "C8 resolves to both of the documents that define it",
              f"{sorted(got)}")
    LEDGER.ok(cmsg in got and "opcodes witnessed" in got[cmsg].text,
              "the cmsg site is its own heading, by content",
              got[cmsg].text[:90] if cmsg in got else "MISSING")
    LEDGER.ok(gate in got and "point_invalid" in got[gate].text,
              "and the gate-fire site is its own table row, by content",
              got[gate].text[:90] if gate in got else "MISSING")
    # THREE, not the handoff's two. 4's one-liner is literal, so it separated
    # `C-8` from `C8` and never saw studies/archivewrite/FINDINGS.md's corrections
    # row -- which is the arc's own worked example, since 1's ambiguous sentence
    # ("C-8 finished") is the hyphenated spelling and "finished" is not something you
    # do to a correction. The resolver finding the third site is the fix, not a bug.
    aw = "studies/archivewrite/FINDINGS.md"
    LEDGER.ok(aw in got and "row censuses disagree" in got[aw].text,
              "and the archivewrite corrections row is the THIRD site, by content",
              got[aw].text[:90] if aw in got else "MISSING")
    LEDGER.ok(len(got) == 3,
              f"so the bare token is AMBIGUOUS across {len(got)} documents",
              "which is 1's whole complaint, measured rather than asserted -- and "
              "one more document than 4's literal one-liner could see, because that "
              "pattern treats the hyphen as a namespace and 2.2 says it is not. "
              "A FOURTH DOCUMENT defining C8 appearing is a real event, not a broken "
              "test: update this count and the three content checks above. (A fourth "
              "definer already exists OUTSIDE the pattern -- combat/PLAN.md's bold "
              "list-lead C8 -- which is what makes the tool's answer a floor.)")
    # The hyphen again, this time end to end: 1's ambiguous sentence writes `C-8`,
    # and a resolver that answered only the unhyphenated spelling would fail on the
    # exact input it was built for.
    LEDGER.ok([(s.path, s.line) for s in whichrung.resolve(ROOT, "C-8")]
              == [(s.path, s.line) for s in found],
              "and `C-8` -- the spelling in the sentence that opened the arc -- "
              "resolves identically")
    LEDGER.ok(whichrung.resolve(ROOT, "ZZ99") == [],
              "a token nothing defines resolves to nothing",
              "whichrung.py reports NOT FOUND and exits 1; the docstring says why "
              "that is not proof of absence")
    # The arc's own acceptance criterion, clause one, applied to its own token: the
    # rung this convention landed under must resolve in one command. Before the
    # pattern widened it did not -- the resolver was blind to the very shape the
    # convention mints, and the pre-merge review caught it.
    rid = whichrung.resolve(ROOT, "R-IDENTS")
    LEDGER.ok(any(s.path == "PLAN.md" and "identifier convention" in s.text
                  for s in rid),
              "and R-IDENTS -- this arc's own rung -- resolves to PLAN.md sec 3",
              f"{[(s.path, s.token) for s in rid]}")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
