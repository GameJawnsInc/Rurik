# Authoring a world: what the client will and will not accept

**This is the distilled operational half of [FINDINGS.md](FINDINGS.md).** Every
claim here is measured at a retail client (build 38797) and names the rung that
measured it; where a claim is a RECONSTRUCTION rather than an observation it
says so. Nothing here is new evidence — read FINDINGS for the runs, the
controls, and what each one could not settle.

It exists because the arc is twenty-three rungs deep, its evidence lives in
gitignored vault run notes, and **a reader arriving at FINDINGS cold will meet
W17 and W19 before meeting W20's reinterpretation of them.**

---

## 1. What you can build

| | established | rung |
|---|---|---|
| terrain, authored, any size to **256×256** | client compiles it | W7 |
| delivered **compressed** (compression 8) | into a retail row | W1, W2 |
| into a **created chain** — a file id ArenaNet never shipped | displaces nobody | W3, W4 |
| the **server** paths against the compiled mesh | two independent readers agree | W13 |
| **bodies** placed on it, validated against the mesh | W15 |
| a character **walks** it | W16, W18, W19 |
| **obstacles** of arbitrary planar shape | W21, W22 |

## 2. The two levers in `map_flags`

One dword in the 41-byte Map Parameters chunk, at payload offset **+21**. Two
**disjoint** bitfields, read once and meeting again in the same function, so
they compose (W14, W17).

### Bit 0 — the water line

Clear, the client **drops every terrain triangle whose three corners are all
≥ 40.0 units under water**. Set, it keeps them.

```toml
map_flags = 1        # submerged ground is walkable
```

The constant is `40.0` at `0x0094DE30`, compared at `0x0072D3ED` inside
PathFlood.cpp's classifier, gated at `0x0072D3C6` (W10, confirmed at the client
by W11). On the shipped areas this was costing real ground — `expanse` gained
**+31,950 cells**, from 50.54% coverage to 99.29% (W12).

### The top byte — the slope threshold set

```toml
map_flags = 0x02000000    # walkability cut moves 35 deg -> 45 deg
```

| top byte in the file | what the client sees | threshold set | walk cut |
|---|---|---|---|
| `0x00` | **1** (normalised) | 15 / 35 / 30 | **35°** |
| `0x01` | 1 | 15 / 35 / 30 | 35° |
| `0x02` | 2 | 10 / 45 / 40 | **45°** |

**The parser normalises a top byte of 0 to 1** (`0x0070D9B2`, `0x0070D9BE`), so
**0 and 1 select the same set** — the boundary is 1-vs-2, not 0-vs-nonzero. Use
`0x02`. Using `0x01` produces a perfect null that looks exactly like a
refutation (W17).

`0x03` and above cross a `< 3` test at `0x0070D9DE` and move another bit;
untested, don't.

**To set both levers: `map_flags = 0x02000001`.** W24 shipped exactly that
and the compiled head read it back intact, with bit 0 demonstrably in force
(a below-water pool meshed). Whether the top byte's SET was honoured in the
same compile is UNVERIFIED -- W24's mesh failure was geometric, and a
floor-only mesh discriminates nothing about thresholds.

## 3. Slopes — there are THREE classes, not two

This is the part most likely to surprise you, and it is why W20 exists.

The classifier reads a three-float array and emits **three** classes:

| | condition | |
|---|---|---|
| **class 0** | slope < `array[0]` | meshes on its own |
| **class 2** | between | **see below** |
| **class 1** | slope > `array[1]` | excluded outright |

Under the cut-35 set that array is {30, 35, …}; under cut-45 it is {40, 45, …}.

**OBSERVED (W23, and it is not a reconstruction any more): class-2 ground
cannot be climbed out of flat ground.** A uniform 42.51° ramp rising from a flat
apron meshes **0 of 288** ramp cells; the identical map at 18.43° meshes
**288 of 288**. One field apart, no strips, no seams, no neighbours.

