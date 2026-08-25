# Refutation lens: EMPIRICAL CONTRADICTION against the `0x002C`-disarms claim

Adversarial recon note. **No client launch, no harness, no `session.py`.** Everything below is
read out of `vault/captures/` and out of `toolkit/authsrv/authsrv.py` as it stands in this
worktree. I attacked the claim from the CORPUS and the RECORD, deliberately *not* from the
disassembly (a parallel lens, `followon-notes/p5-resync-disarm.md`, owns that).

Tags: **OBSERVED** = I ran the measurement and am quoting output. **SOURCED** = a doc/file says
it and I checked the citation resolves. **UNVERIFIED** = I am reasoning past what I measured.

**The claim under attack:**
> "An s2c `0x002C` disarms a pending `+0x48` arrival teleport … while an s2c `0x0029` reaches
> only the grant bake and can therefore only ARM or RE-ARM a destination, **never disarm a stale
> far one**. Therefore `--resync` would zero F35's arrival-teleport warp, and this explains why
> the 2026-08-19 `--stop-echo` run saw the echo ADD a second destination."

**VERDICT: the claim is REFUTED AS STATED, on its second half, twice, from captures.** Its first
half (a `0x002C` disarms) survived a genuine hunt — 3 of 3 armed cases in the corpus — and I
could not find a counter-example to it. Two of its supporting premises are false. Details below.

---

## 0. HEADLINE, before the detail

1. **`--resync` HAS BEEN RUN. The vault holds the tape. It fired 18 times.** The brief,
   `FINDINGS.md:3892` and the parallel note's §8 all say "never run". §1. **OBSERVED.**
2. **REFUTATION: a plain `0x0029` disposed of a pending far arrival, twice, in captures where
   our server sent ZERO `0x002C`.** `+0x48 → 0` and destination `→ [inf, inf]` with 547 ms and
   849 ms still to run on the arm. One of the two cost the rendered copy **nothing** (33 u of
   ordinary walking). §2. **OBSERVED.**
3. **The movetap signature the claim reads as "the disarm" is NOT diagnostic.**
   `stop → 0`, `target → [inf,inf]`, `sep → 0` also appears on a **329 u rendered-copy WARP**
   (`movetap-20260821T172133` L150). Reading that signature as evidence of harmlessness is
   unlicensed. §2.2. **OBSERVED.**
4. **The "payload provenance" distinction that is said to be "the whole of the difference"
   between `--resync` and the REMOVED `0x002C` build is EMPIRICALLY INERT at the fire instant.**
   Over all 18 fires in the only run, `|payload − state["pos"]| ≤ 0.0064 u`. The safety comes
   from the **call site**, not from the variable. §3. **OBSERVED.**
5. **The three armed `0x002C` disarms the corpus actually holds were NOT `--resync`'s payload.**
   They are `--cast-stop=pin`, whose payload is `cast_stop_reckon()` — our **extrapolation**
   (`est = pos + heading·rate·288·dt`, `authsrv.py:1906-1909`), the shape closest to the removed
   build's. P5's own payload has never been observed disarming anything. §4. **OBSERVED.**
6. **F35's warp precedes both `0x002C` sends in its own capture** — consistent with the claim,
   but it means the shipped `0x002C` sender does not fire in F35's trigger regime at all. §5.
7. **The only `--resync` run scores 0.00 hard jumps/min on `movesync.py`** — and it sent zero
   `0x0029` grants, so it never created an armed arrival and is not a test of the disarm. §1.3.
8. **The parallel note's replayed fire-rate (5.60/min) is contradicted by the actual run**:
   **22.75/min, 34.6% of evaluations**, much nearer the flag block's own 25.4/min. §1.4.

---

## 1. `--resync` has already been run, and the tape is in the vault

### 1.1 The find — OBSERVED

