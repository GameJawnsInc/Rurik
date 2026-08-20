# Movement / the warp — handoff

**Written 2026-08-19, revised twice the same day** (corpus pass, then the
mechanism round). Status authority is `PLAN.md` §3 and §8; the full record is
[FINDINGS.md](FINDINGS.md) — read its last two sections first, they supersede
everything above them. This file is what a cold session needs to pick the arc up
without re-deriving it, and what it needs in order not to repeat the failures.

> ## ★ READ THIS BOX FIRST — the arc changed shape on 2026-08-19
>
> **THE MECHANISM IS DECODED IN THE BINARY.** The snap is `0x006022B0`, copying
> SYNC → ASYNC (the rendered copy is dragged onto the authoritative one). It is
> reached from `0x00605FC0`, which has **exactly 3 callers, all message-driven —
> the desync test is never evaluated per frame.** The test itself
> (`0x006055E0`) returns "no snap" when the SYNC agent's own dead-reckoned
> position (`+0x78`) lies within **100.0 u @0x00946560** of the client's recent
> **history** chain — straight-line AND walkable; ⚠ **NOT our grant, and not a
> prediction** (decoded 2026-08-20, FINDINGS "the AgTrack match test is
> decoded" — it retired §4's starred shape 1). Otherwise it runs a FALLBACK of
> **three gates, and ANY ONE of them snaps** (decoded 2026-08-20, FINDINGS
> round 2): straight-line separation over **299.33 u** — the `300.0f
> @0x00946564` is quantised upward by the client's LUT sqrt, so **exactly
> 300.0 u snaps**; OR a walkable `pathCount == 0`, which reports that the
> position OUR grant wrote is **off the navmesh**; OR the sync agent unable to
> take a first step. **"Under 300 u" is therefore NOT safe** — two of the three
> gates are not distance tests at all. And the snap that follows reseeds
> **every** async agent, not just the player's.
>
> **THE WARP, in one sentence:** we answer a click with `0x0029` (a SYNC-ONLY
> message), the authoritative copy glides there and PARKS, the player keyboards
> away, nothing we send afterwards can reach the copy they see — **`0x0025`'s
> async arm is gated shut for the client-controlled agent** — separation grows to
> 3,648 u unwatched because nothing triggers the check, and the next grant or
> arrival redeems the whole gap at once.
>
> **THE SPEED CANDIDATE IS DEAD FOR THE BUILD WE SHIP:** **0% frequency** at the
> fidelity-correct 0.66, measured two independent ways (the ceiling table and the
> snap-trigger replay agree); the **−3.1% magnitude** is an n=1 measurement and
> rides along as colour, not as a second witness. Do not
> build it. `0x0027` at spawn is a measured no-op (the client already holds
> maxSpeed 288.0 / moveSpeed 1.0 in 4,115/4,115 samples).
>
> **THE SCOREBOARD IS NOT A SCOREBOARD YET.** Observation coverage is 31% / 72% /
> 89% across the three configurations, so per *observed* second the default build
> is the WORST on displaced distance, not the best. Nothing can be scored against
> "5.7/min" until denominators are stated. `movesync.py` was repaired this round;
> re-derive before comparing.
>
> Candidates 1-5 are dead (§2). Candidate 6 (the speed term) is dead above.
> **Shape 1 — "make the grant match" — is dead too, as of 2026-08-20**: the test
> it was aiming at never reads our grant (§4 item 1). The whole test is now
> decoded, both halves, and **none of its gates is a server lever** — the one
> real lever found is `0x002C`, which clears the tracking record and sets BOTH
> copies, and which an earlier build already tried and removed as "the warp the
> player described". Read §4 item 1's NEXT JOB before picking anything up.

---

## 0. Before your second command

```bash
git rev-parse --show-toplevel
```

**This bit us on 2026-08-19 and cost a client run.** Work landed on `main` while
the operator ran from a worktree that was 16 commits behind; the flag under test
did not exist in the tree they executed, and `authsrv.py` answered
`unrecognized arguments: --client-endpoint`. A stale tree does not error, it runs
old code. If you land anything on `main` while the operator is running from a
worktree, **fast-forward the worktree in the same breath**.

Three more traps that have each cost a run:

- **`movetap.py` pins build 38797. `session.py --exe` defaults to the NEWEST
  build under `vault/run`, which is 38833.** Always name the exe:
  `--exe "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe"`. Do not reach for
  `--any-build` without diffing first. **That gate was INVERTED and is now REPAIRED
  (2026-08-19).** It refused the legitimately patched 38797 we actually launch —
  three extra patch sites (`0x508E2`, `0x50905`, `0x3DB4CE`) that the single
  hand-typed `patched` hash predated — while the stale `-c2`/`-probe` copies passed,
  and 38833 had no patched hash at all. `Build.patched` is now a TUPLE of accepted
  digests per build: the current patcher's 38797 copy and both 38833 copies are
  committed in `pinned.BUILDS`, and `make_custom_client.py` and `make_run_dir.py`
  each call `register_patched()` into `vault/client-patched/patched_digests.json`
  after their own verification passes. Registration REFUSES a digest equal to any
  known build's pristine, and under `strict` refuses what it cannot diff against a
  pristine image at all. `test_pinned.py` (143 checks, floor 130) and
  `test_buildid.py` (42, floor 39) hold every one of those refusals.
- **`--game-args` needs the `=` form for a single flag.** `--game-args='--foo'`.
  argparse reads a value starting with `-` as another option unless it contains a
  space, so two flags happen to work and one alone dies.
- **Bash heredocs in this environment eat backslashes.** A `\\n` reaches Python as
  a real newline. Write patch scripts with the Write tool, and put scratch in the
  session scratchpad — `/tmp` is `AppData\Local\Temp`, whose `sys.path[0]` has held
  a stray `dis.py` that shadows the stdlib module capstone needs.

---

## 1. The mechanism, stated once

**The warp is a RESYNC, not a teleport** — and as of 2026-08-19 every step of it
is named in the client binary. Full derivation and addresses: FINDINGS' last
section. The short form a cold session needs:

`movetap` reads the **sync** array (`[agentMgr+0xE8]`, ArenaNet's own name via
`AgMsg.cpp` asserts) — the server-authoritative agent our `0x0029` grants steer.
The client renders and reports from the **async** array (`[agentMgr+0x14C]`), the
copy it predicts. Two objects, two world clocks.

1. **We grant, the copy glides, then PARKS.** Speed is baked at grant time:
   `0x005FE950` computes `+0x48 = +0x58 + trunc(dist*1000/(maxSpeed·moveSpeed))`
   and velocity `+0xB0/+0xB4 = unit(d)·speed`. The dead-reckoner `0x005FFB40` is
   only `pos = +0x78 + vel·((t − +0x58)·0.001)` — **it never reads the speed
   fields**, so a mid-flight `0x002B` changes nothing about the current leg.
   In the default build the copy is parked **93.4 of 177.3 s**.
2. **Nothing we send afterwards reaches the rendered copy.** `0x0029` and
   `0x002B` are SYNC-ONLY. `0x0025` looks like it reaches both — but its async
   arm is gated: `0x005FD5D3` skips it when the agent id IS the
   client-controlled agent (`[mgr+0x1E0]` = AgTrack+0x14, set when the client
   registers its own local move, cleared only on removal). **Once the player has
   moved locally, our `0x0025` writes the sync copy only.** Independently
   confirmed numerically: including `0x0025` in a forward simulator of the copy
   made the residual 11× worse. Ungated both-copies messages: `0x0024`,
   **`0x0027`**, **`0x0028`**, **`0x002C`**.
3. **Nobody is watching.** The desync test `0x00605FC0` has **exactly 3 callers
   (0x005FEBEB in the grant bake, 0x006022A1, 0x00602BBD) — all message-driven,
   never per-frame.** So separation grows unchecked: the default build sat
   **127 intervals / 93.4 s at p50 1,522 u, max 3,648 u, with zero snaps.**
4. **Then it is redeemed all at once.** On the next grant or arrival,
   `0x006055E0` asks first whether the SYNC agent's own dead-reckoned position
   (`+0x78`) lies within 100.0 u @0x00946560 of a segment of the client's
   **history** chain — if so, **no snap**. ⚠ That operand is **not our grant**
   and the chain is **not a prediction**; both were decoded on 2026-08-20 and
   both killed §4's starred shape 1 (FINDINGS, "the AgTrack match test is
   decoded"). Otherwise it dead-reckons both copies — the SYNC one on the sync
   clock, the ASYNC one on the async clock — and runs **three gates, any one of
   which snaps** (FINDINGS 2026-08-20 round 2):
   **(1)** straight-line separation (`0x00709990` with `0x006057C8 push 1` =
   straightOnly; the *100 u* test is the walkable one, `0x00605C40 push 0`)
   compared against **300.0f @0x00946564** — effective cut **299.332591 u**,
   so exactly 300.0 u snaps; **(2)** `0x00709E90`'s `pathCount == 0`, which
   means the position our grant wrote is **off the navmesh**; **(3)**
   `0x005FEF70` returning 0 — the sync agent cannot take a first step toward
   the path, blocked by terrain or another agent's personal space.
   Any of the three resyncs **every** async agent via `0x006022B0`, a hard
   SetPosition — one agent failing the gates reseeds the whole roster.
   **That is the warp.**

**The harm, on the build we ship** (`20260819T145717` + movetap `145939`,
n = 251 paired reports): separation **p50 1,164 u, p90 2,163 u, max 3,648 u**;
snap cadence 2.67/min, inter-snap p50 21.7 s, max 41.2 s; 6/6 snaps collapse the
gap (p50 2,069 → 24.5 u) on two independent sources.

**Superseded — do not re-derive, do not re-quote:**
- The **125.9 u / "under 150 u" separation bound is `171153`'s, a REFUTED
  configuration.** The shipped build is ~1,164 u. (And do not attach a "9×"
  multiplier: the second parser's 1,516 u reads `movetap point`, which is stale
  by up to a leg — a different quantity, not a corroboration.)
- `+0x48` is *not* "set once and never re-armed" (304 re-arms in 61 s under
  `--heading-grant`); "stacked grants come due almost immediately" is the tail
  quoted as the rule (p50 2,890 ms, 6 of 304 under 200 ms).
- The `+0x48` arrival snap is nearly invisible on its own (7 arrivals landing
  0.0 u from `m_targetPoint`, visible jump 2.4-21.6 u) — arrivals matter because
  they *call the desync test*, not because they teleport.
- **"A speed term cannot bound frequency" is too strong.** True form: *not at
  0.66* (0% there; 36% at k=0.5, 91% at k=0.1).
- **"The client's own stop is not the trigger" was a check that could not fail.**
  Run in the direction that can fail, intervals *beginning* with a `0x0047`
  converge 4/31 vs 4/219 — a **7.1× lift**. Half the default build's snaps follow
  a client stop.
- **movetap is 9.4-12.9 Hz, not 50 Hz**, and its `now` is the client world clock
  (50 ms quanta, 1.3% slow vs wall). Any "20 ms interval" in the older record is
  a world-clock delta.

---

## 2. The scoreboard — five dead candidates

Read this before designing a sixth. **All five were additions, and all five chose
a point.**

| # | candidate | result |
|---|---|---|
| 1 | suppress the grant | retail sends 2,855 player-directed `0x0029`; not our invention |
| 2 | `--stop-echo` — echo the stop point on `0x0047` | warped anyway 9.9 s after an echo, and the echo dragged the player back |
| 3 | `--heading-grant` — re-grant on every heading | **caused warps.** 12.8/min |
| 4 | "echo the client's own vector" | a **no-op**: retail's `reported + vec2 + 0.5` and our `state["pos"] + heading` are the same expression |
| 5 | `--client-endpoint` — the client's own unclipped endpoint, refreshed | **REFUTED, worst of the three. 14.6/min** against a stated bound of 2 |

| 6 | the direction factor (`0x002B` 0.66 backward) | **DEAD on the shipped build: −3.1% magnitude, 0% frequency**, two independent derivations. Correctly aimed only at the refuted high-grant arms (−50.5% on `--heading-grant`) |

**Both flags default off and must stay off.** Also struck, with reasons in
FINDINGS: any backward/direction guard (retail has none — 25 of 29 backward
grants point behind the player's facing); the `+0.500 u` constant as a fix
(real, but it moves the arrival tick 2 ms against a 5,238 u harm); a `k ≤ 1`
clamp "bounding any warp to 768 u" (false — it bounds against the server's own
`p`, whose drift is a median 538 u and a max 1,429 u); `0x0028
AGENT_STOP_MOVING` at keyboard onset (retail does it in 1 of 499 onsets, and
that one was a zone transfer); and **`0x0027` at spawn** (a measured no-op — the
client already holds maxSpeed 288.0 / moveSpeed 1.0 in 4,115/4,115 samples).

⚠ **"The default build is 5.7/min and is the best configuration this repo has"
NO LONGER STANDS AS WRITTEN.** The 300 u bar counted ordinary walking; on the
repaired two-arm bar the three configurations read **7 / 20 / 13 hard rows** and
**1.31 / 5.69 / 11.88 per minute of span**. But observation coverage is
**31% / 72% / 89%** across them, and per *observed* second the ranking inverts to
4.19 / 7.48 / 11.27 jumps per min — the 4.19 stands (the default build's count did
not move), but 7.48 and 11.27 were computed from the PRE-REPAIR 19 and 11 and must
be re-derived before they are quoted — and 137.8 / 69.5 / 101.4 u displaced per
second, so **the default build is the worst on displaced distance and the best on
frequency-per-span.** It also trades many small warps for few enormous ones
(magnitude p50 **1,969 u vs 569 / 582**, max 3,405 / 768 / 754 u, on the repaired
bar; the pre-repair pair read 549 / 403). Say which denominator you
mean, every time; re-derive with the repaired `movesync.py` before comparing
anything.

---

## 3. Where the evidence points now

**Not the point, and not the speed. The STALENESS — and the fact that nothing we
send can reach the copy the player sees.**

The speed contest is CLOSED, both halves. Naming: `0x002B` = `direction_factor ×
modifier` (1.00 fwd / **0.66 back** / 0.75 side, × snare), locked to its own
trailing byte 0/1,049 violations; the absolute base rides `0x0027` (288.0, boost
383.04). Causation: **the client applies the direction factor locally** — our
runs backpedal at ~186 u/s (0.659× forward) while we send 1.0 in 621/621 sends,
and retail's own steps split 189.6 u/s at rate 0.660 (n=17) vs 189.9 at rate
1.000 (n=10). The wire rate never reaches the rendered copy. And on the
authoritative copy the binary says the glide **never reads `+0x60`** — speed is
baked into velocity and the arrival tick at grant time. Worth ≈3% of magnitude,
0% of frequency, on the build we ship.

**The separation budget says why.** Default build, 712 measurable intervals:
49.6% of growth accrues while the authoritative copy is **PARKED** and the client
walks away; 47.7% while both move; the BACK family carries only 30.4% of growth
and 10% of the copy's travel. (`--heading-grant` is a completely different
budget — 99.3% AUTH-MOVING, 95.9% of it BACK — which is why the 0.66 fix scores
well there and nowhere useful.) ⚠ 79% of the default build's net accumulation
sits in UNCOVERED time, so the table speaks for 21% of the run.

**The lever list, from the binary.** Messages whose async arm is unconditional
for the player's own agent: **`0x0024`, `0x0027`, `0x0028`, `0x002C`**. Not
`0x0029`/`0x002B` (SYNC-only by design), and **not `0x0025`** — its async arm is
gated shut once the player has moved locally. Anything that must correct what
the player *sees* has to come from that four-message list, or from making the
snap not fire at all (§4 item 1).

---

## 4. The next thing to do, in order

**Items 1–4 of the old list were run on 2026-08-19** (FINDINGS, "the corpus pass
on the handoff's list" — every number adversarially re-derived). Outcomes: (1)
**NO** — retail never stops on keyboard onset (1 of 499 onsets, and that one was
a zone transfer; retail's shape is supersession at one RTT, and its only
subtractive move is a zero-length grant answering the client's own `0x0047`);
(2) therefore **the subtraction branch never opens — do not build the
`0x0028`-at-onset fix**, and do not build supersede-every-heading either, which
IS dead candidates 3/5 (both already ran a TIGHTER leash than retail and warped
more — the point is bracketed from both sides and is not the free variable);
(3) resolved at the naming level, causal step open — see §3; (4)
`20260811T173940` was an instrument artifact (the client walked; pre-2026-08-19
captures logged only the `0x0047` stop arm, hiding 130 of 158 positions), but
the impossible-step population in OUR gamesrv corpus is live and larger: **26
unattributed detections** across 7 captures, one of them the default build —
quoted as magnitude and **excess over the 288 u/s budget** (excess p50 671 u,
max 3,804 u over the corpus's n = 43 detections), never as the implied velocity
this line used to carry, which §6 retires and the repaired `movesync.py` demotes
to a labelled gate input.

**That list was then run in full on 2026-08-19** (FINDINGS, "round 3 — the
mechanism is decoded"). Snap trigger: neither timer nor free-running threshold —
message-driven evaluation of a 300 u straight-line test (§1; it was recorded as
"walkable-path" until 2026-08-20 — the walkable conjunct is the 100 u one). Default-build harm:
measured at last, p50 1,164 u (§1). Scoreboard: rebuilt, and the denominators
turned out not to be comparable (§2). Handler statics: **done, and they decided
the causal question** — speed is baked at grant time, `0x0025` is gated, `0x0027`
/ `0x002C` reach both copies (§3). Impossible steps: 25 of 26 are resyncs; the
survivor is a client-side click-move at 2.6× the walk budget. `pinned.py` and
`movesync.py`: **repaired this round** (see §5 and TESTS.md).

### The three shapes worth trying next, in order of evidence

1. **★ ANSWERED 2026-08-20 — and the answer RETIRES this shape.** `0x00605AF0`
   compares **POINT ONLY**: no time, no sequence, no id. (The whole 145-instruction
   body holds exactly one integer `cmp` and it is `sub esp, 0x30`; one absolute
   memory read, and it is the 0.99 constant.) It asks whether a point lies within
   **100.0f** of a segment — **straight-line perpendicular, compared SQUARED and
   STRICT**, *and* within 100.0f of **walkable path length**, compared **LINEAR and
   INCLUSIVE** (~99.6 u effective, because the client's leg sqrt is a table
   approximation biased high, worst +0.39%, n = 5,000). Full decode with pseudocode:
   FINDINGS, "the AgTrack match test is decoded".
   **BUT THE POINT IT TESTS IS NOT OUR GRANT, AND THE LIST IS NOT A PREDICTION.**
   `0x00605643` reads `source+0x78` — the SYNC agent's own position, dead-reckoned to
   the client's clock by `0x005FF880` during the grant bake. Our `0x0029` writes
   `+0x88..+0x94` and `+0x80` and **never `+0x78`** (n = 0 writes in `0x00602A40`'s
   body). And the chain is ArenaNet's `history`: nodes stamped `now` at creation
   (`0x00604DCC`), pushed on the FRONT (`0x00605A93`), one per movement-command
   change with a forced 2.5 s re-sample — so a single click yields a **one-segment**
   polyline. ⇒ **There is no grant we can send that makes this match by
   construction**, and the wire already agrees: `--heading-grant` sat 0.5 u from the
   client's own endpoint (193/193) and is recorded REFUTED at `authsrv.py:1046` for
   CAUSING warps; the click-only capture held 40 grants at 0.0000 u and still logged
   7 hard jumps up to 3,405 u. **Do not build "make the grant match".**
⚠ FIRST, A LOCATION CORRECTION: the "next job" sentence is **not** in `HANDOFF.md` §4 (which is "Prior art — what to take, what to ignore" and contains no such sentence). It is **`PLAN.md`:1417**, the closing clause of §"Movement — the AgTrack match test is DECODED and shape 1 is DEAD (2026-08-20)". `grep -rn -i "next job" HANDOFF.md PLAN.md` returns that one line and nothing else. Replace the clause that currently reads:

> "…and the next job is the undecoded fallback half `0x00605753`–`0x0060583D` where a MISS is actually adjudicated (and the 300.0f gate there is STRAIGHT-LINE, correcting FINDINGS:2373)."

with:

> …and the fallback half `0x00605753`–`0x0060583D` is now DECODED (2026-08-20): a miss is adjudicated by **three** gates, all snapping on failure — straight-line separation over **299.3326 u** (not 300; `0x0046E870`'s LUT sqrt is a one-sided over-estimate, so exactly 300.0 u SNAPS, correcting FINDINGS:2861's ~298.8 u), OR a **walkable** navmesh query returning `pathCount == 0`, which means **our granted SYNC position is off the navmesh**, OR `timeToEvent < 0.0005f` on the first step — so **separation under 300 u is NOT sufficient to avoid a snap**, and the snap itself is a reseed of **every** agent in world 1, not the player jumping. **No gate is a server lever**: gate 1's async operand is written by none of the movement messages (9 of 17 AgMsg handlers touch world 1; `0x0029`/`0x002A` do not), gate 2's failing operand is the point we granted tested against a navmesh we lack, and gate 3 reads neighbouring agents and terrain. **The next job is therefore not another decode but a measurement and a costing**: (a) log `rec.clientControlled` at `[agentMgr+0x1CC+0x20]+id*0x1C` alongside separation to find which gate actually fires — the gates are fenced behind `clientControlled != 0` and `world == 0`, which may explain Lane D's 92.7% above-threshold-no-snap on its own; and (b) price `0x002C`, the one real lever (its handler clears the record then writes **both** copies, so no gate runs), against the record that an earlier build sent five and they were removed as "the warp the player described" (`authsrv.py:7036-7045`). Two loose ends: the Tier-2 provider leg `0x00737350`→`0x00737940` is unverified to write `*pathCount`, which the caller never initialises; and `0x005FCAA0` is a second, gate-free snap route fired from local input.
2. **`0x002C AGENT_UPDATE_POSITION`** — the only catalogued primitive that calls
   `AgTrack::Clear` and then SetPositions BOTH copies, ungated. It is a hard set,
   so it is a teleport by construction; the open question is whether a small,
   frequent, correct one is cheaper than a rare 3,648 u one. We have never sent
   one in THIS corpus (0 of 2,024,792) — ⚠ but that is a census, not a history:
   `authsrv.py:7036-7045` records an earlier build that **did** send them ("five
   AGENT_UPDATE_POSITION went out and three were arrivals, carrying the client
   630, 189 and 765 units"), removed as "the warp the player described". Untried
   in the current corpus, not untried. Retail sends 12 corpus-wide, so this is rare-but-real
   in ArenaNet's own traffic.
3. **`0x0027 AGENT_UPDATE_SPEED_BASE` as a mid-flight re-bake** — worthless as a
   spawn constant, but it reaches both copies unconditionally AND re-issues the
   outstanding grant (`0x00602910` → `0x00602A40` → `0x005FE950`), so it is the
   only lever that can re-aim a stale in-flight destination without naming a new
   point.

Still open, and worth one measurement each: the `0x0025` async gate means the
predicted copy is unreachable **while a pending record exists** — does clearing
that record (item 2's `AgTrack::Clear`) reopen it? And the survivor step's
2.6×-budget click-move wants a movetap run over a long ungranted click-move.

---

## 5. How to score any candidate, in one minute

```bash
python toolkit/harness/session.py --keep-open --exe "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe" --game-args='--your-flag'
```

Play for a minute — **hold S and click distant ground**, which is what reproduces
it — then:

```bash
python toolkit/clientscan/movesync.py --wire-only
```

**This needs no `movetap`, no build pin, no second terminal.** `movesync.py` was
**repaired on 2026-08-19** and now: reads the SPLICED `0x003D`+`0x0047` c2s
stream (the old source was the `0x0047` stop arm only, which on every pre-fix
capture hid ~80% of the client's positions); makes a **speed-gated hard-jump
count the verdict** on TWO ARMS — implied speed > 400 u/s at dt ≥ 0.05 s, and
**displacement ≥ 520 u BELOW that dt floor**, where a speed is not a measurement.
The second arm is what this round added, and it is retail-calibrated: retail scores
ZERO on both (largest sub-floor step 19.15 u over 82 intervals against a 520 u arm,
27x of headroom; largest step inside 2 s 517.87 u / 1.352 s), while the corpus goes
**61 → 64 hard rows over 961 captures / 4,582 intervals** — the three restored rows
being its fastest genuine events, all at ~32 ms. It also demotes the 300 u bar
to a labelled, refused legacy count; refuses on COVERAGE as well as median
cadence; prints no quotable RATE above its own refusal — and, the other half of
that rule, does not let a refusal SUPPRESS a COUNT either: under the
`MIN_INTERVALS` floor it prints the count, the magnitude and the excess with no
`/min` anywhere, because only a per-minute number needs a denominator.

⚠ **The old "anything at or above 5.7/min is worse than shipping nothing" bar is
RETIRED** — that number counted ordinary walking (retail scores 6.4/min on the
same rule with zero intervals above 400 u/s). Score on the hard bar, and **state
the denominator**: rate per minute of span AND per minute of actively-reported
time, because coverage runs 31-89% across configurations and the ranking inverts
between them. Two different "active time" thresholds are in play and they are
not interchangeable: the coverage / per-observed-second figures in this file and
FINDINGS use gaps ≤ 2.0 s, while `movesync.py`'s printed active-time rate uses
`FREE_SILENCE` = 1.042 s and prints the sweep beside it — say which one a number
used, every time. Quote **magnitude and rate together**, never one alone. For a
discontinuity, quote **magnitude and excess over the 288 u/s budget** — never
implied velocity, which is arithmetic on a denominator the event itself created.

For the separation number too, run `movetap.py --seconds 300` in a second terminal
once the map has loaded, then `movesync.py` without `--wire-only`.

**Standing rule for any warp run: keep the keyboard moving the whole time.** The
client emits `0x003D` only while moving, so a stationary wait blinds every
wire-side instrument exactly when the phenomenon fires — 8.7% of retail's own
grants sit outside any watched interval for this reason.

---

## 6. Traps this arc actually fell into

Not general advice — each of these cost something here.

- **Over-fitting, five times.** A rule drawn from the cases studied hardest, then
  used as a gate. The bit-exact landing rule suppressed a real 42 u teleport; a
  four-term precondition excluded 2 of 4 known warps; a probe design would have
  called every ordinary glide a teleport; and **a prediction that bounded teleport
  SIZE while the harm arrived as FREQUENCY shipped a fix that warped the owner's
  character.** State predictions in the units the harm arrives in, and bound both
  magnitude and rate.
- **Vacuous controls.** A no-collapse control in `test_movesync` judged **zero
  rows** — `all([])` is True — inside the section whose job is proving the checks
  can fail. Assert the row count first. Caught by reading output, not by the test.
- **Tautological comparisons.** The first wire-only test compared a point against a
  segment it defined, because where grants outnumber reports the grant-time report
  is often the *same record* as the pre-jump position. It read 0.0 u and looked
  like a refutation.
- **Instruments that score the wrong quantity, quietly.** `warpscan` said
  "NOT near any grant" for 10 of 12 detections; that line was the finding and read
  as a puzzle for two runs. `movetap`'s floor demanded 7,500 samples from a reader
  that sustains 13 Hz, so it printed FAIL over the run that overturned the arc.
  Both are fixed; the lesson is that a floor which fires on every healthy run is
  how a real FAIL gets waved through.
- **Believing a summary over the binary.** "The client normalizes it" was true of
  the `0x0025` jump table as a whole and false for its dominant case, which is a
  bare `mov`. Disassemble the case you are standing in.

Added 2026-08-19, each paid for in this arc's own rounds:

- **A NEGATIVE CAN BE VACUOUS TOO, and it looks like evidence.** "The client's
  own stop is not the trigger — 0 of 31" was structurally impossible to observe:
  every `0x0047` sits at a report-interval boundary, and an interval in which the
  client moved hundreds of units cannot END on a stop report. Run in the
  direction that CAN fail and the answer flips to a 7.1× lift. **Before quoting a
  zero, ask what a non-zero would have looked like.**
- **A COUNT PRINTED ABOVE A REFUSAL IS ALSO REFUSED.** `movesync` correctly said
  "REFUSING a verdict" at a 1.28 s cadence; the "5 unexplained jumps" printed
  above that line became the arc's "largest remaining hole" for a week. The tool
  now prints no quotable RATE above its own refusal — and the rule has a SECOND
  half the first repair got backwards: a refusal must not SUPPRESS a count either.
  The `MIN_INTERVALS` floor used to `return` before the hard section, so a
  nine-interval capture carrying a 3,000 u step printed a bare tally; a count and a
  magnitude need no denominator. But the habit is the fix.
- **THE DENOMINATOR IS PART OF THE MEASUREMENT.** Three configurations were
  ranked on jumps/min for weeks while their observation coverage was 31% / 72% /
  89%. Per observed second the ranking inverts. State span-vs-active every time.
- **AN IMPLIED VELOCITY OVER A WINDOW THE EVENT CREATED IS NOT A QUANTITY.**
  "23,279 u/s" was 740.7 u across a 32 ms window that existed only because the
  client emitted an extra report immediately after the snap. Magnitude and excess
  over budget survive; velocity does not.
- **A GATE THAT LOOKS SYMMETRIC MAY BE GATED ON ONE SIDE.** `0x0025` is
  classified as reaching both agent arrays and does — for every agent except the
  one the client controls. A per-opcode census that stops at "which arrays does
  this handler touch" gets the player's own case exactly backwards.
- **CALIBRATE THE SAMPLER BEFORE QUOTING ITS UNITS.** `movetap` was recorded as
  50 Hz and is 9.4-12.9 Hz; its `now` is a world clock running 1.3% slow in 50 ms
  quanta. A whole round's "20 ms intervals" were world-clock deltas.
- **A FIX'S OWN REVIEW IS NOT OPTIONAL.** Both instrument repairs this round came
  back FIX-FIRST from an adversarial reviewer: the `movesync` speed gate silently
  dropped the corpus's three fastest real events, and the `pinned` digest-set
  change accepted 10 MB of random bytes as "patched" when the pristine image was
  absent. Both were caught by re-running the attack, not by reading the diff.
