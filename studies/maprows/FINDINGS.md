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
- **Two corrections to `mapdata/FORMAT.md`**, one of them load-bearing for the
  server: ArenaNet sends the **masked** file id, not the bit-31 form (§8).

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
| GAME_SMSG **`0x0195`**, handler `0x0084ED00` | `msg+0x04` — schema field 1, `dword` |
| GAME_SMSG **`0x01A4`**, handler `0x0084F170` | `msg+0x1C` — schema field 7 |
| the download/bloat pipeline | `DnBloat.cpp` ← `FcArchive.cpp`, id arrives with the download request |

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
`0x1B97D`, which resolves to MFT row 7982.

**GAME_SMSG `0x0199` field 2 is the instance's map id.** It holds exactly one
value per connection in 9 of 9, and those values resolve through
`s_missionClientData` to:

| map id | name | file id | row |
|---|---|---|---|
| 146 | Lakeside County | `0x1B97D` | 7982 |
| 148 | Ascalon City | `0x1B97D` | 7982 |
| 164 | Ashford Abbey | `0x1B97D` | 7982 |

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

## 8. Two corrections to `studies/mapdata/FORMAT.md`

**(a) ArenaNet sends the MASKED file id.** OBSERVED. `FORMAT.md` records, and
`archive.py`'s docstring repeats, that "a server must send the bit-31 id exactly
as the archive stores it" and that the masked `0x1B97D` is refused. But
ArenaNet's own live server sent **`0x1B97D`, masked**, in 9 of 9 captured
instance loads, and the retail client loaded Pre-Searing from it.

MEASURED, to remove the obvious escape: `0x8001B97D` is stored with bit 31 in
**both** the owner's live install and `dat_study`, and `0x1B97D` is stored
plainly in **neither**. So the client must normalise the high bit when resolving
a map file id, and "the client does not mask" is **CONTESTED at minimum and
probably false**.

INFERRED, not established: `FORMAT.md`'s own transcript of the failure reads
`Map file '0x01b97d' failed to load. Attempting to re-bloat.` — the client
resolved the id and then failed on the map's *Bloated stream*, which is the state
`test_rebloat.py` deliberately creates. A re-bloat confound would explain both
observations. **This has not been re-run, and the server's current behaviour
should not be changed on the strength of a hypothesis.** The safe reading is that
the bit-31 form is known to work and the masked form is what retail uses.

**(b) Four bit-31 ids land on map rows, not two.** MEASURED. `FORMAT.md` says
"two of the 25 land on map-flagged rows". Reading the raw pairs:
`0x8001B97D`→7982, `0x8005E728`→7982, `0x8001C539`→20118, `0x8005E715`→20118 —
**two rows, each named by two bit-31 ids**, which is the head/partner pair. Also
the count is archive-dependent: 25 in `dat_study`, **29** in the owner's live
install, the four extra having accumulated since the snapshot.

---

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
4. **Which of `+0x48` and `+0x58` the client prefers**, and what the 172
   disagreements mean. Both are used here; neither is understood.
5. **`0x01A4`'s field 7** is a second map-file-id carrier (§2b) and has never
   been seen on a capture — all nine of ours used `0x0195`.
6. **The names in §6 are not proof of geometry.** A forced row means its
   *dimensions* are unique, and dimensions are not identity. The two anchors and
   the upstream rate are what make the mapping credible; a single row's name is
   as good as its `rival_rows` count says it is.
