# Full moddability: N professions, N attributes, N skills

Third document in the arc, and the first written against a different question.
[`FINDINGS.md`](FINDINGS.md) asked *can we add an eleventh profession* and answered no.
[`WORKAROUNDS.md`](WORKAROUNDS.md) asked *is there a way around the wall* and answered yes —
ride an existing id. **The owner has since replaced the target: arbitrary N custom
professions, with their own attributes and their own skills. Riding an existing id is now
the FALLBACK, not the design.** Six design tracks, each adversarially verified. This is the
synthesis, plus one census the synthesist ran rather than deferred.

Where this document supersedes its predecessors it says so, in §5, by claim.

No client was launched. Nothing was patched or written. `C:\gw` was never touched. Both
client builds were opened `rb`.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes on this machine, this pass. Names the file, address, count. |
| **OBSERVED** | Watched happening in a running client, by this repo, at a dated pass. |
| **CLIENT-DATA** | Read out of the shipped client by a third party whose code we read. |
| **SOURCE-CODE** | Read in some project's source. Nobody's source is ground truth. |
| **UPSTREAM** | A reimplementation says so. |
| **INFERRED** | Our reasoning on top of the above. Names what it stands on. |
| **CONTESTED** | Sources disagree; this document does not pick a winner. |
| **UNMEASURED** | Nobody has run the check. Distinct from NOT FOUND — we did not look. |
| **NOT FOUND** | We looked and there is no answer in what we hold. A real result. |

Corpus: `vault/client/2026-07-29_221c13772c7a/Gw.exe` (build 38797, 10,483,904 B), the
cross-check build `vault/client/2026-04-30_b174de1f2d8d/Gw.exe`, `vault/dat_study/Gw.dat`,
21 mirrored prior-art repositories.

---

## 1. The ceilings

**This is what the owner is buying.** Every row is a hard number with the bytes that set it,
or the word UNMEASURED. Nothing here is estimated into a number.

### 1.1 Professions

| Configuration | Ceiling | What sets it | Cost to raise |
|---|---|---|---|
| **Today, unpatched** | **11** (ids 0–10) | **34 distinct functions** bound-check profession on build 38797 — MEASURED this pass, §5.1. Every one is a session-ender (the assert reporter is noreturn, pass 1 §12-E1) | R1 — one 5-byte `call` NOPed at VA `0x00487C11`, one site for all 19,758 asserts. Converts every check to a fall-through |
| **R1 + detours, custom id on the byte-wide carriers only** | **256** | GAME_SMSG `0x00A6`/`0x00B7`/`0x0056`/`0x015A` and GAME_CMSG `0x0060` all carry profession as a plain `u8`; the setter `0x007F7330` writes both bytes into the agent struct at `+0x10E`/`+0x10F` with **zero comparison instructions in its whole body** (MEASURED, re-disassembled twice this pass) | Already there. 256 is the field width, not a patch target |
| **If the custom id must also ride the `0x0059` appearance dword** | **16 by width; 11 in practice** | The dword is decoded by one generic table-driven extractor at `0x0091D490` over an 8-record table at `0x00BC8AC8`. Dumped this pass: slot 3 = profession, **shift 20, width 4**. All eight widths sum to **exactly 32 with zero gaps and zero overlap**. And the extracted nibble is bound-checked `< 0xB` at `0x004A8B0A` with an assert at `0x004A8B14` (`UiGame:613`) — MEASURED this pass | **Do not put the custom id there.** Send a legal placeholder (≤10) in slot 3 and carry the real id on the `u8` fields. Cost: whatever UI reads the cached nibble shows the placeholder |
| **If you insist on widening the nibble** | **32** | A **data-only** repartition of the same 8-record table: slot 2 (hairStyle) width 6→5 and shift 24→25, slot 3 width 4→5, shift unchanged. No code touched — **and the repartition moves read and write together**, because the same table drives the packer as well as the extractor (§1.1a) | Beyond 32: **UNMEASURED.** It requires knowing how many faces/skins/hair colours/heights actually ship, so you know which field can afford to shrink. Nobody has counted them |

### 1.1a Two corrections to §1.1, found after synthesis

**The custom range is `id >= 12`, not `id >= 11`.** This document keys its whole design on
`id >= 11` — in §1.1, §2.2 ("for `id >= 11` indexes our own N-row table"), §2.4, and S3's
prediction, and **S6 and S7 both probe with profession byte 11**. But **11 is the client's own
reserved/none sentinel**: all nine reserved attribute rows carry profession `11` at `+0x00`
(MEASURED — orchestrator re-verified: `{26,27,28,45,46,47,48,49,50} → 11`, and the professions
present across all 51 rows are exactly `1..11`). Probing with 11 would test the sentinel, and
any anomaly would be unattributable between "custom id rejected" and "sentinel handled
specially". **Change the custom range to 12 throughout and re-key S6/S7.**

*Symmetrically, and it retires pass 2's Tier-2 fallback:* the skill table uses **profession 0**
as its none-marker — **1,764 of 3,443 rows carry it** (MEASURED). Pass 2 recommended riding id
0; that would take over a value 1,764 shipped skill rows use to mean "no profession".