**And the condition is sharper than "needs a class-0 neighbour".** That ramp's
apron IS class-0 and IS adjacent. The one thing W20's successful run had is
class-0 ground that **RISES**, carrying the flood to the heights the class-2
ground occupies. *Hypothesis, untested: the flood accepts class-2 ground only at
heights it already reached through class-0 ground.*

The original, weaker form of the same observation (W20, four strips varied at
once): three runs at cut 45 differing only in the
shallowest strip: with 43.78° or 41.19° as the shallowest, the map compiled to
**the flat apron alone**; adding an 18.43° strip made the 42.51° and 43.78°
strips appear. Being *adjacent* to the flat apron was not enough.

**So: a steep region needs a gentle approach THAT CLIMBS WITH IT.** A map made
only of 41–45° slopes
will compile to nothing but its flat ground, and nothing in the toolchain warns
you.

**Measured cut positions:**

- cut-35 set: the boundary is **35**, cut in (32.0, 36.1) (FINDINGS 48).
- cut-45 set: cut in **(43.78, 45.00]** (W20) — a 45.00° slope authored in *our*
  measure came out excluded, but that sits exactly on the threshold where
  float32-vs-double decides it, so it does not settle strict-vs-non-strict.

**This reinterprets W17 and W19.** `gen_ramp`'s first three strips are class 0
and its strip 4 (41.5–42.5°) is class 2, so W17's `WWWW.` and W19's climb both
happened *with class-0 strips beside them*. Their findings about the top byte
and about traversability stand; the reading that **a 41–42° slope is walkable on
its own does not**.

### The master rule (how Ashcoil authors a whole landscape legally)

W24's showcase map composes the numbers above into one construction, worth
stating because it makes the forbidden band impossible rather than avoided:

- **Walkable ground: pre-quantization gradient <= 40 units/cell.**
- **Walls: hard discontinuities >= 192 units in one cell.**
- **Quantize everything to 48.** Then every axial step is 0 or 48 (30.2 deg,
  class 0 under cut-45 with the worst triangle plane at 35.3 deg), every wall
  is >= 144 after the snap (56.3 deg, class 1), and **no step can land in the
  conditionally-meshed 40-45 deg band at all**. Requires `map_flags` top
  byte 2 -- under the 15/35/30 set the same 35.3 deg planes are class 2.
