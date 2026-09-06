# NPC tracking — where the server thinks a hostile stands, against where the client holds it

**Opened 2026-09-06** on the owner's instruction, after the render-object arc's last question
(`GROUNDZ-Q6`) reduced to *"our copy of a parked hostile sits 24 u from the body the client
draws, and no payload we could send fixes that"*. This arc is about the copy, not the payload.

**Identifiers.** `NPCTRACK-F<n>` = measured facts. `NPCTRACK-Q<n>` = open questions, and the
derived fix (Q1). `NPCTRACK-R<n>` = runs. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Everything in F1–F5 is measured on tapes and captures that already existed** — no client was
launched to open this arc. The three scripted stairs runs are the same route, map, harness and
client build, and differ only in the server between them:

| run | tape (`vault/research/…`) | capture (`vault/captures/gamesrv/…`) | server |
|---|---|---|---|
| `1zCA` | `movecode/1zca-agenttap.jsonl` | `authsrv-20260905T233210-c1` | 1z-bz planes + 1z-by router |
| `GROUNDZ-R1` | `renderobj/r1-agenttap.jsonl` | `authsrv-20260906T013213-c1` | + nothing |
| `GROUNDZ-R2` | `renderobj/r2-agenttap.jsonl` | `authsrv-20260906T024050-c1` | + GROUNDZ-F9 |

**The instrument is [review/npcdrift.py](review/npcdrift.py)**, which prints every number below
from those files and carries a positive control (§F4's model must reproduce the client to ≤ 20 u,
and the pre-Q1 integrator must sit ≥ 40 u from it) so the next session cannot quote a broken
scorer. The operator's own bridge session (`1zBW`, pre-router) is reported where it adds
something and is not pooled: its halts are dominated by the wedge 1z-by since closed.

---

## The question, stated so it can be refuted

The server keeps its own position for every hostile — `agent["pos"]` — and every range check,
the leash, the plane word and GROUNDZ-F9's correction read it. The client keeps two copies of
the same hostile: the SYNC copy (world 0, the one our `0x0029`/`0x002A`/`0x0028` write) and the
DRAWN body (world 1). `agenttap` reads both through the client's own accessor. **How far is the
server's copy from the client's, when does the gap open, and what would the server have to
compute to close it?**

The server's number comes from its own halt labels — *"agent 10 halts at (x,y)"* — which print
`agent["pos"]` at the instant the `0x0028` goes out. Nothing below dead-reckons the server's copy.

## NPCTRACK-F1 — the drift, measured: a median 53.8 u at the halt

At every `0x0028` the server sent agent 10, the server's copy against the client's copies 0.5 s
later (settled):

| run | halts | vs the DRAWN body p50 / p90 / max | vs the SYNC copy p50 / p75 / p90 / max | halts over 40 u |
|---|---|---|---|---|
| `1zCA` | 13 | 63.3 / 487.8 / 520.1 | 63.3 / 112.5 / 482.6 / 525.9 | 7 / 13 |
| `GROUNDZ-R1` | 14 | 47.6 / 120.4 / 193.3 | 47.9 / 91.9 / 126.6 / 193.3 | 10 / 14 |
| `GROUNDZ-R2` | 13 | 56.0 / 163.1 / 317.1 | 56.0 / 157.8 / 164.8 / 318.2 | 9 / 13 |
| **pooled** | **40** | **55.7 / 193.3 / 520.1** | **53.8 / 113.4 / 193.3 / 525.9** | **26 / 40** |

**OBSERVED.** RUN-R2's "24 u" was one halt's drift at one instant; the arc's number is a median
of 53.8 u with two-thirds of halts over 40 u. The operator's bridge session, pre-router, sat at a
median 487.5 u over 6 halts (max 955.8) — the wedge, not this mechanism, and 1z-by's business.

## NPCTRACK-F2 — the client's own two copies of the hostile agree

At the same instants, the client's SYNC copy against its DRAWN body: **max 19.6 u, over 12 u on
2 of 40 halts** (12.4 u once on `1zCA`, 19.6 once on `R1`, 9.5 max on `R2`). **The drift is
server-versus-client, not the client's handoff** — whatever the server models, the target is one
point, and the sync copy is the one our messages address. Every number after this is scored
against the SYNC copy.

