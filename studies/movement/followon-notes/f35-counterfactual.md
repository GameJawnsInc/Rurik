# CANCELWALK-F35 — the no-cast counterfactual, mined out of the existing corpus

Written 2026-08-25, RECON session, worktree `movement-realfix-followon-a1`.
**No client launch, no harness, no `session.py`.** Static analysis of the pinned
pristine build-38797 client plus existing vault captures only.

Every claim carries a tag: **OBSERVED** (I measured it here), **SOURCED** (a doc
or the binary says it and I checked the citation resolves), **UNVERIFIED** (I am
reasoning and have not measured it).

The handoff asked for "30 seconds of owner run time" to register and then test
the prediction that F35's `+0x48` arrival teleport fires **castless**.
**It already has, three times, on tape.** §5 still carries a registered
prediction — but it is now a confirmation with a corrected exposure floor, and
30 seconds is provably too short (§4.3).

---

## 0. The answer, in one paragraph

**OBSERVED. The `+0x48` arrival teleport fires with no cast anywhere in the
session.** `vault/captures/movetap/movetap-20260821T124010.jsonl` L1785, paired
on the wall clock with `vault/captures/gamesrv/authsrv-20260821T123942-c1.jsonl`
at `gs_t = 254.194`: a parked drawn body jumps **54.20 u backward onto the armed
zero-lead grant destination** in one 121 ms sample, at the instant the sync copy
reaches that destination, `+0x9C` flips to `[inf, inf]` and `+0x48` clears to 0.
That capture contains **zero c2s `0x0046` USE_SKILL frames**, zero c2s `0x003E`
clicks, and the server was **silent for 8.6 s** across the event. The mechanism
is §8.3f's F35 exactly, minus the cast.

**F35's "quiet window" nuance drops out. The cast is not part of the mechanism —
it is one of several ways for the player to be quiet. F35 is fully REALFIX's.**

Two further castless drags are on tape (§2.4), and one more in the owner-era
`--cast-stop=pin` regime. **But the corpus also refutes the simple form of the
mechanism**: of **586** arrival fires, only **8** drag the body (§3.3). What
gates the drag I could not determine (§6.1) — and that, not the castless
question, is now F35's open problem.

---

## 1. Row semantics — a correction the doc's wording invites

**OBSERVED, and it matters for anyone re-running this scan.** §8.3f describes
F35 as "the drawn body snapped ... onto the sync copy". In a `movetap` row the
drawn body is **`async_at`**, not `live`/`point`/`sync_at`:

| movetap field | what it is |
|---|---|
| `point` / `live` / `sync_at` | the **SYNC** agent (world 0) — the block `movetap` polls directly |
| `async_at` | the **ASYNC** twin (world 1) — **the drawn body**, and the copy whose position the client REPORTS on the wire |
| `target` / `target_invalid` | the SYNC block's `+0x9C` armed destination |
| `stop` | the SYNC block's `+0x48` arrival tick |

**Proof that `async_at` is the reported body — OBSERVED.** In
`movetap-20260825T140548.jsonl` L96 `async_at` settles at
`[-5482.48, -2407.14]` and stops; the paired gamesrv capture records the c2s
`0x0047` at `t = 38.800` reporting `[-5482.484375, -2407.138671875]`. Same
number, same instant, two independent instruments.

**SOURCED:** `gate1_read`'s docstring in `toolkit/clientscan/movetap.py` — "the
SYNC agent against its ASYNC twin", world 0 for SYNC at `0x006057A3`, world 1
for ASYNC at `0x006057A0`. Citation resolves; I did not re-derive the two clock
sites.

**`+0x48` is an ETA, not a past timestamp — OBSERVED.** At
`movetap-20260825T140548.jsonl` L89 the tick is armed to `38868` while the client
clock reads ≈`37240` — **1.6 s in the future** — and the sync copy is 498 u from
its target, which at 288 u/s is 1.73 s. `movetap`'s own comment names
`A_STOP = 0x48` "`m_timeStopMovement`, absolute ms, 0 = not moving"; the
measurement says the value is the absolute ms at which movement will END, i.e.
the predicted arrival. The grant bake computes it, the arrival primitive zeroes
it.

---

## 2. The mine

### 2.1 What was scanned

**OBSERVED.**

- **32** `movetap` captures in `vault/captures/movetap/`; **31** carry samples
  (`movetap-20260821T123318.jsonl` holds a head record and nothing else).
  **42,816** lines, **42,784** samples, **3,950 s** of tape, all agent id 1.
