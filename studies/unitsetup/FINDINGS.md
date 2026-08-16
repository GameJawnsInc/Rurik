# How a unit comes to exist — server and client setup of agents

**2026-08-16.** This is a **synthesis over existing code and studies, not new measurement**: nothing below was probed, captured or disassembled for this document. It stands on [../smsg/FINDINGS.md](../smsg/FINDINGS.md) (wire corpus + client asserts for the agent-lifecycle opcodes), [../character/FINDINGS.md](../character/FINDINGS.md) (player identity/appearance/level channels, and the label vocabulary used throughout), [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md) (property dispatch, death bit), [../unitmodels/FINDINGS.md](../unitmodels/FINDINGS.md) (model/composite resolution), [../heroes/FINDINGS.md](../heroes/FINDINGS.md) (the four hero gates), [../enemy/PLAN.md](../enemy/PLAN.md) (definition-slot and death probes), [../monsterai/FINDINGS.md](../monsterai/FINDINGS.md) and [../divergence/FINDINGS.md](../divergence/FINDINGS.md) (behaviour fidelity), [../movement/FINDINGS.md](../movement/FINDINGS.md) and [../profession/RESKIN.md](../profession/RESKIN.md) (position and level measurements), [../msgtable/FINDINGS.md](../msgtable/FINDINGS.md) (independent static recovery of message shapes), plus the live server code (`toolkit/authsrv/authsrv.py`, `toolkit/authsrv/agents.py`, `toolkit/content.py`).

Labels are the vocabulary of [../character/FINDINGS.md](../character/FINDINGS.md):15-21 — OBSERVED, UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND. The smsg/agentprops studies additionally use **SOURCED** for claims read out of the client's own compiled asserts/disassembly; that label is carried through where those studies use it. Where a source doc already labels a claim, its label is carried, not upgraded. `schema/messages.json` is imported from OpenTyria, so our schema and our server agreeing is **one** witness (`schema/messages.json:2`, UPSTREAM base; CORROBORATED only once `schema/overrides.json` is applied per [../msgtable/FINDINGS.md](../msgtable/FINDINGS.md):242).

Three contradictions flagged by the review pass are resolved in §7, each by reading the cited files; the resolutions are also applied inline where the affected claims appear.

**File:line citations were read at commit `fd63344`.** `main` had already grown `toolkit/authsrv/authsrv.py` by ~29 lines (insertions near :2252 and :6842) before this doc merged, so numbers cited above those points drift by that much — re-locate by symbol or quoted comment, not by number, the same way [../monsterai/FINDINGS.md](../monsterai/FINDINGS.md) is read.

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
6. **The player-create burst** (`authsrv.py:6404-6709`, OBSERVED, in send order): PLAYER_DATA bracket → `INSTANCE_LOADED` → `PLAYER_INFO` 0x0059 ("PLAYER_CREATE": player number, agent id, appearance dword, name) → party-of-one bracket (size before leader — order load-bearing) → **`WORLD_CREATE_AGENT` 0x0020** (`authsrv.py:6517-6536`) → `AGENT_UPDATE_ATTRIBUTE_POINTS` 0x0037 (**must precede profession** or the client asserts `attribState` — `authsrv.py:6537-6547`, OBSERVED crash) → `PLAYER_UPDATE_PROFESSION` 0x00B7 → `AGENT_SET_PROFESSION` 0x00A6 → unlocked skills → `SKILLBAR_UPDATE` → `CHARACTER_UPDATE_FACTIONS` 0x00E9 (field 9 = level 1, `authsrv.py:6603-6606`) → `AGENT_UPDATE_ATTRIBUTES` 0x003A → energy/health maxima on 0x009F (`authsrv.py:6628-6635`) → weapon bracket (`0x006E` → `0x0048` → `0x006D` → attack speed 0x0035, `authsrv.py:6660-6702`) → **`WORLD_UPDATE_CONTROLLED_AGENT` 0x0022** — the control transfer, `[agent_id, 3]` (`authsrv.py:6704-6705`) → `INSTANCE_LOAD_FINISH`.
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

