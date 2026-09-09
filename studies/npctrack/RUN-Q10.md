# RUN-NPCTRACK-Q10 — two hostiles, the first multi-agent measurement

**Registered 2026-09-07, not yet run.** `main` at `a6c979b` plus `--enemies N`. Every movement
measurement in this repo so far was one player and ONE hostile (agent 10). Two chasers share
the player's world-0 frame, each other's discs (the client's avoidance pass runs per agent,
F14), the follow's disc park, the corridor on the wire (Q9), and the keyboard lead's new disc
door (1z-cg) — none of it measured. Agent-driven: RUN-1zCE's stairs script, with two Hatchers
spawned at the compass ring (east, then north of the arrival point).

## Predictions

- **P1 — both chase and both park.** Each hostile parks at the disc of the player's frame:
  ≥ 1 halt within `enemy_reach()` + 20 u of the player's report for BOTH agents 10 and 11, and
  neither halts inside the OTHER's 80 u disc (the avoidance pass sidesteps it, F14). REFUTED by
  a hostile that never arrives, or two parked bodies within 60 u of each other.
- **P2 — the copies hold for both.** `npcdrift` at the halt's own instant p50 ≤ 15 u for each
  hostile (one-hostile runs read 1.6–6.7); `copysep` p90 ≤ 20 u pooled.
- **P3 — the player is not yanked.** `sessionscore`: zero client snaps, zero 0x002C beyond
  the scripted runs' 0–1; the player's drawn body on the mesh (worst ≤ 1 u).
- **P4 — the corridor still goes on the wire** for both (≥ 2 `leg:` sends per hostile on the
  hole crossing), and both drawn bodies stay on our mesh (worst ≤ 2 u, Q9's number was 0.15).
- **Exposure floor:** both hostiles must reach the player's disc at least once; otherwise the
  run measured nothing.

## The run

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10,11 --seconds 150 --wait 300 --out vault/research/npctrack/q10-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:9 wait:5 Q:2 W:3 wait:8" --hold 15 --shots 2.0 --game-args "--map 146 --explorable --enemies 2 --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

## Scoring

`python studies/movecode/review/sessionscore.py` (the hostile rows pool every hostile on the
tape and name them); `studies/npctrack/review/npcdrift.py <tape> <capture>` is agent-10-only
today (`AGENT = 10` at the top) and needs an `--agent 11` pass or a loop before P2 can be read
for the second body — that is the one instrument change this run needs first.


## The runs — 2026-09-09, agent-driven, twice (`studies/npctrack/review/q10run.py`)

The `--agent 11` pass had already landed with the groundwork commit, so nothing needed
building first. Two runs of the registered script, back to back, on `main` at `1207ef4b`
plus nothing: tapes `q10-agenttap.jsonl` (734 samples, capture `20260909T123825`) and
`q10b-agenttap.jsonl` (716 samples, capture `20260909T124637`). Both harness verdicts PASS,
no crash. `sessionscore.py` REFUSED both at 11 accepted reports against its floor of 20 —
the registered 30 s script is too short for it — so P3 is read off the tape and the
capture directly (`scratchpad q10p1.py`, the same quantities).

| | run a: agent 10 | run a: agent 11 | run b: agent 10 | run b: agent 11 |
|---|---|---|---|---|
| 0x0028 halts | 10 | 11 | 10 | 11 |
| **P1** halts within reach + 20 u of the report | 7/10 | 8/11 | 7/10 | 8/11 |
| **P1** halts with the OTHER drawn body inside 80 u | **9/10** | **9/11** | **8/10** | **9/11** |
| **P1** both parked within 60 u of each other | **6** | **6** | **5** | **5** |
| **P2** `npcdrift` at the halt's instant, p50 | 3.8 u | 13.8 u | 5.4 u | 13.2 u |
| **P2** copysep sync vs drawn, p90 / max | 14.1 / 34.6 | 21.9 / 42.3 | 4.7 / 30.8 | 4.7 / 30.8 |
| **P4** 0x0029 legs on the wire | 0 | 0 | 0 | 0 |

**P1 REFUTED, the same way twice.** Both hostiles chase and both park — the exposure floor
is met — but they park **in one body**: from t = 10.6 s (run a) / 10.4 s (run b) the two
sync copies are **0.0 u apart** and stay there through every later halt, the drawn bodies
with them, and the server's own halt labels name **the same point for both agents** at
the same tick (run a: `(10174, 8103)` at 11.60 / 11.70 s, then `(9928, 8103)`,
`(9848, 8375)`, `(10568, 8523)` … identical pairs to the end). The sheet's "neither halts
inside the other's 80 u disc" assumed F14's pass would sidestep the second chaser; it did
not, and the tape says why: the two copies were **side by side** (13 u apart in run a,
65 u in run b, both walking at 288 toward the same target point) when they converged, so
the other agent sat outside the pass's ±60° forward cone (F14 rule 3) and the pass never
ran; two agents dead-reckoning to one point from beside each other simply meet there.
**P2 MET** for both (the second hostile's drift is 2.5–3.5× the first's on both runs,
unexplained, under the bar). **P3 MET** on the tape: one `0x002C` per run (the scripted
runs' 0–1), zero body jumps over 60 u, the drawn hostiles never closer than 70 / 41 u
(run a) and 73 / 73 u (run b) to the drawn player. **P4 NOT MEASURED**: zero corridor
legs on either run — with `--enemies 2` both hostiles spawn on the compass ring 80 u from
the player, and no geometry intervenes on this script (Q9's two legs came from a spawn
across the hole). Zero exposure, not a null.

**The retail half, at the desk the same afternoon (`review/chasercensus.py`).** Chases of
the player never overlap in the corpus (5 connections, 8 chases, 0 pairs) — zero exposure.
The same server rule with far more exposure is two NPCs on ANY one target
(`--any-target`): 28 connections, 113 chases, 14 overlapping pairs. **ArenaNet sends
co-chasers the same order, bit for bit**: `0x002A` follows to two NPCs on one target
within 0.25 s of each other are identical on **12 of 13** (max 7.5 u); the one rich pair
(`20260819T132414`, agents 29 and 30 on agent 36, later 28 too) carries six consecutive
follows at 0.5 s with the same six points for both agents — the point is the target's own
server position. And its NPC legs are not kept apart either: over 7,635 simultaneous
`0x0029` pairs to two NPCs (55 connections) the point separation is p5 49 / p10 108 u,
**292 under 24 u (two radii), 513 under 80 u, and the 1st percentile is 0.0**. So the
identical order is retail-faithful; what retail's server does with its own copies
between the order and the halt is not on the wire (its chasers' halts in that pair fall
at different instants, 180.28 and 184.30, but they also started 1.5–3 s apart).

**Verdict: nothing ships.** Two chasers standing in one body is a visible symptom, but
every witness we have says the wire shape is ArenaNet's, the client's pass is blind to a
side-by-side approach by its own cone, and a server-side park bearing per chaser would be
a RECONSTRUCTION with no retail witness. It is recorded as a lever, for the owner's eye:
if two hostiles in one body reads as wrong in play, the derivation is retail's server-side
separation, and the only observable of it is the halt instant.
