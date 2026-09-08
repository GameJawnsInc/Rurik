# How a unit comes to exist — server and client setup of agents

**2026-08-16.** This is a **synthesis over existing code and studies, not new measurement**: nothing below was probed, captured or disassembled for this document. It stands on [../smsg/FINDINGS.md](../smsg/FINDINGS.md) (wire corpus + client asserts for the agent-lifecycle opcodes), [../character/FINDINGS.md](../character/FINDINGS.md) (player identity/appearance/level channels, and the label vocabulary used throughout), [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md) (property dispatch, death bit), [../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md) (model/composite resolution), [../heroes/FINDINGS.md](../heroes/FINDINGS.md) (the four hero gates), [../enemy/PLAN.md](../enemy/PLAN.md) (definition-slot and death probes), [../monsterai/FINDINGS.md](../monsterai/FINDINGS.md) and [../divergence/FINDINGS.md](../divergence/FINDINGS.md) (behaviour fidelity), [../movement/FINDINGS.md](../movement/FINDINGS.md) and [../profession/RESKIN.md](../profession/RESKIN.md) (position and level measurements), [../msgtable/FINDINGS.md](../msgtable/FINDINGS.md) (independent static recovery of message shapes), plus the live server code (`toolkit/authsrv/authsrv.py`, `toolkit/authsrv/agents.py`, `toolkit/content.py`).

Labels are the vocabulary of [../character/FINDINGS.md](../character/FINDINGS.md):15-21 — OBSERVED, UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND. The smsg/agentprops studies additionally use **SOURCED** for claims read out of the client's own compiled asserts/disassembly; that label is carried through where those studies use it. Where a source doc already labels a claim, its label is carried, not upgraded. `schema/messages.json` is imported from OpenTyria, so our schema and our server agreeing is **one** witness (`schema/messages.json:2`, UPSTREAM base; CORROBORATED only once `schema/overrides.json` is applied per [../msgtable/FINDINGS.md](../msgtable/FINDINGS.md):242).

Three contradictions flagged by the review pass are resolved in §7, each by reading the cited files; the resolutions are also applied inline where the affected claims appear.

**File:line citations were read at commit `253b863`.** `main` had already grown `toolkit/authsrv/authsrv.py` by ~29 lines (insertions near :2252 and :6842) before this doc merged, so numbers cited above those points drift by that much — re-locate by symbol or quoted comment, not by number, the same way [../monsterai/FINDINGS.md](../monsterai/FINDINGS.md) is read.

---

## 1. The one-page answer: server → wire → client, in order

### 1a. The player's own body

There is no character store — one hardcoded test character (uuid, name, 37-byte settings blob) is the entire roster (`toolkit/authsrv/authsrv.py:2131-2145`, OBSERVED). The pipeline:

1. **Portal (HTTP, 6601).** `webgate.py` mints a deterministic `user_id`/`token` from the login email (`toolkit/portal/webgate.py:66-74`, OBSERVED). No character data exists at this stage.
2. **Auth channel (6112).** DH/ARC4, then `AUTH_CMSG_PORTAL_ACCOUNT_LOGIN` (0x0038) validated against the shared `SessionStore` (`toolkit/portal/sessionstore.py:91-106`). The reply burst ends with `REQUEST_RESPONSE` **last** — that message, not the character data, flips the client to character select (`toolkit/authsrv/authsrv.py:4851-4909`, OBSERVED; pinned by `toolkit/authsrv/test_handshake.py:326-348`).
3. **Instance handoff.** `AUTH_CMSG_REQUEST_GAME_INSTANCE` → `GAME_SERVER_INFO` + `REQUEST_RESPONSE(0)` (`authsrv.py:4813-4848`, OBSERVED; request shape CORROBORATED, [../character/FINDINGS.md](../character/FINDINGS.md):1645-1649).
4. **Game channel up.** The server volunteers `INSTANCE_LOAD_HEAD` → player-name bracket → `INSTANCE_LOAD_INFO` (agent id 1, map id, explorable flag), and sets `state["pos"]`/`state["plane"]` from `MAP_STATIC_CONFIG` right there (`authsrv.py:5298-5353`, OBSERVED).
5. **Three client requests** — OBSERVED on a real capture arriving ITEMS → SPAWN → PLAYERS ([../character/FINDINGS.md](../character/FINDINGS.md):1742-1743); our handlers are order-agnostic:
   - `REQUEST_ITEMS` (0x0091) → inventory/gold/weapon-set bracket ending in `READY_FOR_MAP_SPAWN` (`authsrv.py:5573-5647`). The weapon item is declared with `0x0161 CREATE_NAMED_ITEM` here, **before** anything can wear it.
   - `REQUEST_SPAWN` (0x0088) → `INSTANCE_LOAD_SPAWN_POINT` (map file_id, position, plane) + `INSTANCE_LOAD_FINISH` (`authsrv.py:6869-6900`).
   - `REQUEST_PLAYERS` (0x0090) → **the unit itself** (next).
6. **The player-create burst** (`authsrv.py:6404-6709`, OBSERVED, in send order): PLAYER_DATA bracket → `INSTANCE_LOADED` → `PLAYER_INFO` 0x0059 ("PLAYER_CREATE": player number, agent id, appearance dword, name) → party-of-one bracket (size before leader — order load-bearing) → **`WORLD_CREATE_AGENT` 0x0020** (`authsrv.py:6517-6536`) → `AGENT_UPDATE_ATTRIBUTE_POINTS` 0x0037 (**must precede profession** or the client asserts `attribState` — `authsrv.py:6537-6547`, OBSERVED crash) → `AGENT_PROFESSIONS` 0x00B7 → `AGENT_SET_PROFESSION` 0x00A6 → unlocked skills → `SKILLBAR_UPDATE` → `CHARACTER_UPDATE_FACTIONS` 0x00E9 (field 9 = level 1, `authsrv.py:6603-6606`) → `AGENT_UPDATE_ATTRIBUTES` 0x003A → energy/health maxima on 0x009F (`authsrv.py:6628-6635`) → weapon bracket (`0x006E` → `0x0048` → `0x006D` → attack speed 0x0035, `authsrv.py:6660-6702`) → **`WORLD_UPDATE_CONTROLLED_AGENT` 0x0022** — the control transfer, `[agent_id, 3]` (`authsrv.py:6704-6705`) → `INSTANCE_LOAD_FINISH`.
7. **Then, and only then**, the NPC population spawns — `spawn_population()` or `spawn_enemy()`, mutually exclusive branches (AST-proven by `toolkit/authsrv/test_population.py:324-350`), then henchman/hero bodies (`authsrv.py:6729-6851`).

### 1b. An NPC body

All NPC creation funnels through one function, `create_agent_world()` (`toolkit/authsrv/authsrv.py:3845-3959`, OBSERVED):

1. `0x0056 NPC_UPDATE_PROPERTIES` — the **type declaration** (definition slot), first create only; a definition is per-instance and outlives its agents (measured by the burrow probe, `authsrv.py:3862-3875`; retail sends it once for 140 re-creates, [../smsg/FINDINGS.md](../smsg/FINDINGS.md):884-887, OBSERVED).
2. `0x0057 MONSTER_COMPOSITE` — only if the npc row has `model_id`; retail itself declares 8/44 definitions with no 0x0057 (`authsrv.py:3893-3901`; `content/npcs.toml:70-74`, OBSERVED).
3. `0x00F0 AGENT_INITIAL_STATUS` — **only if `entry["effects"]` is truthy** (`authsrv.py:3919-3921`), which in practice means only mid-burrow. This is a known divergence — see §6d.
4. **`0x0020 WORLD_CREATE_AGENT`** — model_id = `0x20000000 | definition`, kind 9 (`authsrv.py:3923-3928`).
5. `0x009F [42, agent, max_health]` — the health maximum (`authsrv.py:3929-3931`).
6. `0x00A6 AGENT_SET_PROFESSION` — only if the npc row has one (`authsrv.py:3940-3943`).
7. `0x0026 AGENT_UPDATE_FLAGS [agent, 9]` — the burst tail, a merge the client masks (`authsrv.py:3949-3951`).
8. `0x0035` attack speed — mandatory, because the client constructs every `AvChar` with interval 0.0 and asserts `m_attackInterval` on the first swing (`authsrv.py:3953`, `:6693-6702`, OBSERVED failure mode).

