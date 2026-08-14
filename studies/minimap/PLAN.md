# The minimap ladder — from static reads to an authored-map compass

**Arc:** `studies/minimap/` · **Companion:** [FINDINGS.md](FINDINGS.md) · **Date:** 2026-08-14

This is the ordered work list, cheapest first. Every rung states its **prediction before its procedure** (house rule, CLAUDE.md "A probe states its prediction first") and every rung is falsifiable — the refutation is written into the rung. Client rungs are marked **NEEDS OWNER GO-AHEAD**: parallel sessions share one harness and one `main`, and a client run against ArenaNet is never in scope here (all runs are loopback, our DH, caged).

**What is already settled** (see FINDINGS): the compass/mission-map/world-map ground image is a per-continent ATEX atlas in the archive, cropped by the area row's footprint rect, selected between two footprints by the `0x0199` map-type byte our server sends; the compass draw/ping is the opcode pair `0x002B` (c2s) / `0x0091` (s2c), and our server drops `0x002B` unnamed. The ladder turns those static reads into measured facts and then into an authored-map compass, and prices the last step honestly.

---

## Tier 1 — static, no client, no harness contention (hours each)

### S1. Correct `s_worldData` in `consttable.py`
**Prediction (a regression claim, since the measurement is in hand):** stride **48**, count **10**, `stride_from` = the accessor's own `lea/shl` at `0x005A93CD`, corroborated by `WORLDS = 10` and by `count == chunkCX × chunkCY` on 7 of 7 worlds. The current `stride=24, "UNSETTLED"` at `toolkit/clientscan/consttable.py:539` (printing `20 × 24`) is wrong; 48 is already in its own rival-stride list.
**Procedure:** edit the row; `test_consttable.py` re-derives closure from the anchor, so a wrong stride reddens it. Keep the rival-stride print — 48's divisors still close, and the module's blind-spot doctrine says report that, not hide it.
**Cost:** ~30 min. **Do first — it is a correction to a committed claim.**

### S2. Pin the footprint selector into `maprows` §9 item 4
**Prediction:** the branch at `0x008C276B-0x008C2782` is the only place the compass reads either footprint; `MissionCliGetMap()==0 → A`, non-zero → B. `GmMapView` will have its own read and may or may not use the same rule.
**Procedure:** `codescan --field 0x48 --in CompassMap` and `--field 0x58 --in CompassMap`, then the same in `GmMapView`; record whether GmMapView branches identically. Note `--field`'s declared blind spots (`test_codescan.py` §10): a constant held in a register, a multi-step address.
**Cost:** ~1 h. **Retires a named open item with a measurement.**

### S3. Commit the atlas reader as `toolkit/clientscan/worldmap.py`
**Prediction (state before re-running on a third archive):** 409 tile records over 7 worlds; trailing u32 = 0 on 409/409; ≥401 resolve to `ATEX`; the 8 that do not are exactly {387674, 387678, 387680, 387682, 387684, 388093, 388095, 388097}, all in worlds 0/1.
**Procedure:** locate `s_worldData` through `consttable` (never a hardcoded VA); walk the `0x00A37390` (chunk) and `0x00A373E8` (parchment) tables; emit `(tier, world, chunk_x, chunk_y) → file_id` with provenance per row. This is a `source = "client-table"` extraction — `content.py`'s two conditions apply (extractor in repo + named by the row; build recorded). Bulk output to `vault/`, never the repo.
**Cost:** ~half a day with a test. **The reusable asset the rest of the ladder rides on.**

