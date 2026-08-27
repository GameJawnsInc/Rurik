# LANE A2 -- can on_bp FAULT, and what happens if it does?

Tree: C:/gd/Rurik/.claude/worktrees/movecode-b2 (verified)
Client: vault/client/2026-07-29_221c13772c7a/Gw.exe, build 38797, PRISTINE
Scratch probes (NOT repo code): vehgeom.c, readable.c, vehstress.c, ctlbrace.c, vehfault.c

## Binary facts (OBSERVED)
- All four sites begin `55 8bec` (push ebp; mov ebp, esp). codescan --dis.
  - 0x005FE950 bake     `55 8bec 83ec24 53 8b5d08 ... 8bf1 (mov esi,ecx)`  -> thiscall
  - 0x006020B0 teleport `55 8bec 83ec1c d94508 ... 8bd9 (mov ebx,ecx)`     -> thiscall
  - 0x00602A40 setter   `55 8bec 53 8bd9 56 57 f7432000000200 (test [ebx+0x20],0x20000)`
        -> ecx IS the agent and A_FLAGS=0x20 is corroborated by the client's own test
  - 0x00605FC0 agtrack  `55 8bec 83ec08 ... 8b7d08 (edi=arg1) 8bf1 (esi=ecx) 8b5f10 (ebx=[edi+0x10])`
        -> the AGENT is arg1 here, not ecx. sites.h deref_agent=0 is correct.
- Gw.exe PE: machine 014C, characteristics 0x0122 -> LARGE_ADDRESS_AWARE = TRUE.

## Probe results (OBSERVED, this machine, Win11 26200, x86 WOW64)

### vehgeom.exe -- geometry of the unguarded write (movehook.c:216-218)
    hits 200000/200000, all results correct
    sizeof(CONTEXT) 0x2CC
    ExceptionRecord 0x012FF87C (+0x50) -> CONTEXT 0x012FF8CC..0x012FFB98
    trap esp 0x012FFD34 ; write target esp-4 = 0x012FFD30
    INSIDE CONTEXT? no    INSIDE EXCEPTION_RECORD? no
    gap between CONTEXT end and trap esp: 412 bytes
    ebp preserved YES; x87 st0 survived YES; xmm0 survived YES
  => the write cannot fault (kernel already wrote ~0x360 bytes below esp to
     stage the dispatch) and does not corrupt the dispatched CONTEXT.

### readable.exe -- the guard against real allocations
    PAGE_EXECUTE (execute-only)  readable=1  actual_read=OK   <- x86 has no exec-only; NOT a hole
    PAGE_NOACCESS                readable=0  actual_read=FAULT
    PAGE_GUARD (prot 0x104)      readable=0  actual_read=FAULT
    MEM_RESERVE                  readable=0  actual_read=FAULT
    unaligned p                  readable=0  (conservative)
    4 bytes before region end    readable=0  actual_read=OK    (conservative)
    straddles 2 committed rgns   readable=0  actual_read=OK    (conservative)
    p=0xFFFFFFF0 / 0xFFFFFF50    VirtualQuery FAILS (returns 0)
    A_TARGET_POINT 0x9C+16 = 0xAC <= 0xB0 -> single readable(ag,0xB0) DOES cover all seven reads

### vehstress.exe (built /LARGEADDRESSAWARE, matching Gw.exe)
    MAX APP ADDR 0xFFFEFFFF  -- p+0xB0 wraps only for p >= 0xFFFFFF50,
      which is above the highest queryable address => VirtualQuery fails first.
      *** the p+n overflow is UNREACHABLE ***
    1,812,199 hits / 6 s / 4 threads while a 5th thread churned the address space
    wrong results (emulation): 0
    guard said YES then read FAULTED: 269,566   *** TOCTOU escapes are real ***

### ctlbrace.exe -- movehook.c:170 `g_ctl_armed && a == g_ctl` vs trnint3.c:78 `a == g_ctl`
    movehook.c logic: 11 unhandled EXCEPTION_BREAKPOINT / 400 trials x 8 threads
    trnint3.c  logic:  0
  *** CONFIRMED CRASH-CLASS REGRESSION FROM THE PRECEDENT ***

## Negatives (attacked, found nothing)
- p+n overflow in readable(): unreachable (VirtualQuery gates p <= 0xFFFEFFFF).
- BaseAddress+RegionSize overflow: impossible in a 32-bit address space
  (last region ends at 0xFFFF0000); (DWORD) casts do not truncate on x86.
- PAGE_EXECUTE not covered by the mask: harmless, x86 has no execute-only memory.
- readable(ag,0xB0) coverage: highest byte touched is ag+0xAB. COVERED.
- readable(esp,16) coverage: highest byte touched is esp+15. COVERED exactly.
- The unguarded write at c->Esp-4: architecturally cannot fault (see vehgeom).
- VirtualQuery inside a VEH: no deadlock in 1.8M dispatches under address-space
  churn. It cannot self-deadlock on the VAD lock -- a thread holding that lock
  is in kernel mode and cannot be executing a user-mode int3.
- Recursion: on_bp filters ExceptionCode != EXCEPTION_BREAKPOINT first, so an AV
  raised inside the handler does not re-enter the handler's body.
- The four measurement sites have NO armed-flag gate (g_addr[] is never cleared),
  so a thread trapped in flight across the disarm is still emulated correctly.
  Only control B has the gate bug.
