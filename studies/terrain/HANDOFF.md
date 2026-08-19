# Terrain texturing — handoff to a cold session

**Written 2026-08-18.** **This is NOT a status document.** `PLAN.md` §8's terrain
block is the status authority and it is current; this file deliberately does not
restate it, for the reason `CLAUDE.md` opens with. What is here is what the code
and the commits cannot tell you: the traps, and the things a cold session
predictably gets wrong.

**Read in this order.** `PLAN.md` §8 "The terrain texturing arc" (where it is) →
`studies/terrain/FINDINGS.md` §7.6–§7.21 (the mechanism, every rung locked to a
client capture) → §8 (the live open list) → §9–§12 if you are touching props or
the camera. FINDINGS is ~2,000 lines; do not read it front to back to start work.

---

## 1. The one-paragraph state

**The mechanism is closed and client-locked, and the arc's open list is short.**
The corner selector is a selection-sort comparator network (2048/2048 over two
captures), the coverage mask is PHYSICAL (212/212), the base layer is the corner
that sorts first (102/102), `trnvariation` reproduces the client's PRNG stream on
511/511 consecutive live draws, and the authored-tag-3 caveat is discharged on a
block that carries 590 authored cells (1024/1024). The exported ground **does not
repeat** beyond a floor the art itself sets. Props bind correctly except one
sub-model, which now draws a marker. The camera's field of view is measured —
75.000° horizontal, far plane 48000. What is left is small and none of it blocks
a render: the lightmap's transfer curve, the quadrant's `+u` convention, and
three named-but-not-understood fields.

## 2. What will bite you, in the order it will bite

**Terrain builds ONCE, at map load, and the window is about seven seconds.**
Walking does not retrigger it. A hook armed after that point sees *nothing*, and
it fails in the most misleading way possible: `hits 0` with a perfectly correct,
ASLR-resolved breakpoint address. That cost a run. **Start
`toolkit/clientscan/trnhook/autoinject.py` BEFORE you launch the client** — it
polls at 25 ms and injects ~1.5 s after the process appears. Never poll for the
pid by hand.

**Hardware breakpoints do not deliver in this client.** Proven by a control. Use
`int3`. Everything in `trnhook/` already does.

**You cannot aim the old instrument, and "walk there" does not work either.**
`trnlayers.c` keeps the first 512 cells that hit, so it captures whichever block
the client builds first — four runs, four different un-requested blocks. And the
blocks with the most authored tag 3 are *unreachable*: ranked by authored count,
the top four in the archive have **zero** walkable probes, because dense authored
tag 3 sits on decorative terrain no player stands on. Rank candidate blocks by
authored count **and walkability**, and aim with `trnblock.c`, which filters on
the block's own reseed (`vault/research/terrain/target_block.txt`, one hex dword)
and stays armed until the target completes.

**`build.ps1` used to build only `trnhook.c`, which is the DEAD
hardware-breakpoint design.** It takes a source argument now
(`& build.ps1 trnblock.c`) and names the DLL after it, but a stale habit will
silently produce a hook that cannot fire.

**A crashed client reports ALIVE.** The ArenaNet assert box is a modal dialog
*inside* the process, so `Get-Process` is useless as a liveness check. Enumerate
visible titled windows and treat any class that is not `ArenaNet_Dx_Window_Class`
as the crash. `Gw.log` may simply stop mid-auth chatter with no error line.

**`test_trnblend.py` §5's offset formula has no term for the UV block.** Feed it
a modern capture and every window read misaligns by 16 bytes per record and
scores *silently wrong* — not a skip, not a crash. Use
`studies/terrain/tag3check.py`, which asserts the layout against the file's own
header, or `16 + 4n + 8n + 16n`.

**`toolkit/clientscan/asserts.py`'s census is incomplete.** It does not contain
`GmCam.cpp:1728`, which is genuinely in the bytes at `0x004F38D9`. An agent
reasonably challenged a citation on the strength of that census and was wrong.
Do not treat it as exhaustive.

**Blender traps.** `tools/blender/gwcam.py` **saves over the .blend it opens** —
work on a copy or open with `open_mainfile` and never save. The exported scenes
carry **no light objects** (lighting is baked into the `gw_light` vertex colours,
so render with a plain white world; an added sun double-lights and flattens the
albedo). And `kamadan.blend` has a void-skirt plane at z ≈ −5002 holding 17.7% of
its terrain vertices, which any "find open ground from the bbox" heuristic finds
first.

