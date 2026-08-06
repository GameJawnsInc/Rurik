# The area table, and how a string id becomes a word

Build 38797. Static analysis of `vault/run/2026-07-29_221c13772c7a/Gw.exe` as a
file, plus reads of `vault/dat_study/Gw.dat`. The client was never launched, no
debugger attached, no process memory read, no network touched.

This closes the naming half of `studies/mapdata/FORMAT.md`'s map-identity
problem and opens a capability the repo did not have: **turning any `name_id`
in any client table into the text the game displays.**

## Labels

| Label | Meaning |
|---|---|
| **MEASURED** | Checked against real bytes on this machine. The address or count is given so it can be re-read. |
| **INFERRED** | Our reading of measured bytes. |
| **UPSTREAM** | A reconstruction says it. Repeatedly wrong below. |
| **NOT ESTABLISHED** | We looked and could not settle it. Listed in §6 rather than glossed. |

Everything here is checked by `toolkit/clientscan/test_areatable.py`.

---

## 1. The answer in one page

- The client carries a static array of **888 per-map records of 124 bytes each
  at VA `0x0096DE38`**, indexed by map id. MEASURED, and found by two locators
  that share no method.
- **Every one of the 888 carries a name string id, and all 888 are distinct.**
  All 888 resolve to text.
- A client **file reference is one dword holding two 16-bit halves, each biased
  by `0x100`**. Inverting it gives an archive file id, and that formula resolves
  **1089 of 1089** text-file references. This is the general bridge from a
  reference baked into `Gw.exe` to a row in `Gw.dat`.
- A **text file is 1,024 records and a 2-byte tail**; a record is
  `u16 length, u16 aux, u16 kind` then `length - 6` payload bytes. **All 1,089
  files, across all eleven languages, tile exactly.**
- **`AreaInfo.file_id` is not a map file.** All 157 populated values resolve to
  `ATEX` textures and **none** to a map-flagged row. Four upstream sources name
  this field `file_id` and give it `file_id1()`/`file_id2()` accessors as though
  it addressed a map.
- Our 888 names agree with gw-preservation's independently typed table on
  **386 of 397** shared map ids, and **two of the eleven differences are
  upstream errors we can now correct**.
- The array is **888 records**, not the 877 or 883 upstream claims.

---

## 2. Where the table is, and why we believe it — MEASURED

Two locators, run independently, agreeing on one address:

**Structural.** Scan `.rdata` at 4-byte steps for a 124-byte-stride run where
every record satisfies eight constraints at once — four small enum fields
(campaign, continent, region, type) and three `min <= max` pairs (party size,
player size, level), plus a populated name id. Any one could coincide; a false
positive has to satisfy all of them across 64 consecutive records.

**From code.** The compiler turns `array[i]` on a 124-byte record into
`imul reg, reg, 0x7C`, and loads the base as an absolute address nearby. Scan
`.text` for `6B /r ib` with `ib == 0x7C` and collect nearby dwords landing in
`.rdata`.

```
BOTH: VA 0x0096de38   (file offset 0x56ce38)
```

The stride is corroborated by the instruction the compiler emitted; the base is
corroborated by data that fits a layout the instruction knows nothing about.

**The array is bounded at both ends, which matters more than its length looking
plausible.** Walking forward, exactly **888** records validate, and the bytes
immediately after the 888th are `P:\Code\Gw\Const…` — ArenaNet's own source
path, i.e. the array ends precisely where a string block begins. A count that
merely "looked long enough" would prove nothing.

**888 contradicts every upstream count.** GWCA (two forks) and OpenTyria all
imply 877; GWToolboxpp's vendored GWCA states `Count = 0x373` = 883 explicitly.
Both are hand-maintained enums that stop at the highest map somebody had named,
and GWCA's own header says of its name array `// This array needs testing lol.`
Neither number was ever read off the binary. Ours was.

### Layout — UPSTREAM, and it does not all survive

The field offsets come from four mirrors that state them identically: GWCA
(GregLando113 and JaborGW), GWToolboxpp's vendored copy, and
Py4GW_Reforged_Native. That is weaker than it looks — GWCA's own header credits
`entice/gw-interface`, so the agreement is partly one ancestor counted four
times.

