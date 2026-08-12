# Assert expressions in committed prose — an audit, a scrub, and its revert

**Read §6 first if you are here for the rule.** The scrub this document spends most of
its length on was **undone**. What is live is the refined ruling and the checker; the
rest is kept as the record of a rule read too strictly and what that cost.

**2026-08-12.** The provenance gate's boundary is MEASUREMENT vs EXPRESSION (owner's
ruling 2026-08-11, [PLAN.md](../../PLAN.md) §7 Q3). Measured facts are permitted in
bulk; ArenaNet's expression is not, and the ruling names one form of it outright:

> **Still refused:** … **verbatim assert expressions with their source path and line**.
> A derived table may carry the *constraint* (opcode, field, bound, address) and must
> leave the expression text out.

`toolkit/content.py` has enforced the *measurement* side of that gate for
`source = "client-table"` rows since the day it was written, and `test_content.py`
proves the refusal fires. The *expression* side was enforced by nobody and applied to
nothing. This study audited what accumulated behind that, scrubbed 46 sites, and then
**reverted every one of them** when the owner refined the ruling rather than authorise
the rest of the sweep. What closes the gap is the checker, at a much lower setting than
the audit assumed.

**Label vocabulary** is [studies/character/FINDINGS.md](../character/FINDINGS.md)'s.

---

## 1. The answer in one page

- **MEASURED.** The `P:\Code` grep that opened this — 73 occurrences in 17 files —
  is **the wrong instrument, and it undercounts by about 4x**. Only **13 of the 73**
  are the refused triple. Scanning for the *rule* instead of for one string finds
  **134 refused triples in 16 files**. The grep misses them because most of the drift
  never spells the full build-machine path: it cites `AgMsg.cpp:513` or `Array:587`,
  which is what `asserts.py --grep` and the crash dialog actually print.
- **MEASURED.** The drift takes **three shapes**, and any tool built for one misses
  the others:
  1. the **crash dialog** — `Assertion: <expr>` with the location beside it or on the
     next line;
  2. the **`asserts.py --grep` paste** — `Module:line "<expr>"`;
  3. an **unquoted expression** in a fenced block with no label and no quotes, which
     is the one both of the obvious matchers miss.
- **This is drift, not defiance.** Of the 16 files carrying a triple, the great
  majority of the text predates the 2026-08-11 ruling. Before that date the boundary
  was not written down: `.gitignore`'s rationale said "only our code and our
  observations", which cold sessions read as forbidding *any* table of client-read
  numbers — the failure mode recorded at the top of `CLAUDE.md` is sessions refusing
  **too much**, not helping themselves to too much. The docs were written under a rule
  that had no expression/measurement line in it, by sessions doing exactly what the
  repo asks — reading the client rather than reasoning about it — and quoting their
  evidence. §3 is the timeline.
- **SCRUBBED, THEN REVERTED — and the round trip is the finding.** 46 sites in 15
  files were rewritten to keep the constraint and drop ArenaNet's wording. Once the
  ruling was refined (below), all 46 were **reverted**: with citation permitted, every
  rewrite was a net loss. The paraphrases ran longer and repeatedly dropped the exact
  symbol — `MissionCliIsGameMaster()` became "a game-master predicate",
  `!s_reusableAgentArray.Count()` became "an empty-list bound" — and four crash-dialog
  transcripts became second-hand reports of a primary artifact. The tree is back to
  its pre-audit text, at **134 citations in 16 files**. §4 is what the scrub cost,
  kept because it is the evidence that reverting was right.
- **STOPPED, by the owner, the same day — and the stop is the most useful result
  here.** 104 citations remained in 5 files, 65 in
  [studies/smsg/FINDINGS.md](../smsg/FINDINGS.md). Asked whether provenance was
  starting to cost more than it protected, the owner **refined the ruling** rather
  than authorising the rest of the sweep: *a single assert cited as evidence is a
  measurement; the refusal targets bulk dumps and decompiled bodies.* The 104 are
  permitted, the backlog is retired, and `smsg` keeps the quotes that make its naming
  argument auditable. §6.
- **DONE.** `toolkit/provlint.py` + `toolkit/test_provlint.py`, in `CLAUDE.md`'s suite
  list — repurposed from a zero-tolerance gate into an **accumulation tripwire**. It
  is silent on `smsg`'s 65 and fires on a 15-row dump appended to a document that
  argues from none. That is the only part of this study with no recurring cost.

---

## 2. The classification of the 73

`git grep -n 'P:\\Code' -- studies` returns 73 lines in 17 files. Classified against
the ruling rather than against the string:

| | | count |
|---|---|---|
| **(a)** | expression **+** path **+** line — **REFUSED** | **13** |
| **(b)** | a location and nothing else — **permitted**, and the docs are built out of these | **55** |
| **(c)** | expression **+** path, **no line** — incomplete triple, judgement call | **5** |

### 2.1 The 13 in category (a)

All were scrubbed and all were **reverted** once the ruling was refined (§6). The
table is kept as the classification it was, and the third column records what the
scrub would have left — which is the concrete form of §4's argument that reverting was
right, since in most rows it is strictly less than the original.

| site | constraint kept | location kept |
|---|---|---|
| `agentprops/FINDINGS.md:390` | upper bound 1.0 on `fraction` | `CharPool.cpp(84)`, build 38797 |
| `cmsg/FINDINGS.md:308` | two-sided bound **[-1.0, 1.0]** on `rotation` | `ChCliApi.cpp:5562` |
| `customarea/FINDINGS.md:4061` | index-against-count bound | `Array.h(587)` |
| `datwrite/FINDINGS.md:1719` | non-null bound on the `skill` pointer | `ChCliSkill.cpp(1022)` |
| `enemy/PLAN.md:341` | non-positive bound on the damage message's `amount` | `AvChar.cpp(5893)` |
| `enemy/PLAN.md:449` | index-against-count bound | `Array.h(587)` |
| `enemy/PLAN.md:574` | strictly-positive bound on `range` | `CharPool.cpp(98)` |
| `enemy/PLAN.md:874` | the lookup's found-flag bound | `Map.cpp(1762)` |
| `enemy/PLAN.md:969` | non-null pointer bound, `baseItem` adjacent | `ItCliApi.cpp(400)` |
| `enemy/PLAN.md:1026` | non-zero bound on `m_attackInterval` | `AvChar.cpp(4791)` |
| `enemy/PLAN.md:1173` | non-zero bound on `m_attackInterval` | `AvChar.cpp(4791)` |
| `enemy/PLAN.md:2381` | upper bound 1.0 on `fraction` | `CharPool.cpp(84)`, build 38797 |
| `tape/FINDINGS.md:408` | `PLAYER_FLAG_CONNECTED` required **clear** in `playerFlags` | `MsCliGame.cpp:76` |

### 2.2 The 5 in category (c), and how they were ruled

`(c)` is expression text beside a path with **no line number**, so the ruling's triple
is not complete. Four of the five were scrubbed anyway, on the ground that the refused
artifact is the verbatim text and the missing line makes it a smaller disclosure rather
than a different one. All four are now reverted; the reasoning is recorded because it
is what the (c) category MEANT under the strict reading:

- `datwrite/FINDINGS.md:105` — scrubbed to "the bound on `s_skill`'s array size".
- `enemy/PLAN.md:599` — bare identifiers `syncPtr`/`asyncPtr`; scrubbed to "bounds on".
- `enemy/PLAN.md:600` — scrubbed to "index-against-count bound".
- `textrec/FINDINGS.md:42–44` — expression on :44, path on :42. Scrubbed, and this is
  one of the two places the rewrite **added** a measurement: the claim is "ArenaNet
  naming both the struct and its size", and with the expression gone the size had to be
  stated outright (`StringHeader` is **6** bytes, which the adjacent `cmp word ptr
  [edi], 6` independently gives).

### 2.3 Sixteen more, found by hand after the checker said clean

Grepping the tree for the *expressions themselves* — `fraction <= 1.0f`,
`index < m_count`, `damage.amount <= 0` — after the machine pass turned up sixteen
further sites in files already reported clean. They are all prose paraphrases of the
triple, which §5 records as the checker's largest blind spot. Scrubbed the same way and
reverted the same way:
`agentprops` :210 :427 :493, `enemy/PLAN.md` :19 :587 :1209–:1215 (a nine-row
stack-trace table, module + line + expression per row) :1224 :2394, `tape` :156 :722,
`presearing/MANIFEST.md` :157 :841, `presearing/R4C2-FEASIBILITY.md` :53, and
`PLAN.md` :1655.

One site is deliberately **kept**: `PLAN.md:1112`, where the ruling illustrates what it
forbids with `P:\Code\Base\Rtl\Random.cpp` plus an expression. A rule that cannot show
what it means is harder to follow than one that quotes itself once, and `provlint.py`
does not flag it (no line number).

One was **left** for the owner:

- `livekey/FINDINGS.md:42` — `expression "init"`. A bare identifier with no line. The
  ruling explicitly permits "the *constraint* (opcode, **field**, bound, address)", and
  a one-word identifier is a name rather than authored text. Flagged here so the
  decision is visible rather than silent; if the owner wants (c) treated as (a)
  uniformly, this is the one site left to change.

---

## 3. Why this is drift — the timeline

