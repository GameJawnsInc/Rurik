# Reading the map data out of Gw.dat

Six reading tracks, each adversarially re-verified, plus hand checks. The
synthesis agent that was meant to write this document was blocked by a safety
classifier, so this was assembled by hand from the verified track results; where
that limits confidence it is noted.

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes in the archive on this machine. |
| **SOURCE-CODE** | Read in some project's source. Nobody's source is ground truth. |
| **INFERRED** | Our reasoning from the above. |
| **NOT FOUND** | We looked and there is no answer in what we have. |

This task is different in kind from all our protocol work, and the difference is
worth stating plainly. Every claim in `studies/movement/FINDINGS.md` rests on
somebody's reconstruction, because no ground truth for the protocol exists. Here
the artifact is on disk. A format claim is falsifiable, and most of the claims
below were falsified or confirmed against real bytes rather than argued from
source. That is why this document has far more MEASURED than the movement study
had OBSERVED.

---

## What we can do now, and what still blocks us

**We can open the archive, enumerate its 177,342 files, decompress any of them,
and walk a map file's chunk table to the exact byte.** That is implemented and
committed as `toolkit/mapdata/`. Collision geometry — the walkable polygons, the
map boundary, and 194,200 static obstacles with radii — is reachable today.

**Three things block a working collision implementation**, in descending order of
severity:

1. **SOLVED after this document was first written.** The claim here was that
   nothing maps a map id to a file. In fact MFT row 2 is a stored table of
   `(file_id, row)` pairs, and all six of OpenTyria's map_file_ids resolve
   through it to real map files. Kamadan is row 22371 and its geometry is parsed
   (see below). A later revision of this section still said "**Ascalon City
   Pre-Searing is still unreachable**". **That is now false too** — it is row
   7982, and the reason it looked unreachable is a bug in our own lookup rather
   than anything missing from the archive. See "Finding a specific map" below,
   which has been rewritten.
2. **There is no Z coordinate.** MEASURED. Nothing in the file says what height
   a plane sits at. GWToolbox fabricates `zplane = (i == 0 ? UINT32_MAX : i - 1)`
   when loading from the archive, which is a tell that it is not in the data.
3. **The pathfinding graph is not decoded.** Only the trapezoid sub-tag was
   read. The portals, sink nodes, and x/y node vectors that a real A* needs are
   still opaque. Collision — "is this point walkable" — does not need them.
   Pathing around obstacles does.

So the honest position: **server-side collision is achievable now; server-side
pathfinding is not; and neither can be aimed at a specific map yet.**

**Update, 2026-08-05: collision is no longer achievable-in-principle, it is
implemented.** `toolkit/mapdata/pathmap.py` decodes the navmesh and answers
"is this point walkable"; `toolkit/authsrv/authsrv.py` clips both keyboard and
click destinations against it. Item 2 above still stands and constrains it: with
no height in the file, the test is "walkable on ANY plane", which is right for
flat ground and wrong under a bridge. Item 3 stands unchanged — a click across
the map walks the straight line and stops at the first wall instead of routing
around it.

---

## The archive container

All MEASURED unless noted, and implemented in `toolkit/mapdata/archive.py`.

```
0x00  33 41 4E 1A     magic "3AN\x1A"
0x04  20 00 00 00     header size, 32
0x08  00 02 00 00     block size, 512
0x0C  70 AD CB 4C     CRC-32/ISO-HDLC of the first 12 bytes (0x4CCBAD70)
0x10  00 FE BE F8     MFT offset
0x18  28 F1 40 00     MFT size in bytes
```

**A correction to our own study.** `studies/movement/FINDINGS.md` "corrected"
OpenTyria's archive magic, asserting the on-disk bytes are `1A 4E 41 33`. They
are `33 41 4E 1A`. OpenTyria's constant `'\x1ANA3'` is a multi-char literal,
which packs high byte first, so little-endian on disk reverses it — upstream was
right and our correction of it was wrong. That error survived an adversarial
verification pass in the movement study and was caught in one read here, which is
a fair illustration of what ground truth is worth.

