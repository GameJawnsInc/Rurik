# Refutation lens: REACHABILITY AND CONTROL FLOW

Adversarial pass on the claim that an s2c 0x002C AGENT_UPDATE_POSITION disarms a pending
+0x48 arrival teleport, while an s2c 0x0029 AGENT_MOVE_TO_POINT can only arm/re-arm.

All binary work is against the **pinned pristine build-38797 client**
(`C:\gd\Rurik\vault\client\2026-07-29_221c13772c7a\Gw.exe`; `pinned.py` reports
PRISTINE on every codescan invocation). **No client, harness or session.py was
launched.** Static disassembly + existing vault captures only.

Tags: **OBSERVED** = I measured it here. **SOURCED** = a doc/binary says it and I
verified the citation resolves. **UNVERIFIED** = I am reasoning.

---

## 0. Verdict

**REFUTED as a whole. The 0x002C half is confirmed; the 0x0029 half is false; the
prediction that follows does not follow.**

| Sub-claim | Status |
|---|---|
| A 0x002C that finds `+0x48 != 0` routes through 0x006020B0, which clears +0x48 at 0x006021E6 | **CONFIRMED — OBSERVED twice**, statically (no branch/assert/early-return can skip it) and empirically (3 of 3 armed cases in the movetap corpus disarmed within ~80 ms) |
| 0x006020B0 overwrites +0x9c at 0x0060216D | **CONFIRMED and UNDERSTATED.** It does not write the new position there — it **parks +0x88/+0x8c/+0x9c/+0xa0 to the +inf sentinel at 0x00948654** and zeroes +0x90/+0x94/+0x98/+0xa4/+0xa8 |
| 0x0029 "reaches only the grant bake ... has no path to the clear" | **REFUTED — OBSERVED.** 0x0029 → 0x00602A40 → (0x00602AF8) → 0x006011F0, which contains two direct `call 0x6020b0` sites at 0x00601817 and 0x00601899 |
| 0x0029 "can only ARM or RE-ARM a destination, never disarm a stale far one" | **REFUTED — OBSERVED.** 0x00602A40 writes +0x88..+0xa8 wholesale from its own argument (0x00602A84..0x00602ACD, +0x9c at 0x00602AB0), unconditionally. It **REPLACES** the pending destination |
| This explains the 2026-08-19 --stop-echo result ("the echo ADDS a second destination rather than overwrite the pending one") | **REFUTED.** The binary says the echo overwrites +0x9c. Whatever the operator saw, this mechanism does not explain it |
| Therefore --resync would **zero** F35's arrival-teleport warp | **DOES NOT FOLLOW — OBSERVED.** All 6 aligned 0x002C sends produced an instantaneous rendered-position jump of **100.5 – 523.0 u**. The disarm *is* a snap. It trades F35's warp for its own |
| (brief premise) --resync was "built, NEVER RUN" | **FALSE — OBSERVED.** `gamesrv/authsrv-20260820T182119-c1.jsonl` holds **18 rows labelled `RESYNC 0x002C ...`** |

---

## 1. The arrival primitive 0x006020B0 — the clear cannot be skipped

`python toolkit/clientscan/codescan.py --dis 0x006020B0 --count 120`

### 1a. The entry guard is a non-fatal assert, not an early return (OBSERVED)

```
006020B6  d94508           fld dword ptr [ebp + 8]      ; arg.x
006020B9  d90554869400     fld dword ptr [0x948654]     ; SENTINEL
006020BF  dde1             fucom st(1)
006020CD  f6c444           test ah, 0x44
006020D0  7a22             jp 0x6020f4                  ; x != SENTINEL -> skip, no assert
006020D2  d9450c           fld dword ptr [ebp + 0xc]    ; arg.y
006020DC  7a18             jp 0x6020f6                  ; y != SENTINEL -> skip, no assert
006020DE  6812080000       push 0x812                   ; assert line 2066
006020ED  e8ce5ae8ff       call 0x487bc0
006020F2  eb02             jmp 0x6020f6                 ; falls through -- no return
006020F4  ddd8             fstp st(0)
006020F6  8bcb             mov ecx, ebx                 ; <-- all three paths converge
```