### S4. Find the producer of the compass's world index (`[ebx+0x84]`)
**Prediction:** it is `s_missionClientData[map].continent` (`+0x04`, UPSTREAM offset) directly or through a small mapping — the continent histogram over 888 rows has exactly the 7 values that carry tile arrays.
**Why not already settled:** a containment test (footprint vs each world's grid) failed as a discriminator — the biggest grid always contains — and is reported as a failed method, not a result.
**Procedure:** `codescan --field 0x84 --in Compass`, walk back to the writer; cross-check `GmMapHelpers:28 sourceWorld < WORLDS` @ `0x0054e2d2`.
**Cost:** 1-2 h. Refutable both ways.

### S5. Render the atlas crop offline and compare to a compass we already have on disk
**Prediction:** for Kamadan (row 449, continent 4, footprint `(2080,3136)..(2496,3584)`, 416×448 cells), decoding the covering world tiles and cropping at 1 px/cell produces a picture recognisably matching an existing vault screenshot of Kamadan's compass. **Rival that must lose:** the same crop from map 143's footprint `(960,448)..(1280,992)` must NOT match Kamadan's compass. If the 1-px-per-cell scale is wrong the match fails and this rung says so.
**Procedure:** `worldmap.py` (S3) → `archive.read` → `atex.parse` → `atexlevel.decode_level` → `dxt1.decode` → `png.write` (all committed and tested). Compare against frames in `vault/captures/harness/*/` — **no client run if a usable Kamadan frame exists; check first.** If none does, this becomes a client rung.
**Cost:** ~half a day. Converts §3's disassembly reading into a picture at no harness cost, and settles the 1-px-per-cell scale (currently RECONSTRUCTION).

### S6. Confirm the compass draw/ping opcode from the sender
**Prediction (mostly already met by deep dive B — state it as confirmation):** exactly one sender reaches `CharMsg:8129`'s bound at `0x00920262`, writing GAME_CMSG `0x002B`; its s2c broadcast partner is `0x0091` (`CharMsg:4934` @ `0x0091EA43`). The knot pack is low-half-first; a single knot is a click, a run is a drag.
**Procedure:** `asserts.py --at 0x0091EA43` and `--at 0x00920262` to bound the functions, `codescan --dis`/`--xrefs` to re-read the opcode immediates and the sole-producer claim (thunk `0x00816110` has 1 direct caller, 0 raw-dword occurrences). Cross-check the live corpus with `cmsgstream.timed(stamp, "c2s", "game")`, remembering the `0x8000` c2s mask (`test_cmsgnames.py`) — the single live `0x002B` is at `20260807T143055` t=50.70 s. Absence in the other captures is expected (no operator was told to draw).
**Cost:** 2-4 h. **The route to a named opcode for the one surface that is a pure protocol gap.**

### S7. Transcription-only: recover the hostile compass-dot colour
**Prediction:** the answer to "does a hostile NPC-class agent's compass dot go red" is already on disk in the `npc_allegiance` run artifacts or its frames.
**Procedure:** re-read `vault/` artifacts for the four-arm run behind `studies/enemy/PLAN.md:479-487`. If frames exist, the answer is there; if not, say NOT FOUND and fold it into the next combat run's screenshot checklist rather than spending a launch on it.
**Cost:** under an hour.

---

## Tier 2 — one client run each, cheap arms (NEEDS OWNER GO-AHEAD; batch one go-ahead over the set)

### C1. Baseline: retail map on our server, compass frame vs the S5 crop
**Prediction:** the compass on Kamadan (map 449) under **our** server is pixel-comparable to the offline S5 crop — the compass ground image owes nothing to the server.
**Procedure:** `harness/session.py --keep-open --shots N`, map 449, no probe. Score with `shotlabel.py` used correctly (`test_shotlabel.py`): join by wall clock, noise floor = median of the idle window (not max, never two pairs), a frame inside the send's own second is neither baseline nor after, score a strip not a pair.
**Cost:** ~1 run, ~5 min. **The control every later arm is read against.**

### C2. The discriminating arm: same terrain, two map slots
**Prediction:** deploy the identical authored terrain at `map_id = 143` (continent 1, footprint 320×544) and at a slot on a different continent with a very different footprint (e.g. row 144: continent 2, `(4736,2272)..(5088,2912)`, 352×640). The compass image must **change between the two arms** and must **not** change when the terrain changes at a fixed slot. **If the compass instead tracks the terrain, FINDINGS §3's whole model is refuted and the ladder stops here.**
**Procedure:** `deploy.py --area sculpt --install --launch --dat <copy>` twice with the row's `map_id` swapped; `--serve` on a second launch for the navmesh readback (`studies/customarea/FINDINGS.md` §59.3: the run that installs cannot serve — `--install` arms the head to zero and the client then locks the archive). Screenshots through the hold; `capture_error_dialog` fires on every run.
**Cost:** ~4 runs (2 arms × install+serve), ~30 min harness. The E1-collision shape — two builds differing in one field — and the cheapest thing that can refute the model.

### C3. Flip the map-type byte on a slot where A ≠ B
**Prediction:** on one of the **172 rows where FOOTPRINT_A ≠ FOOTPRINT_B**, toggling `0x0199` field 3 between 0 and 1 (`authsrv --explorable`) shifts the compass ground image to a different crop of the same continent, and nothing else changes. **Negative control:** on map 143 (A == B) the same flip produces no compass change — without it the experiment is unfalsifiable.
**Procedure:** two probe-free harness runs per arm; strip-score against the pre-flip idle window; register a `probes.py` step so the flip is timestamped in the capture.
**Cost:** ~4 runs. **Turns FINDINGS §3.3 from a disassembly reading into an OBSERVED fact — the answer to the brief's "do we hold the lever" question.** It does not make our map look right; it proves we hold the lever. (Note: map 143's A == B, so a live-retail row must be borrowed for the positive arm — the `maps.toml` map.144 caution about unknown live rows applies.)