At the MFT offset sits `4D 66 74 1A`, `"Mft\x1A"`, with the entry count at
MFT+0x0C. **The header cross-checks itself**: the file header declares the
table's size and the table header declares its count, and `count * 24 == size`
only if the 24-byte stride is right. That is the cheapest real validation
available and `Archive.__init__` refuses to open a file that fails it.

Entry layout, 24 bytes: `offset u64, size u32, compression u16, flags u16,
counter u32, crc u32`.

- Compression is 0 (stored) or 8 (huffman/LZ77). Tally across the whole archive:
  **{0: 38633, 8: 138708}**, reproduced independently by our own reader.
- `crc` was **NOT FOUND** when this was written, and is now MEASURED: it is
  CRC-32/ISO-HDLC over the entry's stored bytes. GWUnpacker calls it CRC,
  OpenTyria calls it checksum, and neither computes or verifies it, so upstream
  was right by name and untested in fact. `studies/datwrite/FINDINGS.md` has the
  derivation and `toolkit/mapdata/test_datcrc.py` checks it — 19,703 rows on a
  strided sample, all three rules, `--full` for every row.
- The header field at 0x0C is the same polynomial over the header's own first 12
  bytes, and MFT row 3 checksums itself with its self-entry removed from the
  stream. **A writer must maintain all three.**

**Two archives are not the same archive.** The install copy holds 177,335
entries; the copy our patched client has actually run holds **177,342** — same
allocated size, same MFT offset, seven more files, because a running client
writes to the archive it was launched from. File ids are content keys and should
survive that. **Raw MFT row indices do not.** Any row index in a study is only
meaningful against the copy it was measured on. `vault/dat_study/Gw.dat` is now a
copy of the run-dir archive for exactly this reason.

### Decompression

`toolkit/mapdata/gwdat.py`, ported from `gw-preservation/fileserver-utils`'s Go
implementation. Its static tables are byte-identical to GuildWarsMapBrowser's
`xentax.cpp` — all 256 entries checked element by element, not spot-checked.

**How much to trust it, stated carefully because it is easy to overstate.**
"Produced exactly the declared number of bytes" is *not* evidence of
correctness: the decode loop stops at the declared size by construction, so the
match is forced. With the bound removed it overshoots every file tried (91,350
against a declared 91,114; 20,766 against 20,649), because the trailing u32 is a
truncation length rather than a natural stopping point. Fournux's
`DECOMPRESSION.md:26` says as much.

The real evidence is structural and independent of that length field: decompress
a map and walk its FFNA chunk table, and the chunk sizes consume the output to
the exact byte — confirmed on two separate maps (24 chunks / 2,925,270 bytes and
22 chunks / 3,389,269 bytes) — plus 628 of 628 cross-references resolving to
correctly-typed payloads. Not yet done: diffing our output against `xentax.cpp`'s
on the same input, which needs a C compiler this machine lacks. That remains the
check that would settle it.

---

## The FFNA container

Magic `ffna`, then a type byte, then a chunk table of `(u32 id, u32 size,
payload)` running to end of file. Type 3 is a map. Type 4 exists and was missed
by the first pass — a single instance, caught only when the verifier re-derived
the histogram.

Chunk ids observed resolve to distinct payload kinds; `0x21000009` resolves to
both ATEX and DDS payloads, so chunk id does not determine payload format
uniquely.

**Map files are identifiable by their MFT flags alone**, which is cheaper than
anything the tracks proposed. MEASURED: exactly **349 entries carry flags 259**,
and every one sampled decompresses to an `ffna` type-3 payload. The high byte is
the stream (1, which carries maps) and the low byte is the entry flags (3). No
decompression is needed to enumerate them — one pass over the table.