"ORDER IS LOAD-BEARING. The definition must precede the agent that uses it" (`authsrv.py:4310-4312`); violating it crashes the client on `Array.h(587)` `index < m_count` — §6a.

Agent ids are **hand-picked constants, never generated**: player = 1 (`authsrv.py:1131`), test enemy = 10 (a content-authored allocator choice, "not facts about the game" — `content/world.toml:11,33-36`, RECONSTRUCTION by its own provenance note), area rows carry their own, validated for uniqueness at load (`authsrv.py:4131-4188`) and against live collisions at create (`authsrv.py:3877-3883`). All OBSERVED from code.

### 1c. What retail does around a create — the comparison target

The retail create idiom is measured with zero exceptions ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):1162-1198, OBSERVED): `0x00F0` precedes its agent's `0x0020` **472/472** — *immediately* only **with `0x001E` removed**, which that study states at `:1162` and which this line dropped until 2026-08-17; in the raw stream a `WORLD_SIMULATION_TICK` sits between them about half the time, and §8 Q11's answer carries the five-capture measurement; the gate is `0x0020` field[4] — `0x00F0` iff kind ∈ {5 player, 9 NPC} (130/130 and 342/342), `0x0115` iff kind 1 (44/44), visual equipment `0x006E→0x0048` only inside kind-5 creates (76/130, 0/397 elsewhere). The most common full template is `009F 00F0 0020 006D 0026` (132/527); only 5/527 creates are a bare `0x0020`. Removal is the opposite shape: `0x0021` is a lone message 413/416 (99.3%), `[agent_id]` only, 0 double-removes, 0 removals of a never-created id ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):260,1185, OBSERVED) — a discipline our `remove_agent()` reproduces and enforces (`authsrv.py:3797-3842`, OBSERVED).

Our post-create ordering (health → profession → flags) is the **server's own choice** — the wire study pins `0x00F0`-before-`0x0020` strictly but measured no strict adjacency rule among the post-create messages. Label RECONSTRUCTION for the ordering, per the smsg report's own caveat.

### 1d. What the client does with it

`0x0020` allocates a **fresh** 308-byte object — a create, not an update ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):145-199, OBSERVED/SOURCED; shape independently reproduced by static table recovery, [../msgtable/FINDINGS.md](../msgtable/FINDINGS.md):242, CORROBORATED). For an NPC, the model id's low bits index the per-connection definition table filled by `0x0056` (record layout byte-exact, [../smsg/FINDINGS.md](../smsg/FINDINGS.md):766-797, SOURCED). The composite dwords of `0x0057` are archive file ids of geometry-bearing ffna files, sent exactly when the `0x0056` file's own skeleton carries the COMPOSITED flag ("no own geometry") — the same fact measured from the wire (8/8, 36/36, 43/43) and from the archive bit (14,571/14,571) by two agents working blind ([../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md):33-40,392-411,690, OBSERVED/SOURCED). Players never get `0x0056`/`0x0057` at all (0 player-class joins in 3 captures); their appearance is the packed dword in `0x0059` ([../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md):710-717, OBSERVED; bit layout CORROBORATED, [../character/FINDINGS.md](../character/FINDINGS.md):186-236). Names follow the repo's own "commit the id, resolve the string at run time" pattern, proven as the client's actual behaviour: an NPC's EncString words rendered as "Hatcher [Collector]" with no text on the wire ([../enemy/PLAN.md](../enemy/PLAN.md):436-441, OBSERVED); a completed hero record makes the roster row switch from the body's name to `s_heroClientData` row 1 — "Norgu" — with no name ever sent ([../heroes/FINDINGS.md](../heroes/FINDINGS.md):880-897, OBSERVED).

---

## 2. Default state

What a unit has when nothing overrides it. "OURS/placeholder" below means RECONSTRUCTION in the house vocabulary — the source itself says it is invented.

### 2a. Values our server sends by default

