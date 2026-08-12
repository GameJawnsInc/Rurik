# Attributes: how many can exist, and what raising the ceiling costs

Fourth document in the profession arc, and the first about one dimension only.
[`MODDABLE.md`](MODDABLE.md) §1.4 called attributes *"the one dimension nobody has
measured a route through"* and §7 ranked its own deferral of that measurement as risk 5.
This pass ran it. Four tracks, each adversarially verified, plus a synthesis census that
re-derived every headline from raw bytes rather than trusting the tracks.

Where this document supersedes `MODDABLE.md` it says so, by claim, in §4.

No client was launched. Nothing was patched. Nothing was written to the repo or the vault.
`C:\gw` was never touched. Both client builds were opened `rb`.

## Labels

Same vocabulary as [`studies/character/FINDINGS.md`](../character/FINDINGS.md) and
`MODDABLE.md` §Labels: **MEASURED / OBSERVED / CLIENT-DATA / SOURCE-CODE / UPSTREAM /
INFERRED / CONTESTED / UNMEASURED / NOT FOUND**.

Corpus: `vault/client/2026-07-29_221c13772c7a/Gw.exe` (build 38797), the cross-check build
`vault/client/2026-04-30_b174de1f2d8d/Gw.exe`, `vault/dat_study/Gw.dat`.

---

## 1. The number, and its cost

> **204 custom attributes — ids 52 through 255.** The ceiling is set by the skill table's
> **one-byte** attribute field at row `+0x29`, and by nothing softer. Everything between 51
> and 255 is a patch, not a wall.
>
> **Cost: 64 same-length literal edits, 127 tail-reference edits, and two data relocations** —
> the 51×20 definition table (which has **zero** bytes of in-place slack) and the 51-entry
> pointer array (which has **at most 7 slots**). **191 edits, every one same-length.**
>
> **Or ~11 function detours instead**, which trades 191 edits for a resident DLL. §2.4.
>
> *The tail figure shipped as "≥ 116, census NOT closed" — the one estimate in this document.
> Closing it took two attempts. The first produced **97** and declared the census closed; that
> was **wrong**, and the document's own floor was the better number. The tail is reached
> through **two** encodings, and 97 counts only one of them. The count across both is
> **127**, and §14 says plainly which encodings are enumerated and which are not.*

**MEASURED, this pass.** The ceiling is a field width. The skill row's attribute id is read
as a byte — `cmp byte ptr [eax + 0x29], 0x33` at `0x008CAB27`, with the register-widened
form of the same field at `0x008CAB68`. A row stride of `0xA4` puts a different field at
`+0x28` and another at `+0x2A`, so `+0x29` is one byte wide and an attribute id a skill can
name must fit in it. Ids `0`–`50` ship, **51 is the client's own NONE sentinel and is
permanently reserved** (§3), so `52`–`255` is what remains: **204**.

That is a real modding surface. It is 40 professions at five own attributes each, against
`MODDABLE.md` §1.2's "9 free slots is ~2 professions and then it is gone."

### 1.1 What it costs, by class

Every row is a byte pattern I counted this pass on build 38797, never a linear sweep.
`delta = 20 × (N − 51)` is the number of bytes the record grows; for a full `N = 256`
table, `delta = 4100` and the per-character record goes from `0x43C` (1,084 B) to
`0x1440` (5,184 B).

| # | Class | Sites | Edit | Same length? |
|---|---|---|---|---|
| **A** | The row count / bound literal `0x33` | **21** | → `N` | **Yes** — all `imm8`/`imm32` in place |
| **B** | The array's byte size (`0x3FC`) and dword count (`0xFF`) | **5** | → `20N`, `5N−1` | **Yes** |
| **C** | The record stride `0x43C` | **26** | → `0x43C + delta` | **Yes** — 19 are `imul r32, r/m32, imm32` |
| **D** | Tail-field references, **two encodings** | **127** = 97 direct + 25 biased + 5 bias immediates | `± delta` | **Yes at every site. §14 — two encodings closed, others not enumerated** |
| **E** | The 51-entry pointer array `0x00C0EEC0`–`0x00C0EF8C` | **7** | bounds + base | Yes, but **≤ 7 spare slots** in place |
| **F** | The 51×20 definition table at `0x00A35740` | **5** displacements | repoint | **Table must MOVE — 0 bytes of slack** |

**A — the bound, 21 sites.** 18 are `cmp`-vs-51 sites classified BOUND in §3. The other
three are the ones no prior pass in this arc saw, because they are `mov`, not `cmp`:

- `0x00457B8D` `mov edx, 0x33` — the **pointer-array builder's loop count**. NEW, §4.1.
- `0x0081849D` and `0x00818870` `mov ecx, 0x33` — array-length loop counters in the record
  copy/assign function and the in-place element shifter.

**B — the array size, 5 sites.** Four `mov edx, 0x3FC` at `0x008199AB`, `0x00819C71`,
`0x00823C09`, `0x00824AEC`, each feeding a generic size-parameterised helper; one
`mov ecx, 0xFF` at `0x00818FD8` driving a `rep movsd` of 255 dwords (`= 0x3FC`).

**C — the stride, 26 sites and not 55.** `MODDABLE.md` §1.2a reports *"`0x43C` occurs at 55
sites in `.text`"* and treats the population as the attribute record's. **It is not.** Of the
53 that anchor-decode, **25 lie in the `ChCliAttrib` cluster `[0x818000, 0x81A000)`**
(18 `imul`, 3 `add`, 2 `lea`, 1 `sub`, 1 `push`) and **exactly one more is attribute-related
outside it** — the reverse-walk destructor's `imul esi, edi, 0x43c` at `0x00823DB2`. The
**other 27 belong to unrelated structures** that merely happen to be `0x43C` bytes long or
carry a field at `+0x43C`; nineteen of them cluster in `[0x0043B000, 0x0043D000)` alone.
A patcher driven by "every `0x43C` in `.text`" corrupts 27 innocent sites. §4.3.

**D — the tail, reached through TWO encodings and counted at 127.** This shipped as the one
floor in the table (`≥ 116`). A first attempt counted **97** direct `disp32` references — 93
in-cluster over 18 functions plus 4 in `0x0081A410`, which receives the record as an argument
and so carries no marker at all — and **wrongly declared the census closed**. It counts one
encoding. The other biases a pointer into the tail (`add reg, 0x428`) and then accesses at
*negative* displacements, which no `[0x400, 0x43C)` scan can see: **5 bias immediates + 25
biased accesses**. `+0x41C` and `+0x430` are written by the zero-initialiser and appear in
neither the 97 nor any direct form — which is how the second encoding was found rather than
assumed. **The document's own floor was the better number.** Method, the closure check, and
the remaining blind spots in **§14**; §2.3 is the layout.

**E — the pointer array is nearly full.** The iterator at `0x005A9210` encodes the array's
capacity as **two absolute addresses**, `mov edx, 0xc0eec0` at `0x005A9222` and
`mov esi, 0xc0ef8c` at `0x005A9227`; `(0xC0EF8C − 0xC0EEC0) / 4 = 51`. Two more references
sit in the iterator body (`sub esi, 0xc0eec0` at `0x005A925A`, `mov eax, [esi*4 + 0xc0eec0]`
at `0x005A926A`) and three in the builder (`0x00457B83`, `0x00457BA8`, `0x00457BAD`). The
array lives in `.data`'s uninitialised tail. **The nearest address above its end that `.text`
references at all is `0x00C0EFA8` — 28 bytes, seven pointer slots.** So the array grows in
place only to **58** and must be relocated for anything beyond that.

