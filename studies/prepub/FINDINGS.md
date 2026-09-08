# The pre-publication audit: what publishing this repository actually exposes

**2026-09-07.** This is the pass [PLAN.md](../../PLAN.md) §6's credential row asked for on
2026-08-05 — *"a credential-scrubbing / anonymising pass is a gate before any public
push"* — run, and it closes that gate. The ruling it discharges is `PLAN.md` §7 **Q16**.

**Identifiers.** `PREPUB-F<n>` = findings, each with the file and line it was found at.
Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**The headline is a negative, and it is the one worth reading first: the provenance gate
came through clean.** Four independent sweeps aimed at ArenaNet's expression across 5 MB
of prose and 483 modules returned **zero confirmed crossings**. The exposure this audit
found was entirely on the *personal information* axis, and the worst of it was not in the
captures the 2026-08-05 row was written about — it was in the source, which is the half
nobody was looking at.

---

## 1. Method, and what it does not cover

**15 dimensions, 27 agents, adversarially verified.** Each dimension got a finder and a
skeptic; the skeptic was told to re-open every cited file at every cited line, to default
to REFUTED when uncertain, and specifically to refute anything flagging a permitted assert
citation, a measured table carrying its provenance, or a "to be safe" removal — because
this repo has **measured** that its direction of error is over-refusal
([studies/provenance/FINDINGS.md](../provenance/FINDINGS.md); 46 citations rewritten on
2026-08-12 and all 46 reverted). 54 raw findings, 3 refuted outright, the rest confirmed
or severity-corrected. Every finding below was then re-verified by hand against the tree
before it was acted on.

**Coverage, stated honestly:**

* **Tracked files: complete** for the patterns searched (700 files, all of `toolkit/`,
  `studies/`, `content/`, `schema/`, the root documents).
* **History: structurally complete, content-sampled.** Every path ever added was
  enumerated (704, against 700 tracked now) and every blob ranked by size. The 2,645
  commit *messages* were grepped for the personal-information patterns. The 2,645 commit
  *diffs* were pickaxe-searched for named patterns, **not read**. A secret introduced and
  removed under a pattern nobody thought to search for would not have been found.
* **NOT covered:** the vault (gitignored, out of scope by construction), the owner's
  GitHub account settings, and anything outside this repository.

---

## 2. PREPUB-F1 — the credential oracle. **OBSERVED**, and the one that mattered

`toolkit/portal/sessionstore.py:9-14` and `toolkit/authsrv/test_handshake.py:103-105`
pinned two GUIDs as *"the real UUIDs observed on the wire"* — a `user_id` and a game
`token`. **They are not reproduced here, and that is the point of the finding rather than
an omission from it:** this document would otherwise republish the exact thing it exists
to retire, which is how the first draft of it was written and what the sweep in §7 caught
on its own author. Read them out of `git show b9eef520` if you need them; after the
history pass they are gone from there too.

`toolkit/portal/webgate.py:180-181` computes those as `stable_guid("user:" + email)` and
`stable_guid("token:" + email)`, and `stable_guid` at `webgate.py:66-74` is published in
the same repository as `uuid.UUID(sha256(seed).hexdigest()[:32])`. **Running that function
against the owner's real ArenaNet login address reproduces both constants exactly.**

So the pair was a **confirm-a-guess oracle for the account address**: not a disclosure of
the address, but a published way to test a guess at it, with the hash function shipped
alongside. Two things compounded it. The scrubber's own docstring
(`toolkit/scrub_captures.py:23`), restated at `RUNBOOK.md:827`, gave that account's
password length as an exact byte count; and
`studies/review/FINDINGS.md:261` recorded a byte length beside *"a real `…@gmail.com`
login name"*.

**This is the same shape as the finding one row above it in `PLAN.md` §6** — *"the recipe
was the exposure, not the vault"* — arriving a second time, in a different file, and
again not caught by any rule. The 2026-08-05 gate was aimed at `vault/captures/portal/`.
The vault was never the problem: it was gitignored in the first commit and **no vault
file, capture, key, binary or image appears in any of the 2,645 commits** (§7). The
problem was four lines of source.

**Fixed.** `sessionstore.py`'s example pair is regenerated from the synthetic loopback
credential (`accounts.py` SYNTHETIC, `loopback@rurik.invalid`) — the docstring's actual
subject is the `bytes_le` GUID layout, and a synthetic pair demonstrates the byte-swap
exactly as well. `test_handshake.py` now *derives* its constants through
`webgate.stable_guid` from `TEST_EMAIL`, which is the stronger check anyway: a change to
`stable_guid` now moves the test with it instead of silently disagreeing. Both byte
lengths are now non-numeric.