The retail create idiom is measured with zero exceptions ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):1162-1198, OBSERVED): `0x00F0` immediately precedes its agent's `0x0020` **472/472**; the gate is `0x0020` field[4] — `0x00F0` iff kind ∈ {5 player, 9 NPC} (130/130 and 342/342), `0x0115` iff kind 1 (44/44), visual equipment `0x006E→0x0048` only inside kind-5 creates (76/130, 0/397 elsewhere). The most common full template is `009F 00F0 0020 006D 0026` (132/527); only 5/527 creates are a bare `0x0020`. Removal is the opposite shape: `0x0021` is a lone message 413/416 (99.3%), `[agent_id]` only, 0 double-removes, 0 removals of a never-created id ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):260,1185, OBSERVED) — a discipline our `remove_agent()` reproduces and enforces (`authsrv.py:3797-3842`, OBSERVED).

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
| level | **never sent per-agent at spawn** (0x009F prop 36 unsent for everyone); player gets per-player level 1 via 0x00E9 field 9 only | `authsrv.py:6603-6606`; no prop-36 send site in the spawn paths | OBSERVED; consequences in §2b |
| effects / initial status | `0`, so no `0x00F0` at all | `authsrv.py:4283,4333,3919-3921` | OBSERVED code; a measured divergence from retail's 472/472 — §6d |
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

---

## 7. Contested readings, resolved

The review pass flagged three contradictions between subsystem reports. Each was resolved by reading the cited files in this tree.

**Resolution 1 — int property 42: the delta model wins; two study docs are superseded-but-uncorrected.** [../enemy/PLAN.md](../enemy/PLAN.md):577-583 ("sets the maximum AND refills to full — OBSERVED… cannot be used to set current health") and [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):175-178 ("always refilled the health bar, in every probe that used it") both still state the refill reading with no correction note. The newer measurement — [../profession/RESKIN.md](../profession/RESKIN.md):1489-1533 (harness 20260813T215004): 25/100 → max 200 gave **125**, not 200, at 62.3% against the 62.5% the delta predicts, and reversible — refutes it explicitly, names the ldufr/Headquarter `health = 1.f` lineage as the UPSTREAM source of the error, and is encoded as the live authority at `agents.py:118-132`. **This document carries `health += (new_max − old_max)`, OBSERVED**, and flags PLAN.md §6g and agentprops §1c-consequence-3 as superseded in place. One residue survives: §6g's raw observation (max→0 rendered a full bar, then crashed on `range > 0`) is not re-explained by the delta model — under a −100 delta the bar should not fill — so that single frame remains UNVERIFIED in mechanism; see open question 5. The practical consequence stands either way: re-sending the current maximum is a no-op (delta zero, RESKIN §18.12), so property 42 is not a "restore to full" lever.

**Resolution 2 — 0x00F1 is bidirectional; "only acts on a 0→1 transition" is over-compression.** The status word is **assigned whole** ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):306); the edge detection governs only a side-effect (the AgentView reset fires when bit 0x10 was clear before), confirmed by the refutation pass reading the setter's `old XOR new` (`:317`). The same section explicitly endorses the bidirectional probe — kill on set, revive on clear — as "now independently SOURCED" (`:308`), and the probe itself is OBSERVED both directions ([../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):145-158). Taken literally, the transition-only reading would make revive-by-clearing impossible, which was measured working. **Carried: 0x00F1 kills on set and revives on clear (OBSERVED + SOURCED); 0x00F0 is the pre-create snap form of the same field.**