| Field | Default | Comes from | Label |
|---|---|---|---|
| model_id tag | `0x20000000 \| definition` (NPC), `0x30000000 \| player_number` (player) | `agents.py:72-73`; high-nibble kind tag | CORROBORATED ([../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md):914-920; mask width 24 vs 28 bits disputed) |
| kind (h000B) | 9 NPC / 5 player | `agents.py:76-77` | CORROBORATED (0=item/5=player/9=NPC, [../character/FINDINGS.md](../character/FINDINGS.md):821) |
| direction | `(1.0, 0.0)` fixed | `agents.py:751` | RECONSTRUCTION (retail field 7 is only "direction-shaped", UNVERIFIED — [../smsg/FINDINGS.md](../smsg/FINDINGS.md):166-191) |
| speed | 288.0 u/s | `agents.py:79,742` | UPSTREAM value (matches GWW run speed); field semantics INFERRED per smsg |
| h001E / h0023 / h0027 | `1` / `1.0` / `0x41400000` | `agents.py:751-752`, carried verbatim from the retail player template | shape OBSERVED (client-authored 38771 template, [../character/FINDINGS.md](../character/FINDINGS.md):797-810); meaning UNVERIFIED |
| trailing zeros + `(INF, INF)` sentinels | as retail sends them | `agents.py:753` | shape OBSERVED, meaning UNVERIFIED |
| allegiance | spawn row default `"hostile"` → `'mons'` FourCC | `authsrv.py:4272,2340-2344` | RECONSTRUCTION — `'mons'` is **not** a client-recognised constant; the client renders any unrecognised token hostile ([../enemy/PLAN.md](../enemy/PLAN.md):477-524, OBSERVED). Player sends `'play'`, which is recognised (SOURCED, agent+0xE8) |
| max health (NPC) | row `max_health`, else 100 | `authsrv.py:4273`; `content/world.toml:13` | RECONSTRUCTION (placeholder) |
| health/energy max (player) | 100 / 25 | `content/world.toml:227-243` → `agents.py:849-850` | UPSTREAM — the row's own note: values from gw-preservation, "not observed on our wire"; the property **ids** (41/42) are SOURCED |
| health semantics (prop 42) | `health += (new_max − old_max)` — a delta grant, **not** set-and-refill | `agents.py:118-132`; [../profession/RESKIN.md](../profession/RESKIN.md):1489-1533 | OBSERVED (harness 20260813T215004). **Supersedes** [../enemy/PLAN.md](../enemy/PLAN.md):577-583 and [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):175-178 — see §7, resolution 1 |
| attack speed | NPC 1.33 (axe), player 1.75 (hammer) | `authsrv.py:2353,711` | RECONSTRUCTION — "has to be non-zero rather than right"; the non-zero requirement is OBSERVED (client asserts `m_attackInterval`); 1.75 is UPSTREAM (wiki, formula CORROBORATED) |
| level | player: prop 36 = `START_LEVEL` sent pre-create since 2026-08-17 (roster reads `W1`, harness `20260817T153701` — was **never sent**, hence §2b's `W0`); NPCs still rely on the 0x0056 level byte, retail's own spawn idiom (prop 36 absent from all 1,068 census create bursts) | `authsrv.py` player burst; `agents.py` PROP_LEVEL | OBSERVED both halves |
| effects / initial status | `0x00F0` payload 0 (row `effects` if set), unconditional preamble since 2026-08-17 | `authsrv.py` create paths; was gated until §6d's closure | OBSERVED — retail's 472/472 idiom, now ours |
| profession | NPC: only if the content row carries one; player: Warrior | `authsrv.py:3940-3943,876` | OBSERVED code |
| equipment | player: one weapon (item id 1) if `EQUIP_WEAPON`; NPC: none, ever | `authsrv.py:6660-6702` | OBSERVED code |
| attacks_back | **False** for population rows; True only for the legacy test enemy | `authsrv.py:4285` vs `:2334` | OBSERVED code — most spawned units are inert by default (§4) |

### 2b. What the client assumes before any message arrives

| State | Client default | Label |
|---|---|---|
| Health bar | **full and red**, with no health message at all; the player's own orb reads 1, not 0 | OBSERVED ([../enemy/PLAN.md](../enemy/PLAN.md):410-414) |
| Level | **0, indefinitely** — the literal absence of a prop-36 send, rendered as `W0` | OBSERVED ([../profession/RESKIN.md](../profession/RESKIN.md):1089-1108); UPSTREAM corroboration [../character/FINDINGS.md](../character/FINDINGS.md):1232-1249 |
| Equipment | naked; the client invents no fallback armor | OBSERVED ([../character/FINDINGS.md](../character/FINDINGS.md):1395-1400) |
| Attack interval | 0.0 — the first swing attempt asserts and kills the client | OBSERVED failure mode (`authsrv.py:6693-6702`) |
| Flags word bit 0x20000 | clear — several agent-directed messages are **silently inert** until set | SOURCED ([../enemy/PLAN.md](../enemy/PLAN.md):617-655) |
| Roster row without a live agent | renders as a container: no name, level sentinel 0xFF | OBSERVED ([../heroes/FINDINGS.md](../heroes/FINDINGS.md):464-469) |

---

## 3. Location

**The player's arrival point is a static per-map fact, not a per-character one.** `content/maps.toml` `[map.N]` carries `spawn_x`/`spawn_y`/`plane`, loaded once into `MAP_STATIC_CONFIG` (`toolkit/content.py:331-339`; `authsrv.py:1567`, fallback map 449 at `:1573`) and read three times: at `INSTANCE_LOAD_INFO` (sets `state["pos"]`, `authsrv.py:5348-5353`), for `WORLD_CREATE_AGENT`'s position, and for `INSTANCE_LOAD_SPAWN_POINT`. Map 148's coordinate is provenanced as landing in exactly one trapezoid of that map's own mesh with a negative control (`content/maps.toml:14-27` — value UPSTREAM from gw-preservation, verification OBSERVED).

**NPC positions are content-sourced, navmesh-checked.** The legacy enemy is placed by an offset from wherever the player arrived (`ENEMY_OFFSET`, nudged onto walkable ground by `enemy_spot()`, `authsrv.py:4087-4109`). Area rows carry absolute `x`/`y` read back out of the client-compiled navmesh, "not off a screenshot" (`content/world.toml:305-315`, OBSERVED provenance note). Every placement passes `place_on_mesh()` (`authsrv.py:4191-4220`): spiral search up to 480 units in 48-unit steps, and **refusal** rather than silent placement if nothing walkable is found — "a missing NPC is a smaller lie than a present one nobody can reach". With no navmesh loaded, placement is trusted unchecked with a printed warning (`authsrv.py:4206,4245-4247`).

**After spawn, "where the player is" is one field, `state["pos"]`, and three channels maintain it** (all OBSERVED from code; this mechanism postdates [../movement/FINDINGS.md](../movement/FINDINGS.md) — see the CONTESTED note): keyboard packets (0x003D) carry the client's live position in slot 1, adopted through a 900-unit sanity gate (`authsrv.py:5984-5987,1680-1692`; slot-1 reading CORROBORATED, [../movement/FINDINGS.md](../movement/FINDINGS.md):755-759); a 20 Hz tick integrator walks toward `state["dest"]` and is **never broadcast** — explicitly "the weaker of the two opinions" (`authsrv.py:5463-5501`); and move-cancel reports (0x0047) are accepted **unconditionally** — "THE SERVER NO LONGER ARGUES" (`authsrv.py:6337-6371`). **CONTESTED:** [../movement/FINDINGS.md](../movement/FINDINGS.md):649-655 still documents the opposite 0x0047 policy ("We override the client's reported position… Keep ours") as the deliberate choice; the code reversed it on the strength of a session (7 corrections reviewed, none defensible) recorded only in the `authsrv.py:6340-6355` comment, with no FINDINGS entry — both citations stand, the code is current, the doc is stale. Click-moving is a measured blind spot: the client sends no position between clicks (median 0 reports across 35 intervals; one 37 s gap — `authsrv.py:6179-6183`, CORROBORATED by [../movement/FINDINGS.md](../movement/FINDINGS.md):805-810), which is why clicks are gated on a 1-second freshness window for `state["pos"]` (`authsrv.py:6225-6247`, MEASURED over 532 reports).

Every NPC behaviour keyed to "the player" reads this same field (`enemy_move_tick`, `authsrv.py:3402-3418`, OBSERVED).

**Added 2026-08-17:** retail spawn positions are no longer data nobody reads — `toolkit/authsrv/agentroster.py` (landed with the Isle arc) extracts every `WORLD_CREATE_AGENT` from a capture *with* its field-5 world coordinates and groups repeat creates into **stations** (same tag/definition/model/position/plane), separating stationary NPCs from wanderers by measurement. That is the instrument for turning captured placements into content rows with real provenance, the half `content/world.toml`'s "R4c's real spawns are server-only data nobody has captured yet" note was waiting on.

---

## 4. Behavior — the default model, and its retail fidelity

**There is no state machine with named states.** Behaviour is per-tick sweep functions over `state["agents"]`, on a fixed 20 Hz daemon tick (`TICK_SECONDS = 0.05`, `authsrv.py:1140`; loop `:5355-5479`), in a deliberate order ending move → attack → burrow, "so a body that died this tick is seen dead by burrow_tick" (`authsrv.py:5418-5444`). Retail's own tick cadence is variable, 6.9–40 Hz by instance load — our fixed 20 Hz is a known divergence with a correct payload ([../divergence/FINDINGS.md](../divergence/FINDINGS.md):261-287, D6, OBSERVED).

**A unit does nothing at all unless two gates pass**: `attacks_back` true **and** allegiance == hostile (`authsrv.py:3226,3234,3408,3411`, OBSERVED). Population rows default `attacks_back = False` (`authsrv.py:4285`), so **most spawned units are inert by design**; only the legacy Hatcher fixture fights by default (`:2334`). This happens to match the retail corpus — ambient locomotion is common, combat rare (5 of 76 hostiles ever fight), and in 4 of those 5 fights the player attacked first, refuting our aggro-on-approach model for the observed cases ([../monsterai/FINDINGS.md](../monsterai/FINDINGS.md) §3.1-3.2, OBSERVED) — but no comment claims the default was chosen for that reason (UNVERIFIED intent).

The distance model, constant by constant (full sabotage-tested ledger: [../monsterai/FINDINGS.md](../monsterai/FINDINGS.md) §5; current line numbers re-located, the doc's own are stale):

| Constant | Value | Label |
|---|---|---|
| `AGGRO_RANGE` (`authsrv.py:2512`) | 1200 u | RECONSTRUCTION — "Ours", doubles as notice range and (absent) leash |
| `ENEMY_MELEE_RANGE` (`:2596`) | 150 u | RECONSTRUCTION — refuted from both sides by retail per-model reach (~65 u vs ~599/706 u) |
| `ENEMY_MOVE_RATE` (`:2597`) | 0.75 × 288 = 216 u/s | RECONSTRUCTION — a fraction never observed sent to a retail hostile (80/96/100/288 u/s observed) |
| `ENEMY_TURN_RATE` (`:2623`) | 2π/3 rad/s | CORROBORATED — bit-identical to ArenaNet's own quantised maximum; the one constant that goes red under sabotage |
| rotation `atan2(dy,dx)+π` (`:3352-3367`) | — | atan2 convention CORROBORATED; the +π offset OBSERVED (owner, screen, 2026-08-11) |
| `SWING_WINDUP_RATIO` (`:2573`) | 0.4458 × declared speed | OBSERVED, n=42 clean windups; superseded a refuted flat constant |
| skill selection (`pick_skill`, `:3545-3584`) | round-robin | RECONSTRUCTION — "nothing in this project knows how a Guild Wars monster chooses" (owner's ruling as testing fixture) |

Movement uses the destination-once model — `0x0029 MOVE_TO_POINT` on transitions and past a 120-unit drift, `0x002B` speed once per chase-start, positions never streamed (`authsrv.py:3438-3451`; model shape matches retail's 16% 0x002B-per-move rate, [../divergence/FINDINGS.md](../divergence/FINDINGS.md) D8). No wander, no patrol, no leash (no spawn anchor is even stored), no pathfinding (straight line + `pathmap.clip` wall-stop; A* exists unused), no line of sight — all documented gaps, RECONSTRUCTION-by-absence ([../monsterai/FINDINGS.md](../monsterai/FINDINGS.md) §5).

**Death and revive.** Death is not removal: `hit_enemy` sets `dead=True` and sends `0x00F1` with bit 0x10, then kill reward, then flags — the order OBSERVED from exactly two uncontaminated retail kills (`authsrv.py:2925-2947`; re-derived each run by `toolkit/authsrv/test_killwindow.py`). The corpse stays in `state["agents"]`; `revive_due` clears the bit after 8 s and refills **one tick later**, because the client's death path zeroes the pools and logs `Health non-zero on resurrect` otherwise — the deferral is MEASURED, 13→0 log occurrences ([../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):502-573; `authsrv.py:2514-2529,3109-3138`). Actual world removal (`0x0021` + state pop) is exercised only by the burrow cycle (`authsrv.py:3986-4062`); no despawn-on-disconnect teardown was found (UNVERIFIED absence).

---

## 5. Player vs NPC

| | Player | NPC (`create_agent_world`) |
|---|---|---|
| model_id base | `0x30000000 \| player_number` | `0x20000000 \| definition` |
| kind byte | 5 | 9 |
| Type declaration | none — appearance is the 0x0059 packed dword | `0x0056` (+ `0x0057` if composite), once per instance |
| Identity | literal UTF-16 name in 0x0059 (the one literal-text name channel, CORROBORATED [../character/FINDINGS.md](../character/FINDINGS.md):262-275) | EncString ids in 0x0056; heroes resolve from the client's own static table |
| Attributes/skills | full bracket: 0x0037 → 0x00B7 → 0x00A6 → skills → 0x00E9 → 0x003A | none by default; 0x00A6 only if the row has a profession |
| Pools | energy 41 + health 42 | health 42 only |
| Equipment | weapon bracket 0x006E/0x0048/0x006D (+0x0161 earlier) | none — and retail agrees: 0x006E targets player-class agents 130/130, 0 NPCs |
| Party/roster | party-size/set-party/build window | none (heroes/henchmen get their own roster messages — [../heroes/FINDINGS.md](../heroes/FINDINGS.md)) |
| Control | `0x0022 WORLD_UPDATE_CONTROLLED_AGENT` — sent only for the player | never |
| Camera | no wire message exists; client-local once 0x0022 names the body (`toolkit/harness/drive_client.py:557-578`) | — |

RECONSTRUCTION caveat on the camera claim (inferred from absence + harness behaviour, not from a disassembly). One structural warning: on live traffic, player number and agent id are **two different id spaces** with a control-transfer excursion (725→300→725) we have no model of; our server works only because both constants are 1 in a solo instance ([../divergence/FINDINGS.md](../divergence/FINDINGS.md):291-322, D7, OBSERVED).

A **hero** is an NPC body plus four client-side gates, each a measured assert cleared by a specific message or ordering: `0x0074` creates `charHeroData` (ChCliHero.cpp:199); `0x0037` creates `attribState` (ChCliAttrib.cpp:156); `0x00B7` **for the hero's own agent** clears the `s_profChapter` bound (ConstChar.cpp:1296); and the order `0x0037 → 0x00B7 → 0x003A` clears ChCliAttrib.cpp:435 ([../heroes/FINDINGS.md](../heroes/FINDINGS.md):867-910, OBSERVED). The hero's identity (name/epithet/bio) never rides the wire — the server sends index 1..39 into `s_heroClientData` (40 × 24 bytes @ VA 0x00A35E08, OBSERVED). There is no `[hero.*]` content table; hero authoring is CLI flags and module globals only (OBSERVED absence).

---

## 6. What the client requires, and how it fails

### 6a. Hard crashes (asserts, OBSERVED unless noted)

| Violation | Assert | Evidence |
|---|---|---|
| `0x0020` referencing a definition slot never declared via `0x0056` | `index < m_count`, `Array.h(587)` — crash timestamp equals the packet's send timestamp | [../enemy/PLAN.md](../enemy/PLAN.md):443-458; same shared bounds primitive gates 18 of 477 handlers (`:684-694`) |
| profession before attribute points | `attribState`, `ChCliAttrib.cpp(435)` | [../character/FINDINGS.md](../character/FINDINGS.md):515-516; hit independently by two arcs |
| hero chain out of order | the four-gate sequence of §5 | [../heroes/FINDINGS.md](../heroes/FINDINGS.md):867-874 |
| float prop 34 sent as absolute instead of 0..1 fraction | `fraction <= 1.0f`, `CharPool.cpp(84)` | [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):386-397 |
| int prop 42 driven to 0 | `range > 0`, `CharPool.cpp(98)` | [../enemy/PLAN.md](../enemy/PLAN.md):571-576 (see §7 res. 1 for the superseded refill framing around it) |
| starting a swing with attack interval unset | `m_attackInterval` | `authsrv.py:6693-6702` |
| weapon "type" sent where an item id belongs | `ptr`, `ItCliApi.cpp(400)` | `authsrv.py:6674-6688` |

### 6b. Ordering rules that are measured, not stylistic

`0x0056→0x0057` paired 50/50 with zero orphans; definition before first use, once per instance ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):870-887). `0x00F0` immediately before its own `0x0020`, 472/472, never after (`:1162`). Every id worn via `0x006E` previously declared by `0x015E`/`0x0161`, 621/621 (`:1460-1465`). `0x0048` after every `0x006E`, 366/366 (`agents.py:731-738`). Party size before leader (`authsrv.py:6433-6440`). All OBSERVED.

### 6c. Non-fatal failure modes — "wrong" that does not crash

An unrecognised allegiance FourCC renders hostile, by fall-through rather than by matching a magic value ([../enemy/PLAN.md](../enemy/PLAN.md):477-524, OBSERVED). Refilling health in the same burst as a death-bit clear produces only a `Gw.log` complaint, gone when deferred one tick ([../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):502-573, OBSERVED). `0x01BF`'s embedded name string and trailing bytes are accepted and ignored — the roster reads the agent instead ([../heroes/FINDINGS.md](../heroes/FINDINGS.md):471-509, OBSERVED). A wrong kind byte silently mis-feeds downstream consumers rather than crashing ([../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md):821,960-963, CORROBORATED). Messages gated on flags bit 0x20000 are silently inert on a fresh agent ([../enemy/PLAN.md](../enemy/PLAN.md):617-655, SOURCED) — the trap that made five death-message probes read as null results. And a `SILENT` wire result never proves nothing happened ([../smsgsweep/FINDINGS.md](../smsgsweep/FINDINGS.md) §3.4, OBSERVED).

### 6d. The 0x00F0 gap — our largest known omission at create time

Retail: `0x00F0` before **every** kind-5 and kind-9 create, exceptionless, majority payload 0x0000 ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):224,1162-1183, OBSERVED). Us: the only send site is gated `if entry.get("effects"):` (`authsrv.py:3919-3921`), and every default spawn sets `effects = 0` (`:4283,4333`) — so NPCs get it only mid-burrow, and the player burst contains **no** 0x00F0 send at all (whole-file check: one declaration at `:1228`, one send site). Tracked as divergence D2 ([../divergence/FINDINGS.md](../divergence/FINDINGS.md):167-186,731), but D2's "≈0.93 per-agent ratio" framing predates the exceptionless per-kind correction, and neither D2 nor `PLAN.md`'s burrow note calls out the player-side 0/N violation — the sharper picture exists only across two documents and is connected here (OBSERVED in each part; the connection is this synthesis').

> **CLOSED 2026-08-17, the day after it was written.** Q2's census supplied the payload
> model the fix was waiting on, and the gamesrv now sends `0x00F0` unconditionally as
> the create's immediate preamble on both paths — `create_agent_world` (payload from the
> row's `effects`, else 0; heroes and henchmen inherit through the funnel) and the
> player burst (payload 0, the 342/366 kind-5 majority). `test_burrow` pins the new
> `56 57 F0 20` head; caged validation harness `20260817T152952`. The non-zero payload
> tail (kind 5's combat values, kind 9's `0x1000` ambient flag) remains future work,
> recorded at D2's closure note. The table row in §2a describes the pre-fix server.


### 6e. What the client DOES with the initial-status word — SOURCED, 2026-08-17

Added after the unconditional send landed, because "what payload should we send" deserved
an answer from the binary rather than only from the corpus. The chain, read on the pinned
build 38797:

| step | address | what it does |
|---|---|---|
| handler | `0x0091F810` | a thin trampoline: pushes `msg+8` (the status dword) and `msg+4` (the agent), calls the worker. `0x00F1`'s stub sits directly below it at `0x0091F830` → `0x00814CC0`, which is the two forms sharing one shape. |
| worker | `0x00814C30` | bounds-asserts the agent against the record count (the familiar `Array.h(587)` primitive, pushed as `0x24B`), computes the per-agent record at `[ctx+0x7C] + agent*0x34`, then calls the consumer with the word |
| consumer | `0x008183F0` | **`mov [record+0x30], eax`** — stores the ENTIRE word verbatim — then **`test al, 0x10`**, and that is the only bit it branches on |

**`test al` reads the LOW BYTE ONLY.** Bits 8–31 are stored and never examined on this
path — so `0x1000` (the hostile-NPC bit, 198/202) and the kind-5 high-word values
(6, 7, 8, 12 in bits 16–19) are **retained per agent and consumed lazily by some later
reader**, not acted on at create time. That is exactly what the wire showed from the other
side: the payload is per-agent and identical across every re-create of a visibility churn,
and no other message in the stream distinguishes a non-zero agent from a zero one
(§8 Q2's follow-up).

**The practical consequence, and it retires the risk in the D2 fix.** Sending payload `0`
for every agent cannot misbehave at create time: the only bit the create path branches on
is death, and `0` clears it. The non-zero payloads are a fidelity gap, not a correctness
one — we are not failing to trigger anything the client does when the body appears.

**The reader, found — and it is another hop rather than an answer.** Offset 0x30 is a
tiny, ubiquitous displacement: `codescan --field 0x30` returns **3,992 rows** across the
image, which is a haystack rather than an answer. The narrowing that worked: every
function touching this table must multiply by the record stride, so scanning `.text` for
`imul r32, r32, 0x34` (`6B /r ib`, register form) finds all 151 sites, of which sixteen
sit in the agent-record neighbourhood. Exactly one of those reads offset 0x30:

    0081A5FF  mov eax, [ebx+0x7c]            ; the record table
    0081A602  imul ecx, esi, 0x34            ; agent * stride
    0081A605  mov eax, [ecx+eax+0x30]        ; <-- the stored status word
    0081A609  mov [edi+0x10c], eax           ; copied WHOLESALE into another object

**A correction to this document's own first draft, kept because the mistake is
instructive.** That draft said `--field 0x30` "returns a single row" and could never have
found this access, the base+index+displacement form, because its docstring does not list
that encoding. **Both halves were wrong, and the fault was mine.** The scanner returns
3,992 rows and `0x0081A605` is among them, correctly classified `base=ecx index=eax` — it
anchors on the displacement BYTE and verifies against capstone's own encoding record, so
the addressing form never mattered. What produced the false claim was reading the output
through `tail`, which shows the last rows plus the trailing caveat block and hides the
3,991 above. **The instrument was right and the operator truncated it** — the same shape
as this repo's own "a partial run reported as a full one" defect, one level down.

So the word **propagates rather than being decided on**: create path stores it, this
function copies all 32 bits into an object at `+0x10C`, and no bit above 4 has been
branched on anywhere yet. The enclosing routine looks like a constructor — two
`memset`-shaped calls (sizes 0x24 and 8) and a `cmp dword [ebx+0x4ec], 0xDDDDDDDD` debug
sentinel above the copy.

**What would finish it** is now one well-defined step rather than a search: find what
reads `+0x10C` of the object that constructor builds. Until then every bit above 4 is
**UNVERIFIED in meaning**, and this document says so rather than naming them from their
correlations — three hops of propagation is not a semantics.

---

## 7. Contested readings, resolved

The review pass flagged three contradictions between subsystem reports. Each was resolved by reading the cited files in this tree.

**Resolution 1 — int property 42: the delta model wins; two study docs are superseded-but-uncorrected.** [../enemy/PLAN.md](../enemy/PLAN.md):577-583 ("sets the maximum AND refills to full — OBSERVED… cannot be used to set current health") and [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):175-178 ("always refilled the health bar, in every probe that used it") both still state the refill reading with no correction note. The newer measurement — [../profession/RESKIN.md](../profession/RESKIN.md):1489-1533 (harness 20260813T215004): 25/100 → max 200 gave **125**, not 200, at 62.3% against the 62.5% the delta predicts, and reversible — refutes it explicitly, names the ldufr/Headquarter `health = 1.f` lineage as the UPSTREAM source of the error, and is encoded as the live authority at `agents.py:118-132`. **This document carries `health += (new_max − old_max)`, OBSERVED**, and flags PLAN.md §6g and agentprops §1c-consequence-3 as superseded in place. One residue survives: §6g's raw observation (max→0 rendered a full bar, then crashed on `range > 0`) is not re-explained by the delta model — under a −100 delta the bar should not fill — so that single frame remains UNVERIFIED in mechanism; see open question 5. The practical consequence stands either way: re-sending the current maximum is a no-op (delta zero, RESKIN §18.12), so property 42 is not a "restore to full" lever.

**Resolution 2 — 0x00F1 is bidirectional; "only acts on a 0→1 transition" is over-compression.** The status word is **assigned whole** ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):306); the edge detection governs only a side-effect (the AgentView reset fires when bit 0x10 was clear before), confirmed by the refutation pass reading the setter's `old XOR new` (`:317`). The same section explicitly endorses the bidirectional probe — kill on set, revive on clear — as "now independently SOURCED" (`:308`), and the probe itself is OBSERVED both directions ([../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):145-158). Taken literally, the transition-only reading would make revive-by-clearing impossible, which was measured working. **Carried: 0x00F1 kills on set and revives on clear (OBSERVED + SOURCED); 0x00F0 is the pre-create snap form of the same field.**