**Residual, and it is not remediable by editing files:** the pinned pair is in the diffs
and one commit message of history. See §8.

---

## 3. PREPUB-F2 — the operator's own character names. **OBSERVED**

Five character names, at eight sites. One is in code — a comment at
`toolkit/clientscan/routerbench.py:36`. The other seven are prose:
`content/items.toml:240`, `studies/newopcodes/FINDINGS.md` ×4,
`studies/quests/FINDINGS.md:686`/`:760`, `studies/combat/PLAN.md:609`, and
`studies/movement/ROUTER.md:89`. One of the five correlates directly with the
`GameJawnsInc` commit identity on 2,641 commits.

**Two of them were hex-encoded and invisible to a name search.**
`studies/quests/FINDINGS.md:548` carried `<the name's first UTF-16 units>…` as a UTF-16 run inside a
quoted payload, and `:1004` carried two more whose *lengths* were the actual evidence
(11 − 8 = 3 = 43 − 40). A tree-wide scan for the literal strings passed both lines clean.
**Whoever audits this next: search the encoded forms, not just the strings.**

This matters because the repo documents, with dates, a live-service capture campaign on a
named secondary account (§3 R0b, §6.2). The character names are the account-side
identifiers that tie those documented sessions to real accounts.

**Fixed.** Every site now carries the identifier the claim actually rests on — the
connection id, the map id, the unit length — which in each case was already present in the
sentence. `content/items.toml` needs only "five distinct characters"; `ROUTER.md:89` needs
"map 146, wire-named"; `:1004`'s check is arithmetic on two lengths. **No count, no claim
and no cross-check changed.** Verified by a tree-wide sweep for both the literal names and
for any `00XX`-shaped UTF-16 run that decodes to text: zero hits.

---

## 4. PREPUB-F3 — other people's names and their typed chat. **OBSERVED**

`studies/chat/FINDINGS.md` named **12 real Guild Wars players** intercepted off-wire from
ArenaNet's live service, four of them paired with the verbatim text those people typed in
public chat. `schema/overrides.json:2935`/`:2923` duplicated a subset into the tracked
wire schema — the file most likely to be vendored downstream. `:2328` carried a real
guild's name and tag; `toolkit/authsrv/authsrv.py:9049` carried a third party's name in a
server source comment.

**The argument for fixing this is the repository's own, and it had already been made.**
`studies/newopcodes/FINDINGS.md:231` rules:

> *Guild names and tags are other players' data. They are on the wire and they are
> plaintext, and that fact is itself a protocol finding worth recording — but a roster of
> real guilds does not need to be in git to make the point.*

That standard was applied at line 231 and **not** at line 624 of the same document, nor in
the chat study, nor in the schema. This is not a new rule; it is an existing rule that was
applied once and then not carried.

**Fixed**, using the remedy that rule already chose: senders keep their **playerId and
connection**, bodies keep their **channel, content class and unit length**, the literal
text stays in `vault/captures/live/`. §3's cross-check needs only that playerId 57
resolves to two *different* names on two connections; §5's channel finding needs
conversation-vs-advert, not the words. `studies/chat/FINDINGS.md` carries a header note
recording the redaction and pointing at the rule.

---

## 5. PREPUB-F4 — the operator's Windows account name. **OBSERVED**

`C:\Users\<name>\…` in four lines across three files (`studies/smsg/FINDINGS.md:1110`,
`studies/animref/HANDOFF-2026-09-02.md:116`,
`studies/movement/followon-notes/a2-campaign-handoff.md:19`/`:80`). The handle is the stem
of the account address in F1, so it published a second identifier beside the commit
identity. All four are dead scratchpad paths whose contents were never retained.

**Fixed** — replaced with `<user>`, the placeholder `toolkit/harness/livesession.py:667`
already uses for the same shape. Complete set; confirmed by `git log -S`.

---

## 6. PREPUB-F5..F7 — the second gate, which is a licence question

**F5. GWCA had no notice. CORROBORATED.** `toolkit/authsrv/agents.py:1185`/`:1255` and
`toolkit/clientscan/genericvalue.py:206` ship constant tables taken from GWCA (MIT,
**attribution required**), marked `UPSTREAM` at the call site. `THIRD-PARTY-NOTICES.md`
had sections for GuildWarsMapBrowser, OpenTyria, Headquarter and Tyria-Extractor — and
none for GWCA, the one upstream whose tables ship *inside* `toolkit/`.

