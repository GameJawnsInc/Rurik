# LANE A4 -- Control B: deadlock, soundness, and can it fail?

Tree: C:/gd/Rurik/.claude/worktrees/movecode-b2 (verified).
NOTE: movehook.c grew 421 -> 437 lines DURING this review (a peer session is editing
it live). All line numbers below are against the 437-line version; code text quoted
verbatim so the citation survives drift.

## Binary verification (OBSERVED)

codescan --dis against vault/client/2026-07-29_221c13772c7a/Gw.exe (build 38797):
  0x005FE950  55 8bec   push ebp / mov ebp, esp   (bake)
  0x006020B0  55 8bec                              (teleport)
  0x00602A40  55 8bec                              (setter)
  0x00605FC0  55 8bec                              (agtrack)
All four are entries. The site emulation is correct FOR THIS BUILD.

gwpe section table: .text is the FIRST section, vaddr 0x1000, vsize 0x537FAE.
No .textbss / .textN. text_span() therefore spans base+0x1000 .. base+0x538FAE and
all four RVAs (0x1FE950 .. 0x205FC0) fall inside it.

## Q1 DEADLOCK -- attacked, found nothing

- CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD): does NOT take the loader lock
  (SNAPMODULE/SNAPMODULE32 do; SNAPTHREAD is NtQuerySystemInformation + heap).
  The worker also cannot start until DllMain returns and the loader lock is free.
- The snapshot handle is a captured section, not a lock. Holding it across a
  suspend is safe.
- Inside the suspend window (l.287-292) the only calls are GetThreadContext,
  ResumeThread and integer compares -- all syscalls, no user-mode lock. The
  comment at l.285-286 is CORRECT. CloseHandle(h) is after ResumeThread; the
  next pass's snapshot allocation happens with nothing suspended.
- Suspending a thread inside on_bp is IMPOSSIBLE here, and the reason is
  ordering, not luck: control A's int3 runs on the worker thread itself
  (excluded by `te.th32ThreadID == self`), g_ctl is armed at l.353 AFTER
  sampling, and the sites at l.360. This invariant is load-bearing: any future
  "re-sample on timeout" (which is the natural fix for Q4) would break it.
  Even then on_bp holds no user-mode lock, so it would be a perturbation risk,
  not a deadlock.
- Worst case wall time: 40 passes x Sleep(25) = 1000 ms + enumeration, then
  CTLB_MS = 8000 ms. Sites arm ~9.0-9.3 s after DllMain. See F5.

VERDICT: no deadlock.

## Q2 SOUNDNESS OF THE RESTORE+REWIND

Sound -- but NOT for the reason the comment gives. l.181-184 claims "B may safely
be an arbitrary mid-instruction address: it is never emulated, only restored."
That is false as a general statement. If g_ctl were genuinely mid-instruction, the
0xCC would corrupt the CONTAINING instruction and no trap would occur at g_ctl at
all. Concrete: `8B 43 40  mov eax,[ebx+0x40]`, patch the 0x43 -> `8B CC` +
`40` = `mov ecx,esp` / `inc eax`. Silent register corruption, no breakpoint, and
control B reports DID NOT FIRE while the damage stands until l.356 restores it.

It is safe ONLY because g_ctl comes from a suspended thread's Eip, which is by
definition an instruction boundary in that thread's decode stream. The comment
gives permission the design does not have -- and trnint3.c literally fed g_ctl
from a FILE (arm64.py), so "any address is fine" is a live invitation to regress.

Contrast with the SITE patches: those ARE emulated (l.231-233 push ebp + Eip=a+1)
and are valid only if the first byte really is 0x55. gensites.py checks that
against the PINNED image at generate time; nothing checks the RUNNING image. See F2.

## FINDINGS

F1 CRASH  -- g_ctl_armed gate drops a concurrent/late hit -> unhandled int3
F2 CORRUPTION -- sites armed blind; both controls green while the instrument is broken
F3 WRONG-DATA -- "COULD NOT ARM" does not cover a failed poke
F4 WRONG-DATA -- single cold sample -> false DID NOT FIRE, wording blames the machinery
F5 ROBUSTNESS -- ~9.3 s of blind time before the sites arm
F6 CRASH  -- failed restore clears g_ctl_armed anyway -> orphan 0xCC, guaranteed later crash
F7 NIT    -- memcmp(s,".text",5) prefix-matches .textbss/.textN
