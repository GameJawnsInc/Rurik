# RUN-1zCG — the owner's next stairs session under the lead's two new doors

**Registered 2026-09-07, before any session.** `main` at `8ffee6d` plus MOVECODE-1z-cg
(`A2_LEAD_DISC_CLEAR`, `A2_LEAD_W0_ORIGIN`; `--no-lead-disc-clear`, `--no-lead-w0-origin`).
Hand-driven, the owner's own route: the stairs with the Hatcher chasing, pressing into the
walls on the way up, the hole above the stairs walked round (not skipped this time — the
snap lives there). The tape records both bodies. No question to answer in words: the
scorecard is the instrument, and the owner's eye is the tie-break.

## What it tests

RUN-FEEL2's tape held a second "fall through the stairs" the run sheet never scored: at 63.8 s
the client's own gate 2 snapped the PLAYER's body 166 u into the hole above the stairs, froze it
1.5 s, and the body then walked the next lead 460 u as a click-order — "pulled 452 u out" until
[§1z-ck](FINDINGS.md) read the live path ([FINDINGS §1z-cg](FINDINGS.md)). Two doors on the
keyboard lead close the two links (a lead ending inside the Hatcher's disc, which halts
world-0; a lead clear from the report but not from world-0, which the client bakes from).
Retrodicted on FEEL2 (`studies/movecode/review/w0origin.py --check`): the founding lead becomes
the corridor's first vertex from world-0, four more leads move, every new point is on the mesh,
and the three scripted stairs climbs change nothing.

## Predictions

- **P1 — no client snap.** `sessionscore.py`'s "client snaps (fence shut + body jump > 100 u)"
  reads **0** over the session. FEEL2 read 2 on the same route. REFUTED by any snap whose
  world-0 was off our mesh at the instant (the class the doors close); a snap with world-0 ON
  the mesh and the separation past 299 u is the other class (the fence latch, 1z-bw) and is
  recorded, not scored here.
- **P2 — the doors fire.** At least **2** fired keyboard leads carry a door tag in
  `lead_clip_why` (`+w0-route`, `+w0-clip`, `+disc-past`, `+disc-short`) — the exposure floor;
  a session where the hole is not walked round measures nothing.
- **P3 — the player's drawn body stays on the mesh** while the client's own reports are on it:
  worst ≤ 1 u (FEEL2 60.2 u = the snap).
- **P4 — nothing else moves.** Zero leads, 0x002C re-pins, world-0 vs body moving p50 and the
  hostile's numbers within FEEL2's bands on the scorecard.

## The run