**698 map payloads, not 349.** Every map exists as a *pair* — a stage-1 file and
a stage-2 file, linked by the MFT `next` field. OpenTyria hardcodes stage 2.
Which one the client actually loads at runtime is **INFERRED**, not measured:
stage 2 is the larger, apparently final form, but nobody watched the client.

---

## The pathing geometry

Inside a map's pathing chunk, a tag-structured stream. What is decoded:

| Tag | Content | Status |
|---|---|---|
| 7 | A polygon, `u16 count` then `count` × `Vec2f`. `length == 2 + 8*count` in 349/349 maps. Duplicates plane 0's `polyData`; NOT the map boundary — see the corrections below. | MEASURED |
| 8 | `u32 plane count`, then that many planes of ten tag-framed sub-records — the walkable surfaces | DECODED, and checked |
| 12 | `u16 count` + one `u16` per plane, non-decreasing | structure MEASURED, meaning NOT FOUND |
| 13 | Static obstacles: 3-byte grid cells at 1024 units, plus float triples | framing MEASURED, cell meaning NOT FOUND |
| 14 | `u32 boundaryHash + u8 flag` | MEASURED |

Tag 14 is worth singling out as the best-evidenced small result in the pass: the
stage-1 file ends with the same u32, byte-identical to the stage-2 tag-14
payload, in 18 of 18 maps checked. A cross-stream identity like that is much
harder to get by accident than a plausible-looking field layout.

Two corpus-scale corrections matter for anyone sizing data structures:

- **Obstacle radii run 2.167 to 525.83** across 194,200 obstacles in 349 maps.
  An earlier 121-map sample gave "2.2 to 284.8" — short by nearly a factor of
  two.
- **The terrain field ImHex calls `cellSize` is not constant.** 24576.0 in 348
  maps, 55296.0 in one. Hardcoding it would work almost everywhere and fail
  silently in one place, which is the worst failure shape available.

Plane sub-tags for vectors, x/y nodes, sink nodes and portals are **NOT
decoded**. Those are the pathfinding graph.

**No height data anywhere.** `GmPos` in our own server is 2D + plane, and that
turns out to match what the file offers.

---

## Finding a specific map — solved 2026-08-06

This section used to open "**NOT FOUND**, and this is the finding that shapes
what to do next." It is kept as a heading because the reasoning that replaced it
is worth more than the conclusion: **the blocker was never in the archive. It was
in our reader.**

### The bit-31 file ids

MEASURED. The file-id table holds 171,025 pairs and 171,023 distinct ids. **25 of
those ids have bit 31 set**, and `file_id_table()` did an exact-match lookup, so
it silently resolved none of them. Two of the 25 land on map-flagged rows:

```
0x8001B97D -> row 7982    flags 259   1,300,036 bytes
0x8001C539 -> row 20118   flags 259   1,394,028 bytes
```

Masked, those are `0x1B97D` and `0x1C539` — and those are exactly the two ids
that a working upstream server sends for the Pre-Searing zones. For **none** of
the 25 is the masked form also present in the table as a real id, so the two can
never compete; `toolkit/mapdata/archive.py` now registers a bit-31 id under both
forms, plain ids first, and `test_pathmap.py` §6 asserts that non-collision so a
future archive cannot quietly break the assumption.

**Why the bit is set is NOT ESTABLISHED.** That the client's own lookup masks it
is INFERRED from the id a working server sends, not measured — we have not read
the client's lookup code. `studies/datwrite/FINDINGS.md` lists a "~29-entry bit-31
file-id watchlist" as an open question; this is that watchlist, and it is 25
entries on this copy. Reading `Gw.exe`'s file-open path would settle the meaning.

### Row 7982 is the Pre-Searing region

The identification does not rest on upstream's say-so. gw-preservation's map
table (unlicensed — read, cite, never copy) assigns three zone names to file id
`0x1B97D` and records independent spawn coordinates for two of them. Those
coordinates were never fitted to anything of ours, so they are a real test:

