# Identifier conventions — for NEW tokens

**Written 2026-08-20.** This file is the home of the convention. `CLAUDE.md` points here
in one line and does not restate it, and neither should anything else — that is the
lesson of [HANDOFF.md](HANDOFF.md) §2.3, where the same ladder written down in two places
drifted until `R0` and `R0a` named overlapping but unequal things. The evidence, the
census and the three defects this fixes are in [HANDOFF.md](HANDOFF.md) §2. Status
authority remains `PLAN.md` §3.

> **Nothing here applies retroactively, and that refusal is a decision, not an omission.**
> Every existing identifier is grandfathered — `C-6`, `R0a`, `H1`, `A5` keep their names
> in the documents, in the commit messages and in the owner's own memory of what happened.
> A mass rename was considered and **refused**: it is the exact shape of the 2026-08-12
> provenance scrub, where 46 citations were rewritten across sixteen documents and all 46
> were reverted. Owner-ratified: `PLAN.md` §7 Q8 (2026-08-20). Read the box at the top of
> [HANDOFF.md](HANDOFF.md) before proposing one.
> The convention below helps documents written after it; §4's resolver is what helps with
> the ones written before it, and it is the half that pays off today.

## 1. The rule

A new identifier is **a registered word, one hyphen, and the document's own local token**:

```
GATEFIRE-C3        PROPS-P1        ITEMMODS-M1
```

- **The word names the document that DEFINES the token**, and is unique across the tree.
  Where an arc has a single minting document, the arc's name is the obvious word
  (`CUSTOMAREA`). Where an arc has several — `studies/profession` already does — each
  minting document takes its own word (`MODDABLE`, `WORKAROUNDS`). The unit is the
  defining document because that is the thing a reader has to open.
- **Deriving the word from the filename: take the SUBJECT, not the file shape.**
  `PROBE-GATEFIRE.md` takes `GATEFIRE` — `PROBE`, `FINDINGS`, `PLAN`, `HANDOFF` and
  `NOTES` name a shape, not a subject, and are never the word. Strip the shape prefix
  and keep the rest verbatim, plural included (`WORKAROUNDS.md` → `WORKAROUNDS`);
  uppercase the result — verbatim means the letters and the plural, not the case
  (`HANDOFF-props.md` → `PROPS`, if it minted). Where the shape word is a suffix
  (`U7-RUN.md`), strip it from either end; where stripping leaves something that fails
  the constraints below or collides with a sibling, name the word explicitly in the
  legend and move on — the legend is the registration, the filename only the default.
  Where an arc has several minting documents and one of them is the arc's own
  `FINDINGS.md`, that one takes the ARC name (`MOVEMENT`) and the others take their
  own subject word.
- **The word is uppercase A–Z0–9, four characters or more, with no internal hyphen** so
  the split at the first hyphen is unambiguous. Do not abbreviate to two letters: a short
  code buys nothing a word doesn't and re-creates the defect.
- **The local token is whatever series that document already runs** — `C3`, `D1`, `4b`.
  Keep the shape you have; do not renumber to fit a prefix.
- **The token stays dumb.** It does not encode what kind of thing it is. Encoding kind in
  the letter is what produced defect (b) — the same letter meaning "correction" in one
  arc and "build step" in another. The *legend* says the kind; see §2.
- **One exception: `PLAN.md` §3's ladder.** It is the project's own namespace, it is
  cited from everywhere, and its rungs stay bare (`R5m`, `R-ISLE`). Note that some
  rungs are themselves hyphenated (`R-ISLE`, `R-IDENTS`) — those are NOT word
  prefixes: `R` is not a registered word, and anything whose lead is under four
  characters is a ladder rung, not a prefixed token. Everything else that mints
  identifiers takes a word.

## 2. Registering a word

There is no central list of words, deliberately. A registry outside the defining document
is a second copy of a fact, and [HANDOFF.md](HANDOFF.md) §2.3 records what the second
copy did to the R ladder.

