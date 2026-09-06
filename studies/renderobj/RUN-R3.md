# GROUNDZ-R3 — the terrace above the stairs, scripted: does F11's reported-plane word put the Hatcher on the surface?

**Registered before the run.** `GROUNDZ-R3`. F11 shipped from the owner's session
([npctrack/RUN-FEEL.md](../npctrack/RUN-FEEL.md)): on the terrace above map 146's stairs our
mesh has no trapezoid, `_npc_plane` held the carried 29, and the client drew the Hatcher 52 u
into the ground for 16 s. The fix names that ground with the player's own reported plane when
the hostile is within its stop radius of the report, and F9's correction then carries it.
RECONSTRUCTION until a body rises. Server `main` at `63fdd95`. Agent-driven: a long W press
slides the body up the staircase (the R3/R4 route reached (10688, 8593) in 5 s; the owner's
terrace points are 400–800 u further along the same diagonal), a short turn takes it around the
wall, and two pauses let the Hatcher park beside it.

## 1. Exposure

| | floor |
|---|---|
| tape samples with both bodies | ≥ 200 |
| the player's body on the terrace: samples with `planes_at(player)` = {0} at y > 8800 and x > 11000 | ≥ 60 (2 s) |
| **the hostile parked within 80 u of the player on ground our mesh has no trapezoid under** | **≥ 30 samples (1 s)** — without this the run has zero trials and the owner drives |

## 2. Predictions

**P1 — THE WORD.** During the exposure, the hostile's client plane equals the player's reported
plane (0) on **≥ 90 %** of samples, and the capture shows at least one `PLANE CORRECT` or a follow
order carrying the mover's plane 0 while the hostile stands on uncovered ground. **REFUTED IF the
hostile's client plane stays 29 through the exposure** — then the fallback did not fire or the
client ignored the word.

**P2 — THE SURFACE.** With the hostile parked within 80 u of the player on the terrace, its
ground z is within **15 u** of the player's (the owner's session: 52 u for 16 s). **REFUTED IF
≥ 35 u for ≥ 1 s of the exposure.**

**P3 — NOTHING ELSE MOVES.** Zero `0x002C`; Q1 same-instant ≤ 30 u; no new halt/re-follow class.

## 3. The run

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 150 --wait 300 --out vault/research/renderobj/r3-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:9 wait:5 Q:2 W:3 wait:8" --hold 15 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

## 4. Scoring

The feel session's timeline script (planes, heights and our mesh per body per second) over the
new tape, plus `npctrack/review/npcdrift.py` for P3.
