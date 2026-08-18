/* Dump the CLIENT'S OWN per-cell terrain layer descriptors.
 *
 * THE QUESTION. Since the corner selector closed (FINDINGS 7.9) our exporter
 * chooses a coverage quadrant in PERMUTED index space, while
 * `import_gwmap.py` places that quadrant's alpha in PHYSICAL space --
 * FINDINGS 7.10, and the reason the owner sees "corners where there should be
 * half-and-half". Whether the client's own coverage is permuted or physical
 * decides which of two fixes is right, and it is not something to reason
 * about: the client builds the answer every frame.
 *
 * WHERE. `0x00761A25` is the `call 0x757a80` at the end of TrnTexBlendHi,
 * reached once per cell with the finished descriptor array in the frame:
 *
 *     [ebp-0x10] [ebp-0x0C] [ebp-0x08]   up to three (coverage<<16)|texIndex
 *     [ebp-0x34] [ebp-0x30] [ebp-0x2C] [ebp-0x28]   the four corner TYPES
 *
 * Both in one frame, so a capture is self-contained -- no need to locate the
 * cell in the map to test the question.
 *
 * WHY THE PATCH STAYS ARMED. A one-shot restore would give ONE cell, and 81%
 * of cells are single-material and say nothing. So instead of restoring, this
 * EMULATES the 5-byte `call rel32` it replaced: push the return address
 * (target+5) and set Eip to the callee. The int3 survives, and every cell is
 * captured until the ring is full.
 *
 * Windows API and CRT only. Output under vault/, which is gitignored.
 */
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <stdio.h>

#define SITE_RVA  0x00361A25u          /* 0x00761A25 - 0x00400000, the call */
#define CALLEE_RVA 0x00357A80u         /* 0x00757A80, what it calls */
#define RET_LEN   5u                   /* the call instruction it replaced */
#define NCAP      512u                 /* cells to capture */
#define WIN_LO    0x40u                /* bytes below ebp */
#define PRNG_OFF  0xD4u                /* [ebp-0x18] is chunk+0x1d0; +0xD4 = chunk+0x2A4 */
#define WIN_LEN   0x60u   /* ebp-0x40 .. ebp+0x20: adds arg3 sel, arg4 var */
#define OUTDIR    "C:\\gd\\Rurik\\vault\\research\\terrain"

static DWORD g_site, g_callee;
static BYTE  g_orig;
static volatile LONG  g_n = 0;
static volatile LONG  g_done = 0;
static DWORD g_ebp[NCAP];
static DWORD g_rng[NCAP][2];
static DWORD g_uv[NCAP][4];   /* base rect: span u,v then origin u,v (7.2) */
static BYTE  g_win[NCAP][WIN_LEN];

static int poke(DWORD addr, BYTE val, BYTE *saved)
{
    DWORD old;
    if (!addr || !VirtualProtect((LPVOID)addr, 1, PAGE_EXECUTE_READWRITE, &old))
        return 0;
    if (saved) *saved = *(BYTE *)addr;
    *(BYTE *)addr = val;
    VirtualProtect((LPVOID)addr, 1, old, &old);
    FlushInstructionCache(GetCurrentProcess(), (LPCVOID)addr, 1);
    return 1;
}

static LONG CALLBACK on_bp(PEXCEPTION_POINTERS ep)
{
    CONTEXT *c = ep->ContextRecord;
    DWORD a = (DWORD)ep->ExceptionRecord->ExceptionAddress;
    LONG slot;
    if (ep->ExceptionRecord->ExceptionCode != EXCEPTION_BREAKPOINT || a != g_site)
        return EXCEPTION_CONTINUE_SEARCH;

    slot = InterlockedIncrement(&g_n) - 1;
    if (slot < (LONG)NCAP) {
        g_ebp[slot] = c->Ebp;
        {   /* the PRNG pair for THIS cell, chased from the frame */
            DWORD sub = *(DWORD *)(c->Ebp - 0x18);
            g_rng[slot][0] = *(DWORD *)(sub + PRNG_OFF);
            g_rng[slot][1] = *(DWORD *)(sub + PRNG_OFF + 4);
            /* FINDINGS 7.2: the UNMASKED (base) path reads its own
             * rectangle -- span at obj+0x68/0x6C, origin at obj+0x70/0x74 --
             * which we have never implemented. Captured as raw dwords; they
             * are floats. */
            g_uv[slot][0] = *(DWORD *)(sub + 0x68);
            g_uv[slot][1] = *(DWORD *)(sub + 0x6C);
            g_uv[slot][2] = *(DWORD *)(sub + 0x70);
            g_uv[slot][3] = *(DWORD *)(sub + 0x74);
        }
        memcpy(g_win[slot], (const void *)(c->Ebp - WIN_LO), WIN_LEN);
        if (slot == NCAP - 1) InterlockedExchange(&g_done, 1);
    }

    /* Emulate the `call rel32` we overwrote: push return, jump to callee. */
    c->Esp -= 4;
    *(DWORD *)c->Esp = g_site + RET_LEN;
    c->Eip = g_callee;
    return EXCEPTION_CONTINUE_EXECUTION;
}

static DWORD WINAPI worker(LPVOID unused)
{
    PVOID veh;
    DWORD base = (DWORD)GetModuleHandleW(NULL);
    int waited = 0;
    FILE *f;
    (void)unused;

    g_site   = base + SITE_RVA;
    g_callee = base + CALLEE_RVA;
    veh = AddVectoredExceptionHandler(1, on_bp);
    poke(g_site, 0xCC, &g_orig);

    while (!g_done && waited < 900000) { Sleep(50); waited += 50; }
    poke(g_site, g_orig, NULL);
    Sleep(120);                         /* let in-flight handlers finish */

    CreateDirectoryA("C:\\gd\\Rurik\\vault\\research", NULL);
    CreateDirectoryA(OUTDIR, NULL);
    f = fopen(OUTDIR "\\layers_dump.bin", "wb");
    if (f) {
        DWORD n = (DWORD)g_n; DWORD lo = WIN_LO, len = WIN_LEN;
        if (n > NCAP) n = NCAP;
        fwrite(&n, 4, 1, f); fwrite(&lo, 4, 1, f); fwrite(&len, 4, 1, f);
        fwrite(&base, 4, 1, f);
        fwrite(g_ebp, 4, n, f);
        fwrite(g_rng, 8, n, f);
        fwrite(g_uv, 16, n, f);
        fwrite(g_win, WIN_LEN, n, f);
        fclose(f);
    }
    f = fopen(OUTDIR "\\layers_dump.txt", "w");
    if (f) {
        fprintf(f, "base 0x%08X site 0x%08X callee 0x%08X\ncaptured %ld\n",
                (unsigned)base, (unsigned)g_site, (unsigned)g_callee, (long)g_n);
        fclose(f);
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
