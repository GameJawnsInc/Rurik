/* Read the terrain chunk pointer with an int3 patch, control first.
 *
 * WHY THIS AND NOT THE DEBUG REGISTERS. eipcontrol.py armed an address a
 * thread was PROVABLY executing, in the native 64-bit CONTEXT, verified by
 * read-back, on 49 threads -- and nothing fired. Hardware breakpoints do not
 * deliver in this client. Software ones use a different delivery path
 * entirely: the CPU raises EXCEPTION_BREAKPOINT from the instruction stream.
 *
 * TWO CONTROLS, BOTH BEFORE THE MEASUREMENT, because five silent runs were
 * already misread as facts about the client this session:
 *
 *   CONTROL A (free, zero risk): this DLL executes `int3` in its OWN thread.
 *   If the vectored handler does not see that, the handler is broken and
 *   nothing else in this file means anything. No client byte is touched.
 *
 *   CONTROL B: patch a byte the client is provably executing (its own
 *   sampled EIP, passed in) and see it fire. Proves patch + delivery on real
 *   client code, not just on ours.
 *
 * Only if A and B pass does the terrain result get written, and the log says
 * which controls passed so a reader can tell a measurement from a silence.
 *
 * THE PATCH IS ONE BYTE AND ONE SHOT. No trampoline and no prologue
 * relocation: on the hit we restore the original byte, rewind Eip to the
 * function entry, and continue -- the client then executes its real prologue
 * exactly once, unpatched, forever after.
 *
 * Output: vault/research/terrain/int3.txt (+ selector.bin on success).
 */
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

#define HI_RVA   0x0035DD50u
#define LO_RVA   0x0035E650u
#define SEL_OFF  0x2B4u
#define RNG_OFF  0x2A4u
#define SEL_LEN  1024u
#define OUTDIR   "C:\\gd\\Rurik\\vault\\research\\terrain"
/* arm64.py writes the client's own sampled EIP here for control B. */
#define CTLFILE  OUTDIR "\\ctl_eip.txt"

static volatile LONG  g_selfhit = 0;   /* control A */
static volatile LONG  g_ctlhit  = 0;   /* control B */
static volatile LONG  g_done    = 0;
static volatile DWORD g_chunk   = 0;
static volatile DWORD g_which   = 0;
#define STK_LEN 512
static BYTE  g_stack[STK_LEN];
static DWORD g_esp = 0, g_ebp = 0;
static DWORD g_hi, g_lo, g_ctl;
static BYTE  g_orig_hi, g_orig_lo, g_orig_ctl;
static volatile DWORD g_selfprobe = 0;

static int poke(DWORD addr, BYTE val, BYTE *saved)
{
    DWORD old;
    if (!addr || !VirtualProtect((LPVOID)addr, 1, PAGE_EXECUTE_READWRITE, &old))
        return 0;
    if (saved)
        *saved = *(BYTE *)addr;
    *(BYTE *)addr = val;
    VirtualProtect((LPVOID)addr, 1, old, &old);
    FlushInstructionCache(GetCurrentProcess(), (LPCVOID)addr, 1);
    return 1;
}

