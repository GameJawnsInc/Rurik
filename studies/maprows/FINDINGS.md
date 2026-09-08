# Naming the archive's 349 map rows

Build 38797, pinned pristine `vault/client/2026-07-29_221c13772c7a/Gw.exe`, read
as a file. `vault/dat_study/Gw.dat` read read-only, and `C:\gw\Gw.dat` read
read-only once (§8). Six live captures from ArenaNet's own service replayed
offline. The client was never launched, no debugger attached, no packet sent.

This arc was opened to find the join `s_missionClientData` index → map file id,
on the assumption that the client must have one. **It does not, and that is now
proven rather than assumed.** What the arc found instead is a different join
that does not go through a file id at all, and it names map rows.

## Labels

Drawn from [studies/character/FINDINGS.md](../character/FINDINGS.md), with
`MEASURED` kept from [studies/mapdata/FORMAT.md](../mapdata/FORMAT.md) because
half of this document is byte-level reads rather than client behaviour.

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes on this machine. Address or count given so it can be re-read. |
| **OBSERVED** | We saw it happen — here, ArenaNet's own traffic in our own captures. |
| **SOURCED** | The client's own compiled assert text says it. ArenaNet's words, not a reconstruction. |
| **CORROBORATED** | Genuinely independent lineages agree; each use names which. |
| **INFERRED** | Our reading of the above. |
| **REFUTED** | We predicted it, tested it, and the artifact said no. |
| **NOT FOUND** | We looked, and record where. |

Everything here is reproducible with `toolkit/clientscan/maprows.py`.

---

## 1. The answer in one page

- **The map geometry file id is not in the client's static data.** REFUTED, twice,
  by methods sharing nothing: an exhaustive byte sweep with a null control (§2a),
  and a backwards walk of every producer of the file-id argument (§2b). The
  earlier conclusion in `mapdata/FORMAT.md` and `areatable/FINDINGS.md` was right;
  it is now evidence rather than an absence of evidence.
- **The table is called `s_missionClientData`**, not `AreaInfo`. SOURCED — the
  client's own assert. Its accessor at `0x005A8580` measures both the count and
  the stride out of the binary: `cmp esi, 0x378` (888) and `imul eax, esi, 0x7c`
  (124). Both numbers were previously structural inferences of ours; they are now
  the client's own. (§3)
- **The join was never needed.** `s_missionClientData` carries, at `+0x48` and
  `+0x58`, the map's **footprint on its continent** — a rect in terrain cells.
  The map file carries its own rect in world units. At the known pitch of 96.0,
  **the footprint's size equals the map's terrain dims in 319 of 319 cases.**
  Shift every footprint one cell and it is 0 of 319. (§5)
- **That names map rows.** 53 of 349 rows have dims unique in the archive, so
  their names are forced; 20 of those resolve to exactly one name. Against
  gw-preservation's independently hand-typed table the join scores **350 of 353
  (99.2%) versus a 5.4% shuffle control**, and on the 20 forced rows **15 agree,
  0 differ, and 5 are named that no upstream names.** (§6, §7)
- **ArenaNet's own server does the join, and we watched it.** GAME_SMSG `0x0195`
  field 1 is the map file id and `0x0199` field 2 is the map id. In 9 of 9 live
  connections, three *different* named zones — Ascalon City, Lakeside County,
  Ashford Abbey — loaded the one file `0x1B97D`. **Row → name is one-to-many,
  measured, not assumed.** (§4)
- **Bit 31 is a RENAME, not a spelling — and the first version of §8 got this
  wrong and is retracted there.** The client never masks: the index stores the id
  verbatim (`0x0047C027`) and the lookup is an exact 32-bit compare
  (`0x0047AA20`). `FcArchive` renames a row to `id | 0x80000000` when it has
  requested a replacement, and `DnArchive` re-links the plain id when the
  replacement is installed. ArenaNet always sends the plain id; our `dat_study`
  simply cannot answer it, while the archive the live client actually read binds
  `0x1B97D` to a different row entirely. **A `file_id` is archive STATE, not a
  property of the map.** (§8)

---

## 2. There is no static map-id → file-id table. REFUTED two ways.

### 2a. The byte sweep, with a null control

MEASURED. Every dword at **every alignment in all five sections** of the
10,483,904-byte image was decoded through the client's own file-reference
encoding — 7,948,289 plausible packed dwords, 3,026,172 distinct decoded ids —
and tested against the 702 file ids that name one of the 349 map-flagged rows.

```
OBSERVED   21 dwords decode to a map-head id, hitting 6 distinct ids
NULL       500 random equal-size non-map id sets from the same archive
             total hits   mean 21.4   5-95pct 10..37     p = 0.354
             distinct ids mean 16.0   5-95pct 10..22     p = 1.000
```

**The map ids are at chance on volume and *below* chance on distinctness.** A
real 349-entry table would put ~349 distinct map ids in the image; there are 6,
scattered across `.text` and `.rdata` with no stride. An independent sweep by a
second worker, scoring 216 in-range map ids against a size-matched control from
the same numeric range, reached the same shape from the other side: 28 of 216
map ids present against 38 of 216 controls.

A separate census covered **all 31 dword columns** of the 888-record table, in
both the raw and packed readings. No column resolves to a map-flagged row. This
extends `areatable/FINDINGS.md` §3, which had tested `+0x68` alone.

*What this does not cover, stated because a negative is only as good as its
scope*: ids stored at a width other than 32 bits, as a base-plus-delta table, as
text, inside compressed data, or **computed rather than stored**. §2b closes
that last one from the other side.

A third worker reproduced the column half independently and **strengthened** it:
no dword at **any** of the 124 record offsets — not merely the one upstream
names — resolves to a map-flagged row, read either raw or through
`textrec.combine()`. Best column: 1 of 888, at unaligned offset 59.

### 2b. Every producer of the file id, walked backwards

MEASURED. The file id reaching the archive layer has exactly **two** sources,
and both are the network:

| source | where the id sits |
|---|---|
| GAME_SMSG **`0x0195`**, handler `0x0084ED00` (38797; `0x0084EDC0` in 38833) | `msg+0x04` — schema field 1, `dword` |
| GAME_SMSG **`0x01A4`**, handler `0x0084F170` | `msg+0x1C` — schema field 7 |
| the download/bloat pipeline | `DnBloat.cpp` ← `FcArchive.cpp`, id arrives with the download request |

**The whole of `0x0195` is now decoded** — all seven fields, 30 loads, both builds:
[studies/mapload/FINDINGS.md](../mapload/FINDINGS.md). Two results bear directly on this
document. Field 1 is **one-to-many over maps** (14 map ids resolve onto 7 files; 165811
carries both the Great Temple of Balthazar and the Isle of the Nameless, 2,205–2,734 units
apart on one connected mesh), so it names a **terrain file**, not a map — which is the
missing half of §6's mapping. And in 38833 the handler sits at `0x0084EDC0` calling
`0x853C60`, a clean **+0xC0 shift** from the addresses below, so those are build-38797
addresses rather than wrong ones.

The chain is `0x0084ED00` → `0x00853BA0` → UI message `0x10000098` →
`0x00707BB0` → `0x00707650` → `0x00707330` → `0x00713630`, and it was walked in
both directions: `0x00853BA0` has **2 direct references and 0 data words**, and
`0x00707BB0` has **1**, so there is no vtable route into either. The client's own
words at the far end, each cited as the evidence for one claim:

```
0x00707bc3  Map:2045      filename
0x0071368b  MapData:4552  filename
0x007d8b1f  FcArchive:1128  (int) fileId > 0
```

