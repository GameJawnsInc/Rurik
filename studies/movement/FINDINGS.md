# What we actually know about movement

Six reading tracks over OpenTyria and six other prior-art mirrors, each then
adversarially re-verified. This document records only what survived verification,
and labels everything.

## Labels used throughout

| Label | Meaning |
|---|---|
| **OBSERVED** | We saw it ourselves, against the real client, in our own logs. |
| **UPSTREAM** | OpenTyria's code says this, and a verifier confirmed the line. OpenTyria is a reconstruction; this is not a fact about ArenaNet's server. |
| **RECONSTRUCTION** | OpenTyria itself signals it is guessing — offset-named field, placeholder magic, commented-out call, or the author saying so. |
| **UNVERIFIED** | A track claimed it and the verifier could not confirm it, or refuted it. Do not build on this. |
| **NOT FOUND** | We looked and there is no answer in the sources we have. |

The most important consequence of that table: **no claim below is a sourced fact
about retail Guild Wars.** The only ground truth we possess is our own client
behaviour. Everything else is somebody else's reconstruction, and the whole
value of this pass is knowing which is which.

---

## The answer in one page

**The server does not stream positions. It sends a destination once and lets the
client animate the walk.** This is the load-bearing finding of the pass, it was
independently confirmed by two verifiers reading the code themselves, and it is
what our current interpolator gets structurally right by accident.

In OpenTyria, one world tick does exactly this (`GmAgent.c:430-459`, read and
confirmed):

1. Broadcast one message, `GAME_SMSG_WORLD_SIMULATION_TICK` (0x001E), whose
   entire payload is a `uint32 delta_ms` (`GameMsg.h:520-523`).
2. Integrate every live, moving agent's position server-side, silently
   (`GmAgent.c:392-428`). No packet is emitted for the integration.
3. Regenerate health/energy.

Per-agent position messages are *events*, not a stream:

| Opcode | Name | When it is sent |
|---|---|---|
| 0x0029 | `AGENT_MOVE_TO_POINT` | Once per movement leg — on a client move order, **and from inside the tick** when a pathfound agent crosses an intermediate waypoint (`GmAgent.c:405-407` then `:359`). |
| 0x002C | `AGENT_UPDATE_POSITION` | Twice in the whole codebase, both snap-backs: pathfinding failure (`GmAgent.c:386`) and the `/stuck` command (`GmChat.c:152`). |
| 0x0028 | `AGENT_STOP_MOVING` | Once, on explicit client cancel (`GmAgent.c:471`). Natural arrival sends nothing at all. |

Three things corroborate the "client animates" reading. The tick is capped at
**500 ms** (`GameSrv.c:5`, gated at `:1955-1957`) — far too coarse to be a
position stream. `MOVE_TO_POINT` carries no speed and no duration
(`GameMsg.h:538-544`), so the client must already know both. And the *client*
volunteers its own final position back on cancel, opcode 0x0047, which the
server then accepts verbatim if it is within tolerance (`GmAgent.c:475-491`) —
a server that owned the walk would have no use for that message.

What this means for us, concretely: our 20 Hz tick is not wrong, but it is not
doing the thing the comment in `authsrv.py:132-139` thinks it is. The answer
that comment asks for — "probably `AGENT_UPDATE_DESTINATION` rather than
`MOVE_TO_POINT`" — is **no**: `MOVE_TO_POINT` is the correct message and
`AGENT_UPDATE_DESTINATION` (0x002A) is never sent by upstream at all. The real
gap is that upstream broadcasts `WORLD_SIMULATION_TICK` every tick and we never
send it once.

Second most important, and unwelcome: **we have no pathfinding and no
collision, and neither does our reference for the map we are actually in.** See
the pathfinding section — the data is on our disk, but the map id we need is not
in any table we have.

---

## The upstream movement model

Everything in this section is what OpenTyria's code does, verified line for
line. Read every "UPSTREAM" as "OpenTyria's engineering choice, provenance
unknown".

### Tick

| Element | Value | Where | Label |
|---|---|---|---|
| Outer loop | `while (!srv->quit_signaled) { GameSrv_Update(srv); }`, no sleep | `GameSrv.c:2057-2059` | UPSTREAM |
| Idle throttle | a single 16 ms blocking IOCP wait per update | `GameSrv.c:1910` | UPSTREAM |
| World tick | **not** fixed-Hz — a *maximum interval* of 500 ms | `GameSrv.c:5`, `:1955-1957` | UPSTREAM |
| Timestep | variable; `delta_ms` from a monotonic ms clock, converted to seconds for the math | `GmAgent.c:437-438` | UPSTREAM |
| On-demand ticks | the tick also fires synchronously from four handlers *before* they mutate state | `GmAgent.c:348, :384, :469`; `GmChat.c:150` | UPSTREAM |
| Per-tick broadcast | `WORLD_SIMULATION_TICK` (0x001E), payload = `uint32 delta_ms` | `opcodes.h:166`, `GmAgent.c:261-268` | UPSTREAM |

Nothing anywhere cites a source for the 500 ms cap or the 16 ms poll. Treat
both as invented numbers that happen to work.

**Load-bearing ordering detail.** `GameSrv_WorldTick` advances
`srv->last_world_tick` *before* the agent loop (`GmAgent.c:441` vs the loop at
`:444`). This is not stylistic: `UpdateAgentDestination` calls `WorldTick` as
its own first statement (`GmAgent.c:348`, verified), and the tick reaches
`UpdateAgentDestination` via waypoint advance. Advancing the timestamp after
the loop instead would give infinite recursion; the guard at `GmAgent.c:433`
only short-circuits because line 441 already ran.

