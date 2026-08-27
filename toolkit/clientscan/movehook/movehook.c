/* movehook -- MOVECODE-B2. A persistent multi-site tap on the movement code.
 *
 * WHAT IT ANSWERS. MOVECODE-B1 established the mechanism and left one gap, and
 * the gap is a RATE that nothing static can reach (studies/movecode/FINDINGS.md
 * §4.1). Bit 18 of m_flags is `isWaypoint` -- "this leg does not end at the final
 * destination" -- and the bake 0x005FE950 assigns it from its arg2. The shared
 * setter hardcodes that arg to 0, so every wire-driven grant arms a hard arrival;
 * but the setter then calls obstacle avoidance (0x00600840) and a priority-queue
 * path solve (0x006011F0), and BOTH re-bake with arg2 = 1 when the point they
 * computed differs from where the agent is headed. So the client re-plans our
 * grants. How OFTEN is MOVECODE-P1, and this hook is its instrument:
 *
 *     hook the bake's ENTRY, read arg2 and the return address, and the rate and
 *     the responsible caller both fall out of the same record.
 *
 * ONE EMULATION SHAPE, WHICH IS A DESIGN CONSTRAINT AND NOT LUCK. Owner's ruling,
 * PLAN.md §7 Q12(d): the hook stays hand-rolled -- no MinHook, no Detours, no
 * §6.1 derivation row -- and it buys that by hooking only FUNCTION ENTRIES. A
 * persistent int3 must re-emulate whatever instruction its 0xCC displaced;
 * entries all begin `55` (push ebp), so one three-line emulation covers every
 * site. Hooking the glide-vs-teleport branch 0x0060029F directly -- seven bytes,
 * mid-function -- would have needed its own, and the teleport's entry gives the
 * identical ledger because that branch's only CLEAR-path consequence IS the call
 * to 0x006020B0. `gensites.py` re-reads each site's first byte out of the pinned
 * client and refuses to generate `sites.h` if any is not 0x55, so a build bump
 * stops the build instead of arming a breakpoint mid-instruction.
 *
 * READING ARGUMENTS AT AN ENTRY HOOK. The 0xCC replaced the FIRST byte, so the
 * `push ebp` has not run and esp is exactly as the caller left it:
 *
 *     [esp+0] return address      [esp+8]  arg2
 *     [esp+4] arg1                [esp+12] arg3          ecx = `this`
 *
 * That is why the return address is free here and would not be after the
 * prologue -- and the return address is what closes MOVECODE-Q4, whose whole
 * problem is that `--xrefs` sees direct rel32 branches only. `trnint3.c` uses the
 * same fact (`[esp+4] is arg1, the chunk`).
 *
 * TWO CONTROLS BEFORE ANY MEASUREMENT IS BELIEVED, copied from `trnint3.c`
 * because a hook that reports "0 teleports" is worthless unless the machinery
 * would have caught one:
 *
 *   CONTROL A (free, no client byte touched): execute `int3` in a buffer this
 *   DLL allocated. If the vectored handler does not see that, the handler is
 *   dead and nothing else in this file means anything.
 *
 *   CONTROL B (real client code): sample a live client thread's own Eip, patch
 *   THAT byte, and see it fire. Proves patch + delivery on the client's
 *   instruction stream rather than on ours. `trnint3.c` read the Eip from a file
 *   an external tool was supposed to write; this samples it in-process with
 *   Toolhelp32 + GetThreadContext, so the control cannot be skipped by a missing
 *   sidecar. It is THREE-VALUED -- fired / did not fire / could not arm -- and
 *   the sidecar prints which, because "could not find a client thread executing
 *   in .text" is a fact about the run and not a failed control. Same posture as
 *   `origin.py`'s ours/live/unknown.
 *
 * A RUN THAT MEASURED NOTHING SAYS SO. The sidecar records, per site, how many
 * hits arrived and how many records were stored, plus both controls' verdicts.
 * "The hook never fired" and "the client never did it" are different failures and
 * a silent zero merges them.
 *
 * Windows API and CRT only -- no third-party library, so CLAUDE.md carve-out 3
 * covers this and the second gate needs no new row (PLAN.md §7 Q12(d)).
 * Addresses come from content/movecode.toml via gensites.py; nothing is
 * hardcoded here. Output goes under vault/.
 */
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdlib.h>

#include "sites.h"

