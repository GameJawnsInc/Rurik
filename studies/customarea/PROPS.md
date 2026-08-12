# The Stripped props chunk — reconnaissance, and why it is an arc

**Written 2026-08-12, after rung E10.** `0x10000004` is the last chunk standing
between `stripbuild.py` and a map that is entirely ours. FINDINGS 34 makes it a
hard gate: no props object, no navmesh. This document is what a survey and an
hour of disassembly established, and — more usefully — what they did **not**,
so the next attempt starts from the right place.

**NOTHING HERE IS A CODEC.** No props chunk has been decoded. The 12 bytes
`stripbuild.py` borrows are still borrowed.

## What the corpus says

MEASURED over all 349 map pairs on `vault/dat_study/Gw.dat`:

| | |
|---|---|
| chunks | 349, one per map |
| distinct sizes | **342** |
| smallest | **12 B** — the ladder template, row 46197 |
| next smallest | 16 B (two maps) |
| signature / version | `0x39583392`, version byte 17, on 349/349 |
| Stripped : Bloated ratio | 0.1416 corpus-wide (FINDINGS 17) |

**342 distinct sizes over 349 maps** is the headline: this is a variable-length
record format holding real content, not a stub. The donor's 12 B is the corpus
MINIMUM, which is why FINDINGS 36/38/39/43 all compiled — a near-empty props
chunk satisfies the gate.

### The two smallest, which is all the structure that fell out

```
12 B   92 33 58 39 | 11 | 00 00 00 04 00 00 | ff
16 B   92 33 58 39 | 11 | 00 00 00 04 00 00 06 00 00 00 | ff
```

* `0xFF` terminates, as it does in the terrain chunk (tag 255) and the Stripped
  path chunk. So the body is a **tag pipeline**, which is the family both other
  chunks belong to.
* The 16-byte form is the 12-byte form with `06 00 00 00` inserted before the
  terminator — consistent with one extra record.

### What was tried and does NOT fit

Stated so nobody spends the survey again:

* `size == 9 + n*k` and `size == 12 + n*k`, for every stride `k` in 1..200,
  with `n` read as a `u32` at +5 — **0 of 349** for every `k`.
* the same with `n` as a `u16` at +5 — **0 of 349**.
* `{u8 tag, u32 size}` records, the TERRAIN chunk's framing — does not close on
  the 12-byte body.
* `{u8 tag, u16 count}` records — closes on the 12-byte body and **not** on the
  16-byte one, which is the shape of a coincidence rather than a law.

The `u32` at +5 varies per map (67108864, 147456, 70656, 93440, 43008 …) and is
not a record count under any stride tried. What it is, is **NOT FOUND**.

## The parse chain, which is the useful part

Read out of the pinned build 38797 image, `BaseAddr 0x00400000`:

```
s_chunkInfo[0x04].load  = 0x00712200      (the dispatch, FINDINGS 17)
  0x00712207  three assert gates on the caller's struct
  0x00712264  call 0x00738A90 with five args      <- the parser
     0x00738A90  push/pop ebp; jmp 0x0073CC80     (a thunk)
        0x0073CC80  asserts its two pointers, then
        0x0073CCD5  call 0x0047F490 -- allocates 0x228 bytes
        0x0073CCDF  call 0x00737B40 -- with the chunk pointer
```

`s_chunkInfo[0x04].bloat = 0x00712280` is the other half and is what FINDINGS
34's hard gate actually calls.

**The tag walk is inside `0x00737B40` or below it, and has not been read.**

`PrProp.cpp` carries 8 assert sites — `prop->model` at 730/771/805/806 — which
says a prop record has a **model** field and nothing more about the framing.
There is no `PrpData` module in the assert census, so the census gives no
per-record vocabulary the way `TrnCodec*` did for terrain.

## Why this is an arc and not an afternoon

The Stripped TERRAIN codec (FINDINGS 37) is the precedent, and it took its own
arc. What made that one tractable was `TrnDataBloat`'s **eleven-stage pipeline
table** at `0x00A74958` — a table of function pointers, one per tag, that could
be dumped and read stage by stage. Whether props has an equivalent is unknown;
`0x0073CC80` is a constructor-and-dispatch shape rather than a table walk, so
the first job is to find out.

The standard the result has to meet is the one `strippedterrain.py` and
`pathchunk.StrippedPath` met: **349/349 byte-identical re-encode, with a
mutation control that a memcpy fails.** A codec that replays stored sizes
round-trips every file it can walk and understands nothing, and this repository
has caught exactly that twice.

## What it would unlock, stated honestly

`stripbuild.py` borrows 54 bytes in three chunks. Props is 12 of them. Reading
it removes one of three, so **the headline "97.69% generated" barely moves** —
2.31% to about 1.8%.

That is not the reason to do it. The reason is that props is where **objects**
live: FINDINGS 34 says the props object supplies the portal and collision point
pairs the decomposition runs over, so until it is written, a map from this
toolkit can have our ground and cannot have a single tree, wall, door or portal
on it. Header and Zones are 42 bytes of constant that nothing needs to vary.
**Props is the one that is not a constant.**
