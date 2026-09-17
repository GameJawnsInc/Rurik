# PLAN.md §8 split, and the open-item sweep behind the new §8 (2026-09-17)

**What this is.** On 2026-09-17 `PLAN.md` §8's 226 entries moved byte for byte to
[PLAN-LOG.md](../../PLAN-LOG.md), and §8 became a short list of what is open. This
document is the record of how that list was seeded, every candidate the sweep produced,
and — the part worth keeping — how wrong the sweep was and in which direction.

Labels are the house vocabulary ([studies/character/FINDINGS.md](../character/FINDINGS.md)).
Nothing here is a fact about the client; every row is a claim about our own documents.

## 1. The measurement that started it — OBSERVED

`PLAN.md` at `01639d69`: 1,402,484 bytes, 12,110 lines. By section: §8 1,113 KB (79 %),
§3 145 KB, §6 and §7 49 KB each, §1–§2 and §4–§5 together 33 KB. §8 held 226 `###`
entries, 71 dated August and 164 September (some carry two dates), newest first, and the
newest read "RAN AND SCORED … nothing ships" — a changelog of closed work under the
heading "Immediate next actions". `PLAN.md` had taken 261 commits since 2026-09-01,
nearly all of them a prepend at the same line.

The cost was not disk. `CLAUDE.md` tells every session to read `PLAN.md`; the `Read` tool
stops at 2,000 lines and says nothing; so a cold session got the newest sixth of the
file and took it for the file — the stale-tree failure `CLAUDE.md` already describes, in
a document instead of a checkout.

## 2. The move — OBSERVED, and refutable

Everything from the first `### ` under `## 8.` to the end of the file went to
`PLAN-LOG.md` under a short header. The script asserted, before writing anything, that
the heading is unique, that no H2 follows §8, that §8 had no preamble, and that
`kept + moved` reassembles the original byte for byte. Moved: 1,123,668 bytes, sha256
`baf5cd3d0eb2cae9…`, 226 entries. `git show 01639d69:PLAN.md` is the other half of that
check for anyone who wants to repeat it.

What had to follow the text, each found by a lint going red rather than by foresight:

* `test_provlint.py` — 21 of `PLAN.md`'s 23 assert citations moved, so the grandfathered
  ceiling moved with them (tree total 488 before and after).
* `test_seclint.py` — the known `8.0` heading collision is the log's now; STALE and NEW
  both fired on the rename.
* `identlint.ROOT_DOCS` — without the log the site count fell 1107 → 1106 and
  `whichrung.py` stopped resolving into the entries.
* `test_checks.py` — `PLAN-LOG.md` joined the link-checked documents, and §8 got a byte
  ceiling (40,000) with a vacuity floor and a synthetic control. The placeholder body
  used mid-split reddened the floor, and the pre-split file measures 1,113,422 against
  the ceiling, so both directions have been seen red.

Seventy-four "`PLAN.md` §8" citations across `studies/`, `TESTS.md` and code comments
were **not** re-pointed, on purpose: the log's header and §8's own preamble say that a
citation dated before 2026-09-17 resolves in the log, commit messages cannot be edited
at all, and `CLAUDE.md` records what the last mass re-point in this repo cost.

## 3. The sweep — method

Eight Sonnet agents, one byte-balanced slice of the log each (~140 KB), pinned to the
worktree and made to prove it. Each was asked for what every entry *itself* leaves open
(a quoted trigger phrase required), then to search the whole log, `PLAN.md` and the
cited study for a later closure, and to call an item closed only with a line to point
at. Judgement stayed with the orchestrating session, which checked a sample against
the code and the studies before anything reached §8.

## 4. What the sweep got wrong — OBSERVED, n = 10, and the reason §8 is short

Ten older candidates the agents returned as open were checked against the code, the
suite or the study's own text. **Three were closed, with no log line saying so:**

* `ENEMY_SKILL_FRACTION = 0.25` "still an invention" — gone; `test_skilldamage.py` and
  `test_agentlife.py` both describe its replacement.
* `INTERACT_RANGE = 250.0` "admitted-invented" — it is 144.0 with a WIKI citation and
  the owner's "probably 2x" beside it.
