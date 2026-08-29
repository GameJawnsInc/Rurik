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
 * TWO EMULATION SHAPES, AND THE SECOND ONE IS STILL A DESIGN CONSTRAINT. Owner's
 * ruling, PLAN.md §7 Q12(d): the hook stays hand-rolled -- no MinHook, no
 * Detours, no §6.1 derivation row -- and it buys that by hooking only shapes
 * whose displaced instruction is ONE BYTE and trivially re-emulable. A
 * persistent int3 must re-emulate whatever its 0xCC displaced:
 *
 *     SHAPE_ENTRY  `55 push ebp`  ->  esp -= 4; [esp] = ebp; eip = a + 1
 *     SHAPE_RET    `C3 ret`       ->  eip = [esp]; esp += 4
 *
 * Every site was SHAPE_ENTRY until 2026-08-29, when the MapFindPath RETURN tap
 * (HANDOFF-PLANE.md §4.2) needed the answer rather than the question. Both
 * shapes share the property that made the entry rule safe: a one-byte
 * instruction has no interior, so a one-byte patch cannot land mid-instruction.
 * What is still refused is a shape whose displaced instruction is longer --
 * hooking the glide-vs-teleport branch 0x0060029F directly, seven bytes,
 * mid-function -- and the teleport's ENTRY gives the identical ledger anyway,
 * because that branch's only CLEAR-path consequence IS the call to 0x006020B0.
 *
 * `gensites.py` re-reads each site's first byte out of the pinned client and
 * refuses to generate `sites.h` unless it matches THAT ROW'S OWN SHAPE -- which
 * is a tighter gate than the single global 0x55 it replaced, because an entry
 * that decayed into something else is still caught. A build bump stops the build
 * instead of arming a breakpoint mid-instruction.
 *
 * THE ASYMMETRY BETWEEN THE TWO SHAPES, because it decides an error path. At an
 * entry, failing to emulate merely loses a sample -- the client re-executes
 * `push ebp` on the next pass. At a RET there is no safe skip: leaving Eip on
 * the 0xCC re-traps forever, and at 0x0070A0D4 the next eleven bytes are the
 * compiler's own int3 padding. So the ret arm's fallback is control B's proven
 * technique -- restore the byte, rewind, let the client run its own `ret` once,
 * and mark the site DISARMED so the sidecar reports a hook that stopped
 * measuring rather than a client that stopped calling.
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

#define NCAP      32768u          /* records kept; ~7 MB at v2's record size.
                                   * Run 1 used 2,062 in 263 s over four sites;
                                   * B3 adds MapFindPath, which a path solver can
                                   * call far more often than an agent moves, and a
                                   * full ring is a TRUNCATED run whose rates are
                                   * biased toward whatever happened early. */
#define DEF_RUN_MS 600000u        /* 10 minutes, then disarm and write */
#define CTLB_MS   8000u           /* how long control B waits for its own hit */
#define RET_MAX_POINTS 9u         /* out_path capacity, in points. NINE, and it
                                   * is not a percentile: it is the LARGER OF
                                   * THE TWO CALLERS' OWN maxCount -- snap gate
                                   * 2 pushes 4 (`006057F4 6a04`), click-to-move
                                   * pushes 9 (`0081AF43 6a09`), read statically
                                   * from both frames and confirmed live on r7
                                   * where arg4 was 9 or 4 and nothing else,
                                   * 214/214. At 9 the buffer CANNOT truncate
                                   * for either known caller, which retires the
                                   * standing "compare shapes only on the
                                   * untruncated ones" caveat rather than
                                   * shrinking it. Was 4 until 2026-08-29: that
                                   * cost nothing for the pathCount question
                                   * (the COUNT is exact at any capacity) and
                                   * cost shape comparison on 16 of r7's 214.
                                   * PRICE, stated: out_path sits in EVERY
                                   * record of EVERY site, so this is
                                   * 20 dwords x NCAP = 2.5 MiB more of the
                                   * client's address space (10.75 -> 13.25 MiB)
                                   * for a field only 3.8% of r7's records used.
                                   * The ring is a fixed record COUNT, so it
                                   * does not shorten a run. */
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

static void beside_dll(char *out, size_t n, const char *leaf)
{
    char *slash;
    out[0] = 0;
    if (!GetModuleFileNameA(g_self, out, (DWORD)n)) return;
    slash = strrchr(out, '\\');
    if (slash) slash[1] = 0; else out[0] = 0;
    if (out[0]) strncat(out, leaf, n - strlen(out) - 1);
}

static void cfg_path(char *out, size_t n) { beside_dll(out, n, "movehook.cfg"); }

/* THE STOP FILE, and it exists because the first live run was worse without it.
 *
 * There is no Ctrl+C for an injected DLL: the code runs on the CLIENT's threads,
 * and the console that ran the injector has already exited. On 2026-08-27 the
 * operator finished the useful part of a capture in four minutes and then had to
 * stand still for six more with no way to end it and no idea when it would end --
 * and the capture's own record shows the cost, 337 of its 600 seconds holding a
 * character that had stopped moving.
 *
 * So the run ends on ANY of three conditions and the sidecar says WHICH: the timer,
 * a full ring, or this file appearing. `attach.py --stop` writes it. */
static int stop_requested(void)
{
    char path[MAX_PATH];
    beside_dll(path, sizeof path, "movehook.stop");
    return path[0] && GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES;
}