The one handler that *does* read `s_missionClientData` — GAME_SMSG `0x0191` at
`0x0084EB30` — takes its index off the wire too and uses record `+0x0C` to pick
a game type. It produces no file id.

### 2c. The map file does not identify its area either

MEASURED, and this closes the other direction. A census of all 698 map payloads
— 16,094 chunks over 52 distinct ids, independently reproducing `mapchunks.py`'s
own chunk total — was swept for a field that could be an area id: **every chunk
id × every offset × u8/u16/u32 × both byte orders**, over each chunk's first 192
bytes, the whole payload of every chunk under 4 KB, and every chunk's last 64
bytes. Requiring a value present in all maps, inside `0..887`, and distinct: the
best field reaches **232 of 349 distinct** and is a count, not an id.

**The positive control is what makes that a result.** Drop the range test and the
same sweep immediately finds fields distinct in **349 of 349** — and every one
lies inside the 16-byte random v4 content UUID in chunk `0x2000000C`, which
`mapbuild.py` already documents as never read by the client. The sweep can fire;
what it fires on is a UUID.

Two further hypotheses, both NOT FOUND with their own decoys: the map carrying
its area's **name string id** (best 9 real against 5 decoy once the two
byte-identical constant chunks are excluded — base rate), and the map carrying
**its own file id** (22 of 698 files hit, but those same files contain 6–42
*foreign* map ids each, averaging 21.6 occurrences, so the self-hits are
coincidence).

**The dependency join is empty, and measurably so.** Pooling 268,580 references
over 4,504 dependency lists gives 21,998 distinct file ids; the two
`s_missionClientData` texture fields give 319. The intersection is **exactly
0**, so the relation is `0 of 349` under `file_id`, `thumbnail_id`, and both
pooled. The positive control — the same code with each area assigned a texture
drawn from the dependency pool — returns 15 / 329 / 5, so the join works and the
relation is genuinely absent. Also **0 of 21,998 dependency ids name a map head
or partner**, so there is no map-to-map reference graph there either.

Two census facts worth keeping for other arcs: head and partner dependency lists
are **identical list-for-list in 349 of 349 pairs**; the Stripped `Sight` chunk
is **9 bytes in 349 of 349** where its Bloated partner runs to 478 KB, i.e. a
stub; and `0x20000016` (PathEngine) exists in **exactly one map of 349**.

*Not swept*: the interiors (bytes 192…len−64) of the ten bulk chunks over 4 KB.

---

## 3. The table is `s_missionClientData`, and the client measures itself

SOURCED and MEASURED. The accessor at `0x005A8580`:

```
005A8584  mov  esi, [ebp+8]        ; map id
005A8587  cmp  esi, 0x378          ; 888
005A858F  push 0xbbd               ; line 3005
005A8594  mov  edx, <"P:\Code\Gw\Const\ConstMission.cpp">
005A8599  mov  ecx, <"index < arrsize(s_missionClientData)">
005A85A3  imul eax, esi, 0x7c      ; 124
005A85A7  add  eax, 0x96de38       ; the base
```

`codescan.py --xrefs 0x0096DE38` finds **exactly one** word holding that VA, at
every alignment across all sections: this instruction. **888 and 124 stop being
our structural inference and become ArenaNet's own constants** — and 888 is
independently corroborated on the wire, where `0x0197` field 2 carries 888 as the
"no map" sentinel (§4).

Across the accessor's **106 call sites**, only `+0x68` and `+0x14` ever reach the
file-id encoder, and both are asset ids: of `+0x68`'s 72 distinct values, 135
decompress to `ATEX`, 8 to MPEG audio, and exactly **one** is map-flagged — a
guild hall shared by three rows. Not a lookup.

**A formula we had on loan is now the client's own.** `textrec.py`'s `combine()`
was inverted from GWCA's accessors — UPSTREAM. The client's encoder at
`0x004702B0` computes `(id-1) divmod 0xFF00`, adds `0x100` to each half, and
writes them as a two-character wide filename; the decoder at `0x00470300` is its
exact inverse and `File.cpp:850` names it in an assert:

```
0x0047124b  File:850  !ExtractArchiveFileId(path, nullptr)
```

That is precisely `combine()`. **CORROBORATED** — upstream's accessors and
ArenaNet's compiled arithmetic, which share no lineage. It also explains the
failure mode: an id of 0, or one whose halves fall below `0x100`, is refused
before the archive is touched.

---

## 4. ArenaNet's own join, OBSERVED on the wire

Six live captures, all connections, decoded whole through `tape.decode_all`.
**GAME_SMSG `0x0195` field 1 is the map file id**: 9 of 9 instance loads carry
`0x1B97D`.

**GAME_SMSG `0x0199` field 2 is the instance's map id.** It holds exactly one
value per connection in 9 of 9, and those values resolve through
`s_missionClientData` to:

| map id | name | file id |
|---|---|---|
| 146 | Lakeside County | `0x1B97D` |
| 148 | Ascalon City | `0x1B97D` |
| 164 | Ashford Abbey | `0x1B97D` |

**A ROW IS DELIBERATELY NOT IN THAT TABLE, and an earlier version of it named
row 7982 in all three cells.** That was wrong, and it was wrong in an instructive
way: `archive.py`'s `file_id_table()` registers a bit-31 id under BOTH its raw
and masked forms, which is our convenience and **not what the client does** —
the client compares exactly (§8). So "`0x1B97D` → row 7982" was an artifact of
our own reader. In the archive the live client was actually reading, `0x1B97D`
binds to **row 177262**. The file id is the durable fact here; the row is a
property of one copy of the archive.

**Row → name is one-to-many, and this is the measurement that proves it.**
`FORMAT.md` recorded 101 file ids claimed by more than one map id and left
"real, or upstream copy-paste?" open; for this file it is real, on ArenaNet's own
traffic. It also agrees with that document's independent geometric result, that
the Pre Ascalon City *and* Ashford Abbey spawns both land in row 7982's
trapezoids — two methods, one answer.

**A control was run and it does not discriminate; recorded rather than dropped.**
If `0x0199` field 2 is the map id, sessions sharing a value should share a spawn
point. Ashford Abbey's two sessions agree to 59.6 units, but Lakeside County's
four sessions span **20,476 units** and Lakeside County sits **675 units** from
an Ashford Abbey spawn. That is expected — you arrive at the portal you entered
by — which is exactly why the control is worthless here and must not be quoted as
support. The reading rests on the one-value-per-connection property, the opcode's
position in the instance-load family, and the independent trapezoid result above.

---

## 5. The footprint join — MEASURED

`s_missionClientData` carries two rects, at `+0x48..+0x54` and `+0x58..+0x64`,
unnamed in every upstream mirror. 632 of 888 rows carry at least one; they are
equal on 716 rows and differ on 172, and both are kept because nothing says which
the client prefers. They are the map's **footprint on its continent, in terrain
cells**:

```
footprint_width  == (rect.x1 - rect.x0) / 96      rect from chunk 0x2000000C
footprint_height == (rect.y1 - rect.y0) / 96
```

96.0 is not fitted here — it is the cell pitch `terrain.py` measured as
`rect/dims` exactly and `stripbuild.py` derives its rect from. The offset between
the two rects is the map's placement on its continent and differs per map, so
**only the size is shared. That is the whole join and also its whole limit.**

Two worked anchors, each consistent on all four values:

| row | terrain rect | in cells | footprint | implied offset |
|---|---|---|---|---|
| 7982 (Pre-Searing) | −18432, −24576, 21504, 24576 | −192, −256, 224, 256 | 768, 512, 1184, 1024 | (960, 768) |
| 22371 (Kamadan) | −18432, −21504, 21504, 21504 | −192, −224, 224, 224 | 2080, 3136, 2496, 3584 | (2272, 3360) |