MSVC `fucom / fnstsw / test ah,0x44 / jp`: `jp` is taken on NOT-EQUAL (equal sets
C3 only → `ah&0x44 == 0x40`, one bit, odd parity, PF=0). The assert therefore
fires only when **both** components equal the sentinel. All three paths converge
on 0x006020F6. **This guard cannot skip the clear.**

### 1b. Exactly one branch between entry and the clear, and it lands above it (OBSERVED)

```
006021BC  7417             je 0x6021d5      ; skips only the +0x68..+0x74 copy
...
006021D5  8b7b28           mov edi, dword ptr [ebx + 0x28]
006021D8  c7433c00000000   mov dword ptr [ebx + 0x3c], 0
006021DF  c7434000000000   mov dword ptr [ebx + 0x40], 0
006021E6  c7434800000000   mov dword ptr [ebx + 0x48], 0    <-- THE CLEAR
```

The `je` target (0x006021D5) is **above** 0x006021E6, so both arms reach the
clear. The two intervening calls (0x005FF880 at 0x006020F8, 0x0070A150 at
0x006021B2) have their result consumed by `test eax,eax` at 0x006021BA, which is
only meaningful for a returning callee.

**On the assigned angle the claim SURVIVES here: once 0x006020B0 is entered, the
+0x48 clear is unconditionally reached.**

### 1c. What 0x0060216D actually stores — the sentinel, not the new position (OBSERVED)

```
0060211D  d90554869400     fld dword ptr [0x948654]          ; SENTINEL
00602155  898388000000     mov dword ptr [ebx + 0x88], eax   ; +0x88 = SENTINEL
00602164  89838c000000     mov dword ptr [ebx + 0x8c], eax   ; +0x8c = SENTINEL
0060216D  89839c000000     mov dword ptr [ebx + 0x9c], eax   ; +0x9c = SENTINEL
00602179  8983a0000000     mov dword ptr [ebx + 0xa0], eax   ; +0xa0 = SENTINEL
0060217F / 00602189 / 00602194 / 0060219E / 006021A8         ; +0x90/+0xa4/+0x94/+0x98/+0xa8 = 0
```

The new position goes to +0x78..+0x84 (`esi = ebx+0x78`, stores at 0x00602132,
0x0060213A, 0x00602143, 0x0060214F).

**The sentinel at 0x00948654 is `0x7f800000` = +inf** (read out of the PE:
`pefile.get_data(0x948654 - 0x400000, 8)` → `0000807f...`). **OBSERVED.**
This is confirmed independently from the capture side: every parked movetap row
prints `"target": [Infinity, Infinity, 0], "target_invalid": true`.

So the claim's "overwrites +0x9c" is *weaker* than the truth: it **parks the
destination to +inf**. Here the claim is understated, not wrong.

---

## 2. `0x487bc0` RETURNS — the asserts protect nothing (OBSERVED)

```
00487C11  e8fa050000       call 0x488210            ; the report
00487C19  8b4dfc           mov ecx, dword ptr [ebp - 4]
00487C1E  e8866b1200       call 0x5ae7a9            ; __security_check_cookie
00487C26  c20400           ret 4                    ; RETURNS (stdcall, 1 arg)
```

Stack cookie + `__security_check_cookie` epilogue + `ret 4`. A never-returning
function does not get a cookie epilogue. Whether the callee 0x00488210 can itself
terminate in some configuration is **UNVERIFIED** — I did not disassemble it —
but 0x487bc0 is compiled as a returning function and every call site in this arc
is followed by fall-through code that consumes the post-assert state.

---

## 3. The 0x002C handler 0x005FDA50 — both arms reached, no early return (OBSERVED)

