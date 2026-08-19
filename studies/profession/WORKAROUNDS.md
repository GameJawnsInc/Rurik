# Is there a way around the wall?

Sequel to [`FINDINGS.md`](FINDINGS.md). Pass 1 measured the wall; this pass asked whether
there is a way around it. Six routes surveyed, each adversarially re-verified by a second
reader who re-ran every disassembly. This document is the synthesis. **Where a verifier
weakened or refuted a survey claim, the corrected claim is what appears in the body** and
the original is recorded in §10.

Four load-bearing corrections were re-checked a third time by the synthesist against the
binary — two refutations of a surveyor by a verifier, one shape correction, and one new
measurement that answers pass 1's own top offline question. Every one held. The
synthesist's re-checks are marked as such at the call site.

No client was launched. `C:\gw` was never touched. Nothing was patched, written or
modified. Both client builds and the archive were opened `rb`.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes on this machine, this pass. We say which bytes: file, address, count. |
| **OBSERVED** | Watched happening in a running client, by this repo, at a dated pass. |
| **CLIENT-DATA** | Read out of the shipped client by a third-party tool whose code we read. |
| **SOURCE-CODE** | Read in some project's source. Nobody's source is ground truth. |
| **UPSTREAM** | A reimplementation says so. A reconstruction, not a fact about retail. |
| **INFERRED** | Our reasoning on top of the above. Names the claims it stands on. |
| **CONTESTED** | Sources disagree and this document does not pick a winner. |
| **NOT FOUND** | We looked and there is no answer in what we have. A real result. |

Corpus: `vault/client/2026-07-29_221c13772c7a/Gw.exe` (build 38797, 10,483,904 B), the
cross-check build `vault/client/2026-04-30_b174de1f2d8d/Gw.exe`, the already-built
loopback client `vault/client-patched/Gw.custom.2026-07-29_221c13772c7a.exe`,
`vault/dat_study/Gw.dat`, and 21 mirrored prior-art repositories.

---

## 1. The honest verdict

**A route exists, and it is (c) widened: an existing profession id carrying authored
attribute names in the client's own nine reserved slots, an authored profession label,
authored icons, and — the part this pass adds — a small runtime detour on the handful of
accessor functions that would otherwise show the host profession's identity.** Days to two
weeks for the parts already proven in this repo, plus one genuinely new capability — a
~60-line pure-`ctypes` cross-process write extending `keytap.py`, hours of work, no new
dependency at all.

**And (a) — a real eleventh profession — is no longer refused on a hard blocker.** This
document's own first draft said it was, naming the armour-composite art gate as the one
thing engineering could not move. **That was wrong, and it was refuted after synthesis in
about five minutes** by a check all six tracks had deferred. See "The art blocker" below;
the correction is large enough that it changes §7's recommendation, so read §1 to its end
before acting on any other section.

### What moved since pass 1

Pass 1 refused (a) on two grounds: 29 bound checks that each end the session, and eight
backing tables with no spare row in four incompatible growth shapes. **Both grounds have
moved, and neither moved the way anybody expected:**

- **The 29 session-enders are one patch site, not 29.** All 19,758 assert read sites route
  to one callee, and that callee's own handoff into the noreturn reporter is a single
  `call` at VA `0x00487C11` (file offset `0x00087011`, bytes `E8 FA 05 00 00`) whose target
  `0x00488210` has **exactly one direct caller in the entire image**. Five bytes converts
  every bound check in the game from a session-ender into a fall-through — strictly cheaper
  than pass 1's framing by a factor of 29.

  **Verified independently by the orchestrator, and the fall-through is sound rather than
  merely reachable** (MEASURED — a full `E8 rel32` sweep of every executable section found
  20,131 call sites targeting `0x00487BC0`, matching `asserts.py`'s own independent-sweep
  figure exactly, and **exactly one** targeting `0x00488210`). Reading `0x00487BC0` end to
  end settles the two things that would have broken this patch:
  - **`ret 4` is correct for all 20,131 callers uniformly.** The routine takes one *stack*
    argument at `[ebp+8]`; `edx` and `ecx` are register arguments, saved to locals at
    `0x00487BD0`/`0x00487BD3`. That is what pass 1's "edx-first / ecx-first / shared-tail"
    shapes are — one convention, not three.
  - **NOPing the call leaves the stack balanced.** The four `push`es at
    `0x00487C04`–`0x00487C10` are cleaned by the caller's own `add esp,0x10` at
    `0x00487C16`, *after* the call — cdecl. So with the call removed, execution falls
    through the `add`, still runs the security-cookie check at `0x00487C1E`, and reaches
    `mov esp,ebp / pop ebp / ret 4`. The epilogue pass 1 correctly called unreachable
    becomes reachable **and correct**.
- **The "no spare row" problem is an artifact of assuming you must index the table.**
  Every named profession-keyed table sits behind exactly one small accessor function,
  bounded by `int3` padding on both sides, with a countable caller list — 31, 4, 12, 1, 2,
  4, 4, 14, 12 (MEASURED, reproduced exactly by two readers). A detour replaces the
  *function*; it never indexes the *array*. Append, re-stride, code-insertion and
  compiler-unrolled-stack — pass 1's four incompatible growth shapes — all collapse into
  one uniform operation the moment the unit of work is the accessor rather than the row.

So the arithmetic wall and the assert wall are both soluble in tooling that costs hours,
not weeks.

### The art blocker: refuted after synthesis, and it was four tool calls

**Everything from here to the end of §1 replaces what this document originally concluded.**
The paragraphs above survived; the two that followed them did not. The original §1 named the
armour composite gate as *"the only blocker in the whole document that no amount of
engineering moves"*, rested §6 blocker 6 and §7 Option 5 on it, and filed the trace as
**W1 — top of the ladder, an offline afternoon, nobody has run it.**

It was not an afternoon. A completeness critic ran it in about five minutes, and the
synthesist here re-ran every number against the binary before accepting it. **All of it
holds** (MEASURED, build 38797, this pass, by two readers independently):

- **There is a single choke point, and it is an ordinary accessor.** `0x005AE200`
  (`ConstComposite`), `int3`-bounded, `ret` at `0x005AE2BE`, **exactly 3 direct callers** —
  `0x008320B8`, `0x008321FB`, `0x0083247E`. Profession is arg0, bound-checked `< 0xB` at
  `0x005AE209`.
- **Profession is the OUTER axis**, not an inner stride: index is
  ~~`component + 6·axis2 + 12·profession`~~ **`blitId + 6·sex + 12·profession`**,
  computed by the `lea` chain at `0x005AE291`–`0x005AE29A`. **Append shape, not
  re-stride.** **CORRECTED 2026-08-19** — the outer-axis and append findings
  stand; the name of the 6-valued fast axis did not. The accessor takes FIVE
  arguments and ArenaNet names all of them, in source order at ascending
  addresses: `sex < CHAR_APPEARANCE_SEXES` (`0x00639F44`),
  `blitId < MODEL_NUM_TEX_BLITIDS` (`0x00639F60`) and
  `component < COMPOSITE_COMPONENTS` (`0x00639F80`), with
  `blitId < arrsize(s_dims)` and `blitId < arrsize(s_format)` ahead of them.
  So the 6 is **blitId** (MODEL_NUM_TEX_BLITIDS, and `s_dims` has 6 rows) and
  **`component` is a FOURTH argument that indexes INSIDE the pointee**, not a
  term of this index. COMPOSITE_COMPONENTS is 8, which is why it could never
  have been the 6. Full account:
  [../playercomposite/FINDINGS.md](../playercomposite/FINDINGS.md) §1.1–1.3.
- **It reads two parallel 132-entry dword arrays** at `0x00BF4018` and `0x00BF4228`,
  **exactly 528 bytes apart** (11 × 2 × 6 × 4 = 528 ✓), each holding **17 distinct values**.
- **They hold POINTERS, not art.** All 132 entries of table B resolve into `.rdata`.
  **AND THEY ARE NOT A SEAM TO FILE IDS — 2026-08-19, dereferenced at last.** The
  two arrays are ONE CSR structure, not two alternatives: `B[idx]` is a 9-dword
  non-decreasing prefix array, `A[idx]` an array of 16-byte records, and the
  return is `A[idx] + 16*P[component]` with `*count = P[c+1]-P[c]`. The records
  are **texture-atlas RECTs** `{left, top, right, bottom}`, unsigned — 359/359
  satisfy `0<=l<r<=W, 0<=t<b<=H` against that blitId's own `s_dims`, where XYWH
  fails 269/359 and LRTB fails 284/359. The complete value set across all 359
  records is `{0,128,256,384,448,512}`: **there is no file id anywhere in either
  table at any depth.** A player's file ids come from Gw.dat file `0x33EA`
  instead — [../playercomposite/FINDINGS.md](../playercomposite/FINDINGS.md).
- **And the fact that decides it: only 8 distinct profession rows exist across the 11
  professions, because professions 0, 1, 2 and 9 already share a byte-identical row.**

That last line is the whole refutation. **Four professions sharing one composite row is a
configuration ArenaNet themselves ship.** Giving an eleventh profession an existing
profession's armour is therefore not authoring art — it is **copying 12 dwords per table,
24 in total, every value already present in the owner's own client**. Nothing ArenaNet
expressed enters the repo: we commit an index and perform the copy at patch time against
the owner's install. The provenance gate is not engaged at all.

**Two caveats that survive and must travel with the claim.** Table A is only partly static —
44 of its 132 pointers land in initialised `.data` and **88 land in `.data`'s uninitialised
tail**, so they are populated at runtime (MEASURED). The static copy is proven for table B
only; table A wants the detour form or a runtime check. And the *original* W1 method line was
wrong in a way that would have manufactured a false negative: it sent the reader to
`0x00777F10`, **which never receives profession at all**. Profession reaches `0x00832080`
(`push edi` at `0x00832351`) and *that* calls `0x005AE200`. A reader following the method as
written would have found no profession use and filed "it fans out, back to art" — the exact
wrong answer, confidently.

### So what actually refuses (a)

Not art. What is left is smaller and more ordinary:

- **The census is bounded but not closed.** An earlier draft of this section claimed the
  surface had *grown* to "at least ten" tables on the strength of two more found
  incidentally. **That was double-counting** — both are aliases of costume arrays pass 1
  already counted, seen through their general accessors rather than their search loops
  (§10). The surface did not grow. The honest count is **~13 profession-keyed lookups over
  ~11 backing arrays, each behind one accessor**: 8 named by the `arrsize` sweep, plus 2
  costume, 1 composite pair, 1 jump table, and 1 compiler-unrolled stack lookup.
- **`asserts.py --grep arrsize` has now been run** — it was prescribed in pass 1's own
  reproduce section, cited by five tracks across two passes, and executed by none of them
  until the critic did it in ten seconds. **235 sites, of which 8 are profession-bounded
  arrays** (§8-W2). It is a *partial* enumerator, not a census closer: it names none of the
  costume arrays, neither composite array, and not the jump table, because those asserts are
  worded on the constant rather than on `arrsize`.
- **Nobody has ever done this.** Five independent reimplementations in four languages prove
  the inject → hook → overlay path ships and works, and **not one writes new content into a
  compiled client data table** (§3, R6). There is no reference implementation and no
  documented failure to learn from.

**(a) is therefore no longer refused on a hard blocker. It is refused on unbuilt tooling,
an unclosed census, and the absence of any precedent** — which is a materially different
answer from pass 1's, and a materially different one from this document's own first draft.
Whether that is worth building is §7, and it is genuinely a decision now rather than a
foregone conclusion.

### The pattern this pass failed to break

Pass 1's lesson was that its top-ranked risk took five minutes and that six agents each
filed it as somebody else's scope. This document opened by quoting that lesson and
instructing its own reader to *"be suspicious of anything everyone is deferring."*

