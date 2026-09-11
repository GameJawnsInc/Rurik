# PROBE-GATEFIRE — does the client ever *evaluate* the snap test?

**Status of this document:** procedure, not result. **No gate-fire run has happened** —
`vault/captures/movetap/` holds exactly five files, all stamped 2026-08-19, and not one of
them carries `gate_reach`, `state_record` or `hist_head`. Every address is build **38797**.

Written 2026-08-20 against tree `C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de`;
**the instrument merged to `C:/gd/Rurik` (main) as `442f3ff` / `e3dfb98` on 2026-08-20, and
every command below now names main.** ⚠ **CORRECTED, and this was the most dangerous line in
the file:** twenty-three commands used to begin
`cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de`. That worktree is **still on
disk**, still checked out at `8ebc424`, and **36 commits behind**. A `cd` into it does not
fail — it runs the pre-C1 instrument, whose `movetap.py` greps `gate_reach` **15** times,
writes `shut:apply` **8** times, and contains **no** `gate1`, **no** `early_out_a` and **no**
`print_episodes` at all. Copying the old commands produced a clean-looking capture with the
wrong fields and no error: the exact "confident wrong number from old code" failure step 1
exists to catch, aimed at this document.

**Every quoted output block in §6 is now pasted verbatim from a real printer run**, and each
one carries its provenance label. §6 says which blocks are OBSERVED and which are
FIXTURE-DRIVEN, because none of them can be a measurement until the run happens.