```
+0x00 campaign   +0x04 continent   +0x08 region   +0x0C type   +0x10 flags
+0x14 thumbnail_id
+0x18/+0x1C party size min/max     +0x20/+0x24 player size min/max
+0x30/+0x34 level min/max
+0x68 file_id    +0x6C mission_chronology   +0x70 ha_map_chronology
+0x74 name_id    +0x78 description_id
```

The offsets fit: the constraint conjunction holds across all 888 records, and
`name_id` at `+0x74` yields 888 distinct ids that all resolve to sensible map
names. That is the layout earning its place, not being taken on trust.

---

## 3. `file_id` is a texture — SOURCED against UPSTREAM

The single clearest correction here. Of the 888 records, **157 carry a non-zero
`file_id`**, 72 distinct values. Every one resolves through the archive's
file-id table. And then:

| Check | Result |
|---|---|
| targets that decompress to magic `ATEX` | **157 of 157** |
| targets on a map-flagged row (flags 259) | **0 of 157** |
| MFT flags on the targets | `{3: 157}` — the texture class, not the map class |
| agreement with upstream's `map_file_id` on the 40 shared ids | **0 of 40** |

`thumbnail_id` at `+0x14` behaves the same way: 858 populated, 858 of 858
resolving, every sampled one also `ATEX`.

So `AreaInfo` carries **two texture ids and no map geometry id**. GWCA's
`file_id1()`/`file_id2()` accessors split this field as though it addressed a
map file, and GWToolboxpp's pathfinding code works around it with the comment
*"GW::Map::GetMapInfo() alone returns 0 for outposts and many maps"* — building
a shadow table from StoC packets plus a hand-curated fallback. **Their
workaround was right and their diagnosis was wrong**: the field is not an
incomplete map id, it is a complete id of something else.

This also corrects our own `studies/mapdata/FORMAT.md`, which said
"`AreaInfo.file_id` is zero throughout the static executable". Wrong in detail
— 157 are non-zero — and right in consequence: it still does not tell you which
file holds a map's geometry. **That id genuinely is not in the client's static
data**, which is why a server has to send it.

---

## 4. The file reference encoding — MEASURED, and it generalises

The load-bearing new result, because it is not about maps at all.

A file reference baked into `Gw.exe` is **one dword holding two 16-bit halves,
each biased by `0x100`**. Inverting GWCA's accessors:

```
archive_file_id = (high16 - 0x100) * 0xFF00 + (low16 - 0x100) + 1
```

Nothing was fitted. The formula came from upstream's accessors, and the
archive's own file-id table either knew the resulting ids or did not:

| Reading of the same dword | Resolves |
|---|---|
| **two-part combine (above)** | **1089 / 1089** |
| low 24 bits | 471 / 1089 |
| low 16 bits | 130 / 1089 |
| raw dword | 0 / 1089 |

`toolkit/clientscan/textrec.py` exposes this as `combine()`. Any table in the
client that references an archive file should be readable through it.

---

## 5. String id to text — MEASURED

```
string id  ->  file_index = id // 1024,  record_index = id % 1024
file_index ->  slot in a 1,089-entry pointer array  (11 languages x 99 files)
slot       ->  packed reference -> archive file id -> MFT row -> decompress
blob       ->  1,024 records, then a 2-byte tail
record     ->  u16 length, u16 aux, u16 kind, then length - 6 payload bytes
```

The `// 1024` split is CLIENT-DATA, read out of Tyria-Extractor rather than
re-derived. What makes it credible is that it lands on the right words.

**The pointer array is located structurally**, as the longest run of dwords
pointing at an 8-byte `(packed_reference, 0)` record — no address is carried
between builds. It lands on VA `0x00BF0210`, which is where the `datwrite`
study measured it by a different method.

**Ordering is `[language][file]`, proven rather than assumed.** Each
decompressed file's two trailing bytes are `(language_index, file_index)`, and
they agree with the array position: slot 0 → `00 00`, slot 1 → `00 01`,
slot 99 → `01 00`, slot 100 → `01 01`.