**W1 was then deferred by all six tracks of this pass, by all six verifiers, and by the
synthesis that ranked it #1 while still not running it.** It took four tool calls and it
refuted the headline. The lesson has now failed to transfer twice, in consecutive passes,
each of which had it written down. That is worth more than the finding: **"an afternoon"
is what an agent writes when it has not tried, and a ladder rung nobody has run is not
evidence about cost.**

**Pass 1's own headline result stands unchanged and got stronger.** The assert reporter is
noreturn, and it now reproduces on the 2026-04-30 build too: 19,680 sites, one distinct
callee at `0x00487a80`, a report function `0x00488090`–`0x0048834D` with zero `ret`, ending
in the same three-argument terminator wrapper at `0x5b9d22` (MEASURED). The shape is not a
build-38797 accident.

---

## 2. The route table

Decide from this table. Each route is scored on four axes and the fifth column is the one
that decides whether it is a conversation with the owner or not.

| Route | Verdict | What it actually buys | Build cost | Maintenance cost | Drags in |
|---|---|---|---|---|---|
| **R1 — Neuter the assert** | **WORKS. 1 site, not 29.** | Removes the *session-ender*. Does **not** make index 11 valid — an out-of-range read becomes a read of adjacent bytes. Clears **1 of 8** pass-1 blockers. | **5 bytes.** One `call` NOPed at `0x00487C11`. Smaller than any patch `make_custom_client.py` already applies. | **One signature per build**, and it is the *same* signature for all 19,758 asserts. Cheap to re-verify (seconds); the function is small and hot, so re-verify rather than carry forward. | Nothing new. **One real cost:** it silences `read_error_dialog.py` image-wide — the only machine-readable evidence a client assert leaves — for as long as it is applied. |
| **R2 — PE surgery** | **MECHANICALLY CLEAR, PARTIALLY USEFUL.** | Spare room for grown/relocated tables. Retires "no spare row" for **6 of ≥10** tables; the costume tables are a different shape and are not fixed by it. | **1–2 days** for a stdlib PE section-appender this repo has never written (must also relocate/strip a 23,744-byte Authenticode block), plus ~half a day of per-table repoints. | Re-locate ~10–12 signatures per build **and re-measure this-build free-byte counts** (8 bytes after the jump table, 7 free section-header slots are 38797 facts, not invariants). | New **writer capability class** — every existing patch tool is same-length in-place. Pure stdlib, no toolchain. Would want a `datwrite`-grade test suite before it touches anything launched. No licence row. |
| **R3 — Runtime hooking** | **WORKS, and it is the structurally right tool.** | Collapses **all four** of pass 1's growth shapes into one operation. Enables the **redirect** (11 → *N*) that a table widening cannot express. Clears blockers 2–5 *in principle*. | **~60 lines of `ctypes`** extending `keytap.py`, plus a PID-provenance guard. `keytap_patch.py` already proves hand-assembled code caves. Hours, not days. | Same signature count as R2, resolved at **launch time** rather than authoring time — more resilient to a relink, still broken by a recompile. Does not shrink the count. | **Live cross-process writes** — a capability `toolkit/` does not have (zero `WriteProcessMemory` anywhere) and one the launch cage does not cover. Also the textbook AV/EDR injection signature. **No new dependency** for the byte-poke form; a compiled DLL only if code must run every frame. |
| **R4 — Reskin / creative middle** | **ROUTE OPEN. This is the deliverable.** | Profession name, abbreviation, the combined "Class1/Class2" label, and all 51 attribute rows including the nine reserved ones. Rides an existing id, so it touches **none** of pass 1's blockers — it goes around them. | Two `repoint_skill.py`-shaped tools (~250 lines each) plus an archive text fill through the already-tested `datplan`/`datwrite`/`datcheck` trio. Days. | ~7–12 accessor VAs re-located per build by the same structural scan `repoint_skill.py` already automates. | **Nothing new.** Pure stdlib + `gwpe.PE`. No licence row. Identity lives in *this* patched client + *this* archive copy, not on the server — a different distribution shape from (b). |
| **R5 — Integrity & durability** | **NO OBSTACLE FOUND.** (Enabler, not a route.) | Confirms nothing in the client blocks any of the above, and that **structural byte-shape location is durable across a real 90-day build gap** — 6 signatures, exact hit counts, non-uniform drift 320 B–25,616 B. | n/a | Re-run 6 signature searches when a build lands. Under a minute. | Nothing. **The one measured ceiling:** the largest contiguous `int3` run in the whole 5.47 MB `.text` is **78 bytes**, and zero runs reach 100 — so anything past a small trampoline needs R2's new section. |
| **R6 — Prior art** | **PRECEDENT FOR CODE. ZERO FOR CONTENT.** | Proof the inject → hook → overlay path ships and works, five independent reimplementations in four languages. **Nobody, anywhere, writes new content into a compiled client data table.** | n/a | n/a | **PLAN.md §6.1 rows before any code is taken** from GWCA (MIT), GWToolbox++ (MIT), MinHook (BSD-2-Clause, verified from `LICENSE.txt`) or Dear ImGui (MIT) — **none of the four has a row today.** A C/C++ toolchain only if per-frame code is needed. |

**Read the table this way.** R1, R2, R3 and R5 are *capabilities*. R4 is the only row that
is a *deliverable*. R6 says nobody has done the thing R1–R3 would enable, so there is no
reference implementation and no documented failure to learn from — the same *nobody tried*
verdict pass 1 reached, and it means the same thing.

---

## 3. Route by route

### 3.1 R1 — Neuter the assert: one routine, 19,758 callers

**MEASURED, build 38797, re-run independently by both readers and spot-checked by the
synthesist.** The chain pass 1 established is confirmed byte-for-byte, and this pass adds
the three facts that decide *where* to patch:

- **`0x00487BC0`'s calling convention is caller-clean.** The prologue normalises `ecx` and
  `edx` into locals; the only branch selects the caller's expression pointer versus a
  default and **both arms converge** at `0x00487C01`; four dwords are pushed and
  `call 0x00488210` fires at `0x00487C11`; `add esp,0x10` at `0x00487C16` executes
  regardless of whether the call runs. The security-cookie epilogue and `ret 4` at
  `0x00487C26` are self-contained. **So the call can be removed without breaking the
  caller's stack contract.**
- **`0x00488210` has exactly one direct caller in the image** — `0x00487C11`
  (`codescan.py --xrefs`, 1 rel32 reference, 0 data words; both readers). The patch is
  therefore *assert-exclusive*: it cannot also silence a non-assert fatal path.
- **The layer below it is shared and must not be patched.** `0x005BC094` has **5** direct
  callers; only `0x004884C8` is the assert chain. The other four (`0x005AE58B`,
  `0x005BBC20`, `0x005BF248`, `0x005CB275`) sit in unrelated fatal-error code — one of them
  is the canonical MSVC stack-cookie-failure shape (`IsProcessorFeaturePresent(0x17)`,
  `int 0x29`, exception code `0x40000015`), confirmed by resolving the IAT slot through
  `pefile`. Patching there would silence a GS-cookie violation and C++ termination glue
  along with the asserts. **The assert-exclusive patch point is one level shallower.**

**What it buys, stated precisely.** It removes the *session-ender*. It does not add a row
to any array. After the patch, an out-of-range profession index reads adjacent bytes and
renders or behaves wrong instead of ending the session — which is what pass 1 originally
*hoped* was the failure mode before L1 measured otherwise. **That is one blocker of eight,
and it is the cheapest one.**

**The severity split, and how far it is actually established.** For the append-shaped and
struct-record tables, continuing past a neutered check is a read from mapped, read-only
image data — memory-safe by construction, degrading to wrong data rather than corruption.
The 12-slot jump table at `0x005A5EB8` is categorically different (`jmp dword ptr
[eax*4+base]`, a computed indirect jump), but for the value 11 specifically it is *not* at
risk: pass 1 measured slot 11 populated and aliasing slot 0. **INFERRED**, standing on pass
1's table-shape census; the verifier marked it UNCHECKABLE and it deserves that label —
read-vs-write character downstream was spot-checked at exactly one of the 29 sites.

**And ArenaNet ships no non-fatal mode to flip — but that is asserted with less confidence
than the survey claimed.** The global at `0x00BEC120` gates only extra diagnostic
formatting at the two sites inside the assert-report family; both arms converge, neither
returns early. But the survey checked 2 of the 9 sites its own tool run found, and the
other 7 contain two things it said were not there. **Both re-confirmed by the synthesist
against the raw bytes:**

- Two direct-encoded stores exist: `mov dword ptr [0xbec120], 0` at **`0x00487B53`** and
  **`0x004895A2`** (`C7 05 20 C1 BE 00 00 00 00 00`). The survey's C8 — "no direct-encoded
  instruction anywhere in `.text` stores to this address" — is **REFUTED**.
- A third site does have a genuine early return: `0x00489570` reads the flag, `test`s it,
  and `je 0x4895b1` lands on a bare `ret`. Both stores clear the flag and then reach
  `0x005D5E70`, and the early return is in the routine that would otherwise call it — the
  shape of a **cleanup / re-entrancy guard**, not a verbose-mode switch.

So the conclusion survives — this is not a compiled-in "report and continue" mode — but it
survives on a re-reading, not on the search the survey ran. Whether `0x00489570` is
reachable from the assert chain (e.g. as an `atexit` handler or SEH unwind target) is
**NOT FOUND** and is **W4**.

### 3.2 R2 — PE surgery: a new section and relocated tables

**The mechanics are cleaner than the framing implied, and every one of them reproduced
exactly on independent re-run.**

- **Relocation is free.** All 10 absolute-address disp32 fields checked across the eight
  named tables' accessors — plus the Vendor jump table's own dispatch operand — already
  carry an `IMAGE_REL_BASED_HIGHLOW` entry, out of **140,862** in the image. PE rebasing
  adds a delta to whatever value sits at a relocated field, so **repointing an existing
  field at a new absolute VA, including one inside a freshly appended section, needs no
  `.reloc` change at all.**
- **But a *new* absolute reference is a live gotcha.** `DllCharacteristics` is `0x8140` —
  `DYNAMIC_BASE` and `NX_COMPAT` set, **no CFG** (the Load Config directory is the pre-CFG
  64-byte structure). A literal 13th jump-table slot holding a raw handler VA has no
  `.reloc` entry and resolves wrong at a randomized base. It must either gain one or be
  built PIC-style the way `keytap_patch.py`'s existing cave already is. **INFERRED**,
  standing on the measured flags; no client was launched to observe an actual randomized
  base.
- **Nothing validates the file.** No checksum or trust API is imported (15 DLLs; 482
  imports on 38797, **478** on the 2026-04-30 build — the counts are not uniform across
  builds). The retail checksums are correct (`0x00a02ccd` / `0x009f8510`); **the
  already-built loopback client this repo drives every day carries the original stale
  checksum against a true value of `0x00a01ad3`** — a live mismatch in a file already in
  routine use. The 23,744-byte Authenticode block is necessarily invalid on any patched
  build and nothing reads it. The single TLS callback is MSVC dynamic-TLS-initializer
  boilerplate on both builds.
- **There is room in two places.** 5 sections used, **7 free 40-byte header slots**, and
  `SizeOfHeaders` (`0x400`) exactly accommodates a grown 12-entry table with zero bytes to
  spare. And the Vendor jump table is followed by **8 bytes of unreferenced `int3`
  padding**, `0x005A5EE8`–`0x005A5EEF`, enough in place for one more slot; its bound guard
  `83 F8 0B` takes a one-byte immediate change (**synthesist re-confirmed both**).

**What it does not buy.** Nothing in this route touches the 29 bound checks, the composite
art gate, or the two compiler-unrolled stack lookups. And the costume tables — see §4.2 —
are not append-shaped at all, so "grow the array" does not describe them. **Six of at least
ten tables, and no blocker cleared outright.**