Corpus result and its controls, over 319 distinct `(continent, rect)` footprints
against 349 map rows carrying 104 distinct dims:

```
footprint size exists in the archive        319 of 319   (100.0%)
CONTROL  every footprint +1 cell in x         0 of 319   (0.0%)
CONTROL  +1 cell in x and y                   0 of 319   (0.0%)
CONTROL  random sizes from the observed range  40.9% mean, 50.0% at p95
map rows whose extent is NOT integral in cells:  0 of 349
```

A relation that is exact on the whole corpus, collapses to zero under a one-cell
perturbation, and beats a 41% null is a measurement, not a fit.

---

## 6. The mapping, and how far it actually gets

`toolkit/clientscan/maprows.py`. Size is a two-number key and the archive has no
continent field, so **maps sharing a size cannot be told apart**: 110 footprints
are 512×512, and so are 60 map rows. The tool therefore reports a candidate set
per row and marks a row `exact` only when its dims are unique in the archive.

**A row → one name was never available, and the arithmetic says so before any
measurement does.** There are 888 named areas and 349 geometry files, so if every
area had a file at least **539 areas must share one**. §4 shows three sharing
`0x1B97D` on ArenaNet's own wire. Any tool promising one name per row would be
wrong by construction, which is why this one returns sets.

| | rows |
|---|---|
| dims unique in the archive → name forced | **53** of 349 |
| …of which resolve to exactly one name | **20** |
| …to 2–5 names (legitimate: zones share a file) | 19 |
| …to no name (no footprint of that size) | 14 |
| at least one candidate name | 319 of 349 |
| no candidate at all | 30 |

The 30 with no candidate are maps absent from any world map — the tool says so
rather than inventing a name. Candidate-set size over the 353 map ids upstream
also names: **median 5, mean 18.8**.

This is an honest partial answer. It does not name 349 rows and the tool does not
pretend to; what it does is replace "249 named only by an unlicensed upstream and
100 named by nobody" with a mapping derived entirely from artifacts we may use,
carrying its own uncertainty per row.

---

## 7. Verified against upstream — the permitted use

`gw-preservation/*` grants nothing, so under CLAUDE.md's second gate it may only
**verify a value we derived ourselves**. Nothing from it is copied into the
mapping or the repo; what follows is a pass rate.

Its `instance_definitions.go` hand-types 397 map ids with a name and a
`MapFileId`; all 397 resolve to a map-flagged row. 353 of those also have a
candidate set from our join, which never saw the file.

```
upstream's row inside our candidate set   350 of 353   (99.2%)
CONTROL, a random row per map id          mean 5.4%, p95 7.4%, max 9.9%
```

On the 20 rows we name outright: **15 agree with upstream, 0 differ, and 5 are
rows upstream does not name at all.**

The three disagreements are worth more than the rate:

- **map 256** — upstream says *Gates of Kryta*; the client says *Sunjiang
  District*. This is a **known upstream error**, already established
  independently in `areatable/FINDINGS.md` §6 and explaining a duplicate file-id
  claim in `FORMAT.md`. Our join agreeing with the client here is corroboration,
  not a miss.
- **maps 461 and 463, The Underworld** — both sides agree on the *name*; the row
  is not admitted by the footprint size. NOT FOUND: why. The Underworld is
  instanced and appears seven times in upstream's table, so its footprint
  plausibly describes something other than its geometry file. Recorded as open.

---

## 8. Bit 31 is a RENAME, and my own correction here was wrong

**RETRACTED 2026-08-13, same day it was written.** This section first claimed
"ArenaNet sends the MASKED file id" and concluded that the client must normalise
the high bit. **The client does not mask, anywhere.** The reasoning was a
plausible inference from two archives, and it was wrong because it never asked
which archive the live client was actually reading. Kept rather than deleted,
because the shape of the mistake is the useful part: three measured facts, one
unasked question, and a confident conclusion.

### What the code does — MEASURED

The index built from MFT row 2 stores the id **verbatim**, and the lookup is an
**exact 32-bit equality test**:

```
0047C025  mov  eax, [edi]        ; pair.fileId
0047C027  mov  [esi+0xc], eax    ; node->fileId = pair.fileId   -- bit 31 KEPT
...
0047AA14  mov  eax, [eax+edi*4]  ; bucket chain head
0047AA20  cmp  [eax+0xc], esi    ; curr->fileId == fileId       -- EXACT, no mask
0047AA2C  xor  eax, eax          ; MISS: return 0, no retry
```

Bucket selection does `and ecx, m_hashMask`, so `0x1B97D` and `0x8001B97D` land
in the **same chain** — only the exact compare separates them. Neither open-by-id
wrapper retries. Searched and NOT FOUND: `and reg, 0x7FFFFFFF` anywhere in
`0x00460000..0x004A0000` (0 sites), `0x7FFFFFFF` at all in Map/MapData
`0x00700000..0x00720000` (0), `bt`/`bts`/`btr`/`btc` on bit 31 image-wide (0),
and the shift-pair spelling of a bit-31 clear image-wide (0) — every constant
anchored at every alignment on capstone's own encoding record.

### What bit 31 means — SOURCED and MEASURED

It is a **rename performed by the file client**, not a spelling. `0x007D7B70` is
twelve instructions: bind `fileId | 0x80000000` to the row, then delete the plain
name. Its callers sit in `FcArchive`'s request path, in the branch that clears a
stale file out of the archive **before asking for a replacement**. `0x004766F0`,
reached only from `DnArchive`, is the exact inverse: it re-links the plain id to
the installed row and deletes the bit-31 name. The file client asserts its input
has the bit clear —

```
0x007d8b1f  FcArchive:1128   (int) fileId > 0
```

— so a bit-31 id is never valid input; it only ever exists as archive **state**.
A row named `id | 0x80000000` is a row whose replacement is pending, and its plain
id genuinely stops resolving until the replacement is installed.

### The question I failed to ask — and the measurement that settles everything

The live captures were replayed against `dat_study` and `C:\gw`. **Neither is the
archive the live client was reading.** It played from
`vault/run-live/2026-07-29_221c13772c7a/Gw.dat`, and that copy says:

| archive | `0x1B97D` plain | `0x8001B97D` | bit-31 ids |
|---|---|---|---|
| `run-live` — what the live client actually read | **row 177262** | absent | **9** |
| `dat_study` | absent | row 7982 | 25 |
| `C:\gw` | absent | row 7982 | 29 |

Row 177262 is flags 259, `ffna` type 3, 24 chunks, 2,925,267 B decompressed —
the Pre-Searing map, on a **new row**; old row 7982 is freed and reused (flags
`0xFF03`). So the replacement had been installed on that copy, `DnArchive`
re-linked the plain name, and 16 of the 25 pending renames had cleared.

**The re-link IS persisted to MFT row 2 on disk** — which is the one thing the
disassembly could not settle, and the archive answers it directly.

So every observation reconciles with no masking at all:

- **ArenaNet always sends the plain, logical id.** `0x1B97D` is correct and it
  resolved, because that client's archive had it bound.
- **Our archive refuses it correctly.** `dat_study` has the map renamed away with
  a replacement pending, so `0x1B97D` misses. `FORMAT.md`'s transcript —
  `Map file '0x01b97d' failed to load. Attempting to re-bloat.` — is the miss
  path at `0x00707845`, and the retry at `0x00707866` uses **the same id** with a
  different bloat flag. Re-bloat is LOCAL. No file server is involved, so the
  loopback server was never a confound and the re-bloat hypothesis above is dead
  too.