**`derivlint.py` reported the tree clean, and it was a false negative by construction.**
GWCA is not in its `ATTRIBUTION_REQUIRED` set. `CLAUDE.md`'s own line is *"a rule nothing
checks is a wish"*; this is the sequel — **a rule whose checker does not check the thing
you assume it checks is worse than no checker, because it produces a green light.**
Fixed by adding the section; the checker gap is left open deliberately and is the top item
in §9.

**F6. The Guild Wars Wiki had no notice.** 26 `content/` rows carry `source = "wiki"` (22
in `world.toml`, 4 in `maps.toml`). `PLAN.md:1138` classifies GWW as GFDL 1.2 /
CC BY-NC-SA 2.5 — **attribution required, and not permissive**. Fixed by adding the
section.

**F7. The repository had no licence of its own, in any of the 704 paths ever added.** On
publication that is all-rights-reserved by default — which directly contradicts the
README telling a reader to open the checkout and develop in it. Fixed: **MIT**, with a
carve-out naming the 26 wiki rows, whose ShareAlike and NonCommercial arms travel with
them. Per-row provenance is what makes that carve-out enforceable rather than a
disclaimer: the affected set is 26 identified rows, not "some of the content".

---

## 7. What was NOT found, and these negatives are the load-bearing half

**The provenance gate holds.** Four sweeps specifically hunting ArenaNet's expression:

| Sweep | Result |
|---|---|
| The four mega-documents (`movecode`, `movement`, `customarea`, `skills` — 2.1 MB) | **0 findings** |
| `studies/` arcs N–Z, including every asset-adjacent arc | **0 findings** |
| Derived-data provenance completeness (`content/`, `schema/`, hardcoded tables) | **0 findings** |
| Verbatim authored text | 1 finding, **refuted** |

No asset bytes, no `Gw.dat` chunk payloads, no textures, no audio, no model data, no
decompiled function bodies, no bulk assert dumps. `provlint.py` counts 474 assert
citations across 63 files and every one is a single assert carrying a claim — the
permitted form under §7 Q3 as refined 2026-08-12. **This is the first independent
confirmation that the MEASUREMENT/EXPRESSION boundary is holding in the tree and not just
in the rule.**

**The vault never leaked, and now that is measured rather than asserted.** Across all
2,645 commits, **704 paths were ever added** (against 700 tracked now — the four deletions
are `TESTS.md.old`, `clientpatch/buildid.py` and two `movehook/_lane_*.py`). Not one is a
vault file, capture, key, `.dat`, `.exe`, image or binary. The largest blob in the entire
history is `authsrv.py`. `.gitignore` held from the first commit exactly as
`scrub_captures.py`'s docstring claims.

**Nothing hides off `main`.** Three branches, all fully merged; zero tags; zero pull
requests; zero issues. Publishing `main` publishes exactly the tree and history audited
here.

**One judgment call left open, deliberately — ~~and it is the owner's to rule~~ RULED
2026-09-08.** `content/maps.toml` carries ~10 literal place names (`"Ascalon City"`),
which sits slightly across `CLAUDE.md`'s *"commit the id, resolve the string at run
time"* bullet. Published place names are the mildest possible case of that rule and the
surrounding prose uses them freely. **Recommendation: a one-line ruling scoping that
bullet to authored *bodies* of text — descriptions, dialogue, item names — rather than a
conversion.**

> **The owner ruled exactly that** (`PLAN.md` §7 **Q17**): the bullet is about authored
> bodies of text, a short proper noun used as a label is not one, and the names stay.
> `CLAUDE.md`'s bullet now carries the scope and no longer opens with the word *Names*,
> which was the word doing the over-reaching. Nothing in `toolkit/` changed — nothing
> ever enforced this in code, which is why it could sit unnoticed until a pass went
> looking. Worth recording that this is the over-refusal pattern §7 Q3 is scarred by,
> caught one step earlier: flagged as a question rather than actioned as a conversion.

---

## 8. What publication makes permanent, and what this pass did NOT do

**This pass edited the working tree. It did not rewrite history, and history goes public
in full.**

* **F1's pinned GUIDs remain in the diffs and in one commit message** (`b9eef520`). The
  oracle is therefore still recoverable from `git log` by anyone who looks, even though
  the files are fixed. **This is the only finding whose remediation is incomplete.**
* **F2's, F3's and F4's redacted strings remain in the blobs** of the commits that
  introduced them.
* **The author identity — a real name and a personal address — is on 2,641 of 2,645
  commits.** This is normal git metadata, not a defect, but it is the one item that
  becomes *unchangeable* at the moment of publication.

