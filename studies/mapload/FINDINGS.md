# `GAME_SMSG 0x0195` — the whole message, field by field

**Measured 2026-08-17/18** out of the Isle arc's live captures, against builds **38797 and
38833** (both pinned pristine, read as files; the client was never launched for this). Six
of seven fields are settled; one is deliberately left `UNVERIFIED`. Four analysts and two
skeptics went over it — every number here reproduced under independent re-derivation, and
the section headed *"What was already known"* exists because a first pass presented four of
these readings as new when the tree already held them.

## Labels

Per [studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED, UPSTREAM,
RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND.

## 0. The message

Seven fields, wire size **26 bytes** (`declared_unpack_size`). The handler is
`0x0084EDC0..0x0084EE62` in 38833 — 0xA3 = 163 bytes, 54 instructions — and
`0x0084ED00..0x0084EDA2` in 38797, the same length, calling `0x853C60` where 38797 calls
`0x853BA0`. A clean **+0xC0 shift** between builds, which is also what reconciles this with
[studies/maprows/FINDINGS.md](../maprows/FINDINGS.md)'s `0x00853BA0`.

| # | wire type | offset | meaning | label |
|---|---|---|---|---|
| 0 | `msg_header` | `msg+0x00` | **the opcode itself** — not a payload field | tautology |
| 1 | `dword` | `msg+0x04` | **map FILE id** (archive file id) | OBSERVED |
| 2 | `vec2` | `msg+0x08`,`+0x0C` | **arrival position** | OBSERVED |
| 3 | `word` | `msg+0x10` | **plane** | OBSERVED |
| 4 | `byte` | `msg+0x14` | **heading**, `v · 2π/255` | OBSERVED |
| 5 | `byte` | `msg+0x18` | a flag — **meaning UNVERIFIED** | see §5 |
| 6 | `blob(8)` | `msg+0x1C` | **Windows FILETIME**, kept as a clock offset | OBSERVED |

Field 0 is a fact about our decoder, not about the wire: `codec.py:149` appends
`raw_header`, and the framer *selected* the message by that word. It is listed because it
occupies index 0 in every `values` list a caller will read.

**`0x0195` still has no `name` in `schema/overrides.json`** — `Codec.name_for` answers `'?'`.
The informal `INSTANCE_LOAD_SPAWN_POINT` appears in ten lines across seven files and is
agreed by three independent upstream catalogs (`PLAN.md:738`), so it is UPSTREAM-corroborated
rather than ours. Naming it is a second-gate question and is left alone here.

## 1. Field 1 is a FILE id, and it is one-to-MANY over maps

The handler pushes `[esi+4]` into `0x00853C60`, which passes it **directly** to
`0x004702B0` — the client's own archive-filename encoder (`(id-1) divmod 0xFF00`, `+0x100`
each half) — and only then raises UI message `0x10000098`. It is a file id *by construction
in the client's own code*, not by our inference.

Over the whole live corpus — **11 capture directories, 7 with game channels, 34 game
connections, 30 `0x0195` (exactly one per connection; the 4 without are the 4 with
`map_id 0`)** — there are **14 map ids over 7 distinct files**:

| field 1 | MFT row | map ids |
|---|---|---|
| 113021 | 177262 | 146, 148, 164 |
| 156969 | 21189 | 212, 242, 416 |
| 157087 | 21409 | 238 |
| **165811** | **21641** | **248, 280** |
| 165826 | 71475 | 281 |
| 167730 | 71585 | 309, 310, 311 |
| 167731 | 71587 | 312 |

**map → file is single-valued in 14 of 14. file → map is one-to-many for 3 of 7.** Rows
verified with `archive.binds_plainly` against `vault/run-live/2026-08-13_64fae3b1369b/Gw.dat`
— the archive the capture's own client actually read, not a snapshot.

**This settles the open question at [studies/tape/FINDINGS.md](../tape/FINDINGS.md) §1.2**,
which recorded three pre-Searing maps sharing 113021 and said it "may mean the field is a
region rather than a map, or that pre-Searing Ascalon is one terrain file. It has not been
checked." **It is one terrain file.** Inside 165811 the map-280 arrival and the five map-248
arrivals sit **2,205–2,734 units apart on the same connected walkable mesh** — `pm.route`
returns a path between them, 3 waypoints. Great Temple of Balthazar and the Isle of the
Nameless are two instances cut out of one terrain.

"Area/region file" is the wrong frame: `AreaInfo.file_id` is a loading-screen ATEX, and the
map id travels separately in `0x0199` field 2.

**Corroboration from a second artifact.** `vault/areatable/maprows.json` reaches 5 of the 7
rows by footprint join, and **every observed map id appears in its own row's `map_ids`
list** — 10 of 10 ids on joined rows. Row 21641 reads `dims [352,320], exact=True,
map_ids [248, 280, 784]`. (The two arena files join to rows carrying **no** ids, and two of
the five joined rows are `exact=False`, one of them listing 18 ids across 9 names — so this
corroborates the *direction*, not every row equally.)

## 2. Fields 2 and 3 against the client's own create — the tightest check we have