- **Both forms "worked" for the reason a state variable works**: whichever name
  that copy currently binds.

### What this means for the server — and it is not what §8 first said

The rule is **not** "send the id exactly as the archive stores it". It is:
**send the plain logical id, and serve from an archive that binds it.** A
`file_id` in `content/maps.toml` is therefore **archive-state-dependent**, not a
property of the map — `0x8001B97D` is right for `dat_study` and wrong for
`run-live`, where the same map is `0x1B97D` on a different row. Any content row
carrying a bit-31 id is recording a transient state of one copy.

**(b) Four bit-31 ids land on map rows, not two.** MEASURED, and unaffected by
the above. `FORMAT.md` says "two of the 25 land on map-flagged rows". Reading the
raw pairs: `0x8001B97D`→7982, `0x8005E728`→7982, `0x8001C539`→20118,
`0x8005E715`→20118 — two rows, each named by two ids. Across all 18 bit-31 rows
in `C:\gw`, **0 of 18 also carry a plain id**, which is exactly what a rename
predicts. The population is 2 map files and 14 ATEX textures, so bit 31 is not
tied to a content class; and the set both grows and shrinks with play (25 in
`dat_study`, 29 in `C:\gw`, 9 in `run-live`).

---

## 8.1 BIT-31 REGISTRATION IS GONE AS OF BUILD 38833 — measured 2026-08-27

§8 establishes that bit 31 on a file id is a RENAME. **ArenaNet stopped emitting
those registrations between 38797 and 38833**, and the resync of `dat_study`
(§10.13) is what surfaced it — the mechanism was invisible while the server read
a 38797 archive.

Census over the whole file-id table, all four vaulted generations:

| archive | file ids | bit-31 ids | paired with a masked twin |
|---|---|---|---|
| 38519 | 171,024 | **25** | 25 |
| 38797 | 171,048 | **25** | 25 |
| 38833 | 171,208 | **0** | 0 |
| 38849 | 171,208 | **0** | 0 |

Every bit-31 id that ever existed was paired — **0 orphans in any generation** —
so this is a clean disappearance of a whole registration style, not a decay.

**The two map heads that carried it were both REWRITTEN in the same patch.** On
38797 exactly two map heads were named by four ids rather than two — row 7982
(`0x1B97D` Pre-Searing, plus `0x8001B97D`) and row 20118 (`0x1C539` The
Northlands, plus `0x8001C539`). Those are precisely the two maps §10.11 found
had changed bytes across the patch, and §10.12 found had regenerated their
content UUID. In 38833 both rows are gone from the head set and their
replacements — 177262 and 177590 — carry a single raw id and no twin.

**Consequence for `file_id_table()`'s mask-on-miss lookup: it is now unreachable
on a current archive, and that is fine.** The lookup exists because the id a
server sends is the masked form while only the raw form was in the table. With
no bit-31 ids registered, the raw id resolves directly — `contentids` reports
12 of 12 content map rows agreeing on the resynced archive. The path should NOT
be removed: it is still required for 38519 and 38797, which the crossbuild arc
reads.

**`test_pathmap.py` §6 caught this** rather than being wrong about it. Its checks
are now generation-aware: the census must land on one of the two states we have
seen (25 or 0) — **a third number is a format change nobody has looked at and
still reddens** — and the pairing checks declare skips where there is no twin to
pair. Its floor rises by 3 when bit-31 ids are present, so a 38797 run cannot
quietly lose them. Measured both ways: 73 checks on 38797, 68 with 5 declared
skips on 38833.

**A second registration difference, and it is NOT the same thing.** A map head is
normally named by **two distinct raw file ids**. On 38833, **4 of the 361 heads
are named by only one** — rows 177737, 177743, 177747, 177749, with ids 387574,
388989, 389121 and 389122. All four are among the fourteen heads added in that
patch. Whether single registration is normal for newly added content or a
difference worth chasing is **NOT established here**; it is recorded so the next
reader of `test_mapchunks` §"every head is named by exactly two file ids" knows
the census `{1: 4, 2: 357}` is a fact about the archive rather than a decoder
fault.

## 9. What is not established

1. **Why bit 31 is set.** Still open, and §8 makes it more interesting rather
   than less. Reading the client's `ExtractArchiveFileId` caller chain for a mask
   is the next step and is now cheap — the addresses are in §3.
2. **The remaining 296 rows.** The limit is information-theoretic, not effort:
   the archive carries a map's dims and nothing that locates it on a continent.
   Closing it needs a signal that carries position or region — the Environment
   and Sound chunks are undecoded, and terrain-tile or prop-model distributions
   would cluster by biome, though a statistical cluster is weaker evidence than
   anything in this document.
3. **The Underworld rows 461/463.** §7.
4. **CLOSED 2026-08-14 (studies/minimap rung S2) — which of `+0x48` and `+0x58`
   the client prefers, and what the 172 disagreements mean.** Left in place
   rather than renumbered, because `studies/minimap/FINDINGS.md` §3.3 cites this
   item by its number.
   **`MissionCliGetMap()` (`0x0084D9B0`, reading `missionContext+0x238`) picks:
   0 → `+0x48`, non-zero → `+0x58`** — and the enum is two-valued, so `+0x48` is
   the rect the client crops the continent atlas with while the area is an
   **OUTPOST** instance and `+0x58` the one it uses while it is a **GAME**
   (explorable/mission) instance. ArenaNet's own numbers, all three read out of
   compiled comparisons rather than inferred: `MISSION_MAP_OUTPOST == 0`
   (`QuestLog:261 MISSION_MAP_OUTPOST == MissionCliGetMap()` compiles to
   `call 0x0084D9B0; test eax,eax; je` at `0x0057BEBA`, skipping the assert when
   the answer is zero), `MISSION_MAP_GAME == 1` (`MsCliApi:251`, `cmp
   [esi+0x238],1` @ `0x0084D9EC`), `MISSION_MAPS == 2` (`MsCliMan:486`, `cmp
   [edi+0x238],2` @ `0x0085204B`). — OBSERVED, build 38797, pinned pristine.
   **Six readers apply it, and the count is measured rather than assumed.** The
   table base `0x0096DE38` occurs **exactly once** in the whole image — at
   `0x005A85A8`, inside the accessor `0x005A8580` — so every row pointer the
   client holds came from there, which is what makes an exhaustive answer
   possible at all; and the table is `.rdata`, so any site that *writes*
   `[base+0x48]` is provably not an area row. Three sweeps sharing no premise
   (int3-block co-occurrence with the 106 accessor call sites; a shape sweep for
   a contiguous four-dword rect at both offsets on one base register; a forward
   sweep from all 171 `MissionCliGetMap()` call sites) return the same six:
   `CompassMap.cpp` `0x008C2160` and `0x008C2761`, the compass block at
   `0x008C3141`, `ChCliApi.cpp` `0x00811C64`, and `GmMapHelpers.cpp`
   `0x0054E6A0` and `0x0054E830`. **`GmMapView.cpp` reads neither offset** — 0
   instructions at both over `0x00550A18..0x00553D8B`, no accessor and no
   selector call in that span. Blind to indirect calls and to a row pointer
   cached across functions; both stated so the negative is auditable.
   **The 172 are mostly not disagreements.** Of them, **136 have `+0x48`
   all-zero, 16 have `+0x58` all-zero, and only 20 carry two different non-zero
   rects.** One side is usually simply ABSENT — and the client says so itself:
   the two `GmMapHelpers` readers fall back to the other rect when the preferred
   one is `{0,0,0,0}` (`0x0054E876..0x0054E894` and the mirror at `0x0054E8A4`).
   The compass has no such fallback and bails on a degenerate rect instead
   (`0x008C274F cmp x0, x1; je`). Corroboration from a column the selector never
   touches, with the prediction stated before it was read (a flat or overlapping
   split would have refuted it): the `+0x48`-zero and `+0x58`-zero populations
   are **disjoint on their dominant `type` values** — `{2: 63, 18: 71, 14: 2}`
   against `{10: 12, 13: 3, 14: 1}` — which is what two instance kinds predicts
   and a stale-duplicate reading does not. CORROBORATED, at UPSTREAM strength,
   since `areatable.OFF_TYPE` is UPSTREAM.
   **What is still open is narrower and needs a client:** whether every one of
   the 20 two-rect rows is an outpost/explorable pair, and what a flip of the
   map-type byte actually draws, are UNVERIFIED. `studies/minimap/PLAN.md` rung
   C3 is that experiment, and **its population is 20, not 172**.
