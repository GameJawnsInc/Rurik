# The render object — where an agent's height comes from

**Opened 2026-09-06** on the owner's instruction, after MOVECODE §1z-cb proved the height
cannot be read from the agent: its movement record has no z, and the one candidate field is a
literal zero the client writes on every read.

**Identifiers.** `GROUNDZ-F<n>` = decoded facts about the height chain. `GROUNDZ-Q<n>` = open
questions. Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Everything here is static disassembly of the pinned client**
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`, build 38797, pristine, ImageBase `0x00400000`).
**Nothing has been read out of a running process.** Eight agents produced it, four decoding and
four refuting; **13 claims were corrected**, and §6 lists the corrections that matter because
two of them would have misled a live reader.

---

## GROUNDZ-F1 — the walk from an agent id to its view object

`0x00802160` is a checked id→view lookup over one global array. Disassembled in full:

```
00802163  mov ecx, [ebp+8]              ; arg0 = the agent id
00802166  cmp ecx, [0x00BF96D4]         ; count
0080216C  jae  -> return 0
0080216E  mov eax, [0x00BF96CC]         ; array base
00802173  mov ecx, [eax + ecx*4]        ; obj = arr[id]
00802178  test ecx, ecx / je -> 0
0080217C  cmp dword [ecx + 0x9C], 0xDB  ; TYPE TAG
00802186  setne al / dec eax / and eax, ecx
```

ArenaNet's own name for the base form is `ManagerFindAgent` — the client asserts
`AvApi:1552 !ManagerFindAgent(agent)` at `0x007E0A62`, over the unchecked variant at
`0x00802140`. `0x00802160` is that plus a `type == 0xDB` downcast. Three sibling lookups exist
on the same array with tags `0x200` and `0x400`, so the array holds mixed AgentView types keyed
by agent id.

**The index IS the agent id**, not a separate view id: the `AvAgent` constructor hands the id it
registers under to `AgApi 0x005FC550`, which indexes `[AGBASE+0x14C]` bounds-checked against
`[AGBASE+0x154]` — the same async array and count `movetap.py` already documents.

**The round-trip a live reader should use** is `[view+0x2C] == id`. The registrar at
`0x008014B0` reads `[obj+0x2C]` *as* the array slot (`mov [eax + esi*4], edi` at `0x00801515`),
so the client's own code guarantees it. Same idiom `movetap` already uses on the agent side.

## GROUNDZ-F2 — the object, and the position triple on it

`AvChar` derives from `AvAgent` at offset 0; its own fields begin at `+0xC4`; `sizeof` is
`0x1C4`, witnessed at **three** construction sites (`0x007DF301`, `0x007DF361`, `0x007F627A`),
each `mov ecx, 0x1C4` / `call` operator new / `push 0xDB`. Class identity comes from the strings
trailing the vtables (`0x00A9223C`, `0x00A93930`), **not** from neighbouring asserts — that
distinction is a correction, see §6.

`+0x84`, `+0x88`, `+0x8C` are a position triple, and the proof is at the operand level rather
than "three adjacent floats":

- the accessor `0x007EBFD0` writes `[esi+0x84]`→`out[0]`, `[esi+0x88]`→`out[4]`,
  `[esi+0x8C]`→`out[8]`;
- `0x00802E10`, called with `eax = esi+0x84`, reads `[ecx]`, `[ecx+4]`, `[ecx+8]` and stores
  them into three consecutive globals `0x0108765C/60/64`;
- `0x007E14E0` subtracts three camera statics from all three components and takes a square
  root — a distance from the eye.

`+0x84` and `+0x88` are the agent's own x and y. The per-frame writer is
`0x007EB90F  fstp dword ptr [edi]` with `edi` hoisted at `0x007EB81C` — a `mod=00` store that
`codescan --writes` cannot see, which is a real hole in our tooling and is recorded as such.

## GROUNDZ-F3 — the height field, and its one producer

**`view+0x8C` is the ground z.** In the whole AgentView band there are four stores; one belongs
to a different class, one is the constructor writing `0.0` (`fldz` at `0x007EB4D2`), and the
other two are each the instruction *immediately after* a call to the same function:

```
007EB91B  call 0x007EBF00   ->  007EB920  fstp dword ptr [esi+0x8C]
007ECA59  call 0x007EBF00   ->  007ECA5E  fstp dword ptr [ebx+0x8C]
```

`0x007EBF00` is `AvAgent::GetGroundHeight(const Point* pt, Vec3* outNormal)` — `__thiscall`,
`ret 8`. Its second argument is a **normal** out-pointer, not a second point: `0x007EBFAC`
copies `+0x64/+0x68/+0x6C` into it, and the constructor seeds that triple to `(0, 0, -1.0)`.

It memoises: the key is the query point at `+0x74/+0x78/+0x7C`, the cached height is `+0x30`,
and a sticky failure bit is bit 0 of `+0x58`. **The stored value is the queried altitude minus
1.0** — `0x007EBF6F  fsub qword ptr [0x0093C1D0]`, and `0x0093C1D0` reads `1.0` out of `.rdata`.

**The cache condition, corrected** (the first reading had the branch backwards): it *recomputes*
when any of x, y, plane differs, **or** when the plane is non-zero **and** the failure bit is
set. It takes the cache when all three match **and** either the plane is zero or the bit is
clear. Semantically: **the retry-on-failure only arms for prop-bearing planes**, because nothing
about a plane-0 answer can change.

## GROUNDZ-F4 — the query, and how the plane reaches prop geometry

The producer calls `0x0070A190`, and the client names it in its own log string at `0x00A6B6A0`:
`MapQueryAltitude() invalid params point=(%f,%f,%u) mapRect=(...)`. An image-wide sweep finds
`0x007EBF5E` is the **only** direct AgentView→`MapQueryAltitude` call in the binary.

**The plane word is the only route from an agent to prop geometry**, and the mechanism is
byte-verified by both the decoder and its refuter:

```
0070A40B  lea ecx, [ebx+8]              ; &point.plane
0070A433  cmp dword ptr [ecx], 0
0070A436  je  -> 0x0070A4D7             ; plane == 0: SKIP the whole prop block
0070A475  push dword ptr [ecx]          ; the plane
0070A47A  call 0x00721C40               ; PathApi: plane -> (propIndex, propLayer)
0070A4AB  call 0x00738D30               ; PrApi:  prop altitude
0070A4C1  call 0x004F1BA0               ; min(terrain, prop)
```

with the client's own asserts naming both callees — `PathApi:507 propIndex && propLayer`,
`PrApi:573 props`, `PrApi:574 altitude`, the file string at `0x00A6FF1C` being
`P:\Code\Engine\Map\Props\PrApi.cpp`.

**The terrain half is a heightmap and cannot represent a stair tread.** `TrnQueryAlt`
(`0x0074F720`) seeds the out-altitude to `+INF` (`0x00948654`), walks a rect of chunks, and each
chunk multiplies its coordinate by 32 and tests each quad as **two triangles**, folding results
with the same `min` helper.

## GROUNDZ-F5 — the model side, and why this ends in a reader

`0x007ECB90` hands `&view+0x84` to the model placement API, guarded by the `m_model` handle at
`view+0x60` (`AvAgent:818` asserts it). That reaches `MdlSetPlacement` (`0x00782CB0`), which
resolves the handle through the type-tagged table at `0x0046FE40` with FourCC `'mdl '`, and then
`Model::SetPlacement` (`0x00784010`), which stores nine plain dwords:

**`model+0x10` = pos.x, `model+0x14` = pos.y, `model+0x18` = pos.z.**

`Model::ApplyWorldTransform` (`0x007841D0`) pushes GrTrans stream 2 and, in the no-rotation
fast path, passes **`lea eax, [esi+0x10]`** — the translation *is* `model+0x10..+0x18`, with no
inference at all.

**The world matrix itself is NOT pollable.** It is a slot on a global 96-deep stack (base
`0x00C120C0`, stride `0x1400`, matrices at `+0x7C` stride `0x34`), pushed and popped per model
per frame and reused by every model. Reading it cross-process returns whatever the client was
drawing at that instant, with no agent identity attached.

**But the translation is copied verbatim from persistent per-agent fields, so this arc ends in a
READER, not a hook.** CLAUDE.md carve-out (3) is not needed.

```
level 1:  view = [[0x00BF96CC] + id*4]
          guard  id < [0x00BF96D4],  view != 0,  [view+0x9C] == 0xDB,  [view+0x2C] == id
          ground z = float32 at view+0x8C
