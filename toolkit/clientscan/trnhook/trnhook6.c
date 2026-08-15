/* Read the terrain chunk pointer from the function that owns it.
 *
 * WHY THIS EXISTS. `trnblend.SELECTION = "identity"` pins a per-cell byte the
 * client reads from `chunk+0x2B4` and walks with `inc`. Nothing in the image
 * writes that address, so two rounds of anchored static scanning bounded the
 * question without answering it, and four attempts to find the chunk by the
 * data it points at all landed on per-block pointer tables instead. The chunk
 * is not reachable from its contents -- it is an ARGUMENT. So take it from
 * there: `[ebp-0x40]` in `0x0075DD50` is `[esp+4]` at entry.
 *
 * WHY A BREAKPOINT AND NOT A DETOUR. A 5-byte `jmp` patch would cut the
 * client's `sub esp, 0x158` in half and needs 9 bytes relocated into a
 * trampoline. A hardware execute breakpoint reads the same argument and
 * MODIFIES NO CLIENT CODE, which matters when the thing being measured is
 * whether a rendering path behaves normally. Dr7 is cleared on the first hit,
 * so the client runs unhooked for the rest of the session.
 *
 * Windows API and the CRT only -- no third-party hooking library, so CLAUDE.md
 * carve-out 3 applies and the second gate needs no new row.
 *
 * Output: C:\gd\Rurik\vault\research\terrain\selector.bin  (1024 bytes, the
 * array) and selector.txt (the pointer and a short profile). Both under
 * vault/, which is gitignored.
 */
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

/* Build 38797 preferred image base 0x00400000; the RVA is what survives ASLR. */
#define FUNC_RVA   0x0035DD50u     /* 0x0075DD50 - 0x00400000, the HI path */
/* The caller picks between them at 0x007434E5 with `test eax, 0x2000`, and a
 * default-settings client takes the LO path -- measured 2026-08-15, when a
 * breakpoint on the hi path alone never fired in Kamadan. Watch both and let
 * the client say which it uses. */
#define FUNC2_RVA  0x0035E650u     /* 0x0075E650 - 0x00400000, the LO path */
#define SEL_OFF    0x2B4u
#define RNG_OFF    0x2A4u
#define SEL_LEN    1024u
#define OUTDIR     "C:\\gd\\Rurik\\vault\\research\\terrain"

static volatile LONG  g_done = 0;
static volatile DWORD g_chunk = 0;
static DWORD          g_target = 0;
static DWORD          g_target2 = 0;
static volatile DWORD g_which = 0;

static LONG CALLBACK on_bp(PEXCEPTION_POINTERS ep)
{
    CONTEXT *c;
    if (ep->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;
    c = ep->ContextRecord;
    if (!(c->Dr6 & 0xF))
        return EXCEPTION_CONTINUE_SEARCH;

    /* At function entry [esp] is the return address and [esp+4] is arg1,
     * which 0x0075DD64 copies to ebx and 0x0075DD6A parks at [ebp-0x40]. */
    if (!InterlockedExchange(&g_done, 1)) {
        g_chunk = *(DWORD *)(c->Esp + 4);
        g_which = c->Eip;        /* CONTROL: report WHERE, not which */
    }

    c->Dr0 = 0;                      /* one shot: run unhooked afterwards */
    c->Dr1 = 0;
    c->Dr7 &= ~0x5u;
    c->Dr6 = 0;
    return EXCEPTION_CONTINUE_EXECUTION;
}

static void arm_all_threads(int on)
{
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    THREADENTRY32 te;
    DWORD me = GetCurrentProcessId(), self = GetCurrentThreadId();
    if (snap == INVALID_HANDLE_VALUE)
        return;
    te.dwSize = sizeof te;
    if (Thread32First(snap, &te)) {
        do {
            HANDLE h;
            CONTEXT c;
            if (te.th32OwnerProcessID != me || te.th32ThreadID == self)
                continue;
            h = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT
                           | THREAD_SET_CONTEXT, FALSE, te.th32ThreadID);
            if (!h)
                continue;
            SuspendThread(h);
            c.ContextFlags = CONTEXT_DEBUG_REGISTERS;
            if (GetThreadContext(h, &c)) {
                if (on) {
                    c.Dr0 = g_target;
                    c.Dr1 = g_target2;
                    /* L0|L1, RW/LEN zero = execute, 1 byte, for both slots */
                    c.Dr7 = (c.Dr7 & ~0xFF0000u) | 0x5u;
                } else {
                    c.Dr0 = 0;
                    c.Dr1 = 0;
                    c.Dr7 &= ~0x5u;
                }
                c.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                SetThreadContext(h, &c);
            }
            ResumeThread(h);
            CloseHandle(h);
        } while (Thread32Next(snap, &te));
    }
    CloseHandle(snap);
}

static DWORD WINAPI worker(LPVOID unused)
{
    PVOID veh;
    char path[MAX_PATH];
    int waited = 0;
    (void)unused;

    g_target = (DWORD)GetModuleHandleW(NULL) + FUNC_RVA;
    g_target2 = (DWORD)GetModuleHandleW(NULL) + FUNC2_RVA;
    veh = AddVectoredExceptionHandler(1, on_bp);
    arm_all_threads(1);

    /* The terrain draw runs every frame, so a hit should be immediate. */
    while (!g_done && waited < 600000) {
        Sleep(50);
        waited += 50;
    }
    arm_all_threads(0);

    CreateDirectoryA("C:\\gd\\Rurik\\vault\\research", NULL);
    CreateDirectoryA(OUTDIR, NULL);
    sprintf(path, "%s\\selector.txt", OUTDIR);
    {
        FILE *f = fopen(path, "w");
        if (f) {
            fprintf(f, "image base 0x%08X\ntarget 0x%08X\nhit %d path=%u"
                       "  (1=hi 0x0075DD50, 2=lo 0x0075E650)\n",
                    (unsigned)(DWORD)GetModuleHandleW(NULL),
                    (unsigned)g_target, (int)g_done, (unsigned)g_which);
            if (g_chunk) {
                const unsigned char *sel = (const unsigned char *)(g_chunk + SEL_OFF);
                const DWORD *rng = (const DWORD *)(g_chunk + RNG_OFF);
                unsigned i, counts[256] = {0};
                fprintf(f, "chunk 0x%08X\n", (unsigned)g_chunk);
                fprintf(f, "rng +0x2A4 = 0x%08X 0x%08X\n",
                        (unsigned)rng[0], (unsigned)rng[1]);
                fprintf(f, "first 64 bytes at +0x2B4:\n");
                for (i = 0; i < 64; i++)
                    fprintf(f, "%02X%s", sel[i], (i % 16 == 15) ? "\n" : " ");
                for (i = 0; i < SEL_LEN; i++)
                    counts[sel[i]]++;
                fprintf(f, "distinct=");
                {
                    unsigned d = 0, v;
                    for (v = 0; v < 256; v++)
                        if (counts[v])
                            d++;
                    fprintf(f, "%u  0xE4=%u/%u\n", d, counts[0xE4], SEL_LEN);
                }
            } else {
                fprintf(f, "NO HIT -- breakpoint never fired\n");
            }
            fclose(f);
        }
    }
    if (g_chunk) {
        sprintf(path, "%s\\selector.bin", OUTDIR);
        {
            FILE *f = fopen(path, "wb");
            if (f) {
                fwrite((const void *)(g_chunk + SEL_OFF), 1, SEL_LEN, f);
                fclose(f);
            }
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
