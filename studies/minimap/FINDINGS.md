# The minimap — compass, mission map, world map: where the picture comes from, what the wire carries, and what an authored map gets for free

**Study arc:** `studies/minimap/` · **Date:** 2026-08-14 · **Method:** four recon sweeps (repo knowledge inventory; schema + capture opcode census; client string/assert recon; GWW behaviour checklist) and three deep dives (render data source; opcode frame-bus join; custom-map gap + ladder), each reading the pinned client statically and the live capture corpus, then this synthesis over all seven. No client, game, or server was launched for any input. `C:\gw` was read-only or untouched throughout.

**Client image on every static claim below:** `vault/client/2026-07-29_221c13772c7a/Gw.exe`, **build 38797**, the pinned pristine copy (`toolkit/clientscan/pinned.find()`). Every VA is that image's. **Capture corpus on every wire claim:** the complete live corpus — 3 game-bearing stamped directories (`20260807T133758`, `20260807T143055`, `20260810T235916`), 11 game connections, **22,524 s2c GAME_SMSG and 971 c2s GAME_CMSG**, `frame_report` residual 0 on all 22 connection/direction pairs. The 22,524 equals CLAUDE.md's own figure for the whole live corpus, so this is the full corpus and not a sample. "Ours" counts are from `vault/captures/gamesrv/` + `authsrv/` (1,512 `.jsonl`); `harness/`, `selftest/`, `portal*/`, `raw/` were not scanned and are a stated gap.

---

## 0. The result, and the question it serves

**Custom maps need a working minimap, and this dive was to find out what an authored map already gets and what it cannot get.** The answer is sharp and mostly negative:

**The compass, the mission map (U key), and the world map (M key) are three views of ONE per-continent picture that lives entirely in the client's archive.** — OBSERVED (static, build 38797; §3). The ground image under the dots is a per-continent atlas of 512×512 ATEX tiles compiled into the client, cropped to the area's footprint rectangle. An authored map served at a borrowed area slot shows a crop of *that continent's* art scaled over our terrain — which is the mechanism behind the customarea arc's "featureless brown disc" sighting (§6). Nothing our server sends can supply the drawn art.

**Corrected 2026-08-14 (rung S9 adjudication): this paragraph used to end "…, and a map file contributes nothing to it."** The *art* half is unmoved and still OBSERVED. The **addressing** half is false: `CompassMap`'s ground layer is bounded by a rect it latches out of `Engine\Map\Map.cpp` — `0x008C2939 call 0x70a5c0` copies the LOADED MAP's own world rect into `[CompassMap+0x60..0x6c]`, divides it by the 96.0 cell pitch at `0x0094DE10`, and stores `(0, 0, mapCellsX, mapCellsY)` into `[CompassMap+0x50..0x5c]` (`0x008C298C`/`0x008C299A`/`0x008C29A8`/`0x008C29B2`). Every draw request is **clamped to that rect before the footprint origin is added** (`0x008C2471..0x008C24D2`, then `0x008C2782 add edx, eax` / `0x008C2792 add esi, edi`), and an empty intersection goes straight to the fallback tiler. So the map file cannot supply a pixel and **does** decide how much of the footprint is ever asked for. — OBSERVED. §6 carries the consequence.

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
| **`satelliteCX/CY` at +0x18/+0x1C; satellite tile table at VA `0x00A37440`** | third getter disassembled 2026-08-14 (rungs S3 and S4, independently): `cmp ecx,[edx+0x18]` / `cmp eax,[edx+0x1c]` guarding `ConstWorldMap:1360/1361`, `mov esi,0xa37440` at `0x005A95D0`, same 7×12 `{count, array, world}` shape | OBSERVED — **corrected**, this row read "third getter not disassembled / UNVERIFIED" |
| **`count == gridX × gridY` on 21 of 21** (7 worlds × 3 tiers), each tier's dim offsets read out of that tier's own `cmp` rather than assumed | chunk +0x04/+0x08, parchment +0x0C/+0x10, satellite +0x18/+0x1C | OBSERVED — a check the tables could have failed, and the reason `grids()` in `worldmap.py` deliberately does NOT refuse a disagreement: a function returning only the rows that agree makes the agreement unfalsifiable |
| a **7×12-byte** table @ VA **`0x00A37390`** = `{u32 count, u32 *array, u32 world}`, linear-searched on world | `0x005A9450 mov esi,0xa37390 … cmp eax,0x54` (0x54=7×12) | OBSERVED |
| **`count == chunkCX × chunkCY` on 7 of 7 worlds** (512,32,192,32,192,32,128) | both sides read independently | OBSERVED — this is what makes "grid of tiles" a measurement, not a story |
| worlds 7, 8, 9 have **no record** in the table (accessor returns 0) | table walk | OBSERVED |
| parchment tier has its own identical table @ VA **`0x00A373E8`** | same 0x54 loop | OBSERVED |
| tile index = `chunk.y*chunkCX + chunk.x`, bounded by `ConstWorldMap:1325 offset < files.count` @ `0x005a9480` | `imul edi,[edx+4]; add edi,[ebx]; cmp edi,[esi]` | OBSERVED |
| array slot is a pointer (NULL where no tile) to an 8-byte `{u16 id0, u16 id1, u32 0}`; trailing u32 = 0 on 409/409 | `File.cpp` pair form, same as RESKIN §22 glyph sheet | OBSERVED |
| **409 chunk-tier tiles over 7 worlds; 401 resolve, all 401 magic `ATEX`**; 8 unresolved (ids 387674/387678/387680/387682/387684/388093/388095/388097), 3 in world 0 and 5 in world 1 | ~39.9 MB stored, reproduced from committed code by `worldmap.py` | OBSERVED |
| **THREE tiers, not two: 492 tiles total, 484 resolving, 484/484 `ATEX`** — identically on **all three** vaulted archives (`dat_study` 177,342 MFT rows; `client/2026-04-30_b174de1f2d8d` 177,311; `client/2026-07-29_221c13772c7a` 177,335 — the third is new to this arc and agrees) | rung S3, `toolkit/clientscan/worldmap.py`. The same 8 ids are missing on all three | OBSERVED |
| the 8 are **absent, not renamed** | not in `dat_study`'s file-id table plainly, not under bit 31 (`FcArchive`'s rename bit, `studies/maprows/FINDINGS.md` §8), not at `id ± 1` — while their id-space neighbours 387686/387687 and 388088-388091/388099/388100/388102 ARE present | OBSERVED; **why** they point at ids no archive holds is NOT FOUND, and the four lookups above are the whole search |
| **NOT every tile is 512×512** | over the whole population (n=484, 16-byte partial decompression, no sampling): chunk 397×512² and **4×256²**, parchment 58×512², satellite 14×512² and 11×256². The four odd chunk tiles are world 3 cells (1,5) (2,5) (3,5) (3,6), file ids 338409/338411/338413/338415, and are **not at a grid edge** | OBSERVED — **corrected**: this row read "tiles are 512×512 ATEX … sampled (n=4 of 401)", which is what a 4-tile sample of world 1 will always say. A crop renderer that assumes 512 px per chunk cell misplaces those four, and `CompassMap:472 m_imageDims == CONST_WORLD_CHUNK_SIZE` bounds at 512, so whether the client ever asks for one is **UNVERIFIED** (a client-run question) |
| `CONST_WORLD_CHUNK_SIZE = 0x200 = 512` | `0x008C202D cmp [edi],0x200` / `0x008C2035 cmp [edi+4],0x200` guarding `CompassMap:472 m_imageDims == CONST_WORLD_CHUNK_SIZE` @ `0x008c2043` | OBSERVED |

### 3.2 One atlas, three views

`codescan --xrefs 0x005A93E0` (the chunk-tile getter) has **exactly two direct callers**: `0x005531BD` inside `GmMapView.cpp` (the mission map / world map view) and `0x008C200A` inside `CompassMap.cpp` (the compass). — OBSERVED. So compass, mission map and world map are three crops of one per-continent picture, and **no map file supplies a pixel of it**. `GmMapView` additionally uses all three texture tiers (chunk/parchment/satellite); the compass uses only the chunk tier.

*Corrected 2026-08-14 (rung S9 adjudication), same fix as §0: this sentence used to end "and a map file contributes nothing to any of them", which is true of the ART and false of the ADDRESSING.* The compass clamps every draw request to a rect it latches out of the **loaded map file's** own dims before adding the footprint origin (§0, §6b.4), so the map file decides how much of the footprint is ever asked for. **Measured for `CompassMap` only** — whether `GmMapView` applies the same clamp is **NOT FOUND**, and it matters, because it decides whether the U-key map shows a whole continent crop on an authored map while the compass shows a corner.

### 3.3 THE LEVER: `0x0199`'s map-type byte selects the footprint the compass crops

At `0x008C2761` the compass reads `s_missionClientData[map]` (accessor `0x005A8580`), calls `MissionCliGetMap()` (`0x0084D9B0`), and branches:

```
008C2770  test eax, eax
008C2772  jne  0x8c277c
008C2774  mov  eax,[esi+0x48] ; FOOTPRINT_A.x0        (map == 0)
008C277C  mov  eax,[esi+0x58] ; FOOTPRINT_B.x0        (map != 0)
```

`+0x48` / `+0x58` are `maprows.FOOTPRINT_A` / `FOOTPRINT_B` (`toolkit/clientscan/maprows.py:83-88`), which `studies/maprows/FINDINGS.md:484-485` §9 item 4 recorded as open. **This answers §9 item 4: both, and the selector is `MissionCliGetMap()` — the value the `0x0199` handler writes into `missionContext+0x238` from the map-type byte our own server sends.** — OBSERVED (static; deep dives A and C reached it independently, and rung S2 closed it 2026-08-14).

**The enum is TWO-VALUED, so the `test eax,eax; jne` is a real choice and not a "0 vs anything" collapse** — all three numbers read out of compiled comparisons rather than inferred: **`MISSION_MAP_OUTPOST == 0`**, because `QuestLog:261 MISSION_MAP_OUTPOST == MissionCliGetMap()` compiles to `call 0x84d9b0; test eax,eax; je 0x57bed7` at `0x0057BEBA` — the assert is SKIPPED when the answer is zero; `MISSION_MAP_GAME == 1` (`MsCliApi:251 context->map == MISSION_MAP_GAME`, `cmp [esi+0x238],1` @ `0x0084D9EC`); `MISSION_MAPS == 2` (`MsCliMan:486`, `cmp [edi+0x238],2` @ `0x0085204B`). So **`+0x48` is the OUTPOST footprint and `+0x58` the GAME (explorable/mission) one.** — OBSERVED. *Corrected: this section previously recorded `MISSION_MAP_OUTPOST`'s numeric value as NOT FOUND.*

**Correction to this section's own reading (rung S2): the branch above is neither the only compass read nor the widest of them.** The containing function starts at `0x008C2440` and reads the footprint **twice** — once through the out-of-line helper at `0x008C2160` (called at `0x008C2500`, copying the WHOLE selected 4-dword rect into a local) and then again inline at `0x008C2761`, taking the **origin only**. A third compass-group reader sits at `0x008C3141`/`0x008C314B`. Image-wide there are exactly **six** readers of either footprint: those three, plus `ChCliApi.cpp` `0x00811C64` (which `shr`s the rect by 5 into the 32-cell fog block grid — §4.2), plus `GmMapHelpers.cpp` `0x0054E6A0` and `0x0054E830`. **`GmMapView.cpp` reads neither offset** and calls neither the accessor nor the selector (0 instructions at both over `0x00550A18..0x00553D8B`) — so the prediction's "GmMapView will have its own read" is REFUTED; the map side's read is `GmMapHelpers`.

**The map side has a fallback the compass does not.** `GmMapHelpers` implements `rect = (MissionCliGetMap() == 0) ? (A if A != {0,0,0,0} else B) : (B if B != {0,0,0,0} else A)` (`0x0054E876..0x0054E894` and its mirror at `0x0054E8A4`); the compass instead bails on a degenerate rect at `0x008C274F cmp x0,x1; je`. — OBSERVED.

**The count is closable because the table base `0x0096DE38` occurs EXACTLY ONCE in the image**, at `0x005A85A8` inside the accessor `0x005A8580`, so every row pointer the client holds came from there. Three sweeps sharing no premise return the same six (int3-block co-occurrence with the 106 accessor call sites; a shape sweep for a contiguous four-dword rect at both offsets on one base register; a forward sweep from all 171 `MissionCliGetMap()` call sites). Blind to indirect calls and to a row pointer cached across functions — stated so the negative is auditable. **`s_missionClientData` is in `.rdata`**, which is a second discriminator: any site that *writes* `[base+0x48]` is provably not an area row, which is how `Compass:222`'s `0x008BC398` and the `MsCliApi.cpp` struct copy at `0x0084E322` were excluded.

**Tool trap worth carrying (rung S2, same class as `test_codescan.py` §8/§9 from the other side):** `codescan --in <module>` takes its bounds from `asserts.py`, and `--bounds CompassMap` is `0x008C1E1B..0x008C25A4` — so `0x008C2774`, the branch this section is about, is **0x1D0 bytes past the upper bound** and `--field 0x48 --in CompassMap` returns three rows *not including it*. A module with a long assert-free tail silently truncates every `--in` query and the tool cannot warn, because it does not know where the module ends. Use the **directory** prefix: `--field 0x48 --in 'P:\Code\Gw\Ui\Game\Compass\'` returns 20 instructions and reaches all three compass readers.

Wire correction (recon 2, both deep dives): the map-type value is a **`byte` at field index 3** of `0x0199` (`schema/messages.json` opcode 409 = `[msg_header, agent_id, word, byte, dword, byte, byte]`), *not* a "third dword". RESKIN.md's "dword" is the 4-byte in-memory slot at `missionContext+0x238`, not the wire width.

