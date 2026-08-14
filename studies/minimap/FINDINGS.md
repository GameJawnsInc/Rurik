# The minimap — compass, mission map, world map: where the picture comes from, what the wire carries, and what an authored map gets for free

**Study arc:** `studies/minimap/` · **Date:** 2026-08-14 · **Method:** four recon sweeps (repo knowledge inventory; schema + capture opcode census; client string/assert recon; GWW behaviour checklist) and three deep dives (render data source; opcode frame-bus join; custom-map gap + ladder), each reading the pinned client statically and the live capture corpus, then this synthesis over all seven. No client, game, or server was launched for any input. `C:\gw` was read-only or untouched throughout.

**Client image on every static claim below:** `vault/client/2026-07-29_221c13772c7a/Gw.exe`, **build 38797**, the pinned pristine copy (`toolkit/clientscan/pinned.find()`). Every VA is that image's. **Capture corpus on every wire claim:** the complete live corpus — 3 game-bearing stamped directories (`20260807T133758`, `20260807T143055`, `20260810T235916`), 11 game connections, **22,524 s2c GAME_SMSG and 971 c2s GAME_CMSG**, `frame_report` residual 0 on all 22 connection/direction pairs. The 22,524 equals CLAUDE.md's own figure for the whole live corpus, so this is the full corpus and not a sample. "Ours" counts are from `vault/captures/gamesrv/` + `authsrv/` (1,512 `.jsonl`); `harness/`, `selftest/`, `portal*/`, `raw/` were not scanned and are a stated gap.

---

## 0. The result, and the question it serves

**Custom maps need a working minimap, and this dive was to find out what an authored map already gets and what it cannot get.** The answer is sharp and mostly negative:

**The compass, the mission map (U key), and the world map (M key) are three views of ONE per-continent picture that lives entirely in the client's archive, and a map file contributes nothing to it.** — OBSERVED (static, build 38797; §3). The ground image under the dots is a per-continent atlas of 512×512 ATEX tiles compiled into the client, cropped to the area's footprint rectangle. An authored map served at a borrowed area slot shows a crop of *that continent's* art scaled over our terrain — which is the mechanism behind the customarea arc's "featureless brown disc" sighting (§6). Nothing our server sends can supply the drawn art.

What an authored map *does* get for free is the layer that rides the wire: **agent dots on the compass work today, on our own server** (OBSERVED; §5.1). What it lacks is everything drawn from the archive (ground art, fog, location pins) and everything behind an unbuilt or unsent opcode (quest markers, ping/draw echo).

**The single most useful lever this dive found:** the map-type byte our server already sends in GAME_SMSG `0x0199` selects which of the area row's two footprint rectangles the compass crops with (§3.3) — so we hold a real lever on the compass, even though we cannot yet make it show *our* terrain.

**The single most important protocol finding:** the compass draw/ping is a matched opcode pair, and both ends are named by the client's own asserts — **GAME_CMSG `0x002B` (client→server draw) and GAME_SMSG `0x0091` (server→client broadcast)** — and our server drops `0x002B` silently with no dispatch arm and no allowlist row (§4.1, §5.2). This corrects the recon-stage reading that the c2s draw opcode was NOT FOUND: it was unnamed, not absent.

---

## 1. The three surfaces and the player-facing checklist

Source for this section is GWW (the official Guild Wars wiki, `wiki.guildwars.com`), labelled **WIKI** per this repo's vocabulary (`studies/character/FINDINGS.md`): strong for player-visible values, explicitly weak for internals. Revision ids given because staleness is the failure mode.

### 1.1 The compass (round minimap / "radar")

`Compass` and `Radar` both redirect to `User interface#Compass` — one section is all GWW has. WIKI (GWW, "User interface" §Compass, rev2734525, 2026-07-15):

- Shows allies and foes near the player; always centred on the player; shows cardinal directions. No distinct "self" marker is named — self is implied by centring. **NOT FOUND: a named self icon.**
- Dot key: foes = **red circle**; allies (party/heroes/henchmen/NPC allies) = **green circle**; allied minion/pet/spirit = **green triangle**; neutral minion = **gray circle**; other players in town partied = **dark blue**, open-to-invite = **light blue**.
- Quest marker: if a quest is selected in the log, the objective shows as a **green starburst** in range, a **green arrow** at the compass edge out of range.
- Hero flags: a group flag + up to 3 individual + a cancel, sitting below the compass; click a flag then click the compass/mission map/terrain to order movement (WIKI, "Hero flag", rev2658857).
- The only non-dot visual element is the **Danger Zone** (aggro bubble): a white translucent circle, radius **1012 gwinches**, "the only visual range cue on the radar" (WIKI, "Danger Zone", rev2647572; radius cross-corroborated on "Range" rev2720855 and "Area of effect" rev2685457). Some named creatures (Siege Wurms, Siege Turtles, Kournan Spotters) have a larger *true* aggro range than the drawn circle.
- **NOT FOUND: any wiki text that the compass renders terrain, walls, elevation, or fog.** One ambiguous dungeon anomaly note (The Mausoleum, rev2667968) is the only near-signal and is labelled UNVERIFIED. The positive statement "only visual range cue" reads as GWW confirming nothing else is drawn.

