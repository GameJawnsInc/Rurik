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

> **CORRECTED 2026-08-06, and the correction is the interesting part.** This
> section originally read the four misses as unfilled placeholders in
> gw-preservation's table, on the grounds that three of them share the id
> `0x1b97d` and that build drift would have missed all 397 rather than four. The
> drift half was right; the placeholder conclusion was **wrong, and it was our
> bug rather than their data.** A parallel session found that
> `file_id_table()` did an exact-match lookup while **25 of the archive's
> 171,023 file ids are stored with bit 31 set** — see
> [studies/mapdata/FORMAT.md](../mapdata/FORMAT.md). Masked, two of those land on
> map rows and are exactly the Pre-Searing ids. Re-checked here after the fix:
> `0x1B97D` resolves to row 7982 and `0x1C539` to row 20118. **All 397 resolve.**
>
> The lesson worth keeping: "their data is a placeholder" and "our lookup is
> wrong" predict the same observation, and this section picked the one that
> blamed the other project. The tell was available — three maps sharing an id is
> odd, but so is exactly the four Pre-Searing rows failing together.

Their table also disagrees with OpenTyria on Lion's Arch (`0x34fd` vs
`0x56228`, and **both resolve**), so it is neither derived from OpenTyria nor
uniformly better than it.

**Pre-Searing is reachable.** [studies/mapdata/FORMAT.md](../mapdata/FORMAT.md)'s
"Ascalon City Pre-Searing is still unreachable" is retired. The Catacombs (map
145, `0x1c530`) also parses to **51 planes and 5,246 trapezoids** — MEASURED
here before the fix, and it is where the tutorial's undead live.

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

## 6c. E1 is done, and allegiance is not the hostility switch — OBSERVED

Probe `allegiance`, 2026-08-06, build 38797. Six packets: three
`PLAYER_CREATE` + `WORLD_CREATE_AGENT` pairs, identical except for the position
and the field-12 FourCC, named for their own tokens.

**E1 fell out for free, and it is the more important result.** All three bodies
appeared, correctly placed, correctly named. **The client renders agents it was
not told to control, from six packets, with no agent table and no server
refactor at all.** §6's estimate of "days" for E1 was wrong by about two orders
of magnitude — it is one function, and the probe already contains it.

**The allegiance question came back negative, and the design was confounded.**
All three read as *other players*: light-blue nameplates, light-blue compass
dots, and a **Trade** button on the target window. `'play'`, `'nonc'` and
`'mons'` were indistinguishable.

That is a real result about field 12 but a much weaker one than intended,
because **player-class agents are players by construction**. Every body carried
`model_id = 0x30000000 | n` and a preceding `PLAYER_CREATE`, so the client had
two independent reasons to classify them as players before it ever read field
12. The probe held the wrong thing constant: it varied the token while pinning
the agent class that plausibly outranks it. Choosing player-class was deliberate
— it avoided needing a model file id we do not have — and it is exactly what
made the answer uninterpretable.

A second confound, spotted from play rather than from the packets: **an outpost
does not permit attacking at all**, so "could not attack any of them" carries no
information about hostility. (Kamadan's rift-quest area is reportedly an
exception worth knowing about, but the spawn point is not in it.)

So: **field 12 does not make a player-class agent hostile.** Whether it does
anything for a monster-class agent is untouched. The re-run needs
`model_id = 0x20000000 | n`, no `PLAYER_CREATE`, agent-kind byte 9 rather than
5 — and an explorable map, which makes §7.3 a blocker for this question too.

Three incidental observations, all free:

- The target window reads **`W0`** — profession letter and level — so it takes
  the profession from somewhere without being sent `0x00B7`, and shows level 0
  because we never sent property 36 for these agents.
- Created agents get a **full red health bar** in the target window with no
  health property sent at all.
- The player's own bar reads **1** before anything sets health. Combined with
  §6b's clamp floor of 1, the reading that fits both is that 1 is a display
  floor for a living agent rather than a true health value.

---

## 6d. E2 is done — a real NPC, correctly modelled and correctly named — OBSERVED

Probe `npc_agent`, 2026-08-06, build 38797. Four packets: an NPC definition, its
model, a monster-class agent using it, and a control using a definition index
that was never sent.

**It worked on the first attempt.** `Hatcher [Collector]` stood in the map,
wearing a collector's body, with a **gold nameplate** — plainly different from
the light-blue Trade-able player bodies §6c produced. Everything below follows
from that one screenshot.

**File id 116228 is valid on build 38797.** That number comes from GWLP-R's mock
NPC in **2013** and is still in gw-preservation's agent table in **2026**; it is
now OBSERVED working against our own client. Three lineages, thirteen years, one
id. Two consequences: gw-preservation's NPC table is a *good* lead rather than a
plausible one, and `Gw.dat` model ids are far more stable across builds than the
opcode drift in this project would lead you to expect.

**The EncString mechanism is confirmed, and it is better news than §4 assumed.**
We sent four opaque 16-bit words — `328A E3B9 AA36 2E69` — and the client
displayed **"Hatcher [Collector]"** in English. It resolved them against its own
localized text resources exactly as Fournux describes. So a name cannot be
invented, as §4 said; but a *captured* EncString is portable, self-describing and
needs no text extraction on our side to be useful.

**NPC definitions are MANDATORY, and the definition index is a raw array index.**
The control created a monster-class agent whose definition had never been sent.
The client died on:

```
Assertion: index < m_count
P:\Code\Base\rtl\Array.h(587)
Build: 38797     When: 8/6/2026 09:43:32
```

`0x63` — our 99 — appears repeatedly in the trace arguments, and the crash
timestamp equals the packet's send timestamp exactly. This is a **bounds check on
a dense array**, not a missing-resource path: the client indexes its NPC
definition table directly with whatever the agent's model id carries. A server
that creates an agent before defining its type does not get a missing model, it
gets a crash.

That is why gw-preservation sends `NPC_UPDATE_PROPERTIES` + `NPC_UPDATE_MODEL`
**once per definition, before any agent that uses it**
(`gameservice/instance.go:614-640`). We copied the ordering because it was the
only observed one; now we know what enforces it.

**Open, and cheap to close:** whether definition indices must be dense. We defined
only index 2 — never 0 or 1 — and it worked, so the array presumably grew to hold
three entries and 99 was simply past the end. Whether the client tolerates sparse
definitions, or silently allocates up to the highest index seen, is untested.

**Where this leaves the arc.** E1 and E2 are done, four rungs collapsed to two.
What remains between here and an enemy is not rendering — it is **hostility**
(§6c, still open and now needing an explorable) and **a hostile creature's
definition** (§7.1, still NOT FOUND — every id we have is an Ascalon townsperson).

---

## 6e. Hostility is one dword, and it is not a magic word — OBSERVED

Probe `npc_allegiance`, 2026-08-06. One Hatcher definition, four monster-class
bodies, identical in every field but the team token. Result, in order:

| Token | Nameplate |
|---|---|
| `'play'` — the player's own | **green** |
| `'nonc'` — a client constant | **green** |
| `'nonn'` — the other client constant | **green** |
| `'mons'` — a value the client has never seen | **RED** |

**Field 12 of `WORLD_CREATE_AGENT` is what makes an agent an enemy.** That is the
question §6c set out to answer and got confounded on; here it is, clean.

**The mechanism is identity, not vocabulary — and that was read out of the binary
before the probe ran, which is why the probe was worth running.** Static analysis
of our own `Gw.exe` (build 38797, never executed):

- **`'play'` appears nowhere in the image as a dword constant.** Not once in
  10 MB. The client cannot be comparing the field against it — yet three
  lineages send it and it demonstrably works.
- The only allegiance-shaped constants anywhere are `'nonc'` and `'nonn'`, and
  they occur in exactly one four-instruction function at `0x1AB130`:
  `f(x) = (x == 'nonc' || x == 'nonn')`.

So the field is an opaque team **identity** with exactly two special cases. The
player's own agent carries `'play'`, equality makes anything else carrying it an
ally, and the two constants mark non-combatants. Anything else is a team that is
not yours — which the client renders red.

**`'mons'` was right for the wrong reason.** It is not a magic value; it is
hostile *because it is unrecognised*. Any arbitrary dword should do the same, and
that is a one-packet check whenever someone wants it.

**Not attackable — but that is the outpost, not the allegiance.** Guild Wars
forbids attacking in a town, so this run could not test targetability whatever
the answer was. §7.3 explains why that is now the load-bearing blocker rather
than a cosmetic one — and §7.3a gives a way to test it without solving the map
problem at all.

**What this means for the arc.** Combined with §6b (damage lands and is
fractional) and §6d (NPCs render from a known-good definition), **every wire
mechanism a first enemy needs is now proven.** We can put a red, hostile,
correctly-modelled body in a map today. §7.1's "no hostile definition exists"
stops being a blocker for a *first* enemy the moment you accept that a hostile
Hatcher is an enemy: the model and the allegiance are independent fields, and
only the allegiance decides whether the client treats it as a foe.

---

## 6f. A fight renders, the field order is confirmed, and death is not `0x002D`

Probe `enemy_damage`, 2026-08-06. A hostile Hatcher, health 100, then damage
aimed at *it* with the player as the cause.

| Sent | Client displayed |
|---|---|
| `-0.25`, target = enemy | **25 damage** on the enemy |
| `-0.5`, target = enemy | **50 damage** on the enemy |
| `AGENT_PLAYER_DIE` on the enemy | **nothing** |

**The first agent slot of `0x00A3` is the target — OBSERVED.** §6b could not test
this: it sent target and cause as the same agent, so the two slots were
indistinguishable and the order rested on ldufr's struct alone. Here they
differed and the damage landed on the enemy. Every damage packet this project
writes from now on is aimed correctly, and that was a coin-flip until this run.

**Fractional health is confirmed on a second agent**, with a maximum we chose:
`-0.25` and `-0.5` of 100 came out as 25 and 50. §6b was not a quirk of the
player's own bar.

**So the client renders a fight.** Floating damage numbers over a hostile body,
its health bar draining, damage accumulating across packets. That is the visible
result the arc was aiming at, and it needs no AI, no interaction handling and no
explorable map.

**`AGENT_PLAYER_DIE` (`0x002D`) does nothing to an NPC.** Combined with §6b's
finding that damage floors at 1 and cannot kill, **we do not currently hold a
mechanism that kills anything.** The name is ldufr's and says *player*; the four
remaining candidates are in the `kill` probe, ordered so the risky ones cannot
cost the safe ones. If none works, the next move is reading the client's
agent-view code rather than guessing further — `AvChar.cpp` is already named by
the assert in §6b.

---

## 6g. Three of four death candidates are dead, and we can now name ArenaNet's files

Probe `kill`, 2026-08-06. Four candidates, one packet each, on one hostile
Hatcher. The crash timestamp (`10:56:33`) lands exactly on step 8's send
timestamp, which identifies the culprit without argument.

| Candidate | Result |
|---|---|
| float property 42 = `0.0` (health fraction → zero) | **nothing** |
| `AGENT_ALLY_DESTROY` (`0x003E`) | **nothing** |
| int property 42 = `0` (maximum health → zero) | health bar **refilled to full**, then `Assertion: range > 0`, `P:\Code\Gw\Char\CharPool.cpp(98)` |
| `AGENT_PLAYER_DIE` on the *player* | **never ran** — sent 7 s after the crash, into a client that was no longer reading |

**Int property 42 sets the maximum AND refills to full — OBSERVED.** This is the
first direct confirmation of Headquarter's `agent->health = 1.f;
agent->health_max = value;` against the real client, and it has a practical
consequence: **property 42 cannot be used to set current health.** It is
max-health-and-heal. Anything that wants an agent at partial health must set the
max and then damage it down, which is what our probes have been doing by luck
rather than by design.

**`CharPool.cpp` corroborates §6b in ArenaNet's own vocabulary.** The crash
dump's string region carries that file's assert expressions, and beside
`range > 0` sits **`fraction <= 1.0f`**. *Fraction* is their word for it. §6b
measured that health is a fraction; the client's own assert text says so.

### The capability that matters more than the result

`toolkit/clientscan/msghandler.py` finds a message's handler by table lookup, and
**every assert call site inside a handler carries a pointer to ArenaNet's own
source path.** Reading those strings turns "which reconstruction do we believe"
into "which file did they write it in":

```
GAME_SMSG 0x002D handler @ 0x005FDB70
  asserts in  P:\Code\Engine\Agent\AgMsg.cpp   expressions 'syncPtr', 'asyncPtr'
  (the bounds check that killed us in 6d is the same P:\Code\Base\rtl\Array.h,
   'index < m_count' — one shared assert, two different crashes)
```

The handler is **not a no-op**: it bounds-checks the agent id, resolves a `syncPtr`
and conditionally an `asyncPtr` out of two per-agent arrays, calls the same
routine on each, and finishes with a call against a structure at `+0x94`. So
`0x002D` does real work and our NPC simply did not visibly respond to it — which
is a different problem from the message being wrong, and it is why the untested
fourth candidate is worth one more packet before anything larger.

**This method generalises to all 482 receive handlers**, and it is the strongest
naming source this project has found. It belongs to `studies/msgtable`, not to
this arc, but it was discovered here.

---

## 6h. Why `0x002D` did nothing, read out of the client — and it is probably not death

`AGENT_PLAYER_DIE` aimed at the player did nothing either. That is four dead
candidates, so the guessing stopped and the handler got read properly.

The handler resolves the agent's `syncPtr` and calls `0x006025F0` on it. That
function is twenty instructions and **its entire body is behind one test**:

```
0x006025F0   mov  esi, ecx                    ; the agent
             test dword ptr [esi+0x20], 0x20000
             je   return                      ; <-- flag clear: DO NOTHING AT ALL
             ...
             call 0x5FF880
             fldz
             fst  dword ptr [esi+0xC8]        ; zero a float pair
             fstp dword ptr [esi+0xCC]
             mov  dword ptr [esi+0x4C], 0