| Point | In row 7982 | In Kamadan (control) |
|---|---|---|
| Pre Ascalon City spawn | **1 trapezoid** | 0 |
| Ashford Abbey spawn | **1 trapezoid** | 0 |
| Barradin Estate spawn (id `0x1BA26`) | **1 trapezoid** | 0 |
| Foible's Fair spawn (id `0x1BACB`) | **1 trapezoid** | 0 |
| Kamadan spawn | — | 1 trapezoid |

Exactly one is what a non-overlapping tiling gives for a point on the ground, and
the control shows the test discriminates rather than accepting anything. Row 7982
parses to **58 planes and 6,120 trapezoids with zero malformed**, spanning
x −18432..21504, y −24576..24576 — about five times Kamadan's trapezoid count.
The two spawns that land in it are ~26,000 units apart, so at minimum this one
file covers both locations.

A quiet corroboration worth recording: row 7982 was **already** one of the two
reference maps in `test_archive.py`, the "24 chunks tiling 2,925,270 bytes
exactly" fixture that validates the decompressor. The Pre-Searing map had been
sitting in our own test suite the whole time, unrecognised.

### The upstream table, refereed

397 map definitions were read out of the mirror and every one checked against the
archive. This is the useful shape of the result — not "upstream says so" but
"upstream makes 397 mechanically checkable claims, and here is the pass rate":

- **393 of 397 file ids resolve, and 393 of 393 land on a map-flagged row.** Not
  one lands on a non-map row. A sampled FFNA check is 25/25 type-3.
- The 4 that did not resolve are **exactly** the two bit-31 ids, i.e. our bug,
  not their error.
- 249 of the 349 map-flagged rows are claimed. **100 map rows are named by
  nobody.**
- 101 file ids are claimed by more than one map id. Some are obviously right —
  The Underworld appears 7 times, The Hall of Heroes 3 — and some are
  explorable/outpost pairs that plausibly share one terrain file. Which of those
  are real and which are upstream copy-paste is UNVERIFIED and this document does
  not adjudicate it.
- File id is **not** monotonic in map id (227 rises, 135 falls, 30 equal), so the
  bracketing trick that would have named the remaining 100 maps is dead. Recorded
  because it was the cheapest idea and it failed.

### Which of a map's two ids a server sends — answered

MEASURED, and it closes an open question this document previously said needed a
retail capture. Every map-flagged row carries **exactly two** file ids, 349 of
349. Taking the smaller of each pair gives 349 distinct ids, taking the larger
gives 349 distinct ids, and **the two sets are disjoint** — no id is the smaller
for one map and the larger for another, so the split is a real structural
property and not an artefact of sorting.

Upstream's 397 `map_file_id` values are **397 for 397 the smaller id. Zero are
the larger.** The server sends the low id.

(This also corrects the old wording here. The two ids are not in separate
*ranges* — low `0x29BA..0x5B38E` and high `0x22E2C..0x5EC06` interleave. They are
two disjoint *sets*.)

### What is still not answered

Naming the remaining 100 map rows. Route 1 below was tried the same day and
**half worked**, which is recorded in [studies/areatable/FINDINGS.md](../areatable/FINDINGS.md):

1. ~~**Find the area table in `Gw.exe` and read its name string ids.**~~ Done.
   The table is at VA `0x0096DE38`, it holds **888 records** (not upstream's 877
   or 883), and all 888 name ids now resolve to text via
   `toolkit/clientscan/textrec.py`. So **map id → name is solved for the whole
   game, from the client itself.**

   But it does not name an archive row, because **`AreaInfo.file_id` is not a
   map file** — all 157 populated values resolve to `ATEX` textures and none to
   a map-flagged row. This corrects the claim made higher up in this document
   that the field is "zero throughout the static executable": it is non-zero 157
   times and still useless for geometry. The map file id genuinely is not in the
   client's static data, which is why a server has to send it.
2. Render candidates in GuildWarsMapBrowser and identify by eye.
3. Match geometry against a known landmark or map extent — now much cheaper,
   because a candidate's *name* is available even when its file is not.

