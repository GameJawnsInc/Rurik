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
| the AgTrack mirror alone (seeded as the live guard is; replay ticked to the tape end, F10) | 20.9 / 59.7 / 110.0 / 488.0 | 14 |
| `state["pos"]`, the report track | 41.8 / 106.3 / 173.8 / 510.5 | 20 |
| the last accepted report, always | 50.7 / 184.4 / 324.2 / 465.5 | 22 |
| *the pre-Q1 integrator, for scale (F1)* | *53.8 / 113.4 / 193.3 / 525.9* | *26* |

"Standing" is derived from ANIMREF-RE §40.11's measurement — the player's world-0 and drawn body
sit 0 u apart when standing — and the server knows it from the last accepted report being a
`0x0047`. The hybrid's error against the true world-0 is p50 0.0 u over all samples (p90 33 / 61 /
53 per run); the mirror alone is p50 19–26 u while moving, p90 58–95. (This paragraph first said
the mirror "sat 91.0 u from world-0 for the last 25 s" of R2 — that was the offline replay
stopping its ticks at the last event, corrected in F10; the live mirror never had it.) That
residual is the mirror's, not this arc's — **NPCTRACK-Q2**, and F10 reads it off the tape.

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
  parked out of reach of the server's player halts on the clock; whether a fresh follow then
  opens is F8's rule, below — the first cut opened one on the next tick and RUN-R1's wire
  showed why that is wrong.
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
against the measured 53.8, over-40 halts ≈ 9 / 40 against 26 / 40. **RUN-R1 measured 11.8 u and
4 of 23 at the halt's own instant (F9)** — inside the desk prediction — and 76.6 on the metric as
registered, which turned out to measure the re-follow.

## NPCTRACK-F8 — RUN-R1's wire: the open rule must run in the client's frame too

RUN-R1 ran on 2026-09-06 at 09:23 **without its tape** ([RUN-R1.md](RUN-R1.md) RESULT) — the tape
tool crashed at `open()` because the runsheet named a directory that did not exist and the tool
only created its default one (fixed in `agenttap.py`; the sheet's first write-up blamed the
command for not running, wrongly) — so P1–P3 have zero trials. The capture alone caught a regression: **37 halts and 37 fresh follows in 77 s
against 13 on every pinned run, 27 of the 37 halts with the copy more than 92 u from the server's
player against 0 of 40 before**, and seven halts at one point in 3.4 s.

