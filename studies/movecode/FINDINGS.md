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
| `[click, click+walk_t]`, closed by `0x003E`/`0x0039` only | 77.44 s | **7** | 3 of 27 |
| `[first grant, ETA]`, closed by `0x003E`/`0x0039`/capture-end | 82.22 s | **25** | 4 of 27 |

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