1. **Pick a word** per §1 — the subject, recognisable out of context.
2. **Check it is free**, with a plain grep on the word plus its hyphen:

   ```bash
   grep -rn --include='*.md' -F 'GATEFIRE-' PLAN.md HANDOFF.md TESTS.md studies/
   ```

   Use `-F` on the word, NOT §4's resolver — a legend line is bold prose, and neither
   §4's pattern nor `whichrung.py` can see a definition that is not a table row or a
   heading (`whichrung.py GATEFIRE` answers NOT FOUND for a word that is in use; that
   is the pattern's documented floor, not a free word). If anything outside your own
   document answers, pick another — with two carve-outs: hits inside `studies/idents/`
   and inside `PLAN.md` §3's own `R-IDENTS` row are this convention TALKING ABOUT a
   word, not a document using it, so ignore them (otherwise every worked example below
   poisons its own word); and `RUNBOOK.md` and `CLAUDE.md` sit outside this corpus, so
   check them by hand if the word is operational rather than research vocabulary. A
   word is TAKEN only when a legend line in a defining document declares it. Check it
   against the citation labels too (`GWCA`, `WIKI`, `Py4GW`, `GWLP-R`), which are the
   existence proof this convention is copied from — words, used across many documents,
   zero collisions (HANDOFF §2.5).
3. **Declare it once, in your defining document**, beside the table or list that mints the
   tokens. That line *is* the registration, and it is where the KIND lives:

   ```
   **Identifiers.** `GATEFIRE-C<n>` = build steps, things to do. `GATEFIRE-H<n>` = rival
   hypotheses. Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).
   ```

   One document may run several series under one word; the legend names each letter's
   kind on its own line or its own row. A plain `grep -F '<WORD>-'` finds the
   declaration; the token resolver cannot, because a legend line is prose and the
   resolver matches only defining rows and headings. That is the price of having no
   registry, and it is paid knowingly.

## 3. Three worked examples

- **A new arc mints its first token.** `studies/itemmods` has decode milestones and no
  identifiers yet (OBSERVED 2026-08-20). Word `ITEMMODS`, legend line declaring
  `ITEMMODS-M<n>` = milestone, table row `| **ITEMMODS-M1** | … |`. Well-formed.
- **One document, two series (hypothetical — PROPS.md mints nothing today, OBSERVED
  2026-08-20).** Suppose `studies/customarea/PROPS.md` grew a rung table *and* a
  prediction table. Word `PROPS`, one legend with two rows: `PROPS-A<n>` = rung,
  `PROPS-P<n>` = a prediction registered before a probe runs. `PROPS-P1` is well-formed;
  `PROPS-PRED1` is not — the kind belongs in the legend, not in the token.
  `customarea/FINDINGS.md`'s existing `P1`–`P4` stay `P1`–`P4`; nothing here reaches
  backwards.
- **The collision this is for.** A document wanting `R1`–`R6` as its own route table —
  `studies/profession/WORKAROUNDS.md` already did, against the project ladder's `R1` —
  would today mint `WORKAROUNDS-R1`. The ladder's bare `R1` stays bare, and
  WORKAROUNDS' existing bare `R1`–`R6` stay grandfathered; the benefit is that `R1` and
  `WORKAROUNDS-R1` cannot be confused by a session that opened only one of the two
  documents. (Same arc as §1's multi-document example, on purpose — profession is the
  arc this rule was shaped on.)

## 4. Resolving a token you found in prose

**Ship-today mitigation, and it works on the grandfathered tokens too**, which the
convention above cannot help. It matches *defining* sites — a table row or a heading
beginning with the token — not every passing mention.

**The tool is `python toolkit/whichrung.py C-8`** (add `--full` to print the whole
defining row). It is hyphen-insensitive on purpose: `C8` and `C-8` resolve to the same
sites, because [HANDOFF.md](HANDOFF.md) §2.2 rules the hyphen a weak signal, not a
namespace. `toolkit/identlint.py` is a DIFFERENT tool — it prints the census and the
collision count and is the tripwire in §5; it has no resolve flag and ignores
unrecognised arguments silently, so do not reach for it here.

The raw one-liner, for a shell with no toolkit to hand — looser than the tool, and
hyphen-LITERAL:

```bash
T=C8; grep -rn --include='*.md' -E "^\| *\*{0,2}${T}\b|^#{1,6}.*\b${T}\b" PLAN.md HANDOFF.md TESTS.md studies/
```

**The one-liner is literal; the tool is not, and the difference bites on this very
example.** `T=C-8` finds only archivewrite's corrections-ledger row; `T=C8` finds only
the cmsg heading and the PROBE-GATEFIRE build-step row. The tool finds all three — and
the true answer is AT LEAST three, because a fourth `C8`, the lead of
`studies/combat/PLAN.md`'s own bold-list series, sits in exactly the class the floors
paragraph below is about, invisible to row-and-heading patterns. Four arcs, four kinds,
one bare token; the sentence this arc opened on — *"C-8 finished"* — is ambiguous
across all of them. Run the grep with BOTH spellings, or use the tool, which normalises
the hyphen away; a one-hit result from the raw grep is not a resolution. **The matching
pattern and every count live in the tools, not here** — one home per fact, same reason
as §2. (This one-liner's historical home, HANDOFF §4, is annotated as superseded; this
is the live copy.)

**The counts are floors, not totals — OBSERVED 2026-08-20.** HANDOFF §2.1's 108 rows over
10 documents came from a table-row-leading pattern; re-running it wider the same day found
definitions in headings and in bold list leads across roughly two dozen further documents,
nearly three times the original count, and *that* is still a floor because a token first named
mid-paragraph matches no reliable pattern at all. Quote the tool's live number, dated, or
quote none.

## 5. Enforcement — an accumulation tripwire, not a gate

`toolkit/identlint.py` + `toolkit/test_identlint.py`, the same posture as
`toolkit/provlint.py`: existing tokens are grandfathered into a baseline, and the test goes
red when *new* unprefixed namespaces accumulate past it — not when a commit contains one.
A hard gate over 80 documents produces a red suite for reasons nobody wants to fix at 2am,
and a rule nothing checks at all is a wish. This is the middle option, on purpose. The
ceilings live in the TEST and the pattern in the tool — `identlint.py` counts and never
judges — and this document restates neither; a session raising a ceiling records why in
the test, where provlint's are.

## 6. The bare-integer commit-subject prefix is RETIRED

**OBSERVED (the commits and their monotonicity —
`git log --all --format='%s' | grep -E '^[0-9]+:'`) + RECONSTRUCTION (what the number
meant), 2026-08-20.** A run of bare-integer subject prefixes starts at `29:`
(`b3d282a`) and climbs monotonically, all dated 2026-08-19/20 (HANDOFF §2.4) — and the
count is deliberately NOT pinned here: it grew by one (`43:`) between this arc's
census and its landing, because each subject is immutable but the SET grows until
minting stops. Run the command; do not trust a copy. No document ever defined the
sequence. It is the plain form of the informal round counter that `PLAN.md` also
cites as `§N` / `§N.M` for the pvpui/heroes/attributes/items investigation — each such
commit resolves against the `PLAN.md` diff it landed with, and nowhere else. The number
alone does not resolve: `studies/customarea/FINDINGS.md` uses `§30`, `§32`, `§35` as its
own local sections, unrelated. **Retired as of this convention: stop minting them.**
Nothing is rewritten; this paragraph exists so a session that meets one in `git log`
has somewhere to land.