**Borrowed map-id slots show the SLOT's name and world map.** `content/maps.toml`
`[map.27]` opens an existing retail map by file id; the client prints map 27's
name over it and its minimap does not match. That is the documented label/content
split, not a fault — but opening the world map (M) crashed the client on that
row, so don't. The capture needs no input at all.

## 3. The instruments that are ready, and what they cost

| tool | what it answers | cost |
|---|---|---|
| `studies/terrain/repeatprobe.py` | does the ground repeat? artifact-gated, states its predictions first | offline, minutes |
| `studies/terrain/tag3check.py` | the arg4≠0 claims, from a capture | offline, seconds |
| `trnhook/trnblock.c` + `autoinject.py` | one NAMED tile block's per-cell descriptors | one client run |
| `toolkit/clientscan/fovread.py` | the live field of view, camera position and target | seconds, read-only |
| `toolkit/clientscan/fovaxis.py` | which axis the fov spans | seconds, read-only |

`fovread` and `fovaxis` are pure `ReadProcessMemory` — no injection, no
breakpoint, no window to miss. Both need the client to be **in a map**; at
character select the globals read zero and the tools say so.

## 4. Open, and worth taking in this order

1. **The lightmap's TRANSFER CURVE.** Tag 9 is applied as `shade / 255`, the
   simplest mapping the measurement allows; 348 of 349 maps saturate at 255, so a
   gamma or a scale-and-bias would fit the corpus equally well. `--no-lightmap`
   is the control. This is the last thing that could change how the ground reads.
2. **The quadrant's `+u` ORIENTATION** — which world axis is `+u` is a
   convention chosen in code, not a measurement.
3. **Named, not understood**: `table_b` (Kamadan's values are all odd), terrain
   tag 0's `tex_word`/`tex_f12`/`tex_f16`, and the 4-dword table at
   `0x00A73DF8` = `{3, 3, 3, 0x30}`.
4. **The FOV discrepancy**, if anyone cares to close it: the client is
   horizontal-fixed, ArenaNet's 2018 patch note says vertical. Measured, not
   reconciled, and deliberately not guessed at.

## 5. What NOT to redo

- **The Wang model.** Coverage shapes come from the art (97 of 101 textures, no
  fitting); the tile→texture binding is `dep[tile + (1 if tag3b else 0)]`,
  349/349; tag 3's bit order is settled twice over; the lightmap attaches per
  vertex on tag 1's corner grid.
- **§7.2's second UV rectangle.** REFUTED — 0 of 512 cells; `0xFFFF` marks an
  unused slot whose 1/2048 span is sub-texel. It was the last hypothesis for
  large-scale repetition and it evaporated.
- **The repeat question.** Answered. The export sits on the ideal-random floor.
- **Scanning for a projection MATRIX by its shape** — zero found in 399 MB.
  Search for the cotangent VALUES instead, and require ADJACENCY.
- **Running `fovaxis.py` at a square window.** At aspect 1.0 the horizontal and
  vertical readings predict the identical pair and each self-confirms; near-square
  is worse than exact. Use portrait, where the two readings swap which cotangent
  is larger.
- **Decoding AMAT to fix the prop fall-through.** Wrong in kind — AMAT is a
  compiled shader binary (`TECH`/`PASS` chunk tags), not a texture-index table —
  and the fall-through is 0.11% of one map.

## 6. Two failure modes this arc kept repeating

**Reading disassembly and not testing it against a running client.** Four claims
were retracted that way, §7.2 among them: three days of "likeliest cause" against
ten minutes of measurement.

**Duplicated rules drift, and every test stays green.** The base-layer rule lived
in `trnblend`, `mapexport` and `import_gwmap`, drifted in all three, and each
copy was self-consistent so the suite could not see it. **Diff the exported
artifact, not just the unit.**

And one added this session: **date the code before crediting an improvement to
it.** A defect recorded at 31.6% measured 0.11%, and the obvious story — "the fix
shrank it" — was wrong; the binding code predated the claim by two hours and the
two numbers were different metrics. The retraction is §9's opening.
