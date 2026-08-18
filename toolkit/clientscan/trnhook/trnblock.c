/* Capture ONE NAMED tile block's per-cell terrain layer descriptors.
 *
 * WHY THIS EXISTS, and it is not a refinement of `trnlayers.c` -- it answers
 * a question that one cannot. Every client-truth number in FINDINGS 7.11-7.14
 * comes from a block where terrain tag 3 is zero on every cell ("defer to the
 * PRNG"), because `trnlayers.c` stores the FIRST 512 cells that hit the
 * breakpoint and the first block built is whichever the client gets to first.
 * On Lornar's Pass that was (8,18), then (4,2), then (0,2) -- never one with
 * authored values, and 4% of cells corpus-wide carry them.
 *
 * The authored blocks are ALSO mostly unreachable: ranked by authored count,
 * the top four blocks in the archive have ZERO walkable probes (FINDINGS 8),
 * so "walk there and let it build" is not available either. Standing in the
 * right place cannot aim this instrument.
 *
 * SO AIM IT AT THE DATA INSTEAD. `chunk+0x2A4`'s first dword is the block's
 * unstepped reseed, `(tile_x << 16) ^ tile_y` -- which is not an assumption:
 * FINDINGS 7.9 read (8,18) and (4,2) out of it and then reproduced those two
 * blocks' selectors cell by cell, 2048 of 2048. This hook keeps a cell only
 * when that dword equals a target read from
 *
 *     vault/research/terrain/target_block.txt      one hex dword, e.g. 00040003
 *
 * With no target file it LOCKS TO THE FIRST block it sees and keeps only that
 * one, which is what `trnlayers.c` was doing by accident whenever a capture
 * happened to fit inside one block.
 *
 * NCAP is 1024 -- a whole 32x32 block, where `trnlayers.c`'s 512 could only
 * ever be half of one.
 *
 * A RUN THAT MATCHES NOTHING IS LOUD. The sidecar records hits, matches and
 * the distinct block ids seen, so "the target never built" is distinguishable
 * from "the hook never fired" -- the two failures a silent zero would merge.
 *
 * Windows API and CRT only (CLAUDE.md carve-out 3). Output under vault/.
 */
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <stdio.h>

#define SITE_RVA   0x00361A25u         /* 0x00761A25, the call at TrnTexBlendHi's end */
#define CALLEE_RVA 0x00357A80u         /* 0x00757A80, what it calls */
#define RET_LEN    5u
#define NCAP       1024u               /* a whole 32x32 tile block */
#define WIN_LO     0x40u
#define PRNG_OFF   0xD4u               /* [ebp-0x18] is chunk+0x1d0; +0xD4 = chunk+0x2A4 */
#define WIN_LEN    0x60u               /* ebp-0x40 .. ebp+0x20: arg3 sel, arg4 var */
#define NSEEN      32u                 /* distinct block ids to remember */
#define OUTDIR     "C:\\gd\\Rurik\\vault\\research\\terrain"

static DWORD g_site, g_callee;
static BYTE  g_orig;
static volatile LONG g_n = 0;          /* cells STORED */
static volatile LONG g_hits = 0;       /* cells the breakpoint saw */
static volatile LONG g_done = 0;
static DWORD g_target = 0;             /* 0 = lock to the first block seen */
static volatile LONG g_locked = 0;
static DWORD g_ebp[NCAP];
static DWORD g_rng[NCAP][2];
static DWORD g_uv[NCAP][4];
static BYTE  g_win[NCAP][WIN_LEN];
static DWORD g_seen[NSEEN];            /* distinct block ids, for diagnosis */
static volatile LONG g_nseen = 0;

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

static void note_seen(DWORD id)
{
    LONG i, n = g_nseen;
    for (i = 0; i < n && i < (LONG)NSEEN; i++)
        if (g_seen[i] == id) return;
    if (n < (LONG)NSEEN) { g_seen[n] = id; InterlockedExchange(&g_nseen, n + 1); }
}

