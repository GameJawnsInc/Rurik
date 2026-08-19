# Movement / the warp — handoff

**Written 2026-08-19, at commit `7eedde8`.** Status authority is `PLAN.md` §3 and
§8; the full record is [FINDINGS.md](FINDINGS.md), 2,100+ lines. This file is what
a cold session needs to pick the arc up without re-deriving it, and what it needs
in order not to repeat the five failures.

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
  `--any-build` without diffing first — on 2026-08-19 the pin refused a legitimately
  patched 38797 whose only sin was three extra patch sites (`0x508E2`, `0x50905`,
  `0x3DB4CE`) the pin's `patched` hash predates. **`pinned.py`'s patched hash is
  stale relative to the current patcher, and 38833 has no patched hash at all.**
  That is an open defect: the run dirs the pin still accepts (`-c2`, `-probe`) hold
  the OLDER patch, so the working directory fails and the stale copies pass.
- **`--game-args` needs the `=` form for a single flag.** `--game-args='--foo'`.
  argparse reads a value starting with `-` as another option unless it contains a
  space, so two flags happen to work and one alone dies.
- **Bash heredocs in this environment eat backslashes.** A `\\n` reaches Python as
  a real newline. Write patch scripts with the Write tool, and put scratch in the
  session scratchpad — `/tmp` is `AppData\Local\Temp`, whose `sys.path[0]` has held
  a stray `dis.py` that shadows the stdlib module capstone needs.

---

## 1. The mechanism, stated once

**The warp is a RESYNC, not a teleport.**

`movetap` reads the **sync** array (`[AGBASE+0xE8]`) — the server-authoritative
agent, the one our `0x0029` grants steer. The client **reports from the copy it
predicts and renders**. Those are different objects. Our grant makes the
authoritative copy glide toward the granted point at the speed *we* name; the
predicted copy moves at whatever the player's input and the client's own collision
produce. They separate, and every few seconds the client snaps the predicted copy
onto the authoritative one. **That snap is what the player calls the warp.**

Measured both sides at once (run `20260819T171436` + capture `20260819T171153`,
183 matched pairs):

- separation p50 **125.9 u**, max **673.7 u**
- **13 of 13** jumps >300 u collapse it: mean **587.0 u → 22.3 u**, a 96% collapse
- the alignment sweep **peaks at the offset the 8,573 timestamps gave**, which was
  never fitted to the data; pairing 7 s out of true collapses only 34%

Confirmed retrospectively on the **default build** from the wire alone
(`20260819T145717`): landings sit **43.9 u** from the granted path against
**744.8 u** for an unrelated grant, **18 of 30 on-path against 0 of 31**, and the
corpus's biggest warps (3,166 / 2,583 / 2,234 u) land at fractions 0.5–1.0 along
grants **12–21 seconds old**.

**Superseded, and do not re-derive them:** `+0x48` is *not* "set once and never
re-armed" (304 re-arms in 61 s under `--heading-grant`); "stacked grants come due
almost immediately" is the tail quoted as the rule (lead times p50 2,890 ms, 6 of
304 under 200 ms); and the `+0x48` snap itself is nearly invisible — 7 arrivals,
all landing 0.0 u from `m_targetPoint`, visible jump **2.4–21.6 u**, including one
where the cached `m_point` was 593.7 u stale and the player still moved 2.4 u.

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

**The default build is 5.7/min and is the best configuration this repo has.**
Both flags default off and must stay off. Also struck, with reasons in FINDINGS:
any backward/direction guard (retail has none — 25 of 29 backward grants point
behind the player's facing); the `+0.500 u` constant as a fix (real, but it moves
the arrival tick 2 ms against a 5,238 u harm); and a `k ≤ 1` clamp "bounding any
warp to 768 u" (false — it bounds against the server's own `p`, whose drift is a
median 538 u and a max 1,429 u).

---

## 3. Where the evidence points now

**The speed, not the point.** In the refuting run the player moved at a median
**111.7 u/s** while every grant told the client `moveSpeed = 1.0` = **288.0 u/s**.
A 2.6× mismatch, on every grant, untouched by all five candidates.

**But the clean form of that failed and is not to be quoted as if it held.**
"Separation grows at `288 − player speed`", no free parameter, over 13 growth
runs: mean predicted **179.6**, observed **124.8**, mean |error| **93.2 u/s**,
per-run errors −165.8 to +91.1. Two unquantified reasons are visible: the
authoritative agent arrives and stops until the next grant re-arms it, so its
average speed is below 288; and separation is a vector distance, so it depends on
the angle between the two copies' travel. **Speed is a major term, not the model.**