- **An elevated road leaves flat ground only through a SLOT** -- flanked by
  rock >= 192 above both the road and the ground beside it, the flanks
  terminating ABRUPTLY (an abrupt end presents a >= 144 face, legal; a
  TAPERING flank sweeps its height difference continuously through the
  forbidden band somewhere, always). Ashcoil hit this three separate times
  (the mouth, the top-out, the draw's uphill bank); the fix was a slot each
  time, and the third was caught only by the offline validator.

**And one W24 lesson the master rule does NOT cover: a narrow gate can fail
to flood even when every local slope is legal.** Ashcoil's coil entrance --
~3 cells wide between a 1008-unit wall and the flank ridge, wobbled and
snapped -- never admitted the flood, and connectivity pruning then deleted
the entire elevated system. The pool's circular 48-riser staircase on the
same map meshed fine, so the staircases were not the problem; the GATE was.
Every surface this arc walked before W24 was wide open. Until clearance is
measured, treat anything under ~5 cells of walkable width as unproven.

### Authoring an EXACT slope

The terrain codec's `snap_block` projects each **4×4 sub-block independently**.
If you want a slope the client classifies at the value you intended:

- make `dz` (height change per 96-unit cell) a **multiple of 4**, and
- align each constant-slope region to the **4×4 sub-block grid**.

Do both and the snap moves nothing (worst sample 0) and every interior column is
identical. Do neither and it spreads by up to **1.4°** — which is what limited
W19 to a 3.94° bracket (W20).

## 4. Props and obstacles

```toml
trees = 1
prop_outline = 288             # half-width, WORLD units
prop_outline_shape = "square"  # or "L"
```

- A prop with **no** footprint blocks nothing. That is what every prop this
  project placed before 2026-08-21 carried — and it is **retail-normal**:
  Kamadan's 516 props share 280 outline points between them (W21).
- A footprint is honoured **1:1 in world units**. Authored half-width 288 put
  the mesh's last walkable x at 2640 against an authored edge at 2640 (W21).
  The `scale` byte does not scale it.
- The **shape is the polygon**, non-convex included — a square with its
  north-west quadrant cut out leaves that notch walkable while the other three
  quadrants are complete holes (W22).
- A character hitting one **stops and slides** along it, rounding its corner
  (W21's trace).

Untested: self-intersecting or open rings (43 of retail's 37,548 outlined props
are not closed, so the client tolerates them); whether the prop *model*
contributes collision; vertical extent.

## 5. Gotchas that have each cost a run

- **`seed_x`/`seed_y` on an area is the compiler's FLOOD SEED, not the player's
  spawn.** The spawn comes from the MAP row. `seed_x` has three consumers in
  `toolkit/` and none is the player. This was written up wrongly in W13 and
  corrected 2026-08-21.
- **A flood seed on ground the client will not mesh CRASHES the compiler** —
  `Assertion: (dest == vertices + 1) || (dest[-1].pos != dest[-2].pos)`,
  `PathFlood.cpp(681)` (W13). Not a clean failure; the map simply never
  compiles.
- **The run that PRODUCES a mesh can never serve it.** `--install` arms the head
  to zero so the client must recompile, so at server start there is no mesh, and
  once the client is up it holds the archive exclusively. Serving takes a
  **second, unarmed** run (W13).
- **The server cannot see `map_flags`** — zero occurrences under
  `toolkit/authsrv/`. No flag effect is ever server-side.
- **Terrain grid row 0 renders at world maxY** (FINDINGS 4's argmax on
  345/346 maps; W23's apron trapezoid -- authored at gy >= 14, meshed at
  world y 0..1728 -- confirms it against the client). Props are placed in
  world coordinates and do NOT flip, so anything positioned from a grid cell
  must convert: world y = (dims-1-gy)*96+48. `deploy.assemble` does this for
  trees as of 2026-08-22; every earlier treed map was flat or y-symmetric,
  which masked the mismatch. RECONSTRUCTION until W24's client run scores it.
- **Agent ids 1, 30 and 200–206 are reserved** (player, henchman, heroes), as
  are definitions 9 and 10–16. `area_population` RAISES rather than filters, so
  one bad id refuses the whole area at start-up and nothing runs (W15).

## 6. How to measure a result here, learned the hard way

Five instrument faults in this arc, every one a fault in how the result was to
be **read** rather than in the thing measured. They are worth more than any
single finding:

1. **Don't clip a band asymmetrically against a wall.** W12 predicted "96–99%"
   because 98.86 + 3 is not a coverage figure; the measurement came in at 99.29
   and the *clip* failed, not the model.
2. **Make sure the instrument can reach.** W16's first walk plan ran out of leg
   and looked like a failure to cross.
3. **Name WHERE, not just how much.** W18's "max y over the whole trace" was
   satisfied by the character climbing a *different*, always-walkable strip.
4. **A value ON a boundary cannot test the boundary.** W20 authored a slope at
   exactly 45.00° to test strict-vs-non-strict; both sides compute it
   differently, so the operator was never in play.
5. **A summary statistic can hide the answer.** W21's "max x" could not
   distinguish *blocked* from *blocked and walked around*; the raw trace held a
   far stronger result — collision, slide, and both authored edges to the unit.

Two habits that worked:

- **Score the compiled mesh offline before spending a walk.** It is free, it
  catches dead premises, and in W19 and W22 it *was* the result.
- **Give both arms the identical plan and vary one field.** It makes an
  anomalous number diagnosable instead of merely disappointing — and it is why
  every one of the five faults above was caught at all.

## 7. Where the evidence is

`studies/worldmaps/FINDINGS.md` for the arc, per rung. The run notes —
predictions registered before each run, and full scoring after — are in
`vault/research/worldmaps/WORLDMAPS-W<n>-RUN.md`, which is gitignored and local.
`PLAN.md`'s WORLDMAPS section is the status authority.