return:      ret
```

**Bit `0x20000` of the agent's flags word decides whether the message does
anything.** Every agent we have ever aimed `0x002D` at — a freshly spawned NPC,
a standing player — was stationary and almost certainly had that bit clear. So
all three null results are explained by *state*, exactly as the probe's own
prediction said they would have to be: the message is not inert, we were sending
it to agents that could not respond to it.

**And the body is not death.** It zeroes a float pair at `+0xC8`/`+0xCC` and
clears `+0x4C` after a call carrying a literal `6`. A zeroed two-float vector on
an agent is a velocity or a facing, not a corpse. `0x002D`'s handler and
`0x0028`'s (`AGENT_STOP_MOVING`) share the identical opening — same context
fetch, same bounds check, same `Array.h` assert — which puts them in the same
family.

**Best current reading: `0x002D` cancels something on a moving agent, and
ldufr's name for it is wrong.** That is a hypothesis with an obvious experiment:
send it while the character is running. If the character stops dead, the message
is a movement cancel and death is somewhere else entirely.

**Consequence for the arc.** Death is not any of the five things we have tried.
An enemy can be spawned, made hostile, and damaged to 1, but nothing in our hands
can finish it. That is now the single blocking unknown for combat, and the way to
it is the method from §6g — read the handlers — rather than more packets.

---

## 6i. `0x002D` is not death, and the tool that found that had a defect

Probe `moving_die`, 2026-08-06, with the player running throughout. No death, no
animation, no prompt — **and the character's movement appeared to stop when it
landed.** Reported tentatively by the operator ("I think it did"), so this is
*consistent with* the §6h reading rather than a clean confirmation; `0x002D` and
`0x0028` were not distinguished from each other.

Taken with §6h's disassembly — a body gated on a moving-agent flag that zeroes a
float pair and clears a state word — the fair summary is: **`0x002D` does
something to a moving agent, that something looks like cancelling motion, and
ldufr's name `AGENT_PLAYER_DIE` is not supported by the code.** Five candidates
have now failed to kill anything.

### The map: every receive opcode to the file ArenaNet implemented it in

Every assert compiles to `mov edx, <expr>; mov ecx, <file>; call <assert>`, so a
handler names its own source file. `msghandler.py --map` now does this for all
477 receive handlers:

| Handlers | File |
|---|---|
| 30 | `P:\Code\Gw\Item\Cli\ItCliApi.cpp` — `0x0135`–`0x0162` |
| 18 | `P:\Code\Base\rtl\Array.h` — the shared bounds assert |
| 17 | `P:\Code\Engine\Agent\AgMsg.cpp` — **`0x001E`–`0x002F`, the whole agent cluster** |
| 7 | `P:\Code\Gw\Guild\Cli\GuCliApi.cpp` |
| 3 | `P:\Code\Gw\Mission\Cli\MsCliApi.cpp` — `0x0191`, `0x01A2`, `0x01A3` |
| 2 | `P:\Code\Gw\Char\CharMsg.cpp` — `0x0057`, `0x0091` |
| 1 | `P:\Code\Engine\Agent\agint.h` — `0x0020` |

Only 7 files across 477 handlers, because a handler with no assert names nothing.
That is silence, not absence.

### A defect that had already produced a wrong reading, in this session

`read_table()` masked the opcode with `0xFF`. **MEASURED: 229 of the 477 receive
opcodes are above `0xFF`**, so nearly half of them collapsed onto a byte and a
lookup returned whichever entry the walk reached first — with nothing in the
output to say so.

It had already bitten. The first version of the table above read
`MsCliApi.cpp` as handling `0x91, 0xA2, 0xA3`, and **`0x00A3` is the damage
message**, so "damage is implemented in the mission client" was one sentence away
from being written down as a finding. The real opcodes are `0x0191, 0x01A2,
0x01A3` and none of them is damage. `0x00A3` has no assert and names no file.

Fixed, with the mask removed at both the table walk and the CLI, and verified
both directions: `0x002D` still resolves to the same handler, and `0x0199` now
resolves to itself instead of to `0x0099`.

---

## 6j. The property dispatch, read — and death is not in it

Full write-up: **[studies/agentprops/FINDINGS.md](../agentprops/FINDINGS.md)**.

The float-property path (`0x00A3` → `0x00813040` → `0x00818210`) is a jump table
over properties 16–62, and **it acts on exactly 8 of the 47**: 16 (damage), 33,
34, 43, 44, 52, 55, 62 — health and energy, and nothing else. The other 39 fall
to the default case.

Three results matter for this arc:

- **The fraction is confirmed from the code.** The damage case is
  `fld [esi+0x24]` (the agent's maximum health) `fmul` the value we sent. §6b
  measured that from the outside; this is the instruction that does it.
- **Headquarter is wrong about critical damage.** It applies properties 16, 17
  and 55 identically in one fall-through switch. The real client dispatches 16
  and 55 to their own targets and sends **17 to the default**, where it does
  nothing.
- **Death is not an agent property**, on either the float or the int path. That
  closes the last place §6i left to look on this channel.

Where death goes next is recorded in that document §4, and the best lead is
`0x005FC380` — the only other thing the damage path does, called immediately
after the record update and not yet read.

---

## 6k. Death, found — and the arc's blocking unknown is closed

`AGENT_UPDATE_EFFECTS` (`0x00F1`), **bit 4 (`0x10`) of the effects dword**. Set
it and the agent dies; clear it and the agent gets back up. OBSERVED both
directions, 2026-08-06. Full write-up in
[studies/agentprops/FINDINGS.md](../agentprops/FINDINGS.md) §1c.

**Death was never a message.** Seven candidates were tried across §6f–§6i —
`AGENT_PLAYER_DIE` at an NPC and at the player, `AGENT_ALLY_DESTROY`, float
health zero, int health zero, damage past its floor, an absolute health modifier
past zero — and every one was a guess at *which message kills*. The answer is a
bit in a bitfield, and it was found by reading the client's own use of the
`+0x30` word rather than by sending an eighth guess.

Two practical consequences for anything built on this:

- **Reviving is two operations.** The death path zeroes the health and energy
  pools, so clearing the bit alone returns a body at ~0–1 health that dies to
  any scratch. Clear the bit, then set health.
- **Death drops the client's target**, nameplate and all.

**Every mechanism a first enemy needs is now proven against our own client:**

| Capability | Where |
|---|---|
| spawn a second agent | §6c |
| render it as a correctly-modelled, correctly-named NPC | §6d |
| make it hostile | §6e |
| give it health | §6g, §1c of the props study |
| damage it, in the right units, at the right target | §6b, §6f |
| heal or set health silently | agentprops §1b, property 34 |
| **kill it, and revive it** | **§6k** |

What remains is not protocol. It is a server that does these things on its own —
§7.2's agent table, a hostile NPC at instance load, and something that decides
when to send them.

---

## 6l. The enemy is in the world — OBSERVED

2026-08-06. A hostile Hatcher stands in the map on an ordinary login, with a
100-point health bar, no `--probe` flag and no timed sequence. `spawn_enemy()`
in `toolkit/authsrv/authsrv.py`, with the shared definitions in
`toolkit/authsrv/agents.py`.

**Nothing on the wire is new.** It is §6k's opening burst moved onto the login
path: NPC definition, model, monster-class `WORLD_CREATE_AGENT` carrying an
unrecognised allegiance token, and maximum health. Each was established
separately and is cited at its call site.

**E1, E2 and the E4 gate are all closed.** What was scouted in §6 as four rungs
is now: a body exists, it is an NPC, it is hostile, it has health, it can be
damaged and killed and revived — and the server does the first four by itself.

**What it does not do is anything.** It stands. It has no behaviour, no reaction
to being clicked, and no reason to exist beyond proving it can. The next rung is
the first one that requires the server to *decide* something rather than
transcribe a proven packet:

- **Answer `INTERACT_PLAYER`.** §7.3a measured the client sending `0x0033` at
  the hostile agent 11 and 32 times in two sessions while we ignored every one.
  That is the player's attack intent, already arriving, already recorded.
- **Track health server-side.** `spawn_enemy` seeds `state["agents"]` with
  health, max health and a `dead` flag, and nothing reads it yet.
- **Close the loop.** Damage on a timer or on interaction, death at zero via the
  effects bit, and a revive. Every packet for that is proven; what is missing is
  the decision about when to send them, which is the first genuine game logic
  this project would own.

---

## 6m. A repeatable fight — OBSERVED, and the arc's deliverable

2026-08-06. Clicking the hostile Hatcher damages it, seven or so clicks kill it,
and eight seconds later it stands back up at full health. **The cycle repeats.**

**It works in an outpost**, which was the open worry, and it works because
combat is driven from `INTERACT_PLAYER` rather than `ATTACK_AGENT`. A town
forbids attacking, so the client never sends `0x0026` there — but it does keep
reporting the click, which §7.3a had already measured arriving 11 and 32 times
while this server ignored every one. What to do about a click is the server's
decision. That single choice retired the map blocker for this rung.

**Where the line falls between what is known and what is ours:**

| Proven against our client | Invented by us |
|---|---|
| the damage message, its fraction units, its target-before-cause field order | how hard a click hits (15% of maximum) |
| the death bit, and that it reverses | how often a click may hit (1 s) |
| that reviving takes two operations | how long a body stays down (8 s) |
| that the client reports clicks in a town | that a click means an attack at all |

The right column is not a claim about retail Guild Wars and must never be cited
as one. Real numbers are obtainable — the wiki documents attack rates and weapon
damage, and a captured fight would give the true thing — and nothing about the
structure changes when they replace these.

### What this arc did not build

Honest list, because "a fight works" invites over-reading:

- **The enemy does not fight back.** It has no attacks, no aggro, no target. It
  is a punching bag that dies convincingly.
- **It does not move.** §6's E3 is untouched; the tick integrates the player
  only, and the navmesh clipping that exists is the player's.
- **There is one of it, in one map, at one spot**, hardcoded 300 units east of
  a spawn point that is itself a fallback.
- **Nothing persists.** Health, death and the revive timer live in the
  connection's `state` dict and vanish with the socket.
- **Aggro, drops, experience, respawn placement and skills do not exist**, and
  none of them was scouted.

---

## 6n. The enemy stands in Pre-Searing, on Pre-Searing's own ground — OBSERVED

2026-08-06. Map 148 is a real entry instead of a substitute, so the character
now stands in Ascalon City Pre-Searing rather than in Kamadan's geometry under
Ascalon's name. The Hatcher is there and takes damage, **and the collision
follows what is drawn** — the first time in this project that the navmesh the
server clips against has described the same place the client is rendering.

**It took a correction to another session's inference to get there, and the
client made it.** Sending the *masked* id `0x1B97D` — the form
gw-preservation's table carries and the form `archive.py` was built to resolve —
reached the client and was refused outright:

```
Map file '0x01b97d' failed to load.  Attempting to re-bloat.
Map '0x01b97d' failed to load / Creating default map
Assertion: found    P:\Code\Engine\Map\Map.cpp(1762)
```

The archive stores it as `0x8001B97D`, and sending that loads. So **masking is
right for finding the row and wrong on the wire**, and the two had been
conflated. `archive.py`'s docstring had flagged "the client masks it" as an
inference rather than a measurement, which is exactly why it was safe to test:
the claim was labelled, so falsifying it cost one launch. Corrected at the
source in [studies/mapdata/FORMAT.md](../mapdata/FORMAT.md) and in
`archive.py` rather than only here.

**A mistake of mine worth keeping.** Before that launch I checked that the
pathing chunk parsed, that the spawn point was walkable, and that the enemy's
spot was walkable — three real checks, all of them on *our* side of the wire.
None of them could have caught this, because the question was never whether we
could read the file. "Our parser accepts it" and "the client accepts it" are
different claims, and only the second one mattered.

---

## 6o. Arming the player, and the wall the client will not go past

Session of 2026-08-06, continuing §6m. The deliverable was "make basic attacking
work". It does not work, and this section says exactly how far it got and what
is now known that was not known before. Six hypotheses were tested against the
live client and all six failed; the failures are listed because each one costs a
client relaunch and nobody should pay for them twice.

### The client will not initiate an attack — NOT FOUND

**`GAME_CMSG_ATTACK_AGENT` (0x0026) has never been sent by this client, to us,
in any session.** Not on left click, not on space, armed or unarmed, in an
outpost or an explorable, with the target rendering red and taking damage.
OBSERVED across every capture in `vault/captures/authsrv`. A click on our enemy
produces `INTERACT_PLAYER` (0x0033) and nothing else — which is what the client
sends for an NPC you talk to.

The opcode is real and registered on this build: send descriptor @VA
`0x00bc8d78`, `cmds[] @0x00c00734`, two fields. **SOURCED.** So the capability is
compiled in and something about the world we present stops the client choosing
it.

Eliminated, each by a live test:

| Hypothesis | Result |
|---|---|
| No weapon item exists | Created one. No change. |
| Weapon not on the body | `0x006E` sent, hammer renders in hand. No change. |
| Weapon not in the hand slots | `0x006D` sent with the item id. No change. |
| Player has no energy | Property 41 = 25. Globe shows it. No change. |
| Player has no health pool | Property 42 = 100. No change. |
| Map is a town | Lakeside County, `is_explorable` = 1. No change. |
| Target not flagged attackable | `0x002F` sent. No change — and see below, it is not that field. |

**Four independent attempts to locate the send site in the binary all failed**,
and the reason is worth recording so the fifth person does not repeat them:
descriptor xrefs (none), `cmds[]` xrefs (none), opcode-pushed-then-called
clustering, and immediate stores of the opcode as word and as dword. All four
also come up empty for **0x0046**, which the client demonstrably *does* send —
so they are not evidence about attacking, they are evidence that the client
reaches its send table by a route none of those methods sees. Do not re-run them.

### `0x002F` is not the allegiance byte — SOURCED, and a correction

GWCA documents `AgentLiving::allegiance` at `+h01B1` with values named
outright — `1` ally/non-attackable, `3` enemy, `6` npc/minipet
(`GameEntities/Agent.h:222`). ldufr names opcode `0x002F`
`AGENT_UPDATE_ALLEGIANCE`, and it looks like the way to set it. **It is not.**
Its handler at `0x005fdd70` passes field 2 to a setter at `0x00602e20`, which
writes `[esi+0xE8]` — nowhere near `+0x1B1`. Sending it changed nothing
observable.

Further: **nothing in this image writes `+0x1B1` or `+0x1B2`** in any addressing
form a displacement scan finds, including FPU stores. Either GWCA's offsets are
for a different build than 38797, or the write is computed. Settle that before
trusting any `+h01xx` offset from GWCA against this build.

### Items: rendering a weapon is not equipping one — OBSERVED

Three different messages, and they are not interchangeable:

| Message | What it does |
|---|---|
| `0x0161 CREATE_NAMED_ITEM` | declares the item's bytes; places nothing |
| `0x0147 ITEM_WEAPON_SET` | fills the weapon-swap UI slots |
| `0x006E UPDATE_AGENT_VISUAL_EQUIPMENT` | puts it on the BODY — this is what draws it |
| `0x006D NPC_UPDATE_WEAPONS` | agent + leadhand + offhand, as **item ids** |

**An open question from `studies/character/FINDINGS.md` is now closed: `0x006E`
renders with no bag behind it.** We sent `0x0161` + `0x006E` with no
`INVENTORY_CREATE_BAG` and no `ITEM_MOVED_TO_LOCATION`, and the hammer appeared
in the character's hands. OBSERVED.

**`0x006D` carries item ids, not weapon types.** Sending weapon type 3 there —
on the theory that it sets `weapon_type` at `+h01B2` — took the client down on
`Assertion: ptr`, `P:\Code\Gw\Item\Cli\ItCliApi.cpp(400)`, with `baseItem` in
the adjacent strings. It looked 3 up in the item table, got null and died.
OBSERVED. The client presumably derives `weapon_type` from the item's own
`ItemType`, the way it derives the mesh from `file_id`.

The starter hammer itself is `GmDefaultArmors.c:80-93`, the sixth entry of the
Prophecies warrior array — five armour pieces and one `ItemType_Hammer`.
UPSTREAM; no capture of ours carries those bytes. It is accepted by the client
without complaint, which is not the same as being correct.

### The player's own pools were never sent — OBSERVED, and fixed

The enemy got a health pool the day it was spawned and **the player never got
one, in any session**. Property **41 = energy**, **42 = health**, both on the int
channel `0x009F`. CORROBORATED before sending — gw-preservation's working server
sends exactly these two with naming comments (`gameservice/player.go:268-269`),
and our own read of the int-record dispatch found cases for `{32, 41, 42}` and
nothing else (`studies/agentprops/FINDINGS.md` §3b), with 42 already measured as
maximum health. **41 is now OBSERVED**: the energy globe reads 25.

This did *not* make skills castable, so an empty energy pool was not the only
thing stopping them. Skill completion moved to a separate branch.

### Generic values, and the animation precondition — the best result here

GWCA's `GenericValueID` namespace (`Packets/StoC.h:36-70`) is a richer and
better-commented table than Py4GW's and it corrects one of our sends:

- **`1` is `melee_attack_finished`** — the END of a swing. We sent it expecting
  an animation and got none, which is correct behaviour for an id meaning "that
  one is over".
- **`4` is `attack_started`** — "caster_id is victim, target_id is attacker".
- It independently corroborates three ids we had already MEASURED ourselves —
  16 damage, 34 health, 55 armour-ignoring — and 4 lands in the same client
  dispatch case as 50 and 60 that our own read of the int table found
  (`{4, 50, 60}`).

**`0x00A0` is `GenericValueTarget` — CONFIRMED by crash.** It was INFERRED from
its field shape matching `0x00A3`. Sending `attack_started` on it reached the
melee attack animation code, which is proof the opcode and the id are both
right.

**The precondition that blocks the animation, read out of the client at
`0x007F82C0` — SOURCED:**

```
fld   dword ptr [esi + 0xec]     ; weapon_attack_speed
fldz / fucom / fnstsw / test ah, 0x44
jp    0x7f82fc                   ; assert ONLY if it is zero
push  0x12b7                     ; line 4791 -> "m_attackInterval"
call  0x487bc0
0x7f82fc: fld dword ptr [esi + 0xf0]   ; attack_speed_modifier, line 4792
```

`esi` is the agent: `[esi+0x158]` is read a few instructions later and that is
`type_map` in GWCA's map. So **both `+0xEC` and `+0xF0` must be non-zero before
the client will animate a melee attack**, and ours are zero. That is the crash
`Assertion: m_attackInterval / P:\Code\Gw\AgentView\AvChar.cpp(4791)`.

**What sets them is NOT FOUND.** No `mov` and no `fstp` writes either offset by
displacement anywhere in the image. GWCA calls `+0xEC` "the base attack speed of
the last attack's weapon", which suggests the client computes it from the
equipped weapon rather than being told — so the last thing tried was putting the
hammer in a real equipped-items bag. **That change is UNTESTED.**

### What does work — OBSERVED

A click now *orders* an attack rather than being one, and the server swings on a
timer (`begin_attack`, `attack_tick`). Confirmed by the owner:

- the player visibly changes from **outside-combat idle to inside-combat idle** —
  the client genuinely enters a combat state, we are not drawing that
- swings land at an interval after a single click, without further input
- the enemy dies and revives on the existing cycle

Read that carefully: **a fight that looks right on screen is not evidence that
attacking is solved.** The client still is not initiating, and this is a
workaround standing in for a mechanism we have not found.

Two gaps the owner named and this session did not close: **the player does not
path into range** (the server never moves the player, so a click outside
`ATTACK_RANGE` does nothing until you walk in), and **there is no swing
animation** (the precondition above).

`ATTACK_INTERVAL = 1.33` and `ATTACK_RANGE = 1500` are **OURS**, invented to make
a fight legible. GWCA calls 1.33 the base for axe/sword/daggers and a hammer is
slower. Nothing here is a claim about retail.

### A revive bug, and its fix — UNTESTED

A revived enemy stood up with an empty health bar while our own bookkeeping said
full, so it still took seven swings to drop and the bar never moved. The cause:
re-asserting the **same** maximum with property 42 refills nothing. The fix uses
property 34, which we MEASURED as a delta (`-50.0` took off exactly 50 health,
§1b of the agentprops study) and which GWCA independently just calls `health`.

Note the reasoning trap this nearly created: "seven hits to kill" looks like
evidence the client's health was restored. It is not — the client cannot die
from property 16 at all (it floors at 1), so the seven is purely our server's
counter resetting and says nothing about the client's pools.

### Codec: nested_struct is implemented, and one schema entry is wrong

`toolkit/schema/codec.py` refused field type 12 outright, which was correct while
the element layout was unknown and stopped being correct once
`studies/msgtable/FINDINGS.md` recovered the client's tables: type 12 is a
**one-byte** repeat count and the parser "rewinds to cmd+4 per repetition", so
the element layout is the schema tail. Implemented both directions; 11 messages
that were undecodable now decode. The old test asserted nested messages were
"refused" and was passing against 64 zero bytes — which is opcode 0, not a
nested message at all — so it is replaced by a round-trip that pins the count
byte to a computed offset.

**~~`0x00E3 SKILL_ACTIVATED` disagrees with our schema and works by
coincidence.~~ RETRACTED 2026-08-06 — it agrees, and the disagreement was a
misreading of our own tool's output.** The claim was that the binary is
`dword, agent_id, word` against our `agent_id, word, dword`, that the two
coincide only while `copy` is 0, and that it "breaks the first time `copy` is
nonzero, silently". None of that is true. The client's descriptor is
`cmds ['0xe3', '0x10', '0x204', '0x404']`, which decodes to
**`agent_id(4), word(2), dword(4)`** — field for field what we carry. The last
two cmds were read in the wrong order.

MEASURED, and the check is deliberately wider than the one opcode so a broken
comparator would show up as disagreement everywhere rather than agreement here:
**all 477 GAME_SMSG messages the client registers agree field-for-field with
`schema/messages.json` + `overrides.json` on build 38797. Zero disagreements.**
`0x00E2`, `0x00E4` and `0x00E5` agree too.

Two things made the misreading easy, and both are now closed:

- **`msgshape.py` printed types 0 and 1 both as `dword`.** They are 4 bytes
  either way so nothing was ever misframed, but it discarded the only two
  semantic tags the client's descriptors carry, and `[dword, u16, u32]` is
  exactly the output a reader reconstructs "dword, agent_id, word" from. It now
  prints `agent_id` and `float`, so its output is directly comparable to the
  catalog. The mapping is `studies/msgtable`'s inference, cited at the
  definition: 127 type-0 fields against 127 `agent_id` fields across the 748
  shared messages, and type 1 appearing 4 times only inside the agent-position
  messages we type as `float`. Restricted to GAME_SMSG the correlation is
  **90/90 type-0 ↔ `agent_id` and 4/4 type-1 ↔ `float`, no exceptions.**
- **No `overrides.json` entry was needed and none was written.** Adding one, or
  "fixing" the call site to match the retracted layout, would have broken a
  working code path — `authsrv.py`'s `SKILL_ACTIVATED` echo is correct as it
  stands.

So the msgtable study's *"zero messages agree on total size but disagree on
decomposition"* stands; this section previously claimed it had found the
counter-example and it had not.

```bash
python toolkit/clientscan/msgshape.py 0x00E3
```

**The lesson is the one this repo keeps relearning from the other direction.**
Every prior trap here was the binary being harder to read than it looked
(zeroed `cmds` arrays, the `0xFF` opcode mask). This one was a *rendering* that
was easier to read than it should have been: the output was correct and
lossy, and lossy output invites the reader to supply the missing half from
memory. A tool that prints less than it knows is a tool that will eventually be
quoted as saying something it did not.

**A trap for anyone re-deriving field layouts:** most `cmds[]` arrays read as all
zeros in the file and are filled in at runtime by initializers that **copy from a
constant pool** (`mov eax,[src]; mov [dst],eax`), not by immediate stores. A
static zero decodes as type 0, a 4-byte scalar, which is a *plausible* field
descriptor — so a naive scan produces a confident wrong answer. This session
nearly published one.

### Where to go next, in order

**Superseded by §6p, which ran item 1 and killed it.** Kept because the ordering
was right and because item 3 turns out to be unsupported for a reason worth
reading. The live list is at the end of §6p.

1. ~~**Does the equipped-items bag give the weapon an attack speed?**~~ **RUN.
   It does not.** §6p.
2. **If it is not the bag**, find what writes `+0xEC`. It is not a displacement
   store. Try the caller chain from the crash — runtime→static is `+0x120000`
   for that dump, giving `0x7F867F`, `0x7F9F5F`, `0x7F3486`, `0x801732`.
   *§6p reproduces the crash and extends this chain from four frames to
   nineteen, each named to ArenaNet's own source file.*
3. ~~**The Collector lead, untried.**~~ **Unsupported — see §6p.** `0x20C` is not
   a collector marker; it is a hardcoded wire constant in the one lineage we
   copied it from, sent identically for a merchant, a collector and a guard.
4. **Pathing into range**, which is ours to write and needs no client knowledge.

---

## 6p. The bag is not the source, and the crash chain is an AgentView chain

Probe `attack_anim`, 2026-08-06, build 38797. One packet that mattered:
`0x00A0` generic value **4** `attack_started`, target = a hostile Hatcher,
cause = the player. Everything else in the probe exists to give it something to
swing at.

### The result: lead 1 is dead — OBSERVED

**The equipped-items bag does not give the client a weapon attack speed.** The
client died on the *same assert, at the same line*, as it did before the bag
existed:

```
Assertion: m_attackInterval
P:\Code\Gw\AgentView\AvChar.cpp(4791)
Build: 38797     When: 8/6/2026 16:31:49
```

The causal link needs no argument: the gamesrv log has
`s2c PROBE[attack_anim] generic value 4 attack_started target=7 cause=1
(0x00a0, 18B)` and then, with nothing in between,
`ConnectionResetError: [WinError 10054]`.

And the weapon really was equipped this time — the same log shows
`CREATE_NAMED_ITEM(starter hammer)`, `INVENTORY_CREATE_BAG(equipped)`,
`ITEM_MOVED_TO_LOCATION(hammer -> equipped 0)`, `WEAPON_SET[0] leadhand=1` and
`NPC_UPDATE_WEAPONS(leadhand = item 1)`. Bag, slot, weapon set and body, all
four, and `+0xEC` is still zero. So the reading GWCA's comment invited — that
the client computes the attack speed from the equipped weapon — is **not
satisfied by any of the four things we know how to equip.**

That closes the only written-and-unrun hypothesis in the arc. It is a negative,
and it is worth more than it looks: `--no-weapon` aside, there is now nothing
about *our* item handling left to blame.

### The caller chain, named to ArenaNet's own files — SOURCED

§6o asked for this and could only give four frames. The dump gives nineteen.
`BaseAddr: 002E0000` against the image base `0x400000` makes the fixup
**`static = runtime + 0x120000`**, and that is not assumed — the innermost frame
lands at `0x00487BDB`, `0x1B` bytes into the assert routine §6o had already
identified as `0x487BC0`.

Each frame is named by running `asserts.py --at` on it: **a function's own
assert call sites carry ArenaNet's source path**, which is §6g's method applied
to a stack trace instead of to a message handler.

| # | static | ArenaNet's file, from asserts in the same function |
|---|---|---|
| 0 | `0x00487BDB` | the assert routine itself |
| 1 | `0x007F82FA` | **AvChar** — 4791 `m_attackInterval`, 4792 `m_attackModifier` |
| 2 | `0x007F867F` | **AvChar** — 2222 `dancer`, 4745 `loop < 500` |
| 3 | `0x007F9F5F` | **AvChar** — 5893 `damage.amount <= 0`, the §6b assert |
| 4 | `0x007F3486` | **AvChar** — 1484 `curr->fileId` |
| 5 | `0x00801732` | **AvManager** — 714 `s_refCountAlert`, 775 `!s_reusableAgentArray.Count()` |
| 6 | `0x007DF2CE` | **AvApi** — 480 `agent`, 497 `stat` |
| 7 | `0x004E28C3` | **GmView** — 2840 `MissionCliIsGameMaster()` |
| 11 | `0x0063543D` | **FrApi** |
| 14 | `0x0062BE5F` | **EvtApi** |
| 15 | `0x004815B0` | **ExeTimer** |

Read bottom-up it is `ExeTimer → EvtApi → FrApi → … → GmView → AvApi →
AvManager → AvChar → AvChar → AvChar → assert`. Two things fall out.

**Frame 3 is the damage function.** `0x007F9F5F` sits inside the very function
that asserts `damage.amount <= 0` — the assert §6b earned with a positive
damage value. So generic value 4 and generic value 16 arrive at the *same*
AvChar routine, which is direct support for something the arc had only inferred
from field shapes: `0x00A0` and `0x00A3` are the int and float halves of one
mechanism. **Frame 6 names its own arguments** — `AvApi` asserting `agent` and
`stat` on consecutive lines is an entry point taking exactly those two things.

### Where to look next: AgentView, not the agent

§6o read the precondition site as operating on the agent. Every frame from 1 to
6 is an AgentView file, `AvChar` is the AgentView's own per-character object,
and `AvManager:775` calls its pool `s_reusableAgentArray` — recycled, which a
simulation agent would not be. So the object at `esi` is an **AvChar**, and the
searches that came up empty were aimed at the wrong place: "nothing writes
`+0x1B1`" and "no `fstp` writes `+0xEC` by displacement" were both looked for
outside AgentView.

> **§6q settles this and corrects the half of it that overreached.** There *is*
> an `fstp` to `+0xEC`, two of them, both inside `AvChar` — the displacement
> scan that missed them was simply not looking in this range. And the inference
> that AvChar is "not the struct GWCA documents" is **wrong**: GWCA names
> `+0xEC` `weapon_attack_speed` and `+0xF0` `attack_speed_modifier`, which is
> exactly what ArenaNet's own asserts call them. GWCA's `AgentLiving` *is*
> AvChar. What is true is that GWCA's map **drifts** — see §6q.

**The next move for item 2 is to read AvManager's pool init and AvChar's own
code, not to keep scanning for stores to an agent.**

### Lead 3 was unsupported, and reading beat guessing again — MEASURED

§6o's item 3 was "the enemy is a `Hatcher [Collector]` whose flags word is
`0x20C`, and collectors are non-combatants". Checked against the mirror it came
from, before spending a launch on it:

```
gameservice/StoC.go:113     flags  int  //wire:uint32,val:0x20C
```

**`0x20C` is a hardcoded constant on the wire field, not a per-NPC value.**
gw-preservation sends it identically for `gram_merchant`, `hatcher_collector`
and `ascalon_guard`; not one of its seven definitions carries a flags value of
its own. A number that never varies cannot be what distinguishes a collector
from a guard, so "those bits are why a click reads as interact" has no support
behind it.

What *does* vary per definition is `AllegianceFlags`, and it is the field-12
team token §6e already settled: five of the seven are `'nonc'` and two are
`'play'`. The non-combatant marker upstream is the allegiance, and we already
override it to an unrecognised token to get a red nameplate.

**The proposed experiment would not have tested its own hypothesis.** Swapping
in "a genuinely hostile NPC definition" changes the model id, the file id and
the EncString. The flags word would stay `0x20C`, because `0x20C` is all we
have. The hypothesis is about the flags; the experiment changes the model; §6e
established those are independent fields. Six misses in §6o came from guessing
at bit meanings, and this would have been the seventh — caught by reading the
source of the number rather than by running it.

### The run before this one measured nothing, and said so in the friendliest way

Recorded because the failure is a general one and it nearly landed in this
document as a finding.

The first attempt used `session.py --keep-open`, which spared the client and
let `main()`'s `finally` stop the servers anyway. The client's only peer was
those servers, so it dropped the connection and fell back to character select —
**`Code=007`, "Your connection to the server was lost"**. The probe never fired:
its first step is two seconds after the spawn rung the harness reads its verdict
at, and the stack was killed in that gap.

**The symptom was a client still running, still responding, with no assert
dialog** — which is exactly what a probe that ran and found nothing looks like.
The reading it invited was "no crash, so the bag worked", i.e. the opposite of
the truth. It was caught by checking the gamesrv log for the probe's own step
lines before believing the absence, and the log had none.

That is the fourth time this project has been wrong, or nearly wrong, about an
absence produced by an instrument that was not running. `--keep-open` now holds
the stack too, and blocks inside the run rather than orphaning it — the log
pumps are daemon threads on that process, so exiting would have truncated the
gamesrv log one line before the interesting one.

### Where to go next, in order

1. **Find what writes `+0xEC`, in AgentView.** Read `AvManager`'s pooled
   `s_reusableAgentArray` init and `AvChar`'s refresh path. The frames above are
   the entry points, and `asserts.py --at` names the file for any address, so
   the chain can be walked further without a disassembler.
2. **What does the client already know about a weapon that we never told it?**
   The `0x006E` mesh renders from `file_id`, so the client resolves an item's
   real record from `Gw.dat` — which means an attack speed may be a property of
   the *item type* rather than of anything on the wire, and our `STARTER_HAMMER`
   is UPSTREAM (OpenTyria's `GmDefaultArmors.c`) with two modifier words nobody
   in this repo has decoded. Those words are the obvious place a weapon's speed
   would live.
3. **Pathing into range**, still ours to write and still needing no client
   knowledge. It is the only item on this list that cannot fail for a reason we
   do not understand.
4. **The revive fix is still untested** — the probe ends the session by design
   before a kill-and-revive cycle can run, so property 34 has not been seen
   against a revived body. It needs a session driven by clicks, not a probe.

---

## 6q. The attack speed is a MESSAGE, and it is one nobody has ever sent

2026-08-06, continuing §6p. The wall is down. The client no longer asserts on
`m_attackInterval`, and a body swings a weapon on screen.

**`GAME_SMSG 0x0035` — `agent_id, float base, float modifier`, 14 bytes.** It is
the only thing in the entire image that gives an agent an attack speed, and
without it the client physically cannot animate a melee attack.

### The chain, end to end — SOURCED

Every step read out of our own pinned build 38797. Each caller is *unique*:
there is exactly one path in, which is why it can be stated this flatly.

```
GAME_SMSG 0x0035   handler 0x0091D810   (CharMsg neighbourhood)
                     reads {[msg+4] agent_id, [msg+8] float, [msg+0xC] float}
  -> 0x0080EA60      thin forwarder, same three arguments
  -> 0x007E0690      AvApi: agent id -> AvChar* via AvManager 0x00802160,
                     asserts the lookup (AvApi.cpp:739 `ptr`)
  -> 0x007FBD30      AvChar::SetAttackSpeed(float base, float modifier)
                       assert base     != 0    AvChar.cpp:7207
                       assert modifier != 0    AvChar.cpp:7208
                       [this+0xEC] = base
                       [this+0xF0] = modifier
