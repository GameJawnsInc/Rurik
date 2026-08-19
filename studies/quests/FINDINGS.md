# Quests: what the client models, what the wire carries, and how close authoring actually is

**Study arc:** `studies/quests/` · **Date:** 2026-08-15 · **Method:** seven recon lanes (repo knowledge inventory; client assert/disassembly reconstruction; the wire opcode family; where quest data lives; the capture corpus; GWW as an independent lineage; the content-store substrate), then three adversarial verification passes run against the artifacts rather than against the lanes' prose, then this synthesis. Every disputed number below was re-measured for this document. No client, game, or server was launched. `C:\gw` was untouched.

**Client image on every static claim:** `vault/client/2026-07-29_221c13772c7a/Gw.exe`, **build 38797**, the pinned pristine copy (`toolkit/clientscan/pinned.find()`). Every VA is that image's, and **none of it has been re-checked against 38833** — see §7.

**Capture corpus on every wire claim:** the complete live corpus — 6 stamped directories under `vault/captures/live/`, of which **3 carry decrypted game channels** (`20260807T133758`, `20260807T143055`, `20260810T235916`), **12 game connections, 971 c2s GAME_CMSG and 22,524 s2c GAME_SMSG**, `cmsgstream.frame_report` residual **0** on 12 of 12. All 27 live-origin files sit under `captures/live/` and nowhere else (`toolkit/origin.py`).

---

> **New here? Read [HANDOFF.md](HANDOFF.md) first** — the traps, in the order they
> bite, and what to read next. This file is ~1,200 lines and is not meant to be read
> front to back to start work.

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

#### Q7: the quest leaves the log, and ArenaNet's doubled `0x0052` is NOT required

**OBSERVED**, `vault/captures/harness/20260816T002523`, build 38833, map 449. The server now runs the lifecycle rather than replaying a script: the probe places the giver and stops, and every quest message after that is a reply to a click.

```
c2s 0x0039 INTERACT      -> 0x0080 our line, 0x0081 flush, 0x007E accept option
c2s 0x003B 0x85B701      -> 0x0049 QUEST_ADD[1463],  then 0x0012 -> 0x004C
c2s 0x0039 INTERACT      -> the same window, now carrying the TURN-IN option
c2s 0x003B 0x85B707      -> 0x0052 QUEST_REMOVE[1463]  (ONCE)
                            0x004A QUEST_REMOVE_AND_UNLIST[1463]
```

On screen afterwards: **Active Quests empty, Quest Summary empty, and the tracker line under the level bar gone.** The dialog offers *"I spoke to the gate guard."* rather than the accept line, so the giver's offer switches on held state.

**The doubling is not load-bearing. OBSERVED.** ArenaNet sends `0x0052` twice then `0x004A`, 3 of 3, and §4.2 flagged that as exactly the shape a party broadcast would have. **One `0x0052` removes the quest.** That is consistent with `0x0052`'s body at `0x0080F7A0` being a binary-search deleter — a second call has nothing to find — and it means a solo corpus could never have separated "protocol" from "one player's copy of a two-player message" by counting.

**It does not prove the second copy IS a party broadcast**, and nothing here can: every live session is a solo operator. What is now established is narrower and enough to build on — **the second `0x0052` is not required for the client to remove a quest**, so our server sends one. The party reading stays UNVERIFIED and its test is still §4.3 item 3, a two-player capture.

**No reward was granted and none was looked for.** The completion family (`0x004E`, `0x006C`, `0x0096`, `0x0097`, `0x00FB`) is still 0 of 22,524.

**Still open:** `0x007E`'s `field1` kind enum (7 values, none named); whether an option can be declined; **and the marker is not maintained** — we send `0x009F [11, agent, 5]` once and never update it, where ArenaNet flips it to 4 on accept and back to 5 on turn-in. The giver keeps a green `!` while holding a quest it cannot offer. That is a server-side gap, not a protocol unknown, and the transitions to copy are already measured above.

**Superseded: candidate 3** (replay the 43-unit offer line) is moot; the option was never in the dialog string.

~~**Remaining candidates are now 2 and 3 above**~~, and 2 should be done properly before 3: the earlier scan looked only at the window between `INTERACT` and the click, which is where the original hypothesis came from and also its blind spot. Widen it to the whole session and diff what precedes a giver interaction against a non-giver one. `0x004B` (bulk assign of the `+0x518` list, `array32[64]`) and `0x00FA` (`array32[32]`, once per session at map load) are the two load-time bulk assignments in the corpus that **carried empty arrays and therefore no evidence**, and a per-NPC available-quest list is exactly the shape either could have.

**The overhead marker glyphs, MEASURED 2026-08-16 — and one of them refutes a reading this document carried.**

`--probe quest_marker_states` walked one NPC through every state with `--shots 1`, holding each 7 s so no state could fall between frames the way it had three times before. `vault/captures/harness/20260816T104707`.

| property | glyph | label |
|---|---|---|
| *(none yet)* | nothing | the baseline, and it is what makes the rest a measurement rather than a description |
| `11 = 5` | green **`!`** | OBSERVED |
| `11 = 4` | green **down arrow** | OBSERVED |
| `11 = 3` | green down arrow, **indistinguishable from 4** | OBSERVED |
| `12 = 0` | nothing — back to baseline | OBSERVED (was RECONSTRUCTION) |

**`4` does not draw a `?`.** This document and `questdefs.py` both said it did, on the strength of the owner's description of the in-game behaviour plus the corpus's state transitions. The state reading was right — 4 *is* what ArenaNet sends when a held quest is turn-in-able at that NPC, and the accept/turn-in flips are unchanged — but the glyph is an **arrow**, which reads as *"this NPC is your objective"*. The `?` the owner described is real in-game; mapping it onto property-11 value 4 on this NPC was the inference, and that is what fell. Where the `?` does come from is now an open question, and the two surfaces this run did not touch are the dialog window and the compass.

**`3` and `4` are the same glyph here.** Four frames of each, differing only in the marker's bob phase. Whatever distinguishes them is not the overhead mark, so a state machine cannot use the glyph to tell them apart — and we still emit 3 nowhere, now for a second reason: we cannot say what sending it would communicate.

**The CLEAR is measured.** `[12, agent, 0]` took the glyph down to a bare head. Its *value* range is still never exercised (0 in 22 of 22 and 16 of 16), so "property 12 clears" is OBSERVED and "what a non-zero property 12 does" is not.

**The property-11 glyph vocabulary, swept 2026-08-16 — and the `?` is NOT IN IT.**

`--probe quest_marker_sweep` walked one NPC through values 0–9 with a **CLEAR between every value**, so each is a run of glyph-bearing frames bracketed by bare ones and the frame→value mapping is read off the green-pixel trace rather than computed from the probe clock. `vault/captures/harness/20260816T110535`.

| value | glyph | |
|---|---|---|
| 0 | green **`!`** | same as 5 — 0 is *not* "no marker" |
| 1 | green **diamond / gem** | stable across its frames |
| 2 | a **rotating** object | changes shape frame to frame; not nameable from 3 frames |
| 3 | green **down arrow** | *(earlier run)* |
| 4 | green **down arrow** | *(earlier run)*, indistinguishable from 3 |
| 5 | green **`!`** | the control |
| 6 | faint vertical shape | translucent |
| 7 | solid vertical shape | |
| 8, 9 | **nothing** | |

**Eight of ten values draw something.** The corpus only ever carries 3, 4 and 5, so the overhead marker vocabulary is substantially wider than one operator's route revealed — which is what the "two witnesses to a route, not to the protocol" caveat has been warning about since §4.1.

**NOT FOUND: a `?` anywhere in 0..9.** The owner reports a `?` replacing the `!` over an NPC whose given quest is in progress. The in-progress states are exactly 3 and 4, and on build 38833 both draw a **down arrow**. So on this build, that surface, that NPC, the `?` is not what property 11 renders.

**Method note that cost two readings before it was adopted.** These are 3D icons; value 2's changes shape frame to frame. A single frame is therefore not a reliable glyph identification, and any claim made from one — including this document's earlier "4 draws `?`" — should be re-read as a claim about one animation phase. Values 0, 1, 3, 4 and 5 were checked across multiple frames and are stable; 2, 6 and 7 were not, and their rows above are correspondingly weaker.

**Where the `?` might still be, neither checked:** the **quest tracker** under the level bar — `studies/minimap/FINDINGS.md:721` recorded a `?` there when `0x0049` fired with EMPTY strings, which reads as a missing-text placeholder rather than a state marker, and our reward run showed real text in that slot with no `?` — and the **dialog window**. Both are surfaces no run in this arc has interrogated.

**THE `?` IS THE OPTION KIND. Found 2026-08-16, in the dialog, after three runs looked for it over the NPC's head.**

`--probe dialog_icons` put one `0x007E` of every kind into a single window, each line labelled with its own kind number, so the icons are compared inside one frame rather than across six screenshots. `vault/captures/harness/20260816T111948`.

| kind | code | icon | reading |
|---|---|---|---|
| 16 | `0x01` | green **tick** | accept |
| 17 | `0x02` | red **prohibition** | decline |
| 18 | `0x03` | gold **`!`** | a quest available to take |
| 21 | `0x04` | green **dot** | advance |
| 22 | `0x05` | gold **`?`** | a quest already in progress |
| 23 | `0x07` | a **bag** | turn in |

**So the `!` and the `?` are one mechanism — the option kind — and the kind is bound 1:1 to the `0x003B` code (§8.2, 41 of 41).** The owner's description maps exactly: kind 18 while the quest is available, kind 22 once it is in progress. Every icon is a distinct, legible glyph, and the bag on the turn-in line is the reward the completion panel would pay.

**A name this repo invented and carried for three weeks was wrong.** `0x007E`'s field 4 is `0xFFFFFFFF` in 41 of 41 and was called `OPTION_NO_ICON` on that and nothing else. The icons come from the **kind**; every field 4 in this run was `0xFFFFFFFF` while six different icons drew. Renamed `OPTION_FIELD4_ALWAYS`, which says only what is known. Two readings survive and neither is testable from the corpus: an icon *override* whose `0xFFFFFFFF` means "use the kind's own", or something unrelated to icons.