**The record header is `u16` length, and getting that wrong is instructive.** A
first pass read it as a `u32`, which walks a plausible distance into a file and
then stops dead — it tiled 3 files of 99 and looked correct on the ones it got,
because the failure only appears when a record's `aux` field is non-zero. With
the `u16` reading, **all 1,089 files tile to exactly 1,024 records and a 2-byte
tail with no remainder**. Text coverage is complete.

(It was 98 of 99 for one language when this was first written, the holdout being
file 98, which `gwdat.py` could not decompress. That was a zero-length Huffman
code both reference implementations drop; fixed the same day — see §8.)

Record kinds, censused over language 0:

| kind | count | share | what it is |
|---|---|---|---|
| `0x07` | 66,330 | 65.4% | high-entropy payload, `aux` non-zero and varying. Shaped like a per-record compression with `aux` as the decoded size. **NOT ESTABLISHED.** |
| `0x10` | 28,410 | 28.0% | plain UTF-16LE. This is what `get()` returns. |
| `0x06` | 5,735 | 5.7% | NOT ESTABLISHED |
| `0x05` | 879 | 0.9% | NOT ESTABLISHED |
| `0x08` / `0x0D` / `0x0E` | 16 / 4 / 2 | — | NOT ESTABLISHED |

`get()` returns `None` for a kind it cannot decode rather than handing back
bytes dressed as a string. **All 888 area names happen to be kind `0x10`**, so
the naming result does not depend on the uncharacterised majority.

---

## 6. Against upstream's names

gw-preservation's server ships 397 map definitions with hand-typed names. It has
never read our binary and we did not fit anything to it. Comparing
punctuation-insensitively on the 397 shared map ids: **386 match, 11 differ.**

Of the eleven, four are upstream's deliberate disambiguation (`Pre Ascalon
City`, `Pre Fort Ranik`) or placeholders (`Cinematic Eye Vision A`–`D` for what
the client calls `The First Vision`…`The Final Vision`), three are spelling
(`Divine Coast` for `Divinity Coast`, `Zos Shrivros` for `Zos Shivros`, an
apostrophe in `Fisherman's Haven`), and **two are real errors**:

| map id | client says | upstream says |
|---|---|---|
| 256 | **Sunjiang District** | Gates of Kryta |
| 726 | **Kilroy's Punchout Tournament** | Plains of Jarin |

Map 256 matters beyond itself: `studies/mapdata/FORMAT.md` records 101 file ids
claimed by more than one map id, and map 256 was one of them — it and map 14
both claimed `0x8A33` under the name "Gates of Kryta". That duplicate is now
explained as an upstream copy-paste rather than a fact about the archive.

---

## 7. What this does and does not solve

**Solved.** Map id → name, for all 888 maps the client knows, from the client
itself. Any `name_id` in any client table, including the skill table's, is now
resolvable offline.

**Not solved.** Map id → *map file*. `AreaInfo` does not carry it (§3), so
naming the 100 map-flagged archive rows that no mirror names is still open. The
routes left are geometry matching and rendering, not static analysis — unless
the id turns up in a table we have not found.

---

## 8. What we did not establish

1. **Record kinds `0x05`, `0x06`, `0x07`, `0x08`, `0x0D`, `0x0E`.** Kind `0x07`
   is 71% of all records; if it is a compression, decoding it opens the whole
   corpus. `aux` is a candidate decoded-size field on shape alone.
2. **The `aux` field on kind `0x10` records is always 0**, so nothing here
   constrains what it means in general.
3. ~~**Text file 98** does not decompress — `gwdat.py`'s huffman table hole.~~
   **Fixed the same day.** It was a zero-length Huffman code that both reference
   implementations park and never read back; see `toolkit/mapdata/gwdat.py` and
   `test_gwdat.py`. All **1,089** text files across all 11 languages now
   decompress and tile to 1,024 records, so text coverage is complete and the
   census in §5 above is over the whole corpus rather than 98 of 99 files.
4. **Whether `AreaInfo`'s remaining fields mean what upstream says.** Only the
   ones our constraints exercise are evidenced; the icon and chronology fields
   were carried across untested.
5. **Why bit 31 is set** on 25 archive file ids (see `studies/mapdata/FORMAT.md`).
   Reading the client's file-open path would settle both that and the exact form
   in which the client hands a reference to the archive layer.
