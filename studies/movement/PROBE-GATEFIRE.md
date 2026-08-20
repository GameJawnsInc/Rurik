# PROBE-GATEFIRE — does the client ever *evaluate* the snap test?

**Status of this document:** procedure, not result. Nothing below has been run against a
client. Every address is build **38797**. Written 2026-08-20 against tree
`C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de`, revised the same day after an
adversarial review of the instrument.

**Route: POLLING, WITH CAVEATS THAT TRAVEL WITH THE OUTPUT.** The cheap route survives
review, but four of its printed numbers did not. The aliasing guard was structurally
blind in exactly the band this probe's leading hypothesis lives in; two headline shares
folded failed reads into real ones; one hypothesis was refuted by construction; and half
the instrument the sample outputs describe does not exist yet (**C1 has since
landed and is mutation-proven; C2-C9 have not**). §3 step 2 is now a
blocking change list, and §5 is a verbatim statement of what this instrument cannot see
that sits **before** the analysis, not after it.

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

`agent+0xC4` is the movement mode fed to `0x00602660`'s 1..8 switch, so **9 is outside the
normal range** and early-out A's prior is low: every `0x002B` our server has ever sent
carries mode 1 (n = 754, whole vault), and `0x002B`'s handler `0x005FD9D0` is what writes
`+0xC4` from the wire via `0x00602990` at `0x00602A29`. `agent+0x48` is non-zero in
**25.9 / 36.1 / 44.2 / 84.7 / 95.4 %** of samples across the five corpus captures
(n = 4,115), so A's *first* conjunct is satisfied most of the time. `+0xC4` lies inside
`AGENT_SPAN` (0xD0), which movetap already reads in one block — recording it costs **zero
extra reads**. Both early-outs are therefore checkable for free, and step 2 makes them so.

**But the whole test is fenced.** The caller `0x00605FC0` reaches it only when
`clientControlled` (AgTrack record+0x00) is non-zero (`0x00606002`) *and* the agent's world
!= 1 (`0x00606013`). `clientControlled` is one-shot: `AgTrack::Clear` (`0x00605F70`) zeroes
it, and only local player input re-arms it (`0x00605F10`). **CORROBORATED** against the
pinned image this round: the arm writes `rec[+0x00]=1` and `rec[+0x04]=0` only when
`rec[+0x00]==0` (`0x00605F3F` / `0x00605F43`); Clear zeroes both only when non-zero; the
arm's two call sites (`0x005FC784`, `0x005FC8B9`) sit in functions reached **only** from
the input chain `0x00535380` → `0x008163A0` (octant resolver, modes 1..8) →
`0x0081A8F0` / `0x0081ADB0` / `0x0081B650`.

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

**(b) The loopback fence is not the retail fence.** `AgTrack::Clear` has three call sites.
Two are ours to reason about (`0x005FCA94`, `0x0060602E`). The third, `0x005FDA78`, sits in
a function with **zero direct callers** and one `.rdata` word at `0x00A52E20` — it is the
dispatch of `MsgFormatRecv` descriptor `0x00A52E18`, `cmds[0] = 0x2C`, i.e. the
**GAME_SMSG `0x002C` handler** (`0x005FDA50`), which calls `AgTrack::Clear(msg.agentId)`
**unconditionally as its first act**. Our server has sent `0x002C` **zero times across
every gamesrv capture in the vault (89 files scanned)**. Retail's dominant *clearing* edge
is inert on loopback. Any duty cycle this run measures is a loopback duty cycle, and that
is a second incomparability on top of the town-vs-explorable one in §4. If the fence turns
out to be stuck **open**, this is the first explanation to reach for.

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

### The collision audit, done before the run because that is the point

- **H1 and H2 both predict "above the cut, no snap."** They are separated *only* by
  `gate_reach`, which is read every sample. ✅
- **Inside H2, "gate 1 emptied it" and "an early-out vetoed it" are separated** by the
  directly measured separation *plus* `+0x48` / `+0xC4` / `m_point`. All four are reads
  inside blocks movetap already fetches. That is why the ASYNC read and the `+0xC4`
  extraction are **required code changes and not niceties**. ✅
- **They are not mutually exclusive.** Each can hold over different stretches. **The
  analysis reports the joint table and elects no winner.** An output that prints one
  verdict is a design defect.
- **Residual collision, partially closed:** "the dispatch was never called" and "the
  dispatch was called but fenced" both look like nothing happening. Polling cannot fully
  separate them — but the appender witness (step 2, change C5) turns part of it into a
  **positive** observation for free, because `hist_head` and the `+0x08..+0x14` cache
  changing between two samples witnesses that the caller ran and took an append branch.
  What stays unobservable is the `shut:noop` branch, which writes nothing at all. See §5
  and §8.

### What would refute each — every one a positive observation, not an absence

1. **H1 dies** if `gate_reach` reads `test-runs` in ≥ 50% of real STRAIGHT-block samples.
   No comparison arm needed; H1 refutes on its own data.
2. **H1 dies a second way** if STRAIGHT and WIGGLE show the *same* fence duty cycle **and**
   the same episode rate — then the local-command edge is not what gates the test and the
   mechanism story is wrong. (Shares alone will not do it; see §5 item 4.)
3. **H1 dies a third way** if the STRAIGHT blocks report **A ≥ 0.5** after flaky-read
   contamination has been excluded. The shares are then an artefact of when we looked, and
   this is escalation trigger §2(a).
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
Episode count and A are falsifiable at this block length; a median is not, and step 13's
output refuses to quote one when the majority of runs are censored.

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
(§9).

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
  and it is printed with every result.