5. **`0x01A4`'s field 7** is a second map-file-id carrier (§2b) and has never
   been seen on a capture — all nine of ours used `0x0195`.
6. **The names in §6 are not proof of geometry.** A forced row means its
   *dimensions* are unique, and dimensions are not identity. The two anchors and
   the upstream rate are what make the mapping credible; a single row's name is
   as good as its `rival_rows` count says it is.

---

## 10. The table's SIZE, and the "no map" sentinel our server had wrong

**MEASURED 2026-08-27, desk only** — pinned build 38797 plus the three other
vaulted clients read as files. The client was never launched.

§3 establishes that the table is `s_missionClientData` and that the client
measures its own extent. This section measures the extent's *value*, because a
constant in `authsrv.py` disagreed with it for weeks and nothing scored the
disagreement.

### 10.1 What was wrong

`authsrv.py`'s `MAP_ID_COUNT` was **877**, sourced from OpenTyria's enum, and it
is the value the first `MANIFEST_DONE` of **every login burst** carries as the
"no map" sentinel. Row 877 on our pinned build is a real, populated row —
`Forsaken Tunnels: Level 2`, a genuine `type 18` dungeon
([studies/presearing/MANIFEST.md](../presearing/MANIFEST.md) §560, CLIENT-sourced).
So the server's "no destination" named an actual dungeon level.

`NO_MARKER_MAP` in the same file was already **888** and already re-derived off
the exe by `test_quests.py` §19 — which stayed green the whole time, because it
only ever scored one of the two names. The file's own comment flagged the
disagreement as **OPEN** and said *"nothing here has measured which. Do not
quietly make them equal."*

### 10.2 The measurement — four witnesses, no shared method

| # | Witness | Reads |
|---|---|---|
| 1 | `mission < MISSIONS` compiled | `cmp edi, 0x378` at `0x008524AC` (MsCliMan:368) and `cmp eax, 0x378` at `0x0085236B` (MsCliMan:409). **888**, two sites |
| 2 | `areatable.py` | **888** consecutive valid records, structural and code locators agreeing on the base |
| 3 | The client's own store | `mov dword ptr [reg+0x134], 0x378` — and see §10.3 for why that field is the one that matters |
| 4 | `test_quests.py` §19 | already re-derived 888 for `NO_MARKER_MAP` |

### 10.3 The field our argument actually feeds — OBSERVED

This is the leg that makes it a ruling rather than a coincidence of two numbers.

`GAME_SMSG_INSTANCE_MANIFEST_DONE` is `0x0197`. Its receive handler is
`0x0084EDE0`, which reads three fields off the message and calls `0x00852040`
with four arguments (`add esp, 0x10`):

```
0x0084EDE9  mov esi, [eax+0xc]     ; our field 3
0x0084EDEC  mov edi, [eax+8]       ; our field 2 -- the map
0x0084EDEF  mov ebx, [eax+4]       ; our field 1 -- the "phase"
```

Inside `0x00852040`, our map argument lands at `[ebp+0x10]` and is stored:

```
0x0085222B  mov eax, dword ptr [ebp + 0x10]
0x0085222E  mov dword ptr [edi + 0x134], eax
```

`codescan.py --field 0x134 --in MsCliMan` finds **three stores and zero reads**.
Two of the three are the literal `0x378`, and one of those (`0x008520E1`) sits
beside `[edi+0x168] = 4` — `MANIFEST_TYPES`, the "none" type — and
`[edi+0x130] = 0`. **So 888 is the client's own resting value for "no map" in
exactly the slot our argument writes.**

### 10.4 It moves with the table — and 877 is nowhere

Scanning every vaulted client for `mov dword ptr [reg+0x134], imm32` finds
**five such stores on every build**, and the immediate tracks the table:

| Build | Immediate |
|---|---|
| 38519 (2026-04-30) | **883** ×5 |
| 38797 (2026-07-29) | **888** ×5 |
| 38833 (2026-08-13) | **888** ×5 |
| 38849 (2026-08-20) | **888** ×5 |

ArenaNet added five maps between 38519 and 38797 and the sentinel followed them,
same five sites, same shape. That is the field *being* the table's size rather
than coinciding with it once.

**The control, and it is the half that kills 877:** the same byte scan looking
for `0x36D` (877) as a compare bound finds it **zero times on all four builds**.
877 is not a client constant and never was one — the real sequence is 883 → 888,
and OpenTyria's enum end sits between them naming nothing. Its enums stop at the
highest map somebody had bothered to name; they were never read off a binary.

### 10.5 The OPEN comment's guess was wrong in an interesting way

It feared "two different numbers for one past the last map … either two different
quantities or a bug." Both halves resolve, but not as posed:

- **877 and 888 ARE the same quantity**, and 877 was simply wrong. UPSTREAM
  against MEASURED.
- **`MISSION_MAPS` was never that quantity at all.** MsCliMan:486's
  `context->map != MISSION_MAPS` compiles to `cmp dword ptr [edi+0x238], 2` — so
  `MISSION_MAPS = 2`, a two-element enum indexed by an internal context field.
  A survey pass had reported that none of MsCliMan's asserts bounds a map id;
  that reading was right about the *conclusion* and wrong about *this assert*,
  which does name a map and bounds it at 2 because it is not the map id.
  `MANIFEST_TYPES = 4` the same way (`cmp esi, 4`).

### 10.6 Status and what is NOT established

`MAP_ID_COUNT` is **888** as of `2026-08-27`, `NO_MARKER_MAP` is defined *as*
`MAP_ID_COUNT` so the identity is expressed once in code rather than as two
literals, and `test_quests.py` §19/§19b score both names, the per-build immediate
and the 877 control (83 checks with the vault, floor 73 without).

**NOT established, and it is the honest gap: nothing in MsCliMan READS +0x134.**
The consumer is in another module and was not chased. The client writing 888 into
that field in its own reset path is strong evidence 888 is a legal resting value
there; it is **not** proof the client tolerates *receiving* 888 from the wire at
that instant in the burst. **UNVERIFIED until a login reaches character select
with the new value** — one loopback run, no ArenaNet contact.

### 10.7 PRE-REGISTERED, before the run — the loopback confirmation

Written and committed **before** the client was launched, per the house rule that
a probe states its prediction first. §10.6 leaves exactly one thing unmeasured;
this is the run that measures it.

**Question.** Does the client complete the login burst and reach a map when the
first `MANIFEST_DONE` carries `map_arg = 888` instead of `877`?