**Resolution 3 — "0x009F has exactly three live cases" and "level travels as property 36" are both over-compressions, and the file reconciles them.** [../agentprops/FINDINGS.md](../agentprops/FINDINGS.md):290-298 (the CORRECTED section) shows **seven** dispatch layers: the three-case figure ({32, 41, 42}, SOURCED) is dispatch #1 only — the per-agent *record* path at `0x00818170` — while the int-main switch (`0x00812FE0`) has 47 real cases over ids 0–66. So property 36 is not a client no-op. The stale-reading trap: agentprops `:356-359` says PublicLevel(36) "goes to the generic case `0x008129B0`" — but that address is **int-pre's** default, not int-main's (`toolkit/clientscan/test_genericvalue.py:75,77` pins the two defaults as distinct addresses); by elimination over the published switch memberships, 36 must be one of int-main's 47 real cases (RECONSTRUCTION when this was written; **upgraded to SOURCED the same day** — open question 4 was run, the case body is `0x00812D6E` and it writes, see §8 Q4's answer). Meanwhile the "never confirmed a visible effect" caveat is itself obsolete: [../profession/RESKIN.md](../profession/RESKIN.md):1089-1108 (harness 20260813T172323) sent 36 = 1/15/20 and the roster row tracked `W1`/`W15`/`W20` exactly, against the pre-registered criterion in `toolkit/authsrv/probes.py:361`. **Carried: property 36 is the per-agent displayed level — OBSERVED for the player's own agent via the roster readout; the CORROBORATED upstream-lineage label of [../character/FINDINGS.md](../character/FINDINGS.md):1139 stands for the general claim; the nameplate/NPC surface is CORROBORATED-by-structural-similarity only** (the planned `agent_level` probe, [../enemy/PLAN.md](../enemy/PLAN.md):1738-1740, is still unrun).

---

## 8. Open questions, with the cheapest experiment for each

1. **Is the hero 0x01C2 default word order stale?** `HERO_SWAP = False` (`authsrv.py:2254`) makes the default path send `party_hero_add(1, HERO_AGENT_ID, HERO)` — word_a (msg+8) = agent id (`authsrv.py:6488-6496`; `agents.py:510-539`). But §11.1 settled msg+8 = **hero index** ([../heroes/FINDINGS.md](../heroes/FINDINGS.md):556-578): the default arm is H1, the one that **rendered nothing**. Cheapest: read the capture from the landing run behind commit fd63344 and check which words the winning session actually sent — pure offline, no client launch. If it used `--hero-swap`, flip the default and rename the parameters.
   **ANSWERED 2026-08-16, same day — twice, and the second round corrected the first.** Round one: it did not even need the capture — the winning arm is in the study's own table (H2, `wordA=1 wordB=200`, the swap order), the default was stale exactly as suspected, and the flip landed with parameters renamed `hero_index, agent_id`. Round two, hours later: a parallel desk-work arc ([../heroes/FINDINGS.md](../heroes/FINDINGS.md) §17) read GmHeroCommander's own party scan and narrowed §11.1 — **msg+0xc = agent id is the only word H1/H2 truly settled**; msg+8 is UNVERIFIED, owner-leaning (its filter is a "my id" accessor, and player number, hero index and owner agent id are ALL 1 in every rig that rendered — the exact confound §11.1 warned about at agent 200 and then walked into one field over); and msg+0x10 → entry+0x8 is the commander-scan **key** (SOURCED), with the hero id there RECONSTRUCTION — §17.2 refuted the prediction that filling it fixes the commander click. The code now reflects round two: `party_hero_add(party_id, word_a, agent_id, hero_key, unk_b)` — `word_a` deliberately positional again — with the default sending `PLAYER_NUMBER` at msg+8, the agent at msg+0xc, the hero id as `hero_key`, and `--hero-swap` re-sending H1 (renders nothing) as the control. `hero_index` was a parameter name for roughly six hours, which is this repo's "naming either one would bake a guess into the call site" warning proving itself on schedule. **Round three, the same evening:** the separating rig ran in a parallel session ([../heroes/FINDINGS.md](../heroes/FINDINGS.md) §18) — hero index **2** with msg+8 still carrying 1, and the row rendered "Mo1 Goren" — so msg+8 ≠ hero index is now refuted **by experiment**, not just questioned. What msg+8 is remains UNVERIFIED, owner-shaped; the residual tie (owner player number vs owner agent id, both 1 in every rig so far) needs a player number that differs from the player's agent id. Three readings of one u16 in one day, each narrower than the last, and only the middle one ever reached a parameter name.
