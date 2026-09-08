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
