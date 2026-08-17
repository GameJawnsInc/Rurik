# Authoring quests — can we, what would it cost, and what to do next

**Arc:** `studies/quests/` · **Companion:** [FINDINGS.md](FINDINGS.md) (what quests *are*) · **Date:** 2026-08-15
**Tree:** written from `.claude/worktrees/festive-heyrovsky-8cdf6e`, pinned build **38797** (`vault/client/2026-07-29_221c13772c7a/Gw.exe`), live corpus `vault/captures/live/`.

This is a decision document, not a study. It answers one question — *is a session spent on quests worth it, and on what* — and every rung below is written so it can go red.

---

## 1. The verdict

**YES, and it has already happened.** On 2026-08-15 a probe sent one hand-built `GAME_SMSG 0x0049` QUEST_ADD at a real, unmodified retail client on our own server and a quest-log entry appeared — a `?` icon under the level bar, 23.8% of that icon slot differing from a run without the message (`studies/minimap/FINDINGS.md:721`, `toolkit/authsrv/probes.py:2467`). It rendered `?` rather than a name for exactly one reason: **the probe deliberately sent three empty strings**, because the marker was what was under test and "an authored string is a separate question" (probes.py's own comment).

So the brief's literal question is settled OBSERVED. The question that decides whether a session is worth spending is the next one: **can a quest carry OUR words, and can a player accept and finish it.** That splits into one cheap experiment and one short chain, and the cheap experiment goes first.

> ### Q0 RAN, 2026-08-15, AND IT IS GREEN
>
> **The quest tracker reads `Ascalon:`.** Probe `quest_name`, build 38833, **map 449**, loopback, caged; capture `vault/captures/harness/20260815T200632`, `hold002` → `hold012`, **8,085 of 218,400 px** differing in the tracker box, worst channel delta 247. A string id we chose came back as a rendered glyph, so **rung Q2b's premise holds and the naming half of authoring is done** — the problem is now "which string id", not "can we name a quest at all".
>
> **The client then asked us for the description on its own** (`c2s 0x8012 REQUEST_QUEST_INFO`, which we drop). It took the entry as a real quest.
>
> ### Q3 RAN THE SAME DAY, AND IT IS GREEN
>
> **Our own prose renders.** The server answers `GAME_CMSG 0x0012` with a `0x004C` built from `content/quests.toml`, and the Quest Log's summary pane reads *"Speak to the gate guard, then return to me."* with our objective above it. Capture `vault/captures/harness/20260815T204539`. Rungs **Q2 and Q3 are done**; `test_dispatch`'s recorded drop for `0x0012` is closed.
>
> **The framing question is settled, by a crash.** A bare literal killed the client on `(codedString[0] & ~WORD_BIT_MORE) >= WORD_VALUE_BASE`, `TextApi.cpp:585`. `questdefs.coded_literal` now refuses to build one. **Route B's 128-code-unit claim is no longer RECONSTRUCTION** — authored prose demonstrably fits and renders, minus the three units the framing costs.
>
> **A bonus nobody costed: we can choose the log SECTION.** `flags = 32` put the quest under *"Primary Quests"*, exactly as §1.4's `test al, 0x20 → sortCode 1 → heading id 0x464` predicted. §3's table said `section` was "not authorable"; it is, to one of four, from the server.
>
> **What Q3 did NOT settle:** the client composes part of the heading itself (*"Ascalon (Kamadan, Jewel of Istan):"* — the map name is not ours), and the **name** slot is still ArenaNet's id `0x3D64`. Authoring our own name is still rung **Q2b** and still needs `textwrite.py`.
>
> ### Q4 RAN THE SAME DAY, AND IT IS GREEN — THE GATE IS OPEN
>
> **`0x0080` + `0x0081` opens the NPC dialog window.** Titled *"Hatcher [Collector]"* — the client resolved the speaker's name from the bare `agent_id` — carrying our authored line. Capture `vault/captures/harness/20260815T211339`. The frame between the two messages shows **no window**, so §2.5's accumulator/flush split is confirmed, not just the pair.
>
> **This was the rung the whole ladder sat behind**, and §6 called it right: EXPENSIVE, not BLOCKED. `test_dispatch`'s gate on `0x003B` (*"blocked behind 0x0039"*) is closed, and `authsrv.py`'s deferral to *"an NPC-service study"* is retired.
>
> **What it did not settle:** the server answers *any* interaction with *every* quest's giver line, because there is still no npc→quest binding — §3's `[quest.X.server]` block remains a proposal. And `0x003B` is still unanswered, so nothing can be *accepted* yet. **That is Q5, and it is now the only thing between here and a quest a player can take.**
>
> ### Q5 IS HALF DONE, AND THE OTHER HALF NOW HAS A MEASURED NEGATIVE
>
> **Done:** `0x003B` decodes (`0x800000 | quest_id<<8 | code`), verified against three of ArenaNet's own dwords with an encoder as inverse; the server answers code `0x01` with `0x0049` from the quest row and code `0x03` with nothing, matching ArenaNet 2 of 2. `test_dispatch`'s second recorded drop is closed. **No client has exercised the arm**, so it is RECONSTRUCTION until one does.
>
> **Not done, and it is the rung's real content:** nothing we send makes a **clickable option** appear, so no client has ever sent us a `0x003B`. Replaying ArenaNet's own greeting line verbatim renders the same text and **no option**, across two runs with the click placed on the greeting's own last line. That refutes the natural hypothesis (the option is in the dialog string) and points at the **agent** instead — theirs was a real giver, ours is a collector.
>
> **Consequence for this document:** Q5's acceptance criterion as written — *"the player clicks accept in a window we opened"* — cannot be met until the option renders, and that is now its own rung with three named candidates (FINDINGS, Q5 section). The rest of the ladder is unaffected: Q6 (instance replay) and Q7 (turn-in) both drive off `0x003B` codes and inherit the same blocker, so **the option renderer is now the critical path**, not any of the six verbs.
>
> **Three things Q0 did NOT settle, stated so the green does not spread further than it earned:**
> 1. **The compass free rider went unclaimed.** The run was on map 449, so the marker fields were 449's and §7.3 is untouched. Map **148 cannot load at all**: no client archive in the vault binds `0x1B97D` as the server's does — four run dirs hold only the bit-31 mid-replacement spelling and the 38833 copy binds a rewritten file. That is archive state from the terrain arc, not a quest problem, and it is the first thing to fix before the compass question can be asked.
>    **FIXED 2026-08-16, with one premise refuted.** `datwrite.py --relink-plain 0x1B97D`
>    re-bound the plain id to row 7982 in the canonical
>    `vault/run/2026-07-29_221c13772c7a/Gw.dat` — the DnArchive re-link minus the
>    download; sha-verified backup beside the archive, journal and censuses under
>    `vault/research/relink-1b97d-2026-08-16/`. `contentids` preflight is green
>    **10 of 10, maps 146/148 included**, against the archive `select_run_exe`
>    launches, so the compass question can now be asked on 146/148 with the pinned
>    38797 client. The refuted premise: the 38833 copy's file is **not** a terrain-arc
>    rewrite — row 177262's bytes are sha-identical across the pristine 2026-08-13
>    snapshot, the 38833 run dir and the 38833 run-live copy, so it is ArenaNet's own
>    38833-generation map, merely a different generation than `dat_study` serves. A
>    38833-exe run still needs `--map 449` or a same-generation `RURIK_DAT`.
> 2. **`0x004C` was never sent**, so no authored *prose* has reached a client — only an 8-unit name slot. Route B's claim that description and objectives hold ~125 characters is still RECONSTRUCTION, and rung Q3 is still its test.
> 3. **The `?` icon is not the name.** `studies/minimap/FINDINGS.md:721` read it as "the empty name string we deliberately sent"; the icon is still present here *beside* `Ascalon`. Empty strings produced **no text**, not a `?`.

### The one test that decides the naming half

**Change one literal in `toolkit/authsrv/probes.py:2467` and run the existing probe once.**

```
  before: Step(8.0, 0x0049, [1, _SPAWN_WORLD, 148, 148, 0, "", "", "", 0], ...)
  after:  Step(8.0, 0x0049, [1, _SPAWN_WORLD,   0, 148, 32, "\u3D64", "\u3D64", "\u3D64", 148], ...)
```

Three fields change besides the strings, and the reason is a census I ran myself over every `0x0049` in the three keyed live captures (n=10): ArenaNet sends **plane ∈ {0, 26}**, **flags ∈ {0, 32}** (32 in 8 of 10), **home_map ∈ {146, 148}**, and **slot 0 = `3D64` in 10 of 10**. The probe sent plane **148** and home_map **0** — two values ArenaNet never sends. `0x3D64` is the word ArenaNet itself puts in slot 0 of every quest add in the corpus, and it resolves through `toolkit/clientscan/textrec.py` as string id **15460 → `'Ascalon'`** (plain record, no key needed; the rival raw-word reading gives 15716, which returns `None`).

**Cost:** one line, one caged loopback run, ~40 s. **NEEDS OWNER GO-AHEAD** (client run).

| Outcome | What it means | What it unblocks |
|---|---|---|
| The log entry reads **`Ascalon`** instead of `?` | The repo's governing rule — *commit the id, resolve the string at run time* — holds for quests. Authoring is a content-TOML plus six messages, and the naming problem is reduced to "which string id". | Rungs Q2–Q7 as written. |
| The entry still reads `?` or blank | Our coded-string construction is wrong on the wire even though it re-encodes byte-identically offline. Everything downstream that carries a string is suspect, and the string16 encoding becomes rung 1 rather than an assumption. | Nothing until fixed — but it fails **cheap**, which is the point of putting it first. |
| The client asserts or drops the connection | We are out of bounds on a field, most likely `quest_id = 1`. Re-run with an id inside the observed band. | A bound we need to know anyway — see §6's `CHALLENGES` finding. |
| **A compass starburst also appears** | The `NOT FOUND` at `studies/minimap/FINDINGS.md:727` was a malformed probe, not an unknown protocol, and `CompassQuestEffect.cpp` does not need disassembling. | Retires an open item three lanes inherited. |

That last row is a free rider on the same run and is the reason to fix the fields even if you only care about the name.

---

## 2. The substrate, as it actually is

Not what the study says quests are — what it would **cost** to add them.

### What is free

| What | Where | What it gives us |
|---|---|---|
| The content store takes a new table with **zero loader changes** | `toolkit/content.py:345-385` (`load()` walks every `*.toml`), `:194-201` (`_check_provenance` is the only per-row gate) | I wrote a three-field `content/quests.toml` to a scratch dir and loaded it through this tree's real loader: `census: {'quest': 1}`, `why: quest.hello_ascalon  source=invented`. No per-kind required-field dict exists anywhere in the file's 418 lines. |
| Provenance is **enforced and tested** | `toolkit/content.py:85` `UNLICENSED`, `:104` `EXTRACTED`, `:121` `NEEDS_BUILD`, `:125` `NEEDS_CAPTURE`; `toolkit/test_content.py:29-75`, ledger floor 39 | A quest row citing `client-table` with no `extractor` that exists on disk, or no `build`, is refused at load. Eight refusal rules are broken on purpose by a test. |
| Test discovery is from the **disk** | `toolkit/run_suite.py:142-158` walks `toolkit/` for `test_*.py`; `toolkit/test_srclint.py:223-265` checks `TESTS.md` bidirectionally | A `toolkit/test_quests.py` is picked up with no registration — but its `TESTS.md` entry must land in the same commit or `test_srclint.py` §7 goes red. |
| The row shape is **already precedented** | `vault/content/npcs.toml` `enc_name = [33026, 17658, 61813, 62562, 27710]`, extractor `toolkit/authsrv/npcdefs.py:13` | A quest's three coded strings are the same object as an NPC's name: a list of u16 code units, not text. Do not invent a representation. |
| Every message is **already decodable and encodable** | `schema/messages.json` carries field layouts for all fifteen quest opcodes; `toolkit/authsrv/cmsgstream.py` frames all 12 keyed live connections at residual 0 | I re-ran `frame_report`: 12 of 12 clean. The wire half needs no reverse engineering, only naming. |

### What a quest table would actually cost

The loader is free; the **consumer** is the whole job, and it does not exist.

| Cost | Evidence |
|---|---|
| **Fifteen opcodes to name.** `schema/messages.json` carries **0 names on all four channels** (487 GAME_SMSG, 194 GAME_CMSG). `schema/overrides.json` names exactly one quest opcode — `GAME_CMSG 18 REQUEST_QUEST_INFO`. `GAME_SMSG 76` (`0x004C`) has no override entry at all. | I checked `ov['channels']['GAME_SMSG'].get('76')` → `None`. |
| **Two dialog opcodes to name** — and they are the ones the whole path turns on. `GAME_SMSG 0x0080` and `0x0081` are unnamed in *both* files. See §6. | `msgshape.py 0x0080` → `RECV handler 0x0091e750, [string16], wire 248`; `0x0081` → `RECV handler 0x0091e770, [agent_id], wire 6`. |
| **Zero server code.** `grep '0x0049\|QUEST_ADD\|0x0012'` over `toolkit/authsrv/authsrv.py` returns one unrelated comment at line 279. No constant, no send site, no handler. The only `0x0049` this project has ever emitted came from `probes.py`. | Confirmed by grep. |
| **Two recorded, deliberate drops to close.** `toolkit/authsrv/test_dispatch.py:110-114`: `0x0012` is *"REAL MISSING WORK, not a no-op… Answering it needs a quest table this repo does not have, and inventing quest text is worse than the drop."* `:127-130`: `0x003B` is *"Blocked behind 0x0039… Handle it when INTERACT gets a reply."* | Read verbatim. |
| **`0x0039` INTERACT stores and answers nothing.** `authsrv.py:5101-5102` sets `state["interacting"]` and `state["interact_byte"]`, with a comment saying the reply must wait until *"an NPC-service study says what an interaction should ANSWER"*. | This document is that study. See §6. |
| **No id allocator, for any table.** `toolkit/contentids.py` is not one — it is a map-`file_id` consistency check between the server's and the client's archives (`:166-283`). NPC `agent_id`/`definition` values are hand-picked and coordinated by prose comment (`content/world.toml:317-320`). | Quest ids need the same convention — and §6 shows the range is far tighter than anyone assumed. |
| **`content/*.toml` and `git` have never held a quest row.** `git log --diff-filter=A --name-only --all \| grep -i quest` → empty, all branches. `TESTS.md` word-boundary `quest` → zero. | Two lanes checked; I re-ran the git one. |

**Current census** (`python toolkit/content.py`, 2026-08-15): `area 3, attack_speed 1, attribute 51, item 1, map 10, npc 56, player 2, skill_effect 12, skills 1333, spawn 4`. `PLAN.md:592-594`'s baseline is stale (it records `player 1` and no `attribute`/`skills` rows) — worth fixing in whatever commit touches §3.2.

---

## 3. A draft `content/quests.toml` — **RECONSTRUCTION**

Labelled RECONSTRUCTION as a whole: this is a schema we built. Every *value* below is measured and cited per column in §5; the *shape* is ours and retail may organise it differently.

```toml
# content/quests.toml -- the quest table.
#
# WHAT A ROW IS. A quest as the CLIENT can express it, plus the state OUR server
# has to hold to run it. Those are two different things and the row says which is
# which: everything under [quest.X] up to `flags` goes on the wire in GAME_SMSG
# 0x0049 / 0x0050 and is MEASURED; everything under [quest.X.server] is ours and
# is INVENTED. The client has no field for a prerequisite, a giver or a reward.
#
# THE STRING COLUMNS HOLD WIRE CODE UNITS, NOT STRING IDS, and the distinction
# has already cost one draft. `enc_name = [0x3D64]` is the u16 the server puts on
# the wire; the ARCHIVE string id it denotes is 0x3D64 - 0x100 = 15460, which
# `textrec.py` resolves to 'Ascalon'. Reading the TOML number as a string id
# gives 15716, an encrypted record that returns None. Same column, two numbers,
# and only one of them is what `codec.py` wants.
#
# ID ALLOCATION. The client asserts `challengeId < CHALLENGES` at
# UiCtlWebLink.cpp:576, compiled `cmp edi, 0x5b9; jl` -- CHALLENGES == 1465 on
# build 38797, measured. The highest quest id in our whole live corpus is 1462.
# There is no high band. Ours go in the gaps, and a row that picks one has to say
# which gap and why.

# ---------------------------------------------------------------------------
# A quest of ArenaNet's, transcribed from OUR OWN capture. Every number here was
# read off the wire; not one word of ArenaNet's text is in this file, and none
# could be -- the name and description ids resolve to RC4 records whose key this
# repo has not recovered. That is a safety property, not a limitation.
# ---------------------------------------------------------------------------
[quest.observed_80]
quest_id      = 80
enc_location  = [0x3D64]                              # slot 0, constant in 10/10 adds
enc_name      = [0x1703, 0xA86E, 0x9E9B, 0x4C82]      # slot 1
enc_npc       = [0x3374, 0xA50C, 0xD6AC, 0x226D]      # slot 2, SHARED with quest 1462
marker_x      = 11715.0
marker_y      = 3517.0
plane         = 26
marker_map    = 148
home_map      = 148
flags         = 0                                     # bit0 DESC_FILLED is set by 0x004C, never by us

[quest.observed_80.provenance]
source    = "capture"
capture   = "20260807T143055"
origin    = "live"
extractor = "toolkit/authsrv/questdefs.py"            # DOES NOT EXIST YET -- content.py refuses this row until it does
note = """
Transcribed from ArenaNet's own GAME_SMSG 0x0049 at t=28.179 on connection
:60935, with the 0x004C at t=28.241 supplying nothing this row keeps.

`enc_name` and `enc_npc` are STRING IDS with a trailing varint, not text: both
leading ids resolve to ENCRYPTED archive records (44 of 44 name/NPC slots do,
against 22 of 22 bare plain ids in slot 0). We cannot read them and do not want
to -- the words are ArenaNet's expression. The numbers are measurement.

CORPUS CAVEAT, and it applies to every capture-sourced quest row: the session
that produced this also carries quest id 1462, which GWW identifies as
'Getting Started in Guild Wars', a REFORGED MODE quest added 2026-05-27. The
character was opted into Reforged Mode. Nothing here is known to be baseline.
"""

# ---------------------------------------------------------------------------
# A quest of OURS. This is the row shape the ladder in section 4 actually
# targets, and section 5 argues it is the better route.
# ---------------------------------------------------------------------------
[quest.rurik_first_errand]
quest_id      = 1463                                  # see the CHALLENGES note; 1463/1464 are the only free ids under the bound
enc_location  = [0x3D64]                              # 'Ascalon' -- ArenaNet's id, resolved at run time, never committed as text
enc_name      = [0x3D64]                              # PLACEHOLDER until Q2b writes our own record; then a bare id of ours
enc_npc       = [0x3D64]
marker_x      = 9826.0
marker_y      = 8077.0
plane         = 0
marker_map    = 148
home_map      = 148
flags         = 32                                    # 8 of 10 observed adds carry 0x20; meaning UNVERIFIED

# The 0x004C body. 128 code units each, which is real prose -- unlike the 8-unit
# name field above. `description`/`objectives` as literal strings are OURS and
# carry no provenance obligation at all.
description = "Speak to the gate guard, then return."
objectives  = "Return to the guard."

  [quest.rurik_first_errand.server]
  # Nothing in this block reaches the wire as a quest field. It is what OUR
  # server holds, and the client has no column for any of it.
  verb        = "dialogue"                            # one of the six; see studies/presearing/MANIFEST.md:696-709
  giver_npc   = "hatcher"                             # a key into content/npcs.toml
  accept_code = 1                                     # 0x003B low byte that accepts
  turnin_code = 7                                     # 0x003B low byte that turns in
  requires    = []                                    # prerequisite quests, by key -- state, not just completion
  min_level   = 0
  reward_xp   = 0                                     # UNIMPLEMENTABLE TODAY: see section 6, the reward family has zero wire samples

[quest.rurik_first_errand.provenance]
source = "invented"
note = """
Ours. The quest, its words, its objectives and its id.

`enc_location` cites ArenaNet's own string id 0x3D64 and that is deliberate and
permitted: it is the pattern content/maps.toml already uses -- commit the id,
resolve the string from the owner's own archive at run time. `enc_name` is the
same id as a PLACEHOLDER only; the intent is that Q2b writes our own plain text
record with toolkit/mapdata/textwrite.py and this becomes a bare id of ours.

`flags = 32` is a value we copied without understanding it. Nothing names bit 5
and no assert reads it. If a run shows it matters, that discovery belongs in
FINDINGS, not silently here.
"""
```

### Cross-check: what the client can express vs. what a quest is to a designer

The client's side is `questTag` plus the 52-byte `challengeSortArray` entry (`charContext+0x52C`, stride `0x34`, count at `+0x534`; the deleter at `0x0080F7A0` frees exactly the five slots typed as pointers, which is the check that could have failed and did not). The designer's side is GWW's `Template:Quest infobox` and `Template:Standard prerequisites`.

| Designer's field (GWW) | Client's field | Verdict |
|---|---|---|
| `id` | entry `+0x00`, the u32 every quest message carries | **Agree.** One u32, and it is the binary-search key. |
| `name` | `enc_name`, slot 1 of `0x0049` | **Agree in kind, disagree in size.** 8 code units is an id reference, not a name. |
| — | `enc_location` (slot 0), `enc_npc` (slot 2) | **Client-only.** The designer has no word for either. Slot 0 is constant `3D64` in 10/10; slot 2 is *shared between quests with the same giver* (80 and 1462 both cite `3374 A50C…`). |
| — | `plane`, `marker_map` vs `home_map` | **Client-only, and two map ids, not one.** `home_map` is stable per quest across re-sends; `marker_map` moves as the quest advances. Which is giver vs marker is UNVERIFIED. |
| `type` = Primary/Secondary/Festival/Mini-mission/Minigame | `questTag.questType` ∈ {0, 1, 2} | **THE BIG DISAGREEMENT. These are different taxonomies at different layers and neither corroborates the other.** The wiki's is a 5-value display/story category; the client's is a 3-value **UI frame-class discriminator** (`QuestLog:167` selects a `QuestChallenge` factory for 0, `QuestMission` for 1, and **NULL** for 2). And decisively: **no quest message on the wire carries `questType` at all.** Writing a `quest_type` column would be pure invention. **Do not.** |
| `given by`, `given at` | *nothing* | **Server-only.** The client's log entry has no giver field. The binding is ours. |
| `required` / `required2/3`, `active`/`complete`/`unstarted`, `minimum` level, `profession`, `nationality`, `required hero` | *nothing* | **Server-only, and richer than "requires quest X".** GWW gates on a prerequisite's **state** (active vs complete vs unstarted), not merely its completion. A `requires = ["quest_key"]` column cannot express that. |
| `section` (quest-log grouping) | `sortCode`, four groups | **Not authorable.** Computed client-side from three challenge flag bits and `questType`, with four hardwired heading string ids. We can place a quest into one of four; we cannot make a fifth. |
| `acceptance reward`, `experience reward`, `completion reward` | *nothing in the log entry* | **THE SECOND BIG DISAGREEMENT.** Rewards are the designer's most-wanted column and the one with the least evidence. They ride a separate family — `0x004E`, `0x006C`, `0x0096`, `0x0097`, `0x00FA/0x00FB` into `GmQuestComplete.cpp`, which is a **3D scene with a model, a light and animation sequences**, not a dialog. Every one of those opcodes has **zero occurrences** in the entire live corpus, because the operator never completed a mission. |
| `repeatable` | *nothing* — GWW itself says *"These quests are not marked as repeatable in-game"* | **Agree that it is server state.** |
| — | `flags` bit 0 = `CHAR_CHALLENGE_FLAG_DESC_FILLED` | **Client-only and NOT authorable.** `0x004C`'s body sets it (`or dword ptr [esi+4], 1` at `0x0080F2D0`) and `0x0054`'s body *returns immediately if it is clear* (`test byte ptr [edi+4], 1; je` at `0x0080F9CD`). Sending an objectives update before answering the description request is a **silent no-op**. |

---

## 4. The ladder

Ordered cheapest-first. Every rung names what can go **red**. Costs use this repo's honest units, and the split is the single most useful thing here: **`PLAN.md:806-810` measured its own estimates as wrong by 15–100× in the agent-farmable lane and by nothing at all in the lane that needs the owner.** So the desk rungs below are almost certainly over-costed and the client rungs are not. Budget go-aheads, not hours.

### Tier 0 — the deciding run

| Rung | What it is | Acceptance criterion (can go red) | Depends on | Cost |
|---|---|---|---|---|
| **Q0** | The naming probe of §1: `probes.py:2467` with `enc_* = [0x3D64]` and the three out-of-distribution fields corrected. | The quest log renders **`Ascalon`**, not `?`. Red if it renders `?`, blank, or the client asserts. Free rider: whether a compass starburst draws. | nothing | **1 line + 1 caged loopback run, ~40 s.** **NEEDS OWNER GO-AHEAD.** |

**Do this before anything else and before writing a line of the server.** Everything from Q2 down assumes the client accepts a string id we chose; Q0 is the only thing that tests it, and it costs less than reading this paragraph.

### Tier 1 — static, agent-farmable, no client, no harness contention

| Rung | What it is | Acceptance criterion (can go red) | Depends on | Cost |
|---|---|---|---|---|
| **Q1** ✅ | Name the seventeen opcodes in `schema/overrides.json`: SMSG `0x0049`, `0x004A`, `0x004B`, `0x004C`, `0x004D`, `0x004E`, `0x0050`–`0x0054`, `0x0080`, `0x0081`; CMSG `0x0011`, `0x0013`, `0x0014`, plus the confirmation note on `0x0012`. Each with its own evidence chain and its own confidence. | **`test_dispatch.py`'s `unlisted_named` goes red the moment an opcode is named without an arm or a `DROPPED_ON_PURPOSE` row — that check firing IS the rung working**, and the row must land in the same commit. (Same shape as minimap S11.) | nothing | **~1 agent-day.** All seventeen currently carry `name: null`, so every one is a net gain. |
| **Q1b** (b) ✅ | Fix the two documentation defects this study walked into. (a) Add the **Fournux/Tyria-Extractor** row to `PLAN.md` §6.1's derivation register — it is MIT, mirrored, cited across 8+ study docs, and **has no row**; §6.1 starts at `PLAN.md:1061` with 16 rows and `PLAN.md:33` is the *prior-art landscape table*, which grants nothing. (b) Fix `toolkit/content.py:93-96`, which still declares *"verbatim assert expressions with their source path and line"* to be refused expression — `CLAUDE.md`'s REFINED 2026-08-12 clause reverses exactly that, and this entire study is built on single cited asserts. | (a) is a second-gate obligation: **no Fournux naming may be used until it lands.** (b) A cold session reading `content.py` first will re-run the 2026-08-12 over-refusal that cost 46 reverted citations. | nothing | **~1 hour.** Do it in the first commit. |
| **Q2** | `content/quests.toml` + `toolkit/authsrv/questdefs.py` (the extractor, modelled on `npcdefs.py`) + `toolkit/test_quests.py` + its `TESTS.md` entry. | The test declares a `checks.py` floor and asserts things the artifact can refute: **every** `enc_*` word list re-encodes to the varint form byte-identically; **every** `marker_map` is a real `areatable.py` row or exactly **888**; **every** authored `quest_id` is under `CHALLENGES` and not in the observed set. A quests.toml with a fabricated id goes red. | Q1b(a) if any Fournux naming is used | **~1 agent-day.** The loader change is **zero** — I verified a draft loads. |
| **Q2b** | *(Only if Q0 is green and the owner wants authored names.)* Write our own quest-name string into the owner's own archive with `toolkit/mapdata/textwrite.py`, commit the bare id. | `textwrite.py`'s own guards (refuses `C:\gw` and `vault/dat_study`) hold; an empty merge is byte-identical; the name appears on screen. **This tool already exists, is tested, and has 188 authored skill names on a retail screen behind it** (`TESTS.md:473`, `:508`). No lane in the recon found it. | Q0 | **~1 agent-day + 1 run.** |

**Q1 LANDED 2026-08-16, and it moved more than a column of names.** Twelve opcodes named, one RENAMED, four deliberate abstentions each carrying what would settle it. The evidence for eleven of the twelve is the FRAME BUS, and it was made refutable before it was used: the pairing was PREDICTED from FINDINGS §1.6 and §2.1 -- structurally, "the two adds share an id, the two text-fills share an id, the three marker ops do not" -- and then read out of the bytes, **11 of 11**. It is committed as `toolkit/clientscan/framebus.py` with `test_framebus.py` behind it, so the `why` on every row is reproducible by RUNNING; a measurement that lives in a scratch script is the same debt §7.9 already names for the codec. **The acceptance criterion worked as written**: naming CMSG `0x0014` made `test_dispatch.py` §7 go red before the `DROPPED_ON_PURPOSE` row landed. **And it retired an open question** -- `0x004E` VICTORY_BANNER → QUEST_COMPLETE_PANEL, because its body posts into the band `GmQuestComplete` subscribes to, which is the "nothing static will substitute" §7.6 ruled out while half the join sat in its own document. [FINDINGS.md](FINDINGS.md) §9.

**Q1b(b) is done; Q1b(a) is NOT.** `toolkit/content.py` no longer calls a single cited assert refused expression, and `PLAN.md` §7 Q3's REFUSED bullet gained a forward pointer to its own refinement -- the dated ruling text itself was left alone, because a decision record is supposed to say what was decided that day. **The Fournux/Tyria-Extractor row is still missing from §6.1**: `PLAN.md:33` is the prior-art landscape table and grants nothing, `:700` is prose, and the register at `:1061` has no row. It is a second-gate obligation and it has been open since 2026-08-13.

### Tier 2 — server dispatch, one client run each (NEEDS OWNER GO-AHEAD; batch one go-ahead over the set)

| Rung | What it is | Acceptance criterion (can go red) | Depends on | Cost |
|---|---|---|---|---|
| **Q3** | Answer `GAME_CMSG 0x0012` with `GAME_SMSG 0x004C` built from a TOML row. Closes `test_dispatch.py:110-114`'s recorded drop. | The quest-log **detail pane** shows our description. Red if the pane is empty, or if `0x0054` (objectives) is a silent no-op because we sent it before `0x004C` — the client's own gate at `0x0080F9CD` makes that failure look exactly like "the client ignored us". **Watch for it: ArenaNet itself trips it twice in the corpus.** | Q0, Q2 | **~half a day + 1 run.** |
| **Q4** | **Answer `0x0039` INTERACT with `0x0080` + `0x0081`.** This is the gate the whole subsystem sits behind, and §6 shows it is not blocked. | An NPC dialog **window opens** on screen when the player clicks the giver. Red if nothing opens, or if the window opens attributed to the wrong agent. | Q1 | **~half a day + 1-2 runs.** |
| **Q5** | Accept: decode `0x003B` as `0x800000 \| (quest_id<<8) \| code`, answer code `1` with `0x0049` from the quest row. Closes `test_dispatch.py:127-130`. | The player clicks *accept* in a window we opened and **their own quest appears in their own log**. Red if the id decode misses, or if the accept arrives with a code we did not model. | Q3, Q4 | **~half a day + 1 run.** |
| **Q6** | Instance-load replay: on every new game connection, one `0x0050` per held quest, `0x0051 [(inf,inf), 0, 888]` to clear stale markers, one `0x0053` to re-arm the active quest. | Walk through a map transition and the quest log **survives**. Red if it empties — which is what happens if you skip this. Second red: **do not bulk-restore with `0x0049`** — its body writes `charContext+0x528` (`mov [ebx+0x528], ebx` at `0x0080F20B`), so the last quest pushed silently becomes the active one. `0x0050` does not touch it. | Q5 | **~half a day + 1 run.** |
| **Q7** | Turn-in: `0x003B` code `7` → `0x0052` (twice, as ArenaNet sends it) then `0x004A`. | The quest **leaves the log** on turn-in. Red if it stays, or if the double remove turns out to be a party artefact rather than the protocol. **No reward is granted at this rung and the acceptance criterion must not claim one** — see §6. | Q5 | **~half a day + 1 run.** |

### Tier 3 — the verbs, and R4c-1's bar

| Rung | What it is | Acceptance criterion (can go red) | Depends on | Cost |
|---|---|---|---|---|
| **Q8** | The remaining five verbs as reusable server behaviours: kill-count, item-collect, area-trigger, escort, timer (`studies/presearing/MANIFEST.md:696-709`). | Each verb advances an objective and updates the log via `0x0054`. **Kill-count needs the objective-text placeholder** (`"… [6…0] remain."` is live substitution, not a static string). Red per verb. | Q3–Q7 | **~1 agent-day each for four; escort is a week and needs ally pathing and a fail state.** |
| **Q9** | **R4c-1's actual bar**: two mandatory quests completable end to end, six of six verbs. | `PLAN.md:589-591`: *"2 of 2 mandatory quests completable, 6 of 6 quest verbs implemented"*, both at 0 today. **Both mandatory pre-Searing quests are dialogue-verb quests**, so the whole quest half of R4c-1 turns on Q4 and Q5, not on any verb being hard. | all | **Owner call on what "mandatory quests" means — see §5.** |

### Which lane owns what

**Agent-farmable, no owner, no client:** Q1, Q1b, Q2, Q2b's authoring half, Q8's desk work. Estimate these and expect to be wrong by 15–100× the fast way.

**Needs the owner, and the estimate is honest:** Q0, and one run apiece for Q2b, Q3, Q4, Q5, Q6, Q7. That is **seven runs and one go-ahead batch**. Everything else is throughput, and throughput has never been this project's constraint.

**Needs a live capture campaign against ArenaNet (a separate, heavier decision):** the completion/reward family. See §6.

---

## 5. The provenance boundary, per column

The gate's boundary is **MEASUREMENT vs EXPRESSION** (`CLAUDE.md`, owner's ruling 2026-08-11, `PLAN.md` §7 Q3). Applied to this schema:

### MEASUREMENT — permitted in bulk, per row, extractor named, build/capture recorded

| Column | Why it is measurement |
|---|---|
| `quest_id` | An id. Read off ArenaNet's own wire. |
| `enc_location`, `enc_name`, `enc_npc` | **Lists of u16 code units — string *references*, not strings.** This is the repo's governing pattern (`model_id = 419, name_string_id = 2519`) and `vault/content/npcs.toml` already stores exactly this shape. |
| `marker_x`, `marker_y`, `plane`, `marker_map`, `home_map` | Coordinates and ids. |
| `flags` | A bit field. |
| The 52-byte entry layout, the `0x34` stride, `charContext+0x52C`/`+0x528`, `CHALLENGES = 1465` | Offsets, strides, addresses, bounds — the ruling names all four. |

Conditions, and `toolkit/content.py` enforces two of the three: the **extractor must exist in this checkout** (`:265-287`), the **build must be recorded** for `client-table`, and **provenance is per row**, which a human still has to read.

### EXPRESSION — refused, and no `extractor` field makes it loadable

- The **resolved text** of any of those ids. The words. `enc_name = [0x1703, 0xA86E, 0x9E9B, 0x4C82]` is permitted; whatever those four words spell is not, and must never be written next to them as a comment.
- Any quest description, objective or reward blurb of ArenaNet's, transcribed from a capture.
- **A safety property worth stating, because it cuts the other way from how it reads:** ArenaNet *does* inject literal UTF-16 into `0x004C` — I dumped it and it decodes to the player's own character name inside a `%str1%` template. That literal is the **player's** name substituted into a template, not ArenaNet's prose. ArenaNet's actual quest text is entirely behind encrypted ids: `textrec.py 5635` (quest 80's name id) returns `None`. **ArenaNet's quest words are not present as text anywhere in our capture corpus and cannot be transcribed by accident.** An implementer reading "ArenaNet sends literal UTF-16" could reasonably conclude the opposite.

### INVENTED — ours, no gate at all

Our quest ids, our `description` and `objectives` prose, every field under `[quest.X.server]` — verbs, giver bindings, prerequisites, rewards. `source = "invented"` and nothing more is required.

### The two routes, and which is better

**Route A — reproduce ArenaNet's quests.** Needs the RC4 key to read the name and description, so that we can then… not commit them. The key is **NOT FOUND** after 17 refuted readings from the archive side (`studies/textrec/FINDINGS.md`) and 13 more from the wire side, against two null controls, none beating the null. It is the expensive route to the forbidden answer.

**Route B — write our own quests.** Judged **clearly better**, and not by a small margin:

1. **No transcription risk exists at all.** Our words never pass through ArenaNet's.
2. **Description and objectives are 128 code units each and can hold real authored prose.** Our codec round-trips ~125 characters through `0x004C` and `0x0054` today. *(RECONSTRUCTION — that is our own components agreeing; no literal has ever been sent to a client, and ArenaNet always frames one as `0x0BA9 0x0107 <text> 0x0001`, which `codec.py:352` does not add. Q3's acceptance criterion is what tests it.)*
3. **The 8-unit name field has a solved answer nobody in the recon found.** `toolkit/mapdata/textwrite.py` merges an authored string into a plain text record in the owner's own archive, with write guards refusing `C:\gw` and `vault/dat_study`, an empty merge asserted byte-identical, and a stated provenance position: *"The strings are ours. Nothing here reads ArenaNet's text."* The precedent already shipped — 188 authored skill names on a retail screen (`TESTS.md:508`). Commit the id, resolve the string at run time, exactly as the rule says.
4. The **six verbs** are the reusable part, and they do not care whose quest runs on them.

**The consequence the owner has to rule on:** `PLAN.md` §3.2's R4c-1 bar says *"2 of 2 **mandatory** quests completable"*, and the mandatory two are ArenaNet's (a profession test, then A Second Profession). Under Route B those two would be reproduced **by mechanism with our own text** — same verb, same gate, same server behaviour, different words. That is either exactly what the bar meant or a weakening of it, and only the owner can say which. **Name the ruling in §3.2 rather than letting the ladder answer it by default.**

---

## 6. What would have to be true that isn't

Sorted by whether it is genuinely **BLOCKED** or merely **EXPENSIVE**. `CLAUDE.md` records twice that this repo has scored work impossible when it was only costly, and `PLAN.md` §7 Q6 permits a native C/C++ toolchain outright. The most important entry below is the first.

### The one that was scored BLOCKED and is not: the INTERACT reply

`test_dispatch.py:127-130` gates `0x003B` behind *"Handle it when INTERACT gets a reply"*; `authsrv.py:5082`'s comment defers to *"an NPC-service study"*; three recon lanes reported the reply's shape as not existing anywhere in the repo. **It exists, it is two opcodes, and both are already in our corpus and already decoded.**

I derived the client half independently:

- **`GAME_SMSG 0x0080`** → handler `0x0091E750` → body `0x00811740` in `ChCliApi.cpp`. It **appends** its one `string16` into an array at `charContext+0x2C, +0x14`, bounded by the count at `+0x1C` (guarded by `Array:587 index < m_count`). It is a text **accumulator**, one line per message.
- **`GAME_SMSG 0x0081`** → handler `0x0091E770` → body `0x008117B0`. It builds `{1, agent_id, text_ptr}` where `text_ptr` is *that same buffer*, **posts UI frame message `0x100000A6`** via the post helper `0x00633D70`, then **zeroes the count** at `+0x1C`. It is the **flush**, tagged with who is speaking.
- Frame `0x100000A6` has exactly **one subscriber** (`0x004ECEAF`, `call 0x00633BD0` — the subscribe helper) and two publishers, one of which is `0x008117FC`, i.e. the `0x0081` body itself.

And the wire half agrees, from ArenaNet's own traffic in `20260807T143055`:

```
  24.259  c2s 0x39 INTERACT  [_, 99, 0]
  26.816  s2c 0x80 [str<10u>]        s2c 0x81 [99]      <- dialog opens, agent 99
  27.679  c2s 0x3b  qid 80 code 3
  27.719  s2c 0x80 [str<43u>]        s2c 0x81 [99]      <- the OFFER text
  28.147  c2s 0x3b  qid 80 code 1
  28.179  s2c 0x49 QUEST_ADD [80, ...]                  <- accepted
  28.181  c2s 0x12 REQUEST_QUEST_INFO [80]
  28.241  s2c 0x4c [80, str<43u>, str<10u>]
  28.43   c2s 0x39 INTERACT  [_, 99, 0]
  28.479  s2c 0x80 [str<10u>]        s2c 0x81 [99]      <- 49 ms, a tight interact->reply pair
```

**The clincher, and it is a check that could have failed:** the `0x0080` string at 27.719 begins `1706 F80F ACBB 4FA2 010A 0BA9` — **byte-identical to the description field of the `0x004C` at 28.241**. The dialog text and the quest description are the same string. That is a join across two message families and two artifacts, and it makes the naming **CORROBORATED** (frame-bus disassembly × live wire), not a wire correlation.

Both are unnamed in `schema/messages.json` **and** `schema/overrides.json`. Neither has ever been sent by our server. **Dialogue — the verb that gates both mandatory pre-Searing quests, and therefore the entire quest half of R4c-1 — is EXPENSIVE (rung Q4, half a day and one run), not blocked.**

### Genuinely BLOCKED, and it blocks the thing we do not want

| Blocker | Owned by | Test that would clear it |
|---|---|---|
| **The 64-bit RC4 key.** ArenaNet's quest names and descriptions are unreadable: 44 of 44 name/NPC slots resolve to encrypted records, and 30 key constructions across two arcs have failed against null controls. | `studies/textrec/` | Disassemble `TextParser.cpp` at `0x7CC570`/`0x7CCB50` directly. The wire now supplies **known-good input** — a captured coded string with a known trailing varint — so the parser can be traced against a concrete example instead of swept. **But note this blocks only Route A**, and Route A ends at content we are forbidden to commit. Deprioritise it. |

### EXPENSIVE, and the cost is a live capture campaign

| Gap | Why | What it would take |
|---|---|---|
| **The whole completion and reward half.** `0x004E`, `0x006C`, `0x0096`, `0x0097`, `0x00FA/0x00FB` have **zero occurrences** across all 12 keyed live connections — I confirmed the absence. The operator never completed a mission. `GmQuestComplete.cpp` is a **3D scene with a model, a light and animation sequences**; a completion we trigger will try to load a model file, and if we have not staged one the failure will look nothing like a protocol bug. | The corpus has a hole, not a mystery. | **One narrated live capture in which the operator completes a mission**, under `RUNBOOK.md` §"Capturing a live session" and the behavioural rule. Nothing else recovers it. Until then, **Q7's acceptance criterion must not claim a reward.** |
| **Whether the `0x003B` service families other than quest dialogue ever reach the wire.** All 22 captured selects carry high byte `0x00`; merchant/skill-unlock/item-unlock/hero-unlock are inferred from client code only. | Bounds how general Q4's dialogue implementation needs to be on day one. | The same capture. Visit a merchant. |
| **A decline code.** No `0x003B` value in the corpus produces a refusal — the operator never declined. Codes `1` (accept) and `7` (turn in) are OBSERVED **by consequence** (5 of 5 and 3 of 3); `3` produces no reply (2 of 2); `4` produces an objectives update once. | | The same capture. Decline something. |

### EXPENSIVE and mislabelled as blocked: escort

`studies/monsterai/FINDINGS.md` establishes that **ArenaNet's AI as a mechanism** — the decision function, its inputs, its tick — is not recoverable from the client or any capture campaign. That is a statement about reproducing *ArenaNet's* AI. It says nothing about whether **we** can write an escort NPC that walks a path and has a fail state, on our own server, with `source = "invented"` doing exactly the job it exists for. Escort is a week of work and will not match retail. It is not blocked, and scoring it blocked would refuse work the finding never forbade.

### Small, cheap, and real

- **`toolkit/contentids.py` still clears a pair the client will refuse** (`PLAN.md` §8, UNFIXED). Not a quest blocker, but any quest rung that installs content inherits it.
- **`asserts.py` misses a fourth shape.** 13 tail-call sites image-wide, and one of them is the assert that fixes `QUEST_TYPE_MISSION == 1`. Worse than advertised: the tool's own `~370-site` shortfall counts only `call rel32`; these are `jmp rel32` and sit **outside** it. Every "no assert names X" negative anywhere in this repo is a floor computed by a scanner blind to this shape.
- **Quest id headroom is three, not a high band.** `UiCtlWebLink.cpp:576` `challengeId < CHALLENGES` compiles to `cmp edi, 0x5b9; jl` at `0x00884131` — **CHALLENGES == 1465** on build 38797, measured this session. The highest id in the corpus is 1462. There is no safe high band to author into. *(The bound is in the web-link control, so whether the quest log enforces the same one is UNVERIFIED — but the advice to "author well above ArenaNet's range" is refuted either way.)*
- **Build drift.** Every binary number here is 38797. The owner's live install runs **38833**. Frame ids and struct offsets probably did not move — and "probably" is what the VA-drift rule exists to refuse. Budget a re-run before anything ships against 38833.

### The corpus caveat nobody joined up

Quest id **1462** appears eight times in our live captures. GWW identifies id 1462 as **"Getting Started in Guild Wars"**, a **Reforged Mode** tutorial quest added 2026-05-27, visible only to characters opted into Reforged Mode. **The entire live quest corpus was captured on a Reforged-opted character.** The id→name binding is CORROBORATED (our wire × the wiki, two lineages, and five of the seven corpus quest ids resolve to named GWW pages); the Reforged gating is UPSTREAM (GWW, one witness). This does not invalidate the protocol readings — the instance-load replay shape, the flag gates, the marker sentinel are all structural. It does mean **"ArenaNet's server does X" should read "ArenaNet's server does X for a Reforged-Mode character"** wherever a reward, a text template or a quest set is involved, and it is the correct caveat to carry into `FINDINGS.md`.

---

## 7. Killed — tempting wrong answers, what killed them, and what they would have cost

The recon produced seven lanes and three adversarial passes. These are the answers that looked right and were not. Recording them because the next cold session will find them just as attractive.

| Killed | By what | What it would have cost |
|---|---|---|
| *"The quest frame band is ten ids, `0x1000014C..0x10000155`, and QuestTaskTracker subscribes to all ten"* | Disassembly. The subscribe run continues to `0x0057CC6A` — **seventeen** ids, `0x1000014C..0x1000015C`, uninterrupted, and the publisher block is twenty. Two independent verifiers reproduced it. | The truncation was the stated reason for believing the band is quest-shaped, and it silently excludes `0x156..0x15C` — where `GmQuestComplete`'s five ids and the whole completion half live. |
| *"The subscribe helper is `0x00637BD0`, and GmQuestComplete uses a different one"* | rel32 arithmetic: `0x0057CBA1 + 0x000B702F = 0x00633BD0`. I hit the same value independently from the `0x100000A6` scan. There is **one** helper, used by QuestTaskTracker, QuestLog, GmQuestComplete and the Compass alike. | A fabricated two-API distinction in the middle of the frame-bus model. |
| *"Fournux/Tyria-Extractor has a `PLAN.md` §6.1 derivation-register row at line 33"* | `PLAN.md:33` is the **prior-art landscape table**, which grants nothing. §6.1 begins at `PLAN.md:1061` and its 16 rows contain no Fournux entry. | Adopting an upstream's per-slot naming through an ungated second gate — precisely the `gwdat.py` failure the register was built to prevent. The lane that made the error simultaneously wrote *"record the Fournux row before any of its naming is used."* |
| *"Do not plan to patch Gw.dat for quests; the honest name path is borrowing one of ArenaNet's existing plain string ids"* | `toolkit/mapdata/textwrite.py` exists in this tree, committed, tested, guard-railed, with 188 authored skill names on a retail screen behind it (`TESTS.md:473`, `:508`). Seven lanes missed it. | The entire quest-naming story reduced to picking words out of ArenaNet's vocabulary. Nothing in the plain set spells "Bandit Raid". |
| *"The `0x003B` code semantics cannot be derived from the wire alone"* | Consequence, on the same corpus that lane read: code `1` is followed by `0x0049` **5 of 5**, code `7` by `0x0052`×2 + `0x004A` **3 of 3**, across five independent quest ids. | A live capture campaign budgeted to recover something already on disk. *(The residual gap is real and narrower: no **decline** code has ever reached the wire.)* |
| *"Nothing in this repo has a shape for the INTERACT reply"* | `GAME_SMSG 0x0080` + `0x0081` — see §6. Both already in the corpus, both already decoded, the client half traced to frame `0x100000A6`. | The whole dialogue verb, and therefore R4c-1's entire quest bar, scored as blocked behind an unknown. This is the single largest correction in the study. |
| *"Why `0x0049` draws no compass marker is NOT FOUND; disassemble `CompassQuestEffect.cpp`"* | Not killed — **demoted**. The probe sent `plane = 148` and `home_map = 0`, values ArenaNet never sends (n=10: plane ∈ {0,26}, home_map ∈ {146,148}). Two untested hypotheses precede any disassembly. | A disassembly session for what may be a malformed probe. Q0 tests it for free. |
| *"Carry `quest_type` as an integer 0/1/2 in `content/quests.toml`"* | **No quest message on the wire carries `questType` at all.** The client's `questTag` is 8 bytes; every quest message addresses a quest by a bare u32 that is the log entry's first dword. How the UI synthesises the tag is unrecovered. | A fabricated column deciding which UI class renders our quests, with no server-side way to set it. *(And `QUEST_TYPE_CHALLENGE == 0` vs the client's own noun for a quest-log row — `challengeSortArray` — is a live CONTEST, not a settled reading.)* |
| *"Do not send `0x004C` unsolicited on first add; it is a pull, not a push"* | Quest 1462 at `t=29.197`: `0x0049`, `0x0054`, `0x004C` and `0x0051` all arrive **unsolicited**, mid-session, and the client sends `0x0012` anyway 17 ms later. | A rule stated universally from a corpus showing both behaviours. What is actually mandatory is the **responder**: the client asks in 4 of 4 accepts regardless. |
| *"Author Rurik quests well above ArenaNet's occupied id range"* | `CHALLENGES == 1465`, measured this session from `cmp edi, 0x5b9` at `0x00884131`. The corpus maximum is 1462. | A retail assert on the first authored quest. |
| *"`studies/smsg` corroborates the Second Profession gate from live wire data"* | What was measured is a 64-of-136 zero rate on a profession field. Reading that zero as *"has not yet done A Second Profession"* is the same wiki-sourced belief the other document used. **Two documents sharing one upstream belief is one witness counted twice.** | The exact failure `CLAUDE.md` names about `schema/messages.json` and OpenTyria, in a new place. |

**Where the verifiers disagreed with each other, and it is unresolved:** whether the compass needs separate work at all. One pass argues the compass subscribes to six quest frame messages from one contiguous function and therefore *"needs no separate work"*; two others carry the measured half-refutation from `studies/minimap` (a `0x0049` send drew no starburst). Both argue from real evidence. Q0 settles it in one run, which is why it is Tier 0 and not a Tier 3 risk.

---

## 8. The recommendation

**Next session: run Q0 — one line in `probes.py:2467`, one caged loopback run — and if it is green, spend the session on Q1 + Q1b + Q4, because the INTERACT reply is `0x0080` + `0x0081`, it is half a day, and it is the gate under R4c-1's entire quest bar.**

**What NOT to do:** do not chase the RC4 key (it is the expensive route to content we are forbidden to commit); do not disassemble `CompassQuestEffect.cpp` before Q0 corrects the probe's two out-of-distribution fields; do not budget a live capture campaign to recover the `0x003B` code semantics, which are already on disk; do not write a `quest_type` column, which no wire message can set; and do not use a line of Fournux's naming until its `PLAN.md` §6.1 row lands.