Handler resolved authoritatively, not guessed:
`python toolkit/clientscan/msghandler.py 0x002C` → table 0x00a52d70 [RECV],
`handler 0x005fda50`. Body is 0x005FDA50..0x005FDB64 (`ret` at 0x005FDB64,
`int3` padding after) — short and fully linear.

```
005FDA78  e8f3840000       call 0x605f70     ; AgTrack::Clear, BEFORE both SetPositions
005FDA83  3b86f0000000     cmp eax, [esi + 0xf0]     ; id < sync_count?
005FDA89  7214             jb 0x5fda9f
005FDA9A  e821a1e8ff       call 0x487bc0             ; assert 587 -- RETURNS
005FDAA2  8b86e8000000     mov eax, [esi + 0xe8]     ; SYNC array
005FDAA8  8b0488           mov eax, [eax + ecx*4]    ; OOB read if the assert returned
005FDAAE  85c0             test eax, eax
005FDAB0  7514             jne 0x5fdac6
005FDAC1  e8faa0e8ff       call 0x487bc0             ; assert 579 -- RETURNS
005FDAC6  8b07             mov eax, [edi]            ; proceeds with eax possibly NULL
005FDAE5  e836500000       call 0x602b20             ; SetPosition, SYNC
005FDAED  3bbe54010000     cmp edi, [esi + 0x154]    ; id < async_count?
005FDB04  e8b7a0e8ff       call 0x487bc0             ; assert 587
005FDB09  8b864c010000     mov eax, [esi + 0x14c]    ; ASYNC array
005FDB25  e896a0e8ff       call 0x487bc0             ; assert 584
005FDB49  e8d24f0000       call 0x602b20             ; SetPosition, ASYNC
005FDB54  e8375e0000       call 0x603990
005FDB64  c3               ret
```

Answers to the assigned questions:

* **The bounds compare at 0x005FDA83 and the null test at 0x005FDAAE do not
  abort.** They call a returning reporter (§2) and then dereference anyway.
  **The handler has no early-return path at all.**
* **The ASYNC arm is reached unconditionally after the SYNC arm.** Every branch
  between 0x005FDAE5 and 0x005FDB49 is an assert-skip that jumps forward past the
  assert and rejoins. "Does the sync arm taking an unusual branch skip the async
  arm?" — **no, because the sync arm has no unusual branch to take.**
* **The failure mode is a crash, not a silent skip.** If 0x005FDAAE fires and
  0x487bc0 returns, `ecx = 0` reaches 0x00602B20 → `mov ebx, ecx` (0x00602B29) →
  `cmp dword ptr [ebx + 0x48], 0` (0x00602B44): a read at linear address 0x48.
  Access violation, not a missed disarm. (Crash itself UNVERIFIED — nothing was
  run.)

**RETRACTION.** An earlier draft of this note flagged the brief's "calls
AgTrack::Clear then SetPositions BOTH copies" as contradicted, on the grounds
that 0x00603990 is called at 0x005FDB4E *after* both SetPositions. That was my
error: authsrv.py:3833 identifies AgTrack::Clear as **0x00605F70**, called at
**0x005FDA78 — before both**. The brief is correct and my flag was wrong. What
0x00603990 is remains **UNVERIFIED**; it is a different call and changes nothing.

---

## 4. 0x00602B20's parked branch — real, but empirically vacuous

```
00602B44  837b4800         cmp dword ptr [ebx + 0x48], 0
00602B57  7422             je 0x602b7b        ; +0x48 == 0 -> PARKED
00602B74  e837f5ffff       call 0x6020b0      ; ARMED -> the clear
00602B79  eb4e             jmp 0x602bc9
00602B7B  8907             mov dword ptr [edi], eax   ; PARKED: +0x78..+0x84 only
```