* "`test_guards` §8 is red on main" — 45 of 45 green.

Seven held (`EFFECT_TYPES` still five; `RUN-R8.md` still headed NOT RUN; skills §34.10
"Neither has run"; MORALE-Q5/Q6 still in the study's open table; crossbuild's three
residuals; NPCTRACK-Q3; smsgsweep §7.5). And several more are closed on the face of it
to anyone who has read September — "conditions, hexes and enchantments are unmodelled",
"energy is not enforced", "the c2s hero direction is NOT FOUND", "no reward is GRANTED"
— which the agents could not see, because the closing entries do not name the old item.

**So the direction of error is over-reporting, it grows with the age of the entry, and
the mechanism is that this project closes things by shipping them, not by writing
"closes X".** A grep for a closure is a one-directional guard: it can clear an item and
can never convict one. §8 therefore lists an item only if it is from September's arcs
or if something *current* still says it is open. One correction ran the other way: §3's
R-ISLE row still calls rung 8d open while skills §49.7 closes its question, and an
agent trusted the row.

## 5. The candidates — UNVERIFIED unless §8 lists them

One bullet per candidate with no closure found; "log N" is the entry's heading line in
`PLAN-LOG.md` as of the split. *(unsure)* marks the agent's own doubt. Candidates the
agents closed with a citation are not listed — some eighty of them, most from the
movement arc, where each entry's NEXT is the following entry's subject.

### 5.1 September (log 30–605)

* log 55 — movement speed's decrease arm has no snare content row.
* log 67 — the RA tape's Mind Burn pair reads non-integer points; scoped out, not chased.
* log 82 — no content row uses `passive` / `group`; five retail definitions named.
* log 40 — one Javelin for 45, n = 1, unexplained.
* log 40 — the Frenzy arm UNSEPARATED; both orderings fit four hits.
* log 35 — Weakness: heroes and bodies get the arithmetic and no wire.
* log 162 — retail's reply to `0x005E` unobserved; `0x0065`, `0x001B` unmodelled *(unsure)*.
* log 207 — the `GmDeckBuilder` set-picking flag unread.
* log 207 — nothing writes either skill list: trainers, tomes, capture signets.
* log 150 — the settings blob's `5a`–`5e` groups as an appearance record: a guess.
* log 283 — map 888 on a 38888 client (arm A) never loaded.
* log 243 — model viewer: lazy thumbnails, Maps tab first-open cost, reverse index.
* log 272 — manifest hash function, `0x0196` body, the 5-of-17 request.
* log 231 — which arenas carry no death penalty, UNREAD (the study says nothing to model).
* log 231 — ZERODRAW with a Deep Wound on the foe, not run.
* log 316 — Mend Condition (275) not modelled.
* log 312 — `pathrec.py`, `movetap.py`, `compositetrap.py` deliberately not split out.
* log 267 — shrines and gadgets as server-created agents: an arc, not built.
* log 326 — a `datplan` check of the corner's mesh lip, only if the defect recurs.
* log 330 — leg B's mirror diverges 514 u; an undecoded client rule, a `codescan` question.
* log 342 — do retail's `0x002A` follow points advance along a wall before the next
  report? Registered, no run.
* log 342 — RUN-1zDB's P4: the owner's answer was "i don't remember"; dead, not open.
* log 356, 368 — two hostiles park in one body; nothing ships, a lever for the owner's eye.
* log 358 — a live witness of a headless Pre-Searing character taking a spell *(unsure)*.
* log 364 — the w0-route corridor share "registered to shrink"; never re-measured *(unsure)*.
* log 372 — 39 % of refused-lag accrued with the copy parked under a steering re-report.
* log 390 — two bad chords named, not tuned away *(unsure)*.
* log 392 — §1z-cl's plane-words fix unchecked by a run *(unsure)*.
* log 398 — a separation re-pin, not shipped *(unsure)*.
* log 400 — the guard's 2.7 s late-sweep branch CONTESTED, for a hook read.
* log 406, 410 — two snaps left; retail's leads cross plane seams 144 of 3,151 *(unsure)*.
* log 461 — NPCTRACK Q3 needs a wedge run with the tape; Q8 an observation.
* log 438 — 13 of 35 model-leg residuals: props or coarse trapezoids, UNVERIFIED.
* log 517 — the dropped-click / silent-client hole.
* log 538 — a real `D1_LEAD` default: its own arc, if wanted.
* log 557 — RUN-1zBS never ran; moot since the waiver was deleted.

