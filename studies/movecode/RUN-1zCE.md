# RUN-1zCE — the stair climb under the wall slide: does world-0 keep up with the body once a blocked lead becomes the wall's next vertex?

**Registered before the run.** `MOVECODE-1z-ce` shipped at `0d3f163` from a desk derivation:
RUN-GROUNDZ-R3's climb sent 15 keyboard leads of zero length (the client's heading due east into
the wall the body slides along) and the sync copy trailed the drawn body 100–139 u for the climb;
ArenaNet's server grants the wall's next vertex in the slide direction (49 of 62 live cases to
0.0 u), and `A2_LEAD_WALL_SLIDE` now does the same. RECONSTRUCTION on our map until a body climbs
under it. **This is that climb: R3's own script, same route, same build but the one commit, so R3
(`authsrv-20260906T161545-c1`, `renderobj/r3-agenttap.jsonl`) is the control** — the known-bad
arm already run, on the identical route, two hours earlier. Agent-driven; no aiming. Server
`main` at `0d3f163`.

## 1. Exposure

| | floor |
|---|---|
| tape samples with the player's two copies | ≥ 400 |
| keyboard grants with the report on plane 29 (the climb) | ≥ 10 (R3: 13) — below this the climb did not happen and the run is void |

## 2. Predictions

**P1 — THE LEADS.** On the climb (grants whose report is on plane 29), ≥ 10 of the grants are
`wall-slide` with length ≥ 50 u, and no more than 3 are zero leads. R3: 0 wall-slide, 15 zero
leads of 15. **REFUTED IF ≥ 5 climb grants are zero leads** — then the slide is not firing on the
live report stream the way it fired on the replayed one.

**P2 — WORLD-0 KEEPS UP.** Over the tape samples inside the climb window (from the first plane-29
report to 0.5 s after the last), the player's sync copy vs its drawn body: **p50 ≤ 40 u** and
**p90 ≤ 80 u**. R3 on the same window and instrument: ~100–139 u. **REFUTED IF p50 > 80 u.**

**P3 — THE CLIENT WALKS IT.** The body keeps climbing: the reports still advance ~100 u per 0.5 s
along the 44.3° line, no `0x002C` re-pin, no gate-1 snap, and the body reaches the terrace
(a report at y > 9100) within 1 s of R3's time (18.0 s). REFUTED if a re-pin fires on a slide
grant or the body parks on the stairs.