- **The hook has a bad record here and does not exist.** The hardware-breakpoint route
  delivered nothing across five silent runs and cost two commits of retracted
  conclusions. Only the int3 + VEH pattern in `trnhook/trnblock.c` has ever worked, and
  that is the **terrain** hook — **there is no hook source for `0x00606002`, and no
  `trnhook*.dll` on disk in either tree.** Escalating means writing a new `.c` and
  building it: its own evening. Also, each hit stalls a client whose desync is a race
  between two clocks — the instrument would perturb the phenomenon.

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
returns a confident number from old code.

### Step 1 — prove the tree, and prove the instrument is in it

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && git rev-parse --show-toplevel && git rev-list --count HEAD..main && grep -c gate_reach toolkit/clientscan/movetap.py
```

Healthy:

```
C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de
0
15
```

**The third number is the one that matters.** As of writing, `C:\gd\Rurik` (main) has
**zero** occurrences of `gate_reach` — the instrument exists only as uncommitted
working-tree changes in this worktree, and `git rev-list --count HEAD..main` returns 0 in
*both* directions, so a commit-count check does **not** catch it. A run from a normal
terminal at `C:\gd\Rurik` does not fail. It produces a clean-looking capture with no fence
field and reproduces the exact puzzle this run exists to solve.

### Step 2 — LAND THE CODE CHANGES, PROVE THEY LANDED, THEN COMMIT

**This step is a gate, not a formality.** As of writing, `movetap.py` contains **no `sep`,
no `gate1`, no ASYNC-array read at `AGBASE+0x14C`**, and still writes `shut:apply` /
`world1:apply`. Every sample output in steps 13 and 14 below describes code that does not
exist yet. **The run does not launch until the greps in this step answer.** If a change
cannot be landed, **delete its lane from the outputs** rather than shipping a procedure
that promises a number nothing computes.

Nine changes. C1–C5 are the fence lane and are the ones the review turned red; C6–C8 are
the gate-1 and early-out lanes; C9 is bookkeeping that goes into every stored row.

| | change | file / site | why |
|---|---|---|---|
| **C1** ✅ **DONE** (`movetap.fence_verdict`, mutation-proven: restoring `flips*4 >= n` turns the new skewed-fence selftest case RED) | **Replace the aliasing guard.** Over consecutive-sample pairs where **both** values are real (non-`unread:`): `phi = flips/pairs`; `p` = open share over real samples; `white = 2*p*(1-p)`; **`A = phi/white`**. **REFUSE when `A >= 0.5`.** Print `A` with `phi`, `p` and `pairs` beside it. | `movetap.fence_verdict` (`movetap.py:1044`) | `flips*4 >= n` is blind for duty cycles outside **[14.6%, 85.4%]** — under full aliasing consecutive samples are near-independent Bernoulli(p) and E[flips]/n → 2p(1-p), whose **maximum is 0.5**, so a lopsided fence **cannot** trip a 0.25 bar at any flip rate. Simulated at 10.4 Hz over 45 s with exponential dwells (n = 470/cell): open 15 ms / shut 185 ms = **10.04 true transitions/s**, utterly unresolvable, yields `flips/n = 0.137` and the old guard prints **"not aliased"** over a 7.5% / 92.5% split. That is **byte-for-byte the H1-CONFIRMED block** this document used to show as its own evidence. `A` is scale-free: simulated **0.07** for a genuinely slow fence (5 s / 5 s), **0.88–0.93** for balanced fast (100 ms, 30 ms), **0.94–1.04** for every lopsided fast case the old bar waved through (15/185, 30/370, 185/15, 300/30 ms). |
| **C2** | **Print run lengths, not just transition counts.** Per observed state, per block: number of contiguous runs, **median run length in samples AND seconds**, minimum run, and **how many runs are CENSORED by the block boundary**. **Refuse to quote a median when the majority of runs are censored.** Print the Nyquist bar in the output: at ~10.4 Hz a two-state signal needs ≥ 2 samples per half-cycle, so any state whose **minimum observed run is 1–2 samples is unresolved**. **Report the effective n as the number of EPISODES, never the number of samples.** | `movetap` summary | The prediction is stated in run lengths and the tool computed none. A 92.4% share over 564 samples with 3 transitions has an effective n of about **4**, not 564. |
| **C3** | **Fix the flip denominator.** Count a flip only when `last['gate_reach']` **and** `s['gate_reach']` are both non-`unread:`, and carry the count of usable consecutive pairs as the denominator. **Exclude `world1` ↔ `shut` transitions** from the flip count — or count `fence_state` transitions rather than `gate_reach` transitions. | `movetap.py:968` | As written, `real → unread → real` counts as two transitions. A 10% flake rate manufactures **0.20 flips/sample — 80% of the escalation bar** — below the 25% unread refusal at line 1035, whose printed consequence is *"THIS is the outcome that earns the hook"*. A world-index change is also not a fence flip. |
| **C4** | **Fix the sentinel hole in the jump table.** Make it a **three-way tally — reachable / fenced / unread-or-missing** — print all three, never fold the third into either, and **REFUSE the sentence when the third is ≥ 25% of the jump rows.** Rewrite the sentence so it does not assert an execution (see C9). | `movesync.py:602-606` | `tested = sum(... if be == "test-runs")` against `len(rows)` folds `be is None` (the first paired sample, or any `t` missing from `by_t` at line 566) **and** `be == "unread:<why>"` into *"The rest reached 0x00605840 … the HISTORY APPENDER"* — a could-not-read counted as a real fence-shut, in the headline. The population refusal at line 589 uses a **different denominator** over hundreds of samples and cannot protect nine jump rows. **This is the exact number §6 quotes as its H1 evidence.** |
| **C5** | **Add the appender witness.** Per block, from data already on disk: **(a)** how often `hist_head` **or** the `+0x08..+0x14` cache CHANGED between consecutive samples — a **positive** observation that the caller ran and took an append branch; **(b)** how often `hist_head` went to **0** while `gate_reach` was **unchanged** — a positive observation that an arm or a Clear ran **between** two samples, i.e. an aliasing detector independent of the state field itself. Print both limits in the output. | analyser | Costs nothing: `movetap` already stores `hist_head` and the full 28-byte `state_record` every sample. Limits to print: the appender **dedups at 2500 ms** (`0x0060593A cmp eax,0x9c4`), so silence under 2.5 s proves nothing; the `shut:noop` branch writes nothing and stays unobservable. |
| **C6** | **Read the ASYNC agent and compute `sep` and `gate1` from memory** — array at `AGBASE+0x14C`, count at `AGBASE+0x154` (from `0x0060577A` / `0x0060575E`, where `esi` = AgTrack `this` = `AGBASE+0x1CC`). Classify `above` / `below` / `undecided`, refusing the 295–305 u band. | `movetap` sample path | The only thing that separates "gate 1 emptied the population" from "an early-out vetoed it". §1's collision audit calls it required, and it does not exist. |
| **C7** | **Record `agent+0xC4`** and derive `early_out_a = (agent+0x48 != 0 and agent+0xC4 == 9)`. | `movetap` sample path | `+0xC4` is already inside `AGENT_SPAN` (0xD0) — **zero extra reads**. Fourth exit, above gate 1, absent from the mechanism table until today. Low prior, free to check, and if it ever fires it presents as H1. |
| **C8** | **Derive `point_invalid`** = both `agent+0x78` and `agent+0x7C` == `INVALID_POS` (`0x7F800000`). | `movetap` sample path | Fifth exit (`0x00605643`–`0x0060567F`). `movetap.py:217` already names the constant, and `A_POINT = 0x78` is already read. |
| **C9** | **Rename `shut:apply` → `shut:append`, `world1:apply` → `world1:append`,** and purge every printed sentence that asserts an execution nobody observed. `gate_reach` is a **counterfactual label on a state read**: it names the branch the caller **would** take if it ran. `movesync`'s *"The rest reached `0x00605840` — the HISTORY APPENDER"* asserts an execution the sampler never sees. | both files | §10(1): a shut fence does **not** mean the server's position was applied. `shut:apply` reads as the opposite and would have driven server work at a problem that is not there — and that string is written into every stored row permanently. |

**Tests, in the same commit.** C1's new guard needs a case in `test_movesync.py`'s
fence-verdict section that is **fabricated lopsided-aliased** (e.g. 7.5% open with
near-independent consecutive samples) and **must go red**. The old bar waves that case
through; a guard that cannot go red on the case it was written for is not a guard.

**Commit before the client launches.** A run whose instrument exists only as unsaved
working-tree state is one `git checkout` from being unreproducible.

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && git add -A && git commit -m "gatefire: the fence, its aliasing ratio, the two early-outs, and gate 1's real operands"
```

