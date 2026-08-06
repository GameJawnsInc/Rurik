# What adding an enemy would take — a scouting pass

Written 2026-08-06. No client was launched. Everything here is reading the
mirrors, our own schema and our own `Gw.dat`, plus four measurements against the
archive that could have failed.

The headline: **"an enemy" is four separable problems, and the field data for
three of them already exists.** A second body is days. A body the client renders
as a monster needs numbers we do not own but which two independent lineages
publish and which our own archive can partly check. A body that *fights* is R4a,
and nobody in fifteen years has built it.

Two findings are worth reading even if nothing else here is acted on.

**§6b — the damage channel, now MEASURED against our own client.** There is no
damage message; damage is agent property 16 on `0x00A3`, and the float is a
**fraction of maximum health**, not an absolute amount. Health **clamps at 1**,
so a damage packet cannot kill. And a positive value crashes the client on
ArenaNet's own `Assertion: damage.amount <= 0`. This cost four packets and no NPC.

**§4 — allegiance is a FourCC.** The `PLAYER_TEAM_TOKEN = 'play'` we already send
in every spawn is that field, and the friendly-NPC value is `'nonc'`. Hostility
is plausibly one dword in a message we already send correctly.

## Labels

Same vocabulary as [studies/character/FINDINGS.md](../character/FINDINGS.md):
**OBSERVED** (we saw it, our client, our logs) · **MEASURED** (checked against
real bytes on this machine) · **CLIENT-DATA** (read out of the shipped client) ·
**UPSTREAM** (a reimplementation says so) · **CORROBORATED** (independent
lineages agree; each use names them) · **CONTESTED** · **UNVERIFIED** ·
**NOT FOUND**.

---

## 1. Where the server is today

**OBSERVED, ours.** `toolkit/authsrv/authsrv.py` creates exactly one agent, the
player, in reply to `GAME_CMSG_INSTANCE_LOAD_REQUEST_PLAYERS`
([authsrv.py:1434-1511](../../toolkit/authsrv/authsrv.py)). Four structural facts
matter more to this arc than any protocol detail:

- **There is no agent table.** Position, plane, destination and heading live in
  the per-connection `state` dict (`authsrv.py:767`, `:823-828`);
  `PLAYER_AGENT_ID = 1` is a module constant. A second agent has nowhere to live.
- **The world tick integrates one destination** (`authsrv.py:830-899`) and
  deliberately broadcasts nothing — the client's own report is treated as the
  better opinion. **That reasoning does not transfer to an NPC.** For a
  server-owned agent there is no second opinion, so the tick becomes the only
  truth and its output must go on the wire. This is the one place where the
  movement arc's hard-won conclusion inverts, and it is worth writing down before
  someone "fixes" the new broadcast back out again.
- **The server cannot route.** The pathfinding graph is decoded only as far as
  its sub-record sizes ([studies/mapdata/FORMAT.md](../mapdata/FORMAT.md)).
  Collision works. A monster can walk straight lines and be stopped by walls; it
  cannot walk around a building.
- **Only Kamadan's geometry is wired up.** `MAP_STATIC_CONFIG`
  (`authsrv.py:259-266`) carries OpenTyria's six maps. §5 changes this
  materially.

`toolkit/schema/codec.py` already encodes every field type this arc needs
(`agent_id`, `dword`, `byte`, `vec2`, `string16`, `array32`). `nested_struct` is
unsupported and nothing below needs it.

---

## 2. The wire inventory

Shapes are from `schema/messages.json`. **None of these opcodes appears in
`schema/overrides.json`, and every one has real fields**, so each is among the
744 of 748 messages that agree field-for-field with the message-format tables
recovered from our own `Gw.exe` at build 38797
([studies/msgtable/FINDINGS.md](../msgtable/FINDINGS.md) §1) rather than one of
the 29 header-only stubs. **CLIENT-DATA** for the shapes; names are UPSTREAM
except where §3 upgrades them.