The ruling that makes these refusable is **dated 2026-08-11**. The documents are older,
and the direction of the pre-ruling error was the opposite one.

- Before 2026-08-11 the gate's written rationale ended "— only our code and our
  observations". `CLAUDE.md` now records what that produced: sessions read it as
  forbidding a table of numbers read out of the client and **refused every time** — a
  derived assert table left undecided, R4c-2's unit data left unbuilt. The problem the
  ruling was written to fix was **excessive refusal**.
- Meanwhile the repo's central method — "the wins in this repo all came from capturing
  the client and reading it" — actively rewards quoting the client's own words, and
  `CLAUDE.md` still calls the assert strings the thing that "converts *which
  reconstruction do we believe* into *which file did they write it in*". A session
  citing assert text in 2026-08-06 was following the method as written.
- The ruling drew the measurement/expression line for the first time and enforced it in
  exactly one place — `content.py`, for `source = "client-table"` rows. Prose was never
  in scope and no tool ever looked at it.

So: sessions doing the right thing under the rule they had, and a rule that moved
without a sweep behind it. The interesting part is the **enforcement asymmetry**, not
anybody's conduct — one half of one ruling got a checker and a test on the day it was
written, and the other half got a sentence.

---

## 4. What the scrub cost — measured, which is why it was reverted

**At the time this was written as "nothing load-bearing", and that was true only in the
narrow sense that no claim became unsupported.** Reread against a ruling that permits
citation, the cost is plain and it is not nothing. The rewrite rule — keep bound, field,
symbol, address, line; drop wording — turns out to lose information *whenever the
wording is where the symbol lives*, which for an assert expression is most of the time:

| original | rewrite | what went |
|---|---|---|
| `GmView` — 2840 `MissionCliIsGameMaster()` | "2840 a game-master predicate" | the function name |
| `AvManager` — 775 `!s_reusableAgentArray.Count()` | "an empty-list bound on the reusable-agent array" | the symbol, and 20 characters longer |
| `AvChar` — 4745 `loop < 500` | "4745 bounds a loop counter below 500" | nothing, and still longer |
| `ChCliApi:4809 !(playerId & CHAR_CLASS_BASE_MASK)` | "bounds the id to have no `CHAR_CLASS_BASE_MASK` bits set" | nothing, and two lines instead of one |
| `missionMaskBytes <= MISSION_MASK_BYTES` | "bounds a mission-mask byte count by `MISSION_MASK_BYTES`" | the parameter name |

**And the crash-dialog blocks were the worst of it.** Four fenced transcripts —
`agentprops`, `enemy` ×3 — were rewritten from what the client actually printed into a
description of what it printed. That converts a **primary observational record** into a
second-hand report, in a repo whose first rule is "real bytes → replicate ONE piece →
verify". `enemy/PLAN.md` even had to have its own framing sentence edited from *"the
client says so in ArenaNet's own words"* to *"the client's own bound says so"* — the
prose was fighting the scrub, which is usually the tell.

Two rewrites did **add** a measured detail (`textrec`'s `StringHeader` size, `texture`'s
8-byte stride). Both turned out to be redundant: the surrounding text already carried
the number, which is why the revert loses nothing there either.

**All 46 are reverted.** The tree reads as it did before the audit.

`studies/texture/FINDINGS.md` still earns its line: it has **zero** `P:\Code`
occurrences, was correctly reported clean under that grep, and carried a citation all
the same (`ImgAtex.cpp:1560`). That single file is the whole argument for scanning for
the rule rather than for a string — a point that survives the ruling change intact,
because it is about the instrument, not the policy.

---

## 5. The checker

`toolkit/provlint.py`, proved by `toolkit/test_provlint.py` (19 checks, in the suite
list). Two design points are worth recording because both were arrived at by getting
them wrong first:

- **The hard problem is the false-positive rate, not the catch rate.** A location, a
  line, a field name, a bound, a VA and a struct offset are *all permitted* and the
  study docs are built out of them. The first draft flagged 457 sites at ~37% precision
  — quoted *locations*, our own `authsrv.py:897` citations, our own disassembly,
  upstream mirrors, and `Build: 38797` parsed as a source location. A checker at that
  precision gets switched off inside a day, and switching it off restores the exact
  silence it exists to end. `test_provlint.py` §3 is therefore the long section:
  fifteen permitted forms that must **not** be reported.
- **`Module:123` is indistinguishable from English prose without a vocabulary.** So
  pass 1 harvests one: a stem is vouched only if the corpus shows it somewhere carrying
  a real `.cpp`/`.h` on a line with no upstream marker. That is what separates
  `AgMsg:208` from `Build: 38797`. The denylist for upstream headers is checked in the
  direction that can do damage — it must not shadow a real ArenaNet module. `MapData`
  was on it for a draft on the strength of GWLP-R's `MapData.scala`, which would have
  silently dropped `customarea`'s findings; the test now pins that it is off.