### Agent fields

The complete movement state of a `GmAgent` (`GmAgent.h:14-37`):

    GmPos position;          // :17   x, y, plane
    Vec2f direction;         // :18   unit vector
    GmPos destination;       // :19   ONE point - the current leg, not the route
    float rotation;          // :20   radians, computed, never read
    float speed_base;        // :30
    float speed;             // :31   0 or speed_base, nothing else
    size_t waypoint_idx;     // :35   cursor into the route
    WaypointArray waypoints; // :36

`GmPos` is `{float x; float y; uint16_t plane;}` (`GmDefs.h:15-24`). Plane is
per-*point*, not per-agent. Ten bytes on the wire; twelve in memory, because
`GmDefs.h` is outside any `#pragma pack` region — a real porting trap.

There is **no boolean "moving" flag**. `speed == 0.f` is the entire test
(`GmAgent.c:394`).

### Destination handling

- A destination is one point. The route is a separate pathfinder-produced
  waypoint array walked by an index; the client never receives the array, only
  the current leg (`GmAgent.c:377-381`, `:405-407`). UPSTREAM.
- On leg completion the whole `GmPos` is copied (`GmAgent.c:404`), which is the
  *only* way plane ever changes during movement. There is no plane-transition
  logic. UPSTREAM.
- On arrival: destination zeroed, speed zeroed, waypoints cleared, and **no
  packet sent** (`GmAgent.c:420-427`). UPSTREAM.
- **Defect — do not copy.** `UpdateAgentDestination` divides by the vector norm
  with no zero guard (`GmAgent.c:352-356`). A destination equal to the current
  position yields NaN direction and NaN rotation, and it is reachable: the
  pathfinder pushes `dst_pos` unchanged when source and destination share a
  trapezoid (`GmPaths.c:957-962`), so a client clicking its own feet triggers it.

### Speed

| Element | Value | Where | Label |
|---|---|---|---|
| Player base speed | `288.f` | `GameSrv.c:1002` | RECONSTRUCTION — uncommented magic literal, no unit, no citation |
| Unit | world units per **second** | `GmAgent.c:437-438` (ms to s) then `:398` (`dist = delta * speed`) | UPSTREAM |
| Modifiers | none exist | `speed` is only ever assigned `0.f` or `speed_base`; repo-wide grep confirms | UPSTREAM |
| Wire delivery | once, in the `speed_base` field of `CREATE_AGENT` | `GmAgent.c:149`, `GameMsg.h:397` | UPSTREAM |
| `AGENT_UPDATE_SPEED_BASE` (0x0027) / `AGENT_UPDATE_SPEED` (0x002B) | defined, never sent | `opcodes.h:172, :176` | UPSTREAM |

288.0 is corroborated by a second lineage — GWCA comments
`float speed; // default 288.0` on the same field position
(`GregLando113__GWCA/Include/GWCA/Packets/StoC.h:135`). Two references agree;
neither cites a measurement. That is better than one source and it is still not
a fact.

Non-player agents cannot move in OpenTyria, because there are none:
`GameSrv_CreateAgent` has exactly one caller in the whole tree
(`GameSrv.c:996`, inside `GameSrv_CreatePlayerAgent`, itself called only from
`GameSrv.c:1236`).

### Heading / rotation encoding

**This is not settled, and the reference cannot settle it.**

- `agent->rotation` is computed once as `atan2f(direction.y, direction.x)`
  (`GmAgent.c:357`, verified) and is then never read by any code anywhere.
- The rotation broadcast is a **commented-out call to a function that does not
  exist**: `GmAgent.c:360` is `// GameSrv_BroadcastAgentRotation(srv, agent);`
  and there is no definition or declaration of that symbol in the tree.
  RECONSTRUCTION, and the clearest such signal in the movement code.
- There is no dispatch handler for `GAME_CMSG_ROTATE_PLAYER` (0x0040); the
  constant appears once, at `opcodes.h:87`, and nowhere else.
- The `AGENT_UPDATE_ROTATION` (0x002E) struct **does** name its payload:
  `GameMsg.h:546-551` declares `uint32_t sin; uint32_t cos;` — sin first. But
  the message is never populated, and the wire format table types both fields
  `DWORD`, not `FLOAT` (`msgdefs.c`, `GAME_SMSG_0046`), even though `TYPE_FLOAT`
  exists and is used elsewhere in the same table. So even the numeric
  representation is unconfirmed. UNVERIFIED.
- The only heading the client actually receives from this server is the
  `Vec2f direction` unit vector inside `CREATE_AGENT` — two little-endian
  floats, unpacked (`GmAgent.c:147`, `msgpack.c:269-280`).
  `AGENT_UPDATE_DIRECTION` (0x0025) is never sent.

Corroboration from other lineages that it is float data: GWLP-R annotates both
fields of its rotate packet with "This is actually a float value."
(`P057_RotateAgent.java:15-26`), and GWCA's in-memory agent struct carries
`rotation_angle` / `rotation_cos` / `rotation_sin` at adjacent offsets
(`Agent.h:104-106`) — but that is the entity layout, not the packet, and it
lists cos before sin. The sin-then-cos wire ordering is single-source.

### The message we most need, and how much of it is understood

