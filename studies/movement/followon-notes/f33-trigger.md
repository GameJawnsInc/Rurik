# F33 — the trigger condition for reconcile-on-answer

Recon note, written 2026-08-25. **No client was launched; no harness, no
`session.py`.** Everything below is static disassembly of the pinned pristine
build-38797 client plus arithmetic over existing vault captures.

Every claim carries a label:

- **OBSERVED** — measured in this session; the command that produced it is quoted.
- **SOURCED** — a doc or the binary says it and I checked the citation resolves.
- **UNVERIFIED** — reasoning. Nothing was measured.

Pinned client for every disassembly: `C:\gd\Rurik\vault\client\2026-07-29_221c13772c7a\Gw.exe`
(build 38797, verified PRISTINE by `pinned.py`, printed by every `codescan.py` run).

---

## VERDICT, up front

**The polyline hypothesis SURVIVES, but not in the form the lane brief states it,
and the corpus cannot confirm it to the standard a fix should be built on.**

1. The brief's geometric claim — *"mid-walk the lagging copy sits ON the
   player's own history polyline, inside the match radius, so the test returns
   no-snap no matter how large the euclidean sep"* — is **OBSERVED true at BOTH
   named non-snap cells**, literally and to two decimal places. R10's 505–522 u
   in-walk episode: `poly_d` **0.00–0.01 u** across all 28 samples, because the
   chain still holds nodes dated 2.1 s back sitting exactly where the copy now
   is. R9's ~312 u non-snap: `poly_d` **0.00 u** at sep 312.2 in the two samples
   where the instrument's 8-node window reached far enough to see (it collapses
   to a 115 ms window one sample later and reports a spurious 268.95 — §2.5(c)
   catches the artifact in the act).
2. The brief's mechanism for the walk-START asymmetry — *"at a walk start the
   copy is OFF the new polyline"* — is **right in its effect and incomplete in
   its reason**, and the missing half is in the binary, in one straight-line
   block (§1.4). At a walk start the local input path calls the arm
   `0x00605F10`, which **NULLS the chain head** (`0x00605F4F`), and then, seven
   instructions later, sets the destination through `0x00602A40` → the bake →
   the dispatch. So the copy is not merely off the new polyline: **there is
   barely a polyline at all**, and what little there is points the wrong way —
   `[destination → body-now]`, the leg **ahead**, while the stale copy lags
   **behind**. The arm is a no-op on an already-armed record
   (`0x00605F3F`/`0x00605F43`), so **only a walk start empties the chain**; a
   held-key walk never does. That single asymmetry is the whole trigger.
3. **"sep" IS the wrong variable — and "distance to the polyline" is the right
   variable one level too low.** `poly_d` is genuinely what the match test
   compares (§1.2), and it does explain both named non-snap cells. But it only
   decides anything on the instants the test is *evaluated*, and evaluation is
   itself conditional: *(a dispatch into `0x00605FC0` occurs)* AND
   *(`clientControlled` is set)*. Eleven seconds of 864 u separation passed
   harmlessly in R10 not because `poly_d` was small — it was 864.5 — but because
   nothing dispatched. Both conditions are event-scale; the movetap corpus
   samples at ~10–20 Hz and **cannot resolve either**. That gap I cannot close
   from captures.
4. So the sharpened statement of the trigger, at the confidence the evidence
   supports (**SUPPORTED, not OBSERVED**):
   > F33 fires when our answer's grant bake dispatches the desync test **into a
   > freshly-armed fence whose history chain the arm has just emptied**, with
   > separation above 299.33 u. An in-walk answer does not fire it because the
   > fence was already open, the arm was a no-op, the chain still holds nodes
   > running back along the leg, and the lagging copy is sitting on them — a
   > match, and all three gates are short-circuited.

   **The variable to instrument is therefore not `sep` and not `poly_d`. It is
   the shut→open fence transition** — equivalently, "was there a local player
   movement command between the last snap/Clear and this answer". `sep` only
   sets the magnitude of the warp once the trigger has fired.