**The parked branch writes +0x78..+0x84 and nothing in the +0x88..+0xa8 block.**
Verified against the `--field 0x9c --in AgAgent` census: the only +0x9c stores in
the module are 0x005FE507, 0x005FEC52, 0x0060216D and 0x00602AB0, none inside
0x00602B7B..0x00602BC9.

So the assigned worry is well-formed: **if a state exists with a live destination
in +0x9c and +0x48 == 0**, a 0x002C takes the parked branch and disarms nothing.

**MEASURED, and the state does not occur.** Across all 32 movetap captures,
42,784 `kind:"sample"` rows (all agent 1), classifying each row by
`stop` (= +0x48, movetap.py:459) and finiteness of `target` (= +0x9C,
movetap.py:465):

| | `target` finite | `target` == [inf,inf] |
|---|---|---|
| **`stop != 0` (armed)** | **13,778** | **0** |
| **`stop == 0` (parked)** | **0** | **29,006** |

**Both off-diagonal cells are empty.** +0x48 and +0x9c are perfectly coupled in
the observed corpus.

*Positive control on that search*, because a clean zero is exactly the shape a
broken filter produces: the same loop finds **1,850 distinct non-zero `stop`
values**, **1,842 distinct finite `target` points**, armed rows in **28 of 32**
captures, and **1,222 armed↔parked transitions**. The loop can see variety; the
zero is real.

*Caveat*: the poll is 50 Hz, so a coupled-write window shorter than ~20 ms would
be invisible. That is exactly the window 0x00602A40 has — 0x00602AB0 (+0x9c) and
0x00602AD3 (the call that arms +0x48) are 0x23 bytes apart with no branch
between them, so the two are written in the same instruction stream.

**So the parked-branch concern is real in the code and vacuous in practice.**
This part of the claim SURVIVES.

---

## 5. THE REFUTATION — 0x0029 both overwrites the destination AND reaches the clear

`msghandler.py 0x0029` → table 0x00a52d70 [RECV], **handler 0x005fd890**.
That handler is straight-line to a single call:

```
005FD8B8  7214             jb 0x5fd8ce        ; assert-skip only
005FD8D9  7514             jne 0x5fd8ef       ; assert-skip only
005FD8F4  ff7714           push dword ptr [edi + 0x14]
005FD906  6a00             push 0
005FD908  50               push eax                    ; &position
005FD913  e828510000       call 0x602a40      ; UNCONDITIONAL
```

### 5a. 0x00602A40 REPLACES the destination (OBSERVED)

```
00602A40  55               push ebp                          ; __thiscall, ret 0xc
00602A48  f7432000000200   test dword ptr [ebx + 0x20], 0x20000
00602A4F  7514             jne 0x602a65
00602A60  e85b51e8ff       call 0x487bc0                     ; assert 2334 -- returns
00602A65  816320fffff7ff   and dword ptr [ebx + 0x20], 0xfff7ffff
00602A6F  83f8ff           cmp eax, -1
00602A72  7406             je 0x602a7a                       ; skips ONLY the +0x80 write
00602A7A  8b4d08           mov ecx, dword ptr [ebp + 8]      ; arg0 = &position
00602A84  898388000000     mov dword ptr [ebx + 0x88], eax   ; +0x88 = arg.x
00602A8D  89838c000000     mov dword ptr [ebx + 0x8c], eax   ; +0x8c = arg.y
00602A96  898390000000     mov dword ptr [ebx + 0x90], eax
00602A9F  898394000000     mov dword ptr [ebx + 0x94], eax
00602AA8  898398000000     mov dword ptr [ebx + 0x98], eax
00602AB0  89839c000000     mov dword ptr [ebx + 0x9c], eax   ; +0x9c = arg.x   <<<<
00602AB9  8983a0000000     mov dword ptr [ebx + 0xa0], eax   ; +0xa0 = arg.y
00602AC2  8983a4000000     mov dword ptr [ebx + 0xa4], eax
00602ACD  8983a8000000     mov dword ptr [ebx + 0xa8], eax
00602AD3  e878beffff       call 0x5fe950                     ; the +0x48 arm
00602AF8  e8f3e6ffff       call 0x6011f0                     ; <<< see 5c
```