static void clear_stop(void)
{
    char path[MAX_PATH];
    beside_dll(path, sizeof path, "movehook.stop");
    if (path[0]) DeleteFileA(path);
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
    /* SIX args, not three, and the widening is what made the record version 2.
     * Three covered the movement sites (the setter's thiscall takes three), but
     * MOVECODE-B3's `MapFindPath` is a navmesh query with an output buffer among
     * its parameters -- an entry hook that cannot see arg4 cannot record WHERE the
     * client asked its answer to be written. Reading six dwords off the caller's
     * stack costs nothing extra: `readable(esp, 28)` covers all of them in the one
     * guard that already ran. Args beyond a function's real arity are whatever the
     * caller happened to leave there and MUST NOT be read as parameters -- the site
     * row's own `nargs` is what says how many are meaningful. */
    DWORD arg1, arg2, arg3;       /* [esp+4],  [esp+8],  [esp+12] */
    DWORD arg4, arg5, arg6;       /* [esp+16], [esp+20], [esp+24] */
    DWORD have_agent;             /* 0 = the block below is not meaningful */
    DWORD id;                     /* +0x10 */
    DWORD flags;                  /* +0x20 -- bit 18 is isWaypoint */
    DWORD stop;                   /* +0x48 m_timeStopMovement, the arrival tick */
    DWORD x98;                    /* +0x98 -- MOVECODE-Q3's field */
    DWORD point[4];               /* +0x78 m_point       : where the body IS */
    DWORD segment[4];             /* +0x88 m_segmentPoint: the leg's end */
    DWORD target[4];              /* +0x9C m_targetPoint : the destination */
    /* DEREFERENCED POINTER ARGUMENTS, and the record is v3 because of them.
     *
     * `MapFindPath`'s from/to and `AgApi`'s targetPoint are passed BY REFERENCE, so
     * a record holding only the argument dwords holds addresses in the client's
     * address space and nothing replayable. Writing `pathdiff.py` is what surfaced
     * it: the replay harness had no coordinates to replay. Which args to follow is
     * per site (`deref_a` / `deref_b`, 1-based, 0 = none) and comes from the
     * content rows, so this stays a table-driven property rather than a special
     * case for one address.
     *
     * SEPARATE FIELDS rather than reusing `point`/`segment`, which are dead when
     * `have_agent` is 0. Aliasing one slot to two meanings is how a reader ends up
     * confidently plotting a query as a body position. `have_pts` says which of the
     * two were actually read. */
    DWORD have_pts;               /* bit 0 = pt_a valid, bit 1 = pt_b valid */
    DWORD pt_a[4];
    DWORD pt_b[4];
    /* v4: WHAT IT TAKES TO SEE A WARP AT ALL.
     *
     * Runs 1 and 2 both reported `m_point -> m_targetPoint` at the teleport as
     * "over 100 u, a visible warp". It is nothing of the kind: `m_point` (+0x78) is
     * the last COMMITTED position -- the extrapolator brings it forward only on
     * demand -- so at the arrival tick it still holds where the leg STARTED, and the
     * figure is the LEG's LENGTH. Run 2 settled it: 25 of 25 consecutive teleports
     * chain to exactly 0.00, target[N] == m_point[N+1] to the bit.
     *
     * A warp is the body being somewhere the client did not walk it to, so seeing
     * one needs the position the client would RENDER: m_point advanced by velocity
     * over (arrival tick - point timestamp). Those are the two fields below, and
     * without them the question cannot be asked. `0x005FFC19` is the client's own
     * form: `out.x = [esi+0x78] + vx * dt`, dt in ms scaled by 0.001. */
    DWORD vel[2];                 /* +0xB0, +0xB4 -- velocity x, y */
    DWORD ptime;                  /* +0x58 -- the timestamp m_point is valid AT */
    /* v5: THE OTHER SIDE OF A CORRECTION.
     *
     * Run 4 caught the snap for the first time -- 11 `snaptest` calls, 6 `reseed`
     * calls, and 18 position jumps that dead reckoning cannot explain. But both
     * sites take a SECOND AGENT as an argument and the record held only `this`,
     * which is half of a correction: `reseed` reads its arg1 as an agent
     * (`0x006022C0` -> edi, then `[edi+0x24]`, `[edi+0x48]`, `[edi+0x88..0x90]`),
     * and `snaptest` reads its arg2 the same way (`[ebx+0x24]` under assert
     * AgTrack:458 `source.GetWorld() == WORLD_SYNC`).
     *
     * With both sides captured the separation the test judges can be RECOMPUTED
     * offline, which matters because an entry hook cannot see which gate the
     * function chose -- and run 4 made zero `MapFindPath` calls at range 300, so
     * gate 2 was not the decider and the gate is still unmeasured.
     *
     * Which argument holds it is per site (`deref_agent_arg`, 1-based, 0 = none),
     * from the content rows, so this stays table-driven. */
    DWORD have_src;
    DWORD src_id, src_flags, src_stop, src_ptime;
    DWORD src_point[4];
    DWORD src_segment[4];
    DWORD src_target[4];
    DWORD src_vel[2];
    /* v6, 2026-08-28: THE WORLD FIELD, THE FACING, AND THE AGTRACK FENCE.
     *
     * APPENDED, never inserted, and that is the whole reason this block sits at
     * the bottom of a struct whose grouping would prefer `world` next to `id`.
     * sec.1e.3: readhook described v3 as scalars + [point, segment, target, pt_a,
     * pt_b] with `have_pts` among the scalars while this file declared it AFTER
     * target[4]. Both totalled 38 dwords, so `reclen` matched and the guard whose
     * own message warns about "a record whose fields would silently shift" could
     * not fire -- every point block was read one dword late for a whole run. A
     * LENGTH CHECK CANNOT CATCH A REORDER. Appending changes the length, so a
     * mismatched reader fails loudly instead.
     *
     * `world` (+0x24) closes sec.1i.7's standing item: the sync side has been
     * identified from call-site STRUCTURE (which argument reseed takes) rather
     * than from the record, which works but is indirect. WORLD_SYNC is the
     * literal 0 -- AgTrack:458's assert body runs when the field is non-zero.
     *
     * `facing` (+0xC4) is the second half of snaptest's early-out at 0x0060563A,
     * `cmp dword [ebx+0xc4], 9` / `je 0x605683` where 0x605683 is `mov eax, 1`.
     * Its first half, m_timeStopMovement, is already captured as `stop`/`src_stop`,
     * so this ONE field makes a NO-SNAP-before-any-gate evaluable offline. ebx
     * there is arg2, the agent snaptest already dereferences -- which is why the
     * early-out costs an offset and not the two mid-function sites sec.1s.9 asked
     * for, neither of which gensites would have accepted.
     *
     * `fence` is agtrack's per-agent `clientControlled` dword -- the operand of
     * the branch at 0x00606009 that skips the whole snap path on zero. Read HERE,
     * at the entry, on the same invocation that then branches on it. sec.1s.8
     * item 1's defect was that this was SAMPLED by movetap at 11.4 Hz against a
     * median shut run of 13 samples, by a classifier the counted outcome mutates;
     * reading the operand at the decision is the fix. `have_fence` distinguishes
     * "read it, it was 0" from "could not read it", which is the distinction a
     * bare 0 would destroy. */
    DWORD world, facing;
    DWORD src_world, src_facing;
    DWORD have_fence, fence;
    /* v7, 2026-08-29: THE ANSWER, not just the question -- the MapFindPath
     * RETURN tap (HANDOFF-PLANE.md §4.2). Appended, never inserted, for the
     * reason the v6 block above states.
     *
     * `esp` IS THE JOIN KEY AND ITS OWN AUDIT, and it is stored on EVERY site
     * rather than only the ret ones. All four MapFindPath exits are
     * `8B E5 5D C3` -- `mov esp,ebp / pop ebp / ret` -- so esp at a ret is
     * EXACTLY the esp the entry hook saw one call earlier, which is what lets a
     * reader pair an answer to its question on (tid, esp). Storing it
     * universally costs one dword and makes the pairing's precondition
     * CHECKABLE: a pair whose two esp values disagree refutes that paragraph
     * rather than being a bad record, and `pathdiff.py` must say so out loud
     * instead of pairing anyway. An instrument has to be able to report that
     * the thing it was built on turned out to be false.
     *
     * `have_out` is `have_fence`'s lesson applied again, and here the
     * distinction IS the measurement: bit 0 says outCount was READ, so "could
     * not read it" and "the client answered ZERO" stay different facts -- and
     * pathCount == 0 under a lock is exactly what §4.2 predicts.
     *
     * `out_n` vs `out_count` makes TRUNCATION visible rather than silent:
     * out_count is the client's own answer, out_n is how many points this
     * record kept. RET_MAX_POINTS is 9 as of 2026-08-29 -- the larger of the
     * two callers' own maxCount, so the buffer cannot truncate for either.
     * See the define for the price and for why 9 rather than a percentile.
     *
     * THE BOUND IS THE LITERAL 36, NOT AN EXPRESSION, and that is a
     * requirement rather than a style: test_movehook.py §11 parses this struct
     * out of the C with `\[\s*(\d+)\s*\]` and compares it field-by-field to
     * readhook's layout table. `[RET_MAX_POINTS * 4]` would not match that
     * pattern, the field would drop silently out of §11's parse, and the one
     * check that can catch a reader/writer disagreement would stop covering
     * the widest field in the record. */
    DWORD esp;
    DWORD have_out;               /* bit 0 = out_count read, bit 1 = out_path */
    DWORD out_count;              /* *arg5 -- the client's own pathCount */
    DWORD out_n;                  /* points actually copied (<= out_count) */
    DWORD out_path[36];           /* RET_MAX_POINTS * 4 dwords, {x,y,plane,w} */
} rec_t;