| Opcode | Name (ldufr) | Wire shape | Bytes |
|---|---|---|---|
| `0x0020` | `WORLD_CREATE_AGENT` | 23 fields — already sent for the player | 99 |
| `0x0021` | `WORLD_REMOVE_AGENT` | `dword agent_id` | 6 |
| `0x0056` | `NPC_UPDATE_PROPERTIES` | 6×`dword`, 2×`byte`, `string16(8)` | ≤46 |
| `0x0057` | `NPC_UPDATE_MODEL` | `dword`, `array32(8)` | ≤42 |
| `0x009B` | `AGENT_UPDATE_NPC_NAME` | `agent_id`, `string16(32)` | ≤72 |
| `0x00AA` | `AGENT_CREATE_NPC` | `agent_id`, `dword class`, `dword npc_id` | 14 |
| `0x009F` | `AGENT_PROPERTY_UPDATE_INT` | `dword prop_id`, `agent_id`, `dword value` | 14 |
| `0x00A0` | `..._INT_TARGET` | `prop_id`, `agent_id target`, `agent_id cause`, `value` | 18 |
| `0x00A2` | `..._UPDATE_FLOAT` | as `0x009F`, value is a float | 14 |
| `0x00A3` | `..._FLOAT_TARGET` | as `0x00A0`, value is a float — **this is damage** (§7.4) | 18 |
| `0x002F` | `AGENT_UPDATE_ALLEGIANCE` | `dword`, `dword` | 10 |
| `0x002D` | `AGENT_PLAYER_DIE` | `dword agent_id` | 6 |
| `0x0026` (CMSG) | `ATTACK_AGENT` | `agent_id`, `byte` | 7 |

Note `prop_id` comes **first** in the property messages, before the agent id —
verified against OpenTyria's struct (`GameMsg.h:203-215`) and against our own
capture, and already correct in `toolkit/authsrv/probes.py`.

Property ids come from two files by the same author (**UPSTREAM, one lineage,
stated twice**) — OpenTyria's 66-entry `GmAgentProperties.h` enum and
Headquarter's `AG_ATTR_*` defines (`code/client/agent.c:6-18`). They agree on
numbers and differ on names, and where they differ the *client* file is the more
useful one because it says what the client does with the value:

| id | OpenTyria's name | Headquarter's name |
|---|---|---|
| 16 | `DamageModifier1` | **`AG_ATTR_DAMAGE`** |
| 17 | `DamageModifier2` | **`AG_ATTR_CRITICAL_DAMAGE`** |
| 36 | `PublicLevel` | `AG_ATTR_SET_LEVEL` |
| 41 / 42 | `Energy` / `Health` | `AG_ATTR_SET_ENERGY` / `AG_ATTR_SET_HEALTH` |
| 43 / 44 | `EnergyRegen` / `HealthRegen` | `AG_ATTR_SET_ENERGY_PS` / `..._HEALTH_PS` |
| 55 | `HealthModifier2` | **`AG_ATTR_ARMOR_IGNORING`** |

Also present and unnamed by the client: `MeleeAttack = 2`, `SkillDamage = 10`,
`Knockdown1 = 35`, `FightStance = 58`, `CastSkill = 60`. Headquarter rejects any
id outside `0..65`, which corroborates the enum's 66-entry span.

**OBSERVED, and worth having:** the client accepts `0x009F` with property 36 on
its own agent and neither crashes nor disconnects — three packets at values 1, 15
and 20, session ran 250 s afterwards
(`vault/captures/authsrv/authsrv-20260805T164849-c2.jsonl`, the `level` probe).
What it *did* is unknown; the operator was watching the Hero window, which is the
other level channel. Transport proven, effect not.

**Align by shape and name, never by number.** gw-preservation numbers this
neighbourhood one lower (its `AgentUpdateNPCProperties` is `0x0055`, its
`AgentUpdateNPCModel` `0x0056`) while agreeing with us on `0x0020`. The drift is
documented in [studies/character/FINDINGS.md](../character/FINDINGS.md) §b and
our delta against build 38797 is measured at zero. Do not shift our catalog.

---

## 3. `NPC_UPDATE_PROPERTIES` decoded — CORROBORATED

Three sources, no shared authorship, agree on this message, and the third one
supplies the widths:

- **Fournux/Tyria-Extractor** (MIT, Rust, independent live sniffer) gives byte
  offsets and names (`doc/NPC_AND_VENDOR_EXTRACTION.md` §3).
- **gw-preservation/server** (Go, sole author "Energy", independent of ldufr)
  builds the same message field for field (`gameservice/StoC.go:107-118`).
- **Our schema**, whose widths are the client's own 38797 tables.