For the player's own agent, in the same connection:

```
0x0195 field 2 == WORLD_CREATE_AGENT 0x0020 field 5    29 of 29
0x0195 field 3 == WORLD_CREATE_AGENT 0x0020 field 6    29 of 29
```

Cheaper and tighter than anything else here. Two cautions kept on the record: both messages
come from ArenaNet's server, so this pins the **semantics** from one speaker, not their
correctness; and identifying the player's agent must match the `0x017D` name with
`startswith`, because in a PvP arena `0x0059` carries a **suffixed** form of it — an exact
match silently drops the four arena connections. Take the **first** `0x0020` per agent id,
never the last: one agent in `20260810T235916` has three creates and the third is 2.99 s
later after the player turned, which is the repo's `sorted()[-1]` defect in a new place.

## 3. Field 2 is the ARRIVAL position — the client-side consumption test

The independent witness is the client. Restricting to the two opcodes the repo establishes
as carrying the player's own position (`0x003D MOVE_SET_HEADING`, *"field 1 is a real
position"*; `0x0047 MOVE_CANCEL_REPORT_POSITION`, filled from `playerControlledChar`) and
**not** `0x003E MOVE_TO_COORD`, whose own override note says its vec2 *"cannot be the
player's position"*:

**30 connections carry `0x0195`; 27 of them also carry a position report; 23 are
bit-identical.** All four exceptions are explained rather than excused. The client's run
speed is `0x0020` field 9 = **288.0** in every player create in the corpus:

| capture | map | field 5 | d | dt | implied speed |
|---|---|---|---|---|---|
| 20260807T143055 | 148 | **1** | 9067.2 | 3.07 s | **2953 u/s = 10.3× run** |
| 20260810T235916 | 148 | **1** | 5979.8 | 3.62 s | **1654 u/s = 5.7× run** |
| 20260817T183756 | 242 | 0 | 452.3 | 76.78 s | 5.9 u/s — walkable |
| 20260817T231139 | 248 | 0 | 33.3 | 23.34 s | 1.4 u/s — walkable |

The two walkable ones are a player who moved before reporting. The two impossible ones both
carry field 5 = 1; of the 25 field-5 = 0 loads with c2s data, **none** mismatches.

## 4. Field 4 is a HEADING, and the divisor is 255

The handler does `fild(2·v)`, `fmul qword [0x946258]`, `fdiv qword [0x9495A8]`. Both
constants read out of both images: **3.1415927410125732** (float32 π) and **255.0**.

```
round( atan2(0x0020 field 7) · 255/2π )  ==  0x0195 field 4     29 of 29
residual, continuous 1/255-turn units                           [-0.4843, +0.4843]
```

Symmetric about zero and bounded inside ±0.5 — the signature of round-to-nearest on a
255-step quantiser. Divisor controls: **256 → 19/29** with a one-sided residual
`[0, +0.9921]`; **128 → 2/29**; **360 → 2/29**. The wire picks 255 and so does `.rdata`.

**A district hypothesis was tested and REFUTED.** Field 4 varies within one map across
connections (map 248: 209, 209, 209, 197, 254), which looks district-like — but `0x0199`
field 1 for those same five loads reads **1, 35, 14, 35, 12**. Districts 1/35/14 all give
209, and district 35 gives both 209 *and* 197. Different partition; there is a real district
field and this is not it.

## 5. Field 5 — correlated, and left UNVERIFIED on purpose

It is 1 in **4 of 30** loads, and the handler **passes it without testing it**: it reaches
`0x00853C60`, is stored into a record at `[ebp-0x20]`, and the only nearby `cmp` is against
a constant 1, not against this value. (The handler contains no `cmp`/`test` at all; the one
branch, `jns` at `0x0084EE24` with `fadd [0x93C1D8]` = 4294967296.0 = 2³² on the
fall-through, is the MSVC unsigned-to-float fixup, not a semantic branch.)

All four `f5 = 1` loads are the **earliest load in their capture** by FILETIME, and a clean
controlled pair exists inside one capture: `20260817T180610` loads map 416 then map 212
**15.097 s** later with `(156969, (-2132.0, 1054.0), 0, 146)` identical and field 5 going
1 → 0.

**Why this is not called "the login flag" here.** Only 2 of the 4 `f5 = 1` loads carry any
c2s position at all, and **both report the identical constant `(9250.0, -1200.0)`** — the
same point in two captures three days apart. That is *one* distinct observation, not two,
and a fixed value reads at least as much like a staging or uninitialised slot as like "the
avatar was genuinely elsewhere". The correlation is real; the mechanism is not established.

## 6. Field 6 is a Windows FILETIME, and it exposes two server clocks

The handler copies the 8 bytes, calls `Now64()` — which asserts
`Time:178 context->realTime` — subtracts 64-bit, and stores `blob8 − Now64()` at
`ctx+0x368/0x36C` as a **clock offset**. Decoded as a FILETIME the values are real wall
times (e.g. `b'\x08!\xe9\x9f\xc0.\xdd\x01'` → **2026-08-18T03:12:14.121351**).