`WORLD_CREATE_AGENT` (0x0020) is 23 fields after the header, 97 payload bytes,
99 = 0x63 total (`msgdefs.c:1917-1942`, re-verified against the wire sizes in
`msgpack.c:30-84`). Of its fields, **15 of 24 are named only by their byte
offset** — 62%, the worst ratio of any struct in the repo (`GameMsg.h:387-412`).

Seven of those fifteen get an assigned value; eight are never assigned at all
and ride whatever the shared message buffer's memset left there
(`GmAgent.c:144-157`, `GameSrv.c:140-145`). The assigned ones are placeholders
in the plainest sense:

- `h0027 = 0x41400000` — the IEEE-754 bit pattern for `12.0f`, written into a
  field declared `uint32_t`. Bytes known, meaning not.
- `h004B` and `h0059` are both `(+INF, +INF)` — a sentinel.
- `h000B = 5`, `h001E = 1`, `h0023 = 1.f`, `h003B = 0`.

The meaningfully-named movement fields on this message are exactly four:
`position`, `plane`, `direction`, `speed_base`. There is no destination and no
waypoint data on it.

---

## Pathfinding, collision, terrain

**Read this first: collision is *not* gated on map geometry we do not possess.**
Two full retail `Gw.dat` archives are on our disk right now —
`C:\gd\Rurik\vault\client\2026-04-30_b174de1f2d8d\Gw.dat` (4,196,497,128 bytes)
and `C:\gd\Rurik\vault\client\2026-07-29_221c13772c7a\Gw.dat` (4,198,489,600
bytes), the second matching our patched client. The gate is the reader, not the
bytes.

**Read this second: it is gated on a map id we do not have.** OpenTyria
hardcodes six maps (`GmMapsConfig.c:3-35`) and only Kamadan has a spawn point.
Ascalon City Pre-Searing — map 148, where our character actually stands — is not
among them, so we do not have its `map_file_id` and would have to recover it
from the archive ourselves. This is already recorded honestly in
`authsrv.py:180-194`.

### The representation

OpenTyria's navigation is a **2D trapezoidal decomposition**: vertical-slab
trapezoids with horizontal top and bottom edges, four neighbour pointers, two
portal ids (`GmPaths.h:5-19`, read directly). Not a navmesh of triangles, not a
grid, not a waypoint graph — waypoints are the *output* of a query, not the
stored form.

Point location uses the classic trapezoid-map search DAG: XNode (side of a
directed segment), YNode (above/below a horizontal), SinkNode (leaf holding a
trapezoid), walked from a per-plane root (`GmPaths.h:23-60`, `GmPaths.c:11-52`).

The search is A* over trapezoids with a binary min-heap, cost = accumulated
crossing-point distance, heuristic = distance to the nearest point on the
neighbour's top/bottom edge, capped at `MAX_COST = 10000`, and the resulting
corridor is funnel-smoothed into the waypoint list (`GmPaths.c:944-1057`,
`GmPathHeap.c:3-61`). The comment calling 10000 "the ingame constant"
(`GmPaths.c:946`) cites nothing. RECONSTRUCTION.

### Where the geometry comes from

`Gw.dat`, read at server start with a hardcoded relative path
(`GameSrv.c:103-106`, verified verbatim), through a real MFT reader and Huffman
decompressor (`FaArchive.c`, `FaCompress.c` — 508 lines, a real implementation).
The map file is an "ffna" RIFF container and **only the Path chunk is
imported** (`GmMapDataImport.c:563-571`); the MapParameters import is commented
out.

Archive magic, corrected — the first track misquoted this and it is the one
byte-level constant an implementer would copy. `FaArchive.h:3` reads
`#define FILE_ARCHIVE_MAGIC ((uint32_t)'\x1ANA3')`, i.e. the bytes
`0x1A 'N' 'A' '3'`. Not `AN\x1A3`.

The path chunk validates signature `0xEEFE704C`, version 12
(`GmMapDataImport.c:5-7, :97-113`). Trapezoid records are 44 bytes (11 x uint32)
with an exact-size hard check (`GmMapDataImport.c:209-235`).

**Do not record that layout as empirically validated.** The first track argued
the exact-size checks were "strong evidence this was verified against real
Gw.dat bytes"; the verifier refuted that inference. There is no test, no
fixture, and no capture in the repo showing this parser has ever been run
against an archive. Given `h000C`, the blind-skipped blocks, and the uncited
fast-math tables, transcription from a disassembly of the client's own parser is
at least as likely. RECONSTRUCTION we must re-derive ourselves.

Two parts of the chunk are skipped blind, with the tag byte never even read
(`GmMapDataImport.c:115-130`, `:180-191`). Both consume a fixed length while
only asserting an upper bound — if either block is longer than assumed, the
whole per-plane parse desyncs silently.

### Collision

**There is no wall-collision routine anywhere in OpenTyria.** Walkability is
enforced only at path-request time: `PathFinding` returns false if either
endpoint resolves to no trapezoid (`GmPaths.c:952-955`), and the move is then
cancelled and the position re-broadcast (`GmAgent.c:382-387`). The per-tick
integrator performs no containment test whatsoever (`GmAgent.c:392-428`) — it is
structurally the same unchecked straight-line step we already wrote.

The only "blocking" concept is a static portal flag (`flags & 0x4`). The
dynamic hook is commented out at `GmPaths.c:442` and `:497`, and
`IsPlaneBlocked` is defined nowhere. The two commented lines are not even
identical: `:497` references `portal->next_plane_id`, a field that does not
exist in `struct Portal` — that line could never have compiled. Long-dead code.