#define NCAP      16384u          /* records kept; ~1.6 MB */
#define DEF_RUN_MS 600000u        /* 10 minutes, then disarm and write */
#define CTLB_MS   8000u           /* how long control B waits for its own hit */
#define DEFDIR    "C:\\gd\\Rurik\\vault\\research\\movecode"
#define OUTENV    "RURIK_MOVEHOOK_OUT"
#define MSENV     "RURIK_MOVEHOOK_MS"

/* TWO CONFIG CHANNELS, AND THE SECOND ONE IS NOT REDUNDANT.
 *
 * The environment works only when whoever sets it also LAUNCHED the target:
 * `GetEnvironmentVariableA` inside an injected DLL reads the CLIENT's environment,
 * inherited from whatever started Gw.exe, not from the injector. `test_movehook.py`
 * spawns its own cmd.exe host and so can use it; `attach.py`, which injects into a
 * client already in the world, cannot -- and the bug that hides here is silent, the
 * DLL simply using its defaults while the operator believes otherwise.
 *
 * So a `movehook.cfg` BESIDE THE DLL wins over the environment. `attach.py` writes
 * it; the DLL finds it from its own module path. Same precedent as
 * `trnblock.c`'s target_block.txt, for the same reason: an injected DLL's only
 * reliable channel is the filesystem. */
static HINSTANCE g_self;

static void cfg_path(char *out, size_t n)
{
    char *slash;
    out[0] = 0;
    if (!GetModuleFileNameA(g_self, out, (DWORD)n)) return;
    slash = strrchr(out, '\\');
    if (slash) slash[1] = 0; else out[0] = 0;
    if (out[0]) strncat(out, "movehook.cfg", n - strlen(out) - 1);
}

/* `key` from movehook.cfg, else the environment, else `dflt`. */
static DWORD cfg_dword(const char *key, const char *envname, DWORD dflt)
{
    char path[MAX_PATH], line[512];
    FILE *f;
    size_t klen = strlen(key);
    cfg_path(path, sizeof path);
    if (path[0] && (f = fopen(path, "r")) != NULL) {
        while (fgets(line, sizeof line, f)) {
            if (strncmp(line, key, klen) == 0 && line[klen] == '=') {
                DWORD v = (DWORD)strtoul(line + klen + 1, NULL, 10);
                fclose(f);
                if (v) return v;
                break;
            }
        }
        fclose(f);
    }
    {
        char buf[32];
        DWORD n = GetEnvironmentVariableA(envname, buf, sizeof buf);
        if (n && n < sizeof buf) return (DWORD)strtoul(buf, NULL, 10);
    }
    return dflt;
}

static void cfg_string(const char *key, const char *envname,
                       char *out, size_t n, const char *dflt)
{
    char path[MAX_PATH], line[512];
    FILE *f;
    size_t klen = strlen(key);
    cfg_path(path, sizeof path);
    if (path[0] && (f = fopen(path, "r")) != NULL) {
        while (fgets(line, sizeof line, f)) {
            if (strncmp(line, key, klen) == 0 && line[klen] == '=') {
                char *v = line + klen + 1, *e;
                e = v + strlen(v);
                while (e > v && (e[-1] == 10 || e[-1] == 13)) *--e = 0;
                if (*v) { strncpy(out, v, n - 1); out[n - 1] = 0; fclose(f); return; }
                break;
            }
        }
        fclose(f);
    }
    {
        DWORD got = GetEnvironmentVariableA(envname, out, (DWORD)n);
        if (got && got < n) return;
    }
    strncpy(out, dflt, n - 1);
    out[n - 1] = 0;
}

/* One event. Fixed size and self-describing: the reader takes `reclen` from the
 * header rather than assuming this layout, so adding a field does not silently
 * mis-parse every prior capture. */
typedef struct {
    DWORD seq;
    DWORD tick;                   /* GetTickCount at the hit */
    DWORD site;                   /* index into SITES */
    DWORD tid;
    DWORD retaddr;                /* [esp] -- which caller. Closes Q4. */
    DWORD ecx;                    /* `this` */
    DWORD arg1, arg2, arg3;       /* [esp+4], [esp+8], [esp+12] */
    DWORD have_agent;             /* 0 = the block below is not meaningful */
    DWORD id;                     /* +0x10 */
    DWORD flags;                  /* +0x20 -- bit 18 is isWaypoint */
    DWORD stop;                   /* +0x48 m_timeStopMovement, the arrival tick */
    DWORD x98;                    /* +0x98 -- MOVECODE-Q3's field */
    DWORD point[4];               /* +0x78 m_point       : where the body IS */
    DWORD segment[4];             /* +0x88 m_segmentPoint: the leg's end */
    DWORD target[4];              /* +0x9C m_targetPoint : the destination */
} rec_t;