**RESOLVED at the naming level (2026-08-19 corpus pass — FINDINGS "the corpus
pass on the handoff's list"):** both rules were right about different factors of
one product. `0x002B` = `direction_factor × modifier` (1.00 fwd / 0.66 back /
0.75 side, × snare), locked to its own trailing byte 0/1,049 violations; the
absolute base rides `0x0027 AGENT_UPDATE_SPEED_BASE` (288.0, boost 383.04 —
23% of retail intervals run boosted; we send `0x0027` never and `0x002B` = 1.0
always, 621/621). Rule B's backward-1.0 was a join-lag artifact.
**⚠ The CAUSAL step did not survive:** we send 1.0 always and our client STILL
backpedals at ~186 u/s (0.66× forward) in 8 of 12 runs — the factor is applied
client-side to the predicted copy regardless of the wire float. The corpus
settles the VALUES; whether a non-1.0 rate steers the AUTHORITATIVE copy is
open, decidable by static analysis of the `0x002B`/`0x0027` handlers or by the
movetap backpedal run. **And the paired movetap join says the default build's
authoritative copy is mostly PARKED** (moving 39.8% of backward intervals, mean
114.57 u/s; duty cycle tracks grant rate 0%→98%) — separation there is the
client walking away from a parked point, which a speed multiplier cannot touch
while it is parked.

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
unattributed detections at v p50 2,521 u/s** across 7 captures, one of them the
default build.

The new list, all corpus/offline before any client run:

1. **Measure the snap trigger** from the five existing movetap runs: timer or
   separation threshold? This decides whether ANY slow-the-copy fix can bound
   FREQUENCY — if the resync is timer-driven, a speed term shrinks magnitude
   only, the arc's own named failure mode. Never computed; the data is in hand.
2. **Measure the default build's own harm**: separation p50/max by direction
   family and snap cadence from movetap `145939` ⊂ capture `145717`. Every
   quoted separation bound (125.9 / 150 u) is imported from a refuted
   configuration.
3. **Rebuild the scoreboard speed-gated.** Retail through our 300 u detector
   scores 6.4/min with ZERO intervals above 400 u/s; our builds score 1.3 / 5.4
   / 11.9 hard-jumps/min (was: 5.7 / 12.8 / 14.6). Fix movesync to read the
   spliced `0x003D`+`0x0047` stream (warpscan already does), speed-gate the
   jump bar, print the honest bar and the MAX cadence.
4. **Static-analyse the client's `0x002B`/`0x0027` handlers**
   (msghandler/codescan) — decides offline whether a non-1.0 rate steers the
   authoritative copy, possibly retiring the client run.
5. **Adjudicate the 26 impossible-step population** (15 of 26 sit at 729–768 u,
   dt ≈ 0.30 s — the `0x003D` heading-vector length; one measurement's lead).
6. **Fix `pinned.py`** before the next live run: accepted-digest SETS appended
   by the patcher (or structural patch-site verification), plus a 38833 row.

Only then decide the sixth candidate. Its VALUES are ready (backward 0.66 as
literal `c3f5283f`, side 0.75, base 288.0 via `0x0027` at spawn as its own
change, speed-before-point order, re-send at report cadence — "edge-triggered"
was falsified at 72.2% same-family repeats). Its CAUSAL step is not.

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

**This needs no `movetap`, no build pin, no second terminal.** It prints the pair
count before the verdict, refuses above a 0.5 s report cadence, and gives you
jumps/min directly. Compare against the scoreboard in §2: **anything at or above
5.7/min is worse than shipping nothing.**

**⚠ 2026-08-19: that bar is contaminated and must be speed-gated before the next
candidate is scored** (§4 item 3): the 300 u rule counts ordinary walking across
report gaps — retail itself scores 6.4/min on it with zero intervals above
400 u/s. The hard-jump numbers are 1.3/min (default) / 5.4 (`--heading-grant`) /
11.9 (`--client-endpoint`). Until movesync is fixed, gate by implied speed
(>400 u/s, dt ≥ 0.05 s) and quote BOTH the magnitude and the rate. And when
movesync REFUSES a verdict, the counts printed above the refusal are refused
too — that is how the "5 unexplained jumps" hole got minted.

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
