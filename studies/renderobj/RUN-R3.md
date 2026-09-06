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

---

## RESULT — RAN 2026-09-06 16:15, agent-driven, `main` at `5c5999e`. **P1 MET, P2 MET, P3 met on the wire and on Q1's median with one sub-bar red. F11 is CONFIRMED: the correction went out 50 ms after the park and the body stood on the surface.**

Capture `authsrv-20260906T161545-c1`, tape `r3-agenttap.jsonl` (670 paired samples over 63 s).
The route did what it was written to do: W:9 slid the body up the staircase to the terrace at
`(11303, 9151)` by 18.0 s, the Hatcher parked beside it at `(11238, 9104)` — 80 u, **on ground
our mesh has no trapezoid under** — and stood there 7.8 s swinging; Q:2 W:3 then took both
around onto level ground. Scored with `studies/renderobj/review/terrace.py`.

| | GROUNDZ-R3 | the owner's session (F11's specimen) |
|---|---|---|
| exposure: hostile parked within 80 u of the player on uncovered ground | **84 samples, 7.8 s** | 132 samples, 17.8 s |
| **P1** hostile's client plane == the player's during it | **82 of 84 (98 %)** — the two at 29 precede the correction | 0 of 132 |
| the order that carried it | `PLANE CORRECT … 29 -> 0` at **19.03 s, 50 ms after the 18.98 s halt**; the client's plane read 0 on the next sample | none — every order said mover 29 |
| **P2** height gap, hostile − player | **+14.3 u** p50 and p90, max 15.3; ≥ 35 u for **0.0 s** | +51.9 u for 15.1 s |
| the reader | live: −1050.8 → −1058.6 → −1072.5 → −1074.9 as it moved; **−0.1 u** beside the player on level ground at 29 s | frozen at −1050.1 across 230 u |
| **P3** `0x002C` / Q1 same-instant p50 / halts over 40 u | 0 / **11.7 u** / **6 of 16 (38 %)** | 0 / 6.2 / 0 of 22 |

**P2's 14 u is the terrace's own slope, not a sink**: the player stood 47 u further up a ramp
that rises ~0.3 u per u of y (from −1050.8 at y = 9104 to −1065 at 9151), and the moment both
bodies stood on level ground the gap read −0.1 u. The metric trap F10 named, seen from the
good side. What the run adds to F11 is the whole chain with the client's clock on it: park →
the reported-plane word → F9's zero-distance `0x0029` in the parked branch's next tick → the
client's plane and height live within one sample.

**The red sub-bar is the stairs, and it is GROUNDZ-Q7's.** All six halts over 40 u fall in the
climb (10.4–16.8 s). Our mesh has **no trapezoid under the player at 7 of the 17 grant points
between 9 and 18 s** — the body reads plane 29 the whole way, our decode says NONE at
(10266, 8156), (10300, 8212), (10371, 8284), (10445, 8356), (10521, 8431), (10743, 8647) and
(11184, 9080) — so the keyboard lead had no origin to clip from and every grant was the report
itself, a ~103 u step every 0.5 s, and **world-0 trailed the body by 100–139 u for the whole
climb** (sep 109 / 125 / 122 / 117 u at 11.9 / 12.9 / 14.6 / 17.4 s; 10–17 u on the flat before
it). The hostile's disc runs in world-0's frame, so its parks and the model's fell where the
body was half a second ago; Q1's median stands (11.7 u) and its tail does not. The stairs of
map 146 are walked by the client and half-absent from our trapezoids: **Q7 is not "the terrace"
but the staircase and the terrace both.**

### CORRECTION 2026-09-06 (GROUNDZ-F12) — the red sub-bar's cause was misread

"Our mesh has no trapezoid under the player at 7 of the 17 grant points … the keyboard lead had
no origin to clip from" is wrong on both counts. The seven points are 0.000–0.398 u outside the
stairs' right side — exact containment refusing the client's edge-riding report, four of them
inside at the unit — and the lead HAD an origin (the sliver door admitted every one). What it
had was a heading INTO the wall: every one of the 15 climb reports carries vec2 (766.8, 0.0),
due east, while the body slides 44.3° up the stairs' right side, so the ray was blocked at its
first 2 u sample and clipped to zero (`lead_clip_why: clipped`, 15 of 15). That is why world-0
trailed the body 100–139 u. Retail's answer to the same situation is the next vertex of the
wall along the slide ([MOVECODE-1z-ce](../movecode/FINDINGS.md), shipped); replayed, the climb's
leads become 27–457 u. The stairs are in our mesh; Q7 is closed at [FINDINGS F12](FINDINGS.md).
