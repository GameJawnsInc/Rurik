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