**Why it is not already answered.** §10.3 shows the argument is stored at
`context+0x134` and that nothing in MsCliMan reads it back. But `MISSIONS = 888`
appears in the module as a **strict** bound — `mission < MISSIONS` — so **888 is
exactly the value that would trip it** and 877 is exactly the value that would
not. If our map argument ever reaches a bounds-checked path, the flip we just
shipped turns a silent mislabel into an assert. That is a real and specific way
for this to be wrong, and it is why the run is worth doing rather than a
formality.

**H1 (predicted).** The client reaches the map. The field takes 888 from the
client's own reset path, and MsCliMan performs three stores and zero reads of it,
so nothing on this path bounds-checks our argument.

**H0 (the refutation, and what it would look like).** The client dies with
`Assertion: mission < MISSIONS` naming `MsCliMan.cpp(368)` or `(409)`. If that
appears, 888 is wrong **for the wire** even though it is right for the field, the
flip is reverted, and §10 is rewritten to say that the client's internal sentinel
and the value a server may send are different questions.

**Design — two arms, treatment first.**

- **Arm A, treatment:** `MAP_ID_COUNT = 888`, as shipped. Predicted: reaches the map.
- **Arm B, control:** `MAP_ID_COUNT = 877`, the old value, restored temporarily.
  Predicted: also reaches the map.

Treatment runs first so that a crash answers the question immediately. The control
runs regardless of A's outcome — it is what separates "the change is fine" from
"the harness cannot tell", and per this repo's own rule a failed control must not
be allowed to void a positive treatment.

**What to watch, in priority order.**

1. The harness's **capture-derived** verdict — the spawn rung, read from messages
   the client itself sent. Not a screenshot: §"WHY THE VERDICT COMES FROM THE
   CAPTURE" in `harness/session.py` records two runs with byte-identical
   screenshots that stopped at different rungs.
2. The client's error log and any crash dialog, specifically for MsCliMan:368/409.
3. Whether A and B differ **at all**.

**The outcome that is NOT a vindication, stated now so it cannot be spun later.**
If both arms reach the map identically, this run has **not** confirmed 888 is
correct — it has only shown the client is indifferent to the value on this path,
which is what "three stores, zero reads" already predicted. The ruling would still
rest on §10.2–§10.4's static evidence, and the honest summary is *"behaviourally
neutral, and correct on the measurement."* A green pair is a weak result by
construction. Only H0 would be strong, and it would be strong against us.

**Run:** `python toolkit/harness/session.py` (default `--until map`), loopback,
synthetic credential, caged `ours`-DH build. No ArenaNet contact.

### 10.8 THE RUN HAPPENED — 2026-08-27, both arms, and the result is the weak one §10.7 predicted

Agent-driven, caged, loopback, synthetic credential. No ArenaNet contact. Two
runs, `--until map`, verdicts read from the client's own messages.

| Arm | `MAP_ID_COUNT` | Wire | Verdict |
|---|---|---|---|
| **A** treatment | 888 | `MANIFEST_DONE[2, map 888]` | **PASS**, 8/8 rungs, `body is in the map` t+28.6 s |
| **B** control | 877 | `MANIFEST_DONE[2, map 877]` | **PASS**, 8/8 rungs, `body is in the map` t+23.1 s |

Captures: `vault/captures/harness/20260827T122700` and `…T122757`.

**The exposure is verified, not assumed.** Both arms' `gamesrv.log` were grepped
for the send itself and they differ exactly where they should:
`MANIFEST_DONE[2, map 888]` against `MANIFEST_DONE[2, map 877]`, with the second
round's `MANIFEST_DONE[0, map 148]` identical in both. An arm that never met its
condition has zero trials, and this one met it.

Arm B moved **only** the manifest sentinel: `NO_MARKER_MAP` was pinned to 888 by
hand for that run rather than left as `= MAP_ID_COUNT`, because the identity this
section shipped would otherwise have dragged the quest-marker sentinel along and
confounded the arm. Both edits were reverted immediately; the tree is clean.

**What the run establishes: H0 is REFUTED.** §10.7 named one specific way the flip
could be wrong — `MISSIONS = 888` is a **strict** bound, so 888 is precisely the
value that would trip `mission < MISSIONS` where 877 would not. It does not trip
it. No assert fired, `Gw.log` carries no `Assertion:` line in either arm (its only
`Error:` is `Failed to store credentials`, which is the synthetic credential and
is present in both), and `undecodable` is 0 both times, so the framer met nothing
it could not read. **The flip is safe on the login path.**

**What the run does NOT establish, exactly as pre-registered.** Both arms passed
identically, so this did **not** confirm 888 is correct — it showed the client is
*indifferent* to the value on this path, which is what "three stores, zero reads"
already predicted at §10.3. The ruling still rests on §10.2–§10.4's static
evidence. The honest one-line summary is **"behaviourally neutral, and correct on
the measurement."** A green pair was always going to be the weak outcome; only H0
would have been strong, and it would have been strong against us.

Do not read the 28.6 s / 23.1 s difference as a signal. It is n=1 per arm and
dominated by client boot, not by anything after the manifest.

### 10.9 Two things the run turned up that it was not looking for

**1. The harness REFUSES a stock loopback run today, and it is right to — and this
was ALREADY KNOWN.** `RUNBOOK.md`'s failure table has carried a row for it since **2026-08-23**, naming
the same map and the same cause: the client **writes to its own `Gw.dat`** as it patches
content, so a map it has loaded can end up re-pointed at an appended row that no
longer matches the frozen `dat_study` copy the server reads. What is new here is
only the census below and the third remedy. `contentids.preflight` stopped the first
attempt cold:

> map 146/148 `0x1B97D`: the two archives bind this id to **different files** —
> server row 7982 is 1,300,036 B crc `0xA0AE500A`, client row 177262 is
> 1,300,044 B crc `0x33F1A289`.