static DWORD  g_base;
static DWORD  g_addr[NSITES];
static BYTE   g_orig[NSITES];
static volatile LONG g_hits[NSITES];
static volatile LONG g_n = 0;
static rec_t  g_rec[NCAP];

static volatile LONG  g_selfhit = 0;      /* control A */
static volatile LONG  g_ctlhit  = 0;      /* control B */
static DWORD  g_selfprobe = 0;
static DWORD  g_ctl = 0;
static BYTE   g_ctl_orig;
static int    g_ctl_armed = 0;

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

/* Is `n` bytes at `p` safe to read RIGHT NOW?
 *
 * The handler dereferences ecx as an agent pointer. At a thiscall entry that is
 * what ecx is -- but "is" is a claim about the code, and a wrong one faults
 * INSIDE a vectored handler, which takes the client down in a way nobody could
 * attribute to us. VirtualQuery is a real cost and these sites fire tens of times
 * a second, not per-pixel, so it is affordable and it is the honest guard. */
static int readable(DWORD p, DWORD n)
{
    MEMORY_BASIC_INFORMATION mbi;
    if (!p || (p & 3u)) return 0;
    if (!VirtualQuery((LPCVOID)p, &mbi, sizeof mbi)) return 0;
    if (mbi.State != MEM_COMMIT) return 0;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return 0;
    if (p + n > (DWORD)(ULONG_PTR)mbi.BaseAddress + (DWORD)mbi.RegionSize) return 0;
    return 1;
}

static void copy4(DWORD *dst, DWORD src)
{
    if (readable(src, 16)) memcpy(dst, (const void *)src, 16);
}