**Correction to a repo premise (recon 4):** the widely-cited **5,020 gwinch** figure is *party/object-visibility* range, ~12% *larger* than the drawn compass circle — **not** the compass's drawn radius. The back-calculated drawn radius is ≈4,482 gwinches (RECONSTRUCTION, from "about 12% larger"; no exact wiki number exists). The circle actually drawn is the 1012-gwinch Danger Zone. If `studies/monsterai/FINDINGS.md:763` or anywhere treats 5,020 as the compass's drawn radius, that is the fix.

### 1.2 Pinging and drawing

WIKI, "Ping" (rev2646868): a ping is a coloured ripple circle — **red** = a team player clicks the compass or calls a target (some enemies auto-ping red on specific attacks); **yellow** = mission/quest auto-flag; **blue** = a mission-critical bundle on the ground. Pings are party-visible and anonymous to viewers; heroes/henchmen ignore all pings except called targets. Called-target behaviour: WIKI, "Priority target" (rev2659030) — calling auto-pings the foe red, sets a party-window icon (bright red current / dark red prior), acquirable party-wide by the 'T' key.

**NOT FOUND: drawing (drag) documented as distinct from pinging (click).** GWW names the gesture once ("pinged or drawn on … by clicking or dragging") and never elaborates on colour, persistence, or a separate mechanic. **NOT FOUND: any ping/draw duration or rate limit anywhere on GWW** — see §4.1 for the number, read out of the binary instead.

### 1.3 The mission map (U key)

WIKI, "Mission Map" (rev2678351): the path travelled shown as red breadcrumb dots; resizable, scroll-zoomable; a full icon key (resurrection shrines, collectors, player location+direction, hero flags, portals, dungeon bosses/exits, keys, capture points, PvP bases). Trail resets on disconnect. Exploration/fog is the Cartographer system (WIKI, "Cartographer", rev2735483): title tiers at 60/70/80/90/95/100% per continent, "scraped" by pushing against area edges. Exploration is a **character** attribute (CORROBORATED by strong implication — titles live on the character; some dungeons reset exploration on exit). **NOT FOUND: an explicit statement of storage granularity** — that is a save-format question GWW cannot answer.

### 1.4 The world map (M key)

WIKI, "World Map" (rev2641098): a full-screen continent view; visited outposts shown as travel-able icons; player as a green crosshair; the same red breadcrumb trail at local zoom. "The green current location marker is approximately as large as the danger zone marker in the compass" — a direct scale cross-reference. PvP/guild-hall areas are absent from the world map but appear "fully explored" on the mission map. Map travel is party-wide with a ~10 s warn-and-object delay and per-destination party-size caps (WIKI, "Map travel", rev2675235). **OBSERVED counterpart:** opening the map produces zero network traffic (§5.3).

### 1.5 Observer mode / PvP

WIKI, "Observer mode" (rev2440424): observers get the **mission map** overlay ('u'), never a documented compass. **NOT FOUND: any wiki statement on the compass in observer mode or general PvP arenas, or on enemy-dot hiding.** The only PvP→compass facts GWW documents are two transitional recolourings (a PvP spirit about to die and a PvP minion about to go masterless both flip to green triangle briefly). This is a confirmed documentation gap, not a search failure.

---

## 2. The client's module structure for this subsystem