From 0x00602A7A to 0x00602AD3 **there is no branch**. Every accepted 0x0029
stamps the entire +0x88..+0xa8 block with the granted point. There is exactly ONE
destination pair per agent (+0x9c/+0xa0) and ONE arrival tick (+0x48).
**This is replace, not append.**

The claim's "never disarm a stale far one" fails on its own terms: a re-arm to a
near point *is* the removal of the stale far one. And the "**adds a SECOND
one**" reading of the 2026-08-19 --stop-echo refutation — repeated verbatim in
`toolkit/authsrv/authsrv.py:15002` ("measured, added a second one") — **cannot be
produced by this mechanism.** Whatever the operator saw, it was not
"0x0029 can't overwrite +0x9c".

*(One UNVERIFIED hypothesis worth someone else's time: +0x88/+0x8c is
`m_segmentPoint` and +0x9c/+0xa0 is `m_targetPoint` — genuinely **two** point
pairs, which 0x00602A40 happens to set identically but which 0x005FE950's
long-distance branch at 0x005FEAE3 writes separately (+0x88 only, from the
requested point, leaving +0x9c untouched). A "second destination" could live in
that split. I did not chase it.)*

### 5b. Neither arm store can ever write zero (OBSERVED — this part of the brief holds)

Function start confirmed: nearest `int3` padding before 0x005FEA80 is at
0x005FE950, and 0x005FE950 has a `push ebp` prologue.

```
005FEAAF  8b4508  mov eax, [ebp+8] ; 005FEAB2 inc eax ; 005FEAB3 cmp eax,1
005FEAB6  7305    jae 0x5feabd     ; 005FEAB8 mov eax,1        <- floor of 1
005FEAD6  894648  mov dword ptr [esi + 0x48], eax

005FEB35  034d08  add ecx, [ebp+8] ; 005FEB38 cmp ecx,1
005FEB3B  7305    jae 0x5feb42     ; 005FEB3D mov ecx,1        <- floor of 1
005FEB46  894e48  mov dword ptr [esi + 0x48], ecx
```

`jae` is unsigned, so the only value that could reach either store as 0 would
have to satisfy `unsigned(v) >= 1` and equal 0 — impossible. **Confirmed: neither
0x005FEAD6 nor 0x005FEB46 can act as a clear.**