---

## How much to trust these sources

Better than the protocol corpus, with the same caveat about counting lineages.

- `Jonathan-Greve__GuildWarsMapBrowser` and `gwdevhub__GuildWarsMapBrowser` are a
  fork pair — one source, not two. Its `FFNA_ImHexPatterns` are the single best
  artifact available, being machine-readable format specs.
- `Fournux__Tyria-Extractor` (Rust) and `gw-preservation__fileserver-utils` (Go)
  are separate lineages, and the latter's decompressor tables matching
  GuildWarsMapBrowser's byte for byte is genuine cross-lineage corroboration.
- Both map-browser repos credit `kytulendu`'s GWDatBrowser for decompression — a
  fifth ancestry node upstream of the lineage that was not examined. Apparent
  agreement between them may partly reflect that shared ancestor.
- OpenTyria ranks **low** here. Its parser has no test and no fixture, and four
  of its `FaArchive.h` line citations in the first pass drifted by one line.

---

## Kamadan's pathing chunk, parsed

MEASURED 2026-08-05, first geometry actually read out of the archive.

Resolved via the file-id table: map_file_id `0x345CC` -> MFT row 22371 -> FFNA
type 3 -> chunk `0x20000008`, 199,130 bytes. Signature `0xEEFE704C` and version
byte 12 both match what OpenTyria specifies, so those two constants move from
reconstruction to confirmed.

Header is `sig u32, version u32, u32 (83 here)`, then tag-framed records from
offset 12. **The framing IS uniform: `u8 tag`, `u32 size`, payload.** It walks
Kamadan's 199,130 bytes to the exact final byte, six records, ending on a
`tag 255, size 0` terminator with nothing left over.

### Two corrections to an earlier version of this section

Both were made here on 2026-08-05 and both are instructive, so they are recorded
rather than quietly overwritten.

**The u32 after tag 7 is a SIZE, not a count.** Tag 7's is 130 -- the byte
length of its payload -- and the point count is the `u16` that follows, 16. An
earlier pass read the size as the count and pulled 130 points out of a record
holding 16, running 114 points past the end and into tag 8. Every value looked
plausible, because what follows tag 7 is also map coordinates in the same space.
The half-right result this section already warned about, one paragraph after the
warning. The corpus measurement in the table above (`length == 2 + 8*count` in
349/349 maps) had it right the whole time and was not reconciled against.

**Tag 7 is not the map boundary.** It is a byte-identical copy of plane 0's
`polyData`, and the walkable geometry extends well outside it: trapezoids span
x -18432..9081 and y 1726..21504, against tag 7's x -11856..-1636, y 4840..19912.
Its 16 points are also not ordered as a ring, so a point-in-polygon test over
them means little. Do not use tag 7 to decide what is in the map.

**Spawn check, redone properly.** Our spawn (-9067, 13218), from OpenTyria's
static config and never checked against anything, falls inside **exactly one**
of the 1,270 trapezoids. Exactly one is what a non-overlapping tiling should
give -- stronger than the bounding-box test the earlier version settled for, and
it corroborates upstream's static config and the navmesh layout at once.

### Tag 8: the planes, decoded

Layout from GuildWarsMapBrowser's ImHex pattern
(`FFNA_ImHexPatterns/gw_file_pattern_complete.hexpat`) — **one lineage**, a fork
pair, no test and no fixture. A hypothesis, and treated as one. What promotes it
to evidence is that it is self-checking and checks out; see
`toolkit/mapdata/test_pathmap.py`, which is where these numbers live.

`u32 plane_count`, then per plane ten sub-records in a fixed order, each with the
same `u8 tag + u32 size` framing as the top level:

| Order | Tag | Content | Element |
|---|---|---|---|
| 1 | 0 | Plane header: 8 × `u32` counts | 32 B |
| 2 | 11 | `polyData` | `Vec2f`, 8 B |
| 3 | 1 | `edgeVectors` | `Vec2f`, 8 B |
| 4 | **2** | **trapezoids — the walkable surfaces** | **44 B** |
| 5 | 3 | root node type (0=X, 1=Y, 2=sink) | 1 B |
| 6 | 4 | x BSP nodes | 16 B |
| 7 | 5 | y BSP nodes | 12 B |
| 8 | 6 | sink nodes | 4 B |
| 9 | 10 | portal trapezoid indices | 4 B |
| 10 | 9 | portals | 9 B |

Header counts, in order: `polyData, edgeVectors, trapezoids, xNodes, yNodes,
sinkNodes, portals, portalTraps`.

Trapezoid, 44 bytes: `u32 ×4` plane-local neighbours (`0xFFFFFFFF` = none),
`u16 ×2` portals (`0xFFFF` = none), then `float yTop, yBottom, xTopLeft,
xTopRight, xBottomLeft, xBottomRight`. A y span whose left and right edges are
straight lines, so the point test is one interpolation and two comparisons.

**Why this is more than "a source said so":**

- The plane walk consumes tag 8 exactly — 39 planes over Kamadan's 193,629
  bytes, landing on the final byte. Every element size participates; a wrong 44,
  16, 12 or 9 desyncs inside the first plane.
- Each sub-record's length equals its count from the plane header, and the count
  lives in a different part of the file from the data it sizes.
- All 1,270 of Kamadan's trapezoids are well formed: **zero** inverted y spans,
  **zero** crossed x edges. A misread struct gives inversions in bulk.
- The walk succeeds on **349 of 349 maps in the archive**, not just Kamadan, and
  no map anywhere in the corpus produced a single malformed trapezoid. A layout
  that merely happened to fit one map would not survive that.

**Where the source is wrong.** Tag 11's `size` field is exactly **twice** the
length of the data that follows, in all 39 of Kamadan's planes. Counts are
authoritative; the size field is not. Anything that trusts it to skip forward
desyncs on every map. GuildWarsMapBrowser is unaffected because its pattern
indexes arrays by count and only displays the size — which is also why the error
could survive there unnoticed.

**The routing graph was never in those sub-tags.** This section used to end
"Still not decoded: portals, BSP nodes, sink nodes, edge vectors. Those are the
pathfinding graph." Half wrong, and the useful half is where it was wrong.

The intra-plane routing graph is the **four neighbour indices inside every
trapezoid record**, which our parser unpacked and discarded on the next line.
MEASURED 2026-08-06: 2,472 directed links in Kamadan and 12,478 in Pre-Searing,
none out of range, and **every one symmetric** — and on the stronger test that
upstream's TL/TR/BL/BR naming predicts, a link across a top edge is answered
across a bottom edge, **14,950 of 14,950**. Four indices in one 44-byte record
checked against four in a different record; our decoder cannot force that.

**Portals (tag 9) are now decoded too**, three fields of five:

| field | meaning | evidence |
|---|---|---|
| `u16 traps` | trapezoids of this plane touching the crossing | summed per plane it equals that plane's `portalTraps` count — **1,168 of 1,168 planes** |
| `u16 offset` | start of this portal's run in `portalTraps` | the `[offset, offset+traps)` slices **partition** that array exactly — **396 of 396 planes**, every entry covered once; all 6,146 indices valid trapezoids of their own plane |
| `u16 neighbour` | the plane on the other side | in range **3,034 of 3,034**; the plane relation is reciprocal **764 of 764** |
| `u16 pair_id` | the crossing this portal is one side of | every value shared by **exactly two** portals — 1,517 groups of two across 3,034 portals, no singleton and no triple — and the partner is in the plane named, naming back, **3,034 of 3,034** |
| `u8 flag` | always zero on all 3,034 | no information |

**`pair_id` is an identifier, not an index, and reading it as one is what hid
it.** Its values are always below the map's total portal count, which makes "a
global portal index" the obvious guess; that guess is refuted, pairing
reciprocally 0 times out of 3,034. Two other readings were tried and refuted
too — a local portal index in the neighbouring plane (12 of 1,465), and a
one-to-one plane relation (only 18 of 3,034 portals have a unique reciprocal,
because several portals can cross the same plane boundary).