Then prove each lane landed — every one of these must be non-zero:

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && grep -c "gate_reach" toolkit/clientscan/movetap.py; grep -c "0x14c\|0x14C" toolkit/clientscan/movetap.py; grep -c "gate1" toolkit/clientscan/movetap.py; grep -c "early_out_a" toolkit/clientscan/movetap.py; grep -c "shut:append" toolkit/clientscan/movetap.py; grep -c "shut:apply" toolkit/clientscan/movetap.py
```

The last one must be **0**.

### Step 3 — the affected tests. Not the full suite.

The full suite is 96 files / ~10 min at four jobs and the owner runs it constantly. These
seven are the ones this run depends on.

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/test_movesync.py
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/test_pinned.py
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/test_buildid.py
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientpatch/test_cage.py
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientpatch/test_dhbuild.py
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/harness/test_harness.py
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/test_origin.py
```

Each ends `ALL CHECKS PASSED (N checks)` and exits 0.

| test | checks *before* the step-2 changes | a red one means |
|---|---|---|
| `test_movesync.py` | **110** (floor 61) | The analyser that turns the run into a number is broken — both bar arms, the fence sentinels, the shuffle control. **The run can be taken and still not be interpretable.** The step-2 changes add checks (C1's red-on-lopsided case, C2's censoring refusal, C4's three-way tally), so expect a *higher* number; **set the floor from that green run, never from a guess, and never above what one produces.** |
| `test_pinned.py` | 143 | The build gate `movetap` sits behind. `assert_build` may accept the wrong image, and every hardcoded RVA is then reading whatever else is mapped. |
| `test_buildid.py` | 42 | The build-number readout. **Step 5 would lie**, which is worse than not running it. |
| `test_cage.py` | 18 | **The launch gate itself. Do not launch anything.** This is the only thing between an `ours`-DH binary and the real service, and a broken gate is indistinguishable from a working one until it matters. (~1 min; it queries the Windows Firewall once per client.) |
| `test_dhbuild.py` | 48 | The whose-DH answer is untrustworthy, including its hostile-filename-order refusals. Every cage verdict is downstream of this. |
| `test_harness.py` | 156 | The driver: launch safety, capture tails, and `verdict_after_hold` — a client that dies during the hold must retract the PASS. That wiring shipped broken once and printed `RUN VERDICT: PASS` over a corpse. |
| `test_origin.py` | 32 | **Run this one first if anything else is red.** It answers "did the vault drift". A capture from another build landing in `captures/gamesrv/` turns three tests red with no code changed. If it names two build ids, the other reds are downstream of the vault, not of you. |

Then the two selftests, which need no client:

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/movetap.py --selftest
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/movesync.py --selftest
```

Both end `selftest passed`, exit 0.

> **NOT `gatetap.py` / `gatescore.py` / `studies/movement/gatefire.tsv`.** Those were
> specified during planning and never written. They do not exist. The instrument is
> `movetap.py` + `movesync.py`.

### Step 4 — the safety audits

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientpatch/dhbuild.py
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientpatch/cage.py
```

Healthy — verified today:

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
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/buildid.py --exe "C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe"
```

Healthy, exactly:

```
build 38797, from the getter at 0x004729E0 (16 callers)
```

Anything else — **especially `38833`** — stop. `[AGBASE+0x1CC]` on another build does not
error; it reads whatever else is mapped and returns a plausible `clientControlled`.

### Step 6 — is anyone else using the vault right now?

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && Get-ChildItem C:\gd\Rurik\vault\captures\gamesrv\*.jsonl | Sort-Object LastWriteTime | Select-Object -Last 3 Name,LastWriteTime; (Get-Process Gw -ErrorAction SilentlyContinue).Count
```

**This is not a hypothetical.** Four gamesrv captures were written between 08:45 and 09:40
today by a session this arc did not run. `movesync`'s `newest()` is
`sorted(glob, key=getmtime)[-1]` over the **shared** vault, and `session.py` has no
`--capture-root` CLI flag. If the timestamps are recent and not yours, **pass every path
explicitly in step 14** and do not use the bare form.

Note the client count. If it is not 0, the multi-instance mutex is NOPed on every build
here, so two clients can be up — which is why step 10 pins the pid.

---

## 4. THE RUN

### Step 7 — Terminal 1: start the stack

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/harness/session.py --keep-open --warn 5 --game-args "--map 146 --explorable"
```

**Do not pass `--exe`.** The default is build-pinned and *self-reporting*:
`select_run_exe()` filters by the build number read out of each image and picks the
directory named after that build's vault stamp — never by mtime. Passing `--exe`
suppresses the `client:` line entirely (it prints inside `if not a.exe:`), which is the
only place the build appears at launch. (`session.py --help` still says "default: newest
under vault/run". **That text is stale and is contradicted by the code three lines away.**
Do not act on it.)

**Do not pass `--enemy`.** It is off by default since 2026-08-12: the standing hostile
spawns 300 u from arrival against `AGGRO_RANGE` 1200 and killed the character 10 s into a
*movement* session. This is movement work.

**Never pass `--any-build`** to `movetap` at any point in this run.

#### Why map 146, and what it costs

The prior n = 24 corpus is **map 148, Ascalon City (Pre-Searing) — a town**
(`explorable = false`). I confirmed `map_id: 148` in all twelve recent gamesrv captures,
and the whole corpus spans at most **4,684 u** corner to corner (n = 5, 4,115 samples),
consistent with city walls. A 40 s straight leg needs 11,520 u at the 288.0 u/s that is
`maxspeed` in **100%** of those samples. **Not performable on 148.**

Map 146 (Lakeside County) loads the **same terrain file** — `file_id 0x1B97D`, row 7982,
crc `0xA0AE500A` — with `explorable = true`. So `contentids.preflight` is unaffected: I ran
it and got **12 of 12 map rows agree across both archives**, with 146 and 148 both on row
7982. Row 7982 covers the whole Pre-Searing region: navmesh extent **39,936 × 49,152 u**,
58 planes, 6,120 trapezoids.

**The cost, stated plainly, and it is now TWO costs.** (i) The fence shares from this run
are **not** directly comparable with the n = 24 corpus, because that was a town instance
and this is an explorable one, and the fence is per-agent and per-map. (ii) Separately and
independently: retail's dominant clearing edge, the GAME_SMSG `0x002C` handler's
unconditional `AgTrack::Clear`, is **inert on loopback** — our server has sent `0x002C`
zero times in the entire vault (§1(b)). The loopback fence is not the retail fence. Say
both in the write-up.

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

So: **run away from the city, in the direction where the tap's position readout shows both
coordinates falling.** Six thousand units out, at roughly (5969, 3481), the best local ray
opens to 17,850 u (62 s) — more room than this script needs.

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
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/movetap.py --pid NNNN --block A --note "map 146 explorable, gatefire" --seconds 45
```

Healthy start:

```
build 38797 (pinned)
reader capability 10.4 Hz (measured, 40 reads) -- BELOW the requested 50 Hz, so the floor is set from 10.4
polling agent 7 at 50 Hz for 45s -> C:\gd\Rurik\vault\captures\movetap\movetap-20260820T...jsonl
```

**UNVERIFIED: ~10 Hz.** The pre-change reader measured 9.47–12.94 Hz over the five existing
captures (n = 4,115). The step-2 changes add ~4 cross-process reads on ~14, so ~10 Hz is
arithmetic, n = 0. It cannot make the run fail spuriously — `calibrate()` runs the *new*
sample path 40 times before the run and sets the floor from what it measured.

Then, live, twice a second:

```
  [  12.4s] pos (    8140,    6134)  sep    1417.3 u  above     shut:append
  fence shut:append -> test-runs (raw 0 -> 1, armed 7) at t+14.10s
```

*(That line is of code C6 and C9 add. It does not exist before step 2.)*

### Step 11 — the in-game script, block by block

| # | block | `--seconds` | what you do | live signal that it is working |
|---|---|---|---|---|
| 1 | **A — instrument positive control** | 45 | Click distant open ground. Let the glide finish. Click again. Repeat. | The tap must print `-> test-runs` **at least twice**. **If it never prints `test-runs`, ABORT the session** — the record address is wrong and every `shut` after this is meaningless. |
| 2 | **B — null control** | 30 | Stand completely still. No keys, no clicks. | `sep` small and flat. This is the residual on a known-null stretch, and the only place the separation reading's noise floor can be measured. |
| 3 | **C1–C3 — STRAIGHT ×3** | **40 each** | (a) Click ground **far away**; (b) *immediately* hold **one** movement key in the opposite direction; (c) **do not change heading, do not click, do not release** for the whole block. Turn only if terrain forces it. | `sep` climbs monotonically past 1,000 u while `gate_reach` sits at `shut:append`. **That pair on screen is H1 happening in front of you.** |
| 4 | **D1–D3 — WIGGLE ×3** | 60 each | Move continuously and change heading about once a second — hold W, tap A/D alternately. Never stop, never click. | `test-runs` appears and the fence flickers. Expect the aliasing refusal here; see §1. |
| 5 | **FREE — accumulate snaps** | 300 | Play normally under our grants: click ground, walk, click again, cover distance. This is the block `movesync` scores. | Snaps appear as `sep` collapsing. |
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
median: **a run censored at both ends of a block is a lower bound, not a median**, and
step 13's output refuses to quote one as such.

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

`movesync` drops any pair outside ±0.25 s and hard-FAILs below 20 pairs, so **the tapping
window must sit strictly inside the gamesrv capture's span.** Start each tap *after* the
`body is in the map` verdict; Ctrl-C the last tap *before* closing the client.

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
> 6. THIS RUN IS NOT COMPARABLE WITH THE n = 24 CORPUS, TWICE OVER. That corpus is map 148, a town instance; this is map 146, explorable, and the fence is per-agent and per-map. Separately: in retail the dominant clearing edge is GAME_SMSG 0x002C, whose handler (0x005FDA50, dispatched from the descriptor at 0x00A52E18) calls AgTrack::Clear as its first act -- and our server has sent 0x002C zero times in the entire vault. The loopback fence is not the retail fence.
>
> 7. WHAT STAYS INVISIBLE EVEN WITH THE APPENDER WITNESS. hist_head and the +0x08..+0x14 cache changing is a positive observation that the caller ran an append branch, but the appender dedups at 2500 ms, so silence shorter than that proves nothing; and the shut:noop branch (fence shut, world != 0) writes nothing at all and is unobservable by any polling method. "The dispatch was never called" and "it was called and took shut:noop" remain the same reading. Only an int3 at 0x00606002 separates those two.
>
> 8. n = 1 SESSION IS n = 1, and the fence is per-agent: movetap polls only the ChCli-controlled agent. If the interesting snaps happen on a hero or a follower, nothing in this run looks there.

---

## 6. THE ANALYSIS

### Step 13 — the primary answer comes from the tap alone

Each `movetap` prints its own closing block. **This is the answer to the question this
probe exists to ask**, and it needs no capture, no clock alignment and no pairing:

```
THE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- a COUNTERFACTUAL
label on a state read, not an observation that the caller ran (see the caveat box):
  shut:append                          402   71.3%
  test-runs                            162   28.7%
  unread:*                               0    0.0%

  EPISODES (this is the effective n, not the sample count):
    shut:append   4 runs, median 96 samples (9.2 s), min 41 (3.9 s), 2 CENSORED by block
    test-runs     3 runs, median 47 samples (4.5 s), min 12 (1.2 s), 1 CENSORED by block
    Nyquist bar at 10.4 Hz: a run of 1-2 samples is UNRESOLVED, not short.

  ALIASING: phi 0.011 over 558 usable pairs, p(open) 0.287, white 0.409, A = 0.026.
  A < 0.5 -- the shares above are not an artifact of when we looked.

  APPENDER WITNESS (positive observations, from hist_head + the +0x08..+0x14 cache):
    append branch witnessed on 37 consecutive-sample pairs
    hist_head -> 0 with gate_reach UNCHANGED on 2 pairs (an arm or a Clear ran
      BETWEEN samples -- direct evidence of aliasing, independent of the state field)
    LIMITS: the appender dedups at 2500 ms (0x0060593A), so silence under 2.5 s
      proves nothing; the shut:noop branch writes nothing and stays unobservable.

GATE 1 (0x006057E1) ON ITS OWN OPERANDS:
  above                                489   86.7%
  below                                 61   10.8%
  undecided (295-305 u band, refused)   14    2.5%

THE TWO EARLY-OUTS ABOVE GATE 1:
  early_out_a (+0x48 != 0 && +0xC4 == 9)   0    0.0%
  point_invalid (m_point == +inf)          0    0.0%
```

*(Shape is a RECONSTRUCTION — the format is what step 2's changes are specified to print;
the run has not happened, and before step 2 lands, most of this block does not exist.)*

Read the STRAIGHT blocks' files first. **They carry the finding.** Quote their episode
counts, never their sample counts.

### Step 14 — the secondary cross-tab, on the FREE block only

Pass both paths explicitly. Do **not** use the bare form (step 6).

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/movesync.py --movetap "C:\gd\Rurik\vault\captures\movetap\movetap-<FREE block stamp>.jsonl" --capture "C:\gd\Rurik\vault\captures\gamesrv\authsrv-<stamp>-c1.jsonl"
```

It echoes `movetap:` and `capture:` on its first two lines. **Read them.** Then the fence
share (now printed *before* anything that can return early), then the fence either side of
every hard jump, as a **three-way** tally.

If you need the wire half alone — note the exact form, `--wire-only` is a flag and takes no
argument:

```powershell
cd C:/gd/Rurik/.claude/worktrees/gatefire-probe-plan-9c31de && python toolkit/clientscan/movesync.py --wire-only --capture "C:\gd\Rurik\vault\captures\gamesrv\authsrv-<stamp>-c1.jsonl"
```

### What each hypothesis literally looks like

**H1 (FENCE-CLOSED) confirmed** — the STRAIGHT files read like this while WIGGLE shows
`test-runs`:

```
  shut:append                          521   92.4%
  test-runs                             43    7.6%
  EPISODES: shut:append 2 runs, both CENSORED -- median REFUSED (majority censored);
            min run 188 samples (18.1 s). test-runs 1 run, 43 samples (4.1 s).
            Effective n for this block: 3 episodes.
  ALIASING: phi 0.005, p 0.076, white 0.140, A = 0.036. Not aliased.
GATE 1 ... above 498  88.3%
EARLY-OUTS ... early_out_a 0, point_invalid 0
```

and in `movesync`:

```
   the fence at each hard jump (n=9):
     server t     step   fence BEFORE            fence AT
         2.000    900.0   shut:append            test-runs
     jump rows: 1 REACHABLE (test-runs) / 8 FENCED (shut:*|world1:*) / 0 UNREAD-OR-MISSING.
     On the 8 fenced rows the caller WOULD have taken an append branch without any
     gate being evaluated -- an inference from a state read, not an observed call.
```

→ **The fence explains the 92.7%.** No exit is doing anything for most of the time.
**But read caveat 4 before writing that sentence**: this same block is what a 15 ms /
185 ms fence would print, and it is `A` — not the share — that tells the two apart.

**H2 (THE EXITS DECIDE) confirmed** — `test-runs` ~90% in *both* arms, no separation
between them, and either gate 1's distribution nearly all `below` outside of snaps, or a
surviving `above`-and-no-snap population in which an early-out is satisfied:

```
  test-runs                            508   90.1%
  shut:append                           56    9.9%
  EPISODES: test-runs 2 runs, both CENSORED; median REFUSED. Effective n: 3.
  ALIASING: A = 0.31. Not aliased.
GATE 1 ... below 511  90.6%   above 39  6.9%   undecided 14  2.5%
EARLY-OUTS ... early_out_a 0  0.0%   point_invalid 0  0.0%
```

→ **The 92.7% was an artefact of the wire proxy**, which over-stated separation. This is
this arc's most frequent failure mode (`warpscan`, the pre-splice `movesync`, the "20 ms
intervals"), and it would send the work back to the *pairing*, not forward to a hook.

If instead `above` **survives** at high share with `test-runs` and no snap, look at
`early_out_a` and `point_invalid` in the same rows **before** concluding anything about
gates 2 and 3. Either one firing there is a mechanism finding, not a puzzle.

**Neither of them** — e.g. snaps whose preceding sample reads `shut:*` with a real
separation collapse. Then look at `0x005FCAA0`, the gate-free `ResyncAllAsync`, whose three
callers include two that fire when the local command layer's own path test returns 0. That
is the arc's unexplained 12–59 s snaps, and this would be the first instrument that could
name them.

---

## 7. FAILURE TABLE

| symptom | most likely cause | the check that confirms it |
|---|---|---|
| Capture has no `gate_reach`; `movesync` prints `REFUSED: ... predates the field` | You ran from the wrong tree, or the step-2 changes were never committed | `grep -c gate_reach toolkit/clientscan/movetap.py` in the shell you actually used — must be non-zero (step 1) |
| Capture has `gate_reach` but no `sep` / `gate1` / `early_out_a` | Step 2's C6/C7 never landed; you are running the fence lane alone | The six greps at the end of step 2. If C6 cannot land, **delete the gate-1 lane from the outputs** rather than quoting a number nothing computed |
| Rows say `shut:apply`, not `shut:append` | C9 never landed. That string is written into every stored row permanently | `grep -c "shut:apply" toolkit/clientscan/movetap.py` must be **0** |
| `movetap` exits `FAIL: found TLS blocks but none resolved...` | Started before the client was in a map | `session.py` must have printed `[PASS] ... body is in the map` first (step 12) |
| `movesync` prints `FAIL: fewer than 20 pairs` | The tap window did not overlap the capture, **or** `newest()` picked a foreign file | Read the `movetap:` / `capture:` echo lines. Four foreign captures landed today 08:45–09:40 — re-run with explicit `--movetap`/`--capture` (step 6) |
| `movetap` FAILs on the sample floor | The reader stalled, or the block was too short | Its own line: `N samples over Xs = Y Hz` against `floor = elapsed * target_hz * 0.5`. `MIN_SAMPLES` 40 / `MIN_SPAN_SECONDS` 5 are absolute |
| Fence reads `shut:*` at 100% including blocks A and A′ | **Wrong record address** — not a finding | Blocks A/A′ must show `test-runs`. If not, the run is void. Cross-check `agtrack_count` against the agent-array size, and `agent_id_field` against `agent` |
| Many `unread:agent-id-mismatch` | `agent+0x10` disagrees with the id resolved through ChCli — we are holding the wrong object | The field is in every row; `movetap`'s denominator refusal fires at ≥ 25% |
| `REFUSED: A >= 0.5 ... aliased` in a **WIGGLE** block | Expected. The fence is flipping fast, which is what WIGGLE does | Compare against the STRAIGHT files. **Not an escalation trigger** |
| `REFUSED: A >= 0.5 ... aliased` in a **STRAIGHT** block | Polling cannot resolve this fence | **Escalate (§9)** — *but only after* the flaky-read exclusion. Read `pairs` (usable consecutive pairs) against `n`: with C3 landed, `unread` values cannot enter the flip count. If `pairs` is far below `n`, the read is flaky and the finding is about the reader, not the fence |
| `A` looks high but `unread:*` is 10–20% | The pre-C3 contamination band: `real → unread → real` counted as two flips, ~0.20 flips/sample, below the 25% unread refusal | Confirm C3 landed. This exact failure would have sent an evening to a hook DLL for a bad read |
| `movetap` prints `median REFUSED (majority censored)` | Correct behaviour, not a fault. The block was too short to contain a complete run | Quote the **minimum uncensored run** and the **episode count**; a censored run is a lower bound |
| `movesync` refuses the jump sentence: `>= 25% of jump rows unread-or-missing` | C4 working. The old code folded these into "the rest reached the appender" | Look at the three-way tally. A could-not-read is not a fence-shut |
| Client dies ~30 s in, `Assertion: found, Map.cpp(1762)` | Server and client archives disagree on the map | `contentids.preflight` runs automatically at launch. Green today (12/12). A running client holds `Gw.dat` open exclusively, so this cannot be checked afterwards |
| Client hangs at character select | `_play` **refused** rather than clicking at a coordinate of unknown meaning — the window was not 1936×1040 | Read the harness output for the refusal before assuming the client died. A previous session left a client at 716×1040 and put the Play fraction on **Delete**, six times |
| Client stuck on *Connecting to ArenaNet*, no sockets at all | Updater alive on a caged build | `dhbuild.py` must read `updater=killed` for `run/`. Rebuild with `make_custom_client.py`; **do not open the cage** |
| Everything green, capture lands in a directory `git status` cannot see | You used RUNBOOK's hand-rolled loop, whose `--vault vault/captures/gamesrv` is **relative** and lands in a phantom worktree vault | `Test-Path C:\gd\Rurik\.claude\worktrees\gatefire-probe-plan-9c31de\vault` must be **False**. `session.py` is not affected — it builds every path with `vault_path()` |
| Two clients running; the tap reads the wrong one | `gw_pids()[-1]`; the multi-instance mutex is NOPed on every build here | Always `--pid NNNN` from `session.py`'s own line (step 8) |

---

## 8. WHAT THIS RUN CANNOT ANSWER

The full statement is the caveat box in §5 and it is not repeated here. The five items
that constrain what the write-up may claim:

1. **"The dispatch was never called" vs "it was called but took `shut:noop`."** Polling
   samples state, not events. The appender witness (C5) turns *part* of this into a
   positive observation — `hist_head` or the `+0x08..+0x14` cache changing witnesses an
   append branch — but the `shut:noop` branch writes nothing at all, and the appender's
   2500 ms dedup (`0x0060593A`) means silence under 2.5 s proves nothing. Only a
   breakpoint at `0x00606002` closes the rest.
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

---

## 9. THE ESCALATION, if it is earned

Triggered **only** by §2(a) or §2(b). It is a second evening, and the prerequisite is real:

- No `trnhook*.dll` exists on disk in either tree (gitignored), and `trnblock.c` is the
  **terrain** hook. **A new `.c` must be written** for `0x00606002` / `0x0060580A` /
  `0x0060581E` on the int3 + VEH pattern — poke `int3`, `AddVectoredExceptionHandler`,
  emulate the overwritten `call rel32` by pushing the return and setting `Eip`, and count
  hits / matches / distinct ids so "never fired" is distinguishable from "never matched".
- Toolchain verified present today: MSVC `...\14.51.36231\bin\Hostx64\x86\cl.exe`, Windows
  SDK `10.0.26100.0`; `build.ps1`'s glob resolves. Covered by CLAUDE.md carve-out (3); no
  third-party library is linked, so the second gate needs no new row.
- **A negative needs a positive control.** Before believing any silence, run
  `python toolkit/clientscan/trnhook/eipcontrol.py <pid>` — it arms whatever the process's
  own EIP was just doing, so it assumes nothing about the client. Silent there means
  breakpoints do not deliver in this client at all, and nothing measured that way says
  anything about `0x006055E0`. Five silent runs were once read as facts.
- **Rule out the reader first.** §2's flaky-read band and the failure table's `A`-with-
  unread row exist because the cost of a false escalation is precisely this evening.

---

## 10. MECHANISM CORRECTIONS MADE WHILE WRITING THIS — read before the write-up

All four were found by disassembling the pinned 38797 image, and all four change how a
result reads.

**(1) `0x00605840` is the HISTORY APPENDER, not an apply.** It allocates a node
(`0x00605A50 call 0x604bb0`), links it to the old head (`mov [edx+4],[esi+4]`) and
push-fronts it (`0x00605A93 mov [esi+4],edx`), with a 2500 ms dedup at `0x0060593A`
(`cmp eax,0x9c4`). It never touches the ASYNC agent. **A shut fence therefore does not mean
the server's position was applied — it means no correction happens at all and the player's
prediction is left completely alone.** The capture field was named `shut:apply`, which
reads as the opposite and would have driven server work at a problem that is not there.
Renamed to `shut:append` / `world1:append` in step 2 (C9), because that string is written
into every row permanently. **And note what the rename does not buy:** `shut:append` is
still a counterfactual label on a state read — §5 item 1.

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
float at `0x00948654` (`0x7F800000` = +inf = `AGENT_INVALID_POSITION`, already named
`INVALID_POS` at `movetap.py:217`), return 1. Neither was in the mechanism table. Both
present on a capture as "above the cut, nothing snapped", i.e. as H1. C7 and C8 record them
at zero extra reads.

---

## 11. PROVENANCE OF EVERY NUMBER IN THIS DOCUMENT

**OBSERVED — disassembled from the pinned 38797 image:** the caller's four outcomes and
their sites; the fence's two conditions at `0x00606002` / `0x00606013`; `0x00605840` as the
appender with its allocation, link and push-front; the 2500 ms dedup at `0x0060593A`;
record `+0x08..+0x18` as a written-and-read cache; the ASYNC array at `AGBASE+0x14C` and
count at `AGBASE+0x154` (from `0x0060577A` / `0x0060575E`, where `esi` = AgTrack `this` =
`AGBASE+0x1CC`); gate 1 at `0x006057E1` comparing two `position_at` results; gates 2 and 3
at `0x0060580A` / `0x0060581E`; `mov edi,1` at `0x00605822`; the world-0 assert at
`0x0060561A` and the history walk's start at `0x006056AF`; the arm at `0x00605F10` writing
`rec[+0x00]=1` / `rec[+0x04]=0` under `0x00605F3F` / `0x00605F43` / `0x00605F4F`, its two
call sites `0x005FC784` / `0x005FC8B9` and their input-only chain
`0x00535380 → 0x008163A0 → 0x0081A8F0 / 0x0081ADB0 / 0x0081B650`; `AgTrack::Clear`
(`0x00605F70`) and its three call sites `0x005FCA94` / `0x005FDA78` / `0x0060602E`; the
`0x002C` handler `0x005FDA50` with zero direct callers, `.rdata` word `0x00A52E20`,
`MsgFormatRecv` descriptor `0x00A52E18`, `cmds[0] = 0x2C`, count 4 matching
`schema/messages.json`'s four fields; early-out A at `0x00605634`–`0x00605641`; early-out B
at `0x00605643`–`0x0060567F` with the constant at `0x00948654`; `+0x48` written only by
`0x005FE950` and its five call sites `0x005FEC7E` / `0x006002B5` / `0x00600B0A` /
`0x00601936` / `0x00602AD3`; the arm path `0x0081AA88 → 0x005FC6E0 → {0x00605F10,
0x00602660}` and `0x00602660`'s 1..8 switch writing `agent+0xB8/+0xBC/+0xC0`; `0x002B`'s
handler `0x005FD9D0` writing `+0xC4` via `0x00602990` at `0x00602A29`.

**MEASURED, read-only, n stated:** movetap corpus n = 5 captures / 4,115 samples — rates
**9.47–12.94 Hz**, `maxspeed` 288.0 u/s in 100%, max coordinate span 4,684 u, `+0x48`
non-zero in **25.9 / 36.1 / 44.2 / 84.7 / 95.4 %** of samples, `+0x48` change rates
0.07 / 0.18 / 0.24 / 2.91 / 5.23 per second and changing on **25%** and **41%** of
consecutive samples in the two fast captures, and **0 of 4,115** samples in the `+0x48`
arrival-clamp branch; `+0x48` change rate vs s2c `0x0029` grant rate over 3 clock-aligned
pairs — **5.23 vs 5.61, 2.91 vs 3.16, 0.24 vs 0.22 /s, ratios 0.93 / 0.92 / 1.09**; client
c2s command rate 1.96–8.62 msgs/s in the same windows; **`0x002C` sent 0 times across 89
gamesrv captures**; every `0x002B` we have sent carries mode 1, n = 754, whole vault;
`map_id: 148` in 12 of 12 recent gamesrv captures; snap corpus **24 snaps / 351.4 s of
tapping = 0.068 snaps/s = 3.85% of 623 paired intervals**; navmesh `0x1B97D` = 58 planes /
6,120 trapezoids / 39,936 × 49,152 u; from the spawn, median ray over 72 headings 1,375 u
and only 2 of 72 ≥ 20 s, best 12,850 u @ 230°, continuously walkable to 12,800 u at 50 u
granularity; `sqrt(89600) = 299.3325909`; `contentids.preflight` 12/12 with 146 and 148
both row 7982; `dhbuild` all-ok; `cage` 7/0; `buildid` 38797; `select_run_exe` → the 38797
stamp directory; `test_movesync` 110 checks / floor 61; `grep -c gate_reach` = 15 in
`movetap.py`, 5 in `movesync.py`, **0** occurrences of `sep`, `gate1` or `AGBASE+0x14C`.

**MEASURED BY SIMULATION, not from the client** (Monte-Carlo at f = 10.4 Hz, 45 s,
exponential dwells, n = 470 samples/cell): the old guard's blind band **[14.6%, 85.4%]**
from `2p(1-p) ≥ 0.25`; open 15 ms / shut 185 ms → 10.04 true transitions/s, 7.5% open,
`flips/n = 0.137`, old verdict "not aliased"; open 185 ms / shut 15 ms → 9.84 transitions/s,
0.147, also passes; `A` = **0.07** (5 s / 5 s), **0.88–0.93** (100 ms, 30 ms balanced),
**0.94–1.04** (15/185, 30/370, 185/15, 300/30 ms). Also arithmetic, not measurement: a
300 s FREE block yields **~20–23 snaps** at the corpus rate, and 0 of 23 rejects
"p ≥ 15% of snaps begin below the cut" at **2.4%**.

**UNVERIFIED:** the ~10 Hz post-change rate (arithmetic, n = 0); **the fence's runtime flip
rate, duty cycle and dwell distribution — n = 0, this run is their first measurement ever**;
the 80% / ≤ 2 episodes / A < 0.5 shape H1 requires; whether the early-outs' operands are the
SYNC record `movetap` resolves or its ASYNC twin; whether the client's map-146 instance lets
the player reach the open ground the terrain mesh shows; whether `0x709990`'s LUT yields
exactly 299.3326 (the 89600.0 predicate is used precisely so this does not have to be
resolved, and the 295–305 u band is refused rather than classified).

**NOT FOUND:** any code recording the map id into a movetap capture — which is why step 10
passes `--note`. Any field in the existing five-capture corpus co-located with the arm or
the Clear, which is why the fence's dwell was unmeasurable before this run.

**RETRACTED from the previous draft of this document:** *"I measured `+0x48` — a different
field, but driven by the same local-command edge"* and the inference *"2 of 5 captures would
already trip the bar, so expect WIGGLE to alias."* `+0x48` tracks our own server's grant
stream; the measurement was real, the attribution was wrong. What replaces it is in §1.
Also retracted: H3, and the refutation rule *"H3 dies if `hist_head` is 0"*, which was
unfalsifiable — `hist_head` is identically 0 on world 0 by construction.