```
$ python -c "... count kind=='resync' rows per gamesrv capture ..."
authsrv-20260820T181209-c1.jsonl {'resync': 1,  'r:in-agreement': 1}
authsrv-20260820T182119-c1.jsonl {'resync': 52, 'r:in-agreement': 30, 'fired': 18,
                                  'r:resync': 18, 'r:rate-limited': 4}
```

`vault/captures/gamesrv/authsrv-20260820T182119-c1.jsonl` also carries **18 `kind:"sent"` rows
with `opcode: 44`**.

### 1.2 Provenance chain — every link checked, OBSERVED

| link | evidence |
|---|---|
| the shipped sender's f-string | `authsrv.py:4148-4152` — `"RESYNC 0x002C at ({payload[0]:.0f},{payload[1]:.0f}) plane {plane} -- the CLIENT's own report, {age * 1000:.0f} ms old, closing a modelled {sep:.0f} u between the authoritative copy and it"` |
| the capture's send label | `"RESYNC 0x002C at (10009,8045) plane 0 -- the CLIENT's own report, 0 ms old, closing a modelled 186 u between the authoritative copy and it"` — same string, same field order, same rounding |
| the record shape | the capture's rows carry exactly `_maybe_resync`'s `rec.event("resync", fired, reason, age, separation, payload, plane, sync, ours)` (`authsrv.py:4130-4140`), reason vocabulary included (`in-agreement`, `rate-limited`, `resync`) |
| the date | `--resync` landed in commit `3e40bde` *"The 0x002C resync, behind --resync, OFF by default"*, **2026-08-20 17:47:42 -0400**; the capture's own `wall` is **2026-08-20T22:21:29Z = 18:21 local**, **34 minutes later** |

This is not a lookalike. It is the flag, driven the same evening it was built.

**Three published statements are therefore stale:**
* the orchestrator's brief — *"`--resync` (REALFIX-P5, built, NEVER RUN)"*;
* `studies/movement/FINDINGS.md:3892` — *"already built (`--resync`), never run"*;
* `followon-notes/p5-resync-disarm.md` §8 — eight predictions "for an owner-driven `--resync`
  run", several of which (P2's telemetry shape, P6's fire rate) an existing tape can already
  score. P6 is scored in §1.4 and it **fails**.

### 1.3 What the run does and does not settle — OBSERVED, and this cuts both ways

```
$ python toolkit/clientscan/movesync.py --wire-only --capture .../authsrv-20260820T182119-c1.jsonl
    SOURCE  52 client self-reports, SPLICED ... (46 x 0x003D + 6 x 0x0047)
    GRANTS  0 player 0x0029 to agent 1, decoded from the wire bytes
    HARD JUMPS  n = 0 of 51 interval(s)   RATE 0.00/min
       Nothing in this capture moved the client further than it could have walked, on either arm.
```

**Zero hard jumps under 18 `0x002C` sends** — the safety half of P5 has a real, if small,
positive result on the owner's own machine.

**But `GRANTS 0`.** Opcode census on that file: `0x0029` = **0**, `0x002A` = 0, `0x002C` = 18,
`0x0025` = 7. The build in that run *"stopped broadcasting position at all, except an impossible
one"* (commit `259508e`). **With no grant, no far `+0x48` was ever armed, so the run cannot
test the disarm and cannot test F35.** And no `movetap` tape exists for 2026-08-20, so no
`+0x48` observation exists for any `--resync` fire, ever.

> **The disarm has never been observed under `--resync`. What HAS been observed (§4) is
> `--cast-stop=pin`'s `0x002C`, a different call site with a different payload.**

### 1.4 The fire rate, scored against the parallel note's prediction — OBSERVED

```
resync evaluations: 52 over 47.46 s span
fires: 18 = 22.75/min = 34.6% of evaluations
fired separations: min 123.5  p50 236.4  max 1916.9 u
```

