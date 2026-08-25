# The REALFIX follow-on recon — what the 2026-08-25 desk session settled

**Branch `claude/movement-realfix-followon-a1`, worktree
`.claude/worktrees/movement-realfix-followon-a1`, off `main` at `d5da5e8`.**

Written against [CANCELWALK.md](../CANCELWALK.md) §0's *"Session handoff for the
follow-on gaps"*. **The CANCELWALK arc stays CLOSED — nothing here reopens it.**

**No client, harness or `session.py` was launched.** Every number below comes
from static disassembly of the pinned pristine build-38797 image
(`vault/client/2026-07-29_221c13772c7a/Gw.exe`) or from existing vault captures.
Five recon lanes plus three adversarial skeptics, 550 tool calls; the skeptics
were given the load-bearing claim and told to refute it, defaulting to *refuted*
under uncertainty.

Labels throughout the notes: **OBSERVED** (measured here), **SOURCED** (a doc or
the binary says it and the citation was checked to resolve), **UNVERIFIED**
(reasoning).

---

## The five notes

| Note | Covers | Headline |
|---|---|---|
| [p5-resync-disarm.md](p5-resync-disarm.md) | handoff 1 — P5 vs F35, the `--stop-echo` reconciliation | The disarm mechanism is CONFIRMED and **already measured in-corpus**; the `--stop-echo` refutation does **not** transfer to `--resync`, but not for the reason first proposed |
| [f35-counterfactual.md](f35-counterfactual.md) | handoff 1 — F35's no-cast counterfactual | **F35 fires castless and it is already on tape — the owner's 30-second run is not needed.** And F35's framing needs correcting: 586 arrival fires, only 8 move the body |
| [f33-trigger.md](f33-trigger.md) | handoff 1 — F33's trigger | The polyline hypothesis SURVIVES, and the binary supplies the missing half: **only a walk start empties the history chain** |
| [cancelwalk-residuals.md](cancelwalk-residuals.md) | handoff 2, 3, 4 | Two residuals **STRUCK**, one **re-filed to REALFIX**, two sized to a one-line gate; bookkeeping **CLEAN and run** |
| [slow-plateau.md](slow-plateau.md) | handoff 2 — the slow-plateau regime | **Not a speed regime at all** — it is collision sliding, with a measured 94.0 u/s floor |

---

## 1. What is ANSWERED, and needs no owner run

### 1.1 F35's no-cast counterfactual — ANSWERED FROM TAPE

The handoff's first action item was *"30 seconds of owner run time: walk, stop,
stand still ~2 s"* to see whether F35's arrival teleport fires with no cast.
**It does, and the evidence already existed.**

`movetap-20260821T124010.jsonl` L1785 × `authsrv-20260821T123942-c1.jsonl` at
`gs_t = 254.194`: a parked body jumps **54.20 u backward onto the armed
zero-lead grant destination** in one 121 ms sample, exactly as the sync copy
arrives; `+0x9C` → `[inf,inf]`, `+0x48` → 0. That capture holds **zero `0x0046`
USE_SKILL frames**, zero clicks, all-`zero-lead` grants, and **8.58 s of total
server silence** across the event. Two further castless drags exist
(`movetap-20260821T082702` L1195/L1644, 26 u and 29 u). **OBSERVED.**

**Consequence: the "quiet window" nuance drops out. F35 is fully REALFIX's, and
the prediction registered for the run is retired as already-satisfied.** The
registered form is kept in [f35-counterfactual.md](f35-counterfactual.md) §5 in
case the owner wants the live confirmation anyway; it is bounded to 5 minutes.

### 1.2 …but F35's own framing was over-read, and this is the bigger finding

Scanning 31 movetap captures (42,784 samples) against 119 indexed `ours`
gamesrv captures: **586 arrival fires. Only 8 drag the drawn body.** The other
578 land the sync copy exactly on the armed point with the tick consumed, and
the body does not move.

