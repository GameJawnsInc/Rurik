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

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 240 --wait 300 --out vault/research/movecode/1zcg5-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --hold 200 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

HANDS OFF until "body is in the map" (about 25 s), then 200 s of your own play, then it tears
itself down.

## Scoring

```powershell
python studies/movecode/review/sessionscore.py
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

**Session 6 — registered, not run.** The clean stairs run the crash pre-empted, under the gate:

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
