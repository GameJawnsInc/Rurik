# Twenty-two opcodes the Factions captures brought in

**2026-08-17.** Two owner-driven live captures of a **new Factions character** landed
today and carried twenty-two `GAME_SMSG` opcodes ArenaNet had never sent us before:

| capture | where | game channels |
|---|---|---|
| `vault/captures/live/20260817T183756` | Shing Jea Monastery | 4 |
| `vault/captures/live/20260817T180610` | starter zone | 3 |

The census, re-run first-party this pass over every `game-*.jsonl` in
`vault/captures/live/` (`toolkit/schema/codec.py`, `Codec.decode_stream("GAME_SMSG", …)`,
every one of the 20 channels consuming to the final byte with `err=None`):

- **before:** 155 distinct opcodes over **12** connections (`20260807T*`, `20260810T235916`)
- **after:** **177** over **20**
- **the difference is exactly 22**, and it is exactly the set below — a check that could
  have come out at 21 or 23 and did not.

**All 22 already had FIELD SHAPES in `schema/messages.json` and NO name.** Verified:
`schema/overrides.json`'s `GAME_SMSG` block names 64 opcodes and none of these. Their
neighbour `0x00B8 TRIAL_FEATURE_RESTRICTED` *[high]* is in there, which is what made the
gap conspicuous.

**Correct the brief before anything else: there is a THIRD capture.**
`vault/captures/live/20260817T183323` (1 game channel, 2,487 messages) is the same
character on the same evening, between the two named ones, and it is where the "20
connections" in the headline comes from (12 + 3 + 1 + 4). It contributes no new opcode,
but it changes sighting counts for six of the twenty-two and it **refutes one field
reading outright** (`0x0071`, below). Two of the eleven investigating agents read only
the two captures the brief named and reported counts short by 18. Sighting counts in this
document are over **all three** 2026-08-17 captures unless a row says otherwise.