Differencing it against local capture time across the 14 loads of `20260817T231139` splits
them into two tight groups:

```
A (delta ~0)       n=5   maps [248 x5]                              spread 5.45 ms
B (delta ~+1.4454) n=9   maps [280,280,280,280,281,309,310,311,312] spread 3.23 ms
gap between group means 1.4454 s, over a session spanning 847.3 s
```

**Not a per-IP artifact**: map 309 sits on the same address as all five map-248 connections
and lands in group B. Two server clocks, ~1.45 s apart, stable to a few milliseconds across
fourteen minutes.

## 7. A misattribution in the tree, corrected

[studies/enemy/PLAN.md](../enemy/PLAN.md) placed `0x0084EE83` — an
`or dword ptr [edx+0x2A8], 0x10` sticky-bit set — inside `0x0195`'s handler, and reasoned
about whether *our* server could trip it. **It is in `0x0199`'s handler**, which begins at
`0x0084EE40` in 38797, past `0x0195`'s handler end at `0x0084EDA2`. The descriptor table
settles it:

```
descriptor VA 0x00BCB27C  idx 39  dispatch 0x0084ED00  cmds[0]=0x0195
descriptor VA 0x00BCB2AC  idx 43  dispatch 0x0084EE40  cmds[0]=0x0199
```

The `cmp` at `0x0084EE7D` is on `0x0199` field 6 at `msg+0x18`. The *conclusion* there
survives — that field is **0 in 30 of 30** loads — but it survives for a different opcode
than the one the document names.

## 8. What was already known — read this before citing anything above as new

A first pass presented four of these seven readings as fresh OBSERVED work when the tree
already held them, and that is the largest error in the original write-up:

- **`schema/overrides.json:828`** — under a *different* opcode's `why` — already recorded
  the handler storing a vec2 + plane, the `v·2π/255` heading conversion, the
  `blob8 − Now64()` clock offset, and the consumption test at 6 of 8 loads with the field-5
  correlation at 8/8. **That is fields 2, 3, 4, 6 and the field-5 correlation.**
- **`studies/maprows/FINDINGS.md:116-122`** already had the handler, field 1 at `msg+0x04`
  as the archive file id, and the `0x004702B0` encoder.
- **`studies/tape/FINDINGS.md:56`** already had 113021 → MFT row 177262.

**Genuinely new here:** the 38833 addresses and the +0xC0 build shift; the corpus expansion
from 8 loads to 30; the **file → map one-to-many table** and the terrain-file settlement;
the heading divisor discriminated against 256/128/360; the FILETIME wall-clock decode and
the two-clock split; and the `0x0084EE83` misattribution.

That the knowledge was filed under another opcode's `why` is itself the lesson: it was
unfindable from `0x0195`. This document is where it lives now.

## 9. What is NOT established

- **Field 5's meaning.** §5. Correlated with first-load-in-capture and with the two
  consumption-test misses; mechanism unknown; the client never branches on it.
- **A trapezoid test that looked stronger than it is.** All 22 distinct
  `(field 1, field 2, field 3)` triples land in exactly one trapezoid whose only plane
  equals field 3, against a null control of the same positions against the wrong files at
  **20/132 = 15.2%**. But **19 of the 22 have field 3 = 0**, and plane 0 holds 73–94% of
  every file's trapezoids — an oracle answering "plane 0" scores most of them. The null
  control varies the FILE and never the PLANE, so it tests a different question. The three
  arena samples carry nearly all the discrimination. §2's 29/29 is the better evidence.
- **A live conflict about `0x0020` field 7.** It measures as a **unit vector** — `|f7| = 1.0`
  in **182 of 182** creates on one map-280 connection — while `schema/overrides.json`'s own
  `0x0020` note says `agint.h:929` bounds-checks fields **5/7** as a world position. One of
  those is wrong and the repo currently holds both. §4's heading result reads f7 as a
  direction and works, which is evidence but not a resolution.

## 10. One fixture this settles, and the change it implies

`content/maps.toml [map.280]` pre-registered **two** facts for the Isle capture to answer,
and only the file id was reported at the time:

```
wire arrival, all 4 map-280 loads:  (-6036.0, -2519.0)
content/maps.toml [map.280]:        spawn_x = 1136.0, spawn_y = -463.0
```

The row's own spawn is a **mesh-centre probe** — the row says so — and retail's arrival is
**2,600+ units away**. `studies/unitsetup/FINDINGS.md:99` confirms those row values are what
our server sends as `0x0195` field 2, so this was a live fidelity gap.

**Both were then answered in the row itself (2026-08-18).** `file_id` is confirmed six
times over, with the pre-registered *third branch* also firing — the id is shared with map
248, which is what §1 is about — and `spawn_x/y` now carry **retail's arrival position**.
The replacement is what the row's note asked for in its previous form (*"replace spawn_x/y
if fidelity to retail matters"*) and it passes the same walkability check the old value
did: `(-6036, -2519)` lands in **exactly 1 trapezoid on plane 0** of file 165811, against
**0** for the Pre-Searing control. The old value was never wrong — it was verified walkable
too. It was just **ours**, and this is a retail emulator.