**Resolution 3 — "0x009F has exactly three live cases" and "level travels as property 36" are both over-compressions, and the file reconciles them.** [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):290-298 (the CORRECTED section) shows **seven** dispatch layers: the three-case figure ({32, 41, 42}, SOURCED) is dispatch #1 only — the per-agent *record* path at `0x00818170` — while the int-main switch (`0x00812FE0`) has 47 real cases over ids 0–66. So property 36 is not a client no-op. The stale-reading trap: agentprops `:356-359` says PublicLevel(36) "goes to the generic case `0x008129B0`" — but that address is **int-pre's** default, not int-main's (`toolkit/clientscan/test_genericvalue.py:75,77` pins the two defaults as distinct addresses); by elimination over the published switch memberships, 36 must be one of int-main's 47 real cases (RECONSTRUCTION when this was written; **upgraded to SOURCED the same day** — open question 4 was run, the case body is `0x00812D6E` and it writes, see §8 Q4's answer). Meanwhile the "never confirmed a visible effect" caveat is itself obsolete: [../profession/RESKIN.md](../profession/RESKIN.md):1089-1108 (harness 20260813T172323) sent 36 = 1/15/20 and the roster row tracked `W1`/`W15`/`W20` exactly, against the pre-registered criterion in `toolkit/authsrv/probes.py:361`. **Carried: property 36 is the per-agent displayed level — OBSERVED for the player's own agent via the roster readout; the CORROBORATED upstream-lineage label of [../character/FINDINGS.md](../character/FINDINGS.md):1139 stands for the general claim; the nameplate/NPC surface is CORROBORATED-by-structural-similarity only** (superseded same-arc: the `henchman_level` run of 2026-08-17 OBSERVED a second agent's roster row tracking prop 36 — §8 Q3; the floating-nameplate surface alone stays unprobed).