**The mechanism is a silent keyboard leg.** At t=25.34 the client sent one heading; the server
answered with a lead grant 108 u ahead and armed its keyboard leg; then no report for five
seconds, and the stop that ended it reported the same point — the body never moved (the route's
W leg into the staircase side). The server's report track dead-reckoned `state["pos"]` 604 u
ahead of the body; the client's world-0 copy sat at our lead point, 56 u from the hostile's copy.
**The model parked at once in that frame, as the client's resolver would** (inside 80 u, inside
the cone) — faithful. The follow-open test, unchanged from the old integrator, then read the
report track 537 u away and opened a fresh follow, which parked at once again, every half second.
The pinned runs had the same silent stretch (RUN-R2's T1 = 317 u at its t=26.87); the old
integrator hid it by walking its copy to 80 u from the fictional player and swinging from there.

**The rule, shipped the same day:** a copy already inside the swing reach of the CLIENT's frame
AND inside the ±60° cone of the leg it would be ordered — the exact question `_npc_disc_hit_ms`
asks at a leg's first instant — is **not re-followed until that belief moves**, and it does not
swing either, because the swing reads the server's own player. During the mismatch the hostile
stands where the client draws it, which is the honest picture. Retail never meets this case:
its server's player copy IS the frame. Ours has two, and this is where they disagree
([NPCTRACK-Q5](#open)). A frame point BEHIND the copy does not hold it, for the same reason it
does not park it (the cone) — the first draft of the rule forgot the cone and the test's own cone
check caught it. The model now records every disc park (`npc_model act=disc`, with the frame it
used) and every hold (`act=hold`) into the capture, so a park can be explained without a tape.
`test_agentlife` `section_client_model` pins the hold, the no-swing, and the release; green 333.


## NPCTRACK-F9 — RUN-R1 with its tape: the copy stands where the client's does, and my comparator did not

RUN-R1 ran a third time on 2026-09-06 at 09:43 with the tape ([RUN-R1.md](RUN-R1.md), second
RESULT). Two readings of one run:

| copy vs the client's sync copy | pinned runs (old arm) | RUN-R1 (Q1 + F8) |
|---|---|---|
| **at the instant the halt was sent** | 59.3 / 45.7 / 68.0 u p50; 26 of 40 over 40 u | **11.8 u p50; 4 of 23 over 40 u** |
| at the model's own disc parks (`npc_model` rows) | — | **9.3 u p50, max 77.8, n = 21** |
| 0.5 s after the halt — **the metric P1/P2 were registered on** | 63.3 / 47.9 / 56.0 | 76.6 |
| the client walking within 0.5 s of the halt | 4 / 4 / 4 | 17 of 23 |

**P1 and P2 as registered are REFUTED, and the registered metric is what failed.** It read the
client half a second after the halt, which was fair on the corridor integrator (the hostile then
stood and swung) and measures the re-follow under the model (F8's hold releases the moment the
client's frame is out of reach, and a fresh follow goes out 0.05 s after the halt whenever the
player kept moving). At the instant the server acted, the drift went from 46–68 u to 11.8, and at
the parks the server recorded itself, 9.3. **Q1 is CONFIRMED on the instant the server acts, and
the registered prediction is recorded as failed** — a parked-run comparator, written by the author
of this repo's own note on parked-run comparators. The review tool prints both metrics and the
walking count; P1′/P2′ are registered on the instant metric for the control run.

**P3 MET:** 0 of 23 halts landed on a walking client copy (10 of 40 before). **P4b REFUTED with
its reason:** 15 of 23 halts had the copy more than 92 u from the server's player — the frame
mismatch made visible, not a loop. While the player walks, the server's report track leads the
client's world-0 by ~100 u (the disc rows print both), the copy parks at world-0's disc as the
client's does, and the server sees it 180 u short. The old arm hid this by walking to 80 u from its
own player. The cadence it produces — halt, fresh follow 0.05 s later, park — is retail's mid-chase
halt (§40.2 chase 3) at a higher rate, because retail's server player IS the frame:
**NPCTRACK-Q6**. The two worst parks (77.5 / 77.8 u) are the two where the live frame sat 33–35 u
behind the true world-0 — the mirror's error, Q2, as F5 predicted.

**The control ran the same morning (10:06, `--no-npc-client-model`, agent-driven) and closes the
comparison:** same-instant p50 **54.8 u** on the old arm against **11.8** on the model, 7 of 12
halts over 40 u against 4 of 23, 3 of 12 halts on a walking client copy against 0 of 23, the wire
shape identical to the pinned runs (12 / 39 / 12), and F4's model reproducing that tape's client
copy to 10.2 u — a fourth tape. **Q1 is CONFIRMED with a control.** The registered +0.5 s metric
read 21.6 u on the control — it would have passed the OLD arm — so it is unreliable in both
directions and is retired from the verdict lines. One caveat the control raises rather than
settles: the drawn hostile parked closer to the drawn player on the old arm (83.5 u against 101,
one run each); what the operator sees behind a running player is the model arm's re-follow
cadence (Q6) against the old arm's swing from an imaginary spot, and only their next session can
rank those.


## NPCTRACK-F10 — the mirror's residual, read off five tapes: one artifact of mine, three real sources, one refuted repair

**First the artifact.** F5's "once 91 u standing for 25 s" and Q2's copy of it were my replay's,
not the mirror's: the offline replay stopped ticking at the capture's last event, so the leg the
stop-echo grant had armed never arrived and the trace held its pre-arrival point for the rest of
the tape. The live guard ticks every world tick. The replay now ticks to the tape's end
(`review/npcdrift.py`), and with that the mirror's error against the true world-0 is **p50 0.0 u**
on all five tapes (1zCA, GROUNDZ-R1, GROUNDZ-R2, RUN-R1, its control), p90 30 / 63 / 44 / 74 /
92, max 107–152. F5's mirror row becomes 20.9 / 59.7 / 110.0 at the halts (14 of 40 over 40 u);
the hybrid row is unchanged, because it already used the stop report while standing.

**Then the real sources, each located to the sample.** A jump census (the error growing by more
than 20 u between two tape samples) over the five tapes puts every jump inside 0.35 s of one of
three things, all under an OPEN fence during a keyboard walk:

1. **The first press.** At t≈9.0 on every run the client's world-0 has our lead point as its
   destination (`tx,ty` = (10248, 8077)) but a velocity of (0, 288) — it walks **+y**, the body's
   old facing, for a 312 ms / 90 u leg, then at that leg's arrival tick re-bakes toward our
   destination ((282, −60) toward (10248, 8077)). Our `0x0025` said (1, 0). The mirror bakes toward
   the lead at once and leads world-0 by the turn's cost: 52 → 104 u over 0.3 s, decaying.
2. **A body that cannot move.** At t≈25.5 on every stairs run the W press is into the staircase
   side: one `0x003D`, our lead grant 108–132 u ahead, then no report for five seconds and a
   `0x0047` at the SAME point. World-0 never moves (`v0 = 0` throughout, destination written).
   The mirror walks the lead's full length in 0.46 s and waits there: 57–132 u for the whole
   silent stretch. (The server's own report track meanwhile dead-reckoned 604 u through the wall —
   a keyboard-arc defect, flagged separately.)
3. **Held-heading grants** (the zero-lead at each report while walking): world-0 walks a short
   leg to the report point and parks there with velocity 0 until the next one; the mirror does
   the same from its own settled point. ≤ 30 u for under 0.2 s, on both sides of zero.

**The rule the samples support, stated so it can be refuted:** for the controlled agent under
an open fence, a `0x0029` writes the OUTSTANDING destination; the copy takes it up at its next
arrival tick, the end of whatever leg it is on; a local move event (the press, each subsequent
report) arms a short leg of the client's own toward the body's near position; and a copy with no
leg in flight has no next arrival, so a body that cannot move leaves world-0 frozen with our
destination written and unwalked. **OBSERVED on the tape at the sample level, CONTESTED against
[studies/movecode/FINDINGS.md](../movecode/FINDINGS.md)'s write-set reading that "the client
never carries world-0 forward from local input"** — the (0, 288) leg at 9.06 has epoch 8135,
before our grant reached the client, and no message of ours carries +y. **CORRECTED BY F11, the same
day:** the +y leg is a wire-driven bake after all — the shared setter's own obstacle avoidance
sidestepping the parked hostile, 66 ms after our grant, on the tape clock's 55 ms offset — so the
"local leg" reading above is withdrawn and the movement arc's write-set stands. What survives of
this paragraph is the observation, not the rule. **And item 2's "destination written" is wrong
too** — the tape holds the invalid-position sentinel on both copies for the whole silence; the
destination was never installed (movecode §1z-cd, and Q2's entry).

**One repair, refuted offline before it was built.** "Defer every grant's bake while a gesture is
pending, take it up at the next report or arrival" — replayed on the five tapes it is three to
six times WORSE (moving p50 86–140 u, p90 276–517 against the mirror's 21–26 / 64–95): during a
normal walk world-0 does walk toward our leads, and a mirror that waits falls a report interval
behind on every leg. The two real sources above are a turn the server cannot see and a wall the
client does not report; neither is a bake-timing rule. **Q2 stays open with these numbers**, and
what would close it is the client's own local-leg model (the facing, the turn rate, the first
waypoint) — MOVECODE's dig, not a tuning knob here.


## NPCTRACK-F11 — the first-press excursion is the client sidestepping the parked hostile

F10's first real source, read to the field on the tape and matched to the movement arc's own
decode. It is not a bake-timing rule, it is not a local leg, and this arc has the inputs.

**The sidestep.** At every first press the sync copy first takes our lead as a straight hard leg
(R1: `seg = tgt = (10248, 8077)`, `v = (288, 0)`, arrival 1465 ms), and **66 ms later a second
bake replaces it with a 90 u perpendicular leg carrying the waypoint bit** (`flags 0x60005`,
bit 18 set; `seg = (9845, 8167)`, `tgt` unchanged, `v = (0, 288)`, 312 ms). At that leg's end a
hard bake resumes toward the target. This is
[studies/movement/FINDINGS.md](../movement/FINDINGS.md)'s corroborated sidestep computer
`0x00600500` (`AgAgent.cpp:1261`, `MathSqrt(combinedRadiusSq) + 1.0f >= distFromLine`), reached
from the shared setter's obstacle avoidance `0x00600840` at `0x00602AEB` — *"setting a
destination, from either world copy, runs avoidance immediately"* — and the obstacle is the
**parked Hatcher, standing 80 u ahead exactly on the line to the lead**. Wire-driven, then: F10's
"local leg" reading is withdrawn and the movement arc's write-set stands.

The geometry the decode states, checked on all **18 waypoint legs across five tapes** (bit 18
rising with a finite segment): the waypoint is the start point displaced perpendicular to the
velocity, **away** from the obstacle, by `(combinedRadius + 10) − |distFromLine|`, with
`combinedRadius = 12 + 12 + 56 = 80` — the follow's own disc. Every first press is 80 + 10 − 0 =
89.9 u with the hostile 0.0 u off the line; the others fit to within 3 u (63.2 → 29.4 measured
against 26.8; 47.0 → 45.2 against 43; 53.7 → 36.4 against 36.3; 7.3 → 82.5 against 82.7; 59.8 →
30.4 against 30.2); a tie at 0.0 goes left; one leg of 18 (R2 at 38.79, obstacle behind) does not
fit and is presumably a different obstacle. **16 of 18 legs have the hostile within 60 u of the
copy's line, the other two at 61 and 63.**

**What is NOT decoded is the trigger**, and two proxies for it were tried offline and are
recorded so nobody re-fits them: (a) "obstacle within 81 u of the line anywhere along the leg"
fires 5–11 times per run against the tape's 2–6 and worsens two runs' p90; (b) the same with an
"ahead, within 130 u" bound fires 5–9 and halves the first-press excursion (max 107 / 99 / 101 /
121 / 122 → 85 / 69 / 69 / 86 / 55 u) without closing it, because it also fires on grazing passes
the client ignores (e.g. the second lead at 9.57 with the hostile 79 u beside the line) and on
grants from a standing copy. The fired-versus-quiet census is the check any decode must pass:
**12 grants fired** (hostile ahead by 44–116 u, within 62 u of the line, 60–122 u away) and
**29 quiet grants** with the hostile ahead and within 81 u of the line — the quiet ones at small
`along` with the hostile beside the copy (7–25 u ahead, 75–80 u aside), from a standing copy
(24.1–24.5 s on three runs), or on the stairs where the sidestep point would fall off the
client's mesh (the computer validates its waypoint through `0x0070A150` and returns
`AGENT_INVALID_POSITION` otherwise). The caller's own test is a collision-time predictor —
`AgAgent:1352` at `0x006009C8`, *`(timeToEvent == HUGE_VAL) || (m_point.position !=
obstacleCenter)`*, with a constant at `0x00943898` and calls into `0x0070A0E0`, `0x0046E000`
and `0x00487BC0` in the 170 instructions read — and reading it is the next step, in the movement
arc where the function lives. **With it, the mirror can sidestep too, and the server has every
input: the hostile's position is the client's own copy since Q1.** *(CORRECTED in F14, the same
day: the caller that fires around a parked AGENT is the agent-avoidance pass `0x006011F0`
(movecode §1z-be.2), not `0x00600840`, whose predictor is the terrain trace; the trigger is
read there, and it is shipped.)*

**The wall was handed over and came back corrected the same afternoon**
([movecode §1z-cc, §1z-cd](../movecode/FINDINGS.md)). The 604 u the report track ran during the
silence was one missing keyword in one of the server's two navmesh clippers (1z-cc, shipped with
`test_kbdsync` §16). The reading this arc handed over with it — a plane-blind lead sent onto the
stair tread — is **refuted at 0 of 240** moving grants with the plane clip in force (1z-cd): the
granted point is on plane 0, the mover's own plane, one 2 u sample short of the seam, and F10's
"frozen with our destination written" was wrong too — the tape holds the client's
`AGENT_INVALID_POSITION` sentinel on both copies for the whole silence, **the destination was
never installed**, which is the client's own pathfinder refusing to path into 104 u of plane-0
ground our mesh carries as open. Prop geometry we do not carry, in the pathmap's court; Q2's
entry below has the whole correction.

**What this leaves for the NPC frame.** The mirror's remaining excursions are bounded and
located: ~100 u for 0.3 s at a press toward a parked hostile (until the sidestep is modelled),
the lead's length for a silent leg the client refuses to path (until the mesh carries the prop),
and ≤ 30 u held-heading transients. Q2 stays open on the predictor only.

## NPCTRACK-F12 — RUN-R2: Q1 holds a second time, and 1z-cc reaches this arc's wire

[RUN-R2.md](RUN-R2.md). On the tree after the keyboard arc's clip fix: **6.7 u** at the halt's own
instant (R1 11.8, the old arm 54.8), 4 of 23 over 40 u, the wire shape identical to R1's. During
the silent leg at the staircase side the server's player copy now stops 98 u from the body
instead of 604, and the hostile **swings four times** at a player standing beside it instead of
holding out of reach for five seconds. One registered prediction is refuted as written, P3 — 5 of
23 halts on a walking client copy by the tape's instrument — and F13 (withdrawn) explains why that
instrument over-reads on this arm; the hook's client-side count is 2 of 15.

## NPCTRACK-F13 — WITHDRAWN the same afternoon: "the client's follow re-targets itself" was my join artifact, and RUN-R3's hook says so

**What was claimed** (committed at `5c90065`, two hours before this): that the Hatcher's sync
`m_targetPoint` changed 24 / 19 / 23 times over three tapes with no server order within 0.35 s,
at a 0.56 s cadence, landing 144 u from our last ordered point — a client-side follow re-target,
contested against ANIMREF-RE §38.2's *"no local chase"*.

**What was wrong: the join window.** I searched for an explaining order only in the 0.35 s
BEFORE each tape event. The capture stamps a send when the server's recorder writes the row,
which on these three tapes is **−67 ms to +38 ms** (p10..p90, p50 −11 ms) around the sample in
which the client already shows the order applied — the stamp can trail the client. With a
symmetric ±0.2 s window the count is **0 / 0 / 0**. The "0.56 s cadence" was our own re-path
interval, the "144 u from the last order" was the distance between consecutive re-path points at
288 u/s, and the "0.5 s after our last order" was the next order, stamped a few tens of
milliseconds after the tape showed it. [RUN-R2.md](RUN-R2.md)'s window at 12.88–13.95 s shows it
line by line.

**What the hook says** ([RUN-R3.md](RUN-R3.md), the route under `movehook`, agent-driven): with
the tape's own pointers naming the two objects (sync `0x27ADFD38`, async `0x27ADDAA0`), **every
setter and bake on the sync copy returns to the `0x002A` wire handler — 26 of 26** — and the async
copy's 41 setter calls return to `0x00604A48`, inside AgTrack: the handoff that drags the drawn
body after the sync copy, plus three path-solver re-bakes. No non-wire caller touches the sync
copy. **§38.2 stands, and the movement arc's decode was right where my tape read was wrong.**

**What survives, and it is P3's instrument that changes.** RUN-R2's five "halts on a walking
copy" are this artifact in another dress: under F8 a fresh follow trails the halt by 50 ms, and
the last tape sample before the halt's stamp already shows the fresh follow's leg. The client's
own evidence is the hook's teleport census on the sync copy: **our halts landed on a parked body
13 of 15 times and cut a walk 2 of 15** (the resolver's own disc parks are the other 13
teleports, from `0x0060181C`, and one is the tick's arrival). So the tape's "walking at the halt"
column is good to ±70 ms and no better, which is fine on the old arm (the next order came ≥ 0.5 s
after a halt) and not fine on this one; `review/npcdrift.py` says so on the line it prints, and
the hook is the instrument for P3 from here. Q7 is withdrawn.

**The lesson is the note this repo already has** ([[feedback-validate-the-simulator-against-the-
thing-itself]]): a claim about the client from a join of two clocks needs a symmetric window and
the client's own instrument before it is a claim. This one was two hours old and cost one hooked
run to retract, which is the cheapest version of the mistake.

## NPCTRACK-F14 — the sidestep's trigger DECODED and SHIPPED: it is the client's agent-avoidance pass, and the same pass is what halted the copy at the wall

F11 left one thing unread — the trigger — and named the wrong function for it. The sidestep
computer `0x00600500` has two callers, and the one that fires around a PARKED AGENT is the
**agent-avoidance pass `0x006011F0`** (movecode §1z-be.2's decode: the shared setter runs it at
`0x00602AF8` right after the bake, args `(time, &m_point, 1, 0)`), not the terrain-avoidance
sibling `0x00600840` F11 pointed at (whose `AgAgent:1352` predictor is the swept TERRAIN trace,
0 fires in every hooked capture). This session read the pass's tail and the tick's re-run, and
the whole trigger is now on record. Per other agent in the same world, in this order:

1. the copy must be walking (`+0x48` armed, `0x006016AA`) and the point must differ from the
   obstacle's (`0x006016C5`);
2. **closing**: `rel · relv > 0` with `rel = other − point`, `relv = v_other − v_this` skips
   (`0x0060164E`, arg4 = 0 at both the setter and the tick) — a parked agent behind is
   separating, one ahead is closing;
3. **the cone**: `unit(rel) · unit(v_this) > 0.5` (`0x00601791 fcomp [0x009458BC]`), the same
   60° the disc stop uses;
4. **overlap**: `combinedRadius² ≥ d²` (`0x006017BC`, `0x005FED20` → 80 u for two radius-12
   agents on layer 0). **Not overlapping → a deadline**: `0x005FEEC0` solves
   `|rel + relv·t| = R` (`t = (−c − √(c² − a′b)) / b` with `a′ = d² − R²`, `b = |relv|²`,
   `c = rel·relv`, +INF when `b = 0`, the discriminant ≤ 0 or `t < 0`), the running minimum
   goes to `+0x44` as `time + max(min(t × 1000, 60000), 1)` (`[0x00943898]` = 1000.0,
   `[0x00A53750]`/`[0x00A53758]` = 60000, `0x006019C6 ftol`), and the tick calls the pass again
   when it is due (`0x00600495`–`0x006004BF`, arg3 = 1). Since the deadline lands at contact
   and the tick re-arms 1 ms when it finds `d` a hair over `R`, **the sidestep fires on the
   first world-0 tick with `d ≤ R`** — which is what a per-tick pass reproduces.
5. **On overlap**, the computer's exits in the client's order: the obstacle is our TARGET agent
   → notify 5 + park (the disc stop, `0x0060181C`, Q1's); we are already at `m_targetPoint`
   (`0x0060182D`) or the retry counter `+0x64` has passed 6 (`0x006018B8`) → halt; the
   obstacle's disc **covers `m_targetPoint`** (`0x006005D8`, before any query) or the waypoint
   fails the mesh (`0x0070A150`) or `stepclear` → `AGENT_INVALID_POSITION` → **halt in place,
   `0x00601899`** (teleport to the point, velocity zero, both target blocks invalid; notify 4 on
   world 1 only); else **bake the waypoint with isWaypoint = 1** (`0x00601936`), then terrain
   avoidance and `0x005FFCB0` on the new leg. At the waypoint's arrival the tick finds bit 18
   set and re-bakes toward `m_targetPoint` with isWaypoint = 0, no notify (`0x0060029F` →
   `0x006002B5`). The setter clears bit 18 and every bake resets `+0x64`, so a wire grant
   mid-sidestep re-aims from the dead-reckoned point and runs the pass afresh.

**The census that accepts it — seven tapes, 232 player grants** (the three pinned runs, R1,
R1's control, R2, R3), the pass replayed on the mirror's sync copy against the hostile's sync
copy off the tape, scored against every waypoint leg the tape shows (bit 18 rising or its
epoch changing, finite segment):

| | fired both | model only | tape only | quiet both | halts predicted | halts the tape confirms |
|---|---|---|---|---|---|---|
| pooled | **24** | 1 | 1 | 206 | **14** | **14 of 14** |

Waypoint error at the matched fires **p50 0.2 u** (the first presses, fired AT the setter with
the hostile 64–75 u dead ahead), p90 13.8, max 15.3 — every error over 5 u is a deadline-driven
fire where the client's copy stood 9–15 u further along than the model's at the bake, i.e. the
client fired **one world-0 tick after contact**: the tape's `clock0` steps **100 ms** (sometimes
50) on r1/r2/r3, so a fire lands 0–100 ms after contact and this mirror fires at contact.
MEASURED, not modelled (the tick's phase is unknown). The one disagreement is one event: on
GROUNDZ-R2 the client's tick at ~37.56 s fired with the 37.606 s grant already applied (a 46 ms
stamp lag), the model fired at contact 37.515 with the old target and again after the grant —
15 u for 0.3 s, then the cascade's one missed short leg. The model-only/tape-only pair are that.
Everything F11 called quiet is quiet for a reason the pass names: beside the copy (7–25 u
along, 75–80 aside) is **outside the cone** (cos 0.09–0.31); from a standing copy `+0x48` is
not armed; the stairs never reached the mesh check on these tapes (the `--mesh` arm changed
nothing).

**And the hook agrees, which is the instrument the tape is not.** RUN-R3's `movehook` window
holds agent 1's sync object (`0x2614F640`) for 32 s: 17 setter calls, **exactly one bake
returning to `0x0060193B`** — the sidestep at 46.5 s, `pt (9275, 7900) → tgt (9795, 7900)`,
with its waypoint re-bake `0x006002BA` (flags `0x00060005`, bit 18) 312 ms later — and
**exactly one teleport returning to `0x0060189E`**, at the wall lead
`(10029, 8540) → (10105, 8540)`, in the same millisecond as its setter and bake, **with no
`stepclear` and no `mapfindpath` record between them**. The model fires once and halts once in
that window, at those two grants, and nowhere else.

**THE HALTS ARE THE WALL SILENCE, and this corrects three documents.** All 14 predicted halts
are the computer's first exit: **our lead's endpoint lay inside the parked hostile's 80 u
disc**, so the client halted the sync copy in the setter's own call and the target block never
outlived the millisecond. R1's specimen (cap 25.4212, the grant `(10118.5, 8526.5)` with the
hostile at `(10076, 8556)`): **51.7 u** from the target; R3's: 35 u; R1's control run halted
seven times this way in its chase phase, with 50–160 u leads ending beside a hostile walking
in. The tape confirms each halt within one sample (velocity zero, both target blocks at the
sentinel, `stop = 0`). So F10's *"frozen with our destination written"*, 1z-cd's *"the
client's pathfinder declined to produce a path"* and this arc's Q2 entry (*"104 u of plane-0
ground the client will not path into — prop geometry we do not carry"*) are all the same
misreading: the destination WAS installed, and what stopped world-0 was the hostile's
collision disc around the lead's END, the exact class 1z-cd downgraded because *"a cylinder in
the way does not leave the target unset"* — it does, when it covers the target, because the
halt invalidates both blocks. 1z-cd's registerable question (*"would it have installed a
SHORTER one?"*) is answered from the bytes: the refusal is about the endpoint. The drawn body
stood too because its own quarterstep (16 u, the hostile 80 u off at 24.8°) is the same pass on
world 1 — 1z-be.3's run-2 S press, *"target covered → no sidestep → notify 4"* —
RECONSTRUCTION for world 1 on that run, OBSERVED for world 0. The mesh is not implicated by
this specimen; a correction is appended at movecode §1z-cd.3.

**What shipped** (`MIRROR_AVOID`, revert `--no-mirror-avoid`, in the capture header):
`agtrack_mirror.SyncAgent.avoid` transcribes the pass (steps 1–5, `AVOID_*` constants cited),
`bake_waypoint` / `consume_waypoint` / `avoid_halt` the three writes, and `AgTrackMirror` runs
it at `on_grant` (the setter's call) and on every walking tick; `AgTrackGuard.set_obstacles`
feeds both mirrors, and `authsrv._npc_obstacles` answers with every other agent's **client
model** — the hostile's SyncAgent since Q1, so the obstacle is the copy the client actually
avoids — or its server position standing. `test_agtrack_mirror` §17 (68 → 92) pins every tape
shape including the revert arm and a no-provider vacuity control; `test_agtrack_guard` §15
(81 → 89) the feed and the provider. The stepclear query (`0x005FEF70`) inside the computer is
not modelled; other radii/layers are UNMEASURED and take 80; the hostile's own copy gets no
pass (nothing on these maps for it to avoid).

**What it buys the frame (Q2), like for like on the seven tapes through the shipped code,
obstacles = the tape's hostile copy:**

| | pass ON | pass OFF (the revert arm) |
|---|---|---|
| mirror vs the client's world-0 while MOVING, p50 / p90 / max (n = 1,509 samples) | **10.1 / 19.9 / 105** | 14.8 / 89.3 / 150.9 |
| per run, p90 | 16–25 | 76–105 |
| the hybrid frame at the 120 halts, p50 / p75 / p90 | **1.5 / 9.4 / 17.6** | 3.6 / 17.4 / 49.9 |

F10's ~100 u first-press excursion is gone (the per-run maxima 25–36 u, one 105 = the cascade
above); the wall silence's mirror walk is gone (the mirror halts where the client does). What
is left of Q2 is the tick phase (≤ 29 u for ≤ 100 ms at 288 u/s), the mesh/`stepclear` arm
these tapes never exercised, and 1zCA's one 357 u halt that both arms share and that is not
this mechanism.

**OUT OF SAMPLE — [RUN-R4.md](RUN-R4.md), 2026-09-06 15:13, the same route on a tape the
pass had never seen:** 3 of 3 sidesteps matched (waypoint error ≤ 0.3 u), the one predicted
halt confirmed (the wall lead ending 48.5 u from the hostile), mirror vs world-0 while moving
p90 **25.1 u**, Q1 at 9.1 u, zero `0x002C`, the wire shape unchanged. Twenty-seven sidesteps
and fifteen halts reproduced against two disagreements over eight tapes.

## NPCTRACK-F15 — the client parks the hostile INSIDE the disc, by its next tick's worth of walking; Q1's residual is that, derived, and Q4 closes with it

F14's pass is also the hostile's own disc stop — its target-agent exit (`0x0060181C`: the
blocker is the agent in `+0x98`, notify 5 and park at the copy's own point). The server's Q1
model parks the copy exactly ON the 80 u disc, solved on the leg's line (`_npc_disc_hit_ms`).
The client cannot: its pass runs at the world-0 tick, the deadline it armed at the setter lands
at contact, and the park is the copy's dead-reckoned point at the first tick that finds
`d ≤ R` — so the client's park should sit INSIDE the disc by whatever the copy walked between
contact and that tick, and never outside it. A prediction with a sign and a bound.

**MEASURED on the seven tapes** (`studies/npctrack/review/parkcensus.py`): 185 stops of the
hostile's sync copy, of which 61 are our own `0x0028` landing on a walking copy and 21 are
arrivals at the ordered point (the tick's `0x00600333`, the copy on its previous target); the
**103 disc parks** that remain, by the player's state at the park:

| player | n | d to world-0: p10 / p50 / p90 | min / max | inside the disc (80 − d) |
|---|---|---|---|---|
| STANDING | 37 | 63.8 / 71.1 / 79.6 | 61.8 / 84.9 | **mean 8.4 u**, histogram [0,5) 8 · [5,10) 14 · [10,15) 9 · [15,20) 5, one at −4.9 |
| moving | 66 | 76.9 / 84.2 / 92.4 | 60.2 / 96.1 | the 33 ms sample lags the park and the player walked on |

At a standing player **36 of 37 parks are inside the disc** (the one outside, by 4.9 u, is a
player whose world-0 the tape read 33 ms after the park), and the depth is 0–18 u: the sync copy walks 0–63 ms past contact before its tick parks it. So
**Q1's number — 6.7 / 11.8 / 15.7 u median at the halts, and RUN-R2's "the model's own parks
vs the client's copy, p50 7.5" — is this**: the model stops on the disc, the client 8 u short of
it on average, and the rest is F5's frame. It is the floor of what the server can know: the
tick's phase is the client's, invisible from the wire. (An estimator that parks the model half
a tick inside the disc would zero the MEAN error; it is not built — the 8 u is invisible to the
player and a fudge of the mean is not a derivation.) The 100 ms step the tape's `clock0` shows
does not put a bound of 29 u on this: the depth's maximum is 18 u, so the tick that runs the
pass is finer than the clock's coarsest step (the tape also shows 50 ms steps); UNVERIFIED
which, and it does not matter to the server.

**Q4 closes on the same decode.** §38.2's *"velocity extrapolation inside the reach test"* is
F14 step 4: the other agent is dead-reckoned to the tick's time from its own `+0x78/+0xB0/+0x58`,
the deadline is the quadratic on `rel + relv·t` with `relv = v_other − v_this`, and the park
happens at the first tick with `d ≤ R` on those positions. F4's model has no extrapolation term
and reproduces the tape to 10 u because a standing or slowly moving frame makes the term small
(a head-on closing at 576 u/s would put the park up to 29 u deeper per 50 ms — one park at
60.2 u is the only candidate in the corpus). The server's `_npc_disc_hit_ms` already solves the
hit against the frame at each tick; nothing to change.

*RUN-R4 (registered after F15, run 15:13): 8 disc parks at a standing player, all inside the
disc, 64.4–78.6 u, mean depth 6.9 u; two moving-player parks read 98–100 u at the sample and
both are world-0's own sidestep after the park, the mechanism of F14 seen from the other side.*

## Open

- **`NPCTRACK-Q2` — the AgTrack mirror's POSITION fidelity, handed to MOVECODE.** The mirror was
  built and validated for snap VERDICTS; as a position it is p50 0.0 u from the client's world-0
  over five tapes, p90 30–92, max 107–152, and **F10 locates every excursion**: the first press's
  local leg along the old facing (up to ~100 u for 0.3 s), a body blocked by a wall while the
  mirror walks the lead (57–132 u for the silent stretch), and ≤ 30 u held-heading transients.
  (The "91 u for 25 s" this entry first carried was the replay's own artifact, F10.) It is the
  whole residual between F5's hybrid (17.5 u) and the truth (11.6). The one repair tried offline
  is refuted (F10). **F11 decoded the first-press excursion**: the client's sidestep around the
  parked hostile (geometry confirmed on 18 legs; the TRIGGER — the collision-time predictor in
  `0x00600840`, `AgAgent:1352` — is the one thing left to read, with a 12-fired / 29-quiet census
  as its acceptance test). With the predictor read, the mirror can sidestep, and the server has
  the inputs.

  **The WALL CASE half of that residual went to MOVECODE and came back REFUTED, 2026-09-06
  ([movecode §1z-cd](../movecode/FINDINGS.md)).** The reading taken over was that our
  `0x0029` names the stair tread — a point on plane 29 the client's own navmesh cannot reach
  from the ground through the staircase side — and that the lead should refuse or shorten a
  grant whose plane differs from the mover's. Scored on the real map-148 mesh at the specimen
  (`authsrv-20260906T094349-c1` t = 25.4197), **the granted point is on plane 0, the mover's
  own plane**: the grant is (10118.5, 8526.5) and `planes_at` there is `{0}`, one 2 u sample
  short of the seam at 10120.5, with `pm.route` returning a same-plane path because origin and
  destination are the **same trapezoid**. `A2_LEAD_PLANE_CLIP` has made a cross-plane grant
  impossible since 2026-09-04 (`pm.clip` only ever returns a sample it has already tested on
  the given plane), and the corpus agrees at **0 of 240** moving grants with the clip in force
  against **49 of 282** where it is reverted, bypassed or predates the flag — the positive
  control that makes the zero mean something. (Zero-distance leads are excluded from both:
  their destination IS the report, so cross-plane is impossible by construction, and counting
  them halves every rate.) So the lead is exonerated.

  **And the tape corrects THIS ENTRY'S OWN mechanism, in F10's item 2.** F10 reads *"world-0
  frozen with our destination written and unwalked"*. On `r1-agenttap.jsonl`, joined to the
  capture at `tape_t = cap_t − 0.95998 s`, **the destination was never written**: 19 of the
  run's 20 non-degenerate `0x0029` leads land verbatim in the client's own world-0
  `m_targetPoint` within −25..+49 ms, and the 104 u grant at cap 25.4212 is the one that does
  not — `grep` for `10118.5341796875` returns 0 over the whole tape, and no sampled value is
  within 2.0 u of it. Across all 55 samples of the silence **both** copies hold
  `m_segmentPoint` and `m_targetPoint` at the client's own `AGENT_INVALID_POSITION` sentinel
  (`(inf, inf)`, `toolkit/clientscan/movetap.py:524`), velocity `(0, 0)`, the drawn body at the
  report point to the bit and `ground_z` constant; no movement opcode goes out in the gap that
  could have cleared a target. **The numbers in this entry do not change** — the mirror still
  walks the lead's full 57–132 u while the body stands still — but "frozen with a destination"
  should read "frozen with NO destination", and that is a different fault with a different fix.

  What the wall case measurably IS, and it is still open: **the client's own pathfinder declined
  to produce a path.** A body that took a destination and was then blocked — by a wall or by a
  creature — would hold a target with zero velocity; holding the invalid-position sentinel with
  no segment at all is a refusal to path, §1z-bc's named `pathCount == 0` class. That
  substantially **downgrades the collision candidate**: agent 10 was 80.1 u away at 24.8° off
  the pressed heading and swinging in melee at that instant, but a cylinder in the way does not
  leave the target unset. What is left is a navmesh disagreement, and ours is the wrong one:
  our mesh holds **104 u of plane-0 ground due east** the client will not path into. The player
  stands +0.002 u from the west edge of a triangular trapezoid; the body moved 0 u across three
  east presses (t = 25.42, 32.14, 36.88) then **512 u south** without difficulty at t = 39.29,
  and on the north press our mesh independently answered 0.0 u and the server correctly granted
  a zero-lead. The leading reading is **prop geometry we do not carry** — the staircase side is
  a model, not a trapezoid, the residual `a2_clip_lead`'s docstring and §1z-cc both already name.

  **The run's question, registerable as it stands:** the client refused a 104 u destination
  outright. Would it have installed a SHORTER one — is the refusal about the endpoint being
  unreachable, or about the whole corridor? Nothing on the server side can answer it, because
  both readings predict the same wire, and the tape's own blind spot is the ~65–110 ms between
  the samples bracketing the grant.

  **CLOSED on both halves, 2026-09-06 (F14).** The first-press excursion's trigger is the
  agent-avoidance pass, decoded and shipped in the mirror (`MIRROR_AVOID`): the mirror's
  error against the client's world-0 while moving is p90 **19.9 u** over 1,509 samples against
  89.3 on the revert arm. And the wall half was never a navmesh disagreement: the lead's
  endpoint lay 51.7 u from the parked hostile, inside its disc, and the same pass halted the
  copy in the setter's own call — the "104 u of plane-0 ground the client will not path into"
  above is withdrawn as a mechanism (the ground may or may not be prop-covered; this specimen
  cannot say). What remains is the world-0 tick's phase (fires land 0–100 ms after contact,
  ≤ 29 u), the mesh/`stepclear` arm no tape reached, and one 357 u halt on 1zCA shared by
  both arms.
- **`NPCTRACK-Q3` — the sync copy against the drawn body ACROSS AN OBSTACLE.** F2 holds on the
  stairs route, whose walls are the staircase sides. On the operator's bridge session the two
  still agreed to 28.8 u at the halts, but en route around the wedge is unmeasured, and a sync
  copy that dead-reckons straight through a wall while the body paths around it is what the
  decode says should happen. Only a wedge run with the tape can say how far apart they get.

  **MEASURED on the eight tapes, 2026-09-06 (`review/copysep.py`), and the route already
  crosses the wedge tip and the staircase side:** 6,192 samples, separation p50 1.4 / p90 13.0
  / p99 20.2 / max 57.9 u; while either copy moves p50 4.9 / p90 13.4. The widest instants are
  the spawn chase's first second on six of eight tapes (the drawn body trailing the sync copy
  by 21–37 u — the AgTrack handoff's lag, ANIMREF-RE §37.2) and two old-arm transients at a
  park (52–58 u, one copy walking while the other stood). Nothing at the wedge or along the
  staircase side. **What this route cannot show** is a wall INSIDE the chord: the hostile
  follows 80 u behind the player along the walked polyline, so its straight leg is always the
  corridor the player just walked. Q3 stays open only for a route that puts a wall between the
  parked hostile and the player before the follow re-opens — the owner's mouse play showed
  28.8 u at the halts on the bridge, which is the nearest measurement there is.
- ~~**`NPCTRACK-Q4` — the resolver's velocity extrapolation of the target**~~ **CLOSED 2026-09-06
  (F15)**: it is the agent-avoidance pass's deadline on `rel + relv·t` with the other agent
  dead-reckoned to the tick (F14 step 4); small here because the frame stands or walks slowly
  at the parks. And the parks themselves land 0–18 u INSIDE the disc at the client's next tick
  (mean 8.4 u at a standing player, n = 37, 36 of 37 inside), which is Q1's residual, derived.
- **`NPCTRACK-Q6` — the mid-chase halt cadence.** Behind a running player the server's report
  track leads the client's world-0 by ~100 u, so the copy parks at world-0's disc every re-path
  interval, halts, and is re-followed 0.05 s later: 23 halts and 23 opens in 77 s against 13
  on the old arm (about the same message total, 84 against 76; nothing inside 0.4 s). Faithful
  to the client, noisier than retail, whose server player IS the frame and whose copy therefore
  never arrives behind a player running at its own speed. The lever is the frame (Q2), not the
  follow.
  **The corpus half, 2026-09-06 (after F14 closed Q2):** retail's follow point is *"the
  server's copy of the player: 12–32 u from my own last report when that report was under
  0.35 s old, 75–85 u when it was 0.5 s old"* (animref §38.3's ~74 u lag; the copy walks the
  reported polyline one report late), so retail aims its hostile at what our mirror now models
  (world-0), while ours aims at the freshest accepted report, ~100 u further along while the
  player runs. The disc does not care (the client parks on the target agent's world-0 either
  way, F14/F15); what differs is the walk's aim point and the server's own arrival/halt
  bookkeeping, and no operator-visible consequence is predicted from it — so the lever is
  recorded, not pulled: if the owner's eye ever names the cadence, the change is one line
  (`_npc_follow_tick`'s point ← `_npc_frame`), with a run whose prediction is retail's
  spacing (consecutive points 144 u apart at 288 u/s, the first ~74 u behind the report).
- ~~**`NPCTRACK-Q7`**~~ **withdrawn with F13**: the sync copy has no local re-target; its
  setter is wire-only (R3's hook, 26 of 26). The mirror's velocity term is not needed for a
  mechanism that does not exist.
- **`NPCTRACK-Q8` — a lead that ends inside a hostile's disc halts world-0 at once (F14).**
  MEASURED: 14 halts on seven tapes, seven of them on the old arm's chase phase, each a lead
  of 50–160 u ending within 80 u of the hostile's copy. The mirror now halts with the client,
  so the frame and the re-pin guard read it right; whether the player ever SEES it is
  unmeasured — the drawn body halts by the same pass on world 1 (1z-be.3) when its own short
  step is covered, and on every specimen here it stood anyway. The lever, if a symptom ever
  names one, is MOVECODE's: clip the keyboard lead to end outside every agent's disc, which
  turns the halt into the sidestep the client would take. Not built: no symptom, and a lead
  the client refuses costs the frame nothing now.
- **`NPCTRACK-Q5` — the operator's picture is still world-0's.** The drawn hostile parks 80 u from
  the player's WORLD-0 copy, and that copy is p50 34 / 23 / 40 u from the drawn player while
  moving on these runs (p90 284 / 91 / 247). Q1 makes the server agree with the client about
  where the hostile stands; it does not move the hostile closer to where the operator is looking.
  That is MOVECODE's two-world problem, unchanged.

## Runs

- **[RUN-R1.md](RUN-R1.md)** — three attempts: without its tape (the sheet's own path bug; the
  wire found F8), a 5 s cut, and the full run at 09:43 (F9): **P1/P2 refuted as registered, the
  comparator at fault; 11.8 u at the halt's instant against 46–68; P3 met; P4b refuted and
  explained (Q6)**; the control at 10:06: **P1′–P3′ MET, 54.8 u against 11.8** — Q1 CONFIRMED with a
  control.
- **[RUN-R2.md](RUN-R2.md)** — ran 12:47 (F12): **6.7 u at the halt, Q1 twice**; P3 refuted (5 of
  23, all F13's local re-target); 1z-cc reaches this arc's wire — the report track's drift at the
  wall 604 → 98 u and the hostile swings four times at a standing player instead of holding.
- **[RUN-R4.md](RUN-R4.md)** — ran 15:13, agent-driven, after F14/F15 shipped: **F14 holds
  out of sample** — 3 of 3 sidesteps to 0.3 u, the one predicted halt confirmed on the tape,
  mirror vs world-0 while moving p90 25.1 u, Q1 9.1 u, zero re-pins, the wire shape as R2/R3.
- **[RUN-R3.md](RUN-R3.md)** — ran 12:56 under `movehook`: **P1 REFUTED, F13 withdrawn** — the
  sync copy's setter is wire-only (26 of 26); our halts hit a parked copy 13 of 15 times; the tape's
  Q1 number a third time, 15.7 u at the halt (6.7, 11.8 before; old arm 46–68).

## Review tools

- `python studies/npctrack/review/npcdrift.py <tape>` — Q1's instant metric, the walking count,
  the F1–F5 pooled numbers and the pinned-tape control.
- `python studies/npctrack/review/avoidcensus.py [--no-avoid]` — F14: the shipped mirror's
  agent-avoidance pass replayed on the seven tapes, scored against the tape's waypoint legs and
  halts, and the frame with and without it.
- `python studies/npctrack/review/parkcensus.py [-v]` — F15: where the client parks the
  hostile relative to the player's world-0, disc parks separated from arrivals and our halts.
- `python studies/npctrack/review/copysep.py` — Q3: the hostile's sync copy against its drawn
  body over every sample, with the widest instants located.

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
- **A tape join must be symmetric around the capture's stamp** (F13, withdrawn). The capture
  stamps a send −67..+38 ms around the tape showing it applied; a backward-only window turned
  our own 0.5 s re-path into "the client re-targets itself" for two hours. Before any "no
  order explains this": symmetric window, check the cadence against our own timers, then the
  hook names the caller.
- **Name the caller with the hook before reading a function's trigger** (F11 → F14). The
  sidestep computer has two callers; the study read the terrain one, whose predictor never
  fires, and called the trigger unread for a day. RUN-R3's hook had the return address
  (`0x0060193B`) the whole time.
- **A sentinel with no segment is not a pathfinder refusal** (F14 vs 1z-cd). The avoidance
  halt invalidates both target blocks in the setter's own millisecond, so "the destination
  was never installed" and "the client refused to path" are indistinguishable on a 30 Hz tape.
  Before reading a mesh disagreement off that shape, ask whether the lead's endpoint sat
  within 80 u of any agent's copy.
- **A residual with a sign and a bound is a derivation, not a fudge** (F15). The client parks
  its copy at its next tick, so its park can only be inside the disc by at most one tick of
  walking; the census confirmed the sign and the bound (0–18 u, 36 of 37). That turns Q1's
  "7–16 u" from an unexplained residual into a floor. What would have been a fudge is parking
  the model half a tick inside to zero the mean — not built.
