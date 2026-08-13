# Recon — what this project has not explored, 2026-08-13

A survey arc, not a rung. It answers one question: **after nine days and 53 test files,
which parts of the game, the archive, the protocol and our own codebase has nobody
looked at?** — and then digs into the best answers far enough to say whether they are
worth doing.

**Method.** Two workflows, 19 agents, all read-only, no client launched. Phase 1 was
eight independent censuses, each searching a *different way* (client subsystems, archive
file types, protocol surface, game systems from the player's side, the project's own
stated unknowns, toolkit code coverage, prior-art mirrors, the capture corpus), then a
ranking pass that re-ran the load-bearing numbers itself. Phase 2 was ten recon digs on
the winners, then a brief. 108 raw gaps in, one ranked map out. Every number below
carries how it was obtained.

**READ THIS BEFORE ACTING ON ANY "ABSENT" CLAIM.** The digs ran against this worktree at
`392df23`, which was level with `main` when the session opened. `main` advanced **16
commits during the session** (HEAD `305a1a5`, *"Merge: text viability, and the party pair
that unblocks the abbreviation"*). Every claim of the form *"nothing does X"* therefore
carries a timestamp. The load-bearing ones were **re-verified against `main` by hand**
after the digs returned and are marked ✔MAIN; the rest are as-of `392df23`.

---

## 1. The headline

Two findings, and they are the same finding from opposite sides.

**(a) The instruments are not pointed at anything.** Five of eight censuses converged on
this independently. The map arc closed 349/349 byte-identical on **0.394% of the archive's
rows and 10.63% of its bytes** — while the largest population in `Gw.dat`, **64,260 `ffna`
type-2 model rows at 24.05% of stored bytes**, had no decoder and, it turned out, did not
need one written: `archive.ffna_chunks` already walks all 64,260 with **zero failures**
and nobody knew. The pattern repeats at every scale, and it is always the same shape —
a finished, tested instrument with no consumer.

**(b) The readouts are weaker than their green counts.** A sabotage sweep patching one
module-level constant at a time found **11 of 15 deliberately wrong constants pass with
`ALL CHECKS PASSED`**, including six GAME_SMSG opcodes carrying every agent movement
message the server sends. A documented sensitivity result is *unreachable in a routine
run* because a vault cache never invalidates on code change. And nine client runs
executed 2026-08-12 were never scored, leaving four opcodes ledgered as crashing when
three independent checks say they do not.

**The consequence for what to do next.** The cheapest work available is not new
capability. It is **repairing readouts and reading evidence already on disk**: one line
in `cmsgstream.py`, one field in `maprows._stamp`, eight literals in `test_agentlife.py`,
ten lines in `msgmix.py`, and re-scoring runs that already ran. Each is minutes, and each
un-blinds a measurement the project is currently making wrongly.

---

## 2. Instruments built, never used

Every row measured this session. OBSERVED unless noted.

| Instrument | State | Ever used |
|---|---|---|
| `archive.ffna_chunks` on models | walks **64,260 of 64,260** model rows, 0 failures | never run on them before this session |
| `npcdefs.py` | 126/126 byte-identical, in the suite, 3 sabotages | `--emit` never run; `vault/content/` does not exist |
| `pathmap.route` | tested A\* | **0 call sites in the server** |
| AUTH channel decode | frames to residual **0 on 8 of 8** connection-directions | **0 of 96 AUTH opcodes named** — one line blocks it ✔MAIN |
| 117 crash dialogs | 72 assert sites, 33 modules | **0 of 334** sweep-ledger rows carry a location |
| `msgmix.py` (ranks what to build next) | reads **6 of 306** sessions, **0 of the c2s direction** | ✔MAIN — `[-6:]` at `:87`, `kind != "sent"` at `:99` |
| `vault/dat_durability` | complete, armed, byte-verified experiment | documented **nowhere**; `studies/datwrite/FINDINGS.md:1455` says it is unrun |
| `content.py` `client-table` provenance path | written, enforced, tested | **zero rows** in `content/` have ever used it ✔MAIN |

**The pattern is worth naming, because it will recur.** This project's failure mode is not
building the wrong thing — the instruments are good, and several are better than their
authors recorded. It is that **finishing a tool and using it are separate acts**, and only
the first one has a test.

---

## 3. The archive, completely censused

Full MFT sweep, 177,341 rows / 4,113,227,787 stored bytes, 58.7 s, **0 decode errors**.
Method matters: a census that decompresses every row unconditionally returns **48,072**
type-2 rows, because **38,633 rows are STORED** and yield garbage. Honouring
`entry.compression` the way `Archive.read()` does gives the true histogram. (The ranking
agent got this wrong on its first pass and corrected itself — recorded here so the next
sweep does not repeat it.)

| Class | Rows | % rows | % bytes | Decoder |
|---|---:|---:|---:|---|
| **ffna2 — models** | **64,260** | 36.235% | **24.05%** | container ✔, geometry ✘ |
| ATEX — textures | 52,274 | 29.477% | 27.42% | container walk only |
| MPEG | 30,712 | 17.318% | 31.63% | NONE |
| ffna8 — sound descriptors | 24,426 | 13.773% | 0.04% | NONE |
| OTHER | 1,690 | 0.953% | 3.30% | `textrec` subset |
| ATTX | 1,648 | 0.929% | 1.80% | **`atex.parse` raises on 118 of 118** |
| AMAT | 1,043 | 0.588% | 0.01% | NONE |
| **ffna3 — maps** | **698** | **0.394%** | **10.63%** | **FULLY DECODED** |
| AMP / DDS / ID3 / ZERO / AMET / ffna4 | 590 | 0.333% | 1.11% | NONE |

**Models: a model is exactly three MFT rows, and the count closes to the row.**
21,420 × 3 = 64,260, **0 orphans, 0 unreachable**. 20,303 chains are length 3, 724 carry
one ATEX, 393 carry two — and 724×1 + 393×2 = 1,510 reproduces the archive-wide stream
histogram term for term. **Ten chunk-id pairs are exact bi-implications per model** over
21,420 models (214,200 tests, 0 violations), two of them crossing MFT rows, so it is a
property of the model rather than of a row. Sub-typing is real and measurable: labelled
by whether any map's Dependencies chunk names the row, **9,132 of 21,420 (42.6%) are
map-declared, and 0 of the 5,572 sequence-carrying, 0 of the 1,117 self-textured and
0 of the 759 geometry-less models are** — against random expectations of 2,376 / 644 / 324.
The container is not map-specific: it is ArenaNet's generic RIFF service with a 5-byte
header, which is new to this repo.

**Verdict: bank the container map, do NOT open geometry.** The server never decodes a
model and never will — `agents.py` sends ids and the client loads geometry from its own
archive. Geometry buys prop collision, retiring borrowed NPC ids, and authored props;
it is a terrain-sized arc, and there is **no `PLAN.md` §6.1 row covering model geometry**
for the upstream that would be leaned on. File the §6.1 row now while it costs one table
row, and write `mdlfile.py` for the container and the fully-decoded `0xFAC` chunk only —
with a mutual-refusal control, since maps and models share the `ffna` container and the
failure otherwise is a plausible desync rather than an error.

---

## 4. The suite's blind spots

**11 of 15 single-constant sabotages survive green.** Method: patch one module-level
constant by AST node, verify the edit applied (0 of 15 failed to apply), run that
constant's own tests. `test_agentlife.py` printed `ALL CHECKS PASSED (189 checks)` under
eight different sabotages, six of them GAME_SMSG opcode numbers —
`AGENT_MOVE_TO_POINT 0x0029→0x002A`, `AGENT_UPDATE_STATUS 0x00F1→0x00F0`,
`AGENT_UPDATE_SPEED`, `AGENT_UPDATE_ROTATION`, `SKILL_ACTIVATED`,
`AGENT_PROPERTY_UPDATE_INT_TARGET`.

The mechanism is exactly the shape `CLAUDE.md` already records from 2026-08-11: the file
references **9 opcode symbols and pins exactly one** to a hex literal — and that one
symbol is the only opcode absent from the survivor list. ✔MAIN: still 1 of 9.

**A documented check is silently disarmed.** `CLAUDE.md` records for `test_maprows` that
*"CELL_PITCH was set to 64.0 — six go red"*. True on a **cold** cache (554–557 s per arm:
96.0 → exit 0 / 23 checks; 64.0 → exit 1 / exactly six red). **Warm — the way anyone
actually runs it, 9.6 s — 96.0000001, 96.001, 96.01, 96.1, 96.5, 97.0, 100.0, 112.0,
64.0 and 48.0 all exit 0 with `ALL CHECKS PASSED`.** Root cause is a one-field asymmetry
between two caches in the same repo: `maprows._stamp` returns `{dat, size, mtime}` with
no code-version field, while `mapchunks.archive_stamp` already carries `format:
CACHE_FORMAT`. `CELL_PITCH` is consumed *upstream* of the cache write, and only `--all`
drops the cache. ✔MAIN — `_stamp` still has three fields.

**A third of the corpus is never swept.** Every sampled map test uses a deterministic
stride, so the union of all ten default samples is **116 of 349 map heads (33.2%)**; the
same 233 maps are never seen, and **neither the smallest (row 46196, 1,368 B) nor the
largest (row 131910, 3,088,128 B) is in any default sample**.

**A free second witness is unused.** The 2026-04-30 client snapshot's `Gw.dat` holds the
**same 349 map pairs at identical row indices with identical sizes, 349/349** — and three
map tests pass against it today. `test_mapfile` refuses it on an entry-count gate citing
*"file ids travel, row indices do not"*, which this measurement contradicts for this pair
of builds. Every "349 of 349" claim in the repo could gain a second witness for free.

---

## 5. What the recon settled, by area

### 5.1 The AUTH channel — best ratio in the repo

`cmsgstream.py:128` picks the catalog from *direction* and ignores the `channel` argument
it accepts at `:105`. ✔MAIN. With the catalog corrected, all four auth connections decode
to the exact byte: **78 c2s / 4,075 B and 91 s2c / 3,939 B, residual 0 on all 8
connection-directions**. The load-bearing control is that the *current* catalog cannot
frame these bytes at all — **AUTH 8/8 clean vs GAME 0/8**, every GAME attempt dying within
3–9 bytes.

Seven measured divergences between our auth server and ArenaNet's, each checked on both
sides. Two matter:

- **The heartbeat echoes the client's dword** — 15/15 are echoes, 0 carry 16; ours sends
  a constant 16 in **732 of 732** emitted messages, and `authsrv.py`'s comment claims it
  does not echo. The comment is false in both directions. CONTESTED → OBSERVED.
- **`0x0026` is the real answer to ASK_SERVER_RESPONSE** — `c2s 0x0035 → s2c 0x0026 → s2c
  0x0003`, in that order in all four sessions; we answer with `0x0003` alone.

Also new: retail sends **`0x0017`** as the third s2c message in every session and we have
no name for it. And the **80 `unhandled` records in `vault/captures/authsrv/` are all
`0x0009` UPDATE_CHARACTER_SETTINGS**, which retail answers 7/7 and we answer never —
leaving the request open, which is the exact condition `authsrv.py`'s own comment records
as having stalled a Play press for eight minutes.

Two corroborations worth banking: `GAME_SERVER_INFO`'s 24-byte blob is a `sockaddr_in`
(family==2 8/8, address in the client's actual TCP destination list 8/8, byte-reversed
reading **0/8**, other 4-byte windows 8 of 304); and `REQUEST_GAME_INSTANCE` field 3 is
the map id, corroborated three ways.

### 5.2 One in five client messages is decoded and thrown away

Measured over 306 `vault/captures/gamesrv/*.jsonl` (66.3 MB). **`948` is a count of log
*records*, not messages** — `note_unhandled` emits one per (session, opcode) first
occurrence. Verified two ways: across **884 (session, opcode) pairs, 0 have a record count
≠ 1 and 0 have a summary count ≠ the decoded count**. So decoded-count is the true
dropped-count: **2,116 messages across the 10 D9(a)-visible opcodes**, plus a **third
bucket nobody has reported** — 7 opcodes / 54 messages with no arm that D9(a) never saw
because every occurrence predates the fix. **Total 2,170 of 10,393 = 20.88%**, against
`note_unhandled`'s own docstring claim of 9.8%.

Largest drops: `0x0092` MISSION_MASK_REPORT **571** (all-zero in 515 of 571 because
nothing we send sets a bit), `0x00C1` TARGET_SELECT **363**, `0x000A`/`0x000B` 302 each,
`0x000D` 287, `0x0008` 131, `0x0040` ROTATE_PLAYER **108**. `0x0040` and `0x00C1` are
**fully named in `overrides.json` with three legs of evidence each and are dropped 100%**.

Free corroboration on a 4.8× larger sample than the override entries were written from:
`TARGET_SELECT` field2 == 0 in **363 of 363**; `ROTATE_PLAYER` has 64 finite angles all
inside ±π, 28 exactly `+inf`, 16 exactly `−inf` — the two `.rdata` sentinels the entry
names. UPSTREAM → CORROBORATED.

**The INTERACT defect is real.** ✔MAIN: `0x0039` — named INTERACT from ArenaNet's own
client traffic, **3.0% of live c2s** — has **no dispatch arm** (0 grep hits in
`authsrv.py`), while `0x0033` has one and has not been sent by any client since
2026-08-06.

### 5.3 The crash dialogs are a subsystem map

All 117 `crash-dialog.txt` parsed: 111 `Assertion`, 5 `Exception: c0000005`, 112 resolve
module+line, **72 distinct sites across 33 modules**. Two independent joins — a step-window
join from `gamesrv.log`, and a wall-clock join with the UTC offset derived *per run* —
attribute **103 to a specific GAME_SMSG opcode, 80 distinct, agreeing 103/103**.

Contiguous crash-proven blocks, which is a subsystem map the static handler map cannot
produce:

| Block | Range | Swept | Crash-proven |
|---|---|---:|---:|
| ITEMS / MERCHANT / TRADE | `0x0137–0x016A` | 38 | 23 |
| MISSION | `0x0173–0x01B9` | 54 | 15 |
| PARTY | `0x01BA–0x01D1` | 21 | 11 |
| SKILLS | `0x00D1–0x00D6` | 6 | 4 |
| QUESTS | `0x0096–0x0097` | 2 | 2 |
| STORAGE | `0x0083–0x0084` | — | ✔ |
| HEROES | `0x0072` | — | ✔ (×3) |

**TITLES: NOT FOUND.** Not one of the 72 sites names a title, rank or reputation module.
Do not schedule titles on this evidence.

**Nine runs were never scored.** Nine `--encstring` runs at 17:41–17:48 on 2026-08-12 are
referenced by no ledger file. Three independent checks say they are clean: 8 of 9 produced
no crash dialog; the sweep's proof-of-life fence shows **29–34 c2s messages over 13.6–15.9 s
after each probe**; and `--from-report` on all eight bisected runs prints `SILENT`, eight of
eight. **Cleared twice each: `0x0033`, `0x009E`, `0x00B9`, `0x00C0`** — all four still
ledgered ASSERTED. `0x019C` and `0x01D4` went to an already-dead client and are
**UNRESOLVED, not cleared**.

The correction cannot simply be recorded: `smsgsweep.record()` is first-write-wins, so
`--record` prints `recorded 0` and changes nothing, and the ledger has **no field for the
payload regime** — an encstring SILENT and an all-zero ASSERTED must not share a key.

### 5.4 Scale: transport is closed, pathing is the R4c blocker

The `~7,000 encode+encrypt per tick` claim is **sourced** (`studies/review/FINDINGS.md:302`)
and reproduces within 1% on both components. But it is not the send path: with hexlify +
recorder + print, the real path is **38,820 msg/s = 1,941 per 50 ms tick**, 3.9× slower,
the recorder ~70% of it. End to end with a player orbiting at 288 u/s, **800 chasing agents
cost 1.42 ms of a 50 ms tick — 2.84%**. Nothing is O(n²), and a cross-client O(n²) cannot
be written because `world_tick` is defined inside `handle()` and closes over one
connection's state.

A better denominator than "an R4 budget near 60": **ArenaNet's own server sustained
31.5 msg/s mean and peaked at 2,090 messages in one second** — 104 in a single tick against
our 1,941. **18.6× headroom at their peak, 1,232× at steady state. Record transport as
closed** (with the number amended from 7,000 to 1,941).

**The risk is `route()`, and it is one function.** Median is fine (0.342 ms). The tail is
not: over 1,500 in-band routes on Pre-Searing, **p50 0.360 ms, p90 1.451, p99 29.409,
p99.9 87.682, max 320.695 ms = 6.41 tick periods**, with **11 of 1,500 (0.73%) exceeding a
whole tick** on the thread that owns the world. Eight monsters re-pathing once a second
hits that roughly every 17 s, and the symptom is an intermittent world freeze — this
project's hardest failure to attribute. Cause is **not the A\***: a per-phase split
(validated against the shipped `route()` on 40 of 40 pairs) puts **search at 3.5% and
`_string_pull` at 94.2%**, cross-checked by call count. The dig's own first answer — a
"50.7× heapq speedup" — was an artifact of a variant that skipped the string-pull, and is
recorded here as **refuted**.

### 5.5 The replay oracle is refuted by its own subject — strike it

HANDOFF §7 specifies it as the project's test strategy and says *"Build it at R2."* R2
landed 2026-08-05. Three mentions in planning prose, zero lines of code.

**ArenaNet's own server does not pass the oracle as specified against its own recording.**
Same character, same account, same map, same session, minutes apart: **11 of 2,633 messages
and 95 of 41,997 bytes identical (0.2%), diverging at message 6.** The comparison is not
broken — the identical method reports **99.3% opcode-sequence agreement (LCS 295/297,
histogram cosine 1.0000)** on the very pair that is 5.4% byte-identical. **A gate that
cannot go green cannot go red for a reason.**

The obvious tolerance layer is vacuous by its own control: masking the first three dwords
lifts same-map agreement to 88–94% but blanks **45% of bytes and 60–68% of messages
entirely**, and scores **76.8–97.5% on *different maps***. A non-vacuous layer needs to know
which of **540 (opcode, field) slots** is an agent id, a timestamp or an RNG draw — and
`overrides.json` names **zero fields in the whole file**. `test_catalog`'s 477/477 pins field
*types*, which is the axis that does not help.

The prize is already banked anyway: `studies/divergence` D1–D11 *is* the oracle's output,
produced by histogram comparison. **Verdict: NO.** Strike HANDOFF §7 and PLAN §4-A1's
shadow-server paragraph; replace with a structural load-prefix conformance gate that needs
no field semantics and has a built-in negative control (different-map pairs at 3.5–20%).
Do not call it an oracle. Caveat: the 99.3% figure is n=2 connections on one map.

### 5.6 The vault holds a finished experiment nobody wrote down

`vault/dat_durability/Gw.dat` carries a tracer at the exact offset `ARMED.json` claims; the
armed row hashes to the recorded value, and the pre-arm baseline is reproduced by **two
archives the experiment never touched**. Documented **nowhere** — zero citations in either
tree, `studies/crossbuild/DURABILITY.md` does not exist — while
`studies/datwrite/FINDINGS.md:1455` says it is unrun and `studies/crossbuild/PLAN.md` rung 6
is exactly this deliverable. It also carries a **cross-build diff (334 changed rows: 308
silent relocations, 24 added, 1 recycled, 1 deleted)**, which is the empirical answer to how
much an ArenaNet update moves.

**But as staged it cannot fire.** No file in either tree references that archive, and
`archive.py`'s default reader is `dat_study`. To fire it must live on an archive the updater
touches — and `ARMED.json` warns `NOT_PLAYABLE`, because the 25-byte overwrite lands in a
compressed stream. That trade is the owner's.

Two framing corrections. The vault holds **8,541 images but only 2,580 screenshots** —
5,918 are third-party UI atlases under `mirrors/`, so a naive count overstates 3.3×. And
screenshots are **not** the footprint problem: **ten copies of the 3.91 GB archive are
39.10 GB of a 45.17 GB vault (86.6%)** against images' 7.7%, three of the ten byte-identical
at all 256 sampled windows and one a retained damaged copy. **Do not prune screenshots** —
they are cited as evidence in at least six places and are the only possible witness for
visual claims. A self-correction worth keeping: the first pass reported 13 "images-only"
sessions; nine pair to a `gamesrv` wire log by timestamp, so the true sole-record set is
**4 dirs / 12 images / 22.5 MB**.

### 5.7 The client-table backlog is one module, not 23 extractions

A general, build-independent locator exists: each `Gw\Const\*.cpp` static table is followed
immediately by a string, so `base + count*stride` lands on that string's first byte.
Verified on **12 of 14 tables by raw bytes**; the 2 non-closures are 4 bytes each and both
explained (alignment padding, a `-1` sentinel). Independent confirmation: the anchor
arithmetic and the accessor's own indexed load land on the identical file offset. This is
the idiom `reskin.py` already uses for one table — it just does not claim to generalise,
and it does. Eight table addresses are absent from every document and every `.py`.

**The real backlog is provenance, not symbols:** ✔MAIN — `content/*.toml` contains **zero
rows with `source = "client-table"`**. The machinery the 2026-08-11 ruling created, that
`content.py` enforces and `test_content.py` tests, has never been exercised by one row.

Three prior candidates argued down, which is the useful half: **`s_charCondition` does not
block R4b** (it is a name vocabulary; the mechanism is already graded SERVER-ONLY and no
duration is in any client table). **`s_energyTable`'s magic-number approximation in
`skilltable.py` is exactly right on the shipped corpus** (0 of 3,443 rows disagree) — latent,
not live, and it becomes live the first time the reskin arc authors a skill above 25 energy.
**`s_attribPoints[0] = 5` is dead data** — the accessor special-cases index 0 and returns 0,
which reconciles a self-contradiction in `reconstruction/FINDINGS.md`. And four listed
symbols (`s_avoidCount`, `s_sortedList`, `s_refCountAlert`, `s_indexTotal`) **are not tables
at all** and should be struck.

### 5.8 Textures — an unguarded writer, and ATTX is invisible

**ATTX is not "ATEX with a trailer".** It is an ATEX container with a constant 21,923-byte
`ffna` type-7 file appended, whose own chunk table closes exactly on **118 of 118**, verified
three ways. **`atex.parse()` raises on 118 of 118 ATTX and 0 of 3,645 ATEX** — the module is
blind to the entire terrain-texture class, which is exactly the class rungs e10f/e10g consume.

Three documented claims refuted: `studies/texture/FINDINGS.md`'s explanation of its own
non-closers is wrong (see §6C); "a one-level file has only ever been seen at DXTA" is a
stored-subpopulation artifact (real population: 77 DXT3 + 27 DXTA); and `atex.py`'s docstring
claim that both shapes are "attested in retail" is wrong for the full-chain all-raw case,
**0 of 3,763**.

The missing test is now cheap: a throwaway DXT1 decoder scores PLANAR below **all five** rival
layouts on **200 of 200** adjacent code-0 level pairs (planar MAE 10.617 vs 32.940 for the
next best), using only code-0 levels — no sub-codec needed. Honest limit: decisive *paired*,
not as an absolute threshold.

---

## 6. Contradictions, corrections and things this session got wrong

Recorded because a contradiction between two measurements is information, and because two of
these are this repo's named failure mode reproducing *inside the recon itself*.

**A. `main` moved 16 commits during the session.** ✔ verified. Its HEAD landed `0x00A6` for
the player's own agent plus the party pair `0x00B0`/`0x00B1`, `shotlabel.py`/`shotloop.py`
("the screen is the other channel"), and `studies/agentprops/FINDINGS.md`. Consequences: the
PARTY block is partly done and any "server sends 0 of it" claim is stale; the confounded-
screenshot problem now has an instrument. Re-verified as still true on `main`:
`cmsgstream.py:128`, `msgmix.py:87`/`:99`, `maprows._stamp`, the missing `0x0039` arm,
`test_agentlife`'s single opcode pin, and zero `client-table` content rows.

**B. Two digs disagree by exactly 948.** One reports 11,341 decoded messages over 306 files,
another 10,393 over the same 306. The difference is exactly the `unhandled` record count, and
the second dig independently established that every `unhandled` record has a corresponding
`decoded` record. **Treat 10,393 as the denominator**; 11,341 double-counts.

**C. "The 1,669 non-closing texture rows are exactly the ATTX class" is 21 rows short.**
`studies/texture/FINDINGS.md:47` says 52,253 of 53,922 closed. The full census gives
ATEX 52,274 + ATTX 1,648 = 53,922 — denominators match to the row, so **21 ATEX rows also do
not close**. The dig that examined this sampled 3,645 ATEX and saw 0 non-closers, which is
consistent with a 0.04% rate: **the sample was underpowered for exactly the residual it needed
to rule out.** Its refutation of the stated *cause* stands; its claim of a *pure* ATTX set does
not.

**D. Two live-corpus denominators are in circulation.** 22,524 s2c over 12 game connections
(reproducing `test_codec`'s figure) versus `msgmix.py`'s 21,543 over 8. Given §5.2, the
8-connection figure is a **windowed read of the newest 6 files**. Rate analyses built on it —
including the 2,090 msg/s peak — should be re-run after the `msgmix` fix.

**E. Three project documents are contradicted by measurement.**
`studies/datwrite/FINDINGS.md:1455` (durability unrun — it is armed and verified);
`RUNBOOK.md`'s "the client dials the `GAME_SERVER_INFO` host at hardcoded port 6112" (live,
`sin_port` is 6112 in 8/8, but two captures run **everything on port 80** with zero packets to
6112 while their own `wire_meta` shows 6112 was admitted — a rival reading fits the same data
and only a loopback run on a third port discriminates); and `authsrv.py`'s heartbeat comment.

**F. Two dig premises were wrong in the useful direction.** "The model format has zero mentions
in this repo" — `studies/customarea/FINDINGS.md:428` already names `ffna` type 2, the chunk ids
and thirteen vertex strides. "19 `s_*` symbols unreferenced" — it is 18 on `main`, and four of
them are not tables.

**G. A trap in our own tooling, found in passing.** `mapchunks.chunk_label()` silently
mislabels chunk ids from other riff types instead of refusing them: the 24,426 `ffna` type-8
files carry ids 1 and 2, which render as map chunk names — one of them a `NULL_LOAD` slot the
module warns never to emit.

**H. Two agents caught confident wrong numbers in their own instruments and reported them.**
One read `0x0039` as having a dispatch arm from a `decoded`-vs-`unhandled` comparison, not
realising `decoded` is logged *before* dispatch and that 107 of 306 captures predate the D9(a)
instrumentation; the AST settles it. The other's first sabotage driver matched constants by
decimal text while the source writes hex, so **11 of 15 patches silently failed to apply and
were scored as "caught"** — producing a confident and exactly inverted headline. Both are the
repo's recorded failure mode, reproduced inside a session designed to look for it. Weight the
rest of this document accordingly.

---

## 7. Two things to fix regardless of what else is decided

**7.1 `atex.py` can truncate the owner's install.** ✔MAIN — `atex.py:329` is
`with open(a.make, "wb") as f: f.write(data)`, reached directly from `--make OUT`, with **no
guard of any kind**. It is the only binary writer in `toolkit/mapdata/` without one, in a repo
where `datwrite`, `rebloat`, `mapbuild`, `mapexport` and `reskin` all have one and two were
added *because* the class of tool had already written into the wrong tree.
`--make C:\gw\Gw.dat` would truncate the owner's 4.2 GB archive. Not tested, and correctly not
tested. Copy `rebloat.guard_target`'s shape, with a positive control that an ordinary scratch
path is still allowed.

**7.2 `vault/state/sessions.json` sits outside the scrub root.** ✔ verified structurally
(field names only; no values read out). Five session records, each carrying an `email`, a
36-character `user_id` and a 36-character `token` in cleartext; three of the five emails are
real-shaped rather than the synthetic `rurik@local` / `asd@local`, and the newest record is
dated today. `scrub_captures.py:528` defaults its root to `require_dir("captures")`, so
`vault/state` is **never walked** — and `RUNBOOK.md` names `captures-scrubbed/` as the one tree
that may leave the machine. The vault is gitignored and this is not a disclosure; it is a hole
in the process that exists to prevent one.

---

## 8. Recommended order

Lanes follow PLAN §5's own finding that the constraint is human time, not agent time.

### LANE A — desk work, no client, no human

| # | Action | Expected result |
|---|---|---|
| 1 | `atex.py` output guard (§7.1) | `--make C:\gw\Gw.dat` refused; scratch path still allowed |
| 2 | `maprows._stamp` gains `format: CACHE_FORMAT` (1 line) | a **warm** `test_maprows` at `CELL_PITCH = 64.0` goes red with the same six failures the cold run produces |
| 3 | Eight literal opcode pins in `test_agentlife.py` | sabotage sweep flips from 11 survived / 4 caught to 4 / 11 |
| 4 | `cmsgstream.py:128` channel fix (1 line) + ship the AUTH-clean/GAME-desync assertion | `test_cmsgnames` auth count 2 → 17; 22 UPSTREAM auth names become CORROBORATED or CONTESTED with zero new capture |
| 5 | Add a `regime` dimension to the sweep ledger, then re-score the nine orphaned runs | `0x0033`/`0x009E`/`0x00B9`/`0x00C0` move ASSERTED → SILENT-under-encstring; `0x019C`/`0x01D4` land UNRESOLVED. Do **not** just add `--record` — first-write-wins prints `recorded 0` |
| 6 | `msgmix.py`: widen `[-6:]`, drop the `kind == "sent"` filter | the tool that ranks what to build next sees 306 sessions and both directions for the first time |
| 7 | `0x0039` arm beside the existing `0x0033`, plus `0x0092`/`0x00C1`/`0x0040` handlers | dropped fraction falls from 20.9% toward ~3% |
| 8 | Bound `_string_pull`, re-measure the same 1,500 routes | p99.9 falls from 87.7 ms; "11 of 1,500 over a whole tick" → 0, with the None-rate unchanged and every path still passing `route()`'s own gate |
| 9 | Write `studies/crossbuild/FINDINGS.md` from `vault/dat_durability`; correct `datwrite/FINDINGS.md:1455` | a finished experiment stops being invisible |
| 10 | Point the scrub at `vault/state` (§7.2) | the tree that may leave the machine actually covers the credentials |
| 11 | Strike HANDOFF §7 and PLAN §4-A1's shadow-server paragraph; leave the load-prefix carve-out | weeks removed from the ladder, and the vacuous tolerance layer recorded as a refuted rival so it is not rediscovered |
| 12 | Run the map suite against the second vaulted archive (19 tests take `--dat`; three pass today) | every "349 of 349" gains a second witness for free |
| 13 | `npcdefs.py --emit`, then re-census `content.py` | R4c-1/R4c-2 gain their first extracted rows; `vault/content/` exists |
| 14 | `consttable.py --verify` seeded with the 12 closures, then `s_effect` | the first `client-table` provenance row in this repo's history |

### LANE B — needs a client at the keyboard

1. **Send `0x009E` with a real encoded string and a live agent id.** Cheapest visible
   player-facing result available; crash evidence and encstring evidence both point at it, and
   `main`'s new `shotlabel.py` can now read the screen mechanically instead of by eye.
2. **One bisected encstring run each for `0x019C` and `0x01D4`** — two ledger rows currently
   neither cleared nor confirmed.
3. **Confirm the party pair actually draws.** `main`'s own commit says whether an entry DRAWS is
   UNVERIFIED and needs one run.
4. **Loopback run with auth on a port that is neither 6112 nor 80** — discriminates RUNBOOK's
   "hardcoded 6112" from "the client reuses the auth port" in a single run.
5. **`0x0166`/`0x0167` → c2s `0x0079`**, with a `0x0079` arm added first — the only two
   GAME_SMSG opcodes in 334 ledger rows that provoke a client reply.

### LANE C — live service or an owner decision

1. **Where to arm the durability tracer.** As staged it cannot fire, and the playable archive
   trade is the owner's.
2. **Vault pruning** — 39.10 GB of 45.17 GB is ten copies of one archive. Screenshots are 7.7%
   and should not be touched.
3. **A live capture exercising what our harness cannot** — `0x003B` NPC_SERVICE_SELECT appears
   22 times live and never once from us, always between `0x0039` INTERACT and `0x0012`. Our
   world has no service NPCs, so the action is *impossible* here rather than untried.
4. **Model geometry: recommend NO for now** — but file the §6.1 row either way, because the
   second gate wants it *before* the module and it costs one table row today.

---

## 9. What is still not known

- **Whether the durability experiment can ever fire.** How ArenaNet's updater selects its
  target archive is unmeasured. This is the crux and it is unanswered.
- **Whether a well-formed `0x009E` renders anything.** SILENT means no reply and no crash, not
  "visible". The incidental screenshot pair is confounded (43.3% base rate over 284 runs).
- **What the load-burst opcodes mean** — `0x0008`, `0x000C`, `0x000D`, `0x0028`, `0x0079`,
  `0x0093`. Counts, arrival times and layouts; no semantics. `0x0093`'s single word is 146 =
  `0x92` in all 9 samples, suggestive of a MISSION_MASK_REPORT pairing and deliberately not
  built on.
- **Why `0x0033` stopped being sent** — 206 occurrences in the 2026-08-05/06 corpus, 0 since,
  0 live, while we still dispatch it.
- **Whether `0x008A` is being driven wrongly** — ours: 554 occurrences in 285 of 306 sessions,
  inside every instance load. ArenaNet's: exactly once per capture, only on the
  character-creation connection. An unexplained state divergence nobody has looked at.
- **The 21 non-closing ATEX rows** (§6C) and the 11,341-vs-10,393 discrepancy (§6B) — both
  arithmetic, both cheap, both open.
- **Server memory at scale, GIL contention between the three threads that call `send()` on one
  connection, and per-tick skill-cast cost.** Every benchmark was single-threaded with a socket
  sink, so no TCP or kernel cost is included, and it has **not** been shown that our server can
  push 2,090 msg/s through a real connection.
- **`authsrv.MAP_ID_COUNT = 877`** sits beside a client table this project measured at 888 rows,
  and nothing checks the two against each other. Flagged, not diagnosed.
- **What the 12,288 non-map-declared models are.** Measured: not declared by any map, and they
  alone carry sequence chunks and their own textures. Characters/armour/weapons is a guess.
- **Every static client-side claim rests on one build (38797)**, though a second build sits in
  the vault and only 2 of 28 `clientscan`/`clientpatch` tests read it.
- **How much of this document `main`'s 16 commits already supersede.** Six specific claims were
  re-checked by hand and all six still hold; the full delta has not been enumerated.

---

## 10. Method, and what would have made it better

Two workflows: 8 census lenses + a ranking pass, then 10 recon digs + a brief. 19 agents,
~3.76M tokens, 1,318 tool calls, all read-only, no client launched, nothing written outside a
scratch directory.

**What worked.** Multi-modal sweeping — eight lenses each searching a *different* way — is what
produced the convergence signal; the five-lens agreement on the player-facing cluster is worth
more than any single lens's confidence. Requiring a stated prediction before an expensive
measurement caught at least two rationalisations. And requiring the ranking agent to *re-run*
the load-bearing numbers rather than pass them through corrected six figures, including one of
its own.

**What did not.** Nobody pinned the tree to a moving `main`, and 16 commits landed underneath
the digs — the exact hazard `CLAUDE.md` documents, arriving from the direction it does not
(not a stale worktree read by mistake, but a correct worktree that went stale while being read).
**A survey arc should re-check its "absent" claims against `main` at write-up time**, which is
what §6A is; doing it up front would have been cheaper.

Modalities still unswept: a full correctness/sabotage sweep beyond the 15 constants sampled;
the external-authority lens (diffing the GW wiki's own Pre-Searing inventory against `content/`,
which would produce a denominator nobody here derived); and an audit of PLAN §6.1's derivation
register against what the code actually *imports*, which is the direction that can do damage.