`p5-resync-disarm.md` §3.6 / prediction P6 says *"4-10 fires/min and 20-35% of position
reports, not the 25.4/min the flag block projects"*, and adds *"a rate near 25/min means the
shipped-default regime is not what I replayed"*. The measured run is **22.75/min** — the flag
block's own projection is the better estimate here, and the replay's is ~4× low.
**CAVEAT, stated because it matters:** the 0820 run granted nothing, so its modelled sync copy
sat parked while the player walked away, which grows separation as fast as it can grow. It is
not the shipped-default regime either. The honest reading is that **neither number is a
prediction for a modern run**, and the replay's figure should stop being quoted as one.

---

## 2. THE REFUTATION — a `0x0029` disposed of a pending far arrival. Twice.

Method: scan every `movetap` tape for a `+0x48` that went to **0 with more than 300 ms still to
run** — an arm that vanished without maturing. Four events exist corpus-wide. Two of them are
`--cast-stop=pin`'s `0x002C` (§4). **The other two are in captures where our server sent no
`0x002C` at all.**

**Positive control on the negative claim**, run before believing it: the same opcode counter on
those two captures returns `0x0029 = 145` / `0x0029 = 174` and `0x0025 = 170` / `0x0025 = 280`
while returning `0x002C = 0`. The counter finds sends it should find. **OBSERVED.**

### 2.1 THE CLEAN ONE — `movetap-20260822T165918.jsonl` L512→L513, OBSERVED

```
L512 now=65967 stop=66514 upd=65563 sep=42.09 sync=[10506.37,6339.21] async=[10535.50,6308.83]
                                     point=[10437.99,6433.35] target=[10599.08,6211.55] vel=[169.24,-233.03]
L513 now=66118 stop=0     upd=66105 sep= 9.50 sync=[10518.49,6325.20] async=[10511.33,6331.45]
                                     point=[10518.49,6325.20] target=[inf,inf]          vel=[0.0,0.0]
```

and on the wire, `vault/captures/gamesrv/authsrv-20260822T165910-c1.jsonl`:

```
t=69.613  SENT 0x29  ZERO LEAD (10518,6325) plane 0 [dir legacy+zero-lead]
```

* the arm at L512 had **547 ms to run** (`66514 − 65967`) and its destination was **396 ms of
  leg** away (`|target − sync| = 155 u`);
* one sample later `+0x48 = 0`, `+0x9c = (inf, inf)`, `+0x78 = sync = (10518.49, 6325.20)` —
  **bit-for-bit the point the `0x0029` granted**, and velocity **exactly zero**;
* the rendered copy moved **33.10 u**, in its own direction of travel, and kept going
  (`sep` 9.5 → 43 → 81 → 115 u over the next 350 ms). **No warp. No snap. Nothing.**

**A stale far destination was disposed of by an `AGENT_MOVE_TO_POINT`, at zero cost to the
player, with no `0x002C` within a mile of it.**

### 2.2 THE DIRTY ONE — `movetap-20260821T172133.jsonl` L149→L150, OBSERVED

```
L149 now=32817 stop=33666 upd=32017 sep=315.45 g1=ABOVE
     sync=[10931.48,5366.59] async=[10834.95,5666.90] point=[10867.21,5587.84]
     target=[10999.77,5131.51,plane 18]  vel=[80.34,-276.57]
L150 now=32917 stop=0     upd=32886 sep=  6.08 g1=below
     sync=[10940.40,5348.81,plane 18] async=[10938.88,5354.69] point=[10940.40,5348.81]
     target=[inf,inf]                    vel=[0.0,0.0]
```

wire (`authsrv-20260821T172112-c1.jsonl`):

```
t=35.914  SENT 0x29  AGENT_MOVE_TO_POINT(11000,5132 on plane 0->18)   <- arms the far destination
t=36.687  SENT 0x29  AGENT_MOVE_TO_POINT(10940,5349 on plane 0->18)   <- from MOVE_TO_COORD [10940.4013671875, 5348.80517578125]
```

