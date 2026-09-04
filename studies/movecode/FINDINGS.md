# MOVECODE — findings

**Identifiers.** `MOVECODE-B<n>` = build steps, `MOVECODE-Q<n>` = open questions,
`MOVECODE-P<n>` = pre-registered predictions. The arc's scope, the tool inventory
and the question ranking are in [PLAN.md](PLAN.md); this file is the record of what
was measured. Convention: [studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Build pin: every address in this document is build 38797**,
`vault/client/2026-07-29_221c13772c7a/Gw.exe`, 10,483,904 bytes, image base
`0x00400000`. Behavioural claims may survive a build bump; addresses will not.

---

## 1. MOVECODE-B1 — the bit-18 reconciliation. **DONE, and Q1 is ANSWERED.**

### 1.1 The answer in one paragraph

**There was never a contradiction.** `m_flags` bit 18 (`0x40000`) of `agent+0x20` is
one bit with one meaning, and the two readings on record — "isWaypoint /
glide-vs-teleport selector" and "is moving" — are two names for the same predicate:

> **the leg currently being walked does not end at the final destination.**

That is literally what `m_segmentPoint != m_targetPoint` computes, and it is
literally what "this leg ends at a waypoint" means. The bit has **two writers and
one reader**, they sit in different functions, they cannot race, and both answer
that same question — one from geometry at construction, one from an explicit
argument per grant. **`isWaypoint` is the better name and it is OURS**: the string
`waypoint` appears in zero assert expressions image-wide (OBSERVED,
`asserts.py --grep "(?i)waypoint"` → 0 sites, subject to the tool's own floor).

**MOVECODE-Q1 does not reprice the arc, and that is itself the finding.** The
hoped-for outcome in `PLAN.md` §2.1 — *"If bit 18 is genuinely a wire-reachable
glide selector, a large part of this campaign's remaining warp budget is a one-field
fix"* — **does not happen.** Bit 18 is wire-reachable at exactly one moment (agent
creation, opcode `0x0020`) and is sealed against the wire for the entire rest of an
agent's life. There is no field we can add to a grant to make the client glide.

**But the sweep found something better, and it moves the arc's critical path.** See
§1.6: the client re-bakes with `isWaypoint=1` **from its own obstacle-avoidance and
its own priority-queue path solver**, on every grant. The teleport is not a trap our
grants spring — it is the client's precision landing at the end of a leg *the client
itself computed*. That makes **MOVECODE-Q2 (the navmesh differential) the critical
path**, and it is a stronger reason for Q2 than the one Q2 was ranked on.

### 1.2 The instrument, and why `--field` could not answer this

`--field 0x20` anchors on the **displacement** and never looks at the immediate. On
38797 it returns 8,483 rows image-wide, because `+0x20` is a displacement every
third structure uses; and filtering those rows for `0x40000` finds the dword
spellings and reports a confident zero for everything else. It also cannot see the
bake's own set/clear at all, because those apply `0x40000` to **`eax`**, not to
memory — an independent lane ran exactly that filter, got the two memory rows, and
flagged the trap itself: *"Anyone re-running my command would conclude bit 18 has
one writer. It has two."*

The deeper trap is one of **width**, not encoding:

> **bit 18 of the dword at `+0x20` is also bit 2 of the BYTE at `+0x22`.**

MSVC narrows `flags |= 0x40000` to `or byte [esi+0x22], 4` as a matter of routine,
and that instruction carries neither `0x20` nor `0x40000` anywhere in its bytes.
This is `studies/enemy/PLAN.md` §6o's failure arriving a fourth time by a new road.

So `codescan.py` gained **`--bit DISP:N`**, which *derives* the views rather than
trusting the caller to think of them, sweeps the field's displacement at each width
**and** the mask and its complement as an immediate, and prints what it searched and
what it cannot reach. It landed with `--upto` (read the instructions *ending* at a
VA, aligned by consensus search) and a phantom filter. Commit `0e25e04`; the
instrument's own three self-inflicted defects and their controls are in
[TESTS.md](../../TESTS.md) §12 for `test_codescan.py`.

**The narrowed spelling turns out not to exist in this image** — and that is a
measurement, not an assumption. Two independent scans agree. `--bit 0x20:18`
unbounded returns 10,151 rows over the whole `.text` section, of which **54 are
8- or 16-bit memory accesses at `+0x22` and not one of them is a SET, CLEAR or
TOGGLE** — every one is a `mov` or `movzx` on an unrelated structure. Separately, a
lane's hand-rolled `narrowscan.py` covering `80 /n ib`, `F6 /0 ib`, `66 83 /n ib`,
`66 81 /n iw`, `88`/`8A`, `C6 /0 ib` and `0F B6/B7/BE/BF` returned zero **with a
positive control that passed**. The client *does* narrow in this very function —
`0x005FEA1E test al, 4` is a byte-width test of bit 2 of `m_flags` — so the zero is
a fact about bit 18, not an artifact of a client that never narrows.

**The phantom rate is worth knowing before trusting any unbounded bit scan.** Over
the whole image the filter drops **1,353 of 11,504 rows, 11.8%**, as VAs that are
not instruction boundaries at all; the unfiltered SET count is 136 and the real one
is 47 (of which exactly one is a memory form). A one-byte anchor cannot avoid this,
and an unbounded scan that does not filter is roughly one part in eight fiction.

### 1.3 The census — every read and every write of bit 18

`python toolkit/clientscan/codescan.py --bit 0x20:18 --in AgAgent`, build 38797,
AgAgent bounds `0x005FE0C3..0x00602CE2` (70 assert sites, one source file).
**All OBSERVED.**

| VA | instruction | effect | function | condition |
|---|---|---|---|---|
| `0x005FE56C` | `or dword [ebx+0x20], 0x40000` | **SET** | constructor `0x005FDE30` | `m_segmentPoint != m_targetPoint` |
| `0x005FEA3B` | `or eax, 0x40000` | **SET** | bake `0x005FE950` | bake arg2 (`[ebp+0xc]`) `!= 0` |
| `0x005FEA49` | `and eax, 0xfffbffff` | **CLEAR** | bake `0x005FE950` | bake arg2 `== 0` |
| `0x005FEA4E` | `mov [esi+0x20], eax` | store-back | bake `0x005FE950` | unconditional |
| `0x0060029F` | `test dword [esi+0x20], 0x40000` | **TEST** | tick `0x00600140` | the only reader |

**`0x005FE56C` is the only `or dword [reg+0x20], 0x40000` in the entire 5.4 MB
`.text` section** — image-wide, not module-bounded. `0x0060029F` is the only reader
of the bit anywhere. There is no second consumer that would need a second meaning,
which is the structural reason the "two readings" could not have been two bits.

Pinned as a test (`test_codescan.py` §12d) so it reddens if a future change to the
anchoring drops the site or invents a second.

### 1.4 Writer 1 — the constructor, a one-time geometric seed

`0x005FDE30` is the **AgAgent constructor** (prologue + security cookie from
`[0x00BF4440]` + vtable store `0x005FDE8E mov dword [ebx], 0xa52f60`), corroborated
by the repo's own record at `studies/movement/CANCELWALK.md:665` (CANCELWALK-F9,
labelled OBSERVED there). It has **exactly one direct caller**, `0x005FD1F7`.

```
005FE534  fld dword [ebx+0x88]     ; m_segmentPoint.x
005FE53A  fld dword [ebx+0x9c]     ; m_targetPoint.x
005FE540  fucompp
005FE544  test ah, 0x44
005FE547  jp 0x5fe56c              ; differ -> SET
005FE549  fld dword [ebx+0x8c]     ; .y
005FE54F  fld dword [ebx+0xa0]
005FE55C  jp 0x5fe56c              ; differ -> SET
005FE55E  mov eax, [ebx+0x90]      ; .plane, an INTEGER compare
005FE564  cmp eax, [ebx+0xa4]
005FE56A  je 0x5fe577              ; all three equal -> skip
005FE56C  or dword [ebx+0x20], 0x40000
```

Three refinements the record did not have, all OBSERVED:

- **The fourth dword is copied but never compared** (`+0x94` vs `+0xA8`). The
  comparison is `(float x, float y, int plane)`.
- **The site is OR-only and monotone.** It never clears the bit when the points are
  equal — `0x005FE56A` just jumps past. It can only ever raise it.
- **`test ah, 0x44` + `jp` is the compiler's jump-if-not-equal.** Equal gives
  `ah & 0x44 == 0x40`, one bit, odd parity, PF=0, not taken; not-equal gives `0x00`
  and unordered gives `0x44`, both even parity, PF=1, taken.

### 1.5 Writer 2 — the bake, the per-grant authority

`0x005FE950` assigns the bit from its **second stack parameter**:

```
005FEA19  mov eax, [esi+0x20]
005FEA35  cmp dword [ebp+0xc], 0      ; <- arg2, the real isWaypoint
005FEA39  je 0x5fea42
005FEA3B  or eax, 0x40000             ; non-zero -> SET   (glide)
005FEA40  jmp 0x5fea4e
005FEA42  mov dword [esi+0x64], 0     ; the zero arm also clears +0x64
005FEA49  and eax, 0xfffbffff         ; zero -> CLEAR     (hard arrival)
005FEA4E  mov [esi+0x20], eax
```

**This is the only site image-wide that can CLEAR bit 18.** The two writers cannot
race: the constructor never calls the bake, and none of the bake's five callers lies
inside the constructor. The constructor seeds the bit once at `t=0` from geometry;
the bake is the two-valued authority for the rest of the agent's life.

**The register chain was audited rather than assumed**, because every claim above
rests on `eax` at `0x005FEA4E` still holding what `0x005FEA19` loaded, and on `esi`
being the same object at both ends. Walking the fourteen instructions between them
and reading capstone's own register-write set for each: the only writers of `eax`
are the two intended bit operations, **`esi` is never written at all**, and
everything in between touches only the FPU status word, EFLAGS, or memory. Chain
intact — so `test al, 4` at `0x005FEA1E` really does test **bit 2** of this same
`m_flags` value, and it is *not* a bit-18 site despite matching a naive byte-mask
search.

### 1.6 The five bake callers — and the finding that moves the arc

`--xrefs 0x005FE950` → 5 direct rel32 callers, 0 data words. **arg2 is genuinely
two-valued.** All OBSERVED, every call site read with `--upto`:

| call site | arg2 | bit 18 | enclosing function — identified by its own asserts |
|---|---|---|---|
| `0x00602AD3` | `0` | CLEAR | the shared setter `0x00602A40` |
| `0x006002B5` | `0` | CLEAR | the tick `0x00600140`, the glide arm's re-bake |
| `0x00600B0A` | **`1`** | **SET** | `0x00600840` — **obstacle avoidance** |
| `0x00601936` | **`1`** | **SET** | `0x006011F0` — **the local path solver** |
| `0x005FEC7E` | *forwards* | — | propagates its own `[ebp+0xc]` to attached agents |

The two `isWaypoint=1` functions are named by ArenaNet's own asserts, which is what
makes this more than a guess:

- **`0x00600840` is obstacle avoidance.** `AgAgent:1352` reads
  `(timeToEvent == (float)HUGE_VAL) || (m_point.position != obstacleCenter)`.
- **`0x006011F0` is a path solve.** It carries three asserts from
  `P:\Code\Base\rtl\PriQ.h` — **a priority queue** — alongside
  `AgAgent:1711 radius <= m_visibilityRadiusCount`.

**And the shared setter calls both, on straight-line code, immediately after baking
with `isWaypoint=0`:**

```
00602AD3  call 0x5fe950     ; bake, isWaypoint=0  -> CLEARS bit 18
00602AE2  call 0x5ffcb0
00602AEB  call 0x600840     ; obstacle avoidance   -> re-bakes with isWaypoint=1
00602AF8  call 0x6011f0     ; the path solver      -> re-bakes with isWaypoint=1
```

**Both `isWaypoint=1` sites are guarded by the same thing, and it is not exotic: a
float inequality on the point the function just computed.** OBSERVED, both read with
`--upto`:

```
; obstacle avoidance, 0x00600840
00600AEE  jp  0x600afe   ; components differ -> fall into the bake
00600AFA  jnp 0x600b27   ; both equal        -> SKIP the bake
00600B02  push 1         ; isWaypoint = 1, point = lea [ebp-0x44]

; the path solver, 0x006011F0
00601920  jp  0x601929   ; differ -> bake it as a waypoint
00601922  jmp 0x601859   ; equal  -> loop back and keep solving
0060192B  push 1         ; isWaypoint = 1, point = lea [ebp-0xa4]
```

Read as source, both say the same sentence: *if the point I just computed differs
from where I am currently headed, re-aim at it and mark it an intermediate.* The
solver's equal-branch jumping **backwards** to `0x00601859` is a loop, which is what
a `PriQ.h` consumer should look like.

So the `isWaypoint=1` path is **structurally reachable from a wire-driven grant**,
behind an ordinary point comparison. What is *not* established here is how often it
fires on any particular grant — that is a runtime property, and it is what
MOVECODE-P1 and B2 are for.

So the picture in `PLAN.md` §2.1 — *"Every `0x0029` we send arms a hard arrival at
the granted point"* — is **mechanically correct but reads as more sinister than it
is**. The client does not passively accept our point and schedule a yank. It takes
our point as a **destination**, runs its own avoidance and its own priority-queue
path solve over it, and re-bakes intermediate **waypoints** with `isWaypoint=1`
wherever its own solution needs them. The hard arrival is the **final** leg's
precision landing onto `m_targetPoint`, and it is invisible whenever the client's
own solution and our copy agree about where the body should be.

**This is the same conclusion `studies/movement/ROUTER.md` §10 reached from the
wire, arrived at independently from the code**, and it is why Q2 rather than Q1 is
the critical path: the client has its own solver, and our warps are the distance
between its answer and ours.

### 1.7 The wire question — Q1's second half

**Bit 18 is wire-reachable at exactly one moment: agent creation.** OBSERVED.

`0x005FD080` is the receive handler for **opcode `0x0020`** (agent create, 24 wire
fields), reached only by indirect dispatch from table `0x00a52d70` (slot
`0x00A52D90`; 0 direct rel32 callers). It is the sole caller of the constructor, at
`0x005FD1F7`, and it opens **two** independent routes to bit 18:

1. **The constructor writes the whole `m_flags` dword from a wire field, unmasked**,
   before the geometric test runs — `0x005FDE6D mov edx, [ebp+0x1c]` /
   `0x005FDE70 mov [ebx+0x20], edx`, fed by `0x005FD1E1 push dword [edi+0x10]`. The
   handler then asserts bit 17 is present in that value
   (`0x005FD1FC test dword [eax+0x20], 0x20000`), which is good evidence the field
   really is the flags word.
2. **`m_segmentPoint` and `m_targetPoint` arrive as two separate pointer
   parameters** — `[ebp+0x60]` → `+0x88..+0x94` and `[ebp+0x58]` → `+0x9C..+0xA8` —
   so a create message is free to make them differ, which fires `0x005FE56C`.

**Every post-creation wire route is sealed**, and one of them is sealed by
construction rather than by absence:

- **`0x0026`, the only "set agent flags" receive opcode, provably cannot touch bit
  18.** Its handler `0x005FD640` reaches `0x00602880`, which merges
  `stored = wire ^ ((current ^ wire) & 0x3f0000)` — taking bits 16..21 from the
  **current** agent unconditionally. Bit 18 lies inside `0x3f0000`.
  ```
  006028A6  mov ecx, [esi+0x20]
  006028AB  xor edx, [ebp+8]
  006028AE  and edx, 0x3f0000
  006028B4  xor edx, [ebp+8]
  006028B7  mov [esi+0x20], edx
  ```
  This is the strongest available NO on the update channel: not "does not in this
  corpus", but *cannot*.
- **All 8 callers of the shared setter `0x00602A40` end with bit 18 CLEAR**, because
  `isWaypoint` is not a parameter of the setter at all — it is the literal `6a 00`
  at `0x00602A7F`, on straight-line code. No caller can influence it. Those 8
  include the `0x0029` handler (`0x005FD913`) and the `0x002A` handler
  (`0x005FD9B4`).

**Consequence for the server:** there is no field we can add to a `0x0029` or
`0x002A` grant that makes the client glide. The only wire lever on bit 18 is the
create message, and it applies once.

### 1.8 The neighbouring bits — `+0x20` is one flags word

Reported because `--bit` now surfaces non-covering rows as `NEIGHBOUR` instead of
dropping them, and a bit's neighbours are what tell you whether the field is one
word or several packed ones. Two names are **ArenaNet's own**, from single asserts
cited as evidence (permitted, per the provenance gate):

| bit | mask | name | evidence |
|---|---|---|---|
| 17 | `0x20000` | `INTERNAL_FLAG_IN_WORLD` | `AgAgent:2334 m_flags & INTERNAL_FLAG_IN_WORLD`, assert at `0x00602A56` |
| 18 | `0x40000` | *(no ArenaNet name)* — ours: `isWaypoint` | `waypoint` in 0 assert expressions |
| 19 | `0x80000` | `INTERNAL_FLAG_MOVEMENT_STALE` | `AgAgent:1198 !(m_flags & INTERNAL_FLAG_MOVEMENT_STALE)`, assert at `0x0060015C`, guard at `0x0060014B shr eax, 0x13` |

Bits 0, 1, 3 and 16 are also live. The word is used as **one** flags dword; nine
separate guard reads test bit 17 across AgAgent.

---

## 1b. MOVECODE-B2 — `movehook`, built and tested, NOT yet run

The instrument for §4.1's gap. Four sites, all function **entries**, so the
persistent-`int3` handler re-emulates one shape (`push ebp`) rather than an
arbitrary instruction per site — owner's ruling `PLAN.md` §7 Q12(d), and
`gensites.py` refuses to generate the site table if any row's first byte is not
`0x55`. The procedure is [RUN-B2.md](RUN-B2.md); the prediction it will be scored
against is §3 below and was registered before the instrument existed.

**What is verified statically, and it is the part that decides whether the headline
number will be real.** All OBSERVED, build 38797:

- **`ecx` is the agent at every site that dereferences it.** Bake
  `0x005FE95C mov esi, ecx`; teleport `0x006020C5 mov ebx, ecx`; setter
  `0x00602A44 mov ebx, ecx`. `agtrack` does not dereference, because nothing shows
  `ecx` is an agent there.
- **The captured `arg2` really is the `isWaypoint` the bake tests.** At an entry
  hook the `push ebp` has not run, so `esp` is the caller's: the hook reads
  `[esp+8]`. After `push ebp / mov ebp, esp`, `ebp = entry_esp - 4`, so
  `[ebp+0xc] = entry_esp + 8` — the same slot. Cross-checked against the bake's own
  `0x005FE957 mov ebx, [ebp+8]` (arg1) landing on `entry_esp + 4`. If these had
  disagreed the headline rate would have been a different argument entirely.

**CORRECTION, 2026-08-27: the five-lane adversarial review DID produce its work,
and this section previously said it did not.** All five agents died returning
`None` (usage limits), and from the orchestrator's side that is indistinguishable
from having done nothing — so it was written up as a total loss. It was not. Every
lane had persisted its notes to disk before dying, and all five files were intact:
they are now in [review/](review/). The lesson is the opposite of the one first
recorded: **persist-as-you-go WORKED, and the thing that failed was only the
structured return.** Check the scratchpad before declaring a fan-out empty.

**What they found, and it was not cosmetic.** The lanes verified the emulation
independently — A1 compiled a 32-bit probe that runs the handler's three lines
verbatim against a hand-assembled `55 8B EC` stub and compared the emulated push
against a real one from the same frame (identical: pushed value, `ebp`, arg
pointer, EFLAGS) — and then found **five crash-class defects the hand review had
missed**, all now fixed:

- **The control-B gate was a MEASURED crash, not a theoretical one.** `if
  (g_ctl_armed && a == g_ctl)` declined a trap the DLL itself had planted whenever
  dispatch landed after the flag cleared — two threads inside the ~10–30 µs restore
  window, or one thread straddling the `CTLB_MS` timeout. A2's probe measured **11
  unhandled `EXCEPTION_BREAKPOINT`s per 400 trials × 8 threads** with that form and
  **zero** with `trnint3.c`'s unconditional `a == g_ctl`. movehook had regressed its
  own precedent. Now matched on address alone, with a single-owner
  `InterlockedExchange` restore and the hit published last.
- **`AddVectoredExceptionHandler`'s return was unchecked**, and Control A executes
  an `int3` three lines later — so a failed registration would kill the client the
  instant it was injected, writing no file, unattributable.
- **`RemoveVectoredExceptionHandler` is not a barrier.** `Sleep(150)` is a guess;
  the handler is now deliberately left registered, which is safe because `g_addr[]`
  is never cleared and a straggler still emulates correctly.
- **Sites were armed BLIND** — `poke`'s return ignored, so a site whose patch failed
  reported `hits 0` with both controls green. That is precisely the confident-zero
  shape this repo keeps getting caught by; the sidecar now says `NEVER ARMED`.
- **A slot was published before its record was written**, so a preempted handler
  left a partial record that decodes as a plausible real one (all-zero reads as
  site 0, seq 0) and got counted. `tick` is now written last as a commit flag and
  `readhook.py` drops anything still 0, reporting the count.

**And A5 predicted, statically, the anomaly the live run then produced**: that the
teleport takes its destination in its ARGUMENTS rather than from `m_targetPoint`,
and that `m_targetPoint` can hold `+INF`. §1c.6 is that exact value arriving in the
capture. A refutation lane earned its keep before the instrument was ever armed.

The hand review found one defect the lanes did not: `readable()`'s range test
computed `p + n` before screening for overflow, so a pointer near `0xFFFFFFFF`
would wrap and compare happily inside the region. Unreachable today
(`VirtualQuery` fails on kernel-space addresses in a 32-bit user process), but a
bounds check whose own arithmetic can wrap is not a bounds check. Also hardened:
the region-end sum, and a comment recording that Control B's sampling **must** run
before the sites are armed, because it suspends client threads and suspending one
inside our own vectored handler is a deadlock.

**Two defects the test caught before any client run** (`TESTS.md` §7/§8 for
`test_movehook.py`): the throwaway host was spawned `stdin=DEVNULL`, so `cmd /k`
read EOF and died in half a second while the injector's resulting `WinError 299`
read exactly like the known 64-bit-enumerating-WOW64 bug — *the error was about the
corpse*; and the DLL read its config from the **environment**, which an injected
DLL inherits from the *client*, not the injector, so `attach.py`'s `--minutes` and
`--out` would have been silently ignored on every live run.

**Status: UNVERIFIED against the client.** Nothing here is a measurement of the
game. 38 checks green, controls proven to fire inside a real injected process, and
the run itself waits on the owner.

---

## 1c. MOVECODE-B2 RUN 1 — Ascalon City, 2026-08-27. **P1a REFUTED, P1b CONFIRMED, Q4 ANSWERED**

**OBSERVED.** 10-minute window, 263 s of activity, 2,062 records, ring 13% full.
Both controls FIRED. Capture kept at
`vault/research/movecode/run-2026-08-27-ascalon/`. Build 38797, image base
0x00BD0000; every address below is rebased to 0x00400000.

Only **one agent (id 1)** ever baked or teleported. A prediction made before the
run — that Ascalon City's NPC crowds would dominate the record — was **wrong**:
NPC movement does not pass through these sites at all.

### 1c.1 P1a is REFUTED, and it is refuted cleanly

**0 of 586 bakes carried `isWaypoint = 1`. 0.0%.** All 586 returned to
`0x00602AD8` — the shared setter. `0x00600B0F` (obstacle avoidance) and
`0x0060193B` (the PriQ path solve) **never appeared as bake callers at all**,
across ten minutes that included repeated clicks into building corners and
through NPC crowds.

So §1.6's reframing — "the client re-plans our grants by re-baking them with
`isWaypoint = 1`" — **is wrong**, and `PLAN.md` §2.1's original reading stands
unmodified: every grant arms a scheduled hard arrival, and nothing in a normal
session converts one into a glide. The refuter was registered in
[RUN-B2.md](RUN-B2.md) §1 before the instrument existed, and this is it.

### 1c.2 But the client DOES re-plan — through a door nobody was watching

The setter's own callers split three ways, and `arg3` separates them exactly:

| caller | n | `arg3` | what it is |
|---|---|---|---|
| `0x005FC8F5` | 525 | `-1` always | internal re-issue, keeps the plane |
| `0x005FD918` | **49** | `{0, 29, 17, 18}` | **the `0x0029` wire handler — OUR grants** |
| `0x0060244D` | 12 | `-1` always | internal re-issue, keeps the plane |

`-1` is "do not write the plane" (`0x00602A6C` skips `agent+0x80` on −1), and the
49 wire calls carry real plane numbers — which is `0x0029`'s field 4 = the agent's
current plane, exactly as FINDINGS:3393 has it. So **the client re-issued the
destination 537 times against our 49 — about 11 to 1.**

**That is the re-planning, and it routes through the SETTER rather than through
the re-bakers.** Because the setter hardcodes `isWaypoint = 0`, every one of those
537 re-plans arms *another* hard arrival. The mechanism §1.6 was reaching for is
real; the route it proposed is not. `0x005FC7A0` (the 525-caller's function) sits
**outside AgAgent's assert bounds** and is reached from three sites at
`0x0081A8F0`/`0x0081ADB0`/`0x0081B220` — NOT DETERMINED what subsystem that is,
and it is now the most interesting open question in the arc.

### 1c.3 P1b CONFIRMED — and the decoded branch is confirmed live

**131 of 131 teleports had bit 18 CLEAR.** Their callers:

| caller | n | p50 | max | >100 u |
|---|---|---|---|---|
| `0x00600333` | 102 | 116.3 | 3,603 | 53 |
| `0x006025AB` | 28 | 579.1 | 4,525.9 | 21 |
| `0x00602B79` | 1 | 4,325.1 | — | 1 |

`0x00600333` is the return of `0x0060032E call 0x6020b0` — **the bit-18-CLEAR arm
of the branch at `0x0060029F`**, precisely as `PLAN.md` §2.1 decoded it statically.

> **⚠ CORRECTED TWICE — read §1d.3 and then §1e.2 before quoting the table above,
> because the second correction RETRACTS the number entirely.**
>
> §1d.3: `0x006025AB` is a **halt-in-place**, not a jump — it teleports the agent to
> its own current position, so its 28 rows measure `m_point` against a stale
> `m_targetPoint` and mean nothing. That took "75 over 100 u" down to 53.
>
> §1e.2: **the remaining 53 are not warps either.** `m_point` is the last *committed*
> position, so at the arrival tick it holds where the leg STARTED — the figure is a
> LEG LENGTH at every caller. Run 2 settled it: consecutive teleports chain to
> exactly 0.00, 25 of 25. **No warp count from run 1 or run 2 stands.**

75 teleports moved the body over 100 u. The operator's own report of the trigger
matches the model exactly: *"clicking somewhere far/cornered and pressing a
directional key mid-walk"* — the grant arms a hard arrival, the player walks off
under keyboard control, the scheduled tick yanks them back.

### 1c.4 MOVECODE-Q4 ANSWERED: the 3-caller claim HOLDS dynamically

`0x00605FC0` (AgTrack dispatch) was entered **759 times from exactly three
distinct return addresses** — `0x005FEBF0` (575), `0x006022A6` (131),
`0x00602BC2` (53) — matching the static `--xrefs` count of exactly 3 direct
callers. **No indirect caller appeared.** All three pass `this + 0x1CC`.

`0x006022A6` fired **exactly 131 times, the exact teleport count**, confirming
§2.2's "the teleport's tail" as a 1:1 relationship rather than an inference.

This is the answer the whole site was added for: the snap really is
message-driven, and the assumption the model rests on survives contact.

### 1c.5 MOVECODE-Q3: `+0x98` was 0 in all 586 calls

`arg2` was `0` in every setter call from every caller, so `agent+0x98` never
changed. `0x002A` was never used this session. The field's MEANING is still
UNKNOWN — but we now know our own traffic never sets it, so nothing observed so
far can have depended on it.

### 1c.7 THE 525-PATH IS NAMED: the client walking its own path, one leg at a time

**OBSERVED, 2026-08-27, static.** §1c.2 left `0x005FC7A0` unidentified and called it
"the most interesting open question in the arc". It is now named, and the answer
reframes the model.

**`0x005FC7A0` is an `AgApi.cpp` set-destination entry point**, and ArenaNet's own
asserts inside its body give its parameter names: `AgApi.cpp:1041`
*"targetPoint.position != AGENT_INVALID_POSITION"* at `0x005FC7CD`, and
`AgApi.cpp:1043` *"moveSpeed <= AGENT_MAX_MOVE_SPEED"* at `0x005FC81D`. It is
`__cdecl`, and its first argument is an **agent ID** — an index into the array at
`ctx+0x14C`, bound-checked against `ctx+0x154` under `Array.h:587` — not a pointer.
Signature: `(agentId, targetPoint*, moveSpeed, flags & 0xf, valueStoredTo+0x50)`.

**Why all 525 carried `arg3 = -1`:** it is not a per-call decision at all. The call
site `0x005FC8F0` **hardcodes** `push -1` (plane: do not change) and `push 0`
(isWaypoint: hard arrival), exactly as the `0x0029` handler hardcodes its own. Two
different callers, the same constant, for different reasons.

**Its only three callers are in `ChCliBase.cpp`** — the client's own character layer —
and the asserts there are what settle the interpretation: `ChCliBase.cpp:154`
*"index < arrsize(m_path)"* at `0x0081AC3D`, and `ChCliBase.cpp:164`
*"this == context->playerControlledChar"* at `0x0081AD27`.

**So the 525 are the client walking `m_path`, leg by leg, gated on the
player-controlled character.** That is the shape of the whole thing:

> We grant a **destination** (49 times). The client solves a path to it, then feeds
> itself each **leg** as a fresh destination through `AgApi` (525 times) — and every
> leg, like every grant, arms a hard arrival at its end.

**RECONSTRUCTION, and it is the reframing that matters.** The teleport is not our
grant fighting the client. It is the client's own **precision landing at the end of
each leg it computed**, which is what §1.6 was reaching for and attributed to the
wrong function. It also explains P1a's refutation rather than sitting awkwardly
beside it: the client never needs `isWaypoint = 1`, because it does not walk a
multi-leg route as one baked leg — it re-issues each leg as a complete destination.
**A ~10:1 leg-to-grant ratio is therefore the expected shape of normal movement, not
a pathology**, and B5 must be designed against it rather than against our grant rate.

**What this makes urgent.** Those legs come from a path the client solved with
`MapFindPath` — so **B3 is now the direct continuation of this finding**, not a
parallel errand: the legs the client walks ARE the output of the queries B3 captures.


### 1c.6 CORRECTED — the +INF was NOT an anomaly. It is what the teleport WRITES.

**Static recon on 2026-08-27 refuted this section's own reading, and the correction
is more interesting than the claim.** §1c.6 originally reported the `+inf` in
`m_targetPoint` as an anomaly that ArenaNet's assert exists to prevent. Both halves
of that were wrong.

**OBSERVED — the sentinel is confirmed.** `AGENT_INVALID_POSITION` is the float at
`0x00948654`, whose bytes are `00 00 80 7F` = `0x7F800000` = IEEE `+inf`. It is
compared **per component**, not as a struct: the teleport's own guard loads `[ebp+8]`
and `[ebp+0xc]` against it (`0x006020B6`, `0x006020D2`) and fires assert
`AgAgent:2066 point.position != AGENT_INVALID_POSITION` at `0x006020E3` only when
both match. So the value's identity is settled.

**OBSERVED — but the teleport WRITES that sentinel itself, every time.** Reading
`0x006020B0`'s body through: `ebx = this`, `esi = ebx+0x78`, and the stores are

| store | VA | what |
|---|---|---|
| `+0x78..+0x84` ← **the ARGUMENTS** | `0x00602132`–`0x0060214F` | where the body lands |
| `+0x88`, `+0x8C` ← `+inf` | `0x00602155`, `0x00602164` | `m_segmentPoint` **invalidated** |
| `+0x9C`, `+0xA0` ← `+inf` | `0x0060216D`, `0x00602179` | `m_targetPoint` **invalidated** |
| `+0xB0`, `+0xB4` ← `0.0` | `0x0060210E`, `0x00602117` | velocity zeroed |

So `+inf` in `m_targetPoint` is the client's **"arrived, no destination"** marker,
written on *every* teleport. Our hook reads state at ENTRY, so it sees the *previous*
teleport's marker — which is why exactly 1 of 131 records showed it: the one case
where two teleports ran back to back with no setter call between them. **Normal
state, correctly captured, wrongly interpreted.** `readhook.py` still counts
non-finite targets separately, which remains the right presentation — only the
prose calling it an anomaly was wrong.

**And the arc's `PLAN.md` §2.1 is wrong on this in the opposite direction.** It says
the teleport *"copies `+0x9C`'s 16 bytes into `+0x78/+0x7C/+0x80/+0x84`"*. It does
not: it writes its own **arguments** there and puts the sentinel **into** `+0x9C`.
The data flow is backwards in the record. What the caller passes is the destination;
`m_targetPoint` is an input to the *decision*, not the source of the copy.

**NOT DETERMINED, and explicitly withdrawn: the stuck character.** §1c.6 suggested
the `+inf` might explain it. It cannot — the value is routine. What remains OBSERVED
is only that movement events ceased at t=263 s with the player pinned at
(11979.8, 10491.5) plane 29 while our server re-granted that same position. The
cause is unknown and nothing here bears on it.

**One more thing the read turned up, UNVERIFIED as to purpose:** the teleport
**recurses**. At `0x0060221E` it calls itself with the same 16-byte point rebuilt
from `[ebp+8..0x14]`, after walking an array at `[ebx+0x28]` with count `[ebx+0x30]`.
Carried or attached agents is the obvious guess and is not evidence.


---

## 1d. The static recon that followed run 1 — three answers and two of my own errors

**OBSERVED unless marked. Build 38797, 2026-08-27.** Full lane notes in
[review/](review/); the load-bearing addresses below were re-verified by hand.

### 1d.1 §1c.7 was right but incomplete — here is the whole loop

`agapi_setdest` (`0x005FC7A0`, `AgApi.cpp`) is not called once per gesture. The
sequence is:

1. One user gesture — a key (`chcli_dir` `0x0081A8F0`, whose caller decodes two
   signed axes into an 8-way octant, from `GmWalk.cpp`) or a click (`chcli_point`
   `0x0081ADB0`) — runs **the client's own pathfinder for up to 9 waypoints**.
2. **Waypoint 0** goes straight to `agapi_setdest`.
3. **The rest are parked in `ChCliBase::m_path`** — `this+0x70`, 8 entries × 16 B,
   bounded by `ChCliBase:154 index < arrsize(m_path)`, and padded with
   `AGENT_INVALID_POSITION` to mark the end.
4. On arrival, **the client's own agent simulation raises a notification** (`push 5`
   at `0x00600342` and `0x006017E3`, each carrying `agent+0x50`), which lands on
   case 5 of the jump table at `0x0081B568` and calls **`chcli_advance`
   `0x0081B580`** — which pops `m_path[0]`, bumps the sequence, re-issues that one
   waypoint, and shifts the array down.

**So one gesture yields up to ~9 `agapi_setdest` calls, and that is run 1's 525.**
Both begin-move paths assert they run only for the local player (`ChCliBase:164`,
`ChCliBase:248`), and **nothing from the wire enters the loop**: our `0x0029`
reaches the shared setter directly from `0x005FD913` and never touches `m_path`.

`agent+0x50` is the sequence number, and it is the loop's own interlock —
`chcli_advance` compares its copy at `0x0081B58D` and ignores a stale advance.

### 1d.2 MY ERROR: `chcli_advance` was committed at the WRONG ADDRESS

The row first said `0x0081B220`, which I took from `codescan --dis`'s *"nearest
earlier int3 padding"* line. **That line says, in the tool's own words, "best effort,
not proof of a function boundary."** MSVC did not pad between `0x0081B220`'s function
and `0x0081B580`, so `func_start` walked straight past the real entry. `0x0081B580`
has its own `55 8b ec` prologue and its own single xref (`0x0081B548`); `0x0081B220`
is a different function holding the notify dispatcher.

**§4.3 of this document already records this trap** — from the other direction, where
`func_start` returned `None` and a lane read that as evidence. It returns a *wrong
value* just as readily. Fixed in the row, with the reasoning kept there.

### 1d.3 MY ERROR: §1c.3's per-caller teleport distances conflate two different things

§1c.3 reports `0x006025AB` with *"p50 579.1, max 4525.9"* alongside the main path's
116 u, presenting all 131 as comparable jumps. **They are not.** `0x006025A6` sits in
`0x00602540`, a **halt-in-place** method: it extrapolates `m_point` to now
(`0x00602580`), then teleports the agent **to its own current position**
(`0x006025A4 mov ecx, esi` — the destination is `esi+0x78`). Its telling caller is
`0x006022D8`: *if `m_timeStopMovement` is set, stop it here first.*

So for those 28 records the "distance" I computed is `m_point` against a **stale
`m_targetPoint`**, which measures nothing. Only `0x00600333`'s 102 are displacements.
**The headline "75 over 100 u" is therefore over-counted** and the honest figure is
the 53 from `0x00600333` alone.

### 1d.4 Why the character stayed pinned — the teleport is a FULL STOP

Withdrawn in §1c.6 as "NOT DETERMINED"; the mechanism is now OBSERVED, and I
verified the two load-bearing stores by hand rather than taking them from the lane:

| what | VA | effect |
|---|---|---|
| velocity `+0xB0/+0xB4` ← 0.0 | `0x0060210E`, `0x00602117` | no speed |
| **`m_timeStopMovement` `+0x48` ← 0** | **`0x006021E6`** | **the gate** |
| `m_targetPoint` ← `+inf` | `0x0060216D`, `0x00602179` | no destination |

And the extrapolator `0x005FF880` opens with `cmp dword ptr [esi+0x48], 0` /
`je` (`0x005FF89A`, `0x005FF8A8`) — **so with `+0x48` zeroed it skips extrapolation
forever.** Every teleport ends the agent's movement authority until something
re-arms it. That is exactly the observed state: pinned at one coordinate, movement
events stopped, our server re-granting the same position into an agent that will not
move on its own initiative.

### 1d.5 Nothing checks collision on a teleport destination

The teleport does call a spatial query — `0x006021B2 call 0x0070A150` → `0x00722B90`,
whose neighbourhood carries `PathObstacle:176 "radius >= 0"`. But its result feeds
**only** `+0x68..+0x74` and only when non-zero (`0x006021BC je`). **`+0x78` is written
before the call and is never corrected by it.** The destination itself comes from
uncollided linear extrapolation whose only clamp is the world rectangle
(`0x005FFC24`), and the plane is **copied, never re-resolved** (`0x005FFD7`… →
`out->plane = [esi+0x80]`).

Sharpest of all: `AgAgent:978`
*"!m_timeStopMovement || ((int)(m_timeStopMovement - time) >= 0)"* — an extrapolation
that over-runs the stop time **asserts and then performs the extrapolation anyway**
(the assert call falls through to `0x005FFBAD`).

**SUPPORTED:** every mechanism needed to land inside geometry is present and none of
the machinery to prevent it is. **NOT SUPPORTED:** that this is what happened at
t=243.5 s, or what set plane 29. That needs a trace, not the image.

### 1d.6 `MapFindPath`'s caller 1 IS the snap's gate 2

`PLAN.md` §2.2 described gate 2 as *"`MapFindPath` returning `pathCount == 0`"* by
inference. It is now located: `0x00605802 call 0x709e90` inside `0x006055E0`, with
the test at `0x0060580A cmp [ebp-0x60], edi` / `0x0060580D je` and `edi` provably 0
on every reaching path. It asks with **`maxCount = 4`** and **`range = 300.0f`** —
the same 300 the separation gate uses. The only other caller is `chcli_point`'s
`0x0081AF51`, asking `maxCount = 9`, `range = 10000.0f`.

**`arg4 = maxCount` is confirmed by an argument that cannot be forced true:** both
callers' output buffers close *exactly* on the stack-cookie slot — caller 1 reserves
4 × 16 at `[ebp-0x44]`, caller 2 reserves 9 × 16 at `[ebp-0x94]`, and both end at
`[ebp-0x04]`. Two capacities, two frame sizes, both to the byte.

---

## 1e. RUN 2 — Ascalon City, long walks. **P1a REPLICATED, Q2's first answer, and the "warp" figure RETRACTED**

**OBSERVED, 2026-08-27.** Nine sites, 198 records, both controls FIRED, ring 0.6%
full. Capture at `vault/research/movecode/run2-2026-08-27/`. The operator walked
long routes around corners and across bridges, plus a few short ones.

| site | hits |
|---|---|
| `mapfindpath` | 8 |
| `chcli_point` | 8 |
| `chcli_dir` | **0** |
| `agapi_setdest` / `setter` / `bake` / `teleport` / `chcli_advance` | **26 each** |
| `agtrack` | 52 (= 2 × 26) |

### 1e.1 P1a REPLICATED: still 0.0% glide, on the obstacle-rich case

**0 of 26 bakes carried `isWaypoint = 1`**, all 26 returning to the setter. This was
the run designed to provoke the re-bakers — long routes around corners — and neither
`0x00600B0F` (avoidance) nor `0x0060193B` (the solve) appeared. Two independent runs,
different movement, **zero glides in 612 bakes.**

### 1e.2 **I RETRACT the "visible warp" figure from every prior run**

Runs 1 and 2 both printed `m_point → m_targetPoint` at the teleport under the label
*"over 100 u (a visible warp)"* — 75, then 53 after §1d.3, then 23 here. **All of it
is mis-framed. Those are LEG LENGTHS.**

`m_point` (+0x78) is the last **committed** position; the extrapolator brings it
forward only on demand (§1d.4), so at the arrival tick it still holds where the leg
**started**. The teleport commits the body to the leg's end.

**The check that settles it, and it is not an argument — it is an identity.**
Consecutive teleports **chain to exactly 0.00**: `target[N] == m_point[N+1]` to the
bit, **25 of 25**. The timings agree — 2,677 u over 9.5 s is ~282 u/s, ordinary
walking speed. A 2,677 u warp in one tick would be absurd.

`readhook.py` now prints the chain test beside the figure and says in words that
these are legs. **A warp — the body being somewhere the client did not walk it to —
this tap could not see at all**, because it needs `m_point` advanced by velocity to
the arrival tick. Record **v4** captures `+0xB0/+0xB4` and `+0x58` so run 3 can ask
the question; runs 1 and 2 cannot, and no warp count from them stands.

### 1e.3 A SECOND defect of mine: the reader read every point block one dword late

`pathdiff` reported *"no coordinates"* on a **v3** capture. The cause: `readhook.py`
described v3 as *scalars + [point, segment, target, pt_a, pt_b]* with `have_pts`
appended to the scalars, while `movehook.c` declares `have_pts` **after** `target[4]`.
Both total 38 dwords, so `reclen` matched and **the guard whose own message warns
about "a record whose fields would silently shift" could not fire.**

`have_pts` came back as `m_point.x` — 0 for a site with no agent — so the coordinates
were discarded, and every point block was off by one dword. A length check cannot
catch a reorder. `test_movehook.py` §11 now **parses `rec_t` out of movehook.c** and
compares name and width in order; planting the exact historical reorder makes it go
red, which is the check the length test could never be.

### 1e.4 MOVECODE-Q2: on Ascalon City, our mesh agrees — **8 of 8**

With the reader fixed, `pathdiff` replays every captured query:

```
OURS-FAILED  0   0.0%      OFF-MESH  0   0.0%      BOTH-OK  8  100.0%
```

The queries chain — each `from` is the previous `to` — and the first begins at
**(9826.0, 8077.0)**, which `content/maps.toml` independently pins as map 148's spawn
landing in exactly one trapezoid. That chaining is a strong check that the
dereference reads true coordinates rather than plausible garbage.

**This does NOT clear our decode.** Router run 5's pocket was **map 280**, not 148,
and 8 queries is a small sample from one town. What it establishes is that **the
instrument works** and that Ascalon City is not where our mesh is wrong. All 8 came
from `chcli_point` with `range = 10000.0f` — exactly the click-to-move caller
profile §1d.6 predicted from the image.

### 1e.5 Our server granted NOTHING, and the client still moved 26 legs

**All 26 setter calls came from `agapi_setdest`. Zero from the `0x0029` wire
handler.** Run 1 saw 49 wire against 537 internal; run 2 saw **0 against 26**.

The client solved, walked and committed 26 legs across a long route with **no
movement grant from us at all**. Whether that is our server declining to grant on
this path, or the click policy not firing, is NOT DETERMINED here — but it sharpens
§1c.7's point past where that section put it: our grant rate is not merely a minority
input, it can be **absent** while the client moves normally. B5 has to be designed for
a client that does not need us to walk.

---

## 1f. RUN 3 — Isle of the Nameless, interrupted walks. **THE TELEPORT IS EXONERATED**

**OBSERVED, 2026-08-27.** Map 280, 3,417 records, v4, both controls FIRED, ring 10%
full. Operator did long walks interrupted mid-walk with a directional key and
**reports seeing 3–4 warps**. Capture at
`vault/research/movecode/run3-2026-08-27-isle/`. Predictions were registered in
[RUN-B2.md](RUN-B2.md) before the run.

### 1f.1 MOVECODE-P2a REFUTED — and this is the arc's biggest result so far

The measurement v4 exists for. For every teleport, advance `m_point` by velocity to
the arrival tick — the client's own form at `0x005FFC19`,
`m_point + v × (stop − ptime) × 0.001` — and compare against `m_targetPoint`:

| caller | n | leg (`m_point`→target) p50 | **divergence (extrapolated→target)** |
|---|---|---|---|
| `0x00600333` (tick arm) | 25 | 147.2 | **p50 0.1, max 0.3** |
| `0x006025AB` (halt) | 17 | 707.0 | **p50 0.1, max 0.3** |

**Zero. On all 42, across keyboard interrupts.** The body was already exactly where
the teleport put it; the "leg" figure is only the distance from the *stale committed*
`m_point`, and the extrapolation covers it to within floating-point noise.

**So the teleport is never a warp. It is the ordinary arrival mechanism**, and
`PLAN.md` §2.1's framing — *"every `0x0029` we send arms a scheduled hard arrival …
a warp the moment the body is elsewhere"* — is wrong about the second half: the body
is never elsewhere. This was pre-registered as the refuting outcome and named the
bigger finding, and it is: **the warp the operator saw came from somewhere else.**

P2b was confirmed and turned out to measure something weaker than intended — chaining
fell to 11/41 (run 2: 25/25) — but with divergence at zero, a broken chain only means
consecutive teleports belong to different paths, which is what an interrupt does. **A
broken chain is not evidence of a warp.**

P2c confirmed and comfortably past its exposure floor: `chcli_dir` **618** (was 0).

### 1f.2 P1a is PARTIALLY REVERSED: avoidance DOES fire — at 1.2%

**8 of 687 bakes carried `isWaypoint = 1`, and all 8 returned to `0x00600B0F` —
obstacle avoidance**, the re-baker §1.6 predicted and §1c.1 declared never fires.

It fires. Runs 1 and 2 saw zero across 612 bakes because both were click-driven; run
3's keyboard interrupts produced it. All 8 are agent 1 within one episode
(t = 69.5–83.0 s, clustered near (−4700, 2100)) — a keyboard walk into geometry.
`0x006002BA` (the tick) also baked twice, another first.

So §1c.1's refutation stands **for click-driven movement** and is **too strong as
stated**: the correct claim is that the re-bakers are rare and input-dependent, not
that they never run. Still no unknown bake caller in 1,325 bakes across three runs,
so MOVECODE-Q4 holds.

### 1f.3 MOVECODE-Q2 on map 280: **7 of 7 BOTH-OK. MY PREDICTION REFUTED.**

I predicted map 280 would produce non-zero `OURS-FAILED` or `OFF-MESH`, because
router run 5 found our decode reads the player's open ground there as a pocket. It
did not: zero OFF-MESH, zero OURS-FAILED, on the map we believed we got wrong.

Per the pre-registration's own terms: **run 5's pocket was not a mesh-decode
failure**, and ROUTER-Q10 (route *quality* — a legal but ugly route) takes its place
as the explanation. Our mesh is not the problem on map 280.

### 1f.4 The new suspect, and it is named by the capture

**`MapFindPath` was called twice from `0x00605807` with `range = 300.0f`** — that is
the **snap's gate 2** (§1d.6). Two evaluations of the desync test in a run where the
operator saw 3–4 warps, while the teleport was provably innocent on all 42.

The other five queries came from `chcli_point` at `range = 10000.0f`, so the two are
cleanly separable by range alone.

**Our server also granted this run**: 38 of 677 setter calls came from the `0x0029`
wire handler (run 1: 49; run 2: 0), against 634 from `agapi_setdest`. And keyboard
walking re-issues *per input tick* — 617 of those 634 came from `chcli_dir`'s call
site `0x0081AC14` — which is why 618 keyboard events produced 617 destination sets.

**Two sites are added for run 4**: `snaptest` (`0x006055E0`) and `reseed`
(`0x006022B0`), both verified `55 push ebp`. The first says *which gate failed*, the
second says a correction was actually **applied, and to whom** — without it, a failed
gate and an applied snap are the same record.

---

## 1g. RUN 4 — the snap CAUGHT, and the warp is OURS

**OBSERVED, 2026-08-27.** Map 280, 491 records, v4, both controls FIRED, ended by
`--stop` at 79 s. Capture at `vault/research/movecode/run4-2026-08-27-snap/`. First
run with the two snap sites armed.

**`snaptest` fired 11 times and `reseed` 6 times** — the first capture of a
correction actually being applied.

### 1g.1 The causal chain, in the record, in order

```
#231 setter    ret=0x005FD918   <-- OUR 0x0029 WIRE GRANT
#232 bake      ret=0x00602AD8
#233 agtrack   ret=0x005FEBF0
#234 snaptest  ret=0x00606021   <-- the desync test runs
#235 reseed    ret=0x006060E7   <-- the correction is APPLIED
#236 teleport  ret=0x006025AB   <-- halt-in-place
```

**Our grant, then the test, then the correction.** The same shape repeats at
`#295`, `#398` and `#471`; the pair at `#243`/`#479` follows a `chcli_dir`
keyboard event instead.

### 1g.2 The warp, measured — and it is NOT the teleport

Run 3 exonerated the teleport (§1f.1): divergence 0.1 u over 42 samples. So the
detector had to change. For every record carrying the player's position block, ask
whether the move since the previous one is explained by that agent's **own**
velocity and **own** timestamps:

**18 jumps that dead reckoning cannot explain**, and they land on the reseeds:

| record | site | unexplained |
|---|---|---|
| `#235` | **reseed** | **1,359.5 u** |
| `#295` | **reseed** | **1,784.0 u** |
| `#398` | **reseed** | **1,048.9 u** |
| `#471` | **reseed** | **2,048.2 u** |

At `#235` the agent should have been at `(−5834.0, −470.7)` by its own velocity over
804 ms. It was at `(−6264.1, 819.0)`.

**So the warp is the snap, and the snap follows our grant.** Not the client's own
path-following, which run 3 measured exact to 0.3 u.

### 1g.3 What this does NOT yet establish, and the reason is structural

**`reseed`'s `arg1` is another AGENT, not a point.** `0x006022C0` loads it into
`edi` and reads `[edi+0x24]` (world), `[edi+0x48]`, `[edi+0x88..0x90]`
(`m_segmentPoint`) — so the function copies one agent's state onto another, and a
record holding only `this` holds **half of a correction**. The same is true of
`snaptest`, whose `arg2` is the source agent under assert `AgTrack:458
source.GetWorld() == WORLD_SYNC`.

That matters for reading §1g.2 honestly: the rows at `#239`, `#299` and `#475` show
the jump **reversing** on the next setter, which is what two agents alternating in
one timeline look like — not necessarily one body moving twice. **Which agent each
jump belongs to is NOT DETERMINED from a v4 capture.**

**Gate attribution is also still open.** Run 4 made **zero** `MapFindPath` calls at
`range = 300.0f`, so gate 2 was not the decider; whether gate 1 (separation),
gate 3 (step clearance) or the history-chain match settled each of the 11 tests is
unmeasured.

### 1g.4 Record v5 answers both, and is wired

`deref_agent_arg` names, per row, which argument holds a second agent — `1` for
`reseed`, `2` for `snaptest` — and the DLL reads that agent through the **same**
`read_agent()` used for `this`, so the two sides of a correction cannot be
described differently by construction. With both captured, **gate 1's separation is
recomputable offline** rather than inferred, and `readhook.py` now prints it against
both thresholds this repo already argued over (100.0 and 299.332591, `PLAN.md` §7
Q11).

Run 5 is that measurement. Until then §1g.2's magnitudes are OBSERVED and their
**attribution to a particular agent is not**.

---

## 1h. RUN 5 — the snap APPLIES rarely, the warp is a ROLLBACK, and Q2 finally bites

**OBSERVED, 2026-08-27.** Map 280, 3,246 records, **v5**, both controls FIRED, 206 s,
ended by `--stop`. Capture at `vault/research/movecode/run5-2026-08-27-v5/`.

### 1h.1 A TRAP THE RECORD WALKED INTO, caught by pairing on agent id

v5's first output claimed a separation of **p50 7,197 u, max 9,566** — most of the
map, and it would have read as a catastrophic desync. It was nothing of the kind.
`snaptest`'s `ecx` **is not `this`**: all 70 of its records reported agent ids of
`574588536` and `459313176` — readable memory that is not an agent.

The row had been marked `thiscall` because `0x006055FB` saves `ecx` to a local. **A
register being SAVED does not make it a `this` pointer**, and that is the
verify-the-operand failure this repo already has a note about. `snaptest` no longer
dereferences `ecx`, and what `ecx` holds there is **NOT DETERMINED**.

`readhook.py` now pairs the separation **on agent id** and prints how many records it
excluded, because a distance between two *different* agents is not a desync — it is
the distance between two characters, and it looked like a finding.

**The honest number, over the 14 reseeds where both sides are agent 1:**
separation **min 23.6, p50 634.9, max 1,897.2**, with **11 of 14 past gate 1's
299.33 cut** and 11 of 14 past the 100.0 history band. So **gate 1 (separation) is
what fires**; the 3 under the cut failed some other gate.

### 1h.2 §1g's headline needs qualifying: the snap is CALLED often and APPLIES rarely

Following each reseed to the next record carrying agent 1's position:

**12 of 14 did not move the player at all** (`d(before)` 3.6–14.4 u). **2 of 14 moved
it to the source** — **690.8 u** and **510.7 u**.

So "the warp is the snap" (§1g.2) is right about the mechanism and wrong about the
rate. 70 desync tests → 14 reseeds → **2 actual displacements**. §1g's 18
"unexplained jumps" were measured without agent attribution, exactly as §1g.3 warned;
this supersedes them.

> **CORRECTED by §1i.1.** The "d(before)" figures in this subsection were computed
> by following each reseed to the next record carrying **agent id 1**, and id 1 names
> TWO objects (the two world copies), not one body. That walk crosses between two
> agents 940 u apart and scores the crossing as a displacement. The 2-of-14 headline
> happens to survive re-scoring by address, but it survives for a different reason
> than the one given here — read §1i.6.

### 1h.3 What the two real warps ARE: a ROLLBACK

Both are the same shape, and it is visible in the coordinates:

| reseed | source position | equals |
|---|---|---|
| `#889` | `(−7871.4, 1804.5)` | **`#812`'s player position** |
| `#2427` | `(−6027.3, 6632.3)` | **`#2305`'s player position** |

**The source agent is holding a position the player occupied at an EARLIER reseed,
and the correction pulls the player back to it.** The player walks away, the sync
twin does not follow, and the next correction rolls the player back to where the twin
still thinks it is. That is the warp the operator has been seeing, and it is a
**rollback to a stale sync position**, not a jump to a new one.

> **"STALE" IS WITHDRAWN — §1i.2.** The sync copy is not holding still. It walks, at
> 288 u/s, over 52 distinct positions spanning 10,368 u, every one of them within
> 0.00 u of ground the player really covered. What it does is **idle 100.2 s of a
> 207.6 s run against the local copy's 37.8 s**, in 18 stalls of median 4.85 s,
> because our server grants it a destination only 51 times. The rollback is real;
> the cause is STARVATION, not staleness, and it is ours.

### 1h.4 MOVECODE-Q2 finally bites — and §1f.3's refutation was an n=7 artifact

**2 of 20 queries OFF-MESH (10%)** on map 280:

```
(-6034.1, 6885.1) -> (-4705.9, 7670.4)   start OFF mesh, goal on mesh
(-5526.5, 7877.5) -> (-4284.3, 8482.0)   start on mesh, goal OFF mesh
```

Run 3 sampled 7 queries on this map and got 7/7 clean, and §1f.3 read that as
refuting the map-280 prediction outright. **With 20 queries the gap appears.** Both
failures are in the same north-east region (y ≈ 6,900–8,500), which is where to look.

So §1f.3 is **corrected, not reversed**: our decode of map 280 does have a hole, run 5
locates it, and the earlier "refuted" was a small-sample result stated too strongly.
Router run 5's pocket may yet be a decode failure after all.

### 1h.5 P1a: avoidance again, and the same rate

**9 of 618 bakes glided (1.5%)**, all from `0x00600B0F`, matching run 3's 1.2% on the
same input style. Three runs, 1,943 bakes, still no unknown bake caller — Q4 holds.

---

## 1i. CHASING THE STALE SYNC TWIN — it is not stale, it is STARVED, and the starver is ours

**OBSERVED, 2026-08-27**, from the run 5 capture
(`vault/research/movecode/run5-2026-08-27-v5/`) re-scored after a method defect, and
from the matching server-side log
(`vault/captures/gamesrv/authsrv-20260827T180821-c1.jsonl`, 5,098 rows, 218.5 s).
No new client run was needed: both artifacts already existed.

### 1i.1 THE METHOD DEFECT — one agent id names TWO objects, and §1h.2 rode on it

`GAME_SMSG_WORLD_CREATE_AGENT` runs its handler body **twice** with the agent array
base advanced `0x64`; `AgAgent.cpp:312` names the two `m_world` 0 and 1. So **agent
id 1 is two objects**, and every per-agent trajectory this arc has computed —
including §1h.2's warp rate — filtered on `id == 1` and treated the result as one
body.

It is not one body. Keyed on `ecx` (the object's address) the run 5 capture holds:

| object | records | sites | what drives it |
|---|---|---|---|
| `0x21E20128` | 1,209 | bake 567, setter 557, teleport 71, reseed 14 (as `this`) | the client's own path solver |
| `0x21E208D8` | 124 | setter 51, bake 51, teleport 22 | **the wire, and only the wire** |
| `0x060C9B6C` | 70 | snaptest 70 | **not an agent at all** (§1h.1's ecx) |

The two copies sit **940 u apart** at reseed `#22`. An id-filtered walk crosses
between them and reports the crossing as a displacement — 940 u **inside a single
15 ms `GetTickCount` tick**, which is not a motion any client could produce. That is
the artifact §1h.2 measured.

`0x21E208D8` is the **`WORLD_SYNC`** copy, and this is read off the record rather
than assumed: it is the agent passed as the source argument at every one of the 84
`reseed`/`snaptest` observations, and the client asserts that argument's world itself, at
`AgTrack.cpp:458` — the expression and its polarity are read out in §1j.1.

`readhook.py` now censuses world copies by address, names the sync side from
`reseed`'s source argument, and **raises when an id is ambiguous** — a census that
silently merged the copies would read exactly as clean as a correct one
(`test_movehook.py` §12, both directions, commit `09b1b1a`).

### 1i.2 The twin is NOT frozen — §1h.3's "stale" is withdrawn

§1h.3 said the sync twin "holds a position the player occupied earlier" and "does not
follow". The first half is true; **the second is wrong**. The twin has 52 distinct
positions spanning 10,368 u, 70 distinct position timestamps and 52 distinct
velocities. It walks, at exactly 288 u/s, and **52 of its 52 distinct positions are
within 0.00 u of a position the player actually occupied** — it is not on an
independent path, it is behind on a shared one.

What it is, measured over the same 207.6 s clock window, from each agent's own
declared `[ptime, stop]` legs (union, so the ~10× sampling difference between the two
copies cannot manufacture the result):

| | in motion | idle |
|---|---|---|
| local copy `0x21E20128` | **169.8 s** | 37.8 s |
| sync copy `0x21E208D8` | **107.4 s** | **100.2 s** |

The twin spends **62 extra seconds standing still**, in **18 stalls, p50 4.85 s, max
9.03 s**. At 288 u/s that is **~18,000 u of lost path progress** (48,913 u against
30,920 u implied). During the longest stalls the local copy was still receiving
destinations and walking.

*Use the union-derived figures, not the summed ones.* Summing consecutive sampled
positions gives 49,378 u and 27,160 u, but the hook fires on the twin only at
`snaptest` and `reseed` — p50 **1281 ms** apart — so its chord sum under-reads a
curved path far more than the local copy's does. The interval union is insensitive to
that; the raw sums are quoted only to show they do not disagree.

**The correct word is STARVED, not stale.**

### 1i.3 The twin's ONLY destination source is our server, proven 1:1

Our server sent **51** `0x0029 AGENT_MOVE_TO_POINT` in that session. The twin took
**51** setter calls. Equal counts are weak evidence, so the pairing was tested where
it can fail: **inter-event gap sequences**, which need no clock alignment between the
server log's `t` and the hook's `GetTickCount`.

**All 50 gaps agree — median residual 2 ms, maximum 15 ms**, both spans 185.0 s. The
pairing is exact.

The negative control is the local copy: it took **557** setter calls against 51 grants
ever sent, so its destinations cannot be coming from our wire. That is §1e.5 ("our
server granted nothing and the client still moved 26 legs") seen from the inside — the
client path-solves for the local copy and the wire drives the sync copy, and the two
are separate.

### 1i.4 Against retail: the twin is granted more sparsely than ANY of 118 live agents

Grants per second is not comparable — across 37 live connections it ranges 0.086/s to
9.142/s purely with how much the operator was moving. Normalising by **path walked**
removes the free parameter (`0x0029` field 2 is the destination, SOURCED by four
`worldDims` asserts).

**The denominator has to be built the same way on both sides**, and this bit me once:
retail's is the **granted path** (the chain of destination-to-destination distances
reconstructed from the wire), so ours must be too. Our server logs its own
destinations, so it can be: the 51 fired grants chain to **36,387 u**.

| | grants per 1000 u |
|---|---|
| retail, 118 agents | min **1.70**, p10 2.47, **p50 4.30**, p90 10.27, max 21.79 |
| our sync copy, same construction | **1.40** |

**The twin sits below retail's MINIMUM — 0 of 118 live agents were granted more
sparsely — and retail's median is 3.07× ours.**

(The first pass reported 1.65, dividing by the distance *implied* by the twin's
motion time rather than by the granted chain. Both figures are below retail's
minimum, but only the chain is the same quantity retail's is, so 1.40 is the one
that means what its label says. Its measured walked path, a third denominator,
gives 1.88 — also below 1.70.)

Ticks are not the shortfall: we send `0x001E` at 19.65/s against retail's 5.822/s.
Nor is it the local copy, which at 11.39 per 1000 u of its own walked path sits up
at retail's p90 — but it is driven by the client's own solver, not by us.

### 1i.5 WHY our server under-grants — TWO defects, and only one of them is the mesh

The server log records its own refusals. **17 movement clicks refused outright**, plus
**13 of 64 grant verdicts refused** on `heading-rate` — so **30 of 81
movement-authority events were suppressed (37%)** against 51 granted.

**I first read all 17 as geometry refusals and that was wrong.** The branch at
`authsrv.py:16453` picks between three reasons and only two of them are about the
mesh:

```
fresh  = (time.time() - state["pos_seen"]) <= 1.0        # 16373
placed = here == {a2_place_plane}                        # is the PLAYER on the mesh
reason = "geo-stale" if not fresh else "geo-unplaced" if not placed else "geo-blocked"
```

| reason | n | what it actually means |
|---|---|---|
| `geo-stale` | **13** | the server has no position report inside its own 1.0 s window |
| `geo-blocked` | 3 | the straight-line clip failed |
| `geo-unplaced` | 1 | the player's own position will not place on the mesh |

**The 13 are a CADENCE defect and have nothing to do with geometry.** Position reports
arrive at **0.448/s**, with an inter-report gap of p50 0.80 s but **p90 7.24 s and max
14.01 s**; **44% of gaps exceed the 1.0 s window and the session spends 69% of its
time staler than that**. All 13 refused clicks landed in such a window (12 measured at
1.20–9.48 s old; the 13th arrived before the first report at all). **Our server refuses
to answer because it does not know where the player is**, and the window it tests
against is tighter than the cadence it actually receives.

**The 4 geometry refusals are Q2, and they are unanimous about where.**

| refused click | reason | §1h.4's independent verdict |
|---|---|---|
| `(−5282.7, 7513.6)` | `geo-blocked` | — |
| `(−4705.9, 7670.4)` | `geo-unplaced` — "cannot place **them**" | **start** off mesh |
| `(−4284.3, 8482.0)` | `geo-blocked` — "not a straight shot" | **goal** off mesh |
| `(−6724.6, 8312.2)` | `geo-blocked` | — |

**4 of 4 sit in the north-east region (y > 5,000)** that §1h.4 named from the
`MapFindPath` side, and two of them are that section's exact off-mesh coordinates,
with the reason code matching which end was off-mesh. The staleness refusals, by
contrast, are spread 7 north-east to 6 elsewhere — which is what a defect unrelated to
geometry should look like, and is the control that separates the two.

So: **the navmesh hole is real and is confirmed from two independent sides, but it
accounts for 4 of 17 refusals, not 17.** An earlier draft of this section said the
two were "one defect seen from two sides"; that holds for the four and not for the
thirteen.

The branch's own comment states the intent: *"Something is in the way, so the client is
pathing around it and knows more than we do. Say nothing, and drop our own destination
rather than integrate along a line the player is not walking."* **The silence is not
free**, and that is the finding common to both defects: the client is not left to its
own pathing — it is left to walk the local copy away from a sync copy that receives
nothing, until the desync test rolls the player back.

### 1i.6 What the warp actually IS, at the byte level

§1h.2's "2 of 14 displaced the player" survives re-scoring, but the signature is
sharper than a distance. Per object, counting steps where `m_point` moved but `+0x58`
— the stamp saying when `m_point` was valid — **did not advance at all**:

* local copy: **10** such steps out of 1,208
* sync copy: **0** out of 123

A walk always advances both. **The sync copy is never discontinuously repositioned;
only the local copy is.** At both real warps the local copy's post-warp position is
*exactly* the twin's teleport **target** — `(−7871.4, 1804.5)` and `(−6027.3, 6632.3)`
— and the `reseed` leaves it halted, `m_targetPoint` `(inf, inf)`, velocity 0, stop 0,
which is the state §1c.6 established the teleport writes.

This also retracts a claim I made mid-analysis: scored in each agent's own frame
**neither** object ever exceeds 312 u/s, which looks like "nothing ever teleports". That
was an artifact of computing speed only where the clock delta was non-zero — the filter
discarded exactly the ten steps that matter. `readhook` now counts them instead.

### 1i.7 Status and what is NOT settled

* **MOVECODE-Q2 is no longer only a decode question.** It has a measured server-side
  consequence, confirmed from two independent sides — but it costs **4 of 17**
  refusals, not 17. Bounded to y ≈ 7,500–8,500 by those four.
* **A SECOND, LARGER defect is now named and is not the mesh: the freshness window.**
  `authsrv.py:16373` requires a position report inside 1.0 s; the session spends **69%
  of its time staler than that**, and it cost **13 of 17** refused clicks. This is a
  cadence question (how often the client reports, or how long we are willing to trust
  the last report, or whether the model should answer when the report is stale — which
  is what `D1_LEAD`'s `a2_click_leg` block at `authsrv.py:16385` already does, and it
  is inert under the shipped default). **It is cheaper to investigate than the mesh and
  it is the bigger contributor.**
* **The existing candidate fix is already in the tree and is OFF.** `D1_LEAD`
  (`authsrv.py:4595`, REALFIX-A2) makes geometry *not* refuse a click, because the
  answer is a verbatim echo of the client's own point — "retail's contract, 23/23
  bit-exact". Every one of the 17 refusals recorded `d1_passthrough: false`. It is a
  four-term bundle with its own registered predictions
  (`studies/movement/REALFIX.md` §0.9) and requires `--zero-lead` and `--plane-carry`;
  **turning it on is a decision for the owner, not a consequence of this section.**
* **NOT DETERMINED: which instruction writes `m_point` at the reseed.** The hook is an
  entry hook, so it reads the local copy at its OLD position and the next record
  carrying that object is 1.4–2.4 s later. That the new position equals the twin's
  target is OBSERVED; that `reseed` itself performs the write is RECONSTRUCTION.
* **NOT DETERMINED: what `heading-rate` costs.** 13 refusals is a sixth of our grant
  budget and no measurement here separates its effect from the geometry refusals'.
* The `+0x24` world field is **not captured** — the sync side is currently identified
  from `reseed`'s source argument, which works but is indirect. Capturing `+0x24`
  would make it direct and is one row in `content/movecode.toml`.

---

## 1j. THE CLIENT SIDE OF THE SAME MECHANISM — read out of the binary

**2026-08-27.** Four independent static/capture lanes with an adversarial refutation
pass over each load-bearing claim (three were REFUTED and are recorded as such below).
Build 38797 throughout. This closes three things §1i left NOT DETERMINED.

### 1j.1 WORLD_SYNC == 0, and the direction is proven from the bytes

`AgTrack:458` `source.GetWorld() == WORLD_SYNC` compiles at `0x0060561A` as
`cmp dword ptr [ebx+0x24], 0` / `je` (skip the failure report). **The assert body runs
when the world field is NON-zero, so the passing value — `WORLD_SYNC` — is the literal
0.** Two independent polarity controls were run against ArenaNet's own asserts at
**`AgTrack:457`** and **`AgAgent:2211`**, either of which could have come out the other
way: the first tests a truthy condition and the second an explicit equality, and BOTH
compile to the same skip-on-pass shape as the assert above. So the polarity is anchored
against two known-sign neighbours rather than assumed from one. **OBSERVED.**

At both — and only — direct call sites of `reseed` (`0x00605EF1`, `0x006060E2`):

* **`this` (ecx) = `world[1].agentArray[i]`** — the local/display copy
* **`arg1` = `world[0].agentArray[i]`** — the **sync** copy, same index `i`

The two array descriptors are `0x64` apart, exactly the world stride. **OBSERVED.**

**State flows arg1 → this.** Within `reseed`'s 191 instructions
(`0x006022B0..0x0060253C`, `ret 8`) there are **ZERO stores whose destination base is
edi (arg1)**: all sixteen `[edi+…]` operands are 15 reads plus one address-take
(`0x00602438 lea eax,[edi+0x9c]`), while the body's agent-object stores all go through
esi (`this`). **OBSERVED, and it settles §1i's open question in the direction §1i
guessed: the player is rolled back to the twin, never the twin caught up to the
player.**

**One honest amendment the refutation pass forced, because the first draft of this
claim over-reached.** "Read-only" holds for `reseed`'s own body, **not** for its whole
call graph. `reseed` passes `arg1` as a `this`-pointer at **two** sites, not one:
`0x00602323 mov ecx,edi → 0x005FFB40` (verified pure), and
`0x006024BE mov ecx,edi → 0x005FF9F0`, which **does** store into `arg1` at
`0x005FFA2E fst dword ptr [esi+0xb8]`. That write is a **lazy cache fill, not a state
transfer**: it fires only when `[arg1+0xB8]` already holds the `+INF` sentinel at
`0x948654`, and the value stored is derived **solely from `arg1`'s own** `+0xBC`/`+0xC0`
via `0x005BCA00`. `+0xB8` is a cached facing angle, and `reseed` then writes that same
angle *into* the destination agent at `0x006024CB` — which is itself arg1 → this flow.
So the direction stands; the blanket phrase "arg1 is never written" would not have.
(One further limit recorded rather than papered over: the setter `0x00602A40` forwards
the `edi+0x9c` pointer on to `0x005FE950`, which is store-free through it at depth 2;
**depth 3 is NOT DETERMINED**.)

### 1j.2 WHICH instruction writes `m_point` — §1i.7's first open item, ANSWERED

`reseed` writes `m_point` (+0x78), the position stamp (+0x58), velocity
(+0xB0/+0xB4), `m_segmentPoint` (+0x88) and `m_targetPoint` (+0x9C) on the world-1
agent **through callees, not directly**. The unconditional path is
`0x00602369 call 0x00602B20` (every branch above it converges there), which either

* calls the teleport `0x006020B0` when `this->+0x48 != 0` — and the teleport **zeroes
  velocity** at `0x0060210E`/`0x00602117`, which is exactly the halted `(inf, inf)`,
  `|v| = 0`, `stop = 0` state §1i.6 measured at both real warps; or
* writes the sync point straight into `m_point` — `0x00602B7B mov [edi], eax` with
  `edi = lea edi,[ebx+0x78]`, plus +0x7C/+0x80/+0x84.

So §1i.6's "the local copy lands exactly on the twin's teleport target" is no longer
an inference from coincidence: **`reseed` installs the sync agent's point and the
teleport is one of its two arms.** **OBSERVED.**

### 1j.3 WHY the twin falls behind — a HARD PIN, and this refines §1i.2

**This is the finding that explains §1i.2's oddest number** — that 52 of 52 twin
positions are within 0.00 u of ground the player really covered.

`Agent::GetPointAt` at `0x005FF820`:

```
0x005FF829  mov ecx,[edx+0x48]      ; m_timeStopMovement
0x005FF82C  test ecx,ecx
0x005FF82E  je  0x005FF861          ; no stop time -> extrapolate
0x005FF832  sub eax,ecx             ; time - m_timeStopMovement
0x005FF834  js  0x005FF861          ; still before the stop -> extrapolate
            ... copies [edx+0x88..0x94] (m_segmentPoint, 16 bytes) to out
```

**Past its stop time an agent's reported position is `m_segmentPoint` VERBATIM — the
endpoint of its last granted segment — and does not advance at all.** The lane found
its own falsifiable control and it held: the extrapolator carries assert
`AgAgent:978` `!m_timeStopMovement || ((int)(m_timeStopMovement - time) >= 0)`, the
exact complement of this branch, so an inverted reading would have been caught.
**OBSERVED.**

That is why the twin's positions are always positions the player occupied: **the twin
is pinned at the endpoint of the last destination our server granted**, and our server
grants only destinations the client itself chose (51 of 51 bit-identical echoes,
§1j.5). The twin is not "following slowly" — between grants it is **not moving at
all**, and §1i.2's 18 stalls of median 4.85 s are that pin.

**REFUTED, and it corrects a claim I made in §1i:** "the sync agent moves only when
the server grants" is wrong *as a statement about simulation*. The advance routine
`0x005FF880` is **world-generic by construction** — it indexes both its clock
(`+0x148 + world*0x64`) and its spatial grid by the agent's own `+0x24`, with no
compare and no branch on the world, and none of its 8 direct callers gates on world.
`INTERNAL_FLAG_IN_WORLD` (m_flags bit 17, `0x20000`) is the precondition, not the
world field. Of 8 sites in AgAgent that *do* branch on `+0x24`, **all 8 gate
timer-queue bookkeeping and none gates the position advance.** So the sync agent is
simulated locally like any other; what is wire-only is its **destinations**, and what
freezes it is the pin above. **OBSERVED.**

### 1j.4 Two more open items closed, and one capture claim REFUTED

* **`snaptest`'s `ecx` is the AgTrack object at `context+0x1CC`** — not an agent, which
  is why §1h.1's deref produced ids like 574588536. `agtrack 0x00605FC0` does
  `mov esi, ecx` and calls `snaptest` with `mov ecx, esi`; agtrack's `this` is
  `context+0x1CC` via `0x00602BB7 add ecx, 0x1cc`. Its `arg1` is a 0x1C-byte
  per-agent-id state record whose first dword is `clientControlled`. **OBSERVED —
  §1h.1's "NOT DETERMINED" is now determined.**
* **The reseed loop is not targeted.** `agtrack` diverts world-1 agents away entirely
  (`cmp edx, 1` / `je`), runs `snaptest` only for a sync-world agent, and **on a zero
  return reseeds EVERY world-1 agent**, not just the one that failed. **OBSERVED.**
* **REFUTED — the twin's big position steps are a SAMPLING artifact, not storage and
  not a wire jump.** A lane proposed both; the refutation pass killed both. The hook
  fires on the twin only at `snaptest` (70) and `reseed` (14), **p50 1281 ms apart**,
  and 288 u/s × 1.281 s = **368.9 u**, matching the observed p50 step of 368.6 u
  almost exactly. **The twin really is walking between our samples.** The seeding rule
  survives in amended form: when a new leg is installed, base `m_point` equals the
  previous leg extrapolated to the new `+0x58` — 34 of 34 sampled transitions across
  runs 4 and 5 agreeing to under 3e-4 u.
* **REFUTED — "`m_point` has exactly three stores in AgAgent".** There are at least
  **six**: `0x005FE46F`, `0x005FEA92`, `0x00602C28` (visible to `--field 0x78`) plus
  `0x005FF8B9`, `0x00602B7B`, `0x00602132` spelled in forms that filter misses. A
  reminder of the standing rule that a `--field` census is a floor.

### 1j.5 What our server does, independently confirmed

* **No server-side path solving at all.** Every destination we put on the wire is a
  **bit-identical echo of a point the client chose — 51 of 51** in run 5. **OBSERVED.**
* **LOAD-BEARING NEGATIVE: we have no position-correction channel.** Our server never
  tells the client where *it* thinks the player is — not by default, and not under the
  movement flags. So the only thing that ever reconciles the two copies is the client's
  own reseed, which is the rollback. **OBSERVED.**
* **`0x001E`'s delta is real**, from a monotonic clock (QueryPerformanceCounter), not a
  constant — but it is emitted on a fixed ~20 Hz sleep loop and per-tick `int()`
  truncation of the sleep overshoot makes the running sum advance the client's world
  clock **~1.3% slow**, where retail's sum tracks wall clock to 0.1%. **This is very
  likely the already-recorded "movetap's `now` runs 1.36% slow"** — that `now` is the
  int32 this message advances. **CORROBORATED.** Far too small to explain the warps,
  and worth fixing on its own terms.

### 1j.7 The asymmetry is COMPILED IN, not a property of this capture

**ONE WITNESS.** The synthesis pass read these bytes itself and they did **not** go
through the refutation pass the rest of §1j did. Treat accordingly.

The two worlds are reached through **two different agent arrays**, and the names are
ArenaNet's own — two asserts in `AgMsg.cpp`, at lines 579 and 584, name the pair
**`syncPtr`** and **`asyncPtr`**:

| path | array | bound | which array |
|---|---|---|---|
| `agapi_setdest` `0x005FC7A0` — **local input** | `[ctx+0x14C]` | `[ctx+0x154]` | **asyncPtr** |
| the wire handler `0x005FD890` — **our `0x0029`** | `[ctx+0xE8]` | `[ctx+0xF0]` | **syncPtr** |

`0x14C − 0xE8 = 0x154 − 0xF0 = 0x64`, the known world stride. Both funnel into the same
destination setter `0x00602A40`.

**So local player input structurally cannot address the sync world, and the wire cannot
address the local one.** That is compiled in — it is not something this run happened to
exhibit, and no grant policy changes it. It is the reason §1i.3's 557-vs-51 split is a
property of the client rather than of our server.

The capture agrees, split by `this` on the setter's return address:

| object | from | n |
|---|---|---|
| local `0x21E20128` | `0x005FC8F5` (`agapi_setdest`, local solver) | 546 |
| local `0x21E20128` | `0x0060244D` (the shared teleport) | 11 |
| **twin `0x21E208D8`** | **`0x005FD918` (AgMsg, the wire) — and nothing else** | **51** |

Replicated in run 4 (75/5 against 9). And **51 of 51 twin leg starts follow a setter
within 250 ms, with 0 legs starting without one.**

**The gate reads the twin through the freezing accessor.** Three of `0x005FF820`'s six
callers (`0x006057AD`, `0x006057BA`, `0x006058BF`) are inside `snaptest` itself, which
fetches both positions through it, hands them to `0x00709990` with the float at
**`0x00946564` = 300.0**, and compares. So the pin of §1j.3 is not incidental to the
desync test — **it is what the desync test measures.** `agtrack` then branches:
`test eax,eax` / `jne` skips the correction entirely; only a ZERO return reaches the
reseed walk.

### 1j.6 Still open after this pass

* **UNVERIFIED, flagged by the lane that found it:** `reseed`'s preamble may make its
  second-half guard at `0x00602457` always false — `0x006022E7` calls `0x00602540`
  whenever `this->+0x48 != 0`, and that path reaches the same state the guard tests.
  If so, the stop-dead/re-face block is dead code in practice. Not resolved.
* `agent+0x24` is still **not captured** by the hook, so the world identity is read
  from call-site structure rather than from the record. One row in
  `content/movecode.toml`.
* Nothing here measures the `heading-rate` suppressor (§1i.5), which is still a sixth
  of our grant budget.

---

## 1k. MOVECODE-K1 — the keep-alive re-grant, BUILT and PRE-REGISTERED. Not yet run.

**Built 2026-08-27.** `--keepalive-grant`, off by default,
`toolkit/authsrv/authsrv.py` + `test_keepalive.py` (32 checks, floor 32).

### 1k.1 What it does, and why it is not "grant more often"

While our model says the client's **sync** copy has PARKED more than 100.0 u from the
player's own last **reported** position, re-grant that reported position, unclipped.

Two things make this the sixth candidate rather than a repeat of the five dead ones:

* **The target is named.** §1j.7: local input resolves through `asyncPtr`
  (`[ctx+0x14C]`) and the wire through `syncPtr` (`[ctx+0xE8]`). A `0x0029`
  **cannot move the displayed body** — it re-bases the sync twin and nothing else.
  That is why this is safe where the tick's own arrival broadcast was not: `0x002C`
  is a hard set and lands on *both* copies. Every earlier candidate was scored with
  an instrument that could not tell the two copies apart.
* **The trigger is the pin, not a clock.** §1j.3: past `m_timeStopMovement` the twin's
  position is `m_segmentPoint` verbatim and does not advance at all. `_sync_position`
  already models exactly that, so the grant fires when the twin has parked — not on a
  timer, which grants hardest when the player is stationary and the twin is already
  correct.

### 1k.2 What the graveyard forbids, compiled in as refusals

`--heading-grant` refreshed at 0.32 s — **faster than retail's 0.49 s** — and still
warped. Its epitaph names two failures, and both are refusals in the code:

| the dead candidate's failure | what K1 does |
|---|---|
| point computed from `state["pos"]`, the server's model | sends `state["client_pos"]`, written only on the accept path and only from what the client said |
| point CLIPPED to our navmesh | unclipped — the point is one the client already stood on |

And one guard the graveyard implies but never had: **a REJECTED position report
refuses the grant**, because a disagreement between our model and the client is term
(1) failing live.

`test_keepalive.py` §5–§7 check these **at the source**, not through the verdict,
because an edit swapping `client_pos` for `pos` would keep every behaviour test green
while reintroducing a measured warp. Both guards were proven to go red by planting the
exact regressions.

### 1k.3 THE PREDICTION, registered before the run

Scored with **`movehook`**, which no earlier candidate had — it separates the two world
copies by object address, so "separation" means what its label says rather than
pooling two bodies (§1i.1).

| quantity | run 5 (control) | K1 predicts |
|---|---|---|
| twin idle time | **100.2 s** of 207.6 s | falls toward the local copy's **37.8 s** |
| twin grant gaps, p50 | **1.78 s** | falls toward retail's **0.82 s** |
| grant density | **1.40** / 1000 u | rises toward retail's p50 **4.30**, floor 1.70 |
| reseeds past the 299.33 cut | **11 of 14** | falls toward **0** |
| reseeds that DISPLACED the player | **2** | **0** |

**REFUTED IF** the reseed count does not fall, **or** if any displaced reseed appears
that run 5 did not have. The second clause is the one that matters: four of the five
dead candidates improved one number while making the warp worse, and
`--client-endpoint` in particular met both its terms and went from 5.7 to 14.6
jumps/min. **A fall in idle time with no fall in reseeds is a REFUTATION, not a
partial win.**

### 1k.4 The negative control, and why it is a flag rather than a second run

`--keepalive-separation <huge>` disarms the re-grant while leaving **every other term
of the run identical** — same build, same flags, same operator, same map. It is
refused without `--keepalive-grant`, because a run carrying only the override would
look configured and change nothing.

Run the control arm **in the same session** if the operator's patience allows; a
control taken from a different day carries the day's own differences.

### 1k.5 What is NOT claimed

* **Nothing here has been run.** Every number in §1k.3's left column is run 5; the
  right column is a prediction. UNVERIFIED until a capture says otherwise.
* The pin budget the earlier drafts quoted (300 u ÷ 288 u/s = 1.042 s) assumed
  separation grows at the full walk speed. **That rate is not cleanly measurable from
  run 5** — 8 of 14 reseeds have a grant landing inside the same tick, so grants and
  reseeds are temporally entangled. The **cadence** comparison (ours p50 1.78 s
  against retail's 0.82 s) needs no such assumption and is what K1 is built against.
* K1 does not touch the two defects §1i.5 named. The freshness window still refuses 13
  of 17 clicks and the map-280 mesh hole still refuses 4. K1 grants **in spite of**
  those refusals rather than fixing them, which is deliberate — it is one change — but
  it means a null result does not clear them.

---

## 1l. MOVECODE-K1 ARM A — **REFUTED, and it made the warp WORSE**

**OBSERVED, 2026-08-27.** Map 280, 966 records, v5, both controls FIRED, 114 s of a
228.7 s server session. Capture at `vault/research/movecode/k1-treatment/`, server log
`vault/captures/gamesrv/authsrv-20260827T212317-c1.jsonl`. **The control arm was never
run** — the runsheet's file-the-capture step used bash `cp` on a PowerShell machine and
died — so everything below compares against **run 5** rather than against a matched
control, and that is a weaker comparison than §1k.4 asked for.

### 1l.1 The operator's report, which is the ground truth here

> *"did a few long walks, then pressed keyboard after ~3-4 clicks and warped back to
> spawn. i ended the run stuck in the ground after warping back to spawn again and
> pressing W during a long walk."*

**Two warps to spawn, and the character ended stuck in terrain.** Run 5's warps were
690.8 u and 510.7 u; nothing in five prior runs put the body back at the spawn point.

### 1l.2 The instrument said it was CLEAN, and the instrument was wrong

This is the finding worth keeping, independently of K1.

| | run 5 | arm A |
|---|---|---|
| reseeds past the 299.33 cut | 11 of 14 | **3 of 17** |
| displacements **following a reseed** | 2 | **0** |

Read off §1k.3's registered table, arm A **passed**: the reseed count fell and the
displaced-reseed count went to zero. It is the number I chose to be refuted by, and it
would have scored a run the operator watched warp to spawn as an improvement.

**What it missed:** both warps went through the **teleport** arm
(`teleport → setter`), not the record straight after a reseed, so they were counted in
the total and then buried under a subcount that happened to be zero.

| | run 5 | arm A |
|---|---|---|
| displacements, total | 10 | 3 |
| **largest displacement** | **1,871 u** | **5,970 u** |
| total displaced distance | 8,527 u | 8,040 u |

**5,970 u and 1,947 u**, and both land on the spawn point's own coordinates — spawn is
`(−6036.0, −2519.0)`, the two landings are `(−6032.8, −1828.0)` and
`(−5932.3, −2284.1)`. The operator's "warped back to spawn" is in the bytes, twice.

`readhook` now leads with **magnitude and total**, with the per-site attribution as
detail. A displacement is a warp whichever site performed it.

### 1l.3 Why it fired at all, and why twice

`keepalivelog.py` over the arm's server log: **1,773 verdict rows, 2 fired.**

| reason | n | when |
|---|---|---|
| `no-report` | 1,527 | all before t = 90 s |
| `rate-limited` | 119 | after the first report |
| `twin-walking` | 117 | after the first report |
| `report-rejected` | 8 | — |
| **`keepalive` (fired)** | **2** | **t = 60–90 s** |

**The first `position_report` arrived at t = 77.8 s.** So the 1,527 `no-report`
refusals are correct behaviour — the flag refuses until the client has told us where it
is. Both fires happened in the 12 seconds *after* that first report, and then the flag
never fired again: `twin-walking` blocked everything after t = 90.

**Separation at the verdicts: min 103, p50 5,044, max 5,977 u.** Our sync model had the
twin ~5 km from the player.

### 1l.4 The design error, and it is mine

> **WITHDRAWN by §1m.1.** This subsection says the keep-alive granted a 5,000 u leg.
> It did not: both fires were ~100 u nudges (sep 103.2 and 114.15), and the spawn warp
> at t=78.91 happened **0.8 s before the first one**. The 5,044 u p50 I quoted is a
> distribution over `twin-walking` REFUSALS, not grants. The paragraph below is kept
> because a wrong reading with its correction attached is worth more than a deleted
> one — but do not carry any of it forward. §1l.5's own "NOT DETERMINED" caveat was
> the correct reading and the rest of this section talked past it.

The sync model is seeded at spawn and advances only on grants we send. Our server
granted little, so by t = 78 s the model still had the twin **near spawn** while the
player had walked 5 km away. The keep-alive then did exactly what it was built to do:
it granted the player's reported position to a twin sitting at spawn — **a 5,000 u
leg**.

While the twin walks that leg it is somewhere on a straight line from spawn, wrong
everywhere along it, and my `twin-walking` gate **refuses to correct it** for the whole
traverse. The client's desync test meanwhile compares the player against that
mid-traverse position and pulls the player back toward it.

**The flag has no bound on how far a re-grant may send the twin.** A keep-alive is
supposed to nudge a twin that has drifted; granting a 5 km leg is not a nudge, and the
`twin-walking` gate then guarantees a long window in which nothing can fix it. Both of
`--heading-grant`'s epitaph terms were respected — the point was the report in hand and
it was unclipped — and the candidate still failed, on a term the graveyard does not
name: **the LENGTH of the leg the grant creates.**

### 1l.5 Status

**MOVECODE-K1 is REFUTED as built** and joins the graveyard as the sixth candidate.
What a rebuild would need, and none of it is a small edit:

* **A distance cap.** Refuse the re-grant when the modelled separation exceeds some
  bound, or grant an intermediate point instead of the player's own. An uncapped
  re-grant is a teleport with extra steps.
* **Something to fix a twin that is already kilometres out.** The cap alone leaves that
  case unhandled, and it is the case arm A was in from t = 78 s onward.
* **A matched control.** Arm A is compared to run 5, which had a different walk
  (`chcli_dir` 140 against run 5's 494 — far less keyboard input), so the reseed and
  grant counts are not like-for-like.

**NOT DETERMINED:** whether the two warps were *caused* by the keep-alive. Two fires is
too few to attribute, the arms were not matched, and run 5 had displacements of its own.
What is OBSERVED is that the largest displacement is **3.2× run 5's** and that both
landings are at spawn, which is where our starved sync model had the twin.

---

## 1m. CORRECTING §1l, and MOVECODE-K2 — the click echo

### 1m.1 §1l.4 BLAMED THE WRONG THING, and the log says so plainly

§1l.4 said the keep-alive "granted a 5,000 u leg" and that this produced the spawn
warps. **Both halves are wrong.** Reading the fired rows rather than the aggregate:

| t | event | detail |
|---|---|---|
| 68.35 | click | refused `geo-stale` |
| **77.85** | **first position report ever** | player at `(−5117.8, −503.7)` |
| 78.37–78.63 | keepalive | `twin-walking`, sep **2066 → 1993 u**, falling |
| **78.91** | **report** | **player at `(−5978.7, −2250.2)` — SPAWN** |
| 79.69 | keepalive | **FIRED, sep 103.2 u** |
| 80.86 | keepalive | **FIRED, sep 114.15 u** |

**Both fires were ~100 u nudges, and the warp at t=78.91 happened 0.8 s BEFORE the
first one.** The p50 5,044 u figure §1l quoted came from the `twin-walking` rows,
which are refusals — I read a distribution over refused verdicts as if it described
the grants. **MOVECODE-K1 did not cause the spawn warps**, and §1l.4's "design error"
paragraph describes a leg that was never granted. §1l's own §1l.5 caveat
("NOT DETERMINED whether the keep-alive caused the warps") was the correct reading and
the rest of the section talked past it.

**K1 stays refuted** — it fired twice in 1,773 verdicts, which is no exposure — but it
is refuted for being *inert*, not for being harmful.

### 1m.2 What DID cause it: a gate the client cannot satisfy

The first 77.85 s of that session, from the server's own log:

* **4 clicks. All 4 refused `geo-stale`.**
* **0 position reports.**
* **0 grants.** The sync copy never left spawn while the operator click-walked
  ~2,000 u away from it.

`fresh` is `(time.time() - pos_seen) <= 1.0`. This file already had the measurement
that makes that unsatisfiable, two screens below the gate:

> *the client sends NO position while click-moving. `0x003E` carries a destination and
> a plane and nothing else, and one capture ran 37 seconds without the client saying
> where it was.*

**So during click-walking the precondition is not slow, it is impossible**, and every
click dies for a reason the client cannot fix. §1i.5 called this "a cadence defect"
and put it at 13 of 17 refusals; that was right about the count and too gentle about
the mechanism. It is not that reports are late. In that mode **there are none**.

The operator's first keyboard press produced the first report, and 1.06 s later the
client reconciled the accumulated divergence by putting the body back on the sync copy
— at spawn. **"pressed keyboard after ~3-4 clicks and warped back to spawn."** Twice.

### 1m.3 MOVECODE-K2 — `--click-echo`

**One condition.** When a click is refused for **staleness only**, answer it with the
**verbatim clicked point** instead of saying nothing. `geo-unplaced` and `geo-blocked`
keep refusing — they are the geometry defect (§1i.5's other 4) and want the mesh fixed,
not a policy change.

It sends `dest`, the click's own destination field, unclipped, through the **same send
the shipped path already uses**. Both of `--heading-grant`'s named failures are
structurally impossible: the point is not computed from `state["pos"]`, and it is not
clipped. It still passes through the **rate gate**, so it cannot out-run retail's
cadence and a click under active keyboard authority is still dropped — retail's own
measured contract.

**THE HONEST COUNTER-ARGUMENT, and it is why this is opt-in.** Answering a click has
its own measured harm, recorded in `authsrv.py` beside the gate:

> *the player clicked a spot up a staircase, the character set off correctly towards
> the FOOT of the stairs — a real route, around the railing — and about a second later
> snapped onto a straight line aimed at the clicked point, straight through the
> railing.*

That is this same mechanism from the other side: our grant moves the sync copy onto the
straight line and the client's reconcile pulls the body onto it. **So both arms are
wrong and the question is which is less wrong** — refusing leaves the sync copy at the
ORIGIN, diverging by the whole distance walked (2,000 u, measured); echoing leaves it
on the straight line to the DESTINATION, diverging only around obstacles. That is a
measurement, not an argument, which is what the run is for. `--router` answers the same
click with real legs and is the better answer where a mesh exists; K2 is the fallback,
and ROUTER intercepts first so they compose rather than race.

### 1m.4 The registered prediction — MOVECODE-P3

Against **K1 arm A** as the baseline (`vault/research/movecode/k1-treatment/`), same
map, same walking style — *click-walk first, then press a key*, which is the sequence
that produced the warps.

| quantity | arm A | K2 predicts |
|---|---|---|
| `geo-stale` clicks answered | **0 of 4** | **all of them** |
| grants to the sync copy | 13 | **> 13** |
| sync copy idle | **74.3%** of its span | falls |
| displacements landing within 300 u of spawn | **2** | **0** |
| largest displacement | **5,970 u** | **< 5,970 u** |

**REFUTED IF the largest displacement exceeds 5,970 u, or if any displacement still
lands within 300 u of the spawn point.** The second clause is the one that matters —
it is the operator's own report turned into a number.

**EXPOSURE FLOOR, pre-registered.** The arm needs **≥ 3 `click_verdict` rows with
`click_echo: true`**. Fewer means the operator did not click-walk enough for the flag
to act and the arm measures nothing — re-run, do not conclude. This is the floor K1
arm A failed (2 fires) and which §1l should have led with.

**A THIRD OUTCOME THAT IS NOT A REFUTATION.** If the spawn warps stop but the
character starts phasing through railings on clicked routes, that is the staircase harm
above arriving as predicted, and it argues for `--router` rather than against K2.
Record it as its own row rather than scoring it as failure.

---

## 1n. MOVECODE-K2 RUN — **CONFIRMED on every registered clause, and it bought a NEW harm**

**OBSERVED, 2026-08-27.** Map 280, 1,058 records, v5, both controls FIRED, 88.1 s.
Capture `vault/research/movecode/k2/`, server log
`vault/captures/gamesrv/authsrv-20260827T230405-c1.jsonl`. Baseline throughout is
**K1 arm A**, same map and operator.

### 1n.1 The registered table — every row passes

**Exposure floor MET**: 8 echoed clicks against a floor of 3.

| §1m.4 quantity | arm A | K2 | predicted | |
|---|---|---|---|---|
| `geo-stale` clicks answered | 0 of 4 | **8 of 8** | all | ✅ |
| grants to the sync copy | 13 | **18** | > 13 | ✅ |
| sync copy idle | **74.3%** | **10.7%** | falls | ✅ |
| displacements within 300 u of spawn | 1 (a second at 691 u) | **0** | 0 | ✅ |
| largest displacement | **5,970 u** | **446 u** | < 5,970 | ✅ |

**The starvation is fixed, and not marginally.** The sync copy went from **2,804 u of
path to 17,627 u**, against the local copy's 18,577 u — **the two copies now walk
together**, which is the thing this whole arc has been trying to produce since §1i.
Its in-motion share went from 25.7% to 89.3%, *above* the local copy's 83.0%.

The three remaining displacements are **446, 292 and 363 u, all mid-route** — 6,000 to
7,700 u from spawn. Nothing went back to the spawn point. The operator confirms
**keyboard walking no longer warps**.

### 1n.2 The NEW harm, which the metric cannot see BY CONSTRUCTION

> *"by the 2nd click i already warped near the destination, then the third click had me
> no-clipping through props/on the base terrain… long range clicks or a
> second-click-to-move during a long click-to-move also gave me no-clip-terrain-walk"*

**A displacement counter cannot detect no-clip**, and that is structural rather than an
oversight I can tune away: no-clip is a **WALK** — `m_point` and the `+0x58` stamp both
advance, at 288 u/s, exactly like any legal leg. Every metric in §1m.4 is blind to it.
§1m.4 pre-registered this outcome as "not a refutation", and that label was right about
the *bookkeeping* and much too comfortable about the *harm*: a character walking through
props is not a smaller defect than one warping to spawn, it is a different one.

**The mechanism, and it is the same one from the other side.** K2 grants the clicked
point verbatim. The sync copy has no path solver — it walks the **straight line** to
whatever it is granted. The client's reconcile then puts the body on that line
(the 446/292/363 u displacements), and from there the body continues along ground its
own pathing would never have chosen. `authsrv.py` already had this measured, beside the
gate K2 changed:

> *the player clicked a spot up a staircase, the character set off correctly towards
> the FOOT of the stairs — a real route, around the railing — and about a second later
> snapped onto a straight line aimed at the clicked point, straight through the
> railing.*

That is this run's report, written down before this run happened. **K2 did not
introduce the straight line; it made the sync copy actually travel it** by answering
the 8 clicks that were previously dropped.

### 1n.3 So the trade is now measured, and it is not obviously good

| | refusing (shipped) | echoing (K2) |
|---|---|---|
| sync copy | parked at the ORIGIN | walks the straight line to the DESTINATION |
| divergence | the whole distance walked (2,000 u) | only around obstacles |
| the warp | **back to spawn**, 5,970 u | **forward to the route**, 446 u |
| the body ends up | where it was long ago | **inside props, on base terrain** |

§1m.3 predicted exactly this shape and called it "which is less wrong". The measurement
says K2 is 13× smaller in displacement and **worse in kind** — a 446 u nudge that
leaves you inside a prop is not obviously better than a 5,970 u one that leaves you at
spawn, and only the operator can price that.

### 1n.4 The answer is already in the tree, and it is `--router`

`router_answer_click` (`authsrv.py:5086`) answers a click with **the legs of a real
route over our mesh** instead of a straight line — which is what retail does
(ROUTER.md §1: waypoint chains at leg-completion cadence). Two properties settle why it
is the right next arm rather than a new build:

* **It never consults `fresh`.** It intercepts *above* the whole freshness/geometry
  block — "the freshness/geometry/hold machinery below never runs for it" — and
  returns False only when there is no mesh or no position belief. So it would have
  answered all 8 of this run's stale clicks, **without K2 being involved at all.**
* **A routed leg is walkable by construction**, so a reconcile onto it lands on ground
  the client's own collision agrees with. That is precisely the no-clip.

They compose rather than compete: ROUTER intercepts first, and K2 catches whatever it
falls through on.

**The known objection, and it is real.** The router arc already ran and the character
still warped — its run 5 showed *"a perfect routing origin and all four clicks routing
away from their destinations"*. `router_answer_click` takes its origin from
`state["pos"]`, the server's **integrator guess**, and during click-walking that guess
is never corrected by a report (§1m.2: zero reports in 78 s). A route from a wrong
origin is a wrong route.

**MOVECODE-K3, if the router arm reproduces that:** route from
`_sync_position(state, now)` instead of `state["pos"]`. We know where the sync copy is
**exactly** — we put it there, and §1i.3 proved the pairing 1:1 to a 15 ms maximum —
whereas `state["pos"]` is a belief. Routing from the copy the client actually
reconciles against is the origin that cannot be stale. **UNVERIFIED**; it is a
one-expression change and should not be built before the router arm says whether it is
needed.

---

## 1o. THE ROUTER ARM — **REFUTED, and it is WORSE than the echo alone.** My §1n.4 recommendation was wrong

**OBSERVED, 2026-08-27.** Map 280, `--router --click-echo`, 219 records, both controls
FIRED, 104.0 s. Capture `vault/research/movecode/k2-2/`, log
`authsrv-20260827T231722-c1.jsonl`.

**`--click-echo` never ran in this arm.** `router_answer_click` intercepts above the
freshness block and returns True, so there were **0 `click_verdict` rows**. This arm is
router-only, and the readout said "CLICK VERDICTS: 0" for a run that answered every
click -- exactly the blind report `keepalivelog.py` exists to prevent. It is
router-aware now.

### 1o.1 The ranking, measured, on the one number that survives all three arms

| arm | largest displacement | total | n |
|---|---|---|---|
| shipped, refuse the click (K1 arm A) | **5,970 u** | 8,040 u | 3 |
| **`--click-echo` alone (§1n)** | **446 u** | **1,101 u** | 3 |
| `--router` (this arm) | **2,127 u** | 3,276 u | 4 |

**The echo alone is the best configuration measured, by 4.8x over the router and 13x
over the shipped default.** §1n.4 recommended adding `--router` on the argument that a
routed leg is walkable by construction. That argument was sound and **the measurement
refutes it**: the operator reported "still warping/terrainwalking, even on single
clicks", and the number agrees.

The starvation stays fixed in both -- sync copy 82.4% in motion, 23,971 u of path
against the local copy's 26,929 u -- so this is not a regression to §1i's problem. It
is a worse *reconcile*.

### 1o.2 WHY, and the route is not the bug

I checked the failing route offline against the real mesh, and **it is a valid route**:
origin `(-4764, -2140)`, clicked destination `(-2581, -666)`, first granted leg
`(-6120, -2356)` -- 1,356 u the *wrong way*. All three legs are individually CLEAR, and
both shortcuts are genuinely BLOCKED (`origin -> leg2` stops 1,051 u short,
`origin -> dest` stops immediately). So `pathmap.route()` found a real way around a real
obstacle, 2.20x the straight line, which is ordinary.

**The bug is not the route. It is that our route is not the CLIENT'S route.** The
client paths the same click over its own mesh, gets a different answer, and the
reconcile then drags the body onto ours -- 1,356 u westward on that click. Echoing the
bare destination diverges only *around obstacles*; granting our own waypoints diverges
by the whole difference between two independent path solvers.

### 1o.3 The pathology the router-aware readout now names

**The same first leg was granted FOUR times** -- `(-6902, 3595)` x4, and
`(-6025, 3741)` x2 -- with `router_leg abandon` between them. The router recomputes on
each new position, lands on the same waypoint, and re-grants it, dragging the body back
to it each time. Its origins march while it does: `(-5899, 636)`, `(-6130, 1318)`,
`(-6199, 1523)`, `(-6393, 2096)` -- the integrator walking a route nobody is on.

That is the operator's "double click has even worse behaviors, clipping into the ground
or warping around". **Warping around** is this loop.

### 1o.4 Where that leaves it

* **Do not run `--router` for this.** REFUTED on its own registered ground.
* **`--click-echo` alone is the best measured configuration** and stays the
  recommendation.
* **MOVECODE-K3 (route from `_sync_position`) is WITHDRAWN before being built.** §1n.4
  proposed it to fix the router's origin. The origin is not the defect -- the origins
  above are on-mesh and the routes are valid. Fixing the origin would produce a
  *different* valid route that the client still disagrees with.
* **The residual is mesh AGREEMENT, not mesh correctness.** Every arm's remaining harm
  is the same shape: whatever we grant, the client's own solver disagrees, and the
  reconcile drags the body onto our answer. The only grant the client cannot disagree
  with is **the destination it chose itself**, which is why the echo wins -- and the
  no-clip that survives it (§1n.2) is the irreducible part of that disagreement, on the
  straight line between two points both parties agree on.

**NOT DETERMINED:** whether anything short of matching ArenaNet's own navmesh closes
the remaining gap. Three server-side policies have now been measured against it and the
best of them is the one that asserts the least.

---

## 1p. WHAT RETAIL ACTUALLY DOES DURING A CLICK-WALK — R1, offline

**Retail answers every click, immediately, from a position it does not have.** Over the
live corpus — 21 capture dirs → 20 admitted by the origin gate, 61 game connections,
61/61 decoding with byte closure in both directions, 7,028 c2s messages — there are **32
c2s `0x003E` clicks**, and **32 of 32 were answered within 0.065 s** (observed first-grant
latency 0.007–0.065 s). The answer is one of exactly two things: **the bit-exact clicked
point (19 of 32)**, or **a part-way first waypoint (13 of 32)** that is, in our own
independent decode of ArenaNet's own pathing archive, **a bit-exact navmesh trapezoid
corner in 13 of 19 distinct cases** and within 0.01 u of a trapezoid edge in 18 of 19. It
did all of this while holding a client position report **older than 1.0 s on 22 of 32
clicks** (older than 10 s on 13 of 32, max 20.99 s) and **no client position at all on 5
of 32**. **What this means for `--click-echo` is not that it is a lucky heuristic: it is
the exact subset of retail's contract we can reproduce bit-for-bit.** On all **13 of 13**
scorable clicks retail echoed, our own mesh independently says a straight line suffices,
so the echo *is* retail's answer there; on the other class our route's first waypoint
matches retail's on **0 of 11** routable rows, missing by 290.4–2,351.3 u. §1o's
conclusion stands and is now corroborated from ArenaNet's side.

**Whole-section scope, stated once and applying to every number below.** 32 clicks / 12
connections / 7 sessions / 6 maps / 5 characters, and **61 of 61 live connections come
from one client IP (10.0.0.210), one GPU string, one account (`capture`)** — **one
operator, one machine**, solo, across three client-build eras. The 26 clicks that can be
scored against a mesh sit on **two navmeshes, not three maps**: content maps 146 and 148
both resolve to pathing file 113021 (n=15), map 280 to 165811 (n=11). Nothing here is
evidence about a party, a crowded outpost, stacked geometry (0 of 26 rows have a stacked
destination), or any post-Searing outdoor, explorable, PvP or dungeon mesh.

---

### 1p.1 R1 was mostly already answered, and `HANDOFF-WARP.md` §4 sends the next session to re-measure it

**REFUTED.** `HANDOFF-WARP.md:74` reads:

> **Nobody has ever looked.** Three policies were invented and measured against each
> other; none was compared against ArenaNet answering the same situation.

That is wrong, and **this document is one of the places it is wrong from**. §1n.4 of this
file already writes "which is what retail does (ROUTER.md §1: waypoint chains at
leg-completion cadence)". `studies/movement/ROUTER.md` §1/§3 is a 605-line record of
exactly the comparison the handoff says nobody made, dated 2026-08-26, and
`python toolkit/clientscan/routerbench.py --census` still reproduces it bit-for-bit today
at HEAD `1f36508`: `live clicks: 29, skipped connections: 1`,
`kinds: {'part-way': 13, 'verbatim': 16}`, `within 0.2s: 29/29`. `--score` prints
`scored clicks: 26   refused: 4` with exactly 13 rows at `firstwp=0.0u`. A handoff that
sends a cold session to re-derive a committed, still-green measurement is the exact
failure mode the top of `CLAUDE.md` is about, and it cost this arc five agent-lanes to
discover.

**The replacement text for `:74`:**

> **Mostly already looked at; the record is `studies/movement/ROUTER.md` §1/§3 and
> `REALFIX.md` §0.14–§0.15/§0.18, and `FINDINGS.md` §1n.4 already cites it.**
> `routerbench.py --census` prints ≥29 attributed clicks, ≥16 verbatim / ≥13 part-way,
> all answered within one RTT, and still reproduces on 2026-08-28. What is genuinely open
> is narrower and is listed in §1p.10.

**`HANDOFF-WARP.md:81-84`** — "**Does retail's client send position during a
click-walk?** Ours does not … If retail's client *does*, something we send (or fail to
send) suppresses it, and that is a far better lever than any grant policy." This one is
**PARTLY answered, and the committed answer is overstated in our own tree** (§1p.4). It
should read: *"Answered at reduced strength: retail's client is ~5–10× quieter during
click-walks than during keyboard steering, but it is not silent — 3–4 of 27 windows carry
position rows. There is no large lever here; the lever is the origin question in §1p.3."*

**`HANDOFF-WARP.md:89-90`** — "It is also the only route that can tell us the residual
no-clip is *unavoidable* rather than *unsolved*." **REFUTED, strike it.** Retail's chains
come off the mesh the client agrees with **by construction**, so measuring them cannot
bound what our mesh can achieve. That question belongs to R4 and the handoff already
assigns it there at `:126-131`.

---

### 1p.2 The contract, re-derived today (R1b — ANSWERED)

**OBSERVED.** Independently rebuilt by four lanes from `livewire.decode_conn`, three of
which never called `routerbench.census()`. The corpus-wide split, including the
connection the committed census cannot attribute, is **19 verbatim / 13 part-way of 32**;
`ROUTER.md`'s method-bounded 16/29 and 13/29 are over a method-selected population and
should be quoted with the 32 alongside.

| clause | status | evidence |
|---|---|---|
| first answer within one RTT | **OBSERVED** | 32 of 32 clicks answered, latency 0.007–0.065 s (3.1× inside the 0.2 s cut) |
| answer is the bit-exact click point, or a part-way waypoint | **OBSERVED** | 19 / 13 of 32; all 19 echoes are `first_dist == 0.0` **exactly**, so "verbatim" is not an artifact of `EXACT_TOL = 5.0` — the smallest part-way offset is 131.08 u, a 131 u margin |
| terminal grant is the bit-exact click point | **OBSERVED** | every completed chain |
| further legs at leg-completion cadence, 288 u/s | **PARTLY — n=5 chains** | 9 of 10 origin-free legs within 20 ms, but **7 of the 10 come from one specimen** (`_63805`), 3 of 5 first legs are circular (origin dead-reckoned at the speed under test), and one chain contradicts it |
| chain grammar: one `op43` speed row at chain start | **OBSERVED on 1 of 5** | only `_63805@1103.590` carries it; the other four multi-grant chains carry **no** `op43` for the player agent within ±0.5 s |
| any new c2s input abandons the chain | **OBSERVED** | ends over 26 scored: terminal 18, `superseded:62` 5, `superseded:61` 2, `superseded:57` 1 |

**CONTESTED, n=1 — the cadence counterexample.** `20260821T163511/_61106 t=67.787`
granted two waypoints **41 ms apart** (+0.007 s, +0.048 s) with 777 u of walking between
the origin and wp0, from an origin anchored to a raw report 0.12 s old; the whole
1,546 u / 5.37 s chain was granted inside 2.19 s. `ROUTER.md` does not mention this
specimen. It is contested rather than refuting because its first grant sits 34.7 u from
the D1 lead prediction and could be a keyboard-lead refresh; four arguments favour the
click reading, and one cheap check settles it (does any other `op61` on that connection
draw two `op41`s?).

**Corrections to `ROUTER.md`'s own reporting**, all measured, none affecting its
conclusions:

* **"29/29 within one RTT" is not a third fact.** `kind` is `no-answer` **iff** `first_dt`
  is `None` or `> RTT_WINDOW`; measured, both buckets are 0, so `within == total` is
  algebraically identical to `16 + 13 = 29`. `test_routerbench.py:247` and `:253` both
  check it, so one ledger check is a duplicate.
* **`firstwp = 0.0` and `len r = 1.00` are one bit printed as three columns.** Over the 13
  rows, `max |ratio − 1| = 0.000e+00` exactly and `max retail→ours = 2.3e-13`; over all 15
  one-leg scored rows `--score`'s `firstwp` equals `--census`'s own `d` column 15/15.
* **"scored 26, refused 4" mixes units.** The 4 are *connections*, hiding **6 clicks**.
  The honest ledger is 26 scored + 6 unscored = 32.
* **"24/26 retail legs clip-clean" is 24/25 computed** — the 26th (`_60935@58.694`) never
  had the field computed, because `route()` refused first.
* **8 of the 26 published length ratios compare our full route to a superseded ONE-grant
  fragment** (all 8 have `n_grants = 1`), including ROUTER-Q3's headline "0.34–0.41× our
  length" (both specimens) and ROUTER-Q2's 127.84×. Only the 18 terminal-chain ratios are
  like-for-like; the two clean ones are `_63805` 1.18× and `_60935` 1.26×.
* **"every retail waypoint ≤120.3 u from our polyline … ≤12.0 u" is a directed distance.**
  Reverse (our corners → retail's polyline) is **202.7 u** and **249.9 u**; reverse exceeds
  forward on 10 of 25 routed rows. Publish the Hausdorff or both directions.
* **"nothing went stale" is corpus-invariance, not robustness.** The newest live capture is
  `20260824T074002`; `ROUTER.md` is dated 2026-08-26. No new click-bearing capture has
  landed, so invariance was guaranteed. The prose should carry `≥29 / ≥16 / ≥13` floors
  plus the per-connection anchors, the way `test_routerbench.py` already does.

---

### 1p.3 Retail does not need a fresh client position, and our freshness gate models a contract it does not have

**OBSERVED — the strongest actionable finding in this section, and it does not depend on
§1p.4 at all.**

| | count | denominator |
|---|---|---|
| clicks answered with last position report **> 1.0 s** old | 22 | 32 |
| > 5.0 s | 16 | 32 |
| > 10.0 s | 13 | 32 |
| **no client position ever reported on the connection** | 5 | 32 |
| answered anyway, within 0.065 s | **32** | 32 |

Age of the last report at click time, n=27 attributable: p0 0.035, p50 2.334, p75 13.144,
max **20.993 s**. Connection `20260817T183323/_49545` runs 78.7 s with 3 clicks and **zero
`0x003D` and zero `0x0047` for the whole connection** — verified to carry its own prologue
(`op10`, `op11 'Gw/38833.0 (Win32)'`, `op409`), so those are real zeros over a whole
connection, not a mid-stream view. All three clicks were answered by agent 332 with
bit-equal echoes at +0.030/+0.032/+0.032 s.

**Weight correction, applied.** That connection is **not** the strongest evidence for
anything about silence: it carries 2.11 s of the corpus's ~70 s of click-caused motion
(**3.0%**), its clicks rank 21st, 22nd and 24th of 32 by exposure, and its zero-`op61` half
is **selected on** — `routerbench.player_agent()` votes with `op61`, so the census skips a
click-bearing connection **iff** it has no `op61`. Its real value is R1(b): three more
bit-equal verbatim echoes, and it contributes exactly zero to R1(a)'s published headline,
which already dropped its clicks as no-origin.

**Therefore:** `fresh = (time.time() - state.get("pos_seen", 0.0)) <= 1.0`
(`authsrv.py:16583`) encodes a precondition **retail does not have**. And retail is not
compensating with corrections either:

* **`0x002C AGENT_UPDATE_POSITION` fires 13 times in the entire live corpus**, 5 of them to
  the player, over 7,038 s of in-world connection span — one player reposition per 1,407 s.
  **None of the five is a correction:** 2 are spawn placements (no prior report, no prior
  grant), 3 are jumps of 5,308–5,376 u after 26.1–71.7 s of report silence. 0 of 5 is under
  1,000 u.
* **No snap-back through the ordinary grant either.** Conditioned on a self-report ≤0.5 s
  old, **3 of 3,501** player grants (0.09%) land more than 1,000 u from it; p99 is 817.1 u,
  barely above the 765 u heading lead. The unconditioned 2.37% tail beyond 1,000 u is
  report *staleness*, not repositioning, and disappears once the report is required fresh.
* **A periodic server-side position sync is NOT FOUND.** Of 3,672 player grants, **3,621
  (98.6%) answer a c2s input within 2 s** (median latency **36 ms**); the 51 unprompted ones
  all had a prior input 2.19–15.57 s earlier and 34 of the 51 sit on 2 of 9 connections.
  There is no clock-driven mechanism to copy.
* **`RECONSTRUCTION`, n=2:** `0x0067` (op103) looks like an invalidate-position sentinel —
  all 3 rows in the corpus carry `(inf, inf)`, and two of them precede the two spawn-placement
  `0x002C` by 1.94 s and 2.00 s.

---

### 1p.4 Does the client report during a click-walk? The committed answer is OVERSTATED — and it is ours

This is the section that corrects our own record. **`REALFIX.md` §0.18 states "retail's own
client is report-silent during click-walks (zero counterexamples corpus-wide)";
`routerbench.py:180-182` asserts it in `modeled_origin`'s docstring; `authsrv.py:5044`
ships the chain scheduler on it.** Two lanes were asked to re-measure it, and **both
independently built the same vacuous instrument and got zero.**

**REFUTED — the zero is an identity, not a measurement.** `routerbench.py:108` defines
`INPUT_OPS = frozenset({OP_REPORT, OP_CLICK, OP_STOP, 57})` = `{61, 62, 71, 57}`, which
**contains both position-bearing opcodes**. Both lanes closed the exposure window at the
first c2s row in `INPUT_OPS`, then counted rows with op in `{61, 71}` strictly inside it.
The counted event *is* the terminator, so `n_inside` is identically 0 for any possible
corpus. Two published exposures, 70.07 s and 70.34 s, both with the same forced zero.

**The positive control nobody had run.** 27 synthetic c2s `0x003D` spliced into the exact
midpoint of every one of the 27 published windows in the **real** corpus: **0 of 27
recovered**, and the exposure fell **exactly 50.0%** — the signature of edge-eating.

**With a window censored only by a genuine new command:**

| window construction | exposure | position rows inside | windows carrying any |
|---|---|---|---|
| `[click, click+walk_t]`, closed by `INPUT_OPS` (published) | 70.07–70.34 s | **0 (forced)** | 0 of 27 |
| `[click, click+walk_t]`, closed by `0x003E`/`0x0039` only | ~~77.44 s~~ **79.73 s** | ~~7~~ **24** | ~~3 of 27~~ **4 of 27** |
| `[first grant, ETA]`, closed by `0x003E`/`0x0039`/capture-end | 82.22 s | **25** | 4 of 27 |

> **ROW 2 CORRECTED 2026-08-28, §1s.7 — it was not reproducible.** Two independent
> reimplementations get **27 windows / 79.73 s / 24 rows / 4 of 27** under *both* the
> published construction (`term{62,57}` / `count{61,71}`) and `term{62,71,57}` /
> `count{61}`; `term{62}` alone gives 26 windows; and **no 3-window subset of the
> carrying counts `{12, 7, 3, 2}` sums to 7.** The original row's script was a
> scratchpad artifact that cannot be re-run — the two are inconsistent, not
> differently sensitive. **And of the 24, only 3 sit at the odometer stride** (490–530 u
> at ~288 u/s): 22 of 24 are lead-CHANGED steering reports, which refute nothing about
> a click-walk. The counterexample class is ~3, not 24 — see §1s.7.

**The null was wrong too.** The quoted 0.500 s keyboard baseline is the **steering**
cadence: of 2,917 consecutive `op61` pairs, 2,574 change the lead vector (median 0.500 s)
and **343 do not** (median **1.768 s**, p10 0.501, p90 1.786). A click-walk is a
steady-heading walk by construction, so its null is the steady arm — **~47 reports over
82.22 s, not ~140**. Independently, a second lane found the mechanism: **the client
re-sends `0x003D` every ~510–512 units TRAVELLED**, not on a clock — over 243
unchanged-heading pairs with real displacement, distance IQR/median = **0.008** (p25 509.2,
p50 510.0, p75 513.3; 205/243 within ±6% of 512) against time IQR/median = 0.253, and
distance still holds at p50 511.0 on the **101 pairs not moving at ~288 u/s**, which are the
only rows that can separate the two hypotheses. An odometer predicts **1.96 sends per
1,000 u**, not the 5.997/1,000 u the published power calculation used.

**The corrected reading, and its label.** **OBSERVED:** retail's client is **markedly
quieter during click-walks than during keyboard steering** — 4 events in 67.90 s = 0.0589/s
against a steady-heading null of 0.566/s, **9.6× quieter**; under the odometer null,
7 observed against ~43.7 predicted over 22,303 modelled units, **0.16×**. **The published
`P(0) = 1.8e-53` and `λ = 121.5` must not be quoted**: the report process is bursty, not
Poisson (147 of 3,197 gaps hold 67.8% of all gap-time), and assumption-free permutation
nulls put the honest bracket at **1e-8 to 1e-23** depending on the control's start-event
definition, with the like-for-like run-onset control at 1.8e-20.

**And the survivors' attribution is CONTESTED, not settled.** One lane read all 7 as
keyboard takeovers because the server answered each with a grant along the reported heading
(0.00 deg on 7/7) — but **the corpus base rate for that test is 92.9% within 5 deg over
n=3,018**, so 7 of 7 is expected ~59% of the time under the rival and the test does not
separate. The `|lead|` magnitude test is worse: **all 3,079 `op61` in the corpus carry
`|lead|` in [765.02, 768.00] — 100.0%** — it is a constant-magnitude direction vector and
discriminates nothing. Meanwhile 22 odometer sends fire **while a click destination is
commanded and never cancelled**, at 282.7–288.1 u/s, all 22 with no `0x0047` within 1.0 s
(nearest 1.53 s), on 3 connections; corpus-wide, 303 reports in that regime and 202 of them
moving at run speed with no nearby stop, on 5 connections. **A steady keyboard walk and a
click-walk produce the same wire signature at the same ~1.77 s cadence, and this corpus
cannot tell them apart.**

**Circularity, flagged:** `modeled_origin` produces `walk_t`, which produces the exposure,
and its own docstring asserts the silence being tested. The residual suppression is
therefore **UNVERIFIED**, not OBSERVED.

**What survives at full strength from this lane, and it is not small:**

* **`{0x003D, 0x0047}` is complete for c2s position.** Over 46 distinct c2s opcodes and
  7,028 rows, with every integer field also reinterpreted as float32, no other opcode
  carries a coordinate pair — 0 hits across the 15 other tested opcodes. The negative
  control **passed**: the same detector finds `0x003D` 3078/3079, `0x0047` 172/172, s2c
  `0x0029` 2459/7904, and is correctly low on `0x003E` (6/13, since a click point is often
  far from the player). A first pass anchored on "near the last report" **failed** its own
  control on `0x002C` and was discarded and rebuilt.
* **`0x0009` is a 5.005 s liveness heartbeat carrying no position** — 10 distinct payloads
  in 1,410 messages, 1,340 of 1,349 gaps in [4.8, 5.2] s. `0x0093`'s whole payload is one
  2-byte word, structurally too small for a coordinate pair.
* **`0x0047` is not a periodic ping.** Gap spread p10 1.535 / p50 18.021 / p90 80.047 /
  max 765.7 s, against the heartbeat control's p10 4.988 / p50 5.005 / p90 5.007 (0.4%
  spread). Its `(x,y)` equals the next `0x003D`'s reported position on **132 of 172** (86.3%
  of the 153 comparable), against a control of 22/3,026 = 0.7% for `0x003D`→`0x003D` — a
  110× enrichment, so "stopped here" is well supported. **But it is not a clean census of
  stops**: only 98 of 181 keyboard runs (54.1%) end in one, and 160 of 172 sit *inside* a
  run. Two of the originally-cited supports are dead — the consecutive-run test cannot
  discriminate (the known-periodic heartbeat scores 78.7% runs of 1) and the "preceded by
  `0x003D` 116/172" enrichment is only 1.53× over a 44.2% base rate.
* **The silent exposure is real walking time**, not a parked client: on 13 of 23 silent
  windows (50.72 of 62.95 s) the first report after the window lands nearer the 288 u/s walk
  model than the origin, including `_63805@1103.590` (8.95 s silent, d_model 0.0 u vs
  d_origin 1,936.9 u).
* **Our own cadence is inside retail's range, on the slow end** — ours 0.448/s and 69.4%
  stale, against retail's per-connection p50 1.122/s and p50 0.406 stale, with **14 of 61
  (23.0%)** retail connections slower than ours and 8 of 53 with ≥2 reports staler (max
  0.963). *(The originally-published "7 of 53" dropped 7 connections with **zero** reports —
  rate 0, slower by any reading — i.e. it excluded exactly the connections that belong in the
  numerator.)* **Our client's cadence is not the pathology; the freshness gate is.**

---

### 1p.5 The one-leg discriminator: 24 of 26, and every way that is weaker than it reads

**OBSERVED, with a CORROBORATED label rather than a bare measurement**, because one column
is a wire fact and the other is `route()` run from a dead-reckoned origin over our decode of
ArenaNet's mesh.

Hypothesis H: our mesh says a straight line from the modelled origin to the click is
walkable (`route()` returns exactly `[origin, click]`) **iff** retail echoed verbatim.

| | retail verbatim | retail part-way |
|---|---|---|
| our mesh: one leg | **13** | **2** |
| our mesh: many-leg | **0** | **11** |

Agreement **24 of 26**. Rebuilt three independent ways — a join of the two committed CLI
outputs on `(cap, conn, t)`, a from-scratch per-connection rebuild, and **a dense
`walkable()` sampler at 512 interior points that shares no code path with `route()` or
`clip()`** — all three give the identical 2×2, with 0/26 disagreements from the dense
sampler. **The arithmetic is not in dispute.** Six things about it are:

1. **H has a free parameter, and the claim that it does not is deleted.** It routes from
   `modeled_origin`, which dead-reckons at `RUN_SPEED = 288.0` u/s. Sweep: **22/26 at
   200–240, 23/26 at 277, 24/26 at 288–328, 23/26 at 400, 21/26 instantaneous.** Retail's own
   measured chain-leg band is 277–328 u/s (`routerbench.py:90-91`), so **H scores 23–24/26
   across the band its own constant is measured over**, not 24/26 outright.
2. **"Zero false negatives" bounds to 13 of the 16 known verbatim clicks** — 3 are untestable
   because maps 242, 248 and 310 have no content row. At 277 u/s one verbatim row
   (`_62994@135.655`) leaves the one-leg cell, and it leaves as a `route()` **refusal**, not a
   multi-leg path, so across 277–328 u/s the mesh never returns a multi-leg verdict on a
   verbatim click.
3. **The 13v/13p balance and its 50% baseline are manufactured by the exclusion**, which
   removed exactly **3 verbatim and 0 part-way**. The census baseline is 16/29 = 55.2%; the
   exclusion moved it to the weakest available 50.0%.
4. **The majority baseline is the wrong comparator.** A destination shuffle (keep each origin,
   permute click points within the same mesh, 200 trials) scores min 13 / **median 17** / p95
   20 / max 22, mean 17.5. The true pairing beats every trial, but **the effect is ~6.5 rows
   over the correct null, not ~11.**
5. **26 rows are not 26 trials.** 8 connections, 5 captures, **2 navmeshes**; `_62994` supplies
   **12 of 26 in a 48-second window**, and only 3 of 8 connections carry both answer kinds. A
   within-connection permutation null gives **p = 0.0009**, not the ~1e-05 that 26 independent
   trials implies. **5 of 26 rows are clicks 29–43 u from the origin** and 7 of 26 are under
   400 u (all 7 verbatim), where one-leg is trivially true; and **4 of the 13 verbatim rows get
   their verdict from `route()`'s same-trapezoid shortcut** (`pathmap.py:687`), which runs no
   walkability test at all — the dense-512 sampler clears all 4 independently, but `route()`
   alone could not have shown it.
6. **Two of the 11 part-way "many-leg agreements" are rows where OUR MESH is wrong, not rows
   where retail took a detour.** `20260807T143055/_60935 t=58.694` has origin and destination
   in **different connected components** with both endpoints on-mesh — our mesh says
   unreachable while retail answered the click; and `_52318 t=262.438` has **retail's own
   granted leg not clip-clean on our mesh**, with our route 127.8× longer than retail's chain.
   Corrected part-way column: **2 one-leg / 9 many-leg / 2 our-mesh-cannot-represent-it.**
   Folding a refusal in as "many-leg" scores a mesh disagreement as a point for H.

**The rival sweep, restated.** "No rival comes close" is **not supported**. In-sample, H
against the best fitted straight-line-distance cut is McNemar **4-vs-1 discordant, exact
two-sided p = 0.375** — 24/26 and 21/26 are not distinguishable on this corpus. Worse, **on
the 14 rows outside `_62994` a distance cut separates perfectly** (8 verbatim all ≤1,325.1 u,
6 part-way all ≥1,341.1 u, **14/14**) while H scores 12/14, both of its errors there. **The
defensible claim is transfer, not margin:** leave-one-connection-out gives **H 24/26 vs
distance 17/26** (McNemar 8-vs-1, **p = 0.039**), because distance needs a different cut per
subset (≤1,325 outside `_62994`, ≤2,737 inside) while one-leg carries across unchanged.
Other rivals, each given its best fitted threshold or a per-group majority oracle against
H's zero-to-one: modelled-origin age 15/26, last-reported-position age 15/26, distance from
the previous click 13/18 (8 undefined), map id 16/26 (3-group oracle), connection 19/26
(8-group), capture 18/26 (5-group), same-trapezoid-as-origin 17/26 — and only **4 of the 13
verbatim clicks are same-trapezoid**, so the mechanism is line-of-sight across trapezoids,
not trapezoid identity. Two named "rivals" were **vacuous**: `clip2_frac > 0.95` is H
restated (frac == 1.0 matches on 26/26, no row falls in the interval), and "origin/destination
on the mesh" scores exactly the baseline because **26 of 26 rows have both endpoints on-mesh**
— which also means the one `route()` refusal is a genuine no-path.

**The informative core, and it has no power in either direction.** Restricted to rows where
the origin model is inside its validated regime (age ≤2 s), the two classes overlap in
distance (d ≥1,276.4 u), and our mesh is not demonstrably broken: **n = 6 (2v/4p), H agrees
4/6 — exactly the 4/6 majority baseline.** Intermediate cuts: age ≤2 s alone, n=12, 10/12 vs
7/12; d ≥1,276.4 u alone, n=19, **17/19 vs 13/19** with verbatim still 6/6, and there is a
4,911 u click retail echoed verbatim against a 1,276 u click it answered part-way, so the
result is not an artifact of trivially short clicks.

**The straight-line clip is not a second instrument. REFUTED as corroboration.**
`pathmap._sightline`'s docstring states its sample set is exactly `clip()`'s — "the same n,
the same f = k/n" — and the bodies agree (`clip` at `:539-559`, `_sightline` at `:851-871`,
both `n = max(1, int(dist/step))`), and `_string_pull` asks `_sightline(origin, dest)` first.
So **`n_wp == 1` ⟺ `clip(origin, dest, step=16) == dest` is a theorem on the string-pull
branch**, verified over 3,000 random on-mesh pairs with 0 breaks. The "26/26 agreement" is a
**consistency check**, not a measurement, and the "identical cells at step 1/2/4/8/16/32/64"
robustness is **a null over zero exposure**: 0 of 26 corpus lines are blocked at 0.5 u yet
clean on the 16 u grid, only 1 of 26 contains any sub-16 u blocked run (10.0 u, and the 16 u
grid caught it), and 0 of 500 band-matched wild lines flip. The identity is **not** general:
for the plane-aware call the server actually makes (`authsrv.py:5139` passes `start_plane` and
`goal_plane`; the 26 rows were computed plane-blind), on mesh 113021 with **stacked**
destinations `route()` and `clip@16` disagree on **38 of 300 = 12.7%** (all 38 are
`route()=None` while clip reaches). The corpus has **0 of 26 stacked destinations**, so it had
zero exposure to the one regime where the instruments demonstrably differ — on the mesh
supplying 15 of the 26 rows.

**`modeled_origin`, validated for the first time — promote this, it is the most useful thing
the arc produced this pass.** Three independent held-out calibrations against reports the
function cannot see:

| conditioning | p50 error | n |
|---|---|---|
| all ages, vs a "never moved" naive of p50 502 u | **14.0 u** (better on 505/633) | 633 |
| age 0–0.5 s / 0.5–1 s / 1–2 s | 15.3 / 15.9 / 14.4 u | 511 / 323 / 183 |
| age > 2 s | **250–373 u**, p90 up to 1,301 u, max 1,795 u | **52 total** |
| age 5–10 s / ≥10 s (conditioned on model travel > 50 u) | 267.6 / **475.3 u** (max 2,972 u) | 11 / 29 |

**13 of the 26 scored rows sit above 2 s**, i.e. in the regime with 52 validation samples.
But the specific window carrying H's margin — `_62994`, 23.27 s unanchored — closes with a
held-out error of **58.9 u against a naive 6,611 u**, so the modelled origin is the better
choice exactly there. **A caveat, not a refutation**; and under the module's only other
origin (`last_pos_before`) the verbatim column is 11/13 rather than 13/13, with the two
flipping rows' candidate origins **5,700 u apart**.

---

### 1p.6 Retail's part-way waypoints are mesh boundary points — the ray-clip model is dead, but the direct refutation is n=1

**OBSERVED.** Of the 28 grants in the 13 part-way chains, 23 are router-chosen (not the
bit-exact click point) — and those 23 are only **19 distinct points**, because
`(-3039.0, -6531.0)` is granted for three clicks and `(-6941.0, -10766.0)` for three more,
all six inside connection `_62994`. **Deduplicated, on the two navmeshes we hold:**

| test | count | decoy behaviour |
|---|---|---|
| **bit-exact trapezoid CORNER** | **13 of 19** | **0 of 19 under every decoy tried**, including (1,0) and (−1,0) |
| exactly 0.0 from a trapezoid edge | 16 of 19 | degrades to 10/19 and 12/19 under (±1, 0) |
| within 0.01 u of an edge | 18 of 19 | — |
| neither | 1 of 19 | — |

**Lead with the corner form**: it is decoy-proof in both axes, whereas the edge-distance
test slides along horizontal trapezoid top/bottom edges under an x-shift. Vacuity guards
that could have failed and did: 300 random walkable points give **0** exactly-0 hits on map
146 (p50 29.8 u) and 0 on map 280 (p50 23.3 u); the 13 verbatim first grants (raw user click
points) give 0 exactly-0, p50 14.2 u; 200 random walkable *integer* points give 0 of 200
corner hits on each of maps 146, 148 and 280; the 16 verbatim first grants are 0 of 16
integer-valued. **Concentration, stated in the sentence:** **8 of the 19 distinct points come
from one 9-grant chain** (click 11, `_63805`, map 280), and it is the best-behaved specimen
(8/8 exactly-0, 7/8 corners). Drop it and n=11 with 8 exactly-0 (72.7%) and 6 corners
(54.5%). Per-mesh the direction replicates: 113021 n=7 → 6/6; 165811 n=12 → 10/7.

**CORROBORATED:** `ROUTER.md` §1's "interior waypoints are integer-valued mesh vertices" is
independently confirmed and is stronger than the doc states — **12 of 15 interior grants have
both coordinates integer-valued and are bit-exact trapezoid corners in our decode**, and the
3 misses are exactly the two exemptions the doc names. The doc claimed bit-exact *prop
outline* vertices; navmesh trapezoid corners are a different structure, so this is a second
witness, not the same one restated. *(The dedup caveat above has not been applied to this
15; treat it as an upper bound on independence.)*

**REFUTED — the origin→click ray-clip model.** But the refutation is weaker than the lane
first stated and the corrected version is worth stating precisely, because **4 of the 6
"killer" clicks received back, bit-exactly, the waypoint already in flight** (prev-grant ages
5.60 / 1.86 / 1.85 / 4.04 s), and the corpus base rate for that is **69 of 216 = 31.94%** of
consecutive player-grant pairs whose first grant is an integer router waypoint. Only
`t=122.976` and `t=146.434` got a *new* waypoint; for the other four the router's answer to
that click was never observed. Stripping the 5 re-issues corpus-wide leaves **8 genuine
part-way router answers: on-ray 3 of 8, clip reproduces 2 of 8.** **The only model-light
single-specimen refutation is `_62994 t=146.434`** — fresh origin (age 0.25 s, error scale
~16 u), perp 157.9 u, clip residual 933.5 u, requiring 291.8 u of origin error to rescue.
`t=122.976` needs only 240.4 u against a measured p50 dead-reckoning error of 267.6 u at its
7.49 s origin age. And the logic "a clip's answer is a function of the ray, these rays differ
and the answer does not move" is **invalid as stated** — non-injectivity does not refute
functionhood; clip-then-snap-to-nearest-corner *is* a ray-function that could have been
constant, and it was tested and failed (snaps land 109.4–960.8 u away), so the clip stays
dead but by the perpendicular-offset arm, which is not independent of it.

**The geometry, with its error bar.** Perpendicular offset of retail's first part-way
waypoint from the origin→click ray, n=13 (9 distinct waypoints, 5 connections, 3 captures):
min 0.0 / p25 7.3 / **p50 71.6** / p75 139.8 / max 328.3 u (modelled origin); p50 123.3 /
max 529.1 (reported origin). **3 of 13 within 5 u is the origin-robust count**; "within 10 u"
is 4 of 13 modelled or 3 of 13 reported. **Median |modelled − reported| origin is 600.7 u
(max 5,192.1 u) against a median effect of 71.6 u**, and 7 of 13 rows move by >10 u between
the two. **On the 6 rows where the answer does not depend on the origin choice, the split is
3 on-ray / 3 off-ray.** Deduplicated to 9 distinct waypoints: p25 1.3 / p50 49.7 / p75 101.7,
4 of 9 within 10 u. **Scale matters and was missing:** median perp is **2.02% of the ray
length** and **2.44 deg of bearing**; 12 of 13 are within 5.3% and 8.7 deg. Against a
random-walkable null at the same along-fraction band, retail's waypoint sits at the **1.0th
percentile** at the median and 13 of 13 at or below the 10th. **"Off the ray" is true relative
to the clip model's prediction of exactly zero, never relative to the mesh.**

The stated control — "the 16 verbatim clicks give |perp| = 0.0, so the measure is calibrated"
— **cannot fail and must be deleted**: all 16 verbatim first grants are bit-exact equal to the
click point, which is the ray's own endpoint, so their perp is 0 for *any* origin (verified by
substituting (0,0), (1e6, −1e6) and (−33333, 77777): max |perp| = 0.0 in all three).

**Where retail's waypoint *is* on the ray, our clip reproduces it — 3 of 13, from three
different connections**, residuals 1.1 / 1.5 / 16.5 u at step 2.0, along-fractions 0.950 vs
0.950, 0.064 vs 0.065, 0.420 vs 0.432. **On-ray is necessary but not sufficient:** two more
on-ray rows have `clip_along = 1.000` against retail stops 922.3 u and 726.4 u short.

**The two exceptions to H, named:**

* **`_63805 t=1233.471`, map 280 — RECONSTRUCTION, explained.** Retail's grant is collinear
  with our line (1.3 u lateral, 59.6% along): a truncation, not a detour. Our line's ring
  clearance drops to ≤24 u at exactly **2 of 133 interior samples**, at f = 0.592 and 0.599 —
  and retail's grant sits at f = 0.596, between them. Our zero-width clip walks a ~24 u gap a
  solver moving a body would refuse.
* **`_61106 t=67.787`, map 280 — NOT FOUND, unexplained, n=1.** Retail's first grant is
  **101.7 u laterally off our straight line at 51.7% along** — a real detour — over a corridor
  our mesh reports at the probe's **full 96 u ring clearance for its whole interior** (n=86
  samples). Our mesh has nothing there to route around, and the chain ran to a bit-exact
  terminal over 3 grants, so this is retail's considered answer, not an interruption.
  Candidates, none tested: an obstacle absent from our pathing decode on map 280, a dynamic
  agent, or a solver emitting from a coarser graph than the one it validates against.

**REFUTED by the lane against its own hypothesis:** a radius-aware corridor gate does **not**
improve the discriminator, despite explaining exception 1's location. Swept r = 0, 8, 12, 16,
24, 32, 48 u with and without a 64 u endpoint trim: nothing beats 24/26. r = 8–24 blocks a
click retail answered **verbatim** (`_64103 t=268.097`, d = 384.5 u, interior clearance 16 u)
while still passing both exceptions — strictly worse at 23/26; r = 32/48 fixes exception 1 and
still blocks that same verbatim click, a one-for-one trade. **Zero radius stays the best gate
on this corpus.**

---

### 1p.7 Retail's grant density to the player, and what the gap actually is

**OBSERVED.** Retail grants the player's **own** agent at pooled **3.19 per 1,000 u of granted
path** (29 rows: min 2.17, p10 2.39, p50 3.22, p90 4.08, max 4.31). Our shipped **1.40**
(§1i.4: 51 grants chaining to 36,387 u) is **below even the player-specific floor**. The
hypothesis that retail barely grants the player either — which would have aimed this whole arc
at the wrong mechanism — is **REFUTED**.

**The warrant is filter-independence, not a reproduction.** The published claim that
`min_n >= 18` "reproduces the committed 118-agent figure exactly, so the comparison is
like-for-like by construction" is **REFUTED and must not be repeated**: `min_n` is a free
parameter fitted to one target on a flat surface (`max = 21.79` holds for 34 of 38 swept
values), **no integer `min_n` yields 118** (17→128, 18→121, 19→120, 20→116), the stated excuse
"the corpus grew" is false (the committing commit is 2026-08-27; the newest live capture is
**2026-08-24**), the reported p10 2.48 is a **miss** against the committed 2.47, and the
original committed row's "**3.1 M u of path**" exceeds the entire corpus's unfiltered ceiling
of **2,940,424 u**. §1i.4's construction is not recoverable from its prose. **The conclusion
does not need it:** the player minimum is **2.169 at every cut including no cut at all**, and
**0 of 54 unfiltered player rows sit at or below 1.40.**

**Scope and error bars, both of which the headline lacked.** The 29 rows come from **13
sessions, 11 maps, 3 client-build eras, 1 account**; one session supplies 43.3% of the pooled
grants and one map 53.7% of the pooled path. Per-era pooled is **2.77 / 3.37 / 2.74** with 19
of 29 rows in the middle era, so **the honest cross-era figure is ~2.7–3.4, not a point 3.19**.
And **our 1.40 is n=1 with no error bar** — Poisson on 51 counts alone is ±14%, so even +3σ
≈ 2.0, still below the 2.17 floor and below the lowest-era pooled 2.74, but the asymmetry
belongs in the sentence.

**The legible form, because "per 1,000 u of granted path" is self-referential:** the rate is
identically `1000 / (mean distance between consecutive grant destinations)`. **Retail's mean
player grant step is ~313 u. Ours is ~714 u.**

**The stronger, matched result the pooled comparison misses:** in the 12 connections carrying a
player row plus ≥3 NPC rows, the player is granted **less** densely than its own connection's
NPC median in **11 of 12** (sign test p = 3.2e-03) and less densely than **every** NPC in its
instance in 8 of 12. Player cross-connection log-rate sd is 0.197 against an NPC
*within*-connection log sd of 0.497 — the player's cadence looks regulated; the NPCs' does not.

**Selection audit, passed:** all 7 excluded connections (5 with no `0x0022`, 2 with zero player
grants) show **zero** c2s player movement of every kind — 0 heading, 0 click, 0 interact, 0
rotate, 1 stop in total. **There is no connection in the corpus where the player walked and was
not granted.** And `min_n >= 18` is conservative, not favourable: the 25 rows it drops have min
2.87 and p50 4.22.

**So the gap is cadence and latency on the heading arm, not a missing message type.** 92.6% of
retail's player grants answer a `0x003D` heading report at a **36 ms median**, and 88.0% of
them (3,230 of 3,672) land inside a keyboard walk at 1.895 grants/s over 1,704.8 s of
report-covered exposure, on 42 of 42 connections with ≥5 s of exposure. **We already send
`0x0029`.** *(The lane's first exposure construction required heading walks to close and
censored 34 of 56 connections while they still carried grants — deleting 1,070.4 s and 845
grants, 23% of the numerator, i.e. exactly the long walks. Three constructions are reported;
the conclusion holds on all three.)*

**REFUTED — a correction to the record that reaches outside this arc.** **s2c `op409` (`0x0199`)
field 1 is the PLAYER NUMBER, not the player's agent id.** Three independent witnesses of the
controlled agent — `op34` (`0x0022`) f1, `op89 PLAYER_CREATE` f2, and `routerbench.player_agent`'s
`op61` heading vote — agree 56/56, 53/53 and 53/53 with each other, while `op409` f1 agrees with
each on **0 of 56 / 0 of 56 / 0 of 53**. Positive evidence with its vacuity guard: `op409` f1
keys exactly one `PLAYER_CREATE` row on 56 of 57 connections, against 15.4% for a random agent
id from the same connection. This corroborates `studies/divergence/FINDINGS.md` D7 (n=4) at
**n=56 connections / 35 distinct (map, agent) instances**. Two independent adversarial passes
confirmed it, one using the **bit-exact click echo** — a witness with no free parameter — which
names `op34` f1 on 10 of 10 and `op409` f1 on 0 of 10. `routerbench.player_agent()` itself is
correct; its module docstring's gloss of `[409, 1, 146, ...]` is not, and the R1 brief inherited
the error.

---

### 1p.8 What this changes about §1o, and what it does not

**§1o's conclusion SURVIVES, and it is now corroborated from ArenaNet's side rather than
inferred from ours.**

§1o.4 said: *"The residual is mesh AGREEMENT, not mesh correctness … the only grant the client
cannot disagree with is the destination it chose itself."* Retail's own behaviour is that
statement from the other end: **retail's part-way answers are bit-exact points on ArenaNet's
navmesh** — 13 of 19 distinct router-chosen grants are bit-exact trapezoid corners in our decode
of the same archive, 18 of 19 within 0.01 u of an edge. Retail grants exactly the points the
client's own solver already agrees with, because it *is* the client's mesh. **Our route's first
waypoint is never one of them: 0 of 11 routable part-way rows, missing by 290.4–2,351.3 u** —
while retail's own granted legs are clip-clean on our mesh for 12 of 13. That is §1o.2's "our
route is not the CLIENT'S route" measured, not argued.

**REFRAMED, and this is the sentence that should carry forward: the echo's win is that it is
the subset of retail's contract we can reproduce bit-exactly.** Retail echoes the click point
on **19 of 32 clicks (16 of 29 attributed)**, the majority class. On **13 of 13** scorable
verbatim clicks our own mesh independently says one leg suffices, so on that class the echo is
retail's answer and we match **bit-for-bit, 13 of 13**. On the other class we match **0 of 11**,
and no policy this arc has built reproduces it at all. `--click-echo` is not a heuristic that
happened to win; it is retail's answer for the majority class, adopted for the right reason.

**§1o.3's repeated-first-leg pathology is now explained offline, and it is NOT generic to
recomputation.** Replaying the router arm's own 8 logged `(origin, dest)` pairs from
`authsrv-20260827T231722-c1.jsonl` through both policies on identical inputs: the router produced
**4 distinct points, max repeat 4, and 1 pointing away from the click (cos = −0.906)**; the
clip-gated echo produced **8 distinct points, max repeat 1, 0 backwards (all cos = +1.000)**. The
mechanism is that A*'s answer space is the mesh's discrete corner set, so many origins in one
region map to one corner, while `clip()`'s answer space is the continuous ray and is monotone
toward the click, guarded by `moved > COLLISION_STEP` (`authsrv.py:5189-5191`). **RECONSTRUCTION
limit:** under the clip policy the origins would themselves differ, and **1 of the 8 clip answers
moves 0.0 u** and would be a refusal, not a grant.

**What this does NOT settle.** §1o's "NOT DETERMINED: whether anything short of matching
ArenaNet's own navmesh closes the remaining gap" is **still NOT DETERMINED, and R1 could never
have settled it** — retail's chains come off the client's own mesh by construction, so measuring
them bounds nothing about ours. What R1 *did* produce toward it is three named coordinates where
our decode disagrees with what ArenaNet's server actually did (§1p.10 item 7), which is a
cheaper entry to R4 than a fresh differential.

**And the case for building a one-leg gate is NOT made.** Measured over the same 26 rows:

| policy compared to retail | unconditional echo | one-leg-gated |
|---|---|---|
| grant **bit-exactly equal** to retail's first grant | 13 / 26 | **13 / 26 — the gate buys nothing** |
| emits the same **kind** of answer retail emitted | 13 / 26 | 24 / 26 |
| emits a grant whose straight line **leaves our mesh** | 11 / 26 | 0 / 26 (+1 where `route()` refuses) |

The gate's only measured win is the third row — and **both available else-branches are
already-measured-worse arms**: routing is `--router` (2,127 u largest displacement) and refusing
is the shipped default (5,970 u), against the echo alone's 446 u. A gate whose false branch is a
refuted policy is not an improvement; it is a refuted policy with extra steps.

---

### 1p.9 The lanes and sub-lanes that came back underpowered or vacuous — printed as results

A lane that could not measure its question is a result. Six of them:

1. **"Zero position reports in a click-walk"** — the instrument's maximum possible reading was 0
   (§1p.4). Two lanes, independently, same defect. Exposure 70.07 s and 70.34 s, both vacuous;
   the honest windows are 77.44 s (7 rows) and 82.22 s (25 rows).
2. **"Identical clip verdicts at step 1/2/4/8/16/32/64"** — a null over **zero exposure**. 0 of
   26 corpus lines are blocked at 0.5 u yet clean on the 16 u grid; 0 of 500 band-matched wild
   lines flip. It could not have come out any other way.
3. **"The straight-line clip is an independent second instrument"** — 26/26 agreement is a
   theorem on the string-pull branch, and the divergence class fires 0/300 per mesh in the
   corpus's own regime. Two instruments agreeing here is **one instrument counted twice** — the
   same defect this repo names for OpenTyria and `schema/messages.json`.
4. **The perp control (16 verbatim clicks at |perp| = 0.0)** — cannot fail; verified by
   substituting three absurd origins.
5. **"On-mesh origin / destination discriminates"** — vacuous: 26 of 26 rows have both endpoints
   on the mesh, so the test never varies.
6. **The informative core of H** — n=6 (2v/4p), H 4/6, majority baseline 4/6. **The headline
   separation is not established there in either direction.** That is the honest statement of how
   much of the 24/26 is carried by rows with a fresh origin, overlapping distance and a sound mesh.

Also underpowered rather than negative: **the cadence clause** (5 multi-grant chains corpus-wide,
7 of 10 origin-free legs from one specimen, 1 contested counterexample); **the re-click question**
(all 5 re-click specimens are also long-range, 922–4,243 u, so re-click and distance are perfectly
confounded and only new capture separates them); and **`0x002A` field 5**, which is
in-agent-universe on 0.772 of 464 rows and is an uncatalogued **second agent id** on an opcode that
addresses the player 215 of 464 times.

**And a documentary correction that a cold reader will otherwise trip on:** `authsrv.py:5105-5107`
and `ROUTER.md` §4 rule 1 both cite `REALFIX` §0.15 for a claim §0.15 does not make. §0.15 says
"**keyboard-occupied — the older click DROPPED OUTRIGHT**", which is about the older click of a
rapid *pair*. §0.14's V-RETAIL-2 says the opposite for single mid-keyboard clicks: of 7, only the
two SHORT ones (72/149 u) were echoed verbatim immediately and **all four distant ones (1,387–6,919 u)
got PART-WAY points**. The shipped comment generalises the pair rule into a single-click rule.

---

### 1p.10 What this makes worth doing next, ranked

Every candidate in this arc that asserted **more** about where the player should go did worse
(`--client-endpoint`, `--router`, K3). The first two items below assert **less** — they each delete
a refusal — which is why they rank above anything that adds a policy.

**1. Stop dropping clicks under keyboard authority. — BUILT 2026-08-28 as
`--answer-kbd-click` (MOVECODE-R1-B1), OFF by default, UNRUN.**
**7 of 32 live clicks (21.9%)** arrive with the latch our Rule 1 arms on (an `op61` with
`movementType != 0` within `GRANT_LOCAL_WINDOW = 3.0 s`, no intervening `0x0047`) and **retail
answered every one within one RTT**, with answers **635–2,445 u from any D1 lead prediction**, so
they are click answers and not lead refreshes. 14 of 32 were within the window; 6 dropped because a
`0x0047` had cleared the latch; 1 dropped as ambiguous (answer 34.7 u from the D1 prediction); 7
survive both confounds. *Vacuity note: the `movementType != 0` filter passes every `op61` in the
corpus — distribution `{1:2033, 3:494, 2:373, 8:49, 4:51, 7:42, 5:19, 6:18}`, no zeros — so the
discriminating work is done by the two confound checks, not the predicate. It is nonetheless the
server's own predicate (`moving = values[4]`, `authsrv.py:15426`), which is what makes the
comparison legitimate.*
**Predicted failure mode:** a click answered under a live keyboard authority races the lead
refreshes and the client briefly sees two authorities — §0.15's *actual* contract (drop the
**older** click of a rapid pair) is the guard that must stay, and removing that too would be the
"assert more" error in reverse.
**Refuted by:** a run reporting warps on single clicks that arrive mid-key, or larger displacements
on the answered mid-keyboard clicks than the current build's dropped ones show.

**AS BUILT.** `_grant_verdict`'s rule 1 stops refusing and the click falls through to **rule 2**,
which still holds-and-coalesces — that is the pair contract §0.15 actually states and it deliberately
stays. The reason string stays `"grant"` rather than gaining a value: `grantsim.py:2000` filters
`w[2] == "grant"` and `policyreplay.py:267` switches on `"locally-moving"`, so a new enum would have
silently shrunk two scorers instead of erroring. The turnaround is still exactly countable, because
**GRANTED with a non-null `keyboard_age` inside the window is unreachable with the flag off** — and
that pair is the registered exposure floor (≥ 3 such rows). Checks live beside rule 1's own in
`test_position_trust.py`; the mutation that deletes rule 2 as well was run and reddens exactly the
one check written for it.

**2. Delete the 1.0 s freshness gate on the echo path. — BUILT 2026-08-28 as
`--echo-any-refusal` (MOVECODE-R1-B2), OFF by default, UNRUN.**
Retail answered **22 of 32** clicks with a report older than 1.0 s, **13 of 32** older than 10 s
(max 20.99 s), and **5 of 32** with no client position ever reported, all within 0.065 s.
`authsrv.py:16583`'s `fresh = … <= 1.0` models a precondition retail does not have. The decisive
point is structural: **a bit-exact echo of the click point needs no origin at all**, which is
exactly why the echo is the arm that can be ungated by freshness.
**Predicted failure mode:** none for the echo, which asserts nothing about the origin — but the gate
is genuinely load-bearing for any origin-dependent path, because `modeled_origin`'s held-out error
is p50 ~15 u below 2 s and **250–475 u above it on only 52 samples**. Ungate the echo, keep the gate
on everything that computes.
**Refuted by:** an echo-only run where displacements *rise* once the geo-stale refusals stop — i.e.
the refusals were suppressing a harm rather than causing one.

**AS BUILT, and it crosses §1m.3's scoping on purpose.** The gate becomes
`bool(CLICK_ECHO) and (ECHO_ANY_REFUSAL or not fresh)`, so the echo answers `geo-unplaced` and
`geo-blocked` as well as `geo-stale`. §1m.3 refused geometry deliberately; **§1p.11 is what makes
the crossing arguable rather than reckless** — 7 of K2's own 8 echoed clicks *already* granted a
line our mesh calls blocked, so the flag does not open a new harm class, it stops pretending the
class is closed. `fresh` still gates every path that COMPUTES from the position belief, which is the
job it can actually do (`modeled_origin` p50 ~15 u under 2 s, 250–475 u over it). The flag
**requires `--click-echo` and raises without it** — it is one term inside `CLICK_ECHO and (...)`, so
alone it is inert, and a run launched on it would file a capture of the *shipped* policy under this
arm's name. Exposure floor: ≥ 3 `click_verdict` rows with `echo_any_refusal: true` **and a reason
other than `geo-stale`** — the flag alone would not separate them from K2's staleness arm.
**Its expected cost is MORE no-clip, which no displacement counter can see (§1n.2), so the operator's
report is the instrument and that outcome is pre-registered as its own row rather than as a
refutation.**

**3. Do NOT build the one-leg gate yet. — DESK, already measured; this item is a decision, not work.**
It buys **0** additional bit-exact matches (13/26 either way), and its only win is stopping a grant
whose straight line leaves our mesh in **11 of 26** cases — into an else-branch that is either
`--router` (2,127 u) or refusal (5,970 u). Its discriminator is also weaker than 24/26 reads: the
correct null is **17.5/26**, the informative core is **n=6 at 4/6 = baseline**, and on the 14 rows
outside one connection a fitted distance cut beats it **14/14 to 12/14**. It also needs the 288 u/s
dead-reckoned origin on 13 of 26 rows.
**What would make it worth building:** a third else-branch that asserts nothing — echo anyway and
let the client's own solver route — measured against the echo alone; or n raised past 26 by item 4.

**4. Add content rows with `file_id` for maps 242, 248 and 310. — DESK.**
It moves **3 known-verbatim clicks** into the scorable matrix (the current 13v/13p balance was
manufactured by their exclusion, which removed 3 verbatim and 0 part-way), and lifts the corpus from
**2 navmeshes to up to 5** — the single largest scope limit on everything in §1p. It is a check that
**can fail**: all 3 are verbatim, so a many-leg verdict on any of them is H's first false negative.
**Refuted by:** those maps having no pathing file, which is the only way it returns nothing.

**5. Census `0x0025 AGENT_MOVE_DIRECTION` against `0x0029` on the existing cache. — DESK, cheap.**
**2,595 of 4,473 `0x0025` rows (58.0%) address the player** — the highest player share of any
movement opcode, above `0x0029`'s 33.7% — and `studies/movement/FINDINGS.md` already records that our
server sends `0x0025` at 32.2/min (4.7× our grant rate) and that including it made a residual 11×
worse. **Nobody has computed retail's `0x0025`:`0x0029` pairing per report.**
**Predicted failure mode of acting on it:** sending more `0x0025` is an "assert more" move and the
prior on it is bad; the census is worth doing precisely to find out whether the pairing is a *rate*
we are getting wrong or a *primitive* we are misusing.
**Refuted by:** the two not being paired per report, in which case `0x0025` is not part of the click
contract and the residual lives elsewhere.

**6. Settle the report-during-click-walk question with a window that CAN return non-zero. — DESK
first; ONE RUN only if the desk answer stays contested.**
Re-run the exposure census with a command-only terminator, a pre-registered exposure floor, and the
odometer null (1.96 sends per 1,000 u, not 5.997); score the 3–4 surviving windows against a
discriminator that actually separates. **What is NOT a discriminator:** the `|lead|` magnitude test
(100.0% of 3,079 `op61` carry `|lead|` in [765.02, 768.00]) and the answer-along-heading test (corpus
base rate 92.9% within 5 deg, so 7 of 7 is p ≈ 0.59). A candidate that could work: `0x003D` field 5
`movementType`, which takes values 1–8 and is undecoded here. Also fix `REALFIX` §0.18,
`routerbench.py:180-182` and the comment at `authsrv.py:5044`, all of which state the silence as
absolute.
**Refuted by:** finding a `movementType` value that partitions the click-outstanding regime cleanly,
which would settle it at a desk; failing that, the question is worth one targeted capture of 3–5
minutes of pure click-walking, which would raise K from 27 to hundreds.

**7. Characterise the three named mesh-disagreement specimens. — DESK to characterise, LONG ROAD to fix.**
`_60935 t=58.694` (origin and destination in **different connected components** on our mesh, both
endpoints on-mesh, retail answered the click), `_52318 t=262.438` (retail's own granted leg **not
clip-clean** on our mesh, our route 127.8× longer), and `_61106 t=67.787` (retail detoured **101.7 u**
over a corridor our mesh calls fully clear at 96 u for its whole interior). These are three named
coordinates on two maps where our decode of ArenaNet's own pathing chunk disagrees with what
ArenaNet's server actually did — R4's cheapest entry, and much cheaper than a fresh differential.
**Refuted by:** a decode bug in `pathmap` for those regions, which is the first thing to look for and
far cheaper than concluding the mesh is wrong.

**Two loose ends worth recording rather than ranking.** (a) The 3 clicks on
`20260817T183323/_49545` are invisible to every committed instrument because
`routerbench.player_agent()`'s `op61` heading vote returns an empty `Counter` there — but **s2c
`op32` field 5 (spawn position) agrees with the connection's first `op61` on 51 of 53 attributable
connections** and would have let the exposure census score all 32 clicks instead of dropping 5. A
click-echo attribution fallback also works, but **must never be applied to `ours` captures**: a
verbatim echo is precisely what the arm under test produces. (b) The two `0x002C` rows on `_52294`
share a timestamp (`t=363.324`, points 68.6 u apart, both ~5,300 u from the same stale report). Two
repositions of one agent in one frame is either a decode artifact or a real double-write, and n=1
cannot say which — worth one look at the raw frame before anyone cites it.

---

### 1p.11 OUR OWN K2 RUN, re-scored against that contract — the echo's grants are almost never walkable, and the log says they all were

**OBSERVED, 2026-08-28**, at a desk, from artifacts that already existed: the K2 arm's
server log (`vault/captures/gamesrv/authsrv-20260827T230405-c1.jsonl`, 2,784 rows) and its
matching client-side capture (`vault/research/movecode/k2/movehook.bin`, 1,058 records,
both controls FIRED). No run. Script kept at `scratchpad/replay_syncgate.py` in the
session that produced it; the numbers below are what matter and are reproducible from the
two artifacts named.

Sections §1n–§1o scored K2 on **displacement**, which is the right headline and is blind
to the no-clip by construction (§1n.2). This scores the other quantity: **were the lines
we granted walkable at all?**

The sync model is seeded at the map-280 spawn `(−6036, −2519)` — `authsrv.py:14475`, the
one instant the two copies are known to be in the same place because we put them there —
then advanced by each grant decoded from its own `sent` row's wire bytes, and clipped with
`pathmap.clip(step=COLLISION_STEP=16.0)` on file `0x287B3`.

| # | t | sync origin | clicked dest | straight | clip falls short |
|---|---|---|---|---|---|
| 1 | 10.99 | (−6036, −2519) | (−3407, −1865) | 2,709 | **1,347** |
| 2 | 22.35 | (−3407, −1865) | (−2298, 2199) | 4,213 | **449** |
| 3 | 40.60 | (−2298, 2199) | (−3928, −360) | 3,034 | **3,034** (no progress) |
| 4 | 53.78 | (−3928, −360) | (−6060, −403) | 2,132 | 0 — clear |
| 5 | 62.06 | (−5433, 21) | (−9026, 4465) | 5,714 | **4,322** |
| 6 | 72.28 | (−6708, 2127) | (−3209, 6793) | 5,832 | **3,749** |
| 7 | 87.28 | (−5491, 4411) | (−5709, 7063) | 2,661 | **2,261** |
| 8 | 89.88 | (−5553, 5157) | (−5686, 7808) | 2,654 | **2,380** |

**1 of 8 clear, 7 of 8 blocked**, median shortfall ~2,300 u. The no-clip is not an
occasional artifact of the echo; on this run it is what the echo did almost every time.

**Controls, because a sync model that silently fails closed reads exactly like a clean
result.** Seed returns at t=0; **13 of 13** legs park within 0.5 u of their granted point
once their travel time has elapsed; mesh selection scores map 280 at coverage **1.00**
over the 18 client-reported positions against a runner-up of 0.78 (and 146/148 at 0.33
each, so the known shared-pathing-file tie is nowhere near the top); **16 of 18** granted
points place on the mesh. *A first draft of this replay omitted the spawn seed, so
`_sync_position` returned `None` for all 8 clicks and the script confidently reported the
opposite conclusion. The controls above exist because of that.*

**AND THE LOG CALLS ALL EIGHT "clear line".** `authsrv.py:16910` builds the click answer's
label as

```python
f"AGENT_MOVE_TO_POINT({dest[0]:.0f},{dest[1]:.0f}"
f" on plane {cur_plane}->{dest_plane}, clear line)"
```

— `clear line` is a **string literal**. Nothing computes it. It rides the click-answer send
path, which under `CLICK_ECHO` is reached exactly when `not fresh`, i.e. exactly when the
geometry check above it (`if fresh and placed: … pm_c.clip(...)`, `authsrv.py:16635`) has
been **skipped**. So the label asserts a property in the one state where the property was
never evaluated, and 7 of the 8 it asserted it for were false. This is "a check that
cannot fail is not a check" one layer out: a **label** that cannot be false, sitting in the
artifact a later session audits. It should be computed, or it should say
`geometry not evaluated`.

**A verbatim echo can also park the authoritative copy OFF the mesh, and it cascades.**
Click 2's destination `(−2298, 2199)` is not contained by any trapezoid in our decode; the
echo granted it anyway; it then became click 3's origin, and click 3's clip therefore made
**zero progress** (3,034 of 3,034 u). Independently witnessed by the client itself:
`pathdiff` replays the 9 `MapFindPath` queries `movehook` captured in this same run and
returns **OFF-MESH on 3 of 9**, two of which are that very point as goal and then as start.
The client asked those queries routinely while the operator walked, so this is our decode
failing where ArenaNet's succeeded — MOVECODE-Q2, on named coordinates.

**What this does and does not license.** "Blocked" here means *our* mesh says blocked, and
our clip agrees with the client's on ~35.7% of stops on this map (`ROUTER.md` §3). So this
is a statement about our decode as much as about the world — but it is the **same mesh any
gate would use**, which makes it the right mesh for costing a gate and the wrong one for
claiming the client no-clipped. The operator's report (§1n.2) is the independent witness
that it did.

### 1p.12 A gate on this was built at a desk, measured, and REFUTED — by its own numbers and by the graveyard

**REFUTED.** The obvious move from §1p.11 is to gate the echo on a clip test taken from
`_sync_position()` — the ray the sync copy will actually walk — instead of skipping
geometry because the player's position is stale. It is **not** the withdrawn MOVECODE-K3
(route from `_sync_position`): it asserts no corridor and invents no waypoint, it only
decides whether to answer.

Pre-registered before running: 2–5 of 8 refused would be a real trade; 0 means inert (K1's
death), 8 means a full revert to the shipped refusal and its 5,970 u spawn warp.

**Measured: 7 of 8 refused** — outside the band, at the revert end. It would have fed the
sync copy on one click in eight, which is §1i's starvation returning.

And the graveyard already held it. `--heading-grant` (`authsrv.py:1200`, candidate #4)
**granted a clipped point**, and the clip is one of the two reasons its epitaph gives:

> *"it sent `clip_to_walkable(...)`, a point shortened by OUR navmesh where the client's
> own collision disagrees"* … *"the clip is dropped because the client collides for itself
> and does it better than our navmesh does."*

The variant here avoids heading-grant's *other* failure (it clips the click's own ray from
an exact model rather than an invented heading ray from `state["pos"]`), but commits that
one squarely, and §1p.6 independently kills the shape from retail's side: retail's part-way
waypoints are **bit-exact navmesh trapezoid corners**, not points on the player's ray, so a
clip stop is not the thing retail sends either.

**Three roads to the same wall, which is the finding.** §1p.8's table shows the one-leg
gate buys 0 additional bit-exact matches; this shows the clip gate degenerates to refusal
7 of 8; and the graveyard shows a clipped grant already lost once. Every server-side lever
that consults our navmesh is capped by how well it agrees with ArenaNet's, and
**`--click-echo` wins because it is the only one that never consults it.** That is §1o's
"the residual is mesh AGREEMENT" arrived at from a fourth direction.

### 1p.13 Incidental — HANDOFF §4's R2 is cheaper than it says, and one thing I got wrong

**OBSERVED.** `HANDOFF-WARP.md` §4 R2 prices "which gate fires?" at *"one content row +
one run"* and says only gate 1 has ever been confirmed. **Gate 2 needs neither.**
`movehook` already taps `MapFindPath`, and snaptest's gate-2 call is
`00605802  call 0x709e90` — so a captured query whose **return address** is `0x00605807`
is that call site having executed. Censused across all 9 movehook captures:

| capture | records | MapFindPath | gate 2 (`0x00605807`) | planner (`0x0081AF56`) |
|---|---|---|---|---|
| `k1-treatment/` | 966 | 11 | **3** | 8 |
| `k2-2/` | 503 | 13 | **2** | 11 |
| `k2/` | 1,058 | 9 | **1** | 8 |
| `run3-…-isle/` | 3,417 | 7 | **2** | 5 |
| `run5-…-v5/` | 3,246 | 20 | **1** | 19 |
| `run2-…`, `run4-…-snap` | 198 / 491 | 8 / 5 | 0 | 8 / 5 |
| `run-…-ascalon` | 2,062 | — | pre-B3, no site | — |

**9 gate-2 executions across 5 distinct captures**, of 73 queries. *(The raw sweep said 12
across 6: `vault/research/movecode/movehook.bin` and `k1-treatment/movehook.bin` are the
same file, identical MD5 `18a65c1d…`. **That top-level path is `readhook.py`'s DEFAULT
target**, so `python readhook.py` with no `--bin` silently reports on the K1 arm's
capture.)*

Flow reaches `0x00605802` only after gate 1 has passed, so **each execution is a witness to
a gate-1 pass**. This is *not* the same quantity as `PLAN.md`'s starred *"Gate 2 has n = 0
observed firings"* (line 4942), which counts which gate **decided** the 24 measured snaps
and is not contradicted here — but that line is dated **2026-08-20** and four of the five
captures holding these executions were taken on **2026-08-27**. R2's real remaining cost is
one content row for **gate 3** (`0x005FEF70`) alone.

**AND A MISTAKE, recorded because the method is the point.** Reading the tail of
`0x006055E0` I concluded the three gates were an AND rather than "any one of which snaps",
and was about to correct `PLAN.md` §3's R3 row. A skeptic tasked with refuting me did:
**the polarity is inverted — `1 = NO SNAP, 0 = SNAP`**, established from the sole caller
(`0x00606021 test eax,eax / jne 0x606110`, which returns doing nothing on nonzero and
otherwise falls through to the roster reseed at `0x006060E2 call 0x6022B0`). The three-way
AND on the *accept* path is exactly "any one gate snaps" on the *failure* path. The
mechanics I read were right and the meaning was the opposite; I had taken our own invented
name `snaptest` as evidence of direction. **The whole function was also already decoded
correctly on `main`** — [studies/movement/FINDINGS.md](../movement/FINDINGS.md) §3117–3143,
same pseudocode, same `edi` sweep, same caller-derived polarity, reproduced there by two
skeptics. I spent an agent rediscovering it because I disassembled before grepping
`studies/movement/`. Both documents stand unchanged.

---

---

## 1q. MOVECODE-R1-B1 ARM — **REFUTED on its registered clause, and by the exact mechanism its own predicted failure mode named**

**OBSERVED, 2026-08-28.** Map 280, `--click-echo --answer-kbd-click`, 1,804 records,
both controls FIRED, 97.9 s server span / 46.8 s of tracked motion. Capture
`vault/research/movecode/r1b1/`, log `authsrv-20260828T105948-c1.jsonl`. Baseline
throughout is the **K2** arm, same map and operator.

### 1q.1 The registered table

**Exposure floor MET**: 4 grants fired with the keyboard latch armed, against a floor
of 3. Zero `locally-moving` refusals in the whole run, which is the flag's negative
control — that reason is unreachable while it is on.

| §1p.10 quantity | K2 | B1 | predicted | |
|---|---|---|---|---|
| grants fired with the latch armed | 0 (unreachable) | **4** | ≥ 3 | ✅ floor met |
| clicks answered | 8 | 4 | rises | ❌ **fell** |
| **largest displacement** | **446 u** | **537 u** | **≤ 446 u** | ❌ **REFUTED** |
| displacements within 300 u of spawn | 0 | **0** | 0 | ✅ |

**REFUTED.** The registered clause was *"refuted if the largest displacement exceeds
446 u"*, and it is 537 u. The three displacements are **537, 527 and 321 u**, total
1,385 u against K2's 1,101 u.

**And the walk was SHORTER, which strengthens rather than weakens it**: the local copy
walked **9,734 u over 46.8 s** against K2's 18,577 u over 88.1 s. B1 produced a larger
maximum displacement in **half** the path.

The spawn clause passes cleanly — closest approach **2,403 u**, and the three landings
are at `(−5881, −121)`, `(−6079, 2537)` and `(−7365, 4147)`. Nothing went back to
`(−6036, −2519)`. **This is not a regression to arm A's failure**; it is a different,
smaller one that the arc's own scoring number nonetheless refuses.

### 1q.2 The attribution, on a CHECKED clock pairing

The two clocks are different, so they were aligned the way §1i.3 aligned them — by the
grant pairing, and **the pairing is tested rather than assumed**: the server sent
**30** `0x0029` and the sync copy took **exactly 30** setter calls, and the 29
inter-event **gap sequences** agree at **p50 4 ms, max 16 ms** with an offset spread of
**0.021 s**. Gaps need no shared origin, so this is a check that could have failed.

| server t | event | |
|---|---|---|
| 16.26 | B1 click grant `(−5979, −336)` | latch age 1.08 s |
| 23.54 | B1 click grant `(−4606, 2936)` | latch age 1.18 s |
| **25.51** | **DISPLACEMENT 537 u** | **+1.97 s** |
| 35.90 | B1 click grant `(−7712, 5964)` | latch age 1.74 s |
| **37.87** | **DISPLACEMENT 527 u** | **+1.97 s** |
| 44.61 | B1 click grant `(−8592, 4693)` | latch age 1.12 s |
| **47.65** | **DISPLACEMENT 321 u** | **+3.04 s** |

**Three of three displacements follow a B1 click grant, at +1.97, +1.97 and +3.04 s.**
Two of them at the same 1.97 s to the centisecond. The fourth B1 grant (t = 16.26) is
the one that did not warp, so it is 3 of 4 grants rather than 3 of 3 — the count that
matters is that **no displacement in this run failed to follow one.**

The operator's report is the independent witness and it agrees: *"got some warps. ended
with a W press that caused a warp."* The last displacement is the 321 u one at
t = 47.65, and a `W` press is exactly what produces the heading grant it lands beside.

**This is B1's own predicted failure mode, quoted from `authsrv.py` before the run:**

> *a click answered under a live keyboard authority races the lead refreshes and the
> client briefly sees two authorities*

That is what 1.97 s after a click grant, landing 136 u from the next heading grant's
destination, looks like on the wire.

### 1q.3 What the run does NOT separate, and it is inherent rather than sloppy

**All 4 of B1's fires were also K2 echoes of `geo-stale` clicks**, so this arm does not
separate "answering a mid-keyboard click" from "echoing a stale click while the keyboard
is authoritative". That confound cannot be walked around: the latch ages measured are
**1.08–1.74 s**, and `fresh` is `<= 1.0 s`, so a click arriving late enough to be
mid-keyboard is by construction already stale. The two conditions overlap by
arithmetic, not by accident.

The consequence for the reading is real: **B1's action set was a subset of K2's echo
set in this run**, and what B1 changed was only whether those 4 echoes survived rule 1.
Without the flag all four would have died as `locally-moving` and this run would have
answered **zero** clicks.

**Which is why "clicks answered fell from 8 to 4" is not the regression it looks like.**
It is a different walk: the operator was told to click while holding a key, so the run
contains fewer pure click-walk legs than K2's did. The two arms are not comparable on
that row and it should not be quoted as one.

### 1q.4 The other six clicks, and the exposure B2 now has for free

Six clicks were refused `geo-blocked` (t = 26.72 → 41.55), clustered in the north-east
at y ≈ 4,400–5,300 — the region §1i.5 and §1h.4 both name. Those are exactly the set
`--echo-any-refusal` (R1-B2) exists to answer, and **6 ≥ its registered floor of 3**, so
that arm's exposure is reachable on this operator's own walking pattern without any
special instruction.

### 1q.5 Status

* **`--answer-kbd-click` is REFUTED and stays OFF.** It is kept in the tree with its
  numbers, like the seven before it.
* **The eighth candidate, and the pattern holds with one correction.** §1o said every
  candidate asserting *more* about where the player should go does worse. B1 asserts
  nothing about *where* — it only removes a refusal — and it still lost. The sharper
  statement is that **every candidate that puts a grant on the wire while the client
  already has an authority does worse**, which is a claim about *when* rather than
  *where*, and rule 1 was right for a reason its own comment got wrong.
* **`--click-echo` alone remains the best measured configuration** at 446 u.
* **NOT DETERMINED:** whether B1 would refute on a walk where the mid-keyboard click is
  *fresh* — which needs a report inside 1.0 s of the click, i.e. a click within a second
  of a key edge. No such click occurred here and the arm cannot be scored on it.

---

---

## 1r. MOVECODE-R1-B2 ARM — **REFUTED on its registered clause, and it is the first arm in this family where the two ways of scoring a warp DISAGREE**

**OBSERVED, 2026-08-28.** Map 280, `--click-echo --echo-any-refusal`, 3,375 records,
both controls FIRED, 205.8 s server span. Capture `vault/research/movecode/r1b2/`, log
`authsrv-20260828T113351-c1.jsonl`. Baseline is **K2**, same map and operator.

### 1r.1 The exposure is MET and, unlike B1's, it is CLEAN

**8 geometry echoes against a floor of 3.** More important than the count is what the
run does *not* contain: **the single `geo-stale` click (t = 38.85) was dropped
downstream as `locally-moving`** — the operator's own reported slip, *"i messed up the
second click-to-move (didn't stop)"* — so **zero K2-staleness echoes reached the wire.**

Every one of the 46 grants this arm put up came from a **geometry** echo. That is the
confound §1q.3 could not escape, absent: B1's action set was a subset of K2's, and B2's
is disjoint from it. **This is the cleanest arm the family has produced.**

The drop was caught by the readout's own cross-check rather than by reading the log by
hand — *"an echo is a DECISION, not a grant; rule 1 runs after it"* — which is the guard
added when this runsheet was written, firing on the first run that needed it.

### 1r.2 REFUTED, and truncation does not rescue it

| quantity | K2 | B2 | predicted | |
|---|---|---|---|---|
| non-`geo-stale` echoes | 0 (unreachable) | **8** | ≥ 3 | ✅ floor met |
| **largest displacement** | **446 u** | **1,094 u** | **≤ 446 u** | ❌ **REFUTED** |
| displacements within 300 u of spawn | 0 | **0** | 0 | ✅ |

**B2 walked 2.2× further than K2** (local-copy path 26,155 u over 168.1 s against
11,777 u over 88.2 s, both measured the same way), so a larger *maximum* is partly an
extreme-value effect and quoting it raw would be the denominator trap this arc has
already paid for. **It was checked both ways and the refutation survives both:**

| matched on | B2 | K2 |
|---|---|---|
| K2's span (first 88.2 s) | n = 3, **largest 1,094 u** | n = 3, largest 446 u |
| K2's path (first 11,777 u, t ≤ 68.0 s) | n = 3, **largest 1,094 u** | n = 3, largest 446 u |

All three of B2's displacements fall inside K2's own denominators, so there is nothing
to truncate. **1,094 u against 446 u is 2.45×, on a matched walk.**

### 1r.3 The finding that cuts the OTHER way, and it is unregistered

Scored as a **rate**, B2 is the **best of the three arms** — on both normalisations:

| arm | span | local path | n | largest | total | per 1000 u | u per 1000 u |
|---|---|---|---|---|---|---|---|
| K2 | 88.2 s | 11,777 u | 3 | 446 u | 1,101 u | 0.255 | 93.5 |
| B1 | 33.7 s | 9,734 u | 3 | 537 u | 1,385 u | 0.308 | 142.2 |
| **B2** | **168.1 s** | **26,155 u** | **3** | **1,094 u** | **2,203 u** | **0.115** | **84.2** |

**B2 warps less OFTEN and harder WHEN it does** — half K2's rate per unit walked, and
2.45× its worst single event. **6 of its 8 geometry echoes produced no displacement at
all.**

**This is the first time in this arc that the two scorings disagree**, and it matters
because the choice of headline was never argued — §1o.1 picked "largest displacement" as
*"the one number that survives all three arms"*, which was a statement about
comparability, not about which harm is worse. Every arm since has happened to rank the
same way on both, so nothing forced the question. It is forced now.

**The registered clause governs and B2 is refuted by it.** Two reasons not to reach for
the rate instead, both weaker than they look and stated as such: the operator experiences
the maximum, not the mean; and n = 3 per arm is far too small for a rate to carry a
decision. **Neither is a reason to believe the rate finding is noise** — it is the same
n = 3 the refutation rests on.

### 1r.4 The mechanism, and the mesh is NOT the limiting factor

`pathdiff` replays the client's own `MapFindPath` calls through our mesh: **10 of 10
BOTH-OK, 0 OFF-MESH, 0 OURS-FAILED.** So none of this run's warps is a map-280 navmesh
hole, and MOVECODE-Q2 is not the explanation here.

What those queries *do* show is the divergence stated exactly: **the client's own solver
returned 2–5 waypoints for every click**, and we granted a **single straight line** to
the same destination. That is §1o.4's "mesh AGREEMENT, not mesh correctness" seen from
the sharpest angle yet — our mesh can answer every query, and the answer we *send* is
still not the path the client walks.

**The warp IS the reconcile closing that divergence, and the numbers coincide exactly.**
The snap tests recorded separations of **682.7 / 1,093.7 / 3,368.1 u**; the displacements
are **657.9 / 1,093.7 / 451.0 u**. `1093.7` appears in both lists to the decimal.

**And the worst one fires at ARRIVAL, which is the sharpest thing in this run.** The
1,094 u displacement began at `(594.4, −805.4)` — **293 u from the point the operator
had clicked** — and ended at `(−456.9, −1107.4)`, **1,188 u from it**. The player walked
almost the whole way to their destination and was then thrown four times that remaining
distance backwards. A 446 u nudge mid-route and a 1,094 u yank one step from the goal are
not the same defect at different sizes.

The coupling is also **loose**, unlike B1's: the gaps from each displacement to the
preceding geometry echo are **+13.78, +15.86 and +13.05 s**, against B1's +1.97/+1.97/
+3.04. B1's warps raced a competing authority; B2's accumulate over a long straight leg
until the separation crosses the cut. Different mechanisms, and the timing separates them.

### 1r.5 Status

* **`--echo-any-refusal` is REFUTED and stays OFF**, kept with its numbers as the ninth.
* **`--click-echo` alone remains the best measured configuration** at 446 u.
* **§1m.3's original scoping is VINDICATED.** It refused geometry deliberately; §1p.11
  argued the refusal was already hollow because 7 of K2's 8 echoes were blocked lines
  anyway. That argument was **sound about the wire and wrong about the outcome** —
  answering geometry refusals *knowingly* is worse than answering them *unknowingly*,
  because the set it adds is exactly the set where the straight line is longest.
* **NOT DETERMINED, and only the operator can supply it: the no-clip row.** §1p.10 item 2
  pre-registered "more no-clip" as its own outcome rather than a refutation, and **no
  metric in this file can see it** (§1n.2). The operator's report of this run does not
  mention it either way, so that row is **UNSCORED**, not zero.


### 1r.6 The no-clip row: an offline detector was BUILT, FAILED ITS POSITIVE CONTROL, and is not published as a result

**The row is UNSCORED because of a handoff defect, and the defect is worth naming
because the runsheet did not have it wrong — the handoff did.** `RUN-R1B.md` §1 states
that no-clip is pre-registered, that every metric is blind to it, and that *"the
operator's report is the instrument for this and nothing else is"*. The server also
prints it as a startup banner. What reached the operator was a **bare command**, pasted
without the runsheet's own observation step, and the answer came back
*"i didn't pay attention as it wasn't noted in the run B2 instructions."* **The
instruction existed and did not travel with the command.** An instrument that is a human
has to be briefed in the same breath as the launch, or it is not an instrument.

**Then the dependency was attacked directly, and this is the part worth keeping.** If
no-clip could be read out of the capture, no briefing would be needed. The detector walks
the LOCAL copy's sampled positions and runs each chord through `pathmap.clip()` — the
server's own geometry primitive — counting chords the mesh says are blocked. Warp steps
(stamp not advancing) are excluded, sub-1 u chords are dropped, and long chords are capped
so a sparse sample cannot manufacture a corner cut.

**It was calibrated against a control pair whose answer is already known**, which is the
only reason its failure is legible:

| arm | what it should show | steps | blocked | rate | worst |
|---|---|---|---|---|---|
| `k1-treatment` (shipped, clicks REFUSED — body is entirely client-pathed) | **clean** | 134 | 1 | **0.7%** | 73 u |
| `k2` (echo — operator REPORTED no-clip, §1n.2) | **dirty** | 158 | 1 | **0.6%** | 171 u |

**No separation.** The arm that should be clean scores *higher* than the arm the operator
watched no-clip in. Swept over chord caps 400/800/2000/6000 u and tolerances 16/32/64 u,
the rates stay ~1% in both and `n` stays at **1–2 blocked chords per arm**. **A detector
that cannot tell the control pair apart cannot score B2**, and its readings for B1 (0) and
B2 (2) are therefore reported nowhere else in this document.

**WHY it fails, and it is NOT the obvious reason.** The first hypothesis was that our mesh
is terrain-only and cannot represent a prop. **Refuted by measurement:** map 0x287B3's
mesh has **2,769 trapezoids with a median y-extent of 44.8 u, and 70.6% are under 80 u** —
prop scale. The mesh is fine enough.

The real limit is **sampling**. `movehook` fires on path-solver *events* — bake, setter,
teleport — not at a fixed interval, so a capture yields only **134–571 usable chords** for
a whole run, and the body's actual traversed path between two decision points is not
recorded. At a ~1% base rate that is **n = 1–2**, which is no power at all.

**What would work, costed rather than hand-waved:** a hook that samples the body's
position on a timer (or reads the client's own collision result) instead of at solver
entries. That is a `movehook.c` change and a `sites.h` regenerate, not a new arc — and it
would retire a row this family has now deferred to human attention **four times**.

**Until then the row is genuinely UNSCORED for B1 and B2**, it cannot be recovered from
the captures on disk, and only a re-run with the operator briefed *before* the walk can
close it. That does not change either refutation: both were refuted on displacement, which
is measured.

### 1r.7 §1r.3's RATE is DISQUALIFIED as a scoring number — it ranks the spawn-warping shipped arm above `--click-echo`

**OBSERVED, 2026-08-28, at a desk.** No client run, no new capture: every number below
comes from `readhook.py` at HEAD `7c56fb7` over the six movehook captures already in
`vault/research/movecode/`. Scored by an adversarial pass that attacked seven vectors;
the verdict was HOLDS, and **the pass found a stronger argument than the one I had
written, plus two overreaches of mine that are corrected in place below.**

**First, the arms table reproduces bit-for-bit** — 5,970 / 446 / 2,127 / 537 / 1,094 u,
matching §1o.1, §1q.1 and §1r.2 exactly, with the individual displacement lists intact
(K2: 446, 363, 292). Nothing has drifted, which is what makes the rest of this a
statement about the metric rather than about the captures.

#### The disqualifying argument, and it needs no statistics at all

§1r.3 ranked the arms on displacements per 1,000 u and called B2 "**the best of the
three arms** — on both normalisations". Extended to all six captures **on §1r.3's own
denominator**, the count rate ranks:

| rank | arm | n per 1000 u | largest displacement |
|---|---|---|---|
| 1 | `--echo-any-refusal` (B2) | 0.115 | 1,094 u |
| **2** | **shipped, refuse the click (K1 arm A)** | **0.170** | **5,970 u — warps to spawn** |
| 3 | run 5 (pre-policy) | 0.211 | 1,871 u |
| **4** | **`--click-echo` (K2, the recommendation)** | **0.255** | **446 u** |
| 5 | `--router` | 0.260 | 2,127 u |
| 6 | `--answer-kbd-click` (B1) | 0.308 | 537 u |

**The count rate ranks the shipped configuration — the one the operator watched warp
the character 5,970 u back to spawn, twice (§1l.1) — as SECOND BEST of six, above the
arm this arc recommends.** A scoring number that does that is disqualified on its face,
before any p-value.

**Precision, because §1r.3's claim was two columns and only one of them dies.** The
*magnitude* normalisation (u per 1,000 u) does **not** have this defect — it puts the
shipped arm last at 454.7, correctly. But on that surviving column B2 beats K2 by
**84.2 against 93.5, a 1.11× margin**, not the "half K2's rate" §1r.3's prose carries
over from the count column. **"Best on both normalisations" is true and misleading**:
one normalisation is disqualified, and on the other the margin is 1.11×.

#### The numerator does not move, and the rate is not distinguishable from noise

Local-copy path against displacement count, readhook's own census:

| arm | local path | n |
|---|---|---|
| B1 | 9,734 u | **3** |
| K2 | 18,577 u | **3** |
| `--router` | 26,929 u | **4** |
| shipped | 31,136 u | **3** |
| B2 | 42,526 u | **3** |

**Across a 4.37× range of walked path the count is 3, 3, 4, 3, 3.** K2 and B2 recorded
**the same three displacements each**; the whole rate difference is the denominator.

The exact conditional test for two Poisson counts (Przyborowski–Wilenski) conditions on
the total and asks how the events split between the exposures — no rate estimate, no
free parameter. K2 vs B2 gives **two-sided p = 0.377** on readhook's paths and
**0.383** on §1r.3's, and the verdict is **denominator-proof across five**: local path
0.377, sync path 0.387, span 0.388, motion-time 0.411, records 0.144. The one-sided
test — the direction §1r.3 actually claimed — is **0.263**. **No denominator in the
tree makes the pair significant.**

Over all fifteen pairwise comparisons on §1r.3's own denominator the smallest p is
**0.354**, and a Poisson goodness-of-fit across all six arms gives **χ² = 2.046,
p = 0.843**: *one common rate per unit distance fits every arm.* Cap sensitivity from
500 u to none leaves K2 vs B2 in 0.355–0.394.

**Minimum detectable outcome** (this was labelled "power" in my first draft and that
was wrong): holding B2 at 3 events, the design does not reach p ≤ 0.05 until the other
arm shows **6** — a 4.58× ratio. True **power** at the observed 2.29× ratio is **0.149**;
80% power needs R ≈ 6.2× or roughly 8–9× more walking.

**Scoped honestly:** 6 of 75 pairwise tests across all denominators do reach p ≤ 0.05,
and **all six sit on the two denominators the goodness-of-fit rejects** — sync path
(p = 0.0046) and record count (p = 0.0298). Both are instrument artifacts rather than
exposure: the shipped arm's sync path is 2,804 u *because its policy refuses to grant*,
so the arm under test sets its own denominator. Local path, span and motion time all
pass as exposures (GOF p = 0.41 / 0.46 / 0.47).

#### What this corrects, precisely

§1r.3 wrote: *"Neither is a reason to believe the rate finding is noise — it is the
same n = 3 the refutation rests on."* **That sentence does not survive.** The exact
conditional test is such a reason and was available from the same numbers.

**And my own first draft of this section overreached in the opposite direction**, saying
the rate arm of the methodology dilemma "is empty at this n" and that the alternative
"has no discriminating power". That is false as a statement about the *design*. The
corrected form, which the refutation pass supplied:

> This closes the methodology question §1r.3 flagged, and closes it without a
> preference. **Neither statistic reaches p ≤ 0.05.** The size comparison sits **at the
> design's evidential ceiling** — perfect separation (1,094, 658, 451 all exceed 446,
> 363, 292), exact permutation two-sided **p = 0.100**, the smallest value 3 v 3 can
> produce — while the count comparison landed at **p = 0.377 against an attainable
> 0.027**. The rate is not the weaker *instrument*; it is the one that found nothing
> where it could have found something. And the count rate ranks the shipped
> spawn-warping arm second of six, which disqualifies it before any p-value.

**Largest displacement therefore stays the scoring number** — not because it is the
better estimator (at n = 3 a maximum is noisy and exposure-biased; what defends it is
that it is the harm the operator actually experiences, and §1r.2 already matched B2
against K2 on both span and path and got 1,094 u either way) — but because the count
rate is disqualified and the magnitude rate's margin is 1.11×.

#### §1r.3's denominator is now identified, and the document contradicts itself about it

§1r.3's paths are readhook's chord sum **with chords over 2,000 u dropped**, and its
span column is the **tick** span where readhook prints the **ptime** span. Verified
against all three published figures: K2 **11,777**, B2 **26,155**, B1 **9,734**, every
one to within 0.5 u. **The check that could have failed did not:** B1's published figure
equals its *uncapped* sum, so the rule predicts B1 contains no chord over 2,000 u — and
its capped and uncapped sums are identical at 9,734 u, which coincidence would not
produce. Both rules are defensible; neither is written down.

**They are 118 lines apart in this file and neither says it changed.** §1q.1 reads
*"9,734 u over 46.8 s against K2's 18,577 u over 88.1 s"*; §1r.2/§1r.3 read K2
**11,777 u over 88.2 s** and B1 over **33.7 s** — the same captures, two path rules and
two span rules, unflagged. Anyone comparing a figure from §1q against one from §1r is
comparing two different quantities.

#### A hypothesis of mine this data REFUTED, kept because it was tested

I suspected the count was pinned near 3 by **sampling density** rather than by the world
— §1r.6 established that `movehook` fires on solver events rather than on a timer, which
left the no-clip detector at n = 1–2, and the displacement counter reads the same
records. **Refuted.** Displacements per 1,000 local records spread 2.39–23.81 (≈10×),
*worse* than the per-distance spread of 4.37×, and a proper goodness-of-fit **rejects
record count as an exposure** (p = 0.0298) while accepting distance, span and motion
time. *(The spread comparison alone was near-tautological — with n pinned at 3, rate
spread is denominator spread by algebra — so the GOF is what carries this, not the
ratio I first quoted.)*

My first draft concluded from that that **"what pins the count near 3 is NOT
DETERMINED"**, and that over-reads. The supported statement is the weaker and cleaner
one: **the six counts are consistent with a single common rate per unit distance across
every arm (χ² p = 0.843), and no arm-specific mechanism is required to explain them.**

#### What it changes, and it is less than it looks

**No shipped behaviour moves.** B1 and B2 were already refuted and off on largest
displacement, and `--click-echo` already stands at 446 u. This resolves a
**documentation** question, not a policy one.

**One cold-start line is actively misleading and should be corrected**:
`HANDOFF-WARP.md`'s arms table calls `--echo-any-refusal` *"REFUTED, §1r — but the best
RATE of any arm"*, which invites exactly the reach this arc has documented cold sessions
making. It should read: *"— its rate is lower, but the count rate is disqualified (it
ranks the shipped spawn-warping arm above `--click-echo`) and no arm's rate is
distinguishable from any other's, §1r.7."*

**Method note the parse itself produced.** `readhook`'s world-copy census does **not**
print the two copies in a stable order — `k2-2` and `r1b2` print the sync copy first,
`k2`, `k1-treatment` and `r1b1` print the local copy first — so anything reading them
positionally silently swaps two bodies that sit hundreds of units apart. Key on the
`WORLD_SYNC` / `other world` label. Run 5 additionally prints a **third** entry also
labelled `other world` — the `snaptest` `ecx`, which readhook flags itself as
`NOT AN AGENT` (§1h.1) — and a label-keyed parse that does not skip the disowned entry
lets it **overwrite the real local copy**, replacing a 49,378 u path with none at all.
It did exactly that here, and was caught only because the guard refused to print an
incomplete row rather than treating a missing field as a zero.

---

## 1s. THE DESK PASS OF 2026-08-28 — R3's three named candidates are DEAD on their own refuting shape, a SECOND gateless reseed route is now OBSERVED firing live, and three of the four "our mesh is wrong" specimens are not

**Desk only, 2026-08-28.** Six lanes ran offline against artifacts already on disk; each was
then attacked by an adversarial skeptic that re-ran the load-bearing steps independently.
**One lane came back REFUTED (L1), five HOLDS-WEAKENED.** No client was launched, no DLL
was built, no capture was taken. Every `codescan`/`asserts`/`msgshape`/`areatable` call in
the pass passed `--exe C:/gd/Rurik/vault/client/2026-07-29_221c13772c7a/Gw.exe`
**explicitly** (build 38797) — the `sorted()[-1]` default would have picked
`2026-08-20_21511009c460`, and the relative `vault/client/…` form the briefs quote throws
`FileNotFoundError` inside a worktree, so the absolute path is mandatory here.

**Read this before quoting any denominator below.** One lane (L3) landed
`content/maps.toml`, `toolkit/test_content.py` and `toolkit/clientscan/test_routerbench.py`
into the shared worktree while the others were running. Every "of 26 rows", "of 40/41
grants", "of 8 connections" figure in §1s.5 and §1s.7 — and every one in §1p.5 and §1p.6 —
is pinned to the **pre-change** corpus and moves when those rows land. §1s.4's own numbers
are post-change.

**The pass's shape, honestly:** two genuinely new results (§1s.1, §1s.4's forced-verdict
census), three corrections to our own record (§1s.5, §1s.7, and the retraction below), and
a large amount of re-derivation of things already committed on `main` that the arc's own
handoff does not cite. **HANDOFF-WARP.md §4's R1 already records this failure costing five
agent-lanes; R3 and R6 cost two more in this pass.** §1s.8 prints the vacuous and forced
results.

**[§1r.7](#) ran in this same pass and is filed with §1r because it corrects §1r.3, not
because it is separate work.** It disqualifies the displacement **rate** as a scoring
number — the count rate ranks the *shipped* spawn-warping arm 2nd of 6, above
`--click-echo` — and shows that no arm's rate is distinguishable from any other's
(K2 and B2 recorded the same 3 displacements each; exact test p = 0.377; one common rate
per unit distance fits all six arms at p = 0.843). **Read it before quoting any rate in
§1s**, and note that it closes the largest-vs-rate methodology question §1r.3 had flagged
for an owner view.

---

### 1s.1 A SECOND reseed route with NO gates — two lanes found it from opposite ends, and it is now OBSERVED firing

**OBSERVED, and this is the best thing in the pass.** `reseed` (`0x006022B0`) has **exactly
two** direct callers — `--xrefs` reports "2 direct rel32 reference(s), **0 word(s) holding
the VA**", so §4 item 2's virtual-dispatch caveat does not apply here and this is a census
rather than a floor. Rebasing the return addresses in the movehook corpus, pooled over **10
distinct captures, n = 53 reseed records**:

| retaddr | route | count |
|---|---|---|
| `0x006060E7` | inside `agtrack`'s **gated** snap loop, downstream of `snaptest` | **32** |
| `0x00605EF6` | inside `0x00605E40`, which calls `snaptest` **zero times** | **21** |

**21 of 53 = 39.6% of every reseed this arc has ever captured did not come through
`snaptest` at all.** The route is `ResyncAllAsync`: `0x00605E40` has exactly one inbound
reference image-wide (`0x005FCAAE jmp`) from the thunk `0x005FCAA0`
(`call 0x47f660 / mov ecx,[eax+8] / lea ecx,[ecx+0x1cc] / jmp 0x605e40`), which has 3
callers (`0x004E6E82`, `0x00816499`, `0x0081655D`); its body calls only the assert helper
and `reseed`; `snaptest` `0x006055E0` has exactly one caller image-wide (`0x0060601C`). Its
loop is instruction-for-instruction the gated one — null check, `test [eax+0x20],0x10000`,
Array:587 bounds assert, inline record clear, `cmp esi,[edi+0x14] / setne bl` for the
`i != focusId` third argument.

**CORROBORATED — this promotes `studies/movement/FINDINGS.md:3242` and `:3722` from
UNVERIFIED to OBSERVED.** Those lines predicted this exact function, thunk and caller list
and labelled the route as not-yet-seen live. Two lanes reached it independently in this
pass: L1 from a static walk of the fence, L2 from the retaddr census. The skeptic
reproduced every structural fact on the pinned build.

**Concentration, in the sentence:** 14 of the 21 firings come from **one** capture
(`k1-treatment`), in one burst (seq 920–964); the route fired in 5 of the 7 snap-capable
captures. **n = 21 is not 21 independent events.**

**The route was a NO-OP in this corpus — n = 7, not 19.** On `m_segmentPoint` (`+0x88`),
the field `reseed` actually copies, **0 of 7 finite gateless rows** are non-zero against
**19 of 20 finite gated** rows (Fisher p ≈ 1e-6). The lane's published 0-of-19 counted 12
non-finite rows (the `+INF` `AGENT_INVALID_POSITION` sentinel at `0x00948654`, asserted by
AgAgent:974) as zeros on one side while scoring 3 `inf` rows as non-zero on the other —
`math.hypot(nan,nan) > 1e-3` is False. Corrected, n drops 19 → 7 across 3 captures, 3 of
the 7 from one file. **The best vacuity attack on this null FAILED and the result is
stronger for it:** `arg1 − ecx` is a nonzero constant per capture and *identical* at the
gated and gateless sites (k1 +2624, k2 +984, k2-2 −4264, r1b1 +4920, r1b2 −1640, run4
−2952, run5 +1968), so both routes carry the same two world copies and the ~0 separation is
not a same-object identity.

**Whether the route is wire-reachable is OPEN, and the lane's claim that it is not is
REFUTED.** "Driven by LOCAL input … no wire policy can close it" generalised from 2 of 3
callers; the third, `0x004E6E82`, was never opened, and `studies/movement/FINDINGS.md:2386`
already associates that entry with **opcode `0x0023` — a wire opcode**.

**Method consequence, and it reaches back through the arc.** `readhook.py:637-646` pools
`tests + seeds` with **no caller split**, so every separation statistic this arc has
published mixes the two routes. §1h.1's run-5 "n = 14" is **11 gated + 3 gateless**.

---

### 1s.2 R3 is CLOSED at a desk, on its own refuting shape — and the suppressor that does exist cannot be scored from any corpus we hold

`HANDOFF-WARP.md:195-208` names three candidates and registers the refuting shape: *"if
every reader of those bits is cosmetic, this route is dead in an afternoon."* **All three
are dead, and the afternoon is spent.**

**The fact that makes the three verdicts rigorous rather than shallow (OBSERVED):**
`snaptest`, bounded exactly at `0x006055E0..0x0060583D` (207 instructions), **touches
`m_flags` zero times.** Its entire agent-field surface is `+0x24` (world, assert only),
`+0x48`, `+0x78`/`+0x7C`/`+0x80`/`+0x84` and `+0xC4`; everything else is stack, AgTrack
record, or 16-byte position-block offsets ≤ `0x14`. **The decision function cannot read
bits 17, 18 or 19 because it never touches the word they live in.**

* **(a) `INTERNAL_FLAG_MOVEMENT_STALE`, bit 19 (`0x80000`) — DEAD. OBSERVED (static).**
  Mask confirmed from `shr eax,0x13` at `0x0060014E` guarding ArenaNet's own assert
  AgAgent:1198. Image-wide memory-form operations on the bit number exactly **3**: SET
  `0x00602429` (inside `reseed`), SET `0x00602A22` (inside the `0x002B` rate/facing
  setter), CLEAR `0x00602A65` (the destination setter). **Zero memory-form TESTs anywhere
  in `.text`.** The two SHIFT CANDIDATEs `codescan` also printed (`0x00600EC5`,
  `0x00601138`) were traced and are `shl eax,4` loop arithmetic — genuine false positives.
  *Caveat that must travel with this:* `codescan` does not search a mask held in a register
  or a compound mask, so "zero memory-form TESTs" is not "never tested".
* **(b) `INTERNAL_FLAG_IN_WORLD`, bit 17 — DEAD as a lever. OBSERVED.** Mask confirmed from
  `shr eax,0x11` at `0x005FE6BD` guarding AgAgent:297. Its 9 tests in AgAgent split 5
  assert guards and 4 real branches (`0x00602462`, `0x0060254E`, `0x006025F8`,
  `0x0060293D`) — every one inside `reseed`, its callee `0x00602540`, or the re-aim setter
  `0x00602910`, i.e. **the CORRECTION, never the decision.** `0x00602462`'s block is
  additionally gated on `reseed` arg3 (`cmp [ebp+0xc],0 / je 0x602536`), which is
  `i != focusId` and therefore 0 for the player's own agent. Set in **78,745 of 78,745**
  movetap rows; clearing it would freeze the agent, not spare it.
* **(c) `agent+0x98` — does not gate the reconcile. OBSERVED.** `--field 0x98 --in AgTrack`
  returns **0 instructions**, and an exhaustive capstone operand sweep of 12 reconcile-path
  ranges (`snaptest`, `agtrack`, `seg_match`, `GetPointAt`, gate 3 `0x005FEF70`, `map_dist`,
  `find_path`) finds no `0x98` displacement in any of them. On the reconcile path it appears
  **exactly once** — `0x00602441 push dword [edi+0x98]` inside `reseed` — and there it is
  **forwarded** to the setter, never tested.

**The suppressor that DOES exist, at the strength that survived.** `agtrack` `0x00605FC0`
computes `rec = [this+0x20] + id*0x1C` and at `0x00606002` does
`cmp dword [eax+ecx*4], 0` / `0x00606009 je 0x606103`; the tail returns doing nothing or
appends history. On a zero `clientControlled` record, `snaptest` is never called and the
reseed walk never runs **for that invocation**. Reproduced exactly by the skeptic on the
pinned build.

**"Complete" is REFUTED, and so is the novelty.** The *decision* is per-agent; the
*correction* is roster-wide — `0x0060604C..0x006060EE` walks every non-DESTROYING world-1
agent and calls `reseed` on it, so a zero record on the player stops the player *triggering*
a reseed and does not stop the player *being* reseeded by someone else's snap. And
`agtrack` **clears records itself on its own snap branch** (`0x0060602E call 0x605f70`, plus
`0x006060A2`/`0x006060A9` inside the walk). None of this is new: **`movetap.py:66-155` has
carried the full `0x00605FC0` fence disassembly in prose since 2026-08-20**, including
`00606002 cmp dword[record+0x00],0  clientControlled` and both facing-9 early-outs verbatim,
and `movement/FINDINGS.md:3246`, `:3681` and `:3722` carry the rest.

**A retracted claim was reintroduced and must not be re-published.** "Every local
destination-set re-arms the fence" is **FALSE**: `0x00605F3F cmp dword[eax+ecx*4],0` /
`0x00605F43 jne 0x605f57` makes the setter a **no-op on an already-armed record**.
`movement/FINDINGS.md:3681` already caught and corrected exactly this.

**Whether the fence suppresses warps is NOT-MEASURABLE-BY-THIS-METHOD.** See §1s.8 item 1
for why the 0.329%-vs-0.113% contrast is not a measurement of suppression.

---

### 1s.3 Gate 1 decides the majority of snaps — at 19 of 28, not 23 of 28 — and gate 3 is a DISJUNCTION `main` already had

**OBSERVED.** Denominator: the 32 **gated** reseeds pair **1:1 and exactly** with the 32
`snaptest` calls that returned 0 (a gated reseed within 2 ms; no `snaptest` has two
candidates, none is orphaned), and the paired records carry **byte-identical source-agent
blocks 28/28**, so the reseed record is a faithful snapshot of gate 1's operands. 28 are
scorable — `run4` is a v4 capture with no `src` block. Snap rate overall **32 of 245
`snaptest` calls = 13.1%**.

**Gate 1 firmly decided 19 of 28 (67.9%); at most 25 of 28 (89.3%); 6 of 28 are
UNDETERMINED** because the verdict flips inside the feasible evaluation window. The lane's
23-of-28 came from an unjustified `[t0, t0+200 ms]` band; the client's own assert
**AgAgent:978** (`!m_timeStopMovement || ((int)(m_timeStopMovement - time) >= 0)`, at
`0x005FFB9E` in the extrapolator and again at `0x005FF0F0` inside gate 3) names
`m_timeStopMovement` as the ceiling, and `stop`/`src_stop` are already fields in the record.
Band sweep: `[t0,+200]` 23 over / 1 straddle / 4 under; `[t0,+500]` 23/2/3; `[t0,+1000]`
22/3/3; `[t0, min(stop,src_stop)]` **19/6/3**. Empirical `m_point` staleness is p50 17 /
p90 1,382 / p99 8,613 / max 21,735 ms (n = 2,944), so 200 ms is not conservative.

**The conclusion the arc needs survives every band**: gate 1 is the majority explanation at
each, clearing the lane's pre-registered "< 50% means the wrong gate" threshold. **The nine
separation-managing candidates were aimed at the right gate** — for the gated snaps, in a
world containing one agent.

**The gate-2 coincidence check, at its honest p.** 3 of the 4 not-gate-1 snaps had a
`MapFindPath` query at the same tick; **0 of 23** gate-1 snaps did. The published
p = 0.00137 is the **one-sided** value on a 27-row table with the ambiguous row deleted;
two-sided including it is **p = 0.0031** at the lane's band and **p = 0.0256** under the
assert band. And 7 of the 24 over-cut rows sit in captures (`r1b1`, `r1b2`) that recorded
**zero** gate-2 executions at all. Supportive, not decisive.

**RECONSTRUCTION:** 209 of 245 `snaptest` calls (85.3%) were resolved before any gate ran —
by an early-out or the 100 u history chain. This is inference from an absence and rests on
the `MapFindPath` hook not dropping records (73 records corpus-wide, `claimed == stored`,
0 partial, in every capture).

**REFUTED — "gate 3 is agent-vs-agent blocking, not a terrain test."** Two independent
kills. **(a) `main` already had the fuller answer**: `studies/movement/FINDINGS.md:3180`
records the call site as OBSERVED and `:3183` names **both** ways it returns zero — a
neighbour agent inside a 60-degree forward cone (`fcomp [0x9458BC]` = 0.5f) whose combined
radius contains A, **OR** `timeToEvent < 0.0005f` (threshold at `0x00A53744`, read raw as
`0.0005000000237487257f`); `:3240`, `:3639`, `:3954` and `:3357` carry the rest. **(b) The
negative is false.** The 430 bytes the lane stopped short of contain `0x005FF496 call
0x70a0e0`, then `0x005FF49E fldz` / `0x005FF4A6 fcom st(1)` / `0x005FF4AC test ah,1`, then
`0x005FF510 fcomp dword ptr [0xa53744]`; and `asserts.py --at 0x005FEF70` **misses two
sites in that same extent** whose expression pointers (`0xa53390`, `0xa533a8`) read
AgAgent:764 `timeToEvent >= 0` at `0x005FF4B6` and AgAgent:773 at `0x005FF508`. **Gate 3 is
a disjunction: neighbour-agent crowding OR an obstacle time-to-impact test.** The negative
was published from a tool whose own banner says every "no assert names X" answer is a floor
and that it is short by ~370 sites — and it was short by exactly the two that mattered.

**REFUTED — "`0x006007A9` is a phantom, so gate 3 has exactly one real caller."**
`boundary_status(0x006007A9)` returns **confirmed**. The address the provenance quotes as
failing is `0x006007B5`, twelve bytes later, phantom only because it lands mid-instruction
inside the `je` at `0x006007B0`. `0x006007A9` is a textbook thiscall inside the
obstacle-sidestep `0x00600500`, and `main:3278`/`:3357` already record **n = 2 of 2 direct
callers**. This matters operationally: the proposed `stepclear` content row's `verified`
prose would have committed a false provenance statement that `content.py` **cannot** catch,
and "presence alone discriminates gate 2 from gate 3" is unsound until the hit is filtered
on `retaddr == 0x0060581E` (free — `rec_t` already stores it).

**THE HARD BOUND ON ALL OF §1s.3, and it bounds §1p's whole client-side picture too.**
Across all 10 captures the hook dereferenced **exactly one agent id (1, the player) and
exactly two agent objects per capture — the two world copies.** The snap loop is
roster-wide and produced exactly one reseed record per snap in every case, consistent with a
roster of one. **There is nobody to crowd with, so this corpus cannot exercise gate 3's
agent half at all**, and the K-vs-R "crowding" lead (4/10 vs 1/18, p = 0.041) is
**NOT-MEASURABLE-BY-THIS-CORPUS** — it is a map/operator difference with a crowding label
attached. The attribution table is **28 snaps of one agent in a world containing one agent.**

---

### 1s.4 Maps 242, 248 and 310 are committed — item 4's forecast was wrong in both directions, and the forced-verdict census is the number §1p.5 was missing

**CORROBORATED — the three file ids.** 242 → 156969, 248 → 165811, 310 → 167730, on two
independent predicates over the map→file **edge** plus an existence check. Wire: pairing
each connection's first `0x0199` field 2 with its first `0x0195` field 1 over **61 live
connections, 57 carrying both**, gives 242 → 156969 on 5/5, 248 → 165811 on 17/17,
310 → 167730 on 1/1, and all 14 map ids in the corpus are single-valued. Archive
(`vault/dat_study/Gw.dat`, a *different* copy from the one `studies/mapload/FINDINGS.md` §1
used): 156969 → MFT 21189 (64 planes / 3,307 traps), 165811 → 21641 (68 / 2,769),
167730 → 71585 (13 / 443), and **25 of 25 arrivals across maps 242/248/309/310/311 land in
exactly 1 trapezoid on the plane their own `0x0195` field 3 declares** (the committed rows
say 24 of 24 — one low; see the fixes block). Geometry-fit, with a wrong-mesh control that
survived a vacuity attack **decisively**: on `_54071`, coverage is **1.000 on the wrong
file 113021** and 1.000 on 167730 — coverage cannot separate them — yet heading-clip
agreement gives 113021 **0 of 53** and 167730 **24 of 53 = 45.3%**.

**The question was already answered in the tree.** `studies/mapload/FINDINGS.md:53-60`
committed the whole table on 2026-08-17/18, and `content/maps.toml` `[map.280]`'s own note
already stated 165811 carries map 248. This lane turned a known measurement into a
selectable row; it did not derive anything.

**§1p.10 item 4's forecast was wrong in both directions. OBSERVED.** It buys **+1** scored
click (26 → 27, refusals 4 → 3), not +3, and **3 navmeshes, not 5** — 248 resolves to
165811 which the corpus already held via map 280, so the ceiling was 4. Grouping is
`{113021: 15, 165811: 11, 167730: 1}`. The other two clicks fail for a **scorer** reason
that no content row can fix: neither connection has a c2s position anchor before its click
(`_60966`'s first `0x003D` is **26.74 s after** the click; `_52092`'s is 1.84 s after; zero
rows before, either way).

**REFUTED — "the check that could fail did not fire."** Item 4's registered payoff was that
all 3 admitted clicks are verbatim, so a many-leg verdict on any is H's first false
negative. **On the one specimen actually admitted, a many-leg verdict was geometrically
unattainable.** Holding the row's own modelled origin and its own 832.0 u click distance
fixed and sweeping 720 directions, **259 of 259 on-mesh destinations route ONE-LEG**;
many-leg only becomes attainable past ~1,200 u at that origin. It is not a mesh-wide
property — the base rate at 800–864 u on 167730 is 57.2% one-leg over n = 400 random
on-mesh pairs — so the specimen was unusually open, not the mesh.

**THE NEW NUMBER, and it quantifies §1p.5 item 5's "trivially one-leg" caveat for the first
time. OBSERVED.** Running that same sweep over all 27 rows: **10 of 27 verdicts are
forced** — 7 one-leg at P ≥ 99.5% (all verbatim) and 3 many-leg at P ≤ 0.5% (all part-way)
— and **17 of 27 are informative, where H scores 15 of 17.** The +1 row contributes **0 of
the 17**. H's headline 2×2 moves 13/2/0/11 → 14/2/0/11 = 25/27, honestly stated as
**24–25/27 across 277–328 u/s**, the same band §1p.5 item 1 already forced onto the 26-row
version.

**And the ≤ 2 s standard was applied asymmetrically.** The lane disqualified its two
RECONSTRUCTION rows for origin ages of 21.5 s and 50.0 s, then counted the new row (origin
age **14.0 s**) toward H without the same caveat. A held-out check on that connection puts
`modeled_origin` at **652.2 u error against a naive "origin never moved" of 200.9 u** — the
model loses there. The verdict survives perturbation (one-leg at 200–400 u/s and on 360/360
perturbed origins out to r = 475 u) but the row is **not in a validated regime**, and it
enters neither of §1p.5's two informative cuts (age ≤ 2 s fails; d ≥ 1,276.4 u fails at
832 u). **The single largest scope limit on §1p is not materially relieved:** 167730
supplies 1 of 27 rows, 26 of 27 are still on the original two meshes, and `_62994` still
supplies 12 of them in a 48-second window.

**CONTESTED, flagged for whoever owns `content/`:** `explorable = false` on `[map.310]`.
The literal reading is verified — AreaInfo type is 11, not the 2 that means explorable —
but `type == 2` is calibrated only against Pre-Searing, type 11 is uncalibrated and rare
(17 of 888 records), and `map_explorable`'s own docstring makes it the **combat** gate,
while `studies/isle/FINDINGS.md:713` records **553 observed damage events on map 310**. The
row asserts combat is impossible on a map we have 553 damage events from. Not a behaviour
regression — unconfigured maps already default False — but it must carry a CONTESTED note
rather than a bare `false`.

---

### 1s.5 The three named mesh specimens: one is CLOSED, one is LOCATED, and the third survived its own debunk

**Specimen A (`_60935 t=58.694`) is NOT a mesh disagreement. OBSERVED, n = 1.** Sampling
the origin→click ray at 0.1 u on **every** plane: walkable over f 0.94000–0.95042, **FALSE
over f 0.95046–0.95425 — a 10.00 u gap** — walkable again f 0.95429–0.97498. The gap is
real in ArenaNet's own pathing data and **retail did not cross it either**: it granted a
point 131.08 u short of the click, at along-fraction 0.9503, 0.53 u off our own ray, and
our `clip` stops **within ~0.5–1.2 u of retail's grant** depending on step (1.14 u at
step 4.0, 0.48 at 1.0, 0.58 at 0.25). A's origin is modelled but at age 0.951 s, inside
§1p.5's validated regime. **A's defect is `route()`'s refuse-vs-truncate policy**
(`pathmap.py:698-703` returns None on a component split), not its geometry — the click
point is covered only by plane 20, so all three plane-hint settings return None.

**Specimen B (`_52318 t=262.438`) is a real, located, fixable defect — but it is a
TOLERANCE, not a decode bug. OBSERVED, n = 1.** Retail's granted point lies
**1.268e-06 u outside** the exact real edge of `p0#1994`. Evaluated in exact rational
arithmetic over the decoded float32 corners, `|float64 lerp − exact| = 1.06e-13 u` — so
**nothing decodes wrong and `contains()` is mathematically correct**; the grant is
genuinely outside. What is missing is a tolerance for comparing **float32-quantized wire
coordinates** against an exactly-evaluated boundary, in `Trapezoid.contains`
(`pathmap.py:327`) and `walkable`'s flat copy (`pathmap.py:460`). Retail's grant is the
intersection of the click ray with that edge — along-fraction 0.065287, perpendicular
offset 0.000039 u, measured from a **reported** origin at age 0.348 s.

* **The fix is an epsilon, not float32, and the float32 route was tested and BREAKS**
  `_63805 t=1103.590`, whose leg runs exactly along `p0#1295`'s left edge (`x − left64` =
  0.000e+00 at 6+ consecutive samples).
* **Size it at ~1e-2 u, not 1e-4.** Half a float32 ULP is 1.221e-04 u at B's own
  |x| = 2992.7 and 9.766e-04 at map148's extreme |x| = 21504, so 1e-4 is **below the
  quantization it exists to absorb everywhere |coord| ≥ 2048**. And
  `studies/movement/FINDINGS.md:1670` already measured retail grant deviations to
  **0.0025 u**, "tracking the float32 ULP by binade" — 25× the proposed number. The corpus
  cannot select a size: 1e-4, 1e-3 and 1e-2 all give 26/26 chains clip-clean and 41/41
  grants on-mesh.
* **The exposure is 1 of 41 grants, not 11 of 40.** Ten of the eleven "exactly 0.0 u from an
  edge" grants are **degenerate** (f == 0.0 or 1.0 — the lerp returns a corner exactly and
  the hazard cannot arise); `contains()` accepts all eleven anyway. Genuine non-degenerate
  near-edge landings corpus-wide: 3 of 41, one of which is rejected. The eleven also come
  from 6 click rows on **2 connections of 8**.
* **The negative control that DID pass:** the 26 raw user click points are min 69.54 u /
  p50 1,412.23 u from an edge, **0 of 26 within 1e-2 u**. Edge-sitting is a property of
  retail's *router output*, not of the point population.
* `CELL_SLACK = 1.0` (`pathmap.py:184-201`) is applied at `:424-425` and `:458` but not at
  the acceptance comparison `:460` — factually true, but its stated job is keeping
  `walkable()`'s bucket from missing a trapezoid `contains()` would find, which it does
  correctly. An acceptance epsilon is a **new** policy, not a misplaced existing one.

**Specimen C (`_61106 t=67.787`) — the "plane-blindness artifact" reading is REFUTED, and
§1p.6's exception 2 stands as NOT FOUND.** The lane measured ring clearance restricted to
**plane 0**, the plane it had itself just shown is empty over that stretch, and read the
resulting 0.0 u as a debunk of the published 96 u corridor. Restricted to **plane 17**, the
plane retail actually transited: clearance is the **full 96 u for f 0.075–0.500 and 64 u at
f 0.525**; at retail's grant0 the plane-17 ring is 68 u, and at our straight line at the
same along-fraction it is 76 u. **Retail moved 101.7 u laterally to a point with LESS
clearance on its own plane.** A plane-17-aware router going straight would have had more
room. §1p.6's "our mesh has nothing there to route around" survives intact.

**Also REFUTED — "C's two anomalies share one cause."** On the lane's own cached data,
grant0 (+0.007 s) is the 101.7 u detour with wire plane words **(17,17) — no transition** —
and grant1 (+0.048 s) is 1.60 u lateral with words (0,17), which *is* the handoff. The 41 ms
cadence pair spans a non-transition waypoint and a transition waypoint, so the handoff
cannot explain the first one's offset. **And the "fourth row shares C's cause" grouping
falls with it**: `_63805 t=1233.471`'s grant is a **1.29 u truncation**, not a detour.

**What DOES survive there is a genuine refinement of §1p.6's exception 1. RECONSTRUCTION,
n = 1.** `_63805 t=1233.471`'s grant carries wire words **(29,0)** — retail's server
explicitly announced a plane-29 destination — and the `{0,29}` union clearance dips to 28 u
at f = 0.600 while plane 0 → 0.0 and plane 29 → 8.0. So the committed "~24 u clearance dip
our zero-width clip walks" **is the plane-blind union thinning at a plane seam**. It
explains why the committed dip exists; it does not supersede it, and it does not join C.

**Two of the lane's own hypotheses died correctly and are worth recording:** the unused
forward portal index is a **redundant second witness that agrees** (map148 378/378 keys,
906 == 906 memberships; map280 698/698, 1230 == 1230; zero reverse-only, zero forward-only),
and the tag-13 obstacle candidate is **NOT-MEASURABLE** (0 of 26 corpus lines cross one, but
the positive control gives only ~1.5 expected crossings, p ≈ 0.22). **CONTESTED:** retail's
`0x0029` plane-word field order is not settled by geometry — **both** candidate orders match
our decode on 40 of 40 grants with **zero** discriminating rows.
`studies/movement/FINDINGS.md:849-880` remains the sole witness.

---

### 1s.6 `0x0025` is absent from the click contract — as an ENTAILMENT, on n = 2 exposed trials — and our defect is ONE ARM, not our rate

**CORROBORATED, and this is the lane's strongest result.** `0x0025` carries nothing the
server computes, at n = 2,595 (against the committed n = 2,256): the vec2 is a unit vector
(|v| p50 0.999593, max exactly 1.000000, 100% below 1.01), the angle to the client's **own**
reported vec2 is p50 and p90 both 0.0000 deg, and the trailing byte equals the c2s `0x003D`
field-4 `movementType` on **2,550 of 2,592 = 98.38%**. The null the lane did not run and
the skeptic did: shifting to the report five places earlier on the same connection gives
**1,243 of 2,380 = 52.23%**, against a mode-guess baseline of 61.50%. Reproduces
`movement/FINDINGS.md:3809` at larger n. Field decode independently confirmed on the pinned
build by `msgshape`, which recovers the **client's own** cmds-table initializer writes and
is therefore a second witness rather than the OpenTyria import counted twice: `0x0025` RECV
table `0x00a52d70`, handler `0x005fd540`, `[u32, vec2, u8]`, 15 B; `0x0029` handler
`0x005fd890`, `[u32, vec2, u16, u16]`, 18 B.

**The same-frame subordination is real but it is not `0x0025`'s property.** Timestamps
**tie** — dt from a player `0x0025` to the next player `0x0029` is 0.000000 s at p50, p90
*and* p99 — so the pairing must be scored on merged wire **order**. Forward: 2,592 of 2,595
(99.88%) carry a same-frame position-moving message. Backward: 2,592 of 3,672 (70.59%). But
`0x002B` shows the same subordination at **100.00% forward (n = 1,273)** while `0x0027`
(n = 184) and `0x002A` (n = 215) both read **0.00%** — the instrument is not vacuous and
the rule is more general. **`movement/FINDINGS.md:3810` already committed the stronger
form.** CORROBORATION of a committed result, not a new finding.

**§1p.10 item 5's registered refutation FIRES — but as an entailment, not a 32-trial
measurement.** The lane's "0 of 32 clicks, 0 of 32 chains, 0 of 5 multi-grant chains" is
arithmetically right and its **exposure is 2, not 32**: on 24 of 32 clicks the preceding
report's own `0x0025` had already been sent (0.20–20.95 s earlier, median 2.29 s), 5 had no
report at all, 1 was 17.12 s stale, and the 2 genuinely exposed sat at lags of 0.67 s and
0.12 s against a 36 ms answer median. The in-instrument control (82.0% of 3,079 reports vs
0 of 32 clicks) contrasts a population that **by construction** holds a fresh vector with
one that by construction does not. **The conclusion nonetheless holds as an entailment of
two already-committed facts** — the client sends **no position** while click-moving
(`movecode/FINDINGS.md:1716`) and `0x0025` is `unit(the client's own vec2)`
(`movement/FINDINGS.md:3809`). A click supplies a **point**, not a vector, so there is
structurally nothing to echo. **Independent evidential weight: n = 2.** State it that way.

**REFUTED — the "if and only if" trigger.** Necessary: `0x0025` → a fresh `0x003D` exists,
2,592 of 2,595 = 99.88%. Sufficient: a fresh `0x003D` → a `0x0025` follows, **2,543 of
3,079 = 82.59%**. 17.4% of fresh reports draw none. The lane's own body concedes it (492 of
2,990 first-grants bare).

**OUR SIDE: the pooled row describes no configuration our server has ever run. OBSERVED.**
Every `0x0025` send's `label` field carries the arm inline. Partitioned on it instead of on
a date proxy, agent-filtered, same 60 ms instrument on both sides, post-2026-08-22:

| arm | n(0x0025) | forward | backward | ratio |
|---|---|---|---|---|
| `[legacy+zero-lead]` | 1,673 | **100.00%** | 90.09% | 0.901 |
| `[zero-lead]` | 464 | **100.00%** | 89.23% | 0.892 |
| `[legacy]` | 1,636 | **0.67%** | 3.01% | 4.470 |
| untagged | 861 | 0.46% | 1.71% | 3.679 |
| *pooled (the published row)* | 4,634 | *46.44%* | *72.29%* | *1.557* |
| **retail, same instrument** | 2,595 | 99.81% | 70.53% | 0.707 |

**Not one arm is near 46.44% or 72.29%.** Our zero-lead arms are at or **above** retail on
the forward test and **over-pair** on the backward one. The defect is that the `legacy_dir`
arm ships a bare direction — `authsrv.py:15788-15794` fires `0x0025` on
`turned or state['walking'] is not True` while the accompanying grant is gated separately on
`zero_ok` (`HEADING_GRANT` defaults False at `:1200`) — which is already committed at
`movement/FINDINGS.md:3899`. It is a per-arm defect, not a global misuse and not a rate
error.

**DO NOT correct §1p.10 item 5's "32.2/min, 4.7× our grant rate" in place.** That is a
**per-run** figure for a named default build with its per-run counts stated. Replacing it
with a pooled mean over 230 heterogeneous logs is a denominator substitution: per-log today
the ratio is p10 0.00 / p50 0.70 / p90 1.92 / **max 134.0** (n = 164 finite) and the rate
p10 0.0 / p50 12.2 / p90 67.4 / **max 165.1 per min**; **66 of 230 logs contain zero
grants** — the exact `HEADING_GRANT = False` condition the committed figure describes — and
80 of 230 are still ≥ 4.0×, 62 of 230 still ≥ 25/min. The committed figures are live,
currently-reproducible configurations.

---

### 1s.7 The click-walk silence: the counterexample class is ~3, not 24 — and I RETRACT §1p.4's 7-row cell as unreproducible

**The refutation of the absolute wording HOLDS — and it was already committed at §1p.4,
whose own heading calls the answer OVERSTATED.** This lane verified it independently rather
than discovering it. What is genuinely new: an independent reimplementation, a 27/27
anti-vacuity splice control, the `movementType` test, the closing-rate discriminator, the
per-connection table, and the replacement texts in the fixes block.

**CORROBORATED — the vacuity, reproduced from scratch.** Rebuilding the `INPUT_OPS`
terminator gives 0 inside, **0 of 27 recovered** by the splice, and exposure falling
**exactly −50.0%** — the edge-eating signature. The corrected census reproduces exactly
under an independent implementation on cache-verified data (61/61 connections re-decoded
byte-identical, 153,688 rows): **K = 27 windows, 79.73 s exposure, 24 position rows inside,
4 of 27 windows carrying.**

**But the counterexample class is ~3, not 24. OBSERVED.** Scored on the tree's **own**
committed discriminator (§1p.4: lead-changed pairs p50 0.500 s = steering; lead-unchanged
p50 1.768 s at ~511 u stride = odometer — reproduced exactly, stride p50 509.9 u), **22 of
the 24 are lead-CHANGED**. By stride, the cleaner marker, only **3 of 24 sit at the odometer
stride**: 513.8 u / 1.784 s and 509.3 u / 1.768 s on `_63805 t=1233.471`, and 514.1 u /
1.786 s on `_62994 t=136.480`, all at 287.9–288.1 u/s. The remaining twelve on `_52318` are
strides of 12.6–300.3 u at 109–383 u/s — **383 u/s exceeds the 288 run speed** — and the
lane's own discriminator calls that window RECEDING at −264.7 u/s and excludes it. **Half
the headline is a class the lane rejects three claims later.** A steering-cadence report
inside a click-outstanding window is a keyboard report and refutes nothing about a
click-walk.

**REFUTED — "it is a session property, not a client property."** `_63805`'s three click
windows split **0 / 7 / 3**, and the zero window (`t=1103.590`, 6.725 s) sits inside a
**36.70 s report gap covering 1,936.9 u on that same connection**. A property of the session
cannot produce heterogeneity within the session. And the contrast mixed nulls: scored
against `_63805`'s **own** report stream — the control that gave `_62994` its p_le = 0.0002
— that connection gives obs 10 vs null p50 12 (uniform) / 18–19 (command-onset), i.e.
**0.53–0.83×, the same direction as the corpus**, at p_le 0.16–0.41. **Underpowered, not
null.** Seven of the nine per-connection rows have odometer expectations of 0.0–3.7 reports
and carry no information at all.

**The permutation nulls are biased upward and must be quoted as a bracket.** The observed
window terminates at the first command and therefore contains **zero** commands by
construction; the null windows are unconstrained and can span commands, which correlate
with report bursts. Truncating the null identically moves uniform p_le **0.0203 → 0.0622**
(crosses 0.05) and command-onset **0.00005 → 0.00285**. Significant under command-onset
(p ≈ 0.003), **not** under uniform (p ≈ 0.06).

**The silence specimen survives at full strength, and it is what the original claim's
authors were looking at. OBSERVED.** `20260807T143055/_62994` leaves two gaps of **23.27 s
(6,611 u, 284.1 u/s)** and **27.84 s (7,529 u, 270.4 u/s)** with 8 and 4 clicks issued
inside them and **zero** c2s position reports. Confounds checked and clean: no s2c `0x002C`
reposition, no `409` map load inside either gap, capture continuous (max inter-row gap
0.58 s), 113 and 23 player grants inside them. Player attribution verified twice — agent 31,
132 grants within 0.25 s of a client report at a median 765.5 u (the D1 lead constant),
runner-up 2,056.8 u, plus bit-exact click echoes. Click-anchored permutation on that
connection alone: **obs 2 vs null p50 22–33, p_le 0.00005 / 0.00020 / 0.00035 / 0.00130**
across all four control definitions. *Caveat in the sentence:* "two gaps between consecutive
position rows contain zero position rows" is an identity and the two quoted are the
**maxima** of that connection's gap distribution, so the odometer-null figure is not a null
test — the permutation is the defensible statistic. And the same connection produces a
12.03 s / 2,388.0 u gap with **zero clicks inside**.

**I RETRACT §1p.4's second table row.** `FINDINGS.md:2175` publishes "77.44 s / **7** / 3 of
27" for the command-terminated window. It is **not reproducible from `routerbench`'s
committed instrument**, and the cause is not the terminator or the counted set:
`term{62,57}/count{61,71}` — the published construction — gives **exactly 27 / 79.73 s /
24 / 4-of-27**, identical to `term{62,71,57}/count{61}`; `term{62}` alone gives 26; and no
3-window subset of the carrying counts `{12, 7, 3, 2}` sums to 7. The row's script was a
scratchpad artifact and cannot be re-run. **They are inconsistent, not differently
sensitive.**

**The `movementType` candidate is NOT-MEASURABLE-BY-THIS-METHOD, not NOT FOUND.** Its
numbers reproduce exactly (inside `{1:16, 2:2, 3:6}`, p = 1.00 / 0.76 / 0.26 against a
corpus of `{1:2033, 2:373, 3:494, 4:51, 5:19, 6:18, 7:42, 8:49}`, n = 3,079) — but the test
population **is** the 24 in-window reports whose attribution the lane itself calls CONTESTED
and which are 22/24 steering-cadence. A test for "does `movementType` mark a click-walk
report" run over a population that may contain zero click-walk reports cannot return a valid
negative, and n = 24 has no power against anything short of a total partition. **§1p.10
item 6's pre-registered refutation criterion is neither met nor honestly tested.**

**The closing-rate discriminator is a real instrument and passes both controls. OBSERVED.**
Pointed at grant points on **1,751 known-walked legs** it scores 1,717 CLOSING (98.1%) at
p10/p50/p90 = 276.9 / 287.8 / 382.7 u/s — recovering the measured run speed with **no fitted
parameter** — and the negative control the lane did not run (replace the grant with a random
grant from the same connection) gives **45.6% at p50 84.1 u/s**. It separates "moving toward
the click point" from "moving away". **It does not separate a keyboard walk aimed at the
click from an autonomous order-walk**, which is the contested hypothesis.

**NOT-MEASURABLE-BY-THIS-METHOD, and this is the most useful claim in the lane.** Every
discriminator in this family — `movementType`, `|lead|`, answer-along-heading, closing rate,
arrival/overshoot — is computed **from position reports**, and the silent class has none by
definition: **15 of 16 silent clicks have zero trajectory rows before the next click.** No
report-derived instrument can be applied to the class that supports the mechanism. Note also
that the census loses **5 of 32 clicks** because `routerbench.player_agent()` votes with
`op61` — §1p.10 loose end (a) already names `20260817T183323/_49545` (78.7 s, 3 clicks, zero
`op61`) and offers the `op32` fallback. **The most report-silent connection in the corpus is
excluded from a census about report silence.** It biases retail *louder*, so it does not
rescue the absolute claim.

**The overshoot specimen cuts harder than the lane stated.** On `_63805 t=1233.471`, reports
at 1231.025 and 1232.803 sit **1.778 s apart (odometer cadence) BEFORE the click** and are
already closing on a point not yet clicked (2,976.2 → 2,464.0 u); post-click the client
closes to 60.3 u and stops on an explicit c2s `0x0047` at t = 1242.730, **391.3 u past the
click point**. The client was on that heading 2.4 s before the click existed.

---

### 1s.8 The lanes and sub-lanes that came back vacuous, forced, or refuted by their own skeptic — printed as results

In §1p.9's style. Eleven of them, and three are the same defect this arc has now published
five times.

1. **"Suppression buys ~3×" (L1's headline) — KILLED, and the classifier is mutated by the
   outcome it classifies.** The 0.329% (187/56,918 fence-open) vs 0.113% (20/17,657
   fence-shut) contrast reproduces to the digit over 74,575 adjacent sample pairs in 60
   captures, and is not a measurement. (a) The offered control — "no open-fence event
   ≥ 150 u in the preceding 2.0 s" — looked for a preceding **detected warp**, never at fence
   **state**, so it could not have found the confound it was offered as ruling out; the
   matched control fires hard (**18 of 20 shut-arm events within 15 samples of an 'open'
   reading vs 15.6% ambient (624/4,000), p = 4.1e-13**; 6 of 20 within 2 samples vs 2.8%,
   p = 1.3e-05). (b) The sampler runs at **11.4 Hz / 87.8 ms median period against a median
   shut run of 13 samples and 640 transitions over 78,745 samples** — the exact condition
   `movetap.py`'s own docstring **pre-registers as INCONCLUSIVE**, and the abort was not
   invoked. (c) `agtrack` zeroes the whole roster's `clientControlled` on snap
   (`0x0060602E`, `0x006060A2`, `0x006060A9`), so "shut" is partly the **post-snap** state.
   (d) The sign **inverts within date** — 2026-08-24 gives shut 10/1,306 = 0.766% against
   open 3/1,838 = 0.163%, i.e. shut **4.7× worse**. (e) Simpson: moving 4.3×, stationary
   1.6×, with **14 of the 20 shut-arm events being ≥ 150 u jumps from a standstill** — not
   the prediction-drag this arc calls a warp. Concentration: 8 files, 6 of 20 from one, 14
   of 20 from three, and three of them inside 2.4 s at 179/177/178 u — one episode counted
   three times.
2. **Bit 19 "never observed set, 0 of 78,745" — NOT-MEASURABLE-BY-THIS-METHOD.** Bit 19 is
   SET at `0x00602A22` and CLEARED at `0x00602A65`, plausibly inside one 87.8 ms sample
   interval. The offered control (6 rows of bit-18 toggling across 5 files = 0.0076%) proves
   the reader is live, not that an 11.4 Hz poll could catch it. The static half carries the
   verdict alone.
3. **The facing-9 armed/unarmed cross-tab — NOT-MEASURABLE-BY-THIS-METHOD, correctly
   self-labelled.** All 6 armed-state events are in one file and the next sample shows
   facing back to 1. `movetap` samples state, not executions
   (`studies/movement/PROBE-GATEFIRE.md:765` says this in terms).
4. **L3's "check that could fail did not fire" — FORCED, 259 of 259.** §1s.4.
5. **L3's fourth positive control (seeded origin bit-identical, 27/27) — a check that cannot
   fail, and its own script's docstring says so** ("the seed MUST be overwritten and the
   seeded origin MUST be BIT-IDENTICAL"). It tests code equivalence in exactly the regime
   where the two models cannot differ. **Three controls passed; one is an identity.**
6. **L4's epsilon safety zeros — vacuous.** "0 newly-walkable of 40,000 uniform samples at
   eps = 1e-3 and 1e-2" has an expectation of **0.02–0.3**, computed from the lane's own
   instrument (0 / 0 / 3 / 21 on map148 and 0 / 0 / 4 / 28 on map280 at 1e-3 / 1e-2 / 1e-1 /
   1.0). It could not have returned anything else at the sizes reported as safe.
7. **L4's "bit-exact refutable form" — 99.48% forced.** The discrepancy is 1.268e-06 u
   against a float32 ULP of 2.441e-04 at that magnitude — **0.0052 ULP** — so the two could
   only have differed on a 0.52% straddle.
8. **L4's "11 of 40 grants sit at exactly 0.0 u from an edge" — 10 of the 11 are
   degenerate.** §1s.5.
9. **L5's "0 of 32 clicks" — exposure 2 of 32.** §1s.6. This is "zero exposure is not a
   null" one level above §1p.4's terminator-set form.
10. **L5's "the entire ratio excess is the unaccompanied population" — an algebraic
    identity.** `accompanied / grants = 2,590/3,672 = 0.7053` and the backward rate is
    `2,590/3,672 = 0.7053`; the forward and backward tests read the same 1:1 nearest-neighbour
    pairing from two ends. Removing the unaccompanied population leaves the backward rate **by
    construction**. §1p.9's "two instruments may be one theorem", exactly.
11. **L6's floor F3 — implied by F2.** `D_hi ≡ 288 × expo_seconds` by construction, so
    `F2 (expo ≥ 40 s)` forces `F3 (≥ 8,000 u)`: 288 × 40 = 11,520. **Two of five
    pre-registered floors are one floor, in the lane whose whole brief was about checks that
    cannot fail.** Relatedly, "22,962 modelled units" is 288 × 79.73 s restated, not a
    measured distance: the uncapped grant-chain length over the same windows is **54,856 u**
    and the `min()` cap binds on 23 of 27.

**Also underpowered rather than negative:** L2's K-vs-R crowding lead (one agent id and two
agent objects in the entire 10-capture corpus — §1s.3); L2's gateless `m_segmentPoint` null
after the NaN correction (n = 7 across 3 captures, 3 from one file); L4's `starts[0]`
component hazard (**zero exposure** — all three specimens have `n_containing == 1` at the
origin); and L6's `movementType` test (§1s.7).

---

### 1s.9 What this changes about the ranked list (§1p.10)

**Items 1 and 2** were run and REFUTED before this pass (§1q, §1r). Untouched.

**Item 3 — "do NOT build the one-leg gate" is CONFIRMED as a decision, and now has the
number it was missing.** 10 of 27 rows are geometrically forced; the informative subset is
17 rows and H scores 15 of 17 there. n rose 26 → 27 and the **informative core did not
grow** — the new row contributes 0 of the 17. Nothing changes; the item stays a decision.

**Item 4 — CLOSED, delivered, and wrong in both directions.** +1 click and 3 navmeshes,
not +3 and 5. The follow-on (a `routerbench.modeled_origin` fallback anchoring on the
connection's own `0x0195` field 2) is **REPRICED DOWN**: ~1 hour desk, buys 2 clicks whose
origins are 21.5 s and 50.0 s stale — far outside the ≤ 2 s validated regime — and both are
RECONSTRUCTED as one-leg, so the expected yield is confirmation of a possibly-forced kind.
**Buy it for the 4th navmesh (156969), not for H**, and gate it on an explicit staleness
column so §1p.5's regime stays separable.

**Item 5 — CLOSED on its registered clause, but as an entailment (n = 2 exposed), not a
32-trial measurement.** Do **not** correct the 32.2/min premise. Two cheap things replace
it: (a) our forward-pairing defect is the **`legacy_dir` arm**, not our rate — the zero-lead
arms already sit at or above retail; (b) `authsrv`'s jsonl records origin, build, `world_id`
and `map_id` but **no argv/flags row**, and every ours-vs-retail comparison in this arc
inherits that blindness. A handful of lines.

**Item 6 — REPRICED and REDESIGNED. Do not buy the run as item 6 frames it.** "3–5 minutes
of pure click-walking, raising K from 27 to hundreds" raises n on the quantity that is
already settled and leaves attribution exactly as unsettleable, because a bigger corpus
still cannot observe key state. If the run is bought it must carry the missing variable and
the right statistic: **(i)** fix input mode by protocol — 3–5 min mouse-only with hands off
the movement keys, then 3–5 min of mouse clicks with a key held, **filed as two arms with
the arm recorded in the capture header** — or record key state; **(ii)** pre-register
**odometer-stride reports (490–530 u at ~288 u/s) inside a click-outstanding window** as the
statistic — corpus n = 3 today — **not total reports inside**, which is dominated by
keyboard steering and is what produced the 8×-inflated headline; **(iii)** carry the `op32`
spawn-position attribution fallback so all 32 clicks and any zero-`op61` connections score.
Same operator time; it turns an unfalsifiable attribution into a two-arm comparison with a
registered prediction (mouse-only should reproduce `_62994`; mixed should reproduce
`_63805`; if mouse-only reports at baseline, the mechanism is dead).

**Item 7 — SPLIT THREE WAYS.**
* **A (`_60935`) — CLOSED as a mesh disagreement.** Our mesh reproduces retail to ~0.5–1.2 u.
  What remains is `route()`'s refuse-vs-truncate policy, which is a **server decision**, not
  a `pathmap` change, and it is the same decision as item 3's "third else-branch that asserts
  nothing".
* **B (`_52318`) — LOCATED and COSTED.** A quantization tolerance at `pathmap.py:327` and
  `:460`, **~1e-2 u**, best implemented by pre-computing the slacked bounds into
  `_build_grid`'s record so the hot path pays nothing, with its own test section and a floor
  bump (`test_pathmap.py` is 981 lines, floor 68). Half a day. **Price it as a correctness
  fix, not a scope win:** the measured corpus exposure is 1 of 41 grants on n = 1 row.
* **C (`_61106`) — STILL NOT FOUND**, and it survived a debunk the plane data does not
  support. §1p.6's remaining candidates (a dynamic agent; a solver emitting from a coarser
  graph than the one it validates against) are untouched by this pass.

**NEW, and it is the top of the list: ONE owner-driven run with four new movehook sites
answers four open questions at once.** `0x00606009` (the fence, **counting executions**
rather than sampling state — this is the only thing that can settle §1s.8 item 1),
`0x00605634` + `0x00605683` (the facing-9 early-out's first compare and its return-1 tail),
`0x005FCAA0` (the gate-free `ResyncAllAsync` — the only instrument that can attribute the
fence-shut warps and the only one that can catch the gateless route firing *cold*), and
`0x005FEF70` (gate 3, filtered on `retaddr == 0x0060581E`), which discriminates gate 2 from
gate 3 **by presence alone** on all 3 undiscriminated snaps and captures `MapFindPath`'s
output path as a free by-product — the "second tap" the `mapfindpath` row's own `limits`
field says is needed. **Cost:** 4 rows in `content/movecode.toml` + a `gensites.py`
regenerate (NSITES 11 → 12+; `teleport`'s site *index* moves, harmless only because
`readhook.site_names()` resolves by RVA) + a DLL rebuild + one owner-driven run on build
38797 (`vault/run/2026-07-29_221c13772c7a/Gw.exe`, ours → loopback, caged). **Ring-fill
caveat:** `0x005FEF70`'s second caller sits on the avoidance retry path, which `main:3333`
says retries up to 6 times per collision event, so that site may fire far more often than
gate 3 does.

**NEW, desk, cheap:** split `readhook.py`'s separation report by reseed caller and switch it
to dead-reckoned positions — as it stands (`:637-646`) it pools the gated and gateless
routes and quotes stale `m_point`. **And two instruments are worth promoting** into
`toolkit/clientscan/` beside `routerbench`, with their controls as tests: the forced-verdict
sweep (which is the first thing that can say whether a 2×2 cell could have come out the
other way) and the closing-rate discriminator (the first thing in this arc that can tell a
click answer from a lead refresh **without consulting our navmesh**). Both passed a real
positive *and* a real negative control.

---

### 1s.10 What is NOT settled

* **Whether the AgTrack fence suppresses warps at all.** The corpus cannot answer it — an
  11.4 Hz sampler against a 1.14 s median shut run, with a classifier the counted outcome
  mutates. Needs a breakpoint counting executions at `0x00606009` / `0x0060601C` /
  `0x0060602E`. Owner's run.
* **Which route produces the fence-shut warps** — `ResyncAllAsync` `0x005FCAA0`, the arrival
  teleport `0x006020B0`, or our own `0x002C` pins. The tap cannot attribute them.
* **Whether `0x005FCAA0` is wire-reachable.** Its third caller `0x004E6E82` was never
  characterised, and `movement/FINDINGS.md:2386` associates that entry with **opcode
  `0x0023`**. If it is, a wire policy *can* reach the gateless route.
* **Whether the gateless route ever fires with a non-zero separation.** All 19 observed
  firings follow closely on a gated snap that had just glued the copies, so this corpus
  cannot see it firing cold. That is the residual risk to "the candidates were aimed at the
  right gate".
* **Gate 2 vs gate 3 on the 3 undiscriminated snaps**, and `k2 seq 720` (snapped at a
  recomputed 293.4 u, 2% *under* the cut, with no gate-2 query — either a missed record or
  a ~20 ms evaluation-time error). UNVERIFIED.
* **Gate 3's AGENT half has never been exercised by anything in this arc.** 10 captures, one
  agent id, two agent objects. Nothing here has measured a crowded world.
* **Whether a bare `0x002B` with no paired `0x0029` trips assert AgAgent:1198** by leaving
  bit 19 set. Statically it must — `0x00602990` sets the bit at `0x00602A22` and the only
  clear in the image is inside the destination setter a bare `0x002B` does not reach — and
  the corpus never catches bit 19 set, which the sampling cannot distinguish from "always
  cleared inside a tick". UNVERIFIED.
* **The attribution of the 3 odometer-stride reports inside click-outstanding windows.**
  Structurally unsettleable from the wire; needs the two-arm capture of §1s.9 item 6.
* **`agent+0x98`'s meaning — MOVECODE-Q3's remaining half.** Narrowed (it travels with the
  destination, is copied to follower agents alongside `m_segmentPoint`/`m_targetPoint`, is
  forwarded unchanged by `reseed` and by the re-aim, and is compared against a register at
  `0x006017CB` inside the local path solver `0x006011F0`), but that register's origin is
  untraced.
* **`explorable` for AreaInfo type 11.** An owner decision, or a calibration against an
  upstream column — permitted only as *verification* of a value we derived, per `PLAN.md`
  §6.1.
* **Whether the epsilon changes anything outside the two meshes and 26 rows.** The map corpus
  is 349 maps and `route()`/spawncheck/coverage consumers were not swept.
* **Whether file 165811 is 68 or 70 planes** — only `vault/dat_study/Gw.dat` was parsed (68);
  `vault/run-live/2026-08-13_…/Gw.dat` was not.
* **All `--in <module>` bounds in §1s.2 and §1s.3 are approximate.** `asserts.py` is short by
  ~373 sites, and `AgTrack`'s assert-derived upper bound `0x00605DE6` is **already known to be
  short** — `agtrack` itself lives at `0x00605FC0`.

---

## 1t. MOVECODE-R2 — the gate/fence run. **The operator was right, the detector was under-counting, and gate 3 is finally OBSERVED**

**OBSERVED, 2026-08-28.** Map 280, `--click-echo`, **9,094 records, v6**, both controls
FIRED, 13 sites, ~187 s of tracked motion. Capture
`vault/research/movecode/r2/movehook.bin`, image base `0x00230000` (every address below
rebased to `0x00400000`). Predictions were registered in [RUN-R2.md](RUN-R2.md) §1 before
the instrument existed. Three analysis lanes, each attacked by an adversarial skeptic; all
three came back **HOLDS-WEAKENED**, and the weakenings are in §1t.6.

**The operator's report is the finding this run turns on:**

> *"there is still clipping. the warp shape for this run was approximately getting yanked
> out of my cornered click to move, and put into place as if I'd run a straight line
> toward the destination from my original starting position"*

---

### 1t.1 The registered table

| # | prediction | result | |
|---|---|---|---|
| **P1** | the fence is READ, and seen both open and shut | **1,914 of 1,914 read (100%)**, 1,867 open / 47 shut | ✅ **CONFIRMED** |
| **P2** | two independent routes to the fence count agree | direct **47** vs derived **4** | ❌ **REFUTED — and the error was ours** |
| **P3** | the facing-9 early-out fires | `facing == 1` on **157 of 157**; never 9 | ❌ **REFUTED for this walk** |
| **P4** | `resync` fires, and the question is whether it fires COLD | 2 firings, **0.03 s and 0.05 s** after a gated snap, separations **30.0 u / 18.7 u** | ✅ floor met, **cold-fire answered NO** |
| **P5** | gate 3 discriminates, filtered on `retaddr == 0x0060581E` | 4 `stepclear` hits, **1 is gate 3** | ✅ **MET — first observation in the arc** |

Exposure floors: `snaptest` 157 (floor 20) ✅, `resync` 2 (floor 1) ✅, fence reads 1,914
(floor 50) ✅, fence shut 47 (floor 3) ✅, gate 3 1 (floor 1) ✅. **All five met.**

**P2's refutation is instructive and it is mine.** The "independent second route" was not
independent: it asked `world == 1?` before `was it tested?`, but `agtrack` tests the
**fence first** (`0x00606009`) and the world second (`0x00606013`). So every fence-shut
invocation on a world-1 agent is structurally invisible to it — **43 of them** — and
`47 − 43 = 4`, exactly the derived count. The derived construction is a **subset**, not a
witness. Only a direct read at the decision can see a fence shut on an agent the world
check would have diverted anyway.

---

### 1t.2 THE MECHANISM — all 11 displacements are ONE event, and it is not the teleport

**OBSERVED, replicated digit-for-digit by two independent lanes and both their skeptics.**

Every displacement is a **gated** `reseed` (`0x006022B0`, caller `0x006060E7`) reaching
`SetPosition` (`0x00602B20`) at `0x00602369`, which writes `m_point` at `0x00602B7B`
(`mov [edi], eax`, `edi = ebx+0x78`) and **never stamps `+0x58`** — which is precisely the
signature the displacement detector keys on. The value written is the **WORLD_SYNC copy's
own dead-reckoned position**:

> `landing = src_point + src_vel × (q.ptime − src_ptime) / 1000`

Perpendicular residual **max 0.000208 u on 11 of 11**; `|src_vel| = 288.0` on 10 of 10;
the 11th has `src_vel = 0` and `|landing − src_point| = 0.000 u`. Implied `dt` matches the
clock difference to **0.00 ms**.

**The vacuity control PASSED, and the lane had not run it — the skeptic did.** Applying
the same formula at the **146 snaptests that did not reseed** gives error **p50 129.33 u**
with only 7.5% under 1 u, against **< 0.001 u on 13 of 13** reseed rows. The formula could
have fitted everything and does not.

**"After teleport x10, after reseed x1" was an ATTRIBUTION DEFECT, not two mechanisms.**
`reseed` calls the halt-in-place `0x00602540` at `0x006022E7` when the body is moving, and
*that* calls the teleport at `0x006025A6`. The teleport sitting in front of a displacement
is **reseed's own child call**. All 11 follow a gated reseed, 1:1 with the 11 gated
reseeds. `readhook` now says so at the call site.

**Arithmetic closure, a check that could have failed:** 13 reseeds − 1 branch-skipped
(source idle) = 12, and `setter@0x0060244D` fires **exactly 12** times.

**PRIOR ART, and it is substantial — this is a corroboration, not a discovery.**
`studies/movement/FINDINGS.md:2617` already states *"`0x006022B0` hard-SetPositions the
player onto the authoritative copy. **That is the warp**"*, with `:3204` and `:3675`
carrying the rest; §1j.2 already OBSERVED that reseed installs the sync agent's point, and
§1j.4 already measured the extrapolation identity to under 3e-4 u over 34 transitions.
**What is genuinely new:** that the source is the *other world copy* with the extrapolation
term **measured** — §1g.3 explicitly recorded this as NOT DETERMINED from a v4 capture —
plus the per-record attribution of all 11, the arithmetic closure, and §1t.4's recall gap.

---

### 1t.3 The operator: RIGHT IN DIRECTION, and the literal claim is NOT confirmed

**This is where the first lane over-claimed and the skeptic caught it, and the correction
matters because it is the difference between two different lines.**

The lane measured perpendicular distance to the **sync copy's own velocity ray** — got
0.0001 u — and reported it as confirmation of *"a straight line toward the destination
from my original starting position"*. **Those are two different lines.**

**The capture holds the operator's actual line and the lane never used it.** `mapfindpath`
records `pt_a` (query start) and `pt_b` (query end); 14 of 15 come from `chcli_point`'s
`0x0081AF56`, paired 1:1 with the 14 clicks. **Operand check: `pt_a` equals the local
copy's `m_point` at the click to 0.0 u on 14 of 14**, so `pt_a` *is* "where I was when I
clicked" and `pt_b` *is* the destination.

Perpendicular from **that** chord: **1.5, 10.4, 13.6, 37.5, 38.4, 40.0, 49.2, 122.2,
264.9, 555.9 u** — 3 of 10 within 32 u, **median 39 u, max 556 u**. That is not "on the
line", and it barely improves on the orchestrator's first 2-of-11 attempt.

**But the operator is not scored wrong, and the mechanism explains the perception exactly.**
Paired **within event** — same body, same chord, milliseconds apart:

| | perpendicular to the click chord |
|---|---|
| **before** the yank | 3.4, 37.5, 310.9, 356.5, 395.2, 444.1, 555.6, 606.5, 661.9, 942.7 u |
| **after** the yank | 1.5, 10.4, 13.6, 37.5, 38.4, 40.0, 49.2, 122.2, 264.9, 555.9 u |

**8 of 10 move TOWARD the chord; the median falls from ~420 u to ~39 u.** The reason is
structural: the snap puts the body on the **server's copy**, and the server's copy sits
about **3× closer to the straight line** than the local copy does (SYNC p50 156 u against
LOCAL p50 516 u), because it has no path solver and walks straight at whatever we grant.

**So the correct labels are:** *landing == the sync copy's extrapolated position* is
**OBSERVED and exact**; *"put into place as if I'd run a straight line"* is **SUPPORTED IN
DIRECTION, not confirmed as landing-on-the-line**. The operator described the direction of
a real effect and the sensation it produces; the geometry is "yanked onto the server's
copy, which is much straighter than your route was."

**The CORNERED half (claim 1) is CONTESTED at this n.** A de-circularised instrument
(local max perpendicular from the click chord using only samples *before* the warp) gives
warped p50 444 u against control p50 243 u — overlapping, and the control max exceeds 5 of
9 warped rows. **10 warped clicks against 4 control clicks is too few.**

**A test that does NOT work, recorded so it is not quoted:** path tortuosity of the local
copy before each snap looked like a refutation (reseed p50 1.00 vs control 1.28) and is a
**sampling-density artifact** — reseed windows hold 3–7 samples and controls hold dozens;
matched on sample count both give p50 1.00. **NOT-MEASURABLE-BY-THIS-METHOD.**

---

### 1t.4 THE DETECTOR UNDER-COUNTS, and the backstop is free

**OBSERVED.** `SetPosition`'s direct-write branch calls `agtrack` **unconditionally** at
`0x00602BBD`, so every unstamped `m_point` write returns to `0x00602BC2` and is countable
with no threshold. That census finds **15**; the displacement detector finds **11**.

Two of the four are genuine misses (**#3656 and #5338**) that escaped because the stamp
*happened* to advance across the record gap. Both moved the body **opposite to its own
declared heading** — `v = (23.22, 287.06)` against motion `(−9.53, −116.83)`, dot −33,758;
and `v = (−0.83, −271.29)` against motion `(0.44, 142.61)`, dot −38,691. That form needs
no target and no extrapolator, which matters because both landing records carry
`target = (inf, inf)` and a distance-to-target computed there is not computable at all —
the lane published one and its own next sentence contradicted it.

**The true relocation total for this run is ~7,055 u over 13 events, not 6,418 u over 11.**

**Why the detector is structurally blind:** **47.4% of local-copy record gaps
(1,620 of 3,417) have the stamp advancing.** It cannot see a warp there. It does not bite
for the reseed-driven class *only* because `reseed` is itself hooked and the denominator
closes at 13 — a reason the lane never gave. `readhook` now prints the census beside the
count as an explicit **recall** check.

---

### 1t.5 The fence suppresses almost nothing, and "shut" is mostly the POST-SNAP state

**OBSERVED.** Of the 47 shut invocations, **43 sit on a world-1 agent** that `0x00606016`
diverts regardless. **The fence prevented exactly 4 desync tests of the 161 that would
otherwise have run — 2.5%.**

And "shut" is overwhelmingly a *consequence* rather than a cause: **37 of 47** shut
invocations land within 100 ms of a gated reseed, against **45 of 1,867** open ones
(Fisher one-sided **p = 8.5e-46**). `agtrack` clears the roster's `clientControlled` on its
own snap branch, so most of what a sampler would have called "the fence suppressing" is the
client having just snapped.

**That closes §1s.8 item 1 in the direction it suspected.** The killed "suppression buys
~3×" finding was a sampler reading post-snap state; read at the decision, the fence is
worth 4 tests in 1,914 entries.

---

### 1t.6 Three defects of ours this run exposed, all now fixed

1. **The v6 fields were captured and never PRINTED.** The fence, the facing and the gate-3
   split were written correctly into the record and no report section existed, so the run's
   five registered predictions had to be scored out of a scratchpad script while the readout
   said nothing. **A field captured and never reported is a field the run does not have.**
   `readhook` gained four v6 sections; `test_movehook.py` §14 now requires the *report* to
   print them, with a v5 control that requires it not to — round-tripping a field cannot
   catch this.
2. **The chain test pooled the two world copies.** It printed **25/124** on this capture;
   per object it is **4/66 (local) + 31/57 (sync) = 35/123**. Every "did not chain" row
   across that seam compares one copy's target with the *other* copy's next point and is
   guaranteed not to link. The line then read the total out as *"candidates for a real
   divergence"*. **This is §1i.1's id-pooling defect arriving in a second place**, and it
   also silently changed K2's figure (11/34 → 14/33) when fixed.
3. **The displacement attribution named a position, not a cause** (§1t.2).

---

### 1t.7 What else the run says

* **The teleport is exonerated a THIRD time.** Extrapolating `m_point` by velocity to the
  arrival tick against `m_targetPoint`: **p50 0.13 u, max 0.29 u over 125 samples**
  (run 3: p50 0.1, max 0.3, n=42). It is the ordinary arrival mechanism.
* **`WORLD_SYNC == 0` is now read DIRECTLY from the record** — `src_world == 0` on 157 of
  157 snaptest rows. §1i.7 listed this as identified only from call-site structure; that
  item is **closed**.
* **Our grant cadence is now essentially retail's.** Sync-copy grant gaps p50 **0.86 s**
  against retail's 0.82 s, and **3.57 grants per 1,000 u** against retail's p50 4.30 and
  floor 1.70 (§1i.4 measured **1.40** and called it below every one of 118 live agents).
  **The starvation §1i named is fixed**, and the residual is not cadence.
* **P1a replicates a fourth time:** 3 of 1,776 bakes glided (0.2%), all from `0x00600B0F`
  (avoidance), against 1.2% and 1.5% in runs 3 and 5. No unknown bake caller in ~3,700
  bakes across five runs; MOVECODE-Q4 holds.
* **MOVECODE-Q2 bites again, at NEW coordinates.** `pathdiff` returns **3 of 15 OFF-MESH
  (20%)** on map 280, at `(−4926.6, 3765.9)`, `(−10475.9, 4400.2)` and `(−6749.2, 6211.4)`.
  §1h.4 bounded the hole to y ≈ 6,900–8,500; **two of these sit well below that**, so the
  region is larger than the bound, not confirmed by it.
* **The no-clip row is SCORED for the first time in five attempts.** The operator reports
  clipping is still present under `--click-echo`. That is the known residual (§1n.2), and
  it is now a recorded observation rather than a fifth deferral.

---

### 1t.8 What is NOT settled

* ~~**WHICH caller produced the two missed `SetPosition` warps**~~ — **the site is BUILT
  as of 2026-08-28, and it is one row rather than the two this line asked for.**
  `0x00604A50` and `0x00606394` **cannot be hooked**: both are `e8 call 0x602b20`, first
  byte `0xE8`, and `gensites` refuses anything that is not `55`. That is the same mistake
  §1s.9 made three times — *naming a call SITE when the question is "which caller"*.
  **The callee is the answer.** `SetPosition` `0x00602B20` **is** a `push ebp` entry with
  **7 direct callers** (`0x005FDAE5`, `0x005FDB49`, `0x005FF74B`, `0x00602369` = reseed,
  `0x006028FF`, `0x00604A50`, `0x00606394`), and the record already carries the return
  address — so one hook names whichever fired, including **five this arc has never
  observed**, and `deref_arg_a = 1` captures the point being installed so the landing is
  measured at the write instead of inferred from the next record. Rowed in
  `content/movecode.toml`, `sites.h` regenerated (14 sites, all `0x55`), DLL rebuilt.
  **UNRUN.**
* **Operator claim (1), the cornered trigger.** 10 warped clicks against 4 controls, groups
  overlapping. Settling it needs a run that logs the client's solved path.
* **Why `agtrack` snapped on 11 of 157 tests when 37 exceeded gate 1's 299.33 u cut.** An
  entry hook cannot see which gate the function took, and gate 3 fired once.
* **Gate 3's AGENT half is still unexercised.** One agent id and two objects in the whole
  capture; there is nobody to crowd with.
* **Whether `0x005FCAA0` is wire-reachable** — unchanged from §1s.10, and its third caller
  `0x004E6E82` is still uncharacterised.
* **Why `ptime` advanced 774 ms across #5332 → #5341** on a body that had already arrived.
  It does not touch the 11, but "ptime only advances on walk-commit" is not fully closed.

---

## 1u. MOVECODE-R3 — **the run is UNSCOREABLE, my runsheet is why, and the keyboard rival is back**

**OBSERVED, 2026-08-28.** Map 280, `--click-echo`, **2,709 records, v6, 14 sites**, both
controls FIRED, 268 s. Capture `vault/research/movecode/r3/`, log
`authsrv-20260828T162424-c1.jsonl`. Three analysis lanes, each attacked by a skeptic:
**two HOLDS-WEAKENED and one REFUTED — the refuted one being the lane whose headline I
had already reported.**

The operator's own design, which turned out to be better than the one the runsheet asked
for:

> *"10 cornered clicks, with WASD moves after arriving on clicks 4, 6, and 10. 10 open
> clicks, with WASD moves on 14, 16, and 20. then 4 W-interrupted corner clicks. the
> final one warped me, and i closed the run"*

---

### 1u.1 R3-P2 is UNSCOREABLE, and pooling with R2 does not rescue it

**The floors govern and three were missed** — clicks 27 of 30, **displacements 1 of 8**,
`setposition` 2 of 10. `RUN-R3.md` §2 says in terms that such a run *"measures nothing
and must be re-run, not reported through."* It is not reported through.

**Pooling with R2 was the obvious rescue and it is arithmetically impossible.** The exact
stratified test conditions on each run's arm sizes *and* its number of warped clicks. R2
contributes one CLEAR click; R3 contributes one warp. **The smallest attainable one-sided
p, computed from the margins alone before looking at any outcome, is 0.0839** — 0.1376 if
OFF-MESH folds into BLOCKED. **The pre-registered p ≤ 0.05 was unreachable under every
possible outcome**, so no result this pass could have produced would have counted.

**And naive pooling would have printed p = 0.0233.** That number is a Simpson artifact
end to end: run predicts outcome (R2 82% of clicks warped against R3's 4%, p = 4.1e-06)
*and* predicts exposure (R2 91% BLOCKED against R3's 46%, p = 1.4e-02). Stratified by run
it becomes **p = 0.5594**. Neither run shows any within-run effect at all — R2 alone
BLOCKED 8/10 against CLEAR 1/1 (p = 1.0), R3 alone 1/12 against 0/14 (p = 0.4615) — and
the per-run odds ratios are **0 and infinity**, so Breslow–Day is not computable, which is
itself the finding.

### 1u.2 THE RUNSHEET SET TWO FLOORS THAT CANNOT BOTH BE MET. That is my error, not the operator's

`RUN-R3.md` §2 asked for **≥ 30 clicks** *and* **≥ 8 displacements**, and §4 prescribed a
**click-dominated** walk to get the clicks. Measured per-click warp rates:

| regime | warps per click | 95% CI |
|---|---|---|
| R2 (keyboard-interrupted throughout) | **11/14 = 78.6%** | 49.2–95.3% |
| R3 (click-dominated, as prescribed) | **1/27 = 3.7%** | 0.09–19.0% |

**At the rate the prescribed walking style produces, 8 displacements needs ~216 clicks**
(CI 42–8,536). The runsheet asked for 30. **The walk did exactly what it was told and the
design could not fill its own outcome floor in eight minutes.**

Keyboard density is the mechanism: R2 ran 1,615 `chcli_dir` over 175 s (**9.21/s**, every
one of its 14 clicks key-exposed), R3 ran 350 over 262 s (**1.34/s**, with **15 of 27
clicks carrying zero keyboard**). I asked for the arm that does not warp and then
required warps from it.

**The lesson is not "ask for more clicks".** It is that an outcome floor and an exposure
prescription have to be checked against each other *before the run*, using whatever rate
the prior run already measured. That check costs one division and it was not done.

### 1u.3 What the run DID buy: the classifier is validated, and the operator's own labels are recoverable from the bytes

**CORROBORATED, and this is the durable result of the pass.** The CLEAR/BLOCKED
classifier — `pathmap.clip(pt_a → pt_b)` over `mapfindpath`'s recorded endpoints — agrees
with the operator's eye-labels on **23 of 24 mapped clicks (95.8%)**, Fisher p = 5.6e-06.
A 20,000-permutation label shuffle puts **P(agreement ≥ 23/24) = 0.00000** against a
shuffled median of 13/24. The two methods share nothing: one is geometry over ArenaNet's
pathing chunk, the other is a person looking at a screen. Both disagreements are named —
one genuine miss (a 3,296 u click the operator called cornered and our mesh says is
clear), one OFF-MESH destination, which is our decode gap rather than a statement about
the client.

**And a second, independent instrument recovers the operator's click NUMBERING.** He
named WASD on clicks 4, 6, 10 and 14, 16, 20. The clicks carrying any `chcli_dir` in
window are **exactly [4, 6, 10, 14, 16, 20]** — 6 of 6, no false positives, P by chance
within the two blocks **6.9e-05**, and `chcli_dir` played no part in building the mapping.
The same instrument separates his two keyboard treatments without being told they differ:
**WASD-after-arriving starts +5.6 to +20.7 s after its click; the W-interrupted tail
+2.3 to +5.9 s.**

**Exposure, corrected.** R3 is **14 CLEAR / 12 BLOCKED / 1 OFF-MESH** — my first readout's
"14/13" folded the OFF-MESH row into BLOCKED. R2 is **1 CLEAR / 10 BLOCKED / 3 OFF-MESH**,
which is why R2 cannot supply a control arm: *it has one*.

### 1u.4 §1i's starvation story is NOT refuted — the lane that said so made a LEVEL ERROR

A lane reported *"§1i's starvation story is REFUTED AND INVERTED"* and its skeptic killed
the framing. **§1i is a RUN-level claim** (grants per 1,000 u below retail's floor, so the
twin falls behind); the lane's evidence is **event-level**. The run-level test the lane
never ran, over its own 8-run corpus: grants/1000u against warps-per-snaptest
**rho = −0.476** (perm p 0.241), against warps-per-grant **rho = −0.429** (p 0.301) —
**both carrying §1i's own sign**, neither significant at n = 8. The one positive
correlation shares the path denominator on both axes and is the spurious-ratio artifact.

**Correct label: NOT FOUND / UNDERPOWERED. §1i stands, unconfirmed and unrefuted.**

**What does survive, and it is a real refinement.** Warps cluster immediately after
grants — **32 of 40 gated reseeds across eight runs fire within 500 ms of one**,
Poisson-binomial P(≥32) = 1.23e-17, every figure reproduced. But against the *correct*
null — warps as a random subset of snaptests rather than of wall time — the enrichment is
**zero**: 80.0% of warps are grant-adjacent against 79.5% of snaptests, exact p = 1.0.

> **The grant SCHEDULES the desync test; it does not raise the per-test failure rate.**
> Warp count therefore scales with test count, not with grant scarcity.

That also dissolves the 11× drop without needing a new mechanism: R3 granted 55 times
against R2's 104, so it ran fewer tests. And the drop is **not denominator-robust** —
on `agtrack` invocations (a clean single-object per-invocation exposure, verified to fire
on exactly one `ecx` in every run) R2's 11 against R3's 1 gives **p = 0.31**. The lane
reported only the two denominators giving p < 1e-3.

**A factual correction that reaches the server side:** our server did **not** grant zero
clicks. Under `--click-echo` it echoed **12 of 14** refused clicks in R2 and **22 of 24**
in R3, verbatim (`authsrv.py:16883`, `fired=True, geo-stale`).

**A check that could have failed eight times and did not:** the sync-copy setter count
equals the server's own `0x0029` send count **1:1 in all eight runs** — 13, 18, 21, 30,
46, 104, 55, 51.

### 1u.5 The keyboard rival is NOT refuted. On the least-arbitrary denominator it is the factor that separates

A lane reported the keyboard trigger REFUTED — *"30 bursts across 121.3 s of click-idle
time produced ZERO displacements against 4.61 expected, Poisson P(0) = 0.010"* — **and I
repeated that headline before its skeptic returned.** It does not survive, three ways:

1. **The denominator is wall seconds**, which the lane's *own* claims 2 and 8 separately
   prove is the one thing this instrument's density cannot support (record density tracks
   input: R2/R3 time-normalised site ratios run 4.7–6.9 on input-driven sites). The lane
   refuted its own headline twice and did not connect the claims.
2. **The zero is FORCED by window selection.** With `active = [click, click+W]`, a
   displacement is idle iff its lag exceeds W. Pooled lags top out at **6.30 s**; the lane
   chose **W = 10 s** and cited that 6.30 s as evidence the window was *not* tuned. Any
   W ≥ 6.30 s makes the idle arm zero with probability 1. Its own script docstring writes
   the tell out loud. **Click-idle exposure of the settled mechanism's own sites is
   literally zero** — `reseed` 0/15, `setposition` 0/2, `setter@0x0060244D` 0/14. That is
   a zero-exposure vacuum, the **seventh** in this arc.
3. **No minimum detectable effect.** The test can only reject a standalone keyboard
   potency ≥ ~65% of the click-active rate.

**And the sign reverses on an honest denominator.** On a structural, non-outcome-selected
opportunity set (either record from `teleport`/`reseed`/`setposition`; n = 107, 12
movers): **keyboard in-hold 11/31 against 1/76, Fisher < 0.0001**, stable across hold
windows from 50 ms to 2 s, and **within R2 alone Fisher 0.0119**. On that same denominator
the **click factor does not separate** — pooled 12/87 vs 0/20 (p = 0.1173), R2 alone
(p = 0.5602). The lane's ratio of 1.05 is one endpoint of a range running **1.05 → 2.20 →
11.0** as structurally-impossible pairs are removed; 92% of its denominator was
`setter→bake` pairs that have never moved a body.

**Correct label: NOT-MEASURABLE on this corpus, and still live.** Not refuted.

**Two further things that outrank the corner.** In the per-click 2×2, the best-scoring
factor is the keyboard one (`interrupt` 11/20 vs 0/21, **p = 0.0001**) and the next is
plain **distance** (≥ 2500 u: 10/22 vs 1/19, **p = 0.0048**), both beating corner
(p = 0.0335) — **and corner is 71% collinear with distance**, agreeing on 29 of 41 clicks.
There is a CLEAR click at 3,318 u that warped 282 u.

**But none of it is separable from the RUN**, and that is the honest bottom line: **every
un-interrupted click in the corpus is an R3 click.** Corner, distance and keyboard are
mutually confounded with each other and with the run.

### 1u.6 What the next run needs — and it needs an INSTRUMENT change first

**The design (from L3, upheld by its skeptic as the most valuable thing it produced):** a
**2 × 3 factorial**, **distance held in a narrow band (1,800–2,200 u)** so it cannot proxy
for corner, three keyboard levels (**none / after-arrival / interrupting**), **INTERLEAVED,
not blocked** — R3's block structure is what made phase and factor inseparable — and
**~20 clicks per cell**. At R2's interrupted rate that is a few minutes; at R3's
click-only rate the *no-keyboard* cells will produce almost no warps, which is the point:
**that cell is the control and its emptiness is the measurement.**

**The prerequisite, and it is why another run should not be booked yet.** Every
disagreement in this pass reduces to the same thing: **the hook has no input-independent
sampling backbone**, so the denominator can be chosen to give either answer, and both
lanes chose one without a sensitivity analysis.

**The fix is available and it is one row.** The movement tick `0x00600140` is a
`push ebp` entry (re-read from the pinned image 2026-08-28: `55 8b ec 83 ec 2c 53 56`).
It runs per agent per frame regardless of input, which is exactly the missing
denominator — **and hooking it simultaneously answers §4 item 2**, which has stood open
since B1: the tick is a C++ virtual with **0 direct callers**, reached only through
`call dword [reg+4]`, and §4 says in terms *"a breakpoint reading the return address
settles it in one run; static analysis will not."*

**Costed honestly, because it is not free:** at ~30 fps over two agents, an 8-minute
capture would write ~29,000 records into a 32,768 ring and truncate everything else. R3
used 2,709. So the tick site wants a **short capture (2–3 minutes)**, or a stride, or its
own run — and `readhook` already reports ring fill, which is the number to watch.

### 1u.7 Corrections to the record from this pass

* **`readhook`'s per-site table prints LIVE addresses, and record `retaddr`s are LIVE
  too** — both rebase by `(− cap.base + 0x00400000)`. I briefed three lanes that retaddrs
  were already static; `pathdiff.py`'s own `reb()` had it right all along. Combined with
  the call-vs-return off-by-five (`0x00602369` vs `0x0060236E`), this is **two distinct
  address-space traps in one readout**, and both produce the same symptom: every known
  caller reported as unknown.
* **R3's exposure is 14 CLEAR / 12 BLOCKED / 1 OFF-MESH**, not the 14/13 first reported.
* **R3-P1 is UNSCORED, not refuted** (2 records against a floor of 10). Both returned to
  `reseed`; the other six callers did not fire, which is a fact about the walk.
* **R3-P3 is CONFIRMED** — the captured `arg1` equals the landing to **0.000 u** on both
  records, so the landing is measured at the write rather than inferred.

---

## 1v. MOVECODE-R4-A — **the tick is NOT a frame clock (P1 refuted), AgTimer IS its dispatcher (P2 answered, correcting §4), and I crashed the client getting here**

**OBSERVED, 2026-08-28.** Map 280, 161.5 s, **3,664 records, 15 sites**, both controls
FIRED, ended by `--stop`. Capture `vault/research/movecode/r4a/`. Run A was the
instrument-only run [RUN-R4.md](RUN-R4.md) §1 requires before the experiment.

### 1v.0 FIRST: the crash, because it was ours

The first attempt at this run **crashed the client** — `c0000005`, seconds after arming.
The stride added for the tick was written as

```c
if (SITES[i].stride > 1u && ((nth - 1) % stride) != 0u)
    continue;
```

directly above the `push ebp` re-emulation at the bottom of the same loop, **whose own
comment reads *"This must happen on every hit — a skipped prologue is a corrupted frame,
not a missing sample."*** `continue` leaves the for-loop, so on a strided-out hit EIP never
advanced past the `0xCC` and the caller's frame was never built. At stride 64 that is **63
of every 64 hits** on a site that fires for every agent.

Fixed by gating the *record* rather than jumping past the *emulation*. **Nothing in the
suite could have caught it**: §7 injects the real DLL into a throwaway `cmd.exe` where
every site deliberately **fails to arm**, which is the property that section tests — so the
handler's hot path is never executed by any test, and a behavioural test needs the vaulted
client, a live process and an armed breakpoint. `test_movehook.py` §15 now checks the
property **structurally** (no `continue`, `break` or stray `return` between the address
match and the emulation) with a control that plants the exact crashing statement.

Nothing persists: the hook patches process memory, never the file on disk.

### 1v.1 R4-P1 REFUTED — the tick fires 0.62/s, not ~60/s

**97 hits over 156.2 s.** A per-agent-per-frame update over two agents at 30 fps predicts
~60/s. **It is off by a factor of ~100**, and the floor (≥ 5,000) is missed by 50×.

| site | hits | tick / site |
|---|---|---|
| `teleport` | 72 | 1.35 |
| `snaptest` | 111 | 0.87 |
| `chcli_point` | 103 | 0.94 |
| `bake` / `setter` / `agtrack` | 689 / 688 / 771 | 0.13 |

**So the tick is an ARRIVAL TIMER CALLBACK, not a per-frame update** — which fits the
mechanism the arc already decoded and did not join up: its arrival test at `0x006001EB` is
`now == +0x48`, **exact equality**, and an exactly-equal time test is only sane if the
function is *scheduled for* that tick rather than polled every frame. §2.1 and §4 item 2
both call it "the movement tick" and §4 says it "runs several times a second"; **that is
wrong, and this run is what says so.**

**The consequence is the one that matters and it is negative: §1u.6's instrument
prerequisite is NOT solved.** The tick was added to be the input-independent sampling
backbone every denominator dispute in §1u reduced to. Arrivals are input-driven, so its
rate tracks player activity exactly like every other site here. **No per-frame site is
known, and the denominator problem is still open.**

*The row is corrected in `content/movecode.toml` and its stride removed — 1-in-64 stored 2
records of 97 and cost §1v.2 most of its evidence. The stride MECHANISM is kept because a
genuine per-frame site would need it, but no site uses it today.*

### 1v.2 R4-P2 ANSWERED — and it REFUTES §4 item 2's exclusion

**Both stored tick records return to `0x006040EA`.** That is `0x006040E7 + 3`, and
`--dis 0x006040E7` reads `ff 50 04  call dword ptr [eax + 4]` — **inside
`AgTimer::Advance` `0x00603FE0`.**

§4 item 2, open since B1, says the tick is a virtual whose dispatcher `--xrefs` cannot
name, that "a breakpoint reading the return address settles it in one run", and that
**`AgTimer::Advance` "is the obvious candidate and is *ruled out*, because it dispatches
slot 1 with no pushed args (`0x006040E7 call dword [eax+4]`, no `add esp`) while the tick
is `ret 8`."**

**The exclusion is refuted by the capture.** The obvious candidate was right; the static
argument that killed it was not. §4 item 2 is otherwise vindicated — only a breakpoint
could have settled it — and it is now **CLOSED**.

*n = 2, because the stride discarded the other 95. The two agree, the arithmetic is exact,
and the site is now unstrided so the next run gives ~100.*

### 1v.3 What else the run holds — and a mesh-selection trap worth carrying

* **10 displacements** on the local copy, 13 reseeds, 14 `setposition`, 72 teleports.
* **103 clicks and 116 planner queries** — by far the click-richest capture in the arc
  (R2: 14, R3: 27).
* **`stepclear` fired 9 times**, against R2's 4 and R3's 2.
* **THE MESH SELECTOR PICKS THE WRONG MAP HERE, and it is not a tie.** Scoring the 1,478
  sampled agent positions against every mesh in `content/maps.toml`, **Sparkfly Swamp
  (287493) wins at 0.962** against map 280's 165811 at **0.947**. The run is map 280 —
  the first captured position is `(−6036.0, −2519.0)`, its committed spawn, to the decimal,
  and the server log says so. `HANDOFF-WARP.md` warns that "two meshes tie"; **it is worse
  than a tie, the wrong one can win**, and the spawn coordinate is the anchor that settles
  it. The positions run to x = +11,860 because the operator explored far more of the isle
  than R2 or R3 did, which is what widened the coverage overlap.

### 1v.4 THE OPERATOR HAS A DETERMINISTIC NO-CLIP REPRO, and that is the most valuable thing here

> *"was able to easily repro a no-clip walk by clicking around a corner then clicking again
> after a short delay (~1s). that would put me in a straight line path towards the point i
> clicked, through or over terrain/props"*

**The no-clip row has been UNSCORED four times** (§1n.2, §1p.10 item 2, §1r.6, §1t.7) and
§1r.6 built an offline detector for it that **failed its own positive control** — the arm
that should have been clean scored *higher* than the arm the operator watched no-clip in.
Its diagnosis was that `movehook` samples on solver events, so a whole run yields only
134–571 usable chords at a ~1% base rate: **n = 1–2, which is no power at all.**

**A deterministic repro changes what is possible**, because it supplies the known-positive
class the detector never had. And this capture contains it: of 103 clicks, **84 are the
second click of a pair issued within 2.0 s of the first**, and the operator says the
manoeuvre reliably produces the walk-through.

**This is also the mechanism the arc already predicted from two directions and never
measured.** §1n.2: the sync copy has no path solver, so under `--click-echo` it walks the
**straight line** to whatever it is granted, and the reconcile puts the body on that line.
§1n.3 called the residual "worse in kind" than the warps it replaced. §1o.3 recorded the
operator's earlier report that "double click has even worse behaviors, clipping into the
ground". **Retail's own contract has a rule about exactly this shape** — `REALFIX` §0.15's
"the older click of a rapid **pair** is dropped outright" — and §1p.9 flagged that
`authsrv.py` generalises that pair rule into a single-click rule it does not state.

**Status: UNVERIFIED here.** What is OBSERVED is the repro's existence, the operator's
description, and 84 rapid pairs in a capture on the right mesh. Scoring it is the next
piece of work and it is the first time it has been tractable.

---

## 1w. THE NO-CLIP — **§1w.1's "it is not a walk" is WITHDRAWN. Read §1w.7 FIRST**

> **CORRECTED 2026-08-28, hours after it was written, by the operator.** This section
> concluded "the body does not WALK through geometry, it is PUT there", on a detector
> that reported **561 walked samples with zero off-mesh**. The operator's reply:
>
> > *"the main thing i intentionally triggered a few times was me no clipping through
> > props and walking on the base terrain only. i.e. instead of walking around a
> > mountain i would walk through its faces onto the base terrain underneath, walking
> > in a straight line towards the second click. not a glide, not a jump, just a
> > wall/mountain/corner/etc ignoring terrain walk"*
>
> **That is a sustained WALK, deliberately triggered, several times — and the detector
> said it could not have happened.** §1w.7 is why: the instrument was plane-blind, so is
> every line-level primitive in `pathmap`, and underneath that our navmesh **does not
> contain the mountain at all**. The zero was structural, not a measurement.
>
> **What survives unchanged is everything about the INSTALLS** (§1w.1's table, §1w.2's
> controls, §1w.4, §1w.5). What is withdrawn is the exclusive claim — "installed, NOT
> walked" — and the "zero walked off-mesh" it rested on. This is the third time in this
> arc the operator has contradicted a metric and been right.

## 1w-orig. The reseed INSTALLS the body inside geometry — which is true, and is not the whole story

**OBSERVED, 2026-08-28**, from `vault/research/movecode/r4a/` (R4-A, §1v) and its server
log. No new run. Two lanes, each attacked by a skeptic: **one HOLDS-WEAKENED, one
REFUTED**, and in both cases **the skeptic's work is better than the lane's** — one found
the correct operand sitting in the record the lane had searched around, the other found
the lane's headline was an unpowered null contradicting the operator.

The row this scores has been **UNSCORED four times** (§1n.2, §1p.10 item 2, §1r.6, §1t.7).

### 1w.1 The answer, and it collapses two defects into one

> **SUPERSEDED 2026-08-28 by §1x.5.** The quote below and the table's walked row are
> refuted: the lane's own scorer, run verbatim from disk, prints **walked 569, off-mesh
> 14 (2.5%), max depth 435.6 u** — and the committed 561/95 split does not regenerate
> (the disk script prints 569/87), so the table's provenance is broken. The INSTALLED
> row stands. §1x.5 has the decomposition of the 14.

> ~~**The body does not WALK through geometry. It is PUT there.**~~

Attributing every sampled position of the displayed copy by whether it was reached by
walking or written by the reseed chain:

| | n | off-mesh | depth |
|---|---|---|---|
| **walked** | 561 | **0 genuinely** | — |
| **installed** | 95 | 21 | median **239.1 u**, max **390.7 u** inside blocked ground |

**There is no walked off-mesh excursion in this run at all.** The lane reported one —
10 frames, 156 ms, "2.0 u depth" — and its skeptic killed it outright: `nearest_walkable`
finds walkable ground **0.000023–0.000199 u** away on all ten frames. It is `walkable()`
failing a float boundary test while the body walks *along a trapezoid edge*, and the
"2.0 u depth" was the floor of a home-rolled ring search that starts at r = 2.0 — **an
instrument's minimum reported as a measurement, with a justification invented for it.**
The repo ships `nearest_walkable`; one call would have shown it.

**Relocation landings are off-mesh at 6 of 10, against 10 of 96 control episodes
(p ≈ 6.9e-4).** *(The lane published 3.4e-7 by counting 636 autocorrelated 16 ms frames as
independent trials — three sentences after correctly refusing to do exactly that elsewhere.
Clustered, it is 6.9e-4, stable 3.6e-4–9.1e-4 over a 250 ms–5 s sweep.)* **It is not a hole
in our mesh:** walk samples within 1,500 u of a landing are off-mesh at 4.6%.

**So the no-clip and the warp are the same defect wearing two faces.** §1t.2 established
that a gated reseed installs the sync copy's dead-reckoned position through `SetPosition`;
this shows **where** that lands — inside props and terrain, because the sync copy has no
path solver and walks the straight line (§1n.2). The arc has been treating "warps to spawn"
and "walks through walls" as two harms to be traded off (§1n.3). They are one mechanism.

**The committed formula does this better than either lane did.** §1t.2's
`landing = src_point + src_vel × (ptime − src_ptime)/1000`, read straight off the reseed
record's own `src_*` fields, gives **13 of 13 under 1 u, median 0.000110 u** on this
capture, and passes its vacuity control here (non-reseed snaptests: 0 of 14 under 1 u,
median 71.86 u). The lane instead searched a ±3 s window over the sync *object* with an
argmin, got 9/10 within 16 u, and needed a guard **because the window is the free parameter
its "zero free parameters" claim denied**.

### 1w.2 What the detector can and cannot do — and why §1r.6 failed

**The positive control §1r.6 never had now exists and it PASSES.** The sync copy walks the
straight line *by construction*, so it must score dirtier. It does: on chords ≥ 100 u,
**local 2/51 against sync 9/52, p = 0.028**; length-standardised, **4.7×**.

*(The lane led with "38×", which is the chord-length confound the brief had named as
probably dominant: 86% of local chords are under 32 u — median 4.9 u — where nothing can be
blocked, against a sync median of 173 u. The real separation is 4–5× on n = 103, not 38× on
n = 605.)*

**And this explains §1r.6's failure.** Its control pair was `k1-treatment` against `k2` —
**both of them client-pathed bodies**. It was comparing two arms of the same class, which is
why the arm that "should be clean" scored higher. The discriminating contrast is not
policy-vs-policy, it is **walked-vs-installed**.

**The rapid-pair contrast the runsheet asked for is NOT-MEASURABLE.** 541 scored chords
carry **k = 2** blocked, and with the walked arm now at **k = 0** no design reaches any
p at all. Sweeping gap bands and window lengths gives 18 cells whose *best attainable*
one-sided p ranges 0.032–0.409 — **one of eighteen could ever have cleared 0.05.**

**A statistical control that FAILED, reported instead of its p-values.** A circular-shift
permutation of the click series cannot detect a time-lock that must exist: with 103 clicks
in 156 s and windows covering 20–50% of the run, a random shift lands nearly the same
exposure. Every shift p-value computed in that lane is uninterpretable and **none is quoted
here.** That was the best methodological move either lane made.

### 1w.3 NOT SETTLED: whether the operator saw a glide or a jump

Two reseeds (t+130.188, t+131.172) move the body **572.3 u and 275.3 u through blocked
ground at exactly 288 u/s on the stamp clock — but inside ONE wall-clock tick.** Which
clock is real to the eye is **NOT-MEASURABLE-BY-THIS-METHOD**, and the wording "installed,
not walked" should not be read as settling it.

The related trap, and it is the fourth "check that cannot fail" this arc has caught:
"no chord is superhuman on the stamp clock" is **true by construction** — `SetPosition`
writes a self-consistent (point, time) pair at run speed, so the install *defines* itself
as walking-speed on the clock it rewrites. On the wall clock those same steps are
infinite.

### 1w.4 The rapid pair: the lane said "not the defect" and it had power 0.04

**REFUTED as a claim; the question is open and the operator may well be right.** The
lane's evidence was second-of-pair 9/32 against isolated 1/7 (p = 0.653). At those arm
sizes, **the chance of detecting an isolated rate of even ZERO is 0.04.** The design could
not have found the operator's effect if it were total.

**What is genuinely established about pairs:**

* **Retail answers both clicks of a rapid pair too** — 7 of 7 under 4.0 s in the live
  corpus, zero no-answers corpus-wide. So *answering both* is not the defect, and
  `REALFIX` §0.15's drop rule is the **keyboard-occupied cell only** — its channel-clear
  cell has both answered in 30–60 ms. §1p.9 already flagged that `authsrv.py` generalises
  that pair rule beyond what §0.15 states; this confirms the direction.
* **What differs is the CONTENT of the answer.** We grant the float32-exact clicked point
  on **55 of 55** granted clicks; retail, in the matched 1,000–4,000 u band, is **3
  verbatim to 6 part-way**. `origin_age` is not the confound (verbatim p50 1.92 s against
  part-way 3.39 s).
* **The client re-solves every click** — 103 clicks → 103 `MapFindPath`, strict 1:1 — **and
  almost never walks the solved chain** (`chcli_advance` 22). Corroborated from a second
  direction the lane did not use: `isWaypoint = 1` on **1 of 689 bakes**, so the setter's
  own obstacle-avoidance re-bake fired **once** in 156 s.
* **The reseed warps the drawn body FIRST and installs the leg second** — all 10
  unstamped-move steps sit 0 ms from a reseed and relocate it 159.0–1,234.5 u.

**A published number that must not be carried: "click grants draw a reseed 18/55 against
1/34, p = 9.5e-4" is invalid.** The numerator 18 exceeds the **13 reseeds that exist in the
capture** — clustered click grants each get credited with the same reseed. Under 1:1
nearest-prior attribution it is **11/55 against 2/34, p = 0.12**, and the two arms are
disjoint regimes anyway (zero-lead grants are 34/34 keyboard-armed, click grants 50/55
keyboard-clear), with a zero-lead grant's destination *being* the reported body position
(|grant − body| p50 **5 u**), so it cannot desync two copies by construction.

### 1w.5 THE FINDING WITH A LEVER ON IT: `D1_LEAD` was OFF, so the hold built for this was inert

**OBSERVED, from source.** `authsrv.py:17000`'s outstanding-answer hold carries
`and D1_LEAD`; the flush at `:6609` is `if D1_LEAD and (...)`; and the arming stamp
`state["a2_click_answered_at"]` is written inside `if D1_LEAD:` at `:17114`. `--d1-lead` is
`store_true`, and **[RUN-R4.md](RUN-R4.md) §5 passes only `--click-echo --map 280`.**

**So the §0.17 hold — built for exactly this repro — was inert for the whole run**, and
every fired click grant carries `arm="click"`. That is not a proposal, it is a
configuration fact about the capture this section scores: **the run measured the policy
with its own guard switched off.**

*Per the graveyard discipline, no fix is proposed here. What is recorded is that a
mechanism intended to bound this behaviour was not running, which makes any reading of
R4-A as "the shipped policy's residual" wrong.*

### 1w.6 Status

* **The no-clip row is SCORED** for the first time: the body is **installed** inside
  geometry by the reseed, at median 239 u and max 391 u depth, 6 of 10 landings off-mesh
  against a 4.6% matched spatial control. **It is the warp mechanism, not a separate one.**
* **No walked off-mesh travel exists in this run** — the only candidate was a 1e-4 u float
  boundary artifact.
* **NOT SETTLED:** glide or jump; the rapid-pair effect (power 0.04); and whether
  `D1_LEAD` on would change any of it.
* **The instrument problem from §1u.6 is unchanged.** §1v.1 refuted the tick as a
  per-frame denominator, and this pass needed exactly that: the chord contrast died at
  k = 0–2 because position sampling is event-driven. **A timer-based position sampler is
  still the missing instrument, and no candidate site is known.**

### 1w.7 WHY THE DETECTOR COULD NOT SEE IT — our navmesh has no mountain in it

**OBSERVED, 2026-08-28.** Three nested reasons, each one enough on its own.

**1. Every line-level primitive in `pathmap` is PLANE-BLIND.** `walkable(x, y)` takes no
plane. `clip()` calls it. `_sightline()` binds `walkable = self.walkable` and calls it.
`route()`'s string-pull calls `_sightline`. **So the entire chain projects to 2D**, and
§1w.1's detector — built on `clip()` — asked "is some surface walkable at this (x, y)"
when the question was "is the body on a surface it could have reached".

**2. The record carried the plane the whole time and no detector used it.** `m_point` is
16 bytes — `float x, float y, int plane, int` — so `point[2]` is the plane. In r4a it
takes values 0 (×621), 61 (×25), 22 (×4), 24 (×3), 21 (×2). A plane-aware pass over the
same samples finds **8 of 589 declaring a plane the mesh does not offer at their (x, y)**
— e.g. seq 1047 at `(−162.3, 822.4)` declares plane 61 where the mesh has only plane 0.
Small, real, and *not* the phenomenon the operator describes.

**3. AND THIS IS THE ONE THAT ENDS THE LINE OF ATTACK: our navmesh is essentially a
SINGLE SURFACE.** Stacked geometry — more than one plane at the same (x, y) — occurs on:

| | stacked |
|---|---|
| 4,000 random walkable points in the walked region | **0.2%** |
| the body's own 589 sampled positions | **1.4%** |

`pathmap.py`'s own docstring says it in terms: on stacked geometry *"(a prop top over
terrain, a bridge over ground — **THERE IS NO HEIGHT in this file**)"*.

> **So the mountain the operator walks through is not in the navmesh as an obstacle.
> There is one walkable surface, and a straight line across it is legal at every sample
> BY CONSTRUCTION. No `pathmap`-based detector can ever score this row.**

**That explains all four previous failures at once**, and it corrects the diagnosis
§1r.6 reached. §1r.6 asked whether the mesh was too coarse to hold a prop and **refuted
that by measurement** — 2,769 trapezoids, median y-extent 44.8 u, 70.6% under 80 u,
"the mesh is fine enough". **That answered RESOLUTION. The problem is CONTENT**: a mesh
of any fineness that contains only the ground cannot say you walked through a mountain
standing on it.

**The two instruments that would work, neither of them ours today:**

* **The client's own collision** — the `PathObstacle` machinery (`PathObstacle:176
  radius >= 0`, reached from the teleport's spatial query at `0x0070A150` → `0x00722B90`,
  and the step-clearance gate `0x005FEF70` already hooked as `stepclear`). That is a
  different structure from the trapezoid navmesh and we do not decode it.
* **Terrain height.** ~~The operator's own words — *"onto the base terrain underneath"* —
  are a height claim~~ **WITHDRAWN AS THE LEAD the same day — see §1w.8.** The operator's
  correction: it is not about height, it is about OBSTACLES. Height stays on the list only
  as an instrument of last resort.

**What this means for the arc, stated plainly — REFUTED 2026-08-28, §1x:** ~~the
no-clip row cannot be scored offline with what we have~~. It can, and §1x did: the massif
is a **HOLE in the trapezoid tiling** (carved by the prop's authored outline ring), not a
second plane — this section's decisive "single surface" measurement asked about STACKING
and concluded absence-of-obstacle from it, which does not follow. Plane-blindness is
irrelevant to a hole: `walkable()` unions all 68 planes, so it over-covers, and a hole is
a hole on every plane. §1r.6's sampling-power diagnosis was right after all — the
mid-walk footage hides in 8.9–19.8 s event-sampling gaps that sit exactly over the repro
windows. Score CHORDS and outline-interior membership, not points. §1n.2 said "the operator's report is the
instrument for this and nothing else is" — that is still true, and now it is understood
rather than merely observed.

**A method note worth keeping.** Three tests were run before this was understood, and
each failed differently: **adjacency** between sampled trapezoids says 0 of 9 plane
changes are legal, which is **too strict** (event-driven sampling skips intermediates);
**connectivity** over the union-find says 6 of 6 are legal, which is **too loose** (the
map is essentially one component, so it always says yes); and **`route()`** says all nine
are straight-line legal at ratio exactly 1.00, which is **the plane-blind chain again,
one level deeper**. A clean answer from the third would have been published if the first
two had not disagreed with each other.

### 1w.8 CORRECTED, same day: not a height claim — an OBSTACLE claim. The operator's map model

**OPERATOR, 2026-08-28**, with two screenshots (client-rendered imagery — described here,
never committed; they live in the owner's screens folder, `gw077.jpg` and its neighbour):

> *"i wouldn't really call it a height claim, it just seems to be how the maps are
> shaped. ... it's not a "height" thing because you're not supposed to walk over the
> mountain either. the "base terrain" just seems to be how their maps are set up, with
> props (like mountains, walls, stairs, etc) that can either be walkable or walls placed
> upon that base terrain. and our clipping lets us walk on that. it's definitely an
> obstacle thing, that's the one worth digging into"*

**Screenshot 1:** the massif from outside — a rock formation rising off the isle's ground.
**Screenshot 2:** the body INSIDE it — upright, mid-stride on a surface that continues
under the rock, the massif's face filling the frame. Not falling, not floating: a walk.

**What this corrects in §1w.7.** Instrument 2 — "terrain height" — was this document's
framing, not the operator's, and it is withdrawn as the lead. The operator's model is:
**a base terrain layer, with props (mountains, walls, stairs) placed upon it, each one
walkable or a wall — and the no-clip ignores the PROPS while walking the base layer.**

**And that model PREDICTS §1w.7's own key measurement.** The navmesh being "essentially a
single surface" stops being a curiosity and becomes the observation that **the pathing
chunk we decode may be (or be dominated by) the base layer** — with the prop obstacles
represented somewhere we do not read. That is a hypothesis, not a conclusion; the dig is
what settles it, and it decomposes into four offline questions:

* **Q1 — decisive, cheapest.** Does mesh 165811's coverage have a **hole** at the massif's
  footprint, or is the interior covered by trapezoids we score walkable? Render coverage
  (`toolkit/mapdata/png.py` exists), overlay r4a's walked samples and its rapid-pair
  chords, compare against the isle's known shape. A hole means the detector's zero was a
  sampling artifact and clip() should be re-run on the no-clip chords; full coverage means
  the block genuinely is not in the trapezoids we read.
* **Q2.** Which trapezoid / plane-record fields does `pathmap.py` read and discard, and do
  any of them differ regionally (massif interior vs open ground)?
* **Q3.** Do prop placements (`props.py`) plus prop model files (`modelfile.py`) carry
  collision data? `Engine\Map\Path\` has nine modules including `PathObstacle.cpp` and
  `PathDataImport.cpp` ("what it imports is in `Gw.dat`" — srvtree §5), and
  `PathApi:753/754 obstacleCenter/obstacleRadius` is a shipped obstacle interface our
  `pathmap.py` has no counterpart for.
* **Q4 — client side.** What structure does the resolve at `0x0072B840` walk, who besides
  the teleport calls the spatial query `0x0070A150` → `0x00722B90`, and does the per-step
  mover consult ANY static geometry — or is retail's wall integrity purely
  (server-granted paths) + (client pathfind for prediction), so that a server granting a
  straight line gets a client that walks it without ever asking?

**Why Q4's answer matters even though the fix is server-side either way:** B3-3 Q5 already
showed the teleport's position write is never gated on the spatial query. If the WALK
stepper is the same — no static collision anywhere in the mover — then the retail client
never had wall integrity of its own, the mountain was always enforced by what retail's
server would grant, and our fix is exactly one thing: **grant paths from a mesh that
contains the obstacles.** Which makes Q1–Q3 the critical path and the four dead detectors
a closed chapter.

## 1x. THE OBSTACLE DIG — the mesh HAS the mountains, the no-clip IS scorable offline, and the client asks about geometry every step and ignores the answer

**OBSERVED, 2026-08-28**, same day as §1w.8, which posed the four questions this answers.
Four lanes + four skeptics, no new run; artifacts and every cited script preserved at
`vault/research/movecode/obstacle-dig/`. Two lane verdicts CONFIRMED, two WEAKENED — and
for the second pass running the skeptics outproduced the lanes: the decisive finding of
the whole dig (§1x.2's prop-127 result) is a skeptic's, made while refuting its lane.

### 1x.1 Q1 CONFIRMED — the mesh has holes, and the repro chords cross them

Mesh 165811 (map 280): 68 planes, 2,769 trapezoids — and **12.9% of its bounding-box
grid is interior ground with no trapezoid on ANY plane** (46.2k cells at 40 u, 24
components over 50 cells, the largest ~5,440 × 6,480 u). The skeptic re-derived the
holes with an **independent struct walk of the pathing chunk** — own tag walk, own
trapezoid decode, own containment lerp — landing within 3 cells of 358,068 (`walkable()`
cross-check 0/20,000 disagreements): **the holes are in the file, not the instrument.**

Overlaying r4a: 84 of 102 click gaps are rapid pairs (≤ 2,000 ms), and **39 of 84
rapid-pair chords are partially uncovered — 8 below 50% covered, the worst 19.3% on a
1,406 u chord — with 90% of the uncovered footage in genuine interior holes**, not
coastline (the skeptic's addition, closing the lane's own caveat). Renders:
`q1_coverage.png`, `q1_overlay.png` — the yellow chords visibly cut straight across the
black holes.

### 1x.2 Q3 — THE MOUNTAINS ARE CARVED INTO THE MESH, by authored prop outline rings

The skeptic's finding, and the dig's decisive one. Map 280 carries **665 prop
placements over 92 models; 98 placements have authored outline rings**, and **97 of 98
ring interiors are fully unwalkable in the retail mesh** (5,298 interior samples, 1
walkable). **The rock the operator walked through is prop 127** (model 28, at
(2788, 5249)): a 12-point outline whose carve the mesh follows **edge-for-edge**
(`sk_prop127_track.png` — red ring on black hole), and **28 of the 32 local-body samples
inside that outline are off-mesh with `containing()` empty on ALL 68 planes** — the
plane-blindness-immune direction.

So the operator's model (§1w.8) is CONFIRMED with one refinement: **the props' walls are
already IN the pathing data, as holes carved by their outlines.** The "base terrain" the
body walks on inside them is render-side only — the navmesh offers no surface there at
all, which is why "walking on the base terrain" and "off-mesh" are the same statement.

Two subsidiary results, both labelled: prop MODEL files also carry **collision
sub-meshes** (14 of 92 models, 69 of 665 placements, near-disjoint from the outlined
population — 1/69 overlap); whether they merge into the navmesh is **UNRESOLVED** — a
compile experiment with the measured specimen (model 24, fid 0x28535, 46 verts/156
indices, single placement at (−9389, −856)) would settle it. And the lane's own headline
clause — "the largest prop has no outline, a plausible mechanism for the repro" — was
**REFUTED by its skeptic**: that prop was never within 3,346 u of the walk, and it is
not the largest placed footprint.

### 1x.3 Q2 WEAKENED — tag 13 is a real skipped obstacle layer, and it is NOT this defect

`pathmap.py` opens only the planes tag; **tags 7/12/13/14 and plane tags 3/4/5/6/11/1
are skipped outright.** Tag 13 decodes as a per-cell CSR — count byte + wrapping-u8
prefix-sum offset (law holds 990/990 cells, re-derived independently) — indexing **167
round-collider records (107 distinct circles, r 21–70 u)**. Real, spatially structured,
fully unread. But not this defect: **0 of 1,199 body samples inside any circle, nearest
circle 701.6 u from the repro leg** — too small, too sparse, wrong places. Best current
reading (RECONSTRUCTION): the data-side face of `PathApi:753/754
obstacleCenter/obstacleRadius`, the shipped round-collider interface. Filed, not the lead.

### 1x.4 Q4 CONFIRMED — the mover consults the mesh every ~16 ms and ignores the answer

The per-step chain, every call site byte-verified on the pinned 38797 image:
`chcli_advance 0x0081B580 → agapi_setdest 0x005FC7A0 → setter 0x00602A40 → bake
0x005FE950 → 0x0070A150 → 0x00722B90` — the walker asks the pathing query **on every
advance step**. And the answer gates nothing that moves: the authoritative `m_point`
(+0x78) is **written before the query**; the query's only consumer is the +0x78→+0x68
copy; the movement read path (`0x005FFB40`) dead-reckons from +0x78/+0xB0/+0x58 and
**never reads +0x68**; and the resolve writes to a local buffer (`lea eax,[ebp-0x10]`),
so it cannot correct +0x78 through the pointer. `0x0070A150` has exactly 5 direct
callers and **zero stored VA words image-wide** — no vtable route around that census.
What +0x68 feeds is UNKNOWN (the "display copy" reading is unlabelled RECONSTRUCTION and
sits awkwardly with a display that did not freeze off-mesh; open).

> **Wall integrity on retail was never the client's. It is the server's grants.**
> B3-3 Q5 showed the teleport unguarded; this shows the WALK is too. MOVER-BLIND.

### 1x.5 The corrections this forces, owned in one place

1. **§1w.1's "installed, NOT walked" is dead; the installs stand.** The scorer on disk
   prints walked 569 / off-mesh 14 (2.5%); the committed 561/95 does not regenerate
   (569/87). The 14 decompose: **10** are a continuously-moving run t+53.59–53.75 s
   riding the carve boundary of prop 127's outline ~1e-4 u on the blocked side — §1w
   dismissed exactly these as float noise, and they are the **entry of a no-clip walk**;
   **3** sit within ±200 ms of installs; **1** is an install-straggler. Independent
   counts without the install-hold attribution: 20–25 of ~550–600 (three measurements,
   three dedup conventions, all ≫ 0). And the pair at **(3122, 6619), 113.4 u off-mesh,
   twice, 6.7 s apart, the second clear of any install** — the body STANDING inside the
   massif on render-only ground. That is the operator's second screenshot, in numbers.
2. **§1w.7's "cannot be scored offline" is refuted by this section's own scoring** —
   marked in place there. Stacking ≠ holes; plane-blindness is irrelevant to holes.
3. **A wrong committed number propagated.** Both dig briefings carried §1w's "every
   walked sample scored on-mesh" as context; both skeptics contradicted it from raw
   artifacts. Cost: none this time, because skeptics measure — but it is the
   carried-forward-constant failure again, one section later.

### 1x.6 What is settled, and the lead

**The mechanism end to end, every link now measured:** our server grants the verbatim
clicked point (55/55, §1w.4) → the client re-solves but does not drive from the solve
(§1w.4) → the granted straight line drives +0x78 → the mover's geometry consult is
non-gating (§1x.4) → the body crosses carved prop holes (§1x.1–1x.2). Retail never
shows this because retail's server grants routed part-way points — the one link in the
chain that is ours to change.

**THE LEAD: server-side path-solved grants on our own mesh — WHICH ALREADY EXIST.**
Corrected within the hour: `--router` (ROUTER-B2, `studies/movement/ROUTER.md`, owner's
2026-08-26 ruling) is exactly this, five scored runs behind it, and its arc closed on a
"mesh fidelity defect" that §1y now largely reverses. The lead is therefore not to BUILD
the router but to RUN it against the no-clip repro — [RUN-R5.md](RUN-R5.md). **The
offline no-clip detector is promoted to `toolkit/clientscan/noclipscore.py`** (validated:
reproduces §1x.1's numbers bit-for-bit). Filed behind the lead: tag 13's client-side
consumer; the collision-sub-mesh merge experiment (specimen named); +0x68's reader.

## 1y. THE POCKET FORENSICS — the router arc's "wrong-mesh" closing largely REVERSED; the router is the no-clip fix, and R5 is registered

**OBSERVED, 2026-08-28**, same session as §1x, desk-only. Trigger: §1x.6 recommended
building what already exists — `--router` (ROUTER-B2) went through five scored runs on
2026-08-26 and its arc closed on two mesh-fidelity specimens (`ROUTER.md` §10: run 4's
`dest-off-mesh` refusals "a real decode gap"; run 5's "our decode reads the player's open
ground as a pocket"). Both specimens re-examined with §1x's instruments, off the vault
logs' own coordinates (`authsrv-20260826T211820/215206-c1.jsonl`). Scripts and renders:
`vault/research/movecode/obstacle-dig/`.

### 1y.1 Run 4's refusals were CORRECT

Five of the six refused destinations are bare of any outline and 32–100 u past the mesh
edge — **inside the building footprints of §1y.2's compound**; the sixth is inside prop
505's authored outline. Clicks onto structures, refused. Not a decode gap.

### 1y.2 Run 5's "pocket" is a WALLED COMPOUND

The four clicks' direct east lines each cross exactly two ~200–290 u voids (`pocket.py`).
The terrain under band 2 carries a **Δh ≈ 500 u** vertical feature (`pocket2.py`); band 1
is at grade. The render (`edgevec.png`) shows the voids as crisp architectural footprints
— rectangles, an L/U compound, long thin walls — with 14 prop placements on and around
them, several centred on voids. **The west-then-east route (ratio 1.66) was a legal
detour around a real compound.** And run 5's own client reports never place the body east
of x ≈ −5300, so "the player walks freely east" never actually tested the bands — which,
with a non-gating mover (§1x.4), would prove nothing anyway: a keyboard walk crosses
anything.

### 1y.3 The file holds no extra walkable geometry there

A whole-chunk coordinate scan over band 1's box, with a positive control on known covered
ground (`bandscan.py`/`bandclass.py`): the only structured hit is plane 23's **tag-1
block, which decodes as the plane's boundary ring** — all 68 planes carry one, vertex
count tracking trapezoid count (`edgevec.py`) — redundant with the trapezoids we already
read, not extra area. Tag 11 "polyData" is 92 scattered points map-wide. **Our decode's
voids are the FILE's voids.**

What remains open of `ROUTER.md` §10's mesh-fidelity claim, stated exactly: **(a)**
whether the voids are FATTER than the visible walls — the operator's eye answers this,
R5 prediction P4; **(b)** §1p.6's waypoint-vocabulary mismatch (retail's part-way points
are never ours, 0/11) — real and untouched by this; **(c)** B5's measured 0.25–8.0 u
standing penetrations. The headline "our mesh reads open ground as a pocket" is not
supported by the specimens that prompted it.

### 1y.4 A third carve source exists (filed, not chased)

Of the compound's 14 props, only 3 reference collision-mesh models and only 2 carry
outlines — **most of these building voids carry NEITHER §1x.2 mechanism.** Something else
carves structure footprints into the compiled mesh (render geometry at compile? a model
sub-chunk our reader does not classify?). Filed with Q3's compile experiment. If R5's P4
is refuted (the line east is visibly open), the next instrument is dumping the client's
own imported mesh — §1x.4 already measured its runtime layout (planes at M+0x18, stride
0x54, count at M+0x20).

### 1y.5 The instrument is promoted and the run is registered

**`toolkit/clientscan/noclipscore.py`** scores any movehook capture: body-sample off-mesh
census with outline attribution, plus rapid-pair chord coverage. Validated on r4a — 655
samples, **21 deep off-mesh naming THREE walked-into massifs (props 127, 179, 221)**;
84 pairs, 39 crossing, worst 19.3% over 1,406 u — §1x.1's numbers bit-for-bit. The mesh
is pinned by `--map-fid`, never selected (§1v.3's trap); the local body is picked by
bake/setter count and printed (two-world-copies trap).

**[RUN-R5.md](RUN-R5.md)** registers four predictions. The run's signature is a
DISSOCIATION: section B's chords still cross the rock (the geometry did not change)
while section A's body goes clean (only legal legs are granted). A body still deep
off-mesh under click-only movement would indict the display/reconcile path, not grant
content — and the reconcile is the mechanism §1t.2 already measured.

## 1z. R5 RAN — the no-clip is DEAD under the router, the dissociation measured 34/34 vs 0/37, and the operator's "backtrack" is the two-copies divergence made visible

**OBSERVED, 2026-08-28**, log `vault/captures/gamesrv/authsrv-20260828T214828-c1.jsonl`
(67 s of routing, 44 routed clicks). **The movehook was not armed**, so scoring is from
the server log alone — position reports are sparser than movehook samples and
`noclipscore.py` section A proper could not run. Scored by
`obstacle-dig/r5score.py`. The operator, verbatim:

> *"this time I couldn't clip in, the new behavior was the second click would make me
> path back to the original position of the first click, then continue walking towards
> the second from there"*

### 1z.1 The predictions

* **P1 (body clean) — SUPPORTED.** 108 reported positions, **1 off-mesh at depth
  0.0 u** (a boundary touch inside prop 247's outline — B5's 0.25–8 u standing-penetration
  class). R4-A under `--click-echo`: 21 samples 65–391 u deep inside three massifs. The
  operator could not reproduce the clip at the same rock. *Caveat: sparse reports, no
  movehook track; the floor of ≥6 deliberate manoeuvres was "a couple" plus sustained
  rapid re-clicking (44 routed clicks total).*
* **P2 (the dissociation) — MEASURED, TOTAL.** **34 of 34** routed clicks' direct
  origin→dest chords cross uncovered ground (worst 28.8% covered over 4,937 u) — the
  geometry did not move — while **0 of 37** granted-leg chords cross anything. Grant
  content is the whole difference, exactly §1x.6's chain read backwards.
* **P3 (on-rock clicks) — OBSERVED**, six of them ((2779, 6455), (3447, 6707),
  (3868, 6781) at the rock; three more NE): verdict `clip-fallback dest-off-mesh` — walk
  straight toward the click, stop at the geometry. Retail-shaped behaviour, no grant into
  the hole.
* **P4 (the compound) — CONFIRMED BY EYE.** *"there's some walls east northeast from the
  spawn, yeah."* `ROUTER.md` §10's "wrong-mesh" closing is now retired on both specimens
  and the eyewitness; what survives is only §1p.6's waypoint vocabulary and the
  unmeasured fattening question.

### 1z.2 The backtrack — **THIS DIAGNOSIS IS WRONG. See §2a.** It is a routing defect

> **SUPERSEDED 2026-08-28, hours later, by the operator: *"it's not a cosmetic bug, it's
> mechanically broken. i shouldn't be backtracking."*** He was right and this section was
> wrong twice over — wrong that it was benign, and wrong about the mechanism. The cause
> is `_shared_edge` answering the MIDPOINT of a shared trapezoid edge, so a body near one
> END of a long edge is routed to the middle of it first: **§2a**. The two-copies reading
> below is left standing as a record of a plausible story that measurement killed; the
> one thing it got right is that the server's origins were fresh, which is what pointed
> the next look at `route()` instead of at state.

### 1z.2-orig The backtrack, diagnosed from the log (REFUTED)

**The server's origins were FRESH** — section 3 of `r5score.py` shows them advancing
along the granted legs between reports (the world-tick integrator), with
|origin − last report| growing to 1,324 u only as report age grows to 15 s. So the
origin is not the defect. The mechanism (RECONSTRUCTION, from settled pieces): the wire
grant carries only a destination, so the client's **sync copy** walks OUR corners from
wherever it was — while the **local copy** runs ahead on the client's own solve, whose
corners are never ours (§1p.6: 0/11). A rapid second click delivers a new grant, the
reconcile drags the local body onto the sync copy — which, having walked our
2,600 u first leg for only ~0.3–1 s, is still near the click-1 position. **"Path back to
where I was when I first clicked, then continue" is the two-world-copies mechanism
(§1n.2) wearing its benign face**: bounded by inter-click walk distance, no clipping,
the same divergence that under `--click-echo` produced installs inside geometry.

### 1z.3 Registered candidate, NOT built: the re-click pin-leg
*(Written under §1z.2's refuted diagnosis. It is NOT the backtrack's fix — §2a is —
and it is not obviously needed at all now. Kept as a filed idea, demoted.)*


On a re-click whose freshest client report is younger than ~2 s, grant **the client's
own reported position as leg 0** before the routed corners — §1w.4 already measured
that a grant whose destination IS the reported body position cannot desync the two
copies by construction, so the sync copy converges to the body instead of the body
being dragged back. Needs its own runsheet with a REFUTED-IF (candidate harm: an extra
grant per pair re-enters §0.15 territory). Filed behind it: the keyboard channel is
still client-free, and mesh fattening is still unmeasured.

### 1z.4 Status

**The click channel under `--router` is clip-free at this run's exposures, and the
no-clip defect is closed as a grant-content defect** — opened §1n, mechanism §1t.2,
scored §1w–§1x, fixed by ROUTER-B2, verified here. What remains on the arc is
cosmetic (the backtrack, §1z.3's candidate) and channel-scoped (keyboard).

## 2a. THE BACKTRACK IS A ROUTING DEFECT AND IT IS FIXED — `_shared_edge` aimed the walker at the MIDDLE of every edge it crossed

**OBSERVED and FIXED, 2026-08-28.** The operator, after §1z called it cosmetic:

> *"it's not a cosmetic bug, it's mechanically broken. i shouldn't be backtracking"*

### 2a.1 The defect, in one line of code

`pathmap._shared_edge` returned **`((lo + hi) * 0.5, y)`** — the midpoint of the interval
two trapezoids share. On map 280 trapezoid **531** borders the corridor **1921** along
`x ∈ [448, 3936]` at `y = 7008`. The body stood at **x = 3367.5**, forty-three units from
stepping straight north into that corridor. The midpoint is **2192.0**, and 2192.0 is
exactly the waypoint the server granted (`authsrv-20260828T214828-c1.jsonl`, t=116.48).
**The walker was sent 1,176 u WEST to the middle of an edge it should have crossed beside
itself.** That is the backtrack, and it is ours, not the mesh's.

**Ruled out first, each by measurement:** the origin was the client's own report, age
0.3 s, drift 1.4 u — not stale state (§1z.2's one correct finding). The graph is intact —
531 and 1921 name each other, and 1921 is the *only* trapezoid bordering 531 above, so
this is not the 4-neighbour-slot limitation. The mesh permits the step — `clip()` north
43.5 u is CLEAR and the 3,317 u leg east along the corridor is CLEAR.

**`_string_pull` could not repair it, and the reason generalises:** it only **drops**
waypoints the previous one can already see, and here the corner after the midpoint is
genuinely out of sight around real geometry (the direct line blocks at 529 u). *Dropping
is not sliding.* A smoother built entirely out of one operation cannot fix a defect that
needs the other.

### 2a.2 The census, before and after

| | backward first legs (cos < 0 toward the click) | worst cos |
|---|---|---|
| midpoints | **7 of 34** routed clicks | −0.917 |
| corner pull | **1 of 34** | −0.526 |

The survivor is plausibly legitimate: its direct line blocks after 176 u of 4,976 and the
route is 1.31× — a real detour around real geometry. **Length saved: median 253 u, max
3,218 u. Paths lost: 0. Paths lengthened: 0.** (R5's 34 clicks and a 300-route corpus
sweep both.)

### 2a.3 The fix, and the two reds it went through

`_pull_corners` slides each crossing along **its own** interval to the point minimising
`|A→P| + |P→B|`, Gauss-Seidel, before `_string_pull` runs. Every candidate stays inside
the interval, hence inside both trapezoids. **Two real regressions were built and caught
before this shipped**, and both are the reason it is a candidate contest rather than a
replacement:

1. **The first minimiser was wrong.** For neighbours on the same side of the edge it took
   "the projection of the nearer endpoint", which is not the minimiser — **19 of 300
   corpus paths got LONGER**. Fixed by the reflection construction (reflect B across the
   edge line, cross to it, clamp — `f` is convex, so clamping the unconstrained optimum
   is the constrained optimum).
2. **A pulled point can cut a corner the midpoints rounded off** — **4 of 300 routes lost
   their path** to route()'s own gate. So the midpoint answer is kept as a **fallback
   candidate**: both are gated, the shorter legal one wins, and the pull can only ever
   improve on the midpoint answer, never lose one.

**And a third red the BENCH caught, which is the one worth carrying forward.**
`clip()` is a sampler; the pull moves crossings toward edge *ends*, where sub-16 u slivers
live. `routerbench.py` re-clips at **2.0 u** because `authsrv.A2_LEAD_CLIP_STEP` does
before sending, and its "every routed specimen's legs clip-clean" **went red** on a leg
that passed `route()`'s own 16 u gate. The pulled candidate now pays the 2.0 u gate; the
fallback keeps 16.0, so the pre-existing answer is untouched. *Two of our own components
disagreeing is the one kind of agreement this repo does not count as evidence — here it
was the disagreement that was informative.*

**Cost, measured, on the thread that owns the world:** corpus sweep p50 4.9 → 10.5 ms,
p95 12.9 → 23.3 ms, max 20.8 → 30.4 ms, **0 of 300 over a 50 ms tick in either arm**;
R5's real clicks 1.5 → 3.0 ms mean. Roughly double, inside budget, and the headroom is
now the thing to watch — the named next lever is gating only the segments the pull
actually moved.

### 2a.4 Tests

**`test_pathmap.py` §13**, seven checks, floor 68 → 75, and the first of them is the
**control**: with `CORNER_PULL_ROUNDS = 0` the specimen must still route backward at
cos < −0.5. A fix whose control cannot reproduce the bug is asserted, not tested. Then
the fix (cos +0.85), no length paid (4,711 u against 7,930 u), every segment re-clipped,
and the two no-loss properties over a 120-draw sweep **with an exposure guard** so a
sweep that routed nothing cannot pass them vacuously. Green at 75 checks / 5 skips.
`test_router.py` 68/68 and `test_routerbench.py` 48/48 green after the fine-step gate.

### 2a.5 The instrument that lost the run — FIXED, §2b

The R5 run's **movehook capture was armed and produced nothing** — `attach.py` reported
`LoadLibraryA returned 0x5EF90000 (loaded)`, the config named
`vault/research/movecode/r5`, and **no directory was ever created**. The stop file was
still on disk afterwards, un-cleared, and the DLL clears it only *after* its poll loop
exits — so the worker never completed its exit path, and the client is gone, so it cannot
be diagnosed post hoc. **Everything in §1z and §2a is scored from the server log alone.**
The DLL writes exactly once, at the end; a run that ends any other way writes nothing.
That is an instrument defect (no periodic flush, no `DLL_PROCESS_DETACH` write, no error
if `fopen` fails). **Fixed the same day — §2b.**

## 2b. THE INSTRUMENT THAT LOST R5 — fixed, and the test that should have caught it did not exist

**FIXED 2026-08-28**, `movehook.c` / `attach.py` / `test_movehook.py` §7 + §16.

### 2b.1 Three defects, all of them the instrument's

R5 armed an 8-minute capture, the operator played, `--stop` ran, and **nothing reached
disk** — no `movehook.bin`, no `movehook.txt`, no output directory. The run was scored
from the server log instead (§1z, §2a), which happened to carry the routing story; that
was luck, not design.

| | was | now |
|---|---|---|
| **when it writes** | **exactly once**, past the end of the poll loop — any ending that loop does not reach discards every record | a **snapshot every 15 s** during the run; worst case is 15 s of loss |
| **process exit** | nothing; a client that closes or crashes with a run armed takes the records with it | `DllMain` writes on `DLL_PROCESS_DETACH`, standing down once the worker's own final write happened |
| **failed write** | **silent** — `fopen`'s NULL dropped, so an unwritable path looked exactly like a run that captured nothing | recorded in `g_werr` and reported twice: in `movehook.txt`, and in a `movehook.status` file **beside the DLL** |

Two structural changes fall out of the second row. The writer is now **Win32**
(`CreateFileA`/`WriteFile`) rather than CRT stdio, because it is called at process
shutdown where the CRT may be torn down and stdio can deadlock under the loader lock —
the `.txt` report keeps stdio and is deliberately **not** written from `DllMain`. And the
write is **atomic** (temp file, then `MoveFileExA`), so a snapshot interrupted mid-flight
cannot replace a good capture with a truncated one.

`attach.py` changed on both ends: it **proves the output directory writable before
injecting** (and refuses, rather than spending a run on a path that does not work), and
`--stop` **waits for the artifact and reports a missing one**. Its old text — *"the DLL
polls at 100 ms; it will disarm and write within a second"* — was printed on R5 and was
false; the operator reasonably believed it.

### 2b.2 The testing lesson, which is the durable part

**`test_movehook.py` §7 injected the DLL into a real process, waited for output, and
asserted the `.txt` sidecar — the SUMMARY. It never once asked whether the CAPTURE
existed.** 176 checks in that file and not one of them could have caught a run that
produces no data. The artifact a test does not name is the artifact that can vanish.

§7 now requires the `.bin`, its `MVHK` header, that **`readhook.py` can parse what the
DLL just wrote** (the writer was rewritten under this change — "the bytes still mean what
the reader thinks" is exactly the property that rewrite could break), and that no `.part`
temp survives.

**§16 verifies the exit path BEHAVIOURALLY, not just structurally**: a real 32-bit
`cmd.exe` is injected with a long timer, a **control** confirms nothing is on disk
mid-run so the file cannot be attributed to the normal ending, then its stdin is closed
for a **graceful** exit — `TerminateProcess` does not run `DllMain`, and a test built on
`kill()` would prove nothing — and the capture must appear. That is the R5 scenario
itself, and it passes.

**Two checks went red against the fix, and both were the test working.** One read
`WriteFile` inside `write_bin` when that call lives in its one-line `put` helper — a
wrong **operand**, the second this arc has paid for. One still looked for `snapshot(`
after the detach path was inlined.

### 2b.3 The operator's own hypothesis, and what it changes

> *"i think i may have killed the server before running the stop, maybe that did it"*

**Consistent with every piece of evidence, and it decides WHICH half of the fix carries
the case.** The tell was always the `movehook.stop` file still sitting on disk at 21:51:
the DLL clears it only after its poll loop exits, so nothing was alive to consume it —
the client was already gone when `--stop` ran. `session.py`'s teardown closes the client
on **every** path including `--keep-open`, and `drive_client.close_client` sends
**WM_CLOSE first** (graceful, so `Gw.log` survives) with a `terminate()` fallback after
20 s. So:

| how the client goes away | what saves the capture |
|---|---|
| WM_CLOSE — harness teardown, or closing the window | **the `DLL_PROCESS_DETACH` write** |
| `TerminateProcess` — the 20 s fallback, or a taskkill | **the periodic snapshot**; DllMain does not run at all |

Both are now verified behaviourally, **in separate hosts**, for a reason worth keeping.

### 2b.4 Two mechanisms racing through one artifact cannot be attributed by the artifact

The first version of the snapshot test reused the exit test's host and told the two
writes apart by **mtime**. It went red — and neither mechanism was broken. Standalone
repro of the same sequence showed both working; the DLL's own status file dated the
snapshot's write **86 ms before** the file's mtime, which means the "before" reading the
test took was **already the exit write's**. The check was comparing a write against
itself.

Chasing that produced one genuine fix on the way, which is why the red was still worth
having: `outdir()` reads `movehook.cfg` through `fopen` on **every call**, and the detach
path called it — at `DLL_PROCESS_DETACH`, where every other thread is already terminated,
possibly inside the CRT holding its locks. That is the exact hazard this file documents
for the *writer*, walked into again one line away from it. The path is now resolved once
at arm time into `g_outdir`, and the shutdown path builds its strings with kernel32
(`lstrcpynA`/`lstrcatA`) rather than `snprintf`. It was not the cause of the red, and it
is committed as a fix on its own merits — not as the answer to a question it did not
answer.

**§16 now runs one host per mechanism.** (f) injects, confirms by control that nothing is
on disk before the first flush, then closes stdin for a **graceful** exit and requires the
capture to appear from nothing. (g) injects a second host, waits past `FLUSH_MS` (read
out of the C source, never restated in the test), requires the file **with the host still
alive**, then **`TerminateProcess`es it** — no DllMain, nothing more can possibly be
written — and requires what survived to be a capture `readhook.py` parses. That second
host is the operator's own scenario if the WM_CLOSE path ever times out.

**Suite:** `test_movehook.py` **180 checks green**, floor 105 → 118.

## 1z-b. R5b — the run R5 should have been: instrument green, P1–P4 all read, and the operator could NOT reproduce the no-clip

**OBSERVED 2026-08-29.** `vault/research/movecode/r5/movehook.bin` (3,933 records,
1.0 MB, 126.8 s of local-body samples) + `authsrv-20260829T085952-c1.jsonl`.
`--router --map 280`. This is R5 re-run with a working instrument: **9 successful
writes, `last write error: 0`** — §2b's fix carrying a real run, and the first movehook
capture of a router session.

### 1z-b.1 The four predictions, all with exposure

| | | |
|---|---|---|
| **P1** body never crosses a carved hole | **MET** | 699 deduped samples, **65 off-mesh but ZERO deeper than 1 u** — every one a trapezoid-boundary touch. r4a under `--click-echo`: 21 samples 65–391 u deep inside three massifs. |
| **P2** the dissociation | **MET, and stronger than R5a** | **24 of 26** rapid-pair chords cross uncovered ground (worst **5.8% covered over 2,554 u**) while the body stays clean. R5a measured 34/34 vs 0/37 from the server log; this is the same split measured from the *client's own memory*. |
| **P3** on-rock clicks are not granted into the hole | **MET, n = 17** | **17 `dest-off-mesh` verdicts** — 12 `clip-fallback`, 5 `refused`. The operator: *"clicking the rock itself walked me into its normal collision"* — the fallback walks straight at the click and stops at the geometry, and the client's own collision holds it at the face. That is the designed behaviour, seen from both ends. |
| **P4** the compound is real | **CONFIRMED BY EYE** | Screenshot from the spawn: a walled stone structure with a green roof, east-north-east, on the line the router detoured around. `ROUTER.md` §10's "our decode reads open ground as a pocket" is now retired on all three of its supports. |

**And the headline the operator supplied directly: the corner-click manoeuvre would
not reproduce.** Under `--click-echo` it was, in their words, *easy to repro*.

### 1z-b.2 The warps, and what changed about them

**13 installs moved the displayed body, 40–550 u — and EVERY landing is on-mesh.**
Under `--click-echo` (§1w.1) relocation landings were off-mesh **6 of 10** at median
239 u inside blocked ground. Same mechanism, same reseed→`SetPosition` chain (§1t.2),
now landing on legal ground every time, because what it dead-reckons from is a legal
leg. The operator's *"small warp or two"* is the two 540–550 u steps at t+65.1 and
t+126.4.

### 1z-b.3 The bridge report is UNSCORED, and that is the honest word for it

> *"then some terrain walking around the bridge to the west near the end of the
> capture"* … *"some of the things i reported near the end of the run may not show up
> on the wire"*

The operator is right, and the log proves it: the first `--stop` **disarmed the hook**
(status at that moment: 3,862 records, `running`), so play after it is not on the wire.
Two further reasons this cannot be scored from what we have:

* **Zero stacked-geometry exposure.** A bridge is the one shape our navmesh cannot
  represent — `pathmap` has no height, so a deck over ground is the 0.2% stacked case
  (§1w.7). Sweeping a 48 u grid over the walked region **plus 1,500 u of margin finds
  ZERO stacked cells**, and **0 of 712 samples** stood on any. There is no bridge in
  the region this capture covers, as our mesh sees it.
* **All 712 samples are plane 0**, and none declares a plane the mesh lacks.

**So this is zero exposure, not a null** — the standing rule. What it costs is a
runsheet fix, not a finding: **`--stop` ends the capture, so it must be the LAST thing
the operator does**, and RUN-R5 now says so.

### 1z-b.4 Status

**The click channel under `--router` is clip-free across two runs and two instruments**
— server-log positions (R5a) and the client's own `m_point` samples (R5b) — with the
repro attempt failing at the same rock that produced it under `--click-echo`. The
straight lines still cross the geometry on 24 of 26 chords, which is the point: the
geometry did not change, the grant content did.

**Still open and unchanged:** the keyboard channel (client-free); mesh fattening;
§1y.4's third carve source; retail's waypoint vocabulary (§1p.6). **New and small:**
whether anything is walkable-through around the west bridge — needs a run whose
`--stop` comes after it.

## 1z-c. THE BRIDGE, AND THE STUCK CLIENT — a PLANE channel the arc has never scored, and the first captured client-side movement LOCK

**OBSERVED 2026-08-29**, two operator-driven captures: `r5bridge` (45 s, the bridge
walk the operator went back for) and `r5stuck` (23 s, armed *after* the client had
already stopped responding to move commands). Both `--router --map 280`. Scored with
`noclipscore.py`, which this section extends.

### 1z-c.1 The instrument was blind again, in the other direction

**§1w.7 established that plane-blindness is irrelevant to a carved HOLE.** That is
true, and it is exactly what made this look settled. **A BRIDGE is the other case, and
there the plane is the entire question**: `containing(x, y)` unions all 68 planes, so a
body on a deck and a body on the ground *under* that deck are the same query and both
score on-mesh.

`noclipscore.py` section A read **0 off-mesh on a capture the operator took because
they had just walked under a bridge twice.** New **section C** asks the plane-aware
question — `m_point` has carried it all along (`float x, float y, int plane, int`):

| capture | stacked samples | declares a plane the mesh lacks | section A |
|---|---|---|---|
| **r5bridge** | 10 | **6** | 0 |
| r5 (§1z-b) | 0 | 0 — and it now says **ZERO EXPOSURE**, not "clean" | 0 |
| r4a (`--click-echo`) | 13 | 5 | 21 deep |

The r5bridge anomalies are the operator's two episodes: the body on **plane 37 where
the mesh offers only 0** at (−1031.5, 6282.8) and (−1467.9, 6420.9), and on **plane 0
where the mesh offers only 37** at (−2821.9, 6404.3). Deck-over-ground, both
directions. **This channel is orthogonal to everything the arc has scored** — a plane
anomaly is invisible to 2D coverage, and 2D depth is invisible to the plane test.

*Two defects were found in `noclipscore.py` writing this: section B `return`ed when a
capture had fewer than two clicks, which SILENTLY SKIPPED section C — a keyboard-only
walk would have been scored with the one section that can see a bridge missing. And the
zero case had to be given words: a run with no stacked geometry anywhere now says ZERO
EXPOSURE rather than reporting a reassuring zero.* `toolkit/clientscan/test_noclipscore.py`
holds all of it, including a control that a body on the plane the mesh DOES offer is
not flagged, and fixtures that prove their own premise against the real mesh first.

### 1z-c.2 THE STUCK CLIENT: the plane was impossible, and the client could not path out of it

The operator got **stuck in open ground** — no move command worked — and armed the hook
while stuck. It is the most diagnostic capture in the arc.

**What the client did, OBSERVED:**

* **The body never moved: 0 u of path in 22.9 s**, both copies.
* **The walker NEVER RAN.** `agapi_setdest` **0 hits**, `chcli_advance` **0 hits** —
  against 49 clicks that each reached `chcli_point` and each produced a `MapFindPath`.
  The client solved a path for every click and drove the body with none of them.
* **All 49 path queries start from plane 41 at (−2803.4, 509.4), where our decode
  offers only plane 0** (46 of them asking for a plane-0 goal). **68 of 68 body samples
  declare that same impossible plane.**
* **The fence is SHUT on 110 of 110 reads** (`clientControlled == 0`), against
  **804 OPEN / 11 SHUT** in the healthy run — the cleanest client-side discriminator
  the arc has.
* `m_timeStopMovement` is **0 on every one of the 186 display-body records**; in the
  healthy run it varies.
* **93 gateless reseeds** (`ResyncAllAsync`, the route §1s.1 could never catch firing
  cold) re-install the position **at 0.0 u separation** — 93 no-ops that keep the bad
  (x, y, plane) alive.

**The mechanism, RECONSTRUCTION from pieces the arc already owns:** the client's
point-resolve indexes `pt.plane` into its plane array (§1x.4's decode of `0x0072B840`,
guarded by `Array.h`'s bounds assert), and B3-3 Q5 measured that on an install **"the
plane rides along unchanged"** — `SetPosition`/teleport copy the 16-byte point, so a
relocation can carry a STALE plane to a new (x, y). A start point whose plane does not
contain it cannot resolve; the query yields no path; nothing calls `setdest`; the body
cannot walk — and because it cannot walk, it can never re-plane itself. **A plane
desync is a movement LOCK, where a position desync is only a warp.**

**Our own router is MORE FORGIVING and cannot reproduce it:** `route()` from that point
returns a 2-waypoint path from plane 41 *and* from plane 0. So the server would happily
keep granting legal paths to a client that cannot move — which is exactly what the log
shows.

**What our server contributed, and it is not the cause:** 100 of 127 router rows are
`kbd-drop` (79%, against 13% in the healthy run) — every click refused under believed
keyboard authority — and 58 zero-lead grants pinned the frozen position. So *clicks*
were dropped by us while *keyboard* movement was locked client-side. Both inputs dead,
two different reasons.

**REFUTED, by its own control:** the first hypothesis here was that zero-length grants
(destination == the reported position) caused the lock. **The healthy run has 76 of 76
zero-length grants and a 46.7 s stretch at one position**, and did not lock. The
discriminator is the plane and the fence, not the grant length.

### 1z-c.3 What is NOT established

The causal chain from the impossible plane to the dead walker is **RECONSTRUCTION**: we
observe the queries and the silence after them, not the client's failure to resolve.
Plane indices are our decode's; they come from the same file the client reads, but the
identity is assumed. **The onset is not captured** — the hook was armed after the lock
— so what set plane 41 is unmeasured. *(SUPERSEDED 2026-08-29, same day: not captured
CLIENT-side. The server log had it the whole time — §1z-d reads the onset out of
`authsrv-20260829T091543-c1.jsonl`, and it is the client's own plane-carry across a
boundary, echoed back by our grant path. The MapFindPath tap below is still the missing
client-side half of the chain.)* `r4a` carries the mirror anomaly 200 u away
(declaring plane 0 where the mesh offers 41), so this neighbourhood produces plane
confusion under both policies.

**The cheapest next measurement** is a `MapFindPath` RETURN tap (`0x00709F0F`,
`0x00709F44`, `0x0070A0AD`, `0x0070A0D4` — named in `content/movecode.toml`'s own
`limits` note): it would turn "the client asked from an impossible plane" into "the
client got pathCount 0", which is the one link this section infers.

## 1z-d. THE ONSET WAS IN THE SERVER LOG ALL ALONG — and the lock now has a repair

**OBSERVED 2026-08-29**, from `vault/captures/gamesrv/authsrv-20260829T091543-c1.jsonl`
(the stuck session's server-side capture, matched by its 127 router rows / 100
kbd-drop) — read the same day §1z-c.3 called the onset unmeasured. One correction
first: the "healthy run" §1z-c.2 cites for comparison is `085952`, the same morning's
§1z-b r5 session (12/90 = 13.3% kbd-drop, 76 zero-lead grants — the exact figures),
not the 08-28 evening file.

### 1z-d.1 The onset, observed

* **The client reported plane 41 first, from ground where 41 is CORRECT.** The first
  plane-41 anywhere in the session is a c2s `MOVE_SET_HEADING` at t=29.03 from
  (−2921.0, 523.4) — where our mesh offers exactly {41}. This is the strongest
  corroboration yet that the client's plane indices are our decode's: the client
  acquired 41 precisely where we say 41 lives.
* **1.5 s and 150 u later the mesh offers only {0} and the client still said 41** —
  the plane rode along across the boundary. B3-3 Q5 measured this for installs
  ("the plane rides along unchanged"); this is the same defect on the client's own
  walking report path, in the wild.
* **Our trust guard rejected that report — and the grant path echoed its plane
  anyway.** `position_report` idx 988: `accepted: false`. The very next
  `grant_verdict` used the same packet's `plane_dest=41` and sent
  `ZERO LEAD (−3074, 22) plane 41`. The position validator and the grant plane were
  never connected.
* From t=39.9 the client repeated a byte-identical report at the frozen coordinate:
  **82 accepted reports (81 `in-budget`, 1 `stop-report`), one coordinate, plane 41,
  40.4 s (t=39.87..80.23).** REFINES §1z-c.2's "58 zero-lead grants pinned the frozen position": 58 is
  the session's total zero-lead count; **43 carried a mesh-impossible plane, 35 of
  those at the frozen coordinate**; the early approach (t=1.7–19 s) was all plane 0
  and correct.
* **The wrong-plane emission is unique to the lock, and it is pure echo.** Full
  outbound census, every plane-bearing send checked against the mesh at its own
  point: stuck **43 of 65** wrong-plane; r5bridge **0 of 53** (including 9
  legitimate plane-37 deck grants — the positive control that the census can pass
  real stacked traffic); r5 **0 of 128** (3 off-mesh-point sends are a separate,
  milder class); 08-28 healthy **0 of 104**. The server never *invents* a wrong
  plane; it faithfully relays the client's confusion.

### 1z-d.2 What landed: a repair keyed on behaviour, and a tripwire that only watches

The obvious fix — never emit a plane the mesh does not offer at the emitted point —
is **wrong, and this file's own arc proves it twice**: `plane_at`'s 9-of-198 failure
class is exactly "the client's plane is CORRECT and our decode's coverage is missing"
(bridge-over-ground), a send site that second-guessed the client's plane through
`plane_at` was reverted for overruling it in precisely the wrong place, and
`test_position_trust` pins verbatim echo at the zero-lead site as design. An
instantaneous geometry test cannot tell "client on a deck we failed to decode" from
"client with a stale plane". **Behaviour can**: the locked client reported keyboard
movement (0x003D is emitted only while moving) from a byte-identical position for
40.4 s — a deck-walker moves, and a standing player sends no 0x003D at all.

So `authsrv.py` now carries (commit this section lands in):

* **The plane repair** (`plane_repair_track` / `_maybe_plane_repair`, ON by default,
  `--no-plane-repair` reverts): after accepted 0x003D reports repeat an identical
  (x, y) for 5.0 s claiming a plane the mesh does not offer there, with an
  unambiguous single-candidate resolution, send a numbered, labelled `PLANE-REPAIR`
  0x002C — the client's own frozen point, the mesh's plane — at most once per 10 s
  while the signature persists. 0x002C's slot-2 plane is what the client writes to
  agent+0x80 (§1x.4's decode), which is the exact field its path queries read from —
  RECONSTRUCTION: that this heals the lock is the registered prediction, not yet a
  measurement (the stuck session sent zero 0x002C of any kind, so the heal has never
  been tried). Every clause that is not the lock DISARMS the streak (moving client,
  offered plane, ambiguous stack, off-mesh point, NaN coordinate, trust-refused
  report, pure-turn report, stale stream — a report gap over 5.0 s re-arms the
  clock, because the evidence must be a live stream). The constants derive from the
  one measured lock (exact-equality freeze because the reports were byte-identical;
  5.0 s HOLD against a 40.4 s lock; the 5.0 s GAP from the capture's own gap
  structure — 2.47 s intra-episode must survive, 10.3 s inter-episode must not —
  REFUSED-IF a future lock drifts or is shorter, in which case re-derive, don't
  loosen). A fire also heals `zl_last_grant_plane`, or the SAME packet's zero-lead
  grant would restamp the sync copy with the plane the 0x002C just corrected; the
  grant's field 3 still echoes the report's plane by the verbatim-echo design, and
  whether that residue matters on a healed client is unmeasured. A false fire (a
  client frozen 5 s on a deck our decode missed — the 9/198 class, no measured
  instance in four sessions) restamps a correct plane with no positional yank;
  NOT established recoverable, since the client carries plane words rather than
  re-deriving them. In a healthy run it fires ZERO times.
* **The first draft of this repair was refuted before it ran, by the review.** It
  disarmed the streak on every 0x0047 stop-report ("no movement claim, no lock
  evidence") — and replaying the source capture through the shipped code showed the
  measured lock INTERLEAVES stop-reports (a victim mashes keys; 1 stop at the
  frozen coordinate itself), pushing the first fire to 9.3 s and tripling the
  sends against a prediction of "~5 s, one 0x002C". Stops are now ignored entirely
  and freshness is the GAP bound's job. **Replay of the shipped design over
  r5stuck: fires at t=44.98, 55.12, 70.80 — the first 5.11 s after the freeze,
  each legitimate (this client stayed locked the whole capture; no repair existed
  to heal it).**
* **The plane-echo tripwire** (in `_note_wire_move`, the send() choke point all
  three player-moving opcodes route through): an outbound slot-2 plane the mesh does
  not offer at its own point gets a `plane_echo` row and a transition print — and
  goes out **unchanged**. The 43 silent echoes above would each have been a named
  row. Observation only; the rewrite is the twice-refused design.
* `test_planerepair.py` (35 checks, floor 30) holds both to the disarm clauses, the
  label, the transition-only logging, the no-mutation property, and the r5stuck
  premise against the real map-280 mesh.

### 1z-d.3 What is still NOT established

The client-side half of the chain is still §1z-c.3's inference — the `MapFindPath`
RETURN tap remains the cheapest next measurement, and would also measure whether a
repair's restamp actually revives the walker (predict: first post-repair query
starts from the restamped plane and returns pathCount > 0). The repair has never
fired against a live client — its next lock is its first trial, and the registered
prediction (timing restated from the offline replay above, which is its authority):
the `plane_repair_due` ladder reaches `plane-lock` within ~5 s of the first
continuous report episode at the frozen point, numbered PLANE-REPAIR 0x002C rows go
out at most every 10 s while the lock persists, and — the part no replay can score —
the client walks on the next click after fire #1, so a healed client shows exactly
ONE fire. Repeat fire numbers on a live lock mean the restamp is NOT healing, which
would refute the agent+0x80 reconstruction rather than the trigger. A lock whose
victim stops pressing keys entirely is invisible to it (no 0x003D stream, no
evidence — key-MASHING victims are covered, that was the first draft's blind spot);
nothing here covers NPC planes; and the onset itself is not prevented — the
client's plane-carry is the client's, we only heal its consequence.

---

## 1z-e. THE CORPUS ALREADY HELD TWO MORE LOCKS — the sweep, the replay, and a poisoning loop on tape

**OBSERVED 2026-08-29, desk-only** — no client run, two instruments over evidence that
already existed: §1z-c's section-C question asked of **every** movehook capture in the
corpus (13; it had only ever run on three), and the shipped `plane_repair_track`
replayed over **every** gamesrv session JSONL (1,209 files). This is §4.3 of
[HANDOFF-PLANE.md](HANDOFF-PLANE.md) executed, and the handoff's instinct ("mine
before registering another run; the corpus often already holds the event") was right
twice over. One correction first: §1z-d.2 above says `test_planerepair.py` "35
checks, floor 30" — the shipped file declares **floor 36** and the handoff's "41
checks, floor 36" is current; the smaller figures predate the review's additions.

### 1z-e.1 The census: the plane-carry is COMMON, it self-heals, and it is not map-specific

Method: same body-sample selection as `noclipscore.py` section C (position-reporting
sites, local body by bake/setter census), but each record's **own** `point[2]` as its
declared plane — section C dedupes same-tick samples and re-found the plane by tick,
which aliases when records share a tick, so its counts were lower (k1-treatment: 48
deduped anomalies vs 78 raw impossible records; same events, different denominators).
The review showed the alias is not only a denominator difference: **on k2-2 it
erased two real anomalies outright** (seq 436, own plane 31 on offered {0}; seq 472,
own plane 0 on offered {32} — each scored "ok" off a same-tick sibling's plane).
**Section C is fixed in this commit** — it now carries each record's own plane
(`test_noclipscore.py` §5 pins the alias shape, red against the pre-fix code) — and
the published §1z-c counts move under the fixed lookup, deliberately: **r5bridge
6 → 8, r4a 5 → 8, r5 stays 0 (zero exposure)**. The mover is the fix, not the
corpus.
Consecutive impossible samples group into episodes; an episode closes on the first
sample whose declared plane the mesh offers. Meshes pinned per capture from the run
records (never selected): map 280's `0x287B3` for the r/k/isle/snap/v5 series,
Ascalon's `0x1B97D` for run-1/run-2. Analyzer and per-capture output:
`vault/research/movecode/plane-sweep/`.

| capture | mesh | body records | impossible | episodes |
|---|---|---|---|---|
| r5stuck | 280 | 51 | **51** | 1 — the §1z-c lock, capture starts mid-lock |
| k1-treatment | 280 | 362 | 78 | 2 — one server-stamped (§1z-e.4), one ends the capture INTO lock #3 |
| k2 | 280 | 382 | 3 | 1 |
| k2-2 | 280 | 168 | 24 | 4 |
| r1b1 | 280 | 660 | 0 | 0 — with stacked-ground exposure (7 deduped samples on >1-plane ground) |
| r1b2 | 280 | 1,257 | 0 | 0 — exposure 3 (thin, stated) |
| r2 | 280 | 3,418 | 40 | 3 |
| r3 | 280 | 947 | 0 | 0 — exposure 51, the solid null |
| run3-isle | 280 | 1,314 | 7 | 1 |
| run4-snap | 280 | 183 | 14 | 2 |
| run5-v5 | 280 | 1,209 | 21 | 3 |
| run-ascalon (§1c) | 148 | 1,168 | 31 | 4 — the last ends the capture INTO lock #2 |
| run2 (§1e) | 148 | 78 | 6 | 2 |

* **13 of the 22 non-lock episodes are strict carries**: the declared plane equals the
  plane of the last legal sample — the body walks off plane-N ground and keeps saying
  N. Durations 0.2–18.6 s; **20 of 22 self-heal on tape** (the client re-planes and
  walks on); the two that do not are the two whose captures end inside them, and each
  is the client-side face of a server-side lock below.
* **The carry appears at one boundary in BOTH directions.** Around map 280's 0|17
  boundary (x ≈ −6300..−5900), run4/run5 episodes declare 17 on {0} ground and
  r2/run3/k2-2 episodes declare 0 on {17} ground — the declared plane follows where
  the body CAME FROM, not a fixed side of the line. Two carry episodes also span
  1,667 u and 2,717 u of walking. RECONSTRUCTION: these are temporal carries (the
  client's plane word lagging its ground), not a spatial offset in our decode — a
  decode offset predicts one fixed (declared, offered) pair per boundary regardless
  of travel direction, and no plausible offset is 1,667 u wide. The 9-of-198
  decode-hole class may still own individual episodes; nothing here rules a specific
  episode either way.
* **The remaining 9 episodes** are boundary tangles (multi-plane walks), two
  cases where the declared plane matches nothing the body had recently stood on
  (k1's dissolved under review into the client's own reseed machinery flapping at a
  seam — §1z-e.4; run2's is unattributed), and the two lock onsets. The strict
  SAME/other split also undercounts carries: the ascalon lock onset declares 29 held
  from the episode before last, across one legal plane-0 touch — a carry by any
  reasonable reading, "other" by the strict criterion.
* The three zero captures had exposure (stacked-ground samples: 7 / 3 / 51), so the
  nulls are non-vacuous — though r1b2's 3 is thin and is stated rather than leaned on.

### 1z-e.2 The replay: three sessions fire, and all three are REAL

`plane_repair_track`, exactly as shipped, fed every `position_report` row with
`source == "0x003D"` in session order (`moving=1` throughout — the row does not
record the movementType enum, and the arm's own census has never seen a pure-turn
0x003D in 7,988 records; stop rows excluded exactly as the live call site excludes
them). **The mesh is PINNED per session from the session's own tape** — word 3 of its
`INSTANCE_LOAD_INFO` send, resolved through `content/maps.toml` — never voted: a
13-mesh containment vote was tried first and collapsed eligibility 70 → 6, which is
§1v.3's wrong-map selector measured from the other side (meshes overlap in world
coordinates; Sparkfly contains map-280 walks).

Coverage, with every skip counted — and CORRECTED by the pre-publication review,
which found the first pass's label parse wanting: 1,209 files scanned; 112 sessions
carry ≥ 6 0x003D reports. The first pass scored **47** under their pinned mesh and
screened **63** "no-map-row" sessions under both arc meshes (zero fires; its one
screen fire dissolved — a session starting at Ascalon's own spawn (9826, 8077),
mis-screened under the 280 mesh, clean under its own). The review then showed the
63-session pool was **manufactured by an exact-match on the `INSTANCE_LOAD_INFO`
label** — 235 files carry suffixed labels (`INSTANCE_LOAD_INFO [is_explorable=1,
FORCED]`), and with a prefix match **every session with position rows names its
served map**. Re-screened under true served meshes: zero fires, unchanged. Even the
two map-167 sessions (08-22, 114 + 24 rows; that map's mesh id is absent from the
default archive) score zero fires under the authored ashcoil mesh in the run
archive — every report claims plane 0, the mesh's only plane, so the streak never
arms. The independent replay also reproduced the result on both clocks (`t` and
`wall_unix`), found no other session whose streak held even 3.0 s, and measured the
tightest fire margin at 72 ms over HOLD — the "exactly three" is not
threshold-fragile.

**Result: three sessions fire; zero fires anywhere else.**

| session | map | fires (t, restamp, claimed plane) | what it is |
|---|---|---|---|
| `authsrv-20260829T091543` | 280 | 44.98 / 55.12 / 70.80 → 0, claimed 41 | **the §1z-c lock** — reproduces §1z-d's replay numbers exactly, from the shipped code, independently |
| `authsrv-20260827T055221` | 148 | 339.56 → 0, claimed 29 | **lock #2**, §1z-e.3 |
| `authsrv-20260827T212317` | 280 | 115.88 → 0, claimed 31 | **lock #3**, §1z-e.4 |

The "zero fires in a healthy run" clause of §1z-d survives, sharpened: zero fires in
every session that did not contain a real frozen-impossible-plane episode — and the
trigger retro-discovered two locks nobody had reported.

### 1z-e.3 Lock #2 — Ascalon, 2026-08-27 05:52, §1c's own session

The session behind §1c's run 1 (`run-2026-08-27-ascalon`; no run doc names the
session, so the pairing is fingerprinted: the frozen coordinate's float BIT patterns
(x=1178283849, y=1176759779) appear in 35 bin records spanning 59.7 s — the same
59.69 s window as the session's frozen reports — and the GetTickCount boot-epoch
anchor (2026-08-20 20:53:44 ± 3 s, agreed by four captures) nests the bin's record
window 05:54:01–05:58:24 inside this session and no other; the only other map-148
sessions that day are two ~4 s aborted logins with zero position reports. Do not
date these bins by mtime — both 08-27 bins' mtimes are copy-out artifacts). The client froze
at (11979.82, 10491.47) declaring plane 29 where the mesh offers only {0}:
**t=294.8..354.5, every report at one byte-identical coordinate, accepted, in mash
bursts** — a burst, a **36 s pause**, a burst — while the zero-lead grants echoed
plane 29 back throughout. Then the reports stop entirely at t=354.5 and the session
sits silent for 9.2 minutes until the client force-closes the connection at t=907 —
**10.2 minutes from freeze to kill**. The client-side capture ends inside the same episode (its v1 instrument had
no click/query/walker sites, so §1z-c's dead-walker signature cannot be read from it;
the server tape is the evidence here). Onset, same shape as §1z-d: plane 29 was
carried through a 12.6 s WALKING episode (2,866 u), one legal plane-0 sample, then
two client-side jumps (4,562 u and 4,393 u within 0.8 s — the first refused by trust,
the second accepted) into the frozen point, still claiming 29.

The replay consequence worth keeping: **the burst-pause-burst mash delays the first
fire to ~45 s after freeze onset** — the 36 s silence exceeds `PLANE_REPAIR_GAP` and
re-arms the clock, by design ("one keypress cannot inherit a minutes-old streak").
The constants' REFUSED-IF does not trigger (the freeze is byte-identical, no drift),
but §1z-d.3's "~5 s to first fire" is now known to hold only for a continuously
mashing victim; a despairing one is healed on the next mash burst instead.

### 1z-e.4 Lock #3 — the K1 treatment session, and a poison story REFUTED by its own review

`authsrv-20260827T212317` is the K1 keep-alive re-grant treatment session (§1l's
arm; the pairing is fingerprinted — the session's byte-exact
(−5933.03955078125, −2195.1767578125) plane-0 rows sit on 6 byte-exact records in
the k1 bin, only this session holds `keepalive_verdict` rows, and its two
`fired: true` at t=79.69/80.86 are §1l.3's exact figures). Two things on this tape:

* **A poison story this section's first draft told, and the pre-publication review
  REFUTED — kept because the refutation is the finding.** The draft read: client
  reports plane 22 (t=79.16, 0x003D) → keepalive re-grant emits plane 0 from stale
  state (t=79.69) → client adopts 0 on {22} ground (t=79.97). The skeptic dumped the
  window WITHOUT the draft's 0x003D-only filter and the story inverts: **the client
  itself reported plane 0 first, in a 0x0047 stop-report at t=79.373 at that exact
  coordinate** — the draft's dump had filtered out the stop arm — and the era's code
  (ddff031) builds the keepalive from `state["plane"]`+`state["client_pos"]`,
  written together on the accept path by that very stop. The client-side hook agrees:
  the displayed body's plane flips 0↔22 by its OWN reseed/teleport machinery (first
  flip t≈79.05, before any keepalive ever fired; only 2 keepalives fired in the whole
  228.7 s session), the keepalive's 0x0029 lands on the **parked sync twin**, not the
  displayed body, and the t=80.56 flip to 22 happens AGAINST the server's latest
  plane word. **The server relays here too — §1z-d's "never invents a wrong plane"
  survives a second test it could have failed.** The client flapping its own plane at
  a boundary seam is itself a real observation (it is the carry class churning), and
  one residue stays PLAUSIBLE and filed: the two later flips each landed on the same
  frame as a `ZERO LEAD` whose field-4 carry word matched the flip's target — a
  grant-triggered client reseed through THAT field is a different mechanism than the
  refuted one and is worth its own probe; the first flip had no wire trigger at all.
* **The lock.** t=110.66: with the body walking at carried plane 31 (the client
  capture's second episode — 1,667 u of walking, declaring 31), the client reports
  from (−5919, −165), **4,745 u away, with no server send in between** — a
  client-side rollback, §1h's class — and keeps plane 31, which the mesh does not
  offer there. It then mashes (move types 1/2/4, headings changing, position
  byte-identical) for 6 s until the reports stop; the session sits silent and the
  client force-closes at t=228.7. The client-side hook had been stopped at 109.7 s —
  **seconds before the freeze** — so the capture ends into the lock (the §5.2
  `--stop` trap, already biting on 08-27).

### 1z-e.5 What this changes in §1z-d.3's registered prediction

* **All three locks share the onset shape**: a legally-acquired plane carried across
  a discontinuity — a walked boundary (§1z-d), or a client-side rollback jump (both
  08-27 locks) — onto ground that does not offer it. The rollback variant is new:
  the discontinuity does not have to be walked.
* **"A healed lock shows exactly ONE fire" is WEAKENED as a discriminator.** Both
  historical locks also show exactly one replayed fire — because the victim's report
  stream ENDS (gives up, then force-closes), not because anything healed. A single
  fire followed by stream-end is what an unhealed lock looks like too. The live
  discriminator is unchanged from the part that mattered: **movement resumes after
  fire #1**. Repeat fires still refute the agent+0x80 heal reconstruction.
* **Prevalence**: 3 locks in the 112 movement sessions the corpus holds (all
  scored, after the review closed the coverage holes) — but the
  two 08-27 locks happened under refuted-and-retired policies (K1's keepalive
  re-grant; §1c's era), so this is not a rate for the shipped default. Under the
  router-era defaults the count is 1 (r5stuck), from one day of runs.
* **The silent-lock blind spot has a measured grey zone**: lock #2's victim paused
  36 s mid-lock. The repair heals such a victim on their next mash burst; a victim
  who never presses again stays invisible, as §1z-d.3 already states — and both
  08-27 sessions END in exactly that silent phase, minutes of it.

---

## 1z-f. RUN-R6 RAN — the trigger stayed silent through the heaviest plane exposure ever captured, the under-bridge is a GLITCH, and the carry's mechanism got its cleanest measurement

**OBSERVED 2026-08-29 (session `authsrv-20260829T132441`, 7.8 min; client capture
`vault/research/movecode/r6/movehook.bin`, 6,152 records, both controls FIRED,
ended by `--stop`; scoring scripts beside the bin in `r6/scoring/`).** The
[RUN-R6.md](RUN-R6.md) trial, scored by four parallel lanes (episodes, press,
wire, mesh) whose load-bearing disagreement was settled by a fifth tabulation —
see the mechanism bullet, where one lane's reconstruction is refuted by its own
column. Hook↔session alignment: `t = tick/1000 − 750664.395`, derived from a
222-match report↔sample histogram (p10–p90 spread 0.26 s); the hook covered
t∈[186.4, 437.3].

**Operator context that reframes §1z-c:** walking UNDER the bridge is not
normally possible — it is a glitched state, replicated only 2–3 times this run,
and the capture's final move command is one such crossing.

### 1z-f.1 The registered predictions

* **P1 — healthy on every observable, but its floor is UNMET.** Zero
  `plane_repair` rows, zero 0x002C sends of any kind, zero `[plane-repair]`
  prints; the due-ladder's 15 transitions are `plane-legal` ×8 / `off-mesh` ×7
  and it **never even armed** — because not one of the 202 position reports
  (170 0x003D + 32 stops, ALL accepted, zero trust refusals) ever claimed a
  plane the mesh does not offer at its point. The 4 `plane_echo` rows fall
  under P1's registered echo-without-fire clause and cross-check cleanly
  (below). The shortfall the record keeps: the session is **7.8 min against the
  registered ≥15-min floor** — §3.5's free-play extension did not happen, so
  the first prospective healthy data point is real but under-exposed. The next
  ordinary session at full length completes it.
* **P2 — UNREAD, and the premise is the finding.** The wall-press control never
  produced its signature: the pressed body **slid along the compound wall at
  ~94 u/s** on a ~180 u diagonal instead of freezing — the longest
  byte-identical accepted-report streak in the whole session is **0.837 s**
  against the 8 s floor. Zero exposure to the freeze test, honestly unread. Two
  live observations survive: the reported position poked in and out of the
  compound's undecoded footprint (six of the seven `off-mesh` ladder
  transitions are this window), so the disarm work was split between
  `plane-legal` AND `off-mesh` — the ladder's healthy churn observed live for
  the first time; and the blocked-client-streams-frozen premise (which the
  08-22 session's 10.6 s frozen stream proves for SOME geometry) does not hold
  at this wall. A future P2 needs a pinning corner, not a slidable wall.
* **P3 — MET with two orders of magnitude to spare.** Section C on the bin:
  1,064 deduped samples, **73 stacked-ground, 293 impossible** (the biggest
  plane harvest the arc has taken; r5bridge's whole capture held 8); 24
  distinct on-deck stints against a floor of 6 crossings.
* **P4 — UNREAD, as the registration expected.** No lock. The heal remains
  untried; the trigger's live silence through this run's exposure is the
  specificity evidence, not the heal's.

### 1z-f.2 The echo census found a NEW relay subclass — and "never invents" survives its third test

Recomputed independently of the tripwire from all **349** plane-bearing sends
(every one 0x0029, parsed off the wire, checked against the mesh at its own
packet point): **4 wrong-plane, 7 off-mesh-point (the separate mild class, all
in the press window), 338 legal** — and the 4 match the tripwire's `plane_echo`
rows 1:1. Against the corpus: healthy 0/285 (§1z-d.1), the lock 43/65, **R6
4/349 — the first nonzero census outside a lock session, and every one is the
glitch on the wire.** All four are **router one-leg answers relaying the
client's own `MOVE_TO_COORD` dest plane** — the client clicked under-deck
points and named plane 0 for them; `router_answer_click` relayed the click's
slot-2 verbatim. §1z-d measured the server as a faithful relay on the REPORT
channel; this extends it to the CLICK channel. The server's own tracked plane
(the send's second word) was the client's latest accepted report's plane every
time — no stale state. **And the server never authored a leg into the
under-deck volume**: 84/88 sends into the deck footprint are legal plane-37
deck traffic, every router-computed waypoint is mesh-legal, and the final
under-crossing's click was answered with a route OVER the deck (leg 1
plane 37) — the client went under by its own click-driven, **report-silent**
movement (a 62 s stretch around echo #4 has zero position reports).

### 1z-f.3 The carry's mechanism: grants correct, walking channel stale — fully client-internal

The episode census (per-record planes, no dedupe): **18 impossible-plane
episodes totalling 60.7 s of the 251.0 s armed window** — 17 "declares 37 on
{0}" flanking the bridge, 1 under-deck (§1z-f.4).

* **Impossible plane alone does NOT break path resolution.** Walker sites
  (`agapi_setdest`/`chcli_advance`) fired inside 13/18 episodes; the other
  four show 139–607 u of live in-episode body drift; 67 clicks and 85 path
  queries land inside the windows. **No episode reproduces the r5stuck
  signature** (clicks+queries with a dead walker and a frozen body). The lock
  needs more than a wrong plane word — consistent with §1z-e's corpus carries
  and sharpening §1z-c's reconstruction: the lock's resolve failure is a
  further condition, not a consequence of the word alone.
* **These carries are NOT decode gaps.** The same ground scores CLEAN
  (0/192 declared-37) before t+68 with re-planes exactly at the decoded landing
  lines (x=−1643/−2852 — the client's own re-plane line coincides with our
  portal columns to the unit, the strongest deck-decode corroboration yet);
  afterwards the declared-37 smears up to **2,611 u past the east landing**
  and flips 0↔37 mid-ground — no fixed undecoded surface produces that.
* **The mechanism, settled by a per-site tabulation of the 60 mixed-plane
  ticks** (`r6_tiebreak.py` — this is where one lane's reconstruction died: it
  read the correction path as the poisoner, the other lane read it as the
  corrector, and the columns decide). On points offering exactly {0}:
  **`reseed` carries plane 0 in 17/17 records and `teleport` in 30/34 — the
  grant-install channel wrote the CORRECT plane — while the client's own
  `setter`/`bake` carry the stale 37 in 17/21.** ALL 74 of the run's reseeds
  and 130/270 teleports fall inside the episode windows (24 % of the capture):
  the correction machinery fires exactly while the walking channel misdeclares,
  and loses. With 0/202 reports impossible and 4/349 sends impossible (all
  click relays), **every wire input during the carries was clean — the stale
  plane lives entirely client-side**, in the walking/bake channel, and the
  sync copy shows the same 37 during the big carries. RECONSTRUCTION: the
  walking channel's plane rides the client's own state (§1x's chain — movement
  never reads the resolve), so no send-side policy can prevent a carry; the
  repair's report-keyed trigger remains the only server-side handle.

### 1z-f.4 The under-bridge is a GLITCH, and the 9/198 doctrine gets its boundary

Mesh ground truth (trapezoid-level, no sampling): plane 37 is a closed
17-trapezoid lens (x −2852..−1643, y 6301..6638) whose entire footprint offers
ONLY {37} (581/581 fine-scan points, zero plane-0 overlap), with unmeshed void
on the flanks and **exactly two portals, one at each landing line — there is no
under-deck ground of any plane and no legal path into the under-deck region.**
The displayed body's under-deck record: ONE episode (E18, the capture's final
records — entry at (−1657.2, 6438.1) plane 0, 14 u inside the east landing, at
t≈431, **open at capture end**: the operator's final crossing, with `--stop`
landing mid-traversal). The other 1–2 replications left only their clicks on
the wire (the four echoes at t=241–402, dests spanning the footprint) — under-
deck movement is click-driven, report-silent, and commit-sparse
(sample-and-hold), so the bin structurally under-samples it; 2–3 replications
against 1 resolved episode is consistent, stated, and not a count.

**RECONSTRUCTION, triply supported: retail's own mesh lacks under-deck
walkable ground, and the under-deck client is OUTSIDE its own navmesh.**
(a) our byte-exact parse of the client's own pathing chunk has no surface
there; (b) the operator reports normal walking cannot enter — which an absent
surface predicts and a real-but-undecoded floor would contradict; (c) while
under, the client declares plane 0, which the location does not hold.
**The 9/198 client-right-by-default doctrine is NOT touched on its own
channel** — it was measured on position REPORTS, and this run's 202 reports
were all legal (the under-deck points were never reported from, only clicked
to). What R6 adds is the doctrine's boundary: a client-named plane in a CLICK
dest can be a glitch-state's word, and the send path relays it. r5bridge's 8
anomalies reclassify identically (6 east-side carries paired with correct
plane-0 reseeds + 2 under-deck at (−2821.9, 6404.3) — the operator's original
two under-walks): **§1z-c's "deck-over-ground, both directions" reading is
revised — neither class was a decode gap.**

### 1z-f.5 What this leaves

The heal is still untried; the next trial is the same runsheet run to its
15-minute floor (with the P2 wall swapped for a pinning corner or the control
dropped). Filed: the ZERO-LEAD field-4 carry probe (§1z-e.4) still stands;
whether the click-relay subclass should ever be answered differently at a
{37}-only dest is a policy question the twice-refused rewrite doctrine says to
leave alone absent behavioural evidence. The alignment constant
(`tick/1000 − 750664.395`) and the lane scripts are in `r6/scoring/` for the
next reader.

---

## 1z-g. R6b — P1's floor MET, a SECOND stuck class found and healed BY A GRANT, and all four locks now tell one story

**OBSERVED 2026-08-29 evening (session `authsrv-20260829T142904`, 16.33 min of
active play; client capture `vault/research/movecode/r6b/movehook.bin`, 19,058
records, both controls FIRED, ring 58%, ended by its own timer — it ran 15 min
against RUN-R6 §6's `--minutes 16`, a deviation nothing scored rests on;
scripts in `r6b/scoring/`; alignment `t = tick/1000 − 754527.563`).** Scored by
four lanes plus two follow-up censuses. Corrections to my own quick look, which
the lanes caught: the session holds **30** echo rows, not 34; the stuck sits at
t=951.9–969.2, not in the [990, 1118] window I guessed; and t=990–1004 is
report-silent glitch movement with a LIVE walker, not a stuck. The JSONL was
still growing during scoring (the `--hold` window); all numbers are from a
frozen snapshot ending t=1526.37.

**Operator context:** ~7:30 in they found the NE bridge (deck + shallow water,
both meant to be walked); they saw "a lot of snapbacks"; and near the end they
S-pressed to a stop inside the west bridge's inaccessible under-path, got
stuck, and got unstuck by idling a few seconds.

### 1z-g.1 The predictions, closed

* **P1 — MET, floor and all.** 16.33 min of active play (floor ≥15). Zero
  fires on all three surfaces; the ladder's 11 transitions are `plane-legal` ×6
  / `off-mesh` ×5 — never armed. Echo census recomputed independently:
  **30/797** wrong-plane sends (R6: 4/349; healthy corpus: 0/285), matched 1:1
  to the tripwire; 29 are the known click-relay subclass and 1 is new in
  label class only — a routed chain's TERMINAL leg carrying the click's dest
  plane. All 30 sit at the two glitch structures; under the amended clause
  they refute nothing. The 9/198 false-fire class stayed unreal in a session
  whose operator DID get stuck.
* **P2 — UNREAD, and proposed RETIRED.** No corner press was attempted (§6
  allowed that). But the control's question is now answered by natural play:
  the `plane-legal` disarm got R6's press-window flutter, and the `off-mesh`
  disarm got an **11.16 s live demonstration** here (the stuck's own frozen
  stream, disarmed on every row). Both disarm clauses have live evidence; a
  synthetic control adds nothing they didn't.
* **P3 — continuity numbers** (already MET in R6): 217 stacked / 221
  impossible on 3,059 deduped samples. **New:** carries now appear on ordinary
  ground far from any bridge — clusters declaring 29/24/31/32 on {0} across
  the whole map (largest n=61 at (−6940, 3494)) where R6's 17 carries all
  flanked the west bridge. Section A: 82 deep off-mesh, 73 of them the stuck
  window (max 20.2 u, the under-path void); zero at the NE hill.
* **P4 — UNREAD by the letter** (no fire, so the 0x002C heal is still
  untried) — **but see §1z-g.3: the heal MECHANISM was corroborated live by a
  grant that wasn't the repair.**

### 1z-g.2 The stuck: a SECOND class, structurally invisible to the shipped repair

t=951.911–963.073: **31 accepted 0x003D reports, one byte-identical coordinate
(−2250.758, 6347.810), plane 0, 11.16 s, max gap 1.385 s** — the freeze and
live-stream halves of the lock signature, fully present; replayed through the
shipped tracker, an on-mesh point would have fired at +5.24 s. It never armed
because the point is **OFF-MESH** (`containing()` = {}; the under-path void):
every row hit the off-mesh disarm, and `plane_at()` returns None there — **the
repair has neither authority nor a fix plane at an off-mesh freeze. Confirmed
coverage gap**, filed as an owner policy question rather than patched: the
off-mesh clause's reason is the 9/198 doctrine's "no authority to say
anything", and arming there means inventing a plane. Two mitigations lower the
severity: this class self-heals if the victim idles ~3 s and clicks (measured
below), and the on-mesh lock class — the one that never self-heals — is the
one the repair covers.

Onset (RECONSTRUCTION on observed anchors): a catch-up teleport snapped the
displayed body 756 u east onto the sync copy's position mid-grant-walk; the
operator's S-press cancelled the click-walk and parked the body off-navmesh,
where the walker could not resolve an origin. **The dead walker was then
measured in keyboard form**: `agapi_setdest`/`chcli_advance` **0 hits for
~20 s** against 34 `chcli_dir`, 30 clicks and 30 path queries — r5stuck's
signature, reproduced live. And the operator's mash actively sealed it: **30
consecutive clicks were kbd-dropped** by the 3.0 s keyboard-authority window.

### 1z-g.3 The HEAL, corroborated by accident

The recovery is on both tapes end to end: **5.69 s of idle** → the next click
outlives the keyboard-authority window and draws a **ROUTED answer whose leg 1
carries plane 37** (the server's copy had drifted; route() crossed the deck
portal — that is where the fresh word came from) → the sync copy bakes 37 at
**+9 ms** → the local walking channel flips 0→37 at **+25 ms**, still at the
frozen point → first `agapi_setdest` at **+72 ms** → the body moves at
**+81 ms**. The server then abandoned its leg on the next keyboard report and
the body walked to the client's OWN click dest — **the grant's contribution
was the PLANE WORD, not the destination.** §1z-d.2's heal reconstruction ("the
plane word is what the path queries read") was UNVERIFIED; **it now has a live
corroboration: a plane word delivered by a grant revives a dead walker within
~100 ms.** (Why a plane heals an off-mesh origin: the word selects the layer —
at that (x, y) the deck polygon exists and the ground does not.)

### 1z-g.4 All four locks, one story

The in-lock fresh-plane census, run over every lock on record
(`r6b/scoring/r5stuck_grants.py`, `locks_grants.py`):

| event | in-lock plane-bearing sends | fresh (≠ poison) | in-lock answered clicks | outcome |
|---|---|---|---|---|
| r5stuck (41) | 33 | **0** — all echo 41 | **0** (82 kbd-drops) | locked till give-up |
| Ascalon 08-27 (29) | 11 | **0** — all echo 29 | 0 routed (zero-lead only) | locked till force-close |
| K1 08-27 (31) | 3 | **0** — all echo 31 | 0 routed | locked till force-close |
| r6b stuck (0, off-mesh) | — | **first fresh send heals** | 1 (after 5.69 s idle) | **healed in 81 ms** |

**A lock persists exactly as long as every send echoes the poison — and a
mashing victim structurally suppresses the one channel that could deliver a
fresh plane** (kbd-drop eats every click within 3 s of keys), while the
zero-lead echo path faithfully relays the poison by design. The 0x002C repair
is the fresh-plane source that depends on neither idling nor luck; its premise
now carries r6b's live corroboration. Registered expectation for the first
true repair fire: **the restamp heals within ~100 ms of receipt**, the r6b
timing. The folk remedy also falls out: "stop pressing and click" works for a
click-capable victim because idling releases kbd-drop — r5stuck's victim
mashed to the end and never got a click through.

### 1z-g.5 The NE bridge — the first BY-DESIGN stacked pair, and it is DECODED

Plane 42, 17 trapezoids: **its mid-span genuinely overlaps plane 0 — 359/747
fine-scan points offer {0, 42}** (deck over shallow water, exactly as the
operator described), with two portals (SW ramp, NE end). The arc's first
confirmed by-design deck-over-walkable-ground, and our decode HOLDS it — the
west bridge's {37}-only footprint is the contrast, not the norm. The two
{42}-only echoes are ordinary click relays at deck-edge spots outside the
water overlap. **The hill ascent stayed on mesh** — zero deep off-mesh among
83 body samples covering it — so whatever blocks normal entry up the hill is
invisible to the 2-D decode (RECONSTRUCTION: the client's slope/collision
layer — possibly tag 13's skipped colliders, §1x; filed, not settled).

### 1z-g.6 The snapbacks, quantified — and two instrument findings

On movesync's two-arm bar over the accepted report stream: **2 hard jumps,
0.13/min of span** (R6: 0; the R3-era configs: 1.31/5.69/11.88; retail: 0) —
**both glitch-placed** (one IS the stuck-release; one trails a NE plane-42
carry). Zero hard jumps in plain walking; P1's healthy claim stands with a
stated caveat: the wire bar sees only 7 % of the span (report-silent click
play is invisible to it), and the operator's rubber-banding lived there — 172
client-side reseeds (88 % inside glitch states; §1z-f's "ALL 74/74 inside
impossible-plane episodes" does not reproduce verbatim in r6b — the coupling
holds over the union of glitch states), and 7 scoreable teleport drags ≥150 u,
5 of them at the NE bridge. Instrument findings the next scorer needs:
**bake/setter records carry click-dest installs** (4,680 of ~4,700 have a
same-tick `agapi_setdest` prefix), so per-interval speed bars on the hook
stream are disqualified (they flag known-good walking at 400–700 u/s), and
section A's early "deep off-mesh transients" inside prop outlines are most
plausibly dest-install records, not body positions.

---

## 1z-h. THE `MapFindPath` RETURN TAP IS BUILT — a second emulation shape, the answer on tape, and `OURS-FAILED` split in half

**BUILT 2026-08-29 (HANDOFF-PLANE §4.2), not yet run against a client.** Four
lanes of disassembly against the pinned 38797 image priced it first; the build
is `content/movecode.toml`'s four `mapfindpath_ret*` rows plus capture **v7**.
Every address and every claim below came out of the client's own bytes.

### 1z-h.1 What the disassembly settled, including one refutation

The working hypothesis was "at a `__cdecl` ret, esp is back where it started, so
the existing six-arg read works unchanged and the out-pointers now aim at
written memory". **Half confirmed, half refuted, and the refuted half would have
silently corrupted every capture.**

* **CONFIRMED, and it is what makes the tap cheap:** all four exits are
  byte-identical `8B E5 5D C3` — `mov esp,ebp / pop ebp / ret` — so esp at every
  ret is EXACTLY the esp the entry hook saw. `mov esp,ebp` makes it
  path-independent (the differing `add esp,N` and pop counts cannot matter), ebp
  is written exactly once in the body, and no branch targets an epilogue, so no
  path evades it. The six-arg read needed no change at all.
* **REFUTED — arg2's slot is CLOBBERED.** The callee caches `to` in ebx and then
  reuses the caller's arg2 slot as FPU scratch: `fstp dword ptr [ebp+0xc]` NINE
  times, the first three before any branch, so it is unconditional on all four
  paths. At every ret `[esp+8]` holds a float. Copying the entry row's
  `deref_arg_b = 2` onto a ret row would have dereferenced a float as a point
  pointer — and `readable()` can ACCEPT it, since 10000.0f is `0x461C4000`, a
  plausible committed address in a 32-bit client. Sixteen bytes of unrelated
  memory would have been stored as "the destination" and scored OFF-MESH,
  reading exactly like the decode gap the tool exists to find. **`to` is
  readable at the ENTRY only**, which is why that row stays and why the two
  records must be joined rather than one replacing the other.
* **The signature is closed from the body AND both callers:** arg3 = float range
  (300.0f at snap gate 2, 10000.0f at click-to-move), arg4 = maxCount,
  **arg5 = `int* outCount`**, **arg6 = `point* outPath`**, stride 16, elements
  `{float x, float y, int plane, int}` — the same shape as `m_point`. Both
  callers branch on `*outCount` and NEITHER reads eax; eax is leftover scratch
  and is four different kinds of leftover at the four exits. **The two range
  constants are corroborated by the corpus, not just by the disassembly:**
  `pathdiff` over r6b's 935 captured queries reports exactly two callers —
  `0x00605807` (snap gate 2, 102 queries) and `0x0081AF56` (click-to-move, 833)
  — with range min 300.0 and p50/max 10000.0. The static read of two `fld`
  constants and the live census of 935 calls agree.
* **The exit list is complete at four**, checked rather than assumed: a byte
  scan of all 581 body bytes finds five `0xC2`/`0xC3` and the fifth is a phantom
  inside `call 0x47f660`'s displacement; the linear decode closes to the byte on
  eleven bytes of `0xCC` padding at `0x0070A0D5`. **One caveat stated rather
  than discovered later:** the function sets up no SEH frame, so a C++ exception
  from a solver callee would unwind past all four rets and the query would be
  recorded as unanswered.
* **The four exits are NOT four outcomes.** `0x0070A0D4` is two semantically
  different exits sharing one epilogue — the ordinary completion (the collapse
  loop's three early exits jump to `0x0070A0CE`, inside that epilogue) and the
  fallback-solver path (four rejection tests, including a PLANE MISMATCH at
  `0x0070A035`, all jump to `0x0070A0AE` and run `call 0x721a30`). The record
  says WHICH DOOR; `out_count` says WHAT ANSWER. `0x0070A0AD` is the RARE arm
  (the collapse consumed the whole buffer), which is the opposite of what its
  position suggests.

### 1z-h.2 What landed

* **A second emulation shape.** Every site was `55 push ebp` until now, which is
  what let the handler emulate ONE instruction (Q12(d)); the ret sites are
  `C3 ret` and emulate `eip = [esp]; esp += 4`. Both shapes keep the property
  that made the entry rule safe — a one-byte instruction has no interior, so a
  one-byte patch cannot land mid-instruction. `gensites.py` now checks each
  byte against **its own row's shape**, which is TIGHTER than the global `0x55`
  it replaced (an entry that decayed into something else is still caught), and
  refuses an unrecognised shape rather than defaulting.
* **Three structural refusals the bytes cannot express**, because each is a
  silent-garbage bug: a ret row that sets `deref_arg_b` (the float above), one
  that sets `deref_agent` (ecx is scratch at a return), and any row naming a
  shape the handler does not emulate. All five refusals are proven to fire.
* **The asymmetry between the shapes, and it decides an error path.** At an
  entry, failing to emulate loses a sample. At a ret there is no safe skip —
  leaving EIP on the `0xCC` re-traps forever — so the fallback restores the
  byte, rewinds, and marks the site DISARMED, so a sidecar zero is attributable
  to us rather than to the client.
* **Capture v7**, appended: `esp` (on every site), `have_out`, `out_count`,
  `out_n`, `out_path[16]`. 264 → 344 bytes per record.
* **The join is (tid, esp), and the key audits its own premise.** Because esp at
  a ret must equal esp at the entry, a pair whose values disagree REFUTES §1z-h.1
  rather than being a bad record — `_pair_mfp` refuses it, counts it, and both
  `readhook`'s v7 section and `pathdiff` print it. An instrument has to be able
  to report that the thing it was built on turned out to be false.
* **`have_out` keeps "could not read it" and "the client answered ZERO" apart**,
  the `have_fence` lesson — and here the distinction IS the measurement, because
  pathCount == 0 is the registered prediction. `out_n < out_count` records
  truncation rather than hiding it (capacity 4 points: snap gate 2 asks 4 and is
  captured whole, click-to-move asks 9).

### 1z-h.3 The result that does not need a run: `OURS-FAILED` was over-counting

`pathdiff` scored three-valued, and `OURS-FAILED` — "we found no route where
the client asked one" — **assumed the client had found one**. It cannot have
been checked, because the answer was not on tape. With v7 it splits:
`OURS-FAILED` (we failed, the client succeeded — our bug, now measured),
`THEIRS-FAILED` (we routed, the client returned 0 — §4.2's lock prediction),
and **`BOTH-FAILED` (neither found a path — NOT our bug, and every one of these
was previously counted as ours)**. The size of that over-count is unknown until
a v7 capture exists, and it bears directly on MOVECODE-Q2's headline. The
control that makes the claim real is in `test_movehook.py` §17e: the same
query, scored by the old path, comes out `OURS-FAILED`.

### 1z-h.4 Tests, and the one honest gap

`test_movehook.py` gains **§15b** (the emulation's arms counted against its
`c->Eip` assignments — §15's `continue`-scanner structurally cannot see a
missing `else`, which is exactly how this change could have crashed the client)
and **§17/§17e** (44 checks: the rows, all five refusals, v7-is-appended, the
pairing and its esp refusal, and the five-valued split with its control). Floor
118 → **153**, re-counted per section off a real green run. §9's positive
control was corrected in the same commit — it served `0x55` everywhere, which
is now a WRONG client — and the four ret names joined §14's COUNTED tuple,
where a stride would decimate the pairing while `hits` stayed whole.

**The gap, stated plainly:** no offline test proves a persistent `0xCC` at a
`ret` resumes correctly on real hardware. §7/§16 inject into a 32-bit `cmd.exe`
where every site fails to arm — deliberately, which is why the handler's hot
path is never executed by a test. What IS proven offline: the DLL compiles and
loads with the new shape (§6/§7/§16 green), the rows match the pinned image's
bytes, and the reader/pairing/verdict logic behave. The emulation itself is a
live-run question, and the first ordinary session answers it.

---

## 1z-i. R7 — THE RETURN TAP RAN, AND THE CLIENT'S OWN PATHFINDER FAILS EXACTLY WHEN ITS PLANE IS IMPOSSIBLE

**OBSERVED 2026-08-29, the tap's first live run** (`vault/research/movecode/r7/`,
capture v7, 5,627 records, both controls FIRED, ended by `--stop`; session
`authsrv-20260829T163…`; scored by four lanes). The operator walked, clicked
rocks, deliberately triggered under-bridge walks, and **ended the run standing
underneath the west bridge** — which is why the capture contains what it does.

### 1z-i.1 The instrument: it works, and the design's premise held on hardware

* **214 entry hits, 214 `ret4` hits — exact 1:1**, and `ret1/ret2/ret3` fired
  **zero** times. The sidecar shows no `NEVER ARMED` marker on any of them, so
  the zeros are "never taken", not a dead patch — the distinction that census
  exists for.
* **214/214 paired on (tid, esp), ZERO esp mismatches.** The premise §1z-h.1
  rests on — esp at a ret equals esp at the entry — held on every live
  invocation. It is corroborated by a route that never touches esp: across the
  214 pairs, `retaddr`, `arg1`, `arg3`, `arg4`, `arg5`, `arg6` are
  **bit-identical** entry-vs-ret while **`arg2` differs 214/214** — the
  clobber §1z-h.1 predicted, confirmed live. Five fields matching while the
  sixth changes proves both records are live reads of the SAME addresses.
* **The refuted half, made concrete:** the ret's arg2 slot holds 179 distinct
  plausible float values (0.0 ×36, then 196.37, 987.93, 1703.37, …). Those are
  the values that would have been dereferenced as point pointers had
  `deref_arg_b = 2` been copied onto the ret rows.
* **`ret1`'s zero is positively EXPLAINED, not merely observed**: its guard is
  `dist²(from,to) ≤ FLT_EPSILON`, and the closest query in the whole run misses
  it by a factor of **4.4e10** (minimum separation 72.6 u). That is the
  strongest form an arm census can take.
* **Cost**: on 211 of 214 invocations both int3 round trips *plus* the client's
  own navmesh solve completed inside one 15.6 ms timer quantum. A
  self-calibrating estimator (calibrated on `setter`→`bake`, an interval of
  known trap content) puts one handler at ≲33 µs, the ret tap at ~7 ms over a
  196 s run (**0.004 %**), and the whole 19-site instrument at ~0.09 %. The
  naive "windows with a query vs without" comparison was **refused** as
  uninterpretable — it is structurally blind (every ret is the next seq after
  its entry), confounded (a query *is* a moment the player had stopped), and
  r6b, which has **no ret sites at all**, shows the same or larger inflation.

### 1z-i.2 THE RESULT: pathCount == 0 ⟺ an impossible from-plane, exceptionlessly

The 10 `pathCount == 0` answers are not scattered. Classified by whether the
declared from-plane is one our mesh offers at that (x, y):

| from-point | n | pathCount == 0 |
|---|---|---|
| on our mesh, plane **matches** | 187 | **0** |
| on our mesh, plane **mismatches** | 10 | **10** |
| off our mesh entirely | 17 | **0** |

**Exceptionless in both directions.** Nine of the ten are inside the plane-37
deck lens declaring plane 0 — the operator's underwalks — in one 5.2 s window
plus the capture's final query. And the internal control is decisive: inside
that same footprint, **31 queries declaring plane 37 all returned > 0 while 9
declaring plane 0 all returned 0**, and one pair 1.2 s apart (seq 4628 vs 4785)
carries **bit-identical from-point x and y dwords** — `0xC508D354` /
`0x45C92E61` — with only the plane word differing, 37 → 0, and pathCount going
1 → 0. The discriminator is isolated to the plane word: not the location, not
the destination, not the range.

> ⚠ **CORRECTED 2026-08-30 (§1z-o).** The last clause is FALSE. The two queries
> share their from-point x/y dwords and differ in **caller, range, maxCount AND
> destination** — `seq 4628` (ret `0x0081AF56`, range 10000, maxCount 9, dest
> (−2062.85, 6422.47)) against `seq 4785` (ret `0x00605807`, range 300, maxCount 4,
> dest (−2012.97, 6361.00)). Only the FROM-POINT is held identical. The pair is the
> best single observation in the run and it is **not a controlled A/B**; say so
> when quoting it.

### 1z-i.3 §1z-c.3's inferred link is now OBSERVED

§1z-c.3 said in terms: *"we observe the queries and the silence after them, not
the client's failure to resolve."* Both halves are now on tape and joined. Mean
site count in the 60 ms after the answer returns:

* `pathCount > 0` (n=204) → `agapi_setdest` **0.95**, reseed 0.02, teleport 0.05
* `pathCount == 0` (n=10) → `agapi_setdest` **0.00** (10/10), reseed **1.00**,
  resync 0.70, setposition 1.10, teleport 0.70

The complete chain, observed ten times: **click → query from a mismatched plane
→ pathCount 0 → NO setdest → the correction machinery fires, fence SHUT.** The
positive control sits 1.07 s after the last failure: same click→query path,
from-plane 37, pathCount 1, setdest **fires**, fence open. The fence reproduces
§1z-c's reading independently (43/43 SHUT in the mismatch window against 5/84,
0/49, 0/32 in on-deck, recovery and healthy windows minutes apart), and the
6.34 s `setdest` gap at t=165.3 is the only one of the capture's top eight long
gaps that contains any query at all — it contains eight, every one pathCount 0.

**This CORROBORATES the §1z-c LOCK reconstruction**, and it explains §1z-g's
heal-by-grant: a fresh plane word restores the *input* the client's own solver
needs. **Two caveats stated rather than found later:** r7's state was
**transient** (5.2 s, self-clearing) where §1z-c's was persistent, and **the
body was not frozen** — so "the client cannot resolve" is corroborated, "the
body cannot move" is not. The run ends **on a failure, mid-onset, under the
bridge.**

### 1z-i.4 The OFF-MESH 29.4 % is NOT our decode gap

61 of the 63 are off because the **click destination** is unwalkable — the
operator clicking rocks, cliffs and water — and **the client's own solver
agrees every one of them is unwalkable**. Quoting 29.4 % as a decode-gap rate
would be wrong twice over: wrong about the cause, and taken from a run whose
operator was deliberately clicking at scenery. `OURS-FAILED` and `BOTH-FAILED`
both read **0**.

### 1z-i.5 MY SHAPE METRIC WAS A TAUTOLOGY, and it is fixed

The `AGREE 144` this run first reported was **vacuous**, and I suspected it
because every row read "endpoints 0.0 u apart". Confirmed two ways: the callee
**overwrites `outPath[count-1]` with the requested destination verbatim**
(`0x0070A04E` / `0x0070A053`), and `route()` ends at the goal by construction —
so the comparison was destination-vs-destination. Measured: the gap is exactly
0.0 on 129 of 131 comparisons, **`DIFFER` never fired once in 214 queries**, and
a deliberate **800 u** perpendicular detour scored PERFECT AGREEMENT.
Disqualified under the repo's own rank-a-known-bad-arm rule.

**Replaced with symmetric Hausdorff** over the two polylines, with the query's
own from-point prepended to the client's buffer (measured: the client's
`out_path` omits the start — its first waypoint equals the from-point in 1 of 86
answers, p50 446 u away). The new metric ranks every known-bad arm worse than
the truth and responds monotonically to displacement. Two other candidates were
**rejected by the same rule**: first-waypoint ranks a known-bad straight line
*better* than the truth (our route is a bare 2-point chord on 42 of 86 rows),
and leg-count is blind to perpendicular displacement.

**The honest re-score, and the finding the old metric hid:**

| verdict | old | corrected |
|---|---|---|
| AGREE | 144 | **97** (45.3 %) |
| DIFFER | 0 | **34** (15.9 %) |
| UNCOMPARED (truncated) | — | **13** (6.1 %) |
| OFF-MESH / THEIRS-FAILED / OURS-FAILED / BOTH-FAILED | 63 / 7 / 0 / 0 | unchanged |

**On 42 of the 86 rows where the client returned a bent path, our route is a
bare 2-point straight line** — all previously scored 0.0 u AGREE. Truncation is
now its own verdict: scoring a non-comparison as agreement is what inflated the
count by 13. `test_movehook.py` §17f pins the metric against the known-bad arm
and demonstrates the disqualified form beside it (floor 153 → 157). **The
five-valued split of §1z-h.3 stands** — THEIRS-FAILED reads `out_count` directly
— only the shape axis was empty.

### 1z-i.6 Filed, not fixed

* ~~**`pathdiff --map auto` ranks the WRONG map first.**~~ **FIXED, §1z-j
  below.**
* ~~**`readhook`'s motion denominator**~~ **FIXED, §1z-k below — and it was
  three defects, not one.**
* ~~**`nearest_walkable` over-reports off-mesh depth by up to 3×**~~ **FIXED,
  §1z-l below.**
* ~~**`RET_MAX_POINTS` should rise 4 → 9**~~ **DONE, §1z-m below — as capture
  v8, so the r7 capture stays readable.**

---

## 1z-j. THE MAP IDENTIFIER PICKED THE WRONG MAP — the score had an AREA TERM, and the guard beside it only looked one way

**FIXED 2026-08-29, desk-only.** §1z-i.6 filed this; it is closed here.

### 1z-j.1 The defect, in both halves

`pathdiff --map auto` scored each candidate mesh by *the fraction of captured
endpoints that land on it* — **which has an area term by construction: a bigger
mesh swallows any point cloud.** On r7, a map-280 capture, **Sparkfly Swamp
scored 99.3 % against map 280's own 81.8 % and WON.** `auto` refused only
because of its 0.20 margin rule, with 2.5 points to spare.

Measured over five labelled captures, the shipped score put the true map first
in **2 of 5** — and both of those "wins" were ties at margin 0.000.

The guard beside it could not catch this either. It warned only when coverage
fell **below 50 %**, and its own text said *"a wrong map produces 100 % OFF-MESH
and looks like a result"* — it was built entirely for the direction where a
wrong map looks **BAD**. The direction that actually fools a reader is the
other one: believed on r7, Sparkfly reports **OFF-MESH 3 (1.4 %) instead of 63
(29.4 %)** — the wrong map makes our decode look **20× better**, and OFF-MESH is
the MOVECODE-Q2 signal the tool exists to produce. **A guard that only fires
when the answer already looks wrong is not a guard.**

### 1z-j.2 The fix: a second term with no area in it

The client's own **plane word**. Every query's from-point carries the plane the
client believed it was on; on the right mesh that plane is one `containing()`
offers there, and on a wrong mesh it is a coincidence. The term is
**conditioned on the points that landed**, so mesh size cancels out of it.

**Restricted to NON-ZERO planes**, and that restriction is what makes it sharp:
plane 0 exists on every mesh and covers most of it, so a point declaring 0
agrees with a wrong mesh by coincidence — plain plane agreement still reads
59–67 % on wrong meshes. It falls back to all-plane agreement when a capture
has no non-zero declarations, which is honest rather than clever: such a
capture has no plane signal and should land under the refusal bar.

Score = `on-mesh fraction × non-zero-plane agreement`. Measured over the same
five labelled captures:

| capture | true map | old score | new score | new margin |
|---|---|---|---|---|
| r7 | 0x287B3 | **WRONG** (Sparkfly) | ✅ | 0.799 |
| run2-2026-08-27 | 0x1B97D | ✅ (tie, 0.000) | ✅ | 0.875 |
| r6b | 0x287B3 | **WRONG** (Sparkfly) | ✅ | 0.613 |
| r5bridge | 0x287B3 | **WRONG** (Ascalon) | ✅ | 0.438 |
| run3-isle | 0x287B3 | ✅ (0.071) | ✅ | 0.071 |

**2 of 5 → 5 of 5.** Under the new score Sparkfly ranks **11th of 13** on r7
despite its 99.3 % coverage, because its plane agreement is 0 %.

**THE REFUSAL THRESHOLDS ARE UNCHANGED** (`best < 0.6` or `margin < 0.2`
refuses), and that is deliberate: *the score was the broken part, not the
guard.* run3-isle — 7 queries with **zero** non-zero-plane points — still falls
under the bar and is refused rather than guessed, which is the right answer for
a capture with no plane signal. §18 asserts the thresholds are unchanged, so a
future weakening cannot be smuggled in as "making the fix pass".

### 1z-j.3 And the other half: the cross-check now speaks in both directions

`cross_check_map()` scores the **named** map against every candidate with the
same discriminator and says so when it loses. It never overrides the operator —
an explicit `--map` is a decision — it only refuses to stay silent. On r7 with
`--map 0x46305` it now prints `ANOTHER MESH FITS THIS CAPTURE BETTER` and names
map 280, immediately above the flattering `OFF-MESH 3` it would otherwise have
handed a reader unchallenged.

`test_movehook.py` §18 pins both halves against a **real** known-bad arm rather
than a constructed one — the mesh that actually beat the true map — plus the
control that the correct map produces no warning (a guard that fires on the
right answer too is noise). Eight checks; archive-dependent, so the floor does
not move.

---

## 1z-k. THE MOTION WINDOW — one expression, three defects, and the reader had been CRASHING on run 1

**FIXED 2026-08-29, desk-only.** §1z-i.6 filed the first of these; looking at it
properly found two more in the same line.

The world census computed `max(ptime) - min(ptime)` over every record of an
object. That is wrong three ways:

**(1) An unset stamp is not a timestamp.** Exactly **two records per object** —
the run's first `setter` and `bake`, both at t+0 — carry `ptime == 0`: an agent
stamp the client had never set. They drag `min` to zero and inflate the
denominator by the whole pre-capture uptime. On r7 that turned 193.5 s into
280.6 s and printed **"in motion 61.8 %"** where the truth is **87.8 %** — a
**27-point error from 2 records in 1,785**. It is in **every v4+ capture in the
corpus**, not just r7. The existing "impossible leg" guard cannot catch it:
those records carry `stop == 0` too, so `stop > ptime` is false and they are
never examined — **that guard tests the LEG; this defect is in the STAMP.**

**(2) Motion could exceed its own window.** `stop` is a *future* arrival the
client has predicted, so a leg can legitimately end after the last observation.
Merely dropping the zeros still produced percentages **over 100** (107.9 % on
run3-isle). We can only claim motion during the window we actually observed, so
legs are now **clipped into it** rather than the window stretched to fit them.

**(3) It crashed on v1–v3.** Those records have no `ptime` field at all, so
`readhook.py --bin` raised `KeyError` and **produced no report** for run 1 — the
arc's only v1 capture, and §1c's whole evidence base. `test_movehook.py` §4
pins *"a v1 capture still parses"*, and that was true of the **parse** and never
of the **report**. Two separate sites had to be fixed; the second was found by
the new test rather than by reading, which is the point of writing it.

**Corrected corpus figures** (previously all understated, some grossly):

| capture | printed | corrected |
|---|---|---|
| r7 | 61.8 % | **87.8 %** |
| r6b | — | 72.8 % |
| r4a | — | 100.0 % |
| run3-isle | 95.3 % (and 107.9 % once de-zeroed) | **99.0 %** |
| r5stuck | — | **0.0 %** — the lock, correctly reading zero motion |
| run-2026-08-27-ascalon (v1) | **CRASH** | `UNAVAILABLE`, with the reason |

The exclusion is **counted and printed**, never silent: *"2 record(s) carried an
UNSET position stamp and are excluded"* — because "we ignored two records" and
"there were none" are different facts, and the first is the one that explains a
number. `test_movehook.py` §19 pins all three with the control that matters —
the OLD expression, on the same fixture, must still produce the inflated
denominator, or the section pins nothing. Floor 157 → 163.

---

## 1z-l. `nearest_walkable` — an AXIS CLAMP is not a nearest point, and the off-mesh depths were up to 3× too big

**FIXED 2026-08-29, desk-only.** Closes the third defect §1z-i.6 filed.

### 1z-l.1 The defect

`nearest_walkable` found its candidate by clamping y into the trapezoid's span
and then x into its edges **at that y**. That is an *axis clamp*, and it is the
true nearest point only when the edge it lands on is axis-aligned. Against a
**slanted** edge it walks along y and then along x instead of projecting
perpendicularly.

The docstring said the error was "bounded by the edge slope over the radius,
and within the small radii this is for" — which was true of the caller it was
written for (`authsrv`'s routable-origin rescue, radius 16) and **quietly
stopped holding the moment an offline scorer asked at radius 600.**
`noclipscore.py` quotes this value as *"how far off-mesh"*, so the error rode
into every depth an r6/r6b-era scoring pass published.

**Measured over r7's 67 off-mesh endpoints against dense boundary sampling**
(deliberately not against another analytic formula — validating an analytic fix
with the same analytic formula proves nothing):

| | before | after |
|---|---|---|
| worst ratio vs truth | **2.967×** (77.43 u where truth is 26.10 u) | **1.000×** |
| worst absolute over-report | **64.91 u** | **0.00 u** |

A second, latent defect in the same function: the returned distance was
recorded **before** the boundary nudge moved the point, so a caller could get a
post-nudge point beside a pre-nudge distance. It did not manifest on r7's 67
(0 of 67) but it was real, and it is fixed by recomputing after the nudge.

### 1z-l.2 The fix, and the part that only mattered once the big error was gone

The exact nearest point of a convex quad is the nearest point on its **four
edges** (or the point itself when inside) — four perpendicular projections
clamped to their segments. Cost is paid back by a **bounding-box lower bound**
that skips a candidate before any projection, so the large-radius case this was
wrong for is the one the early-out helps most.

Then a second pass was needed. With the 65 u error gone, the **nudge** became
the dominant term: a flat `1e-3` of the way to the trapezoid's centre is ~0.5 u
on a 500 u trapezoid, and the worst ratio was still 6.78× at a point 0.08 u
off-mesh. The nudge now **escalates** — 1e-6, 1e-5, 1e-4, 1e-3, 1e-2 — taking
the smallest step that clears the float boundary. That is what took the worst
over-report from 0.57 u to **0.00 u**.

### 1z-l.3 What it does not change, and the tests

`pathmap.py` is on the **server path**, and `authsrv`'s ROUTER-B5 origin rescue
is the other caller. Nothing there moves: `test_pathmap` (80 checks),
`test_router` (68), `test_routerbench` (48) and `test_noclipscore` (10) are all
green, including the benchmark that guards route() latency against the 50 ms
tick. The rescue asked for a *routable point* and still gets one; what changed
is that the distance beside it is now true.

`test_pathmap` §12d pins the geometry on a **synthetic 45° trapezoid**, because
a real mesh cannot isolate the property: the exact answer is the perpendicular
foot at 35.355 u and (25, 25), while the old axis clamp returns 50.000 u and
(50, 50) — and the **control asserts the old arithmetic still produces 50.000
on that same fixture**, so the check is pinning a real distinction rather than a
tautology. §12e pins the point/distance pairing over **596** real boundary
probes; its first draft found **one** probe and would have passed vacuously,
because these trapezoids are hundreds of units wide and a fixed step off the
centre never leaves them — the probe is now derived from each trapezoid's own
edge. Floor 75 → 80.

---

## 1z-m. `RET_MAX_POINTS` 4 → 9 — capture v8, and v7 stays readable on purpose

**DONE 2026-08-29, desk-only.** The last of the four defects §1z-i.6 filed.

**Nine is not a percentile.** It is the larger of the two callers' own
`maxCount` — snap gate 2 pushes 4 (`006057F4 6a04`), click-to-move pushes 9
(`0081AF43 6a09`) — read statically from both frames and confirmed live on r7,
where `arg4` was 9 or 4 and **nothing else, 214/214**. At 9 the buffer *cannot*
truncate for either known caller, which **retires** the standing "compare
shapes only on the untruncated ones" caveat rather than shrinking it. Sizing to
a percentile of observed counts would have left a caveat alive for the sake of
a few dwords.

What 4 actually cost, stated rather than assumed: **nothing** for the registered
`pathCount == 0` prediction (the COUNT is exact at any capacity, and snap gate 2
— the caller that prediction is scored on — never truncated), and shape
comparison on **16 of r7's 214**, which is the `UNCOMPARED` row §1z-i.5 had to
introduce.

**The price, stated:** `out_path` sits in every record of every site, so this is
20 dwords × NCAP = **+2.5 MiB** of the client's address space (10.75 → 13.25
MiB) for a field only **3.8 %** of r7's records used. The ring is a fixed record
*count*, not a byte budget, so it does not shorten a run.

### 1z-m.1 A NEW VERSION, not a wider v7 — and that was the whole call

r7 is a **v7** capture with a 16-dword `out_path`, and it is the arc's only
capture carrying the client's own answers. Redefining v7 in place would have
made `reclen` disagree and **orphaned it** — precisely the failure §4 pins with
*"a v1 capture still parses"*: versioning that orphans the evidence is worse
than not versioning at all. So both layouts live in the table, and r7 still
parses and still scores identically (AGREE 97 / DIFFER 34 / UNCOMPARED 13 /
THEIRS-FAILED 7 / OFF-MESH 63).

**A second version-coupling was fixed with it.** Two readers quoted the module
constant `RET_MAX_POINTS` as *this record's* capacity — which becomes a lie the
moment the writer moves, reporting "capacity 9" at a v7 record that holds 4.
Capacity is now `ret_capacity(r)`, derived from the record's own `out_path`
length, so it is right for every version by construction.

The C keeps the **literal** `out_path[36]` rather than `[RET_MAX_POINTS * 4]`,
and that is a requirement rather than a style: §11 parses `rec_t` out of the C
with `\[\s*(\d+)\s*\]` to compare it field-by-field against the reader's table,
and an expression would drop the widest field in the record silently out of the
one check that can catch a reader/writer disagreement.

Tests: §17 now asserts both layouts exist with 4 and 9 points, that the C and
the reader agree on version 8, and that `ret_capacity` reads a v7 record as 4
and a v8 record as 9. Floor 163 → 169. **The DLL was rebuilt and §6/§7/§16
re-injected green**, so the widened record loads and runs.

---

## 1z-n. The plane-disagreement census — the repair's licence, priced

HANDOFF §D asked for this and named four things it would settle. It settles all
four, overturns the arc's own mesh-labelling practice on the way, and produces
one result the handoff pre-registered as the headline: **a non-zero fire count.**

Everything below is re-runnable rather than quoted:

```bash
python toolkit/clientscan/planecensus.py            # census + repair replay
python toolkit/clientscan/planecensus.py --echo     # the tripwire's denominator
python toolkit/clientscan/planecensus.py --identify # score the map identifier
python toolkit/clientscan/test_planecensus.py       # 54 checks, floor 54 (was 29/14 when first written)
```

### 1z-n.1 The mesh label was wrong for half the corpus, and the fix is IN BAND

**`version.map_id` is a login constant, not the live map.** It reads **148 in
1,206 of 1,212 captures** while the corpus's real geometry spans at least
`0x1B97D`, `0x287B3` and `0x287D3` — and map 148's own spawn is ~15,000 u from
where most reports sit. It is emitted before `--map`/`--file-id` rewrite
anything; grep `client asked for map` in `authsrv.py`.

**The server records the mesh itself.** Every capture carries a `sent` record,
opcode 405, labelled `INSTANCE_LOAD_SPAWN_POINT(file N)`. Over all 1,212 files:
**zero captures name two ids, and all 12,215 position_reports are attributed.**
That beats both prior practices — `noclipscore.py` hand-pins map 280 and
`pathdiff.py` makes `--map` a value a human types from memory.

Two further witnesses agree and are kept as cross-checks rather than sources:
the harness `gamesrv.log`'s `MAP OVERRIDE: 280` / `[map] navmesh 0x287B3` line
(**176 of 176 agree, 0 disagree**), and its `[c1] GAME version: … world_id=…
player_id=…` line, which joins 1:1 to the capture's own `version` record across
1,201 keys with zero collisions.

⚠ **THE ARCHIVE IS PART OF THE PIN.** A file id does not name geometry alone.
`0x287D3` decodes to **27 trapezoids in `dat_study`, 55 in `-c2`, 2 in `-probe`
and 64 in `reskin-roster`** across the 17 vaulted archives, and `0x5F0B2` binds
in `-probe` ALONE. Scoring map 143's 318 reports against a 1-plane stub reports
**61.3% OFF-MESH** (195 of 318), which reads as a decode failure and is really an empty mesh.
Stub meshes are named and excluded from the headline, never averaged in.

**Why the headline survives that anyway:** the meshes that actually carry the
corpus — `0x1B97D`, `0x287B3`, `0x345CC`, `0xB602` — decode **identically across
all 17 archives** (`0x5D037` also does, but at 26 trapezoids it is a STUB and is
excluded from the headline, not a carrier), and running the census against `-probe`
instead of `dat_study` reproduces 11,754 / 670 / 259 / 208-51 / 239 unchanged.
`test_planecensus.py` §5 pins that invariance, and pins that a stub really does
move between the two, so the check cannot pass by comparing an archive with
itself. **Numbers about `0x287D3` and `0x5F0B2` are archive-scoped and must name
one; the headline is not.**

### 1z-n.2 The census

**12,296 reports scored.** Keep the two words apart: **12,757 are ATTRIBUTED**
(every report has a mesh id from its own capture), **12,619 are SCOREABLE**
against `dat_study`, and **12,296 enter the headline** once stub meshes are
excluded. "174 of 174 captures" is a statement about map ids, not about usable
geometry — 2 captures / 138 reports have no mesh in the default archive:

| | n | of |
|---|---|---|
| off-mesh — the mesh offers nothing | 805 | 6.5% of scored |
| on-mesh | 11,491 | 93.5% |
| **AGREE** — declared plane is offered | **11,232** | **97.75% of on-mesh** |
| **DISAGREE** | **259** | **2.25% of on-mesh** |

> Re-stamped 2026-08-30 evening (was 11,754 / 670 / 11,084 / 10,825): the
> owner's three RUN-R8-adjacent captures landed after the pin (+227/+228/+87
> scored, +135 off-mesh of which 127 are the abort's carve-park, **0 new
> disagreements, 0 new trips**). Re-derived over the as-of-pin corpus first:
> all four pinned figures reproduce EXACTLY, so this is corpus growth, not a
> moved constant — the corpus-counts-redden protocol, followed.

**Item 3 answered — the 9-of-198 failure class at corpus scale.** `plane_at`'s
docstring measures 189/198 = 95.5% agreement over four sessions. At corpus scale
it is **97.66%**, so the small sample was if anything pessimistic. The failure
splits two ways, both of which `test_noclipscore.py` already names
(`DECK_OVER_GROUND` / `GROUND_UNDER_DECK`, §1z-c):

* **208 (80.3%)** — client declares non-zero N, our mesh offers **only 0**. The
  bridge-over-ground class the docstring describes ("client says 12, we find 0").
* **51 (19.7%)** — client declares **0**, our mesh offers only non-zero N. The
  inverse. 11 of these are specifically `offered [37]`, which is R7's signature.

⚠ **CALL THEM DIRECTIONS, NOT CLASSES.** "Two classes" implies two mechanisms and
there is one. **All 259 disagreements have `|offered| == 1`** — not one is the
bridge-over-ground *stacking* the docstring pictures. It is a single coverage
defect with the roles swapped, and the two directions alternate inside one
capture — though NOT in `20260829T163930`, whose 11 rows are **all** the
inverse direction. An earlier draft said that trace showed both within 10 s; it
does not.

**Item 2 answered — what a declared 0 means.** It is a **real geometric index,
not a null sentinel**, and the numbers are asymmetric enough to act on:

| declared | agree | disagree | disagreement rate |
|---|---|---|---|
| 0 | 9,422 | 51 | **0.54%** |
| non-zero | 1,403 | 208 | **12.91%** |

A declared non-zero plane is **24× more likely** to disagree with our decode
than a declared 0. `pathdiff.py` refuses to reason from a declared 0 and the
repair draws its strongest inference from it; this says the refusal is the
better-calibrated of the two, but for the opposite reason to the one assumed —
0 is not noisy, it is the value we almost always *agree* with.

The bridge trace in capture `20260829T163930` shows the mechanism directly: the
client declares **37** on the deck (mesh agrees), flips to **0** at a repeated
byte-identical coordinate (mesh offers only 37), recovers to **37** (server-caused,
§1z-o.6)
8.9 s later, then declares **0** further on where the mesh does offer **[0]**.
The plane word tracks geometry; the disagreements are transients over ground we
have not decoded.

### 1z-n.3 ★ THE DISARM CLAUSE HAS NEVER ENGAGED — 0 of 259

**All 259 disagreements are unambiguous, and not one reaches the `ambiguous`
disarm.** Two precisions the first draft of this section got wrong: only **239 of
the 259 reach the trigger at all** (13 are `0x0047` stop-reports, 6 are refused,
1 has a null source, and the track sees none of those), and **"arms" is the wrong
verb** — passing the ambiguity door returns `"arming"`, which RESETS the hold
clock rather than advancing it. The zero is still a zero, and it is neither
reassuring nor an accident of sampling:

1. **At the repair's call site `plane_at`'s `prefer` branch is DEAD BY
   CONSTRUCTION.** The trigger calls `plane_at(x, y, prefer=plane)` only after
   proving `plane not in offered`, so `prefer in planes` can never be true and
   the function reduces to "one candidate, or None". The clause can therefore
   only fire on genuinely STACKED ground.
2. **Stacked ground is a fraction of a percent.** Whole-mesh scan at 8 u:
   `0x287B3` has 6,367 stacked cells of 3,796,950 on-mesh (**0.17%**), and
   `0x1B97D` 55,009 two-plane plus **3,529 genuine three-plane** cells of
   11,838,541 (**0.50%**). The commonest stacked set on map 280 is exactly
   `{0, 42}` — the NE bridge HANDOFF ★3 scanned. So "max |offered| is 2" is a
   fact about **where one operator walked**, not about the meshes.
   ⚠ And the walk **over-sampled** stacked ground — per map about **5.4× on
   `0x287B3` and 3.5× on `0x1B97D`**; the "10×" an earlier draft quoted pooled
   both meshes' visits against the SMALLER map's areal rate. Visited stacking is
   **194/11,491 = 1.69%** of on-mesh (194/11,084 = 1.75% before the 2026-08-30
   evening captures; the earlier 1.73% divided by 11,208, which
   still carried the stub meshes the headline excludes) against an areal
   0.17–0.50%. More walking narrows this
   zero's support; it does not confirm it.
3. **On the west bridge the clause is geometrically impossible.** Fine scan at
   8 u over 4,488 samples around R7's arming points: **plane 0 is offered
   nowhere**, and 100% of on-mesh samples offer exactly one plane.

**This CONFIRMS and sharpens HANDOFF ★3.** The safety test is not merely
inverted — over the whole corpus it has never once engaged. `test_planerepair.py`
proves the clause works on synthetic stacked geometry; what it has never had is
corpus exposure.

★2 is confirmed exactly. All three `arming` rows sit at points where the client
declares **0** and the mesh offers only **[37]**, and `plane_at` returns 37 — a
fire would have restamped the player up onto the bridge deck.

### 1z-n.4 ITEM 1 — the replay reproduces §1z-e.2 independently, and NOTHING MORE

> ⚠ **CORRECTION, SAME DAY, BEFORE ANYONE QUOTED THIS.** The first draft of this
> subsection called the replayed fire count "★ THE HEADLINE" and read the fires as
> members of ★4's *"the client is right and our decode's coverage is missing"*
> class. **Both halves were wrong, and the section was written without reading
> §1z-e** — the arc's own cycle trap, walked into while citing it.
> **§1z-e.2 had already run this exact replay** ("three sessions fire; zero fires
> anywhere else"), had already pinned the mesh per session in band, had already
> rejected the containment vote as §1v.3's wrong-map selector, and had already
> adjudicated all three sessions as **REAL LOCKS** — §1z-e.3's victim froze at one
> byte-identical coordinate and force-closed the connection **10.2 minutes later**.
> `RUN-R6.md` calls the same replay "the true-positive side".
> What follows is therefore a **corroboration**, not a discovery: an independent
> instrument, written without knowledge of §1z-e.2, reproducing its table to the
> row. That is worth something — it is a second derivation from a different
> code path — but it is not new, and calling a lock a false fire inverts the
> record.

Replaying `plane_repair_track` clause for clause over the corpus:

| | |
|---|---|
| **live fires (`kind == "plane_repair"`)** | **0** |
| **would-fire, replayed** — REPLICATES §1z-e.2 exactly | **5**, in 3 captures |
| longest HOLD streak accumulated | **15.25 s** against a 5.0 s hold |
| captures ever reaching `holding` | 4 |

The three sessions are §1z-e.2's three, with the same times and the same claimed
planes: `20260829T091543` (44.98 / 55.12 / 70.80, claimed 41 — the §1z-c lock),
`20260827T055221` (339.56, claimed 29 — lock #2), `20260827T212317` (115.88,
claimed 31 — lock #3). Two independent replays, written months apart in different
files, agree to the row.

**The live zero is not evidence of quiet.** The repair shipped
**2026-08-29 11:22:45 (`dcf9484`)**; all three would-fire captures predate it and
their harness logs carry no plane-repair banner. The trigger has never been armed
during a session that would have fired it.

All five would restamp the player **to plane 0**, and all five are "client
declares non-zero N, mesh offers only [0]". ⚠ **That shape is NOT by itself ★4's
class.** ★4 warns that an instantaneous geometry test cannot tell a deck we failed
to decode from a stale plane — which means the shape is *ambiguous*, not that it
resolves against the repair. §1z-e.2/e.3/e.4 resolved these three the other way,
on behaviour rather than geometry: each victim froze at one byte-identical
coordinate and stopped being able to play. Geometry supports that reading too:

A useful discriminator, measured to the NEAREST EDGE of the declared plane's own
trapezoids (a centroid reads hundreds of units away while a long thin deck passes
underfoot — measure to the edge):

| session | declares | mesh offers | nearest geometry of the DECLARED plane |
|---|---|---|---|
| `20260827T055221` | 29 | [0] | **1,563 u** |
| `20260827T212317` | 31 | [0] | **3,761 u** |
| `20260829T091543` | 41 | [0] | **90 u** |

At 1,563 u and 3,761 u there is no coverage story to tell: the declared plane's
geometry is nowhere near, so the plane word is stale and restamping to what the
mesh does offer is the correct repair. `20260827T212317`'s victim was frozen
byte-identically for 5.72 s while still emitting `0x003D` movement claims.

⚠ **`20260829T091543` at 90 u is the one that stays open, and it is also the
capture the repair was DERIVED FROM** — its 100 disagreements are **3 distinct
points**, one carrying **82 byte-identical accepted reports**, and `authsrv.py`
cites *"82 accepted reports, one coordinate"* in the trigger's own docstring.
Three of the five would-fires are the mechanism replayed against its own training
case, and its geometry is the one place a deck-edge coverage gap is plausible.
§1z-c adjudicated it a real lock on its dead-walker signature; that evidence, not
the geometry, is what carries it. **Do not quote "5 fires" without this.**

⚠ **AND THE DISCRIMINATOR IS WEAK.** Run over all **259** disagreements it puts
**114 in 50–200 u and 100 in 200–1,000 u** — a broad ambiguous middle — with
**38 clearly stale (>1,000 u) and 7 clearly underfoot (<50 u)**. (An earlier
draft quoted 113 / 100 / 17 / 7 over 237, which was the PRE-FIX 238-row corpus;
re-scored on 259 the stale bucket more than doubles, which strengthens rather
than weakens the reading.) It also **fails on
R7**, whose armings read 265–374 u ("ambiguous") while the client's own pathfinder
settles them outright (§1z-o). Geometry alone cannot adjudicate this class. The
instrument that can is the movehook return tap, and it has been run once.

### 1z-n.5 Item 4 — the `plane_echo` tripwire, with a denominator

**282 trips / 7,778 on-mesh player-agent sends ≈ 3.6%.** (Denominator 7,778 as
of the 2026-08-30 evening captures — was 7,543 at the pin, 0 new trips. This
read 281/7,542
until 2026-08-30, when a defect in `planecensus.label_captures` was found: it
dropped any capture with zero `position_report`s, and the echo channel scores
SENDS. The one capture it dropped holds the corpus's **only `0x002A`**, and that
send is a trip. `test_planecensus.py` now pins it.) The live tripwire has
logged **43**, in 3 captures, because it was introduced at `dcf9484` and has
watched three sessions. Its retrospective exposure is ~6.5× what it has seen.

⚠ **Quote it as ≈3.7%, never to three significant figures.** Two careful
independent measurements of this same quantity landed on 282/7,465 = 3.78% and
282/7,543 = 3.74%, differing only on a capture-labelling convention. The rate is
also **bimodal**: 75 of the 106 captures carrying player sends trip zero
times, and `20260829T091543` alone trips **43 of 84 = 51%** — a pre-`dcf9484`
capture, so the live tripwire missed the one session that would have supplied 43
rows by itself.

The decode was settled by CONTROL, not inference: it must reproduce the live
tripwire at **4 / 30 / 9** on `{132441, 142904, 163930}` before any rate is
quotable, and `planecensus.py --echo` prints that control first and prints a bare
COUNT with no rate if it fails.

### 1z-n.6 Is it a rate? Only if you say which denominator

**Disagreement is not ambient — it is bimodal.** Against a homogeneous binomial
null the dispersion ratio is **≈30, and ≈10 even after collapsing every frozen
repeat to a single event** (an independent re-derivation on the on-mesh
population got 35.0 and 11.1 against this section's original 29.2 and 9.3 — quote
the magnitude, not the digits; both agree the overdispersion is an order of
magnitude). The concentration is real, not an artifact of stuck clients
re-reporting.

⚠ **BUT SAY WHICH CAPTURES COULD HAVE DISAGREED. "157 of 174 carry exactly zero"
is a population conflation and this section published it for a day.** Of the 174
captures carrying reports, **40 sit on a stub or unbound mesh and CANNOT
disagree** — zero exposure, not a clean run. The honest split:

| | captures |
|---|---|
| carry `position_report`s | 174 |
| — of those, unscoreable (stub or unbound mesh) | **40** |
| **scoreable** | **137** |
| — with ≥1 disagreement | **17** |
| — genuinely clean | **120** |

So the rate is **17 of 137 = 12.4% of scoreable captures**, not 17 of 174. Among
the 120 clean ones, by ON-MESH report count — the only reports that *can*
disagree — **1 has zero on-mesh reports, 16 have 1–4, 23 have 5–19, 54 have
20–99, 26 have ≥100**, summing to 120. (Was 17 of 134 / buckets summing to 117
before the three clean 2026-08-30 evening captures: on-mesh 87 → the 20–99
bucket, 100 and 220 → ≥100.) (Two earlier drafts printed
11/38/27/55/24 summing to 155, then 41/16/23/53/24 summing to 157 — the first
counted on-mesh with stubs in, the second folded the 40 unscoreable captures into
the "clean" pile.) Say "24 captures of ≥100 on-mesh reports carry zero
disagreements"; never "157 captures are clean".

But the row count is the wrong unit for "how often": **259 disagreeing reports
are 123 distinct points.** The split is visible per capture and there are two
populations — `20260829T091543` is 100 rows over **3** points and
`20260827T055221` is 19 rows over **1**, while `20260826T095804` is 39 rows over
**39**. Quote points for frequency and rows only for exposure.

### 1z-n.7 A fifth instrument defect, and one that is NOT identified

`pathdiff.map_scores`' identifier can now be scored against real labels
(`--identify`). Of **58** identifications it ACCEPTS, **16 are wrong**: 28
accepted with non-zero plane signal, **0 wrong**; 30 accepted on the all-plane
fallback, **16 wrong**. Its own docstring expects that fallback to be worthless
and the refusal bar to catch it — at n = 3-5 points one mesh reaches 1.000 while
the runner falls below 0.8, so the margin passes.

⚠ **The cause is NOT identified and the obvious fix is not licensed.** All 16
failures share a second property exactly: their true answer is `0x287D3`, the
27-trapezoid stub. "No plane signal" and "the right mesh is nearly empty and
loses on coverage to anything" are **perfectly collinear on this corpus**.
Record the observation; do not ship "refuse when `nz_land == 0`" on the strength
of it.

### 1z-n.8 What this does NOT settle

* **Whether the heal works.** Untried. The census names the geometry to press
  against (the west bridge, where our mesh offers only the deck) but a lock is
  still not provokable on demand.
* **Whether the 51 inverse-class rows are decode holes or client transients.**
  The bridge trace favours transient-over-undecoded-ground, n = 1 episode.
* ~~**138 reports on `0x5F0B2`** are unscoreable and unknown.~~ **CORRECTED:**
  they are unscoreable *in `dat_study`* only. Bound against
  `vault/run/2026-07-29_221c13772c7a-probe/Gw.dat` the mesh loads (1 plane, 23
  trapezoids) and **all 138 score: 0 off-mesh, 138 agree, 0 disagree.** The first
  draft quoted a zero without asking what a non-zero would have required — this
  arc's own trap, committed while auditing for it.
* **Every timing figure still rides through movehook's 19 `int3` taps**
  (HANDOFF trap 6) — though this census is desk-only over the server's own
  records and does not depend on them.

---

## 1z-o. R7's SERVER side — the lock seen from both ends at once, and a morphology the trigger cannot catch

HANDOFF §D′ item 2 asked for this: R7's *"9 ladder rows and 9 echo rows"* were the
last unpublished part of the arc's most decisive run. They are published below.

**Read §1z-i first — it is the other half of this run and it is already scored.**
§1z-i.2 holds the client-side result (`pathCount == 0` ⟺ an impossible from-plane,
187 / 10 / 17) and §1z-i.3 the causal chain. This section re-derived that table
independently and reproduces it to the row — corroboration from a second
instrument, not a new result. **What is new here is the SERVER side and the JOIN.**

⚠ **Say "exceptionless" with the restriction attached, or it is false.** Scored
over all 214 queries as *"the declared plane is not among those offered"*, the law
breaks 17 times — but all 17 sit at from-points where `containing()` returns **[]**,
so our mesh offers nothing and has no opinion to be wrong about; the client routed
from them 17 of 17. The surviving form is sharper: **restricted to the 197 queries
whose from-point our mesh can speak about, separation is perfect in both
directions, 197/197** (Fisher exact two-sided p = 5.2e-17). The 17 are a
measurement of OUR decode (MOVECODE-Q2), not a break in the plane law.

⚠ **A framing this section was commissioned to write has been REFUTED by its own
data.** HANDOFF §D′ item 2 prescribed writing R7 up as *"a near-miss on a false
fire, not an encouraging arming"*. That is wrong. Plane 0 was not undecoded ground
the client was standing on; it was **invalid at that point by the client's own
navmesh** — the client's pathfinder answered `pathCount = 0` there seven
consecutive times and started answering again the instant the declared plane
flipped to 37 (§1z-o.4). Had the repair fired it would have restamped 0 → 37,
which is what the client declared 8.9 s later — after OUR OWN grant put a 37 on the
wire (§1z-o.6). **R7's arming was a TRUE POSITIVE.**

⚠ **The "natural experiment" is suggestive, not a controlled A/B — state it that
way.** The pair at `0xC508D354` / `0x45C92E61` shares its from-point x and y dwords
bit-for-bit and answers 1 on plane 37 and 0 on plane 0, 1.19 s apart. But the two
queries have **different callers** (`0x0081AF56` range 10000 vs `0x00605807` range
300) and **different destinations**. Only the from-point is held identical. It is
the best single pair in the run and it is not an experiment anyone designed.

### 1z-o.1 The readout, in full — and it is a TRANSITION log

R7 is `authsrv-20260829T163930-c1.jsonl` (map 280 / `0x287B3`; `--zero-lead`,
`--grant-suppress`, `--cast-stop=pin`, **`--router`** and the plane repair all ON —
204 `router_route` / 94 `router_leg` rows are on the tape, so clicks were answered
by our own routes, same as R6/R6b). It carries 9 `plane_repair_due` rows and 9
`plane_echo` rows. The ladder logs on a CHANGE of
`why`, so "9 rows" is **9 transitions, not 9 reports** — every count taken from it
must say so.

```
t=135.96  LADDER plane-legal  plane=0   (-5819.59,-313.15)
t=255.07  LADDER arming       plane=0   (-1908.33,6407.31)   <- lock onset
t=255.07  ECHO   op41 plane=0 offered=[37] (-1908.33,6407.31)
t=255.26  LADDER holding      plane=0   (-1908.33,6407.31)
t=255.81  ECHO   op41 plane=0 offered=[37] (-1908.33,6407.31)
t=256.54  ECHO   op41 plane=0 offered=[37] (-2015.65,6426.14)
t=256.91  LADDER arming       plane=0   (-2006.48,6424.53)   <- clock RESET
t=257.43  ECHO   op41 plane=0 offered=[37] (-2015.65,6426.14)
t=257.76  LADDER holding      plane=0   (-2015.65,6426.14)
t=257.98  ECHO   op41 plane=0 offered=[37] (-2015.65,6426.14)
t=258.55  ECHO   op41 plane=0 offered=[37] (-2119.76,6453.45)
t=258.96  ECHO   op41 plane=0 offered=[37] (-2089.10,6531.36)
t=259.23  ECHO   op41 plane=0 offered=[37] (-2075.07,6441.84)
t=263.98  LADDER plane-legal  plane=37  (-1822.78,6424.68)   <- recovery (OURS, 1z-o.6)
t=272.02  LADDER off-mesh     plane=0   (163.75,6572.05)
t=272.04  LADDER plane-legal  plane=0   (161.83,6569.94)
t=284.95  LADDER arming       plane=0   (-2067.12,6515.66)
t=284.95  ECHO   op41 plane=0 offered=[37] (-2067.12,6515.66)
```

All 9 echoes are opcode `0x0029` and all carry plane **0** where the mesh offers
only **[37]**.

⚠ **They are NOT all zero-lead, and an earlier draft of this section said they
were.** Decoding each echo's co-timed send (`<HIffHH` — op, agent, x, y, field3,
field4; all joined within 0.2 ms) splits them **5 `ZERO LEAD` / 4
`AGENT_MOVE_TO_POINT(… ROUTER one leg)`**. That matters because the design licence
usually cited here — `test_position_trust` pinning verbatim echo — **covers the
zero-lead site only**. The router leg is a separate sender.

Provenance is still **100% client-supplied for all nine**: the one-leg send takes
`pf, ps = plane_first, plane_second` and its override is gated behind
`if D1_LEAD:`, and `D1_LEAD` is `False`. So five echo the client's *reported*
plane and four echo the plane word off the client's own `MOVE_TO_COORD`. Three of
the nine sit at points the client never reported, and one precedes the client's
first report of its point by 0.9 s — so "echoing the report back" is the right
picture for five of them and not for all.

⚠ **THE TWO CHANNELS DO NOT COUNT THE SAME WAY, and "9 and 9" invites the error.**
The ladder is gated on `if why != state.get("pr_why")` — a REASON TRANSITION.
`plane_echo` has no such gate; `_note_wire_move` calls `rec.event` on every bad
send and only the console print is transition-gated ("Logged per send, printed on
transition"). So **9 echo rows are 9 sends; 9 ladder rows are 9 transitions over
101 evaluated reports**, of which 9 disagreed. The two nines are a coincidence.

⚠ **AND THE LADDER ALONE IS INCOHERENT — an instrument defect, filed here.**
Replaying the trigger per report shows a `why == "arming"` at **t=257.4250** on
(−2015.65, 6426.14) that is NEVER LOGGED, because the previous `why` was already
`"arming"` on a *different* point (−2006.48, 6424.53). The capture therefore reads
`arming @ A` → `holding @ B`, and `holding` requires `pr_point == pt`, so the
logged sequence describes a state machine that cannot exist. **A transition log
keyed on the reason string cannot represent a re-arm onto a new point.** Anyone
reconstructing the streak from the ladder alone gets it wrong.

⚠ **Which is why the 1.02 s below is NOT a ladder number.** The ladder's last
logged `holding` for that streak sits at t=255.2553, **held = 0.185 s**. The 1.021 s
peak is at t=256.0915 — a hidden row. Quoting the streak requires the
`position_report` stream; the ladder cannot produce it.

### 1z-o.2 Why it never fired: the streak decomposition

Replaying the trigger over R7's own reports gives four streaks:

| streak | window | held | at |
|---|---|---|---|
| 1 | 255.07 → 256.09 | **1.02 s** | (-1908.33, 6407.31) |
| 2 | 256.91 → 256.91 | 0.00 s | (-2006.48, 6424.53) |
| 3 | 257.43 → 257.98 | 0.55 s | (-2015.65, 6426.14) |
| 4 | 284.95 → 284.95 | 0.00 s | (-2067.12, 6515.66) |

Cause of death per streak, since "it never fired" is the arc's actual question:
streaks 1 and 2 were killed by an `arming` on a NEW point (99.6 u and **9.3 u** of
movement — the point test is exact float equality, so 9 u is as good as 99);
streak 3 by `plane-legal` at t=263.98, with a 6.005 s report gap that would have
produced `stale-stream` anyway had the point held; streak 4 because **no further
`0x003D` report exists in the capture at all**.

**Max 1.02 s against `PLANE_REPAIR_HOLD` = 5.0 s — 20% of the bar.** This
confirms `HANDOFF-PLANE.md`'s "1.021 s" and adds the decomposition. Nothing here
was near-miss luck, and the cause of death differs per streak (below). The track
compares the reported point by EXACT equality, so a new coordinate re-arms.

### 1z-o.3 ★ TWO LOCK MORPHOLOGIES, and `HOLD = 5.0` only catches one

This is the section's decision-relevant finding.

| | continuous freeze | intermittent freeze |
|---|---|---|
| example | `20260829T091543` (§1z-c), `20260827T055221` (§1z-e.3) | **R7** |
| behaviour | one byte-identical coordinate for tens of seconds — the doctrine block's *"82 accepted reports over 33 s"* | freeze ~1 s, jump ~100 u, freeze ~0.55 s, jump |
| longest hold | 15.25 s / 5.72 s | **1.02 s** |
| does `HOLD = 5.0` catch it? | **yes** | **structurally NO** |

R7's victim was locked on every other observable — its own pathfinder was
answering `pathCount = 0` at those exact coordinates, `agapi_setdest` never fired
after them (§1z-i.3) — and the repair could not have helped it, because between
freezes it emitted a new coordinate and re-armed the clock. **The trigger's hold
is calibrated on the morphology it was derived from.** Whether 5.0 s is the right
bar is now a question with evidence on both sides rather than one.

⚠ Do NOT read this as "lower `HOLD`". A shorter hold trades a miss for a false
fire, and this section's n is **one intermittent lock**. It is a question to put
to the owner beside the specificity evidence (§1z-e.2), not a change to ship.

### 1z-o.4 ★ THE JOIN — one lock, two instruments, by coordinate AND by clock

The server-side ladder and the client-side query failures are the SAME events, and
proving it needs no clock alignment because the coordinates are exact floats:

| | n |
|---|---|
| distinct client-side points answering `pathCount == 0` | 8 |
| server-side echo points | 6 |
| server-side `arming`/`holding` points | 4 |
| **zero-answer points that are ALSO server echo points** | **3** |
| **zero-answer points that are ALSO server arming/holding points** | **2** |
| **CONTROL — points where the client's query SUCCEEDED that appear anywhere in the server's plane channel** | **0 of 192** |

The control is what makes this a join rather than a coincidence: the server's plane
channel does not light up wherever the client happens to query. It lights up on the
failures, and only there. (-1908.33, 6407.31) and (-2015.65, 6426.14) are
simultaneously the server's two `holding` coordinates and points where the
client's own pathfinder could not resolve its position.

**This is the first time the plane lock has been observed from both ends at the
same coordinates**, and it closes §1z-c.3's original gap from the server side as
§1z-i.3 closed it from the client side.

**And with the clock offset adopted (§1z-o.14), the window reads as one story.**
Inside `t = 255.070 … 263.981` — the server's arming → holding → `plane-legal`
episode — the client issued 17 `MapFindPath` queries:

```
 256.183  from (-1908.33,6407.31) p0  mesh[37]  pathCount=0
 256.526  from (-1908.33,6407.31) p0  mesh[37]  pathCount=0
 258.105  from (-2015.65,6426.14) p0  mesh[37]  pathCount=0
 258.542  from (-2015.65,6426.14) p0  mesh[37]  pathCount=0
 258.948  from (-2119.76,6453.45) p0  mesh[37]  pathCount=0
 259.230  from (-2093.19,6520.99) p0  mesh[37]  pathCount=0
 259.433  from (-2080.52,6465.44) p0  mesh[37]  pathCount=0   <- last zero
 260.495  from (-2092.27,6364.60) p37 mesh[37]  pathCount=1   <- plane flips, answers resume
 260.917 … 263.511   10 more, all plane 37, all pathCount >= 1
```

**Seven consecutive zeros, every one declaring plane 0 where the mesh offers only
37, and the run of zeros ends on the report where the declared plane flips to 37.**
The two server `holding` coordinates are the first two rows. An eighth zero sits
0.90 s BEFORE the server's first `arming` — the client was already failing when the
ladder began, which is what a transition log looks like from the other side.

### 1z-o.5 ★ GATE 2 HAS FIRED — three times, in R7, and the cause is the plane word

`HANDOFF.md` carries this in a starred block:

> *"★ AND READ THIS BEFORE COSTING ANYTHING AGAINST GATE 2: it has n = 0 observed
> firings. … Every snap we have ever measured is explained by gate 1 alone.
> **Gate 2 is knowledge, not a lever. Do not build a fix against it.**"*

**That is REFUTED by R7's own return tap.** The claim was an inference from snap
statistics — 24 snaps, none beginning below gate 1's 299.33 u threshold, therefore
gate 2 is never reached. R7 measures the gate site directly instead, and it *is*
reached: `MapFindPath`'s two callers split **204 click-to-move (`0x0081AF56`) and
10 snap-gate-2 (`0x00605807`)**, the split §1d.6 identified and §1z-h counted. What
was never split by caller is the ANSWER:

| caller | pathCount | n | a `reseed` (`0x006022B0`) follows |
|---|---|---|---|
| gate 2 `0x00605807` | **== 0** | **3** | **3 / 3** |
| gate 2 `0x00605807` | > 0 | 7 | 0 / 7 |
| click-to-move `0x0081AF56` | == 0 | 7 | 7 / 7 |
| click-to-move `0x0081AF56` | > 0 | 197 | 0 / 197 |

**Exceptionless at 214/214**, and the second row is the control that makes it a
finding rather than a coincidence: gate 2's own queries do NOT produce a reseed
when they answer normally. Each of the three zero-answers is followed by `reseed`
**in the same client tick (Δ = 0 ms)**, then `teleport` and `setposition` — which
is the snap, exactly as §1 decodes it ("any of the three resyncs *every* async
agent via `0x006022B0`, a hard SetPosition").

**Why this was never seen before, stated so it does not look like an oversight:**
gate-2 queries are not rare — §1d.6's census counts them across all nine movehook
captures — but until §1z-h built the four `ret` sites, movehook was an ENTRY-ONLY
tap. The question was recorded and the answer was not. R7 is the return tap's only
run, so R7 is the only capture in which a gate-2 firing *could* have been observed.
The handoff's "n = 0" was true of the instruments that existed when it was written.

Gate 2 being *reached* is itself informative: gate 1 runs first, so on all ten
occasions separation was **below** 299.33 u. The handoff's inference fails not
because its 24 snaps were mismeasured but because it generalised from snaps it
could see to a gate whose site it was not watching.

**What fired it was the plane word.** The three points are
(−5880.50, 1492.71) declaring 17 where the mesh offers [0], and
(−2189.21, 6437.80) and (−1787.27, 6530.05) declaring 0 where it offers [37] —
the second of those being the natural-experiment coordinate itself, whose
plane-37 twin answered `pathCount = 1` 1.19 s earlier and did **not** reseed.

⚠ **This joins two threads the arc has kept apart.** The plane channel was filed
as a LOCK ("a plane desync is a lock where a position desync is only a warp") and
the snap as the WARP. They meet here: an impossible plane fails the client's own
gate-2 query, and the gate reseeds every agent in world 1. The plane channel is a
warp cause, not only a lock cause.

⚠ **What this does NOT license.** It does not make gate 2 a server lever — the
failing operand is still the client's own declared plane tested against the
client's own navmesh, and nothing we send writes it. ★4's refusal of "never emit
an impossible plane" is untouched. What changes is the costing: a fix aimed at the
plane channel now has a measured warp consequence to weigh, where before the
answer was "gate 2 never fires, ignore it".

### 1z-o.6 ★ WHO PUT THE 0 THERE — an ordered chain, and it points at US

R7's recovery is **not** the client healing itself, and an earlier draft of this
section said twice that it was. Both halves of the episode have our traffic in
them, and the ordering is by in-client `seq` — a monotonic counter — so it does
**not** ride the ±10 ms clock alignment.

**Recovery — server-caused, and this half is clean:**

```
259.445  OUR  ROUTER clip-fallback -> (-2092.27,6364.60)  f3=37 f4=37
         pf = _router_plane(pm, stop, cur_plane) = pm.plane_at(...)   <- OUR MESH
seq 4969 SYNC setter arg3=37   (+3 ms)
seq 4970 SYNC bake plane 37, target (-2092.27,6364.60)
seq 4986 LOCAL plane 37, m_point == (-2092.27,6364.60) bit-exact   (+1.05 s)
260.496  the client's next MOVE_TO_COORD declares 37 -- its first 37 since onset
```

That is the **only** 37 on the wire in the interval, and we computed it from our
own mesh. The client adopted our plane word and started answering its own
pathfinder again.

**Onset — probable, not proven, and it runs through our own plane-matching.**
At the onset the router path ran `a2_matched_field4(0, 37) -> 0`, overriding the
carry off the body's true plane 37 to the route's first waypoint plane, and the
chain that follows is on tape in seq order:

```
253.756  client 0x0047 stop-report, plane 37
254.157  client MOVE_TO_COORD -> values[2] = 0   (a DESTINATION plane, legitimately 0)
254.159  OUR  ROUTER leg 1/2, f3=0 f4=0          (carry overridden off 37)
seq 4781 SYNC setter arg3=0                       <- our f4 landing
seq 4785 GATE 2 queries from SYNC m_point (-2189.21,6437.80) plane 0 -> pathCount 0
seq 4787/4788/4790  LOCAL reseed -> teleport -> setposition   (the snap)
seq 4792 LOCAL now plane 0
```

**The propagation mechanism is the gate-2 reseed of §1z-o.5** — the same three
firings, and the middle one is SYNC's `m_point` at the instant of our own field-4
write. That ties the warp finding to our own wire.

⚠ **State it exactly this way and no stronger:** *our grant is the only identified
author of the agent's plane-0 word, by an ordered on-tape chain; the write into
the LOCAL copy is inferred, not observed.* Against a stronger claim: the client's
own click 2 ms earlier already carried a plane-0 word (a destination plane,
correctly 0); all 760 LOCAL `setter` calls pass `arg3 = 0xFFFFFFFF` ("leave
`+0x80` alone") yet LOCAL's plane changes four times in the episode, so **the
LOCAL copy's plane word is written by a path movehook does not hook**; and the
whole onset sits inside one 16 ms tick, which the alignment cannot resolve.

⚠ **AND THE OBVIOUS FIX IS A REGRESSION — this was tried, not reasoned about.**
`a2_matched_field4`'s docstring said "**for one `--d1-lead` send**" while three
router call sites invoke it with `D1_LEAD = False`, and that reads as a leak. It
is not. **Gating those three was actually applied and the tests run: it turns
`test_router.py`'s "first leg carries the corridor's plane, matched" RED.** The
asymmetry is the design:

* where field 3 is a plane **we** computed (the corridor plane, `_router_plane()`)
  field 4 must match it **unconditionally**, or a routed leg with `pd != pc`
  reopens the P-17 phasing door that ROUTER-B2 closed;
* where field 3 is the **client's own** plane passed through (the one-leg verbatim
  echo, "wire-identical to the shipped clear-line fire, planes included") the
  override is gated so the echo stays byte-verbatim outside the lead.

The real defect was the **contract line**, and it was wrong the day it was written
— `8cbcbc9` created the helper for `--d1-lead`, `995a515` (ROUTER-B2, same day)
added four router call sites and never revised it. **Fixed 2026-08-30**: the
docstring now states the rule, carries this counterexample, and says "do not fix
it by gating them"; `test_router.py` gained five locks pinning 3-ungated +
1-gated and the summary line, so the next reader who tries lands on the reason.
**Two independent analyses made this mistake; the third would have shipped it.**

What remains genuinely open is the PREMISE, not the plumbing: matching field 4
trades a phasing snap for a plane the body has not reached yet, and on a route
that crosses a seam R7 shows that trade going wrong. One observation, no fix
proposed.

### 1z-o.7 R7 SCORED AGAINST THE CORPUS — and the exposure control is the finding

§1z-o's numbers are a session's. §1z-n's are the corpus's. Neither means much
until R7 is placed in the distribution, and placing it turns up something the
single-session read could not: **R7's signature belongs to the session, not to
the geometry, and not to the session either — it belongs to the pair.**

Re-runnable, with the same instrument that produced the census:

```bash
python toolkit/clientscan/planecensus.py --focus 20260829T163930
```

⚠ **TWO DENOMINATORS, AND R7 READS DIFFERENTLY UNDER EACH.** §1z-o counts what
the plane-repair TRIGGER evaluates — accepted `0x003D` reports only — and gets
**9**. The census counts every `position_report` on a non-stub mesh and gets
**11** (the extra two are `0x0047` stop-reports, which the trigger never sees).
Neither is wrong. Say which rule is in force.

**Position.** R7 is a *small* capture with an *outsized* signature:

| | R7 | corpus | R7's rank |
|---|---|---|---|
| position_reports | 122 | 11,754 | 31 of 134 |
| off-mesh | 1 | 670 | 37 of 134 |
| DISAGREE (census rule) | 11 | 259 | **8 of 134** |
| distinct disagreeing points | 4 | 123 | — |
| direction N→0 | **0** | 208 | 15 of 134 |
| direction 0→N | **11** | 51 | **2 of 134** |
| `plane_echo` rows logged | 9 | 43 | 2 of 134 |

**Rate: 9.09% of on-mesh reports against the corpus's 2.34% — about 4×.** But it
supplies only 4.25% of the corpus's disagreeing rows and 3.25% of its distinct
points, and seven captures carry more. **Outlier in rate, mid-pack in volume.**

**★ R7 is 100% INVERSE where the corpus is 80% FORWARD.** The corpus splits
208 "client declares N, mesh offers only 0" against 51 of the inverse. R7 is
**0 and 11**. It therefore supplies **11 of the corpus's 51 inverse rows (21.6%)
out of a 122-report session** — and every one of the corpus's `offered [37]`
inverse rows. No other capture has a single one.

**★ THE EXPOSURE CONTROL — and it is not vacuous.** "Only R7 disagreed on
plane-37 ground" would be empty if only R7 stood there. It did not:

| capture | reports on ground our mesh calls [37] | disagreeing |
|---|---|---|
| **R7** | 41 | **11 (26.8%)** |
| R6 `20260829T132441` | **74** | 0 |
| R6b `20260829T142904` | 16 | 0 |
| `20260829T091845` | 5 | 0 |

**R6 had nearly twice R7's exposure and never disagreed once. 11/41 against
0/95, Fisher exact two-sided p = 6.5e-07.** ⚠ **The statistic stands; the reading
below is CORRECTED in §1z-o.8** — §1z-f.4's trapezoid ground truth resolves the
height ambiguity this paragraph hedges, and the answer is on-deck versus
under-deck, not session versus session. R7's own
disagreeing coordinates sit **18.6–50.4 u** from points those sessions stood on
and agreed at — the same bridge structure, not a separate place. ⚠ The mesh has
no height, so (x, y) proximity does not establish *physical* identity: R7 may
have been under the deck where the others were on it. That is the arc's standing
limitation and this control cannot lift it. What it does kill is the trivial
explanation, "only R7 went there".

**★ AND THE CONTROL RUNS THE OTHER WAY TOO.** R7 is not simply a
"disagreeing session": on plane-[17] ground it reported **34 times and agreed
34 times**, while `20260826T095804` disagreed **23 of 36** on that same plane
set. And R7 agreed 44 of 44 on plane-[0] ground. **Neither the session nor the
geometry alone predicts the signature; the pair does.** That is a sharper
constraint on §1z-o.6's "our own grant" chain than §1z-o.6 could state on its
own — whatever authored the plane-0 word was present in R7 and absent in three
identically-configured sessions on the same ground.

**Configuration does not explain it.** All three armed sessions ran the same
banner: `MAP OVERRIDE: 280`, navmesh `0x287B3`, **`--router` ON**, plane repair
ON. R6 and R6b are not a different policy; they are the same policy, more
exposure, no event.

**★ R7 IS THE ONLY ARMED SESSION THAT EVER DISAGREED AT ALL.**

| session | reports | disagreements | echoes logged | points |
|---|---|---|---|---|
| R6 | 202 | **0** | 4 | 0 |
| R6b | 225 | **0** | 30 | 0 |
| R7 | 122 | **11** | 9 | 4 |

Every prospective disagreement the repair has ever been in a position to see is
R7's. Three armed sessions, 549 reports, one episode.

**And the two channels are INDEPENDENT — do not use echoes as a lock proxy.**
R6b logged **30** echoes with **zero** client disagreements, three times R7's
echo count. The outbound channel measures what WE emit; the ladder measures what
the CLIENT declares. R6b's 30 are server-originated at glitch structures
(§1z-g); R7's 9 co-occur with a client that was failing its own pathfinder. A
session can be loud on one channel and silent on the other, and R6b is the proof.

### 1z-o.8 R6 AND R6b SCORED THE SAME WAY — two silences, and they are not the same silence

```bash
python toolkit/clientscan/planecensus.py --focus 20260829T132441   # R6
python toolkit/clientscan/planecensus.py --focus 20260829T142904   # R6b
```

Both scored ZERO disagreements, and §1z-f/§1z-g already read them as healthy.
What the corpus adds is **what each was in a position to disagree about**, which
is the only thing that makes a zero worth anything.

| | R6 | R6b | R7 | corpus rank (R6 / R6b) |
|---|---|---|---|---|
| position_reports | 202 | 225 | 122 | 13 / 12 of 134 |
| off-mesh | 15 | **47** | 1 | 17 / **3** of 134 |
| DISAGREE | **0** | **0** | 11 | — |
| `plane_echo` rows logged | 4 | **30** | 9 | 3 / **1** of 134 |
| reports on plane-[37] ground | **74** | 16 | 41 | — |
| reports on STACKED ground | 0 | **5** | 0 | — |

**R6 carries the corpus's heaviest plane-37 exposure and disagreed zero times.**
Its 74 reports are **54% of the 136 plane-37 reports in the whole corpus**, which
puts a number on §1z-f's own title claim ("the heaviest plane exposure ever
captured") for the first time.

**R6b has more echo rows than any other capture, and is the corpus's third most
off-mesh**, with zero disagreements — 30 echo rows against R7's 9. ⚠ **"Loudest"
is the wrong word and §1z-o.11 withdraws it:** R6b's echo RATE is 3.88% against
the corpus's 3.73% — dead ordinary. It has the most rows because it granted 774
times, more than any other armed session. R7, quiet by count, has the highest
rate of the three at 5.11%. That pairing is the proof that
**the two channels are independent**: the echo channel measures what WE emit, the
ladder what the CLIENT declares, and R6b is loud on the first and silent on the
second. Do not use one as a proxy for the other.

**⚠ AND R6 CORRECTS §1z-o.7's INTERPRETATION — the statistic stands, the reading
does not.** §1z-o.7 set R7's 11-of-41 against R6/R6b's 0-of-95 on "the same
ground" (p = 6.5e-07) and hedged that the mesh has no height. **§1z-f.4 lifts the
hedge, and the answer is not the one §1z-o.7 leaned toward.** Plane 37 is a closed
17-trapezoid lens (x −2852..−1643, y 6301..6638 — re-derived here, identical),
there is **no under-deck ground of any plane**, and the under-deck client is
outside its OWN navmesh, reached by a glitch rather than by walking. R6's
under-deck excursions were **click-driven and report-silent** — its 202 reports
were all legal, and its 4 echoes are the clicks. R7 REPORTED from under the deck;
R6 clicked under it and reported from on top.

So the honest reading is **on-deck versus under-deck, not session versus
session.** The two populations are not the same physical ground at all; they only
share (x, y), which is exactly what a heightless mesh cannot distinguish. §1z-o.7's
"whatever authored the plane-0 word was present in R7 and absent in three
identically-configured sessions" is **withdrawn** — what was absent in R6/R6b was
the glitch state, not the author.

**What survives, and it is better:** §1z-f.4 reached "the under-deck plane-0
declaration is a glitch-state word, not a decode gap" from MESH GROUND TRUTH, and
§1z-o reached "R7's plane 0 was invalid at that point" from the CLIENT'S OWN
PATHFINDER. Two independent instruments, one conclusion. **R7's arming was a true
positive, and it is now doubly supported.**

(One reconciliation, since a finer scan disagrees with §1z-f.4's wording: an 8 u
sweep of the lens bounding box finds **43 of 4,561 points offering {0, 37}**
against §1z-f.4's "zero plane-0 overlap, 581/581". All 43 sit at exactly
**x = −2852**, a single scan column on the west landing line. It is a
sample-on-the-edge artifact of the bounding-box sweep, not under-deck ground, and
§1z-f.4's interior claim stands.)

### 1z-o.9 ★ WHY THE DISARM HAS NEVER ENGAGED — the better answer

§1z-n.3 explained the `ambiguous` disarm's 0-of-259 by rarity: stacked ground is
0.17% of map 280. **That is true and it is not the main reason.** Scoring every
report that landed on stacked ground, corpus-wide:

| offered | reports | captures | disagreeing |
|---|---|---|---|
| `[0, 18]` | 154 | 14 | 0 |
| `[0, 46]` | 16 | 3 | 0 |
| `[0, 22]` | 11 | 1 | 0 |
| `[0, 26]` | 5 | 1 | 0 |
| `[0, 20]` | 5 | 3 | 0 |
| `[0, 42]` | 3 | **1 (R6b)** | 0 |
| **total** | **194** | | **0** |

**194 reports have stood on stacked ground and not one of them disagreed.** The
`[0, 18]` stack alone was visited 154 times by 14 different captures — this is not
an unvisited corner of the map.

**The structural reason: a stack offers TWO chances to be right.** The disarm
requires a report that is on a stack AND declares a plane that is neither of the
two offered. Offering two planes makes disagreement strictly less likely than
offering one, so the safety valve is **anti-correlated with the hazard by
construction** — it is least likely to be reachable exactly where it would be
needed. That is a sharper statement of ★3's inversion than rarity alone, and it
does not depend on how much of the map is stacked.

R6b is the corpus's only witness to the `{0, 42}` NE-bridge pair (§1z-g.5's
by-design stacked deck): **3 reports, all agreeing.** The entire live exposure of
the geometry ★3's table was measured on is three reports in one session.

### 1z-o.10 ★ THE CENSUS AGAINST THE ARMED CORPUS — 95% of it is replay, and the live 5% is confounded

§1z-n reads over 134 captures and states rates as if they were one population.
They are two. The repair shipped at `dcf9484`, **2026-08-29 11:22:45**; every
session before that ran with the trigger DISARMED, so every claim the census
makes about them is a REPLAY — what the repair would have done, not what it did.
Splitting on the harness banner (`"plane repair (default ON)"`, an artifact,
rather than on the timestamp, an inference):

| | ARMED | replay-only | armed share |
|---|---|---|---|
| captures | **3** | 131 | 2.2% |
| position_reports | 549 | 11,205 | 4.7% |
| DISAGREE | **11** | 248 | **4.3%** |
| distinct disagreeing points | 4 | 119 | 3.3% |
| reports on stacked ground | 5 | 189 | 2.6% |
| `plane_echo` rows LOGGED | **43** | **0** | **100%** |
| fires | **0 observed** | 5 replayed | **0%** |

**The two halves of the repair's case come from disjoint evidence.** Every firing
observation is counterfactual — all 5 would-fires are in sessions where the
trigger was not running. Every echo observation is prospective — the tripwire
shipped with the repair, so 43 of 43 logged rows are armed. **Nothing in the
record both fired and was watched.**

**Four armed harness runs exist, not three.** `20260829T163038` is
banner-confirmed armed and produced **no capture at all** — no `report.json`, no
frames, its `gamesrv.log` stopping at the startup banner. An aborted launch. So
"the repair has been armed four times" and "three armed sessions have data" are
both true and neither substitutes for the other.

**On rates, the armed slice looks REPRESENTATIVE — and that is the one
reassuring number here.** Disagreement per on-mesh report reads **2.26% armed
against 2.34% replay-only**; echo trips per on-mesh send, **3.33% against 3.81%**.
Three sessions on one afternoon reproduce the corpus rate. That is worth stating
because the opposite would have been easy to find.

#### ★ But the arming is perfectly confounded with `--router`

| | router OFF | router ON |
|---|---|---|
| **disarmed** | 055221 (1 fire), 212317 (1 fire), ~1,190 more | 091543 (**3 fires**), ~10 more |
| **ARMED** | **— EMPTY —** | 132441, 142904, 163930 (**0 fires**) |

**`--router` is ON in 14 of 1,210 banner-carrying runs (1.2%) — and in 4 of 4
armed runs (100%).** The cell "armed, router off" is empty. **The plane repair
has never once run without the router**, so its entire prospective record was
taken under a click policy that 98.8% of the corpus did not use.

That is not a small caveat, because the router is not a bystander on this
channel: it is the arm that computes its own plane words and matches field 4 to
them (§1z-o.6), and it makes the armed sessions **grant-dense** — 1,292 on-mesh
`0x0029`-family sends across 549 reports (2.35 per report) against the
replay-only corpus's 6,250 across 11,205 (0.56 per report), a **4.2× difference**.
The armed sessions supply **17.1% of all on-mesh grants from 4.7% of reports**.
So the echo rate's reassuring 3.33-vs-3.81 comparison is between populations whose
grant behaviour differs fourfold, and the echo channel is a function of grants.

The confound is not total, and the exception matters: **`20260829T091543` was
router-ON and disarmed**, and it supplies 3 of the 5 would-fires. So the firing
evidence is not purely a router-off phenomenon either. What has never been
observed is the diagonal — armed without the router, or a fire while watched.

#### What this means for the ruling

HANDOFF §D′ item 1 asks the owner to rule on a default-ON arm that has no ruling.
The census strengthens the *specificity* case (§1z-e.2's zero-fires-elsewhere
replicates, and §1z-n's rates hold on the armed slice). It does **not** provide a
prospective firing record, and it cannot separate the repair from `--router`.
**Two cheap runs would fix that**: one armed session with `--no-router`, which
fills the empty cell, and one press against §1z-n's named geometry, which is the
only way the heal gets tried. Both are desk-cheap to specify and neither has been
run.

⚠ **And the mesh axis is narrow too**: all 3 armed captures are `0x287B3`
(map 280), while the replay corpus is 71 captures on `0x1B97D`, 53 on `0x287B3`,
6 on `0x345CC`, 1 on `0xB602`. Nothing prospective has ever been recorded on the
mesh that carries the *plurality* of the corpus.

### 1z-o.11 R6/R6b's ECHO ROWS scored against the corpus — and "loudest" was a volume artifact

§1z-o.8 scored the three armed sessions on the INBOUND channel and noted R6b as
"the corpus's loudest echo session" with 30 rows against R7's 9. Scoring the
OUTBOUND channel properly changes that reading and supersedes a published claim.

#### The funnel — and it reconciles §1z-f.2 exactly

Every published echo number sits at a different stage of the same funnel, which
is why they have looked inconsistent:

| stage | R6 | R6b | R7 |
|---|---|---|---|
| sends on the tripwire's three opcodes | **349** | 797 | 176 |
| not the player's agent | 0 | 0 | 0 |
| non-finite point | 0 | 0 | 0 |
| point OFF-MESH — **the tripwire is silent by design** | **7** | 23 | 0 |
| ON-MESH — **the tripwire's real denominator** | **342** | 774 | 176 |
| TRIP (= logged rows) | **4** | **30** | **9** |

§1z-f.2 reports R6 as *"349 plane-bearing sends: 4 wrong-plane, 7
off-mesh-point, 338 legal"*. That is this funnel exactly — 338 legal + 4 wrong =
342 on-mesh — and the recomputation matches the live tripwire at **4 / 30 / 9**,
the control that has already caught two bad parses on this channel.

**The denominator for an echo RATE is the on-mesh row, not the 349.** The
tripwire cannot speak when `offered` is empty, so those sends are a genuinely
different class and counting them dilutes the rate — quote R6 as **4/342**, never
4/349.

Corpus-wide the same funnel reads **8,408 sends on the three opcodes → 424 not
the player's agent (the tripwire's own first gate) → 442 off-mesh → 7,543 on-mesh
→ 282 trips.** By opcode the trips are **281 × `0x0029`, 1 × `0x002A`, 0 ×
`0x002C`** — the lone `0x002A` in the whole corpus is a trip. So **the tripwire is structurally blind to 442 of the player's
7,984 grants — 5.5%** — and that number belongs beside its 3.73% rate every time,
because a tripwire that cannot speak about off-mesh sends is silent exactly where
our decode is weakest.

#### ★ R6b is loud by VOLUME, not by rate

| | trips | on-mesh sends | rate | rank by count |
|---|---|---|---|---|
| R6 | 4 | 342 | **1.17%** | 18 of 31 |
| R6b | 30 | 774 | **3.88%** | **2 of 31** |
| R7 | 9 | 176 | **5.11%** | 12 of 31 |
| corpus | 282 | 7,543 | **3.74%** | — |

**R6b's rate is the corpus rate.** It ranks second of 31 by echo
COUNT and is entirely ordinary by rate — it granted 774 times, more than any
other armed session, because it was long and routed. R7, the quiet one by count,
has the *highest* rate of the three. **§1z-o.8's "loudest echo session" is
withdrawn as a signal: it is a volume artifact.** Rank sessions by rate or say
"most rows" and mean it.

#### What the rows actually are

**All 43 logged echoes in the entire corpus emit plane 0** — 41 where the mesh
offers only `[37]`, 2 where it offers only `[42]`. The live echo record is one
sentence: *we put plane 0 on the wire at a point our mesh calls a deck.*

By sender, from each echo's co-timed send label:

| | `ROUTER one leg` | `ROUTER leg` | `ZERO LEAD` |
|---|---|---|---|
| R6 | 4 | — | — |
| R6b | 29 | 1 | — |
| R7 | 4 | — | 5 |

**38 of 43 are router paths and 5 are zero-lead** — so the design licence usually
cited for the echo channel (`test_position_trust` pinning verbatim echo at the
zero-lead site) covers **5 of 43**, and §1z-o.1's correction generalises: the
router is the dominant echo sender, not the zero-lead arm.

**★ AND §1z-f.2's FIELD-4 RULE EXTENDS, with exactly one exception.** That
section observed of R6's four that *"the server's own tracked plane (the send's
second word) was the client's latest accepted report's plane every time — no
stale state"*. Replaying the report stream against every trip: **R6 4/4, R6b
30/30, R7 8/9.** The single miss is R7's last echo, `t = 284.95`, whose label
reads `ZERO LEAD (-2067,6516) plane 0 carry 37` — field 4 is supplied by the
arrival **carry**, not by the tracked report plane, which is the documented
behaviour of that arm rather than stale state. So across 43 trips the server's
field 4 was **never** stale: the one deviation is a different mechanism writing
it on purpose.

#### ★ The exposure control — same deck, three very different rates

Bucketing every corpus send by the plane-set our mesh offers at the send point:

| offered `[37]` | sends | tripping | rate |
|---|---|---|---|
| R6 | 88 | 4 | **4.5%** |
| R6b | 51 | 28 | **54.9%** |
| R7 | 35 | 9 | **25.7%** |
| `20260829T085952` | 3 | 0 | 0% |

Three identically-configured sessions sending into the same decoded geometry trip
at 4.5%, 54.9% and 25.7% — R6 against R6b is **4/88 versus 28/51, Fisher exact
p = 1.6e-11**. **Deck geometry alone does not determine the echo rate** — and unlike the inbound case (§1z-o.8), no on-deck/under-deck distinction
rescues a geometric reading here, because these are points WE chose to send to.
What differs is which points each session's clicks and routes selected.

And the complement is as sharp: **on plane-`[0]` ground R6 sent 248 times and R6b
552, tripping ZERO** — while 97 other captures sent 5,981 times there and tripped
**140**. The armed sessions' echoes are exclusively a deck phenomenon; the
corpus's `[0]`-ground trips are the opposite direction (a non-zero plane emitted
onto plane-0 ground) and belong to different sessions entirely.

#### A published claim that no longer holds

§1z-f.2 calls R6 *"4/349 — the first nonzero census outside a lock session"*.
Scored corpus-wide, **31 captures carry at least one recomputed trip and 28 of
them are not lock sessions.**

> ⚠ **THAT COUNT READ 30 UNTIL A DENOMINATOR AUDIT, and the miss is instructive.**
> When `label_captures`' send-only bug was fixed, the rate it broke was corrected
> from 281/7,542 to 282/7,543 — but the CAPTURE COUNT drawn from the same
> population was not, and the rank denominators in the table above kept saying
> "of 30". **A population fix propagates to every figure drawn from that
> population.** `test_planecensus.py` §6 now pins the identities and the ten
> headline figures so the next such drift goes red instead of into a sentence. R6 was the first one *looked at*, not the first
there is. The claim should read "the first non-lock session to be censused",
which is a statement about the arc's attention rather than the corpus.

⚠ **What the echo channel still cannot tell you.** It is observation-only and
scoped to sends, so it says nothing about whether a bad emission was ADOPTED by
the client — R6b emitted 30 and its client never once declared an impossible
plane (§1z-o.8), which is the cleanest available demonstration that emitting one
is not sufficient to cause one. With n = 3 armed sessions there is no usable
correlation between echo count and disagreement count, and none should be
computed.

### 1z-o.12 THE CENSUS AGAINST THE MOVEHOOK CORPUS — and the LOCK inverts the channels

The census (§1z-n) scores what the client REPORTS. The movehook corpus records
what the client BELIEVES, from inside. Every session has both, so the same
question can be asked twice.

#### The in-band pin TRANSFERS — 19 of 19, and a hand-pin retires

A movehook bin does not record its map, which is why `noclipscore.py` hand-pins
map 280 and says in capitals that the coverage-score selector picks the wrong one
(§1v.3). It does not have to: **pair each bin to its gamesrv capture by
byte-exact float dwords and the census's in-band pin comes with it.** All **19**
pin (20 `movehook.bin` files exist; `vault/research/movecode/movehook.bin` is a
byte-identical copy of `k1-treatment`'s). Meshes: **17 x `0x287B3`, 2 x
`0x1B97D`**.

⚠ **THE RAW MATCH COUNT IS THE WRONG DISCRIMINATOR, and a first pass using it
refused four captures.** Two coordinates are shared corpus-wide: map 148's spawn
`(9826, 8077)` appears in **111** captures and map 280's `(-6036, -2519)` in
**40** — the latter because it is what most map-280 reports carry in `ours`.
Those two generate nearly every runner-up, so a raw-count margin measures shared
spawns. **Score CORPUS-UNIQUE matches instead** — coordinates appearing in
exactly one of 1,212 captures — and every pairing becomes decisive: 8 to 1,248
uniques against a runner-up of 1. `r5stuck` goes from 1 raw match (refused) to
**50 uniques against a runner-up of 0**.

**The method reproduces every pairing the record made by hand** — §1z-e.3's
`ascalon` -> `20260827T055221`, §1z-e.4's `k1-treatment` -> `20260827T212317`,
§1z-c's `r5stuck` -> `20260829T091543` — as its top match.

#### ⚠ A raw client-side rate is 2x too high: the SITE trap

The first pass read **6.31%** client-side. Splitting by the site each sample came
from shows why that is not the client's opinion:

| site | on-mesh samples | disagree | rate |
|---|---|---|---|
| `setter` | 9,689 | 274 | **2.83%** |
| `teleport` | 1,151 | 169 | 14.68% |
| `reseed` | 264 | 129 | **48.86%** |
| `setposition` | 88 | 74 | **84.09%** |
| `bake` | 52 | 0 | 0.00% |

`reseed`, `setposition` and `teleport` are the **correction machinery firing** — a
sample there is the instant of a snap, not a belief held during play.
`noclipscore.body_samples`' site list is right for *where is the body* and wrong
for *what plane does the client think it is on*. Everything below is the walking
channel only, and any client-side plane rate must say which filter produced it.

#### ★ THE RESULT: the lock inverts the two channels

| | client walking channel | server reports |
|---|---|---|
| **16 non-lock sessions** | 274 / 9,361 = **2.93%** | 13 / 1,303 = **1.00%** |
| **the 3 lock sessions** | 49 / 655 = **7.48%** | 131 / 286 = **45.80%** |
| all 19 | 323 / 10,016 = 3.22% | 144 / 1,589 = 9.06% |

**Away from a lock the client's own state is ~3x more anomalous than its
reports. Inside a lock the server's reports are ~6x more anomalous than the
walking channel.** The two channels are sensitive to opposite failure modes:

* **The CARRY is client-internal and report-silent.** r6 reads **16.29%**
  client-side against **0.00%** on the wire; r6b 3.92% against 0.00%; k2-2 12.50%
  against 0.00%. Already decoded for R6 in §1z-f.3 ("18 impossible-plane episodes
  totalling 60.7 s... the stale plane lives entirely client-side, in the
  walking/bake channel") and §1z-f.4's report-silent under-deck movement. New here
  only in that it holds across sessions.
* **The LOCK is report-loud and walking-silent.** `r5stuck` reads **100.00%**
  client-side on **17** surviving walking samples against **81.97%** over **122**
  reports — the walking channel has almost stopped producing samples at all,
  which is what "the walker is dead" looks like from inside. `ascalon` is 0.83%
  against 13.67%; `k1-treatment` 18.18% against 48.00%.

**131 of this subset's 144 server-side disagreements — 91% — come from the three
lock sessions.** That is where server-side plane disagreement lives.

⚠ **AND THIS SUBSET IS NOT THE CORPUS.** It contains all three of the corpus's
locks, so its server-side rate (9.06%) is four times the census's 2.34%. The
channel comparison is valid within the subset; the subset is enriched. Quote the
non-lock row against the census, not the total.

#### Two corroborations

**Off-mesh matches on both channels** — 6.51% client-side against 6.31%
server-side — which is expected: off-mesh is a statement about our decode's
coverage, not about anything the client declares. It is the control that says the
two populations are looking at the same geometry.

**The direction split is stable across instruments.** Client side: **598
"declares N, mesh offers only 0" against 124 "declares 0, mesh offers only N"** =
83 / 17. Server side (§1z-n): **208 / 51** = 80 / 20. Two independent
instruments, two populations, the same ratio.

⚠ **What this cannot settle.** The client-side "sample" is a choice — 6.31%
unfiltered, 3.22% on the walking channel — so the filter travels with the number
or the number is meaningless. `r5stuck`'s 100% rests on **17 samples**, which is
the right order for a dead walker and far too few for a rate. And nothing here
says which channel is *right* when they disagree: both are scored against OUR
mesh, so a decode gap moves both together.

### 1z-o.13 THE LADDER SCORED AGAINST THE CENSUS — and it is measuring seam contact

The `plane_repair_due` ladder is the repair's own view of the plane channel; the
census is the exhaustive view of the same channel. Per-session breakdowns are
published already (§1z-f, §1z-g, §1z-o.1). This is the ladder measured AGAINST
the census, and it does not come out well.

**Control first.** Replaying `plane_repair_track` per report reproduces the live
ladder exactly — **15 / 11 / 9** rows, and not only the counts: the ordered `why`
string, the `plane` and the 2-dp coordinate match on all 35.

#### The compression — on ONE denominator

⚠ **A first draft of this section committed the arc's own denominator swap.** It
priced compression off 549 `position_report`s while pricing the hidden count off
the 474 the trigger actually evaluates (549 − 75 `0x0047` stop-reports, which
`_maybe_plane_repair` never sees). 549 − 35 = 514, not 439. Stated on one
denominator:

| | |
|---|---|
| reports the trigger EVALUATES (0x003D) | **474** |
| ladder rows | **35** |
| **compression** | **13.5 evaluations per row** |
| evaluations computed but not logged | **439** |

Per-report clause outcomes: `plane-legal` 404, `off-mesh` 61, `holding` 5,
`arming` 4 (+75 stop-reports never evaluated).

**The ladder cannot express a rate.** 439 of 474 evaluations left no trace,
because the reason string did not change. That is the design — a capture that
cannot show the arming edge cannot answer "why didn't it fire" — but it means
**no denominator is recoverable from the ladder**, and every rate in §1z-n had to
come from the report stream. It is also how §1z-o.1's hidden `arming` row
vanishes.

#### What the 35 rows are — and pick your denominator

| ladder `why` | rows | evaluations compressed | census category |
|---|---|---|---|
| `plane-legal` | 17 | 404 | AGREE |
| `off-mesh` | 13 | 61 | OFF-MESH |
| `arming` + `holding` | **5** | **9** | **DISAGREE** |

The mapping holds by construction — the ladder's `offered` and the census's are
the same `containing()` call on the same in-band-pinned mesh.

**"5 of 35" is 14.3% of ROWS but 9 of 474 is 1.9% of EVALUATIONS**, and the row
denominator is the one that flatters the ladder. Say which.

#### ★ THE OFF-MESH CHANNEL IS MEASURING FLOAT SEAM CONTACT

All **13** `off-mesh` ladder rows sit within **0.0056 u** of walkable ground —
depths `0.0 ×6, 0.0009 ×3, 0.0019, 0.0033, 0.0045, 0.0056`. They are floats
landing on a trapezoid edge. Meanwhile the armed set's 63 off-mesh reports split
**30 seam touches (< 0.01 u) and 33 genuinely off-mesh (>= 10 u)** — and **the
ladder spent all 13 rows on the seam half and none on the other.**

The mechanism is the transition gate. R6b holds the armed corpus's one real
excursion — **32 accepted reports parked at one point 20.1 u off-mesh over
11 s** — and it produced **no ladder row at all**, because `why` was already
`"off-mesh"`, set 16 reports earlier by a 0.0001 u seam touch somewhere else.
**A transition log keyed on a reason string cannot distinguish a 0.0001 u edge
kiss from an 11-second parked excursion**, and here it reported the first and
hid the second.

#### ★ AND THE LADDER CANNOT SCORE ITSELF

`plane_repair_due` rounds `reported` to **2 decimal places**. Scoring each row
against its OWN logged coordinates rather than joining back to the
full-precision `position_report` moves **9 of 35 rows** across census categories
(`plane-legal` -> `off-mesh` 3, `off-mesh` -> AGREE 6). The 17 / 13 / 5 split
above is only correct **because it joins to the report stream**. Anyone
re-deriving it from the ladder alone gets a different answer — which is the same
lesson as §1z-o.1's 1.02 s, from a second direction.

#### Coverage, and a vacuous zero named as one

Replaying the trigger over all 134 non-stub captures as if armed throughout gives
**657 rows**: `plane-legal` 355, `off-mesh` 199, `report-refused` 46, `arming`
34, `holding` 11, **`plane-lock` 5**, `stale-stream` 4, `rate-limited` 3 — **54
disagreement rows from 15 of 134 captures**. The shipped ladder's 35 rows are
**5.3%** of that, and its 5 disagreement rows **9.3%**.

The 5 counterfactual `plane-lock` transitions match the 5 known would-fires 1:1
(1 / 1 / 3 across the sessions §1z-e.2 named), so the ladder can count fires.

⚠ **But `plane-lock` is ZERO in every armed capture, and 9 of the trigger's 13
clause strings never fire there — three of them UNREACHABLE, not merely
unobserved**: `not-moving` cannot occur (movementType is never 0 across 474
decodes), `report-refused` cannot occur (549/549 reports accepted), `off` cannot
occur (`PLANE_REPAIR` is True). **The shipped ladder is a 35-row log of a trigger
that never fired**, and most of its vocabulary has no live witness.

⚠ **A DEFECT IN THIS SECTION'S OWN REPLAY, caught before publication.** A first
pass omitted the `rate-limited` clause, so every post-`HOLD` report read
`plane-lock` and a burst of fires collapsed into ONE transition — 4 for 5, and an
invented claim that the ladder cannot count its fires. Modelling `MIN_INTERVAL`
gives 5 and 5. Clause order is `holding` -> `rate-limited` -> `plane-lock`.

### 1z-o.14 What R7 does NOT settle

* **The HEAL is still untried.** Zero fires means the `0x002C` restamp has never
  been tested on a live locked client. R7 came closest and stopped at 20%.
* **Whether the echo prolonged the lock.** The server echoed plane 0 back nine
  times while the client was stuck. Recovery was OURS, not the client's (§1z-o.6),
  so the question is no longer "did the echo delay an unaided recovery" but "did our
  own traffic cause the episode AND end it". A `--no-router` run would separate them.
* **n = 1 for the intermittent morphology.** Everything in §1z-o.3 rests on one
  episode in one session.
* **What happened after the third arming is UNKNOWN.** The last `position_report`
  of any kind is the arming itself at t=284.952902, and the capture then runs to
  t=905.671 — **620.7 s with no position reports** while the connection stays up.
  That is the shape §1z-e.3's lock #2 ends in (reports stop, session sits silent),
  but R7's operator also stopped the hook by request at about the same moment, so
  **the silence is equally consistent with the session simply being over.** The
  capture cannot separate them. Do not read it as a third lock, and do not read it
  as clean.
* ~~The clock join was not needed and was not done.~~ **It has since been done,
  and it is better than the coordinate join.** `tick` is `GetTickCount()` (grep
  `r->tick = GetTickCount()` in `movehook.c`) — wall clock at a 15–16 ms quantum,
  NOT the ~50 ms world clock 1.3% slow, which is `ptime`/`stop`. So alignment is a
  constant offset, not a rate fit. Three independent anchors: 204 `MOVE_TO_COORD`
  packets paired ordinally to the 204 click-to-move queries (**0 coordinate
  mismatches in 204**), 117 of 122 `position_report` coordinates matched on exact
  float32 identity, and 176 of 176 outbound grant destinations. **Adopted:
  `t_server = tick_ms/1000 − 762353.145`, ±10 ms.** The anchors disagree by about
  11 ms, which is the round trip and not error — the capture's own `ping_summary`
  reads `last_ms: 11`. ⚠ **Anchor A is a lower bound** (it excludes the c2s leg)
  and anchor C is method-dependent — an independent re-derivation got sd 0.34
  against 0.012 — so quote A and B, not C. ⚠ **The band is wider than the
  `GetTickCount` quantum (15–16 ms), so NO claim about which of two events within
  ~16 ms happened first is supported by this alignment.** §1z-o.4's in-window
  sequence is safe because its steps are hundreds of ms apart; a tighter ordering
  claim would not be.

---

## 2. Corrections to the record

Each of these was in circulation and each is now measured against the bytes.

### 2.1 `PLAN.md` §2.1's setter row conflates two different `push 0`s

The row reads: *"the shared setter `0x00602A40` … passes `isWaypoint=0`, which
CLEARS `m_flags` bit 18"*. The **conclusion is right** and the **mechanism is
wrong**, in a way that matters because it points at the wrong instruction:

- The setter's own unconditional AND, `0x00602A65 and dword [ebx+0x20], 0xfff7ffff`,
  clears **bit 19**, not bit 18. `~0xFFF7FFFF == 0x00080000`. Bit 18's clear-mask
  would be `0xFFFBFFFF`.
- The `push 0` inside the `0x0029` **handler** (`0x005FD906`) is not `isWaypoint` at
  all. It is the setter's arg2 and lands in **`agent+0x98`**
  (`0x00602AA5 mov eax, [ebp+0xc]` / `0x00602AA8 mov [ebx+0x98], eax`).
- The real `isWaypoint` is **arg2 of the bake**, hardcoded one frame further out at
  `0x00602A7F`.

This is [[a-forwarder-names-the-messenger]] from the other direction: the constant
was attributed to the frame that *passes* it rather than the frame that *means* it.

### 2.2 `agent+0x98` has readers — MOVECODE-Q3's premise is REFUTED

`PLAN.md` §3's Q3 row says of `+0x98`: *"no reader was ever traced."* There are
**11 instructions touching `+0x98` in AgAgent alone — 4 stores and 7 reads**,
including a compare and two `push dword [reg+0x98]` sites passing it as a scalar
argument (OBSERVED, `--field 0x98 --in AgAgent`). The write side is also now
resolved: **`+0x98` is the shared setter's arg2**, which `0x0029` hardcodes to `0`
and `0x002A` fills from the wire dword `[edi+0x18]` — *that single field is the
entire difference between the two opcodes.* What `+0x98` **means** is still open;
that part of Q3 stands.

### 2.3 `asserts.py --grep` can return a confident zero for a string that is present

Two lanes disagreed on whether `AgAgent:1143` exists. **It does**, and the
disagreement is worth recording because the tool was not at fault:

- `asserts.py --grep "segmentPoint"` → **0 sites**, and `AgAgent:1143` is absent
  from `--file AgAgent`.
- The site is real: `0x00600245 push 0x477` (= 1143), file string
  `P:\Code\Engine\Agent\AgAgent.cpp`, expression string at `0xa5346c` =
  **`m_segmentPoint.position != AGENT_INVALID_POSITION`**, assert call at
  `0x00600256`.
- It is unreadable to `asserts.py` because the compiler scheduled an
  `fstp st(0)` (`0x00600254`) into the fixed byte pattern — **exactly** the failure
  the tool warns about in its own banner ("SHORT BY 370 MORE … e.g. an `fstp` at
  `0x006029BC`, which is AgAgent:2366").

So **`movetap.py:464`'s citation `m_segmentPoint (assert AgAgent:1143)` is CORRECT
and now verifiable**, and the lane that reported it missing had labelled its own
answer `NOT FOUND` *by method* rather than proven absent — which is the label doing
its job. The lesson is the standing one: [[feedback-negative-needs-positive-control]]
— a filtered search that cannot find a string you already know is not evidence of
absence. When an assert matters, read the expression pointer at the call site.

---

## 3. Pre-registered predictions

Registered **before** the runs that test them, per the standard that got the router
arc four honest results.

### MOVECODE-P1 — for B2 (the `0x0060029F` teleport ledger)

**Prediction.** With a hook on the branch at `0x0060029F` during a normal walk on
our own server, the branch will be taken **both ways within a single granted
leg**: bit 18 SET on the intermediate re-bakes the client's own solver produces, and
CLEAR on the final arrival. Specifically:

- **P1a.** Some `0x0029` grants will be followed, before the arrival tick, by at
  least one bake with `isWaypoint=1` originating from `0x00600B0A` or `0x00601936`
  — i.e. the client re-plans our grant.
- **P1b.** Every teleport (`0x006020B0`) will be preceded by a bit-18 CLEAR, and
  the distance moved by that teleport will be **small** whenever the client's own
  last leg agreed with our copy, and **large** exactly when it did not.

**What refutes it.** If bit 18 is observed CLEAR for the entire lifetime of every
granted leg — no `isWaypoint=1` re-bake ever fires on a server-granted destination —
then §1.6's reframing is wrong, the client does *not* re-plan our grants, and
`PLAN.md` §2.1's original reading stands unmodified. That is a real possible
outcome: §1.6 establishes that the setter *calls* both re-bakers, not that either
*reaches* its `isWaypoint=1` site under the setter's arguments.

**Status: UNVERIFIED — the reachability of `0x00600B0A` and `0x00601936` under the
setter's own arguments is not established.** This is the one load-bearing gap B1
leaves; see §4.

### MOVECODE-P2 — for B3 (the navmesh differential)

**Prediction.** Hooking `MapFindPath` (`0x00709E90`) will show the client's own
solver — `0x006011F0`, the `PriQ.h` path solve — producing **multi-leg routes with
`isWaypoint=1` intermediate points on the same grants where our
`pathmap.route()` produces a different leg sequence**, and run 5's "pocket" will
**not** reproduce: the client will resolve the player's open ground as walkable
where our decode reads it as enclosed.

**What refutes it.** The client refusing the same region our mesh refuses — which
would make run 5's tour-shaped routes a route-*quality* problem (ROUTER-Q10) rather
than a decode bug, and would move the arc's weight back onto route selection.

---

## 4. What B1 leaves open, stated as gaps rather than left silent

1. **The load-bearing one, now narrowed to a runtime question.** Both
   `isWaypoint=1` sites are reachable and their guards are read: an ordinary float
   inequality on the point the function just computed (§1.6). What is **not**
   established is the *rate* — how often obstacle avoidance or the path solver
   actually displaces the point on a server-granted destination, and therefore how
   often a grant of ours ends its life gliding rather than snapping. Nothing static
   can answer that; MOVECODE-P1 pre-registers it and B2's hook on `0x0060029F`
   measures it. Until then, §1.6's *mechanism* is OBSERVED and its *significance* is
   a RECONSTRUCTION.
2. **`--xrefs` sees direct rel32 branches and stored data words only, and
   MOVECODE-Q4 is no longer a worry but a demonstrated property.** Every caller
   count here inherits that limit. **The movement tick `0x00600140` is a C++
   virtual method** — OBSERVED: `0x00A52F64` is *slot 1* of a two-entry vftable at
   `0x00A52F60`, whose slot 0 is a textbook MSVC scalar deleting destructor
   (`0x005FE920`, `push 0x134` = the class size), and whose address the constructor
   stores at object offset 0 (`0x005FDE8E mov dword [ebx], 0xa52f60`). Both words
   are in the relocation table, which is the refutable test that they are pointers
   rather than string bytes that look like one; everything around them is
   unrelocated string data, which bounds the table at exactly two entries. The tick
   is `ret 8` — `this` in `ecx` plus two stack args — and is reached only by
   `call dword [reg+4]` after a vptr load.

   So `--xrefs 0x00600140` returns **0 direct callers for a function that runs
   several times a second**, and that zero is the same zero a genuinely dead
   function produces. The discriminator is cheap and should be the rule:
   **a 0-direct-caller function whose only reference is a relocated `.rdata` word is
   a virtual, and its true caller list is unknown.** Which call site dispatches it is
   NOT DETERMINED — there are 112 `call dword [reg+4]` sites in `.text` and none in
   the movement region; `AgTimer::Advance` (`0x00603FE0`) is the obvious candidate
   and is **ruled out**, because it dispatches slot 1 with no pushed args
   (`0x006040E7 call dword [eax+4]`, no `add esp`) while the tick is `ret 8`. A
   breakpoint reading the return address settles it in one run; static analysis
   will not. That is a B2 site.

   > **CLOSED 2026-08-28 by MOVECODE-R4-A (§1v.2), and the exclusion above is
   > REFUTED.** The tick was hooked and **both captured records return to
   > `0x006040EA`** — which is `0x006040E7 + 3`, since `ff 50 04
   > call dword ptr [eax + 4]` is three bytes. **`AgTimer::Advance` IS the
   > dispatcher.** The `ret 8` / no-`add esp` argument that ruled it out does not
   > survive contact. The rest of this item is vindicated: only a breakpoint could
   > have settled it. The same run also refutes "runs several times a second" — it
   > fires **0.62/s**, and is an **arrival timer callback**, not a per-frame
   > update, which is why its arrival test can be an exact equality.

3. **`func_start` returns `None` when MSVC does not pad, and a lane read that
   backwards.** Two lanes disagreed on which function contains the `isWaypoint=1`
   bake at `0x00600B0A`. Resolved from the bytes, and the answer is `0x00600840`:
   it carries a full prologue (`push ebp / mov ebp, esp / sub esp, 0x64 / push ebx /
   push esi / push edi`) sitting **immediately** after the previous function's
   `mov esp, ebp / pop ebp / ret 0x10` with **zero `int3` bytes between them**, and
   its epilogue is `0x00600B5B ret 8` — which matches the setter's two-argument
   thiscall at `0x00602AEB` exactly. The tick's own first `ret` is at `0x006004FF`,
   far short of it. `func_start(0x00600B0A)` answers `None` purely because of that
   missing padding (`0x006011F0`, by contrast, has a clean `cc cc cc…` run before
   it), and the lane that took `None` as "then it belongs to the previous function"
   inverted the tool's own "best effort, not proof of a function boundary" warning.
   **A `None` from `func_start` is an absence of evidence about the boundary, not
   evidence that there is none.**
4. **`asserts.py` is short by ~373 sites**, so every `--in <module>` bound —
   including AgAgent's `0x005FE0C3..0x00602CE2` — is approximate, and every "no
   assert names X" is a floor. §2.3 is a worked example of that floor hiding the
   answer.
5. **`+0x98`'s meaning** (Q3) is still unknown; only its writers and the existence
   of its readers are settled.
6. **Bit 18 has no ArenaNet name.** `isWaypoint` is our reconstruction from
   behaviour. It is a good name and it should be used, but it should not be quoted
   as the client's own.

---

## 1z-q. The history chain, decoded whole — and why a SERVER-SIDE MIRROR is the derived fix

> **Numbering note: this is `1z-q`, skipping `1z-p`.** `1z-p` is reserved as
> `RUN-R8.md`'s staleness test (`grep -n '^## 1z-p'`); creating it here would
> falsely signal R8 ran. R8 is still not run.

**Why this section exists.** The warp is not fixable by choosing a better grant
POINT — five candidates that each chose a point are dead (§2 scoreboard), and a
head-to-head over the banner-labelled corpus (two-arm hard bar, active-time
denominator, 2026-08-30) reads **router-ON 1.60/min vs router-OFF 2.44/min**:
the router halves the warps and kills the no-clip, it does not stop the warps,
and **no configuration this repo ships stops them.** The decoded mechanism says
why (§1): the snap fires when the SYNC (authoritative) copy fails the client's
own reprieve test — *is my current dead-reckoned position within 100 u of a
segment of my recent HISTORY?* — and then the fallback gates snap. That history
chain is the lever nobody has modelled. This section decodes it completely so
the server can model it.

**Method.** Four static lanes on the pinned pristine 38797 image
(`capstone`/`pefile`, read-only, carve-out (1)) plus an adversarial verify lane
that re-disassembled every load-bearing site itself. Built on — not re-derived
from — the 2026-08-20 match-test decode (`studies/movement/FINDINGS.md` "THE
AgTrack MATCH TEST IS DECODED") and HANDOFF §1/§4. **Zero offset disagreements
across the four lanes**; the verify lane caught one real error (below) and one
over-asserted cadence label. Every claim here is OBSERVED at an address unless
tagged otherwise.

### 1z-q.1 The structure — ArenaNet's own `history` of `historyPoint`s

Module `P:\Code\Engine\Agent\AgTrack.cpp`. Their nouns, from single-citation
asserts (measurement, not a dump): `history`, `historyState`, `historyPoint`,
`returnedSegment` (AgTrack:447), `clientControlled` (457),
`source.GetWorld() == WORLD_SYNC` (458). It is a singly-linked, push-front list
— newest at the head — one per agent.

**Node, 0x2C bytes** (each field's store address in the create path 0x00605A2F):

| off | field | store |
|---|---|---|
| +0x00 | time (`now`) | 0x00604DCC (allocator) |
| +0x04 | next (older) | 0x00605A5D; head = state+0x04, set 0x00605A93 |
| +0x08..+0x14 | position x, y, plane, w4 | 0x00605A63/69/6F/75 |
| +0x18/+0x1C | velocity x/y (= agent+0xB0/0xB4) | 0x00605A81/87 |
| +0x20/+0x24 | speed factors (= agent+0x5C/0x60) | 0x00605A7B/8D |
| +0x28 | facing (= agent+0xC4) | 0x00605A90 |

**State record, 0x1C bytes**: +0x00 clientControlled, +0x04 history head
(newest), +0x08..+0x14 position seed, +0x18 time. Array base [mgr+0x20], count
[mgr+0x28], stride 0x1C; manager = agentMgr+0x1CC, from which [ctx-0xE4] = the
SYNC array (agentMgr+0xE8) and [ctx-0x80] = the ASYNC array (agentMgr+0x14C).

### 1z-q.2 What a node's position IS — and why one grant cannot forge a match

**node.position = 0x005FF820(agent, now)** — OBSERVED, and sharper than the
prior gloss. That resolver returns the **commanded destination** agent+0x88..+0x94
when the agent has ARRIVED (0x005FF839, gated on the arrival tick agent+0x48),
**else the +0x78 leg-start position DEAD-RECKONED to `now`** via 0x005FFB40
(0x005FF868). The sampled agent is the **SYNC copy** (bulk sampler pushes
[ctx-0xE4][id], 0x00604B05). So the chain is a trail of where the
server-authoritative agent has been, sampled on the client's own world clock
(agent+0x24 selects the per-world clock at [ctx + world*0x64 - 0x84]).

The match test's tested point **q = sync+0x78, dead-reckoned to `now` at the
caller** (0x00605643 reads it once; the bake 0x005FE9EA->0x005FF880 does the
dead-reckon; 0x006055E0 contains no such call). **No single grant writes +0x78**
— 0x0029 writes +0x88..+0x94/+0x80, n=0 to +0x78 — which is the whole content
of HANDOFF §4 item 1's "no grant we can send makes this match by construction",
now confirmed from writer, reader and layout at once. ⚠ **But that is a fact
about ONE message, not about a grant SEQUENCE.** +0x78 evolves continuously by
`+0x78 + vel*dt`, and our grants set `vel` and the destination the bake
integrates toward. A sequence of grants therefore steers +0x78, the chain, and
every future q. **The lever is the grant TRAJECTORY, not any one point** — which
is exactly why every point-choosing candidate died.

### 1z-q.3 Lifecycle — writers, the two timers, eviction, and the resets that matter

**One writer** (recorder 0x00605840, 3 direct callers), **one allocator**
(0x00604BB0, sole caller the recorder). A node is pushed only on a **7-field
command change** — position x/y/plane vs the state seed, velocity/speed*2/facing
vs the head node (0x00605945..0x006059B4) — OR the **forced 2.5 s re-sample**
(0x0060593A `cmp eax,0x9c4`, eax = now - head.time). An identical command within
2.5 s pushes **nothing** (fall-through 0x006059BA). A second, independent timer
lives in the per-tick update loop: **3.333 s keep-alive** (0x00604AAE
`cmp eax,0xd05`) that calls the recorder when the head is stale. RECONSTRUCTION:
so a moving or parked agent drops a breadcrumb every ~2.5-3.3 s (~720 u at
288 u/s) — the chain is **coarse**, a single click yields a one-segment chain.

**Eviction is monotone pruning by the READERS, plus wholesale clears.** Neither
the recorder nor the allocator ever trims by count or age; storage is
slab-recycled (256 nodes/slab, reclaim at >5000 ms) independently of chain
length. The visible chain shortens only when a reader truncates it — see §1z-q.4.

⚠ **CORRECTION — a draft of this decode said snaps and 0x002C leave the chain
intact. They do NOT** (verify lane C1, byte-proven). **AgTrack::Clear
(0x00605F70) zeroes state+0x00 AND state+0x04** (0x00605FA7/0x00605FAE), and it
is called on: the **0x002C** handler (0x005FDA78), **every match-test MISS**
(dispatch 0x0060602E, plus the roster reseed loop clears each async agent), and
**player-input re-arm** (0x00605F10). The teleport/reseed PRIMITIVES
(0x006020B0/0x006022B0) really do leave state+0x04 alone — but the HANDLERS that
call them clear first. **Consequence for the mirror: a snap and a 0x002C both
RESET the chain**, and the mirror must model that reset (it is an event the
server already knows it caused). Genuine agent-lifecycle clears
(despawn 0x00605DA0, world teardown 0x00604700/0x00605E40) are the only OTHER
resets, and the server already tracks both.

### 1z-q.4 The walk — newest->oldest, no break, OLDEST match wins, then truncate

The reprieve test 0x006055E0 (sole caller the dispatch 0x0060601C) walks the
chain **newest->oldest** (0x00605732), tests each **segment** = (node[i].position
-> node[i-1].position) against q with the decoded 100 u dual test, and **does not
break on a match** — it records `lastMatch` and keeps going, so the **oldest**
matching node wins (0x00605718). On any match it sets `lastMatch.next = NULL`
(0x00605746), **dropping the older tail**. A second reader — the by-time render
query 0x00604ED0 inside the update loop — prunes identically
(`returnedSegment.next = NULL`, 0x006055C2). **Both readers only prune
monotonically toward the newest matched node; neither edits node contents nor
grows the chain.** NOT FOUND (by disasm): any path-replanner reading the chain,
and any chain read by the 0x0047 stop handler (its handler 0x0091DB00 never
touches AgTrack). The chain is **fully encapsulated in AgTrack.cpp**.

### 1z-q.5 ★ THE STRATEGIC RESULT — a server-side AgTrack mirror is feasible, and it is the fix

Everything the chain's contents depend on is **server-known and decoded**:
the grant bake equations (§1), the dead-reckon formula, the 7-field push rule,
the 2.5 s / 3.3 s timers, the seed-vertex selection, and the reset events
(snap, 0x002C, re-arm, despawn, teardown). No external module contributes; the
two readers' only side effect is a prune the server can compute. **Therefore the
server can maintain a byte-faithful mirror of the player's sync-agent history
chain and evaluate the client's own reprieve test BEFORE emitting a grant** —
answering "will this grant keep the authoritative copy within 100 u of its own
trail, or trip the snap?" This is the first movement lever that is a **property
of a derived model, not a chosen point**, and it is what retail's denser grants
were implicitly satisfying.

⚠ **The residual uncertainty, stated plainly.** The mid-flight sample uses the
client's world clock (~1.36 % slow, Q-noted). A byte-exact mirror would need
that clock. But the test's tolerance is **100 u**, and 1.36 % clock error over a
2.5 s window at 288 u/s is **~10 u** — an order of magnitude inside the band. So
the mirror need only be ~100 u faithful, and the one thing it cannot reproduce
exactly is ~10x too small to matter. RECONSTRUCTION, and the replay below is how
it gets checked rather than asserted.

⚠ **The graveyard caution the mirror EXPLAINS.** "Grant 3x denser like retail"
is naively wrong — `--heading-grant` (12.8/min) and `--client-endpoint`
(14.6/min) were density increases that made warps WORSE, because each re-grant
baked a new velocity/destination that jumped +0x78's integration OFF its own
trail. Density that follows the continuous path preserves the tube; density that
jumps it breaks the tube. **Raw density cannot tell the two apart; the mirror's
reprieve-test check is exactly the discriminator that can.** That is the
retrodiction the fix must pass, and it passes it by construction.

### 1z-q.6 NEXT — desk-only, and it needs no client run

1. **Build the mirror** (`toolkit/authsrv/agtrack_mirror.py` or similar): the
   node/state structs above, the recorder push rule, both timers, the walk, and
   the reset events, driven by the grants the server already emits.
2. **Replay it against the capture corpus** — every gamesrv JSONL carries our
   grant stream and the client's reports. The mirror's predicted reprieve-test
   verdict (match / miss) must equal the client's actual snap/no-snap at each
   evaluation. **This is the validity check, and it is verbatim-first over data
   that already exists — no new runs, no owner time.** A mirror that reproduces
   the historical snaps is trusted; one that does not is wrong and says so.
3. **Only then** derive the grant-insertion policy that keeps the mirror's
   verdict at MATCH, and — per the arc's rule — one verbatim confirmation tap
   against a live chain (the movehook can read AgTrack directly), not a run
   campaign.

**What this section does NOT settle.** Whether the mirror actually reproduces
the corpus snaps (step 2, unrun); the sweep 0x00604880's exact cadence (verify
lane C3, unresolved — bounded impact, it textures the re-sample rate but not the
"nobody watches the desync" result); the meaning of `facing == 9`, a second
server-invisible no-snap path (NOT FOUND); and 0x005FF820's world-clock table
index (Q, bounds how non-reconstructible the mid-flight sample is — see the
100 u argument above).

---

## 1z-r. The mirror is built and replayed -- the SYNC SIM is confirmed by every warp in the corpus, and the chain's replay taught three things the decode alone could not

**What exists now** (commit `6dff112`, branch `claude/agtrack-mirror`):
`toolkit/authsrv/agtrack_mirror.py` -- §1z-q step 1, the server-side
transcription of the chain machinery, every rule carrying its citation and
every model choice labelled in place; `toolkit/authsrv/test_agtrack_mirror.py`
-- 64 synthetic checks pinning each transcribed rule, bare machine; and
`toolkit/clientscan/agtrack_replay.py` -- §1z-q step 2, which drives the
mirror through a gamesrv capture's own event stream (grants 0x0029/0x002A,
0x002C, 0x002B, the c2s command stream 0x003E/0x003D/0x0047, synthetic
100 ms ticks for arrivals and the keep-alive) and scores it against
movesync's two-arm hard bar. No client was launched; every number below is
this instrument over captures already on disk, and the instrument is in the
tree.

### 1z-r.1 ★ THE SYNC SIMULATION IS VALIDATED BY THE CLIENT'S OWN SNAPS

A real AgTrack snap reseeds the rendered copy FROM the sync copy
(§"THE SNAP IS A WHOLE-ROSTER RESEED", studies/movement/FINDINGS.md:3191),
so at every observed warp the post-step report must land ON the mirror's
simulated sync position -- a prediction the mirror had no access to when it
was written, since the sim is built from the bake equations alone.

**Measured (agtrack_replay over 177 scoreable captures, 2026-08-05..08-30):
251 hard-bar steps; 223 of them land within 150 u of the mirror's sync
position at that instant -- median 24 u, p90 173 u -- after starting
440..6,124 u away.** On the two 2026-08-30 shipped-default captures it is
10 of 10, 20.8..136.8 u. The bake, the settle, the dead-reckoner, the
arrival teleport and the speed stores, composed over whole sessions,
reproduce the client's authoritative copy to node-tolerance at every moment
that matters. §1z-q.5's "everything the chain depends on is server-known"
is CONFIRMED by retrodiction for the sync half.

**The 28 steps that do NOT land on sync are a finding, not noise**: a
hard-bar step that lands elsewhere (e.g. `20260827T212317`'s pair at
~1,800-1,940 u off) was never an AgTrack reseed -- a second displacement
mechanism, wire-invisible to the reseed model (candidates: the gate-free
local-input snap route 0x005FCAA0, HANDOFF §4's named loose end; carve
fall-throughs). The replay now measures this partition per step
(`to_sync`), which no earlier instrument could.

### 1z-r.2 The reprieve test, in the current regime: killing cell EMPTY

The falsification cell was defined in advance: an observed warp whose
window holds ONLY MATCH verdicts -- the mirror flatly contradicted (a MATCH
jumps clean over all three gates, so it is sufficient for no-snap). On the
two 2026-08-30 captures (shipped default + router):

| model | covered | gates-blind | contradicted | false alarms | match rate |
|---|---|---|---|---|---|
| freerun (no reader-2 prune) | 7/10 | 0 | 3 | 4 | 93.7% |
| prune 3000 ms | 10/10 | 0 | **0** | 33 | 80.4% |

The three freerun misses decompose exactly, and the decomposition is the
section's real payload:

- **Two matched on OLD TRAIL** (segments 10.7 s and 23.6 s old): the sync
  copy trails the player along the same route, so a long-lived chain always
  holds a segment near q -- but the real client snapped, proving its chain
  DID NOT hold those segments at those moments. Old trail is not
  protection.
- **One was a 0.6 u boundary case**: q-to-c measured 99.3 u against the
  99.919968 u effective single-leg threshold (§round 5) -- inside the
  replay's interpolation noise. Not a structural contradiction.

Control arm (feedback: run the known-bad arm): forcing the radius to 10 u
degrades false alarms 4 -> 45 (11x) and match rate to 70.6% -- the metric
can go red on a broken mirror, so its green means something.

### 1z-r.3 What the replay taught that the decode could not

1. **Reader 2 was the missing rule.** The first mirror omitted the by-time
   render query 0x00604ED0 (§1z-q.4 names it; its cadence is §1z-q's own
   flagged unknown). Its effect -- continuous monotone pruning -- is now a
   PARAMETER (`prune_ms`), and the corpus adjudicates: freerun leaves 62
   attributable contradicted steps corpus-wide, prune=3000 leaves 49, and
   prune <= 3000 empties the cell entirely in the current-config regime.
   The parameter's true semantics (query time, per-agent applicability)
   remain UNRESOLVED; the dial stands in for them honestly.
2. **Invisible resets are real dynamics, and freerun chain state is
   unknowable in principle.** A gate-2/gate-3 snap at small separation
   reseeds invisibly (no hard step), Clears the chain, and closes the
   fence; fence-closed grants then APPEND (round 5: "client only is
   REFUTED"); the next player input re-arms and wipes the head. Gate 3 is
   other-agents state the server cannot see, so no replay can track the
   real chain exactly across such an event. RECONSTRUCTION, but it is the
   only story consistent with all three freerun misses AND the
   fence-closed no-snap stretches at 1,500-6,300 u separation. This is why
   the mirror is deliberately CONSERVATIVE: over-predicting a snap costs a
   trajectory-following grant; under-predicting costs a warp.
3. **The corpus's older config eras expose unmodelled vocabulary.**
   Attributable contradicted steps cluster in 08-19..08-27 captures --
   the heading-grant/client-endpoint/pre-router eras, whose sessions carry
   opcodes the replay does not yet model (0x0025 direction arms, 0x0027
   re-issue, 0x0028 stops). Named residual, not hand-waved: the replay
   models the shipped vocabulary and says so.

### 1z-r.4 ★ THE POLICY TARGET, SHARPENED

§1z-q.5 said the lever is the grant trajectory. The replay sharpens it:
**the tube that protects the client is segment 0 plus at most ~3 s of
nodes -- the CURRENT leg. A grant policy must keep q (the sync copy's own
dead-reckoned position) within 100 u of the player's current command
segment, and must never lean on deeper history**, because invisible resets
delete it without notice. This retires, in advance, any policy shaped like
"the player walked here 30 s ago, so granting near that trail is safe" --
the two old-trail misses are the counterexamples, measured.

**NEXT (step 3, desk-first)**: derive the grant-insertion rule from the
mirror -- before emitting, evaluate; if MISS is predicted, emit a
trajectory-following grant (one that lands q inside the current-leg tube)
instead of the raw destination. The mirror's evaluate() is already the
pre-emit check §1z-q.5 asked for. One verbatim confirmation against a live
chain (movehook reads AgTrack directly) comes only after the rule exists on
paper -- not a run campaign.

**What this section does not settle**: reader 2's true semantics (the
prune dial stands in); gate 3 (unmodelled, conservative direction); the
older-era opcode vocabulary in the replay; the 26 gates-blind and 9
no-eval steps corpus-wide; and the 0x005FCAA0 attribution of the 28
off-sync steps.

---

## 1z-s. The pre-emit grant rule, DERIVED -- three zones, three clauses, and a corpus retrodiction that pre-empts 217 of 251 historical warps

**What exists now** (branch `claude/agtrack-guard`):
`toolkit/authsrv/agtrack_guard.py` -- the policy layer over the mirror, every
constant a decoded client constant or one arithmetic step from two of them;
`toolkit/authsrv/test_agtrack_guard.py` (41 checks, bare machine, constants
cross-pinned against authsrv's own resync derivations);
`agtrack_replay.py --policy` -- the retrodiction; and SHADOW wiring in
`authsrv.py` (telemetry rows `agtrack_guard` / `agtrack_repin`, ON by default
like the plane-echo tripwire, fused to self-disable on any internal error,
`--no-agtrack-shadow` to silence). **No active arm exists: nothing vetoes a
real send and nothing fires a real re-pin.** Zero client runs in any of it.

### 1z-s.1 The derivation -- the zones the decoded machinery forces

The reprieve test and its gates (SS-1z-q/1z-r) force a three-zone structure
on the sync copy's state, and every policy clause below is read off the
zones rather than designed:

- **GREEN** -- q within 100 u of the current-leg tube: MATCH, which jumps
  clean over all three gates. NOTHING can snap. Retail lived here (its
  stop-acks answered the client's own point at p50 34 ms).
- **YELLOW** -- out of tube, separation < 299.332591 u, sync on-mesh:
  evaluations run the gates; 1 and 2 pass; gate 3 (other agents) is the
  residual. A path-following grant recovers the tube at 288 u/s.
- **RED** -- separation >= 299.332591 u, or sync off-mesh: ANY evaluation
  snaps -- **including the evaluation triggered by the grant that tries to
  fix it** (the bake's tail dispatch tests q = the settled +0x78, which the
  grant did not move). No 0x0029 recovers from red. The only exit is
  0x002C, whose handler Clears FIRST so no test runs behind it
  (p5-resync-disarm SS-1, measured live).

**The three clauses** (each forced, none tuned):

1. **VETO + REPLACE.** A grant whose own delivery evaluation predicts a
   snap is never sent. With a fresh accepted report the re-pin goes first
   -- and the held grant may follow IMMEDIATELY, because after a 0x002C
   the fence is closed and a grant APPENDS instead of testing (dispatcher
   fence 0x00606002; round 5's "client only is REFUTED"). The composition
   is safe by the decode.
2. **PROACTIVE ARRIVAL CHECK.** The evaluations the server does not
   trigger are the sync copy's own arrivals -- and the mirror KNOWS every
   arrival tick (it computed it at the bake). Predict the evaluation at
   q = destination before the tick matures; a predicted snap re-pins
   first, on the server's own clock. **This closes p5-resync-disarm's
   HOLE A** (the report-driven sender could never reach an arrival inside
   a report gap; the mirror is not report-driven).
3. **TUBE-KEEPING IS AUDITED.** The shadow predicts every emitted grant's
   delivery verdict, so "the router keeps the tube" is a per-capture
   number, not a belief.

**The error budget** (why the veto line is not the raw red line): veto when
`modeled_sep + 288 * report_age + 10 >= 299.332591` -- the async copy can
be up to speed*age past its last accepted report (corroborated as a real
ceiling, authsrv's RESYNC_MAX_REPORT_AGE block), and the client's slow
clock is worth ~10 u (1z-q.5). The re-pin preconditions inherit
`_resync_verdict`'s derivations and are RE-DERIVED from R_MATCH and
DEFAULT_RUN_SPEED (max age = 100/288 s exactly; min interval 0.5 s under
the 299.33/576 s closing bound); `test_agtrack_guard.py` pins equality with
authsrv's constants so the two derivations cannot drift. **This also
answers p5-resync-disarm SS-4's open threshold dispute** (shipped 100 vs
resyncscore's 299.33): both were half right -- 100 u is the TUBE (where
MATCH protection lives), 299.33 is the CLIFF; the trigger is neither raw
number but the predicted verdict, budget-discounted.

### 1z-s.2 Two model corrections the retrodiction forced (and what they teach)

- **The two-world bracket.** First wiring: after the guard's own predicted
  snap it believed the fence closed, so grants "appended" unchecked -- and
  two real snaps landed inside that blind window. The server is only
  CERTAIN of Clears IT caused (1z-r.3's invisible resets cut both ways),
  so the guard now runs TWO mirrors: the main one applies every predicted
  reset, the TWIN applies only our own 0x002C. Reality is bracketed; a
  grant is vetoed if EITHER world predicts its delivery snaps. Cost:
  measured disturbance, below.
- **The click-silence glide.** The client reports NOTHING while pathing a
  click (silences to 37 s), so a raw last-report async belief goes stale
  exactly when it matters, and a click node planted at the stale position
  manufactured a false MATCH near the lagging sync copy. The guard now
  glides its async belief toward a click-in-flight destination at the
  granted speed (the client's own glide model applied to the async copy;
  straight-line, labelled an estimate). With both corrections the
  current-regime retrodiction is clean.

### 1z-s.3 The retrodiction (agtrack_replay --policy, live constraints, no future knowledge)

Corpus, 177 captures, 8,079 grants, 251 hard-bar warps:

| | n | share |
|---|---|---|
| pre-empted by VETO (clause 1) | 193 | 76.9% |
| pre-empted by RE-PIN due (clauses 1/2) | 24 | 9.6% |
| **pre-empted total** | **217** | **86.4%** |
| blocked (re-pin wanted, no fresh accepted report) | 8 | 3.2% |
| unseen | 26 | 10.4% |

Current regime (the two 2026-08-30 shipped-default captures): **10 of 10
pre-empted, 0 blocked, 0 unseen.** The refuted-density era (08-19, the
graveyard's `--heading-grant`/`--client-endpoint` day): 59 of 61 handled --
the graveyard failure retrodicted by the mechanism (32.3% of that day's
1,412 evaluations predicted MISS; the shipped+router day: 4.3%).

**The 26 unseen decompose, and none is silent**: the non-AgTrack
displacement mechanism (steps landing 1,800-1,940 u OFF the sync trajectory
-- 1z-r.1's partition; candidate 0x005FCAA0), the 08-24..08-27 eras whose
capture vocabulary the replay does not model (0x0025 direction arms,
0x0027/0x0028), one sub-300 u step consistent with a yellow-zone gate-3
snap (unguardable by construction -- gate 3 is other agents' state), and
the abort session's carve-entry step. The 8 blocked are HOLE A/C's honest
residual: the re-pin cannot fire on a position the server has no fresh
accepted claim to.

**Disturbance (the false-positive cost), stated as the UPPER BOUND it is**:
16.5% of corpus grants vetoed in shadow, 5.45% of quiet time with the
policy active; current regime 22.4% / 1.99%. Shadow over-states an active
arm structurally: the first veto's re-pin collapses separation, so the
grants after it -- counted as further vetoes in shadow -- would be green.
The lock-session stretches (where the sync copy sat parked >1,000 u out
for minutes) dominate the count, and vetoing there is CORRECT.

### 1z-s.4 Staging, and what ships

Shadow ships ON (telemetry only, plane-echo's class; fused; flag to
disable). **The active arms are deliberately NOT built in this change**:
actually vetoing sends and actually firing the re-pin change wire
behaviour, which is a flagged, owner-visible step -- the plane repair's
Q14 lesson is exactly about shipping a behaviour arm without that
conversation. The shadow's own rows are the evidence that conversation
needs: per-grant predicted verdicts against whatever the owner actually
plays, accumulating with zero operator cost.

**What this section does not settle**: the active arms (built next, OFF by
default, priced by the shadow's numbers); gate 3 (unmodelled, conservative
direction); the older-era opcode vocabulary in the replay; the exact
active-mode disturbance (shadow bounds it above); and the 0x005FCAA0
attribution of the off-sync steps.

### 1z-s.5 ADDENDUM, same night -- the active arm SHIPS, on by default

**Owner's direction, verbatim intent: "i just want movement code that
works."**  The staging split in 1z-s.4 (shadow now, active later, behind a
conversation) is overruled -- the working rule is the deliverable, not a
flag to ask about.  The active arm is therefore built and DEFAULT ON:

- **What it does**: when `repin_state` says DUE -- predicted red
  separation, off-mesh sync, a maturing arrival that would miss, or the
  budget crossing the cliff -- authsrv sends ONE `AGTRACK RE-PIN 0x002C`
  carrying the client's own last accepted report.  Fired from three
  places: both report arms (age ~0, the freshest instant) and the world
  tick at 2 Hz (the only sender that can beat a maturing arrival --
  clause 2 needs the server's clock, not the report stream).
- **What it can never do**: suppress, hold, or alter any grant.  The arm
  is ADDITIVE -- the only wire change it can make is an extra 0x002C at
  the client's own claimed position, correction bounded <= 100 u by the
  freshness gate (the client's own "close enough" radius).  With
  `--no-agtrack-repin` the wire behaviour is the pre-1z-s server exactly.
- **Bookkeeping is one path**: the re-pin goes through the ordinary
  send() choke, so `_note_wire_move` re-seeds the legacy sync model and
  the guard's own `on_emit` Clears both mirrors and stamps the rate
  limiter.  Guard state is fed from two threads (recv loop + world tick),
  so every access serialises through `_agtrack_guard_call`'s lock.
- **Tested**: `test_agtrack_guard.py` section 12 drives
  `authsrv._agtrack_maybe_repin` with a choke-faithful fake send -- the
  fire, its payload (the CLIENT's report, never ours), the post-fire
  safe-composition state, the no-second-fire, the staleness refusal, the
  flag-off restoration, and the unusable-plane refusal (floor 41 -> 49).
  Affected authsrv suite green: 224/73/41/121/26/20.
- **The verdict on whether it works comes from ordinary play**: every
  session now writes `agtrack_guard` rows (per-grant predicted verdicts),
  `agtrack_repin` transitions, and `agtrack_repin_fire` events beside the
  warps-or-not of the report stream -- the same instruments that scored
  every earlier candidate will score this one, with no dedicated run
  asked of anyone.  Prediction, stated first (the probe rule): on the
  retrodiction, sessions like tonight's two see their ~10 warps replaced
  by re-pins at a rate well under `--resync`'s old 5.6/min, and the
  residual warp classes are 1z-s.3's blocked/unseen (report-starved
  moments, gate 3, the non-AgTrack mechanism).

---

## 1z-t. THE PLAYER'S WORLD-0 SYNC — the defect measured in the client, the cause read in the binary, and the three-term fix shipped default ON

**This section closes ANIMREF-RE §40.12 item 1**, which handed the MOVECODE arc a
number to hit (retail ~74 u, ours 806 u) and an instrument that measures it live.
It is desk work over artifacts already on disk: **zero client runs**, one new
default, one revert flag per term.

### 1z-t.1 The defect, measured — and one of §40.11's two headline numbers is an instrument artifact

`agenttap.py` records BOTH client copies of an agent. On the 2026-09-02 kite
(`vault/research/animref/agenttap-20260902T213401.jsonl`, 507 player samples,
~11 Hz over 55 s) the player's own world-0 (sync) copy sits far from the world-1
copy that is DRAWN. §40.11 published "median 237 u, max 806 u". **The median is
robust and the maximum is not:**

| reading | p50 | p90 | max |
|---|---|---|---|
| raw `m_point` (+0x78), as §40.11 quotes | 237.0 | 511.8 | **805.8** |
| `AgAgent::position_at` semantics (clamp first) | 237.0 | 431.3 | **516.1** |

`m_point` is sample-and-hold and `+0x58` is its settle stamp; the stamp's age at
sample time runs p50 **2.8 s** on the sync copy (max 13.4) and p50 1.3 s on the
async one, which is older than 0.2 s in **91%** of samples. Dead-reckoning must
therefore go through the client's own rule (`movetap.py:851-876`): **clamp first**
— if `m_timeStopMovement != 0` and `when >= it`, the agent sits on its segment
point and is NOT integrated, because dead-reckoning past the arrival tick invents
a separation the client never computes. **Quote 237 u p50 / ~430-510 u p90 and
retire the 806.** This is the movetap point-column trap in a new tool, the third
time this arc has paid for it, and it changes no conclusion: 237 u against
retail's ~74 u is still the defect.

**A second correction to the same capture, and it matters for every future run.**
Joined to the harness's own `report.json` legs, **every A and D leg travelled 0 u**:

| leg | drawn body | world-0 | separation |
|---|---|---|---|
| wait   |    0 u (vmax 0)   |   0 u |   0 .. 0 |
| S (4s) |  751 u (vmax 190) |   0 u |   0 .. 751 |
| D (4s) |    0 u (vmax 0)   |   0 u | 237 .. 237 |
| A (5s) |    0 u (vmax 0)   |   0 u | 237 .. 237 |
| W (4s) | 1138 u (vmax 288) | 749 u |   0 .. 627 |
| S (3s) |  357 u (vmax 190) | 425 u |   0 .. 315 |
| D (3s) |    0 u (vmax 0)   |   0 u | 198 .. 198 |
| W (3s) |  514 u (vmax 288) | 149 u |  48 .. 465 |
| A (3s) |    0 u (vmax 0)   |   0 u | 341 .. 341 |

In Guild Wars **A and D turn in place**; Q/E strafe. So four of the nine legs
translate nothing, the client correctly emits no `0x003D` across them, and the
15.4 s "report gap" that looks alarming in the wire is the client behaving
correctly. §40.11's numbers rest on **four** real translation legs. **A future
verification run must drive W/S (and Q/E for strafe), or it scores turn-in-place
legs as movement.** The per-leg table is also the sharpest statement of the
defect: world-0 travels 0 u where the body travels 751, 149 where it travels 514,
and **425 where the body travels 357** — the last one an overshoot, visible
directly, and the subject of term 2 below.

### 1z-t.2 The cause, read in the binary — a fixed-magnitude chase of the body's past

Reconciling §40.11's "nothing updates the client's world-0 self-copy" with
`studies/movement/FINDINGS.md`'s "0x0025 is facing-only, 0x0029 is sync-only":
**both are half-right, and the exact statement is one sentence.** The client never
carries world-0 forward from local input, `0x0025`'s setter `0x00602660` writes
the facing triple `+0xB8/+0xBC/+0xC0` and nothing else (12 stores, exhaustive),
and `0x0029` is SYNC-ONLY (handler `0x005FD890`, sync arm `0x005FD8CE`, no async
arm) — so **under our zero-lead default a fresh `0x0029` is the sole thing that
moves the player's world-0 position.**

The bake `0x005FE950` does not write a position. It settles `+0x78`, then arms a
velocity of **fixed magnitude `|v| = maxSpeed x moveSpeed` (`+0x5C x +0x60`),
distance-independent**, plus an arrival tick `+0x48`; the `<= 1.0 u`
short-circuit at `0x005FEA85` parks the copy on arrival. So world-0 does not sit
still so much as **chase the body's past at exactly the body's own speed**, glide
for about one report interval, and park — with a lag fixed at grant time that can
never decay. A lead can stop world-0 falling behind; **because `|v|` does not
scale with distance it can never make it catch up.**

Write-set table, build 38797, recv table `0x00A52D70`:

| SMSG | handler | arrays | fields |
|---|---|---|---|
| `0x0025` | `0x005FD540` | sync always; async GATED (`0x005FD5CD` pending record, `0x005FD5D3` id == `[mgr+0x1E0]`) | `+0xB8/+0xBC/+0xC0` ONLY |
| `0x0027` | `0x005FD700` | both, ungated | settle, `+0x5C`, then re-bake of the outstanding destination |
| `0x0028` | `0x005FD7D0` | both, ungated | settle + teleport to the agent's OWN point; PARKS both |
| `0x0029` | `0x005FD890` | **SYNC ONLY** | `+0x80`, `+0x88..+0x94`, `+0x98 = 0`, `+0x9C..+0xA8`, then the bake |
| `0x002A` | `0x005FD930` | **SYNC ONLY** | as `0x0029` plus `+0x98` = the extra wire word |
| `0x002B` | `0x005FD9D0` | **SYNC ONLY** | `+0xC4` = movementType, `+0x60` = moveSpeed; read only by the NEXT bake |
| `0x002C` | `0x005FDA50` | both, ungated, after `AgTrack::Clear` | hard set; tail-calls reconcile |

### 1z-t.3 ★ THE LAW, and it has no free parameter

**separation = report_gap x body_speed.**

Our in-leg `0x003D` gaps are modally **1.80 s**: 1.80 x 288 = **518.4 u**
predicted against **516.1 u** measured, −0.4%. Retail's 0.257 s x 288 = **74.0 u**
(§38.3). **Cadence ratio 7.00x, separation ratio 6.97x.** Report LATENCY is not
the defect — at the instant each `0x003D` is sent the reported point is a median
**12.3 u** from the body (max 33.7). The client tells the truth promptly; it tells
it rarely, and we answer with a point that was already old.

### 1z-t.4 ★ THE SHIPPED AgTrack GUARD IS STRUCTURALLY BLIND TO THIS — measured, from the run itself

The active re-pin arm has been default ON since `2f00ea5` (§1z-s.5), and the
obvious question is whether it already handles this. **It does not, and the kite
proves it from both ends.** In `vault/captures/gamesrv/authsrv-20260902T213400-c1.jsonl`
the guard evaluated **10 grants and returned `code=pass, why=match` on 10 of 10**,
while the actual world-0-vs-drawn separation at those same instants was
0.0, 513.8, 237.0, 511.8, 511.8, 114.9, 277.2, 192.6, 197.6, 465.1 u.
`agtrack_repin_fire` = **0**.

The reason is structural, not a bug: the guard's MATCH is the **reprieve test** —
the sync copy against the client's own recorded history chain, oldest-match-wins
over the whole chain — and it is satisfied *precisely because* the sync copy sits
on ground the player already walked. **"On the trail" and "near the body" are
different predicates**, and zero-lead's verbatim echo makes the first one true by
construction, which is exactly what makes zero-lead warp-safe. The guard prevents
snaps; it was never built to see world-0 lagging the rendered body, and it cannot.
**The two are orthogonal and both are wanted.**

(Instrument note: a text search for "agtrack" in a run's console log reads zero in
three unrelated situations — the per-grant rows go only to the JSONL recorder, a
fired re-pin's console line is capitalised `AGTRACK RE-PIN`, and the two capture
directories use DIFFERENT STAMPS for one run: gamesrv telemetry `213400`, authsrv
wire `213356`, tap `213401`. Score the JSONL, never the console.)

### 1z-t.5 Retail, derived — the lead is the sync mechanism, and the clip is not only wall-safety

On the adjudicated 9 live captures, retail's keyboard grant is
`0x0025` → (`0x002B` on family change) → `0x0029` at `reported + vec2 + 0.5*u`,
`|vec2|` pinned 765.018/768.000, inter-grant p50 **0.492 s**, 43.3% of dests
clipped short. Under that lead the baked leg is **2.18 s** long against a
**0.491 s** re-grant interval — **the copy is re-baked 4.45x before it could ever
arrive**; only 282 of 3,071 legs (9.2%) reach `+0x48`, and the copy is parked at
**1.8%** of moving samples against ZERO_LEAD's **14.8%**. So it never stops
walking, and since `S ≈ v_body` it walks WITH the body at a fixed offset rather
than chasing it.

**The one-variable counterfactual** (same grant times, same
`0x002B`/`0x0027`/`0x0028`/`0x002C` streams, ONLY the destination changed):
retail's dests hold the sync copy **p50 62.2 u** from the rendered body where our
ZERO_LEAD holds **p50 387.5 u** — 6.2x.

**An identity check that could have failed, and did not.** The simulated client
world-0 lands **2.8 u** from ArenaNet's *server's* own copy of the player —
measured independently as the destination of NPC `0x002A` follows naming the
player, which is not an input to the simulation — against positive controls of
80.0 u (last reported position), 74.2 u (interpolated body) and 15,677 u (a frozen
copy), over 45 follows with the player walking at p50 287.4 u/s.

**Where the ~74 u comes from: the question's two readings are two different
objects and both are true.** The SERVER's copy is a sample-and-hold on the last
report (NPC follow dests best-fit the player's own reported polyline at
tau = **0.257 s**). The CLIENT's world-0 is a constant-offset shadow: its distance
to the body is FLAT in grant age (58-67 u from an anchor 0.1 s old to one 2.0 s
old) while its distance to the anchoring report grows at exactly body speed
(455.4 u measured against 288 x age = 455.8). Under ZERO_LEAD the two errors ADD.

**The clip is NOT only wall-safety, and this CONTESTS the framing this section
started with.** On identical grant times, retail's clipped mixture gives p50 62.2
/ p90 239.1 against a flat 766 u lead's 157.9 / **650.6** — the 43.3% of dests
retail shortens is the only difference between those arms and it owns the tail.

**One theorem died in the deriving and should not be resurrected:** that the lead
sets the loop time constant, tau = Lambda/S. Retail's stream fits it beautifully
(2.633 s measured against 765.5/288 = 2.658 s) and **it is a coincidence** — a 19x
sweep of flat leads from 86 to 1600 u returns beta 0.924-0.934 throughout, tau
6.3-7.4 s regardless of Lambda. What mean-reverts retail's error is the clipped
mixture, not the lead magnitude.

### 1z-t.6 ★ THE CROSS-CHECK — scored against the client's OWN world-0 track, which no earlier candidate in this arc had

Every previous simulation in this arc (`grantsim`, `agtrack_replay`) validated
against snaps and wire. The tap holds world-0 itself, in a **different regime**
from retail's corpus: our client, 1.8 s cadence, short start-stop legs.

**Step 1, the check that can fail.** Drive the model with the grants ACTUALLY
sent and score against the OBSERVED world-0: **p50 0.0, p75 13.2, p90 16.0,
max 69.1 u.** (Before the `position_at` clamp went in, the same model read p90
136 / max 504 — the clamp is 90% of the model's accuracy and it is the client's
own rule, not a smoothing choice.)

**Step 2, the counterfactual**, same reports, same cadence, only the policy
changed, scored against the OBSERVED DRAWN BODY:

| arm | p50 | p75 | p90 | max |
|---|---|---|---|---|
| SHIPPED (observed, ZERO_LEAD)      | 237.0 | 340.7 | 431.3 | 516.1 |
| lead 520, no stop echo             | 179.3 | 283.0 | 335.1 | 414.6 |
| lead 766, no stop echo             | **425.3** | 529.0 | 581.1 | 660.6 |
| lead 520 + stop echo               |   0.0 |   9.5 |  69.7 | 335.1 |
| lead 460 + echo + `0x002B` rate    |   0.0 |   8.6 |  63.1 |  85.7 |
| **lead 520 + echo + `0x002B` rate**| **0.0** | **4.4** | **13.3** | **85.9** |
| lead 766 + echo + `0x002B` rate    |   0.0 |   4.2 |  13.3 |  86.5 |

**THE THREE TERMS ARE NOT SEPARABLE, and the ablation is why this ships as one
behaviour.** The lead ALONE at 766 u is **worse than shipping nothing** (p50 425
against 237) because it overshoots every stop; the stop echo is what collects it.
Any reading of "the lead is the fix" or "the stop echo is the fix" alone is
refuted by its own row here.

**AND THIS ANSWERS THE RETAIL DERIVATION'S OWN OPEN QUESTION.** Scored on
ArenaNet's forward-running captures the family rate reads as noise (62.2 → 51.9 u)
and the derivation asked outright whether that corpus simply never leaves cruise.
**It does not leave cruise.** Our kite has real backpedal legs — the drawn body
runs at `{190.1, 288.0}` u/s while world-0 has only ever run at 288.0, because we
send the player no `0x002B` at all (0 of 7 `AGENT_UPDATE_SPEED` rows in the
capture name the player; all seven name the Hatcher) — and on that substrate the
term is worth **p90 69.7 → 13.3 and max 335.1 → 85.9**. `0x002B` is not inert; it
is invisible to a corpus that never backpedals.

**Why 520 and not D1's 766.** The lead must cover the most ground the body can
travel between two re-aims or `+0x48` fires and the copy parks. The client's
`0x003D` is DISTANCE-triggered: held-heading chords run p95 **513.8**, p99
**515.1 u** (corroborating REALFIX-W2's ~515 u from a different corpus). 520 is
read off the client's own trigger, not fitted. 460/520/766 sit within noise of
each other once the echo is on (p75 8.6 / 4.4 / 4.2); 766 is 1.49x the trigger
distance with a signed p95 overshoot of +513 u against +342 at 520.

### 1z-t.7 What ships — `KBD_SYNC`, default ON, four flags

`authsrv.py`, on the `0x003D` and `0x0047` arms only. **The click arm is not
touched.**

1. **LEAD** the heading grant `520 u` along the client's own reported heading,
   then clip it to the navmesh with `a2_clip_lead` (§0.17's D2 term, reused). The
   LENGTH is ours, the DIRECTION is the client's, and the ray is anchored on the
   REPORT in hand — never `state["pos"]`, which is `--heading-grant`'s epitaph.
2. **SPEED TRUTH**: the edge-triggered `0x002B` family rate, same slot and same
   edge as A2's, labelled `KBD SPEED-TRUTH`.
3. **STOP ECHO** at every `0x0047`: `0x002B [1.0, 9]` then a zero-distance
   `0x0029` at the reported stop, both plane words the client's own.

Revert: `--legacy-kbd-sync` (all three, byte-identical to the pre-1z-t wire),
`--no-kbd-lead`, `--no-kbd-speed-truth`, `--no-kbd-stop-echo` (one term each, so
one run can convict one term). `D1_LEAD` owns the slot when both are set, so a
`--d1-lead` run still measures REALFIX-A2 and not a mixture. Plane words on the
heading arm are DELIBERATELY untouched — the only thing 1z-t changes there is the
POINT, so one run can convict it.

**This is not `--stop-echo` and not `--heading-grant`, and both epitaphs were read
first.** `--stop-echo`'s own 2026-08-25 correction block is the licence: *"the
harm is the WALK, whose length is |D − the sync copy's settled +0x78| —
reconstructed at ~1,286 u for the 2026-08-19 echo, against a ~60 u p50 for
retail's own stop-ack, which is MECHANICALLY THE SAME MESSAGE... The refutation is
of BAKING A LONG LEG FROM A FAR COPY."* Term 1 supplies exactly the precondition
that refutation names. The same block also retracts the operator's "it adds a
SECOND destination": every `0x0029` overwrites unconditionally.

Tests: `test_kbdsync.py` (32 checks, floor 32) and `test_position_trust`'s
re-aimed stop-arm section. `test_d1lead`'s two count-locks moved with the code
(the clip's call sites 1 → 2, the family re-arm 6 → 7) — and the clip lock now
SUBTRACTS the definition, because `def a2_clip_lead(state, reported, dest)`
matches the anchored-call pattern and a bare count reads 3 for two calls: this
arc's substring trap, for the fifth time.

### 1z-t.8 What this does NOT settle

- **The verdict is an operator run and nothing here substitutes for it.** The
  registered prediction: `agenttap.py --agents 1` during a keyboard walk reads
  world-0 vs world-1 **p50 under 150 u** (baseline p50 237 / p90 431 / max 516 on
  `agenttap-20260902T213401`, which is the before-picture and needs no new run).
  The offline counterfactual says p50 0 / p90 13 / max 86 and the model's own
  validation error is p90 16 u. **REFUTED IF** the p50 stays above 200 u, or if
  the operator reports a NEW visible warp class the shipped default did not have.
  **Drive W/S, not A/D.**
- **The guard's behaviour under a lead is UNVERIFIED.** With a lead the grants are
  no longer past-trail nodes, so the reprieve test will MATCH less often and the
  re-pin may fire where it never has. The arm is additive by construction (it can
  never suppress, hold or alter a grant — §1z-s.5), so the worst case is extra
  `0x002C` re-pins bounded ≤100 u at the client's own reported position. It should
  be scored from the first capture's `agtrack_guard` rows.
- **The n is thin**: four real translation legs, one map, one operator, one
  capture with world-0 ground truth. The retail side is 9 captures and 2,442
  moving reports, but it has no world-0 ground truth at all. The two together are
  the argument; neither alone is.
- **The click path is untouched** and its own failures (F-A/F-B/P-17, the
  report-starvation that silences every report-driven guard) are unaffected.
- **A re-grant timer is REFUTED before being built**: a 0.5 s timer re-using the
  last REPORTED anchor is roughly free (p90 583.8 → 536.2) while the same timer
  extrapolating the anchor forward blows the tail to p90 **2,416** / max 18,067 u,
  because the body may have stopped or turned inside the silence. Do not build it.
- `0x0027` matters to the glide and `0x002B` does not, **on retail's substrate**
  (62.2 → 51.9 without `0x002B`; 82.0 / p90 646.4 without both) — and §1z-t.6 shows
  that conclusion is regime-bound. We send neither today; only `0x002B` is added
  here.

### 1z-t.9 ★ RUN-1zT RAN 2026-09-03 AND CONFIRMED — p50 237 u → 0.0 u

Runsheet and full readout: [RUN-1zT.md](RUN-1zT.md). Registered bound was p50
< 150 u to confirm, > 200 u to refute.

**The registered arm** (`agenttap-20260903T073122`, scripted walk, hands off):

| | baseline 09-02 | run |
|---|---|---|
| world-0 vs drawn body p50 | 237.0 | **0.0** |
| p75 / p90 | 340.7 / 431.3 | **1.0 / 17.7** |
| max | 516.1 | **198.9** |

Exposure 3,572 u of body translation over 193 moving samples, well over floor.
Wire: 12 `KBD LEAD`, 7 `KBD SPEED-TRUTH`, 1 `KBD STOP-ECHO`.

**Term 2 is now a measurement rather than an inference.** World-0's own speed set
went from a bare `[288]` — against a body running `{190, 288}` — to
**`[190, 216, 288]`**. The `0x002B` family rate reaches the client and world-0
walks the family the body is using. This is the term the retail corpus called
inert (§1z-t.6); it is not, and a forward-running corpus simply cannot see it.

**The residual is an acquisition transient, not a standing error.** Per leg:
the opening `W` runs body 868 / world-0 962 u and carries the whole run's 198.9 u
maximum; every leg after it tracks to within a few units — `S` 743/722 (sep ≤
24.6), `Q` 509/509 (≤ 6.5), `E` 513/509 (≤ 6.5), `S` 504/510 (≤ 6.3). The law of
§1z-t.3 predicted the *steady state* and the steady state is what collapsed.

Enemy control unchanged: agent 10's own two copies p50 5.2 / max 27.9 u.
**§40.11's reading — that the enemy was a faithful victim — survives its own
test**, since nothing enemy-side changed and the enemy stayed faithful.

**★ THE §1z-t.8 UNVERIFIED ITEM RESOLVED, IN THE PREDICTED DIRECTION.** A lead
stops grants being past-trail nodes, so the AgTrack reprieve test should stop
MATCHing trivially. It did: baseline 10/10 `pass/match` with **zero** re-pin
fires; this run 12 `pass/match` **plus one `veto/gate2-offmesh` and one real
`agtrack_repin_fire`**. The guard is now doing work it could not do before, on
an off-mesh grant, and it remains additive by construction. **Two exposures to
watch, neither yet a defect:** the clip's `origin-unwalkable` door opened on
**3 of 12** grants (the client's reported position off *our* mesh — known
coverage debt; the door's fallback is a safe zero-distance lead), and
`agtrack_repin blocked/arrival-risk` fired **7** times — clause 2 wanting a
re-pin with no fresh accepted report to carry it.

**A second, unregistered arm exists and is NOT the result.** The first attempt
(`agenttap-20260903T072932`) had the operator supplying keyboard input alongside
the script, so two sources drove one body. It confirms on the median (p50
**123.0** u) but its maximum separation is **854 u, worse than the baseline it
beats** — a fix that works reading as a regression on the tail because the arm
was contaminated. Recorded as a free second regime and as the reason the runsheet
now carries a HANDS-OFF block. **Process note, and it is the session's own
mistake:** this run needed no human aiming at all — scripted `--walk`, a
read-only tap, a self-closing session — and handing it over as a runsheet rather
than driving it is what created the opportunity to contaminate it.

**What this closes and what it does not.** It closes §1z-t as a mechanism: the
law, the cause and the three terms are confirmed against the client's own copy.
It does **not** yet close the operator's *felt* symptoms — the swing-distance and
warp-beside-the-enemy reports of §40.7 — because this run scored memory, not
experience. That is ANIMREF-RE §40.13's question and wants an ordinary session,
not an instrumented one.

### 1z-t.10 Provenance

All figures are measurements over the owner's own captures via extractors in this
repo (`agenttap.py`, `movetap.py`'s `position_at`, `tape.py`/`codec.py`,
`animgrammar.py`) plus read-only static reads of the pinned pristine 38797 client
via `codescan.py` (carve-out 1, no launch). The counterfactual simulator is
session scratch over the same artifacts; its validation against the observed
world-0 is stated above and is the only reason its numbers are quoted. No asset
bytes, no upstream derivation, no §6.1 register row required.

---

## 1z-u. THE FRESHNESS GATE, DERIVED — the fix as asked is refuted, the operator's "bad run" was 1z-t's own lead, and the lead is now OPT-IN

**Asked:** "do the freshness gate fix" — `PLAN.md` §7 Q13's cheapest item — after the
operator's first ordinary session (RUN-FEEL, 2026-09-03 08:46) showed **40 of 40 clicks
refused `geo-stale`**. **Answered by derivation, and the answer is not the fix that was
asked for.** Zero client runs. Four derivation lanes + three skeptics on the gate (one
lane lost to an API outage; its script survived and was run by hand), then a
correction to 1z-t built and **refuted by two more skeptics before it reached main**,
then the conservative change that did ship. Every number below was re-derived by at
least one lane told to refute it.

### 1z-u.1 Widening the window is dead by arithmetic, and the gate protects nothing

- **The 1.0 s constant cannot be "widened to a principled value."** On the operator's
  own 40 clicks the report age was **15.0–21.3 s** for clicks 1–31 (only the spawn
  stamp existed) and **3.8–11.5 s** for 32–40. Any window ≤ 15 s answers ≤ 9 of 40;
  only ≥ 23 s answers all — past retail's own observed maximum of **20.99 s**.
  Widening converges on bypass. NOT-FOUND with a positive control: "widen" was never
  built or run.
- **The gate does not protect the plane word.** Both plane words are computed ABOVE
  it and identically with or without it — field 3 = the click's own plane
  (`values[2]`, `:18925`), field 4 = `state["plane"]` from the last accepted report
  (`:18974`, paired at `:19009`). `fresh` decides only whether geometry RUNS and
  whether the answer is SENT. The gate comment's thesis ("answering stale corrupts
  the plane") is really an argument for not answering — and the shipped cost of not
  answering is the measured 5,970 u spawn warp (K1 arm A).
- **Retail has no freshness precondition.** Adjudicated 9: **26 of 26** clicks
  answered in 30–65 ms, **21 of 26** with a report older than 1.0 s or none ever (max
  20.99 s), and nothing bad follows — 0 repositions, next input answered 17/18.
- **D1's model-aware bypass (`a2_click_leg`) is structurally inert in click play** —
  armed only by a fired `--d1-lead` keyboard grant, popped by the next report.

### 1z-u.2 `--click-echo` is LIVE for the answer decision and REFUTED as a default — three lenses

`--click-echo` (K2) is the only bypass that survives the graveyard: geo-stale only,
the client's own x,y, 8/8 answered, 446 u largest displacement, 0 spawn landings, and
`--echo-any-refusal`'s refutation provably does not transfer (zero staleness echoes
reached its wire; all 46 grants were geometry echoes). It stays opt-in. Three
skeptics, each told to refute shipping it as the default, each did, for different
reasons:

1. **It would not have fixed this session.** Phase-split of the tap: during the 6.2 s
   of drag-clicking (31 of 40 refusals, a click every 0.13–0.20 s) world-0 vs drawn
   body was **p50 23 / p90 138 / max 166 u** and every Hatcher swing in that window
   landed **70–94 u** from the rendered body — inside reach. The two long-range
   swings (486, 420 u) and the 495 u tail are the **keyboard arm's** (§1z-u.3). A K2
   counterfactual on the drag makes the median WORSE (23 → 57 u) for a 23 u tail
   gain; the recovered SIM script agrees in shape (click burst 1: shipped p50 23 /
   p90 138 vs K2-as-coded p50 36 / p90 98). "K2 answers 40/40" overstates the wire:
   under the shipped rate tower a 5–7 Hz drag coalesces to **21 of 40** echoes.
2. **Its plane word is a lock hazard on seam-rich maps.** K2's field 4 is
   `state["plane"]`, frozen across a click walk the echoes themselves drive across
   seams. OBSERVED in K2's own client bin: 16 of 18 SYNC stamps were 0 while 5 of 8
   echoed legs crossed non-zero planes; at 89.89 s a gated reseed rewrote the LOCAL
   body's plane 32 → 0 — legal by 752 u of timing. Corpus counterfactual: **709**
   incoherent stamps in 36 of 116 click sessions — **0 on map 146**, the operator's
   map. The matched-word variant is worse (1,607). The derived word, if this path is
   ever built: field 4 := `pm.plane_at()` of the modelled sync copy.
3. **It reopens the no-clip on long clicks.** 7 of 8 of K2's own echoed lines were
   mesh-blocked (shortfalls to 4,322 u); client-side depth inside blocked ground 347 u
   (r4a) against a 2 u control. `--router` kills it (0 samples > 1 u deep in two
   runs) — but every router run predates `PRESS_SUPERSEDES_LEG`, which places both
   copies on the RAW click chord, and had zero attack presses.

**In the operator's 08:46 session either arm would have been clean**: all 40 dests
on-mesh, 29–270 u from the body, 0/40 blocked lines, `route()` one leg for 40/40.
The no-clip is a property of LONG clicks across geometry, not of this regime.

**What the click path should eventually get** (not built here): `--router` as the
default, with (a) the click-leg record re-armed to the routed first leg so the press
re-pin stops placing the body on the raw chord, and (b) the derived plane word. That
is its own arc with its own run. **Q13 is updated, not closed.**

### 1z-u.3 ★ THE SESSION'S SYMPTOMS WERE 1z-t's OWN LEAD — a keyboard lead maturing unanswered

The tap's tail (p90 223 / max 495 u), both long-range swings and the starved attack
trace to **one grant**. The `KBD LEAD` at 24.09 s sent world-0 519.5 u west at
speed-truth 0.66. The client's next heading report **66 ms later** was refused
`heading-rate` and **dropped by design** — `_heading_grant_ok`: *"a refused heading
grant is DROPPED, NOT HELD — the next report carries a fresher position"* — a premise
that failed: no `0x003D` for 2.7 s / 567 u. **The drawn body kept walking its OWN
north-west heading** (tap target (9554,8705), v = (−92, 195), from 24.08 to 26.75 s —
NOT the lead's endpoint). At the lead's arrival (26.85 s, ETA 24.09 + 518/190) the
client's arrival reconcile **snapped the drawn body 498 u** onto the sync copy's
parked point (9412,8041) — and that snap **shut the AgTrack fence**, after which every
grant is walked as an order and key releases go unreported: five keyboard reports,
**no `0x0047` ever**, the stop echo never fired, the keyboard latch stayed armed
(ANIMREF-RE §41, `f6fe4e5`; attribution to this lead corrected by that session in
`faa5b94`). Zero clicks occurred between 22.06 and 27.99 s. Skeptic 3's correction:
the click gate still produced ~36% of the p90 tail (a 1.7 s excursion of refused
post-snap clicks) — not blameless, not the cause.

**The same thing is inside RUN-1zT's CONFIRMATION, and the p50 0.0 is contaminated.**
From 18.65 s — an arrival snap (25 u) of the 15.747 s lead whose 16.211 s re-report
was rate-refused — the drawn body's walk target equals OUR granted dest **to the
unit on every later leg** ((9481,8430), (10014,8430), (9511,8950), (9511,8430),
(8991,8430)), and per-leg body travel is ~520 u for both 3 s and 4 s holds (Q 509, E
513, S 504 in §1z-t.9). **World-0 vs body cannot distinguish "world-0 follows the
body" from "the body follows world-0."** One release in seven produced a `0x0047`,
and that one followed the leg whose leads were all zero-length clip fallbacks.
§1z-t.9's headline stands as a measurement and falls as a confirmation: it needs an
enslavement detector (async target == granted dest; per-leg travel vs hold duration)
before it is quoted again.

### 1z-u.4 The correction I built, and why it was refuted before merging

I read the missing `0x0047` as the client executing a grant it did NOT propose as a
click-order, and built the fix: make the lead the client's OWN proposed endpoint
(retail's D1 formula, `d1_lead_dest`). Desk evidence: per keyboard burst "closed by
a `0x0047` within 3 s", 520 u lead 1 of 9 vs D1's own-endpoint ~70%. **Committed on
the worktree as `8641930`, refuted by two skeptic lanes, reverted as `723641e`.**
What they established, each re-derived from captures:

- **The mechanism is NOT FOUND in any decode and contradicted by the record.** The
  `0x0029` handler writes `+0x80/+0x88..+0xA8` and bakes; nothing reads a pending
  proposal. REALFIX §0.10 layer 1, §0.11, §0.17 and RETHINK §2 all say every fired
  `0x0029` is an order-walk once the fence is shut — D1's own-endpoint leads
  included (§0.17: 24 of 36 D1 leads walked through walls).
- **Retail's own wire refutes it directly.** ArenaNet sends a dest that is NOT the
  client's proposal on **1,223 of 3,072** grants (40% — the D2 clip), 988 on-ray but
  SHORT — our 520 u geometry. Next input after on-ray grants 400–766 u short
  (n = 447): KBD 397 / STOP 21 / none 7, the same shape as bit-exact grants, all 21
  stops landing SHORT of the dest. By the diff's own metric, bit-exact D1 bursts
  close at **13.7%** and CLIPPED ones at **38.8%** — the opposite direction.
- **My 11% vs 70% was an instrument artifact.** A 1 s burst gap splits a held walk
  (report cadence modally 1.8 s) into several "bursts" most never followed by a
  release, while A2's 2.4 s protocol legs make one burst per release. Per held-key
  LEG the zero-lead arm closes 3 of 4 (9 of 9 at a 6 s window). And the D1 arm hides
  contiguous silent full walks with the own-proposal point — 063459 t = 154–176 s
  (8 bursts, zero `0x0047`, §0.10's incident #29), 073609 t = 25.8–35.3 s (the §0.11
  golden lock repro), five silent walks to the D1 endpoint after 3.7–8.2 s of
  silence.
- **Under the diff the 08:46 session plays out identically with a ~766 u snap
  instead of 498.** The point's identity never enters the fence logic.
- **The §0.11 input-lock armer is live on the KBD path.** `pc_matched` is False on
  all 14 fired `KBD_SYNC` rows; 073121's 12.358 s grant has plane cur = 0, dest = 29.
  I skipped `a2_matched_field4` on this arm "to change one variable" — the skip
  reintroduced a decoded lock cause.
- A number in the reverted comments, "1,650 of 3,037 bit-exact", has no extractor
  in `studies/`; REALFIX §3.2's **1,642 of 2,599 on-ray rows at +0.500** is canonical.

**Retail's D1 formula is retail-verbatim and sync-neutral-to-mildly-better; it is
not a stop-report mechanism.** If the length is ever changed it is argued on
**maturation margin** — 766 u leaves ~250 u over the ~515 u report chord where 520
leaves 5 — with the longer forced walk stated as its cost.

### 1z-u.5 What shipped: the lead is OPT-IN, the two additive terms stay

One run convicted one term, so that term is out (§29's rule, applied). `KBD_SYNC_LEAD_ON`
defaults **False**; `--kbd-lead` opts in; `--no-kbd-lead` still parses and wins so
pre-1z-u runsheets keep their meaning; the banner prints the split and warns when
the lead is on. The family rate and the stop echo stay ON — nothing has convicted
them, and under zero-lead the copy parks near the report, the drift is §1z-t.3's
report-chord lag, and the stop echo closes it at every stop (the scripted
counterfactual's "stop-ack only" arm: p50 237 → 0, p90 431 → 272, with no
forced-walk exposure). The formula is unchanged behind the flag.

**Before the lead returns, in order, each with its own test:** (a) a rate-refused
heading is HELD and re-baked at the floor, never dropped, and an in-flight keyboard
lead is killed by the zero-distance re-pin on any press or click (what `PRESS ENDS
THE WALK` already does for click legs) — never let a keyboard lead outlive its
answer; (b) `a2_matched_field4` on the KBD grant and stop-echo path; (c) the
enslavement detector on any lead run; (d) the two new `0x002C` senders
(`AGTRACK RE-PIN`, `PRESS ENDS THE WALK`) audited as fence-shutters — 08:46 had five
before the keyboard burst.

`test_kbdsync` pins the split and the flag semantics; the affected suite is green.

### 1z-u.6 Corrections to the record, collected

- **The operator's map is 146 (Lakeside County), not 148.** The `version` row's
  `map_id` is the LOGIN map and reads 148 for every session in the corpus; the
  instance is `MAP_UPDATE_CURRENT 0x0099` (`9900 9200` = 146; K2 and R7 `9900 1801`
  = 280). Found independently by two skeptics.
- **RUN-FEEL's "the press re-pin lands 0.2–24 u from the drawn body, so the teleport
  hypothesis is refuted" measured the body AFTER the hard set.** Joined to the last
  sample BEFORE the raw world-0 jump, the ten `0x002C`s moved the drawn body
  13.8 / 19.5 / 83.8 / 30.2 / 96.9 / 57.4 / 0.3 / 86.5 / 0.2 / 39.2 u. Symptom 3 has
  five specimens in that session and the click gate is not their cause.
- **RUN-FEEL's `click_moving_at` diagnosis of the stuck attack was WRONG** (§41 found
  `kbd_moving_at`, unbounded). A task chip carrying the wrong mechanism was spawned
  from this session and correctly overridden by the session that took it.
- **"The body walked to the lead's endpoint at 216 u/s"** (§1z-t's correction text
  and §41.2) is wrong on the tap: it walked its own heading and was SNAPPED. Told to
  the §41 session.
- `heading-rate`'s "dropped, not held" premise is false whenever the client is
  silent on a matured lead — the next derivation target, (a) above.
- `agtrack_guard` telemetry lives in the gamesrv JSONL, not the console; a fired
  re-pin's console line is capitalised `AGTRACK RE-PIN`.

### 1z-u.7 Provenance

All figures are measurements over the owner's own captures via extractors in this
repo (`w0score.py`, `agenttap.py`, `tape.py`/`codec.py`, `livewire.py`,
`readhook.py` on the K2 movehook bin) plus read-only static reads of the pinned
38797 client via `codescan.py`. No asset bytes, no client launch, no upstream
derivation.

---

## 1z-v. THE ROUTER IS THE DEFAULT CLICK POLICY — §1z-u's derived answer built, with its two conditions, and the composition the router never had

**Asked:** "continue the movement arc: do the router fix" — the click path's derived
answer from §1z-u.2: *`--router` as the default, with (a) the click-leg record re-armed
to the routed first leg so the press re-pin stops placing the body on the raw chord,
and (b) the derived plane word.* **Built at a desk, zero client runs**, one retrodiction
over the operator's own 08:46 capture with its prediction registered first, and the
affected suite green. Ident `MOVECODE-1z-v`.

### 1z-v.1 What shipped, and why each piece is derived rather than chosen

- **`ROUTER = True`.** The derivation is §1z-u.1–.2 and is not restated: the freshness
  gate cannot be widened (click ages 15–21 s; only ≥ 23 s answers all 40, past retail's
  20.99 s max), it protects no plane word, retail has no freshness precondition
  (26/26), `--click-echo` is refused as a default on three lenses, and the router is the
  one click policy in the file that answers every processed click with a **legal leg**
  over our own mesh — five scored runs (ROUTER.md §§6–10), the no-clip dead under it
  (§1z), warps ~1.5× fewer than the refusal regime (HANDOFF §B). `--no-router` restores
  the pre-1z-v click path byte-for-byte (the gate, the `geo-stale` refusals, the
  hold/void/rate tower); `--router` still parses as a no-op so every runsheet written
  before today keeps its meaning; the nine pairwise refusals (`--click-sweep`,
  `--arrival-carry`, `--cancel-answer`, `--stop-answer`, `--family-rate-probe`,
  `--checksum-probe`, `--pc-spoof`, `--interact-walk`, `--move-speed-effects`) now
  carry the `--zero-lead` precedent's hint — *pass `--no-router` to run this arm* —
  only when the router was not asked for explicitly, so the advice is followable.
- **(a) `ROUTER_LEG_REARM` (`--router-raw-leg` reverts).** The 0x003E arm arms the
  click-leg record (ANIMREF-RE §37, `_click_leg_arm`) on the **raw click chord before the
  router runs** — its order of operations — while the body walks the **routed** leg.
  Every reader of the record then models a straight line the client is not walking:
  PRESS ENDS THE WALK's `0x002C` at the modelled body (ANIMREF-RE §39), the approach's
  snap guard, the swing gate's ETA. The press is the dangerous one: a `0x002C` lands
  **both** copies on its point, so a mid-chain press would hard-set the body onto the
  unclipped chord the router exists to keep off the wire — §1z-u.2 lens 3's warning,
  *"every router run predates `PRESS_SUPERSEDES_LEG` … and had zero attack presses"*:
  the composition had never been exercised. Now the router re-aims the record at the
  leg it grants (first leg, or the clip-fallback's stop; a verbatim answer's leg *is* the
  chord and is left alone), and **every chain leg re-arms it again from the waypoint the
  body reached, at its own grant instant** — the record gains a `start` and keeps the
  click's stamp `t0` as its identity, which is what `_player_body_moving` and the
  approach's own check read. `test_router` §5 drives the known-bad arm: without (a) a
  mid-chain press re-pins at the chord's (144, 0); with it, on the routed leg.
- **(b) `ROUTER_SYNC_PLANE` (`--router-report-plane` reverts).** The one-leg verbatim
  answer's field 4 is the SYNC copy's plane word (`agent+0x80`; `0x0029` is sync-only,
  §1z-t.2). It was `state["plane"]`, the last accepted report's plane — frozen for the
  whole click walk because the client reports nothing while click-walking, while the
  walk crosses seams; §1z-u.2 lens 2 measured the cost on K2's own bin (16 of 18 SYNC
  stamps 0 while 5 of 8 echoed legs crossed non-zero planes) and corpus-wide (709
  incoherent stamps in 36 of 116 click sessions, 0 on map 146), and §1z-i is why it
  matters: a from-plane the ground does not offer is `pathCount == 0`, exceptionless.
  The derived word, as §1z-u.2 wrote it: **the mesh's plane under the MODELLED sync
  copy** — `_sync_position`'s lerp of the last granted leg at 288 u/s (the same equation
  the validated mirror runs, §1z-r) — via `plane_at(prefer=report plane)`, so the wire is
  unchanged wherever the mesh offers the report's plane there, the mesh's single plane
  where it does not, and the report's plane where the mesh cannot say or the model is
  unseeded (refuse to guess). The routed / chain / fallback sites keep their matched
  pairs — `a2_matched_field4`'s RULE block and §1z-o.6's counterexample stand.
- **The press and the follow now abandon a live chain** (`router_leg` rows,
  `cause=press` / `cause=approach`). ROUTER-Q8 left interaction/cast/attack opcodes
  out of the abandon set "in v1" because retail's corpus never fired them mid-chain
  (zero exposure). It is decided for these two by **our own** press contract rather
  than by retail's wire: `_press_supersedes` sends a `0x002C` and the tick swings or
  sends a `0x002A` follow within the same tick, and a chain that kept granting its
  remaining `0x0029` legs at cadence behind that would be two movement orders for one
  body — exactly the two-sender fight `--interact-walk`'s refusal names. Casts are still
  Q8's remainder.
- **Readout.** A routed click writes **no `click_verdict` row** — `router_route` rows
  carry the verdict (verbatim / routed / clip-fallback / refused / kbd-drop, reason, ms),
  verbatim rows now carry `plane4` beside `plane4_report`, and `router_leg` rows carry
  every grant and abandon with its cause. A scorer that counts `click_verdict` rows
  reads zero on a default session; `keepalivelog.py` already reads the router rows.
  The startup banner prints `ROUTER ON by default` with the two conditions' state and
  warns when a condition or the router is off — say so when reporting a run.

### 1z-v.2 The retrodiction — the operator's 40 refused clicks, replayed through the shipped router

**Registered before running:** 40 of 40 answered `verbatim` (§1z-u.2 measured
`route()` one leg for 40/40 on these clicks), 0 refused, 0 `kbd-drop`; (a) and (b) with
**zero exposure** on this capture (open ground, map 146, plane 0 everywhere). Harness:
`studies/movecode/review/clickretro.py` — drives `authsrv.router_answer_click` as it
ships, on the map-146 mesh from the owner's own archive, from the router's **own origin
model** (the integrator walking the last granted leg at 288 u/s, reset by each accepted
report — ROUTER-B1's origin result), with the keyboard latch armed by the capture's five
`0x003D`s exactly as the 0x003D arm arms it.

| capture `authsrv-20260903T084616-c1` | shipped then | router now |
|---|---|---|
| clicks | 40 | 40 |
| answered | **0** (40 × `geo-stale`) | **40** (40 × `verbatim`, n_wp 1) |
| refused / dropped / clip-fallback | 40 / 0 / 0 | 0 / 0 / 0 |
| origin → click distance | — | 25–385 u |
| (a) multi-leg or fallback answers; presses inside a live chain | — | 0; 0 of 28 |
| (b) verbatim rows where field 4 ≠ the report's plane | — | 0 of 40 |

**Held.** The keyboard drop did not fire: the five `0x003D`s at 23.56–24.16 s armed the
latch and no `0x0047` ever cleared it (ANIMREF §41's cell), but the next click came at
27.99 s — 3.8 s later, past `GRANT_LOCAL_WINDOW`'s 3.0 s — so retail's contract dropped
nothing here. Under a stuck latch a click inside 3.0 s of the last report IS dropped;
that is retail's measured behaviour (§0.15), bounded by the window, and it is why §41's
latch fix matters to the click path too.

**What the retrodiction does not show, said plainly.** It is a verdict census, not a
separation counterfactual. The separation counterfactual for this session already
exists — §1z-u.2 lens 1's K2 sim, whose echoes are wire-identical to the router's
verbatim one-leg answers (same point, same words on this map): drag-phase p50 23 → 36–57 u,
p90 138 → 98 u, a wash inside the 100 u tube. This session's tail was the keyboard
lead's (§1z-u.3), now opt-in. The router's value on this map is the one §1i priced —
grant density 1.40 per 1,000 u against retail's 4.30 median and 1.70 minimum, the sync
copy never left standing at the last grant while the body walks away — and its value
elsewhere is the dead no-clip and the halved warps, both measured on map 280.

### 1z-v.3 What this does not settle

- **The origin's plane.** `route(start_plane=…)` and the clip-fallback's `_router_plane`
  carry still read `state["plane"]`, the frozen report plane, for the **body** model's
  surface. The derived word is the same construction over `state["pos"]`; it is scoped
  out of (b) because (b) names the SYNC copy and the preference falls back rather than
  refusing on an unmatched plane. Filed, not built.
- **§1z-o.6 stands.** The routed / chain / fallback field 4 still matches field 3
  unconditionally, with its one measured counterexample (R7: 0 over a true 37).
- **Casts do not abandon a chain** (ROUTER-Q8's remainder); `--cast-stop=pin`'s own
  click-walk suppression still fires on every mid-chain cast, conservatively.
- **The re-armed record's error terms are §37's, now per leg**: a body stopped by the
  client's own collision short of a waypoint is modelled at the waypoint; a bent client
  path ends later than our straight leg. ROUTER-Q9's µs dest race is unchanged.
- **The operator's next ordinary session scores this at zero cost.** Expect
  `ROUTER click to (x, y): … ROUTER one leg` where `geo-stale` used to be, and
  `router_route` rows in the capture; the felt questions are RUN-FEEL's four, with the
  keyboard lead off. Separation via `agenttap.py` and `w0score.py`; the enslavement
  caveat of §1z-u.3 does not arise on a verbatim one-leg answer (the granted point is
  the client's own click, which the body was walking to anyway), and does arise on a
  multi-leg chain, whose legs are orders.

### 1z-v.4 Tests and provenance

`test_router.py` 103 checks (floor 73 → 103; §5 is new), `test_playerswing.py` 116
(one source lock updated for the press arm's `rec=rec`), `test_d1lead.py` 94 (its
call-site censuses unchanged: `a2_matched_field4` 10, family-edge 7,
`a2_click_answered_at` 4), `test_grantsim.py` 86, `test_policyreplay.py` 14,
`test_kbdsync.py` 33, `test_familyrate.py` 26, `test_cancelwalk.py` 124,
`test_position_trust.py` 235, `test_planerepair.py` 41, `test_clickecho.py` 25,
`test_srclint.py` 26 — all green. The retrodiction is a measurement over the owner's
own capture via a harness in this repo; the mesh is read from the owner's own archive
at run time; no new static reads, no client launch, no upstream derivation.

---

## 1z-w. The routing origin's plane word, and a cast ends the route — §1z-v.3's two filed items, built

**Asked:** "do the first two, origin plane word and cast abandon." Zero client runs; the
affected suite green; the 08:46 retrodiction re-run with a new census column. Ident
`MOVECODE-1z-w`.

### 1z-w.1 The origin's plane word (`ROUTER_ORIGIN_PLANE`; reverted WITH (b) by `--router-report-plane`)

- **What it is.** After the origin snap, the router's carry becomes the mesh's plane
  under the **body model** — `_router_plane(pm, origin, report_plane)`: the report's
  plane where the mesh offers it there, the mesh's single plane where it does not, the
  report's plane where the mesh cannot say. It feeds `route()`'s start preference, the
  clip-fallback's stop-plane carry, the matched flag, and every `router_route` row
  (`plane_origin` beside `plane_report`). §1z-v condition (b) is the same construction
  over the sync copy; this is it over the body — one construction in two places, so
  **one revert**: a run that convicts the construction convicts both.
- **Its exact exposure, derived before it was built.** `route()` is **provably
  unchanged** by it: `start_plane` is a preference that falls back to every candidate
  when unmatched, and the derived word differs from the report's only when the mesh
  offers a single plane the report is not on — the case in which `route()` already
  took that single trapezoid. The **one wire effect** is the clip-fallback's field 3/4
  when its stop lands on **stacked** ground reached from single-plane ground: the stop
  now carries the origin's deck instead of the frozen report's. `test_router` §6
  drives that cell both ways (5 matched under the default; 3 under the known-bad arm,
  which also tells `route()` 3).
- **The census it enables is the real yield.** Every router row now measures the
  frozen-report staleness at the routing origin. The plane census (§1z-n) bounds it
  from below — 2.34% of on-mesh reports disagree with the mesh at REPORT time (0.54%
  for a declared 0, 12.91% for a declared non-zero) — but the origin during a click
  walk is a report frozen for the walk's whole length while the walk crosses seams,
  and that term has never been measured. The operator's next default session on a
  seam-rich map measures it for free.

### 1z-w.2 A cast that begins ends the route

- **What it is.** `handle_skill_press`, at the begin instant (`not queued`), attack and
  non-attack alike: `router_abandon(state, rec, "cast", now)`; the skill-press arm now
  hands the recorder over so the row is written. Reasoning as for the press and the
  follow (§1z-v.1): the body stops to cast — or an attack skill's chase re-orders it —
  and a chain still granting its remaining `0x0029` legs at cadence behind that is two
  movement orders for one body. ROUTER-Q8 is now decided for three opcodes (press,
  follow, cast); the interact arm stays refused outright (`--interact-walk`).
- **What it deliberately does not do, and the derived next step.** The cast-stop pin
  keeps its click-walk suppression (B1 of the 2026-08-25 CANCELWALK review). That
  clause's stated justification — *"no belief can place the body"* — is **false under
  a chain since §1z-v (a)**: `_click_leg_start(silent=True)` places the body on the
  re-armed routed leg, the same model PRESS ENDS THE WALK already pins at. So the
  derived behaviour for a cast during a click walk is the press's own: a `0x002C` at
  the modelled body, then the halt. That changes a ruled arm (CANCELWALK §8.3g "pin
  it", with B1 as a reviewed blocker), so it is filed with this reasoning rather than
  built under a scope named "abandon". With abandon alone a cast mid-chain leaves the
  sync copy parking at the current waypoint while the body stands casting — a
  separation of at most one leg, evaluated at the next grant or report — which is
  strictly less than before, when the chain kept walking the copy.

### 1z-w.3 Retrodiction, tests, provenance

`studies/movecode/review/clickretro.py` gained the (b′) column. The 08:46 capture:
40 clicks → 40 `verbatim`; **origin plane ≠ report plane on 0 of 40** (map 146,
plane 0 everywhere), and the capture holds no skill press at all and no chain ever formed, so no cast met one — **zero exposure
for both items here**, said as such. Their exposure is map 280's seams and multi-leg
clicks with a cast in flight.

`test_router.py` 114 checks (floor 103 → 114; §6 is new), `test_cancelwalk.py` 124,
`test_castcancel.py` 31, `test_castcycle.py` 35, `test_guards.py` 41,
`test_pools.py` 127, `test_playerswing.py` 116, `test_d1lead.py` 94,
`test_cmsgnames.py` 16, `test_planerepair.py` 41, `test_position_trust.py` 235,
`test_kbdsync.py` 33, `test_familyrate.py` 26, `test_clickecho.py` 25,
`test_grantsim.py` 86, `test_policyreplay.py` 14, `test_srclint.py` 26 — all green.
Measurements over the owner's own capture via the harness in this repo; the mesh from
the owner's own archive at run time; no new static reads, no client launch.

---

## 1z-x. THE ENSLAVEMENT DETECTOR — §1z-u.5 item (c) built into `w0score.py`, and RUN-1zT re-scored by it

**Asked:** "do the enslavement detector next." Zero client runs. Built at a desk over the
four taps already in the vault; the detector's two controls were fixed before it was
written and it passes both. Ident `MOVECODE-1z-x`.

### 1z-x.1 The question, and the signal that answers it

§1z-u.3: *world-0 vs the drawn body cannot distinguish "world-0 follows the body" from
"the body follows world-0."* Once the client's AgTrack fence is shut, every `0x0029` we
send is walked as an order (REALFIX §0.10/0.11/0.17), the drawn body's walk target
becomes **our granted point to the unit**, and the two copies agree because the body is
enslaved — the p50 0.0 of RUN-1zT's registered arm. The number is a measurement; the
confirmation needs a second witness.

The witness is the ASYNC copy's own walk target, `+0x9C`, which `agenttap.py` already
records as `tx, ty`. `w0score.py` now joins each tap to the gamesrv capture that
produced it (the newest `authsrv-*-c1.jsonl` whose wall span overlaps; `--grants`
overrides) and classifies every player `0x0029` by the client's **own** last click and
last report before it — the point decoded from the row's plaintext bytes, never the
label's rounded text:

| kind | the granted point is | following it is |
|---|---|---|
| `own-click` | the client's last `0x003E` point, to 1 u | the client's own choice, not enslavement |
| `at-report` | within 50 u of its last `0x003D`/`0x0047` | a zero-lead grant at the body, not enslavement |
| `server-chosen` | anything else — a keyboard lead, a routed waypoint | **enslavement**, when the body's target equals it |

A moving sample is ENSLAVED when its target equals, to `GRANT_EPS = 1.0` u, a
server-chosen grant sent at or before it (50 ms of slack for the two recorders' write
order; on RUN-1zT the matched samples agree to **0.00 u**, 115 of 115). The onset is the
first **sustained** run of three enslaved moving samples — RUN-1zT carries one matched
sample at 8.00 s, the first lead firing at the walk's start, and that blip is not the
onset. Capture-level: ENSLAVED at ≥ 25% of moving samples, FREE at zero, MIXED between;
per harness leg (`--legs`): ENSLAVED at ≥ 50% of the leg's moving samples, plus a
**HELD KEY, BODY PARKED** flag when a key held ≥ 1 s moved the body under 50 u — the
other face of the same symptom. The scorer prints all of it beside THE NUMBER, and a
contaminated capture gets **MEASURED, CONTAMINATED** (exit 3) instead of CONFIRMED; a
tap with no gamesrv capture to join gets **MEASURED, NOT CONFIRMED** (exit 3), never a
silent pass.

### 1z-x.2 The four taps, re-scored — the detector reads what the record said

| capture | regime | server-chosen grants | enslaved moving samples | onset (tap clock) | verdict |
|---|---|---|---|---|---|
| `agenttap-20260903T073122` (RUN-1zT, registered arm) | scripted keyboard, lead ON | 8 of 13 | **115 of 193 (59.6%)** | **17.77 s** | **ENSLAVED** |
| `agenttap-20260902T213401` (the baseline) | scripted keyboard, zero-lead | 0 of 10 | 0 of 130 | — | FREE |
| `agenttap-20260903T084632` (RUN-FEEL) | mouse, lead ON | 2 of 2 | 0 of 94 | — | FREE |
| `agenttap-20260903T072932` (first attempt) | scripted + operator input, lead ON | 54 of 63 | 19 of 516 (3.7%) | 6.18 s | MIXED |

**RUN-1zT per leg** (with `--legs`): opening W 868 u, 2.3% (the 8.00 s blip); S 743 u,
25.0% (the onset lies inside it); **third W: 2.9 u in a 5.0 s hold — HELD KEY, BODY
PARKED**; Q 509 u / E 513 u / S 504 u at **100%** each against free-walk expectations of
648 / 648 / 760 u (the body travels the granted leg, not the hold); the closing W: 0 u in
4.0 s, parked again. That is §1z-u.3's claim as a table — the five later targets equal
our dests to the unit and the per-leg travel is ~510 u whatever the hold — with the
parked W legs, which the record had only as "one release in seven produced a `0x0047`".

**The baseline's zero is not vacuous**: its ten grants are all `at-report` (zero-lead),
so the body's target could not have equalled a server-chosen point; the detector's
positive control is RUN-1zT and its negative control is this capture, and `--baseline`
now asserts both beside the scorer's own p50 237 / max 516 reproduction.

**RUN-FEEL reads FREE, which is correct and worth saying.** Its two leads were
server-chosen and the drawn body followed neither — it walked its own north-west heading
((9553.5, 8705.1), the tap's most frequent target) and was **snapped**, not walked, onto
the sync copy, exactly as §1z-u.3 and §41.2 corrected. The fence shut after that snap,
but no later `0x0029` arrived for the body to follow (the session's remaining grants were
`0x002C` re-pins), so the detector has nothing to flag. Enslavement is "follows an
order"; a shut fence with no order is invisible to it, and the parked-key flag is the
instrument for that regime when a runsheet supplies legs.

### 1z-x.3 A clock correction to the record

§1z-u.3 and RUN-1zT.md date the arrival snap **18.65 s**. On the tap's clock it is
**17.69 s**: the body lands on the 14.7 s lead's endpoint (10001.1, 8430.3) with v = 0 and
an infinite target, and from 17.77 s its target is the 17.7 s lead (9481.1, 8430.3). The
two figures are the same instant on two recorders — the gamesrv recorder's `t` starts
~1.0 s before the tap's `head.t0` (07:31:21 vs 07:31:22). Neither is wrong; a reader
joining the two files must say which axis a stamp is on. `w0score.py`'s constant carries
the tap-clock value with this note.

### 1z-x.4 What this settles and what it does not

- **RUN-1zT's confirmation is withdrawn by its own scorer**, as §1z-u.3 said it must be:
  `w0score.py` on that capture now prints MEASURED, CONTAMINATED. §1z-t's *mechanism*
  (the law, the cause, term 2's `[190, 216, 288]`) stands; the lead term stays opt-in.
- **Any future lead run is scored with this in place** — §1z-u.5 (c) is done. The
  remaining gates before the lead returns are (a) hold-not-drop and kill-on-press, (b)
  `a2_matched_field4` on the keyboard path, (d) the fence-shutter audit.
- **The detector sees orders, not fences.** A body that was snapped and then parked with
  the fence shut but received no further grant reads FREE. The parked-key flag catches the
  keyboard face of that regime given a runsheet; the mouse face has no leg stamps and is
  filed.
- **A routed multi-leg click chain will read as enslavement by construction**: interior
  waypoints are server-chosen and the body follows them as orders — that is the router's
  design and retail's. On a click session under the router default, read the per-sample
  fraction against the chain rows before calling it contamination; the one-leg verbatim
  answer is `own-click` and reads FREE.

### 1z-x.5 Tests and provenance

`test_w0score.py` — new, 38 checks with the vault (floor 35 from the vault-less run;
section 5 skips and lowers nothing): the classification, the join's causality and band,
the onset rule, the three bars, the per-leg table and the parked flag, the plumbing, and
the two real controls. `test_srclint.py` green. All figures are measurements over the
owner's own captures via extractors in this repo; no client launch, no static reads, no
upstream derivation.

---

## 1z-y. HOLD, NOT DROP — and the lead KILLED on a press or a click: §1z-u.5 item (a) built, with one derived correction to its text

**Asked:** "do the hold-not-drop and kill-on-press next." Zero client runs; the two gates
§1z-u.5 (a) named before the keyboard lead may return, built additive and ON, each with
its revert, each driven through the shipped heading arm's own bytes in `test_kbdsync`.
Ident `MOVECODE-1z-y`.

### 1z-y.1 (a1) A rate-refused heading grant is HELD and re-baked at the floor

`_heading_grant_ok`'s docstring dropped a rate-refused heading report on a premise —
*"the next report carries a fresher position"* (median 0.28–0.30 s) — and §1z-u.3 is the
premise failing: the re-aim 66 ms after the 24.09 s lead was refused `heading-rate`,
no `0x003D` followed for 2.7 s / 567 u, the lead matured on the old heading, and the
arrival reconcile snapped the body 498 u and shut the fence. Now the refused report's
**own** grant — the point or the lead the arm had already computed above its verdict
row, with the plane words as computed — is stored (`heading_hold_note`) and
`heading_hold_tick`, polled at the three sites `grant_flush_tick` is, sends it the
instant the shared floor opens: the family row (edge-triggered, a no-op when unchanged)
then the `0x0029`, with the arm's own post-send bookkeeping. **Newest wins, never a
queue**: every refused report overwrites, every fired one clears, the stop arm and the
click arm clear, a body that has stopped drops it, R11's action hold suppresses it, and
a hold older than the click hold's own expiry (`HEADING_HOLD_MAX_AGE` =
`GRANT_PENDING_MAX_AGE`, the equality pinned) is dropped — each with a
`grant_verdict` row (`deferred-heading` on a fire; `heading-hold-expired` /
`-stopped` / `-action-hold` otherwise), a reason vocabulary disjoint from the arm's
own so grantsim's replay filter is untouched.

**This is live under the shipped zero-lead default, not only under `--kbd-lead`.**
Under zero-lead the held point is the report itself, so the sync copy gets the freshest
anchor at the floor instead of waiting out a silent interval — §1z-t.3's law is
separation = report_gap × speed, and a dropped report doubles the gap. Under the lead
it is the re-aimed lead, which is what keeps the copy from maturing on a heading the
body left. Not under `--d1-lead` (that bundle has its own containment and `test_d1lead`
pins its one leg-arm site) and not under the CANCELWALK lead arms or the PC spoof
(pre-registered diagnostic wires). `--no-kbd-hold` reverts.

### 1z-y.2 (a2) A press or a click kills an in-flight keyboard lead — with a grant, not a 0x002C

A fired keyboard lead now arms `state["kbd_leg"]` (the D1 leg record's shape, own key,
own rows, popped by either report arm). On a `0x0026` press or a `0x003E` click while
that leg is in flight, `_kbd_lead_kill` sends a **zero-lead grant at the modelled
body** — `a2_leg_position`: report + heading × elapsed at the family speed, clamped at
the lead — with the body's own plane in both words, so the sync copy re-aims to where
the body is and the lead's 520 u arrival never fires. A lead that has already matured
is not re-granted (its arrival has already been evaluated); the row says `matured`.
`--no-kbd-lead-kill` reverts; inert without `--kbd-lead`.

**The correction to §1z-u.5's text, derived from the mirror.** The item said *"killed by
the zero-distance re-pin … what PRESS ENDS THE WALK already does"* — a `0x002C`. The
mirror's own transcription (`agtrack_mirror.on_update_position`) is why that is the
wrong primitive here: a `0x002C` runs `AgTrack::Clear` first, and `clear()` sets
`client_controlled = False` — **the fence closes** — until the client's next movement
command re-arms it. Every grant between a `0x002C` kill and that command would be an
ORDER, which is the enslavement the kill exists to prevent (and the reason §1z-u.5 (d)
asks for the two `0x002C` senders to be audited). A `0x0029` on the body's own trail is
the reprieve test's MATCH — zero-lead's warp-safety by construction (§1z-r) — so the
copy arrives beside the body and the fence stays open. `test_kbdsync` locks the kill's
source to `AGENT_MOVE_TO_POINT` and against `AGENT_UPDATE_POSITION`.

The click case is worth stating: under the router a click's own answer supersedes the
copy's leg anyway, but a click inside the 3.0 s keyboard-authority window is dropped by
retail's contract and a refused click sends nothing — exactly when the lead would
mature. The kill runs before the router answers.

### 1z-y.3 Tests, and what this does not settle

`test_kbdsync.py` 33 → 60 checks (floor 60): the hold stored with the lead its own
heading names and the words as computed; kept inside the floor; fired at the floor
with the row, the leg record and the plane slot; newest-wins; a fired report clears;
zero-lead holds the report; expiry, stopped body and R11 each drop with their row; the
known-bad arm drops and sends nothing (the 08:46 shape); the kill at 1.0 s into a 520 u
lead grants (1288.5, 2000.25) with 232 u unwalked, consumes the record and rows it; a
matured lead is not re-granted; no leg, no send; the known-bad arm arms no record and
leaves an armed one alone; the kill is a grant and not a `0x002C`; and six source
locks (the two call sites, the three poll sites, the hold's position inside the arm,
the leg's arm and pops, the stop arm's clear). `test_d1lead` 94 (its one-arm-site and
one-guarded-send censuses hold — the flush spells R11's guard differently for that
reason), `test_position_trust` 235, `test_router` 114, `test_playerswing` 116,
`test_cancelwalk` 124, `test_familyrate` 26, `test_clickecho` 25, `test_planerepair`
41, `test_grantsim` 86, `test_castcancel` 31, `test_guards` 41 — green.

Not settled: the lead stays **opt-in**. Item (a) is built; (b) `a2_matched_field4` on
the keyboard path and (d) the fence-shutter audit are still owed, and the lead's length
is to be argued on maturation margin (§1z-u.4). The hold's live effect under zero-lead
is a prediction, not a measurement: the operator's next keyboard session scores it for
free (`HELD HEADING` lines and `deferred-heading` rows where a re-aim used to vanish).
No client launch, no static reads, no upstream derivation.

---

## 1z-z. The matched plane word on the keyboard lead grant — §1z-u.5 item (b), built; the stop echo was already matched by construction

**Asked:** "do the matched plane word on the keyboard path next." Zero client runs; one
constant, one call, one flag, nine checks through the shipped arm's own bytes. Ident
`MOVECODE-1z-z`.

### 1z-z.1 What was wrong, and what shipped

§1z-t left the keyboard lead branch's plane words untouched *"to change one
variable"*, and §1z-u.4 measured the cost: `pc_matched` False on all 14 fired KBD rows,
and 073121's 12.358 s lead carrying **dest 29 / cur 0** — a sync copy sent 520 u across
a seam stamped with the plane it left, which is the stale-stamped copy stage 1 of the
input lock needs (REALFIX §0.11: *"plane-carry's one-grant lag leaves the SYNC copy
stamped with the OLD plane across a seam … a same-direction crossing re-report fires a
full lead with pd ≠ pc, and within ~80 ms the client's plane-mismatch reconcile snaps the
drawn body onto the sync copy and clears clientControlled: fence shut"*). §0.11's
armer-kill (e2) was built for D1 only: *"under `--d1-lead`, field 4 always MATCHES field
3 — on grants AND on the stop-repin."*

**Built:** `KBD_SYNC_MATCHED` (`--no-kbd-matched-plane` reverts; `--legacy-kbd-sync`
clears it with the rest). Inside the KBD lead branch, before the lead point and after
the carry — the D1 branch's own order — `a2_matched_field4(plane, zl_plane_cur)`
overrides the carried word to the report's plane and the row's `pc_matched` records
where it changed the wire. A refused crossing re-aim is held with the matched word (§1z-y
composes: the hold stores `zl_plane_cur` after the match). **The KBD stop echo needed
nothing**: it sends the report's plane in both words — a zero-distance echo has one plane
— matched by construction, and the send's own comment says so; the test pins it.

### 1z-z.2 Scope, stated as a pin

The item names the **KBD lead grant**. The shipped zero-lead default still sends
`--plane-carry`'s one-grant lag at a crossing (dest 29 / cur 0), and `test_kbdsync` §12
pins that **unchanged**: F1 is an owner-ruled arm, §0.11's control era shows the
zero-lead crossing snap *recovering* on the next press (3/3 fence re-arm cycles — the lock
needs the lead's click-walk regime composed with the snap, and zero-lead has no such
regime), and the plane repair stands behind it. Whether the default should match too is a
question about F1, filed, not decided here.

Two recorded facts sit either side of this word and neither moved: retail's nonzero
pairs are bit-identical 222/222 (REALFIX §0.9), and its half-zero pairs show the one-grant
lag (79.7% of 306 crossings) — ROUTER-Q7's deviation, now also the keyboard lead's; and
§1z-o.6's counterexample (matching to a dest plane the copy's point cannot resolve, gate 2
firing) is the helper's own open question and applies to this caller exactly as to the
router's. `a2_matched_field4` now has ten call sites and its def; `test_d1lead`'s census
names the tenth.

### 1z-z.3 Tests, and what remains before the lead returns

`test_kbdsync.py` 60 → 69 (floor 69): ON with its flag; a crossing lead goes out
dest 29 / cur 29 with `pc_matched` TRUE; the known-bad arm sends dest 29 / cur 0 (the
073121 shape); a same-plane lead records no override; the held re-aim carries the matched
word; the zero-lead default's lag pinned unchanged; the stop echo's words; the match's
position inside the branch. `test_d1lead` 94 (its call-site census updated to ten),
`test_router` 114, `test_position_trust` 235, `test_playerswing` 116, `test_cancelwalk`
124, `test_familyrate` 26, `test_clickecho` 25, `test_planerepair` 41, `test_grantsim`
86, `test_srclint` 26 — green.

Of §1z-u.5's list, (a) and (b) and (c) are built; **(d) remains** — the audit of the
two `0x002C` senders (`AGTRACK RE-PIN`, `PRESS ENDS THE WALK`) as fence-shutters, which
§1z-y made more pointed (a `0x002C`'s Clear closes the fence until the next movement
command) — and the lead's length is still to be argued on maturation margin (§1z-u.4).
The lead stays opt-in until then. No client launch, no static reads, no upstream
derivation.

---

## 1z-aa. THE FENCE-SHUTTER AUDIT — every server 0x002C shuts the fence, the fence re-arms only at a keyboard walk-start, and a lead must never be sent into the window: §1z-u.5 item (d), measured and built

**Asked:** "do the fence-shutter audit next" — the last of §1z-u.5's four gates before the
keyboard lead may return. Zero client runs: the audit is a join over captures already in
the vault, and its derived action is one gate with one flag and fifteen checks. Ident
`MOVECODE-1z-aa`.

### 1z-aa.1 The instrument, and what the corpus holds

`movetap`'s `fence_state` is AgTrack's own per-agent `clientControlled` dword, read at
the record (`S_CONTROLLED`, the operand of `cmp dword [rec], 0` at 0x00606002). The
`agenttap` rows' `controlled` field is the controlled agent's *id*, not the flag, so the
09-03 taps cannot see the fence; the 60 movetap tapes (08-19 → 08-26) can. Server
`0x002C`s in the 213 gamesrv captures, by sender: `AGTRACK RE-PIN` 32 (9 sessions,
08-30 onward), `PRESS ENDS THE WALK` 14 (2 sessions, 09-02 onward), `RESYNC` 24,
`CAST-STOP PIN` 7, `APPROACH RE-PIN` 1. **No movetap tape overlaps the two senders the
item named** — they shipped after the last tape — so their fence effect is read off the
handler they share with the two senders that WERE taped: three tapes, twelve specimens
(`CAST-STOP PIN` ×6 on 08-25 13:09 and 14:05, `RESYNC` ×6 on 08-25 17:42).

### 1z-aa.2 The measurement (OBSERVED)

| | |
|---|---|
| fence shut at the next sample after a server `0x002C` | **12 of 12** (one specimen shows one open sample of delivery latency first) |
| re-armed at the `0x002C` itself | 0 of 12 |
| re-armed at a `0x0047` stop inside the window | **0 of 4** |
| re-armed at a moving `0x003D` after a park (a keyboard walk-start) | **7 of 8** |
| shut span, where a re-arm was seen | 1.9 – 5.8 s (the operator's next key press) |
| shut span, no command in the window | > 6 s, two cast-stop pins |
| body travel inside the shut window | 0.0 u in 11 of 12 (parked bodies) |
| zero-lead grants inside the shut window | 1–2 per window, at the re-arming report, no visible effect on a parked body |

The one specimen that moved the body — a cast-stop pin at 14:05 landing 523 u from it
at 6,458 u/s — is the pin's own placement onto a stale reckon (CANCELWALK-F34/F35's
class), not the fence's doing; noted, not this audit's.

So the transcription's Clear is right (`agtrack_mirror.on_update_position` →
`clear()` → `client_controlled = False`) and its **re-arm rule is corrected by the
tape**: the fence re-opens at the keyboard walk-start applier — REALFIX §0.11's *"the
only fence re-armer"* — and not at a stop. `agtrack_guard.on_report` re-arms both
mirrors on a `0x0047` too (*"Both kinds re-arm the record"*), which the tape refutes 0/4;
`on_click`'s re-arm is unmeasured (no click fell in a window). **CONTESTED, recorded, not
changed**: the replay validation (§1z-r) rests on the mirror as transcribed, and the
error's direction is the conservative one — after a stop the mirror predicts a test that
the client does not run.

**What the tape cannot say.** Every taped `0x002C` landed on a parked body. Whether a
held key keeps driving the body while the fence is shut has zero exposure here; the
behavioural evidence is RUN-1zT's enslaved legs (§1z-x: a held Q/E/S moved the body the
granted leg and parked; two held W legs moved it 2.9 u and 0 u), read with §0.11 stage 2.

### 1z-aa.3 What follows for the six senders, and the gate built

While the fence is shut every `0x0029` is an order. A zero-lead grant is an order to the
body's own reported point — the tape shows them landing on parked bodies without effect,
and under a held key the cost is bounded by the report chord. A **lead** into the window
is §0.11 stage 2 verbatim: the body walks it as a click-order, releases go unreported,
the walk-start applier never runs, the fence never re-opens — the 08:46 lock. So all six
senders compose with a lead into the lock by construction, and `AGTRACK RE-PIN` worst of
all: it fires from the report arm *above* the lead site, so the lead of the very report
that carried it lands in the window it just opened. §1z-s's *"re-pin-then-grant is safe
by construction because the fence closes"* is true of snapping and false of enslavement;
the two are different hazards.

**Built:** `KBD_LEAD_FENCE_GATE` (`--no-kbd-lead-fence-gate` reverts; `--legacy-kbd-sync`
clears it). The server tracks the fence it shut — `fence_shut_at`, stamped in the send
choke at every player `0x002C` whatever sender labelled it, cleared in one place: the
`0x003D` arm, on a moving report that arrived with the keyboard latch clear (the tape's
walk-start), with a `fence` row naming how long it was shut. Not cleared by a stop (0/4)
and not by a click (unmeasured, so conservative). A keyboard or D1 lead computed while it
is set degrades to the zero-lead point, `lead_src=fallback`, `lead_clip_why=fence-shut`;
the held re-aim (§1z-y) inherits the degraded point; no leg record is armed. Under the
shipped default (lead off) the gate is inert; it exists so the lead cannot return without
it. The 1z-y kill was already a grant rather than a `0x002C` for this exact reason.

### 1z-aa.4 Tests, and where the keyboard lead now stands

`test_kbdsync.py` 69 → 84 (floor 84): the tracker stamped by a player `0x002C` and by
nothing else; a mid-walk lead degrades with the row saying `fence-shut` and arms no
record; a walk-start report re-arms with its row and the lead of that report fires; the
hold stores the degraded point; the D1 lead degrades the same way; the known-bad arm
sends the 520 u lead into the shut fence; and four source locks (stamped in the choke
once, cleared in one place, the stop arm does not touch it, both branches pass the gate).
`test_d1lead` 94, `test_position_trust` 235, `test_router` 114, `test_playerswing` 116,
`test_cancelwalk` 124, `test_familyrate` 26, `test_clickecho` 25, `test_planerepair` 41,
`test_grantsim` 86, `test_agtrack_mirror` 64, `test_agtrack_guard` 49 — green.

**All four of §1z-u.5's gates are built** — (a) the held re-aim and the kill (§1z-y),
(b) the matched word (§1z-z), (c) the enslavement detector (§1z-x), (d) this gate. What
remains before `--kbd-lead` becomes the default is not a gate but an argument and a run:
the lead's length on maturation margin (§1z-u.4: 766 leaves ~250 u over the ~515 u report
chord where 520 leaves 5), and one scripted keyboard run under `--kbd-lead` scored by
`w0score.py` with the detector — which now cannot read an enslaved body as a
confirmation. No client launch, no static reads, no upstream derivation; all figures over
the owner's own captures via extractors in this repo.


---

## 1z-ab. THE LEAD'S LENGTH — the maturation-margin question is void under the hold, the operative bounds are the trigger below and the order-walk above, and 520 stands

**Asked:** "do the lead length argument next" — §1z-u.4's deferred question, the last item
before `--kbd-lead` can be argued for as a default: 520 u (§1z-t.6, the report chord + 5)
or retail's 766 u (the client's own proposal), "on maturation margin — 766 leaves ~250 u
over the ~515 u report chord where 520 leaves 5". Zero client runs; three extractors over
the owner's own captures, in one module (`toolkit/clientscan/leadmargin.py`, with
`test_leadmargin.py`), and the decode already in `agtrack_mirror.py`. Ident
`MOVECODE-1z-ab`. **The constant does not move.**

### 1z-ab.1 What the two numbers are (OBSERVED)

- **766 is the client's own proposal, and it is a fixed ray.** `|vec2|` on every decoded
  `0x003D` is 765.0–768.0 u on all eight movement types (8,442 forward reports p50 766.79;
  4,047 backpedal p50 767.39; side 766.98–767.18) — not a time at a speed but ~768 u =
  **1.5 × the 512 u trigger**. Retail grants that (clipped on 40%, REALFIX §3.2), so
  retail's copy carries a 256 u (0.89 s at cruise) margin over its next report.
- **The trigger.** 1,126 of the 1,160 same-heading cruise chords at or over 505 u (≥ 1 s
  apart, ≤ 320 u/s so warps are excluded — a 6,182 u "chord" in 21.8 s is a teleport) lie
  in [505, 518); the excess over 512 in 1 u bins: −7:2 −6:2 −5:4 −4:3 −3:54 −2:56 −1:103
  +0:303 +1:300 +2:183 +3:69 +4:45 **+5:2**; **ceiling 517.5 u**. Types 4/7/8 (190/216 u/s)
  chord the same 512–515 — distance, not time, REALFIX-W2 corroborated on 1,255 logs.
  Another 225 same-heading pairs under 505 u are reports a sub-degree heading nudge fired
  (the 7-field command change), not the trigger; counted, excluded from the band.
- **The tail over 518 u, 34 chords, splits in two** and neither is the trigger: 6 late
  reports of 525–573 u (13–61 u late — a frame hitch of 45–210 ms, all type 1), and
  **28 silent walks** of 619–6,182 u = 1.2–12 triggers over 2.2–31 s at cruise speed, a
  body walking without reporting — §0.11 stage 2's *"releases go unreported"*, and eight
  of them within 2 u of 765.5–767.5 u: a D1 order walked end to end (§1z-ab.5c).

### 1z-ab.2 The maturation-margin premise, refuted by the decode

§1z-u.4's margin is protection against a DROPPED re-aim: the copy keeps walking the old
heading, and a longer lead gives the next natural report time to re-aim it before it
matures. Two things kill that premise, and the first was in the transcription all along:

**(a) A lead's copy sits outside the reprieve tube by construction.** The AgTrack chain
holds the body's own command points (`record_async` at each `0x003D`/`0x003E`/`0x0047`)
and the newest segment ends at the report that triggered the lead, so a copy ≥ 100 u down
the ray misses the match test, and **every** evaluation on it — every grant with the fence
open (caller A), every arrival (caller B), the sweep — goes to gate 1: |copy − body| <
299.33 u. A dropped re-aim therefore snaps at the **next grant's own evaluation** whenever
the turn is wide enough (separation = closing speed × silence; a reversal at 576 u/s
crosses 299 u in 0.52 s), whatever the length. The 08:46 case (§1z-u.3: refusal at
24.155 s, 2.7 s of silence, a 498 u snap at the arrival): with 766 the copy matures 0.86 s
later and the 26.85 s re-aim's evaluation snaps at ~500 u anyway. The margin bought
nothing; the mechanism was gate 1, not maturation.

**(b) The hold (§1z-y) bounds the silence at floor + tick = 0.55 s**, inside which no lead
over 158 u can mature (`bounds: no_mature_in_hold`, 520 > 288 × 0.55). The dropped-re-aim
case the margin was for no longer exists on the shipped path.

### 1z-ab.3 What the length does govern (MEASURED)

**(i) Cruise maturation.** In cruise the re-aim lands one chord after the grant; the copy
trails the body by the loop lag and both run the same family — the client's own velocity
fields hold exactly {190, 216, 288} u/s (933 moving samples over five taps, no slow plateau:
FINDINGS:1201's ½/⅓ plateaus are a report-derived artifact) — so the copy reaches its point
before the re-aim **iff the lead is under the chord plus the frame jitter**. On tape at 520:

| capture | lead legs ≥ 300 u | distance to go when the re-aim landed | matured | park |
|---|---|---|---|---|
| RUN-1zT (`agenttap-20260903T073122`, before the 17.77 s onset) | 3 | 13.9 / **0.7** / 3.9 u | 1 (at its point within the last sample) | 0.00 s |
| RUN-FEEL (`agenttap-20260903T084632`, operator, lead ON) | 2 | 465.9 (re-aimed at 0.44 s) / 7.5 u | 0 | — |
| the twelve 08-26 D1 sessions at 766 (movetap, 625 legs ≥ 600 u) | 625 | p50 642 u | 5, all clipped stubs | 0.00 s |

So 520 sits **at** the edge: one tap sample (33 ms, 6–10 u) over the trigger's ceiling. The
copy reaches its point on the +5 u chords and the six hitched reports, for ≤ 0.2 s.

**(ii) A cruise park is benign in the decode.** Arrival → miss → gate 1 (separation ≈ the
lag, 4–74 u on the legs above) passes → gate 2 (the clipped endpoint is on-mesh) passes →
`NOMATCH_PASS`, no Clear, no record. `RESYNC` is off by default — and must stay off on any
lead run: its model holds the client at its *last report*, so under any lead it reads up to
a whole lead of separation and would fire on every leg. The one live consumer is the guard's
clause 2: `arrival_risk` models a keyboard body as parked at its last report (`_async_est`
glides only toward a click), so it **predicts a snap at every maturing lead** — RUN-1zT's
log: `agtrack_repin blocked arrival-risk` ×7, RUN-FEEL ×1 — and was blocked every time by
`REPIN_MAX_REPORT_AGE` (0.347 s; a cruise re-aim's report is 1.8 s old). Latent, and
recorded (§1z-ab.5b): the guard needs a keyboard glide term before that precondition is
ever loosened.

**(iii) The one cost monotone in the length is the order-walk.** If a lead is ever walked
as an order — a fence shut by something the 1z-aa tracker does not see — the body walks
the lead. 766 costs 246 u more per event than 520. Nothing else in the decode depends on
the length above the trigger: the hold's residual is the hold's (§1z-ab.5a); a wall nearer
than the chord clips both lengths to the same stop; the stop echo re-pins the copy at the
stop and the copy *trails* the body, so §1z-t.6's echo-less overshoot rows (766 "worse than
shipping nothing") are the copy walking on after the body stopped, not a length effect.

### 1z-ab.4 The derived answer: 520 stands

The length must exceed the trigger's ceiling (517.5 u) — 520 does, by one tap sample — and
should be the smallest such value, because the only quantity that grows with it is the walk
in the failure mode the four gates exist to prevent. 766 is refuted as a margin and costs
246 u; no number between them buys a mechanism; a number under the ceiling parks the copy
every chord. The bounds are pinned in `test_leadmargin` against `authsrv`'s own constants
(the lead, the floor, the tick, gate 1, the reprieve radius), so a lead or a floor moved
without this argument goes red. **Not changed:** `KBD_SYNC_LEAD`. **Not added:** a length
knob — nobody has a derived reason to turn one, and a run-stat loop over it is what the
2026-08-30 direction refuses.

### 1z-ab.5 Residuals, recorded

- **(a) The hold's same-family wide turn** (the hold's, not the length's; lead-only). Two
  copies can separate for the whole window before the re-bake is evaluated: cross-family
  (W↔S, 288 + 190) × 0.55 s = 262.9 u, under gate 1 by 36 u; **same-family** (a camera
  swing under a held W, 2 × 288) × 0.55 = **316.8 u, over it**. Corpus: 3,623 rate-refused
  heading re-aims in 123 sessions (2,018 under 30°, 1,019 at 30–90°, 309 at 90–150°, 277 at
  ≥ 150°); predicted separation at the re-bake, closing speed × (0.5 − since_last + 0.08):
  **1 ≥ 299.33** (310 u — a 137° forward-family turn at since_last 0.000,
  `20260826T104840` t=100.1), 26 ≥ 250. Under zero-lead the re-bake's point is a chain node
  and MATCHes, so this is the lead's exposure alone. Not built; the derived fix is a re-bake
  that sends the zero-lead point when the modelled separation is within `CLOCK_SKEW_U` of
  gate 1 — filed for the run's scoring.
- **(b) The guard's keyboard-glide gap** (§1z-ab.3 ii). Filed.
- **(c) The SILENT-WALK signature.** 28 same-heading cruise chords of 1.2–12 triggers in
  the server logs alone, 08-10 → 09-01, eight of them a D1 order walked end to end. This is
  §0.11's lock readable **without a tape** — `w0score`'s detector needs the drawn body's
  target, which only a tap holds. Filed as the next instrument (a silent-walk verdict from
  the gamesrv log), not built here.
- **(d)** The 225 sub-505 u same-heading pairs are nudge reports, not the trigger, and the
  extractor's 1.15° cosine tolerance is what admits them; they are counted as `below`.

### 1z-ab.6 Tests, docs, and what remains

`toolkit/clientscan/test_leadmargin.py`, new: 25 checks (floor 24, bare-machine sections
1–3 over synthetic gamesrv and tap rows; section 4 reproduces the corpus figures as floors
and signatures when the vault is present and skips loudly otherwise). `test_kbdsync` 84
unchanged (the `KBD_SYNC` block's (c) paragraph and the constant's comment rewritten to the
derived result; the formula and the constant untouched), `test_d1lead` 94, `test_srclint`
26 — green. TESTS.md, PLAN.md §8 + Q13, HANDOFF.md §C.

**What remains before `--kbd-lead` becomes the default is the run** (set up 2026-09-03 as
`RUN-1zAB.md`, not yet run)**:** RUN-1zT's script
under `--kbd-lead` with the four gates on (HANDS OFF THE KEYBOARD), scored by `w0score.py`
with the enslavement detector and, per §1z-ab.5a, with `--resync` off. Then `0x005FCAA0`.
No client launch, no static reads, no upstream derivation; every figure above is
reproducible with `python toolkit/clientscan/leadmargin.py --check`.


---

## 1z-ac. RUN-1zAB RAN — INCONCLUSIVE by its own registration; the detector had a co-directional-lead blind spot (closed), and the residual is the lead maturing at the report boundary

**Asked:** "set up the --kbd-lead run" then "go ahead and drive it". Driven 2026-09-03 18:39
on the loopback stack, agent-driven, RUN-1zAB.md's script verbatim. Capture
`agenttap-20260903T183943`, gamesrv `authsrv-20260903T183941-c1`, harness
`20260903T183905`. Ident `MOVECODE-1z-ac`.

### 1z-ac.1 The registered verdict, stated first

RUN-1zAB §2 required **FREE for the whole capture AND p50 < 150 u AND travel scaling
with hold**. Two of the three held. The detector did not read FREE.

| | registered | measured |
|---|---|---|
| world-0 vs the drawn body, p50 | < 150 u confirms | **1.0 u** ✅ |
| per-leg travel scales with hold | required | **W 1,062 / 1,155 / 1,045 u (5 s), S 543 / 677 u (4 s), Q 620, E 589 u (3 s)** ✅ |
| enslavement verdict | FREE confirms | **MIXED** ❌ |

**⇒ INCONCLUSIVE.** Not REFUTED either: nothing read ENSLAVED, no held-key leg parked
(the ≤ 50 u clause), no new warp class. Exposure well over floor — 5,869 u of body
translation over 278 moving samples, 22 `KBD LEAD` on the wire (floor 8), 13 lead legs
≥ 300 u (floor 3). The banner named all three terms and all four gates. **The bar is not
moved after the fact**; what follows is why MIXED, split into a detector defect and a real
residual.

### 1z-ac.2 The detector's co-directional-lead blind spot (OBSERVED, and it is ours)

As shipped, the detector read **MIXED, 50 of 278 (18.0 %)**. Reading the flagged samples
raw refutes 44 of them. On the S leg (14.91–17.30 s), every flagged sample has:

| | |
|---|---|
| the drawn copy's target `+0x9C` | (10105.2, 8604) |
| world-0's target `+0x9C` | (10105.4, 8604) |
| our granted dest | (10105.4, 8604) |
| body target vs grant | **0.53 u** — inside `GRANT_EPS`, so flagged |
| body target vs world-0's target | **0.2 u apart — NOT the same value** |

**The two copies point at two different places.** World-0 carries our grant exactly
(0.00 u); the drawn copy carries its own backpedal projection. The detector flagged it
because our lead lands 0.53 u from the client's own co-directional target — and that is
**by construction**: §1z-t.6 derived the 520 u length from the client's own ~512 u report
chord, so on any straight lead leg our grant dest and the client's own target nearly
coincide. The instrument built to resolve §1z-u.3's "world-0 vs body cannot tell" was
confounded by the very tuning that makes the lead work.

**The discriminator, from the decode.** A `0x0029` with the AgTrack fence **OPEN** is
applied to world-0 only (sync-only handler `0x005FD890`, §0.11), so world-0's target
becomes the grant and the drawn copy keeps its own; with the fence **SHUT** the full
applier writes **both** copies to the grant. So the body is enslaved to a grant **iff its
target is bit-identical to world-0's target** — not merely within `GRANT_EPS` of the
grant. Validated against both controls and the run:

| capture | flagged by the loose join | bit-identical | distinct |
|---|---|---|---|
| RUN-1zT (known ENSLAVED) | 114 | **113** | 1 |
| RUN-1zAB (this run) | 50 | 6 | **44** (0.53–0.75 u) |
| the zero-lead baseline (known FREE) | 0 | 0 | 0 |

**Built:** `TGT_SAME = 0.1` and the `both_agree` / `enslaved` split in `w0score.py`; the
loose count is kept and printed beside it so a report names what was excluded. Controls
after the change: baseline **FREE**, RUN-1zT **ENSLAVED 113 of 193 (58.5 %)** from the
same 17.77 s onset — the known positive survives. This run re-reads **6 of 278 (2.2 %)**
and **seven of its eight legs FREE**.

### 1z-ac.3 The residual six are REAL, and they are the lead maturing (OBSERVED)

The remaining six samples are not a confound. On the Q strafe leg both copies carry
(11146.4, 10073.3) bit-identically, and one sample earlier — 29.23 s — the drawn body sits
at **(11145.9, 9561.9) with velocity 0 and no target**: our *previous* granted endpoint,
exactly 520 u from the leg's start. The drawn body reached our lead's end and parked for
one sample; the next grant re-aimed it and it walked on.

**Why it happens, and it is structural rather than bad luck.** 520 u divided by each
family's speed lands within 0.01 s of that family's own measured report gap:

| family | 520 / speed | report gap |
|---|---|---|
| forward, 288 u/s | 1.81 s | 1.80 s |
| backpedal, 190 u/s | 2.74 s | 2.74 s |
| side, 216 u/s | 2.41 s | 2.40 s |

Maturation and the re-aim are a **photo finish in every family** — which is §1z-ab.4's
"520 sits one tap sample over the trigger's ceiling" seen from the other side. When
maturation wins, the drawn body parks momentarily on our point. Cost, measured: the Q leg
travelled 620.4 u against a 646 u free-walk expectation, **~26 u and one sample of stall**.

**It is not a lock, and this is the part that matters.** ⚠ **CORRECTED 2026-09-03 by §1z-ad, and this whole paragraph is why n = 1 was not enough:** the rerun of this same script armed the lock on five of eight legs. The park and the lock are the SAME event — a lead maturing — and this run merely won every coin flip. Read §1z-ad before quoting anything below. The player's release was reported
(`0x0047`) on that leg and on all seven; the body stopped where the player let go — 385 u
short of our grant on the Q leg, 34 u short on the S leg — no `0x002C` was sent all run,
no re-pin fired, and the maximum `position_at` separation was 155.6 u with no ~500 u
arrival snap. §0.11 stage 2's signature (releases swallowed, the applier never running) is
**absent**. The four gates composed as designed; the enemy control stayed p50 0.6 / max
63.6 u.

### 1z-ac.4 What is NOT concluded

- **`--kbd-lead` is not promoted.** The run was registered to confirm on FREE and did not.
  It stays opt-in.
- **The length is NOT tuned.** §1z-ab.4 refuses a length sweep and this run does not
  reopen it: the residual is the boundary the length argument already named, its measured
  cost is ~26 u with no lock, and moving the constant to dodge a photo finish is the
  treadmill the 2026-08-30 direction exists to refuse. If it is ever revisited, the object
  is the re-aim cadence, not the lead.
- **Two gates had zero exposure by construction** (no press or click, so no KILL; no
  `0x002C`, so no FENCE GATE) — reported as zero, not as passes. The HOLD fired **12**
  times (`deferred-heading` re-bakes) and is the one gate this run exercised.
- **`agtrack_repin blocked arrival-risk` fired 6 times**, as §1z-ab.5b predicted: the
  guard models a keyboard body as parked and wants a re-pin at every maturing lead. Still
  latent, still blocked by `REPIN_MAX_REPORT_AGE`.

### 1z-ac.5 Tests and the next step

`test_w0score` 38 → **45** (floor 44): section 6 drives the confound (a drawn copy whose
own target is inside `GRANT_EPS` of a server-chosen grant while world-0 carries the grant
reads FREE, and the loose count still names it), real enslavement (both copies identical
reads ENSLAVED with an onset), the threshold's position between float identity and the
measured 0.53 u floor, a known-bad arm at twice the threshold, and a parked world-0
enslaving nothing. `test_leadmargin` 25, `test_kbdsync` 84, `test_d1lead` 94 green.
`studies/movecode/review/gatecensus.py` gained the hold's re-bake row (it counts
`deferred-heading` verdicts, which is how the hold reports itself).

**Next:** the run that would settle `--kbd-lead` is a rerun on the fixed detector — the
same script, whose only registered failure was an instrument defect now closed. That is a
judgement call for the owner rather than a session, because it spends operator machine
time on an arm that is already opt-in and already measured p50 1.0 u. Then `0x005FCAA0`.


---

## 1z-ad. THE RERUN REFUTES — the same script, same build, same flags, and the lead armed REALFIX §0.11's lock on five of eight legs; §1z-ac's "no lock" was n = 1 and is CORRECTED

**Asked:** "rerun it on the fixed detector." Registered before launching (RUN-1zAB's
rerun block, committed `55e4edc`), driven 2026-09-03 19:12, agent-driven, hands off.
Capture `agenttap-20260903T191321` / `authsrv-20260903T191320-c1` / harness
`20260903T191246`. Ident `MOVECODE-1z-ad`. **The lead stays OFF.**

### 1z-ad.1 The verdict: REFUTED, on both clauses that were registered to refute

| registered | measured |
|---|---|
| REFUTES the fix: **ENSLAVED ≥ 25 %** | **ENSLAVED, 29 of 60 moving samples (48.3 %)**, onset t = 15.40 s |
| REFUTES the §1z-ac reading: a held-key leg moving ≤ 50 u, or an unreported release | **five of eight legs parked** (35 u, 0, 0, 0, 0) and **one reported stop for seven key legs** |
| expected FREE or MIXED under 5 %, every flag a maturation park | wrong on both counts |
| travel scales with hold | **fails**: body translated 1,347 u total against run 1's 5,869 u |

Not a marginal call and not an instrument artifact: the flags are the **strict**
bit-identity test §1z-ac shipped, and they are corroborated by three independent
signatures the detector does not use — travel that does not scale, five parked
held-key legs, and six of seven releases never reaching the wire.

### 1z-ad.2 The door that opened, to the second (OBSERVED)

> **The OBSERVATION below stands; the CAUSAL framing does not. §1z-am (2026-09-04)
> scored 'a clear lead matured before the release' over all 17 lead runs: **six healthy
> runs carry it and one locked run carries none**, so it is neither necessary nor
> sufficient. REALFIX §0.11's two-stage account ("neither alone suffices") is untouched —
> what is refuted is reading this maturation as *the door*.**

Not a `0x002C`, not a dropped re-aim, not a gate failing. **A lead matured while the
key was still held.**

| gamesrv t | |
|---|---|
| 15.82 | `S` pressed; the fence re-arms at the walk-start; lead `(9850,8283)`, 520 u backpedal |
| 16.80 | re-aim, lead `(9724,8318)`, 520 u, `clip=clear` — **matures at 16.80 + 520/190 = 19.54 s** |
| 19.80 | the player releases `S` — **0.26 s after the lead matured** |
| — | **no `0x0047` is ever sent.** The release is swallowed |
| 21.55 | the next report is at `(9724,8318)` — **our lead's endpoint, exactly** |
| 28.26 → 37.72 | reports keep arriving with `mt` 7, 8, 4 — keys ARE being pressed and the client says so — and the body does not move |

That is REALFIX §0.11 stage 2 verbatim: the body walks the lead as a click-order, the
release goes unreported, the walk-start applier never runs, the fence never re-opens.
The client is locked for the remaining five legs.

**The four gates could not have stopped it, and this is a coverage gap rather than a
bug in any of them.** The FENCE GATE (§1z-aa) degrades a lead only when *we* shut the
fence with a `0x002C`; here the fence was open and we shut nothing — it worked
correctly *after* the lock, degrading four later leads to `ZERO LEAD (fence-shut)`. The
HOLD (§1z-y) had **zero exposure** (no rate-refused re-aim all run). The KILL had zero
exposure (no press, no click). The MATCHED WORD does not bear on maturation. **No gate
covers a lead maturing unanswered while the fence is open** — which is §1z-u.3's
original mechanism, the one that made the lead opt-in in the first place.

### 1z-ad.3 §1z-ac is CORRECTED: the 26 u park and the lock are the same event

§1z-ac read six flagged samples on run 1, found the drawn body had reached our endpoint
and parked for one sample before resuming, and concluded "**~26 u and one sample of
stall. NOT A LOCK**", citing the reported releases. **That conclusion was drawn from
n = 1 and is falsified by n = 2.** The maturation park *is* the lock's arming event; run
1 simply won every coin flip and run 2 lost one. Both runs show the same photo finish
(§1z-ac.3: 520/speed within 0.01 s of each family's report gap) — what differs is
whether the key was released before or after the arrival tick. On run 1 every release
beat the maturation; on run 2 one release lost by **0.26 s** and cost the session.

The reported-stop count is the cleanest discriminator between the two runs and it is
free from the wire: **7 stops for 7 key legs (run 1) against 1 (run 2).**

### 1z-ad.4 §1z-ab's refutation of the maturation margin is INCOMPLETE (CONTESTED)

§1z-ab.2 declared the maturation margin "void", on the ground that a lead's copy is
outside the reprieve tube so **a dropped re-aim** snaps at the next grant's own
evaluation whatever the length. That argument is sound for the path it addresses and
**does not cover this one**: nothing was dropped here, no re-aim was due, and the
failure was the arrival tick firing mid-hold. The length does govern that timing
directly — at 766 u the same lead matures at 16.80 + 766/190 = **20.83 s, after the
19.80 release**.

**This is recorded, not acted on, and 766 is NOT adopted.** It would move the photo
finish, not remove it: a longer lead still matures inside any hold longer than
`length/speed`, and §1z-t.6 measured 766 alone as *worse than shipping nothing* on the
separation the lead exists to fix. Tuning the constant against a two-run sample is the
treadmill the 2026-08-30 direction refuses. What this run establishes is the **object**
a fix must address, and it is not the length: **a lead must never be left to mature.**
The server knows when it sent one and at what family speed, so the maturation instant is
computable — `authsrv.py` already carries exactly this idea for another arm
(`HEADING_GRANT`: *"REFRESH THE CLIENT'S ARMED DESTINATION. It is the only thing that
stops a stale one maturing into a teleport"*). A refresh before maturation, or no lead
at all, are the two candidates; neither is derived yet and neither ships here.

### 1z-ad.5 What stands, and what this run cost

- **`--kbd-lead` stays OPT-IN and OFF.** The opt-in discipline (§1z-u.5) is what kept
  this out of the operator's ordinary session; it is vindicated, not revised.
- **No default-ON path is implicated.** The gates are inert without the lead; `AGTRACK
  RE-PIN` (gate1-red) and `PLANE-REPAIR #1` fired *on* the locked client, downstream of
  the lock, and neither caused it.
- **The §1z-ac discriminator is unaffected and is doing its job** — it read this capture
  ENSLAVED on the strict test, and the two samples it excluded as co-directional
  confound were genuinely that.
- **Method note.** One run said "probably fine"; two runs said "the lock is live." A
  single scored run of a stochastic failure is a point estimate, and §1z-ac published a
  mechanism claim ("no lock") on one. Two runs of a coin flip are not many either — what
  makes this one decisive is that the failure it found is a *mechanism* with a timeline,
  not a shifted statistic.

`test_w0score` 45, `test_leadmargin` 25, `test_kbdsync` 84 — unchanged and green; no
code changed in this section. The next object is the one named in §1z-ad.4, and choosing
between its two candidates is the owner's call.


---

## 1z-ae. REFRESH BEFORE MATURATION — the lead's arrival is a §0.11 stage-1 armer, and the server now pre-empts it; the first draft aimed from the model and a test lock caught it

**Asked:** "do the refresh-before-maturation fix" — the object §1z-ad named after the
rerun locked five of eight legs. Ident `MOVECODE-1z-ae`. **No client run yet**; the
registered prediction for one is §1z-ae.6. Inert under the shipped default, because the
lead it guards is still opt-in.

### 1z-ae.1 Why the arrival is an armer, and why §0.11 did not name it

REALFIX §0.11 decodes the lock as two stages and says *"neither alone suffices"*:
stage 1 is a **snap whose dispatcher clears `clientControlled`** (fence shut), stage 2 is
the lead's click-walk regime, under which *"every press acquires a fresh click-order,
releases are ignored, no `0x0047` is emitted, and the keyboard walk-start applier — the
only fence re-armer — never runs."* §0.11 named exactly one stage-1 route, plane-carry's
stale word across a seam, and §1z-z's matched field 4 kills that one.

**The lead's own arrival is a second route to the same stage, and it was already measured
in this repo** — in the `HEADING_GRANT` block, from the client's own memory
(`movetap.py`, 2,332 samples): *"agent+0x48 is set ONCE at the grant and never re-armed,
and at that exact millisecond the client SNAPS to the granted point"* — seven arrivals,
98 u to 5,238 u, every one within one 20 ms sample of schedule. A maturing lead **is** a
snap. Compose it with stage 2, which the lead itself supplies, and the lock is complete
without any plane mismatch. That is what §1z-ad measured: no `0x002C`, no dropped re-aim,
the plane constant at 29, matched words on every grant — and five dead legs.

**Why it is a race and not a constant.** The `0x003D` is distance-triggered at ~512 u
(REALFIX-W2) and the lead is 520 u, so on a held key the next report is due at 512/S and
the arrival at 520/S — **8 u apart, 0.028 s at 288 u/s and 0.042 s at 190**. Normally the
report wins and its own re-aim re-arms `+0x48`. When it loses, the arrival fires. Same
script, same build: run 1 clean, run 2 locked.

### 1z-ae.2 The fix, and what it deliberately is not

At **ETA − 2 ticks**, push the leg's own destination `KBD_SYNC_LEAD` further along the ray
it is already on, clipped, with matched plane words. The grant re-bakes and re-arms
`+0x48` a full leg further out, so the snap never fires.

- **Not a re-pin at the modelled body**, which is what §1z-y's kill sends. At the ETA the
  model puts the body *at* the lead's endpoint (`a2_leg_position` clamps there), so a
  re-pin would be a zero-distance grant — the `distSq ≤ 1.0` short-circuit — which arms
  `+0x48 = now+1` and moves the same arrival one tick later. **Only an extension
  postpones it.** The kill stays what it is: the answer to a press or a click, where the
  player has told us the leg is over.
- **Not a longer lead** (§1z-u.4's maturation margin, which would also have avoided
  §1z-ad's lock at 766 u). §1z-t.6 measured 766 alone as *worse than shipping nothing* on
  the separation the lead exists to fix (p50 425 u against 237), and a longer lead still
  matures inside any hold longer than `length/speed`. It moves the photo finish rather
  than removing it. **`KBD_SYNC_LEAD` is untouched**; §1z-ab.4's refusal of the length
  sweep stands.

### 1z-ae.3 ★ The first draft aimed from the model, and `test_d1lead` caught it

The draft computed a fresh lead from `a2_leg_position` — where the model puts the player
now — and clipped it from there. `test_d1lead`'s clip census went red: *"EVERY call is
anchored on the REPORT in hand… `state['pos']`-anchored is `--heading-grant`'s graveyard
(R2-1): a ray from the model's belief aims the lead from somewhere the client is not."*

**The lock was right and the draft was wrong.** The corrected shape extends the
**existing** leg instead of starting a new one: the record's origin and `t0` are
untouched and only `dest` moves, so

- the ray keeps the anchor the client itself reported;
- `a2_leg_position` is **continuous across the refresh** — the same instant reads the same
  point before and after, pinned by its own check;
- the clip runs from that report, spelled `a2_clip_lead(state, reported, dest)` like the
  other two callers, because the census reads the spelling.

The census moved 2 → 3 with the third site named, not bumped: its own comment already
allowed *"a third caller anchored correctly"* and forbade *"a second one anchored on the
model"*, which is exactly the distinction that had to be made. **This is the check that
could fail doing its job on a change written the same evening.**

### 1z-ae.4 The bounds, because an extension that never stops is a runaway

1. **Once per report.** The counter lives in the leg record and every `0x003D` arms a
   fresh record, so a silent client gets one extension and no more. A second consecutive
   silence is not a race — it is a client that has stopped reporting.
2. **Only while the keyboard latch says moving** — a reported stop clears it.
3. **Never while our own `0x002C` has the fence shut** (§1z-aa's tracker, the same read
   the lead itself takes).
4. **Clipped**, so a blocked body — where the model drifts fastest — shortens it. If the
   mesh refuses the extension outright the tick sends **nothing** and says
   `refresh-blocked`: re-baking the same point would only re-arm the same arrival.
5. **Past the ETA it sends nothing and says `refresh-late`**, once per leg. The arrival
   has already fired; a silent miss would hide §1z-ad's own event.

**Known side effect, stated rather than discovered later.** The margin is two ticks and
the race is ~0.03 s — narrower than one tick, which is why the margin cannot be tuned to
sit inside it — so the refresh will usually fire ~0.06 s **before** the report that would
have pre-empted it. Its send stamps the shared grant clock, so that report's own lead can
be refused `heading-rate`, and §1z-y's HOLD then re-bakes it at the floor. That path is
already shipped and tested; the copy runs on the refreshed lead, computed from a model
validated to p50 0.0 / p90 16 u (§1z-t.6), for at most one floor interval.

### 1z-ae.5 Tests

`test_kbdsync` 84 → **106** (floor 106), section 14: the flag and its global; the margin
as two ticks and the budget as one; not due mid-leg; **due** → one grant extending the
ray with matched words and a wire label, the arrival moved a full leg out, the record
keeping its origin and `t0`, the position model continuous across it; the second
extension refused and the budget resetting with the leg; refused on a reported stop and
on a shut fence; `refresh-late` past the ETA, once not per tick; `refresh-blocked` when
the clip refuses; the known-bad arm (`--no-kbd-lead-refresh`) leaving the lead to mature;
inert with the lead off; and four source locks. `test_d1lead` 94 (census re-aimed),
`test_position_trust` 235, `test_router` 114, `test_playerswing` 116, `test_cancelwalk`
124, `test_srclint` 26 — green.

### 1z-ae.6 The registered prediction, before any run

| | |
|---|---|
| **CONFIRMS** | `kbd_leg act=refresh` rows fire, **zero `refresh-late`**, and the capture reads FREE with every key leg's release reported and travel scaling with hold |
| **REFUTES** | any `refresh-late` row (the backstop lost its own race), or a lock at all (ENSLAVED / a parked held-key leg) |
| **Expected** | ~1 refresh per cruise leg, since the margin usually beats the report; `refresh-blocked` only where the route meets geometry |
| **Says nothing** | one clean run does not settle a race — §1z-ad is the reason. Two runs, and the mechanism rows (`refresh` firing, `refresh-late` absent) are the verbatim check, not the verdict word |


---

## 1z-af. THE REFRESH IS REFUTED BY ITS OWN VERIFICATION RUNS — preventing the arrival does not prevent the lock, so §1z-ae.1's armer account is not sufficient; the backstop is now OPT-IN

**Two runs, both locked**, on RUN-1zAB's script with `--kbd-lead` and the refresh live.
Registered bounds are §1z-ae.6's, written before either run. Ident `MOVECODE-1z-af`.

### 1z-af.1 The verdict

| | §1z-ae.6 registered | run A `agenttap-20260903T195932` | run B `agenttap-20260903T200621` |
|---|---|---|---|
| verdict | FREE confirms | **MIXED 24.3 %** | **ENSLAVED 31.4 %** |
| parked held-key legs | any refutes | **2** (S, W) | **3** (S, S, W) |
| reported stops / 7 key legs | all seven | **3** | **3** |
| `refresh` rows | expected | 3 | 2 |
| `refresh-blocked` | expected on geometry | 3 | 1 |
| **`refresh-late`** | **any refutes** | 0, and unreadable — see §1z-af.2 | **1** |

**⇒ REFUTED, on both registered clauses.** Run B carries a `refresh-late`: an arrival won
its race in spite of the backstop. And every run locked regardless — including run A,
where the backstop lost no race it could see.

### 1z-af.2 An instrument defect of mine, found by the first run and fixed before the second

Run A reported **zero `refresh-late` and three `refresh-blocked`**, and the first number
was worthless: the blocked path set the same `refresh_late` latch the late path checks, so
on exactly the legs where the clip had refused the extension — the legs where the arrival
was therefore still coming — a `refresh-late` could not be emitted. Split into two latches
and pinned by a test that drives blocked-then-late on one leg (`42a47e3`), which is how
run B could report the late arrival at all. **A backstop that cannot say it lost is not a
backstop**, and this one could not for a whole run.

### 1z-af.3 What it means for §1z-ae.1's mechanism

§1z-ae.1 argued the lead's arrival is a §0.11 stage-1 armer, from the client's own memory
(`+0x48` fires once and the client snaps to the granted point). That reading is not
overturned — the snap is measured — but **it is refuted as a SUFFICIENT account of the
lock**: two runs prevented most arrivals and locked anyway, and run B's early `S` leg
parked at 0 u before any refresh had fired at all. Something else arms it, or the arrival
is not the arming route on this path. §0.11's own stage-1 route (plane-carry's stale word)
is killed by §1z-z here, so the armer on the keyboard path is now **UNIDENTIFIED**, and
that is the honest state.

One repeatable detail for whoever picks this up: in **both** refresh runs the `E` strafe
leg read ENSLAVED 100 % and every leg after it parked, with onsets 29.58 s and 29.80 s —
the same place in the same script. §1z-ad's lock, without the refresh, armed on a
backpedal at 15.40 s instead, so this is not a fixed trigger; but a repeated onset inside
one arm is a lead worth pulling.

### 1z-af.4 Disposition, by §29's rule

`KBD_LEAD_REFRESH` now defaults **False**; `--kbd-lead-refresh` opts in and
`--no-kbd-lead-refresh` still parses and wins. One run convicts one term (§29, applied to
the lead itself in §1z-u); this had two. It also roughly **doubles the effective lead**
(520 → up to 1,040 u), and §1z-t.6 measured longer leads as worse on the very separation
the lead exists to fix — so leaving a refuted backstop on inside `--kbd-lead` would be
shipping a measured-harmful quantity on a hypothesis two runs contradict.

The code and its 22 checks stay: the mechanism rows (`refresh`, `refresh-late`,
`refresh-blocked`) are the instrument the next session reads the race with, and they cost
nothing while the flag is off. **Nothing shipped changes** — the lead is opt-in, so the
refresh was inert for anyone not passing `--kbd-lead`.

### 1z-af.5 Where the keyboard lead now stands

Four scored `--kbd-lead` runs exist, all on one script and one map:

| run | refresh | verdict | parked legs | stops / 7 |
|---|---|---|---|---|
| 18:39 (§1z-ac) | off | MIXED 2.2 % (strict) | 0 | 7 |
| 19:12 (§1z-ad) | off | ENSLAVED 48.3 % | 5 | 1 |
| 19:58 (run A) | on | MIXED 24.3 % | 2 | 3 |
| 20:05 (run B) | on | ENSLAVED 31.4 % | 3 | 3 |

**Three locks in four runs, and the samples do not separate the arms** — n = 2 either
side, one metric, one route. Nothing here says the refresh helps or harms; it says it does
not fix. The lead stays OPT-IN and OFF, which is where §1z-u put it and where every run
since has kept it.

**The next object is not another backstop.** It is the armer: what shuts the fence on the
keyboard path once §1z-z has killed the plane route. `agenttap` cannot see the fence (its
`controlled` field is the controlled agent's id, §1z-aa.1), and `movetap` — which reads
`clientControlled` directly — has not been run against a lead arm. That is the
instrument gap to close before the next fix is designed, and it needs no new theory.


---

## 1z-ag. THE ARMER, IDENTIFIED — the lead's own arrival teleports the drawn body onto world-0 across a gate-1 separation and clears the fence, with no message of ours within a second of it

**Asked:** "close the instrument gap: run movetap against the lead arm." `movetap.py` reads
AgTrack's `clientControlled` at the record; `agenttap` cannot see the fence at all
(§1z-aa.1), which is why §1z-af had to leave the armer unidentified. Prediction registered
before launching (RUN-1zAB's armer block, `a2a1560`). Ident `MOVECODE-1z-ag`.

### 1z-ag.1 The answer, in the client's own memory

`movetap-20260903T202134` × `authsrv-20260903T202121-c1`, `--kbd-lead`, refresh OFF (its
default since §1z-af). The run **locked** — 1 reported stop for 7 key legs — so the
exposure floor this run registered was met.

| client clock | fence | `+0x48` | sync copy | drawn body | body velocity | separation |
|---|---|---|---|---|---|---|
| 16826 | open | 17740 | 10022.6 | 10369.4 | **0.00** | 347.1 |
| … | open | 17740 | walking | 10369.4 | **0.00** | growing |
| 17730 | open | 17740 | 9851.4 | 10369.4 | **0.00** | **518.0** |
| **17831** | **shut** | re-armed | 9839.7 | **9849.4** | −190.08 | **6.84** |

Two consecutive samples. The sync copy walks the granted lead while **the drawn body is
parked**; separation grows 347 → 518 u, past gate 1's **299.33 u**; the arrival due at
17740 fires; and the drawn body's point is written **520 u exactly onto our granted
destination** while `clientControlled` clears. The fence never re-arms for the remaining
46 s.

**It is not the `+0x78` sample-and-hold artifact**, which is the trap `movetap`'s own
docstring exists to warn about (*"across a perfectly normal glide the `+0x78` trace is
flat for the whole leg, then one step onto the destination — exactly what a teleport looks
like"*). Checked directly: through the whole approach `async_vel_raw` is **(0.00, 0.00)**
and the integrated position equals the raw point, which is what a parked agent looks like
and what a gliding one cannot. Velocity becomes −190.08 only *after* the jump.

So this is REALFIX §0.11 stage 1 on the keyboard path, and it is the `HEADING_GRANT`
block's own measurement — *"`agent+0x48` is set ONCE at the grant and never re-armed, and
at that exact millisecond the client SNAPS to the granted point"* — caught in the act,
with the gate it fails visible in the same rows.

### 1z-ag.2 Every registered discriminator, answered

| registered | measured |
|---|---|
| the fence flips open→shut once and stays shut | **yes** — one shut, no re-arm in 46 s |
| §0.11's `async_reqtoken` fingerprint reproduces | **no, and it does not discriminate here**: the token reads 0 both before and after, so on this path it does not mark the edge |
| a position snap rides the same sample | **yes — 520 u**, far larger than §0.11's ~15 u, because this is a gate-1 failure rather than a plane reconcile |
| the plane words are already equal before the shut | **yes in run A, 29 = 29 at every transition** — the plane route is not this armer. **But run B shows the disagreement still occurs** (§1z-ag.7), so this is “not the armer here”, not “eliminated” |
| no server message rides the shut edge | **confirmed, and wider than registered**: no player `0x0029` or `0x002C` within **±1.5 s**. Nearest send is an enemy speed message 1.39 s before; our next player grant is 1.13 s *after* |
| would re-open the arrival reading | **it does** — §1z-ag.3 |

### 1z-ag.3 §1z-af.3 is CORRECTED: the arrival is the armer

§1z-af.3 wrote that preventing the arrival did not prevent the lock and therefore the
armer was "UNIDENTIFIED". **The observation stands; the conclusion was wrong.** This
capture shows the arrival arming the lock directly. What §1z-af measured was that the
refresh's **coverage** was incomplete — it fires at most once per report, was
`refresh-blocked` by the clip 1–3 times per run, and lost one race outright — and one
uncovered arrival is enough.

**The refresh was also the wrong shape**, which the same rows show: the body was already
parked while the copy walked, so extending the lead pushes the copy *further* from a
stationary body and the eventual arrival fails gate 1 by more. **The quantity that kills
is the separation at the arrival, not the arrival's timing.** That is why a backstop built
to postpone it could not work, and it is the part §1z-ae got wrong at the design level
rather than in coverage.

### 1z-ag.4 The guard has the predicate and did not fire in time

> **CORRECTED by §1z-ah.2 (2026-09-03).** Both candidate reasons below are wrong,
> and the capture settles it without the live chain dump this section asks for: the
> guard reported `arrival-risk` at t=18.074, **0.425 s BEFORE** the 18.499 arrival --
> it was neither blind nor late -- and was refused by the report-freshness gate alone
> (last accepted report 2.311 s old against a 0.347 s ceiling, zero refusals since,
> previous re-pin 6.1 s back). This section's own draft said so before the merged text
> replaced it. §1z-ah builds the fix on that gate.

`agtrack_guard.arrival_risk` asks exactly the right question — is an arrival maturing
within the horizon whose evaluation predicts a snap. On this capture it **did not fire
before the snap**. The wire shows the fatal lead evaluated `agtrack_guard pass match` at
−1.918 s, and the first `arrival-risk` row lands at **+0.392 s, after the fact**.

Two candidate reasons, and the rows cannot separate them, so both are recorded rather than
chosen:

1. **The guard was blind through the window.** Its last state transition before the snap
   was `none / not-tested` — the code the mirror returns when it believes the fence is
   shut — and our own `AGTRACK RE-PIN` had shut it 5.7 s earlier.
2. **The `pass/match` may be an old-trail match**, which is the failure §1z-r.4 named
   outright (*"keep q within 100 u of the CURRENT leg — old history is deleted by
   invisible resets and is never protection"*). The body had walked forward through
   ≈9849 earlier in the run, and `AgTrack::Clear` zeroes the head **but the seed
   survives**, so the first node recorded after a Clear forms a segment with a stale seed
   that can span the whole earlier leg. **UNVERIFIED** — it needs the mirror's chain
   dumped at that instant, not inferred from a verdict word.

Either way the practical statement is the same and it is measured: **the guard cleared the
lead that armed the lock, and reported the risk only after the body had already moved.**

### 1z-ag.5 The derived fix, named not built

An arrival is harmless when separation is small — that is §1z-r's reprieve and the whole
basis of zero-lead's warp-safety. So the action before a maturing lead is **not to extend
it but to retract the copy to the body's own reported point**, which is exactly the
zero-lead grant §1z-y's kill already sends on a press or a click. It needs one more
trigger: *an arrival is due and the modelled separation exceeds gate 1*. A grant and not a
`0x002C`, for the reason §1z-y already gives — a `0x002C`'s own Clear shuts the fence.

That is a change with its own registered run, and §1z-ag.4 says the predicate it should
use needs auditing first: a fix hung on `arrival_risk` inherits whatever kept
`arrival_risk` quiet here.

### 1z-ag.6 The instrument, honestly

**The capture failed `movetap`'s own sample-rate floor** — 613 samples over 60 s = 10.2 Hz
against a 50 Hz target, floor 1500 — and it said so and refused to certify itself:
*"It stalled; do not read a null out of it."* Nothing above is a null. The snap is a
positive event captured in two consecutive samples; the arrival instant is the client's
own `+0x48`; the parked-body check is a velocity field, not a rate; and the ±1.5 s wire
window comes from the gamesrv capture, whose timing the tap's rate cannot affect. What the
undersampling costs is **resolution and completeness**: the shut is located inside
`[17730, 17831]` rather than at an instant, and **other fence transitions could have been
missed between samples**. The client's own world clock advanced 51.5 s over 60 s of wall
time — it was running ~14 % slow — which is worth knowing before anyone reads a timing
figure off this capture, and is the likely cause of the tap's own shortfall.

**And the shortfall is reproducible, which makes it an instrument limitation rather than a
fluke.** A second capture, started at the map rung so it covered the whole walk, read
**575 samples over 48 s = 12.0 Hz** and failed the same floor. Two attempts, 10.2 and
12.0 Hz, against a reader that measured itself at ~14 kHz capability beforehand: on this
machine `movetap` cannot hold 50 Hz while the harness is driving the client. Closing that
is the next instrument job, and until it is closed **no `movetap` capture taken under the
harness can be certified** — which is why everything above is stated as a positive
observation and nothing as a null.

### 1z-ag.7 The second capture is a WITHIN-ARM CONTROL, and it separates the two routes

`movetap-20260903T202916` × `authsrv-20260903T202912-c1`, identical script and flags.
**That run did not lock: 7 reported stops for 7 key legs** (run A: 1), 31 heading reports
(run A: 12). Its only open→shut transition is a different animal:

| | run A — LOCKED | run B — CLEAN |
|---|---|---|
| what shut the fence | the lead's **arrival** (`+0x48` due inside the sample gap) | **no arrival armed at all** (`+0x48` = 0 both sides) |
| separation at the shut | **518 u**, over gate 1 | **96.8 u**, under it |
| the body at the shut | parked, then moved **520 u** onto our dest | moving, then stopped; moved **3.5 u** |
| plane words | equal (29 = 29) | **disagree — sync 0, drawn 29** |
| re-armed afterwards | **never**, 46 s | **yes, 3.8 s later** |
| reported stops | 1 of 7 | 7 of 7 |

Both of §0.11's ingredients are visible in this arm and they do not carry the same weight:
**the plane-mismatch shut self-heals** — it re-armed at the next walk-start, exactly as
§1z-aa measured — while **the arrival-across-gate-1 shut never re-arms and takes the
session with it.** That is the route to fix, and it is also why the same script locks in
some runs and not others.

**One thing this obliges me to withdraw.** I registered that the plane words would already
be equal because §1z-z matches field 4 to field 3, and in run B **the client's two copies
disagreed anyway** (sync 0, drawn 29). Matching the words *in our grant* does not make the
client's two copies agree — the drawn body can cross a seam while the sync copy has not
been re-granted. §1z-z is not thereby broken (its own test pins what it does), but
“§1z-z removes the cross-plane state” is not a claim these runs support, and §1z-af
leaned on it when it ruled the plane route out.


---

## 1z-ah. THE RETRACT, BUILT — the guard predicted the snap 0.43 s early and one gate refused it; a body MEASURED stationary lifts that gate, and the arrival never matures

**Asked:** "do the retract fix." §1z-ag.5 named it — *"before a maturing lead whose modelled
separation exceeds gate 1, **retract** the copy to the body's reported point — §1z-y's kill
with a third trigger, **a grant and not a `0x002C`**… Its predicate needs auditing first."*
The audit was done first, as that sentence asked, and it changed **both** halves of it: the
primitive is the `0x002C` and not the grant, and the predicate was never the problem.
Ident `MOVECODE-1z-ah`.

### 1z-ah.1 The primitive, adjudicated against the mirror

Run A's fatal leg replayed through `agtrack_mirror` — the instrument §1z-r validated against
every warp in the corpus. Each candidate retract aims at the same place, the body's own
reported point:

| candidate | separation when it fires | its own delivery verdict |
|---|---|---|
| `0x0029` at maturation | 520.0 u (RED) | **SNAP** |
| `0x0029` in RED | 378.7 u (RED) | **SNAP** |
| `0x0029` early | 227.2 u (yellow) | nomatch-pass — safe |
| `0x002C` at maturation | 520.0 u (RED) | not-tested — safe, fence shuts |

**§1z-ag.5's grant is refuted by §1z-s.1 clause 3, on this leg.** *"RED — separation ≥
299.332591 u: ANY evaluation snaps — **including the evaluation triggered by the grant that
tries to fix it**… No `0x0029` recovers from red."* A retract grant does not move `q`: the
bake settles `+0x78` where the copy already is and re-aims only the destination, so its own
bake-tail dispatch tests the 520 u separation and snaps. The grant is safe only *early*, and
the modelled separation crosses gate 1 at **t0+1.05 s** while the arrival is at t0+2.735 s —
so "before a maturing lead" and "while a `0x0029` still works" are 1.7 s apart, not the same
moment.

**And an early grant cannot be triggered on separation either.** The sync copy and a walking
body advance together, so a separation-threshold retract fires on every held-key cruise chord
over the threshold — reintroducing exactly the lag the lead exists to remove. The timing
trigger fares no better: §1z-ae.1's photo finish (report at 512 u, arrival at 520 u, **8 u =
0.03 s apart, narrower than one tick**) means no tick-polled margin can sit between them.
That is the same wall the refresh hit, and it is why this section does not ship another
pre-emption of the arrival.

### 1z-ah.2 ★ §1z-ag.4 is CORRECTED — the guard was neither blind nor late

§1z-ag.4 recorded that `arrival_risk` *"did not fire before the snap"*, offered two candidate
reasons (a mirror that believed the fence shut; an old-trail match off a surviving seed) and
chose neither, marking it UNVERIFIED. **Both candidates are wrong, and the capture says so
without a replay.** From `authsrv-20260903T202121-c1`:

| | |
|---|---|
| fatal leg armed | t=15.764, 520 u backpedal at 190.08 u/s → arrival **t=18.499** |
| the guard's row | t=**18.074** — `agtrack_repin code=blocked why=arrival-risk` |
| so the risk was seen | **0.425 s BEFORE the arrival**, not after it |
| last accepted report | t=15.763, age at that tick **2.311 s** |
| the ceiling | `REPIN_MAX_REPORT_AGE` = `R_MATCH`/`RUN_SPEED` = 100/288 = **0.347 s** |
| refused reports since | **0** — so not `rejects` |
| previous re-pin | t=11.966, **6.1 s** back — so not the rate |

**The predicate was right and one gate stood in front of it: the report-freshness gate, and
nothing else.** §1z-ag.4's own draft had this (*"its preconditions refused it… the gap
§1z-ab.5b filed as latent"*) and the merged text replaced it with the two-candidate account.
The `KBD_SYNC` block had already written the same thing down: *"the guard's clause 2 models a
keyboard body as parked, so it predicts a snap at every maturing lead **and is blocked only by
`REPIN_MAX_REPORT_AGE`**."* Three documents knew; none of them acted, because the row said
`blocked` and did not say by what. It does now (§1z-ah.6).

### 1z-ah.3 Why that gate may NOT simply be opened

A `0x002C` is not sync-only. Its handler `0x005FDA50` Clears the record first, then
SetPositions the **sync** twin (`AgMsg.cpp` 579) **and the async** twin (`AgMsg.cpp` 584) —
*"both copies land on the same point"* (`studies/movement/FINDINGS.md`:3246). So re-pinning a
**silently walking** body back to a stale report drags the drawn body with it, and that is not
hypothetical in this repo: an earlier build sent five, *"three were arrivals, carrying the
client 630, 189 and 765 units"*, removed as **the warp the player described**. `RUN_SPEED ×
age` is precisely the bound that prevents that recurrence, and **on age alone the gate must
stand.**

### 1z-ah.4 ★ THE DISCRIMINATOR — two identical reports are a MEASUREMENT, not an assumption

The gate bounds *how far the body may have walked since it last spoke*. That bound is a
worst case over a silent client. But when the **last two accepted reports carry the same
point** to within the client's own zero-distance radius (`ZERO_DIST_SQ` = 1.0, the bake's own
short-circuit), the body did not move across that interval **at all** — that is not a guess
about a silent client, it is two measurements of a still one. A stationary body's next
movement produces a walk-start `0x003D` (§1z-aa: 7 of 8), so while nothing new has arrived it
is still standing there, and the harm bound for re-pinning **onto** it is `ZERO_DIST_SQ`
rather than `RUN_SPEED × age`. The gate then has nothing left to protect.

**A walking body can never satisfy it**: its consecutive reports sit ~512 u apart, the
client's own `0x003D` distance trigger. Run A is the specimen — the parked body reported
`(10369.4169921875, 8282.3349609375)` **bit-identical three times** (t=11.892 / 14.028 /
15.763) while the lead walked the sync copy 520 u away from it.

Refused outright while a click is gliding the copy (`async_dest`), because then the report is
not where the body is. Refused on a placement, which is where *we* put the agent rather than
the client telling us twice — section 9's own existing stale-report check caught the looser
first draft and is the reason this is two **reports** and not two positions.

### 1z-ah.5 What it does to the leg that armed the lock

`STATIONARY_WAIVER`, ON, `--no-repin-stationary-waiver` reverts. Measured on run A's leg:

| arm | `arrival_risk` | re-pin | `blocked_by` |
|---|---|---|---|
| waiver OFF (what ran in run A) | **True, SNAP** | blocked | **stale-report** |
| waiver ON (the new default) | True, SNAP | **due** | — |
| waiver ON, body WALKING (known-bad) | **False** | none | — |

The re-pin lands at `(10369.42, 8282.33)` — where the body is standing — for a measured harm
of **0.000 u**. After it, `t_arrive = 0` and `dest = None`: **the 520 u arrival that armed
REALFIX §0.11 stage 1 never matures**, and the sync copy sits 0.000 u from the body, well
inside gate 1's 299.33. The known-bad arm is stronger than required: a walking body's sync
copy tracks it, so no snap is predicted and the re-pin is never even proposed — the warp of
§1z-ah.3 cannot be reached by this path at all.

### 1z-ah.6 What else changed, and the residual

- **A `0x002C` now clears the keyboard leg record.** By the same decoded argument the
  `ac_queue` clear beside it already rests on: `0x00602B20`'s armed arm reaches the teleport
  primitive `0x006020B0`, which clears the arrival tick at `0x006021E6`. The client will never
  mature that lead, so a leg left armed would let the kill, the refresh or the watchdog act on
  a leg that no longer exists — the stale-arrival defect by a third door.
- **The row names the blocker** (`blocked_by`: `no-report` / `rejects` / `stale-report` /
  `rate` / `unseeded`). §1z-ag had to replay a capture to learn which gate refused, and
  published two wrong explanations before asking it directly. A guard nobody can see
  not-firing is a wish.
- **THE RESIDUAL, stated rather than discovered later: the retract shuts the fence.**
  §1z-ag.5's reason for preferring a grant is true — a `0x002C`'s Clear closes AgTrack until
  the next walk-start. The trade is deliberate: a **bounded** shut window against a
  **permanent** lock, and the window is already the shipped AGTRACK RE-PIN's own behaviour
  rather than a new hazard. Three things bound it: §1z-aa's gate degrades any lead computed
  while `fence_shut_at` is set; the heading arm is report-driven, so no grant is sent between
  the re-pin and the next report; and the fence re-arms at that report if it is a walk-start
  (§1z-aa, 7 of 8). What this does **not** do is re-open §1z-aa's CONTESTED re-arm rule.

### 1z-ah.7 Tests, and the registered prediction

`test_agtrack_guard.py` 49 → **71 checks (floor 71)**: the waiver ships ON with its revert
flag; the predicate over one report, two identical reports, the 1.0 u boundary (which
*counts* — the client's own `distSq <= 1.0`), 1.1 u (which does not), a refused report, a
placement, and a click in flight; run A replayed on both arms with the blocker named and the
harm measured at 0.000 u; the arrival proven not to fire through the window that snapped in
the capture; the known-bad walking arm; the rate and the rejects still biting under the
waiver; and the `0x002C` leg clear. `test_kbdsync` 106, `test_d1lead` 94,
`test_position_trust` 235, `test_router` 114, `test_cancelwalk` 124, `test_playerswing` 116,
`test_guards` 41, `test_grantsim` 86, `test_srclint` 26, `test_bareimport` 8 — green.

**REGISTERED BEFORE ANY RUN.** The next `--kbd-lead` run should show, in the gamesrv rows:
`agtrack_repin code=due why=arrival-risk` where run A logged `blocked` / `blocked_by`
`stale-report`; an `AGTRACK RE-PIN 0x002C` at a point within 1 u of the preceding report;
`kbd_leg act=clear by=0x002C` beside it; and the reported-stop count for keyboard legs back
near 1:1 rather than run A's 1 of 7. **REFUTED IF** the lock still arms with the re-pin
firing, or if a re-pin fires at a point more than 1 u from the body's last report (the harm
bound is the whole safety argument), or if the operator sees any backward yank — which would
mean a walking body reached the waiver and §1z-ah.4's discriminator is wrong.

**Not settled.** The lead stays OPT-IN: this removes the armer §1z-ag identified, it does not
re-argue §1z-t.6's separation counterfactual. And the run itself is the verdict — §1z-af is
the standing reminder that a derived backstop can be convicted by its own two verification
runs. `movetap` still cannot certify a capture taken under the harness (§1z-ag.6), so the
score for this one comes from the gamesrv rows and the operator, not from the tap.


---

## 1z-ai. RUN-1zAH RAN — the retract fires, lands on the body for 0.0 u and never at a moved one; the OUTCOME clause refuted, and the run's own exposure census says why it could not have settled it

**Asked:** "set up the --kbd-lead run", then "go ahead and drive it." Four runs, arms
alternating T C T C, RUN-1zAB's script and build verbatim with one variable changed.
Agent-driven, hands off, ~90 s each. Ident `MOVECODE-1z-ai`.

### 1z-ai.1 The mechanism: CONFIRMED, and the harm bound held absolutely

| run | arm | stops / 7 key legs | legs armed | parked | retracts | travel |
|---|---|---|---|---|---|---|
| T1 | waiver **ON** | 7/7 | 32 | **0** | 3 | 5,894 u |
| C1 | OFF | 7/7 | 25 | 2 | 0 | 3,514 u |
| T2 | waiver **ON** | 7/7 | 33 | **1** | 1 | 4,727 u |
| C2 | OFF | **1/7** | **7** | **5** | 0 | **773 u** |

Every row §1z-ah.7 registered appeared. Four retracts fired, all in arm T
(`code=due why=arrival-risk` at T1 18.10 / 30.31 / 40.49 and T2 30.27) exactly where arm C
logged `code=blocked blocked_by=stale-report` — **the `blocked_by` field added for this run
naming its own gate, live.**

**THE HARM BOUND, which is the whole safety argument: every fired retract read
`prev_d = 0.0 u` and `next_d = 0.0 u`.** The body had not moved a unit across the two
reports that licensed the retract, and the next accepted report landed exactly on the point
we pinned to. Zero violations across four runs, on a checker that reads 0 over the
1,262-capture corpus and goes red with exit 1 on a synthetic. **And it refused correctly
live**: T1's 10.46 s arrival-risk stayed `blocked / stale-report` with the waiver ON,
because the body had moved.

### 1z-ai.2 ★ The OUTCOME clause fired, and the bar does not move

RUN-1zAH §2b registered: *"REFUTES — arm T locks (ENSLAVED, or a held-key leg moving ≤ 50 u,
or stops ≪ legs) on a run where a retract fired."* **T2 fired a retract and had a held-key
leg that moved 0 u in 4.0 s. That is REFUTED by the sheet's own words and is recorded as
refuted.**

**What the rows also show, as analysis and explicitly not as a rescue.** T2's parked leg
cannot be the mechanism under test: its lead was **zero-length** (armed 15.71 s,
`dest = (10368.68, 8281.62)` against a report of `(10368.7, 8281.6)` — a grant to the point
the body already occupied), the guard logged **no `arrival-risk` row at all** in that window
(correctly — with no separation nothing is predicted to snap), and it follows the
`gate2-offmesh` AGTRACK RE-PIN that fires at **≈11.9 s in all four runs, both arms**. So the
clause caught a different defect from the one it was written for. **That is a flaw in the
pre-registration**, and the fix belongs in a new registration rather than a re-reading of
this one.

**The persistent lock is a different object from "a parked leg"** and the run separates
them cleanly. Run A's signature is a fence that never re-arms: 1 stop of 7, ~7 legs armed
instead of ~30, every later leg parked. **C2 reproduces it exactly** (1/7, 7 legs, 5 parked,
773 u, plus 5 leads degraded `fence-shut` by §1z-aa's gate). **Neither arm-T run produced
it**, and T2's single parked leg recovered on the next leg (1,014 u). n = 2 per arm.

### 1z-ai.3 ★ THE EXPOSURE CENSUS — the floor counted the wrong thing

RUN-1zAH §3 required "≥ 8 `KBD LEAD` grants" and every run cleared it (25–33 fired). The
`lead_clip_why` census says what those grants were:

| run | `clear` (full 520 u) | `clipped` | `origin-unwalkable` (zero-length) | `fence-shut` |
|---|---|---|---|---|
| T1 | **4** | 18 | 10 | 0 |
| C1 | **4** | 11 | 10 | 0 |
| T2 | **2** | 16 | 15 | 0 |
| C2 | **2** | 4 | 1 | 5 |

**Only 2–4 leads per run survive the clip at full length** — 26 of T1's 32 legs and 27 of
T2's 33 carried ≤ 1 u after clipping, because on this route the client's reported position
sits off our navmesh repeatedly (ROUTER-B3's origin-unwalkable door, working as designed).
The arm under test is *a 520 u lead maturing*, so **the run had a quarter of the exposure
its floor claimed**. A floor that counts lead grants does not measure it; it must count
leads that survive `a2_clip_lead`. This is the defect class the floor exists to prevent,
committed by the floor itself.

### 1z-ai.4 One instrument defect, caught by the run

`capture_flags` swept companion policy modules with `sys.modules.get`, and the guard is
imported **lazily at character placement — after the header row is written**. So the header
recorded the waiver only in the arm that passed `--no-repin-stationary-waiver`, whose own
resolution imports the module early: **the A/B could name its flag in the reverted arm
only**, the worst half to be able to identify. Now a real `__import__` (both modules are
stdlib-only, so the bare-machine path is untouched). Fixed after the campaign rather than
during it, so all four runs share one binary.

### 1z-ai.5 Where this leaves it

**The mechanism is confirmed and safe; the outcome is not confirmed.** The waiver converts
exactly the blocked re-pins it was derived to convert, lands them on a stationary body for
0.0 u, and never fires at a moved one. It has **not** been shown to prevent the lock: arm T
avoided the persistent lock twice and arm C hit it once, but at 2–4 maturing leads per run
with n = 2 that is a direction, not a result.

**`--kbd-lead` stays OFF. The waiver stays ON** — additive, bounded at 1 u by measurement,
and its refutation would be a violation row, of which there are none in four runs or in the
corpus.

**What a next run needs, registered here so it is not re-derived:** an exposure floor
counted in **unclipped** leads (`lead_clip_why == "clear"`), a route that produces them —
the current one spends most of its leads on off-mesh origins — and a REFUTES clause that
names the **persistent** lock (stops ≪ legs, no re-arm) rather than any parked leg, since
those turn out to be two different objects with two different causes.


---

## 1z-aj. RUN-1zAJ RAN — the exposure defect is FIXED (floor met 4/4, clear leads 2–4 → 9–14), seven more retracts all at 0.0 u, and the run is **INCONCLUSIVE** because the control never produced the defect

**Asked:** "fix the exposure floor and rerun on a route with unclipped leads." Both done,
then four runs T C T C. Captures `authsrv-20260903T222122 / 222324 / 222522 / 222719-c1`
with their taps. Ident `MOVECODE-1z-aj`.

### 1z-aj.1 The two repairs, and they worked

**The floor now counts leads that survive `a2_clip_lead`** (`gatecensus.py`, floor 8).
Pointed at RUN-1zAH's own captures it reads `UNDER FLOOR (4)` — the defect §1z-ai found,
now caught automatically.

**The route was the problem, not the map.** `leadroute.py` (new) scores a mesh with the
server's own test — `walkable(origin)`, then `clip(origin → origin + 520·u)` at the same
2.0 u step. Around map 146's spawn: **0–300 u is 0 % off-mesh at a mean 13.6/16 clear
headings**; 400–500 u is 8 % off; 700–900 u is 25 %. RUN-1zAH's script ranged to 2,091 u
and its own reports read 26 % and 48 % origin-off-mesh. The new script oscillates — every
forward leg answered by a backpedal — and stays inside ~300 u.

| | RUN-1zAH | RUN-1zAJ |
|---|---|---|
| clear (full 520 u) leads per run | **2, 4, 4, 2** | **9, 14, 11, 13** |
| `origin-unwalkable` per run | 10, 10, 15, 1 | **1, 2, 0, 3** |
| floor verdict | UNDER FLOOR ×4 | **MET ×4** |

Predicted 8–12 before the run; measured 9–14. The desk model of the mesh was right.

### 1z-aj.2 The mechanism, again and more of it

| run | arm | reports | stop-echoes | legs armed | retracts |
|---|---|---|---|---|---|
| J-T1 | waiver ON | 32 | 12 | 19 | **4** |
| J-C1 | OFF | 37 | 12 | 25 | 0 |
| J-T2 | waiver ON | 30 | 12 | 18 | **3** |
| J-C2 | OFF | 36 | 12 | 24 | 0 |

**Seven more retracts, every one `prev_d = 0.0 u`, zero violations.** The arms mirror each
other exactly: arm C logged `blocked / stale-report` at 9.4 / 39.4 / 46.5 s and 9.4 / 39.4 s,
and arm T converted the same events at 39.4 / 46.5 and 29.2 / 39.3. **And the waiver
refused correctly in arm T too** — the 9.4 s row stayed `blocked / stale-report` in *both*
arm-T runs, because the body had moved there. Running total across both sheets:
**11 retracts, 0 violations**, on a checker that reads 0 across 1,262 captures and exits 1
on a synthetic.

### 1z-aj.3 ★ INCONCLUSIVE — the control never produced the defect

**All four runs are healthy: 12 stop-echoes for 13 movement legs, in every one.** No
persistent lock anywhere — not in arm C, which is what the run needed. RUN-1zAJ §2
registered this outcome in advance: *"INCONCLUSIVE — … arm C never locks (the regime did
not produce the defect)."* So it is inconclusive, and the clean arm T is **not** evidence
the fix works.

**Why, and it was derived before the run rather than after.** §1zAJ §2 registered: *"more
clear leads buy more TRIALS, not better odds per lead… a `clear` lead means our mesh says
nothing stops the body for 520 u, so a freely walking body covers its 512 u report trigger
and re-aims before the arrival."* That is exactly what happened. The oscillating script
made leads full-length **and** made every leg end in a reported stop, which kills the lead
by design (§1z-y). **The two requirements are in tension: the geometry that lets a lead
reach 520 u is the same geometry that lets the body keep walking and re-aim it.** Run A's
lock needed a body parked *while its key was held* on a ray our mesh called clear — our
mesh and the client's collision disagreeing — and that is not something a route can
schedule.

### 1z-aj.4 Two observations, recorded not scored

- **The `D:1` turn-in-place leg is flagged `HELD KEY, BODY PARKED` in all four runs.** A
  and D turn without translating — the scorer's own table header says so — so 0 u is
  correct there and the flag is a false positive on turn keys. It would have tripped
  RUN-1zAH's old REFUTES clause in every run of both arms, which is a second, independent
  reason §1z-aj's narrowing to the *persistent* lock was necessary.
- **J-T2 has one leg reading `ENSLAVED 100.0 %` while travelling 360.6 u of a 380 u free
  walk.** Normal travel, neighbours FREE, no lock. That is §1z-ac's bit-identity test
  firing on a co-directional leg: our granted lead pointed where the body was already
  going. Not a refutation under the registered clause, and recorded here because a
  100 % leg that is not a lock is exactly the reading a later session would misquote.
- **Arm T arms fewer legs than arm C** (18–19 against 24–25) and takes fewer reports. That
  is the retract's own `0x002C` clearing `kbd_leg` (§1z-ah.6) and shutting the fence
  briefly — expected, and the cost side of the trade that section stated.

### 1z-aj.5 Where this leaves it

**The exposure instrument is fixed and proven** — floor met 4/4, and it retro-flags
RUN-1zAH. **The mechanism has 11 firings and no violation.** **The outcome is still
unmeasured**, and after two sheets the reason is structural rather than procedural: this
harness route cannot reliably manufacture "a full-length lead over a parked body", because
on a clear ray the body does not park.

> **REFUTED by §1z-al (2026-09-04).** The enemy's collision cannot park a keyboard body at
> all: the resolver's park arm is gated on the blocker being `+0x98`, a walking player's
> `+0x98` is 0 (0 of 3,032 moving samples), the drawn body passes within **4.8 u** of the
> Hatcher at full speed, and the lead's own `0x0029` clears `+0x98` anyway. The paragraph
> below is kept as written because it is what the next step WAS.

**What a next attempt needs is not another route.** It needs the parking to be caused
rather than waited for — the `--enemy` Hatcher's collision blocking the body mid-leg is the
one mechanism in this harness that stops a walking body without our mesh knowing, and it is
already in every run. Scoring which legs ran into it, and whether the body's stall is what
run A's fatal leg had, is the derived next step. `--kbd-lead` stays OFF; the waiver stays
ON.

---

## 1z-ak. PRESS ENDS THE WALK NEEDS NO HARM BOUND — its payload is a MODEL of the body, not the stale report `repincheck` scores it against, and the drawn body's own tape puts every pin within 6.9 u

**Asked:** RUN-1zAH's sweep incidentally lit up a second `0x002C` sender — *"does
`PRESS ENDS THE WALK` have a harm bound at all, and does it need one?"* Answer: **it does
not need one**, and the reason is structural rather than lucky. No client run; the corpus
already held both instruments. Ident `MOVECODE-1z-ak`.

### 1z-ak.1 What the sweep actually surfaced, counted honestly

`repincheck.py --all` over the corpus (now **1,270** captures): **108 × `0x002C`, 0
violations** — §1z-ah's waiver still clean. `PRESS ENDS THE WALK` appears **14 times in
exactly 2 captures** (`authsrv-20260902T140659-c1` ×4, `authsrv-20260903T084616-c1` ×10);
it is a young arm, shipped 09-02.

Re-scoring the press arm by the re-pin's own licensing rule today reads **5** would-be
violations, **all inside the 08:46 capture** — last accepted report 5.57/7.61/9.01/12.11/
**13.48 s** stale, with the previous two accepted reports **12.7 u** apart (a body that was
moving when it last spoke). `146218d`'s registration noted **7** on that day's
1,262-capture corpus; today's re-sweep of the same rule finds 5, in the same single
capture, with the same ages and the same 12.7 u report pair. The count is not reproducible
across the two sweeps and **nothing here rests on it** — the harm is what was measured, not
the tally. The other capture's 4 pins all fire *before its first accepted report*, so they
have no age and no `prev_d` at all.

### 1z-ak.2 ★ `age` and `prev_d` are the wrong instrument for this arm — it never sends the report

The re-pin's two gates are harm predictors **because `AGTRACK RE-PIN`'s payload is
`client_pos` verbatim**: it puts the client's own last accepted report back on the wire, so
"how stale is that report" and "was the body moving when it last spoke" bound exactly how
far the body may have walked away from the point being sent.

**`PRESS ENDS THE WALK` sends a different thing.** `_press_supersedes` (`authsrv.py:11400`)
puts `_click_leg_start(state, now, silent=True)` on the wire — the click leg **lerped to the
instant of the press**, i.e. the server's model of where the body is *now* — and then calls
`_forget_client_position(state, "press superseded the click leg")` in the same breath. The
stale report is not the payload; it is the thing this sender **drops**. That asymmetry is
already written down as the rule at `_forget_client_position`'s docstring (*"THE POINT'S
SOURCE decides… a `0x002C` at a point OUR MODEL computed CONTRADICTS the last report, so
forget it; a `0x002C` at THE REPORT ITSELF agrees with it, so keep it"*), and it sorts these
two senders onto opposite sides.

The 08:46 numbers make it concrete: the last accepted report is at t=24.156 s, `(9913,
7961)`. The five "stale" pins fire at 29.7–37.6 s at `(9633,8309)`, `(9568,8311)`,
`(9543,8392)`, `(9518,8250)`, `(9536,8313)` — **446 to 568 u away from that report.** The
pin is nowhere near the report whose age is being scored. Judging it by `age`/`prev_d` is
the same category error as scoring a `RESYNC` by a click's licensing rule. **The quantity
that matters is `|pin − the DRAWN body|`**, because `0x002C`'s handler `0x005FDA50`
SetPositions the async twin too (`AgMsg.cpp` 584) — that is the whole reason §1z-ah.3 would
not open the freshness gate on age.

### 1z-ak.3 ★ THE MEASUREMENT — the drawn body, read out of the client, at every press pin

The wire cannot see the rendered body, so this is a join to the `agenttap` tape: the async
(world-1) copy of agent 1 through the client's own `AgAgent::position_at` accessor, clamp
included (`w0score.live`). **`authsrv-20260903T084616-c1` is the only capture in the corpus
carrying both press pins and a tape spanning them** — `agenttap-20260903T084632`, 220
samples, tape `t0` = capture wall + 16.295 s (the same offset ANIMREF-RE §41 derived
independently, 16.296). Two instruments that share nothing: the server's leg model, and
`ReadProcessMemory` on the client's own agent block.

| capture t | pin | drawn body at the press | **residual** | next drawn sample |
|---|---|---|---|---|
| 16.421 | (9951,7975) | (9951,7975) | **0.0** | 0.0 u from pin |
| 19.421 | (9894,8148) | (9894,8148) | **0.0** | 0.0 |
| 21.055 | (9884,8089) | (9884,8089) | **0.0** | 23.6 (walked on) |
| **21.860** | (9941,8193) | (9935,8197), **v = 289 u/s** | **6.9** | **0.0 — reached the pin 30 ms later** |
| 22.508 | (9992,8016) | (9992,8016) | **0.0** | 0.0 |
| 29.730 | (9633,8309) | (9633,8309) | **0.0** | 15.4 (walked on) |
| 31.767 | (9568,8311) | (9568,8311) | **0.0** | 0.0 |
| 33.166 | (9543,8392) | (9543,8392) | **0.0** | 0.0 |
| 36.269 | (9518,8250) | (9518,8250) | **0.0** | 12.7 (walked on) |
| 37.638 | (9536,8313) | (9536,8313) | **0.0** | 0.0 |

**10 of 10 scored. Worst residual 6.9 u. Nine of ten are 0.0 u.** OBSERVED. The five
"stale" rows — the ones the re-pin rule would have convicted, at ages to 13.5 s — are
**0.0 u every one**. The client's own reprieve radius is `R_MATCH` = 100 u; the worst pin
here is **1/14th of it**.

**The one moving case is the informative one.** At 21.860 the drawn body was mid-walk
(v = (213, −194), 289 u/s) and the pin sat 6.9 u away — **ahead of it along its own path**:
the next tape sample, 30 ms later, has the body *at* the pin. (§1z-ak.7 bounds this one:
the tape runs at 9.1 Hz effective, ~31 u of travel per sample, so for a MOVING body read
“within a sample of the body's path” rather than 6.9 u to the unit. The nine parked
readings carry no such error.) That is a forward nudge of
one frame's travel, not a backward yank. **No pin in the set moved the body backward.**

**Why this is not luck.** The leg model is built to track the body: ANIMREF-RE §37.5
measured **10 of 10 post-click reports within 3.5 u of the modelled end** on open ground and
stated its three error terms with their directions. This tape is that claim checked from the
other side — against the rendered body rather than the next report — and it holds.

### 1z-ak.4 The verdict, and what a bound would have cost

**`PRESS ENDS THE WALK` already carries the strongest bound available to it**: it pins to a
model of the body's current position and discards the stale report, where the re-pin pins to
the report and therefore needs `RUN_SPEED × age` to bound it. Adding a freshness gate to
this arm would gate it on the staleness of a fact it does not use — and would **refuse the
five pins that measured 0.0 u of harm**, i.e. it would break the press response (ANIMREF-RE
§39's whole point: a press must end the walk *now*, 12–32 ms) to protect against a warp the
tape says is not there. **No bound. No flag. No code change.** §1z-ah.3's warp (*"630, 189
and 765 units"*) came from a sender that put **our integrator's** position on the wire while
the client had not moved; this one puts a model of the body on the wire *at the instant the
client's own click leg is being cancelled*, and the body is measured to be there.

**Residual, stated rather than discovered later.** The 08:46 specimen is an open-ground
click kite, which is §37.5's *good* case. A **bent path** is the untested geometry: the model
is a straight-line lerp, so a bowed client path puts the pin off the arc by the bow, and a
press mid-bend truncates to the segment waypoint (§37.5 names both, with directions). That
error is bounded by the leg's own length and self-corrects at the next report, and **n = 0**
here — it is not evidence of harm, it is the cell this capture could not fill. **FILLED by §1z-ak.6 (2026-09-04): the bow error is real and exceeds `R_MATCH`, and it belongs to the `--no-router` / `--router-raw-leg` revert flags rather than to the shipped default.** The other
press capture (`140659`, CASE 6) has **no tape partner**, so its 4 pins are unmeasured by
this instrument; §39.6 already scored them on the operator's own screen (*"all three worked
as intended"*, no jump). **TAKEN UP in §1z-ak.7 (2026-09-04): three of the four are cleared
without a tape by the LEG-AGE bound — which turns out to be `REPIN_MAX_REPORT_AGE` on the
leg clock — and the fourth is uncertified, not harmed.**

### 1z-ak.5 What was built

- **`studies/movecode/review/pressharm.py`** — the join above, re-runnable. Prints the
  per-pin residual against the drawn body, flags anything over `R_MATCH`, and **exits 1 on
  zero exposure** (a capture with press pins but no tape scores nothing, and that is not a
  pass — §1z-ai's lesson). Currently: 10 of 10 scored, worst 6.9 u, exit 0.
- **`repincheck.py`'s SCOPE comment now records that the exemption was CHECKED**, in both
  the docstring and at the branch that skips the sender — with the reason (the payload is a
  model, not the report) and the number (0.0–6.9 u). It was previously left as *"their own
  question"*, which is how an unexamined exemption becomes a permanent one.
- **`repincheck.py` is deliberately NOT extended to score this sender.** Its rule is the
  waiver's licensing rule and does not apply here; the right check for this arm needs the
  drawn body, which is a different instrument on a different input. Two rules in one scorer
  is how the first draft read 7 violations that were never violations.

### 1z-ak.6 ★ THE BENT-PATH CELL, FILLED — the bow error is real and over `R_MATCH`, and it belongs to the REVERT FLAGS, not to the shipped default

§1z-ak.4 left one cell empty and named it: the specimen was an open-ground click kite, so
a **bent** path — one the client must walk around — was `n = 0`. Filled here by derivation
(`studies/movecode/review/bentbound.py`), because the corpus cannot fill it by observation
and the geometry can answer it at the desk. No client run.

**First, why the corpus cannot fill it, checked rather than assumed.** Every one of the
08:46 session's clicks was scored against map 146's mesh with the server's own test
(`walkable(origin)` then `clip(origin → dest)` at the lead clip's 2.0 u step):
**0 of 37 chords are bent — every one clips clean.** That is not luck, it is where the
operator stands: at the session's own click lengths (53–276 u) **0 of 496**
(origin, heading) pairs over the 31 drawn-body positions of that session are bent, rising
to only **15 of 452 (3.3%)** at 300–500 u. §1z-ak's measurement was taken in a regime with
**zero bent exposure**, which is exactly why it could not speak to this.

> **A confound this section walked into first, recorded so the next reader does not.** A
> bend detector built on the body's own path — traversed length against the chord — flags
> two legs in that tape at bow 1.54 and 1.65. **Both are false.** The window opens at the
> click, and the body is still turning off its *previous* heading for the first ~150 ms, so
> a click-induced **corner** reads as a bow. The mesh is the instrument that separates
> them, and it says neither leg had anything to walk around.

**Second, the size of the error, and it is not the bow.** `_click_leg_arm` records a
straight leg and `_click_leg_start` lerps it at 288 u/s; the body walks the **route** at
288 u/s. Both advance on the same clock, so at time *t* the model sits at arclength 288*t*
along the **chord** while the body sits at 288*t* along the **longer route** — the error is
lateral **and along-track, because the model runs ahead on the shorter path**, and it is
larger than the bow alone. `max_t |chord(288t) − route(288t)|` is the worst residual a
press pin could carry on that leg. **Positive control: a clear chord's route IS the chord,
and the harness returns 0.000 u on 60 of them** — it invents no error on a straight walk.

| bow (route/chord) | n | p50 | p90 | max | over `R_MATCH` |
|---|---|---|---|---|---|
| 1.00–1.25 — a rock / a corner | 135 | 40.6 u | 107.8 u | 164.9 u | **19 of 135** |
| 1.25–2.00 — a real detour | 78 | 174.6 u | 298.4 u | 401.9 u | 71 of 78 |
| 2.00–5.00 — around a building | 90 | 464.3 u | 906.5 u | 1118.8 u | 89 of 90 |
| 5.00+ — around the mountain | 97 | 1112.3 u | 3090.8 u | 11825.4 u | 97 of 97 |

**The headline is the MILDEST band and the tail is deliberately not quoted.** Even at
bow < 1.25 — a rock, not a mountain — **19 of 135 exceed the client's own 100 u reprieve
radius**. Pooling the four bands would produce a p50 of 212 u, and that number is about the
sampler rather than about the game; the 73× bow at the top is a random walkable point on
the far side of terrain, which is a click a player can make but not one this repo should
build a headline on. RECONSTRUCTION: our mesh, our `route()` (A* + string-pull), **not the
client's pathfinder**. Mild bows are geometry and travel well; the extreme tail may be our
connectivity decode as much as the world.

**Third, and this is the finding: the bow error is not the shipped default's.** The 08:46
capture ran **`ROUTER: False`** — its flags row says so — so the click-leg record was the
**raw chord**, which is the regime the table above describes. Under the current default
`ROUTER_LEG_REARM` re-aims that record at the **routed** leg (`_router_rearm_leg`, at the
first waypoint and again at each chain leg), so `_click_leg_start` lerps **a segment of the
route the body is actually walking** and the bow term is gone by construction. §1z-v built
that flag for exactly this reader, and its comment names it: *"Every reader of the record —
`PRESS ENDS THE WALK`'s `0x002C` at the modelled body… would place the body on a straight
line the client is not walking."* **This section is the size of the thing that comment was
protecting against**, measured: up to 164.9 u at bow < 1.25, and past `R_MATCH` in 14% of
even that band.

**What this does and does not change.**

- **§1z-ak's verdict STANDS for the shipped default.** No bound, no flag, no code change.
  The 0.0–6.9 u measurement is valid where it was taken, and under `ROUTER` the bow term it
  never exercised cannot arise.
- **It becomes a stated cost of two revert flags.** `--no-router` and `--router-raw-leg`
  restore the raw-chord record, and on bent geometry a press pin under them can place the
  drawn body **past the client's own forgiveness radius**. Those flags exist for
  diagnostics (§1z-v: *"the diagnostic arms the composition matrix refuses beside the
  router need it"*), so this is a composition hazard to read before reaching for one, not a
  defect in anything shipped.
- **It is still `n = 0` OBSERVED.** No bent press pin has ever been captured with a tape
  over it. The table is derived; what would settle it is one run on `--no-router` with a
  route that has something to walk around and an `agenttap` tape — and there is no reason
  to spend an operator run on a regime we do not ship.

### 1z-ak.7 ★ THE 140659 PINS — a `0x002C` cannot audit itself, but two of the four are provable anyway, and the bound turns out to be `REPIN_MAX_REPORT_AGE` on the LEG clock

§1z-ak.4 left the CASE 6 capture's four pins *"unmeasured by this instrument"* because it
has **no tape partner**. Taken up here. Three of the four are cleared without one, the
fourth is not, and the argument that clears them names a bound this arm was already
carrying and nobody had written down.

**First, why the wire can never do it, and this is the general statement.** A `0x002C`
**is self-fulfilling**: its handler SetPositions *both* copies onto the payload, so from
the instant it lands the body **is** where we pinned it, and every later report describes
the **post-pin** body. `next_d` — the distance from the pin to the next accepted report —
therefore measures where the body went *after* we put it there, never how far we moved it.
That is why `repincheck` prints `next_d` as context and never as a verdict, why §1z-ak
needed an out-of-band reader of the client's memory, and why **no amount of wire data can
audit a pin**. On this capture the first accepted report arrives at **t = 39.987**, after
all four pins (14.727 / 19.299 / 31.162 / 35.681); the client is silent for the first 40 s.

**Second, two origins ARE provable, and the arithmetic checks against the wire.** The
payload is `p0 + 288·dt` along the click chord. Where `p0` can be established from the
capture alone, the pin is reproducible:

| pin | its leg's origin `p0` | why that origin is certain | model | the wire's pin |
|---|---|---|---|---|
| 14.727 | **the spawn**, `(9826.0, 8077.0)` | `INSTANCE_LOAD_SPAWN_POINT`, and **no movement command of any kind precedes it** — the click at 14.412 is the session's first, so the body had never left the spawn | (9877.06, 8002.02) | **(9877, 8002)** |
| 19.299 | **pin 1's own point** | pin 1 set *both* copies there and cleared movement; **no movement command falls between** 14.727 and the click at 19.000, so the body was parked on it | (9959.37, 7976.70) | **(9959, 7977)** |

Both reproduce the emitted payload exactly. The self-fulfilling property that makes a pin
un-auditable is the same property that makes the *next* one provable: **a pin establishes
the position its successor's leg starts from.**

**Third, the bound — and it is a constant this arm already had.** On a **clear** chord from
an **exact** origin the body walks that same line, and its own travel lies in
`[0, 288·dt]`, so `|model − body| ≤ 288·dt`, attained only if the body never started at
all. And `288·dt` reaches `R_MATCH` at

> `dt = 100 / 288 = 0.347 s` — **`REPIN_MAX_REPORT_AGE`**, the very constant that gates the
> `AGTRACK RE-PIN`, read on the **leg** clock instead of the **report** clock.

Not a coincidence: both are `R_MATCH / RUN_SPEED`, and both answer the one question — *how
far can the body have moved since the last thing we know for certain.* The re-pin's
certainty is a client report; the press pin's is its leg origin. **`PRESS ENDS THE WALK`
was never unbounded; its bound is the age of the leg it lerps, and this is where that gets
written down.**

**All seven click chords in this capture are CLEAR** on map 146's mesh (checked with the
server's own `walkable` + `clip`), so §1z-ak.6's bow term does not apply here either.

| pin | leg age | bound | origin | verdict |
|---|---|---|---|---|
| 14.727 | 0.315 s | **≤ 90.8 u** | **provable** (spawn) | **CLEARED** — under `R_MATCH` whatever the body did |
| 19.299 | 0.299 s | **≤ 86.1 u** | **provable** (pin 1) | **CLEARED** |
| 31.162 | 0.235 s | **≤ 67.5 u** | chained (4 click legs, no report) | cleared *by age*; its origin carries its own error |
| 35.681 | **1.084 s** | **≤ 312.2 u** | approach-armed leg | **UNCERTIFIED — over `R_MATCH`** |

**The fourth pin is the one this capture cannot rule out, and "uncertified" is not
"harmed".** Its leg is 1.084 s old — three times the 0.347 s limit — and its origin comes
from the approach's own follow leg, dead-reckoned through 40 s of client silence. The bound
only says the wire cannot exclude a correction past `R_MATCH`; the body walking its chord
normally puts the real residual near zero. The only evidence that bears on it is the one
§39.6 already recorded, and it is the right instrument for a visible warp: this is Q6b #2 of
the operator's own CASE 6 run, and the operator's verdict was **"all three worked as
intended"**, no jump.

**What would actually produce the bad case is already named.** `288·dt` is attained only if
the body **stopped mid-leg without our knowing**, and the one mechanism in this harness that
does that is the `--enemy` Hatcher's collision — which was chasing and nibbling throughout
this very capture, and which §1z-aj.5 independently nominated as the next thing to cause
rather than wait for. That is a hypothesis this section does not test, recorded because the
two arcs meet here.

**An instrument debt, stated because it bounds §1z-ak.3 too.** The 08:46 tape asks for 30 Hz
in its header and delivers **9.1 Hz effective** (220 samples over 24.3 s; gap p50 109 ms,
max 220 ms) — **~31 u of body travel per sample at run speed**. An attempt to measure the
click **start transient** off it (does the body really cover `288·dt` in the first 0.3 s?)
produced two artifact populations and no signal: apparent travel of 23 u in 10 ms, which is
the client starting **before the server sees the click** (one network hop), and a body
reading 0.0 u for 250 ms then the whole chord at once, which is `position_at`'s **arrival
clamp** returning `m_segmentPoint`. **No transient number is published from it.**
Consequently §1z-ak.3's single **moving** specimen (6.9 u) carries roughly one sample
interval of uncertainty — it is honestly *"within a sample of the body's path"* rather than
6.9 u to the unit. **The nine 0.0 u readings are unaffected**: those bodies were parked
(`v = 0`, `stop = 0`) and stable across neighbouring samples, where there is no sampling
error, and the headline — nothing near `R_MATCH`, no pin moving the body backward — stands
on them.

**`pressharm.py` now carries both arms.** With a tape it measures against the drawn body;
without one it falls back to the leg-age bound, prints the origin caveat, and **exits
non-zero on an uncertified pin** — so a capture like this one reports "1 pin not cleared"
rather than the flattering "unmeasured" it used to. Run on 140659 it exits 1 and names
35.681.

---

## 1z-al. THE ENEMY CANNOT CAUSE THE PARKING — the resolver's park arm is gated on `+0x98`, the lead's own `0x0029` clears it, and the drawn body walks through the Hatcher at 4.8 u

**Asked:** "now cause the parking with the enemy collision" — §1z-aj.5's derived next step,
in its own words: *"the parking must be CAUSED, not waited for — the `--enemy` Hatcher's
collision blocking the body mid-leg is the one mechanism in this harness that stops a
walking body without our mesh knowing."* **That plan is REFUTED, at the desk, with no
client run.** Ident `MOVECODE-1z-al`.

### 1z-al.1 The gate is `+0x98`, and it was in the decode all along

The collision resolver `0x006011F0` runs its neighbour test for every agent in a ±60°
forward cone, but the arm that actually stops the body — the kind-5 arrival and the
teleport-in-place (`0x006020B0`: velocity 0, `m_targetPoint` ← +INF, `+0x48` ← 0) — fires
**only when the blocking neighbour IS the agent named in `+0x98`**:
`0x006017CB cmp ebx,[esi+0x98]` (ANIMREF-RE §38.2). `+0x98` is the *destination agent* — who
this body is FOLLOWING. **A keyboard or click walk carries `+0x98 = 0`.** There is no
followed agent, so the arm cannot fire no matter who is standing in the way. The resolver is
a **follow-arrival** mechanism, not a physical barrier.

### 1z-al.2 ★ And the lead's own opcode clears the field the park needs

This is the part that makes it structural rather than merely unlikely. `0x002A`'s handler
passes the wire's fifth field into the shared setter's `+0x98` slot; **`0x0029`'s handler
`0x005FD890` passes 0 into that same slot** — so a `0x0029` CLEARS the follow (§38.2,
answering §35.5's open decode). **The keyboard lead IS a `0x0029`.** Every lead grant
destroys the precondition the park requires, so "a maturing lead" and "a body parked by the
enemy" are **mutually exclusive by construction**, not two things that merely failed to
co-occur. No route, no script and no enemy placement can hold both at once.

### 1z-al.3 The corpus agrees, and it is not close

`studies/movecode/review/collisionpark.py` over all **17 agenttap tapes, 9,852 paired
samples** (both copies of the player and the Hatcher, read through the client's own
`position_at`):

| | |
|---|---|
| player moving samples | **3,032** |
| … with the drawn copy's `+0x98` set | **0** (sync copy: 4) |
| moving samples **inside** the 80 u disc | **636 of 3,032 (21.0%)** |
| closest approach at speed | **4.8 u**, player at 190.1 u/s, `+0x98 = 0` |

Twelve passes come inside 17 u at full run speed with no deflection, no velocity change and
no stop. **If the disc blocked a keyboard body, none of those 636 samples could exist.**
OBSERVED.

### 1z-al.4 ★ THE POSITIVE CONTROL — the resolver does fire, for the agent that carries `+0x98`

A negative this large is worthless without showing the same reader finding the thing it
should find (the standing rule; §1z-ak.6's own harness earned its numbers the same way). The
**Hatcher** chases the player, so *its* `+0x98` names agent 1, and the resolver must be
visible stopping it at `r + r + 56` = 80 u:

| | |
|---|---|
| Hatcher samples with `+0x98` set | **2,538 of 9,852 (25.8%)** |
| Hatcher halts (was > 100 u/s, now < 20) | **432** |
| distance to the player at the halt | p10 68.3, **p50 84.5**, p90 194.0 |
| inside the 60–100 u band (the disc) | **267 of 432 (62%)** |

**The mechanism works and the reader sees it.** It fires for the agent that names a target
and never for the one that does not. That is the gate, measured from both sides.

> **A false start recorded, because it is the trap this section nearly published.** The
> corpus does hold 29 player stalls in the 65–90 u band, clustered near 75 u, which reads
> exactly like an 80 u collision stop. It is not one: `+0x98` is **0 on both copies for the
> five samples BEFORE each stall**, so nothing was being followed. Those are the **Hatcher's
> own** 80 u chase-halt (ANIMREF-RE §40) seen from the player's frame — the enemy settles at
> its disc whenever the player stops, so the *separation* clusters at 80 u without the
> player ever being stopped by anything. A distance histogram alone would have "confirmed"
> the collision park; only the `+0x98` column refutes it.

### 1z-al.5 What this retires, and what is actually left

- **§1z-aj.5's next step is dead as written.** Its premise — *"the one mechanism in this
  harness that stops a walking body without our mesh knowing"* — is wrong on its own terms:
  the enemy does not stop the walking body **at all**. Nothing about the route, the script
  or the enemy's placement can be adjusted to fix that; the field the mechanism needs is
  zeroed by the very grant under test.
- **The retract's outcome question is therefore still open, and this closes a door rather
  than opening one.** §1z-aj left it INCONCLUSIVE because the control never produced the
  lock, and the proposed way to force it does not exist.
- **What remains, from the arc's own record, and this section does not choose between
  them.** (a) §1z-aj.3's other candidate — *"our mesh and the client's collision
  disagreeing"* — **ANSWERED in §1z-ao.5: the lead's ray crosses a plane-29 → plane-0 seam
  and `pm.clip` is plane-blind, so the server scored it CLEAR and the client would not walk
  it** —, i.e. terrain or a prop the client stops on where our mesh says clear; the
  lead needs `clip()` to pass, so only a **disagreement** can serve, and whether one exists
  is a question about our own decode's gaps. (b) §1z-ad's specimen, where the armer was not
  a parked body at all but a **swallowed `0x0047`** — **taken up in §1z-am, which confirms the
  swallow at frame level and REFUTES the maturation as its cause** — the lead matured 0.26 s before the
  player released and the release went unreported. These are different mechanisms and the
  arc has been treating them as one. Picking between them is the next decision; **it is not
  a run, and after this section it is not an enemy.**

**No code changed. `--kbd-lead` stays OFF; the waiver stays ON.**

---

## 1z-am. THE SWALLOWED `0x0047` — the client really never sends it, the lock is visible from the wire alone, and §1z-ad's "the lead matured" is REFUTED as the cause

**Asked:** "now do the swallowed `0x0047`" — the second of §1z-al.5's two remaining
candidates. Answered from the corpus; no client run, no code change. Ident
`MOVECODE-1z-am`.

### 1z-am.1 The fact, established at the frame level rather than the decoded one

§1z-ad said the release "is swallowed". That was read off the decoded rows, which cannot
distinguish *"the client did not send it"* from *"we did not parse it"* or *"we refused
it"*. Checked directly on `authsrv-20260903T191320-c1`: the c2s **frame** opcodes, taken
from each frame's own plaintext before any handler runs, are
`0x8009` ×13, `0x803d` ×12, `0x80c1` ×6, **`0x8047` ×1**, and one each of `0x800a /
0x800d / 0x8090 / 0x808a / 0x8008`. The four `unhandled` rows are all login-time
(`SEND_MACHINE_SPEC` and friends); there is no `Undecodable`, and no refused
`position_report`. **One `0x0047` frame exists in the whole 62 s session, against seven
key legs.** The client genuinely never sent the other six. OBSERVED, and now at the layer
that can tell the three cases apart.

### 1z-am.2 The denominator was wrong, and the first pass got a meaningless number

A corpus sweep comparing `0x0047` counts against `0x003D` counts reads a baseline ratio of
**0.15** and a lead-run ratio of **0.22** — and it means nothing, because `0x003D` fires on
every heading change, not once per leg. **The honest unit is the key leg**, and the harness
walk spec carries every press and release instant, so scripted runs can be scored exactly.
Two further controls the first pass lacked: a leg whose capture **ended** before a stop
could arrive is excluded rather than counted as a miss, and the rate is broken out per key:

| key | n | closed | | key | n | closed |
|---|---|---|---|---|---|---|
| W | 218 | **85%** | | Q | 21 | 67% |
| S | 143 | **92%** | | E | 21 | 67% |
| A | 4 | 0% | | D | 8 | 12% |

**A and D turn in place** — they translate nothing, so no stop is reported, and pooling them
with W/S would have manufactured a deficit out of the key layout. On **W/S legs only**:
lead-ON **74 of 97 (76%)**, lead-absent **244 of 264 (92%)**.

### 1z-am.3 ★ The signature is TERMINAL, not a rate — and it is readable from the wire alone

The 76%/92% gap is not the finding; the **shape** is. Healthy runs miss a leg here and there
and recover (`YYYYYYYY.YYYY`). A locked run reports a **prefix and then never again**:
`Y......`, `YYY....`. Scoring *trailing silence* — legs after the last closed one:

| | runs with ≥ 2 trailing silent legs |
|---|---|
| `KBD_SYNC_LEAD_ON` | **6 of 17** |
| lead flag absent | **0 of 32** |

Baseline runs never reach 2; their worst is exactly 1, which is the capture ending. **This
is a lock detector that needs no tape, no `movetap`, and no enslavement scorer** — three
instruments the arc has been leaning on, one of which cannot certify under the harness at
all (§1z-ag.6). It is a wire-only signature.

**Confound stated: the comparison is not clean.** Every lead-ON run uses the `WSWQESW` or
`WSWSQEWSDWSQE` script and every lead-absent run uses something else; **no lead-OFF run in
the corpus uses `WSWQESW`**, so script and flag are not separable here. What *is* clean is
the within-script variation — of the 11 lead runs on the identical `WSWQESW` script, build
and flags, **6 lock and 5 do not**, which is the coin flip §1z-ad described and does not
depend on the cross-script comparison.

### 1z-am.4 ★ THE REGISTERED TEST, AND IT REFUTED §1z-ad's CAUSE

§1z-ad named the mechanism: *"a lead matured while the key was still held"*, measured on one
run as maturing **0.26 s** before the release. Registered before computing anything:

> **PREDICTION.** The runs that go terminally silent are exactly those in which at least one
> clear-clipped lead's maturation instant — `t_arm + 520/speed`, both taken from the
> server's own `kbd_leg` row, **no free parameter** — falls before that leg's release.
> **REFUTED IF** a locking run has none, or a healthy run has one.

| | locked | healthy |
|---|---|---|
| an early maturation | **5** | **6** ← refutes |
| none | **1** ← refutes | 5 |

**Both refutation conditions fired.** Six healthy runs carry exactly the event §1z-ad
identified as the cause — `20260903T202542` has a lead maturing **1.24 s** before its S
release and reports all seven stops — and one locked run (`20260903T073055`) carries none at
all. **Maturation-before-release is neither necessary nor sufficient** for the swallowed
stop.

**What this does and does not overturn.** REALFIX §0.11 decodes the lock as **two** stages
and says in its own words *"neither alone suffices"* — a snap that clears `clientControlled`
(stage 1), composed with the click-walk regime in which *"releases are ignored, no `0x0047`
is emitted, and the keyboard walk-start applier — the only fence re-armer — never runs"*
(stage 2). **§0.11 is untouched by this and in fact predicted it.** What is refuted is
§1z-ad's framing of the maturation as *"the door"* — a single sufficient trigger — which is
how the arc has been quoting it since, including in §1z-al.5's own list of candidates. The
maturation supplies stage 1 and the corpus shows stage 1 alone doing nothing eleven times.

### 1z-am.5 A discriminator that looks perfect and is CIRCULAR

`lead_clip_why == "fence-shut"` separates the two groups almost exactly — locked runs read
0/4/2/2/5/5, healthy runs read 0 in ten of eleven. **It cannot be evidence, and it is
printed by the instrument with this warning so it is not re-discovered and believed.**
`fence_shut_at` is *our* flag, set by our own `0x002C` and cleared by a client walk-start
report; when the client stops reporting, the flag stops clearing. It is the same silence
read from the server's side — one theorem, two instruments (§1z-u's standing trap), not an
independent cause.

### 1z-am.6 What would settle it, and why it is not a run

The remaining question is stage 2's own gate: **what makes the client stop emitting
`0x0047` while it keeps emitting `0x003D`?** The locked runs are not silent — 12 `0x003D`
still arrive in `191320`, `mt` 7/8/4 — so this is a selective suppression of the *stop*
report, not a mute client. Two things would answer it and neither is another scripted run:

- **The fence dword itself — BUILT in §1z-an (2026-09-04), unverified against a live
  client until one run writes a tape.** `clientControlled` is what §0.11's account turns on, and
  `movetap`'s `fence_state` reads it — but **no `movetap` tape overlaps any of these runs**
  (the lead arm shipped after that campaign, the same gap §1z-aa hit), and `movetap` cannot
  certify under the harness anyway (§1z-ag.6, 10–12 Hz against a 50 Hz floor). Adding the
  dword to `agenttap`, which *does* run alongside these captures at 9 Hz, is the cheap
  version and is a tooling change rather than an experiment.
- **The client's `0x0047` sender.** `studies/movement/FINDINGS.md`:1160 already establishes
  it is **send-only — no receive handler in the agent table at all** — so it has never been
  located from the receive side, and `codescan`'s field/xref anchors do not reach a
  send-side opcode immediate. Finding it is its own dig, and it is the one thing that would
  read the gate directly rather than inferring it.

**No code changed. `--kbd-lead` stays OFF; the waiver stays ON.** Instrument:
`studies/movecode/review/stopcensus.py`.

---

## 1z-an. THE FENCE DWORD IS ON `agenttap` — movetap's reader CALLED not copied, a free negative control, and verified offline because `agtrack_fence` takes a closure

**Asked:** "now add the fence dword to agenttap" — the cheap half of §1z-am.6's two ways to
settle stage 2. Tooling, not a finding. Ident `MOVECODE-1z-an`. **`--no-fence` reverts.**

### 1z-an.1 Why here and not `movetap`

`clientControlled` — the dword at the agent's AgTrack record that the dispatcher's
`0x00606002` tests *before* the three-gate snap test runs at all — is the field REALFIX
§0.11's two-stage account turns on, and `movetap` has read it since §1z-aa. It cannot answer
the current question for two reasons already on file: **no `movetap` tape overlaps any lead
run** (the arm shipped after that campaign — §1z-aa hit the same gap), and `movetap` cannot
certify a capture taken under the harness at all (§1z-ag.6, 10–12 Hz against its own 50 Hz
floor). **`agenttap` already runs beside every one of these captures.** Putting the column
there costs a tooling change instead of a campaign.

### 1z-an.2 What was added, and what was deliberately *not* re-derived

**`movetap.agtrack_fence` is CALLED, not reimplemented** — same record walk, same bounds
checks (`state-array-null`, `state-count-implausible`, `id-out-of-bounds`,
`agent-id-mismatch`), same string sentinels. A drift in `OFF_AGTRACK` / `STATE_STRIDE` /
`S_CONTROLLED` therefore breaks **one** place, and `movetap --selftest` (250 checks, still
green) keeps owning them. Two things are this file's own:

- **`memo_reader`, a per-sample read memo.** `agtrack_fence` fetches the AgTrack header and
  the armed id on every call, and this tape calls it once per tapped agent — but those are
  per-*AgTrack*, not per-agent, so the second agent's copies are pure cost. That matters
  here in a way it does not in `movetap`: **this reader already delivers ~9 Hz of the 30 it
  asks for** (§1z-ak.7, gap p50 109 ms), so a wasted round trip is bought out of the sample
  rate the fence exists to explain. The memo is scoped to one sample and thrown away —
  a memo that outlived the sample would stamp a **stale fence with a fresh timestamp**,
  which is worse than not reading it, and the test drives that both ways.
- **The SYNC block is the one handed over.** The record is keyed by agent id, so the copy
  cannot change `clientControlled` — but it *does* change `gate_reach`, whose world term
  separates `test-runs` (world ≠ 1) from `world1:append`. **World 0 is the branch on which
  the test at `0x006055E0` is actually reached**, which is the question being asked.

### 1z-an.3 ★ The negative control is free, and it is the point

`0x00605F10` writes `clientControlled` from **exactly two callers, both in the ChCliBase
local-command block** — it is set for the LOCAL PLAYER's agent and nobody else. The tape
already polls the Hatcher, so **its record must read `shut` for the whole run**, and the
summary asserts that and says so loudly when it does not: an `open` there means this reader
is indexing the wrong record and the player's column is worth nothing. A negative control
that costs one agent we were already tapping is the cheapest kind there is, and this arc has
just spent two sections (§1z-al, §1z-am) on readings that only survived because a control
was run.

An `unread:` value is a **third thing** and must not trip that control — a fence that could
not be read is not a shut one. That is `movetap`'s own rule and the reason the state is a
string rather than a boolean; the test pins it.

### 1z-an.4 Verified offline, and exactly how far that goes

`toolkit/clientscan/test_agenttap.py`, **15 checks, floor 15, bare machine** — fake memory,
no client, no vault. That is possible only because `agtrack_fence` takes a `read(addr, n)`
closure, which is a design decision of `movetap`'s paying off two arcs later. The four
`gate_reach` branches through agenttap's own call shape; `clientControlled == 0` reading
`shut` and never a failure value; an unreadable AgTrack reading `unread:`; an id mismatch
refused; `read_copy`'s new `(fields, raw block)` return still refusing a short block and an
id mismatch; the Hatcher control **driven both ways, including the RED**; and an old
fence-less tape still summarising, which all 17 tapes in the vault are.

**Two things the test caught that a live run would have hidden.** The `(fields, block)`
change left the **success path still returning a bare dict** — every good sample would have
raised inside the poll loop, and a tape is only written at the end. And the floor was
**guessed at 17**; a green run produces 15, and `checks.Ledger` refused the guess rather
than passing 15 silently. Both are the failure shapes CLAUDE.md's own rules name.

**WHAT IT DOES NOT COVER — CLOSED the same day by §1z-an.6 (RUN-1zAN): the column READS, the
control is exceptionless and the rate cost is nil. The paragraph below is what was
outstanding before that run.** **The column is UNVERIFIED
against a live client.** No tape has been written with it. The offsets are `movetap`'s and
its selftest re-encodes each instruction from the constants, so the *addressing* is as good
as `movetap`'s; what is untested is that this process, on this build, reads a plausible
fence at run time — and **the sample-rate cost is unmeasured**. The memo bounds it to one
extra header read plus one record read per agent per sample, but "bounded" is not
"measured", and a reader already at 9 Hz is the wrong place to assume. **`--no-fence` exists
for exactly that**: if the column costs more rate than it is worth, the revert is one flag
and the tape goes back to what §1z-ak.7 measured.

### 1z-an.5 What it will answer

§1z-am left the question sharp: the client keeps emitting `0x003D` while suppressing only
`0x0047`, so this is a **selective suppression of the stop report, not a mute client**. With
this column a lead run's tape says, per sample, whether the player's fence was open or shut
and whether the snap test was reachable — which turns §0.11's stage 1 from an inference into
a reading, and puts the fence transition on the same clock as the missing stop. **One
ordinary scored `--kbd-lead` run writes it.** The other half of §1z-am.6 — the client's
send-only `0x0047` sender — is untouched and remains its own dig.

### 1z-an.6 ★ RUN-1zAN RAN — every registered clause CONFIRMED, and the wire corroborates the column to one sample

Driven 2026-09-04, agent-driven, hands off, one run arm T. Capture
`authsrv-20260904T103712-c1`, tape `agenttap-20260904T103713`, harness
`20260904T103636`, verdict PASS. `RUN-1zAN.md` registered the four predictions and
the abort before launching.

| registered | measured |
|---|---|
| **P1 — the Hatcher reads `shut` on 100%** | **680 of 680 `shut`.** Zero `open`, zero `unread:`. |
| **P2 — the player reads, not `unread:`** | **680 of 680 read: 581 `open`, 99 `shut`. Zero `unread:`.** |
| **P3 — at least one transition** | **three:** `shut→open` 6.79, `open→shut` 21.44, `shut→open` 23.91 |
| **P4 — within ~2× of 9.1 Hz** | **10.73 Hz** (680 samples / 63.4 s, gap p50 92 ms) |

Exposure floor met on all three clauses: 680 samples against a floor of 200, 680
non-`unread:` player samples against a floor of 1, and the capture reached the map.

**The negative control is the result that matters and it is exceptionless.** The
Hatcher's record read `shut` on every one of 680 samples while the player's read
`open` on 581 of them — from the *same* reader, the *same* AgTrack array, one
index apart. `0x00605F10`'s two local-command callers say only the local player's
agent is client-controlled, and that is now measured rather than inferred. A
reader on the wrong record could not produce that split.

**AND THE RATE COST IS NIL.** 10.73 Hz against the fence-less tapes' 9.1 Hz —
this run was *faster*, which is machine-load variance and **not** a speedup from
adding reads; what it establishes is that the fence read is nowhere near this
reader's bottleneck. `--no-fence` stays as the revert and has no reason to be used.

**★ THE CROSS-CHECK NOBODY REGISTERED, and it is the strongest thing in the run.**
The column can be checked against an instrument that shares nothing with it — the
wire. §1z-aa's rule is that a server `0x002C` shuts the fence and a keyboard
walk-start re-arms it:

| the wire | the client's own memory |
|---|---|
| the run's **only** `0x002C` (`AGTRACK RE-PIN`) at tape t **21.40** | fence `open → shut` at **21.44** — *one sample later* |
| the only walk-start `0x003D` in the window, tape t **23.97** | fence `shut → open` at **23.91** — *one sample earlier* |
| the server's own `fence` row: `rearm by=walk-start`, **`shut_for` 2.569 s** | the tape's shut window: **2.47 s** |

Both edges land within one 92 ms sample of the wire event that the decode says
causes them, and the two independent measurements of the shut window agree to
0.1 s. **This is §1z-aa's fence-shutter rule confirmed from the client's memory
for the `AGTRACK RE-PIN` sender — which §1z-aa itself could not test**, in its own
words: *"No movetap tape overlaps the two senders the item named."* 1 of 1 for the
shut and 1 of 1 for the walk-start re-arm; n = 1 each, and the point is the
agreement, not the count.

**What the run does NOT show, exactly as the sheet pre-registered.** It is
**healthy** — `stopcensus` reads `YYYYYYYY.YYYY`, 12 stops for 13 legs, no
terminal silence — so it carries **no evidence about the lock**, which §1z-am's
census already said would be the likely outcome on this route (the four sibling
`222xxx` runs read the same pattern). The instrument is verified; the question it
was built for still needs a run that locks, and §1z-am puts that at roughly 6 in
17 on the `WSWQESW` script rather than this one.

**The column ships verified. `--no-fence` reverts and is not recommended.**

---

## 1z-ao. RUN-1zAO CAUGHT THE LOCK WITH THE FENCE READING — all three clauses confirmed, and the discriminator is WHAT SHUT THE FENCE, not that it shut

**Asked:** "go after the lock." Four runs, arm C (`--no-repin-stationary-waiver`, the
known-bad revert, chosen to provoke), RUN-1zAH's `WSWQESW` script. Runs 1–3 healthy;
**run 4 LOCKED with a valid tape.** Registered in `RUN-1zAO.md` before launching. Ident
`MOVECODE-1z-ao`. **Specimen: capture `authsrv-20260904T110025-c1`, tape
`agenttap-20260904T110026`, harness `20260904T105954`.**

### 1z-ao.1 The three registered clauses, all CONFIRMED

`stopcensus` reads **`Y......`**, trailing silence 6 — leg 1 closed at 12.97, legs 2–7
never reported a stop. Tape valid: **637 samples, zero `unread:`, Hatcher control `shut`
637 of 637.**

| registered | measured |
|---|---|
| **P1** the fence SHUTS at or before the lock onset | shut at **17.67**; the onset is leg 2, whose release is **18.68** ✓ |
| **P2** it STAYS shut for the whole silent tail | **43.5 s, zero transitions**, final state `shut` ✓ |
| **P3** the healthy prefix shows a shut→open re-arm | shut **10.91** → re-armed **14.74** ✓ |

No refutation condition fired.

### 1z-ao.2 ★ The mechanism, observed whole in the client's own memory

Leg 2 is `S` (backpedal), pressed 14.68, released 18.68. From the tape, both copies of
the player:

| t | sync (world 0) | drawn body | separation | body v |
|---|---|---|---|---|
| 14.74 | starts walking the lead | **(10373, 8286)** | 19 u | **0.0** |
| 16.53 | walking | **unmoved** | **312 u — past gate 1 (299.33)** | **0.0** |
| 17.58 | walking | **unmoved** | **502 u** | **0.0** |
| **17.67** | **(9853, 8286)** | **(9853, 8286)** | **0.0** | 0.0 |
| 17.77 | walking | walking | 0.6 u | 190.1 |

**The drawn body did not move for 3.0 seconds while the key was held**, the sync copy
walked the granted 520 u lead away from it at 190.1 u/s, separation crossed gate 1 at
16.53 and reached 502 u — and at **17.67 the arrival fired and teleported the drawn body
520 u onto the granted point**, collapsing separation to 0.0 in one sample. **The fence
shut in that same sample**, and there is **no server `0x002C` anywhere near it** (the
run's `0x002C`s are at 10.91, 20.43 and 36.60).

The server's own arithmetic predicted the instant: the lead was armed at 14.71 at
speed 190.08, so it matures at `14.71 + 520/190.08 = ` **17.44** — **0.23 s before the
observed shut**, and **1.01 s before the key was released**. That is REALFIX §0.11
**stage 1 — "a snap whose dispatcher clears `clientControlled`" — observed directly, in
the client's memory, for the first time.**

### 1z-ao.3 ★★ THE DISCRIMINATOR: it is WHAT SHUT THE FENCE, not that it shut

Both kinds of shut occur **in this one run**, which is what makes the comparison clean:

| shut | cause | re-armed? |
|---|---|---|
| **10.91** | a server **`0x002C`** (`AGTRACK RE-PIN`, `gate2-offmesh`) — the tape's transition lands in the same sample as the send | **YES, at 14.74**, on the next walk-start. Bounded window: 3.8 s. |
| **17.67** | the client's **own arrival-snap**, no `0x002C` involved | **NO. Never, for 43.5 s.** |

**And the client kept reporting walk-starts the whole time.** After 17.67 it sent
`0x003D` at **17.71, 20.43, 27.15, 31.88, 36.60, 42.32** — one per remaining leg press —
and the fence stayed shut through all six. So §0.11 stage 2's *"the keyboard walk-start
applier — the only fence re-armer — never runs"* is **sharpened by measurement**: the
client goes on *reporting* walk-starts on the wire, and the fence still does not re-arm.
Whatever suppresses the re-arm does not suppress the `0x003D`, and it does suppress the
`0x0047`.

**This is the trade §1z-ah.6 stated as its residual, now measured on both sides** — *"a
bounded shut window against a permanent lock"*. The bounded one is ours; the permanent
one is the snap's.

### 1z-ao.4 Why §1z-am's maturation test failed, resolved

§1z-am refuted "a lead matured before the release" as the cause, on six healthy runs that
had exactly that event. This specimen shows why, and it is not a contradiction:
**maturation is necessary but not sufficient — it must produce a SNAP**, and a snap needs
the separation at the arrival past gate 1, which needs the drawn body to be **parked while
the sync copy walks**. In the healthy runs the body walks with the lead, separation stays
small, the arrival is a no-op. **§1z-ag said exactly this** — *"the quantity that kills is
the separation at the arrival, not its timing"* — and this is the direct observation of it.
§1z-am's refutation stands and §1z-ag's account absorbs it.

### 1z-ao.5 ★ WHY the body was parked — §1z-al.5's candidate (a), with a mechanism

The remaining question is why the drawn body refused to move for 3 s under a held key.
The lead's own geometry answers it, and the answer is in **our** mesh:

| | |
|---|---|
| the fatal lead | `(10373, 8286)` → `(9853, 8286)`, 520 u due west |
| our mesh, origin | walkable, and the planes it offers there are **[29]** |
| our mesh, destination | the planes it offers there are **[0]** |
| our mesh, the ray | `clip` shortfall **0.0 u — scored CLEAR at full 520 u** |
| the client | **did not walk it at all** |

**`pm.clip(x0, y0, x1, y1, step)` takes no plane argument — it is plane-blind by
construction**, and `a2_clip_lead` scores a lead with it. So the server granted a
full-length lead across a **plane-29 → plane-0 seam** that our mesh cannot see and the
client's body would not cross. That is **§1z-al.5's candidate (a) — *"our mesh and the
client's collision disagreeing"* — with a specific mechanism**, and it is the parking
that §1z-aj.5 wanted caused and §1z-al proved the enemy could not cause.

Corroboration, and its limit: once the snap put the body at `(9853, 8286)` — plane 0 —
it walked west immediately at 190.1 u/s. **FIXED in §1z-ap** (`A2_LEAD_PLANE_CLIP`, `--no-lead-plane-clip` reverts; the
same lead now clips to 14 u reading `plane-seam`, and the term retrodicts 6 of 6 locked
runs below gate 1). **RECONSTRUCTION**, not OBSERVED: the seam is
consistent with the refusal and our clip is provably plane-blind, but this run does not
show the client refusing *because* of the plane, and one specimen cannot exclude geometry
our mesh simply lacks.

### 1z-ao.6 What this run does and does not settle

- **The instrument did what it was built for.** The fence column turned §0.11 stage 1
  from an inference into a reading, and the discriminator in §1z-ao.3 was not visible from
  the wire at all — §1z-am's only fence signal was our own flag, and circular.
- **n = 1 locked specimen**, one route, one build, arm C. It can and did refute nothing;
  what it gives is a mechanism observed end to end and a named, testable cause for the
  parking.
- **The lock rate did not reproduce.** Today: **1 of 4** arm-C runs, against the corpus's
  6 of 10. Recorded rather than explained; four runs is a thin base either way and this
  campaign was sized to catch one specimen, not to estimate a rate.
- **Nothing shipped.** `--kbd-lead` stays OFF, the waiver stays ON, and the plane-blind
  clip is a **derived candidate defect, not a fix** — it needs its own section, and the
  obvious repair (a plane-aware clip) touches the routing path that §1z-o and §1z-v both
  have arms in.

---

## 1z-ap. THE PLANE-BLIND CLIP, FIXED — the lead's ray must stay on the report's own plane, and it retrodicts 6 of 6 locked runs

**Asked:** "fix the plane-blind clip." §1z-ao.5 named it from the specimen; this builds it,
behind one flag, with the known-bad arm in the test. Ident `MOVECODE-1z-ap`.
**`A2_LEAD_PLANE_CLIP` ON, `--no-lead-plane-clip` reverts.**

### 1z-ap.1 The defect, in one sentence of the mesh's own documentation

`PathingMap.walkable()` says what it does: *"Is this point inside any trapezoid, **on any
plane**?"* — and `clip()` was built on it. There is **no height in the pathing file**, so a
plane-29 trapezoid and a plane-0 trapezoid can occupy the same `(x, y)` and be different
physical places with no straight walk between them. A ray from a bridge to the ground
beneath it therefore scored **CLEAR at full length**. That is not a bug in `walkable` —
its contract is right for its own callers — it is a term `a2_clip_lead` never applied.

### 1z-ap.2 What it cost, measured rather than argued

RUN-1zAO's specimen (§1z-ao), scored through the shipped code on both arms:

| | `--no-lead-plane-clip` | shipped |
|---|---|---|
| the fatal lead `(10373,8286) → (9853,8286)` | **520.0 u, `why="clear"`** | **14.0 u, `why="plane-seam"`** |

At 520 u the sync copy walked away from a body that would not follow, separation crossed
gate 1 and reached 502 u, and the arrival warped the drawn body 520 u and shut AgTrack's
fence for good. At 14 u the ray cannot reach gate 1 at all, so **the arming event is
unreachable rather than merely less likely**.

### 1z-ap.3 ★ THE RETRODICTION — 6 of 6

Every locked run in the corpus, re-scored on map 146's mesh at the lead armed on its
**first silent leg** (the arming event), plane-blind against plane-aware:

| run | reach before | after | |
|---|---|---|---|
| `20260903T191246` | 520 u | **6 u** | prevented |
| `20260903T195857` | 520 u | **36 u** | prevented |
| `20260903T200549` | 520 u | **146 u** | prevented |
| `20260903T202051` | 520 u | **6 u** | prevented |
| `20260903T214957` | 520 u | **2 u** | prevented |
| `20260904T105954` (RUN-1zAO) | 520 u | **14 u** | prevented |

**6 of 6 fall below gate 1's 299.33 u**, every one on a plane-29 origin. The seventh
locked run, `20260903T073055`, had **no lead armed on its silent leg at all** — and it is
the same run §1z-am found had no early maturation either, the odd one out in both tests.
Consistent, and it says this fix does not explain that one.

### 1z-ap.4 What it does NOT do, which is most of the corpus

Re-scoring **464** keyboard leads: the plane term changes **36 (7.8%)**, and **all 36 are
`plane-seam`**. The other 92.2% come back bit-identical. That is the shape a fix should
have — it bites on the cross-seam rays and nowhere else — and the test pins it directly: a
same-plane clear ray is **bit-identical on both arms**, because a clip that perturbs
healthy grants by epsilon rewrites every one of them and the 222/222 word doctrine starts
matching floats the client never sent.

### 1z-ap.5 The build

- **`pathmap.clip(..., plane=None)`.** Default is the historical behaviour to the bit.
  Given a plane, a sample must also satisfy `plane_at(prefer=plane) == plane`. The term
  can only ever stop the walk **earlier**, never later, so it cannot lengthen a lead —
  the failure direction is a short grant, which the client is authoritative over anyway.
  Crossing surfaces is a **portal's** job (`adjacent()` walks them, `route()` searches
  them); a straight-line clip is not the place to model one.
- **`a2_clip_lead`** takes the plane from `plane_at(reported, prefer=state["plane"])` —
  the REPORT's own plane word, never `state["pos"]` (`--heading-grant`'s graveyard). When
  `plane_at` returns None it **refuses to guess** and the term is disabled, which is this
  site's existing no-mesh doctrine.
- **The row names the door.** A new `why` value, **`plane-seam`**, decided by whether the
  sample one step past the stop is still on the mesh: on the mesh means the ray left the
  *plane*, off it means the ordinary wall clip. This file already paid once for a clip
  whose row did not say which door opened (the P-17 press, `lead_clipped=false`).
- **The `plane=` kwarg is passed only when the term is in force**, so a stub or an older
  mesh object takes the historical call unchanged rather than raising inside the recv
  loop — caught by the test, not by a session.

**Tests.** `test_d1lead` **94 → 104, floor 104**, §2e, and it **drives the known-bad arm
first** so the shipped cell is known to measure the plane term and not the wall.
`test_kbdsync` 106, `test_router` 114, `test_pathmap` 80, `test_position_trust` 235,
`test_srclint` 26 — green.

### 1z-ap.6 What is NOT fixed, and it is deliberate

- **The ROUTER's clip is untouched.** It calls `pm.clip` without a plane, so click
  routing behaves exactly as before. The same seam is presumably there, but the router
  has arms in §1z-o and §1z-v and changing it in the same commit would mean a run
  convicts two terms (§29's rule). **Its own section.**
- **The fix is UNRUN — RUN IN §1z-aq the same day: the mechanism CONFIRMED live
  (0 of 65 arm-A leads cross a seam at gate 1 against 4 of 62 in the known-bad arm),
  the outcome still open (no lock in EITHER arm).** Every number below is a desk
  re-score of captured leads; no
  client has been driven with `A2_LEAD_PLANE_CLIP` on. The retrodiction is strong —
  6 of 6, on the exact leads that armed the observed locks — but retrodiction is not a
  run, and §1z-af is the standing reminder that a derived backstop can be convicted by
  its own verification runs.
- **`--kbd-lead` stays OFF.** This removes an armer; it does not re-argue the lead.
- **RECONSTRUCTION stands where §1z-ao.5 put it.** That the client refused *because* of
  the plane is still inferred: the seam is consistent with the refusal and the clip is
  provably plane-blind, but no run has shown the client's own reason.

---

## 1z-aq. RUN-1zAQ — the plane clip FIRES LIVE and the door is shut: 0 of 65 against 4 of 62, and the known-bad arm reproduced the defect

**Asked:** "run it." §1z-ap was a desk fix and §1z-af is the standing reminder that a
derived backstop can be convicted by its own verification runs. Four runs, alternating
**B, A, B, A**, `--no-lead-plane-clip` the only variable, `--no-repin-stationary-waiver`
held ON in both arms. Registered in `RUN-1zAQ.md` before launching. Ident
`MOVECODE-1z-aq`. **All three powered predictions PASS.**

### 1z-aq.1 The result

| run | arm | leads | `plane-seam` | **cross-seam ≥ gate 1** | lock |
|---|---|---|---|---|---|
| `115542` | **B (off)** | 32 | 0 | **3** | no |
| `115725` | **A (on)** | 31 | **1** | **0** | no |
| `115909` | **B (off)** | 30 | 0 | **1** | no |
| `120055` | **A (on)** | 34 | **2** | **0** | no |
| | **A total** | **65** | **3** | **0** | 0/2 |
| | **B total** | **62** | 0 | **4** | 0/2 |

- **P1 EXPOSURE — PASS.** Both arm-A runs met the seam; the route exercises the fix.
- **P2 THE FIX — PASS.** **Zero** of 65 arm-A leads reach gate 1 across a plane change.
- **P3 THE CONTROL — PASS, and this is what makes P2 mean anything.** The known-bad arm
  produced **4** such leads, every one at the full **520 u reading `why="clear"`** — the
  §1z-ap defect, reproduced live on demand. Two ran **plane 29 → 0** and two **plane
  0 → 29**, so the seam is crossed in both directions and the term catches both.
- All four tapes valid: **Hatcher control `shut` on 100%** (645–660 samples each), zero
  `unread:`. No abort.

### 1z-aq.2 ★ And it does not perturb the healthy grants — confirmed live, not just at the desk

Arm A's `maxreach` is still **520 u**: full-length leads go on being granted where the ray
stays on one plane. Of 65 leads only **3** were clipped by the term. That is §1z-ap.4's
7.8% desk figure holding up in front of a client — the fix bites on cross-seam rays and
nowhere else, which is the property that matters more than the fix working at all. A clip
that shortened healthy grants would have rewritten every one of them and broken the
222/222 word doctrine on floats the client never sent.

### 1z-aq.3 What this run does NOT show, as pre-registered

**No lock occurred in either arm — including the known-bad one — so this run set carries
NO evidence about the outcome.** That was registered as P4's explicit weakness before
launching: the lock is per-RUN and probabilistic at a measured **1 in 4** (§1z-ao), so two
runs per arm expect **0.5** locks in arm B and 0 of 2 is entirely ordinary. **A reader
must not take "arm A did not lock" as the fix working** — arm B did not lock either.

**The run was powered for the MECHANISM and the mechanism is what it settled**: the fix
fires, the door is shut on this seam, and the arm without it re-opens the door on demand.
Whether closing that door prevents the lock is the outcome question, and it needs either
many more runs at a 1-in-4 rate or — better, and in this arc's own idiom — a route chosen
to make the arming event frequent rather than incidental.

### 1z-aq.4 What stands

- **§1z-ap ships confirmed at the mechanism level.** `A2_LEAD_PLANE_CLIP` stays ON;
  `--no-lead-plane-clip` reverts and now has a measured cost — 4 full-length cross-seam
  grants in 62 leads.
- **`--kbd-lead` stays OFF.** This removed an armer; it did not re-argue the lead.
- **The ROUTER's clip is still plane-blind and was not under test** (§1z-ap.6) — **TAKEN
  UP in §1z-ar: plane-blind for CERTAIN, harmful UNMEASURED, NOTHING SHIPPED, and the
  last of three desk instruments was refuted by its own positive control.** Arm B's
  0 → 29 crossings say the seam is not a one-way curiosity, which makes the router's own
  section worth writing.
- **One map, one route, one build**, and the seam met is the plane-29 structure this route
  happens to cross. P2 says the door is shut on THIS seam, not that no plane-blind grant
  survives anywhere.

---

## 1z-ar. THE ROUTER'S CLIP — plane-blind for certain, harmful UNMEASURED, and NOTHING SHIPPED: three desk instruments, the last refuted by its own control

**Asked:** "now do the router's clip" — the residual §1z-ap.6 named. **No code change
beyond a comment.** Ident `MOVECODE-1z-ar`. This section is mostly a record of
measurements that did not hold up, which is why it exists.

### 1z-ar.1 What is CERTAIN, from the code

The router's A* walks `adjacent()`, which **does** respect planes and portals. The
**string pull** then drops any waypoint the previous one can "see", and its visibility
test is `_visible` → `_sightline`, whose own docstring says it *"answers exactly
`clip(x0, y0, x1, y1) == (x1, y1)`"* — **plane-blind**. `route()`'s final gate calls
plane-blind `clip` as well. So **the pull can in principle undo the A*'s plane
discipline, and neither the pull nor the gate would notice.** That is a code fact and
needs no measurement.

The lead had exactly this shape and it cost a 520 u warp (§1z-ap). The question is
whether the router's version ever fires.

### 1z-ar.2 What is NOT established — three attempts, and why none of them counts

| attempt | result | why it does not count |
|---|---|---|
| **(a)** count pulled segments whose two planes are **never portal-linked anywhere on the map** | 6 of 144 (4.2%) | a **lower bound only**: a pair linked *somewhere* can still be shortcut *here*, so the 138 "linked" crossings may hide more |
| **(b)** compare the plane sequence before and after the pull | "the pull removed a transition on **14%** of routes" | the sequence was **my reconstruction** (`plane_at(prefer=…)` chained), not the router's own labels — it oscillates on stacked geometry, so this measures my reconstruction's instability |
| **(c)** for each plane-changing segment, does **any point on it carry both planes**? | **78.4%** are "discontinuities" | **REFUTED BY ITS OWN POSITIVE CONTROL** — see below |

**★ The control is the finding.** (c) looked authoritative: it used `route(with_planes=True)`'s
own plane labels and asked a purely geometric question. So it was pointed at 300 cross-plane
links the router itself asserts in `_cross`, and asked to find both planes at their meeting
point. **It found 92 of 300 — 31%.** A test that misses **69% of the portals it is told
about** cannot be believed when it reports finding nothing, and 78.4% is therefore a
statement about the test.

**And the miss explains itself:** at a plane-39 trapezoid's centre, only plane 39 is
present — plane 0 is not, though `_cross` links them. **Portal-linked trapezoids do NOT
reliably overlap in 2D.** `_shared_edge`'s *"the same physical place on two planes"* reads
as 2D coincidence and is not one, so "is this plane change legitimate?" **cannot be answered
by sampling the segment at all.** Every approach above was built on that assumption.

### 1z-ar.3 And there is no observed harm to anchor on

The lead had a specimen: a captured run where the drawn body demonstrably did not move on a
granted ray (§1z-ao). **The router has none.** It shipped default-ON at §1z-v, and the
campaign since is `--walk` keyboard-only — no clicks, so **no router grants at all** in the
runs that carry tapes. The corpus cannot answer this either.

### 1z-ar.4 Decision: NOTHING SHIPS

A router plane term now would be **a fix justified by a confounded measurement**, which is
the failure this repo has already paid for once. The `clip(plane=)` machinery exists and is
tested (§1z-ap); wiring it into `_visible` is a two-line change **and it stays unwritten
until something says it is needed.** The direction of error matters too: over-clipping the
ROUTER shortens click paths for every player on every map, where over-clipping a keyboard
lead only shortens a lead the client is authoritative over anyway.

**What was written instead:** the plane-blindness is now **named at `_visible`**, with the
control's 31% and the "portal links are not 2D overlaps" fact, so the next reader does not
re-derive this from scratch or, worse, ship the two-line change on a desk number.

### 1z-ar.5 What would settle it, and it is not another desk pass

**The same move that settled the lead: a client run with a tape over it.** A click route
with `ROUTER` on, crossing the plane-29 structure this map has, and `agenttap` reading
whether any routed leg leaves the drawn body parked while the server thinks it is walking.
That is an observation of the client's own behaviour and does not need the portal question
answered at all — which is exactly why it is the right instrument.

**§1z-as took up the first of these and calibrated the click verb; it also found the
BIND — the geometry that forces a route is the bridge whose PROP eats the click, so the
probe still needs one owner-aimed click or a different map.** Two things to fix first,
both cheap: **the harness drives keys, not clicks**, so a router
run needs a click script (`--walk` cannot produce one), and the plane-29 structure needs a
route that actually crosses it.

### 1z-ar.6 An honest property of the SHIPPED lead fix, found on the way

Since portal-linked trapezoids do not reliably overlap in 2D, `plane_at(prefer=)` flips at
the plane boundary whether or not a portal is there — so **§1z-ap's lead clip stops at ANY
plane change, including a legitimate portal crossing.** It is more conservative than
strictly necessary: a lead whose ray genuinely passes through a portal is now clipped short.

**That is the safe direction and the fix stands** — the failure mode is a shorter grant,
which the client is authoritative over, and RUN-1zAQ measured the cost at **3 of 65 leads**
with full-length grants otherwise unaffected. Recorded because "clips at plane changes" and
"clips at illegitimate plane changes" are different claims, and §1z-ap's text should not be
read as the second. RUN-1zAO's own 29 → 0 seam **is** portal-linked somewhere on the map;
the portal simply was not on that ray, which is why clipping it was right.

---

## 1z-as. THE CLICK SCRIPT — calibrated, and it hits the bind: the geometry that forces a route is the geometry whose PROP eats the click

**Asked:** "write the click script" — §1z-ar's prerequisite, since the ROUTER only runs on
a click and the whole recent campaign is `--walk` keyboard-only. Three calibration runs.
Ident `MOVECODE-1z-as`. **The script exists and is calibrated; the router probe it was for
is still not deliverable, and §1z-as.5 says why.**

### 1z-as.1 The verb reaches the world — which was not known

`session.py` has carried a `click:<fx>,<fy>` walk verb since the panel probes, but its own
executor calls it *"a UI click at a FIXED window fraction — **a panel button, not a world
target**"* and `parse_walk` retires the aiming caveat *"for everything except a
world-anchored CLICK"*. Four runs in the whole corpus had used it, all at
(0.39–0.41, 0.56–0.61), all UI. **Pointed at the ground it works: 13 of 14 click legs
across three runs produced a `MOVE_TO_COORD`.** No new primitive was needed.

### 1z-as.2 ★ The camera calibration, confirmed predictively

`yaw:N` right-drags N pixels. Measured over a four-step sweep, the click's world bearing
moved **−24.0° per `yaw:300`** — 0.0 → 336.0 → 312.0 → 288.0 → 264.0, exactly linear:

> **12.5 pixels per degree.**

**Then it was used as a prediction rather than a fit:** the next run opened with `yaw:1500`
(= 120°) and the first click came back at **240.0°** — the calibration's own answer, to the
tenth. That is the part worth having; a fit that is never asked to predict is a curve.

### 1z-as.3 The range calibration, and its limit

At `fx = 0.5`, measured body-relative from the tape: **`fy` 0.46 ≈ 420–620 u**, **0.62 ≈
80 u**, **0.70 ≈ at the feet**. Useful, and **not stable**: the same `fy = 0.46` returned
**2,697 u** where the ground falls away, because a screen ray meets sloping terrain further
out. So `fy` sets a *rough* range on level ground and nothing more — **the wire, not the
fraction, is what says where a click went.**

### 1z-as.4 ★★ PROPS SWALLOW CLICKS — the owner's observation, and it explains everything

Watching the run:

> *"your click landed on the bridge prop, which was obscuring what is the ground point you
> were trying to click. when you click a prop like that you'll walk in a straight line at
> it"*

That is the harness's aiming limit stated exactly, and **no screen fraction chosen at the
desk can know a prop is there.** It accounts for every anomaly above at once: the
`verbatim` router verdicts (a straight walk **at** the prop, never a route), the range
jumping to 2,697 u at an unchanged `fy`, and the `dest-off-mesh` refusals — **we carry no
prop geometry** (§0.17's named remainder), so a prop surface point is never on our navmesh.

**And that makes the mesh the SENSOR.** A click whose destination is off our navmesh is a
prop hit or the void; on it, the click reached the ground. Scored that way the last run
reads **2 GROUND, 5 prop/void — and the split is exactly the router's own: both GROUND
hits are the two `verbatim` answers and all five prop hits are the five `dest-off-mesh`
refusals, 7 of 7.** A blind script cannot aim, but a run can be **scored on the subset that
landed**, which is what makes a click probe possible at all without the owner at the
keyboard. `clickcal.py` prints that column.

**This also makes §1z-ap/§1z-ao's plane-29 structure concrete: it is that bridge.** The
"bridge over the ground beneath it" in `clip`'s docstring was written as the generic case
for a file with no height in it; the owner's sentence says it is literally the thing the
fatal lead crossed.

### 1z-as.5 THE BIND, and it is why the router probe is not deliverable yet

A router probe needs a click the router must **bend** — the string pull only runs on more
than two waypoints. Scanning map 146 from the spawn for bearings where a straight line is
blocked but a route exists gives four, at **355°/700 u, 350°/700 u, 95°/700 u and
90°/550 u** (3–4 waypoints each).

**Those are the bridge.** The obstacle that forces the route is the obstacle whose prop
occludes the ground in front of it — so a blind click aimed there lands on the prop and the
client walks straight at it, which is the one outcome that produces no routing at all.
**The geometry that makes a route necessary is the geometry that eats the click**, the same
shape as §1z-aj.3's tension and §1z-al's mutual exclusion.

Every ground hit so far has come back `verbatim` — a straight-line pass-through — so
**zero genuinely routed multi-waypoint paths exist under any tape**, and §1z-ar's question
is exactly where it was.

### 1z-as.6 What ships, and the two ways out

**Shipped:** `studies/movecode/review/clickcal.py` — the calibration, the prop sensor, and
the exposure count. The script itself is one line and is now writable against measured
constants rather than guesses:

```
--walk "wait:3 yaw:1500 click:0.5,0.46 wait:3 click:0.5,0.46 wait:3 yaw:-250 click:0.5,0.46 wait:3 ..."
```

**Not shipped: a router probe**, because it would measure nothing.

The two ways out, and the first is cheaper than it looks:

- **The owner aims one click.** This is precisely the boundary that has always been theirs —
  a world-anchored click needs the scene — and it is one click, not a session: click past
  the bridge onto ground that needs routing, with the tape running. Everything after that
  is scoreable from the wire.
- **Or move the probe off this obstacle — DONE in §1z-at, and it answered differently:
  the map was never wrong.** Map 146 is 17-20% route-forcing with ~89% of those obstacles
  terrain-shaped; the SPAWN just sits beside a bridge, and the nearest terrain obstacle is
  2,827 u away. Find a map whose routing obstacles are terrain
  rather than props, where the click can land on open ground beyond a bend. That is a desk
  search over the archive's meshes and needs no run to start.

---

## 1z-at. THE MAP SEARCH — it is THIS map, a different PLACE; the walk script now navigates to 16 u, and blind click targeting across an obstacle is what is left

**Asked:** "find a map whose obstacles are terrain, not props" — §1z-as.6's second way out.
Ident `MOVECODE-1z-at`. **The search answers differently than it was posed, and the answer
is cheaper.**

### 1z-at.1 ★ §1z-as's bind was the SPAWN's neighbourhood, not the map

`mapscout.py` scores each explorable map for the thing a click probe needs — the share of
(origin, bearing, range) triples at click range where the straight chord is **blocked but
routable** — and classifies the blocking hole by flood-filled size, a **compact** hole being
prop-shaped and a **big** one terrain:

| map | chords | route-forcing | terrain-shaped |
|---|---|---|---|
| **Lakeside County (146)** | 178–353 | **17.0–19.7%** | **87–89%** |

> **§1z-av CORRECTS THE WHOLE RANKING: `0x1B97D` is the entire Pre-Searing region and map
> 146's spawn is ASCALON CITY's** (`content/maps.toml`, which said so all along) — so this
> table scored a CITY, and against single-region maps it was never like-for-like.
>
> **§1z-au CORRECTS the "terrain-shaped" column: it is an UPPER BOUND on terrain, not a
> measurement of it.** A screenshot from the spot this table chose shows Ascalon City's
> WALL — the size proxy called a large building terrain, exactly the failure its own
> docstring names.
| Isle of the Nameless (280) | 383 | 12.3% | 83% |
| Domain of Anguish (474) | 344 | 9.0% | 89% |
| Lornar's Pass (90) | 344 | 6.7% | 78% |
| Sparkfly Swamp (558) | 465 | 4.9% | 96% |

**Map 146 ranks FIRST** — which contradicts §1z-as, and the contradiction is the finding.
§1z-as scanned bearings **from the spawn only** (4 of 288, all the bridge) and concluded the
map was wrong. It is not: 146 is 17–20% route-forcing and ~89% of those obstacles are
terrain-shaped. **The spawn just happens to sit beside a bridge.** A one-origin scan
generalised to a map, and a five-map scan caught it.

**The nearest terrain-shaped route-forcing spot is 2,827 u from the spawn on foot — about
10 s at run speed**: stand at `(9165, 10189)`, click toward `(9158, 10789)`, bearing 91°,
3 waypoints, blocking hole big enough to hit the flood cap. No new map, no content work.

### 1z-at.2 ★★ The walk script is now DERIVED from the mesh, and it navigates to 16 u

`mapscout.py --script` emits a `--walk` plan that reaches a computed spot: the mesh's own
route from the spawn, one `yaw`+`W` pair per leg, using §1z-as's calibration
(**12.5 px/degree**, 288 u/s) and closing with a click fan at the target bearing.

Driven, it put the body at **(9159, 10203)** against a computed target of
**(9165, 10189)** — **16 u**. That validates three things at once that had only been
assumed separately: the yaw calibration composes over a multi-leg plan, **`W` does follow
the camera's forward** (the run's tape checks what §1z-as could only assume), and a mesh
route converts to a keyboard plan that lands where it says. **The harness can now be sent
to a computed coordinate**, which it could not before, and that is worth more than the
probe it was built for.

### 1z-at.3 What still does not work: blind click targeting ACROSS an obstacle

Four clicks from the spot, all `fx=0.5, fy=0.46`, ranges **511 → 1031 → 1429 → 1767 u**
(the same `fy` walking outward as the camera meets falling ground — §1z-as.3's instability
again):

| range | landed | router |
|---|---|---|
| 511 u | prop/void | `clip-fallback / dest-off-mesh` |
| 1031 u | prop/void | `refused / dest-off-mesh` |
| **1429 u** | **GROUND** | `refused / no-path-or-gate` |
| 1767 u | prop/void | `refused / dest-off-mesh` |

**The 511 u click landed 75 u SHORT of the intended `(9158, 10789)` — inside the obstacle's
own hole.** That is the geometry, not bad luck: aiming *past* a barrier at a shallow camera
angle puts the ray into the barrier's near face. Click further to clear it and the
destination lands in mesh the router says it has **no path** to. **One ground hit in four,
and it was unroutable.**

So the obstacle is no longer prop occlusion (§1z-as) — that was solved by moving away from
the bridge. It is that **clearing a barrier blind requires knowing how far past it to aim,
and the screen fraction does not carry that.** Still **zero routed multi-waypoint paths
under any tape**; §1z-ar's question is unchanged.

### 1z-at.4 What ships, and what the remaining step is

- **`mapscout.py`** — the map ranking, the terrain/prop size proxy (labelled as a proxy: it
  cannot see a prop, it infers one from a footprint), the nearest-reachable-spot search, and
  the script emitter.
- **The correction to §1z-as**: the map was never wrong.
- **Not shipped: a router probe.** Three runs of blind click targeting have now produced one
  ground hit that the router refused.

**The remaining step is one aimed click, and it is worth being plain about why.** Everything
around it is solved — the harness navigates to a computed spot, the tape reads both copies
and the fence, and the wire scores where every click landed. What is missing is the single
judgement a screen fraction cannot encode: *how far past that ridge is open ground.* That is
the aiming boundary this repo has always drawn, and the cheapest form of it is one click
from the operator standing at `(9165, 10189)` with the tape running.

---

## 1z-au. THE SCENE IS READABLE — the "terrain" obstacle is the CITY WALL, the size proxy was fooled exactly as advertised, and aiming is no longer the operator's alone

**Asked:** the operator, fairly — *"idk what you're asking me"*. The ask was a single
world-anchored click, and before handing that over it was worth checking whether the desk
could do it after all. **It can, and this section is what looking cost and bought.** Ident
`MOVECODE-1z-au`. No code change.

### 1z-au.1 ★ The correction: my "terrain-shaped" obstacle is a BUILDING

§1z-at picked `(9165, 10189)` as the nearest **terrain-shaped** route-forcing spot — the
blocking hole flood-filled past the cap, so the size proxy called it terrain. A screenshot
from that exact spot shows what is actually there: **the character is standing against
Ascalon City's wall**, a masonry structure filling the right half of the frame, with the
gate and its red doors up-left and open grass to the left.

**That is the proxy failing in precisely the way it was documented to fail.** `mapscout.py`
says of it: *"it cannot see a prop; it infers one from a footprint, and a large building or
a small island would each fool it."* A city wall is a large building. So §1z-at's
"87–89% terrain-shaped" is **an upper bound on terrain, not a measurement of it** — big
holes are terrain *or* big structures, and this map's biggest holes are its city.

It also explains §1z-at.3's clicks without any new mechanism: the 511 u click landing 75 u
short "inside the obstacle's own hole" was landing **on the wall**, which is §1z-as's prop
rule again at a different address.

### 1z-au.2 ★★ And the scene is READABLE at the desk, which changes the boundary

The harness's `shot:` verb writes a PNG; that PNG can be opened and looked at, and its
**compass rosette cropped and enlarged is a top-down local map** — it shows the city to the
west, open field east, long diagonal walls south, and **water** to the south-east.

So the standing rule that *"world-anchored clicks stay with the owner"* was drawn when the
harness could not aim **and could not look**. It can now do both: walk to a computed
coordinate (§1z-at, 16 u), photograph it, and read the result. **The remaining gap is not
seeing, it is the world↔screen mapping** — knowing which fraction hits a point one has
identified — and that is arithmetic with a measured FOV (75.000° horizontal,
`studies/.../fovread`), a known camera bearing and a known body position, not a judgement
call.

**This does not retire the boundary, it narrows it**, and the narrowing should be checked
rather than assumed: the projection has not been built or validated, and §1z-as's own
range instability (the same `fy` returning 511 u and 1,767 u as the ground falls away) is
the warning that a flat-ground projection will not be enough.

### 1z-au.3 Where the probe actually stands

**Water, south-east on the compass, is the obstacle worth aiming at** — it blocks routing,
it is genuinely terrain rather than a structure, and unlike a wall or a bridge **it does not
occlude the ground beyond it**, which was the whole failure of §1z-as and §1z-au.1. Nothing
has tested it yet.

What is built and working, none of which needs revisiting: navigation to a computed
coordinate (§1z-at), the fence column and both drawn copies on the tape (§1z-an), the
prop/ground sensor on every click (§1z-as), and the screenshot. What is missing is one
target that forces a route and is not behind a building — and the compass says where to
look for it.

**Nothing is asked of the operator that the desk has not first tried.**

---

## 1z-av. THE WATER HUNT — it does not converge, and the reason is structural: §1z-at's ranking measured a CITY, and open country has almost no route-forcing geometry

**Asked:** "go for the water". Four runs, no water reached. **This section is the negative
result and the two corrections it forced**, and it ends the blind-fan approach rather than
extending it. Ident `MOVECODE-1z-av`. No code change.

### 1z-av.1 ★ CORRECTION: §1z-at's map ranking measured Ascalon City

`content/maps.toml` says it plainly, and it was in the repo before any of this started:

> *"Three map ids share one file because row 7982 covers the whole Pre-Searing region…
> **WE DO NOT KNOW WHERE LAKESIDE'S SPAWN IS**… Ascalon City's coordinate is reused…
> Pre-Searing is one continuous terrain, so **if this lands inside the city walls the fix is
> to walk out** rather than to guess again."*

**Map 146, map 148 and map 164 are one mesh** — `0x1B97D`, extent x −18432…21504 — and map
146's spawn is **Ascalon City's**. So §1z-at's headline, *"map 146 ranks FIRST, 17–20%
route-forcing, 87–89% terrain-shaped"*, was computed over a region that is largely a
**city**, and its "terrain-shaped" holes are its walls and buildings. §1z-au caught one of
them by photograph; this is the general case.

**The ranking is not a terrain comparison and must not be read as one.** Against Lornar's
Pass or Sparkfly Swamp it was never like-for-like: those are single regions, this is a city
plus its countryside scored as one map. That the repo had already written down where the
spawn is, and that the fix is to walk out, is the part worth remembering — **the answer was
on disk before the first run.**

### 1z-av.2 The country is 8–10 km away, and photographs confirm the walk out

Grid clearance over the whole mesh (96 u cells, distance transform from every unwalkable
cell) puts the most open ground at **(5560, 816), 2,400 u of clearance, 9,240 u from the
spawn** — a 32 s walk. Two runs photographed the way there: `(9165, 10189)` is against the
city wall (§1z-au), and `(8632, 6768)` — the lowest hole-density candidate at 0.179 — is at
the **city gate**, with a dirt road, a mossy **rock slope** (terrain at last) and open
country with trees and sky visible beyond the arch.

So the geography is now known and the navigation works. What does not work is what waits
out there.

### 1z-av.3 ★★ THE STRUCTURAL RESULT: open country has almost no route-forcing geometry

Ground in the open country with an obstacle at click range (250–650 u clearance), scored for
how many of 18 bearings produce a **blocked-but-routable** chord:

| position | clearance | walk from spawn | route-forcing bearings |
|---|---|---|---|
| (4600, 1680) | 576 u | 8,261 u | **2 of 18** |
| (6520, 1680) | 576 u | 9,549 u | **0 of 18** |
| (6616, −48) | 576 u | 10,562 u | **0 of 18** |
| (3736, 816) | 576 u | 9,476 u | **0 of 18** |
| (7480, 816) | 480 u | 10,737 u | **0 of 18** |

**An isolated obstacle forces a route only if you click almost exactly through it.** In open
country the obstacles are lone rocks with clear ground either side, so the angular window
that bends a path is narrow — 0 to 2 bearings in 18. Dense geometry gives plenty of
route-forcing chords, but dense geometry is the city, and the city's obstacles are the props
that eat the click (§1z-as, §1z-au).

**That is the bind in its general form, and it is the third instance of this shape in the
arc** (§1z-aj.3's exposure tension, §1z-al's mutually exclusive `+0x98`): *the geometry that
forces a route is the geometry that defeats a blind click, in both directions.* "Find a map
whose obstacles are terrain" does not escape it — terrain obstacles are sparse, and sparse
obstacles are the ones a blind fan misses.

### 1z-av.4 The blind fan is the wrong instrument, and the right one is derivable

Seven runs across §1z-as, §1z-at and here have produced **one** ground click that the router
answered, and it answered `no-path-or-gate`. That is enough evidence about the method:
**a fan of screen fractions cannot reliably hit a target this narrow**, and running more of
them is the treadmill the 2026-08-30 direction refuses.

**BUILT AND REFUTED in §1z-aw, then REPLACED BY A READ in §1z-ax (which also corrects
half of §1z-aw's evidence: the V near the body is geometry, not a varying pitch)** — the flat-ground model failed its own hold-out (205 u
mean, 569 u worst) because the camera's PITCH VARIES, and the fix is to READ the camera
(`fovread.py` already does) rather than fit it. The derived alternative is already
identified in §1z-au.2 and is **arithmetic, not a run**:
a world→screen projection from the measured **75.000° horizontal FOV**, the calibrated
camera bearing (**12.5 px/degree**, §1z-as), and the body position the tape reports. With
it, a click goes at a **chosen world point** — the route-forcing chord `mapscout.py` already
computes — instead of at a guessed fraction. **The pieces all exist and none of them needs a
client.**

Its one known hazard is on file: §1z-as.3's range instability (the same `fy` returning
511 u and 1,767 u as the ground falls away) says a **flat-ground** projection will not be
enough, and the honest form validates against the 14 click→world pairs already captured
before it is trusted.

**What is NOT recommended is another blind fan, and what is not needed is the operator** —
§1z-au's point stands: the desk can see the scene now, and what it is missing is a
projection it can build.

---

## 1z-aw. THE PROJECTION — built, REFUTED by its own hold-out, and the failure names the fix: read the camera, do not fit it

**Asked:** "build the projection" — §1z-av.4's derived alternative to the blind fan.
Built, and **it does not work.** Ident `MOVECODE-1z-aw`. `studies/movecode/review/clickaim.py`
ships with its verdict in its header and `--aim` refusing to emit a table.

### 1z-aw.1 What was built

A ground-plane intersection from a third-person camera: a screen row `fy` is a ray depressed
`θ + α(fy)` below horizontal, meeting flat ground at `H / tan(θ + α)` from the camera. `FOV_v`
comes from the repo's measured **75.000° horizontal** and the window aspect; `α` accounts for
the **viewport not being the window** (`dc.click` takes fractions from `GetWindowRect`, which
includes the title bar), with the viewport's top and height fitted rather than guessed.

**And a hold-out gate, written before any data existed**: fit on some points, score on
points the fit never saw, and refuse to print an aim table if the held-out error is worse
than the flat-ground assumption can excuse. §1z-as's yaw calibration earned its keep by
predicting `yaw:1500 → 240.0°` *before* the run; this file was held to the same test.

### 1z-aw.2 ★★ It failed that test, and the data says why in one line

An eight-point sweep on the map's most open ground — **all 8 clicks landing on GROUND**, every
body position read from the tape:

| `fy` | 0.36 | 0.42 | 0.48 | 0.54 | 0.60 | 0.66 | 0.70 | 0.44 |
|---|---|---|---|---|---|---|---|---|
| range (u) | 686 | **255** | **1057** | 923 | 141 | 62 | 83 | 464 |

**That is not monotone in `fy`.** A click lower on the screen must land nearer; 0.42 → 255 u
against 0.48 → 1057 u cannot happen under *any* fixed camera. Fitted on five points and
scored on three, the hold-out came to **205 u mean, 569 u worst** — against an aiming need of
roughly ±100 u.

**The gate did its job.** Fitted and reported on the same points, the model would have shown a
310 u rms and looked like a tuning problem; the hold-out shows it is a *modelling* failure, and
the non-monotonicity shows it is not fixable by adding parameters.

### 1z-aw.3 The diagnosis, and it is not the slope

§1z-as.3's slope hazard was the anticipated risk and it is **not** what happened — slopes
would bias ranges long or short, not reverse their order. **The camera's pitch is not
constant.** `fy` alone therefore does not determine the ray, and no fit *over `fy`* can
recover a parameter that moves between samples.

### 1z-aw.4 ★ The fix is a READ, and the instrument already exists

`toolkit/clientscan/fovread.py` — built two arcs ago for the FOV question — **already reads
the client's live camera**: `Position` at `0x00C07860`, `Target` at `0x00C0786C`, `fov` at
`0x00C078C4`, the three the frustum builder's own failure path prints under
`Invalid frustum:`. Position, target and FOV **are** the view transform.

So the projection should be **evaluated per click from the client's own camera**, not fitted
across clicks — at which point a varying pitch stops being an error term because it is being
measured. That is this repo's standing method (*"the wins all came from capturing the client
and reading it, never from reasoning about it"*) applied to a place where I reasoned first.

**What remains** is small and needs no new derivation: read those three vectors beside the
click, build the view matrix, project the route-forcing point `mapscout.py` already computes,
and click the fraction that comes out. The failure above is what says to do it that way.

---

## 1z-ax. THE CAMERA IS READ, NOT FITTED — the projection is exact, and half of §1z-aw's evidence was geometry I mis-measured

**Asked:** "read the camera." Built on `fovread.py`'s existing read; **12 bare-machine
checks green, no client used** (the harness is the operator's). Ident `MOVECODE-1z-ax`.
**Nothing has been aimed at a live client yet, and §1z-ax.4 says what that needs.**

### 1z-ax.1 What replaces the fit

`fovread.py` already reads all three terms of the view transform, from the frustum builder's
own failure path: **`Position` `0x00C07860`, `Target` `0x00C0786C`, `fov` `0x00C078C4`**. With
those there is nothing to fit — `clickaim.py` now carries `project()`, `ray()` and
`to_ground()`, evaluated **per click from the client's own camera**. A pitch that moves stops
being an error term because it is being measured.

**And the window chrome stopped being a fitted parameter.** §1z-aw carried the viewport's top
and height as two of its four fitted terms — which is how a title bar ended up inside a camera
model. `viewport_in_window()` reads it exactly (`GetClientRect` + `ClientToScreen` against
`GetWindowRect`, which is what `dc.click` uses).

### 1z-ax.2 ★ The correction §1z-ax owes §1z-aw

§1z-aw called its sweep *"not monotone in `fy`, which no fixed camera can produce"* and blamed
a varying pitch **for all of it**. That was too strong. **Half of it is ordinary geometry:**

Clicks **below the body's own screen row** land *between* the camera and the body, so
`|ground − body|` is **V-shaped, with its minimum at the body**. §1z-aw measured exactly that
unsigned distance — and its tail, `0.60 → 141, 0.66 → 62, 0.70 → 83`, is the V, not a
contradiction. The projection reproduces it, minimum at the body's row.

**What survives is the inversion higher up** — `0.42 → 255` against `0.48 → 1057`, both well
above the body's row, where the geometry says monotone. *That* still needs the read camera,
and it is the half of §1z-aw's evidence that was real.

The lesson is the small one: **I chose the wrong quantity.** The signed range along the view
direction is what a camera model is monotone in; the unsigned distance to the body is not, and
reading a V as a refutation cost a section. The self-check pins both directions so it cannot
happen twice.

### 1z-ax.3 What is checked, and what is only declared

`clickaim.py --selftest`, **12 checks, floor 12, bare machine** — a ground point projects and
unprojects to itself at 200/600/1500 u; the body lands on the centre column; a point behind
the camera and a ray above the horizon each return **None rather than a fabricated
coordinate**; and **a 24° yaw shifts a fixed point by the fraction of screen width the
measured 75.000° FOV requires** — §1z-as's `yaw:300` calibration *falling out of* the geometry
rather than being assumed by it, which is the closest thing to an independent check available
without a client.

> **Not a `test_*.py`, deliberately.** `run_suite.py` walks `toolkit/` only, and
> `test_srclint` §7 requires every name in `TESTS.md` to **exist** there — so a test file under
> `studies/` is both undiscovered by the suite and a stale entry in the list. I wrote one,
> srclint refused it, and it was right. `movetap.py --selftest` is the precedent for a study
> tool whose checks travel with it, and this follows it.

**Two terms are declared, not established, and are pinned so changing them is deliberate:**
`UP_AXIS` — the movement wire is `(x, y)` and the pathing file has **no height**, so the third
float is *presumed* height; and `fov` read as the **full** angle, per §fovaxis's 75.000°
horizontal, where `fovread.describe` prints both readings precisely because it was unsettled.

### 1z-ax.4 What it still needs, and it is one run

The arithmetic is exact and self-consistent; **what it has never done is aim at a live
client.** The step is small: read `Position`/`Target`/`fov` beside the click — the natural home
is a column on `agenttap`, exactly as the fence was added in §1z-an — project the
route-forcing point `mapscout.py` computes, and click the fraction that comes out. The
validation is built in and needs no new instrument: **the click's own `MOVE_TO_COORD` says
where it landed**, so predicted-versus-actual is a residual in world units, per click.

**That run is not taken.** The harness is the operator's, and this is the point at which the
projection stops being arithmetic and starts costing a client launch.