**The largest untested assumption in the whole route is that a hand-rolled section-append
produces a loader-accepted file.** No tool here has ever grown a PE. That is retirable
entirely offline against a synthetic stub with no ArenaNet bytes involved — **W6**.

### 3.3 R3 — Runtime hooking and DLL injection

**This is the route whose measurement changes the shape of the problem, and it was
undersold by its own surveyor.**

- **Every named profession-keyed backing table is read by exactly one instruction in the
  whole 10.5 MB image, and that instruction sits inside a small standalone accessor
  bounded by `int3` padding on both sides.** Measured and reproduced exactly by two
  readers, with caller counts: `s_charProfession` (accessor `0x005AB7B0`, **31** callers),
  `s_charProfessionAbbrev` (`0x005AB7E0`, **4**), `s_profChapter` (`0x005AB810`, **12**),
  the second name array (`0x005AB840`, **1**), body scale (**2**), hair palette
  (`0x005A8E40`, **4**), skin palette (**4**), and the two costume searches (**14** and
  **12**). The attribute accessors reproduce pass 1's counts exactly: 1 / 5 / 22 / 6.
- **Reaching a target does not require finding its callers.** An inline splice patches the
  *callee's* entry bytes, so it works through direct calls, indirect calls and tail jumps
  alike. Demonstrated on the hardest case in the document: the Vendor dispatch function
  `0x005A59C0` has exactly one direct reference (a `jmp` thunk at `0x005A5EF0`), and that
  thunk is never called — its address is **pushed as a value** at two sites, consistent
  with registration as a UI callback. Pass 1 filed its caller as never traced; this
  advances the trace one level and it is **still not closed** — the widget is NOT FOUND.
- **The toolchain already exists here.** `keytap.py` is pure `ctypes`, does ASLR-correct
  module-base resolution across the WOW64 boundary, and is read-only by explicit
  construction (`PROCESS_VM_READ`, never `WRITE`; zero `WriteProcessMemory` anywhere in
  `toolkit/`). The client really is 32-bit (`Machine = 0x14C`, verified from the PE header
  rather than inferred). `VirtualAllocEx` / `WriteProcessMemory` / `VirtualProtectEx` have
  the identical binding shape, and the full sequence is proven in pure `ctypes` by
  `ldufr/Headquarter`'s `tools/process.py` (MIT). **INFERRED**, standing on documented
  Win32 contracts and structural analogy — nothing was executed against any process this
  pass.

**The structural insight, and it is the one no single track could state.** Pass 1's four
growth shapes are four shapes *of the data*. A detour never touches the data. Widening a
`[4][11]` colour table means every race's row moves; a detour on `0x005A8E40` means writing
`if (profession == 11) return <our value>; else <tail-call the original>`. Inserting a
jump-table case means code insertion; a detour on `0x005A59C0` means one comparison. The
two compiler-unrolled stack lookups have no table to grow at all — and a detour does not
care, because it replaces the function that materialises them.

**What it does not buy.** It does not shrink the *census*. Every accessor still has to be
found, per build, and this pass raised the count rather than lowering it. It does not touch
the art gate. And it is genuinely new operational ground: live writes into a running
process, a failure mode `read_error_dialog.py` may or may not observe, and no guard.

**The safety gap is smaller than the survey stated, and this is a correction in the
route's favour.** `cage.assert_launch_safe` and `dhbuild.classify` gate an **exe path** and
a **network destination**, never a process handle — true, and confirmed by reading both
files. But the survey's blocker text ("nothing in this repo resolves a running PID back to
its exe path") is **REFUTED**: `toolkit/harness/session.py:264` already defines
`image_name(pid)` via `QueryFullProcessImageNameW`. The missing piece is the composition
`image_name → dhbuild.classify → cage_state`, not the primitive. That is the guard, and it
must exist before any live write.

### 3.4 R4 — The creative middle: how custom it can look with no new id

**ROUTE OPEN, scoped to text identity, and this is the deliverable.**

- **Profession identity text is id-resolved through exactly three arrays** — full name
  (`0x00A38794`), abbreviation (`0x00A387E8`), and a second name array (`0x00A38868`) —
  each behind one accessor, each bound-checked `< 0xb`, each entry a string id resolved at
  run time by a shared helper pair (`0x7C9410` / `0x7C93F0`). **Re-pointing a row at
  another existing id is exactly the shape `repoint_skill.py` already proves for skills.**
- **The compound "Class1/Class2" label is one shared format call.** Two
  independently-compiled sites (near `0x00876729` and `0x008A74F9`) resolve *both*
  professions through the full-name accessor and combine them with format id `0x2FF`, with
  a special-cased no-secondary branch on format id `3`. A separate function at `0x00538D60`
  does the identical combine for the *abbreviated* text via format id `0x33A` — which
  explains the abbreviation accessor's caller count of 4 (both symmetric branches of one
  function). Reproduced byte-exact by the verifier. **Which on-screen widgets these feed is
  INFERRED** from the well-known Guild Wars convention and is not confirmed to a screen —
  pass 1's §12-A1 correction is exactly this kind of shape-based screen guess being wrong
  once already.
- **The attribute table is confirmed at pass 1's corrected base**, independently re-dumped
  this pass by a script that computes the base from the accessors rather than trusting
  pass 1: row 45 at file offset `0x00634AC4` reads `(11, 45, 71982, 71983, 0)`; row 26 at
  `0x00634948` reads `(11, 26, 2122, 2123, 0)`; row 17 at `0x00634894` reads
  `(1, 17, 2112, 2113, 1)`; rows 0 and 44 carry the primary flag. **Pass 1's §5 and its
  §12-C1/C2 corrections are re-verified, not merely restated.** All four static accessors
  bound-check `< 0x33` on the **row index**, never on the stored profession field.
- **All ten reserved-slot string ids still resolve to empty text records**
  (2122/2124/2126, 71982/71983, 100257/100259/100261/100263/100265 — re-run this pass).

**Two honest limits the survey named and this document keeps in the body.**

**Filling an empty text record is not a one-line write.** Per `studies/datwrite/FINDINGS.md`,
all 1,077 text files use compression 8 and **no compression-8 encoder exists in this
repo**; the escape hatch is flipping that file's MFT row to *stored*, after which the fill
is an insert that shifts every later record in that file's payload. Real, multi-step, and
inside demonstrated tooling — but bigger than "fill an empty record" implies. The
per-operation edit count was **not** measured for this shape; `datplan.py` was not run
(writer tools are forbidden this pass).

**Every text change lives in *this* client's PE and *this* archive copy.** Unlike (b),
which is server-only and visible to any client, (c)'s identity is a property of which
patched build and which archive a player is running. Fully inside the local/personal
boundary; a structurally different distribution shape, and one that needs re-locating on
every client update.

**And the glyph is still NOT FOUND.** This pass tried a second bounded approach — the ATEX
container-walk probe at `0x006C3050` has only 2 direct callers, both plausibly the texture
loader's own entry points — and came up empty. That neither closes nor contradicts pass
1's NOT FOUND; it is one more cheap static lead that did not pan out. The *format* half
stays closed (`studies/texture/FINDINGS.md`, OBSERVED 2026-08-06).

### 3.5 R5 — Integrity, durability and the updater

**No obstacle. This route's value is that it makes the other five costable.**

The client validates neither its own checksum nor its Authenticode signature, imports no
verification API, is not packed, has no CFG, and its one TLS callback and both
`IsDebuggerPresent` call sites are ordinary MSVC CRT boilerplate — byte-for-byte identical
in shape across both builds. The updater kill switch gates exactly one narrow downloader
subsystem: the patched `sete al` forces a global at `0x01087810` to read *disabled*, and
that global has 6 absolute references (1 write, 5 reads) all inside a VA range roughly
`0x00833EC0`–`0x00834B92`, with **no overlap against any of the 29 `CHAR_PROFESSIONS`
sites, the DH accessor, or the mutex guard** (independently cross-checked).

**Two measurements from this route are load-bearing elsewhere in the document:**

**Durability is measured, not assumed.** Across a real ~90-day, cross-development-cycle
build gap, **six** structural byte-shape signatures — the four already shipping
(`SIG_KEYS`, `SIG_MUTEX`, `SIG_DOWNLOAD`, `TAP_SIG`) plus two derived from scratch this
pass for the attribute accessors and the `imul`-stride colour tables — each reproduced
their **exact hit count** (1/1/1/1 and 4/2) while their VAs drifted by **non-uniform**
amounts: 336 bytes for the mutex guard, 25,392–25,616 for the DH cluster, ~9,040 for the
new profession signatures, 320 for the assert callee. `.text` itself grew 44,032 bytes.
**Any patch plan anchored to a raw address is guaranteed broken by the next build; one
anchored to a byte shape survived both samples.** n=2 is induction, not a guarantee.

**The in-place code ceiling is 78 bytes.** `.text` carries 146,527 `int3` bytes across
26,243 runs, of which only **8** are ≥40 bytes, **zero** reach 100, and the single largest
contiguous run in the whole 5,471,232-byte section is **78 bytes**. (2026-04-30:
144,620 / 25,598 / 7 / 0 / **47**.) `.text` is not writable. This is why
`keytap_patch.py`'s 38-byte cave is close to the largest thing that fits at all, and it is
the measurement that forces anything larger onto R2's new section or R3's `VirtualAllocEx`.

### 3.6 R6 — Has anyone hooked content in, and what would it drag in?

**Precedent for code execution is overwhelming. Precedent for content is zero.**