**The appearance dword has a WRITE path, it was never located, and it fails silently.**
`--xrefs` on the field table returns **two** consumers, not one: the extractor `0x0091D490`
that this document names, and **`0x0091D430`, the packer**, which it does not —
`eax = (value & ((1 << width) - 1)) << shift`. **Neither bound-checks the VALUE**; both assert
only `slot < 8`. So a packed profession id ≥ 16 is masked to `id mod 16` with **no assert, no
crash and no log** — a failure mode absent from this entire document, and the worst kind,
because every other failure here is loud. The packer's thunk at `0x008153B4` has **zero direct
`rel32` callers** (the extractor's thunk has 52), which is evidence the client does not reach
it by direct call — but `codescan --xrefs` is documented blind to indirect calls, so that is a
floor, not a proof. **Consequence: P2's "scales to 255 as a single edit" is unproven in the
direction that fails silently.** If anything builds the `0x0059` dword client-side, the ceiling
for professions created through the picker is **16, not 256**.

> **Owner's constraint, 2026-08-12 — and it makes this question non-blocking.** *"16 is a fine
> upper limit if the work to expand it is overly complex. Let's not skip it without taking a
> look first."*
>
> So the honest headline is a conditional, and **both arms are acceptable**: the ceiling is
> **256** if nothing packs the dword client-side, and **16** if something does. Sixteen means
> ids 0–15 with 0 = None and 1–10 shipped — **five custom professions**, which is a real
> modding surface and is far from the "+1" the owner ruled out as the backup plan.
>
> The look was taken and it was worth taking: the naive reading ("the nibble is decorative")
> is **refuted** — the nibble has real consumers including a hard bound check at 11 — and the
> naive pessimism ("therefore 16") is refuted too, because the nibble and the live profession
> byte are **different storage**. What remains open is one `--xrefs` (§9), and its worst
> outcome is a ceiling the owner has already accepted.

**The headline number is 256, and the sentence that earns it is the third row.** Pass 1
flagged the 4-bit nibble as the possible real ceiling and nobody had traced it. It is traced
now, and the answer is not "the nibble is decorative" (which is what one design track
concluded and its verifier refuted): **the nibble has at least eight consumers, one of them
a hard bound check at 11 in the character-summary UI.** What makes 256 reachable is that the
nibble and the mechanically-live profession byte are *different storage* — the nibble lands
in a ChCliApi per-agent cache record at `+0x18`, the live value in the Agent object at
`+0x10E` — so the wire can carry a legal placeholder in one and the custom id in the other.

### 1.2 Attributes

| Configuration | Ceiling | What sets it | Cost to raise |
|---|---|---|---|
| **Today, zero patch** | **51 rows, of which 9 are free** — ids 26, 27, 28, 45–50 | 51-record × 20-byte table at `0x00A35740`; the nine reserved rows carry real name/description string ids that resolve to **empty** archive records (MEASURED pass 1, re-verified pass 2) | Free. Fill the empty text records. **This is a FALLBACK tier — 9 slots is ~2 professions' worth of attributes and then it is gone** |
| **Past 51** | **UNMEASURED, and it is the one dimension where the detour trick does not dissolve the growth shape** | **19 distinct functions** carry the `0x33` immediate (MEASURED this pass, §5.2). Worse: the per-character rank store is a **51 × 20 array embedded at offset 0** of a `0x43C`-byte record, and `51 × 20 = 0x3FC` with named fields at `+0x400`, `+0x408`, `+0x410`, `+0x418`, `+0x420`, `+0x434` filling `[0x3FC, 0x43C)` exactly. The `0x43C` stride is MEASURED from the binary search at `0x00819340` (`imul edi, [ebx+8], 0x43c`) | 19 detours **plus** either a struct relayout (every one of those six field offsets is baked into code) or an out-of-band store. The out-of-band store is not a stub: the reader at `0x00818C90` performs pool allocation off `[ctx+0x410]`/`[+0x418]`/`[+0x420]` and calls four engine functions; the writer at `0x00819220` walks a **separate 16-byte-stride pending-change array** at `[ctx+0x400]`/`[+0x408]`, calls three more, and cross-references the profession-id and primary-flag accessors. **Whether an out-of-band store can reproduce that is UNMEASURED** |

**The 0x3FC/0x43C arithmetic closing exactly is the strongest structural evidence in this
document**, because it is refutable: it predicts the record size from two independently
measured facts (a 20-byte stride, a bound of 51) and lands on the stride a third,
unrelated instruction carries.

> **Orchestrator's re-verification, and a correction to this document plus one to the
> re-verification itself.** The cited instruction is real but the address is the enclosing
> *function*, not the instruction: `imul edi, [ebx+8], 0x43c` is at **`0x0081934E`**, while
> `0x00819340` is that function's `push ebp`. Confirmed by exact byte match on
> `69 7B 08 3C 04 00 00`, one hit in `.text`.
>
> **Worth recording how nearly this was mis-refuted.** A first check disassembled `.text`
> linearly from the section start and reported **zero** `imul`-by-`0x43C` sites and **zero**
> `cmp ..., 0x33` sites — and was about to be written up as a refutation of the document's
> strongest claim. It was caught only because a `cmp ebx, 0x33` was plainly visible at
> `0x00818CC9` in a targeted disassembly, contradicting the sweep. **A linear sweep from a
> section start desynchronises on data and padding and then silently decodes garbage**; every
> count it produces is worthless without a byte-pattern cross-check. Redone by byte pattern:
> **39 register-form `cmp r32, 0x33` sites**, including the five accessors at
> `0x005A9265`–`0x005A9327` and both `ChCliAttrib` runtime sites `0x00818CC9`/`0x00819244`.
> This is the same class of error as pass 1's `--field`/`--xrefs`/assert-scan under-reporting:
> **a confident zero from a method that cannot see.**

### 1.2a The attribute ceiling is worse than the table above says — the detour reaches none of it

Two findings after synthesis, both MEASURED, and together they make attributes the hardest
dimension in the project rather than the second-hardest.

**1. The `0x43C` record size is compiler-inlined at ~19 sites, and a detour cannot reach an
`imul`.** `0x43C` occurs at **55 sites in `.text`** (orchestrator-confirmed by byte search:
55 raw `3C 04 00 00`), of which **19 are inlined stride multiplies** — 17 `imul r32, r/m32,
0x43C` plus 2 with an `[r/m+d8]` operand — the rest being `lea`/`add`/`sub`/displacements.
**18 of the 19 sit in `[0x818000, 0x81A000)`; one is outside, at `0x00823DB4`.** The
2026-04-30 build reproduces the classification exactly (19/17/2/3/3/4), with its outlier at
`0x0081D9A4`.

This is **§5.3's `0x005A8600` problem in the attribute dimension, and this document does not
notice it.** §2.2's load-bearing claim is *"a detour replaces the function"*. An inlined
`imul reg, reg, 0x43C` **is not a function**. The accessor-detour architecture reaches
**zero** of these 19. So §1.2's "19 detours plus a struct relayout" is not the cost: the 19
there is the *`0x33`-bound function* count, and the relayout is a **separate, additional**
≥19 inlined stride sites plus six baked field offsets — one of which lies outside any
"detour `ChCliAttrib`" scope. **The out-of-band store is therefore the only candidate, not
one of two, and its feasibility remains genuinely UNMEASURED.**

**2. Attribute id 51 is the client's own NONE sentinel, so the growth path starts poisoned.**
Reading all 3,443 skill rows: the attribute byte at `+0x29` takes 43 distinct values — 0–25,
29–44, and **51** — and **1,960 rows (56.9%) carry attribute 51**, while ids 26/27/28 and
45–50 carry **zero** rows (MEASURED, orchestrator-verified). 51 is `CHAR_ATTRIBS_MAX` itself.

- **The first custom attribute cannot be id 51.** Growing the table to 52+ makes 51 a real
  attribute that 1,960 skill rows already claim to own. **Reserve 51 permanently; start
  custom attributes at 52.**
- **§5.2 conflates two semantics under one count.** Its 19 functions "carry the `0x33`
  immediate" — but some are **bound checks** (patch to N) and some are **sentinel
  comparisons** (must *not* move, or must move together with 1,960 data rows). The document
  treats all 19 as detour targets. **That BOUND-vs-SENTINEL split is unmeasured and is
  precisely the number a stub generator needs.** Classify before costing.

### 1.5 Authored text — the ceiling nobody counted, and the first content-side limit

The profession tables hold **string ids, not pointers** (MEASURED: name `{2040–2048, 31548,
31549}`, abbrev `{2049–2057, 31553, 31554}`, second-name `{2058–2066, 31556, 34524}`; chapter
is an ordinal, not a string). So the archive pipeline is on the critical path, and its supply
is finite.

`studies/datwrite/FINDINGS.md`: **678** ids are empty in all eleven languages, every text file
holds exactly 1,024 records, and *"no file has spare capacity — the ceiling is real."*

| Consumer | Cost |
|---|---|
| Per profession | **3** ids (name, abbreviation, second name) |
| Per own attribute | **2** ids (name, description) |
| Per skill | **0** — all 3,443 skill name string ids are **distinct, zero shared**, so each dead row owns its id and its record is overwritable in place |

At five own attributes that is **13 ids per profession → 678 ÷ 13 ≈ 52 professions.**

**52 is comfortably "arbitrary N" for the stated purpose, so this is a row to add rather than
a blocker** — but §1.4 says "N professions: 256" and §2.5 and §8.1 both say "allocate from the
678-empty pool" without ever dividing. **A design that consumes a fixed pool and never sizes
it is exactly the shape this pass was told to hunt for**, and it went three drafts unnoticed.

### 1.3 Skills

| Configuration | Ceiling | What sets it | Cost to raise |
|---|---|---|---|
| **Today, zero patch** | **~1,300 redefinable ids** inside 3,443 | `studies/skills/FINDINGS.md` §5 — free-standing ids nothing ships as a player skill. Redefine name, icon, cost, recharge, owning profession, attribute | Free. `repoint_skill.py` is the proven shape. **Scales to N professions** — this is the only dimension where the fallback tier genuinely serves arbitrary N, as long as you never need more than ~1,300 skills in total |
| **Past 3,443** | **UNMEASURED** | **4 distinct functions** carry the bound (MEASURED this pass, §5.3) — and one of them is why the accessor-detour architecture does not cover skills. `0x005A8600` runs at startup with a **hardcoded `mov esi,0xd73` loop count and the raw base `0x00988ED0` inlined**, materialising two parallel 3,443-entry pointer arrays at `0x00C07E20` and `0x00C0B3EC` (**13,772 bytes apart = 3,443 × 4** ✓). It never calls the row accessor. Plus nine relocated absolute addresses across three base constants (`studies/datwrite/FINDINGS.md`), zero blank rows, and a largest contiguous `.rdata` zero run of 1,055 B — six rows | 4 function patches (not one detour), a new PE section for the grown table, and a decision about the two startup arrays. **Whether they can be grown, or must be replaced wholesale, is UNMEASURED** |

### 1.4 The one-line answer

**N professions: 256, with an architecture that is a bigger build than any prior document
costed. N skills: ~1,300 free today and arbitrary only after unbuilt work. N attributes:
51 today with 9 spare, and arbitrary is the one dimension nobody has measured a route
through.** A profession with no attributes of its own is a costume — so §1.2's UNMEASURED
row is the single most important unknown in this document, and §7 ranks it accordingly.

---

## 2. The architecture

Everything below is a **static, on-disk patch plus one resident DLL**. Nothing is injected
into a running process on the normal path. That choice is load-bearing and §2.3 explains why.

### 2.1 What is patched (build time, in `make_custom_client.py`'s pipeline)

Four edits to the exe, applied to the same mutable bytearray as the existing DH / mutex /
updater / key-tap patches, and verified the same way (write, re-read from disk, re-verify).

| # | Site | Bytes | What it does |
|---|---|---|---|
| **P1** | VA `0x00487C11`, file offset `0x00087011` | `E8 FA 05 00 00` → five `NOP` | Neuters the assert reporter image-wide. **One site for all 19,758 asserts** — the target `0x00488210` has exactly one direct caller in the image, and `ret 4` is correct for all callers uniformly (one stack arg at `[ebp+8]`; the four pushes at `0x00487C04`–`0x00487C10` are balanced by the caller's own `add esp,0x10` at `0x00487C16`, cdecl) |
| **P2** | VA `0x004D93CD` | `83 FB 0B` → `83 FB <N+1>` | The character-creation picker's arity. A bare loop bound with no assert attached — invisible to `asserts.py --grep CHAR_PROFESSIONS`, which is why two passes could not explain why none of the 29 sites is in `CharCreate`. **One-byte immediate, so it scales to 255 as a single edit**; whether the list widget behind it has its own capacity is UNMEASURED |
| **P3** | The PE entrypoint | 5-byte `CALL` at VA `0x005AE591` | Redirects the first instruction the process ever executes into our stub. **MEASURED this pass: entrypoint bytes `e8c7090000 e974feffff` are byte-identical on build 38797 and on the 2026-04-30 cross-check**, 90 days apart — stronger durability evidence than any signature currently shipping in this repo. Anchored on `AddressOfEntryPoint`, a header field, so there is no signature to go stale; the only per-build check is that the bytes there still open with a 5-byte `E8` |
| **P4** | A new PE section, appended | ~100–300 KB | Holds every detour stub and every N-sized replacement table. Needed because the largest contiguous `int3` run in the whole 5.47 MB `.text` is **78 bytes** |

**P4 has three mechanical requirements, all MEASURED:** 5 sections used with **7 free
40-byte header slots on 38797 and 6 on the 2026-04-30 build** (re-measured this pass — the
slack is a per-build fact, not an invariant); `SizeOfHeaders` is `0x400` with zero bytes of
slack after twelve entries; and the `IMAGE_DIRECTORY_ENTRY_SECURITY` entry's
`VirtualAddress` is a **raw file offset, not an RVA**, so appending where the 23,744-byte
Authenticode block currently sits requires patching that directory entry forward or
stripping the block. Nothing validates checksum or signature (no verification API among the
482 imports), so stripping is safe.

### 2.2 What is detoured

**Not 13 functions. At least 34, and the census is still a floor.** §5.1 is the measurement.
Each detour is a 5-byte `E9 <rel32>` spliced over the target's entry, into a per-site stub
in P4's section that (1) replays the stolen instructions, (2) for `id < 11` jumps back into
the original body — so the legacy path is byte-identical by construction, not by care —
and (3) for `id >= 11` indexes our own N-row table.

**One stub per site, not one shared dispatcher.** The sites disagree on argument count
(the composite accessor at `0x005AE200` takes five, and bound-checks four of them), on
stolen-byte length (5–9 bytes, computed per site by disassembly, never hand-picked), and on
what they return. A shared dispatcher would need a selector pushed at every site — more
bytes for less. Sharing happens at the *data* layer: one common region, one helper for the
`id >= 11 → row` arithmetic.

Addressing inside a stub is PIC — `call $+5 / pop eax / lea` with a link-time-constant
displacement, the idiom `keytap_patch.py`'s existing cave already proves — because
`DllCharacteristics` is `0x8140` with `DYNAMIC_BASE` set (MEASURED, both builds) and a
literal absolute operand with no `.reloc` entry resolves wrong at a randomized base. **This
applies to the DLL-path pointer as well as to the IAT read**; one design track wrote the
IAT read correctly and the path push as a bare `push imm32`, which is the same bug the
jump-table gotcha already named once.

**Where the detour trick does NOT apply, stated plainly:**

- **The skill table** (§1.3) — `0x005A8600` inlines the base and its own loop bound. A
  detour on the row accessor is provably insufficient, and this was found by chasing
  `studies/datwrite`'s nine-relocation census back to enclosing functions.
- **Per-character attribute ranks** (§1.2) — the storage is embedded, not indirected, and
  the two functions that touch it are allocators, not getters.
- **Composite table A** (`0x00BF4018`) — 88 of its 132 pointers land in `.data`'s
  uninitialised tail and are populated at runtime. Independently re-measured by a verifier
  this pass. For `id >= 11` the design **aliases** an existing profession's row rather than
  authoring new content, which is the configuration ArenaNet themselves ship
  (professions 0, 1, 2 and 9 share a byte-identical row).
- **The Vendor jump table** — 12 code slots. Beyond 12, extra ids alias slot 0's handler,
  which is what stock's own slot 11 already does.

### 2.3 What is injected — nothing, and that is the point

The task brief asked whether a DLL injected at process start could be too late for a table
read during static init. **The question dissolves rather than needing an answer.** P3 patches
the file on disk; the patched bytes are the first bytes the loader ever maps for that page.
There is no TLS-callback-versus-DllMain race and no "did the hook land before the first
read" question, because our code is not injected — it is already there.

The stub reads `LoadLibraryA` out of the client's **own already-resolved IAT slot** at
`0x00939174` (confirmed by direct import enumeration; the client itself calls through it at
`0x006DDBE1`) and loads our DLL. The DLL's `DllMain` installs the detours as **same-process**
`VirtualProtect` + writes — a materially safer capability class than the cross-process
`WriteProcessMemory` route pass 2 costed, and one `toolkit/` can adopt without the
PID-provenance guard that route needed. Heavy work (reading the config sidecar, populating
tables) defers off `DllMain` per GWToolbox++'s own loader-lock note.

**Two documented alternates, both FALLBACKS:**

- **DLL search-order side-load as `d3d9.dll`** — zero exe bytes touched. MEASURED reachable:
  the client calls `LoadLibraryA("d3d9.dll")` at `0x006DDBE1`, and the 482-entry import table
  carries no `SetDllDirectoryA/W`, `SetSearchPathMode` or `SetDefaultDllDirectories`, and the
  embedded RT_MANIFEST carries no search-order hardening. Runs later than P3 (renderer bring-up
  rather than pre-CRT), and a system-DLL name is a named AV/EDR pattern.
- **`CreateRemoteThread`** — development iteration only, behind an `assert_injectable_pid`
  guard that resolves the PID's image, requires `dhbuild.classify() == OURS` and requires the
  cage to be up, and that accepts a PID **only** from the caller's own process-creation return
  value, never from a scan. The mutex patch enables multiboxing, so "the `Gw.exe` process" is
  not a well-defined singular target.

### 2.4 What is allocated

P4's section holds: the ~34+ stub bodies; N-row replacement tables for every append-shaped,
re-strided, search-loop and unrolled-stack site; the alias tables for composite A and the
jump table; and our own attribute-rank store if §1.2's UNMEASURED row resolves in favour of
an out-of-band design. Budget: roughly 1.4 KB per profession if costume tables are
represented at max capacity, so hundreds of professions is 100–300 KB against a 2.83 MB
`.rdata` — nothing.

### 2.5 What is authored

Two new content kinds in `content/*.toml`, loaded by the **existing** `content.py` with zero
loader changes (`load()`'s `for kind, rows in raw.items()` has no hardcoded kind list —
verified by reading it):

```
[profession.<key>]  id, tier, name, abbreviation, campaign_tag,
                    primary_attribute, attributes, source="invented"
[attribute.<key>]   id, name, description, is_primary, source="invented"
[skill.<key>]       id (redefined from the ~1,300 free pool), owning profession,
                    attribute, cost, recharge, icon id, string ids
```

A build tool `profbuild.py` mirrors `mapbuild.py`'s shape exactly: validate, read any
borrowed ArenaNet constants **at build time from the owner's own install** (raising a
`NoConstants`-shaped refusal if none is supplied, never a silent fallback), allocate string
ids from the 678-empty pool, emit a gitignored `.profpack`, drive `textwrite.py` →
`datwrite.Writer.replace()` against an archive **copy**, drive `dxt1`/`atex` for icons.

### 2.6 Order of operations at client startup

```
build time   patched Gw.exe (P1..P4) + patched archive copy + .profpack, all in vault/
     |
  1  Windows loader maps the image, processes static imports, runs their DllMains,
     releases the loader lock
  2  PE entrypoint 0x005AE591 executes our 5-byte CALL into P4's section
  3  stub: call/pop to recover EIP, read IAT slot 0x00939174, PIC-compute the DLL
     path pointer, call LoadLibraryA
  4  our DllMain: install ~34 same-process detours (VirtualProtect + write);
     read the {va, kind} table and the N-row content from the sidecar named by an
     env var our launcher sets; defer everything heap/file-touching off DllMain
  5  stub calls the ORIGINAL entrypoint target 0x005AEF5D -- the MSVC
     __security_init_cookie shape (sentinel 0xBB40E64E, MEASURED) -- and CRT
     startup, static init and WinMain proceed untouched
  6  0x005A8600 runs and materialises the two 3,443-entry skill pointer arrays.
     ***Our detours are already in place; that ordering is the reason step 3 is
     at the entrypoint and not in a later hook.***
  7  login; character select; the picker loop at 0x004D90F0 iterates to P2's bound
  8  server sends 0x00A6/0x00B7 carrying the custom u8 id, and 0x0059 carrying a
     LEGAL PLACEHOLDER (<=10) in appearance slot 3 -- see SS1.1 row 3
```

Step 6 is the only place in this design where the loader's timing does real work, and it
was found by a verifier chasing a claim, not by the loader track.

---

## 3. B+C: the direct answer

The owner offered B+C as a warm-up and asked whether it is on the critical path. **Answer:
B is free and orthogonal — do it. C is about half on the path, and the half that is on the
path is the half nobody thinks is interesting.**

### 3.1 Artefact by artefact

| B+C artefact | Verdict for arbitrary N |
|---|---|
| **Server-side behaviour** (skills, stats, damage, energy, recharge on an existing id) — this is all of B | **ORTHOGONAL.** Costs nothing, needs nothing from either document, and is neither reused nor wasted — it is a different layer that a native profession also needs. Do it whenever |
| **Archive text fill** — `datwrite.py` / `datplan.py` / `datcheck.py` | **REUSED UNMODIFIED, on the critical path.** Every custom profession, attribute and skill under every tier needs a name resolved at run time from an authored-empty record. Tier-agnostic by construction |
| **DXT1 icon pipeline** — `dxt1.py` / `atex.py` | **REUSED UNMODIFIED, on the critical path.** OBSERVED-closed end to end since 2026-08-06; the only new work is a call site |
| **The content schema + provenance discipline** (`content.py` rows, commit-the-id, borrowed constants read at build time) | **REUSED UNMODIFIED, on the critical path.** This is `mapbuild.py`'s pattern and it is what keeps the whole design inside the gate |
| **String-id allocation from the 678-empty pool** | **REUSED, with one genuinely new capability.** Today's tested path *fills an already-referenced empty id*. For ids ≥51 the pointer lives in our own out-of-band table, so the tool must allocate a **never-referenced** id. Unbuilt |
| **`repoint_skill.py`'s write path** — point an existing row's field at another existing id | **THROWN AWAY.** It is definitionally scoped to reuse an existing compiled slot. Its *method* (find a table by shape, never by address; cross-check against an index-identity invariant) carries forward and must be re-run against 34 more functions; its diff does not |
| **The 9 reserved attribute slots** | **A FALLBACK TIER, not a component.** 9 slots ÷ 4–5 attributes = ~2 professions and then the resource is gone. It teaches you nothing about growing the attribute space |
| **Riding profession id 0** | **THE FALLBACK, labelled as such every time it appears in this document.** It yields exactly one custom profession. Pass 2 recommended it; that recommendation is superseded as the primary goal by the owner's ruling |
| **R1, the assert neuter** | **NOT A B+C ARTEFACT AT ALL.** B+C rides an existing id specifically so it never trips an assert, so doing B+C first produces zero progress toward R1. R1 is an independent prerequisite for every tier above the fallback |

### 3.2 Recommendation

**Do B now (it is free). Do C's content half in parallel with the real work, because that
tooling is genuinely reused. Do not do C's identity-repoint half first, and do not let it
front-run the engineering.**

The reason is §5.1: the detour architecture was costed by three consecutive documents at
~13 functions and the real number is **at least 34**. That is where the estimate is wrong,
that is what a spike would find, and C's repoint half exercises none of it. A staged plan
that spends its first weeks on the comfortable half will discover the 2.6× at the end
instead of the beginning. §6 orders it the other way.

---

## 4. Verifier verdicts — and the pattern in them

**Six tracks. Six verifications. Zero DOES NOT SCALE. Zero YIELDS ONLY +1. All six returned
SCALES WITH CAVEATS.** That is a reassuring headline and it should be read with suspicion,
because **the caveats all landed in the same place**: every single track's census was short.

| Track | Verdict | Where the caveat landed |
|---|---|---|
| D1 ceilings | SCALES WITH CAVEATS | Nibble-consumer census refuted: 1 claimed, ≥8 found |
| D2 tables | SCALES WITH CAVEATS | Accessor census: 13 claimed, ≥16 found by the verifier, **34 by this synthesis** |
| D3 attributes/skills | SCALES WITH CAVEATS | Skill-table consumers: 1 accessor claimed, a second literal-inlining function found |
| D4 loader | SCALES WITH CAVEATS | A concrete, still-unlocated second unrolled table; a non-PIC push in the cave |
| D5 content | SCALES WITH CAVEATS | Native-tier attribute storage treated as covered by machinery that does not cover it |
| D6 staging | SCALES WITH CAVEATS | Skill-table patch surface: 1 mechanism claimed, 2 found |

**The mechanism scales. The census does not, and nobody's census did.** That is this pass's
finding, and it is why §5 exists and why §7 is ordered by discoverability rather than by
severity.

### 4.1 Corrections — refuted

**R1 — "The appearance dword's profession nibble has exactly one consumer and is a
decorative secondary cache."** REFUTED. One of the extractor's four direct references is a
pass-through thunk at `0x008153C0` with **52 further callers**. Reading the two bytes before
each: **41 push a compile-time slot immediate and 11 pass it as a runtime variable**. Slot 3
(profession) is requested at **7** of those sites, plus the `0x0059` handler's own direct
call — eight, not one. Re-run by the synthesist this pass; the distribution is
`{0:4, 1:4, 2:5, 3:7, 4:4, 5:2, 6:11, 7:4, runtime:11}`.

**Corrected claim, in the body at §1.1:** the nibble is durably stored, has at least eight
consumers, and one of them — at `0x004A8B0A`, assert VA `0x004A8B14`, module `UiGame` line
613, in the character-summary path — bound-checks the extracted value `< 0xB`. So a design
that widens only the byte-wide fields while packing the same id into the appearance dword
crashes specific UI flows for any id above 10. **The fix is to keep the custom id off the
appearance dword entirely**, which no track proposed because none had traced the consumer.

**R2 — "There is one other compiler-unrolled 2-D stack lookup and it was NOT FOUND."**
REFUTED. There are two: `0x005AAE20` and `0x005AB9E0`, one caller each, both called from
the same consuming function as the already-known `0x005AB470` (calls at `0x00509019`,
`0x00509024`, `0x0050902E`, within ~20 bytes of one another). Reproduced by the synthesist:
all three appear in §5.1's census.

**R3 — "The skill table sits behind one accessor with 101 callers."** REFUTED as a complete
description. `0x005A8600` bypasses it — §1.3 and §5.3.

### 4.2 Corrections — weakened

**W1 — "The profession ceiling is a clean 256, gated only by the ~13 table accessors."**
The 256 survives (§1.1) but the gating clause does not: the census is 34, and the nibble
has a live bound check. Corrected in §1.1 and §2.2.

**W2 — "13 profession-keyed accessors."** Reproduced exactly, digit for digit
(31/4/12/1/2/4/4/12/14/2/8/3/1), and **is a strict subset of a set 2.6× larger** — §5.1.
This supersedes `WORKAROUNDS.md` §1's *"~13 profession-keyed lookups over ~11 backing
arrays"* and §6's blocker-2 row, both of which read as a bounded surface.

**W3 — "The per-character attribute rank accessors are storage accessors."** They are not.
The reader performs pool allocation and calls four engine functions; the writer walks a
separate pending-change array and calls three more, plus both static accessors. "Redirect to
an externally-owned store" is the right *shape* and a much bigger *lift* than the phrasing
implies. Corrected in §1.2.

**W4 — "A relative-operand patch needs no `.reloc` entry."** True for the splice; **false
for the cave's own DLL-path pointer** if written as a literal `push imm32`. `DYNAMIC_BASE` is
set. Corrected in §2.2.

**W5 — "7 free section-header slots."** True on 38797; **6 on the 2026-04-30 build**
(measured this pass). A per-build fact, not an invariant — exactly as `WORKAROUNDS.md` §3.2
warned in prose and no document then honoured in a number.

**W6 — "The safe N today is 9."** Internally inconsistent in its own source: 9 reserved
attribute slots at 4–5 per profession is ~2 professions' worth of *attribute
differentiation*, and the tier that uses them mints **zero** new profession identities.
Corrected: the honest figure is **0 new professions from that resource alone**.

**W7 — a labelling slip.** Pass 1's reserved-attribute and blank-skill-row results were
labelled UPSTREAM by one track. They are this repo's own prior MEASURED results. Relabelled.

---

## 5. The census this pass ran instead of deferring

Three consecutive documents built the profession-table census the same way: from a
hand-curated list of accessor VAs. **Nobody ever walked ArenaNet's own bound-check sites back
to their enclosing functions.** A verifier noticed this and found three more functions by
hand. Doing it mechanically takes about ten minutes.

Method: for every profession-, attribute- or skill-bounded assert VA the tools name, walk
back with `codescan.Image.func_start()` to the preceding `int3` padding, dedupe by function
start, and count direct `rel32` callers of each. `func_start` is documented best-effort, so
spot-checks were run: four sampled starts all open `push ebp; mov ebp, esp`.

### 5.1 Professions — 34 distinct functions, and it is still a floor

**MEASURED, build 38797:** 39 bound-check sites (29 `CHAR_PROFESSIONS` asserts + 8
`arrsize` asserts + the `UiGame:613` nibble check + the picker's assert-less loop bound)
resolve to **34 distinct functions**, with one site unresolved (`0x00884517`, `UiCtlWebLink`
— no `int3` padding within `0x800` backwards). **173 direct `rel32` callers in total.**

```
0x004a8a20   3   UiGame character summary (the nibble bound check) -- NEW
0x004d90f0   3   the character-creation picker loop
0x00510f10   1   GmSkTome                                          -- NEW
0x0057a040   0   PvpItemList                                       -- NEW
0x0058a790   2   TemplatesHelpers                                  -- NEW
0x005a09e0   2   VnUnlockSkill                                     -- NEW
0x005a8e40   4   hair palette          [in pass 2's list of 13]
0x005a8ee0   4   skin palette          [in pass 2's list of 13]
0x005a9140   6   ConstItem                                         -- NEW
0x005aa230  36   ConstChar -- MORE CALLERS THAN ANY OF THE 13      -- NEW (found by a verifier)
0x005aac00   1   ConstChar                                         -- NEW
0x005aae20   1   ConstChar unrolled-stack #2                       -- NEW (found by a verifier)
0x005aaeb0   2   ConstChar                                         -- NEW
0x005ab170   1   ConstChar                                         -- NEW
0x005ab470   1   unrolled-stack #1     [in pass 2's list of 13]
0x005ab560   2   ConstChar                                         -- NEW
0x005ab7b0  31   profession name       [in pass 2's list of 13]
0x005ab7e0   4   abbreviation          [in pass 2's list of 13]
0x005ab810  12   chapter               [in pass 2's list of 13]
0x005ab840   1   second name / picker label list  [in pass 2's list of 13]
0x005ab870   1   ConstChar                                         -- NEW
0x005ab9e0   1   ConstChar unrolled-stack #3                       -- NEW (found by a verifier)
0x005aba70   2   ConstChar                                         -- NEW
0x005ad6f0   4   ConstSealedDeck                                   -- NEW
0x005ae200   3   armour composite      [in pass 2's list of 13]
0x0082ff60   2   body scale            [in pass 2's list of 13]
0x00831280   0   CpsPlayer                                         -- NEW
0x00832130   2   CpsTex                                            -- NEW
0x00833280   3   CpsData s_type[0].count                           -- NEW
0x008ee150   8   costume 3-axis        [in pass 2's list of 13]
0x008ee1d0  12   costume body          [in pass 2's list of 13]
0x008ee250   2   costume 2-axis        [in pass 2's list of 13]
0x008ee2b0  14   costume hat           [in pass 2's list of 13]
0x0091cd50   2   AcctTemplate                                      -- NEW
+1 unresolved  0x00884517  UiCtlWebLink
```

**Pass 2's thirteen reproduce exactly and are a strict subset. Twenty-one more functions
bound-check profession and none of them appears in any prior document in this arc.**

Two honest qualifications:

1. **Not all 34 need a detour.** Several are *consumers* that bound-check a profession and
   then do something that is not a table read — the PvP item list, the skill tome, the web
   link, the account template. Those degrade to "this one feature shows the host profession"
   rather than needing an N-row table. But every one of them is a site where a custom id
   changes behaviour, and without P1 every one of them ends the session.
2. **34 is still a floor, four ways.** `asserts.py` prints its own shortfall (19,758 read
   against an independent sweep of 20,131 — short by ≥370 image-wide); the picker's bound
   proves that assert-less bounds exist and are invisible to the census; `func_start` is
   best-effort; and `--xrefs` sees no indirect or computed call.

### 5.2 Attributes — 19 distinct functions

**MEASURED:** 21 sites (9 `CHAR_ATTRIBS` asserts + 11 `arrsize(s_attrib)` asserts + the
pointer-array iterator's bound at `0x005A9265`) → **19 distinct functions**. Prior documents
named seven of them (four static accessors, two `ChCliAttrib` runtime sites, one pointer
array). Caller counts: `0x005A92F0` 22, `0x0080D910` 10, `0x005A9320` 6, `0x005A92C0` 5,
`0x005A9210` 4, `0x00819220` 4, the rest 0–2.

### 5.3 Skills — 4 distinct functions, and one of them breaks the architecture

**MEASURED:** the five `0xD73` bound sites resolve to three functions —
`0x005A88B0` (the row accessor, **101 callers**), `0x005A88F0` (5 callers), and
`0x005A8980` (1 caller, 3 bound checks, inlines the base and folds `base+0x10`/`base+0x2A`
into instruction displacements). **Plus a fourth carrying no assert at all**: `0x005A8600`,
one caller, which at startup runs

```
005A861C  mov eax, 0x988ed0          <- the table base, inlined
005A8623  mov esi, 0xd73             <- its own row count, hardcoded, no assert
005A8630  mov [edx + 0xc07e20], eax
005A8639  mov [edx + 0xc0b3ec], eax
005A863F  add eax, 0xa4              <- the row stride
005A8647  jne 0x5a8630
```

building two parallel 3,443-entry pointer arrays. `0xC0B3EC − 0xC07E20 = 13,772 = 3,443 × 4`
✓. **A detour on the row accessor does not touch this.** It is the concrete counter-example
to "every table sits behind one accessor" — and it was found by chasing a relocation census
back to a function, the same method as §5.1.

---

## 6. The staged plan, with gates

Offline before launch. Each rung states its **question**, its **prediction** and **what to
watch** before its method. Do not proceed past step *k* until measurement *m* holds.

Every launch rung inherits the house rules, written into the rung: ours-DH build, verified
cage, loopback only, `cage.assert_launch_safe`, named account, archive writes only ever
against a **copy** — never `vault/dat_study/Gw.dat`, never `C:\gw`.

---

**S0 — Prerequisite, not an experiment. One commit.**
`toolkit/authsrv/agents.py`'s `CHAR_PROFESSIONS_MAX = 6` is an observed-corpus floor
mislabelled as the client's constant, and it refuses every experiment below. Replace the
literal with a check against the loaded `content.World`: accept any id in
`world.rows("profession")` plus the ten shipped ids. Blocks everything; costs nothing.
**Named as a prerequisite by pass 1 and pass 2 and still not done.**

---

**S1 — GATE. Close the census. Offline, hours.**

> **Question.** How many functions bound-check profession, attribute or skill, and which of
> them serve profession-keyed *data* (needing an N-row table) versus merely *consume* a
> profession (degrading to host behaviour)?
>
> **Prediction.** More than 34 for professions. §5.1's number is a floor by four independent
> mechanisms; the picker proves assert-less bounds exist and nobody has swept for the
> `cmp reg, 0x0B` shape image-wide. If the sweep returns ≤34, the census is genuinely closed
> and the build estimate below is trustworthy for the first time in this arc.
>
> **What to watch.** The split between data-serving and consuming. That split, not the raw
> count, is the number the stub generator consumes.
>
> **Method.** §5's walk, extended: sweep `.text` for `83 F8 0B` / `83 FB 0B` / `83 FE 0B`
> and every other `cmp r32, 0x0B` encoding, resolve each to its enclosing function, subtract
> the 34. Then classify each of the resulting set by whether it reaches a table base.

**Do not proceed to S3 until S1 holds.** This gate exists because three documents costed this
architecture on a number that is wrong by 2.6×.

---

**S2 — GATE. Retire the section-append assumption. Offline, hours. Zero ArenaNet bytes.**

> **Question.** Will Windows load and run a PE32 whose section table we grew by hand?
>
> **Prediction.** Yes. A synthetic stub already proved the mechanism (pass-3 track D6:
> baseline and grown build both exit 42, 14 bytes changed, all in the header region).
> Standing on 7 free header slots, `SizeOfHeaders` accommodating 12 entries exactly, and
> nothing validating checksum or signature.
>
> **What to watch.** The `IMAGE_DIRECTORY_ENTRY_SECURITY` `VirtualAddress` — it is a **raw
> file offset**, not an RVA, and is the one edit the synthetic stub did not exercise.
> Also `SizeOfImage` arithmetic and section alignment.
>
> **Method.** Repeat the append arithmetic against a **copy** of the real `Gw.exe` via
> `pefile`, statically, without launching. Only the launch half needs a caged session.

---

**S3 — GATE. One detour, end to end, byte-verified. Offline, days.**

> **Question.** Does a 5-byte splice into an appended section, on the smallest
> profession-keyed accessor (`s_profChapter`, `0x005AB810`, 44-byte table, 12 callers),
> return our value for `id >= 11` and stock's for `id < 11`?
>
> **Prediction.** Yes, and the `id < 11` path is byte-identical by construction because the
> stub jumps back into the original body rather than reproducing it.
>
> **What to watch.** Follow the displacements, the way `keytap_patch.verify()` already does.
> **Verify by reading bytes, never by launching first.** Also: run a per-byte-offset xref
> sweep over the stolen-byte range, to prove nothing external branches mid-splice. That check
> was performed holistically for one site this arc and per-byte for none.

---

**S4 — Re-verify P1 statically. Offline, minutes.** One `--xrefs` on `0x00488210` (expect
exactly one direct caller) and one full read of `0x00487BC0`. Cheap re-confirmation, not
discovery.

---

**S5a — GATE. FIRST LAUNCH: caged loopback, UNPATCHED baseline.**

> **Question.** Does `read_error_dialog.py`'s crash-evidence channel behave as expected on
> this build, this session?
>
> **Prediction.** It does. It is the only machine-readable evidence a client assert leaves.
>
> **What to watch.** That the channel fires at all. **P1, once applied, silences it
> image-wide** — so the unpatched baseline must run and be captured before it is spent, or
> every later anomaly is unattributable. This ordering is not optional.

---

**S5b — Caged loopback, P1 + S3's single detour.** Watch one thing only: does the client
reach character select. Cheap to attribute precisely because it is the only delta from S5a.

---

**S6 — Caged loopback: the out-of-range probe.**

> **Question.** With P1 applied, does an agent whose profession byte is 11 survive the party
> window, the attribute panel and a nameplate render?
>
> **Prediction.** It survives all three and renders wrong, because the append-shaped tables
> are read-only image reads and the jump table's slot 11 is populated. **If it crashes, some
> site uses the index for a write** — a read-vs-write character that this arc has spot-checked
> at exactly one of the 34 sites.
>
> **What to watch.** *Which* action triggers anything. That names the first function to
> detour, and it orders §5.1's list.
>
> **Control.** A quiet window before the first send, to measure what the client says
> unprompted in this session.

---

**S7 — Caged loopback: the nibble probe. NEW this pass, and it is the cheap one.**

> **Question.** Send `0x00A6`/`0x00B7` carrying profession id 11 while `0x0059` carries a
> legal placeholder (say 1) in appearance slot 3. Does the character-summary path at
> `0x004A8A20` behave, and which surfaces show 11 versus which show 1?
>
> **Prediction.** The bound check at `0x004A8B0A` passes (it sees 1), and the surfaces that
> read the Agent object's `+0x10E` show the custom id while the surfaces that read the
> ChCliApi cache at record `+0x18` show the placeholder. **The split is the measurement.**
> If nothing shows the custom id, the byte-wide carriers are not authoritative for display
> and §1.1's 256 is worth less than it looks.
>
> **What to watch.** The split, per surface: character summary, party window, hero panel,
> nameplate, tooltip.
>
> **Control.** A second character on a stock profession, unchanged, in the same session.

---

**S8 — The attribute-storage decision. Offline, an afternoon — and see §7's warning about
that phrase.**

> **Question.** Can attribute ids ≥51 be served from an out-of-band store, or does the
> per-character rank machinery have to be re-implemented?
>
> **Prediction.** Re-implemented, in part. Standing on the measured shape: the reader is a
> pool allocator over `[ctx+0x410]`/`[+0x418]`/`[+0x420]`, the writer merges deltas across a
> separate 16-byte-stride array at `[ctx+0x400]`/`[+0x408]`, and the whole context is a
> `0x43C`-byte record found by binary search over a global sorted array — so there is no
> stable per-character pointer to key an external map on.
>
> **What to watch.** `0x008197C0`, `0x00818730`, `0x00818DF0`, and whatever allocates the
> `0x43C` records. If a single allocation site with a baked `0x43C` exists, growing the
> struct is a candidate and the whole question changes.

**Do not commit to "attributes of their own" as a deliverable until S8 holds.**

---

**S9 — Author one native profession end to end.** Text, icon, one attribute set drawn from
whatever S8 permits, a handful of redefined skills. Not via the FALLBACK id-riding trick —
via the appended-section path, so the milestone measures the thing being built.

**S10 — Template to N.** Software engineering, not research.

---

### Fallback tiers, with drop triggers

Every tier below Tier 0 is labelled a FALLBACK because it is one.

| Tier | What it is | Drop trigger that lands you here |
|---|---|---|
| **Tier 0 — the design** | Arbitrary N via P1–P4 + N detours | — |
| **Tier 1 — a handful (2–5)** | Same architecture, smaller N | Per-profession authoring cost dominates, or S1's census keeps growing |
| **Tier 2 — FALLBACK: exactly one, riding profession id 0** | Pass 2's recommendation. Fully provisioned, owned by no shipped profession, composite row shared with 1/2/9. **Yields exactly +1** | S3 or S5b fails: no client-side PE edit is durable |
| **Tier 3 — FALLBACK: reserved attribute slots only, existing id** | Nine slots, zero new profession identities. Archive write only, no PE edit | Tier 2's repoint is refused for stability |
| **Tier 4 — FALLBACK: pure server-side reskin** | Zero client bytes. Available today | Even the archive-write path is refused |

---

## 7. Risk register — ordered by how cheaply each risk is discoverable

Not by severity. **The whole lesson of this arc is that the cheap decisive measurement gets
deferred**: pass 1's top-ranked risk was five minutes of work six agents each filed as
somebody else's scope; pass 2 quoted that lesson, told its reader to be suspicious of
anything everyone defers, and then deferred its own #1 and #2. Both inverted a headline.

| # | Risk | Cost to discover | Status |
|---|---|---|---|
| **1** | **The census is short.** Costed at 13; the real count is ≥34, and that is a floor | **~10 minutes** | **RUN THIS PASS. §5.** Was deferred by three documents. The method — walk asserts back to enclosing functions — was sitting in the tools the whole time |
| **2** | **The nibble has live consumers with a bound check at 11** | ~15 minutes (one extra `--xrefs` hop on a thunk) | **RUN.** By a verifier, after the design that owned it named the exact command and did not run it. §4.1-R1 |
| **3** | **The skill table has a consumer that bypasses the accessor** | ~10 minutes (one disassembly from a relocation census) | **RUN.** By two verifiers independently. §5.3 |
| **4** | **11 of the appearance thunk's 52 callers pass the slot as a runtime variable**, so the consumer census cannot be closed by static immediate-scanning at all | **UNKNOWN — needs a different method.** A caged run with a logging detour on the extractor would enumerate them in one session | **NOT RUN.** Named here rather than left implicit |
| **5** | **Attribute storage past 51 may be a re-implementation, not a redirect** | An afternoon of disassembly (S8) | **NOT RUN — and this is the one this pass most likely deferred.** See below |
| **6** | Whether the two 3,443-entry skill pointer arrays can be grown or must be replaced wholesale | An afternoon (disassemble `0x005A8600`'s consumers) | **NOT RUN** |
| **7** | Whether a hand-grown section loads on the *real* exe (S2) | Offline arithmetic is hours; the load test needs one caged launch | **PARTIALLY RUN.** Synthetic stub: yes. Real exe: static facts re-measured this pass, load untested |
| **8** | Per-byte stolen-byte isolation at each splice site (does anything branch mid-splice?) | Minutes per site, ~34 sites | **NOT RUN** at any site per-byte |
| **9** | **Zero precedent anywhere** for writing new content into a compiled client data table — 21 mirrors, five reimplementations, four languages | Cannot be discovered cheaply. The earliest real signal is S5b/S6 | Structural. Why S6 is sequenced before any authoring |
| **10** | Per-build maintenance now scales with the census: ~34 profession + 19 attribute + 4 skill byte-shape signatures per client update, on top of the DH rotation the runbook already requires | Measured per signature (under a minute each); the aggregate is untested at this count | Real, and it grew 2.6× this pass |
| **11** | P1 silences `read_error_dialog.py` image-wide, at exactly the point in the ladder where crash attribution matters most | Known | Mitigated by S5a's ordering and by the resident DLL's own log + VEH (§2.3 note) |
| **12** | AV/EDR flags the patched exe or a side-loaded `d3d9.dll` | One caged session | Extension of a risk class this project already accepts for four existing patches |

### The one this pass most likely deferred: risk 5

**Every track that touched attributes handed the storage question to a track that did not
exist.** D3 measured the two functions and correctly reported that they are allocators
rather than accessors. D5 asserted that attribute ids outside 0–50 would be "served by
D2–D4's arbitrary-N machinery" — and D5's verifier called that out as an unflagged
assumption, correctly, because D2's machinery is about *tables behind accessors* and this is
*storage embedded in a struct*. D1 measured the 51 bound at nine sites and stopped there.
D6 costed attributes at 9 free slots and left the rest.

So the shape is exactly pass 1's: six readers, one question, nobody's scope. It is offline,
it is a handful of `--dis` calls, and the answer decides whether "attributes of their own"
is a feature or a costume. **Run S8 before writing the confident sentence.** The `0x43C`
arithmetic in §1.2 is the first half of it and took two commands.

---

## 8. Provenance and licence

### 8.1 How the content pipeline stays inside the gate

The gate's boundary is MEASUREMENT vs EXPRESSION (`CLAUDE.md`, owner's ruling 2026-08-11).
This design is inside it by construction, for the same reason `mapbuild.py` is:

- **Committed to git:** ids, invented strings, counts, offsets, strides, bounds, addresses,
  layouts. A profession row is `id = 11, name = "…", primary_attribute = …,
  source = "invented"`. An attribute row is three ids and a boolean. A skill row is a
  redefined id plus numbers.
- **Resolved at run time from the owner's own archive:** every authored string, every icon.
  Commit `name_string_id = 100257`; the client resolves it.
- **Read at build time from the owner's own install, never committed:** any ArenaNet
  constant a profession borrows — the composite row for an aliased profession (24 dwords),
  the palette row, the five mandatory chunk payloads if map work is ever involved.
  `profbuild.py` raises a `NoConstants`-shaped refusal if no install is supplied. **A silent
  fallback here is the bug that `mapbuild.py` already shipped once** (FINDINGS 14's "five
  constants" turned out to be four; the fifth takes two values), so the builder must
  **verify each borrowed constant against the thing it is rebuilding and name any
  substitution**.
- **Enforced, not trusted:** `test_profession.py` should carry (a) a syntax-tree scan of
  `profbuild.py` and `textwrite.py` requiring no `bytes` literal over two bytes — the check
  `test_mapbuild.py` §2 already proves necessary; (b) a *prose* scan of the same files for
  the borrowed constants in raw, hex, spaced-hex and `\x` forms, because a docstring quoting
  bytes is invisible to a syntax-tree scan and that is exactly how one was caught; (c) a
  mutation control — change one TOML field, require only its byte range in the `.profpack`
  to move, which is the only check a memcpy-shaped builder fails; (d) the two-sided
  `C:\gw` / `vault/dat_study` write guard **with a positive control**, per
  `test_rebloat.py`. Floor set from a real green run, never guessed.

This document reports addresses, counts, bounds, offsets, strides, ids and layouts. It
reproduces no assert expression text paired with a source path and line, no decompiled
bodies, no asset bytes, no authored strings. Assert sites are cited as VA + module:line
only, following `FINDINGS.md` §3's convention.

### 8.2 The `PLAN.md` §6.1 rows this design needs

| Upstream | Licence | Needed by this design? |
|---|---|---|
| **MinHook** | BSD-2-Clause (read from `LICENSE.txt`) | **Row required if vendored.** Recommended: vendor it rather than hand-roll, because a general accessor trampoline needs a variable-length instruction relocator — MinHook vendors the Hacker Disassembler Engine precisely because writing one correctly is hard, and hand-templating 34+ call-site shapes in Python byte literals does not scale. **No row today** |
| **GWCA** (GregLando113, JaborGW) | MIT | **Row required if its scanner patterns or `GameEntities` structs are lifted.** This design deliberately keeps location offline in Python (`asserts.py`/`codescan.py`) rather than copying GWCA's live in-process AOB scan, so a row is needed only if that changes. **No row today** |
| **GWToolbox++** | MIT | **Row required if its injection sequence or `DllMain` deferral pattern is copied rather than re-derived.** Cited here for mechanism only. **No row today** |
| **Dear ImGui** | MIT | **Not needed.** Nothing recommended here draws an overlay |
| **`ldufr/Headquarter`** | MIT | Registered. Cited as proof the write sequence works in pure `ctypes` |
| **`gw-preservation/*`**, **`Py4GW_Reforged`** | No licence — all rights reserved | **Verify-only.** The `d3d9` side-load fallback is corroborated by their technique existing; no code taken, none usable |
| **sgwlpr** | AGPLv3 | Nothing taken |
| **GWLP-R** | BSD-style | Verify-only, per pass 1 |

**None of the first three has a row today**, and the house rule requires the row *before* a
line of derived code is written. Whichever of P1–P4 or the DLL lands first, the row lands
before it.

---

## 8a. Found after synthesis — including a component nobody designed

**Secondary professions are absent from this entire document, and they are the one thing in
Guild Wars that serialises a profession id to disk and to another player.**
`0x0058A790` (`TemplatesHelpers`, which §5.1's census lists with "2 callers") bound-checks
**two** profession arguments — `[ebp+0x10]` and `[ebp+0x14]`, both `< 0xB`, two separate
asserts — and then calls the profession-name accessor. That is the primary/secondary pair, in
the function that formats **skill templates**.

Two consequences:

- **The census counts functions, not profession arguments.** §2.2 sizes stubs by argument
  count, but §5.1 counted functions — 39 bound-check sites collapsing to 34 functions already
  implies multi-bound functions the census flattened. **A stub generator driven by that census
  under-generates at every paired site.** Re-run the walk-back counting sites per function.
- **The template codec is a second serialisation ceiling and nobody has measured it.** A skill
  template encodes primary and secondary profession into a string players paste to each other
  and the client writes to disk. If its profession field is narrower than a byte, that caps
  custom professions independently of everything in §1 — and unlike the appearance nibble,
  this one leaves the machine. **Added to §9.**

**The plan does not find the fatal problem first.** The cheapest disproof of the headline
deliverable — "attributes of their own" — was sequenced as **S8 of 10** and took one command
(§1.2a). Two more items this document costs at "hours" or "an afternoon" are also single
scans: risk 6's `0x005A8600` arrays, and the BOUND-vs-SENTINEL split. Meanwhile **S1**, the
gate the plan actually turns on, is a `cmp r32, 0x0B` sweep that only refines a count already
known to be a floor. **Recommended reorder: §1.2a's stride scan → the `0x33` BOUND/SENTINEL
split → S1 → S2 → S3.** Everything above that line is offline and under an hour combined;
three of the four were sequenced *after* a caged launch.

**And a question three passes carried as open is now closed.** §9's *"do the reserved
attribute ids and the primary flag hold on the 2026-04-30 build?"* — **yes, identically,
across a 90-day build gap.** The 51×20 table was located *structurally* in both images (unique
candidate in each: file offset `0x634740` on 38797, `0x6289D8` on 2026-04-30) by requiring
`rec[+0x04] == index` for all 51 rows and `profession <= 11`. Same profession blocks, same ten
primary flags `{(0,5),(6,4),(12,6),(16,3),(17,1),(23,2),(35,7),(36,8),(40,9),(44,10)}`, same
nine reserved name string ids, `desc == name+1` in 50 of 51 on both. **Tier 3 is not per-build.**

---

## 9. Open items and NOT FOUND

These are results.

| Question | Status | What would answer it |
|---|---|---|
| **Does the skill-template codec's profession field have its own width?** | **NOT FOUND — never asked, and it is a serialisation ceiling that leaves the machine** | Read the template encoder reached from `0x0058A790`. Offline. This caps custom professions independently of §1 |
| **Can a custom profession be taken as a SECONDARY?** | **NOT FOUND — secondary professions are undesigned (§8a)** | Re-run §5.1's walk-back counting bound-check sites per function, not functions |
| **Does anything build the `0x0059` dword client-side?** | **UNMEASURED — and it decides whether the picker ceiling is 16 or 256** | `--xrefs` on the packer `0x0091D430` and its thunk `0x008153B4`. If nothing reaches it, say so as a MEASURED result; if something does, professions created through the picker cap at 16 |
| **Which of the 19 `0x33` sites are BOUND checks and which are SENTINEL comparisons?** | **UNMEASURED — and it is the number a stub generator needs** | Classify each; offline, minutes |
| ~~Do the reserved attribute ids and the primary flag hold on the 2026-04-30 build?~~ | ✅ **CLOSED — yes, identically. Carried open through passes 1, 2 and 3** | §8a |
| **Can attribute ids ≥51 be served out-of-band, or must the pool allocator and pending-change merge be re-implemented?** | **UNMEASURED — the deferred one, §7 risk 5** | **S8.** Offline, a handful of `--dis` calls |
| Can the two 3,443-entry skill pointer arrays at `0x00C07E20`/`0x00C0B3EC` be grown, or must `0x005A8600` be replaced wholesale? | **UNMEASURED** | Disassemble its consumers; offline |
| The 11 appearance-thunk callers that pass the slot as a runtime variable | **NOT FOUND by static means** | A logging detour on `0x0091D490` in one caged session |
| Which surfaces read the Agent object's `+0x10E` profession versus the ChCliApi cache's `+0x18` nibble | **UNMEASURED** | **S7.** One caged session, zero authoring — the cheapest launch rung in this document |
| Is the census closed at 34? | **Floor, not census.** Four independent mechanisms make it short | **S1.** Sweep for `cmp r32, 0x0B` image-wide |
| The enclosing function of `0x00884517` (`UiCtlWebLink`) | **NOT FOUND** — no `int3` padding within `0x800` backwards | A wider walk-back, or `--in UiCtlWebLink` bounds |
| Does the character-creation picker's list widget have its own capacity bound beyond `cmp ebx,0xb`? | **UNMEASURED** | Trace the UI-set call at `0x00633C10` |
| How wide can appearance slot 3 grow past 5 bits? | **UNMEASURED** | Count the shipped faces / skins / hair colours / heights, then decide which field can shrink |
| Does a hand-appended section load on the real `Gw.exe`? | **UNMEASURED** (static facts re-measured; load untested) | **S2**, then one caged launch |
| Per-byte external-branch isolation over each stolen-byte range | **UNMEASURED** at every site | Per-site `--xrefs` sweep; minutes each |
| Which widget resolves the profession glyph? | **NOT FOUND** — three independent bounded attempts across two passes | **S7**'s split answers it as a side effect. Format half stays closed (`studies/texture/FINDINGS.md`, OBSERVED) |
| Which profession-adjacent on-screen surfaces are **server** strings rather than client-table lookups? | **NOT FOUND, and still nobody has asked** — carried unchanged from pass 2 §9 | The cheapest identity in the ledger: zero client patching, zero archive writes, zero per-build maintenance. This repo already proves `string16` puts arbitrary UTF-16 on the wire (22,524/22,524) |
| GAME_SMSG `0x003A`'s per-dword encoding — packed `(id, rank)` or positional? | **NOT FOUND.** Shape is MEASURED: `[agent_id, array32[48]]`, wire 8–200 B, which retires the "42 fixed slots" uncertainty in `authsrv.py`'s own comment | A caged loopback probe |
| Is client skill-effect logic parameterised enough for a redefined id to be more than a reparameterised existing effect? | **NOT FOUND** | Belongs to the skills arc. Bears directly on "skills of their own" |
| Does the archive-write path stay durable under sustained real play? | **Open**, carried from `studies/datwrite/FINDINGS.md` | N exposes hundreds of records where the fallback tier exposes ~10 |
| Do the reserved attribute ids and the primary flag hold on the 2026-04-30 build? | **Open**, carried unchanged from pass 1 and pass 2 | One re-run |

---

## 10. Reproduce

Read-only against the pinned build. `--exe` must be passed explicitly — `asserts.py`'s
default is the owner's install at `C:\gw`.

**Resolve the vault with `vaultpath`, never with a relative `vault/...`.** A worktree has no
vault of its own and the relative form silently resolves to nothing.

```bash
EXE="$(python -c "import sys; sys.path.insert(0,'toolkit'); import vaultpath; \
      print(vaultpath.vault_path('client','2026-07-29_221c13772c7a','Gw.exe'))")"

# ---- SS1.1: the appearance dword. One generic extractor, one 8-record table.
# slot 3 = profession, shift 20, width 4. All eight widths sum to exactly 32.
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x0091D490 --count 26

# The consumer census that refutes "the nibble has one reader": four direct
# references, one of which is a THUNK whose own 52 callers are the real fan-out.
python toolkit/clientscan/codescan.py --exe "$EXE" --xrefs 0x0091D490
python toolkit/clientscan/codescan.py --exe "$EXE" --dis  0x008153C0 --count 6
python toolkit/clientscan/codescan.py --exe "$EXE" --xrefs 0x008153C0   # 52

# The bound check on the extracted nibble -- push 3; call thunk; cmp eax,0xb.
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x004A8AE0 --count 24
python toolkit/clientscan/asserts.py  --exe "$EXE" --at  0x004a8b1e

# ---- SS1.2: the per-character attribute context stride is 0x43C, and
# 51*20 = 0x3FC with named fields filling [0x3FC, 0x43C). Closes exactly.
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x00819340 --count 34

# ---- SS1.3 / SS5.3: the skill-table consumer that bypasses the row accessor.
# mov eax,0x988ed0 / mov esi,0xd73 / two arrays 13,772 B apart = 3,443 * 4.
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x005A8600 --count 30
python toolkit/clientscan/codescan.py --exe "$EXE" --xrefs 0x005A88B0   # 101

# ---- SS5: the bound-check site lists the census is built from.
# PROVENANCE: this output pairs ArenaNet's assert EXPRESSION with Module:line,
# which is the one combination CLAUDE.md refuses. Carry VA, module and bound
# only -- never paste a row of it into a tracked file.
python toolkit/clientscan/asserts.py --exe "$EXE" --grep CHAR_PROFESSIONS   # 29
python toolkit/clientscan/asserts.py --exe "$EXE" --grep CHAR_ATTRIBS       # 9
python toolkit/clientscan/asserts.py --exe "$EXE" --grep arrsize            # 235

# ---- SS2.1: entrypoint bytes, byte-identical across a 90-day build gap,
# and the per-build header slack (7 slots on 38797, 6 on 2026-04-30).
python - <<'PY'
import sys, os; sys.path.insert(0, os.path.join(os.getcwd(), "toolkit"))
import vaultpath, pefile
for tag in ("2026-07-29_221c13772c7a", "2026-04-30_b174de1f2d8d"):
    p  = str(vaultpath.vault_path("client", tag, "Gw.exe"))
    pe = pefile.PE(p, fast_load=True)
    b, ep = pe.OPTIONAL_HEADER.ImageBase, pe.OPTIONAL_HEADER.AddressOfEntryPoint
    img = pe.get_memory_mapped_image()
    free = (pe.OPTIONAL_HEADER.SizeOfHeaders
            - (pe.DOS_HEADER.e_lfanew + 24 + pe.FILE_HEADER.SizeOfOptionalHeader
               + 40 * pe.FILE_HEADER.NumberOfSections)) // 40
    print(tag, "EP=0x%08X" % (b + ep), img[ep:ep+10].hex(),
          "dllchar=0x%04X" % pe.OPTIONAL_HEADER.DllCharacteristics,
          "sections=%d free_hdr_slots=%d" % (pe.FILE_HEADER.NumberOfSections, free))
PY
```

**The census itself** (§5) is three scratch scripts in the session scratchpad:
`census2.py` (the 29 `CHAR_PROFESSIONS` sites → 25 enclosing functions, with caller counts
and a diff against pass 2's list of 13), `census3.py` (the union of 39 sites → **34**
functions, 173 callers), `census4.py` (attributes → 19, skills → 4). Each walks
`codescan.Image.func_start()` back from a bound-check VA and dedupes. They should be
preserved to `vault/research/profession-moddable-2026-08-12/` alongside the tracks' output,
per the customarea precedent: **a reproduce section citing a directory that deletes itself
is not a reproduce section.**