Fournux's offsets *look* wrong against our wire — a four-byte header, `u32`
where we have `byte`, fixed-length names where we have a count prefix. They
reconcile exactly under the client's own field semantics recovered in
[studies/msgtable](../msgtable/FINDINGS.md) §2.2, where type 4 is "unsigned int,
`count` wire bytes **widened to a 4-byte slot**". **MEASURED, four for four:**

| Message | Our wire bytes | Widened struct | Fournux |
|---|---|---|---|
| `0x0021` | 6 | 8 | `0x08` ✓ |
| `0x009B` | ≤72 | 72 | `0x48` ✓ |
| `0x0056` | ≤46 | 52 | `0x34` ✓ |
| `0x0020` | 99 | 116 | `0x74` ✓ |

Including the 23-field `0x0020`, where the sum could easily have missed. So
Fournux documents the deserialized struct, we document the wire, and they are the
same message. The result:

| Our field | Meaning | Corroboration |
|---|---|---|
| dword 1 | NPC model id (definition index) | Fournux + gw-pres (which calls it `agentId` and passes `definitionIndex` — a stale name) |
| dword 2 | **model file id** — the `Gw.dat` resource | both |
| dword 3 | skin file id | Fournux names it; gw-pres sends 0 |
| dword 4 | packed visual adjustment: signed hue, sat, lightness, then **unsigned scale %** | Fournux's decode; gw-pres sends `0x64000000` and calls the field `scale` — `0x64` = 100 % in the high byte, which independently confirms both the meaning and the byte order |
| dword 5 | appearance value | Fournux names it; gw-pres sends 0 |
| dword 6 | NPC flags | both; gw-pres sends `0x20C` |
| byte 1 | primary profession | both |
| byte 2 | default level | both |
| string16(8) | model-level name, as an EncString | both |

`NPC_UPDATE_MODEL` likewise: gw-preservation sends `npcId`, a `uint16` count of
1, then one `modelId` — exactly our `dword, array32(8)`, whose `array32` carries a
u16 count prefix. Two lineages, same shape.

**The name fields are not text — CORROBORATED (Fournux + GWLP-R + gw-pres).**
Both name fields carry an *EncString*: UTF-16 code units that are references into
the client's localized text resources, resolved as `file_index = text_id / 1024`,
`record_index = text_id % 1024` against a per-language file array in `Gw.dat`.
gw-preservation stores them as literal hex quads (`"2b5e 9f0f b437 7153"` for
*Ascalon Guard*); GWLP-R's mock NPC passes a five-word `hashedName` of the same
shape. We cannot label an NPC by sending its English name.

---

## 4. Allegiance is a FourCC, and it is probably the hostility switch

**MEASURED, from gw-preservation's own agent table.** Its `allegianceFlags`
values decode as ASCII:

```
1886151033 = 0x706C6179 = 'play'   Ralena Stormbringer, Vassar  (party-allied NPCs)
1852796515 = 0x6E6F6E63 = 'nonc'   merchants, collectors, Ascalon Guard  (non-combatant)
```

`'play'` is **the exact value `authsrv.py:234` already sends as
`PLAYER_TEAM_TOKEN`**, in the same slot of the same message, chosen in an earlier
pass because three lineages agreed on it against OpenTyria's `0xBAADF00D` debug
fill ([studies/character/FINDINGS.md](../character/FINDINGS.md) §d, which
identifies field 12 of `0x0020` as an allegiance FourCC). This measurement closes
that loop from a second direction: the field is real, it is a FourCC, and it
distinguishes *kinds of agent* rather than *teams*.

**The obvious inference — and it is an inference, not a finding:** a hostile
agent carries a third FourCC. `'mons'` (`0x6D6F6E73`) is the guess the pattern
invites. **NOT FOUND** in any mirror: all seven of gw-preservation's NPCs are
friendly Ascalon townsfolk, GWLP-R hardcodes `factionColor = 0x20` in a
`TODO: COMPLETE ME!` factory, and OpenTyria never sends allegiance at all.

This is the cheapest high-value experiment in the whole arc: spawn one agent,
vary one dword, watch whether the nameplate turns red and whether the client will
let you attack it. It is probe 4 in §8.

---

## 5. The map problem shrank — MEASURED

`gw-preservation/server` carries **397 map definitions with `Gw.dat` file ids**
(`gameservice/instance_definitions.go`). Checked against *our own* archive
through our own MFT file-id table (`toolkit/mapdata`), on this machine:

```
gw-preservation map file ids resolving in our build-38797 archive:  393 / 397
the four misses:  146 Lakeside County · 147 The Northlands
                  148 Pre Ascalon City · 164 Ashford Abbey
```

Three of the four misses share the single id `0x1b97d`, which is what an unfilled
placeholder looks like, not what build drift looks like — drift would have missed
all 397, not four. Their table also disagrees with OpenTyria on Lion's Arch
(`0x34fd` vs `0x56228`, and **ours resolves**), so it is neither derived from
OpenTyria nor uniformly better than it.

Two consequences:

1. **[studies/mapdata/FORMAT.md](../mapdata/FORMAT.md)'s "we cannot name a map we
   do not already have an id for" is now true of 4 maps, not 391.** Pre-Searing
   Ascalon City specifically is still unreachable.
2. **One Pre-Searing map loads today.** The Catacombs (map 145, `0x1c530`) parses
   to **51 planes and 5,246 trapezoids** — MEASURED, this session, using the
   existing `PathingMap.load`. It is Pre-Searing, it is explorable, and it is
   where the tutorial's undead live. It has no published spawn point, but a
   walkable point is derivable from our own navmesh.

**License, flagged and not decided here.** `gw-preservation/*` carries **no
license, i.e. all rights reserved** (PLAN.md §1.1: "read them, learn from them,
cite them — never copy from them"). Verifying their ids against our archive is
reading. Pasting their 397-row table, or their seven agent definitions, into our
repo is copying, and it is the owner's call, not an implementer's. The
provenance-gate question in PLAN.md §7 Q3 applies as well: these are
ArenaNet-derived numbers. A defensible middle path exists — treat their table as
a *lead* and re-derive each id we actually use by loading it and checking the
geometry matches the map we think it is — but it is a decision, so it is written
down rather than assumed.

---

## 6. The rungs, cheapest first

**E1 — a second body of a kind we already make.** *(days)*
Send the player's spawn burst again with `agent_id = 2`,
`model_id = CHAR_CLASS_PLAYER_BASE | 2`, another name, a position a few hundred
units away. No new message types, no unknowns. Answers the one question gating
everything else: **does the client render an agent it was not told to control?**
Forces the first real refactor — an agent table, and a spawn routine taking an
agent rather than reading module constants (§7.2).

**E2 — a body the client renders as an NPC.** *(days, and no longer blocked)*
`WORLD_CREATE_AGENT` with `model_id = 0x20000000 | npc_model_id`
(`CHAR_CLASS_MONSTER_BASE`, corroborated ldufr + gw-pres + Fournux), preceded by
`NPC_UPDATE_PROPERTIES` and `NPC_UPDATE_MODEL`. Real numbers exist for seven
Ascalon NPCs, and one file id — **116228** — appears in *both* gw-preservation
(2026, `hatcher_collector`) and GWLP-R's mock NPC (2013,
`NPCFactory.java:109`), thirteen years and two lineages apart. That is the
strongest evidence available that these ids are stable and usable.

gw-preservation's send order, which is the only observed one:
`NPC_UPDATE_PROPERTIES` + `NPC_UPDATE_MODEL` once per *definition*, then per
*agent* `AGENT_UPDATE_NPC_NAME` → `AGENT_INITIAL_EFFECTS` → `WORLD_CREATE_AGENT`
(`gameservice/instance.go:614-640`). Note it never sends `AGENT_CREATE_NPC`
(`0x00AA`) at all — **CONTESTED**: OpenTyria and Headquarter declare that
message, nobody on disk sends it, and what it is for is open.

**E3 — a body that moves under server control.** *(days, after E1)*
The tick already integrates a destination; for an NPC it must also broadcast
`AGENT_MOVE_TO_POINT` / `AGENT_UPDATE_POSITION` — the code path the movement arc
deliberately silenced for the player. Straight-line patrols clipped to the
navmesh are reachable now; anything that walks around a corner is behind the
pathfinding graph.

**E4 — a body that fights.** *(R4a; months, genuinely unprecedented)*
See §7.4.

---

## 6b. The damage channel, measured against our own client — OBSERVED

Probe `damage`, 2026-08-06, build 38797, one session, four packets. Everything in
this section is ours: our client, our logs, our screenshots. It supersedes the
UPSTREAM reading in §7.4 wherever the two differ.