static DWORD  g_base;
static DWORD  g_addr[NSITES];
static BYTE   g_orig[NSITES];
static volatile LONG g_hits[NSITES];
static int    g_armed[NSITES];   /* did the 0xCC actually go in? */
static volatile LONG g_n = 0;
static rec_t  g_rec[NCAP];

static volatile LONG  g_selfhit = 0;      /* control A */
static volatile LONG  g_ctlhit  = 0;      /* control B */
static DWORD  g_selfprobe = 0;
static DWORD  g_ctl = 0;
static BYTE   g_ctl_orig;
static volatile LONG g_ctl_armed = 0;
static const char *g_why = "unknown";

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
    DWORD base, end;
    if (!p || (p & 3u)) return 0;
    /* Overflow FIRST, before any arithmetic that could wrap. `p + n` for p near
     * 0xFFFFFFFF wraps to a small number that compares happily against the region
     * end, so the range check would pass on a pointer that is nowhere near the
     * region. Unreachable today -- VirtualQuery fails on kernel-space addresses
     * and this is a 32-bit user process -- but a bounds check whose own arithmetic
     * can wrap is not a bounds check, and the cost of getting it right is a line. */
    if (n == 0 || p > 0xFFFFFFFFu - n) return 0;
    if (!VirtualQuery((LPCVOID)p, &mbi, sizeof mbi)) return 0;
    if (mbi.State != MEM_COMMIT) return 0;
    /* PAGE_NOACCESS and PAGE_GUARD are the two that fault on a read. Note
     * PAGE_EXECUTE (execute-only, no read) also would on hardware that enforces
     * it; x86 page tables do not, and Windows maps it readable, so it is not
     * screened here. */
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return 0;
    base = (DWORD)(ULONG_PTR)mbi.BaseAddress;
    if (mbi.RegionSize > 0xFFFFFFFFu - base) end = 0xFFFFFFFFu;
    else end = base + (DWORD)mbi.RegionSize;
    if (p + n > end) return 0;
    return 1;
}

static void copy4(DWORD *dst, DWORD src)
{
    if (readable(src, 16)) memcpy(dst, (const void *)src, 16);
}

/* Follow a POINTER ARGUMENT and copy the 16-byte point it names.
 *
 * `which` is 1-based over the caller's stack args and 0 means "this site has no
 * such pointer" -- the site table carries it, so which args are references is a
 * property of the row rather than a branch on an address. Returns 1 when the point
 * was actually read, so the record can say which halves are real instead of
 * leaving a zeroed point looking like the origin. */
/* Copy an agent's position block. Shared by `this` and by a SECOND agent named in
 * an argument, so the two cannot drift apart -- the run-4 record had `this` only,
 * which is half of a correction. Returns 0 when the pointer is not readable. */
