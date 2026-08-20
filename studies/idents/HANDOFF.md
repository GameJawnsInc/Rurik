# Identifier conventions — handoff

**Written 2026-08-20.** Status authority remains `PLAN.md` §3 and §8; this arc has no
rung there yet and should get one before it lands. This file is what a cold session
needs to open the arc without re-deriving the census, and — more importantly — what it
needs in order not to repeat a failure this repo has already paid for once.

> ## ★ READ THIS BOX FIRST — the failure mode of this arc is the CURE, not the disease
>
> The problem below is real but **small and cheap**. The obvious fix — sweep 80 study
> documents and renumber 108 identifiers into a clean scheme — is the **exact shape** of
> the 2026-08-12 provenance scrub that `CLAUDE.md` records: a session read a rule
> literally, rewrote 46 citations across sixteen documents, and **all 46 were reverted**
> when the owner asked whether the cure cost more than the disease. It did.
>
> **A mass rename of existing tokens is out of scope and should be refused.** Every
> historical identifier is load-bearing in commit messages, in PLAN.md §8 write-ups, and
> in the owner's own memory of what happened. `C-6` means something to anyone who lived
> through the archivewrite arc, and renaming it to `AW-COR-6` buys a cold agent
> five seconds and costs everyone else their index.
>
> **The deliverable is a convention for NEW identifiers plus a resolver, not a migration.**

---

## 1. The problem, stated once

A session writes "C-8 finished, looking into C-9 next, before D-1 can be approached."
The reader cannot tell from that sentence which document defines `C-8`, what *kind* of
thing it is, or whether `D-1` exists at all. This is not hypothetical — it is the
question that opened this arc.

## 2. What is already measured — do not re-derive this

All **OBSERVED (mine, 2026-08-20)**, from `C:/gd/Rurik` at `9ee3010`, by grep over
`PLAN.md`, `HANDOFF.md`, `TESTS.md` and `studies/`. 52 study arcs, 80 study documents.

### 2.1 The census — 108 single-letter work-item rows across 10 documents

| Document | Tokens defined |
|---|---|
| [PLAN.md:348](../../PLAN.md:348) | `R0a R0b R1 R1.5 R2 R3 R4a R4b R4c R5 R5m` |
| [HANDOFF.md:107](../../HANDOFF.md:107) | `R0 R1 R2 R3 R4a R4b R4c R5` |
| [studies/archivewrite/FINDINGS.md](../archivewrite/FINDINGS.md) | `A1–A8`, `C-1–C-13` |
| [studies/customarea/FINDINGS.md](../customarea/FINDINGS.md) | `A-1 A0 A1–A3 B1–B3 C0–C3 D1 D2 E1–E3 F1 F2 P1–P4` |
| [studies/movement/PROBE-GATEFIRE.md](../movement/PROBE-GATEFIRE.md) | `C1–C9`, `H1 H2` |
| [studies/unitmodels/PLAN.md](../unitmodels/PLAN.md) | `U1–U10` |
| [studies/quests/AUTHORING.md](../quests/AUTHORING.md) | `Q0 Q1 Q1b Q2 Q2b Q3–Q9` |
| [studies/models/PLAN.md](../models/PLAN.md) | `M1–M6 M6b` |
| [studies/profession/MODDABLE.md](../profession/MODDABLE.md) | `P1–P4` |
| [studies/minimap/FINDINGS.md](../minimap/FINDINGS.md) | `A1 A2` |

### 2.2 Three distinct defects, and they need different fixes

**(a) Cross-arc collision.** `A1` and `A2` are defined in three arcs (archivewrite,
customarea, minimap). `C1`–`C3` in two. `P1`–`P4` in two. The bare token carries no arc.

**(b) Kind collision — the sharper one.** The same letter means different *categories*
of thing, so even knowing the arc does not tell you what a token IS:

| Token | Arc | What it actually is |
|---|---|---|
| `C-1`–`C-13` | archivewrite | a **corrections ledger** — things we got wrong |
| `C1`–`C9` | movement | **build steps** — things to do |
| `C0`–`C3` | customarea | **ladder rungs** — §9 |
| `A1`–`A8` | archivewrite | **routes/options** — mutually exclusive candidates |
| `H1`,`H2` | movement | **rival hypotheses** — [PROBE-GATEFIRE.md:140](../movement/PROBE-GATEFIRE.md:140) |
| `P1` | customarea | a **prediction** |

"C-8 finished" is not even well-formed against the archivewrite reading — a correction
is not a thing you finish. The hyphen is a *weak* signal (archivewrite hyphenates,
movement does not) but it is not a rule and must not be taught as one.

**(c) The same letter, twice, in ONE document.** [customarea/FINDINGS.md:681](../customarea/FINDINGS.md:681)
§9 defines ladder rows `A0`, `B1`, `C0`, `D1`, `F1`; [§11:766](../customarea/FINDINGS.md:766)
then uses `### A.`, `### B.`, `### C.` as *corrections* section headings. Same document,
same letters, different systems.

### 2.3 The R ladder has already drifted, and this is the strongest evidence

