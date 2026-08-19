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
