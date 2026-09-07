# RUN-1zCG — the owner's next stairs session under the lead's two new doors

**Registered 2026-09-07, before any session.** `main` at `43ef732` plus MOVECODE-1z-cg
(`A2_LEAD_DISC_CLEAR`, `A2_LEAD_W0_ORIGIN`; `--no-lead-disc-clear`, `--no-lead-w0-origin`).
Hand-driven, the owner's own route: the stairs with the Hatcher chasing, pressing into the
walls on the way up, the hole above the stairs walked round (not skipped this time — the
snap lives there). The tape records both bodies. No question to answer in words: the
scorecard is the instrument, and the owner's eye is the tie-break.

## What it tests

RUN-FEEL2's tape held a second "fall through the stairs" the run sheet never scored: at 63.8 s
the client's own gate 2 snapped the PLAYER's body 166 u into the hole above the stairs, froze it
1.5 s, and the next lead pulled it 452 u out ([FINDINGS §1z-cg](FINDINGS.md)). Two doors on the
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
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 240 --wait 300 --out vault/research/movecode/1zcg-agenttap.jsonl
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