**Session 6, 2026-09-08.** Terminal 1 first, and leave it running -- it waits up to 300 s for
the client process to appear, so it must be armed BEFORE the launch:

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 240 --wait 300 --out vault/research/movecode/1zcg6-agenttap.jsonl
```

Terminal 2 brings up the whole stack and launches the client:

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --hold 200 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

HANDS OFF THE KEYBOARD until "body is in the map" (about 25 s) -- the harness is typing the
login and the map entry, and a stray key lands in its script. Then **200 s of your own play**,
and it tears itself down on its own; nothing is left parked on screen.

*(`--map 146` is correct and the capture will say map 148: `content/maps.toml` records the two
sharing one FILE id, so the geometry and the mesh the scorer picks are the same either way.
Session 5's map note is settled by this.)*

## Scoring

```powershell
python studies/movecode/review/sessionscore.py
```

```powershell
python studies/movecode/review/flankcensus.py
```

reads the newest capture and finds the tape by wall overlap; `w0origin.py --tape
vault/research/movecode/1zcg-agenttap.jsonl` lists every lead the doors moved.

---

## RESULT — the owner's session, 2026-09-07 10:05 (capture `authsrv-20260907T100541-c1`, tape `movecode/1zcg-agenttap.jsonl`, 159 s, 314 accepted reports, 219 fired leads, 1,854 tape samples)

*"Felt pretty normal overall, still some rough points."* Four observations, each traced on the tape
to one mechanism; three of them are ours and fixed at the desk the same day (§1z-ch and its two
smaller doors), one is recorded.

| | prediction | measured | |
|---|---|---|---|
| **P1** | zero client snaps | **2**, and NEITHER is the class the doors close: 30.9 s (180 u) is **gate 3** — the Hatcher's disc containing a world-0 that had stalled at the stairs' top seam 150 u behind the body; 112.4 s (325 u, separation 300) is **gate 1** — the owner's own click, which the router sent 700 u EAST first (§1z-ch). The hole class: **zero** — the player's drawn body **0.00 u** off our mesh over 1,854 samples against FEEL2's 60 u. | ❌ as registered, ✅ on the class |
| **P2** | ≥ 2 door-tagged leads | **15**: `clipped+w0-route` 8, `wall-slide+w0-route` 6, `wall-slide+disc-past` 1 | ✅ |
| **P3** | the player's drawn body on the mesh with the reports on it | 0.00 u worst | ✅ |
| **P4** | nothing else moves | 0x002C re-pins **5** (budget-red 2, gate1-red 2, gate2-offmesh 1) against FEEL2's 1 on a session twice as long with far more wall pressing; world-0 vs body moving p50 112 u (FEEL2 97); zero leads 2 of 219 | WATCH |

**The four observations, on the tape.**

1. *"The Hatcher terrain walks for about a second entering the stairs, more from the bottom."*
   Five entries from the foot with the client plane word **0 on the stairs' trapezoids for
   0.4–1.7 s**. The copy parks in the CLIENT's frame (F8's hold: out of reach of the server's
   player, in reach of the frame) and that branch never sent GROUNDZ-Q5's correction — 1.0 s of
   the 1.4 s at 98.3 s; the drawn body then takes the plane one order after the sync copy (0.5 s,
   the client's). **Fixed:** the correction fires from the hold branch too
   (`test_agentlife` `section_hold_plane`).
2. *"Slight warping near the top of the stairs where I was probably colliding with the Hatcher."*
   The two snaps above. At 30.9 s world-0 had been sent NORTH by a key-direction heading while
   the body went west, then two `plane-seam` leads stopped it at the terrace's edge while the
   body stepped down onto the stairs (plane 29); the Hatcher chases the FRAME (world-0, F5) and
   parked against it; world-0's next leg into the Hatcher's disc fired gate 3 and the body was
   pulled 180 u back onto world-0 — beside the Hatcher, which is what the owner saw. The seam
   stall is one report long, retail's own lag; retail's leads DO cross plane seams (144 of 3,151
   walking-player grants, field 3 the far plane, field 4 the mover's), but 1z-bc's refutation of
   the seam clip stands (six fatal leads all crossed file-linked portals the body never walked),
   so this is **recorded, not built**. The 112 s snap is §1z-ch's, fixed.
3. *"Weird chase behaviour around corners: he walks the opposite direction first."* 6 of the
   session's 23 corridor legs pointed more than 90° off the player; the five corridors replayed
   ran **3–7× the straight distance**. §1z-ch: three defects in the router's corner pass.
   **Fixed:** 1.01–1.85×; the session's legs re-solved: backwards 6 → 3, mean 1.05×; RUN-Q9's own
   270 u detour round the hole becomes the hole's corner.
4. *"Wall clipping near the bottom and top of the stairs."* Three bare follows (39, 89, 135 s)
   walked the Hatcher 31–65 u through the stairs' flank and the hole: the copy stood 1.5–11 u off
   our mesh in a seam, `route()` refused the origin (at 135 s also the goal — the report on the
   hole's edge), and the follow fell back to the straight order. **Fixed:** both ends stepped onto
   the mesh (`nearest_walkable`, 16 u) before routing.

---

## RESULT, session 2 — 2026-09-07 10:59 (capture `authsrv-20260907T105915-c1`, tape `movecode/1zcg2-agenttap.jsonl`, 89 s, 201 reports, 151 fired leads, 943 tape samples)

*"Good improvements. The Hatcher still clips through the stairs on entry, top or bottom, only
for about a second before stabilising. The around-the-wall pathing is better, and I got a tiny
warp near the top of the stairs that is probably within acceptable margin."*

(The run sheet's fixed `--out` name overwrote session 1's tape; this one is renamed
`1zcg2-agenttap.jsonl` and the sheet's command should carry a new name per session.)

| | measured | |
|---|---|---|
| client snaps | **1** (27.3 s, 138 u, the "tiny warp"): world-0 on the mesh, separation 179, no agent within 80 u — gate 3's terrain branch at the stairs' foot flank, where world-0 was 30 u off the report's line; not a class the doors cover | recorded |
| the player's drawn body off our mesh | 0.00 u, 0 of 943 | ✅ |
| the doors | 11 `+w0-route`, 1 `wall-slide+w0-route`; zero leads 1 of 151 | ✅ |
| the Hatcher's stairs entries | **4, the drawn plane wrong for 0.36 / 0.36 / 0.46 / 0.73 s** (session 1: 0.4–1.7 s). Each is the re-path cadence: the order that carried the copy onto the stairs said `0->29`, the next order 0.5 s later `29->29`. **Retail's own update after a crossing order: p50 0.64 s, p25 0.28, p90 2.08** (954 NPC orders with field 3 ≠ field 4 on the live corpus, 796 followed by the far plane as field 4). At the wire's floor. | at retail's shape |
| the Hatcher off our mesh | 14.3 u worst, 25 of 943: 34.6–35.8 s (16 u) and 83.9–85.1 s (31 u) at the stairs' foot flank, 77.2 s (12 u) at the hole's edge | see below |
| **0x002C re-pins** | **7** (gate1-red 3, gate2-offmesh 3, budget-red 1), world-0 vs the body moving p50 165 u, separations 305 / 579 / 304 u at the gate-1 pins; **79 of 151 fired leads degraded to `fence-shut`** | the finding: §1z-ci |

**§1z-ci, the fence latch under a held key.** The server's latch re-arms at a keyboard
walk-start — a moving report after a stop — and the owner never stops, so after every re-pin
the latch ran to its 8 s bound (7.06, 9.21 s; 13–44 leads refused each time) while the client's
own fence read OPEN within 0.05–0.5 s on 7 of 7 pins. World-0 stalled, fell 300–579 u behind,
and the next gate-1 re-pins were that. **Fixed:** the fence also re-arms at the first moving
report more than two bounding radii off the pin point — a shut fence does not drive a held key
(1z-aa.2 measured 0–2.9 u), so a body that has walked is a body whose fence is open. Retrodicted
on this session: 74 of the 79 refusals lift, 0.36–0.87 s after each pin; the harness's held-key
case (the fence shut ~3 s, 1z-bw) leaves the body on the pin and lifts nothing.
`--no-fence-rearm-moved` reverts; `test_kbdsync` +4 (floor 176 → 180).

**The foot flank at 84 s.** The corridor's first vertex — the corner at the stairs' foot — stood
24 u from the player, and the client halts a copy whose target its target-agent's disc covers
(F14), so the Hatcher's copy stood in the flank wall while our model walked on and sent the next
leg from a point the client never reached. A vertex inside the player's disc is now the bare
follow (`test_agentlife` +1). Retail's own corridor vertices sit ON wall corners (of 1,965 NPC leg
endpoints followed by a turn, 14% have under 4 u of clearance and almost none 4–12 u), so no
body-radius inset is built: a hostile brushing a corner is retail's shape.

---

## RESULT, session 3 — 2026-09-07 12:12 (capture `authsrv-20260907T121212-c1`, tape `movecode/1zcg3-agenttap.jsonl`, 80 s, 176 reports, 127 fired leads, 839 tape samples)

*"Still seeing the Hatcher sink into the stairs on approach. Also got stuck near the end for a
couple seconds. Options?"*

| | measured | |
|---|---|---|
| 0x002C re-pins | **1** (gate1-red) — down from 7 under 1z-ci; fence-shut refusals 0 of 127 | ✅ |
| the stairs entries | 5 episodes, longest **0.82 s** (retail's plane-update cadence in explorables p50 0.64 / p90 2.08; no retail capture has a monster on stairs — the owner: an outpost, no NPC walks these in retail) | left for now, by the owner's ruling |
| the player's drawn body off our mesh | 0.00 u | ✅ |
| world-0 vs the body moving p50 | 136 u | WATCH |
| **the stuck stretch** | 68.5–71.4 s: the client's own snap put the body on the hole's corner with ITS fence shut; keys dead 2.9 s; the escape click at 69.8 s dropped by our router (`kbd-drop`); then 71.4–74.9 s the body walked our leads as click-orders at 288 u/s until a walk-start reopened the fence. **Corrected by §1z-ck:** the session had ONE client snap (the raw column read two more, 151 and 261 u, at 72.4 and 75.0 s — the walk itself) | **§1z-cj, §1z-ck** |

**The chain, on the tape.** 65.9–68.0 s: the body ran round the east and north of the hole
while world-0, 130 u behind on short clip-point leads (the ray blocked 17 u out at the hole's
edge — retail grants the clip point there too, 5 of 5), was sent by door B along the corridor
to the hole's corner **(11288, 9151)**. The Hatcher, chasing world-0's frame, stood 45 u from that
corner, and the client's avoidance **halted world-0 on it** (F14 — door A's rule, which runs on
the ray and never saw door B's vertex). The body ran on to 264 u; at 68.51 s the client's gate 1
snapped it 255 u back onto world-0 and shut its fence. Our latch knew only our own `0x002C`, so
the next lead went into the client's shut window: the body walked it as an order (288 u/s; the
"yanks" at 72.4 and 75.0 s were this walk on the sample-and-hold column, §1z-ck) — until the
owner's re-press at 74.95 s re-armed the fence. The guard's
sweep read the separation as red only at 71.2 s, blocked on a stale report: its async estimate is
the last report, not a body still running under a held key, and world-0 was halted with no
arrival to mature.

**Fixed, 1z-cj:** (a) door B's vertex is checked against every hostile disc and skipped for the
next point whose leg from world-0 holds; (b) the client's own reseed is read off the report —
one that jumps more than 150 u off the position model, lands within 24 u of the mirror's
world-0, and whose PREVIOUS report stood more than 100 u from world-0 (session 3: 373 / 9.5 /
236 u) — and stamps the latch with that point as the pin, so no lead goes into the client's window
and the walked-off-pin rule lifts it when the body next moves under its keys. Validated across
every tape (see §1z-cj). `--no-client-reseed-latch` reverts.

**Not moved:** the escape click. Our router drops a click while the keyboard is active
(`kbd-drop`; retail answers 7 of 7 such clicks, ROUTER review §1.7). It is a registered run
question with its own exposure floor (`--answer-kbd-click`), and with (b) in place the stuck
window is gone before the click matters.

---

## RESULT, session 4 — 2026-09-07 14:45 (capture `authsrv-20260907T144522-c1`, tape `movecode/1zcg4-agenttap.jsonl`, 108 s, 216 reports, 152 fired leads)

*"1zCG wasn't great. The Hatcher commits too hard at waypoints around the top of the stairs.
Warps when colliding with him around the top and bottom walls. Ended suspended in mid-air and
stuck. The main point of contention is pathing desync around the stairs' walls."*

| | measured | |
|---|---|---|
| client snaps, live path | **6** (214, 391, 279, 247, 226, 718 u) | REFUTES P1 |
| 0x002C re-pins | 3 (2 gate2-offmesh at the foot's edge class, 1 arrival-risk) | WATCH |
| the player parked on a plane word our mesh lacks at its point | 3 episodes, **longest 12.0 s** (the end) | RED, new metric |
| world-0 vs the body moving p50 / p90 | 132 / 350 u | WATCH |
| door-B leads / their idle at the vertex | 39 / **11.6 s** (0.30 s mean; six 0 u legs) | **§1z-cl** |
| the Hatcher's drawn body off our mesh | 17.5 u worst, 27 of 1,217 | RED |

**The chain** ([FINDINGS §1z-cl](FINDINGS.md)): every snap is the body climbing the stairs
on plane 29 while world-0 walks door B's corridor to the foot one vertex per 0.5 s heading
tick, idling 0.3 s at each; at 299 u the client's gate 1 snaps the body onto world-0 at the
foot; the last snap (95.34 s) carried the report's plane word 29 onto a plane-0 point and left
the body hanging in mid-air, unable to walk, for the run's last 12 s. **Fixed:** the lead's
plane words are the mesh's at the destination and at world-0 (`--no-lead-plane-words`), a
door-B lead chains to the next vertex at the copy's arrival (`--no-kbd-lead-chain`), and door
B never names the vertex world-0 stands on.

## RESULT, session 5 — 2026-09-08 18:38 (capture `authsrv-20260908T183848-c1`, tape `movecode/1zcg5-agenttap.jsonl`, 143 s, 225 reports, 144 fired leads) — **THE CLIENT CRASHED**

*"i put myself around the wall at the bottom of the stairs, in the very corner. the hatcher then
walked up to me. this blocked me in — couldn't escape the corner and couldn't move past the
hatcher. i started spamming move commands and got this error."* — then the client's crash dialog
(`vault/research/movecode/1zcg5-crash.txt`):

```
Assertion: !(m_flags & INTERNAL_FLAG_MOVEMENT_STALE)
P:\Code\Engine\Agent\AgAgent.cpp(1198)      Build: 38797   When: 9/8/2026 18:40:20
```

**The P1–P4 checks did not get their run**: the client died at tape t=92.3 s (capture t=91.5),
half the intended session. What the tape and scorecard hold up to the crash:

| | measured | |
|---|---|---|
| the assert | `AgAgent.cpp:1198`, the movement tick's STALE-flag guard | **§1z-cm** |
| the split on the wire | seq 2723 `0x002B` / 2724 `0x001E` / 2725 `0x0029`, 0.3 ms | OBSERVED |
| client snaps up to the crash | 1 (119 u at 41.2 s) | — |
| player parked on a plane word the mesh lacks (mid-air) | 0 episodes | ✅ P2 held so far |
| world-0 vs body moving p50 / p90 | 164 / 300 u | over P4's 100 u — but half a session |
| the Hatcher off our mesh, worst | 12.5 u (22 of 1,623), the foot flank | RED, unchanged from s4 |

**The chain** ([FINDINGS §1z-cm](FINDINGS.md)): the corner-box put the owner spamming clicks;
each click sent a `0x002B` then a `0x0029`, and `world_tick`'s `0x001E` slipped between them.
The `0x002B` SET the client's `MOVEMENT_STALE` flag; the click was answered to a zero-distance
STOP-ECHO, so an arrival was due at the very next tick; that tick ran on the stale flag and
asserted. Retail serialises the pair (2,403 of 2,403 at a zero wire gap); our per-message send
lock did not. **Fixed:** `STALE_PAIR_GATE` holds a `0x001E` on the send condition while another
thread has a `0x002B`/destination pair open (`--no-stale-pair-gate` reverts).

**Session 6 — REGISTERED 2026-09-08, predictions below fixed BEFORE the run.** The clean
stairs run the crash pre-empted, under the gate. Build: `main` at the 1z-cn merge —
`STALE_PAIR_GATE` ON, `KBD_LEAD_CHAIN` / `A2_LEAD_PLANE_WORDS` ON (1z-cl, still unchecked by a
run), and **neither 1z-cn fix in**, deliberately. Same route as sessions 1–5: up the stairs
from the southern tongue with the Hatcher chasing, pressing into the walls on the way, the
hole above the stairs walked round. **Press into the flank corner at the foot too** — that is
where 1z-cn's chords live and where session 5 crashed.

**The two questions to answer in words afterwards, asked now so the run cannot be
rationalised into agreeing** (feedback: ask run questions before the run):

1. Did anything warp, stick, or leave you hanging in mid-air — and if so, where?
2. Did the Hatcher clip through the stairs' flank or commit oddly at the corners?


- **P0 — zero crashes**; `sessionscore.py`'s "pairs split by a 0x001E" reads **0** (the gate's
  own signature; the known-bad arm `--no-stale-pair-gate` reproduces the split).
- **P1–P4** as session 5 registered them (zero snaps, zero mid-air ≥ 1 s, chain ≥ 5, p50 < 100 u).
- Recorded: whether the corner-box itself recurs — the Hatcher filling the only exit is
  NPCTRACK-Q6/Q10, not a sync defect, and is out of MOVECODE's scope.
- **Recorded, not scored: the foot flank** ([FINDINGS §1z-cn](FINDINGS.md)). The capture now
  carries `npc_order` rows naming what `_order` solved from at BOTH exits, so
  `python studies/movecode/review/flankcensus.py` can pin every hostile order rather than the
  128 of 432 the label allows. The two derived fixes are deliberately NOT in this build — this
  run is 1z-cm's check, and a second movement default would have one run convict the pair.

*Map note: the mesh selector scored this capture against map 148; the run command names map 146.
The stalepair finding is wire-only and map-independent, so this is not chased here.*

---

## RESULT, session 6 — 2026-09-08 20:39 (capture `authsrv-20260908T203914-c1`, tape `movecode/1zcg6-agenttap.jsonl`, 104 s, 364 reports, 165 fired leads, 153 clicks answered)

*"no crashes now, feels smooth. couldn't retrigger the air-walk, but don't call it fixed —
it's not clear how to repro exactly. i spent the end of the run spam clicking while in the
corner and didn't hit any crashes or asserts."*

| | registered | measured | |
|---|---|---|---|
| **P0** | zero crashes, zero split pairs | **0 crashes, 0 asserts; 0 of 158 pairs split** — and **the gate FIRED once** (92.65 s, tick held 0.27 ms, 138 pairs opened / 138 closed, 0 bare) | ✅ **with a positive control** |
| **P1** | zero client snaps | **0** separation-gate snaps. The one 155 u jump is OUR OWN grant's arrival teleport | ✅ after an instrument fix |
| **P2** | zero mid-air ≥ 1 s | **0 episodes — but ZERO EXPOSURE**, the trigger never occurred | **not a pass** |
| **P3** | ≥ 5 `act=chain` rows | **4** | under the floor: under-measured |
| **P4** | world-0 vs body moving p50 < 100 u | **130.3 u** (s4 132, s5 164) | ❌ REFUTED |

**P0, and why the gate firing matters more than the zero.** A zero on a rare race proves little
by itself; what makes this a check is that **the race actually happened and was closed**. The
gate held a tick once, at 92.65 s — inside the 90–100 s window where the owner was
spam-clicking in the corner (48 of the session's 153 clicks). Session 5 split 1 pair in 130;
session 6 split 0 of 158 and holds 1. The one occurrence became a hold. **n = 1: one event, not
a rate**, and the crash also needs an arrival due at that tick, which nothing here can observe —
so this is "the mechanism fired and was handled once", not "the crash is impossible".

**P1 needed the instrument corrected first, and this is §1z-ck's lesson a second time on the
same metric.** The scorer read one "client snap" of 155 u at 81.2 s. It is not the gate: the
landing point sits **0.5 u from an `AGENT_MOVE_TO_POINT ... ROUTER one leg` WE sent 0.2 s
earlier**, so it is that grant's own arrival teleport — every grant we send arms the teleport
branch and never the glide branch (`movement/FINDINGS.md`:1147), and spam-clicking lands one
every ~0.1 s. `sessionscore.py` now books a jump landing on a point we granted as a **grant
arrival** and prints it beside the snap count, so the exclusion can never quietly swallow a
real one. **Run against the known-bad arms it still ranks them badly**: s2 1, s3 1, s5 1, and
s4 **5** snaps — which also corrects §1z-cl's "six": one of those six (42.2 s, 279 u) was a
grant arrival too.

**P2 is a zero-exposure null and must not be read as a pass.** The mid-air class needs a jump
that lands carrying a plane word our mesh does not offer there (F11's cached height). The
session's only jump landed at (10615, 8017) on plane 0, **where our mesh offers plane 0** — the
precondition never occurred. The owner's *"couldn't retrigger the air-walk, but don't call it
fixed"* is exactly right, and this is the mechanism-level reason for it: **§1z-cl's plane-words
fix is still unchecked by any run.** The stairs themselves were well exposed (237 of 1,094
samples with the body on mesh plane 29), so this is the trigger being rare, not the route
being wrong.

**P4 refuted, P3 under its floor.** The door-B chain fired 4 times against a registered floor of
5, so it is under-measured rather than refuted; and world-0 still trails the body by 130 u at
the median, which §1z-cl's chain was meant to move and has not.

**The flank, recorded not scored** ([FINDINGS §1z-cn](FINDINGS.md)) — worse, as expected with
both fixes deliberately out and the owner pressing the corner as asked: the hostile's drawn
body reached **23.65 u off our mesh** (s5 12.5, s4 17.5), its worst yet. **The `npc_order` rows
shipped in 1z-cn paid off immediately: 102 of 102 orders pinned exactly** (label inference
managed 24–40 per session), 5 bad chords, **3 in-disc + 2 route-2pt, and zero UNEXPLAINED** —
the corpus's one unexplained chord class is closed by the operand alone. Both fixes are now
unblocked for their own arm.

**New, and it wants its own look:** the player's own drawn body read **8.30 u off our mesh on 3
samples**, and 14 of the session's reports land up to 8.3 u off it, where session 5 had none.
The client is saying it stands where our decode has nothing, at the corner the owner pressed.
UNVERIFIED whether that is missing geometry in our decode or something else.


---

## Session 7 — REGISTERED 2026-09-08, predictions fixed BEFORE the run (MOVECODE-1z-co's check)

Build: `main` at the 1z-co merge — **both flank fixes ON** (`pathmap.ROUTE_GATE_FINE`,
`NPC_LEG_DISC_CLIP`), on top of everything session 6 already carried. The capture header names
both arms (`capture_flags()` now sweeps `pathmap`).

**The route matters more than usual: the chords live at the flank corners.** Same stairs
route, and **press into the corner at the foot with the Hatcher on you**, the way session 6
ended — that is the geometry that produced 10 of the corpus's 11 bad chords. Walk the hole
above the stairs round rather than skipping it.

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 240 --wait 300 --out vault/research/movecode/1zcg7-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --hold 200 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

HANDS OFF THE KEYBOARD until "body is in the map" (~25 s), then 200 s of play; it tears itself
down.

**Predictions.**

- **P1 — the Hatcher's drawn body stays on our mesh: worst < 5 u** (s4 17.5, s5 12.5, s6
  **23.65**). This is the number the arc has printed RED on every hand-driven session and the
  one both fixes exist to move.
- **P2 — zero bad chords.** `flankcensus.py` reads **0** orders whose chord leaves our mesh
  beyond 2 u (s6: 5 of 102). The retrodiction says 9 of 11 go to 0.0 u.
- **P3 — the exposure floor, so a null cannot be an empty run**: at least **60 hostile
  destination orders** with the operand pinned from `npc_order` rows, and at least one
  in-disc clip actually taken. A session that never corners the Hatcher measures nothing here.
- **P4 — nothing else moves**: 0 crashes and 0 split rate/destination pairs (1z-cm still
  holding), client snaps 0, `0x002C` re-pins ≤ 3, and the router's own timing inside its
  band — `sessionscore.py`'s other rows within their session-6 values.

**Carried, still unchecked and NOT scored here**: §1z-cl's mid-air fix has never met its
trigger (session 6 was a zero-exposure null). If a mid-air episode appears it is a finding;
its absence still proves nothing.

**The two questions to answer in words**, fixed now:

1. Does the Hatcher still clip through the stairs' flank or the corner you back into?
2. Anything new or worse than session 6 — warps, sticking, or the chase behaving oddly at
   corners now that it takes them rather than cutting them?


---

## RESULT, session 7 — 2026-09-08 23:08 (capture `authsrv-20260908T230801-c1`, tape `movecode/1zcg7-agenttap.jsonl`, 104 s, 163 reports, 90 fired leads)

*"the range of his approach is strange, almost like he's following a server position where I'm
not quite pushed into the corner like I am on the client. if i approach the corner slowly i can
get him hitting me from actual melee range. if i collide with him near the corner there are some
warps."*

| | registered | measured | |
|---|---|---|---|
| **P1** | hostile drawn body worst < 5 u | **0.00 u**, 0 of 744 (s6 23.65) | ✅ |
| **P2** | zero bad chords | **0 of 41** | ✅ |
| **P3** | ≥ 60 pinned orders, ≥ 1 in-disc clip | **41** orders, clip fired **once** | ❌ under the floor |
| **P4** | nothing else moves | 0 re-pins (s6 3), 0 split pairs, **1 client snap** | mostly ✅ |

Also clean for the first time: halt points off our mesh **0**, hostile plane-lag episodes **0**.

**1z-co is confirmed on the number it was built for** — the flank RED that stood since session
1 reads 0.00 u — with the caveat that P3's floor was not met, so the in-disc clip's own arm is
thin (one firing).

**The owner's three observations are one mechanism and it is the next defect**
([FINDINGS §1z-cp](FINDINGS.md)): the follow targets `state["pos"]`, the server's position
model, and in the corner that model walks a ~500 u keyboard lead the player's body never
travels — the wall holds the body still while the client keeps reporting a walking velocity, so
the model drifts **144–259 u** out of the corner and the Hatcher parks 80 u from a phantom.
The slow-approach control is the owner's own and it is decisive: standing still,
|report − drawn| is **0.0 u** at the median and the Hatcher closes to 77 u; moving, it is
**41.3 u** and 10 of 19 halts stand beyond the 92 u swing reach. The warps are the same root
seen from the other end — the client's own gate reseeding the body onto a world-0 the refused
corner leads left 155 u behind.

**Session 8 is not registered yet**: the fix touches `D1_LEAD`'s doctrine and the follow's
target together, and wants its own derivation first.