**OBSERVED, and it is a live defect, not a hypothetical.** [PLAN.md:348-358](../../PLAN.md:348)
carries `R0a`, `R0b`, `R5m`, `R1.5`. [HANDOFF.md:107-114](../../HANDOFF.md:107) still
carries the un-split `R0` and has none of the other three. `R0` was split into `R0a`
(vault + provenance) and `R0b` (live capture) in PLAN.md and HANDOFF.md was never
updated — so **"R0" in HANDOFF.md and "R0a" in PLAN.md name overlapping but unequal
things, and a cold session reads whichever it opens first.** That is verbatim the
failure `CLAUDE.md`'s opening rule was written about, occurring inside the identifier
system itself. Fixing this one is worth more than any convention.

### 2.4 A fourth namespace exists only in the git log

14 commits carry a bare-integer subject prefix, running `29:` → `42:` monotonically
(`git log --format='%s' | grep -E '^[0-9]+:'`). **No document defines it.** A session
reading "40: the player's swing is the WEAPON's number" cannot resolve `40` anywhere in
the tree. Decide whether this sequence is retired, documented, or left alone.

### 2.5 Prior art that already works — study it before inventing

Citation labels (`GWCA`, `WIKI`, `Py4GW`, `GWLP-R`) are used across 5–7 documents each
with **zero collisions and zero ambiguity**, because the label is a word, not a letter.
That is a free existence proof for the recommendation in §3.

## 3. The decisions the new session has to make

Framed, not pre-made. My recommendation is marked where I have one.

1. **Scope.** Confirm the box at the top: new identifiers only, no migration. *Get the
   owner's yes on this explicitly* — it is the decision that determines whether this arc
   costs an hour or two days.
2. **Prefix shape.** Recommendation: **arc-scoped word prefixes**, `GATEFIRE-C3`,
   `AW-A5`, `CUSTOMAREA-D1` — following §2.5's proof rather than inventing. The
   alternative is bare letters plus a mandatory "in the gate-fire arc" in prose, which
   is what we do now and is what failed.
3. **Kind encoding.** Does the token say what kind of thing it is (`H` hypothesis,
   `C` correction, step numbers bare), or does the *table* say it and the token stay
   dumb? Recommendation: the table says it — a per-document legend row — because
   encoding kind in the token is what produced defect (b) in the first place.
4. **Where the convention lives.** `CLAUDE.md` is already long and its own §"Where the
   project is" warns against restating things. Recommendation: a short
   `studies/idents/CONVENTION.md`, with one line in `CLAUDE.md` pointing at it.
5. **Enforcement, and this is the real question.** `CLAUDE.md` says *"a rule nothing
   checks is a wish"* — and it is right; `PLAN.md` §1.1's second gate sat broken for two
   days behind exactly that. But `toolkit/provlint.py` is explicitly *"an accumulation
   tripwire, not a gate."* Pick which of the two this is. Options:
   - a `test_identlint.py` that fails when a NEW table-row token has no arc prefix
     (needs a baseline of the 108 existing tokens, grandfathered);
   - a tripwire that only reports growth in the collision count;
   - documentation only, no checker.
   Recommendation: the middle one. A hard gate on 80 documents will produce a red suite
   for reasons nobody wants to fix at 2am.
6. **Fix §2.3 regardless of the rest.** HANDOFF.md's R table should either be deleted in
   favour of a pointer to PLAN.md §3, or synced. This is a one-commit fix and does not
   depend on decisions 1–5.
7. **Retire or document §2.4's integer prefix.**

## 4. The resolver — ship this even if nothing else lands

This works today and is the cheapest possible mitigation. It matches only *defining*
rows (a table row beginning with the token) and headings, not every passing mention:

```bash
T=C8; grep -rn --include='*.md' -E "^\| *\*{0,2}${T}\b|^#{1,6}.*\b${T}\b" PLAN.md HANDOFF.md TESTS.md studies/
```

For `C8` it returns two hits — `studies/cmsg/FINDINGS.md:151` and
`studies/movement/PROBE-GATEFIRE.md:355` — which demonstrates the problem and solves it
in the same line. Consider wrapping it as `toolkit/whichrung.py` so it is discoverable;
consider also that a bash one-liner in `CLAUDE.md` may be enough and a tool is scope
creep. **Do not skip this in favour of the convention** — the convention only helps
documents written after it, and there are 80 written before it.

## 5. Working notes for the new session

- **Establish the tree first**, per `CLAUDE.md`: `git rev-parse --show-toplevel`. This
  arc touches root-level documents, so a stale worktree is especially dangerous here.
- **Take a branch and a worktree.** But note the conflict: this arc's output is a
  convention other sessions need to *read*, so it is stale for everyone until merged.
  Land it fast rather than perfecting it.
- **No client, no server, no vault writes.** This arc is documents only.
- **Zero code changed means zero tests** — unless decision 5 produces a checker, in
  which case run `test_srclint.py` and the new test, not the full suite.
- **Add the PLAN.md §3 row and the §8 next-action** when it lands, in the same commit.

## 6. What this handoff does not claim

The census in §2.1 was produced by one grep pattern over table-row-leading tokens. It
will **miss** identifiers defined in prose or in list items rather than table rows, and
it drops rows whose token is followed by a status marker in some shapes. Treat 108 as a
**floor**, not a total — same discipline as `asserts.py` counts. Re-run it wider before
publishing any headline number.