**What the corpus can and cannot say, stated plainly.** No single measurable
variable separates snap from non-snap **at the sample level**: `poly_d` shifts
the odds by a factor of two and no more (§2.3), and a large part of even that
is contaminated by the 8-node truncation artifact (§2.5c). The evidence is
strong **per episode** — all three named cells come out right, in the mechanism's
own terms — and rests on 9 shipped-era snap events against 559 above-cut
non-snap samples. **I could not determine the trigger to the standard of a
decision rule from captures alone**; §4 names the one run that would.

**The single most valuable line in this note**, if only one survives: the
existing claim that the history polyline can never veto a snap for the player's
agent (`PROBE-GATEFIRE.md` §(3), the sentence that retired H3) is **REFUTED on
three independent grounds** in §1.3 — a third, fence-independent caller of the
appender that its xref list never had; the dispatch's own world-1 arm appending
*into* an open fence; and 26 consecutive capture samples showing `fence: open`
with a non-null head. The polyline is live, and it is the thing doing the
vetoing.

---

## 0. Two corrections owed before anything else

### 0.1 The brief names the wrong address for "the desync test"

**OBSERVED.**

```
$ python toolkit/clientscan/codescan.py --xrefs 0x00605AF0
0x00605AF0: 1 direct rel32 reference(s)     006056FD  call

$ python toolkit/clientscan/codescan.py --xrefs 0x00605FC0
0x00605FC0: 3 direct rel32 reference(s)     005FEBEB / 006022A1 / 00602BBD  call
```

- `0x00605AF0` is `seg_match`, the per-segment test. **One** caller.
- `0x00605FC0` is the **AgTrack dispatch** — the thing with three callers.
- The desync test proper (match half + three gates) is a third function the
  brief does not name: it starts at **`0x006055E0`** (`55 8B EC` / `sub esp,0x80`
  / the `0xBF4440` cookie load; `codescan --dis 0x006055E4` decodes
  mid-instruction and prints garbage). Match loop `0x00605643`–`0x00605751`,
  gate half `0x00605753`–`0x0060583D`. `FINDINGS.md:3643` already has the
  3-caller count on the right address.

### 0.2 A claim of mine died, and the control killed it

I first wrote that the two early-outs in `0x006055E0`'s prologue appear in no
document. Then I ran the grep I had only asserted. **False**:
`PROBE-GATEFIRE.md:79-80` tabulates them as EARLY-OUT A and B, and
`FINDINGS.md:2899-2917` decodes A and names `+0xC4 = facing` from the same
assert — with a detail I did not have, that `0x00602660`'s facing switch covers
only 1..8, so `facing == 9` is out of range and A's prior is low. Recorded here
because the lane brief demands positive controls on negatives and this is what
one catches.

---

## 1. Route A — the binary

### 1.1 `0x006055E0`'s shape (re-read this session, agrees with FINDINGS §2.2)

`__thiscall`, `ret 8`. `ecx = this` (AgTrack subsystem), `[ebp+8] = esi = state`
(the per-agent AgTrack record), `[ebp+0xc] = ebx = source` (the AgAgent).
Named by ArenaNet's own asserts — **OBSERVED**,
`asserts.py --at 0x006055E0 --span 600`:

```
0x0060560b  AgTrack:457   state->clientControlled
0x00605625  AgTrack:458   source.GetWorld() == WORLD_SYNC
0x00605768  Array:587     index < m_count
0x0060578c  AgTrack:519   asyncPtr
```

Prologue, two early "return 1 = no snap" exits (both already SOURCED, §0.2):

```
00605634  cmp dword [ebx+0x48], 0     ; the arrival tick
00605638  je   0x605643
0060563A  cmp dword [ebx+0xc4], 9     ; `facing`, 4-bit (AGENT_FACING_MASK = 0xF)
00605641  je   0x605683               ; -> mov eax,1
00605643  mov  eax,[ebx+0x78]         ; q  <- the SYNC copy's raw +0x78
```