### C4. Targeted opcode probes with screen readout
**Prediction (per candidate, before sending):** `0x0049` (QUEST_ADD) with a vec2 inside our map's rect and `dest_map_id` = our slot draws a **green starburst on the compass** and a quest-log entry; `0x008C` (MAP_EXPLORATION_MARK) with (x,y,markSpanCount) inside the map unfogs one block on compass and mission map; `0x008D` draws **nothing** (static catalogue). `0x0091` (COMPASS_DRAW_BROADCAST) with knotCount ≤ 16 draws a polyline — **never send knotCount > 16 (process kill, FINDINGS §4.1)**.
**Procedure:** `smsgsweep --plan --only <op> --set <field>:<value>` → `sweeploop`/`shotloop` → `shotlabel`. Four paid-for cautions: (i) verify the server's own `plain=` hexdump matches intent — `--set` silently shipped the degenerate payload for an hour (`studies/smsgsweep/FINDINGS.md` §5c retractions); (ii) the ledger is keyed by regime (all-zero vs filled are different rows); (iii) `SILENT` = no c2s reply and is blind to anything drawn — the screen is the instrument; (iv) `--enemy` is opt-in, a combat-free run must warn if no hostile.
**Cost:** one launch per opcode, ~40 s each. Budget ~2 h for a dozen. **This is where quest markers and the exploration reveal get their first OBSERVED screen result — and where §4.2's `0x008C`-vs-`0x0089/0x008B` contest can be settled by which opcode actually unfogs a block.**

---

## Tier 3 — the expensive half, only if the owner wants the picture to be ours

### A1. Author one atlas tile
**Prediction:** replacing the 512×512 ATEX at the tile covering map 143's footprint changes the compass, mission map **and** world map together (all read the same table, FINDINGS §3.2). If only one changes, §3.2 is wrong.
**Procedure:** `png.py` → `dxt1.encode` → `atex` container → `datwrite --replace` if it fits (it will not — ours writes uncompressed, median tile is 110,608 B stored), else `datmove`, into a **throwaway run-directory archive only**. Follow `iconset.py`'s scars: `file_id_table` returns one-based row numbers while `Archive.entries` is positional, so `entries[row]` reads the row before the one named; check the whole plan before the Writer opens. Prefer `datwrite --restore` from a donor over `--revert` (a journal expires the moment a client runs, `studies/crossbuild/FINDINGS.md` §4c; no journal exists for the icon rows left armed in `vault/run/reskin-roster/`).
**Cost:** 1-2 days + runs. **Collateral to state up front:** a tile spans up to four of map 143's footprint chunks, all shared with other Pre-Searing maps — arming them changes every neighbour's compass in that archive copy.

### A2. Repoint the area row's footprint (the RESKIN move)
**Prediction:** editing `s_missionClientData[143]`'s `+0x48..+0x54` (and `+0x58..+0x64`) to a rect whose size equals our authored dims makes the compass crop that size (32/64/96 cells instead of 320×544), and the player marker projection becomes self-consistent for the first time.
**Procedure:** extend `toolkit/clientpatch/reskin.py`. The table is `.rdata`; the same three constraints as its four existing tables apply — locate structurally (never by address), require anchor AND shape to agree, write out of place, assert containment (every changed byte inside the intended dword) plus a read-back (`test_reskin.py`'s first version wrongly assumed "4 bytes changed" when only two moved).
**Cost:** 1-2 days + runs. **A1 makes the compass the right *picture*; A2 makes it the right *shape*. Neither alone is enough** — which is the cost the owner should see before Tier 3 starts: making an authored map's compass right means both an archive write and a client patch.

---

## Risks that could moot a rung

1. **The model may be incomplete.** Only `CompassMap.cpp` was disassembled; `CompassCanvas/Marker/Target/QuestEffect/Model` were read as assert lists, and `CompassAIControl`/`CompassModel` carry zero visible asserts. If a second ground layer is drawn from map data by one of those, FINDINGS §3 is incomplete — **C2 is early precisely because it can refute the whole model cheaply.**
2. **`asserts.py` is a floor** (370 sites short); every "no assert names X" inherits it.
3. **`OFF_CONTINENT = 0x04` is UPSTREAM.** If the layout is wrong the S4/§3.4 join moves.
4. **The world map may have no server lever at all** (`map_open` silent, exploration per-character/client-local) — surface 1e may not be a gap we can close.
5. **Harness contention and the two-run rule:** `--install` arms the head to zero and the client locks the archive, so a navmesh readback needs `--serve` as a second launch (`studies/customarea/FINDINGS.md` §59.3). A run that "completes" is not evidence a hazard is absent.
6. **Archive safety:** every write goes to a run-directory copy; `C:\gw` and `vault/dat_study` are refused by the `datwrite`/`atex`/`iconset` guards; a new client under `vault/run/` costs a UAC prompt (the cage is per-binary).