* the arm had **849 ms to run** and its destination was **475 u** away;
* it vanished, destination erased to `[inf, inf]`, `+0x78` = **`[10940.40, 5348.81]`**, which is
  the second grant's point to the movetap's 2-dp precision, **and the copy's plane became 18**,
  which is the *grant's* plane (`0->18`) — the client's own reports were still plane 0 at
  `t=36.465` and only became 18 at `t=36.765`, *after*. Velocity → exactly 0.
  **Three independent fingerprints all say "the grant's bake wrote this", not "the client
  reconciled onto its history".** OBSERVED.
* **and the rendered copy jumped 329.05 u** (`(10834.95,5666.90) → (10938.88,5354.69)`),
  collapsing `sep` from 315.45 to 6.08 across the client's own gate-1 cut (`g1` "above" →
  "below"). The paired wire shows the same event as `position_report drift=356.07` at
  `t=36.765`. **UNVERIFIED** which of the two fired first, but the co-occurrence is measured.

**This event is the load-bearing one for a second reason.** It carries the *exact* movetap
signature the claim's supporting evidence relies on — `stop → 0`, `target → [inf,inf]`,
`sep → ~0` — **and it is a 329 u warp of the player's body.** So:

> **"We sent a `0x002C`, and the movetap then showed `target → [inf,inf]`, `stop → 0`, `sep → 0`,
> therefore the `0x002C` disarmed it harmlessly" is not a valid inference.** The same signature
> is produced by a `0x0029`, and it is produced by a warp. What discriminates harm is only
> **where both copies land relative to the player**, never the signature.

### 2.3 What survives of the claim's second half

The narrow mechanical sentence — *"a `0x0029` cannot reach the `+0x48` clear at `0x006021E6`"* —
is **not** contradicted by either event: in both, the clear was reached by the arrival primitive
running one tick after the bake armed at `now+1` (`0x005FEAD6`'s short-circuit arm; SOURCED from
`p5-resync-disarm.md` §2.2, and corroborated here by `vel = [0,0]` and `+0x78 = D`).

What IS refuted is the sentence's **operational content**, which is what the whole argument
rests on: *"can therefore only ARM or RE-ARM a destination, **never disarm a stale far one**"*,
used to conclude that only `--resync` can remove F35's stale arm. **A `0x0029` removed a stale
far arm, at zero cost, in the corpus, twice.**

The real discriminator is not the opcode. It is **`|D − the sync copy's settled +0x78|`**:
* under ~1 u → the bake short-circuits, parks the copy, arms at `now+1`, and the destination is
  gone next tick with no leg walked (the two events above);
* over that → a full bake, and the copy **walks** the leg — which is F27/F33/the `--stop-echo`
  symptom.

`0x002C`'s advantage is that it makes `|D − +0x78|` **irrelevant** by teleporting the copy to
`D` instead of walking it there. That is a real and important advantage — but it is a
**magnitude** argument, not the categorical one the claim asserts, and the claim should be
restated that way. Note also that a zero-lead `0x0029` lands in the short-circuit only
**6 of 539 times** (1.1%; SOURCED, `REALFIX.md:68` via `grantsim.py`), which is exactly why the
route is unreliable rather than unavailable.

---

## 3. The payload-provenance distinction is real in the code and INERT in the run

The record's framing (`authsrv.py:3850-3866`) is:

> *"IT SENT OUR INTEGRATOR'S POSITION. This does not, and **that is the whole of the difference
> between the two**: THE PAYLOAD IS THE CLIENT'S OWN LAST ACCEPTED REPORT, NEVER `state["pos"]`."*

**In the code the distinction is real — SOURCED, citations resolve.** `_resync_verdict:4030`
reads `state.get("client_pos")` and returns it as the payload; `state["client_pos"]` is written
at `authsrv.py:3764` on `_take_client_position`'s **accept path and nowhere else**; the verdict
refuses outright (`"no-client-report"`) if it is absent.