**F — the definition table cannot grow in place at all.** 51 × 20 B at `0x00A35740` ends at
`0x00A35B3C`, and **`0x00A35B3C` is itself referenced by `.text`** — another object starts
exactly there. Slack: **zero bytes, zero rows.** Growing the table means relocating it and
repointing five displacements. Those five also give the accessor-to-field map, which no prior
document in this arc records:

| Accessor | Bound check | Load | Field |
|---|---|---|---|
| `0x005A9290` | `0x005A9297` | `0x005A92B3` | `base + 0x0C` — description string id |
| `0x005A92C0` | `0x005A92C7` | `0x005A92E3` | `base + 0x10` — primary-attribute flag |
| `0x005A92F0` | `0x005A92F7` | `0x005A9313` | `base + 0x08` — name string id |
| `0x005A9320` | `0x005A9327` | `0x005A9343` | `base + 0x00` — owning profession |

### 1.2 Ceilings that are NOT below this one, and why the checks were worth running

Three candidates were measured this pass and none of them caps `N`.

| Candidate | Real value | Does it cap N? |
|---|---|---|
| **Skill-template / build-code struct** | **12 attribute entries per saved build** — compiled `cmp …, 0xc` at `0x0091CE0E`, `0x00585B8E`, `0x0058AFB7`, three modules, reproduced on both builds | **No.** It caps how many distinct attributes **one saved or pasted build** may reference, not how many exist. Vanilla's primary+secondary pair needs ~10 |
| **GAME_SMSG `0x003A` attribute sync** | wire `[agent_id, array32[48]]`; the handler divides the count by 3 → **16 entries per packet** | **No.** The writer stores by id-indexed offset, so disjoint packets compose additively. Send `ceil(N/16)` messages, each with a count that is an exact multiple of 3 |
| **Template codec's id field width** | variable, up to **19 bits** | **No.** Comfortably past 255 |

**The `0x003A` result is the most valuable thing this pass produced that is not about
attributes at all.** `studies/character/FINDINGS.md` §c carries the three-parallel-arrays
reading of `0x003A` as *UNVERIFIED, single-lineage — do not build on this*, sourced only to a
third-party reimplementation. It is now **MEASURED from our own pinned client**: the receive
handler at `0x0091D8C0` computes `n = count / 3` by the canonical `mov eax, 0xAAAAAAAB; mul;
shr edx, 1` idiom, forwards `base+0`, `base+n*4`, `base+n*8` through `0x0080EB40` into
`0x00819BB0`, whose `n`-gated loop calls the already-known attribute writer `0x00819220` once
per index with one value from each sub-array. **UPSTREAM → MEASURED. That question is closed.**

Consequence for our own server, and it is live: `toolkit/authsrv/authsrv.py` sends `0x003A`
with `[0] * 42`. That is wire-legal (42 is a multiple of 3, under 48) but it is **fourteen
repeated `(0, 0, 0)` triples**, not 42 independent slots. Harmless only because every value is
zero, and wrong the moment a non-default rank must be conveyed. (The file's own comment
already retracts the "42 slots" reading — the retraction is correct and the payload was never
updated to match.)

### 1.3 Authored text is not binding

204 custom attributes × 2 string ids = **408** of the **678** ids empty in all eleven
languages (`studies/datwrite/FINDINGS.md`). That leaves 270, or 90 professions at 3 ids each.
The pool is shared with professions and is worth sizing in any final plan, but at these
numbers it does not bind. This corrects the omission `MODDABLE.md` §1.5 flagged in the
profession dimension — here the division was done.

---

## 2. Append or relayout — settled

`MODDABLE.md` §1.2a concluded that because the `0x43C` stride is compiler-inlined and *"a
detour replaces a function; an inlined `imul` is not a function"*, **an out-of-band store is
the only candidate**. The premise is right. The conclusion is wrong, twice over — once in the
direction of pessimism and once in the direction of optimism.

### 2.1 The optimistic reading fails: appending does not work

The proposal was to leave offsets `0x000`–`0x43B` byte-identical and let ranks 51..N live in
an appended tail, so that no field displacement moves and the cost collapses to 19 `imul`
patches. **Refuted, MEASURED.**

The reader (`0x00818C90`) and writer (`0x00819220`) both compute the slot address as
`lea eax, [ebx + ebx*4]` / `lea esi, [edi + eax*4]` — `base + index × 20`, fresh from the
record base on every call, with **no branch anywhere in the arithmetic for `index ≥ 51`**.
Raising the bound alone therefore lands index 51 on top of live tail data. There is no
version of "append" that does not require the tail to move.

### 2.2 …and the record's layout is not what the arc has been recording

The refutation is sharper than "index 51 lands four bytes into a slot", because the layout
in `MODDABLE.md` §1.2 is off by four bytes.

**MEASURED, triangulated three ways.** The binary-search locator at `0x00819340` keys on
`cmp ebx, dword ptr [eax]` at `0x00819382` — **`record + 0x00` is the search key**, not rank
data. The reader, given the record pointer the locator returned, reads its slot at
`[esi + 0x14]` where `esi = record + index × 20` — consistent only with an element spanning
`[esi+4, esi+24)`. And a constructor near `0x00823BF9` sizes the array directly:
`lea ecx, [esi+0xbc]` / `mov edx, 0x3fc` with the enclosing record base independently at
`esi+0xB8`.

| | `MODDABLE.md` §1.2 | **Corrected, this pass** |
|---|---|---|
| `[0x000, 0x004)` | — (part of the array) | **binary-search key** |
| the 51 × 20 array | `[0x000, 0x3FC)` | **`[0x004, 0x400)`** |
| the named tail | `[0x3FC, 0x43C)`, 64 B | **`[0x400, 0x43C)`, 60 B** |

