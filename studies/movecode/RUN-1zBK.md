# RUN-1zBK — the lead under the shipped guard, follower removed

**Registered in [FINDINGS.md](FINDINGS.md) §1z-bj.5** (committed `2a95145`, 2026-09-05): the
`--no-enemy` arm of RUN-1zBI, to separate the short seam-clipped lead from the follower's
avoidance disc. `MOVECODE-1z-bk` scores it. One run, agent-driven, hands off, owner away.

## 1. The configuration

RUN-1zBI's command with the follower removed (the harness default `--no-enemy`): shipped
guard (gate-2 seam tolerance, stationary waiver, plane clip, origin test all ON), lead ON,
same `WSWQESW` route on map 146.

## 2. The prediction (from §1z-bj.5)

The short seam-clipped lead is walked without the follower (body ≥ 150 u/s within 0.3 s of
the press); **refuted if** the hold is dead with no follower (the cause would be the short
lead alone).

## 3. The run

Terminal A: `python toolkit/clientscan/agenttap.py --agents 1 --seconds 75`
Terminal B: `python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"`

## RESULT — RAN 2026-09-05 11:13. Scored in [FINDINGS.md](FINDINGS.md) §1z-bk.

**Prediction MET.** Legs 1–3 walked (909 / 810 / 941 u); leg 2S's 494 u `plane-seam` lead was
backpedalled in full. No dead hold — §1z-bj's follower reconstruction holds.

**But a different failure on the same route.** After leg 3 crossed the 29→0 seam and stopped at
`(11456,9151)` plane 0, the client's reported position **froze there for the last four legs**
(~21 s); the drawn body was pinned there through four held keys; on leg 5E it settled 308 u
out before a `budget-red` `0x002C` reseed returned it. Four AGTRACK re-pins fired (all after
the freeze, so consequence not cause). **`stopcensus` no-lock (`YYYYYYY`), `w0score` CONFIRMED
(p50 0, moving p50 9.9, max 148 u, FREE)** — both blind to a body pinned at a stale report with
both copies reseeded together. The onset is client-side and upstream of our re-pin; the next
check is the `MapFindPath` return tap on this route (§1z-bk.4), and a lead-OFF `--no-enemy` run
to see if the seam freeze is the shipped default's too.