### 5.2 Early September, the lead arc (log 606–1680)

* log 606 — `leadtap.align` finds no anchors on a lead-off capture.
* log 630 — why the report freezes at the far side of the 29→0 seam; and whether it
  happens on the lead-OFF default.
* log 640 — a movehook tape at the setter's avoidance exit; four offsets read live.
* log 679 — nine owed one-sentence documentation fixes from the review.
* log 699 — `gate1-red` still lands on a walking body ("named as debt"); the client's
  true gate-2 tolerance (≥ 32 u, n = 1).
* log 707 — the guard must not re-pin onto a walking keyboard body it cannot restart.
* log 716 — a lead through a portal must carry the destination's plane; why run 2's
  copy left the ray after 105 u.
* log 729 — why the client refuses a file-linked portal along a straight ray.
* log 843 — the client's send-only `0x0047` sender, never located.
* log 891, 902 — the bent-path cell, n = 0 observed.
* log 947 — `movetap` fails its own rate floor under the harness.
* log 1671 — ANIMREF's desk queue: §19 per-bar adrenaline with cross-drain, §15's
  movement-start gate, §16's visual ids' appearance.

### 5.3 Late August, movement and the desk arcs (log 1681–3634)

* log 1681 — §7 Q14, the plane repair's default-ON ruling (confirmed open in §7).
* log 1681 — RUN-R8 pre-registered, never run (confirmed: the sheet says NOT RUN).
* log 1681 — silent-lock case; NPC planes; ZERO LEAD's field-4 carry word.
* log 1681 — keyboard channel, mesh fattening, the third carve source, retail's
  waypoint vocabulary.
* log 2137 — glide or jump, NOT SETTLED *(unsure)*.
* log 2286 — two hook sites to name the caller of two missed `SetPosition` warps.
* log 2354 — is the gateless reseed route wire-reachable; mesh specimen C not found.
* log 3634 — heading-rate's cost not separated from the geometry refusals'.
* log 1681 — tag 13 and `PathApi:753/754`; 14 of 92 prop collision sub-meshes unmerged.
* log 2588 — `test_pathchunk`'s `--all` constants have no 38833 value.
* log 2636 — is playercomposite §9.8's leggings reading contaminated.
* log 2717 — nothing in `MsCliMan` reads `+0x134`; `TAPE-TRANSFER-PORT`; 79 of 103 sweep
  candidates never verified.

### 5.4 August, skills, morale and authored places (log 3635–5673)

* log 4236 — Ignite Arrows' adjacency splash, a named gap.
* log 4284 — a caged acceptance run for CASTMECH (free spell, queued spell, attack skill).
* log 4284 — `test_guards` §8 red on main — **REFUTED here, §4: green.**
* log 4284 — R-ISLE rung 8d — **see §4: skills §49.7 closes its question; §3's row is stale.**
* log 4344 — the sub-1 % adrenaline boundary and the gate rule: two staged captures,
  neither run (confirmed, skills §34.10).
* log 4344 — reason ids for the 1934–1993 block; the cast-animation duration NOT FOUND;
  `GmSkSlot`'s refresh UNVERIFIED; `EFFECT_TYPES` still five (confirmed in code).