**The mechanism is confirmed.** `AGENT_PROPERTY_UPDATE_FLOAT_TARGET` (`0x00A3`)
with property 16 damages the agent named in the **first** agent slot. We sent
target and cause as the same agent, so this run does not separate the two slots —
but it does confirm that a damage packet in this shape is accepted and acted on.

**The units are FRACTIONAL, and that settles a contested point.** Int property 42
with value 100 raised a health bar reading `100`. Then:

| Sent | Client displayed | Bar |
|---|---|---|
| `-0.25` | **25 damage** | 100 → **75** |
| `-25.0` | **2500 damage** | 75 → **1** |

The float is a fraction of maximum health, multiplied by `health_max` for display.
GWCA's "AgentLiving.hp is a percentage" reading wins; **Headquarter's clamp of a
0..1 health against an absolute `health_max` is its own defect**, and any server
that copies its arithmetic will be wrong by a factor of `health_max`.

**Health clamps at 1, not 0 — a damage packet cannot kill.** 2500 damage against
75 health left the character alive at 1 with no death animation and no state
change. Death is therefore a separate mechanism, and `AGENT_PLAYER_DIE`
(`0x002D`) is the obvious candidate. This was not a question the probe set out to
ask and it is the most useful thing it returned: an enemy that only deals damage
can never kill anyone.

**A positive value is illegal, and the client says so in ArenaNet's own words.**
The fourth step sent `+25.0` as a control on "the value is added". The client
died on the spot:

```
Assertion: damage.amount <= 0
P:\Code\Gw\AgentView\AvChar.cpp(5893)
Build: 38797     When: 8/6/2026 01:53:06
```

The crash timestamp equals the packet's send timestamp to the second, so the
causal link needs no argument. This is the same class of evidence as the
manifest-phase assert that fixed the map load: **ArenaNet's text, naming their
source file, their line, and their field.** Three things follow:

1. The channel is **damage-only**. Healing travels some other way — unknown, and
   not to be guessed at by flipping this sign again.
2. The field is named `damage.amount` in ArenaNet's source, and the client
   enforces the sign convention itself rather than trusting the server.
3. `AvChar.cpp` is a **view**-layer file, so the assert fires in presentation
   rather than in the simulation. Worth remembering when reading `0x00A3` as
   "combat": some of what it drives is animation and floating numbers.

The probe now stops at three steps. Re-running it as it stands is safe and
repeatable; putting the positive step back is not.

**The cage did its job.** The client crashed with its Sentry reporter compiled
in, and the dump stayed local (`Crash.dmp`) with no outbound connection. This is
exactly the scenario PLAN.md §6 predicted and the reason the firewall rule
exists — the first deliberately malformed packet of the project crashed the
client on the first try.

---

## 7. Blockers, ranked

### 7.1 No monster definition exists anywhere — NOT FOUND

E2 is unblocked for a *friendly Ascalon NPC* and still blocked for an *enemy*.
Every published definition is a townsperson. Fournux states outright that "no
complete static NPC-definition table has been confirmed in the archive or client
executable" — its own extractor recovers definitions by sniffing the live
service, which is exactly the capture campaign PLAN.md §1.7 predicted would be
needed for the genuinely server-side data.

Three routes: browse `Gw.dat` for a monster model with
`gwdevhub/GuildWarsMapBrowser` (mirrored, renders models); brute-force nearby
model ids around the known-good ones and look at what appears; or capture one
live session in an area with monsters, which yields `NPC_UPDATE_PROPERTIES` for
every model on screen and is required under every strategic option anyway.

### 7.2 The server has no agent model

Not research, just work, and it should land at E1 rather than E4: an agent table,
allocated ids, a tick that iterates agents, and broadcast-to-connections instead
of the current single-connection `send`. Every later rung assumes it.

### 7.3 Placement

The Catacombs is reachable (§5) and has no published spawn point; a walkable
point must come from our own navmesh. Pre-Searing Ascalon City, the finish line's
home map, still has no resolvable file id.

### 7.4 Combat is unwritten, everywhere — NOT FOUND

Checked per-file across the mirrors: no damage model, no aggro, no monster AI
anywhere. gw-preservation spawns NPCs and never makes them act.
OpenTyria declares `health`, `health_max`, `level` and a waypoint array on its
agent struct and fills none of them for a non-player. GWLP-R's `NPCFactory` is
annotated `TODO: COMPLETE ME!` and hardcodes a level-1 Mesmer.

