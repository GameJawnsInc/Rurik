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
`toolkit/mapdata/pathmap.py` (the FFNA pathing-chunk struct layout and field names,
derived from `FFNA_ImHexPatterns/gw_file_pattern_complete.hexpat`).

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
