# LANE A1 -- is the instruction emulation EXACTLY right?

Tree: C:/gd/Rurik/.claude/worktrees/movecode-b2 (verified).
NOTE: the Read tool served a STALE movehook.c (421 lines). The file on disk is 438
lines and has `env_dword`/`RURIK_MOVEHOOK_MS`. All line numbers below are read from
the raw bytes on disk.

## Verdict on the emulation itself: it is exactly right. I could not break it.

### 1. Do all four sites begin `55 push ebp`? YES -- OBSERVED
`codescan.py --dis` against the pinned client
(vault/client/2026-07-29_221c13772c7a/Gw.exe, build 38797):

    005FE950  55 push ebp / 8bec mov ebp,esp   (bake)
    006020B0  55 push ebp / 8bec mov ebp,esp   (teleport)
    00602A40  55 push ebp / 8bec mov ebp,esp   (setter)
    00605FC0  55 push ebp / 8bec mov ebp,esp   (agtrack)

All four have `8B EC` at +1, so `Eip = a+1` lands on a real instruction boundary.
gensites.py:105-109 refuses to emit sites.h if any first byte != 0x55.

### 2. Is `push ebp` correctly emulated? YES -- OBSERVED, measured
Built a 32-bit probe (scratchpad/pushemu2.c) that runs movehook.c:231-233 verbatim
against a hand-assembled `55 8B EC ...` stub, comparing the emulated push against a
real one from the SAME frame:

    UNPATCHED  pushed=00AFFB9C expected(ebp)=00AFFB9C  OK
               ret=010011AD calleeEbp=00AFFB08 &arg1=00AFFB10 eflags=00000246
    PATCHED    pushed=00AFFB9C expected(ebp)=00AFFB9C  OK
               identical to unpatched: pushed=yes ebp=yes argp=yes eflags=yes
    HAMMER (4 threads x 25000): hits=100001 corrupted=0
    CONTROL (unpatched, same loop):        corrupted=0

Every architectural effect is reproduced: ESP-=4, SS:[ESP]=EBP (SS base 0, flat),
EFLAGS untouched (0x246 both ways -- `push` sets no flags and the handler writes
none), EIP+=1. AC is clear so no #AC. `push` is not a control transfer so there is
no shadow-stack effect. Nothing is missed.

### 3. Is `a + 1` right? YES for a 1-byte displaced instruction.
A 2-byte first instruction would leave an orphan second byte and `a+1` would execute
it as an instruction -- that is exactly FINDING 1 below, realised on a real build.

### 4. Args read BEFORE the esp write? YES -- correct order.
movehook.c:200 snapshots `DWORD esp = c->Esp` and :208-212 read [esp+0..12] from that
snapshot; the emulation is at :231. Args are read from the pre-push esp, which is
what the header's `[esp+0]=ret, [esp+4]=arg1` claim requires. The snapshot makes it
robust even against later reordering. No defect.

### 5. Is writing 4 bytes below the client's esp safe? YES -- and it is SAFER than
the push it replaces. Measured (scratchpad/pushemu.c) at a real hit:

    client Esp at hit     = 005AFD24
    write target Esp-4    = 005AFD20
    ep->ContextRecord     = 005AF8BC   (Esp - ctx  = 1128 bytes)
    ep->ExceptionRecord   = 005AF86C   (Esp - erec = 1208 bytes)
    handler's own esp    ~= 005AF754   (Esp - sp   = 1488 bytes)
    Esp-4 inside CONTEXT record:        no  (sizeof CONTEXT 0x2CC; its top is Esp-412)
    Esp-4 inside EXCEPTION_RECORD:      no

Two consequences, both good:
  (a) Guard page is impossible. Exception dispatch already committed >=1488 bytes
      below Esp before the handler ran, so the page holding Esp-4 is committed by
      construction. The real `push ebp` could fault and grow the stack; the emulated
      one cannot.
  (b) The write lands in a ~408-byte dead gap above the dispatch frame -- it does not
      overlap the CONTEXT or EXCEPTION_RECORD the dispatcher is still holding.
100,001 hammer iterations, 0 corrupted pushes. Also confirmed: ExceptionAddress ==
the int3 address, and ContextRecord->Eip is already decremented to it.

Precedent agreement: trnhook/trnblock.c:123-124 performs the identical
`c->Esp -= 4; *(DWORD*)c->Esp = ...` and is a proven capture.

## What IS wrong: the emulation's PRECONDITION is never checked at run time.

### FINDING 1 -- CRASH. Nothing verifies the displaced byte was 0x55.
`SITE_FIRST_BYTE` is defined at sites.h:13 and referenced NOWHERE in movehook.c
(grep). poke() (movehook.c:130-140) saves the pre-existing byte into g_orig[i] and
returns int; the call at :361 discards the return and never inspects the byte.
gensites.py checks 0x55 -- but against `pinned.find()` (gensites.py:83), a FILE, the
07-29 snapshot. inject.py takes a PID. Nothing joins the two.

OBSERVED, from the owner's own vault -- four snapshots exist and run/ holds
launchable dirs for three builds (07-29 pinned, 08-13, 08-20). In snapshot
2026-04-30_b174de1f2d8d the four RVAs read 0x02 / 0x8B / 0x08 / 0x8B -- none is 0x55.
0x005FE950 there is:

    005FE950  8b4514  mov eax, dword ptr [ebp + 0x14]     <- mid-EPILOGUE
    005FE953  8946fc  mov dword ptr [esi - 4], eax
    005FE956  5f 5e 5b  pop edi / pop esi / pop ebx
    005FE959  8be5    mov esp, ebp

and resuming at a+1 disassembles as:

    005FE951  45      inc ebp
    005FE952  1489    adc al, 0x89
    005FE954  46      inc esi
    005FE955  fc      cld

Mitigating, and I checked it: 08-13 and 08-20 are byte-identical to the pin in the
first 48 bytes of all four sites, so the risk is LATENT today, not live. It goes live
on the next ArenaNet build bump -- and the pin deliberately does not follow.

### FINDING 2 -- WRONG-DATA. Arming is neither verified nor reported.
poke()'s return is discarded (:361); the sidecar (:413-419) prints only
name/rva/va/hits. Controls A and B never touch a SITE address (B patches a sampled
Eip, :351-353). MEASURED: in test_movehook.py's own host (SysWOW64 cmd.exe), all four
site addresses are FREE or RESERVE across 5 trials, so all four pokes fail and the
sidecar still reads `bake ... hits 0` -- textually identical to a real client run
where the site WAS armed and the player never moved. test_movehook.py:333-336 asserts
`hits 0` and labels it "sites that could not arm report ZERO hits", but that
assertion passes in both worlds.

### FINDING 3 -- ROBUSTNESS. The VEH is removed on a fixed 150 ms timer.
:366-369 restore the bytes, Sleep(150), RemoveVectoredExceptionHandler. A thread that
executed the 0xCC just before the restore and is still dispatching at +150 ms finds no
handler: unhandled EXCEPTION_BREAKPOINT at a movement function entry. Deleting :369
closes it for free.