2. **What payload should a kind-5 (player) 0x00F0 carry?** The 472-corpus payload breakdown exists ([../smsg/FINDINGS.md](../smsg/FINDINGS.md):224) but is not split by kind. Cheapest: re-run the existing corpus census splitting payload by `0x0020` field[4] — offline analysis of tapes already in the vault.
3. **Does an NPC's nameplate/target window read the same prop-36 field the roster does?** Cheapest: the already-specified `agent_level` probe ([../enemy/PLAN.md](../enemy/PLAN.md):1738-1740) — prop 36 at a second agent, watch the nameplate. One caged run.
4. **What does int-main's case 36 actually write?** Cheapest: `python toolkit/clientscan/genericvalue.py --id 36` against the pinned vault exe — no client launch, minutes.
   **ANSWERED 2026-08-16, same day, SOURCED (build 38797, pinned pristine).** `genericvalue.py --id 36` derives a real int-main case body at `0x00812D6E` — not the generic default `0x008129B0` the stale agentprops line claimed. Disassembled (`codescan.py --dis 0x00812D6E`): two container calls keyed on the agent id against the manager object's field `+0x7CC` (`0x00817BE0`, then `0x0080BC90` which returns the per-agent entry), then **`mov [entry+0x2C], value`**, then `0x007DFE10(agent, value)` — a persistent per-agent store plus a notification. The dispatcher prologue confirms the register roles: the handler's args are `(property_id, agent_id, ?, value)`, the agent id is bounds-asserted against the record count, and the value survives untouched to the case. So property 36 is a real per-agent write for ANY agent id, which strengthens — but does not yet prove — that the NPC nameplate reads the same store; Q3's caged probe remains the on-screen half.
5. **The §6g residue under the delta model** (max→0 rendered full, then `range > 0`). Cheapest: re-run the kill probe's step with intermediate maxima (100→50→10) using RESKIN §18.13's HUD-number method, which reads exact values rather than bar fills.
6. **0x006E slot order for Legs/Head/Boots/Gloves** — CONTESTED, one lineage vs two ([../character/FINDINGS.md](../character/FINDINGS.md):1481). Cheapest: the per-slot `0x006F` probe — send one item to one named slot and look.
7. **Does retail enforce any ordering among the post-create messages (0x009F/0x00A6/0x0026)?** Our order is RECONSTRUCTION. Cheapest: adjacency-with-subject-match measurement over the existing four tapes, the same instrument §3 of the smsg study already built.
8. **The 0x0047/position write-up gap.** The code's current trust-the-client policy rests on a session recorded only in comments (`authsrv.py:6340-6355`), and [../movement/FINDINGS.md](../movement/FINDINGS.md):649-655 says the opposite. Cheapest: no experiment — a superseding note in the movement FINDINGS citing the session, the same fix its own §2b already models.
9. **Definition-index collisions across areas** — `area_population()` validates within one area only (`authsrv.py:4160-4187`); no global registry exists. Cheapest: a static whole-content check in `test_population.py`, no client involved.
10. **What the client renders for a declared-but-composite-less definition** (0x0056 sent, no 0x0057, file needing one) — NOT FOUND in any study; only the crash case (undeclared slot) is measured. Cheapest: one caged run sending a COMPOSITED-flagged file id with the 0x0057 withheld, screenshot the result.
11. **Corpus breadth.** All four tapes share one character, one account, two areas — every "4/4 tapes agree" figure is one character record sampled four times ([../smsg/FINDINGS.md](../smsg/FINDINGS.md), caveats). Cheapest real fix: one live capture on a different character, under the existing `RUNBOOK.md` live procedure and behavioural rules.