**New this session, and it narrows early-out A usefully.** Which of the three
dispatch callers can reach A at all is decided by `+0x48`'s state at the moment
each one dispatches — **OBSERVED**, from the three disassemblies plus
`codescan --field 0x48 --in AgAgent` (33 instructions, 4 stores
`0x005FE531 / 0x005FEAD6 / 0x005FEB46 / 0x006021E6`, the last the only zeroing
store — the brief's census, reproduced exactly):

| dispatch caller | `+0x48` when it dispatches | can early-out A fire? |
|---|---|---|
| `0x005FEBEB` — grant bake tail | just **armed** at `0x005FEB46` | **yes**, iff `facing == 9` |
| `0x006022A1` — arrival primitive tail | just **cleared** at `0x006021E6` | **no** |
| `0x00602BBD` — SetPosition's unarmed arm | 0, that is why this arm was taken (`0x00602B44`) | **no** |

So A is not a general "an agent in motion is exempt" rule: it is reachable only
on the grant-bake route and only for one facing value. **UNVERIFIED as
behaviour** — `facing == 9` was `false` in every movetap sample I read
(`early_out_a` is recorded in the tapes; see §2).

### 1.2 The match half, and what "the polyline" actually is

The loop (re-disassembled `0x00605640`–`0x00605751`, agrees instruction for
instruction with `FINDINGS.md:2690`'s pseudocode, so this is **CORROBORATION**
not a new decode):

```
prev = state.position          (record +0x08..+0x14 — the SEED vertex)
node = state.history           (record +0x04 — head, NEWEST)
while node: if seg_match(q, node.position, prev, 100.0): lastMatch = node
            prev = node.position ; node = node.next
if lastMatch: lastMatch.next = NULL ; return 1      (0x00605746 — TRUNCATES)
else:         run the three gates                    (0x00605753)
```

`q` is the sync copy's `+0x78`. The radius is `100.0f` at `0x00946560`, effective
**99.919968 u** through the LUT sqrt; gate 1's cut is `300.0f` at `0x00946564`,
effective **299.332591 u**. Both **SOURCED**, `FINDINGS.md:3668`.

### 1.3 THE LOAD-BEARING FINDING — `PROBE-GATEFIRE.md` §(3) is REFUTED

`PROBE-GATEFIRE.md:1520-1526` argues:

> "the arm zeroes `hist_head` (`0x00605F4F`); the open-fence NO SNAP path returns
> at `0x00606023` without appending, and the SNAP path calls `Clear` first. So
> `hist_head` is identically 0 through every open stretch on world 0.
> **Consequence: whenever the fence is open, the fallback always runs and the
> exits fully decide.**"

If that held, the polyline could never veto anything for the player's agent and
this lane's hypothesis would be dead on arrival. **It does not hold.**

**(a) The appender has a THIRD caller the argument never considered. OBSERVED.**

```
$ python toolkit/clientscan/codescan.py --xrefs 0x00605840
0x00605840: 3 direct rel32 reference(s)
  00604B2A  call      <-- NOT in PROBE-GATEFIRE's provenance list
  00606037  call      (the dispatch's post-snap append)
  0060610B  call      (the dispatch's fence-shut / world-1 append)
```

`0x00604B2A` sits inside a per-agent sweep (`0x006048C0`–`0x00604B38`, stride
`0x1c` = the AgTrack record stride) that pulls each agent out of the **SYNC**
array (`0x00604B05 mov eax,[edi-0xe4]`, the same `AGBASE+0xE8` the dispatch
reaches at `0x006060D5`) and calls the recorder on it. It is outside the fence
entirely. `PROBE-GATEFIRE.md`'s own §11 provenance list names `0x00605840` "as
the appender" but lists no xref count for it — the two-caller model was assumed,
not measured.

**(b) The dispatch itself appends into an OPEN fence, on the world-1 arm.
OBSERVED**, re-disassembling `0x00605FC0`:

```
00606002  cmp dword [eax+ecx*4], 0   ; clientControlled
00606009  je   0x606103              ; SHUT  -> if world==0 append, else return
00606013  cmp edx, 1                 ; world
00606016  je   0x60610b              ; OPEN + world 1  ->  APPEND
0060601C  call 0x6055e0              ; OPEN + world 0  ->  the test
00606023  jne  0x606110              ; returned 1 -> return, no append
0060602E  call 0x605f70              ; returned 0 -> Clear ...
00606037  call 0x605840              ; ... then append
```

The AgTrack record is indexed by **agent id** (`0x00605FCE mov ebx,[edi+0x10]`),
so the sync copy and the drawn async body of the same agent **share one record
and one polyline**. Every async-side dispatch while the fence is open appends
the *drawn body's* position to the chain the sync copy is later tested against.
That is the polyline the brief is talking about, and it is fed continuously.

**(c) The capture data says so directly, and it is not marginal. OBSERVED.**
In R10's own tape `movetap-20260825T130918.jsonl`: **425 samples read
`fence_state: "open"`, and all 425 of them have a non-null `hist_head`** —
longest unbroken run 161 samples spanning 12.7 s, the head address stepping
forward as nodes are pushed. In `movetap-20260821T210639.jsonl`: **2,661 open
samples, 2,661 with a non-null head, in one continuous 197-second run.**
Under §(3) every one of those should have read zero.

**§(3) should be struck.** Its consequence — "whenever the fence is open the
exits fully decide" — is the sentence that retired H3, and it is not true.

### 1.4 THE MECHANISM, read off consecutive instructions

This is the part I would keep if only one paragraph survived. **OBSERVED**,
`codescan --dis 0x005FC8A0`, one straight-line block with no intervening branch,
inside the local-player-input function that is one of the arm's only two callers:

```
005FC8B0  push [ebp+8]                 ; agent id
005FC8B3  lea  ecx,[ebx+0x1cc]         ; the AgTrack subsystem
005FC8B9  call 0x605f10                ; THE ARM:  clientControlled := 1
                                       ;           hist_head       := 0   <-- CHAIN EMPTIED
005FC8CB  call 0x5ff540                ; (a test)
005FC8DE  call 0x602990                ; SetMoveSpeedAndFacing (+0x60, +0xC4)
005FC8ED  mov  [esi+0x50], eax
005FC8F0  call 0x602a40                ; THE SHARED AGENT-MOVE MUTATOR
```

`0x00602A40` reaches the destination bake `0x005FE950` at `0x00602AD3`
(**SOURCED**, `FINDINGS.md:2754` and `PROBE-GATEFIRE.md:226`), and the bake's tail is
`0x005FEBEB call 0x00605FC0` — the dispatch (**OBSERVED**, §0.1's xref list and
my own disassembly of `0x005FEB30`).

Two facts complete it:

- **The arm is a no-op on an already-armed record. OBSERVED**, and this is the
  whole asymmetry: `0x00605F3F cmp dword [eax+ecx*4],0 / 0x00605F43 jne 0x605f57`
  jumps past **both** the flag store and the head-null when the record is already
  armed. So a held-key walk that never lets the fence shut **never re-empties the
  chain**; only a shut→open transition does.
- **What the chain looks like immediately after an arm.** The seed vertex
  `state.position` is written by the recorder as the **destination** while the
  agent is moving (`0x006058D6 mov ecx,[esi+0x48] / test / je 0x605909` selecting
  `agent+0x88..+0x94`; **SOURCED**, `FINDINGS.md:2783`, and `FINDINGS.md:3711`
  states the resulting shape as REALFIX-O1: "the polyline is [current
  destination] → [current leg start] → [older leg starts] … LAG is on the
  polyline by construction; LEAD is not"), and this local path
  dispatches on the **async** array (`0x005FC8F0`; **SOURCED**,
  `FINDINGS.md:3277`), so the world-1 arm at `0x00606013` appends one node at the
  drawn body's current position. The polyline right after a walk start is
  therefore **`[destination → body-now]` — the leg AHEAD of the player.**

Put together, and this is the answer to the lane's question:

| | fence state at the answer | chain the test walks | copy's relation to it | outcome |
|---|---|---|---|---|
| **walk START** (shut→open) | just armed | `[destination → body-now]`, the leg **ahead** | copy lags **behind** ⇒ off it | fall through to gate 1 ⇒ **SNAP** above 299.33 u |
| **in-walk** (already open) | untouched, no re-null | nodes accumulated **back along the leg** | copy lags **onto its own trail** ⇒ within 99.92 u | **match**, gates short-circuited ⇒ **no snap at any sep** |
| **long stale stand** (shut) | shut, no dispatch | irrelevant — `0x00606009 je 0x606103`, the test is never reached | — | **no snap**, however large sep grows |

The third row is what lets 864.5 u of staleness accumulate; the first row is
what spends it. R10's own phrasing — *"the trigger looks like the walk-start
reconcile meeting an arriving answer, not any answer"* — is correct, and this is
why: **the walk start is the only thing that empties the chain.**

**Confidence: SUPPORTED, not OBSERVED.** Every instruction above is read; what
is not measured is that this sequence is what executed at any particular snap.
§4 says how to close that.

---

## 2. Route B — the corpus

### 2.1 Instrument, and the positive control that earns it

Snap detector: the drawn body teleports onto the copy — async displacement
≥ 100 u between consecutive samples at dt ≤ 0.15 s (≥ 667 u/s against a
288.0 u/s cap), `sep` ≥ 100 u before and < 40 u after and < 40 % of before.
Script: `scratchpad/f33score.py` (read-only; not committed).

**Positive control — it re-finds the arc's own named events, unprompted:**

| doc event | doc figure | this detector |
|---|---|---|
| R9 F33, "7 of 7" (§8.2a) | 7 snaps | **7** in `movetap-20260824T213933.jsonl` |
| R9 rep-1 mid-walk snap | 523.7 u at sep 555.3 | jump **523.7**, sep **555.3** |
| R9 cast-3 mid-cast snap | 365.5 u | jump **365.5** |
| R10 F33 walk-start snap (§8.3d) | 836.2 u, staleness 864.5 | jump **859.8**, sep **864.5** |
| R10 F34 parked warp (§8.3d) | 167.6 u backward | jump **167.6**, sep 167.6 → 0.00 |
| F35 wire-silent arrival teleport (§8.3f) | 177.4 u | jump **177.4** in `movetap-20260825T140548.jsonl` |

Six independently documented magnitudes reproduced to 0.1 u from the raw tapes.
The detector is not tuned to them.

### 2.2 Corpus split, and why it must be split

**`movetap-*` splits into two populations and they must not be pooled.**
The 2026-08-21/22 files carry above-cut samples in the tens of thousands and
snaps every 2–3 s; `CANCELWALK.md:8.2a` records that R8's session had max sep
280.8 u and F18's 265.8 u, so those files are a different server configuration
(the pre-zero-lead lead-grant era). Seven of their snaps are also **cross-plane**
(sync plane 0, async plane 18) at a fixed ~30 s cadence with near-identical
clocks in two separate files — a scripted portal/teleport loop, not F33. Only
the **2026-08-24/25 shipped-era captures** are scored as the primary corpus.

Files used, primary: `movetap-20260824T141620 / T163558 / T183544 / T213708 /
T213933`, `movetap-20260825T130918 / T140548`. n = 5,134 samples, 16 snaps,
**568 samples above the 299.333 u cut, 9 of them snaps**.

### 2.3 THE 2×2s

Unit of analysis: one movetap sample, restricted to `sep > 299.333` (the F33
regime). "SNAP" = a snap fires between this sample and the next.
Variable (ii) is computed from the tape's own `hist` array — the client's
history chain, read out of client memory by `movetap.py`, not reconstructed
from reports. Distance is point-to-polyline over `[hist_seed → node0 → node1 → …]`.

**SHIPPED-ERA, n = 568 above-cut samples**

| | poly < 99.92 u | poly ≥ 99.92 u |
|---|---|---|
| **SNAP** | 2 | 7 |
| **no-snap** | 207 | 352 |

| | sep > 299.33 | sep ≤ 299.33 |
|---|---|---|
| **SNAP** | 9 | 7 |
| **no-snap** | 559 | 4,559 |

| | fence open | fence shut |
|---|---|---|
| **SNAP** | 5 | 11 |
| **no-snap** | 2,450 | 2,668 |

| | chain present | chain empty (`hist_head == 0`) |
|---|---|---|
| **SNAP** | 3 | 6 |
| **no-snap** | 283 | 276 |

**EARLIER-CONFIG (do not pool), n = 20,396 above-cut samples**

| | poly < 99.92 u | poly ≥ 99.92 u | chain unusable |
|---|---|---|---|
| **SNAP** | 11 | 51 | 7 |
| **no-snap** | 6,730 | 8,424 | 5,173 |

### 2.4 Reading the tables honestly

**Neither (i) nor (ii) separates.** Snap rate given `poly < R` is 2/209 = 0.96 %;
given `poly ≥ R` it is 7/359 = 1.95 %. A **factor of two**, in the predicted
direction, on nine events. In the earlier corpus 0.18 % vs 0.53 %, factor three.
That is a nudge, not a decision rule, and I will not dress it as one.

**The (iii) fence table must not be read as a share.** `PROBE-GATEFIRE.md:1070`
already measured that the fence changes at or above movetap's own sample rate
("76 transitions over 623 usable pairs at 10.4 Hz is 1.02 of what INDEPENDENT
samples would give"), so per-sample shares are aliased. My 5-open / 11-shut
split for snaps is an aliased reading of a variable that flips inside one sample
interval, and as a share it says nothing.

**But LONG RUNS of the fence are not aliased, and those are readable.** A
141-consecutive-sample `shut` reading is not a sampling artifact of a variable
that flips every ~100 ms; it is a variable that did not flip for eleven seconds.
And the two R10 episodes separate cleanly on exactly that:

| R10 episode | samples | sep | fence, every sample | chain | outcome |
|---|---|---|---|---|---|
| in-walk, t 15.69–17.90 | 28 | 307–522 u | **open, 28/28** | 8 nodes reaching 2.1 s back; `poly_d` 0.00 | **no snap** |
| stale stand, t 84.61–95.56 | 141 | 312–864 u | **shut, 141/141** | `hist_head == 0`, 140/141 | 11 s of nothing, then **SNAP** in the 100 ms after the chain and target went live |

That is the §1.4 mechanism's own prediction, and it is what the two episodes do.
It is two episodes, so it is corroboration, not proof.

**The two SNAP ∩ `poly < R` shipped-era rows are almost certainly the snap's own
aftermath, not its precondition. OBSERVED, and then reasoned:**

```
movetap-20260824T213933  t=88.26  sep=365.5  hist_n=1  poly_d=0.00
movetap-20260825T130918  t=95.56  sep=864.5  hist_n=1  poly_d=0.00
```

Both are `hist_n == 1`, with that single node sitting **exactly** on the sync
copy, and both are the **first** sample in which `hist_head` goes non-null after
a long run of `hist_head == 0`. The snap path itself is `Clear` (nulls head) then
`append` (`0x0060602E` → `0x00606037`) — and `0x00606037` pushes the same
`source` the test just ran on, i.e. **the sync agent**. A one-node chain sitting
on the copy's own position is precisely and only what that pair leaves behind;
the walk-start chain predicted by §1.4 would instead be one node at the *drawn
body*, which is not what these rows show. **UNVERIFIED** — I cannot
prove ordering inside a 50 ms sample — but if those two are aftermath the
shipped-era (ii) table becomes **SNAP 0 / 7, no-snap 207 / 352**, a clean
separation on nine events. I am recording both readings rather than picking.

### 2.5 The three named cells, each got right

**(a) R10's in-walk 505–519 u NON-SNAP — the polyline explains it exactly.
OBSERVED**, `movetap-20260825T130918.jsonl`, t = 15.69–17.90 s, 28 consecutive
above-cut samples, `fence: open` on all 28, **no snap**. Row t = 16.45:

```
sync  = (-6227.98, -2435.32, 0)      async = (-5713.83, -2362.64, 0)   sep = 519.3
seed  = (-4973.09, -2257.92)  seed_at = 19124  (a FUTURE tick -> the destination)
nodes = t16461 (-5732.6,-2365.3)   <- the drawn body, now
        t14674 (-6242.2,-2437.3)   <- 1.77 s ago
        t14401 (-6242.2,-2437.3)
        t14384 (-6239.0,-2436.9)
        t14367 (-6235.8,-2436.4)
        t14349 (-6232.4,-2435.9)
        t14332 (-6229.2,-2435.5)
        t14315 (-6226.1,-2435.0)
polyline distance from the sync copy = 0.00 u   (0.00-0.01 across the episode)
```

The copy is standing on nodes the body laid down 1.8–2.1 s earlier. It is inside
the 99.92 u radius by 99.92 u of margin. **This is the brief's hypothesis,
measured, in the cell it was written for.** Bare sep (519.3, well above the cut)
predicts a snap here and is wrong; the polyline predicts no snap and is right.

**(b) R10's 864.5 u walk-START SNAP — the chain was EMPTY. OBSERVED**, same file,
t = 84.61–95.56 s: **141 consecutive above-cut samples, `fence: shut`, and
`hist_head == 0` with `hist_why: "empty:head-null"` on 140 of them.** Eleven
seconds at up to 864.5 u above the cut, and nothing snapped, because with a null
head `0x006056B8 test esi,esi / je 0x605751` walks straight to the gates and the
gates were never reached — no dispatch. Then, in two consecutive 50 ms samples:

```
t=95.51  sep=864.5  fence=shut  head=0          target=[inf,inf]
t=95.56  sep=864.5  fence=shut  head=499787760  target=VALID     <- our answer baked
t=95.66  sep= 24.2  fence=open  head=499787848                    <- SNAPPED
```

The destination arming (`target_invalid` False) and the chain going non-null are
the answer's grant bake landing; the snap is in the next sample. **Bare sep
cannot be the trigger** — sep was 864.5 for the whole eleven seconds and the
snap took the last 100 ms of it.

**(c) R9's ~312 u in-walk NON-SNAP — the instrument's 8-node cap is caught
faking a refutation, in one sample. OBSERVED**, `movetap-20260824T213933.jsonl`,
t = 123.86–124.72, 9 samples, `fence: open` on all 9, sep 299.7–312.2, no snap.
The whole episode with the chain's own time span printed:

```
t=123.76 sep=278.8  polyd=  0.00   8 nodes spanning  116 ms
t=123.86 sep=312.2  polyd=  0.00   8 nodes spanning 1183 ms   <- reaches the copy
t=123.96 sep=312.1  polyd=  0.00   8 nodes spanning 1217 ms   <- reaches the copy
t=124.11 sep=301.7  polyd=268.95   8 nodes spanning  115 ms   <- window collapsed
t=124.21 sep=301.2  polyd=268.66   8 nodes spanning  115 ms
t=124.31 sep=300.6  polyd=267.59   8 nodes spanning  117 ms
...
t=124.72 sep=299.7  polyd=262.86   8 nodes spanning  113 ms
```

**`poly_d` goes 0.00 → 268.95 in one 150 ms step while `sep` moves 312.1 → 301.7.**
No real geometry moves 269 u in 150 ms at a 288 u/s cap. What changed is the
*window*: `movetap.py`'s `HIST_MAX_NODES = 8` truncates the chain, and here the
recorder is pushing a node roughly every 16 ms — the player is walking with the
camera turning, so the movement command changes every frame and the
`0x0060593A` 2500 ms dedup never bites. From t = 124.11 the eight newest nodes
cover only the last 115 ms of a chain that two samples earlier demonstrably
reached all the way back onto the copy.

So this cell is **not** a refutation. Read at the samples where the instrument
could see far enough (t = 123.86, 123.96), the copy is **on the polyline at
`poly_d = 0.00` with sep 312.2** — the same shape as cell (a), and R9's own
"one in-walk grant at sep ~312 did not snap" is explained by the same mechanism.
Every `poly_d ≥ R` figure in §2.3's tables is an **upper bound**, and the
`poly ≥ R` column is contaminated by exactly this artifact — which is another
reason not to read the factor-of-two as real.

**Contrast worth keeping:** in cell (a) the 8-node window spans **2.1 s** (a
straight click leg, few command changes); at t = 124.11 it spans **0.115 s**. The
same cap means completely different reach depending on how the player is moving.
Any future scoring of "distance to the polyline" must raise `HIST_MAX_NODES` or
it is measuring the walking style, not the geometry.

---

## 3. What this means for REALFIX

1. **Our own answer is the trigger event, mechanically.** The grant bake
   `0x005FE950` ends in `0x005FEBEB call 0x00605FC0` — every `0x0029` we send is
   a dispatch, and a dispatch is the only way the desync test ever runs. "F33 is
   reconcile-on-answer" is now decoded, not inferred: the answer *is* the
   evaluation. **OBSERVED** from the call site.
2. **Grant cadence is doubly implicated.** The zero-lead policy grants only on
   c2s `0x003D`, so a long straight leg produces one grant at its start — one
   evaluation, at the moment the staleness is largest. More grants would mean
   more evaluations at *smaller* separations, each of which either matches or
   passes gate 1. That is an argument *for* `--resync`'s extra cadence that this
   arc has not made, and it is **UNVERIFIED**.
3. **`--resync` (REALFIX-P5) has a second, unrecorded mechanism.** Its payload is
   `0x002C`, whose handler `0x005FDA50` calls `AgTrack::Clear` (`0x005FDA78`)
   **first**. `Clear` zeroes both `clientControlled` and the history head
   (`0x00605FA7` / `0x00605FAE`). So a `0x002C` does not merely co-locate the
   copies — it **shuts the fence**, and the test cannot run again until local
   player input re-arms it. That strengthens the brief's own prediction that
   `--resync` zeroes F35, and extends it to F33. **SOURCED** (the Clear call site
   and its two stores are in `FINDINGS.md:3652` and I re-read both this session);
   the *behavioural* consequence is **UNVERIFIED** — `--resync` has never run.
4. **A cheap non-obvious lever exists and I am flagging it, not recommending it.**
   Early-out A returns "no snap" unconditionally when `+0x48 != 0 && facing == 9`,
   and `0x002B`'s setter `0x00602990` writes `facing` from the wire with no clamp
   (`0x00602A29`), and 9 passes the client's own `AGENT_FACING_MASK` assert.
   `FINDINGS.md:2915-2917` already prices this: the same setter also writes
   `moveSpeed`, the character stops turning, and suppressing the test means the
   client never reconciles at all. **Do not build on this without a registered
   run.** It is listed because it is the only server-reachable exit above gate 1.

---

## 4. What I could not determine, and the one run that would

**I could not determine F33's trigger to the standard of a decision rule.** The
blocker is structural, not effort:

- The desync test is **event-driven**. It runs when a dispatch happens into an
  open fence. Neither "a dispatch happened" nor "the fence was open at that
  instant" is observable by polling; `PROBE-GATEFIRE.md:1070` already measured
  the fence changing at or above movetap's sample rate, and the same is true of
  `hist_head`, which steps on almost every sample in an open stretch.
- So every cross-tab in §2.3 is a sample of a state, correlated with an event it
  did not observe. **`PROBE-GATEFIRE.md:738`'s own warning applies to this note
  verbatim**: "the caller reached X" is an inference and must be written as one.

**The run that settles it** is the one PROBE-GATEFIRE already specifies and has
never had: an `int3` at `0x00606002` on the `trnblock.c` pattern
(`toolkit/clientscan/trnhook/`), counting **every evaluation** instead of
sampling the state around it. Three fields at the trap would close this lane
outright: the fence value, `hist_head`, and the return of `0x006055E0`. With
those, "did the match veto or did gate 1 fire" stops being an inference.

**Two cheaper improvements, both to the existing instrument, both worth doing
before that run:**

1. **Raise `HIST_MAX_NODES` from 8.** §2.5(c) is undetermined solely because of
   it. Eight nodes is 115 ms of chain in the camera-turn regime.
2. **Drop `HIST_SEP_GATE = 250.0` for at least one run.** The chain is currently
   never read below 250 u, so the "does the copy stay on the polyline while it
   converges" question — the whole no-snap side of the hypothesis — is invisible
   in the regime where the fix has to work.

---

## 5. Provenance

**Commands run this session** (all read-only, against the pinned pristine
client): `codescan.py --xrefs` on `0x00605AF0`, `0x00605FC0`, `0x00605F70`,
`0x00605F10`, `0x00605840`; `codescan.py --dis` at `0x006055E4`, `0x00605640`,
`0x00605AF0`, `0x00605F10`, `0x00605FC0`, `0x005FEB30`, `0x00602380`,
`0x006029F0`, `0x00604AE0`; `codescan.py --field 0x48 --in AgAgent`,
`--field 0xc4 --in AgAgent`; `asserts.py --at` on `0x006055E0`, `0x006022F0`,
`0x00602990`.

**Captures read**: every file under `vault/captures/movetap/` — 32 files, of
which 6 are unusable here (the five 2026-08-19 tapes predate the `fence_state`
/ `hist` fields, and `movetap-20260821T123318.jsonl` holds zero sample rows).
26 files scored: 7 shipped-era, 19 earlier-config. Scored with
three throwaway read-only scripts in the session scratchpad —
`f33score.py`, `f33window.py`, `f33twobytwo.py`, `f33runs.py`. No gamesrv or
live capture was pooled with a movetap one.

**Nothing outside `studies/movement/followon-notes/` was modified.**