```

`base` and `modifier` are **ArenaNet's own argument names**, read from the
assert strings at `0xA93F2C` and `0xA93F34` — not ours and not a
reconstruction's.

**The constructor writes 0.0 to both** (`0x007F1FD2`: `fldz; fstp [ebx+0xEC];
fstp [ebx+0xF0]`). So an agent the server never tells has an attack speed of
exactly zero, and the animation path asserts non-zero on the way in
(AvChar.cpp:4791/4792). The client asserts at **both ends** — on the write and
on the read — which is as clear a statement as a binary can make that this
field is never legitimately zero.

That is the whole of the `m_attackInterval` crash, and it explains why §6p's
negative was so total: **equipment was never the channel.** Bag, slot, weapon
set and body are all inputs to the *simulation*; the attack speed is something
the server states outright, on its own message.

### Nobody sends it, and nobody has named it

- **OpenTyria** names `GAME_SMSG 0x0033`, `0x0034` and `0x0037` and **skips
  `0x0035`** — a hole in the most complete public catalog, right where this is.
- No reference server sends it. Checked across gw-preservation, OpenTyria and
  GWLP-R.
- Our own catalog had the shape right all along (`agent_id, dword, dword`, 14
  bytes — one of the 477 that agree with the binary) and no name.

The name in `authsrv.py` is therefore **ours**, taken from the client's own
`SetAttackSpeed` argument names rather than invented.

### What the two floats mean — CORROBORATED, three ways

| field | meaning |
|---|---|
| `+0xEC` `base` | seconds between attacks, by weapon or creature type |
| `+0xF0` `modifier` | multiplier on that duration; **1.0 = none**, 0.75 = +25% IAS, 0.67 = +33% IAS |

An increase in attack speed makes each attack *shorter*, so the modifier goes
**down** as the character gets faster. The client multiplies the pair at
`0x007F837E` (`fld [esi+0xf0]; fmul [esi+0xec]`).

**And that multiplication reproduces the wiki's published table exactly.**
WIKI (GWW, "Attack speed" §"Attack durations and effect of IAS and DAS", read
2026-08-06), which states outright that these are the exact values the game
uses:

| base | ×0.67 | wiki's +33% | ×0.75 | wiki's +25% |
|---|---|---|---|---|
| 1.33 axe/sword/daggers | 0.8911 | **0.8911** | 0.9975 | **0.9975** |
| 1.5 scythe/spear | 1.005 | **1.005** | 1.125 | **1.125** |
| 1.75 hammer/staff/wand | 1.1725 | **1.1725** | 1.3125 | **1.3125** |

Six for six, to four decimals, on a check that could have failed. GWCA's
`Agent.h:181-182` independently names the same two offsets
`weapon_attack_speed` and `attack_speed_modifier`, gives 1.33 for
axe/sword/daggers and glosses the modifier as "0.67 = 33% increase". Three
sources with no shared ancestry — a wiki built from twenty years of play, a
reimplementation's header, and our own disassembly — agreeing on the same two
fields at the same two offsets.

**Our hammer therefore swings at 1.75s, not the 1.33 the server had been using.**
`ATTACK_INTERVAL` was invented in §6m and is now WIKI, and it is the same
constant we put on the wire, because the rate the server swings at and the rate
the client animates at are one number and they had been two.

### The assert is NOT synchronous with the packet — OBSERVED, and it cost a run

The first fix sent `0x0035` for the player only. **The client still died on the
same assert.** The reason is in the frames §6p had already named without anyone
reading what they were:

`AvApi 0x007DF280` takes a single float and fans it out to seven subsystems —
it is the **per-frame tick**, not the message path. So `attack_started` does not
animate anything. It **queues a request** at `AvChar+0xCC`, and a later frame
walks the queue and dispatches on `request->type` through a 28-entry jump table
at `0x007F8BF8`. **Type 3 is the melee swing**, and type 3 is the entry that
reaches the precondition.

Two consequences, and the first is a trap worth naming:

- **The crash blames the frame, not the packet.** It lands a moment after the
  send, in a stack with no message-handling in it at all, on whichever AvChar
  the request was queued against — *not necessarily the agent you aimed at*.
  Anyone reading that stack cold would not guess a packet caused it.
- **Every living agent needs an attack speed**, not just the one you think is
  attacking. That is what fixed it: the player, the standing enemy and the
  probe's own body all get one now.

### GWCA's offsets are exact here and drift later — MEASURED

Worth recording because §6o burned a session on the other end of the same map.

- `+0xEC` / `+0xF0`: GWCA is **exact**, names confirmed against ArenaNet's asserts.
- `+0x1B1` / `+0x1B2` (GWCA's `allegiance` byte and `weapon_type` u16):
  **nothing in AgentView touches either offset.** But a `byte` at `+0x1B7` and a
  `u16` at `+0x1B8` are written from seven and six sites respectively — the same
  byte-then-u16 shape, displaced by exactly 6.

So GWCA's map is not wrong, it is **drifting**: correct at `+0xEC`, six bytes
stale by `+0x1B1` on this build. Treat any GWCA offset as a lead to verify
per-field, and never as a coordinate. The `+0x1B7`/`+0x1B8` identification is
INFERRED from the shape match, not proven.

### The first agent slot of generic value 4 is the ATTACKER — OBSERVED

This corrects an UPSTREAM claim with our own bytes, and the evidence is a crash
rather than a screenshot, which makes it stronger than anything watching could
have produced.

GWCA's note on generic value 4 reads **"caster_id is victim, target_id is
attacker"** — i.e. this id inverts the usual roles. `hit_enemy` was built on
that: it put the enemy in slot 1 and the player in slot 2. **It is wrong for our
field order, and every swing this server has ever ordered was telling the client
to animate the ENEMY.**

The proof is the intermediate run that failed, and it was a controlled
experiment by accident:

| | agent 1 (player) | agent 7 (Hatcher) | packet | result |
|---|---|---|---|---|
| run A | attack speed **1.75** | **none** | `slot1=7, slot2=1` | **CRASH** m_attackInterval |
| run B | 1.75 | 1.33 | `slot1=7, slot2=1` | survives |

In run A the *only* agent in the world with a valid attack speed was the
player, in slot 2. The client asserted, and it can only assert on an AvChar
whose attack speed is zero. **So the body being animated was not the player,
and therefore not slot 2.** Slot 1 named agent 7. Slot 1 is the attacker.

That the fix for run A was "give the other agent an attack speed too" is what
makes it a measurement: had slot 2 been the attacker, run A could not have
crashed at all.

The A/B run, with both bodies on screen at different distances, agrees — and
returned one thing the model does not yet explain:

| step | packet | seen |
|---|---|---|
| A | `slot1=Hatcher, slot2=player` | the Hatcher **turns to face the player** and attacks — **and the player attacks too** |
| B | `slot1=player, slot2=Hatcher` | **only** the player attacks |

Step B is decisive on its own: if slot 2 were the attacker the Hatcher would
have swung and it did not. Step A's turn-to-face is a second free result — the
client reorients the slot-1 agent toward slot 2 before swinging, so slot 2 is at
minimum what the attack is *aimed at*.

**The extra player animation in step A is UNEXPLAINED and is not being written
down as understood.** MEASURED from the capture: the server sent exactly two
`0x00A0` packets that session and nothing else — no `INTERACT_PLAYER`, no
`hit_enemy`, no second attack — so the client produced two animations from one
packet. The candidate worth testing first is that **slot 2 plays a hit
reaction** and a flinch on a hammer-carrying body read as an attack at a
glance; that would also explain the asymmetry, since step A's victim is the
player in the foreground and step B's is a Hatcher nobody was watching. One
probe settles it: send step A and watch the *Hatcher* rather than yourself.

**This does not contradict §6f.** `0x00A3`'s first slot is the agent *damaged*;
`0x00A0` value 4's first slot is the agent *swinging*. Same message shape,
different roles per value id — which is exactly what GWCA's per-id note exists
to warn about, even though the note itself has the roles the wrong way round
for this build. **Read the slots per value id, never once for the opcode.**

### Two placement mistakes, both of which invalidated a run

Worth keeping because neither was a protocol error and both cost a launch, and
because the second was only caught by the owner looking at the screen.

- **The probe's Hatcher at +300 east landed exactly on the standing enemy.**
  `enemy_spot()` places that one at +300 whenever it is walkable, which it
  usually is. Two bodies in one spot: z-fighting, two nameplates stacked, and an
  animation whose performer could not be told from its neighbour.
- **Moving it to +600 to get clear put it out of sight**, apparently behind a
  wall. The only Hatcher on screen was then the *standing* one — which neither
  packet ever names. "The Hatcher did not swing" was therefore uninformative,
  and would have read as evidence for the wrong conclusion.

It sits at **+150** now, with the standing enemy at +300: both on screen, at
different distances, no flag needed and nothing turned off. A probe whose two
candidate bodies are not simultaneously visible cannot answer "which one moved",
and neither placement failure was visible from the server side at all.

### A note on method, since §6o's search was reported as exhaustive

§6o recorded "no `mov` and no `fstp` writes either offset by displacement
anywhere in the image". There are 238 instructions touching `+0xEC` image-wide,
and two of them write it from inside `AvChar`.

Two things were wrong with that search, and the second is the one worth
carrying forward.

**It was scoped to the wrong place and reported as a global absence.** Bounding
AgentView by its own assert sites turns 238 unreadable hits into 5, two of them
stores, in under a minute — and the range §6p had already established was
sitting there unused.

**And an access-flag filter cannot see either writer.** MEASURED: classify the
`+0xEC` accesses by capstone's operand-access flag and you get **zero** stores
in AvChar. Both real writers are `fstp`, which capstone reports as an operand
*read*. That is not a thin or suspicious result, it is a clean confident
nothing — the exact shape of §6o's sentence. **A float field is essentially
always written with an x87 store, so a tool that trusts the access flag is
blind to precisely the fields most worth chasing.**

Both traps are now in `toolkit/clientscan/codescan.py`, and both are pinned by
`test_codescan.py` with the counts they produce when the rules are removed
(18 instead of 11; 0 stores instead of 2), so neither can quietly come back.

**A third trap, found 2026-08-10 inside the tool this section describes.** The
image-wide figure above reads 238 and not 233 because `--field` was searching
one displacement encoding of two, and `--xrefs` one byte alignment of four. Both
produced the same clean confident zero §6o's sentence did — `--field 0xE --in
ExeArchive` answered "0 instructions" over a range containing `0x00478FB8 mov
byte [edi+0xe], al`, which is disp8 and so was never a candidate. The scans now
cover every encoding and every alignment, and both entry points print which ones
they searched, so a zero carries the discipline that produced it. `test_codescan.py`
§7 pins each at a named address. **Any absence claim in this study that came out
of `--field` with an offset under `0x80`, or out of `--xrefs`, was made by a
narrower search than its wording implies and should be re-run before it is
leaned on.**

```bash
python toolkit/clientscan/codescan.py --field 0xEC --in AvChar
```

---

## 7. Blockers, ranked

### 7.1 No HOSTILE definition exists anywhere — NOT FOUND

Narrowed by §6d rather than removed. The *method* is proven end to end and one
definition is known to work, so this is no longer "can we render an NPC" but
"which numbers make a Charr". Every published definition is a townsperson. Fournux states outright that "no
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

### 7.3a "Attacking doesn't work" is partly our own silence — OBSERVED

`--explorable` was tried and did not unlock attacking. But instrumenting the
session rather than believing the symptom found something better, and it
contradicts the assumption both runs were made under:

| Run | `INTERACT_PLAYER` (`0x0033`) at the red agent | `ATTACK_AGENT` (`0x0026`) |
|---|---|---|
| no flag | **11** | never |
| `--explorable` | **32** | never |

**The client issues interaction requests at the hostile agent in a town, and our
server answers none of them.** There is no handler for `0x0033` anywhere in
`authsrv.py`. That is the same shape as every movement bug this project has had:
the client asks, we say nothing, and the symptom looks like the client refusing.

> **STRUCK 2026-08-11 — both sentences above are false. See §10.6.**
> `authsrv.py:2636` has dispatched `0x0033` to `begin_attack` for days: the click
> reaches us and does start a fight. And `0x0033` is not an "interaction request"
> — it is **arm 1 of the six-arm world-action switch** at `0x00514840`, the one
> where ArenaNet's agents get arm 0 (`0x0026` ATTACK). The client is neither
> refusing nor asking; it resolved the click to a different action and sent it.
> The table survives as data; its framing does not. Those two rows are 2 of the
> **ten** `is_explorable = 1` sessions §10.6 measures, which together produced
> 80 × `0x0033` and zero `0x0026` — the town-versus-field gate was open and
> changed nothing, so `--explorable` is REFUTED as the lever rather than merely
> "tried and did not unlock attacking".

Two candidate causes remain, and this narrows rather than settles:

1. The client never sends `ATTACK_AGENT` at all — possibly the town, possibly
   the character having no weapon and no skills, possibly because it wants the
   interaction acknowledged first.
2. We ignore the interaction it *does* send.

Cause 2 is ours and is cheap to remove; cause 1 needs cause 2 gone before it can
be read honestly. **Do not conclude the outpost is the blocker** — the evidence
for that is currently an absence, and this project has been wrong three times
about absences produced by instruments that were not running.

One caution on `--explorable`: it changed nothing visible, but it also was not
*disproven* — 11 interactions versus 32 is a difference in how hard the player
clicked, not a measurement. Leave the flag; do not read it either way yet.

### 7.3b Attackability may not need a real explorable at all

`INSTANCE_LOAD_INFO` carries an **`is_explorable`** field, and this server has
always sent 0 — correctly, since map 148 is a town. Guild Wars forbids attacking
in a town. So the outpost that blocked §6e may be the client's own reading of
that one field rather than anything about the geometry.

If it is, combat is testable **today**, on Kamadan's geometry, with no map work
at all. If it is not, the negative is worth as much: it says the town/field
distinction is baked into the map data, and §7.3 becomes mandatory rather than
merely desirable.

Implemented as `--explorable` on the server, off by default — a server that lies
about its own map should do so only when asked.

### 7.3 Placement — largely retired

**Superseded by the file-id fix in §5.** Pre-Searing is reachable, so the map
blocker is no longer "we cannot name the zone" but the much smaller "we have not
chosen a spawn point in it". A walkable point is derivable from our own navmesh
without anyone else's data.

What survives: whether an explorable changes attackability is still untested
(§7.3a/§7.3b), and now testable properly.

### 7.3-old Placement

The Catacombs is reachable (§5) and has no published spawn point; a walkable
point must come from our own navmesh. Pre-Searing Ascalon City, the finish line's
home map, still has no resolvable file id.

### 7.4 Combat is unwritten everywhere else — but no longer unknown here

**Superseded in part by §6b, §6f and §6k.** The wire mechanisms for damage and
death are now measured against our own client, so this is no longer a research
blocker — it is unwritten *code*, which is a different and much smaller problem.
What the survey below still describes accurately is that **no other project has
any of it**, so there is nothing to copy and no reference to check against.

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

## 10. What draws the "cannot attack" marker — the refusal, read out of the binary

**OBSERVED 2026-08-11**, from build 38797, `codescan.py --dis` and `asserts.py`.
For a year of sessions this question was answered by absence: the client "has never
once sent ATTACK_AGENT to us" and what stopped it was NOT FOUND after testing the
weapon, the pools, the explorable flag, the team token and `0x002F`. The harness now
shows the client drawing a **prohibited marker on the target's own health bar**, so
the refusal is a decision, and decisions have code.

### The chain

`GmCoreAction`'s available-actions builder at **`0x005144F0`** fills a mask (`ebx`)
of what the player may do to the current target. Its own asserts name it:
`GmCoreAction:240 actionsList`, `:349 displayOrderIndex != arrsize(displayOrder)`.

```
005144F8  esi = actionsList          ; assert GmCoreAction:240 if null
00514541  call 0x7e1460  (AvPrefs)   ; -> je 0x5147af : bail, EMPTY list
00514551  call 0x84df60              ; -> jne 0x5147af : bail, EMPTY list
0051455E  cmp edi, [ebx+4]           ; target == self -> skip
00514570  test al, 0x10              ; a flag on SELF -> skip
0051457B  call 0x7e0da0 (AvApi:193)  ; -> reads AgentView +0x9C
00514583  cmp eax, 0xDB              ; TYPE TAG. not 0xDB -> ebx = 2, no attack
0051458D  call 0x7df870              ; -> the ALLEGIANCE enum
005145AD  lea eax,[edi-1]
005145B0  cmp eax, 5
005145B3  ja  0x514614               ; NOT 1..6 -> ebx = 2, no attack
005145B5  jmp [eax*4 + 0x5147b8]     ; six-arm switch, one arm per allegiance
```

**The six arms are our own `ALLEGIANCE_*` constants**, 1..6 — `agents.py` already
carries exactly that enum, and five separate readers of the byte compare it against
**3**, which is `ALLEGIANCE_ENEMY`.

### The two facts that matter, and they are new

**1. A lookup MISS returns 7, which is out of range.** The allegiance getter is
four instructions:

```
007DF876  call 0x802160                      ; a DIFFERENT list from the +0x9C one
007DF87E  test eax,eax / je
007DF882  movzx eax, byte ptr [eax + 0x1b5]  ; the allegiance byte
007DF88B  mov eax, 7                         ; NOT FOUND -> 7
```

7 fails `cmp eax,5 / ja` and drops straight to the minimal mask. So an agent that
renders, carries a nameplate and can be TARGETED — all of which our Hatcher does,
because those come off the AgentView list at `0x802160`'s sibling `0x802140` — still
offers no attack action if it is absent from the *character* list. Being visible and
being attackable are two different registrations.

**2. The allegiance byte is WRITE-ONCE, at construction.** `+0x1B5` has exactly two
writers in the whole image, `0x007F2419` (`mov al, [ebp+0x14]` — a constructor
parameter) and `0x007FA261` (`mov al, [edi+0x1c]`). **Nothing updates it afterwards.**

That is why `0x002F` was tested and did nothing, and it retires that line of
attempts: there is no post-construction setter to reach. Whatever decides an agent's
allegiance is decided **when the agent is created**, from the create burst, and a
later message cannot correct it.

### What this does NOT establish, said plainly

Which of the two gates our Hatcher actually fails. The `+0x9C == 0xDB` type tag and
the allegiance enum are separate, and this reading has not measured either value for
a live agent of ours. Our create sends field 3 = 1 and field 4 = 9 — **identical to
ArenaNet's worm**, an agent the client does attack — so the type tag is unlikely to
be the difference, but "unlikely" is not "measured".

**The cheapest next step is a read, not a run**: `keytap.py` already reads client
memory cross-process, so resolving our agent's object and printing `+0x9C` and
`+0x1B5` answers in one shot which gate fails, and turns this from a mechanism into
a diagnosis.

**Ruled out this session, so it is not re-tried:** the allegiance FourCC. Our create
sends `'mons'` where ArenaNet sends `'mon1'`, and that is the ONLY field differing
between our Hatcher's create and ArenaNet's worm's beyond ids, position and speed.
It looked decisive. It is not: **neither token appears anywhere in the image**, as a
dword or as text, so the client cannot be recognising either. `nonc` and `nonn` do
appear, exactly as §6e recorded. The team token is compared to the PLAYER's at
runtime (`ChCliBase.cpp:326`), which is why an unrecognised token reads red — and
red was always what §6e measured. Colour is not attackability, and the old comment
generalised from one to the other.

### 10.1 The read — and it REFUTES the chain above

**OBSERVED 2026-08-11**, `toolkit/clientscan/agentprobe.py`, reading the live
client's own memory while our Hatcher stood in the map:

| agent | `+0x9C` | `+0x1B5` | `+0x13C` bit 0x10 |
|---|---|---|---|
| player (1) | `0xDB` — CHARACTER | 1 `ALLY_NONATTACKABLE` | clear |
| **Hatcher (10)** | **`0xDB` — CHARACTER** | **3 `ALLEGIANCE_ENEMY`** | **clear** |

**Every gate in §10 passes.** Our agent is registered as a character, the client
has resolved its allegiance to ENEMY, and the flag that would skip the switch is
clear — so `GmCoreAction`'s six-arm switch runs its ENEMY arm and the mask is
built. The refusal is NOT in that function, and §10's chain, though correctly
read, is not the blocker.

**What that eliminates is worth more than what it found.** Every previous attempt
at this problem — §6e's team-token work, the `0x002F` attempts, the hostile-token
experiments — was aimed at convincing the client our agent is an enemy. **It
already is one, and now that is measured rather than assumed.** That whole family
of hypotheses is closed.

**A claim of mine that has to come back: the prohibited marker on the target's
health bar is NOT known to mean "cannot attack".** I read a small icon and
asserted a meaning for it. The read says the client considers the agent an
attackable-class enemy, so whatever that marker is, it is not the refusal. It may
be a range indicator, a line-of-sight marker, or something else entirely.
Screenshot-reading is not evidence, and this is the second time in two days that
inferring a mechanism from a picture has cost a detour.

**Where this leaves the question.** The agent's STATE is right, so the block is in
the path between "the mask says attack is available" and "the client transmits".
Candidates not yet read, in the order they gate:

- `0x007E1460` (AvPrefs) at `0x00514541` — returns 0 and the list is dropped whole
- `0x0084DF60` at `0x00514551` — nonzero and the list is dropped whole
- whatever consumes the mask and decides to send `0x0026`/`0x0027`

`agentprobe.py` makes each of these a read rather than a run, which is the loop
that just worked: three hypotheses eliminated in one 30-second measurement where
each would previously have cost a session.

### 10.2 The remaining gates, read — and a caveat about the whole section

**OBSERVED 2026-08-11.** Both bail-out gates in `0x005144F0` are now read.

**`0x0084DF60` — the player-flags gate.** Four instructions:

```
0084DF60  call 0x47f660            ; the thread-local game context
0084DF65  mov eax, [eax + 0x44]
0084DF68  mov eax, [eax + 0x2a8]   ; the PLAYER FLAGS dword
0084DF6E  shr eax, 4 / and eax, 1  ; returns bit 0x10
```

and the call site drops the action list **whole** when it returns nonzero. `+0x2A8`
is the same `context->playerFlags` the transfer work already named (bit 2 is
`PLAYER_FLAG_CONNECTED`, `MsCliGame.cpp:76`).

**Bit `0x10` is set in exactly two places and cleared in NONE.** Compare bit 2,
which has one setter (`0x008513A7`) and two clearers (`0x00850CA7`, `0x00851534`).
Both setters have the same shape and both are gated on a message field:

```
cmp dword ptr [msg + 0x18], 0
je  <skip>
or  dword ptr [ctx + 0x2a8], 0x10
```

`0x0084EE83` sits inside the handler for **`GAME_SMSG 0x0195`
INSTANCE_LOAD_SPAWN_POINT** (handler `0x0084ED00`), which our server DOES send. So
this was a live candidate for shooting ourselves in the foot. **It is not:** our
`0x0195` carries `[file_id, vec2, 0, 0, 0, 8 zero bytes]` — every trailing scalar
is zero, so the `je` is taken and the bit stays clear. Set-once-never-cleared is
worth keeping in view for the day we do put something there.

**`0x007E1460`** is a three-line wrapper: look the agent up in the plain
`0x00802140` array, return 0 if absent, else tail-jump to `0x005FCAE0`. Our agent
IS in that array — §10.1 read its object through it — so this gate is passed.

### The caveat, and it applies to all of §10

**`0x005144F0` may not be on the send path at all.** Its own asserts call it an
`actionsList` with a `displayOrder`, which reads like the UI's available-actions
menu rather than the code that decides to transmit `0x0026`. The genuine send site
is the six-arm `action` switch at `GmCoreAction:933`/`:997`, guarded by
`AvValidate(targetAgentId)`. Everything in §10 and §10.1 is correctly read and may
still be beside the point, and saying so is cheaper than someone else re-reading it
to find that out.

**What is established regardless, and it is the durable part:** our agent's state
is right. It is a CHARACTER, its allegiance is ENEMY, its skip flag is clear, and
the player flag that would empty the action list is clear. Four properties that
every previous attempt at this problem was trying to arrange, now measured rather
than assumed — and `agentprobe.py` measures them in thirty seconds.

### 10.3 THE GATE IS OUR WEAPON, not our enemy — bit 25 of the equipped item

**OBSERVED 2026-08-11.** Read from `GmCoreAction:997`'s classifier down to the leaf.
§10 chased the target for three sections. The target was never the problem.

**The chain, end to end.** `0x005149A0` (assert `GmCoreAction:997
AvValidate(targetAgentId)`) classifies a candidate target and its caller at
`0x004E22D5` **skips the target when it returns nonzero**. For the CHARACTER tag
`0xDB` it checks the flags bit, then switches on allegiance through the table at
`0x00514A60`. The table's dwords are `514A2A, 514A1C, 514A1C, 514A2A, ...`, so
**allegiance 3 (ENEMY) lands on `0x00514A1C`**:

```
00514A1C  call 0x5147f0
00514A21  test eax,eax
00514A23  je  0x514a56      ; ZERO -> not an eligible target
00514A25  xor eax,eax / ret ; NONZERO -> eligible
```

so for an enemy, eligibility is `0x005147F0` and nothing else. And that function
never looks at the target:

```
005147F9  push 0 / lea eax,[ebp-4] / push eax
005147FB  call 0x845890          ; equipment slot 0
00514801  call 0x845470          ; -> esi, the ITEM
0051480B  test esi,esi
0051480D  je  0x514838           ; NO ITEM -> return 0
0051480F  call 0x80d3e0          ; the player's own agent
00514815  call 0x80cee0          ; a predicate on the player
0051481F  jne 0x514838           ; -> return 0
00514821  push esi
00514822  call 0x8451e0          ; the ItCliApi item lookup
0051482A  mov eax, [eax + 0xc]   ; the item record's +0xC
0051482D  shr eax, 0x19
00514830  and eax, 1             ; BIT 25
00514833  ret
```

`0x00514838` is `xor eax,eax / ret`.

**So whether the client will attack an enemy is decided by BIT 25 of the player's
own equipped weapon record.** Three ways to fail it: no item in the slot, the
player-side predicate at `0x0080CEE0`, or the bit being clear.

**Why every previous attempt missed it.** They were all aimed at the target — the
team token, `0x002F`, the hostile allegiance, §6e's colour experiments. The
`ATTACK_AGENT` note does say "after testing the weapon (item and body)", and that
is true: it tested whether a weapon EXISTS. It could not have tested this, because
nothing had read the leaf. Our character carries the starter hammer and the client
draws it, so the item exists; what is unmeasured is bit 25 of its record.

**This also finally explains the `m_attackInterval` assert** recorded next to the
`EQUIP_WEAPON` code: "the weapon it was drawing had no attack speed". A weapon
record the client renders but does not consider a usable weapon is exactly the
state both symptoms describe.

**What is NOT established, and it is one step:** the value of bit 25 on our item,
and what sets it. That is a read of the same kind §10.1 did — `agentprobe.py`
already reaches the client's memory read-only, and the item is reachable through
`0x845890(slot 0)` -> `0x845470` -> `0x8451e0`. Do that before changing anything:
the whole point of this section is that four sessions were spent adjusting the
wrong side of the interaction.

---

### 10.4 The read — bit 25 is SET, and §10.3 is REFUTED

**OBSERVED 2026-08-11**, `toolkit/clientscan/itemprobe.py` against a live loopback
client, plus ArenaNet's own bytes in both live captures. §10.3 ended by naming one
step and telling the next reader to take it before changing anything. Taken:

```
context 0x01BB8988  manager 0x049BEFA0  inventory[0] = 0x00000001