## NPCTRACK-F3 — which stop rule the client's copy obeyed, and whether our halt cut it

ANIMREF-RE §38.2 decoded the client's follow: the `0x002A` handler writes the SYNC copy's
destination to the point named; the collision resolver stops the copy when the agent in `+0x98`
(the player's SYNC copy) is inside `(rA + rB + 56)² = 80²` **and inside a ±60° forward cone**;
and *nothing reads `+0x98` to fetch the followed agent's current position* — the copy walks to the
point it was given, and only a re-path moves the point.

Classifying each halt by where the client's sync copy stood 0.5 s after it:

| | halts | server copy vs SYNC there |
|---|---|---|
| **AT-DISC** — 68–92 u from the player's SYNC copy | 15 | p50 18.7 / 35.2 / 12.8 per run |
| **AT-POINT** — within 12 u of the last ordered point | 1 | 41.6 |
| **NEITHER** | 24 | p50 112.5 / 91.9 / 90.7 per run |

**The halts where the client stood at its disc are the ones the server got nearly right; the
NEITHER halts carry the drift.** And the cut census — was the sync copy still walking at the last
tape sample before the `0x0028`, with a finite target? **10 of 40** (4 / 4 / 2), remaining leg to
its target p50 119 / 105 / 170 u. So §40.9's "the halt freezes the rendered body short" is real
but a **minority** mechanism, one quarter of halts. (A first cut of this census used the DRAWN
body's motion over the 0.3 s before the halt and read 31 of 40 — the drawn body's own settling
after the sync copy stops, not a cut. The sync copy's velocity is the right column.)

## NPCTRACK-F4 — the client's own equations reproduce its copy: 10 u median

This is the arc's load-bearing measurement, and the reason no fix in it is tuned.

`toolkit/authsrv/agtrack_mirror.SyncAgent` is the client's decoded dead-reckoner (`0x005FFB40`:
`pos = +0x78 + v × dt`, no clamp) and bake (`0x005FE950`), already run by this server for the
PLAYER's world-0 copy and validated against the corpus (`agtrack_replay.py`). Feed it the
Hatcher's own messages from the capture — each `0x002A`/`0x0029` a bake, each `0x002B` a pure
store of `moveSpeed`, each `0x0028` a halt in place — add §38.2's disc stop, and sample it at every
tape instant against the tape's SYNC copy:

| arm | all samples p50 / p90 (2,460) | at the 40 halts p50 / p75 / p90 / max | halts over 40 u |
|---|---|---|---|
| dead-reckoner alone | 71 / 74 / 67 per run | 74.5 / 156.3 / 248.7 / 510.5 | 32 |
| + the disc stop, no cone | 10.0 / 7.4 / 13.6 | 14.9 / 20.3 / 49.2 / 209.9 | 4 |
| **+ the disc stop with the ±60° cone** | **10.0 / 4.9 / 11.6 ; p90 14.6 / 23.9 / 21.7** | **11.6 / 17.7 / 22.8 / 57.3** | **1** |

**OBSERVED.** The two disc-only outliers (209.9 u on `R1` at 28.0 s, 208.4 on `R2` at 40.0 s)
are both a player standing BEHIND a copy that is walking away to its ordered point — inside 80 u,
outside the cone — and both go to 0.0 / 10.1 u with the cone. Both terms are the decode's; neither
was adjusted to fit. The disc fired 29 / 27 / 32 times per run against 13 / 14 / 13 halts: **most
of the client's stops are the resolver's, not our `0x0028`.**

**This also settles the mechanism without a simulation of my own.** The server's integrator
(pre-Q1) walked its copy along an A* corridor toward the LIVE player and parked it 80 u from
`state["pos"]`. The client's copy walks straight to the ORDERED point and parks 80 u from the
player's WORLD-0 copy. Between re-paths the server's copy tracked a player the client's did not
know had moved, and at the stop the two discs sat in different frames.

## NPCTRACK-F5 — the frame, and the best the server can do with it

The disc references the player's world-0 copy, which the wire never carries. The server has three
things it could put there. The same model as F4, in each:

| frame for the disc | at the 40 halts p50 / p75 / p90 / max | halts over 40 u |
|---|---|---|
| the tape's world-0 (truth; not available live) | 11.6 / 17.7 / 22.8 / 57.3 | 1 |
| **the last accepted report while STANDING, the AgTrack mirror while MOVING** | **17.5 / 38.0 / 78.3 / 488.0** | **9** |
| the AgTrack mirror alone (seeded as the live guard is) | 24.3 / 80.4 / 110.0 / 488.0 | 17 |
| `state["pos"]`, the report track | 41.8 / 106.3 / 173.8 / 510.5 | 20 |
| the last accepted report, always | 50.7 / 184.4 / 324.2 / 465.5 | 22 |
| *the pre-Q1 integrator, for scale (F1)* | *53.8 / 113.4 / 193.3 / 525.9* | *26* |

"Standing" is derived from ANIMREF-RE §40.11's measurement — the player's world-0 and drawn body
sit 0 u apart when standing — and the server knows it from the last accepted report being a
`0x0047`. The hybrid's error against the true world-0 is p50 0.0 u over all samples (p90 33 / 61 /
53 per run); the mirror alone is p50 20–30 u even standing, because on `R2` it sat **91.0 u from
world-0 for the last 25 s** of the run with the player parked, and while moving it is p50 19–22 u,
p90 58–78. That residual is the mirror's, not this arc's — **NPCTRACK-Q2**.

