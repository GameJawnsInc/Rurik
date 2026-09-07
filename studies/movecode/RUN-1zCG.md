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