**In the only run it did no work — OBSERVED.**

```
fired = 18   payload-vs-ours differing by > 0.01 u: 0   max |payload − state["pos"]| = 0.0064 u
```

The reason is structural, not accidental: `_take_client_position` executes
`state["pos"] = reported` three lines above `state["client_pos"] = ...` (`:3752` and `:3764`),
and **both** `_maybe_resync` call sites run in the same handler invocation as the take
(`:13904` — *"It sits AFTER the take"* — and `:15004`). So at the instant of every fire,
`state["pos"] == state["client_pos"]`, and a build that sent `state["pos"]` from these two call
sites would have put **the identical 18 messages** on the wire.

> **The safety of `--resync` relative to the removed build comes from WHERE it is called (a
> report handler, `age ≈ 0`), not from WHICH variable it reads.** The removed build sent from
> the world tick, where `state["pos"]` is the integrator's extrapolation and can be a whole leg
> old — that is the difference, and it is a call-site difference. The published sentence
> "that is the whole of the difference" attributes the safety to the wrong term, and anyone
> reasoning from it will conclude that a payload swap alone is sufficient. It is not; the
> **staleness gate and the call site** are.

This is a correction to the framing, not a refutation of the flag. `RESYNC_MAX_REPORT_AGE` is
the term that actually bounds the harm, and it is only ever exercised because the call site
makes `age ≈ 0` (the parallel note measures 0 `stale` refusals in 558 replayed reports —
SOURCED, and consistent with what I see here: all 18 fires log `"age": 0.0001`-scale values).

---

## 4. The three armed `0x002C` disarms the corpus actually holds — and whose they are

All six `0x002C` our server has ever sent with a `movetap` watching are `--cast-stop=pin`'s.
Aligned to their payloads by exact coordinate match (no clock assumption needed):

| capture | wire | `+0x48` before | sync copy jump | **rendered copy jump** | after |
|---|---|---|---|---|---|
| `130918` L163 | `t=24.717 CAST-STOP PIN (-5298,-2401)` | **armed**, 32 ms left | 229.14 u | **10.56 u** | `stop=0`, `target=[inf,inf]`, both copies on the payload |
| `130918` L279 | `t=34.010 (-5175,-2426)` | parked | 278.83 u | 18.48 u | both copies on the payload |
| `130918` L396 | `t=43.254 (-5274,-2283)` | parked | 162.93 u | 12.59 u | both copies on the payload |
| `130918` L505 | `t=52.046 (-5267,-2407)` | parked | 100.44 u | 6.73 u | both copies on the payload |
| `140548` L259 | `t=52.581 (-5101,-2446)` | **armed**, 1629 ms left, dest 512 u away | 517.61 u | **9.86 u** | `stop=0`, `target=[inf,inf]`, `sep=0.00` |
| `140548` L556 | `t≈75.5 (-3494,-2526)` | **armed**, 1583 ms left, dest 512 u away | 523.09 u | **2.10 u** | `stop=0`, `target=[inf,inf]`, `sep=0.00` |

**OBSERVED**, all six, by payload-coordinate match to 2 dp.

**I hunted for the counter-example the brief asked for — a `0x002C` after which an arrival
teleport fired anyway inside the same armed window — and there is none.** 3 armed cases, 3
disarms, 0 survivals. **Part (i) of the claim survives.** So does the sub-claim that the
`0x002C` lands both copies on the *message's* point rather than on the stale `+0x9c`: in all
six, `sync_at == async_at == payload` on the next sample.

**But two caveats bound how far that carries — OBSERVED:**