## NPCTRACK-F6 — what does NOT explain it, including two instruments of my own that were wrong

- **The client's handoff** — refuted by F2.
- **Our halt cutting the walk short** — a quarter of halts (F3), not the mechanism.
- **"Aim the server's copy at the ordered point instead of the live player"** — this was the first
  candidate, and a hand-written 20 ms integrator scored it as no change against today's rule.
  That integrator reproduced the client's copy only to **16 u p50 with a 143 u p90 tail**, and it
  ranked the frames the wrong way round (it put the mirror *below* today's integrator). It is
  superseded by F4 and none of its numbers are cited. The aim IS half of the client's rule; alone
  it is not the fix, because the frame is the other half.
- **The payload** — `GROUNDZ-Q6` already measured that no point the server could send sits on the
  drawn body; this arc says why: the server's copy was in the wrong frame.

## NPCTRACK-F7 — Q1 SHIPPED: the server's copy of a hostile is the client's own model

`toolkit/authsrv/authsrv.py`, `NPC_CLIENT_MODEL = True`, revert `--no-npc-client-model`.

- **The copy is a `SyncAgent`** per hostile, seeded at `agent["pos"]` and re-seeded whenever
  anything else moves `agent["pos"]` (a respawn), driven by the follow's own five send sites
  (`_send`): the opening follow, the re-path, the speed, the halt and GROUNDZ-F9's correction.
  Its clock is the follow's own integrated elapsed time, which is what the server's step has always
  been measured in and what every chase fixture fakes by rewinding `moved_at`.
- **The disc stop** is solved on the leg's own line (the first instant the copy is within
  `follow_stop_radius()` of the frame point and has it inside the cone), which is exact where the
  client's per-frame check is 16 ms coarse; the copy is placed ON the disc.
- **The frame** is F5's hybrid: `state["last_report"]` when it was a stop and no click leg is in
  flight, else the guard's `mirror.sync.position()` under the guard's lock, else `state["pos"]`.
- **Arrival is the model parking** — disc, point or halt. The `0x0028` still waits for the
  half-second clock (§40.9), so it lands on a body the client has already stopped, which is
  retail's shape (§40.2: p50 0.496 s after the last follow, a no-op on a parked body). A copy
  parked OUT of reach halts on the clock and gets a fresh follow on the next tick — retail's
  chase 3 (*"a halt, then a fresh follow 0.23 s later"*), never a re-path per tick.