**Route: POLLING, WITH CAVEATS THAT TRAVEL WITH THE OUTPUT.** The cheap route survives
review, but four of its printed numbers did not. The aliasing guard was structurally
blind in exactly the band this probe's leading hypothesis lives in; two headline shares
folded failed reads into real ones; one hypothesis was refuted by construction; and half
the instrument the sample outputs described did not exist when they were written
(**all nine changes have since landed and are merged** — `442f3ff`, merged `e3dfb98`,
2026-08-20, after four adversarial rounds; §12 is that review's accepted residue).
§3 step 2 is now a landing **checklist** rather than a blocking change list, and §5 is a
verbatim statement of what this instrument cannot see that sits **before** the analysis,
not after it.

---

## SAFETY

> **THE OWNER DRIVES THIS RUN.** Every block needs world-anchored ground clicks and a
> judgement about where open ground is. That is on the far side of the agent-pilotable
> line (roster/HUD readouts are pilotable; world-anchored clicks and appearance verdicts
> are not). An agent may run the tap, the audits and the analyser. **An agent may not
> play.**
>
> **THE DH BINDING.** A client may only be launched at the server whose Diffie-Hellman
> exponent matches the parameters it carries. This run is `ours` → loopback, which
> requires a verified cage. `ours` → live is refused *by the bytes*, not by a filename —
> Stage A completes with whatever credential the client autofilled before the patch
> matters.
>
> **THE BUILD.** `C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe` — build 38797,
> dh `ours`, CAGED, `updater=killed`. Verified today.
>
> **Neither launch gate checks the build number.** `dhbuild.classify` answers
> `ours`/`stock`; `cage_state` answers CAGED. `vault\run\2026-08-13_64fae3b1369b\Gw.exe`
> is `ours` **and** CAGED and would launch cleanly — it is build 38833, on which every
> address in this decode reads whatever else is mapped. Step 5 is what catches it.
>
> `session.py` has no `--host`. The destination comes only from `--auth-host` /
> `--portal-host`, both `127.0.0.1` by default; the host handed to the cage is derived
> from the actual argv, and `FORBIDDEN_CLIENT_ARGS` blocks `--client-arg` from smuggling
> one past. **Do not pass `--host`. Do not open the cage. Do not touch `C:\gw`.**

---

## 1. THE PREDICTION — stated before any step

### The question

`0x006055E0` decides whether to hard-copy the server-authoritative SYNC agent onto the
locally-predicted ASYNC agent the player sees. Return 1 = NO SNAP, 0 = SNAP.

It has **five** exits, not three. The three gates were decoded first and are the reason
this probe exists; the two early-outs above them were found while revising this document
and are listed here because either one presents on a capture as *"above the cut and
nothing snapped"* — which is the exact shape H1 claims as its own confirmation.

| | site | fires when | effect |
|---|---|---|---|
| **EARLY-OUT A** | `0x00605634`–`0x00605641` | `agent+0x48 != 0` **and** `agent+0xC4 == 9` | return 1 — **NO SNAP**, before gate 1 and before the history walk |
| **EARLY-OUT B** | `0x00605643`–`0x0060567F` | `agent+0x78` **and** `agent+0x7C` both equal the float at `0x00948654` (`0x7F800000` = +inf = `AGENT_INVALID_POSITION`) | return 1 — **NO SNAP** |
| GATE 1 | `0x006057E1` | `300.0 < dist` — effective cut **299.3326 u** (the LUT sqrt at `0x0046E870` is biased high) | SNAP |
| GATE 2 | `0x0060580A` | `MapFindPath` pathCount == 0 — our SYNC point does not resolve on the navmesh | SNAP |
| GATE 3 | `0x0060581E` | `0x005FEF70` returns 0 | SNAP |

Every one of those addresses was re-disassembled out of the pinned 38797 image on
2026-08-20 and every byte still reads as stated — see §11.

`agent+0xC4` is the movement mode fed to `0x00602660`'s 1..8 switch, so **9 is outside the
normal range** and early-out A's prior is low: every `0x002B` our server has ever sent
carries mode 1 (**n = 759**, whole vault, all 759 with the trailing mode byte `01`), and
`0x002B`'s handler `0x005FD9D0` is what writes `+0xC4` from the wire via `0x00602990` at
`0x00602A29`. `agent+0x48` is non-zero in **25.9 / 36.1 / 44.2 / 84.7 / 95.4 %** of samples
across the five corpus captures (n = 4,115 — re-derived today, all five shares exact), so
A's *first* conjunct is satisfied most of the time. `+0xC4` lies inside `AGENT_SPAN` (0xD0),
which movetap already reads in one block — recording it costs **zero extra reads**. Both
early-outs are therefore checkable for free, and step 2's C7/C8 made them so.

**But the whole test is fenced.** The caller `0x00605FC0` reaches it only when
`clientControlled` (AgTrack record+0x00) is non-zero (`0x00606002`) *and* the agent's world
!= 1 (`0x00606013`). `clientControlled` is one-shot: `AgTrack::Clear` (`0x00605F70`) zeroes
it, and only local player input re-arms it (`0x00605F10`). **CORROBORATED** against the
pinned image this round: the arm writes `rec[+0x00]=1` and `rec[+0x04]=0` only when
`rec[+0x00]==0` (`0x00605F3F` / `0x00605F43`); Clear zeroes both only when non-zero; the
arm's two call sites (`0x005FC784`, `0x005FC8B9` — `--xrefs` returns **exactly 2**) sit in
functions reached **only** from the input chain `0x00535380` → `0x008163A0` (octant
resolver, modes 1..8) → `0x0081A8F0` / `0x0081ADB0` / `0x0081B650`.

Prior measurement — n = 24 snaps over 623 paired intervals, 5 movetap × gamesrv pairs —
found **0 of 24 snaps began below gate 1's threshold** (min before-separation 342.8 u),
yet **303 of 327 above-threshold intervals (92.7%) did not snap**, non-monotonically.

**So: which exit actually fires — and is the test even reached?**

### Two things about the fence that change how any result reads

**(a) On world 0 the first half cannot veto, so the fence is the whole question.**
`0x006055E0` asserts `[agent+0x24] == 0` at `0x0060561A` — it only ever runs on world 0.
The first half's 100 u history walk starts at `[esi+0x04]` (`0x006056AF`), i.e. at the
AgTrack record's `hist_head`. The arm zeroes `hist_head` (`0x00605F4F`); the caller's own
tail appends **only** on the world1 and shut branches, returning at `0x00606023` without
appending on an open-fence NO SNAP, and calling `Clear` first on a SNAP. Therefore
**`hist_head` is identically 0 for the whole duration of every open stretch on world 0**,
the 100 u history veto **cannot fire**, and whenever the fence is open the fallback always
runs and the exits above fully decide. This is why the old H3 was retired (below).

> **⚠ CORRECTED 2026-08-25 — the bolded conclusion is REFUTED for the A1 regime**
> (`movetap-20260825T202345`, scored in REALFIX.md §0.5): the chain was **alive in
> 617/641 samples, up to 8 nodes**, appending at grants, stops and seam-crossings
> **with the fence open**. So the 100 u veto RUNS with live data on world 0, and it —
> not the fallback exits — decided every high-separation no-snap press in that tape
> (sep 351–509 u held because the copy stood at dist 0.0 ON a same-plane chain
> segment). The static reasoning above was sound for the appenders it knew (the
> caller's tail genuinely appends only on the world1/shut branches — re-verified);
> what it missed is **another appender running during open stretches** — identified
> the same night (REALFIX.md §0.6): the append at `0x0060610B` runs unconditionally
> on every ARMED world-1 dispatch, and the per-id record is **shared across worlds**,
> so async dispatches feed the very `hist_head` the world-0 test walks; a periodic
> staleness sweep (`0x00604B2A`, > 3333 ticks, fence-independent) appends too. The
> fallback half of `0x006055E0` appends on **no** branch — and it was never
> undecoded (FINDINGS' round-2 section had it since 2026-08-20).
> Duty-cycle conclusions built on "the veto cannot fire" need re-reading against
> this — starting with H3's withdrawal below, which was grounded ON (a)
> ("unobservable by construction") and is now overturned in both ground and
> content: the A1 tape shows the match veto observable, operating, and DECIDING
> the "above the cut, no snap" population. H3 was right.

**(b) The loopback fence is not the retail fence.** `AgTrack::Clear` has three call sites
(`--xrefs 0x00605F70` returns **exactly 3**, re-checked today). Two are ours to reason
about (`0x005FCA94`, `0x0060602E`). The third, `0x005FDA78`, sits in a function with **zero
direct callers** and one `.rdata` word at `0x00A52E20` — it is the dispatch of
`MsgFormatRecv` descriptor `0x00A52E18`, `cmds[0] = 0x2C`, i.e. the **GAME_SMSG `0x002C`
handler** (`0x005FDA50`), which calls `AgTrack::Clear(msg.agentId)` **unconditionally as
its first act**. Our server has sent `0x002C` **zero times across every gamesrv capture in
the vault — 984 files scanned today**, with a positive control on the same scanner
(opcode 41 / `0x0029` found in 76 files, opcode 43 / `0x002B` in 78), so the null is a
measurement and not a broken grep. Retail's dominant *clearing* edge is inert on loopback.
Any duty cycle this run measures is a loopback duty cycle, and that is a second
incomparability on top of the town-vs-explorable one in §4. If the fence turns out to be
stuck **open**, this is the first explanation to reach for.

### The two rivals — H3 was retired, and why

| | hypothesis | what it predicts on this run |
|---|---|---|
| **H1** | **FENCE-CLOSED** *(leading)* | In the STRAIGHT blocks `gate_reach` reads `shut:*` for ≥ 80% of **real** samples, the aliasing ratio **A < 0.5**, and the number of fence **episodes** per 40 s block is **≤ 2** — while measured separation grows past 1,000 u and nothing snaps. The 92.7% is then explained with no exit acting at all. |
| **H2** | **THE EXITS DECIDE** | `gate_reach` reads `test-runs` in ≥ 80% of real samples in *both* arms, and once separation is measured from **memory** rather than proxied, the "above the cut but no snap" population is explained by gate 1 emptying it — or, where it survives, by early-out A (`+0x48 != 0 && +0xC4 == 9`) or early-out B (`m_point` == +inf) being satisfied at those samples. The 92.7% was an instrument artefact of the wire proxy. |

**H3 (MATCH-VETO) is withdrawn.** Its operational signature was "`test-runs` **and**
`hist_head` non-NULL", and by (a) above that is **unobservable by construction** on world
0: `hist_head` is identically 0 through every open stretch, so the old refutation rule 4
("H3 dies if `hist_head` is 0") would have fired on every run regardless of the truth —
a check that cannot fail, wearing the costume of a refutation. Its content did not
disappear, it collapsed: H2 now carries the "above the cut, no snap survives" population,
and the two early-outs are the concrete mechanisms that would produce it.

> **⚠ REVERSED 2026-08-25 — H3 was right.** The withdrawal above stood on §(a),
> which the A1 tape refuted (see the correction there): the chain is live during
> open stretches, the match veto runs, and it is what held every high-separation
> no-snap press in `movetap-20260825T202345` — the early-outs were inert in that
> run. REALFIX.md §0.5 is the decoded mechanism.

### The collision audit, done before the run because that is the point

- **H1 and H2 both predict "above the cut, no snap."** They are separated *only* by
  `gate_reach`, which is read every sample. ✅
- **Inside H2, "gate 1 emptied it" and "an early-out vetoed it" are separated** by the
  directly measured separation *plus* `+0x48` / `+0xC4` / `m_point`. All four are reads
  inside blocks movetap already fetches. That is why the ASYNC read and the `+0xC4`
  extraction were **required code changes and not niceties** — both landed as C6/C7. ✅
- **They are not mutually exclusive.** Each can hold over different stretches. **The
  analysis reports the joint table and elects no winner.** An output that prints one
  verdict is a design defect.
- **Residual collision, partially closed:** "the dispatch was never called" and "the
  dispatch was called but fenced" both look like nothing happening. Polling cannot fully
  separate them — but the appender witness (C5) turns part of it into a **positive**
  observation for free, because `hist_head` and the `+0x08..+0x14` cache changing between
  two samples witnesses that the caller ran and took an append branch. **Note where that
  witness actually lives:** it is `movesync.print_appender_witness`, reached only through
  `movesync.print_fence` — `movetap` has no such printer and prints no witness at all
  (§6 used to show one under `movetap`; see the ⚠ CORRECTED note there). What stays
  unobservable is the `shut:noop` branch, which writes nothing at all. See §5 and §8.

### What would refute each — every one a positive observation, not an absence

1. **H1 dies** if `gate_reach` reads `test-runs` in ≥ 50% of real STRAIGHT-block samples.
   No comparison arm needed; H1 refutes on its own data.
2. **H1 dies a second way** if STRAIGHT and WIGGLE show the *same* fence duty cycle **and**
   the same episode rate — then the local-command edge is not what gates the test and the
   mechanism story is wrong. (Shares alone will not do it; see §5 item 4.)
3. **H1 dies a third way** if the STRAIGHT blocks report **A ≥ 0.5** after flaky-read
   contamination has been excluded. The shares are then an artefact of when we looked, and
   this is escalation trigger §2(a).
   **⚠ A HOLE IN THIS RULE, found 2026-08-20 while syncing this document to the code, and
   stated rather than papered over:** if a STRAIGHT block contains **zero** transitions —
   the single-state outcome H1 most plausibly produces — then `A` is not computed at all.
   `fence_verdict` prints *"The fence never changed state, so there is no aliasing ratio to
   compute"* (§6, block 3), and rule 3 **cannot fire on that block**. It is therefore not a
   refutation route on precisely the data H1 predicts. Rules 1 and 2 are unaffected and are
   what must carry a zero-transition run. Logged as §12 item 12.
4. **H2 dies** if a substantial population survives with `test-runs`, memory-measured
   `gate1 == "above"`, no snap, **and** neither early-out satisfied (`+0x48 == 0` or
   `+0xC4 != 9`, and `m_point` not the +inf sentinel).
5. **The instrument dies, and the run is void** if `test-runs` is never once observed
   across blocks A and A′. That is indistinguishable from reading the wrong address, so
   it is a **refusal**, not a result. See step 11.

### PREDICTION, in one sentence

> In the STRAIGHT blocks `gate_reach` reads `shut:append` for ≥ 80% of real samples with
> **≤ 2 fence episodes per 40 s block and an aliasing ratio A < 0.5**, while measured
> separation exceeds 1,000 u and nothing snaps; in the WIGGLE blocks `test-runs` is
> observed at least twice on the same character, same map, same session.

**UNVERIFIED:** the 80%, the ≤ 2 episodes and the A < 0.5 are the *shape* H1 requires, not
measured quantities — **n = 0 runtime observations of `clientControlled` exist**. This run
is the first measurement of that field, ever.

**Note the criterion changed, and why.** It used to read "median contiguous shut-run
≥ 5 s". At a 30–40 s block length with H1 true, every run is censored by the block
boundary at both ends, so that criterion is satisfied **by construction** — unfalsifiable.
Episode count and A are falsifiable at this block length; a median is not, and the tap's
own output refuses to quote one when the majority of runs are censored — see §6 block 5,
which prints `median REFUSED (2 of 2 runs censored by the capture boundary)` in place of a
number.

### One outcome that is not a failure, and would be misread as one

The aliasing refusal is **live, not exotic**, and the WIGGLE blocks may well trip it.

**The reason previously given for expecting that was wrong and is corrected here.** This
document used to argue from `+0x48` — "a different field, but driven by the same
local-command edge". It is not. `+0x48` is written only by `0x005FE950`, whose five call
sites (`0x005FEC7E`, `0x006002B5`, `0x00600B0A`, `0x00601936`, `0x00602AD3`) sit in the
movement-tick and SMSG-grant functions; the arm path is
`0x0081AA88 → 0x005FC6E0 → {AgTrack arm 0x00605F10, 0x00602660}`, and `0x00602660`
switches on movement mode 1..8 writing `agent+0xB8/+0xBC/+0xC0` and **never `+0x48`**.
Measured over 3 clock-aligned movetap × gamesrv pairs, `+0x48`'s change rate against our
own server's s2c `0x0029` grant rate: **5.23 vs 5.61 /s, 2.91 vs 3.16 /s, 0.24 vs 0.22 /s
— ratios 0.93, 0.92, 1.09.** `+0x48` is a readout of our send rate, not of the fence.

**What survives, and it is enough to expect aliasing:** a *client-side event field*
demonstrably changes on **41%** of consecutive samples at 12.94 Hz in this corpus (25% in
the other fast capture), i.e. the sampler is already at or past Nyquist for the client's
event layer. Client c2s command rate in the same windows was **1.96–8.62 msgs/s**
(`0x003D` + `0x003E` + `0x0047` + `0x0040`).

So: expect the WIGGLE blocks to alias. **That is WIGGLE doing its job.** Its only role is
to prove the reader *can* see `test-runs`, which two observed samples achieve. The finding
is carried by the STRAIGHT blocks, where H1 predicts almost no transitions at all. An
aliasing refusal in STRAIGHT is a different matter — that one sends the work to the hook
(§9), and §6 block 7 is exactly what it looks like when it fires.

---

## 2. WHY POLLING, AND WHAT WOULD SEND IT TO THE HOOK

The cheaper route was **not** rejected. Three reasons it is the right one here:

- **The fence is a plain dword in a flat array, and the reader already holds its base.**
  The whole chain is `AGBASE + 0x1CC` → `[+0x20]` array, `[+0x28]` count, stride `0x1C`,
  field `+0x00`. Two extra `ReadProcessMemory` calls. No compiler, no injection, no
  vectored handler in a rendering client's hot path.
- **The primary job is the fence, and the fence is pollable — with a stated resolvable
  band.** Gate 1 subsumes all 24 known snaps; gate 2 has n = 0 firings. The marginal thing
  a hook buys is *which of gates 2/3 fired in the cases gate 1 did not* — and there are no
  such cases in the corpus. The band this instrument can and cannot resolve is §5 item 3,
  and it is printed with every result — the tap now derives the poll rate from the
  sequence's own timestamps and prints both Nyquist thresholds by name.
- **The hook has a bad record here and does not exist.** The hardware-breakpoint route
  delivered nothing across five silent runs and cost two commits of retracted
  conclusions. Only the int3 + VEH pattern in `trnhook/trnblock.c` has ever worked, and
  that is the **terrain** hook — **no `.c` under `toolkit/clientscan/trnhook/` names
  `0x00606002`, `0x006055E0`, `0x0060580A` or `0x0060581E`** (all seven sources grepped
  today; all seven use `AddVectoredExceptionHandler`), and **no `trnhook*.dll` is built in
  `C:/gd/Rurik`**. Escalating means writing a new `.c` and building it: its own evening.
  Also, each hit stalls a client whose desync is a race between two clocks — the instrument
  would perturb the phenomenon.

**Escalate to the hook on either of these, and nothing else:**

- **(a)** a STRAIGHT block reports the aliasing refusal — **A ≥ 0.5** — *after* the
  flaky-read exclusion in change C3 has been applied, or
- **(b)** any snap is classified `gate1 == "below"` with the fence open **and neither
  early-out satisfied**. That is the only positive evidence gate 2 or gate 3 ever fires,
  and gate 2 is the single gate with a server-side fix (it means *our* server put the SYNC
  point somewhere unresolvable on the navmesh).

Do **not** escalate on a large `undecided` share — that means the sample rate was too low,
and the remedy is caching the resolve, not a compiler. Do **not** escalate on an
unread-contaminated flip count: change C3 exists precisely because a 10–20% flaky read
used to manufacture ~0.20 flips/sample, 80% of the old bar, in a band the 25% unread
refusal never reached. The direction of that error was an evening spent writing a hook DLL
for a bad read.

---

## 3. PRE-FLIGHT

Begin **every** command with the `cd`. Your default shell may sit in another tree, and a
relative `python toolkit/...` there runs *that* tree's copy — which does not error, it
returns a confident number from old code. **This is not hypothetical for this document in
particular:** every command below used to name a worktree that is still on disk and 36
commits behind, and answers a `cd` without complaint.

### Step 1 — prove the tree, and prove the instrument is in it

```powershell
cd C:/gd/Rurik && git rev-parse --show-toplevel && git rev-parse --abbrev-ref HEAD && grep -c gate_reach toolkit/clientscan/movetap.py && grep -c "shut:apply" toolkit/clientscan/movetap.py
```

Healthy — measured on main, 2026-08-20:

```
C:/gd/Rurik
main
31
0
```

**The last two numbers are the ones that matter, and they are a pair.** A tree carrying the
pre-C1 instrument reads `15` and `8`; the merged one reads `31` and `0`. `movesync.py` reads
`24` on the same grep.

⚠ **CORRECTED.** This step used to run `git rev-list --count HEAD..main` and expect `0`, and
its note claimed *"`C:\gd\Rurik` (main) has **zero** occurrences of `gate_reach` — the
instrument exists only as uncommitted working-tree changes"*. Both halves are now false and
one of them was never a check: main carries 31 occurrences on a clean tree, and
`rev-list --count HEAD..main` **from main is 0 by construction** — it was also 0 in *both*
directions while the instrument was uncommitted, so it never distinguished anything. This
repo's own rule is that a check which cannot fail is not a check. The `gate_reach` /
`shut:apply` pair above can go red, and does, in the stale worktree.

### Step 2 — THE CODE CHANGES: A LANDING CHECKLIST, NOT A GATE

⚠ **CORRECTED — this step used to be a blocking gate and is not one any more.** It said
*"As of writing, `movetap.py` contains **no `sep`, no `gate1`, no ASYNC-array read at
`AGBASE+0x14C`**, and still writes `shut:apply` / `world1:apply`. Every sample output in
steps 13 and 14 below describes code that does not exist yet. **The run does not launch
until the greps in this step answer.**"* **All nine changes are merged at `e3dfb98`.** `sep`
is written at `movetap.py:1132`, `gate1` / `gate1_why` / `async_ptr` / `async_count` in `gate1_read`
(`movetap.py:1046`), the `AGBASE+0x14C` ASYNC read is live, and `shut:apply` occurs **zero**
times in the file.

Run the greps at the end of this step anyway. They are no longer a gate on the code; they
are what tells you **the shell is in the merged tree** and not in the 36-commits-back
`gatefire-probe-plan-9c31de` worktree, which is still on disk and still answers a `cd`.

Nine changes. C1–C5 are the fence lane and are the ones the review turned red; C6–C8 are
the gate-1 and early-out lanes; C9 is bookkeeping that goes into every stored row. The
"why" column is kept as the rationale record — it is why each change exists, and deleting
it would delete the reasoning that survived four adversarial rounds.

| | change | landed as | why |
|---|---|---|---|
| **C1** ✅ **LANDED**, mutation-proven (restoring `flips*4 >= n` turns the skewed-fence selftest case RED) | **Replace the aliasing guard.** Over consecutive-sample pairs where **both** values are real (non-`unread:`): `phi = flips/pairs`; `p` = open share over real samples; **`A = phi / 2p(1-p)`**. **REFUSE when `A >= 0.5`.** | `movetap.fence_verdict(reach, flips, pairs, n, rate, seq=())` at **`movetap.py:4703`** (not `:1044`, which the old row cited). ⚠ **The spec in this row was written against a print format the code does not use:** it said *"Print `A` with `phi`, `p` and `pairs` beside it"* and §6 quoted a `white` cell. **There is no `white` cell and no `ALIASING:` line** — no printable string in either file carries a `white` field (`grep -i white` returns exactly one hit and it is a comment, `movetap.py:3393`; the real guarantee is `test_probedoc.py` §4's AST walk over the format strings, not a grep). The ratio arrives inline in one transition sentence; see §6. Also unstated in the old row and load-bearing: `p_open` is over `n - unread`, **not** over `n`. | `flips*4 >= n` is blind for duty cycles outside **[14.6%, 85.4%]** — under full aliasing consecutive samples are near-independent Bernoulli(p) and E[flips]/n → 2p(1-p), whose **maximum is 0.5**, so a lopsided fence **cannot** trip a 0.25 bar at any flip rate. Simulated at 10.4 Hz over 45 s with exponential dwells (n = 470/cell): open 15 ms / shut 185 ms = **10.04 true transitions/s**, utterly unresolvable, yields `flips/n = 0.137` and the old guard prints **"not aliased"** over a 7.5% / 92.5% split. That is **byte-for-byte the H1-CONFIRMED block** this document used to show as its own evidence. `A` is scale-free: simulated **0.07** for a genuinely slow fence (5 s / 5 s), **0.88–0.93** for balanced fast (100 ms, 30 ms), **0.94–1.04** for every lopsided fast case the old bar waved through (15/185, 30/370, 185/15, 300/30 ms). |
| **C2** ✅ **LANDED** | **Print run lengths, not just transition counts.** Per observed state: contiguous runs, **median in samples AND seconds**, minimum run, and **how many runs are CENSORED by the block boundary**. **Refuse to quote a median when the majority of runs are censored.** Print the Nyquist bar. **Report the effective n as the number of EPISODES, never the number of samples.** | `movetap.print_episodes(seq, rate=None)` at **`movetap.py:4599`**. Beyond what this row specified: it derives the seconds axis from the **sequence's own timestamps** rather than from `rate`, and prints a **measured poll-rate line** naming the gap between poll rate and sample rate as the share of polls that produced no row; it prints `effective n = N episode(s) ... QUOTE THE EPISODES.`; the Nyquist line names **two** thresholds, `2.0/hz` DETECT and `5.0/hz` CHARACTERISE; and a run split by an unread sample is flagged, with the run count called an **UPPER** bound. | The prediction is stated in run lengths and the tool computed none. A 92.4% share over 564 samples with 3 transitions has an effective n of about **4**, not 564. |
| **C3** ✅ **LANDED** | **Fix the flip denominator.** Count a flip only when `last['gate_reach']` **and** `s['gate_reach']` are both non-`unread:`, and carry the count of usable consecutive pairs as the denominator. **Exclude `world1` ↔ `shut` transitions.** | `pairs` now arrives from `count_flips` and is **not** `n-1`; a poll that produced no row appends its own marker to `seq`, so `len(seq) >= n` and `pairs` is read against `len(seq)-1`. The old row's cited site `movetap.py:968` is now unrelated code. | As written, `real → unread → real` counted as two transitions. A 10% flake rate manufactures **0.20 flips/sample — 80% of the escalation bar** — below the 25% unread refusal, whose printed consequence is *"THIS is the outcome that earns the hook"*. A world-index change is also not a fence flip. |
| **C4** ✅ **LANDED** | **Fix the sentinel hole in the jump table.** A **three-way tally — reachable / fenced / unread-or-missing** — all three printed, the third never folded into either, and **REFUSE the sentence when the third is ≥ 25% of the jump rows.** | `movefence.print_jump_tally(rows, indent='   ')` at **`movefence.py:240`**; `UNREAD_REFUSE_SHARE = 0.25` at `movefence.py:104`. The old `tested = sum(...)` at `movesync.py:602-606` no longer exists. It prints a **4-line table plus a 2-line sentence**, not the one-liner §6 used to quote. | `tested = sum(... if be == "test-runs")` against `len(rows)` folded `be is None` **and** `be == "unread:<why>"` into *"The rest reached 0x00605840 … the HISTORY APPENDER"* — a could-not-read counted as a real fence-shut, in the headline. The population refusal uses a **different denominator** over hundreds of samples and cannot protect nine jump rows. **This is the exact number §6 used to quote as its H1 evidence.** |
| **C5** ✅ **LANDED** | **Add the appender witness.** Per block: **(a)** how often `hist_head` **or** the `+0x08..+0x14` cache CHANGED between consecutive samples; **(b)** how often `hist_head` went to **0** while `gate_reach` was **unchanged**. Print both limits. | `movefence.print_appender_witness(samples, indent='   ', population='movetap sample(s)')` at **`movefence.py:456`**, called only from `print_fence` at `movefence.py:558`. ⚠ **It is in `movefence`, re-exported by `movesync`, and in neither case `movetap`** — the fence section was cut out of `movesync.py` on 2026-09-11 and the printer went with it, so `movesync.print_appender_witness` still resolves and is still what `main()` reaches; `grep -c appender_witness toolkit/clientscan/movetap.py` = **0**. §6's step-13 block used to show this section under the tap's own output; it was never there. | Costs nothing: `movetap` already stores `hist_head` and the full 28-byte `state_record` every sample. Limits printed: the appender dedups at 2500 ms (`0x0060593A cmp eax,0x9c4`) — and the shipped LIMIT 1 goes further than this row asked, naming the four `0x0060594B` / `0x0060595E` / `0x0060596B` / `0x0060597B` jumps that make the suppression **conditional** on the cached fields also holding still; the `shut:noop` branch writes nothing and stays unobservable. |
| **C6** ✅ **LANDED** | **Read the ASYNC agent and compute `sep` and `gate1` from memory** — array at `AGBASE+0x14C`, count at `AGBASE+0x154` (from `0x0060577A` / `0x0060575E`, where `esi` = AgTrack `this` = `AGBASE+0x1CC`). Classify `above` / `below` / `undecided`, refusing the 295–305 u band. | `GATE1_ABOVE, GATE1_BELOW, GATE1_UNDECIDED` at `movetap.py:536`; `movetap.gate1_verdict(g1, g1why, early_a, point_bad, n)` at `movetap.py:4814`. Beyond the row: a **`plane-mismatch`** refusal it never anticipated, printed in the `undecided` row's own why-breakdown, and a whole-block **ASYNC-twin refusal** at the 25% bar. | The only thing that separates "gate 1 emptied the population" from "an early-out vetoed it". §1's collision audit calls it required. |
| **C7** ✅ **LANDED** | **Record `agent+0xC4`** and derive `early_out_a = (agent+0x48 != 0 and agent+0xC4 == 9)`. | `early_outs()` at `movetap.py:894`. | `+0xC4` is already inside `AGENT_SPAN` (0xD0) — **zero extra reads**. Fourth exit, above gate 1, absent from the mechanism table until this document. Low prior, free to check, and if it ever fires it presents as H1. |
| **C8** ✅ **LANDED** | **Derive `point_invalid`** = both `agent+0x78` and `agent+0x7C` == `INVALID_POS` (`0x7F800000`). | `point_invalid` at `movetap.py:914`; `INVALID_POS` at **`movetap.py:524`** (the old row cited `:217`). | Fifth exit (`0x00605643`–`0x0060567F`). `A_POINT = 0x78` is already read. |
| **C9** ✅ **LANDED** | **Rename `shut:apply` → `shut:append`, `world1:apply` → `world1:append`,** and purge every printed sentence that asserts an execution nobody observed. | `grep -c "shut:apply" toolkit/clientscan/movetap.py` = **0**. `movesync` reads **both** spellings (`REACH_ALIASES`, `movefence.py:96`) and prints only the new one, with a NOTE line counting the legacy rows — `_selftest_spellings` at `movefence.py:1375` binds it. | §10(1): a shut fence does **not** mean the server's position was applied. `shut:apply` reads as the opposite and would have driven server work at a problem that is not there — and that string is written into every stored row permanently. |

**The tests landed in the same commit.** `test_movesync.py`'s fence-verdict section includes
the fabricated lopsided-aliased case that **must go red** under the old bar; the section runs
**14 checks against a floor of 7**. A guard that cannot go red on the case it was written for
is not a guard.

⚠ **CORRECTED — the commit block that used to sit here has been removed.** It read
`cd <stale worktree> && git add -A && git commit -m "gatefire: …"`. The work is committed and
merged; running `git add -A && git commit` from main today would commit whatever else happens
to be in the tree.

The landing greps — every one of these must be non-zero except the last:

```powershell
cd C:/gd/Rurik && grep -c "gate_reach" toolkit/clientscan/movetap.py; grep -c "0x14c\|0x14C" toolkit/clientscan/movetap.py; grep -c "gate1" toolkit/clientscan/movetap.py; grep -c "early_out_a" toolkit/clientscan/movetap.py; grep -c "shut:append" toolkit/clientscan/movetap.py; grep -c "shut:apply" toolkit/clientscan/movetap.py
```

Expected, measured 2026-08-20: `31`, `4`, `87`, `17`, `51`, **`0`**.
The stale worktree answers `15`, `1`, `0`, `0`, `0`, `8` — every one of the six differs, which
is the point of running all six rather than the first.

### Step 3 — the affected tests. Not the full suite.

The full suite is **139 files** — `toolkit/run_suite.py` walks `toolkit/` from the disk and
that walk finds 139 today — and the owner runs it constantly. The last measured wall clock is
**621 s over 96 files at four jobs, 2026-08-14**; 43 files have landed since, so treat that
figure as a floor of unknown tightness and **UNVERIFIED** as a runtime for today's tree.
These seven are the ones this run depends on.

```powershell
cd C:/gd/Rurik && python toolkit/clientscan/test_movesync.py
cd C:/gd/Rurik && python toolkit/clientscan/test_pinned.py
cd C:/gd/Rurik && python toolkit/clientscan/test_buildid.py
cd C:/gd/Rurik && python toolkit/clientpatch/test_cage.py
cd C:/gd/Rurik && python toolkit/clientpatch/test_dhbuild.py
cd C:/gd/Rurik && python toolkit/harness/test_harness.py
cd C:/gd/Rurik && python toolkit/test_origin.py
```

Each ends `ALL CHECKS PASSED (N checks)` and exits 0. All seven were re-run green on the
merged tree on 2026-08-20; the counts below are from that run.

| test | checks | a red one means |
|---|---|---|
| `test_movesync.py` | **150** (floor 100) | The analyser that turns the run into a number is broken — both bar arms, the fence sentinels, the shuffle control. **The run can be taken and still not be interpretable.** ⚠ **CORRECTED: this row used to read "110 (floor 61)" and to say "the step-2 changes add checks … so expect a *higher* number".** The changes are in the count now. 150 is with every vault capture present; **100 is the bare-machine subset** and is the declared floor (7 sections skip without the vault), read off a real green run on 2026-08-20 — `test_movesync.py:125` records that in the floor's own comment. |
| `test_pinned.py` | 143 | The build gate `movetap` sits behind. `assert_build` may accept the wrong image, and every hardcoded RVA is then reading whatever else is mapped. |
| `test_buildid.py` | 42 | The build-number readout. **Step 5 would lie**, which is worse than not running it. |
| `test_cage.py` | 18 | **The launch gate itself. Do not launch anything.** This is the only thing between an `ours`-DH binary and the real service, and a broken gate is indistinguishable from a working one until it matters. (~1 min; it queries the Windows Firewall once per client.) |
| `test_dhbuild.py` | 48 | The whose-DH answer is untrustworthy, including its hostile-filename-order refusals. Every cage verdict is downstream of this. |
| `test_harness.py` | 156 | The driver: launch safety, capture tails, and `verdict_after_hold` — a client that dies during the hold must retract the PASS. That wiring shipped broken once and printed `RUN VERDICT: PASS` over a corpse. |
| `test_origin.py` | 32 | **Run this one first if anything else is red.** It answers "did the vault drift". A capture from another build landing in `captures/gamesrv/` turns three tests red with no code changed. If it names two build ids, the other reds are downstream of the vault, not of you. |

Then the two selftests, which need no client:

```powershell
cd C:/gd/Rurik && python toolkit/clientscan/movetap.py --selftest
cd C:/gd/Rurik && python toolkit/clientscan/movesync.py --selftest
```

`movetap` ends `selftest passed -- 250 checks, floor 250`; `movesync` ends
`selftest passed -- 80 checks, floor 80`. Both exit 0. **Those two totals are EXACT floors**
(`SELFTEST_FLOOR` at `movetap.py:1481` and `movesync.py:1097`), so any net loss of a check
reddens them — and for `movetap` that is the **only** per-section guard there is (§12 item 9).

> **NOT `gatetap.py` / `gatescore.py` / `studies/movement/gatefire.tsv`.** Those were
> specified during planning and never written. They do not exist. The instrument is
> `movetap.py` + `movesync.py`.

### Step 4 — the safety audits

```powershell
cd C:/gd/Rurik && python toolkit/clientpatch/dhbuild.py
cd C:/gd/Rurik && python toolkit/clientpatch/cage.py
```

Healthy — re-verified 2026-08-20:

```
Every build is where it belongs.
```
```
  [ok] run/2026-07-29_221c13772c7a
       dh:    ours (want ours) -- OUR parameters, keys/rurik_dh_2026-07-29_221c13772c7a.json
       cage:  CAGED (want CAGED)
       patch: {'updater_killed': True, 'mutex_guard_nopped': True, 'mutex_renamed': True, 'key_tapped': True}
...
7 client(s), 0 in the wrong state.
```

Anything else — including `cage_state` answering `None` twice in a row — **stop**. `None`
means the firewall query did not answer, and that is not permission.

`key_tapped: True` is expected residue (`dryrun_keycapture.py` did not restore the
untapped default last run). Harmless here: `pinned.assert_build` accepts the image.

### Step 5 — the build, read out of the image itself

```powershell
cd C:/gd/Rurik && python toolkit/clientscan/buildid.py --exe "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe"
```

Healthy — the whole output, re-verified 2026-08-20 (this block used to be introduced as
"exactly" and showed only the last line):

```
client: C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe
        (given on the command line)

build 38797, from the getter at 0x004729E0 (16 callers)
```

Anything else — **especially `38833`** — stop. `[AGBASE+0x1CC]` on another build does not
error; it reads whatever else is mapped and returns a plausible `clientControlled`.

### Step 6 — is anyone else using the vault right now?

```powershell
cd C:/gd/Rurik && Get-ChildItem C:\gd\Rurik\vault\captures\gamesrv\*.jsonl | Sort-Object LastWriteTime | Select-Object -Last 3 Name,LastWriteTime; (Get-Process Gw -ErrorAction SilentlyContinue).Count
```

**This is not a hypothetical, and it got worse while this document was being written.**
Twenty gamesrv captures carried today's stamp by 12:53 — newest
`authsrv-20260820T125214-c1.jsonl` — from sessions this arc did not run, in a shared vault
that now holds **984** `*.jsonl`. `movesync`'s `newest()` is
`sorted(glob.glob(pattern), key=os.path.getmtime)[-1]` (`movesync.py:621`) over that shared
vault, and `session.py` has no `--capture-root` flag. If the newest timestamps are not yours,
**pass every path explicitly in step 14** and never use the bare form.

Note the client count. If it is not 0, the multi-instance mutex is NOPed on every build
here, so two clients can be up — which is why step 10 pins the pid.

---

## 4. THE RUN

### Step 7 — Terminal 1: start the stack

```powershell
cd C:/gd/Rurik && python toolkit/harness/session.py --keep-open --warn 5 --game-args "--map 146 --explorable"
```

**Do not pass `--exe`.** The default is build-pinned and *self-reporting*:
`select_run_exe()` filters by the build number read out of each image and picks the
directory named after that build's vault stamp — never by mtime. Passing `--exe`
suppresses the `client:` line entirely (it prints inside `if not a.exe:`), which is the
only place the build appears at launch. (`session.py --help` still says "default: newest
under vault/run". **That text is stale and is contradicted by the code three lines away** —
re-checked 2026-08-20, still stale. Do not act on it.)

**Do not pass `--enemy`.** It is off by default since 2026-08-12: the standing hostile
spawns 300 u from arrival against `AGGRO_RANGE` 1200 and killed the character 10 s into a
*movement* session. This is movement work.

**Never pass `--any-build`** to `movetap` at any point in this run.

#### Why map 146, and what it costs

The prior n = 24 corpus is **map 148, Ascalon City (Pre-Searing) — a town**
(`explorable = false`). `map_id: 148` holds in the twelve most recent gamesrv captures
(re-checked today against a different twelve files). A 40 s straight leg needs 11,520 u at
the 288.0 u/s that is `maxspeed` in **100%** of those samples, and the corpus has no such
room: the largest **single-axis** extent is **4,684 u** and the largest **point-to-point
separation inside any one capture** is **5,238 u** (n = 5, 4,115 samples; per-capture
pairwise maxima 5238.1 / 2939.1 / 3065.1 / 2338.3 / 3874.4 u), consistent with city walls.
**Not performable on 148.**

⚠ **CORRECTED.** That sentence used to read *"the whole corpus spans at most 4,684 u corner
to corner"*. 4,684 u is the maximum extent along **one axis** (the dy of
`movetap-20260819T145939`), not a corner-to-corner span; an exhaustive pairwise walk over
that capture's 39 unique `+0x78` points gives **5,238.1 u**, and pooled across all five
captures **6,788 u**. Both are lower bounds — `+0x78` is stale between updates. **The
argument is untouched**: 5,238 u is still far under the 11,520 u a 40 s leg needs.

Map 146 (Lakeside County) loads the **same terrain file** — `file_id 0x1B97D`, row 7982,
crc `0xA0AE500A` — with `explorable = true`. So `contentids.preflight` is unaffected: it
returned **12 of 12 map rows agree across both archives**, with 146 and 148 both on row
7982. Row 7982 covers the whole Pre-Searing region: navmesh extent **39,936 × 49,152 u**,
58 planes, 6,120 trapezoids. **UNVERIFIED as of this rewrite:** the 12/12 verdict is carried
from the original run and was not re-executed — it needs both `Gw.dat` archives, and a
running client holds one open exclusively. `content/maps.toml` still carries 146 and 148 on
`file_id 0x1B97D` at row 7982, so the premise holds; note the same file also records row
177262 in build 38833's archive, and **row 7982 is the pre-update generation — the one build
38797 uses**, which this document had never said.

**The cost, stated plainly, and it is now TWO costs.** (i) The fence shares from this run
are **not** directly comparable with the n = 24 corpus, because that was a town instance
and this is an explorable one, and the fence is per-agent and per-map. (ii) Separately and
independently: retail's dominant clearing edge, the GAME_SMSG `0x002C` handler's
unconditional `AgTrack::Clear`, is **inert on loopback** — our server has sent `0x002C`
zero times across all 984 gamesrv captures (§1(b)). The loopback fence is not the retail
fence. Say both in the write-up.

Healthy output, in order:

```
  webgate up: 127.0.0.1:6601  pid NNNN
  authsrv up: 127.0.0.1:6112  pid NNNN
  gamesrv up: 127.0.0.3:6112  pid NNNN
account: <synthetic>
client: build 38797, 2026-07-29_221c13772c7a (chosen by BUILD and name, never by mtime; skipped 2026-08-13_64fae3b1369b)
cage: ours build, cleared for 127.0.0.1
client pid NNNN: Gw.exe -authsrv 127.0.0.1 -portal 127.0.0.1 -windowed -log ...
  [PASS] t+  N.Ns  client keyed the auth channel
  [PASS] t+  N.Ns  client sent PORTAL_ACCOUNT_LOGIN
  [PASS] t+  N.Ns  login accepted
  [PASS] t+  N.Ns  client asked for a game instance
  [PASS] t+  N.Ns  client opened its game channel
  [PASS] t+  N.Ns  game channel keyed
  [PASS] t+  N.Ns  client requested its spawn
  [PASS] t+  N.Ns  body is in the map
RUN VERDICT: PASS  (target: map)
```

The `client:` line above is quoted character for character from `select_run_exe()`'s own
output, re-run 2026-08-20.

Two listeners on 6112 at different hosts is the healthy shape — the game channel is a
second `authsrv.py` instance and the client declares its channel in its version header.

The harness's only input is one click on **Play**. Everything after `body is in the map` is
you, at the keyboard.

### Step 8 — read the two things you will need all session

Write down:

- **the client pid**, from the `client pid NNNN:` line
- **the gamesrv capture filename**, which appears in `C:\gd\Rurik\vault\captures\gamesrv\`
  as `authsrv-<stamp>-c1.jsonl` the moment the game channel keys

`session.py --keep-open` **blocks** until you close the client. Everything below happens in
a second terminal.

### Step 9 — walk to the open ground

Before any tapping. The spawn (9826, 8077) is Ascalon City's coordinate reused for map 146
— `content/maps.toml` says so and says why. Straight-line room from the spawn is poor in
most directions: over 72 headings the median unobstructed ray is **1,375 u (4.8 s)**, and
only **2 of 72** afford ≥ 20 s.

**One direction is good, and it is enough.** Heading ~230° — *both x and y decreasing* — is
continuously walkable for **12,850 u = 44.6 s** at 288 u/s (checked at 50 u granularity,
0 unwalkable steps over 12,800 u). **That is what pays for the 40 s STRAIGHT blocks** and
it is the only added time in this run.

So: **run away from the city, in the direction where the tap's `+0x48` target readout shows
both coordinates falling.** Six thousand units out, at roughly (5969, 3481), the best local
ray opens to 17,850 u (62 s) — more room than this script needs.

**UNVERIFIED:** this is the *terrain* navmesh from the archive. It does not encode the
map-146 instance's own boundary, and our navmesh agrees with the client's at 189/198 exact
plane matches (n = 532). If the client fences you in sooner, block A will show it and the
STRAIGHT blocks shorten — short blocks are data, not failures, but say so, because a
shortened block costs episodes and episodes are the n that carries the finding.

### Step 10 — the tap: one command per block

**One `movetap` per block.** That is how this run records block boundaries — each file
carries its own fence distribution, its own episode statistics and its own aliasing ratio,
and no join between two clocks has to be written. Ctrl-C is the documented normal stop and
is handled; the floor is scored against the time actually run.

Pass `--pid` every time — `movetap` otherwise takes `gw_pids()[-1]`, and "last one wins"
has picked the wrong thing three times in three files.

```powershell
cd C:/gd/Rurik && python toolkit/clientscan/movetap.py --pid NNNN --seconds 45
```

⚠ **CORRECTED, and the old command could not run at all.** It read
`movetap.py --pid NNNN --block A --note "map 146 explorable, gatefire" --seconds 45`.
**`movetap` has no `--block` and no `--note`, and no way to name its output.** The real
parser (`movetap.py:4301-4308`) is `[-h] [--pid PID] [--hz HZ] [--seconds SECONDS]
[--selftest] [--any-build]`; both flags raise `unrecognized arguments` and the block never
starts. The file is stamped `movetap-<YYYYmmddTHHMMSS>.jsonl` and its head row carries only
`pid`, `exe`, `hz` and `wall`. **Write the block letter down against the stamp by hand as
each tap ends** — nothing in the capture records which block it was, and step 13 tells you
to read the STRAIGHT files first.

Healthy start — in this order:

1. a **7-line** `PREDICTION, stated before the run and not after it:` block (about `+0x48`),
2. an **11-line** `SECOND PREDICTION, for the fence on the snap test at 0x006055E0:` block,
3. one `  ctx 0x…  AGBASE 0x…  array 0x…` line from `resolve(verbose=True)`,
4. then these two:

```
reader capability 10.4 Hz (measured, 40 reads) -- BELOW the requested 50 Hz, so the floor is set from 10.4
polling agent 7 at 50 Hz for 45s -> C:\gd\Rurik\vault\captures\movetap\movetap-20260820T...jsonl
```

⚠ **CORRECTED:** this block used to open with a line `build 38797 (pinned)`.
`pinned.assert_build` prints **nothing** on success — the build gate is silent, and the two
prediction blocks are what actually appear first.

**UNVERIFIED: ~10 Hz.** The pre-change reader measured 9.47–12.94 Hz over the five existing
captures (n = 4,115). The step-2 changes add ~4 cross-process reads on ~14, so ~10 Hz is
arithmetic, n = 0. It cannot make the run fail spuriously — `calibrate()` runs the *new*
sample path 40 times before the run and sets the floor from what it measured, and C2's
episode block now prints the **measured** poll rate rather than assuming one.

Then, live, the loop prints **exactly two kinds of line** and nothing else:

```
  +0x48 12043 -> 12691 (due in 0.65s)  target (5969, 3481) glide=1
  fence shut:append -> test-runs (raw 0 -> 1, armed 7) at t+14.10s
```

⚠ **CORRECTED, and this one changes what the operator can watch for.** The old block showed
a per-sample line `[  12.4s] pos (    8140,    6134)  sep    1417.3 u  above     shut:append`.
**No such line exists.** `sep`, `gate1`, `early_out_a` and `point_invalid` are computed and
written into every row, but **none of them is printed during the run** — the only live prints
are the `+0x48` change line and the fence-transition line above (`movetap.py:4434` and
`:4445`). A transition that involved a failed read is additionally suffixed
`   [NOT a counted flip: a read failed]`. **You cannot watch separation climb in real time.**
What you can watch is the fence line: its presence, its absence, and its rate.

### Step 11 — the in-game script, block by block

| # | block | `--seconds` | what you do | live signal that it is working |
|---|---|---|---|---|
| 1 | **A — instrument positive control** | 45 | Click distant open ground. Let the glide finish. Click again. Repeat. | The tap must print `-> test-runs` **at least twice**. **If it never prints `test-runs`, ABORT the session** — the record address is wrong and every `shut` after this is meaningless. |
| 2 | **B — null control** | 30 | Stand completely still. No keys, no clicks. | Almost nothing prints: no `+0x48` changes, no fence transitions. This is the residual on a known-null stretch, and the only place the separation reading's noise floor can be measured — **but that measurement is made afterwards, from the file, not on screen.** |
| 3 | **C1–C3 — STRAIGHT ×3** | **40 each** | (a) Click ground **far away**; (b) *immediately* hold **one** movement key in the opposite direction; (c) **do not change heading, do not click, do not release** for the whole block. Turn only if terrain forces it. | **Silence on the fence line is the signal.** With H1 true the tap prints no `fence …` line at all for the whole 40 s, while `+0x48` lines keep arriving. That silence plus a large `sep` in the closing block is H1 — but `sep` only appears at the end, so do not expect to see it climb. |
| 4 | **D1–D3 — WIGGLE ×3** | 60 each | Move continuously and change heading about once a second — hold W, tap A/D alternately. Never stop, never click. | `fence …` lines appear repeatedly and `test-runs` shows up in them. Expect the aliasing refusal in the closing block; see §1 and §6 block 7. |
| 5 | **FREE — accumulate snaps** | 300 | Play normally under our grants: click ground, walk, click again, cover distance. This is the block `movesync` scores. | `+0x48` lines with large jumps in `target`. Snaps are scored afterwards by `movesync`; nothing on screen names one. |
| 6 | **A′ — positive control repeat** | 45 | As block A. | Same as A. Catches an instrument that drifted mid-session. |

Total tapping ≈ **12 min**; with the walk-out and setup, ≈ 25 min at the keyboard. The
only change from the previous script is STRAIGHT 30 s → 40 s: **+30 s of run time in
total**, bought because the STRAIGHT blocks are where the finding lives and each one
contributes exactly **one episode** to the n that matters.

**What 40 s does and does not buy — say this in the write-up.** With H1 true, each
STRAIGHT block contains ~zero transitions, so the effective n is **3 episodes**, one per
block, **each censored at both ends**. Forty seconds does not un-censor them; it gives a
larger lower bound per episode and a real chance of one uncensored run if the fence is
slow-but-not-static. It is why the H1 criterion is now episode count and `A`, not a
median: **a run censored at both ends of a block is a lower bound, not a median**, and the
printer refuses to quote one as such — §6 block 5 shows the refusal, and §6 block 3 shows
what a *fully* censored single-episode block looks like.

**Counterbalance if you run a second session:** `A B [D C]×3 FREE A′`. Operator fatigue and
client-state drift must not align with an arm.

#### The standing keyboard rule, and where this run breaks it deliberately

`HANDOFF.md` §5: *keep the keyboard moving, because the client emits `0x003D` only while
moving and a stationary wait blinds every wire-side instrument.* Blocks C, D and FREE obey
it in full.

**Block B is stationary on purpose**, because this run's primary lane is memory, which is
not blind. The consequence is explicit and must be carried into the write-up:
**no wire-derived rate, coverage figure or `movesync` verdict may be quoted over block B.**

#### The one thing the operator must actually do, or the run answers nothing

`clientControlled` is re-armed *only* by local player input, through an edge detector that
fires on the movement command **changing** — CORROBORATED this round from the arm's two
call sites and their input-chain-only callers. A run where you sit still, or let the
harness do everything, can produce a perfect capture in which the test is never evaluated —
which is indistinguishable from "no gate fired", and is the exact null this probe exists to
tell apart. **Drive the character, with the keyboard, throughout every block that is not B.**

### Step 12 — stop the tap before you close the client

`movesync` drops any pair outside ±0.25 s (`MAX_PAIR_GAP = 0.25`) and hard-FAILs below 20
pairs, so **the tapping window must sit strictly inside the gamesrv capture's span.** Start
each tap *after* the `body is in the map` verdict; Ctrl-C the last tap *before* closing the
client.

---

## 5. WHAT THIS INSTRUMENT CANNOT SEE — read this before §6, not after it

*The box below is the measurement review's own text, carried verbatim. It sits here, ahead
of every number this run produces, because an instrument's blind spot belongs next to its
output.*

> WHAT THIS INSTRUMENT CANNOT SEE, and it must be read before any share in this document is quoted.
>
> 1. THIS IS A SAMPLER OF STATE, NOT A COUNTER OF EVENTS. `gate_reach` is a COUNTERFACTUAL: movetap reads clientControlled (AgTrack record+0x00) and the agent's world index and names the branch the caller 0x00605FC0 WOULD take if it ran. Nothing here observes 0x00605FC0 executing. "test-runs" does not mean the test ran; "shut:append" does not mean the appender ran. Any sentence in this write-up of the form "the caller reached 0x00605840" is an inference, and it must be written as one.
>
> 2. THE FENCE'S REAL DWELL IS UNMEASURED AND WAS UNMEASURABLE BEFORE THIS RUN. n = 0 prior runtime observations of record+0x00. The existing five-capture corpus contains no field co-located with the arm (0x00605F10) or the Clear (0x00605F70), and the field previously nominated as a proxy, +0x48, was checked and REFUTED: across three clock-aligned movetap x gamesrv pairs its change rate tracks our own server's 0x0029 grant rate at ratios 0.93, 0.92 and 1.09 (5.23 vs 5.61 /s; 2.91 vs 3.16 /s; 0.24 vs 0.22 /s). It is a readout of our send rate, not of the fence.
>
> 3. THE RESOLVABLE BAND, STATED IN NUMBERS. The reader measured itself at 9.47-12.94 Hz over the existing corpus (n = 4,115 samples). A two-state signal needs at least two samples per half-cycle, so this instrument can DETECT alternation only where every dwell exceeds about 0.2 s and can CHARACTERISE it only where every dwell exceeds about 0.5 s. The client's own movement tick is 15-33 ms. If the fence opens on a command edge and shuts at the next tick, this instrument sees a nearly-always-shut fence and cannot say so.
>
> 4. THE OLD ALIASING GUARD WAS BLIND EXACTLY HERE, WHICH IS WHY IT WAS REPLACED. `flips*4 >= n` compares against a statistic that saturates: under full aliasing consecutive samples are near-independent and the expected flip fraction is 2p(1-p), maximum 0.5. It can therefore only fire for open shares between 14.6% and 85.4%. Simulated at 10.4 Hz over 45 s: a fence open 15 ms and shut 185 ms -- 10 true transitions per second, wholly unresolvable -- produced 7.5% open, 0.137 flips per sample, and the verdict "not aliased". That is byte-for-byte the shape this probe's leading hypothesis predicts as its own confirmation. The aliasing ratio A = phi / 2p(1-p) is reported in its place; A near 1 means the shares are an artifact of when we happened to look, at any duty cycle.
>
> 5. QUOTE EPISODES, NOT SAMPLES. A 92% share over 564 samples with 3 transitions has an effective n of about 4. Every share in this document is reported beside its episode count, its median run length, and how many of its runs were censored by the block boundary. A run censored at both ends of a 30 s block is a lower bound, not a median.
>
> 6. THIS RUN IS NOT COMPARABLE WITH THE n = 24 CORPUS, TWICE OVER. That corpus is map 148, a town instance; this is map 146, explorable, and the fence is per-agent and per-map. Separately: in retail the dominant clearing edge is GAME_SMSG 0x002C, whose handler (0x005FDA50, dispatched from the descriptor at 0x00A52E18) calls AgTrack::Clear as its first act -- and our server has sent 0x002C zero times in the entire vault. *[STALE since 2026-08-20, before this annotation was first written: the `--resync` run `authsrv-20260820T182119-c1.jsonl` sent 18, and `--cast-stop=pin` (shipped 2026-08-25) has since added 6 with co-timed movetap — corpus total 24 (`followon-notes/refute-lens-empirical.md` §1.1/§8.2, README §2.1). Still true of this probe's own capture, which predates both.]* The loopback fence is not the retail fence.
>
> 7. WHAT STAYS INVISIBLE EVEN WITH THE APPENDER WITNESS. hist_head and the +0x08..+0x14 cache changing is a positive observation that the caller ran an append branch, but the appender dedups at 2500 ms, so silence shorter than that proves nothing; and the shut:noop branch (fence shut, world != 0) writes nothing at all and is unobservable by any polling method. "The dispatch was never called" and "it was called and took shut:noop" remain the same reading. Only an int3 at 0x00606002 separates those two.
>
> 8. n = 1 SESSION IS n = 1, and the fence is per-agent: movetap polls only the ChCli-controlled agent. If the interesting snaps happen on a hero or a follower, nothing in this run looks there.

**Three notes added 2026-08-20, outside the box because the box is the review's own text
and is not edited:**

- Item 3's band is now **printed by the instrument rather than assumed by the reader**. C2
  derives the poll rate from the sequence's own timestamps and names both thresholds:
  at 10.40 Hz it prints DETECT above **0.19 s** and CHARACTERISE above **0.48 s** — which is
  item 3's "about 0.2 s" and "about 0.5 s", now measured per block instead of carried in
  prose.
- Item 7's LIMIT is **weaker than the box states, and the shipped code says so**: the 2500 ms
  dedup is only the first test of a chain (`0x0060594B`, `0x0060595E`, `0x0060596B`,
  `0x0060597B` all jump to the same append target on *inequality*), so an append is
  suppressed only when the head is younger than 2500 ms **and** the cached fields also held
  still. A moving agent can append twice inside the window. Read LIMIT 1 in §6 block 11.
- Item 4's ratio has one blind spot of its own, and it is on H1's own ground: **when a block
  contains zero transitions there is no `A` at all**, so refutation rule 3 cannot be scored
  on it. §1 rule 3 and §12 item 12 carry it.

---

## 6. THE ANALYSIS

**PROVENANCE OF EVERY BLOCK IN THIS SECTION — read this first.** Each block below is
**pasted verbatim from a real printer run**, byte for byte, including the lines that run past
200 characters. Nothing here is retyped, re-wrapped or tidied. Two provenance tiers, marked
per block:

- **OBSERVED** — real stdout over real vault captures. There are two, and both show the
  instrument **refusing** on pre-C9 data, because that is what the vault contains.
- **FIXTURE-DRIVEN** — the real printers (`movetap.fence_verdict`, `movetap.gate1_verdict`,
  `movetap.print_episodes`, `movesync.print_fence`) over hand-laid synthetic input. **Real
  code, invented data.** The *shape* is a measurement of the code; **every number in them is
  an illustration and not an observation of the client**, and §12's closing rule applies to
  them exactly as it applied to the numbers they replaced.

**There WAS no third tier when this was written, and there is one now — CORRECTED
2026-08-29, and read the correction rather than the claim.** This paragraph said
`vault/captures/movetap/` holds five files, all 2026-08-19, that none carries `gate_reach`,
`state_record` or `hist_head`, and that *"no post-C9 movetap capture exists anywhere,
n = 0"*. **MEASURED over all 60 files and all 78,805 rows: 53 carry all three**, the
earliest `movetap-20260821T081927.jsonl`, and 33 carry R5/R7's own fields as well. The run
happened, 53 times. So *"no real closing block from the tap can exist"* is no longer a
reason for anything, and blocks 1–10 are FIXTURE-DRIVEN today by inheritance rather than by
necessity. **That is a debt, not a defect**: a fixture-driven block is still regenerated and
still compared byte-for-byte by `test_probedoc.py`, so nothing here is unchecked — what is
missing is that the shapes are hand-laid input rather than a real walk, and §12's closing
rule still applies to them exactly as it always did. Re-deriving them from a real capture
needs **both** witnesses moved together, the tier word here and `probedoc_fixtures.DOC_BLOCKS`,
or §5 reddens.

**How to tell if these blocks have gone stale:** they were produced at HEAD `2361a83`, and
**re-derived unchanged at `e2468e5` on 2026-09-10**. The pins are as of the 2026-09-11
split that created `movefence.py` — it did not exist at `e2468e5`, and `movesync.py`'s
digest moved with the cut and not with anything it prints. Measured at the split:
`movetap.py` sha256 `44d87c2f4df8c95fcfe826e7e052950cb1098ab04ee440c6495ce053b1115953`,
`movesync.py` sha256 `76b6b534e0c674e0f0cb533768a91c0b4953aca51834664056f370cda3f97ead` and
`movefence.py` sha256 `08a1594a7c43246e72f52f66d15cb94ebbc2416284aa58d074dbf8883b5be9d1`. If
any hash has moved, re-derive every block before quoting one — a printed sentence that
changed upstream makes this whole section a description of code that no longer exists, which
is the failure this rewrite was commissioned to repair.

> **The 2026-09-10 re-stamp, and what a moved hash did and did not mean.**
> `movetap.py`'s hash moved from `6bef2bb…` to `44d87c2…` at `3e7ed3a2`
> (2026-09-05, MOVECODE-1z-cb). **The blocks below were not stale**: the whole
> diff is a thirteen-line COMMENT recording that the fourth word of an agent
> point is a hardcoded zero and there is no z column to add — `A_POINT = 0x78`
> is unchanged and no printer was touched — and `test_probedoc.py` re-derived
> every block from the real printers and matched all of them byte for byte.
> The instruction above is still the right one and was followed rather than
> waived: **re-derive, then re-stamp**. A whole-file hash reddens on a comment,
> which is the correct direction for a staleness signal a reader consults
> without running the suite — it costs one re-derivation and it cannot miss a
> real drift.

⚠ **REPINNED 2026-08-21 for REALFIX-T1 and REALFIX-I1, and the blocks below were re-read
rather than re-hashed.** Both files changed: `movetap.py` gained the history-chain walk
(`history_chain`, gated at `sep > 250 u`) and its `_selftest_chain` section, and `movesync.py`
gained `offset_detail` / `offset_line` and the `wall_unix` preference. **What the blocks below
quote is unaffected** — no printer in either file changed, and the run-summary line the chain
walk adds (`REALFIX-I1 history chain: …`) is NEW output rather than a rewrite of an existing
block, so nothing here describes code that no longer exists. The hashes above are the current
ones; a future session that finds them moved is still under the rule in the paragraph above.

⚠ **REPINNED AGAIN, same day**, after a verifier lane and a mutation lane went over the
REALFIX-I1 landing. `movetap.py` moved for three reasons and **none of them is a printer
this section quotes**: prose corrections at the node-layout comment (the block recycle is
measured on the block's NEWEST node, and the sever pass is the real dangle guarantee), the
future tolerance getting its own constant on its real ground, and twenty-four new selftest
checks. The one OUTPUT that changed is the run summary's chain-cost line, which moved into
`chain_cost_line()` and whose delta now prints as a **Hz change** (`-47% Hz if the gate were
removed`) rather than as an unsigned share — still new output, still not quoted below.
`movesync.py` did not move; its hash is unchanged, which is the check working.

⚠ **REPINNED A THIRD TIME, 2026-08-29, for CANCELWALK-R5 and R7 — and the verdict this
time is ZERO DRIFT, which is worth as much as a hit.** `movetap.py` moved in three commits
none of the notes above records: `d08caa8` (R5 Tier-1, the walk-start footprint), `edb9c37`
(H8 refuted at a desk) and `2361a83` (the R7 review), 392 insertions over 2026-08-24.
**Not one line of it is a printer this section quotes.** An AST comparison of every
top-level function across `c91b90d..HEAD` returns `fence_verdict`, `gate1_verdict`,
`print_episodes`, `count_flips`, `chain_cost_line`, `history_chain` and `early_outs`
**byte-identical**; three functions were added (`_r5_fields`, `controller_read`,
`_selftest_r5`) and eight changed, and the two new decoders carry **zero `print` sites** —
they return dict keys that ride into the stored row and are never rendered. `main()`'s only
change is `sample(...)` gaining `ctx=_ctx`. The independent evidence is stronger than the
argument: `test_probedoc.py` regenerated all **15 of 15** blocks and compared them
byte-for-byte, with the hash as its single FAIL. The only output that moved is
`--selftest`'s, which this section does not quote.

⚠ **AND THE PIN WAS GREEN OVER THINGS THAT WERE ALREADY WRONG, which is the part to read
before trusting the next green.** A sha over the source cannot see the prose between the
blocks, and nobody swept it at either earlier re-pin:

* **The sentence carrying the pin was self-inconsistent.** It said the blocks were produced
  at HEAD `e3dfb98` against these hashes — but `movetap.py` at `e3dfb98` hashes to
  `eedaf547…`, not to the `9ef4b98d…` that was written beside it. The hash was moved twice
  by the two notes above while the HEAD token was left behind, so `e3dfb98` had been stale
  by two re-pins. `test_probedoc.py`'s `PIN_RE` matches only the sha, never the HEAD, so
  nothing could catch it. Both now name `2361a83`.
* **The third-tier paragraph above was false by 53 files.** It said
  `vault/captures/movetap/` holds five files, all 2026-08-19, none carrying `gate_reach`,
  `state_record` or `hist_head`, and that *"no post-C9 movetap capture exists anywhere,
  n = 0"* — which was the stated reason blocks 1–10 are FIXTURE-DRIVEN. **MEASURED
  2026-08-29 over all 60 files and all 78,805 rows: 53 carry all three fields**, the
  earliest being `movetap-20260821T081927.jsonl` — which **predates the 12:23 re-pin of
  that same day by four hours.** It was untrue when the hash was last bumped and nobody
  looked. **33 carry R5/R7's own fields** (`reqtoken`, `async_reqtoken`, `ctrl_status`,
  `walk_suppressed`, `gate_a`), first `movetap-20260824T163558.jsonl`. That paragraph has
  been corrected above; whether blocks 1–10 should be re-derived from a real capture is a
  decision this note does **not** make, but if it is made it must be made in **both**
  witnesses at once — the document's tier word and `probedoc_fixtures.DOC_BLOCKS` — because
  `test_probedoc.py` §5 reddens if they disagree, and relabelling was never a way out.
* **About 25 of this document's ~30 `*.py:NNN` line citations are stale**, including
  **all eight `movesync.py` ones, under a pin that is GREEN** — `movesync.py` has not
  moved since the pin and its citations rotted before it. The substantive claims survive
  (`grep -in white` still returns exactly one hit in `movetap.py` and it is still a comment;
  `movesync.py` still returns none); only the line numbers moved. **They are deliberately
  NOT swept here.** Nothing checks them, they rot again on the next commit, and a
  25-citation sweep that buys a few days is the treadmill this repo has already paid for
  once. The honest fix is a check that resolves a citation against the symbol named beside
  it; until that exists, read every `file.py:NNN` in this document as approximate and grep
  for the symbol instead.

⚠ **THIS SECTION WAS WRONG BEFORE 2026-08-20, in five separate ways, and the record of that
is load-bearing.** The blocks it showed were written **before the instrument existed**, and
every one of them drifted:

1. It printed an `ALIASING: phi 0.011 over 558 usable pairs, p(open) 0.287, white 0.409,
   A = 0.026.` line. **No such line is ever printed, and there is no `white` field** —
   `grep -i white` over `movetap.py` and `movesync.py` returns exactly one hit, and it is a
   COMMENT (`movetap.py:3393`, the word "Whitespace-normalised") -- **no printable string in
   either file carries a `white` field**, which is the load-bearing half and is enforced by
   `test_probedoc.py` §4's AST walk rather than by a grep. The ratio arrives
   inline, in one transition sentence, as block 1's second-to-last line.
2. Its fence header was 2 lines. The code prints **3**, ending
   `each value names the branch it WOULD take on this state:`.
3. It showed an `unread:*  0  0.0%` row. **That row cannot ever print** — `fence_verdict`
   iterates `sorted(reach.items(), key=lambda kv: -kv[1])` -- by DESCENDING COUNT -- and a
   label with no occurrences is not in `reach` at all.
4. Its EPISODES block differed in nearly every particular: no poll-rate line, no
   `effective n = … QUOTE THE EPISODES.` line, a Nyquist line naming one threshold instead
   of two, `4 runs, median 96 samples (9.2 s)` instead of the code's
   `4 run(s), median 96 samples (7.60 s)`, and no `a LOWER BOUND -- censored` marker on the
   min cell.
5. **It showed an APPENDER WITNESS section under `movetap`.** That printer is
   `movesync.print_appender_witness` and `movetap` has none — `grep -c appender_witness
   toolkit/clientscan/movetap.py` = **0**. The section was attributed to the wrong tool
   entirely.

§12 item 10 recorded (1) and part of (3) as accepted residue. It undercounted; the full
account is above and item 10 is now marked closed with what was actually found.

**One more shape correction that is not about §6's text but about how it is used:**
`movetap.gate1_verdict(g1, g1why, early_a, point_bad, n)` takes `early_a` and `point_bad` as
**tally dicts**, not integers — it calls `.get(True, 0)` on them at `movetap.py:4848`. A
caller passing counts raises `AttributeError`. The early-out rows print a count, a percentage
**and** an `(N unread)` tail, which is where that third value comes from.

### Step 13 — the primary answer comes from the tap alone

Each `movetap` prints its own closing block when it stops. **This is the answer to the
question this probe exists to ask**, and it needs no capture, no clock alignment and no
pairing.

**Block 1 — FIXTURE-DRIVEN. STRAIGHT / H1 confirmed.** The closest analogue of what this
section used to show: 402 `shut:append` + 162 `test-runs` over n = 564.

```

THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, NOT an observation that the caller ran. Nothing here sees
0x00605FC0 execute; each value names the branch it WOULD take on this state:
  shut:append                           402   71.3%
  test-runs                             162   28.7%
  EPISODES (this is the effective n, not the sample count):
    poll rate 12.50 Hz over 45.04 s, from the sequence's own timestamps and NOT from the sample rate; the sample rate is 12.51 Hz and the gap between the two is the share of polls that produced no row.
    shut:append                4 run(s), median 96 samples (7.60 s), min 41 (3.20 s, a LOWER BOUND -- censored), 2 censored
    test-runs                  3 run(s), median 47 samples (3.68 s), min 12 (0.88 s), 0 censored
    effective n = 7 episode(s) of real state over 564 real sample(s). QUOTE THE EPISODES.
    Nyquist bar: two samples per half-cycle at 12.50 Hz means this reader can only DETECT alternation whose every dwell exceeds 0.16 s, and can only CHARACTERISE one above 0.40 s.
  6 transition(s) over 563 usable pair(s) at 12.5 Hz = 0.03 of the independent-sample expectation at a 28.7% open share -- the fence persists across many samples, so the shares above are not aliased.
  Pair this file with its gamesrv capture: python toolkit/clientscan/movesync.py
```

Read the aliasing sentence carefully. It is one line, it has no label, and it carries five
things: the transition count, the usable-pair denominator, the rate, the ratio `A`, and the
open share. `A = 0.03` here. **§12 item 5 applies to that sentence** — all five of its cells
are unpinned by any test, so it is an illustration of shape; the *decision* (the `A >= 0.5`
bar) is pinned, and both its denominators are pinned.

**Block 2 — FIXTURE-DRIVEN. Gate 1 and the two early-outs, clean.** This is the second half
of the same closing output.

```

GATE 1 (0x006057E1) ON ITS OWN OPERANDS -- the SYNC agent against its ASYNC
twin, each dated to the clock the client dates it to and each clamped the way
0x005FF820 clamps. NOT a wire proxy:
  above                                 489   86.7%
  below                                  61   10.8%
  undecided                              14    2.5%  (band 9, plane-mismatch 5)
  the 295-305 u band is REFUSED rather than classified: the client's sqrt at 0x0046E870
  is a LUT approximation biased high, so the effective cut is 299.3326 and this
  reader cannot resolve the step. A plane mismatch is refused too -- 0x00709990
  takes a different path there and it is not decoded.

THE TWO EARLY-OUTS ABOVE GATE 1 (each returns 1 = NO SNAP before gate 1 is
reached, and each presents on a capture as "above the cut and nothing snapped"):
  early_out_a (+0x48 != 0 && +0xC4 == 9)          0    0.0%   (0 unread)
  point_invalid (m_point == +inf)                 0    0.0%   (0 unread)
```

Two things the old block did not have. The `undecided` row's label is plain `undecided` —
**not** `undecided (295-305 u band, refused)` — and it carries its own why-breakdown inline,
`(band 9, plane-mismatch 5)`. `plane-mismatch` is a second refusal reason that nothing in the
C6 spec anticipated: `0x00709990` takes a different path across a plane boundary and it is
not decoded. The 4-line paragraph under the table is printed every time and this document
used to omit it entirely.

**Block 3 — FIXTURE-DRIVEN. The single-state STRAIGHT block, and the likeliest real H1
outcome.** If H1 is true, a 40 s STRAIGHT block contains **zero** transitions. This is what
that prints, and §6 has never had a block for it:

```

THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, NOT an observation that the caller ran. Nothing here sees
0x00605FC0 execute; each value names the branch it WOULD take on this state:
  shut:append                           416  100.0%
  EPISODES (this is the effective n, not the sample count):
    poll rate 10.40 Hz over 39.90 s, from the sequence's own timestamps and NOT from the sample rate; the sample rate is 10.40 Hz and the gap between the two is the share of polls that produced no row.
    shut:append                1 run(s), median REFUSED (1 of 1 runs censored by the capture boundary), min 416 (39.90 s, a LOWER BOUND -- censored), 1 censored
    effective n = 1 episode(s) of real state over 416 real sample(s). QUOTE THE EPISODES.
    Nyquist bar: two samples per half-cycle at 10.40 Hz means this reader can only DETECT alternation whose every dwell exceeds 0.19 s, and can only CHARACTERISE one above 0.48 s.
  0 transition(s) over 415 usable pair(s) at 10.4 Hz. The fence never changed state, so there is no aliasing ratio to compute -- a single-state run is reported as one, NOT as a resolved measurement.
  Pair this file with its gamesrv capture: python toolkit/clientscan/movesync.py
```

**There is no aliasing ratio in that block, and that is the point.** One episode, fully
censored, median REFUSED, `A` not computed. Refutation rule 3 (`A >= 0.5`) **cannot be
scored on this block at all** — see §1 rule 3's ⚠ note and §12 item 12. A run that prints
this is not a failed run; it is H1's own prediction, and it must be reported with rules 1
and 2 carrying the weight.

**Block 4 — FIXTURE-DRIVEN. Block A as it really looks: all four labels, plus the drop
markers.** Only labels that actually occur are printed, so blocks 1 and 3 are the sparse
cases. A real positive-control block will show more:

```

THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, NOT an observation that the caller ran. Nothing here sees
0x00605FC0 execute; each value names the branch it WOULD take on this state:
  shut:append                           355   76.8%
  test-runs                              73   15.8%
  world1:append                          15    3.2%
  shut:noop                              14    3.0%
  unread:agent-id-mismatch                5    1.1%
  EPISODES (this is the effective n, not the sample count):
    poll rate 10.40 Hz over 44.81 s, from the sequence's own timestamps and NOT from the sample rate; the sample rate is 10.27 Hz and the gap between the two is the share of polls that produced no row.
    shut:append                9 run(s), median 30 samples (2.79 s), min 1 (0.00 s), 2 censored, 6 split by an unread sample -- the run count is an UPPER bound
    test-runs                  4 run(s), median 20 samples (1.83 s), min 2 (0.10 s), 0 censored
    world1:append              2 run(s), median 7.5 samples (0.63 s), min 6 (0.48 s), 0 censored
    shut:noop                  1 run(s), median 14 samples (1.25 s), min 14 (1.25 s), 0 censored
    unread:agent-id-mismatch   1 run(s), median 5 samples (0.38 s), min 5 (0.38 s), 0 censored
    unread:sample-dropped      1 run(s), median 3 samples (0.19 s), min 3 (0.19 s), 0 censored
    unread:resolve-failed      1 run(s), median 2 samples (0.10 s), min 2 (0.10 s), 0 censored
    effective n = 16 episode(s) of real state over 457 real sample(s). QUOTE THE EPISODES.
    Nyquist bar: two samples per half-cycle at 10.40 Hz means this reader can only DETECT alternation whose every dwell exceeds 0.19 s, and can only CHARACTERISE one above 0.48 s.
    UNRESOLVED: shut:append, test-runs, unread:resolve-failed each show a run of <= 2 samples. That is not a short dwell, it is a dwell this instrument cannot see the bottom of.
  8 transition(s) over 453 usable pair(s) at 10.3 Hz = 0.07 of the independent-sample expectation at a 16.0% open share -- the fence persists across many samples, so the shares above are not aliased.
  Pair this file with its gamesrv capture: python toolkit/clientscan/movesync.py
```

Four things to notice. **(i)** `world1:append` and `shut:noop` are real labels and the
distribution prints them when they occur — the old block showed neither, which is the same
blind spot that produced §12's movetap ITEM 1. **(ii)** `unread:sample-dropped` and
`unread:resolve-failed` appear as their **own episode rows** but **not** in the share table
above: a poll that produced no row is not a sample, so it is counted in `seq` and excluded
from `reach`. **(iii)** A run split by an unread sample is flagged and the run count is
called an **UPPER** bound. **(iv)** The `UNRESOLVED:` line names every state whose minimum
run was ≤ 2 samples — that is the Nyquist bar acting on this specific block, not a generic
warning.

**Block 5 — FIXTURE-DRIVEN. `early_out_a` FIRED.** The mechanism finding §1's collision
audit is watching for:

```

GATE 1 (0x006057E1) ON ITS OWN OPERANDS -- the SYNC agent against its ASYNC
twin, each dated to the clock the client dates it to and each clamped the way
0x005FF820 clamps. NOT a wire proxy:
  above                                 377   81.6%
  below                                  74   16.0%
  undecided                              11    2.4%  (band 7, plane-mismatch 4)
  the 295-305 u band is REFUSED rather than classified: the client's sqrt at 0x0046E870
  is a LUT approximation biased high, so the effective cut is 299.3326 and this
  reader cannot resolve the step. A plane mismatch is refused too -- 0x00709990
  takes a different path there and it is not decoded.

THE TWO EARLY-OUTS ABOVE GATE 1 (each returns 1 = NO SNAP before gate 1 is
reached, and each presents on a capture as "above the cut and nothing snapped"):
  early_out_a (+0x48 != 0 && +0xC4 == 9)         31    6.7%   (6 unread)
    *** IT FIRED. That is a mechanism finding, not a puzzle: on those samples the test returns NO SNAP above gate 1, so no gate is deciding anything.
  point_invalid (m_point == +inf)                 0    0.0%   (6 unread)
```

The `*** IT FIRED.` line prints for either early-out. **If you see it, escalation trigger
§2(b) is not what you have** — you have the fourth or fifth exit acting above gate 1, and
the "above the cut, nothing snapped" population is explained without any gate deciding
anything. Note the `(6 unread)` tail on both rows: the early-out tallies have their own
three-valued domain and their own unread count.

**Block 6 — FIXTURE-DRIVEN. WIGGLE / H2 shape, with the median refusal.** `test-runs` at
90.1%, both runs censored:

```

THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, NOT an observation that the caller ran. Nothing here sees
0x00605FC0 execute; each value names the branch it WOULD take on this state:
  test-runs                             508   90.1%
  shut:append                            56    9.9%
  EPISODES (this is the effective n, not the sample count):
    poll rate 10.40 Hz over 54.13 s, from the sequence's own timestamps and NOT from the sample rate; the sample rate is 10.35 Hz and the gap between the two is the share of polls that produced no row.
    test-runs                  2 run(s), median REFUSED (2 of 2 runs censored by the capture boundary), min 254 (24.33 s, a LOWER BOUND -- censored), 2 censored
    shut:append                1 run(s), median 56 samples (5.29 s), min 56 (5.29 s), 0 censored
    effective n = 3 episode(s) of real state over 564 real sample(s). QUOTE THE EPISODES.
    Nyquist bar: two samples per half-cycle at 10.40 Hz means this reader can only DETECT alternation whose every dwell exceeds 0.19 s, and can only CHARACTERISE one above 0.48 s.
  2 transition(s) over 563 usable pair(s) at 10.3 Hz = 0.02 of the independent-sample expectation at a 90.1% open share -- the fence persists across many samples, so the shares above are not aliased.
  Pair this file with its gamesrv capture: python toolkit/clientscan/movesync.py
```

```

GATE 1 (0x006057E1) ON ITS OWN OPERANDS -- the SYNC agent against its ASYNC
twin, each dated to the clock the client dates it to and each clamped the way
0x005FF820 clamps. NOT a wire proxy:
  below                                 511   90.6%
  above                                  39    6.9%
  undecided                              14    2.5%  (band 10, plane-mismatch 4)
  the 295-305 u band is REFUSED rather than classified: the client's sqrt at 0x0046E870
  is a LUT approximation biased high, so the effective cut is 299.3326 and this
  reader cannot resolve the step. A plane mismatch is refused too -- 0x00709990
  takes a different path there and it is not decoded.

THE TWO EARLY-OUTS ABOVE GATE 1 (each returns 1 = NO SNAP before gate 1 is
reached, and each presents on a capture as "above the cut and nothing snapped"):
  early_out_a (+0x48 != 0 && +0xC4 == 9)          0    0.0%   (0 unread)
  point_invalid (m_point == +inf)                 0    0.0%   (0 unread)
```

`median REFUSED (2 of 2 runs censored by the capture boundary)` is the criterion change from
§1 doing its job in the output. The min cell still prints, tagged
`a LOWER BOUND -- censored`. Effective n = **3**, over 564 samples. Quote the 3.

**Block 7 — FIXTURE-DRIVEN. THE ALIASING REFUSAL, and it exits 1.** Seeded simulation of a
fence open 15 ms / shut 185 ms at 10.4 Hz over 60 s — the exact case the old `flips*4 >= n`
guard waved through:

```

THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, NOT an observation that the caller ran. Nothing here sees
0x00605FC0 execute; each value names the branch it WOULD take on this state:
  shut:append                           584   93.6%
  test-runs                              40    6.4%
  EPISODES (this is the effective n, not the sample count):
    poll rate 10.40 Hz over 59.90 s, from the sequence's own timestamps and NOT from the sample rate; the sample rate is 10.40 Hz and the gap between the two is the share of polls that produced no row.
    shut:append               39 run(s), median 10 samples (0.87 s), min 1 (0.00 s), 2 censored
    test-runs                 38 run(s), median 1 samples (0.00 s), min 1 (0.00 s), 0 censored
    effective n = 77 episode(s) of real state over 624 real sample(s). QUOTE THE EPISODES.
    Nyquist bar: two samples per half-cycle at 10.40 Hz means this reader can only DETECT alternation whose every dwell exceeds 0.19 s, and can only CHARACTERISE one above 0.48 s.
    UNRESOLVED: shut:append, test-runs each show a run of <= 2 samples. That is not a short dwell, it is a dwell this instrument cannot see the bottom of.
  REFUSED: 76 transition(s) over 623 usable pair(s) at 10.4 Hz is 1.02 of what INDEPENDENT samples would give at this 6.4% open share. The fence is changing at or above this reader's own rate, so the shares above are aliased and mean nothing. THIS is the outcome that earns the hook: an int3 at 0x00606002 on the trnblock.c pattern counts every evaluation instead of sampling them (toolkit/clientscan/trnhook/).
```

`A = 1.02`, inside C1's stated 0.94–1.04 calibration band for lopsided fast cases. **In a
WIGGLE block this is expected and is not an escalation trigger. In a STRAIGHT block it is
escalation trigger §2(a)** — but only after reading `pairs` against `n` per the failure
table, because a flaky read can manufacture transitions.

**Block 8 — FIXTURE-DRIVEN. THE UNREAD REFUSAL, and it exits 1.** 29% of samples could not
read the record:

```

THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, NOT an observation that the caller ran. Nothing here sees
0x00605FC0 execute; each value names the branch it WOULD take on this state:
  shut:append                           280   65.1%
  unread:agent-id-mismatch              126   29.3%
  test-runs                              24    5.6%
  EPISODES (this is the effective n, not the sample count):
    poll rate 10.40 Hz over 41.25 s, from the sequence's own timestamps and NOT from the sample rate; the sample rate is 10.40 Hz and the gap between the two is the share of polls that produced no row.
    shut:append               40 run(s), median 7 samples (0.58 s), min 7 (0.58 s), 1 censored, 40 split by an unread sample -- the run count is an UPPER bound
    unread:agent-id-mismatch  46 run(s), median 3 samples (0.19 s), min 1 (0.00 s), 1 censored
    test-runs                  6 run(s), median 4 samples (0.29 s), min 4 (0.29 s), 0 censored, 6 split by an unread sample -- the run count is an UPPER bound
    effective n = 46 episode(s) of real state over 304 real sample(s). QUOTE THE EPISODES.
    Nyquist bar: two samples per half-cycle at 10.40 Hz means this reader can only DETECT alternation whose every dwell exceeds 0.19 s, and can only CHARACTERISE one above 0.48 s.
    UNRESOLVED: unread:agent-id-mismatch each show a run of <= 2 samples. That is not a short dwell, it is a dwell this instrument cannot see the bottom of.
  REFUSED: 126 of 430 samples (29%) could not read the record. No share above is a fact about the client. Fix the read before quoting any of them.
```

`No share above is a fact about the client.` The share table still prints — that is
deliberate, and §12 item 7 explains why: the refusal sentence's own cells are unpinned, and
the table above it is the redundancy that would expose a refusal reading `0 of n (0%)`.

**Block 9 — FIXTURE-DRIVEN. Gate 1's own refusal, on the ASYNC twin, and it exits 1.**
A different denominator from the fence's, and it says so:

```

GATE 1 (0x006057E1) ON ITS OWN OPERANDS -- the SYNC agent against its ASYNC
twin, each dated to the clock the client dates it to and each clamped the way
0x005FF820 clamps. NOT a wire proxy:
  above                                 280   56.0%
  unread:async-slot-null                 90   18.0%
  unread:async-id-mismatch               60   12.0%
  below                                  55   11.0%
  undecided                              15    3.0%  (band 11, plane-mismatch 4)
  the 295-305 u band is REFUSED rather than classified: the client's sqrt at 0x0046E870
  is a LUT approximation biased high, so the effective cut is 299.3326 and this
  reader cannot resolve the step. A plane mismatch is refused too -- 0x00709990
  takes a different path there and it is not decoded.

THE TWO EARLY-OUTS ABOVE GATE 1 (each returns 1 = NO SNAP before gate 1 is
reached, and each presents on a capture as "above the cut and nothing snapped"):
  early_out_a (+0x48 != 0 && +0xC4 == 9)          0    0.0%   (0 unread)
  point_invalid (m_point == +inf)                12    2.4%   (0 unread)
    *** IT FIRED. That is a mechanism finding, not a puzzle: on those samples the test returns NO SNAP above gate 1, so no gate is deciding anything.

  REFUSED: 150 of 500 samples (30%) could not read the ASYNC twin. No share in this block is a fact about the client -- and the 'above the cut, no snap' population is exactly what an unreadable twin would fabricate. THE FENCE VERDICT ABOVE IS UNAFFECTED; it has its own denominator.
```

**`THE FENCE VERDICT ABOVE IS UNAFFECTED; it has its own denominator.`** That sentence is
the whole reason the two verdicts are separate printers. A failed control does not void a
treatment — an unreadable ASYNC twin kills gate 1's shares and leaves the fence's intact.

**Block 10 — FIXTURE-DRIVEN. Nothing carried the field at all.** This is what a run from the
wrong tree prints, and it is a refusal rather than a zero:

```

THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, NOT an observation that the caller ran. Nothing here sees
0x00605FC0 execute; each value names the branch it WOULD take on this state:
  no sample carried a gate_reach at all. This run says NOTHING about the fence.
```

```

GATE 1 (0x006057E1) ON ITS OWN OPERANDS -- the SYNC agent against its ASYNC
twin, each dated to the clock the client dates it to and each clamped the way
0x005FF820 clamps. NOT a wire proxy:
  no sample carried a gate1 at all. This run says NOTHING about gate 1. The fence verdict above is unaffected.
```

`This run says NOTHING about the fence.` If you see that, go back to step 1 — you are almost
certainly in `gatefire-probe-plan-9c31de` or another pre-C1 tree.

**Read the STRAIGHT blocks' files first. They carry the finding.** Quote their episode
counts, never their sample counts.

### Step 14 — the secondary cross-tab, on the FREE block only

Pass both paths explicitly. Do **not** use the bare form (step 6).

```powershell
cd C:/gd/Rurik && python toolkit/clientscan/movesync.py --movetap "C:\gd\Rurik\vault\captures\movetap\movetap-<FREE block stamp>.jsonl" --capture "C:\gd\Rurik\vault\captures\gamesrv\authsrv-<stamp>-c1.jsonl"
```

It echoes `movetap:` and `capture:` on its first two lines. **Read them.**

**Block 11 — FIXTURE-DRIVEN. The whole `movesync` fence section as it prints post-C9.**
This is the block this document used to show as a five-line snippet:

```

THE FENCE ON THE SNAP TEST (0x006055E0), from movetap's `gate_reach` -- a COUNTERFACTUAL label on a state read, not an observation that the caller ran:
   shut:append                           326   83.6%  fenced
   test-runs                              60   15.4%  reachable
   shut:noop                               3    0.8%  fenced
   world1:append                           1    0.3%  fenced
   the fence at each hard jump (n=9):
     server t     step   fence BEFORE                           fence AT
        20.769   4920.0   shut:append                            shut:append
        33.846    600.0   shut:append                            shut:append
        42.308    600.0   shut:append                            shut:append
        69.231   4440.0   shut:append                            shut:append
        96.154   3000.0   test-runs                              shut:append
       171.538   1080.0   shut:append                            shut:append
       183.077   3480.0   shut:append                            test-runs
       244.615   3960.0   shut:append                            shut:append
       269.231   2040.0   shut:append                            shut:append
     THREE-WAY over the BEFORE column, and they sum to 9:
       reachable          1   BEFORE read `test-runs` -- fence open, world != 1
       fenced             8   BEFORE read a real state in which the test is NOT reached (shut:append x8)
       unread/missing     0   (none) -- NOT folded into either count above, which is what this bucket exists for
     1 of 9 snap(s) began with the record in the ONE state where 0x006055E0 is reached; 8 began in a state whose branch is 0x00605840 or a bare return.
     THAT SECOND HALF IS AN INFERENCE AND HERE IS ITS PREMISE: the sampler reads `clientControlled` (AgTrack record+0x00) and the agent's world index, never the instruction pointer, and the caller's tail at 0x00606009/0x00606013 selects the branch from exactly those two fields. NOTHING HERE OBSERVED 0x00605840 EXECUTE. For an observation rather than an inference, read the appender witness below.

   APPENDER WITNESS -- the only POSITIVE observations in this section, over 3119 consecutive pair(s) of 3120 movetap sample(s):
     (a) a WRITE to the state record landed between two samples: 104 of 3119 judged pair(s) (hist_head moved on 104, the +0x08..+0x14 cache on 102; the arms overlap and the tally is the OR)
         arm coverage: hist_head readable both sides on 3119 pair(s), the cache on 3119. The write is OBSERVED; that 0x00605840 is what wrote it is the inference, premised on those being the fields it writes.
     (b) hist_head -> 0 with gate_reach UNCHANGED: 2 of 3078 pair(s) where both gate_reach reads are real and equal. EACH SUCH PAIR is an arm or an AgTrack::Clear running BETWEEN two samples -- an aliasing witness that does not depend on the state field whose aliasing is the question.
     LIMIT 1 -- a zero above is WEAK, and the window is CONDITIONAL: the appender dedups at 2500 ms (`0x0060593A cmp eax, 0x9c4`), but that test is only the FIRST of a chain -- 0x0060594B, 0x0060595E, 0x0060596B, 0x0060597B each jump to the SAME append target 0x00605A2F on INEQUALITY -- so the append is suppressed only when the head is younger than 2500 ms AND the sample still matches the cached one. A MOVING agent CAN append twice inside the window; silence across a shorter pair proves nothing only where the cached fields also held still. Spacing p50 0.096s, max 0.096s; 0 of 3119 judged pair(s) span 2.5s or more.
     LIMIT 2: the `shut:noop` branch writes nothing at all and is unobservable by construction -- an absent witness is not evidence that it did not run.
```

Four differences from what §6 used to quote, all of them structural:

- The distribution rows carry a trailing **bucket column** — `fenced` / `reachable` /
  `unread` — so a mislabelled row prints its share beside the wrong bucket and is visible.
  §12 item 2 is about exactly this table and is worth reading before quoting a row from it.
- The jump tally is a **4-line three-way table plus a 2-line sentence**, not the one-liner
  `jump rows: 1 REACHABLE (test-runs) / 8 FENCED (shut:*|world1:*) / 0 UNREAD-OR-MISSING.`
  The three buckets are printed and **sum to the row count**, which is stated in the header
  line so a reader can check it.
- The sentence under it names its own premise in capitals —
  `NOTHING HERE OBSERVED 0x00605840 EXECUTE` — which is C9's purge of asserted executions.
- **The APPENDER WITNESS lives here**, at the end of `print_fence`, and nowhere else. Arm
  (b) — `hist_head -> 0 with gate_reach UNCHANGED` — is the aliasing witness that does not
  depend on the state field whose aliasing is the question, and it is the number §2's
  polling-vs-hook decision actually reads.

**Block 12 — OBSERVED. What the same command prints TODAY, on the newest paired data the
vault actually holds.** Real stdout, `movetap-20260819T145939.jsonl` ×
`authsrv-20260819T145717-c1.jsonl`:

```
movetap: movetap-20260819T145939.jsonl
capture: authsrv-20260819T145717-c1.jsonl

clock offset 1787165837.301 from 8393 truncated `wall` stamp(s) [PRE-REALFIX-T1, max-estimator]: residual 1.000 s = 288 u at 288 u/s -- this capture predates the float stamp
SOURCE 268 spliced self-reports (236 x 0x003D + 32 x 0x0047); `position_report` agrees exactly
CADENCE p50 0.254s  MAX 131.767s  actively reported 74.2s = 23% of a 320.3s span
PAIRS 251 of 268 reports and 2063 samples (dropped 17 outside +/-0.25s)
PAIRED WINDOW 177.3s, of which 67.5s actively reported (38%)

separation (live vs the client's own report), n=251:
   p50 1164.3 u   p90 2162.6 u   max 3648.0 u

HARD JUMPS -- speed > 400 u/s at dt >= 0.05s, or >= 520 u below it, with the separation either side. THE VERDICT.
   n = 6 of 250 paired interval(s)
   server t     step   excess     before      after
     150.562   1968.9   1036.6     1033.1        4.6
     201.230    971.2    543.6      678.1       18.1
     224.770   3166.2   3022.3     3221.4       93.9
     265.946   2016.6   1867.2     2069.1       23.9
     281.660    838.6    699.6      705.8        0.0
     314.165   3405.3   3164.5     3430.0       20.2
   magnitude p50 2017 u  max 3405 u;  excess over a 288 u/s walk p50 1867 u  max 3165 u
   RATE 2.03/min of the paired window (177.3s), 5.33/min of actively-reported time (67.5s = the sum of gaps <= 1.042s, a threshold borrowed from the legacy bar)
   separation mean 1856.2 u -> 26.8 u  (collapse 99%)

THE FENCE ON THE SNAP TEST (0x006055E0), from movetap's `gate_reach` -- a COUNTERFACTUAL label on a state read, not an observation that the caller ran:
   REFUSED: none of the 251 paired samples carries `gate_reach`. This movetap predates the field -- re-run `python toolkit/clientscan/movetap.py` and pair the new file. Nothing here is a fact about the client, and in particular it is NOT 'the fence was never open'.
   the fence at each hard jump (n=6):
     server t     step   fence BEFORE                           fence AT
       150.562   1968.9   missing:sample-carries-no-gate_reach   missing:sample-carries-no-gate_reach
       201.230    971.2   missing:sample-carries-no-gate_reach   missing:sample-carries-no-gate_reach
       224.770   3166.2   missing:sample-carries-no-gate_reach   missing:sample-carries-no-gate_reach
       265.946   2016.6   missing:sample-carries-no-gate_reach   missing:sample-carries-no-gate_reach
       281.660    838.6   missing:sample-carries-no-gate_reach   missing:sample-carries-no-gate_reach
       314.165   3405.3   missing:sample-carries-no-gate_reach   missing:sample-carries-no-gate_reach
     THREE-WAY over the BEFORE column, and they sum to 6:
       reachable          0   BEFORE read `test-runs` -- fence open, world != 1
       fenced             0   BEFORE read a real state in which the test is NOT reached (none)
       unread/missing     6   (missing:sample-carries-no-gate_reach x6) -- NOT folded into either count above, which is what this bucket exists for
     REFUSED: 6 of 6 jump row(s) (100%) could not be classified, at or above the 25% bar. There is no sentence about the client available from 6 row(s) with that many holes in them.
     ...and the population refusal above cannot stand in for this one: it is a different denominator over a different population -- every paired sample, hundreds of rows -- while this bar is over these 6.

   APPENDER WITNESS -- the only POSITIVE observations in this section, over 2062 consecutive pair(s) of 2063 movetap sample(s):
     REFUSED: none of the 2062 pair(s) carries `state_record` or `hist_head` on BOTH sides (2062 unjudgeable). This movetap predates those fields -- re-run `python toolkit/clientscan/movetap.py` and pair the new file. This is NOT 'the appender never ran'.

   CONTROL (paired 7 s out of true): n=6 mean 1713.9 -> 679.2 u (collapse 60%)
   WARNING: the control collapses nearly as much as the real pairing. This statistic is measuring the procedure.

   alignment sweep (collapse % vs offset error):
      -1.00s:89%  -0.50s:94%  -0.25s:96%  +0.00s:99%  +0.25s:97%  +0.50s:95%  +1.00s:91%

LEGACY BAR -- step >= 300 u, no time term. GAP-CONTAMINATED; never a verdict.
   REFUSING a verdict: 32 of 267 report intervals exceed the 1.042s free-silence line, so a walk at 288 u/s clears 300 u inside them.
   refused count: 28 paired step(s) >= 300 u
```

**This is the single most useful block in this section for day one.** Every movetap capture
in the vault predates `gate_reach`, `state_record` and `hist_head`, so until the run happens
this is what a paired run prints — and every one of the three fence lanes **refuses by
name** rather than returning a zero:

- `REFUSED: none of the 251 paired samples carries 'gate_reach'. … Nothing here is a fact
  about the client, and in particular it is NOT 'the fence was never open'.`
- every jump row reads `missing:sample-carries-no-gate_reach`, the three-way tally puts all
  6 in `unread/missing`, and the sentence refuses at **100%** against the 25% bar.
- `REFUSED: none of the 2062 pair(s) carries 'state_record' or 'hist_head' on BOTH sides
  … This is NOT 'the appender never ran'.`

**If your own run prints any of those three, your tap did not carry the new fields** — check
step 1 before reading anything else in the output. The wire half above them is unaffected and
is real: the hard-jump table, the separation collapse, the control and the alignment sweep
all came out of these two files.

**Block 13 — OBSERVED. The wire half alone.** Note the exact form — `--wire-only` is a flag
and takes no argument:

```powershell
cd C:/gd/Rurik && python toolkit/clientscan/movesync.py --wire-only --capture "C:\gd\Rurik\vault\captures\gamesrv\authsrv-<stamp>-c1.jsonl"
```

```

=== authsrv-20260819T145717-c1.jsonl
    SOURCE  268 client self-reports, SPLICED from the decoded c2s stream (236 x 0x003D + 32 x 0x0047)
            cross-check: `position_report` agrees exactly (268 rows)
    GRANTS  40 player 0x0029 to agent 1, decoded from the wire bytes (never from a label)
    DENOMINATOR  267 interval(s) over 320.3s
            cadence p50 0.254s   MAX 131.767s
            actively reported 74.2s = 23% of span; the rest is silence
            THE HONEST BAR: at 288 u/s a 300 u step is FREE above 1.042s of silence, and 32 of 267 intervals (12%) are that silent

    HARD JUMPS -- TWO ARMS, and each is the one the other cannot be. THE VERDICT.
       at dt >= 0.05s: implied speed > 400 u/s. Silence cannot mint one -- a longer dt LOWERS an implied speed.
       below that dt, where a speed is not a measurement: displacement >= 520 u. Retail's largest step below the floor is 19.15 u of 82 intervals, and its largest inside 2.0s is 517.87 u, so retail scores 0 on both arms.
       n = 7 of 267 interval(s)
       magnitude                p50 1969 u     max 3405 u
       excess over budget       p50 1208 u     max 3165 u   (d - 288*dt: what no walk explains)
       implied speed            p50 1794 u/s   max 6335 u/s
          ...and that speed is THE GATE'S OWN INPUT, not a headline: for a discontinuity the denominator is a window the event itself created, so it moves with the report cadence and the two lines above do not.
       arms: 7 by SPEED (> 400 u/s at dt >= 0.05s), 0 by DISTANCE (>= 520 u below that dt)
       1 of 7 straddle a PLANE FLIP (`values[2]`). ANNOTATION, NOT EXCLUSION -- planes 0/18/19 share the x/y frame on this corpus, so a flip does not make a displacement fictional.
       RATE  1.31/min of span (320.3s)
             5.66/min of actively-reported time (74.2s = the sum of gaps <= 1.042s)
             THAT THRESHOLD IS `FREE_SILENCE` = 300/288 -- borrowed from the LEGACY bar this file otherwise calls never-a-verdict, and load-bearing:
             0.300s -> 14.21/min   1.042s -> 5.66/min   5.000s -> 3.40/min
             so the active-time rate is not quotable without the threshold that made it.
       RECONCILE: 2 of 7 hard interval(s) are THEMSELVES longer than 1.042s (3.237s, 1.485s), so they happened in time the active denominator EXCLUDES -- that rate's numerator counts events its own denominator does not contain.
       LANDING vs the granted path: perp p50 78.3 u   on-path 4/7
       CONTROL (an unrelated grant):  perp p50 1582.2 u   on-path 0/7
       grant age at the jump: p50 1.18s  max 18.77s
       5 of 7 row(s) are DEGENERATE -- the grant-time report IS the pre-jump record, so the landing sits on its own segment by construction
         non-degenerate: on-path 2/2

    LEGACY BAR -- step >= 300 u, no time term. GAP-CONTAMINATED; never a verdict.
       REFUSING a verdict: 32 of 267 intervals (12%) exceed the 1.042s free-silence line. Ordinary walking clears this bar inside those gaps, so what follows is a mixture, not a measurement.
       refused count: 31 step(s) >= 300 u = 23 walking (<= 288 u/s) + 7 clearing the HARD bar + 1 neither (360.3 u/s)
       refused rate:  5.81/min of span
```

⚠ **`--wire-only` prints NO fence section at all.** It is a different printer
(`movesync.print_wire_only`, `movesync.py:932`), not a subset of the paired one. An operator
reaching for the wire half to check the fence would find nothing there and could misread that
absence as a null. Use the paired form for anything about the fence.

### What each hypothesis literally looks like

**H1 (FENCE-CLOSED) confirmed** — the STRAIGHT files read like **block 1** (few transitions,
`shut:append` dominant, `A` well under 0.5) or like **block 3** (no transitions at all, no
`A`), while the WIGGLE files show `test-runs` in **block 6**'s shape, and `movesync`'s jump
tally reads like **block 11**: most rows `fenced`, one or two `reachable`.

→ **The fence explains the 92.7%.** No exit is doing anything for most of the time.
**But read caveat 4 before writing that sentence**: block 1 is what a 15 ms / 185 ms fence
would also print, and it is `A` — not the share — that tells the two apart. And if the block
looks like **block 3**, there is no `A` at all, so that discrimination is unavailable and the
claim must be made on rules 1 and 2 alone. Block 7 is what the aliased case looks like when
the guard catches it.

**H2 (THE EXITS DECIDE) confirmed** — `test-runs` ~90% in *both* arms, as in **block 6**, no
separation between them, and either gate 1's distribution nearly all `below` (block 6's
second half) or a surviving `above`-and-no-snap population in which an early-out is satisfied
(**block 5**).

→ **The 92.7% was an artefact of the wire proxy**, which over-stated separation. This is
this arc's most frequent failure mode (`warpscan`, the pre-splice `movesync`, the "20 ms
intervals"), and it would send the work back to the *pairing*, not forward to a hook.

If instead `above` **survives** at high share with `test-runs` and no snap, look at
`early_out_a` and `point_invalid` in the same rows **before** concluding anything about
gates 2 and 3. Either one firing there is a mechanism finding, not a puzzle — and block 5 is
what that looks like.

**Neither of them** — e.g. snaps whose preceding sample reads `shut:*` with a real
separation collapse. Then look at `0x005FCAA0`, the gate-free `ResyncAllAsync`, whose three
callers include two that fire when the local command layer's own path test returns 0. That
is the arc's unexplained 12–59 s snaps, and this would be the first instrument that could
name them.

---

## 7. FAILURE TABLE

| symptom | most likely cause | the check that confirms it |
|---|---|---|
| `movetap` refuses to start: `unrecognized arguments: --block` (or `--note`) | You copied the pre-2026-08-20 step 10. Those flags never existed | The real parser is `[--pid] [--hz] [--seconds] [--selftest] [--any-build]` (`movetap.py:4301-4308`). Record the block letter by hand against the file stamp |
| Tap's closing block reads `no sample carried a gate_reach at all` (§6 block 10); `movesync` prints `REFUSED: … predates the field` (§6 block 12) | You ran from the wrong tree — most likely the `gatefire-probe-plan-9c31de` worktree, which is still on disk 36 commits back and answers a `cd` without error | `grep -c gate_reach toolkit/clientscan/movetap.py` **in the shell you actually used** must be **31**, and `grep -c "shut:apply"` must be **0** (step 1). The stale tree answers 15 and 8 |
| Capture has `gate_reach` but no `sep` / `gate1` / `early_out_a` | Impossible on the merged tree — C6/C7 are in the same commit. If you see it, you are on a hand-edited tree | The six greps at the end of step 2. All six differ between the merged and stale trees |
| Rows say `shut:apply`, not `shut:append` | A pre-C9 tree. That string is written into every stored row permanently | `grep -c "shut:apply" toolkit/clientscan/movetap.py` must be **0**. `movesync` will still *read* such a file and prints a `NOTE:` line counting the legacy rows, but the tap that wrote them is the wrong one |
| `movetap` exits `FAIL: found TLS blocks but none resolved...` | Started before the client was in a map | `session.py` must have printed `[PASS] ... body is in the map` first (step 12) |
| `movesync` prints `FAIL: fewer than 20 pairs` | The tap window did not overlap the capture, **or** `newest()` picked a foreign file | Read the `movetap:` / `capture:` echo lines. Twenty foreign gamesrv captures landed today by 12:53 in a vault of 984 — re-run with explicit `--movetap`/`--capture` (step 6) |
| `movetap` FAILs on the sample floor | The reader stalled, or the block was too short | Its own line: `N samples over Xs = Y Hz` against `floor = elapsed * target_hz * 0.5`. `MIN_SAMPLES` 40 / `MIN_SPAN_SECONDS` 5 are absolute |
| Fence reads `shut:*` at 100% including blocks A and A′ | **Wrong record address** — not a finding | Blocks A/A′ must show `test-runs`. If not, the run is void. Cross-check `agtrack_count` against the agent-array size, and `agent_id_field` against `agent` |
| Many `unread:agent-id-mismatch` | `agent+0x10` disagrees with the id resolved through ChCli — we are holding the wrong object | The field is in every row; the fence's own refusal fires at ≥ 25% (§6 block 8) |
| The tap prints no `fence …` line for a whole STRAIGHT block | **Expected under H1**, and it is not a fault | The closing block is where you find out: §6 block 3 (one censored episode, no `A`) is the H1 shape. §6 block 10 is the wrong-tree shape. They are not confusable — one names a label, the other says no sample carried the field |
| Gate 1's block ends `REFUSED: … could not read the ASYNC twin` | C6's twin read is failing — a different failure from the fence's | §6 block 9. **The fence verdict is unaffected and says so in its own sentence.** Do not discard the fence result because gate 1 refused |
| `undecided` carries a large `plane-mismatch` count | The SYNC and ASYNC agents are on different navmesh planes, where `0x00709990` takes an undecoded path | Not an escalation trigger and not a fault. It is a refusal, printed in the `undecided` row's own breakdown (§6 block 2) |
| `REFUSED: … is 1.02 of what INDEPENDENT samples would give` in a **WIGGLE** block | Expected. The fence is flipping fast, which is what WIGGLE does | Compare against the STRAIGHT files. **Not an escalation trigger** (§6 block 7) |
| The same refusal in a **STRAIGHT** block | Polling cannot resolve this fence | **Escalate (§9)** — *but only after* the flaky-read exclusion. Read `pairs` (usable consecutive pairs) against `n`: with C3 landed, `unread` values cannot enter the flip count. If `pairs` is far below `n`, the read is flaky and the finding is about the reader, not the fence |
| `A` looks high but `unread:*` is 10–20% | The pre-C3 contamination band: `real → unread → real` counted as two flips, ~0.20 flips/sample, below the 25% unread refusal | C3 is landed on the merged tree, so this is a symptom of a stale tree rather than of the fence. This exact failure would have sent an evening to a hook DLL for a bad read |
| `movetap` prints `median REFUSED (N of N runs censored by the capture boundary)` | Correct behaviour, not a fault. The block was too short to contain a complete run | Quote the **minimum uncensored run** and the **episode count**; a censored run is a lower bound and is tagged `a LOWER BOUND -- censored` in the min cell (§6 blocks 3 and 6) |
| `movesync` refuses the jump sentence: `could not be classified, at or above the 25% bar` | C4 working. The old code folded these into "the rest reached the appender" | Look at the three-way tally above it. A could-not-read is not a fence-shut. On a pre-C9 movetap this fires at 100% (§6 block 12) |
| `--wire-only` shows no fence at all | Not a fault, and not a null | `--wire-only` is a **different printer** (`print_wire_only`) with no fence section (§6 block 13). Use the paired form |
| Client dies ~30 s in, `Assertion: found, Map.cpp(1762)` | Server and client archives disagree on the map | `contentids.preflight` runs automatically at launch. It was 12/12 when last run; **that verdict was not re-executed for this rewrite** and needs both archives. A running client holds `Gw.dat` open exclusively, so this cannot be checked afterwards |
| Client hangs at character select | `_play` **refused** rather than clicking at a coordinate of unknown meaning — the window was not 1936×1040 | Read the harness output for the refusal before assuming the client died. A previous session left a client at 716×1040 and put the Play fraction on **Delete**, six times |
| Client stuck on *Connecting to ArenaNet*, no sockets at all | Updater alive on a caged build | `dhbuild.py` must read `updater=killed` for `run/`. Rebuild with `make_custom_client.py`; **do not open the cage** |
| Everything green, capture lands in a directory `git status` cannot see | You used RUNBOOK's hand-rolled loop, whose `--vault vault/captures/gamesrv` is **relative** and lands in a phantom worktree vault | `Test-Path (Join-Path (git rev-parse --show-toplevel) 'vault')` — **True** from `C:\gd\Rurik`, **False** from any worktree. ⚠ **CORRECTED: this row used to name the worktree path and expect False**, which inverts and stops catching anything now that every command names main. `session.py` is not affected — it builds every path with `vault_path()` |
| Two clients running; the tap reads the wrong one | `gw_pids()[-1]`; the multi-instance mutex is NOPed on every build here | Always `--pid NNNN` from `session.py`'s own line (step 8) |

---

## 8. WHAT THIS RUN CANNOT ANSWER

The full statement is the caveat box in §5 and it is not repeated here. The five items
that constrain what the write-up may claim, plus one found while syncing this document to
the shipped code:

1. **"The dispatch was never called" vs "it was called but took `shut:noop`."** Polling
   samples state, not events. The appender witness (C5) turns *part* of this into a
   positive observation — `hist_head` or the `+0x08..+0x14` cache changing witnesses an
   append branch — but the `shut:noop` branch writes nothing at all, and the appender's
   dedup (`0x0060593A`, and the four conditional jumps after it) means silence under 2.5 s
   proves nothing **only where the cached fields also held still**. Only a breakpoint at
   `0x00606002` closes the rest. **And note where the witness is:** `movesync`, not
   `movetap` — the tap alone never prints one, so step 13 cannot answer this and step 14
   must be run to get even the partial answer.
2. **Gate 3 is not computable offline.** `0x005FEF70` reads neighbouring agents' predicted
   positions, radii, team and a visibility bitmap, then runs a terrain trace. This run
   attributes it only by elimination, and elimination has failure modes — now with two
   more exits above gate 1 in the elimination chain than the previous draft knew about.
3. **Gate 2 stays n = 0** unless a snap classifies `gate1 == "below"` with neither
   early-out satisfied. That is the escalation trigger, and gate 2 is the one gate with a
   server-side fix.
4. **Which agent is fenced.** `AgTrack+0x14` records the last id the re-armer touched;
   `movetap` polls only the ChCli-controlled agent, resolved through `OFF_SYNC_ARRAY`. If
   the interesting snaps happen on a hero or a follower, this instrument will not see
   them. Nothing in this run checks. **UNVERIFIED, and it matters for C7/C8:** whether the
   early-outs' operands are the SYNC record movetap reads or its ASYNC twin is exactly
   what C6's `AGBASE+0x14C` read must settle — record both and say which you quoted.
5. **n = 1 session is n = 1, and it is n = 3 episodes per arm.** The fence is per-agent and
   per-map, the loopback instance has no `0x002C` clearing edge at all, and every STRAIGHT
   episode is censored by its block. Do not treat one run's shares as settling anything.
6. **Whether the fence aliased, on a block where it never changed.** Added 2026-08-20. `A`
   is computed from transitions; a block with zero transitions has none, and the printer
   says so rather than printing a number (§6 block 3). That is the correct refusal, but it
   means the H1-shaped outcome is exactly the outcome on which the aliasing check is silent.
   A fence that opens for 15 ms once per second and is never caught open would print
   `100.0% shut:append`, one episode, and no `A` — indistinguishable, from this block alone,
   from a fence that was genuinely shut for 40 s. Arm (b) of the appender witness in `movesync`
   is the only independent evidence available for that case, and it needs the FREE block's
   pairing to be read at all.

---

## 9. THE ESCALATION, if it is earned

Triggered **only** by §2(a) or §2(b). It is a second evening, and the prerequisite is real:

- **No `.c` under `toolkit/clientscan/trnhook/` names `0x00606002`, `0x006055E0`,
  `0x0060580A` or `0x0060581E`** — checked across all seven sources (`trnblock.c`,
  `trnhook.c`, `trnhook6.c`, `trnint3.c`, `trnint3b.c`, `trnint3c.c`, `trnlayers.c`), all
  seven of which use `AddVectoredExceptionHandler`. `trnblock.c` is the **terrain** hook.
  **No `trnhook*.dll` is built in `C:/gd/Rurik`** (gitignored); one exists in an unrelated
  terrain worktree and is not this hook. **A new `.c` must be written** on the int3 + VEH
  pattern — poke `int3`, `AddVectoredExceptionHandler`, emulate the overwritten `call rel32`
  by pushing the return and setting `Eip`, and count hits / matches / distinct ids so "never
  fired" is distinguishable from "never matched".
- Toolchain verified present 2026-08-20: MSVC `...\14.51.36231\bin\Hostx64\x86\cl.exe` under
  `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\` (note **18**, not 2022),
  Windows SDK `10.0.26100.0`; `build.ps1`'s glob resolves. Covered by CLAUDE.md carve-out
  (3); no third-party library is linked, so the second gate needs no new row.
- **A negative needs a positive control.** Before believing any silence, run
  `python toolkit/clientscan/trnhook/eipcontrol.py <pid>` — it arms whatever the process's
  own EIP was just doing, so it assumes nothing about the client. Silent there means
  breakpoints do not deliver in this client at all, and nothing measured that way says
  anything about `0x006055E0`. Five silent runs were once read as facts.
- **Rule out the reader first.** §2's flaky-read band and the failure table's aliasing-with-
  unread row exist because the cost of a false escalation is precisely this evening.

---

## 10. MECHANISM CORRECTIONS MADE WHILE WRITING THIS — read before the write-up

All four were found by disassembling the pinned 38797 image, and all four change how a
result reads. **All four were re-disassembled on 2026-08-20 and every byte still reads as
stated** — see §11's OBSERVED list for the instruction-level record.

**(1) `0x00605840` is the HISTORY APPENDER, not an apply.** It allocates a node
(`0x00605A50 call 0x604bb0`), links it to the old head (`mov [edx+4],[esi+4]`) and
push-fronts it (`0x00605A93 mov [esi+4],edx`), with a 2500 ms dedup at `0x0060593A`
(`cmp eax,0x9c4`). It never touches the ASYNC agent. **A shut fence therefore does not mean
the server's position was applied — it means no correction happens at all and the player's
prediction is left completely alone.** The capture field was named `shut:apply`, which
reads as the opposite and would have driven server work at a problem that is not there.
Renamed to `shut:append` / `world1:append` by C9, because that string is written into every
row permanently; `movesync` still reads the old spelling and prints a NOTE line counting
those rows, because stored rows are not rewritable. **And note what the rename does not
buy:** `shut:append` is still a counterfactual label on a state read — §5 item 1.

The caller's four outcomes, in full:

| | condition | what happens |
|---|---|---|
| `test-runs` | fence open, world != 1 | `0x0060601C call 0x6055e0`. **On NO SNAP the caller returns at `0x00606023` without appending**; on SNAP it calls `AgTrack::Clear` then the appender then the roster reseed |
| `world1:append` | fence open, world == 1 | `0x00606016 je 0x60610b` → appender, no test |
| `shut:append` | fence shut, world == 0 | `0x00606103 test edx,edx` → appender, no test |
| `shut:noop` | fence shut, world != 0 | `0x00606105 jne 0x606110` → returns, nothing |

**(2) Record `+0x08..+0x18` is a live last-appended cache, not unused.** It was labelled
NOT FOUND. The appender writes all five dwords at `0x00605A38`–`0x00605A4D` and reads
`+0x08`, `+0x0c`, `+0x10` back at `0x00605945`, `0x00605958`, `0x0060596B` for the dedup.
`AgTrack::Clear` zeroes **only** `+0x00` and `+0x04`, so when the fence is shut this tail is
**stale**, not live — a reader must not treat it as current. **It is also a free witness**:
C5 uses changes to it, and to `hist_head`, as positive evidence that the caller ran.

**(3) The first half's 100 u history veto cannot fire on world 0.** `0x006055E0` asserts
`[agent+0x24] == 0` at `0x0060561A`; the walk starts at `[esi+0x04]` (`0x006056AF`), i.e.
`hist_head`; the arm zeroes `hist_head` (`0x00605F4F`); the open-fence NO SNAP path returns
at `0x00606023` without appending, and the SNAP path calls `Clear` first. So `hist_head` is
identically 0 through every open stretch on world 0. **Consequence: whenever the fence is
open, the fallback always runs and the exits fully decide** — which is why H3 was retired
and why "above the cut, no snap" is no longer ambiguous between two hypotheses.

**(4) There are two exits above gate 1.** `0x00605634`–`0x00605641`:
`if (agent+0x48 != 0 && agent+0xC4 == 9) return 1` — NO SNAP, before gate 1 and before the
history walk. `0x00605643`–`0x0060567F`: if **both** `agent+0x78` and `agent+0x7C` equal the
float at `0x00948654` (`0x7F800000` = +inf = `AGENT_INVALID_POSITION`, named `INVALID_POS` at
**`movetap.py:524`** — the previous draft cited `:217`), return 1. Neither was in the
mechanism table. Both present on a capture as "above the cut, nothing snapped", i.e. as H1.
C7 and C8 record them at zero extra reads.

---

## 11. PROVENANCE OF EVERY NUMBER IN THIS DOCUMENT

**OBSERVED — disassembled from the pinned 38797 image, and re-read instruction by
instruction on 2026-08-20:** the caller's four outcomes and their sites; the fence's two
conditions at `0x00606002` (`cmp [eax+ecx*4],0`) / `0x00606013` (`cmp edx,1`) with
`0x0060601C call 0x6055e0` between them; `0x00605840` as the appender with its allocation,
link and push-front; the 2500 ms dedup at `0x0060593A` (`cmp eax,0x9c4`); record
`+0x08..+0x18` as a written-and-read cache; the ASYNC array at `AGBASE+0x14C` and count at
`AGBASE+0x154` (from `0x0060577A mov eax,[esi-0x80]` / `0x0060575E cmp eax,[esi-0x78]`,
where `esi` = AgTrack `this` = `AGBASE+0x1CC`); gate 1 at `0x006057D8 fld [0x946564]` /
`0x006057E1 fcom st(1)` comparing two `position_at` results; gates 2 and 3 at
`0x00605802 call 0x709e90` / `0x0060580A` / `0x0060581E`; `mov edi,1` at `0x00605822`; the
world-0 assert at `0x0060561A` and the history walk's start at `0x006056AF`; the arm at
`0x00605F10` writing `rec[+0x00]=1` / `rec[+0x04]=0` under `0x00605F3F` / `0x00605F43` /
`0x00605F4F`, its two call sites `0x005FC784` / `0x005FC8B9` (**`--xrefs` = exactly 2**) and
their input-only chain `0x00535380 → 0x008163A0 → 0x0081A8F0 / 0x0081ADB0 / 0x0081B650`;
`AgTrack::Clear` (`0x00605F70`) and its three call sites `0x005FCA94` / `0x005FDA78` /
`0x0060602E` (**`--xrefs` = exactly 3**); the `0x002C` handler `0x005FDA50` with zero direct
callers, `.rdata` word `0x00A52E20`, `MsgFormatRecv` descriptor `0x00A52E18`,
`cmds[0] = 0x2C`, count 4 matching `schema/messages.json`'s four fields; early-out A at
`0x00605634 cmp [ebx+0x48],0` / `0x0060563A cmp [ebx+0xc4],9` / `0x00605641 je 0x605683`;
early-out B at `0x00605643`–`0x0060567F` with `0x0060564F fld [0x948654]`; `+0x48` written
only by `0x005FE950` and its five call sites `0x005FEC7E` / `0x006002B5` / `0x00600B0A` /
`0x00601936` / `0x00602AD3`; the arm path `0x0081AA88 → 0x005FC6E0 → {0x00605F10,
0x00602660}` and `0x00602660`'s 1..8 switch writing `agent+0xB8/+0xBC/+0xC0`; `0x002B`'s
handler `0x005FD9D0` writing `+0xC4` via `0x00602990` at `0x00602A29`.

**MEASURED, read-only, n stated** (every figure in this block re-derived on 2026-08-20
except where marked): movetap corpus n = 5 captures / 4,115 samples — rates
**9.47–12.94 Hz**, `maxspeed` 288.0 u/s in **100.0%** of all five, largest single-axis
extent **4,684 u** and largest within-capture point-to-point separation **5,238 u**
(per-capture 5238.1 / 2939.1 / 3065.1 / 2338.3 / 3874.4 u; pooled 6,788 u — all lower
bounds, `+0x78` is stale between updates), `+0x48` non-zero in
**25.9 / 36.1 / 44.2 / 84.7 / 95.4 %** of samples, `+0x48` change rates
0.07 / 0.18 / 0.24 / 2.91 / 5.23 per second and changing on **25%** and **41%** of
consecutive samples in the two fast captures, and **0 of 4,115** samples in the `+0x48`
arrival-clamp branch; `+0x48` change rate vs s2c `0x0029` grant rate over 3 clock-aligned
pairs — **5.23 vs 5.61, 2.91 vs 3.16, 0.24 vs 0.22 /s, ratios 0.93 / 0.92 / 1.09**; client
c2s command rate 1.96–8.62 msgs/s in the same windows; **`0x002C` sent 0 times across 984
gamesrv captures**, with a positive control on the same scanner (`0x0029` in 76 files,
`0x002B` in 78); every `0x002B` we have sent carries mode 1, **n = 759**, whole vault, all
759 with trailing mode byte `01` (25 further opcode-43 rows in the vault are GAME_CMSG
`COMPASS_DRAW` on the other channel and are correctly excluded); `map_id: 148` in 12 of 12
recent gamesrv captures; snap corpus **24 snaps / 351.4 s of tapping = 0.068 snaps/s =
3.85% of 623 paired intervals**; navmesh `0x1B97D` = 58 planes / 6,120 trapezoids /
39,936 × 49,152 u; from the spawn, median ray over 72 headings 1,375 u and only 2 of 72
≥ 20 s, best 12,850 u @ 230°, continuously walkable to 12,800 u at 50 u granularity;
`sqrt(89600) = 299.3325909` (agrees with `studies/movement/FINDINGS.md:3126`);
`dhbuild` all-ok; `cage` **7 client(s), 0 in the wrong state**; `buildid` 38797 from the
getter at `0x004729E0` (16 callers); `select_run_exe` → the 38797 stamp directory, quoted
character for character in step 7; `test_movesync` **150 checks / floor 100**;
`movetap --selftest` **250 / floor 250**, `movesync --selftest` **80 / floor 80**; the suite
is **189** `test_*.py` files on disk (counted with `run_suite.find_tests()`, which discovers
from the DISK — never from this document or from CLAUDE.md); `grep -c gate_reach` = **31** in `movetap.py`, **24**
in `movesync.py`, `shut:apply` **0**, `gate1` 87, `early_out_a` 17, `shut:append` 51, the
`AGBASE+0x14C` read present — and the stale `gatefire-probe-plan-9c31de` worktree answers
15 / 8 / 0 to the first three. **NOT re-derived for this rewrite:** `contentids.preflight`
12/12 (needs both `Gw.dat` archives) and the suite's 621 s wall clock (measured 2026-08-14
over 96 files, 43 files ago).

**MEASURED BY SIMULATION, not from the client** (Monte-Carlo at f = 10.4 Hz, 45 s,
exponential dwells, n = 470 samples/cell): the old guard's blind band **[14.6%, 85.4%]**
from `2p(1-p) ≥ 0.25`; open 15 ms / shut 185 ms → 10.04 true transitions/s, 7.5% open,
`flips/n = 0.137`, old verdict "not aliased"; open 185 ms / shut 15 ms → 9.84 transitions/s,
0.147, also passes; `A` = **0.07** (5 s / 5 s), **0.88–0.93** (100 ms, 30 ms balanced),
**0.94–1.04** (15/185, 30/370, 185/15, 300/30 ms). Also arithmetic, not measurement: a
300 s FREE block yields **~20–23 snaps** at the corpus rate, and 0 of 23 rejects
"p ≥ 15% of snaps begin below the cut" at **2.4%**.

**FIXTURE-DRIVEN — real code, invented input.** Every number inside §6 blocks 1–11: the
counts, the percentages, the episode statistics, the poll rates, the `A` values, the jump
rows and the witness tallies. They are output of `movetap.fence_verdict`,
`movetap.gate1_verdict`, `movetap.print_episodes` and `movesync.print_fence` over hand-laid
state lists (block 7 over a seeded `random.Random(20260820)` exponential-dwell simulation),
at HEAD `e3dfb98`. **The shapes are a measurement of the code; the numbers are illustrations
and are not facts about the client.** §12's closing rule governs them.

**OBSERVED, from the vault, in §6:** blocks 12 and 13 only —
`movesync --wire-only --capture authsrv-20260819T145717-c1.jsonl`, and the same capture
paired with `movetap-20260819T145939.jsonl`. Both movetap captures predate the C6–C9 fields,
which is why both fence lanes refuse.

**UNVERIFIED:** the ~10 Hz post-change rate (arithmetic, n = 0); **the fence's runtime flip
rate, duty cycle and dwell distribution — n = 0, this run is their first measurement ever**;
the 80% / ≤ 2 episodes / A < 0.5 shape H1 requires; whether the early-outs' operands are the
SYNC record `movetap` resolves or its ASYNC twin; whether the client's map-146 instance lets
the player reach the open ground the terrain mesh shows; whether `0x00709990`'s call into the
LUT sqrt at `0x0046E870` yields exactly 299.3326 (the 89600.0 predicate is used precisely so
this does not have to be resolved, and the 295–305 u band is refused rather than classified).
⚠ **CORRECTED: this last clause used to read "whether `0x709990`'s LUT yields exactly
299.3326"**, which attributes the LUT to the wrong function and drops the leading zeros every
other address in this document carries. `0x00709990` is the path-length query
(`__cdecl(from, to, float range, int straightOnly)`, `FINDINGS.md:2842`); the LUT sqrt it
calls is `0x0046E870`, nine instructions over a 256-entry table at `0x0093CAC8`
(`FINDINGS.md:3118`). `gate1_verdict` prints both, correctly and separately — see §6 block 2.

**NOT FOUND:** any code recording the map id — **or the block label** — into a movetap
capture. `movetap` takes no `--note` and no `--block`, so the block ↔ stamp mapping is the
operator's to keep by hand (step 10). Also: any field in the existing five-capture corpus
co-located with the arm or the Clear, which is why the fence's dwell was unmeasurable before
this run. Also: any appender-witness printer in `movetap` — it is `movesync`'s.

**RETRACTED from previous drafts of this document:** *"I measured `+0x48` — a different
field, but driven by the same local-command edge"* and the inference *"2 of 5 captures would
already trip the bar, so expect WIGGLE to alias."* `+0x48` tracks our own server's grant
stream; the measurement was real, the attribution was wrong. What replaces it is in §1.
Also retracted: H3, and the refutation rule *"H3 dies if `hist_head` is 0"*, which was
unfalsifiable — `hist_head` is identically 0 on world 0 by construction. Also retracted,
2026-08-20: the `white` cell and the `ALIASING:` line (never printed), the `unread:* 0 0.0%`
row (structurally unprintable), the appender-witness section under `movetap` (wrong tool),
the `--block` / `--note` flags (never existed), `build 38797 (pinned)` as a startup line
(the gate is silent), the live `pos … sep … above … shut:append` line (never existed), and
*"the whole corpus spans at most 4,684 u corner to corner"* (that is a single-axis extent).

---

## 12. KNOWN LIMITS OF THE INSTRUMENT — accepted residue, 2026-08-20

C2-C9 landed after four adversarial rounds. Every round closed a narrower instance
of one defect class: **the code was right and the check was missing, so mutating a
PRINTED number passed the whole suite.** Round 4's reviewer was asked to call the
stop, and returned SHIP on a specific test: *no remaining unpinned printed number
can, on its own, flip whether H1 reads CONFIRMED or REFUTED, or flip whether
escalation trigger 2(b) fires.* The verdict logic and both refusal bars are pinned;
what follows is what is NOT, listed so a reader can tell a measured number from a
merely-printed one. **Anything below may be wrong in the output without any test
going red — do not transcribe these cells into a write-up without re-deriving them.**

1. ROUTING FACT THIS SHIP RESTS ON, so write it down rather than trusting it silently: `movesync.py` never reads `gate1`, `early_out_a` or `point_invalid` -- zero hits in the whole file, re-verified 2026-08-20 -- and PROBE-GATEFIRE.md routes it to 'the secondary cross-tab, on the FREE block only' while refutation rules 1, 2, 3 and 5 are all scored on STRAIGHT/WIGGLE blocks from the tap alone ('the primary answer comes from the tap alone'; 'Read the STRAIGHT blocks' files first. They carry the finding.'). Every residue below that lives in movesync is bounded by that fact. If a future round moves a decision into movesync -- e.g. scores rule 1 off its distribution, or teaches it to read gate1 -- RESIDUE 1 and RESIDUE 2 (list items 2 and 3 below; the list numbering and the RESIDUE numbering differ by one and always have) become live holes the same day and must be closed first. NOTE, 2026-08-20: one thing already crosses this line and is stated in §8 item 1 -- the APPENDER WITNESS lives in movesync only, so the partial answer to 'called but shut:noop' is unavailable from the tap alone. That is a routing consequence, not a new hole.

2. RESIDUE 1 (movesync, same defect class as the item just closed, one file over). `print_fence`'s distribution table binds exactly ONE row: `_dist_row(out, "shut:append")` is checked for count, percentage and bucket, and no other label is read back. Mutations that stay fully GREEN at 80/80 and 150/150: tripling the printed count and percentage of the `test-runs` row (invisible -- label right, bucket right, number silently wrong), and relabelling `test-runs` as `shut:append` in the print loop. `test-runs` is literally the label refutation rule 1 names. Two things keep it off the FIX-FIRST list and neither is a check: the routing fact above, and the fact that the same capture file's own movetap block prints the same species of number under a table that IS fully bound (five labels, count+percentage+label binding, plus a producer-domain control), so a mutation here contradicts a pinned number for the same data. The bucket column also makes a cross-bucket relabel print `test-runs`'s share beside bucket `reachable` under a `shut:append` label -- structurally self-revealing, but a mitigation, not an assertion. THE FIX IF A FIFTH ROUND HAPPENS: widen the existing `_dist_row` check from one label to every key in `counts`, plus movetap's producer-domain control pattern (`{REACH_TEST_RUNS} | set(REACH_FENCED)` covered by the fixture) -- roughly three checks, and it is the exact fix that was just applied to movetap's table.

3. RESIDUE 2 (movesync). The per-jump table's own row cells are unpinned: swapping the `fence BEFORE` and `fence AT` columns in the row print, and scaling the `step` column, are both GREEN. The three-way tally sentence beneath the table -- the one §6 block 11 quotes as the H1 shape -- is pinned WHOLE against a hand-computed string, and it is computed from the BEFORE column, so a swapped table visibly disagrees with a pinned aggregate. The table is illustration under a pinned claim; a reader who quotes individual rows rather than the tally would get the per-row story backwards.

4. RESIDUE 3 (movesync, already self-reported by that lane's fixer). `print_appender_witness`'s LIMIT 1 sentence prints four numbers nothing reads back: `Spacing p50 {p50:.3f}s, max {dmax:.3f}s; {far} of {len(dts)} judged pair(s) span 2.5s or more.` (movefence.py:510). `far` -> `len(dts)` and `p50` -> `max` are both GREEN. These qualify how strongly a ZERO in arm (a) reads. Arm (a)'s and arm (b)'s counts AND both denominators are pinned (`_WITNESS_FIELDS` covers them, and substituting `judged` for `reach_pairs` in either position is red), and arm (b) is the aliasing witness §6 block 11 actually reads for the polling-vs-hook decision.

5. RESIDUE 4 (movetap, PRIMARY block, and the largest single one). The 'not aliased' sentence in `fence_verdict` -- the branch that prints when A < 0.5, and the last line of §6 blocks 1, 4 and 6 -- has ALL FIVE of its printed cells unpinned: `flips`, `pairs`, `rate`, `A` and the open share. Substituting phi for A, n for pairs, flips+5 for flips, 2*rate for rate, and p over n for p over real samples are each GREEN. Why this is residue and not a stop: the DECISION is not in the number. The A >= 0.5 threshold is pinned (0.5 -> 5.0 is red, four FAILs), phi's denominator is pinned (`pairs` -> `n` is red), p's denominator is pinned (`n - unread` -> `n` is red, and the check names the exact 92.5%-behind-a-20%-flaky-read case), and in the REFUSED twin sentence -- §6 block 7, the one that fires at A >= 0.5 and says 'THIS is the outcome that earns the hook' -- both `pairs` and the open share ARE pinned. Arithmetically no substitution I could construct crosses the bar from inside this branch: A = phi / 2p(1-p) and 2p(1-p) <= 0.5, so A < 0.5 forces phi < 0.25. It misreports a magnitude into the write-up; it cannot flip escalation trigger 2(a) or refutation rule 3. THE FIX IF A FIFTH ROUND HAPPENS: the refusing twin is already pinned verbatim -- pin the non-refusing one the same way, one hand-computed sentence.

6. RESIDUE 5 (movetap). The `alias is None` sentence ('the fence never changed state, so there is no aliasing ratio to compute') has its `pairs` cell unpinned. That is the last line of §6 block 3, which is now the block this document names as H1's likeliest outcome -- see item 12.

7. RESIDUE 6 (movetap). Both REFUSAL sentences' own cells are unpinned -- the fence's `REFUSED: {unread} of {n} samples ({pct}%)` (§6 block 8) and gate 1's identically-shaped one (§6 block 9) can each be hard-wired to `0 of n (0%)` while still refusing. Both bars ARE pinned (4x -> 40x is red in both). The mitigation is redundancy rather than a check: the true unread count is printed one block above in each case, in a share table that IS bound cell by cell, including its unread row. A refusal whose own count reads 0 looks like a bug and invites an operator to override a categorical 'No share above is a fact about the client' -- that is the failure path, and it needs a person to ignore the instrument's stated verdict.

8. RESIDUE 7 (movetap). `print_episodes`' per-state MEDIAN cell is unpinned (printing the min in its place is GREEN). Everything else on that line is pinned cell by cell -- run count, min, the seconds axis including the historic (k-1)/hz off-by-one, censored, split, effective n, the real-sample total, both Nyquist thresholds, the UNRESOLVED line, and both printed rates. Low consequence by the document's own reasoning: §1 RETIRED the median criterion ('median contiguous shut-run >= 5 s') as unfalsifiable at a 30-40 s block length and replaced it with episode count and A, both of which are pinned; and the printer already refuses to quote a median when the majority of runs are censored (§6 blocks 3 and 6 show that refusal).

9. RESIDUE 8 (test_movesync.py, the other lane's file, both fixers reported it). The external per-section floor tables are stale in BOTH directions: MOVETAP_SECTIONS declares 7/7/8/26/11 where the sections execute 14/15/22/38/13, and MOVESYNC_SECTIONS declares 14/19/6/11 where they execute 20/24/6/15 (`test_movesync.py:207` and `:239`, re-verified 2026-08-20). Nothing is red -- a floor below a green run is legal -- but section 9 could shed 14 of its 22 checks and still be certified as having run. Bounded by the module totals, which are EXACT and were read off real green runs (movetap 158/158, movesync 80/80), so any net loss reddens; and movesync additionally carries current in-file `_floor`s (20/24/6/15). movetap has no in-file per-section floor, so for movetap the stale external table is the only per-section guard.

10. RESIDUE 9 -- **CLOSED 2026-08-20, and it undercounted.** It read: *"PROBE-GATEFIRE.md §6's quoted block has drifted from what the code now prints. Its ALIASING line reads `phi 0.011 over 558 usable pairs, p(open) 0.287, white 0.409, A = 0.026`; the code prints a prose sentence with a different shape and does not print `white` at all. Its fence table shows three labels and omits `world1:append` and `shut:noop` ... The block is explicitly labelled a RECONSTRUCTION, so this is drift rather than a false claim."* Both halves were correct and there were **three more**: the header was 2 lines where the code prints 3; the `unread:*  0  0.0%` row was structurally unprintable, not merely absent; the EPISODES block was wrong in nearly every particular (no poll-rate line, no effective-n line, one Nyquist threshold instead of two, wrong seconds axis, no censoring marker); and the whole APPENDER WITNESS section was attributed to `movetap`, which has no such printer. §6 was rewritten from real printer output on 2026-08-20 and every block in it is now pasted verbatim with a provenance label. **The lesson this item is kept for:** the block carried a RECONSTRUCTION label and was still wrong in five ways, because a label on a shape does not check the shape. What replaces the label is the sha256 pin at the top of §6.

11. PROCESS RESIDUE. Round 4 ran the affected tests against a tree carrying four other files' uncommitted work from prior rounds and from a parallel lane, so its 150-check green was a verdict on that tree at that moment, not on a merged state. **RE-RUN AFTER THE MERGE, 2026-08-20: `test_movesync.py` = 150 checks green on `e3dfb98`, clean tree, and all twelve per-section `executed N of a floor of M` lines land where item 9 predicts.** Coverage was **7 test files + 2 selftests**; `toolkit/run_suite.py` was NOT run in either pass (forbidden by both briefs), so this is affected-test coverage and not suite coverage. Name the count when it is reported.

12. NEW, 2026-08-20 (document and instrument, found while syncing §6 to the code). **Refutation rule 3 cannot be scored on the outcome H1 most likely produces.** `A` exists only where the fence changed state; a STRAIGHT block with zero transitions prints 'there is no aliasing ratio to compute' (§6 block 3) and rule 3 has nothing to test. The refusal is correct -- inventing an `A` from zero transitions would be worse -- but it means the aliasing check is silent exactly where H1 lives, and a 15 ms-per-second fence that is never once caught open would print `100.0% shut:append`, one censored episode, and no ratio. From that block alone it is indistinguishable from a genuinely shut fence. What is available instead: refutation rules 1 and 2 (both unaffected), and arm (b) of the appender witness in `movesync`, which needs the FREE block's pairing to be read at all. Recorded in §1 rule 3, §5's third added note, and §8 item 6. THE FIX IF A FIFTH ROUND HAPPENS: nothing in the code -- the printer is already right. This is a hole in the REFUTATION SET, and closing it means adding a rule that a zero-transition STRAIGHT block can fail.

**The rule this list exists to enforce:** a number in this document's sample outputs
is evidence only if a check binds it. Where a cell above is unpinned, the number is
an illustration of SHAPE, not a measurement — and §11's provenance tiers apply. **That
rule now has teeth it did not have before:** §6's blocks are pasted from real printer
runs and pinned to a source hash, so a drifted sentence is detectable by re-running the
command rather than by noticing prose.