Client position corrections are accepted with **no walkability check at all** —
only a same-plane test and a distance cap (`GmAgent.c:475-491`). A client can
place itself 99 units inside a wall.

### Terrain and height

**There is no Z coordinate anywhere.** `GmPos` is 2D + plane. No wire message
carries a height. `Vec3f` exists but is used only by the generic message packer.
No height, altitude, or terrain-lookup function exists in the tree.

The `Terrain` (2) and `Collision` (14) chunks are enumerated in the chunk-id
enum and **never read by any code path** (`GmMapDataImport.h:6, :18`). If we
ever want terrain height or static prop collision, this reference gives us
nothing at all.

That the client derives ground height locally from its own map data is a
reasonable inference and is *not* sourced.

### What a "plane" is

**NOT FOUND.** Two independent greps confirmed it: nothing in OpenTyria defines
what a plane means physically — vertical layer, bridge deck, overlapping
surface. Not one comment. Mechanically it is a `uint16` index into
`PathStaticData.planes` assigned by import order, each plane an independent 2D
decomposition with its own search root, joined to other planes only by paired
portals within the same map file. Any physical reading is our inference.

---

## How far to trust OpenTyria

The single most useful thing the provenance audit found is that OpenTyria is
**two projects with very different trust profiles**.

**The wire-format layer is machine-extracted from the client binary.**
`code/msgdefs.info` is `msgdefs.c` plus 526 `// Handler Rva: XXXXXXXX`
annotations — real client RVAs. Verified: stripping the RVA lines from
`msgdefs.info` yields a file byte-identical to `msgdefs.c`. The extraction
method is live-process instrumentation — byte-signature scanning into `Gw.exe`'s
`.text` section to hook its own send/recv routines (`tools/trace-packets.py:28-30`,
`tools/process.py:444`). This layer is the mirror's most valuable asset and the
best-evidenced thing in it.

**The server-semantics layer is a one-person, ~19-month hobby reconstruction.**
180 commits, sole author, 2024-07-16 to 2026-02-21, 78 distinct commit days, 53
of 180 commit messages containing "fix". The only test file tests integer and
IP-address parsing.

### Coverage is the real gap, not comment smell

| Direction | Formats extracted | Given a semantic name | Actually dispatched / sent |
|---|---|---|---|
| AUTH_CMSG | 57 | 19 | 13 |
| AUTH_SMSG | 39 | 13 | 9 |
| GAME_CMSG | 194 | 101 | **16** |
| GAME_SMSG | 487 | 239 | 76 |
| **Total** | **777** | **372 (48%)** | — |

29 of 251 client opcodes are handled. That figure was reproduced exactly by the
verifier.

Reverse-engineering fingerprints are sparse in absolute terms — 7 TODO-class
markers in the whole repo, no FIXME/HACK/XXX at all, exactly one debug-fill
constant in a protocol field (`0xBAADF00D` at `GameSrv.c:1233`) — but they are
**concentrated in exactly the structs we need**, and `CREATE_AGENT` is the worst
one in the repo.

### Corrected numbers

The provenance track's aggregate statistics did not survive verification and are
corrected here. Its *line-level* citations were reliable; its greps were not.

| Statistic | Track claimed | Verified |
|---|---|---|
| Offset-named struct fields (declarations) | 70 of 956 (7.3%) | **39** — GameMsg.h 21, AuthMsg.h 6, proto.h 5, FaArchive.h 4, GmChar.h 2, GmPaths.h 1. The 70 counted *use sites* in .c files. |
| `CREATE_AGENT` offset-named | 15 of 24 (62%) | **confirmed** |
| Hardcoded auth settings blob | ~470 bytes | **591 bytes** (`AuthSrv.c:548`) |
| `abort()` call sites | 38 | **34** |

### Per-subsystem trust