static int read_agent(DWORD ag, DWORD *id, DWORD *flags, DWORD *stop, DWORD *ptime,
                      DWORD *point, DWORD *segment, DWORD *target, DWORD *vel,
                      DWORD *world, DWORD *facing)
{
    /* The guard was 0xB8 and `facing` lives at +0xC4, so it now has to cover
     * +0xC8. Widening a bounds check is not a formality here: reading four bytes
     * past a committed page inside a VECTORED HANDLER faults in a way nobody
     * could attribute to us, which is the whole reason `readable` exists. */
    if (!readable(ag, A_FACING + 4u)) return 0;
    *id     = *(DWORD *)(ag + A_ID);
    *flags  = *(DWORD *)(ag + A_FLAGS);
    *stop   = *(DWORD *)(ag + A_TIME_STOP_MOVEMENT);
    *ptime  = *(DWORD *)(ag + A_POINT_TIME);
    *world  = *(DWORD *)(ag + A_WORLD);
    *facing = *(DWORD *)(ag + A_FACING);
    memcpy(point,   (const void *)(ag + A_POINT),         16);
    memcpy(segment, (const void *)(ag + A_SEGMENT_POINT), 16);
    memcpy(target,  (const void *)(ag + A_TARGET_POINT),  16);
    memcpy(vel,     (const void *)(ag + A_VELOCITY),       8);
    return 1;
}