**A gap this exposes in our own server, unbuilt:** `_quest_lines` returns `SERVICE_TURN_IN` the moment a quest is held, so we emit kind 23 and **never kind 22**. That is honest for `rurik_first_errand`, whose objective completes on acceptance, but it means a quest with real objectives would show a bag rather than a `?` while it was still in progress. The state to send is 22 until the objective completes and 23 after — and we have no objective state to make that turn on.

**The objective state, built 2026-08-16 so kind 22 can fire.**

`_quest_lines` used to return `SERVICE_TURN_IN` the instant a quest was held, so the option kind went 18 → 23 and **kind 22 was unreachable** — the state existed on the wire and had no way to happen on our server. It now returns three states, bound to the agent being spoken to:

| player's state | code | kind | icon |
|---|---|---|---|
| not held | `0x03` SHOW | 18 | gold `!` |
| held, objective unmet | `0x05` IN_PROGRESS | 22 | gold **`?`** |
| held, objective met | `0x07` TURN_IN | 23 | bag |

The quest gains a second NPC. `giver_agent` offers it; `objective_agent` — the gate guard — completes it, and talking to that agent is an **event, not a menu**: `_objective_quests` is separate from `_quest_lines` precisely so the guard never offers the quest it finishes. Completion sends `0x0054` with the row's `objectives_done` line, and sends `0x004C` first if the client never asked, because `0x0054` is a silent no-op until `DESC_FILLED` is set (§8, the gate at `0x0080F9CD`).

**Verified as logic, not on screen, and the distinction matters.** Kind 22's *rendering* is measured — `dialog_icons` drew the gold `?`. What was unverified is that our server ever *emits* it, which is pure state and is driven end to end by `test_quests.py` §14: SHOW before accepting, IN_PROGRESS once held, TURN_IN once the guard is visited, the guard offering nothing in any state, and the objective refusing to re-fire. **A five-click live sequence against two NPCs was attempted three times and produced no interaction at all** — the harness cannot reliably hit an NPC's screen position, and the camera faces a different way each run. That is a harness limit, not a protocol unknown, and it is the honest reason this rung has a unit test where the others have a capture.

**Two things in the new path are RECONSTRUCTION and labelled so in the code.** What a code-`0x05` click does — offered 3 times in the corpus, clicked 0 — so our arm shows a reminder screen with no options rather than inventing a state change. And `objective_agent` binds by **agent id**, which is per-connection and per-spawn: a probe-world binding, not a content one. A real binding needs a spawn row with a stable key, which is rung R5.

**THE `?` IS OPTION KIND 22, IN THE DIALOG — OBSERVED 2026-08-16, on the owner's screen.**

Three runs looked for it over the NPC's head and it was never there: property 11 draws eight glyphs across values 0–9 and not one is a `?`. It is the **option kind on the dialog line**. A window titled with the NPC's name shows the quest as one clickable row, and while the quest is held-and-unfinished that row carries a gold `?` where an available quest carries a `!`.

So the icon column of `0x007E` is the KIND field, and the kind↔code table already measured from the corpus is the whole vocabulary:

| kind | code | icon |
|---|---|---|
| 18 | `0x03` | `!` — a quest available to take |
| 22 | `0x05` | **`?`** — one already in progress |
| 16 | `0x01` | green tick — Accept |
| 17 | `0x02` | red prohibition — Decline |
| 23 | `0x07` | a bag — turn in |

**Field 4 is exonerated.** It is `0xFFFFFFFF` in 41 of 41 and this repo named it `OPTION_NO_ICON` on that evidence alone — a guess dressed as a name. The icon comes from the kind, so field 4 is unexplained again and the name should be read as a placeholder, not a finding.

**Why it took three runs.** The owner's phrasing — a `?` "instead of a `!`" — is exactly right about the game and I mapped it onto the overhead marker, which is the other place a `!` appears. The corpus could not settle it either way: kind 22 is offered 3 times and clicked 0, so nothing in the capture shows what it renders. The measurement needed a person to talk to an NPC and look.

**KNOWN BUGS, LEFT OPEN 2026-08-16 by the owner's decision — and they are ONE fix, not two.**

1. **`INTERACT_RANGE = 250.0` is too far.** Ours, admitted unmeasured. Reading ArenaNet's off the corpus failed: the player's position is unknown at most interact moments and the agent positions available are stale spawn coordinates, giving 541–4275 units, which is a bad join rather than a range.
2. **Clicking an NPC does not walk the player to it.** In stock, a click on a distant NPC walks you over and the dialog opens on arrival; ours does not move the player at all.

**Why they are one fix:** the range gate is only correct once the walk exists. Tightening (1) without (2) would leave a player unable to talk to anything they are not already standing on — the quest would become unplayable in exactly the way the gate was meant to make it realistic. The corpus supports the pair: the client sends `0x0039` from wherever the player stands and ArenaNet answers 23 of 29, leaving 6 unanswered, which is a server ignoring an out-of-range ask while the client walks the player in.

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

**Label: OBSERVED for the association and the byte-identical string; RECONSTRUCTION for the names.** No assert has been traced to either handler and neither has been fired at a client.

> **SUPERSEDED 2026-08-15 on the last clause, and it was true when written.** Both have now been fired at a retail client by this server: `0x0080` then `0x0081` opens the NPC dialog window (rung Q4), and `0x0081` with no preceding `0x0080` **closes** it — so `0x0081` is the flush/show and not a second text message. `schema/overrides.json` names them `NPC_DIALOG_TEXT` and `NPC_DIALOG_SHOW`, `high`, on those two lineages (rung Q1, §9). What is *still* unsettled is the six extra `0x0081` firings at quest-accept instants, which a labelled single-action run would separate. But *"dialogue is blocked because nobody knows the reply"* is dead, and the two opcodes to confirm are named, shaped, and already decodable by our codec.

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
| **"`0x0049`'s string16 cap of 8 code units is OBSERVED"** (lane D) | The cap came from `schema/messages.json`, imported from OpenTyria's `msgdefs.c`. The client's own recovered descriptor printed `string16(0)`; the 78-byte fixed wire size was *consistent* with 8 but did not pin it | A content schema's literal-name limit resting on an OpenTyria field annotation while wearing an OBSERVED label. The longest value ArenaNet ever sends is 5 words, so the boundary has never been tested from either side. **SUPERSEDED 2026-08-19 — the label is now defensible, as CORROBORATED.** That `string16(0)` was a `msgshape.py` display defect, not a silent descriptor (`studies/heroes/FINDINGS.md` §9, fixed `c81d6d1`). The recovered descriptor reads `[u32, vec2, u16, u16, u32, string16(8), string16(8), string16(8), u16]` — **three** wide strings of capacity **8**, and the 78-byte total closes on them exactly (2+4+8+2+2+4+3×18+2). So the cap is pinned by the client's own table, a witness genuinely independent of OpenTyria; the two agree. What does **not** change is the last sentence: the boundary is still untested from either side, and three fields where lane D discussed one is worth re-reading. |

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

> **HALF-ANSWERED 2026-08-16, and the wrong half of that paragraph was the confident one.** *"Nothing static will substitute"* was written while **half the join sat in this document's own §1.6 table**: `0x004E`'s handler body is `0x0080F670` (§2.1) and `0x0080F6C7` publishes `0x10000155` (§1.6), 0x57 bytes inside it. Read from the bytes rather than from the arithmetic, `0x0080F670` does `push 0x10000155` / `call 0x00633D70` — the **post** helper, not the `0x00633BD0` subscribe helper — with no `int3` padding in between, so the publish site is inside this handler and not a wedged-in helper. **`0x004E` feeds `GmQuestComplete`, statically, and the opcode is renamed `QUEST_COMPLETE_PANEL`** (§9). The 2026-08-13 sweep had already fired it at a client and photographed a centre-screen banner animation, which is what §1.5's model-and-light scene looks like from outside — two lineages sharing no ancestry.
>
> **What the live capture is still needed for is the OTHER half, and it is the half that matters for authoring:** what the panel expects *in* those three dwords. Firing the opcode is now cheap; knowing what to put in it is not. Do not read this as the reward arc being unblocked — read it as the reward arc being one loopback run away from its first real question.

### 7.7 Is `0x0011` abandon?

**Cheapest decisive test:** §4.3 item 4 — one abandon from the log context menu, in an outpost, on a live capture. It settles `0x0011` *and* joins `QuestLog:261` to GWW's town-only statement, converting an UNVERIFIED reading into a two-lineage CORROBORATED one for the price of one action.

### 7.8 What are quests 218 and 222?

**Cheapest decisive test:** one GWW search, `insource:"| id = 218"`, via the `browse-gw-wiki` skill. They occupy the same structural slot in two runs and vary with the character, and they are the evidence that lane F's 41–89 band is a sample rather than a census.

### 7.9 Auditability and documentation debt — cheap, and each is a rule nothing currently checks

