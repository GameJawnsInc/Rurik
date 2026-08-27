# LANE A5 — is movehook capturing the RIGHT data, and would the capture answer MOVECODE-P1?

Tree: C:/gd/Rurik/.claude/worktrees/movecode-b2 (verified).
Client: vault/client/2026-07-29_221c13772c7a/Gw.exe, build 38797, imagebase 0x00400000.
All disassembly OBSERVED via `toolkit/clientscan/codescan.py`.

NOTE: `readhook.py` and `test_movehook.py` did not exist in the directory at my first
`ls` and appeared partway through this review — another session is writing here. All
readhook.py line numbers below are from the copy I read.

---

## Q1 — arg2 = [esp+8] at entry vs [ebp+0xc] at 0x005FEA35.  CORRECT. No finding.

Frame arithmetic, OBSERVED:

    005FE950  55      push ebp        <- the 0xCC replaces THIS byte
    005FE951  8bec    mov ebp, esp

At the hit `esp = esp_entry`. After the prologue `ebp = esp_entry - 4`, so

    [ebp+0x00] = saved ebp      = [esp_entry-4]
    [ebp+0x04] = return address = [esp_entry+0]
    [ebp+0x08] = arg1           = [esp_entry+4]
    [ebp+0x0c] = arg2           = [esp_entry+8]
    [ebp+0x10] = arg3           = [esp_entry+12]

`sub esp,0x24` / `push ebx/esi/edi` after 0x005FE951 move esp, never ebp. So
movehook.c:196 `r->arg2 = ((DWORD*)esp)[2]` IS the slot read at
`005FEA35 cmp dword ptr [ebp+0xc], 0`.

I read EVERY instruction in 0x005FE950..0x005FEA35 (four --dis windows). Nothing
writes [ebp+0xc]. The only writes into the frame in that span are
`005FE9D9 mov [ebp-0x14],ecx` and `005FE9F3 mov [ebp+8],eax`.

## Q2 — arg1 = [esp+4] vs [ebp+8] at 0x005FE957.  CORRECT, and the entry hook is REQUIRED.

    005FE957  8b5d08  mov ebx, dword ptr [ebp+8]     ; arg1 = a POINTER to a 4-dword point
    005FE95E  d903    fld dword ptr [ebx]

Same arithmetic: [ebp+8] == [esp_entry+4]. Confirmed.

A point in the hook's favour worth recording: **the bake CLOBBERS its own arg1 slot.**

    005FE9EF  8b4658  mov eax, dword ptr [esi+0x58]   ; the client's clock
    005FE9F3  894508  mov dword ptr [ebp+8], eax      ; arg1 slot reused as a scratch time
    ...
    005FEAAF  8b4508  mov eax, dword ptr [ebp+8]      ; read back as a TIME
    005FEB35  034d08  add ecx, dword ptr [ebp+8]      ; m_timeStopMovement = travel + now

A hook placed one byte later (after `push ebp`) that read `[ebp+8]` would still be
fine, but any hook that sampled the slot *later in the function* would have logged a
timestamp as "arg1". Entry-hooking is the correct choice here.

## Q3 — is ecx the agent at bake / setter / teleport?  ALL THREE CONFIRMED.

* **setter 0x00602A40** — `00602A44 mov ebx, ecx`; then `00602A48 test dword [ebx+0x20],
  0x20000` (m_flags IN_WORLD), `00602A84 mov [ebx+0x88]` (m_segmentPoint),
  `00602AA8 mov [ebx+0x98]`, `00602AB0 mov [ebx+0x9c]` (m_targetPoint).
* **bake 0x005FE950** — `005FE95C mov esi, ecx`; `005FE999 fld [esi+0x78]` (m_point),
  `005FEA19 mov eax,[esi+0x20]` / `005FEA4E mov [esi+0x20],eax` (m_flags),
  `005FEAD6 mov [esi+0x48],eax` (m_timeStopMovement).
* **teleport 0x006020B0** — `006020C5 mov ebx, ecx`; `006020FF lea esi,[ebx+0x78]`,
  writes +0x78..+0x84, +0x88/+0x8c, +0x9c/+0xa0, +0xb0/+0xb4.

## Q4 — agtrack 0x00605FC0 with deref_agent = 0.  CORRECT, and provably so.

`ecx` at agtrack is NOT an agent. Two independent proofs:

1. From its only in-region caller, the bake itself:

        005FE9CC  call 0x47f660                  ; global context
        005FE9D2  8b4808  mov ecx,[eax+8]
        005FE9D9  894dec  mov [ebp-0x14],ecx
        ...
        005FEBE1  8b4dec  mov ecx,[ebp-0x14]
        005FEBE5  81c1cc010000  add ecx, 0x1cc   ; <- ecx = context-derived subsystem
        005FEBE4  56      push esi               ; <- arg1 IS the agent
        005FEBEB  e8d0730000  call 0x605fc0

2. From agtrack's own body: `00605FF6 mov eax,[esi+0x20]` is used as an **array base**
   (`00606002 cmp dword [eax+ecx*4],0`, stride 28 via `lea ecx,[ebx*8]; sub ecx,ebx`),
   and `00605FDA cmp ebx,[esi+0x28]` is a **bounds count** guarded by an assert
   (`push 0x24b`).