* log 4712 — MORALE-Q5, Q6 (confirmed in the study's table); a GIF-rate capture of a
  killing blow's number.
* log 4857 — narrow-gate clearance, water and shore, slope materials, a created map's
  minimap; top byte 3+ untested; strict or non-strict at the 45° boundary.
* log 5297 — the glyph's discount watched draining on screen *(unsure)*.
* log 5562 — SL uses level 20 *(unsure — the code now takes the level)*; the
  unmet-requirement term unmodelled (confirmed in a code comment); `--practice-target`
  does two jobs.

### 5.5 August, items, opcodes and the PvP-UI arc (log 5674–7001)

* log 5674 — hero AI policy waits on the substrate's row shape.
* log 5706 — `equipped_attribute_bonuses()` reads content instead of decoding `modifiers`;
  542 cannot be composed; 34 of 157 identifiers extract no text id.
* log 5863 — purchases do not persist and stock is infinite; `0x0038` and whether
  attribute points are owner-private.
* log 5960 — REALFIX-Q5; the composite's non-movement costs; the 0.039 replication.
* log 6279 — `0x0060`, `0x008D`, `0x00B0` unnamed or without a consumer.
* log 6343 — what reads `+0x10C`; per-NPC-type weapon rows; heroes §21.2; `0x006E` and
  the hands; property 66; property 30; `0x00B9` field 2; secondary profession selection;
  ten `name: null` rows and `0x0092`'s cap (**reframed since**: `0x0092` acknowledges
  manifest hashes, divergence D13).
* log 6546 — hiring NOT FOUND; no server arm for the attribute triple; `0x0093`'s retail
  usage unobserved.

### 5.6 August, models, archive, quests, heroes (log 7002–8764)

* log 7002 — FA1 header bytes `+0x09..+0x0B`; the shell texture's alpha meaning.
* log 7115 — rung A5 never run; gap A (`symbol_count == 1`); A1b; A9 and A10 archives
  "LEFT DEPLOYED" *(unsure — nothing records the revert)*.
* log 7605 — `INTERACT_RANGE` — **REFUTED here, §4: now 144.0.** Giver binding by
  connection agent id; Q6 across a portal; the reward GRANT (**closed on the face of it**:
  the MANTID run scored a grant).
* log 7801, 8018 — `0x0074`'s other 17 fields; `0x01BF`; follow AI; hero skill-bar
  delivery and the c2s direction NOT FOUND (**closed on the face of it**: RUN-HEROLIB
  observed `0x005C` and `0x000F`); retail's send order.
* log 8156 — `--probe cast_anim` unrun; conditions, hexes, enchantments, energy and
  damage timing (**all closed on the face of it** by the effect substrate, the energy
  entry and CASTMECH).
* log 8279, 8209 — minimap tier 3 (A1, A2); the C1 run's two caveats *(unsure)*.
* log 8401 — 132 skill icons undrawn; `0x003C` with more than one player *(unsure)*;
  skill descriptions; `s_skill +0x44` scaling (**REFUTED here, §4**).
* log 8572 — terrain's four named-not-understood fields; the lightmap's on-screen
  consumer; Blender's lightmap colour space.

### 5.7 Mid-August, the oldest entries (log 8765–10276)

* log 8766 — 37 of 68 build-coupled addresses outstanding *(unsure)*; `SIG_KEYS`' three
  implementations disagree.
* log 8898 — the account-posture call (confirmed unmade, crossbuild).
* log 9208 — `0x002E` has a builder and no send site.
* log 9228 — 3 of 34 CHANGED screens read; `0x0191` has no usable run (confirmed).
* log 9258 — eight named opcodes retail sends continuously and we never send.
* log 9597–9622 — a capture-to-row compiler; R4a's shrine and spawn table (confirmed in
  §3); the Pre-Searing manifest's upkeep; OpenTyria build, devalued; Probe 3 with no
  date (§7 Q2); the C# core, overtaken by events and never ruled *(unsure)*.
* log 9633–9702 — which of polygon, trapezoid and DAG the client reads *(unsure)*; a
  plane whose prop is its surface, z measured; prop indices between 0 and 67.
* log 9856 — allocator pressure and a compressor (confirmed, crossbuild).
* log 9917–10057 — props tag-4/6 `value` words and the tag walk; four prop-placement
  residuals; the roles of 15 and 30; environment tags 0, 4 and 7.
* log 10224, 10272 — maprows option C, planned and deliberately deferred; 296 rows
  limited by information.

## 6. What would make this list trustworthy

Not another sweep. The over-report comes from closures that never name what they close,
so the repair is at the write side: when an entry goes into the log, take the §8 line
out in the same commit — which is now the rule, and `test_checks.py` holds the size that
makes ignoring it visible. For the rows above, the cheap honest move is per arc: whoever
next opens an arc's study reads its rows here against the code and strikes what shipped.