*Not confirmed*: the brief's fourth site, `0x005FE531 mov dword ptr [ebx+0x48],
esi`, is a **register** store and I did not prove `esi != 0` there. It sits
0x2a bytes after 0x005FE507, which writes a real +0x9c from `[ebp+0x58]`. So
"0x006021E6 is the ONLY clear" is **NOT ESTABLISHED**. The §4 corpus measurement
makes it moot for behaviour, but the census claim as stated is unproven — and the
tool's own footer names a blind spot (a field reached through a **biased `this`**)
that no anchored scan can close.

### 5c. 0x0029 HAS a call path to the +0x48 clear (OBSERVED)

`--xrefs 0x006020B0` → 7 direct call sites: 0x0060032E, 0x00600A91, 0x00601817,
0x00601899, 0x0060221E, 0x006025A6, 0x00602B74.

**0x00601817 and 0x00601899 are inside the function that begins at 0x006011F0** —
and **0x00602A40 calls 0x006011F0 at 0x00602AF8**.

That 0x006011F0..0x00601899 is one function, not two, is established three ways
(OBSERVED):
* **No `int3` padding separates them.** A naive byte scan reports "runs" at
  0x0060123B, 0x00601608, 0x006017FE, 0x00601823, 0x00601882, 0x006018A0, but
  each is length 1 and each is a 0xCC *inside* an instruction — 0x006017FE is the
  ModRM byte of `8bcc mov ecx, esp` at 0x006017FD; 0x00601823 is a byte of
  `c745cc01000000` at 0x00601821. **There is no real padding.**
* **Control flow crosses.** `00601828 e9d5010000 jmp 0x601a02` and
  `006018A7 e956010000 jmp 0x601a02` both jump forward past 0x00601899 into a
  common epilogue.
* **The frame is shared.** 0x006011F3 allocates `sub esp, 0xbc`; 0x006018C9 uses
  `lea eax, [ebp - 0xbc]`. Argument slots agree: `[ebp+0x10]` is read at
  0x006011FA and again at 0x006018AF; `[ebp+0xc]` at 0x006017F7, 0x00601854,
  0x006018BD — matching the 4 args pushed at 0x00602AF0..0x00602AF5.

The nearer call site's guard is readable:

```
0060182D  d94678           fld dword ptr [esi + 0x78]      ; current position x
00601830  d9869c000000     fld dword ptr [esi + 0x9c]      ; destination x
0060183D  7a6d             jp 0x6018ac                     ; NOT equal -> away
0060183F  d9467c           fld dword ptr [esi + 0x7c]
00601842  d986a0000000     fld dword ptr [esi + 0xa0]
0060184F  7a5b             jp 0x6018ac                     ; NOT equal -> away
...
00601899  e812080000       call 0x6020b0                   ; position == destination -> ARRIVE NOW
```

So the client has an **"already at the destination" fast path that calls the
arrival primitive immediately**, and it is reachable from the 0x0029 arm in the
same handler invocation. Note that 0x005FE950's short-distance branch (taken when
the FPU compare at 0x005FEA8B says `d <= 1.0`) writes `+0x78..+0x84 = the
requested point` at 0x005FEA92 — which makes the equality at 0x0060182D exact for
a zero-distance grant. **A stop-echo should therefore have self-disarmed inside
its own handler.** It reportedly did not.

**I could NOT determine** which branch 0x006011F0 actually takes at runtime for a
given grant — that needs values I have no way to obtain statically, and I am not
permitted to run anything. But the *reachability* claim under attack is refuted
by the CFG alone: **the path exists.** "It has no path to the clear" is false.

---

## 6. The prediction fails for a different reason: the disarm is itself a warp

`--resync` sends **0x002C** (authsrv.py:3801, "THE RESYNC SENDER -- GAME_SMSG
0x002C AGENT_UPDATE_POSITION"), fired only from `_maybe_resync` (:4118), called
from the two client-position arms (:13904, :15004) "and from nowhere else".
Citations verified.

### 6a. Premise correction: --resync HAS been run (OBSERVED)

The brief says "REALFIX-P5, built, **NEVER RUN**". Scanning all 1,167 gamesrv
`.jsonl` captures for `opcode == 44` finds **24 rows in 3 files** (positive
control: the same scan finds 4,828 rows of `opcode == 41` / 0x0029 across 134
files, plus 9,423 × 0x003D and 1,057 × 0x0047):

* `authsrv-20260820T182119-c1.jsonl` — **18 rows**, labels of the form
  `"RESYNC 0x002C at (10009,8045) plane 0 -- the CLIENT's own report, 0 ms old,
  closing a modelled 186 u ..."`. That is the --resync sender's own label format.
  **--resync ran on 2026-08-20 and fired 18 times.** There is no movetap capture
  for 20260820, so its effect on +0x48/+0x9c was never observed; on the wire the
  client's next 0x003D reports continue smoothly forward from each resync point.
* `authsrv-20260825T130906-c1.jsonl` (4) and `authsrv-20260825T140517-c1.jsonl`
  (2) — labels `"CAST-STOP PIN 0x002C at (...) -- reckoned [cancelwalk R10]"`.
  **The 0x002C primitive is in production today under the shipped
  `--cast-stop=pin` default.**