The `CreateRemoteThread` + `LoadLibrary` sequence is independently implemented at least
**five** times across the mirrors in **four** languages — AutoIt (GWCA's example), C++
(GWToolbox++'s shipping `Inject.cpp`, GWLP-R-Utils' launcher), Rust (Tyria-Extractor, with
explicit `SeDebugPrivilege`), and pure `ctypes` Python (Headquarter). GWCA locates its
targets by **live in-process byte-pattern scan** — never a hardcoded VA — hooks the
client's own `EndScene`-equivalent via MinHook, and GWToolbox++ drives Dear ImGui against
that device pointer, compositing third-party UI into the game's own backbuffer with input
via `SetWindowLongPtrW` subclassing. Separately, `gw-preservation/network-logger`
demonstrates a **DLL-search-order-hijack** needing no `CreateRemoteThread` and no exe
modification: a 113-line C proxy built with a bundled TinyCC. **Its precondition holds for
our build** — no static `d3d9`/`d3d8`/`xinput` import among the 15 DLLs, with the literal
name strings present in `.rdata` (file offsets 6604028, 6605728, 6605776). *String
presence is not proof they reach `LoadLibrary`; the call sites were not disassembled.*

**And GWToolbox++ already neuters a compiled bound-check assert at runtime, for a synthetic
id outside the shipped range** — it locates the assert by scanning for its own compiled
strings and writes `0xEB` over the conditional jump, specifically so custom quest ids do
not trip it. *(SOURCE-CODE, MIT. The assert's file name and condition text are deliberately
omitted — see §10-D.)* **That precedent transfers only where nothing downstream reads a
real array at the out-of-range value**, which is a client-side-only synthetic id drawn
entirely by the overlay. Pass 1 measured that most of the 29 `CHAR_PROFESSIONS` sites do
not meet that precondition.

**What nobody does.** Across all 21 mirrors, every runtime memory write found is either a
1–2 byte code patch through a same-process `VirtualProtect`+`memcpy` helper, or a field
write on an already-allocated runtime object. **Not one writes new content into a
compile-time-sized data table.** The verifier extended the search into
`Py4GW_Reforged_Native` (~250 files), which the surveyor had flagged as unchecked, and
found the identical picture — a port of the same `MemoryPatcher`, used only for small code
patches. **NOT FOUND, corroborated by an independent extension.**

**Licence and register reality, checked from the files rather than from memory.** GWCA MIT,
GWToolbox++ MIT, MinHook **BSD-2-Clause** (read from `LICENSE.txt`, not the README badge),
Dear ImGui MIT — **none of the four has a `PLAN.md` §6.1 row today**, and the house rule
requires the row *before* a line of derived code is written. `Py4GW_Reforged_Native` carries
**Apache-2.0**, unlike its base repo and unlike `Py4GW`, both of which have no LICENSE at
all — a genuine correction to this repo's blanket "Py4GW_Reforged: no licence" framing.
`gw-preservation/*` grants nothing (verify-only, and its 113-line proxy could only ever be
read, never copied). `shiburito/gw_in_browser` is GPLv3 and targets the WASM client, a
different build entirely.

**The dependency question splits cleanly, and the split is still worth knowing — but it is
no longer a gate.** A cross-process byte poke needs nothing beyond `ctypes`. Anything that
must keep running inside the client every frame needs a compiled DLL, and therefore a C/C++
toolchain.

**Owner's ruling 2026-08-12, `PLAN.md` §7 Q6, `CLAUDE.md` dependency carve-out (3): "a
compiler is a cost, not a blocker."** This paragraph originally treated a native toolchain
as an unprecedented third carve-out the owner would have to authorise, and deferred to them
on it. They authorised it — unprompted, while this pass was running, precisely because the
stdlib-only rule read cold makes native routes look *forbidden* rather than *expensive*.

So the split is now **economics, not permission**: prefer `ctypes` where it suffices,
because it means no compiler in the iteration loop, and reach for a DLL where it does not,
without apology. What survives the ruling and still binds: the **server path** stays
dependency-free, the fixed-byte-pattern tools must keep working on a bare machine, and the
**second gate is untouched** — MinHook, Dear ImGui, GWCA and GWToolbox++ each still need a
`PLAN.md` §6.1 derivation-register row and a licence check before a line is taken, and
**none of the four has one today**.

The recommended route needs none of this regardless: a redirect on ten accessors is a
one-shot write, not a per-frame draw loop.

---

## 4. What this pass corrects in pass 1

Named explicitly, so nothing is superseded silently.

### 4.1 The 29 bound-check sites are one patch site

**SUPERSEDES** `FINDINGS.md` §1, §9-assumption-1 and §11, wherever they cost (a) at "29+
signatures" *for the assert layer*. The 29 sites remain 29 *sites*; but they are not 29
*patches*, because all of them route to one callee whose noreturn handoff is a single
5-byte `call` with exactly one direct caller in the image. Pass 1 was right that every
bound check is a session-ender; it did not measure that the session-ending is centralised.
**The 29-signature maintenance figure still applies to any plan that widens the immediates
(L5); it does not apply to a plan that neuters the reporter.**

### 4.2 The costume tables are not 11-entry arrays and their growth shape is not "append"

**SUPERSEDES** `FINDINGS.md` §3's table row *"costume body / costume hat — `0x00BBD73C` /
`0x00BBE680`, 11-entry, 16 B / 4 B stride, append"*. **Both halves of that row are wrong,
and the synthesist re-confirmed both against the binary:**

- **Costume body (`0x00BBD73C`)** is a bounded **linear search**: `shl esi,4; add
  esi,0xbbd73c` gives a start offset of `profession × 16`, then a loop of up to **23**
  iterations at a **160-byte** stride. Since 160 = 16 × 10, the array partitions into
  exactly **ten** residue classes and the ten shipped professions occupy all ten. A
  profession id of 11 lands on the same residue as profession 1, sharing 22 of its 23
  probe indices — **silent wrong data, not a clean bounds failure**.
- **Costume hat (`0x00BBE680`)** is the same shape, not a direct index: bound `esi < 0xb`
  at `0x008EE2B7`, then `lea ecx,[esi*4 + 0xbbe680]` and a loop of up to **0x3b = 59**
  iterations at a **0x28 = 40-byte** stride. 40 = 4 × 10 — ten residues again.

**This is a fifth growth shape pass 1 did not catalogue**, and it is the worst-behaved one:
append, re-stride, code-insertion and unrolled-stack all *fail*; this one *aliases*.

### 4.3 The profession-keyed table surface is at least ten, and the census is not closed

**SUPERSEDES** `FINDINGS.md` §1's "at least eight distinct backing arrays" as a working
count. Two more profession-gated tables sit in the exact code region the costume work
already had open, each reached by one of the same four `ConstCostume` assert sites the
census is built from (**synthesist re-confirmed both by disassembly**):

- **`0x00BBE658`** — a genuine direct 2-D index, `lea eax,[esi+esi*4]; lea eax,[edi+eax*2];
  mov eax,[eax*4+0xbbe658]`, i.e. `profession + 10 × style`, gated at `0x008EE281`.
- **`0x00BBD690`** — a **three-axis** index, `eax = edi + 4·ebx + 40·esi` in dword units,
  where `ebx` is the `CHAR_PROFESSIONS`-bounded value (assert `0x008EE19E`) with a
  **16-byte** stride and `edi` is bounded `< 4` (race, 4-byte stride). Profession is an
  **inner axis** here, so widening it moves every outer row — **a third re-stride table**,
  where pass 1 named two.

**And all three carry a compiled-in *ten* against a bound of *eleven*.** The outer stride
of `0x00BBD690` is 40 dwords = 10 profession slots, while the assert admits 0..10. Either
ArenaNet's own table has a latent one-row overrun at the top profession id, or our axis
attribution is wrong. **Open, and it is `W2`'s business.** The systematic sweep pass 1's
reproduce section already specifies — `asserts.py --grep arrsize`, which recovers every
table's real source symbol name — **has still not been run by anyone**, across two passes,
despite being cited by five tracks.

### 4.4 The character-creation profession picker is loop-driven over a compile-time eleven

**ANSWERS** `FINDINGS.md`'s L2b and its §13 row *"Is the character-creation profession
picker loop-driven or hand-placed? NOT FOUND — nobody opened the module."* **MEASURED,
disassembled independently by the surveyor, the verifier and the synthesist, byte-exact
three times:**

A function bounded `0x004D90F0`–`0x004D93DC` by `int3` padding initialises `mov ebx,1` at
`0x004D9199`, calls a per-iteration filter at `0x004DAE20`, resolves the **second** name
array through its accessor `0x005AB840` at `0x004D9393`, feeds the result to a
list-style UI-set call at `0x00633C10` with control ids `0x56`, `0x5D` and `0x5F`, and
closes with a back-edge at `0x004D93C9`:

```
004D93C9  43         inc ebx
004D93CA  895dfc     mov dword ptr [ebp-4], ebx
004D93CD  83fb0b     cmp ebx, 0xb          <-- the picker's arity
004D93D0  0f82dafdffff jb 0x4d91b0
```

**Three consequences, and they pull in different directions.**

1. **L2b's stated prediction held.** Pass 1 predicted *"hand-placed, or table-driven over a
   compile-time-sized table — i.e. not the runtime-`valueCount` shape."* It is the second:
   a loop, over a **compile-time** eleven, with **exactly ten** iterations (`ebx` = 1..10).
2. **(a)'s UI layer is a data edit plus one immediate**, not a code edit. That lowers (a)'s
   UI cost materially, exactly as pass 1 said it would if this came out data-driven.
3. **And it explains pass 1's own unexplained observation.** Pass 1 flagged that *not one*
   of the 29 sites is in the `CharCreate` directory and could not say why. The reason is
   now measured: **the picker's arity is enforced by a bare loop bound with no assert
   attached** (`83 FB 0B`, a one-byte immediate change to `0x0C`), which
   `asserts.py --grep CHAR_PROFESSIONS` structurally cannot see. **The census is a floor in
   a second way pass 1 did not name** — it misses not only unreadable asserts but every
   bound enforced without one.

**What is NOT established: the module.** The survey claimed `CrProfession.cpp` "almost
certainly", citing `asserts.py --at`. The verifier read the tool's source: `--at`'s default
span is a flat 2,000-byte address window, not a function boundary. **The loop function's
own only internal assert is a generic `Array.h` template bounds check**, and eight
`UiCtlInstance.h` sites sit in the same window immediately before it. **Whether this
function belongs to `CrProfession.cpp` (with UI-control code inlined into it) or to a
neighbouring translation unit is genuinely open.** The *behaviour* is measured; the *label*
is not.

### 4.5 The assert-noreturn chain reproduces on the cross-check build

**STRENGTHENS** `FINDINGS.md` §1 / §12-E1, which measured it on 38797 only. On
2026-04-30: **19,680** assert sites, **one** distinct callee (`0x00487a80`, drift 320
bytes), a report function `0x00488090`–`0x0048834D` with **zero `ret`**, ending in
`call 0x5b9d22` — a `(arg, 2, 0)` wrapper matching 38797's `0x5BC094` down to the push
sequence. Three of four links independently re-walked; the final SEH/CRT step was not.

### 4.6 Two smaller supersessions

- `FINDINGS.md` §13's *"Is the Vendor jump table's index-11 slot a real twelfth value or
  code-folding?"* remains **CONTESTED**. The one-step `--xrefs` pass 1 said nobody ran has
  now run: the enclosing function `0x005A59C0` has one direct reference (a `jmp` thunk at
  `0x005A5EF0`) whose address is **pushed as a value at two sites**, consistent with a UI
  callback registration. **The widget is still NOT FOUND** and the CONTESTED verdict stands.
- The reserved attribute rows and the primary flag were **not** re-checked on the
  2026-04-30 build. `FINDINGS.md` §13's open row *"Do the reserved attribute ids and the
  primary flag hold on the 2026-04-30 build?"* is unchanged.

---

## 5. Do the routes compose? — the part no single track could see

They do, and the composition is the answer. Grading six routes separately would have
missed it twice over.

### 5.1 Composition A — (c)+, the deliverable

Four already-proven capabilities and one cheap new one, stacked:

| Layer | Route | Status | Buys |
|---|---|---|---|
| Behaviour: skills, stats, damage, energy, recharge | (b), server-side | **Free, today** (`studies/skills/FINDINGS.md` §5) | Everything mechanical |
| Attribute names | R4 + `datwrite` | **Nine reserved slots, MEASURED; needs L3** | Authored attribute identity |
| Skill / attribute icons | `studies/texture/FINDINGS.md` | **OBSERVED, closed end to end 2026-08-06** | Authored art inside the provenance gate |
| Profession label + abbreviation | R4, static PE repoint | **Same shape as `repoint_skill.py`** | The name on every surface that reads the id |
| Anything the static repoint misses | R3, one-shot detour | **~60 lines `ctypes`, hours** | The residue |

**What this delivers.** A character whose profession label, abbreviation, attribute names,
skill set, stat behaviour and skill icons are entirely ours, riding profession *N*'s id, on
the owner's own client, with **zero ArenaNet bytes in the repo** — because every piece of
it is an *id* committed to git and a *string or texture* resolved at run time from the
owner's own archive. That is the `mapbuild.py` pattern, and it is the strongest evidence in
either document that (c) stays inside the gate.

**What still lies.** Body scale, hair and skin palette, armour silhouette, animation set,
the profession glyph, and any text surface the three name arrays do not reach (the caller
counts are documented floors — `--xrefs` does not see indirect or computed addressing).

### 5.2 Composition B — (a)-lite: profession 11 borrowing profession *N*'s art

This is the shape that only appears when R1's, R3's and R2's measurements sit in one place:

1. **R1** — one 5-byte patch. Index 11 stops ending the session.
2. **R3** — a detour on each profession-keyed accessor. For *identity* tables (name,
   abbrev, chapter, scale) return **our** value for 11. For *art* tables (colour palettes,
   costume searches, composites) return **profession *N*'s** value for 11.
3. **Nothing needs a spare row.** The detour never indexes the array, so pass 1's four
   growth shapes plus §4.2's aliasing fifth all become irrelevant simultaneously.
4. **R2 is optional**, needed only if a detour outgrows 78 bytes and wants a section rather
   than `VirtualAllocEx`.
5. **R5** says nothing in the client objects, and that byte-shape signatures survive a
   build gap.

**This is a shape, not a plan, and the difference is the whole of §6.** It is not costable
today for two reasons, both of which are cheap to retire and neither of which anyone
retired:

- **Does the composite art gate have a single hookable choke point?** If yes, the redirect
  gives profession 11 an existing profession's armour for free, and **(a)'s last hard
  blocker dissolves**. If no, it is back to art we cannot author. **NOT FOUND. W1.**
- **How many accessors are there?** At least ten, found by accident rather than by census.
  **W2.**

**INFERRED**, standing on: R3's measurement that every *named* table has one accessor
(MEASURED); R1's measurement that the assert is one site (MEASURED); pass 1's measurement
that the composite chain bounds profession before loading a resource (MEASURED). **It does
not stand on any measurement of the composite path's internal structure, because none
exists.**

### 5.3 What composition does *not* fix

Being explicit, because the temptation here is to let a stack of "plausible" read as
"solved":

- **The glyph consumer is still unlocated** after two independent bounded attempts. A
  detour cannot hook a function nobody has found.
- **The census ceiling is unknown.** Every route's cost is per-table; an unbounded table
  count is an unbounded cost.
- **Per-build maintenance multiplies, it does not divide.** R3 moves signature resolution
  from authoring time to launch time. It does not reduce the count, and this pass raised it.
- **Live cross-process writes are new operational ground** with no guard, no test, and a
  failure mode this repo's only crash-evidence channel may not observe — and R1's patch, if
  also applied, disables that channel image-wide. *Those two interact badly and should not
  be enabled in the same session without W4 answered.*

---

## 6. Removes an obstacle vs achieves the goal

Pass 1 listed the blockers to (a). Scored honestly, one row per blocker, "cleared" meaning
*a measurement says the obstacle is gone*, not *a route exists that might address it*:

| # | Pass-1 blocker | Status after this pass | By what |
|---|---|---|---|
| 1 | 29 bound checks, each a session-ender | **CLEARED** — 5 bytes, one site | R1, MEASURED (1 direct caller) |
| 2 | ≥8 backing tables, zero spare row | **NOT CLEARED, but BOUNDED — and the count did NOT go up.** ~13 lookups over ~11 arrays, enumerated | §4.3 as corrected, §8-W2 (run) |
| 3 | Two `imul`-strided 2-D tables (now three) | **CLEARED IN PRINCIPLE** — a detour never indexes them | R3, INFERRED from the accessor measurement |
| 4 | 12-slot code jump table | **CLEARED, cheaply** — slot 11 already aliases slot 0; 8 bytes of padding follow it; the bound is a 1-byte immediate | R2 + pass 1, MEASURED |
| 5 | Two compiler-unrolled stack lookups | **CLEARED IN PRINCIPLE** — a detour replaces the function | R3, INFERRED |
| 6 | Armour composite four-axis art gate | **CLEARED — and it was never an art gate.** One accessor (`0x005AE200`, 3 callers) over two 132-entry **pointer** tables; professions 0/1/2/9 already share a row, so a redirect is a **24-dword copy of values already in the image**. Caveat: 88/132 of table A is runtime-populated | W1, **run after synthesis**; MEASURED twice |
| 7 | Profession glyph consumer unlocated | **NOT CLEARED** — second bounded attempt also failed | R4, NOT FOUND |
| 8 | Character-creation picker construction unknown | **ANSWERED** — loop over a compile-time 11; one more immediate + one array row | §4.4, MEASURED |

**Six cleared or clearable, one answered, one remaining — and the one remaining is a
locate-it problem, not a wall.** The two rows this section originally scored as survivors
were blocker 2 and blocker 6, and **both were wrong when first written**:

- **Blocker 6 was scored NOT CLEARED and called the one thing engineering cannot move.** It
  is cleared, and it was never an art problem — see §1. This was the document's central
  refusal and it did not survive four tool calls.
- **Blocker 2 was scored "count went UP" on two tables found incidentally.** Both were
  aliases of arrays pass 1 had already counted (§10). The surface did not grow; it is now
  enumerated at ~13 lookups over ~11 arrays, each behind one accessor.

So the honest state of (a) is no longer "unbounded on four fronts" (pass 1) or "blocked on
art" (this document's first draft). **It is: one unlocated UI consumer, a census that is
bounded but not provably complete, tooling that does not exist yet, and zero precedent
anywhere for writing content into a compiled client table.** Those are costs and risks, not
walls.

**The discipline this section enforces, stated plainly.** Neutering the assert does not add
a row to an 11-entry array. Confirming that `.reloc` covers a disp32 does not grow a table.
Proving that `CreateRemoteThread` ships in five projects does not put an eleventh
profession on a character-select screen. Every route in §2 removes an obstacle; **not one
of them, alone, achieves the goal.**

**But this section also has to be honest about its own failure mode, which is the opposite
one.** Both rows it originally scored as immovable were scored that way *without the
measurement that would have settled them*, and both inverted within minutes of somebody
taking them seriously. Refusing to count a route until it is proven is correct; **scoring a
blocker as permanent because nobody looked is not the same thing**, and this table did that
twice in one pass.

---

## 7. The decision

Five real options. The costs are the ones measured above, not estimates.

**Option 1 — Do (b) and stop.** Zero cost, available today, needs nothing from either
document. Custom skills, stats, damage, energy and recharge on an existing profession id.
*What you give up:* every element of identity. The label lies.

**Option 2 — Do (b) + (c). ★ Recommended.** Days to two weeks, mostly experiments.
Adds authored attribute names in the client's own nine reserved slots, authored icons
(OBSERVED-closed), and an authored profession label through a `repoint_skill.py`-shaped
tool. **No new dependency, no new dependency class, no licence row, no live-process
writes.** Inherits `studies/datwrite/FINDINGS.md`'s standing archive-durability unknown and
the compression-8 flip-to-stored step. *What you give up:* body scale, palettes, armour,
animations, the glyph.

**Option 3 — Option 2 + the accessor detour ((c)+).** Adds weeks and a real capability
decision. Buys the identity surfaces a static repoint misses, plus the ability to make one
profession id present differently without touching any table. **Costs: a new live
cross-process write path outside the launch cage, a PID-provenance guard that must be built
first, an AV/EDR interaction this repo has never had, and per-build re-derivation of ~10–12
accessor signatures.** Recommend only if Option 2 lands and the residue is visible enough
to be worth it.

**Option 4 — Pursue (a)-lite (§5.2). Now costable, because W1 and W2 have been run.**
The original text here said *"not costable today, and that is a statement about two
unanswered offline questions, not about difficulty"* — and then ranked those questions #1
and #2 without running either. Both were run after synthesis, in minutes. What they bought:
the composite gate is a redirect rather than art (§1), and the table census is bounded at
~13 lookups over ~11 arrays (§8-W2). **(a)-lite is now a build estimate rather than an
unknown** — R1's five bytes, R3's ~60 lines of `ctypes`, ~13 accessor signatures relocated
per build, and the composite row copied as 24 dwords.

**Option 5 — Pursue (a) proper. The refusal is WITHDRAWN, by this section's own stated
criterion.** The original text refused it because *"the armour composite gate needs real
per-combination art we can neither derive nor commit"*, and added: *"if W1 says the
composite path has one choke point, this option becomes Option 4 and the refusal is
withdrawn."* **W1 says exactly that** — one accessor at `0x005AE200`, three callers, two
pointer tables, and four professions already sharing a row in ArenaNet's own shipping
configuration. The condition the document set for itself has been met, so the refusal goes.

What refuses (a) *now* is not a blocker but a bill: unbuilt tooling (a PE section appender
this repo has never written, a cross-process write path it does not have), a census that is
bounded but not provably complete, an unlocated glyph consumer, and **no precedent anywhere
in five reimplementations for writing content into a compiled client table**. That is a
real project with a real tail. It is not impossible, and this document should not have said
it was.

### Recommendation

**Option 2, ridden on profession 0 — and treat (a) as open rather than closed.**

Option 2 remains the recommendation: it is the only row in §2 that is a deliverable rather
than a capability, it needs nothing this repo does not already have working and tested, it
stays inside both gates by construction, and its unknowns are one caged loopback probe each
rather than an unbounded tail.

**One correction to it, and it matters more than its size suggests: ride profession id 0,
not a shipped profession.** This document says "an existing id" nine times and never asks
*which*. Repointing a shipped profession's name id changes that label for **every Warrior
in the game**; profession 0 has no such collateral. And it is fully provisioned — MEASURED
this pass: name id 2040, abbreviation 2049, chapter 0, second-array 2058, a jump-table slot,
and a composite row *byte-identical to professions 1, 2 and 9*. It is owned by no shipped
profession, carries zero attribute rows, and no player character can be it. Two known
obstacles, both ours to change: at least one lookup guards it explicitly (`test esi,esi` at
`0x005AB47B`), and `agents.py`'s `CHAR_PROFESSIONS_MAX` refuses it from below.

**On (a): the honest position is now "unbuilt", not "blocked".** Both of this document's
stated hard blockers dissolved when someone finally measured them. That is not a reason to
build it — the bill in Option 5 is real and the absence of precedent is a genuine risk —
but it is a reason not to file it as impossible, which is what both passes did on evidence
that took minutes to overturn.

**And the meta-lesson is now the most reliable finding in either document.** Pass 1's
top-ranked risk was five minutes of work that six agents each filed as somebody else's
scope. This document quoted that lesson, instructed its reader to *"be suspicious of
anything everyone is deferring"*, and then deferred its own #1 and #2 rungs through six
tracks, six verifiers and a synthesis. Both, when run, inverted a headline. **Treat "an
afternoon" in any ladder here as an admission that nobody has tried, and run the cheap thing
before writing the confident sentence.**

The call is the owner's. This document's job was to make it cheap to make — and its own
history is the argument for making the cheap measurement first.

---

## 8. The ladder

Cheapest first, dependency-ordered, **offline before launch**. Each states its **question**,
its **prediction** and **what to watch** before its method — a probe with no stated
expectation can be rationalised into agreeing with anything afterwards.

Every launch rung inherits the house rules and they are written into the rung: ours-DH
build, verified cage, loopback only, `cage.assert_launch_safe`, named account, archive
writes only ever against a **copy**.

**Ranked by information-per-hour, not by comfort.** W1 and W3 are near the top precisely
because they are the ones that were deferred.

> ### Post-synthesis status — read this before running anything below
>
> Three rungs changed after this ladder was written. The original text of each is kept
> intact, because a prediction stated before its result is the only reason to trust the
> result — and in W1's case the prediction was right while the *method* was wrong.
>
> | Rung | Status | What changed |
> |---|---|---|
> | **W1** | ✅ **RUN, and the prediction HELD.** Single accessor, `0x005AE200`, 3 callers. | Took ~5 minutes, not an afternoon. **Its method line below is wrong** — see the correction under it. Result in §1; it refutes this document's original headline. |
> | **W2** | ✅ **RUN.** 235 `arrsize` sites, **8 profession-bounded arrays**. | Took ~10 seconds, not an hour. But it is a **partial enumerator, not a census closer**: it names no costume array, neither composite array, and not the jump table, because those asserts are worded on the constant rather than on `arrsize`. |
> | **W3** | ⛔ **CANNOT SUCCEED AS WRITTEN.** | Its target `0x00C0EEC0` lies in `.data`'s **uninitialised tail** (MEASURED — past `SizeOfRawData`), so there are no file bytes to read. A reader would get 51 zeros and report "the reserved rows are null" — confidently wrong. Re-specify as a **runtime** read via `keytap.py`'s ReadProcessMemory against a live caged client, or let W8 carry it. W3's *second* half (`--dis 0x0081A020`) is still offline and still worth doing. |
>
> W1 and W2 were this ladder's #1 and #2 by its own ranking, and both were deferred by six
> tracks, six verifiers and the synthesis. Between them they cost about five minutes and
> inverted a headline. **That is the ladder's most useful output and it is not in any rung.**

---

**W1 — Does the armour composite gate have a single choke point? Offline, one afternoon,
no launch. The highest-value item in this document.**

> **Question.** Does the four-axis chain at `0x008322A0` (profession `< 11` at
> `0x008322AC`, then `< 6`, `< 8`, `< 2`, then `call 0x00777F10` at `0x00832321`) read its
> profession-keyed data through a **single accessor function** — the shape every one of the
> ten named tables has — or does it index inline, or fan out to several sub-tables?
>
> **Prediction.** **Single accessor, or at most two.** Standing on the measurement that
> every profession-keyed table in the image found so far has exactly one reading instruction
> inside one small `int3`-bounded function, and that the four bound checks are chained in
> one function before a single resource call rather than scattered. **If the prediction
> holds, a detour mapping profession 11 → profession *N* gives an eleventh profession an
> existing profession's armour with zero authored art, and (a)'s last hard blocker
> dissolves.** If it fans out, (a) stays refused and this document's §6 scoreboard is final.
>
> **What to watch.** `--dis` through `0x00777F10`'s callees, then `--xrefs` on whatever
> table base appears, looking for the one-reader/one-accessor signature. Watch for the
> opposite tell too: several disp32 bases inside one function body is the fan-out case.
>
> **Method.** `codescan.py --dis 0x008322A0` and `--dis 0x00777F10`, then `--xrefs` on every
> absolute address either body touches. Bundle `asserts.py --at` on each to name the module.
>
> **Why it is here.** Pass 1 filed it NOT FOUND. All six tracks this pass named it and every
> one filed it as out of scope. It is the only remaining blocker that engineering cannot
> route around, and nobody has spent an afternoon on it.
>
> ---
>
> **RESULT — the prediction held; the method above is WRONG and would have produced a false
> negative.** Correct the method before anyone re-runs this.
>
> **`0x00777F10` never receives profession at all.** At `0x0083231E` it is called with
> `([ebp+8], ebx=component, lea eax [ebp-8], 0)`. Profession goes to `0x00832080` instead
> (`push edi` at `0x00832351`), and *that* is what calls the accessor. A reader following
> "`--dis 0x00777F10`, look for the profession-keyed accessor" finds no profession use and
> files **"it fans out — back to art"**, which is this document's original wrong conclusion
> reached by a second route.
>
> **Corrected method:** `--dis 0x00832080`, then `--dis 0x005AE200`.
>
> **What it found** (MEASURED, two readers): accessor `0x005AE200`, `int3`-bounded, `ret` at
> `0x005AE2BE`, **3 direct callers**; profession is arg0, bounded `< 0xB` at `0x005AE209`;
> index is `component + 6·axis2 + 12·profession` — **the axis name is CORRECTED to
> `blitId + 6·sex + 12·profession` 2026-08-19, see line 110** — so profession is the **outer** axis and the
> growth shape is **append, not re-stride**; two parallel 132-entry dword arrays at
> `0x00BF4018` / `0x00BF4228`, exactly 528 B apart, 17 distinct values each, table B
> resolving 132/132 into `.rdata` — **pointers, not art**; and **only 8 distinct profession
> rows, because professions 0, 1, 2 and 9 already share a byte-identical row.**
>
> **Caveat to carry:** 88 of table A's 132 pointers land in `.data`'s uninitialised tail and
> are runtime-populated, so the static 24-dword copy is proven for table B only. Table A
> wants the detour form or a runtime check.

---

**W2 — Close the profession-keyed table census. Offline, an hour. Bundle with W1.**

> **Question.** How many profession-keyed tables are there, and what is each one's real
> source symbol name and growth shape?
>
> **Prediction.** **More than ten, and at least one more aliasing shape.** Standing on: pass
> 1 named eight, this pass found two more *by accident* in a region already open, and three
> of the four `ConstCostume` tables carry a compiled-in ten against a bound of eleven. If the
> count comes back at exactly ten, that is itself informative — it would mean the surface is
> bounded and (a) becomes costable.
>
> **What to watch.** The 10-vs-11 anomaly in §4.3. Either ArenaNet's own `0x00BBD690` has a
> latent one-row overrun at the top profession id, or our axis attribution is wrong. Both
> are worth knowing and the sweep should distinguish them.
>
> **Method.** `asserts.py --exe $EXE --grep arrsize` — the grep pass 1's reproduce section
> already prescribes, that five tracks cited and none ran, across two passes. Then `--xrefs`
> on each named base and `--dis` on each accessor.

---

**W3 — Is the 51-entry pointer array at `0x00C0EEC0` populated at the reserved rows?
Offline, minutes.**

> **Question.** Do the nine reserved attribute rows (26, 27, 28, 45–50) carry valid non-null
> pointers in the runtime array at `0x00C0EEC0`, or nulls/sentinels?
>
> **Prediction.** **Non-null, because the array is built from the 51-row definition table at
> startup rather than compiled in.** Standing on: it is bound-checked `< 0x33` at
> `0x005A9265` identically to the definition table, and it is reached by a **binary search**
> over sorted `(key, ptr)` pairs. **If non-null for all 51, the reserved rows are
> structurally live and L3's central question may be pre-answered without a launch.** If the
> nine read null, `(c)`'s attribute half needs a second patch and L3 must run.
>
> **What to watch.** Also settle the survey's own internal disagreement: R4's C5 asserted the
> array is keyed by *attribute id, never profession*, while R4's C6 found one of its four
> callers (`0x0081A06A`) passing the **same register** to both a profession-bounded chapter
> accessor and this lookup with no intervening reassignment. Those two cannot both be right.
>
> **Method.** Read 51 dwords at `0x00C0EEC0` via `gwpe.PE`; census null vs non-null. Then
> `--dis 0x0081A020` to resolve the key domain.
>
> **Why it is here.** R4's verifier named this as a missed offline check that could
> substitute for a live probe. Nobody ran it. Same pattern as W1.

---

**W4 — Is the early return at `0x00489570` reachable from the assert chain? Offline, an
hour.**

> **Question.** Two direct-encoded stores clear the flag at `0x00BEC120`, and a third site
> returns early when it is zero. Is `0x00489570` (or its only caller, the shutdown-shaped
> routine near `0x0048B0A0`) reachable from `0x00487BC0` → `0x00488210` → `0x005BC094` →
> `0x005BBF04`, e.g. as a registered `atexit` handler or SEH unwind target?
>
> **Prediction.** **Not reachable from the assert chain.** Standing on the shape: both stores
> clear the flag and then reach `0x005D5E70`, and the early return guards the routine that
> would call it — a re-entrancy/cleanup guard, not a report-and-continue switch. If it *is*
> reachable, "ArenaNet ships no non-fatal mode" is wrong and R1 gets cheaper still.
>
> **What to watch.** The remaining sites of the nine that reference `0x00BEC120`; only three
> have been characterised.
>
> **Method.** `--xrefs 0x00489570`, `--xrefs 0x0048B0A0`, then walk the CRT terminator's
> handler registration.

---

**W5 — Retire the section-append assumption on a synthetic PE. Offline, hours. Zero
ArenaNet bytes.**

> **Question.** Will Windows load and run a PE32 whose section table we grew by hand?
>
> **Prediction.** **Yes.** Standing on: 7 free 40-byte header slots, `SizeOfHeaders` (`0x400`)
> exactly accommodating 12 entries, and the fact that nothing validates checksum or
> signature. If it fails, R2 is closed and the 78-byte ceiling becomes hard.
>
> **What to watch.** `SizeOfImage` arithmetic, alignment, and the Authenticode directory —
> the three places a hand-rolled appender gets it wrong.
>
> **Method.** Hand-build a tiny synthetic PE32 stub with unrelated placeholder code, add one
> `IMAGE_SECTION_HEADER`, grow `SizeOfImage` and `NumberOfSections`, append raw data, and
> relocate or strip the trailing security block. Run it. **No client bytes are involved
> anywhere in this rung.**

---

**W6 — The cross-process write primitive and its guard. Offline, hours. No client.**

> **Question.** Can `keytap.py` be extended to `VirtualAllocEx` / `WriteProcessMemory` /
> `VirtualProtectEx` in pure `ctypes`, and can a PID be resolved to a safety verdict before
> any write?
>
> **Prediction.** **Yes to both.** The write half mirrors bindings already in the file, and
> the guard is a composition of two things that already exist — `session.py:264`'s
> `image_name(pid)` via `QueryFullProcessImageNameW`, and `dhbuild.classify(exe)`.
>
> **What to watch.** **Build the guard first and make it refuse.** A write path that can
> reach a process it did not launch through the cage is the actual risk here; the API
> bindings are the easy half. Test the refusal against a `C:\gw` PID before testing the
> write against anything.
>
> **Method.** Extend `keytap.py`; write `test_keytap.py` sections for the refusals before the
> positives, per this repo's own pattern. **This rung stops at a passing test suite — no
> client is patched and none is launched.**

---

**W7 — The name-repoint probe. One caged loopback launch, zero authoring, zero archive
writes.** *This is pass 1's L2c, unchanged and still the cheapest launch rung.*

> **Question.** Which surfaces resolve a profession's name and glyph through the PE arrays'
> string ids?
>
> **Prediction.** **The name changes everywhere; the glyph does not change anywhere.** This
> pass adds a testable refinement: the **compound "Class1/Class2" label** should follow too,
> because both its full-name (`0x2FF`) and abbreviated (`0x33A`) forms resolve through the
> same two accessors — so nameplates, party window and hero panel should all move together,
> and any one that does not has its own hard-coded source.
>
> **What to watch.** The *split*. A widget that does not follow the id is a widget with its
> own source, and that is the measurement.
>
> **Control.** A second profession left untouched in the same session.
>
> **Method.** A `repoint_skill.py`-shaped analogue re-pointing `s_charProfession[n]`'s name
> id at a different **existing** id. Needs pass 1's L0 only.

---

**W8 — The reserved attribute probe.** *Pass 1's L3, unchanged, unless W3 pre-answers it.*
Needs L0.

**W9 — The profession-11 probe, with and without the assert patch.** *Pass 1's L4, plus a
second arm this pass makes possible.*

> **Question.** With the 5-byte patch at `0x00487C11` applied to a scratch copy, does the
> client survive all three actions (party window, attribute panel, nameplate render) that
> currently end the session?
>
> **Prediction.** **It survives all three and renders wrong**, because the append-shaped
> tables are read-only image reads and the jump table's slot 11 is populated. If it crashes
> instead, some site uses the index for a **write**, which §3.1 flags as unchecked at 28 of
> 29 sites.
>
> **What to watch.** Run the unpatched arm **first**, so the patched arm has a baseline. And
> note the cost: with the patch applied, `read_error_dialog.py` finds nothing for **any**
> assert in the client, so the two arms cannot share a session and the patched arm has no
> crash-evidence channel at all. Order matters more here than anywhere else in the ladder.

---

**W10 — (c), delivered.** *Pass 1's L6, unchanged.* Needs W8 green.

---

## 9. Open items and NOT FOUND

These are results.

| Question | Status | What would answer it |
|---|---|---|
| Does the armour composite gate at `0x008322A0` read through a single accessor? | **NOT FOUND — every one of six tracks filed it out of scope** | **W1.** Decides whether (a)-lite exists at all |
| How many profession-keyed tables are there? | **≥10, census open.** Two found by accident this pass | **W2.** The `arrsize` sweep, prescribed in pass 1, unrun in two passes |
| Are the nine reserved attribute rows populated in the runtime pointer array at `0x00C0EEC0`? | **NOT FOUND** | **W3.** Minutes, offline, may pre-answer W8 |
| Is `0x00C0EEC0` keyed by attribute id or profession id? | **CONTESTED within this pass** — one surveyor claim asserts attribute id; the same surveyor's other claim shows a caller passing a profession-bounded register | **W3**, second half |
| Which widget resolves the profession glyph? | **NOT FOUND** — second independent bounded attempt (the ATEX validator's 2 callers) also came up empty | **W7.** Format half stays closed (`studies/texture/FINDINGS.md`, OBSERVED) |
| Is `0x00489570`'s early return reachable from the assert chain? | **NOT FOUND** — 3 of 9 sites referencing `0x00BEC120` characterised | **W4** |
| Does the 3-axis table `0x00BBD690` have a latent one-row overrun at profession 10, or is our axis attribution wrong? | **Open, found this pass** | **W2** |
| Does the picker loop function belong to `CrProfession.cpp`? | **Open.** Behaviour MEASURED; module attribution rests on a flat 2,000-byte window, and the function's own only assert is a generic template check | `asserts.py` with a function-scoped span, or a symbol-bearing site inside `0x004D90F0`–`0x004D93DC` |
| Is the Vendor jump table's slot 11 a real twelfth value or code-folding? | **CONTESTED.** Advanced one level (pushed as a callback pointer at 2 sites, never called directly); the widget is still unlocated | Trace the two push sites' registration |
| Does an indirect (register or vtable) call reach `0x00488210`? | **NOT FOUND** — `--xrefs` cannot search that shape | A different method; implausible for a private non-virtual helper, not provably absent |
| What is the exact `datplan` edit count for an in-container empty-record fill? | **NOT FOUND** — the cited 7-edit/4,184-byte figure measures a *different* operation (a new top-level file) | Run `datplan.py` against a copy, once writer tools are permitted |
| Do `d3d9`/`xinput` name strings actually reach `LoadLibrary`? | **Open** — strings present in `.rdata`, call sites not disassembled | An hour with `--dis`; only matters if the DLL-proxy route is pursued |
| Do the reserved attribute ids and the primary flag hold on the 2026-04-30 build? | **Open** (carried unchanged from pass 1) | One re-run |
| Is `s_attrib` write-safe — does anything else reference the reserved rows? | **Open** (carried unchanged from pass 1) | `--xrefs` on `0x00A35740` + *n*·20, needed before W10 |
| **Which profession-adjacent on-screen surfaces are SERVER strings rather than client-table lookups?** | **NOT FOUND — and nobody has asked.** Both passes assumed identity is entirely client-table-resolved | The cheapest identity in the whole ledger: zero client patching, zero archive writes, zero per-build maintenance. This repo has already proven the server can put arbitrary UTF-16 on the wire (`string16`, 22,524/22,524 re-encoding to ArenaNet's own bytes) and that agent names are server-supplied. Sweep the catalogue for profession-adjacent string fields, then check them against a live capture |
| Does riding **profession 0** avoid the collateral of repointing a shipped profession's label? | **Open, and it is now the recommended host id** (§7) | MEASURED provisioned: name 2040, abbrev 2049, chapter 0, second-array 2058, jump-table slot, composite row shared with 1/2/9. Two known obstacles, both ours: `test esi,esi` at `0x005AB47B`, and `agents.py`'s `CHAR_PROFESSIONS_MAX` refusing it from below |
| ~~What is the second `s_charProfession`-named array at `0x00A38868` for?~~ | ✅ **CLOSED — it is the character-creation picker's label list.** Carried open from pass 1 §13 | §4.4 measures the picker resolving it through accessor `0x005AB840`; R3 measures that accessor at exactly 1 caller. Both facts were already in this document (§10-F8) |

---

## 10. Corrections ledger

Recorded rather than overwritten, per house style.

### A. Refuted by a verifier — the corrected claim is what appears above

**A1 — "No direct-encoded instruction stores to `0x00BEC120`." REFUTED.** Two exist:
`mov dword ptr [0xbec120], 0` at `0x00487B53` and `0x004895A2`, both the canonical
`C7 05` ModRM+disp32+imm32 form — precisely the addressing shape the surveyor's own caveat
said the scan *could* see. The verifier confirmed them three independent ways; **the
synthesist confirmed both a fourth time by direct disassembly.** Instructive because it is
the same class of decode error the *same surveyor* caught correctly for a different address
in the same pass, applied unevenly to the one address it called "the single most valuable
thing this track could find". Both stores sat inside the 9-hit list the survey said it
decoded by hand.

**A2 — "Every bound check on `0x00BEC120` converges; never an early return." WEAKENED.**
True at the two sites examined; a third at `0x00489570` has a genuine `ret` at `0x004895B1`
gated directly on the flag. 2 of 9 sites were examined. The conclusion — no compiled-in
non-fatal assert mode — survives on the *shape* of the third site (a cleanup guard), not on
the search that was run. **W4.**

**A3 — "The costume-hat table at `0x00BBE680` is a simple direct-indexed array." REFUTED.**
It is a bounded linear search, stride 40, up to 59 iterations — structurally the same as
costume body. The surveyor had disassembled a **different, uncatalogued** table
(`0x00BBE658`, reached by a different assert site) and reported it under costume hat's
name. **Synthesist re-confirmed by disassembling `0x008EE2B0` directly.** The correction
propagates: the route's own cost estimate priced costume hat as a simple relocation, which
it is not.

**A4 — "Nothing in this repo resolves a running PID back to its exe path." REFUTED.**
`toolkit/harness/session.py:264` already does, via `QueryFullProcessImageNameW`. The
surveyor's grep searched injection-technique terms, not PID-resolution terms. **This makes
R3 less blocked than its own survey presented**, which is worth flagging in a document
whose failure mode is optimism.

**A5 — Citation slips that a literal re-run would not reproduce.** R4's evidence line
describes `--xrefs` on three *array* addresses returning 31/4/1; those addresses each return
**0 direct references and 1 word**. The 31/4/1 are the *accessor functions'* caller counts
and are correct at the right address. R2's claimed jump-thunk target is off by one byte
(`0x005A59C0`, not `0x005A59C1`). R2's import count is 482 for 38797 but **478** for the
older build, stated as one figure for both. R6 counts "three languages" for five files
spanning four, and 113 lines as 114. None changes a conclusion; all four would fail a
naive re-run, which is the point of recording them.

### B. Weakened

**B1 — "This pass found a second, non-overlapping cluster of profession-11 sites."**
The measurement is real and reproduced; the *novelty* is not. `FINDINGS.md` §12-B5 already
records that an `arrsize`-based grep recovers sites sharing the identical compiled bound
outside the symbol census, and states outright that the gate is more pervasive than the
census shows. This pass adds concrete accessor VAs and caller counts to a phenomenon
already on the record. **This document's own §4.3 and §4.4 are the genuinely new part** —
the count going to ≥10, and the picker's assert-less loop bound.

**B2 — "The `push <line>` literal makes cross-build relocation fragile."** The byte pattern
is real, but `asserts.py`'s `grep()` matches on the assert's **expression string**, never
the line number — read from the tool's source by the verifier. The stated fragility
mechanism does not describe how the census actually relocates across builds, and pass 1's
own 29/13 cross-build reproduction is direct evidence the real anchor survived. The
narrower true gap — that the disp32 table address has no structural self-check the way the
skill table's `id == index` invariant provides one — is smaller and different.

**B3 — "`repoint_skill.py` needed an adjacent ArenaNet string to kill six false
candidates."** Its own docstring says the fix was an index-identity constraint (the first 64
ids equal their own index); the string cross-check is a separate, later corroboration
applied after the table is already uniquely found. A misattribution inside an otherwise
sound maintenance-cost argument.

**B4 — "All 5 reads of the updater-disabled global are plain `cmp [addr],0`."** Four are;
the fifth (`0x00834064`) is `xor eax,eax / cmp [addr],eax / sete al / ret` — functionally
equivalent, not literally as described. The disjointness conclusion is unaffected.

**B5 — Two threads a survey's own tooling surfaced and then dropped.** `VirtualProtect`
appears in R5's own "interesting imports" output and its call sites were never
investigated, despite being the import most directly relevant to the `.text`-writability
question the track existed to answer; the verifier traced both (`0x005E77F0`, `0x0090BF4E`)
and found `__fastfail`-guarded CRT memory-probe boilerplate. `OutputDebugStringA` is
present on 38797 and **absent** on the 2026-04-30 build — a real build asymmetry invisible
to the scan because its "interesting import" set matched the bare name without the `A`/`W`
suffix. Neither overturns anything; both are live threads closed by omission rather than by
evidence.

### C. Verdict adjudication

**No verifier called a verdict TOO OPTIMISTIC.** One (R3's) explicitly noted its
corrections made the route *less* blocked than its own surveyor presented — two of four
stated blockers were overclaimed. That is worth naming in a document whose default risk is
the opposite: **on this pass the surveyors were, on balance, more pessimistic than their
evidence supported, and the corrections ran toward the routes being cheaper.** This
document's §6 scoreboard exists to keep that from reading as "therefore (a) is reachable."
Five obstacles cleared out of eight is five out of eight, and the two that remain are the
two that were always going to be hardest.

### D. Provenance violation caught in a survey and stripped here

**R6's own report reproduced ArenaNet's compiled assert file name together with its
compiled condition text**, read out of a third party's (MIT-licensed) source rather than
from our own disassembly. `CLAUDE.md`'s boundary refuses that pairing regardless of who
extracted it — a permissive licence covers *that project's* code, not ArenaNet's embedded
string. **It is stripped from §3.6 above**, which reports the mechanism (scan for the
assert's own strings, write `0xEB` over the conditional jump) and the class of check
defeated, without either string. Logged here because the finding *about* provenance risk
was itself the provenance risk, and because pass 1's §12-E already records three
stale-or-wrong citation failures in a row — this is the fourth in the same family.

### E. Found during synthesis

**E1 — The picker's arity is enforced by an assert-less loop bound.** `cmp ebx,0xb` at
`0x004D93CD` (bytes `83 FB 0B`), invisible to `asserts.py --grep CHAR_PROFESSIONS`. See
§4.4. This answers pass 1's L2b, explains pass 1's own unexplained "none of the 29 is in
`CharCreate`", and adds a second sense in which the assert census is a floor: it misses
every bound enforced *without* an assert, not only unreadable asserts.

**E2 — Three `ConstCostume` tables carry a compiled-in *ten* against a bound of *eleven*.**
§4.3. Either a latent overrun in ArenaNet's own shipped code at the top profession id, or
our axis attribution is wrong. Neither reading was resolvable in the time available and
both are worth writing down.

**E3 — R1's patch and R3's write path interact badly and no track owned the interaction.**
R1's patch disables `read_error_dialog.py` image-wide; R3's failure mode is a fault that
this repo's only crash-evidence channel may or may not observe. Enabling both in one session
removes the last machine-readable signal from the one activity most likely to need it.
Folded into W9's ordering.

### F. Found AFTER synthesis, by the completeness critic — and this is where the pass's real
### findings are

A seventh reader was asked only *what is missing*. As in pass 1, it moved the answer more
than any survey track did. **Every item below was re-verified by the orchestrator against the
binary before being folded in; all of them held**, including their caveats.

**F1 — The armour composite gate is not an art gate, and this document's headline was
wrong.** §6 blocker 6 scored it *"NOT CLEARED. Nothing touches it"*; §1 called it the only
blocker engineering cannot move; §7 Option 5 refused (a) on it. It is one accessor over two
pointer tables, with four professions already sharing a row. Full result in §1 and W1.
**Cost of the check that overturned it: four tool calls.** Orchestrator re-verification: 3
callers confirmed exactly (`0x008320B8`, `0x008321FB`, `0x0083247E`); table separation 528 B
confirmed; 132 entries and 17 distinct values confirmed in both tables; table B 132/132 into
`.rdata` confirmed; **8 distinct profession rows with `{0,1,2,9}` sharing confirmed**; table
A's 88/132 uninitialised-tail caveat confirmed.

**F2 — W1's own method line pointed at the wrong callee.** `0x00777F10` never receives
profession. Anyone re-running W1 as originally written would have reproduced this document's
wrong conclusion by a second route. Corrected in the rung.

**F3 — "The table count went UP to ≥10" was double-counting.** Both "newly found" tables are
aliases of costume arrays pass 1 already counted, reached through their general accessors
rather than their search loops (`0x00BBD690 ≡ 0x00BBD73C`, `0x00BBE658 ≡ 0x00BBE680`; each
folded base is row *esi*=1 of the same array). Worse, `0x00BBD690` is **not a table at
all** — because `esi ≥ 1` the array is never read at its folded base, which lands inside the
preceding assert-string pool and decodes as a source path. §6 blocker 2 and W2's prediction
both rested on this.

**F4 — W3 cannot succeed as written**, and would have produced a confident false null. Its
target is in `.data`'s uninitialised tail. Confirmed by the orchestrator. Re-specified in the
ladder.

**F5 — Two routes neither pass considered.**
*(a)* **Ride profession id 0.** The document says "an existing id" nine times without asking
which; repointing a *shipped* profession's label changes it for every character of that
profession. Profession 0 is fully provisioned (MEASURED: name 2040, abbrev 2049, chapter 0,
second-array 2058, composite row shared with 1/2/9), owned by nobody, and carries zero
attribute rows. Folded into §7's recommendation.
*(b)* **Server-authored text surfaces.** Both documents treat profession identity as entirely
client-table-resolved. This repo has already proven the server can put arbitrary UTF-16 on
the wire (`string16`, 22,524/22,524 re-encoding to ArenaNet's own bytes) and that agent names
are server-supplied. **Which profession-adjacent on-screen surfaces are server strings rather
than client-table lookups is a question nobody has asked** — and it is identity with zero
client patching, zero archive writes and zero per-build maintenance. The cheapest column in
the ledger, and it is empty. Added to §9.

**F6 — The detour model survives a deliberate attempt to break it.** Per this pass's own
warning that *a hook intercepts a call and inline indexing is not a call*, the critic
attacked R3's three hardest cases and could not: the four costume tables are four separate
`int3`-bounded accessors, the compiler-unrolled stack lookup at `0x005AB470` is a genuine
standalone function with profession as arg0, and the composite accessor is standalone.
**An unverified "it works" reads identically to a verified one until someone checks**, so
this is recorded as checked.

**F7 — Maintenance measured for the three signatures the recommendation actually needs.**
R5 measured six; the composite and two costume accessors were not among them. All three are
**unique-hit on both builds** with non-uniform drift (composite `0x1AD691`→`0x1AB321`;
costume 3-axis `0x4ED5AD`→`0x4E337D`; costume 2-axis `0x4ED690`→`0x4E3460`). This is the
first time the per-build maintenance number is measured rather than asserted: ~13 byte-shape
signatures, all unique-hit, resolvable in under a minute.

**F8 — A pass-1 NOT FOUND closed and not noticed.** Pass 1 §13 asks what the second
`s_charProfession`-named array at `0x00A38868` is for. §4.4 measures the character-creation
picker resolving it through accessor `0x005AB840`, and R3 measures that accessor at exactly
one caller. **It is the picker's label list.** The sequel had the answer in two of its own
sections and dropped the open row instead of closing it.

---

## 11. Licence and provenance

Second gate, separate from provenance, and this pass moves it.

| Repo | Licence | Bearing after this pass |
|---|---|---|
| **GWCA** (GregLando113, JaborGW) | MIT | **No `PLAN.md` §6.1 row.** Cited here for hook *mechanism* and *location technique* (AOB scan, assert-string anchor, near-call resolution), all read as source. A row is required before any of it is implemented. Note the currency caveat: `GregLando113/GWCA` has been archived read-only since 2023-11-14 and the GWCA vendored into current GWToolbox++ builds is closed-source |
| **GWToolbox++** (gwdevhub) | MIT | **No row.** Cited for the injection sequence, the render-callback pattern, and the runtime assert-neuter precedent. Nothing taken |
| **MinHook** (vendored in both) | **BSD-2-Clause** — read from `Dependencies/minhook/LICENSE.txt`, not the README badge | **No row.** Only relevant if vendored; this repo's need is a ~10-line splice, not MinHook's generality |
| **Dear ImGui** | MIT | **No row.** Only relevant if a render overlay is ever built, which nothing recommended here requires |
| **`ldufr/Headquarter`** | MIT | Registered. Cited as proof the full write sequence works in pure `ctypes` |
| **`apoguita/Py4GW_Reforged_Native`** | **Apache-2.0** | **Correction to this repo's records.** `CLAUDE.md` and `PLAN.md` §6.1 frame "Py4GW_Reforged" as no-licence; the base repo and `Py4GW` indeed have no LICENSE file, but the **Native** sibling carries Apache-2.0. Worth carrying forward if its MinHook/ImGui plumbing is ever wanted |
| **`gw-preservation/*`** | **No licence — all rights reserved** | Verify-only. Its 113-line XInput proxy is context, not usable prior art; **gMod**, which it references, is not in our mirrors at all — no source, no licence, nothing to verify against |
| **`shiburito/gw_in_browser`** | **GPLv3** | Targets the WASM client, a different build entirely. Cited only to note a separate hooking surface exists there |
| **GWLP-R**, **OpenTyria**, **sgwlpr**, **Tyria-Extractor** | unchanged from `FINDINGS.md` §15 | No new use this pass |

**Which proposals would need a register row, stated plainly:**

- **Option 1 (b), Option 2 (c): none.** Every mechanism is Win32 API, our own disassembly,
  or tooling already in this tree.
- **Option 3 ((c)+, the `ctypes` detour): none, if written from the Win32 contracts.**
  `CreateRemoteThread`/`WriteProcessMemory`/`VirtualProtectEx` are Microsoft's documented
  API, independently reinvented five times in four languages including once in pure
  `ctypes` — not meaningfully any one mirror's expression. **A row becomes required the
  moment a specific byte pattern, patch byte sequence, class design or scanner algorithm is
  lifted rather than re-derived against build 38797.**
- **Option 4 ((a)-lite): a row for MinHook** if its trampoline logic is vendored rather
  than hand-written, and rows for GWCA/GWToolbox++ if their scanner patterns are copied.

**The provenance gate, and why the recommended route stays inside it.** Everything Option 2
commits is an **id** — an attribute id, a name string id, a description string id, a texture
file id — with the string or the texture resolved at run time from the owner's own archive.
Nothing ArenaNet expressed enters the repo. That is the `mapbuild.py` pattern and it is why
(c) is inside the gate while (a), which needs armour composites, sits outside it. **Option
3 does not change this**: a detour that returns *our* id for profession 11 commits a
comparison and an id, not a byte of ArenaNet's art.

This document reports addresses, counts, bounds, offsets, strides, ids and layouts. It
reproduces no assert expression text, no source path paired with a condition, no asset
bytes and no authored strings. §10-D records the one place a survey did and where it was
stripped.

---

## 12. Reproduce

Read-only against the pinned build. `--exe` must be passed explicitly — `asserts.py`'s
default is the owner's install at `C:\gw`.

**Resolve the vault with `vaultpath`, never with a relative `vault/...`.** A worktree has no
vault of its own and the relative form silently resolves to nothing.

```
EXE="$(python -c "import sys; sys.path.insert(0,'toolkit'); import vaultpath; \
      print(vaultpath.vault_path('client','2026-07-29_221c13772c7a','Gw.exe'))")"

# R1: the assert reporter has exactly ONE direct caller. This is the whole route.
python toolkit/clientscan/codescan.py --exe $EXE --xrefs 0x00488210
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x00487bc0 --count 40

# R1, corrected: the deeper terminator layer is SHARED -- 5 callers, 4 non-assert.
python toolkit/clientscan/codescan.py --exe $EXE --xrefs 0x005bc094

# R1, the refutation (S10-A1). TWO stores clear the flag; a THIRD site returns early.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x00487b40 --count 10
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x00489570 --count 12

# R3: caller counts are of the ACCESSOR, not the array. The array itself returns
# 0 direct references and 1 word -- that is the accessor's own embedded immediate.
python toolkit/clientscan/codescan.py --exe $EXE --xrefs 0x005AB7B0   # 31
python toolkit/clientscan/codescan.py --exe $EXE --xrefs 0x005AB7E0   # 4
python toolkit/clientscan/codescan.py --exe $EXE --xrefs 0x005AB810   # 12
python toolkit/clientscan/codescan.py --exe $EXE --xrefs 0x005AB840   # 1

# S4.4: the picker IS loop-driven, over a COMPILE-TIME 11, with no assert on the
# bound. `83 FB 0B` at 0x004D93CD is a one-byte immediate change.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x004D9199 --count 8
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x004D93C6 --count 8

# S4.2: costume hat is a SEARCH LOOP (stride 0x28, <=0x3b iters), not an array.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x008EE2B0 --count 22
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x008EE1D0 --count 20

# S4.3: two MORE profession-keyed tables, uncatalogued by pass 1.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x008EE260 --count 18
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x008EE170 --count 20

# R2: the jump table ends at 0x005A5EE8; 8 bytes of int3 follow, unreferenced.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005A5EE0 --count 8

# W2: RUN. 235 sites, 8 of them profession-bounded arrays. A partial enumerator,
# not a census closer -- it names no costume/composite array and not the jump table.
# PROVENANCE: this output pairs ArenaNet's assert EXPRESSION with Module:line, which
# is the one combination CLAUDE.md still refuses. Carry symbol, VA and bound only --
# never paste a row of it into a tracked file. (FINDINGS.md §3 does this correctly.)
python toolkit/clientscan/asserts.py --exe $EXE --grep arrsize

# W1: RUN, and it REFUTED this document's original headline. The composite gate is
# one accessor over two POINTER tables, not an art gate.
# NOTE 0x00777F10 NEVER RECEIVES PROFESSION -- that was W1's original method and it
# manufactures a false negative. Profession goes to 0x00832080, which calls the accessor.
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x00832080 --count 40
python toolkit/clientscan/codescan.py --exe $EXE --dis 0x005AE200 --count 60

# W1, the fact that decides it: professions 0,1,2,9 already share a byte-identical
# composite row, so a redirect copies 12 dwords per table from the owner's own client.
python - <<'PY'
import pefile
exe = __import__('subprocess').run(
    ['python','-c',"import sys;sys.path.insert(0,'toolkit');import vaultpath;"
     "print(vaultpath.vault_path('client','2026-07-29_221c13772c7a','Gw.exe'))"],
    capture_output=True, text=True).stdout.strip()
pe = pefile.PE(exe, fast_load=True); b = pe.OPTIONAL_HEADER.ImageBase
img = pe.get_memory_mapped_image()
for nm, A in (("A", 0x00BF4018), ("B", 0x00BF4228)):
    v = [int.from_bytes(img[A-b+4*i:A-b+4*i+4], 'little') for i in range(132)]
    rows = {}
    for p in range(11):
        rows.setdefault(tuple(v[12*p:12*p+12]), []).append(p)
    print(nm, len(set(v)), "distinct;", len(rows), "distinct profession rows;",
          "shared:", [g for g in rows.values() if len(g) > 1])
PY
```

`pefile`-driven checks (the read-only-analysis carve-out) for the R2/R5 facts — reloc
coverage over 140,862 `HIGHLOW` entries, `DllCharacteristics == 0x8140`, `LoadConfig`
size 64, the 23,744-byte security directory, 5 sections with 7 free header slots, the
`int3` census (146,527 B / 26,243 runs / largest **78**), and the stale checksum on
`vault/client-patched/Gw.custom.2026-07-29_221c13772c7a.exe` (stored `0x00a02ccd`, computed
`0x00a01ad3`) — were produced by scratch scripts in the session scratchpad. They should be
preserved to `vault/research/profession-workarounds-2026-08-12/` alongside the tracks'
output, per the customarea precedent: **a reproduce section citing a directory that deletes
itself is not a reproduce section.**
