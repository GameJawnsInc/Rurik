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

**SUPERSEDED in code (note added 2026-08-16): the override was reversed, and
this section is the stale side.** The live 0x0047 handler now accepts the
client's position and plane unconditionally — "THE SERVER NO LONGER ARGUES" —
recording the disagreement instead of correcting it
(`toolkit/authsrv/authsrv.py:6337-6371`). The session that settled it is
recorded in that comment: all seven corrections it sent were indefensible on
review (two were plane changes we could not see because clicking sends no
keyboard packets; two snapped the player off collision geometry our trapezoids
have never read; teleporting a player nine units is pure damage). `on_mesh` is
still measured per stop (57/61 on our mesh) as evidence about our map data, not
grounds for moving the player. See `../unitsetup/FINDINGS.md` §3.

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

---

## Movement, rebuilt from playtests (2026-08-05)

The section above was written before any of this was tested against a running
client. What follows was.

### Keyboard movement is a DIRECTION. FIXED, and verified in play.

`GAME_SMSG_AGENT_MOVE_DIRECTION` = **0x0025**, `dword agent, vec2 direction,
byte movement_type`. Answering WASD with `AGENT_MOVE_TO_POINT` — an absolute
destination — was the single cause of a whole session's worth of symptoms.

An absolute destination has exactly two failure modes and this server hit both,
alternately, across five attempted fixes:

* a point **past a wall** and the client walks toward it;
* a point **at or behind** the player and the client walks backwards to it.
  Against a wall `clip(pos, pos + heading)` returns approximately `pos`, so a
  clipped grant means "walk to where the server thinks you are". With a fresh
  position that is a snap; with one gone stale during click-to-move it is a long
  straight walk back over buildings. Both were reported, and they are one bug.

A direction has neither failure mode. There is no point to name, so there is no
wrong point to name.

SOURCE: GWLP-R (`MoveRotateClick.onKeyboardMove` → `EntityMovementView
.sendChangeDirection`), a different lineage from OpenTyria. Its opcodes run 11
below build 38797's, consistently across five messages whose field shapes all
match `schema/messages.json` — which came from the client's own tables, so the
shapes are corroborated independently of GWLP-R:

| GWLP-R | ours | our schema's shape | reading |
|---|---|---|---|
| P026 MoveDirection | 0x0025 | `dword, vec2, byte` | agent, direction, type |
| P028 MovementSpeed | 0x0027 | `dword, float` | agent, speed |
| P030 MoveToPoint | 0x0029 | `dword, vec2, word, word` | agent, point, planes |
| P032 SpeedModifier | 0x002B | `dword, float, byte` | agent, modifier, type |
| P035 AgentRotate | 0x002E | `dword, dword, dword` | agent, cos, sin |

`movement_type` is a DIRECTION enum, not a mode: Forward 1, DiagFwLeft 2,
DiagFwRight 3, Backward 4, DiagBwLeft 5, DiagBwRight 6, SideLeft 7, SideRight 8,
Stop 9. Our own captures only ever showed 1 and 4 — forward and backward.

### The server does not broadcast position at all any more

Every correction it ever sent was damage. In the session that settled it, seven
went out and not one was defensible: two "plane disagreements" of 11 and 26
units that were an artefact of never learning the plane, and two off-mesh stops
of 26 and 9 units. Teleporting a player nine units is pure harm.

`AGENT_UPDATE_POSITION` is **not a teleport**. Observed in play: the client
appears to WALK to a granted position, in a straight line, over a couple of
seconds, passing over buildings. "Instant snap" and "warped across the map" are
the same message at two distances. The claim that it is a teleport was inherited
from upstream and is contradicted by our own client.

### Slot 1 of 0x003D is the client's live position — believe it

MEASURED advancing at 211 units/sec over 120 samples. GWLP-R does the same thing
(`pos.position = position` straight out of the keyboard packet), which is
independent agreement reached from opposite directions.

The earlier failure that produced "pinned at spawn" was a different situation,
not a warning against this: back then no keyboard `MOVE_TO_POINT` was sent at
all, so the client never animated, reported spawn forever, and we copied it back.

### Plane indices in the archive ARE the protocol's plane numbers

MEASURED over 198 position-and-plane reports: 189 landed inside a trapezoid
whose plane index was exactly the plane the client named — 0→0 (148×), 12→12,
5→5, 4→4, 3→3. First result tying map geometry to the wire.

The 9 exceptions were all "client says 12, we find 0": a bridge and the ground
under it, in a file with no height. `PathingMap.plane_at` returns None rather
than guessing when a point is ambiguous.

Planes are **not floors**. Kamadan has 39 and there is no Z anywhere in the
file; they are connected regions of walkable surface. Crossing one is routine,
which is why a server that treats every plane change as significant is wrong
almost constantly.

### Click-to-move: BROKEN, and NOT DEBUGGABLE FROM THE WIRE

Reported from play: sometimes it paths correctly, sometimes it warps the player
to the clicked point, sometimes it walks a straight line through walls, and
clicking a staircase can drop the player onto the floor underneath.

The two `word` fields of 0x0029 are **UNRESOLVED**, and the two sources
contradict each other:

* OpenTyria `GameMsg.h:538` — `uint16 plane` then `uint16 current_plane`, filled
  from `destination.plane` and `position.plane`. Destination FIRST.
* GWLP-R `P030` — `currentPlane` then `nextPlane`, documented "0 if player stays
  in the same plane". Current FIRST.

Both orders have been shipped and played. Neither fixed anything. OpenTyria is
the better-matched witness on this message — it defines the opcode as 0x0029,
exactly our build, where GWLP-R's is 30 from another era — and that is the order
currently in the server, on grounds of provenance rather than evidence.

**Why the experiment cannot be run.** Two routes, both closed:

1. *A/B by eye.* Ruled out by the player: the bugs are intermittent, so single
   trials of a symptom that comes and goes measure nothing. `--click-sweep`
   exists and cycles the fields through every assignment, but a human cannot
   score it.
2. *Automatic detection.* We have the navmesh, so "did that path cross
   unwalkable ground" is computable — if there is a path to check. There is not.
   MEASURED: the median number of client position reports between one click and
   the next is **ZERO**, across 35 click intervals. The client reports position
   on keyboard input; while click-moving it says nothing until it stops or the
   player clicks again, once for 37 seconds straight.

So the server sees the request, and sometimes where it ended up, and nothing in
between. **Click-to-move is unobservable from the server.**

What remains is the client's own code: the handler for 0x0029 in `Gw.exe`. The
msgtable study recovered build 38797's message tables from that binary with
capstone and pefile, so the approach is proven in this repository, but
`toolkit/clientscan/` is string scanning only. The disassembly is new work.

One piece of player knowledge worth keeping, because it corrects a claim made
earlier in this branch: in the stock game a click at a far or awkward point
walks a plain straight line toward it — and is still STOPPED by obstacles. So
the client does collide on a server-granted destination. An earlier test here
suggested otherwise; that test had keyboard movement on `MOVE_TO_POINT` as well
and could not tell the two paths apart.

---

## What the client's own code says (2026-08-05, disassembly)

The first movement facts in this project that are neither a reconstruction nor an
inference from play. `toolkit/clientscan/msghandler.py` turns an opcode into the
function that consumes it; the route is a table lookup, not a search, because the
12-byte receive descriptor the msgtable study recovered carries a dispatch
pointer as its third member.

### 0x0029 AGENT_MOVE_TO_POINT — both fields identified

```
0x005fd890   handler
    builds a local {x = [msg+8], y = [msg+0xc], plane = [msg+0x10], 0}
    calls 0x00602a40(this = agent, &that, 0, [msg+0x14])

0x00602a40   cmp eax, -1 / je / mov [ebx+0x80], eax
             [ebx+0x88..0x94] = the point        (first copy)
             [ebx+0x98]       = arg2
             [ebx+0x9c..0xa8] = the point again  (second copy)
             lea esi, [ebx+0x78]  ->  passed to the movement starters
```

* **First wire word = the DESTINATION's plane.** It is packed into the position
  struct beside x and y and travels with the point.
* **Second wire word = the AGENT's CURRENT plane.** It is written to
  `agent+0x80`, and the agent's own position is `{x @0x78, y @0x7c, plane
  @0x80}` — which is what `lea esi, [ebx+0x78]` hands to the movement code.

So **OpenTyria's field order is correct** (`plane` then `current_plane`,
`GameMsg.h:538`) and GWLP-R's `(currentPlane, nextPlane)` is not, for this build.
Two lineages contradicted each other, both orders were shipped and playtested,
and the binary settles it.

Corroboration for `+0x80` being a plane that does not depend on either source:
across the agent module it is used as `add ecx, [esi+0x80]` (indexing per-plane
data) and `xor eax, [ecx+0x80]` (an equality test).

**-1 means "leave the plane alone", and a server CANNOT say it.** The field is
msgtable type 4 — "unsigned int, count wire bytes widened to a 4-byte slot" — so
`0xFFFF` arrives as 65535, not -1. Four of the eight internal callers of
`0x00602a40` push `-1`; the idiom exists but is unreachable from the wire. A
server must therefore send a CORRECT current plane, and a wrong one is written
straight into the agent, after which the client collides against the wrong
surface. That is the shape of both reported click bugs.

### 0x002A AGENT_UPDATE_DESTINATION is the same call with one more argument

Its handler at `0x005fd930` is byte-identical to `0x0029`'s except for a single
push: where MOVE_TO_POINT hardcodes `0` for arg2, UPDATE_DESTINATION passes a
fifth wire field (`[msg+0x18]`, a dword). That argument lands in `agent+0x98`,
which the internal move re-issuers at `0x00602448` and `0x00602984` deliberately
preserve by passing `[edi+0x98]` back in.

**NOT YET TRIED**, and the most promising remaining lead for click-to-move. An
older comment in our own tick code guessed that AGENT_UPDATE_DESTINATION was
what makes the client animate properly; the disassembly says it is at minimum
the same movement call with one more server-controlled input.

### The handler table is a general tool now

Any message whose meaning is contested can be resolved this way rather than
argued about:

    python toolkit/clientscan/msghandler.py 0x0029 --follow

Send-only opcodes report "the client only SENDS this one" instead of failing,
because send descriptors are 8 bytes and have no dispatch member.

---

## Where movement was left (2026-08-05, end of session)

Closed by the owner as good enough, with the remaining faults recorded rather
than chased. Read this before reopening movement — several of the obvious next
ideas were tried in this session and made things worse.

### Working, and verified in play

* **Keyboard movement.** Stable, wall-hugs without rubber-banding.
  `AGENT_MOVE_DIRECTION` 0x0025, direction echoed from the client, movement type
  passed through, re-sent only on a real change of direction.
* **Click-to-move at range.** "Incalculable distances now stop in a
  straight-line-til-obstacle way just like stock." That is the owner's
  comparison against the retail game, and it is the closest thing to a fidelity
  result this project has.
* **Stairs.** Stable in ordinary play; the character paths to the foot of a
  staircase and climbs it rather than walking through the railing.

### Still broken

**Warping near stairs when mixing input modes.** Reproduction, from the owner:
**hold S and spam-click destinations on different planes.** Rare in normal play,
easy this way.

That combination is exactly what the server handles worst, and the mechanism is
known even though the fix is not:

* Holding S drives `AGENT_MOVE_DIRECTION` with movement type 4 (Backward) while
  clicks drive `AGENT_MOVE_TO_POINT`. Two movement commands, interleaved, with
  one shared piece of state.
* Every answered click writes the player's *current plane* into `agent+0x80`
  (read out of `Gw.exe` — see the disassembly section). We take that from the
  client's last report, which may be up to a second old, and spam-clicking
  across planes changes the true value faster than we learn it.
* `-1` means "leave the plane alone" and is **unreachable from the wire**: the
  field is msgtable type 4, unsigned. So the server cannot decline to answer the
  question; it can only decline to answer the click.

Guards already in place, each of which reduced the rate: answer a click only
when a client position report is under a second old, only when the geometry can
place the player (on the mesh, exactly one plane, and that plane the one the
client named), and only when the straight line to the destination is clear.
About 6% of clicks are deferred to the client's own pathing as a result.

### Do not retry these

Each was tried in this session and was wrong.

1. **Clipping the keyboard leg.** Any destination we invent is wrong in one of
   two ways — past a wall the client walks through it, at the wall
   `clip(pos, pos + heading)` returns approximately `pos` and the client walks
   backwards to it. There is no safe value between. Keyboard movement must not
   name a point at all.
2. **Broadcasting position.** `AGENT_UPDATE_POSITION` is not a teleport; the
   client appears to WALK to a granted position, over buildings, taking seconds.
   Every correction this server ever sent was damage, including 9- and 26-unit
   ones.
3. **Clipping the click, or refusing a short one.** The client paths clicks by
   itself, competently. Substituting our own destination overwrites a correct
   route with a straight line — caught in play with screenshots on a staircase.
4. **Deriving the plane from the navmesh when the client has just told us.**
   MEASURED, that overrules the client on 3.7% of reports, most often "client
   said 5, we would have sent 0", and writes the wrong surface into the agent.

### The one untried lead

`0x002A AGENT_UPDATE_DESTINATION`. Its handler is byte-identical to
MOVE_TO_POINT's except that the server supplies the argument 0x0029 hardcodes to
zero — the value written to `agent+0x98`, which the client's own internal move
re-issuers deliberately preserve. What `+0x98` does is not decoded. Read the
handler before sending anything:

    python toolkit/clientscan/msghandler.py 0x002a --follow

### The larger gap

**There is no server-side pathfinding**, and there cannot be until the plane
sub-records (portals, x/y BSP nodes, sink nodes, edge vectors) are decoded. Every
click the server declines is the client covering for us. A real server owns
pathing and sends the legs of the route.

## The position-trust LATCH — measured 2026-08-19, and it is a real defect

**The owner reported a warp from memory**: click far, go hands-off, then mix in
WASD (they later reproduced it by holding **S** while spamming click-to-move) and
the character sometimes jumps. Hard to reproduce deliberately, so the session
added `--trace-move` (prints every client position report beside the server's own
belief, plus the origin each click's collision ray is cast from) and the owner
drove a 6-minute session on map 449 — harness `20260819T113049`, gamesrv log,
240 position reports and 102 clicks.

**The measurement, and the two regimes are categorically different:**

| | `\|dX\|` median | `\|dY\|` median |
|---|---|---|
| ADOPTED (n=190) | **2 u** | **19 u** |
| REJECTED (n=50) | **497 u** | **1457 u** |

When the model tracks, it tracks to a couple of units. The rejections are not the
tail of that distribution — they are a different population, which rules out
gradual speed drift as their cause (`DEFAULT_RUN_SPEED` 288 u/s against a client
measured at ~197–211 would accumulate hundreds of units smoothly, not jump).

> **The parenthesis above is wrong and the conclusion it supports is right.**
> There is no 288-vs-197 mismatch: the integrator's *effective* rate is
> **282.3 u/s** (288.0 × 0.05 ÷ 0.0510, from 1,415 measured tick sends — the
> loop steps a constant 14.4 u per iteration and the real period is 51 ms, not
> 50) against a client keyboard cruise of **282 u/s** p50. That is 0.1%, and
> adopted-report drift is a median of 11 u. `197` appears nowhere in the corpus
> and `211` is movementType 7's number and the click-walk number, generalised.
> Speed drift is refuted as a cause *because it does not exist*, not because it
> would be smooth. Full correction in "Speed is not the divergence" below.

**THE DEFECT IS THAT THE GUARD LATCHES.** `_adopt_client_position` refuses any
report more than `CLIENT_POSITION_TRUST_RADIUS = 900 u` from our belief. That is
sound against a lying client and exactly backwards against a *diverged server*:
once the error exceeds 900 u, every subsequent correction is also >900 u, so the
model can never resynchronise. **Longest unbroken reject streak: 36 reports.**
21% of all reports in the session (50 of 240) were refused. A guard whose failure
mode is "stay wrong forever" needs an escape hatch — a consecutive-rejection
counter that capitulates, or a re-sync on any message that carries an
authoritative position.

**What the warp then looks like on the wire.** Three clicks were cast from a ray
origin more than 900 u from where the client itself had just said it was
(1030 u, 1106 u, 1151 u), and each produced an `AGENT_MOVE_TO_POINT` computed
from that wrong origin — a destination with a plausible shape and the wrong
place. That is a warp with a straight face. It is only 3 of 102 clicks, though:
**the ray origin is usually fine** (median error 30 u, 90th percentile 115 u), so
this is a consequence of the latch rather than an independent bug, and the
click-origin hypothesis the session started with is REFUTED as a general cause.

**What is NOT established: the floors.** The owner suspected planes, and the
three bad clicks all carried `on plane 5->0`, and 53% of the session's move
orders cross a plane (48 same-plane, 54 changing among planes 0, 5, 27). But of
the four reject streaks, only **one** was preceded by a plane-changing move
order. So plane changes are frequent and suggestive and the correlation does not
hold up — UNVERIFIED, and worth one designed probe rather than another eyeball.
The known plane weakness is still on record above: clicking sends no plane, so
the server only learns it from keyboard packets.

**Why this outranks the walk-to-interact work.** `0x002A` was shipped OFF the
same day for dragging the player through a staircase, and any server-driven walk
inherits this: it moves the player with no position report to correct the model,
which is precisely the condition that opens a >900 u gap. Fix the latch first.

---

## The warp is CLOSED — the client teleports onto a destination WE granted

**OBSERVED, 2026-08-19, run `20260819T114743`.** The owner reproduced the warp
with a screen recording running. It is not drift, not our ray origin, not the
enemy, and not the plane fields. It is this:

```
t=42.726  c2s MOVE_TO_COORD    [10995.26953125, 5549.82470703125]  plane 18
t=42.726  s2c AGENT_MOVE_TO_POINT(10995,5550 on plane 0->18, clear line)
          ... player cancels, fights, then stands still. Client sends one ping
              and one target-deselect. The server sends nothing at the player. ...
t=54.320  c2s MOVE_SET_HEADING  [10995.26953125, 5549.82470703125]  plane 18
```

**MEASURED.** 2,843.963 u in 3.770527 s = **754.26 u/s**, 2.62× base run speed,
while the recording shows the character motionless. The reported position is not
*near* the destination — it is the **same IEEE-754 bit pattern**, `14cd2b46` /
`996ead45`, hand-decoded from the raw frame plaintext without the schema
decoder, in the click frame, in our grant, and in the snap. The plane matches
too: over all 62 self-reports in the run the plane census is `{0: 61, 18: 1}`,
and the single `18` is the snap.

**It is a real body position, not an echo — a check with no free parameter.**
Advance the disputed report's *own* heading `(-511.857, 572.243)`, normalised,
at 288 u/s for the measured dt of 0.717666 s: predicted `(10857.474, 5703.877)`,
measured next report `(10858.894, 5702.290)`. Residual **2.130 u over 204.558 u
travelled**, heading-vs-displacement angle **0.000°** against a run median of
3.802°. A stale echo cannot predict the next frame.

**No speed in Guild Wars closes the gap.** WIKI (GWW, "Speed boost", fetched
2026-08-19): boosts cap at +34%; the four cap-breakers top out at Junundu Tunnel
+66%. At the most generous 1.66× the 3.77 s window buys 1,802.6 u against
2,843.9 needed — short by 1,041 u. The only `AGENT_UPDATE_SPEED` naming the
player all run was `1.0 = 288 u/s`.

### Three independent clocks agree

| Instrument | Value |
|---|---|
| Wire: grant → snap | **11.594 s** |
| Screen recording duration | **11.867 s** |
| Recording filename (`11-48-41`) vs the click's wall clock (`11:48:41.7`) | same second |

The recording opens on the player running toward a distant bridge, shows them
turn, back off, fight, and stand still, and ends with them **standing on the
bridge**. The warp lands between video 11.050 s and 11.175 s — one 0.125 s
window, coincident with the first movement input after ~4 s of stillness.

### It is OUR grant, not the client's own click memory

Both carry identical coordinates, so the value cannot separate them. The
**contrast** can. Across all 918 gamesrv captures: 331 clicks, **113 granted an
`AGENT_MOVE_TO_POINT`, 218 refused**; 25 inter-report steps exceed 320 u/s;
**four land bit-exactly on an earlier granted destination — all four in the
granted arm, none in the refused arm.**

| Run | speed | lag | planes |
|---|---|---|---|
| `20260814T100340` | 7,874 u/s | 16.284 s | 0→0 |
| `20260818T103840` | 402 u/s | 19.686 s | 0→18 |
| `20260819T113105` | 489 u/s | 0.867 s | 5→0 |
| `20260819T114743` | 754 u/s | 11.594 s | 0→18 |

`C(113,4)/C(331,4) = 0.0131`. **Bit-exact landing on your own click goal is
normal** — it is the arrival clamp, and it happens in *both* arms (five in the
refused arm, at 0.15×–0.86× of base speed). What happens only in the granted arm
is landing there at an *impossible* speed.

### The mechanism, read out of the client — MEASURED, build 38797

> **CORRECTED 2026-08-19. The two field names below were SWAPPED, and the
> correction sharpens the finding rather than softening it.** `+0x88` is
> **m_segmentPoint** (assert `AgAgent:1143`, guarding the loads at `0x00600227`
> / `0x00600236`) and `+0x9C` is **m_targetPoint** (assert `AgAgent:1144` at
> `0x00600282`). "syncPoint" came from `AgAgent:2147`, which names a **stack
> local in a different function**, not this field. Because they are two
> different fields, `AgAgent:1158`'s 1.0-unit assert does **not** compare
> `+0x88` against itself and it **can** fire — that earlier claim is withdrawn.
> The real gap is sharper: **nothing anywhere compares m_targetPoint against the
> agent's actual position before `0x0060032E` writes it.**
>
> Two more from the same pass. The teleport is **conditional** — `0x006001EB`
> requires `time == +0x48` **exactly**, and `0x0060029F` then tests m_flags bit
> 18: SET glides, CLEAR teleports. And `0x00602A40` passes isWaypoint = 0, so
> **every grant we send arms the teleport branch and never the glide branch.**

`0x0029`'s handler `0x005fd890` calls `0x00602A40`, which stores the wire point
**twice** — into m_segmentPoint (`agent+0x88`) and m_targetPoint (`agent+0x9c`) — writes the second plane word to
`agent+0x80`, clears `INTERNAL_FLAG_MOVEMENT_STALE` (bit 19, from
`shr eax, 0x13` at `0x0060014E`), and caches a velocity and an **arrival tick**
at `agent+0x48`. Until that tick, `0x005FFB40` dead-reckons linearly. **At the
arrival tick**, the movement tick `0x00600140` copies the 16 bytes at
`agent+0x9c` and calls `0x006020B0` — the teleport primitive — which writes them
straight into `agent+0x78/+0x7c/+0x80/+0x84`, zeroes velocity, invalidates the
destination with `+inf` (`0x00948654` = `0x7F800000`), and drags every attached
agent along. **No path solve, no collision check, and no distance guard on that
value**: `AgAgent:1158`'s 1.0-unit assert compares `+0x88` against itself and
cannot fire, and the call at `0x0060032E` is straight-line past it.

**The destination survives every cancel, by construction.** The exhaustive
writer census of `+0x88` and `+0x9c` finds no clear anywhere except the `+inf`
invalidation at arrival. And `0x0047` — the client's own move-cancel — has **no
receive handler in the agent table at all**; it is send-only. So a granted
destination is erased only by being consumed or overwritten by a newer grant.

*This closes an open question already on file:* `studies/smsg/FINDINGS.md:390`
asks whether flag `0x80000` is "moving by direction". It is not — the client
names it itself, `INTERNAL_FLAG_MOVEMENT_STALE`, one assert site,
`AgAgent:1198`.

### What this REFUTES, including two of our own leads

- **REFUTED — "cross-plane grants are our invention."** They are attested:
  **455 of 2,855** player-directed `0x0029` in the live corpus (15.9%) carry
  differing planes, across 29 of 39 connections, and the exact `(dest=18,
  cur=0)` pair we sent occurs **11 times in ArenaNet's own traffic**. Do not
  suppress the message. What is unattested is the **lag** — live cross-plane
  grants are answered a median **0.465 s** later, and ArenaNet re-grants the
  player every 0.492 s median, so its destinations are always ~half a second
  ahead and constantly refreshed. Ours sat armed for 11.6 s.
- **REFUTED — the click ray-origin hypothesis** (median error 30 u, p90 115 u
  over 102 clicks; only 3 of 102 exceed 900 u).
- **REFUTED — "it warps you back to where you started."** Three jumps landed
  5–37 u from a previously-occupied spot, but the null nearest-neighbour
  distance to the earlier track has a *minimum* of 5.3 u and a 5th percentile of
  24.9 u. Those three **are** the null distribution.
- **CONTESTED — the other 8–13 impossible jumps.** Every one is preceded by a
  grant (13/13 within one interval, against a 25.3% base rate), but they do
  **not** land on granted destinations (1 of 13 within 5 u, against a 1-in-80
  null; median 145 u vs a null of 122 u). Grant-triggered and not
  grant-landing — the arrival snap does not explain them. Named measurement:
  poll `agent+0x78/+0x7c`, `+0x88..+0x94`, `+0x9c..+0xa8`, `+0x48` and `+0x20`
  bit 19 out of the live client across a granted click, which
  `toolkit/harness/keytap.py` can already do in pure `ctypes`.

### Speed is not the divergence

**MEASURED.** Integrator effective **282.3 u/s** against a client p50 of
**282 u/s** — 0.1%. Adopted-report drift median 11 u, max 55.7 u over 53
samples. All of the divergence in the flagship run is the two click excursions
and none of it is speed.

The client's speed *does* split by `movementType`, and the enum is a direction
family: forward `{1,2,3}` **284.96 u/s** (n=184), backward `{4,5,6}` **187.89**
(n=114), side `{7,8}` **~215** (n=48, the weak row). The within-file
backward/forward ratio is **0.6584–0.6614** across 12 files, which refutes the
tidy `2/3 = 0.6667`. Two cautions that matter more than the numbers:

- **Do not build a per-type table into the integrator.** Types 7+8 are 0.71% of
  moving time and account for **0.87%** of the flat-288 over-run. A full
  per-type table removes 37% of the error; the other 63% is an unexplained slow
  regime (sustained plateaus at ½ and ⅓ of each type's own cruise, 27% of
  forward moving time) that no constant models. And the integrator is re-aimed
  every report while moving, so per-type error cannot accumulate past one
  interval: max 113.5 u against `INTERACT_RANGE` 250.
- **The absolute scale is CONTESTED**: 284.96 measured in 2D, versus 288 with
  ~1% of the motion vertical and therefore invisible to a chord in a format with
  no height. Both reproduce the ratio. The separating measurement is one capture
  along a straight leg >512 u inside a single trapezoid of constant elevation.

Also corrected: `0x003D` is **distance-triggered** (fixed ~512 u chord) with a
~0.5 s heartbeat fallback, not time-triggered — so a `dt < 0.6 s` "curvature
control" selects only the heartbeat and discards every clean cruise sample.

### The fix that shipped, and what it deliberately is not

`_adopt_client_position` is gone. `_position_verdict` + `_take_client_position`
replace it, both receive sites route through one function, and the budget is
`max(900, 580 · dt)` — **never smaller than the old flat radius**, so nothing
that passes today can be refused tomorrow. The Nth consecutive refusal is
adopted regardless (`CLIENT_POSITION_REJECT_STREAK = 2`), which makes a 36-long
streak unreachable for any constants.

**A tighter budget was designed, costed and thrown away.** `BASE 120 + 580·dt`
would newly refuse **8** corpus reports the flat 900 accepts — all eight in the
one run whose displacements have no established cause. Tightening where the
model is least understood turns an open question into a regression.

**The guard's record is 0-for-72.** Counted from the servers' own
`[map] ignoring a Nu jump` lines across the four harness runs that have any
(7 + 11 + 50 + 4), scored by asking whether the client's next report is
reachable from the point we refused or the one we preferred at 478 u/s: **client
right 71, guard right 0, undecidable 1**. It survives only as a single-frame
refusal and as the place the telemetry hangs.

> **Do not reuse two numbers from the working notes.** A replay of this question
> reported **85** refusals and a largest true-but-refused drift of **18,647 u**.
> Both are artifacts of an unvalidated replay: the servers printed **72**, and
> the largest drift anywhere in the harness tree is **4,116 u**. Two draft
> designs had already pinned 18,647 in a test that would have gone red forever
> against a number no server ever produced.

Also fixed in the same change: the `0x003D` arm wrote `state["plane"]`
unconditionally **28 lines above** the position guard, so a refused report left
the server holding the client's new plane against its old position — measured at
t=54.320, plane 18 against a point our navmesh puts on plane 0. Position and
plane are now adopted or refused together. And `position_report`'s
`accepted=True` was a **literal**, emitted from the stop arm only, so the
flagship capture's JSONL held 5 of 62 reports and none of the four refusals —
our own telemetry failing the "a check that cannot fail is not a check" rule.

**The latch fix does not fix the teleport, and must not be reported as doing
so.** The client still relocates onto points we grant; the server now stops
arguing with it within one report instead of never. The blast radius it *does*
close is real and was measured: during the excursion the server drove the
Hatcher to within 9 u of the phantom and `enemy_attack_tick` — the only path
that reduces `player_health` and the only path that sets `player_dead` — swung
and connected, at a player standing **2,844 u away** with nothing on screen to
explain it.

### The candidate warp fix — RUN, and REFUTED (2026-08-19)

**Result first.** `--stop-echo` does **not** stop the teleport. Harness run
`20260819T134811`: one clean trial — a 4,118 u grant to (11010, 5471) plane
0→18 at t=25.05, the same shape as both teleports on record — with a stop echo
fired at t=34.91, 9.86 s later and well inside both known lags. The operator
watched the character teleport to the bridge regardless. The prediction printed
at startup named that outcome as the refutation, so there is nothing to
reinterpret: **overwriting the armed destination is not the mechanism.**

**And the echo may be harmful, which is a stronger result than the null.** The
operator also reported that immediately after the teleport the character began
walking *back* toward where it had warped from — which is precisely where the
echo had planted a destination a moment earlier. So the echo does not *replace*
the pending click destination; it **adds a second one**. Since it fires on every
stop, it leaves a live destination at every place the player has ever stood
still — and "you get dragged back to where you stopped" is the other half of the
warp the owner originally reported from memory. Left off, and now labelled
REFUTED at the flag rather than merely unproven.

**A method note that cost this run its wire evidence.** The client sends no
position while standing still, and it was silent for the final **11.74 s** —
which contains both known warp windows (11.6 s and 19.7 s post-grant). The
capture therefore shows no impossible step at all, and `warpscan.py` scored the
run "1 trial, no teleport". That verdict was wrong, and only the operator's own
eyes caught it. **Any future warp run must keep the keyboard moving through the
whole waiting period** — a tap of W every couple of seconds is enough to keep
the instrument recording. A detector that goes blind exactly when the phenomenon
fires is worse than no detector, because it reports a clean null.

### CONFIRMED ON THE WIRE, without the echo (run `20260819T135526`)

The teleport reproduced with `--stop-echo` OFF and the operator tapping W
through the wait, so the client kept reporting and the landing is recorded:

```
t=29.889  s2c AGENT_MOVE_TO_POINT(10987,5432 on plane 0->18, clear line)
   ... 10.4 s of ordinary keyboard movement at 184-288 u/s ...
t=40.248  c2s MOVE_SET_HEADING (11028.8, 5427.9) plane 18
          2,305 u in 0.23 s = 9,878 u/s -- 34x run speed
```

The plane flips 0→18 with the position, as before. **Lag 10.36 s**, joining
0.9, 2.1, 10.8, 16.3 and 19.7 s. No function of the grant distance fits that
spread, so the arrival-tick arithmetic stays OPEN.

**The path-back was MY bug, not the game's.** With `--stop-echo` on, the
operator saw the character walk back toward the pre-warp position immediately
after the teleport. With the echo off, on the very next run, it did not. n=1
each and operator-observed rather than on the wire (the client went silent for
17.8 s after the landing), but the direction is unambiguous and it matches the
mechanism: the echo plants a destination at every place the player stops.

**And "bit-exact landing" was never a property of the teleport.** This landing
sits **42 u** from the granted point, not on it — the client snapped and then
walked 42 u before its next report, which is 0.23 s at the 186 u/s it was
already moving. The two bit-exact cases were simply the ones whose report fell
on the instant of the snap. `warpscan.py` had that 1.0 u tolerance as a
DETECTION GATE and it silently suppressed this teleport entirely, reporting
"1 trial, no teleport" for a run the operator had just watched warp. The
detector is now the impossible step alone; grant proximity is reported, never
required. Corpus-wide that turns 4 detected teleports into **12 — 7 near a
grant, 5 not** — and the 5 unattributed are the same CONTESTED population as
before.

### What the refuted fix was, and why it looked good



ArenaNet answers `0x0047` (move-cancel): **70 of 88** replies are a
zero-distance `0x0029` whose destination equals the position the client just
reported — a stop-here echo — plus `0x0028 AGENT_STOP_MOVING` (257 corpus-wide,
81 naming the player). **We send nothing.** Since the client's armed destination
is cleared only by consumption or by a newer grant, echoing the client's own
stopping point back would overwrite the syncPoint with where the player already
is, and the arrival snap becomes a no-op. Attested in shape, grounded in the
disassembly — and it may fix nothing for the 13 grant-triggered jumps that do
not land on grants. It needs a flag, a run, and a prediction stated first.

**And do not report `0x002C AGENT_UPDATE_POSITION` as ArenaNet's correction
channel.** There are 12 in the entire live corpus over 4,916 s of identified
play; only 2 name the player, both at the same instant inside a
flags-4/status-16 → flags-5/status-0 transition after 26 s of client silence.
That is a death and respawn. **Zero corrective snaps of a walking player in
1.37 hours.** ArenaNet re-issues a destination or stops the agent; it does not
write positions at a player who is moving.

### The arrival time is an exact formula, and it does NOT predict our teleport

**MEASURED**, build 38797, `0x005FE950`:

```
m_timeStopMovement (+0x48) = m_timeUpdated (+0x58)
                           + floor(dist * 1000 / (maxSpeed(+0x5C) * moveSpeed(+0x60)))
```

absolute milliseconds on the world clock at `AGBASE + m_world*0x64 + 0x148`.

**Applied to the flagship run with no free parameter it is 5.4 s wrong.** Grant
distance 4,515.65 u, moveSpeed 1.0, and the velocity fit pins maxSpeed at
288.0 u/s — that same velocity term tracks the client to **1.3% over 1,864 u**,
so the arm and the speed are right. `floor(4515.65 * 1000 / 288)` = 15,679 ms
puts the jump at **t = 45.57 s**. It happened at **t ≈ 40.13 s**.

Two readings survive, and nothing static separates them:

- **(A)** `+0x58` was stale — it is written from a *cached* clock at
  `0x005FF89E`, not a fresh query.
- **(B)** something client-side re-armed `+0x48` after the grant.

**The keyboard is REFUTED as the re-armer.** `0x0025`'s handler `0x005FD540`
reaches only a facing setter writing `+0xB8`/`+0xBC`/`+0xC0`. The exhaustive
writer census of `+0x48` finds five stores, all in `AgAgent.cpp`: the
constructor, the spawn path, the two inside `0x005FE950`, and the teleport's own
clear.

**`0x0027` DOES re-arm** — `SetMaxSpeed` calls back into `0x00602A40` with the
agent's *current* position — which makes it the cheapest lever we have for
re-aiming a stale grant without sending a teleport. `0x002B` does **not** re-arm,
so our `AGENT_UPDATE_SPEED` before each grant changes nothing about a move
already in flight.

### Why the obvious probe would have been worthless

The first design polled `m_point` (`+0x78`). **It would have reported a teleport
on every ordinary click-to-move.** `+0x78` is not the agent's position — it is
the position as of `+0x58`, advanced only when `0x005FF880` runs, and that has
eight call sites, all event-driven, none per frame. So across a *correct* glide
the trace is flat for the whole leg then steps once onto the destination —
identical to a teleport. It would also have **missed** the real failure: if the
exact-equality tick is ever missed, the agent dead-reckons past its destination
unbounded (no clamp, only assert `AgAgent:978`) while `+0x78` never moves.

That is the third over-fitted claim of this arc, after the bit-exact-landing
rule and the four-term warp precondition. All three had the same shape: a
pattern drawn from the cases studied hardest, then used as a **gate**. The live
position has to be reconstructed —
`(+0x78,+0x7C) + (+0xB0,+0xB4) * (now − +0x58) * 0.001` — and
`toolkit/clientscan/movetap.py`'s selftest refuses to pass unless every term of
it is in the record.

## MEASURED IN THE CLIENT'S OWN MEMORY: the teleport is not a bug (2026-08-19)

`toolkit/clientscan/movetap.py`, two runs, 2,332 samples at 50 Hz. The WOW64 TEB
walk resolved on the first attempt, and `maxSpeed = 288.0` / `moveSpeed = 1.0`
are now **read directly out of the agent** rather than fitted to the wire.

**Seven arrival consumptions** — a sample where `m_point` lands on
`m_targetPoint` (within 1 u) while `+0x48` clears to 0 and the target goes
`+inf`. That is the teleport primitive `0x006020B0` firing:

| jump | armed | fired | error |
|---|---|---|---|
| 98 u | 194118 | 194129 | +11 ms |
| 680 u | 29567 | 29657 | +90 ms |
| 803 u | 197017 | 197032 | +15 ms |
| 2,129 u | 50133 | 50145 | +12 ms |
| 2,743 u | 274733 | 274770 | +37 ms |
| 3,393 u | 158718 | 158751 | +33 ms |
| **5,238 u** | **218272** | **218299** | **+27 ms** |

Every one fires within one 20 ms sample of its scheduled tick. **So the snap is
how the client completes EVERY server-granted move** — the 98 u one is
invisible, the 5,238 u one is "the warp", and they are the same code path.

**`+0x48` is set once at the grant and never re-armed** — reading (B) is
**REFUTED**. In the flagship case it was armed at `t+63.98` to `218272`
("due in +18.09 s", target `(11039.38, 5465.95)`) and fired at `t+82.34`, 18.36 s
later, onto exactly that point, plane 0→18. The formula predicted 18,187 ms
against 18,087 actual — **0.55%, with no free parameter**, using constants read
out of the client.

**So the cause is entirely ours.** We grant a destination 5,238 u away, the
client schedules its arrival 18 s out, the player walks somewhere else, and at
the scheduled instant the client does what it always does. ArenaNet never gets
here because it **re-grants every ~0.5 s** (median inter-grant 0.492 s, 88.5%
triggered by a `0x003D` heading, granting the client's own proposed endpoint plus
0.5 u): its arrival ticks are always half a second out and a few units away, so
the snap is a sub-unit correction that nobody can see. Ours matures for
eighteen seconds.

**A trap for the next reader, and it is why the first probe design was scrapped.**
Most `m_point` jumps in the trace are NOT teleports — they are the cached point
being brought forward by `0x005FF880` when a new grant arrives. Of eleven jumps
over 300 u in the long run, only four are arrivals. The discriminator is not the
jump size: it is **landing on `m_targetPoint` while `+0x48` clears**.

**Still unexplained:** the `--stop-echo` run warped even though the echo fired
9.86 s after the grant and should have overwritten the destination (a
zero-distance move takes the `distSq <= 1.0` short-circuit at `0x005FEA90` and
arrives on the very next millisecond). Under the mechanism now confirmed, that
warp should not have happened. `movetap.py` attached to a `--stop-echo` run
settles it in one pass, and that is the next measurement rather than the next
guess.

## `--heading-grant` REFUTED — my fix caused warps (2026-08-19)

Run `20260819T152716`, `--heading-grant` on, operator spam-clicking distant
ground while holding S. **Two teleports in six seconds, each onto a point this
server had just granted:**

| grant sent | landed | separation | jump | speed |
|---|---|---|---|---|
| t=36.719 `(9591, 8245)` | t=37.000 `(9590.70, 8245.42)` | **0.51 u** | 767 u | 2,719 u/s |
| t=38.903 `(9487, 8786)` | t=39.190 `(9490.63, 8771.30)` | 15.1 u | 752 u | 2,617 u/s |

Both fired **0.28 s** after their grant. The operator experienced it as being
warped *backwards*, and that is exactly right: they were holding S, so the
heading pointed behind them, `pos + heading` was 766 u behind them, and the
grant scheduled a teleport to it.

**The error in the model, which matters more than the flag.** I read `0x0029` as
"tell the client where it is heading". It is not. **It is a scheduled teleport to
that point.** It only looks harmless when the client really does cover the
distance in the scheduled time. Grant a point the player is not travelling
toward at full speed and you have scheduled a warp.

**And rapid re-granting makes it worse, not better.** The arrival distance is
measured from the agent's *cached* `m_point`, which each grant carries forward at
the previous grant's velocity — so the second grant's arrival came due in 0.28 s
rather than the 2.66 s its 766 u implies. Stacking grants does not bound the
teleport; it converts one large one into many small frequent ones. That refutes
"refresh like ArenaNet" **as implemented here**, and it also explains why the
original far-click warp did not reproduce in this session: the flag was
manufacturing its own warps continuously, so no grant ever survived long enough
to mature.

**Why ArenaNet's version works and ours does not.** Their granted point is the
**client's own** proposed endpoint — the client's reported position plus the
client's own vec2, echoed back with half a unit added — so client and server
agree on where the agent is going. Ours is a server extrapolation from a report
already a few hundred milliseconds stale, and the client is asked to be somewhere
it was never going.

**The prediction was met and the conclusion was still wrong.** It said "no
arrival consumption exceeds roughly 800 u"; observed 767 u and 752 u. It bounded
the **size** of the teleports and said nothing about their **number**. A
prediction that cannot fail in the direction the harm actually arrives is not a
prediction — the fourth over-fit of this arc, and the first one where the metric
itself was the mistake.

**Where that leaves the fix.** Three candidates are now dead: suppressing the
grant (retail sends it), echoing on move-cancel (`--stop-echo`, refuted), and
refreshing on every heading (`--heading-grant`, refuted and harmful). What
survives, untried: grant the client's own endpoint verbatim the way retail does —
`reported position + the client's own vec2 + 0.5 u along it` — rather than a
server-computed point, which is a different message from the one tested here.
And the `0x0027` lever, which re-arms `+0x48` from the agent's *current*
position, remains the only measured way to re-aim a stale grant without naming a
new point.

## The live corpus answers §8's question, and §8 asked the wrong axis (2026-08-19)

Method: 9 live captures, all `origin = live` from `wire.jsonl`'s own record and
corroborated by a manifest naming an exe under `vault/run-live/`, framing residual
**0** on every connection in both directions; 44 (capture, connection) series with a
controlled agent resolved from `0x0022`/`0x0037`/`0x003A`/`0x00DA`/`0x00B7` plus
`0x0195`-vs-`0x0020` spawn geometry — an identification that touches neither `0x0029`
nor `0x0025`, so nothing about the grant relation is circular on identity. Four
measurements, each attacked by an independent skeptic who re-implemented the
arithmetic without reading the measurer's scripts; contested quantities re-measured a
third time. Numbers marked **ADJUDICATED** are the third reading and are the ones to
carry.

### 1. The answer, and why the question's two branches both miss

**§8 asked: do retail's heading grants point BEHIND a backward-moving player, and do
those ever produce an impossible-speed step? If they point behind and never warp our
mechanism story is wrong; if they never point behind, the fix is to echo the client's
own vector.**

**Neither branch fires, because both assume the DIRECTION of the granted point is what
separates us from retail. It is not.**

**Against TRAVEL — OBSERVED, they never point behind.** Backward-family headings
(c2s `0x003D`, `movementType` ∈ {4,5,6}) are **64 of 2,675** (2.4%); **64 of 64** drew
a player-directed `0x0029` within 1.0 s, median latency 0.034 s.

| family | n | grants >90° from travel | median angle | max |
|---|---|---|---|---|
| backward {4,5,6} | 44 | **0** | 4.16° | 70.0° |
| forward {1,2,3} | 2,333 | 51 (2.2%) | 2.06° | 180.0° |
| side {7,8} | 41 | 1 (2.4%) | 8.08° | 176.3° |

Reproduced three times to the same rows. A 20-cell filter sweep (`maxdt` 1/2/3/5/∞ ×
`mintravel` 0/4/16/64) returns behind = 0 in every cell, n 13–57; unfiltered it is
0 of 57, and the 16 excluded rows were opened and none is behind.

**But quote the null at cluster level.** The 44 rows sit on **12 connection clusters
in 6 captures** and **31 of 44 come from one capture** (`20260817T231139`). Rows inside
one held-S segment are not independent draws. 0 of 12 clusters gives a 95% upper bound
of **22.1%**, against the forward family's own 2.2% background. **This shows backward
is not different from forward — not that backward is clean.**

**Against FACING — 25 of 29 (86.2%) point behind, and the number says nothing about
ArenaNet.** The skeptic ran the substitution control: delete the server's messages
entirely and score the *client's own* `vec2` against the same reconstructed facing.
Result **25 of 29, median 135.0°** — byte-identical. The 86.2% restates
"backpedalling means moving opposite your facing", which is how the facing
reconstruction was defined. It is a property of the client's message, not of the
server's reply.

**Impossible steps — OBSERVED, zero.** Over the controlled agent's own self-reports:
**0 of 2,565** intervals at `dt ≥ 0.05 s` exceed 400 u/s (0 exceed 390); **0 of 2,524**
exceed 520 u inside 2.0 s. Largest step inside 2 s **517.87 u / 1.352 s = 383.1 u/s**;
largest implied speed **388.80 u/s**, which is 0.75% over the fastest speed the wire
itself ever declares for a player (`0x0027` = 385.92 u/s).

**And the null's recall is 0 of 1.** The corpus's one genuine retail teleport —
`20260817T183756` conn 52294, a 5,376 u `0x002C` hard-set at t=363.324 — is invisible
to this detector, because the client's last `0x003D` on that connection is t=337.242
and none follows. The instrument goes blind exactly where the phenomenon lives, the
same defect as the `--stop-echo` run's null. State exposure in **grants**: **2,830 of
3,098 player-directed `0x0029` (91.3%) land inside a watched interval**; 268 (8.7%) do
not, over 1,503.7 s of a 5,297.8 s corpus.

**So: never behind travel, usually behind facing, never warping — and the fix follows
from none of it.**

### 2. The framing correction that matters more than the answer

**`HEADING_GRANT = False` (`authsrv.py:1026`), set only by an opt-in flag at 9564. In
the default build the heading arm sends NO `0x0029` at all** — only `0x0025`; the
`clip_to_walkable` destination is `state["dest"]`, the server's internal model, and
never reaches the wire. **The teleport the owner watched in the default configuration
therefore arrives through the CLICK arm** (`authsrv.py:7617`, the `clear line` log line
present in both confirmed warp runs), where `dest = values[1]` is the client's own
clicked point verbatim — **which is exactly what retail sends too** (18 of 41 click
grants land on the clicked point to 0.0000 u, 0 at +0.5).

**The difference on that path is not the point. It is that retail's click grant is
superseded within a median 0.490 s by the heading grants that follow, and ours is never
superseded by anything.** That is the strongest available reading of "ours matures for
eighteen seconds". It is a hypothesis under test, not a result — and it is close enough
to what `--heading-grant` tried that the difference must be stated precisely (§4).

**Three of the four dead fixes were aimed at a path that, by default, sends nothing.**

### 3. Our `0x0025` carries a vector 765× too long. It is real, it is fixed, and it is
inert.

Found independently by the orchestrator from our own captures, and confirmed by the
corpus pass from the other side.

| | n | \|v\| p50 | unit-length (<1.01) |
|---|---|---|---|
| Retail, 9 live captures | 3,789 | 0.999593 | **3,789 / 3,789** |
| Ours, 119 vault captures | 4,760 | 766.942 | **56 / 4,760** |

Zero overlap; retail has 0 samples above 100 u, we have 4,704. Decoded from the wire
bytes on both sides. Cause: `authsrv.py` answered a heading with `list(heading)` —
`values[3]` of the client's `0x003D`, a **displacement** of magnitude 765.017–768.000 —
in a field the client reads as a **direction**. The log line beside it formats `:.0f`,
written expecting a large number, so no reader ever saw a `1,0` go past.

**Why it is inert, and the first reason given was WRONG.** "The client normalizes it"
is false for the dominant path. Setter `0x00602660`'s **case 1 (0°, `0x0060267D`) is a
bare dword copy** and **case 4 (180°) is `Vec2Negate` into that same tail**, so for
**3,918 of 4,760 sends (82.3%) the client stored our 765-long vector RAW** at
`agent+0xbc/+0xc0`. What makes it harmless is the consumer: `--field 0xBC --in AgAgent`
finds 7 accesses, and the only float read is `0x005FFA1D`, a **lazy angle cache** —
compare `+0xb8` against the `+inf` sentinel at `0x00948654`, and on a miss load
`+0xc0`/`+0xbc` and call `0x005BCA00`, whose CRT descriptor at `0x00A3E770` reads
`\x05atan2`. **atan2 is scale-invariant**, so the stored angle is identical either way.
It is also not the warp on independent grounds: the `+0x48` writer census finds five
stores and none is on this path.

**Fixed anyway** — one line, matching retail exactly, locked by `test_position_trust.py`
§8 with a control that hands the matcher the defect on purpose. Shipped as a
correctness fix, **not** as a warp fix.

**Two side results.** 56 of our sends carried `facing = 0`; the client's table is
`dec eax; cmp eax,7; ja default`, so 0 underflows to the default and does nothing —
retail never sends 0. And this closes an open question in `studies/smsg`, which flagged
"cases 2 and 3 are ±atan(1/2) = 26.57°, not the 45° a forward-diagonal would suggest"
as an oddity it could not explain: the construction is `normalize(2·v + perp(v))`, a
sqrt-free diagonal, two parts along the heading to one across. `tan a = 1/2` is what
that costs. It was never meant to be 45°.

### 4. What a refuter overturned

**OVERTURNED — the "one displacement quantum, never extended" clamp.** Proposed as an
invariant (`k = |target − report| / |vec2| ≤ 1.001` in 2,689 of 2,689). **REFUTED.**
**ADJUDICATED** under the stated pairing rule (most recent c2s movement message is a
`0x003D` within 1.0 s; n = 2,938 of 3,170 player grants):

| class | n | over one quantum | max \|dest − report\| | max k |
|---|---|---|---|---|
| on the client's ray (\|cross\| ≤ 1 u) | 2,599 | 44 (1.69%) | 1,036.7 u | 1.35 |
| off the client's ray | 339 | 20 (5.9%) | **1,420.3 u** | 1.85 |
| all heading-triggered | 2,938 | **64 (2.18%)** | 1,420.3 u | 1.851 |

Retail exceeds one quantum *on the client's own ray*, so **a hard 768 u cap is tighter
than retail.** Two agents contradicted each other at k = 4.196 / 3,210.2 u; that row
(`20260807T143055` conn 62994, t=146.471) has a `0x003E` click between the heading and
the grant and is a **click** grant. Both were reading real rows from different
populations; the direction of the finding survives every rule.

**CORROBORATED, and killed as a fix — the "+0.500 u" endpoint.** Retail's heading grant
is `dest = reported_pos + vec2 + 0.500·unit(vec2)`. 1,642 of 2,938 (55.9%) sit within
1 u of the client's ray with along-track residual 0.500 ± 0.01; max deviation 0.0025 u,
tracking the float32 ULP by binade. **0 of 2,938 land on the bare endpoint.** The
constant is **additive, not multiplicative**, at 70σ. Present in 8 of 8 captures, every
per-capture median within 4e−5 of 0.500000. **Cite the constant, not the 55.9% — the
rate varies 32.8%–88.3% by session.** It also corroborates the agent identification
rather than depending on it: of 1,642 hits found with *no agent filter at all*, 1,642
land on an independently-identified controlled agent and 0 elsewhere.

**WEAKENED — `0x002C` is not reserved for scene transitions.** 12 in the corpus. 4
address the controlled agent on 3 occasions, all scene events. **8 address other agents,
and 6 of those are mid-session teleports of 1,262–4,633 u with no `0x0021` removals
within ±1 s, on a hard 30.0 s cadence** — a recall or respawn timer, not a transition.
"ArenaNet does not write positions at a moving player" survives **only for the
controlled agent**.

**CONTESTED — `0x002B`'s float as a direction-family speed.** Forward 1.0000 in 627/840
and backward 0.6600 in 47/57 by one attribution rule; backward carrying 1.0000 in 15/69
and ~180 distinct one-off floats by another, i.e. the channel also carries snares and
buffs. **Neither wins on the wire; do not average them.** Settled by `movetap.py` on
`agent+0x5C`/`+0x60` during sustained backpedalling.

**WEAKENED — the `movementType` enum as a metric compass.** The per-value angle table
is **RECONSTRUCTION** and its two advertised controls cannot fail: "the cycle closes to
360.0°" is arithmetically forced (eight random angles also sum to 360.000) and the
"unfitted strafe control at exactly 90.0" reads back its own assignment. Measured
rather than snapped, `1→4` is median 162.5° (n=4) and mt=6 clusters 10° off its
assigned 135°. The **sign** survives a ±20° perturbation; the precision does not. It is
a direction family — anchored independently by the speed split, forward 287.79 u/s
(n=1,493) vs backward 189.51 (n=14), ratio 0.6585 — but it is not an angle table.

**OVERTURNED, in both directions — the `0x0025`/`0x002B` trailing byte.** It is the
`movementType` echo: values {1..8} only, equal to the most recent c2s `0x003D`'s
`movementType` in **2,215 of 2,254 (98.27%)**, the 39 disagreements all adjacent enum
values at transition instants. **Reading it as an ANGLE is REFUTED** — and so is the
follow-on recommendation to rename it in `schema/overrides.json`, which **must not be
actioned**: `facing` rests on ArenaNet's own assert `AgAgent.cpp:2368
'!(facing & ~AGENT_FACING_MASK)'`, a mask-bounded enum is exactly what that implies,
and the schema's field lists carry no field names at all. There is nothing to rename.

**OVERTURNED — the `vec2` magnitude constants are not unexplained.** 765.017474 ..
768.000021 over n=2,675 with **0 above 768.001** (a hard ceiling), dominated by
765.017539 (n=1,456, 54.4%, internal spread 1.4e−4) and 768.000000 (n=367, 13.7%). It
does **not** scale with speed. Filed as mechanism NOT FOUND with `movementType`
specifically excluded — **that exclusion is REFUTED**: mt=1 lands on a discrete constant
in **1,594 of 1,753 (91.2%)** against **168 of 754 (22.3%)** for mt ∈ {2,3}, replicated
within-connection on **17 of 17** connections carrying ≥10 of each.

### 5. Four candidates killed. One survives, and it is not new.

1. **KILLED — "stop extrapolating, echo the client's own vector."** §8's branch 2 is a
   no-op. Retail's expression is `reported_pos + vec2 (+0.5 u)`; ours is
   `state["pos"] + heading`. **The formula is the same.** Confirmed independently by
   two agents from opposite directions.
2. **KILLED, again — "on `0x0047`, echo the client's stop point back."** Re-proposed
   this pass as a new requirement with a counterfactual crediting it with the whole
   effect. **It is `--stop-echo`,** already implemented at `authsrv.py:7716-7730` with
   the recommended opcode, point and latency, and already refuted by the run built for
   it. The grounds for reviving it misread this document: the 9.86 s figure is the
   interval from the *grant* to the echo, not the echo's latency.
3. **KILLED — any direction test, backward special case, or "refuse to grant behind the
   player" guard.** Retail has none: 25 of 29 backward grants point behind facing, up
   to 768.5 u. Such a guard would be wrong on every backpedal — the fifth over-fit.
4. **KILLED — "add the +0.500 u" as the fix.** The constant is real to ±0.00003 in 8 of
   8 captures and is *not* a fix: `+0x48` is a scheduled tick, and 0.5 u moves the
   schedule by **2 ms at maxSpeed 288**, below the 20 ms resolution at which this repo
   verified its seven arrivals. Unmeasurable by our own instrument, against a harm of
   5,238 u. Ship it as a shape detail, never as the change.

**A safety claim struck before it gets built.** "A `k ≤ 1` clamp bounds any warp to
768 u regardless of how stale `p` is" is **false**. The clamp bounds the grant to 768 u
from the `p` *the server holds*, and that is the broken quantity: post-collision drift
is a median 538 u and a max 1,429 u, so the real bound is ~2,200 u. A bound asserted
over the wrong variable is this arc's signature failure.

**What survives:** grant on every `0x003D` while moving (retail does not gate on
"turned"; inter-grant median **0.490 s**, 82.1% of gaps ≤ 1.0 s, n=3,127), from the
client's **just-reported** position, as `0x0025` then `0x002B`-if-the-family-changed
then `0x0029` (retail's shapes: `0x0025`+`0x0029` 48.5%, `0x0025`+`0x002B`+`0x0029`
23.2%, bare `0x0029` 19.1%), clipped short on collision (909 of 2,938 are).

**Standing: UNPROVEN, and it is a refinement of a REFUTED run.** It differs from
`--heading-grant` in the origin term and the moveSpeed term — **and the origin term is
now known to be a no-op.** `_take_client_position` sets `state["pos"] = reported` on
every accepted report, and the heading arm reads `px, py = state["pos"]` immediately
after; the two are equal except on a refusal, which the latch fix made rare and
never longer than 2. **So the surviving candidate differs from the refuted run by the
moveSpeed term and the cached-`m_point` carry, and by nothing else.** A run that
changes more than that at once teaches us nothing about which mattered.

### 6. Still unknown, cheapest measurement each

1. **Which term made `--heading-grant` warp?** NOT FOUND from the wire and *cannot* be
   found there — a cache-free model reproduces every mechanism conclusion equally well,
   so nothing in the carry model is load-bearing evidence. **Cheapest: `movetap.py` on
   `+0x48`/`+0x9C`/`+0x78` across a `--heading-grant` run.** The arrival formula has no
   free parameter and already predicted 18,187 ms against 18,087 actual. **This is the
   next experiment.**
2. **Does `0x002B`'s float track the direction family?** CONTESTED. `movetap.py` on
   `agent+0x5C`/`+0x60` during deliberate sustained backpedalling, wire logged alongside.
3. **The two `vec2` magnitude constants.** Mechanism NOT FOUND, but `movementType`
   stratifies them 91.2% vs 22.3%, 17/17 within-connection. **Cheapest: a controlled
   session holding W alone versus W+A, counted by class.** No memory probe for the first
   cut.
4. **Is `768 = 8 × 96` causal?** UNVERIFIED. The ceiling is exact (0 of 2,675 above
   768.001) but only 10 of 68 distinct integral grant destinations are multiples of 96
   in both coordinates. Treat the terrain-pitch reading as a label, not a measurement.
5. **Retail's off-ray grants.** 339 of 2,938 (11.5%) leave the ray by >1 u; 147 of 339
   (43.4%) have both coordinates integral against 4 of 2,599 on-ray (0.2%), and 74.8% of
   integral destinations are reused points — the same signature in NPC grants. Server
   -authored waypoints. Purpose NOT FOUND, low priority: they are not the player's warp.
6. **The 5 of 12 corpus teleports that land nowhere near a granted point.** Untouched.
7. **Retail's blind budget.** 268 of 3,098 player grants (8.7%) sit outside any watched
   interval, and the detector demonstrably misses the corpus's one real retail teleport.
   Nothing in the corpus buys this back. **Any future warp run must keep the keyboard
   moving through the whole waiting period**, or the instrument goes blind exactly when
   the phenomenon fires.

**Instrument note. Retire the 320 u/s ceiling** used earlier in this arc: it fires on
**505 of 2,565 (19.7%)** of legitimate retail intervals, because it sits below the
383.04 u/s movement-boost mode the wire declares literally. Use `implied speed > 400 u/s
AND dt ≥ 0.05 s` **for the controlled agent only** — retail declares `0x0027` = 399.00
for party-member agents 69 times, leaving a 400 u/s ceiling 0.25% of headroom on those —
plus the dt-free `dd > 520 u within 2.0 s`, and qualify every negative with the blind
budget.

## The warp is a RESYNC, not the `+0x48` teleport — two-sided, simultaneous (2026-08-19)

Run `20260819T171436` (movetap, 61 s, agent 1) against gamesrv capture
`authsrv-20260819T171153-c1.jsonl`, `--heading-grant` ON, operator holding S and
clicking distant ground. **The first run in this arc to watch both sides at once**, and
it overturns the mechanism this document has carried since the arc began.

**CAVEAT FIRST, because it governs how much weight this carries.** The run is **below
`movetap`'s own floor and the tool printed FAIL**: 786 samples against a floor of 7,500.
That is an instrument defect, not an operator error — `movetap` requests 50 Hz and
sustains **12.9 Hz** (p50 sample gap 76 ms), so `floor = seconds * hz * 0.5` can never
be met at the default rate and every run at `--hz 50` fails it. A floor governs a
**null**; this run is not a null (750 of 786 samples carry an armed arrival, and 13
jumps were caught), so the positives below stand and no negative is claimed from it.
n = 7 arrivals, 13 jumps, one 61 s window, one run.

### The two instruments describe the same character and disagree

Matching each client position report to the nearest `movetap` sample by wall clock
(n = 182 pairs inside the window):

| movetap field | p50 | p90 | max |
|---|---|---|---|
| `live` (reconstructed) vs the client's own report | **125.9 u** | 455.7 u | **673.7 u** |
| `point` (+0x78, un-extrapolated) vs the same | 122.1 u | 469.1 u | 632.9 u |

**It is not a reconstruction artifact.** If `live`'s extrapolation were drifting, the
raw `point` would track the wire *better*; the ratio of p50s is **0.97**, and the
extrapolation age is p50 **0.10 s** (p90 0.30). Both fields disagree with the client
equally, so the disagreement is in the client, not in our arithmetic.

**`movetap` reads the SYNC array (`[AGBASE+0xE8]`). The client reports from the copy it
predicts and renders.** This answers the open question `PLAN.md` §8 has carried as
"sync (`+0xE8`) vs async (`+0x14C`) decides whether the model we watch is the one the
player sees": **it is not.**

### The wire's "teleports" are the client re-converging onto the authoritative agent

Every client step > 300 u inside the window, with the separation either side:

| server t | step | separation BEFORE | AFTER |
|---|---|---|---|
| 166.899 | 747.8 u | 537.3 u | 114.6 u |
| 169.368 | 757.5 u | **673.7 u** | **49.5 u** |
| 171.637 | 746.7 u | 567.4 u | 91.9 u |
| 173.756 | 748.8 u | 510.5 u | 152.1 u |
| 218.485 | 753.8 u | 610.3 u | 90.0 u |

**13 of 13**, mean separation **395.1 u → 119.7 u, a 70% collapse**, and the size of the
jump tracks the size of the gap it closes. The largest jump closes the largest gap. A
teleport onto a granted point would show no such relation — and `warpscan` already said
so from the other side without being able to say why: **10 of its 12 detections are
"NOT near any grant"**, because the landing point is on the authoritative agent's glide
path, not at any granted endpoint.

### What that overturns in this document

- **"`+0x48` is set once and never re-armed" — REFUTED as a general statement.** With
  `--heading-grant` on it was re-armed **304 times in 61 s** (7 arms from zero, 7 clears,
  304 re-arms). The original observation stands for a *single click grant*; it was never
  a property of `+0x48`.
- **"Stacked grants come due almost immediately" — REFUTED as typical.** Re-arm lead
  times: min 61 ms, **p10 1,009 ms, p50 2,890 ms**, p90 8,949, max 17,664; **6 of 304**
  under 200 ms and **0** already in the past. Last session's 0.28 s was the tail, quoted
  as the rule.
- **The `+0x48` snap is nearly invisible.** All 7 arrivals landed **0.0 u from
  `m_targetPoint`** with the glide bit clear — so every one took the teleport branch, as
  predicted — and the **visible** jump (`live` immediately before the snap vs the target)
  was **2.4, 4.2, 4.7, 7.0, 12.0, 21.6 and 2.4 u**. The last of those is the decisive
  row: the cached `m_point` was **593.7 u** stale and the player still moved 2.4 u,
  because dead reckoning had already carried the agent to the target. **A stale
  `m_point` does not produce a visible jump.**

**So the mechanism is:** our `0x0029` makes the client's authoritative copy glide to the
granted point at 288 u/s regardless of what the player is doing. The predicted copy
follows the player's input. They separate at roughly the speed difference, and every
~2.4 s the client snaps the predicted copy onto the authoritative one. **That snap is
the warp.** It explains the operator's own observation that it is "easiest to trigger at
longer ranges" — a longer grant is a longer authoritative glide and a bigger gap to
close — and it explains why retail never does it: retail's granted point is the client's
own proposal, so the two copies agree by construction, **and** retail re-grants every
median 0.490 s, continuously re-pinning the authoritative copy to the player's real
motion.

### What it means for the fix

**It does not resurrect any dead candidate on its own terms.** "Echo the client's own
vector" is still arithmetically a no-op — retail's `reported + vec2 + 0.5` and our
`state["pos"] + heading` remain the same expression. But the *reason* the surviving
candidate should work has changed and is now mechanistic rather than mimetic: granting
on every heading from the client's own report keeps the authoritative copy pinned to the
player, so the resync has nothing to close. That is a stronger argument than "retail
does it", and it is testable directly.

**The metric to watch is SEPARATION, not jump size, and no instrument reports it.** That
is the actionable change: `warpscan` scores landing points against granted points, which
is why 10 of 12 came back "NOT near any grant" — it is measuring the right events under
the wrong model. A separation series needs both sides, which this run now proves is
possible.

**Unmeasured, and stated as inference rather than result:** that the same resync drives
the **default-build click warp**. This run had `--heading-grant` on. The mechanism and
the operator's range observation both point that way, and nothing here establishes it.

### Two instrument defects found by this run

1. **`movetap`'s floor is unmeetable.** It sustains ~12.9 Hz against a requested 50, so
   `seconds * hz * 0.5` fails every default run. Either the floor is computed from the
   achieved rate or the default `--hz` drops to something the reader can hold. As it
   stands the tool cries FAIL on runs that measured plenty, which is how a real FAIL gets
   ignored.
2. **`warpscan` names resync events "TELEPORT ... NOT near any grant".** The detections
   are real events; the model behind the label is wrong. Its own "not near any grant"
   line was the evidence, sitting unread in the output for two runs.

### The separation number, re-measured by the instrument (supersedes the hand analysis above)

The table above was scored by hand, pairing each report with the nearest sample
regardless of how far off it was and taking the clock offset from a single
stamp. `toolkit/clientscan/movesync.py` does it properly -- offset estimated as
`max(timegm(wall) - t)` over **8,573** whole-second stamps (truncation only ever
loses fraction, so the max converges from below; the mean would sit half a
second low, and half a second at 288 u/s is **144 units**), and any report more
than 250 ms from a sample dropped rather than stretched.

**183 pairs, 13 resync jumps, mean separation 587.0 u -> 22.3 u: a 96% collapse.**
Carry these, not the 395.1 -> 119.7 (70%) above; the difference is entirely the
pairing gate and the offset, and the hand figures are left in place only so the
correction is visible. Post-jump separations are **1.0 to 59.5 u** -- the resync
closes the gap almost completely, which the loose pairing had blurred.

**Two things that could have refuted it and did not.** Pairing 7 s out of true
collapses only **34%**, so the statistic does not survive its own shuffle. And
the alignment sweep **peaks exactly at the offset the timestamps gave**
(-1.0 s: 39%, -0.5: 85%, -0.25: 95%, **0.00: 96%**, +0.25: 86%, +0.5: 80%,
+1.0: 65%) -- the offset was derived from the stamps and never fitted to
maximise the headline, so the peak landing there is an independent check that
the two clocks are lined up.

**Instrument note.** `warpscan.py` is not retired but it is now the secondary
reading: it scores landing points against granted points, which is the wrong
model for this event and is why 10 of its 12 detections said "NOT near any
grant". `movesync.py` prints the PAIR COUNT before the verdict, for the same
reason `warpscan` prints the TRIAL count.

## The resync explains the DEFAULT-build warp too, from measured positions alone (2026-08-19)

The previous section established the mechanism with `--heading-grant` ON and
flagged the generalisation to the default build as **inference, not measurement**.
This closes it, retrospectively, over captures already in the vault, with no
client run.

**NO GLIDE RECONSTRUCTION, deliberately.** The obvious retrospective test is to
integrate the authoritative agent forward from each grant at 288 u/s and compare.
That stacks four assumptions -- a speed, a straight line, no collision, an
arrival rule -- underneath the conclusion. None is needed, because of one
measured fact from the two-sided run: **the position the client reports
immediately after a resync sits 1.0-59.5 u from movetap's reading of the sync
agent** (n=13, mean 22.3). A landing point is therefore a *reading* of the
authoritative agent. So the test uses three measured quantities -- the landing,
the client's own reported position when we granted, and the point we granted
(decoded from the logged wire bytes, filtered to agent 1 because NPC grants share
the opcode) -- and asks pure geometry: does the landing lie on the segment
between the other two?

`toolkit/clientscan/movesync.py --wire-only`. Two gates run before any verdict:

| capture | build | cadence | jumps | perp p50 | CONTROL p50 | on-path | control on-path | grant age p50 |
|---|---|---|---|---|---|---|---|---|
| `20260819T145717` | **default** | 0.25 s | 31 | **43.9 u** | **744.8 u** | **18/30** | **0/31** | **5.84 s** |
| `20260819T171153` | heading-grant | 0.29 s | 32 | 2.8 u | 119.1 u | 24/32 | 9/32 | 0.32 s |
| `20260819T113105` | default | 2.75 s | 24 | 80.3 u | 108.2 u | 9/20 | 8/24 | 1.20 s |
| `20260819T145421` | default | 0.25 s | 6 | 8.2 u | 21.5 u | 2/3 | 3/6 | 10.09 s |
| `20260811T173940` | default | 1.28 s | 5 | — | — | **no player grants at all** | | |

**The verdict rests on the top two rows and only those.** The other three cannot
carry it and say so rather than being quietly averaged in:

- `113105`'s report cadence is **2.75 s**. The client emits `0x003D` only while
  moving, so at 288 u/s it travels ~790 u between reports and **57% of its
  intervals clear the 300 u jump bar** -- the jump population is contaminated
  with ordinary walking. Its control duly scores as well as its treatment
  (108.2 vs 80.3, 8/24 vs 9/20), which is the gate earning itself rather than a
  refutation. `--wire-only` now refuses a verdict above 0.5 s cadence.
- `145421` has n=3.
- `173940` has **5 jumps and zero player grants**. This model says nothing about
  those and they remain unexplained; see below.

**On the two captures whose data can carry the test, it holds.** The default
build's discrimination is the stronger of the two: **43.9 u against 744.8 u, and
18 of 30 landings on-path against 0 of 31 for an unrelated grant.** The
corpus's biggest warps are in it and they land where the model says:

| t | step | perp | frac | grant age |
|---|---|---|---|---|
| 224.770 | **3,166 u** | 19.0 u | 0.980 | **18.77 s** |
| 164.527 | 2,583 u | 0.0 u | 1.000 | 12.41 s |
| 293.523 | 2,234 u | 8.4 u | 0.518 | 21.54 s |

A 3,166 u jump landing 19 u off a line drawn to a point granted **18.77 seconds
earlier** is the flagship warp profile, and it is on the granted path.

**THE NUMBER THAT MATTERS FOR THE FIX is the grant age at the jump.** Default
build **5.84 s median, 56.17 s max**. `--heading-grant` **0.32 s**. Retail
re-grants at a median **0.490 s**. So the default build leaves a grant
outstanding an order of magnitude longer than retail ever does, and the
authoritative copy glides along it the whole time.

**But cadence alone is NOT the fix, and this is the constraint that kills the
easy answer.** `--heading-grant` held grant age to 0.32 s -- *faster* than
retail -- and still warped, with mean separation 587 u before each resync. So a
grant that is fresh but points somewhere the player is not going diverges just as
surely as a stale one. **Both terms are required: the granted point must be where
the player is actually going, AND it must be refreshed.** Retail does both; each
of our two configurations does exactly one.

**Still unexplained: `173940`'s 5 jumps with no player grant preceding any of
them.** If nothing we sent steered the authoritative copy, this mechanism cannot
be what moved the player. That capture is sparse (28 reports, 1.28 s cadence) so
some of the 5 may be ordinary walking mis-scored, but the count is not zero and
it is not explained. It is the same open population as the "5 of 12 corpus
teleports that land nowhere near a granted point" recorded earlier in this
document, and it is now the largest remaining hole in the mechanism.

**A correction to my own method, recorded because the failure was instructive.**
The first version of this test also predicted that the position just *before* a
jump would sit further from the segment than the landing. It came back **0.0 u
for almost every row**, which read as a refutation and was a tautology: where
grants outnumber reports, the "client position at grant time" is often the *same
record* as the pre-jump position, so it lies on its own segment by construction.
Those rows are now counted and reported (`origin==pre-jump record`: 28 of 32 in
`171153`, 11 of 30 in `145717`) and no claim rests on them. The surviving half of
the test -- the landing against the segment -- never depended on it.

## `--client-endpoint` REFUTED, and it is the worst of the three (2026-08-19)

Run `20260819T182652`, `--client-endpoint` on, operator holding S and clicking
distant ground. **Scored against the prediction stated before the run**, which had
two parts precisely so it could fail in the direction the harm arrives:

| | bound | observed | |
|---|---|---|---|
| FREQUENCY | under 2 jumps/min | **14.6/min** (16 in 65.6 s) | **REFUTED** |

For comparison in the same units: `--heading-grant` **12.8/min**, the default
build **5.7/min**. **Both of my candidate fixes are worse than shipping nothing**,
and this one is the worst of the three. The default build remains the best
configuration this repo has.

**The mechanism is confirmed a third time, which is not the consolation it
sounds like.** 12 of 16 landings on the granted path, perpendicular offset
**7.5 u** against **338.9 u** for an unrelated grant, grant age at the jump p50
**0.28 s**. So the fix satisfied both terms it was designed for -- the point was
the client's own unclipped endpoint and it was refreshed faster than retail -- and
the character warped more, not less.

### What the run says is actually wrong, and it is not the point

**The player was moving at a median 111.7 u/s (p25 88.7, p90 282.2) while we told
the client its moveSpeed was 1.0, which is 288.0 u/s.** A 2.6x mismatch, sent on
every grant. The authoritative copy glides at the speed WE name toward the point
we name; the predicted copy moves at whatever the player's input and the client's
own collision produce. Nothing in any of the five candidates addressed that.

**But the obvious quantitative form of that claim does NOT hold, and it is
recorded as a failure rather than trimmed.** Predicted: separation grows at
exactly `288 - (the player's own speed)`, no free parameter. Measured over the 13
growth runs between resyncs in the two-sided capture: **mean predicted 179.6 u/s,
mean observed 124.8 u/s, mean |error| 93.2 u/s**, per-run errors from -165.8 to
+91.1. Separation does grow, and the speed mismatch is real and large -- but
"288 minus the player's speed" over-predicts it by about a third and scatters
wildly. Two reasons are visible and neither is quantified: the authoritative agent
ARRIVES and stops until the next grant re-arms it, so its average speed is below
288; and separation is a vector distance, so it depends on the angle between the
two copies' travel, not only on the speed difference. **Speed is a major term. It
is not the whole model, and this document does not claim it is.**

### The structural read, after five failures

All five candidates were variations on **what point to grant**. The measurements
now say the point is not the free variable: every configuration grants something
765 u away, and the authoritative copy then glides toward it at a speed the server
chose rather than the speed the player has. **The server cannot know the player's
instantaneous speed and the client can** -- it is the product of input the server
never sees and collision the server models differently.

That suggests the next intervention should be a **subtraction rather than an
addition**, which every one of the five was. The default build's remaining warps
come from a click grant left outstanding a median 5.84 s; the candidate primitive
is `0x0028 AGENT_STOP_MOVING`, which would CLEAR the outstanding destination when
keyboard movement begins rather than re-aiming it. Untested, and deliberately not
shipped in the same breath as this refutation.

**Recommendation until then: ship the default.** `--client-endpoint` and
`--heading-grant` both default to off and both should stay off. Neither is a fix
and both are measurably harmful.

---

## 2026-08-19, later — the corpus pass on the handoff's list

Twelve agents over the full corpus (14 live dirs, 49 game connections, framing
residual 0 on 98/98 connection/direction rows; all 961 gamesrv files, 2,024,792
`sent` records), three analysis lanes each attacked by an independent skeptic who
re-derived the load-bearing numbers with their own parsers. Everything below is
what SURVIVED that; where a first-pass number died, the death is recorded next to
the survivor. Player agent per retail connection: `0x0037` primary, corroborated
by `0x00DA`/`0x00B7`, 48/49 resolved, 0 disagreements — and cross-checked with an
id-free signature (|grant dest − last self-report| p50 765.52 u for the player vs
2,186.97 u for every other agent).

### Handoff §4 item 1 is ANSWERED: retail does NOT stop on keyboard onset

**No `0x0028`.** 580 keyboard onsets (a c2s `0x003D` after >1.0 s of silence),
499 with a player grant outstanding: terminated by a superseding `0x0029` in 496,
by `0x002A` in 2, by `0x0028` in exactly 1 — and that one sits in the same segment
as a `0x00F1` status change and a `0x01A5 GAME_SERVER_TRANSFER`, i.e. a zone
transition. An injection control (a synthetic `0x0028` planted 20 ms after every
onset, same classifier) reports 496/499, so the zero is ArenaNet's, not the
code's. Population honesty, per the verifier: 492 of the 499 outstanding grants
were HEADING grants; the literal click-outstanding case is 5–11 episodes — all
superseded by `0x0029`, none stopped, latency 0.029–0.063 s. Retail's 95
player-directed `0x0028` (of 282 all-agent) are STATE messages: zone transfer /
status / skill at 48% union coverage vs ~7% in a matched control, and they show
no timing relationship to keyboard onset (within 1 s after an onset: 4.61% of
onsets vs 4.15% of uniform random moments). Retail's shape is SUPERSESSION — a
fresh grant answering the heading itself at one RTT (p50 0.035 s), steady-state
gap p50 0.491 s — and its only genuinely subtractive move is a ZERO-LENGTH grant
answering the client's own c2s `0x0047` cancel (96 of 114 answered, 70 landing
<5 u from the reported stop; that is dead candidate #2's shape, with the
difference that retail's is a REPLY to a client cancel, not a destination planted
at every stop). **The §4-item-2 subtraction branch does not open. Do not build
the `0x0028`-at-onset fix** — it would introduce a message we have never sent
(0 of 2,024,792) for a purpose retail does not use it for. And do not build the
supersede-every-heading replacement either: that IS candidates 3 and 5, and the
leash measurement shows both already ran TIGHTER than retail (p90 100.7 / 96.0 u
vs retail's 384.4 u, retail-length legs) and warped more. Retail's leash is
bracketed from both sides; **the point is not the free variable**, now measured
rather than argued.

### Handoff §4 item 4's capture half is CLOSED: an instrument artifact, and the arc's own trap

`20260811T173940`'s five "jumps with zero player grants" were **stop-to-stop
displacements of a client that walked the whole way.** Until 2026-08-19,
`position_report` was emitted from the `0x0047` arm ONLY (28 rows in this
capture, paired 1:1 with the 28 stops to within 0.1 ms, all `source=None`); the
130 c2s `0x003D` rows carrying the client's position between stops were invisible
to movesync. Spliced (158 rows, cadence p50 0.251 s instead of 1.284 s), the five
jumps read 74.4 / 196.5 / 10.0 / 122.3 / 243.3 u/s — 0 of 5 above the 288 u/s run
speed; largest inner step 512.6 u over 1.801 s = 284.6 u/s. The verifier
re-derived all of it with its own parser and closed the remaining blind spots:
displacement across every client silence ≥2 s is EXACTLY 0.0 u (bit-identical
positions both sides), and `0x003D` field 1 is a live position, not a cache
(heading[i] predicts the realised displacement to i+1 at p50 5.6°, 0/107 beyond
90°, vs 33.5° for a shifted control). The capture's 107 `0x0025` sends are all
bit-exact echoes of the client's own preceding heading at p50 0.22 ms — the
server expressed no intent of its own. **The `movesync` number that created this
hole was quoted from above its own REFUSING-a-verdict line** (1.28 s cadence >
the 0.5 s bar); when a tool refuses, the count it printed above the refusal is
refused too. The artifact is broad: movesync's 300 u rule reports jumps in ~30 of
the 50 legacy (stop-arm-only) captures; the spliced stream shows impossible steps
in only 5 of them.

**The corpus half of item 4 is NOT closed and has GROWN.** warpscan (which globs
`vault/captures/gamesrv` only — the old "12 corpus teleports" phrasing misread as
retail) now shows **26 unattributed detections that are kinematically impossible**
(⚠ implied velocity, RETIRED in the round-3 section below — quote magnitude and
excess over the 288 u/s budget, excess p50 671 u / max 3,804 u over n = 43
detections; the numbers this line carried were v p50 2,521 u/s, max 23,279 u/s)
across 7 of our captures — including 1 in the
default-build `145717` and 10 in `171153`. 15 of the 26 sit in a tight 729–768 u
band at dt ≈ 0.30 s — suspiciously the length of the `0x003D` heading vector —
but that is one measurement's worth of lead, not a hypothesis.

### The `0x002B` contest RESOLVES — both rules were right about different factors of one product

`0x0029` was never the place to look: its layout is `[hdr, dword agent, vec2,
word, word]` — **no speed field.** Retail's speed is a two-channel product:

- **`0x002B AGENT_UPDATE_SPEED`** carries `direction_factor × modifier`:
  1.00 forward / **0.66 backward** / 0.75 side, times a snare in [0.01, 1.0].
  Locked to the message's own trailing byte with **0 violations in 1,049
  player-directed rows** (0.66 on backward bytes 46/46, 0.75 on side 55/55, 0.33
  on forward 44/44; 1.0 never on a back/side byte, ~74 expected under
  independence). The product structure is carried past n=1 by a family-ceiling
  test: all 6 backward one-off floats ≤0.66 where 81.7% of forward one-offs
  exceed it (p = 3.7e-5), all 5 side one-offs ≤0.75 (p = 1.1e-3), and the one
  bit-decidable case (0.2178 = f32(0.66)×f32(0.33), one ULP off a literal) sits
  on a backward byte. Rule B's "backward carries 1.0 in 15/69" reproduces (16/69)
  and is a JOIN-LAG artifact: all 16 carry a non-backward own byte (13× byte 9,
  which follows a c2s `0x0047` in 86/86 and is always float 1.0). Rule A's exact
  arithmetic (627/840, 47/57) is NOT recoverable — 47 backward-at-0.66 exceeds
  the 46 that exist player-directed — but its substance holds (own-byte
  attribution: 597/849 forward, 46/52 backward).
- **`0x0027 AGENT_UPDATE_SPEED_BASE`** carries the absolute base in u/s: 288.00
  ×65, **383.04 ×76** (the boost), 385.92/325.44/230.40/191.52/144.00 tail, over
  153 player-directed sends. 23–24% of retail's player movement intervals run at
  a non-288 base (measured p50 ~381 u/s). Buffs live here, not on `0x002B`
  (which the client asserts into [0.01, 1.0]) — value-vocabulary inference, not
  a disassembled handler.

The backward VALUE is confirmed by a third record type: sustained same-family
c2s windows give 287.9 u/s forward vs **189.78 u/s backward, ratio 0.659**,
against 288 × 0.66 = 190.08 predicted (0.16% error), floor-independent. The side
factor 0.75 is wire-declared, displacement-UNCONFIRMED (8 intervals,
turn-contaminated). The family partition {1,2,3}/{4,5,6}/{7,8} is
displacement-earned for forward and mt=4; mt=5/6 ride on the wire lock alone.

**Ours: `0x002B` = 1.0 in 621/621 player sends; `0x0027` sent 0 times ever.** And
our runs backpedal 23–82% of the time against retail's corpus at 2.4% — the
retail corpus under-samples exactly the input that reproduces our bug.

**⚠ THE CAUSAL STEP DID NOT SURVIVE, and this is the pass's most important
negative.** The displacement measurement was offered as the independent arm, and
our own corpus is its confound: **we send 1.0 always and our client STILL
backpedals at ~186 u/s (0.642–0.668 of forward) in 8 of 12 runs** — the 0.66
factor is applied CLIENT-SIDE to the predicted copy regardless of the wire float.
So the corpus settles the VALUES and cannot settle whether writing a non-1.0
rate steers the authoritative copy. That question needs either the client run
(movetap on `+0x5C`/`+0x60` during sustained backpedal on a build that sends
`0x002B(0.66, byte 4)`) or static analysis of the client's `0x0027`/`0x002B`
handlers — `msghandler.py`/`codescan.py` exist and no one has opened the binary
for this. Also FALSIFIED in passing: "retail's `0x002B` is edge-triggered on the
family change" — 72.2% of 1,008 consecutive player `0x002B` pairs carry the SAME
family (36.9% identical family+float), median gap 0.518 s. It re-sends at report
cadence.

### TWO NEW STRUCTURAL FINDINGS, both from the verifiers

**1. The scoreboard metric cannot tell retail from our worst build.** Retail's
own client reports, run through our 300 u jump detector: **440 "jumps" = 6.4/min
on span** — nominally worse than our default build's 5.7 — while having **ZERO of
2,665 intervals above 400 u/s** (max implied speed 388.8 u/s, just over the
383.04 boost the wire declares). Our builds by the same speed-gated detector:
**7 / 20 / 13** impossible intervals — corrected 2026-08-19 from 7 / 19 / 11 when
the hard bar gained its distance arm — with magnitudes p50 **1,969 / 569 / 582 u**
and max **3,405 / 768 / 754 u**. (This line used to quote implied maxima
6,334.8 / 4,177.3 / 2,671.0 u/s; the restored rows push two of those to 19,046 and
23,279, which is exactly why the velocity is retired below and magnitude and excess
are the quotable pair.)
That is the cleanest retail-vs-us separation in the arc, and it means the 300 u
bar (movesync's `JUMP_UNITS`, no time normalisation) counts ordinary walking:
23 of the default build's 31 "jumps" are ≤288 u/s, and 69% of its rate
denominator carries no reports at all. **Speed-gated, the three configurations
read 1.31 / 5.69 / 11.88 hard jumps per minute of span** — repaired 2026-08-19
with the bar's distance arm, n = 7 / 20 / 13; the pre-repair pass read
~1.3 / 5.4 / 11.9 (against the recorded 5.7 / 12.8 / 14.6;
also note 9.1/min reproduces for `171153` where the record says 12.8 — same
contaminated metric, different denominator — restate both, pick neither). Every
number a candidate has been scored with inherits this; a sixth candidate scored
against a 5.7/min bar is scored against noise.

**2. The default build's authoritative copy is mostly PARKED, not gliding.**
movetap run `145939` sits INSIDE default-build capture `145717` (39 of its 40
grants in-window). Joined to the family stream: during backward stretches the
authoritative copy is MOVING in only **109 of 274 20-ms intervals (39.8%), mean
114.57 u/s** — on average SLOWER than the client's 186, not 102 u/s faster. Its
duty cycle tracks the grant rate monotonically across all five movetap/gamesrv
pairs: 2.9 grants/min → 0% moving, 8.5 → 12%, 13.0 → 40%, 190.9 → 91%, 336.7 →
98%. So in the DEFAULT build the separation is generated by **the client walking
away from a mostly-parked authoritative point**, and a moveSpeed multiplier on a
parked object changes nothing for the fraction of time it is parked. The "gap
102 u/s → 300 u in 2.94 s" harm arithmetic asserted 288 u/s as the copy's speed
from movetap's FIELD values (+0x5C/+0x60 read 288.0/1.0 in 4,115/4,115 samples —
true, and not a displacement); it is refuted as arithmetic, though the fix's
direction may survive. This also explains a third of the old "288 − player
speed" model's failure without new parameters.

### What this hands the sixth candidate

The VALUES are ready and are the best-evidenced numbers in the arc: backward
0.66 (send the literal wire float `c3f5283f`), side 0.75, base 288.0 on `0x0027`
at spawn (its own change, never folded in), retail's order speed-before-point,
re-send at report cadence not on edges. **The CAUSAL STEP is not ready**: it is
grounded in nothing our corpus can see, the one paired movetap join points the
other way (parked copy), and — the critic's sharpest point — **nobody has
measured what triggers the snap.** If the resync is timer-driven, slowing the
copy shrinks magnitude and leaves rate untouched: the arc's own named failure
mode, again. If it is threshold-driven, a speed term buys rate. The five movetap
runs already hold the answer (inter-snap interval vs separation-at-snap) and it
has never been computed. A candidate chosen because it matches retail's wire is
also the common ancestor of dead candidates 3, 4 and 5 — retail-shape imitation,
not "addition", is the recurring parent.

**The order of work, all corpus/offline before any client run:**
1. Compute the snap trigger from the five existing movetap runs — timer vs
   threshold decides whether ANY separation-rate fix can bound frequency.
2. Re-derive the default build's own separation (p50/max, by family) and snap
   cadence from movetap `145939` ⊂ `145717` — the harm has never been measured
   on the configuration being fixed; the 150 u bound quoted everywhere is
   imported from a refuted configuration.
3. ~~Rebuild the scoreboard speed-gated (and fix movesync: read the spliced
   `0x003D`+`0x0047` stream the way warpscan already does, print the honest bar
   — at 288 u/s a 300 u step is free above 1.042 s of silence — and print the
   MAX cadence, not only the p50; pin `JUMP_UNITS` with a test).~~ **DONE
   2026-08-19**, and the repair found a fifth defect the list did not name: a
   speed-only bar is DISTANCE-BLIND below its own dt floor and was discarding the
   corpus's three fastest genuine events. The bar now has two arms (speed
   > 400 u/s at dt ≥ 0.05 s, distance ≥ 520 u below it), 61 → 64 hard rows over
   961 captures, and every constant is pinned by `test_movesync.py` (102 checks,
   floor 57).
4. Static-analyse the client's `0x002B`/`0x0027`/`0x0029` handlers
   (msghandler/codescan) to decide whether a non-1.0 rate steers the sync copy
   — the cheapest unspent instrument; it may retire the client run entirely.
5. Adjudicate the 26 impossible-step population (item 4's live half).
6. ~~Fix `pinned.py` before the next live run needs it: the recorded `patched`
   hash predates the current patcher (three extra sites), 38833 has no patched
   hash at all, so movetap's gate refuses a legitimately patched 38797 and
   cannot represent 38833.~~ **DONE 2026-08-19, by the first of the two named
   directions**: `Build.patched` is a per-build TUPLE of accepted digests (the
   current patcher's 38797 copy and both 38833 copies committed), and
   `make_custom_client.py` and `make_run_dir.py` register what they write into
   `vault/client-patched/patched_digests.json` after their own verification.
   The loosening is gated in the direction that matters — a digest equal to any
   known build's pristine is refused with no `--force`, `strict` refuses what it
   cannot diff against a pristine image, and every registry row is re-validated
   on read — with each refusal mutation-proven (`test_pinned.py` 143 checks,
   floor 130; `test_buildid.py` 42, floor 39).

### Corrections to the record found in passing

- FINDINGS above (:1340): corpus-wide base rates are now **282 / 95 / 114**
  (0x0028 all / 0x0028 player / c2s 0x0047) over all 14 dirs, superseding
  257 / 81 / 88 (9 captures).
- The "12 corpus teleports / 5 near no grant" population is GAMESRV (our runs),
  not retail, and is now 43 / 26.
- `PLAN.md` §8's header said "FOUR fixes dead" over a body that counts five, and
  its "+0x48 is set once and never re-armed" line predates its own refutation
  (:1851). Both fixed this pass.
- The scored-run measurements `analyze_movement.py` greps labels for
  (`keyboard`/`click`) do not exist in the corpus — all 40 default-build grants
  are labeled `AGENT_MOVE_TO_POINT(... clear line)`.
- Guide-level: `codec.decode_one` returns a THREE-tuple `(opcode, values,
  nbytes)`; unpacking two inside a broad `except: continue` silently zeroes a
  census (it did, once, mid-pass, and was caught by a row count).

---

## 2026-08-19, round 3 — THE MECHANISM IS DECODED, AND THE SPEED CANDIDATE IS DEAD

Four measurement lanes (snap trigger, separation budget, the impossible-step
population, client-handler statics), each adversarially re-derived by an
independent skeptic who re-parsed from raw bytes with its own reader. **The
empirical and the static lane converge on one mechanism from opposite
directions, and neither knew the other's result.** Everything below is what
survived; refuted headlines are recorded beside their replacements, because
three of this round's first-pass claims died in verification.

### THE SNAP, named in the binary

Client read: `vault/client/2026-07-29_221c13772c7a/Gw.exe`, build 38797
**pristine**, sha256 `221c1377…` (the `run/` copy differs in 9 spans, 5 in
`.text` — a 37-byte cave at VA 0x004514E2 plus an `e9` detour at 0x007DC0CE —
and no address quoted here lies in any patched span). ArenaNet's own assert
strings name the structure: `syncPtr` = `[agentMgr+0xE8]`, `asyncPtr` =
`[agentMgr+0x14C]` (`AgMsg.cpp`); agent `+0x24` = `m_world` (0 = WORLD_SYNC);
each world carries its own clock at `[agentMgr+0x148 + m_world*0x64]`;
`+0x48 m_timeStopMovement`, `+0x5C maxSpeed`, `+0x60 moveSpeed`, `+0xC4 facing`,
`+0xB0/+0xB4` **velocity in u/s**, `+0x78` epoch position, `+0x58` epoch time.

**The snap is `0x006022B0`, and it copies SYNC → ASYNC.** Proven at the call
site (`edi` = agentMgr+0x1CC, so `[edi-0x80]` = asyncPtr and `[edi-0xE4]` =
syncPtr): the async agent becomes `this`, the sync agent is pushed as the
source. The body stops the destination, computes `syncPoint` (the source's
`+0x88` destination if it has arrived, else a dead-reckon on the DESTINATION's
world clock), and calls `0x00602B20` — a hard SetPosition. **The predicted copy
the player sees is dragged onto the authoritative one**, exactly as the arc's
model said, now with an address.

**THE TRIGGER — and it settles the timer-vs-threshold question by making both
answers half right.** `0x00605FC0` (subsystem `agentMgr+0x1CC` =
`AgTrack.cpp`, the client's own prediction tracker) has **exactly 3 callers —
0x005FEBEB (inside the grant bake), 0x006022A1, 0x00602BBD — all
message-driven. The desync test is NEVER evaluated per frame.** When it does
run it calls the compare `0x006055E0`, which:
1. asks whether one of the client's **outstanding predicted commands MATCHES**
   the server's grant (per-record test `0x00605AF0`, constant 100.0 @0x00946560)
   — if so it returns 1 and **nothing snaps**;
2. otherwise dead-reckons the sync agent on the sync clock and the async agent
   on the async clock and asks `Map.cpp`'s path query `0x00709990` for the
   distance between them, compared against **300.0f @0x00946564**
   (`006057BF fld [0x946564]` … `006057EA jne` → over 300 returns 0);
   ⚠ **CORRECTED 2026-08-20: this gate is STRAIGHT-LINE, not walkable path.**
   `0x006057C8 push 1` sets `0x00709990`'s `straightOnly` argument, and
   `0x00709B3F` jumps back to plain `sqrt(dx²+dy²)` on it. The walkable-path
   conjunct is the *100 u* test at `0x00605C40`, which pushes **0**. This line
   said WALKABLE for a day; the two thresholds use the same function in
   opposite modes, which is exactly how it went unnoticed.
3. returning 0 drops `0x00605FC0` into the loop (inlined at 0x0060604C) that
   resyncs **every** async agent onto its sync twin.
Below 300 two further geometric checks (`0x00709E90`, `0x005FEF70`) can still
force the snap. A second entry exists with no compare at all: `0x005FCAA0` →
`jmp 0x00605E40`, callers 0x004E6E82 / 0x00816499 / 0x0081655D. **Not** the
snap: opcode `0x0023`, whose handler only logs *"Agent %u position out of sync
with server"*.

**So there IS a 300 u threshold, and it is not free-running.** That is why the
empirical lane refuted "threshold" and was right to: in the default build the
client sat **127 intervals / 93.4 s at separation p50 1,522 u, max 3,648 u,
with ZERO convergences** — because no grant arrived to make anything look. And
it is why "timer" dies on crossing brackets (default: no convergence across a
33.8 s separated stretch ⇒ T > 33.8 s; capture 152716: longest inter-convergence
gap 2.2 s, p50 2.0 s, CV 0.09 ⇒ T ≤ 2.2 s). Empirically the fired events are the
authoritative copy's **START** and **ARRIVAL** transitions — default build
exposure-weighted: PARKED 0.00/min over 93.4 s | MOVING-no-transition 1.10/min
over 54.5 s | START inside 12.52/min over 14.4 s | ARRIVAL inside 15.96/min over
15.0 s; 7 of 8 convergences sit in the 16.6% of exposure carrying a state change
(binomial P = 2.4e-5; pooled 16 of 28 in 11.5%, P = 7.1e-9). Arrival lift:
`+0x48` due within 500 ms of an interval's start converges 11/23 vs 11/393,
**17.1×**, n = 416 — and the association survives dt-matching (7/11 vs 1/167).
A grant that re-arms an ALREADY-MOVING copy does **not** snap it (2/33, 15/304,
4/103 against shuffle base rates of 6-9%) — consistent with the static read,
where a matching pending command returns 1.

### SPEED IS BAKED AT GRANT TIME — the glide never reads it

- **Q1. `0x002B` writes the SYNC agent ONLY, and is a pure store.** Handler
  `0x005FD9D0` reaches `[esi+0xe8]` and nothing else; setter `0x00602990` is
  three asserts then exactly three stores — `or [esi+0x20], 0x80000`,
  `mov [esi+0xc4], edi` (facing), `fstp [esi+0x60]` (moveSpeed) — and `ret 8`.
  It touches no tick, no velocity, no position. The `+0x48` writer census in
  AgAgent returns 4 stores and `0x00602990` is not one of them.
- **Q2. The dead-reckoner `0x005FFB40` is, in full,
  `out = [+0x78] + ([+0xB0],[+0xB4]) * ((t - [+0x58]) * 0.001)` plus a
  world-bounds clamp. `+0x60` and `+0x5C` do not appear.** Speed enters only at
  the bake in `0x005FE950`: `fld [esi+0x60]` × `fmul [esi+0x5c]` → the arrival
  tick `+0x48 = +0x58 + trunc(dist*1000/(maxSpeed*moveSpeed))` (clamped ≥ 1) and
  the velocity `+0xB0/+0xB4 = unit(d) * speed`. The zero-distance branch
  (dist² ≤ 1.0) snaps to dest, zeroes velocity, sets `+0x48 = now+1`.
  **⇒ H1-WEAK: a mid-flight `0x002B` changes the number the NEXT grant bakes and
  nothing about the current leg.** The FINDINGS arrival formula is byte-exact.
- **Q3. `0x0027` is the lever we have never pulled.** Handler `0x005FD700`
  applies setter `0x00602910` to the SYNC agent **and then again to the ASYNC
  agent**. The setter settles (dead-reckons to now, rewrites `+0x78`, sets
  `+0x58 = now`), stores `+0x5C`, and then — if in-world and the existing target
  `+0x9C` is valid — **re-issues the outstanding grant** (`0x00602A40` →
  `0x005FE950`), re-baking velocity and re-arming `+0x48` from the *current*
  speed product. That is the whole of FINDINGS:1385: `0x0027` re-arms because it
  replays the grant; `0x002B` is a store.
- **⚠ THE LEVER LIST, and the gate that kills the obvious fix.** Per-handler
  census of the 18-row recv table at 0x00A52D70 — SYNC-ONLY: 0x0021, 0x0022,
  0x0023, **0x0029**, 0x002A, **0x002B**. BOTH copies: 0x0024, 0x0025, 0x0026,
  **0x0027**, **0x0028**, **0x002C**, 0x002D, 0x002E, 0x002F. The first-pass
  conclusion — "we only send SYNC-ONLY messages; add a `0x0025` beside each
  grant" — was **REFUTED twice by the verifier.** (a) It is not a change: we
  already send 187 × `0x0025` in the 5.80 min default run (32.2/min, 4.7× the
  grant rate; 411 and 184 in the other two). (b) **`0x0025`'s async arm is GATED
  and the gate closes on the player**: `0x005FD5CD` skips it when the agent holds
  a pending AgTrack record, and `0x005FD5D3` (`cmp ebx,[esi+0x1e0]`) skips it
  when the agent id IS the client-controlled agent — `[mgr+0x1E0]` = AgTrack+0x14,
  written at 0x00605F45 when the client registers its own local move, cleared
  only on agent removal. **Once the player has moved locally, a server `0x0025`
  for their agent writes the sync copy only.** The same gate sits on 0x002D and
  0x002E; it does **not** exist on 0x0024, 0x0027, 0x0028 or 0x002C, whose async
  arms are unconditional.
- **`0x002C` is the clean primitive**: handler `0x005FDA50` calls `0x00605F70`
  = `AgTrack::Clear(agentId)` (zeroes the pending-record head/tail at
  0x00605FA7/0x00605FAE) and then `0x00602B20` SetPosition **twice, once per
  array**, with no `[esi+0x1e0]` gate on either arm.

### THE SEPARATION BUDGET — the copy is not slow, it is OFF

Forward simulator of the authoritative copy driven **only by our wire**
(0x0029/0x002B/0x0027/0x0028/0x002C), using the binary's own model; calibration
against movetap `|sim − live|` p50 0.0-13.0 u, max 72.2 u while the copy travels
3,000-23,000 u (conditioned on the copy actually gliding: p50 21.5, p90 49.7).
`0x0025` was **excluded because including it made the residual 11× worse**
(p50 133 → 1,451 u) — an independent confirmation of the async-gate read above.

Default build (movetap 145939 inside gamesrv 145717), coverage 62.4 s of
179.9 s (34.7%), 712 intervals; growth 6,706 u, shrink −4,877 u, net +1,830 u:

| class | time % | growth u | growth % | mean d(sep)/dt |
|---|---|---|---|---|
| AUTH-PARKED / client moving | 49.5 | 3,329 | **49.6** | +36.4 u/s |
| AUTH-MOVING / client moving | 46.0 | 3,200 | **47.7** | +19.5 u/s |
| AUTH-MOVING / client still | 1.2 | 177 | 2.6 | +201.3 u/s |
| AUTH-PARKED / client still | 3.3 | 0 | 0.0 | 0 |

AUTH-PARKED/FORWARD is the single biggest cell (34.6% of growth). **The BACK
family — the one the 0.66 fix targets — carries only 30.4% of growth and 10% of
the copy's travel.** The `--heading-grant` contrast is a completely different
budget: 99.3% of growth is AUTH-MOVING/client-moving, 95.9% of it in BACK.
Duty cycle, matched: client 95.5% vs copy 47.2%. **⚠ 79% of the default build's
net accumulation sits in UNCOVERED time** (covered 62.4 s → +1,830 u; uncovered
101.3 s over 16 gaps → +6,774 u; snaps → −9,692 u), so the table speaks for 21%
of the run; the identity `sep(last)−sep(first) == covered + uncovered +
snap-crossing` closes to ±0.000 u in all five runs but is telescoping, i.e. it
validates bookkeeping, not the model.

Snaps are resyncs on two independent sources (selection by wire speed, outcome
by client memory): **6/6 collapse in the default build (p50 2,069 → 24.5 u),
13/13 in `--heading-grant` (537.5 → 19.8 u)**.

### ★ THE CEILING: the speed candidate is dead for the build we ship

| run | jumps/min | mean jump | @dirfactor | @0.66-always | Δ magnitude |
|---|---|---|---|---|---|
| DEFAULT (13.0 grants/min) | 2.3 | 1,723 u | 1,670 u | 1,357 u | **−3.1%** |
| `--heading-grant` (336.7/min) | 12.8 | 589 u | 292 u | 318 u | **−50.5%** |

**Frequency: 0% at any trigger threshold below ~500 u** (−14% at T=500, −17% at
T=700). Independently, the snap-trigger lane replayed the real 39-grant sequence
against a copy at 288·k (calibrated: k=1 reproduces the measured 6 STARTs / 33
re-arms / 5-6 arrivals) and got **11 triggers at k=1 AND at k=0.66 — a 0%
reduction** — with 7 at k=0.50 (−36%) and 1 at k=0.10 (−91%). **Both lanes agree
at the fidelity-correct value: 0.66 buys nothing on frequency and ~3% on
magnitude in the build we ship.** It is correctly aimed only at the high-grant
arms, which are themselves refuted configurations. The whole wire speed channel's
ceiling on separation growth: dirfactor 3.7%, a hindsight oracle rate 31.1%, a
perfect velocity match 50.4% (algebraically the complement of the parked share).
**`0x0027` at spawn is a NO-OP**: the client already holds `+0x5C` = 288.0 and
`+0x60` = 1.0 in 4,115/4,115 movetap samples.
Retail refutes the double-apply worry: retail's predicted copy backpedals at
p50 189.8 u/s = 0.659 × 288 (n=32) and splitting those steps by the rate
actually in force gives 189.6 at 0.660 (n=17) and 189.9 at 1.000 (n=10) — **the
wire rate never reaches the client's own predicted copy**, so sending 0.66 would
not slow the player. It would also not help them.

### THE DEFAULT BUILD'S OWN HARM, measured at last

Every separation bound the arc has quoted (125.9 u p50, "under 150 u") came from
171153, a **refuted** configuration. The build we ship reads **separation p50
1,164 u, p90 2,163 u, max 3,648 u** (n = 251 paired reports of 268 over a 179.9 s
movetap window); by family fwd 1,265 / 2,260 / 3,648, back 1,276 / 1,731 / 1,851,
stop-reports 782 / 1,930 / 2,344. Snap cadence 2.67/min, inter-convergence p50
21.7 s, min 1.8 s, max 41.2 s. **⚠ Do not quote a "9×" multiplier** — a second
parser over `movetap point` gives 1,516 u, but `point` is the copy's position at
its last update, stale by up to a whole leg (|live − point| p90 2,205 u, max
5,217 u), so that is a different quantity, not a corroboration.

**⚠ AND THE SCOREBOARD'S DENOMINATORS ARE NOT COMPARABLE ACROSS CONFIGURATIONS.**
Time inside report intervals ≤ 2 s is **31.3% / 72.3% / 89.2%** of span for
default / heading-grant / client-endpoint — the default build is blind for
220.2 s of its 320.3 s, largest gap 131.8 s. Per *observed* second the ranking
inverts: 4.19 / 7.48 / 11.27 jumps per min and 137.8 / 69.5 / 101.4 u displaced
per second, which makes the default build the WORST on displaced distance rather
than the best. It remains the best on frequency per span. **State which
denominator you mean, every time.**

### The impossible-step population, adjudicated

25 of 26 are resyncs, but **graded honestly the evidence is 4 strongly
evidenced, 13 consistent-but-weak, 9 unadjudicated** — the 150 u point-ball
rescues 18 of them only because that ball fires on 73-85% of ORDINARY landings
in the two captures supplying 17 of the 26, and on half the movetap-paired rows
the sync copy is parked ON the granted point, so the "second arm" is the first
arm again. What is solid: every paired impossible step lands on the
**authoritative** agent (|landing − auth| p50 8.9-20.2 u, max 93.9 u, against an
ordinary-landing control that separates), and bit-exact landing on a granted
destination is 8 of 64 impossible vs 8 of 1,882 ordinary.
- **`warpscan`'s label regex undercounts player grants badly** — 293 of 740
  (171153), 134 of 327 (182652), 34 of 131 (152716), 2 labels vs 147 raw
  (100340). Decode `sent` plain bytes; never trust the label.
- **STOP QUOTING THE IMPLIED VELOCITY.** "v p50 2,521 / max 23,279 u/s" is
  arithmetic on a denominator the discontinuity itself created: the three fastest
  rows are the client emitting an **extra `0x003D` 32-33 ms after its regular
  283-301 ms report**, immediately on the discontinuity (verified as separate TCP
  frames — c2s seq 465→466, 50→51, 190→191, each a distinct 26-byte read — so not
  decode coalescing). The displacement (582-741 u) is real; the velocity is not a
  quantity. Use **magnitude and excess over the 288 u/s budget** (`d − 288·dt`):
  corpus 43 detections, excess p50 671 u, max 3,804 u.
- The 729-768 u band is **our own grant leash**: heading-derived grants cap the
  step at 767.7 u (n=21, p90 757.5) while click-derived grants in the same corpus
  do not.
- **The sole survivor** (20260814T100340 @ t=856.22) is not "a displacement
  nothing on the wire can explain" — it is a **client-side click-move executed at
  2.6× the walk budget** (736 u/s over ≥4,100 u), and the client's own clicks in
  that gap sit 79-158 u from the landing. Re-scope it as a speed anomaly on the
  client's OWN commanded destination; the decider is a movetap run over a long
  ungranted click-move.

### Claims that DIED in verification this round — do not re-quote

- **"The client's own stop is not the trigger" (0/31, 0/9, 0/2) was A CHECK THAT
  CANNOT FAIL.** All 57 in-window `0x0047` messages sit exactly at a
  report-interval boundary (0 strictly inside, all five runs), and a convergence
  interval — one in which the client moved hundreds of units — can never END on a
  stop report. Run in the direction that CAN fail, intervals **beginning** with a
  cancel converge 4/31 (12.9%) vs 4/219 (1.8%): a **7.1× lift**. Half the default
  build's convergences follow a client stop. The arc's own §6 trap, fired again.
- **"A speed term cannot bound frequency" is too strong** — it is categorical
  where the model is not. True statement: **not at the fidelity-correct 0.66**
  (0% there; 36% at k=0.5, 91% at k=0.1, where a copy slow enough never goes idle
  so clicks stop landing on an idle copy).
- **Two of the five arrival-linked convergences are common cause, not resync**:
  they land 0.0 u from the last `0x003E` click destination, open with a `0x0047`,
  and never cross 400 u/s — the copy was granted that click point and the client
  walked to the same click point. Strictly gated it is 3 of 6 arrivals, not 5 of 6.
- **movetap is not 50 Hz** — measured wall-clock p50 dt is 76-106 ms, i.e.
  **9.4-12.9 Hz**; its `now` is the client world clock, stepping in 50 ms quanta
  and running **1.3% slow** vs wall (−2.363 s over 180 s). Last round's "20 ms
  intervals" were world-clock deltas. The duty-cycle conclusion survives; the
  units in the record do not.
- **A `0x0047` does NOT mean the client is parked** — 16 of 32 "STOP" segments in
  the default run show the client displacing 5-2,583 u at 184-284 u/s. The
  proposed coverage extension is refuted; coverage stays gap-limited.
- **"All 124 non-unit `0x002B` sends are from 2026-08-11" is FALSE** — they span
  60 captures from 08-11 to 08-19 (55 on 08-11, 16 on 08-19). The
  no-counterfactual conclusion survives only because the two 08-19 captures sit
  at 11:29 and 15:48 UTC while the movetap windows are 18:59-21:15 UTC.
- **The default-build harm magnitudes above are SIMULATED separation, not
  measured teleport**: measured client displacement at those 7 landings is mean
  2,136 u / max 3,405 u / 4,985 u per minute, against the simulator's 1,723 /
  3,430 / 4,022 — 24% low on the arm being headlined.
- **The −3.1% ceiling is an n=1 measurement wearing a high-confidence label**: of
  the −375.45 u behind it, one landing contributes −343.22 u and the only other
  contributes −32.23 u, below the ~70 u noise floor. Its DIRECTION is
  deterministic (5 of 7 deltas are exactly 0.000000 because the candidate's rate
  IS 1.0 there); its precise value is not.

### THE MECHANISM, in one paragraph

The player clicks. The client predicts the move locally, registers a pending
AgTrack command, and walks its own copy. We answer with `0x0029` — a SYNC-ONLY
message — so the authoritative copy glides to that point and **parks** there
(parked 93.4 of 177.3 s). The player then keyboards away; `0x0025` is the only
thing we send afterwards and **its async arm is gated shut for the
client-controlled agent**, so nothing we send ever reaches the copy the player
sees. Separation grows unchecked — to 3,648 u — because the desync test is only
ever evaluated from a grant or an arrival, never per frame. Then the next grant
or arrival calls `0x00605FC0`; the client's pending command does not match our
grant; the walkable path between the two copies exceeds **300.0f**; and
`0x006022B0` hard-SetPositions the player onto the authoritative copy. **That is
the warp: not a race between two speeds, but a stale destination held by a parked
copy that nothing we send can correct, redeemed all at once the moment the
client is finally asked to look.**

### What this hands the seventh candidate

**Not the speed.** The direction factor is real, retail-faithful, and worth
≈3% of magnitude and 0% of frequency in the build we ship; `0x0027` at spawn is
a measured no-op. Ship neither as a warp fix. The corpus and the binary now
point at three untried shapes, in order of evidence:
1. **MAKE THE GRANT MATCH the client's outstanding predicted command** — the
   first branch of `0x006055E0` returns "no snap" when it matches, constant 100.0
   @0x00946560. This is what retail gets for free by answering the client's own
   click with the client's own point, at one RTT, before the client's record
   ages out. It is the only shape that prevents the snap rather than shrinking it.
   Read `0x00605AF0`'s per-record test to learn what "match" actually compares.
2. **`0x002C AGENT_UPDATE_POSITION`** — the only catalogued primitive that calls
   `AgTrack::Clear` and SetPositions BOTH copies, ungated. It is a hard set, so it
   is a teleport by construction; the question is whether a small, frequent,
   correct one is cheaper than a rare 3,648 u one. We have never sent one (0 of
   2,024,792).
3. **`0x0027 AGENT_UPDATE_SPEED_BASE`** — reaches both copies unconditionally and
   **re-issues the outstanding grant**, so it is the only lever that can re-aim a
   stale in-flight destination without naming a new point. Worthless as a spawn
   constant; possibly useful as a mid-flight re-bake.
**Before any of it, fix the denominators** (see the scoreboard warning above) —
no candidate can be scored against 5.7/min, and per-observed-second the default
build is not the champion the scoreboard says it is.

### The two instruments were repaired the same round — what the bar reads now

`movesync.py`'s hard bar has **TWO ARMS**: implied speed > 400 u/s at dt ≥ 0.05 s,
and displacement **≥ 520 u below that dt floor**, where a speed computed over a
window the event itself created is not a measurement. Corpus-wide that is
**61 → 64 hard rows over 961 captures / 4,582 intervals**; the three restored rows
are the corpus's fastest genuine events (740.7 u / 0.0318 s and 582.1 u / 0.0331 s
in `182652`, 617.0 u / 0.0324 s in `171153`), and the narrow form is deliberate —
the wide `dist ≥ 520 & dt ≤ 2.0 s` spelling sweeps in four ordinary walking rows at
284-286 u/s. **520 u is bracketed on both sides by measured data**: retail's largest
step inside 2 s is 517.87 u / 1.352 s and its largest step below the dt floor is
19.15 u over 82 intervals, while the smallest walking row the wide form would catch
is 525.3 u. Retail scores **ZERO on both arms**.

Re-derived on that bar, the three configurations read **7 of 267 / 20 of 468 /
13 of 197 hard rows**, **1.31 / 5.69 / 11.88 per minute of span**, magnitude p50
**1,969 / 569 / 582 u** and max **3,405 / 768 / 754 u**; the default build's excess
over the 288 u/s budget is p50 **1,208 u**, max **3,165 u**. `20260811T173940`
still reads **0 hard of 157**. **Implied velocity is demoted everywhere to a
labelled gate input** — magnitude and excess are the pair to quote. Two of the
default build's 7 hard intervals are themselves longer than the active-time
threshold, and 5 of the 7 are DEGENERATE for the on-path test (the grant-time
report IS the pre-jump record), leaving n = 2 on-path 2/2 as the whole
non-tautological on-path evidence on that capture.

`pinned.py`'s gate is repaired in the same round and in the opposite direction:
`Build.patched` is a per-build TUPLE of accepted digests, the patchers register
what they write, and the loosening is fenced by refusals that a mutation reddens
(a digest equal to any known build's pristine, a strict registration with no
pristine to diff against, a registry row that fails re-validation on read).

---

## 2026-08-20 — THE AgTrack MATCH TEST IS DECODED, AND IT DOES NOT READ OUR GRANT

Four independent decode lanes (the caller `0x006055E0`, the per-record test
`0x00605AF0`, the two geometry primitives, and a corpus measurement), each then
attacked by three separate skeptics who re-parsed from raw bytes with their own
readers. **The mechanics survived almost untouched. The SEMANTICS did not, and
the shape this arc was reaching for died with them.** Every address below was
re-read by this session from the pinned pristine 38797 image, not carried from a
lane's transcription.

### The predicate, as a server author would implement it — OBSERVED

```
# 16-byte position block: { f32 x; f32 y; i32 plane; u32 w }.  World units.
# R = 100.0f, the f32 at 0x00946560 (bytes 00 00 c8 42) — read, not inferred.

def agtrack_ok(mgr, state, source):        # 0x006055E0, __thiscall, ret 8
    assert state.clientControlled          #  AgTrack.cpp(457), on 0x00605601
    assert source.world == WORLD_SYNC      #  AgTrack.cpp(458), agent+0x24, SYNC == 0

    # --- two early-outs, both meaning "no snap" ---
    if source.timeStopMovement != 0 and source.facing == 9:   # +0x48, +0xC4
        return 1                                             # 0x00605634 / 0x0060563A
    q = copy16(source[0x78:0x88])          # 0x00605643 — NOT our grant. See below.
    if q.x == +INF and q.y == +INF:        # AGENT_INVALID_POSITION (0x00948654)
        return 1

    prev      = copy16(state.position)     # state+0x08..+0x14  (the seed vertex)
    node      = state.history              # state+0x04, head = NEWEST
    lastMatch = None
    while node is not None:                                  # 0x00605732 mov esi,[esi+4]
        if not (prev.x == +INF and prev.y == +INF):          # guard tests PREV only
            if seg_match(q, node.position, prev, R):         # 0x006056FD
                lastMatch = node                             # NO break — keeps the LAST
        prev = copy16(node.position)                         # 0x0060571A
        node = node.next
    if lastMatch is not None:
        lastMatch.next = None              # 0x00605746 — truncate, dropping the OLDER tail
        return 1                           # -> caller does nothing
    return fallback_half()                 # 0x00605753..0x0060583D — DECODED in "round 2"
                                           #   below (§ "THE FALLBACK HALF IS DECODED",
                                           #   :3073), can ALSO return 1.
                                           # ^ this comment said UNDECODED for five days while
                                           #   the decode sat 350 lines down in the same file —
                                           #   and on 2026-08-25 a session carried the stale
                                           #   label into REALFIX §0.5 before a re-read caught
                                           #   it (§0.6). Verified byte-for-byte that night:
                                           #   the span appends to the history chain on NO
                                           #   branch (appender exonerated; the real
                                           #   open-stretch appenders are named in §0.6), and
                                           #   warp A = gate 2 OR gate 3, gate 1 byte-excluded.

def seg_match(q, a, b, r):                 # 0x00605AF0, ret 0x10, 1 direct caller (a floor)
    if a.x == b.x and a.y == b.y:                    # degenerate-segment guard
        d2 = (a.x-q.x)**2 + (a.y-q.y)**2             # STRAIGHT LINE, SQUARED
        return r*r > d2                              # STRICT (>); NO path test on this arm
    d2, t = closest_pt_on_segment(q, a, b)           # 0x0046DE80 -> |q-c|^2, t clamped [0,1]
    if not (r*r > d2):                               # STRICT (>), SQUARED, in a register
        return 0
    c = b if t >= 0.99 else Pos(a.x + t*(b.x-a.x),   # 0.99f, f64 @0x00A53BF8
                                a.y + t*(b.y-a.y),
                                a.plane, 0)          # 4th dword FORCED to 0, 0x00605BD5
    return map_path_len(q, c, limit=r, straight_only=False) <= r     # 0x00709990
                                                     # WALKABLE, LINEAR, INCLUSIVE (<=)
```

**Match = (straight-line perpendicular distance to the segment < 100 u, compared
SQUARED) AND (walkable path distance to the closest point on it <= 100 u, compared
LINEAR).** The two conjuncts differ in every axis that can be got wrong: one is
squared and strict, the other linear and inclusive; one is as-the-crow-flies, the
other as-the-crow-walks. **CORROBORATED** — the `[ebp-0x20]` slot holding the
radius is written exactly once (`0x00605B7B fstp qword`), and the squaring at
`0x00605B87` is `fmul st(0),st(0)` on a register copy that is never written back,
so the tail really does compare against 100 and not 10,000. Two skeptics
re-derived that independently; a second write anywhere would have refuted it.

> **2026-08-25 — this pseudocode was exercised on live data and held, and its
> plane line turned out to be load-bearing.** REALFIX.md §0.5: `c.plane = a.plane`
> (the node's plane, `0x00605BD5` above) is what hands the chain's plane words to
> `map_path_len`, whose mismatch route is a real navmesh pathfind (`0x00721A30` at
> `0x00709B99`; no path → exactly `range+1.0`). In `movetap-20260825T202345` a
> cross-plane covering segment failed the veto that way (→ both observed warps),
> while same-plane covering segments held it at separations up to 509 u. An
> empirical-fit skeptic derived the rolling-`prev` segment walk and the node-plane
> inheritance from the tape alone before reconciling with this section — the
> decode and the tape now witness each other independently.
> **2026-08-26 addendum: the DEGENERATE arm's plane-freeness is now exercised
> live and load-bearing** (REALFIX.md §0.8): eight `--pc-spoof` grants stamped a
> parked copy's `+0x80` to a bogus plane at separations up to 494 u with the
> snap test provably running, and the veto held every time — the parked copy's
> dist-0 covering segment takes the `a == b` arm above, which reads no plane
> word and calls no pathfind. A parked copy's self-veto is plane-proof; the
> plane term is confined to the non-degenerate mismatch→pathfind route.

### The two operands — and this is where the arc's framing died

**1. The compared point is NOT our grant. REFUTED (Lanes A and B, and the arc's
own gloss).** `0x00605643` reads `source+0x78`. Our `0x0029` never writes that
field: I disassembled `0x00602A40`'s body and the message's 16-byte point goes to
`+0x88..+0x94` (`0x00602A84`–`0x00602A9F`, the destination) and is mirrored to
`+0x9C..+0xA8`, with the plane word to `+0x80` (`0x00602A74`) — **n = 0 writes to
`+0x78`** in that body, from a scan that did find the `lea esi,[ebx+0x78]` at
`0x00602ADB` in the same range, so it was not blind. What fills `+0x78` instead is
the client itself: `0x00602AD3` calls the bake `0x005FE950`, which at
`0x005FE9EA` calls `0x005FF880`, which does `lea edi,[esi+0x78]`, tests
`[esi+0x48] != 0`, dead-reckons through `0x005FFB40` on the world clock and stores
back through `edi`. **OBSERVED: q is the SYNC agent's own position, dead-reckoned
to the client's clock at the instant our message is processed** — a quantity that
depends on the client's delivery-time `now` and on its own per-agent speed product
(`+0x5C` × `+0x60`), neither of which we hold server-side.

**2. The chain is `history`, not a prediction list. REFUTED (Lanes A and B's
"predicted-movement polyline" / "pending predicted waypoints").** ArenaNet names
it in four asserts read from the image: `historyState->history`,
`historyPoint->position != AGENT_INVALID_POSITION`,
`(int)(time - history.time) >= 0`, `!state->history->velocity.x`. Nothing in the
module says *predicted*, *pending*, or *waypoint*. The allocator stamps
`node+0x00 = now` at creation (`0x00604DCC mov [eax],ecx` with `ecx` = the clock
pushed at `0x00605A32`) and the insert is **push-front** — `0x00605A55 mov
ecx,[esi+4]` / `0x00605A5D mov [edx+4],ecx` / `0x00605A93 mov [esi+4],edx`. **Head
= newest, `next` runs newest → oldest**, so `lastMatch->next = NULL` discards the
OLDER tail. That closes the top open question of *both* decode lanes, on bytes
rather than argument.

### What the polyline actually is — OBSERVED, from the recorder `0x00605840`

No lane found the routine that BUILDS the list; two skeptics did, and I
re-disassembled it. It is reached from the same dispatcher as the test
(`0x00605FC0` routes world 1 → record at `0x0060610B`, world 0 → test at
`0x0060601C`).

- **The seed vertex is the DESTINATION while the agent is moving.**
  `0x006058D6 mov ecx,[esi+0x48]` / `test ecx,ecx` / `je 0x605909` selects between
  `agent+0x88..+0x94` (`m_segmentPoint`, the current destination, with
  `state.time = +0x48` the **arrival tick**) and the agent's position dead-reckoned
  to now (`state.time = now`). Those land in the state at
  `0x00605A38`–`0x00605A4D`. **Lane A's "the client's LIVE position is the first
  vertex" is REFUTED**; one skeptic had only WEAKENED it to "the last recorded
  sample", and the recorder settles it outright.
- **Each node holds a LEG-START position.** `0x00605A60`–`0x00605A75` copies
  `[ebp-0x44..-0x38]`, which was loaded from `agent+0x78..+0x84` at
  `0x0060584D`–`0x00605873` and then dead-reckoned in place by
  `0x006058BF call 0x5ff820`.

So the chain, newest first, is **[current destination] → [start of the current
leg] → [start of the previous leg] → …**. The first segment is the leg being
walked *now* — the one genuinely forward-looking element in the structure — and
every segment after it is a chord of ground the client has already covered.

**It is coarse, not a breadcrumb trail.** A node is pushed only when the movement
command CHANGES (destination, plane, velocity, both speed factors and facing all
compared at `0x00605945`–`0x006059B4`) or when the head is older than **2500 ms**
(`0x0060593A cmp eax, 0x9c4`). A single click therefore produces a **one-segment**
polyline — the narrowest tolerance case, and the one this project most needs to
reason about. At 288 u/s a forced 2.5 s re-sample chord can span ~720 u.

### Struct layouts — CORROBORATED, by the refutable check

ArenaNet's own field names land on the offsets the code reads, and both strides
close to the exact byte.

| record | stride | fields |
|---|---|---|
| `state` = `stateArray[agentId]`, base `[mgr+0x20]`, count `[mgr+0x28]` | **0x1C = 28** (`lea ecx,[ebx*8]` / `sub ecx,ebx` / `*4` at `0x00605FF9`) | `+0x00 clientControlled`, `+0x04 history`, `+0x08..+0x14 position`, `+0x18 time` |
| `history node` | **0x2C = 44** (`imul eax,eax,0x2c` at `0x00604BFC` and `0x00604DBD`) | `+0x00 time`, `+0x04 next`, `+0x08..+0x14 position`, `+0x18/+0x1C velocity`, `+0x20/+0x24` speed factors (`agent+0x5C`/`+0x60`), `+0x28 facing` (`agent+0xC4`) |

- **Lane A's "node is ≥0x20 bytes" — WEAKENED.** It is exactly 0x2C, and three
  fields nobody named are written at `0x00605A7B`/`0x00605A8D`/`0x00605A90`.
- **Lane A's "state+0x18 is a sample timestamp with a 250 ms freshness window" —
  WEAKENED.** The 250 ms constant is real (`0x00604F09 cmp eax, 0xfa`, and the
  client names it: `MathAbs((int)(nearestTime - compareTime)) <= TOLERANCE_TIME`),
  but `state+0x18` is the **arrival tick** while moving, so the test means "still
  on this leg, or arrived under 250 ms ago", not "this sample is fresh".
- The position block's **4th dword (`+0x14` / `agent+0x84`) is UNVERIFIED** — copied
  verbatim on the `t >= 0.99` arm, forced to 0 on the lerp arm, loaded but unused
  by `0x00709990` in the decoded portion. The **`+0x10` plane field is OBSERVED**:
  `0x007099F1 cmp esi,edi` / `jl` compares it as a **signed int**.

### The primitives, and a correction to this document's own record

- **`0x0046DE80`** — `__fastcall(ecx=q, edx=a, [ebp+8]=b, [ebp+0xc]=&t)`, returns
  the **SQUARED** point-to-segment distance in `st(0)` and writes the clamped
  parameter `t` through the out-pointer. **OBSERVED**: no `fsqrt` and no `call`
  anywhere in the 252-byte body, and the tail is two `fmul st(0),st(0)` plus
  `faddp`. Independently corroborated by instruction-stream emulation against an
  exact-rational reference: max distance error **1.6 ulp of scene scale (n = 2,000
  per scale at 1 / 100 / 5,000 / 40,000; n = 8,000 total)**, out-param error
  **1.93e-06**. Clamp constants read from the image: `0.0 @0x0093CF10`,
  `1.0 @0x0093C1D0`. Its source file is **NOT FOUND** — zero asserts in a ~3.5 KB
  unasserted run. Degenerate input (`a == b`) yields NaN, unguarded — which is
  exactly why the caller's `a == b` branch exists.
- **`0x00709990`** — `__cdecl(from, to, float range, int straightOnly)`, returns
  **min(walkable path length, range + 1.0)** in **linear** world units.
  **CORROBORATED** as a `Map.cpp` routine (no assert inside; the next function
  asserts at Map.cpp:1195/1197, and the callee `0x00721A30` asserts at
  PathApi.cpp:698/699). The straight-line shortcut is the exception, not the rule:
  it needs matching planes **and** `dist² <= 1.0`, or `straightOnly != 0`. The
  `range+1` saturation is a designed "unreachable" sentinel — passing `r` as both
  the budget and the threshold makes `result > r` mean exactly "no path".
- **⚠ CORRECTION to §"THE TRIGGER" above (FINDINGS:2372-2375), which calls the
  300.0f fallback gate a WALKABLE PATH LENGTH. It is STRAIGHT-LINE.**
  `0x006057C8 push 1` sets `straightOnly`, and `0x00709B3F cmp [ebp+0x14],0` /
  `jne 0x709ae0` jumps back to the plain `sqrt(dx²+dy²)` path. The **100 u** test
  is the walkable one (`0x00605C40 push 0`); the **300 u** gate is not. OBSERVED.
- **The path length is a slight OVERESTIMATE.** Each leg goes through the
  table-driven approximate sqrt `0x0046E870`. Three independent emulations against
  the real 256-entry table at `0x0093CAC8` agree: worst relative error
  **3.88–3.90e-03 (n = 5,000 / 5,000 / 5,010)** against **2.06e+01–3.07e+01** for a
  cube-root rival on the same samples, and **every** sample overshoots. **So the
  second conjunct's effective threshold is ~99.6 u of true walkable length**, and
  the 300.0f gate is likewise biased toward snapping.
  ⚠ **CORRECTED 2026-08-20: the 300.0f gate's effective cut is 299.332591 u, not
  "~298.8".** That figure applied the worst-case relative error uniformly; the
  error is exponent-dependent and the crossing is a **quantisation step**, not a
  smooth offset. Measured exhaustively over **all 2,560,001 float bit patterns**
  of `distSq` in [80000, 100000] by reimplementing `0x0046E870`'s nine
  instructions against the real LUT: the first `distSq` that snaps is exactly
  **89600.0f** (bits `47AF0000`) = **299.332591 u**. Consequence worth stating
  plainly: **a true separation of exactly 300.0 u SNAPS** — `approx_sqrt(90000)`
  returns 300.186584, so `300.0 < result` holds. The same census finds **27
  under-estimates in 2,560,001 samples** (min rel err −4.47e-08, tie artifacts at
  bucket edges), so "every sample overshoots" is true of the coarse n = 5,000
  samples above and *very nearly* true exhaustively — the direction of the bias
  stands, the absolute "never" does not.

### The gates upstream, and the three ways the test never runs at all

None of the decode lanes mentioned these, and a server author reading only the
predicate would assume it always fires.

1. `0x00606002 cmp [eax+ecx*4],0` / `je 0x606103` — if `state->clientControlled`
   is 0 the match function is **never called**.
2. `0x00606013 cmp edx,1` / `je 0x60610b` — if the source agent's world is 1
   (async) control goes straight to the recorder with no test attempted.
3. `0x006056B8 test esi,esi` / `je 0x605751` — if `state->history` is NULL the loop
   is never entered and `edi` stays 0.

**And the mechanism is ONE-SHOT.** `AgTrack::Clear` (`0x00605F70`) zeroes
`clientControlled` **and** `history` (`0x00605FA7`/`0x00605FAE`). The only thing
that re-arms the flag is `0x00605F10`, called from two player-input sites — and it
nulls the history again (`0x00605F48` sets the flag, `0x00605F4F` clears the
head). So after any miss the test is not consulted until the player next steers,
and then the polyline restarts **one segment long**. Storage is block-recycled
rather than freed: 256-entry blocks, reclaimed when the block's newest entry is
older than **5000 ms** (`0x00604C03 cmp ecx, 0x1388`), with the sweep NULLing any
`next` that points into the reclaimed span. That is the ageing bound on the
polyline, and it closes both lanes' "is the truncated tail freed?" question.

### The early-outs, and the one lever that is real but unmeasured

`0x00605634`–`0x00605641`: **`+0x48 != 0` AND `facing == 9` returns 1
unconditionally**, before any geometry runs. `+0xC4 = facing` is **CORROBORATED**
by ArenaNet's own `!(facing & ~AGENT_FACING_MASK)` at AgAgent.cpp(2368), a 4-bit
mask; the client's facing dispatcher `0x00602660` switches on `facing-1` over a
table covering **only 1..8**, sending 9 to a bare epilogue that computes no facing.
**What `facing == 9` MEANS is NOT FOUND, and I refuse to guess the other eight.**

- **Lane A's "9 is the only value anything in .text checks `+0xC4` against" —
  WEAKENED.** The immediate-form scan reproduces exactly (**n = 16** sites: 1 real
  nonzero — `0x0060563A`, against 9 — 13 against 0, 2 against the `0xDDDDDDDD`
  debug fill), and a skeptic re-ran it wider including SIB bases with the same
  answer. But it does not cover the register forms: **n = 17 further sites**
  compare `+0xC4` against a register. "The only IMMEDIATE" is supported; "the only
  value anything checks" is not.
- The lever is reachable: `0x002B`'s setter `0x00602990` writes `+0xC4` with no
  clamp, and 9 passes the client's own mask assert. **Costs, stated because they
  are not free**: the same setter writes `+0x60 moveSpeed` (so a `0x002B` carrying
  facing 9 must also carry rate 1.0 to be identity), the character stops turning,
  and suppressing the test means the client never reconciles at all — divergence
  accumulates silently instead of being corrected once. **Whether that trade is net
  better is UNVERIFIED and has NOT been run.**

### The corpus lane returned a rigorous measurement of a DIFFERENT pair

**Say this out loud rather than letting the static reading borrow it.** Lane D
measured |our granted point − the client's *stated destination*| over **n = 1,107
player grants in three "ours" captures**: p50 **0.000 u**, p90 0.500, p95 97.9,
p99 472.0, max 748.7, and **1,053/1,107 = 95.1% within 100 u**. Its procedure
checks are sound and could have failed (the `client_endpoint` arm reads
**0.5000 u, max 0.5006, 193/193** against the 0.5 u our source writes; the
`click_grant` arm reads **0.0000 u, 467/467**), and its shuffled control fires
correctly (**p50 2,073–2,608 u; 0/40, 11/740, 6/327 within 100 u**). The only
non-tautological arm — `heading_grant`, **n = 447** — reads p50 0.0, p90 163.1,
p99 618.5, max 748.7, **393/447 = 88% within 100 u**, with all **73/73** of the
>1 u tail lying **on** the client's own segment (perpendicular offset max 0.0 u),
i.e. clipped short along the ray rather than translated off it.

**None of that is evidence about this predicate.** The query point is
`sync.+0x78`, which never appears on the wire, and the polyline is mostly past
async positions, which also never appear on the wire. Lane D paired two
*endpoints*, neither of them an operand of the test. One skeptic marked it
**REFUTED** as support; another marked it **UNDECIDABLE**, which is the more
precise verdict — the measurement is fine, it answers a different question.
Recorded here as: **destination fidelity is OBSERVED and excellent; proximity-
predicate support is NOT ESTABLISHED, and no corpus pass can establish it.**

Two further disclosures from that lane, both named by the lane itself:

- **A named proxy.** For keyboard movement the client has no fixed destination.
  `pos + heading` is a ray tip of measured magnitude **765.0–768.0 u** (all four
  captures) whose same-mode drift is **p50 398.3 u, p90 635.0 u (n = 148)** inside
  a 0.25 s median window — against the 72 u a 288 u/s walk covers in that time.
  The "destination" is exactly well-defined only for CLICK movement (`0x003E`).
- **A corpus correction.** `20260811T173940` is **not** a retail/live comparison —
  `origin.origin_of` returns `ours`, its origin record names
  `toolkit/authsrv/authsrv.py`, its peer is `127.0.0.1:55588`, and it contains
  **zero** player `0x0029`. It is the corpus's zero-grant arm (0 hard jumps of 157
  intervals), not a live baseline.

**And the hard-jump shares cut against a monotone story.** By grant arm:
zero-grant **0/157 = 0.0%**; click-only, all 40 grants at 0.0000 u from the
client's own click, **7/267 = 2.6%** (with jumps of 1,968.9 / 2,016.6 / 3,166.2 /
3,405.3 u); heading **20/468 = 4.3%**; client-endpoint, 193 grants at 0.5000 u
from the client's own endpoint, **13/197 = 6.6% — the HIGHEST**. Different
sessions and different play, so an observation and not a controlled comparison —
but the capture whose grants match the client's own number to half a unit jumps
the most.

### Claims that DIED this round — do not re-quote

- **"`0x006055E0` walks the client's PREDICTED-movement polyline / a list of
  pending predicted waypoints" — REFUTED.** It walks `state->history`: nodes
  stamped `now` at creation (`0x00604DCC`), pushed on the front (`0x00605A93`),
  named `history` / `historyState` / `historyPoint` by ArenaNet in four asserts.
  Exactly one segment — the seed to the head node — looks forward.
- **"The polyline's first vertex is the client's LIVE position" — REFUTED.**
  While the agent is moving it is the **destination** (`agent+0x88..+0x94`), with
  the state's time field holding the **arrival tick**.
- **"The position you send / the server's reported position is what gets
  compared" — REFUTED.** `q = source+0x78`, the sync agent's own dead-reckoned
  position; `0x0029` writes `+0x88..+0x94` and `+0x80` and never `+0x78`
  (**n = 0** writes in `0x00602A40`'s body).
- **Lane A's one-sentence rule for a server author** ("the client will not snap if
  the position you send lands within 100 units of the polyline it has predicted")
  — **REFUTED on both halves.** It is true only for the `dist² <= 1.0` degenerate
  branch at `0x005FEA92`, i.e. exactly when the grant is too small to matter.
- **"Below 300 u, `0x00709E90` / `0x005FEF70` can still force the snap [on a
  match]" — REFUTED as stated.** `0x0060574C jmp 0x60582b` jumps clean over the
  entire fallback half. Those two threaten the **no-match** path only.
- **This document's own "the 300.0f gate is a WALKABLE PATH LENGTH" — REFUTED.**
  `0x006057C8 push 1` makes it straight-line. The walkable test is the 100 u one.
- **"A miss means the client snaps" — never established, and it does not follow.**
  A hit is SUFFICIENT for return 1; the converse needs the fallback half, which is
  undecoded and can also return 1.
- **HANDOFF's "`0x002C`: we have never sent one (0 of 2,024,792)" is a corpus
  census, not a history.** `authsrv.py:7036-7045` records that an earlier build
  *did* — "five AGENT_UPDATE_POSITION went out and three were arrivals, carrying
  the client 630, 189 and 765 units" — and that it was removed as "the warp the
  player described". `0x002C` is untried *in the current corpus*, not untried.
- **Lane D's own retracted number**: a first staleness pass read p50 1,636–2,115 u
  by scoring each armed grant against every later client statement; restricted to
  same-mode continuation it is **p50 398.3 u**. The first figure was a change of
  mind wearing drift's name.
- **Three open questions died by being ANSWERED**: list direction (push-front,
  head = newest), the insert site (`0x00605840`), and the fate of the truncated
  tail (block-recycled on a 5 s rule, never freed).

### What this means for the fix

**What our server would have to send for the match to succeed: nothing we can
send.** The predicate reads no field our `0x0029` writes. The grant sets the
destination (`+0x88..+0x94`) and the plane (`+0x80`); the test reads the position
(`+0x78`), which the client re-derives itself by dead-reckoning the sync agent on
its own clock during the bake. The only lever on `q` is indirect and one message
late — where our *previous* grant will have carried the client's own extrapolation
by the time the *next* message lands — and computing that needs the client's
delivery-instant `now` and its own per-agent speed product, which we do not have.
The correct restatement of the shape is therefore **"keep the server's tracked
position on the path the client actually walked"**, not "aim the grant at the
client's destination".

**What stands in the way, from the consequence skeptic, and it is decisive.**

1. **The experiment already ran and failed.** `--heading-grant` put our grants
   0.5 u from the client's own proposed endpoint (**193/193**) — inside 100 u of
   the polyline by construction — and `authsrv.py:1046` records it **REFUTED on
   run `20260819T152716`: it CAUSES warps**, two teleports in six seconds. The
   click-only capture held 40 grants at **0.0000 u** from the client's own click
   and still logged **7 hard jumps of up to 3,405 u**. We are already passing the
   destination-fidelity test; making it easier to pass buys nothing.
2. **The mechanism is one-shot** (see the gates above), so any strategy built on
   staying inside the radius gets one mistake, and the second is measured against
   a one-segment polyline — which predicts exactly the clustering `--heading-grant`
   produced.
3. **A miss is not a snap.** The fallback half is where the decision actually
   lives once the match fails, and it is undecoded.
4. **The effective threshold is 99.919968 u** (⚠ this line read ~99.6 until round 5 re-measured it exhaustively), biased toward snapping.

**Nothing here is a fix, and none of it has been run.** The one short-circuit that
does exist — `0x002B` carrying `facing = 9` against an armed `+0x48`, which
returns 1 before any geometry — buys snap suppression at the cost of a character
that stops turning and a client that stops reconciling entirely. That is a
candidate to *price*, not a fix to ship, and it is **UNVERIFIED**.

### Method note

The four decode lanes shared one scratchpad root, and one lane reports a file it
wrote there was overwritten mid-run by a sibling agent, with content matching the
check it was about to perform. **Lane agreement on the `0x0046E870` sqrt result is
therefore not blind in the replication sense.** The finding survives — two
skeptics re-derived it in private directories from the image bytes, and this
session re-read every load-bearing address above independently — but four-way
agreement should be quoted as fewer than four witnesses on that specific point.

---

## 2026-08-20, round 2 — THE FALLBACK HALF IS DECODED, AND "UNDER 300 u" IS NOT SAFE

Four independent decode lanes (fallback control flow; `0x00709E90` blind; `0x005FEF70` blind; a corpus measurement), then three skeptics re-parsing from raw bytes. **Every address, string and constant below was re-read by this session from the pinned pristine 38797 image**, and the two numbers that changed — the effective gate-1 threshold and the shape of the correction — were re-measured here rather than carried from a lane.

This half runs **only when the 100 u history walk found no match** (`0x00605744 je 0x605753`; a match takes `0x0060574C jmp 0x60582b` clean over everything below). It is where a MISS is adjudicated.

### THE DIRECT ANSWER: is separation under 300 u sufficient to avoid a snap?

**No. OBSERVED.** Separation under the threshold is **necessary but nowhere near sufficient**. Only one of the three gates is a distance test at all. Gate 2 is a *walkable-navmesh* query on the authoritative position and gate 3 is a local obstruction predicate; either can force a snap at *any* separation, including zero. A twin 50 u away on the far side of a wall passes gate 1 and snaps on gate 2. **And the threshold itself is not 300 u — it is 299.3326 u** (below). Every "300 u" in this document and in `PLAN.md` §"Movement" should be read as "the outer bound of one of three gates, guarding one of at least two snap routes, and its real value is 299.33".

### The fallback, as a server author would implement it — OBSERVED

```
# this = agentMgr + 0x1CC.  16-byte position block { f32 x; f32 y; i32 plane; u32 w }.
# Records: agentMgr + 0xE8 + world*0x64 = { +0x00 Array.m_data, +0x08 m_count, +0x60 time }.
# EXACTLY TWO worlds.  WORLD_SYNC == 0 (authoritative), world 1 == async (rendered).

def agtrack_dispatch(this, state, source):            # 0x00605FC0, ret 4 — THE ENTRY
    assert state.id < this.recordCount                #  Array.h(587)
    rec = this.records[source.id]                     #  0x1C stride, base this+0x20
    if not rec.clientControlled: ...                  #  0x00606002 -> gates NEVER run
    if source.world == 1: return record_history()     #  0x00606013 -> gates NEVER run
    if agtrack_ok(this, rec, source): return          #  nonzero = NO SNAP, do nothing
    clear_record(source.id)                           #  0x00605F70
    record_history(rec, source)                       #  0x00605840 — appends, not a fix
    for i in range(world[1].m_count):                 #  0x0060604C..0x006060F4  THE SNAP
        a = world[1].m_data[i]
        if a is None or (a.flags & 0x10000): continue
        clear_record(i)                               #  zeroes that agent's 0x1C record
        resync(this=a, world[0].m_data[i], i != this.focusId)     # 0x006022B0

def agtrack_ok(this, state, source):                  # 0x006055E0, ret 8
    ... first half: two early-outs, then the 100 u history walk ...
    if matched: return 1                              # 0x0060574C — NO SNAP
    # ---------------- FALLBACK HALF, 0x00605753..0x0060583D ----------------
    ok = 0                                            # 0x00605756 xor edi,edi
    assert source.id < world[1].m_count               # Array.h(587)
    twin = world[1].m_data[source.id]
    assert twin                                       # AgTrack.cpp(519) "asyncPtr"
    A = position_at(source, world[0].time)            # 0x006057AD — SYNC on SYNC clock
    B = position_at(twin,   world[1].time)            # 0x006057BA — ASYNC on ASYNC clock

    # GATE 1 — STRAIGHT-LINE separation, compared LINEAR (not squared)
    d = map_dist(A, B, range=300.0, straightOnly=1)   # 0x00709990, saturates at 301.0
    if 300.0 < d: return ok                           # 0x006057EA  -> SNAP

    # GATE 2 — WALKABLE navmesh query.  A is arg1 = the START point.
    pathCount = 0                                     # NOT initialised by the caller
    find_path(A, B, maxDist=300.0, maxCount=4, &pathCount, &P)    # 0x00709E90
    if pathCount == 0: return ok                      # 0x0060580D  -> SNAP

    # GATE 3 — can `source` take a first step from A toward P, right now?
    if not step_is_clear(source, A, P): return ok     # 0x00605820  -> SNAP

    return 1                                          # 0x00605822 — NO SNAP
```

**All three gates snap on failure; all three must pass to avoid a snap.** `edi` is the sole return accumulator: a mechanical `regs_access()` sweep of `[0x605753, 0x60583E)` returns exactly three writes (`0x00605756 xor`, `0x00605822 mov 1`, `0x00605830 pop`) — **n = 3, and no others**. Two skeptics reproduced that sweep independently. Direction re-confirmed at the sole direct caller (`--xrefs 0x006055E0` = 1 site): `0x00606021 test eax,eax / jne 0x606110` returns doing nothing. **1 = NO SNAP, 0 = SNAP.**

### ★ THE THRESHOLD IS 299.3326 u, NOT 300 — and exactly 300.0 u SNAPS

**OBSERVED, measured in this session, and it corrects this document's own record.** `0x00709990` computes `dx²+dy²` and square-roots it through `0x0046E870`, a nine-instruction table sqrt with **no Newton refinement**: exponent halving `((bits>>24)+0x3F)<<23` plus a 256-entry LUT at `0x0093CAC8` indexed by **byte 2 only** — mantissa bits 15..0 are discarded. I re-implemented those nine instructions exactly and measured:

| quantity | value | n |
|---|---|---|
| relative error, distSq ∈ [80000,100000) | **[+4.97e-06, +3.18e-03]**, **0 under-estimates** | 20,000 |
| `approx_sqrt(90000)` | **300.186584** (true 300.0) | — |
| last non-snapping distSq | 89599.992188 (`47AEFFFF`) → 299.332581 | binary search over float bit patterns |
| first snapping distSq | **89600.000000** (`47AF0000`) → 300.186584 | " |
| **effective threshold, TRUE straight-line separation** | **299.332591 u** — shortfall **0.667409 u** | " |
| distinct outputs, true separation ∈ [295,305) | **13** (quantisation ≈ **0.866 u** near the boundary) | 20,000 |

**A true separation of exactly 300.0 u takes the `jne` and SNAPS.** The error is one-sided (**0 of 20,000** under-estimates), so the gate fires **early and never late**. The exact predicate is `snap iff distSq >= 89600.0f`.

- **Lane A's "STRICT — exactly 300.0 passes" — REFUTED** (both skeptics, and re-measured here). True of the register comparison, false of the world.
- **Lane A's "soft boundary at the ~1e-4 relative level" — REFUTED.** Understated ~6× at the boundary and ~39× at worst, and it misses that the bias is one-signed.
- **⚠ CORRECTION to this document, FINDINGS:2861 ("the 300.0f gate ~298.8 u") and `PLAN.md`:1417.** That figure applied the worst-case 3.9e-3 relative error uniformly. The error is exponent-dependent; at this boundary it is +6.22e-04, and the crossing is a **quantisation step**, not a scaled offset. **299.3326 u, not 298.8 u.** The companion ~99.6 u figure for the 100 u test is derived the same way and should be re-measured before it is quoted again.

### The three gates in detail

**GATE 1 — `0x00709990(A, B, 300.0f, straightOnly=1)`, `0x006057BF`–`0x006057EA`. OBSERVED.**
With arg4 ≠ 0, `0x00709B3F cmp [ebp+0x14],0 / jne 0x709ae0` always takes the straight branch, so this is a **straight-line 2-D distance in linear world units** — only `.x`/`.y` are differenced; `.plane` merely orders the pair. It **saturates at maxDist+1 = 301.0**, which is provably harmless to the predicate since `min(d,301) > 300 ⟺ d > 300` (this closes Lane D's stated worry that the clamp "needs re-deriving" — it does not). `fcom st(1)` / `test ah,1` (isolates C0) / `jne` fires iff `300.0 < d`. **A twin on a different plane but horizontally close passes this gate** — the zplane is compared but not used as a distance.

The x87 trap does not bite: `0x006057E5 fstp st(1)` overwrites the callee's result with 300.0 **and pops**, so `0x006057FA fstp dword [esp]` passes **300.0f** into gate 2, not the measured distance. **CORROBORATED** — verified by two skeptics via two different routes, and the compiler's own lone `fstp st(0)` at `0x00605829` is only correct at depth exactly 1, a check that could have failed.

**GATE 2 — `0x00709E90(A, B, 300.0f, 4, &pathCount, &P)`, `0x006057EC`–`0x0060580D`. OBSERVED.**
Six args (`add esp,0x18`). I read the push order directly: the last push is `0x006057FE lea eax,[ebp-0x5c]` = **arg1 = A = the SYNC (authoritative) position**; arg2 = `[ebp-0x80]` = the async twin. It is `MapFindPath` in `P:\Code\Engine\Map\Map.cpp` — the assert six bytes before the entry reads `*pathCount <= maxCount`, Map.cpp(1239), naming both out-params and the integer. This is a **walkable navmesh query over trapezoid cells**, not arithmetic.

- **`4` is `maxCount`, an array capacity** — `shl eax,4` (×16-byte stride) at `0x0072726B`, `sar eax,4` at `0x0072729D`. **CORROBORATED, by a check that could have failed twice**: the two callers pass different values matching their own buffers — AgTrack `4`→`ebp-0x44` (64 B) and ChCliBase `9`→`ebp-0x94` (144 B), both ending exactly at `ebp-0x04`. **n = 2 direct callers** (a floor; `--xrefs` finds direct branches only).
- **The prediction's "boolean-ish success flag" — REFUTED**, and its own stated refutation condition thereby fired. `out1` is a **mutable count**: `0x00709FDF shl edi,4` uses it as an index and `0x0070A0A1 dec dword ptr [eax]` decrements it. The gate reading survives because the test is an equality against zero.
- **★ `pathCount == 0` means the START point is off the navmesh — NOT that the destination is unreachable. OBSERVED (Lane B), and it inverts the intuitive story.** All three zero-writes in the reachable chain are conditioned on the start (`0x0072B132` after `0x0072AE40` fails to resolve the start's trapezoid; `0x0072B57E`; `0x00727356`). An **unreachable** destination yields a **non-zero partial path** (`0x0072B4E8` string-pulls to the best node seen) and does **not** snap here. The accepted fast path cannot return 0 (the dedup loop floors at 1), and a zero from the fast path is never reported (`0x00709FD4 test edi,edi / je 0x70a0ae` reroutes into the full A\*). **So gate 2 snaps when the position WE granted is unwalkable.**
- **Lane B's "written on every path, never left uninitialised" — WEAKENED.** It is an assertion about three untraced callees, and it matters: a mechanical scan of `0x006055E0`–`0x00605840` finds exactly two references to `[ebp-0x60]` — `0x006057F0 lea` and `0x0060580A cmp` — so **the caller never initialises the slot**. The Tier-1 leg (`0x00709F06`) and the Tier-3a leg (`0x00727140`, single `ret`, two-armed store) provably write it. **The Tier-2 alternate-provider leg (`0x00709F44` → `0x00737350` → `0x00737940`) is UNVERIFIED by every lane and every skeptic.** If that path can return without writing, gate 2 reads uninitialised stack and the snap decision is non-deterministic. **This is the one live hole in the decode.**
- The `300.0f` handed to gate 2 as `maxDist` is **inert on the common path**: `0x00709F45` computes its own budget `sqrt(distSq) + 0.5` (`0x00709FB1 fadd qword [0x945b40]`). `maxDist` is consumed only on the Tier-3b fallback and the provider path. The same constant is a hard threshold at one call site and dead weight at the next.

**GATE 3 — `0x005FEF70(this=source, A, P)`, `0x0060580F`–`0x00605820`. OBSERVED.**
`__thiscall`, `ret 8`, strict 0/1, **exactly two exits** (`0x005FF51D` → 0, `0x005FF528` → 1) and **exactly one branch to the zero tail** (`0x005FF350 je`) plus the fall-through at `0x005FF51B`. In one line: *"standing at A, can I take a step toward P right now?"* — a candidate-direction test, not a path query.

Two ways to reach zero, both **positive findings of an obstruction**: (a) a neighbour agent inside a 60° forward cone (`fcomp [0x9458BC]` = 0.5f) whose `combinedRadiusSq` already contains A — compared **squared against squared** (`0x005FED20` ends `fmul st(0),st(0)` on both branches; `0x005FF348 fcomp qword [ebp-0x20]`); (b) `timeToEvent < 0.0005f`. The threshold is `0x00A53744`, read raw as **0.0005000000237487257f**; `test ah,5 / jp` gives **return 1 iff `timeToEvent >= 0.0005` OR NaN**, return 0 strictly below — so it is **inclusive** at the boundary and `+inf` ("no obstacle") returns 1.

**The zero is a REJECTION, not an error. CONFIRMED by all three skeptics.** There is no validity early-out, no null check on either pointer; bad state is reported through asserts (AgAgent.cpp 702/716/717/764/773), a separate channel. The two zero-paths are indistinguishable to the caller. Degenerate input fails **safe**: `to == from` produces NaN and returns 1.

ArenaNet's strongest single naming here, read from the image: **`(timeToEvent == (float)HUGE_VAL) || (m_point.position != obstacleCenter)`, `P:\Code\Engine\Agent\AgAgent.cpp`(773)** — one line that names the callee's return, its out-param, the sentinel, and pins `m_point.position` to `agent+0x78`, the exact offset the first half reads.

Gate 3 **discards the magnitude of its second argument** (only `normalize(to-from)` is used), and bounds its terrain search by the agent's **own cached AgMap cell rect** (`agent+0xF0..0xF3`, four signed bytes × `CELL_SIZE` 2048.0), not by anything derived from A — so if A has drifted out of that rect, gate 3 searches the wrong box. **UNVERIFIED** whether that is reachable in practice.

### ★ THE SNAP IS A WHOLE-ROSTER RESEED, not the player's position jumping — OBSERVED

No decode lane found this; two skeptics did, and I disassembled `0x0060603C`–`0x00606100` myself. On a zero return the caller does **not** merely correct `source`:

```
0x0060606A  a   = world[1].m_data[i]           ; skip null, skip (a.flags & 0x10000)
0x006060A2  rec = 0 ; rec.next = 0             ; clear that agent's 0x1C record
0x006060B3  setne bl on  i != this->focusId    ; -> arg2
0x006060D5  s   = world[0].m_data[i]           ; the SYNC twin
0x006060E2  call 0x6022B0(this=a, s, flag)     ; authoritative -> rendered
0x006060F4  jne 0x606051                       ; FOR EVERY AGENT IN WORLD 1
```

`0x006022B0` dead-reckons the sync agent at the **async** clock into a local ArenaNet names **`syncPoint`** (`syncPoint.position != AGENT_INVALID_POSITION`, AgAgent.cpp(2147)) and `0x00602B20` writes it into the async agent's `+0x78/+0x7c`. **One agent failing the three gates resyncs the entire visible roster.** If this project models the snap as "the player's character teleports", the model is wrong by a factor of the roster.

- **Lane A's "the fall-through runs `call 0x605f70` + `call 0x605840`" — WEAKENED.** True but it stops reading at `0x00606037`, before the loop that is the actual correction.
- **"`0x00605840` is the correction" — REFUTED.** It is the **history appender** (allocates via `0x00604BB0`, links at `record+0x04`) and it runs on the ordinary path too — for every non-client-controlled agent (`0x0060610B`) and every async agent. Anything treating it as the fix is inverted.

### Naming and layout — CORROBORATED, and two derivations retire

Every string below was read with `img.cstr()` in this session, not transcribed: `state->clientControlled` and `source.GetWorld() == WORLD_SYNC` (AgTrack.cpp 457/458), `asyncPtr` (AgTrack.cpp 519), `index < m_count` (`P:\Code\Base\rtl\Array.h`), `*pathCount <= maxCount` / `maxCount` / `pathCount` (Map.cpp 1239), `timeToEvent >= 0` and the HUGE_VAL line (AgAgent.cpp 764/773), `syncPtr` / `asyncPtr` (`P:\Code\Engine\Agent\AgMsg.cpp` 579/584), `time == context->world[m_world].timerQueue.GetTime()` (AgAgent.cpp 2211). Constants read raw: `0x00946560` = 100.0f, `0x00946564` = 300.0f, `0x00948654` = +inf, `0x00A53744` = 0.0005f.

- **`this = agentMgr + 0x1CC` — OBSERVED, stated not derived.** Lane A spent its two highest-ranked refutation risks on stride arithmetic; the constant is a literal at four call sites (`0x005FCA8E`, `0x0060229B`, `0x00602BB7`, `0x005FDA72`), each applied to `[0x47F660()+8]`. **Both of Lane A's top refutation risks retire.**
- **The two clocks are genuinely two clocks — CORROBORATED by a check that could have failed.** `[this-0x84]` and `[this-0x20]` differ by exactly `0x64`, the observed record stride, so they are the same field in adjacent records. Independently, `0x005FCFA8` computes `world[0].time - world[1].time`, stores it, and **buckets** it (`cmp eax, 0xffffd8f0` = −10000 ms; `cmp eax, 0x3e8` = +1000 ms). If they were one clock that whole block is constant zero. Two new named desync constants for this project.
- **The task prompt's framing "a different file means a different subsystem owns that array" — REFUTED.** `Array.h:587` is the container template's inlined `operator[]` bounds check; it names the *type*, not a different owner. The identical assert recurs at `0x005FF04A` on a different array in the same struct.
- **`0x005FF820` "cached fast path" — WEAKENED.** The control flow is as read, but the branch is **semantic, not an optimisation**: `+0x48` is `m_timeStopMovement` (AgAgent.cpp 978), so past the arrival time it returns the **stored destination exactly**, not an extrapolated overshoot. A server-side reimplementation cannot skip that arm as a cache.
- **The two asserts here are advisory.** `0x00487BC0` is `ret 4` with no noreturn path — on a bounds violation the client still performs the out-of-bounds read at `0x0060577D` and still dereferences a possibly-null `asyncPtr` at `0x005FF829`.
- **`+0xC4` — the skeptic's proposed CONTESTED label is REFUTED, and the field is an INTEGER.** One skeptic flagged `0x0060563A cmp dword [ebx+0xc4], 9` as contradicting a "facing = float" reading. `--field 0xC4 --in AgAgent` returns **5 accesses, n = 0 of them floating-point**: `push`, `cmp eax,[ecx+0xc4]`, `mov eax,[edi+0xc4]`, and two integer stores. The one site cited as evidence for float (`0x005FF546`) compares `+0xC4` as an **integer** and applies `fld` to `+0x60` — a *different* field. This is consistent with this document's existing reading (a 4-bit masked enum, dispatcher over 1..8) and **Lane C's float claim is refuted at the exact site it cited**.

### The corpus lane measured a proxy, and the gate cannot free-run — SAY THIS OUT LOUD

**Lane D returned a rigorous measurement, but not of the pair this section is about, and the static reading must not borrow empirical support from it.**

What it measured, **n = 5 movetap × gamesrv pairs, all `origin.origin_of` = `ours`, no pooling across origins**: SYNC is a **direct** cross-process read of `[AGBASE+0xE8]`'s `+0x78`, dead-reckoned by the binary's own formula. **ASYNC is a PROXY** — the client's own c2s self-report spliced from `0x003D`/`0x0047`. `movetap.py` reads the sync array only; **the async array at `[agentMgr+0x14C]` was never read**. So separation is knowable only at report instants, and the "moments the client evaluated the test" is itself approached by proxy (player `0x0029` grants).

Its results, with n: **24 snaps over 623 paired intervals. 0 of 24 began below the gate** (minimum before-separation **342.8 u**, max 3430.0 u) — a check that could have failed, since 21 of the 24 sit at a `dt` whose detector floor is below 300 u. **303 of 327 above-gate intervals (92.7%) produced no snap.** The relation is **non-monotonic**: the 1000–2000 u band is the largest above-gate band by exposure and the quietest (**1 snap in 140**). At 503 grants, separation p50 **120.5 u**, p90 462.5, max 2251.5. A time-shuffle control fires correctly (real P = 1.26e-07; re-paired ±3 s / ±7 s → 0.265 / 0.512 / 0.66 / 0.999).

**But Lane D's "a free-running 300 u gate would have fired at 52.4% of instants" must not be quoted — WEAKENED, and the mechanism is structural.** The gate cannot free-run: it is fenced behind `rec.clientControlled != 0` and `source.world == 0` (`0x00606002`, `0x00606013`), and the mechanism is **one-shot** — `clear_record` zeroes the flag, and only two player-input sites re-arm it. That alone predicts long stretches of large separation with zero snaps and predicts the non-monotonic bins, **with no veto from the 100 u match test**. Lane D's own hypothesis (the 100 u test short-circuiting) is therefore **UNVERIFIED and no longer the leading explanation**.

Two further disclosures the lane made itself: **`20260819T182652`** (2.38 MB, the arc's largest capture) has **no movetap partner** and contributes nothing; and Lane D re-flags that **`20260811T173940` is `ours`, not retail**, which matters because `movesync.py`'s `HARD_JUMP_SPEED = 400.0` / `HARD_JUMP_UNITS = 520.0` cite that corpus as retail-calibrated. Finally, Lane D's cuts used 300.0 u; the client's cut is 299.3326 u. The headline (0/24, min 342.8 u) is unaffected; the percentage figures shift by whatever falls in [299.3326, 300.0).

**Bottom line: the three gates are a pure static decode of one image (build 38797), n = 0 runtime observations. Which gate actually fires in our runs is UNKNOWN.**

### What this means for the fix — per gate, and the honest answer is mostly "no lever"

**GATE 1 — half a lever, and the half we hold is not the half that matters.** Operand A is ours end-to-end: `0x0029`'s handler `0x005FD890` indexes world[0] (`syncPtr`, AgMsg.cpp 579), and the bake `0x005FE950` writes `+0x78/+0x7C`, `+0x48`, `+0xB0/+0xB4`. **Operand B is not.** A capstone sweep of all seventeen AgMsg receive handlers shows **nine** fetch the async twin at `[agentMgr+0x14C]` and act on it (`0x0024`–`0x0028`, `0x002C`–`0x002F`), while **the two movement grants `0x0029` and `0x002A` touch world[0] alone**. That asymmetry *is* why reconciliation exists. Controlling one operand reduces to "grant positions near the client's last self-report", which restates "do not diverge" rather than suppressing anything.

**GATE 2 — NO LEVER, and it is a tripwire pointed at us.** Its failing operand is arg1 = **A = the SYNC position, the point our own `0x0029`/`0x002A` wrote**, tested against a navmesh our server does not have. We can trip it by accident and **cannot avoid tripping it by design without map data**. This is the gate a server-side position check could least reproduce, and the one most likely to be firing in our captures.

**GATE 3 — NO LEVER.** Of its three inputs, `this` and `from` are ours, but `to` is a navmesh product of gate 2, and the predicate sweeps neighbouring agents' predicted positions, radii, team and a visibility bitmap before running a terrain trace. **No message writes `timeToEvent` or its 0.0005 threshold.** Not a lever by any reading.

**And the gates are not the only snap route.** `0x005FCAA0` is a public no-arg ResyncAllAsync (`lea ecx,[ecx+0x1cc]; jmp 0x00605E40`) running the **same per-agent reseed with no gate evaluation at all**, with three callers, two of which fire when the *local* command layer's own path test `0x0070A170` returns 0. **A fix built on the three gates does not close this.** This is a candidate mechanism for Lane D's unexplained snaps 12–59 s after the last grant. **UNVERIFIED.**

**Preventing the snap is probably the wrong goal.** Each gate fires on a condition the client has just established it cannot walk out of. Suppressing the reseed leaves the rendered world permanently offset from the authoritative one — and per the reseed loop, **world-wide rather than cosmetic**.

**The one real lever is `0x002C`, and this document already knows what it costs.** Its handler `0x005FDA50` clears the track record **first** (`0x005FDA78`), then writes the sync twin (`syncPtr`, AgMsg.cpp 579) and the async twin (`asyncPtr`, AgMsg.cpp 584) — so neither follow-up notification reaches a gate, no reseed happens, and both copies land on the same point. **But that is the client's supported primitive for an INTENDED warp, not a snap suppressor**: FINDINGS:2983-2987 already records `authsrv.py:7036-7045` — an earlier build sent five and "three were arrivals, carrying the client 630, 189 and 765 units", removed as "the warp the player described". **Prediction can be switched OFF but not ON**: `0x00605F10` (which sets `clientControlled`) has exactly two callers, both in AgApi reached only from the ChCliBase local-command block, and of **472** distinct receive-handler VAs in the client's dispatch tables **exactly one** lands in `0x0081xxxx`–`0x0082xxxx`, and it is outside that block. (Entry points only, not transitive reachability — a strong negative, not a proof.)

**Nothing here is a fix, and none of it has been run.**

### Claims that DIED this round — do not re-quote

- **"Gate 1 is STRICT; exactly 300.0 u passes"** — **REFUTED.** 300.0 u snaps; the cut is `distSq >= 89600.0f` = **299.332591 u**.
- **"The sqrt is approximate at the ~1e-4 relative level"** — **REFUTED.** +6.22e-04 at the boundary, +3.18e-03 worst, **one-sided** (0/20,000 under-estimates).
- **This document's own "the 300.0f gate ~298.8 u" (FINDINGS:2861)** — **REFUTED**, off by 0.53 u; the crossing is a quantisation step, not a scaled offset.
- **"`out1` is a boolean-ish success flag" (the prediction)** — **REFUTED**; it is a count (`shl edi,4`, `dec [eax]`).
- **"`pathCount == 0` means the destination is unreachable"** — **REFUTED.** It means the **start** point is off the navmesh; an unreachable destination gives a non-zero partial path.
- **"`*pathCount` is written on every path" (Lane B)** — **WEAKENED** to an untraced assertion; the caller never initialises `[ebp-0x60]`, and the Tier-2 provider leg is unverified.
- **"The fall-through corrects `source`" (Lane A)** — **WEAKENED**; it reseeds **every** async agent.
- **"`0x00605840` is the correction"** — **REFUTED**; it is the history appender and runs on the ordinary path.
- **"`0x005FF820` has a cached fast path" (Lane A)** — **WEAKENED**; the `+0x48` arm is semantic (returns the stored destination), not a cache.
- **"A different file means a different subsystem owns that array" (the task's framing)** — **REFUTED**; `Array.h:587` is the container template.
- **"`+0xC4` is a float, so the `== 9` compare is CONTESTED"** — **REFUTED**; **n = 5** accesses, **0** floating-point, including the site cited as evidence.
- **"A free-running 300 u gate would have fired at 52.4% of instants" (Lane D)** — **WEAKENED**; the gate cannot free-run.
- **Lane D's own hypothesis that the 100 u match test is vetoing** — **UNVERIFIED and displaced**; `clientControlled` explains the same data structurally.

### Scorecard against the pre-registered prediction

**All six numbered items CONFIRMED** — twin resolution, the two dead-reckons on separate clocks, and all three gates with the right polarity. **The predicted CONSEQUENCE was right and is now sharper.** Its own stated refutation condition **fired** on item 4 (`out1` is a count, not a boolean-ish flag) and the gate reading survived it. **What it got wrong is a framing it never stated**: it treats the three gates as *the* snap condition. They are the snap condition only for an agent with `clientControlled != 0` in world 0, there is a second gate-free snap route, and the correction is a whole-roster reseed. **And it inherited "300 u", which is wrong by 0.667 u in the snapping direction.**

### Method note

The three skeptics wrote in separate private scratch directories (the collision that cost a blind-replication claim last round did not recur). The gate-1 threshold was measured independently **three times** — two skeptics and this session — reaching 299.3326 u by binary search over float bit patterns and by exhaustive scan. Everything above is build 38797, static, read-only, **n = 1 image, 0 runtime observations**. Nothing was written to the repo or the vault. **The single highest-value next measurement is a breakpoint at `0x0060580D` and `0x00605820` during a live desync**, logging `rec.clientControlled` at `[agentMgr+0x1CC+0x20] + id*0x1C` alongside separation: it says which gate fires, and it can refute the `clientControlled` mechanism outright.

---

## 2026-08-20, round 3 — THE TWO OTHER CALLERS, and gate 2 is KNOWLEDGE, NOT A LEVER

`0x00709E90` (gate 2's query) and `0x005FEF70` (gate 3's predicate) each have **exactly two direct callers**. Round 2 decoded the AgTrack side of both. This round decodes the other side of each, to ask what the client uses these functions *for* when it is not judging itself. Three blind decode lanes, then three skeptics re-parsing from raw bytes. **Every address, string, constant and push order below was re-read by this session from the pinned pristine 38797 image**, and the one repo-side measurement was re-run here rather than carried from a lane.

### THE DIRECT ANSWER: does the client plan with the query it is judged by?

**Same function, different question — and that is what makes gate 2 a tripwire rather than a self-consistency check. OBSERVED.** The client's own move planner and the desync gate both call `0x00709E90`, on the same navmesh object (`MapFindPath` resolves it itself at `0x00709E99 call 0x47f660 / mov esi,[eax+0x14]` and uses `[esi+0x74]`, so the two callers are on identical map data by construction). But **they never share a start point.** The planner's start comes from `0x005FC400`, whose `0x005FC42D mov eax,[edi+0x14c]` reads the **ASYNC / world[1]** array — the copy the player sees. Gate 2's `arg1` is the **SYNC** agent's dead-reckoned point (`0x006057AD`, on ebx, which `0x0060561A`'s guard names `source` with the assert `source.GetWorld() == WORLD_SYNC`, AgTrack.cpp:458). **The client never once asks "is there a path from the sync point?"** — that question is put in exactly one place in the image, and it is the gate. So gate 2 is not the client checking its own work; it is the client checking **our** work with its own tool, and the planner's success carries no information about the gate's verdict in either direction.

---

### THE TWO CALLERS

#### `0x0081ADB0` — the local player's move-to-point planner. ChCliBase.cpp. CORROBORATED.

**Extent verified from bytes, not from `func_start`:** `0x0081ADA4` is an int3 run, `0x0081ADB0` is `55 8b ec 81 ec d0 00 00 00` with a /GS cookie load, and `0x0081B1E7` is `c2 04 00` followed by six int3 — a `ret 4` thiscall.

ArenaNet names it. The assert at `0x0081B16D` reads

> `this == context->playerControlledChar` — `P:\Code\Gw\Char\Cli\ChCliBase.cpp` line **248**

and the caller supplies exactly that object: `0x00816510 call 0x47f660 / mov eax,[eax+0x2c] / mov esi,[eax+0x680]`, then `mov ecx,esi`. **Hero, NPC, minimap-preview and cursor-hover readings all die at the call site**, before the assert is even reached.

What it does with the query — `0x0081AF25`–`0x0081AF51`, re-read here:

```
MapFindPath(&curPos, dest, 10000.0f, maxCount=9, &pathCount(=9), &path[0..8])
```

The last push is `&[ebp-0xd0]`, so **arg1 = curPos (the start), arg2 = the clicked point (the goal)** — same slot roles as the gate, no inversion. `path[0]` is handed to AgApi `0x005FC7A0` as the immediate move target (that function's own assert, AgApi.cpp:1041, names the argument `targetPoint`), and `path[1..count-1]` are copied into **`m_path` at `this+0x70`**, whose capacity is pinned at **8** by `0x0081B073 cmp ebx,8 / jb` guarding ChCliBase.cpp:239 `index < arrsize(m_path)`. **So the 9 is `arrsize(m_path) + 1` — one immediate step plus eight queued waypoints.** The queue has a live consumer (`0x0081B580` pops `m_path[0]`, feeds AgApi, shifts the array down one 16-byte entry), so this is a real movement plan, not a preview.

**Does anything it writes move an agent? Yes — through the same mutator our own messages use.** `0x005FC7A0` reaches `0x00602A40`, and `0x00602A40` is the single shared agent-move setter: SMSG `0x0029`'s handler reaches it twice (`0x005FD913`, `0x005FD9B4`) on the SYNC array `[agentMgr+0xE8]`; the local planner reaches it once (`0x005FC8F0`) on the ASYNC array `[agentMgr+0x14C]`. **Same code, two world copies — the arc's two-copy model proved at one address.** `--xrefs 0x00602A40` gives **8** direct callers (`0x005FC8F0, 0x005FD913, 0x005FD9B4, 0x00602448, 0x00602984, 0x00604A43, 0x006062D5, 0x00606323`); five are unexamined and are the complete direct-call inventory of "things that can move an agent". New offset from ArenaNet's own name: `0x00602A48 test [ebx+0x20], 0x20000` guards `m_flags & INTERNAL_FLAG_IN_WORLD`, so **agent+0x20 is `m_flags`** and `INTERNAL_FLAG_IN_WORLD == 0x20000`.

**It is input-driven, and the negative was controlled.** Upward direct-call closure from `0x0081ADB0`, depth 7: **19 functions, 32 edges**, entirely in ChCliBase.cpp / ChCliApi.cpp / GmWalk.cpp / GmView.cpp / GmCoreAction.cpp. **0 of 32 edges and 0 of 19 functions lie in the AgMsg receive region `0x005FCF70`–`0x005FDE60`.** Positive control for that null: 27 distinct rel32 targets are called from inside that region, and re-running the identical containment test on three of them fired **3/3** (e.g. `0x0047F660`, 18 of its 1,089 call sites inside the region). The filter was capable of returning non-zero.

**⚠ WHERE THE GRAPH IS INCOMPLETE.** `--xrefs` searches `call`/`jmp rel32` plus every four-byte window at every alignment across all five sections. **It does not search indirect calls through a register or a vtable, or addresses the image computes rather than stores.** For the two nodes nearest the query this is unusually tight — `0x0081ADB0` and `0x008164C0` each report **1 direct reference and 0 stored VAs anywhere in the image**, which excludes a function-pointer table entry *for those two specifically* — but the same cannot be said for the five nodes further up the chain, and no lane disproved an indirect entry there. **"Input-driven" is a strong negative with a controlled filter, not a proof.** It is stated that way here deliberately: the last time this arc leaned on a filtered negative, it needed a positive control before anyone believed it.

**It ends in a send, inside three guards.** `0x008164C0` finishes at `0x00816563 call 0x00920720`, which builds `{u32 0x3E; f32 x; f32 y; i32 plane}`, 16 bytes, and hands it to GcGameCmd → MsgConn. `schema/messages.json`'s `GAME_CMSG_0062` is `msg_header + vec2 + dword`, `declared_unpack_size` **14** = 2+8+4 — an exact independent match (the schema came from OpenTyria; this came from the binary). **The send fires on both the success and the planning-failure legs** (`0x00816539 test eax,eax / jne 0x816562` skips only a local fallback) — ⚠ **but that claim was WEAKENED by a skeptic and the weakening is right**: three earlier guards can suppress it entirely — a map-extents rejection of the picked point (`0x008164CB call 0x70a5c0` + four float compares), a null `playerControlledChar`, and **bit 4** of `[esi+0x10c]`. Note the callee tests a *different* bit of the same word, **bit 8** (`0x0081AEE4 test dword ptr [esi+0x10c], 0x100`). Two distinct bits of one flags word, either of which suppresses a move.

#### `0x00600500` — AgAgent's obstacle-sidestep waypoint computer. AgAgent.cpp. CORROBORATED.

**⚠ `func_start` is wrong here, and this is its second miss in this arc.** It reports `0x00600140`. The real entry is `0x00600500`: `55 8b ec 83 ec 7c` + `a1 40 44 bf 00 / 33 c5 / 89 45 fc`, paired with `0x00600832 xor ecx,ebp / call 0x5ae7a9` and `0x0060083D ret 0x10`; both direct callers (`0x00600ABE`, `0x006018D2`) target `0x00600500`. **The heuristic's actual failure mode is now named: there is NO int3 padding before it** — `0x006004FF` is the previous function's `c3`. Same for `0x00600840`. That is more useful than "wrong a second time": the heuristic is unreliable specifically where the linker packed two functions flush.

Signature, with ArenaNet's own parameter names:

```
Point __thiscall AgAgent::<sidestep>(Point* ret, Point* point,
                                      Vec2* obstacleCenter, float combinedRadiusSq)
```

The naming assert is the refutable kind. A lane derived `[ebp-0x48]` independently as `(dy*(vx-px) - dx*(vy-py)) / len` — the signed perpendicular distance from `obstacleCenter` to the line `point -> m_targetPoint.position` — **before** reading the string; ArenaNet calls it `distFromLine`:

> `MathSqrt(combinedRadiusSq) + 1.0f >= distFromLine` — `P:\Code\Engine\Agent\AgAgent.cpp` line **1261**

and the branch polarity matches exactly (`fcompp / test ah,0x41 / jnp` skips on `<=`). The routine computes **one** waypoint — `point` displaced perpendicular to the agent's velocity by `(combinedRadius + 10.0) − |distFromLine|`, on the side away from the obstacle — validates it, and returns it or `AGENT_INVALID_POSITION`.

**New agent offsets, all from ArenaNet's own names:** `+0x9C/+0xA0 = m_targetPoint.position.x/.y` (AgAgent.cpp:1250, `m_targetPoint.position != AGENT_INVALID_POSITION`); `+0x64` = the avoidance retry counter; `+0x40` = a collision deadline. **`AGENT_INVALID_POSITION = (+INF, +INF)`** — `0x00948654` holds `0x7F800000`, and it is the same sentinel that pads the unused tail of ChCliBase's `m_path` and that GmView screens a failed world-pick against. Also new: `0x00600937` asserts `timeToEvent >= 0` (AgAgent.cpp:1339) on the return of `0x0070A0E0` — **independent confirmation, from a call site this arc had never looked at, that `0x0070A0E0` returns `timeToEvent`**, which round 2 asserted from inside `0x005FEF70` alone.

**PREDICTION2 said this call sits in a candidate-direction loop. REFUTED.** Branch enumeration over `0x00600500`–`0x0060083D`, n=15 (4 backward, 11 forward), re-run by two skeptics: the only true back edge is `0x00600812 jb 0x600804`, the plane-consistency walk over the returned nodes. `0x006005DA` is a shared **error exit** — it loads +INF, stores the sentinel into the return buffer, and `0x006005FF jmp 0x60082b` forward to the epilogue. It has **three** predecessors, one more than the prediction knew about (**CORRECTED 2026-09-04, studies/movecode/FINDINGS.md §1z-be.2: FOUR** — the fall-through at `0x006005D8`, when the obstacle's `combinedRadiusSq` covers `m_targetPoint`, reaches the exit before any query) (`0x0060079C` after `0x0070A150`, `0x006007B0` after `0x005FEF70`, and `0x00600806` from inside the plane loop). The retry lives one frame up in `0x00600840` and is **bounded at 6**: `mov ecx,[esi+0x64] / lea eax,[ecx+1] / mov [esi+0x64],eax / cmp ecx,6 / jae`, identical at both call sites (n = 2 of 2). What that loop iterates is **successive collision events**, not directions — each pass re-runs the swept terrain trace and acts only when time-to-impact rounds to **0 ms**.

`0x00600840` itself has **4** direct callers, one of which is `0x00602AEB` — inside the shared mutator `0x00602A40`. So setting a destination, from either world copy, runs avoidance immediately.

---

### THE 4-vs-9 maxCount ASYMMETRY: **INCIDENTAL. REFUTED as a lever, twice, on the bytes.**

PREDICTION2 asked whether a stricter bar for judging than for planning would be a real finding. It would have been. It is not what is there.

- **`*pathCount` is the number of points ACTUALLY EMITTED**, not a status. Both emitters compute it as `(cursor − base) >> 4`: `0x007297B2 mov ecx,[ebx+0x80] / sub ecx,[ebx+0x7c] / sar ecx,4 / mov [eax],ecx`, and the same shape at `0x00727368`. A capacity of 4 therefore yields **4**, never 0.
- **Overflow is silent and has no failure channel.** `maxCount` becomes an end pointer, `base + maxCount*16` (`shl eax,4 / add eax,ecx`), and the writer refuses to pass it: `0x007265A9 cmp esi,[edx+0x98] / jae 0x726623`, where `0x00726623` is `pop esi / ret` — **void**, no `eax` written. Truncation drops the point; it does not report anything.
- **A truncated result is not rescued into a zero either.** Map.cpp rejects a short path (`0x0070A028`, `0x0070A035`) and falls to `0x0070A0AE call 0x721a30`, whose result is returned **unvalidated** — `add esp,0x1c` straight into the epilogue at `0x0070A0CE`.

⇒ **A corridor needing five corners gives gate 2 `count = 4`, which is `!= 0`, which is NO SNAP.** Lane A's §5 "real behavioural consequence" — that gate 2 can report zero on a route the planner would have solved — **is REFUTED**, and Lane A had itself flagged the untraced fallback as its weakest link.

⚠ **And Lane C's structural refutation of the same claim was WEAKENED even though its conclusion was right.** "The 4-entry array exactly fills the frame, so 4 is capacity not policy" is circular — the compiler sized the frame *from* the declaration, and Lane A's 9-entry array is equally flush against its own cookie. The conclusion survives on the emitter mechanism above and on nothing else. **Cite the emitter, not the frame arithmetic.**

**Same verdict for the arg3 asymmetry (300.0f at the gate, 10000.0f at the planner), which Lane A raised as "a far bigger lever nobody has been looking at" — REFUTED, three independent ways.** (a) It never reaches the post-coincidence march at all: `0x00709FB1 fadd qword [0x945b40]` substitutes `|to−from| + 0.5`. (b) Where it *is* used — tier 1 and the A* fallback — it is a **remaining-distance budget**, and exhausting it jumps to the emitter's **success** exit; a smaller budget stops earlier and *successfully*. (c) It cannot bind at gate 2 at all: **gate 1 runs first and snaps above 299.332591 u straight-line**, so gate 2 is only ever evaluated when the two copies are within 299.33 u — a 300 u march budget for a goal at most 299.33 u away is never the binding constraint. **This closes Lane A's top open question outright.**

**Taxonomy correction that matters for anyone reading the ladder.** `MapFindPath` is **four** stages, not three, and the last is unvalidated. Tier 0 = coincidence (`0x00709ED7`, squared distance against `1.1920929e-07`, so ≈3.5e-4 u — effectively reachable only by the gate, since the planner already returned at `dist <= 1.0`). Tier 1 = an optional external provider (below). Tier 2 = `0x007219D0`, which receives a **normalized direction and a length**, not the goal — it is a **straight-line march**, and Map.cpp subjects its result to four post-conditions. Tier 3 = `0x00721A30 → 0x0072B0E0`, **the real graph search**, run on any tier-2 rejection and returned raw. `0x00709E90` carries **zero asserts of its own** (n = 0 over `0x00709E90`–`0x0070A0E0`); its Map.cpp attribution comes from its assert-bearing sibling `0x00709D30` and from PathApi/PathFind downstream. ⚠ **Lane A's citation of `0x00709E6C "*pathCount <= maxCount"` (Map.cpp:1239) as *this* function's post-condition is REFUTED** — that address is below `0x00709E90` and belongs to the sibling. The two functions also take **different arities** (`add esp,0x20` vs `add esp,0x1c`), which is why Lane A's slot map and Lane C's looked contradictory and were each correct for their own callee. **Quoting one slot map at the other function is off by one argument.**

---

### `0x005FEF70`: do the two callers treat a zero return the same way? **YES. The arc did NOT over-generalise the predicate. CONFIRMED, n = 2 of 2 direct callers.**

Both sites read 0 as *"that step is not takeable"* and both respond by **throwing away the position under test**:

- gate 3, `0x0060581E test eax,eax / je 0x60582b` → returns with `edi` still 0 → **SNAP**;
- `0x006007AE test eax,eax / je 0x6005da` → returns **AGENT_INVALID_POSITION**, candidate discarded.

Argument order matches too: at both sites the **last push is the position** (`0x006007A8 push edi`; `0x00605818 push eax` = `&syncPos`), so **arg1 = from, arg2 = to** in both. The round-2 reading — "standing at `from`, can I take a step toward `to` right now?" — survives from a completely independent direction, where `from` is unambiguously the agent's present position and the surrounding machinery is immediate collision resolution at `timeToEvent == 0 ms`.

**Two narrowings, both of which make the arc's claim smaller and therefore better:**

1. **It is never asked whether `to` is legal ground. OBSERVED, n = 2 of 2 sites.** At the avoidance site the candidate has already been certified by `0x0070A150` immediately before — a thunk into `0x00722B90`, which returns 1 only if the point resolves on the navmesh **with no snapping needed** (a bit-identical `fucompp` round-trip) **and** is not inside a path obstacle (PathObstacle.cpp). At gate 3 the `to` is `pathArray[0]`, a navmesh product by construction. **So the predicate is purely about transit, never about destination validity.** Any reading of gate 3 that leans on `0x005FEF70` to mean "the destination is a valid place" is unsupported.
2. **The two sites apply it at very different scales.** Here `|to − from|` is bounded by roughly `combinedRadius + 10` — tens of units. At gate 3, `pathArray[0]` can be far away. **Whether `0x005FEF70`'s internals are scale-sensitive is UNVERIFIED** — the 60-degree cone and the `timeToEvent < 0.0005f` cut both plausibly are, and no lane read the function end to end with an eye on how `|to − from|` is consumed. If it turns out to be scale-sensitive, "one predicate" becomes "two", and narrowing (1) is the part that survives.

⚠ Cross-caller caution, and it does **not** transfer: at `0x006007ED` the sidestep computer calls the sibling `0x00709D30(point, &delta, 1, maxCount=4, ...)` and treats `pathCount == 0` as **benign** — `0x006007FC je 0x600814` skips the plane loop and **accepts** the candidate. Different function, different arg3 type (integer `1` vs an f32 stored through `fstp dword [esp]`). **It is not a contradiction and must not be quoted as one.** What it does show is that a zero count from this query family is not intrinsically "off the navmesh". Also note `maxCount = 4` appears here too, in the avoidance path — further evidence that **4 is simply what AgAgent asks for.**

---

### WHAT THIS ROUND ACTUALLY SETTLED

**1. The CONTESTED item resolves in the arc's favour, and NARROWER than the arc stated. CONFIRMED.**
`pathCount == 0` reports that **the START point could not be resolved on the navmesh** — not that the destination is unreachable, and not the general "no complete path" signal Lane A proposed. In the tier that actually decides (`0x0072B0E0`) all three exits are start-conditioned: `0x0072B132` (the start's node lookup returned NULL), `0x0072B57E` (the working start copy was snapped during setup, per a bare 2-D x/y equality test at `0x007297D0`), and `0x0072B170` writes 1. **An unreachable goal yields a non-zero PARTIAL path** — the A* exhausts, takes the best-so-far node and string-pulls to it (`0x0072B4E8`). ⚠ **Lane A's "zero is the general no-complete-path signal, set at `0x00727356`" is REFUTED**: `0x00727356` is inside tier 2, and a tier-2 zero is not the function's answer — `0x00709FD4 test edi,edi / je 0x70a0ae` reroutes it into the full search. **Gate 2 does not test connectivity. It tests whether OUR point resolves at all.**

**2. There is a geometry-free channel from a wire integer to a snap. OBSERVED, and it is the round's strongest result.**
`0x0072AE4F mov eax,[ebx+8] / cmp eax,[ecx+0x20] / jb / xor eax,eax; ret` — the start point's plane field is **unsigned-range-checked against `staticData->map.Count()`** and the lookup returns NULL on failure, which becomes `*pathCount = 0` at `0x0072B132`. **ArenaNet's name for what `pathmap.py` calls a "plane" is `map`**, corroborated at three sites on the identical `+0x20` displacement, two of them carrying the name verbatim: PathApi.cpp:510 `map < path.staticData->map.Count()` and PathFind.cpp:1719 `m_map < m_path.staticData->map.Count()`. **A start plane index at or above the map's plane count snaps before a single float is touched.** The GOAL is resolved with the *snapping* variant instead, and a failure there does not take the same exit — **start must resolve exactly; goal gets snapped.** That asymmetry is the sharpest available statement of "whose position has to be on the navmesh," and it is a structural claim that could have failed.

Both of our `0x0029` plane fields reach that check: `0x005FF820`'s arrived arm copies `agent+0x88..+0x94` verbatim (so the plane is `agent+0x90` = wire field 3), and the in-flight arm uses `agent+0x80` (= wire field 4) at `0x005FFBD7`. **On the arrived arm the point gate 2 pathfinds FROM is byte-for-byte the destination our `0x0029` wrote.**

⚠ **Lane C's specific value 65535 is UNDECIDABLE and should not be quoted.** `0x00602A6C` reads the plane argument as a full dword and skips the write when it equals **−1**. Our schema types both fields as `word`. **Nobody checked whether the client's unpacker sign-extends or zero-extends.** If it sign-extends, `0xFFFF` arrives as −1 and is the *leave-the-plane-alone* sentinel — the exact opposite of a snap. **State the finding as "any plane index ≥ `map.Count()` and below 0xFFFF" and it is safe either way.**

⚠ **Lane C's "every operand of the failing test is ours" — WEAKENED.** `MapFindPath` also validates the **goal**: `0x0070A03A push ebx / lea eax,[ecx+4] / push [ecx+0x74] / 0x0070A042 call 0x722b90 / test eax,eax / je 0x70a0ae` — the same on-navmesh-and-not-in-obstacle test. So the client's own predicted position is an operand of the accept/reject decision too. And `agent+0x80`'s writer has **eight** callers, one of them inside the local planner's own AgApi path, so that field is not server-exclusive. **All three lanes missed both.**

**3. Tier 1 is `PathEngine.dll`, and that closes round 2's "one live hole in the decode" — conditionally. OBSERVED.**
Round 2 recorded a WEAKENED note: gate 2 passes an **uninitialised** `pathCount` (only two references to `[ebp-0x60]` in the whole function — `0x006057F0 lea` and `0x0060580A cmp`), and the Tier-1 provider leg was unverified to write it. It is now traced. `0x007372A0` is three instructions: `return ([obj+4] != 0)`. The object is built at `0x00737380`, which does `push 0xa6fedc` = **`"PathEngine.dll"`** → `call [0x939174]` = **`LoadLibraryA`** (confirmed against the import table), bails on NULL, then `push 1 / call [0x939288]` = **`GetProcAddress` by ordinal 1**; the wrapper's own module string is `P:\Code\Engine\Map\PathEngine\PeObject.cpp`. **Tier 1 is optional external middleware, loaded dynamically.** Tiers 0, 2 and 3 write `*pathCount` on every exit. **And `PathEngine.dll` is not present in the owner's install**: the pinned vault snapshot's `MANIFEST.json` records `source_dir = C:\gw` with only `Accounts.json` excluded, and the directory holds no such file. ⚠ **Caveat, stated because it is real:** `LoadLibraryA` also searches system directories and `PATH`, and the snapshot is dated 2026-08-14, so "absent from the install directory" is strong evidence and not proof. **Downgrade the hazard from "live hole" to "inert on this install, contingent on a DLL that is not there."**

**4. `0x0029` field 3/4 — CONFIRMED and CLOSED, but it is the third derivation, not news.**
`0x005FD890` builds `{x, y, field3}` into a local Point and passes `field4` as `0x00602A40`'s third argument; `0x00602A6C` writes it to `agent+0x80` unless it is −1, and `0x00602A93` writes the Point's plane to `agent+0x90`. So **field 3 = destination plane, field 4 = current plane** — CLICK_SWEEP variant 1 `(dest, cur)` is correct, and variants 3/4/5 (which force a 0) write a wrong `map` index into `agent+0x80`. ⚠ **`studies/smsg/FINDINGS.md`:130-133 already carries this as SOURCED**, and credits `studies/movement/FINDINGS.md` with having it first. **The actionable residue is a stale comment, not an experiment**: `authsrv.py:2838` still says "0x0029's 'planes' is not from the binary and remains UNVERIFIED", and `studies/smsg/FINDINGS.md`:1498 still lists it as debt.

⚠ **Lane C's "our navmesh agreement with the client has never been MEASURED" — REFUTED.** Both measurements are already in the tree, one of them in the docstring of the function Lane C quoted from. `pathmap.plane_at` records **n = 198 client position-and-plane reports, 189 landing inside a trapezoid whose plane index is exactly the plane the client named (95.5%)** — that *is* a measurement of index-space equality — with all 9 failures the known "client says 12, we find 0" bridge-over-ground case in a file with no height. `authsrv.py:8048-8055` records **n = 532: 93.8% clean, 5.5% off our mesh, 0.8% on a plane the client did not name, 0.0% ambiguous.** What is genuinely unmeasured is **our verdict against the client's own path-query verdict**, which needs a client run.

⚠ **Lane C's "our `walkable()` is plane-blind, so we cannot express the client's question" — WEAKENED.** True of `pathmap.walkable()`, false of the server at the site that matters: the click grant arm already computes `here = {t.plane for t in pm_c.containing(...)}` and `placed = here == {cur_plane}`, and refuses the grant when it fails. Where the plane-aware predicate is genuinely absent is the **heading arm**, which goes through `clip_to_walkable` → `pm.walkable` and, per its own docstring, **suspends collision entirely and returns the destination unclipped when our mesh does not cover the player**. That arm is **88.5% of 2,855 player-directed grants**.

**5. A MEASURED defect in our own content — n = 12, re-run in this tree.**
Every configured spawn was put through its own map's pathmap and asked which planes contain it:

| outcome | n | maps |
|---|---|---|
| OK (configured plane is one the geometry names) | **8** | 27, 143, 144, 146, 148, 280, 449, 558 |
| **PLANE-MISMATCH** (plane in range, wrong set) | **1** | **474** — spawn (0,0), config plane **0**, our geometry says plane **31** and only 31, out of 45 |
| OFF-MESH (point in no trapezoid on any plane) | **3** | 55, 90, 194 |
| no mesh available | 0 | — |

Map 474 is the shape that matters: **plane 0 is in range, so `0x0072AE52`'s bounds check passes and the trapezoid lookup then fails on the wrong plane's set → NULL → `*pathCount = 0` → gate 2 snaps.** A server-written, in-range, wrong integer. It also breaks the server's own click guard before any gate is involved — `placed = here == {cur_plane}` is false, so on map 474 the server silently refuses every click until the first accepted client report replaces `state["plane"]`.

**⚠ But read the severity honestly, which the skeptic who found this did not.** All four failures carry spawn `(0.0, 0.0)` — an **unset placeholder**, not authored content. **Every map with a real spawn coordinate passes, 7 of 7.** The fifth placeholder (map 558) passes by accident. So this is a latent data defect in placeholder rows, on maps this project does not currently serve; the maps actually in play (146/148 Pre-Searing, 449 Kamadan, 280 Isle of the Nameless) are all OK. (One discrepancy on the record: the skeptic reported 7 OK across 11 rows; this session's re-run gives 8 OK across all 12. The difference is map 558.)

**6. What our server actually writes, audited. OBSERVED, n = 12 config rows + every emit site.**
Every plane integer we send is either the literal **0** (all 12 `map_static_config` rows) or an **echo of the client's own number** — `state["plane"]` is assigned in exactly one place (`authsrv.py:2303`) and only inside `if accept:` on an accepted client position report, and the click arm's `dest_plane` is the client's own `values[2]` from CMSG `0x003E`. **So the channel in §2 exists and we do not currently fire it.** ⚠ **Lane C's "a newly-mapped channel to CAUSE a snap with a single out-of-range 16-bit integer" is therefore REFUTED as a consequence claim** — the mechanism is real, the exposure is not. It is a bounds invariant worth asserting, not an explanation for anything observed.

---

### WHAT THIS MEANS FOR THE FIX

**This is knowledge, not a lever. Say it plainly and do not cost a fourth fix against gate 2.**

Three things converge on that, and the third is the one nobody in three lanes said out loud:

1. **Both parameters that differ between the gate and the planner are verdict-neutral.** `maxCount` 4-vs-9 cannot produce a zero (the emitter counts what it wrote and drops silently on overflow); `arg3` 300-vs-10000 is a march budget whose exhaustion jumps to the *success* exit, and gate 1 fences gate 2 inside 299.33 u anyway. **There is nothing here to tune.**
2. **Every zero-write in the deciding tier is start-conditioned, and the start is ours** — but we only ever write plane 0 or the client's own echo, so we do not trip it on purpose or by accident today.
3. **★ GATE 2 HAS NEVER BEEN OBSERVED TO FIRE, and gate 1 subsumes every snap this project has measured.** Gate 1 runs first and returns SNAP whenever **straight-line** separation exceeds **299.332591 u**, so gate 2 is reached only below that. The arc's runtime lane measured **24 snaps over 623 paired intervals, with 0 of 24 beginning below the gate and a minimum before-separation of 342.8 u straight-line** (max 3,430.0 u). Every observed snap is explained by gate 1 alone; gates 2 and 3 were never evaluated at any of them. The proxy caveats are real — the async position is approximated from the client's own self-reports, and the before-separation is not the gate's own dead-reckoned instant — but **this is the only runtime evidence that exists and it points away from gate 2.** Three lanes wrote thousands of words about a gate with **n = 0 observed firings**.

**Two corrections to this document's own §"What this means for the fix" (round 2).**
- "We **cannot avoid tripping it by design without map data**" is **stale**. We have the map data: `toolkit/mapdata/pathmap.py` reads `PATHING_CHUNK = 0x20000008` out of the owner's own `Gw.dat` at run time, the extractor is in this repo, the layout is credited to GuildWarsMapBrowser in `PLAN.md` §6.1's derivation register and `THIRD-PARTY-NOTICES.md`, and nothing is committed. **Provenance is not the blocker on the navmesh route** — scoring it as one would be exactly the over-refusal `CLAUDE.md` warns about.
- The WEAKENED note on `*pathCount` being written on every path can be **narrowed to "inert on this install"** per §3 above, with its DLL-search caveat carried along.

**What a route would cost, priced rather than recommended** (three items, cheapest first — none of these is a fix for a symptom we have measured):

- **Assert the spawn-plane invariant** — ~20 lines plus a test entry in `TESTS.md`. It reuses `pathmap.containing`, which the click arm already calls, and it would have caught map 474 and the three off-mesh placeholders. **Cheap, defensive, and it closes the only measured defect three lanes and three skeptics produced.** Value is bounded by the fact that no map currently served fails it.
- **Fix two stale citations** — `authsrv.py:2838` and `studies/smsg/FINDINGS.md`:1498 both still call `0x0029`'s plane fields UNVERIFIED against three independent binary derivations. Minutes.
- **Make the heading arm plane-aware** — `pathmap.plane_at(x, y, prefer=cur_plane)` already exists and is measured at 189/198. Today the heading arm sends `(plane, plane)`, asserting the destination's plane equals the current one because "we cannot know the destination's plane from a heading". ⚠ **Retail does not do that**: over **n = 987** live `0x0029`, fields 3 and 4 are equal in 973 and **differ in 14 (1.4%)**, and those 14 are the plane transitions. So we deviate from ArenaNet's own shape on exactly the population where it matters, on 88.5% of 2,855 player-directed grants. **Price it with its failure mode stated**: `plane_at` is wrong ~5% of the time and is wrong exactly at bridges and stairs, which is where the two symptoms players actually report live. That makes it a **candidate to price, not a fix to ship** — and it is a candidate for the *symptom*, not for gate 2, which we have no evidence ever fires.
- **The thing that would actually decide anything is still a runtime measurement, and it has not moved.** A breakpoint at `0x0060580D` and `0x00605820` during a live desync, logging `rec.clientControlled` at `[agentMgr+0x1CC+0x20] + id*0x1C` alongside separation. It says which gate fires, it can refute the `clientControlled` mechanism outright, and after this round it can also settle whether gate 2 is ever reached at all. **Everything above is static: n = 1 image, 0 runtime observations.**

---

### Claims that DIED this round — do not re-quote

- **"The 4-vs-9 maxCount asymmetry is a stricter bar for judging than for planning"** (PREDICTION2) — **REFUTED.** `*pathCount` is the emitted count (`0x007297B2`–`0x007297C3`); overflow drops silently through a void return (`0x00726623`); the fallback returns truncated results unvalidated (`0x0070A0C6`→`0x0070A0CE`).
- **"Gate 2 can report `pathCount == 0` on a route the client's own planner would happily have solved"** (Lane A §5) — **REFUTED**, same mechanism. Lane A flagged it as its own weakest link and was right to.
- **"arg3 300.0f vs 10000.0f is a 33× asymmetry and a far bigger lever than 4-vs-9"** (Lane A, open question 1) — **REFUTED** three ways; arg3 is a march budget, exhausting it succeeds, and gate 1 fences gate 2 below 299.33 u so it can never bind.
- **"Gate 2 is a self-consistency check on the client's own navmesh"** (PREDICTION2's consequence) — **REFUTED.** The planner starts from ASYNC (`0x005FC42D`), the gate from SYNC; the planner is never asked the gate's question.
- **"`0x006007A9` sits inside a candidate-direction loop; `0x006005DA` is a loop head"** (PREDICTION2) — **REFUTED.** n = 15 branches, one back edge, and it is the plane walk; `0x006005DA` is a shared sentinel exit with three predecessors.
- **"`pathCount == 0` is the general no-complete-path signal; start-off-navmesh is one way to get there"** (Lane A) — **REFUTED.** That reads a tier-2 zero as the return value; `0x00709FD4` reroutes it into the full search, whose deciding exits are all start-conditioned.
- **"`0x00709E6C '*pathCount <= maxCount'` (Map.cpp:1239) pins `0x00709E90`'s parameter names"** (Lane A) — **REFUTED.** That address is inside the sibling `0x00709D30`; `0x00709E90` has **n = 0** asserts of its own.
- **"Our navmesh's agreement with the client's has never been measured"** (Lane C) — **REFUTED.** n = 198 (189 exact plane matches) and n = 532 (93.8% clean) are both already in the tree.
- **"A single out-of-range 16-bit integer is a channel from our wire bytes to a warp"** (Lane C) — **mechanism CONFIRMED, exposure REFUTED.** Every plane we write is literal 0 or the client's own echo.
- **"65535 is reachable and snaps unconditionally"** (Lane C) — **UNDECIDABLE.** `0x00602A6C` compares against −1 as a dword and the wire field is a `word`; nobody checked the widening. Quote it as "≥ `map.Count()` and below 0xFFFF".
- **"Every operand of the failing test is ours"** (Lane C) — **WEAKENED.** `MapFindPath` validates the goal too (`0x0070A042 call 0x722b90`), and `agent+0x80`'s writer has eight callers including one in the local planner's path.
- **"maxCount 4 is capacity not policy, because the array fills the frame"** (Lane C) — **WEAKENED**; the argument is circular. The conclusion holds on the emitter, not on frame arithmetic.
- **"The CMSG 0x3E goes out whether or not the local plan succeeded"** (Lane A) — **WEAKENED.** True, but inside three earlier guards: a map-extents rejection of the picked point, a null `playerControlledChar`, and bit 4 of `[esi+0x10c]` (note the callee tests bit **8** of the same word — two different bits).
- **"Our `walkable()` cannot express the client's plane question"** (Lane C) — **WEAKENED.** The click arm already does; the **heading** arm does not.
- **"The `0x0029` field 3/4 assignment can now be closed from the binary"** (Lane C) — **CONFIRMED but not new**; `studies/smsg/FINDINGS.md` carries it as SOURCED and this is the third independent derivation. The debt is two stale comments.
- **This document's round-2 "we cannot avoid tripping gate 2 by design without map data"** — **REFUTED.** `pathmap.py` reads the pathing chunk out of the owner's own `Gw.dat` at run time; the data is not the missing piece.
- **This document's round-2 "the Tier-2 provider leg is the one live hole in the decode"** — **WEAKENED to inert.** It is `PathEngine.dll`, dynamically loaded, and absent from the owner's install directory (with a `LoadLibrary` search-path caveat).

### Scorecard against the pre-registered prediction

`PREDICTION2.md`, written before the lanes ran.

| Prediction | Verdict |
|---|---|
| `0x0081AF51`'s containing function is the client's own movement planner, turning a local move intent into a predicted path | **RIGHT**, and named: ChCliBase.cpp player move-to-point, `this == context->playerControlledChar` |
| "asks for 9 and iterates them ⇒ consuming a path, not testing proximity" | **RIGHT** |
| The 9 is a waypoint capacity | **RIGHT**, specifically `arrsize(m_path) + 1` = 1 immediate step + 8 queued |
| "the client PLANS with the SAME query the desync test JUDGES it with" | **RIGHT at the function level, WRONG as stated** — same subroutine and same navmesh, but different start world copy, different goal, 9 vs 4, 10000.0f vs 300.0f |
| ⇒ "gate 2 is a self-consistency check on the client's own navmesh" | **WRONG. REFUTED.** The planner never plans from the point the gate tests |
| Refutation criterion "server-message-driven" | **TESTED, did not fire**, with a 3/3 positive control — and stated with the indirect-call caveat intact |
| `0x006007A9`'s containing function is an obstacle-avoidance / candidate-direction search | **HALF RIGHT.** It is obstacle avoidance — but a **one-shot** sidestep computer, not a direction search |
| "`0x006005DA` is a loop head or continue-target" | **WRONG. REFUTED.** Error exit, three predecessors, one back edge in the function and it is elsewhere |
| ⇒ "a steering loop corroborates the `0x005FEF70` reading" | **RIGHT CONCLUSION, WRONG REASON.** The reading is corroborated — by a bounded 6-attempt retry one frame up, not by a loop at the call site |
| Refutation criterion "the two callers treat a zero return differently" | **TESTED, did not fire.** Identical polarity, identical meaning, n = 2 of 2 |
| "whether the 4 vs 9 is a meaningful asymmetry — a stricter bar for judging would be a real finding" | **WRONG.** It is incidental, and so is the 33× arg3 gap |

**And the framing it never stated, which is the round's real correction:** the prediction treats gate 2 as something worth finding a lever in. It is a gate that **gate 1 fences below 299.33 u** and that **has n = 0 observed firings** across the arc's only runtime measurement (24 snaps, 623 paired intervals, minimum before-separation 342.8 u straight-line). The decode is worth having. It is not a fix, and nothing here should be built against.

### Method note

Three decode lanes wrote in **separate, uniquely-named** scratch directories (the collision that cost a check two rounds ago did not recur), then three skeptics re-parsed from raw bytes. This session independently re-read every load-bearing address, string, float constant, push order and branch target above, and re-ran the spawn-plane measurement in this tree rather than accepting it. `func_start` was wrong once more (`0x00600140` for `0x00600500`) and the reason is now recorded rather than the count: **no int3 padding before the function**. Everything static is build 38797, **n = 1 image, 0 runtime observations**; the one repo-side number is **n = 12** configured maps. Nothing was written to the repo or the vault by the lanes or the skeptics.

### Orchestrator's own re-measurement of the spawn precondition (OBSERVED)

The consequence skeptic reported "4 of 12" configured spawns failing the client's
start-node precondition and named three maps. I re-ran it exhaustively through
`authsrv.load_pathmap` + `PathingMap.containing`, and the count is **3 of 12, not
4** — maps **55, 90 and 194** — so the named list was right and the total was
one high. **All three are literal `(0.0, 0.0)` placeholders**, not surveyed
spawns that drifted: five maps carry `(0,0)` (55, 90, 194, 474, 558) and two of
those happen to land inside a trapezoid anyway. So the honest statement is *"five
maps have no surveyed spawn point and three of them are consequently off-mesh"*,
which is a content gap, not a navmesh defect.

**But the same run found a defect the audit did not flag, and it is the shape
this round's decode predicts.** Map **474**'s spawn `(0,0)` resolves to
**plane 31**, while its static config declares **plane 0**. Every other
configured map agrees at plane 0 (n = 8 of 9 on-mesh maps). A config plane that
disagrees with the navmesh's own answer is precisely the input that makes the
client resolve the wrong plane's trapezoid set at `0x0072AE40` — the
geometry-free zero this section describes. It is latent today for the same
reason the rest of the channel is latent (the spawn is a placeholder and the map
is not in play), and it should be fixed when 474 gets a real spawn rather than
carried as a surprise.

---

## 2026-08-20, round 4 — THE WARP IS REPRODUCIBLE ON DEMAND, AND SUPPRESSING OUR OWN GRANTS REMOVES ~90% OF IT

**OBSERVED.** Five client runs on the owner's own machine, one operator, one
session, back to back. Every number below is read off the captures with
`movesync.py`'s repaired two-arm hard bar (implied speed > 400 u/s at
dt >= 0.05 s, or displacement >= 520 u below that floor). This is the first
round of this arc driven by PLAY rather than by corpus archaeology, and it
produced in one evening both things the arc had been missing: **a reliable
trigger** and **a clean control**.

### 1. The trigger — hold S and spam-click forward

| stamp | clicks | headings | **grants** | span | jumps | rate | p50 / max | displacement |
|---|---|---|---|---|---|---|---|---|
| `20260820T182554` keyboard only | 0 | 18 | **0** | 26.2 s | **0** | 0.00/min | — | **0 u/min** |
| `20260820T182934` click, then keyboard | 5 | 74 | **0** | 114.8 s | **0** | 0.00/min | — | **0 u/min** |
| `20260820T183311` **hold S + spam-click** | 196 | 128 | **140** | 44.0 s | **5** | 6.82/min | 1,372 / 3,010 u | 11,182 u/min |
| `20260820T195137` baseline repeat | 207 | 132 | **199** | 41.8 s | **8** | 11.49/min | 795 / 1,917 u | 9,687 u/min |
| `20260820T195315` **`--grant-suppress`** | 180 | 112 | **2** | 43.2 s | **1** | **1.39/min** | 651 / 651 u | **903 u/min** |

**The grant count is the whole story.** Warps appear only where we grant, scale
with how much we grant, and all but vanish when we stop.

### 2. Why ordinary play does not warp — the server was already refusing

`20260820T182934` is the finding nobody expected: the owner clicked five times
and **the server answered none of them**, for reasons it logged verbatim:

> `click to (11388, 2298): not a straight shot -- leaving it to the client's own pathing`
> `click to (7961, 11308): we last saw the player 8.9s ago -- leaving it to the client's own pathing`

The staleness guard is strict enough that **2.1 s was too stale**. Because the
owner clicked and then keyboarded, every click was refused, no grant went out,
and — decisively — **the desync test was never evaluated at all**, since the
grant bake `0x005FEBEB` is one of only three callers of `0x00605FC0`. Zero
grants, zero jumps, and the client pathed itself to the clicked point anyway
(cos 0.994–1.000, closing 90–3,224 u across silences of 1.2–17.0 s, n = 5).

**Holding S defeats that guard**, because the client emits `0x003D` continuously
while moving, so "we last saw the player" never goes stale and every click is
granted. That is the whole trick, and it is why the arc could never summon the
warp before: casual play keeps the guard shut.

### 3. Keyboard movement is healthy — CORRECTED, and it corrects an operator report

`20260820T182554` is three ~8 s W-holds. **Every interval sits at 283–287 u/s**
against a 288 u/s walk, with exactly three `0x0047` stops (one per release), so
these were genuinely continuous holds and not re-presses. **0.00 hard jumps.**
The client walks correctly on its own local prediction with almost no server
involvement — 6 `0x0025` in 27 s and no grants at all.

This **refutes** the working report that "holding W gives ~1 s of movement then
stops": it did not reproduce under `--explorable` with no grant flags. The
symptom is real to the operator but is configuration-dependent and is NOT a
property of keyboard movement as such. What DID show up in the same capture is
the client's own unit/terrain collision, cleanly: during a stretch the operator
described as walking into a wall at ~40°, `x` froze at `11123.0`, speed fell to
**260–265 u/s**, and the report cadence tightened from 1.80 s to **0.50 s**.

### 4. `--grant-suppress` — the A/B

Two runs, 100 seconds apart, same operator, same play, one flag different.
**199 grants → 2. Hard rows 11.49 → 1.39/min (8.3×). Displacement 9,687 → 903
u/min (10.7×).** Both terms fell together.

**The pre-registered prediction was 3.1× on displacement and 2.5–3.7 hard rows
per minute. The result beat it on both.** Recorded because a prediction that was
too pessimistic is as much a miss as one that was too optimistic.

**A REVIEWER PREDICTION FAILED, in our favour.** The size term was expected to
worsen — surviving jumps 2.7× bigger, p50 1,969 u against 735 u. The single
survivor is **651 u, smaller than the baseline's own 795 u p50**. With **n = 1**
that settles nothing about the distribution; it only says the penalty did not
appear here. Two or three more runs would.

⚠ **VARIANCE IS LARGE AND THE A/B IS n = 1 PER ARM.** The two baseline runs of
the identical play differ by 1.7× in rate (6.82 vs 11.49/min) and 1.15× in
displacement. The effect survives that only because it is ~10×.

### 5. THE TIMING EVIDENCE THAT MOTIVATED THE FIX IS WORTHLESS — REFUTED

The fix was proposed on "4 of 5 hard jumps landed 0.10–0.23 s after a grant."
**That is a restatement of grant density and nothing else.** In `183311`, 140
grants span 32.7 s at one every 0.150 s, so **49.2% of the capture's wall clock
and 57.1% of its own report instants are also within 0.23 s of a grant.** A
rotation control — sliding the jump times against an untouched grant train over
199 offsets — scores a mean **2.39 of 5**, and 77 of 199 rotations equal or beat
the real 3 of 5. Fisher one-sided **p = 0.64** at 0.23 s, **p = 0.34** at 0.30 s.

**What survives the identical test**, and what the flag actually rests on:

- **THE LANDING GEOMETRY** — five sub-unit landings on points we had granted,
  **p = 3.0e-5**. Grant density cannot fake landing *on* the destination.
- **THE REPORTING-CONTROLLED 2×2** — 5.67 jumps/min while granting against 0.88
  while silent, **P = 3.4e-10**.
- **THE DECODE** — `0x0029` is SYNC-ONLY, so a grant issued while the player
  drives locally cannot reach the copy they see and can only create divergence.

### 6. What this is NOT — retail contradicts the premise

**ArenaNet grants continuously while the player keyboards and does not warp.**
88.5% of 2,855 player-directed live `0x0029` are triggered by a `0x003D`
heading, at a median inter-grant gap of 0.492 s. Retail does not warp because its
destination is **the client's own proposed endpoint plus 0.5 u** — it follows
rather than leads.

`--grant-suppress` forbids exactly what retail does most. **It works by making us
quiet, not by making us correct**, and "suppress the grant" already sits on the
dead-candidate scoreboard. It is a palliative for OUR stale destinations.

**The cost is real and is not visible in these captures.** `state["pos"]` feeds
aggro radius, `clip_to_walkable` and interaction range. Staying silent means our
authoritative position stops tracking the player, which will surface in combat
and interaction rather than in movement. **UNMEASURED:** the cost of rule 1 in
its own regime — the n = 5 evidence that a refused click still walks the player
is all from clicks after a STOP, where rule 1 never fires.

### 7. What is still unbuilt

**Grant the client's own endpoint**, continuously, the way retail does — so the
two copies agree instead of one going silent. FINDINGS' candidate #1 calls this
"the only shape that PREVENTS the snap rather than shrinking it." `--heading-grant`
was an attempt at it and is REFUTED for warping more, but its own record says why:
the destination was left to mature into a teleport. A SHORT, always-refreshed
endpoint grant is a different animal and has never been tried.

**And the server models no unit-vs-unit collision at all** (`authsrv.py`: "client
collides for itself and does it better than our navmesh does"). The client's model
is now decoded as a by-product of the gate work — radius at `agent+0xD0`, combined
radii via `0x005FED20`, a 60° forward cone, and the sidestep at `0x00600500`
displacing perpendicular to velocity by `(combinedRadius + 10.0) - |distFromLine|`,
all on ArenaNet's own field names. When an NPC blocks the player, their client
stops them and our copy walks through: the same divergence, arriving as
rubber-banding rather than as a snap.

## 2026-08-20, round 5 — THE REAL FIX, RESEARCHED: the invariant, retail's policy, and the offline harness that scores candidates before a client run

Five research lanes and three skeptic lanes, no client run, nothing written to the repo or the vault. Round 4 ended with a paragraph saying the fix "has never been tried"; this round found that paragraph contradicted 1,570 lines earlier in its own document, decoded what the client actually asks and when, re-measured retail's policy term by term against a nine-capture `live` corpus, built and then broke an offline scorer, and comes out with a smaller, sharper claim than it started with. **The headline is not a candidate. It is that the offline instrument cannot rank the candidates it was built to rank, and the reason it cannot is itself a finding about the mechanism.**

Origin discipline, stated once and honoured throughout: every `ours` number below comes from eleven loopback captures under `vault/captures/gamesrv/` plus five `movetap` pairs; every `live` number comes from the nine-capture retail corpus named in §3.1. **The two are never pooled and every figure carries its origin.** All static claims are build 38797 from the pinned image `vault/client/2026-07-29_221c13772c7a/Gw.exe`, n = 1 image, 0 runtime observations, and every address in this round was re-read by two lanes independently.

**Identifiers.** `REALFIX-*` tokens minted here and below are declared in
[REALFIX.md](REALFIX.md)'s legend — that file is the arc's buildable spec.

---

### 1. Round 4 §7 is REFUTED as stated, and the replacement is narrower than either reading

`FINDINGS:3598-3605` reads, in full: *"**Grant the client's own endpoint**, continuously, the way retail does… `--heading-grant` was an attempt at it and is REFUTED for warping more… A SHORT, always-refreshed endpoint grant is a different animal and has never been tried."*

**It has been tried.** `--client-endpoint` (`CLIENT_ENDPOINT`, `authsrv.py:1138`, block at `:9843-9878`) computes `ex,ey = reported + heading + 0.5·unit(heading)` — the client's own reported position plus the client's own vec2 plus retail's own +0.500 u constant, **unclipped**, sent on every `0x003D` while moving, **measured grant age at jump p50 0.28 s**, which is shorter-lived than `--heading-grant`'s 0.32 s and far shorter than retail's own 0.492 s median. That is a short, always-refreshed endpoint grant by every term in round 4's own sentence, and it is the *more* precise match than `--heading-grant`, whose point is computed from our stale `state["pos"]` and clipped by our navmesh. It ran as `20260819T182652` (`ours`) and was refuted at `FINDINGS:2028` under the header "`--client-endpoint` REFUTED, and it is the worst of the three".

Round 4 §7 names only `--heading-grant` and never mentions `--client-endpoint` by name or by its refutation. **Recorded as REFUTED-as-stated. A later lane must not re-propose or re-build `--client-endpoint` under the belief that it is fresh.**

What round 4 *appears* to mean and does not say is narrower: no configuration has combined a short always-refreshed client-endpoint grant with a fix to the underlying SYNC-ONLY architecture. Round 5 narrows it further, and this is the substantive correction: **the untried configuration is not a short lead. It is NO lead** — granting the client's just-reported position with the 765–768 u tip *dropped* — and that is a different animal again from both refuted runs. See §6.

---

### 2. THE REALFIX INVARIANT, as adjudicated

#### 2.1 When the client asks

`0x00605FC0` (the AgTrack dispatch) has **exactly 3 direct callers** — CONFIRMED independently by two lanes with `codescan --xrefs` — and they reduce to **two event classes**:

- **(A) the destination bake**, `0x005FEBEB` at the tail of `0x005FE950`, unconditional on the glide arm (`0x005FEBCE je 0x5febe1` skips only the facing dispatcher `0x00602660`). Reached by every `0x0029`/`0x002A`, by `0x0027`'s re-issue through `0x00602A40`, and by any local async destination set through the shared mutator.
- **(B) a hard SetPosition**, `0x006022A1` (the tail of the teleport primitive `0x006020B0`) and `0x00602BBD` (the unarmed arm of `0x00602B20`), which are the two arms of one dispatch. Reached from the arrival consumption (`0x00601817`/`0x00601899`, whose site compares `[esi+0x78]` against `[esi+0x9c]`), the collision resolver (`0x00600A91`), `0x002C`'s two arms (`0x005FDAE5`/`0x005FDB49`), and the resync's own writes.

**OBSERVED.** Xref counts CONFIRMED by the skeptic pass: 3 into `0x00605FC0`, 7 into `0x006020B0`, 7 into `0x00602B20`, each list matching. The recursion assert quotes ArenaNet's own words at `0x0060227B`: `!(*curr)->m_timeStopMovement || ((*curr)->m_targetPoint.position != AGENT_INVALID_POSITION)`, `P:\Code\Engine\Agent\AgAgent.cpp` line 2090 — a single assert cited as the evidence for a single claim, which is what the provenance gate permits.

**"Dispatched exactly once per SetPosition" is REFUTED.** `0x006020B0` recurses over the child array at `0x0060221E`, each recursion reaching its own `0x006022A1`; and after the bake's own dispatch, `0x005FEC7E` re-bakes each child, `0x005FEC9A` enters the bounded-6 collision frame whose `0x00600A91` SetPositions, and `0x005FECAC` (also `0x00602BE5`) reaches `0x006011F0`'s arrival consumer. **Every instant count in this round is a FLOOR**, and any rate arithmetic built on "one dispatch per grant" is a lower bound.

The fence upstream: `0x00606002` (`clientControlled == 0` ⇒ never called), `0x00606013` (`source.world == 1` ⇒ straight to the recorder), and one-shot behaviour — `AgTrack::Clear` (`0x00605F70`) zeroes the flag at `0x00605FA7` and the history head at `0x00605FAE`; only `0x00605F10` re-arms, with 2 callers, both under ChCliBase player-command sites (module named by assert: `this == context->playerControlledChar`, `ChCliBase.cpp` line 164, at `0x0081ad27`). **New this round:** the re-arm is a **no-op on an already-armed record** (`0x00605F3F cmp` / `0x00605F43 jne`), which the one-shot narrative has been mis-stating — it does not re-null the head on every player command.

#### 2.2 What makes it pass — and the exception that decides the whole policy question

The match test walks the history chain newest→oldest with `prev` seeded from `state.position`:

```
match ⟺ ∃ segment (node[i].position → node[i-1].position)
        with  ‖q − closestPoint(q, seg)‖² < 100.0²      (STRICT, SQUARED, straight-line)
        AND   walkPathLen(q, c) ≤ 100.0                 (INCLUSIVE, LINEAR, navmesh)
```

where `q = source[0x78..0x88]` — **the SYNC copy's own dead-reckoned position, never our grant** (`0x00602A40` writes `+0x88..+0x94`, `+0x9C..+0xA8` and `+0x80`, and n = 0 writes to `+0x78`).

**⚠ The conjunction is not unconditional, and the exception is exactly the regime that matters.** `0x00605AFF`/`0x00605B0C` test `a.x == b.x && a.y == b.y` and route a **degenerate** segment into a point test whose success at `0x00605B5E je 0x605c60` jumps directly to `0x00605C62 mov eax,1`, **skipping the walkable query pushed at `0x00605C40` entirely.** And segment 0 is degenerate exactly when `+0x48 == 0` at the recording instant: the recorder's `+0x48 == 0` arm (`0x00605909`) writes the same `[ebp-0x44..-0x38]` block into both `node.position` (push at `0x00605A60`) and `state.position` (the seed, `0x00605A38`). **Under keyboard movement, with no destination held, the 100 u test on segment 0 is straight-line only.** OBSERVED, new this round; it replaces the doc-level claim that "the two conjuncts differ on every axis that can be got wrong", which is true for segments 1..n and false for segment 0.

**The 100 u radius is re-measured and the ~99.6 u debt is retired.** `FINDINGS:3133` said the companion figure "should be re-measured before it is quoted again"; it now has been. Re-implementing the nine instructions at `0x0046E870` with the 256-entry LUT at `0x0093CAC8` and scanning **all 2,048,001 float patterns in [9000, 11000]**: the last passing `distSq` is 9983.9990234375 (true 99.9199631, approx 99.91996002) and the first failing is `0x461C0000` = 9984.0f (true 99.9199680, approx 100.23970795). **The single-leg effective TRUE threshold is 99.919968 u.** `[99.61, 100.00]` is the many-leg accumulation limit and is a different quantity. The method's positive control is gate 1: the same scan over [80000, 100000] (2,560,001 patterns) reproduces `89600.0f` → **299.332591 u** to seven significant figures, three times independently, including that **a true separation of exactly 300.0 u SNAPS**. **OBSERVED.**

⚠ **`FINDINGS:3037` and `HANDOFF.md`'s match-test description read ~99.6 u until this round's write-up; both are corrected in the same commit as this section.** And the supporting claim that the table sqrt's error is "one-signed positive" is **REFUTED as an exhaustive statement**: 27 under-estimates in 2,560,001 patterns over [80000,100000] (worst −4.474e-08 relative) and 16 in 2,048,001 over [9000,11000] (worst −3.701e-08). The bias is overwhelmingly positive and the boundary pattern itself over-estimates, so no conclusion moves — but "0 under-estimates" was an n = 20,000 sample quoted beside an exhaustive result.

**Where the polyline comes from — "client only" is REFUTED.** `0x00606103 test edx,edx / jne 0x606110` means a world-0 agent with `clientControlled == 0` falls through to `0x0060610B` and **appends**. The fence is closed after every snap until the next player local command, so during those windows **our own** sync-side bakes and SetPositions push nodes and rewrite `state.position`. The re-arm nulls the head (`0x00605F4F`) but never clears `state+8..+0x18`, so the seed that segment 0 runs to can be a server-written point that survives the re-arm. The control attribution in any policy argument must say "client, plus our own writes during fence-closed windows", not "client only".

Coarseness and expiry: a node is pushed on any movement-command change (`0x00605945`–`0x006059B4`) or when the head is older than **2500 ms** (`0x0060593A cmp eax,0x9c4`); 256-entry blocks are recycled when the block's newest entry is older than **5000 ms** (`0x00604C03 cmp ecx,0x1388`), stride `0x2c`, block span `0x2c04`. `seg_match` reads only positions — **no time filter at all** in `0x00605AF0..0x00605C6A`. The 250 ms constant at `0x00604F09` is in a different function and its role in the match test remains **UNVERIFIED**.

#### 2.3 What happens on a miss, and what a snap costs

```
A = deadreckon(sync,  world[0].time)      # 0x006057AD — OURS, end to end
B = deadreckon(async, world[1].time)      # 0x006057BA — never on the wire
GATE 1: MapDist(A,B,300.0,straightOnly=1) > 300.0f  -> SNAP   # 0x006057EA, cut 299.332591 u
GATE 2: MapFindPath(A,B,300.0f,4,&n,&P); n == 0     -> SNAP   # 0x0060580D, start-conditioned
GATE 3: step_is_clear(source, A, P) == 0            -> SNAP   # 0x00605820, 60° cone, 0.0005 s cut
        else                                           NO SNAP
```

`edi` is the sole return accumulator, n = 3 writes across `[0x605753, 0x60583E)`. A **match short-circuits all three**: `0x0060574C jmp 0x60582b` with `mov eax,edi` at `0x0060582E` and `esi` provably 0 there. The round-3 sentence "below 300 two further checks can still force the snap" was already recorded REFUTED-as-stated at `FINDINGS:2986-2988`; it is confirmed dead and should not be re-quoted.

⚠ **Two names in the address table are downgraded.** `asserts.py --at 0x00709E90 --span 600` returns **0 sites** and the only naming evidence (`*pathCount <= maxCount`, `Map.cpp(1239)`) sits at `0x00709E75` inside the sibling `0x00709D30` — which `FINDINGS:3420` already lists under "Claims that DIED this round — do not re-quote". `asserts.py --at 0x00709990 --span 400` also returns 0 sites. **The behaviour of both is OBSERVED; the names "MapFindPath" and "MapDist" are RECONSTRUCTION — project labels, not the client's word.** Any later document quoting them owes the qualifier.

**A snap is roster-wide, and it is worse than previously recorded.** `0x0060604C`–`0x006060F4` loops every agent in world 1, skipping nulls and `flags & 0x10000`, and `0x006060A2 mov [eax+ebx],0` / `0x006060A9 mov [eax+ebx+4],0` run **unconditionally** — zeroing not only every agent's `clientControlled` flag but **every agent's history head** (record+4, the same field `clear_record` nulls at `0x00605FAE`). One agent failing the gates destroys the entire visible roster's polyline. Modelling a snap as "the player's character teleports" is wrong by a factor of the roster, and the consequence — the next test after any snap has a NULL head and goes **straight to the gates** (`0x006056B8`) — applies to every agent at once.

And the gates are not the only route: `0x005FCAA0` is a public no-arg `ResyncAllAsync` (`lea ecx,[ecx+0x1cc]; jmp 0x00605E40`) running the same per-agent reseed **with no gate evaluation**, 3 callers (`0x004E6E82`, `0x00816499`, `0x0081655D`), two firing when the *local* command layer's own path test `0x0070A170` returns 0. **UNVERIFIED as a live route; a fix built on the three gates does not close it.**

#### 2.4 The bake, and the law that ranks every candidate

```
d        = D − [+0x78]                       # 0x005FEB57 fsub [esi+0x78]  ← from the COPY
S        = [+0x60] * [+0x5C]                 # 0x005FEBA4 fld / 0x005FEBA7 fmul
[+0xB0],[+0xB4] = unit(d) * S                # 0x005FEBBF / 0x005FEBC8
[+0x58]  = now ;  [+0x48] = now + trunc(|d|*1000/S), clamp ≥ 1
read(t)  = [+0x78] + vel*((t − [+0x58])*0.001)     # 0x005FFB40
```

**The bake measures `d` from `+0x78` — the copy — and never re-pins `+0x78` toward the player.** Re-granting re-aims; it does not correct accumulated error. That single instruction is why cadence alone bounds nothing, and it is what `FINDINGS:1486-1492` observed empirically ("stacking grants does not bound the teleport; it converts one large one into many small frequent ones") without naming.

**★ The `distSq ≤ 1.0` short-circuit dispatches nothing.** `0x005FEA85 fcom st(1) / test ah,0x41 / jp 0x5feae1` sends `distSq > 1.0` to the glide arm; **fall-through at `0x005FEA92` is the `≤ 1.0` arm**, which writes `+0x78..+0x84 = D` directly, stores the residual `fldz` into `+0xB0`/`+0xB4` (**velocity zeroed**), arms `+0x48 = max(now+1, 1)`, and `0x005FEADE ret 0xc`. CONFIRMED and strengthened by the skeptic pass: `0x005FE99C lea edi,[esi+0x78]` proves the distance really is measured from `+0x78`, and there is **no path from that arm to `0x005FEBEB` nor to the child-bake / collision / arrival fan-out at `0x005FEBF0-0x005FECAC`.** A grant within 1.0 u of the copy's own brought-forward position is the only server message that hard-writes `+0x78` and evaluates no test at all.

**THE INVARIANT.** *At every instant the client is asked to judge — a bake, or any hard SetPosition, with the fence open — the SYNC agent's own dead-reckoned position `+0x78` must lie within 99.919968 u of the client's history polyline (straight-line to the segment, plus a walkable conjunct that is skipped on a degenerate segment), or else survive three gates the server can neither see nor address.*

**REALFIX-O1** — the polyline is [current destination] → [current leg start] → [older leg starts]. Segment 0 looks forward *only* while the client itself holds a destination (`+0x48 != 0` at the recording instant, `0x006058D6`). **Under keyboard movement nothing ahead of the player is on the polyline, and everything behind on ground already walked is.** LAG is on the polyline by construction; LEAD is not. RECONSTRUCTION from OBSERVED control flow, and it is the single most load-bearing structural fact in this round.

**REALFIX-O2** — `t_max = 100 / ‖v_player − S·û‖`. At our measured median player speed of 111.7 u/s against a declared 288, `‖Δv‖ = 176.3` ⇒ `t_max = 0.567 s`. Retail's median inter-grant is **0.490 s** (`live`, n = 3,127) — *inside that bound*, and nothing in the derivation used retail's number as an input. CORROBORATED by a check that could have failed.

**REALFIX-O3** — `dist ≤ S · Δt_refresh` ⇒ the copy arrives before the next grant, `+0x78` is re-pinned to `D` exactly, and the lead is bounded by `dist` **with no assumption about the player's speed**. At Δt = 0.30 s and S = 288 that is 86 u. This is the only obligation the server can discharge from what it knows.

**REALFIX-O4** — copy speed vs player speed is unavailable; the server cannot know instantaneous player speed and the client can.

**REALFIX-O5** — every granted point must resolve on the client's navmesh, plane included (gate 2's failing operand is our own point).

**REALFIX-O0** — *a match must happen at all.* After every snap the head is NULL and the first test goes to the gates. Any family whose safety argument runs through the match owes this assumption explicitly.

**REALFIX-O6** — for `0x002C` only: `|D − async position|` must be small, and the server has never read the async array (`movetap.py` reads `[AGBASE+0xE8]`; `[agentMgr+0x14C]` is unread). UNVERIFIED, not satisfied.

**The runaway law, which unifies the two rival diagnoses.** The tree's standing attribution for `--client-endpoint`'s failure is the **speed** term (`authsrv.py:1094-1098`: "the player moved at a median 111.7 u/s while every grant told the client moveSpeed 1.0 = 288.0"); the invariant lane's is the **lead** term. **Both are one term.** The copy travels a lead `L` at `S` while the player travels it at `v_player`; harm accrues at `(S − v_player)` for `L/S` seconds, so the runaway is `L · (S − v_player)/S` per cycle and **the two variables multiply**. Retail is safe at `L = 766` because their `v_player ≈ S` (forward 288, backpedal 189.8 u/s = 0.659 × 288, n = 32, `live`); we are unsafe at the same `L` because ours is 111.7. **At `L = 0` the speed error cannot produce overshoot at all** — the copy parks at `D` and the short-circuit zeroes velocity — which is why zero lead is simultaneously the zero-speed-error configuration and why the lead family is not testing a variable the record blames on something else. RECONSTRUCTION, from OBSERVED pieces.

#### 2.5 Violation modes, with the corrections carried

**(a) The copy runs AHEAD — `--client-endpoint`.** `D` re-pinned every 0.34 s to ~766 u ahead of the player; `+0x78` integrating at 288 toward it; gap closing at 176.3 u/s; convergence onto the ray tip in 766/176.3 = 4.35 s ⇒ 13.8/min against a measured 14.6/min (−5.4%), and snap magnitude ≈ the tip (max 754 u, p50 582 u). Shape explained decisively, rate suggestively.

⚠ **Two corrections to how this was argued.** First, the sawtooth rows pooled runs: 582 u p50 / 754 u max / 13-of-197 are `20260819T182652` (`--client-endpoint`), while 119.7 u and 124.8 u/s are `20260819T171436` + `authsrv-20260819T171153-c1.jsonl` (`--heading-grant`), and `FINDINGS:3201` records that `182652` **has no movetap partner and contributes nothing**. Same origin, different configuration — the arithmetic `(582 − 119.7)/124.8` is cross-configuration and must be labelled or dropped. Second, **the "one-shot fence throttles the rate" reading is REFUTED as co-equal**: the fence closes only on a snap and re-opens on any player local command; in a run described as holding S and spam-clicking, with 193 grants in 65.6 s, the closed windows are sub-second and the fence cannot remove ~160 dispatches/min. **The runaway mechanism is the surviving reading.**

**(b) The copy parked far behind — the default build.** `0x0029` is SYNC-ONLY and `0x0025`'s async arm is gated shut for the client-controlled agent: `0x005FD5CD cmp dword [eax+ecx*4],0 / jne` skips when a record is armed, and `0x005FD5D3 cmp ebx,[esi+0x1e0] / je` skips when the agent id *is* the controlled agent — the id latched at `0x00605F45` inside the flag==0 branch and cleared only on removal, so **the second gate is permanent for the session**. Separation p50 1,164 / p90 2,163 / max 3,648 u (n = 251 paired reports, `ours`, movetap-confirmed).

⚠ **The "Kills: any policy that refuses to grant" verdict is DOWNGRADED.** The cited run `20260820T182934` measured 5 of 5 clicks refused, 0 grants, **0 jumps, 0 u/min**, and a client that pathed itself to the clicked point anyway (cos 0.994–1.000, closing 90–3,224 u across silences of 1.2–17.0 s, n = 5). The cost is real and lives in aggro radius, `clip_to_walkable` and interaction range, and `FINDINGS:3589-3595` marks it **UNMEASURED**. Record it as an unpriced non-movement cost, not a kill.

**(c) The granted point off-navmesh — gate 2.** Mechanism CONFIRMED including the geometry-free plane channel (start plane ≥ `map.Count()` and below 0xFFFF returns NULL at `0x0072AE4F`→`0x0072B132` before a float is touched; 65535 UNDECIDABLE). **Exposure today is nil** — every plane we send is literal 0 or the client's own echo — and **gate 2 has n = 0 observed firings**: 24 snaps over 623 paired intervals, 0 of 24 beginning below the gate, minimum before-separation 342.8 u. Gate 1 fences it. The severity note travels with the citation: every map with a real spawn coordinate passes, 7 of 7; the maps in play (146/148/449/280) are all OK; the latent instance is map 474's `(0,0)` placeholder.

**(d) Gate-3 crowding.** Reached only below 299.33 u. A neighbour inside the 60° forward cone whose `combinedRadiusSq` contains `A` returns 0 ⇒ snap at *any* separation, including zero, and it arrives as rubber-banding rather than as a teleport, which the hard bar does not count. ArenaNet's own naming, cited as the single assert it is: `(timeToEvent == (float)HUGE_VAL) || (m_point.position != obstacleCenter)`, `AgAgent.cpp` line 773. The collision resolver itself hard-SetPositions, so **a crowd generates test instants nobody asked for.**

**(e) One-shot and expiry.** The second mistake is judged harder than the first (NULL head ⇒ straight to the gates); a pass shrinks the budget (`lastMatch->next = NULL` at `0x00605746`); the chain covers at most ~5 s of past; and silence does not remove the test — `--grant-suppress` removes the *bake* caller only.

---

### 3. Retail's policy, as an executable spec

#### 3.1 The nine-capture corpus is RESOLVED

The recon lane flagged the 9-member `live` subset as UNVERIFIED as to membership. It is now settled and independently reproduced by two lanes working from separate loaders: of 13 `origin=live` session directories, **exactly 9 carry ≥ 1 player-directed `0x0029`**, and that set reproduces every FINDINGS denominator to the unit.

`20260807T143055, 20260810T235916, 20260817T180610, 20260817T183323, 20260817T183756, 20260817T231139, 20260818T094648, 20260818T132739, 20260819T132414`

(`183323` contributes 3 grants and 0 headings.) Denominators, `live`: `0x003D` **2,675**; player `0x0029` **3,170**; heading-paired **2,938**; on-ray **2,599**; off-ray **339**; at +0.500 **1,642**; `0x0047` **114**; `0x003E` **26**; inter-grant n **3,127**, p50 **0.490 s**, **82.1%** ≤ 1.0 s. **OBSERVED, and cite this set rather than "9 live captures".**

#### 3.2 The policy

```
on c2s 0x003D (pos=v[1], plane=v[2], vec2=v[3], movementType=v[4]):
    u        = normalize(vec2)                       # |vec2| ∈ 765.017 .. 768.000
    endpoint = pos + vec2 + 0.500*u                  # D1  ADJUDICATED
    dest     = <world-anchored truncation>(pos, endpoint)   # D2  OBSERVED-new, §3.4
    send 0x0025 (agent, u, movementType)             # S1
    if movementType != last_family: send 0x002B (agent, rate(family), family)   # S2
    send 0x0029 (agent, dest, dest_plane, cur_plane) # S3  — 0x0029 is ALWAYS last

on c2s 0x0047 (pos=v[1], plane=v[2]):
    send 0x002B (agent, 1.0, last_family)            # 77.2% of stops
    send 0x0029 (agent, pos, plane, plane)           # zero-distance echo, 61.4%
    # NOT 0x0028. 22.8% of stops draw nothing at all.

on c2s 0x003E (click):
    send 0x0029 (agent, clicked_point_verbatim, dest_plane, cur_plane)
    # then let the heading stream supersede it; do not hold it.
```

**ADJUDICATED terms, reproduced this round:** D1's +0.500 u constant (1,642 of 2,599 on-ray rows at residual 0.500 ± 0.01; **1** of 2,599 within ±0.01 of the bare endpoint; the residual histogram over [−2,+2] is a single spike, `{0.0: 2, 0.4: 1, 0.5: 1643}`; per-capture rate **32.8%–88.3%**, so **cite the constant, never the rate**). `0x0025`'s unit-length content (p50 0.999593, n = 2,256, 100% < 1.01) and its trailing-byte `movementType` echo (2,217/2,256 = 98.27%). The burst shapes: `0x0025`+`0x0029` **1,506 (49.0%)**, `0x0025`+`0x002B`+`0x0029` **734 (23.9%)**, bare `0x0029` **585 (19.0%)**, and — omitted by `FINDINGS:1746` — `0x0029`+`0x002B` **243 (7.9%)**, over 3,071 grant bursts of 3,336, per-capture **36.4–88.5 / 5.8–29.2 / 3.8–34.0 / 1.4–9.9%**. Every one of those counts was reproduced by a second lane using its own burst decoder.

**OBSERVED-new, with the spread that the pooled figure hides:**

- **`0x0025` carries nothing the server computes.** The vec2 is `unit(client's own vec2)` — angle to it p50 0.000°, **2,193 of 2,231 exactly 0°**, the 38-row tail being family transitions.
- **Message order is a hard rule.** `0x0025 → 0x0029` 1,499 · `0x0025 → 0x002B → 0x0029` 707 · bare 568 · `0x002B → 0x0029` 200 · `0x002B→0x0029→0x002B→0x0029` 32 · `0x0029→0x0029` 17. **`0x0029` is last in every shape that contains it; `0x0025` precedes `0x002B`; zero counter-examples in 3,023 of 3,071 bursts.**
- **The stop reply is a zero-distance `0x0029` and the companion is `0x002B`, not `0x0028`.** Of 114 stops: 98 (86.0%) answered within 1.0 s, of which exactly **70** land < 1 u from the reported stop (`|dest − stop|` p50 **0.000 u**), latency p50 0.034 s. `0x002B` present in 88 (77.2%) — **per capture 45.5% / 50.0% / 66.7% / 75.0% / 77.8% / 86.0% / 88.9% / 100.0%, and 57 of the 114 stops come from one session**. `0x0028` in 7 (6.1%). `FINDINGS:1338`'s count of 70 is preserved; its denominator of 88 is corrected to **114**. Its "257 corpus-wide, 81 naming the player" `0x0028` census is also stale — on the adjudicated 9 the counts are **282 and 95**, of which only **7 (7.4%)** fall in a stop window. **A server author must not send `0x0028` on a stop.**
- **The first `0x003D` after a stop is not special**: 112 of 112 answered, latency p50 0.035 s, identical to mid-run (2,559/2,563 = 99.8%). No resume gate.
- **Family change ⇒ `0x002B`.** Within a 0.06 s burst, changed 503/552 (91.1%) vs same 156/2,002 (7.8%). A second lane using a slightly different burst-membership rule gets 576/586 (98.3%) vs 242/2,043 (11.8%). **The direction replicates on every capture that has family changes; the multiplier does not** — per capture **6.3× / 6.4× / 6.7× / 8.6× / 8.7× / 19.4× / 59.2×**, with one capture at n = 0 family changes. **Quote it as "≥ 6× on every capture that has family changes", not as 11.7×.**
- **`0x0027` is sent rarely and only on a real base-speed change**: 153 player-directed sends, `383.04 ×76, 288.00 ×65, 385.92 ×6, 325.44 ×2, 230.40 ×2, 144.00 ×1`. Not per grant.

#### 3.3 Three claims that do not survive, and one label that is upgraded

- **T1's "99.9% of headings answered within 1.0 s" is WEAKENED to a check that cannot fail.** Shifting every grant timestamp by **+0.35 s** — below the 0.490 s inter-grant median, destroying causality outright — still answers **99.4%–100.0%** per capture. What carries the claim is the *latency*: at a ≤ 0.10 s window the pooled rate is **95.1%** but per capture it runs **43.0%–100.0%** (`20260817T183756` = 77/179, answer latency p50 **0.123 s** / p90 0.259 s against O1's pooled p50 0.035 / p90 0.053 — a 5× outlier the pooled row hides). **Retail answers nearly every heading; the "no trigger predicate at all" phrasing is not established by the 1.0 s number alone.**
- **`0x0029`'s trailing word fields are NOT "NOT FOUND"; they are CLOSED.** `0x005FD890` builds `{x, y, field3}` into a local Point and passes field4 as `0x00602A40`'s third argument, which `0x00602A6C` writes to `agent+0x80` unless it is −1: **field 3 = destination plane, field 4 = agent's current plane** (`FINDINGS:3364` "CONFIRMED and CLOSED", third independent derivation at `:3428`, SOURCED with rivals ruled out at `studies/smsg/FINDINGS.md:130-135`). The wire corroborates rather than contests: both fields are 0 ~84% of the time because plane 0 is the common case, the non-zero rows are "often equal to each other" (`(mt=1, w3=26, w4=26) ×52`), and retail's two fields differ in **14 of 987 (1.4%)** — the plane transitions. **"Send 0" is refused: it writes a wrong map index into `agent+0x80`. Send `(dest_plane, cur_plane)`, the order `authsrv.py:9987` already uses.**
- **T5's fourth row is misdescribed.** Trigger census of 3,170 player grants: heading **2,938 (92.7%)**, `0x0047` **118 (3.7%)**, click **41 (1.3%)**, and **73 (2.3%)** which were called "no prior c2s move msg". **Zero of 3,170 have no prior c2s movement message.** All 73 answer a `0x003D` older than the 1.0 s pairing window — lag p10 1.04, **p50 2.58**, p90 10.26, max 15.57 s. **Retail re-grants on a stale heading; it does not grant out of nowhere.** A server author reading the old wording builds an unsolicited-grant channel, which is the wrong mechanism.
- **T4 is UNDECIDABLE and both numbers should stop being quoted.** `FINDINGS:1600`'s "click grant superseded within a median 0.490 s" conflates the corpus-wide inter-grant median with the click grant's lifetime; a direct measurement gives p50 1.923 s, but at **n = 23 over the corpus's only 26 clicks**, in keyboard-dominant sessions, neither figure is established. What survives is the direction (click grants *are* superseded) and one structural fact: **41 grants attribute to 26 clicks — retail re-grants during a click-move with no new c2s message.**
- **SP1 stays CONTESTED and the "third rule" is a variant.** Attributing `0x002B` by the message's own trailing byte gives n = 1,049: forward 900 → 1.0 ×648 (72.0%), 0.33 ×44, 200 distinct values; backward 64 → 0.66 ×46 (71.9%), 1.0 ×12; side 78 → **0.75 ×55 (70.5%), which was in neither prior rule**; 214 distinct floats corpus-wide. **Both arms of the old contest are true at once** — a family-rate mode at ~71% per family and a wide continuous buff/snare population in the same field. But the rule falls back to "the last `0x003D` within 1.0 s" by construction and the trailing byte *is* that heading's echo 93–98% of the time, so it is ~95% one of the two arms it is offered as arbitrating, and the per-family n's do not reproduce from a pure own-byte partition (935/52/62 against 900/64/78). **The decider is unchanged: `movetap.py` on `agent+0x5C`/`+0x60` during sustained backpedalling.**

#### 3.4 D2 — what a "clipped" destination is, and what it costs us

**911 of 2,938 heading-paired grants (31.0%, per-capture 7.3%–48.5%) are on the client's own ray and short** — `|cross|` p50 0.0002 u, p95 0.0071, max 0.81; along-track p05 22.1 / p25 167.4 / **p50 347.9** / p75 551.9 / p95 714.1 u, i.e. a median **45.4%** of one displacement quantum, continuous rather than quantized (densest 0.01-wide fraction bin holds 2.3%). Reproduced independently by a second lane to the unit, including a shortfall p50 of 418.8 u. **8 of 911 (0.9%) land *behind* the report**, min −60.8 u.

Four tests, each able to fail, establish that the truncation is **world-anchored at a locally straight boundary running across the ray**:

| test | result |
|---|---|
| **E** — does the destination ride the player? | `|Δdest|/|Δplayer|` p50 **1.03** for full-length pairs (n=585) vs **0.12** for clipped pairs (n=205), 64.9% under 0.25 |
| **F** — what direction is the local line? | 192 collinear neighbourhoods, angle(line, ray) p50 **78.8°**, **117 of 192 in the 75–90° bin**; destination-cloud anisotropy p50 **0.000** vs 0.557 for the trigger positions |
| **B** — agent collision? | nearest other agent's granted position p50 **326.3 u**, 26 of 493 (5.3%) under 10 u, no radius spike |
| **H14** — the previous destination resent? | 72 of 867 (8.3%) vs 74 of 1,922 (3.9%) — 2.1×, not a mechanism |

**And the strongest wire-only rival was built, pre-registered and REFUTED.** H-STALE (`dest = p_k + vec2 + 0.5·u` from an *earlier* report) predicts on-ray, shortened-only, TEST E's ~0 ratio, TEST F's ~90° (a frozen origin with a rotating ray puts destinations on an arc), continuous depth, few repeats — and it predicts both of the things the clip measurement itself refuted. Searching 12 reports back: **2 of 911 clipped grants (0.2%) match an earlier origin to < 1 u, best-error p50 142.3 u, against a declared control of 3.8% for the at-+0.5 population.** The clipped set matches an earlier origin *less* often than the unclipped set does. **The clip is not derivable from the wire.**

⚠ **It is not a pairing artifact, and the control is tighter than first reported.** Clipped rows do pair looser (lag p90 0.158 / p99 0.524 s against 0.054 / 0.246 for at-+0.5; 8.0% beyond 0.2 s vs 2.2%), but pushing the window four steps past the first control gives 30.8% at ≤ 0.15 s, **30.6% at ≤ 0.10 s and 30.6% (781 of 2,549) at ≤ 0.07 s** — tighter than the at-+0.5 population's own p90.

**Two predictions written before the numbers were REFUTED, and they matter.** The player is **not** blocked (client speed on the trigger interval p50 **287.8 u/s** clipped vs 287.9 unclipped; 1.7% vs 1.5% under 100 u/s) — this is the ray *grazing* geometry the player then slides along, not walking into a wall. And **the client walks straight past it**: within 3 s the median along-fraction reached is **1.20**, with **57.4% overshooting the granted point by > 20 u** against 20.2% for +0.5 grants. **The clip shortens the leg the authoritative copy is given while the client keeps going — it is a separation-growth source, not a stop.**

**The identification of the boundary as the walkable navmesh is RECONSTRUCTION**, and its previously-cited evidence is withdrawn: the `Map.cpp(1239)` / `0x00709E90` identification is on `FINDINGS:3420`'s do-not-re-quote list, and that address is in the *client* binary describing the client's own resync gate — a different machine than the server whose D2 this models. The trapezoid reading has separate support at `FINDINGS:3380`; the grade stands, the citation does not.

⚠ **The cost claim "we express D2 on ~11.5% of grants where retail expresses it on 100%" is REFUTED and must not propagate.** It inverts `FINDINGS:3368`: **88.5% is the heading arm's share of retail traffic** (corroborated at `:3582`), not a collision-suspension rate. The suspension predicate is `if not pm.walkable(px, py)` at `authsrv.py:3122-3128`, and this tree measures it at `authsrv.py:10080-10086`: *"MEASURED over 532 reports — 93.8% clean, 5.5% not on our mesh at all, 0.8% on a single plane that is not the one the client named, 0.0% genuinely ambiguous."* **Our server expresses a clip on ~94% of grants and suspends it on ~5.5%.** (The 2,855 denominator that travelled with the inverted claim is also superseded by 2,938 of 3,170.)

**What D2 does change is the framing of the lead family.** Retail's own effective lead is **not** "766 u always": 1,642 grants (56% of the heading-paired set) sit at the full 765–768 u tip, and **911 (31%) sit at a median 348 u**, 0.9% of them behind the player. **Retail itself ships a mixture of leads that the 0 / 86 / 766 spine brackets** — and it is safe at all of them only because its `v_player ≈ S` (§2.4). RECONSTRUCTION, from the OBSERVED depth distribution.

---

### 4. Instruments and substrate — what exists, what does not, and three captures nobody named

**Committed and validated:** `resyncscore.sync_track()` (`toolkit/clientscan/resyncscore.py:626`) — the glide-and-park forward model of the SYNC copy — and `validate_sync_model()` (`:678`), which checks it against a direct memory read through `movesync.pair()`. **This corrects a standing belief that no forward simulator was ever committed.**

⚠ **But it is a NARROWER instrument than round 3's, and the "extends round 3's calibration" framing is REFUTED.** Round 3's model is "driven only by our wire (`0x0029`/`0x002B`/`0x0027`/`0x0028`/`0x002C`)" (`FINDINGS:2455-2457`); `resyncscore`'s takes its grants from `movesync.load_grants` (`resyncscore.py:423`), which decodes **only opcode 41 = `0x0029`** (`movesync.py:229`), and glides at a constant `run_speed`. A grep over `toolkit/` for round 3's budget instrument (`AUTH-PARKED` / `AUTH-MOVING`) returns **0 hits outside the two `studies/movement/` documents**. The five-pair numbers below are a **new calibration of a different model**, not a widening of an old one.

**Excluding `0x0025` is sound and should stay** — it rests on a handler read, not on residual-fitting: `0x0025`'s handler `0x005FD540` reaches only a facing setter writing `+0xB8`/`+0xBC`/`+0xC0` (`FINDINGS:1379-1381`), and the `+0x48` writer census finds five stores, none of them `0x0025`. It touches neither `+0x78`, `+0x58`, `+0x48` nor the velocity. **Excluding `0x002B`, `0x0027` and `0x002C` is NOT sound** — all three move the copy — which scopes the simulator to `0x0029`-only policies and puts three of the five candidates outside it (§6).

**Five calibration pairs exist in the vault, not two.** Every `movetap-*.jsonl` file pairs with a wire capture:

| capture | movetap | n | residual p50 | p90 | max | **parked %** | **glide-conditioned p50** |
|---|---|---|---|---|---|---|---|
| `145717` | `145939` | 251 | 0.00 | 43.54 | 67.42 | 53.0% | **27.55** |
| `150336` | `150349` | 29 | 0.00 | — | 42.73 | 58.6% | **23.54** |
| `150522` | `150537` | 59 | 0.00 | — | 33.78 | 83.1% | **24.53** |
| `152716` | `152723` | 106 | 19.27 | 38.53 | 59.46 | 8.5% | **20.68** |
| `171153` | `171436` | 183 | 14.42 | 30.46 | 60.54 | 3.8% | **14.62** |

**All `ours`. The unconditioned p50 is diluted by parked samples** — the three pairs reading 0.00 are exactly the three that are 53–83% parked — and the statistic `FINDINGS:2457` itself uses is the glide-conditioned one. Round 3's `|sim − live| p50 0.0–13.0 u, max 72.2 u` should be restated as **unconditioned p50 0.0–19.3 u, max 67.4 u, n = 628 over five pairs; glide-conditioned p50 14.6–27.6 u.** The two pairs that are *not* parked-dominated are the high-grant configurations — the only regime resembling any grant-heavy candidate — and there the per-sample model error runs p90 30.5–38.5 u, max 59.5–60.5 u **against a 99.92 u decision radius.** That ratio is the honest bound on any offline verdict.

**REALFIX-U1.** Three of the five pairs (`150336`/`150349`, `150522`/`150537`, **`152716`/`152723`**) are named in no study document; their run configuration is UNVERIFIED because the gamesrv jsonl headers carry no argv. **`152716` is the `--heading-grant` decisive trial and it is NOT wire-only** — it has a full SYNC-array movetap trace and it is the widest-residual pair in the set.

**REALFIX-U2 — the substrate inversion, and it decides the whole input plan.** The client's reports after a capture's own first teleport describe a player standing where no other policy would have put them. Honest counterfactual window = `[start, first measured hard step)`:

| stamp | span s | clean s | clean % | reports | clean distance u |
|---|---|---|---|---|---|
| `182652` (`--client-endpoint`) | 65.6 | **3.2** | **4.9%** | 10 | 259 |
| `171153` | 210.9 | 33.4 | 15.8% | 56 | 3,185 |
| `195137` | 41.8 | 8.5 | 20.4% | 20 | 2,121 |
| `145717` | 320.3 | 138.8 | 43.3% | 14 | 1,982 |
| `152716` | 36.0 | 29.3 | 81.4% | 84 | 6,076 |
| **`100340`** | 765.1 | **719.0** | 94.0% | 274 | **43,177** |
| **`173940`** | 100.0 | **100.0** | 100% | 158 | 9,353 |
| **`182554`** | 26.2 | **26.2** | 100% | 21 | 6,433 |
| **`182934`** | 114.8 | **114.8** | 100% | 79 | 22,586 |

**The refuted-run captures are CALIBRATION substrate; the zero-grant captures are COUNTERFACTUAL substrate.** The capture that refuted `--client-endpoint` yields 3.2 s and 259 u of uncontaminated track. The four clean captures give ~960 s and ~81,500 u of policy-free player path. Independently re-measured by a second lane to within one report interval.

⚠ **The counterfactual substrate is fast-running and click-free, and both biases are load-bearing.** Player speed p50 is **263.3 / 262.3 / 283.2 / 280.0 u/s** against a declared 288, which is the regime where any lead policy's runaway rate `(S − v_player)` is *smallest* — **a null for a lead candidate on this substrate is not an acquittal.** And clicks number **0 / 5 / 21 / 0**, so the default build sends ~0 grants there and achieves near-perfect survival by doing nothing. **The harness can price harm a candidate ADDS and can never price harm a candidate REMOVES.**

**Report cadence, which sizes every blind spot** (non-hard intervals ≤ 2.0 s, `ours`): gap p50 0.251–0.301 s and chord p50 **32.7–69.7 u** on seven captures; `100340` 0.500 s / 94.8 u; `182934` 0.501 s / 127.5 u; and **`182554` 1.785 s / 445.9 u**, reproducing `TESTS.md`'s "a straight keyboard hold reports every 1.80–1.82 s". Chord **p90** exceeds the 99.919968 u match radius on **4 of 4** counterfactual captures (141.6 / 514.4 / 477.5 / 516.1 u) and **7 of 11** calibration captures.

**REALFIX-U3 — denominator debt.** `FINDINGS:2519-2523`'s active-time triple does not fully reproduce. Measured this round on the whole capture at the same 2.0 s threshold: jumps per minute of *active* time **4.19 / 7.87 / 13.32** (default / `--heading-grant` `171153` / `--client-endpoint`) against FINDINGS' 4.19 / 7.48 / 11.27, and u displaced per active second **137.8 / 73.5 / 124.0** against 137.8 / 69.5 / 101.4. **The first term matches exactly in both, which establishes the method; the other two are presumably scoped to the movetap window rather than the capture.** Name the window, every time. What does not change is the ruling: **per span the default build looks best on frequency and per observed second it is the WORST on displaced distance**, and `FINDINGS:2643`'s "no candidate can be scored against 5.7/min" stands.

---

### 5. The candidate set, with exact deltas from refuted runs

**REALFIX-P0 · DEFAULT (control, shipped).** Click grants only, clipped from our origin, three refusals; bare `0x0025` on a *turned* heading; nothing on stop. Violates O1, O2, O3. Measured `ours`: 1.31/min span, 4.19/min active, 137.8 u per active second, separation p50 1,164 u, click grants left outstanding a median 5.84 s and a max 56.17 s.

**REALFIX-P2 · ZERO-LEAD.** `D = the client's just-reported position, verbatim.` Satisfies O1 **by construction** (`q` is a point the client reported standing on), O3 (lead ≤ 1.0 u, no runaway term), O5 **by witness**, and — the point of §2.4 — it is the only configuration in which the speed error cannot produce overshoot, because the copy never travels past `D`.

> **Delta from `--client-endpoint` (`20260819T182652`, REFUTED, 13/197 hard, 11.88/min span): the lead term, and TWO others that were not named.**
> (1) **the lead**: drop `+ vec2 + 0.5·unit(vec2)` — 766 → 0;
> (2) **the stop arm**: any `0x0029` on `0x0047` **IS `--stop-echo`**, bit-identical to `authsrv.py:10345-10360`, which is **run and killed** (`20260819T134811`; `authsrv.py:1012-1017`: "the echo does not overwrite the pending click destination; it adds a SECOND one"). **Cut it. `--client-endpoint` had no stop grant.**
> (3) **the trigger**: the shipped heading path is gated at `authsrv.py:9758` behind `turned or state.get("walking") is not True`, and `walking` is cleared only by the *click* arm. On click-heavy play every click reopens it (`182652`: 193 grants against 193 headings; `171153`: 447/447), so the gate is invisible in both refuted runs — but on the **click-free counterfactual substrate** it opens on only **11.1% / 24.3% / 61.2% / 80.8%** of moving reports (`182554` / `182934` / `100340` / `173940`), a **1.24×–9× cadence delta**. **Name it, do not hide it.** Retail has no trigger predicate; P2's grants are zero-distance and take the `≤ 1.0 u` short-circuit when the copy is caught up, so extra cadence is nearly free for *this* candidate specifically — which is the ground for dropping the gate in P2 and not a general licence.
> ⚠ **CORRECTED 2026-08-21, by the build this section specified.** The short-circuit clause is FALSE of P2's grants: the `≤ 1.0 u` distance is measured from the **SYNC COPY** (`fsub [esi+0x78]` at `0x005FEB57` — §2.4's own point turned back on the candidate that cited it), not from the client, and the copy is chasing a player at run speed. Replayed through `grantsim.py` on the four zero-grant captures: **6 of 539** synthesized P2 grants take the short-circuit; median `|d|` from the copy 101–512 u; **every other P2 grant is a class-A test instant.** "Nearly free" is retracted; the gate-drop trade is priced on the numbers in `REALFIX.md` §P2's correction instead.

**REALFIX-P3 · SHORT-LEAD** (`L = min(S · Δt_refresh, radius) = 86 u`). Discharges O3 mechanically: `dist ≤ S·Δt` ⇒ the copy arrives before the next grant and `+0x78` is re-pinned to `D` exactly, with no speed assumption.

> **Delta from `--client-endpoint`: the lead magnitude only, 766 → 86 — provided the clip is DROPPED.** As first drafted, P3 added `clip_to_walkable` while P2 and `--client-endpoint` are both unclipped, making it a two-variable step from both neighbours. **Adjudicated: run the family unclipped at 0 / 86 / 766 and treat O5 as a named risk rather than a code term** — because retail's D2 is world-anchored geometry we cannot compute (§3.4) and our heading arm's clip suspends collision entirely when our mesh does not cover the player anyway (`FINDINGS:3428-3432`; the plane-aware predicate lives on the *click* arm).

⚠ **P3's safety argument as previously written is REFUTED, and the replacement is a direct measurement of the right operand.** The old argument scaled a 398.3 u tip drift proportionally to an 86 u lead to get "~45 u p50 / ~71 u p90, inside the radius". Three defects: the 398.3 figure is `ours`, not `live` (`FINDINGS:2924`, `:2951`); the decomposition `tip(t₂) − tip(t₁) = Δp + L·Δû` has an `L`-independent term (measured `|Δp|` p50 **46.9** / p90 **143.7 u** over 852 same-mode consecutive `0x003D` pairs, `ours`, against `766|Δû|` p50 27.2 u); and the operand measured directly refutes the bound — **`|D(L=86) − the client's next report|` reads p50 89.4 u, p90 136.4 u, with 389 of 852 = 45.7% at or beyond 99.919968 u** (turn-conditioned subset, n = 291: p50 41.1 / p90 116.8 u, 14.8% beyond). **On either selection the p90 is 1.6–1.9× the claimed ~71 u and lies outside the radius.**

**And that measurement is exactly the right operand at the arrival instant.** Under P3, O3's whole point is that the copy *arrives*; at arrival `+0x78 = D` exactly, so `q = D` and the match operand is precisely `|D − the client's track|`. **P3 therefore fails the match on roughly 46% of its arrivals** — which is not automatically a snap (an 86 u lead keeps gate 1's 299.33 u comfortably), but it routes those instants to gates 2 and 3, which are invisible offline (§7). **This is the clearest single number separating P2 from P3, and it favours P2.**

**REALFIX-P1 · RETAIL MIMICRY — a fidelity reference, not an experiment.** Full §3.2 policy including S1/S2/S3 ordering, `(dest_plane, cur_plane)` planes, the stale-heading re-grant (T5 corrected), and the zero-distance stop echo. **Delta from `--client-endpoint` = FOUR terms** (family-rate `0x002B`; a clip; real plane fields; click-grant supersession), so a bad result names none of them. It also **cannot express D2 faithfully** — retail's clip is world-anchored geometry, ours is a navmesh line-walk that suspends off-mesh. Its harm scales as `766 · (288 − v_player)/288`, so it will look harmless on any fast-running capture and break the first time the owner backpedals or is snared. **Keep it as the reference the lead family is read against; do not run it as an ablation, and do not run it first.**

**REALFIX-P4 · `0x0027` RE-ARM — CUT.** `0x0027`'s setter `0x00602910` settles the agent by dead-reckoning to *now* and rewriting `+0x78` **to the runaway point**, then re-issues the outstanding grant. It re-*aims*; it does not re-*pin*. `0x0027` at spawn is a measured no-op (`+0x5C` already 288.0, `+0x60` already 1.0, in 4,115/4,115 movetap samples). It needs a new SMSG constant, a new builder in `agents.py` and a new wire test — `0x0027` has **no constant, no builder and no call site anywhere in the repo**, its only namesake being `GAME_CMSG_ATTACK_SKILL` in the opposite direction — bought for a candidate the mechanism read grades FAILS provably and the harness admits it cannot score. **Recorded as a dead candidate with grounds; its one genuinely new property (it reaches both copies, no `[esi+0x1e0]` gate) is subsumed by any family that never lets a destination go stale.**

**REALFIX-P5 · `0x002C` CLIENT-PIN — already built (`--resync`) ~~, never run~~.** *["never run" CORRECTED 2026-08-25: `authsrv-20260820T182119-c1.jsonl` holds 52 resync verdict rows, 18 fired, 18 `0x002C` sends, landed by commit `3e40bde` 34 min before the capture — but that run sent ZERO `0x0029` (grants), so it never armed an arrival and is NOT a test of the disarm. The missing experiment is one evening with grants enabled and a movetap attached; protocol registered at `followon-notes/p5-resync-disarm.md` §8, staged 2026-08-25. `RESYNC_SEPARATION` reconciled to 100.0 the same day — the ruling is on the constant in `authsrv.py`.]* Fires only on the client's own last accepted report, never our integrator, under four refusals (report age ≤ 100/288 = 0.347 s; zero refused-report streak; separation ≥ threshold; rate ≥ 0.5 s). O1 is n/a by construction — `0x002C` clears the AgTrack record first (`0x005FDA78`) then SetPositions both copies, so no follow-up reaches a gate and no roster reseed happens. **Delta from the REMOVED `0x002C` build = TWO terms** (payload changed from `state["pos"]` to `state["client_pos"]`; three refusal gates that did not exist), so it is not a clean ablation either. **It trades snaps for yanks**: the removed build's five sends "carried the client 630, 189 and 765 units… that is the warp the player described" (`authsrv.py:2580-2585`). **O6 is UNVERIFIED, not satisfied** — the quantity that decides whether it is safe is the async array, which nothing in this repo has ever read.

**REALFIX-P6 · GRANT-SUPPRESS (control, shipped, run once).** 1.39/min vs 11.49/min span (8.3×), 903 vs 9,687 u/min (10.7×), `ours`, **n = 1 A/B pair with two identical-play baselines differing 1.7× in rate**. It removes the bake caller only; arrivals, `0x002C`, collision resolution and the resync's own SetPositions still dispatch. **It works by making us quiet, not by making us correct**, and `state["pos"]` silently stops tracking — an UNMEASURED cost in aggro radius, `clip_to_walkable` and interaction range. **The correct interim ship and the wrong destination.**

**Dead candidates carried forward** (from `FINDINGS:1716-1737` plus this round): echo-the-client's-vector (a no-op, same expression); `--stop-echo` (run and killed, and **re-entering P2 by the back door was caught only in review**); any direction/backward guard (retail has none — 25 of 29 backward grants point behind facing, up to 768.5 u); "+0.500 u as the fix" (real to ±0.00003 u but worth 2 ms at 288 u/s, below the instrument's 20 ms); the `k ≤ 1` safety clamp (struck pre-build); `--heading-grant`; `--client-endpoint`; `0x0028` at keyboard onset (retail's onset behaviour is SUPERSESSION — 496 of 499 terminated by a fresh `0x0029`, `0x0028` exactly once and that one a zone transfer); "supersede every heading" (already the two refuted runs under another name).

---

### 6. What offline scoring cannot see — and the four things that broke the scorer

An offline harness was specified, built to spec by one lane and independently reimplemented by another. **It does not do the job it was built for, and the reasons are findings.**

**6.1 A separation threshold is not a snap model.** A naive proxy — simulate the copy from grants, flag every report at ≥ 299.332591 u — predicts **16, 12 and 34** snaps on three captures that sent **zero grants** and measured **zero jumps**, and 46 against a measured 7 on the default build whose real separation is p50 1,164 u for 320 s. **REFUTED as a scorer.** A caller-aware proxy (test instants + match + gate 1, every constant the client's own) takes those three captures to **exactly zero structurally**, which is the check that matters.

**6.2 The headline calibration is implementation-dependent.** Two independent implementations of the same written specification, driven by the same as-sent `0x0029` streams over the same eleven `ours` captures, give **69** and **80** predicted against **60** measured — 1.15× and 1.33×. They agree on the three structural zeros and on eight of eleven per-capture counts, and diverge most on the round-4 captures (`183311` 6 vs 10, `195137` 8 vs 12). **A `[0.7, 1.5]×` acceptance band drawn after seeing 1.15 swallows both, and would swallow 90 against 60.** Pin the spec to a golden fixture or say the number is implementation-dependent.

**6.3 The instrument is not "strong on geometry, weak on cadence" — that asymmetry is manufactured.** Its own nulls: the **smallest** geometry perturbation (rotate destinations by 1) moves the total 69 → 73, **+5.8%**; the **smallest** cadence perturbation (shift −0.35 s) moves it 69 → 76, **+10.1%**. The claimed asymmetry sets rotate-by-17 (+64) beside shift-by-+0.35 s (−9). What *is* true and load-bearing: **the +0.35 s causality-destroying shift scores 60, dead on the measured total**, so the total is not discriminating on sub-report-interval timing; and **deleting the match test doubles the prediction (122 vs 69)**, so the match test is genuinely load-bearing.

**6.4 It cannot separate the lead family, and the parameter that decides the ranking is not in its sweep.** Running leads 0 / 86 / 766 through the specified scorer on the four counterfactual captures, `ours`:

| capture | match ON: 0 / 86 / 766 | match OFF: 0 / 86 / 766 |
|---|---|---|
| `173940` | 0 / 0 / 12 | — |
| `182554` | 0 / 0 / 3 | 10 / 10 / **3** |
| `182934` | 2 / 2 / 14 | 23 / 23 / **22** |
| `100340` | 3 / 2 / 26 | 48 / 45 / **30** |

**With the match test on, P2 and P3 are indistinguishable on three of four captures; only the already-refuted 766 u lead separates. With it off, the ranking INVERTS and the refuted configuration wins on three of four.** And the draft's own degradation rule — skip the match test wherever the report chord p90 exceeds the radius — **fires on 100% of the counterfactual substrate** (chord p90 141.6 / 514.4 / 477.5 / 516.1 u) and on 7 of 11 calibration captures, i.e. it forces the entire counterfactual onto the scorer §6.1 refuted. **The sweep varied the match RADIUS (50/100/200 u) and never the match test's PRESENCE, which is the axis the ranking is not invariant on.**

**6.5 Under zero lead the match test is a tautology of the proxy's construction — but the underlying structure is real.** `q` at every P2 dispatch is a point the client itself reported, and the proxy's polyline *is* the report track, so the distance is 0 by identity, not by measurement. The structure behind it is nonetheless the invariant's O1: a lagging copy is on ground already walked. **The consequence is that P2 needs a different offline metric.** Its residual exposure is not snaps but **REALFIX-M1, lag age** — how far back on the polyline `q` sits, in seconds of client travel, against the chain's ~5 s block-recycle bound (`0x00604C03 cmp ecx,0x1388`). That is measurable and is not a tautology.

**6.6 Three proxy biases, and the third was missing.** *Optimistic (we under-predict):* the real chain is truncated on a match (`lastMatch->next = NULL`), so our 5 s window is more generous than the client's; and the polyline is not client-only (§2.2), so nodes exist that we cannot see. *Pessimistic (we over-predict):* **the client's history nodes are pushed at its own local-move rate, so our report track is a SUBSAMPLE** — our polyline lies chordally inside the true one and our distance-to-polyline is systematically over-estimated. Direction stated for all three; magnitude **NOT FOUND** for all three. Combined with the simulator's own p90 30–41 u / max 60 u error in the high-grant regime, **the two proxy errors are of the same order as the 99.92 u decision radius.**

**6.7 Structurally invisible at any offline resolution.** Gate 2 and gate 3, both of which can only *add* snaps — so **every harness score is a FLOOR on total harm**, and gate 3 arrives as rubber-banding the hard bar does not count at all. The `0x0025` async-arm gate. The gate-free `ResyncAllAsync` route. Unit-vs-unit collision, which the server models not at all while the client's model is fully decoded (radius at `agent+0xD0`, combined radii via `0x005FED20`, the 60° cone, the sidestep at `0x00600500` displacing by `(combinedRadius + 10.0) − |distFromLine|`). The client's own `+0x5C`/`+0x60` under a buff or snare (retail's 214 distinct `0x002B` floats, `live`). Whether the *player* moves differently under a candidate. And the whole non-movement cost of silence.

**6.8 And the simulator's scope excludes three of the five candidates.** It bakes `S = 1.0 × 288.0` and models no `0x002B`, so under P1's family rates a BACK leg runs at 190.1 u/s while the harness bakes 288 — a 1.51× error in the operand of both the match test and gate 1. `0x0027` (P4) and `0x002C` (P5) are likewise unmodelled. **P1, P4 and P5 are outside the instrument.**

**⇒ What the harness IS.** A calibration instrument (it reproduces the measured hard-jump census on eleven `ours` captures across five configurations, and takes the three zero-grant captures to zero structurally); a **refusal** instrument (it can kill a candidate that predicts harm the zero-grant control did not have); and an **exposure meter** (REALFIX-M1 lag age for P2, REALFIX-M2 arrival match-failure fraction for P3, and `resyncscore`'s yank column for P5). **It is not a ranker, and the P2-vs-P3 question needs a live A/B.** Reporting it as a ranker is the same defect as reporting a partial suite run as a full one.

---

### 7. What this round changed in the record

REFUTED and replaced: round 4 §7's "never been tried" (§1); "the two conjuncts differ on every axis" for segment 0 (§2.2); "the polyline is client-only" (§2.2); "dispatched exactly once per SetPosition" (§2.1); "the one-shot fence throttles the observed rate" as a co-equal reading (§2.5a); the ~99.6 u match threshold, now 99.919968 u exhaustively (§2.2); "one-signed positive" sqrt error (§2.2); `0x00709E90`/`0x00709990`'s names as OBSERVED (§2.3); "0x0029 fields 3/4 NOT FOUND" and "send 0" (§3.3); T5's "no prior c2s move msg" (§3.3); "we express D2 on ~11.5% of grants" (§3.4); "`152716` is wire-only" (§4); "`resyncscore`'s simulator extends round 3's calibration" (§4); P3's proportional-drift safety argument (§5); "the harness can settle P2 vs P3" (§6.4).

WEAKENED with the caveat carried inline: T1 (a null reproduces it); T3's 11.7× (per-capture 6.3×–59.2×); P2's 77.2% and O1's latency (per-capture spread); SP1's "third rule" (a variant, ~95% one of the arms it arbitrates); T4 (UNDECIDABLE at n = 23); §3(b)'s "Kills" verdict on refusal policies (unpriced non-movement cost).

New OBSERVED: the nine-capture membership; retail's message ordering, stop shape, `0x0025` echo, `0x0027` census; D2's four properties and H-STALE's refutation; the two caller classes and their xref graphs; the `≤ 1.0 u` short-circuit's non-dispatch; the roster-wide history wipe; the re-arm's no-op-when-armed; five calibration pairs with glide-conditioned residuals; the substrate inversion; the caller-aware proxy's eleven-capture calibration and its nulls; the lead sweep; `|D(86) − next report|`.

---

## 2026-08-21 — REALFIX-L1 FIRST RUN: the keyboard arm holds the invariant, and the control starves itself

**OBSERVED, `ours`.** Two sessions, one machine, ~9 minutes apart, **scripted input
identical to the leg** — the first A/B in this arc where the two arms ran the same
input by construction rather than by an operator's best effort:
`session.py --until map --keep-open --walk "W:25 yaw:250 W:25 S:20 yaw:-250 W:25
S:20 W:25 yaw:200 S:15 W:25" --game-args="--explorable[ --zero-lead]"`, ~195 s of
continuous keyboard with two backpedal legs, `movetap` attached both arms. The
operator's one intervention was a mid-run observation that the map's obstacles put
the walk into walls — which the numbers below confirm and the design absorbs: both
arms ground the same walls (interval speed p50 182.4 vs 188.1 u/s, sub-100 u/s
share 16% vs 19%, chord p90 514.5 vs 514.7 u — matched to a few percent).

| arm | capture | grants | hard rows | hard /min active | sep p50 / p90 / max |
|---|---|---|---|---|---|
| A `--explorable` (P0 control) | `20260821T081744` | **0** (0 clicks sent) | **0** | 0.00 | **4,402 / 6,287 / 6,811 u** (n=63) |
| B `+ --zero-lead` (P2) | `20260821T082631` | **66** fired, 4 `heading-rate` refused | **0** | 0.00 | **267 / 523 / 531 u** (n=68) |

**The flag worked end to end, on all three witnesses.** The gamesrv argv carries
`--explorable --zero-lead --no-enemy`; the capture holds 66 `grant_verdict` rows
with `arm="zero-lead"` (66 fired / 4 rate-refused of 70 headings — the 0.5 s floor
is nearly inert at keyboard cadence, as designed); and `movetap` watched the client
re-arm `+0x48` **81 times** in arm B against **0 changes** in arm A, targets
marching along the walked path. (One display gap for the record: the startup
prediction banner goes to gamesrv stdout, which `session.py` does not echo outside
`--serve` — verify the flag from the capture's own verdict rows, not the harness
transcript.)

### Adjudication against the pre-registration, both directions

**P2's harm bounds are MET at zero.** ≤ 1.0 hard rows/min active: **0.00**. ≤ 40 u
per active second: **0.0**. Sixty-six grants meant ~66 class-A test instants — the
desync test *evaluated* at every one, fence transitions visible in movetap — and
none snapped. Under the decoded invariant this is the predicted outcome, now
OBSERVED at a real client rather than proved by the offline tautology (round 5
§6.5).

**P2's separation bounds are MISSED AS WRITTEN, by the mechanism the record itself
names.** p50 267.5 vs the ≤ 150 bound; p90 523.0 vs ≤ 520. The bound was
calibrated on a ~0.3 s report cadence; this walk's keyboard cadence is **1.8 s**
(gap p50 1.80 s on arm B), and a copy chasing 1.8-s-stale points at run speed lags
by exactly the report **chord** — and the separations sit at chord scale (sep p90
523 vs chord p90 514.7). That is the *benign* pre-registered failure signature
("frequent small displacements at the report-chord scale"), and the hard-row
falsifier (p50 > 520 u refutes lag-on-polyline) **cannot fire because there are no
hard rows at all.** ⚠ Both arms' separation figures also carry a systematic the
prediction did not budget: `offset_from_stamps` resolves the movetap↔wire clock to
a 1.00 s spread, worth up to ~288 u on any single pairing. The **16× arm contrast
dwarfs it; the absolute P2 bounds do not** — so the p50/p90 misses are recorded as
UNDECIDABLE-leaning-miss, to be settled by a run with a finer offset anchor, not
argued away.

**P0's prediction FAILED, and the failure is a design contradiction worth more
than a pass.** The control was predicted at 3–6 hard rows/min active (bracketing
the measured 4.19) — it produced **zero grants and zero hard rows**, because L1's
own protocol is click-free and the default build's only grant arm is the click.
The 4.19 figure came from a capture with 40 click grants. **A click-free protocol
starves the default build into the zero-grant regime, where round 5 §4 already
measured 0 jumps of 435 intervals** — the pre-registration reused a number outside
its trigger context, this arc's signature failure, caught by its own control arm.
What the control *did* measure is the cost of silence: **the authoritative copy
parked 4,402 u (p50) from where the client actually was, max 6,811 u** — the
AUTH-PARKED budget of round 3, now with a movetap trace under a known input
script. Arm B pulled that to 267 u: **a 16× reduction in how wrong our
authoritative position is**, which is the quantity `state["pos"]`'s consumers
(aggro, interact, clip) actually read.

### What this run does not settle, and the one that would

No warps were removed because the substrate had none to remove — the instrument
prices harm added, never harm removed, and L1's keyboard regime adds none under
either arm. **The decisive regime is round 4's trigger — hold S and spam-click —
which is 11.49 hard rows/min under the default build.** That input cannot be
scripted by the walk grammar (a held key and simultaneous clicks), and clicking
at world targets is the operator's side of the boundary anyway: **REALFIX-L1's
second run is the owner reproducing round 4's trigger with `--zero-lead` on,**
prediction unchanged from the flag's startup banner. Two further residues: the
long report silences against walls (14–27 s, five per arm) are the blind-budget
regime and went unprobed; and movetap stalled to 12.2 / 9.5 Hz against its own
floors on both arms (background load; positives valid, nulls void — do not read
the arm-A "0 `+0x48` changes" as exhaustive, though with 0 grants there was
nothing to re-arm).

## 2026-08-21, later — L1 FIRST RUN IS VOID AS A P2 VERDICT: the operator saw arm B warp, and the design cannot rule on it

**OPERATOR-REFUTED, same day.** The section above reported arm B at 0 hard rows and
called P2's harm bounds "MET at zero." **The operator watched arm B bug out near
the map's bridge.** The instrument did not see it, and the run's design is why —
three defects, all mine:

1. **The negative was quoted past its blind budget.** Arm B was inside a report
   interval ≤ 2 s for only 32% of its span; the hard bar cannot see inside a
   silence, and round 5's own instrument note orders every negative qualified by
   exactly this. "0 hard rows" was a claim about 63 observed seconds wearing the
   costume of a claim about the run.
2. **Geometry stalls and desync stalls are indistinguishable in this trace.** The
   scripted walk plowed into obstacles and the walkmesh's end in BOTH arms, so a
   stuck-and-silent stretch in arm B (where the bug lives, per the operator) has
   an innocent twin in arm A. The "matched collision substrate" table in the
   section above measured that the two arms stalled EQUALLY — which is precisely
   why it cannot say WHY either one stalled. A control that shares the confound
   is not a control.
3. **The 16× separation contrast survives; nothing else does.** Copy-parked-at-
   4,402 u vs copy-at-267 u is read off continuous movetap tracks and does not
   depend on catching any event. Every per-event claim from this run — including
   "~66 test instants, none snapped" — is WITHDRAWN as unverifiable.

**The operator's hypothesis, registered before analysis: ANGLED MOVEMENT LOSES
SYNC, and the failure was near the bridge.** Two candidate mechanisms fit the
decoded record, both UNVERIFIED:

- **The plane echo.** Both arms cross plane 0 ↔ 18 six times (OBSERVED, the
  report stream's own `values[2]`; the plane-18 stretches are the bridge, and arm
  B's 21.6 s silence sits inside one). Retail's `0x0029` carries
  `(dest_plane, cur_plane)` and they DIFFER at transitions (14 of 987);
  `--zero-lead` echoes the single reported plane into BOTH fields. A wrong plane
  in `agent+0x80` is gate 2's own operand, and the walkable-100 match conjunct
  runs on the navmesh the plane names.
- **Node-chain corner-cutting.** History nodes push on a movement-command change
  or a 2.5 s head age (`0x0060593A`); a steady angled slide changes no command,
  so the polyline is chords of ~2.5 s of curved travel — and the match's
  straight-line-to-segment test is STRICT at ~100 u. A copy correctly lagging ON
  the real path can sit > 100 u from a chord that cuts the bridge approach's
  corner, fail the match, and hand a 300–500 u lag to gate 1.

Analysis of both captures against both candidates is running; REALFIX-L2 gets
designed from its result, with the confound controlled — legs bounded by stops,
no leg long enough to go silent, open-ground control legs, and the bridge crossed
deliberately. Until then the only L1 claims that stand are the separation
contrast and the flag's mechanical operation (66 grants, telemetry, 81 client-
memory re-arms).

## 2026-08-21, round 6 — THE BRIDGE EVENT IS FOUND: three rendered-copy resyncs, every one at a plane-rewriting grant, and the instrument was reading the wrong copy

Two analysis lanes, one adversarial skeptic, one design lane; no client run, no repo
write until this section. **The operator's report is confirmed and located**: arm B
warped three times, all on the plane-18 corridor (the bridge), and the reason no
instrument saw it is that every L1 number was computed on the copy the operator
cannot see.

### 1. The instrument correction

**OBSERVED.** `movetap` records BOTH copies and always has: `sync_at` (world 0,
authoritative — what `movesync.sep` and every L1 figure read) and `async_at`
(world 1, rendered — what the operator watches). Nobody read `async_at`. On it:

| | arm A (0 grants) | arm B (66 grants) |
|---|---|---|
| rendered-track steps | 2,694, max **33.4 u** | 2,041 |
| steps > 100 u at > 1.5× run speed | **0** | **3** — 387.1 / 468.2 / 322.4 u |

The skeptic reproduced L1's own headline separations through `movesync` before
accepting this, so the disagreement is in what was read, not in a loader. **The
16× separation contrast survives as what it always was** — the authoritative
copy's error, the quantity `state["pos"]` consumers read — **and it says nothing
about what the player sees.** L1's write-up treated it as if it did.

**REALFIX-E, the only admissible event definition from here on** (adopted from the
design lane after the skeptic refuted every alternative): an adjacent-sample step
of the `async_at` track ≥ 150 u within a ≤ 0.25 s sample pair. Grounds: the
control's maximum is 33.4 u, the smallest positive is 322.4 u; 150 sits 4.5×
above one and 2.1× below the other. **`sep`, `gate1`, `fence_raw`, the plane
words and the wire hard bar are NOT identifiers** — the skeptic ran each against
arm A and every one fires there too (fence clears ×3, plane mismatch on 121
samples, sep-above-cut on 2,695 of 2,695). They are covariates.

### 2. The three events

**OBSERVED, arm B (`movetap-20260821T082702`, 9.5 Hz — below floor; positives
valid).** Artifact tests pass on all three: `async_ptr`/`id`/`count`/`world`
single-valued across the file, `async_branch` "integrated" on both sides,
persistence ≥ 10 samples.

| | E1 | E2 | E3 |
|---|---|---|---|
| UTC (movetap's own clock — no wire alignment needed) | 12:27:21.72 | 12:27:47.89 | 12:28:50.11 |
| leg | L3 `W:25` | L4 `S:20` | L7 `S:20` |
| grant plane word | 18 → **0** | 0 → **18** | 0 → **18** |
| magnitude / dt | 387.1 u / 0.117 s | 468.2 u / 0.098 s | 322.4 u / 0.111 s |
| displacement · commanded heading | **−387.0 u** | **−468.2 u** | **−322.2 u** |
| lands vs contemporaneous SYNC copy | 15.6 u | 16.7 u | 27.6 u |
| client's own `sep` (memory, no alignment) | 431.5 → 15.6 | 513.7 → 16.7 | 378.8 → 27.7 |
| `clientControlled` same sample | 1 → 0 | 1 → 0 | 1 → 0 |

Backward, onto the lagged authoritative copy, at the bridge: the operator's warp,
three times. After each event the rendered copy re-walks the granted leg back to
the client's last reported position — **a round trip with net wire displacement
0.0 u**, which is why the hard bar stayed silent. ⚠ Stated with the skeptic's
correction: this is the **already-booked blind-budget defect**, not a new class —
each event opens a 21.6 / 17.3 / 5.5 s report silence *starting at the snap*, and
at the 0.30 s cadence P2's bounds were calibrated on, the 4.16 s of round trips
would have carried ~14 report instants. And after each event the character goes
**dead**: freezes of 21.9 / 19.4 / 6.1 s begin 1.50 / 1.66 / 1.20 s after the
snap (the rendered copy travels 337–468 u in between), with motion resuming only
at the next scripted key-down. ~47 s of a 198 s walk. That the fence clear is
what disables keyboard drive is **UNVERIFIED**; the freeze is OBSERVED.

### 3. What is established, exactly — and no more

**The plane word is NECESSARY in this run and NOT SUFFICIENT.** Among the 31
movetap-covered grants landing with gate 1 already failing (sep > 299.33 u):
plane-changed 3 warp / 1 not; plane-unchanged **0 warp / 27 not** (Fisher
two-sided **p = 0.00089**). Anchoring is per-event on the client-memory
`agent+0x80` flip — the wire pairs with each flip 5-of-5 inside one sample —
and the table is **alignment-sensitive by construction**: re-anchoring on a
fitted mean lag (+0.077 s) moves E3 into the wrong cell and fabricates a phantom
warp. The mean-lag variant is printed to show the sensitivity, never used.

- **The hole: grant #37** (t = 147.877, w4 = 0 onto a sync copy reading plane 18,
  sep 511.2 u, fence armed, same 18→0 direction as E1) matched every stated
  precondition and **did not warp**. The mechanism as stated over-predicts one in
  four (treatment n = 4).
- **The location confound is real and its separating cell was EMPTY in this run**:
  all 4 plane-rewriting landings sit in or within ~250 u of the plane-18 corridor;
  all 27 controls sit outside it. "In-corridor, above-cut, no rewrite" had n = 0.
  REALFIX-X6 fills it at n = 9 in L2.
- **Which plane variable is operative is UNDECIDABLE here** — three definitions
  (w4 ≠ sync `+0x80`; w4 ≠ previous grant's w4; sync plane ≠ async plane) are
  collinear in this run and give identical tables. REALFIX-I1 (the history-chain
  walk in movetap) decides it, and X5 separates "causes" from "permits".
- **The wire-to-warp chain, RECONSTRUCTION from OBSERVED pieces and the leading
  reading:** `0x0029` field 4 → `0x00602A6C` → `agent+0x80` → `q`'s plane in the
  16-byte copy at `0x00605643` → the match's **walkable conjunct**
  (`0x00605C40`/`0x00709990`, start unresolved at `0x0072AE4F`) → no match →
  gate 1 at 379–495 u → whole-roster reseed. The registered candidate named
  gate 2; the data implicates **the match conjunct** — gate 2 is refuted as the
  site (in arm A it is reached 0 times; in arm B the echoed plane is always one
  our mesh puts the granted point on — correct for the point, stale for the copy).
  **The failure in one sentence: `--zero-lead` stamps the CLIENT's current plane
  onto a copy standing ~1.8 s and ~500 u behind, so the plane belongs to a
  different point** — observed-context-is-part-of-the-claim, in wire form.
- **First runtime evidence the match test fires at all**: 27 of 27 above-cut
  same-plane landings did not snap, so the 100 u match was protecting at every
  one (round 2's displaced "the match is short-circuiting" is revived). ⚠ This is
  a **null from a below-floor instrument** and carries its rescue argument in the
  same sentence: max intra-leg sample gap 0.215 s (B) / 0.176 s (A), so a
  persistent 300–470 u displacement cannot hide between samples.
- **`clear_record`'s snap-path position is NOT independent evidence** —
  `clientControlled` drops 1→0 three times in arm A, which sends zero grants.
- **Arm A's null carries its coverage**: movetap covered 113.3 s of its 199 s
  walk (57%), missing the first four legs and two plane flips — and arm A cannot
  express the signature at all (0 grants ⇒ the dispatcher is never entered), so
  the causal weight is entirely on the within-arm-B contrast.

**CORNER-CUTTING is REFUTED at the events, in the strong form.** A chain node at
every wire report gives **0 exceedances** of the 99.92 u radius (max 72.4 u); the
tapped `hist_head` chain agrees (max 70.2 u); only the thinned 2.5 s-rule proxy
exceeds, its over-estimate bound is v·gap = **514 u at the p50 gap** — larger than
anything it "found" — and the steady-turn sagitta at the client's own node rule
is 1.6 u. At the three warps the distance is 0.0 / 0.0 / 0.0 u. Its only
surviving route is a **collision deflection**, which is what REALFIX-X2a tests.

**"Angled movement" is UNTESTED, not refuted.** The L1 walk's rendered-track
|dψ/dt| p90 is 0.007 rad/s — the grammar contained no sustained angled motion.
X1/X2a/X2b are its first real test.

### 4. Retail corrections and the walk facts

- **Corpus correction, carry everywhere:** the "14 of 987 (1.4%)" differing-plane
  rate at `FINDINGS:3407`/`:3790` is ONE capture's rate. Over the live corpus:
  **1,245 of 9,733 (12.8%), per-capture 1.4%–30.2%, with `20260817T231139`
  supplying 51% of the differing rows.** *(Corroborated 2026-08-26 by the A2
  recon's independent recount — 495 of 3,170 (15.6%) on the 9-stamp subset —
  which flagged the 1.4% as CONTESTED before finding this correction; the two
  recounts agree and the 1.4% must not be quoted as a corpus rate. The same
  recon adds the crossing-level census the rate alone lacks: at 306 plane-
  crossing grants, field 4 traces to a real recently-relevant plane in 305/306
  — one-grant lag dominant at 79.7% — retail never observed fake-labelling.)*
- **Retail's field order** (agent-internal, so identification-free): dest_plane
  **leads** — the agent's cur_plane becomes it afterwards in 939 of 1,245 (75.4%,
  delay p50 0.64 s; 83.6% under a symmetric ±3 s window). ⚠ Measured over the
  whole agent population, overwhelmingly NPCs; the player-identified version is
  UNVERIFIED (87% vs 39% under two identification rules). REALFIX-F1 is grounded
  in NPC grants and labelled so.
- **REALFIX-W1/W2, the walk facts that redesign L2** (full set in REALFIX.md §6):
  every key-down emits a `0x003D` at the exact previous stop position (10 of 10),
  so every leg opens at separation 0 and legs are independent trials; and free-
  travel reports are **DISTANCE-triggered at ~515 u** (chord p50 513–514 u at
  both 1.80 s and 2.74 s gaps), so under zero-lead separation saturates at one
  chord and the copy's lag is set by the client's own report trigger, not by our
  grant floor — **at keyboard cadence P2 has no cheap cadence dial.**

### 5. Where the arc goes

REALFIX-L2 (REALFIX.md §6): six cells, X2a-vs-X3 as the mechanism crux, X6
filling the empty confound cell, X5 running the invariant's own falsifier
deliberately at sep 228 u, instruments first (T1 float wall stamp kills the 1.00 s
offset spread; T2 float leg stamps; I1 the chain walk gated on sep > 250 u), arm
P0 as geometry calibration, then P2, then **REALFIX-F1** (field 4 = the plane
that arrived with the point the copy stands on — one line, one state slot) only
if X1/X3 produce events. The round-4 trigger run stays with the owner and is
unchanged. Pre-registered predictions with their power arithmetic are in the
protocol; the ladder-deciding cell is X2a — a positive there sends the arc to
P3/§2.2, because W2 means no grant-side parameter can shorten the chord.

## 2026-08-21 — REALFIX-L2 RAN AND REACHED NO CELL: the plan's frame was 108° wrong, and yaw is not linear

**The instruments landed and work. The protocol did not run.** Two arms, identical
28-leg plan, P0 (`--explorable`) then P2 (`+ --zero-lead`), movetap attached after
the map verdict at 20 Hz. Captures `20260821T123327` / `123942` (gamesrv),
`movetap-20260821T123338` / `124010`. **Not one of the six cells was visited.**

### What went wrong, measured from P0's own capture

| constant | plan assumed | **MEASURED** | error |
|---|---|---|---|
| spawn facing (REALFIX-W5) | −65.80° | **+44.31°** (first held heading, n=4 intervals within 1°) | **+108°** |
| yaw response (REALFIX-W4) | −0.0800 °/px, linear | `yaw:332` → **−1.69°** (−0.0051 °/px); `yaw:951` → **+113.22°** (+0.119); `yaw:−1451` → **−140.00°** (+0.097); `yaw:111` → **+26.78°** (+0.241) | **nonlinear AND sign-inconsistent** |

Every leg after the first inherits the facing error, and the yaws cannot correct it
because their response is not a constant times pixels. The character walked
northeast — x 9826→14170, y 8077→11130 — while the bridge corridor the round-6
events came from (x 10860–11123, y 4326–5279, plane 18) sits ~2,300 u south.
**0 of 2,567 (P0) and 0 of 2,154 (P2) samples inside it.**

⚠ **The navmesh march did not catch this and could not have.** It marched from the
*assumed* spawn facing, so it validated a path the client never walked; it reported
"zero unintended blocked legs" for a plan that never left the wrong quadrant. **A
plan validated only against our own mesh is validated against our own assumption.**
The operator flagged wall contact twice during these runs and was right both times.

**REALFIX-W4 is REFUTED as a calibration.** The design lane's own supporting
measurement — "the commanded heading is exactly constant within a leg, max
deviation 0.000° over 16 legs" — is *within-leg constancy*, which is true and
useful, and it does not license a **between-leg** yaw response. The two were
conflated (by this session, in the plan assembly) and the conflation is what put
`yaw:N ⇒ −0.08·N` into a protocol as if it were measured.

### What the run DID establish

- **REALFIX-I1 works.** First chain walks ever taken from a live client: P2
  **775 `ok`** node walks, 119 `truncated:max-nodes`, 1,259 `not-attempted:below-gate`
  (the gate doing its job), 1 `empty:head-null`. P0: 179 `ok`, 2,193 truncated. The
  refusal vocabulary appears in real data and no sample returned garbage.
- **The chain walk's live Hz cost is now measured**, closing readiness item (3):
  **23,839 Hz gated vs 18,430 Hz forced, −23%** at the reader's own capability. The
  offline read-count figure (+112%) is the pessimistic bound; the achieved Hz cost
  is a quarter of that.
- **REALFIX-T1 is in the captures** — `wall_unix` present, so the 1.00 s offset
  spread that cost round 6 its alignment is gone from every future run.
- **A weak but real data point on the mechanism.** P2 sent **79 grants**, and
  movetap recorded **680 of 2,154 samples with separation above the gate-1 cut**
  (p50 424, max 530 u) — **with zero REALFIX-E events** (async step max **54.2 u**;
  P0's max 62.5 u). And the two copies' planes **never disagreed**: the
  `(sync_plane, async_plane)` census is `{(0,0): 2,070, (29,29): 84}`, against L1
  arm B's 45 mismatched samples. **Consistent with round 6's reading — above-cut
  separation alone does not warp, and no plane mismatch means no warp — but it is
  not a test of it**, because the run never produced the treatment condition (a
  plane rewrite onto a lagged copy). Recorded as corroboration of the *necessity*
  half at n=680, not as evidence about sufficiency.
- Both arms crossed a plane 0↔29 boundary (84–90 samples) in the northeast, so
  **the map has a second plane boundary the character reaches on its natural
  facing** — a candidate site that needs no yaw at all.

### What REALFIX-L3 needs, in order

1. **Calibrate yaw empirically, or design around it.** The response is nonlinear
   and possibly saturating (332 px → 1.7°, 951 px → 113°). Cheapest: one dedicated
   run of `yaw:N wait:2 W:2` for N ∈ {±100, ±250, ±500, ±1000, ±2000}, reading the
   held heading after each — no map knowledge needed, and it is the calibration
   `PROBE-GATEFIRE`-style protocols have always required before steering.
2. **Or relocate the cells to the plane 0↔29 boundary** the character reaches on
   its own facing, which removes yaw from the critical path entirely. Its geometry
   is unmeasured; P0's capture is the calibration substrate for it.
3. **Either way, the plan must be validated against an OBSERVED path, never a
   marched one.** The rule already exists (`REALFIX.md` §6.1.5, cell assignment
   from the observed path); what this run shows is that it must also govern plan
   *construction*, not only scoring.

## 2026-08-21, later — THE YAW CALIBRATION: W4 is CONFIRMED, my refutation of it is WITHDRAWN, and W5 was the only broken constant

**OBSERVED, `ours`, dedicated sweep** — capture `20260821T130913`, harness
`20260821T130838`, plan `[wait:2 W:2 wait:2 S:3]` baseline then the same cycle
after each of `yaw:±100, ±250, ±500, ±1000, ±2000`. Eleven out-and-back
measurements around spawn, each leg's travel bearing taken from its own first and
last report with the leg boundaries read off `REALFIX-T2`'s float stamps.

### The yaw response is LINEAR, and it is the number the design gave

| token | Δ facing | °/px |
|---|---|---|
| −100 | +7.47° | −0.07468 |
| ±250 | ∓20.06° | −0.08023 |
| ±500 | ∓40.06 / +40.28° | −0.08011 / −0.08057 |
| ±1000 | ∓80.28 / +80.36° | −0.08028 / −0.08036 |
| ±2000 | ∓160.36 / +160.06° | −0.08018 / −0.08003 |

**Least squares through the origin: −0.080152 °/px, n = 9, residual max 0.55°
over a ±2,000 px range.** `REALFIX-W4`'s `−0.0800` reproduces to three figures.

⚠ **THIS WITHDRAWS THIS DOCUMENT'S OWN "W4 IS REFUTED", written hours earlier and
merged.** That claim came from reading yaw responses out of the L2 capture, where
two things corrupted every pairing: **S legs reverse the travel bearing by 180°**
and were being read as yaw effects (the ±179.8° "responses"), and **wall-slid legs
report the wall's bearing, not the facing** (the −0.005 °/px "response"). The
correct method needs a dedicated sweep with clean legs, which is what this is. A
constant is not refuted by a measurement taken through a confound the measurement
did not control for.

### The operator caught the one bad leg, and the guard now catches it too

The operator warned mid-run that the first out-and-back angles looked like they
were hitting a wall. **They were**: leg 0 ran **436 u of an expected 570 (76%)
with a 71° mid-leg bend**, and its `yaw:100` pairing reads −13.65° against the
−8.02° every other token predicts. It is **EXCLUDED** by two automatic rules —
distance < 80% of `v·duration`, or a mid-leg bearing deviation > 20° — and both
rules are in the fitter rather than in prose. Without the exclusion the fit moves
and the residual triples.

### W5, the spawn facing, is the ONLY constant that was wrong — and it is not 44°

`REALFIX-W5` said −65.80°. The L2 post-mortem then said "+44.31°, measured". **Both
are wrong, and the second is wrong in an instructive way.** L2 arm P0's opening
trace, read interval by interval:

| gap | dist | bearing | |
|---|---|---|---|
| 1.57 s | 428.7 u | **+3.30°** | free travel, full speed |
| 0.50 s | **46.9 u** | +77.66° | cadence tightens, speed collapses to 94 u/s |
| 0.50 s | 58.0 u | +65.06° | |
| 0.50 s | 104.3 u | +45.52° | |
| 0.50 s | 107.7 u | +44.37° | |
| 0.50 s | 106.4 u | **+44.30°** | held — **this is the WALL's bearing** |

That is round 4's own wall-contact signature (report cadence 1.80 s → 0.50 s at
contact, speed falling to 260–265 u/s there and to 94 u/s here). **The "+44.31°
held heading" the post-mortem measured was the character sliding along a wall**,
which is exactly the error the post-mortem was written to correct, committed one
paragraph later. Recorded because it is the second time in one day this arc read a
wall as a fact about the player.

**The true spawn facing, from two independent runs:** L2 arm P0's first free
interval `+3.30° − 2.40°` (`yaw:-30`) = **+0.90°**; the calibration's second W leg
`−7.41° + 8.02°` (`yaw:100`) = **+0.59°**. **W5 = +0.75° ± 0.15°**, against the
−65.80° the plan assumed — a **66.5° error**, and the whole reason L2 walked
northeast into a wall instead of southeast to the bridge.

### What this unblocks

Steering is calibrated: from spawn `(9826, 8077)` at `+0.75°`, the bearing to the
bridge's north apron `(10990, 5750)` is **−63.42°**, i.e. **`yaw:801`** — one
token, and the geometry march can be trusted for the first time because both of
its frame constants are now measured rather than assumed. **REALFIX-L3 is the L2
plan with `W5 = +0.75°`**, and the standing rule from the L2 post-mortem still
governs: the plan is validated against the OBSERVED path, and any leg that runs
short or bends is a wall, not a datum.

## 2026-08-21 — REALFIX-L3: THE WARP IS REPRODUCED PROSPECTIVELY, THE PLANE REWRITE IS THE TRIGGER, AND CORNER-CUTTING IS REFUTED AT THE CELL BUILT TO TEST IT

**OBSERVED, `ours`.** Two arms, the corrected six-cell plan (`W5 = +0.75°`,
`W4 = −0.080152`), identical scripted input, movetap attached after the map
verdict at a requested 20 Hz. P0 `20260821T131938` / `movetap-…131955`;
P2 `20260821T132546` / `movetap-…132603` (`--zero-lead`). **Both arms reached the
bridge this time** — P0 spent 48% of its samples in the corridor with 555 on
plane 18, against L2's zero — which is what makes everything below a measurement
rather than an accident.

Scored on **REALFIX-E only** (an `async_at` step ≥ 150 u within ≤ 0.25 s), the
definition pre-registered in round 6 precisely so that `sep`, `gate1`, `fence` and
the plane words stay covariates and cannot be recruited as identifiers.

### 1. The headline, and the control that gives it its weight

| | **P0 default** | **P2 `--zero-lead`** |
|---|---|---|
| **REALFIX-E events** | **0** | **3** — 476.8, 465.9, 242.8 u |
| max `async_at` step | **43.0 u** (n = 2,537) | 476.8 u (p99 38.3) |
| grants | **0** | 88 |
| samples above the gate-1 cut | **2,461 (97%)** | 747 (29%) |
| samples with the two copies' planes DISAGREEING | **571** | 137 |
| fence clears | 2 | 6 |

**The control is the finding.** P0 carried the supposedly dangerous state far more
heavily than P2 — **7× the plane-mismatch samples and 97% of its run above the
gate-1 cut, against P2's 29%** — and its rendered copy never moved more than
**43 u** in a sample. Separation and plane disagreement are not sufficient, and
they are not even close. What P0 lacks is the **grant**: with none sent, the
AgTrack dispatcher is never entered and the client is never asked the question.

### 2. Every event is a plane rewrite, and the timing is now real

Each event follows a grant by **0.05 / 0.10 / 0.11 s** — the bake → dispatch →
reseed chain, timed against `REALFIX-T1`'s **0.354 ms** clock residual (0.10 u at
run speed) rather than round 6's 1.00 s slop. Decoded from the sent bytes:

| event | grant | dest | plane word | previous grant's | sep before → after |
|---|---|---|---|---|---|
| t+46.37, 476.8 u | t=63.695 | (10951, 4929) | **18** | 0 | 500.7 → 23.9 |
| t+76.49, 465.9 u | t=93.759 | (10948, 4625) | **18** | 0 | 509.1 → 13.8 |
| t+110.85, 242.8 u | t=128.111 | (10948, 4617) | **18** | 0 | 294.7 → 23.0 |

All three are **backward** (y falling 4916→4439, 4622→4157, 4617→4374), all land
on the lagged authoritative copy (13.8–23.9 u), all carry `fence_raw` 1→0 in the
same sample, and all sit on the bridge (`async` plane 18) with the **sync copy
reading plane 0** — the copy is on the near side, the client is on the deck, and
we stamp the client's plane onto the copy.

**The grant-level 2×2, from client memory, the whole run:**

| | above the cut | below |
|---|---|---|
| **plane word rewritten** | **8 grants → 3 events** | 2 → 0 |
| plane word unchanged | **28 grants → 0 events** | 50 → 0 |

**Twenty-eight grants landed on a copy more than 299.33 u out of position with
the plane word unchanged, and not one of them warped.** Fisher exact on the
above-cut row, 3/8 against 0/28: **p = 0.0078**. Round 6 measured 3/4 against
0/27 retrospectively; this is the same result obtained forward, from a run
designed to produce it, with a control arm that could not express it.

**Still necessary-not-sufficient, and the ratio is now better measured**: 5 of the
8 plane-rewriting above-cut grants did **not** warp (round 6's grant #37 was the
first such case, at n = 1). Whatever selects those 3 from those 8 is unmeasured;
`REALFIX-I1`'s chain nodes are recorded in this capture (709 `ok` walks) and are
where that question gets answered.

### 3. The crux cell resolves: corner-cutting is REFUTED

⚠ **READ THE CORRECTION FIRST — "THE X2a CELL NEVER RAN" below.** X2a did not run (0 of 783 samples in its window are on the deck), so its null is not evidence and this section's X2a leg is WITHDRAWN; corner-cutting remains refuted on the chain measurements.

All three events are on the **shuttle** — constant x ≈ 10,950, y sweeping
4,113–4,929, i.e. **REALFIX-X3**, the straight perpendicular crossing with no wall
contact. The wall cells ran and produced nothing: **the late legs (X1's parapet
slides across the boundary and X2a's slides inside the deck) carry 55 grants, 15
of them above the cut and 3 of them plane-rewriting, and produced 0 events.**

REALFIX-X3's pre-registration reads: *"`X3 ≥ 6 with X2a = 0` ⇒ **A**, B refuted."*
The direction is met — **X3 = 3, X2a = 0** — while the count is under the
predicted 6 because the plan yielded 8 above-cut plane-rewriting instants rather
than the 11 simulated. **Recorded as: candidate B (corner-cutting) is REFUTED at
the cell built to test it, and candidate A (the plane echo) is the surviving
mechanism, at a rate lower than predicted.** ⚠ X2a's null is a null: at 3 events
per 8 treated grants, the probability of seeing none in its 15 above-cut instants
is not negligible, and the cell's own power note said so before the run.

⚠ **The X5 falsifier did NOT cleanly fire.** Event 3's pre-snap separation reads
**294.66 u, below the 299.332591 cut** — which is `REALFIX.md`'s stated condition
for the invariant itself to fail. It is **not** claimed here: movetap achieved
**9.1 Hz against the 20 requested**, so consecutive samples are ~110 ms apart and
the copy covers ~32 u between them; the true pre-snap separation is within
sampling reach of the cut. **Positives valid, nulls void, and this particular
positive's covariate is not precise enough to fire a falsifier.** A rerun at a
sustained 20 Hz decides it.

### 4. What this licenses, and what it does not

**Licensed:** the plane word is the trigger under `--zero-lead`, forward and
backward, in two independent runs, with a control arm that carried more of every
rival condition and produced nothing. **REALFIX-F1** — send the plane that
arrived with the point the copy is standing on, rather than the client's current
plane — now has a reproduction to be tested against, and its own prediction is
already written: the three bridge reseeds go to zero, separation unchanged within
5%, and the field-4 mismatch count goes to 0.

**Not licensed:** which of the 8 treated grants warp (3 did, 5 did not); anything
about the round-4 spam-click regime, which this plan does not touch; and any claim
resting on a sub-100 ms covariate at 9 Hz. **The tap rate is now the binding
instrument limit** — it has run at 7.8–9.1 Hz against a 20 Hz request in every
session today, and `REALFIX-T3` said the residual becomes sample-phase-bound the
moment the clock stopped being the problem. It did; it is.

### REALFIX-I1's first result: the copy is ON the polyline, so the walkable conjunct is the only thing that can fail

**OBSERVED**, from L3's P2 capture (`movetap-20260821T132603`), 709 complete chain
walks, 698 of them scorable against the recomputed match predicate:

- **The nearest chain segment to the SYNC copy is 0.0 u away in 698 of 698
  samples (100%).** The straight-line conjunct of `seg_match` therefore passes
  everywhere in this run, and **no warp here can be a straight-line failure.**
  With the copy provably on the polyline, the only conjunct left to fail is the
  **walkable** one at `0x00605C40`/`0x00709990`, whose start is `q` — carrying the
  plane word `agent+0x80`, which is the field `--zero-lead` rewrites. **Round 6
  reached that site by eliminating the alternatives; this reaches it by
  measurement.**
- **76 of the 698 samples have the nearest segment on a DIFFERENT plane than the
  sync copy**, and event 3's neighbourhood is one of them: `syncplane 0` while the
  nearest chain segment reads `segplane 18`, held across four consecutive samples
  before the snap.

⚠ **The 0.0 u is partly definitional under this policy, and round 5 §6.5 named
that before the run.** Under zero lead the copy parks on a previously granted
point, a granted point IS a previously reported position, and chain nodes are
positions the client reported — so a small distance is expected by construction.
What the measurement adds beyond the tautology is (a) it is **exactly** 0.0 and
not merely small, so the identity holds through the client's own node bookkeeping
rather than approximately, and (b) it holds at the warp instants, which is what
rules the straight-line conjunct out **there**. Under any leaded policy the same
measurement would not be definitional — and that is the version worth taking.

## 2026-08-21 — REALFIX-F1 RAN: zero warps, but its own primary falsifier FIRED, and the event reduction is not significant at n = 1

**OBSERVED, `ours`.** Third arm on the identical L3 plan, `--zero-lead
--plane-carry`, capture `20260821T143411` / `movetap-…143429` (9.5 Hz — below
floor, positives valid, nulls void).

| | **P0 default** | **P2 `--zero-lead`** | **F1 `+ --plane-carry`** |
|---|---|---|---|
| **REALFIX-E events** | 0 | **3** | **0** |
| max `async_at` step | 43.0 u | 476.8 u | **38.3 u** |
| grants | 0 | 88 | 93 |
| plane-word changes | — | 10 | **24** |
| samples above the gate-1 cut | 97% | 29% | 38% |
| separation p50 / p90 / max | 3712 / 6046 / 6138 | 150 / 498 / 530 | 227 / **491** / 527 |

**F1 is doing the thing it was built to do.** 24 grants carried a field 4 that
differs from field 3 — the carry firing at every boundary crossing — against 0 in
the control, where the two fields are equal by construction.

### The falsifier fired: the mismatch did not go to zero

F1's pre-registration, printed at startup: *"grants whose field 4 differs from
the SYNC copy's `agent+0x80` go to 0 … FAILS IF the field-4 mismatch count is not
0."* Scored against client memory, per grant, both arms:

| | grants | field 4 ≠ the copy's own plane |
|---|---|---|
| P2 `--zero-lead` | 88 | **8 (9%)** ⚠ undercount — strictly-before pairing gives **10**; see the F1b entry |
| F1 `+ --plane-carry` | 93 | **5 (5%)** ⚠ undercount — strictly-before gives **6** |

**Five is not zero, so the primary falsifier FIRED.** And all five sit **above the
cut** — the exact combination that produced 3 of 8 events in the control:

```
t= 50.21 (10950,4720) w3=18 w4=18 | copy plane 0 | sep 514
t= 77.42 (10950,4708) w3=18 w4=18 | copy plane 0 | sep 511
t=104.67 (10950,4699) w3=18 w4=18 | copy plane 0 | sep 511
t=178.93 (11123,5249) w3=18 w4=18 | copy plane 0 | sep 366
t=191.66 (10860,4816) w3=18 w4=18 | copy plane 0 | sep 429
```

⚠ **CORRECTED by the F1b offline screen below: THREE of these five are a sub-frame arrival race (F1 sent the right value ~24 ms early), and only `t=178.93` and `t=191.66` are two-interval lags.** As written this read: **the spec's own NAMED LIMIT, biting exactly where it said it would**: *"F1 under-corrects when the copy is more than one grant interval
behind."* All five send `w4 = 18` because the **previous grant** was already on
plane 18 — the client had been on the deck for two grants while the copy was
still back on plane 0. F1 corrects a one-interval lag; these are two-interval
lags. The limit was written before the run and is now measured.

### ⚠ The event reduction is NOT significant, and saying otherwise would be the


On the condition that actually matters — above the cut **and** field 4 wrong —
the control had **8 such grants and 3 events**; F1 had **5 such grants and 0
events**. **Fisher exact: p = 0.196.** At these counts, zero events in five
exposures is what chance produces about one time in five. **F1's zero is
consistent with the fix working and equally consistent with it doing nothing to
the events**, and the run cannot separate those.

What the run *does* establish: F1 **reduces the exposure** (8 → 5 dangerous
grants, −37%) by a mechanism that is measured rather than argued, and it does so
without touching position — separation p90 **498 → 491 u (−1.4%)**, inside the
±5% the prediction demanded.

⚠ **The p50 separation moved 150 → 227 u (+51%) and above-cut time 29% → 38%,
and F1 cannot have caused either** — it changes one 16-bit field and no
coordinate. That is run-to-run path variance on an identical script, the same
variance that made L1's two identical-play baselines differ by 1.7×. **It is also
the reason the event comparison is weak: if the substrate moves that much between
runs, a 3-versus-0 difference at n = 1 per arm is not a measurement.**

### What this means for the fix

**The mechanism story survives and strengthens** — the carry works, the residual
is explained by its own stated limit, and nothing contradicts round 6 or L3.
**The fix is not demonstrated.** Two things would settle it, in order:

1. **REALFIX-F1b — carry the plane of the grant the copy has ARRIVED at, not the
   previous one sent.** The server already computes arrival (`dist / speed` is
   the same arithmetic the bake uses), so this needs no navmesh and no new
   measurement; it closes exactly the two-interval case all five residuals sit
   in. **Predicted: the field-4 mismatch count reaches 0**, which is the
   falsifier F1 just failed, and it is a real prediction because F1's own
   residual pattern says where the remaining five come from.
2. **Repetition.** Three arms × three runs would put the event comparison on
   n = 9 per arm; at the control's 3-in-8 rate, that is enough for the Fisher
   test to separate a real zero from a lucky one.

## 2026-08-21 — REALFIX-F1b BUILT AND REFUTED AT A DESK: the offline screen kills its prediction, corrects two published numbers, and validates the arrival model

**No client run.** `--arrival-carry` sends field 4 = the plane of the grant the
copy has **arrived** at, computed from the client's own bake formula
(`arrival = send + trunc(|dest − copy|·1000/288)`, floored at 1) over the SYNC
model the server already maintains — no navmesh, no new constant. Its point was
to close F1's named limit. **It was pre-screened against captures already in the
vault before any arm was run, and the screen refuted its prediction.**
`python toolkit/clientscan/grantsim.py --planecarry` is the permanent screen.

### 1. THE COUNTERFACTUAL — what each policy would have sent

Field 4 scored against the plane word movetap **actually read in the sample
strictly before each grant**, with grants dropped where the counterfactual's own
divergence contaminates the trace (denominator printed, never hidden):

| policy | `132546` (P2 control) | `143411` (F1 arm) |
|---|---|---|
| shipped `--zero-lead` | **10** of 88 | **18** of 36 |
| F1 `--plane-carry` | 0 of 8 | **6** of 93 |
| **F1b `--arrival-carry`** | 0 of 8 | **3** of 69 |

**F1b does NOT reach 0, so its pre-registered prediction — the falsifier F1
failed — would have failed too.** Recorded before a client was ever pointed at
it, which is the entire reason the screen exists.

**The three survivors are a sub-frame race, not a logic error.** All three land
**8–35 ms after a modelled arrival the client had not yet performed**
(`(10950,4720)`, `(10950,4708)`, `(10950,4699)`, all `w3=18 field4=18` against an
observed plane 0, sep 510–514 u). The client consumes an arrival **on a frame**,
not on the tick. **F1b's logic does close all of F1's genuine two-interval lags.**
A ~40 ms guard band closes the rest and is **REFUSED**: `eps` has no derivation
and would be fitted to the one capture that scores it.

### 2. ⚠ TWO CORRECTIONS TO THIS DOCUMENT'S OWN PUBLISHED NUMBERS

**(a) The field-4 baselines UNDERCOUNT.** FINDINGS's "8 of 88" and "5 of 93"
paired each grant with the *nearest* movetap sample — which can be one taken
**after** the grant, reading back the plane word that grant just wrote and
scoring a genuine rewrite as a match (leads +0.044, +0.043, +0.016 s).
**Strictly-before pairing gives 10 of 88 and 6 of 93.** The 10 is corroborated
independently by this document's own L3 table, which counts **10** plane-word
changes on that capture. Both conventions are kept in the code
(`FIELD4_PUBLISHED_NEAREST` / `FIELD4_MEASURED`) so the correction cannot be
silently re-lost. **F1's improvement is 10 → 6, not 8 → 5.**

**(b) "All five of F1's residuals are the spec's NAMED LIMIT" is WRONG.** Written
in the F1 entry above and merged; the screen shows **three of the five are the
sub-frame arrival race** (F1 sent the right value ~24 ms early) and **only
`178.93` and `191.66` are true two-interval lags**. The named limit is real and
it bit — on two grants, not five.

### 3. What the screen validated on its way past

**The arrival model is falsifiable, and it survives with zero free parameters.**
`agent+0x80` has two writers: our field 4 at the grant, and the client itself at
**arrival**. In the F1 capture the word changes 24 times, **17 of them not at a
grant — and all 17 land on a modelled arrival** (|dt| median 0.070 s, max
0.135 s at a 9.5 Hz tap; strictly early in 4 of 17, by at most 20 ms). That is a
prediction of *when the client will move a byte we do not write*, made from the
bake formula alone, and it lands 17 for 17.
**Control, and it is asserted rather than passed:** the P2 capture makes **zero**
client-authored writes, so the model is unfalsifiable there **by construction** —
the check requires `n == 0` instead of scoring 0-of-0 as a pass.

**The closed simulation is printed BELOW the anchored table and labelled a
tautology**: F1b returns 0 under it *by construction*, because that simulator
derives the copy's plane from the same arrival model F1b's policy reads — and it
**under-counts F1's own residual, 3 against the wire's 6**. Same discipline as
round 5 §6.5, applied to a number that would have flattered this build.

### 4. Where this leaves the fix

**Nothing here is a live result and F1b's arm has not been run** — deliberately:
its own screen says the headline it was built to produce is unavailable.

- **The mechanism story is stronger than before this build**, on the arrival
  model's 17-for-17 and on the corrected baselines.
- **The fix is no closer to demonstrated.** F1 improves the exposure 10 → 6;
  F1b would improve it to 3 with the residual explained but not removed; and
  **F1's own event reduction remains non-significant (Fisher p = 0.196)**. The
  binding constraint is not the policy any more, it is **n**.
- **What settles it is repetition, not another flag**: three arms × three runs
  puts the event comparison on n ≈ 9 per arm, where the control's 3-in-8 rate can
  actually separate a real zero from a lucky one. **The next client time this arc
  spends should buy replicates, not a fourth policy.**

## 2026-08-21, later — ⚠ THE X2a CELL NEVER RAN: the slide legs walked off the deck, and one leg of the corner-cutting refutation is WITHDRAWN

**Operator-reported and confirmed.** The operator watched the L3 runs and noted
the character eventually veers off the bridge into a narrow corridor. It does,
both arms, and the wall cells are the cause.

**What is EXPECTED and worked**: the parapet contact itself. P0's wire shows
textbook wall-slide at t+160–166 — **x pinned at exactly 11123.0 for eight
consecutive reports** while y slides 5372 → 4595, speed **218–225 u/s** against
the 285 u/s free-travel rate, report cadence tightened to **0.50 s**; and again
at t+171–175 against the west parapet, **x = 10860.0**, 146–149 u/s. That is
REALFIX-X1 doing exactly what it was built to do, and it is round 4's own
contact signature reproduced.

**What is NOT expected, and it is a defect in this plan**: the character never
returns. At t+181 it leaves at 512.9 u per interval, full speed, southeast, and
does not come back. **The cause is that a slide displaces the character
PERPENDICULAR to its heading, while the plan's back-out (`S:4` / `S:1.5`)
reverses along the HEADING.** The perpendicular component is never undone, so
every rep starts further along the wall, and three X1 reps plus the X2a transit
accumulate enough drift to leave the deck entirely.

**THE COST, measured**: of the samples in the X2a window (t+195 onward),
**0 of 782 (P0) and 0 of 783 (P2) are on the deck** (`10860 ≤ x ≤ 11123`,
`4532 ≤ y ≤ 5579`). **REALFIX-X2a did not run at all.** Its instants were spent
in open ground southeast of the bridge.

### What this withdraws, and what survives

**WITHDRAWN — the L3 entry's "corner-cutting is REFUTED at the cell built to test
it".** That sentence rests on X2a returning zero events. X2a returned zero
*instants of its own condition*, which is not the same thing and is not evidence.
The cell is **NOT MEASURED**, exactly as `REALFIX.md` §6.1.5's own rule requires
when the observed path leaves the intended one — the rule was written for this
and this is the first time it has had to fire.

**SURVIVES, on stronger evidence than X2a ever was.** Corner-cutting is still
refuted, by two independent measurements that do not involve the wall cells at
all:

1. **Round 6's chain reconstruction**: a node at every wire report gives **0
   exceedances** of the 99.92 u radius (max 72.4 u), and at all three of that
   round's warps the copy-to-polyline distance is **0.0 / 0.0 / 0.0 u**.
2. **L3's own REALFIX-I1 chain walk**, read from the client's own history nodes:
   the sync copy is **0.0 u from the nearest chain segment in 698 of 698 scored
   samples**, so the straight-line conjunct cannot be what fails.

**So the conclusion stands and its X2a leg is amputated.** The distinction
matters because a reader who takes "the wall cell came back empty" as support
would be reading a cell that never happened.

### The fix for the next plan

Back out of a wall cell by **retracing the OBSERVED path**, not by reversing the
heading — or re-anchor with an explicit transit after every slide rep, which the
X1 legs already do between reps and the X2a legs do not. Cheapest correct form:
one transit token before **each** slide rep, accepting ~8 s of walking per rep to
buy a cell that is actually where it says it is. And the general rule this is the
third instance of: **a plan's later legs are only where the plan says while
nothing has touched geometry; after any wall contact, position is an observation,
not a prediction.**

## 2026-08-21 — ★★ REALFIX-L4: THE FIX IS DEMONSTRATED. Pooled 9 of 21 against 0 of 13, Fisher p = 0.0056
⚠ **SCOPE, added 2026-08-21 after REALFIX-L5: this result is REGIME-SPECIFIC and holds only where plane boundaries are crossed.** The spam-click regime has a SECOND mechanism — grant distance, no boundary involved — and `--plane-carry` has no purchase on it at all. See FINDINGS §"REALFIX-L5".

**OBSERVED, `ours`.** Two arms, a **shuttle-only** plan built for exposure rather
than coverage — the wall cells were dropped (they drift off the deck, and X2a
never ran) and that time spent on **8 crossing cycles** instead of 3. Identical
scripted input both arms; movetap attached after the map verdict.
Control `20260821T161910` / `movetap-…161928`; F1 `20260821T162449` /
`movetap-…162505`.

| | **control `--zero-lead`** | **F1 `+ --plane-carry`** |
|---|---|---|
| **REALFIX-E events** | **6** | **0** |
| max `async_at` step | 472.2 u | **60.7 u** |
| grants | 61 | 70 |
| field 4 ≠ the copy's own plane | 14 | **8** |
| **…and above the cut (TREATED)** | **13** | **8** |
| separation p50 / p90 / max | 303 / 513 / 529 | 349 / 515 / 529 |
| samples above the cut | 56% | **69%** |

The six control events: 463.5, 472.2, 263.6, 467.1, 285.3, 458.7 u, each
collapsing separation from 297–515 u onto 13.8–27.1 u. **The design worked as
intended** — 13 treated grants against L3's 8, at a consistent rate (6/13 = 0.46
against L3's 3/8 = 0.375).

### The statistics, and this run is why they close

| comparison | control | F1 | Fisher (one-sided) |
|---|---|---|---|
| L3 alone | 3 of 8 | 0 of 5 | p = 0.196 |
| **L4 alone** | **6 of 13** | **0 of 8** | **p = 0.032** |
| **POOLED** | **9 of 21** | **0 of 13** | **p = 0.0056** |

Under the null that F1 does nothing to events, its 13 pooled treated grants
should have produced **5.6 events**. They produced **zero**.

**And it is not an exposure artifact — the arithmetic runs the wrong way for
that.** The F1 arm sent **more** grants (70 vs 61) and spent **more** of its run
above the gate-1 cut (**69% vs 56%**) with a **higher** p50 separation (349 vs
303 u). It had more of every condition that precedes a warp, and produced none.

### What is now established, and in what terms

**REALFIX-F1 removes the warp.** The mechanism was decoded (round 6), reproduced
prospectively with a control that could not express it (L3), and is now removed
by a three-line change at p = 0.0056 across two independent runs with 34 treated
grants between them. The chain from wire to warp is measured end to end: field 4
→ `agent+0x80` → `q`'s plane in the match test's walkable conjunct → no match →
gate 1 at ~500 u → whole-roster reseed → the character yanked ~460 u backward.

**What is still NOT established, and none of it is load-bearing for the above:**

- **F1 does not zero its own mechanism proxy.** Field 4 still disagreed with the
  copy's plane on **8 of 70** grants here (14 of 61 in the control), so the
  primary falsifier from F1's own banner remains failed. Its offline screen says
  why: some are two-interval lags, some are the sub-frame arrival race. **The
  fix works despite an imperfect proxy, which means the proxy is not the
  mechanism** — a distinction this arc should keep, because F1b was built to zero
  the proxy and would have bought nothing measurable here.
- **The regime is one map, one plan, keyboard-only, click-free.** The round-4
  spam-click regime (11.49 hard rows/min under the shipped default) is untouched
  by any of this and remains the operator's run.
- **The instrument ran at 8.4–9.5 Hz against a 20 Hz request** in both arms.
  Positives valid, nulls void — and the headline here rests on a **positive in
  the control** (6 events) and a null in the treatment. The null is licensed by
  the control's own rate at matched exposure, not by the tap.
- **`--zero-lead` itself remains undemonstrated as a warp fix** against the
  shipped default. It is the substrate F1 is measured on, not a proven
  improvement over P0 — and P0 in this regime sends no grants at all.

## 2026-08-21 — ⚠ REALFIX-L5: THE SPAM-CLICK REGIME IS A DIFFERENT MECHANISM, `--zero-lead` IS INERT IN IT, AND THE COMPOSITE'S ZERO IS NOT A FIX

**OBSERVED, `ours`.** Four arms, map 148, build 38797, human-driven — hold `S`
and spam-click, round 4's own trigger. Owner at the keyboard throughout: a held
key with simultaneous clicks is not expressible in `walk_legs`
(`REALFIX.md`:486) and world-anchored clicking is the operator's side of the
boundary. Captures `20260821T172112` / `172338` / `172557` / `172947`, movetap
on all four.

**Arms recovered from BEHAVIOUR**, because the gamesrv jsonl header carries no
argv (REALFIX-Q8) — and over-determined by three disjoint fingerprints: the
`grant_verdict` reason vocabulary (`"off"` ⟺ `GRANT_SUPPRESS` off,
`authsrv.py`:3306; `"locally-moving"` reachable only with it on, :3317), the
`sent` label prefix, and the `plane_carry` / `carry` telemetry fields. **The
flag labels are earned, not assumed**: `plane_carry = true` and
`carry = "plane-carry"` appear on 180 (A2) and 192 (A3) verdict rows.

| arm | flags | span | grants | **hard jumps** | rate |
|---|---|---|---|---|---|
| **A1** | shipped default | 53.7 s | 145 | **14** of 173 | 15.66/min |
| **A2** | `--zero-lead --plane-carry` | 55.3 s | 193 | **10** of 182 | 10.85/min |
| **A3** | + `--grant-suppress` | 61.3 s | 96 | **0** of 195 | **0.00/min** |
| **A4** | shipped default (bracket) | 47.4 s | 94 | **12** of 152 | 15.17/min |

Scored with `movesync.py --wire-only`, which needs no movetap — necessary
because **A3's tap ran 12.5 s of a 61.3 s arm** (120 samples against 464–519),
and "positives valid, nulls void" refuses a null over 17.7% of an arm. The
paired and wire-only bars agree on A1/A2/A4 — ⚠ but that agreement is an
ALGEBRAIC IDENTITY, not a check: `pair()` dropped zero reports there, so both
ran the same predicate over the same list.

### What survives

**S1 — a clean bracketed P0 baseline in this regime: 15.66 and 15.17/min, a
1.03× spread.** Round 4's two baselines on identical stated play differed
**1.7×**; this is the tightest control pair the arc has. It is the single most
reusable number here.

**S2 — `--zero-lead` does NOT fix the click regime.** A2 is byte-identical to a
bare `--zero-lead` arm on the wire (see W3 below), so it *is* the gap-(a) test:
**RR 0.703, exact 95% CI [0.303, 1.507]** — the interval covers 1.000, i.e.
inert. Power to detect its own pre-registered effect was **11.8%**. Do not read
the 30% as an effect. Its value is structural: it is the arm that isolates
`--grant-suppress`.

**S3 — two confounds refuted by measurement, not by argument.** Warps are
**under**-dispersed (Fano φ = 0.40 over 5 s bins, lower-tail p = 0.008; 0
adjacent-jump pairs in 325 P0 intervals against 2.07 expected), so
interval-level Fisher was conservative rather than optimistic. And the
plane-crossing explanation dies on the cleanest possible control: **A4 crossed
ZERO planes (153/153 reports on plane 0) and warped 12 times.**

**S4 — A3's motion was never superhuman.** Max interval speed **278.31 u/s**
over all 195 intervals, below the character's own 288 u/s run speed. Zero at
every speed bar down to 279 u/s.

### ⚠ WHAT IS WITHDRAWN, and this is most of the entry

**W1 — WITHDRAWN: "the composite removes the warp."** A3 emitted **0 of 96
grants capable of displacing the player** — every one named a point **≤ 0.7 u**
(p50 0.4 u) from where the client had just said it was. On the mechanism's own
denominator A3 contributes **zero trials**. The run cannot distinguish *the fix
works* from *no-op packets are no-ops*. **Restate as:** `--grant-suppress`
removed every displacing grant, and the residual zero-lead grants are incapable
of displacing the client by construction.

**W2 — WITHDRAWN: the attribution to the composite.** Replaying the SHIPPED
`_grant_verdict` against each arm's own recorded `keyboard_age` — positive
control passing, forcing the flag off reproduces every arm's fired count exactly
(145→145, 155→155, 94→94, and A3 on→0) — **bare `--grant-suppress` would have
left A1 with 1 grant of 145 and A4 with 0 of 94.** One already-shipped flag,
already priced by round 4 as a palliative, removes the grants that produced all
26 P0 warps. **L5 contains no contrast that separates the composite from
`--grant-suppress` alone.**

**W3 — WITHDRAWN: every `--plane-carry` claim.** The flag was demonstrably ON
and had **zero opportunity to act**: the client reported **plane 0 on every
single `0x003D`** in A2 (183/183), A3 (196/196) and A4 (153/153), and
`plane_differs` is **0 on all 180 and 192 zero-lead rows**. A single plane means
no plane can differ. **L5 carries no information about REALFIX-F1 whatsoever**,
and A2 is therefore a `--zero-lead` arm for every purpose.

**W4 — WITHDRAWN: p = 3.33e-06.** Correct arithmetic, wrong unit — it treats one
arm as 195 independent runs, and report intervals ~0.3 s apart are not
independent trials. ⚠ The published Poisson figure was separately wrong: it
mixed span variables (capture-row spans where the rate column used movesync
track spans).

**REPLACED BY a bin-level permutation, exact by enumeration, carrying its own
NULL CONTROL** — the same test run on two arms of the SAME condition must come
out non-significant, or it is measuring run-to-run variance rather than
treatment. One-sided, jumps binned per arm, bin labels permuted:

| comparison | 5 s | **10 s** | 15 s | verdict |
|---|---|---|---|---|
| P0 pooled vs **A3** composite | ~0 | **2.0e-04** | 4.8e-03 | significant |
| P0 pooled vs **L6** `--grant-suppress` alone | 5e-06 | **1.6e-04** | 2.2e-03 | significant, same size |
| P0 pooled vs **A2** `--zero-lead` | 0.133 | **0.258** | 0.226 | **NOT significant** |
| **L6 vs A3** | 0.186 | **0.154** | 0.119 | **NOT distinguishable** |
| *null control:* A1 vs A4 | 0.408 | **0.286** | 0.500 | ✓ passes |

**Publish the 10 s row, with the bin width attached** — the figure moves an order
of magnitude between 5 s and 15 s and is not quotable without it. An
independent arm-level random-effects model put the A3 contrast at **0.035**
(0.106 Bonferroni ×3); that is the more conservative reading and this entry does
not choose between them, because they answer different questions — the
permutation asks whether these bins differ, the random-effects model asks
whether ANOTHER P0 arm would have.

**And the row that matters most is L6 vs A3 at p = 0.12–0.19: the composite is
not distinguishable from the single shipped flag.** On the mechanism's own
denominator — displacing grants — the table is P0 26/239 against A3 **0/0**,
which is **p = 1**: no trials at all.

**W5 — WITHDRAWN: "fixed, not quiet."** Three separate defects. It is
**cross-metric**: `drift` is |client report − **server's** blended model|
(`authsrv.py`:2714, emitted :2798), self-reset on every accepted report
(A3 accepted 196/196), so it spans ~0.3 s; `separation` is |client report −
**the client's own SYNC block**|. It is **mis-attributed**: `FINDINGS`:3958's
4,402 u arm is `A --explorable (P0 control)`, a zero-grant default build, **not**
`--grant-suppress` — and no separation measurement of the palliative exists
anywhere in the vault. And **the instrument fails its own control**: pointed at
the known-parked arm, `drift` reads p50 **52.6 u**, *better* than A3's 66.7.
**Corrected wording:** A3 is not the L1 parked-copy failure — compared like with
like, each arm cut to its own first 10.85 s, A3 reads separation p50 **40.4 u**
where the zero-grant arm reads **6,229 u** in its first bucket. Limits: 17.7% of
A3, and the comparison arm is a default build rather than the palliative.

**W6 — WITHDRAWN: "96 grants vs 94, so it is not granting less."** Disjoint
populations. A3's click arm granted **0 of 178**. And the two arms are coupled,
not additive: `_grant_verdict` and `_heading_grant_ok` share one 0.5 s clock
(`state["grant_at"]` is stamped in `send()`/`_note_wire_move` at :3005 for
EVERY player `0x0029` whatever arm sent it; `GRANT_MIN_INTERVAL = 0.5` at
:3252), so A3's 96 zero-lead grants **exist because of** its 178 suppressions.

**W7 — a real cost, newly measured and not to be glossed.** A3 is the **worst**
arm at drift p50 (66.7 u against 31.0–41.8) and p90 (124.8 u), best at max
(175.1 u). The median regression is the treatment's own arithmetic: A3's client
step per interval is 33.6 u, identical to the others, but the **server's model
motion is 57.6 u/interval (≈192 u/s)** against A4's 14.5 — zero-lead re-anchors
`state["dest"]` to a stale point and the integrator chases it at run speed.
Against `ENEMY_DEST_RESEND = 120 u` that is 15.8% exceedance, worst of four; it
buys 0.0% above `INTERACT_RANGE = 250 u` (against 5.5–9.2%) and 0 trust-guard
firings (against 1/1 and 2/2).

### ★ THE FINDING THAT REFRAMES THE ARC: THERE ARE TWO MECHANISMS, NOT ONE

L3/L4 decoded the **plane echo** — field 4 stamping the client's plane onto a
lagged copy at a boundary — and demonstrated `--plane-carry` removing it. **That
mechanism has no exposure in this regime at all**, by the plane census above.

What produces the warps here is **grant DISTANCE**, and it needs no boundary:

| arm | granted destination's distance from the client | over the 299.33 u gate-1 cut |
|---|---|---|
| A1 | p50 1,644 u, max 5,025 u | **140 of 145 (97%)** |
| A2 | p50 1,446 u, max 4,827 u | 152 of 193 (79%) |
| A4 | p50 2,577 u, max 5,642 u | **94 of 94 (100%)** |
| A3 | 0.0 u — by construction, not by measurement | 0 |

The click arm grants a point the player clicked, 1,400–2,600 u away; the copy
cannot match it against its own history; gate 1 (299.332591 u, REALFIX-C0)
fires; the roster reseeds. A2's 79% is exactly its own composition — 38 of 193
grants were zero-lead, and the rest are click grants.

**Independently corroborated on round 4's own captures**, from the other side:
the client never left plane 0 in any round-4 arm and **field 4 was `0` on all
341 grants**, while every one of round 4's 13 hard rows is plane 0→0, follows a
click grant by **0.08–0.23 s**, and several land on the granted point to the
unit — `183311 t+19.64` reports `(10783, 5905)` against a grant of
`(10784, 5905)`.

**So `studies/movement`'s two regimes are two different failures wearing one
symptom, and a fix for one is not a fix for the other.** L3/L4's result stands
in its own regime and is untouched by this entry.

### Why `--zero-lead`'s arm is starved here, measured

`send()`/`_note_wire_move` stamps the ONE shared `grant_at` for every player
`0x0029` whatever arm sent it; `_heading_grant_ok` refuses below
`GRANT_MIN_INTERVAL = 0.5 s`; and the click arm has **no rate limit at all**
with `--grant-suppress` off (`_grant_verdict` short-circuits, :3305). Replaying
round 4's own streams through the imported predicate — positive control
reproducing FINDINGS' published counts first — the zero-lead arm would fire
**26 of 128** (`183311`) and **12 of 132** (`195137`) against 140 and 199 click
grants, but **56 of 112** once `--grant-suppress` silences the click storm.
Measured in the run itself: A2 fired 38 of 180, A3 **96 of 192**.

### An unmeasured geometry fact that explains the whole arc's failure to see a click-side plane rewrite

Probing our own navmesh across the bridge deck (`pathmap.PathingMap.load(0x1B97D)`,
58 planes / 6,120 trapezoids), `containing()` returns **`[0, 18]` — ambiguous —
through the entire middle of the deck**, and the click arm refuses unless our
geometry places the player on exactly one plane and that the one the client named
(`placed = here == {cur_plane}`, :11120). Only two narrow strips grant a click
with plane 18: **y 4560–4760 and y 5320–5560**. 38% of on-mesh probes are
ambiguous, and the ambiguity is exactly where a click-side plane rewrite would
have to happen. ⚠ **Very nearly none, and the exact figure is worth having: of 601 grants
attributable to the CLICK arm, field 4 is non-zero on 2 (0.3%) — against 108 of
704 (15.3%) on the zero-lead arm, which is F1's own territory.** (2,711 further
grants sit in pre-telemetry captures with no `grant_verdict` row to attribute them
by; 39 of those carry a non-zero field 4, so the click-arm figure is a FLOOR over
the attributable set, not a census of the arc.) An earlier draft of this sentence
said **never**, which was overstated by two. **The geometry above is why it is so
close to zero.**

---

## 2026-08-21 — ★ REALFIX-L6: bare `--grant-suppress` scores 7.6×, and round 4's UNEXPLAINED RESIDUE is finally explained

**OBSERVED, `ours`, wire-only** (no movetap). Capture `20260821T183331`, harness
report `vault/captures/harness/20260821T183254`, map 148, build 38797, same
operator, same trigger. **The arm L5 named as deciding and did not run.**

**484 clicks over 89.0 s → 2 grants → 3 hard jumps, 2.02/min**, against the L5
P0 pool's 15.43/min. **A 7.6× reduction**, reproducing round 4's 8.3× on an
independent run and settling W2 above from the other direction: the palliative
alone does most of the work.

### Why only two grants got through — the disarm window

Both fired with **`keyboard_age = None`**. Rule 1 is
`if age is not None and age <= GRANT_LOCAL_WINDOW` (:3316, the constant at
:3230), so the latch was not
STALE — it was **UNSET**, and rule 1 never evaluated. `kbd_moving_at` is armed
by the `0x003D` arm and cleared by the `0x0047` arm (:10401, :11297), and the
code's own comment already names the behaviour: *"THE PRIMARY DISARM of the
locally-driving latch… in the 5 ordinary clicks of `authsrv-20260820T182934-c1`
a 0x0047 had arrived before every single one, so rule 1 refused 0 of 5 there."*

Both grants landed **0.22 s and 0.41 s after a stop report**, and both carried
full lead: **1,758 u and 754 u**, each far over the 299.33 u cut.

**This is not a bug in rule 1. It is rule 1 working as documented** — the same
disarm that makes ordinary click-to-move work is what leaks during a spam-click
session whenever the client emits a move-cancel.

### Why two grants produced three warps — the destination LINGERS

| warp | jump | landed | from | **lag** |
|---|---|---|---|---|
| 1 | 1,095 u | **27.9 u** from grant 1's dest | keyboarding throughout (`movementType=4`) | **8.8 s** |
| 2 | 2,238 u | **114.2 u** from grant 1's dest | after a stop | **35.3 s** |
| 3 | 1,210 u | **0.0 u** from grant 2's dest | — | **6.9 s** |

**Grant 1 fired twice** — at +8.8 s and again at +35.3 s. Two of three landings
are inside the client's own `MATCH_RADIUS` = 99.919968 u.

**CONTROL, and the first version of it was contaminated**: a warp's landing is
itself reported by the client, so drawing "random" points from the raw track
lets the control pick the very point being fitted and score 0.0 u. Excluding
every report within ±2 s of a warp: 200 random track points give **best fit
189.0 u, p50 757 u, and 0 of 200 beat even the worst real grant fit (114.2 u).**

**During warp 1 the player was keyboarding continuously**, `movementType = 4` on
every report either side. The granted destination survived sustained local
movement and fired anyway.

**This is REALFIX-Q5's residue, with instances.** Round 4 measured 1.39 hard
rows/min from 2 grants and never explained it; `REALFIX.md`:289 lists
`0x005FCAA0`'s gate-free reseed as *"a candidate for the unexplained snaps 12–59 s
after the last grant"*. The signature now has a shape: **the granted destination
is not consumed, it lingers, and it re-applies seconds later.** Which site
re-applies it is still UNVERIFIED — that needs a movetap on `+0x48`, which this
run did not carry.

### ⚠ The A3-vs-L6 comparison is confounded by exposure, and the confound is measurable

| arm | stops | clicks | **clicks in a disarm window** | grants via that branch |
|---|---|---|---|---|
| A1 | 4 | 300 | 2 | 0 |
| A2 | 3 | 317 | **0** | 0 |
| A3 composite | 4 | 330 | **0** | 0 |
| A4 | 1 | 262 | **0** | 0 |
| **L6** | 7 | 484 | **9** | **2** |

**A3's zero on this path is untested exposure, not a demonstrated fix** — it
never met the branch once, exactly as L5's own limit 4 predicted. L6 met it nine
times.

**And `--zero-lead` does not touch the click arm**, so the same nine clicks under
A3's flags would have produced the same lead-carrying grants. **PREDICTION,
recorded before it is tested: the composite would NOT have prevented these three
warps.** ⚠ **CONTESTED the same day by a desk screen — see §"REALFIX-F4 REFUTED AT A DESK": under `--zero-lead`, 137 overwrite grants would have fired, the first 0.91–2.13 s after each click grant and 6.0–33.2 s before each warp. Whether the client HONOURS an overwrite is UNVERIFIED, so the prediction is neither confirmed nor withdrawn — it is now the thing the next run decides.**

### ★ AND IT SETTLES L5's OPEN QUESTION: THE COMPOSITE BOUGHT NOTHING MEASURABLE

Bin-permutation, same test and same null control as L5's W4: **L6 vs A3 gives
p = 0.186 / 0.154 / 0.119** at 5 / 10 / 15 s bins. **The composite
(`--zero-lead --plane-carry --grant-suppress`) is NOT distinguishable from
`--grant-suppress` alone**, while both separate from P0 at ~2e-04. Combined with
W2's predicate replay, the ruling is: **the single shipped flag does the work,
and the two extra flags add nothing to the warp count.** What they may still add
is the bounded server model (L5 W5/W7) — that is a different claim on a
different metric and is not established here.

### What this names for the next build

The lever is in the **click arm** and the constant is already measured: a grant
whose destination lies within `MATCH_RADIUS` of the client's last report cannot
reach gate 1. Both L6 grants carried 754 u and 1,758 u. Round 4 already priced
the cost of refusing outright — with every click refused *"the client pathed
itself to the clicked point anyway"*, cos 0.994–1.000, 5 of 5 — so the click
grant is not load-bearing for click-to-move. **Needs a minted identifier and its
own pre-registration before a line is written.**

## 2026-08-21, later — REALFIX-F4 REFUTED AT A DESK BEFORE IT WAS BUILT, and the desk work undermines my own L6 prediction

**No client run, no server code written.** Three offline screens over captures
already in the vault. This is the second candidate the desk has killed
(REALFIX-F1b was the first) and the pattern is now the arc's cheapest instrument.

### 1. REALFIX-F4 — bound the click grant's lead — is REFUTED

**The candidate**, minted here per `studies/idents/CONVENTION.md` (`F<n>` = fix
candidates; F1/F1b/F2a/F2b/F3 taken): refuse a click grant whose destination
lies further than a bound *B* from the client's own last reported position,
since a grant inside `MATCH_RADIUS` cannot fail the match test and reach gate 1.

**Its own refutation criterion, stated in the screen before it ran:** the bound
earns its place only if it refuses the warp-causing grants while NOT refusing
everything — otherwise it is `--grant-suppress` with extra steps.

**Screened over the whole `origin = ours` corpus** — 2,445 grants, 82 warps
attributable to a granted point within 150 u:

| bound | BENEFIT: warp-causing grants refused | COST: all grants refused |
|---|---|---|
| `MATCH_RADIUS` 99.92 u | 81 / 82 (**99%**) | 2,299 / 2,445 (**94%**) |
| `GATE1_CUT` 299.33 u | 77 / 82 (94%) | 2,129 / 2,445 (87%) |
| 520 u | 72 / 82 (88%) | 1,979 / 2,445 (81%) |
| 1,000 u | 29 / 82 (35%) | 1,102 / 2,445 (45%) |

**The curves track each other, and at the loosest bound the ratio inverts
(35% benefit at 45% cost — worse than indifferent).** There is no separation to
find, and the reason is structural: **a click grant is far BY DEFINITION** —
it names the point the player clicked. The population of "far grants" and the
population of "all click grants" are the same population. **F4 is refused. Do
not build it.**

**What this rules out generally:** any click-arm policy keyed on the grant's own
distance. The discriminator, if one exists, is not in the grant.

### 2. Reseed-onto-our-model is REFUTED, and two of L6's three warps are clean

The rival reading of L6's warps — gate 1 reseeds the whole roster onto the
authoritative copy, so the landing is wherever the SERVER believed the player
was, and its proximity to an old granted point is a coincidence of our own
integration. **Tested against `position_report.ours`, the server's own belief,
strictly before each warp:**

| warp | to the nearest GRANTED point | to OUR MODEL | to the client's OWN past track |
|---|---|---|---|
| 1 | **27.9 u** | 966.6 u | 591.1 u |
| 2 | 114.2 u | **2,224.9 u** | **105.2 u** |
| 3 | **0.0 u** | 1,324.6 u | 422.7 u |

**Reseed-onto-our-model is dead** — warp 2 sits 2,225 u from our model. **Warps
1 and 3 are unambiguously the granted destination**, held **8.82 s** and
**6.88 s** and then applied.

⚠ **Warp 2 is UNRESOLVABLE and is withdrawn as evidence for anything**: 114.2 u
to grant 1's destination against 105.2 u to a position the client itself held
26.2 s earlier. At n = 1 that difference cannot be called. **In particular it
must NOT be read as showing that grants QUEUE rather than replace** — that was
this session's first reading of it (grant 2 was already sent when warp 2 fired
on grant 1's point) and the own-past column takes it away.

### 3. ⚠ MY OWN L6 PREDICTION IS UNDERMINED — the overwrite arrives in time

L6 recorded: *"the composite would NOT have prevented these three warps"*,
reasoning that `--zero-lead` does not touch the click arm so the same
lead-carrying grant goes out. **That is true about the GRANT and ignores what
happens 0.5 s later.**

Replaying L6's real report stream through the SHIPPED `_heading_grant_ok`, with
L6's real click grants stamping the shared clock: **137 zero-lead grants would
have fired**, each naming the client's own position. Per warp:

| warp | its grant | overwrites available before it | first one lands |
|---|---|---|---|
| 1 | t+37.06 | **11** | 2.13 s after the grant, **6.69 s before** the warp |
| 2 | t+37.06 | **53** | 2.13 s after the grant, **33.22 s before** the warp |
| 3 | t+71.49 | **10** | 0.91 s after the grant, **5.97 s before** the warp |

**Every warp had an overwrite available, with seconds to spare.**

⚠ **This is NOT a demonstration that the composite works.** It shows the
overwrite would be **sent** in time; it does not show the client **honours** it.
Whether a second `AGENT_MOVE_TO_POINT` clears a pending destination or is held
behind it is **UNVERIFIED** — nothing here reads `+0x48`, and §2's warp 2 can no
longer be used to argue either way. **The prediction is downgraded from
"recorded before it is tested" to CONTESTED, and the run below decides it.**

### What to run, and why it is now cheap

**`--zero-lead --grant-suppress`, in a regime that DELIBERATELY produces
cold-latch clicks.** L6 taught the recipe: rule 1 disarms on a `0x0047` stop, so
**release the movement key for ~0.5 s, click somewhere far, then resume
keyboarding.** L6 produced 9 such windows by accident in 484 clicks; a protocol
aimed at them produces dozens.

**The two outcomes are both informative and they are opposite:** warps → 0 means
the overwrite is honoured and the composite closes the residue `--grant-suppress`
leaves; warps at L6's ~2/min means the destination survives an overwrite, which
sends the arc to the client-side question — which of the 13 SetPosition sites
re-applies a destination seconds later (REALFIX-Q5) — and needs a movetap on
`+0x48`, which L6 did not carry. **Carry one this time.**

**The control is already banked**: L6 itself, `--grant-suppress` alone, 3 warps
in 89 s at 2.02/min, same operator, same map, same day.

## 2026-08-21 — ★ REALFIX-L7: the cold-latch branch reproduced ON PURPOSE, the palliative's parked copy finally MEASURED, and the overwrite hypothesis is still untested

**OBSERVED, `ours`.** Two arms, map 148, build 38797, owner-driven under a
**deliberate cold-latch protocol** — walk, release the key ~1 s, click far,
resume — designed from L6's diagnosis to produce the branch that leaks past
`--grant-suppress`. Control `20260821T210131`, treatment `20260821T210620`.
**Both movetaps ran the full 199.9 s at 12.0 and 13.3 Hz** — against 8.4–9.5 in
every earlier run and 12.5 s of coverage in L5's A3 — so for the first time in
this regime **REALFIX-E on the rendered copy is admissible and carries the
verdict**, which matters because the protocol's standing-still leaves the
control's wire only **17% actively reported**.

| | **control `--grant-suppress`** | **treatment `+ --zero-lead`** |
|---|---|---|
| **REALFIX-E events** | **1** | **0** |
| max rendered step | **3,437.3 u** | **52.1 u** |
| grants | 1 | 116 |
| stops (`0x0047`) | 41 | 44 |
| clicks | 25 | 33 |
| clicks on a cold latch | 1 | 4 |
| **cold-latch grants that ESCAPED** | **1** | **0** |
| **separation p50 / p90 / max** | **1,970 / 3,914 / 4,718 u** | **369 / 514 / 2,034 u** |
| samples above the gate-1 cut | 93% | 67% |

`--plane-carry` was correctly **excluded** this run (`plane_carry = false` on all
116 zero-lead rows), so the treatment is cleanly `--zero-lead --grant-suppress`. ⚠ **And the scorer said otherwise for a while.** The behavioural arm-identifier printed "COMPOSITE `--zero-lead --plane-carry` `--grant-suppress`" from a HARDCODED label string whenever the zero-lead and suppress vocabularies both appeared — it never read `plane_carry`, which the capture records on every verdict row. That is the exact hazard L5's review named ("`--plane-carry` vs `--arrival-carry` indistinguishable; the `carry` field separates them and is not read"), and it is the `vaultpath.require_dir()` principle in another costume: **a fixture that names a thing without reading it turns every claim behind it into a no-op.** Fixed to read the field and to PRINT what it read, so the label can be audited rather than trusted.

### 0. Instrument note — the tap's sample rate is ONE SYSCALL, and it is fixable

Three runs have now recorded a movetap rate (8.4–9.5 Hz, then 12.0–13.3 Hz) as a
bare fact with no cause, and "positives valid, nulls void" has been paid twice
because of it. **Measured 2026-08-22: `_threads_of()` costs 51.7 ms per call on
this machine** (n=20, warm; an independent lane on the same tree measured
39.7–57.7 ms, so it is load-dependent — quote the range) — **which caps the tap
at 19.3 Hz on that call alone**, before a single `ReadProcessMemory`.

The cause is at `movetap.py:514`: `CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,
0)` takes a **system-wide** thread snapshot and the owner filter is then applied
in Python at `:519`. Passing our own pid would not help — `TH32CS_SNAPTHREAD`
ignores `th32ProcessID` by design — so **the fix is to CACHE the thread list**,
which changes rarely for a running client, rather than to re-snapshot per sample.
The `ctypes.WinDLL("kernel32")` construction inside the same function is only
0.013 ms and is not worth touching.

**Nothing here has been changed** — this is a measurement and a costing, not a
patch, and `movetap.py` is a pinned instrument whose edit needs its own test
floor. But the next arc that needs 20 Hz should know the ceiling is one cached
list away, not a rewrite. OBSERVED, `toolkit/clientscan/movetap.py:500-524`.

### 1. The protocol worked, and the conversion is now 3 for 3

The control's single event is **3,437.3 u**, and its next largest rendered step
is **42.9 u** — one discontinuity, nothing marginal. Anchored on REALFIX-T1 at a
**0.218 ms** clock residual, it lands **0.0 u from the granted destination,
10.1 s after the grant**, and the grant fired with **`keyboard_age = None`** —
the cold-latch branch, produced deliberately rather than stumbled into.

**Across L6 and L7 the cold-latch conversion is 3 of 3 clean instances**
(L6 warps 1 and 3 at 27.9 u / 8.82 s and 0.0 u / 6.88 s; L7 at 0.0 u / 10.1 s).
**A grant that escapes rule 1 lands the player on its destination 6.9–10.1 s
later.** That is a reproducible, prospectively-triggered defect.

**And it reconciles L6's ambiguous warp 2.** At the event, separation collapses
**3,418.97 → 0.0 u** while the landing sits 0.0 u from the granted point: the
SYNC copy had *walked to* the granted destination over those 10 s, and the
rendered character was reseeded **onto the copy**. Landing-on-the-grant and
landing-on-our-model are not rival readings — they are the same point, because
the copy integrates toward what we granted. L6's warp 2 was ambiguous for
exactly this reason and stays withdrawn.

### 2. ★ THE PALLIATIVE'S PARKED COPY, MEASURED — and it supplies what L5's W5 said did not exist

L5 withdrew "fixed, not quiet" partly because *"no separation measurement of the
palliative exists anywhere in the vault."* **It exists now, on the same metric,
same instrument, same run, same operator, both arms:**

**bare `--grant-suppress` parks the authoritative copy at p50 1,970 u
(p90 3,914, max 4,718). Adding `--zero-lead` pulls it to p50 369 u — 5.3× —
while events go 1 → 0.**

This is the L1 quantity (SYNC copy against the client's own report — what aggro,
interact range and `clip_to_walkable` actually read), so it is comparable to
L1's 4,402 u parked default, and it is **not** the cross-metric `drift`
comparison W5 struck. **The composite's claim is no longer "fewer warps" — which
this run cannot power — it is "the same silence without the parked copy", and
that contrast is large and well sampled (2,406 and 2,661 samples).**

**A second cost of parking, newly visible: the parked copy sets the warp's
SIZE.** The control's event magnitude (3,437 u) is its separation (3,419 u).
`--grant-suppress` trades warp frequency for warp magnitude, because the copy
drifts further before the reseed lands on it.

### 3. ⚠ THE RUN DID NOT TEST WHAT IT WAS BUILT TO TEST

**The overwrite hypothesis remains UNTESTED, and this is the second run in a row
to fail on exposure rather than on effect.** The treatment let **no** cold-latch
grant out at all, so no lingering destination ever existed for an overwrite to
race. The warp contrast is **1 against 0** — n = 1 per arm, statistically
nothing, and the composite's zero is again *untested exposure* rather than a
demonstrated save.

**What DID appear is a different protective mechanism, caught once in the act.**
At **t+211.41** a click landed on a cold latch, passed rule 1 — and was refused
`rate-limited` by **rule 2**, because a zero-lead grant had stamped the shared
`grant_at` **0.40 s earlier** (`t+211.015`). **`--zero-lead` protects by
PREEMPTING the click grant on the shared clock, not by overwriting a destination
after the fact.** The other three cold-latch clicks were refused upstream by the
geometry/staleness gates and never reached a verdict.

**Preemption is arguably the better mechanism** — it stops the packet at source
rather than racing it — but **n = 1**, and it is not what was pre-registered.
**My L6 prediction stays CONTESTED**: nothing here shows whether the client
honours an overwrite, because no overwrite ever had a target.

### 4. What the next run must do differently

The exposure problem is now the binding constraint two runs running, and its
cause is measurable: **of 58 clicks across both arms, only 5 landed on a cold
latch and only 1 escaped**. The deliberate protocol produced plenty of stops
(41 and 44) but too few clicks, and most clicks died upstream in the click arm's
geometry gates ("not a straight shot", "cannot place them").

**To test the overwrite specifically, the click must be allowed OUT and the
overwrite must be the only thing standing between it and the warp.** That means
an arm where rule 2 cannot preempt it — i.e. the shared clock must be free at
the moment of the click. **Neither this run nor L5 can be re-analysed into that;
it needs a build change or a protocol that clicks immediately after a heading
grant's floor expires, and it should be priced before it is run.**

## 2026-08-22 — ★⚠ REALFIX-L8: the exposure protocol WORKS (32 cold-latch escapes in the control), the treatment's ABORT CONDITION FIRED — and the OTHER mechanism wedged the operator inside the bridge

**OBSERVED, `ours`.** Two arms, map 148, build 38797 (each movetap head records
the exe: `vault/run/2026-07-29_221c13772c7a/Gw.exe`), owner-driven under the L8
protocol (`REALFIX.md` §"REALFIX-L8": turn while moving, release out of a turn,
click immediately, 3–4 rapid clicks 400–800 u along open ground, resume).
Control `20260822T161838` + `movetap-20260822T161918` (2,443 samples, 254.1 s,
9.6 Hz); treatment `20260822T162502` + `movetap-20260822T162513` (396 samples,
41.6 s, 9.5 Hz). **Arm labels are earned, not assumed**: the control carries
`locally-moving` rows (reachable only with `GRANT_SUPPRESS` on) and zero
zero-lead rows; the treatment carries 86 `arm = "zero-lead"` rows with
`plane_carry = false` and `carry = "off"` on every one — cleanly
`--zero-lead --grant-suppress`, no `--plane-carry`, as L7's design requires.
Two same-day captures (`160333`, `160626`, 75 s each) carry no verdict rows and
no tap: setup, excluded. **Both taps pass the REALFIX-E artifact gate**
(`async_ptr`/`async_id`/`async_count`/`async_world` single-valued) and **neither
tap has a single adjacent pair over 0.25 s**, so every pair is inside the E
definition's interval bound; the control tap covers 254.1 s of a 297.3 s
capture span, so its event count is a FLOOR.

**New verdict vocabulary, for the next session that fingerprints arms.** The
shipped click arm now HOLDS a rate-limited click instead of dropping it
(`grant_flush_tick`, `authsrv.py` — "the coalescing half of rule 2": newest
click wins, fired when the floor opens, dropped if the keyboard resumes or the
hold expires). Its rows are `deferred-grant` (fired) and `pending-expired`
(dropped); the zero-lead arm's refusal is `heading-rate`. None of these appear
in L5's fingerprint recipe, which should be read with this addendum.

### The control: the exposure problem that voided two runs is solved

344 clicks, 55 stops, 687 headings over 297.3 s. Upstream of the verdict (server
stdout, harness report `20260822T161814`): 148 × "not a straight shot", 60 ×
"cannot place them", 70 held by the floor, 8 deferred clicks dropped on keyboard
resume. At the verdict: **32 × `grant` — every single one with
`keyboard_age = None`, i.e. 32 escaping cold-latch grants** (pre-registered
prediction: ≥ 8; L7 managed 1) — plus **16 × `deferred-grant`** (keyboard_age
not recorded at fire time; counted beside, never pooled), 24 `locally-moving`,
70 `rate-limited`. Every fired grant carried full lead: cold-latch p50
**1,994 u** (626–4,151), deferred p50 2,495 u (1,303–4,098), **48 of 48 over the
299.33 u gate-1 cut**.

**REALFIX-E: 16 events** (steps 310–5,439 u; largest non-event step 52.6 u).
The pre-registered band was 5–15: **measured 16, one above the top** — the band
was drawn from L6+L7's 3-of-3 parked-copy conversion, and that model did not
generalise to spam cadence (below). Wire bar beside it, per the registration
(`movesync --wire-only`): 12 hard rows, 3.07/min of span, 3.80/min of active
time (1.042 s threshold named), magnitude p50 1,139 u max 5,236 u, grant age at
the jump p50 0.93 s max 10.34 s, landing on the granted path 4/5 non-degenerate,
2 of 12 straddling a plane flip. Separation (tap): p50 515 / p90 2,661 / max
5,472 u, 66% of samples over the cut.

**The conversion model needs restating.** All 16 events are reseeds onto the
SYNC copy — every landing sits 0–27 u from the contemporaneous `sync_at` — but
only **6 of 16 land ≤ 33 u from a fired grant's destination** (two at exactly
0.0 u: the copy had walked to the click and parked — L6/L7's signature). The
other **10 land 116–434 u from any destination: the snap fired mid-glide**, at
one of the next grants' bakes, wherever the copy happened to be. L6/L7's
"destination lingers 7–10 s, then fires" is the PARKED tail of the
distribution, not the rule; at spam cadence 48 fired grants → 16 events (≈ 1:3,
not 1:1).

### The treatment: the abort condition fired — for a NEW reason

44 clicks, 6 stops, 86 headings, 53.5 s span, ended early with the operator
wedged inside the bridge abutment (operator report with screenshot; the wire
agrees — from t+34.8 to t+39.4 the client reported the same position while the
zero-lead arm granted it straight back: **six identical fired destinations at
(10788, 5596) plane 18**, the wire signature of walking-in-place against
collision). Zero-lead: 37 fired, 49 `heading-rate` refused. Click arm: **zero
verdict rows — 0 fired, 0 escaping cold-latch grants.** Upstream: 25 × "not a
straight shot", 16 × "cannot place them — geometry says off-mesh".

**Fewer than 3 escaping grants in the treatment is the pre-registered abort
condition, and it fired: this is the third consecutive exposure failure, the
run answers nothing about the overwrite, and it is NOT scored as a null.** The
overwrite hypothesis (L6/F4 desk screen) remains UNTESTED. But the cause is
not L7's: no click was preempted by rule 2 (none ever reached it), and no click
was mistimed. The arm was derailed in its first half-minute by the arc's OTHER
mechanism, and everything after that is the derailment's shadow — the operator
was off-mesh inside the bridge, so the geometry gates correctly refused every
click from there.

### ★ The plane echo, caught mid-act at 9.5 Hz

The treatment's single REALFIX-E event is the cleanest per-sample record of
mechanism A (L3/L4's plane echo) the arc has:

| world clock | `async_at` (rendered) | `sync_at` (copy) | sep | fence |
|---|---|---|---|---|
| 30.808 | (10846.6, 5617.9) **pl0** | (10556.0, 5751.2) pl0 | 319.7 | 1 |
| 30.908 | (10855.6, 5591.8) pl0 | (10583.1, 5741.5) pl0 | 310.9 | 1 |
| 31.009 | (10862.3, 5564.5) **pl18** | (10610.5, 5731.8) pl0 | 302.3 | 1 |
| 31.110 | (10869.6, 5533.1) pl18 | (10637.9, 5722.0) pl0 | 299.0 | 1 |
| **31.210** | **(10676.9, 5694.6) pl18** | **(10662.2, 5707.6) pl18** | **19.6** | **0** |

The client walks south onto the deck and its reports flip to plane 18
(31.009); the zero-lead grants follow suit — plane-word census over the 37
fired: (0,0) × 23, **(18,18) × 14** — and a grant stamps 18 onto a copy
standing ~300 u behind at **(10662, 5707), a point our mesh places on plane 0
and ONLY plane 0** (`pathmap.containing`, map file `0x1B97D`). In one 100 ms
window the copy's plane flips 0→18, the fence clears 1→0 (`clear_record` on the
snap path), and the rendered player is yanked **251.5 u backward onto the
copy**. Both copies then glide together, plane 18, over plane-0-only ground —
the operator's "floating run" — until the client wedges inside the abutment.
`--plane-carry` was OFF; this is precisely the event class L3/L4 demonstrated
F1 removing, occurring unstaged in the click-regime's own arena.

**Which gate fired is UNDECIDABLE from this tap, and the entry does not pick.**
The last pre-snap sep reads 299.0 u against the 299.332591 u cut, falling
~3 u per 100 ms — but the tap dead-reckons both copies on a 50 ms-quantised
world clock (~±14 u per copy at run speed), so gate 1 (marginally) and gate 2
(the copy's (x, y, plane-18) start unresolvable where plane 18 has no geometry)
are both live. If gate 2, it would be its **first observed firing** (n = 0 to
date) — do not claim it. REALFIX-Q1's ride-along breakpoint
(`0x0060580D`/`0x00605820`, `rec.clientControlled` beside separation) is still
the decider and is still unrun — **four rounds now**.

**This is NOT the invariant falsifier.** `REALFIX.md`:238 requires a P2-arm
snap with the copy behind the player *on ground already walked*. The ground was
walked **at plane 0**, and our own grant had just rewritten the copy's plane
word to 18 — the walkable term had a legitimate reason to fail. The invariant
stands; what fired is the known poison in field 4.

**The wire cannot see this event.** `movesync --wire-only` scores the treatment
**0 hard rows on both arms of the bar** — the client's post-snap report step
was ~102 u. REALFIX-E on the rendered copy was the only instrument that could
carry this verdict, which is what the L8 registration chose it for.

### The floating runs are the plane echo's rendered signature — both arms

The operator's report ("floating, height interpolated straight from A to B",
in the first run too) is located: a reseed that lands the rendered agent
carrying a plane word with **no geometry at its coordinates** leaves the client
resolving height against the wrong (or no) surface. Checked against our own
mesh, per landing: the treatment's event (plane 18 at a plane-0-only point) and
**three control landings** — t=69.685 (10814.5, 4430.7) **pl18**, south-west of
the deck footprint, mesh finds NO plane; t=154.315 (10684.9, 1345.2) **pl22**,
mesh finds none; t=196.109 (9906.8, 578.1) pl0, mesh finds none. The other 13
control landings are plane-consistent. ⚠ The referee here is our own
`pathmap` (measured 189/198 on plane membership, ambiguous exactly at
bridges), so per-landing verdicts are our mesh's word, not the client's.

### What this changes

1. **The L8 choreography is proven and keeps.** 32 escapes against L7's 1,
   from the same build — the protocol changes (click-on-release, rapid
   multi-click, moderate open-ground leads, turning cadence) did exactly what
   they were priced to do. 148 "not a straight shot" refusals and 48 grants
   still escaped: placement volume beats placement perfection.
2. **The overwrite question still has zero exposure after three runs.** The
   pre-registered remedy — price a click-arm exemption from rule 2 — stands,
   but L8 adds a second requirement discovered the hard way: **any L9 must be
   staged OUT of the plane-ambiguous bridge area** (the open plane-0 field at
   x 10700–12300, y ~2700–4300, `REALFIX.md` §L2's own site list — no plane
   boundaries, clear straight runs), and its treatment arm must pre-register a
   decision on `--plane-carry`: without it mechanism A can derail the arm in
   half a minute (measured here); with it the arm carries one more variable.
   That is a pre-registration decision, not a default to assume.
3. **The two mechanisms are now both visible in a single run pair.** Control:
   grant DISTANCE (48 full-lead click grants → 16 reseeds, no plane boundary
   needed — 13 of 16 landings plane-consistent). Treatment: the plane word
   (zero click grants, one reseed, plane rewrite onto off-plane ground).
   A fix ladder that addresses one and not the other will keep scoring
   "mystery" residue from the other; L5's two-regime framing is re-confirmed
   from inside one session.

## 2026-08-22 — ★★ REALFIX-L9: EXPOSURE ACHIEVED AT LAST, AND THE COMPOSITE'S PROTECTION IS DEMONSTRATED — 33 full-lead click grants escaped under `--zero-lead --grant-suppress` and NOT ONE became a warp

**OBSERVED, `ours`.** Two arms, map 148, build 38797, owner-driven under the
pre-registered L9 protocol (`REALFIX.md` §"REALFIX-L9", committed before the
run at `8e160b7`). Control `20260822T165425` + `movetap-20260822T165434`
(1,207 samples, 124.1 s, 9.7 Hz); treatment `20260822T165910` +
`movetap-20260822T165918` (1,133 samples, 134.0 s, 8.5 Hz — 93% of the
capture span, over the registration's 90% null-license floor). Arms earned
from the verdict vocabulary: the control carries `locally-moving` and zero
zero-lead rows; the treatment carries 141 fired `arm = "zero-lead"` rows, all
plane words (0, 0), `--plane-carry` correctly absent. Both taps pass the
artifact gate; **neither has a single adjacent pair over 0.25 s**.

**One protocol deviation, recorded with its purpose met.** Both arms were
played in the spawn-north field (track spans y ≈ 6,000–10,400), not the
registered arena south of the bridge. The arena rule's purpose — one plane, no
boundary — held completely: **every client report (306 and 356), every tap
sample (1,207 and 1,133) and every zero-lead plane word (141) is plane 0**, so
the mechanism-A contamination guard passes and the invariant-falsifier
sharpness (one plane, no plane-word excuse available) holds. Four clicks were
aimed AT the bridge aprons (dests y 5,300–5,800); the player never followed
them and no copy reached them.

### The control: gate passed, conversion measured again

11 escaping cold-latch grants (staging gate ≥ 8 ✓) + 16 `deferred-grant`
fires = 27 full-lead click grants, leads p50 1,290 / 1,385 u, **27/27 over the
299.33 u cut** → **7 REALFIX-E events** (555–3,575 u; largest non-event step
38.3 u), i.e. **0.26 events per fired grant**, inside the registered
0.15–0.5. Every event is a fence-clearing reseed onto the copy (landing
0–27.9 u from `sync_at`; three land exactly 0 u from a clicked destination —
the parked-copy tail, four land 22–602 u away — mid-glide, reproducing L8's
finding). Wire beside it: 6 hard rows, 3.08/min of span, magnitude p50
1,067 u max 2,821 u. Separation p50 621 / p90 1,669 / max 3,555 u. ⚠ The
registered secondary "control separation p50 ≥ 1,000 u" **missed** (621): a
27-grant control keeps the copy moving far more than L7's single-grant
control, which is what the 1,970 u figure came from. Printed, not a verdict
axis, and the miss is the prediction's error, not the instrument's.

### ★★ The treatment: the decision cell, reached on the fourth attempt, and it is the PROTECTED cell

**Exposure first, because three runs died on it: 8 escaping cold-latch grants
(abort < 3 NOT triggered) plus 25 `deferred-grant` fires — 33 full-lead click
grants launched during cold windows**, leads p50 1,539 / 1,676 u (784–2,821),
**33/33 over the gate-1 cut**. The spread-clicks refinement did the work
through the click arm's own deferral channel: a rate-limited cold click is
HELD by `grant_flush_tick` and fired ~0.3–0.5 s later with the latch still
unset — **the deferral is L7's feared rule-2 preemption converted from a
suppressor into a ~0.5 s delay**, which is precisely why no REALFIX-I2 build
change was needed. (34 `rate-limited` rows show rule 2 still working between
those fires.)

**REALFIX-E events: 0.** Largest rendered step in 1,133 samples: **51.0 u**.
Wire agrees: **0 hard rows on both arms of the bar, from 174 player grants**.

**Against the registration's own arithmetic:** the pre-registered binomial at
the conservative per-escape conversion (p = 1/3) gives **P(0 | 8 escapes) =
(2/3)⁸ = 0.039** — the registration pre-stated that a zero under 10 escapes is
suggestive rather than decisive, and this is that case, printed as promised.
On the registered per-fired-grant axis the contrast is stronger: control
**7 of 27** fired grants converted, treatment **0 of 33** — Fisher exact
one-sided **p = 0.0023**; at the control's own conversion the treatment
expected **8.6 events** and produced none. Same operator, same day, minutes
apart, and the contrast is on the mechanism's own denominator (per fired
grant), which is insensitive to the run-level rate confounds L5 warned about.

### The mechanism, and the data distinguishes more than the pooled cell asked

The registered PROTECTED cell pooled "overwrite honoured" with "any in-band
mechanism". The tap separates them:

- **The overwrite is honoured mid-flight.** Every cold escape was followed by
  its first zero-lead overwrite **1.18–3.02 s** later (9–115 more each).
  Separation never exceeded **954 u** against click leads of 1,500–2,800 u —
  the copy launched toward the clicked point and was pulled back before
  arriving. Closest approach of the copy to each clicked destination: p50
  **216 u** in the treatment against p50 **37 u (min 0.0)** in the control,
  whose copies walk all the way and park — that parked state is where the
  control's exact-landing warps come from, and the treatment never enters it.
- **The zero-lead invariant is observed protecting, per sample.** 92 of 1,133
  treatment samples sat ABOVE the gate-1 cut while zero-lead bakes ran the
  desync test continuously — and nothing snapped, because the copy chases the
  player's own reported track and therefore sits on the history polyline the
  match test consults. Lag on the polyline, exactly as REALFIX-O1 argued.
- **L6's lingering-destination residue did not manifest under overwrites**: 33
  lingering candidates, 40+ s of watched window each, 0 events — against
  L6/L7's measured 5–35 s re-application under bare `--grant-suppress` (3-of-3
  conversion there). Whatever re-applies a stale destination, a fresher
  destination defuses it.

### What this settles, and what it does not

1. **The composite's zero is no longer untested exposure — it is a
   demonstrated save.** L5's W1 withdrawal ("the run cannot distinguish *the
   fix works* from *no-op packets are no-ops*") is answered on its own terms:
   33 displacement-capable grants entered the mechanism and none displaced the
   player. The missing contrast from L5/L6 ("the composite is not
   distinguishable from `--grant-suppress` alone") now exists on the
   mechanism's denominator: bare suppress converts escapes at 0.26/grant
   (this run) and 3-of-3 (L6/L7); the composite converts **0/33**.
2. **The residue `--grant-suppress` leaves (L6: 2.02/min) is closed by
   `--zero-lead` in this regime**, and the parked-copy cost (L7 §2) is already
   measured as improved 5.3×. The click-regime lever the arc went looking for
   after L5 turns out to be the composite it already had — what was missing
   for three runs was only the exposure to prove it.
3. **Not settled:** which client mechanism honours the re-aim (the bake
   rewrites the destination on every `0x0029`; whether `+0x48`/arrival
   machinery still holds a stale copy in some path is REALFIX-Q5's question,
   now with 0 observed firings under overwrite pressure); which gate fires
   when protection fails (REALFIX-Q1, breakpoint still unrun — five rounds);
   and the non-movement costs of the composite (aggro/interact against the
   moving copy) which no run has priced. The escape-arm binomial at 0.039 is
   the registered headline number and it is suggestive-plus, not
   overwhelming — a replication arm run to ~15 escapes would put it beyond
   argument if one is ever wanted cheaply.

## 2026-08-22, later — the composite PRICED on L9's own captures, and REALFIX-Q5's gate-free reseed is ATTRIBUTED

**No client run.** Two desk passes over data already in the vault plus a static
walk of the pristine 38797 image. Both feed the ship-the-default decision.

### 1. The composite's server-side cost, measured where the decision needs it

OBSERVED, `ours`, from L9's own captures plus L8's control as a third point
(`position_report` rows; drift = |client report − server blended model|,
self-reset per accepted report):

| arm | drift p50 / p90 / max | model step p50 / interval | reports rejected | player `0x0029`/min |
|---|---|---|---|---|
| L9 control `--grant-suppress` | 9.8 / 30.8 / **2,649 u** | 74.0 u | 4 | 12.1 |
| **L9 composite** | **11.1 / 30.7 / 853 u** | 76.6 u | **0** | **72.5** |
| L8 control `--grant-suppress` | 12.6 / 33.2 / **5,260 u** | 72.9 u | 7 | 9.7 |

**In the normal-play regime the composite costs nothing measurable on the
server model**: drift and model motion are statistically identical (the
controls' 2,600–5,260 u drift maxima ARE the warp episodes — the composite has
none), and it is the only arm with zero rejected reports. The real cost is
wire volume — 174 player `0x0029` in 143.9 s ≈ **72/min — which is HALF of
retail's own cadence** (retail: 88.5% of 2,855 live player grants answer a
`0x003D` at median gap 0.492 s ≈ 122/min). ⚠ **This does not erase L5's W7**
(drift p50 66.7 u, model chasing at 192 u/s): those numbers belong to the
hold-S-and-spam-click posture, where the copy chases hard; the figures above
are the click-and-keyboard posture L9 ran. Regime-dependence, stated, both
kept. Unpriced still: enemies present (every warp run used `--no-enemy` or the
town), where the moving copy meets aggro — expected small (the server model
these consumers read is measured identical), unmeasured.

### 2. REALFIX-Q5 — the gate-free reseed is fired from LOCAL INPUT and GM tooling, not the receive path

Static, pristine 38797, `codescan --xrefs` with the registered positive
control passing first (`0x00605FC0` → its three known callers, exactly).

- **`0x005FCAA0` — the gate-free snap route, THE candidate for no-message
  snaps — has exactly 3 direct callers, and none is a message handler:**
  `0x004E6E82` sits in a **GmView.cpp** function whose own asserts include
  `MissionCliIsGameMaster()` (GmView:2874) — GM tooling, unreachable in
  normal play; `0x00816499` and `0x0081655D` are two call sites inside one
  **ChCliApi.cpp** function asserting `(rotation >= -1.0f) && (rotation <=
  1.0f)` (ChCliApi:5562), `hotKey < CHAR_SKILL_HOTKEYS` (:5613) and
  `character == context->playerControlledChar` (:5692) — **the local player's
  own input API**. Caveat, per the registration: `--xrefs` sees direct
  branches and stored VAs only; an indirect route stays possible and unfound.
- The four never-examined sites are mid-function addresses (0 direct refs to
  the address itself, as expected of call sites) and attribute by module:
  `0x00604A50` → **AgTrack.cpp** (history machinery); `0x00606394` → the
  **AgUpdate.cpp**/CtlLayout boundary region; `0x005FF74B` → **AgAgent.cpp**'s
  position/dead-reckoning region (window carries AgAgent:974/:978, the
  `m_point`/`m_timeStopMovement` asserts); `0x006028FF` → **AgAgent.cpp**'s
  message-application region (window carries AgAgent:2369/:2438
  `INTERNAL_FLAG_IN_WORLD`, beside the `0x0029` writer `0x00602A40`).
  Function-entry recovery for these four is NOT done — and after L9 their
  urgency is gone: the residue they were suspected of producing (L6's
  lingering-destination warps) did not manifest under the composite (33
  candidates, 0 events).

**What Q5 now says:** under bare `--grant-suppress`, the unexplained snaps
have one attributed no-message route (local input / GM through `0x005FCAA0`)
and one message-timed route (arrival-class instants, already in `grantsim`'s
model). Which of them fired in L6 remains runtime work — REALFIX-Q1's
breakpoint, still the arc's one unrun instrument. Under the composite the
question is moot on the evidence: zero residue firings in every composite run.

## 2026-08-22, evening — THE DEFAULT FLIP SHIPPED (PLAN §7 Q9), and the pipe lesson that came with it

**Owner's ruling, same day as REALFIX-L9: `--zero-lead --grant-suppress
--plane-carry` are the shipped default**, with `--no-zero-lead` /
`--no-grant-suppress` / `--no-plane-carry` kept for A/B work. Implementation in
`authsrv.py`'s `main()` only — the module globals still default False, so
nothing that imports the module sees a change; argparse resolves three-state
flags (absent = ON, `--no-*` = off, `--plane-carry` follows `--zero-lead` so
opting out of the policy does not strand the modifier), and the refuted-arm
refusals (`--heading-grant` etc.) now append a hint naming `--no-zero-lead`.

**The one defect the flip surfaced was not in the policy.** With all three
banners printing by default, server startup emitted **9,751 bytes** before the
listening line — past the pipe buffer of any consumer that spawns the server
over an undrained `subprocess.PIPE` — and `test_handshake` wedged mid-handshake
(server blocked in `print()`, recv timed out) within the hour. Fixed at the
source: **the full pre-registration banners print only when a flag is passed
EXPLICITLY**; the default path prints one line per flag (startup now 2,165
bytes). The banners' evidential strings still reach `print()` calls inside
their blocks, so `test_position_trust`'s §14/§15 source pins hold — its three
banner-block anchors were taught the resolved-local shape (`if zero_lead:` as
Name, not `a.zero_lead` as Attribute; the module-walking one scoped to
`main()`, because `zero_lead_composition` now holds bare-name tests that would
shadow it).

**Test state after the flip:** `test_position_trust` 216 green ·
`test_grantsim` 86 · `test_grantsuppress` 85 · `test_srclint` 22 ·
`test_handshake` red on ONE pre-existing check — the vault's newest patched
client reads **build 38849** against a 2026-08-20 key file — byte-identical
red on `main` before the flip, i.e. a peer session's in-flight new-build work,
not this change (the parallel-sessions rule: attribute before you touch).

## 2026-08-22, late — BUILD 38849 REGISTERED, closing test_handshake's red, and the census pair moved for a peer's work as well as ours

**Not a movement finding; booked here because this arc's own test run surfaced
it.** `test_handshake` had been red on "the exe's build matches the key file
the server will load" — exe 38849 against key file `2026-08-20_21511009c460`,
`_build_of_keyfile()` returning None. The drift itself was dealt with on
2026-08-21 (the skills arc rebuilt on 38849, ran its probe there and closed the
build gap, `d21ac05`; the RUNBOOK gained its two mid-run-update entries), but
the REGISTRATION half never happened: no `pinned.BUILDS` row and no
`vault/client/` pristine snapshot, so the newest patched client was
unrepresentable — the same shape as the 38833 gap of 2026-08-19.

**What landed, all measured rather than typed:** `snapshot_client.py` wrote
`vault/client/2026-08-20_21511009c460/` and verified every file byte-identical
to source (Gw.exe sha256 `21511009c460…`, 10,483,904 B; Gw.dat included). A
`Build` row followed with both patched copies read off disk — loopback
`4cc5bc98…` (145 B vs pristine, `dhbuild` says `ours`) and live-capture
`2ff730c7…` (57 B, `stock`). `test_buildid`'s EXPECT row is measured too: **54
`mov eax,imm32; ret` shapes, exactly one in the build range, getter at
`0x004729E0` with 16 callers** — the third build running with the same getter
VA and the same shape count, so only the immediate moves and the in-range
filter still lands on one. **The pin stays 38797** (`PINNED` is an explicit
`number == 38797` lookup, not `BUILDS[-1]`, so a fourth row cannot move it).

**The census pair, and the honest split.** Registering a build costs pins, as
the 2026-08-14 registration also paid: `pinned.py` 12 → 13, **+1, ours**. The
literal was 156 and the tree measured **188 before this arc touched anything**
— `clientscan/typenames.py` 0 → **32**, an 18th file, from a parallel session's
SKILLS-T1 (`326f439`) that moved neither literal. Both literals are now 189 and
the note records which 32 are not ours, because leaving the pair red for a
peer's work is how it goes blind to the next real drift — the 86-vs-113 failure
already recorded there, now twice.

**Green after:** `test_handshake` 23 · `test_buildid` 51 · `test_buildpins` 40 ·
`test_updatecheck` 30.

**⚠ ONE RED LEFT STANDING ON PURPOSE, and it is not ours to clear.**
`test_pinned` fails "run-live/2026-08-13_64fae3b1369b/Gw.exe verifies too" —
that file is byte-identical to 38849's PRISTINE: an unpatched current-build exe
sitting under the previous build's DH tag, which is exactly the wreckage
`RUNBOOK.md` already names ("the old run-live directory is now a trap worth
knowing about… it classifies `stock` and sits in the right folder while having
no cave"), left by the updater overwriting the patched live build in place.
**Red on `main` before this arc, identical text.** It is guarded at the point of
use — `livesession.py` refuses it at preflight on `key_tapped` false — so the
check is reporting a real hazard, and making it green would delete a signal
rather than a problem. Clearing it means removing or renaming a 4 GB directory
in the owner's vault, which is the owner's call, not a test edit.

### 2026-08-23 — the stale run-live directory is GONE, and test_pinned is green

`vault/run-live/2026-08-13_64fae3b1369b/` deleted (owner's instruction), 3.93 GB
across 8 files. Verified before removal, not after: its `Gw.exe` was
**byte-identical to 38849's pristine** — the copy now held at
`vault/client/2026-08-20_21511009c460/` — so nothing unique died with it; its
`Gw.log` carried **no `webgate.ncplatform.net` lines at all**, i.e. no live
session ever ran there after the updater overwrote it, so its `Gw.dat` held no
live-fetched content; and no code, document or capture depends on the path. The
three live captures whose manifests NAME it (`20260817T183323`, `183756`,
`231139`) anchor provenance on the **exe sha256 `7237b620…`**, which is
committed in `pinned.BUILDS` under the 38833 row — and that binary was already
gone, replaced in place by the updater on 2026-08-21, so their chain is no
worse off than it was. `test_pinned` **150 checks, green**; `dhbuild.py` audits
the whole vault clean with both surviving live builds key-tapped
(`mutex=nopped name=renamed`), which the deleted one was not.

**Affected-set state after the registration and the deletion, re-run on a
CURRENT tree:** `test_handshake` 23 · `test_pinned` 150 · `test_buildid` 51 ·
`test_buildpins` 40 · `test_updatecheck` 30, all green.

⚠ **Two things that are NOT this arc's and are live on `main` right now**, both
found by re-running against an up-to-date tree and both worth a peer session's
attention. (1) `toolkit/authsrv/authsrv.py:12567` raises **`NameError: conn_id`**
— the heading arm's new `cancel_on_move(send, state, conn_id)` from commit
`3dcf9d5` ("Movement cancels the cast"), which `test_position_trust`'s extracted
`_arm` closure cannot satisfy; **red identically on `main`**, so it is a real
fault in that arc rather than a stale checker. (2) This worktree was **38
commits behind `main`** and could not load content at all — a peer had written
`vault/content/composite.toml` into the SHARED vault citing
`toolkit/clientscan/composite.py`, which exists on `main` and did not exist
here. The provenance gate refused exactly as designed; the cure was to
fast-forward the worktree. **Both are the parallel-session hazard CLAUDE.md
names, arriving through the vault rather than through git.**

### 2026-08-23 — ⚠ WITHDRAWN THE SAME DAY — "retail's own client logs the warp"

> **Do not quote this section's headline. It was tested within the hour and it is
> WRONG** — the string is a `Map.cpp` pathing-DATA check, absent from all 29
> loopback logs including warp-heavy ones. The refutation, the count and the
> decode are in the next section. The text below is kept unedited as the
> claim that was made.

#### (as written) RETAIL'S OWN CLIENT LOGS THE WARP, against ArenaNet's own server

**OBSERVED, `live`, and found incidentally while verifying the vault deletion —
this is a calibration datum the whole arc has never had.**
`vault/run-live/2026-08-20_21511009c460/Gw.log` is a real live session (its
`Gc::BeginRequest` lines hit `webgate.ncplatform.net` for
`session/create`, `users/login`, `game_accounts` and `token`, and the build is
stock-DH, which `cage`/`dhbuild` permit to point ONLY at ArenaNet). Twice in
that session the client wrote:

> `Error: Client pathing data out of sync with server.  You may observe your character 'warping' during movement.`

**What this establishes:** the phenomenon this arc has spent nine runs on is a
named, logged condition in ArenaNet's own client, and it fires against
ArenaNet's own server. The warp is not purely an artifact of our server —
retail desyncs too, and the client has a string for it.

**What it does NOT establish, and the limits are severe:** n = **2 lines in one
session**, with no rate, no denominator, no separation measurement, and no
movetap beside it — nothing here touches our own measured rates, and it must
not be quoted as "retail warps as much as we do". The trigger is unknown; the
line may report the client's own reaction rather than a rendered teleport (our
own REALFIX-E events are what a rendered teleport looks like, and no such
instrument was running). It is also not new evidence about any candidate fix.

**Why it is worth writing down anyway:** every rate this arc quotes is measured
against an implicit baseline of "retail does not do this", and that baseline is
now known to be **not zero**. The cheap follow-up is already in reach — the
live corpus is six captures deep, and `Gw.log` is one file per run directory:
count these lines across the live sessions and pair them against the wire, which
is desk work needing no client run.

### 2026-08-23 — ⚠ COUNTED, AND IT REFUTES THE ENTRY ABOVE: the pathing-desync line is a MAP-DATA check, not the warp

**The count, every surviving client log in the vault, `Gw.log` and every rotated
`.prev`/`.pre`/`.run` sibling — 31 files:**

| substrate | logs | logs carrying the line | occurrences |
|---|---|---|---|
| **live** (`run-live/*`, webgate login lines present) | 2 | **2** | **6** (4 + 2) |
| **loopback** (`run/*`, `research/*`, our own server) | 29 | **0** | **0** |

Fisher one-sided on logs-carrying, **p = 0.00215**. ⚠ The denominators are logs,
not sessions: `Gw.log` is rewritten per run, so each file speaks only for the
last session in its directory, and 29-vs-2 is an artifact of how many run
directories exist rather than of how much play each substrate saw.

**THE HEADLINE OF THE ENTRY ABOVE IS WITHDRAWN.** It read *"retail's own client
logs the warp… the phenomenon this arc has spent nine runs on is a named, logged
condition."* **That does not survive its own first test.** Our loopback runs
produce the decoded warp constantly — REALFIX-L5 measured 15.66/min, L8 scored
16 REALFIX-E events in one control arm — and **not one of the 29 loopback logs
contains the string.** If it were emitted by the resync path, those logs would
be full of it. The correct reading of the 6-vs-0 split is the opposite of the
one I published: the line tracks **being connected to ArenaNet**, not warping.

**And the binary says what it actually is.** The string is **UTF-16LE** (an
ASCII search finds nothing, which is why it had never turned up in a scan) at
file `0x7963F8` → **VA `0x00B973F8`**, and exactly one instruction stores that
address:

```
0084E0DA  call 0x7081D0        ; predicate -- Map.cpp   (asserts Map:2144 `bits`, Map:2191)
0084E0DF  test eax, eax
0084E0E1  jne  0x84E0F7        ; NON-ZERO = fine, skip the whole block
0084E0E3  push 0xB973F8        ; the string
0084E0E8  push 2               ; log level
0084E0EA  call 0x46EE30        ; the logger -- Log.cpp
0084E0F2  call 0x5FC2F0        ; and ONLY on this path -- AgApi.cpp (AgApi:1260)
```

Module attribution is ArenaNet's own, via `asserts.py --at`: the predicate is
**`Map.cpp`**, the logger is **`Base/Rtl/Log.cpp`**, the failure-path call is
**`Engine/Agent/AgApi.cpp`**. It is **not** `0x00605FC0` (the desync test), not
`0x006022B0` (the snap), and not any of the three message-driven callers this
arc decoded. A `Map.cpp` predicate is a statement about the **pathing DATA the
map file carries versus what the server declares** — which is what the string
says in plain English and what this arc read past.

**What survives, and it is smaller but real:** ArenaNet ships a named condition
for client/server pathing disagreement, it fires against their own service, and
its failure branch calls into `AgApi.cpp` — the same module as `0x005FCAA0`, the
gate-free SetPosition route REALFIX-Q5 has been unable to attribute. **Whether
those two are related is UNVERIFIED** and `asserts.py --at`'s span is a
heuristic, so do not read the shared module as a link; the cheap test is
`--xrefs 0x005FC2F0` and a read of its body, and it is desk work.

**What this costs the arc: nothing.** No rate, no baseline, no candidate moves.
The implicit assumption the entry above tried to overturn — that our measured
warp rates are ours — stands untouched, because the one instrument that could
have contradicted it turns out to be measuring a different thing entirely.

**The lesson is the one this repo already has a rule for**, and it took under an
hour to pay: *"before quoting a zero, ask what a non-zero would have looked
like."* The inverse applies to a positive. I quoted six occurrences as evidence
for a mechanism without first asking what the substrate that DOES warp would
show — and it shows zero.

### 2026-08-23 — ★★ THE CHAIN IS FULLY DECODED, AND IT ENDS ON AN INSTRUMENT: `0x0023` IS ARENANET'S OWN MOVEMENT-STATE CHECKSUM (REALFIX-I3)

**Static, pristine 38797, no client run.** The `--xrefs 0x005FC2F0` follow-up the
entry above called desk work. Every address below is OBSERVED; the labels are
ArenaNet's own, via `asserts.py --at`.

**The whole mechanism, end to end:**

```
Map.cpp predicate 0x007081D0 returns 0
  0084E0E3  push "Client pathing data out of sync with server..."   (UTF-16, VA 0x00B973F8)
  0084E0EA  call 0x0046EE30          ; Base/Rtl/Log.cpp, level 2
  0084E0F2  call 0x005FC2F0          ; <- ONE caller image-wide, this one

0x005FC2F0  (AgApi.cpp) -- four instructions, complete:
  call 0x0047F660 / mov eax,[eax+8] / mov dword [eax+0x1C8], 1 / ret

0x005FD44D  (AgMsg.cpp, inside the 0x0023 handler at 0x005FD3F0):
  call 0x005FEEA0            ; the checksum, below
  cmp  eax, [edi+8]          ; against the message's second dword
  je   epilogue              ; agree -> nothing
  cmp  dword [esi+0x1C8], 0
  jne  epilogue              ; THE LATCH -- already warned, stay quiet
  push [edi+4] / push "Agent %u position out of sync with server" / push 2
  call 0x0046ED40
```

**`agentMgr+0x1C8` is a LOG-SPAM LATCH AND NOTHING ELSE.** Its only writer is
the four-instruction function above; its only reader on this struct is the
`jne` that skips a `printf`. It changes no movement behaviour, gates no branch
in the mechanism this arc decoded, and is **not a lever**. That closes the
"shared module with `0x005FCAA0`" thread the previous entry left open: same
module, no relationship. (`[ctx+8]` is the agent manager on the neighbouring
function's own evidence — `0x005FC310` reads `+0x14C` and `+0x154` off it, this
arc's async array and its count.)

**★ AND THE COMPARED VALUE IS THE FINDING.** `0x005FEEA0` is five instructions
and a `ret`:

```
mov eax,[ecx+0xB4] / xor eax,[ecx+0xB0] / xor eax,[ecx+0x80]
xor eax,[ecx+0x7C] / xor eax,[ecx+0x78] / ret
```

A raw-dword XOR over **exactly the five fields this arc has spent nine runs
on**: `+0x78`/`+0x7C` position (the dead-reckoned operand of the match test),
**`+0x80` the plane word** (REALFIX-F1's whole subject), and `+0xB0`/`+0xB4`
velocity (what the grant bake writes). **`GAME_SMSG 0x0023` is a movement-state
checksum message** — `{agent_id, checksum}`, `declared_unpack_size` 10, shape
`msg_header + dword + dword`, already in `schema/messages.json` and named
`UNKNOWN_8023` in `authsrv.py:4699`. ArenaNet built a desync detector into the
protocol and we have been carrying its schema row, unnamed, the whole time.

**REALFIX-I3 — the instrument this hands us, and its price.** A server that
computes the same XOR over its authoritative copy and sends `0x0023` gets the
**client's own verdict** on whether its state matches ours, per agent, with **no
movetap, no breakpoint and no second process** — the cheapest desync witness in
the arc, and ArenaNet's own. Before anyone builds it, three things are
UNVERIFIED and two of them can kill it:
1. **Which copy is `ecx`.** The handler passes `ebx`, and whether that resolves
   to the SYNC or the ASYNC agent is not read yet. This decides everything: the
   arc's entire subject is that the two differ.
2. **It is BIT-EXACT.** The XOR is over raw float dwords, so any difference in
   any of five fields — a 1-ulp position, a velocity we never modelled — reads
   as mismatch. It is a "did our writes apply exactly" check, not a "are we
   close" check, and our server models velocity nowhere near bit-exactly.
3. **It logs and returns 1.** It is a DIAGNOSTIC: no snap, no correction, no
   behaviour. Its value is that it makes the client speak, and its output is a
   log line — which means reading it needs `Gw.log`, not the wire.

**Why the line never fires in our runs, measured rather than assumed:** across
1,114 gamesrv captures our server has sent `0x0023` **six times, all on
2026-08-12, all from `PROBE[smsgsweep]`, and all with a zero body**
(`23000000000000000000` — agent 0, checksum 0). Never in normal play. So the
per-agent line cannot fire, and the 0-of-31 count in the entry above is
explained at the source rather than left as an anomaly.

**Corrections this closes.** The previous entry's "the failure branch calls into
AgApi.cpp, the same module as the gate-free SetPosition route — whether they are
related is UNVERIFIED" is now **answered: unrelated.** And the withdrawn
headline two entries up is confirmed wrong a second way — ArenaNet's client does
have a per-agent position-desync line, it is `0x0023`'s, and it is one we have
never given it the chance to print.

### 2026-08-23 — REALFIX-I3's first unknown is CLOSED: `ecx` is the SYNC copy, and that is the good answer

**Static, pristine 38797, no client run.** The `0x0023` handler read from its
entry rather than from the middle:

```
005FD3F0  push ebp / mov ebp,esp / push ebx,esi,edi
005FD3F6  call 0x0047F660
005FD3FB  mov edi,[ebp+8]          ; edi = the message
005FD3FE  mov esi,[eax+8]          ; esi = the AGENT MANAGER
005FD401  mov ebx,[edi+4]          ; ebx = message field 1 = AGENT ID
005FD404  cmp ebx,[esi+0xF0]       ; bounds vs the array's count
005FD40A  jb  0x005FD420           ;   else assert Array.h:587 `index < m_count`
005FD420  mov eax,[esi+0xE8]       ; <<< THE ARRAY
005FD426  mov ebx,[eax+ebx*4]      ; ebx = array[agent_id]
005FD429  test ebx,ebx / jne       ;   else assert AgMsg.cpp:370 `ptr`
005FD441  mov ecx,ebx              ; ecx = THAT agent
005FD443  call 0x005FEEA0          ; the five-field XOR
```

**`[agentMgr+0xE8]` is the SYNC array** — this arc's own `HANDOFF.md`:153 names
it, "ArenaNet's own name via `AgMsg.cpp` asserts", and this handler is that
AgMsg.cpp. The count at `+0xF0` sits at the same `+0x8` spacing as the async
pair's `+0x14C`/`+0x154`. Both asserts are ArenaNet's own and are quoted as
single-citation measurements: `Array.h:587 'index < m_count'` and
`AgMsg.cpp:370 'ptr'`. **`ecx` is the server-authoritative copy — the one our
`0x0029` grants steer — not the rendered one.** Message shape is confirmed from
the code as well as the schema: field 1 `[edi+4]` = agent id (it is also what
the `%u` prints), field 2 `[edi+8]` = the checksum.

**Why this is the outcome REALFIX-I3 needed.** The instrument would compare the
client's SYNC state against ours, and the sync copy is precisely the object our
server already models — `state["dest"]`, the integrator, and every
`state["pos"]` consumer. Had it resolved to the async copy the instrument would
have been near-useless, because we cannot see or steer that copy at all
(`0x0025`'s async arm is gated shut for the client-controlled agent).

**And bit-exactness moves from "probably fatal" to "plausible", on the arc's own
prior work.** All five fields are piecewise-constant between our own messages:
`+0x78`/`+0x7C` and `+0xB0`/`+0xB4` are written by the grant bake `0x005FE950`
(`velocity = unit(d)·speed`), and the dead-reckoner `0x005FFB40` only READS
`+0x78` to compute a position — it never writes it. So the checksum's inputs
change on our grants, not continuously, and `grantsim.py` already reproduces
that bake — including the client's LUT sqrt, derived exhaustively for
REALFIX-C0. Reproducing five dwords bit-exactly is the same class of work that
gate 1's 299.332591 u boundary already came from.

**Still UNVERIFIED, and the list is now two rather than three:** the handler
only logs and returns 1, so the readout is `Gw.log` rather than the wire (an
instrument whose output needs the client's own log file, per-agent, unformatted
beyond `%u`); and nothing here says what the SERVER is supposed to put in field
2 — that it is this XOR is inferred from the compare, which is strong but is a
RECONSTRUCTION of retail's sender, not an observation of one. **Measured, not assumed: retail sends `0x0023` ZERO times in the live corpus**
(137 capture files across 20 live sessions), so there is nothing to check the
sender against, so the field-2 semantics stay
inferred until retail sends one or a probe makes the line fire.

### 2026-08-23 — ★★ REALFIX-I3 IS BUILT AND THE CLIENT SPOKE: 26 of 26 on the positive control, 25 of 26 on the model

**OBSERVED, `ours`, two agent-driven loopback runs**, map 148 default, build
38797 (`vault/run/2026-07-29_221c13772c7a/Gw.exe`, named explicitly), identical
scripted walk both arms (`W:5 S:5` x3, ~30 s of movement, no clicks, no aiming),
each bounded by `--hold` and torn down automatically. Captures
`20260823T104522` (wrong) and `20260823T104823` (model); harness reports
`20260823T104456` / `20260823T104757`.

**The readout is the CLIENT'S OWN LOG**, `vault/run/<build>/Gw.log`, which is
rewritten per run — so each arm's count is that arm's alone.

| arm | `0x0023` sent | `Agent 1 position out of sync with server` logged |
|---|---|---|
| **`wrong`** (model XOR `0x5EED0FF5`) | **26** | **26** |
| **`model`** (parked-at-report) | **26** | **25** |
| pathing latch `agentMgr+0x1C8` | — | **0 lines, both arms — clear** |

**THE POSITIVE CONTROL PASSED 26 OF 26, EXACTLY 1:1**, and that is the result
that licenses everything else. It establishes, at a client, all of: the opcode
is `0x0023`; field 1 is the agent id and field 2 the checksum, in that order
(the client's `%u` printed **Agent 1**, our `PLAYER_AGENT_ID`); the id resolves
in the SYNC array without tripping `Array.h:587`; the compare at `0x005FD448`
runs; the log fires at level 2; and the suppression latch was clear throughout.
**The message decoded statically on 2026-08-23 does what the decode said it
does.** First send on the wire: `230001000000f5ef085d` — 10 bytes, opcode,
agent 1, `0x5D08EFF5`.

**THE MODEL ARM FIRED 25 OF 26, which is what its own banner predicted** ("the
line appears ANYWAY... our velocity model is not the client's bake"). So **we do
NOT reproduce the client's five SYNC fields bit-exactly**, and REALFIX-I3 as a
routine desync monitor would be a smoke alarm that is always on. That is a
result about OUR MODEL, not about the client and not about the warp.

**★ AND ONE SEND MATCHED, which is the interesting number.** Exactly one of 26
produced no line, meaning the client's XOR over its own SYNC copy equalled ours
to the dword on that one occasion — five fields, four of them float bits, all
five right at once. That is not a coincidence a wrong model produces.

⚠ **WHICH send matched is UNPAIRED and must not be asserted.** The log line
carries no timestamp, no position and no sequence — only `Agent 1` — so counts
are all it yields, and nothing here pairs the silence to a send. The strong
candidate is the FIRST send, at spawn `(9826.0, 8077.0)` plane 0, before any
grant had ever been baked: that is precisely the domain
`authsrv.checksum_model` states it is true in ("parked-at-report... TRUE only
between an arrival and the next bake"), and at spawn the copy is parked with
zero velocity by construction. **That is an inference from the model's stated
domain, not a measurement**, and the cheap discriminator is a second model run
with a walk carrying more stop-bounded legs: if the silence count stays 1 it is
the spawn, and if it scales with leg starts it is every parked moment.

**What this hands the arc, stated at its real size.** A working, byte-verified
channel for asking the client whether its authoritative copy matches ours,
costing one 10-byte message and reading out in a log file. Its value is NOT
routine monitoring — 25 of 26 says so — it is as a **bit-exactness oracle for a
model**: any future reconstruction of the client's bake (`grantsim`'s, or a
server-side one) can be scored against the client itself rather than against our
own replay, and a run that goes quiet has proven something no offline harness
can. The one match already shows the oracle can say yes.

**Costs and limits, none of them hidden.** It logs and returns 1 — no snap, no
correction, no reply, so it cannot fix anything and cannot be read off the wire.
The compare is integer equality over float bits, so `-0.0` versus `0.0` reads
like a teleport (pinned in `test_poschecksum.py` §1). The sender is still a
RECONSTRUCTION: retail sends `0x0023` zero times in 137 live capture files, so
what a real server would put in field 2 remains inferred from the compare — the
runs above show the client ACCEPTS our reading, which is evidence for it and not
proof. And the latch means any run that hears nothing must check for the
pathing line before claiming a match; both runs above were checked and clear.

**What landed:** `agents.agent_position_checksum` + `agents.CHECKSUM_FIELDS`,
`authsrv.GAME_SMSG_AGENT_POSITION_CHECKSUM` / `CHECKSUM_PROBE` /
`CHECKSUM_WRONG_SENTINEL` / `checksum_model` / `_send_position_checksum`, the
`--checksum-probe {wrong,model}` flag with its prediction printed at startup,
and `toolkit/authsrv/test_poschecksum.py` (20 checks, floor 20, zero headroom)
with its `TESTS.md` entry in the same commit.