**P4 — NOTHING ELSE MOVES.** F11's correction still goes out at the terrace park (`PLANE
CORRECT … 29 -> 0` within 0.5 s of the halt) and the hostile's client plane reads 0 through the
exposure (R3: 82 of 84); the hostile's halts over 40 u from the client's copy fall from R3's 6 of
16 — that last one is a hope, not a prediction, because the disc parks in whatever frame world-0
provides and P2 is what moves the frame.

## 3. The run

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 150 --wait 300 --out vault/research/movecode/1zce-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:9 wait:5 Q:2 W:3 wait:8" --hold 15 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

## 4. Scoring

`python studies/movecode/review/slidescore.py --cap <gamesrv> --tape <tape> --compare-cap
vault/captures/gamesrv/authsrv-20260906T161545-c1.jsonl --compare-tape
vault/research/renderobj/r3-agenttap.jsonl` for P1–P3 on both runs through one instrument;
`studies/renderobj/review/terrace.py` for P4's plane exposure; `studies/npctrack/review/npcdrift.py`
for the hostile's halts.

---

## RESULT — RAN TWICE, 2026-09-06 17:41 and 17:50, agent-driven. **P1 MET twice, P3 MET twice, P2 improved 2.3× but short of its bar, P4 REFUTED on run 1 by a knife edge in F11's reach test, fixed, and MET on run 2.**

Run 1: capture `authsrv-20260906T174137-c1`, tape `movecode/1zce-agenttap.jsonl`, `main` at
`0d3f163`. Run 2: `authsrv-20260906T175056-c1`, `1zce2-agenttap.jsonl`, the same tree plus
`NPC_PLANE_REACH_SLACK` (registered before run 2, below). Both scored beside R3 through
`review/slidescore.py` — one instrument, the client's own position accessor for world-0.

| | R3 (control) | run 1 | run 2 |
|---|---|---|---|
| climb grants: wall-slide / zero leads | 0 / **11** | **12** / 0 | **12** / 0 |
| of which ≥ 50 u | 0 | 9 (420, 317, 214, 110, 461, 358, 255, 152, 105 u) | 10 |
| **P2** world-0 vs drawn body in the climb window, p50 / p90 / max | **111.4** / 127.1 / 134 | **51.4** / 94.4 / 123 | **46.6** / 95.4 / 115 |
| world-0 AHEAD of the body / behind | 0 / 58 | 23 (+29) / 40 (−58) | 27 (+32) / 38 (−54) |
| the whole run, `w0score` moving-only p50 / p90 | 25.2 / 123.3 | 13.8 / 82.3 | 20.3 / 80.3 |
| **P3** reports per 0.5 s / on the terrace at / `0x002C` | 103 u / 17.92 s / 0 | 103 u / 17.88 s / 0 | 103 u / 17.98 s / 0 |
| **P4** hostile's client plane == player's through the terrace exposure | 82 of 84 | **0 of 83** | **82 of 82** |
| the hostile's height gap (the ramp's slope is ~14) | +14.3 | +15.6, **cached** | +13.4, live |
| hostile halts: same-instant p50 / over 40 u | 11.7 u / 6 of 16 | 5.6 u / 1 of 16 | **1.6 u / 0 of 16** |

**P1.** Every climb grant is a wall-slide on both runs; the three short ones (4–49 u) are
reports standing 4–7 u before a vertex, and the next vertex follows at the next report. The
capture header carries `A2_LEAD_WALL_SLIDE`.

**P2, not met and not refuted, and the residual is derived.** The bar (40 / 80 u) was set
without modelling what the client does with a vertex-long lead: its sync copy walks the lead at
the granted 288 u/s while the body slides along the wall at 206 (288 × cos 44.3°, 103 u per
report on all three runs), so world-0 pulls AHEAD (+20, +56, +100 u at 12.5–13.4 s on run 2),
reaches the vertex first, parks, and the body passes it and pulls ahead by 74–93 u until the
next report names the next vertex. That sawtooth is retail's rule plus the client's own sync
speed; nothing in it is tuned. Against it, R3's world-0 was behind on 58 of 58 samples, never
closer than 98 u. **A first draft of this scorer read the tape's raw `x, y` and printed a
half-second "dead time" after every grant; that column is m_point, sample-and-hold, and the
dead time did not exist** — `slidescore.py` now goes through `w0score.live`, as the arc's memory
already said to.

**P3.** The body's climb is bit-for-bit R3's: the client is authoritative and the lead only
moves world-0.

**P4, run 1 REFUTED — a knife edge, not F11.** The model parks ON the disc, exactly
`follow_stop_radius()` from the frame, and F11's reach test was `<= follow_stop_radius()`: R3's
park measured 79.96 u from the report and fired the correction; run 1's 80.02 u did not, and
the Hatcher sat 7.9 s on plane 29 with its height cached, exactly as before F11. **Registered
before run 2:** the reach admits the swing's own deadband (`NPC_PLANE_REACH_SLACK =
BOUNDING_RADIUS`, the 12 u by which `enemy_reach()` exceeds the disc), `test_agentlife`
§plane_reach +2 (exactly 80.0 u names the ground; 200 u still carries; floor 323 → 325, green
343), prediction: the plane word 0 within 0.5 s of the park. **Run 2: the mover's word turned
0 on the follow re-path at 18.65 s, half a second BEFORE the park at 19.16, and stayed 0 for 82
of 82 exposure samples** with the height reader live.

**The hostile's halts on the stairs** — R3's red sub-bar — went 6 of 16 over 40 u → 1 → 0, and
the same-instant gap 11.7 → 5.6 → 1.6 u, because the disc parks in world-0's frame and world-0
now runs beside the body instead of 111 u behind it.

**One instrument reading to know about.** `w0score`'s enslavement detector reads **32 %** on
both runs (R3: 0 %): a wall-slide grant is, by construction, the next vertex of the wall the
body is sliding along, which is also the client's own mover's waypoint (1z-bd.2), so the body's
target equals our granted point whenever it slides. The fence is `open` on every climb sample
and the body moves at 206 u/s, not the grant's 288 — the client walking its own wall, not our
order. Documented at the detector's constant; not a change to it.

~~**Open from this run:** retail's 0x003D cadence on the live corpus is 0.5 s at the median but
945 of 2,797 intervals are 0.1–0.4 s, where ours are a flat 0.5; on a slide a faster report
shortens the vertex park. Whether that cadence is the client's own or a response to something
retail sends is unmeasured.~~ **CLOSED at the desk 2026-09-07:** the fast intervals are
HEADING CHANGES, not a cadence — of retail's 945 intervals under 0.45 s, 838 carry a turn of
more than 5° between the two reports (688 moving, 150 standing) and 107 are straight; the
owner's own hand-driven RUN-FEEL2 reads the same shape on our server (47 of 53 fast intervals
are turns). The keyboard climb is straight, so it reports on the 512 u chord alone. The
client's rule, on both servers; nothing retail sends.
