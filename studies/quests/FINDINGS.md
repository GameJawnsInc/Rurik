# Quests: what the client models, what the wire carries, and how close authoring actually is

**Study arc:** `studies/quests/` · **Date:** 2026-08-15 · **Method:** seven recon lanes (repo knowledge inventory; client assert/disassembly reconstruction; the wire opcode family; where quest data lives; the capture corpus; GWW as an independent lineage; the content-store substrate), then three adversarial verification passes run against the artifacts rather than against the lanes' prose, then this synthesis. Every disputed number below was re-measured for this document. No client, game, or server was launched. `C:\gw` was untouched.

**Client image on every static claim:** `vault/client/2026-07-29_221c13772c7a/Gw.exe`, **build 38797**, the pinned pristine copy (`toolkit/clientscan/pinned.find()`). Every VA is that image's, and **none of it has been re-checked against 38833** — see §7.

**Capture corpus on every wire claim:** the complete live corpus — 6 stamped directories under `vault/captures/live/`, of which **3 carry decrypted game channels** (`20260807T133758`, `20260807T143055`, `20260810T235916`), **12 game connections, 971 c2s GAME_CMSG and 22,524 s2c GAME_SMSG**, `cmsgstream.frame_report` residual **0** on 12 of 12. All 27 live-origin files sit under `captures/live/` and nowhere else (`toolkit/origin.py`).

---

## 0. What this arc settled, and what it did not

**Settled: the quest subsystem is a bounded, fully-readable protocol, and we now have all of it.** Eleven `GAME_SMSG` opcodes (`0x0049`, `0x004A`, `0x004B`, `0x004C`, `0x004D`, `0x004E`, `0x0050`–`0x0054`) and four `GAME_CMSG` opcodes (`0x0011`, `0x0012`, `0x0013`, `0x0014`) form one family whose bodies all live in `ChCliApi.cpp` and all operate on one 52-byte array the client itself names `challengeSortArray`. The struct closes to the byte. The quest lifecycle — offer, accept, describe, mark, advance, turn in, replay on map change — is on the wire in order, twice, and is a directly copyable script. Fifteen opcodes carry `name: null` in `schema/messages.json` today and every one of them can be named off this pass.