`MODDABLE.md` calls the `0x3FC`/`0x43C` arithmetic *"the strongest structural evidence in this
document"* because it closes exactly. **It still closes exactly** — `4 + 1020 + 60 = 1084 =
0x43C` — so the claim survives, having been right for a slightly wrong reason. Appending
index 51 clobbers **five consecutive tail dwords** (`+0x400`, `+0x404`, `+0x408`, `+0x40C`,
`+0x410` — the whole pending-change header plus the start of the next pool header), not one.

### 2.3 The pessimistic reading also fails: a relayout is same-length everywhere it was found

**The answer is RELAYOUT, and it needs no detour and no out-of-band store.** Every stride and
size literal in class C is already `imm32` (`69 /r id` for the 19 `imul`; `81 /x id` for the
`add`/`sub`; `lea` with `disp32`), so `0x43C → 0x43C + delta` is a **byte-for-byte in-place
substitution** — the exact shape `make_custom_client.py` already applies four times.

**But the tail census is open, and one verified claim about it is wrong.** The A1 verification
asserted that every tail reference *"is necessarily encoded as an x86 `disp32`, because offsets
above `0x7F` cannot use the 1-byte `disp8` form, so a uniform delta is a same-length edit at
every reference."* The premise about `0x400 > 0x7F` is true and the conclusion does not
follow, because **the client does not address the tail from the record base.** It biases a
pointer first and then uses short displacements. Two measured counter-examples:

- **`0x00823DA0`, the reverse-walk destructor.** `imul esi, edi, 0x43c` → `add esi, 0x428` →
  then `mov dword ptr [esi - 4], 0`, `[esi + 4]`, `[esi]`, `mov ecx, [esi - 0x18]` — all
  **`disp8`**, all touching tail fields, all invisible to any scan for a displacement in
  `[0x400, 0x43C)`. The function contributes **zero** rows to such a scan while touching four
  tail fields.
- **`0x00818EB0`, the per-record zero-initialiser.** `add eax, 0x408`, then `mov [eax-4], 0`
  (`disp8`), then `lea eax, [eax + 0x43c]` and **thirteen negative `disp32` writes**
  (`[eax-0x43c]` … `[eax-0x414]`) covering `+0x400` through `+0x430` — including the two
  capacity defaults `+0x40C = 0x10` and `+0x41C = 0x40`.

So a relayout has **three different edit rules inside one function**: positive displacements
take `+delta`, negative biased ones take `−delta`, and `disp8` offsets relative to a bias that
itself moved take **no edit at all**. A mechanical "add `delta` to every displacement in the
tail range" patcher gets all three wrong and finds neither function.

What a byte-pattern census can see, MEASURED:

| Encoding | Sites | Scope |
|---|---|---|
| positive `disp32` in `[0x400, 0x43C)` | **91**, over 13 field offsets | `[0x818000, 0x81A000)` |
| negative `disp32`, biased-pointer idiom | **25** | the two attribute regions |
| `disp8` off a bias | **UNMEASURED — not findable this way** | at least 5, in the two functions above |

**≥ 116, and the census is not closed.** Two field offsets the zero-initialiser demonstrably
writes — `+0x41C` and `+0x430` — appear **nowhere** in the 91, which is how the blind spot was
found rather than assumed. Closing it means disassembling each record-touching function from a
trusted boundary. That function census is itself still moving: `MODDABLE.md` §5.2 says 19,
A1 said 7 touch the tail, its verifier found 11, and this pass adds the builder at
`0x00457B70` — **twelfth**, and outside every range either of them filtered on.

### 2.4 The fork

| | **Relayout (literal patches)** | **Out-of-band (detours)** |
|---|---|---|
| New code | none | a resident DLL + a trampoline engine |
| Sites | ≥ 64 literals + ≥ 116 displacements | ~11 function detours |
| Census | **OPEN** — the `disp8` set is not enumerable by scanning | **closed-ish** — functions are enumerable |
| Failure mode | silent memory corruption at an unpatched site | a detour that mis-restores state |
| Per-build cost | re-derive every site each client update | re-derive 11 signatures |

Relayout is mechanically simpler and needs nothing this repo does not already do. Its risk is
entirely in the census. **Neither is chosen here** — §6's ladder makes the census closable
offline before either is committed to, which is the decision that actually matters.

---

## 3. The 51 sites: BOUND, SENTINEL, or neither

**Someone will patch from this table. A wrong row silently corrupts 1,960 of 3,443 skill
rows — 56.9% of the skill table — by turning the NONE marker into a real attribute.**

`MODDABLE.md` §9 lists this split as UNMEASURED and calls it *"the number a stub generator
needs."* It is measured now, and the census it was to be measured over was itself short.

### 3.1 The corrected census

**57 real `cmp`-vs-51 instructions in `.text`**, not the 39 of `MODDABLE.md` §1.2's
orchestrator note and not the 55 of this pass's first attempt. Independently reproduced this
pass by anchored byte-pattern scan across **every** immediate encoding of `cmp` — `0x3C`/`0x3D`
(the AL/EAX short forms), `0x80`/`0x81`/`0x83` `/7`, register and memory operand, 8- and
32-bit — with each hit confirmed by a forward decode from a trusted boundary reaching it
exactly.

| Form | Candidates | Confirmed | Note |
|---|---|---|---|
| `cmp r32, 0x33` | 39 | **39** | the previously-known population, reproduced exactly |
| `cmp [mem], 0x33` (32-bit) | 9 | **9** | previously uncounted — `MODDABLE.md` §1.2a names this as a gap |
| `cmp r8, 0x33` | 48 | **8** | `0x33` is ASCII `'3'`; 40 of 48 are byte-pattern coincidences |
| `cmp [mem], 0x33` (8-bit) | 3 | **1** | the skill row's `+0x29` field |

Both builds reproduce 39 and 9 exactly, at build-shifted addresses, with identical cluster
shapes.

| Class | Count | Meaning |
|---|---|---|
| **BOUND** | **18** | array-size guard. **Patch to N.** |
| **SENTINEL** | **10** | equality against id 51 = NONE. **MUST NOT MOVE.** |
| **Unrelated** | **28** | other subsystems that also bound-check at 51. **Do not touch.** |
| **Unresolved** | **1** | `0x008CB113` — result consumed by `sbb`, not a branch |

### 3.2 BOUND — patch these 18 to N

| VA | Form | Module | Role |
|---|---|---|---|
| `0x005A9265` | reg | `ConstAttrib` | pointer-array iterator's loop bound |
| `0x005A9297` | reg | `ConstAttrib` | accessor → description id |
| `0x005A92C7` | reg | `ConstAttrib` | accessor → primary flag |
| `0x005A92F7` | reg | `ConstAttrib` | accessor → name id |
| `0x005A9327` | reg | `ConstAttrib` | accessor → owning profession |
| `0x00818CC9` | reg | `ChCliAttrib` | **the rank reader** |
| `0x00819244` | reg | `ChCliAttrib` | **the rank writer** |
| `0x0080D913` | mem32 | `ChCliApi` | |
| `0x008A78C2` | mem32 | `AttribList` | create-parameter guard |
| `0x008CAB94` | reg | `GmCtlSkList` | |
| `0x008CB0CC` | reg | `GmCtlSkList` | |
| `0x008ED174` | reg | `GmTipCharAttrib` | tooltip |
| `0x0091CEC0` | mem32 | `AcctTemplate` | **build-template id validator** |
| `0x0091D30B` | reg | `CharData` | silent bound — no adjacent assert |
| `0x0091D387` | reg | `CharData` | silent bound — no adjacent assert |
| `0x00922FD9` | mem32 | `ItemName` | attribute-restriction field |
| `0x00923ABB` | reg | `ItemName` | |
| `0x00923B32` | reg | `ItemName` | |

`0x0091CEC0` is a memory-operand form and is therefore **absent from `MODDABLE.md`'s 39-site
register-only sweep** — the gap that document flagged is real and non-empty.

### 3.3 SENTINEL — these 10 must NOT move

**Id 51 stays the NONE marker forever.** 1,960 of 3,443 skill rows carry it at `+0x29`
(re-measured this pass through `skilltable.py`'s own structural locator: 3,443 rows, 43
distinct attribute values). The first custom attribute is **52**.

| VA | Form | Module | Evidence it is an equality test |
|---|---|---|---|
| `0x0081A077` | reg | character panel | follows `call 0x005A9210`; `je` to a no-attribute path |
| `0x0081A1F9` | reg | character panel | same shape |
| `0x0081A240` | reg | character panel | same shape |
| `0x0081A3FB` | reg | character panel | same shape |
| `0x008CAB27` | **mem8** | `GmCtlSkList` | reads the skill row's `+0x29` byte directly |
| `0x008CAB68` | reg | `GmCtlSkList` | the same field, widened, immediately after |
| `0x008CB097` | reg | `GmCtlSkList` | |
| `0x0092434A` | reg | `ItemName` | on-equal → placeholder string id |
| `0x009258E3` | reg | `ItemName` | on-equal → placeholder string id |
| `0x009261AB` | reg | `ItemName` | on-not-equal → `call 0x005A92F0` |

**And an eleventh site that no `cmp` census can contain.** The iterator at `0x005A9210`
*produces* the sentinel on its out-of-range return path: **`mov eax, 0x33` at `0x005A9284`**.
It sits inside the same function as BOUND site `0x005A9265`, it is what the four
character-panel sites compare against, and it must **not** change. A patcher that swept
`mov r32, 0x33` alongside `cmp r32, 0x33` — the obvious way to catch class A's three `mov`
sites — would rewrite it and break every sentinel test at once.

### 3.4 Unrelated — 28 sites, do not touch

Confirmed by direct disassembly for the structurally interesting ones: three compiler
switch-dispatch jump tables (`0x0053A575`, `0x00583D11`, `0x005D7E18` — `cmp`/`ja`/`movzx`/
`jmp [table]`), two small-set equality checks against `{5, 51, 61}` at `0x0081BD8B` and
`{10, 51}` at `0x0086B55D`, a two-word type-code parser (`0x005BA0DD`, `0x005BA236`,
`0x005BA3A6` — matching ASCII digit pairs), a four-site `GmEffect`/`Array.h` cluster
(`0x00521FAD`, `0x005226EB`, `0x00522AF6`, `0x00522EE5`), and `AcctTemplate`'s *different*
field at `0x0091CC49`. Also checked and clear: **no off-by-one variant** — the only `cmp`-vs-50
and `cmp`-vs-42 sites in the image (`0x005A9074`, `0x005A9117`) belong to `ConstItem`
accessors compiled immediately before the `ConstAttrib` cluster. Linker adjacency, not
semantics.

---

## 4. Corrections

`grows`: **GROWS WITH CAVEATS.** No track returned DOES NOT GROW or GROWS ONLY TO ~60, so no
correction leads this section on that basis. The three below are ordered by how badly acting
on the uncorrected claim would hurt.

### 4.1 A function nobody in this arc has seen: the pointer-array builder

**NEW, MEASURED this pass.** `0x00457B70` builds the 51-entry pointer array at startup:

```
00457B83  mov eax, 0xc0eec0     <- the array, inlined
00457B88  mov ecx, 0xa35740     <- the table base, inlined
00457B8D  mov edx, 0x33         <- 51, hardcoded, NO assert
00457B92  mov [eax], ecx
00457B94  lea eax, [eax+4]
00457B97  add ecx, 0x14         <- the 20-byte row stride
00457B9A  sub edx, 1
00457B9D  jne 0x457b92
```

**This is `MODDABLE.md` §5.3's `0x005A8600` problem in the attribute dimension**, and §5.3
calls that function *"the concrete counter-example to 'every table sits behind one
accessor'."* Here is the same shape for attributes: base inlined, count inlined, stride
inlined, no assert, no accessor call. It is invisible to the assert-walk census (no assert),
invisible to the `cmp r32, 0x33` sweep (it is a `mov`), and invisible to `--xrefs` on the four
accessors (it calls none). `--xrefs` on it returns **0 direct callers and 1 stored VA in
`.rdata`** at `0x0093991C` — a static-initialiser table, so it is reached indirectly.

**How it was missed, including by this pass.** The A2 verification did sweep `mov r32, 0x33`
image-wide, found 22 sites, and cross-checked them "against every already-identified attribute
function range" — finding exactly one. I made the same mistake with the same filter and got
the same three. `0x00457B8D` is outside every range in that filter, **because nobody knew the
function existed.** It surfaced only by chasing the pointer array's absolute address instead of
the constant. *A range filter built from the known census cannot find a function outside the
census* — the same shape as the linear-sweep failure this arc already records, from the other
side.

### 4.2 Two claims weakened: the "uniform `disp32` delta" and the closed function census

The A1 verification's claim that a tail relayout is *"a same-length immediate edit at every
site, because every tail-field reference is necessarily `disp32`"* is **refuted as stated** by
`0x00823DA0` and `0x00818EB0` (§2.3). The *conclusion* — that a relayout is same-length —
survives at every site measured; the *reason* does not, and the reason was load-bearing for
the claim that a displacement scan could enumerate the sites. It cannot. **≥ 116 is a floor.**

Relatedly, the "7 functions touch the tail" figure is an undercount. Verified to 11 by the A1
verification, and 12 with `0x00457B70`. Treat 12 as the new floor.

### 4.3 `MODDABLE.md` §1.2 and §1.2a, superseded by claim

| Claim | Status |
|---|---|
| §1.2 *"a 51 × 20 array embedded at offset 0 of a `0x43C`-byte record"* | **Corrected.** Array is `[0x004, 0x400)`; `[0x000,0x004)` is the binary-search key. §2.2 |
| §1.2 *"named fields at `+0x400` … filling `[0x3FC, 0x43C)` exactly"* | **Corrected.** Tail is `[0x400, 0x43C)`, 60 B. The arithmetic still closes exactly |
| §1.2 *"19 detours **plus** either a struct relayout … or an out-of-band store"* | **Superseded.** No detour is needed: the relayout is same-length. §2.3 |
| §1.2a *"the out-of-band store is therefore the only candidate, not one of two"* | **Refuted.** It is one of two, and it is the more expensive one |
| §1.2a *"`0x43C` occurs at 55 sites … the rest being `lea`/`add`/`sub`/displacements"* | **Corrected.** Only **26** are attribute-related; 27 belong to other structures. §1.1-C |
| §1.2a *"18 of the 19 sit in `[0x818000,0x81A000)`; one is outside, at `0x00823DB4`"* | **Corrected address.** The instruction is at **`0x00823DB2`**; `0x00823DB4` is its immediate. Same error class as the `0x00819340`/`0x0081934E` correction §1.2 already records — and it repeats on the cross-check build (`0x0081D9A2`, cited as `0x0081D9A4`) |
| §1.2a *"the BOUND-vs-SENTINEL split is unmeasured"* | **Closed.** §3 |
| §1.4 *"arbitrary is the one dimension nobody has measured a route through"* | **Closed.** The route is §1.1; the number is 204 |
| §9 *"`0x003A`'s per-dword encoding — packed or positional? NOT FOUND"* | **Closed. MEASURED** — three parallel arrays. §1.2 |
| §9 *"does the skill-template codec's profession field have its own width?"* | **Closed.** Variable-width, up to 19 bits for the attribute field; the real limit is 12 entries per build. §1.2 |
| §9 *"where is the pointer array populated?"* | **Closed.** `0x00457B70`. §4.1 |

One correction in the other direction: the A3 track attributed a "42 independently-zeroed
attribute slots" claim to `authsrv.py`'s current comment. That comment already retracts
exactly that claim. The *payload* is still wrong (§1.2); the *citation* was stale.

---

## 5. The routes that do not grow the table

Costed against arbitrary N, with what a player actually sees. All four are **MEASURED** this
pass, and the ownership mechanism they all share was independently re-derived.

**The mechanism.** Each table row's `+0x00` owning-profession field is read by exactly
**6 direct call sites** of accessor `0x005A9320`, and every one **re-reads the table at call
time** — nothing bakes a copy. So reassigning a row's owner is a same-length, zero-relocation
**data** patch, and it reaches every consumer including the build-template codec. The check
itself: membership in the character's primary/secondary pair via `0x0081FC60`, plus, if the
row's primary flag is set (`0x005A92C0`), exact equality with the primary via `0x0081FA80`.
On failure the client writes **`-1`** into the rank entry's `+0x10` field (`0x00818DF0`).

| Route | Ceiling | Cost | **What a player sees** |
|---|---|---|---|
| **0. Do not grow at all.** Server-side scaling only; no client edit | **unlimited professions, ZERO new attribute identity** | none | Skills scale, but the attribute has no name of its own and the ownership check still fires: the `-1` write lands on the rank entry. **CONTESTED how visible** — plausibly the allocation UI for that stat, not merely its label. The trace from `-1` to a UI consumer is **NOT FOUND** |
| **1. Fill the 9 reserved ids** (26, 27, 28, 45–50) | **9 — about 2 professions** | **free.** Text records only | Indistinguishable from a shipped attribute, if the text is authored. Triple-confirmed inert: profession field = 11 sentinel, **0 of 3,443** skill rows reference them, **all 18** name/description ids resolve to empty archive records (positive control in the same call resolves real text) |
| **2. Reuse a donor profession's ids** | **≤ 10 donors, ~42 ids** | same-length `.rdata` edits at file offset `0x634740`; **zero code** | Full attribute identity for the custom profession — **and the donor profession's attributes are crippled on that client.** Also rides on the separately-costed profession work: the codec at `0x0091CB90` rejects any profession `≥ 0xB` regardless of the table |
| **3. Grow the table** (§1) | **204** | §1.1 | Everything works, including build templates. The only route that is not a costume |

Route 2's cost is worth stating plainly: it is not "a donor loses some polish". A donor
profession whose ids were reassigned reads its own attributes through the same six accessors
and gets the custom profession's rows back.

**A previously uncounted site, found under route 3's ownership trace.** The build-code decoder
at `0x0091CB90`–`0x0091CD43` bound-checks **both** professions against `0xB` (`0x0091CBCA`,
`0x0091CBCF`) and the attribute id against `0x33` (`0x0091CC49`) — and the whole function is
**assert-free**, so it is invisible to `MODDABLE.md`'s 34-function profession census and
19-function attribute census, both of which were built by walking assert sites backward. It is
the one path that **leaves the machine** (a string written to disk and pasted between players),
and missing it does not crash — it silently drops the custom attribute from any shared build.
`MODDABLE.md` §8a pointed this question at `0x0058A790`, which is a display-formatting helper.

**Reproduced on both builds, 90 days apart:** the same 11 profession groups, the same 9
reserved rows, the same file-offset-located table (`0x634740` / `0x6289D8`), the same 39/9
`cmp` counts and cluster shapes.

---

## 6. The ladder

Cheapest first. **Everything above the launch line is offline** and the whole offline block is
hours, not days. Each rung states its **question**, its **prediction** and **what to watch**
before its method — a rung with no stated expectation can be rationalised into agreeing with
anything afterwards.

---

**L0 — Preserve this pass's scratch scans. Minutes.**
`vault/research/profession-attributes-2026-08-12/`. §9's reproduce block regenerates every
number, but a reproduce section citing a directory that deletes itself is not a reproduce
section — the `MODDABLE.md` §10 precedent.

---

**L1 — GATE. Close the tail-reference census. Offline, hours.**

> **Question.** How many instructions reference the per-character record's tail, counting the
> `disp8`-off-a-bias references that no displacement scan can see?
>
> **Prediction.** More than 116 and fewer than 200, concentrated in the 12 known
> record-touching functions, with at least two more biased-pointer idioms beyond
> `0x00823DA0` and `0x00818EB0`.
>
> **What to watch.** A function that touches the tail and contributes **zero** rows to the
> displacement scan — that is the signature of the blind spot, and finding a third instance
> means the count is still a floor. Watch also for a tail field with readers and no writer:
> real and interesting, not an error.

Method: disassemble each of the 12 functions from a trusted boundary (`func_start`, spot-checked
for `push ebp; mov ebp, esp`) to its `ret`, and record every memory operand whose effective
target lands in `[0x400, 0x43C)` under the function's own bias. **Do not** disassemble the
cluster linearly — that is the failure `MODDABLE.md` §1.2 records, where a linear sweep
reported a confident **zero** `imul` and **zero** `cmp` sites in an image holding 19 and 39.

**Gate: do not cost either architecture in §2.4 until this returns a number that stops moving.**
It has moved at every pass so far.

---

**L2 — Build the patch offline and re-run the census against it. Offline, hours. No launch.**

> **Question.** Does the class A–F edit set, applied at `N = 52`, produce an image in which
> every measured invariant still holds?
>
> **Prediction.** All same-length: file size unchanged, section table unchanged, and the
> `0x43C`→`0x450` substitution visible at exactly 26 sites and nowhere else.
>
> **What to watch.** **The 27 unrelated `0x43C` carriers must be byte-identical.** If any moved,
> the patcher is scoping by constant rather than by subsystem, and §1.1-C's correction was not
> applied. Equally: the 10 SENTINEL sites and `mov eax, 0x33` at `0x005A9284` must still read
> `0x33`.

`N = 52` is deliberate — one new attribute, the smallest edit that exercises every class, and
`delta = 20`, small enough that a mis-signed displacement lands inside the record rather than
outside it, where the next rung can observe it rather than crash on it.

---

**L3 — The free rung: author the 9 reserved ids. Offline, then one caged launch.**

> **Question.** Does a reserved row with authored text behave as a real attribute?
>
> **Prediction.** Yes for id 26, 27, 28 and 45–50 — the definition rows already exist, carry the
> reserved profession marker 11, and their string ids resolve to empty records.
>
> **What to watch.** The `-1` invalidation of §5 route 0. A reserved row reassigned to a
> **shipped** profession should allocate normally; one left on marker 11 should not. That
> difference is the cheapest available probe of what the `-1` write costs a player, and it
> answers §7's top NOT FOUND as a side effect.

Archive writes against a **copy** only — never `vault/dat_study/Gw.dat`, never `C:\gw`.

---

**L4 — First launch. `N = 52` against loopback.** Inherits every house rule written into the
rung: ours-DH build, `dhbuild.py`-verified, `cage.assert_launch_safe(exe, host)`, loopback
only, named account.

> **Question.** Does the client open a character with a 52-row attribute table?
>
> **Prediction.** It opens. The failure, if any, is the tail — a wrong displacement corrupts
> the pending-change or pool headers, which the client reaches on the *second* attribute
> interaction, not the first.
>
> **What to watch.** The crash-dialog capture, because it is the only machine-readable evidence
> a client assert leaves — `Gw.log` does not record asserts and a `ConnectionResetError` in the
> gamesrv log appears on a clean teardown too. **And watch for the client staying alive behind a
> modal dialog with its message pump stopped**: `test_smsgsweep.py` §"proof of life" records a
> run that scored 78 opcodes SILENT against exactly that state.

---

**L5 — `N = 256` and the two relocations.** Only after L4. The table must move (0 slack) and
the pointer array must move (≤ 7 slots), so this rung is where the new-section question from
`MODDABLE.md` §S2 actually binds — and unlike the profession dimension, here it is unavoidable
rather than a design choice.

---

**L6 — The wire.** Fix `authsrv.py`'s `0x003A` payload to emit `ceil(N/16)` messages of
triples rather than one array of `[0] * 42`, per §1.2. Independent of every rung above;
sequenced last only because nothing else depends on it.

---

## 7. Open items and NOT FOUND

These are results.

| Question | Status | What would answer it |
|---|---|---|
| The `disp8`-off-a-bias tail references | **UNMEASURED, and not findable by scanning** | **L1.** Per-function disassembly from a trusted boundary |
| Is the record-touching function census closed at 12? | **Floor, not census.** It has grown at every pass: 7 → 11 → 12 | L1. Enumerate constructors/destructors/copy/reset paths systematically rather than incidentally |
| What consumes the `-1` written at `0x00818DF0`? | **NOT FOUND.** Traced one hop further than the dig: the invalidator's two callers funnel through the same `ChCliApi`-adjacent cluster as the documented reader, which raises plausibility and proves nothing | **L3**, as a side effect. Or a logging detour in one caged session |
| `0x008CB113` — real, confirmed, `cmp` consumed by `sbb` not a branch | **UNRESOLVED.** One of 57 | Trace the flag to its use. Minutes |
| `0x0091CC49` — `AcctTemplate`, `cmp` consumed by `setl` | **UNRESOLVED** | Same |
| Where does the pending-change array grow? | **NOT FOUND.** The writer's merge loop was traced to its `ret` and contains no capacity-check-and-grow | Find the append path. It is not keyed to 51 or `0x43C` in anything traced, so it probably does not bind — but "probably" is not a measurement |
| Is `0x00457B70` reached only through the `.rdata` initialiser table? | **UNMEASURED.** 0 direct callers, 1 stored VA | `--xrefs` on `0x0093991C`'s enclosing table |
| Does the sized-delete at `0x00818713` (`push 0x43C`) ever run? | **NOT FOUND.** Guarded by a flag its one static caller passes as 0 | If dead, the class-C count is 25 not 26. Costed as live, which is the safe direction |
| What lies immediately after the definition table at `0x00A35B3C`? | **UNMEASURED.** Known only that `.text` references it, hence slack = 0 | Identify the object. It decides whether relocation is the only option or merely the clean one |
| Does `0x00C0EFA8` bound the pointer array's slack, or is it unrelated? | **UNMEASURED.** 28 bytes is an **upper** bound on slack — a global with no absolute reference would not show | A `.data` object census, or accept 7 as a floor-of-a-ceiling |
| Is a relocated table reachable at all on the real exe? | **UNMEASURED** — the new-section question, inherited from `MODDABLE.md` §7 risk 7 | **L5**, then one caged launch |
| The 21 other image-wide `mov r32, 0x33` sites | **UNMEASURED.** Not traced to their consuming compares | A full dataflow trace. §4.1 is the reason this is not obviously safe to skip |
| Does the 12-entry build-template cap bind a real custom profession? | **UNMEASURED, and probably not** — a primary+secondary pair needs ~10 | Count the attributes an actual custom profession pair would reference |
| Do the 51 sites' classifications hold on 2026-04-30? | **Counts and shapes: yes, MEASURED.** Per-site re-reading: **UNMEASURED** | Re-run §9's block with the second tag |

---

## 8. Provenance

This document reports **addresses, counts, bounds, offsets, strides, ids, layouts and field
widths**. It reproduces no assert expression text, no assert expression paired with a source
path and line, no decompiled function bodies, no asset bytes, no authored strings. Assert sites
are cited as **VA + module name only**, one step tighter than `FINDINGS.md` §3's VA + module:line
convention, because several of this pass's rows would otherwise pair an expression with its file.

Per `CLAUDE.md`'s 2026-08-11 ruling, the boundary is **MEASUREMENT vs EXPRESSION**, and every
row here is measurement. Any table derived from these numbers and committed to `content/*.toml`
carries `source = "client-table"` with the extractor named in the row and the build recorded,
per `toolkit/content.py`'s enforced refusals.

**Second gate.** No upstream was read for this pass. `gw-preservation/*` and `Py4GW_Reforged`
grant nothing and were not consulted; the `0x003A` three-array reading in §1.2 was
**re-derived from our own client's disassembly** specifically so it stops depending on the
third-party reimplementation `studies/character/FINDINGS.md` labels single-lineage. No
`PLAN.md` §6.1 row is required by anything in this document. A row **is** required before the
detour architecture of §2.4 vendors a trampoline engine.

---

## 9. Reproduce

Read-only against the pinned build. **Resolve the vault with `vaultpath`, never with a
relative `vault/...`** — a worktree has no vault of its own and the relative form silently
resolves to nothing, turning every assertion behind it into a no-op.

**Byte-pattern counts, never a linear sweep.** A linear disassembly from a section start
desynchronises on data and padding and then silently decodes garbage: `MODDABLE.md` §1.2
records a sweep that reported a confident **zero** `imul`-by-`0x43C` sites and **zero**
`cmp`-vs-`0x33` sites in an image containing 19 and 39, and was nearly written up as a
refutation of that document's strongest claim.

```bash
EXE="$(python -c "import sys; sys.path.insert(0,'toolkit'); import vaultpath; \
      print(vaultpath.vault_path('client','2026-07-29_221c13772c7a','Gw.exe'))")"

# ---- 3.1: the 57-site cmp-vs-51 census, every immediate encoding.
# Anchored: decode AT each byte-pattern hit, require capstone to agree the
# immediate is 0x33, then confirm the boundary by a forward decode that
# reaches it exactly.  0x33 is ASCII '3' -- 40 of 48 REG8 hits are noise.
python - <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "toolkit"))
import vaultpath, pefile, capstone
pe   = pefile.PE(str(vaultpath.vault_path("client","2026-07-29_221c13772c7a","Gw.exe")),
                 fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
sec  = next(s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text")
data, lo = sec.get_data(), base + sec.VirtualAddress
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True

buckets = {}
for i in range(len(data) - 8):
    op = data[i]
    if op not in (0x3C, 0x3D, 0x80, 0x81, 0x83):     # incl. the AL/EAX short forms
        continue
    if op in (0x80, 0x81, 0x83) and (data[i+1] >> 3) & 7 != 7:   # /7 == cmp
        continue
    ins = next(md.disasm(data[i:i+10], lo+i, count=1), None)
    if ins is None or ins.mnemonic != "cmp" or len(ins.operands) != 2:
        continue
    dst, src = ins.operands
    if src.type != capstone.x86.X86_OP_IMM or src.imm != 0x33:
        continue
    key = ("REG" if dst.type == capstone.x86.X86_OP_REG else "MEM") \
        + ("8" if dst.size == 1 else "32")
    buckets.setdefault(key, []).append((ins.address, ins.op_str))

def real(addr):                      # a hit is a candidate, not a site
    off = addr - lo
    for back in range(0x40, 0x1000, 0x40):
        for ins in md.disasm(data[max(0,off-back):off+16], lo+max(0,off-back)):
            if ins.address == addr: return True
            if ins.address >  addr: break
    return False

tot = 0
for k in ("REG32","MEM32","REG8","MEM8"):
    ok = [h for h in buckets.get(k,[]) if real(h[0])]
    tot += len(ok)
    print("cmp 0x33 %-6s candidates %3d  confirmed %3d"
          % (k, len(buckets.get(k,[])), len(ok)))
    if k in ("REG32","MEM32"):
        for a,o in ok: print("    0x%08X  cmp %s" % (a,o))
print("TOTAL real cmp-vs-51 sites:", tot)          # 39 + 9 + 8 + 1 = 57
PY

# ---- 1.1-C: the 0x43C carriers, SCOPED.  55 raw, 53 decode, and only 26
# are the attribute record's -- 25 in the cluster plus one outlier imul.
python - <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "toolkit"))
import vaultpath, pefile, capstone
from collections import Counter
pe = pefile.PE(str(vaultpath.vault_path("client","2026-07-29_221c13772c7a","Gw.exe")),
               fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
sec  = next(s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text")
data, lo = sec.get_data(), base + sec.VirtualAddress
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True
rows, undec, s = [], [], 0
while True:
    i = data.find(b"\x3c\x04\x00\x00", s)
    if i < 0: break
    s = i + 1
    for back in range(1, 9):        # back=1 matters: push/mov imm32 forms
        ins = next(md.disasm(data[i-back:i+8], lo+i-back, count=1), None)
        if ins is None or ins.address + ins.size < lo + i + 4: continue
        if not any((o.type == capstone.x86.X86_OP_IMM and o.imm == 0x43C) or
                   (o.type == capstone.x86.X86_OP_MEM and o.mem.disp == 0x43C)
                   for o in ins.operands): continue
        rows.append((ins.address, ins.mnemonic)); break
    else:
        undec.append(lo + i)
inc = [r for r in rows if 0x818000 <= r[0] < 0x81A000]
out = [r for r in rows if not (0x818000 <= r[0] < 0x81A000)]
print("raw 3C 04 00 00: %d   decoded: %d   undecoded: %d"
      % (len(rows)+len(undec), len(rows), len(undec)))
print("  cluster [0x818000,0x81A000): %2d  %s" % (len(inc), dict(Counter(m for _,m in inc))))
print("  elsewhere                  : %2d  %s" % (len(out), dict(Counter(m for _,m in out))))
print("  attribute-related total    : %d   (cluster + the 0x00823DB2 outlier)" % (len(inc)+1))
PY

# ---- 1.1-A/B/E: the literals no cmp sweep can see.  0x00457B8D is the one
# that was missed by filtering on the KNOWN attribute function ranges.
python - <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "toolkit"))
import vaultpath, pefile, capstone
pe = pefile.PE(str(vaultpath.vault_path("client","2026-07-29_221c13772c7a","Gw.exe")),
               fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
sec  = next(s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text")
data, lo = sec.get_data(), base + sec.VirtualAddress
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = True
def anchored(val, want=None):
    hits, s = [], 0
    while True:
        i = data.find(val.to_bytes(4, "little"), s)
        if i < 0: return hits
        s = i + 1
        for back in range(1, 10):
            ins = next(md.disasm(data[i-back:i+10], lo+i-back, count=1), None)
            if ins is None or ins.address + ins.size < lo + i + 4: continue
            if want and ins.mnemonic != want: continue
            if not any((o.type == capstone.x86.X86_OP_IMM and o.imm == val) or
                       (o.type == capstone.x86.X86_OP_MEM and o.mem.disp == val)
                       for o in ins.operands): continue
            hits.append((ins.address, ins.mnemonic, ins.op_str)); break
for val, label in ((0x00C0EEC0, "pointer-array start"),
                   (0x00C0EF8C, "pointer-array end"),
                   (0x00A35740, "51x20 table base")):
    print("== 0x%08X  %s" % (val, label))
    for a, m, o in anchored(val): print("   0x%08X  %-5s %s" % (a, m, o))
print("== mov-immediate 0x33 (51) -- 3 structural, 1 of which must NOT move")
for a, m, o in anchored(0x33, "mov"):
    if a in (0x00457B8D, 0x005A9284, 0x0081849D, 0x00818870):
        note = "   <-- SENTINEL PRODUCER, do not patch" if a == 0x005A9284 else ""
        print("   0x%08X  mov %s%s" % (a, o, note))
print("== mov-immediate 0x3FC (the array's byte size)")
for a, m, o in anchored(0x3FC, "mov"):
    if 0x818000 <= a < 0x826000: print("   0x%08X  mov %s" % (a, o))
PY

# ---- 2.2/2.3: the layout correction and the blind spot, read directly.
# Locator keys on [record+0]; reader slots at [esi+0x14]; zero-init biases
# by 0x408 and then writes 13 dwords by NEGATIVE disp32.
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x00819340 --count 24
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x00818CC9 --count 8
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x00818EB0 --count 26
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x00823DA0 --count 22

# ---- 4.1: the pointer-array builder.  Base, stride and count all inlined,
# no assert, no accessor call, 0 direct callers, 1 stored VA in .rdata.
python toolkit/clientscan/codescan.py --exe "$EXE" --dis   0x00457B70 --count 16
python toolkit/clientscan/codescan.py --exe "$EXE" --xrefs 0x00457B70

# ---- 1.2: 0x003A is three parallel arrays, from OUR client, not upstream.
python toolkit/clientscan/msgshape.py 0x003A          # [agent_id, array32[48]]
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x0091D8C0 --count 30
python toolkit/clientscan/codescan.py --exe "$EXE" --dis 0x00819220 --count 12

# ---- 5: the reserved rows are inert, checked three independent ways.
python toolkit/clientscan/skilltable.py --exe "$EXE"   # 3443 rows; 1960 carry 51
python toolkit/clientscan/textrec.py                   # the 18 reserved ids -> empty
```

The 51×20 table's own grouping, the `0x43C` classification and the `cmp` census all reproduce
on the cross-check build `2026-04-30_b174de1f2d8d` at its own structurally-located offset
`0x6289D8` — same eleven profession groups, same nine reserved rows, same 39 and 9 counts,
outlier `imul` at `0x0081D9A2`. Swap the tag in any block above.
```

---

## 12. Two findings that outlive this document

**1. The pointer-array builder at `0x00457B70` was invisible to every census method this arc
has used, and it is the attribute dimension's exact analogue of `MODDABLE.md` §5.3's
`0x005A8600`** — inlined base, inlined stride, hardcoded count, no assert, no accessor call.
Three passes of censuses missed it. It surfaced only when somebody searched for the pointer
array's **absolute address** rather than for its **constant**, because every prior sweep
filtered by VA range or by the `0x33`/`0x43C` immediates, and this site is reached by neither
route from those starting points.

That is a **method** result, not a profession result: *a census keyed on a constant cannot see
a site that only mentions an address, and vice versa.* Both directions are needed, and this
arc has now been bitten by the same shape four times — pass 1's `--field`/`--xrefs`
under-reporting, pass 2's basename collision, pass 3's linear-sweep desync, and this.

The loop is worth reading once, because it validates the whole geometry in six instructions:
it loads the pointer-array base and the definition-table base, sets a count of `0x33`, then
stores a pointer, advances the destination by 4 and the source by `0x14`. **51 records, 20
bytes apart, 4-byte pointers — confirmed by construction rather than inferred.**

**2. Neither table has room to grow in place.** The definition table has **zero** bytes of
slack (its end address is itself referenced by `.text`, so another object begins exactly
there) and the pointer array has **at most seven** spare slots. §1's 204 is therefore gated on
two data relocations that no prior document in this arc costed, which is why L5 sits after a
launch rung rather than before one.

---

## 13. Orchestrator verification

Four headline claims were re-derived independently from the binary before this document was
committed. **All four hold**, by byte pattern and targeted disassembly rather than by linear
sweep:

| Claim | Result |
|---|---|
| The skill row's attribute field is read as a **byte**, setting the 255 ceiling | **CONFIRMED** — `80 78 29 33` at `0x008CAB27` decodes exactly as `cmp byte ptr [eax + 0x29], 0x33` |
| The pointer-array builder exists at `0x00457B83` with `mov edx, 0x33` | **CONFIRMED** — and the two instructions above it load `0xC0EEC0` and `0xA35740`, with `lea eax,[eax+4]` / `add ecx,0x14` below |
| The definition table has zero in-place slack | **CONFIRMED** — `51 × 20` ends at `0x00A35B3C`, and that address is referenced in `.text` **4 times** |
| The pointer array has ≤ 7 spare slots | **CONFIRMED** — `(0xC0EF8C − 0xC0EEC0) / 4 = 51`; the next `.text`-referenced address is `0xC0EFA8`, a gap of 28 B = 7 slots |

**And one proposal of the orchestrator's was refuted by this pass, which is the point of
running it.** The brief proposed an *append* design — ranks 51..N in a tail beyond `0x43C`,
leaving `0x000`–`0x43B` untouched so that no displacement moves — as a way to collapse the
cost to the 19 `imul` patches. §2.1 refutes it from the code: the reader and writer both
recompute `base + index × 20` fresh on every call with **no branch for `index ≥ 51`**, so
raising the bound alone lands index 51 on live tail data. §2.2 then makes the refutation
sharper than the proposal was wrong, by finding that the array actually starts at `+0x004`
(record `+0x00` is a binary-search key), so an appended index 51 would clobber **five**
consecutive tail dwords rather than one.

The half of the brief that did hold is the one that mattered for scope: the `0x43C` stride
sites are `69 /r imm32` and therefore **same-length patchable**, which is what makes relayout
a patch rather than a rewrite — and what refutes `MODDABLE.md`'s "out-of-band store is the
only candidate". **The brief's caution about the other `0x43C` carriers was also warranted and
then some:** of the 53 that anchor-decode, only **26** are attribute-related; the other 27
belong to unrelated structures. A patcher driven by "every `0x43C` in `.text`" corrupts 27
innocent sites.

---

## 14. The tail census — closed for two encodings, and a correction to this section

§1.1 class D shipped as **"≥ 116 tail edits whose census is NOT closed"** — the one estimate
in a document otherwise made of counts. Closing it took two attempts, and **the first was
wrong in a way worth keeping on the record**, because it is this arc's recurring failure
committed by the person who had just written the warning against it.

### 14.1 The first attempt, and why 97 was the wrong answer

A scan for memory operands with a displacement in `[0x400, 0x43C)` and a base register,
decoded from trusted boundaries with each function bounded by the next known entry, gives a
very stable number: **97 sites over 19 functions — 93 in the `ChCliAttrib` cluster plus 4 in
`0x0081A410` — identical on build 38797 and on 2026-04-30**, with a second call-graph hop
adding zero. Total such sites in `.text` is 274; the other 177 belong to unrelated structures.

That number is correct and it is **not the census.** It counts **one encoding**. §2.3 already
recorded the other and named two instances (`0x00823DA0`, `0x00818EB0`), and the first attempt
declared closure without testing against them. The test it should have run is the one §2.3
supplies for free: **`+0x41C` and `+0x430` are fields the zero-initialiser demonstrably
writes, and neither appears among the 97.** Two absent fields, in a set claimed to be
complete.

### 14.2 The second encoding: a biased pointer

`0x00823DA0` is the shape. It computes `imul esi, edi, 0x43c`, then **`add esi, 0x428`** to
bias the pointer into the tail, then adds the record base — and every subsequent field access
reads at a *negative* displacement from that biased pointer (`mov ecx, [esi - 0x440]`,
`lea esi, [esi - 0x43c]` to walk backwards a record at a time). **A `[0x400, 0x43C)`
displacement scan cannot see any of it**: the bias is an arithmetic immediate rather than a
memory displacement, and the accesses land at `-0x4xx`.

Measured across the 43 record-touching functions (the cluster, every function carrying an
`imul`-by-`0x43C`, and `0x0081A410`):

| Form | Sites | Example |
|---|---|---|
| Direct, `disp32` in `[0x400, 0x43C)` | **97** | §14.1 |
| **Bias-establishing** `add reg, imm` with imm in the tail range | **5** | `0x00818EC1` `+0x408` · `0x00819199` `+0x428` · `0x00819926` `+0x410` · `0x0081A2D0` `+0x424` · `0x00823DB8` `+0x428` |
| **Biased accesses** at negative displacement near `−0x43C` | **25** | `0x00818EDD` `[eax−0x43c]` … `0x00818F23` `[eax−0x424]`; `0x00818846`–`0x0081886A` in the shifter |
| **Total tail references to patch** | **127** | |

The five bias immediates are themselves edits: each encodes a tail offset and must move with
`delta`. And `0x00818EB0`'s writes to `[eax−0x430]` and `[eax−0x424]` are exactly the
`+0x41C`/`+0x430` fields that were missing from the 97 — the blind spot closing on the
evidence that revealed it.

**So the document's original floor was the better number.** "≥ 116" was right; "97, closed"
was wrong; the count across both encodings is **127**.

### 14.3 What is closed, what is not

**Closed:** the two encodings above, over the 43 record-touching functions, on both builds.

**Not closed, and stated rather than implied:**

- **Other encodings.** Two were found because §2.3 named them. A third idiom — a bias held in
  a stack slot, an index folded into a `lea` scale, a `memcpy` of a sub-range — would be
  invisible to both scans above. There is no positive evidence of one; there was no positive
  evidence of the second either, until someone checked the two fields that did not appear.
- **Indirect calls.** A function reached only through a vtable or function pointer, receiving
  the record as an argument, is in neither the cluster nor the direct call graph. Same
  blindness `codescan --xrefs` documents.
- **The entry set is heuristic** — 17,900 entries from `call rel32` targets plus
  `int3`-delimited prologues.

**The check that would test closure, and it is the one that worked:** enumerate the tail
fields the zero-initialiser writes, and require every one to appear in the census. Two were
missing and that found the second encoding. **Re-run that check after any future addition to
the count**, because it is the only assertion here the artifact can refute.

### 14.4 Method, and three wrong totals before it was sound

The direct-encoding scan produced **155, then 258, then 274** before the method held. All
three agreed on **93 + 4 = 97**, which is why that sub-count is trustworthy even though the
totals were not — the classification was stable exactly where the global count was not.

The instability was **function extent**: decoding "until `ret`" runs past any function with a
tail call or an interior jump straight into its neighbour, double-counting. The fix is to
bound each decode by the **next known entry**.

The cluster is located **structurally, never by address**: find the 19 `imul r32, r/m32,
0x43C` sites by byte pattern, take the densest 8 KB window holding 18 of them. That yields
`[0x818000, 0x81A000)` on 38797 and `[0x812000, 0x814000)` on 2026-04-30, with outliers
`0x00823DB2` and `0x0081D9A2` — matching §1.1's independently derived outliers on both builds.
**A guessed range gave a confident zero:** an early run assumed the old build's cluster sat at
`0x816000` and reported 0 attribute sites, a wrong answer shaped exactly like a finding.

### 14.5 Reproduce

```
EXE="$(python -c "import sys; sys.path.insert(0,'toolkit'); import vaultpath;       print(vaultpath.vault_path('client','2026-07-29_221c13772c7a','Gw.exe'))")"
```

1. Find the 19 `imul` stride sites: search `.text` for imm32 `3c 04 00 00`, anchor-decode 2–3
   bytes back, keep decodings ending exactly on the immediate.
2. Cluster = densest 8 KB window over those sites.
3. Entries = `call rel32` targets + `cc cc` + prologue matches. Decode each
   `[entry, next_entry)` in `capstone` detail mode.
4. **Encoding 1:** memory operands, `0x400 <= disp < 0x43C`, non-zero base. Expect
   **93 / 4 / 177** (cluster / called-by-cluster / unrelated).
5. **Encoding 2:** over record-touching functions only — `add|sub|lea reg, imm` with imm in
   the tail range (**5**), and memory operands with `-0x460 < disp < -0x3F0` (**25**).
6. **The closure check:** every tail field the zero-initialiser at `0x00818EB0` writes must
   appear somewhere in 4 or 5. `+0x41C` and `+0x430` failing this is what exposed encoding 2.