Under our server today the byte is always effectively A-selecting for authored maps: `authsrv.py:4110` sends `1 if (EXPLORABLE or map_explorable) else 0`, and `content/maps.toml:170` gives map 143 `explorable = false`, so `MissionCliGetMap()` reads 0 → FOOTPRINT_A, the **OUTPOST** rect (`studies/profession/RUNS.md:1096-1097`, OBSERVED on a live run).

**172 of 888 rows have A ≠ B — but only 20 of the 172 carry two different NON-ZERO rects**, and those 20 are the whole discriminating population for the lever. Of the 172: **136 have A all-zero, 16 have B all-zero, 20 carry two real rects** (rung S2, MEASURED over all 888 rows through `maprows.locate_table`). On 152 rows the "disagreement" is one rect being **absent**, not two rects rivalling — which is exactly what the `GmMapHelpers` zero-fallback above is for, and why `read_footprints`' existing skip-an-all-zero-rect rule is the same rule arrived at from the other end. The 20 are ids **135, 254, 255, 424, 426, 428, 433, 435, 451, 474, 476, 478, 480, 491, 492, 493, 494, 495, 545, 554**; nine of them (424, 426, 433, 476, 478, 491, 492, 545, 554) pair a 192×192 rect against a much larger one, which is the shape the outpost/explorable naming predicts. Row 493's A is byte-identical to Kamadan's `(2080,3136)..(2496,3584)`.

**A refutable corroboration from a column the selector never touches**, prediction stated before it was read (a flat or overlapping split would have refuted it): the A-zero and B-zero populations are **disjoint on their dominant `type` values** — `{2: 63, 18: 71, 14: 2}` against `{10: 12, 13: 3, 14: 1}`. Two instance kinds predicts that; "one field is a stale duplicate of the other" does not. CORROBORATED, at UPSTREAM strength, since `areatable.OFF_TYPE` is UPSTREAM.

**All six ids in `content/maps.toml` (143, 144, 146, 148, 449, 194) have A == B**, which is why the lever needs a borrowed slot to demonstrate — and PLAN rung C3's population is **20, not 172**.

### 3.4 The loader, and ArenaNet's own word for it

`CompassMap.cpp`'s image loader at `0x008C21C0` logs the string at `0x00BA04B4`: **"Converting world minimap texture to DXT1.\n"** and forces GR format 15 (DXT1). — SOURCED. So `minimap` is ArenaNet's own word for this texture, and the compass's various `(rect & 3)==0` asserts (`CompassMap:288-291/381-384`) are DXT-block alignment guards. When the image is NULL the code does not clear to a colour — it **tiles** a fallback surface (`0x008C1E00`, `CompassMap:164 (int)rect.x1-(int)rect.x0 > 0`), which is the mechanism behind a "featureless" compass.

**The log line is GATED and this section used to read as though it always fires (rung S9, 2026-08-14).** `0x008C21EB cmp dword [ebp-4], 0xf; 0x008C21EF jne 0x8c21fb` puts it on the **conversion** arm alone — a failed load returns 0 at `0x008C21E4` with no log, an already-DXT1 surface returns at `0x008C21F8` with no log — and **484 of 484 atlas tiles are already DXT1**, so it is dead code for this subsystem. It is also the **only** call to either logger (`0x0046ED40` / `0x0046EE30`) in the whole compass group `[0x008BB100, 0x008C5890)`. **The compass writes nothing to `Gw.log` under any condition on this build.** — OBSERVED. §6 carries what that costs. The fallback tile is DXT1 too and the constructor converts it at `0x008C1CE9 push 0xf; call 0x679480` **without** going through `0x008C21C0`, so it cannot log either.

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

**A rate limiter and knot accumulator sit at the send site** (`0x008C08B8 mov eax, 0xfa`): the client accumulates knots and flushes on a **250-millisecond countdown**, sending nothing when empty. This is the ping/draw rate limit GWW documents nowhere (§1.2), read out of the binary. — OBSERVED. *Corrected: this line read "250-unit countdown … the unit (ms?) is UNVERIFIED".* **Three independent witnesses, one of them on the wire:** the elapsed delta the countdown is decremented by is divided by the double **1000.0** at `0x0093 4389 8` (`0x008C0877 fdiv qword [0x943898]`) to reach seconds; the clock behind `0x0046B4E0` resolves through the import directory to `WINMM.dll!timeGetTime` (millisecond resolution by definition); and **our own captures show consecutive flushes of one stroke at Δ = 0.251988 s and Δ = 0.249950 s** (`vault/captures/authsrv/authsrv-20260805T214038-c2.jsonl` t=183.585/183.837; `authsrv-20260814T100340-c1.jsonl` t=151.669/151.919) — a prediction the captures could have refuted.

**A second, finer limiter was not in the earlier reading:** the drag handler gates each *knot* at a **25 ms floor** (`0x008BF45E cmp ecx, 0x19`; a faster sample UPDATES the last knot in place rather than appending). So a drag emits at most **10 knots per flush** and the 16 cap is never approached from the client side. — OBSERVED.

**The knot coordinate space is CLOSED: absolute world position divided by 96.0 — terrain cells.** The encoder at `0x008C07F0` divides each axis by the double 96.0 at `0x0094DE10` (the same cell pitch `test_terrain.py` pins at `rect/dims == 96.0` exactly) after `0x008C0560` has added the player's own world position, so a knot is absolute and not an offset; three consumers multiply back by that same constant (`0x008BF177`, `0x008BE6C7`, `0x008BE774`). Quantisation is round-away-from-zero (`0x0046DF80` → `0x005B6E0B` then `_ftol`). **The wire discriminates all four readings and could have refuted the measured one:** the client's own compass constants bound a click at `sqrt(0.1650390625) × 11076.9228515625 = 4500.0` world units exactly (hit test `0x008C0130` against the world scale at `0x00BA0318`), and the corpus's one live `0x002B` — `20260807T143055` conn `:60935` t=50.702, `[32811, 7, [3801175]]`, knot `0x003A0057` — lands at (8352, 5568), **3236.4 units** from the position the preceding `0x003D` reports 150 ms earlier and 5.0° off that message's own heading, while halves-swapped (7140.1), unscaled (11562.4) and unscaled-swapped (11580.7) are all **outside** the compass. Signedness is corroborated independently of the two `movsx`: eight loopback knots carry a negative low half, which under an unsigned reading would sit 6.29 × 10⁶ units away. — OBSERVED.

**Field 1 of `0x002B` is a client-allocated STROKE HANDLE and must be echoed, never invented.** `0x008C0038..0x008C0065`: the client either pops the back of a recycle pool at `[canvas+0x68]` or takes the post-increment counter at `[canvas+0x98]` (one read, one write image-wide), and stores it to `[canvas+0xbc]`, which is what `0x008C08D6 push [esi+0xbc]` sends. Two independent corroborations neither dive could force: both multi-draw sessions in our corpus emit **7 then 6**, a decreasing pair a plain counter cannot produce; and the two messages 250 ms apart that are **one stroke split across two flushes share id 6**, while two separate short strokes 250 ms apart differ (7, 6). Allocator OBSERVED; "stroke" RECONSTRUCTION. It rules out colour or ping-type readings — a colour does not come out of a free list.