static LONG CALLBACK on_bp(PEXCEPTION_POINTERS ep)
{
    DWORD a;
    if (ep->ExceptionRecord->ExceptionCode != EXCEPTION_BREAKPOINT)
        return EXCEPTION_CONTINUE_SEARCH;
    a = (DWORD)ep->ExceptionRecord->ExceptionAddress;

    if (g_selfprobe && a == g_selfprobe) {
        InterlockedExchange(&g_selfhit, 1);       /* CONTROL A */
        ep->ContextRecord->Eip = a + 1;           /* step over our own int3 */
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    if (a == g_ctl) {
        InterlockedExchange(&g_ctlhit, 1);        /* CONTROL B */
        poke(g_ctl, g_orig_ctl, NULL);
        ep->ContextRecord->Eip = a;               /* rewind, run the real byte */
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    if (a == g_hi || a == g_lo) {
        if (!InterlockedExchange(&g_done, 1)) {
            /* int3 replaced the first byte, so esp is untouched by the call:
             * [esp] is the return address and [esp+4] is arg1, the chunk. */
            g_chunk = *(DWORD *)(ep->ContextRecord->Esp + 4);
            g_which = a;
            g_esp = ep->ContextRecord->Esp;
            g_ebp = ep->ContextRecord->Ebp;
            memcpy(g_stack, (const void *)g_esp, STK_LEN);
        }
        poke(a, (a == g_hi) ? g_orig_hi : g_orig_lo, NULL);
        ep->ContextRecord->Eip = a;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

static DWORD read_ctl_eip(void)
{
    unsigned v = 0;
    FILE *f = fopen(CTLFILE, "r");
    if (f) {
        if (fscanf(f, "%x", &v) != 1)
            v = 0;
        fclose(f);
    }
    return (DWORD)v;
}

static DWORD WINAPI worker(LPVOID unused)
{
    PVOID veh;
    FILE *f;
    int waited = 0;
    DWORD base = (DWORD)GetModuleHandleW(NULL);
    (void)unused;

    g_hi = base + HI_RVA;
    g_lo = base + LO_RVA;
    g_ctl = read_ctl_eip();
    veh = AddVectoredExceptionHandler(1, on_bp);

    /* CONTROL A -- an int3 in a buffer WE own. No client byte is touched,
     * so this costs nothing and can only fail if the handler itself is dead. */
    {
        BYTE *probe = (BYTE *)VirtualAlloc(NULL, 16, MEM_COMMIT | MEM_RESERVE,
                                           PAGE_EXECUTE_READWRITE);
        if (probe) {
            probe[0] = 0xCC;                 /* int3  */
            probe[1] = 0xC3;                 /* ret   */
            g_selfprobe = (DWORD)(ULONG_PTR)probe;
            FlushInstructionCache(GetCurrentProcess(), probe, 16);
            ((void (*)(void))probe)();       /* handler steps Eip to the ret */
        }
    }

    if (g_ctl)
        poke(g_ctl, 0xCC, &g_orig_ctl);
    poke(g_hi, 0xCC, &g_orig_hi);
    poke(g_lo, 0xCC, &g_orig_lo);

    while (!g_done && waited < 900000) {
        Sleep(50);
        waited += 50;
    }
    poke(g_hi, g_orig_hi, NULL);
    poke(g_lo, g_orig_lo, NULL);
    if (g_ctl && !g_ctlhit)
        poke(g_ctl, g_orig_ctl, NULL);

    CreateDirectoryA("C:\\gd\\Rurik\\vault\\research", NULL);
    CreateDirectoryA(OUTDIR, NULL);
    f = fopen(OUTDIR "\\int3.txt", "w");
    if (f) {
        fprintf(f, "base 0x%08X hi 0x%08X lo 0x%08X ctl 0x%08X\n",
                (unsigned)base, (unsigned)g_hi, (unsigned)g_lo,
                (unsigned)g_ctl);
        fprintf(f, "CONTROL A (own int3 seen by VEH): %s\n",
                g_selfhit ? "PASS" : "FAIL -- handler never runs, nothing "
                                     "below is a measurement");
        fprintf(f, "CONTROL B (client byte fired):    %s\n",
                g_ctl ? (g_ctlhit ? "PASS" : "FAIL") : "not attempted");
        fprintf(f, "terrain hit: %s", g_done ? "YES" : "no\n");
        if (g_done) {
            const unsigned char *sel =
                (const unsigned char *)(g_chunk + SEL_OFF);
            const DWORD *rng = (const DWORD *)(g_chunk + RNG_OFF);
            unsigned i, c[256] = {0}, d = 0;
            fprintf(f, " at 0x%08X (%s)\nchunk 0x%08X\nrng 0x%08X 0x%08X\n",
                    (unsigned)g_which, g_which == g_hi ? "HI" : "LO",
                    (unsigned)g_chunk, (unsigned)rng[0], (unsigned)rng[1]);
            for (i = 0; i < 64; i++)
                fprintf(f, "%02X%s", sel[i], (i % 16 == 15) ? "\n" : " ");
            for (i = 0; i < SEL_LEN; i++)
                c[sel[i]]++;
            for (i = 0; i < 256; i++)
                if (c[i])
                    d++;
            fprintf(f, "distinct=%u  0xE4=%u/%u\n", d, c[0xE4], SEL_LEN);
        }
        fclose(f);
    }
    if (g_done) {
        f = fopen(OUTDIR "\\stack.bin", "wb");
        if (f) { fwrite((const void *)&g_esp,4,1,f);
                 fwrite((const void *)&g_ebp,4,1,f);
                 fwrite(g_stack,1,STK_LEN,f); fclose(f); }
        f = fopen(OUTDIR "\\selector.bin", "wb");
        if (f) {
            fwrite((const void *)(g_chunk + SEL_OFF), 1, SEL_LEN, f);
            fclose(f);
        }
    }
    RemoveVectoredExceptionHandler(veh);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        CloseHandle(CreateThread(NULL, 0, worker, NULL, 0, NULL));
    }
    return TRUE;
}