**BSP x/y nodes and sink nodes are still skipped, and nothing needs them.** They
are an acceleration structure for point-to-trapezoid lookup, which
`PathingMap.containing()` already does by y-banding.

### The client settled the cross-plane question, after the data would not

Intra-plane links alone leave Kamadan in **61 components** (largest 17%) and
Pre-Searing in **91** (largest 50%). Two readings of the portal record were
tried and refuted, and an (x, y) overlap heuristic matching 90% of Kamadan's
portal trapezoids was deliberately not shipped — it is our rule rather than the
file's, and with no height in the file it would join a bridge to the ground
beneath it.

What settled it was reading `Gw.exe`. ArenaNet compiled its own assert
expressions in, and the pathing modules are named:
`P:\Code\Engine\Map\Path\{PathApi,PathData,PathDataImport,PathBsp,PathBuild,PathDir,PathFind,PathFlood,PathObstacle}.cpp`.
Two of those asserts are the answer:

- `m_trapezoid->portalLeft < pathMap.portalCount` (`PathDir.cpp`) — a
  trapezoid's two portal fields index **its own plane's** portal array. Ours
  hold on **3,051 and 3,095** set values, no exception. Every trapezoid
  coordinate also satisfies `PathData.cpp`'s
  `src.x < 131071.0f && src.x > -131071.0f` — **273,522 of 273,522**.
- `!pairRef->portal->pair` (`PathDataImport.cpp`) — the pairing is **resolved at
  import, not stored**. So the file carries an id to resolve *through*, which is
  exactly what `pair_id` turned out to be.

Linking trapezoid → portal → paired portal → trapezoid takes Kamadan from 61
components to **4, the largest holding 93%**, and Pre-Searing from 91 to **15**
with the largest at 78%. That jump is itself evidence: a wrong pairing does not
assemble a map.

### Routing

`PathingMap.route()` is A* over that graph with a string-pulling pass. Three
things about it are measured rather than assumed:

- Waypoints must be the **shared edge**, not the trapezoid centre —
  centre-to-centre between two adjacent trapezoids leaves the mesh when either
  is long and oblique, which produced an unwalkable segment before it was fixed.
- Across a portal there is no shared edge, so the waypoint is the centre of
  where the two trapezoids overlap.
- Where they do not overlap — about a fifth of Pre-Searing's — that fallback can
  fail, so **every segment is re-checked before a path is returned** and a
  doubtful path becomes None. On 120 sampled pairs per map where a straight line
  is blocked, Kamadan routes 106 and Pre-Searing 69, and **every returned path
  is walkable end to end**.

---

## Implementation plan for Rurik

Ordered, with the verifiable steps marked — that property is what makes this
work different from the protocol grind.

1. **Done.** `toolkit/mapdata/archive.py` and `gwdat.py`: open, enumerate,
   decompress, walk chunks. Verifiable, and verified.
2. **Identify one map.** Everything downstream is blocked on this. Recommend
   rendering candidates in GuildWarsMapBrowser rather than more static analysis —
   it is a one-afternoon answer to a question three tracks could not reason out.
3. **Done.** Tag 8 parses into 1,270 trapezoids for Kamadan
   (`toolkit/mapdata/pathmap.py`). The verification proposed here — "extent
   should match the tag-7 boundary polygon" — turned out to be **the wrong
   test**, because tag 7 is not the boundary. What replaced it: the plane walk
   consuming tag 8 to the exact byte, zero malformed trapezoids out of 1,270,
   and the spawn point landing in exactly one of them.
4. **Done.** `PathingMap.walkable()` and `clip()`. Still owed the playtest that
   makes it real: walk into the cube and see whether the server holds.
