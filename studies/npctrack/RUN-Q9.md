# RUN-NPCTRACK-Q9 — the corridor on the wire, on the stairs route

**Registered before the run, 2026-09-07.** `main` at `96ec883` plus the uncommitted
NPCTRACK-Q9 change (`NPC_FOLLOW_CORRIDOR`, `--no-npc-corridor`; `test_agentlife`
`section_corridor_wire`, green 355). Agent-driven: RUN-1zCE's script exactly, which already
carries the hole crossing (`Q:2 W:3` down p0#2496's left edge after the climb), so the Hatcher
must get from the stairs' foot to the terrace and then across the hole above the stairs to
reach the player.

## The question

Q9 as recorded ([FINDINGS.md](FINDINGS.md)): our wire carried no corridor and the client
walks a hostile's `0x002A` dead straight — through the hole above the stairs, 45 u from any
trapezoid, parking 8.4 u inside the wall. The desk half is done (F16): retail's server sends
its NPCs `0x0029` legs while geometry intervenes and the `0x002A` naming the player once the
line is clear, and every such leg in the corpus is a straight-clear segment on the client's
own mesh. The follow now does the same. **This run asks whether the client's copy of the
hostile stays on the mesh when the wire carries the corridor.**

## The control

The same script under the previous default, scored by
`studies/renderobj/review/meshcensus.py --agent 10 --tape <tape>` (the Hatcher's DRAWN body,
world 1, against our mesh of map 146):

| tape | samples | worst off our mesh | samples > 2 u |
|---|---|---|---|
| `movecode/1zce2-agenttap.jsonl` (RUN-1zCE run 2, the direct control) | 657 | **60.3 u** | 138 |
| `movecode/1zce-agenttap.jsonl` | 653 | 38.8 u | 104 |
| `renderobj/r3-agenttap.jsonl` | 670 | 12.8 u | 86 |
| `npctrack/feel-agenttap.jsonl` (the owner's, hand-driven) | 575 | 45.0 u | 169 |
| `npctrack/r1-control-agenttap.jsonl` | 817 | 93.8 u | 129 |

## Predictions

- **P1 — the hostile stays on the mesh.** The Hatcher's drawn body: worst off our mesh
  **≤ 5 u** over the whole tape (the edge class is ≤ 0.5 u; F14's sidestep and the disc park
  can add a few), and **≤ 10 samples > 2 u** against the control's 86–169. REFUTED at
  worst > 5 u or > 10 samples.
- **P2 — the corridor is on the wire.** The capture holds **≥ 2** `FOLLOW … leg:` sends
  (`0x0029` to agent 10 carrying a corridor vertex) — this is also the EXPOSURE FLOOR: fewer
  means the route never put geometry between them and the run measured nothing.
- **P3 — the chase still arrives.** At least one `agent 10 halts at` within
  `enemy_reach()` + 20 u of the player's report at that instant, on the terrace, as RUN-1zCE
  run 2 had. REFUTED by a chase that never parks, or parks > 150 u out.
- **Not asked here:** H1 vs H3 (whether the client's follower ever calls `MapFindPath` for
  an NPC). The fix does not depend on which; the `movehook` tap is not armed.

## The run

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 150 --wait 300 --out vault/research/npctrack/q9-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:9 wait:5 Q:2 W:3 wait:8" --hold 15 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

## Scoring

`meshcensus.py --agent 10 --tape vault/research/npctrack/q9-agenttap.jsonl` for P1; the
gamesrv capture's `FOLLOW … leg:` and `halts at` labels for P2/P3
(`studies/npctrack/review/npcdrift.py <tape> <capture>` for the halts).

---

## RESULT — ran 2026-09-07 01:33 (capture `authsrv-20260907T013309-c1`, tape `npctrack/q9-agenttap.jsonl`, 670 samples, 13 halts, 28 follow orders)

| | prediction | measured | |
|---|---|---|---|
| **P1** | the Hatcher's drawn body worst ≤ 5 u off our mesh, ≤ 10 samples > 2 u | **0.15 u worst, 0 samples > 2 u** (670 samples) against the direct control's 60.3 u / 138 (1zce2) and 12.8–93.8 u / 86–366 on five other stairs tapes | ✅ **MET** |
| **P2** | ≥ 2 corridor legs on the wire (the exposure floor) | **2**: `FOLLOW re-path leg … corridor vertex (10286,8359) plane 0->29` at the stairs' foot, and `FOLLOW leg … (10993,9268) plane 29->0` round the west side of the hole above them; each followed by a `leg-end` 0x002A naming the player once the line was clear | ✅ **MET, at the floor** |
| **P3** | the chase still arrives at the disc | halts at **76, 79, 80, 80 u** from the player (four of 13; the other nine are the disc parking in the client's frame while the script keeps walking, RUN-1zCE's shape) | ✅ **MET** |

**Nothing else moved.** `npcdrift` at the halt's own instant (F9): sync copy p50 **4.3 u**, over 40 u
1 of 13 — between the two RUN-1zCE controls (1.6 / 5.6, 0 / 1 of 16). Its "settled 0.5 s after"
comparator reads 116 u here and **96 / 111 u on the same two controls**: the script walks
continuously, so a fresh follow re-opens within 0.5 s of most halts (9 of 13 here, 11–12 of 16
there) and that column measures the re-follow, not the park. The player's own drawn body:
0.26 u worst, 0 samples > 2 u.

**Q9 is CLOSED.** The client never did path a hostile's `0x002A`; the corridor is now what the
wire says, and on the one route this repo has where geometry stands between the hostile and the
player, the client's copy stayed on the mesh to 0.15 u. H1 vs H3 (whether the client's follower
ever calls `MapFindPath` for an NPC) was not asked and does not matter to the fix.
