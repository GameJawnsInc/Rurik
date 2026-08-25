# P5 (`--resync`) vs F35 — the disarm claim, and the `--stop-echo` reconciliation

Recon note. **No client launch, no harness, no `session.py`.** Static disassembly of the
PINNED PRISTINE build-38797 image (`vault/client/2026-07-29_221c13772c7a/Gw.exe`, which
`toolkit/clientscan/pinned.py` reports as *"verified pristine -- build 38797, PRISTINE"*),
plus existing vault captures and read-only replays.

Tags used on every claim:
**OBSERVED** — I ran the measurement / read the instruction and am quoting the output.
**SOURCED** — a doc or the binary says it and I checked the citation resolves.
**UNVERIFIED** — I am reasoning past what I measured.

---

## 0. Headline, before the detail

1. **The orchestrator's disarm claim is CONFIRMED from the binary, and it is stronger than
   stated.** `0x00602B20`'s armed arm pushes a **by-value copy of the CALLER's point** and
   `0x006020B0` writes **that** into `+0x78`. A `0x002C` therefore lands the body on the
   resync point, clears `+0x48`, and erases the destination to the `+inf` sentinel. It
   cannot itself warp to the stale `+0x9c`. §1.
2. **It is no longer only a prediction — it is already in the corpus.** `--cast-stop=pin`
   (shipped default since 2026-08-25) sends `0x002C`, and one of them landed **while
   `+0x48` was armed at a destination 512 u away**. The movetap shows both copies landing on
   the message's own point, `+0x48 → 0`, `target → [inf, inf]`, separation → 0.00 u, and the
   **rendered** body moving 9.86 u. §1.8. This is the disarm, measured, on the owner's machine.