---

## 8. Open questions, with the cheapest experiment for each

1. **Is the hero 0x01C2 default word order stale?** `HERO_SWAP = False` (`authsrv.py:2254`) makes the default path send `party_hero_add(1, HERO_AGENT_ID, HERO)` — word_a (msg+8) = agent id (`authsrv.py:6488-6496`; `agents.py:510-539`). But §11.1 settled msg+8 = **hero index** ([../heroes/FINDINGS.md](../heroes/FINDINGS.md):556-578): the default arm is H1, the one that **rendered nothing**. Cheapest: read the capture from the landing run behind commit 253b863 and check which words the winning session actually sent — pure offline, no client launch. If it used `--hero-swap`, flip the default and rename the parameters.
   **ANSWERED 2026-08-16, same day — twice, and the second round corrected the first.** Round one: it did not even need the capture — the winning arm is in the study's own table (H2, `wordA=1 wordB=200`, the swap order), the default was stale exactly as suspected, and the flip landed with parameters renamed `hero_index, agent_id`. Round two, hours later: a parallel desk-work arc ([../heroes/FINDINGS.md](../heroes/FINDINGS.md) §17) read GmHeroCommander's own party scan and narrowed §11.1 — **msg+0xc = agent id is the only word H1/H2 truly settled**; msg+8 is UNVERIFIED, owner-leaning (its filter is a "my id" accessor, and player number, hero index and owner agent id are ALL 1 in every rig that rendered — the exact confound §11.1 warned about at agent 200 and then walked into one field over); and msg+0x10 → entry+0x8 is the commander-scan **key** (SOURCED), with the hero id there RECONSTRUCTION — §17.2 refuted the prediction that filling it fixes the commander click. The code now reflects round two: `party_hero_add(party_id, word_a, agent_id, hero_key, unk_b)` — `word_a` deliberately positional again — with the default sending `PLAYER_NUMBER` at msg+8, the agent at msg+0xc, the hero id as `hero_key`, and `--hero-swap` re-sending H1 (renders nothing) as the control. `hero_index` was a parameter name for roughly six hours, which is this repo's "naming either one would bake a guess into the call site" warning proving itself on schedule. **Round three, the same evening:** the separating rig ran in a parallel session ([../heroes/FINDINGS.md](../heroes/FINDINGS.md) §18) — hero index **2** with msg+8 still carrying 1, and the row rendered "Mo1 Goren" — so msg+8 ≠ hero index is now refuted **by experiment**, not just questioned. What msg+8 is remains UNVERIFIED, owner-shaped; the residual tie (owner player number vs owner agent id, both 1 in every rig so far) needs a player number that differs from the player's agent id. **Round four, and the question is CLOSED:** that rig ran too ([../heroes/FINDINGS.md](../heroes/FINDINGS.md) §21) — `--player-number 2` split the candidates, and msg+8 is the **owner PLAYER NUMBER, OBSERVED**: the roster row renders exactly when the field equals the declared player number, consistent across all three rigs. Two rounds beyond it: §19 measured that `0x01C2` carries **no hero identity at all** (a wrong value at msg+0x10 changes nothing — identity lives in `0x0074`'s data-cache record; the party message only binds a slot to an agent), and §21.2 found the two consumers of entry+0x4 compare it against **different** "my id" notions — the arm that renders the roster row is the arm whose commander binding vanishes. The signature's final form is `party_hero_add(party_id, owner_player_number, agent_id, scan_key, unk_b)`: four renames in one day, each tracking a measurement, and the only name that was ever wrong (`hero_index`) is the only one that reached a parameter without one. The residue this leaves for the heroes arc: §21.2's split filter, and msg+0x14's meaning (§20.3).
   **A day later, one clause above retired — and the name held.** "A wrong value at msg+0x10 changes nothing" was true of every observable §19 had, because the commander scan never ran in those sessions: the PvP-UI arc found the rebuild raised into the subscriber map **53 ms too early** ([../pvpui/FINDINGS.md](../pvpui/FINDINGS.md) §19), and with `--party-mine-late` the scan runs and takes exactly this field as the key the commander is filed under — steerable, proven by driving it to 200 with `--hero-roster-id`. `scan_key` turned out to be the right name twice over: it names what the scan reads, and it never claimed the value was a hero id. `0x01C2` still carries no hero *identity* — the roster label's name and profession come from `0x0074`'s record either way.
2. **What payload should a kind-5 (player) 0x00F0 carry?** The 472-corpus payload breakdown exists ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):224) but is not split by kind. Cheapest: re-run the existing corpus census splitting payload by `0x0020` field[4] — offline analysis of tapes already in the vault.
   **ANSWERED 2026-08-17, OBSERVED — `toolkit/authsrv/createburst.py`, predictions on record in its docstring.** Corpus: all three keyed live captures, 12 connections, 951 paired `0x00F0`s (the study's 472 was the one-session subset; subject convention runtime-verified 951/951). The split: **kind 9 (NPC): `0x0000`×357, `0x1000`×202, `0x2000`×1** — the non-zero mass is NPC-side and `0x1000` is its flag, as predicted. **Kind 5 (player): `0x0000`×342, but 24 non-zero** — `0x2000`×4 in the first session, and high-word payloads (`0x60000`×8, `0x70000`×4, `0x80000`×4, `0xC0000`×4) all in the 20260810 combat capture — so the prediction's "a player arrives before anything can be true of it" is refuted in the tail: **"always send 0" is retail-typical for 93% of player creates and wrong for the rest**, and D2 eventually needs a payload model, exactly as [../divergence/FINDINGS.md](../divergence/FINDINGS.md):731 guessed. Two novelties the old corpus could not show: **kind 8 exists** (25 creates, combat capture only — the 472-corpus's "iff kind ∈ {5, 9}" gate extends to it), and **one kind-8 body arrived already dead** — payload `0x0010` = CHAR_STATUS_DEAD, the value the study measured at 0/472 — so spawning a corpse via `0x00F0` is retail-attested, not just SOURCED from the handler.
3. **Does an NPC's nameplate/target window read the same prop-36 field the roster does?** Cheapest: the already-specified `agent_level` probe ([../enemy/PLAN.md](../enemy/PLAN.md):1738-1740) — prop 36 at a second agent, watch the nameplate. One caged run.
   **ANSWERED for the substance 2026-08-17, OBSERVED — harness `20260817T142147`, the first agent-piloted probe run in this repo (launched, keyed, screenshotted and read with no operator present).** New probe `henchman_level` (`toolkit/authsrv/probes.py`, prediction on record): `--henchman hatcher --henchman-body` puts a second live agent (id 30) in the party, and prop 36 at THAT agent moved ITS roster row through **`Mo1` → `Mo15` → `Mo20`** (frames hold002/hold005/hold008-014, each bracketed against the gamesrv log's three sends), while the player's own row sat at `W0` and the per-player `0x00E9` bar sat at `Level: 1` — two in-frame controls, neither moved. So **the prop-36 store is written AND read back per-agent, not just for the local player** — the on-screen half of Q4's `entry+0x2C` disassembly. The row's starting `Mo1` equals the hatcher's `0x0056` `level = 1` byte (`content/npcs.toml:18`), turning the UPSTREAM "byte(dword7) = default level" reading ([../enemy/PLAN.md](../enemy/PLAN.md):159-169) into the best explanation for where a row's level comes from BEFORE any 0x009F — though that frame is also step 1's, so the two channels are not separated at value 1; the 15 and 20 readings had no competing channel. **Still open, narrower:** the floating nameplate/target-frame surface for a non-party NPC (GW may not even render level there), and whether retail henchman rows are fed by pre-create `009F:36` the way player creates are (Q7's census).
4. **What does int-main's case 36 actually write?** Cheapest: `python toolkit/clientscan/genericvalue.py --id 36` against the pinned vault exe — no client launch, minutes.
   **ANSWERED 2026-08-16, same day, SOURCED (build 38797, pinned pristine).** `genericvalue.py --id 36` derives a real int-main case body at `0x00812D6E` — not the generic default `0x008129B0` the stale agentprops line claimed. Disassembled (`codescan.py --dis 0x00812D6E`): two container calls keyed on the agent id against the manager object's field `+0x7CC` (`0x00817BE0`, then `0x0080BC90` which returns the per-agent entry), then **`mov [entry+0x2C], value`**, then `0x007DFE10(agent, value)` — a persistent per-agent store plus a notification. The dispatcher prologue confirms the register roles: the handler's args are `(property_id, agent_id, ?, value)`, the agent id is bounds-asserted against the record count, and the value survives untouched to the case. So property 36 is a real per-agent write for ANY agent id, which strengthens — but does not yet prove — that the NPC nameplate reads the same store; Q3's caged probe remains the on-screen half.
5. **The §6g residue under the delta model** (max→0 rendered full, then `range > 0`). Cheapest: re-run the kill probe's step with intermediate maxima (100→50→10) using RESKIN §18.13's HUD-number method, which reads exact values rather than bar fills.
   **ANSWERED 2026-08-17, OBSERVED — harness `20260817T143333`, probe `health_shrink`, and the mechanism is sharper than any of the three candidates pre-registered.** The HUD-number sequence, frame-bracketed: **50 (full bar) → 100 → 25 → 1 → 25**. Steps 1–3 are the delta model doing what it says (a shrink onto a full pool lands exactly at the new maximum — §6g's "refilled to full" was never a refill, it is the delta's own arithmetic at `health == max`). The discriminator pair is the find: shrinking max 100→50 on a 25/100 pool displayed **1**, and restoring the max returned **exactly 25** — not 51 (store clamped at 1), not 50 (refill), not 12 (fraction survives). The only arithmetic consistent with 25-out is `25 + (50−100) = −25` held in an **unclamped signed store** while the HUD **floors the display at 1**, then `−25 + 50 = 25`. So: current health is signed and can be driven below zero by a max-shrink grant with no complaint; the floor-at-1 this repo knows from the damage path (`agents.py` PROP_DAMAGE, "floors at 1: cannot kill") is at least partly a DISPLAY floor, not a store floor; and §6g's residue dissolves — the full bar at max→0 is the delta landing on max plus max-0's render degeneracy, with `range > 0` the only real event in that frame.
6. **0x006E slot order for Legs/Head/Boots/Gloves** — CONTESTED, one lineage vs two ([../character/FINDINGS.md](../character/FINDINGS.md):1481). Cheapest: the per-slot `0x006F` probe — send one item to one named slot and look.
   **ANSWERED 2026-08-17, OBSERVED — harness `20260817T150232`, probe `armor_slots` — and the contest DISSOLVES for pixels.** Three findings, frame-bracketed with a proven-clean reset between arms (the nine-zero `0x006E` wiped leggings and hammer alike before each re-wear): (1) **`0x006F` is per-slot wear** — the gray starter leggings (new `content/items.toml` rows, the rest of the hammer's own OpenTyria array) rendered on the body from a bare `0x0161` + `0x006F`, refuting the sibling track's doubt about the 109/110/111 mapping. (2) **The ITEM drives its own body placement**: the same leggings rendered on the legs from position 3 AND from position 5 — the slot number does not choose the body part, so no visual experiment can distinguish bag order from the permutation, and the CONTESTED label survives only as protocol bookkeeping (what could still settle it: a client-side read of the equipped-bag memory, or behavior keyed to a position, e.g. the costume slots). (3) The array arm — leggings at 3, boots at 5 through the nine-dword `0x006E`, bag order's own claim — dressed both pieces correctly, CONSISTENT with bag order and, under item-driven placement, incapable of refuting the permutation. Practical consequence: dressing a body is order-safe — declare with `0x0161`, place with either message, and the pieces sort themselves out; the five warrior starter-armor rows now exist in content for whenever the Test Warrior stops being naked. Untested residue: whether position semantics matter for the HANDS (the weapon has only ever been sent at position 0).
7. **Does retail enforce any ordering among the post-create messages (0x009F/0x00A6/0x0026)?** Our order is RECONSTRUCTION. Cheapest: adjacency-with-subject-match measurement over the existing four tapes, the same instrument §3 of the smsg study already built.
   **ANSWERED 2026-08-17, OBSERVED — same run of `createburst.py`, 1,068 creates, and the prediction ("no strict rule") is refuted in an unexpected direction.** The question dissolves rather than resolves: **retail barely sends our post-create repertoire at create time at all.** The kind-split templates: **kind 5 (player)** is `009F:30 (ApplyGuild1) → 00A6 (profession) → 009F:36 (level) → 00F0 → 0020` with an *empty* post-create tail (344/366 in the two dominant templates) — retail delivers guild, profession and level **before** the body exists, where our burst sends everything after. **Kind 9 (NPC)** is `(009F:66) → 00F0 → 0020 → 006D (NPC_UPDATE_WEAPONS) → 0026 (flags)` — and `009F:42` (health max) appears **zero** times in any create burst, confirming from a second direction that retail leaves spawn health to the client's full-bar default and health-max is a rare mid-combat correction ([npcdefs.py](../../toolkit/authsrv/npcdefs.py)'s five-observations note). The rules that do exist: **`006D` before `0026`, 200/200** (extending the overrides note's 151/155 adjacency) and `006D` before `009F:11 (ApplyMarker)`, 48/48; leans at smaller n: `0026` before `00F1` 14/14, post-create `009F:36` before `009F:30` 11/11. **Consequences for our server:** our NPC tail order (health → profession → flags) violates no measured rule — the messages it orders are ones retail doesn't send there, so the RECONSTRUCTION label stands with its reason now measured; our `0026`-as-tail matches retail's shape; the real divergences are repertoire, not order — we omit `006D` (it needs an item id we don't author yet, `authsrv.py`'s own comment) and we send at create time what retail sends never (42) or pre-create (A6). Property 66, the NPC pre-create constant, is past OpenTyria's enum and unnamed anywhere — UNVERIFIED meaning, real int-main case at `0x00812EBD`.
8. **The 0x0047/position write-up gap.** The code's current trust-the-client policy rests on a session recorded only in comments (`authsrv.py:6340-6355`), and [../movement/FINDINGS.md](../movement/FINDINGS.md):649-655 says the opposite. Cheapest: no experiment — a superseding note in the movement FINDINGS citing the session, the same fix its own §2b already models.
   **ANSWERED — and it was already done when this list was written, which is the bookkeeping half of the same defect.** The superseding note went into [../movement/FINDINGS.md](../movement/FINDINGS.md) §7 on 2026-08-16 (the day this study was drafted): the section now opens with its own stale-side warning, cites `authsrv.py`'s comment as the record of the session that reversed the policy, carries the four indefensible corrections, and keeps `on_mesh` (57/61) as evidence about our map data rather than grounds for moving the player. What stayed open for a day was this line, not the work — an item marked open because nobody came back to mark it closed, which is exactly the staleness the top of `CLAUDE.md` is about.
9. **Definition-index collisions across areas** — `area_population()` validates within one area only (`authsrv.py:4160-4187`); no global registry exists. Cheapest: a static whole-content check in `test_population.py`, no client involved.
   **ANSWERED 2026-08-17, and the question sharpened on contact.** Cross-*area* collisions cannot happen — one area loads at a time, and areas replace the global test enemy (the mutual exclusion section 3 AST-proves). What CAN collide is the **party**: player agent 1, henchman 30/definition 9, and up to seven hero bodies at 200..206/definitions 10..16 co-load with *any* area, and `--area sculpt --hero 1,2,3` was a legal command line no check examined. The guard now lives in `area_population()` itself — refusal at load, not at spawn, the file's own "a wasted client run" rule — and `test_population.py` section 5 proves it both ways: six reserved-id sabotages redden, the real store passes, and the test enemy's ids are the deliberate non-example the guard must accept (floor 43 → 51).
10. **What the client renders for a declared-but-composite-less definition** (0x0056 sent, no 0x0057, file needing one) — NOT FOUND in any study; only the crash case (undeclared slot) is measured. Cheapest: one caged run sending a COMPOSITED-flagged file id with the 0x0057 withheld, screenshot the result.
    **ANSWERED 2026-08-17, OBSERVED — harness `20260817T143717`, probe `composite_withheld`, map 449.** Two definitions identical down to one message (76 without its 0x0057, 77 with), two creates four seconds apart, attribution locked by sequence: the frame between the creates shows the control hatcher bodied normally and nothing else; the frame after the second shows the new render — **a solid white untextured box, roughly body-sized, standing at the probe body's spot**. So the missing composite is neither a crash (the declared slot indexes cleanly — the Array.h(587) death is exclusively the UNdeclared case) nor invisibility: **the client draws a positive placeholder volume**. Practical consequences: a content row that loses its `model_id` fails LOUDLY on screen while staying wire-legal, which is the good failure direction; and a white box in any authored area is now a known signature — "the 0x0056 file needed a composite nobody sent" — worth knowing before someone reads one as a texture bug. The no-0x0057 rows retail itself ships (8/44, `content/npcs.toml`'s lakeside_worm note) are the OTHER side of the law: their files carry their own geometry, and this run is the missing cell that proves the flag is what separates the two.
11. **Corpus breadth.** All four tapes share one character, one account, two areas — every "4/4 tapes agree" figure is one character record sampled four times ([../smsg/FINDINGS.md](../smsg/FINDINGS.md), caveats). Cheapest real fix: one live capture on a different character, under the existing `RUNBOOK.md` live procedure and behavioural rules.
    **ANSWERED 2026-08-17, OBSERVED — and it is the arc's last item, so the ladder is closed.** Two live captures on a **new Factions character**, owner-driven under the behavioural rules: `20260817T180610` (creation + first login in the starter zone, salvaged from an interrupted run with `--assemble`) and `20260817T183756` (Shing Jea Monastery, 13/13 plan steps marked, plan seals **AGREE**, `game_mode: base` operator-declared, `exe_unchanged: True`, 5 keys tapped, 952,683 wire bytes, **all four game channels decoding to their final byte**, 9,329 s2c messages). What the second witness settled:
    - **The create preamble is a RULE, and its real shape is now measured.** Across **all five** keyed captures: **1,131/1,131** kind-5/kind-9 creates carry their own `0x00F0` — **567** directly before, **564** with exactly one `WORLD_SIMULATION_TICK` (`0x001E`) between, **never further away and never absent**. The tick is the *only* opcode that ever interposes. This reproduces [../smsg/FINDINGS.md](../smsg/FINDINGS.md):1181's raw-stream split (187 adjacent / 285 tick-separated in capture 143055) **exactly**, from an independent decoder — so the study was right and precise, and what was wrong was this document's own summary, which had dropped its "with `0x001E` removed" qualifier and called the relation "immediately, exceptionless". Corrected in §1c and at the server's send site. Our server emits them adjacent, which is what retail does in 567 of 1,131 creates: inside the envelope, not a divergence.
    - **A dressed body, at last.** `0x006E` carries **six** non-zero slots in 23 of its 35 messages (five in 6, four in 4, seven in 2) — the first multi-slot sample in the corpus, whose entire prior evidence was one weapon at position 0 plus two probe pieces.
    - **`0x006D` weapon ids are item records, confirmed on new ground**: 73/73 non-zero ids were declared earlier in the same stream, and 59 carried item **0** — the legal no-weapon value. (An earlier pass reported 17 undeclared; that was an artifact of one channel not yet loaded, and the count went to zero once all four decoded. Recorded because the near-miss is the lesson: a partial corpus refutes things that are true.)
    - **Removal discipline holds**: **143/143** `0x0021` removals targeted an agent that was live at that moment, zero removals of a never-created id. The 43 ids removed "twice" are ordinary visibility churn — create → remove → re-create → remove — which only reads as an anomaly if you forget to track state, as a first pass here did.
    - **A death and a revival on the real service, the first ever captured.** Agent 27 took `0x00F1` with the status word `0x10`, then `0x00F1` with `0x0` — and was still there to revive, so death is a **status bit and not a removal**, exactly as predicted and as [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md) measured from our own client. Other status words seen: `0x100` (×8) and `0x80` (×1), both unread.
    - **Levels that are not 1**: prop 36 carried 2, 3, 4, 8, 9, 10, 11, 20 and **30** — the last above the player cap, so some body (a boss or a special NPC) is level 30. No level-1 sighting at all in the Monastery capture.
    **What the run did NOT settle, honestly:** a level *changing* on one agent (still unobserved — see PLAN §8's named tutorial capture), and one integrity puzzle worth chasing — `tape.py` refused one channel because it counted **50,391** wire bytes where the decrypt consumed **50,153** (the manifest agrees with the decrypt), so ~216 bytes in `wire.jsonl` are not part of that channel's plaintext. TCP retransmits are the obvious candidate and nothing has checked. The channel's plaintext itself decodes perfectly, so only *tape replay* is affected, not the census.

## THE LEVEL-UP, OBSERVED — twice, and the open question above is CLOSED. 2026-08-19

This document's own "what the run did NOT settle" names *"a level **changing** on one
agent (still unobserved)"*. It is observed now, in capture `20260819T132414` (the operator
marked it live, note ordinal 2) and again in `20260807T143055`, which had been sitting in
the vault for twelve days.

**METHOD: the quest reward is the CONTROL.** A window around a level-up alone names forty
opcodes and proves nothing. The operator marked two events — note 1 "accepting quest
reward" (`wire_t` 227.60) and note 2 the level-up (278.49) — and **both are quest turn-ins
answered by the same reward machinery**, so differencing them isolates the transition.
Shared by both, and therefore NOT levelling: `0x005D`/`0x005E` chat, `0x009C [agent, 100]`,
`0x00EE [10, 0]`, the XP row `0x00EE [0, N]` (**100** vs **1000**), the gold credit
`0x0140 [inv, N]` (**10** vs **50**), and `0x0052` quest-remove.

**THE BURST, and it is one frame:**

| message | reading | evidence |
|---|---|---|
| `0x009F [37, agent, 3]` | **LEVEL UP — the new level** | see below |
| `0x009F [42, agent, 140]` | **maximum health** | `100 + 20×(level−1)` |
| `0x0039 [agent, 10]` | **total attribute points** | the wiki's level table |
| `0x0038 [agent, 6]` | **NOT IDENTIFIED** | see the caution below |
| `0x00EE [14,1] [13,1] [9,1]` | three reward rows absent from the control | |

**PROP 37 IS THE EVENT, PROP 36 IS THE STATE — and that distinction is what makes this
readable.** `0x009F` prop 36 has **1,819** sightings across the corpus (values 1–20 and 30,
dominated by 1 and 20): every agent's level, broadcast at creation. Prop 37 has **two**, and
both sit at a transition. Agent 323 in `20260807T143055` is the clean one:

```
t=10.98   prop 36 = 16      the state
t=21.06   prop 37 = 17      THE LEVEL-UP, carrying the NEW level
t=24.90   prop 36 = 17      the state again, now agreeing
```

**AND THE ARITHMETIC CLOSES ON GW'S OWN PUBLISHED TABLES, which the capture did not
supply.** Our player (agent 27) loaded at prop 36 = **2** with prop 42 = **120**, then
levelled to prop 37 = **3** with prop 42 = **140**:

> WIKI (GWW, "Health" §Maximum health, fetched 2026-08-19): *"Roleplaying characters start
> at level 1 with 100 health. This increases at 20 health per level up to a maximum of 480
> health at level 20."*

`100 + 20×(2−1) = 120` ✓ and `100 + 20×(3−1) = 140` ✓. The whole prop-42 histogram lands on
that ladder — **100 ×16, 120 ×11, 140 ×7, 480 ×35** — with the off-ladder values (455, 483,
555, 590) all under the wiki's stated 610 rune-and-insignia ceiling, which is what that page
says should happen. And:

> WIKI (GWW, "Attribute point" §Level progression, fetched 2026-08-19): level 3 → **10**
> total attribute points.

`0x0039 [27, **10**]` at a level-up to 3. **Three fields, one level, agreeing through two
tables from a source that shares no code or ancestry with anything in `vault/`** — so this
is CORROBORATED rather than one witness counted twice.

**WHAT IS PRIVATE AND WHAT IS PUBLIC, stated as the leading reading rather than a fact:**
the 16→17 level-up carried **only** props 37 and 36, with no `0x0039`, no `0x0038` and no
prop 42, while our own player's carried all of them. The natural explanation is that level
is broadcast to everyone in view and attribute points and maximum health go only to the
owner — but agent 323's identity was never established, so this is RECONSTRUCTION. The
cheap test is a second player in view of one of ours.

**TWO HONEST GAPS.** `0x0038 [27, 6]` sits in the level-up frame and is **not** level-up
machinery: it has 15 sightings across the corpus on four other agents, values 5/25/41/54/65/74,
including a descending run 65→54→41→25→5 that looks like a bar draining. It is NOT
IDENTIFIED and 6 is not the level, the points or the health. And prop 36 was **not** re-sent
to agent 27 after its level-up, though it was to 323 — recorded because it is a real
asymmetry and not smoothed over.

**A NEAR-MISS WORTH KEEPING.** The first pass read prop 37 as "the level" outright and would
have contradicted this document's settled prop-36 finding. What caught it was checking the
existing claim before publishing rather than after: 1,819 sightings against 2 is not two
readings of one field, it is two different fields. **The corpus's own frequency was the
tell, and a single-capture reading could not have seen it.**

