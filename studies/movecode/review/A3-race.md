# LANE A3 -- reentrancy, races, ring buffer (movehook.c)

Tree: C:/gd/Rurik/.claude/worktrees/movecode-b2 (verified).
Client: vault/client/2026-07-29_221c13772c7a/Gw.exe, build 38797, PRISTINE.

## Ground truth established first

**OBSERVED** -- all four sites begin `55 8b ec` (codescan --dis):
0x005FE950, 0x006020B0, 0x00602A40, 0x00605FC0. The one-shape emulation premise holds.

**OBSERVED** (scratchpad/ctxprobe.c, x86, this OS): the entry-hook emulation at
movehook.c:216-218 is sound. Measured in a faithful reproduction:
- `sizeof(CONTEXT)` = 716; exception frame is placed 412 bytes *below* the faulting
  esp, so the `*(DWORD*)(esp-4) = ebp` write does NOT land inside the CONTEXT or the
  EXCEPTION_RECORD the dispatcher built.
- `ContextRecord->Eip == ExceptionAddress` on x86 (the kernel decrements), so
  `c->Eip = a + 1` is right.
- The emulated push survives `NtContinue`: stub read `[ebp]` == the handler's `c->Ebp`.

**OBSERVED** (scratchpad/ctlrace.c): with a 0xCC planted at `g_ctl` and
`g_ctl_armed == 0`, movehook's handler shape returns EXCEPTION_CONTINUE_SEARCH --
the breakpoint escapes. A back-of-chain safety VEH caught it in the probe; Gw.exe
has no such net.

**OBSERVED** (same probe): two nested `VirtualProtect(...,PAGE_EXECUTE_READWRITE,&old)`
calls on one page make the second save 0x40 (RWX) as "the original" instead of 0x20
(PAGE_EXECUTE_READ). Restoring in the wrong order leaves .text writable.

## Findings

### F1 CRASH -- control B declines a trap it planted (movehook.c:170-176, :337-341)
Gate is `if (g_ctl_armed && a == g_ctl)`. Byte restored at :172, flag cleared at :173.
Any trap whose *dispatch* lands after the flag clear falls to :221
EXCEPTION_CONTINUE_SEARCH. Two independent triggers, neither exotic:
 (a) two threads execute the sampled byte inside the ~10-30 us restore window --
     control B deliberately picks a byte a live client thread was executing;
 (b) SINGLE thread is enough: a trap at t=7999 ms whose dispatch straddles the
     worker's CTLB_MS timeout at :340, which restores and clears the flag.
trnint3.c:78 is `if (a == g_ctl)` -- unconditional. movehook REGRESSED the precedent.
Fix: match on address alone (`if (g_ctl && a == g_ctl)`), placed after the site loop;
make the restore idempotent/once via `InterlockedExchange(&g_ctl_armed,0)`.

### F2 CRASH -- poke() is not atomic against a concurrent poke on the same page
Handler :172 and worker :340 can both call `poke(g_ctl, g_ctl_orig, NULL)`.
`InterlockedExchange(&g_ctlhit,1)` at :171 publishes "done" BEFORE the work at :172-173,
so the worker wakes within one Sleep(25), still sees `g_ctl_armed == 1`, and pokes
concurrently. Outcome A: worker restores PAGE_EXECUTE_READ first, handler's
`*(BYTE*)addr = val` faults -> access violation inside a vectored handler -> client dies.
Outcome B: handler restores its captured RWX -> a .text page stays writable all session.
Fix: publish g_ctlhit last; single-owner restore via InterlockedExchange.

### F3 CRASH -- RemoveVectoredExceptionHandler(:353) is not a barrier
:350 restores bytes, :352 `Sleep(150)`, :353 unregisters. Sleep is a guess, not
synchronization; no in-flight counter exists. A site trap raised before :350 but not yet
dispatched at :353 escapes (mechanism OBSERVED in ctlrace E1b). Note the site path is
otherwise robust to a late hit -- `g_addr[]` is never cleared, so the handler still
matches and emulates correctly even after the byte is restored. Unregistering is the
ONLY thing that makes a straggler fatal. Fix: don't remove it (or drain an interlocked
in-flight count first).