3. **The doc tension resolves and one published line is wrong.** The grant wrapper
   `0x00602A40` overwrites `+0x88..+0x94` *and* `+0x9c..+0xa8` **above** the bake's
   `<= 1.0 u` branch, so every `0x0029` overwrites the armed destination unconditionally.
   `authsrv.py:1103-1104` ("overwrites") is right; **`authsrv.py:1149` ("`+0x48` … is set once
   … and is NEVER re-armed") is REFUTED**; the 2026-08-19 "it ADDS a SECOND one" reading
   cannot be literally true and has a better explanation that fits the operator's report
   exactly. §2, §4.
4. **P5 as wired today DOES fire in F35's regime** — replaying the shipped `_resync_verdict`
   over the F35 capture fires at the arming `0x003D` (modelled sep 512.9 u) **and** at the
   stop `0x0047` (modelled sep **177.4 u** — F35's own magnitude), **1.098 s before the
   arrival matured**. §3.
5. **`RESYNC_MAX_REPORT_AGE` never bites at either call site.** Both sites run
   `_maybe_resync` in the same call as `_take_client_position`, so `age ≈ 0` always: over
   558 reports in 16 recent captures the replay produced **0 `stale` refusals**. The 0.347 s
   constant is a harm bound, not a liveness gate. §3.4.
6. **The real holes are elsewhere and I name four.** §3.5.
7. **Q10:** P5 does not "remove the snap" — it **bounds** it at `RESYNC_SEPARATION`, and the
   shipped value (100.0 u) and `resyncscore.py`'s own recommendation (299.33 u) **disagree
   with each other**. A 100 u residual snap is still a snap. §4.
8. **The retail 70-of-88 is a stale denominator, and I re-derived the number.** Over the
   whole live corpus: **172 stops, 147 answered within 1.0 s (85.5%), 134 of them < 1 u from
   the reported stop (77.9% of all stops)**, `|dest − stop|` p50 **0.000 u**, latency p50
   0.034 s. §5.
9. **Retail's stop-ack is mechanically the SAME thing as `--stop-echo`, not the same as
   `--resync`** — it is a `0x0029` through the same wrapper and the same bake, and my model
   says it does **not** take the short-circuit either (p50 60 u from the copy, **0 of 129
   under 1.0 u**). What differs is the LENGTH of the leg it bakes. And retail sends
   `0x002C` to the player's own agent **5 times in the entire live corpus** — retail does
   not use the disarm primitive. §5.

---

## 1. Q1 — the `0x002C` → SetPosition → arrival → `+0x48 = 0` path

### 1.1 The `0x002C` handler `0x005FDA50` — OBSERVED

`python toolkit/clientscan/codescan.py --dis 0x005FDA50 --count 80`

```
005FDA6A  call 0x5fcec0          ; ecx = agentMgr, arg = &msg[+8] (the wire vec2)
005FDA78  lea ecx,[esi+0x1cc] / call 0x605f70    ; AgTrack::Clear(msg.agentId), FIRST
005FDAA2  mov eax,[esi+0xe8]     ; the SYNC array
005FDAA8  mov eax,[eax+ecx*4]    ; sync copy of the agent
005FDAC6..005FDADE               ; local Point {msg.x, msg.y, msg.plane, 0} at [ebp-0x10]
005FDAE5  call 0x602b20          ; SetPosition(sync copy, &localPoint)
005FDB09  mov eax,[esi+0x14c]    ; the ASYNC array
005FDB0F  mov edi,[eax+edi*4]    ; async copy
005FDB2A..005FDB42               ; the SAME point rebuilt
005FDB49  call 0x602b20          ; SetPosition(async copy, &localPoint)
005FDB64  ret
```

Reproduces the orchestrator exactly. The two intervening blocks (`0x005FDA8B`, `0x005FDAB2`)
are bounds/null **asserts**, not conditional skips.

### 1.2 `SetPosition 0x00602B20` — and what the 16-byte push actually is — OBSERVED

```
00602B33  lea  edi, [ebx+0x78]              ; edi = &agent.position
00602B44  cmp  dword [ebx+0x48], 0          ; the arrival tick
00602B55  mov  eax, [esi]                   ; esi = the CALLER's Point*, eax = caller.x
00602B57  je   0x602b7b                     ; parked -> direct write

;--- ARMED (+0x48 != 0) --------------------------------------------------------
00602B59  sub  esp, 0x10                    ; 16 bytes of stack
00602B5C  mov  ecx, esp
00602B5E  mov  [ecx],     eax               ; <- CALLER's point dword 0
00602B60  mov  eax,[esi+4]   / 00602B63  mov [ecx+4],  eax
00602B66  mov  eax,[esi+8]   / 00602B69  mov [ecx+8],  eax
00602B6C  mov  eax,[esi+0xc] / 00602B6F  mov [ecx+0xc],eax
00602B72  mov  ecx, ebx                     ; this = agent
00602B74  call 0x6020b0                     ; the arrival primitive
00602B79  jmp  0x602bc9

;--- PARKED (+0x48 == 0) -------------------------------------------------------
00602B7B  mov  [edi], eax                   ; +0x78..+0x84 := CALLER's point, verbatim
00602B90  push edi / call 0x70a150          ; validity predicate on the new point
00602B9A  je   0x602bb3
00602B9E..00602BB0  +0x68..+0x74 := +0x78..+0x84   ; the "last known good" copy
00602BB7  add ecx,0x1cc / call 0x605fc0     ; the AgTrack dispatcher
00602BC2  mov  dword [ebp-8], 1             ; enables the attached-agent fan-out at 0x00602C0C
                                            ;   (the ARMED path skips that block entirely)
```

**THE LOAD-BEARING ANSWER: the 16-byte stack argument is a BY-VALUE COPY OF THE CALLER'S
POINT.** All four dwords come from `[esi+0]`, `[esi+4]`, `[esi+8]`, `[esi+0xc]` where
`esi = [ebp+8]` is the `Point*` the caller supplied. The callee agrees: `0x006020B0` reads
its arguments at `[ebp+8] / [ebp+0xc] / [ebp+0x10] / [ebp+0x14]` and ends `ret 0x10`
(`0x006022AC`) — a `__thiscall` taking one 16-byte struct by value. **OBSERVED.**

**The parked branch** writes the caller's point straight into `+0x78..+0x84`, refreshes
`+0x68..+0x74` when `0x0070A150` accepts the point, and dispatches. **OBSERVED.**

### 1.3 The arrival primitive `0x006020B0` — what it writes — OBSERVED

```
006020B6..006020F2  assert: the caller's point must not be the sentinel in BOTH x and y
                    (assert id 0x812; sentinel = [0x948654])
006020F6  mov  ecx, ebx
006020F8  call 0x5ff880                     ; the settle -- see 1.5
006020FF  lea  esi, [ebx+0x78]

00602132  mov [esi],     eax   ; eax = [ebp+8]    <- CALLER point .x
0060213A  mov [esi+4],   eax   ; eax = [ebp+0xc]  <- CALLER point .y
00602143  mov [esi+8],   eax   ; eax = [ebp+0x10] <- CALLER point .z
0060214F  mov [esi+0xc], eax   ; eax = [ebp+0x14] <- CALLER point .w

0060210E  fstp [ebx+0xb0], 0.0    ; velocity x := 0
00602117  fstp [ebx+0xb4], 0.0    ; velocity y := 0
00602155  mov  [ebx+0x88], INF    ; segment point x
00602164  mov  [ebx+0x8c], INF    ; segment point y
0060216D  mov  [ebx+0x9c], INF    ; target point x
00602179  mov  [ebx+0xa0], INF    ; target point y
0060217F/00602194/0060219E  +0x90 / +0x94 / +0x98 := 0
00602189/006021A8           +0xa4 / +0xa8 := 0
006021B2  push esi / call 0x70a150
006021BC  je   0x6021d5           ; skips ONLY the +0x68..+0x74 refresh
006021D8  mov  dword [ebx+0x3c], 0
006021DF  mov  dword [ebx+0x40], 0
006021E6  mov  dword [ebx+0x48], 0   ; <<< THE CLEAR
```

**Two corrections to the orchestrator's summary, both material.**

* **`0x0060216D` does NOT write a syncPoint value — it writes `+inf`.** I read the constant
  out of the pinned image with `pefile`: **`[0x948654] = 0000807f` = `+inf`** (OBSERVED).
  Tracing the x87 stack from `fld [0x948654]` at `0x0060211D` through the six `fst/fstp`
  shuffles to `0x00602179` carries exactly one value, so `+0x88`, `+0x8c`, `+0x9c`, `+0xa0`
  all receive it. This block is a **destination ERASE**, not a position copy — and it is
  precisely the movetap observable the follow-on list records for F35
  (`target … arm -> fire -> [inf,inf]`). **The `[inf,inf]` in the movetap IS
  `0x00602155`/`0x0060216D` executing.**
* Independent corroboration that `+inf` is the "no destination" sentinel: at `0x0060226C`
  the client asserts (id `0x82a`) that whenever `+0x48 != 0`, `+0x9c` and `+0xa0` are **not
  both** `+inf`. Armed tick and finite destination are one invariant. **OBSERVED.**

### 1.4 Is the clear UNCONDITIONAL once `0x006020B0` is entered? — OBSERVED: yes

Branch census, entry → `0x006021E6`:

| site | what it tests | do both arms reach `0x006021E6`? |
|---|---|---|
| `0x006020D0 jp 0x6020f4` | caller point .x vs sentinel | yes; `0x6020f4` is `fstp st(0)` falling into the join `0x6020f6` |
| `0x006020DC jp 0x6020f6` | caller point .y vs sentinel | yes; the target *is* the join |
| `0x006020ED call 0x487bc0` | the assert, only when the caller passed `(inf,inf)` | falls through to `jmp 0x6020f6` |
| `0x006021BC je 0x6021d5` | `0x0070A150` rejected the point | yes; skips only the `+0x68..+0x74` refresh |

No other conditional exists between `0x006020F6` and `0x006021E6`. **The clear is
straight-line and unconditional**, with the single caveat that the assert helper
`0x00487BC0` must return — and it is reached only for an `(inf,inf)` caller point, which a
`0x002C` carrying real coordinates is not. **OBSERVED.**

### 1.5 The settle `0x005FF880` (called at `0x006020F8`) — OBSERVED, and it does not change the answer

```
005FF89A  cmp  dword [esi+0x48], 0
005FF8A8  je   0x5ff8e1                    ; parked -> skip the whole block
005FF8B1  call 0x5ffb40                    ; -> eax = the interpolated point for the pending move
005FF8B9..005FF8CE  +0x78..+0x84 := *eax   ; the body is advanced to where the glide had got to
005FF8D9  call 0x603040                    ; AgTrack notify with that interim point
005FF8E1  cmp  dword [esi+0x4c], 0 ...     ; facing block -> +0xb8 / +0xbc / +0xc0
005FF932  mov  [esi+0x58], eax             ; +0x58 := "now"
```

The settle **does** move `+0x78` — but it runs *before* the arrival's own `+0x78` write at
`0x00602132`. Last writer wins, and the last writer is the caller's point. The settle also
cannot re-arm: the writer census (§1.6) finds no `+0x48` store inside it. **OBSERVED.**

### 1.6 `+0x48` writer census — OBSERVED, reproduced

`python toolkit/clientscan/codescan.py --field 0x48 --in AgAgent`
→ `AgAgent 0x005FE0C3..0x00602CE2 (70 assert sites)`, **33 instructions: 4 stores, 29
reads, 0 address-taking**:

```
005FE531  W  mov [ebx+0x48], esi
005FEAD6  W  mov [esi+0x48], eax   <- bake, the <=1.0 u short-circuit arm
005FEB46  W  mov [esi+0x48], ecx   <- bake, the full arm
006021E6  W  mov [ebx+0x48], 0     <- the ONLY clear
```

Matches the orchestrator exactly.

**The caveat, and the check `codescan`'s own footer prescribes for it — RUN, and it comes
back clean.** The named blind spot is *"a field reached through a BIASED `this`"*: `0x48` is
a disp8 offset, so a subobject pointer biased by ±8 would spell the same field `[reg+0x40]`
or `[reg+0x50]` and never show up. The footer's rule is *"re-run at disp−4 and disp+4 before
believing it"*. I ran ±8 (the alias widths that could reach `0x48`):

```
--field 0x40 --in AgAgent --writes : 6 stores
  005FE5AD (same function as 0x005FE531's +0x48 store, same base)
  00600888 · 00600B29 · 00600B50
  006021DF (the arrival, one instruction BEFORE its own +0x48 clear at 0x006021E6)
  00602BDE (SetPosition, same base as its +0x78 writes)
--field 0x50 --in AgAgent --writes : 7 stores
  0060034F · 00600A71 · 006017F0 · 00601875 · 00602577 (+ two byte-granularity decodes)
```

Every one of these sits in a function that also writes `+0x48` **or** `+0x78` off the *same*
base register, which is what "its own field on the agent base" looks like and not what an
aliased `+0x48` looks like. **The hole is checked, not merely acknowledged — but this is
evidence, not proof.** OBSERVED.

**Positive control for the search itself**: the same tool at `--field 0x9c --in AgAgent
--writes` returns 5 rows including `0x0060216D`, and `--field 0x88 --writes` returns
`0x005FEAE3` — both instructions I had already read in the disassembly by eye. The scan does
find stores I know exist.

### 1.7 What the arrival's OTHER caller passes — OBSERVED, and it names F35's mechanism

`--xrefs 0x006020B0` → **7 direct callers**: `0x0060032E`, `0x00600A91`, `0x00601817`,
`0x00601899`, `0x0060221E`, `0x006025A6`, `0x00602B74`. The movement tick's is `0x0060032E`:

```
006001DA  call 0x5ffb40                       ; the dead-reckoned point -> [ebp-0x2c]
006001DF  mov  ebx, [esi+0x48]
006001EB  cmp  edi, ebx / jne 0x600379        ; EXACT equality: now == +0x48, not >=
00600267  lea  ebx, [esi+0x9c]                ; ebx = &m_targetPoint
0060029F  test dword [esi+0x20], 0x40000      ; bit 18 = isWaypoint
006002AC  je   0x6002bf                       ; bit CLEAR -> the TELEPORT branch
006002B5  call 0x5fe950                       ;   (bit SET -> re-bake, i.e. glide onward)
006002F0  fcomp [0x93c1c8] ... assert 0x486   ; the reckoned point must already BE at the target
00600311..0060032C  push the 16 bytes at [ebx] = agent+0x9c..+0xa8
0060032E  call 0x6020b0
```

So the tick-driven arrival passes **`agent+0x9c..+0xa8` (m_targetPoint)** — `+0x78 := +0x9c`.
That is F35. **OBSERVED**, and it agrees with `authsrv.py:1098-1100`'s decode.

And the propagation onto the *rendered* copy is `0x006022B0`, which takes the SOURCE agent's
`+0x88..+0x94` **when the source's `+0x48` has come due** (`0x006022EC..0x006022FF`) and
dead-reckons it otherwise. **OBSERVED.**

### 1.8 THE DISARM, ALREADY MEASURED IN-CORPUS — OBSERVED, and this is the strongest evidence in this note

`--cast-stop=pin` ships `0x002C`, so the claim is no longer counterfactual.

Capture pair (clocks aligned to 1 ms: movetap `now` + 1030 ms = gamesrv `t`, verified on two
independent grant/target coincidences):
`vault/captures/gamesrv/authsrv-20260825T140517-c1.jsonl` ·
`vault/captures/movetap/movetap-20260825T140548.jsonl`

| wire / movetap | what |
|---|---|
| gamesrv `t=52.413` | `0x003D` report at `(-5148.82, -2442.37)`, accepted |
| gamesrv `t=52.414` | `SENT 0x29 ZERO LEAD (-5149,-2442)` |
| movetap **L257** | `point(+0x78) = (-5659.78,-2400.95)` · `target = (-5148.82,-2442.37)` · `stop(+0x48) = 52911` · `updated(+0x58) = 51132` · `sep = 512.6` — leg 512.6 u / 288 = 1.779 s, and `51132 + 1779 = 52911` **exactly** |
| gamesrv `t=52.581` | `SENT 0x2c CAST-STOP PIN 0x002C at (-5101,-2446) plane 0` |
| movetap **L259** | `point = async_at = (-5100.81,-2446.26)` · `target = (inf,inf)` · `stop = 0` · `updated = 51282` · `sep = 0.00` |

**A `0x002C` landed 0.15 s into a 1.78 s armed window whose destination was 512 u away, and
both copies went to the message's own point — NOT to the armed target.** `+0x48` cleared,
`target` flipped to `[inf,inf]`, separation collapsed to 0.00 u, and the **rendered** body
moved **9.86 u** (L258 → L259), forward, which is the pin's own reckon lead and not a yank.

This is §1.2-§1.4's decode executing. **The "if it writes the stale `+0x9c`, a `0x002C` would
itself warp" alternative is refuted twice over — at `0x00602B5E`/`0x00602132` in the binary,
and here on the wire.**

> **⚠ A published claim is now stale.** `studies/movement/PROBE-GATEFIRE.md:748` and
> `toolkit/clientscan/resyncscore.py:31` both say our server has sent `0x002C` **zero** times
> in the vault. Since `--cast-stop=pin` shipped (2026-08-25) that is false: this one capture
> holds two. Anything that reasons from "we have never sent it" needs re-reading.

### 1.9 Verdict on Q1

**CONFIRMED and sharpened.** `0x002C` → `0x00602B20` → (armed) → `0x006020B0` ⇒
`+0x78 := the message's own point`, `+0x48 := 0`, destination `:= (inf, inf)`, velocity `:= 0`.
It disarms, and it lands the body at the resync point.

---

## 2. Q2 — the grant bake, and the three-way doc tension

`0x0029`'s handler is `0x005FD890` (OBSERVED; `0x005FD930` is `0x002A`'s, byte-identical bar
assert id `0x217` vs `0x201`). It resolves the agent out of the **SYNC** array `[esi+0xe8]`
and makes **one** call:

```
005FD8EF..005FD90C   local Point {msg.x, msg.y, msg.field3, 0}
005FD906  push 0                       ; arg1
005FD8F4  push [edi+0x14]              ; arg2 = field4
005FD913  call 0x602a40                ; the shared move setter
```

### 2.1 The wrapper `0x00602A40` — where the overwrite happens — OBSERVED

```
00602A48  test dword [ebx+0x20], 0x20000   ; INTERNAL_FLAG_IN_WORLD, asserted
00602A65  and  dword [ebx+0x20], 0xfff7ffff
00602A6C  if arg2 != -1 -> [ebx+0x80] = arg2
00602A84  mov [ebx+0x88], D.x        \
00602A8D  mov [ebx+0x8c], D.y         |  segment point
00602A96  mov [ebx+0x90], D.z         |
00602A9F  mov [ebx+0x94], D.w        /
00602AA8  mov [ebx+0x98], arg1
00602AB0  mov [ebx+0x9c], D.x        \
00602AB9  mov [ebx+0xa0], D.y         |  target point
00602AC2  mov [ebx+0xa4], D.z         |
00602ACD  mov [ebx+0xa8], D.w        /
00602AD3  call 0x5fe950                    ; the bake, (D, 0, 1)
```

**Every one of those stores is above the bake and above every branch inside it.** So:

> **A new `0x0029` OVERWRITES the armed destination, always. It never adds a second one.**
> **OBSERVED.**

### 2.2 The bake `0x005FE950` and its `<= 1.0 u` short-circuit — OBSERVED

```
005FE9EA  call 0x5ff880                 ; SETTLE FIRST: +0x78 advanced to the reckoned point
005FE9EF  mov  eax,[esi+0x58]           ; "now"
005FEA51..005FEA7D  d = D - (+0x78);  [ebp-8] = |d|^2
                    (0x005FEA5F `fsub [edi+4]`, 0x005FEA6B `fsub [edi]`, edi = esi+0x78)
005FEA80  fld1 / 005FEA85 fcom st(1) / 005FEA8B test ah,0x41
005FEA90  jp 0x5feae1                   ; |d|^2 >  1.0  -> FULL BAKE
                                        ; |d|^2 <= 1.0  -> fall through, SHORT-CIRCUIT

;--- SHORT-CIRCUIT ------------------------------------------------------------
005FEA92..005FEAA9  +0x78..+0x84 := D          ; teleport onto the destination, now
005FEAC6/005FEAD0   +0xb0 / +0xb4 := 0.0       ; velocity zero
005FEAD6  mov [esi+0x48], eax                  ; eax = max(now+1, 1)   <- ARM at now+1
005FEADE  ret 0xc                              ; NO dispatch to 0x605fc0

;--- FULL BAKE ----------------------------------------------------------------
005FEAE3..005FEB07  +0x88..+0x94 := D          ; (redundant with the wrapper, and unconditional)
005FEB0D  call 0x5b6e80                        ; dist = sqrt(|d|^2)
005FEB1B  fmul [0x943898] / 005FEB22 fdiv speed / 005FEB2E call 0x46e0a0
005FEB46  mov [esi+0x48], ecx                  ; ecx = max(now + travel_ticks, 1)  <- ARM
005FEB49..005FEBC8  velocity +0xb0/+0xb4 = unit(D - +0x78) * (+0x60 * +0x5c)
005FEBEB  call 0x605fc0                        ; the AgTrack dispatch
```

**Both arms overwrite `+0x48`.** The short-circuit does not touch `+0x88..+0xa8` — but it
does not need to, because the wrapper already did.

### 2.2a The other four bake callers cannot arm a teleport at all — OBSERVED

`--xrefs 0x005FE950` gives five callers. Checking each against the bake's `arg1`
(`[ebp+0xc]`, tested at `0x005FEA35`), which sets or clears **`m_flags` bit 18 = 0x40000**
(`0x005FEA3B or eax,0x40000` / `0x005FEA49 and eax,0xfffbffff`) — and bit 18 is exactly what
the movement tick branches on at `0x0060029F` to choose **re-bake (glide)** over
**teleport**:

| caller | arg0 (`D`) | arg1 | effect |
|---|---|---|---|
| `0x00602AD3` (the wrapper, from `0x0029`/`0x002A`) | the wire point | `0` (`0x00602A7F push 0`) | **clears** bit 18 ⇒ arms the TELEPORT branch |
| `0x00600B0A` | a local `[ebp-0x44]` | `1` | **sets** bit 18 ⇒ glide/waypoint leg |
| `0x00601936` | a local `[ebp-0xa4]` | `1` | **sets** bit 18 ⇒ glide/waypoint leg |
| `0x006002B5` (the tick's own re-bake) | `&agent+0x9c` — the destination it already holds | `0` | re-aims at the SAME point |
| `0x005FEC7E` | — | — | its function writes `+0x88` (`0x005FEC11`) and `+0x9c` (`0x005FEC52`) before calling: a second wrapper, same overwrite discipline |

So **no bake path introduces a destination the wrapper did not already write**, and the two
non-wrapper paths do not arm the teleport branch at all. This closes the refutation item
"a `0x0029` might reach the bake without `0x00602A40`" in the direction of the claim.
(It also confirms `movetap.py`'s header sentence *"every grant we send arms the teleport
branch and never the glide branch"* from the argument side.)

### 2.3 Resolving the three doc claims

| claim | verdict |
|---|---|
| `authsrv.py:1103-1104` "armed until it fires or until a newer grant OVERWRITES it" | **CORRECT.** `0x00602A40` + `0x005FEAD6`/`0x005FEB46`. |
| `authsrv.py:1149` "`agent+0x48` … is set once when a grant lands and is NEVER re-armed" | **REFUTED.** Two of the four `+0x48` stores in `AgAgent` are the two bake arms, and the handler reaches them on every `0x0029`. The sentence should read "is set on **every** grant and cleared only by the arrival". |
| 2026-08-19: the echo "does not overwrite the pending destination; it ADDS a SECOND one" | **Cannot be literally true.** There is one `+0x48`, one `+0x88..+0x94`, one `+0x9c..+0xa8`, and the wrapper rewrites all three unconditionally. The observation has a different explanation — §4. |

### 2.4 The short-circuit, caught in the wild — OBSERVED

`movetap-20260825T140548.jsonl` **L216**: `point = target = (-5659.78,-2400.95)` (|d| = 0),
`updated(+0x58) = 47777`, `stop(+0x48) = 47778` — **`now + 1` exactly**, i.e.
`0x005FEAD6`'s `max(now+1,1)` arm bit for bit. It fires the next sample with **zero**
displacement. The short-circuit is real and it is a genuinely free "park here".

### 2.5 What a zero-distance-from-CLIENT `0x0029` does to a FAR sync copy — OBSERVED, step by step

The branch operand is `D − agent+0x78` **of the sync copy**, after the settle
(`0x005FEA6B fsub [edi]`, `edi = esi+0x78` set at `0x005FE99C`) — not `D − client`.
`REALFIX.md:68` records the same correction from the other direction: replayed through
`grantsim.py`, only **6 of 539** synthesized zero-lead grants took the `<=1.0 u` arm, median
`|d|` from the copy **101 / 383 / 208 / 512 u**. SOURCED, citation resolves.

So a stop-echo-shaped grant, from the player's point of view:

1. wrapper overwrites both destination blocks with `D` (= where the client is standing);
2. bake settles `+0x78` to the copy's reckoned position, hundreds of units away;
3. `|d| >> 1.0` ⇒ **FULL BAKE**: velocity aimed **from the far copy back toward the player**,
   arrival armed at `now + |d|/288`;
4. the copy then **WALKS** that whole leg, and the reseed `0x006022B0` drags the rendered
   copy with it whenever it runs.

**That is one destination being walked, not two destinations. It looks like "a second
destination" because the player sees the body move toward a place they already left.**

---

## 3. Q3 — does `--resync` fire in F35's regime, as wired today?

### 3.1 F35's timeline, re-derived from the two capture files — OBSERVED

Clock alignment: movetap `now` + **1030 ms** = gamesrv `t` (checked twice against
independent grant→target coincidences, agreeing to 1 ms).

| gamesrv `t` | movetap | event |
|---|---|---|
| 36.364 | L67 | `0x003D` at `(-6172.40,-2383.05)`; `ZERO LEAD (-6172,-2383)` sent |
| 38.169 | **L89** | `0x003D` at `(-5659.78,-2400.95)`, drift 5.47, accepted; `ZERO LEAD (-5660,-2401)` sent. **This arms F35.** `+0x48 = 38868`, `+0x58 = 37087`, `target = (-5659.78,-2400.95)`, `point = (-6172.40,-2383.05)` — leg **512.93 u** ⇒ 1781 ms ⇒ `37087+1781 = 38868` exactly. Report gap 36.364→38.169 = **1.805 s**, the ~512 u `0x003D` chord. |
| 38.800 | ~L97 | `0x0047` STOP at `(-5482.48,-2407.14)`, drift 4.61, accepted, `stop-report`. `async_stop`, `async_vel_raw` go to 0 at L96 — the rendered copy parks. |
| 38.169 → 39.898 | — | **the wire is silent**: no send of any movement opcode between them (next is `t=48.995`). |
| 39.898 | **L111** | the arrival matures. `point → (-5659.78,-2400.95)`, `target → (inf,inf)`, `stop → 0`, `updated → 38868`, and **`async_at` jumps 177.41 u** from `(-5482.48,-2407.14)` to `(-5659.78,-2400.95)`. `sep` at L110 = 185.47 with `gate1 = "below"` — **gate 1 did not do this**. |

**The player stood still for 1.098 s between the stop report and the arrival.** That is the
window `--resync` has to work in, and it is wide.

### 3.2 The verdict, replayed — OBSERVED

I re-implemented the **shipped** `_sync_position` / `_resync_verdict`
(`RESYNC_SEPARATION=100.0`, `RESYNC_MIN_INTERVAL=0.5`, `RESYNC_MAX_REPORT_AGE=100/288`) with
the two call sites' ordering (take → resync → grant), seeded the sync model the way
`authsrv.py:12965` seeds it at placement, and replayed the F35 capture:

```
 t=  36.364 0x003D  -> in-agreement   sep=21.6
 t=  38.169 0x003D  -> RESYNC         sep=512.9      <- before the grant that arms F35
 t=  38.800 0x0047  -> RESYNC         sep=177.4      <- at the stop, 1.098 s before the arrival
 t=  48.995 0x003D  -> RESYNC         sep=177.4
 ...
 FIRES: 8 / 20 reports    refusals: {'in-agreement': 12}
```

**The modelled separation at the stop is 177.4 u — F35's own magnitude, to 0.01 u.** The
model is not guessing; it is reading the same staleness the client is about to express.

### 3.3 The concrete predicted sequence with `--resync` ON

**At `t=38.169` (the arming report), OBSERVED gates + UNVERIFIED consequence:**
take → `client_pos = (-5659.78,-2400.95)`, `age ≈ 0` → verdict FIRE (sep 512.9) → `0x002C`
at that point → sync copy is **parked** at that instant (`+0x48 = 0` since L68), so
`0x00602B20` takes the **parked** arm and writes `+0x78` directly, no arrival involved →
then the zero-lead `0x0029` goes out to **the same point**, so the bake's `|d| ≈ 0` ⇒ the
`<= 1.0 u` **SHORT-CIRCUIT** ⇒ `+0x78 := D` (no motion), velocity 0, `+0x48 := now+1`, and
it fires one tick later onto a point the copy is already on. **Displacement: zero. The
staleness is removed at its source, not intercepted downstream.** This is exactly the shape
already observed at L216 (§2.4).

**At `t=38.800` (the stop), belt and braces:**
take (`stop=True`, always accepted) → `age ≈ 0`, `pos_rejects = 0` (all 20 reports in this
capture are `accepted: true`), plane 0, sep 177.4 ≥ 100, last fire 0.631 s ago > 0.5 →
**FIRE** → `0x002C` at `(-5482.48,-2407.14)`. The sync copy is armed ⇒ arrival primitive ⇒
`+0x78 := the stop point`, `+0x48 := 0`, `target := (inf,inf)`. The async copy has
`async_stop = 0` ⇒ parked arm ⇒ `+0x78 :=` the point it is **already standing on**.
**Rendered displacement: 0.00 u. F35's 177.41 u snap → 0 u.**

### 3.4 `RESYNC_MAX_REPORT_AGE` — the orchestrator's specific question

**It does not bite at either call site, and the player standing still is irrelevant to it.**
Both sites call `_maybe_resync` in the same handler invocation as `_take_client_position`, so
`age = now − client_pos_at ≈ 0` by construction. Over **558 reports in 16 recent `ours`
captures** the replay produced **`stale` = 0** (§3.6). The 0.347 s constant is what its own
comment says it is — *"THE STALENESS BOUND, AND IT IS THE HARM BOUND"* — a cap on how far the
payload can be behind the body at the instant of the fire, not a liveness condition. The
1.098 s the player stands still is *after* the fire, and by then `+0x48` is already zero.

### 3.5 THE HOLES — four, named

**HOLE A (structural, unavoidable in this design): the sender is REPORT-DRIVEN, so an
arrival that matures inside a report gap is unreachable.** At cruise the `0x003D` chord caps
the gap at ~1.80 s (measured in this very capture: 1.805 s) and an arrival for a full chord
of staleness matures at ~1.78 s after its grant. That is a coin-flip. It is harmless *after*
the first fire (every subsequent grant is a zero-distance short-circuit), but the first grant
after any refusal is exposed. `authsrv.py`'s own note frames this as a feature — *"a
click-walk sends no position report for up to 12.9 s, so a server-granted click-walk cannot
be interrupted by this sender"* — and it is the same property.

**HOLE B: `in-agreement` leaves a residual snap of up to `RESYNC_SEPARATION`.** When
`sep < 100 u` the fire is refused and the grant still goes out; the bake then sees
`1.0 u < |d| < 100 u` ⇒ **full bake**, arming a real arrival at a point up to 100 u behind.
**P5 does not remove the snap; it bounds it.** Measured in the pooled replay: **380 of 558
reports refuse with `in-agreement`** — that is the population that keeps a residual.

**HOLE C: `rate-limited` at 0.5 s, and the corpus really does produce sub-0.5 s report
pairs.** In the F35 capture alone: gaps of 0.100 s, 0.299 s, 0.366 s (all `0x0047`-then-
`0x003D` stop-and-go). Pooled, the replay refused **23** fires as `rate-limited`. The
residual staleness there is small (≤ 0.5 s × 288 = 144 u) but it is not zero.

**HOLE D: `no-sync-model` is only closed by the placement seed.** `_note_wire_move` writes
`sync_from = _sync_position(state, now)`, which returns `None` while unseeded — so a grant
**can never seed the model**. Only `authsrv.py:12965` (map placement) does. That is correct
and deliberate, but it means **any path that reaches a live session without running that
block leaves `--resync` permanently inert and silent about it**. I proved the failure mode
accidentally: my first replay omitted the seed and got `no-sync-model` × 14 with **zero**
fires across the entire F35 window. Worth a startup assertion.

**Not a hole here, but the doc's own one, unexercised:** the `report-refused` gate never
opened in this corpus (**0 of 558**) because every report was accepted. The hole
`_resync_verdict:4045-4059` documents is real; it is simply not visible in these captures.

### 3.6 Pooled replay — OBSERVED

16 `ours` captures from 2026-08-24/25 (the shipped `--zero-lead` + `--grant-suppress` +
`--cast-stop=pin` regime), 558 position reports, 1,662 s of span:

```
fires 155 = 5.60/min = 27.8% of reports
refusals: in-agreement 380 · rate-limited 23 · stale 0 · report-refused 0 · no-sync-model 0
per-capture rate: 0.00 - 25.12 /min
```

**Compare with the projection printed on the flag** (`authsrv.py`, the `RESYNC_SEPARATION`
block): *"1,998 fires, 25.4 per minute of span, 42.2% of reports"*. That was replayed over
the older 66-capture corpus, produced partly by two refuted configurations. **On the shipped
default the rate is ~4.5× lower** (5.60/min vs 25.4/min) and the share of reports is 27.8%
vs 42.2%. The block's own caveat — *"treat it as a magnitude, not a score"* — holds, and the
magnitude is over-stated for today's build.

---

## 4. Q4 — does P5 pass Q10's bar?

### 4.1 The existing pricing, quoted — SOURCED (`toolkit/clientscan/resyncscore.py`)

* *"the yank stays p50 **0.08 u** at every one of them, because the payload is always the
  client's own freshest adopted report. Firing more often costs FREQUENCY and not MAGNITUDE"*
  — at a measured send delay of **p50 0.26-0.31 ms, max 50 ms**.
* *"RETAIL IS NOT SYNCHRONISED TO THE UNIT. Its own two copies, through the same model, sit
  **p50 83 u, p75 260 u, p90 653 u, max 2,972 u** apart with zero snaps. A resync threshold
  of 100 u therefore sits at ArenaNet's own MEDIAN separation … raising it to 299.33 u costs
  NO coverage on our corpus (7/7 either way) and halves the retail rate. **Raise the
  threshold, drop the cooldown.**"*
* Retail control, re-run by me: `resyncscore.py --retail` → *"44 usable connection(s) of 56 …
  rule A:parked at threshold 299.33 u / cooldown 1.00s fires 36 time(s) = 0.40/min … yank at
  one report: p50 69.1 u max 349.9 u; 0 firing(s) would clear the hard bar"*. **OBSERVED.**

### 4.2 CHECKING it — three findings

**(a) The shipped constant and the pricing tool DISAGREE, and nothing reconciles them.**
`authsrv.py` `RESYNC_SEPARATION = 100.0`; `resyncscore.py` `RESYNC_SEPARATION = GATE1_UNITS =
299.332591`, with a paragraph arguing *for* 299.33 and *against* 100. Both files are in the
tree, both justify their number, and the flag will run at 100. Under §3.5's HOLE B, **the
threshold IS the residual snap magnitude**, so this is not a cosmetic disagreement: it is the
difference between a bounded-100 u residual and a bounded-299 u one. Someone has to rule.

**(b) The yank bracket DOES cover the stop regime — and at the stop the true yank is
structurally 0.** Broken out of my pooled replay by report source (**OBSERVED**):

```
0x003D fires 128 : modelled sep p50 152 / p90 512 / max 980 u
                   ONE-REPORT yank p50  94.9 / p90 345.9 / max 836.2 u
0x0047 fires  27 : modelled sep p50 240 / p90 437 / max 521 u
                   ONE-REPORT yank p50   0.0 / p90 100.6 / max 365.5 u
```

The **p50 of exactly 0.0 u on the stop arm** is the point: at a stop the client is standing
on the payload, so the message cannot pull it anywhere. `authsrv.py:15004`'s comment —
*"A stop is the cheapest resync there is: the client is standing still at the point it just
reported, so the rendered copy cannot be yanked at all"* — is **confirmed by measurement**,
not just asserted.

**(c) But the ONE-REPORT arm of the bracket is the wrong instrument in today's regime, and it
inflates the price.** Its definition is *"the client's position at its next report"* — and in
the ~1.8 s `0x003D` chord regime the next report can be a full **512 u chord** away. That is
what produces the 0x003D p50 of 94.9 u and the 836 u tail: those numbers measure how far the
player walked before speaking again, not how far the message moved them. The **ZERO-LATENCY**
arm is exactly 0.0 u by construction (the payload *is* the report just taken), and the true
yank is `288 u/s × (send delay + one-way link latency)` — **sub-unit on loopback, 28.8 u on a
100 ms one-way link**. `RESYNC_MAX_REPORT_AGE`'s own comment already says the age it bounds
*"excludes the client→server leg and the server→client leg"*.

**Conclusion on the bracket:** it covers the stop regime and reports the right answer there
(0.0 u). Its moving-arm figure should not be quoted as a cost without the chord caveat.

### 4.3 The Q10 verdict

**P5 does not clear "the stock game doesn't warp" outright, and it should not be sold as if
it does.** Honest scoring:

* At the **stop** — F35's regime — the yank is 0.0 u measured, and the snap it removes is
  177.4 u measured. **It is a strict improvement with no measured cost.**
* At a **moving** report the yank is latency-bounded, not zero. On loopback that is sub-unit;
  over a real link it is `288 × latency` and the flag has never been run over one.
* The **residual** is HOLE B: any staleness under `RESYNC_SEPARATION` still bakes a real leg
  and still arrives as a snap. At 100 u that residual is a ~100 u snap; at 299.33 u it is a
  ~299 u snap. **That fails a literal reading of Q10.** Driving the residual to zero means
  dropping the threshold toward 1.0 u so that every zero-lead grant takes the short-circuit —
  which converts the flag from "occasional correction" into "a `0x002C` before essentially
  every grant", i.e. Rule C's shape, which `resyncscore.py` measured as **failing its own
  retail control** (C fires 29.41/min on retail vs 7.12/min on ours, ratio 4.13).
* The **refused-report hole** (`_resync_verdict:4045-4059`) is guarded by `pos_rejects`, and
  the guard is correct; it is unexercised in this corpus (0 of 558) so the guard itself is
  untested against live traffic.

**The defensible framing for the owner: P5 is the first candidate that removes an
*expression* of the staleness (F35, and by §3.3's short-circuit argument the F27/F33 family
too) without introducing a snap of its own — but it converts an unbounded warp into a
threshold-bounded one, and the threshold is currently disputed between two files.**

---

## 5. Q5 — the retail stop-ack, re-derived, and what it actually is

### 5.1 Where "70 of 88" comes from, and its correction — SOURCED

* `studies/movement/FINDINGS.md:1338` (the original): *"ArenaNet answers `0x0047`
  (move-cancel): **70 of 88** replies are a zero-distance `0x0029` whose destination equals
  the position the client just reported"*. Repeated at `authsrv.py:1108` and `:16922`.
* `studies/movement/FINDINGS.md:3782` (the correction, same study): *"Of 114 stops: 98
  (86.0%) answered within 1.0 s, of which exactly **70** land < 1 u from the reported stop
  (`|dest − stop|` p50 **0.000 u**), latency p50 0.034 s. `0x002B` present in 88 (77.2%) …
  `FINDINGS:1338`'s count of 70 is preserved; **its denominator of 88 is corrected to 114**."*

**So "88" was the count of stops carrying a `0x002B` companion, and the two denominators got
crossed.** The follow-on list's "70 of 88" is the stale form. **SOURCED, citation resolves.**

### 5.2 My own re-derivation over the whole live corpus — OBSERVED

Read-only, `cmsgstream.timed()` over all 22 stamps in `vault/captures/live/`, player agent id
resolved from each connection's own s2c `0x0037` exactly as `resyncscore.retail_tracks` does
(refused if absent — 0 refusals here), 55 judged connections:

```
c2s 0x0047 stops:                          172
  answered by an s2c 0x0029 <= 1.0 s:      147   (85.5%)
  of those, |dest - stop| < 1 u:           134   (77.9% of ALL stops; 91.2% of answered)
  |dest - stop|  p50 0.000 u  p90 0.0 u  max 768.4 u
  answer latency p50 0.034 s  p90 0.139 s
  0x002B inside the stop window:           136
s2c to the PLAYER's own agent, corpus-wide:  0x002C = 5      0x0028 = 105
```

The **shape** reproduces on a larger sample (172 vs 114 stops): retail answers ~86% of stops
within a second and the answer is a zero-distance `0x0029` at the reported stop, p50 exactly
0.000 u, latency p50 0.034 s. My ratio of "all stops" (77.9%) is higher than the study's
61.4% (70/114) because my denominator pools every connection with a resolvable `0x0037`
rather than the adjudicated nine. **All three numbers should be quoted with their
denominator; "70 of 88" should be retired.**

> **The single most useful new number here: retail sends `0x002C` to the player's own agent
> FIVE times in the entire live corpus. Retail does not use the disarm primitive.**

### 5.3 Is retail's stop-ack the same thing as `--stop-echo`? — **YES, mechanically identical**

Both are an s2c `0x0029` naming the player's agent at the client's own reported stop point.
Both therefore go handler `0x005FD890` → wrapper `0x00602A40` → bake `0x005FE950`. **Neither
can disarm** — the only clear is `0x006021E6`, reachable only via `0x006020B0`, and the bake
does not call it. **OBSERVED** (§1.6, §2.1).

The only thing that can differ is the **length of the leg the bake creates**, which is
`|D − sync copy's +0x78|`. Measured, both sides:

| | `|granted point − sync copy|` at the stop-ack | takes the `<=1.0 u` short-circuit |
|---|---|---|
| **retail** (my model, 129 stop-acks) | p10 6.95 · **p50 60.16** · p90 698.7 · max 1572.7 u | **0 of 129 (0.0%)**; ≤10 u 14.7%, ≤100 u 60.5% |
| **ours**, synthesized zero-lead (`grantsim.py`, SOURCED `REALFIX.md:68`) | median **101 / 383 / 208 / 512 u** by capture | **6 of 539 (1.1%)** |
| **ours**, the refuted 2026-08-19 echo at `t=34.912` (UNVERIFIED reconstruction, §5.5) | ~**1,286 u** | no |

So: **retail's stop-ack is not a "park" primitive either — it also bakes a leg. It is just a
short one (p50 60 u = 0.21 s of walk) because retail's copy is near the player.** Ours was
hundreds to a thousand units. **Same mechanism, two orders of magnitude of harm.**

⚠ Caveat on my retail row, stated because it matters: my model glides the copy at 288 u/s
toward each granted destination and parks it, seeded from the first client report. Retail
grants a ~765 u **lead**, so the copy usually never arrives before supersession; the model's
copy position is an approximation. The **direction** of the result (tens of units, not
hundreds) is robust; the exact p50 is not.

### 5.4 So how does retail avoid F35? — my hypothesis test, and it partly FAILS

The orchestrator's hypothesis was *"retail's copy is never stale enough to have a far armed
destination, because it re-grants every ~0.5 s"*. I tested it directly.

**Retail's inter-grant cadence, mine — OBSERVED:**
```
player-agent 0x0029 gaps: n = 3,608   p10 0.083  p50 0.489  p90 1.590  max 52.81 s (mean 1.011)
  > 1.0 s: 645 (17.9%)      > 1.8 s: 175 (4.9%)
```
This reproduces `authsrv.py:1152`'s *"median inter-grant gap for the player is 0.492 s"* to
0.003 s. **SOURCED claim independently OBSERVED.**

**But arms DO mature — OBSERVED:**
```
retail player grants modelled: 3,669
  SUPERSEDED before the arm matured: 3,247 (88.5%)
  arm MATURED (an arrival fired):      422 (11.5%)
  at a matured arrival, |dest - the client's last report|: p50 56.2  p90 767.6  max 5,740.3 u
  client silence at that instant:      p50 0.42  p90 3.57  max 21.61 s
  "F35-shaped" (>=100 u AND >=0.5 s of client silence): 141 (3.84% of all grants)
```

**So the hypothesis as stated is REFUTED: retail does leave arms to mature, ~11.5% of the
time, and 3.84% of its grants are F35-shaped by a crude separation-and-silence criterion.**
Retail's protection is therefore **not** "the arm never matures".

**What it actually is (UNVERIFIED, but it follows from §1.7):** an arrival is only a
*discontinuity* when the copy's dead reckoning has diverged from the `(+0x48, +0x9c)` pair —
the client asserts as much at `0x006002FD` (assert `0x486`: the reckoned point must already
be at the target when the tick fires). Retail's destination is the client's **own proposed
endpoint, ahead of the player**, so the copy reckons toward a point the player is also
walking toward and the arrival lands where the reckoning already is. Our zero-lead
destination is where the player **was**, so the arrival pulls **backward** over the whole
report-overrun. **The sign of the lead, not the cadence, is the discriminator.** Retail's
0.489 s cadence then does a second job: it keeps the overrun small even when the sign is
briefly wrong.

### 5.5 Reconciling the 2026-08-19 `--stop-echo` refutation — the reconstruction

**OBSERVED** from `vault/captures/gamesrv/authsrv-20260819T134827-c1.jsonl`:

```
t=25.052 REPORT 0x0047 stop at (9143.8, 9142.1)
t=25.052 SENT 0x29  STOP ECHO at (9144,9142)
t=25.053 SENT 0x2b  AGENT_UPDATE_SPEED(player, 1.0)
t=25.053 SENT 0x29  AGENT_MOVE_TO_POINT(11010,5471 on plane 0->18, clear line)   <- 4,118 u
t=30.208 .. 34.846  fifteen 0x003D reports, all accepted, walking toward the grant then milling
t=34.912 REPORT 0x0047 stop at (9631.5, 7616.8)
t=34.912 SENT 0x29  STOP ECHO at (9631,7617)          <- the LAST thing on the wire
         (the tape runs on to t=46.648 with no further sends and no further reports)
```

Two things this settles outright:

* **The first echo was superseded 1 ms later** by the click grant — so that echo cannot be
  the "second destination".
* **The warp window (t≈39.4) is genuinely wire-silent**: the capture covers it and holds
  nothing. So the operator's account is the only evidence, exactly as the flag block says.

**UNVERIFIED reconstruction, from the binary + the geometry.** At `t=34.912` the sync copy
had been gliding the 4,118 u leg for 9.86 s ⇒ ~2,840 u along the unit vector
`(0.4531, −0.8914)` ⇒ ≈ `(10431, 6610)`. The echo's `D = (9631, 7617)`. The bake settles
`+0x78` to `(10431, 6610)`, so `|d| ≈ hypot(−800, +1007) ≈ 1,286 u` ⇒ **full bake**, arrival
armed at ≈ `t=39.38`, velocity aimed **back** toward the player. The reseed `0x006022B0`
then hard-copies SYNC onto ASYNC and the rendered body appears out at ~`(10431,6610)` —
"the bridge" — after which it walks back toward `(9631,7617)`, which is *"where the echo had
just planted a destination"*, exactly as the operator described.

**One destination, overwritten as the binary says, and then WALKED from 1,286 u away.** The
"it ADDS a SECOND one" sentence describes the *symptom* correctly and the *mechanism*
wrongly. Note this is the same failure mode the removed `0x002C` build had —
*"not a snap, a WALK"* — arriving through a `0x0029` instead.

**Therefore the `--stop-echo` refutation does NOT transfer to `--resync`.** They share a
payload and nothing else: `0x0029` re-aims and makes the copy walk; `0x002C` SetPositions and
disarms. The refutation is a refutation of *baking a leg from a far copy*, which is precisely
what `0x002C` does not do.

---

## 6. Corrections this note asks the study to absorb

1. `authsrv.py:1149` — *"`agent+0x48` … is set once when a grant lands and is NEVER
   re-armed"* is **false**. Both bake arms write it, on every grant. (§2)
2. The 2026-08-19 *"it adds a SECOND one"* mechanism sentence is **unsupportable**; the
   symptom is explained by a full-bake leg from a far copy. (§4, §5.5)
3. `PROBE-GATEFIRE.md:748` and `resyncscore.py:31` — *"our server has sent `0x002C` zero
   times"* is **stale** since `--cast-stop=pin` shipped. Two are in
   `authsrv-20260825T140517-c1.jsonl`. (§1.8)
4. "70 of **88**" should be "70 of **114**" (the study's own correction), or my larger
   re-derivation **134 of 172**. (§5.1, §5.2)
5. The orchestrator's *"writes `+0x9c` (syncPoint) at `0x0060216D`"* should read *"erases
   `+0x9c` to the `+inf` sentinel at `0x0060216D`"*. (§1.3)
6. `RESYNC_SEPARATION` is **100.0** in `authsrv.py` and **299.332591** in `resyncscore.py`,
   with the latter arguing explicitly against the former. Unreconciled. (§4.2a)
7. The flag's own projected rate (*25.4/min, 42.2% of reports*) over-states today's build by
   ~4.5× — measured 5.60/min, 27.8%. (§3.6)

---

## 7. WHAT WOULD REFUTE THIS

* **§1 (the disarm) is refuted if** anyone finds a `+0x48` store reached through a biased
  `this` pointer at a displacement other than `0x48` — `codescan`'s named blind spot. I ran
  the check its footer prescribes at ±8 (§1.6) and every row there is its own field on the
  agent base, but the encoding classes the footer says nothing anchored can reach
  (`mov eax,0x48` + `add`, or a two-step address) remain genuinely unsearchable. A hook-based
  watchpoint on `+0x48` is the only thing that would settle it.
* **§1 is also refuted if** `0x0070A150` (the point predicate at `0x006021B2`) can be shown to
  throw or long-jump rather than return 0/1, since that is the only call between the `+0x78`
  write and the `+0x48` clear.
* **§1.8 is refuted if** the `t=52.581` `0x002C` and the movetap L257→L259 transition can be
  shown to be different events — e.g. if the ~1030 ms clock offset I derived is wrong. It is
  checkable: I pinned it on two independent grant/target coincidences agreeing to 1 ms, and a
  third would settle it.
* **§2 is refuted if** any `0x0029`/`0x002A` path can be found that reaches the bake
  `0x005FE950` **without** passing `0x00602A40`. All five callers are accounted for in
  §2.2a and none of the other four is reachable from a movement message with a fresh
  destination — but that inventory is `--xrefs`, which by its own footer cannot see indirect
  or vtable calls. A vtable dispatch into `0x005FE950` would reopen this.
* **§3 is refuted if** a run with `--resync` shows a `resync` record with `reason != "resync"`
  at the F35 stop — my replay is a reimplementation, not the shipped code path.
* **§4 is refuted if** an owner-driven run shows a rendered-copy displacement bracketing a
  fired `0x002C` at a **stop** greater than a couple of units. My prediction there is 0.0 u.
* **§5.4 is refuted if** the retail arm-maturation model is shown to be wrong in direction
  (e.g. retail's copy is actually re-seeded by something I did not model, making the 11.5%
  spurious). My model is crude and I say so; the 88.5% supersession figure is the robust half.

---

## 8. REGISTERED PREDICTIONS FOR AN OWNER-DRIVEN `--resync` RUN

Stated before any run, in measurable terms, with the instrument for each.

**Setup:** shipped defaults (`--zero-lead`, `--grant-suppress`, `--cast-stop=pin`) **plus
`--resync`**, one movetap tape and one gamesrv tape on the same clock. The rep that matters
is F35's own, and it needs **no cast**: *walk a straight leg of at least one full `0x003D`
chord (~512 u, ~1.8 s), release, and stand still for 2 s.* Repeat 5×. Then a control arm with
`--no-resync`, same input.

1. **P1 — F35 goes to zero.** With `--resync`, in every rep, `movetap` shows **no `async_at`
   step > 5 u** in the 2 s after the stop. Control arm reproduces the snap:
   at least 2 of 5 reps show an `async_at` step of 100-500 u landing bit-identically on the
   last `ZERO LEAD` grant point, with `target` flipping to `[inf,inf]` in the same row.
   *(Refuted if the treated arm snaps anyway — then the disarm decode is wrong, or the fire
   did not happen; read `resync` records for `fired`/`reason` first.)*
2. **P2 — the stop fire happens and its telemetry says so.** Each rep's gamesrv tape holds a
   `resync` record at the `0x0047` with `fired=true`, `reason="resync"`, `age < 0.05 s`, and
   `separation` between **100 and 550 u** (F35's measured 177.4 u sits inside that).
   *(Refuted if `reason` is `stale`, `rate-limited` or `no-sync-model` — HOLE D in
   particular would show as `no-sync-model` on every record, which is a build bug, not a
   result.)*
3. **P3 — the stop yank is zero.** For every fired `0x002C` at a `0x0047`, the `async_at`
   displacement in the 200 ms **after** the send is **≤ 2 u**, and its median over all such
   fires is **0.0 u**. *(This is the Q10 bar for the stop arm. Refuted by any backward step.)*
4. **P4 — the zero-lead grant becomes a short-circuit.** After a fire on a `0x003D`, the very
   next `ZERO LEAD` grant produces a movetap row with `stop(+0x48) == updated(+0x58) + 1`
   (the `0x005FEAD6` arm), `point == target`, and **zero** displacement on the following row —
   the L216 shape. Expect this on **the majority** of post-fire grants. *(Refuted if `+0x48`
   comes back as `+0x58 + k` for k >> 1: then the resync did not land before the grant, and
   the two call sites' ordering needs re-checking.)*
5. **P5 — the residual is bounded by the threshold, and is visible.** Refused
   (`in-agreement`) reports still arm real arrivals. Expect **non-zero** `async_at` steps in
   the treated arm, all of them **< `RESYNC_SEPARATION`** (i.e. < 100 u at today's constant).
   *(This is the prediction that would keep P5 short of Q10. If steps > 100 u appear in the
   treated arm outside a fire window, my HOLE-B model is wrong and the residual is not
   threshold-bounded.)*
6. **P6 — the fire rate.** Pooled over the run: **4-10 fires/min** and **20-35% of position
   reports**, not the 25.4/min the flag block projects. *(A rate near 25/min means the
   shipped-default regime is not what I replayed.)*
7. **P7 — no self-minted hard jumps.** `movesync`'s hard bar (`HARD_JUMP_UNITS = 520`) is
   cleared by **zero** fired `0x002C`s. *(A fix that mints more than it prevents is refused
   by its own scoreboard — `resyncscore.py`'s rule.)*
8. **P8 — the negative control that makes the whole thing readable.** Run one rep with
   `--resync` and a deliberately raised `RESYNC_SEPARATION` (e.g. 2000 u) so nothing fires.
   The snap must return. If it does not, the treated arm's zero was not caused by the resync.

**Decision shape:** P1+P2+P3 all land ⇒ F35 is closed by P5 and the stop arm meets Q10.
P5 (the prediction) shows a bounded residual ⇒ the owner is choosing a *threshold*, not a
*fix*, and §4.2a's 100-vs-299.33 disagreement has to be ruled before shipping. Any of P1-P3
fails ⇒ the failure names its own door: `reason` on the record, then the movetap `target`
field, then `+0x48` vs `+0x58`.