All directory/assert facts are SOURCED (the client's own `__FILE__` path strings and assert expression text, quoted single-assert-as-evidence per `PLAN.md` §7 Q3) unless a reading is marked otherwise. Counts come from `toolkit/clientscan/asserts.py` keyed on **full source paths**, never basenames (the `test_codescan.py` §8/§9 collision lesson). `asserts.py` is a documented **floor**: it reads 19,758 sites against an independent 20,131 `call rel32`-to-assert-routine sweep — **370 short** — so "0 sites" for a file is never proof it has no asserts.

### 2.1 The directories

| Directory | Files (≥1 assert / total) | Sites | VA span |
|---|---|---|---|
| `P:\Code\Gw\Ui\Game\Compass\` | 7 / 9 | 28 | `0x008bbe15..0x008c57c1` |
| `P:\Code\Gw\Ui\Game\Map\` | 7 / 7 | 79 | `0x005468be..0x0055a636` |
| `P:\Code\Gw\Mission\Cli\` | 6 / 10 | 35 | `0x0084d9fa..0x00854e3e` |
| `P:\Code\Gw\Mission\` (non-Cli) | 1 / 2 | 5 | `MsnTeam` @ `0x009280bf..0x00928375` |
| `P:\Code\Gw\Const\` (WorldMap + Mission rows only) | 2 / 2 | 14 | `0x005a855e..0x005a9600` |

Substring-widening caveat (per the `test_codescan.py` §9 warning): pass the exact prefix, never the bare word. `--in Const` bare pulls 36 files; `--in Map` bare pulls the whole `Engine\Map\*` server/geometry tree; `Compass` bare happens to be safe on this build but is not guaranteed. Use `P:\Code\Gw\Ui\Game\Compass\`, `P:\Code\Gw\Ui\Game\Map\`, `P:\Code\Gw\Mission\Cli\`, and the exact files `ConstWorldMap.cpp` / `ConstMission.cpp`.

### 2.2 Naming corrections that matter to the studies

- The client uses **`MsCli`** for the mission-client directory (10 files under `Mission\Cli\`), not the `Msn`/`MsnMap` the task brief hypothesized. `Msn` prefixes only two files (`MsnTeam.cpp`, `MsnScore.cpp`) sitting *outside* `Cli\`, ~890 KB away in `.text`. — SOURCED.
- **No `Pt*`/`Ctl*` class name for the compass or map exists** anywhere in image or repo (`PtMap`/`PtCompass`/`PtWorldMap`/`CtlMap` all return zero). The real names are the source files: `Compass.cpp`, `CompassCanvas.cpp`, `CompassMap.cpp`, `GmMapWindow.cpp`, `GmMapWorld.cpp`, `GmMapCtlLocationTag.cpp`. — NOT FOUND, confirmed by grep.
- The client's UTF-16 UI-element tables separate the two widgets: **`MapWindow`** at `0x0094CB18` (with `Inventory`, `Quest`, `PartySearch`, `SelectMission`) is the U-key window; **`Compass`** at `0x0094DB1C` (with `LevelProgress`, `MissionProgress`, `SkillBar`, `WeaponBar`) is the HUD element. Two lists, two widgets. — OBSERVED.
- `MissionMap`/`mission map`/`radar`/`MsnMap`/`worldmap`/`cartograph`/`minimap` (lowercase) as strings: **NOT FOUND** in the image (both ASCII and UTF-16LE). The one `minimap` hit is the ALL-CAPS `CHAR_MAX_DRAW_MINIMAP_KNOT_COUNT` (§4.1) and one debug string (§3.4). `MISSION_MAP_*` exists only as an *enum-value prefix* (`MISSION_MAP_GAME`, 12 assert sites), never a file or class.

### 2.3 The structurally-invisible files, located

Seven files in this subsystem carry zero asserts `asserts.py` can see. Deep dive A located all of them — including the two the monster-AI arc left as a blind spot — by scanning `.text` for the 4-byte pointer to each file's `__FILE__` string, which finds tagged-allocation sites the assert scanner misses:

- **`CompassAIControl.cpp`** ≈ `[0x008BD240, 0x008BE700)`, `__FILE__` pushed at `0x008BD250`. Its external calls (`FrApi`×20, `ChCliApi`×7, `TextApi`, `GmChat`) plus `Compass:222 aiFlag < AI_COMMAND_FLAGS` (`0x008bbe15`) and `CompassInt:49 commandFlag < AI_COMMAND_FLAGS` (`0x008bd1a0`) identify it as the **hero/henchman command-flag widget under the compass** — confirmed from its code, not just its path. Nothing to do with monster AI. This closes the standing blind spot at `studies/monsterai/FINDINGS.md:46,96`. — OBSERVED / RECONSTRUCTION (the widget reading).
- **`CompassModel.cpp`** ≈ `[0x008C1780, 0x008C1CC0)`, a pure render helper (`GrTrans`×12, `grint`×7). — OBSERVED (located); purpose RECONSTRUCTION.
- `MsCliClock.cpp`, `MsCliFeat.cpp`, `MsCliConfig.cpp`, `MsCliObserve.cpp`, `MsnScore.cpp` — located, not read. "Zero sites" is the tool's floor, not a census.

---

## 3. Where the compass picture actually comes from — the render data source

**Headline: the hypothesis that the compass renders the compiled pathing map is REFUTED.** — OBSERVED (static). Deep dive A did an exhaustive direct-`call rel32` sweep out of the whole compass group `[0x008BB100, 0x008C5890)` (all nine translation units): **zero** calls into `Engine\Map\Path\*`, `Props\*`, `Sight\*`, `Zones\*`. A whole-image cross-check found **319** sites calling the Path spatial library and **not one is in any `Gw\Ui\` module**. The one apparent Terrain hit (`0x00742F90`) is an `Array<T>` grow helper reached from 15 callers across 5 modules — a measured false positive of by-address labelling, reported not swallowed. (Caveat: the sweep is exhaustive for *direct* calls only; an indirect vtable/function-pointer call would be invisible — §7.)

### 3.1 The chain, measured end to end

The compass ground image is a per-**continent** atlas of 512×512 ATEX tiles compiled into the client, cropped by the area's footprint rect. Deep dives A and C independently traced it; where they overlap they agree.

| step | evidence | label |
|---|---|---|
| `WORLDS = 10` | `0x005A93E9 cmp edi,0xa` guarding `ConstWorldMap:1313 world < WORLDS` @ `0x005a93f3` | OBSERVED |
| `s_worldData` base **VA `0x00A36210`**, **stride 48**, **10 records** | accessor `0x005A93B0`: `lea eax,[esi+esi*2]; shl eax,4` = ×48 at `0x005A93CD`, `add eax, 0xa36210` at `0x005A93D3` | OBSERVED — **correction LANDED 2026-08-14** (rung S1) in `toolkit/clientscan/consttable.py`, which carried `stride=24, "UNSETTLED"` and printed `20 × 24`. 24 is still in its own rival-stride list, and that is the doctrine working: every divisor of 48 closes on the same base |
| **the count is ArenaNet's own `arrsize`, not our division** | the accessor guards ITSELF: `0x005A93B7 cmp esi,0xa` → `index < arrsize(s_worldData)` @ `ConstWorld.cpp:41` | OBSERVED — found on S1's re-verification. This row's first draft derived 10 as `480 B / 48` and cited `ConstWorldMap:1313` for `WORLDS`, which is a **different translation unit and a different function** (the chunk-tile getter at `0x005A93E0`). Both bound at 10, so the two corroborate — but the table's own bound is the direct witness, and it names the symbol |
| the `__FILE__` that assert needs **IS** `consttable`'s anchor for this row | the string at VA `0x00A363F0` is `P:\Code\Gw\Const\ConstWorld.cpp`, and `0x00A36210 + 10 × 48 = 0x00A363F0` | OBSERVED — so the assert and the table close on the same byte from two independent directions |
| the 48-byte record is refutable from CONTENTS, which the closure is not | `+0x14` is `512` on all ten 48-byte records and ragged (`512, 960, 1280, 1440, 3072, 4608, 9216`) on the twenty 24-byte ones; 512 is `CONST_WORLD_CHUNK_SIZE` | OBSERVED — a stated limit of `consttable.rival_strides`, which tests closure and the index column and never column coherence |
| `chunkCX`@+0x04, `chunkCY`@+0x08; `parchmentCX`@+0x0C, `parchmentCY`@+0x10 | bounds asserts `ConstWorldMap:1316/1317` and `:1338/1339` | OBSERVED |
| `satelliteCX/CY` (asserts `:1360/1361`) offsets ≈ +0x18/+0x1C | third getter not disassembled | UNVERIFIED |
| a **7×12-byte** table @ VA **`0x00A37390`** = `{u32 count, u32 *array, u32 world}`, linear-searched on world | `0x005A9450 mov esi,0xa37390 … cmp eax,0x54` (0x54=7×12) | OBSERVED |
| **`count == chunkCX × chunkCY` on 7 of 7 worlds** (512,32,192,32,192,32,128) | both sides read independently | OBSERVED — this is what makes "grid of tiles" a measurement, not a story |
| worlds 7, 8, 9 have **no record** in the table (accessor returns 0) | table walk | OBSERVED |
| parchment tier has its own identical table @ VA **`0x00A373E8`** | same 0x54 loop | OBSERVED |
| tile index = `chunk.y*chunkCX + chunk.x`, bounded by `ConstWorldMap:1325 offset < files.count` @ `0x005a9480` | `imul edi,[edx+4]; add edi,[ebx]; cmp edi,[esi]` | OBSERVED |
| array slot is a pointer (NULL where no tile) to an 8-byte `{u16 id0, u16 id1, u32 0}`; trailing u32 = 0 on 409/409 | `File.cpp` pair form, same as RESKIN §22 glyph sheet | OBSERVED |
| **409 tiles over 7 worlds; `mapchunks.dependency_file_id` resolves 401/409, all 401 decompress to magic `ATEX`** — identically on both vaulted archives (`dat_study` 177,342 rows; `client/2026-04-30_b174de1f2d8d` 177,311 rows); 8 unresolved on both (ids 387674/387678/387680/387682/387684/388093/388095/388097) | ~39.9 MB stored total | OBSERVED |
| tiles are 512×512 ATEX | `atex.parse` on 4 world-1 tiles (rows 44714-44717): all 512×512 | OBSERVED, **sampled (n=4 of 401)** |
| `CONST_WORLD_CHUNK_SIZE = 0x200 = 512` | `0x008C202D cmp [edi],0x200` / `0x008C2035 cmp [edi+4],0x200` guarding `CompassMap:472 m_imageDims == CONST_WORLD_CHUNK_SIZE` @ `0x008c2043` | OBSERVED |

### 3.2 One atlas, three views

`codescan --xrefs 0x005A93E0` (the chunk-tile getter) has **exactly two direct callers**: `0x005531BD` inside `GmMapView.cpp` (the mission map / world map view) and `0x008C200A` inside `CompassMap.cpp` (the compass). — OBSERVED. So compass, mission map and world map are three crops of one per-continent picture, and a map file contributes nothing to any of them. `GmMapView` additionally uses all three texture tiers (chunk/parchment/satellite); the compass uses only the chunk tier.

### 3.3 THE LEVER: `0x0199`'s map-type byte selects the footprint the compass crops

At `0x008C2761` the compass reads `s_missionClientData[map]` (accessor `0x005A8580`), calls `MissionCliGetMap()` (`0x0084D9B0`), and branches:

```
008C2770  test eax, eax
008C2772  jne  0x8c277c
008C2774  mov  eax,[esi+0x48] ; FOOTPRINT_A.x0        (map == 0)
008C277C  mov  eax,[esi+0x58] ; FOOTPRINT_B.x0        (map != 0)
```

`+0x48` / `+0x58` are `maprows.FOOTPRINT_A` / `FOOTPRINT_B` (`toolkit/clientscan/maprows.py:83-88`), whose comment reads "nothing yet says which one the client prefers" and which `studies/maprows/FINDINGS.md:484-485` §9 item 4 records as open. **This answers §9 item 4: both, and the selector is `MissionCliGetMap()` — the value the `0x0199` handler writes into `missionContext+0x238` from the map-type byte our own server sends.** — OBSERVED (static; both deep dives A and C reached this independently). `MISSION_MAP_GAME == 1` (`MsCliApi:251 context->map == MISSION_MAP_GAME`, compiled `cmp [esi+0x238],1` @ `0x0084D9EC`). `MISSION_MAP_OUTPOST` exists (`QuestLog:261`) but its numeric value is **NOT FOUND**.

Wire correction (recon 2, both deep dives): the map-type value is a **`byte` at field index 3** of `0x0199` (`schema/messages.json` opcode 409 = `[msg_header, agent_id, word, byte, dword, byte, byte]`), *not* a "third dword". RESKIN.md's "dword" is the 4-byte in-memory slot at `missionContext+0x238`, not the wire width.

Under our server today the byte is always effectively A-selecting for authored maps: `authsrv.py:4110` sends `1 if (EXPLORABLE or map_explorable) else 0`, and `content/maps.toml:170` gives map 143 `explorable = false`, so `MissionCliGetMap()` reads 0 → FOOTPRINT_A (`studies/profession/RUNS.md:1096-1097`, OBSERVED on a live run). **172 of 888 rows have A ≠ B** (`maprows.py`); map 143 is not one of them (A == B), which is why the lever needs a different slot to demonstrate (PLAN rung C3).

### 3.4 The loader, and ArenaNet's own word for it

`CompassMap.cpp`'s image loader at `0x008C21C0` logs the string at `0x00BA04B4`: **"Converting world minimap texture to DXT1.\n"** and forces GR format 15 (DXT1). — SOURCED. So `minimap` is ArenaNet's own word for this texture, and the compass's various `(rect & 3)==0` asserts (`CompassMap:288-291/381-384`) are DXT-block alignment guards. When the image is NULL the code does not clear to a colour — it **tiles** a fallback surface (`0x008C1E00`, `CompassMap:164 (int)rect.x1-(int)rect.x0 > 0`), which is the mechanism behind a "featureless" compass.

### 3.5 The per-area override, and the marker fog grid

- **`s_missionClientData[map].+0x68` is a per-area compass texture** (an archive file id → ATEX), read at `0x008C3129 cmp [eax+0x68],0` under `test ebx,0x40000`; when set (branch at `0x008C2518`) the compass loads that texture instead of the continent crop. **157 of 888 rows are non-zero; all 157 resolve to ATEX** (corroborating `studies/areatable/FINDINGS.md:110-124` from the code side). — OBSERVED. **None of the ten map ids in `content/maps.toml` has `+0x68` set** (143/144/146/148/449/194 all zero), so every map this project has pointed a client at takes the continent-crop fallback.
- **Compass marker visibility is gated by a per-character bit grid** (`CompassMarker.cpp` `0x008C2EC0`): world coords → `/96.0` (cell pitch, verified double at `0x0094DE10`) → `×0.03125` (verified double at `0x00949CB0`) → index into `char+0x5A4` (an `Array<dword>` bitfield), dims at `char+0x5B4`. `CompassMarker:98 blockPos.x < mapDims.x && blockPos.y < mapDims.y`. — OBSERVED. That the block pitch is therefore 32 terrain cells is RECONSTRUCTION (the `/96` is solid; the `×1/32` is read off the x87 sequence). `GmMapView` sizes the map texture at 4× that grid (`GmMapView:1731 worldMapDims.x == mapDims.x * DXT_BLOCK_SIZE`) and reveals in whole DXT blocks — this is the unfogging painter.

### 3.6 Agent dots — the layer that works (OBSERVED, on our server)

The compass draws dots from the client's own AgentView agent list — the same list `WORLD_CREATE_AGENT` and the position stream feed (8 distinct `AvApi.cpp` entry points called from the compass group; `0x007E0E20` copies a vec3 out of an agent record). Party/self identity from `ChCliApi.cpp` (26 call sites). Nothing about agent rendering comes from `Engine\Map`. — OBSERVED. Player-class agents already render as light-blue nameplates *and* light-blue compass dots on our server regardless of allegiance FourCC (`studies/enemy/PLAN.md:381-384`, probe `allegiance`, 2026-08-06, build 38797).

---

## 4. The opcodes

Method (deep dive B): the client's receive handlers do not call UI code directly — they **post a frame message** (`FrApi` post `0x00633D70`, 864 sites) that a UI module **subscribes** to (`FrApi` subscribe `0x00633BD0`, 466 distinct msgIds), each subscription attributed by the client's own `__FILE__` push. So `opcode → handler → post → msgId → subscribe → module`, two halves read independently. Send side: `SendMessage 0x007DCF00`, 174 direct call sites, recovers each c2s opcode immediate. (Method caveat: the walk is direct-`call`/`jmp` only, depth-bounded; a module that *polls* rather than subscribes is invisible — which is exactly why an event-bus sweep cannot see `0x0199` feeding the map type, §5.)

### 4.1 The compass draw/ping pair — both ends named by the client

**GAME_CMSG `0x002B` = COMPASS_DRAW (client→server).** — CORROBORATED (binary chain + 1 live packet). This is the answer to "is the c2s draw opcode absent" — **it is not; it was unnamed.** `CompassCanvas.cpp @0x008C08DC` → thunk `0x00816110` (1 direct caller image-wide, 0 raw-dword occurrences → in no vtable) → wrapper `0x00920230` which writes opcode `0x2b` and asserts `CharMsg:8129 knotCount <= arrsize(message.knotData)` @ `0x00920262` (bound 16). CompassCanvas is the **sole producer image-wide**. Layout (`schema/messages.json`, no override): `msg_header | dword | array32[16]`. Knots packed low-half-first, read off the wrapper's own loop. Live: **1 occurrence**, `20260807T143055` t=50.70 s, `[32811, 7, [3801175]]` (0x802B masked; one knot `0x003A0057` → 87, 58). A single knot is a click; a run is a drag.

**A rate limiter and knot accumulator sit at the send site** (`0x008C08B8`): the client accumulates knots and flushes on a **250-unit countdown**, sending nothing when empty. This is the ping/draw rate limit GWW documents nowhere (§1.2), read out of the binary. — OBSERVED; the unit (ms?) is UNVERIFIED.

**GAME_SMSG `0x0091` = COMPASS_DRAW_BROADCAST (server→client).** — OBSERVED (static chain + the client's own `CHAR_MAX_DRAW_MINIMAP_KNOT_COUNT`). Handler `0x0091EA20` asserts `CharMsg:4934 message.knotCount <= CHAR_MAX_DRAW_MINIMAP_KNOT_COUNT` @ `0x0091EA43` (bound **16**) — the only occurrence of "MINIMAP" in the image. Its unpack loop is the exact inverse of the sender's pack (knot halves = signed int16). Posts `0x1000009E`; `Compass.cpp` subscribes at `0x008BB5D7`; `CompassCanvas.cpp` renders the polyline (`:1372 knotCount >= 2` @ `0x008c11b2`, `:1362 m_intensities.Count() == m_points.Count()`). Layout `word | dword | array32[16]` — `0x002B` plus a leading `word`, the shape of a rebroadcast stamping in who drew. That the leading word is a sender id is RECONSTRUCTION. **Live count 0** — expected: pings are party-visible (§1.2) and the live captures are a solo operator, so a broadcast to *other* party members never arrives.

**HAZARD if we send `0x0091`:** a `knotCount > 16` takes the assert branch `CharMsg:4934`, but the copy loop is **not** bounded by that assert — at index 16 it overwrites the security cookie and `__security_check_cookie` (`0x005AE7A9`) fast-fails the *process* (a kill, not a dialog). Whether the unpacker refuses an over-range count first is UNVERIFIED. Do not send an out-of-range `knotCount` to a live client.

### 4.2 The exploration / cartography reveal

**GAME_SMSG `0x008C` = MAP_EXPLORATION_MARK.** — CORROBORATED (3 asserts name the 3 fields; live values match). Handler `0x0091E940` → `0x00811BE0`, which posts `0x10000090` and carries the exploration-bitmap asserts: `ChCliApi:201 x + markSpanCount <= context->mapDims.x` @ `0x00811D12`, `:202 y < mapDims.y`, `:203 markSpanCount`, and `:214 blockMapDims == missionRect.x1-x0 / y1-y0` @ `0x00811DCE`. `schema/overrides.json` already fixes its shape to `msg_header | dword | dword | byte` (11 B). Live decodes `[140, 32, 24, 1]` / `[140, 33, 24, 1]` — three small integers matching **(x, y, markSpanCount)** field-for-field, x stepping as the character walks. **47 live occurrences over 6 connections.** `ChCliApi:214`'s `missionRect` is the same `s_missionClientData` footprint rect at `+0x48`/`+0x58` that `maprows.py` measured 319/319 — the consumer side of it, a connection new to the repo. Subscribers of `0x10000090`: `Compass.cpp`, `GmMapWorld.cpp`, `GmMapWindow.cpp` — one opcode feeds the compass **and** both maps, which is the Cartographer unfogging GWW describes.

**CONTESTED — the fog/exploration opcode attribution in the `0x0089`–`0x008C` range.** Deep dive A independently mapped a *different* streaming path for the same feature: `0x0089` (137) declares accum-map init (`ChCliApi:1641 accumMapInitOffset < accumMapInitData.Count()` @ `0x00811AB9`), `0x008B` (139) declares dims + RLE payload and, per A, reaches the **same** `ChCliApi:201` at **the same VA `0x00811D12`** through `0x00811B30`, and `0x00817550` run-length-expands into the `char+0x5A4` bit grid. Deep dive B attributes `ChCliApi:201 @ 0x00811D12` to `0x008C`'s handler (`0x0091E940` → `0x00811BE0`) instead. **Both cannot own the same assert VA.** Two readings are possible and unresolved: (a) there are two related mechanisms — a full-map-init stream (`0x0089` declare / `0x008B` payload) and an incremental single-cell mark (`0x008C`) — and each dive named one; or (b) the dives disagree on which handler reaches `0x00811D12`. The evidence favours `0x008C` being the incremental mark that actually fires in play (47 live, override-confirmed shape, values match the field names), while `0x0089` has **0 live occurrences** (deep dive A flags this as unexplained). The exact partition of the `0x0089`–`0x008C` handlers wants one more disassembly pass before either opcode is named in `overrides.json`. The *feature* — a server-streamed bitmap that unfogs compass and maps, keyed to the footprint rect — is established either way.

### 4.3 Quest markers, and one UPSTREAM name corroborated

A family of s2c opcodes posts to quest-panel frame messages, subscribed by `Compass.cpp`, `GmMapWorld.cpp`, `GmMapWindow.cpp`, and (for the quest log) `QuestLog.cpp`/`QuestTaskTracker.cpp`:

| opcode | proposed role | msgId | live/ours | label |
|---|---|---|---|---|
| `0x0049` | **QUEST_ADD** (with position) | `0x1000014E` | 10 / 0 | UPSTREAM name **now CORROBORATED** — see below |
| `0x0050` | quest add (no position) | `0x1000014E` | 12 / 0 | OBSERVED (attribution) |
| `0x0051` | quest marker move | `0x10000151` | 40 / 0 | OBSERVED |
| `0x004A` / `0x0052` | quest marker remove | `0x10000152` | 6 / 12 | OBSERVED |
| `0x0053` / `0x004D` | quest marker move/set | `0x10000153` / `0x10000154` | 6 / 6 | OBSERVED |

**`0x0049 = QUEST_ADD` is now CORROBORATED on build 38797.** Recon 2 flagged it UPSTREAM (`gw-preservation`/`Fournux` via `studies/datwrite/FINDINGS.md:328-331`), explicitly unverified, with that document's recorded **−1 opcode drift in 35 of 40 discriminating cases** hanging over it and `0x0049` not individually arbitrated. The frame-bus join settles it independently of the upstream: `0x0049` posts `0x1000014E`, and **`QuestLog.cpp` subscribes to `0x1000014E`** at `0x0057BD3D` (as does `QuestTaskTracker.cpp`). A quest-log panel and a quest-task tracker are exactly what "quest add" must reach. Live payload agrees: `[73, 80, (11715.0, 3517.0), 26, 148, 0, <3×encstr>, 148]` = id, world position, plane, destination map, three encoded string ids, current map. (The strings render as garbage because they carry UTF-16 surrogate-range code units — the `string16` phenomenon; they are encoded ids, not player text.) The off-by-one worry is retired for `0x0049` specifically.

### 4.4 The rest of the map UI (attributed, mostly unobserved live)

`0x008D`–`0x0090` (map/compass markers, → `0x10000091`, `Compass.cpp` + `GmMapWindow.cpp`); `0x0096`/`0x0097`/`0x011B`/`0x01BE`/`0x0118`/`0x0119`/`0x0131`/`0x012E` (location tags, `GmMapCtlLocationTag.cpp`/`GmMapWorld.cpp`); `0x0066`/`0x0067` (hero/player map position). Attributions OBSERVED; semantics UNVERIFIED. Most have **0 live occurrences** — a stated but unconfirmed explanation is that the live corpus is one solo character over 3 maps (148/146/164) in the Ascalon/pre-Searing region, so world-map location-tag and hero-position traffic would not fire there; `0x0066` (hero position) has the clean explanation that the sessions had no heroes.

**`0x008D` caution (recon 2):** its 7-record burst is **byte-identical across maps 148/146/164** in 3 live sessions, arguing for a static/global catalogue rather than per-map minimap content — a strong lean on a small sample (3 sessions, 3 maps), not a closed case.

---

## 5. What our server sends, and lacks

### 5.1 What works

- **Compass agent dots** render on our own server's agents, colour-coded (§3.6). — OBSERVED. Populated authored areas now put bodies out (`customarea/FINDINGS.md`, run `20260813T185442`).
- **The `0x0199` map-type byte** is sent correctly per map and reads back as our server set it (§3.3). — OBSERVED.

### 5.2 The unnamed drop

**GAME_CMSG `0x002B` (COMPASS_DRAW) has no dispatch arm in `authsrv.py`.** — OBSERVED (AST of the source). The c2s arm set is `0x0009, 0x0026, 0x0027, 0x0033, 0x0039, 0x003D, 0x003E, 0x0040, 0x0046, 0x0047, 0x0079, 0x0088, 0x008A, 0x0090, 0x0091, 0x0092, 0x00C1`; `0x002B` is not among them, is **not** in `test_dispatch.py`'s `DROPPED_ON_PURPOSE` allowlist (which holds only `0x000A, 0x0012, 0x003B, 0x0060, 0x0064, 0x0084`), and has **no name in `schema/overrides.json`** — so the D9(a) asymmetric tripwire (which fires only on a *named* c2s opcode with no arm) never flagged it. **Our own client has already exercised it: 5 `0x002B` messages are in `vault/captures/gamesrv/`/`authsrv/` as `kind:"decoded"`** — our client drew on its compass and our server silently discarded it into the D9(a) `else`. This is a genuine, previously-unnamed drop.

### 5.3 What our server never sends

Our server sends **none** of the s2c minimap/exploration/quest opcodes organically. Every non-zero "ours" count in §4 is `PROBE[smsgsweep]` synthetic traffic or `tape[...]` replay (labels read off the capture records) — e.g. `0x008C` shows 66 ours, all tape replay. Nothing is generated by our own game logic. Opening the world/mission map produces **zero network traffic** under a labelled run that predicted silence and got it (`studies/cmsg/FINDINGS.md:148`, step `map_open`, `labelrun.py:167`) — OBSERVED — so map *opening* is client-local; that bounds opening, not the whole feature.

### 5.4 Named opcodes not promoted

`GAME_SMSG 0x0195` (`INSTANCE_LOAD_SPAWN_POINT`) and `0x0199` (`INSTANCE_LOAD_INFO`) have informal names in `authsrv.py:171,174` but **no `name` in `schema/overrides.json`** (`Codec.name_for` answers `"?"`). Discussed at length in `studies/maprows/` and `studies/profession/RUNS.md`; the promotion was never done.

### 5.5 The two names for one VA

`0x0084D9B0` is called **`MissionCliGetMap`** in `studies/profession/RESKIN.md:1154` and **`MsCliApiGetMap`** in `schema/overrides.json:461` — one VA, two names, unreconciled. Both are ArenaNet's own (the client spells it `MissionCliGetMap()` at `QuestLog:261`); the source file is `MsCliApi.cpp`, so `MsCliApiGetMap` is the better canonical form.

---

## 6. The authored-map evidence so far

The customarea arc is the only direct visual evidence of the minimap on a map this project built. Both sightings are screenshot-derived and both carry that arc's own "they are not themselves the evidence" caveat — the load-bearing proofs there were the four discriminators (`Gw.log`, navmesh log, archive diff, row-unchanged), not the frame.

- §22 (9-chunk minimal map, `customarea/FINDINGS.md:3353`): "a small square minimap."
- §23 (`PathChunk.minimal` collision test, `:3491-3492`): "a minimap that is a featureless brown disc where Kamadan's is a detailed city."

**CONTESTED within our own record (deep dive C):** §22 reports a "square" minimap and §23 a "brown disc" on essentially the same class of map. §22's frame was caught mid-crossfade with the loading overlay at 100%, so the "square" may be a load-screen element rather than the compass. Unresolved; both non-load-bearing.

The mechanism is now decidable and the **obvious "art is missing" explanation is REFUTED** (deep dive A): every continent chunk each `maps.toml` map needs is present in the archive (map 148 2/2, 146 2/2, 143 4/4, 144 2/2, 449 1/1, 194 2/2), so the tiled placeholder is not being hit for lack of art. The live hypothesis (RECONSTRUCTION, with its refutation attached in PLAN rung S5/C2): the compass crops the continent texture at `footprintOrigin + (world − mapRect.origin)/96.0`, where the footprint origin comes from the *borrowed area row* (map 143 = 320×544 cells) while `mapRect`/dims come from the *authored map file* (~32–96 cells), so an authored map shows only the top-left `dims×dims` texels of a large borrowed footprint window — a small, probably featureless corner of Pre-Searing/Shing Jea art. Consistent with every measurement; not yet confirmed on a screen.

---

## 7. Contradictions and open questions

**Cross-report contradictions, surfaced rather than silently resolved:**

1. **The fog/exploration opcode (§4.2): `0x008C` vs `0x0089`/`0x008B`.** Deep dives A and B attribute the same assert VA `0x00811D12` to different opcodes. CONTESTED; the feature is established, the exact opcode partition is not. One disassembly pass settles it before naming either in `overrides.json`.
2. **The c2s draw opcode: "NOT FOUND" (recon 2, deep dive C S6) vs located `0x002B` (deep dive B).** Reconciled: recon searched *names* (correctly none); deep dive B located the *sender* in the binary. `0x002B` is CORROBORATED. Deep dive C's ladder rung S6 is substantially answered by B and is recast in PLAN as a confirmation, not a search.
3. **The §22/§23 minimap appearance** (§6) — CONTESTED within customarea's own record.
4. **`0x0093`'s live sample count:** `studies/recon/FINDINGS.md:540-543` says 9, a fresh full-live-corpus decode (recon 2) gives 2. CONTESTED; neither chased down. Not minimap-load-bearing, recorded for the next reader.
5. **`0x0199` "third dword" (task premise) vs `byte` at field index 3** (§3.3) — corrected to the byte; RESKIN's "dword" is the memory slot.

**Open questions / NOT FOUND (auditable negatives):**

- **What supplies the compass's world index** (`[ebx+0x84]` at `0x008C2004`): read, never traced to a writer. The `continent → world` map is NOT FOUND — deep dive C's containment test could not discriminate (worlds 0 and 7 both fit continent 0's footprints because the biggest grid always contains) and is reported as a failed method, not a result. The continent field (`s_missionClientData +0x04`) is the leading hypothesis (histogram of 7 continent values matches 7 tile-bearing worlds) but the offset itself is **UPSTREAM** (`areatable.py`, four mirrors sharing one ancestor).
- **Whether a hostile NPC-class agent's compass dot renders red:** the `npc_allegiance` probe (`probes.py:1237-1240`) asked the operator to note it; the result table (`studies/enemy/PLAN.md:479-487`) records nameplate colour only. NOT FOUND — a transcription gap, possibly recoverable from an existing frame.
- **Whether the compass *map image* (not markers) is masked by the fog bitmap:** `CompassMarker` tests the bits, `CompassMap`'s blit does not, `GmMapView` does. Whether the compass composites a second masked layer (in `CompassModel.cpp` or `CompassCanvas.cpp`, profiled but not fully disassembled) is UNVERIFIED.
- **Indirect calls were not swept** — every §3 negative is direct-`call rel32` only; a compass→Path call through a vtable would be invisible. The `.rdata`/`.data` function-pointer sweep that would close this was not run.
- **`s_missionClientData +0x68`** (per-area compass texture, 157/888) is a live lead nothing in the repo has read; none of our slots use it.
- **`MISSION_MAP_OUTPOST`'s numeric value**, the **satellite tier offsets**, and **whether the atlas crop is 1 px per terrain cell** (RECONSTRUCTION; PLAN rung S5 settles it) are all NOT FOUND / UNVERIFIED.
- **The world map may be entirely out of server reach:** `map_open` is silent, exploration is per-character and client-local (WIKI). One silent labelled run bounds opening, not the whole feature — UNVERIFIED that the server has any lever there.
- **Only build 38797 was read.** The second vaulted build (`2026-04-30_b174de1f2d8d`) was touched only for the two-archive tile resolution check (§3.1, which agreed); no other cross-build corroboration was attempted.