**The leading `word` of `0x0091` is an OWNER TAG whose local value is ZERO — not a colour, not an agent id, and never rendered.** *Corrected: this section previously read it as a sender id, RECONSTRUCTION.* Fields 1 and 2 are used for exactly one thing: the two components of the key passed to the line lookup at `0x008BE696..0x008BE6A1`, and the client builds that same key for its OWN strokes with the first component **hard-zeroed** — `0x008C0091 mov dword [esi],0` on creation and `0x008BF43B mov dword [ebp-8],0` on the drag-path lookup. — OBSERVED. That it identifies the drawing party for remote strokes is RECONSTRUCTION (a composite key is what stops two players' `line_id = 3` merging); what number space it draws from is **NOT FOUND**, and the client types it `u16` (cmd `0x204`) rather than with its type-0 `agent_id` tag, which argues against an agent id. **Operational consequence, sharp:** a rebroadcast carrying `origin = 0` makes the drawing client match its own line and append the echo a second time, doubling the stroke.

**GAME_SMSG `0x0091` = COMPASS_DRAW_BROADCAST (server→client).** — OBSERVED (static chain + the client's own `CHAR_MAX_DRAW_MINIMAP_KNOT_COUNT`). Handler `0x0091EA20` asserts `CharMsg:4934 message.knotCount <= CHAR_MAX_DRAW_MINIMAP_KNOT_COUNT` @ `0x0091EA43` (bound **16**) — the only occurrence of "MINIMAP" in the image. Its unpack loop is the exact inverse of the sender's pack (knot halves = signed int16). Posts `0x1000009E`; `Compass.cpp` subscribes at `0x008BB5D7`; `CompassCanvas.cpp` renders the polyline (`:1372 knotCount >= 2` @ `0x008c11b2`, `:1362 m_intensities.Count() == m_points.Count()`). Layout `word | dword | array32[16]` — `0x002B` plus a leading `word`, the shape of a rebroadcast stamping in who drew. That the leading word is a sender id is RECONSTRUCTION. **Live count 0** — expected: pings are party-visible (§1.2) and the live captures are a solo operator, so a broadcast to *other* party members never arrives.

**HAZARD RETRACTED — it is VOID for anything arriving off the wire.** *This paragraph used to read: "a `knotCount > 16` … overwrites the security cookie and `__security_check_cookie` (`0x005AE7A9`) fast-fails the process … Do not send an out-of-range `knotCount` to a live client."* Every clause about the **handler** is true and re-verified: `0x0091EA52` re-loads the count from the message *after* the assert call returns, the destination array is `[ebp-0x84, ebp-0x04)` = 16 × 8 bytes with `sub esp, 0x84` = 128 + the cookie, and `0x0091EA9E` calls the cookie check before the epilogue. **But the message never reaches it.** The generic unpacker in `P:\Code\Net\Msg\MsgConn.cpp` refuses an array count above the descriptor's declared capacity *before* dispatch: `0x007DC455 shr eax,8` extracts the capacity from the cmd (`0x102b >> 8 = 16`), `0x007DC458 cmp ecx,eax`, `0x007DC45A ja 0x007DC620` — which sets error state 2, returns 0, stores nothing, and never reaches the dispatch member at `0x007DC5C4`. The bound is **tight, no off-by-one**, and `CharMsg:4934` is therefore unreachable from the network. — OBSERVED.

**What survives:** the hazard is real inside the client's own *sender* (`0x0092025B jbe 0x920275` skips the assert and falls into a loop terminated only by `cmp edx, edi`), driven by `[canvas+0xec]`, which needs >425 ms of continuous mouse input between two frame updates. Nothing a server sends can drive it. **The practical consequence for PLAN C4 is the opposite of the old warning: an over-range `0x0091` is not dangerous, it is INERT** — the connection is left in error state 2 and the probe measures nothing. Keep `knotCount` in 1..16 for the experiment's sake, not for the client's.

### 4.2 The exploration / cartography reveal

**GAME_SMSG `0x008C` = MAP_EXPLORATION_MARK.** — CORROBORATED (3 asserts name the 3 fields; live values match). Handler `0x0091E940` → `0x00811BE0`, which posts `0x10000090` and carries the exploration-bitmap asserts: `ChCliApi:201 x + markSpanCount <= context->mapDims.x` @ `0x00811D12`, `:202 y < mapDims.y`, `:203 markSpanCount`, and `:214 blockMapDims == missionRect.x1-x0 / y1-y0` @ `0x00811DCE`. `schema/overrides.json` already fixes its shape to `msg_header | dword | dword | byte` (11 B). Live decodes `[140, 32, 24, 1]` / `[140, 33, 24, 1]` — three small integers matching **(x, y, markSpanCount)** field-for-field, x stepping as the character walks. **47 live occurrences over 6 connections.** `ChCliApi:214`'s `missionRect` is the same `s_missionClientData` footprint rect at `+0x48`/`+0x58` that `maprows.py` measured 319/319 — the consumer side of it, a connection new to the repo. Subscribers of `0x10000090`: `Compass.cpp`, `GmMapWorld.cpp`, `GmMapWindow.cpp` — one opcode feeds the compass **and** both maps, which is the Cartographer unfogging GWW describes.

**SETTLED 2026-08-14 (rung S8). This paragraph used to be headed "CONTESTED — the fog/exploration opcode attribution in the `0x0089`–`0x008C` range" and recorded two dives putting `ChCliApi:201 @ 0x00811D12` under different handlers. Reading (a) was right — there ARE two mechanisms — and deep dive A's opcode LABELS were wrong.** Two agents attacked it from opposite ends with the rival answers withheld from both: one from the assert side (bound every function that could contain `0x00811D12`, then ask who calls it), one from the opcode side (start at the receive table and walk each handler forward). **They agree on every VA, every partition and every live count.**

| opcode | body | what it is | live (of 22,524) |
|---|---|---|---|
| `0x0087`/`0x0088`/`0x0089` | 5-byte `jmp` thunks `0x00811A70/80/90` → `0x007E0FC0/D0/E0` → `0x008009E0`/`0x00800B20`/`0x00800C30` | **NOT in this subsystem at all.** AgentView "mannequin" create / destroy / place, into a 64-slot pointer array at `0x00BF969C` whose shared accessor `0x00800750` names itself: `AvMannequin.cpp:225 index < 64` | **0 / 0 / 0** |
| `0x008B` | `0x00811B30..0x00811BDE` | **INIT DECLARE.** `accumMapInitDims = (f1, f2)` → `ctx+0x50/+0x54`; sizes `accumMapInitData` (Array at `ctx+0x44`) to `f3` **bytes**; `accumMapInitOffset (+0x58) = 0`; if `f3 == 0`, expands immediately at `0x00811BD6` | **8** — once per instance, t ≈ 0.58-0.73 s |
| `0x008A` | `0x00811AA0..0x00811B2A` | **INIT PAYLOAD.** `memcpy(data + offset, &array, min(4·count, declared − offset))`; when the buffer fills, calls the expander at `0x00811AFB`, then frees. **This is where `ChCliApi:1641 accumMapInitOffset < accumMapInitData.Count()` @ `0x00811AB9` lives** | **8** — always immediately after its `0x008B`, 8 of 8 |
| `0x008C` | `0x00811BE0..0x00811E75` | **INCREMENTAL MARK.** Holds `ChCliApi:201/202/203/207/214`, ORs bits into an already-existing bitmap, posts `0x10000090` | **47** over 6 conns, t = 3.5-190.7 s |
| `0x008D` | `0x00811E80..0x00811FBC` | 40-byte indexed marker record into `charContext+0x7EC`, posts `0x10000091` | **28** = 7 records × 4 conns |

**`0x008C` owns `0x00811D12`, and it is not an argument — it is a count.** `codescan --xrefs 0x00811BE0` returns **1 direct rel32 reference and 0 words holding the VA in any section**: the `call` at `0x0091E95C`, inside `0x008C`'s handler `0x0091E940`. No vtable, no table, no second caller. The function is bounded on both sides (`push ebp` at `0x00811BE0`, `ret` at `0x00811E75`, ten `int3` before the next prologue at `0x00811E80`), and `0x008B`'s callee `0x00811B30..0x00811BDE` neither contains `0x00811D12` nor calls the function that does. — OBSERVED, both routes.

**The two mechanisms meet in exactly one place.** `codescan --field 0x5a4` returns 11 instructions image-wide and only **two** write bits into the grid: `0x00811E05 or dword [ebx], esi` inside `0x008C`, and `0x008176A7 mov dword [ebx], edx` inside the RLE expander `0x00817550` — whose callers are exactly `0x00811AFB` (`0x008A`) and `0x00811BD6` (`0x008B`), and nothing else. Everything else at `+0x5A4` is `= 0` teardown or a read. — OBSERVED.

**How the wrong attribution was produced, demonstrated rather than guessed.** `asserts.py --at X` is **not** a function bound — it is `near(va, span=2000)`, a fixed 2,000-byte window (`toolkit/clientscan/asserts.py:493-503`). The four functions of this family together occupy `0x00811A90..0x00811E75`, **998 bytes**, so the windows for `0x0089`'s thunk, `0x008A`'s callee and `0x008B`'s callee **all three swallow `0x00811D12`**, and `0x0089`'s window (a 5-byte thunk, so its window is entirely other people's code) also swallows `ChCliApi:1641`. Both halves of the wrong reading are exactly what the default span produces. The fix is not a tighter span — it is the two questions the window cannot answer and `codescan` can: *where does the function end* (`--dis` to the `ret` + `int3` run) and *who calls it* (`--xrefs`). This is the same class as §3.3's `--in CompassMap` truncation and `test_codescan.py` §9's `PrApi` widening: a locator whose answer looks like a measurement.

**The RLE expander, re-derived and then run on ArenaNet's own payloads.** `0x00817550..0x008176F7`: asserts `ChCliApi:77 !(context->accumMapInitDims.x % (8 * sizeof(unsigned)))`, sets `mapDims` (`+0x5B4/+0x5B8`), `SetCount((x*y) >> 5)`, **memsets the whole bitmap to zero**, then per **16-row block** (`0x008175E9 shr eax,4`) reads a **`u16` section length** and emits alternating runs whose lengths are bytes with **`0xFF` as a continuation escape**. Fed the 8 live `0x008A` payloads truncated to their `0x008B`-declared byte count, with a walker written out of `int.from_bytes`: **8 of 8 section chains close EXACTLY at the declared count with exactly `dims.y/16 = 8` blocks**, while four rivals score **0 of 8** (block height 8; block height 32; `u8` section header; `u32` section header). — OBSERVED, and it is ArenaNet's bytes killing the rivals rather than our decoder agreeing with itself.

**Five wire checks, each able to fail:**
1. **`0x008B` immediately precedes `0x008A`, 8 of 8**, adjacent in the decoded stream. The declare must run before the payload; it does.
2. **`ceil(declared_bytes / 4) == array32 element count`, 8 of 8** (26→7, 31→8, 38→10, 38→10, 36→9, 36→9, 26→7, 29→8). Two numbers from two different messages. The rival "declared is a dword count" fails all eight — which is why `0x00811AA0` clamps the memcpy to `count − offset`.
3. **`0x008B` field 1 is `dims.x`, settled from the wire independently of `[ctx+0x50]`:** the value is `(64, 128)` on 8 of 8, all continent 1, and `64 % 32 == 0` satisfies `ChCliApi:77` in that slot where none of the other payload values would. Read as `(y, x)` the grid is 128 wide × 64 tall and continent 1 is **83 blocks tall** — it would not fit. Continent extents at `>>5` over all 888 rows: only continents 1 (48×83), 5 (62×104) and 9 (24×55) fit 64×128, so the value is continent-specific and **the grid is continent-absolute, not per-map** (maps 146/148/164 are 13×16 blocks each).
4. **41 of 41 successive `0x008C` marks are adjacent blocks** (Chebyshev 1). An init stream or a catalogue is not a connected walk.
5. **47 of 47 marks land inside the area row's own footprint rect at `>>5`** — `(x,y)` from ArenaNet's wire, the rect from `s_missionClientData` in ArenaNet's binary, the shift from the client's own `shr …,5` at `0x00811C91..0x00811C9A`, the map id from `0x0199` field 2. Rivals: shift 0 → 0/47, shift 4 → 0/47, shift 6 → 0/47. **Non-vacuity is measured**: only 3-8 of the 888 rows contain a given connection's whole mark set, and the row `0x0199` named is one of them every time. The `(y,x)` transposition is only *partially* refuted here (47/47 against 31/47) because rows 146/148/164's rect is near-square; the disassembly settles it. — CORROBORATED.

**Three results the ladder needs, all OBSERVED from disassembly and none yet tested on a client:**
- **`0x008C` is INERT until the `0x008B`+`0x008A` pair has run.** `0x00811BEE cmp dword [eax+0x5ac], 0; je 0x811e72` — no bitmap, no write, no post, immediate return. `mapBits` is allocated *only* by `Array::SetCount` at `0x008175A1` inside the expander. `smsgsweep` has already sent `0x008C` 108 times that way, so every one of those measured nothing.
- **The init path posts NO frame message.** `call 0x00633D70` appears in `0x00811BE0` (`push 0x10000090` @ `0x00811E62`) and in **none** of `0x00811AA0`, `0x00811B30`, `0x00817550`. The init fills the grid silently; only the incremental mark asks the UI to repaint. **Falsifiable and cheap:** a mid-session init pair should rebuild the bitmap and NOT repaint until the next `0x008C`.
- **`0x008C` reads the SAME `MissionCliGetMap()` footprint lever §3.3 found in `CompassMap`** (`0x00811C6E`, `[esi+0x48]`/`[esi+0x58]`) and its bit writes are then gated by a per-map explorable mask byte fetched from `Engine\Map\Map.cpp` (`0x0070A120`, whose out-params must satisfy `ChCliApi:214`). **A server cannot mark a block the loaded map says is not explorable** — the single most useful thing to know before C4, because it decides whether `0x008C` can unfog anything on our own geometry. What produces that mask is **NOT FOUND** (`0x00721D00` not disassembled).

Naming, with the label each earned: **`0x008B` = MAP_EXPLORATION_INIT_BEGIN** and **`0x008A` = MAP_EXPLORATION_INIT_DATA** — CORROBORATED (disassembly names `accumMapInitDims`/`accumMapInitOffset`/`accumMapInitData`; the wire supplies the byte accounting, the ordering and the field order). **`0x008C` = MAP_EXPLORATION_MARK** — CORROBORATED, and §4.2's field naming is refined below. **`0x0087`/`0x0088`/`0x0089` = mannequin create/destroy/place** — module and bounds OBSERVED, the verbs RECONSTRUCTION, and what a "mannequin" is in player terms is **NOT FOUND** (0 live occurrences, no naming assert). A hero-flag reading is refuted as a certainty: the adjacent `AvFlag.cpp:86 flag < AV_FLAGS` bounds a *different* array (`0x00BF96AC`) at **8**, not 64.

**One field correction to §4.2's own reading:** `0x008C`'s third field is the **half-span (a radius in blocks)**, not `markSpanCount`. `markSpanCount` is the client's *derived* local — the clamped `x1 − x0` (`0x00811CE5 sub esi, ecx`) — so with `f3 = 1` the revealed window is 3×3 blocks. All 47 live values are `1`, so the wire cannot discriminate at n=1; the disassembly can. `schema/overrides.json`'s 11-byte shape is unaffected.

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

**SETTLED 2026-08-14 on both sides, and this paragraph used to read "CONTESTED within our own record … Unresolved; both non-load-bearing."**

- **§22's "square" is a load-overlay artefact — CONFIRMED.** The two frames were located and opened: `vault/captures/harness/20260811T142319/final.png` and `.../20260811T142431/final.png` (both `map_id=148`, neither `report.json` has a `"walk"` key, matching §22's "both of our runs"). Both show the "Ascalon City" loading crossfade frozen at 100% with the world rendered underneath, and the **round** compass dial mostly hidden behind the red loading-curtain art, leaving a small square-ish sliver. It is the ordinary compass cropped by a still-compositing overlay, not a differently-shaped widget. — OBSERVED.
- **§23's "featureless brown disc" is the client's NULL-image FALLBACK — the tiled surface §3.4 describes — and it is POSITIVELY IDENTIFIED.** `CompassMap`'s constructor loads the `File.cpp` pair `{0x24C0, 0x0100}` at `0xBA0368` (`0x008C1C96 push 0xba0368; call 0x679a90`), which is **archive file id 9153, row 8359, a 64×64 DXT1 ATEX with 7 levels** — present and identical in `dat_study` and in both run archives. `0x008C1E00` tiles it with an AND mask (`[edi+0x90]-1`), which is why the constructor power-of-two-checks the loaded dims. The frame is `vault/captures/harness/20260811T161925/hold007.png`. — OBSERVED.

**THE "ART IS MISSING" EXPLANATION WAS REFUTED HERE ON A PREDICATE THAT DOES NOT MODEL THE CLIENT, AND RUNG S13 HAS NOW REINSTATED IT IN A PRECISE FORM — see §6e.** The paragraph below is true as written and answers the wrong question: the tiles are **present as rows** and are **not addressable by the plain id the client asks for**, because in every one of these archives they carry bit 31. `file_id_table()` registers both forms and so answers "present"; the client's exact 32-bit compare returns nothing. **22 of 492 tiles — 18 of them in world 1, which is maps 143, 146 and 148 — were unaddressable in exactly the archives every fallback frame came from.** Original text, retained because its row/id data is correct and is what §6e builds on:

The **"art is missing" explanation is REFUTED** (deep dive A, re-verified by rung S5 against the archive the client actually opened): every continent chunk each `maps.toml` map needs is present (148 2/2, 146 2/2, 143 4/4, 144 2/2, 449 1/1, 194 2/2), and `vault/run/2026-07-29_221c13772c7a-c2/Gw.dat` — the copy those sessions played from — holds all four of map 148's tiles (file ids 116848/116850/116854/116856, rows 44717/44718/44720/44721, every one a 512×512 `ATEX`) **and** the fallback tile 9153.

**The "small featureless corner of a large borrowed footprint" hypothesis is REFUTED as the explanation for what we have actually seen.** *This paragraph used to carry it as the live RECONSTRUCTION.* Rung S5 measured six compass frames across three maps and four sessions and **every one is the fallback tile, not any crop of the atlas** — including frames from **retail map 148**, where nothing is borrowed and nothing is authored. The metric is chromatic ratio `χ = (R−G)/(G−B)`, which survives the compass's `out = a·src + (1−a)·neutral` composite because both differences scale by `a` and the neutral cancels: the six discs sit at **+1.081 … +1.110** (spread 0.029), file 9153 level 0 at **+1.164**, and the four candidate atlas crops at medians **−1.718 (449), −1.414 (144), +0.196 (143), +0.286 (148)** — with **0 of 7,948** 93×93 windows over all four crops falling inside the compass band. Three further controls: two sessions 45 minutes apart give the same disc to **0.08/255**; a ±12 px translation search on frames the player demonstrably walked between finds its best at **(0, 0)**; and a 0-355° rotation search finds its best at **0°** while the compass *bezel* visibly rotates. A ground image that does not translate with the player and does not rotate with the bezel is not being sampled in world space. — OBSERVED.

**A metric that FAILED, kept as a negative.** A normalised-texture template match (z-score both patches, slide a window, take min mean |Δ|) does **not** discriminate and points the wrong way — 0.984 for the fallback against 0.688-0.774 for the atlas crops. Two defects, both in the metric: z-scoring normalises away the one channel carrying the signal, and the search spaces are wildly asymmetric (a few hundred fallback candidates against tens of thousands of atlas windows, so the atlas wins by having more chances). This is exactly the "a blurry brown circle matches anything" hazard, and it is why the surviving metric is a **band with a full-population null** rather than a best-fit score.

**ANSWERED TWICE, 2026-08-14. Rung C1 (§6d) showed the compass DOES draw the atlas; rung S13 (§6e) then found WHY it had not: in every archive these fallback frames came from, 22 of the 492 atlas tiles — 18 in world 1, the world of maps 143/146/148 — carry bit 31, so the plain id the client's tile table holds does not bind and the lookup returns NULL. Read §6e before anything below. The question below expired rather than being solved: on build 38833 against its own archive generation the compass draws the atlas crop on retail map 148 (χ +0.250..+0.279 against the crop's predicted +0.286, with the old fallback frames re-measured at +1.154..+1.160 by the same code as the control).** The whole-disc fallback is **not** a property of our server. Everything from here to the end of this section is the record of the hypotheses that were killed while the premise still held — it remains correct as static analysis and is retained for that, but **do not read it as describing current behaviour.**

*The question, as it stood:* **the open question is no longer "what does the crop look like" — it is "why is the compass image NULL under our server, even on a retail map whose tiles are present?"** Still **NOT FOUND** — but the room is much smaller as of 2026-08-14, because **rung S9 ran two agents, one per hypothesis, each told to refute its own, and BOTH SUCCEEDED.** *This section used to carry those two as the live pair with an experiment to separate them; neither survives, and the experiment it named cannot fire.*

**Hypothesis 1 — "`missionContext+0x230` is not our map id when `CompassMap` is constructed, so `+0x84` latches row 0's `+0x04` (continent 3) and asks world 3 for chunk (0,0)" — is REFUTED, four ways.** — OBSERVED.
1. **The pre-message value is 888, not 0.** `MsCliApi`'s context ctor writes `0x00855E3E mov dword [esi+0x230], 0x378` (and `+0x238 = 2 = MISSION_MAPS`), and the instance teardown re-writes the same 888 at `0x00856119`. **Row 0 is never reached.**
2. **Reading the sentinel is not silent, and it is not a fallback either — it is a crash.** `0x0084DE50` routes through the *asserting* accessor (`0x0084DE5E call 0x5a8580`), which asserts `ConstMission.cpp:3005 index < arrsize(s_missionClientData)` at `0x005A858F` and then indexes anyway (`0x005A85A3 imul eax, esi, 0x7c`). Row 888 lands on the `ConstMission.cpp` `__FILE__` string itself, so `+0x04` reads `0x5C65646F`. `0x005A93E0` asserts that too (`ConstWorldMap:1313`) and then hands it to the `s_worldData` accessor at `0x005A9403`, whose `×48 + 0xA36210` lands ~0x53A0_0000 — far past the last section — and `0x005A9415 cmp ecx, [edx+4]` dereferences it. The assert routine `0x00487BC0` returns and its reporter `0x00488210` has no early gate. **Two assert dialogs and then an access violation, on every map load.** Nothing of the kind is in this arc's record.
3. **The HUD builder is structurally downstream of the instance-load message:** `0x004E7E00` reads the map id (`call 0x84d9c0`), the map type (`call 0x84d9b0`) and `s_missionClientData[mapId]` (`call 0x5a8580`) as its first three acts, and `0x004E1254` branches on the observer bit that only the `0x0199`-class handlers set.
4. **On the wire, `0x0199` is the first s2c message of the instance** and every character/agent message that could trigger the HUD build arrives **0.56–0.91 s later — 9 of 9 live ArenaNet map connections and 8 of 8 recent sessions of our own server, 17 of 17.**

**Hypothesis 2 — "the texture load itself fails at `0x008C21C0`" — is REFUTED to the limit of static evidence, and the decisive argument is the fallback tile itself.** — OBSERVED. The constructor loads tile 9153 through **the same loader** (`0x008C1C96 push 0xba0368; call 0x679a90`) from the same archive in the same process on the same frame the compass is demonstrably drawing it. Beneath that: all **484 of 484** resolvable atlas tiles are `ATEX`/`DXT1` on four archives; every tile our six `maps.toml` slots touch resolves, decompresses whole and passes `atex.parse`, byte-identical across all four; and **0 of 888 area rows' footprints can reach one of the four 256×256 chunk tiles** (18 other world-3 cells are covered 1–7 times each, so the predicate is non-vacuous). Residual, named rather than waved away: a size- or id-dependent refusal inside `0x00470F50`/`0x00470B60` is **UNDECIDABLE STATICALLY** and unmotivated.

**`Gw.log` CANNOT separate them, and never could — the discriminator this section used to name is VOID.** `0x008C21EB cmp dword [ebp-4], 0xf; 0x008C21EF jne 0x8c21fb` puts the log call at `0x008C2203` on the **conversion** arm only: a failed load returns 0 at `0x008C21E4` with no log, and an already-DXT1 surface returns at `0x008C21F8` with no log. Since 484 of 484 tiles are DXT1, the line is unreachable for every world-map tile that exists, and its absence from all 26 `Gw.log` in the vault is exactly what a perfect load produces. Worse, `0x008C2203` is the **only** call to either logger (`0x0046ED40`, `0x0046EE30`) anywhere in the compass group `[0x008BB100, 0x008C5890)` — all nine translation units — and the loader beneath it returns 0 on both failure paths with no log at all. **There is no `Gw.log` evidence to be had in this subsystem, this run or any future run.** — OBSERVED.

**"The fallback" is SEVEN code paths, not one, and four are ordinary edge fill.** `codescan --xrefs 0x008C1E00` returns 7 direct references, 0 data words, all in `CompassMap.cpp`: the per-tile atlas failure `0x008C205F`; four edge fills `0x008C26AD` / `0x008C26D4` / `0x008C26FE` / `0x008C272A` (top, bottom, left, right margins); the `+0x68` override failure `0x008C2745`; and the degenerate-crop bail `0x008C28C3`. **So fallback pixels are normal on any map whose footprint does not fill the disc — only a WHOLE-DISC fallback is the fault rung S5 measured.** Two collateral corrections: `CompassMap:472` **cannot fire as a symptom**, because `0x008C202B je 0x8c2052` jumps over it when the surface is NULL and it blits anyway after asserting; and this section's "all four of map 148's tiles" should read **two** (116848, 116850) under the client's half-open loop `0x008C2807 lea edx,[eax+0x200]; cmp edx,ecx; jb` — §6's own earlier "148 2/2" is the right count, and all four are present either way.

**Where that leaves it, and the ONE cheap reading that discriminates.** With hypothesis 1 dead, `[CompassMap+0x84]` on map 148 is neither 1 (a picture draws) nor 3 (Elona's art draws — row 0 would have been *visible*, not blank), so the surviving values are `{0, 2, 4, 5, 7, 8, 9, ≥10}`, of which **0** is what a zeroed field gives:

| latched world | (1,1) | (2,1) | outcome on map 148 |
|---|---|---|---|
| 0 | NULL | NULL | whole-disc fallback |
| **1 (correct)** | 116848 | 116850 | a picture draws |
| 2 | NULL | NULL | whole-disc fallback |
| **3 (row 0's continent)** | 170536 | 170538 | a picture draws — the wrong continent's |
| 4, 5 | NULL | NULL | whole-disc fallback |
| 6 | NULL | 315586 | partial |
| 7, 8, 9, ≥10 | — | — | whole-disc fallback (no record / world bound) |

**THE THIRD HYPOTHESIS (opened by the S9 adjudication, 2026-08-14). The compass's ground layer is bounded by a LATCH-ONCE copy of the LOADED MAP's own cell dimensions, and where that latch does not cover the crop window, `0x008C1E00` tiles the fallback.** The mechanism is **OBSERVED**; that it is the cause is **UNVERIFIED**.

`0x008C28D0` — one direct caller (`0x008C22F0`, inside the draw entry `0x008C22E0`, itself one caller at `0x008BC695`) — is the surface init, guarded exactly the way `+0x84` is:
```
008C28DE  cmp dword ptr [ebx], 0
008C28E1  jne 0x8c29bc                  ; RUNS EXACTLY ONCE
008C2933  mov dword ptr [ebx], eax      ; the surface, which arms the guard
008C2939  call 0x70a5c0                 ; Engine\Map -- the LOADED MAP's world rect
008C293E..008C2952  [ebx+0x60..0x6c] = that rect
008C2955  fld [ebx+0x6c]; fsub [ebx+0x64]; fdiv qword [0x94de10]   ; (y1-y0)/96.0
008C296F  fld [ebx+0x68]; fsub [ebx+0x60]; fdiv qword [0x94de10]   ; (x1-x0)/96.0
008C298C  [ebx+0x50] = 0 ; 008C299A  [ebx+0x54] = 0
008C29A8  [ebx+0x58] = mapCellsX ; 008C29B2  [ebx+0x5c] = mapCellsY
```
`0x0070A5C0` is a four-dword copy of `[globalCtx+0x14] + 4..0x10` with no validity check and no return code. The crop function `0x008C2450` then **clamps every draw request against `[+0x50..0x5c]` first** (`0x008C2471..0x008C24D2`) and the atlas cell is the *clamped* coordinate plus the footprint origin (`0x008C2782 add edx, eax`, `0x008C2792 add esi, edi`, then `& 0xfffffe00`, `shr 9`). **An empty intersection takes `0x008C24E8 jle 0x8c268a` or `0x008C24F4 jle 0x8c268a` straight into the four edge fills, which with no covered region to exclude cover the whole strip** — branch structure OBSERVED, the coverage arithmetic RECONSTRUCTION, corroborated by ArenaNet's own shape at `0x008C2745`/`0x008C274A` and `0x008C28C3`/`0x008C28C8`, which fill the covered region and then jump to the same block. Two further bails to it exist inside the crop loop (`0x008C27BD jae 0x8c2684`, `0x008C27E7 jae 0x8c28a2`).

Two sub-forms, and only one explains a retail map:
- **H3a (timing) — the one the evidence supports.** If `[globalCtx+0x14]`'s rect is not populated when the first paint runs, `+0x58`/`+0x5c` latch to 0, the intersection is empty for every strip **forever** (latch-once never re-runs), and every map draws a whole-disc fallback including retail 148. This is hypothesis 1's *shape* — latch-before-ready — on a **different field from a different source**, which is exactly why the wire-ordering refutation above does not touch it: `0x0199` is a network message; the map rect comes from the archive load. Circumstantial: `Perf: Map file '0x0287d3' failed to load.  Attempting to re-bloat.` appears in **12 of the 26** `Gw.log` in the vault, so our sessions do not load maps on retail's schedule. **Counter-weight, stated:** the HUD is created from a controlled-character notify, which arrives after the instance loads, so the map is plausibly ready by then — H3a is not free.
- **H3b (dims) — a separate, later prediction that does NOT explain retail 148.** On an authored map our dims are 32/64/96 cells against a borrowed 416×512 footprint, so the compass crops the top-left 32×32 of the footprint and tiles the fallback everywhere else. **This is a live hazard for PLAN C2**, which is scoped as though the whole footprint is cropped.

**Trap for the next reader:** `[CompassMap+0x68]` (map rect x1, written at `0x008C294C`) and `s_missionClientData[map]+0x68` (the per-area texture, §3.5, read at `0x008C2513`) sit **forty instructions apart in one function** on different base registers. A `--field 0x68` sweep returns both and they are unrelated.

---

## 6b. The atlas reader, and the crop rendered offline

### 6b.1 `toolkit/clientscan/worldmap.py` — the reusable asset (rung S3, audited)

Walks the world-map atlas tables out of the pinned image and answers, for every `(tier, world, chunk_x, chunk_y)`, which archive file id holds that tile. **Stdlib only** (`argparse, json, os, re, struct, sys, pathlib` plus repo modules; no capstone, no pefile — carve-out (1) scopes those to two named files and this is neither).

**Every table is located structurally, never at a VA.** `s_worldData` comes through `consttable.table_for(pe, "s_worldData")` — a call, not a literal, and the sabotage that replaces it with `0x00A36210` reddens **9 checks**, two of them behavioural. Each tier's getter is found by a byte shape in `.text` that carries four facts which must agree: the `cmp edi, 0xa` world bound, the tier's own assert (`ConstWorldMap.cpp:1316` chunk / `:1338` parchment / `:1360` satellite — **the tier NAMES are ArenaNet's own word**, read out of `chunk.x < worldData.<tier>CX`), the `mov esi, <table VA>` immediate, and the CX field offset. The module **refuses** if a window is missing a witness, if the loop bound is not a whole number of 12-byte records, if two getters claim one tier, if a world bound disagrees with `s_worldData`'s count, or — the check with teeth — **if the CX offset used by the bound check differs from the one used by the index arithmetic**. Those are two instructions reading the same field for different purposes; a mis-parse moves one and not the other, and on the real image they agree, so **only a planted getter can see it — that sabotage reddens exactly one check and nothing else**. Without it the module would accept a build whose two reads disagree and index with whichever it happened to parse, and every coordinate downstream would be sourced, plausible and wrong.

| tier | table VA | getter | CX/CY | tier assert | count assert |
|---|---|---|---|---|---|
| chunk | `0x00A37390` | `0x005A9450` | +0x04 / +0x08 | `ConstWorldMap.cpp:1316` | `:1325` |
| parchment | `0x00A373E8` | `0x005A9510` | +0x0C / +0x10 | `:1338` | `:1347` |
| satellite | `0x00A37440` | `0x005A95D0` | **+0x18 / +0x1C** | `:1360` | `:1369` |

**Rung S3's four stated predictions were all MET** (409 chunk tiles / 7 worlds; trailing u32 = 0; ≥401 `ATEX`; the exact 8-id miss set), plus PLAN's "all 8 in worlds 0/1" (3 and 5) and "worlds 7/8/9 have no record". The two corrections in §3.1 — a third tier and the four 256×256 tiles — were *found* while measuring, not tuned for.

**The headline is deliberately the weak half and `test_worldmap.py` labels it `WEAK HALF:` in its own output**: "492 tiles over three tiers" is close to true by construction, since the module walks a declared count and emits the non-NULL slots, so an all-wrong reader prints 492 too. **Measured**: seven of the nineteen sabotages leave that headline green. What binds instead: `count == CX × CY` on 21 of 21 from two translation units 4 KB apart, **recomputed in the test** rather than read off the module's own `closes` (a `return True` sabotage reddens 2); 484/484 heads decompressing to magic `ATEX` on three archives with three different row counts; the exact 8-id miss set as a `frozenset` **literal in the test file**; a dword-early/late control written out of `struct.unpack_from` that collapses 484→0 in both directions with all 492 trailers going non-zero; and `consttable` asserted **behaviourally** — the fixture plants a second `s_worldData` under an alternate anchor with every dimension doubled and requires the grids to move to exactly those values.

**Three things scored `ALL CHECKS PASSED, exit 0` against the file as first delivered, and each is a scar this repo already owns** (independent audit, 2026-08-14):
1. **`main()` could stop calling the write guard entirely.** The syntax-tree checks parsed the file *on disk* rather than the module under `--module`, so every AST check was structurally exempt from the one mode the whole sabotage table is measured in — `test_atex.py` §3's "a guard can exist, be documented and be greppable while never being CALLED", one level up. Worse, the write here is `Path(out).write_text`, so the standard "every write-mode `open()` takes a guarded path" scan would have found **zero write sites and passed vacuously**.
2. **The emitted provenance stamped `build: 38797` as a constant** — condition 2 of the 2026-08-11 ruling ("the row records the build") satisfied in *form* while recording a literal, on a tool whose `--exe` takes any file and whose fallback is the owner's auto-updating install. The vault holds three 38797-sized images that are **not** 38797-as-shipped. Now measured per run from `pinned.identify()`, `None` when unidentified, with an `image` field beside it and a control that can fail in both directions.
3. **A reader that never read the trailing u32 passed everything**, because all 492 real records carry zero — the very fact PLAN S3 predicted. Only a fixture can close it: one planted non-zero trailer, required to come back as exactly that one.
A fourth check **could not fail** and was deleted: it asserted one-basedness of the row join, which `archive.py:367` already asserts internally and would have raised before returning. It is floor padding wearing an `iconset` label; two refutable checks replaced it (positional MFT size vs reported `stored`; the off-by-one row must name a *different* file id on all 484).

**Final state: floor 78, MEASURED with zero headroom; 65 with the client and no archive; 40 with neither — both degraded runs reach their verdict, name their skips and go RED. 19 one-edit sabotages built and run, all 19 redden.** *(Rung S3 reported 69/58/35 before the audit; those numbers are superseded.)*

**Extraction:** `vault/exports/worldmap/atlas-38797.json`, 492 rows, one per tile, keyed `(tier, world, chunk_x, chunk_y)`, `source = "client-table"` with extractor, build, image kind and the locating getter's own assert recorded **per row**. Ids and offsets only — no ArenaNet bytes, no authored text. Deliberately **not** a `vault/content/` overlay: that directory is merged into `content.load()` for the *server*, and a 492-row texture index is not world content.

### 6b.2 The crop scale is ONE TEXEL PER TERRAIN CELL — OBSERVED (rung S5)

*This was RECONSTRUCTION and §7 recorded it as an open UNVERIFIED.* Two independent witnesses, and four rival scales collapse.

**The code.** `CompassMap.cpp`'s crop at `0x008C2450`, eight instructions after the footprint branch of §3.3:
```
008C2788  add edx, eax          ; atlas x0 = local x0 + footprint.x0
008C279A  add eax, edi          ; atlas y0 = local y0 + footprint.y0
008C279C  and edx, 0xfffffe00   ; floor onto the 512 grid
008C27B2  shr edx, 9            ; /512 -> the tile index
```
The footprint origin is **added to** the crop's local coordinate, so the two share one unit; a tile is **512** of that unit. A chunk tile is 512×512 texels (§3.1, and `CompassMap:472` bounds at 512) and the footprint is in terrain cells (`maprows.py`'s join, footprint size == map rect / 96.0 on **319 of 319**, one-cell shift → 0/319). ∴ 1 texel = 1 terrain cell = 96 world units. The alternatives die on the same arithmetic: 2 px/cell needs `shr 10`, 0.5 needs `shr 8`, and a per-map scale derived from `chunkCX*512 / footprint size` **cannot exist at all** — 631 footprints of many different sizes index one shared 512-grid.

**The population, two tests neither our decoder nor the client's can force** (tile NULL patterns from the slot arrays, footprints from a table 4 KB away):

| texels per cell | continents whose touched-tile set EQUALS a world's tile set | rows fully covered (of 631) |
|---|---|---|
| 0.25 | 0 | 2 |
| 0.5 | 0 | 144 |
| **1.0** | **5** — c0=w0 (202), c1=w1 (17), c2=w2 (44), c4=w4 (71), c5=w5 (15) | **629 (99.7%)** |
| 2.0 | 0 | 12 |
| 4.0 | 0 | 0 |

The two failures at 1.0 are rows **254 and 255** only, both continent 3, both carrying a footprint out at x ≈ 7,264 that no 2048-wide grid can hold — reported, not trimmed; excluding them, continent 3 is a clean subset of world 3. **Kamadan alone reproduces it**: 100% covered at 1.0, **0.0% at both 0.5 and 2.0**, where the crop lands entirely on NULL slots and produces no image at all.

### 6b.3 What the crop actually looks like

Rendered through `worldmap.py` → `archive.raw` → `gwdat.decompress` → `atex.parse` → `atex.decode_level` → `atex.blocks_to_rgba` → `png.write`, **no stage refusing on any tile touched**. (PLAN S5's pipeline line named an `atexlevel.decode_level`; there is no such module — the level codec lives in `toolkit/mapdata/atex.py:550`, and `dxt1.decode` is reached through `blocks_to_rgba`.) Area 449 (Kamadan) crops to a tropical island city on turquoise water with docks and a walled compound; area 148 to Pre-Searing Ascalon with walls, roads, rivers and portal glyphs. **The crop is a recognisable picture — that half of rung S5's prediction is MET.** The other half could not be run: see §6 above and §7.

Images in `vault/exports/worldmap/` (never the repo): `area449_w4_s1_416x448.png`, `area148_w1_s1_416x512.png`, `area143_w1_s1_320x544.png` (the rival), `area144_w2_s1_352x640.png`, both rival-scale Kamadan renders (261 B and 3 KB of nothing), `compass_fallback_9153_64x64.png`, `world1_full_2048x4096.png`, and `s5_comparison_sheet.png`.

---

## 6c. When the map rect is written — H3a is DEAD, and the latch's numbers on map 148 are now known (rung S12, 2026-08-14)

**The rung's question was "is `[globalCtx+0x14]`'s rect populated by the synchronous map parse, before the compass's first paint?" The answer is yes, three independent ways — and the measurement kept going and produced the arc's first complete candidate explanation for the whole-disc fallback.**

### 6c.1 The context slot, and its exactly-two writers

`0x0047F660` — the getter `0x0070A5C0` opens with — is not a global read; it is **per-thread**: `mov ecx, [0xC0F300]` (a TLS index), `fs:[0x2C]`, then `[slot + 8]`. The setter is its twin at `0x0047F680`. It has **1,089 direct call sites** image-wide, so the slot was found by the rung-S10 method — a conservative forward window from every call site, tracking which registers hold the returned context (copies propagate, calls clobber eax/ecx/edx, any other def kills the track). Result, over all 1,089 windows:

- **`[ctx+0x14]` is WRITTEN at exactly two sites**: `0x00707CC4 mov [eax+0x14], esi` (the install) and `0x0070984C mov [eax+0x14], 0` (the clear). 72 sites read it.
- The install lives in `P:\Code\Engine\Map\Map.cpp` (its own assert: `Map.cpp:730 map`), in the function at `0x00707BB0`: `call 0x713360` (build), assert the result non-NULL, destroy any old map (`0x007140C0`), **then** store the new pointer. **The object enters the slot only after it is fully built.**
- The window method's stated limit: a writer that receives ctx as an *argument* is invisible to it. Mitigated two ways — a four-displacement `--writes` sweep over all of `P:\Code\Engine\Map\` (below) found no other candidate, and `MapIsCreated()` (`0x007098A0`, the function `UiGame:1051 !MapIsCreated()` calls) reads the same slot, which is what makes the two-writer count consistent with everything UiGame asserts.

**A spelling correction that cost this rung twenty minutes and will cost the next reader more: the module prefix is `P:\Code\Engine\Map\`, not `P:\Code\Gw\Engine\Map\`.** PLAN S12's own procedure line had the `Gw\` form; `codescan --bounds` answers *"no asserts, so no bounds"* for it — a silence, not an error — and every `--in` scoped to it returns a confident zero. The real prefix spans `0x00707434..0x00775976`, 77 source files, 721 assert sites.

### 6c.2 The build is a synchronous chunk loop, and the rect writer is chunk `0x2000000C` — the chunk `mapbuild.py` already encodes

`0x00713360` (MapData.cpp) is the **map build driver**: it allocates the 0x138-byte Map object (`Map.cpp`'s ctor `0x00707280` — which initializes array headers at `+0x2C..` and `+0x90..` and **never touches `+4..0x10`**), then walks the file's chunk records **in a loop, dispatching direct calls** through `s_chunkInfo` (`0xA6CF78`, stride 0x28, 23 rows, bound by MapData's own `ptr->id < arrsize(s_chunkInfo)`), with an `MsProgress.h` task list driving the loading bar. No thread hop, no completion callback: the driver returns the finished object, and `Map.cpp:730` installs it.

The rect writer is **chunk id 12**, and its handler is three instructions:

```
007129D0  mov ecx, [ebp+0x18]     ; the Map object (5th handler arg)
007129D6  push dword [ebp+8]
007129D9  lea ecx, [ecx+4]        ; &map->rect
007129DC  call 0x70d780           ; MapParams.cpp -- the ONE caller image-wide
```

`0x0070D780` (MapParams.cpp, asserts at `:198`-class lines) divides the chunk's dims by **3072.0** (= 32 cells × 96.0 — one terrain chunk in world units, the double at `0xA6C7B0`), asserts the result is a whole number of chunks, multiplies back, and writes the four floats to `[map+4..0x10]` plus flags to `[map+0x14]` — the flags the terrain handler then passes to `TrnCreate`. `codescan --xrefs 0x0070D780`: **1 direct reference, 0 data words.** And the parser beside it (`0x0070D920`) checks magic `0x5943EEEF` and version byte 2 at offset +4, floats at the unaligned +5 —

**which is `toolkit/mapdata/mapbuild.py`'s `MAP_PARAMS_CHUNK = 0x2000000C`, sig `MAP_PARAMS_SIG = 0x5943EEEF`, `MAP_PARAMS_VERSION = 2`, `_MP_RECT` at +5, byte for byte.** The client-side rect writer and our file-side encoder are one chunk read from two directions; the file-format arc (customarea FINDINGS 17.4) and this arc meet here. Consequences carried:

- **Our authored maps DO write the rect** — mapbuild generates `0x2000000C` with the authored dims, so an authored map's latch gets our dims. That is H3b's premise, now with the writer named rather than presumed.
- Corroboration from structure: chunk 2 (terrain) asserts `!map->terrain`, passes **`&map->rect` and `[map+0x14]`** into `0x00758540`, and derives its chunk grid from the rect (`>>5` on the cell dims). A rect-less build would malform terrain; every vault frame that shows terrain rendering is therefore also evidence the rect ran.
- Residuals, named: the driver has an **empty-chunk-list early return** (`0x007133F9 je 0x713625`) that hands back an object whose rect no chunk ever wrote — unreachable for retail 148 and for our builds (mapbuild always emits `0x2000000C`), but it exists; and whether the allocator (`0x0047F490`, flags=2) zero-fills is **UNVERIFIED**, which only matters on that path.

### 6c.3 The ordering, three legs, all static

1. **The compass's own source has no NULL path.** `0x0070A5C0` is `getter → [ctx+0x14] → read [+4..0x10]` with **no test of the pointer** — a paint before any install dereferences address 4 and crashes. 26 sessions in the vault, zero such crashes, and the §23 fallback frame is `CompassMap` *itself* painting — so the latch ran, so the slot held a **fully-built** map at every first paint that ever happened. The NULL-deref is the guard that makes the ordering self-proving for a populated rect.
2. **The build is driven synchronously from the instance-load network path.** The map build runs in UiGame's frame proc (`0x004A69C0`, the proc `UiRoot` registers at `0x004A369A`) on **frame message `0x10000098`** (two-level MSVC jump table at `0x004A76A0`/`0x004A76D4`; case `[3]` at `0x004A6E23` → `call 0x707bb0` at `0x004A6E45`). That message has **one poster**: `0x00853BFD` in `0x00853BA0` (MsCli*, beside `MsCliProgress.cpp`'s asserts), called from `0x0084ED90` and `0x0084F271` — the same MsCliApi region whose `+0x230` store rung S9 pinned for the `0x0199` family. And the send is **synchronous, not queued**: `0x00633D70` asserts the id and tail-jumps into the broadcast walk (`0x0064CA30`), and the poster passes **stack-local out-slots** in the args and reads the answer the instruction after the call returns — a queued dispatch would be a use-after-return. So build + install complete inside the network dispatch of the instance-load family.
3. **The HUD is a later message.** Rung S9 already measured the compass's creation downstream of the controlled-character notify, and `0x0199` preceding every character/agent message by 0.56–0.91 s on the wire, 17 of 17. First paint ≥ constructor. UiGame's create arm also **asserts `!MapIsCreated()`** (`UiGame:1051`, calling `0x007098A0`) and then subscribes to the message set including `0x10000098` — no map exists when UiGame arrives; the map arrives on the wire's schedule; the compass arrives after that.

**H3a — "the latch runs before the rect is populated and captures zeros" — is DEAD.** The rect is final before the object is visible to any reader; a paint before the object exists crashes rather than latching; and the paint provably comes later anyway. The re-bloat lines in 12 of 26 logs move *when* the build succeeds, never the order — a failed build installs nothing (`UiGame` bails on the NULL), so re-bloat cannot open a window where the latch sees a half-built map.

### 6c.4 What the latch actually latched on map 148 — and it kills H3 for retail 148 too

**READ THE ERROR FIRST, because it was committed, merged, and caught by the next measurement rather than by review.** This section first claimed map 148's file is **64 × 64 cells, rect ±3072**, that the 416×512 footprint was therefore a region-sized borrow the latch would clip to a corner, and — building on that — that our server's spawn at `(9826, 8077)` lands *outside* the map's own rect and is the cause of every fallback frame. **All of it was wrong, and from a single root cause: `0x0287d3` is not map 148.** It is the customarea arc's **authored sculpt map** — which is exactly why the re-bloat line names it (our authored maps are the ones that fail to load and re-bloat; retail maps do not), and the `Gw.log` quote in PLAN S12's own procedure line is what made it look like map 148's id. Map 148's file id is in the content row all along: `file_id = 0x8001B97D`, masked `0x1B97D`. The lesson is the arc's own house rule turned on itself — **a file id read out of a log line is a claim, not an identity**, and the row that carries the id was one `grep` away.

**The corrected measurement.** `mapexport.py --file-id 0x1B97D`:

- **grid 416 × 512 cells; rect `(−18432, −24576, 21504, 24576)`; extent 39936 × 49152 at pitch 96.0.**
- `(21504 − (−18432)) / 96 = 416` and `(24576 − (−24576)) / 96 = 512` — **exactly the area row's footprint.** Map 148 *is* one of `maprows.py`'s 319-of-319 join rows; the previous text's "148 is simply not among them" was an artefact of the wrong file.
- Our spawn `(9826, 8077)` sits at cell **(294, 340)** of that 416×512 grid — comfortably inside, and consistent with the content row's own provenance note (it lands in exactly 1 trapezoid of that mesh, 0 of Kamadan's).

**So the latch on map 148 holds `[+0x58]/[+0x5c] = (416, 512)` and `[+0x60..0x6c] = (−18432, −24576, 21504, 24576)` — the FULL footprint, not a clipped corner.** — OBSERVED on the file side; the memory read is still C1's.

**Consequence, and it is the real result of this rung's second half: H3 cannot explain the fallback on retail map 148 either.** The crop window clamps against a rect that covers the whole footprint, so the intersection is non-empty everywhere the compass asks — there is no degenerate crop to take. With S9 having refuted H1 and H2, and S12 refuting H3a (ordering) and now H3 itself (dims, on this map), **all three named hypotheses are dead for retail 148**, which is C1's own third branch reached statically and for free:

> `[+0x84] == 1` **and** `[+0x58]/[+0x5c] == (416, 512)` → all three hypotheses dead; the fault is downstream of the crop, in the blit at `0x008C2077` or in rung S5's own metric.

**H3b survives untouched for AUTHORED maps, and the sculpt-map export quantifies it** — that file really is **64 × 64 cells, rect ±3072**, against a borrowed 416×512 footprint, so an authored map's compass can only ever crop a 64×64 corner. PLAN C2's hazard note stands; only its retail-148 half is withdrawn.

**What C1 should now predict, and what it is really for:** `[+0x84] == 1`, `[+0x58]/[+0x5c] == (416, 512)`, `[+0x60..0x6c] == (−18432, −24576, 21504, 24576)`. If the live object reads that way, the memory half has *confirmed everything upstream is healthy* and the entire remaining question is downstream — the per-slot tile load at `0x008C21C0`, the blit at `0x008C2077`, or S5's metric. Any other reading is a genuinely new finding and names its own next rung. **The spawn arm proposed here is VOID** — the spawn is inside the rect and there is nothing to move.

**One lead closed in passing, so the next reader does not chase it:** `[CompassMap+0x80]` — §7's "UNREAD", loaded at `0x008C1FF9` immediately before the tier getter — is **not** an input to the getter. It is written into the per-slot cache record at `[ebx + esi*8 + 0x14]` while the getter's arguments are `[+0x84]` (world) and `edi` (the chunk pair); the constructor zeroes it (`0x008C1C6B`, with `edx` already decremented to 0 by the init loop above it) and `0x008C2A9E inc dword [edi+0x80]` bumps it. It is a **cache generation stamp**. — OBSERVED.

---

## 6d. THE COMPASS DRAWS THE ATLAS — the fallback is not a property of our server (rung C1, first client run of this arc, 2026-08-14)

**The arc's leading question is answered, and the answer is that the premise expired.** *§6 above asks "why is the compass image NULL under our server, even on retail map 148 with the tiles present?" and §0, §6 and PLAN all carry the fallback as a standing fact about our server.* **It is not one.** On **build 38833 against its own archive generation**, retail map 148, our DH, caged, loopback, no probe, no `--enemy`, the compass renders a **recognisable crop of the ATEX atlas** — green fields, walls, roads, water, the player's dot inside the Danger Zone circle. — OBSERVED, one session, five consecutive frames.

**The measurement, with the control that makes it a measurement.** The metric is §6's own chromatic ratio `χ = (R−G)/(G−B)`, sampled over an annulus `28 ≤ r ≤ 72` px about the compass centre `(1808, 153)` — the inner radius excludes the Danger Zone disc. Both frame sets are 1936×1040 with the client window in the same place, so **one disc, one code path, two populations**:

| frames | median RGB | median χ |
|---|---|---|
| `20260811T161925/hold001..004` — the six-frame fallback set §6 measured | (88–90, 57–58, 29–30) | **+1.154 … +1.160** |
| `20260814T225013/hold001..005` — **this run** | (92–94, 78–81, 32) | **+0.250 … +0.279** |
| *(S5's published bands, for reference)* | fallback tile 9153 **+1.164**; six vault discs **+1.081 … +1.110**; **map 148 atlas crop +0.286** | |

The control is the load-bearing half and it was run *first*: the same code, on the same disc, over frames §6 already classified, **reproduces the fallback band** (+1.154..+1.160 against the tile's +1.164). Only then does the new run's +0.250..+0.279 mean anything — and it lands on **map 148's own atlas-crop prediction of +0.286**, computed offline by rung S5 months of reasoning earlier and never fitted to a frame. A ~1.15-vs-~0.26 separation on a metric whose null was measured on this machine, this week, with the same sampler.

### 6d.1 What actually changed, and the honest boundary on WHY

**Three variables moved between the fallback corpus and this run, and this rung separates none of them:**

1. **Client build** 38797 → **38833** (`vault/run/2026-08-13_64fae3b1369b`, ours-DH, `[ok]` under `dhbuild.py`).
2. **Archive generation.** Map 148's file is a genuinely different file: old row **7982**, 1,300,036 B, crc `0xA0AE500A`; new row **177262**, 1,300,044 B, crc `0x33F1A289`. Eight bytes larger and a different checksum — the replacement `FcArchive`'s bit-31 rename had been promising.
3. **The file id form sent in `0x0199`** — `0x8001B97D` (renamed) → `0x1B97D` (plain), following `content/maps.toml`'s 2026-08-14 correction.

**So "the 38833 client fixed it", "the new map file has something the old one lacked", and "the old runs were sending an id whose file the client resolved differently" are all live, and this run votes for none.** Attribution is the next rung, not this one. What *is* settled is the negative that mattered most: **the whole-disc fallback is not a structural property of our server, our DH, our handoff or our `0x0199`** — the same server code, the same synthetic account and the same map id now produce the atlas. PLAN risk 7 ("the compass may never draw the atlas under our server at all") is **RETIRED**.

### 6d.2 The 38797 arm failed, and its failure is a separate OBSERVED result

The first attempt used the 38797 client against `dat_study` and reached **Code=007** at the character screen. The ladder shows exactly where: auth keyed, `PORTAL_ACCOUNT_LOGIN`, login accepted, game instance requested, **game channel opened and keyed**, server sent `INSTANCE_LOAD_HEAD` / `PLAYER_DATA_START` / `INSTANCE_LOAD_PLAYER_NAME` / `PLAYER_DATA_DONE` / **`INSTANCE_LOAD_INFO (0x0199, 15B)`** and loaded its navmesh (`58 planes, 6120 trapezoids`) — then `ConnectionResetError 10054`, **the client hanging up immediately after `0x0199`**. The client's own `Gw.log` stops at the auth phase, 18 lines, with no map-load line at all.

**The cause is the id form, measured on the raw table rather than inferred.** Reading MFT row 2 without `file_id_table()`'s dual registration:

| archive | `0x1B97D` raw | `0x8001B97D` raw | bit-31 ids |
|---|---|---|---|
| `run/2026-07-29_221c13772c7a` (38797) | **absent** | row 7982 | 29 |
| `dat_study` | **absent** | row 7982 | 25 |
| `run/2026-08-13_64fae3b1369b` (38833) | **row 177262** | absent | **0** |

`archive.py`'s own docstring states the rule this confirms — *"THE CLIENT DOES NOT MASK"*, an exact 32-bit compare at `0x0047AA20` with no retry on the map path. So a 38797 client handed the plain id **misses**, and `content/maps.toml`'s corrected plain id is right **only for the generation where the replacement is installed**. The 38833 archive carrying **zero** bit-31 ids is the same fact from the other side: that copy has no pending replacements left.

### 6d.3 A hole in the `contentids` guard, found by walking into it

**`toolkit/contentids.py` cleared the pair that then failed.** It reported `10 of 10 map row(s) agree` for 38797-client-vs-`dat_study`, comparing **server row 7982 to client row 7982** — because it resolves through `archive.file_id_table()`, which *deliberately* registers a bit-31 id under both its raw and masked forms. That dual registration is correct for finding a row and **is not a model of the client**; `archive.py` says so in the same docstring. The guard therefore validates *our reader's* opinion of the id, not the client's, and is blind to the one failure it exists to catch: an id the server will happily resolve and the client cannot.

The fix is not to change `file_id_table()` — its convenience is load-bearing elsewhere. It is for `contentids` to compare on the **raw** table, and to fail when the id `content/maps.toml` will actually put on the wire is absent from the client's archive in the exact form it is sent. **UNFIXED as of this writing** and carried into PLAN §8.

### 6d.4 Two caveats this run must carry

- **The server ran without a navmesh.** `[map] no navmesh for 0x1B97D: [Errno 13] Permission denied: '…run\2026-08-13_64fae3b1369b\Gw.dat'` — pointing `RURIK_DAT` at the *client's own* run-directory archive makes the two contend, and the client holds it open. The run still reached `body is in the map` and the compass result is unaffected (the ground art is drawn by the client from its own archive), but **nothing about pathing or collision was server-validated in this session.** The correct configuration is a **separate copy** of the post-update archive for the server. This is `customarea` §59.3's two-run rule in a new form.
- **Screenshot capture is foreground-gated.** Four of nine `--shots` were skipped as `client not foreground`, and the first arm's `final.png` too. Frames that do land are fine; a run that needs *N* frames should not assume it gets them.

### 6d.5 What this does to the ladder

- **C1's diagnostic purpose is discharged** — not by the `ReadProcessMemory` read it specified, but by the cheaper thing the run made possible: the fallback stopped reproducing, so there is no longer a NULL image to diagnose. The three-dword RPM read is **not** wasted and is now a *confirmation* rung rather than a diagnosis: `+0x84 == 1` and `+0x58/+0x5c == (416, 512)` should now be *visibly* true, and reading them would close §6c.4's file-side prediction against the live object. Demoted from blocking to optional.
- **C2 and C3 are UNGATED.** Both were held behind "an arm whose two halves both draw the fallback is satisfied vacuously". The compass now draws a crop that visibly changes with the map, so both arms have an instrument. C3's 20-row population and C2's world-1-vs-world-2 arm are unchanged.
- **Tier 3's cost question is reopened in the good direction.** Risk 7 warned that if the cause were structural, A1 and A2 would have no point. It is not structural.
- **H3b is untouched.** It was always about authored maps, and this run was retail 148.

**Artefacts:** `vault/captures/harness/20260814T225013/` (five `hold*.png`, `final.png`, `report.json`, three server logs); the failed 38797 arm at `vault/captures/harness/20260814T224512/`. Both are loopback, synthetic credential, `origin = ours`.

---

## 6e. WHY it was NULL: 22 of the 492 atlas tiles were not addressable by the id the client asks for (rung S13, 2026-08-14, static)

> **CORRECTION, same day, before this section had been read by anyone — and it makes the mechanism STRONGER while killing the framing.** As first written this section attributed the fault to the archive **generation** (38797-era copies broken, build 38833's fixed) and rung S13 recorded that *"the refutation clause did NOT fire … no 38797 client drew the atlas."* **That is false. The refutation clause fired.** A population sweep of every harness session carrying a frame found **4 of 320** sessions (scored on hold frames) in the atlas band, and **three of them are build 38797** — `20260813T012916` (χ +0.129), `20260813T013033` (+0.125) and `20260813T103437` (+0.125), all map 148, all visually a full Ascalon crop.
>
> **And the pair that settles it is better than anything this rung designed.** `20260813T103437` (**atlas**) and `20260813T105432` (**fallback**) ran **twenty minutes apart from the SAME run directory** — `vault/run/2026-07-29_221c13772c7a`, the same `Gw.exe`, the same archive path. Same binary, same file, opposite compass. So the variable is not the generation of anything: it is **the armed state of the client's own archive, which changes over the archive's life** — `FcArchive` arms a row when it *requests* a replacement, and the client writes its own `Gw.dat`. The arming happened between 10:34 and 10:54 on 2026-08-13, and every session after it draws the fallback until build 38833 installs the replacements.
>
> **What this changes:** the tile-addressability MECHANISM below is confirmed and now rests on a natural experiment that holds the client fixed, which is far stronger than the static build diff in §6e.2 (that diff is now corroboration, not the argument). What is withdrawn is "38797 is broken and 38833 is fixed" — **38797 drew the atlas perfectly well until its archive was armed.** Read every "generation" below as "armed state at the time of the run".
>
> **A limit of the sweep, stated because it nearly produced a second false claim:** 188 sessions scored χ ≈ **+0.529**, which is not a compass at all — those were measured from `final.png`, which is usually the character-select screen, and the disc samples UI. Only the **320** sessions with a `hold*.png` are scored above; the other 300 are excluded, not counted as either band.

**The cause is found, it is one sentence, and it is the same defect three times over: in the archives every fallback session played from, map 148's world-map tiles carry bit 31 — the "replacement pending" rename — so the PLAIN id the client's own tile table holds does not bind, the exact 32-bit lookup misses, `ConstWorldMapGetChunkFile` returns NULL, and `0x008C1E00` tiles the fallback over the whole disc.** — OBSERVED, measured on the raw id table of five archives.

| tile (map 148, world 1) | `run/38797` plain | armed form | `run/38833` plain |
|---|---|---|---|
| 116848 | **absent** | `0x8001C870` → row 44717 | row 44716 |
| 116850 | **absent** | `0x8001C872` → row 44718 | row 44717 |
| 116854 | **absent** | `0x8001C876` → row 44720 | row 44718 |
| 116856 | **absent** | `0x8001C878` → row 44721 | row 44720 |

Identical in `dat_study`, `run/…-c2` and `run/reskin-roster`. **The client does not mask** (`0x0047AA20`, exact 32-bit compare, no retry — `archive.py`'s own docstring), so all four miss.

**Scope, over the whole atlas** (`vault/exports/worldmap/atlas-38797.json`, 492 tiles, joined to each archive's raw table):

| archive, **as it stands on 2026-08-14** | tiles the client can address | misses | misses by world |
|---|---|---|---|
| `run/2026-07-29…` (armed; every fallback session after 08-13 10:54) | **470 / 492** | **22** | **world 1: 18, world 0: 4** |
| `run/2026-08-13…` (replacements installed) | **492 / 492** | **0** | — |

**These are readings of the archives TODAY, not properties of the builds.** The same `run/2026-07-29…` copy served three atlas sessions earlier on 2026-08-13 — see the correction above — so its 22 misses are a state it entered, not a state it shipped in.

**And that is exactly the right 22.** Map 148 is **world 1** (§7, rung S4), and so are 143 and 146 — the three maps §6's fallback corpus was drawn from. Every frame in that corpus is a world-1 map, and world 1 is precisely where 18 tiles were unaddressable. Kamadan (449, world 4) was never served, so the one continent that would have drawn normally never got the chance. The premise "the compass never draws the atlas under our server" was a survey of a single broken continent.

### 6e.1 The measurement S9 got wrong, and why it could not have caught this

§6 states, and this document has repeated it as OBSERVED: *"all four of map 148's tiles present in the archive the client opened"* and *"484 of 484 resolvable atlas tiles are `ATEX`/`DXT1` on four archives … byte-identical across all four."* **Both are true and both are irrelevant, because they were resolved through `archive.file_id_table()`** — the helper that *deliberately* registers a bit-31 id under **both** its raw and its masked form. Asked for tile 116848 against the old archive it answers **row 44717**; the client asked the same question and got nothing.

The rows were always there. They were never **addressable by the id the client uses**. Presence was the wrong predicate, and the tool that answered it is documented as not being a model of the client — in the same file, in the docstring above the code that does it.

**This is the third thing the same helper has hidden, and the three should be read together:**

1. `content/maps.toml`'s map **file** id — caught 2026-08-14 by the crossbuild arc, which is why the row now reads `0x1B97D`.
2. **`toolkit/contentids.py`** — cleared the 38797 pair that then died at Code=007 (§6d.3). Still UNFIXED.
3. **This** — rung S9's tile-presence check, and through it the whole arc's leading question, which cost S9, S12, C1 and S13 to unwind.

**The fix is the same one in all three places: ask the raw table whether the id binds *in the form it is sent*.** A `file_id_table(raw=True)` or a `binds_plainly(archive, file_id)` helper would have made each of these a one-line check.

### 6e.2 What this does to the three named hypotheses, and to S9's H2

**S13 predicted the ARCHIVE and proposed the map file's rect as the mechanism. The archive half is right; the rect is REFUTED; and "generation" is the wrong noun — it is the archive's ARMED STATE, which varies over one copy's life** (see the correction at the top of this section: one directory, twenty minutes, both outcomes). Both halves matter:

- **The map file is NOT it.** Row 7982 and row 177262 decompress to 2,925,270 and 2,925,267 bytes; the **height field is byte-identical** (sha256 `f9bd7848…` both); `MAP_PARAMS 0x2000000C` is 41 bytes in both with **the first 25 — the whole rect — byte-identical**, differing only in a trailing 16-byte version-4 GUID; `0x20000008` differs by **one** byte; `0x20000002` by 670 of 1,735,664 in one contiguous tail span. Grid 416×512 and rect `(−18432, −24576, 21504, 24576)` in **both**. The latch had the same input all along.
- **The client build is NOT it — and the natural experiment above says so before any disassembly does.** One build, one archive path, twenty minutes, both outcomes. The static agreement is now corroboration: all twelve `CompassMap.cpp` asserts are identical in 38797 and 38833 — same lines (164, 165, 288–291, 381–384, 401, 472), same expressions — and every one is displaced by **exactly +0xA0**. Comparing instruction streams under that displacement: the constructor, the crop, the surface-init latch and the fallback tiler all have **identical instruction counts and ZERO mnemonic mismatches**; the operand-only differences are relocated branch targets. The compass's data is identical too — the footprint table base `0x0096DE38`, `s_worldData`, the chunk-tile table head and world 1's tile array head are all **byte-identical** between builds.
- **The map-type byte is NOT it.** Map 148's `FOOTPRINT_A` and `FOOTPRINT_B` are the same rect `(768, 512, 1184, 1024)`, and a run with `--explorable` forced (the flag the old fallback sessions used) **still drew the atlas** — see §6e.3.
- **S9's hypothesis 2 was right in substance and refuted for the wrong reason.** It said "the texture load fails" and was killed on the argument that the fallback tile was loaded *by the same loader, from the same archive, on the same frame*. That argument is sound and the conclusion was still wrong, because the failure is **upstream of the loader**: the lookup never yields a row to load. S9 named the residual as "a size- or id-dependent refusal … UNDECIDABLE STATICALLY". It was **id-dependent**, and it was **decidable statically** — by reading the raw table instead of the helper.

### 6e.3 A second, smaller result the control run produced: the ground layer arrives LATE

The `--explorable` run was scored on three frames and they are not all alike: `final.png`, taken at the map verdict (~t+10 s), reads **χ +1.182 — the fallback band**; `hold001` (~t+18 s) **+0.403**; `hold002` (~t+26 s) **+0.250 — the atlas**. The first atlas run shows the same shape more weakly (`hold001` +0.279, then +0.250 flat).

**So the compass draws the fallback first and converges to the atlas once the tile load completes** — mechanism UNVERIFIED, but the ordering is OBSERVED on two runs. Consequences: a single early frame is **not** evidence of a NULL image, and §22's "small square minimap" plus any frame caught near the load overlay should be re-read with that in mind. Sampling must be late, and a run that reports one frame reports nothing. *(This does not rescue the old corpus: `20260813T222031` holds **8** frames at a flat +1.154 over the whole hold, and its tiles were unaddressable the entire time.)*

### 6e.4 The one thing that is still open

**Why those 22 rows were replacement-armed in the owner's archives is NOT FOUND**, and it is an ArenaNet-side question about how `FcArchive` requests and `DnArchive` installs replacements — not something our server does. What matters operationally is settled: **an archive with armed atlas rows draws a fallback compass on every map of the affected world, and no amount of server-side work changes it.** The check is one line and belongs in the pre-flight.

---

## 7. Contradictions and open questions

**Cross-report contradictions, surfaced rather than silently resolved:**

1. **CLOSED 2026-08-14 (rung S8) — the fog/exploration opcode.** Two agents, two independent routes, rival answers withheld from both, **agreeing on every VA, every partition and all five live counts**: `0x008C` owns `0x00811D12` as the sole caller of `0x00811BE0`; the init stream is `0x008B` (declare) + `0x008A` (payload); `ChCliApi:1641` belongs to `0x008A`; `0x0089` is an AgentView mannequin message and not in this subsystem. §4.2 carries it, including the `asserts.py --at` 2,000-byte-window trap that manufactured the wrong reading.
2. **CLOSED — the c2s draw opcode.** Recon searched *names* (correctly none); the deep dive located the *sender*. Re-established twice more under rung S6 by a confirmer and an adversary working independently, including a value-first sweep of all 134 materialisations of `0x2b` in `.text`: exactly **one** instruction sits inside any send-call body. §4.1, and the surviving `name_confidence` is **medium** for the c2s half — see §4.1's naming note.
3. **CLOSED — the §22/§23 minimap appearance** (§6): §22 is a load-overlay artefact and §23 is the NULL-image fallback tile 9153, both frames located, opened and measured.
4. **`0x0093`'s live sample count:** `studies/recon/FINDINGS.md:540-543` says 9, a fresh full-live-corpus decode (recon 2) gives 2. CONTESTED; neither chased down. Not minimap-load-bearing, recorded for the next reader.
5. **`0x0199` "third dword" (task premise) vs `byte` at field index 3** (§3.3) — corrected to the byte; RESKIN's "dword" is the memory slot.

**Open questions / NOT FOUND (auditable negatives):**

- **CLOSED 2026-08-14 (rungs S4 and S5, independently) — the compass's world index, and the `continent → world` map is the IDENTITY.** *This bullet used to read "read, never traced to a writer … NOT FOUND."* The chain, whole: `GAME_SMSG 0x0199` field 2 → `0x0084EE5C` → `missionContext+0x230` → `0x0084DE50`, four instructions long and exactly `s_missionClientData[missionContext+0x230] + 0x04` → `0x008C1C78 mov [compassMap+0x84], eax` (the constructor, the **only** direct-displacement writer inside `CompassMap.cpp`'s allocation) → `0x008C2004 push [ebx+0x84]` → `0x005A93E0`, whose first act is `cmp edi, 0xa` guarding `ConstWorldMap:1313 world < WORLDS`. **No lookup table, no offset, no remap.** — OBSERVED. So an offline renderer's only input is the map id, and the world does **not** come from the map file, the archive, or anything our server can vary except that one word.
- **Consequently `s_missionClientData +0x04` is no longer UPSTREAM — it is CORROBORATED from the client's own code**, on three witnesses of which the histogram is deliberately the weakest: the field is passed *unmodified* into a function that bounds it by `WORLDS`; `GmMapWorld` at `0x0054E900 cmp [edi+4], eax` compares another row's `+0x04` against `0x0084DE50`'s return as "same world"; and `max = 9 < 10` over all 888 rows. Why the third is weak, measured rather than asserted: **five** of the record's 31 dword fields are always < 10 (`+0x00`, `+0x04`, `+0x18`, `+0x20`, `+0x2C`), so a range test identifies nothing and only the code names the field. The **NAME** "continent" stays ArenaNet-unattested — `asserts.py --grep '(?i)continent'` returns **0 sites** against that tool's 370-site floor, and the client's own word, everywhere it speaks, is `world`.
- **The prediction's supporting argument is REFUTED, and it matters to the renderer.** PLAN S4 predicted "the continent histogram has exactly the 7 values that carry tile arrays". The area table uses `{0:366, 1:19, 2:168, 3:183, 4:123, 5:24, 9:5}` and the tile tables carry worlds `{0,1,2,3,4,5,6}` — **the two 7-element sets differ in two members**; the "7 = 7" was a coincidence of cardinality. **World 6 has 128 slots / 47 non-NULL tiles no area row asks for**, and **world 9 has five area rows (map ids 883-887) and no record in any of the three tiers**, so `0x005A9450`'s linear search returns NULL (`xor eax,eax; ret` on a miss) and those five maps take the tiled fallback with no ground art at all, unconditionally. An emitter that drops "unreferenced" worlds loses world 6; one with no defined answer for a missing world is wrong on five map ids. — OBSERVED.
- **Deep dive C's failed containment test now has a cause, not a shrug:** `s_worldData` records 0 and 7 are **byte-identical across all 48 bytes**, as are 3 and 8; 5 and 9 differ only at `+0x00`, and 2 and 4 differ only at `+0x00` (same geometry, *different* tile arrays `0x00BF2708` vs `0x00BF2A88`). The test was not merely weak — it was applied to two copies of one record. **Consequence for rung S5: Kamadan's crop must come from world 4, array `0x00BF2A88`. Worlds 2 and 4 have identical grids, so a renderer that picks by grid shape gets Cantha's art for an Elonian map and nothing would catch it.**
- **Our six `maps.toml` slots resolve as** 143→world 1, 144→world 2, 146→world 1, 148→world 1, 194→world 2, 449→world 4. So PLAN C2's "map 143 vs map 144" arm is **world 1 (4×8 grid, array `0x00BF2688`) vs world 2 (16×12, `0x00BF2708`)** — two different tile arrays; the arm discriminates.
- **PARTLY CLOSED (rungs S5 and S7).** **A hostile agent's compass dot IS red on our own server** — `vault/captures/harness/20260811T161925/hold007.png` at 5×: the green dot sits at the exact centre of the white Danger Zone circle (the player) and the hostile's dot is **red, outside it**. — OBSERVED, build 38797, our server, one frame, one agent. **What stays NOT FOUND is the `npc_allegiance` question**, which is which of the four allegiance FourCCs produces which colour, and a screenshot cannot recover a token. **The negative is now hard rather than soft:** the probe's wire capture *does* exist and is citable for the first time (`vault/captures/authsrv/authsrv-20260806T103830-c2.jsonl` and `-20260806T104329-c2.jsonl`, complete four-step runs five minutes apart, `map_id 148`, all four tokens `play`/`nonc`/`nonn`/`mons` verbatim), but **no harness session directory exists for either timestamp** — the probe was driven against a hand-launched client — and a full modification-time sweep of every image under `vault/` finds **zero** frames in a two-hour window bracketing both runs. This is S7's first kind of NOT FOUND (the frames do not exist), not its second (they exist and are illegible). Recovering it costs a fresh screenshotted run of a probe that already exists.
- **Whether the compass *map image* (not markers) is masked by the fog bitmap:** `CompassMarker` tests the bits, `CompassMap`'s blit does not, `GmMapView` does. Whether the compass composites a second masked layer (in `CompassModel.cpp` or `CompassCanvas.cpp`, profiled but not fully disassembled) is UNVERIFIED.
- **Indirect calls were not swept** — every §3 negative is direct-`call rel32` only; a compass→Path call through a vtable would be invisible. The `.rdata`/`.data` function-pointer sweep that would close this was not run.
- **`s_missionClientData +0x68`** (per-area compass texture, 157/888) is a live lead nothing in the repo has read; none of our slots use it.
- **All three CLOSED 2026-08-14.** `MISSION_MAP_OUTPOST == 0` (§3.3, from `QuestLog:261`'s compiled form); the satellite tier is `+0x18/+0x1C` with its table at `0x00A37440` (§3.1, rungs S3 and S4 independently); the atlas crop **is** 1 texel per terrain cell (§6b.2, OBSERVED from the client's own `add`/`shr 9` and from a five-scale population test with four rivals at zero).
- **The world map may be entirely out of server reach:** `map_open` is silent, exploration is per-character and client-local (WIKI). One silent labelled run bounds opening, not the whole feature — UNVERIFIED that the server has any lever there.
- **Only build 38797 was read.** The second vaulted build (`2026-04-30_b174de1f2d8d`) was touched only for the two-archive tile resolution check (§3.1, which agreed); no other cross-build corroboration was attempted.

**New open items, opened by the 2026-08-14 rungs:**

- **~~THE ARC'S LEADING QUESTION: why the compass image is NULL under our server~~ — CLOSED 2026-08-14 by rung C1 (§6d), by the premise expiring.** On build 38833 against its own archive generation the compass draws the atlas crop on retail map 148; the fallback is not a property of our server, and PLAN risk 7 is retired. **What replaces it is an attribution question, and it is genuinely open:** three variables moved at once (client build 38797→38833, archive generation row 7982→177262, and the `0x0199` id form `0x8001B97D`→`0x1B97D`), and C1 separates none of them. The bullet below is the record of the static hypotheses killed while the premise held. Both of them were REFUTED (rung S9, two agents, one per hypothesis, each told to refute its own; both succeeded). §6 carries the refutations, the seven-route breakdown of "the fallback", the surviving world set `{0, 2, 4, 5, 7, 8, 9, ≥10}`, and the third hypothesis — the **latch-once copy of the loaded map's cell dims** at `[CompassMap+0x50..0x5c]`. Everything about "does our authored map's compass show the right crop" is still downstream of it. **`Gw.log` is no longer a route to the answer** and PLAN C1's free discriminator has been struck; what discriminates is a live read of three dwords off the `CompassMap` instance, which is a client run.
- **What supplies `Engine\Map\Map.cpp`'s per-map explorable mask byte** (`0x0070A120` → `0x00721D00`, out-params bound by `ChCliApi:214`). NOT FOUND — `0x00721D00` not disassembled. It decides whether `0x008C` can unfog anything on our own geometry.
- **CLOSED 2026-08-14 (rung S10) — `s_missionClientData +0x40/+0x44` is the area's WORLD-MAP LOCATION-TAG ANCHOR**, a third `Point` in the same terrain-cell units as the two footprint rects, **with the rect's CENTRE as its documented fallback**. — OBSERVED, from four independent expressions of one rule. The getter `0x0054BD80` is the primary witness: pair equals the sentinel → `out = ((x0+x1) × 0.5, (y0+y1) × 0.5)` using the 0.5 at `qword [0x00945B40]`; pair differs → the pair *is* the answer. The consumer names it — `0x0054DC78 push 0x555de0; 0x0054DC85 call 0x630c90` creates a child frame whose proc is bracketed both ways by `GmMapCtlLocationTag.cpp`, and two of the getter's five callers sit beside `GmMapWorld:1052 locationTagFrameId`. **`GmMapWorld`'s five-pair compare is CONFIRMED and sharpened**: it is *"does this area have ANY position at all"* — anchor OR either rect — and its effect is to **destroy / never create** the area's location tag (`0x0054DBA1` → find-child `0x00631C90` → destroy `0x00631220`). **189 of 888 rows fail it.** The two globals `0x00C07CE4`/`0x00C07CE8` are one 8-byte BSS `Point` past the raw image with **zero writers image-wide** (six occurrences, all reads, each hand-disassembled), so the compare is against `(0, 0)`; a second such sentinel sits at `0x00C07CF4/F8`, and `0x0054E91A`/`0x0055AD9C` write the same predicate against a literal zero. **The containment measurement, with controls that must lose:** the anchor lies inside the row's own `FOOTPRINT_A` on **254 of 299** rows (84.95%), against **1.19%** for a duplicate-safe within-continent shuffle (200 trials, self- and equal-rect pairings excluded, 266 distinct rects among 419 rows), **0.67%** for the neighbour pair, and 0.89% for a global derangement — a ~71× separation on a test that could have failed. **Both refutation clauses fail to fire**: the globals are never non-zero, and 0 of the 486 anchor-carrying rows duplicate any rect corner, `(+0x38,+0x3C)`, or continent/region/type/name_id. **The 137 misses are structured and reported rather than trimmed**: all 71 type-18 rows miss (512×512 private-strip footprints at y 9728..12288 with anchors up on the landmass at y 868..6800) and all 20 continent-5 rows miss (footprints y 1600..3328, anchors y 132..860 — disjoint, and *not* a rigid translation: removing the per-continent median offset lifts it only 0/20 → 3/20). Why they differ is **UNVERIFIED**.
- **Two by-products of rung S10, each closing part of an older item.** `s_missionClientData +0x3C` is **`successor`, a row index bounded by `MISSIONS = 0x378 = 888`** (`0x0054C944 cmp dword [ebx+0x3c], 0x378` guarding `GmMapWorld:864 MISSIONS != testMissionData.successor`) — so it is **not** a coordinate, which bounds what the neighbour-pair control above can prove, and it re-derives the 888 row count from a second witness while naming the record's own type `MissionData`. And `s_worldData +0x20/+0x24/+0x28/+0x2C` **is a rect** (world 0 `(0,0,8192,9216)`, world 1 `(286,190,1536,1440)`, …), closing half of the `s_worldData` item below. **A test that FAILED is kept as a negative:** anchor-inside-`s_worldData`-rect scores 482/486 (99.18%) and is worthless — the neighbour-pair control scores 97.94% and world 0's rect alone holds 100% of all 486 anchors. **No reader of `+0x40/+0x44` exists in `P:\Code\Gw\Ui\Game\Compass\`** — all 31 reader instructions in 10 functions are in `P:\Code\Gw\Ui\Game\Map\`, established by intersecting an exhaustive `--field` sweep with a forward window from all 108 accessor call sites and then hand-classifying every survivor. **So S10 does not bear on the arc's leading question**, and that negative is the useful half.
- **`s_worldData +0x00`** takes `{1,1,2,0,3,3,4,1,0,6}` across worlds 0-9, correlates loosely with the area row's campaign field and is **not** equal to it row-wise. `+0x20/+0x24` and `+0x28/+0x2C` unidentified. `+0x14 == 512` on all ten (`CONST_WORLD_CHUNK_SIZE`, consistent with rung S1). **UNVERIFIED.**
- **HALF-CLOSED 2026-08-14 (rung S9). The destructor EXISTS and the widget is not immortal** — *this bullet used to read "the destructor was not found"*. `0x008C22A0` has **1 direct rel32 reference and 0 data words**: `0x008BB6FF`, inside the Compass frame proc's msgId-`0x0B` arm, which destroys all six sub-widgets and then explicitly nulls the pointer (`0x008BB73F mov dword [esi+0x4c], 0`) before freeing the 0x60-byte Compass at `0x008BB761`. So destroying the Compass frame makes the next layout pass rebuild `CompassMap` and **re-latch `+0x84`** — and, per §6, re-latch `[+0x50..0x5c]` too. Two things destroy it: the game-view frame's own destruction, and the `0x10000141` sub-code-0x71 rebuild at `0x004EAEA6`. **What is still NOT FOUND is whether that happens per map INSTANCE.** The create trigger is a controlled-character notify reached through a vtable store (`0x00824606 mov dword [ecx], 0x81b220`), and `codescan` cannot see an indirect edge. Suggestive but not decisive, and labelled **RECONSTRUCTION**: both posters (`0x00813610`, `0x0081B720`) free and re-zero the char-context arrays at `+0x564/+0x568/+0x56C` and reset `+0x694..+0x6A0` immediately before posting, which is per-instance housekeeping. Either answer kills hypothesis 1 — per-instance outright, once-per-login because the latch still follows the first `0x0199`.
- **Whether the compass ever requests a 256×256 chunk tile** (§3.1's four world-3 outliers, against `CompassMap:472`'s 512 bound). **UNVERIFIED** — a client-run question.
- **A second send entry was missed by the earlier producer sweep and is worth recording durably:** `SendMessage` is not the only one. `0x007DCB10` (the dword-array variant, asserting `MsgConn:1186/1187/1194`) has **40** direct call sites of its own, so the true send-call census is **214**, not 174. Found two ways that agree: the callers of the send-descriptor lookup `0x007DDE00` (exactly two, both in `MsgConn.cpp`), and every `.text` site carrying the game-channel stamp `and eax, 0x8000` (18 sites, exactly two in `MsgConn.cpp`). The next producer sweep will otherwise miss the same 40.
- **A count discrepancy in this document, unchased:** §5.3 records `0x008C` at "66 ours, all tape replay"; a 2026-08-14 sweep of `kind == "sent"` over the whole non-live capture tree gives **108**. Different predicates over an append-only tree that grows between reads. Likewise §4's "864 post sites" against a 2026-08-14 independent re-sweep of **871** (the "466 distinct msgIds" is a different quantity from the 1,253 subscribe *call sites* and is not in conflict). Neither is load-bearing; recorded for the next reader.

**Opened by the rung S9 adjudication (2026-08-14):**

- ~~**WHEN is `[globalCtx+0x14]`'s map rect populated, relative to the compass's first paint?**~~ **CLOSED 2026-08-14 (rung S12) — by the synchronous chunk loop of the map build, before the object is installed into the slot, and the compass cannot observe the in-between: `0x0070A5C0` crashes on an empty slot rather than reading zeros.** §6c carries the whole chain (two slot writers image-wide; chunk `0x2000000C` = `mapbuild.py`'s own `MAP_PARAMS_CHUNK` is the rect writer via `0x0070D780`, one caller; the build runs inside the synchronous dispatch of frame msg `0x10000098` posted by the MsCliApi instance-load path). **H3a is dead** — and §6c.4's file-side measurement of map 148 (416×512 cells, rect (−18432,−24576,21504,24576), **exactly the footprint**, with our spawn at cell (294,340) well inside) **kills H3 for retail 148 as well**, so all three named hypotheses are now dead on that map and the fault is downstream of the crop. §6c.4 also records a wrong claim this rung committed and then caught: `0x0287d3` is the authored sculpt map, not map 148.
- **`[CompassMap+0x80]` is UNREAD.** `0x008C1FF9 mov eax, [ebx+0x80]` loads it immediately before the tile-getter call at `0x008C200A` and nothing in this arc has traced it. NOT FOUND.
- **`0x00470F50` / `0x00470B60` — the archive open/read under `0x00679A90` — are not disassembled**, and they carry hypothesis 2's one named residual: a size- or id-dependent refusal that would fail on a ~110 KB atlas tile while succeeding on the 1,936 B fallback. ~1 h static, no client. **UNDECIDABLE STATICALLY** until then.
- **Rung S9's frame corpus grew from six to eight, and two of the eight are attributable to a surviving `Gw.log`** — `20260813T185442/final.png` (χ = +1.0965, paired with `vault/run/…-c2/Gw.log`) and `20260814T100327/final.png` (χ = +1.0954, paired with `vault/run/…-probe/Gw.log`), by the criterion "a run directory's `Gw.log` belongs to the last harness session naming that directory's `Gw.exe`", swept over all 719 sessions from `20260813T185442` forward. Both logs carry `Perf: AuthSrv (127.0.0.1)` (the sink works), no minimap line and no texture error. Given §6 that is evidence for nothing, but it closes the "we never had a log for a session we measured" gap. Both frames are load-overlay-contaminated, so the two χ figures are **ADVISORY**; the load-bearing χ result stays rung S5's.
- **The `Log.cpp` sink is now pinned as a positive control**, which is what makes the §6 negative a measurement rather than an absence: `0x0093D044 s_types = {"Debug","Perf","Error","Fatal"}` (char[4][8]) with `0x0093D024 "%s: %S\n"`, so severity 1 → `Perf: `; and `0x008C2201 push 1; call 0x46ed40` is the same function at the same severity as `0x0049498D push 1; call 0x46ed40`, the `AuthSrv (%S)` banner observed in **25 of the 26** vault logs.