static LONG CALLBACK on_bp(PEXCEPTION_POINTERS ep)
{
    CONTEXT *c = ep->ContextRecord;
    DWORD a = (DWORD)ep->ExceptionRecord->ExceptionAddress;
    DWORD sub, block;
    LONG slot;

    if (ep->ExceptionRecord->ExceptionCode != EXCEPTION_BREAKPOINT || a != g_site)
        return EXCEPTION_CONTINUE_SEARCH;

    InterlockedIncrement(&g_hits);
    sub   = *(DWORD *)(c->Ebp - 0x18);
    block = *(DWORD *)(sub + PRNG_OFF);
    note_seen(block);

    /* No target named: the FIRST block to arrive becomes the target, so a
     * capture is one block by construction rather than by luck. */
    if (!g_target && !InterlockedCompareExchange(&g_locked, 1, 0))
        g_target = block;

    if (block == g_target) {
        slot = InterlockedIncrement(&g_n) - 1;
        if (slot < (LONG)NCAP) {
            g_ebp[slot] = c->Ebp;
            g_rng[slot][0] = block;
            g_rng[slot][1] = *(DWORD *)(sub + PRNG_OFF + 4);
            g_uv[slot][0] = *(DWORD *)(sub + 0x68);
            g_uv[slot][1] = *(DWORD *)(sub + 0x6C);
            g_uv[slot][2] = *(DWORD *)(sub + 0x70);
            g_uv[slot][3] = *(DWORD *)(sub + 0x74);
            memcpy(g_win[slot], (const void *)(c->Ebp - WIN_LO), WIN_LEN);
            if (slot == NCAP - 1) InterlockedExchange(&g_done, 1);
        }
    }

    /* Emulate the `call rel32` we overwrote: push return, jump to callee.
     * This must happen for EVERY cell, matched or not -- the client is mid
     * frame and a skipped call is a corrupted chunk, not a missing sample. */
    c->Esp -= 4;
    *(DWORD *)c->Esp = g_site + RET_LEN;
    c->Eip = g_callee;
    return EXCEPTION_CONTINUE_EXECUTION;
}

static DWORD read_target(void)
{
    FILE *f = fopen(OUTDIR "\\target_block.txt", "r");
    unsigned v = 0;
    int got = 0;
    if (!f) return 0;
    got = fscanf(f, "%x", &v);
    fclose(f);
    return got == 1 ? (DWORD)v : 0;
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
    g_target = read_target();

    veh = AddVectoredExceptionHandler(1, on_bp);
    poke(g_site, 0xCC, &g_orig);

    /* 4 minutes, not the 15 `trnlayers.c` used. That one filled its ring
     * inside a single chunk and stopped; this one stays armed until the
     * TARGET block completes, so a target that never builds keeps every
     * terrain cell in the process running through a vectored handler for the
     * whole timeout. Bounding it bounds that exposure, and the run is decided
     * at map load either way -- terrain builds once, when the map arrives. */
    while (!g_done && waited < 240000) { Sleep(50); waited += 50; }
    poke(g_site, g_orig, NULL);
    Sleep(120);                        /* let in-flight handlers finish */

    CreateDirectoryA("C:\\gd\\Rurik\\vault\\research", NULL);
    CreateDirectoryA(OUTDIR, NULL);
    f = fopen(OUTDIR "\\layers_block.bin", "wb");
    if (f) {
        DWORD n = (DWORD)g_n, lo = WIN_LO, len = WIN_LEN;
        if (n > NCAP) n = NCAP;
        fwrite(&n, 4, 1, f); fwrite(&lo, 4, 1, f); fwrite(&len, 4, 1, f);
        fwrite(&base, 4, 1, f);
        fwrite(g_ebp, 4, n, f);
        fwrite(g_rng, 8, n, f);
        fwrite(g_uv, 16, n, f);
        fwrite(g_win, WIN_LEN, n, f);
        fclose(f);
    }
    f = fopen(OUTDIR "\\layers_block.txt", "w");
    if (f) {
        LONG i, ns = g_nseen;
        fprintf(f, "base 0x%08X site 0x%08X callee 0x%08X\n",
                (unsigned)base, (unsigned)g_site, (unsigned)g_callee);
        fprintf(f, "target 0x%08X %s\n", (unsigned)g_target,
                g_locked ? "(locked to first block seen)" : "(from target_block.txt)");
        fprintf(f, "hits %ld  stored %ld  of %u\n",
                (long)g_hits, (long)g_n, (unsigned)NCAP);
        fprintf(f, "distinct blocks seen %ld:", (long)ns);
        for (i = 0; i < ns && i < (LONG)NSEEN; i++)
            fprintf(f, " 0x%08X", (unsigned)g_seen[i]);
        fprintf(f, "\n");
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
