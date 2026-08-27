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

**Reviewed by hand rather than by fan-out, and that is worth recording.** A
five-lane adversarial review was launched at the C and **all five agents died
returning `None`** (usage limits — the third such failure this session), writing no
notes. The checks were done directly instead. One genuine defect was found and
fixed: `readable()`'s range test computed `p + n` before screening for overflow, so
a pointer near `0xFFFFFFFF` would wrap to a small value and compare happily inside
the region. It is unreachable today — `VirtualQuery` fails on kernel-space
addresses in a 32-bit user process — but a bounds check whose own arithmetic can
wrap is not a bounds check. Also hardened: the region-end sum, and a comment
recording that Control B's sampling **must** run before the sites are armed,
because it suspends client threads and suspending one that sits inside our own
vectored handler is a deadlock.

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