### 6b. Direct empirical test of the disarm — it works (OBSERVED)

The two 2026-08-25 gamesrv captures have near-simultaneous movetap captures
(`movetap-20260825T130918`, `movetap-20260825T140548`). Aligning the sends'
`wall_unix` against the movetap `t`:

```
0x002C sent 1787677771.565 -> (-5298,-2401)          [gamesrv 130906 seq 620]
  dt=-0.018  stop=23805  target=(-5508.5,-2333.6)  live=(-5517.6,-2334.9)
  dt=+0.059  stop=0      target=INF                live=(-5298.1,-2400.7)

0x002C sent 1787681169.976 -> (-5101,-2446)          [gamesrv 140517 seq 1194]
  dt=-0.027  stop=52911  target=(-5148.8,-2442.4)  live=(-5616.7,-2404.4)
  dt=+0.053  stop=0      target=INF                live=(-5100.8,-2446.3)

0x002C sent 1787681194.417 -> (-3494,-2526)          [gamesrv 140517 seq 1719]
  dt=+0.003  stop=76963  target=(-3560.8,-2522.7)  live=(-4016.1,-2500.1)
  dt=+0.084  stop=0      target=INF                live=(-3493.7,-2526.1)
```

**3 of 3 sends that found an armed +0x48 cleared it, and parked `target` to
[inf,inf], within one poll interval (~80 ms).** Exactly what 0x006021E6 +
0x0060216D predict. The remaining 3 sends found `+0x48` already 0 (in two of them
the arrival had fired naturally 27 ms and 109 ms earlier) and took the parked
branch, consistent with §4.

*Retraction of my own near-miss*: a first pass reported the third case as a
**counter-example** (`stop 76963 → 76963`) because it took the first sample after
the send timestamp, at dt=+0.003 — before the packet was applied. Widening the
window shows the disarm at dt=+0.084. There is no counter-example.

### 6c. But every 0x002C snapped the rendered position (OBSERVED)

`live` is the dead-reckoned, rendered position (movetap.py:46,
`live = +0x78 + vel*(now - +0x58)`). Jump across each send, last sample before
vs first sample after the packet lands:

| send | armed before? | pending dest | **live jump** |
|---|---|---|---|
| 130906 seq 620 | yes (23805) | 9.2 u away | **229.1 u** |
| 130906 seq 835 | no | — | **278.8 u** |
| 130906 seq 1052 | no | — | **162.9 u** |
| 130906 seq 1252 | no | — | **100.4 u** |
| 140517 seq 1194 | yes (52911) | 469.4 u away | **517.6 u** |
| 140517 seq 1719 | yes (76963) | 470.3 u away | **523.0 u** |

**Six of six. Every 0x002C produced an instantaneous rendered-position jump
between 100.4 u and 523.0 u.** The disarm is not free — the disarm *is* a snap,
because 0x00602B20 writes +0x78 in both of its branches.

Against PLAN.md Q10 — *"the stock game doesn't warp, i am not going to accept a
fix that still warps"* — **a candidate whose mechanism is "SetPosition both
copies" expresses the staleness as a snap by construction.** That is the owner's
stated failure condition.

Two honest qualifiers, both of which cut in --resync's favour and neither of
which reaches zero:
* These six are `--cast-stop=pin` sends with a **reckoned** payload, not
  --resync's "client's own last accepted report". --resync's payload is bounded
  by `RESYNC_MAX_REPORT_AGE = 100.0/288.0 = 0.347 s`, and authsrv.py:3919 derives
  that bound explicitly *as the harm bound*: "A SetPosition to the client's last
  report **yanks the RENDERED copy backwards** by however far the client has
  walked since that report ... the harm is exactly the client's own 100.0 u
  'close enough' radius." **The sender's own documentation concedes the snap and
  budgets 100 u of it.** Note row 4 above measured 100.4 u — right at that bound.
