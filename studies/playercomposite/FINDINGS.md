<!-- studies/playercomposite/FINDINGS.md -->

> **Provenance of this document.** It is the synthesis of a five-reading /
> five-skeptic pass run 2026-08-19 (11 agents). Every claim carries the project
> label ([../character/FINDINGS.md](../character/FINDINGS.md)). **The
> load-bearing claim — §1.21's two-witness join — was re-run from scratch by the
> orchestrator before this file was written**, not transcribed: the composite
> table was re-parsed from the archive with a fresh script and the shells
> re-classified by an independent FFNA walk. That re-run reproduced residue 0,
> multiplicity `{1: 3803}`, cross-half type agreement 3803/3803, and
> **type 1 → 20/20 composited, type 2 → 20/20 composited, node counts matching
> element-for-element 20/20**. It also produced two corrections to the document
> below, recorded here rather than silently patched in:
>
> 1. **§1.22's type-2 sequence range "10–17" is wrong at one cell.** Shell
>    **18402** (group 0, profession 5, sex 1, n2C=101) carries **seq = 115**,
>    not 10–17. The other 19 are 10–17. The claim that type 2 is the
>    low-animation set survives; its stated range does not, and 18402 is now an
>    open question of its own.
> 2. **File 15018 — the type-1 shell for group 0, profession 1, sex 0 — is the
>    archivewrite arc's standing "unwritable" wall**
>    ([../archivewrite/FINDINGS.md](../archivewrite/FINDINGS.md): row 11196,
>    stored 1,029,564 B in a 1,029,632 B reservation, 68 B of slack,
>    decompressing to 1,514,855 B). Neither arc could see this alone. **The
>    hardest write target in the archive is a player shell**, which is both bad
>    news for authoring it in place and the reason its 68-byte slack matters.
>
> **A third correction, found by building §5's P1 rather than by reading.**
> §5's sabotage 1 — *"Parse `s_items` with 10 or 12 file slots instead of 11 →
> residue must become non-zero"* — **is wrong, and it is the kind of wrong this
> repo has a rule about.** Every record consumes `4 + 4*popcount` bytes, so
> section 2 is entirely dword-aligned and ANY dword-consuming parser lands on
> the exact final byte: measured residue 0 at 9, 10, 11, 12 and 13 slots alike.
> Residue only catches a truncation that is not a multiple of four. What
> actually pins the framing is that the file states the same count twice in
> disjoint halves: **`len(records)` must equal section 1's total id count**
> (3,803 == 3,803, against the rivals' 3,992 / 3,858 / 3,795 / 3,752), and
> **cross-half type agreement** must be total (3803/3803, against 3,212 /
> 2,547 / 2,927 / 3,075). `cpsdata.py` enforces the first as a refusal and
> `test_cpsdata.py` §2 now checks the vacuity itself so nobody re-derives it.
>
> Nothing here was checked against a running client — see §4.12.

---

# The Player Composite Path — what five readings and five attacks settled

**Tree:** `C:\gd\Rurik\.claude\worktrees\nifty-payne-7f6021`. **Binary:** pinned pristine build 38797, `C:\gd\Rurik\vault\client\2026-07-29_221c13772c7a\Gw.exe`. **Archive:** `C:\gd\Rurik\vault\dat_study\Gw.dat`. Read-only throughout; no client launched.

**Headline.** The brief's premise is dead and the gap is closed anyway. ConstComposite's 132-entry pointer tables hold no file ids at any depth — they are texture-atlas rectangles. The player's file ids come from **Gw.dat file id `0x33EA`**, a runtime-loaded composite table of 3,803 records. Parsing it and resolving skeleton types 1 and 2 produces **exactly the twenty shells the archive arc found independently, in the same sex pairing, 20/20** — plus a second, previously unnamed set of twenty low-animation variants on byte-identical node counts. The player-side analogue of `unitassembly.py` is now buildable end to end.

---

## 1. What is now known

Claims a skeptic killed are in §3, not here.

### The ConstComposite accessor (0x005AE200) — settled, and not the seam

1. **The accessor takes five arguments and ArenaNet names all five.** `ConstComposite:460 profession < CHAR_PROFESSIONS` (bound 0xB), `:461 sex < CHAR_APPEARANCE_SEXES` (2), `:462 blitId < MODEL_NUM_TEX_BLITIDS` (6), `:463 component < COMPOSITE_COMPONENTS` (8), `:464 count`. Index is `blitId + 6*sex + 12*profession` (lea chain 0x005AE291–0x005AE29A). **OBSERVED** — five readers agree; two recovered the strings by different routes (`asserts.py --file ConstComposite`, and raw `mov ecx, imm32` operands). Second witness in a different TU: `CpsTex:196/197` with `83 FF 06` at 0x0083213B and `83 FB 08` at 0x00832157.

2. **`studies/profession/WORKAROUNDS.md` lines 110 and 917 are wrong** — "`component + 6·axis2 + 12·profession`". The 6-valued fast axis is **blitId**; `component` is a fourth argument that indexes *inside* the pointee. **OBSERVED.** Fix that file.

3. **The two tables are one CSR structure, not two alternatives.** `B[idx]` (0x00BF4228) → a 9-dword non-decreasing prefix array starting at 0; `A[idx]` (0x00BF4018) → an array of 16-byte records. Return = `A[idx] + 16*P[component]`, `*count = P[c+1]-P[c]`. Both read with the same `edx` in one branch-free block (0x005AE29D … 0x005AE2B4). **OBSERVED**, four independent readings.

4. **The 16-byte records are texture-atlas RECTs `{left, top, right, bottom}`, unsigned.** 359/359 statically readable records satisfy `0≤l<r≤W, 0≤t<b≤H` against that blitId's own `s_dims`. Rivals coded explicitly and refuted: XYWH fails 269/359, LRTB fails 284/359. Second witness with no shared method: the caller at 0x008320E0–0x0083210F builds a bounding box with min into `+0/+4` and max into `+8/+0xC` — the canonical RECT union — and seeds it inverted from `s_dims`. Consumer compares with `jb`/`ja`, so unsigned. **OBSERVED.**

5. **No file ids anywhere in either table, at any depth.** Complete value set across all 359 records is `{0,128,256,384,448,512}`. Both dereference levels terminate. **The brief's "nobody has dereferenced those pointers — that is the seam" is refuted.** **OBSERVED.**

6. **Layout closes byte-exactly, three ways.** `s_dims` 0x00BF37F8 + 6*8 = 0x00BF3828 = first record array; 15 record arrays tile contiguously (each length taken from its *own* B row's `P[8]`, never from spacing) to 0x00BF4018 = table A's base; +132*4 = 0x00BF4228 = table B's base. On the .rdata side, 17 CSR arrays tile 0x00A3ABF0…0x00A3AE58 = `s_components`, +20*4 = 0x00A3AEA8 = `s_format`, +6*4 = 0x00A3AEC0 = the `ConstComposite.cpp` `__FILE__` string. **OBSERVED** (I re-read the tail myself: `0x00A3AEC0` = `P:\Code\Gw\Const\Tool\ConstComposite.cpp`).

7. **Only 44 of 132 cells carry static content**: blitIds 0 and 1. BlitIds 2–5 (88 slots) share exactly **two** pointers (0x00C0EFA0, 0x00C0EFB0) past .data's rawsize, with degenerate CSR `[0,0,0,0,0,0,0,0,1]` — one all-zero record owned by component 7. `s_dims` agrees: `[512,256],[512,512],[256,128],[0,0],[0,0],[0,0]` (verified by me). `s_format` = `[15,19,19,27,27,27]` (verified). **OBSERVED.**

8. **The sex axis is content-bearing only in blit1.** Payload byte-comparison: blit0 identical between sexes in 11/11 professions; blit1 differs in 10/11. Independently: sex-0/sex-1 pointers identical on 56 of 66 (profession, blitId) pairs = 44 (blit2-5) + 11 (blit0) + 1 (blit1). Two readings, arithmetically consistent. **OBSERVED.**

9. **Component 0 is sex-gated in blit1**: `prof0/sex0` CSR `[0,1,2,4,6,7,8,9,9]` (comp0 count 1) vs `prof0/sex1` `[0,0,1,4,6,7,8,9,9]` (comp0 count 0). Holds across the profession pairs. Unexplained. **OBSERVED.**

10. **Component names: NOT FOUND in the image.** Whole-image search (10,483,904 bytes) for `COMPOSITE_COMPONENT` → 1 hit (the assert expression itself), `COMPONENT_` → 0, `s_components` → 1 (its own expression). This is a real absence over the full range. **NOT FOUND** — but see claim 22, which names them from the other end.

### The appearance word

11. **A player's race/sex/profession are unpacked from a single packed 32-bit dword, not read off the agent.** `0x008153C0` is a 5-byte thunk to `0x0091D490`, a bitfield extractor over `s_appearanceSlot` at 0x00BC8AC8 (8 rows × 12 bytes), guarded by `CharData.cpp:178 slot < arrsize(s_appearanceSlot)`. **I read the table myself**, rows are `(self-index, shift, width)`:

    | slot | shift | width | bits | meaning |
    |---|---|---|---|---|
    | 6 | 0 | 1 | 0 | **sex** |
    | 5 | 1 | 4 | 1–4 | unnamed |
    | 7 | 5 | 5 | 5–9 | unnamed |
    | 1 | 10 | 5 | 10–14 | unnamed |
    | 0 | 15 | 5 | 15–19 | unnamed |
    | 3 | 20 | 4 | 20–23 | **profession** |
    | 2 | 24 | 6 | 24–29 | unnamed |
    | 4 | 30 | 2 | 30–31 | **race** |

    Every self-index equals its own position; the eight fields tile all 32 bits with no gap and no overlap. Field→destination: slot 4 → `this+0x3F0` (reduced `div 3`), slot 6 → `this+0x3F4` (`dec; and 1`), slot 3 → `this+0x3E8` (`div 0xB`). The widths are the discriminator — an 11-valued profession cannot come from a 1-bit field. **OBSERVED**, and it corroborates `studies/smsg/FINDINGS.md:830-837`'s `s_appearanceSlot` decode of wire `0x0059` (672 occurrences in the live corpus).

12. **Five of the eight appearance fields are unnamed** (widths 4, 5, 5, 5, 6). **NOT FOUND** — no naming attempted; the cheap next step is other callers of 0x008153C0.

13. **The CpsPlayer constructor brute-forces (race, sex, profession) until one has complete assets.** Loop 0x0082F6F0–0x0082F760: race `(r+1)%3`, then sex `(s-1)&1`, then profession `(p+1)%11`; exhaustion → `CpsPlayer:956 Failed to find any composite assets`; success logs `Substituting` through `Composite: %s [race %u, sex %u, profession %u]`. The three moduli independently witness `CHAR_APPEARANCE_RACES=3`, `CHAR_APPEARANCE_SEXES=2`, `CHAR_PROFESSIONS=11` without relying on the asserts. **OBSERVED.** §2 explains what this loop is *for*.

### CpsData — the actual file-id path

14. **`s_items` records are 48 bytes: header dword at +0x00, eleven file-id dwords at +0x04..+0x2C.** Three independent witnesses: the accessor's own stride (`lea eax,[esi+esi*2]; shl eax,4` at 0x00833477); the fileFlag→offset switch at 0x008336DD–0x00833778 mapping mask bits 0x001…0x400 to offsets 0x04…0x2C with default `CpsData:110 No valid case for switch variable 'fileFlag'`; and `CpsApi 0x0082D7D0`'s 11-iteration gather loop. **OBSERVED.**

15. **`s_fileFlags` (11 dwords at 0x00A978EC) bit 0 splits the slots: {0,5,10} geometry, the other eight textures.** I verified the values myself: `[0,1,1,1,1,0,1,1,1,1,0]`, and `0x00A978EC + 11*4 == 0x00A97918 ==` the `CpsData.cpp` `__FILE__` string (anchor closes). Empirically over **all 20,238 file references in all 3,803 records**: slots {0,5,10} → 6,703 `ffna` with zero exceptions; other slots → 13,535 `ATEX` with zero exceptions. **OBSERVED**, and it is the first-party derivation of GWToolbox's otherwise unexplained `slots_to_try[] = {10u, is_female ? 5u : 0u}` (**CORROBORATED**, `Resources.cpp:1370-1379` via `studies/character/FINDINGS.md`).

16. **Sex selects the slot half: file[0] (+0x04) when `sex==0`, file[5] (+0x18) otherwise** (`CpsPlayer 0x008315DB/0x008315E0`; equivalently `neg ecx; sbb ecx,ecx; and ecx,0x14` at 0x00831737). Slots {0,1,2,3,4} are one sex, {5,6,7,8,9} the other, slot 10 shared. **OBSERVED.** *That sex 0 is male is* **RECONSTRUCTION** *— see claim 21.*

17. **The composite table is Gw.dat file id `0x33EA` (13290).** `push 0x33EA; call 0x00833540` at 0x0082D420 — **I re-disassembled this myself and confirmed the literal and the call**; it is the loader's only caller, and it asserts `CpsData:622 Failed to open composite data file`. **OBSERVED.**

18. **The file's grammar parses with ZERO residue.** MFT row 71, 105,531 bytes. Section 1: `u8 nGroup` (=4), then `nGroup × 11 × 20` length-prefixed u16 id lists (11 and 20 from `CpsData:392/393`). Section 2: 3,803 records of `{u32 header; u32 fileId per set bit of header & 0x7FF}`; `type = header >> 22`. Cursor lands on 105,531 exactly. Four closures that could each have failed: arithmetic (`1 + 880*2 + 3803*2 = 9367` = measured section-1 end); partition (id multiplicity histogram `{1: 3803}` — every record referenced exactly once); cross-half type agreement (each id's section-1 type axis equals that record's own `hdr>>22`, **3803/3803**, disjoint halves of the file); and archive resolution (20,238/20,238 file refs live in `file_id_table(raw=True)`). **OBSERVED.**

19. **In memory the same table is `s_type[race] = {u16 count[11][20]; u16 offset[11][20]}` = 440 words.** The "unexplained factor of 2" in the 0x16 stride is the offset array: the second read at 0x008333DF computes `type + 20*(race*22 + 11 + prof)` off the *same* base `[0x010877E8]`. **OBSERVED** — and it matches the on-disk shape in claim 18 (length-prefixed lists = count + offset). Nothing is reserved; there is no pre-allocated twelfth profession.

20. **`s_components` (20 dwords at 0x00A3AE58) maps composite `type` → component, 8 = none.** I read it myself: **`[8,8,8,3,6,4,5,7,7,7,0,0,2,2,6,3,4,2,5,1]`**. Right-anchored: +20*4 = `s_format`'s base. A result of 8 is not a quiet sentinel — it takes a level-2 diagnostic log at 0x008302E4 and returns 0. **OBSERVED.**

### The join — new in this synthesis

21. **Resolving CpsData type 1 across `(group, profession)` yields EXACTLY the archive arc's twenty shells, in the same sex pairing, 20/20.** I ran it (`vault/research/equipment/cpsdata.json` → section 1 → `s_items[id].file[0]/file[5]`):

    | group | prof | file[0] (sex 0) | file[5] (sex 1) |
    |---|---|---|---|
    | 0 | 1 | 15018 | 16271 |
    | 0 | 2 | 16049 | 12818 |
    | 0 | 3 | 16202 | 16267 |
    | 0 | 4 | 16203 | 15719 |
    | 0 | 5 | 16377 | 16257 |
    | 0 | 6 | 15490 | 16258 |
    | 1 | 7 | 161426 | 161433 |
    | 1 | 8 | 161898 | 161906 |
    | 2 | 9 | 203708 | 203713 |
    | 2 | 10 | 204020 | 204032 |

    That is the archive arc's twenty low ids, and the `file[0]` column is exactly its A-side (skeleton X-span 34.2–37.2 u), the `file[5]` column exactly its B-side (29.1–29.9 u), 10/10 both ways. **All 40 resolve through `file_id_table(raw=True)` onto MFT rows in the archive's own 759-member composited-shell census, `has_fa0=False`, 40/40** (I ran the join: `type1 20/20`, `type2 20/20`). Two witnesses sharing no method — a client data file parsed from disk, and an FFNA chunk walk over the archive — agreeing on the same twenty files and the same pairing. **OBSERVED.** This closes the join the archive arc and its skeptic both left open, and it is what makes claim 16's sex-0 = larger-skeleton observation available. That sex 0 is *male* remains **RECONSTRUCTION**.

22. **Type 2 is a second, previously unnamed set of twenty shells on byte-identical skeletons.** `18393…18404`, `161418/161428`, `161907/161908`, `203714/203715`, `204010/204027`. All 20 are composited shells with no FA0. **Their `n2C` node counts match the type-1 set element-for-element, 20/20** (86, 99, 90, 99, 80, 92, 80, 90, 80, 101, 84, 105, 90, 105, 102, 105, 108, 109 …) while their FA1 sequence counts are **10–17 against type 1's 220–289**. Same skeleton, almost no animation. `CpsPlayer` picks between them on **bit 0 of the constructor's arg0** (`and eax,1; inc eax`, 0x008315B5). **OBSERVED**; what arg0 *is* is **NOT FOUND** (§4).

23. **The component semantics fall out of the type axis.** Combining `s_components` (claim 20, measured) with the base-piece array `0x00A96D9C = [3,4,5,6]` (I verified it, and `+16` lands exactly on the string `race < CHAR_APPEARANCE_RACES`) and the wire slot→type census (claim 26):

    | component | base type | armour type (wire slot) | reading |
    |---|---|---|---|
    | 0 | 10 / 11 (sex-keyed, "Missing face") | — | face |
    | 1 | — | 19 (Head, 104/275) | second head slot |
    | 2 | 12 / 13 (sex-keyed, "Missing hair") | 17 (Head, 171/275) | hair, replaced by headgear |
    | 3 | 3 | 15 (Body, 493/493) | chest |
    | 4 | 5 | 16 (Gloves, 472/477) | hands |
    | 5 | 6 | 18 (Legs, 487/487) | legs |
    | 6 | 4 | 14 (Boots, 483/488) | feet |
    | 7 | 9 | never worn | unknown; sole occupant of the degenerate blits 2–5 |

    Base and armour types land on the *same four* components for chest/hands/legs/feet — the override correspondence is exact and it is what makes the reading more than a guess. **RECONSTRUCTION** (the type→component and slot→type halves are OBSERVED; the body-part *names* are inference from that correspondence plus ArenaNet's own "Missing face"/"Missing hair" diagnostics).

24. **The group axis is race for base identity and something wider for armour.** I mapped section 1's coverage: group 0 carries base types 1–6, 9–13 only for professions 1–6; group 1 only for 7–8; group 2 only for 9–10; **group 3 carries armour types 14–19 for all ten professions and no base identity at all**. Every group carries armour types for every profession. Profession 0 has one cell (type 0, record 0, empty). **OBSERVED.** This is what the substitution loop (claim 13) exists for: a profession looked up in the wrong group has no base types and the sweep finds its home group.

### The wire

25. **Players are dressed by three server messages and none is 0x0056/0x0057.** `0x015E`/`0x0161` declare an item (item id, fileId, type, flags); `0x006E` writes all nine equip slots (agent_id + 9 dwords in the client's own message table); `0x006F` writes one. `0x006E/0x006F` carry **item ids**, not file ids. Measured over 98 keyed game connections with framing residual 0 on 98/98: 3,225 distinct (capture, connection, item id) worn triples, **3,225/3,225 declared earlier on the same connection**. Reproduced independently by two agents. **OBSERVED.** Our server can dress a player: it supplies both halves.

26. **Armour-slot items are composite and their fileId indexes the 3,803-record table; hand-slot items are not.** Per slot, with the client's own `0x7FFFFFFF` mask (0x008484B9): weapon n=23 and offhand n=14 are 0% composite, max masked fileId 175,552; Body/Boots/Legs/Gloves n≈645 each are 100% composite and 100% in range; Head n=449 is 84.2% composite and the *same* 84.2% in range. 588 distinct composite indices, 588/588 in `[0,3803)`. The strong check is cross-build slot↔type homogeneity (a 38797 archive against captures 7 of which are 38833): **Body 493/493 type 15, Legs 487/487 type 18**, Boots 483 type 14 + 5 type 18, Gloves 472 type 16 + 5 type 18, Head 171 type 17 + 104 type 19. **OBSERVED.**

27. **The three Cps classes share one base.** `CpsBase` object is 0x10C bytes; `CpsMonster` overrides 1 of 8 virtuals, `CpsPlayer` all 8; all three ctors call `0x0082E100`. Vtable extents anchored by their own `__FILE__` strings at +0x20 (`CpsBase.cpp`, `CpsMonster.cpp`) and by `s_scaleBase` (11 floats = CHAR_PROFESSIONS) after `CpsPlayer`'s. `CpsMonster`'s sized delete pushes `0x10C` explicitly at 0x0082F5A1. **OBSERVED**, and it corroborates `studies/pvpui`'s independently measured `operator new(0x10C)`.

28. **The live corpus is uniformly LIVE, no ours/live pooling.** `toolkit/origin.py` over every `.jsonl` under `vault/captures/live`: 85 capture-bearing files classify LIVE, 14 UNKNOWN are operator narration with no address fields, 0 classify OURS. **OBSERVED.** **13** of the 14 directories carry wire data (`20260817T175358` has none).

### Negative results (each is a result)

29. **Outbound c2s `0x0057`: NOT FOUND.** 0 occurrences in 5,855 c2s game messages across 98 keyed connections, and 0 in 207 auth c2s. The catalog *has* `GAME_CMSG 0x0057` (`[msg_header, dword, dword]`), so this is a measured zero, not a decode gap; residual 0 on 98/98 in both directions; the 43 c2s opcodes present bracket the gap (0x0051, 0x0060). The **send descriptor is real** (table 0x00BC8CB8) — do not write this up as "not a message". This CONFIRMS `studies/pvpui/FINDINGS.md §28.1`'s belief.

30. **`0x015F` and `0x0162`: NOT FOUND**, 0 occurrences each in 114,985 s2c messages spanning 218 opcodes, both present in the catalog with full field lists. Positively established in their place: **`0x015E` is what declares other players' items** — up to 107 distinct agents receive equipment in a single capture and every one of their item ids was declared by `0x015E`/`0x0161`.

31. **The translation unit of `0x00832080` (caller 1 of the accessor): NOT FOUND.** No assert anywhere in `0x00831C72..0x00832144`. Note the tool's own floor: `asserts.py` reads 19,758 sites against 20,131 independently counted call sites, short by ~370 image-wide, so "no assert here" is a floor. CpsTex is **RECONSTRUCTION** from call topology only.

---

## 2. The assembly order

From a player's identity to the set of archive files the client loads. **Cold points are marked ☒ with the address or id where the trail ends.**

**A. Identity.** A packed 32-bit appearance dword (wire `0x0059`) is unpacked through `s_appearanceSlot` (0x00BC8AC8) by `0x0091D490`: bit 0 → sex, bits 20–23 → profession, bits 30–31 → race. `CpsPlayer`'s ctor (0x0082F5C0) stores the dword at `this+0x10C` and the three fields at `+0x3F4/+0x3E8/+0x3F0`.
☒ Five of eight fields unnamed (widths 4, 5, 5, 5, 6) — presumably face/hair/skin/hair-colour/height selectors. Trail ends at the table itself; naming needs other callers of 0x008153C0.

**B. Availability sweep.** `0x00831540(arg0, race, sex, prof, 1)` is a **predicate** returning literal 0 or 1 (single caller 0x0082F6FF). On 0 the ctor sweeps race mod 3, then sex, then profession mod 11 (0x0082F70B–0x0082F754). This exists because a profession's base identity lives only in its home group (§1.24).
☒ `arg0` — its bit 0 selects skeleton type 1 vs type 2 (0x008315B5). Never identified. Stored at `this+0x3E4`; trace back through 0x0082DBB0/0x0082DBA0's callers.

**C. Base lookups.** Each is `CpsDataGetIds(type, race, prof)` → `ids[0]` → `s_items[id]` → `file[sex ? 5 : 0]`:

| what | type | → component | diagnostic on failure |
|---|---|---|---|
| shell / skeleton | `(arg0 & 1) + 1` → 1 or 2 | 8 = none | "Missing skeleton" |
| face | sex ? 10 : 11 | 0 | "Missing face" |
| hair | sex ? 12 : 13 | 2 | "Missing hair" |
| skin colour | `ConstColorSkin` 0x005A8EE0, `s_colorInfo[race][prof]` | — | "Missing skin color" |
| hair colour | `ConstColorHair` 0x005A8E40, same shape | — | "Missing hair color" |
| four base pieces | 3, 4, 5, 6 from static `0x00A96D9C` | 3, 6, 4, 5 | "Missing base composite" / "Missing base geometry" |
| unknown | 9 | 7 | — |

☒ `ConstColorSkin:710-719` and `ConstColorHair:956-965` are static `.rdata` and were never dumped. Cheap; do it.

**D. The table itself.** `s_type[race].count[prof][type]` (base `[0x010877E8]`, race bound `[0x010877F0]`, both .bss) → u16 id list → `s_items[id]` (base `[0x00BF9804]`, count `[0x00BF980C]`, stride 48). Both bases are runtime loads, not immediates — populated from **Gw.dat file `0x33EA`**, whose grammar is fully parsed (§1.18). For one player's base identity this yields a concrete manifest; e.g. group 0 / profession 1 needs 27 `(type, slot, file)` refs across both sexes — `type1 slot0 15018`, `type3 slot0 13279`, `type3 slot3 72506`, `type9 slot0 88850`, `type11 slot4 259753`, and so on.

**E. Equipment overrides.** `0x015E`/`0x0161` declares an item; `0x006E`/`0x006F` puts its **item id** in one of 9 equip slots; the client caches a 16-byte `ItemData` at `CpsBase+0x24+16*slot`. For an item with `ITEM_FLAG_COMPOSITE` (`test byte [edi+0xC],4`), `ItemData.fileId` is **an index into `s_items`**, not a Gw.dat file id (`CpsPlayer 0x008302A0` passes it unmodified to `0x00833420`). The record's `hdr>>22` is its composite type; `s_components[type]` names the component it **replaces**. An item does not add a component.
☒ **The wire item-type enum is not the composite type enum.** Observed wire types on `0x015E` (Body 7, Boots 4, Legs 19, Gloves 13, Head 16) do not line up with composite types 14–19. Whether the client derives one from the other or the composite type is purely a property of the record is unresolved — and it matters, because *our server picks the wire type*.

**F. Manifest.** `CpsApi 0x0082D7D0` walks each record's 11 slots and appends every non-zero id. The header's bit 17 (`0x20000`) skips a record; the top-10-bit gate (`>= 0x3800000`) only logs `Non-item composite %u requested for manifest` and falls through. `0x00833490` (`CpsData:479`, `:484 !(id & FILE_ID_RESERVED_BIT)` at 0x008334C5) is a **pure assert routine** — every exit is `xor eax,eax`, so it filters nothing.
~~☒ `FILE_ID_RESERVED_BIT` is unmeasured.~~ **MEASURED 2026-08-22: it is bit 31
(`0x80000000`)** — see §9.1. Authoring a player file id must keep bit 31 clear
(all 16,567 composite ids do).

**G. Build.** File ids become models through `MdlBuild 0x0077E210` (`fileName`) or `0x0077E2E0` (`fileName` + `skelFileName`). Geometry is slots {0,5,10} (`ffna`), textures are the other eight (`ATEX`).

**H. Texture composite.** `CpsTex` blits component textures into per-blitId atlases using `ConstComposite(profession, sex, blitId, component)` → a list of rects, scaled by `s_scaleR = [1,2]` for the low-res variant.
☒ Dye: `ItemData+0x05` and `+0x06` are handed to `0x0082DEF0` together with fileId and flags at 0x0082D1E0; that function was never followed, so which texture slots dye recolours is unread. Note `CpsTex:459 teamColorId || tabard` — a team-colour reading of those bytes is live.

---

## 3. What the skeptics killed or weakened

**Do not rebuild on any of these.**

1. **"ItemData is exactly the 0x015E/0x0161 wire prefix."** KILLED, and this one would break a server. The `0x015E` handler (0x00846FA0) pushes nine wire fields; the builder (0x00848450) stores **field 8 → ItemData+0x0C (flags)** and **field 9 → ItemData+0x08** — transposed — and drops wire fields 6 and 7 to `obj+0x48`/`obj+0x4A`, outside the struct. The empirical discriminator settles it without disassembly: reading the last dword as flags makes armour slots ~30% composite; reading field 8 makes them **100%**. Only `fileId` at +0x00 (`CpsBase:342`) and `flags` at +0x0C (`CpsPlayer:1006`) carry ArenaNet's own names; "dye tint"/"dye colours"/"materials" at +0x05/+0x06/+0x08 are **RECONSTRUCTION**, not OBSERVED. The struct's *extent* (16 bytes, `CpsBase+0x24`, stride 16, 9 slots) is solid.

2. **"The twenty are the PLAYER shells" (archive reading) vs "sixteen of twenty are wire-declared NPC shells" (its skeptic).** Both measurements stand; **the skeptic's verdict is now overturned by §1.21.** Recovering the tenth live capture per-connection genuinely adds shell 204020 and moves the closure 299→313 / remainder 460→446 — that correction holds and the archive reading's "it contributed nothing" is false. But `0x0056` declaration proves NPC *use*, not player *non-use*, and the CpsData resolution proves player use directly. **Believe: these are twenty human character shells that are simultaneously the player shells and NPC shells.** The archive's *evidence* did not support its naming; its conclusion happened to be right.

3. **"CpsPlayer reads race/sex/profession off the AGENT via ChCliApi:4729."** KILLED three ways: 0x008153C0 carries no assert at all (it is a thunk), the target is a `CharData.cpp` bitfield extractor, and the selector→field mapping was swapped (6 and 3 reversed). Under the reported mapping profession would come from a 1-bit field. The correct reading is §1.11, and it is a *better* result than the one it replaced.

4. **"0x00831540 is THE ASSEMBLY ORDER end to end."** WEAKENED to the point of being misleading. It has one caller and every exit returns literal 0 or 1; it discards every file id it touches. Anyone who breakpoints it expecting a file set gets a bool. The actual gathering is at the other 12 call sites of `0x008332E0` and `0x00833420`. The lookup *shape* it documents is correct.

5. **"`CpsData:484 !(id & FILE_ID_RESERVED_BIT)` is asserted at 0x00833420."** KILLED. That function ends at 0x00833485; its third assert cites `P:\Code\Base\rtl\Array.h` line 587 (`index < m_count`), an inlined template check. `:484` lives at 0x008334C5 inside the *neighbouring* function 0x00833490. The line number is real, the attribution was not — and it mattered because the citation's whole point was "this is the gate on authoring a player file id".

6. **"`s_components` = `[...,4,5,2,1]`."** KILLED — indices 17 and 18 were transposed. **I re-read the bytes: `[8,8,8,3,6,4,5,7,7,7,0,0,2,2,6,3,4,2,5,1]`.** Those two indices are the Head and Legs armour types.

7. **"Base appearance is type fixed to 1 or 2."** KILLED. The same function makes sex-keyed lookups at 11/10 and 13/12 forty instructions later (components 0 and 2). The type-1/2 lookup resolves *one* item and takes *one* geometry file; it does not populate eight components.

8. **"`0x015F` and `0x0162` are refuted by retail's own wire."** KILLED as a verdict, kept as a measurement. `0x0162`'s upstream claim is about **layout**, and the client's own message table corroborates it (opcode 354's field list is byte-identical to 353's); a zero count cannot refute a layout claim. `0x015F`'s upstream claim is a *restriction* ("used only for…"), which "never used" cannot refute. Note the internal inconsistency: identical evidence shape was correctly labelled NOT FOUND for `0x0057`. Use §1.30's narrower positive claim instead.

9. **"`s_type[profession][type].count`."** KILLED as a spelling. Both asserts take `arrsize` of `s_type[0].count` — so profession and type are the two dimensions of `count`, and `s_type`'s own first index is a third thing. Correct shape is `s_type[race].{count,offset}[prof][type]` (§1.19). Any design that plans to "walk s_type by profession" is planning against a structure the evidence does not show.

10. **"`test_bareimport.py` enforces the clientscan/mapdata seam."** KILLED. It walks `toolkit/authsrv/` only (6 checks) and never imports a mapdata module. Worse for the premise, `toolkit/mapdata/textwrite.py:54` and `toolkit/mapdata/tilerender.py:59` **already import clientscan**. The seam is a preference with no checker. If it is wanted as a rule, someone must write the check and decide what to do about those two files.

11. **"Components 2–5 are empty placeholders."** KILLED by the axis renaming — it is **blitIds** 2–5 that are dead; all 8 components are addressed by every live row. Consequence: an acceptance criterion over `(profession, sex, component)` would be nearly satisfiable and would measure nothing. The correct form is `(profession, sex, blitId ∈ {0,1})` = 44 of 132.

12. **Weak `could_have_failed`s to stop citing.** (a) "blocks close inside their own section" — .data's zero tail is 5.3 MB, almost nothing can fail it, and two blocks are *in* that tail. Cite the exact tiling onto `TABLE_A`'s base and onto `s_components` instead. (b) "zero landing on an empty record" — exactly 1 of 3,803 records is empty, chance expectation ≈0.15. Cite the slot↔type homogeneity. (c) the clustering shuffle control permuted bases *and* links with the same permutation, so the equality gate was shut for all 759 copies and the control could not fail; the gate-open version (permute bases only) does pass, median 25.9 u against a 0.17 u threshold — use that one. (d) "s_components[1]=s_components[2]=8 corroborates the shell reading" — three of twenty entries are 8, so a random draw hits with p=3/20. The load-bearing witness is the "Missing skeleton" string.

13. **Smaller corrections worth carrying.** The `.rdata` CSR block has **no trailing pad** — one array in the middle is 40 bytes (10 dwords `[0,1,2,3,5,6,7,7,7,7]`), and the last closes flush. The 88 uninitialised table-A slots are **2 distinct pointers shared by 88 slots**, not 88 runtime pointers. `s_fileFlags`' two identical halves `(0,1,1,1,1)` **cannot** be evidence for a male/female split — that rests solely on `CpsPlayer`'s `test esi,esi; jne`; what the array says is that slots {0,5,10} differ in kind from the other eight. The `colorCount < arrsize(colors)` string cited as ConstComposite's left anchor belongs to **`ConstItemColor:274`**. `CpsPlayer`'s ctor starts at **0x0082F5C0**, not 0x0082F5A0. **38,396** MFT rows carry exactly two stored ids plus **one** carrying three (38,397 carry *more than one*). `CHAR_APPEARANCE_RACES == 3` is a compile-time cap in CpsPlayer; CpsData bounds race against a **runtime** dword, and the data file declares **4 groups** (§1.24).

14. **Methodological trap, recorded because it produced a confident wrong answer.** 38,397 MFT rows store two file ids; keeping one per row with `setdefault` reported "1 of 74 wire shells composited, 2 monster-reachable" instead of 59 and 299. It was caught only because a *known* composited shell failed to appear in its own class. **I hit the same defect from the other side today**: `shells.jsonl`'s `stored` field holds a single int, and joining on it gave 0/20 — the correct join through `file_id_table(raw=True)` gives 40/40. Any join against that file must go through the id table, not through its `stored` column.

---

## 4. Honest unknowns, ranked by how much they block authoring a player model

1. **What is `arg0` of the resolver, whose bit 0 picks skeleton type 1 vs type 2?** Two complete twenty-shell sets exist (§1.22): fully animated (seq 220–289) and near-static (seq 10–17) on identical skeletons. Authoring against the wrong one produces a character that cannot animate. Trace `this+0x3E4` back through 0x0082DBB0/0x0082DBA0's callers. **Highest blocker — it is a one-bit decision with a total consequence.**
2. **The wire item-type ↔ composite-type mapping.** Our server picks the wire type; if it does not induce the right composite type, every equipped piece lands on the wrong component or none. §2 step E.
3. ~~**`FILE_ID_RESERVED_BIT` (CpsData:484, 0x008334C5).**~~ **MEASURED 2026-08-22, §9.1 — bit 31, and it is a real second id namespace.**
4. **Whether the twenty type-1 shells and their component sets round-trip through our own writers.** `modelwrite.py`/`skelwrite.py` are proven byte-identical on monster geometry (6846/6846, 14571/14571) but no player component file has ever been walked, let alone re-emitted.
5. **What group 3 is** — armour types 14–19 for all ten professions, no base identity, and unreachable from `CpsPlayer`'s `race < 3` (§1.24). Reserved, heroes, or a fourth armour campaign.
6. **What component 7 / base type 9 is.** Never worn in 3,225 wear events, present in every home-group profession cell, and the sole occupant of the degenerate blits 2–5 (which declare a real 256×128 atlas for blit 2 and 0×0 for blits 3–5).
7. **Component 0's sex asymmetry in blit1** (§1.9) — a face component with no female atlas rect needs explaining before the texture path is authored.
8. **The five unnamed appearance bitfields** (widths 4, 5, 5, 5, 6). Needed for anything beyond a default face.
9. **`ConstColorSkin`/`ConstColorHair` `s_colorInfo[race][prof]`** — static `.rdata`, never dumped, cheap.
10. **Dye** — `ItemData+0x05/+0x06` → `0x0082DEF0`, unfollowed; possibly team colour rather than dye.
11. **Composite-id stability across ArenaNet updates.** 588/588 held with a 38797 table against 38833 captures — one crossing, not a guarantee. Anything authored needs a per-row build stamp.
12. **Nothing here was checked against a running client.** Every claim is static or archive-side. The cheapest confirmation is a breakpoint on `0x00833420` during a character load, logging `(id, record)` pairs.

---

## 5. The rung

### What to build

**P1 — `toolkit/mapdata/cpsdata.py`** (promote `vault/research/equipment/cpsdata_parse.py`). Parses Gw.dat file `0x33EA` into `{groups[4][11][20] -> [id]}` and `records[3803] = {hdr, mask, type, files{slot: file_id}}`. Stdlib only, no `Gw.exe` dependency — it reads the archive, so it belongs in `mapdata`, not `clientscan`.

**P2 — `toolkit/clientscan/composite.py`.** The static half: `s_components` (0x00A3AE58), `s_format` (0x00A3AEA8), `s_dims` (0x00BF37F8), `s_fileFlags` (0x00A978EC), the base-piece array (0x00A96D9C), `s_appearanceSlot` (0x00BC8AC8), and the ConstComposite CSR/rect pair. Uses `consttable.py`'s *method* (anchor closure) but **not** its row schema — 17 variable-length arrays is not `count × stride`, and forcing it into one is the `s_worldData` defect. Stdlib only: every claim above was made with `bytes.find`/`struct.unpack_from`, so the byte patterns are fixed and it must keep working on a bare machine. Emits `vault/content/composite.toml` with `source = "client-table"`, `extractor = "toolkit/clientscan/composite.py"`, `build = 38797` **per row** (`attribtable.py --emit-content` is the precedent). **Not** tracked `content/*.toml` — these are the client's own layout, not authorable world facts, and `content.py`'s docstring draws that line itself. Note the trap: `source = "measured"` demands an extractor but *not* a build, which is the wrong row for a number read out of `Gw.exe`.

**P3 — `toolkit/mapdata/playerassembly.py`.** `(group, profession, sex, appearance, equipped composite ids)` → closed archive file set. Land it as **two commits**: first a behaviour-neutral refactor giving `unitassembly.Resolver.resolve` a `seeds` iterable of `(fid, role)` instead of building its queue from `unit.file_id + unit.model_ids`, then the new sibling. The walk (FA5/FAD terminals, the FA6 → ffna-type-8 → chunk-0x1 audio hop, FA8 links with the visited set, FAE, null-slot accounting, the U4 "judged once" ordering fix) is entirely reusable; only the seed and the wire plumbing are monster-specific.

### Acceptance criterion

**The two-witness closure, which I ran today and which the rung must institutionalise:**

> Resolving CpsData composite type 1 across all `(group, profession)` cells and taking `file[0]`/`file[5]` yields a set of shell file ids. Every one of them must resolve through `file_id_table(raw=True)` onto an MFT row that the archive's own FFNA walk classifies as **composited** (FA1 present, FA0 absent), and the resulting twenty must be exactly the twenty the archive's independent band scan names, with the same sex pairing. Then the same for type 2, whose `n2C` node counts must match type 1's **element-for-element**.

Measured today: **type 1 → 20/20 composited, type 2 → 20/20 composited, n2C match 20/20, `has_fa0=False` 40/40.** The two witnesses share no method — one parses a client data file off disk, the other walks chunk tables in the archive.

**Floor** — set from that green run, never guessed. P1: residue 0 on 105,531 bytes; section-1 arithmetic `1 + 880*2 + 3803*2 == 9367`; id multiplicity histogram `{1: 3803}`; cross-half type agreement 3803/3803; 20,238/20,238 file refs resolving; geometry/texture split 6,703 `ffna` / 13,535 `ATEX` with zero exceptions. P3: the two-witness closure above, plus `composited_violations()` empty and set **equality** (print both symmetric differences, never overlap).

**Sabotages that must go red:**

1. Parse `s_items` with 10 or 12 file slots instead of 11 → residue must become non-zero.
2. Shift the record type field `>>21` or `>>23` → cross-half type agreement must collapse from 3803/3803.
3. Read the ConstComposite CSR arrays at stride 8 dwords instead of 9 → several still parse as non-decreasing; the record-block tiling onto `TABLE_A`'s base must die on every row. This is `consttable.py`'s own measured dividing-stride blind spot (`s_eula` as 99×4 instead of 33×12) arriving here — build it first.
4. Swap `TABLE_A` and `TABLE_B` → both are 132 dwords 528 apart and a shape-blind reader accepts it; the rect predicates *and* the tiling must both fail.
5. Feed monster shell **116228** (the hatcher, client-confirmed) as a player shell → it is COMPOSITED and it walks, so a set-based `closed` check passes. The CpsData witness must reject it: 116228 is **absent from the composite table's 16,567 distinct file ids** (I checked — along with 116703, 116377, 116366). If it does not reject, the criterion measures nothing.
6. Read `ItemData.flags` from the last wire dword instead of field 8 → armour-slot composite rate must fall from 100% to ~30%.
7. Point at build **38833** (in the vault) → the extractor must close on 38833's own addresses **or refuse, naming the build**. Never silently return 38797's numbers. `buildpins.py`/`test_buildpins.py` are the precedent; `genericvalue.py` is what the 38833 update actually broke.

**Second gate:** no `PLAN.md §6.1` row is needed for any of the above — every value is our own reading of the owner's own binary and archive with this repo's own PE and FFNA walks (`modelfile.py`'s row is the precedent and states exactly this posture). A row becomes required the moment a **name** for a component, a profession id, or a field in the composite file comes from GWMB, `Py4GW_Reforged`, `gw-preservation` or a wiki page rather than from the client. `gw-preservation` and `Py4GW_Reforged` grant nothing — verification only. The GWToolbox `slots_to_try` corroboration in §1.15 is a citation, not a derivation.

**Provenance caveat on profession ids.** Group 0 = professions 1–6, group 1 = 7–8, group 2 = 9–10 is **OBSERVED**. Attaching profession *names* to ids 1–10 is **UPSTREAM** community knowledge and must be checked against something first-party (or cited with a `§6.1` row) before it lands in a document or a content row.

**Blast radius:** `test_unitassembly.py` (57 checks, floor 57 — its pinned 54/54 and 1,393-file count are the refactor's regression oracle; if either moves, the refactor is wrong and nothing else lands); `test_srclint.py` §7 (a new test without its `TESTS.md` line in the same commit goes red, both directions); `test_content.py` (floor 39 is the deliberately vault-*less* score — the risk is its vault-dependent section, the "every table has at least one row" check near line 134 and the repo-vs-live census at 487–488, once `vault/content/composite.toml` exists; read it before the first emit); `test_consttable.py` only if the ConstComposite blob is added to its 24-row corpus, which the recommendation is **not** to do. `test_bareimport.py` is **not** in the radius — see §3.10.

---

## 6. What a session should do first

Run the join, because it is the one thing that turns five separate readings into one mechanism and it costs one script and no client launch. Load `C:\gd\Rurik\vault\research\equipment\cpsdata.json` (or re-run `cpsdata_parse.py` against `vault/dat_study/Gw.dat` to reproduce it from scratch — 3,803 records, residue 0), resolve section 1 at composite types 1 and 2 across all `(group ∈ 0..3, profession ∈ 0..10)`, take `s_items[id].file[0]` and `file[5]`, and push every id through `archive.file_id_table(raw=True)` onto an MFT row — **not** through `shells.jsonl`'s single-valued `stored` column, which loses the second id and silently returns 0/40. You should get twenty type-1 shells that are exactly the archive band's twenty in the same sex pairing, twenty type-2 shells on element-for-element identical node counts with sequence counts of 10–17 instead of 220–289, and 40/40 classified composited with no FA0. That single result is the acceptance criterion of §5, it proves the CpsData reading and the archive reading are describing the same twenty files, and it converts "we cannot name the files the client would load for a given player appearance" into a manifest you can print — after which the first real decision is §4's number one: which of the two skeleton sets `arg0`'s bit 0 selects, and why.
---

## 7. The arg0 trace — bit 0 is answered, and the answer is "author against type 1" (2026-08-22)

§4's highest blocker is closed by walking the constructor's argument back to
its six call sites. The chain: `this+0x3E4` is written once in `CpsPlayer`'s
ctor (`mov [edi+0x3E4], ebx` at 0x0082F66A, ebx = the FIRST stack argument),
the ctor has ONE caller — the factory 0x0082DB10, which allocates 0x3F8 bytes,
forwards its own six arguments verbatim and registers the object under the
`'comp'` handle tag — and the factory has exactly SIX direct call sites
(`codescan --xrefs`; no data word holds either address, so a vtable route is
excluded; computed calls remain the standing caveat). The availability
predicate 0x00831540 consumes ONLY bit 0 (`and eax,1; inc eax` → CpsData type
1 or 2, after its three bound asserts CpsPlayer:405–407). **OBSERVED**, per
site:

| call site | region / TU evidence | arg0 | bit 0 → type |
|---|---|---|---|
| 0x007F4E5D | agent view (Av) | literal 0 | 0 → **1** |
| 0x007FBEA9 | agent view, same fn | 0 or 2 (a caller bool → bit 1) | 0 → **1** |
| 0x007FC055 | same fn, other branch | 0 or 2 | 0 → **1** |
| 0x00800A37 | agent-view manager | literal 2 | 0 → **1** |
| 0x00875A21 | UiChModel.cpp (character select/creation; UiChModel/UiChInfo asserts bracket it) | literal **3** | 1 → **2** |
| 0x004EE3FD | GmDoll.cpp (GmDoll:1138 in-function) | **6 or 7** — 6 + FrameTestStyles(frame, style) on the doll's own frame | style-dependent |

**The reading: every in-world agent gets composite type 1 — the fully
animated twenty (FA1 sequences 220–289). Bit 0 = 1, selecting the near-static
type-2 set (sequences 10–17), is set ONLY by the character-model UI views —
the char-select model and (style-dependent) the paperdoll — which need idle
poses, not combat animation.** So the authoring question is closed: **author
a playable character against TYPE 1**; type 2 is the menu-preview skeleton
set. RECONSTRUCTION on the *purpose* ("menu preview"), OBSERVED on every
value and consumer above.

**The other bits, honestly:** bit 2 (value 4) gates a CpsPlayer VIRTUAL
(0x00831810, in the vtable at 0x00A96B74): bit set → the return of an MdlApi
call (0x777FF0, MdlApi:85's TU) on the argument; clear → literal 1. Only
GmDoll's 6/7 ever sets it — a "poll the model" behaviour for the UI doll,
unconditionally-true for in-world composites. **Bit 1** (value 2) is carried
by five of six sites (a bool at the agent-view sites, constant at the UI
ones) and its consumer is **NOT FOUND** — the displacement scan sees only
five `+0x3E4` accesses image-wide and none tests bit 1, so it is read through
a register copy or a biased pointer if it is read at all.

## 8. The rung LANDED (2026-08-22)

**P1 was already done by the archive-write session** — `toolkit/mapdata/cpsdata.py`
(the `CompositeTable`/`Record` decoder, `test_cpsdata.py`), landed `28cab35`.
This arc built the two rungs on top of it, plus the one-bit answer §7 above:

**P2 — `toolkit/clientscan/composite.py`.** The client's static tables, read
out of `Gw.exe` and anchor-located (from ArenaNet's own `__FILE__` strings and
the accessor's own operands), closure-verified (359 live rects LTRB-shut, the
88 degenerate zero-records of blits 2–5 counted apart, the appearance bitfield
tiling all 32 bits, s_components on the study's exact bytes), and REFUSING on
any unknown build naming which anchor failed. Emits `vault/content/composite.toml`
(106 rows, `source = "client-table"`, extractor + build per row). One PE detail
it had to get right: the `.data` virtual zero-fill TAIL is modelled — the 88
degenerate records live in it, and a reader that slices past a section's raw
size returns the next section's bytes, which is how those 88 first parsed as
garbage.

**P3 — `toolkit/mapdata/playerassembly.py`**, on a behaviour-neutral `seeds`
split of `unitassembly.Resolver` (committed alone, `test_unitassembly` 57/57
untouched). It takes `cpsdata.CompositeTable`'s record picks and drives the
monster closure walk from a player manifest: **all 40 resolvable identities
CLOSE** — group 0 / prof 1 / sex 0 resolves shell **15018, the archivewrite
arc's hardest wall, in a 173-file closure** — while the 136 foreign-group
cells refuse per the home-group rule. `test_playerassembly.py` owns what sits
ON the table (the manifest's record picks, the disjoint sex/slot split, the
40/40 closure, the exe-side cross-witness that s_fileFlags' clear bits equal
the assembly's geometry slots from a disjoint source); the two-witness shell
closure itself stays `test_cpsdata.py`'s, not re-litigated. One capability the
split added beyond the refactor: a texture/fad-role seed is a TERMINAL (checked
and read, never walked as a model), and a sound/audio seed is refused outright
— the audio closure hangs off a model's FA6.

**One correction the test's first run forced, recorded because the summary it
refutes is this document's own.** §1.22 says the type-2 set's FA1 sequence
counts are "10–17 against type 1's 220–289" — the counts were elided with an
ellipsis, and the universal reading is FALSE: nineteen of the twenty type-2
shells sit in 10..17 and **the (group 0, profession 5) sex-1 shell carries
115**. Still under half its type-1 sibling's 220, so the ordering ("every
type-2 has fewer sequences than its type-1 twin", 20/20) and the reading
("near-static preview set") both stand — but the RANGE claim needed the
outlier named, and `test_playerassembly` §4 now pins it by identity so a
second outlier, or this one moving, goes red. OBSERVED.

## 9.1 FILE_ID_RESERVED_BIT is bit 31, and it is a real second id namespace (2026-08-22)

§4.3's blocker measured. The two asserts `!(id & FILE_ID_RESERVED_BIT)` —
**CpsData:468** (`0x008332ac`) and **CpsData:484** (`0x008334c5`) — each feed
the tested value through the identical idiom `shr eax, 0x1f; not eax; test
al, 1; jne ok`, so the guarded bit is `id >> 31`: **`FILE_ID_RESERVED_BIT =
0x80000000` (bit 31)**. Both routines are pure asserts (every exit is `xor
eax,eax; ret`, as the §2 step F correction and skeptic §5 already established),
so the bit gates AUTHORING/debug rather than filtering anything at runtime.

**It is not hypothetical — the bit tags a distinct id namespace.** The study
archive's raw `file_id_table` (171,023 ids) carries **25 ids with bit 31 set**
(0x8001B97D … 0x8005E728), each resolving to a real MFT row, and the rows they
name are **disjoint from every ordinary (bit-31-clear) id's row** — no reserved
id is an alias of an ordinary one, and a few rows (7982, 20118, 44714…) are
reachable under *two* different reserved ids. So the ordinary file id and the
reserved id are two separate reference spaces, and the client's asserts guard
the ordinary-id code paths against being handed one of the reserved kind.

**For authoring:** every one of the 16,567 composite file ids clears bit 31
(max 375,810), so assembling a player from the composite table never trips the
assert. A mint that ever set bit 31 would, and `playerassembly.manifest`
refuses such a file id before it becomes a seed (`FILE_ID_RESERVED_BIT`,
pinned by `test_playerassembly` §8). What the reserved namespace is FOR — a
computed/virtual id class, a second archive — is not settled here; what is
settled is the bit, that it is real, and that authored ids must avoid it.
