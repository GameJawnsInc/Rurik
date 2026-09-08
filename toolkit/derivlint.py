"""Is every upstream this repo's code NAMES accounted for at the repo level?

THE SECOND GATE HAS NEVER HAD A CHECKER. `CLAUDE.md` states it plainly -- add
the `PLAN.md` section 6.1 row BEFORE a module takes an algorithm, a layout or a
constant table from any upstream -- and section 6.1 itself opens with the day
that rule failed: `gwdat.py` landed declaring itself a port of an unlicensed
repository, the day after the plan wrote "never copy from them" about exactly
that repository, and sat in the running server's dependency chain until a review
found it. The closing line of that paragraph is "The rule was in the plan;
nothing was checking."

Something was checking one HALF. `toolkit/content.py` refuses a content row that
cites an unlicensed source without recording what we verified against. That is
the row-level gate. Nothing looked at MODULES, and on 2026-08-17
Fournux/Tyria-Extractor was found cited over a hundred times across sixteen
study documents and in five modules -- two of them real derivations, one a rule
the module's own docstring says was NOT re-derived -- with no section 6.1 row
and no `THIRD-PARTY-NOTICES.md` entry, four days after two separate studies
flagged it. Its licence is MIT, so the missing notice was an unmet obligation
rather than an untidy table.

WHAT THIS CHECKS, AND WHY IT IS PER-UPSTREAM RATHER THAN PER-MODULE. Measured
first: 21 upstreams are named across `toolkit/`, in 223 (module, upstream)
pairs. `gw-preservation/server` alone appears in 107 modules -- because it is
the UNLICENSED one, and the thing everyone writes down is that we may not copy
it. So "this module names that upstream" is not evidence of derivation, and a
per-pair rule would be permanently red and get deleted, which is the failure
`test_dispatch.py` section 7 documents at length about demanding an arm per
message layout. What IS decidable is the question the Fournux defect actually
posed: is this upstream accounted for ANYWHERE -- a section 6.1 row, a notices
entry, or a row here saying no derivation exists and why. Fourteen upstreams,
all decidable, no treadmill.

Citing, verifying against, and DISAGREEING with an upstream are not derivation.
Three of `NO_DERIVATION`'s rows are exactly that, and each names its site.

    python toolkit/derivlint.py            # the audit
    python toolkit/derivlint.py --pairs    # every (module, upstream) mention

An accumulation tripwire in `provlint.py`'s sense, not a gate: it cannot tell a
port from a paraphrase, and it never looks at what a module DOES. It catches the
one thing that is mechanical -- an upstream arriving in the tree with nobody
having decided anything about it.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(HERE)

import mirror_priorart  # noqa: E402

# Files that name upstreams BY CONSTRUCTION and are therefore not evidence of
# anything. `mirror_priorart.py` is the fetch manifest -- it lists every mirror
# there is, so leaving it in scope would mark all 21 upstreams "named in code"
# and turn this into a census of that one list. This module and its test
# enumerate upstreams in NO_DERIVATION for the same structural reason.
SKIP = {
    "toolkit/mirror_priorart.py",
    "toolkit/derivlint.py",
    "toolkit/test_derivlint.py",
}

# Extra spellings. The slug and the bare repo name are generated; these are the
# short forms the tree actually uses in prose.
EXTRA_ALIASES = {
    "Fournux/Tyria-Extractor": {"Tyria-Extractor", "Fournux"},
    "gwdevhub/GuildWarsMapBrowser": {"GWMB"},
    # The notice credits this project by its real name, which is not its repo
    # slug: `## GWCA -- GregLando113, JaborGW, and gwdevhub/GWToolbox++`. Without
    # this spelling the heading rule below cannot see its own notice.
    "gwdevhub/GWToolboxpp": {"GWToolbox++"},
}

# Slugs whose BARE repo name is an ordinary English word. The generated alias set
# is {slug, slug.split("/")[1]}, and for `gw-preservation/server` that second
# element is `server` -- which appears in 195 of this repository's modules,
# because this repository IS a server. That row said "named in 195 modules" and
# meant nothing at all: it was measuring the English language. Dropping the bare
# form leaves the slug itself, which is what a real citation writes.
NO_BARE_ALIAS = {
    "gw-preservation/server": "`server` matches 195 modules; this project is one",
}

# Upstreams named in real modules where NOTHING is derived. Each row is a
# decision on the record, and both directions are checked: a row for an upstream
# that HAS a section 6.1 row is stale, and a row for one nothing names is an
# orphan that inflates the list until nobody reads it. Same shape as
# `test_dispatch.py`'s DROPPED_ON_PURPOSE, for the same reason.
NO_DERIVATION = {
    "GameRevision/GWLP-R":
        "A SECOND WITNESS, never a source. agents.py:177 uses its 2013 mock NPC "
        "to argue two lineages thirteen years apart AGREE; analyze_movement.py:16 "
        "notes it names the same field `movementType`, beside our own truthiness "
        "test; authsrv.py:1746 cites it as the real support behind a table Py4GW "
        "ships with an off-by-one. Every one of those is our reading corroborated "
        "by theirs, which is the use PLAN.md section 1.1 explicitly permits. No "
        "layout, no constant table, no code.",
    "gw-preservation/server":
        "Named ONCE, at content.py:76, inside the SOURCES table that DEFINES the "
        "`gw-preservation` provenance label -- and the constant immediately below "
        "it, UNLICENSED, is what makes a content row citing that label REFUSE TO "
        "LOAD unless it records what we verified the value against. The slug is "
        "written there so the refusal can name the thing it refuses, which is the "
        "opposite of deriving from it. Note the register spells this source "
        "`gw-preservation` without the repo name (PLAN.md section 6.1, the "
        "content rows), so it cannot be matched off the register text; before "
        "2026-09-08 the row scored `6.1: yes` only because the generated bare "
        "alias `server` matched the word in 195 modules.",
    "apoguita/Py4GW_Reforged_Native":
        "Named ONCE, at areatable.py:35, inside an argument that it is NOT an "
        "independent witness: several projects do them identically and GWCA's own "
        "header credits `entice/gw-interface`, so they are one lineage rather than "
        "four. Citing a repo to DISCOUNT its agreement is the opposite of deriving "
        "from it.",
}

# Upstreams whose licence obliges us to reproduce a notice. If one of these has
# a section 6.1 row, `THIRD-PARTY-NOTICES.md` must carry it too -- that is the
# half of the Fournux defect that was a licence problem rather than a tidiness
# one.
ATTRIBUTION_REQUIRED = {
    "Fournux/Tyria-Extractor": "MIT",
    "ldufr/Headquarter": "MIT",
    "gwdevhub/GuildWarsMapBrowser": "custom, requires repo link + visible credit",
    "Jonathan-Greve/GuildWarsMapBrowser": "custom, requires repo link + visible credit",
    # ADDED 2026-09-08 (studies/prepub/FINDINGS.md sec 9 item 1). These three were
    # missing, and they are the ones whose tables ship INSIDE toolkit/ --
    # agents.py's WEAPON_TYPE_*/ALLEGIANCE_* pairs and genericvalue.py's 32-entry
    # GenericValueID table. So the checker reported the tree clean for weeks while
    # the one upstream it most needed to watch was outside its own list, which is
    # worse than no checker: it produced a green light. Three slugs rather than
    # one because there are three GWCA copies and they do not agree (the notice
    # says which is which); all three are MIT, attribution required.
    "GregLando113/GWCA": "MIT",
    "JaborGW/GWCA": "MIT",
    "gwdevhub/GWToolboxpp": "MIT",
}


def aliases():
    out = {}
    for slug, _why in mirror_priorart.REPOS:
        names = {slug}
        if slug not in NO_BARE_ALIAS:
            names.add(slug.split("/")[1])
        out.setdefault(slug, set()).update(names)
    for slug, extra in EXTRA_ALIASES.items():
        out.setdefault(slug, set()).update(extra)
    return out


def named_in_code(root=None, skip=None):
    """{slug: [module paths]} for every upstream named outside the registries."""
    root = root or REPO
    skip = SKIP if skip is None else skip
    alias = aliases()
    pats = {s: [re.compile(r"\b" + re.escape(n) + r"\b") for n in ns]
            for s, ns in alias.items()}
    hits = {}
    for dirpath, dirs, files in os.walk(os.path.join(root, "toolkit")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel in skip:
                continue
            try:
                txt = open(full, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for slug, ps in pats.items():
                if any(p.search(txt) for p in ps):
                    hits.setdefault(slug, []).append(rel)
    return hits


def register_text(root=None):
    """Section 6.1 ONLY -- not PLAN.md whole.

    `PLAN.md:33` is the prior-art LANDSCAPE table, which grants nothing and is
    not this register; a substring search over the whole file would read it as a
    row and score Fournux accounted-for on the day the row was still missing.
    `studies/quests/AUTHORING.md` section 7 records that exact mistake being
    made by a recon lane, so the narrowing is a fix for an observed failure
    rather than tidiness.
    """
    root = root or REPO
    s = open(os.path.join(root, "PLAN.md"), encoding="utf-8", errors="replace").read()
    start = s.index("### 6.1 The derivation register")
    rest = s[start:]
    # Search from AFTER the heading line. The section own "### " cannot match
    # "\n## " -- three hashes then a space -- but starting at 0 would be
    # relying on that rather than saying it.
    nxt = rest.find("\n## ", rest.index("\n"))
    return rest[:nxt] if nxt != -1 else rest


def notices_text(root=None):
    root = root or REPO
    return open(os.path.join(root, "THIRD-PARTY-NOTICES.md"),
                encoding="utf-8", errors="replace").read()


def notice_headings(root=None):
    """The `## ` headings of THIRD-PARTY-NOTICES.md -- the sections it actually has.

    WHY A HEADING AND NOT THE WHOLE FILE. The old check asked whether the slug
    appeared ANYWHERE in the notices, and the notices end with a section called
    "What is deliberately NOT here" whose whole point is to name upstreams this
    repository does NOT credit -- because they carry no licence and nothing is
    derived from them. One line there reads "`gw-preservation/*` and
    `Py4GW_Reforged` carry no licence at all", and on the strength of it BOTH
    Py4GW slugs scored `notice: yes` (measured 2026-09-08, before this change).
    The checker was reading a disclaimer as an attribution: the exact inversion of
    what it is for. A notice is a section with a heading; that is what this reads.
    """
    return [ln for ln in notices_text(root).splitlines() if ln.startswith("## ")]


def audit(root=None, no_derivation=None):
    """(unaccounted, stale, orphan, missing_notice), each a sorted list.

    `no_derivation` is a PARAMETER rather than a constant read, so a test can
    run the audit against a SYNTHETIC root. The real allowlist describes the
    real tree, so against a planted two-file repo every row in it is an orphan
    -- true, and useless. A checker that can only be pointed at the one tree it
    describes cannot be shown to work.
    """
    root = root or REPO
    nd = NO_DERIVATION if no_derivation is None else no_derivation
    alias, hits = aliases(), named_in_code(root)
    reg, heads = register_text(root), notice_headings(root)

    def anywhere(hay, slug):
        return any(n in hay for n in alias[slug])

    def credited(slug):
        """Named in a notice SECTION HEADING -- see notice_headings."""
        return any(any(n in h for n in alias[slug]) for h in heads)

    unaccounted = sorted(s for s in hits
                         if not anywhere(reg, s)
                         and not credited(s)
                         and s not in nd)
    stale = sorted(s for s in nd if anywhere(reg, s))
    orphan = sorted(s for s in nd if s not in hits)
    missing_notice = sorted(s for s in ATTRIBUTION_REQUIRED
                            if anywhere(reg, s) and not credited(s))
    return unaccounted, stale, orphan, missing_notice


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", action="store_true",
                    help="print every (module, upstream) mention")
    args = ap.parse_args()

    alias, hits = aliases(), named_in_code()
    reg, heads = register_text(), notice_headings()
    print(f"{len(hits)} upstreams named in toolkit/ outside the registries "
          f"({len(SKIP)} files skipped by construction)\n")
    print(f"  {'upstream':38} {'6.1':>5} {'notice':>7} {'no-deriv':>9}  modules")
    print("  " + "-" * 84)
    for slug in sorted(hits):
        r = any(n in reg for n in alias[slug])
        n = any(any(x in h for x in alias[slug]) for h in heads)
        d = slug in NO_DERIVATION
        flag = "" if (r or n or d) else "   <-- UNACCOUNTED"
        print(f"  {slug:38} {'yes' if r else '--':>5} {'yes' if n else '--':>7} "
              f"{'yes' if d else '--':>9}  {len(hits[slug])}{flag}")
        if args.pairs:
            for m in hits[slug]:
                print(f"  {'':38} {'':5} {'':7} {'':9}    {m}")

    unaccounted, stale, orphan, missing = audit()
    print()
    for label, rows, why in (
            ("UNACCOUNTED", unaccounted,
             "named in a module with no 6.1 row, no notice and no NO_DERIVATION row"),
            ("STALE NO_DERIVATION", stale, "the upstream now HAS a 6.1 row"),
            ("ORPHAN NO_DERIVATION", orphan, "nothing in toolkit/ names it"),
            ("MISSING NOTICE", missing,
             "attribution-required licence with a 6.1 row and no notice")):
        if rows:
            print(f"  {label}: {', '.join(rows)}  -- {why}")
    if not (unaccounted or stale or orphan or missing):
        print("  clean: every named upstream is accounted for")
    return 1 if (unaccounted or stale or orphan or missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