Gap magnitude was eliminated as the discriminator (drags at 26–177 u,
non-drags at 9.8–433.7 u — **full overlap**), as were `sep`, gate 1, the async
copy's own arm, `async_branch`, and parked duration. **What gates the drag could
not be determined.** §8.3f's reading of its single instance is right about that
instance and **is not a rule**.

> Leading hypothesis, **UNVERIFIED** but binary-grounded: `0x006020B0` recurses
> at `0x0060221E` over a propagation list at `[ebx+0x28]`/`[ebx+0x30]`;
> `--field 0x28 --in AgAgent --writes` finds only two clears, so the populating
> writer sits in one of `codescan`'s documented blind spots.

**This is the single most important correction in this session**: F35 is real
and castless, but "the armed destination fires and drags the body" is a ~1.4%
outcome, not the mechanism's default. Any exposure number built on the
586-fire population is ~70× too high.

### 1.3 Exposure, re-measured and ~8× wider than §7.8

235 stops across 24 zero-lead click-free captures. **§7.8's table reproduces
row-for-row on its own four captures** (the positive control). Extended:
owner-driven staleness p50 **54.3 u**, **18 of 96 stops past 190 u — one stop in
five**, max 748.3 u. Drag rate on owner-era tapes: **3 in 477 s, one per
~2.6 min.**

**Sharpening §8.3f:** report-overrun *is* chord-bounded (0 of 235 over 512 u,
max 498.2 u) — but **grant-staleness, which is F35's actual magnitude, is not**
(4 of 235 over 512 u). The chord bounds the wrong quantity.

---

## 2. The disarm mechanism — CONFIRMED, and it was already in the tree

`0x002C` AGENT_UPDATE_POSITION (handler `0x005FDA50`) SetPositions **both**
copies — `0x005FDAE5` on the sync array `[esi+0xE8]`, `0x005FDB49` on the async
array `[esi+0x14C]` — through `0x00602B20`, whose armed arm
(`cmp [ebx+0x48],0` at `0x00602B44`) hands a **by-value copy of the caller's
point** (`0x00602B5E`–`0x00602B6F`; callee `ret 0x10` at `0x006022AC`) to
`0x006020B0`, which writes `+0x78` from its own args
(`0x00602132`/`0x0060213A`/`0x00602143`/`0x0060214F`), erases
`+0x88/+0x8c/+0x9c/+0xa0` to the `+inf` sentinel at `[0x948654]`, and clears
`+0x48` at `0x006021E6` — straight-line, no branch target inside the range.
**OBSERVED, by three independent agents.**