- **Nothing changes on the wire.** Same follows, same re-paths, same halts. What changes is where
  the server believes the hostile stands.
- **The corridor router (1z-by) now exists only on the revert arm.** The client's sync copy
  dead-reckons straight (the drawn body paths, F2), so under the model there is no corridor to
  walk and no wedge to escape; `section_follow_router` and
  `studies/movecode/review/followroute.py` pin that arm explicitly. The chase section's wall pin is
  split the same way: the corridor arm is stopped by `clip`, the default never asks.
- **Tests:** `test_agentlife.py` `section_client_model` (20 checks: the standing case reproduces
  the chase section's own 80 u; the divergence the tapes measured — a frame 300 u aside and the
  copy walks to the ordered point where the revert arm parks 80 u from the server's player; the
  cone; each message as the client applies it; the re-seed; all four frame branches; parked out of
  reach), plus the wall split. Floor 294 → 315 from a real green run of 331.

**Desk prediction for the run:** copy-vs-client-sync at the halts p50 ≈ 17.5 u (F5's hybrid)
against the measured 53.8, over-40 halts ≈ 9 / 40 against 26 / 40. `RUN-NPCTRACK-R1` is
registered on those numbers; until it runs, Q1 is derived and desk-validated, not confirmed.

## Open

- **`NPCTRACK-Q2` — the AgTrack mirror's POSITION fidelity, handed to MOVECODE.** The mirror was
  built and validated for snap VERDICTS; as a position it is p50 19–22 u from the client's world-0
  while the player moves, p90 58–78, and on `R2` it stood **91.0 u off for 25 s** after the last
  walk (raw world-0 (11304, 9151) against the mirror's (11223, 9108)). It is the whole residual
  between F5's hybrid (17.5 u) and the truth (11.6). `review/npcdrift.py` prints the comparison
  per run; `scratch/mirrorcheck`-style per-second traces showed the error opening on the first
  grant of each walk and closing to 0 at the next stop until that last one.
- **`NPCTRACK-Q3` — the sync copy against the drawn body ACROSS AN OBSTACLE.** F2 holds on the
  stairs route, whose walls are the staircase sides. On the operator's bridge session the two
  still agreed to 28.8 u at the halts, but en route around the wedge is unmeasured, and a sync
  copy that dead-reckons straight through a wall while the body paths around it is what the
  decode says should happen. Only a wedge run with the tape can say how far apart they get.
- **`NPCTRACK-Q4` — the resolver's velocity extrapolation of the target** (§38.2: *"the client
  tracks a moving target only through the velocity extrapolation inside the reach test"*). F4's
  model has none and reproduces the tape to 10 u, so its horizon is short or its effect small;
  unmeasured.
- **`NPCTRACK-Q5` — the operator's picture is still world-0's.** The drawn hostile parks 80 u from
  the player's WORLD-0 copy, and that copy is p50 34 / 23 / 40 u from the drawn player while
  moving on these runs (p90 284 / 91 / 247). Q1 makes the server agree with the client about
  where the hostile stands; it does not move the hostile closer to where the operator is looking.
  That is MOVECODE's two-world problem, unchanged.

## Runs

- **[RUN-R1.md](RUN-R1.md)** — registered, not run. The stairs route a fourth time, scoring Q1
  against F1's 53.8 u with `--no-npc-client-model` as the control.

## Method notes

- **RUN-R2's tables are in CAPTURE seconds**, and the tape's own clock starts 1.16 s later; the
  90 ms claim there holds in wall time (the plane word changed +43 ms after the correction's
  send). Cosmetic, recorded rather than rewritten.
- **Two of my own desk instruments were wrong before the client's equations were tried** (F3's
  first cut census, F6's integrator). Both were replaced by measurements the client's own decoded
  code produces. The pattern is the standing one: reproduce the thing itself before reading any
  counterfactual off a model of it.
- **The review tool's positive control is the pinned-tape pair** — F4's model must land ≤ 20 u
  from the client's copy AND the pre-Q1 integrator ≥ 40 u from it. A scorer that fails either
  cannot be trusted on R1.