**But the damage mechanism itself is identified — and since §6b, measured against
our own client rather than merely read.** There is no damage message.
Damage arrives as an agent property on `GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET`
(`0x00A3`), and Headquarter's handler is four lines
(`code/client/agent.c:823-867`):

```c
typedef struct { Header header; int32_t attr_id;
                 AgentId target_id; AgentId cause_id; float value; } AttrValue;
...
case AG_ATTR_DAMAGE:            // 16
case AG_ATTR_CRITICAL_DAMAGE:   // 17
case AG_ATTR_ARMOR_IGNORING:    // 55
    target->health = clampf(target->health + pack->value, 0.f, target->health_max);
```

That struct is our schema's `0x00A3` field for field (`dword, agent_id,
agent_id, dword` — 18 bytes), so the shape was CLIENT-DATA before we ever sent
one. **§6b then tested it and corrected it**: damage is negative and the target
does come first, but the value is a *fraction* of maximum health rather than the
absolute quantity this handler's arithmetic implies, and the clamp floor is 1
rather than 0. Read Headquarter here for the mechanism and not for the numbers.

---

## 8. Probe queue

Each states its prediction first, per house rule. All fit
`toolkit/authsrv/probes.py` as it stands, and none needs more than two packets.

1. **`second_agent`** — spawn agent 2 as a player-class body 500 units away.
   *Predicts:* a second character renders and stands there. *If not:* something
   in the player burst is per-connection rather than per-agent, and that is the
   finding.
2. **`npc_agent`** — the same body with `model_id = 0x20000000 | 116703` preceded
   by `NPC_UPDATE_PROPERTIES(116703, file 116228, skin 0, 0x64000000, 0, 0x20C,
   prof 3, level 1, encname)` and `NPC_UPDATE_MODEL`, using
   `hatcher_collector`'s numbers. *Predicts:* a human NPC renders at 100 % scale.
   *If the file id is stale:* nothing renders, or the client asserts on a missing
   resource — either way, cheap and unambiguous.
3. **`npc_bare`** — the `0x2` class nibble with no `NPC_UPDATE_PROPERTIES` at
   all. *Predicts:* a null/default model or an assert. Settles whether properties
   are mandatory before creation or decorative after it.
4. **`allegiance`** — one agent, spawned three times with field 12 set to
   `'nonc'`, `'play'` and `'mons'`. *Predicts:* the nameplate colour changes, and
   under exactly one of them the client will let the player target and attack.
   **This is the enemy question, and it costs one dword.**
5. **`agent_level`** — `0x009F` property 36 on the *second* agent, watching the
   nameplate rather than the Hero window. Re-runs the probe that was aimed at the
   wrong window.
6. **`npc_name`** — `AGENT_UPDATE_NPC_NAME` with a deliberately invalid
   EncString. *Predicts:* an empty or garbled nameplate rather than an assert.
   Establishes whether names block anything.
7. **`damage`** — ✅ **RUN 2026-08-06. See §6b.** Fractional, clamps at 1, and a
   positive value crashes the client on ArenaNet's own assert. Implemented at
   `toolkit/authsrv/probes.py`, still runnable, and worth re-running as the
   calibration for every combat number that follows.
8. **`death`** — *(new, and the direct successor to §6b)* damage the player to 1,
   then send `AGENT_PLAYER_DIE` (`0x002D`). *Predicts:* the death animation and
   the resurrect UI, because the damage channel demonstrably cannot produce them
   on its own. Settles how an enemy would ever finish a kill.
9. **`heal`** — the same shape with property 34/55/56 rather than 16, negative
   sign held. *Predicts:* one of them moves the bar upward. **Do not test this by
   sending a positive value on 16** — that is the crash, and it is now a known
   one.

---

## 9. What not to do

- **Do not invent a model file id.** A plausible number that renders *something*
  is the worst available outcome: it looks like success and is unfalsifiable
  afterwards.
- **Do not carry the player's "say nothing, believe the client" rule over to
  NPCs.** It is correct for an agent the client simulates and exactly wrong for
  one it does not. The movement study's conclusion is scoped to the player.
- **Do not paste gw-preservation's tables into the repo** without an explicit
  decision from the owner. No license means all rights reserved, and the ids are
  ArenaNet-derived on top of that.
- **Do not start on combat before E1.** Every combat message is addressed to an
  agent id, and we have one agent and nowhere to put a second.