**Known limits, stated rather than discovered later.** The third is the one that
matters and it was found by grepping for the expressions *after* declaring the files
clean — which is why it is written down here rather than left for the next session:

- It reads `.md` only. `toolkit/` sources carry `P:\Code` in 9 files; those are tool
  fixtures and comments, and none is a refused triple, but nothing checks that.
- It requires a **line number**, so category (c) — expression + path, no line — is
  invisible to it. All four scrubbed (c) sites were found by hand.
- **It matches three MACHINE formats and no prose paraphrase.** `AgMsg:208 "expr"` is
  caught; *"the CharPool method whose line 84 asserts `expr`"* is not. Sixteen such
  sites survived the first pass in files this study had already called clean.
  **Under the zero-tolerance reading that was a defect; under the tripwire it is
  not**, and the difference is worth stating because it is the clearest example of a
  rule change making work disappear rather than creating it. A dump is a paste, and a
  paste keeps its machine format — nobody hand-paraphrases sixty asserts into prose.
  So the blind spot does not matter at the job the checker now has. **There is no
  standing obligation to hand-grep for paraphrases**; that expectation was created by
  the first draft of this study and is deleted. The checker catches what it catches,
  and that is the standard.
- An upstream marker on a line suppresses the two inference-based shapes. That is
  deliberate (the second gate is a licence question, not this one) but it is a real
  blind spot, and it hid `mapdata/FORMAT.md:233` for the length of a draft because the
  row happens to mention gw-preservation. The crash-dialog shape is now exempt from
  the suppression; the other two are not.

---

## 6. The 104 that remain — CLOSED, and the sweep was stopped

| file | citations |
|---|---|
| [studies/smsg/FINDINGS.md](../smsg/FINDINGS.md) | **65** |
| [studies/monsterai/FINDINGS.md](../monsterai/FINDINGS.md) | 12 |
| [studies/reconstruction/FINDINGS.md](../reconstruction/FINDINGS.md) | 11 |
| [studies/customarea/FINDINGS.md](../customarea/FINDINGS.md) | 9 |
| [studies/skillcast/FINDINGS.md](../skillcast/FINDINGS.md) | 7 |

**These were not scrubbed, and the reason is not effort.** The 33 already done were
incidental citations — a crash the probe caused, a bound quoted in passing. The 65 in
`smsg/FINDINGS.md` are different in kind: that document names twenty GAME_SMSG opcodes,
and its evidence for each name *is* the assert text, quoted so a reader can check the
inference. Its own refutation passes cite the expressions back (`"Every assert quoted
is real, at the quoted line, and genuinely reached"`). Rewriting 65 of those to
"a bound on X at Y:N" is defensible under the ruling and would cost the document
something real: the reader's ability to audit the naming argument without the binary in
front of them.

**RULED 2026-08-12 by the owner, in answer to "are we going too crazy with
provenance?"** — a fair question, and this repo's own record answers it. The
provenance mistakes that have cost something here were **refusals**: `PLAN.md` §7 Q3
lists three, including R4c-2's unit data left unbuilt behind a rule that never forbade
it. Nothing in the record says a disclosure has ever cost anything.

**The ruling: a single assert expression cited as evidence is a MEASUREMENT and is
permitted with its file and line. The refusal targets BULK dumps and decompiled
bodies.** The 104 are permitted. The sweep stops. Two further distinctions came with
it and both narrow the rule:

- **The crash dialog is not extraction.** `Assertion: <expr> / File.cpp(NNN)` is text
  the retail client puts on screen for any player who crashes, and players paste it
  into forums. Treating that identically to a scripted sweep of the PE's string table
  was the original clause's main overreach.
- **Two tiers, not one.** The bytes gate — assets, `Gw.dat` chunks, decompiled bodies
  — is existential, binary, cheap to comply with and impossible to retrofit. Prose
  hygiene is none of those things. Conflating them is what let a low-risk question
  consume a session.

**What is kept.** Nothing of the scrub: all 46 sites are reverted (§4 measures why) and
the test's per-file zero list is gone. What
survives is the cheap half of the original finding: `content.py` enforced this ruling's
permitted side from day one while prose was checked by nobody, and a tripwire with real
headroom closes that for free. `test_provlint.py` now allows `smsg` 80 and an
unlisted document 10, and it was checked in the direction that matters — a 15-row
assert dump appended to `tape/FINDINGS.md` trips it, while `smsg`'s 65 do not.

---

## 7. Reproduce

```bash
python toolkit/provlint.py
```

```bash
python toolkit/test_provlint.py
```
