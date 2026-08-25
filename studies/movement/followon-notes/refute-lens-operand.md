# refute-lens-operand.md — attacking the 0x002C-disarms claim on THE OPERAND

Adversarial-skeptic recon. Angle: **verify the operand, not just the predicate.**
The predicate ("a write happens at 0x006021E6 / 0x0060216D") was already established.
This note asks **what value** goes in and **which object** it goes into.

Disassembly is against the pinned pristine client
`C:\gd\Rurik\vault\client\2026-07-29_221c13772c7a\Gw.exe` (build 38797, PRISTINE)
via `python toolkit/clientscan/codescan.py`. Captures are from `C:\gd\Rurik\vault\captures\`.
No client, harness or session.py was launched.

Tags: **OBSERVED** (I disassembled/measured it) · **SOURCED** (a doc/binary says it and I
checked the citation resolves) · **UNVERIFIED** (reasoning).

---

## 0. Verdict

The assigned fork was:

* **(a)** the arrival writes the **caller's supplied position** → a 0x002C lands the body
  at the resync point → claim holds.
* **(b)** the arrival writes the **agent's stale +0x9c** → a 0x002C would itself teleport
  the body to the stale point → `--resync` is a warp generator → invert the recommendation.

**The answer is (a). OBSERVED twice over — in the binary and, unexpectedly, in a
co-timed capture pair from today.** Option (b) is dead.

**But the claim does not get away clean.** Four corrections, in descending order of
how much they change what the next session should do:

| # | Correction | Effect on the claim |
|---|---|---|
| 1 | **"--resync … NEVER RUN" is false, and more importantly 0x002C is *already shipping*.** The default `--cast-stop=pin` sends 0x002C. 24 of them exist in the `ours` corpus. Six have co-timed movetap. | The claim's mechanism is no longer a hypothesis — it is **measured**, from a different flag. §5. |
| 2 | The arrival primitive **is** operand-neutral, and one of its seven call sites **does** pass +0x9c. That is F35. | Strengthens the physics story; kills the "arrival primitive == disarmer" shorthand. §4. |
| 3 | **+0x9c is `m_targetPoint`, not "syncPoint."** Both the brief and `authsrv.py`'s STOP_ECHO block misname it. | Cosmetic here, load-bearing next time someone reasons from the name. §6.1. |
| 4 | **The "simultaneously explains --stop-echo" leg is NOT supported.** A 0x0029 *does* overwrite the pending destination on the copy it hits. The two destinations were on **two different copies**, which movetap shows directly. | Refuted. §7. |

So: **claim CORE holds and is now measured; claim's --stop-echo COROLLARY is refuted.**

---

## 1. The calling convention, worked out exactly — OBSERVED

### `0x00602B20` SetPosition, `__thiscall(this, const Point4* p)`

```
00602B20  push ebp / mov ebp,esp / sub esp,0xc
00602B29  mov ebx, ecx                  ; ebx = this
00602B30  mov esi, dword ptr [ebp + 8]  ; arg1 = POINTER to a 16-byte point
00602B33  lea edi, [ebx + 0x78]         ; edi = &this->m_point
00602B44  cmp dword ptr [ebx + 0x48], 0
00602B57  je  0x602b7b                  ; +0x48 == 0 -> PARKED branch
; ---- ARMED branch: repack the point BY VALUE onto the stack ----
00602B59  sub esp, 0x10
00602B5C  mov ecx, esp
00602B5E  mov [ecx],     eax            ; from [esi]     (eax loaded 00602B55)
00602B63  mov [ecx+4],   eax            ; from [esi+4]
00602B69  mov [ecx+8],   eax            ; from [esi+8]
00602B6F  mov [ecx+0xc], eax            ; from [esi+0xc]
00602B72  mov ecx, ebx                  ; this
00602B74  call 0x6020b0
```

The 16-byte point reaches `0x006020B0` **by value as four stack dwords**, so inside the
callee they are `[ebp+8] [ebp+0xc] [ebp+0x10] [ebp+0x14]`, with `ecx = this`.
**Confirmed by the callee's own epilogue: `ret 0x10` at `0x006022AC`** — it pops exactly
those 16 bytes. There is no ambiguity left in the convention.

The **PARKED** branch (`0x00602B7B`) writes `this+0x78..+0x84` from the same
`[esi..esi+0xc]` and never touches `+0x48`, `+0x9c`, or the `+0x88..+0xa8` block.

### `0x006020B0` arrival primitive, `__thiscall(this, float x, float y, int z, int w)`

```
006020B0  push ebp / mov ebp,esp / sub esp,0x1c
006020C5  mov ebx, ecx                  ; ebx = this
006020FF  lea esi, [ebx + 0x78]         ; esi = &this->m_point
```

An entry assert (`0x006020B6`–`0x006020ED`, assert id `0x812`) fires when **both**
`[ebp+8]` and `[ebp+0xc]` equal the constant at `0x00948654` — i.e. "you may not
hard-set a position to the invalid sentinel." That the *arguments* are the thing tested
is itself confirmation that the argument is the position being installed.

---

## 2. What actually gets stored — OBSERVED, instruction by instruction

Straight-line `0x006020F6` → `0x006021E6`. **No branch target lands inside that range**
(the only jumps above it, `0x006020D0 jp 0x6020F4`, `0x006020DC jp 0x6020F6`,
`0x006020F2 jmp 0x6020F6`, all land at or before `0x006020F6`), so every row below
executes on every call that survives the assert.

| addr | instruction | value stored | where the value came from |
|---|---|---|---|
| `0x0060210E` | `fstp [ebx+0xb0]` | **0.0** | `fldz` @ `0x006020FD` |
| `0x00602117` | `fstp [ebx+0xb4]` | **0.0** | same |
| `0x00602132` | `mov [esi], eax` | **arg x** | `mov eax,[ebp+8]` @ `0x0060210B` |
| `0x0060213A` | `mov [esi+4], eax` | **arg y** | `mov eax,[ebp+0xc]` @ `0x00602134` |
| `0x00602143` | `mov [esi+8], eax` | **arg z** | `mov eax,[ebp+0x10]` @ `0x0060213D` |
| `0x0060214F` | `mov [esi+0xc], eax` | **arg w** | `mov eax,[ebp+0x14]` @ `0x00602146` |
| `0x00602155` | `mov [ebx+0x88], eax` | **+INF** | `[ebp-0x1c]` ← `fld [0x948654]` @ `0x0060211D` |
| `0x00602164` | `mov [ebx+0x8c], eax` | **+INF** | `[ebp-0x18]`, same constant |
| `0x0060216D` | `mov [ebx+0x9c], eax` | **+INF** | `[ebp-0x1c]`, same constant |
| `0x00602179` | `mov [ebx+0xa0], eax` | **+INF** | `[ebp-0x18]`, same constant |
| `0x0060217F` `0x00602194` `0x0060219E` | `mov [ebx+0x90/0x94/0x98], 0` | 0 | imm |
| `0x00602189` `0x006021A8` | `mov [ebx+0xa4/0xa8], 0` | 0 | imm |
| `0x006021D8` `0x006021DF` | `mov [ebx+0x3c/0x40], 0` | 0 | imm |
| `0x006021E6` | `mov [ebx+0x48], 0` | 0 | imm |

`esi = ebx+0x78`, so rows 3–6 are `this->m_point = arg`.

### The sentinel is +INF — OBSERVED, and it is the first positive control

`0x00948654` holds `00 00 80 7f` = `0x7F800000` = **`+inf` float32**
(read from the pinned PE with `pefile`, ImageBase `0x400000`).

That is the same `[inf, inf]` the F35 movetap rows show in `target` **after** the fire.
So this is not a guess about which field movetap was watching: the binary independently
predicts the exact sentinel the capture recorded.

### Fork resolved

`[ebx+0x9c]` appears exactly **once** in the straight-line body — `0x0060216D` — as the
**destination** of a store whose source is the +INF constant. It is **never read** before
`+0x78` is written. **Option (b) is impossible: `+0x9c` is not an input to this function
at all.**

---

## 3. The settle `0x005FF880` — it DOES move the body, and here the move is dead — OBSERVED

Called at `0x006020F8`, `this` only, before every write above.

```
005FF889  mov esi, ecx                  ; this
005FF890  lea edi, [esi + 0x78]
005FF89A  cmp dword ptr [esi + 0x48], 0
005FF8A8  je  0x5ff8e1                  ; PARKED -> skip the position write entirely
005FF8B1  call 0x5ffb40                 ; -> eax = a 16-byte point (dead-reckoned "now")
005FF8B9  mov [edi],     ecx            ; \
005FF8BE  mov [edi+4],   ecx            ;  > this->m_point = *eax
005FF8C4  mov [edi+8],   ecx            ; /
005FF8CE  mov [edi+0xc], eax
005FF8D9  call 0x603040                 ; spatial re-insert AT the settled point
005FF8E5..005FF929                      ; facing: +0xb8 / +0xbc / +0xc0
005FF932  mov [esi+0x58], eax           ; stamp the world clock
```

Answers to the two questions asked about it:

* **"fires only while a leg is armed"** — **OBSERVED and precise**: the *position* half is
  gated by `cmp [esi+0x48],0 / je` at `0x005FF89A`. The facing half (`+0x4c` gate at
  `0x005FF8E1`) and the `+0x58` clock stamp run unconditionally.
* **"does it move anything?"** — **YES, it writes `+0x78`.** It is the function movetap's
  own comment names as the reason `m_point` is event-driven ("it only moves when
  0x005FF880 runs").

**But inside `0x006020B0` that particular write is dead.** `0x00602132` overwrites `+0x78`
with the argument ~50 instructions later, unconditionally. What survives the settle is the
`0x00603040` re-insert, the facing block, and the `+0x58` stamp — none of which is a
position. **So the settle cannot smuggle a different point into the body.** The operand
answer is unaffected by it.

(The same settle is what `0x00602910` — a *speed* setter, `fldz/fcomp [ebp+8]` assert
`0x90d`, writes `+0x5c` — calls at `0x00602938`. Confirms the brief's identification.)

---

## 4. The primitive is operand-NEUTRAL — and one call site really does pass +0x9c

`--xrefs 0x006020B0` → **7 direct callers**: `0x0060032E`, `0x00600A91`, `0x00601817`,
`0x00601899`, `0x0060221E` (its own attached-agent recursion), `0x006025A6`,
`0x00602B74` (SetPosition's armed branch).

Two of them, disassembled:

* **`0x00602B74` (from a 0x002C)** passes the caller's point. §1.
* **`0x0060032E` (the arrival fire, inside the movement tick at `0x00600140`)** passes
  **`[ebx..ebx+0xc]` where `ebx = lea [esi+0x9c]`** (`0x00600267`; `ebx` is not
  reassigned between `0x00600267` and the repack at `0x00600311`, checked instruction by
  instruction). So **the arrival fire's operand IS `m_targetPoint`.**

The gate above it, OBSERVED:

```
006001A0  mov ecx, [esi+0x48] / test ecx,ecx / je      ; 0 = parked, nothing happens
006001EB  cmp edi, ebx                                 ; edi = world clock, ebx = +0x48
006001ED  jne 0x600379                                 ; fires only on the EXACT tick
```

**So option (b) is exactly what the arrival path does — from a different call site.**
The primitive writes whatever point you hand it. Calling `0x006020B0` "the arrival
teleport primitive that clears +0x48" is a shorthand that hides this; it is better read as
`HardSetPosition(p)`, which *also* tears down the leg.

This does not damage the claim — it sharpens it. Both a 0x002C and the arrival fire route
through the same teardown; the only difference is which point lands. **The 0x002C's point
is chosen by us; the arrival's is a destination we granted seconds ago.** That is the whole
of F35.

---

## 5. THE DECISIVE MEASUREMENT — 0x002C is already shipping, and it behaves as claimed

**The brief says `--resync` was "built, NEVER RUN". That is doubly wrong.** OBSERVED:

* `authsrv-20260820T182119-c1.jsonl` carries **52 `kind:"resync"` verdict rows and 18
  actual `opcode:44` sends**, several `"fired": true` at separations 127–215 u. `--resync`
  *has* been run, on 2026-08-20. (No movetap is co-timed with it — nothing in
  `vault/captures/movetap/` is dated 20260820 — so that run has wire evidence only.)
* Far more importantly: **the shipped default already sends 0x002C.** Both of today's
  captures carry sends labelled
  `"CAST-STOP PIN 0x002C at (…) plane 0 -- reckoned [cancelwalk R10]"`.

Wire census over all **1,167** `ours` captures: **0x002C sent 24 times in 3 captures;
0x0029 sent 4,828 times in 134 captures.** The 0x0029 count is the positive control — the
same scan finds a message I already know we send in bulk, so the 0x002C count is a real
count and not a broken filter.

**Six of those 24 have co-timed movetap.** Correlating on `wall_unix` (movetap's `t` *is*
`wall_unix`), taking the last sample strictly before the send and the first at/after it:

| send `wall_unix` | `stop` (+0x48 SYNC) before | `async_stop` before | **d SYNC** | **d ASYNC (rendered)** | `stop` after | `async_stop` after | land err vs payload |
|---|---|---|---|---|---|---|---|
| …81169.976 | 52911 | 53859 | 517.61 u | **9.86 u** | **0** | **0** | 0.005 u |
| …81194.417 | 76963 | 77726 | 14.40 u | 23.33 u | 76963 | 77726 | 2.104 u ¹ |
| …77771.565 | 23805 | 25773 | 229.14 u | **10.56 u** | **0** | **0** | 0.006 u |
| …77780.858 | 0 | 34760 | 278.83 u | **18.48 u** | **0** | **0** | 0.004 u |
| …77790.101 | 0 | 44267 | 162.93 u | **12.59 u** | **0** | **0** | 0.005 u |
| …77798.893 | 0 | 54304 | 100.44 u | **6.73 u** | **0** | **0** | 0.004 u |

¹ that row's "after" sample is 3 ms after the send — the client had not processed it yet.
The next sample shows the same 0-stop, 0-astop, `[inf,inf]`, land-err-0.36 u shape.

Worked detail for the first row (`movetap-20260825T140548.jsonl`, `t` shown relative to
the send at `wall_unix 1787681169.9763`, payload `2c000100000083669fc535e418c50000`):

```
dt=-0.110  sync=-5645.43,-2402.11  async=-5134.47,-2443.53  stop=52911 astop=53859  target=[-5148.8,-2442.4]  tinv=False
dt=-0.027  sync=-5616.73,-2404.44  async=-5110.64,-2445.47  stop=52911 astop=53859  target=[-5148.8,-2442.4]  tinv=False
dt=+0.053  sync=-5100.81,-2446.26  async=-5100.81,-2446.26  stop=0     astop=0      target=[ inf , inf ]      tinv=True
```

Everything the claim predicts, in one 80 ms step:

1. **The operand is the packet's point.** Both copies land on it to **0.005 u**.
   Nothing anywhere near the pending `target` (-5148.8, -2442.4) — the body ended
   **48 u short of it**, so the leg did **not** complete; it was cancelled.
2. **+0x48 is cleared on BOTH copies** — `0x006021E6`, reached twice because the handler
   `0x005FDA50` SetPositions the sync array (`0x005FDAE5`, `this = [[esi+0xe8]+id*4]`) and
   the async array (`0x005FDB49`, `this = [[esi+0x14c]+id*4]`).
3. **`target` (+0x9c) → `[inf, inf]`** — `0x0060216D` storing `0x7F800000`. Second positive
   control: the binary predicted this sentinel before I looked at the capture.
4. **The rendered body did not warp.** `d ASYNC` is 6.73–23.33 u across all six, i.e.
   *inside* the ordinary per-sample glide of ~23.3–23.9 u that the same rows show
   immediately before. The 100–518 u figures are the **SYNC** copy — invisible.

**A pending far arrival was disarmed by a 0x002C, in ordinary play, six times, with no
visible warp. That is the claim's core, OBSERVED, not argued.**

### The `this`-pointer trap, closed

codescan's own footer warns that a field reached through a **biased `this`** is invisible
to `--field`. That warning applies here and I checked it, because if `0x00602B20` were
called with `this = agent+0xe8` then its `+0x48` would be a different field from the one
the grant bake arms and the whole claim collapses. It is not:

```
005FDAA2  mov eax, dword ptr [esi + 0xe8]   ; the SYNC ARRAY BASE
005FDAA8  mov eax, dword ptr [eax + ecx*4]  ; dereferenced -> a real AgAgent*
005FDACB  mov ecx, dword ptr [ebp + 8]      ; that pointer becomes `this`
005FDAE5  call 0x602b20
```

`[esi+0xe8]` is an **array of pointers**, not an embedded subobject. Same shape at
`0x005FDB09`/`0x005FDB0F` for `[esi+0x14c]`. `this` is unbiased. (`movetap.py` agrees
independently: `OFF_SYNC_ARRAY = 0xE8`, `OFF_ASYNC_ARRAY = 0x14C`, cited to
`0x005FD8CE` / `0x0060577A`.)

### Field census, verifying the brief — OBSERVED

`--field 0x48 --in AgAgent` (`0x005FE0C3..0x00602CE2`, 70 assert sites): 33 instructions,
**exactly 4 stores** — `0x005FE531`, `0x005FEAD6`, `0x005FEB46`, `0x006021E6`. **The
brief's census is correct.**

`--field 0x9c --in AgAgent`: 21 instructions, **5 stores** — `0x005FE507`, `0x005FEC52`
(parent→attached-agent propagation), `0x0060060A` (a false positive: absolute address
`0x9C`, no base register, and the tool flags it), `0x0060216D`, **`0x00602AB0`**.
That last one is **not in the brief** and it matters — see §7.

---

## 6. Corrections to names and to `authsrv.py`'s own doc block

### 6.1 `+0x9c` is `m_targetPoint`, not "syncPoint" — SOURCED, and the citation resolves

`toolkit/clientscan/movetap.py:459-465`, keyed to ArenaNet's own asserts:

```
A_STOP    = 0x48   # m_timeStopMovement, absolute ms, 0 = not moving
A_SEGMENT = 0x88   # m_segmentPoint (assert AgAgent:1143)
A_TARGET  = 0x9C   # m_targetPoint  (assert AgAgent:1144) -- the landing point
```

Both the orchestrator's brief ("writes +0x9c (syncPoint)") and `authsrv.py`'s STOP_ECHO
block ("0x0029 stores its point into the agent's syncPoint at +0x9c") use **"syncPoint"**,
which collides with the *entirely separate* SYNC-vs-ASYNC copy distinction that the
`--resync` doc block in the same file spends a paragraph on. `+0x9c` exists on **both**
copies. **Stop calling it syncPoint.**

The layout, OBSERVED from the setter at `0x00602A82`–`0x00602ACD` and the initialiser at
`0x005FE4DF`–`0x005FE52B`: `+0x88..+0x94` = `m_segmentPoint`, `+0x98` = a scalar,
`+0x9c..+0xa8` = `m_targetPoint`. `0x005FE534`–`0x005FE56C` compares the two and sets
flag `0x40000` in `+0x20` when they differ — the "is moving" test. `0x006020B0` setting
both pairs to `(INF, INF)` therefore leaves a *consistent* "no leg" state, not garbage.

### 6.2 "0x0029 stores its point into +0x9c" needs a hop — OBSERVED

The **grant bake** — `0x005FE950`, the function holding both arm sites `0x005FEAD6` and
`0x005FEB46` — writes the destination into **`+0x88..+0x94` only** (`0x005FEAE3`,
`0x005FEAF2`, `0x005FEAFB`, `0x005FEB07`). It **never writes `+0x9c`.** The `+0x9c` write
on the grant path is one frame up, at **`0x00602AB0`**, in the setter that then calls the
bake at `0x00602AD3`. `movetap.py:15-16` already describes this correctly ("point into
BOTH m_segmentPoint (+0x88) and m_targetPoint (+0x9C), and calls 0x005FE950").

### 6.3 `authsrv.py`'s "no snap" is a claim about the *detector*, not the *position*

The `--resync` block says a 0x002C leaves "no snap" because `AgTrack::Clear`
(`0x005FDA78`, and it is genuinely **first**, before both SetPositions — OBSERVED) zeroes
`clientControlled` so the three-gate desync test is skipped (**SOURCED** to `0x00605FA7` /
`0x00606002`; I verified the call ordering, not the flag write). True and useful — but it
says nothing about the position write itself, which is an unconditional discontinuity of
whatever size the payload implies. The same block is honest about this two paragraphs
later ("A SetPosition to the client's last report **yanks the RENDERED copy backwards** by
however far the client has walked since that report"). **Both sentences are in the same
doc block and they read as contradictory.** They are not: no *reseed*, but a real jump.

---

## 7. The "--stop-echo" corollary is REFUTED

The claim's second leg: 0x0029 "can only ARM or RE-ARM … never disarm", and this
"explains why the 2026-08-19 --stop-echo run saw the echo ADD a second destination rather
than overwrite the pending one."

**It does not explain it, because re-arm is not addition.** OBSERVED: the leg state is a
set of plain scalar fields with single-valued stores —

* `0x00602AB0` overwrites `+0x9c` (`m_targetPoint`) with the new point;
* `0x005FEAE3` overwrites `+0x88` (`m_segmentPoint`);
* `0x005FEAD6` / `0x005FEB46` overwrite `+0x48` (`m_timeStopMovement`).

A second 0x0029 to the same agent object **replaces** the pending destination. There is
nowhere for a "second destination" to accumulate. `authsrv.py`'s own STOP_ECHO block says
as much in passing — "armed until it fires or **until a newer grant overwrites it**" — and
then, four lines earlier, asserts the opposite. The census in §5 shows why the "no clear
anywhere except that arrival" sentence in that block is wrong as written: `0x00602AB0` is a
non-arrival writer of `+0x9c`.

**The two destinations were on two different copies, and movetap shows it directly.**
In the six rows of §5 the sync and async arrival ticks are **independent values**:

```
stop=52911 astop=53859      stop=23805 astop=25773
stop=0     astop=34760      stop=0     astop=44267      stop=0 astop=54304
```

In **three of six** the SYNC copy was parked (`stop = 0`) while the ASYNC copy was armed.
Two copies, two legs, two destinations — and `authsrv.py`'s `--resync` block independently
records that **0x0029 is SYNC-ONLY** while 0x002C "is the one catalogued primitive that
reaches BOTH copies ungated."

That is a complete, simpler explanation of "the character teleported to the bridge anyway
and then walked back toward the echo point," and **it does not use the arm/disarm asymmetry
at all**. The corollary should be dropped or re-derived; it is currently a second story
that happens to fit, presented as corroboration.

---

## 8. What this does and does NOT license about `--resync`

**Does:** the *mechanism* is confirmed and now measured. A 0x002C disarms `+0x48` on both
copies, stomps `m_targetPoint` to the invalid sentinel, and installs the payload point.
`--resync` would therefore zero F35's arrival teleport **in any window where a 0x002C
actually goes out**.

**Does NOT — and this is the honest limit of my angle:**

1. **The six warp-free events prove the payload policy, not the primitive.** `--cast-stop=pin`
   sends a *reckoned* point — the client's position brought forward to now. Of course the
   body barely moves. The primitive will install **whatever** you give it, including a
   stale point, with no distance guard, no path solve and no collision check (§4). A
   0x002C is a warp **exactly as far as its payload is wrong.** `--resync`'s payload is the
   client's last accepted report, which is *weaker* than cast-stop's reckoning.
2. **The measured harm bound is a loopback number.** The 2026-08-20 `--resync` rows report
   `age: 0.0` / `0.0001 s` on every fire, because `_maybe_resync` is called from the
   report-arm itself — so the payload is the report that just arrived, and the back-yank is
   ~0.03 u. `authsrv.py` itself flags that `client_pos_at` is the **server's receive time**
   and excludes both network legs. **On a real network the harm is RTT × speed and nobody
   has measured it.** Against PLAN.md Q10's bar this is the live risk, not the primitive.
3. **F35 is wire-silent, and that is a *cadence* problem, not an operand problem.**
   `--resync` is report-driven; the client emits 0x003D only while moving and 0x0047 only
   on a stop. If F35's stale arm fires during a silent window — and the STOP_ECHO block
   records a click-walk sending no position report for up to **12.9 s** — no 0x002C is
   sent and nothing is disarmed. **"0x002C would disarm it" and "a 0x002C will be in
   flight in time" are different claims and only the first is established here.**
4. **The 517 u SYNC jump is unexplained as a *visual* non-event only by inheritance.**
   I verified `AgTrack::Clear` runs first; I did not verify that nothing renders the SYNC
   copy. The 6/6 small `d ASYNC` is the evidence that it does not matter in practice.

---

## 9. Things I could not determine

* **Whether the 2026-08-20 `--resync` run warped anything.** 18 sends on the wire, 52
  verdict rows, and **no co-timed movetap** — nothing in `vault/captures/movetap/` is dated
  20260820. That run is wire-only and cannot be scored for body displacement.
* **Which handler is s2c 0x0029's**, and therefore whether "0x0029 is SYNC-ONLY" is true
  from the binary. I took it from `authsrv.py`'s `--resync` block (SOURCED, and its own
  cited evidence is about 0x0025 at `0x005FD5D3`, a *different* message — so the citation
  under it does **not** fully support the sentence). The movetap divergence between `stop`
  and `async_stop` (§7) is consistent with it but does not prove it.
* **What `0x005FFB40` computes**, beyond "returns a 16-byte point that the settle installs
  as the current position." Not needed for the operand answer, since the settle's write is
  dead inside `0x006020B0` (§3).
* **Whether the remaining five callers of `0x006020B0`** (`0x00600A91`, `0x00601817`,
  `0x00601899`, `0x006025A6`, and the `0x0060221E` recursion) pass a caller point or a
  field. I read `0x00601817` (caller's `[ebp+0xc]`) and `0x0060221E` (propagates the
  parent's own args); the other three I did not open.