**Build gap, stated once and applying to every row.** The captures are **build 38833**
(each capture's own `kind:"origin"` record says so). Every disassembly, assert and
descriptor below is read from the **pinned pristine build 38797**
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`). Where a claim depends on the two agreeing,
the row says so. Where it was checked against a 38833 client
(`vault/client/2026-08-13_64fae3b1369b/Gw.exe`), the row says that too.

---

## How to read this

Labels are `studies/character/FINDINGS.md`'s, plus `SOURCED` as `studies/smsg/FINDINGS.md`
uses it:

| Label | Meaning |
|---|---|
| **OBSERVED** | measured from our own captures |
| **SOURCED** | read out of ArenaNet's compiled client — an assert expression, a descriptor table, a source path in an allocation tag |
| **UPSTREAM** | somebody else's assertion. Not a fact about retail. Names the lineage. |
| **CORROBORATED** | genuinely independent witnesses agree; each use names them |
| **CONTESTED** | witnesses disagree; both sides recorded, nobody picks |
| **RECONSTRUCTION** | our inference |
| **UNVERIFIED** | claimed, not confirmed |
| **NOT FOUND** | we looked, we say where, there is no answer in what we have |

Eleven agents proposed; fifteen of the twenty-two proposals were then handed to a second
reader told to refute them. **Where the refutation won, this document carries the
refutation and not the proposal**, and says so. Seven opcodes (`0x002F`, `0x006F`,
`0x0071`, `0x00B5`, `0x00C3`, `0x00C5`, `0x00CA`) went through **no** refutation pass; they
are flagged individually, because an unrefuted proposal in this repo has historically been
wrong about something roughly half the time.

---

## The ledger, stated before the results

| verdict | n |
|---|---|
| name earned, from two or more independent witnesses | 9 |
| name taken from upstream, our own evidence consistent but not decisive | 4 |
| mechanism understood, **name NOT FOUND** | 8 |
| **CONTESTED** — upstream and our own client disagree, unresolved | 1 |

**Eight NOT FOUND is the honest half of this pass and the section on it is not an
apology.** One of the eight (`0x006F`) produced the single most decisive result in the
document — it settled a question `studies/character/FINDINGS.md` had recorded as CONTESTED
and then demoted to "no screenshot will ever settle" — while contributing no name at all.
The name and the knowledge came apart, and that is worth more than the count.

---

## The correction that moves five rows: **the vault holds two GWCA mirrors and half the pass read the stale one**

Five separate agents independently "derived" a **+1 opcode shift** against
`vault/mirrors/GregLando113__GWCA/Include/GWCA/Packets/Opcodes.h`, each building an
argument to justify it, one of them across three anchor pairs. **The shift is an artefact
of reading an archived copy.** The vault already holds the maintained fork:

```
vault/mirrors/gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/Packets/Opcodes.h
```

Measured this pass, first-party, over both files' full `GAME_SMSG` name tables (217 entries
each): the maintained fork is **identical on 31** names and **+1 on 186**, with the break
between `0x003B` and `0x003E` — the maintainers inserted one opcode and everything above it
moved. Twenty of our twenty-two opcodes sit above that break.

Read against the maintained mirror and against `ldufr__OpenTyria/code/opcodes.h`, **no
shift is needed anywhere in this pass.** Both lineages name these opcodes at *our* numbers,
delta 0, and they agree with each other on 13 of the 15 they both cover:

| our opcode | ldufr / OpenTyria | gwdevhub / GWCA |
|---|---|---|
| `0x002F` | `AGENT_UPDATE_ALLEGIANCE` | `AGENT_UPDATE_ALLEGIANCE` |
| `0x003A` | `AGENT_UPDATE_ATTRIBUTES` | — |
| `0x005F` | `CHAT_MESSAGE_NPC` | `CHAT_MESSAGE_NPC` |
| `0x0084` | `WINDOW_ADD_ITEMS` | `WINDOW_ADD_ITEMS` |
| `0x009E` | `AGENT_DISPLAY_DIALOG` | `AGENT_DISPLAY_DIALOG` |
| `0x00AA` | `AGENT_CREATE_NPC` | `AGENT_CREATE_NPC` |
| `0x00B9` | `MISSION_INFOBOX_ADD` | `MISSION_INFOBOX_ADD` |
| `0x00BB` | `MISSION_OBJECTIVE_ADD` | `MISSION_OBJECTIVE_ADD` |
| `0x00C3` | `MERCHANT_WINDOW_OPEN` | `WINDOW_MERCHANT` |
| `0x00C4` | `MERCHANT_WINDOW_UPDATE_OWNER` | **`WINDOW_OWNER`** |
| `0x00F5` | `TITLE_UPDATE` | `TITLE_UPDATE` |
| `0x00F6` | `TITLE_TRACK_INFO` | `TITLE_TRACK_INFO` |
| `0x011A` | `TOWN_ALLIANCE_OBJECT` | `TOWN_ALLIANCE_OBJECT` |
| `0x017E` | `INSTANCE_COUNTDOWN_STOP` | `INSTANCE_COUNTDOWN_STOP` |
| `0x0180` | `INSTANCE_COUNTDOWN` | `INSTANCE_COUNTDOWN` |
| `0x005C` `0x006F` `0x0071` `0x00B5` `0x00C5` `0x00CA` `0x011B` | *(absent)* | *(absent)* |

Three consequences, all real:

1. **Every "+1 shift" argument in this pass should be struck.** It reached the right answer
   by luck in this neighbourhood and it contradicts `studies/msgtable/FINDINGS.md`, which
   measured our alignment against build 38797 at **delta 0 on all four channels** and says
   in terms: *do not shift it.*
2. **`0x00C3`'s rejection was based on the stale file.** Its skeptic ruled the merchant
   candidate out because GWCA "assigns `WINDOW_MERCHANT` to `0x00C2`, which under the
   +1 shift would land on our `0x00C3`" — that reasoning evaporates when both lineages put
   a merchant-window-open message at `0x00C3` directly. The verdict below is revised on
   that basis and the revision is labelled as this pass's, not the skeptic's.
3. **ldufr and gwdevhub-GWCA are two lineages, not one** — they disagree at `0x00C3`/`0x00C4`
   and their name *strings* differ throughout. `apoguita__Py4GW`'s `PacketSniffer.py` is a
   third table that agrees at delta 0, but Py4GW grants nothing under `CLAUDE.md`, so it is
   used below only to verify things we derived ourselves, never as a witness on its own.
   `ldufr__Headquarter` is **the same author** as OpenTyria and is never counted twice.

---

## The twenty-two

| opcode | proposed name | label | sightings (channels) | one line |
|---|---|---|---|---|
| `0x011A` | **`TOWN_ALLIANCE_OBJECT`** | CORROBORATED | 126 (7/8) | one row per alliance-controllable Canthan outpost: map, border slot, holder, faction, guild |
| `0x011B` | **NOT FOUND** (role: the `0x011A` list commit) | RECONSTRUCTION (role only) | 7 (7/8) | closes and sorts the 18-row array; both payload fields unnamed |
| `0x00B9` | **`MISSION_INFOBOX_ADD`** | CORROBORATED | 2 (1/8) | appends a framed, closable world callout |
| `0x00BB` | **`MISSION_OBJECTIVE_ADD`** | CORROBORATED | 2 (1/8) | inserts a keyed, completable, re-textable objective |
| `0x005F` | **`CHAT_MESSAGE_NPC`** | UPSTREAM name / SOURCED mechanism | 7 (1/8) | one NPC speech line as a coded string |
| `0x009E` | **`AGENT_DISPLAY_DIALOG`** | UPSTREAM name / layout CORROBORATED | 2 (1/8) | posts an agent-attributed sender+body string to the UI bus |
| `0x00C4` | **`WINDOW_OWNER`** | CORROBORATED | 2 (2/8) | names the agent that owns the next transaction window |
| `0x0084` | **`WINDOW_ADD_ITEMS`** | UPSTREAM name / RECONSTRUCTION | 2 (2/8) | appends dwords to the client's `accumIntList[0]` staging array |
| `0x003A` | **`AGENT_UPDATE_ATTRIBUTES`** | semantics CORROBORATED / name UPSTREAM single-lineage | 5 (5/8) | the player's attribute ranks, three contiguous columns |
| `0x00F5` | **`TITLE_UPDATE`** | CORROBORATED | 5 (3/8) | patches one title track's current points |
| `0x00F6` | **`TITLE_TRACK_INFO`** | CORROBORATED | 7 (7/8) | the whole title-track record: ids, thresholds, two template strings |
| `0x017E` | **`INSTANCE_COUNTDOWN_STOP`** | CORROBORATED | 2 (2/8) | destroys the mission clock object |
| `0x0180` | **`INSTANCE_COUNTDOWN`** (client's own word: mission clock) | CORROBORATED | 3 (2/8) | arms the mission clock: caption, flags, elapsed, duration in ms |
| `0x005C` | **`AGENT_COMBO_STATE`** | SOURCED mechanism / RECONSTRUCTION name | 2 (1/8) | sets one agent's combo-state indicator for the addressed player |
| `0x00AA` | **NOT FOUND** — upstream `AGENT_CREATE_NPC` **refuted by our wire** | RECONSTRUCTION (mechanism SOURCED) | 2 (1/8) | registers {agent, allegiance token, model id} into a keyed roster |
| `0x002F` | `AGENT_UPDATE_ALLEGIANCE` | **CONTESTED** | 2 (1/8) | stamps the ally FourCC into per-agent message plumbing — *not* the rendered allegiance byte |
| `0x006F` | **NOT FOUND** | NOT FOUND (name) / OBSERVED (mechanism) | 7 (1/8) | writes one item into one visual-equipment slot — **and settles the slot order** |
| `0x0071` | **NOT FOUND** | NOT FOUND | 24 (3/8) | closes the templated-agent setup block; inserts the id into a sorted array |
| `0x00B5` | **NOT FOUND** | NOT FOUND | 5 (5/8) | hands a constant 50-byte blob to the client's Preferences module |
| `0x00C3` | `MERCHANT_WINDOW_OPEN` / `WINDOW_MERCHANT` | **UPSTREAM, name not earned** | 1 (1/8) | opens a window over the staged item list |
| `0x00C5` | **NOT FOUND** | NOT FOUND (name) / OBSERVED (behaviour) | 1 (1/8) | a composed EncString that embeds a staged item's own name |
| `0x00CA` | **NOT FOUND** | NOT FOUND | 1 (1/8) | fifth of five `ChCliApi` forwarders into UI message `0x100000B5` |

Channel denominator is 8 = the three 2026-08-17 captures' game channels.

---

# 1. The ones that got a real answer

## `0x011A` — `GAME_SMSG_TOWN_ALLIANCE_OBJECT` — **CORROBORATED**

**126 sightings, 18 per channel, in 7 of 8 channels.** The single best-evidenced result of
the pass, and the one where the refutation pass mattered most: it was proposed as
`GUILD_LADDER_ENTRY` and **two independent refutations killed it from two different
directions**, converging on the same answer.

**Shape** — SOURCED, `msgshape.py 0x011A` on build 38797: RECV table `0x00bca870`, handler
`0x00840480`, 13 fields, 98 wire bytes.

**The decisive evidence, re-derived first-party this pass.** Field 1's eighteen values are
indices into the client's own `AreaInfo` table
(`toolkit/clientscan/areatable.py`, VA `0x0096de38`, corroborated by two independent
locators, 888 rows). All eighteen resolve, and they resolve into a pattern that had
eighteen chances to fail:

| slot (f2) | map id (f1) | region | map type | holder (f3) | faction (f4) |
|---|---|---|---|---|---|
| 1 | 77 | 9 | 13 | 0 | 369,026,534 |
| 2 | 272 | 9 | 9 | 0 | 349,205,013 |
| 3 | 230 | 9 | 9 | 0 | 54,446,395 |
| 4 | 348 | 9 | 10 | 1 | 3,654,411 |
| 5 | 349 | 9 | 10 | 1 | 4,245,803 |
| 6 | 129 | 9 | 10 | 1 | 4,255,130 |
| 7 | 286 | 9 | 10 | 1 | 4,297,405 |
| 8 | 130 | 9 | 10 | 1 | 4,435,737 |
| 9 | 287 | 9 | 10 | 1 | 4,975,850 |
| 10 | 277 | 10 | 10 | 1 | 6,720,266 |
| 11 | 289 | 10 | 10 | 1 | 6,764,057 |
| 12 | 279 | 10 | 10 | 1 | 7,193,047 |
| 13 | 350 | 10 | 10 | 1 | 8,043,209 |
| 14 | 288 | 10 | 10 | 1 | 9,158,694 |
| 15 | 278 | 10 | 10 | 1 | 13,145,198 |
| 16 | 273 | 10 | 9 | 1 | 15,535,571 |
| 17 | 234 | 10 | 9 | 1 | 28,793,659 |
| 18 | 193 | 10 | 13 | 1 | 86,700,909 |

All eighteen: `campaign = 2` (Factions), `continent = 2` (Cantha) — **OBSERVED**, first-party
this pass. Slots 1–9 are **exactly** the nine region-9 maps; slots 10–18 are **exactly** the
nine region-10 maps. The map-type pattern mirrors about the midpoint: a type-13 map at each
end (slots 1 and 18), two type-9 maps inward from each end, six type-10 maps in between.
Two capitals at the two ends of an 18-position line is a **border**, not a leaderboard.

**Field-by-field:**

| field | reading | label |
|---|---|---|
| 1 `u16` | **map id** of the outpost | **SOURCED** — all 18 index the client's own `AreaInfo`, all campaign 2 / continent 2 |
| 2 `u8` | **border position, 1..18**, one end to the other | **OBSERVED** — in bijection with field 1 and partitioning exactly by region. Note GWCA's struct calls this `rank`; it cannot be a ranking of alliances, because a ranking would not partition by map region and faction is **not** monotone in it across the whole list |
| 3 `u8` | **which side currently holds the outpost** (0 for slots 1–3, 1 for slots 4–18) | **RECONSTRUCTION** — one border state only. It is *not* region (slots 4–9 are region 9 with value 1) and it is *not* a "top three" marker (slots 16–18 do not carry the same value as 1–3) |
| 4 `u32` | **the holding alliance's faction points** | **RECONSTRUCTION**, and the strongest inference here: strictly monotone descending within *both* holder groups, 18 of 18, zero exceptions, and the wire order is 1,2,3 then 18,17,…,4 — i.e. each side's list runs from its own end outward, highest faction first. WIKI (GWW, *Alliance* / *Kurzick–Luxon border*, via the `browse-gw-wiki` skill's citation rule): outposts are awarded "with preference going to the alliance with the highest amount of faction first", recomputed every three hours. Magnitudes 3.65 M – 369 M match alliance faction totals; they **rule out** an Elo ladder rating, which in GW1 runs in the hundreds to low thousands |
| 5 `string16(32)` | holding guild **name** — **literal plaintext on the wire, not an EncString** | **OBSERVED** |
| 6 `string16(6)` | holding guild **tag**, literal | **OBSERVED** |
| 7–13 `u8×5, u16, u8` | guild **cape/emblem**: background colour, detail colour, emblem colour, shape, detail, emblem, trim | **CORROBORATED** — our own element-layout read of the row builder `0x00843980` (below) against GWCA's `TownAllianceObject` seven cape fields, `StoC.h:643`. All-zero for exactly two of the eighteen rows |

> **Guild names and tags are other players' data.** They are on the wire and they are
> plaintext, and that fact is itself a protocol finding worth recording — but a roster of
> real guilds does not need to be in git to make the point. The rows are at indices
> 658–675 of `vault/captures/live/20260817T183756/game-10.0.0.210_60966-…jsonl` for anyone
> re-deriving this. `vault/` is gitignored and stays that way.

**Independent corroboration from the client's own element layout.** The second refutation
took a different route and reached the same place: disassembling the row builder
`0x00843980`, the element written at `arraybase + count*0x78` is
`+0x00` ← field2, `+0x04` ← field3, `+0x08` ← field4, `+0x0C` ← name (0x20 wchars),
`+0x4C` ← tag (5 wchars), `+0x58` ← 7 dwords of cape, `+0x74` ← field1, `sizeof == 0x78`.
That is **seven for seven** against Py4GW's independently published `TownAlliance` struct
(`Py4GWCoreLib/native_src/context/GuildContext.py:42`) and against the field *order* of
GWCA's `TownAllianceObject`. Py4GW grants nothing, so it is used here only to verify a
layout we read out of the binary ourselves — which is the permitted use. And
`0x00843AC0` (`0x011B`'s worker) **sorts these rows with stride `0x78` keyed on
`element+0x74`, the map id** — what you do to a fixed list of outposts, and precisely what
nobody does to a ladder.

**Where it lives:** container `[GlobalSingleton(0x0047f660)+0x3c]+0x2a8` — the offset
Py4GW independently calls `factions_outpost_guilds_array`.

**What was ruled out, and why the ladder reading was tempting.** Nothing anywhere says
"ladder": zero hits across every mirror in `vault/mirrors/`, and the only `Ladder` token in
a GW-relevant mirror is a GvG match-type label in GWToolbox's observer window. The GW1
guild ladder is a rated, paged, client-**queried** ~1,000-entry structure; this is an
unsolicited fixed 18-row push at map entry with no rating field and no query preceding it
(on channel `53351` the entire c2s side is 61 bytes against 13,081 inbound).

**The assert evidence the first proposal leaned on was misattributed, and this is a
reusable lesson.** `asserts.py --at` defaults to `--span 2000` (`asserts.py:649`). The six
`GuCliApi:152/202/340/363/384/420` sites returned for `0x00840480` are inside *other*
opcodes' handlers — `--span 128`, the actual function length, returns **0 sites**. The same
six come back for `0x011B` and `0x011C` alike, because a 2000-byte window from any of the
three covers the same region. **No assert names `0x011A`: NOT FOUND.** "It is in the guild
subsystem" survives only through RECV-table membership (`0x00bca870`, sourced as guild at
`studies/smsgsweep/FINDINGS.md` §7.3) — adjacency, not a per-opcode witness.

**Still open.** All 126 sightings are byte-identical, across three sessions inside a
~35-minute window on one evening, one character, two adjacent Shing Jea maps. GWW's
three-hour border cadence means 35 minutes **cannot** see the border move, so "identical"
is equally predicted by a slowly-updating list and discriminates nothing — the constancy
argument the first proposal built on it is void. The 2026-08-07 and 2026-08-10 captures
carry zero `0x011A`, so there is no cross-day sample at all. **A capture more than three
hours after these is the one experiment that would confirm field 3 and field 4 by watching
them change.**

---

## `0x011B` — the `0x011A` list commit — role only, **both fields NOT FOUND**

**7 sightings, exactly once per channel that carries the block, immediately after the 18th
`0x011A` row**, then `0x0119`, then `0x011C`.

**SOURCED mechanism** (re-verified independently by proposer and skeptic): RECV handler
`0x00840500`, table `0x00bca870`, `[u32, u8]`, 7 wire bytes. The handler is a thunk onto
the **same container** `0x011A` fills (`[0x0047f660()+0x3c]+0x2a8`), calling `0x00843AC0`,
which stores field1 → `container+0x20`, field2 → `container+0x18`, sets `container+0x1c = 1`
(a loaded flag), then — if the array holds 2 or more rows — runs an **in-place median-of-three
sort with 120-byte element swaps through a `[ebp-0x18c]` temp, comparing `[eax+0x74]`, the
map id.** So the *role* is real: **this is the commit/finalise/sort for the `0x011A`
array.** `0x011C` then sets `+0x5c = 1` and posts UI message `0x100000ce`; `0x0119` is a
wholesale reset of the guild context. Neither touches `+0x2A8`.

**Both payload fields are NOT FOUND, and the proposal's readings are refuted:**

- **field1 = 58246**, constant across all sightings, stored at `container+0x20`. Proposed as
  "total guild count server-wide". **Unfalsifiable and unsupported**: no reader is
  reachable, no upstream that has mapped this struct names the slot, and it relates to
  nothing in the block (`sum(faction) = 980,596,888`; `sum(slot) = 171`;
  `sum(map_id) = 4,569`; `58246 = 2 × 29123`).
- **field2 = 3**, constant, stored at `container+0x18`. Proposed as a "featured/top-N
  sub-count" because it equals the number of holder-0 rows. **Positively undermined by the
  client's own code**: the last instruction of the row builder is
  `inc dword ptr [eax + ebx*4 + 0x10]` at `0x00843AB1` with `ebx` = the holder byte — the
  client **already counts the holder-0 rows itself** into `parent+0x2B8`/`+0x2BC`
  (Py4GW's `kurzick_town_count`/`luxon_town_count`) and does not need the server to send
  that number. Field2 lands in a *different* slot, `parent+0x2C0`. And the correlation has
  zero degrees of freedom anyway: `count(holder==0) = 3` and `count(slot<=3) = 3` are
  **literally the same three rows**, so the corpus cannot separate "count of holder-0 rows"
  from "the top three" from "the constant 3".

**One witness, counted seven times.** All seven `(0x011A, 0x011B)` blocks hash identically
(`a4a96c447e2adf62`). Every field in the block is equally constant, so constancy
discriminates nothing about *any* field.

---

## `0x00B9` — `GAME_SMSG_MISSION_INFOBOX_ADD` — **CORROBORATED**

**2 sightings, both in the starter-zone capture, channel `53354`, message indices 329 and 331.**
Proposed as `CLIENT_NOTICE_QUEUE_ADD`; **refuted**, and the refutation is the strongest kind
available in this repo — the opcode had already been **seen on screen** and the proposal
never consulted the record.

**OBSERVED, on screen, 2026-08-12**, `studies/smsgsweep/FINDINGS.md:238`: one opcode sent
alone to a fresh client with a real encoded string, `--shots 2`, operator read the frame:
*a framed, closable callout in the world with our string in it* — box plus close button,
anchored in 3D. Same table: `0x00C0` = unframed floating world text, `0x0033` = Message of
the Day, `0x009E` = a chat line. Corroborated in two places written independently of that
table: `PLAN.md:3110`, and `toolkit/authsrv/test_shotlabel.py:20`, where the four
eye-named opcodes are the **negative controls the screenshot scorer is calibrated
against** — a load-bearing fixture in the suite, not a stray note.

**UPSTREAM, two lineages at delta 0**: `ldufr__OpenTyria/code/opcodes.h` and
`gwdevhub__GWToolboxpp/…/GWCA/Packets/Opcodes.h` both name `0x00B9`
`GAME_SMSG_MISSION_INFOBOX_ADD`. **A mission infobox is a framed closable box.** Our
operator's own words and two independent upstream tables converge — which is what promotes
this from "we know what it looks like" to a name.

**SOURCED mechanism** (verified twice): handler `0x0091F0F0` → `0x00813B70`, which does an
`Array<T>::push_back` of `{u32 flag, pointer to a freshly-allocated copy of the string}`
(8-byte element; `wcslen` via `0x0046C3A0`, alloc `len*2+2` via `0x0047F5B0`) into the array
at `[GlobalSingleton(0x0047f660)+0x2c]+0x4f8`, then posts UI frame-bus id `0x1000014C` via
`0x00633D70`. Sibling `0x00BA` (`0x00813C40`) **clears that same array** and posts
`0x1000014D` — consistent with upstream's `MISSION_STREAM_START`, and observed 1–4 times per
channel in **every** live capture including 2026-08-07 and 2026-08-10, i.e. a routine
per-map-load reset on characters that are not new Factions characters.

**Fields:**

| field | reading | label |
|---|---|---|
| 1 `string16(128)` | the callout text, as a **server-allocated dynamic string handle** | **OBSERVED** — four code units, and the first unit **increments by one** between the two sightings (`0x4A9E` → `0x4A9F`). That is a handle, not text. Contrast the same stream at idx 335 (`0x005D`), whose 4-unit prefix is followed by `0x0107` and literal UTF-16 `character B` |
| 2 `u32` | 1, then 0 | **UNVERIFIED**. Worth recording: the smsgsweep run that produced the observed on-screen callout used the all-other-fields-zero regime, so **field2 = 0 is the value proven to render a framed closable callout**, and one of our two live sightings is exactly field2 = 0. field2 = 1 is untested |

**The proposal's whole coherence story does not survive the wire.** It framed
{`0x00B8` canned toast, `0x00B9` append, `0x00BA` clear} as a triplet. Census over all live
channels: `0x00BA` appears in **every** capture; **`0x00B8` appears zero times, anywhere,
ever**; `0x00B9` appears only in the starter zone. They never co-occur. And each `0x00B9`
is **immediately preceded by a `0x00BB` carrying a byte-identical string** — the actual
wire-neighbour, which the proposal's model had no place for:

```
#328  0x00BB  402 | 8 | 4A9E C862 E359 43F2
#329  0x00B9        4A9E C862 E359 43F2 | 1
#330  0x00BB  403 | 1 | 4A9F E72D 8FFD 473E
#331  0x00B9        4A9F E72D 8FFD 473E | 0
```

**Handler-address adjacency is near-worthless here** and the proposal leaned on it: the
dispatch table is *indexed by opcode*, so contiguous handler stubs are the compiler
emitting them in opcode order, not semantic kinship. `0x00BB` in fact touches a
**different** container (`+0x564`, not `+0x4f8`).

---

## `0x00BB` — `GAME_SMSG_MISSION_OBJECTIVE_ADD` — **CORROBORATED**

**2 sightings, adjacent, one channel.** Proposed as `HELP_GUIDE_TIP_ADD`; **refuted on
seven counts**, and the name was sitting unread in the mirrors the whole time.

**UPSTREAM, both lineages at delta 0** — `ldufr__OpenTyria/code/opcodes.h` and
`gwdevhub__GWToolboxpp/…/Opcodes.h`, plus `ldufr__Headquarter` (same author, not a second
witness) and Py4GW (no-grant, verify only). A rival alignment one lower exists in the
**archived** GWCA copies and is refuted by our own bytes, not by argument: `0x00BB` has 3
fields and **inserts**; `0x00BC` has 1 field and only **sets a bit**; `0x00BD` has 2 fields
and **replaces text**. Field counts and semantics match the majority alignment exactly for
build 38797.

**SOURCED mechanism**: handler `0x0091F120` → `0x00813C70`. Keyed insert into a sorted array
at `[GlobalSingleton+0x2c]+0x564`, element stride 12: `+0` id (the key), `+4` text pointer,
`+8` flags. Lookup `0x00807C50` is a **binary search over a sorted array**, not a hashtable
— divide-by-12 midpoint via `mov eax,0x2aaaaaab; imul ecx; sar edx,2` at
`0x00807C77`–`0x00807C80`, key compared at `element+0` — and on a miss the caller memmoves
the tail open before inserting. Skips the insert on a hit (register-once). Posts
`0x1000015A`.

Two siblings jointly own the entry: `0x00BC` (`0x0091F140` → `0x00813D40`) does
`or dword ptr [eax+8], 2` on the **same** flags word and posts `0x1000015B`; `0x00BD`
(`0x0091F160` → `0x00813D90`) replaces the stored text and posts `0x1000015C`. That is an
add / complete / update-string triple, matching upstream's `MISSION_OBJECTIVE_ADD`,
`_COMPLETE`, `_UPDATE_STRING` exactly.

**Fields:**

| field | reading | label |
|---|---|---|
| 1 `u32` | objective id — sort and dedup key, stored at `entry+0` | **SOURCED**. Observed 402 then 403, consecutive |
| 2 `u32` | **a mutable flags word** at `entry+8`; bit 1 (value 2) is set by `0x00BC` | **SOURCED** — the proposal called this "a category, taxonomy unresolved", which mislabels a bitfield as an enum and hides the one fact that most constrains it. Observed 8 then 1, consistent with bits. Individual bit meanings NOT FOUND |
| 3 `string16(128)` | objective text EncString at `entry+4`, replaced by `0x00BD` | **SOURCED** |

**The proposal's core inference had a false positive 24 bytes away.** Its whole case was
"the closest `0x1000015A` subscribe site's asserts land on `GmHelpGuide.cpp:864/949`".
`0x004FEA4E`–`0x004FEA96` is **one contiguous run of six subscriptions** — `0x100000D6`,
`0x1000014E`, `0x10000152`, `0x1000015A`, `0x100001A0`, `0x100001A1` — and `0x1000014E` /
`0x10000152` are `QUEST_ADD` / `QUEST_REMOVE`, already CORROBORATED names in
`studies/quests/FINDINGS.md:401`. The identical reasoning would rename `QUEST_ADD` to
`HELP_GUIDE_TIP_ADD`. `GmHelpGuide` is a bulk **consumer** of list families, not the owner
of this one. Confirming that: `0x1000015B` and `0x1000015C` have exactly **two** subscribers
each, and the only modules consuming the whole triple resolve to `QuestTaskTracker.cpp`
(assert `QuestTaskTracker:542`) and `QuestEntryGroup.cpp`/`UiCtlInstance.h`. A widget owning
a tip catalog would need all three; `GmHelpGuide` and `QuestLog` take only the ADD.

**Honest limit.** The word **MISSION** is upstream's, not ours. `asserts.py --at` over
`0x00813B70`–`0x00813DF0` returns only generic `Array.h:587 index < m_count` — the
implementation module never names itself. What **our** bytes prove is a keyed, completable,
re-textable list of localized strings consumed by the objectives tracker and entry-group
widgets. `0x00BC` and `0x00BD` have never been observed on any wire.

---

## `0x005F` — `GAME_SMSG_CHAT_MESSAGE_NPC` — name **UPSTREAM (single lineage)**, mechanism SOURCED

**7 sightings, all in starter-zone channel `53354`** (indices 336, 408, 469, 520, 578, 690,
858). Proposed CORROBORATED; **the skeptic downgraded the label and the downgrade stands** —
the mechanism is ours, the *name* is not.

**SOURCED**: RECV table `0x00bc8f68`, handler `0x0091dfa0`,
`[agent_id, u8, string16(8)]`, 25 wire bytes. The handler marshals the three fields into a
private helper `0x00810570` (sole caller, per `asserts.py --callers`), which touches a
**"coded string" queue** off `GlobalSingleton+0x2c` and on failure logs the client's own
string *"Invalid coded string received from server"* before clearing the slot. The handler's
own vocabulary is "coded string" — this repo's EncString.

**Fields:**

| field | reading | label |
|---|---|---|
| 1 | the speaking NPC's agent id (11 or 12 here; both given a name/level/profession moments earlier) | **OBSERVED** |
| 2 `u8` | constant 11 across all 7 sightings and both agents | **UNVERIFIED** — zero variance |
| 3 `string16` | the spoken line, as an EncString id | **OBSERVED** + **SOURCED** as the client's own "coded string" |

**Wire context, OBSERVED:** every sighting is immediately preceded by
`0x009F AGENT_PROPERTY_UPDATE_INT` setting property 22 on the same agent, and by `0x005D`
whose decoded payload contains the readable substring `character B`.
`toolkit/clientscan/genericvalue.py --id 22` reads property 22 as `ApplyAnimation` —
**UPSTREAM**, unverified against build 38797 specifically — consistent with an NPC playing a
gesture before it speaks. Agent 11's string is byte-identical across all six of its
sightings.

**Why UPSTREAM and not CORROBORATED.** `GAME_SMSG_CHAT_MESSAGE_NPC` at `0x005F` comes from
**one** naming lineage — and `schema/messages.json`'s own provenance block says it was
imported from OpenTyria's `msgdefs.c`, so "our schema agrees with OpenTyria" is one witness
counted twice. The **`NPC` discriminator specifically is RECONSTRUCTION**: nothing on the
handler path says NPC, and the only reason we believe it is that the two agents it named
here are NPCs. The archived `GregLando113__GWCA` calls the same slot
`CHAT_MESSAGE_GLOBAL`; the maintained fork agrees with OpenTyria, which is why the name is
kept — but that convergence is the mirrors realigning, not two lineages independently
discovering the same thing.

**Corroborating from our own prior work:** `studies/smsgsweep/FINDINGS.md:78` and `:112`
independently classify `0x005F` as FAULTED — *"no assert at all — the client takes an access
violation… an unguarded dereference"* — OBSERVED via loopback fuzzing before these captures
existed, consistent with a path that never reaches a defensive check on this message's own
string.

**Still open.** The byte field (constant, so untestable here). The full body of
`0x00810570` past its first `ret` — the disassembler's linear sweep did not reach the code
the two forward jumps target, so the success path that actually renders the string was
never inspected.

---

## `0x009E` — `GAME_SMSG_AGENT_DISPLAY_DIALOG` — name **UPSTREAM**, layout **CORROBORATED**

**2 sightings, both agent 12, starter-zone channel `53354`, indices 250 and 289.**
Proposed CORROBORATED; **downgraded by the skeptic, and the downgrade stands**, on four
separate defects.

**Layout, CORROBORATED** by three witnesses that did not produce each other:
`msgshape.py` on build 38797 (`[agent_id, string16(32), u8, string16(122)]`, handler
`0x0091ecd0`, 319 wire bytes, struct offsets `+4/+8/+0x48/+0x4c`),
`studies/smsgsweep/FINDINGS.md:237`'s independent measurement, and the clean 38833 stream
decode.

**Mechanism, SOURCED**: handler → sole-caller helper `0x008128b0` → `0x00633d70(0x1000000c,
&struct, 0)` — the client's internal event bus. Event `0x1000000c` has **exactly one poster
and exactly one subscriber** image-wide (scan for `push imm32` + call inside
`framebus.CALL_WINDOW`); the subscriber at `0x004ecc03` sits between `GmView:3215` and
`GmView:3737`, i.e. inside `GmView.cpp`. **So "0x009E drives UI" is SOURCED; "0x009E drives a
DIALOG" is not** — `GmView.cpp` owns the trade dialog, the template manager, the party
window, the world map and item notifies alike, and the subscription cannot be tied to any
`DLG_` constant without following an indirect switch.

**Fields:**

| field | reading | label |
|---|---|---|
| 1 | speaking agent, 12 both times — an **NPC**, not a player | **OBSERVED**. Agents 11–17 each get a `0x009B` `.dat` string id at spawn; player names arrive as *literal* text (`0x017D [381,'character B']`) |
| 2 `string16(32)` | that agent's **name string**, byte-identical in both sightings | **OBSERVED**, and the strong version of the argument: it equals `0x009B`'s string for agent 12 exactly (idx 160), and `0x009B` is our own established agent-name store (`studies/smsg/FINDINGS.md:1013`, handler `0x0091ec60` writing into the per-agent array at `ctx+0x7CC`, stride `0x38`) |
| 3 `u8` | 1 both times | **UNVERIFIED** — zero variance |
| 4 `string16(122)` | a second, *differing* string — the body | **OBSERVED** identity, role **RECONSTRUCTION** |

**Three defects in the original evidence, recorded so they are not repeated:**

1. **It cited a superseded operator note.** `studies/smsgsweep/FINDINGS.md:237` ("printed a
   chat line in Local, sender: body") was corrected on 2026-08-13 by
   `studies/recon/FINDINGS.md:491-499`, which re-ran it with measurement (0.37 % changed
   against a 0.11 % idle floor over 6 idle pairs) and found **two** surfaces: a Local chat
   line *and* a closable framed window titled with the sender — and says in terms that
   `0x009E` is "not merely a chat line", with the second surface **UNVERIFIED**.
2. **Its field-role argument is void by the repo's own words.** `recon:499`: *"one string
   filling both the sender and body fields is an artifact of `corpus_encstring` supplying
   one encoded string, not a property of the message."* That run cannot assign roles.
3. **The call order is wrong.** cdecl reverses the pushes at `0x0091ecd6`–`0x0091ece1`, so
   the call is `0x008128b0(agent_id, &string1, &string2, byte)` — the byte is **arg 4**, and
   the posted struct is `{agent_id, &str1, &str2, 0, byte}`, a 5-dword struct with a zeroed
   slot the proposal does not mention. Exactly the detail a sender implementation needs.

**Rival that fits equally well and could not be separated:** `AGENT_SPEECH` — an ambient
NPC line, chat bubble and/or chat panel, not an interactive dialog panel. Agent 12 is one
of seven NPCs spawned together; the two lines arrive 39 messages apart in an otherwise pure
heartbeat stream; field2 is *redundant* with the name the client already stored, which is
what a self-contained ambient line needs and a store-driven dialog panel would not. The
c2s half of that channel does not decode (`GAME_CMSG` stops at offset 0), so "the player
never interacted with agent 12" is UNVERIFIED. **DIALOG vs SPEECH: UNVERIFIED.**

---

## `0x00C4` — `GAME_SMSG_WINDOW_OWNER` — **CORROBORATED**

**2 sightings** — `183756/58389` idx 1499 (agent 272) and `183756/60966` idx 2269 (agent
279). Proposed as `MERCHANT_WINDOW_UPDATE_OWNER`; **the "MERCHANT" qualifier is refuted by
our own client and the skeptic's `WINDOW_OWNER` stands.**

**SOURCED, and this is the decisive part.** `codescan.py --xrefs` returns *every* reference
to the two globals `0x010876C8` / `0x010876CC` — 11 and 19, all inside
`0x00813F80`–`0x00814496`. Mapping each helper to the opcode whose RECV handler calls it
gives, exactly:

- **one writer**: `0x00C4` → `0x00813FE0` (store agent, set flag = 1)
- **eight readers**: `0x00C3`, `0x00C5`, `0x00C6`, `0x00C8`, `0x00C9`, `0x00CA`, `0x00CB`,
  `0x00CD` — each builds `{id, stored_agent, 0, stored_flag, …payload}`, posts it with UI
  frame message `0x100000B5` via `0x00633D70` (whose own assert is
  `FrApi.cpp:3901 msgId >= FRAME_MSG_EX`), then `mov [0x010876CC], 0` — consume and clear
- **one control that proves the mapping is not an artefact of coarse bounds**: `0x00CC`
  (`0x008143F0`) is in the same block and does **not** read it

**A register written by one opcode and consumed by eight — spanning the merchant family
*and* the trader family (`0x00C6` `TRANSACTION_REJECT`, `0x00CD` `TRADER_WINDOW_OPEN`) plus
five slots upstream does not name at all — is a WINDOW owner, not a MERCHANT WINDOW owner.**

The handler also calls `0x00817950`, which fetches both agents' positions (assert
`AgApi:517 ptr`), compares the two `(x,y)` pairs, computes an angle and applies it: it
**turns the character to face the named agent**. Generic interaction machinery. (The
proposal called this "a possibly-null registered callback"; it is a direct `rel32` call to a
fixed function, and the fetched singleton pointer is merely its first argument.)

**Field 1** = the counterparty agent id. **SOURCED** as the value written into the owner
register plus its active flag.

**Lineage, and why the original label was a miscount.** `MERCHANT_WINDOW_UPDATE_OWNER` is
**one** lineage — OpenTyria and Headquarter are the same author, and the
gw-preservation and Py4GW hits are byte-for-byte that same naming (and both grant nothing).
The maintained GWCA fork says **`WINDOW_OWNER`**, no merchant. And the merchant lineage
contradicts itself: `ldufr__Headquarter/code/client/item.c:523` names the function
`HandleWindowOwner` and the struct `WindowOwner` — generic — and on receipt sets
`world->interact_with = pack->agent_id` and broadcasts `EventType_DialogOpen`. Its extra
`array_clear(&world->merchant_items)` is that project's model choice, not a fact about
retail. So: three witnesses for `WINDOW_OWNER` (GWCA lineage; the merchant lineage's own
implementation; our build-38797 disassembly), one lineage for the merchant spelling.

**The observational asymmetry cuts the same way.** The two sightings are **not** the same
shape:

```
s1  0x00C4[272] -> 11x 0x0161 (priced stock) -> 0x0084[11 ids] -> 0x00CA[1, 1.0f] -> 0x00C3[11, 0]
s2  0x00C4[279] ->  3x 0x0161               -> 0x0084[3 ids]  -> 0x00C5[2, composed string]
```

Two different window kinds behind the same `0x00C4` is what a generic `WINDOW_OWNER`
predicts and what a merchant-specific name does not. Both owners are NPCs (each got a
`0x009B` encoded-string name). None of the eight consumer opcodes other than `0x00C3`/`0x00C5`
ever fires in our corpus, so **we have never observed the stored value being used** beyond
those two.

**Self-correction recorded so it is not re-run:** the skeptic first flagged
`0x011A [… 272 … 'a guild name', 'PR' …]` as a guild tag on agent 272, which would have
made 272 a player and killed the reading. `0x011A` field 0 is a `u16` **map id**, not an
agent id — a numeric collision. Withdrawn.

---

## `0x0084` — `WINDOW_ADD_ITEMS` — name **UPSTREAM**, label **RECONSTRUCTION**

**2 sightings.** `58389` idx 1500–1511: eleven consecutive `0x0161` creates for item ids
2473–2483 then `0x0084 = [2473…2483]`, 11/11, same order, no gaps. `60966` idx 2270–2273:
three creates then `0x0084 = [2241, 2242, 2243]`, 3/3. Proposed CORROBORATED; **downgraded,
and the downgrade stands.**

**SOURCED mechanism**: handler `0x0091E820` → worker `0x00811980`, which appends each wire
dword into the array at `ctx+0x24` (cap `+0x28`, count `+0x2c`), `ctx` reached through a
TLS slot. The consumer at `0x00811A00` asserts `ChCliApi:1587
context->accumIntList[0].Count() == context->accumIntList[1].Count()`, which **pins
`ctx+0x24` to `accumIntList[0]`** — the client's own field name.

**The decisive objection, reproduced first-party this pass:**

```
0x0084  RECV  table 0x00bc8f68  handler 0x0091e820   [array32[16]]
0x00D7  RECV  table 0x00bc8f68  handler 0x0091e820   [array32[8]]
```

**`0x0084` and `0x00D7` dispatch to the same function.** The client makes no distinction
between them, so a name asserting "ITEMS" asserts a distinction the binary does not make.

The buffer is a **shared two-column staging area, not an item window**: appenders
`0x00811980` (list 0; opcodes `0x0084`, `0x00D7`) and `0x00814610` (list 1 at `+0x34/+0x3c`;
opcodes `0x00D8`, `0x00F9`); four drains, each raising a different event and zeroing the
counts (`0x0085`→`0x100000B8`, `0x0086`→`0x100000B9`, `0x00D4`→`0x10000052`,
`0x00E1`→`0x100000BA`). Under upstream's own naming that last drain is
`SKILL_ADD_TO_WINDOWS_END` — the same buffer serves the skill stream as well as the item
stream. It is also **not persistent per-connection**: TLS-sourced, and every drain resets
the count immediately.

**Census: none of the drains ever fires.** `0x0085`, `0x0086`, `0x00D4`, `0x00D5`, `0x00D7`,
`0x00D8`, `0x00E1`, `0x00F9` = **zero** occurrences across all 2026-08-17 channels. The
behavioural half of the name rests entirely on upstream.

**But this pass found the consumer the census missed** — see `0x00C5` below.
`0x00C5`'s own assert requires `accumIntList[0].Count() >= 1`, and on the wire `0x0084` fires
**immediately before it**. The precondition `0x00C5` needs is exactly what `0x0084` had just
satisfied, and `0x00C5`'s string embeds one of the ids `0x0084` staged. That is a live,
observed reader of `accumIntList[0]` in the corpus, and no agent found it.

**Record it as:** name `WINDOW_ADD_ITEMS` = **UPSTREAM** (both lineages, delta 0); payload =
the ids of the immediately preceding `0x0161` batch = **OBSERVED**, n = 2; mechanism =
appends each dword to `ChCliApi accumIntList[0]` = **SOURCED**; **"items" specifically =
NOT ESTABLISHED.** A mechanism-honest alternative name is `ACCUM_INT_LIST0_APPEND`.

---

## `0x003A` — `GAME_SMSG_AGENT_UPDATE_ATTRIBUTES` — semantics **CORROBORATED**, name **UPSTREAM single-lineage**

**5 sightings** (4 in the two named captures, +1 in `183323`), every one carrying the
byte-identical array `[29, 30, 2, 1, 2, 1]`. Proposed CORROBORATED across the board; **the
skeptic split the label and struck one behavioural claim, and both changes stand.**

**Layout, SOURCED, re-derived on the pinned 38797** (`codescan.py --dis 0x0091d8c0`) — the
wire array is **three contiguous columns, n = count/3, not interleaved triples**:

```
mul dword ptr [ecx+8]           ; count
lea eax,[ecx+0xc] ; shr edx,1   ; edx = count/3 = n
lea eax,[eax+edx*8] ; push eax  ; arr3 = payload+0xC + n*8
lea eax,[ecx+0xc] ; lea eax,[eax+edx*4] ; push eax   ; arr2 = +0xC + n*4
lea eax,[ecx+0xc] ; push eax    ; arr1 = +0xC
```

Chain `0x0091D8C0` → `0x0080EB40` → `0x00819BB0`. The client's own arithmetic refutes the
interleaved rival, which is a much stronger argument than the proposal's "retail didn't
crash".

**It really is attributes, and that is not upstream.** `asserts.py --at 0x819bb0` puts the
callee's asserts in **`P:\Code\Gw\Char\Cli\ChCliAttrib.cpp`** — lines 368, 435, 442, all
`attribState`. ArenaNet's own module name, reached by provable dispatch from `0x003A`'s
handler. This is the genuine second witness and it is what makes the semantics
CORROBORATED.

**Fields:** field 1 = the **local player's own** agent id (OBSERVED 5/5, cross-checked per
channel against `PLAYER_INFO`; in one channel there are 16 other players in the district
and `0x003A` is sent for none of them). Field 2 = three columns: **attribute id** (client
bound-checks 0..50), **rank** (client caps at 12 — `CharData.cpp(202)
level < arrsize(s_attribPoints)`, `arrsize` 13), and a third column **RECONSTRUCTION** as
"effective rank including bonuses", OBSERVED here to equal column 2 exactly.

**Profession is OBSERVED, not inferred** — the proposal under-claimed. `0x00A6` reads
`[166, <player>, 7, 0]` in every channel: profession 7 = Assassin, no secondary.
`toolkit/clientscan/attribtable.py --summary` (SOURCED, the client's own self-indexed
`s_attrib` table) gives profession 7 = ids `[29, 30, 31, 35]`, primary 35. **Two ids drawn
from 51 slots both landing in the 4-slot block of the character's independently-measured
profession** is a check that could have failed (~0.5 % under a null) and did not. Id 29 =
Dagger Mastery is CORROBORATED at `studies/character/FINDINGS.md:616-650`.

**A rival killed by a check that could have failed:** "column 3 = attribute points
invested". `attribpoints.py` reads the client's own cost table
`[1,2,3,4,5,6,7,9,11,13,16,20]`; rank 2 costs 1+2 = 3, but column 3 shows 2. Refuted.

**STRUCK: "resent fresh at every area/instance load."** Capture `20260817T180610` contains
two full instance loads of the same character (40 and 23 `WORLD_CREATE_AGENT` respectively,
both channels decoding clean) and **zero** `0x003A`. The discriminator, SOURCED from
`genericvalue.py`: property 36 = `PublicLevel`. In `180610`, `PublicLevel = 1`, health 100,
empty skillbar → no `0x003A`. In `183323`/`183756`, `PublicLevel = 2`, health 120, skillbar
`[814, 783, 2, 858, 0, 0, 0, 0]` → `0x003A` present. **The message is conditional on the
character actually having attribute ranks, not part of the unconditional load preamble.**
Once found, that negative is *additional* behavioural support for the attribute reading.

**n = 1, not 4.** All five sightings carry the identical array — the same character in the
same attribute state. Presenting three agent ids as mutual confirmation is one observation
counted three times.

**Name label**: `ldufr__OpenTyria/code/opcodes.h:186` and
`ldufr__Headquarter/code/client/opcodes.h:185` are a byte-identical macro line from the same
author — **one** witness. Py4GW republishes the identical spelling and grants nothing.
GWCA offers no name at this opcode. **`toolkit/authsrv/authsrv.py:1263` is not a witness** —
our server adopted OpenTyria's name; citing it is circular.

**What would test column 3:** a second character, or the same character with a rune.
One distinct payload exists in the entire corpus.

---

## `0x00F5` / `0x00F6` — `TITLE_UPDATE` / `TITLE_TRACK_INFO` — both **CORROBORATED**

**`0x00F5`: 5 sightings, 3 channels. `0x00F6`: 7 sightings, 7 channels** (absent from
`180610/53345`). Both proposals were **not refuted**, but both skeptics found the presented
reasoning wrong in ways that matter, and the corrected reasoning is what is recorded.

**Both handlers write the same array.** `0x00F6` (handler `0x0091F8F0` → `0x00814FE0`) grows
the array at `[ctx+0x81c]` (stride `0x2C`, capacity `ctx+0x824`) to `index+1`, `rep movsd`
copies **nine** wire dwords into `entry+0x00..+0x20`, then duplicates the two wire EncStrings
into fresh buffers at `entry+0x24` and `entry+0x28`. 9 dwords (36 B) + 2 pointers (8 B) = 44 B
= the stride exactly, with no slack. `0x00F5` (handler `0x0091F8D0` → `0x00814F60`)
bounds-checks its index against the same `ctx+0x824`, writes its second field to
`entry+0x04` — the **second** of those nine dwords — and posts UI message `0x10000065`.
Guards the proposals omitted: `0x00F5` does nothing unless `entry+0x28` is non-null (only
patch tracks that have a description).

**The client witness both proposals missed, and it is what earns CORROBORATED.**
Function `0x008A9880` lives in `AttribTitles.cpp` — assert at `0x008A9908`,
**`AttribTitles:114 codedNextTierName`** (verified this pass: `asserts.py --grep
codedNextTierName` returns exactly that one site; the string
`P:\Code\Gw\Ui\Game\Attributes\AttribTitles.cpp` is present in the image at `0x79e73e`).
It passes **one index** to both `0x005A9350` — which asserts
`ConstTitle:81 index < arrsize(s_titleClientData)`, bound 48 — and `0x008172A0`, which
returns `ctx+0x81c + index*0x2c`. **So `0x00F6`'s field 1 is a title id in ArenaNet's own
48-entry title table, named by the client's own assert.** Without it, the disassembly proved
only "a 44-byte record keyed by an index" and the name came from one mirror.

**A falsifiable wire test that could have failed and did not — re-run first-party this
pass.** `0x00F3` fills a 12-byte-stride rank table at `ctx+0x82c`; `0x00F6`'s fields 4 and 7
should be indices into it. In every channel that carries the block:

```
0x00F3 [199, flags=1, value=0,   <EncString>]
0x00F3 [200, flags=1, value=600, <EncString>]
0x00F6 [2, 1, N, 199, 0, 0, 200, 600, 6, 200, <EncString>, <EncString>]
```

`0x00F6`'s field 5 = 0 **equals** rank 199's value; field 8 = 600 **equals** rank 200's
value. The rank pair is on the wire, not inferred.

**`0x00F6` field map** (entry offsets; SOURCED unless noted):

| wire | offset | reading |
|---|---|---|
| 1 = 2 | — | **title id**; indexes `s_titleClientData` **and** the `ctx+0x81c` array |
| 2 = 1 | `+0x00` | **flags**; bit 0 makes the renderer divide the paired value by 10 and print `N.M` (`mul 0xcccccccd; shr edx,3`) |
| 3 = varies | `+0x04` | **current points** — the only field that varies, and the only field `0x00F5` patches |
| 4 = 199 | `+0x08` | **current rank id** → `0x00F3` record 199 |
| 5 = 0 | `+0x0c` | current rank minimum value |
| 6 = 0 | `+0x10` | the dword GWCA's struct lacks. Read by nothing found. **UNVERIFIED** |
| 7 = 200 | `+0x14` | **next rank id** → produces `codedNextTierName` |
| 8 = 600 | `+0x18` | next rank minimum; `-1` means "no next rank" |
| 9 = 6 | `+0x1c` | rank count. **UNVERIFIED** |
| 10 = 200 | `+0x20` | max rank id; used as an upper bound |
| 11, 12 | `+0x24`, `+0x28` | **printf-style template EncStrings**, not captions — `+0x28` is composed with the next-tier name *and* the number; `+0x24` with the current value |

**`0x00F5` field map:** field 1 = title id (constant 2 in all 5 sightings); field 2 = the new
current-points value.

**OBSERVED progression, whole corpus, this pass:** `1 → 2` (180610), `8` (183323 seed),
`8 → 9 → 10` (183756/60966), `11 → 12 → 13` (183756/52294). One character, one evening, a
single running counter. **Not three independent sessions** — the proposals' "three
independent starting values" is one continuity, not three witnesses.

**Two reasoning corrections, both material:**

1. **The `+1 shift` was unnecessary and contradicted the repo.** OpenTyria names both
   opcodes at our numbers directly (`opcodes.h:282`, `:283`). Citing GWCA's archived table
   plus a manufactured shift imports exactly the drift
   `studies/msgtable/FINDINGS.md` forbids. **Do not ship that justification.**
2. **The "rank threshold" field mapping was wrong.** Fields 4 and 7 are rank **ids**, not
   thresholds; the thresholds are fields 5 and 8, confirmed against `0x00F3` above.

**Build gap closed:** `msghandler.py 0x00F5` against the 38833 client gives handler
`0x0091F930` → worker `0x00814E00`, same receive table `0x00BC8F68`, same descriptor cmds,
same `ctx+0x81c`/`ctx+0x824`, same stride `0x2C`, same store to `entry+4`, same
`0x10000065` post. Identical semantics on the build that produced the bytes.

**What title id 2 IS: not claimed.** Flags bit 0 (tenths) + a next-rank minimum of 600
rendering as `60.0` + 6 ranks + a value climbing 1 → 13 is the shape of a percentage
exploration track for a fresh Factions character; OpenTyria's `GmTitles.h` puts
`TitleId_CanthanCarto` at 2. **UPSTREAM, and consistent, and not decided here.** Every
`0x00F3` record in the older captures (ids 13, 80, 85, 92, 111, 113, 133, 146, 151, 152,
177, 310, 314, 347, 364, 365) carries flags = 0, i.e. integer-point tracks — so this one is
genuinely different in kind.

**Free riders on the same evidence:** `0x00F3` = `TITLE_RANK_DATA` (rank definition: id,
flags, threshold, coded name; array `ctx+0x82c`, stride 12). `0x00F4` = `TITLE_RANK_DISPLAY`
(array `ctx+0x80c`, stride `0x50`, writes `+0x30`, posts `0x10000064`) — UPSTREAM-plus-shape,
not independently confirmed.

---

## `0x017E` / `0x0180` — `INSTANCE_COUNTDOWN_STOP` / `INSTANCE_COUNTDOWN` — both **CORROBORATED**

**`0x017E`: 2 sightings. `0x0180`: 3 sightings** — the proposal said two and missed that
`183756/52294` carries a byte-adjacent duplicate at idx 1201 **and** 1202. Neither proposal
was refuted; both skeptics found the decisive evidence the proposals lacked.

**The client names the object itself.** `0x0180`'s worker `0x0084FC30` allocates a
**0x10-byte** object through the client's own debug allocator tagged with the literal source
path **`P:\Code\Gw\Mission\Cli\MsCliClock.cpp`**, line `0x6D` (109) — verified present in the
image at `0x7965ef` this pass. A **Mission-client clock**, straight out of ArenaNet's build.
That, not any mirror, is what makes these names defensible.

**`0x017E` is the destructor of the object `0x0180` constructs**, and the pairing is
airtight: same slot `[percontext+0x9c]`, same `0x10` size, exactly one caller each
(`0x0084E700` and `0x0084E750`), and image-wide only four sites push UI message
`0x10000093` — two of them are these. `0x017E` frees the owned label handle, frees the
object, posts `0x10000093`, zeroes the slot. `0x0180` tears down any existing clock via that
identical path *first*, then builds the new one and announces it with `0x10000094`.

**"Countdown" is SOURCED, not inferred from round numbers.** The getter `0x0084FB70` (one
caller, reaching `GmMissionStatus.cpp`) computes:

```
elapsed = (flags & 4) ? realtime() - field[4] : field[4]
total   = field[0]
out     = total ? ((elapsed < total) ? total - elapsed : 0) : elapsed
```

**Time remaining, clamped at zero.** And the units are SOURCED too: the consumer at
`0x0052B8B0` `fild`s the result, applies the 2^32 unsigned fixup, then divides by the
double `1000.0` at `0x943898`. **Field 4 is milliseconds.**

**`0x0180` field map** (all SOURCED, upgraded from the proposal's RECONSTRUCTIONs):

| field | reading |
|---|---|
| 1 `string16(122)` | a caption; the client **wcsdups** it (`0x0046C050` measures *and* copies, returning a pointer stored at object `+0x0c` — both teardown paths free it). Observed as a **single** code unit, `0x0575` twice and `0x7B56` once: an encoded string id, **content NOT FOUND** |
| 2 `u8` | UI flag byte, whole value OR'd with 4 into object `+0x08`; bit 0 → style bit `0x10`, bit 1 → layout enum, **bit 2 is the mode selector** (`0x017F` and the getter both branch on `test byte [esi+8],4`; `0x0181` explicitly clears it). Observed 5 in all three sightings |
| 3 `u32` | already-elapsed offset in ms, subtracted from realtime to seed `+0x04`. Observed 0 |
| 4 `u32` | **total duration in milliseconds** at `+0x00`. Observed 10000 and 60000 |

**Cross-build gap closed for these two**: on the 38833 client the handler moves to
`0x0084E810` and the worker to `0x0084FCF0`, with the **same** `MsCliClock.cpp:109` tag, the
same `or ecx,4`, the same realtime call, the same `wcsdup`, the same UI messages, and a
byte-for-byte identical getter. The mechanism holds on the build that produced the captures.

**What our captures contribute is thin, and the proposals overstated it.** In `180610` the
arm-then-stop is two adjacent messages — a 60 s clock cancelled inside the same TCP segment.
In `183756` the arm is at idx 1201/1202 and the stop 85 messages later. **We have never
observed a countdown run to completion**, and both sightings are bare or near-bare. A 10 s
clock in Shing Jea Monastery — an **outpost**, not a mission map — is not explained, and the
"INSTANCE" in upstream's name is not supported by where we saw it. The client's own
vocabulary would render these `MISSION_CLOCK_STOP` / `MISSION_CLOCK_START`.

**Lineage note:** the four mirrors carrying these names (`ldufr__OpenTyria:340-341`,
`gwdevhub` GWCA `:181-182`, gw-preservation's `Constants.ts:337-338`, Py4GW's
`PacketSniffer.py:212-213`) carry byte-identical name strings across an identical name
*sequence*. **That is one naming lineage propagated, not four witnesses.** CORROBORATED
holds because our SOURCED client evidence agrees with it, not because of the count.

**Never observed:** `0x017F` (re-anchor the running clock) and `0x0181` (set the displayed
value directly and leave anchor mode). Their readings are mechanism-only.

---

## `0x005C` — `AGENT_COMBO_STATE` — mechanism **SOURCED**, name **RECONSTRUCTION**

**2 sightings**, `183756/52294` idx 940 and 1167: `(27, 38, 1)` then `(27, 38, 0)`.
Proposed as `AGENT_STATUS_DOT_STATE` with a CORROBORATED gate claim; **the skeptic refuted
the gate claim and renamed it, and both changes stand.**

**SOURCED end to end.** Handler `0x0091DF40` → `0x008103A0`, which does nothing unless
field 1 matches the addressed player. If it matches, `(field2, field3)` go to `0x007DFB40`,
which resolves field 2 through `0x00802160` — the AgentView "type tag == 0xDB CHARACTER"
resolver already named in `studies/enemy/PLAN.md` S10 — and then to `0x007F6DE0` (in
`AvChar.cpp`, exactly one direct caller, so **`0x005C` is the only wire message that sets
this state**):

- field3 == 0 → clear byte `+0x1B4`, post UI frame `0x1000000A` immediately
- field3 != 0 → allocate a queue node on the `+0x140` list, store field3 at node `+0x1C`;
  the deferred path at `0x007FA01D` writes it to the same `+0x1B4` and posts the same frame

**field 3 IS `comboState`, and this was proved rather than assumed** — the post builds a
2-dword payload `{agent, field3}`; `GmAgentStatusDot`'s dispatch at `0x0053E1E6` compares
payload[0] against its bound agent and pushes **payload[1]** as the argument to `0x0053E340`,
whose asserts are the client's own words: **`GmAgentStatusDot:134 comboState !=
CHAR_COMBO_STATES`** and **`:141 No valid case for switch variable 'comboState'`**.
`CHAR_COMBO_STATES == 4` (`cmp esi,4`), so valid states are 0..3.

**The CORROBORATED gate claim was false, and this capture refutes it.** The proposal said
field 1 is compared against `ctx[0x44][0x2ac]`, citing
`studies/heroes/FINDINGS.md:1349-1368` and `studies/pvpui/FINDINGS.md:582-584` as
independent corroboration that this slot is the player's agent id. The full body (the
proposal read a listing truncated at a `ret` a `jne` jumps past) shows the gate is
`field1 == playerRecord[playerId].agentId`, where `playerId = ctx[0x44][0x2ac]` and the
client's own assert names it: **`ChCliApi:4809 !(playerId & CHAR_CLASS_BASE_MASK)`**.
On the wire, `0x0199` arrives as `[409, 1, 238, …]` — playerId = **1** — while `0x0059
PLAYER_CREATE` gives player 1 → agent **27**. **On the proposal's stated mechanism the
handler would no-op on both sightings**, making the whole reading vacuous.
`studies/heroes/FINDINGS.md` §21.2 had already flagged this as unsettled *"in this rig it is
1, and so is PLAYER_AGENT_ID; breaking that needs the client's own value moved."*
**This capture is that test and it moves the value.** The conclusion (field 1 = the local
player) survives via the array indirection and is OBSERVED — but `studies/heroes/FINDINGS.md`
§22 and `studies/pvpui/FINDINGS.md:582-584` both need correcting.

**Fields:** 1 = the addressed player's own agent id (gates the handler); 2 = the target,
which must resolve to a CHARACTER-classed agent or the call is a no-op; 3 = the state,
client-bounded 0..3.

**Context OBSERVED this pass:** both sightings are inside a fight. Agent 38 damages agent 27
at idx 939/942 and again at 944/953/956; agent 27 damages 38 at 1157. Agent 38 was created
with class nibble 0x2 (NPC) against the player's 0x3, and `PLAYER_CREATE` fires exactly once
in the instance — so 38 is definitely not a player.

**What "combo" means as a game mechanic is UNVERIFIED.** The assert gives the enum's name,
not its game-facing meaning. The `GmCtlSkImage:664 comboLink` / `ComboLinkImageList`
asserts offered as skill-chain corroboration are **module proximity, not a traced link** —
they are not in this frame's dispatch. A rival that fits equally well: field 3 is a
hostility/engagement state for the addressed player's HUD which ArenaNet's UI code happens
to call `comboState`. **NOT FOUND upstream:** OpenTyria has no `GAME_SMSG 0x005C` (gap
between `PLAYER_DESTROY` and `CHAT_MESSAGE_CORE`), and no mirror names it.

`studies/skills/FINDINGS.md:719` names opcode 92 `SKILLBAR_SKILL_SET` — that is
`GAME_CMSG` 92, a different message on the client-to-server channel with a different shape
and size. Checked and ruled out.

---

## `0x00AA` — upstream `AGENT_CREATE_NPC` is **REFUTED by our own wire**; name **NOT FOUND**

**2 sightings**, starter-zone channel `53354`: `(15, 'play', 0x20000C2D)` and
`(17, 'play', 0x20000C2C)`, both immediately before the two `0x002F` sightings for the same
two agent ids in the same order.

**The upstream name is refuted, and refuting a two-lineage name with our own bytes is the
best thing this opcode produced.** Both `ldufr__OpenTyria` and the maintained
`gwdevhub` GWCA call `0x00AA` `AGENT_CREATE_NPC`. **Nothing is created.** Agents 15 and 17
were already brought into the world by `WORLD_CREATE_AGENT` at message indices 187 and 204;
`0x00AA` arrives at 339 and 345 — about 135 messages later. Verified first-party this pass.

**Field 3 is the agent's model / type id — OBSERVED, and this is a direct correction.** The
proposal read it as an opaque per-registration handle whose "low byte decreases by 1",
inferring a sequence counter. Checked against the creates:

```
#187  0x0020 create  agent 0x0F  model 0x20000C2D  allegiance 'nonc'
#204  0x0020 create  agent 0x11  model 0x20000C2C  allegiance 'nonc'
#339  0x00AA         agent 0x0F  'play'  0x20000C2D   <- equals the create's model
#345  0x00AA         agent 0x11  'play'  0x20000C2C   <- equals the create's model
```

**Field 3 equals that agent's own `WORLD_CREATE_AGENT` model id, exactly, both times.** The
"counter" was two adjacent model ids.

**And the pair is an allegiance CHANGE.** Both agents were created carrying the token
`0x6E6F6E63` (`'nonc'`) and are then named by `0x00AA` and `0x002F` carrying
`0x706C6179` (`'play'`) — the ally FourCC established at
`studies/enemy/PLAN.md:185-206` and `:477-508`, where field 12 of `WORLD_CREATE_AGENT`
carrying it colours an agent's nameplate green. **OBSERVED**; that the pair *is* an
allegiance change is **RECONSTRUCTION**, but it is corroborated by both lineages naming
`0x002F` `AGENT_UPDATE_ALLEGIANCE`, and it is the first time this repo has seen the
transition on retail's own wire.

**SOURCED mechanism**: handler `0x0091EF10` → `0x00813560`, which (a) looks up or creates a
per-agent record for field 1 in a container at `[ctx+0x2C]+0x8C`, storing field 2 at
`record+4` and field 3 at `record+8`; then (b) under the guard
**`MsCliApi:396 context->map == MISSION_MAP_GAME`**, (c) calls `0x0084DD20` with field 2 as a
**roster key**, enumerating every other agent already registered under the same allegiance
token and linking each to the new one. That extends the allegiance-token system from
"colours a nameplate" to "is a live roster key".

**The name is NOT FOUND.** `AGENT_CREATE_NPC` is refuted. The skeptic's `PARTY_ALLY_ADD` is
**not** an upstream name — it is their own RECONSTRUCTION over a solid SOURCED mechanism, and
no assert or string in the traced chain says "join", "party" or "allegiance" in those words.
Recording a made-up name here would put an invention into the schema, which is the failure
mode this repo's label vocabulary exists to prevent. **Record the mechanism, leave the name
empty.**

**Open:** Shing Jea Monastery is an outpost, so `MISSION_MAP_GAME` almost certainly reads
false there and **only step (a) was exercised live** — the enumeration/link step has never
run in anything we captured. `GAME_SMSG 0x003E AGENT_ALLY_DESTROY` (both lineages) is a
natural counterpart and has never been observed either.

---

# 2. The eight that stayed NOT FOUND — and what that bought

This section is longer than several of the named ones, and it should be. **One NOT FOUND
opcode settled a question two lineages had been contradicting each other about for months.**
A name is a label; what the eight below produced is mechanism, refutation and one closed
contest.

---

## `0x006F` — no name anywhere — **and it settles the equipment slot order**

**7 sightings, all agent 356, `183756/60966`.** No refutation pass was run on this one; I
re-derived all of it first-party this pass instead.

**No canonical name exists in any lineage searched.** OpenTyria's `opcodes.h` skips 111
outright (110 `UPDATE_AGENT_VISUAL_EQUIPMENT` → 112); the maintained GWCA has no entry;
GWLP-R has no `P0111`. `studies/character/FINDINGS.md:1496`'s existing "(unnamed upstream)"
label stands. **NOT FOUND.**

**What it does, OBSERVED:** writes ONE item into ONE position of the same 9-slot array that
`0x006E UPDATE_AGENT_VISUAL_EQUIPMENT` carries in bulk. Fields: agent, slot, item id.

**The result.** `studies/character/FINDINGS.md:1519-1549` records the nine-position ordering
as **CONTESTED** — one lineage (GWLP-R) says permuted, two (ldufr, GWCA) say bag order — and
after the 2026-08-17 `armor_slots` probe it was demoted with the words *"the item drives its
own placement; the position does not choose the body part, so bag order vs permutation
cannot be told apart by looking… the routes that could are a memory read of the equipped
bag or a behavior keyed to position."*

**Retail's own wire is a third route nobody listed, and it decides it.** Each `0x006F` is
immediately preceded by a `0x015E` declaring that item, whose third field is the item type:

| `0x006F` slot | item id | `0x015E` item type | type name |
|---|---|---|---|
| 2 | 5059, 5472 | 7 | Body |
| 3 | 3680 | 4 | Boots |
| 4 | 3787 | 19 | Legs |
| 5 | 4729 | 13 | Gloves |
| 6 | 3263 | 16 | Head |

And the bulk message for the same agent closes it in one shot —
`0x006E [356, 0, 0, 5059, 3680, 3787, 4729, 3263, 0, 0]` at idx 4094 — the array positions
are the same numbering.

**The item-type enum is CORROBORATED across two independent lineages**, checked this pass:
`ldufr__OpenTyria/code/GmItem.h:4-40` gives Boots 4, Body 7, Gloves 13, Head 16, Legs 19;
`gwdevhub__GWToolboxpp/…/GWCA/Constants/Constants.h:129-132` gives Boots 4, Chestpiece 7,
Gloves 13, Headpiece 16, Leggings 19 — different spellings, same numbers, different authors.
Anchored first-party by `ITEM_TYPE_BAG == 3`, SOURCED from our own client
(`studies/smsg/FINDINGS.md`) and matching both.

So:

- **Permuted** (GWLP-R: Boots 3, Legs 4, Gloves 5, Head 6): **exact match, 5 for 5.**
- **Bag order** (ldufr/gw-preservation: Legs 3, Head 4, Boots 5, Gloves 6): **REFUTED.**
  The two hypotheses' numbers are literally swapped, and retail's own type tagging picks
  permuted.

**Label:** the (type, slot) pairs are **OBSERVED**; the type enum is **CORROBORATED**
(two lineages + one SOURCED anchor); the conclusion is therefore **CORROBORATED**, for
retail build 38833, non-visually and non-circularly. Note that this uses **ldufr's own type
enum to refute ldufr's slot order** — a lineage refuting itself is not circular, but it does
rest on that enum being right, and GWCA agreeing is what keeps it from resting on one
source.

**Open:** the two body-item swaps at slot 2 mid-capture (5059 → 5472 → 5059, both type 7)
are unexplained — a tailor or dye preview at the Monastery is a guess. `0x015E`'s own name is
also NOT FOUND; its shape equals the first nine fields of `0x015F CREATE_UNNAMED_ITEM`, and
`studies/smsg/FINDINGS.md:972` already carries it as PARTIAL (`ITEM_LOW_DETAIL`).

---

## `0x0071` — NOT FOUND, and one field reading is refuted by the third capture

**24 sightings across 3 channels** (18 in the two named captures, 6 more in `183323`).
No refutation pass; the correction below is this pass's own.

**NOT FOUND in every source.** OpenTyria skips `0x0071/0x0072/0x0073` outright (`0x0070`
`HARD_MODE_UNLOCKED` → `0x0074` `MERCENARY_INFO`); the maintained GWCA has no entry.
`GAME_CMSG 0x0071` exists in the *other* direction and is a different message space.

**SOURCED mechanism**: handler `0x0091E220` → `0x008113D0` (sole caller). Resolves
`[GlobalSingleton+0x2c]+0x574`, a growable `Array<dword>` (count at `+8`, grow `0x00467800`,
shifted insert `0x0046DBB0`), guarded by the two stock `Array.h:986/987` bounds asserts. It
**binary-searches for the value first and early-exits when already present** — an
insert-if-absent into a sorted array, not an append.

**OBSERVED wire position:** every sighting closes a fixed per-entry block —
`0x0056` / `0x0057` (an NPC definition in a *different*, large id space: 3487, 3488) then
`0x009B` name → `0x009F` property 36 (`PublicLevel`) → `0x00A6` profession → **`0x0071`** —
on a small dense id, 1..6.

**REFUTED: "every sighting is a pre-create event for a not-yet-existing agent."** True for
`183756`, where `0x00F0` + `0x0020` follow. **False for `20260817T183323`, where all six ids
1..6 get name, level, profession and `0x0071` and are then NEVER created by `0x0020` at
all** — checked exhaustively, 0 of 6. So `0x0071` closes the *templated setup* block, and the
world create is **optional**, which the proposal's "the last step before create" framing
gets wrong. (Its stronger negative does survive: **0 of 24 sightings occur anywhere near a
`WORLD_REMOVE_AGENT`**, so a post-removal reading is dead.)

**Field 1** is the templated-agent id in that block — small and dense (1..6) because the
instance is fresh, and re-used a second time in `60966` (1..6, then 5,6,2,4,3,1).

**What the sorted `Array<dword>` at `singleton+0x2c+0x574` actually is remains NOT FOUND** —
no symbol or string names it in the reachable disassembly.

---

## `0x00B5` — NOT FOUND, but the subsystem is SOURCED and unexpected

**5 sightings, one per game channel of `183756` and `183323`, ZERO in `180610`.** All five
carry the **identical 50-byte** `array8` payload
(`050066110008c03c000010000004003c000010000004730000760100007712000c0000000000000000000000406000000000`).
No refutation pass.

**SOURCED, and the disambiguation matters.** `msgshape.py 0x00B5`: RECV table `0x00bc8f68`,
handler `0x0091F070`, `[array8[256]]`. `codescan.py --xrefs` confirms an exclusive
single-caller chain at every hop: `0x0091F070` → `0x00813AB0` → `jmp 0x0049BF50`. Reading
the assert inside that worker at the **exact VA** `0x0049BF67` gives the full path
**`P:\Code\Gw\Pref\PrApi.cpp:1431`**, expression `bytes || !data` — the client's own
**Preferences** API. Neighbouring asserts name `PREF_FLAGS`, `PREF_STRINGS`, `PREF_VALUES`,
`PREF_WINDOWS`, `PREF_LOCATION_COUNT`, `PREF_ENUMS`, `s_flags`, `s_windows`, `s_dirtyFlags`,
`s_delay`, `s_flushDelay`. (`asserts.py:203-208` documents `PrApi` as a **known basename
collision** with an unrelated `Engine\Map\Props\PrApi.cpp`; the exact-VA lookup returned the
full path and disambiguates it as the Preferences file. Verified this pass: the string
`P:\Code\Gw\Pref\PrApi.cpp` is present at `0x542598`.)

**So the server pushes a small, session-stable binary blob into the client's
Preferences/Options module** — not into any agent, item or party subsystem. That is a
genuinely surprising place for a `GAME_SMSG` to land and is the finding here. What the
blob contains is **UNVERIFIED**; "restoring saved window layout / option state at area
load" is RECONSTRUCTION.

**NOT FOUND upstream:** OpenTyria has a gap at 181 (112 → 182); the maintained GWCA has no
entry; GWLP-R's `P181_Unknown.java` declares `long unknown1; String unknown2`, which does
not match our `array8[256]`, so it is a build/numbering mismatch of the kind already
documented at `studies/character/FINDINGS.md:719-722` and is **not** treated as a witness.
Prior in-repo fuzzing (`studies/smsgsweep/FINDINGS.md:116`) independently classified this
opcode's crash guard as "a byte buffer" — consistent with, and not evidence for, the
Preferences finding.

`GAME_CMSG 0x00B5` exists with a different shape; independent table, not a reply to this.

---

## `0x00C5` — NOT FOUND, and the best single observation of the pass

**1 sighting**, `183756/60966` idx 2274: `[2, <12-unit EncString>]`. No refutation pass.

**SOURCED**: RECV table `0x00bc8f68`, handler `0x0091F270` → `0x00814030` (sole caller).
Two asserts inside that worker:
**`P:\Code\Gw\Char\Cli\ChCliApi.cpp:2956 "context->accumIntList[0].Count() >= 1"`** and
`P:\Code\Base\rtl\Array.h:587 "index < m_count"`. So this message **cannot be first** in
whatever sequence it belongs to — it requires an integer accumulator to already hold at
least one value. Its sibling `0x0080` (handler `0x0091E750`, body `0x00811740`, same file,
same `Array:587` guard) is already SOURCED at `studies/quests/AUTHORING.md:358` as a text
accumulator that "appends its one string16 into an array, one line per message". Prior
loopback fuzzing (`studies/smsgsweep/FINDINGS.md:116`) independently classified this
opcode's crash guard as "a non-empty accumulator list" — the same assert reached two ways,
which is a real second witness.

**And this pass found what satisfies that precondition, and what the string contains.**
Hex-dumped first-party:

```
#2270  0x0161  item 2241, name = 7D94 B929 ECF7 5FEE
#2271  0x0161  item 2242
#2272  0x0161  item 2243
#2273  0x0084  [2241, 2242, 2243]        <- appends into accumIntList[0]
#2274  0x00C5  2, 7F2C F8BD B9AE 2C6F  010A  7D94 B929 ECF7 5FEE  0001 0101 0103
                  ^--- template ---^   ^sub^ ^-- item 2241's own name --^  ^args^
```

**`0x00C5`'s string is a composed EncString that embeds, verbatim, the name of an item
`0x0161` declared four messages earlier and `0x0084` had just staged.** The assert's
precondition and `0x0084`'s effect are the same fact seen from two sides. No agent found
this, and it is the concrete evidence that `0x0084`'s accumulator really does feed message
composition — which the `0x0084` census (zero drains observed) had made look untestable.

**Fields:** field 1 `u8` = 2, forwarded into the accumulator worker; role **RECONSTRUCTION**
(candidate: a category selector, since the source expression reads `accumIntList[0]`
literally rather than as an indexed access — whether the wire byte *is* that index is
UNVERIFIED). Field 2 = the composed string, described above.

**NOT FOUND upstream:** OpenTyria has a gap at 197 (`0x00C3` → `0x00C6`); the maintained
GWCA has no entry; GWLP-R's `P197_Unknown.java` is filed under **outbound**, the wrong
direction. **n = 1.**

---

## `0x00C3` — the name is UPSTREAM at delta 0, and it is still not earned

**1 sighting**, `183756/58389` idx 1513: `[11, 0]`. The proposal said NOT FOUND; the skeptic
agreed. **This pass revises the reasoning, not the verdict, and the revision is labelled as
this pass's own.**

**The skeptic's rejection rested on a stale mirror.** It ruled the merchant candidate out
because *"GWCA's Opcodes.h:195 assigns `WINDOW_MERCHANT` to `0x00C2`, which under the
independently-confirmed +1 shift would land on our `0x00C3`"* — an inheritance-by-shift
argument, correctly distrusted. **No shift is needed.** The maintained GWCA puts
`GAME_SMSG_WINDOW_MERCHANT` at `0x00C3` directly, and OpenTyria independently puts
`GAME_SMSG_MERCHANT_WINDOW_OPEN` at `0x00C3` directly. **Two independent lineages, delta 0,
agreeing that this opcode opens the merchant window.**

**And the wire is consistent.** The one sighting closes a flow whose owner is an NPC and
whose content is eleven priced items:

```
0x00C4[272] -> 11x 0x0161 (values 25, 20, 50, 50, 50, 250, 1250, 40, 750, 200, 200)
            -> 0x0084[11 ids] -> 0x00CA[1, 1.0f] -> 0x00C3[11, 0]
```

`0x00C3`'s byte field is **11 — the item count**. That may be a coincidence with a window
kind; at n = 1 nothing separates them.

**Why the name is still not earned, and the objection is real.** SOURCED, re-verified: the
handler `0x0091F340`'s worker `0x00813F80` is one of the five `ChCliApi` forwarders
(`0x00C3`, `0x00C7`, `0x00C8`, `0x00C9`, `0x00CA`) that all post the **same** UI message
`0x100000B5`. Its 4-dword payload is `{wire byte, wire dword, global 0x010876C8, global
0x010876CC}`, and the second global is zeroed immediately after — the consume-and-clear of
`0x00C4`'s owner register. **There is no pricing, trade or merchant-related call or assert
anywhere in the chain.** `studies/smsgsweep/FINDINGS.md` §7.7-7.9 already traced
`0x100000B5` to a 90-message registrar bound to `GmView` and to a **runtime-built**
subscriber list that cannot be read statically, and concluded the five cannot be told apart
from the image.

**Record:** name `MERCHANT_WINDOW_OPEN` / `WINDOW_MERCHANT` = **UPSTREAM**, two lineages,
delta 0; our own wire context is **consistent** but not decisive; the client contributes
**nothing** that distinguishes this opcode from its four siblings. That is
`studies/smsg/FINDINGS.md`'s PARTIAL — mechanism understood, name not earned — and it
should not go into `overrides.json` on this evidence.

---

## `0x00CA` — NOT FOUND, deliberately, following prior art's own refusal

**1 sighting**, `183756/58389` idx 1512: `(byte = 1, dword = 1065353216 = 1.0f)`.

**SOURCED**: handler `0x0091F340`… — no, handler `0x0091F340` is `0x00CA`'s: it reads field 2
with an **FPU load** (`fld dword ptr [msg+8]`), so the client itself treats that dword as a
**float**. It forwards to `0x00814270`, which builds a 7-dword struct
`{field1; global 0x010876C8; global 0x010876CC; the float; 0; [ctx+0x2C]; [ctx+0x24]}` and
posts UI message `0x100000B5`.

**This reproduces, address-for-address, the cluster `studies/smsgsweep/FINDINGS.md` §7.7
already documented** — `0x00CA` is the fifth and last of the five forwarders
(`0x00813F80`–`0x00814270`), all rendering an on-screen result the operator could not tell
apart. That document explicitly and deliberately left all five UNNAMED: *"Naming them needs
the CONSUMER of UI message 0x100000B5 … not another client run."*

**Honouring that refusal rather than overriding it on one field-value sample is the right
call, and is why this is NOT FOUND rather than a name.** A real payload does not supply the
consumer-side read that document says is required, and inventing a distinguishing name for
`0x00CA` alone while its four siblings stayed unnamed would assert a distinction the
evidence does not support. **NOT FOUND in both upstream lineages** (OpenTyria gap at 202;
maintained GWCA no entry).

The one thing this pass adds: the two private globals `0x010876C8`/`0x010876CC` are now
**identified** — they are `0x00C4`'s owner register (above), which was not known when §7.7
was written. That is one of the three unknowns in that section's payload closed.

---

## `0x002F` — `AGENT_UPDATE_ALLEGIANCE` — **CONTESTED**

**2 sightings**, `(15, 'play')` and `(17, 'play')`, immediately after the two `0x00AA`
sightings for the same agents in the same order. No refutation pass; treat accordingly.

**This is the one row where upstream and our own client genuinely disagree, and neither side
is dismissible.**

| side | claim | label |
|---|---|---|
| **upstream** | `0x002F` is `AGENT_UPDATE_ALLEGIANCE` | **UPSTREAM**, two independent lineages (ldufr, maintained GWCA) at delta 0 |
| **our client** | its handler `0x005FDD70` passes field 2 to a setter `0x00602E20` that writes `[esi+0xE8]` — **nowhere near** the `+0x1B1`/`+0x1B5` allegiance byte, and sending it changed nothing observable | **SOURCED** + **OBSERVED**, `studies/enemy/PLAN.md:949-966` and `:1860-1868` |

**The SOURCED mechanism, reproduced independently this pass.** Field 1 is a bounds-checked
index into **two** parallel per-agent arrays at `[ctx+0xE8]` (bound `+0xF0`) and
`[ctx+0x14C]` (bound `+0x154`); the client's own asserts name them **`syncPtr` at
`AgMsg.cpp:655`** and **`asyncPtr` at `AgMsg.cpp:660`**, both firing if the entry is
missing. Field 2 is stamped verbatim into `+0xE8` of **both** the sync and async per-agent
message-channel records. Matching `studies/smsgsweep/FINDINGS.md:70,113`'s crash-census
classification of `0x002F` as touching "a sync/session handle".

**What this pass adds, and it strengthens the upstream side without settling it.** Both
target agents were created carrying `'nonc'` and are named by `0x00AA` then `0x002F` carrying
`'play'` (see `0x00AA` above). So the message *is* sent as an allegiance change, on retail,
by ArenaNet's own server — **and our probe tested only half of the mechanism.** Retail sends
`0x00AA` first. `studies/enemy/PLAN.md`'s "sending it changed nothing" was measured on
`0x002F` alone.

**That is the experiment that would resolve this, and it is cheap.** Nothing in either side
is refuted yet, so the label stays CONTESTED and the name does not ship.

**Open:** what `+0xE8` on the AgMsg sync/async record is read for (no consumer traced);
whether `0x002F` ever fires with a non-`'play'` value — no enemy-side token has ever been
seen in this field.

---

# 3. What the refutation pass changed

Fifteen proposals were refuted or downgraded. The pattern is worth naming because it
repeated:

| opcode | proposed | after refutation | what went wrong |
|---|---|---|---|
| `0x011A` | `GUILD_LADDER_ENTRY` | **`TOWN_ALLIANCE_OBJECT`** | four of six field readings contradicted; the assert evidence was a `--span 2000` windowing artefact naming other opcodes' handlers |
| `0x011B` | `GUILD_LADDER_LIST_END` | role only, **both fields NOT FOUND** | one field reading contradicted by the client counting it itself; the constancy argument was one witness counted six times |
| `0x00B9` | `CLIENT_NOTICE_QUEUE_ADD` | **`MISSION_INFOBOX_ADD`** | the opcode had already been **seen on screen** in this repo, twice, one of them a calibration fixture in the suite |
| `0x00BB` | `HELP_GUIDE_TIP_ADD` | **`MISSION_OBJECTIVE_ADD`** | the "closest subscriber" method has a false positive 24 bytes away that would rename `QUEST_ADD` the same thing; the name was in five mirrors, unread |
| `0x005F` | CORROBORATED | **UPSTREAM, single lineage** | our schema *is* OpenTyria; "schema agrees with OpenTyria" is one witness twice |
| `0x009E` | CORROBORATED | **UPSTREAM name / CORROBORATED layout** | rested on an operator note superseded four days earlier by a measured re-run in the same repo |
| `0x00C4` | `MERCHANT_WINDOW_UPDATE_OWNER` | **`WINDOW_OWNER`** | one lineage, contradicted by the rival lineage, by that lineage's **own implementation**, and by our client's eight-reader register |
| `0x0084` | CORROBORATED | **RECONSTRUCTION** | `0x00D7` shares the identical handler VA, so the binary makes no "items" distinction |
| `0x003A` | CORROBORATED | **split label; one behavioural claim struck** | n = 1 presented as n = 4; a circular citation of our own server; "every instance load" false against a capture never opened |
| `0x005C` | CORROBORATED gate | **SOURCED gate, corrected** | read a truncated listing; the stated gate would have made both sightings no-ops |
| `0x00AA` | `AGENT_JOIN_ALLEGIANCE_GROUP` | **NOT FOUND**; upstream `AGENT_CREATE_NPC` refuted | field 3 is the model id, not an opaque handle |
| `0x00F5`, `0x00F6`, `0x017E`, `0x0180` | names correct | **names stand, reasoning replaced** | all four leaned on a `+1` shift against a stale mirror; all four gained a first-party client witness the proposals missed |

**Three lessons that are cheaper to write down than to rediscover:**

1. **`asserts.py --at` defaults to `--span 2000`.** That window covers ~18 handlers. Bound
   the span to the actual function, or the tool will hand you a neighbour's asserts and they
   will look decisive. It bit two proposals in this pass.
2. **Search this repo's own prior work before the mirrors.** `0x00B9` had been read off a
   screenshot; `0x009E`'s note had been corrected; `0x005C`'s gate had been flagged as
   unsettled with the exact test named. Three proposals asserted things their own repo
   already answered.
3. **Handler-address adjacency proves nothing.** The dispatch table is indexed by opcode;
   contiguous stubs are the compiler, not a family.

---

# 4. What to do next, cheapest first

1. **Fix the mirror, not the arguments.** `vault/mirrors/GregLando113__GWCA` and
   `JaborGW__GWCA` are archived copies; `gwdevhub__GWToolboxpp/Dependencies/GWCA` is the
   maintained one and is +1 on 186 of 217 `GAME_SMSG` names above `0x003E`. **Zero cost:**
   a note at the top of the two archived files, or a line in `PLAN.md` §6.1's derivation
   register, saves the next five sessions from re-deriving a shift that does not exist.
2. **Record `0x006F`'s result into `studies/character/FINDINGS.md`.** The CONTESTED
   nine-position ordering is settled for build 38833: **permuted** (Body 2, Boots 3, Legs 4,
   Gloves 5, Head 6), from retail's own `(item_type, slot)` pairs against a two-lineage type
   enum. That section currently says no screenshot will ever settle it; a capture did.
   **Zero client cost.**
3. **Correct `studies/heroes/FINDINGS.md` §22 and `studies/pvpui/FINDINGS.md:582-584`.**
   `ctx[0x44][0x2ac]` is a **client-side player number**, not the player's agent id — this
   capture separates them (playerId = 1, agent = 27), which is the exact test
   heroes §21.2 said was needed. **Zero cost**, and both documents are currently wrong in a
   way that another opcode's reading was built on.
4. **Add the eight defensible names to `schema/overrides.json` with their `why` text.**
   `0x011A`, `0x00B9`, `0x00BB`, `0x00C4`, `0x00F5`, `0x00F6`, `0x017E`, `0x0180`. Leave
   `0x0084`, `0x005F`, `0x009E`, `0x003A` at medium with the label splits above, and put
   **nothing** in for the eight NOT FOUND. Each entry needs a `test_smsgnames.py`-style wire
   invariant that could go red.
5. **One loopback run settles `0x002F`, and it is the only CONTESTED row.**
   Send `0x00AA(agent, 'play', model)` **then** `0x002F(agent, 'play')` against our own
   server, on an agent created with `'nonc'`. `studies/enemy/PLAN.md` tested `0x002F` alone,
   and retail never sends it alone. Hand-driven, no aiming, fixed-position readout.
6. **One loopback run resolves `0x00B9`'s flag.** Re-run the existing smsgsweep
   `--encstring --only 0x00B9` apparatus with field2 = 1 against the already-proven
   field2 = 0, `--shots 2`. Same instrument that named three of the four in that table; it
   is already built.
7. **One loopback run separates `0x0084` from `0x00D7`.** Send `0x0084` with N ids then
   `0x0086`; separately `0x00D7` then `0x00E1`; see which UI surface receives each. That
   separates the two appenders the binary cannot.
8. **One capture more than three hours after `20260817T183756` confirms `0x011A`.** GWW's
   border recomputes on a three-hour cadence, so a later capture is the only thing that can
   watch fields 3 and 4 move and turn two RECONSTRUCTIONs into OBSERVED. It costs a login,
   not an experiment.
9. **A second character is the highest-value capture available.** `0x003A` has **one
   distinct payload** in the entire corpus, `0x00F6` has one title track, `0x009E` has one
   speaker, `0x00C5` and `0x00CA` and `0x00C3` have n = 1. Almost every UNVERIFIED in this
   document says "zero variance". A different profession at a different title state would
   move six rows at once — and `studies/smsg/FINDINGS.md:58` named exactly this as the
   cheapest open test **ten days ago**.
10. **Two things this document deliberately did not do, so nobody assumes they were
    covered.** No client was launched (read-only pass), so no on-screen verdict exists for
    any of the twenty-two. And the c2s side of these captures **does not decode** —
    `decode_stream("GAME_CMSG", …)` fails at offset 0 on every channel, and the files carry
    one aggregated blob per direction with no per-frame timestamps. That blocks every
    request/response and timing argument in the pass, and fixing the c2s framing would be
    worth more than any single name above.