**The window for rewriting any of that closes on the first public push, and only then.**
`git filter-repo` before publishing is cheap; after publishing it is worthless, because
the old objects are already cloned, cached and archived. That is a decision for the owner
and it is deliberately not taken here. **If the answer is "accept it", record it as a
ruling** — an accepted risk that is written down is a decision, and one that is not is
just a thing nobody looked at.

**Addendum 2026-09-08 — the rewrite ran, and the three bullets above are discharged.**
Owner's decision, 2026-09-07: rewrite, not accept. Two `git filter-repo` passes, run by the
owner on the local machine before the first public push, verified by a local session
against this machine's history rather than the remote's view of it (the local checkout
was 19 commits ahead of `origin/main` when the handoff arrived; they were merged and
pushed first, so the rewrite covered them).

* **Identity.** `--mailmap`: all 2,680 commits now carry the id-prefixed GitHub noreply
  address. The remote draft used the bare `<login>@users.noreply` form, which GitHub
  only honours for accounts created before July 2017; this account dates from 2023, so
  that form would have dropped the attribution the mailmap existed to keep. Confirmed
  after the push through the API: tip and root commit both resolve to the account.
* **Strings.** `--replace-text` and `--replace-message`, 28 entries: F1's two GUIDs in
  their dashed and `bytes_le` forms → the synthetic loopback pair the tree already uses
  (so the message at `b9eef520` now carries the synthetic pair, not the real one); the
  password length; F4's account path; F2's five character names; F3's twelve players,
  two guild names and the tag; and three entries the remote draft's list did not have —
  **the two UTF-16 spaced runs §3 itself warned about** ("search the encoded forms, not
  just the strings": the list that was written from that finding still missed them), and
  the 14-byte phrase from `studies/review/FINDINGS.md`. One literal was three letters and
  as a bare substring would have rewritten "Cluster" in 110 historical blobs; it went in
  as a word-bounded regex.
* **This document.** §3 quoted the first four UTF-16 units of one run as its evidence,
  which is the §7 slip a second time in the same file; a second one-entry pass replaced
  it, in history and in the tree, with the placeholder now at that line.
* **Verification.** Before the rewrite: the replace list was simulated over every blob
  (6,437) and commit message (2,686) on this machine, searching the result for every
  alternate form — other case, dashless and braced GUIDs, UTF-16 and ASCII hex,
  underscored and squashed names, forward-slash paths — plus in-word collateral; that
  simulation is what found the three missing entries and the collateral. After: a pickaxe
  census of every literal across all refs, then the same scan restricted to what local
  branches and tags reach, immediately before the push. Zero residual. 536 commit
  citations across 105 files (`.md`, `.py`, `.toml` — the draft covered `.md` only) were
  re-stamped through filter-repo's commit map in `f85a926e`; the diff is hash-only.
* **What stays, and what a force-push does NOT do.** The pre-rewrite bundle and both
  commit maps sit in `vault/backup/`, local like everything else there. The repository
  was private for the whole of its history until this point, so no clone of the old
  objects exists outside this machine. **But the force-push did not remove them from
  GitHub.** The public commits endpoint refused the old tip afterwards, which is the
  check the first draft of this addendum relied on; the git-database endpoint
  (`/git/commits/<sha>`, `/git/blobs/<sha>`) still served every old commit tried —
  including the one whose message carries the real GUID, with the real address in its
  author field — and the old `sessionstore.py` blob with both credential GUIDs, to
  anyone holding a SHA. GitHub's web UI renders such commits too. The documented
  remedies are a support ticket or waiting for GitHub's own collection; with zero forks,
  issues, pull requests, releases, keys and hooks there was nothing to lose, so
  **the remote repository was deleted and re-created private from the rewritten
  history on 2026-09-08 03:36Z**, main pushed as the only ref, and every old commit
  and blob SHA verified to return 404 before the visibility change. A re-created
  repository is the only state a force-push can be *shown* to have reached.
* **Three traps for the next pass.** The force-push one is above. GitHub Desktop auto-fetches every few minutes and
  dragged the entire old history back into the local object store between the rewrite
  and the push; a scan over all objects would have reported it as residual. Verify over
  `--branches --tags`, close Desktop, and prune after the push. And the classifier that
  guards an automated session blocks every invocation of filter-repo, including
  `--version`: the command has to be handed to the owner verbatim.

---

## 9. The standing weakness this pass leaves behind

**Enforcement of both gates is habit, and habit does not survive a public repository.**
There is no pre-commit hook, no `core.hooksPath`, no `.githooks/`, and no `.github/` at
all, so no CI. Every checker in this tree — `provlint`, `derivlint`, `citelint`,
`srclint`, `content.py` — runs only when a person remembers to run it. Once the repo is
public and takes contributions, "a rule nothing checks is a wish" stops being a slogan
about this project's own past and becomes a live exposure with strangers attached to it.

Three follow-ups, in the order I would do them:

1. ~~**`derivlint` misses attribution-required upstreams that are not in its list** (F5).
   Add both GWCA slugs and `gwdevhub/GWToolboxpp`; require a notice match to be a `## `
   heading rather than any substring; drop the bare-word alias `server`, which is why
   `gw-preservation/server` matches 194 modules and tells you nothing.~~ **LANDED
   2026-09-08**, all three, and the middle one was worse than this row knew. The
   substring rule did not merely admit weak evidence: `THIRD-PARTY-NOTICES.md` ends
   with a section naming the upstreams this repository deliberately does NOT credit,
   and one line of it -- *"`gw-preservation/*` and `Py4GW_Reforged` carry no licence
   at all"* -- was enough to score **both Py4GW slugs `notice: yes`**. The checker was
   reading a disclaimer as an attribution. A notice is now a `## ` SECTION HEADING,
   `GWToolbox++` is registered as an alias so the GWCA heading can credit the project
   by the name it actually uses, and the three GWCA-family slugs are in
   `ATTRIBUTION_REQUIRED`. Dropping the bare `server` alias took that row from **195
   modules to 1** -- it had been measuring the English language, in a repository that
   is a server -- and the one real citation is `content.py:76`, where the slug is
   written inside the table that REFUSES it, so it earned a `NO_DERIVATION` row.
   Tightening also exposed that the register spells that source `gw-preservation`
   without the repo name, so its old `6.1: yes` had been the word `server` matching
   too. `test_derivlint.py` 32 checks, floor 30; the disclaimer case is rebuilt
   against a synthetic root and both arms move.
2. ~~**A `.githooks/pre-commit` that refuses staged vault-shaped paths** regardless of
   location, plus one line in `RUNBOOK.md` to install it.~~ **LANDED 2026-09-08**
   (`toolkit/githooks/pre_commit.py`, `toolkit/test_precommit.py`, 76 checks; install
   per clone with `git config core.hooksPath .githooks`). The gap was demonstrated
   before it was closed: a root-level `authsrv-<stamp>-c1.jsonl` staged cleanly,
   ignored by nothing. It refuses the content shapes this pass found BY HAND too --
   a real-looking address against a synthetic allowlist, a Windows profile path
   naming a real account (F4), and §3's UTF-16-inside-a-hex-dump, the form that
   defeated a tree-wide string search. Its fixtures are assembled at run time rather
   than written out, because its own sweep reads every tracked text file: the first
   draft embedded a real credential GUID and an encoded name fragment, hours after
   the rewrite removed both, in the one file whose job is keeping them out. The `.gitignore` belt is aimed
   at extensions that do not exist in this project (`*.gwcap` appears nowhere else in the
   tree) while the formats that *do* exist — `authsrv-*.jsonl`, `*.raw`, `hold*.png` —
   are covered only by their directory.
3. ~~**Three capture tools default their output path into the checkout rather than the
   vault** (`wirecapture.py --out`, `authsrv.py --vault`, `drive_client.py --outdir`).
   `shotlabel.py:152 resolve_out` already implements the correct refusal — it walks the
   `.git` gitfile so it catches worktrees too — and three other modules already use it.
   Route these three through it.~~ **LANDED 2026-09-08.** The guard MOVED rather than
   being called across a package boundary: it now lives in `toolkit/vaultpath.py`, the
   module all three already import to find the vault, and `shotlabel` delegates to it
   with its own noun — the shape `modelexport` and `unitexport` already use for
   `mapexport.resolve_outdir`, and the rule `refindex.py:161` states outright: the
   write guard is IMPORTED, not re-typed. Each tool resolves its path BEFORE doing
   anything expensive — before the sniffer starts, before the client launches, before
   `authsrv` opens a socket — so a bad path costs nothing instead of being discovered
   after a run that cannot be redone. `vaultpath` had no test at all before this;
   `test_vaultpath.py` is 24 checks and asserts by AST that all three tools really
   call it, since a guard nothing calls is the same as no guard.

None of these is a disclosure today. All three are the mechanism by which one becomes
possible on a repository other people can now push to.
