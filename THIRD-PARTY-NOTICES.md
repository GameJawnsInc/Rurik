# Third-party notices

Rurik contains no third-party code as a dependency — `toolkit/` is Python 3 standard
library only, with the `capstone`/`pefile` carve-out in [CLAUDE.md](CLAUDE.md) for
read-only client analysis. What it does contain is work **derived from** other people's
reverse engineering: file-format layouts, constant tables, and algorithms.

This file is where that is credited. It exists because one licence in this list
*requires* it, and because the project's own rule about the unlicensed repositories in
this field — *read them, learn from them, cite them, never copy from them* — is worth
nothing if we are casual about the ones that do grant a licence.

---

## GuildWarsMapBrowser — Jonathan Bjørn Greve

**Used by:** `toolkit/mapdata/gwdat.py` (the `Gw.dat` huffman/LZ77 decompressor and its
six constant tables, derived from `SourceFiles/xentax.cpp`) and
`toolkit/mapdata/gwentropy.py` (the A6 entropy accountant — it re-uses two of those same
tables, `CODE_LENGTH_THRESHOLDS` and `CODE_LENGTH_SYMBOLS`, in the ENCODE direction, and
re-runs `gwdat.decompress`'s block loop with counters attached. It **imports** both
tables from `gwdat.py` and re-transcribes neither, so nothing new is taken from upstream
— but the direction is new, and it is new because upstream never wrote it: all five
mirrored lineages of this format declare decode only. `PLAN.md` §6.1) and
`toolkit/mapdata/gwmatch.py` (the A7a LZ77 matcher — it **imports** four more of those
same six tables, `LENGTH_BASE`, `LENGTH_EXTRA_BITS`, `DISTANCE_BASE` and
`DISTANCE_EXTRA_BITS`, to read off the format's min match, max match, alphabets and
window, and re-transcribes none of them. The *search* is not upstream's at all — a hash
chain with lazy matching, following deflate's published design — and nobody upstream has
a matcher for this format to take. `PLAN.md` §6.1) and
`toolkit/mapdata/pathmap.py` (the FFNA pathing-chunk struct layout and field names,
derived from `FFNA_ImHexPatterns/gw_file_pattern_complete.hexpat`) and
`toolkit/mapdata/mapchunks.py` (the Dependencies record `{u16 id0, u16 id1, u16 pad}`
and the pair→file-id formula `(id0 - 0xff00ff) + (id1 * 0xff00)`, from the same pattern
file's `MapFileRef`/`MapFileRefPadded` and from `SourceFiles/animation_state.cpp`) and
`toolkit/mapdata/terrain.py` (the **terrain chunk** layout hypothesis, from
`FFNA_ImHexPatterns`, `FFNA_MapFile.h` and `SourceFiles/Terrain.cpp` — what is taken is
the hypothesis and not the layout: every load-bearing field is re-derived from the
client's own 11-entry step table at `0xA74F28` and confirmed corpus-wide, and upstream
is a witness we had to correct on tag numbering, on `cellSize`, and on a storage order
its own pattern and renderer disagree about. `PLAN.md` §6.1).

**Credit, as clause 2 requires:** this software incorporates work by **Jonathan Bjørn
Greve**, from **GuildWarsMapBrowser**, <https://github.com/Jonathan-Greve/GuildWarsMapBrowser>.

**This licence is not MIT**, though it reads like it at a glance. Clause 1 additionally
requires a link to the original repository wherever the notice is reproduced, and clause 2
requires credit in documentation or visibly in derived software. Both are satisfied here.
Reproduced in full:

```
Custom License

Copyright (c) [2023] [Jonathan Bjørn Greve]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

1. The above copyright notice, this permission notice, and a link to the original repository (https://github.com/Jonathan-Greve/GuildWarsMapBrowser) shall be included in all
copies or substantial portions of the Software.

2. Users must provide credit to the original author [Jonathan Bjørn Greve], either by including the author's name and a link to the original repository (https://github.com/Jonathan-Greve/GuildWarsMapBrowser) in the documentation, or by visibly displaying the author's name and the link to the original repository in any derived software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## OpenTyria — ldufr

**Used by:** `schema/messages.json` (the message catalog, imported from `code/msgdefs.c`
by `toolkit/schema/import_msgdefs.py`), `content/items.toml` (`item.starter_hammer`, from
`GmDefaultArmors.c`), `toolkit/mapdata/archive.py` (the archive magic's byte order), and
several map file ids in `content/maps.toml`.

**Licence: the Unlicense — public domain.** No obligation whatsoever, including no
obligation to credit. Credited anyway, because a catalog that came from somewhere should
say where: `schema/overrides.json` exists precisely to keep our corrections separable from
their import, and `CLAUDE.md` warns that OpenTyria agreeing with `schema/messages.json` is
one witness counted twice rather than two.

---

## Headquarter — ldufr

**Used by:** nothing, as code. It appears here for one reason: `schema/overrides.json`
names `GAME_CMSG 0x0040 ROTATE_PLAYER`, and Headquarter's `opcodes.h` has carried that
same name at that same value all along. The name was *not* taken from it — it was read
out of client build 38797's own assertion text, `(rotation >= -1.0f) && (rotation <= 1.0f)`
at `P:\Code\Gw\Char\Cli\ChCliApi.cpp:5562`, reached from the only entry point that feeds
the one send site for that opcode. Headquarter is a second witness, and crediting a second
witness is cheaper than arguing about whether we needed it.

**Licence: MIT** — permissive, attribution only. PLAN.md §4's A3 also quotes its
`opcodes.h` for the 60/40/194/487 message counts. Its derivation-register row was added
2026-08-10, at the moment the first name landed and not before; it should have existed
when A3 was written.

---

## Tyria-Extractor — Fournux

**Used by:** `toolkit/clientscan/textrec.py` (the string-id split `file = id // 1024,
rec = id % 1024`, taken from `doc/SKILL_EXTRACTION.md` and **not** re-derived by us) and
`toolkit/clientscan/skilltable.py` (the 0xA4 skill record layout and its field offsets,
read from the same document and re-derived here). Both carry rows in
[PLAN.md](PLAN.md) §6.1.

**Licence: MIT** — permissive, attribution required, which is why the notice below is
reproduced in full rather than summarised. The mirror is at
`vault/mirrors/Fournux__Tyria-Extractor` (gitignored; `toolkit/mirror_priorart.py`
fetches it).

**This entry is four days late and the delay is worth recording.** Tyria-Extractor is
cited over a hundred times across sixteen study documents and in five modules;
`studies/reconstruction/FINDINGS.md` §9.3 flagged the missing register row on
2026-08-13 and `studies/quests/FINDINGS.md` §7.9 flagged it again on 2026-08-15. The
obligation is small — one row and this notice — and it went unmet because nothing
checked it. `toolkit/derivlint.py` checks it now.

**It is not clean-room for client structures**, and that matters for how its agreement
is scored: its own `README.md` credits GWToolbox++/GWCA as an input, so
Tyria-Extractor agreeing with GWCA is one witness counted twice — the same trap
`CLAUDE.md` names for OpenTyria and `schema/messages.json`. Where it *is* an
independent witness (its PE measurement of 1,333 skill rows, reached by its own parse
of a 2026-07-26 client) the agreement is real, and `test_skilltable.py` scores it
against the wiki as well so the corroboration does not rest on one lineage.

```
MIT License

Copyright (c) 2026 TyriaExtractor contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## What is deliberately NOT here

**`gw-preservation/*` and `Py4GW_Reforged` carry no licence at all, which means all rights
reserved.** Nothing in this repository is derived from them, and the rule is recorded at
[PLAN.md](PLAN.md) §1.1 and enforced at load time: `toolkit/content.py` refuses any content
row citing one of those sources unless it records what we independently verified the value
against in our own artifacts. Reading them, verifying our own findings against them, and
citing them is not copying. `toolkit/mapdata/gwdat.py` was the one place that crossed the
line and it was re-derived on 2026-08-06; see PLAN.md §6's derivation register.

**ArenaNet.** Guild Wars, `Gw.exe` and `Gw.dat` are ArenaNet's. This repository contains
none of their bytes and never has — no client files, no extracted assets, no decompiled
code. See the top of `.gitignore` for the rationale and PLAN.md §7 Q3 for why the gate is
kept absolute rather than restated as a derivation graph. Everything here that describes
their formats is our own observation of a client the owner bought.