- **1,167** `.jsonl` under `vault/captures/gamesrv/`; **1,154** carry
  `origin: "ours"`, **13** are truncated before the origin record, **0** carry
  any other origin. **119** hold decoded c2s/s2c movement traffic and were
  indexed for pairing. `vault/captures/live/` was **never opened** — the two
  origins are not pooled anywhere in this note.
- Pairing was by **wall-clock overlap only** (`movetap.t` vs the gamesrv
  origin's `wall_unix`), per §7.4d correction 1. No trajectory fitting anywhere.

Scratch scanners live in the session scratchpad, not the repo:
`f35mine.py` (jump detector + episode counter), `overrun.py` (stop
staleness/overrun), `fires.py` (arrival-fire census).

### 2.2 The detector, and its positive control

**Signature scanned:** a single-sample `async_at` displacement ≥ 50 u at an
implied speed > 360 u/s (1.25× the 288 u/s cruise), coincident with the SYNC
block's `target_invalid` going False→True **and** `+0x48` clearing to 0.

**Positive control — OBSERVED.** The detector must find the one instance the
docs already name. It does: `movetap-20260825T140548.jsonl` L111, jump
**177.41 u**, `landed_on_target = 0.000 u`, `gs_t = 40.046`, cast 0.879 s
earlier and inside the action window. That is §8.3f's F35 to three decimals.
A second positive control for the cast half: the cast-detector returns non-null
`since_last_cast_s` on four hits and null on twelve, and the null captures'
own c2s opcode histograms contain no `0x0046` at all — so "no cast" is measured,
not merely unmatched.

### 2.3 Results

**OBSERVED.** 92 large single-sample body jumps across the corpus. **16 carry
the full arm→fire→`[inf,inf]` signature.** The other 76 are a different family
(the target was already `[inf,inf]` and `+0x48` already 0 — the F27/F33
reconcile class; several are `gate1 = above` with `sep` 400-500 u collapsing to
~15 u, which is F33's shape).

Of the 16:

| capture | line | gs_t | jump (u) | landed on armed pt | body parked | cast in capture? |
|---|---|---|---|---|---|---|
| `movetap-20260821T124010` | 1785 | 254.194 | **54.20** | 0.00 u | yes | **NO CAST IN CAPTURE** |
| `movetap-20260821T172133` | 150 | 36.810 | 329.05 | 231.3 u | no | no cast in capture |
| `movetap-20260821T172133` | 187 | 41.323 | 819.10 | 0.00 u | no | no cast in capture |
| `movetap-20260821T210152` | 717 | 79.876 | 3437.26 | 0.00 u | yes | no cast in capture |
| `movetap-20260822T161918` | 685/847/1042/1748/2046 | — | 413–2259 | 0–24 u | no | no cast in capture |
| `movetap-20260822T165434` | 483/729/979 | — | 715–3575 | 0.00 u | no | no cast in capture |
| `movetap-20260824T141620` | 287 | 49.643 | 150.91 | 0.00 u | no | cast 0.398 s before |
| `movetap-20260824T213708` | 158 | 23.787 | 110.14 | 8.97 u | no | cast 0.034 s before |
| `movetap-20260825T130918` | 1084 | 98.861 | 167.60 | 13.53 u | yes | cast 0.069 s before |
| `movetap-20260825T140548` | 111 | 40.046 | **177.41** | 0.00 u | yes | cast 0.879 s before (§8.3f's F35) |

**12 of 16 sit in captures with zero `USE_SKILL` frames.** Most of those twelve
are not clean counterfactuals though — the 700-3,500 u ones sit in captures with
click-to-move (`0x003E`), deferred click grants, or the `--zero-lead`-off arm,
i.e. mixed regimes and probably not all one mechanism. **Exactly one is clean,
and it is decisive.**

### 2.4 The clean castless instance, at row level

**OBSERVED.** `movetap-20260821T124010.jsonl` ×
`authsrv-20260821T123942-c1.jsonl`. Capture context, from the wire:
c2s opcode histogram `{0x3d: 86, 0x47: 26, 0x9: 64, …}` — **no `0x0046`, no
`0x003E`**: keyboard walking, no casts, no clicks. All 86 grant verdicts are
`arm = "zero-lead"` (79 `zero-lead`, 7 refused `heading-rate`), i.e. **the
shipped grant policy**.

Wire, around the event:

```
253.252  c2s 0x003D  reports (14129.9932, 11093.6885)   drift 128.6   accepted
253.252  s2c 0x0029  ZERO LEAD (14130,11094) plane 0            <- ARMS the copy
253.985  c2s 0x0009  (ping)
259.009  c2s 0x0009  (ping)
261.829  c2s 0x003D  reports (14129.9932, 11093.6885)   drift 767.91  accepted
```

**Nothing at all leaves the server between 253.252 and 261.829 — 8.58 s of
silence.** The warp happens inside it.

Memory, same instants (`gs_t` = wall-aligned):

```
L1778 253.286  body (14136.30,11099.49)  sync (13952.25,10930.15)  tgt (14129.99,11093.69) tick=247863
L1779 253.420  body (14158.66,11120.07)  sync (13973.44,10949.65)  tgt (14129.99,11093.69) tick=247863
L1780 253.576  body (14169.88,11130.39)  sync (14016.26,10989.04)  tgt (14129.99,11093.69) tick=247863   <- body STOPS
L1781 253.713  body (14169.88,11130.39)  sync (14037.66,11008.74)  ...
L1782 253.828  body (14169.88,11130.39)  sync (14058.86,11028.24)  ...
L1783 253.946  body (14169.88,11130.39)  sync (14090.86,11057.68)  ...
L1784 254.073  body (14169.88,11130.39)  sync (14112.05,11077.18)  tgt (14129.99,11093.69) tick=247863  sep 78.59
L1785 254.194  body (14129.99,11093.69)  sync (14129.99,11093.69)  tgt (inf,inf)           tick=0       sep 0.00
```

Read it off the rows:

1. At `253.252` the player's own `0x003D` reports `(14129.99, 11093.69)`; the
   zero-lead policy grants that exact point as a `0x0029` destination — **which
   arms `+0x48` to 247863**, an ETA 0.84 s ahead.
2. The player keeps walking 54.20 u past their own reported point and **stops**
   at `(14169.88, 11130.39)` (L1780). The client sends **nothing** — no `0x0047`
   in this window at all. `async_branch` stays `integrated` throughout, so the
   park is a real velocity-zero stop, not `position_at` clamping at a segment
   end.
3. The sync copy walks on toward the armed destination.
4. At L1785 the copy arrives, `+0x9C` → `[inf, inf]`, `+0x48` → 0, **and the
   parked body teleports 54.20 u backward onto the destination in the same
   sample.**
5. The body stays there for the next 7.6 s, and the client's own next report
   (`261.829`) names the post-snap point with `drift 767.91` — the client itself
   confirms it went backward.

**No cast exists in this session. `--cast-stop` did not exist yet on
2026-08-21. The wire is silent. Nothing but the zero-lead grant and the client's
own arrival machinery is present.** The counterfactual is measured.

Two further clean-ish castless drags, same signature, both parked bodies:
`movetap-20260821T082702.jsonl` L1195 (26.08 u) and L1644 (28.76 u) — same
regime, same shape, smaller magnitude.

**Caveat, stated plainly:** run `20260821T123903` was an **automated harness
walk pattern** (`walk1-yaw` … `walk62-keyW` screenshots in
`vault/captures/harness/20260821T123903/`), driven as REALFIX-P2's
`--zero-lead` treatment arm, not the owner playing. It is keyboard-only,
click-free, cast-free walking under the shipped grant policy — which is exactly
the regime the counterfactual asks about — but it is a machine's walk, not a
human's. That does not weaken "it fires castless" (the cast is simply absent);
it does mean the *rate* in §4.3 should be read off the owner-era tapes, and it
is.

---

## 3. The mechanism, from the binary

### 3.1 What the arrival primitive does — VERIFIED, with one correction

**OBSERVED** (my own `codescan --dis 0x006020B0`). Along the straight-line path:

- takes a 4-word position at `[ebp+8]`, `[ebp+0xc]`, `[ebp+0x10]`, `[ebp+0x14]`
- asserts at `0x006020DE` if x **and** y equal `dword [0x948654]`
- calls `0x005FF880` (the point-update the tape's `updated` field tracks)
- zeroes velocity `+0xB0` / `+0xB4`
- writes the position into `+0x78` … `+0x84` (`0x00602132`…`0x0060214F`)
- **stores `dword [0x948654]` into `+0x88`/`+0x8C` (segmentPoint) and into
  `+0x9C`/`+0xA0` (targetPoint)** — `0x00602155`, `0x00602164`, `0x0060216D`,
  `0x00602179`
- zeroes `+0x90`, `+0x94`, `+0x98`, `+0xA4`, `+0xA8`
- zeroes `+0x3C`, `+0x40`
- **zeroes `+0x48` at `0x006021E6`**

**CORRECTION owed to the orchestrator's brief.** The brief says the primitive
"writes +0x9c (syncPoint)". It does not write a sync point — it writes the
**INVALID sentinel**. `movetap.py:513` names `VA_INVALID_POS = 0x00948654` and
`INVALID_POS = 0x7F800000` (+inf, AGENT_INVALID_POSITION), and `0x0060216D`
stores a value loaded from that exact address. **OBSERVED, and it closes the
loop between binary and tape**: `+0x9C` → `[inf, inf]` in the primitive is
literally the `target` field going to `[inf, inf]` in every fire row.

Everything else in the brief's list verifies as stated.

### 3.2 What clears `+0x48` — the mechanism sentence F35 needs

**OBSERVED** (`codescan --field 0x48 --in AgAgent`): 33 instructions,
**4 stores, 29 reads**:

```
005FE531  W  mov [ebx+0x48], esi        arm
005FEAD6  W  mov [esi+0x48], eax        arm
005FEB46  W  mov [esi+0x48], ecx        arm  (the grant bake)
006021E6  W  mov [ebx+0x48], 0          CLEAR -- inside 0x006020B0, and nowhere else
```

This reproduces the orchestrator's census exactly, from an independent run —
so the census is a **verified positive control**, not a repeated claim.

**Who can reach the clear — OBSERVED** (`codescan --xrefs 0x006020B0`): seven
direct `call` sites — `0x0060032E`, `0x00600A91`, `0x00601817`, `0x00601899`,
`0x0060221E`, `0x006025A6`, `0x00602B74`. Two of those are the ones that matter:

- `0x0060032E` sits inside the function whose nearest preceding padding is
  `0x00600140` — **the movement tick**. This is the ETA path: the tick reaches
  `+0x48` and fires the arrival. (`codescan` prints "best effort, not proof of a
  function boundary"; I am relying on that caveat and on `authsrv.py`'s
  independent identification of `0x00600140` as the movement tick.)
- `0x00602B74` is SetPosition's armed branch. **OBSERVED** at
  `0x00602B20`: `cmp dword [ebx+0x48], 0` at `0x00602B44`, `je 0x602B7B`
  (parked → plain store to `[ebx+0x78]`), else fall through to
  `call 0x6020B0` at `0x00602B74`. Exactly as the brief says.

**So, the mechanism sentence — and the answer to "what cancels a pending arrival
when the player stops walking?" is NOTHING:**

> Releasing the walk key writes nothing to `+0x48`. The only instruction in
> AgAgent that clears `+0x48` is `0x006021E6`, inside the arrival primitive
> itself, so the arm can only be cleared **by being consumed** — either the tick
> reaches its ETA (`0x0060032E`) or something calls SetPosition on the agent
> while it is armed (`0x00602B74`). The client's stop, c2s `0x0047`, is
> **send-only** — `authsrv.py`'s `--stop-echo` block states it has no receive
> handler in the agent table (**SOURCED**, `toolkit/authsrv/authsrv.py`
> ≈:1102), and the `+0x48` census independently makes the point moot: even if
> there were a handler, no store site exists for it to use. A destination we
> grant is therefore armed until it fires, and a stop cannot disarm it.

**And that is why `--resync` (REALFIX-P5) is the candidate with a live
prediction. OBSERVED:** the s2c `0x002C` handler `0x005FDA50` calls SetPosition
`0x00602B20` **twice** — at `0x005FDAE5` on the agent taken from the SYNC array
`[esi+0xE8]`, and at `0x005FDB49` on the agent taken from the ASYNC array
`[esi+0x14C]`, both indexed by the same agent id — with an `AgTrack` call
(`0x005FCEC0`) and `0x00605F70` ahead of them. Because SetPosition routes an
**armed** agent through `0x006020B0`, a `0x002C` **consumes and clears a pending
arrival on both copies**. A `0x0029` cannot: it reaches only the bake, which
arms. **This is the asymmetry the brief predicted, and it verifies.**

### 3.3 What the corpus says about the primitive — and it refutes the simple story

**OBSERVED.** Census of every arrival fire in the corpus (`target_invalid`
False→True with `+0x48` cleared), 31 captures:

| | fires | of which body parked | body dragged onto the point |
|---|---|---|---|
| whole corpus | **586** | 89 | **8** |
| owner-era tapes (2026-08-24/25) | 109 | 24 | 3 |

**579 of 586 fires land the sync copy exactly on the armed point (< 5 u) and the
tick was always reached — but the drawn body moves in only 8.** Non-dragging
parked fires occur at body-to-destination gaps of 9.8, 15.7, 22.3, 30.2, 76.5,
93.1, 164.4, 237.4, 301.3, 433.7 u; dragging ones at 26.1, 28.8, 30.5, 36.0,
54.2, 167.6, 177.4 u. **The distributions fully overlap: gap magnitude is not
the gate.** Neither is `sep`, nor gate 1's verdict (seven of the eight drags are
`gate1 = below`, and so are most of the non-drags), nor the async copy's own arm
(`async_stop` is 0 on both sides of the comparison), nor how long the body had
been parked.

**So "the arrival teleport drags the drawn body" is true but conditional, and
the condition is unmeasured.** §8.3f's reading of its single instance is
correct about that instance; it is not a rule.

**Leading hypothesis — UNVERIFIED, but binary-grounded and testable.**
`0x006020B0` does not stop at one agent. From `0x006021ED` it walks a
pointer array at `[ebx+0x28]` of length `[ebx+0x30]` and, for each element,
**calls itself at `0x0060221E` with the same position**, then calls `0x006011F0`
and `0x00601F70` and re-checks that element's own `+0x48`/`+0x9C`. That is a
propagation list — "everything attached to this agent lands where it lands". If
the async twin is enrolled in the sync agent's list only under some condition,
that is exactly a mechanism that drags the body sometimes and not others.
`codescan --field 0x28 --in AgAgent --writes` finds only **two** stores, both
`mov [edi+0x28], 0` (`0x005FE86B`, `0x005FF614`) — clears. **The populating
write is outside AgAgent's assert range, or behind one of `codescan`'s own
documented blind spots** (a biased `this`, or an address built in more than one
step). Finding it is the next binary step and it is cheap: `--xrefs` on
`0x006020B0`'s enclosing function, plus `--field 0x30 --in AgAgent`, plus a
re-run at disp±4 per the tool's own "when a subsystem's answer looks too small"
warning.

---

## 4. Exposure of F35 in ordinary play

### 4.1 Report-overrun and grant-staleness at stops — §7.8 extended ~8×

**OBSERVED.** Every c2s `0x0047` stop in every `origin: "ours"` gamesrv capture
that ran **`--zero-lead` with no click traffic** — 24 captures, **235 stops**
(§7.8 used 4 captures and 28 stops). Two metrics, because they are not the same
number:

- **report-overrun** = |stop-reported point − last **accepted** `0x003D` point|.
  This is §8.3f's "how far a leg outruns its last accepted report".
- **grant-staleness** = |stop-reported point − last **granted** `0x0029`
  destination|. This is what §7.8 tabulated, and it is F35's magnitude, because
  the armed destination *is* the last granted point.

They diverge whenever a report is accepted but its grant is refused
(`heading-rate` rate-limiting), which leaves the arm older than the report.

| population | n | p50 | p90 | max | > 190 u | > 299.33 u | > 512 u |
|---|---|---|---|---|---|---|---|
| overrun, all | 235 | 81.2 | 308.4 | 498.2 | 90 (38.3 %) | 47 (20.0 %) | **0** |
| staleness, all | 235 | 105.7 | 345.9 | 748.3 | 99 (42.1 %) | 50 (21.3 %) | 4 |
| overrun, owner-driven | 96 | 28.5 | 177.4 | 498.2 | 10 (10.4 %) | 9 (9.4 %) | 0 |
| **staleness, owner-driven** | **96** | **54.3** | **345.9** | **748.3** | **18 (18.8 %)** | 12 (12.5 %) | 4 |
| staleness, automated walk patterns | 139 | 226.9 | 308.7 | 481.5 | 81 (58.3 %) | 38 (27.3 %) | 0 |

("owner-driven" = the capture contains at least one `USE_SKILL`; the automated
harness walk arms never cast. The split matters: the harness walks deliberate
long straight legs, which is the treatment, so pooling the two overstates
ordinary play.)

**§7.8 reproduces exactly under the staleness definition — OBSERVED, and it is
the positive control for this pipeline.** Its four captures come back
`141556` max 227.6 / 3 of 7 over 190; `163550` p50 24.8, max 345.9, 1 of 13;
`182739` max 256.3, 1 of 4; `081335` p50 89.5, max 120.1, 0 of 4 — matching the
published table row for row (the p50s on the n = 4 captures differ by the median
convention on an even count, nothing more).

**§7.8's headline holds at 3.4× the sample and gets slightly worse: "about one
stop in six" is one stop in five.** 18 of 96 owner-driven stops leave the armed
destination more than 190 u behind.

### 4.2 A sharpening of §8.3f's chord bound

**OBSERVED.** §8.3f says the exposure "scales with report overrun ... which the
`0x003D` chord bounds". Measured:

- **report-overrun is bounded by the chord, exactly: 0 of 235 stops exceed
  512 u; the maximum is 498.2 u.** The bound is real and now has 235 trials
  behind it instead of one run's `sep` maximum.
- **grant-staleness is NOT so bounded: 4 of 235 exceed 512 u, max 748.3 u**
  (all four in `authsrv-20260824T100352-c1`). A refused grant lets staleness
  accumulate across more than one chord.

Since F35's magnitude is the staleness and not the overrun, **F35's worst case
is not capped at ~512 u.** That is a measurement-beats-prose correction, and it
matters for any fix that is sized against the chord.

### 4.3 How often the warp actually fires — and why 30 seconds is not enough

**OBSERVED.** Exposure and yield, from the tapes:

- **261** stop-and-stand episodes across the corpus (body motionless ≥ 1.0 s
  after moving in the preceding second). **99** of them have an armed
  destination live at some point during the stand. So the *condition* is common:
  the treatment arm is well exposed, this is not a zero-trial situation.
- But the arrival drags the body in only **8 of 586** fires corpus-wide, and
  **3 of 109** in the owner-era tapes.
- **Owner-era rate: 3 drags in 477 s of tape = one every ~2.6 minutes of
  play-like recording.** Corpus-wide (mostly machine walk patterns): one every
  ~8.2 minutes.

**A 30-second run has an expected yield below 0.2 events.** The handoff's
"30 seconds of owner time" was sized against a mechanism believed to fire on
every armed stop; the census says it does not. §5 sizes the run off this number.

---

## 5. REGISTERED PREDICTION — CANCELWALK-F35-C1, the no-cast counterfactual

**Self-contained. Everything needed to run and score it is in this section.**
Registered **before** the run, 2026-08-25, RECON session, against zero fresh
observations from it.

### 5.1 What is already decided, and what this run is for

The castless question is **already answered on tape** (§2.4): the teleport fires
with no cast in the session. **This run is a confirmation under today's
defaults, and a first measurement of the drag's gate.** If the owner would
rather spend the time elsewhere, §2.4 is sufficient to file F35 as fully
REALFIX's and drop the quiet-window nuance. Say so rather than running out of
habit.

### 5.2 The recipe — BOUNDED, and it ends by itself

```
python toolkit/harness/session.py --enemy --hold 300 --game-args "--map 280
  --explorable --practice-target --skills 105,153,322"
python toolkit/clientscan/movetap.py --seconds 300
```

- **`--keep-open` is deliberately ABSENT.** §0's recipe carries it; do not copy
  it here. `--hold 300` closes the session after **5 minutes** and
  `--seconds 300` stops the tap at the same wall. **The run ends on its own; no
  window is parked on the owner's screen.**
- **Total owner time at the keyboard: 5 minutes.** Not 30 seconds — §4.3 shows
  the expected yield at 30 s is under 0.2 events. Five minutes buys roughly two
  events at the owner-era rate, which is the smallest run that can be scored at
  all (§5.6).
- **`--cast-stop=pin` is ON by default since 2026-08-25 (§8.3g) and this run
  wants NO CAST AT ALL, so it never activates. Leave the default alone — do not
  pass `--no-cast-stop`, and do not pass `--cast-stop`.** Stated explicitly
  because the ambiguity is the point of the counterfactual: a flag that never
  fires cannot be the cause, and the cleanest way to show that is to leave it
  armed and untouched while never pressing a skill. `--zero-lead` is likewise
  the shipped default and must stay on — it is the thing under test.
- **Do not press a skill at any point in the 5 minutes. Do not click to move.**
  Keyboard walking only. A single `0x0046` or `0x003E` in the tape does not void
  the run, but it does void every episode within 3 s of it.

**The motion pattern, repeated for the whole 5 minutes:** hold one direction key
for a **long straight leg of at least 3 seconds** (≈ 860 u — long enough that the
leg outruns its own `0x003D` chord and leaves the grant behind), **release the
key**, then **stand completely still for 3 seconds** — hands off keyboard and
mouse, no camera turn. Then turn to a new heading and repeat. Aim for **~20
leg-then-stand episodes**. Vary the leg length across episodes (3 s, 4 s, 2 s)
so the staleness at the stop spans the 100–500 u band rather than clustering.

### 5.3 The predictions, in measurable terms

**P1 — the arm survives the stop.** In the `movetap` tape, at ≥ 15 of the ~20
stops, the SYNC block's `target` is a **finite point** (not `[inf, inf]`) at the
moment the body's velocity reaches zero, and `stop` (`+0x48`) is **non-zero and
greater than the sample's `now`** — an ETA still in the future. Neither field
changes value as a result of the key release.
*Confidence: high. §3.2 says nothing can clear it.*

**P2 — the armed point is bit-identical to a zero-lead grant.** For every such
stop, `target` equals the `dest` of the most recent `fired: true` `grant_verdict`
in the paired gamesrv capture, to **0.00 u**, and that grant predates the stop.
*Confidence: high; observed in both known instances.*

**P3 — the teleport fires castless, at least once.** At **≥ 1** of the ~20
episodes, in a single sample: `target` flips finite → `[inf, inf]`, `stop` flips
non-zero → 0, `sync_at` lands on the previously-armed point, **and `async_at`
jumps ≥ 25 u onto that same point (within 5 u)** — with **no `0x0046` anywhere
in the capture** and **no server frame** (`0x0028`/`0x0029`/`0x002C`) in the
gamesrv tape in the ±2 s around it.
*This is the registered claim. Expected count at the owner-era rate: ~2.*

**P4 — magnitude equals the grant-staleness, not the report-overrun.** For each
P3 event, the body's jump distance equals |stop position − armed destination| to
**< 1.0 u**, and that quantity equals the paired gamesrv `position_report`'s
`drift` on the client's **next** `0x003D` to < 1.0 u. Predicted magnitude band
from §4.1: **25–350 u**, p50 near **55 u**; a value above 512 u is possible only
if a grant was refused between the last accepted report and the stop (§4.2), and
if one occurs the tape must show that refusal.

**P5 — the drag is conditional, and the gate is visible.** Across the run there
will be **more arrival fires while the body is parked than there are drags** —
predicted ratio **between 1:5 and 1:20** (§3.3 measured 8 of 89). If every
parked fire drags, §3.3's census is wrong about this regime and that is a
finding in itself.

### 5.4 What REFUTES "it fires castless"

Stated before the run, and any one of these is a refutation, not a
re-interpretation:

- **R1.** Zero P3 events across ≥ 15 scoreable episodes (§5.6), **while** P1 and
  P2 hold — i.e. the arm demonstrably survives every stop and the copy
  demonstrably arrives, and the body never moves. That would say the drag needs
  something the cast supplies, and §2.4's instance would have to be re-examined
  for an unnoticed trigger.
- **R2.** A P3-shaped event that turns out to have a server frame inside its
  ±2 s window. Then it is our wire, not the client's arm, and it is a different
  bug.
- **R3.** The body's jump lands somewhere other than the armed point (> 5 u
  off). Then it is not the `+0x48` arrival — the F27/F33 reconcile family lands
  on the sync copy's *current* position, not on the destination, and 76 of the
  92 jumps in §2.3 are that family.
- **R4.** `target` is `[inf, inf]` at every stop (P1 fails). Then something does
  disarm on stop in this build and §3.2's census is scoped wrong — re-run
  `--field 0x48` at disp±4 and outside AgAgent before believing anything else.

**What does NOT refute it:** a run with few or no stands long enough to score
(that is zero trials, not a null — see §5.6), or a run where the events are
small (< 25 u). Magnitude is set by how far the legs outran their reports, which
is the operator's motion, not the mechanism.

### 5.5 What must be in the tape for it to be scoreable

- `movetap` running for the whole session (§0's "run both instruments").
- Both files aligned on the **wall clock** (`movetap.t` vs the gamesrv origin's
  `wall_unix`). **Never** by trajectory fit.
- The gamesrv capture must record `grant_verdict` rows (it does by default), so
  P2 can be checked against `dest` rather than reconstructed.

### 5.6 Exposure floor — what makes an episode count, and how many are needed

**An episode counts only if all four hold**, checked in the `movetap` tape:

1. the body moved ≥ **500 u** on one continuous heading immediately before the
   stop (so the leg outran its own report chord);
2. the body's velocity is **0.0** for ≥ **2.0 s** after the stop, with total
   movement < 1 u across that window;
3. `target` is finite at the moment velocity reaches zero (an arm exists to
   fire) — an episode where the arm had already been consumed is **not a
   trial**;
4. no `0x0046` and no `0x003E` anywhere within ±3 s.

**Floor: 15 scoreable episodes.** Below that the run is **VOID for R1** — report
it as zero trials, not as a null result, exactly as §7.4a did for R6. A run that
yields 15+ scoreable episodes and 0 P3 events is a real refutation; a run that
yields 6 episodes and 0 events is a run that did not happen.

At ~20 attempts and the observed hit rate this run is expected to return
**1-3 P3 events**. If the owner wants a run that can *also* estimate the gate
(P5) rather than just witness the phenomenon, it needs **10 minutes**, not five —
say so when reporting, rather than over-reading two events.

---

## 6. What I could not determine, and corrections owed

**6.1 What gates the drag. NOT DETERMINED.** §3.3: 586 arrival fires, 89 with
the body parked, 8 drags. I tested and eliminated gap magnitude, `sep`, gate 1's
verdict, the async copy's own `+0x48`/`reqtoken`/velocity, `async_branch`, and
parked duration — none separates the drags from the non-drags. The
`+0x28`/`+0x30` propagation list inside `0x006020B0` (§3.3) is the leading
hypothesis and is **UNVERIFIED**; its populating writer is not visible to
`codescan --field 0x28 --in AgAgent`, which finds only two clears. **This is now
F35's open question, and it is more consequential than the castless one was**:
a fix that assumes every stale arm warps will be sized wrong by an order of
magnitude, and `--resync`'s predicted effect on F35 depends on it. `--resync`
would still zero F35 either way — it consumes the arm before it can fire (§3.2)
— but the *frequency* it removes is 8-per-586, not 89-per-586.

**6.2 `0x0029` reaches only the bake.** **SOURCED**, from the orchestrator's
brief and consistent with the `+0x48` census (three arms, one clear, the clear
unreachable except through `0x006020B0`). I did **not** disassemble the `0x0029`
handler in this session. The seven callers of SetPosition are `0x005FDAE5`,
`0x005FDB49` (both in the `0x002C` handler), `0x005FF74B`, `0x00602369`,
`0x006028FF`, `0x00604A50`, `0x00606394`; if any of the last five turns out to
sit in the `0x0029` path, the arm/disarm asymmetry changes and this note's
§3.2 conclusion needs re-checking. Cheap to close; not closed here.

**6.3 The function boundary at `0x00600140`.** `codescan` reports nearest
preceding padding only and says so. That `0x0060032E` is inside the movement
tick rests on that plus `authsrv.py`'s independent identification. **SOURCED,
not OBSERVED.**

**6.4 Corrections this note owes to existing docs:**

| where | what it says | what the measurement says |
|---|---|---|
| §8.3f | F35's "no-cast counterfactual UNVERIFIED" | **VERIFIED castless**, `movetap-20260821T124010` L1785, three instances corpus-wide (§2.4) |
| §8.3f | "the exposure scales with report-overrun ... which the `0x003D` chord bounds" | true of **overrun** (0 of 235 over 512 u) but **false of staleness**, which is F35's actual magnitude: 4 of 235 over 512 u, max 748.3 u (§4.2) |
| §8.3f | reads the single instance as the mechanism | the mechanism is **conditional**: 8 drags in 586 fires; the gate is unmeasured (§3.3) |
| §8.3f wording | "the drawn body snapped ... onto the sync copy" | the drawn body is `async_at`; `movetap`'s `live`/`point`/`sync_at` is the *other* copy (§1) |
| orchestrator brief | "`0x006020B0` … writes +0x9c (syncPoint)" | it writes the **INVALID sentinel** from `0x00948654` into `+0x9C` — an invalidate, not a sync-point write (§3.1) |
| §0 handoff | F35's first step is "30 seconds of owner run time" | expected yield at 30 s is **< 0.2 events**; the floor is 15 scoreable episodes, ≈ 5 minutes (§4.3, §5.6) |
| §7.8 | 5 of 28 stops past ~190 u, "about one stop in six" | reproduces exactly on its own four captures; extended to 96 owner-driven stops it is **18 of 96, about one stop in five** (§4.1) |