static int deref_arg(DWORD esp, int which, DWORD *dst)
{
    DWORD p;
    if (which < 1 || which > 6) return 0;
    if (!readable(esp, 4u * (DWORD)(which + 1))) return 0;
    p = ((DWORD *)esp)[which];
    if (!readable(p, 16)) return 0;
    memcpy(dst, (const void *)p, 16);
    return 1;
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
     * emulated, only restored.
     *
     * MATCHED ON ADDRESS ALONE, and the earlier `g_ctl_armed && a == g_ctl` was a
     * MEASURED crash rather than a theoretical one: an adversarial probe on this
     * machine produced 11 unhandled EXCEPTION_BREAKPOINTs per 400 trials x 8
     * threads with the flag in the condition, and ZERO with `trnint3.c`'s
     * unconditional form. Two triggers, neither exotic -- two threads inside the
     * ~10-30 us restore window (control B deliberately picks a byte a live thread
     * was executing), or ONE thread whose trap dispatches just after the worker's
     * CTLB_MS timeout clears the flag. Either way the handler declined a trap IT
     * PLANTED and the client took an unhandled breakpoint. movehook had regressed
     * its own precedent; this restores it.
     *
     * The restore has a SINGLE OWNER (InterlockedExchange), because the handler and
     * the worker could otherwise poke the same page concurrently -- one restoring
     * PAGE_EXECUTE_READ while the other is mid-write, which faults inside a
     * vectored handler. And `g_ctlhit` publishes LAST, so the worker cannot wake and
     * start its own restore before this one has finished. */
    if (g_ctl && a == g_ctl) {
        if (InterlockedExchange(&g_ctl_armed, 0))
            poke(g_ctl, g_ctl_orig, NULL);
        InterlockedExchange(&g_ctlhit, 1);
        c->Eip = a;
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    for (i = 0; i < NSITES; i++) {
        LONG nth;
        if (a != g_addr[i]) continue;
        nth = InterlockedIncrement(&g_hits[i]);
        /* STRIDE, added 2026-08-28 for the per-frame tick site.
         *
         * `g_hits[i]` counts EVERY occurrence and is what the sidecar reports, so
         * a strided site still yields an exact denominator -- which for the tick
         * is the whole point: we need the per-frame COUNT, not per-frame records.
         * Storage is what the ring cannot afford. The movement tick runs per agent
         * per frame, so at ~30 fps over two agents an 8-minute run offers ~29,000
         * occurrences against NCAP 32768 -- and the worker loop at the bottom of
         * this file ENDS THE RUN when the ring fills, so an unstrided tick would
         * not merely truncate the tail, it would cut the capture short and starve
         * every other site of the rest of the session.
         *
         * A stride of N stores occurrence 1, N+1, 2N+1 ... so a site always
         * contributes its FIRST hit (a site that fired once still appears) and the
         * stored records stay evenly spaced for timing. Sites with stride 0 or 1
         * are unaffected, which is every site that existed before this.
         *
         * IT GATES THE RECORD ONLY. The first version of this was
         * `if (strided out) continue;` and it CRASHED THE CLIENT on the first run
         * that armed the tick -- c0000005, within seconds. `continue` leaves the
         * for-loop, and the `push ebp` emulation at the BOTTOM of this loop body
         * is what keeps the client running: skip it and EIP never advances past
         * the 0xCC and the frame is never built. 63 of every 64 tick hits took
         * that path. The comment on that emulation block already said "this must
         * happen on every hit -- a skipped prologue is a corrupted frame, not a
         * missing sample", and the `continue` was written directly above it.
         * So the stride is an `if` around the RECORD, never a jump past the
         * EMULATION, and `test_movehook.py` §15 now refuses a `continue` anywhere
         * between the address match and the emulation. */
        if (!(SITES[i].stride > 1u
              && ((DWORD)(nth - 1) % SITES[i].stride) != 0u)) {
            LONG slot = InterlockedIncrement(&g_n) - 1;
            if (slot < (LONG)NCAP) {
                rec_t *r = &g_rec[slot];
                DWORD esp = c->Esp, ag = c->Ecx;
                /* A3-F5: the slot is claimed by the Interlocked above but FILLED
                 * here, and the worker's Sleep(150) is the only thing between a
                 * preempted handler and `fwrite`. A half-written record decodes as
                 * a real one (all-zero reads as site 0, seq 0) and gets counted.
                 * So `tick` is written LAST and IS the commit flag: memset leaves
                 * it 0, and GetTickCount never returns 0 in practice, so `tick != 0`
                 * marks a complete record for EVERY slot. (`seq == slot` was tried
                 * first and fails for slot 0, where a zeroed record has seq 0 too.)
                 * readhook.py drops anything still 0. It costs one store. */
                memset(r, 0, sizeof *r);
                r->seq = (DWORD)slot;
                r->site = i;
                r->tid = GetCurrentThreadId();
                r->ecx = ag;
                /* THE PAIRING KEY, on every site. See the note on rec_t: for
                 * one invocation the entry hook and the ret hook see the SAME
                 * esp, so (tid, esp) joins a question to its answer -- and a
                 * pair that disagrees refutes the design rather than being a
                 * bad record. */
                r->esp = esp;
                /* esp is untouched: the `push ebp` we replaced has not run.
                 * Six args in one guarded read; see the note on rec_t. Falls back
                 * to four dwords when the stack is short, so a thread near the
                 * bottom of its stack still yields the return address rather than
                 * nothing at all. */
                if (readable(esp, 28)) {
                    r->retaddr = ((DWORD *)esp)[0];
                    r->arg1    = ((DWORD *)esp)[1];
                    r->arg2    = ((DWORD *)esp)[2];
                    r->arg3    = ((DWORD *)esp)[3];
                    r->arg4    = ((DWORD *)esp)[4];
                    r->arg5    = ((DWORD *)esp)[5];
                    r->arg6    = ((DWORD *)esp)[6];
                } else if (readable(esp, 16)) {
                    r->retaddr = ((DWORD *)esp)[0];
                    r->arg1    = ((DWORD *)esp)[1];
                    r->arg2    = ((DWORD *)esp)[2];
                    r->arg3    = ((DWORD *)esp)[3];
                }
                /* A SECOND AGENT, when the row names one. Same reader as `this`. */
                if (SITES[i].deref_agent_arg >= 1 &&
                    SITES[i].deref_agent_arg <= 6 &&
                    readable(esp, 4u * (DWORD)(SITES[i].deref_agent_arg + 1))) {
                    DWORD src = ((DWORD *)esp)[SITES[i].deref_agent_arg];
                    r->have_src = read_agent(src, &r->src_id, &r->src_flags,
                                             &r->src_stop, &r->src_ptime,
                                             r->src_point, r->src_segment,
                                             r->src_target, r->src_vel,
                                             &r->src_world, &r->src_facing);
                }
                /* THE AGTRACK FENCE, for the one row that declares it.
                 *
                 * agtrack computes `record = [this+0x20] + id*0x1C` and branches
                 * on `[record]` at 0x00606009, skipping the entire snap path when
                 * it is zero. Reproduced here from the two things the entry has:
                 * ecx (`this`) and the agent named by deref_agent_arg. The stride
                 * is the client's own `lea ecx,[ebx*8] / sub ecx,ebx` -- id*7
                 * dwords -- not a constant anyone chose.
                 *
                 * Guarded at every level, because this runs inside the vectored
                 * handler and a wild id would index anywhere: the base must be
                 * readable, the id is bounded against the client's OWN bound at
                 * [this+0x28] (the same one its Array.h:587 assert checks), and
                 * the record itself is range-checked before the read. `have_fence`
                 * stays 0 if any of that fails, so a refusal is distinguishable
                 * from a genuine zero -- which is the whole measurement. */
                if (SITES[i].deref_fence && r->have_src) {
                    DWORD base = 0, bound = 0;
                    if (readable(ag + 0x20u, 4) && readable(ag + 0x28u, 4)) {
                        base  = *(DWORD *)(ag + 0x20u);
                        bound = *(DWORD *)(ag + 0x28u);
                        if (r->src_id < bound && bound < 0x100000u) {
                            DWORD off = r->src_id * 0x1Cu;
                            if (readable(base + off, 4)) {
                                r->fence = *(DWORD *)(base + off);
                                r->have_fence = 1;
                            }
                        }
                    }
                }
                if (deref_arg(esp, SITES[i].deref_a, r->pt_a)) r->have_pts |= 1u;
                if (deref_arg(esp, SITES[i].deref_b, r->pt_b)) r->have_pts |= 2u;
                /* THE OUT-PARAMS, for the rows that name them -- table-driven
                 * like every other deref, so this stays a property of the
                 * content rows rather than a special case for one address.
                 *
                 * Only meaningful at a RET: at the entry these pointers aim at
                 * uninitialised caller memory (content/movecode.toml's
                 * mapfindpath `limits`), which is the whole reason this tap
                 * exists. Nothing here enforces that -- gensites does, by
                 * refusing the shape/deref combinations that would be wrong.
                 *
                 * The count is read FIRST and gates the path read, because the
                 * count is what says how much of the buffer the callee wrote:
                 * copying RET_MAX_POINTS unconditionally would hand back
                 * uninitialised stack for any answer shorter than that and a
                 * reader could not tell which points were real. */
                if (SITES[i].deref_out >= 1 && SITES[i].deref_out <= 6 &&
                    readable(esp, 4u * (DWORD)(SITES[i].deref_out + 1))) {
                    DWORD p = ((DWORD *)esp)[SITES[i].deref_out];
                    if (readable(p, 4)) {
                        r->out_count = *(DWORD *)p;
                        r->have_out |= 1u;
                    }
                }
                if (SITES[i].deref_out_path >= 1 && SITES[i].deref_out_path <= 6 &&
                    (r->have_out & 1u) &&
                    readable(esp, 4u * (DWORD)(SITES[i].deref_out_path + 1))) {
                    DWORD n = r->out_count;
                    DWORD p = ((DWORD *)esp)[SITES[i].deref_out_path];
                    if (n > RET_MAX_POINTS) n = RET_MAX_POINTS;
                    if (n && readable(p, 16u * n)) {
                        memcpy(r->out_path, (const void *)p, 16u * n);
                        r->out_n = n;
                        r->have_out |= 2u;
                    }
                }
                /* `this`, through the SAME reader the second agent uses. It was a
                 * separate inline copy until v5, which is how two readings of one
                 * struct drift: add a field to one and the other still parses, so
                 * a correction's two sides would be described differently by
                 * construction. `+0x98` is the one field only `this` carries,
                 * because only the setter path has anything to say about it. */
                if (SITES[i].deref_agent) {
                    r->have_agent = read_agent(ag, &r->id, &r->flags, &r->stop,
                                               &r->ptime, r->point, r->segment,
                                               r->target, r->vel,
                                               &r->world, &r->facing);
                    if (r->have_agent)
                        r->x98 = *(DWORD *)(ag + A_X98);
                }
                /* COMMIT. Every field above is in place; this store is what
                 * makes the record readable. See the note at the memset. */
                r->tick = GetTickCount();
            }
        }
        /* Re-emulate the ONE instruction THIS SITE'S SHAPE displaced. This must
         * happen on every hit -- a skipped instruction is a corrupted frame, not
         * a missing sample -- and it is what keeps the breakpoint ARMED, because
         * the 0xCC is never restored. BOTH ARMS MUST ASSIGN c->Eip: an arm that
         * falls through without one leaves Eip on the 0xCC and re-traps forever,
         * which is why test_movehook.py §15 counts the assignments rather than
         * only scanning for `continue`. */
        if (SITES[i].shape == SHAPE_RET) {
            /* `C3 ret`: eip = [esp]; esp += 4. Bare near ret -- gensites refuses
             * any byte but 0xC3 for this shape, so there is no imm16 to add. */
            if (readable(c->Esp, 4)) {
                c->Eip = *(DWORD *)c->Esp;
                c->Esp += 4;
            } else {
                /* NO SAFE SKIP AT A RET (see the file header). Restore the byte
                 * and rewind, control B's proven technique: the client executes
                 * its own `ret` once, unpatched. The site is then DISARMED and
                 * must say so, because a silently disarmed site reports `hits`
                 * about us and a zero about the client. */
                poke(a, g_orig[i], NULL);
                g_armed[i] = 0;
                c->Eip = a;
            }
        } else {
            /* `55 push ebp`: then resume at site+1, the `mov ebp, esp`. */
            c->Esp -= 4;
            *(DWORD *)c->Esp = c->Ebp;
            c->Eip = a + 1;
        }
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

static int mkdirs(const char *dir)
{
    char buf[MAX_PATH];
    size_t i;
    DWORD attr;
    strncpy(buf, dir, sizeof buf - 1);
    buf[sizeof buf - 1] = 0;
    for (i = 1; buf[i]; i++)
        if (buf[i] == '\\') { buf[i] = 0; CreateDirectoryA(buf, NULL); buf[i] = '\\'; }
    CreateDirectoryA(buf, NULL);
    /* CreateDirectoryA failing with ALREADY_EXISTS is the success case, so the
     * return value cannot be read directly -- ask the filesystem instead. The
     * old version returned void and the caller ignored it either way, which is
     * half of why the R5 capture vanished without a word. */
    attr = GetFileAttributesA(buf);
    return attr != INVALID_FILE_ATTRIBUTES
        && (attr & FILE_ATTRIBUTE_DIRECTORY) != 0;
}

/* ---------------------------------------------------------------------------
 * THE WRITER, and why it is Win32 rather than the CRT it used to be.
 *
 * MOVECODE R5 (2026-08-28): the operator armed an 8-minute run, played, ran
 * `attach.py --stop`, and got NOTHING -- no movehook.bin, no movehook.txt, and
 * no output directory at all. `movehook.stop` was still on disk afterwards,
 * which is the tell: the worker clears it only AFTER its poll loop exits, so
 * the loop never exited and the single end-of-run write never ran. The whole
 * capture was lost and the run had to be scored from the server log instead.
 *
 * Three defects, all of them this file's:
 *
 *   1. THE WRITE HAPPENED EXACTLY ONCE, at the end. Any ending the loop does
 *      not reach -- the client exiting, the worker dying, a hang -- discards
 *      every record. Now `snapshot()` runs on a timer during the loop, so the
 *      worst case is FLUSH_MS of loss instead of the whole run.
 *   2. NOTHING WAS WRITTEN WHEN THE PROCESS EXITED. DllMain now writes on
 *      DLL_PROCESS_DETACH -- which is why this writer uses CreateFileA/
 *      WriteFile instead of fopen/fwrite. At process shutdown the CRT may
 *      already be torn down and its stdio is not safe to call under the loader
 *      lock; the Win32 file API is. The .txt report keeps using stdio and is
 *      NOT written from DllMain, because it is a convenience, not the data.
 *   3. A FAILED WRITE WAS SILENT. fopen's NULL was dropped on the floor, so an
 *      unwritable path looked exactly like a run that captured nothing. Every
 *      failure now lands in g_werr/g_wpath and is reported twice: in
 *      movehook.txt, and in a `movehook.status` file BESIDE THE DLL, which is
 *      the one place still writable when the configured output path is not.
 * ------------------------------------------------------------------------- */
/* THE OUTPUT PATH, RESOLVED ONCE AND CACHED -- and this is not a tidy-up.
 *
 * `outdir()` reads movehook.cfg through fopen/fgets EVERY call. At
 * DLL_PROCESS_DETACH every other thread has already been terminated, possibly
 * inside the CRT holding its locks, so calling it there can return an empty
 * buffer or hang -- and an empty dir makes write_bin fail with no file and no
 * clue. That is the exact hazard this file already documents for the WRITER,
 * walked into again one line away from it. Caught by test_movehook.py §16 only
 * once the periodic snapshot existed: before that, the detach write was the
 * first write of the run, so "a file appeared" could not tell the two apart.
 * The mtime comparison is what made it visible.
 *
 * So: the worker resolves the path once, while the process is healthy, and the
 * detach path reads this and never the file. */
static char g_outdir[MAX_PATH];

static const char *outdir_cached(void)
{
    return g_outdir[0] ? g_outdir : DEFDIR;
}

/* Path building for the shutdown path uses kernel32 rather than the CRT, for
 * the same reason. lstrcpynA/lstrcatA are kernel32 exports and stay valid. */
static void path_join(char *out, size_t n, const char *dir, const char *leaf)
{
    lstrcpynA(out, dir, (int)n);
    lstrcatA(out, leaf);
}

static volatile LONG g_wrote = 0;      /* successful .bin writes this run */
static DWORD g_werr = 0;               /* GetLastError of the last failure */
static char  g_wpath[MAX_PATH];        /* what it was trying to write */
static volatile LONG g_final_written = 0;

static int put(HANDLE h, const void *p, DWORD n)
{
    DWORD done = 0;
    return WriteFile(h, p, n, &done, NULL) && done == n;
}

/* Serialise `n` records to <dir>\movehook.bin. Same v6 layout as before, byte
 * for byte -- readhook.py is unchanged. */
static int write_bin(const char *dir, DWORD n)
{
    char path[MAX_PATH];
    HANDLE h;
    DWORD ver = 8, ns = NSITES, reclen = (DWORD)sizeof(rec_t);
    unsigned i;
    int ok = 1;

    if (!dir || !dir[0]) {                 /* an empty path writes nowhere */
        g_werr = ERROR_BAD_PATHNAME;
        lstrcpynA(g_wpath, "(no output directory resolved)", MAX_PATH);
        return 0;
    }
    if (!mkdirs(dir)) {
        g_werr = GetLastError();
        path_join(g_wpath, sizeof g_wpath, dir, "  (could not create directory)");
        return 0;
    }
    path_join(path, sizeof path, dir, "\\movehook.bin");
    /* A partial file is worse than none: write beside it and rename over, so a
     * reader never sees a half-flushed snapshot. */
    {
        char tmp[MAX_PATH];
        path_join(tmp, sizeof tmp, dir, "\\movehook.bin.part");
        h = CreateFileA(tmp, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                        FILE_ATTRIBUTE_NORMAL, NULL);
        if (h == INVALID_HANDLE_VALUE) {
            g_werr = GetLastError();
            lstrcpynA(g_wpath, tmp, MAX_PATH);
            return 0;
        }
        if (n > NCAP) n = NCAP;
        ok &= put(h, "MVHK", 4);
        ok &= put(h, &ver, 4);
        ok &= put(h, &g_base, 4);
        ok &= put(h, &ns, 4);
        ok &= put(h, &reclen, 4);
        ok &= put(h, &n, 4);
        for (i = 0; i < NSITES; i++) {
            DWORD rva = (DWORD)SITES[i].rva, hits = (DWORD)g_hits[i];
            ok &= put(h, &rva, 4);
            ok &= put(h, &hits, 4);
        }
        if (n) ok &= put(h, g_rec, n * (DWORD)sizeof(rec_t));
        if (!ok) g_werr = GetLastError();
        CloseHandle(h);
        if (ok) {
            if (!MoveFileExA(tmp, path, MOVEFILE_REPLACE_EXISTING)) {
                ok = 0;
                g_werr = GetLastError();
            }
        }
        if (!ok) {
            lstrcpynA(g_wpath, path, MAX_PATH);
            return 0;
        }
    }
    InterlockedIncrement(&g_wrote);
    return 1;
}

/* How many records a snapshot may safely serialise while the handler is still
 * appending. A handler claims its slot with InterlockedIncrement and THEN fills
 * it, so the newest few slots can be half-written; hold that many back. The
 * final write does not need the slack -- it runs after the sites are disarmed
 * and the in-flight sleep. */
#define FLUSH_SLACK 32u
#define FLUSH_MS    15000u

/* WRITES EVEN AT ZERO RECORDS, for the same reason the detach path does: a
 * header-only capture still carries the per-site hit counts, and "no file at
 * all" is the exact ambiguity that cost R5 its diagnosis. It also makes the
 * FIRST flush a live proof that the output path works, mid-run, while the
 * operator can still do something about it -- and it makes this path testable
 * (test_movehook.py §16), which a `return` on empty made impossible in a host
 * where no site can arm. */
static void snapshot(const char *dir)
{
    LONG n = g_n;
    n = (n > (LONG)FLUSH_SLACK) ? n - (LONG)FLUSH_SLACK : 0;
    write_bin(dir, (DWORD)n);
}

/* The one report that is still written when the configured output path is not
 * writable. Beside the DLL, where attach.py already looks for the cfg. */
static void write_status(const char *dir, const char *note)
{
    char path[MAX_PATH], line[1024];
    HANDLE h;
    beside_dll(path, sizeof path, "movehook.status");
    if (!path[0]) return;
    h = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS,
                    FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    snprintf(line, sizeof line,
             "movehook status\r\n"
             "out dir: %s\r\n"
             "state:   %s\r\n"
             "records: %ld\r\n"
             "bin writes that succeeded: %ld\r\n"
             "last write error: %lu%s%s\r\n",
             dir, note, (long)g_n, (long)g_wrote, (unsigned long)g_werr,
             g_wpath[0] ? "  writing " : "", g_wpath[0] ? g_wpath : "");
    put(h, line, (DWORD)strlen(line));
    CloseHandle(h);
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
    /* A3-F4. Control A executes an `int3` unconditionally a few lines below. If
     * registration failed, that int3 kills Gw.exe the instant the DLL is injected
     * and writes no file at all -- an unattributable crash, which is the worst
     * possible failure for an instrument. Refuse instead. */
    if (!veh)
        return 0;

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

    /* CONTROL B, and the ORDER HERE IS LOAD-BEARING TWICE OVER.
     *
     * It runs before the measurement sites are armed, so (1) its hit cannot be
     * confused with one of theirs, and (2) -- the safety half --
     * `sample_client_eip` SUSPENDS client threads to read their Eip, and at this
     * point no client thread can possibly be inside our vectored handler, because
     * nothing of ours is armed in client code yet. Suspending a thread that was
     * mid-handler would be a deadlock waiting to be discovered on someone's
     * machine. Arming first and sampling second would be the same code and a much
     * worse program. */
    if (text_span(g_base, &tlo, &thi)) {
        g_ctl = sample_client_eip(tlo, thi);
        if (g_ctl && poke(g_ctl, 0xCC, &g_ctl_orig)) {
            InterlockedExchange(&g_ctl_armed, 1);
            while (!g_ctlhit && waited < CTLB_MS) { Sleep(25); waited += 25; }
            if (InterlockedExchange(&g_ctl_armed, 0))
                poke(g_ctl, g_ctl_orig, NULL);
        }
    }

    /* A stop file left over from a previous run would end this one instantly. */
    clear_stop();

    /* A4-F2: the return was ignored here, so a site whose patch FAILED reported
     * `hits 0` with both controls green -- a confident zero about the client that
     * was really a fact about us. Recorded per site and printed. */
    for (i = 0; i < NSITES; i++)
        g_armed[i] = poke(g_addr[i], 0xCC, &g_orig[i]);

    /* The output directory is resolved and PROVEN WRITABLE BEFORE the run,
     * not after it. R5 spent eight minutes capturing into a path that was
     * never created; the status file says so in the first second instead. */
    lstrcpynA(g_outdir, outdir(), MAX_PATH);
    dir = outdir_cached();
    write_status(dir, "armed");

    waited = 0;
    {
        DWORD since_flush = 0;
        while (waited < run_ms && g_n < (LONG)NCAP && !stop_requested()) {
            Sleep(100);
            waited += 100;
            since_flush += 100;
            /* THE PERIODIC SNAPSHOT. Bounds the loss from any ending this loop
             * does not reach to FLUSH_MS, which is the whole point: R5 lost 8
             * minutes because the only write was past the end of this loop. */
            if (since_flush >= FLUSH_MS) {
                since_flush = 0;
                snapshot(dir);
                write_status(dir, "running (periodic snapshot)");
            }
        }
    }
    g_why = (g_n >= (LONG)NCAP) ? "ring full"
          : (waited >= run_ms)  ? "timer elapsed"
                                : "stopped by request (movehook.stop)";
    clear_stop();

    for (i = 0; i < NSITES; i++)
        if (g_armed[i]) poke(g_addr[i], g_orig[i], NULL);
    Sleep(150);                       /* let in-flight handlers finish */
    /* A3-F3: the handler is DELIBERATELY LEFT REGISTERED. Sleep(150) is a guess,
     * not synchronisation, and there is no in-flight count to drain -- so a trap
     * raised before the restore but dispatched after it can still arrive. The site
     * path survives that: `g_addr[]` is never cleared, so a straggler still matches
     * and still emulates its `push ebp` correctly even though the byte is back.
     * UNREGISTERING is the only thing that would make such a straggler fatal, and
     * it buys nothing here -- this DLL is never unloaded. So we keep it. */
    (void)veh;

    /* The final write. No FLUSH_SLACK here: the sites are disarmed and the
     * in-flight sleep is done, so every claimed slot is filled. */
    if (write_bin(dir, (DWORD)g_n))
        InterlockedExchange(&g_final_written, 1);
    write_status(dir, g_final_written ? "finished, capture written"
                                      : "finished, BUT THE WRITE FAILED");

    snprintf(path, sizeof path, "%s\\movehook.txt", dir);
    f = fopen(path, "w");
    if (f) {
        LONG total = 0;
        fprintf(f, "movehook -- MOVECODE-B2\n");
        fprintf(f, "base 0x%08X  ran %ums  capacity %u\n",
                (unsigned)g_base, (unsigned)waited, (unsigned)NCAP);
        fprintf(f, "ended: %s\n", g_why);
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
            fprintf(f, "  %-10s rva 0x%08X va 0x%08X  hits %ld%s\n",
                    SITES[i].name, (unsigned)SITES[i].rva,
                    (unsigned)g_addr[i], (long)g_hits[i],
                    g_armed[i] ? "" : "   *** NEVER ARMED: the patch FAILED, so "
                                      "this zero is about us, not the client ***");
        }
        fprintf(f, "\nhits %ld  stored %ld of %u%s\n", (long)total, (long)g_n,
                (unsigned)NCAP,
                g_n >= (LONG)NCAP ? "  RING FULL -- the run was truncated and the "
                                    "tail is missing" : "");
        fprintf(f, "capture writes that succeeded: %ld%s\n", (long)g_wrote,
                g_wrote ? "" : "   *** NONE -- there is no movehook.bin for this "
                               "run, and every number above exists only in this "
                               "file ***");
        if (g_werr)
            fprintf(f, "last write error: %lu writing %s\n",
                    (unsigned long)g_werr, g_wpath);
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
    } else if (reason == DLL_PROCESS_DETACH) {
        /* THE CLIENT IS EXITING WITH A RUN STILL ARMED -- the case that cost
         * R5 its whole capture. Everything here is Win32 only: at this point
         * the CRT may already be torn down and stdio is not safe under the
         * loader lock, which is why write_bin uses CreateFileA/WriteFile and
         * why the .txt report is deliberately NOT written from here.
         *
         * FLUSH_SLACK is kept because the sites may still be armed: a handler
         * can be mid-record on another thread even now. Skipped entirely once
         * the worker's own final write has happened, so a normal ending never
         * pays for this and never overwrites the complete file with a
         * short one.
         *
         * IT WRITES EVEN AT ZERO RECORDS, deliberately. A header-only capture
         * still carries the per-site hit counts and proves the run existed --
         * and "no file at all" is the exact ambiguity that cost R5 its
         * diagnosis, where nothing on disk could not be told apart from
         * nothing captured. It also makes this path TESTABLE against a real
         * process exit (test_movehook.py §16), which the n > 0 version was
         * not. */
        if (!g_final_written) {
            const char *d = outdir_cached();
            LONG n = g_n;
            n = (n > (LONG)FLUSH_SLACK) ? n - (LONG)FLUSH_SLACK : 0;
            write_bin(d, (DWORD)n);
        }
    }
    return TRUE;
}