**`[0x948654] = 0x7F800000 = +inf`**, read out of the image (positive control in
the same read: `[0x946560] = 100.0`, the match radius, and `[0x946564] = 300.0f`,
gate 1's cut — both exactly as documented). **That sentinel is the
`target → [inf,inf]` every movetap row shows at a fire.**

### 2.1 It is no longer a prediction — the shipped default already sends it

`--cast-stop=pin` ships `0x002C`. **24 sends exist in the `ours` corpus, six
with co-timed movetap.** The decisive row pair
(`authsrv-20260825T140517-c1` × `movetap-20260825T140548`): a `0x002C` landed
**0.15 s into a 1.78 s armed window whose destination was 512 u away**; both
copies went to the message's own point, `+0x48` → 0, `target` → `[inf,inf]`,
`sep` → 0.00, and the **rendered** body moved **9.86 u** — inside its ordinary
per-sample glide. Across all six: both copies land on the payload to
0.004–0.006 u, rendered displacement 6.73–23.33 u. **No warp. OBSERVED.**

### 2.2 Three claims of mine that the skeptics killed

All three skeptics returned `refuted = true`. Every one of them **confirmed the
core mechanism** and refuted the corollaries I hung on it. Recording them
plainly, because the corollaries were mine:

1. **"A `0x0029` can only arm or re-arm, never disarm"** — the narrow mechanical
   sentence (a `0x0029` cannot itself reach `0x006021E6`) survives, but the
   *operational* claim is **measured false**. Two corpus events show a `0x0029`
   disarming a pending far arm: the `<=1.0 u` short-circuit arms at `now+1` and
   fires one tick later *through the arrival primitive*
   (`movetap-20260822T165918` L512→L513, arm had 547 ms left, destination 155 u
   out; `movetap-20260821T172133` L149→L150, 849 ms left, 475 u out — both in
   captures where our server sent **zero** `0x002C`, positive-controlled).
2. **"This simultaneously explains the 2026-08-19 `--stop-echo` 'adds a second
   destination'"** — **REFUTED.** Re-arm is overwrite, not addition: the leg
   state is single-valued scalars and `0x00602A40` overwrites the destination
   *above* the bake's short-circuit branch, so every `0x0029` overwrites
   unconditionally. `authsrv.py:1149` ("set once … NEVER re-armed") is
   **refuted by the binary**; `authsrv.py:1103` ("or until a newer grant
   overwrites it") is right.
   The two destinations lived on **two different copies** — movetap carries
   `stop` and `async_stop` as *independent* arrival ticks, and in 3 of 6
   measured events the sync copy was parked while the async copy was armed.
   `0x0029` is **SYNC-ONLY**; `0x002C` is the one catalogued primitive reaching
   both ungated.
3. **"Therefore `--resync` would zero F35"** — **NOT ESTABLISHED.** The
   mechanism is proved; the **cadence** is not. F35 is wire-silent by
   definition and `--resync` is report-driven.

**The reconciliation the handoff asked for, in the form the evidence supports:**

> A `0x002C` **teleports** the authoritative copy to its payload and tears the
> leg down on **both** copies. A `0x0029` makes the copy **walk** to its
> payload, on the **sync** copy only, re-arming for the length of that walk.
> Both dispose of the old destination. **The harm is the WALK, and its length is
> `|D − the sync copy's settled +0x78|`.** `--stop-echo` failed because that
> length was ~1,286 u (reconstructed from the 2026-08-19 capture's own
> geometry); retail's stop-ack has the *same mechanism* with a p50 of ~60 u.
> **Same shape, two orders of magnitude of harm** — so the refutation is of
> *baking a long leg from a far copy*, which is precisely what `0x002C` does
> not do.

### 2.3 A premise in the handoff is wrong

**`--resync` has been RUN.** `authsrv-20260820T182119-c1.jsonl` holds **52
resync verdict rows, 18 fired, 18 `0x002C` sends** (I verified this count
myself, independently of the lanes). Commit `3e40bde` lands the sender 34 min
before the capture's wall clock.

**But it is not a test of the disarm**: that run sent **zero `0x0029`**
(verified — `opcode 41 = 0`), so it never armed an arrival. `movesync --wire-only`
reports `GRANTS 0`, `0.00 hard jumps/min`. **The missing experiment is one
evening with grants enabled and a movetap attached, not a new build.**

---

## 3. F33's trigger — the polyline hypothesis SURVIVES, sharpened by the binary

The registered hypothesis was that `sep` is the wrong variable and *distance to
the client's own history polyline* is the right one. **OBSERVED true at both
named non-snap cells, to two decimal places**: R10's 505–522 u in-walk episode
has `poly_d` **0.00–0.01 u** across all 28 samples (the chain still holds nodes
2.1 s back, sitting exactly where the copy now is); R9's ~312 u non-snap has
`poly_d` **0.00 u**.

**The binary supplies the missing half of the walk-start asymmetry.** The local
input arm `0x00605F10` **NULLS the chain head** at `0x00605F4F`, then seven
instructions later sets the destination through `0x00602A40` → the bake → the
dispatch. And the arm is a **no-op on an already-armed record**
(`0x00605F3F`/`0x00605F43`). So **only a walk start empties the chain**; a
held-key walk never does. At a walk start there is barely a polyline at all, and
what little there is points the *wrong way*.

**Sharpened trigger statement (SUPPORTED, not OBSERVED):**

> F33 fires when our answer's grant bake dispatches the desync test into a
> freshly-armed fence whose history chain the arm has just emptied, with
> separation above 299.33 u. An in-walk answer does not fire it because the
> fence was already open, the arm was a no-op, and the chain still holds nodes
> the lagging copy is sitting on.

**Honest limit:** evaluation is itself conditional on *(a dispatch occurs)* AND
*(`clientControlled` is set)*, both event-scale. R10's 11 s at 864 u passed
harmlessly not because `poly_d` was small — it was 864.5 — but because nothing
dispatched. **The movetap corpus samples at ~10–20 Hz and cannot resolve
either.** That gap does not close from captures.

---

## 4. The residuals (handoff 2, 3, 4)

| # | Residual | Verdict |
|---|---|---|
| 1 | Instant-skill divergence | **REAL-AND-SIZED → NEEDS-A-RUN.** A genuine one-line gate: `activation` is bound at `authsrv.py:8656` and live at the gate at `:8940`, same function scope. **The residual's wording is wrong: signets are not instants** (64 of 66 carry an activation time). |
| 1b | *(bonus)* "retail never stops a runner at a cast start" | **DOC CLAIM REFUTED.** Retail's own bare `0x0028` at a cast start is witnessed **4×**, one at cruise speed, immediately after the `0x00E4`. |
| 2 | The click-leg death | **MECHANISM FOUND → STRUCK from CANCELWALK, RE-FILED to REALFIX.** It is the `+0x48` arrival timeout on a destination *the client* armed at the click. The cast is not in the chain — our cast-end burst had not even been sent when the body froze. |
| 3 | Adrenal `0x00D2` adjacency | **STRUCK.** 2 messages / 22 bytes; the 39-of-39 invariant is attack-skill-scoped and already excluded by `not is_attack`; retail's own non-attack adrenal burst breaks the adjacency; both handlers are stateless argument forwarders. |
| 4 | Queued begins | **REAL-AND-SIZED → NEEDS-A-RUN.** `begin_cast()` has no cast-stop and no console label; the branch is exercised **zero times** in the whole gamesrv corpus. **Not a one-liner** — `activation` is not in scope there. |
| 5 | R6's converged-copy precondition | **WRITTEN** — [cancelwalk-residuals.md](cancelwalk-residuals.md) §5, with VOID rules and an instrument requirement. |
| 6 | `test_replay.py` bookkeeping | **CLEAN — verified statically AND run.** `ALL CHECKS PASSED (10 checks)`, floor 4. The module surface is unchanged as predicted. One stale count in its own docstring, noted. |

### 4.1 The slow plateau is not a rate regime

**It is the body pinned against map collision geometry and sliding along it.**

- **The client never reports a sub-cruise speed anywhere.** Across 42,784
  samples `maxspeed (+0x5C)` is `288.0` and `movespeed (+0x60)` is `1.0`, with
  *zero* other values; cached velocity `+0xB0/+0xB4` has magnitude `288.0` in
  **all 13,767** moving samples and `0` otherwise. **Locomotion is bang-bang:
  288 or nothing.** That was the decisive check and it came back flat.
- Every geometrically testable plateau lies on a straight line to ~0.002 u for
  seconds, at **round map coordinates** (`x=0`, `x=1248`, `x=3072`, `y=0`,
  `y=1728`, `x−y=9792`, `x+5y=17184`), reproduced across sessions days apart at
  the same places. **That is a wall.**
- The slide obeys `speed = max(288·cos(incidence), FLOOR)` with **`FLOOR = 94.0
  u/s`** measured (`0.3307 [0.3290, 0.3320]` of same-instrument cruise). The
  projection half is ordinary collide-and-slide; **the floor is genuinely new
  and its mechanism is UNVERIFIED.**

> **DOC CLAIM CONTRADICTED.** `FINDINGS.md:1209-1211` — *"plateaus at ½ and ⅓ of
> each type's own cruise, 27% of forward moving time"*. The **27% reproduces**
> (22.3–25.6% depending on slicing). **The "½" plateau does not exist** — there
> is no 144 u/s cluster in the corpus at all. The "⅓" sits at **0.331** and is
> not a cruise fraction at all. Likely origin of the phrasing, **UNVERIFIED**:
> 93.8 u/s is simultaneously ~⅓ of forward cruise (288) and ~½ of backward
> cruise (187.8) — one constant read under two family baselines.

**Risk to the shipped `--cast-stop=pin`: REAL, PRICED, UNEXERCISED.** A pin
fired during a slide misses by `~294 u/s × gap` unclipped (a vector difference
at ~84°, *not* `288−94`), breaching the 32 u / 35 u bars above ~0.11 s; clipped
against our navmesh it degrades to `93.8 u/s × gap`, breaching at 0.34 s.
**However: 0 of 80 casts in the whole corpus landed in a slide.** An unexercised
door, not an observed defect — and *not* the forward-miss signature §8.3c
predicted.

---

## 5. Does P5 clear Q10? — honestly, not outright

Q10's bar: *"the stock game doesn't warp, i am not going to accept a fix that
still warps."*

- **At the stop — F35's regime — P5 is a strict improvement with no measured
  cost.** Stop-arm yank measured **p50 0.0 u** over 27 fires: the client is
  standing still at exactly the point being sent. Replaying the shipped
  `_resync_verdict` against F35's own capture fires at the stop `t=38.800` with
  modelled `sep = 177.4 u` — **F35's own magnitude to 0.01 u** — **1.098 s
  before the arrival matured**.
- **`RESYNC_MAX_REPORT_AGE` never bites.** Both call sites (`:13904`, `:15004`)
  invoke `_maybe_resync` in the same handler breath as the take, so `age ≈ 0` by
  construction: **0 `stale` refusals in 558 reports**.
- **But P5 BOUNDS the snap rather than removing it.** Staleness under
  `RESYNC_SEPARATION` still bakes a real leg (380 of 558 reports refuse
  `in-agreement`). At 100 u the residual is a ~100 u snap; at 299.33 u it is a
  ~299 u snap. **That fails a literal reading of Q10.**
- **The threshold is unreconciled between two files**: `authsrv.py` uses
  **100.0**; `resyncscore.py` uses **299.332591** and argues explicitly against
  100. It *is* the residual magnitude, so this is not cosmetic.
- **The payload-provenance argument is inert as written.** Over all 18 fires of
  the 2026-08-20 run, `|payload − state["pos"]| ≤ 0.0064 u`, because
  `_take_client_position` writes `state["pos"]` three lines above
  `state["client_pos"]` and both call sites run in the same invocation.
  **The safety is the CALL SITE, not the variable.**
- **The measured 0.0–0.0001 s payload age is a LOOPBACK number** and
  `authsrv.py` says so itself (`client_pos_at` excludes both network legs).
  Over a real link the yank is `288 × latency`. **That is the live risk, not the
  operand.**

**Four named holes** (details in [p5-resync-disarm.md](p5-resync-disarm.md) §3.5):
**A** report-driven, so an arrival maturing inside a report gap is unreachable
(the ~1.8 s chord makes this a coin-flip for the first grant after any refusal);
**B** the `in-agreement` residual above; **C** `rate-limited` on sub-0.5 s
stop-and-go pairs (23 pooled); **D** the sync model is seeded **only** at map
placement — a grant can never seed it, so a missed seed leaves the flag
**silently inert** (reproduced accidentally: `no-sync-model` × 14, zero fires).
**D deserves a startup assertion.**

### 5.1 How retail actually avoids this

My hypothesis was *"retail re-grants every ~0.5 s so its arms never mature"*.
**Partly REFUTED.** Retail's inter-grant gap is p50 **0.489 s** (independently
reproducing `authsrv.py:1152`'s 0.492 s) — but **11.5% of its arms still
mature**, and **3.84% of its grants are F35-shaped** by a separation-and-silence
criterion.

**Retail's protection is the SIGN OF THE LEAD, not the cadence** (UNVERIFIED but
following from the mechanism): retail's destination is the client's *own
proposed endpoint, ahead of the player*, so the copy reckons toward a point the
player is also walking toward and the arrival lands where the reckoning already
is — continuous. Our zero-lead destination is where the player **was**, so the
arrival pulls **backward** over the whole report-overrun. The 0.489 s cadence
then does a second job: it keeps the overrun small when the sign is briefly
wrong.

> **And retail does not use the disarm primitive at all: `0x002C` to the
> player's own agent appears FIVE times in the entire live corpus.** P5 is not
> "what retail does" and should not be sold as fidelity.

---

## 6. Corrections this session asks the record to absorb

1. `authsrv.py:1149` — *"`agent+0x48` … set once … NEVER re-armed"* — **false**.
   Both bake arms write it on every grant.
2. `authsrv.py:1101` — *"no clear anywhere except that arrival"* — **wrong as
   written**: `0x00602AB0` is a non-arrival writer of `+0x9c`.
3. The 2026-08-19 *"the echo ADDS a SECOND destination"* mechanism sentence is
   **unsupportable**. The symptom is a full-bake leg walked from a far copy,
   compounded by `0x0029` being sync-only.
4. `PROBE-GATEFIRE.md:748` and `resyncscore.py:31` — *"our server has sent
   `0x002C` zero times"* — **stale** since `--cast-stop=pin` shipped. 24 exist.
5. **"70 of 88"** should be **70 of 114** (the study's own correction at
   `FINDINGS.md:3782`), or the wider re-derivation **134 of 172** over all 22
   live stamps (147 answered ≤1.0 s, `|dest−stop|` p50 0.000 u, latency p50
   0.034 s). **Quote the denominator.**
6. **`+0x9c` is `m_targetPoint`, not "syncPoint"** (ArenaNet assert
   `AgAgent:1144`; `movetap.py:459-465`). Both the CANCELWALK brief and
   `authsrv.py`'s STOP_ECHO block misname it, and the wrong name collides with
   the sync/async copy distinction that turned out to be load-bearing.
7. `0x006020B0` is **not** "the arrival teleport primitive" — it is an
   operand-neutral `HardSetPosition(p)` that also tears down the leg. Its
   `0x0060032E` call site is the one that passes `+0x9c`; that call site is F35.
8. `FINDINGS.md:1209-1211`'s "½ and ⅓ plateaus" — see §4.1.
9. `FINDINGS.md:3892` and CANCELWALK §0's *"`--resync` … built, NEVER RUN"* —
   **false** (§2.3).
10. The `--resync` flag block's projected rate (*25.4/min, 42.2% of reports*)
    over-states today's build by ~4.5× — measured **5.60/min, 27.8%** over 16
    recent captures.

---

## 7. What still needs the owner, in value order

1. **The `--resync` run that actually tests the disarm** — grants enabled, a
   movetap attached. The 2026-08-20 run had `GRANTS 0` and is not it.
   Predictions registered in [p5-resync-disarm.md](p5-resync-disarm.md) §8.
   **Recipe note, checked in code:** `--resync` alone is enough — the shipped
   `--cast-stop=pin` default **yields** to it (`resolve_cast_stop_default`
   returns `lever:--resync`, `authsrv.py:1807`) and prints the provenance, so
   `--no-cast-stop` is *not* needed. An **explicit** `--cast-stop=pin` with
   `--resync` is refused outright (`:4701`) — one `0x002C` policy per run.
2. **Reconcile `RESYNC_SEPARATION`** (100.0 vs 299.332591) before that run —
   it sets the residual snap magnitude, i.e. the thing Q10 judges.
3. **The instant-skill gate** — a one-line change plus a registered run.
4. **Queued begins** — needs plumbing, then a run.
5. **What gates the 8-in-586 drag** (§1.2) — the highest-value unknown left in
   the staleness family, and it may not be answerable from captures at
   10–20 Hz.

---

*Scripts written during this session live in the session scratchpad, not in the
repo. Nothing outside `studies/movement/followon-notes/` was modified by the
recon lanes.*