- ~~**The coded-string codec belongs in `toolkit/`, not a scratch file.**~~ **DONE 2026-08-17.** `toolkit/clientscan/codedstr.py` carries `encode_id` / `decode_id` / `parse_coded`, and `test_codedstr.py` (18 checks, floor 12) holds the 66/66, the per-slot shape partition and the plain-22/encrypted-44 split — each of §3.2's numbers, refutable. Sabotage confirms it: `BIAS = 0` fails 8 checks. **Two things surfaced in the doing.** (1) The ENCODE half had never existed anywhere — `questdefs.coded_literal` builds a literal run and never encodes an id — so 3.2's headline number was reproducible only by rewriting the script that produced it. (2) **`questdefs.py`'s `LITERAL_MARK` comment read "archive id 263", which is the RAW WORD**; the id is 7, and §3.2 says so. That is the rival reading this section spends a paragraph refuting, sitting in a live comment two lines below a neighbour (`TEMPLATE_STR1`, id 2729) that had it right. Both are now asserted at import, and the bare-framing guard uses `codedstr.BIAS`/`CONT` rather than repeating `0x100`/`0x8000`, so the rule has one home.
- **Land lane D's RC4 scorer and its record set** so the 13-construction negative is auditable rather than a summary.
- **A `test_quests.py` with refutable assertions**, which no lane proposed. `run_suite.py` discovers from disk; `test_srclint.py` §7 enforces `TESTS.md` bidirectionally; `checks.py` requires a declared `floor`. The obvious checks exist and are cheap: every quest row's `enc_*` words re-encode to the varint form; every marker map id is a real `areatable` row or exactly 888; every authored quest id sits outside the observed 41–1462 band. **Without them a quests table is precisely the "rule nothing checks is a wish" CLAUDE.md opens with.**
- ~~**`PLAN.md` §6.1 needs a Fournux/Tyria-Extractor row (MIT, mirrored) before any of its naming is used.**~~ **DONE 2026-08-17, and it turned out to be two rows and a licence obligation.** Flagged by `studies/reconstruction/FINDINGS.md` §9.3 on 2026-08-13 and by this list on 2026-08-15; lane D adopted the naming in the meantime. §6.1 now carries `textrec.py` (the `id // 1024` split, **not** re-derived by us) and `skilltable.py` (the 0xA4 layout, re-derived), `THIRD-PARTY-NOTICES.md` carries the MIT notice, and three further citations are recorded as owing nothing. **The reason it sat four days is the useful part: the flag lived here and the obligation lives in `PLAN.md`, and nothing checked.** `toolkit/derivlint.py` checks it now -- per-upstream, because 21 upstreams appear in 223 module pairs and a per-pair rule would be permanently red.
- **`PLAN.md` §1.7's "four genuinely server-only things" is unamended** since `studies/review/FINDINGS.md:344-350` recommended six or seven on 2026-08-06, and `PLAN.md:277-278` and `studies/srvtree/FINDINGS.md` §6 still cite the four. Quest and dialog state machines belong on that list, and `studies/reconstruction/FINDINGS.md` row 16 already superseded it for quests specifically. **Owner-facing documentation debt, not a code blocker** — but do not cite "§1.7's four" in a quest plan without saying so.
- ~~**`toolkit/content.py:95-96` still declares "verbatim assert expressions with their source path and line" to be ArenaNet's expression and refused.**~~ **FIXED 2026-08-16.** CLAUDE.md's REFINED 2026-08-12 clause reverses exactly that, and **this entire study is built on single cited asserts.** No lane noticed. A cold session reading `content.py` first would re-run the 2026-08-12 over-refusal that cost 46 hand-rewritten citations. The comment now says BULK DUMPS and carries the correction with its cost; `PLAN.md` §7 Q3's own REFUSED bullet gained a forward-pointer to the refinement three paragraphs below it, because that bullet is the other place a reader can stop early. The dated 2026-08-11 ruling text was **not** rewritten — it is a decision record and is supposed to say what was decided that day.
- ~~**Every binary claim here is build 38797** and none has been re-checked against 38833.~~ **RE-CHECKED 2026-08-17, and every one of them HOLDS.** The bullet closed with *"probably did not move; 'probably' is what the VA-drift rule exists to refuse"* — so it was measured instead. **The eleven handler bodies were re-derived by a DIFFERENT ROUTE** (`msghandler.classify`, which reads the client's own receive table) and came back 11 of 11 identical to §2.1's table on 38797, then **unmoved on 38833**. All twelve byte-level citations — the log's `0x34` stride, `+0x52C`/`+0x534`/`+0x528`, the description-filled gate, both frame-bus helpers and the `+inf` constant in `.rdata` — are **byte-identical** across the two builds. The frame-bus pairing is 11 of 11 on both. `CHALLENGES` is **1465** on both, so the authored-id band is unchanged. `areatable`'s extent is **888** on both, from the same table VA.
  **What DID move:** the dispatch stubs (`0x0091DBD0` and neighbours, uniformly `+0x60`) and the `UiCtlWebLink:576` assert site (`+0xD0`). §2.1's prose survives because it names the block, not the stub. **And the scope is smaller than "stable":** on the vaulted **38519** build, ~90 days older, **0 of 12 sites match and the frame-bus scan finds nothing in any quest body**. The true claim is that nothing moved across the 15-day 38797→38833 patch — not that these addresses are durable. `test_quests.py` §20 keeps measuring it, and uses 38519 as its control.

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

---

### 8. The two-screen dialogue — the correction, the tables that force it, and the marker rule

**Date:** 2026-08-16 · **Method:** four recon lanes over the same corpus (option/code census; the description-and-reward screen; the single-quest quirk and the menu screen; marker semantics), then one adversarial verification pass run against the artifacts rather than the lanes' prose. Every number below was re-measured for this section; where the verifier corrected a lane, the corrected wording is what appears here. No client, game or server was launched. `C:\gw` was untouched.

**Corpus for the whole section:** the two keyed live sessions that carry quest traffic, `20260807T143055` and `20260810T235916`. `20260807T133758` carries **0** `0x007E`, **0** `0x003B` and no quest opcodes and contributes nothing. `cmsgstream.frame_report` residual **0** on 24 of 24 connection rows (12 connections, both directions), so every census here is exact for the corpus rather than best-effort.

**One caveat that qualifies every "both sessions reproduce it" below, and §4.1 already established it:** the two sessions are *the same scripted route run twice*, with two characters. Reproduction across them is replication of a route, not an independent sample of the protocol. Two witnesses to a route is what it is worth.

---

#### 8.1 The correction: we collapsed two screens into one

**Our server implements a one-screen flow. ArenaNet's is two.** The `INTERACT` arm in `authsrv.py` builds a list in which each line is *the accept itself* — it emits `OPTION_KIND_QUEST` (18) carrying `SERVICE_ACCEPT` (`0x01`), and a second line carrying `0x07` for a turn-in — so clicking a quest's name in our window immediately adds the quest. §0's Q5 acceptance run is the proof that this is what we built: `0x007E [18, "Accept: …", 0x85B701, 0xFFFFFFFF]` → click → `0x0049`. It worked, and it is the wrong shape.

**What the corpus shows.** A dialogue option carrying a quest name is an **entry point**, not an accept. Clicking it (code `0x03`) draws a *second screen* — the quest's description prose, its reward, an **Accept** line and a **Decline** line — and only the Accept line adds the quest. The two screens are distinguishable from the wire without reading a word of prose:

| | screen 1 — the MENU | screen 2 — the DESCRIPTION |
|---|---|---|
| `0x0080` text | exactly **10** code units, one constant template | **40–62** code units, leading with the quest's own string id |
| option kinds | 18, 22, 21, 15 | 16 + 17, or 23 alone |
| n (screens) | 9 | 17 |
| n (options) | 13 | 28 |

**OBSERVED, and this is a partition with zero crossovers: 41 of 41.** Kinds {15, 18, 21, 22} occur *only* on 10-unit screens (`{10:13}`); kinds {16, 17, 23} occur *only* on screens of 40–62 units (kind 16 `{40:2, 41:1, 43:2, 44:1, 56:1, 59:3, 62:1}`, kind 17 identical, kind 23 `{40:2, 43:2, 56:1, 59:1}`). A single `0x0080` field carries both; nothing else in the message distinguishes them.

**The narrative, re-measured, `20260807T143055` connection `:60935`, agent 99:**

```
26.816  s2c 0x0080(10u) 0x0081  0x007E kind=18 tag=0x805003   quest 80   code 3
                                0x007E kind=18 tag=0x85B603   quest 1462 code 3
27.679  c2s 0x003B 0x805003                                   the NAME was clicked
27.719  s2c 0x0080(43u) 0x0081  0x007E kind=16 tag=0x805001   quest 80   code 1   ACCEPT
                                0x007E kind=17 tag=0x805002   quest 80   code 2   DECLINE
28.147  c2s 0x003B 0x805001                                   the ACCEPT was clicked
28.179  s2c 0x0049 QUEST_ADD[80] · 0x0081 (bare)              added, and the window closes
```

**So §0's Q5 result is confirmed as a mechanism and wrong as a model.** The tag round-trip, the ordering rule and `decode_service_select` all stand unchanged. What is wrong is that our single option pairs kind 18 with code `0x01` — **a pairing that occurs 0 times in 41 samples** — and that a player of our server can accept a quest without ever being shown its description, its reward, or a way to refuse.

---

#### 8.2 The kind × code table, complete

**OBSERVED. The kind field of `0x007E` and the low byte of its tag are in bijection — seven kinds, seven codes, one pair each, 41 of 41, zero off-diagonal.** Both sessions independently exhibit all seven pairs.

| kind | code | n | 143055 | 235916 | offered | clicked | reading | label |
|---|---|---|---|---|---|---|---|---|
| 15 | `0x80` | 2 | 1 | 1 | 2 | **0** | *unexplained* — see below | one fixed id, 10725 |
| 16 | `0x01` | 11 | 6 | 5 | 11 | 10 | **accept** | per-quest |
| 17 | `0x02` | 11 | 6 | 5 | 11 | **0** | **decline** | per-quest |
| 18 | `0x03` | 6 | 3 | 3 | 6 | 4 | **quest name / entry point** | the quest's own name id |
| 21 | `0x04` | 2 | 1 | 1 | 2 | 2 | **advance** | the quest's own name id |
| 22 | `0x05` | 3 | 2 | 1 | 3 | **0** | **in progress** | the quest's own name id |
| 23 | `0x07` | 6 | 3 | 3 | 6 | 6 | **turn in** | one fixed id, 10719 |
| | | **41** | 22 | 19 | 41 | **22** | | |

Codes `0x00` and `0x06` never appear. Kinds **19 and 20 are absent** — an unexplained gap between 18 and 21. Kind **12** (`0x0C`) is special-cased inside the client's own option handler at `0x00509582` (`cmp dword ptr [edi], 0xc / jne`, and on equal it returns without creating an option frame) and appears **0** times on the wire.

**These are floors on the protocol, not a census of it.** Twenty-two clicks are one operator's route run twice. Four codes of seven were ever clicked; three were only ever offered.

**Kind 15 is not a quest option at all. OBSERVED.** Its tag is `0x00000080` — the `0x800000` tag bit is **clear** and the quest-id field is 0 — the only `0x007E` in the corpus whose tag is not a quest tag (bit-23 census: set 39, clear 2; high byte `{0: 41}`). `questdefs.decode_service_select` correctly returns `None` for it, and `encode_service_select` **cannot emit it**, because it unconditionally ORs `SERVICE_TAG_BIT`.

**Kind 15's placement is OBSERVED; its meaning is RECONSTRUCTION.** Both occurrences are at agent 36, on the `INTERACT` immediately after that NPC's last held quest was turned in and unlisted — `t=93.314` after `0x004A[82]` at `t=92.792`, and `t=128.454` after `0x004A[86]` at `t=126.917`. It was never clicked and its label id is `needs_key = True`. "The screen an NPC shows when it has nothing left" is a reading of its position in a timeline. Three lanes labelled this three different ways (RECONSTRUCTION / UNVERIFIED / OBSERVED) off identical evidence; **RECONSTRUCTION is the correct one.**

**Kind 21 IS a quest option and it was clicked, 2 of 2. OBSERVED.** Code `0x04`, quest 62, offered by agent 7 on `:64102` (`t=218.512`, clicked `t=221.576`) and agent 8 on `:49160` (`t=266.312`, clicked `t=266.856`) — in both cases on a *different map connection* from the NPC that gave quest 62, ~45 s after the accept. Its reply is `0x0054 QUEST_OBJECTIVES_UPDATE[62]` + `0x0051 QUEST_MOVE_MARKER[62]` and **no `0x0049`, no `0x004A`** — an advance, not an add and not a completion — followed by a 4-code-unit screen with zero options.

**A confound two lanes reported as part of that reply and it is not.** The same 46 ms batch also carries `0x0054[1462]` + `0x0051[1462]`. That pair also rides the code-`0x01` replies at `t=173.527` / `t=220.709` and the code-`0x07` replies at `t=92.746` / `t=126.864`. It is ambient to quest 1462 and must not be attributed to code `0x04`.

**Two corrections to §0's Candidate 2 block fall out of the full census.**

- **`field4` is `0xFFFFFFFF` in 41 of 41, not "37 of 37".** The same 37 is asserted in `toolkit/authsrv/questdefs.py:170`. **Where 37 came from could not be reconstructed** — restricting to the four town/explorable connections (`:60935`, `:62994`, `:61193`, `:61624`) gives **39**, and no subset the verifier could construct gives 37. Fix the number; `OPTION_NO_ICON` is unchanged.
- **The reply-count table in §2.4 is per-session, not per-corpus.** Reading both sessions doubles it: code `0x01` n=**10** (6× `{0x49,0x4C}`, 4× `{0x49,0x4C,0x51,0x54}` where the `0x51`/`0x54` name quest 1462); code `0x07` n=**6** (`0x0052`×2 then `0x004A` in 6 of 6); code `0x03` n=**4**; code `0x04` n=**2**.

**Per-quest label ids are adjacent by role. OBSERVED.** The accept-line id is exactly one below the decline-line id, 6 of 6 in the four-unit form: q62 `0x166A`/`0x166B`, q80 `0x1704`/`0x1705`, q82 `0x1716`/`0x1717`, q86 `0x1744`/`0x1745`, q218 `0x14EE`/`0x14EF`, q222 `0x150A`/`0x150B`. Kinds 18, 21 and 22 all reuse the quest's **own name id** — byte-identical to slot 1 of `0x0049`/`0x0050` in 11 of 11, e.g. quest 80's name `1703 A86E 9E9B 4C82` is also its kind-18 and its kind-22 label.

**UNVERIFIED and flagged before use: the five-unit varint form.** Quest 1462's ids were published by one lane as name 80660, accept 80672, decline 80673, off a 5-unit run with prefix `0x8102`. Every four-unit id in the pool re-measures exactly; **these three did not reproduce under `textrec.REF_BIAS`**, and the decoder that produced them is not in the evidence. Do not put those numbers in a document or a content row until the decode is named.

---

#### 8.3 Code `0x02` is DECLINE, and why a click-only search could not see it

**OBSERVED. The decline line is on the wire and it is paired with its accept without exception: every kind-16 option is accompanied, in the same burst at the same timestamp, by a kind-17 option carrying the same quest id and code `0x02`. Kind-16 with a same-burst same-quest kind-17: 11. Kind-16 without: 0. Kind-17 without a kind-16: 0.**

**The consequence remains NOT FOUND, and that half must not be invented.** Code `0x02` was clicked **0 of 22** times — the operator never declined — so no s2c reply to a decline exists anywhere in the corpus. GWW says declined quests remain available; the wire is silent.

**`questdefs.py:138`'s "NOT FOUND: a DECLINE code. Do not invent one" is now half wrong, in the direction that matters.** The value *is* observed. Leaving the comment as it stands invites a future session to re-derive it or, worse, to invent a different number.

**The methodological lesson, and it is worth one sentence because it cost this arc a whole rung: §2.4 derived the code semantics from *consequence*, which can only see codes the operator clicked — an option that is offered and never selected is invisible to a click-driven search, and the decline line was sitting in 11 `0x007E` messages the whole time.** Census the **offers** as well as the clicks; the two ledgers answer different questions.

---

#### 8.4 Screen 2 — the description, and where the reward actually is

**OBSERVED. Every `0x003B` code `0x03` is answered with exactly four messages in a fixed order: `0x0080`, `0x0081`, `0x007E` (kind 16), `0x007E` (kind 17). 4 of 4**, at `+0.037` to `+0.048` s. Never two `0x0080`, never one or three options.

**OBSERVED. A check that could have failed and did not.** Screen 2's line length differs between the two sessions by exactly the difference in the player's character-name length: q80 is 43 units in `143055` and 40 in `235916`; q1462 is 44 and 41. The substituted literal is 11 code units (`<11 UTF-16 units: the player's own character name>`) against 8 (`<8 UTF-16 units: the second character name>`). 11 − 8 = 3 = 43 − 40 = 44 − 41.

**OBSERVED, and it is the finding that makes reward authoring cheap: there is no reward message and no reward string. The reward is a 19-code-unit SUFFIX inside the same coded string, byte-identical between the `0x0080` dialog line and `0x004C`'s description slot in 17 of 17 (screen, quest) pairs.**

```
0002 2AE8 E7D4 E5CC 3672            ref 10728
0002 2AEA 8C3F B519 6611 0101 <A>   ref 10730, one numeric argument
0002 2AEC DAC7 81AE 3482 0101 <B>   ref 10732, one numeric argument
```

All three ids are `needs_key = True` — ArenaNet's own generic strings, encrypted, shared by every quest. **So a reward block costs us three ids and two numbers of our own and no authored text from either side**, which is exactly CLAUDE.md's "commit the id, resolve the string at run time".

**CORROBORATED (not OBSERVED): `0101 <word>` is a numeric argument with value `word − 0x100`.** The offset is `textrec.REF_BIAS = 256`, our own decoder's convention, and the discriminator is read out of the owner's archive rather than off a rendered pane: quest 62's fourth run feeds the **plain** template 2438 (`%str1%: %num1%`, `needs_key = False`) exactly `0101 0104` in its numeric slot. The rival reading — that these are string ids — would resolve the reward numbers to plain UI records 100, 250, 500, 25 and 10, which are unrelated records of the wrong kind and length for a reward line. The arithmetic then gives:

| quest | A (ref 10730) | B (ref 10732) |
|---|---|---|
| 80 | 100 | 10 |
| 218, 222, 62 | 250 | 25 |
| 82, 86 | 500 | 25 |
| 1462 | 500 | 100 |

**"A is experience and B is gold" was RECONSTRUCTION. The probe ran on 2026-08-16 and it is now OBSERVED.** `probes.py --probe quest_reward` fed slot A **111** and slot B **222** -- values outside every number in the corpus, so no reading could be ambiguous -- and the rendered pane read **`111 Experience`** and **`222 Gold`**, identically in the quest log's detail pane and in a dialog window. `vault/captures/harness/20260816T103824`. Two things fell out of the same run: `0101 <word>` **is** a `0x100`-biased numeric argument, since 111 and 222 came back exactly (the rival readings would have rendered 367 and 478, or nothing); and the suffix is position-independent from our side too, which the corpus could only show for ArenaNet's. The magnitudes had been right all along -- but they were a plausibility argument, and this is the measurement.

**And the run found a defect no static reading would have.** With the reward block appended directly, the pane rendered `...then return to me.Reward:` -- our last sentence welded to ArenaNet's header. The reward run opens with a bare `0x0002`, which JOINS runs rather than breaking a line; `0x0102` (archive id 2, `
[b]`) is what breaks one. `questdefs.with_reward` now inserts `0002 0102` and `test_quests.py` §12 holds it, along with the ordering rule the same bug implies: the field-length check must run AFTER the block is appended, because 120 units of text passes on its own and overflows once 21 more are on. The templates are encrypted and the RC4 key is NOT FOUND (§3.3), so neither the wire nor the archive can settle which slot is which. The magnitudes fit; that is a plausibility argument, not a measurement.

**Two quests carry extra reward runs our schema has no column for. OBSERVED.** Quests 82 and 86 append two `ref 10738` blocks each (35 units total), whose arguments are **plain** ids (25126/25030 and 26146/26250). Quest 62 appends a `ref 10735` block (38 units) whose second argument is plain template 2438 fed `Armor` (id 2372) and the number 4 — an item reward.

**OBSERVED. Offer prose and turn-in prose are different authored strings, and the turn-in id is the offer id + 2**, 6 of 6 across four quests and both sessions: q80 `0x1706`→`0x1708`, q218 `0x14EA`→`0x14EC`, q82 `0x1718`→`0x171A`, q222 `0x1506`→`0x1508`, q86 `0x1746`→`0x1748`. A single description column in `content/quests.toml` cannot express the turn-in screen.

**OBSERVED. The paragraph framing differs by screen and is not cosmetic.** The offer dialog line separates with `0002 0107` (id 7) and appends a trailing `0002 0107`; the quest-log entry and the turn-in dialog line separate with `0002 0102 0002 0102` (id 2) and append nothing. Build the two heads separately.

**OBSERVED. The turn-in screen is never reached by a code-3 step.** It arrives directly on `INTERACT` with exactly one option, kind 23 / code `0x07`, whose label is a **single shared id in 6 of 6 across five quests** (`2ADF E839 B6FB 19A9`, id 10719). `content/quests.toml`'s per-quest `turn_in_label` is modelling something that does not vary.

**OBSERVED. There is headroom.** `0x0080` caps at 122 code units; ArenaNet's own maximum is 62. The reward run costs 19 (35–38 with an item line), so a description plus a reward fits — but the length check must run **after** the reward run is appended.

**NOT FOUND, and no lane said it: no reward is ever paid anywhere in this corpus.** The completion family `0x004E`, `0x006C`, `0x0096`, `0x0097`, `0x00FB` is **0 of 22,524** s2c and **0 of 971** c2s (§4.2). Everything above is about the *promise* rendered inside a description string. The grant protocol is entirely unobserved and is a separate arc.

---

#### 8.5 The single-quest collapse — the server does it, not the client

**OBSERVED. The quirk is on the wire.** Nine of 18 `INTERACT`-caused screens skipped the menu: on a bare `c2s 0x0039` with no `0x003B` before it, the server sent the description screen directly. Two clean fresh-NPC cases: `:62994` `t=172.712` agent 175 (prior `INTERACT` at `t=167.737`, prior `0x003B` **79.966 s** earlier) → `0x0080` 62 units leading id 5484, `0x0081`, kind 16 `0x803E01`, kind 17 `0x803E02`; and `:61624` `t=220.044` agent 76, same leading id, same two tags.

**The client cannot be manufacturing it.** The description text arrives *inside* `0x0080` and leads with a different string id from the menu template, and residual is 0 on 24 of 24 connection rows, so nothing was dropped.

**And the collapsed screen is byte-identical to the screen the click would have produced. OBSERVED — this is the strongest single measurement in §8.** Quest 82's description screen appears twice at agent 36 on `:62994`: at `t=70.441` as the reply to a code-`0x07` select, and at `t=72.727` as the reply to a bare `INTERACT` at `t=71.757`. Both emit the identical 59-unit `0x0080` leading `1718 A245 9F9C 4859` and the identical pair kind 16 `0x805201` / kind 17 `0x805202`. **The collapse is literally "send the screen the code-3 click would have produced" — one branch over one already-built responder, not a second code path.**

**The refutable form, and it passed: across all 40 screens, ZERO carry exactly one kind-18 line.** Kind-18-per-screen is `{0: 36, 1: 2, 2: 2}`, and both of the "1"s (`t=28.479`, `t=27.983`) pair the kind-18 with a kind-22 in-progress line. A server that always built a list would produce lone kind-18 screens; there are none.

**The trigger, corrected — and one lane's refinement is refuted by that lane's own data.** It is **not** "one actionable line". At `t=218.512` agent 7 presented exactly one line, kind 21 / code `0x04`, the operator clicked it and it did advance the quest — and the server still sent the 10-unit **menu** framing.

> **The collapse fires when the NPC has exactly one OFFER or one TURN-IN to present — 7 of 7 (agents 40, 36, 36, 175 / 40, 36, 76). A lone in-progress line (kind 22, `t=91.052`) or a lone advance line (kind 21, `t=218.512` and `t=266.312`) still gets the menu — 3 of 3.** The discriminator is the option's kind/code family, not whether the line can be clicked.

**GWW's rule, measured.** All four description screens reached via a code-`0x03` click were at the session's **first giver** (agent 99 on `:60935`, agent 53 on `:61193`) — the only NPCs that ever showed a **two**-line list. Every description screen reached with no code-`0x03` click was at an NPC that never showed a list of more than one line. Every list screen in the corpus carries 1 or 2 lines.

**OBSERVED. The menu screen's text is one CONSTANT template plus one VARYING argument.** All 9 menus are `2AE6 F9CB E939 5DD2 010A <4 units> 0001` — id 10726, the plain markup token id 10 (`[topic-f]`, the parameter introducer), one reference, id 1 (`[null]`, the terminator). The 5-unit prefix and the 1-unit suffix are byte-identical across two sessions, five agents, six connections and two characters. Only the middle reference varies: six distinct values over nine screens — ids 12917 (×2), 12919, 12923, 13046 (×2), 5661 (×2), 5707.

**This closes §0's dangling "what it is remains open".** The Q5 block records that the two captured offer lines share the prefix `2AE6 F9CB E939 5DD2 010A` and differ only in one varint group (`3377 …` against `3375 …`), and that replaying them produced no clickable option. Those groups are **12919 and 12917 — the NPC's greeting paragraph, which changes with quest state.** Agent 99 shows 12919 at `t=26.816` before the accept and 12917 at `t=28.479` after; agent 53 shows 12923 then 12917. The option was never in the string; it is `0x007E`, exactly as §0 concluded, and the varying group is the greeting itself.

**CONTESTED, cause UNVERIFIED: the same NPC in the same state gave different greeting paragraphs in the two sessions** — 12919 (138 record symbols) against 12923 (258), with the same two kind-18 options in both, converging on 12917 after the accept. A 120-symbol difference cannot be a character-name substitution. What selects it — profession, gender, or a random pick — is unknown, n=1 pair. (And "the same NPC" is itself inferred: agent 99 on `:60935` and agent 53 on `:61193` are different ids on different connections, related only by role and by both offering quests 80 and 1462.)

**OBSERVED. `0x0081` flushes 40 windows: lines-per-flush `{1: 28, 0: 12}`, options-per-flush `{2: 15, 1: 11, 0: 14}`.** No window carries three options, no `0x007E` ever arrives before its flush (41 of 41 after), and no `0x0080` is ever left unflushed (0 of 28). **Two options is a floor, not a ceiling** — the `0x007E` receive path carries no array, no counter and no bound. `0x00811720` is `push 0 / push [ebp+8] / push 0x100000a3 / call 0x633d70 / add esp,0xc / ret`, and the `GmNpc` subscriber at `0x00509582` creates a fresh child frame per option and records only the *first* at `[esi+0x20]`. **That the client has no maximum anywhere is NOT FOUND, not observed** — `asserts.py`'s module lists are a floor by the tool's own banner (6 readable `GmNpc` sites, 3 unreadable, ~370 unmatched call sites corpus-wide).

**RECONSTRUCTION from `0x00811740`, with no wire witness: a second `0x0080` concatenates into the same buffer rather than starting a new line.** The body computes its write offset as `mov edi,[esi+0x1c] / lea ecx,[edi-1] / neg edi / sbb edi,edi / and edi,ecx`, i.e. it appends starting at index count−1, overwriting the previous terminator, guarded by `Array:587 index < m_count`. **ArenaNet never sends two `0x0080` per window (0 of 40)**, so our accumulate-then-flush model has never been exercised against their usage — and our server's one-`0x0080`-per-quest-row loop renders, under this reading, as one run-on paragraph.

**The window close, and the three lanes disagreed about it.** **OBSERVED:** twelve **bare** flushes (a `0x0081` with no `0x0080` since the previous flush), 12 of 12 following a `c2s 0x003B` — 10 accepts and 2 terminal turn-ins — and **0 of 12 followed by any option**. Each names the giver agent, never 0. **RECONSTRUCTION:** that a bare flush *means close*. `0x008117B0` builds `{1, agent_id, textptr}` where `textptr` is null when the count is zero, posts frame `0x100000A6`, then zeroes the count — so "close the window" and "display a window with no lines" are the same bytes, and nothing has been fired at a client. **`GAME_SMSG 0x007F` occurs 0 times in 22,137 s2c messages**, so there is no explicit close *opcode*; the bare-flush association is what stands in for one.

**Corrected count:** there are **14** zero-option flushes, and 14 of 14 carry the speaker's recomputed marker. Twelve of them are bare; the other two (`t=221.623` agent 7, `t=266.891` agent 8, the code-`0x04` follow-ups) carry a 4-code-unit line (`166D D0B8 9207 0683`) and no option. The "10 of 10" one lane reported is short by four, and conflates the two categories.

---

#### 8.6 The marker, per NPC, over the whole lifecycle

**OBSERVED. `0x009F` property 11 takes THREE values, not two.** Census `{3: 2, 4: 6, 5: 40}` n=48 in `143055` and `{3: 2, 4: 6, 5: 33}` n=41 in `235916`. Value 0 never occurs, 0 of 89. **§0's Candidate 2 block and `probes.py:2701-2718` both say "exactly two values"** — that is true of the scope they measured (`:60935` + `:62994` gives `{5: 37, 4: 6}`) and false of the corpus. All four value-3 sends are on the outpost connections: agent 7 at `t=214.656` / `t=218.512` (`:64102`) and agent 8 at `t=262.549` / `t=266.312` (`:49160`) — the same agents that carry kind 21.

**RECONSTRUCTION, and it is the message the arc was missing: `0x009F` property 12 = 0 is the marker CLEAR.** Without it the model is incoherent — NPCs appear to hold a stale `!` for 18 s. With it, 18 of 18 quest-concluding clicks across both sessions are explained with zero counterexamples. It is 0 in **22 of 22** sends in `143055` and **16 of 16** in `235916`, so the property's own value range is never exercised and the reading rests entirely on consequence.

**REFUTED: the rival reading "property 12 = 0 means the dialog closed."** Two independent refutations. (1) `235916` `t=99.549` emits four prop-12 sends with no `0x0081` anywhere near and no `INTERACT` within seconds. (2) `t=28.179` and `t=27.659` are zero-option flushes — the dialog-closing form — and carry prop 11 = 5 with **no** prop 12, because the giver still had quest 1462 to offer.

**OBSERVED. Value 4 is not "a quest this NPC gave is in progress". It is "a quest you hold can be turned in HERE, NOW", and the in-progress window is marker-free.** Agent 36 on `:62994` gives quest 82 at `t=73.376`, is cleared by prop 12 at `t=73.431`, and carries **no marker for 17.7 s** — until `t=91.136`, the same batch as `0x004D[82]` + `0x004C[82]`, the moment the objective completed. Quest 86 repeats it with a twist: the objective completes at `t=99.549` while agent 36 is out of view (removed `t=86.929`), so the 4 arrives on the re-create at `t=108.805`.

**OBSERVED. The marker follows the NEXT NPC, not the giver.** Quest 80's giver (agent 99 / 53) holds 5 through the entire accept and never takes 4; the turn-in NPC (agent 40) flips 5→4 in the *same millisecond batch* as `QUEST_ADD 80` (`t=28.179` / `t=27.659`) and 4→5 in the same batch as `QUEST_REMOVE 80` (`t=46.797` / `t=45.208`). This is the give-here/turn-in-there case, and it is the one our server has no model for at all.

**OBSERVED. Value 3 is the mid-quest advance marker** — the NPC where an active quest's next dialogue step happens, whose click advances objectives without removing the quest. n=2, one per session, both the identical scenario, and both on the agent that offers kind 21 / code `0x04`.

**OBSERVED. On turn-in the marker is RECOMPUTED, not reset to 5.** It becomes 5 when the NPC gains a follow-up quest and is cleared when it does not — 6 of 6 turn-ins, zero counterexamples: `t=46.765` → `p11[40]=5` (agent 40 then offers 218); `t=70.407` → `p11[36]=5` (offers 82); `t=92.746` → `p12[36]=0` (nothing left).

**OBSERVED, and it is a broadcast, not a targeted clear.** On a quest-log mutation the server re-emits marker state for every NPC on the connection whose state it recomputes. `t=47.655` carries prop 12 = 0 for agents **99, 42 and 40** — five sends to three agents — including a redundant re-clear of agent 99, which had already been cleared 18.5 s earlier at `t=29.197`. `t=45.936` repeats it. Turning a quest in can also *raise* markers on NPCs the player never touched: `t=92.792` carries `p11[48]=5`, `p11[32]=5`×2, `p11[41]=5`×2 alongside `QUEST_REMOVE 82`.

**OBSERVED. The option-bearing dialog window carries the speaker's marker, 12 of 14 and 11 of 12.** The exceptions are the kind-15 screen (both sessions) and the lone kind-22 in-progress screen at `t=91.052` — both of which carry prop 12 = 0 instead, with the prop-11 = 4 arriving 84 ms later inside the objectives batch.

**OBSERVED. Every prop-11 send follows a `WORLD_CREATE_AGENT` for that agent; none precedes one.** Message-index gap: min 2, median 4, max 1306 / 1419. The server is not strict in the other direction — 2 orphans in session 1 (`[11, 41, 5]` at `t=92.792`, whose agent was removed at `t=74.199`), 0 in session 2.

**OBSERVED, meaning RECONSTRUCTION: a re-create can omit the prop-11 send.** Agent 42 on `:60935` is created at `t=20.137` with `0x009F [11, 42, 5]` and re-created at `t=40.200` with a byte-identical create payload (same model dword 536872392, same position, same rotation) and **no** `0x009F`; `:61193` reproduces it. **Whether the client then draws nothing, or keeps the marker it had, is NOT FOUND** — the server subsequently sends prop 12 = 0 to that same agent at `t=47.655`, which fits either reading.

**Scope warning that three lanes tripped over: agent ids are per connection.** Agent 40 on `:62994` never receives prop 11; agent 40 on `:60935` receives it eight times and is one of the two most-marked NPCs in the corpus. Any table of agents needs the connection in the key.

**The owner's rule 5 = "has a quest available" survives, with the denominator stated.** Zero counterexamples among the **10 NPCs (5 per session) the operator actually opened a dialog with**. The remaining 23 marked agents carry 5 and were never spoken to, so nothing in this corpus can confirm or refute their marker. "Zero counterexamples over 89 sends" reads as n=89; the testable n is 10.

**The exact rule our server should implement**, evaluated fresh per (NPC, player quest state) at every agent create and again on every quest-log mutation:

```
5  the NPC has >= 1 quest available to OFFER
4  a quest the player holds can be TURNED IN at this NPC right now
3  a quest the player holds has its next dialogue STEP at this NPC
–  otherwise: send nothing on create; send 0x009F [12, agent, 0] on a live agent
```

There is **no** property-11 value that clears a marker. Sending `[11, agent, 0]` invents a value that occurs 0 times in 89 sends.

---

#### 8.7 What our server must change, in order

1. **Bind the option kind to the code.** `authsrv.py`'s `INTERACT` arm emits (kind 18, code `0x01`) and (kind 18, code `0x07`); neither pair exists on ArenaNet's wire, 0 of 41. Add a code→kind map in `questdefs.py` (`0x01`→16, `0x02`→17, `0x03`→18, `0x04`→21, `0x05`→22, `0x07`→23) and build every `0x007E` through it, so a mismatched pair cannot be constructed.
2. **Build screen 1 (the menu).** One `0x0080` carrying the short greeting, one `0x0081`, then one `0x007E` per line: kind 18 / code `0x03` per available quest (label = the quest's **name** id, 11 of 11), kind 22 / code `0x05` per held in-progress quest, kind 21 / code `0x04` for an advance step.
3. **Build screen 2 (the description) and answer code `0x03` with it.** The arm currently sends **nothing**, on the recorded ground that ArenaNet sends no quest-family reply to an offer. That is right about the *quest* family and wrong about the *dialog* family, and it is the single load-bearing defect: today a player who clicks a quest name in our window gets no screen at all. Send `0x0080` (description + reward run), `0x0081`, `0x007E` kind 16 code `0x01`, `0x007E` kind 17 code `0x02` — 4 of 4, in that order.
4. **Send the decline line, always**, and add a `0x003B` arm for code `0x02` that changes no state and **logs that its consequence is unmeasured** rather than replicating a guess. Add `SERVICE_DECLINE = 0x02` to `questdefs.py` with that note, and correct line 138.
5. **Adopt the collapse.** When the NPC has exactly one OFFER or one TURN-IN, skip the menu and send the description screen on the `INTERACT` itself — 7 of 7. A lone in-progress or advance line still gets the menu — 3 of 3. Both mandatory Pre-Searing quests are single-quest cases, so our always-a-list behaviour is the wrong screen in the case that matters most.
6. **Build the turn-in screen**, which the server does not have: one `0x0080` carrying the **turn-in** prose (a different string from the offer), one `0x0081`, one `0x007E` kind 23 / code `0x07` whose label is the shared generic id, not a per-quest column.
7. **Send exactly one `0x0080` per window.** The current loop sends one per quest row; under `0x00811740`'s concatenation they render as one run-on paragraph, and ArenaNet sends one in 28 of 28.
8. **Close the window.** Append a bare `0x0081` naming the giver agent after every accept (10 of 10) and after a turn-in that does not chain into a new offer (2 of 6; the other 4 open the giver's next offer screen). Our server sends `QUEST_ADD` and stops, leaving the window open with a consumed option in it.
9. **Add the marker clear and recompute the marker.** Send `0x009F [12, agent, 0]` where a marker should disappear; ride every marker update in the same batch as the quest message that caused it; set 4 when the quest becomes turn-in-able (which for a real objective is `0x004D`+`0x004C`, not the accept); re-send on every dialog open and every agent re-create, and deliberately omit it when the NPC has none. Do **not** copy ArenaNet's doubled sends — they are one recompute per log mutation, and commit `a70387b` already established the doubled `0x0052` is not required.
10. **Add a reward-run builder** to `questdefs.py`: append `0002 2AE8 E7D4 E5CC 3672 0002 2AEA 8C3F B519 6611 0101 <0x100+A> 0002 2AEC DAC7 81AE 3482 0101 <0x100+B>` to both the `0x0080` line and the `0x004C` description slot (byte-identical there in 17 of 17), with A and B our own numbers bounded to `0..0xFEFF`. Three ArenaNet ids cited, zero ArenaNet text held. Run the 122-unit length check **after** the append.
11. **Split `content/quests.toml`'s prose columns** into offer and turn-in, and build the two paragraph heads separately (`0002 0107` + trailing for the offer line; `0002 0102 0002 0102` and no trailing for the log entry and the turn-in line). Drop `turn_in_label` as a per-quest column.
12. **Decide what to do about kind 15.** `decode_service_select` rejects its tag (`0x800000` clear → `None`) and `encode_service_select` cannot build it. Either never emit it, or give `0x003B` a non-quest arm first.
13. **Fix the two numbers this section corrects** — `field4` 41 of 41 (`questdefs.py:170` and §0), and property 11's three values (§0 and `probes.py:2701-2718`, which is the comment a future session will read *before* writing the marker code).
14. **Run two probes before any of this ships.** (a) Send `0x009F [11, agent, 5]`, screenshot, then `[12, agent, 0]`, screenshot — that moves the clear from RECONSTRUCTION to OBSERVED and shows in the same run whether 3 and 4 draw different glyphs. `_quest_giver_mark_steps` in `probes.py:2724` is two `Step`s from being it. (b) Send `0x004C` citing 10728/10730/10732 with distinguishable numbers (111, 222) and read which line shows which — the only way to learn which reward slot is experience and which is gold.

---

#### 8.8 Still NOT FOUND

- **The consequence of code `0x02` (decline).** Offered 11 times, clicked 0 of 22. The value is observed; the refusal behaviour is not.
- **The consequence of code `0x05` (in-progress line).** Offered 3 times, clicked 0 of 22.
- **The consequence of code `0x80` / kind 15**, and what kind 15 *is*. Offered twice, clicked 0 of 22, label id 10725 encrypted, tag rejected by our own decoder.
- **Any explicit dialog-CLOSE opcode.** `0x007F` is 0 of 22,137. The bare-flush association is 12 of 12, but "means close" is RECONSTRUCTION and has never been fired at a client.
- **Whether property 12 = 0 actually clears anything.** It is 0 in 38 of 38 sends across both sessions, so the property's value range is never exercised; the entire reading rests on consequence. Cheapest open item in the arc.
- **The other arm of property 12.** At `t=91.052-91.136` and `t=99.549` it is broadcast to agents that never carried property 11 *on that connection* (43, 44, 45, 46, 37, 38, 39, 40, 92 / 37, 38, 39, 40 — all kind 9, create payloads `0x2000059A`, `0x2000058C`, `0x200008E8`). What that does is unknown.
- **The rendered text of the reward templates** 10726, 10728, 10730, 10732, 10735, 10738, 10742 and the option labels 10719, 10725 — all `needs_key = True`, RC4 key NOT FOUND (§3.3). Seven splits of the trailing varint were tested against ids 10726, 5635 and 12919; best ASCII fraction 0.91, none clean.
- **Which reward number is experience and which is gold.** Unresolvable from wire or archive; probe only.
- **The whole payment side.** Zero reward grants in the corpus (§4.2's five opcodes, 0 of 22,524 s2c and 0 of 971 c2s).
- **Any kind or code outside the seven observed pairs**, and any `0x007E` tag with a non-zero high byte — no merchant, skill-unlock, item-unlock or hero-unlock service option reaches the wire, 0 of 41 offers and 0 of 22 clicks. This bounds day-one generality; it does not prove the families absent.
- **Kinds 19 and 20**, absent from the corpus; and **kind 12**, which the client special-cases and which never appears.
- **Any maximum option count.** Two per window is a floor. The client path has no array, counter or bound, and `asserts.py`'s "no assert names a count" is a floor by the tool's own banner, not a census.
- **Whether a multi-`0x0080` window renders as multiple paragraphs.** 0 of 40 flushes carry two lines, so our accumulator model has no wire witness at all.
- **What selects between greeting paragraphs 12919 and 12923** for the same NPC in the same state across the two sessions. n=1 pair.
- **Why agent 42 carries a marker at map load in both sessions**, and why accepting quest 218/222 from agent 40 clears it in the same batch. Never spoken to; create payload byte-identical across sessions. The obvious reading — a second giver for the same quest — is untested.
- **Why the quest-log `0x004C[0]` carries the `%str1%` character-name substitution for quests 80, 218 and 222 but not for 62, 82, 86 and 1462**, while the dialog line always carries it. The split is measured; the cause is not.
- **Quest 1462's five-unit varint ids** (published as 80660 / 80672 / 80673), which did not reproduce under `REF_BIAS = 256`. Name the decoder before those numbers reach a document or a content row.
- **Everything static here is build 38797** (`0x00811720`, `0x00811740`, `0x008117B0`, `0x00509582`, `0x0091E710`) and none of it has been re-checked against 38833.

---

#### Reproducing §8

```bash
cd <tree> && git rev-parse --show-toplevel
cd <tree> && python toolkit/vaultpath.py
cd <tree> && python toolkit/authsrv/cmsgstream.py 20260807T143055 game   # and 20260810T235916, 20260807T133758
cd <tree> && python toolkit/clientscan/msgshape.py 0x007E                # and 0x0080, 0x0081
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x0091e710 --count 60
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x811720 --count 40
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x811740 --count 50
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x8117b0 --count 45
cd <tree> && python toolkit/clientscan/codescan.py --dis 0x00509582 --count 45
cd <tree> && python toolkit/clientscan/asserts.py --file GmNpc
cd <tree> && python toolkit/clientscan/textrec.py --dat <vault>/dat_study/Gw.dat 1 2 7 10 11 2372 2438 10719 10725 10726 10728 10730 10732 10735 10738
```

**Every wire measurement in §8 came from scratch scripts over `cmsgstream.timed`, not from a committed tool**, and that is debt in the same shape §7.9 already names: the `0x007E` option/click ledger, the screen builder that groups `0x0080*` → `0x0081` → `0x007E*`, and the `0x009F` property census. Set `PYTHONIOENCODING=utf-8:replace` or printing coded strings fails on cp1252. **Sort merged c2s/s2c rows by TIMESTAMP ONLY** — sorting the whole tuple reorders same-timestamp frames by opcode, puts `0x007E` (126) ahead of `0x0080` (128), and manufactures a refutation of the ordering rule the server depends on. Until these land as a `test_quests.py`, treat their numbers as reproducible-by-rewriting rather than reproducible-by-running.

---

### 9. Rung Q1 — the names land in the schema, and the frame bus is what carries them

**2026-08-16.** Twelve quest opcodes were named in `schema/overrides.json`, one was
renamed, and four rows record a deliberate abstention. Before this the arc's naming
existed **only in this document**: fifteen of the nineteen quest opcodes were absent
from the overrides file entirely, so `QUEST_ADD`, `QUEST_DESCRIPTION` and the dialog
pair — the arc's biggest single result — were invisible to every tool in the tree that
reads the schema rather than the study.

#### 9.1 The evidence that carries eleven of the twelve, and how it was made refutable

The strongest argument available without a client run is the **frame bus**: a handler in
`ChCliApi` writes the store and posts a numbered frame; UI modules subscribe to ids and
repaint. §1.6 tabulated publisher VAs. §2.1 tabulated handler-body VAs. **Nobody joined
them per opcode**, which is how §7.6 came to say "nothing static will substitute" about
a question those two tables answer between them.

The join was **predicted before it was measured** (`probes.py`'s rule), and the
prediction was structural rather than a list of ten values: *the two adds share an id,
the two text-fills share an id, and the three marker ops — which share one payload
layout — do not.* That is the part a coincidence does not produce. Then the bytes:

| opcode | body | posts | who subscribes |
|---|---|---|---|
| `0x0049` QUEST_ADD | `0x0080F0A0` | `0x1000014E` | QuestLog, QuestTaskTracker, GmView, GmHelpGuide, **Compass**, UiCtlInstance |
| `0x0050` QUEST_ADD_NO_MARKER | `0x0080F470` | **`0x1000014E`** | *(the same — both are adds)* |
| `0x004C` QUEST_DESCRIPTION | `0x0080F290` | `0x1000014F` | QuestChallenge, QuestTaskTracker |
| `0x0054` QUEST_OBJECTIVES_UPDATE | `0x0080F990` | **`0x1000014F`** | *(the same — both fill log text)* |
| `0x004D` QUEST_SET_MARKER | `0x0080F3C0` | `0x10000154` | QuestChallenge, QuestTaskTracker, **Compass** |
| `0x0051` QUEST_MOVE_MARKER | `0x0080F6F0` | `0x10000151` | QuestTaskTracker, **Compass** |
| `0x0053` QUEST_SET_ACTIVE_MARKER | `0x0080F8E0` | `0x10000153` | QuestLog, QuestTaskTracker, GmMapCtlLocationTag, **Compass** |
| `0x0052` QUEST_REMOVE | `0x0080F7A0` | `0x10000152` | QuestLog, QuestTaskTracker, GmHelpGuide, GmMapCtlLocationTag, **Compass** |
| `0x004E` QUEST_COMPLETE_PANEL | `0x0080F670` | `0x10000155` | **GmQuestComplete**, GmView, QuestTaskTracker |
| `0x004A`, `0x004B` | `0x0080F250`, `0x0080F270` | *(nothing)* | — measured negatives |

**11 of 11 bodies agreed, shared ids and all.** The three marker ops carry one identical
5-field layout `[u32 id, vec2, u16, u16]`, so **the payload cannot tell them apart and
the frame id can** — that is the whole naming argument for `0x004D`, `0x0051` and
`0x0053`, and it is why two of them are filed `medium`: the English on top of a measured
distinction is still RECONSTRUCTION.

#### 9.2 The scan window, twice — and both times it failed by returning a short list

The `push imm32` and the `call` that consumes it are **not adjacent**; the body stages
the frame payload in between. §1.6's own scan used a 6-byte window and lost two sites
(it says so, and lane B recovered them by hand). This pass used 24 and lost `0x0050`'s,
whose call sits at **+29** behind three `mov [ebp-x], imm32` — one of them `0x378` ==
**888**, the no-marker map id, which is §2.3's constant turning up as a payload store.

That first read as a **refuted prediction**. It was a refuted *instrument*. Worth
separating, because the two look identical from inside a run: **a window too small does
not error — it returns a confident short list**, the same failure shape as a stale
worktree returning a confident number from an old scanner. `CALL_WINDOW = 48` now, and
`test_framebus.py` §1 plants a call at exactly +29 and at **both edges** of the window,
so shrinking it goes red instead of quietly un-measuring an opcode. Verified by
sabotage: reverting to 24 fails four checks.

#### 9.3 `0x004E` — the rename, and §7.6's premise expiring

`schema/overrides.json` already named `0x004E` **`VICTORY_BANNER`**, `medium`, from the
2026-08-13 sweep: one opcode fired at a fresh client and an operator writing down a
centre-screen victory-flag animation. That arc filed it `medium` for exactly the right
reason — *a name taken from a picture of an effect is a guess about purpose.*

The static join supplies the purpose. `0x0080F670` does `push 0x10000155` /
`call 0x00633D70` (post, **not** the `0x00633BD0` subscribe helper) with no `int3`
padding between body start and push site, so the site is inside this handler rather than
a helper wedged between two bodies — the containment was worth checking, because
everything else here was arithmetic across two tables. `GmQuestComplete` is a 3D scene
with a model and a light (§1.5), which is what a centre-screen banner animation looks
like from the outside. **Renamed `QUEST_COMPLETE_PANEL`, `high`, CORROBORATED** — two
lineages sharing no ancestry, one static and one on-screen. The prior name is kept in
the row, because it is an observation and not a mistake.

**This is the arc's real result, and it is a negative about our process rather than about
the client:** seven recon lanes and this document's own author held both halves and did
not multiply them. The claim that turned out to be wrong — *"Nothing static will
substitute"* — was the confidently stated one.

**MEASURED while checking that, and it is the map the reward arc needs.** All five ids
`GmQuestComplete` subscribes to have a distinct publisher and **every one is a real
`call 0x00633D70` post**, not a subscribe:

| frame id | published at | inside |
|---|---|---|
| `0x10000155` | `0x0080F6C7` | **`0x004E`'s handler body** |
| `0x10000156` | `0x00810B47` | *not a quest-family handler* |
| `0x10000157` | `0x008124C8` | *not a quest-family handler* |
| `0x10000158` | `0x00812473` | *not a quest-family handler* |
| `0x10000159` | `0x0081529E` | *not a quest-family handler* |

So the completion panel is fed by five frames and **only one of them comes from the quest
opcode block** (`0x0080F0A0`–`0x0080FA12`); the other four are published from elsewhere in
`ChCliApi`. That is worth knowing before anyone tries to open the panel from the server:
sending `0x004E` supplies one fifth of what the scene subscribes to. **Which opcodes drive
the other four is the next static question**, and `framebus.py --at` answers it one body at
a time — `0x006C`, this arc's named "instruction-identical twin", is the first candidate to
place. Lane B's by-hand recovery of `0x10000159`'s site at `0x0081529E` is confirmed here.
**ANSWERED 2026-08-19, §9.7:** all four are the other completion-family opcodes' own
bodies — `0x006C`→`0x10000156`, `0x0097`→`0x10000157`, `0x0096`→`0x10000158`,
`0x00FB`→`0x10000159`. The table above stays as written because *"not a quest-family
handler"* was true; what it could not see is that the family feeding the panel is the
completion family itself.

#### 9.4 What was NOT named, on purpose

Four rows carry a `why` and **no** `name`, on `studies/smsgsweep/FINDINGS.md` §7.6's
precedent that a withheld name belongs in the artifact rather than only in a study:

- **`0x004B`** — 32-byte body, `[array32[64]]`, bulk-assigns the `+0x518` list, **posts
  no frame id**, 2 arrivals, no observed consequence. A name would describe the argument
  rather than the effect.
- **CMSG `0x0011`** — `[u32 id]`, **0 of 971**. §7.7's "abandon?" stays open; one abandon
  on a live capture settles it and a shape does not.
- **CMSG `0x0013`** — `[msg_header]` alone, no payload, **0 of 971**. "QUEST_CLEAR_ACTIVE"
  is a plausible reading of a blank message and nothing more.

**CMSG `0x0014` `QUEST_SET_ACTIVE` was named `medium` and is the weakest row in the
family** — shape and position, n=1, no consequence chain. Naming it made
`test_dispatch.py` §7 go red on the same commit, which **is the rung working**: a name
costs somebody a binary read, so named implies handled *or* listed. It is now listed,
with the reason that this server serves one quest and has no second value for "which
quest is tracked".

#### 9.5 The debt this closes, and the debt it does not

§7.9 asked for the coded-string codec to stop living in a scratch file. The same
complaint applies to a *measurement*: the join above was a scratch script for about an
hour. It is now `toolkit/clientscan/framebus.py` with `test_framebus.py` behind it (18
checks, floor 14 — §1 runs on a bare machine against a synthetic PE, §2 declares a
`LEDGER.skip` without the vault). So the `why` text in every one of those overrides rows
is reproducible **by running** rather than by rewriting.

**Still open from §7.9:** the coded-string codec itself, the 66/66 byte-identical
verification that is a claim in prose and not a check, and the fact that **every binary
claim in this document is build 38797** and none has been re-checked against 38833.

#### 9.6 The three dwords: MEASURED, one agent-piloted loopback run (2026-08-19)

§7.6's remaining half — *what the panel expects in those three dwords* — is answered,
and it took exactly the one loopback run §9.3 predicted. Harness `20260819T071548`,
caged loopback, build 38797 client, `--probe quest_panel`: five arms with the
prediction filed in the probe before launch, cadence frames at 1 s scored by
`shotlabel.diff_score` joined to the capture's own wall clocks, then read by eye at
every arm (the masked scorer's banner blind spot from `studies/newopcodes` cannot bite
here — the committed scorer is full-frame — but the panel draws exactly where a mask
would sit, so the eye pass was mandatory either way).

| Arm | Payload | On screen — OBSERVED |
|---|---|---|
| 1 | `(0, 0, 0)` | The 20260813T123003 render reproduces: a 3D victory monument (red-gold panel, eye motif) materializes centre-world in a pyrotechnic burst ~1.5 s after the send, animating ~8–10 s. **No toast.** |
| 2 | `(0, 0, 0)` again | The identical render, again. **The panel re-fires per send** — not one-shot, so value ladders fit in one session. |
| 3 | `(1463, 0, 0)` | The banner, plus a centre-bottom toast: **"You have earned 1,463 experience!"** |
| 4 | `(111, 222, 333)` | **"You have earned 111 experience, 222 gold, and 333 skill points!"** |
| 5 | `(0xFFFFFFFF, ×3)` | **"You have earned 4,294,967,295 experience, 4,294,967,295 gold, and 4,294,967,295 skill points!"** No assert, no clamp, client alive to teardown. |

**The reading, from the client's own sentence: dword 1 is EXPERIENCE, dword 2 is GOLD,
dword 3 is SKILL POINTS.** Zero-valued fields are omitted from the sentence — arm 3
names only experience, arms 1–2 draw no toast at all — which *explains* the 2026-08-13
sweep's silent banner rather than contradicting it: the sweep's all-zero payload
suppressed the whole sentence. Values render unsigned and comma-formatted. Arm 3's
stated hypothesis (field 1 = quest id) is **REFUTED**, and the sentinel property is
what made the refutation legible: 1463 sits outside every corpus range, so its
appearance as "1,463 experience" is not ambiguous with any real quest binding.

**What this does and does not settle.** It settles the DISPLAY — what the panel does
with its payload. It does **not** settle a grant: the Level chip read 1 in the same
frame as the 4.29-billion-experience toast, no client-side state visibly changed, and
the rest of the completion family (`0x006C`, `0x0096`, `0x0097`, `0x00FB`) stays 0 of
22,524 in the corpus. Whether retail pairs this display with a separate state-changing
grant protocol is still the live-capture question, and Q7's acceptance criterion still
must not claim a reward. Also unmoved: which opcodes publish the other four frame ids
GmQuestComplete subscribes to (§9.3). One softening of §9.3's caution: this run fed the
scene exactly ONE of its five subscribed ids and the banner-and-toast path rendered
complete-looking anyway, so an underfed render is a risk for the scene's *other*
content (medals, completion notes, reward models), not for this path.

#### 9.7 The other four publishers: the completion family closes on itself (2026-08-19)

§9.3 ended on *"Which opcodes drive the other four is the next static question"*, and
the answer has a shape nobody predicted in writing but should have: **the five frame
ids GmQuestComplete subscribes to are published by exactly the five completion-family
opcodes** — the same five that are 0 of 22,524 in the corpus. The scene and the
protocol family close on each other, and `0x006C` was indeed the first candidate to
place (§9.3 called it; the twin reading holds).

| frame id | publisher VA | receive-table chain — MEASURED | shape |
|---|---|---|---|
| `0x10000155` | `0x0080F6C7` | `0x004E` (§9.3, the rename) | `[u32,u32,u32]` |
| `0x10000156` | `0x00810B47` | **`0x006C`**: stub `0x0091E180` → body `0x00810AF0`..`0x00810B61` | `[u32,u32,u32]` — `0x004E`'s twin |
| `0x10000157` | `0x008124C8` | **`0x0097`**: stub `0x0091EBD0` → body `0x00812490`..`0x00812505` | `[u8, string16(128)]` |
| `0x10000158` | `0x00812473` | **`0x0096`**: stub `0x0091EBA0` → body `0x008123E0`..`0x0081248D` | `[u32 ×5]` |
| `0x10000159` | `0x0081529E` | **`0x00FB`**: stub `0x0091F9D0` → body `0x00815260`..`0x008152D4` | `[u16,u32,u32]` |

**Mind the swap.** `0x0096` posts `0x10000158` and `0x0097` posts `0x10000157` —
frame-id order does not follow opcode order, which is exactly the detail an
assume-adjacent reading would get wrong, and `test_framebus.py` §1 now asserts it
structurally so a tidy-minded edit goes red.

**Two instruments agree.** Each body was located through the client's receive table
(`msghandler.py <op>`: dispatch stub, one call, the body) and disassembled linearly to
its `ret`; independently, `framebus.py --at <body> --end <ret>` finds exactly one POST
of the expected id in each range (`push imm32` / `call 0x00633D70`). The pairing is
committed as `COMPLETION_BODIES`/`COMPLETION_EXPECTED` in `framebus.py`, printed by the
no-arg run ("4 of 4 completion bodies match"), and checked by `test_framebus.py`
(§1 structurally, §2 against the pinned image — 27 checks, floor 16).

**What it reframes.** The reward arc's remaining gap is now *structured*: the grant is
not one mystery opcode but a five-message scene feed, of which `0x004E` (display:
experience/gold/skill points, §9.6) is measured, `0x0097` is the one that carries a
STRING (the completion-notes/rewards-blurb candidate — RECONSTRUCTION), `0x0096` is
gated on completion-flag bits (the 2026-08-12 sweep's assert), and `0x006C`/`0x00FB`
have screen observations (world burst; hard-mode banner). A loopback ladder over
`0x0096`'s two flag bits and `0x0097`'s u8 enum with the `quest_panel` rig is now the
cheap next probe; the full retail sequencing still needs the narrated live completion.
Schema: `0x0096`/`0x0097` get `why`-only rows (the §9.4 restraint — the join names
their wiring, not their effect); `0x006C`'s row records its name/wiring TENSION
(a chest-labelled burst feeding the quest-completion band) rather than resolving it.
Build scope: these VAs are 38797 measurements, not re-checked on 38833/38519.

#### Reproducing §9

```bash
cd <tree> && git rev-parse --show-toplevel
cd <tree> && python toolkit/clientscan/framebus.py
cd <tree> && python toolkit/clientscan/framebus.py --at 0x0080F670 --end 0x0080F6F0
cd <tree> && python toolkit/clientscan/framebus.py --at 0x00810AF0 --end 0x00810B61
cd <tree> && python toolkit/clientscan/msghandler.py 0x006C --follow --limit 40
cd <tree> && python toolkit/clientscan/test_framebus.py
cd <tree> && python toolkit/authsrv/test_dispatch.py
cd <tree> && python toolkit/harness/session.py --keep-open --shots 1 --hold 120 --game-args '--probe quest_panel'
```