level 2:  model = handle_resolve([view+0x60], 'mdl ')
          drawn z = float32 at model+0x18
```

## GROUNDZ-F6 — what this says about the operator's sink, which is less than it looks

RUN-1zCA's residual was a hostile standing ankle-deep in a stair tread. The obvious reading —
*plane 0 skips the prop query, so the body gets raw terrain* — **is refuted by our own data**:
RUN-1zCA measured plane **29** on both copies for all 269 samples of the sink.

So the prop branch **was** taken. What follows from F3 instead: since every non-init write of
`view+0x8C` is the ground z, **the body is drawn on whatever surface the query returned**, and an
ankle-deep sink is a *wrong-surface answer*, not a skipped query. The candidates are now three,
and they are separable:

1. the prop altitude for plane 29 resolved below the tread;
2. `min()` picked the terrain over the prop;
3. the per-agent vertical term at **`view+0x40`** — omitted from the first field map and found by
   a refuter — which is subtracted from `+0x8C` at three read sites (`0x007EC1DB`, `0x007F62FE`,
   `0x007EB1DE`).

**So the drawn height is not `+0x8C` alone**, and a live reader must capture `+0x40` and `+0x30`
beside it or it will mis-attribute the sink.

## GROUNDZ-F7 — `up is -Z`, and it is RECONSTRUCTION

Load-bearing for reading `min()` as "the highest surface wins", so it is labelled honestly. It
rests on **two** genuinely independent witnesses plus one weaker: the default ground normal is
`(0, 0, -1)` (`0x0093CF24`, stored at `0x0070A1DC` and `0x0070A45F`); the clamp at `0x007FD1A8`
pushes a point back when its z exceeds the ground; and a `fchs` at `0x00737332` negates a
raycast distance against a `{x, y, 50000}` origin.

The first draft offered four witnesses. **Two of them were the same fact stated twice, and that
fact is what the sign is being used to explain** — `min` only means "highest wins" *if* up is
−Z, so quoting it as evidence is circular. Corrected here.

---


## GROUNDZ-F8 — the reader is CONFIRMED live, and the sink is our own stale plane word

**GROUNDZ-R1, 2026-09-06** ([RUN-R1.md](RUN-R1.md)). The arc's static decode is now measured:
799 of 799 samples read `ok` for both agents with **zero refusals**, the round trip held, and
`+0x8C == +0x30` on every single sample — the self-check with no free parameter. The height
varies 171.30 u across the stairs against 21.60 u on the flat, so it is not a constant a wrong
offset happened to land on. **GROUNDZ-F7's `up is -Z` is upgraded from RECONSTRUCTION to
OBSERVED**: heights are negative and grow more negative with altitude.

**And the sink has a measured mechanism.** With both bodies on plane-29 ground by our own mesh,
the Hatcher's client plane read **0** and its height sat **32.5 u below** the player's. The
cause is a link nobody had reason to look at: our follow resolves field 4 **at send time**, the
hostile then walks onto the higher plane and **arrives**, and the halt `0x0028` carries no plane
— so the stale word stands, and `MapQueryAltitude` skips the prop branch (GROUNDZ-F4) and
answers from the terrain under the staircase.

**MOVECODE §1z-bz is not wrong; it is incomplete.** It made every order carry the mover's
current plane, which is what let the Hatcher climb at all. What it cannot do is correct the
plane *after* the last order, and a parked body is precisely when no further order comes.

**`GROUNDZ-Q5`, registered:** re-path when the mover's own plane changes, not only when the
player has moved. One condition, the existing message, no deviation from retail's shape,
`--no-plane-repath` as the revert, and this run's **32.5 u** as the number it must move.


## GROUNDZ-F9 — Q5 SHIPPED: a stationary hostile's plane word is corrected

`NPC_PLANE_REPATH = True`; `--no-plane-repath` reverts. **Two faces of one defect, one flag.**

**The branch that previously sent nothing at all.** A hostile parked in reach with no follow
gets no message of any kind — the tick returns early, and that is the branch GROUNDZ-R1's
sunken Hatcher sat in for 22 s. It now emits **one zero-distance `0x0029`** to the point the
client already has it on, carrying the corrected plane in both words. Nowhere to walk, because
the destination is where it stands.

**The message is retail's own, not an invention.** Field 4 of a `0x0029`/`0x002A` is what writes
the client agent's plane (`agtrack_mirror.bake_grant`: *"agent plane +0x80 <- plane_second"*),
and ArenaNet's servers send NPC-addressed `0x0029` in bulk — **8,160** across the live corpus,
**1,164** of them with field 3 ≠ field 4 (§42.4). A zero-distance grant is the smallest thing
that carries the word.

**The second face:** our own plane changing now re-paths an in-flight follow, instead of waiting
for the player to travel `FOLLOW_REPATH_MOVED`. On a staircase that is exactly when it matters,
and it adds no sends on flat ground because the rate floor is unchanged.

**Rate-limited on `FOLLOW_REPATH_INTERVAL`**, the same floor every other NPC send uses, so a body
oscillating on a seam cannot turn the correction into a storm.

**Tests:** `test_agentlife` `section_plane_repath`, floor 286 → **294** (green run 310). It pins
the correction, that it goes to the body's own point, that the told word is remembered, that no
change sends nothing, the rate floor, the mid-walk re-path, and **the known-bad arm** — with the
flag off the identical stale word produces no correction, which is GROUNDZ-R1's 22 s of plane 0
reproduced.

**Unverified against a client.** GROUNDZ-R1's **32.5 u** is the number this has to move, and the
run that scores it is the stairs route again. Until then this is derived-and-tested, not
confirmed.


## GROUNDZ-F10 — R2: the correction works and its payload is wrong

**GROUNDZ-R2, 2026-09-06** ([RUN-R2.md](RUN-R2.md)), a one-change A/B against R1.

**CONFIRMED:** a zero-distance `0x0029` carries the plane and the client applies it **within
90 ms** — plane 29 → 0 on the very next tape sample, with the ground z re-resolving 10.2 u in
the same step. GROUNDZ-F9's mechanism is real.

**REFUTED, and it is F9's own defect:** the grant is zero-distance in OUR model and **24.04 u
from where the client draws the body**, because `_npc_plane_correct` sends `agent["pos"]`. The
client moved the body onto our point.

**It WALKED, it did not teleport** — corrected the same day. The first reading came off raw
`m_point` deltas, the sample-and-hold column this repo forbids quoting motion from. Through
`w0score.live()` the step is **18.43 u at 189 u/s** then 5.61 u at 63, a decelerating walk into
the point; whole run **1 of 814** steps exceeds 400 u/s on `live()` against **36 on the raw
column**. So the cost is a 24 u twitch of a parked hostile, not the warp class.

**ZERO TRIALS on the sink:** the Hatcher parked where our mesh has no trapezoid, so its plane
could not be adjudicated on any of 213 samples (R1 disagreed on 213 of 213).

**A metric correction that outlives this run:** "the height gap to the player" measures the
staircase's SLOPE, not the sink, whenever the bodies stand at different points — R2's gap is
*larger* than R1's while the planes agree. The sink metric is **does the client's plane equal
the plane our mesh assigns its own x/y**. R1's 32.5 u is "the run where the plane was
demonstrably wrong", not a threshold.

**`GROUNDZ-Q6` — ASKED AND ANSWERED, in the negative.** "Carry the last point we ORDERED" was
measured before it was written and is **worse**: 48.45 u from the drawn body at the correction
against our copy's 24.04, and a median **195.4 u** across the run, because the follow names the
PLAYER's position and the client parks ~80 u short. The follow message is no safer a vehicle
either — 31 of its orders landed on an already-parked body and moved one by up to 83.23 u.

**F9's payload is the closest of the three** (24 / 48 / 195 u). **There is no server-side point
that reliably sits on the drawn body**, because the server never learns where the client put an
NPC. So Q6 reduces to the DRIFT itself, which belongs to the NPC-tracking arc — **opened the same
day: [studies/npctrack/FINDINGS.md](../npctrack/FINDINGS.md), ident word NPCTRACK.** Its F1
measured the drift on 40 halts (median 53.8 u, not 24), F4 reproduced the client's copy with the
client's own equations, and Q1 shipped that model as the server's copy.

## GROUNDZ-F11 — the terrace sink: a missing trapezoid, a held word, and the fix is the client's own report

**The owner's session, 2026-09-06 15:48** ([npctrack/RUN-FEEL.md](../npctrack/RUN-FEEL.md)):
led up the stairs of map 146 and around the wall at the top, the Hatcher was drawn **52 u into
the ground for 16 s** beside a player standing on the surface — *"he didn't walk up the slope
like my character did"*. The tape: from 44.1 s the hostile stood only on points where **our mesh
has no trapezoid** (nearest covered ground 5–45 u off, plane 0 from 46.6 s), its client plane
stayed **29** (our follow orders said so, field 4 = the carried word, `_npc_plane` having nothing
better), and its height reader answered **the cached −1050.1 for 230 u of walking** — `ok`, no
refusal, no surface on plane 29 there — while the player 77 u away read plane 0 at **−1102**.
F9's correction compares the word against `plane_at`, which was silent, so it never fired. This
is R2's "zero trials" region (F10) seen with a body in it.

**SHIPPED (`NPC_PLANE_REACH`, revert `--no-npc-plane-reach`, in the capture header):**
`_npc_plane` now takes the session state, and where the mesh has **no trapezoid at all** under
the mover (`planes_at` empty — a seam, where `plane_at` declines between two, is not silence)
and the mover stands within its follow stop radius (80 u) of the player's last accepted report,
**the player's reported plane names the ground**. The client's own word for ground within reach,
never a guess between our own trapezoids; the carry everywhere else, as §42.5 wrote it. On the
tape this names 0 from 46.6 s, the parked branch then sends F9's zero-distance `0x0029` with 0
(the send the terrace never got), and the client re-resolves the height on plane 0 — the terrain
under the terrace, which is where the player's −1102 came from. `test_agentlife`
§`section_plane_reach` pins the measured shape, out-of-reach, a seam, a mesh without
`planes_at`, the parked branch's correction and the revert arm (floor 323 → green
341). ~~**RECONSTRUCTION until a session on that terrace shows the body rise**~~ **CONFIRMED,
[RUN-R3.md](RUN-R3.md), the same afternoon, agent-driven:** the Hatcher parked on the same
uncovered ground 80 u from the player, the correction `29 -> 0` went out **50 ms after the
halt**, the client's plane read 0 on the next sample (82 of 84 in the exposure) and its height
reader was live again — 14 u below the player on the ramp, −0.1 u beside it on the level. The
owner's session read 52 u for 15 s.

**What it does not cover:** a mover more than 80 u from the player on uncovered ground keeps
its carried word (nothing to name it from); a plane-0 ground whose true height is a prop rather
than terrain (F4's "plane 0 skips the prop query") would still sink — no specimen; and the
missing trapezoids themselves, which are the pathmap's ~~(the terrace is walkable in the client
and absent in our decode of the same data — worth a look at what `from_chunk` drops there)~~
**— struck by F12: the client's BODY never entered it either. Nothing is missing.**

**RUN-1zCE (the same evening) found the reach test's knife edge.** The model parks ON the disc,
exactly `follow_stop_radius()` from the frame, and this fallback's test was `<=
follow_stop_radius()`: R3's park measured 79.96 u from the report and fired, RUN-1zCE run 1's
80.02 u did not, and the Hatcher sat 7.9 s on plane 29 with its height cached as if F11 had
never shipped (0 of 83 exposure samples). The reach now admits the swing's own deadband —
`NPC_PLANE_REACH_SLACK = BOUNDING_RADIUS`, the 12 u by which `enemy_reach()` exceeds the disc —
pinned in `test_agentlife` at exactly 80.0 u and one step short of the slack's end, the 200 u
carry unchanged (floor 323 → 325). Run 2, registered before it ran: the mover's word turned 0 on
the follow re-path half a second BEFORE the park, 82 of 82 samples, height live.

## GROUNDZ-F12 — Q7 CLOSED: nothing is missing from the mesh. The stairs are plane 29, the hole above them is a hole in the client's mesh too, and the two symptoms behind the question were a keyboard lead aimed INTO a wall (fixed, MOVECODE-1z-ce) and a hostile ordered straight THROUGH one (NPCTRACK-Q9)

**Asked:** *"dig into Q7, why the stairs are missing from the mesh."* Ident `GROUNDZ-F12`. Desk
only: the two tapes, 397 captures, the pathing and props chunks, and the live corpus; no run.
New tools `review/meshcensus.py --check` and `../movecode/review/wallslide.py --check`.
OBSERVED unless marked.

**F12.1 The chunk walks and the stairs are in it.** File id 0x1B97D: the tag walk closes to the
byte, 58 planes, 6,120 trapezoids, zero inverted. Plane 29 is the 5-trapezoid staircase prefab
(x 10069–11183, y 8279–9385; 1z-bx.1 named it the same way from the other side). RUN-R3's seven
"NONE" grant points sit −0.004..+0.398 u from the stairs' RIGHT SIDE — the 1z-bf edge class,
exact containment refusing a point the client reports from an edge — and four of the seven are
inside once rounded to the unit. The R3 sheet's "no trapezoid under the player at 7 of the 17
grant points" was our decoder's rounding, read as geometry.

**F12.2 The client's body never leaves our trapezoids.** Per sample, the client's plane word
against ours and the drawn body's distance off our mesh (`meshcensus.py`): R3's tape 670 player
samples, the feel tape 575 — none more than 0.5 u off, and the client's plane word IN our
`planes_at` on 1,072 of 1,072 on-mesh samples. Nine tapes, 6,591 drawn-body samples, worst
0.36 u. The corpus: 397 captures on map 146, **10,529 accepted reports — 9,786 inside a
trapezoid, 552 distinct points within 0.5 u of an edge, 2 within 2 u, 18 beyond**; of the 18,
10 were walking a server grant whose destination sits off our mesh or lie on its leg (the
2026-08-19 endpoint echoes), 7 came within 3 s of a > 200 u jump between consecutive reports
(the body MOVED by the server, then walking back on — among them a 62.8 u park beside the
bridge's north-west end on 2026-08-22, plane 18, held 11 s, the one point in 10,529 worth a
second look), and 1 is the client's own: a 10.7 u stop-report at the foot of the stairs on
2026-09-03. `from_chunk` drops nothing the client walks on.

**F12.3 The hole is real, and it is the client's too.** At y ≈ 9104 our mesh covers x ≤ 11216
(p0#2495) and x ≥ 11308 (p0#2496); at y ≈ 8910 the gap is 410 u wide. No prop stands in it: the
map's props chunk holds 864 placements, the nearest 629 u away, and none of the 34 outlines
covers it. The player's body on the feel tape RAN THE HOLE'S BOUNDARY: (11238, 9120) on
p0#2495's right edge at 44.1 s, the vertex (11280, 9151) at 44.8 s, then down p0#2496's left
edge with the body 0.1–0.2 u from the edge for 80 u (45.65–45.95 s) — a body pressed against
ground it cannot enter, on the client's own mesh, along the line our decode draws. The client's
height reader along that boundary climbs from −1051 (the landing) to −1102 over 350 u while the
hole's interior at (11238, 9104) reads −1050.8, the landing's level (R3): a lower pocket beside
a raised ramp — terrain, not a prop, and exactly *"he didn't walk up the slope like my
character did"*. F11 read the hole as *"walkable in the client and absent in our decode"*: the
second half is true and the first is not — the client's BODY never entered it. What entered it
was the hostile (F12.5).

**F12.4 Symptom A — world-0 100–139 u behind the body on the climb — is a lead aimed into a
wall. FIXED, [MOVECODE-1z-ce](../movecode/FINDINGS.md).** Decoded from the capture's own 0x003D
bytes: all 15 climb reports carry the heading vector **(766.8, 0.0) — due east** — while the
body moves at 44.3° along the stairs' right side, a single 44.3° line from (10366, 8279) to
(11183, 9079) that the client's collision slides the body along. `a2_clip_lead` aims the lead
along the heading, the ray enters the wall at its first 2 u sample, and the grant is the report
back: `lead_clip_why: clipped`, arm zero-lead, `HELD HEADING (X,Y) from (X,Y)`, 15 of 15. Not
"no origin" — an origin, a heading, and a wall. ArenaNet's server does something else, measured
on the live corpus and shipped as `A2_LEAD_WALL_SLIDE` / `pathmap.wall_slide`: the next vertex
of the wall the body presses against, in the heading's slide direction. Replayed through the
shipped function the climb's 15 zero leads become 27 / 94 / 419 / 316 / 210 / 107 / 4 / 457 /
355 / 251 / 148 / 44 / 102 / 120 / 5 u along the stairs. RECONSTRUCTION on our map until a run
walks it; the rule itself is retail's on 62 live specimens.

**F12.5 Symptom B — the Hatcher IN the hole — is our wire, not the client's mesh. Open as
[NPCTRACK-Q9](../npctrack/FINDINGS.md).** The follow's order is a bare 0x002A "go to the
player", and the client walks a hostile's 0x002A dead straight: on the feel tape its sync copy
and drawn body are IDENTICAL on every sample as it cuts from (11219, 9099) through (11296, 9035)
— 45 u from any trapezoid — to park at (11412.8, 8909.7), 8.4 u inside the wall, 76 u from the
player, plane word 29, height cached. The router (1z-by) only ever moved the SERVER's copy
("wire unchanged"), and NPCTRACK-Q1 then replaced that copy with the client's straight-line
one, so nothing has ever routed the client's hostile around anything. On the tapes the
hostile's sync copy is more than 2 u off our mesh while moving on 4 of 9 (r1-control 94 u, feel
45, renderobj-r1 45, r1 29). The owner's *"he pathed around the wall well"* was the player's own
route; the Hatcher went through. F11's correction still does what it says — the plane word is
right wherever the hostile parks — it cannot put the hostile on the ramp.

**Corrections carried:** RUN-R3 (a note under its RESULT), F11's parenthesis above (struck),
npctrack's Q3 closure and RUN-FEEL (the wall).

## Open

- ~~`GROUNDZ-Q5` — ship the plane-change re-path~~ **SHIPPED, GROUNDZ-F9; CONFIRMED by R2 (F10,
  the client applies it in 90 ms).** Its blind spot — ground our mesh does not cover at all — is
  F11's, shipped 2026-09-06 and unverified against a client.
- ~~**`GROUNDZ-Q7` — why does our mesh have no trapezoid on the terrace above the stairs — OR ON
  THE STAIRS?**~~ **CLOSED 2026-09-06, [F12](#groundz-f12): nothing is missing.** The stairs are
  plane 29 and R3's seven "NONE" points were 0.0–0.4 u outside an edge; the client's body never
  leaves our trapezoids (10,529 accepted reports on map 146, 6,591 drawn-body tape samples,
  worst 0.36 u); the hole above the stairs is a hole in the client's mesh too (the owner's body
  slid along its edge to 0.2 u for 80 u). The two symptoms were a keyboard lead aimed INTO the
  wall the body slides along — MOVECODE-1z-ce, shipped — and a hostile the client walks dead
  straight through the hole because our wire carries no corridor — NPCTRACK-Q9. One point in
  10,529 is worth a second look: a 62.8 u park beside the bridge's north-west end on
  2026-08-22, plane 18, held 11 s, three seconds after a jump.
- **`GROUNDZ-Q1` — which of F6's three candidates causes the sink.** Separable by a live read of
  `+0x8C`, `+0x30` and `+0x40` at a known stair position.
- **`GROUNDZ-Q2` — is the position updater per-frame?** NOT FOUND. `0x007EB7F0` is also a vtable
  entry (`0x00A92224`), so a direct-caller search cannot close. Note the memo makes call
  frequency and query frequency different numbers regardless.
- **`GROUNDZ-Q3` — the second, terrain-free height path.** `0x0070A190` returns early through
  `0x007372B0` when `map->[+0x78]` is populated, ignoring the plane entirely and hardcoding a
  flat normal. Its module could not be named — `0x00737xxx` falls in an assert gap.
- **`GROUNDZ-Q4` — stream 2 is assumed to be the world transform.** The enum was never located;
  the bound `GR_TRANSFORMS = 5` and the name `GR_TRANSFORM_VIEW` come from asserts, the
  identification of 2 does not.

**Nothing here has been observed in a running client.** Every float above is a static read. The
three refutable predictions a live reader must satisfy are in `GROUNDZ-F3`/`F5`: `+0x8C` must
bit-equal `+0x30` immediately after a store; `+0x8C` must equal `model+0x18` for the same agent;
and `+0x8C` must vary on a slope and hold constant on flat ground.