Had `deref_agent` been 1 here, `+0x20` would have been recorded as "m_flags" while
actually holding a heap pointer, `+0x48` as "m_timeStopMovement", etc. — a full agent
block of plausible-looking fiction. The author got this right.

**Opportunity (NIT):** at agtrack, `arg1` IS the agent pointer (`push esi`, and agtrack
does `00605FC9 mov edi,[ebp+8]` / `00605FCE mov ebx,[edi+0x10]` = the id). The record
keeps the pointer but never derefs it, so a snap cannot be attributed to an agent.

---

## Q5 — WOULD THE CAPTURE ANSWER P1?

Verdict: **the rate half of P1a is answerable; the "before the arrival tick" clause is
NOT; and P1b's headline distance is being computed from the wrong field.**

### A5-1 (WRONG-DATA) — no sample of the client's own clock; `stop` is uninterpretable

`m_timeStopMovement` (+0x48) is in the **client's** millisecond clock, not
GetTickCount. OBSERVED chain:

    005FF88B  call 0x47f660
    005FF893  8b5808  mov ebx,[eax+8]
    005FF896  6b462464  imul eax,[esi+0x24],0x64
    005FF89E  8b841848010000  mov eax,[eax+ebx+0x148]   ; the client's clock
    005FF8A5  8945fc  mov [ebp-4], eax
    005FF932  894658  mov dword ptr [esi+0x58], eax     ; agent+0x58 = that clock
    ...bake: 005FEB35 add ecx,[ebp+8](=agent+0x58); 005FEB46 mov [esi+0x48],ecx

So `+0x48` and `+0x58` share a base; `GetTickCount` has no established relationship to
it. movehook.c:94 records `stop` and movehook.c:187/`r->tick` records GetTickCount, and
**`+0x58` is not captured** — even though it is 4 bytes and already inside the
`readable(ag, 0xB0)` window the handler validates (movehook.c:199).

P1a is pre-registered as "…will be followed, **before the arrival tick**, by at least
one bake with isWaypoint=1". That clause cannot be evaluated. Recoverable afterwards
only by *assuming* a constant epoch offset and estimating it from the data — i.e. by
inference, where one extra dword would have made it exact.

### A5-2 (WRONG-DATA) — the teleport's destination is in the args, not in `target`, and `target` can be +INF

OBSERVED: 0x006020B0 takes the destination **by value** in four stack args and writes
the AGENT_INVALID_POSITION sentinel into m_segmentPoint and m_targetPoint:

    006020FF  lea esi,[ebx+0x78]
    0060210B  mov eax,[ebp+8]   -> 00602132 mov [esi],eax        ; m_point.x = arg1
    00602134  mov eax,[ebp+0xc] -> 0060213A mov [esi+4],eax      ; m_point.y = arg2
    0060213D  mov eax,[ebp+0x10]-> 00602143 mov [esi+8],eax      ; m_point.plane = arg3
    00602146  mov eax,[ebp+0x14]-> 0060214F mov [esi+0xc],eax    ; m_point.w = arg4  <- NOT CAPTURED
    0060211D  fld dword ptr [0x948654]                           ; 0x7F800000 = +INF
    00602155  mov [ebx+0x88] ; 00602164 mov [ebx+0x8c]           ; m_segmentPoint = +INF
    0060216D  mov [ebx+0x9c] ; 00602179 mov [ebx+0xa0]           ; m_targetPoint  = +INF

(0x00948654 read out of the pinned image = `00 00 80 7f` = +inf.)

readhook.py:210-212 computes P1b's displacement as |m_point - m_targetPoint| at entry.
That is the right answer for exactly one of the **seven** teleport callers:

* `0x0060032E` (the tick) — CORRECT: `00600267 lea ebx,[esi+0x9c]` then the 16-byte
  copy at 0x00600311-0x00600329. Here target IS the destination.
* `0x00601817` (the path solver) — **WRONG**: `006017F7 mov edx,[ebp+0xc]` — the point
  is the solver's own caller-supplied pointer, not m_targetPoint.
* `0x00600A91` (obstacle avoidance) — pushes `[edi]`, a local pointer; not shown to be
  m_targetPoint.
* `0x00601899`, `0x0060221E`, `0x006025A6`, `0x00602B74` — unverified.

Consequences, concrete: (a) for 6 of 7 callers the printed distance is not the distance
moved; (b) any teleport on an agent whose m_targetPoint was already invalidated carries
+INF, and `((inf-px)**2+(inf-py)**2)**0.5` = `inf`, so `p50`/`max` print `inf` and
"over 100 u (a visible warp)" is inflated by one per such record. Nothing in readhook.py
filters non-finite values.

The fix is free on the capture side: the destination is already in `arg1`/`arg2`.
`arg4` ([esp+16]) is the only genuinely missing piece and is not needed for distance.

### A5-3 (ROBUSTNESS) — one 16384-slot buffer, four sites, head-truncated; the two
### highest-rate sites are coupled 1:1

