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
`reseed`/`snaptest` observations, and the client asserts that argument's world itself
— `AgTrack.cpp:458` `source.GetWorld() == WORLD_SYNC`.

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
9.03 s**. At 288 u/s that is ~18,000 u of lost path progress, and it matches the
measured path gap (49,378 u against 27,160 u) directly. During the longest stalls the
local copy was still receiving destinations and walking.

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

### 1i.5 WHY our server under-grants — and it is the SAME defect as MOVECODE-Q2

The server log records its own refusals, and they account for the gap:

* **17 movement clicks refused outright** — `geo-stale` 13, `geo-blocked` 3,
  `geo-unplaced` 1. Every one `fired: false`.
* **13 of 64 grant verdicts refused** on `heading-rate`.

So **30 of 81 movement-authority events were suppressed (37%)**, against 51 granted.

The branch is `authsrv.py:16453`, and its comment states the intent plainly: *"Something
is in the way, so the client is pathing around it and knows more than we do. Say
nothing, and drop our own destination rather than integrate along a line the player is
not walking."*

**The silence is not free**, and that is the finding. The client is not "left to its
own pathing" — it is left to walk the local copy away from a sync copy that receives
nothing, until the client's own desync test fires and rolls the player back.

**And these are Q2's coordinates.** Two of the 17 refusals are *exactly* §1h.4's two
OFF-MESH `MapFindPath` goals, and the server's own reason code matches which end
§1h.4 found off-mesh:

| refused click | server's reason | §1h.4's verdict |
|---|---|---|
| `(−4705.9, 7670.4)` t=170.4 | `geo-unplaced` — "cannot place **them**" | **start** off mesh |
| `(−4284.3, 8482.0)` t=178.7 | `geo-blocked` — "not a straight shot" | **goal** off mesh |

11 of the 17 refusals sit at y > 5000, the same north-east region §1h.4 named. **The
navmesh hole and the twin starvation are one defect seen from two sides**: our decode
of map 280 is wrong in the north-east, the server therefore refuses to grant there,
and the client warps.

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
  consequence and a measured cost in grants.
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