### F4 CRASH -- AddVectoredExceptionHandler return is unchecked (:318), then :329 int3s
`veh` is never tested. Control A executes `int3` in our own buffer unconditionally at
:329. If registration failed, the DLL kills Gw.exe the instant it is injected and writes
no file, so the failure is unattributable. Fix: `if (!veh) return 0;` before control A.

### F5 WRONG-DATA -- the slot is published before the record is written
:182 `InterlockedIncrement(&g_n)` claims the slot; :186-:208 fill it. Worker reads
`n = g_n` at :361 and `fwrite(g_rec,...,n,...)` at :374 with only Sleep(150) between.
A handler preempted mid-record yields a zeroed/partial record in the file. readhook.py
decodes an all-zero record as site 0 = `agtrack`, seq 0, have_agent 0 and counts it in
the per-site "stored" tally. No barrier and no validation anywhere. Fix: `rec[i].seq == i`
holds for every complete record -- validate it in the worker and in readhook.py; or
publish with a second interlocked "committed" counter.

### F6 ROBUSTNESS -- nothing prevents unload; no DLL_PROCESS_DETACH disarm
grep: zero `FreeLibrary` in the repo, and inject.py only remote-calls LoadLibraryA, so
no current tool unloads it. But no `GET_MODULE_HANDLE_EX_FLAG_PIN` either, and DllMain
(:413-421) handles only DLL_PROCESS_ATTACH. An unload while armed leaves four 0xCC bytes
in .text with no handler and no DLL -> guaranteed crash on the next movement bake.

### F7 ROBUSTNESS -- g_ctl_armed is a plain non-volatile int (:113)
Written from the handler (:173) on client threads and from the worker (:338, :340).
Data race / UB; under /O2 the worker's `if (g_ctl_armed)` may read a stale value.
(g_hits/g_n/g_selfhit/g_ctlhit are all correctly volatile+Interlocked.)

### F8 ROBUSTNESS -- readable() is TOCTOU (:134-143 vs :193-:207)
VirtualQuery then read. A concurrent decommit between them faults inside the VEH ->
unattributable client death. Low likelihood (Windows heaps rarely decommit). The larger
real risk is the opposite: a valid-but-wrong pointer passes the page check and records
garbage silently.

### F9 NIT -- movehook.txt prints unclamped g_n as "stored" (:404)
The .bin clamps at :362; the sidecar does not, so a full ring prints e.g.
"stored 16500 of 16384". Print min(g_n,NCAP) stored and g_n-NCAP dropped.

### F10 ROBUSTNESS -- nothing is written until RUN_MS elapses (:348, :358)
Ten minutes armed, output only at the end. A client exit or unrelated crash at minute 9
discards the entire capture, and the sites stay armed for the whole window.

## Attacked and found nothing
- **Ring buffer bounds.** `slot = InterlockedIncrement(&g_n) - 1` gives every hit a
  unique slot; `if (slot < (LONG)NCAP)` is the correct guard; `g_rec[slot]` is never
  written out of bounds. Negative `slot` needs 2^31 hits, and the worker's :348 loop
  exits at NCAP and disarms, so the counter is bounded in practice.
- **Counter growth past NCAP** is bounded to one 100 ms poll plus the four pokes; hits
  past NCAP correctly stop writing while still counting in `g_hits[i]`.
- **`hits` vs `stored`** is the right two-number design: :180 counts before :183 gates.
- **Emulation under concurrency.** `c->Esp -= 4; *(DWORD*)c->Esp = c->Ebp` writes to the
  faulting thread's own stack, 412 bytes clear of the exception frame (measured). Every
  handler runs on its own thread's stack; no cross-thread sharing.
- **Suspended-at-the-0xCC, byte restored.** If Eip == site and the byte is back to 0x55
  the thread simply executes `push ebp` -- correct. If the trap is already pending, the
  handler still matches on `g_addr[]` and emulates correctly. Only F3 makes it fatal.
- **sample_client_eip deadlock.** No user-mode lock is taken between SuspendThread and
  ResumeThread (:272-277); ResumeThread is unconditional on a successful suspend; the
  do/while `continue`s reach Thread32Next correctly. Clean.
- **Handler self-reentrancy.** on_bp calls only VirtualQuery/GetTickCount/memcpy/memset
  plus poke on the control-B path; none route through the four sites.
- **Site fall-through after disarm.** g_addr[] retained, so no F1-equivalent on the sites.