`00605FC0` (agtrack) is called **from inside the bake** at `0x005FEBEB` (OBSERVED; the
bake's body runs past 0x005FEC83). So every bake costs two records and two exceptions.
NCAP = 16384 (movehook.c:74) and RUN_MS = 600000 (movehook.c:75); the worker exits early
on `g_n >= NCAP` (movehook.c:348). Unless the four sites together fire slower than
~27 hits/second, the capture is the **first 16384/R seconds after injection**, not a
sample of the session — and movehook.c:1-15's own header says these sites fire "tens of
times a second" per agent, before counting other agents in the district.

The truncation IS derivable from the file (`sum(per-site hits) > stored`), and
movehook.txt prints "RING FULL". But readhook.py's docstring promises "A full ring is a
truncated run … Said out loud, never silently" and `report()` never compares them — it
reads the sidecar only for controls A and B (readhook.py:135-153). So the promised
warning is a wish.

Note also there is no per-site quota: agtrack answers Q4 with maybe 50 distinct return
addresses but will consume ~half the buffer P1 needs.

### A5-4 (ROBUSTNESS) — measured observer effect, and it is DIRECTIONAL

Compiled and ran a scratch x86 program replicating this exact handler shape (VEH +
`readable()` ×5 + memset + 3× memcpy + `push ebp` emulation), no debugger attached:

    unpatched : 0.001 us/call
    int3+VEH  : 8.811 us/call   (n=20000, two runs, 8.811 / 8.805)

At two hits per bake that is ~17.6 us per bake. A few hundred bakes on a frame is
milliseconds on a ~16 ms budget. RECONSTRUCTION for the direction: both isWaypoint=1
guards are float inequalities between the point the solver just computed and where the
agent is currently headed (FINDINGS §1.6, `00600AEE`/`00601920`); a longer frame means a
larger per-frame displacement, which makes those points MORE likely to differ — so the
instrument biases the exact quantity P1 measures **upward**. Not merely noisy.

### A5-5 (ROBUSTNESS) — `have_agent == 0` leaves 13 fields at zero that read as data

movehook.c:186 memsets the record; movehook.c:199 gates the whole agent block. When the
gate fails, `id/flags/stop/x98/point/segment/target` are all 0 and there is no sentinel.
Concrete bite at readhook.py:199-205: `clear` counts only `have_agent` records but the
denominator is `len(tps)`, so a single guard failure prints

    SOME TELEPORTED WITH BIT 18 SET, which FINDINGS §1.3 says should not happen.
    That is a refutation, not noise.

— a manufactured refutation of §1.3. Honest likelihood: low. `readable()` rejects
`p & 3` and unmapped pages, and a thiscall `this` is essentially always a live 4-aligned
heap pointer. But the consequence is a believable false finding, not a visible failure.
Same shape applies to the stack block (movehook.c:193): if `readable(esp,16)` failed,
`retaddr/arg1/arg2/arg3` stay 0 and the record is indistinguishable from a genuine
`isWaypoint = 0` bake from an unknown caller — and `arg2 == 0` is P1a's discriminator.

### A5-6 (ROBUSTNESS) — the baked point is behind a pointer, so the re-plan's MAGNITUDE is lost

The bake's `arg1` is a pointer to the 4-dword point being baked (`005FE957 mov ebx,
[ebp+8]`, `005FE95E fld [ebx]`). movehook.c:195 keeps the pointer value only. For the
two isWaypoint=1 re-bakes the pointer is a **caller stack local** (FINDINGS §1.6:
`lea [ebp-0x44]` at 0x00600B02, `lea [ebp-0xa4]` at 0x0060192B) — meaningless after the
run. FINDINGS §1.6 ends "our warps are the distance between its answer and ours", and
distance is precisely what is dropped: the capture yields the RATE of re-planning but
not its MAGNITUDE.

Partially recoverable one hit later — the bake copies arg1's point into m_point
(0x005FEA92-0x005FEAA9) on one arm and into m_segmentPoint (0x005FEAE3-0x005FEB07) on
the other — but only if another hit on that agent follows, and which of the two arms ran
is not recorded. Copying `*(arg1)` 16 bytes through the existing `copy4()` would settle
it outright.

### A5-7 (NIT) — P1a as scored is a district-wide bake ratio, not a per-grant rate

readhook.py:176-179 computes "fraction of ALL bakes carrying arg2 != 0", pooled over
every agent in the district. P1a asks about **server-granted destinations**. Nothing is
missing from the capture for the finer question: `retaddr` identifies setter calls from
the 0x0029/0x002A handlers (0x005FD918 / 0x005FD9B9 = call+5), `ecx`+`id` group by agent
and `seq` orders them, so "the last bake before this agent's leg ended" is derivable.
Only the reader is missing it.

Checked and CORRECT: readhook.py:190-191's expected-caller list is call-site+5 in every
case (0x00602AD3→AD8, 0x006002B5→BA, 0x00600B0A→B0F, 0x00601936→93B, 0x005FEC7E→C83).
Site-index order matches `sorted(hook_site)` = agtrack, bake, setter, teleport in both
sites.h and readhook.py:117-125.