* Its own pre-registered replay predicts **1,998 fires, 25.4 per minute of span,
  42.2% of reports** (authsrv.py, RESYNC_SEPARATION block). At ~100 u each.

So "--resync would **zero** F35's arrival-teleport warp" is not supported. What
is supported is: *--resync would remove F35's 177.4 u arrival teleport and
substitute a bounded ~100 u snap at ~25/min.* Whether that trade clears Q10 is
the owner's call, not a measurement — but it is a trade, not a zero.

### 6d. A structural gap in the prediction (OBSERVED)

`_maybe_resync` is called only from the 0x003D and 0x0047 arms. The sender's own
note (authsrv.py, RESYNC block, point (c)) states: **"MEASURED, a click-walk
sends no position report for up to 12.9 s, so a server-granted click-walk cannot
be interrupted by this sender."** F35 is described as wire-silent. **A stale far
arm that fires during a report-silent window cannot be disarmed by --resync at
all**, because --resync never fires there. The mechanism is sound; its trigger
does not cover the case.

---

## 7. One more doc/measurement disagreement, recorded because the measurement wins

`toolkit/authsrv/authsrv.py:15003` says:

> "0x002C arms nothing -- 0x00602B20 writes destination = current."

**The conclusion is right and the reason is wrong.** 0x00602B20 never writes
"destination = current":
* the **parked** branch (0x00602B7B..) writes +0x78..+0x84 only and **does not
  touch the destination block at all**;
* the **armed** branch parks +0x9c/+0xa0 to **+inf** via 0x006020B0.

"0x002C arms nothing" is true (no +0x48 store is reachable from it except the
clear), but anyone reasoning forward from the stated reason will get the
+0x9c state wrong.

---

## 8. What I could not determine

1. **Which branch 0x006011F0 takes** for a given grant, hence whether the
   0x0029→clear path in §5c is *executed* or merely *reachable*. Needs runtime
   values; nothing was run.
2. **Whether `esi` can be 0 at 0x005FE531**, hence whether 0x006021E6 is truly
   the only clear (§5b). The §4 corpus measurement makes it behaviourally moot.
3. **Whether 0x00488210 can terminate the process** in some configuration (§2).
   0x00487BC0 itself provably returns.
4. **What 0x00603990 is** (§3).
5. **--resync's own snap magnitude.** The one run that exists (20260820T182119)
   has no concurrent movetap capture, so §6c's numbers come from the
   `--cast-stop=pin` variant with a reckoned payload, not from --resync.

---

## 9. Commands used

```
python toolkit/clientscan/codescan.py --dis 0x006020B0 --count 120
python toolkit/clientscan/codescan.py --dis 0x00602B20 --count 100
python toolkit/clientscan/codescan.py --dis 0x005FDA50 --count 120
python toolkit/clientscan/codescan.py --dis 0x00487BC0 --count 90
python toolkit/clientscan/codescan.py --dis 0x00602A40 --count 90
python toolkit/clientscan/codescan.py --dis 0x005FE950 --count 75
python toolkit/clientscan/codescan.py --dis 0x006011F0 --count 75
python toolkit/clientscan/codescan.py --dis 0x006017C0 --count 60
python toolkit/clientscan/codescan.py --dis 0x0060187C --count 45
python toolkit/clientscan/codescan.py --field 0x48 --in AgAgent
python toolkit/clientscan/codescan.py --field 0x9c --in AgAgent
python toolkit/clientscan/codescan.py --xrefs 0x006020B0
python toolkit/clientscan/codescan.py --xrefs 0x00602A40
python toolkit/clientscan/codescan.py --xrefs 0x005FE950
python toolkit/clientscan/msghandler.py 0x0029 | 0x002A | 0x002B | 0x002C
```
plus ad-hoc read-only Python over `vault/captures/movetap/*.jsonl` (32 files,
42,784 sample rows) and `vault/captures/gamesrv/*.jsonl` (1,167 files).