| Subsystem | Trust | Evidence |
|---|---|---|
| Wire formats / opcode tables | **High** | 526 client RVAs; extraction tooling in-repo. The one genuinely well-evidenced layer. |
| Auth / crypto | **High** | Real DH via mbedtls, ARC4 ciphers, documented key handoff (`AuthSrv.c:169, :1138-1140, :1190`). **Caveat:** `tools/patch-gw.py:55-62` *rewrites* the client's DH key accessor. The author did not recover ArenaNet's keys; he substituted his own. "Fully understood" is not "a stock client completes this handshake." |
| Pathfinding geometry | **Medium — downgraded** | Structurally sophisticated and internally consistent. But the claim that its fast-math lookup tables are "lifted from the binary, bit-for-bit" is **UNVERIFIED** — no attributing comment exists anywhere in `GmPaths.c`. The track conceded this in its own gaps list and then published it as certain. That is the exact failure mode we are guarding against. Demote to: reconstruction, strongly suggestive form, unverified origin. |
| Map data parsing | **Medium** | Real archive + decompressor + chunk parser. But six configured maps, one spawn point, two blind-skipped blocks, and no evidence the parser was ever run. |
| Character / inventory | **Medium** | Real SQLite schema; one genuinely subtle documented finding (the settings blob leaks the *client's* uninitialised heap fill, `GmChar.h:121`). |
| Movement / tick | **Medium** | The architecture is clear and verified. Every *number* in it (500 ms, 16 ms, 100.f, 288.f) is the author's own choice. |
| Chat | **Low** | 4 of 7 channel prefixes do anything, one command, and message fragmentation is outright broken at both sites — the loop builds a fragment and then sends the unfragmented message (`GmChat.c:44-49`, `:59-64`). |
| Combat | **Absent** | No damage, no attack, no casting, no death. `GmAgent.c:452-457` is the entire health model, ending in `// @TODO: Check if the agent is dead!!!`. |
| NPCs / AI | **Absent** | One agent-creation path, the player's own. |

### The author's own calibration

`GmAgent.c:3`, immediately above `#define MAXIMUM_ALLOWED_CORRECTION 100.f`:

> `// This is way too nice, but we are not implemented a real server anyway...`

This is the provenance-defining line of the entire movement track. The author is
telling us in his own words that this number is invented. He is honest where he
knows he is uncertain — `msg3->idk = 0x2211; // what is that?`
(`GameSrv.c:1793`), five `@Cleanup` comments flagging known-wrong lifecycle
behaviour. **The danger is the places where he silently hardcoded a value with
no comment at all** — 288.f, 500 ms, `MAX_COST = 10000`, the fast-math tables.

---

## Where independent sources agree and disagree

Seven mirrors were checked. **They are not seven sources.** The verifier
established that at least four are derived:

| Lineage | Members | Basis |
|---|---|---|
| **ldufr** | OpenTyria, Headquarter, gw-preservation/network-log-explorer | Headquarter shares OpenTyria's author and its opcode table differs on **2 of ~800** defines. network-log-explorer's tables match OpenTyria 237/238 StoC names and 101/101 CtoS names, and on the two opcodes where it differs from OpenTyria it matches *Headquarter* exactly. |
| **GWCA** | GregLando113/GWCA, JaborGW/GWCA | One repo forked from the other; `AgentAdd` is byte-identical at the same lines in both. |
| **GWLP-R** | GameRevision/GWLP-R, th0br0/sgwlpr | sgwlpr's packet templates carry `<Author>GWLPR Template Updater</Author>` on every relevant packet. |
| **Py4GW** | apoguita/Py4GW (+ Reforged fork) | Not checked by the track at all. It is the catalog our own `authsrv.py:217-219` already cites as authoritative for CtoS numbering. |

**This corrects the track's headline.** It claimed network-log-explorer was "the
closest thing to primary packet-capture evidence" and independent of OpenTyria.
It is neither: it contains no capture data, only decoder tables, and those
tables are ldufr's. So "the three sources closest to our build agree" is really
"ldufr's table agrees with itself."

Real independent agreement on the movement cluster comes down to **three
lineages** — ldufr, GWCA, GWLP-R — plus Py4GW on naming.

### The cross-check

| Fact | ldufr | GWCA | GWLP-R | Py4GW | Rurik's own logs |
|---|---|---|---|---|---|
| 0x0020 = 23 fields, 0x63 bytes | yes, `msgdefs.c:1917-1942` | yes, same field order | yes, `P021_SpawnAgent.java` (23 fields, Java widening) | — | yes, client accepts our copy |
| 0x0020 field #8 type | BYTE | **`// word`** — outlier | short (= BYTE widened) | — | — |
| speed 288.0 units/sec | yes, `GameSrv.c:1002` | yes, `StoC.h:135 // default 288.0` | yes, `moveSpeed` float | — | walks plausibly |
| 0x0029 = DWORD+VECT2+WORD+WORD | yes | — | yes, `P030_AgentMoveToPoint` | — | yes, drives the walk |
| 0x0029 plane field order | destination-plane **first** (`GameMsg.h:538-544`) | — | **currentPlane first** (`P030`) | — | we send the same value twice, so untested |
| 0x002C = DWORD+VECT2+WORD | yes | — | yes, `P033` | — | yes |
| 0x003D wire shape | yes, VECT2+DWORD+VECT2+DWORD, **unnamed** | — | yes, `P054`: positionVector, positionPlane, moveDirection, movementType | yes, **`MOVE_TO_COORD_WITH_DIR`** | shape matches; **our name is contested** |
| CMSG MOVE_TO_COORD | 0x003E | **0x003C** (older build) | -7 offset | 0x003E | 0x003E works |
| rotation payload | `sin`, `cos` (sin first), typed DWORD | `rotation_cos` then `rotation_sin` (in-memory, not wire) | "actually a float value" | — | never sent |

### The one clean disagreement worth keeping

GWCA numbers `MOVE_TO_COORD` 0x003C and `ROTATE_PLAYER` 0x003E; ldufr numbers
them 0x003E and 0x0040 — a consistent +2. That is exactly the "0x003C to 0x003E
drift" our own `toolkit/schema/import_msgdefs.py:18-19` had flagged from
secondhand documentation. Comparing two live sources on either side of the drift
**independently confirms the drift is real**, not a copying error. Our
`authsrv.py:225-226` comment is correct.

Correction to the track: GWCA's SMSG side drifts too, just later — it puts
`AGENT_ALLY_DESTROY` at 0x003D where ldufr puts it at 0x003E. GWCA is uniformly
an older build; the movement cluster only *looked* clean because divergence
starts past 0x002E.

### Where "not found" was wrong

Two gaps the crosscheck track declared were answerable from files in the same
vault:

1. **0x003D is named.** `apoguita__Py4GW/Py4GWCoreLib/enums_src/Packet_enums.py:42`
   gives `0x003D: 'MOVE_TO_COORD_WITH_DIR'`, in a table whose surrounding
   numbering matches OpenTyria's exactly (verified directly in this pass).
   GWLP-R's `P054` names the same shape `moveDirection` / `movementType`. Two
   lineages read this as a **move carrying a direction**, not as a turn.
2. **The rotation payload is named.** `GameMsg.h:546-551` calls the two DWORDs
   `sin` and `cos`. The track searched `msgdefs.c` and never opened the struct
   header beside it.

Both were reported "NOT FOUND" after searching 7 of 22 mirrors. A gap declared
where the answer is one file away is its own kind of error.

### One method to not reuse

The track inferred wire field order from the order of C *assignment statements*
(`GmAgent.c:333-341`). Wire order is fixed by the struct declaration. It landed
right here only by luck; checked properly against `GameMsg.h:538-544`, the
conclusion holds.

---

## What is still ours, and still invented

From `C:\gd\Rurik\toolkit\authsrv\authsrv.py`, honestly labelled.

| Thing | Where | Status |
|---|---|---|
| The straight-line integrator itself | `:568-607` | **INVENTED**, and structurally correct by accident — it is the same shape as `GmAgent.c:392-428`. The difference is that upstream's legs come from A* over real geometry and ours come from a single click. |
| `TICK_SECONDS = 0.05` (20 Hz) | `:139` | **INVENTED.** Upstream's cap is 500 ms. Ours is internal integration granularity only; measurement confirms we do not broadcast per tick (3 arrival packets in a 14-second session). |
| Sending `UPDATE_POSITION` only on arrival and on stop | `:591-603`, `:715-723` | **OBSERVED, and it matches upstream.** We learned by experiment that 0x002C is a teleport that cancels the walk animation. Upstream independently uses it in only two places, both snap-backs. Our best-corroborated movement decision. |
| `GAME_CMSG_TURN_TO_DIRECTION = 0x003D` as a *name* | `:229` | **CONTESTED.** Py4GW: `MOVE_TO_COORD_WITH_DIR`. GWLP-R: position + plane + moveDirection + movementType. Neither reads it as a turn. |
| Keying keyboard movement off 0x003D | `:689-703` | **OBSERVED** that it is necessary — WASD does not send 0x003E. Our own empirical finding, held by nobody else because no reference server handles this opcode at all (OpenTyria has no handler; the constant has no name in its table). |
| `dest = pos + heading` | `:701-703` | **INVENTED.** Nothing anywhere derives a destination this way. If `values[3]` is a unit vector, this walks one world unit per message. |
| `values[4]` read as a boolean "moving" flag | `:699` | **OBSERVED** (seen as 1 while walking) but **mislabelled** — GWLP-R calls the field `movementType`, an enum. Treating nonzero as "moving" is a guess about an enum. |
| `values[1]` (the client's own reported position) ignored | `:698-703` | **UNEXAMINED.** GWLP-R names it `positionVector`. We integrate from our own position and discard the client's. |
| `DEFAULT_RUN_SPEED = 288.0`, commented "Guild Wars' base movement speed" | `:131` | **Two-lineage corroboration, no measurement.** The comment states it as fact; it should say what it is. |
| The comment "A real server ticks slowly... probably `AGENT_UPDATE_DESTINATION` rather than `MOVE_TO_POINT`" | `:132-139` | **ANSWERED and now wrong.** `MOVE_TO_POINT` is correct. `AGENT_UPDATE_DESTINATION` (0x002A) is never sent by upstream. |
| Overriding the client's position on 0x0047 instead of accepting it | `:715-723` | **DELIBERATE DIVERGENCE.** Upstream accepts the client's figure within 100 units and, on reject, sends *nothing*. Ours was a fix for a real bug; upstream's tolerance is self-declared invented. Neither is authoritative. |
| `WORLD_CREATE_AGENT` payload including the h-fields | `:767-786` | **FAITHFUL COPY**, field-for-field verified against `GmAgent.c:144-157` and the 23-field table — including the eight fields upstream never assigns, which we send as explicit zeros (equivalent, since upstream memsets the buffer). Every value in it is upstream's placeholder, not knowledge. |
| No `WORLD_SIMULATION_TICK` (0x001E) ever sent | — | **GAP.** The one message upstream broadcasts every single tick. |
| No pathfinding, no collision, no `.dat` reader | — | **ABSENT.** Confirmed by grep across the repo: the only mentions of `Gw.dat` outside the vault are scripts that copy or snapshot the file. |
| Rotation never sent | — | **Matches upstream**, which also never sends it. Not evidence it is unnecessary. |

---

## What this changes

For `C:\gd\Rurik\toolkit\authsrv\authsrv.py`, ordered by how much it matters. No
code here — descriptions and reasons only.

### 1. Wrong, and should be replaced: the comment block at lines 132-139

It asks an open question this pass answers, and its answer is the wrong one. The
comment guesses that a real server uses `AGENT_UPDATE_DESTINATION` rather than
`MOVE_TO_POINT` to make the client animate. Upstream never sends 0x002A at all,
and `MOVE_TO_POINT` — which we already use — carries no speed and no duration
precisely because the client is expected to animate from the `speed_base` it was
given at spawn. Leaving that guess in place will send the next person down a
dead end. Replace it with what the tick is now actually for (internal
integration granularity) and record the real open item, which is item 4.

### 2. Wrong, and should be replaced: `GAME_CMSG_TURN_TO_DIRECTION` as a name

Two independent lineages read 0x003D as a move-with-direction, not a turn:
Py4GW names it `MOVE_TO_COORD_WITH_DIR`, GWLP-R names its fields
`positionVector, positionPlane, moveDirection, movementType`. Our own empirical
finding — that keying movement on 0x003D broke click-to-move, and that WASD
arrives here rather than on 0x003E — is not in question and should be kept
verbatim; it is the strongest thing we own. But the *name*, and the comment
"Handled entirely client-side; answering it is unnecessary", are contradicted by
prior art and by our own later code, which does answer it. Rename to something
that describes the shape rather than asserting a semantic, and record the
contest.

Three concrete consequences flow from the GWLP-R field naming, each a real
behaviour change and each currently a guess:

- `values[1]` is the client's own position. We ignore it. It is very likely a
  better answer to "where does the client think it is" than our integrator's.
- `values[4]` is `movementType`, an enum, not a boolean. We test it for
  truthiness.
- `dest = pos + heading` is pure invention. If `moveDirection` is a unit vector
  — which is what `direction` means everywhere else in the protocol — then each
  message walks us exactly one world unit, and the walk only works because the
  client re-sends continuously. Nothing verifies that.

### 2b. MEASURED — and the mechanism I first proposed here was wrong

**Superseded.** The first version of this item claimed 0x003D set a destination
one world unit away, so that arrival fired every tick and teleported the
character continuously. That is wrong, and the commit that introduced it
(`5ed61ff`) carries the wrong version in its message. Measurement, not reading,
settled it — `toolkit/authsrv/analyze_movement.py` over the 2026-08-05 capture,
52 samples of 0x003D. What follows replaces it.

**The three open questions from the pass are now answered, from our own capture.**

| Question | Answer | Evidence |
|---|---|---|
| Is `values[3]` a unit vector or a displacement? | **Neither — a fixed-magnitude direction.** `\|v\|` was 765–768 in all 52 samples regardless of facing. | `analyze_movement.py`, section 1 |
| Is `values[4]` a boolean or an enum? | **An enum.** Values 1 (×50) and 4 (×2). Never 0. GWLP-R's `movementType` naming is corroborated; our truthiness test was reading a boolean that is not there. | section 2 |
| Is the 0x8000 CMSG mask on the wire? | **Yes.** Every decoded header was `0x803D`. This settles the contradiction the tick track flagged as UNRESOLVED, and settles it in OpenTyria's favour. | raw `values[0]` |

Since `\|v\|` ≈ 765, `dest = pos + heading` aimed ~765 units away, not one — so
arrival fired rarely (3 times in 14 seconds), not every tick. The old mechanism
was wrong in both directions.

**What is actually happening.** The client predicts and animates keyboard
movement *itself*. Its self-reported position advanced −9067 → −8510 over two
seconds while we sent it nothing whatsoever. It does not need to be told to walk.

The failure is the correction we send afterwards. At t=3.97 the client reported
itself at −8512; we overruled it with our own integrator's figure of −8603, a
**99-unit backward snap**. The next five reports carried a frozen position: the
client stopped predicting. `AGENT_UPDATE_POSITION` is a teleport, and a teleport
cancels whatever the client was animating — which we already knew from
`authsrv.py:591-597` and had fixed for click-to-move but not here.

Note the number. Upstream's `MAXIMUM_ALLOWED_CORRECTION` is **100.0**
(`GmAgent.c:4`), and the drift that accumulated over one ordinary two-second
keyboard walk was 99. That does not make upstream's constant sourced — it is
still its author's own choice — but it stops looking arbitrary.

**First fix attempt — TRIED, REGRESSED, REVERTED.** The reasoning above led to
two changes that both removed invented code: believe the client's reported
position on 0x003D, and accept its figure within tolerance on 0x0047. Tested
against the client on 2026-08-05. It was **worse than what it replaced** —
the character was pinned at the spawn point entirely, moving only in ~2-second
teleport hops under repeated clicking.

The cause was written down in the code I deleted. The comment on the old 0x0047
handler said: *"Echoing the client's figure back pinned it to the spawn point:
it reported 'still at spawn' because we had not moved it, and we confirmed that
was correct."* Believing `values[1]` reset our integrator to the client's stale
position four times a second, so the tick could never accumulate progress —
exactly the deadlock that comment was written to prevent. Reverted.

The lesson generalises past this bug: a comment explaining why something is the
way it is, is evidence. I read it as history and it was a warning.

**What the failed attempt still established.** The measurements hold — the
magnitudes, the enum, the wire mask are properties of the capture, not of the
fix. And it ruled out the "just trust the client" model: the client will not
drive its own position without server agreement, so we cannot get there by
subtraction alone.

**Second fix attempt — the current one, untested at time of writing.** One
change from the known-good state, targeting the original complaint directly:
0x003D now sends `AGENT_MOVE_TO_POINT` for the destination it sets, so the
client is actually told to *walk*. Every `MOVE_TO_POINT` we had ever sent
answered a click; keyboard movement set a destination silently and the client
had no reason to animate. The walk animation is driven by that message
(`GmAgent.c:333-344`).

It is rate-limited to one message per change of direction (>5°) rather than one
per report. Upstream broadcasts one `MOVE_TO_POINT` per *leg*, and this opcode
arrives ~4x/second; re-issuing it every 250 ms would restart the animation
continuously, which is the jitter we are trying to remove. The 0x0047 handler is
left exactly as it was — one variable at a time.

### 3. Unverified but harmless for now: `TICK_SECONDS = 0.05`

Since we stopped broadcasting position every tick, the 20 Hz rate is internal
only. Upstream's 500 ms cap is not a fact about anything — the author picked it.
Do not change ours to 500 ms in the name of fidelity; there is no fidelity to be
had. Do stop describing 20 Hz as a workaround for something.

### 4. Missing, and worth an experiment: `WORLD_SIMULATION_TICK` (0x001E)

This is the single message upstream sends every tick and we have never sent
once. Payload is one `uint32 delta_ms`. It is cheap to send and it is a
plausible candidate for whatever tells the client to keep animating between
destination updates. This is the clearest open experiment the pass produced.

### 5. Wrong in kind, not in effect: `DEFAULT_RUN_SPEED`'s comment

"Guild Wars' base movement speed" states as fact something we have from two
reconstructions, neither of which cites a measurement. The *value* should not
change — two independent lineages agreeing is the best corroboration in this
whole document. The comment should say that instead.

### 6. Structural, and the real next body of work: no pathfinding, no collision

We walk through walls, and so does our reference between waypoints. The
difference is entirely upstream of the integrator: OpenTyria's legs come from A*
over a trapezoidal decomposition parsed out of `Gw.dat`'s Path chunk, and it
refuses a destination that resolves to no trapezoid. Doing the same requires, in
order: an MFT reader, the decompressor, the "ffna" chunk walker, the Path chunk
parser, and Ascalon's `map_file_id`. We have the archives. We do not have the
map id, and OpenTyria's table does not contain it.

Do not treat OpenTyria's parser as a validated spec when doing this. The 44-byte
trapezoid layout, the `0xEEFE704C` signature, and the fast-math tables are all
reconstruction that must be re-derived against a real archive; two blocks in the
chunk are skipped blind with only an upper-bound assert, so a wrong length
assumption desyncs the whole per-plane parse silently.

### 7. A divergence to keep, knowingly: the 0x0047 handler

We override the client's reported position; upstream accepts it within 100 units
and, when it rejects, sends no correction packet at all. Ours came from a real
observed bug. Upstream's tolerance is the one constant in the whole reference
its own author labels as invented. Keep ours; note that it is a choice, not a
correction of upstream.

### 8. Traps to carry forward if we ever port more of this code

- `Vec2f_Dist2` returns **true Euclidean distance** despite the name — it calls
  `sqrtf` (`GmMath.h:8-13`). Any port that assumes squared distance gets the
  arrival comparison wrong.
- `GmPos` is **10 bytes on the wire, 12 in memory** — `GmDefs.h` sits outside
  any `#pragma pack`.
- A world tick **can** emit `MOVE_TO_POINT` (on waypoint advance). A client
  assumption that a tick carries no per-agent packets is unsafe.
- `UpdateAgentDestination` divides by the norm with **no zero guard**, and a
  click on your own position reaches it.
- `PathFinding` can return **false with a non-empty waypoint array**
  (`GmPaths.c:1043-1056`), and the caller never clears it on the failure path —
  stale waypoints survive until the next successful request.
- Do **not** adopt "opcode 71" for 0x0047 from OpenTyria's comment; the constant
  evaluates to 0x8047 and OpenTyria is internally inconsistent about whether the
  0x8000 CMSG mask is on the wire. Our own framing already treats 0x8000 as a
  synthetic table tag, and our capture is the arbiter here, not upstream.

---

## Open questions

| Question | What would answer it |
|---|---|
| Does the client need `WORLD_SIMULATION_TICK` (0x001E) to animate smoothly between destinations? | Send it at ~2 Hz with a real `delta_ms` and watch the walk. A one-session experiment against our own client. |
| What are the two `Vec2f` fields in 0x003D really — is `values[3]` a unit vector or a displacement? | Log raw 0x003D payloads while holding W, and measure the magnitude. Our own capture answers this; no reference can. |
| Is `values[4]` a boolean or an enum, and what are its values? | Same capture, across walk / run / turn-in-place / strafe. |
| What does 0x002E (`AGENT_UPDATE_ROTATION`) actually carry — sin+cos floats, two angles, or something else, and in what order? | Nothing in any mirror settles it: the struct names `sin, cos` but the format table says DWORD, and upstream never sends it. Send it and observe, or dump the client's deserializer table. |
| What is Ascalon City Pre-Searing's `map_file_id`? | Recover it from `Gw.dat` ourselves. Not in OpenTyria's six-map table. |
| What does a "plane" mean physically? | Not in any source. Parse a real map's Path chunk and compare plane count and per-plane Y-extents against a map with a known bridge or overpass. |
| Is 288.0 actually retail run speed? | Two reconstructions agree; neither measured. Time a known in-game distance against a real client. |
| Is the 0x003C to 0x003E CMSG drift the only drift affecting us? | Confirmed real for MOVE_TO_COORD/ROTATE_PLAYER. GWCA's SMSG side also drifts, starting past 0x002E. Only dumping our own client's deserializer table settles the whole map. |
| Which client build were OpenTyria's `msgdefs` extracted from? | Nothing in the repo records it — no version stamp in `msgdefs.c`, `msgdefs.info`, or `opcodes.h`. If ArenaNet changed the tables between builds, the extracted numbering is valid for exactly one `Gw.exe` and we do not know which. |
| Does the retail server tick at fixed Hz, variable timestep, or something else? | Unanswerable from any source we have. OpenTyria's 500 ms cap is its own choice. Only a real server capture would settle it, and there is no real server. |

The last row is the honest shape of this whole document. None of these mirrors is
the client's own deserializer table. Until that is dumped, every one of them —
OpenTyria included — is a reconstruction of varying quality, and our own client's
behaviour is the only ground truth we have.