1. **The payload was not `--resync`'s.** `--cast-stop=pin` sends `cast_stop_reckon()`, which is
   an **extrapolation**: `dist = rate * 288.0 * dt; est = (pos + heading/mag * dist)`
   (`authsrv.py:1906-1909`), navmesh-clipped. `authsrv.py:1944-1946` says so explicitly, in a
   sentence contrasting it with the flag under discussion: *"pairing a reckoned position with
   the plane of a point up to a report-gap behind it splits a 'position and plane are one fact'
   invariant that `--resync` never breaks (**its payload is the report itself**)"*. So the
   corpus's evidence for "a `0x002C` disarms cheaply" was produced by the payload shape closest
   to the **removed** build's, and it still only cost the rendered copy **2.10-18.48 u, all
   forward**. That is mildly good news for P5 (whose payload error is smaller), but it is
   evidence about the pin, not about P5.
2. **n = 3, one flag, one afternoon, one player.** Every one of the three is a *cast*, where the
   body is stopping anyway. None is F35's trigger.

---

## 5. F35 in its own capture, against the two `0x002C` in the same tape

`movetap-20260825T140548.jsonl` — every `+0x48` clear in the tape, OBSERVED:

```
L68   now=35435  matured normally   async step  23.04
L111  now=38894  matured normally   async step 177.41   <- F35
L217  now=47877  matured normally   async step   0.00   <- the short-circuit park
L259  now=51332  DISARMED (1629 ms early)  async step  9.86   <- 0x002C #1
L530  now=73376  matured normally   async step  23.91
L556  now=75480  DISARMED (1583 ms early)  async step  2.10   <- 0x002C #2
```

**F35's warp (L111, `now = 38894`) precedes both `0x002C` sends (`now ≈ 51332` and `75480`) by
12.4 s and 36.6 s.** So the brief's suspicion resolves in the claim's favour: nothing had been
sent that could have disarmed it, and F35 is not a counter-example to part (i).

It is, however, the exact shape of a different problem: **the shipped `0x002C` sender does not
fire in F35's regime.** `--cast-stop=pin` fires at a reckoned *cast*; F35 fired at an ordinary
walk-stop with no cast, and the tape is wire-silent across it. Any claim that "we now send
`0x002C`, so F35 is covered" is false, and the tape says so.

**And a stale published line, already flagged by the parallel lens but understated:**
`PROBE-GATEFIRE.md:748` and `resyncscore.py:31` say our server has sent `0x002C` **zero** times
in the vault. It is not merely stale since `--cast-stop=pin` (2026-08-25, 6 sends) — it was
already false on **2026-08-20**, when `--resync` put **18** on the wire. **OBSERVED.**

---

## 6. What this does to the argument, stated plainly

| leg of the claim | verdict |
|---|---|
| a `0x002C` disarms a pending `+0x48` | **SURVIVES.** 3 of 3 armed cases in the corpus; no counter-example found; both copies land on the message point every time (6 of 6). |
| a `0x0029` "can only ARM or RE-ARM … never disarm a stale far one" | **REFUTED.** Two measured events (`0822` L513, `0821` L150), positive-controlled, in captures with `0x002C = 0`. |
| therefore `--resync` **would** zero F35 | **NOT ESTABLISHED, and now testable in a way the record did not know about.** The one `--resync` run granted nothing, so it never armed an arrival; no movetap watched it; F35's own regime has never had a `0x002C` in it. The prediction is still a prediction. |
| it explains the 2026-08-19 `--stop-echo` "ADDS a SECOND destination" | **The "second destination" reading is dead either way** — the corpus shows a `0x0029` *erasing* the destination to `[inf,inf]`, so a grant demonstrably does not accumulate. But the `0x002C`-vs-`0x0029` categorical split is not what kills it; the walked-leg explanation is (SOURCED, `p5-resync-disarm.md` §5.5), and my §2.3 supports that framing. |

**The claim's conclusion may still be right. Its stated reason is not the reason.** The correct
statement of the mechanism the corpus supports is:

> A `0x002C` **teleports** the authoritative copy to its payload and clears the arm; a `0x0029`
> makes the copy **walk** to its payload and re-arms for the length of that walk. Both dispose
> of the old destination. The harm is the walk, and the walk is `|D − copy|` long. `--resync`'s
> value is that it drives that length to zero **by construction** rather than by luck (1.1% of
> zero-lead grants, SOURCED `REALFIX.md:68`).

---

## 7. WHAT WOULD REFUTE *THIS* NOTE

* **§2 falls** if the two `0x0029` events can be shown to be something else — most plausibly a
  client-internal reconcile that happened to coincide. I ruled that out on three fingerprints
  for `0821` L150 (landing point = the grant's point to 2 dp; **plane 18, which only the grant
  carried at that instant**; velocity exactly 0) and on `sep = 42 u` (far below gate 1) for
  `0822` L513. A movetap poll faster than 10 Hz, or a hooked watchpoint on `+0x48`, would
  settle it outright. My alignment for `0821` uses `updated (+0x58) = 32886` against the grant
  send at `t = 36.687` — a bit-exact coincidence, not a clock estimate.
* **§1 falls** if `authsrv-20260820T182119-c1.jsonl` was produced by some *other* build that
  happened to print the identical f-string and the identical record schema. **I closed this
  door — OBSERVED:** `git show 3e40bde:toolkit/authsrv/authsrv.py | grep -n` returns the sender
  at that commit's `:2722-2723` (`f"RESYNC 0x002C at (…) plane {plane} " f"-- the CLIENT's own
  report, {age * 1000:.0f} ms old, closing a "`) and the record at `:2709`
  (`rec.event("resync", fired=fire, reason=reason,`). The string and the schema both existed
  34 minutes before the capture and are `-S`-unique to that commit in the whole history.
* **§3 falls** if a fire can occur at a call site where `state["pos"] != state["client_pos"]`.
  I checked both call sites (`:13904`, `:15004`) and both take-then-resync; a third call site
  added later would reopen it, which is an argument for asserting the invariant in code.
* **§4's "n = 3" caveat dissolves** the moment a `--resync` run is taken with a movetap
  attached. That is the experiment that has still never been done, and §1 shows it is one
  evening's work, not a new build.
* **My negative claims are positive-controlled** (the opcode counter finds 145/174 `0x0029` and
  170/280 `0x0025` in the same files where it finds 0 `0x002C`; the `+0x48`-clear detector finds
  the six known `0x002C` events and F35). Where I could not measure — which of the reconcile or
  the bake fired first at `0821` L150 — I said so rather than guessing.

## 8. CORRECTIONS THIS NOTE ASKS THE STUDY TO ABSORB

1. `FINDINGS.md:3892` and the follow-on brief: **`--resync` has been run** —
   `authsrv-20260820T182119-c1.jsonl`, 2026-08-20T22:21:29Z, 18 fires, 0 hard jumps,
   0 grants. (§1)
2. `PROBE-GATEFIRE.md:748` / `resyncscore.py:31` — *"our server has sent `0x002C` zero times"*
   was already false on 2026-08-20, not merely since `--cast-stop=pin`. Corpus total: **24**
   (18 + 6). (§1, §5)
3. `authsrv.py:3850-3866` — *"that is the whole of the difference between the two"* attributes
   P5's safety to the payload variable. Measured, the variable is inert at the fire instant
   (18/18, ≤ 0.0064 u); the difference is the **call site**. (§3)
4. `p5-resync-disarm.md` §3.6 / P6 — the replayed 5.60 fires/min is contradicted by the actual
   run's **22.75/min**. Neither figure is a prediction for the shipped-default regime; both
   should carry their regime. (§1.4)
5. Any argument of the form "the movetap showed `target → [inf,inf]` and `sep → 0`, so the
   `0x002C` disarmed it harmlessly" needs the landing-point test attached — the same signature
   accompanies a 329 u warp at `movetap-20260821T172133` L150. (§2.2)