handle     object  +0x28 flags  bit 25
     1 0x1CDC2040  0x22201000  SET

  1 bag(s) in the container map:
    key 0x00000001 at 0x1CFBEB28, 9 slot(s), 1 filled: [(0, 1)]

  BRANCH 1 PASSES: slot 0 holds item 1, gate dword 0x22201000, bit 25 SET.
```

**All three branches of `0x005147F0` pass on our own client.** There is an item in
equipment slot 0; its gate dword has bit 25 set; and the middle predicate is a
narrow special case (below). So the gate returns 1, the ENEMY arm returns 0, and
`0x004E22D5` **adopts** our agent rather than skipping it:

```
004E22D6  call 0x5149a0
004E22DE  test eax, eax
004E22E0  jne 0x4e22e4      ; NONZERO -> skip this agent
004E22E2  mov esi, edi      ; ZERO    -> ADOPT it as the target
```

§10.3's hypothesis is dead. It is the third chain in this section to be killed by
a read after being derived from the disassembly — §10.1 killed §10's, §10.2 killed
its own remaining gates, and this kills §10.3's. **That is now the pattern worth
naming: reading a decision tree out of the binary tells you what the client
CHECKS, and never what the answer IS on our data.** Only the probe does that.

**The field mapping is confirmed, not assumed.** `0x8451e0` returns `obj+0x1c` and
the gate reads `+0xc` of that, i.e. `obj+0x28`. The live object's bytes put our own
known values exactly where `0x0161 CREATE_NAMED_ITEM`'s wire order says they land:

| record | object | live bytes | wire field, and the value WE sent |
|---|---|---|---|
| `+0x00` | `+0x1C` | `60 9b 00 00` | `file_id`, we sent `0x80009B60` |
| `+0x04` | `+0x20` | `0f 06 00 00` | `item_type` **15 = hammer**, `dye_tint` 6 |
| `+0x0C` | `+0x28` | `00 10 20 22` | `flags` = `0x22201000` |

A one-to-one landing of four independently-chosen values is a check the artifact
could have refuted. `record+0xC` IS the wire `flags` word.

**ArenaNet sets the same bit, which is why ours was never the problem.** Read out
of both live captures by joining `0x013F CREATE_BAG` (type 2 = equipped) to
`0x013E ITEM_MOVED_TO_LOCATION` slot 0 and thence to `0x0161`:

```
20260807T143055  slot 0 item -> flags 0x22001000  bit25=1   (Necromancer, staff)
20260810T235916  slot 0 item -> flags 0x22201000  bit25=1   (Ranger, bow)
```

and all four weapon-set leadhand items in each session are the same item. **Our
starter hammer's `0x22201000` is byte-identical to the Ranger's own equipped bow.**
33 of 123 items in that session carry bit 25 — so it is not a constant, and the
equipped weapons having it is a fact about weapons rather than about all items.

**The middle predicate, named.** `0x0080D3E0` is ChCliApi's local-player-id getter
(`ChCliApi:4809 !(playerId & CHAR_CLASS_BASE_MASK)`, matching its own
`test esi, 0xf0000000`), reading `+0x2AC` of the mission context at `[G+0x44]`
(`MsCliApi`). `0x0080CEE0` looks that id up through `0x005FC380` (`AgApi`) and
returns nonzero only when one field equals 1 AND another equals 6 — two specific
equalities, so a narrow special case rather than the common path. NOT measured
live; it is the only branch of the three still resting on reading rather than on a
probe, and it is the least likely of them.

**Corrections to §10.3, both from re-reading the same bytes:**

* The jump table has **six** entries, not four: `0x00514A60` holds
  `514A2A, 514A1C, 514A1C, 514A2A, 514A2A, 514A46`. The index is
  `allegiance - 1` (`0x00514A0C: dec eax`), bounded `<= 5`, so allegiance 7 — the
  lookup-miss value §10 built its original chain on — falls out to `0x514A4E`.
  **Allegiance 2 (NEUTRAL) takes the same arm as 3 (ENEMY).**
* §10.3 wrote "eligibility is `0x005147F0` and nothing else" as though the
  classifier were the action path. It is not. **All three callers of the
  classifier are view or UI** — `GmView` at `0x004E22D6` (preference-gated: the
  two calls before it are `AvPrefs`), `GmView:2611` at `0x004E6BEF`, and
  `UiCtlInstance` at `0x00516AAD`. The gate `0x005147F0` itself has two further
  callers inside `GmCoreAction` (`0x005145BC`, `0x005146A8`), which is the action
  layer — and both use the same "0 means eligible" convention
  (`0x005146AD: neg eax / sbb eax,eax / inc eax`). This does not change the
  verdict: the gate passes, so **every one of the five consumers gets "eligible"**.

**Where this leaves the arc.** The refusal is not the target's allegiance (§10.1),
not the target's flags or type tag (§10.2), and not our own weapon (here). Four
properties of the interaction have now been measured and are all correct. The
`m_attackInterval` assert at `AvChar.cpp(4791)` remains the one hard observation
nobody has explained, and §6p's reading of it — that the field lives on the view
layer `AvChar` rather than on the agent — is now the only surviving lead. §10.3's
claim that bit 25 "finally explains" that assert is withdrawn.

**A standing instruction, earned three times over.** Do not derive another chain
from the disassembly and act on it. Derive it, then read the values it depends on
out of a running client — `agentprobe.py` for agents, `itemprobe.py` for items,
both read-only. Each of those two probes took under an hour and each one killed a
hypothesis that had already survived a session of reasoning.

---

### 10.5 The A/B nobody realised they had run — and its evidence is five days stale

**OBSERVED 2026-08-11**, measured over the whole capture tree (862 `.jsonl` logs, of which
**175 carry a game-channel VERSION**; 430 are auth and 257 have no VERSION record). §8.0
item 0a stated this as "the client aims `0x0026` at agents ArenaNet created and `0x0033` at
ours, in the same map type". That is right in substance and understates the design.

| sessions | `0x0026` ATTACK | `0x0033` | who created the agents |
|---|---|---|---|
| 19 × 2026-08-06, hand-driven | **0** | 206 | **our server** (2–5 `0x0020` each) |
| 2 × 2026-08-10, tape replay | **7** | **0** | **ArenaNet's tape** (0 of our creates, 1074 tape sends) |

**Zero overlap in either direction.** Same client binary, same `authsrv.py` process, same
map — the only variable is whose create burst produced the agents. That is not a comparison
across session types; it is an A/B with the create burst as the manipulated variable, and
it is the strongest evidence in this arc that the difference is IN THE CREATE BURST.

`0x0033`'s first field is **10** in 147 of the 206, and `authsrv-20260806T120212-c2` logs
its own creates as `WORLD_CREATE_AGENT` and `WORLD_CREATE_AGENT(10, hostile)` — so field 1
is an agent id and the operator clicked our Hatcher 147 times without once producing an
attack. In the tape sessions the same client sent `0x0026` at 274, 275, 276 and 284.

**THE PART THAT MATTERS MOST: the 0x0033 side is from 2026-08-06 and nothing has re-tested
it since.** Everything the client reads about our agent has changed in between — the
allegiance and type tag are now MEASURED correct (§10.1), the skip flag is clear (§10.2),
the weapon gate passes (§10.4), and `0x0048`, `0x00A6` and `0x0026` are now sent (§8.0 0g).
The 206-to-0 split is a fact about a **five-day-old server**.

**And no labelled run has ever been pointed at one of our own agents.** `labelrun.py` has an
`attack` step. All three label runs in the vault (`20260810T142912`, `144215`, `151946`) are
**tape** sessions — 1074 sends and zero `0x0020` of our own in every one. The only one that
produced anything is the tape run, where `attack` yielded `0x0026` at agent 284 and
`target_tab` yielded `0x00C1` at 273/274/276. So the instrument that would settle this
exists, is proven to work, and has never been aimed at the question.

**THE CHEAPEST DECISIVE EXPERIMENT IN THE ARC, and it is one operator session.** Run
`labelrun.py` against our OWN server with the Hatcher spawned, and read which opcode the
`attack` step produces. `0x0026` means the blocker is gone and R4a's refusal died to work
already landed; `0x0033` again means it survives every property measured so far and the
create-burst differential is the next place to look. Either outcome is worth more than more
static analysis, and §8.0 0a already says to fold it into the same session as 0c's burrow
probe. **Do not read the 206-to-0 table as current.**

---

### 10.6 It was never a refusal — `0x0033` is a DIFFERENT ARM of the same switch

**OBSERVED 2026-08-11.** Every section of §10 has asked what *withholds* the attack
action. The question was wrong. The client is not withholding anything: it evaluates a
switch, picks an action, and sends it. It picks **arm 1** (`0x0033`) where ArenaNet's
agents get **arm 0** (`0x0026` ATTACK). Same function, same click, same target field.

**The switch, verified here byte by byte.** `0x00514840` takes `(action, targetAgentId,
arg3)`, asserts `action < 6` (`GmCoreAction:933 action < WORLD_ACTIONS`, compiled as
`cmp ebx,6 / jl`) and `AvValidate(targetAgentId)` (`:934`, via `0x007E1460`), then
dispatches through the table at `0x00514984`. The action index arrives from
`0x004E6B20` — `0x004E2172 call 0x4e6b20 / mov ebx, eax` — whose own asserts name it
the click path: `GmView:2229 !(selectFlags & UiMsgGameSelect::FLAG_NO_INTERACT)` and
`GmView:2234 !((selectFlags & FLAG_DBL_CLICK) && !(selectFlags & FLAG_DUE_TO_CLICK))`.

So `0x0033` is not "interact". **It is what the client sends when the world-action switch
resolves a click to arm 1 instead of arm 0.** REPORTED (workflow, not re-verified here):
the arms carry ArenaNet's own menu string ids, arm 0 "Attack", arm 1 "Follow"/"Move To",
arm 2 "Talk To" — which would make `INTERACT_PLAYER` the wrong name for `0x0033` and the
right name for `0x0039`. Treat the id→arm mapping as ours and the labels as UPSTREAM until
someone re-reads them.

**Our server already treats `0x0033` as an attack order — VERIFIED, and §7.3a is wrong.**
`authsrv.py:2636` is `elif opcode == GAME_CMSG_INTERACT_PLAYER: begin_attack(send, state,
values[1], conn_id)`. §7.3a's line "There is no handler for `0x0033` anywhere in
`authsrv.py`" (line 1614 of this file) is false and should be struck. The consequence is
the opposite of what that section assumed: the click IS reaching us and IS starting a
fight; what never happens is the client running its own attack.

**`is_explorable` is EXCLUDED as the cause — and by more than the workflow found.**
`GAME_SMSG 0x0199`'s field is byte offset 8 of a 15-byte message (schema:
`msg_header, agent_id, word, byte, dword, byte, byte`). Swept over every game-channel
session in the vault:

```
2026-08-06  is_explorable=0   48 sessions   0x0033 x126, 0x0039 x16
2026-08-06  is_explorable=1   13 sessions   0x0033 x 80, 0x0039 x 6      <-- gate OPEN
2026-08-10  (tape's own)      11 sessions   0x0026 x  7, 0x0039 x 4
2026-08-11  is_explorable=0   21 sessions   NO WORLD ACTION AT ALL
```

**Ten of the nineteen zero-attack sessions had `is_explorable = 1`** and still produced
only arm 1. The town-versus-field gate at `0x00816090` was open and the classifier still
returned 1, so the transmit leaf is not the cause. (The workflow reached this from one
session; the sweep makes it ten.) `authsrv.py:2316`'s comment — "this one field may be all
that stands between us and testing combat" — is REFUTED by our own wire.

**And the 2026-08-11 row is the operational finding.** Twenty-one game sessions today,
zero world actions of any kind. Nothing has been clicked since 2026-08-06, which is what
§10.5 said and this now measures directly.

**REPORTED and NOT re-verified here** (workflow's readers, each passed through a skeptic):

* `GAME_SMSG 0x0056` field 6 bit `0x200` — **REFUTED.** One session created four agents on
  one definition (field 6 held at `0x20C`) differing only in agent id, position and the
  allegiance FourCC; the client answered `0x0039` for `play`/`nonc`/`nonn` and `0x0033` for
  `mons`. Another session sent no `0x0056` at all and the split still appeared. Field held
  constant, then absent, answer changed. **Do not retune `content/npcs.toml`'s `0x20C`.**
* `0x00F0` / `0x006D` as the gate — **REFUTED.** They are ArenaNet's universal create
  bracket (`0x00F0` before 951/951 team-bearing creates, `0x006D` after 546/546 non-`play`
  creates), including 313 agents nobody ever attacked. Send them as hygiene, not as an
  experiment.
* The equipped-bag story — **CONTESTED, and honestly so.** All 19 zero-attack sessions have
  zero `0x013F`; both attack-producing sessions have bags. But bag presence is perfectly
  collinear with date, driver, and agent provenance, and no session ever mixed them — so
  its `could_have_failed` is unsatisfiable. It is the best-supported candidate and it is
  not established.

**THE INSTRUMENT DEFECT THIS TURNED UP, and it is ours — OBSERVED, verified.**
`asserts.py` self-reported 19,758 readable sites + 3 it named as unreadable. An
independent sweep of `.text` (5,471,232 B) for `call rel32` landing on the assert routine
finds **20,131**. The tool was short by **370 sites it did not know it was missing**: all
three shapes are contiguous byte patterns, and anything the compiler schedules into them
breaks the match. Worked example: `AgAgent:2366` (`AGENT_MIN_MOVE_SPEED`) at `0x006029BC`
carries an `fstp st(0)` and is invisible, while its twin `:2367` three instructions later
at `0x006029D4` is read — which is exactly why nobody noticed. `--grep AGENT_MIN_MOVE_SPEED`
returns 0 sites for an assert that is provably there.

**Every "no assert names X" claim in this arc is therefore a floor, not a census** — and
`codescan.py --in <module>` takes its bounds from the same tool. `coverage_lines()` now
prints the shortfall under every query, measured against the image rather than against the
scanner's own idea of what it missed.

### 10.7 `0x0026` IS ON THE WIRE — the blocker is dead

**OBSERVED 2026-08-11**, capture `authsrv-20260811T134205-c1.jsonl`, the `worldaction`
labelled run on loopback. Both idle controls silent, so the attributions stand.

```
step key            expect     n  opcodes
  1 idle_a         CONTROL     0  --
  2 target_click   traffic     1  0x0026 x1     values=[32806, 10, 0]
  3 menu_open      silence     0  --
  4 dbl_click      traffic     2  0x0026 x2
  5 menu_attack    traffic     0  --
  6 attack_other   traffic     1  0x0026 x1
  7 skill_attack   traffic     1  0x0027 x1     values=[32807, 320, 0, 10, 0]
  8 skill_nonattack traffic    1  0x0046 x1
  9 idle_b         CONTROL     0  --
 10 gateway        traffic     1  0x003E x1
```

**Four `0x0026` and ZERO `0x0033`.** `values[0]` is the client's OR'd opcode (`0x8026`)
and `values[1]` is the target: **10**, our Hatcher. The year-long "the client has never
once sent `ATTACK_AGENT` to us" is over, and it did not take a code change to end it —
§10.6 called it right. `0x0026` is arm 0, `0x0033` is arm 1, the client picks the arm,
and given a correctly-stated agent it picks arm 0. A single left-click is enough (step 2:
one click, one ATTACK); double-click sends two.

**The 206-to-0 split was a fact about a five-day-old server.** Every property §10 chased
was already right; nothing in §10.1–§10.4 was the lever, because by the time they were
measured there was nothing left to lever.

**What now blocks a fight is OURS.** `authsrv.py` has no `GAME_CMSG_ATTACK_AGENT`
constant and no dispatch arm — the client asked to attack four times and got silence, the
same shape as every other bug in this project. `0x0027` does work end to end (step 7:
skill 320 → the server swung → 15 damage → 85/100), so the arm landed for `0x0027` is the
template.

**TWO CLAIMS OF MINE DIE HERE, and both are the same error.**

**1. There is no right-click context menu on a world agent.** `0x005144F0` is real and
really does build an `actionsList` with a `displayOrder` — that is read from its own
assert strings. **Nothing anywhere says it is opened by right-clicking an agent**, and
nothing says it surfaces in the world at all. §10's own caveat had it as "reads like the
UI's available-actions menu", a RECONSTRUCTION; `PLAN.md` §8.0 0k hardened that into "the
menu IS the gate's answer", and `labelrun.py` restated it to an operator as fact. Steps 3
and 5 produced zero messages, and 20 s of frame grabs at 1 fps show no menu at any point.
Cost: two of ten steps. **A gesture is not in the disassembly.**

**2. The "prohibited marker" is a button that clears the selected target.** SOURCED
2026-08-11, owner. §10 was *founded* on that icon — "the client draws a prohibited marker
… so the refusal is a decision, and decisions have code" — and the icon is a standard
control present on every target frame, saying nothing about anything. §10.1 already walked
the claim back to "not known to mean cannot attack, may be range or line of sight"; it is
now closed, and the honest summary is that a whole section's premise was a misread UI
widget. Third time in three days that inferring a mechanism from a picture cost a detour.

### 10.8 The burrow probe, RUN — definitions are per-instance, and `0x1000` is an animation

**OBSERVED 2026-08-11**, capture `authsrv-20260811T135809-c1.jsonl`, probe `burrow` on
loopback. Watched live by the owner; frame grabs at 2 fps corroborate. The wire is the
control that makes it mean anything: `0x0056`/`0x0057` were sent **once, at t=2.73 s**,
and never again — so both re-creates below were bare `0x0020`.

| t | sent | seen |
|---|---|---|
| 5.74 | `0x00F1` [10, `0x1000`] | the Hatcher plays a **fall** animation and lies prone |
| 9.75 | `0x00F1` [10, 0] | it plays a **get-up** animation and stands |
| 12.76 | `0x0021` [10] | clean vanish |
| 16.78 | `0x0020` same id 10, **no definition** | **a correct-looking collector, back** |
| 22.78 | `0x0020` fresh id 12, **no definition** | **a second correct-looking collector** |

**Both re-creates worked, which is the probe's `3 works, 4 works` arm: a definition is
per-INSTANCE and outlives the agents using it.** Declare once at map load, re-create
freely. This is our own client answering the question that §0c had answered only by
inference from ArenaNet's 1-declaration-to-140-creates — and inference was not enough,
because what was untested was OUR create path, not their client. `burrow_tick` now passes
`send_definition=False` and a content row can still opt back in.

**THE PREDICTION THAT WAS REFUTED, and it is the more interesting half.** The probe's
stated honest expectation for `0x1000` was *"nothing visible happens, because a client
that hid an agent on this bit would not also need the removal ArenaNet sends 2.00 s
later."* The reasoning was sound and the conclusion was wrong. **`EFFECT_TRANSITION` is
an ANIMATION, not bookkeeping and not a visibility flag** — set it and the agent goes
down, clear it and the agent gets up. The agent stays rendered and keeps its nameplate
the whole time (my first read of the frame said the body was gone; it is prone behind
the player — SOURCED, owner, who was watching at full resolution).

That resolves the apparent contradiction instead of being contradicted by it: the bit
animates, the **removal** hides. ArenaNet's two 2.00 s windows are exactly the length of
the down and up animations, with `0x0021` landing at the end of the first and `0x0020`
at the start of the second. Our `burrow_tick` already holds the bit for 2.00 s each way,
which was copied from measured timing without knowing what it bought; it buys the
animation, and dropping it would make worms teleport in and out.

**UNVERIFIED, and worth saying:** whether the down animation is burrow-specific or a
generic knockdown. One agent, one model, one probe — a Plague Worm would settle it.

### 10.9 One click, a whole fight — and the client asserted on the revive

**OBSERVED 2026-08-11**, three loopback runs, captures `authsrv-20260811T1406*`,
`T141120`, `T141339`. Driven with a single scripted left-click on the Hatcher at a
window fraction measured off the frame grabs, so no operator hands were involved. A
missed click would have shown as `0x003E` MOVE_TO_COORD; all three sent `0x0026`.

```
t=14.56  c2s 0x0026 ATTACK [agent 10]        <- one click
t=14.57  attack_started + damage 15 + melee_attack_finished
         ... 7 swings, 1.77 s apart (ATTACK_SPEED said 1.75), 15 each = 105
t=25.20  the 7th lands; a 100 hp agent is dead
t=26.10  c2s 0x00C1 TARGET_SELECT [0]        <- the CLIENT drops the dead target
t=33.24  revive + restore max health + refill bar
t=33.28  c2s 0x00C1 TARGET_SELECT [10]       <- and re-acquires it, 40 ms later
```

Both `TARGET_SELECT`s are unprompted client behaviour and neither is something our
decoder can force, which is what makes the death and the revive facts about the client
rather than about our bookkeeping. **`0x0026` → `begin_attack` works end to end.** The
animation renders too: mid-fight frames show the player mid-swing with the hammer up, a
floating `-15`, and a partly-drained bar.

**IT IS STILL NOT A FIGHT IN THE TWO-WAY SENSE.** Nothing swung back and the player took
no damage, exactly as §3's R4a row has said since 2026-08-06. There is no enemy AI; this
rung is the client asking and us answering, not combat.

### THE CRASH, and why twenty sessions of damage testing could not have found it

The first run of this went down two seconds after the kill:

```
Assertion: fraction <= 1.0f
P:\Code\Gw\Char\CharPool.cpp(84)          Build: 38797
```

The trace carries our own message three frames below the assert —
`Arg:00000022 0000000a 0000000a 42c80000`, i.e. property **34**, agent **10**, agent
**10**, and `42c80000` = **100.0f**. That is `revive_due`'s "refill bar" send, which
passed `max_health` where the client wanted a FRACTION of a pool.

**The assert is `<=`, so it can only fire in the POSITIVE direction.** Every value this
project had ever put on the `0x00A3` float channel was damage — `-HIT_FRACTION`, and the
`-50.0` that `GV_HEALTH`'s own comment is built on. A negative number passes
`fraction <= 1.0f` however absurd it is, so the entire damage side of this arc tested that
bound **vacuously**. It took the first kill driven all the way to a revive — the first
positive value ever sent — to reach it.

Fixed by sending `1.0`, and by routing both float-channel sends through `_fraction()`,
which **refuses** out-of-range rather than clamping: a clamp turns a wrong number into a
plausible one and the next caller never learns. Re-run confirms no crash (the session ran
45 s past the revive and exited clean) and that the bar refills — the post-revive frame
shows a full bar against a mid-fight frame showing a drained one, which is the control
that makes "full" mean anything.

**SETTLED the same day, from the client's own dispatcher — `studies/agentprops/FINDINGS.md`
§1d.** Both properties are FRACTIONS and the difference is only who multiplies: `0x00818210`
switches on the property id, sends **16** to an arm that `fmul`s by the max, and sends **34**
to an arm that passes the value through RAW into `0x009215F0` — the CharPool method whose
line 84 is the assert. So `1.0` is a full pool for a reason rather than by luck. **And the probe ran the same
day (§1e): property 34 is a SETTER** — it sets the pool to `fraction × maximum`. The orb
went 100 → 90 on property 16 at -0.10, then to the floor of **1** on property 34 at -0.50,
where a delta predicts 40. So `1.0` on the revive sets the bar full rather than adding to
it, which is why it works from a pool the death path zeroed, and `max_health` was the wrong
*kind* of number rather than merely too large a one. Both the old §1b reading and §1d's own
headline were wrong, and so was the prediction the probe stated before running.

### The instrument defect this turned up, and it is ours

**The harness printed `RUN VERDICT: PASS` on the run that crashed.** A Guild Wars assert
puts up a modal dialog and **keeps the process alive** waiting for a click, so
`proc.poll()` stayed `None`, the hold expired on its timer, and `capture_error_dialog` —
which existed, was tested, and was written precisely for this — was called only from the
`proc.poll() is not None` branch. The crash text sat on screen for the rest of the run and
the report said green. `hold_open` now checks on both exits. Same shape as every other
defect in this file: the check was right and the caller never reached it.

## 11. Something swings back — R4a's other half, met

**OBSERVED 2026-08-11.** Capture `authsrv-20260811T160502-c1.jsonl`, frames
`frames-20260811T160449`, one 65 s loopback run.

**What the operator did, because "no operator input" is what this first said and it
was wrong.** The owner moved the camera while watching, and camera movement is not
free: the capture's client half is one `ROTATE_PLAYER` (0x0040) and one
`TARGET_SELECT` (0x00C1), plus instance-load traffic. What is NOT there is the
part that matters — no `0x0026`, no `0x0033`, no `0x003E`, no skill. **The player
never attacked, never moved and never struck back**, so the fight is entirely the
server's proximity sweep acting on an idle target, which is a stronger
demonstration than the one originally claimed rather than a weaker one. (It also
corroborates §10.7 from the other side: a right-CLICK produced no traffic, and a
right-DRAG that actually turns the camera produces `ROTATE_PLAYER`.)

```
30 x attack_started            agent 10 -> the player
30 x damage 10 to the player   0x00A3 property 16, -0.10
30 x melee_attack_finished
 3 x KILL the player           0x00F1 bit 4 on PLAYER_AGENT_ID
 2 x revive the player         t=15.36 kill, 25.39 revive, 37.66, 47.67, 59.97
```

Ten swings to a death at the Hatcher's own 1.33 s axe speed, and the revive
exactly 10.0 s behind each kill. The frames show the player face-down with both
orbs at zero, then standing at 80 health with a floating red `-10` over their
head as the next swing lands.

**The mechanism was already proven, by an accident.** `hit_enemy` carries a
comment about an early version that put the ENEMY in slot 1 of
`GV_ATTACK_STARTED`: the client animated the enemy and then asserted on
`m_attackInterval`, which is how slot 1 was identified as the swinger and why the
attacker must have a non-zero declared attack speed. `hit_player` is that mistake
made on purpose. Nothing new about the wire had to be discovered to build this —
the three-message swing, the damage fraction and the death bit were all already
known, and what was missing was a sweep that pointed them the other way and a
server that remembered the player's health.

**Two things this run settles that were open.**

**The client accepts `EFFECT_DEAD` on its OWN agent.** This was the one part shipped
UNVERIFIED: no player death was found in either live capture, so the death message
is our agent path aimed at `PLAYER_AGENT_ID` rather than a replication of
ArenaNet's. It works, and it produces the real death pose and zeroed pools rather
than an agent-shaped approximation of one.

**Property 16 drives the player's bar and the floating damage number.** Same
opcode, same property, same fraction semantics as against an agent, with the
target and cause slots swapped.

### What this is NOT, said plainly

- **There is no AI.** The Hatcher stands exactly where it spawned and swings at
  anything inside 1200 units. It does not chase, it does not leash, it does not
  stop when the player walks away except by falling out of range. `AGGRO_RANGE`
  and `ENEMY_HIT_FRACTION` are ours; nothing measured them.
- **The revive is a timer**, not a resurrection shrine, not a party wipe, and not
  whatever retail actually does. `player_revive_due`'s docstring says so at the
  call site.
- **Energy is not restored.** The client's death path zeroes BOTH pools and the
  revive only refills health — the post-revive frame shows the energy orb at 0
  and it stays there. Re-asserting a maximum is documented not to refill
  (`revive_due`), so the fix is not simply another `PROP_ENERGY_MAX`, and the
  energy equivalent of property 34's setter is not known. **Open.**
- **One player, one enemy, one instance.** Nothing here has been tried with two
  hostiles or with an agent that moves.

### 11.1 What ArenaNet's own combat traffic says — and where §11 was wrong

**OBSERVED 2026-08-11**, from the live corpus rather than from our own server: a
five-question fan-out over `vault/captures/live/`, every code-driving claim then
handed to an independent skeptic. **47 verifications, 16 refuted.** The refutations
are the useful half and most take the shape "the arithmetic reproduces exactly,
the inference does not" — recorded here so nobody re-derives a killed claim.

**The corpus.** `20260807T143055` connection `:64103` — a Warrior in Lakeside
County. NPC agent `0x28` attacked player agent `0x1F` seven times between
t=10.266 and t=23.268. Six landed; the seventh was cut off when the player killed
the NPC 0.243 s into it. The player's own agent id was established five
independent ways, including a four-char tag in the create (`play` against `mon1`
on 142 others) — a field that reads as garbage decoded as a number, the
marshalling-type trap again.

**CONFIRMED, and it independently re-derives what §11 built from an accident:**

| claim | strength |
|---|---|
| `0x00A0` value 4: slot 1 is the ATTACKER, slot 2 the target | the set of agents ever given an attack speed is EXACTLY the set ever in slot 1 — **11 to 0** against the rival |
| `0x00A3` property 16: slot 1 is DAMAGED, slot 2 the CAUSE, value is a fraction of the DAMAGED agent's maximum | `|frac| x maxHealth(slot 1)` is a whole number **13 of 13**; against slot 2's maximum, **0 of 13** |
| the player takes damage through the same channel as an NPC | 26 hp of 100 over six swings |

Both were already right in `hit_player`. The `m_attackInterval` accident had them
correct, and this is the first evidence that could have said otherwise.

**REFUTED BY THE RUN — a swing is not instant, and §11 sent it as one.** The
opening is `ATTACK_STARTED`; the landing arrives **0.880–0.919 s later** (mean
0.899, n=6) as `MELEE_ATTACK_FINISHED` **then** the damage, adjacent in one TCP
payload — verified by byte offset rather than by timestamp, 6 of 6. §11 sent all
three messages in the same instant and in the other order, so the damage number
appeared on the frame the animation began. Now two-phase (`start_swing` /
`land_swing`) and a pending landing is DROPPED if its swinger dies or leaves
range, which is what ArenaNet's truncated seventh swing shows.

**`hit_enemy` is deliberately NOT reordered.** The claim about how ArenaNet marks
the CONTROLLED agent's own landings (`0x00A7` rather than `0x009F` value 1) was
**refuted** on review, so the player's swing has no verified model to copy and
guessing at one trades a known shape for an unverified one.

**Claims that did NOT survive — do not rebuild these:**

- **"The declared attack speed is a floor, not the period."** Refuted: the
  measurement reproduces, the inference is contradicted by the claimant's own
  numbers, by an omitted counterexample in the same tape, and by the tape's
  measurable timing noise.
- **"`0x0035` is sent lazily at first swing, never at spawn."** The count
  reproduces; the generalisation collapses once the sample widens past one agent.
- **"ArenaNet never sends `0x009F` value 1 for the controlled agent."** The
  arithmetic reproduces; the mechanism is refuted by a counterexample in the same
  corpus and the operational advice was drawn from the wrong axis.

**NOT FOUND, and it stays not found: no player death anywhere in the corpus.**
"The player can take damage" is OBSERVED; "the player can die" is not. So §11's
death path remains ours rather than ArenaNet's — what the live run settled is
that the client *accepts* it, not that it is what retail sends.

**A METHOD FAULT THAT IS MINE.** The tree moved under the readers: two agents
reported the implementation arriving uncommitted mid-run and `HEAD` moving from
`0421806` to `1d3530f` beneath them. I was editing the tree the research was
reading, which is exactly the hazard `CLAUDE.md` names about pinning subagents.
It happened to catch real defects in the in-flight code — a corpse that could
still cast, and `ValueError` uncaught on the world tick, both now fixed — but that
is luck, not method. Read-only fan-out over a moving tree should use
`isolation: "worktree"`.

### 11.2 It walks now — and `AGGRO_RANGE` was doing two jobs

**OBSERVED 2026-08-11**, capture `authsrv-20260811T174346-c1.jsonl`.

```
t=2.62  agent 10 speed 0.75 (216 u/s)        0x002B
t=2.62  agent 10 walks to (9826,8077)        0x0029  <- the player's position
t=3.33  attack_started: agent 10 swings
t=3.38  agent 10 stops at (9976,8077)        0x0029  <- exactly 150 units out
```

150.0 units of travel in 0.71 s at a declared 216 u/s is 0.69 s of walking, so the
server's own copy of the agent's position and the rate it told the client agree.
Then 20 swings and 2 kills.

**THE DEFECT THIS FIXES IS OURS AND §11 SHIPPED IT.** `AGGRO_RANGE` decided both
when a hostile NOTICES the player and when it can REACH them. A Hatcher rooted to
its spawn point therefore swung at anything within 1200 units — it hit people
across a courtyard it never crossed, and §11's own run is an example: the agent
stood 300 units away for three death cycles and never moved. Reach is now
`ENEMY_MELEE_RANGE` (150) and `AGGRO_RANGE` is the notice and the leash. The walk
is what makes that separation survivable rather than a way of making combat
impossible.

**Two clocks have to agree.** The client is told a DESTINATION and animates its own
way there; the server advances `agent["pos"]` at the same rate, because that is
what every range check reads. The destination is re-announced only when the player
has moved `ENEMY_DEST_RESEND` (120) units, because a tick-rate destination stream
is 20 messages a second at a client that needs one endpoint.

**Stopping is an ARRIVAL, not a zero rate** — `agent_update_speed` refuses anything
below `AGENT_MIN_MOVE_SPEED` (0.01, the client's own assert at `AgAgent.cpp:2366`),
so "speed 0" is not available to say this with, and on the world tick that refusal
would be a `ValueError` the tick has to swallow.

### What is still not there

- **No pathfinding.** `pathmap.route` is an A* and is NOT wired in. This walks a
  straight line and uses `pathmap.clip` to stop at the first thing it cannot cross,
  so an agent meets a wall and waits rather than sliding through it. A hostile on
  the far side of a building will stand against that wall for as long as you stay
  where you are.
- **No leash home.** Walk out past `AGGRO_RANGE` and it stops where it stands; it
  does not return to its spawn anchor.
- **It does not face you.** `agent_update_speed` carries a `facing` field and this
  passes the default.
- **`ENEMY_MELEE_RANGE`, `ENEMY_MOVE_RATE` and `ENEMY_DEST_RESEND` are ours.**
  Nothing measured them, and the wiki's aggro-bubble numbers describe a mechanic
  (a moving circle, a leash, a call-to-arms radius) that none of this implements.

### 11.3 It faces you — on an angle nobody here invented

**OBSERVED 2026-08-11**, capture `authsrv-20260811T175949-c1.jsonl`:

```
2e00 0a000000 db0f4940 920a0640
  |      |        |        `-- 0x40060a92 = 2.0943951 = 2*pi/3 rad/s
  |      |        `----------- 0x40490fdb = 3.14159274 = pi, due west
  |      `-------------------- agent 10
  `--------------------------- GAME_SMSG_AGENT_UPDATE_ROTATION
```

The agent stands due EAST of the player and is told to look due WEST. On film it
is turned toward the player mid-swing instead of showing its back.

**`0x002E` had been defined, documented and never sent** — it sat in `authsrv.py`
for days with a comment describing exactly what it carries. This rung needed no
new discovery at all, because everything about how to fill it was already measured
off ArenaNet's own traffic by work that was not trying to solve this problem:

| what | where it came from |
|---|---|
| `atan2(y, x)` | `test_rotate.py` scores the client's OWN `0x0040` sends against `atan2` of a nearby `0x003D` **direction** vector, beating a null model from the same corpus |
| absolute, in ±π, ±inf as free-spin sentinels | `test_smsgnames.py`, every finite live sample in range |
| turn rate is per-CREATURE and quantised, max `2π/3` to the bit | `test_smsgnames.py` |
| both fields are `dword` holding **float32** | the ROTATE_PLAYER trap; reading them raw made an early `test_smsgnames` compare garbage to π |

`test_rotate.py`'s first version paired against `0x003D`'s POSITION vec2 instead of
its DIRECTION vec2 and scored 0 of 163 — a position has a perfectly plausible
`atan2` too, which is why that failure was silent. The check here that separates
`atan2(y, x)` from `atan2(x, y)` is a player due NORTH reading `+π/2`; the due-west
case cannot tell them apart, since both give ±π.

**What is NOT depended on: which sign is a left turn.** `test_rotate.py` refuses to
pin that on 121/189 and 106/169, which is real and far too weak to write down. An
absolute facing needs no such claim.

**Three defects found in this rung's own first draft, all by sabotage:**

1. **The facing was nested under the destination re-announce**, so it could not
   change until the player had moved 120 units. The 0.15 rad epsilon was
   decorative and an agent tracking a player circling it at constant distance
   never turned. It is called every chasing tick now, gated by the epsilon.
2. **`force=True` on every swing bypassed that epsilon** — 15 of the 16 rotations
   in the first live run were byte-identical to the one before. Dropped: in melee
   the swing is the ONLY call site, so the epsilon is also what tracks a player
   walking around the agent, at one message instead of one per swing. 16 → 1.
3. **Two of the new checks could not fail.** The seam-wrap case moved the player a
   hair NORTH, which does not cross ±π, so both the wrapped and unwrapped versions
   were silent; and the zero-distance guard was tested through `enemy_move_tick`,
   which returns before facing is considered when the agent is inside melee range.
   Fixed by moving south and by calling `face_player` directly.

**A float32 detail worth keeping.** Due west is exactly `+π`, and
`float32(π) = 3.14159274` is GREATER than `math.pi = 3.14159265` by 9e-8 — so the
obvious `-math.pi <= a <= math.pi` bound marks a legitimate facing out of range.
`test_smsgnames`' version of that check is over live samples, none of which land on
the seam, so it never had to notice.

### Still not there

- **It does not turn while dead**, and nothing resets `facing_told` on revive.
- **The turn rate is one constant for every creature.** ArenaNet's is per-creature;
  we send its maximum to everything.
- **`ENEMY_FACING_EPSILON` is ours.** The rest of the numbers are ArenaNet's.

### 11.4 It fights back with a SKILL — and the corpus refused the obvious answer

**OBSERVED 2026-08-11**, capture `authsrv-20260811T181457-c1.jsonl`:

```
t=3.70  agent 10 casts skill 276      0x009F [60, 10, 276]
t=4.46  skill 276 deals 25            0x00A3 [16, player, 10, -0.25]
t=5.07  attack_started                the ordinary swing, between casts
```

0.76 s from cast to landing against ArenaNet's declared 0.75 activation. Six casts,
six swings, two kills. **The client renders the cast**: a skill glyph appears above
the Hatcher's health bar for the activation window, so `0x009F` value 60 from an
NPC drives the client's casting UI and not merely our own bookkeeping.

**THE OBVIOUS ANSWER WAS WRONG AND THE CORPUS SAID SO BEFORE ANY CODE WAS WRITTEN.**
This server already had a skill message — `GAME_SMSG 0x00E3`, which it sends when
the PLAYER casts — and reusing it for an NPC is the move a reader of `authsrv.py`
would make. **All 6 of the `0x00E3` in the entire live corpus name the player**
(agent 31, skills 153/105/394). `0x00E3` confirms a cast the CLIENT initiated; the
client logs `Pending skill %u copy %d not found` when the echo is wrong, and an
NPC's cast has nothing to confirm. A check in `test_agentlife` now fails if anyone
routes an NPC cast through it.

**What the corpus does carry is one NPC skill activation:**

```
0x009F [value 60 = GV_SKILL_ACTIVATED, agent 36, skill 83]
```

**n=1**, in `20260810T235916` connection `:62994`. That is thin and is written
down as thin. It is still the only evidence there is, and it beat inventing a
message — which the live run then confirmed by rendering.

**A near miss, recorded so nobody re-finds it.** A census of `0x00A0` keyed on slot
2 makes value 20 (`GV_EFFECT_ON_TARGET`) look NPC-exclusive — 5 NPC, 0 player. It
is not an NPC casting. In context the PLAYER casts skill 153, and value 20 then
arrives with the player's TARGET in that slot: `[20, 40, 31, 276]` while the player
damages agent 40. **Different value ids put different roles in the same slot**,
which is exactly what `hit_enemy`'s own comment warns about, and a census keyed on
a slot rather than on a role will keep reproducing this.

**The skill and its timings are ArenaNet's**, out of the client's own table via
`skilltable.py`. Skill 276 is chosen because its profession (3) matches the one
this server already declares for the Hatcher at spawn — not picked from nowhere.
`activation=0.75` and `recharge=2.0` are the table's, which is why they are odd
numbers. Only `ENEMY_SKILL_FRACTION` (0.25 of the player's maximum) is ours: the
client carries every real number and we do not read it yet.

**Not the player's cast path.** The skill-dispatch arm carries a standing note that
skill COMPLETION is being built on another branch and not to add to it. None of
this touches it — an NPC announcing its own cast is a different message on a
different channel.

### Still missing

- **One skill, one creature, no bar.** Real hostiles have skill bars; this is a
  single id on a recharge. `content/world.toml` can override it (`skill = 0` turns
  it off) but there is no bar and no selection.
- **No energy, no interrupt, no aftercast.** The table carries `energy`,
  `aftercast` and `adrenaline` for every skill and none of them are read.
- **The effect is damage and nothing else.** Skill 276's real effect is not
  modelled; it deals a flat fraction like a harder swing.

### 11.5 A bar, not a skill — and one slot on it was unreachable (FIXED, 11.6)

**OBSERVED 2026-08-11**, capture `authsrv-20260811T182359-c1.jsonl`:

```
t=4.15  casts 276    t=4.91  deals 25     activation 0.76 vs table 0.75
t=4.96  casts 253    t=5.97  deals 25     activation 1.01 vs table 1.00
t=6.02  casts 312    t=6.78  deals 25     activation 0.76 vs table 0.75
t=6.83  casts 276    ...
```

Four skills, each with its own recharge, selected **first-ready-in-bar-order**.
Three activations measured against three different table values, all within 10 ms.

**AND SLOT 4 NEVER FIRED.** Counts for the run were `{276: 6, 253: 3, 312: 3, 289: 0}`.
This is not a defect in the selector — it is what a strict priority list does when
slot 1 recharges faster than the bar takes to walk. 276 comes back every 2.0 s,
and reaching slot 4 needs 2.0 + 5.0 + 8.0 seconds of everything above it being
busy, which never happens. **A four-slot bar is really a three-slot bar here**, and
the fourth is dead weight until selection changes.

Recorded rather than quietly reordered, because reordering to make the number look
better would have hidden the property. **Fixed in §11.6 with round robin**, on the
owner's call; the paragraph above is kept as the measurement that motivated it.

**The test proves the selector, not the schedule.** `section_enemy_skill` rolls
each slot's recharge forward by hand and requires the picks to be `[0, 1, 2, 3]`,
so it catches a selector that always returns slot 1 or scans backwards. It cannot
catch the reachability problem above, and the two facts are different: the
selector walks the whole bar; the live schedule does not reach the end of it.

**WHOSE BAR THIS IS: ours.** `studies/presearing/MANIFEST.md` §7 read three
Pre-Searing creature pages in full and found **no base skill bar on any of them** —
the Restless Corpse's is explicitly "None", the region's only non-Charr boss has no
`==Skills==` section, and the Grawl bar an earlier pass relied on turned out to be
**invented**. Our Hatcher is a Lakeside creature, so this bar is a fixture that
exercises the mechanism and **not a claim about what a Hatcher does in retail**.
A content row is where a sourced bar goes the day there is one.

**What IS ArenaNet's:** every id, activation and recharge, out of the client's own
table via `skilltable.py` on build 38797. All four are profession 3 — the
profession this server already declares for the Hatcher at spawn — campaign 1,
non-elite, and each has a different `type_code`. **What is ours:** which four of
the 21 that qualify, the priority order, and the flat 0.25 damage. Per-skill
effects are not modelled; giving each slot its own number would be four
inventions instead of one.

**Recharge is per SLOT, not per id** — a bar may carry the same skill twice, and
keying by id would make the second copy share the first's cooldown and the bar
quietly one shorter. Pinned by a check.


### 11.6 Round robin, and every slot fires

**OBSERVED 2026-08-11**, capture `authsrv-20260811T183716-c1.jsonl`. Owner's call.

```
t=3.30  casts 276      casts by skill: {276: 3, 253: 3, 312: 3, 289: 3}
t=4.11  casts 253
t=5.17  casts 312
t=5.98  casts 289      <- the slot that never fired before
t=16.76 casts 276      (the 10.8 s gap is the player's death and 10.0 s revive,
t=17.57 casts 253       not a selection stall -- nothing casts at a corpse)
```

**Three of each, exactly even**, against `{276: 6, 253: 3, 312: 3, 289: 0}` before.

The change is one line and no new numbers: the scan starts **after the last slot
cast** instead of at slot 1, and wraps. Every ready slot gets a turn before any
slot gets a second one. `last_slot` is written by the cast site rather than by
`pick_skill`, so the selector stays a pure read and a test can drive the cursor.

**STILL NOT MEASURED, and this does not change it:** nothing in this project knows
how a Guild Wars monster actually chooses. Round robin, least-recently-used and
priority order are all inventions. This is the invention that reaches every slot,
which was the property actually wanted.

**Three checks, because the first two did not cover the wrap.** The existing suite
passed the round-robin change unchanged — 122 green before and after — which
means nothing in it could tell the two selectors apart. Added:

1. every slot ready, cursor advanced by hand → picks must be `[0,1,2,3,0]`;
   first-ready gives `[0,0,0,0,0]` and goes red.
2. **the wrap specifically**: cursor at the end of the bar, only slot 1 ready →
   must return 0. A sweep that stops at the end returns `None` and the agent
   swings instead of casting a skill that is up. This one is the reason to write
   it out: the modulo on `start` alone satisfies check 1, so check 1 passes
   against a selector with no wrap at all.
3. **the defect as a regression**: the real bar driven against a simulated clock,
   requiring every slot to be used.

### 11.7 Two corrections from the owner, and one of them is about method

**OWNER'S OBSERVATION 2026-08-11: the agent faced AWAY from the player.** §11.3
claimed "on film it is turned toward the player mid-swing instead of showing its
back". That was me reading a 1 fps JPEG and finding what I expected; the owner was
at the machine. **The wire cannot tell a facing from its opposite** — every angle
in the capture is inside ±π, the rate is ArenaNet's, the value round-trips, and
all of it is equally true of a body pointing the wrong way. A person looking at
the screen is the only instrument for this, and I substituted my own frame-reading
for it and reported the result as confirmation.

**The fix is `+ π`, and the `+ π` is measured rather than derived.**
`atan2(dy, dx)` is the bearing from the agent to the player and it is correct by
every derivation available — `test_rotate.py` scores the client's own `0x0040`
sends against exactly that and beats a null model. Sending it turns the agent
around. So **the client's `0x002E` facing is not the same convention as the
heading it reports in `0x003D`**, and *why* is not established: it could be the
zero direction, the sign, or the model's own forward axis. The offset is what is
established, from the one observation that could refute it.

This is §10's lesson for the fourth time, from a new angle: **a derivation tells
you what the client TESTS and never what the answer looks like on screen.**
`test_rotate`'s scoring, `test_smsgnames`' range, the float32 seam, the byte
layout — all correct, all consistent with a backwards agent.

**OWNER'S RULING: casting AI is not being decided here.** §11.4–11.6 built a bar
and then a selection policy for it, and the policy is invented — round robin
reaches every slot, which was the property wanted, but nothing measured it and
nothing should read it as a claim. **A deeper dive into monster AI comes first.**
Until then the bar is a TESTING FIXTURE whose job is to exercise the mechanism —
the message shape, the per-slot recharge, the activation window, the reachability
of every slot — so the parts that *are* evidenced can be tested. `pick_skill` and
the bar constants now say this at the call site. When the AI study lands, the
policy gets replaced rather than extended.

**What in §11.4–11.6 survives that ruling**, because it is measurement rather
than invention:

- `0x00E3` is the player's cast confirmation and NOT how an NPC's cast is
  announced — 6 of 6 in the corpus, and the client's own "Pending skill not
  found" log explains why.
- `0x009F` value 60 with `[agent, skill]` is what the corpus carries for an NPC
  cast (n=1), and the client renders a cast glyph for it.
- Activation times are ArenaNet's and the client honours them: 0.76 / 1.01 / 0.76
  measured against table values 0.75 / 1.00 / 0.75.
- Recharge must be per SLOT, not per skill id.
- `0x00A0` value 20 is not an NPC casting; slot 2 there is the target.