**Settled: the client holds no quest table at all.** Ten source files carry "Quest" in their path and all ten are UI (`P:\Code\Gw\Ui\Game\`). There is no `ChCliQuest.cpp` beside `ChCliSkill.cpp`, no `ConstQuest.cpp` among 39 asserting `Gw\Const\` modules, and a byte scan of the whole PE for `s_quest`, `ConstQuest`, `questClientData`, `QuestData`, `arrsize(s_quest`, `CHAR_MAX_QUEST` and `MAX_QUEST` returns **zero** with `s_missionClientData` as a working positive control at 1. Quest data is server state. That is the whole answer to "who owns quests", and it means authoring one is a content-TOML plus server-message problem, not an archive problem.

**Settled, and this is the finding that changes the plan: the "hello world" is closer than any lane thought, and the thing every lane called the blocker is not one.** All seven lanes scored quest dialogue as blocked behind an unknown reply to `GAME_CMSG 0x0039 INTERACT_AGENT` — `toolkit/authsrv/test_dispatch.py:127-130` says so in the code, and lane G reported "nothing in this recon found a shape for that reply anywhere in the repo". One query over the corpus we already own narrows it to two opcodes with trivial shapes. **`GAME_SMSG 0x0080` (one `string16(122)`) is the dialog text and `0x0081` (one `agent_id`) is whose dialog** (§2.5). Both are already decoded by our codec and both are sitting in `vault/captures/live/`. Dialogue — the verb that gates *both* mandatory Pre-Searing quests — is EXPENSIVE, not BLOCKED. That distinction is the failure CLAUDE.md records twice, once for the provenance gate and once for the compiler carve-out, and it happened again here.

**SETTLED 2026-08-15, BY RUNNING IT — a quest name WE chose renders in a real client.** This section said the cheapest experiment in the arc was "send `0x0049` with `enc_name = [0x3D64]` and see whether the log renders **Ascalon**", and that it was unrun. It ran. **The quest tracker reads `Ascalon:`** — green text beside the quest icon, under the level bar, where the frame before the message has nothing at all. Probe `quest_name` (`toolkit/authsrv/probes.py`), build 38833, map 449, loopback, our DH, caged; capture `vault/captures/harness/20260815T200632`, frames `hold002` (before) against `hold012` (after), **8,085 of 218,400 px differing in the tracker box, worst channel delta 247**. — OBSERVED.

**So the whole chain is ours end to end**: a u16 we put on the wire → the client's own id→text seam at `0x007C93F0` → a rendered glyph. §3.2's decode-side reading is confirmed from the *encode* side against a real client, which is the direction nothing in this repo had ever tested. **The naming half of quest authoring is done, and the problem reduces to "which string id".**

**Two corrections fall out of the same frame, and both were load-bearing.**

- **`studies/minimap/FINDINGS.md:721`'s reading of the `?` is REFUTED.** It recorded the icon as *"the empty name string we deliberately sent"*. It is not: the `?` is the quest **icon** and it is still there in this run, *beside* the name. What the empty strings produced was **no text at all**. Anyone reasoning from "the `?` is the name" would conclude the name field renders as a literal glyph and stop looking.
- **The client asked us for the description, unprompted.** `c2s 0x8012 REQUEST_QUEST_INFO` arrived seconds after our `0x0049`, and our server has no arm for it (`test_dispatch.py:110-114`'s recorded drop, which the log names). That is §2.3's *"the client asks in 4 of 4 accepts regardless"* reproduced on **our** wire against a quest **we** invented — the strongest available corroboration that the client took the entry as a real quest rather than tolerating a malformed one.

**SETTLED 2026-08-15, SAME DAY: our own PROSE renders too, and the bare/framed question was answered by a crash.** Rung Q3 ran (`probes.py`, `quest_description`; build 38833, map 449, loopback, caged). The server now answers `GAME_CMSG 0x0012` with a `GAME_SMSG 0x004C` built from `content/quests.toml`, and the client's Quest Log shows **our sentence**: *"Speak to the gate guard, then return to me."* under *Quest Summary*, with our objective *"Return to the guard."* above it and repeated in the tracker. — OBSERVED, capture `vault/captures/harness/20260815T204539`.

**The control arm killed the client, and that is the better half of the result.** The same probe first sent a second quest whose description was the identical sentence with **no framing**. It did not merely fail to render:

```
Assertion: (codedString[0] & ~WORD_BIT_MORE) >= WORD_VALUE_BASE
P:\Code\Engine\Text\TextApi.cpp(585)                     build 38833
```

`asserts.py --grep WORD_VALUE_BASE` finds that same expression at `0x007c9b1d`, with five more sites across `TextParser.cpp` and `TextEncode.cpp`. The crash stack carried our sentence verbatim as UTF-16 (`S.p.e.a.k. .t.o. .t.h.e. .g.a.t.e...`) beside frame id `1000014f` and opcode `0000004c`, so the bytes arrived intact and **the first word is what it refused**. §3.2's marker/varint rule — derived from `TextParser.cpp` and confirmed 66/66 against ArenaNet's wire — is now **confirmed by the client's own assert, which names both constants**. A literal run must be introduced by a word ≥ `WORD_VALUE_BASE`; `toolkit/authsrv/questdefs.py` refuses to build one that is not, citing this crash. — OBSERVED.

**Three things fell out that no lane predicted.**

- **`0x004C` carries the objectives too**, so nothing needed `0x0054`: its second `string16` rendered as the bulleted objective and in the tracker. §2.2's warning that `0x0054` is a silent no-op before `0x004C` stands, and this run simply never had to reach it.
- **The client composes the heading itself.** The pane reads *"Ascalon (Kamadan, Jewel of Istan):"* — our name id plus **the map's own name, which we never sent**. The client resolves that from the instance, so a quest's displayed heading is not wholly ours to author.
- **§1.4's grouping model is confirmed and one heading id is now named.** We sent `flags = 32` (`0x20`), and §1.4 reads `test al, 0x20 → sortCode 1` with heading string id `0x464` (1124). The quest appeared under **"Primary Quests"**. That is the flag→group→heading chain measured end to end from the wire to the glyph, and it means **we can choose a quest's log section from the server** by picking the flag bit. — OBSERVED.

**SETTLED 2026-08-15: `0x0080` + `0x0081` IS the NPC dialog window, and §2.5's naming is confirmed by sending it.** Rung Q4 ran (`probes.py`, `npc_dialog`; build 38833, map 449, `--enemy --practice-target`, caged). A dialog window opened carrying our line, titled **"Hatcher [Collector]"** — the client resolved the speaker's own name and title from the bare `agent_id` we put in `0x0081`. Capture `vault/captures/harness/20260815T211339`. — OBSERVED.

**The order prediction was confirmed in both halves, which is what makes it a measurement rather than a demo.** §2.5 read `0x0080`'s body as an accumulator that posts no frame message and `0x0081`'s as the flush that displays and zeroes the count. The frame taken between the two steps (`hold003`, after `0x0080` at t=6 s and before `0x0081` at t=10 s) shows **no window at all**; the frame after `0x0081` shows it. So the pair is not merely "two messages that produce a window" — the division of labour between them is as the bodies said. Sending `0x0081` first would show an empty window and discard the lines that followed, which is why the server arm sends every line before the flush.

**This closes the gate `test_dispatch.py` recorded on `0x003B`** — *"blocked behind `0x0039`: this server does not answer an interaction, so no window is ever open and no selection can be made"* — and it retires the framing in `authsrv.py`'s INTERACT arm that deferred to *"an NPC-service study"*. This arc is that study. **Dialogue was EXPENSIVE, not BLOCKED**, exactly as §6's killed table argued, and the whole distance from "scored impossible" to a window on screen was one corpus query and one probe.

**What Q4 did NOT settle, and it is the next rung rather than a caveat.** The server answers *any* interaction with *every* quest row's giver line, because there is no npc→quest binding column yet — `AUTHORING.md` §3's `[quest.X.server]` block is a proposal, not a schema. The window is real; **whose** window it is, is not yet modelled. And nothing here is a *choice*: `0x003B NPC_SERVICE_SELECT` is still unanswered, so the window has our text and no accept button behaviour. That is Q5.

**Q5, 2026-08-15: the server half is done; the CLICKABLE OPTION is not, and the arc now has a measured negative about where it comes from.**

**Done, and tested against ArenaNet's own dwords.** `GAME_CMSG 0x003B` decodes as §2.4 says — `questdefs.decode_service_select` turns `0x805003`, `0x805001` and `0x85B601` into (80, 3), (80, 1) and (1462, 1), with an encoder as its inverse and refusals for a clear tag bit or a set high byte. The server answers code `0x01` with `0x0049` from the quest row and deliberately answers code `0x03` with **nothing**, because ArenaNet's own server sends no quest-family reply to an offer (2 of 2). `test_dispatch`'s second recorded drop is closed. — OBSERVED for the decode, RECONSTRUCTION for the arm, which no client has yet exercised.

**NOT FOUND, and this is the useful part: the clickable option is NOT carried by the dialog string.** The hypothesis was reasonable and the corpus supported it — there is no server message between `0x0039 INTERACT` and the player's `0x003B quest=80 code=3`, and the two captured offer lines share the prefix `2AE6 F9CB E939 5DD2 010A` while differing only in one varint group (`3377 DF18 F3B0 201F` against `3375 FE11 D56F 2195`), which looked exactly like a quest slot.

**It is refuted by replay.** Sending ArenaNet's own ten words verbatim through our `0x0080`/`0x0081` pair at our own NPC renders the *same window* — the string resolves to a readable generic greeting ending in an invitation to talk, so those ids are **plain records, not encrypted** — and produces **no clickable option and no `0x003B`, across two runs with the click placed on the greeting's own last line**. Capture `vault/captures/harness/20260815T214832`; `NPC_SERVICE_SELECT` appears 0 times in the gamesrv log, and the only c2s opcodes in the whole session are the movement and housekeeping set.

So the varint group that varies between the two captured lines is **not** a quest id being handed to the option renderer. What it is remains open.

**What that leaves, in the order worth trying:**
1. ~~**The agent, not the string.**~~ **REFUTED 2026-08-15, and see below.**
2. **A message we are not sending.** Something earlier in the session may arm the NPC's option list; the corpus was searched only between INTERACT and the click, which is where the hypothesis came from and also where its blind spot is. Widen the window to the whole session and diff what precedes a giver interaction against a non-giver one.
3. **A marker we dropped.** The greeting rendered, so the framing is right, but a clickable run may need a marker the greeting does not contain — in which case the OFFER line at `t=27.719` (43 units, sent *after* the first click) is the one to replay, not the greeting.

#### Candidate 1 tested and REFUTED: the giver's own definition is not what arms the option

**OBSERVED**, `vault/captures/harness/20260815T222238`, build 38833, map 449, probe `quest_giver_def`. One variable against the `quest_offer` run: the speaker's definition. Everything else — the replayed ten-word greeting, the flush, the click positions — identical.

The three live givers' definitions, MEASURED by the interval join off `WORLD_CREATE_AGENT`:

| agent | t | model dword | definition | allegiance |
|---|---|---|---|---|
| 99 | 20.140 | `0x200005C8` | **1480** | `play` |
| 40 | 17.941 | `0x200005B3` | **1459** | `nonc` |
| 36 | 66.737 | `0x200005C1` | **1473** | `nonc` |

All three are `CHAR_CLASS_MONSTER_BASE | def` with `AGENT_KIND_NPC` — the same class and kind our own spawns already use — so the definition number is the only difference. The allegiances differ *between* givers, so allegiance is not the marker either.

**The definition took effect, and visibly.** Spawning agent 99 with definition 1480 changed the nameplate and the dialog window's title from `Hatcher [Collector]` to the guard's own name, resolved by the client from its own archive out of the `enc_name` ids in `vault/content/npcs.toml`. That is CLAUDE.md's "commit the id, resolve the string at run time" confirmed a second time, now for an NPC name rather than a quest name.

**And it changed nothing about the option.** Same two paragraphs, no clickable line, `NPC_SERVICE_SELECT` 0 times in the gamesrv log, and the session's c2s set is the movement and housekeeping opcodes only. **So a real giver's definition is not sufficient to arm a quest option**, and candidate 1 is dead.

**A hazard found the expensive way, and it is already documented in this repo.** The first version of this probe used definition **392**, from reading `536872392` as `0x20000188`. It is `0x200005C8`. Definition 392 was never defined by anyone, and creating an agent on it took the client down:

```
Assertion: index < m_count
P:\Code\Base\rtl\Array.h(587)                    build 38833
```

with `Arg:01880000` (0x188) and `Arg:00000063` (agent 99) on the create frame, and `Pc:00117bdb` rebasing to `0x487BDB` — the assert routine at `0x00487BC0`. `agents.npc_properties`' own docstring already says this: *"the definition index is a raw array index on the client, and creating an agent whose definition was never sent takes the client down on `index < m_count`"*. The failure was a bad number, not a new mechanism, and it reproduced a documented one. Two things follow: **push `0x0056`/`0x0057` before any create on a definition the client has not been told about**, and the `WORLD_CREATE_AGENT` model dword is `MONSTER_BASE | def` where the definition is the **low 16+ bits in decimal** — read the hex carefully.

#### Candidate 2 CONFIRMED, twice over: `0x009F` property 11 is the marker, and `GAME_SMSG 0x007E` is the option

Widening the scan from the INTERACT-to-click window to the whole session — the blind spot named above — found **two** messages, and they do different jobs.

**`GENERIC_VALUE 0x009F` property 11 is the quest-giver marker. OBSERVED.** It lands on 5 of 68 created agents in `:60935` and 9 of 88 in `:62994`, covers every dialog speaker in both, and takes exactly two values. The transitions fix their meaning against the quest lifecycle:

```
17.941  PROP11 agent 40 = 5                        map load, no interaction yet
28.179  QUEST_ADD 80      + PROP11 agent 40 = 4    accepted; 40 becomes turn-in
46.797  QUEST_REMOVE 80   + PROP11 agent 40 = 5    turned in at 40; back to 5
66.737  PROP11 agent 36 = 4                        quest 218 held, turned in at 36
```

**5 = has a quest to offer, 4 = turn one in here** — the green `!` and green `?`. RECONSTRUCTION for the two English words, OBSERVED for the transitions (2 of 2 in each direction). Confirmed on screen: sending `0x009F [11, agent, 5]` puts a green exclamation over the NPC's head (`vault/captures/harness/20260815T235047`). **This closes part of §7's open question about `0x009F`'s property enum, which the smsg pass left as "naming them needs a probe".**

**And it is NOT what makes an option clickable** — the probe was built to separate the glyph from the option and did: the `!` appeared and the dialog stayed plain text.

**`GAME_SMSG 0x007E` is the dialog option. OBSERVED, and the check could have failed.** Shape `[u8 kind, string16(128) label, u32 tag, u32]` from the client's own RECV descriptor and `schema/messages.json`, which agree. **The tag is the exact dword the client sends back in `0x003B` if that line is clicked**, and the refutable form of the claim is that no click can arrive unannounced:

> **22 of 22 clicks across both keyed sessions were announced by a prior `0x007E` on the same connection carrying the exact dword. Zero counterexamples.**

`t=26.816` announces `0x805003`; the player sends exactly that at `t=27.679`. `t=28.479` announces `0x85B603`; sent at `t=28.780`. `field1` takes 15,16,17,18,21,22,23 (an option kind, unnamed; quest offers use 18) and `field4` is `0xFFFFFFFF` in 37 of 37.

**ORDER MATTERS, and getting it wrong looks exactly like the message not working.** ArenaNet's burst is `0x0080` → `0x0081` → `0x007E`. The first attempt sent the option *before* the flush, into a buffer `0x0081` then zeroed; the window opened with our prose and no clickable line. `0x0081` opens the window; options are appended to an open one.

#### Q5's acceptance criterion is MET

`vault/captures/harness/20260816T000109`, build 38833, map 449 — the whole loop, every message ours:

```
s2c 0x0056/0x0057  def 1480          the giver's type
s2c 0x0020         agent 99          a body with its nameplate
s2c 0x009F [11,99,5]                 the green '!'
s2c 0x0080         our giver_dialogue from content/quests.toml
s2c 0x0081         flush -> the window opens
s2c 0x007E [18, "Accept: A First Errand", 0x85B701, 0xFFFFFFFF]
c2s 0x003B 0x85B701                  THE PLAYER CLICKED OUR OPTION
    NPC_SERVICE_SELECT quest 1463 code 0x01
s2c 0x0049         QUEST_ADD[1463] built from the content row
c2s 0x0012         REQUEST_QUEST_INFO -- the client asks, 1 of 1
s2c 0x004C         QUEST_DESCRIPTION[1463 template]
```

On screen: a quest log reading **Primary Quests → Ascalon** with an Abandon button, a Quest Summary carrying **our objectives and our description**, and a tracker line under the level bar. **This is the first authored quest in this project to exist in a retail client's quest log, and the first authored prose of any kind to reach one.** It also retires Q3's acceptance criterion in the same run — the detail pane shows our description, and `0x004C`'s `template` framing is confirmed on a live client rather than offline.

**Still open:** `0x007E`'s `field1` kind enum (7 values, none named), whether an option can be declined, and the turn-in half — `0x003B` code `0x07` is decoded and unarmed.

**Superseded: candidate 3** (replay the 43-unit offer line) is moot; the option was never in the dialog string.

~~**Remaining candidates are now 2 and 3 above**~~, and 2 should be done properly before 3: the earlier scan looked only at the window between `INTERACT` and the click, which is where the original hypothesis came from and also its blind spot. Widen it to the whole session and diff what precedes a giver interaction against a non-giver one. `0x004B` (bulk assign of the `+0x518` list, `array32[64]`) and `0x00FA` (`array32[32]`, once per session at map load) are the two load-time bulk assignments in the corpus that **carried empty arrays and therefore no evidence**, and a per-NPC available-quest list is exactly the shape either could have.

**Still not settled: the compass marker.** This run was on **map 449**, not 148, so it says nothing about §7.3 — map 148 cannot load at all right now (see below), and the marker coordinates are 148's. The free rider went unclaimed and §7.3's test is still open.

**Not settled, and it blocked this run first: map 148 is unloadable.** `contentids.py` refuses it, correctly — no client archive in the vault binds `0x1B97D` the way the server's `dat_study` copy does. Four run dirs hold it only under the bit-31 mid-replacement spelling; the 38833 copy binds it to a file 8 bytes larger, written by the terrain arc's allocation work. This is archive state, not a quest question, and it is why Q0 ran on 449.

**Not settled: ArenaNet's own quest prose.** The RC4 key that would decrypt quest names and descriptions out of `Gw.dat` is NOT FOUND (§3.3), which is a blocker for *re-using* their text and no blocker at all for authoring ours — and, usefully, it is why this arc cannot breach the provenance gate by accident.

**So: how close is authoring a quest?** A quest that *appears in the log with a name we chose*, that *answers the client's description request*, that *advances its objectives* and *can be removed* is four messages and one responder, all of whose shapes are measured and all of whose bytes exist in the vault. A quest that is *given by an NPC the player talks to* needs the `0x0080`/`0x0081` pair confirmed — a msghandler pass and one loopback probe. A quest that *draws a compass starburst* is genuinely open, but for a narrower reason than the repo currently records (§7.3). A quest that *completes with ArenaNet's reward panel* is out of reach until somebody completes a mission on a live capture: the entire completion half of the subsystem is **0 of 22,524** in the corpus.

---

## 1. The subsystem as the client models it

### 1.1 The module decomposition — ten files, all UI

**OBSERVED.** `srctree.py` reads **937** distinct `P:\Code\...` source paths out of build 38797. Exactly ten contain "Quest", and every one is under `P:\Code\Gw\Ui\Game\`:

| File | assert sites |
|---|---|
| `GmQuestComplete.cpp` | 29 |
| `Quest\QuestEntryGroup.cpp` | 10 |
| `Quest\QuestChallenge.cpp` | 9 |
| `Quest\QuestLog.cpp` | 8 |
| `Quest\QuestEntry.cpp` | 6 |
| `Quest\QuestList.cpp` | 6 |
| `Quest\QuestTaskTracker.cpp` | 6 |
| `Quest\QuestMission.cpp` | 5 |
| `Quest\QuestTask.cpp` | 3 |
| `Compass\CompassQuestEffect.cpp` | 1 |

**83 sites total, and that is a floor, not a census.** `asserts.py` prints its own shortfall — 19,758 sites read against an independent sweep finding 20,131 `call rel32` landing on the assert routine — and this arc found one of the misses *inside this very subsystem* (§1.3).

**NOT FOUND, with the search named:** there is no `Gw\Quest\` subsystem directory the way there is `Gw\Mission\Cli\` (12 files) or `Gw\Char\Cli\` (14). No `ChCliQuest.cpp`. No `ConstQuest.cpp` among the `Gw\Const\` modules, which do contain `ConstMission.cpp`. Searched with `srctree.py --under` for `Gw/Ui`, `Gw/Char`, `Gw/Const`, `Gw/Mission`, `Gw/AgentView`, `Gw/Net`, `Gw/Item`, `Net/Msg`, plus the whole-tree census. `srctree`'s own caveat applies: a linked translation unit emitting no `__FILE__` path is invisible to it.

**NOT FOUND:** `objective` and `bounty` as identifiers — `asserts.py --grep objective` and `--grep bounty` each return **0 sites**. The client's word for a quest sub-goal is **task**: `QuestTaskTracker:189 stepStr`, `QuestTaskTracker:210 taskDesc`, `QuestTask:71 codedText && codedText[0]`. Both zeroes are floors.

### 1.2 `questTag` — an 8-byte tag, and the client compares both halves

**OBSERVED.** `questTag` is `{int questType; int challengeCode}`. `QuestLog.cpp` builds a literal tag at `0x0057C2B8 mov dword ptr [ebp-8], 2` / `0x0057C2C2 mov dword ptr [ebp-4], 0xffffffff`, then compares both dwords and nothing else at `0x0057C2D4 mov ecx, [edi]` / `cmp ecx, [ebp-8]` / `0x0057C2DE mov eax, [edi+4]` / `cmp eax, [ebp-4]`. The `+4` offset is pinned independently by the assert `QuestEntryGroup:172 questTag.challengeCode < (ITEM_CODE_CHALLENGE_TERM - ITEM_CODE_CHALLENGE_FIRST)`, compiled at `0x0057FECE` as `cmp dword ptr [esi + 4], 0x7fffffff`.

**NOT FOUND:** any `questTag` field beyond those two. The string `questTag.` appears in assert expressions in exactly two spellings — `questTag.questType` (3 distinct strings, 9 sites) and `questTag.challengeCode` (1 string, 1 site). No `questId`, no `questTask`, no arrow form.

**The tag `{2, 0xFFFFFFFF}` is a real sentinel, not compiler noise** — OBSERVED. It is constructed twice (`0x0057C2B8` and again at `0x0057BE4B`/`0x0057BE53`), and questType 2 is exactly the switch case that maps to a NULL frame factory (§1.4).

### 1.3 `questType` — three values, two named, and the assert the tool cannot see

**OBSERVED. `QUEST_TYPE_CHALLENGE == 0.`** `QuestChallenge:197 QUEST_TYPE_CHALLENGE == questTag.questType` compiles at `0x0057E393` to `mov esi, [esi]` / `0x0057E395 cmp dword ptr [esi], 0` / `0x0057E398 je 0x57E3AE` — the assert is skipped when the field is zero. The site pushes `0xc5` (= 197), `edx = 0x00956834` (`P:\Code\Gw\Ui\Game\Quest\QuestChallenge.cpp`), `ecx = 0x00956868` (the expression). The identical pattern repeats for `QuestChallenge:416` at `0x0057E3F5`.

**OBSERVED. `QUEST_TYPE_MISSION == 1`, and the assert that proves it is invisible to `asserts.py`.** The string `QUEST_TYPE_MISSION == questTag.questType` sits at VA `0x00956A10` and is referenced exactly once. The bytes at `0x0057F17D` read `8B 06 5E 83 38 01 74 17 C7 45 08 51 00 00 00 BA E4 69 95 00 B9 10 6A 95 00 5D E9…` —

```
0x0057F17D  mov eax, dword ptr [esi]
0x0057F180  cmp dword ptr [eax], 1
0x0057F183  je  0x0057F19C
0x0057F185  mov dword ptr [ebp + 8], 0x51        ; line 81
            mov edx, 0x009569E4                  ; QuestMission.cpp
            mov ecx, 0x00956A10                  ; the expression
            pop ebp
            jmp 0x00487BC0                       ; the assert routine, TAIL CALL
```

`asserts.py --grep QUEST_TYPE` returns only the two `QuestChallenge` sites. This is the single strongest measurement in the arc and all three verification passes reproduced it byte for byte.

**OBSERVED, and it is a tool finding worth propagating past this study: `asserts.py` has a fourth shape it does not scan.** The regex `\xc7\x45\x08(....)\xba(....)\xb9(....)\x5d(\xe9|\xeb)` over `.text` returns exactly **13** sites with a `P:\`-rooted file operand — `Handle.h` ×6, `GmTrade.cpp:1122`, **`QuestMission.cpp:81`**, `VnItem.cpp:52`, `agint.h:929`, `AgMap.cpp:93`, `AgTimer.cpp:123`, `UiCtlDistrict.cpp:2217`. Two independent verifiers reproduced the same 13-site list.

**Corrected from lane B's original wording, by a verifier who counted the two sweeps separately:** these 13 are **not** a slice of the tool's self-reported ~370-site shortfall. That shortfall is an `E8 call rel32` sweep (20,131 sites). These are `E9 jmp rel32` (13 sites), outside it entirely. **The true gap is at least 383, and the tool's own printed shortfall is itself a floor.** Any "no assert names X" conclusion in any lane of this repo should be re-run against the tail-call shape before it is believed.

**OBSERVED. A third `questType` value, 2, exists, and its name is nowhere in the image.** `QuestLog:167` (assert at `0x0057C2FA`) compiles to a `sub ecx, 0 / je` → `sub ecx, 1 / je` → `sub ecx, 1 / je` chain at `0x0057C2E6`, and `QuestLog:231` (`0x0057C38E`) does the same at `0x0057C37A`. Nine `No valid case for switch variable 'questTag.questType'` sites split 2/3 on case count: two see `{0,1,2}`, six see `{0,1}`, one sees `{0}`. No switch anywhere handles a fourth value.

**NOT FOUND, and refuse to fill it in:** the *name* of value 2. A whole-image ASCII regex for `QUEST_[A-Z0-9_]+` returns exactly two strings — `QUEST_TYPE_CHALLENGE` and `QUEST_TYPE_MISSION`. The value's existence is proven; its identifier is not in the binary. **Do not write `QUEST_TYPE_QUEST` into anything and call it measured.**

**CONTESTED — and this is a real contest the lanes did not name.** What value does an *ordinary* quest carry? Two readings, both from measurement:

- **Type 0 = ordinary quest.** The client's own noun for a quest-log element is `challenge`: `ChCliApi.cpp:4237 context->challengeSortArray.Find(challenge)`. The `GAME_CMSG 0x0012` sender at `0x0080DDD0` does `mov ecx, [eax+0x2c]` / `add ecx, 0x52c` / `call 0x008179F0` — it resolves the id in `challengeSortArray`. That message fires on the wire for quest ids 80, 1462, 218, 82 and 62, which are ordinary story quests on GWW (§5).
- **Type 2 = ordinary quest.** `QuestLog:167`'s factory gives type 2 a NULL frame class (`0x0057C309 xor eax, eax`), which fits an entry the `QuestEntry` base handles without a specialised subclass.

Nobody resolved it, and it matters: **lane B proposed a `quest_type` integer column for `content/quests.toml` on the strength of the enum being measured.** The enum is measured; the *semantics* are not, and — decisively — **no quest message on the wire carries a `questType` field at all** (§2.2). A `quest_type` column in a content row today would be pure invention with a measured-looking provenance label.

### 1.4 The UI class hierarchy and the quest log's own geometry

**OBSERVED.** `QuestLog:167` is a **frame-class factory** selector. Type 0 loads `0x0057DEE0` (a thunk `jmp 0x0057E1A0`, inside `QuestChallenge`'s assert range `0x0057DF33..0x0057E3FF`); type 1 loads `0x0057F150` (`jmp 0x0057EEE0`, inside `QuestMission`'s range); type 2 is `xor eax, eax`. All three converge on `0x0057C319 push edi / push eax` into `call 0x00612E40`.

**RECONSTRUCTION.** `QuestEntry.cpp` is an abstract base with at least three subclass hooks — `QuestEntry:286`, `:294`, `:298` all read `Must be handled by a subclass.` at `0x00580439`, `0x0058045F`, `0x00580477` — and `QuestChallenge`/`QuestMission`/`QuestEntryGroup` are the concrete classes. The class *names* are file names; no RTTI or vtable evidence was gathered.

**OBSERVED. The quest log has exactly four groups**, selected by a `sortCode` of 0..3. `QuestList:225 No valid case for switch variable 'sortCode'` (`0x0057DD98`) is the default of `0x0057DD03 cmp esi, 3 / ja` / `0x0057DD0C jmp dword ptr [esi*4 + 0x57DDA8]`, a 4-entry table. The selector is three flag bits of the challenge record: `0x0057DCB1 test al, 0x10 / je` → 0; `0x0057DCBB test al, 0x20 / je` → 1; `0x0057DCD2 mov esi, 2` / `0x0057DCD7 test al, 0x40 / jne`, else `mov esi, 3`. The `questType == 1` (MISSION) arm jumps straight to `0x0057DCB5 xor esi, esi` — **every mission is group 0**.

**OBSERVED. The four group headings are numeric string ids resolved at run time:** `0x463` (1123), `0x464` (1124), `0x11678` (71800), `0x465` (1125), each pushed into `call 0x007C93F0`. Group 0's heading additionally embeds one substring pulled from the mission client-data record at `+0x74` (`0x0057DD23 push dword ptr [eax + 0x74]`).

**OBSERVED. `0x007C93F0` is the client's own id→text seam** — a one-argument wrapper over the four-argument `0x007C9410`:
```
0x007C93F0  push ebp / mov ebp,esp / push 0 / push dword ptr [ebp+8] / call 0x007C9410 / add esp,8 / pop ebp / ret
```

**OBSERVED. The Quest UI holds coded text, never prose, and the client's own identifiers say so:** `QuestEntry:66 codedName` vs `QuestEntry:139 decodedName`; `QuestEntryGroup:409 decodedNameText`; `QuestChallenge:140 codedName`; `QuestMission:60 codedName`; `QuestTask:71 codedText && codedText[0]`; `GmQuestComplete:312 codedRewardsBlurb.Ptr()`; `GmQuestComplete:363 codedText` (×4 sites). This is CLAUDE.md's "commit the id, resolve the string at run time" confirmed out of ArenaNet's own vocabulary.

### 1.5 The completion panel — a 3D scene, not a dialog

**OBSERVED.** `GmQuestComplete.cpp` carries 29 asserts and they describe a scene: `:138 modelFileName`, `:142 !m_model`, `:155 !m_light`, `:171 sequenceCount >= 1`, `:242 rewardStart`, `:312 codedRewardsBlurb.Ptr()`, `:416 m_light`, `:525 m_model`, `:526 m_light`, `:535 completionNotesFrameId`, `:550 rewardsFrameId`. A completion we trigger will try to load a model file; if we have not staged one, expect a client-side failure that looks nothing like a protocol bug.

**OBSERVED. `CHAR_MISSION_MEDALS == 4`, and `msg.medal` is at `+0xC`.** `GmQuestComplete:611 msg.medal < CHAR_MISSION_MEDALS` (site `0x0052F911`) compiles to `0x0052F906 cmp dword ptr [edi + 0xc], 4` / `jl`. The medal switch handles cases 1, 2, 3, so 0 is the no-medal value. Corroborated by `ConstChar:1249 missionMedal != CHAR_MISSION_MEDAL_NONE`.

**OBSERVED. `COMPLETION_FLAG_PRIMARY | COMPLETION_FLAG_SECONDARY == 3.`** `GmQuestComplete:729` compiles at `0x0052FC1C` to `test byte ptr [ebx + 0x10], 3`. **UNVERIFIED: which of the two is `0x1`.** The assert proves only that the pair is `{1,2}` as a set; the divergent branches carry no naming string. Do not guess.

**OBSERVED. `isSimpleReward` is a tag comparison against 4.** `GmQuestComplete:246 !(isSimpleReward && (rewardCount > 1))` compiles at `0x0052F084` to `mov eax, [edi]` / `cmp eax, 4 / jne` / `cmp ebx, 1 / jbe` → assert. Authoring a reward with tag 4 and two entries trips a retail assert.

**NOT FOUND. There is no enumerable `UiMsgQuest*` vocabulary to recover.** A whole-file regex for `UiMsgQuest[A-Za-z0-9_:]*` returns exactly two matches, both halves of the single `GmQuestComplete:729` expression (`UiMsgQuestCompleteMissionNonMedal::COMPLETION_FLAG_PRIMARY` at file offset `0x5510E5`, `…SECONDARY` at `0x551122`). `COMPLETION_FLAG_[A-Z_]+` likewise returns only those two. One class name in the whole image.

### 1.6 The frame bus — the exhaustive list of ways server state reaches the quest UI

**OBSERVED, and re-measured for this document.** A `push imm32` scan over `.text` for ids in `0x1000014C..0x10000162`, each classified by the call that follows it (`0x00633BD0` = subscribe, `0x00633D70` = post):

**`QuestTaskTracker.cpp` subscribes to SEVENTEEN consecutive ids in one uninterrupted run**, `0x1000014C` through `0x1000015C`, at `0x0057CB94, CBA1, CBAE, CBBB, CBC8, CBD8, CBE5, CBF2, CBFF, CC0C, CC19, CC26, CC33, CC43, CC50, CC5D, CC6A` — every one `call 0x00633BD0`. The idiom breaks at `0x0057CC77 push 1 / call 0x7c93f0`.

**The publisher band is twenty ids wide and its upper edge is a real boundary.** Every id `0x1000014C..0x1000015F` is published from inside `ChCliApi.cpp`'s VA range; `0x10000160` is published five times from `MsCliTourn.cpp` (`0x00854D6A, D9D, DE8, F0E, F59`). So `0x1000015F` is the last quest-bus id, measured rather than assumed.

Publishers, by id, all inside ChCliApi:

| frame id | publisher VA(s) | subscribers seen |
|---|---|---|
| `0x1000014C` | `0x00813C27` | QuestTaskTracker, UiCtlInstance |
| `0x1000014D` | `0x00813C57` | QuestTaskTracker, UiCtlInstance |
| `0x1000014E` | `0x0080F238`, `0x0080F636` | QuestLog, QuestTaskTracker, GmView, GmHelpGuide, **Compass**, UiCtlInstance |
| `0x1000014F` | `0x0080F3A1`, `0x0080FA12` | QuestChallenge, QuestTaskTracker |
| `0x10000150` | `0x0080DAA9` | QuestTaskTracker, GmMapCtlLocationTag, **Compass** |
| `0x10000151` | `0x0080DEC2`, `0x0080F779` | QuestTaskTracker, **Compass** |
| `0x10000152` | `0x0080F8C2` | QuestLog, QuestTaskTracker, GmHelpGuide, GmMapCtlLocationTag, **Compass** |
| `0x10000153` | `0x0080F96A` | QuestLog, QuestTaskTracker, GmMapCtlLocationTag, **Compass** |
| `0x10000154` | `0x0080F44E` | QuestChallenge, QuestTaskTracker, **Compass** |
| `0x10000155`–`0x10000159` | `0x0080F6C7`, `0x00810B47`, `0x008124C8`, `0x00812473`, `0x0081529E` | **GmQuestComplete**, GmView, QuestTaskTracker |
| `0x1000015A`–`0x1000015C` | `0x00813D24`, `0x00813D70`, `0x00813DDA` | QuestMission, QuestTaskTracker, GmHelpGuide |
| `0x1000015D`–`0x1000015F` | `0x00813EBA`, `0x00813EF7`, `0x00813F63` | GmView, List |

*(Two ids show no post site under my scan's 6-byte call window — `0x10000150` and `0x10000159`. Lane B located both by hand at `0x0080DAA9` and `0x0081529E`; the scan is a floor, and the table above uses lane B's VAs for those two.)*

**CORROBORATED (two witnesses that share no ancestry).** `0x0049` posts `0x1000014E`, and `QuestLog.cpp` subscribes to `0x1000014E` at `0x0057BD35` — the frame-bus join `studies/minimap/FINDINGS.md:261` used to promote `0x0049 = QUEST_ADD` from UPSTREAM to CORROBORATED, independently re-derived here from a different scan and placed inside a 20-id family.

**REFUTED, and it was a plausible wrong answer: there are not two subscribe helpers.** Lane B reported the Quest UI's helper as `0x00637BD0` with "GmQuestComplete uses a different helper, `0x00633BD0`". The bytes it quoted are correct — `0x0057CB94` reads `68 4c 01 00 10 ff 73 04 e8 2f 70 0b 00` — but `0x0057CBA1 + 0x000B702F = 0x00633BD0`, not `0x00637BD0`. Every call target in the band resolves to `0x00633BD0`, GmQuestComplete's included; the only difference is the argument form (`[reg+4]` vs `[reg]`), which is a frame-pointer offset, not a second API. **Lane C had this right.**

---

## 2. The wire

### 2.1 The family, and what each opcode does

**OBSERVED.** Eleven receive handlers sit in the `0x0091Dxxx` dispatch block and each forwards to exactly one body in `ChCliApi.cpp`. Shapes are `msgshape.py`'s recovery from the client's own initializer tables, not the imported catalog.

| opcode | proposed name | shape (client's own descriptor) | wire | body | live n |
|---|---|---|---|---|---|
| `0x0049` | **QUEST_ADD** | `[u32 id, vec2 marker, u16 plane, u16 markerMap, u32 flags, str16×3, u16 homeMap]` | 78 | `0x0080F0A0` | 10 |
| `0x004A` | **QUEST_REMOVE_AND_UNLIST** | `[u32 id]` | 6 | `0x0080F250` | 6 |
| `0x004B` | *(bulk assign of the `+0x518` list)* | `[array32[64]]` | 4..260 | `0x0080F270` | 2 |
| `0x004C` | **QUEST_DESCRIPTION** | `[u32 id, str16(128), str16(128)]` | ≤522 | `0x0080F290` | 40 |
| `0x004D` | **QUEST_SET_MARKER** *(flag-setting form)* | `[u32 id, vec2, u16, u16]` | 18 | `0x0080F3C0` | 6 |
| `0x004E` | *(quest-complete panel feed)* | `[u32, u32, u32]` | 14 | `0x0080F670` | **0** |
| `0x0050` | **QUEST_ADD_NO_MARKER** | `[u32 id, u32 flags, str16×3, u16 homeMap]` | 66 | `0x0080F470` | 12 |
| `0x0051` | **QUEST_MOVE_MARKER** | `[u32 id, vec2, u16, u16]` | 18 | `0x0080F6F0` | 40 |
| `0x0052` | **QUEST_REMOVE** | `[u32 id]` | 6 | `0x0080F7A0` | 12 |
| `0x0053` | **QUEST_SET_ACTIVE_MARKER** | `[u32 id, vec2, u16, u16]` | 18 | `0x0080F8E0` | 6 |
| `0x0054` | **QUEST_OBJECTIVES_UPDATE** | `[u32 id, str16(128)]` | ≤264 | `0x0080F990` | 40 |

Client→server:

| opcode | proposed name | shape | live n |
|---|---|---|---|
| `0x0011` | *(abandon? — see below)* | `[u32 id]` | **0** of 971 |
| `0x0012` | **REQUEST_QUEST_INFO** | `[u32 id]` | 16 |
| `0x0013` | **QUEST_CLEAR_ACTIVE** | *(none)* | **0** of 971 |
| `0x0014` | **QUEST_SET_ACTIVE** | `[u32 id, u8 needMarker]` | 1 |
| `0x003B` | **NPC_SERVICE_SELECT** *(carries accept/turn-in)* | `[u32 tagged]` | 22 |

**OVERSTATED and now corrected: `GAME_SMSG 0x0048` is NOT in this family** despite sitting inside the number range. Its body `0x0080F090` is a single `jmp 0x007DF3B0` out of ChCliApi entirely, and it is already named `AGENT_SET_TABARD_VISIBLE` in `schema/overrides.json`. It is also 366 of the 372 messages in the numeric neighbourhood, so a census that counts by range rather than by handler will be swamped by it.

**OBSERVED. `GAME_SMSG 0x004F` and `0x0055` have a SEND descriptor and no RECEIVE descriptor on build 38797.** `msgshape.py 0x004F` prints only `SEND table 0x00bc8cb8 send-only, [u8, u16, u8] wire 6`; `0x0055` only `SEND … [u32] wire 6`. Both are in `studies/smsg/FINDINGS.md`'s list of catalogue orphans, and both are zero in the corpus. **Sending either is inert** — a server that does so is talking to nobody, and the effect is indistinguishable from a bug in our code.

### 2.2 The store the whole family writes to

**OBSERVED, and this is the best-evidenced structural claim in the arc.** The quest log is the array at `charContext+0x52C`, its count at `+0x534`, stride `0x34` = 52 bytes. From the `0x0052` deleter at `0x0080F7A0`:

```
0x0080F7C2  imul edi, ecx, 0x34
0x0080F84D  call 0x0080CAA0                    ; memmove the tail down
0x0080F855  dec dword ptr [ebx + 0x534]
0x0080F85B  imul esi, dword ptr [ebx+0x534], 0x34
0x0080F862  add esi, dword ptr [ebx + 0x52c]
0x0080F86F..0x0080F89F  five guarded call 0x0047F4F0 on [esi+0x30], [esi+0x2c], [esi+0x10], [esi+0xc], [esi+8]
```

The element the client itself names is `challenge`: `ChCliApi.cpp:4237 context->challengeSortArray.Find(challenge)` at `0x0080DDA7`, and `:4253` at `0x0080DDF7`.

**The 52-byte entry, and it is a check that could have failed:**

| offset | field | how it is pinned |
|---|---|---|
| `+0x00` | quest id | the binary-search key at `0x0080F7D4..F7F8` |
| `+0x04` | flags | `0x004C` sets bit 0, `0x004D` sets bit 1 |
| `+0x08`, `+0x0C`, `+0x10` | three short encoded strings | written by `0x0080F0A0` |
| `+0x14` | u16 home map | written by `0x0080F0A0` |
| `+0x18`, `+0x1C` | marker x, y (float) | `0x0050` writes `+inf` into both |
| `+0x20` | plane | |
| `+0x24` | always 0 | the `0x0049` handler zeroes it: `0x0091DB79 mov dword ptr [ebp-4], 0` |
| `+0x28` | marker map id | `0x0050` writes `0x378` (888) |
| `+0x2C`, `+0x30` | the two long description strings | written by `0x0080F290` |

`0x30 + 4 = 0x34` — **the struct closes to the measured stride with no slack, and the five pointers the deleter frees are exactly the five slots typed as pointers and no others.** A wrong layout would have left a free on a non-pointer or a pointer unfreed.

**OBSERVED. `charContext+0x528`, the dword immediately before the array object, is the ACTIVE quest id.** `0x0080F943 mov dword ptr [ebx + 0x528], edi` (the `0x0053` body); `0x0080F74E cmp edi, dword ptr [ebx + 0x528]` gating the `0x0051` notify; `0x0080F8A7 cmp dword ptr [ebx+0x528], ecx` / `0x0080F8AF mov dword ptr [ebx+0x528], 0` on removal; `0x0080DAB1 mov dword ptr [eax + 0x528], 0xffffffff` in the `0x0013` sender.

**`0x0049` sets the active quest as a side effect of adding** (`0x0080F20B mov dword ptr [eax+0x528], ebx`). This is the single most useful authoring consequence in the arc: **push several quests at login with `0x0049` and the last one silently becomes active.** Use `0x0050` for bulk restore (it never touches `+0x528`) and `0x0053` to choose the active one deliberately.

**OBSERVED. Flag bit 0 is `CHAR_CHALLENGE_FLAG_DESC_FILLED`, and the numeric value is proved by the assert's own compiled test.** `ChCliApi.cpp:667 !(flags & CHAR_CHALLENGE_FLAG_DESC_FILLED)` at `0x0080F489` is emitted by `0x0080F47A mov eax,ebx / not eax / test al, 1 / jne` — the tested bit is `0x01`. `0x004C`'s body sets exactly that bit (`0x0080F2D0 or dword ptr [esi+4], 1`), and `0x0054` gates on it.

**OBSERVED, and it is an authoring trap: `0x0054` is a silent no-op unless `0x004C` has already been sent for that quest.** `0x0080F9CD` reads `F6 47 04 01 74 4C` = `test byte ptr [edi+4], 1` / `je 0x0080FA1F` — the entire body is skipped. Sending objective updates before answering the description request looks exactly like "the client ignored us".

**And ArenaNet trips its own trap twice.** At `t=29.197` and `t=66.159` in `20260807T143055`, the server emits `0x0054` for a fresh entry *before* the `0x004C` for it. Those two `0x0054`s were no-ops on ArenaNet's own wire. The warning stands; the implication that ArenaNet's ordering is a safe template to copy verbatim does not.

**NOT FOUND, and this is a structural seam nobody bridged.** No quest message carries a `questType` field. The wire addresses a quest by a **bare u32** that is the entry's first dword; the UI addresses it by an **8-byte tag** whose first half is a `questType`. **How the client synthesises the tag for a wire-delivered quest is not established by any lane.** That rule decides which UI class renders an authored quest, and it is the blocker under lane B's proposed content column.

### 2.3 The lifecycle, in ArenaNet's own order

**OBSERVED**, reproduced from raw bytes for this document over `20260807T143055`, connection `:60935`:

```
27.679  c2s 0x003B  0x805003   qid 80,  code 3   (offer opens)
28.147  c2s 0x003B  0x805001   qid 80,  code 1   (accept)
28.179  s2c 0x0049  [80, (11715.0, 3517.0), 26, 148, 0, <3 enc strings>, 148]
28.181  c2s 0x0012  [80]
28.241  s2c 0x004C  [80, str<43u>, str<10u>]
...
46.765  c2s 0x003B  0x805007   qid 80,  code 7   (turn in)
46.797  s2c 0x004D[80] · 0x004C[80] · 0x0052[80] · 0x0052[80] · 0x004A[80]
```

Instance load, connection `:62994`:
```
66.118  c2s 0x0091 (REQUEST_ITEMS)
66.159  s2c 0x0050[218] · 0x0050[1462] · 0x0054[1462] · 0x004C[1462] · 0x0051[1462, (inf,inf), 0, 888]
66.188  c2s 0x0088 (REQUEST_SPAWN_POINT)
66.684  c2s 0x0090
66.737  s2c 0x0053[218, (6086.0, 4161.0), 0, 146]
```
The same pattern repeats at `t=214.054` (`:64102`) and `t=228.481` (`:64103`).

**OBSERVED. "No marker" has an exact spelling and it is not zero:** marker x = marker y = `0x7F800000` (`+inf`) and map id **888**. `0x0050`'s body reads the constant from `[0x00948654]` (`00 00 80 7f`) at `0x0080F574`/`0x0080F600` and writes `mov dword ptr [esi+0x28], 0x378`.

**CORROBORATED — 888 is not an arbitrary sentinel.** `toolkit/clientscan/areatable.py` on the same exe prints *888 consecutive valid records before the pattern breaks / 888 non-empty, 888 with a name id*. So "no marker" means "map id == MAPS", one past the last valid map. Two lanes reached this independently. **Derive it from `areatable.py`, never pin the literal** — and never send `(0,0)`, which drops a marker at the map origin.

**OVERSTATED and now corrected: turn-in is not a fixed five-message script.** Lane D wrote "Complete: `0x004D`, then `0x004C`, then `0x0052` (twice), then `0x004A`" as directly copyable. Quest 82's turn-in at `t=92.746` produced `0x0052[82] · 0x0054[1462] · 0x0051[1462] · 0x0052[82] · 0x004A[82]` — **no `0x004D` and no `0x004C` at all**; quest 82's `0x004D`+`0x004C` had fired 1.6 s earlier as an objective advance. **The reliable part is `0x0052` twice then `0x004A`, 3 of 3.** The preceding `0x004D`/`0x004C` are a separable objective-advance mechanism.

**REFUTED, and it was a tempting universal: "the description is a PULL; do not send `0x004C` unsolicited on first add."** Quest 1462 is a fresh mid-session accept, not an instance load, and at `t=29.197` the server pushes `0x0049`, `0x0054`, `0x004C` and `0x0051` unsolicited — and the client *still* sends `0x0012` at `t=29.214`, drawing a second `0x004C` at `t=29.275`. **What is mandatory is the responder, not the restraint: the client asks in 4 of 4 accepts regardless of whether it was already told.**

### 2.4 `0x003B` — accept and turn-in, derived from consequence

**OBSERVED.** The decoding is `0x800000 | (quest_id << 8) | code`, 22 of 22 samples, all with high byte `0x00` — the quest-dialog family only. Every one of the 22 decodes cleanly; my own re-decode of both sessions gives 11 of 11 each.

**OBSERVED, from consequence rather than from a name** — and this is a correction to lane E, which filed the code semantics as NOT_FOUND with the closing clause *"it cannot be derived from the wire alone without a matching client disassembly pass"*:

| code | consequence | n |
|---|---|---|
| `0x01` | server replies `GAME_SMSG 0x0049 QUEST_ADD` within 30–55 ms | **5 of 5** |
| `0x07` | server replies `0x0052` ×2 + `0x004A` (± `0x004D`/`0x004C`) within 35 ms | **3 of 3** |
| `0x03` | no quest-family reply, always ~0.4 s before an `0x01` for the same id | 2 of 2 |
| `0x04` | `0x0054` objectives update + `0x0051` marker move for that id | n=1 |

A c2s code whose s2c consequence is deterministic across five independent quest ids **is** derived from the wire. What remains genuinely NOT FOUND is a **decline** code: no `0x003B` value in the corpus produces a refusal, because the operator never declined. The English words *accept* / *offer* / *turn in* are ours — RECONSTRUCTION on top of an OBSERVED consequence.

**NOT FOUND:** whether the four other service families exist on the wire. `schema/overrides.json`'s `0x003B` entry names 8 callers across `GmNpc.cpp`, `VnLearnSkill.cpp`, `VnUnlockSkill.cpp`, `VnUnlockItem.cpp` and `VnUnlockHero.cpp`, but **all 22 captured selects carry high byte `0x00`** — merchant, skill-unlock, item-unlock and hero-unlock are inferred from client code only. This bounds how general a dialogue implementation has to be on day one.

### 2.5 The NPC dialog window — `0x0080` and `0x0081`, and why this is the arc's biggest result

**The problem.** `test_dispatch.py:127-130` drops `0x003B` on purpose with *"Blocked behind 0x0039 above: this server does not answer an interaction, so no window is ever open and no selection can be made. Handle it when INTERACT gets a reply."* Every lane inherited that framing. Lane G looked for the reply's shape and reported it absent from the repo. It is absent from the repo; it is not absent from the vault.

**OBSERVED, measured for this document.** `GAME_SMSG 0x0080` occurs **15 times in 11,241 s2c messages** in `20260807T143055` and 13 in 10,896 in `20260810T235916`. Yet it appears in the window `[t−1.5s, t+0.5s]` around a `0x003B` select **11 of 11 times in the first session and 11 of 11 in the second**. Against a background rate of 0.13%, that is not adjacency by chance.

**OBSERVED.** `GAME_SMSG 0x0081` carries a single `agent_id`, and it is the interacted NPC. Over all three keyed sessions: 29 `c2s 0x0039 INTERACT_AGENT` messages; **23 are followed within 8 s by an `0x0081` naming the SAME agent, 0 name a different agent**, and 6 draw no `0x0081` at all — consistent with the repeat-clicks a player emits while walking into range.

**OBSERVED, and this is the discriminator.** The `0x0080` string at `t=27.719` in `20260807T143055` begins:
```
1706 F80F ACBB 4FA2 010A 0BA9 0107 <11 UTF-16 units: the player's own character name> 0001 0001 0002 0107 …
```
and the description slot of `s2c 0x004C [80, …]` at `t=28.241` — 0.5 s later, the reply to the quest the player was being offered — begins with the **identical 22-code-unit run**, diverging only at the tail. Same leading string id `0x1706 F80F ACBB 4FA2`, same embedded literal UTF-16 character name, same framing. **`0x0080` is the NPC's speech; `0x004C` is the same text filed into the quest log.**

**Shapes, from `schema/messages.json`:** `GAME_SMSG 128 = [msg_header, string16(122)]`, `GAME_SMSG 129 = [msg_header, agent_id]`. Both carry `name: null`. Neither has an override entry.

**Label: OBSERVED for the association and the byte-identical string; RECONSTRUCTION for the names.** No assert has been traced to either handler and neither has been fired at a client. But *"dialogue is blocked because nobody knows the reply"* is dead, and the two opcodes to confirm are named, shaped, and already decodable by our codec.

**One thing the association does not settle.** At `t=26.816` a `0x0080`/`0x0081` pair fires *before* any `0x003B`; at `t=27.719` one fires just *after* a `0x003B` code 3. So `0x0080` plausibly serves both "open the dialog" and "answer a dialog branch". The `0x0081` also fires alone at every quest-accept instant (`28.179`, `29.197`, `47.655`, `73.431`, `92.792`, `173.560`) — six extra firings beyond the 15 paired ones. A labelled single-action run settles it.

### 2.6 The compass — subscribed, but not proven to draw

**OBSERVED.** One contiguous function in the compass module subscribes to six of the quest frame ids: `0x008BB67B` (`0x14E`), `0x008BB688` (`0x150`), `0x008BB695` (`0x151`), `0x008BB6A5` (`0x152`), `0x008BB6B2` (`0x153`), `0x008BB6BF` (`0x154`). An `int3`-padding scan over `0x008BB400..0x008BB700` finds padding only at `0x008BB46C` and `0x008BB475+11` (ending `0x008BB480`) — one function, not six.

**So there is no separate marker opcode to discover.** Quest markers reach the compass through `0x0049`/`0x004D`/`0x0051`/`0x0053`/`0x0050` and nothing else.

**OVERSTATED, and all three verifiers flagged it: lane C's "the compass needs no separate work" is a prediction contradicted by the repo's own screen measurement.** `studies/minimap/FINDINGS.md:721` records that firing `0x0049` at a real client registers the quest — a `?` icon appears under the level bar, 23.8% of that icon slot differing from a control run — and **the compass starburst does not draw; the disc is byte-static across the whole run.** `:727` records the cause as NOT FOUND. Subscribing is not drawing.

**And nobody checked the obvious thing.** `probes.py:2467` sends `Step(8.0, 0x0049, [1, _SPAWN_WORLD, 148, 148, 0, "", "", "", 0], …)`. Measured over every live `0x0049` (n=10) and `0x0050` (n=12):

| field | ArenaNet's observed values | the probe sent |
|---|---|---|
| 3 (plane) | `{0: 8, 26: 2}` | **148** |
| 4 (marker map) | `{146: 6, 148: 2, 164: 2}` | 148 ✓ |
| 5 (flags) | `{32: 8, 0: 2}` | 0 |
| 9 (home map) | `{148: 6, 146: 4}` | **0** |
| `0x0050` flags | `{32: 12}` | — |

The probe put **148 into a field ArenaNet only ever fills with 0 or 26**, and **0 into a field ArenaNet always fills with a real map id**. Two cheap, untested, previously-unnamed hypotheses precede any disassembly of `CompassQuestEffect.cpp`.

**OBSERVED** (lane B, this study): `CompassQuestEffect.cpp` *has* now been disassembled, contrary to what `studies/minimap/PLAN.md:390` Risk 1 still says. It handles exactly four message ids — the dispatch at `0x008BC95B` is `mov eax,[ebx+4] / add eax,-8 / cmp eax,0x4a / ja 0x8BCAC4 / movzx eax, byte ptr [eax+0x8bcae0] / jmp dword ptr [eax*4+0x8bcacc]`, and the `0x4B`-byte index table routes only indices 0, 1, 3, 74 (ids `0x08`, `0x09`, `0x0B`, `0x52`) away from the default. `CompassQuestEffect:254 !obj` at `0x008BC9A2` guards a 32-byte tagged allocation on id `0x09`. **What is still open is the last hop: which arm is reached from which frame message.**

---

## 3. Where quest data lives, and what that means for the provenance gate

### 3.1 There is no static quest table anywhere

**OBSERVED, with a positive control.** A stdlib byte scan of every PE section of build 38797:

| symbol | ASCII hits |
|---|---|
| `ConstQuest` | 0 |
| `s_quest` | 0 |
| `questClientData` | 0 |
| `QuestData` | 0 |
| `arrsize(s_quest` | 0 |
| `CHAR_MAX_QUEST` | 0 |
| `MAX_QUEST` | 0 |
| **`s_missionClientData`** | **1** (at VA `0x00988CB4`, inside `index < arrsize(s_missionClientData)`) |

The control is what makes this a check rather than a wish: the mechanism that would find a quest table finds the mission table.

**OBSERVED. The one thing that looked like a shipped table is not one.** `QuestEntryGroup:247 staticData` resolves through `0x0057FD5E mov ecx, 0xc07da4`. `.data` spans VA `0x00BEC000` with `rawsize` 92,672, so file-backed bytes end at `0x00C02A00`; `0x00C07DA4` is `0x53A4` past that — zero-filled at load, populated at run time.

**OBSERVED. Map files carry nothing either.** Chunk `0x0A "Locations"` is **exactly 13 bytes in all 349 map files** — a single-bucket length histogram — and `toolkit/mapdata/mapbuild.py:50` already lists `0x2000000A` (13 B) among FINDINGS 14's five mandatory chunks that are byte-identical ArenaNet constants across all 349 maps. CORROBORATED, two independent readings in this repo. Chunk `0x07 "Mission"` is real per-map content (349/349, 56–1226 B, median 221, broad flat histogram) but far too small for text, and **nothing in `toolkit/mapdata/` reads it**.

**UPSTREAM agreement, and it is genuinely a second lineage:** `vault/mirrors/Fournux__Tyria-Extractor/doc/QUEST_EXTRACTION.md` §1 — *"No complete static quest_id -> metadata/text references inventory has been confirmed in the archive or client executable."* Its per-slot table assigns quest name, location/category, named NPC, description and objectives all to runtime packets. **But see §6: this upstream has no §6.1 derivation-register row, so its per-slot naming may not be adopted yet.**

**NOT FOUND, and the boundary of the negative stated honestly:** this is a negative about the client **executable** — a symbol scan, the assert-module census, and the `consttable.py` anchor mechanism. **Nobody enumerated `Gw.dat`'s non-map, non-text file kinds looking for a quest resource.** The only archive-side witness is UPSTREAM.

### 3.2 The coded string, decoded — and confirmed against ArenaNet's own bytes

**OBSERVED.** A coded string is a sequence in which words `< 0x100` are markers and words `>= 0x100` are `0x100`-biased base-`0x7F00` varints, most-significant word first, `0x8000` marking continuation. This rule was derived in `studies/textrec/FINDINGS.md` §4 from `TextParser.cpp` and had **never been tested on a source that arc did not have**.

**The refutable check: re-encoding the leading value of every quest EncString in `0x0049` and `0x0050` reproduces ArenaNet's own words byte-identically, 66 of 66, zero mismatches.** Example: our encoder emits `8102 3E14` for id 80660, which is verbatim what the server sent for quest 1462's name.

**The second refutable check, and it splits where a wrong reading would not.** All 66 slots parse; per-slot shapes are `{(0,'id-only'): 22, (1,'id+trailing varint'): 22, (2,'id+trailing varint'): 22}`. Resolving each leading id through `textrec.TextIndex.needs_key` gives **plain 22, encrypted 44, absent 0** — and the split is exactly per-slot: slot 0 is plain 22/22, slots 1 and 2 are encrypted 22/22 each. That is `textrec` §4's own prediction — *"a bare string id … takes the verbatim path, and can only ever have been a plain record"* — confirmed 66/66 on a source it never had. Under a wrong reading the plain share would sit near the archive-wide ~28%, not partition cleanly.

**The discriminator that refuted its rival — OBSERVED, and reproduced for this document.** Slot 0's constant word `0x3D64` reads as string id **15460** under `word − 0x100` and as **15716** under the rival raw-word reading:
```
$ python toolkit/clientscan/textrec.py --dat C:/gd/Rurik/vault/dat_study/Gw.dat 15460 15716
15460  file 15 record  100  'Ascalon'
15716  file 15 record  356  None
```
One reading resolves to a plain, readable record naming the region every captured session played in; the other resolves to an encrypted record returning nothing. **The rival could have won and did not.** `0x3D64` is the only value slot 0 ever takes, across all 22 adds.

The low end of the id space is the client's markup alphabet, resolved through the same rule: `0x0101`→1 `[null]`, `0x0102`→2 `\n[b]`, `0x0104`→4 `%num1%`, `0x0107`→7 `<p>[b]`, `0x0BA9`→2729 `%str1%`, `0x0A86`→2438 `%str1%: %num1%`. All plain, all readable without a key.

**Half of `textrec`'s standing open question is now closed.** `studies/textrec/FINDINGS.md:468` asked *"Does the server send the key with a string reference? … Look for a string16 field in a GAME_SMSG whose contents parse as a coded string with a parameter pair, against our own captures."* Answer: yes — 44 of 44 name/NPC slots parse as `id-varint + one trailing varint`, on ArenaNet's own wire. Candidate 1 at `:408` is confirmed.

### 3.3 The key is not found, and that is a load-bearing negative in a useful direction

**NOT FOUND.** Thirteen constructions from the trailing varint (MSW/LSW accumulation, both orderings, `(sid,v)`, `(v,sid)`, `(v,0)`, `(0,v)`, packed-u16 both ways, varint including the id word, no-strip) were scored on space frequency over 8 records against **two null controls** (a shifted key, and `key=(1,1)`). Best variant reached ≥10% spaces on 1 of 8; both nulls scored 0 of 8. **Nothing beat the null.** A rival hypothesis — the trailing words as three separate string ids — gave 5 of 6 encrypted-or-absent and one accidental hit.

**UNVERIFIABLE by this synthesis, and honestly so.** I did not re-run the 13 constructions; a negative over a self-chosen search space is not cheaply reproducible from a summary, and its value depends on the scorer, the construction set, and n=8. What *is* reproduced is the surrounding structure that makes the negative credible: the trailing varint is present on 44/44 encrypted references and absent on 22/22 plain ones, so its **role** is close to proven even though no packing of it decrypts. **Making this auditable means landing the scorer and the record set as a test beside `textrec.py`, with the 66/66 round trip as its green half.**

**The provenance consequence, and it should be stated explicitly because a reader could get it backwards.** Lane D observed — correctly — that ArenaNet's own server injects literal UTF-16 into quest description strings: the `0x004C` for quest 80 contains `0BA9 0107 <UTF-16> 0001 0001` = template id 2729 (`%str1%`), a marker, the player's character name, a terminator. That is a *substitution*, not authored prose. **ArenaNet's actual quest text is entirely behind encrypted ids and is not present as text anywhere in our capture corpus.** `textrec.py 5635` (quest 80's name id) returns `None`. So there is no way to transcribe their prose out of the vault by accident — the key negative is what protects the gate here.

### 3.4 The correction that changes the authoring plan: we can write our own strings

**Lane D's headline authoring implication was "AUTHORING A QUEST IS A PURE CONTENT-TOML + SERVER-MESSAGE PROBLEM … Do NOT plan to patch Gw.dat for quests"**, followed by *"THE HONEST NAME PATH TODAY IS A BARE PLAIN STRING ID … `enc_name = [0x3D64]` names a quest 'Ascalon' right now"* — i.e. authored quest names are limited to ArenaNet's existing vocabulary or a ~5-character literal stub.

**That is wrong, and seven lanes missed the tool that makes it wrong.** `toolkit/mapdata/textwrite.py` exists in this tree, with `toolkit/mapdata/test_textwrite.py`, and `TESTS.md:473` names it *"the FIRST COMMITTED writer of authored [strings]"*. Its own docstring:

> **THE DESIGN IS A MERGE, NOT A REBUILD** … `merge` keeps every untouched record's PAYLOAD BYTES verbatim out of the archive and only encodes the ones being added. An empty merge is a byte-for-byte identity, which the test asserts …
> **PROVENANCE.** The strings are ours. Nothing here reads ArenaNet's text, and the existing records it preserves are ones we wrote.

It carries write guards refusing `C:\gw` and `vault/dat_study` before opening anything. The precedent has already shipped: `TESTS.md:508` names `test_skillnames.py` as *"the 188 authored skill names a custom [build carries]"*, and `textrec.py:235` states that a plain record's payload is just UTF-16LE, *which is why authoring one needs no key*.

**Corrected scoping.** Quest **data** — identity, position, state, markers, lifecycle — needs no archive write, and lane D is right about that half. Quest **names**, if they are to be arbitrary authored strings rather than borrowed ones, go through `textwrite.py`: merge a new plain text record into the owner's own `Gw.dat`, commit only the bare string id. That is squarely inside the provenance gate — our words, the owner's archive, nothing of ArenaNet's in git — and it is exactly CLAUDE.md's "commit the id, resolve the string at run time".

### 3.5 The content store takes a quests table today

**OBSERVED, reproduced independently twice.** `toolkit/content.py` is 418 lines and enforces **zero** table-specific schema. `load()` walks every `*.toml` under `content/` then `vault/content/`, and the only per-row gate is `_check_provenance` (content.py:194-201), which requires a `provenance` dict with a `source` from a fixed nine-entry vocabulary. Writing a draft `content/quests.toml` to a scratch dir and loading it through this worktree's real loader returns `census: {'quest': 1}` with no code change.

Per-source conditions (content.py:85-145): `EXTRACTED = {"client-table", "measured"}` need an `extractor` path that exists in the checkout; `NEEDS_BUILD = {"client-table"}` also needs a `build`; `NEEDS_CAPTURE = {"capture"}` needs `capture` + `origin`; `NEEDS_PAGE = {"wiki"}` needs `page`; `UNLICENSED = {"gw-preservation"}` needs non-empty `verified` text. All eight refusals are exercised by `toolkit/test_content.py` (floor 39).

**Census, re-run 2026-08-15** (`python toolkit/content.py`): `area 3, attack_speed 1, attribute 51, item 1, map 10, npc 56, player 2, skill_effect 12, skills 1333, spawn 4`. **PLAN.md:592's cited baseline is stale** — it records the 2026-08-14 figure with `player 1` and no `attribute`/`skills` rows.

**The row shape is already decided by precedent, not by invention.** `vault/content/npcs.toml` stores a captured coded string as a list of u16 code units: `enc_name = [33026, 17658, 61813, 62562, 27710]`, with `provenance = {source='capture', capture='20260810T235916', origin='live', extractor='toolkit/authsrv/npcdefs.py'}`. `npcdefs.py:13` states the rationale: *"the permitted side of the provenance gate: measurement, not expression. `enc_name` is … a list of string IDS"*.

**An off-by-`0x100` trap the proposals conflate, and it will bite the first implementer.** Loading a TOML literal of `0x3D64` returns `enc_name: [15716]`; the *archive string id* is **15460**. Two different columns: `enc_*` holds **wire code units** (`0x3D64`), matching `npcs.toml`; `textrec` takes **string ids** (`15460 = 0x3D64 − 0x100`). And the sender must build the `string16` as `''.join(chr(u) for u in row['enc_name'])`, because `codec.py:352` takes a `str`, not a list.

**NOT FOUND:** any id-allocation tooling. `toolkit/contentids.py` is *not* a general allocator — read in full, it does exactly one thing: cross-checks that a map's `file_id` binds to byte-identical content in both the server's and the client's `Gw.dat`. Every `agent_id`/`definition` in `content/world.toml` is hand-picked and coordinated through prose comments (*"deliberately clear of the probes (agents 2..7, definition 2)"*, world.toml:320). Quest ids would need the same manual convention or a new tool.

**NOT FOUND:** any quest row anywhere. `content/*.toml` word-boundary grep for `quest` returns nothing (all hits are `question`/`requested`); `vault/content/` holds only `attributes.toml`, `npcs.toml`, `skills.toml`; `schema/messages.json` carries **zero** quest-named messages; `TESTS.md` has **zero** word-boundary `quest` in 2,885 lines; and `git log --diff-filter=A --name-only --all --pretty=format: | sort -u | grep -i quest` returns nothing on any branch. **No quest-named file has ever existed in this repo.**

---

## 4. The capture corpus: what it has, what it does not, and the next capture's shopping list

### 4.1 What is there

**OBSERVED.** `vault/captures/live/` holds 6 session directories (five stamped 2026-08-07, one 2026-08-10), 27 `.jsonl` files, every one classified `live` by `toolkit/origin.py`, and no `live`-origin file anywhere else in the vault. Only three sessions carry decrypted game channels; all 12 connections read as build **38797** from the client's own VERSION frame.

Quest traffic, re-censused for this document:

| session | s2c | c2s | quest opcodes | quest ids |
|---|---|---|---|---|
| `20260807T133758` | 387 | 52 | **none** | — |
| `20260807T143055` | 11,241 | 419 | `0x49`×5 `0x4a`×3 `0x4b`×1 `0x4c`×20 `0x4d`×3 `0x50`×6 `0x51`×20 `0x52`×6 `0x53`×3 `0x54`×20 `0xfa`×1 | 62, 80, **82**, **218**, 1462 |
| `20260810T235916` | 10,896 | 500 | *identical counts* | 62, 80, **86**, **222**, 1462 |

**The two big sessions are the same scripted route run twice.** Not just the same opcode census to the message — the same `0x003B` sequence in the same order: `80 offer → 80 accept → 1462 offer → 1462 accept → 80 turn-in → [218|222] accept → [218|222] turn-in → [82|86] accept → [82|86] turn-in → 62 accept → 62 code-4`. They differ at exactly two slots. No lane noticed this, and it turns out to be the key to §5.

**Two different characters** — extracted as literal UTF-16 runs inside the `0x0080`/`0x004C` strings: **`character C`** (2026-08-07) and **`character D`** (2026-08-10).

### 4.2 What is not there — and these negatives are the shopping list

**NOT FOUND, and this is the largest gap in the arc: the entire completion half of the subsystem is binary-only.** `0x004E`, `0x006C`, `0x0096`, `0x0097`, `0x00FB` are **0 of 22,524**. Everything said about `GmQuestComplete`'s medals, completion flags, reward tags and 3D scene rests on the image alone, because the operator never completed a mission.

*Correction to lane C, measured here:* `0x00FA` is **not** zero — it fires exactly once per session at map load (`t=17.941` and `t=19.786`), and both times it carries an **empty** `array32[32]` (`msgshape 0x00FA`: handler `0x0091F9B0`, `[array32[32]]`, wire 4..132). Like `0x004B`, it is a real load-time bulk assignment that carried no evidence.

**NOT FOUND:** a `GAME_CMSG 0x0011` sample. Zero across **971** client-to-server messages on 12 keyed connections. *(Lane C wrote "zero in 22,000+ c2s" — the denominator is wrong by a factor of 23; 22,524 is the s2c count. The negative survives at a much weaker strength than advertised.)* Its ABANDON reading rests only on its call site: `0x0057BEA0` in `QuestLog.cpp`, on the `cmp dword ptr [edx+8], 0xb` context-menu arm at `0x0057BE67`.

**NOT FOUND:** a `0x0013` sample (the operator never deselected a quest); only one `0x0014` sample. **NOT FOUND:** any non-quest `0x003B` service family. **NOT FOUND:** what the `+0x518` list `0x004B` assigns actually holds — both observed instances carried an empty array, and its only readers are `GmMapCtlLocationTag.cpp` and `GmCtlItemImage` via the accessor at `0x0080DB30`.

**NOT FOUND, and it is the caveat that bounds §2 and §4 entirely: every keyed live session was played on a character opted into Reforged Mode.** Quest **1462** appears in both big sessions, 8 times, and GWW says 1462 is *"Getting Started in Guild Wars"*, gated behind Reforged Mode and *"added as part of the May 27th, 2026 update"*. Lane F warned about Reforged content in the abstract; lane D observed 1462 on the wire; **neither joined them**. The corpus is therefore not a clean sample of ArenaNet's baseline behaviour, and the instance-load replay shape and the observed reward patterns inherit that.

**NOT FOUND:** anything about parties. Every live session is a solo operator, so **whether quest state is per-character or per-party is untouched by all seven lanes.** The only trace of the question is lane C's open item on `0x0052` arriving twice per turn-in — confirmed here, 3 of 3 — which is exactly the shape a party broadcast would have.

### 4.3 The shopping list, ordered by what it unblocks

1. **Complete a mission.** Unblocks `0x004E`/`0x006C`/`0x0096`/`0x0097`/`0x00FB` and the whole `GmQuestComplete` scene — the largest hole in the arc.
2. **A character NOT in Reforged Mode**, running the same script. Separates protocol from Reforged content, which nothing currently does.
3. **A party of two**, one player accepting a quest. Settles per-character vs per-party and the doubled `0x0052`.
4. **Abandon a quest from the log context menu, in an outpost.** Settles `0x0011`, and joins `QuestLog:261 MISSION_MAP_OUTPOST == MissionCliGetMap()` to GWW's town-only statement (§5.4) — two witnesses for one gate, currently unjoined.
5. **Decline an offer.** No `0x003B` code has ever produced a refusal.
6. **Talk to one NPC and do nothing else** — a labelled single-action run in the `studies/cmsg` §3b style. Settles whether `0x0080` opens the window, answers a branch, or both.
7. **Log in on a character already holding quests.** `0x004B` and `0x00FA` both carried empty arrays, 2 of 2 and 2 of 2.
8. **Talk to a merchant, a skill trainer, and a collector.** All 22 `0x003B` selects carry high byte `0x00`.
9. **Deselect the active quest**, and **click a quest whose marker the client lacks.** `0x0013` = 0, `0x0014` = 1.

---

## 5. GWW, and the blind cross-check

Source labelled **WIKI** per `studies/character/FINDINGS.md`: strong for player-visible values, explicitly weak for internals, and describing the **currently patched live game**, not build 38797.

### 5.1 What a quest is, as a designed object

**WIKI** (GWW, *Quest*): *"Fundamentally, they consist of a series of objectives … and text that both explains the objectives and tells a story… The objectives, initial text, and reward of a quest are listed in the Quest log, and the quest selected in the log may provide a quest marker on the compass map."* Giver marker = a green exclamation mark; destination/mid-point = an arrow; in-range = green star, out-of-range = green arrow at the compass edge.

**`Template:Quest infobox`** — the community's own decades-refined schema, and a strong prior for column names: `id, name, section, image, elite, master, minimission, solo, repeatable, required hero, required hero2, given by, given at, region, campaign, required/required2/required3, required_all, type, profession, primary, secondary, nationality, part of, preceded by, followed by, map/map2–5, map1text–5text, acceptance reward, experience reward, completion reward`. Its `type` `#switch` has exactly five arms: `primary | secondary | festival | mini-mission | minigame|mini-game`, defaulting to secondary.

**`Template:Mission infobox`** is a structurally different object: `name, map, campaign, region, type, partysize (default 8), requiredhero, duration, preceded by, followed by` — **no `id`, no reward fields** — with its own four-value `type`: Cooperative, Competitive, Elite, Challenge. Missions also differ mechanically: *"they do not have resurrection shrines. Should your entire party die while in a mission, you will fail that mission and be returned to the mission's outpost or town."*

**`Template:Standard prerequisites`** decomposes requirements further than the infobox: `campaign, nationality, transfer, hero, profession, primary, secondary, test, unstarted | complete | active` (a prior quest's required **state**, not merely "completed"), `minimum` (numeric level), `reforged`.

**WIKI: quest-log grouping is a display concern the wiki calls Section, and quest traits (Solo, Mini-mission, Master/Elite, Repeatable, Hard Mode Only, Hero required, Flashback) are a third, informal layer** distinct from the `type` field. Repeatable quests *"are not marked as repeatable in-game"*. Abandoning is *"only available in towns and outposts, not combat areas"*.

**WIKI: `Category:Ascalon (pre-Searing) quests` contains exactly 70 pages** — *"The following 70 pages are in this category, out of 70 total"* — plus a `Vanguard quests (9 P)` subcategory whose nine titles all also appear in the 70. So 70 is the total, and the `≤70` framing downstream is sound.

**WIKI, and it is the scoping result for R4c-1:** only two things gate leaving Pre-Searing — one primary-profession test, and *A Second Profession*. Three separately-authored pages agree (`Ascalon Academy` §Requirements, `The Path to Glory` §Requirements, `A Second Profession` §Notes: *"You cannot progress past pre-Searing without taking on a second profession"*). **Flagged as cross-page agreement inside one wiki, not two lineages.**

### 5.2 The blind cross-check on quest *kinds* — REFUTED as a corroboration

The arc set lane B (client) and lane F (wiki) up blind, expecting the client's `questType` enum and the wiki's quest kinds to agree or disagree informatively.

**They did neither, because they measured different objects.** Lane B recovered a **three**-valued client-internal `questTag.questType` that selects which UI **frame class** the quest log instantiates. Lane F recovered a **five**-valued wiki display enum (`primary/secondary/festival/mini-mission/minigame`) plus a separate **four**-valued *mission* enum (`Cooperative/Competitive/Elite/Challenge`). My own wiki fetch confirms quests 62/80/82/86/1462 are all `type=Primary` and Bandit Raid is `type=Secondary` — six quests, two wiki types, and all six are ordinary quest-log entries that would share one client `questType`.

**This must be stated rather than left for a reader to assume, and it has a schema consequence: do not collapse the two.** Primary/secondary is *not* `questType`, and the client's word `challenge` is *not* the wiki's Challenge Mission. Lane F flagged the suspicion in its open questions; no lane resolved it. The blind design was sound and the pairing was mismatched.

### 5.3 The blind cross-check that DID land — quest ids, and nobody claimed it

Lanes C/D/E read the wire. Lane F read GWW. Neither consulted the other. **Five of the seven quest ids in the decrypted corpus resolve to named GWW pages, and both halves were re-verified independently for this document** (wire ids via `cmsgstream`, wiki ids via a MediaWiki API fetch of each page's raw infobox):

| wire id | GWW page | GWW `type` |
|---|---|---|
| 62 | Unsettling Rumors | Primary |
| 80 | Message from a Friend | Primary |
| **82** | **Necromancer Test** | Primary |
| **86** | **Ranger Test** | Primary |
| 1462 | Getting Started in Guild Wars | Primary (Reforged Mode) |
| 218 | — | — |
| 222 | — | — |

**CORROBORATED — two lineages sharing no author, no code and no ancestry.** And the discriminator is sharper than the count, because of §4.1's structural finding: the two sessions run the *same script* and differ at exactly two slots. **The id that varies between them is precisely the one GWW says is profession-specific, and the two values it takes are the two profession tests.** Under a wrong id binding, that alignment has no reason to exist.

**And there is a third, entirely accidental witness sitting in the payloads.** The character names are literal UTF-16 inside ArenaNet's own dialog strings: the only session containing quest **82** (*Necromancer* Test) belongs to **`character C`**; the only session containing quest **86** (*Ranger* Test) belongs to **`character D`**. That is the owner's own naming joke, not a measurement, and it is labelled **RECONSTRUCTION** for exactly that reason — but it is a signal that a wrong binding would not produce, and it is the kind of check this repo prefers: one the artifact could have refuted.

**Open, and cheap: quests 218 and 222 occupy the same structural slot in the two runs and vary with the character, and neither appears in lane F's sampled id bands (41–89 Prophecies Pre-Searing, 1182–1190 Vanguard, 1462 Reforged).** The cheapest decisive test is a single GWW search: `insource:"| id = 218"`. Note that lane F's 41–89 band is itself a sample of ~18 pages out of 70, not a census — and 218/222 are the evidence for that.

### 5.4 What GWW adds that the binary does not

- **Reward vocabulary** (GWW, *Quest reward*): gold, XP, skill points, affiliation points, attribute points (*"two quests which provide 15 attribute points each … each character can earn only 30"*), skill unlocks — *"A small number of quests, mostly early training quests, will teach you skills when they are first accepted rather than when they are completed"* — items, trophies, hero recruitment.
- **Kill-count objective text carries a live placeholder**: *"Find and kill the Bandit Ringleaders inside Regent Valley. [6...0] remain."* Objective strings are templates the client fills, not flat text. Anyone building objective text as a plain string will be surprised.
- **Foe levels scale in discrete bands off the LOWEST-level party member at zone entry** (observed on two Vanguard pages), not an average and not the leader.
- **Abandon is town/outpost only** — which is a second, independent witness for `QuestLog:261 MISSION_MAP_OUTPOST == MissionCliGetMap()` at `0x0057BEC8`, sitting one context-menu arm away from the `0x0011` sender. Joining these is nearly free and would move the ABANDON reading from UNVERIFIED to CORROBORATED.
- **4 of 9 Vanguard quest pages carry the literal placeholder `| id = ?`.** The community does not know those ids. **Use GWW ids as a spot-check against a client- or wire-derived table, never as the table.**
- **The wiki tracks a still-patched service**, not a frozen build: `Zaishen Challenge Quest` computes a rotation table live through 23 August 2026, past this session's date.

**Bandit Raid (id 41) is the best literal first authoring target** — single giver (Baron Egan, Pre-Searing Ascalon City), `{campaign = pre, test = n}` prerequisites, two objectives, a small reward bundle, full dialogue already transcribed — closer to minimal than any profession test (combat + skill-teaching + gating) or Poor Tenant (needs bundle items).

---

## 6. Killed: tempting wrong answers, what killed each, and what believing it would have cost

| killed | by what | cost of believing it |
|---|---|---|
| **"The dialogue verb is BLOCKED — nobody knows the reply to `0x0039 INTERACT_AGENT`"** (`test_dispatch.py:128-130`; every lane inherited it) | One corpus query. `0x0080` fires 15 times in 11,241 s2c yet appears before 11/11 selects in one session and 11/11 in the other; `0x0081` names the interacted agent 23/23 with 0 counterexamples; `0x0080`'s string at `t=27.719` is byte-identical for 22 code units to `0x004C[80]`'s at `t=28.241` | **The verb that gates BOTH mandatory Pre-Searing quests would have been scored impossible when it is a msghandler pass plus one probe.** This is CLAUDE.md's BLOCKED-vs-EXPENSIVE failure for the third recorded time. |
| **"Do NOT plan to patch `Gw.dat` for quests"** + *"the honest name path is a bare plain string id"* (lane D) | `toolkit/mapdata/textwrite.py` exists, is committed, is tested, has write guards, and `TESTS.md:508` records 188 authored skill names already shipped through the same path | Authored quest names capped at ArenaNet's existing vocabulary or a ~5-character stub, forever. **Seven lanes missed it, including the one whose entire mandate was "where does quest data live".** |
| **"The quest frame band is ten ids, `0x1000014C..0x10000155`"** (lane C, and the contiguity was its *stated reason* for believing the band is quest-shaped) | The subscribe run does not stop there. Seventeen consecutive sites, `0x0057CB94..0x0057CC6A`, ids `0x1000014C..0x1000015C`, no gaps | **Excludes GmQuestComplete's `0x155..0x159` and QuestMission's `0x15A..0x15C` — i.e. the entire completion half.** A truncated scan reported as a census. |
| **"The Quest UI's subscribe helper is `0x00637BD0`, and GmQuestComplete uses a different one"** (lane B) | `0x0057CBA1 + 0x000B702F = 0x00633BD0`. Every call in the band, GmQuestComplete's included, targets `0x00633BD0` | A fabricated two-bus API. Anyone tracing the completion panel would have gone looking for a second frame system that does not exist. Correct bytes, wrong rel32 arithmetic. |
| **"`PLAN.md:33` is Fournux/Tyria-Extractor's derivation-register row"** (lane D) | §6.1 begins at `PLAN.md:1061` and its 16-row table has no Fournux entry; line 33 is the §1 prior-art landscape table, which grants nothing and gates nothing | **A second-gate breach in progress.** Lane D then adopted Fournux's per-slot naming (location/category, quest name, named NPC) believing the obligation was discharged. Lane D's own authoring implications say the row must be added first — self-contradictory. This is exactly the `gwdat.py` failure §6.1 was built to prevent. |
| **"The description is a PULL; do not send `0x004C` unsolicited on first add"** (lane C, stated as an instruction) | Quest 1462, `t=29.197`, a fresh mid-session accept: `0x0049`, `0x0054`, `0x004C`, `0x0051` all unsolicited — and the client sends `0x0012` anyway at `t=29.214` | A false universal on ArenaNet's own traffic. **What is mandatory is the responder, not the restraint.** |
| **"The `0x003B` code semantics cannot be derived from the wire alone"** (lane E, filed NOT_FOUND) | Deterministic consequence on the same corpus lane E read: code `0x01` → `0x0049`, 5 of 5; code `0x07` → `0x0052`×2 + `0x004A`, 3 of 3 | A capture campaign scheduled to recover something already in the vault. The residual — **no decline code has ever reached the wire** — is real and is now stated precisely. |
| **"Zero `0x0011` in 22,000+ c2s messages"** (lane C) | 22,524 is the **s2c** count. Total c2s across all 12 keyed connections is **971** | A negative advertised as 23× stronger than it is. |
| **"The compass needs no separate work; there is no marker opcode to find and none to implement"** (lane C) | `studies/minimap/FINDINGS.md:721` — `0x0049` at a real client registers the quest and the compass disc is **byte-static across the whole run**; `:727` records the cause as NOT FOUND. Lane C's own claim concedes it did not resolve the last hop into `CompassQuestEffect.cpp` | A prediction from client structure dressed as a finding, contradicting a screen measurement the repo already owned. Subscribing is not drawing. |
| **"Put `quest_type` (0/1/2) in `content/quests.toml`, sourced from the client's compiled comparisons"** (lane B) | No quest message on the wire carries a `questType` field. The client synthesises the 8-byte tag from a 52-byte entry that has no type slot, by a rule nobody recovered | A column that looks measured and is pure invention. And the semantics are CONTESTED anyway: `challengeSortArray` argues type 0 = ordinary quest; the NULL-factory argues type 2. |
| **"Lane B's `questType` and lane F's quest type corroborate each other"** (the arc's designed blind pair) | Three-valued client UI-class discriminator vs five-valued wiki display enum, on different layers. Six quests span two wiki types and would share one `questType` | Would have written a schema collapsing primary/secondary into `questType` and the client's `challenge` into the wiki's Challenge Mission. **The blind pair produced neither agreement nor disagreement, and that must be said rather than glossed.** |
| **"The six-verb taxonomy is UPSTREAM"** (lane G's label) | GWW nowhere says quests reduce to six verbs. `studies/presearing/MANIFEST.md:696-709` built it over wiki-sourced descriptions, from ~15–20 of ≤70 quests | UPSTREAM reads as "somebody else's fact". It is **RECONSTRUCTION**, ours, partial-coverage — **and `PLAN.md:591` grades R4c-1 "6 of 6" against it.** An acceptance bar we authored, not a fact about retail we must hit. Lane A labelled it correctly. |
| **"`studies/smsg` corroborates the Second Profession gate — field 3 is 0 in 64/136 samples"** (lane A) | The 64/136 zero rate is MEASURED. The attribution to the quest gate is the smsg author's gloss, resting on the same wiki-derived belief the MANIFEST used | Two documents sharing one upstream belief counted as two witnesses — structurally identical to the `messages.json`/OpenTyria trap CLAUDE.md names. |
| **"The escort verb inherits `studies/monsterai`'s unrecoverable problem"** (lane A) | `monsterai/FINDINGS.md:7` says ArenaNet's AI *as a mechanism* is unrecoverable. It says nothing about authoring **our own** escort NPC with a path and a fail state; `content/*.toml` has `source = "invented"` for exactly this | Would refuse work the finding never forbade. Escort is EXPENSIVE (invented pathing, invented fail state, will not match retail) — not blocked. |
| **"`asserts.py`'s 13 tail-call sites are a slice of its own ~370-site shortfall"** (lane B) | The tool's shortfall is a `call rel32` sweep (20,131 sites). The tail-call shape is `jmp rel32` (13 sites), outside it | Understates the tool's blind spot. The real floor gap is **≥383**, and the tool's self-reported shortfall is itself a floor. |
| **"R4c-1's criterion is at `PLAN.md:969-970`, proposed and not yet adopted"** (lane A) | `PLAN.md:969-970` is about `dhbuild.py`/`buildid.py` deduplication. PLAN's own R4c-1 wording is at **589-591**, inside §3.2 — and §3 is the repo's single status authority | Quoted MANIFEST's phrasing under PLAN's name, and understated the criterion's standing. Lane G cited it correctly. |
| **"`0x0049`'s string16 cap of 8 code units is OBSERVED"** (lane D) | The cap comes from `schema/messages.json`, which was imported from OpenTyria's `msgdefs.c`. The client's own recovered descriptor prints `string16(0)`; the 78-byte fixed wire size is *consistent* with 8 but does not pin it | A content schema's literal-name limit resting on an OpenTyria field annotation while wearing an OBSERVED label. The longest value ArenaNet ever sends is 5 words, so the boundary has never been tested from either side. |

**A note on how this table was produced, because it matters more than any row in it.** Three verification passes ran against the artifacts, not the prose, and between them they refuted five load-bearing claims, corrected eight, and found two things no lane found. Two of the refutations are lane-vs-lane: **lane B was right on the frame-band width and wrong on the helper VA; lane C was right on the helper VA and wrong on the band width.** Neither lane would have caught its own error, and reading only one of them would have produced a confidently wrong document. That is the same structure `studies/smsg/FINDINGS.md` §7 records — and unlike that pass, the "what this means for our server" half here *was* attacked, which is where the `textwrite.py` and `0x0080`/`0x0081` findings came from.

---

## 7. Open questions, ordered by what each unblocks

### 7.1 Does the client accept a coded string WE authored? — unblocks all quest text

Everything in §3 is decode-side. Nobody has sent a non-empty encoded string on `0x0049` (`probes.py` deliberately sent `"", "", ""`) or a literal on `0x004C`.

**Cheapest decisive test:** change one literal in `toolkit/authsrv/probes.py`'s `_compass_quest_steps` — `enc_name = [0x3D64]` — and look at the quest log. If it reads **Ascalon**, the whole chain from wire code unit to rendered glyph is ours. One probe run, elevated, no new code.

**Second half, same run:** ArenaNet's literals are never bare — the observed framing is `0x0BA9 0x0107 <UTF-16> 0x0001` (template `%str1%`, a marker, the text, a terminator), and `codec.py:352` adds none of it. Send one `0x004C` with that framing built by hand and one without.

### 7.2 Are `0x0080`/`0x0081` the dialog pair? — unblocks the dialogue verb, and therefore R4c-1

The association is strong (§2.5) but it is a correlation over 22 windows plus one byte-identical string, not a handler trace.

**Cheapest decisive test, two parts, neither expensive:** (a) `python toolkit/clientscan/msghandler.py 0x0080 --follow --annotate` and the same for `0x0081`, to confirm which UI frame each posts; (b) one loopback probe sending `0x0081[<a spawned NPC's agent id>]` then `0x0080[<a coded string>]` and looking for a dialog window. Then a labelled live single-action run — talk to one NPC, do nothing else — to separate "open the window" from "answer a branch". **Both mandatory Pre-Searing quests are dialogue-verb quests, so R4c-1's entire quest bar turns on this, not on any of the six verbs being hard.**

### 7.3 Why does `0x0049` draw no compass starburst? — unblocks quest markers

**Reframed, and the reframing is the finding.** `studies/minimap` recorded this as NOT FOUND and lane A recommended disassembling `CompassQuestEffect.cpp`. But the probe sent `plane = 148` where ArenaNet only ever sends 0 or 26, and `home_map = 0` where ArenaNet always sends a real map id (§2.6).

**Cheapest decisive test, in this order:** (1) re-run `compass_quest` with `plane = 0`, `home_map = 148`, `flags = 32` — inside ArenaNet's observed distribution — before touching a disassembler; (2) in the same run, send `0x0051` and `0x0053`, which are the marker-*named* opcodes and which our server has never sent; (3) only then resolve which arm of `CompassQuestEffect`'s jump table at `0x008BC975` is reached from which frame message.

### 7.4 Where does the client get `questType` for a wire-delivered quest? — unblocks any `quest_type` column

The UI addresses a quest by `{questType, id}`; the wire carries a bare `u32`; the 52-byte entry has no type slot. The synthesis rule decides which UI class renders an authored quest.

**Cheapest decisive test:** trace the writer of the 12-byte record `ChCliApi 0x0080DB40` fills, which is also what supplies the `0x10`/`0x20`/`0x40` grouping bits `0x0057DCB1..0x0057DCD7` read. Answering it settles whether we can control quest-log grouping from the server *at all* — which is a separate question nobody has answered either.

### 7.5 What is `CHALLENGES`? — unblocks the authored-id band decision

`UiCtlWebLink:576 challengeId < CHALLENGES` at `0x0088413E` proves the bound exists; nobody read the immediate. Lane A found a GWToolbox++ precedent for neutering exactly this kind of compiled bound-check *specifically so custom quest ids do not trip it* (`studies/profession/WORKAROUNDS.md:460-465`, UPSTREAM), which transfers only where nothing downstream indexes a real array at the out-of-range value.

**Cheapest decisive test:** `codescan.py --dis 0x0088412E --count 20`. Five minutes, and it tells us whether high-band authored ids trip a retail assert before anyone authors one.

### 7.6 What is inside the completion half? — unblocks reward panels

`0x004E`'s three dwords, its instruction-identical twin `0x006C` posting the adjacent frame id, and the five ids `0x10000155..0x10000159` that `GmQuestComplete` subscribes to. **Zero wire samples for any of it.**

**Cheapest decisive test:** the capture in §4.3 item 1 — one narrated live session in which the operator completes a mission. Nothing static will substitute; the panel is a 3D scene fed by five frame messages from five opcodes.

### 7.7 Is `0x0011` abandon?

**Cheapest decisive test:** §4.3 item 4 — one abandon from the log context menu, in an outpost, on a live capture. It settles `0x0011` *and* joins `QuestLog:261` to GWW's town-only statement, converting an UNVERIFIED reading into a two-lineage CORROBORATED one for the price of one action.

### 7.8 What are quests 218 and 222?

**Cheapest decisive test:** one GWW search, `insource:"| id = 218"`, via the `browse-gw-wiki` skill. They occupy the same structural slot in two runs and vary with the character, and they are the evidence that lane F's 41–89 band is a sample rather than a census.

### 7.9 Auditability and documentation debt — cheap, and each is a rule nothing currently checks

- **The coded-string codec belongs in `toolkit/`, not a scratch file.** `encode_id(sid)` / `parse_coded(words)` are ~15 lines of stdlib, now verified 66/66 byte-identical against ArenaNet's wire. Put them beside `textrec.py` with that 66/66 as a test — it is refutable, cheap, and goes red the day the assumption breaks.
- **Land lane D's RC4 scorer and its record set** so the 13-construction negative is auditable rather than a summary.
- **A `test_quests.py` with refutable assertions**, which no lane proposed. `run_suite.py` discovers from disk; `test_srclint.py` §7 enforces `TESTS.md` bidirectionally; `checks.py` requires a declared `floor`. The obvious checks exist and are cheap: every quest row's `enc_*` words re-encode to the varint form; every marker map id is a real `areatable` row or exactly 888; every authored quest id sits outside the observed 41–1462 band. **Without them a quests table is precisely the "rule nothing checks is a wish" CLAUDE.md opens with.**
- **`PLAN.md` §6.1 needs a Fournux/Tyria-Extractor row (MIT, mirrored) before any of its naming is used.** Flagged by `studies/reconstruction/FINDINGS.md` §9.3 on 2026-08-13 and still open; lane D adopted the naming in the meantime.
- **`PLAN.md` §1.7's "four genuinely server-only things" is unamended** since `studies/review/FINDINGS.md:344-350` recommended six or seven on 2026-08-06, and `PLAN.md:277-278` and `studies/srvtree/FINDINGS.md` §6 still cite the four. Quest and dialog state machines belong on that list, and `studies/reconstruction/FINDINGS.md` row 16 already superseded it for quests specifically. **Owner-facing documentation debt, not a code blocker** — but do not cite "§1.7's four" in a quest plan without saying so.
- **`toolkit/content.py:95-96` still declares "verbatim assert expressions with their source path and line" to be ArenaNet's expression and refused.** CLAUDE.md's REFINED 2026-08-12 clause reverses exactly that, and **this entire study is built on single cited asserts.** No lane noticed. A cold session reading `content.py` first would re-run the 2026-08-12 over-refusal that cost 46 hand-rewritten citations.
- **Every binary claim here is build 38797** and none has been re-checked against 38833, which is what the owner's live install now runs. Frame ids and struct offsets probably did not move; "probably" is what the VA-drift rule exists to refuse.

---

## Reproducing this document

Every command below begins from the tree it was run in.

```bash
cd <tree> && git rev-parse --show-toplevel
cd <tree> && python toolkit/vaultpath.py
cd <tree> && python toolkit/clientscan/pinned.py

# §1 — the client's model
cd <tree> && python toolkit/clientscan/srctree.py --under "Gw/Ui"
cd <tree> && python toolkit/clientscan/asserts.py --modules
cd <tree> && python toolkit/clientscan/asserts.py --file QuestLog        # and the other nine
cd <tree> && python toolkit/clientscan/asserts.py --grep "QUEST_TYPE"    # returns 2, not 3
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x0057f17d --count 12
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x0057c2b0 --count 40
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x0057fd20 --count 60

# §2 — the wire
cd <tree> && python toolkit/clientscan/msgshape.py 0x0049   # and 0x004A..0x0055, 0x00FA
cd <tree> && python toolkit/clientscan/msghandler.py --map
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x0080f7a0 --count 85
cd <tree> && python toolkit/clientscan/areatable.py         # the 888
cd <tree> && python toolkit/authsrv/cmsgstream.py 20260807T143055 game
cd <tree> && python toolkit/authsrv/cmsgstream.py 20260810T235916 game

# §3 — where the data lives
cd <tree> && python toolkit/clientscan/textrec.py --dat <vault>/dat_study/Gw.dat 15460 15716 2729
cd <tree> && python toolkit/mapdata/mapchunks.py
cd <tree> && python toolkit/content.py
cd <tree> && python toolkit/origin.py

# §5 — the wiki, via the repo's own skill (GWW 403s scripted fetchers)
#   browse-gw-wiki: Template:Quest_infobox, Template:Mission_infobox,
#   Template:Standard_prerequisites, Bandit_Raid, Category:Ascalon_(pre-Searing)_quests
```

Three measurements in this document came from short scratch scripts rather than committed tools, and each is named where it is used: the `push imm32` frame-bus scan classified by its following call (§1.6), the tail-call assert regex `\xc7\x45\x08(....)\xba(....)\xb9(....)\x5d(\xe9|\xeb)` over `.text` (§1.3), and the `0x0080`/`0x0081` window join over `cmsgstream.timed` (§2.5). **The first two belong in `toolkit/clientscan/asserts.py` and the third in a test; until they land, treat their numbers as reproducible-by-rewriting rather than reproducible-by-running.**