static LONG CALLBACK on_bp(PEXCEPTION_POINTERS ep)
{
    CONTEXT *c = ep->ContextRecord;
    DWORD a = (DWORD)(ULONG_PTR)ep->ExceptionRecord->ExceptionAddress;
    unsigned i;

    if (ep->ExceptionRecord->ExceptionCode != EXCEPTION_BREAKPOINT)
        return EXCEPTION_CONTINUE_SEARCH;

    /* CONTROL A -- our own buffer. Step over the int3 to the ret. */
    if (g_selfprobe && a == g_selfprobe) {
        InterlockedExchange(&g_selfhit, 1);
        c->Eip = a + 1;
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    /* CONTROL B -- a byte of real client code, one-shot. Restore it and rewind
     * so the client executes its own instruction exactly once, unpatched. This
     * is why B may safely be an arbitrary mid-instruction address: it is never
     * emulated, only restored. */
    if (g_ctl_armed && a == g_ctl) {
        InterlockedExchange(&g_ctlhit, 1);
        poke(g_ctl, g_ctl_orig, NULL);
        g_ctl_armed = 0;
        c->Eip = a;
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    for (i = 0; i < NSITES; i++) {
        if (a != g_addr[i]) continue;
        InterlockedIncrement(&g_hits[i]);
        {
            LONG slot = InterlockedIncrement(&g_n) - 1;
            if (slot < (LONG)NCAP) {
                rec_t *r = &g_rec[slot];
                DWORD esp = c->Esp, ag = c->Ecx;
                memset(r, 0, sizeof *r);
                r->seq = (DWORD)slot;
                r->tick = GetTickCount();
                r->site = i;
                r->tid = GetCurrentThreadId();
                r->ecx = ag;
                /* esp is untouched: the `push ebp` we replaced has not run. */
                if (readable(esp, 16)) {
                    r->retaddr = ((DWORD *)esp)[0];
                    r->arg1    = ((DWORD *)esp)[1];
                    r->arg2    = ((DWORD *)esp)[2];
                    r->arg3    = ((DWORD *)esp)[3];
                }
                if (SITES[i].deref_agent && readable(ag, 0xB0)) {
                    r->have_agent = 1;
                    r->id    = *(DWORD *)(ag + A_ID);
                    r->flags = *(DWORD *)(ag + A_FLAGS);
                    r->stop  = *(DWORD *)(ag + A_TIME_STOP_MOVEMENT);
                    r->x98   = *(DWORD *)(ag + A_X98);
                    copy4(r->point,   ag + A_POINT);
                    copy4(r->segment, ag + A_SEGMENT_POINT);
                    copy4(r->target,  ag + A_TARGET_POINT);
                }
            }
        }
        /* Re-emulate the ONE instruction shape every site begins with:
         * `55  push ebp`. Then resume at site+1, the `mov ebp, esp`. This must
         * happen on every hit -- a skipped prologue is a corrupted frame, not a
         * missing sample -- and it is what keeps the breakpoint ARMED, because
         * the 0xCC is never restored. */
        c->Esp -= 4;
        *(DWORD *)c->Esp = c->Ebp;
        c->Eip = a + 1;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

/* The main module's .text span, read from the PE headers already mapped in this
 * process. Control B needs it to reject a sampled Eip that is inside a system
 * DLL -- patching ntdll would prove nothing about the client. */
static int text_span(DWORD base, DWORD *lo, DWORD *hi)
{
    BYTE *p = (BYTE *)base;
    DWORD e, nsec, opt, i, secoff;
    if (!base || *(WORD *)p != 0x5A4D) return 0;
    e = *(DWORD *)(p + 0x3C);
    if (*(DWORD *)(p + e) != 0x00004550) return 0;
    nsec = *(WORD *)(p + e + 6);
    opt  = *(WORD *)(p + e + 20);
    secoff = e + 24 + opt;
    for (i = 0; i < nsec; i++) {
        BYTE *s = p + secoff + i * 40;
        if (memcmp(s, ".text", 5) == 0) {
            *lo = base + *(DWORD *)(s + 12);
            *hi = *lo + *(DWORD *)(s + 8);
            return 1;
        }
    }
    return 0;
}

/* Sample a live client thread's Eip inside .text. Returns 0 if none was found,
 * which is reported as "could not arm" rather than as a failed control. */
static DWORD sample_client_eip(DWORD lo, DWORD hi)
{
    HANDLE snap;
    THREADENTRY32 te;
    DWORD me = GetCurrentProcessId(), self = GetCurrentThreadId(), found = 0;
    int pass;

    for (pass = 0; pass < 40 && !found; pass++) {
        snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
        if (snap == INVALID_HANDLE_VALUE) return 0;
        te.dwSize = sizeof te;
        if (Thread32First(snap, &te)) {
            do {
                HANDLE h;
                CONTEXT c;
                if (te.th32OwnerProcessID != me) continue;
                if (te.th32ThreadID == self) continue;
                h = OpenThread(THREAD_GET_CONTEXT | THREAD_SUSPEND_RESUME,
                               FALSE, te.th32ThreadID);
                if (!h) continue;
                /* Keep the suspended window as short as possible: suspend, read
                 * Eip, resume. Nothing that takes a lock happens in between. */
                if (SuspendThread(h) != (DWORD)-1) {
                    c.ContextFlags = CONTEXT_CONTROL;
                    if (GetThreadContext(h, &c) && c.Eip >= lo && c.Eip < hi)
                        found = c.Eip;
                    ResumeThread(h);
                }
                CloseHandle(h);
            } while (!found && Thread32Next(snap, &te));
        }
        CloseHandle(snap);
        if (!found) Sleep(25);
    }
    return found;
}

static const char *outdir(void)
{
    static char buf[MAX_PATH];
    cfg_string("out", OUTENV, buf, sizeof buf, DEFDIR);
    return buf;
}

static void mkdirs(const char *dir)
{
    char buf[MAX_PATH];
    size_t i;
    strncpy(buf, dir, sizeof buf - 1);
    buf[sizeof buf - 1] = 0;
    for (i = 1; buf[i]; i++)
        if (buf[i] == '\\') { buf[i] = 0; CreateDirectoryA(buf, NULL); buf[i] = '\\'; }
    CreateDirectoryA(buf, NULL);
}

static DWORD WINAPI worker(LPVOID unused)
{
    PVOID veh;
    unsigned i;
    DWORD waited = 0, tlo = 0, thi = 0, run_ms;
    char path[MAX_PATH];
    const char *dir;
    FILE *f;
    (void)unused;

    run_ms = cfg_dword("ms", MSENV, DEF_RUN_MS);
    g_base = (DWORD)(ULONG_PTR)GetModuleHandleW(NULL);
    for (i = 0; i < NSITES; i++) g_addr[i] = g_base + SITES[i].rva;

    veh = AddVectoredExceptionHandler(1, on_bp);

    /* CONTROL A. Costs nothing and touches no client byte. */
    {
        BYTE *probe = (BYTE *)VirtualAlloc(NULL, 16, MEM_COMMIT | MEM_RESERVE,
                                           PAGE_EXECUTE_READWRITE);
        if (probe) {
            probe[0] = 0xCC;
            probe[1] = 0xC3;
            g_selfprobe = (DWORD)(ULONG_PTR)probe;
            FlushInstructionCache(GetCurrentProcess(), probe, 16);
            ((void (*)(void))probe)();
        }
    }

    /* CONTROL B, before the measurement sites are armed so its hit cannot be
     * confused with one of theirs. */
    if (text_span(g_base, &tlo, &thi)) {
        g_ctl = sample_client_eip(tlo, thi);
        if (g_ctl && poke(g_ctl, 0xCC, &g_ctl_orig)) {
            g_ctl_armed = 1;
            while (!g_ctlhit && waited < CTLB_MS) { Sleep(25); waited += 25; }
            if (g_ctl_armed) { poke(g_ctl, g_ctl_orig, NULL); g_ctl_armed = 0; }
        }
    }

    for (i = 0; i < NSITES; i++)
        poke(g_addr[i], 0xCC, &g_orig[i]);

    waited = 0;
    while (waited < run_ms && g_n < (LONG)NCAP) { Sleep(100); waited += 100; }

    for (i = 0; i < NSITES; i++)
        poke(g_addr[i], g_orig[i], NULL);
    Sleep(150);                       /* let in-flight handlers finish */
    RemoveVectoredExceptionHandler(veh);

    dir = outdir();
    mkdirs(dir);

    snprintf(path, sizeof path, "%s\\movehook.bin", dir);
    f = fopen(path, "wb");
    if (f) {
        DWORD n = (DWORD)g_n, reclen = (DWORD)sizeof(rec_t), ver = 1, ns = NSITES;
        if (n > NCAP) n = NCAP;
        fwrite("MVHK", 4, 1, f);
        fwrite(&ver, 4, 1, f);
        fwrite(&g_base, 4, 1, f);
        fwrite(&ns, 4, 1, f);
        fwrite(&reclen, 4, 1, f);
        fwrite(&n, 4, 1, f);
        for (i = 0; i < NSITES; i++) {
            DWORD rva = (DWORD)SITES[i].rva, h = (DWORD)g_hits[i];
            fwrite(&rva, 4, 1, f);
            fwrite(&h, 4, 1, f);
        }
        fwrite(g_rec, sizeof(rec_t), n, f);
        fclose(f);
    }

    snprintf(path, sizeof path, "%s\\movehook.txt", dir);
    f = fopen(path, "w");
    if (f) {
        LONG total = 0;
        fprintf(f, "movehook -- MOVECODE-B2\n");
        fprintf(f, "base 0x%08X  ran %ums  capacity %u\n",
                (unsigned)g_base, (unsigned)waited, (unsigned)NCAP);
        fprintf(f, "control A (our own int3): %s\n",
                g_selfhit ? "FIRED" : "DID NOT FIRE -- the vectored handler is "
                                      "dead and nothing below means anything");
        if (!g_ctl)
            fprintf(f, "control B (client code): COULD NOT ARM -- no client "
                       "thread was sampled executing inside .text. That is a "
                       "fact about the run, not a failed control.\n");
        else
            fprintf(f, "control B (client code at 0x%08X): %s\n", (unsigned)g_ctl,
                    g_ctlhit ? "FIRED" : "DID NOT FIRE -- patch or delivery on "
                                         "real client code is unproven, so a "
                                         "zero below is NOT evidence of absence");
        fprintf(f, "\nper site:\n");
        for (i = 0; i < NSITES; i++) {
            total += g_hits[i];
            fprintf(f, "  %-10s rva 0x%08X va 0x%08X  hits %ld\n",
                    SITES[i].name, (unsigned)SITES[i].rva,
                    (unsigned)g_addr[i], (long)g_hits[i]);
        }
        fprintf(f, "\nhits %ld  stored %ld of %u%s\n", (long)total, (long)g_n,
                (unsigned)NCAP,
                g_n >= (LONG)NCAP ? "  RING FULL -- the run was truncated and the "
                                    "tail is missing" : "");
        fclose(f);
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        g_self = h;
        DisableThreadLibraryCalls(h);
        CloseHandle(CreateThread(NULL, 0, worker, NULL, 0, NULL));
    }
    return TRUE;
}