This is not one drifted client. **All three current run directories**
(`2026-07-29_221c13772c7a`, `2026-08-13_64fae3b1369b`, `2026-08-20_21511009c460`)
carry the same 1,300,044 B / `0x33F1A289` Pre-Searing map, and only the server's
pristine `vault/dat_study/Gw.dat` has 1,300,036 B. The older directories are the
mirror image — they agree with `dat_study` on 146/148 and differ on map **143**
instead (`-c2` 4,352 B, `-probe` 1,168 B, `reskin-roster` 6,012 B against
`dat_study`'s 9,284 B). So there is **no run directory that agrees with
`dat_study` on every content map row.**

The remedy used here, and it is arguably the more correct configuration rather
than a workaround: point the server at the archive the client actually draws.

```
RURIK_DAT="C:/gd/Rurik/vault/run/2026-07-29_221c13772c7a/Gw.dat" \
    python toolkit/harness/session.py --until map
```

`contentids` then reports **12 of 12 map rows agree**. Whether `dat_study` should
be re-synced instead is an open operational question and is **not** decided here.

**2. §10's archive-dependence does not reach `spawncheck`'s headline — measured,
not assumed.** [toolkit/mapdata/spawncheck.py](../../toolkit/mapdata/spawncheck.py)
defaults to `dat_study`, which the above shows is *not* the archive the client
draws, and maps 146/148 are exactly the rows that differ between them. Re-running
the census with `--dat` pointed at the client's archive gives **the same 8 of 15
and the same verdict on every single row**. The 8-byte difference does not move
the navmesh's answer for those arrival points. That is a check that could have
changed this morning's number and did not — which is worth more than the number.

### 10.10 CORRECTION to §10.9 — it is GENERATION SKEW, not modification

§10.9 recorded the `dat_study` ↔ run-dir divergence on map 146/148 and let
`RUNBOOK.md`'s standing explanation stand: *the client writes to its own `Gw.dat`
as it patches content*. **That mechanism is real and documented since 2026-08-23,
but it is not what happened here.** Measured the same day:

| copy | row | size | crc |
|---|---|---|---|
| `dat_study` | 7982 | 1,300,036 | `0xA0AE500A` |
| `dat_study_38833` | **177262** | **1,300,044** | **`0x33F1A289`** |
| `run/2026-07-29_221c13772c7a` | **177262** | **1,300,044** | **`0x33F1A289`** |
| `run/2026-08-13_64fae3b1369b` | **177262** | **1,300,044** | **`0x33F1A289`** |
| `run/2026-08-20_21511009c460` | **177262** | **1,300,044** | **`0x33F1A289`** |
| `client/2026-07-29…` (pristine 38797) | 7982 | 1,300,036 | `0xA0AE500A` |
| `run/…-probe`, `run/…-c2` | 7982 | 1,300,036 | `0xA0AE500A` |

The run dirs' "modified" map is **byte-identical to the 38833 archive
generation**, down to the MFT row index. **All three land on the same row 177262**,
and independent client-side appends could not produce one shared index — each
client would have appended at its own next free row. They were re-staged from a
38833-era source.

So: **`vault/dat_study` — the archive the SERVER reads — is a 38797-era snapshot,
and the current run dirs are 38833-era.** The `-probe` and `-c2` dirs are the old
generation, which is exactly why they agreed with `dat_study` on 146/148 and
differed on map 143 instead: that difference IS local authoring, and this one is
not.

**Note the trap in the naming.** `run/2026-07-29_221c13772c7a` carries the
**38833** map. The directory is named for the exe build it was staged for, and
its `Gw.dat` has since moved on — so the name is not evidence about the archive
inside it. That is the same shape as
[[project-rurik-sorted-last-defect]]'s lesson: never infer a build from a
filename.

**What this changes.** The remedy in §10.9 (`RUNBOOK`'s new third route,
`RURIK_DAT=<run dir>/Gw.dat`) is unaffected and still correct — it points the
server at the bytes the client draws, which is right whatever the cause. What
changes is the DIAGNOSIS a future session should reach for first: **check the
generation before suspecting damage.** `dat_study` being a generation behind is
a re-stage away from fixed and is not corruption; `datcheck`'s repair paths are
the wrong tool for it.

### 10.11 And it refutes PLAN.md item (C)'s leading candidate

§8's archive-independent-content item ranks candidate durable keys and says
**"The crc is the one to try, and it needs measuring across a patch before it is
trusted."** Measured, on both patches on disk:

| patch | size+crc identical | MFT row identical |
|---|---|---|
| 38519 → 38797 (~90 days) | 170,409 / 170,718 (**99.819%**) | 170,412 / 170,718 (**99.821%**) |
| 38797 → 38833 (15 days) | 170,985 / 171,012 (**99.984%**) | 170,995 / 171,012 (**99.990%**) |

Two results, and the second is the one that matters.

1. **The item's stated PREMISE is not supported.** It prefers crc "since row
   indices do not survive a patch". On both patches available the **row survived
   marginally better than the crc did**. That does not make the row a good key —
   it is an index into one archive's MFT and answers a different question — but
   the reason given for rejecting it is empirically wrong, and a rule resting on
   a wrong reason is worth restating on a right one.
2. **crc is REFUTED as a durable MAP key, which is the question (C) actually
   asks.** The item already frames it exactly: *"crc identifies a FILE, and
   whether it identifies a MAP across an ArenaNet update is exactly the open
   question."* Map 146/148 is the same map in both generations and **its crc
   changed**. So a content row keyed on crc would have failed to resolve across
   precisely the update (C) exists to survive. crc is the wrong key, and the
   27 changed rows in one 15-day patch are how often it would bite.

**Not settled here:** the fallback candidate, the content UUID in chunk
`0x2000000C`. `mapbuild.py` records it as never read by the client, so nothing
guarantees ArenaNet keeps it stable — and the discriminating test is narrow by
construction: only the rows whose bytes CHANGED can say anything, and there were
27 of them.

### 10.12 The content UUID is refuted too — so ALL THREE of item (C)'s candidates fail

§10.11 refuted the crc. The fallback is the content UUID in the stripped params
chunk, and it fails the same way, on the same maps.

**Two maps changed bytes across the 38797 → 38833 patch**, out of 696 shared map
heads. They are the entire discriminating set — an unchanged map cannot say
anything about whether a key survives a change:

| file id | MFT row | UUID |
|---|---|---|
| `0x1B97D` | 7982 → 177262 | `0af52e87…` → `f7a5db04…` **REGENERATED** |
| `0x1C539` | 20118 → 177590 | `7c536e52…` → `110481b5…` **REGENERATED** |

**0 of 2 held.** The UUID regenerates on precisely the maps where a durable key
would have to work. `mapbuild.py` already warned that nothing guarantees
ArenaNet keeps it stable, since the client never reads it; that caution is now a
measurement.

**CONTROL: on 8 unchanged maps the UUID holds 8 of 8.** Without it, "regenerated"
could just be an unstable reader, and the two rows above would be noise.

So item (C)'s three named candidates stand as:

| candidate | verdict |
|---|---|
| MFT `crc` + `size` | **REFUTED** — identifies a FILE; changes when the map changes (§10.11) |
| map dims from `0x2000000C` | already recorded weak — 104 distinct over 349 rows |
| content UUID | **REFUTED** — regenerates on the changed maps, 0 of 2, control 8/8 |

**What that means for (C), stated carefully.** It is not that (C) is impossible;
it is that **every key it proposed is a fact about the BYTES, and bytes are what
a patch changes.** A durable map key has to come from something ArenaNet holds
stable *because the game depends on it* — the map id the server sends, or a join
through `s_missionClientData`, which §3 already establishes the client measures
itself. That is a different design from the one (C) sketches, and naming it is
the useful half of this refutation.

**The honest limit: n = 2.** That is the whole changed set of one 15-day patch,
not a sample of it, and both failed — but a patch that rebuilt more maps could in
principle behave differently. The cheap way to widen it is the same scan across
the 38519 → 38797 pair, where §10.11 already counted 309 changed file ids
overall; this run did not decode their params.

**Two instrument defects were found getting here and both are worth carrying**,
because each produced a confident wrong answer first:
1. `mapbuild.MAP_PARAMS_CHUNK` is `0x2000000C`, the **BLOATED** spelling; the
   stripped partner uses `0x1000000C` and `MapFile.find()` returns None for the
   wrong one rather than raising. A 40-minute corpus scan reported "0 maps with
   params" in both generations. Now named as `STRIPPED_MAP_PARAMS_CHUNK` at the
   definition site.
2. The corrected sweep then reported **"347 of 347 UUIDs identical"** — over an
   EMPTY discriminating set, because its change-detector read `size`/`crc` off
   objects that did not carry them, so every map compared equal to itself. A
   vacuous green that looked like a strong result. The fix is this section's
   shape: find the changed set FIRST, report its size, and refuse to conclude
   when it is empty.

### 10.13 RESOLVED — `dat_study` is the 38833 generation as of 2026-08-27

Owner's ruling: resync. Done, and the divergence §10.10 measured is closed —
`contentids` reports **12 of 12 map rows agreeing with no `RURIK_DAT`**, so
`RUNBOOK`'s third route is no longer needed for the current run dirs.

**The source was NOT `vault/dat_study_38833`, and that matters.** That directory
is a deliberately preserved regression fixture: its live file-id table occupies
`0xF57D5000..0xF5923800`, **destroying the `Mft\x1a` magic** and leaving a
2,892,800 B orphaned tail of a stale MFT generation that `datmove.plan_move`
picks with nothing in the current rule set refusing it —
[studies/archivewrite/FINDINGS.md](../archivewrite/FINDINGS.md) §1.5, which calls
it "a ready-made regression fixture" for rung A3 and says the archive "would look
clean afterwards … right up until the client rotated its table back onto our
payload." Promoting it would have put that trap under the server's own reference
archive **and consumed the fixture**. The same paragraph names the clean
counterpart, and that is what was installed:
`vault/client/2026-08-13_64fae3b1369b/Gw.dat`.

**Nothing was deleted.** The vault now holds three generations, each with a job:

| path | generation | why it is kept |
|---|---|---|
| `vault/dat_study/` | **38833** | what the server reads now |
| `vault/dat_study_38797/` | 38797 | every 38797-pinned measurement and the crossbuild arc — `RURIK_DAT` at it reproduces an old number |
| `vault/dat_study_38833/` | 38833, damaged | the A3 regression fixture, untouched |

**Verified byte-for-byte rather than by size.** MFT sha256 `4ce9ef10dce12583`,
self-crc `0xA1F24741` — both identical to the source read *before* the copy —
with 177,738 payload CRCs recomputed and 10 of 10 open-time rules cleared.

**What it costs.** Tests that pinned facts about *which* archive is on disk move,
and that is the honest price of the resync rather than a defect in it. Known so
far: `test_archive`'s map count (349 → 361; ArenaNet added twelve maps) and
`test_pathmap`. `test_spawncheck` is unaffected, measured both ways. Each red is
classified by re-running it against `dat_study_38797` — green there and red here
means the resync caused it; red both ways means it was already broken.

### 10.14 THE BILL IS PAID — twelve reds classified by that exact method, and two of them were NOT the resync

**2026-08-29.** A full suite run scored **170 green / 19 red of 189**. Twelve of
the reds were the price §10.13 predicted, and they are now fixed. Every one was
classified by the method that section prescribes — re-run against
`dat_study_38797` — and the classification earned its keep, because **two of the
twelve were not drift at all.**

**349 → 361 is not "twelve maps were added", and the difference matters.** By
FILE ID the old 349 are a strict subset of the new 361: none lost, twelve added,
and of the 349 common ids **347 are byte-identical by (size, crc)** — exactly two
were rewritten, `0x1B97D` and `0x1C539`. By ROW the arithmetic is different:
7982 and 20118 *left* the head set and 177262 and 177590 *joined* it, because
those are the **same two maps relocated** by a completed `FcArchive`/`DnArchive`
rename. 349 − 2 + 14 = 361. **The file id is portable and the row is not**, and
the two rows most likely to be pinned as fixtures — the smallest heads — are
exactly the two that moved.

**The shape of the fix, per the standing rule (floor + signature, never an exact
value), with the exceptions stated:**

* **Population counts became FLOORS** (`>= CORPUS_MAPS`) plus the *structural*
  claim split out of the conjunction — `len(heads) == len(pairs)` is
  generation-independent and was the half that mattered. This is
  `test_mapfile`'s existing shape, which is why that file **passed while its
  seven siblings failed**: the answer was already written down in this repo and
  the others had not followed it.
* **Row-keyed tables were rekeyed BY FILE ID.** `test_mapexport`'s `ORACLE` and
  `MULTI_AXIS` were keyed by ROW and indexed with a *file-id-resolved* row —
  which is the actual defect, and it killed the module with a bare `KeyError`,
  no verdict and no ledger. The pinned values are untouched: the rewritten
  Pre-Searing still reproduces all eight oracle numbers, the dims, the rect and
  864 props **exactly**, which is what proves the content is the same map.
* **Per-generation KNOWN STATES** where an exact identity is the claim —
  `test_bit31`'s study census becomes `in (25, 0)`, `test_pathmap`'s
  `KNOWN_HIGH_BIT_CENSUS` shape. The `client/` and `run-live/` censuses stay
  **exact**, deliberately: those are dated snapshots that are never resynced, so
  a move there is a real regression and softening them would erase a live check.
* **A vacuous population is SKIPPED, not passed.** On 38833 the bit-31 table
  drains to zero, and `test_playerassembly`'s three rename-discriminator checks
  are all *vacuously true* over an empty set. They now skip with the reason
  named and the floor drops 35 → 32, raised back by `+= 3` on a copy that still
  has a pending rename to discriminate — `test_archive` section 4's idiom, so
  neither generation carries slack.

**THE TWO THAT WERE NOT THE RESYNC**, and this is why the control is not
optional:

* **`test_mapscale` is a CODE change**, bisected to `53c3911` (WORLDMAPS-W24)
  with `git archive` at nine commits over one unchanged archive. The tree
  scatter's world y was `gy*96+48` while z was sampled from the authored cell,
  standing every tree on terrain from a **different grid row**; W24 flipped it to
  `(dim-1-gy)*96+48`. Verified on all five props (gy → 31−gy every time) with
  the nine differing bytes lying entirely inside the props chunk. The constant
  was stale **because the code was fixed**, so it is re-pinned as an equality —
  a floor would pass a pipeline that had silently started emitting something
  else, which is the whole failure that row exists to catch — with the bisect
  recorded beside it.
* **`test_mapbuild` exposed a latent test defect.** Section 8 selected a donor
  by comparing against the section's donor but then called `build_like`, which
  re-derives its *own* donor. With Water taking two corpus-wide values, "differs
  from donor A" implies "differs from donor B" only when A and B share a value —
  true on 38797 **by luck**, false on 38833. The baseline is now a control build
  rather than the archive's bytes, and `build_like`'s donor is pinned to the one
  selection used.

**`test_worldmap` records a content GAIN, not a loss:** the eight world-map tiles
this file named as permanently absent are **present** in the newer archive, at
consecutive rows 177,601–177,608, each a real 512×512 ATEX. Its own section-4
skip message had predicted exactly this — *"a file id is archive STATE, so one
copy cannot show the split is a property of the atlas rather than of that copy"*
— and the second vintage answered: it was the copy's. The equality became a
subset plus a floor plus an arithmetic tie, keeping the eight as a named literal.

**Not consolidated, deliberately.** `CORPUS_MAPS = 349` lives in eight files and
the obvious tidy is one home. It was **refused** on the analysis's own argument:
after this fix the constant is a *floor* at every site, and eight copies of a
lower bound that stays true as the archive grows are harmless — while merging
eight independent measurements into one turns them into a single witness counted
eight times, which is the failure this repo names for `schema/messages.json` and
OpenTyria. A single home changed 349 → 361 would be the identical defect one
generation later. (The framing that this was a `PLAN.md` §7 Q12(a) violation was
**wrong** and is withdrawn: Q12(a) is about client-derived constants belonging in
`content/*.toml`, not about test-fixture pins.)

**Still open, filed rather than fixed:** `test_envchunk`, `test_soundchunk`,
`test_props` and `test_terrain` are green *by measuring less* — their
completeness gates derive from the moved pin, so under `--all` they now SKIP
where they used to ASSERT (`test_terrain` scores 50 against a floor of 49 with
**six** declared skips). And `test_pathchunk`'s `--all` population constants
(`CORPUS_PLANES`, `CORPUS_TRAPS`, `CORPUS_CHILDREN`, the stripped winding counts)
have **no measured 38833 value yet** — re-pinning them without their own
two-archive control is exactly what the standing rule forbids, and when someone
measures them the right shape is the known-states tuple, not a floor, because for
those the exactness *is* the claim.