5. **Done**, on both 0x003D (keyboard) and 0x003E (click) rather than 0x003E
   alone — keyboard movement is the path that actually produced the wall-clip,
   since it sets a fresh destination four times a second.
6. **Mostly done, and it cost far less than this step assumed.** "It needs
   sub-tags nobody has decoded" was wrong: the intra-plane graph was in the
   trapezoid record the whole time, and `PathingMap.route()` does A* over it.
   What is genuinely left is pairing trapezoids across a portal, which is the
   only thing between us and whole-map routing.

Do not treat OpenTyria's parser as a validated spec while doing this. Its
44-byte trapezoid record, `0xEEFE704C` signature and fast-math tables are
reconstruction, and two blocks in its chunk walk are skipped blind with only an
upper-bound assert, so a wrong length assumption desyncs the parse silently.

Two of those three have since been **confirmed against real bytes**: the
signature and the 44-byte trapezoid record both hold for Kamadan, the latter
because a wrong size desyncs the plane walk. That is upstream being right, not
upstream being trustworthy — it was checked, and the check is what counts.

---

## Open questions

| Question | What would answer it |
|---|---|
| ~~Which map file is Ascalon City Pre-Searing?~~ | **Answered 2026-08-06: row 7982, file id `0x1B97D`, stored with bit 31 set.** |
| ~~Which of a map's two file numbers does a server send?~~ | **Answered 2026-08-06: the smaller one, 397 for 397.** |
| ~~What is the u32 at entry+0x14?~~ | **Answered elsewhere and this table was stale.** `studies/datwrite/FINDINGS.md` establishes it as CRC-32/ISO-HDLC over the stored bytes, and `toolkit/mapdata/test_datcrc.py` checks it against real bytes. Same for the header field at 0x0C. |
| Why is bit 31 set on 25 of the 171,023 file ids? | Read the client's file-open path in `Gw.exe`. That the lookup masks it is inference from a working server's behaviour, not measurement. |
| What are the other 100 map-flagged rows? | No mirror names them. Route 1 above: find the area table in `Gw.exe` and resolve its name string ids through the archive's text records. |
| Are the 101 shared file ids real, or upstream copy-paste? | Geometry. If two named zones share a file, both their spawns should land in it, as Pre Ascalon City's and Ashford Abbey's do. |
| Is our decompressor exactly right? | Diff against `xentax.cpp` output on the same input. Needs a C compiler. Separately, it fails on 12 of 1,089 text files with a huffman table hole — that is a live defect and the cheaper thread to pull. |
| ~~What do plane sub-tags 1, 3–6, 9–11 hold?~~ | **Largely answered 2026-08-06.** Tag 9 (portals) is decoded but for one field; tags 4/5/6 are a lookup acceleration structure nothing needs. The routing graph turned out to be in the trapezoid record all along. |
| ~~How do you pair a portal's trapezoids with its neighbour's?~~ | **Answered 2026-08-06 by reading the client's asserts.** The portal record's fourth `u16` is a shared pair id, not an index; `PathDir.cpp` pins trapezoid→portal and `PathDataImport.cpp` says the pairing is resolved at import. Kamadan goes from 61 components to 4. |
| Why do 4 components remain in Kamadan, and 15 in Pre-Searing? | Some are genuinely separate (instanced sub-areas, unreachable geometry) and some may be a link we still miss. Nobody has looked. |
| What is the portal `u8` flag for? | Zero on all 3,034 portals seen. No information in this corpus. |
| Why is tag 11's size field double its data, in every plane of every map? | Unknown. Systematic, not noise, so it means something. |
| Does the navmesh agree with the collision the client enforces? | The server now logs `on_mesh` on every stop report. A playtest answers it. |
| What height does a plane sit at? | Not in the file. Possibly derived by the client from terrain. |
| Does the client load stage-1 or stage-2 map files? | Watch it. We have the instrumentation.  |

The last row is the shape of the whole document: we have far more measurement
here than anywhere else in the project, and the remaining gaps are mostly
answerable by experiment rather than by argument.
