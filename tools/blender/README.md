# `tools/blender/` — the Blender half of the map pipeline

`import_gwmap.py` turns a `rurik.gwmap` terrain interchange into a Blender mesh.
`export_gwmap.py` turns a Blender mesh back into one. The interchange is produced
by `toolkit/mapdata/mapexport.py`, which reads one map's terrain out of `Gw.dat`
and writes a JSON manifest plus a de-tiled float32 height field, and consumed by
`toolkit/mapdata/mapbuild.py`, which assembles a whole map file from it. Nothing
here opens an archive, and nothing here writes one.

```
Gw.dat ──mapexport──> .gwmap.json ──import_gwmap──> .blend
                            ^                          │
                            └────export_gwmap──────────┘
                            │
                            └──mapbuild──> a map file
```

## Why `bpy` is allowed in this directory and nowhere else

`CLAUDE.md` pins `toolkit/` to **Python 3, standard library only**, so the server
and every checker keep working on a bare machine. `bpy` is not stdlib and is not
installable — it exists only inside Blender's own interpreter. `tools/blender/`
sits outside that rule and holds only code that cannot run anywhere else.
Nothing under `toolkit/` imports this file: its test,
`toolkit/mapdata/test_blenderimport.py`, is stdlib-only and drives Blender as a
**subprocess**, so the rule is never bent in order to test the exception to it.

The interchange is also re-read from scratch here rather than through
`mapexport.load_export`. Blender's interpreter is not this project's, so a
`sys.path` walk into `toolkit/` would reintroduce exactly the dependency the
format exists to remove — the point of an export is that a tool which knows
nothing about ArenaNet's archive can open it. It is ~40 lines of `json` and
`struct`, and it verifies every sha256 before it uses a byte. That the two
loaders are independent implementations is also what lets the test compare them.

## Running it

Headless, which is what the test does:

```
blender --background --python-exit-code 66 \
    --python tools/blender/import_gwmap.py -- \
    <map>.gwmap.json --dump summary.json --clear
```

Everything before `--` belongs to Blender; everything after belongs to the
script. Options:

| flag | what it does |
|---|---|
| `--out FILE.blend` | save the scene when the import is done |
| `--dump FILE.json` | write the built mesh's summary (counts, bbox, named vertices, per-axis sha256, and a `props` block when proxies were built) |
| `--dump-verts FILE.f32` | write every vertex as interleaved little-endian float32 x,y,z |
| `--name NAME` | name for the object and its mesh |
| `--clear` | empty the scene first (the startup cube, camera and light) |
| `--no-props` | terrain only; skip the props collection even when the export carries the sidecar |

Interactively: open the file in Blender's text editor and run it, or
`import import_gwmap; obj, gw = import_gwmap.import_gwmap(r"…\map.gwmap.json")`
then `import_gwmap.build_prop_objects(gw)` in the Python console. `--clear` is
off by default so running it inside a scene you care about does not delete it.

## Props are PROXIES, not models

A format_version-2 export carries a `.props.json` sidecar — every placement of
the map, from both of the archive's props streams, cross-checked at export time
(`toolkit/mapdata/mapexport.py`). The importer turns each into a proxy object
in a `<name>.props` collection: an outlined prop becomes its **measured
footprint polygon** extruded, any other a 16-gon cylinder at the **measured
placement radius**. The proxy *height* is invented for display (half the
radius, floored at 10) and is the one number that measures nothing. **No
ArenaNet model geometry is decoded anywhere in this tree** — a prop reaches
Blender as a transform, a footprint and a radius, with the sidecar record on
the object as `gw_*` custom properties (model index, model file id, rot bytes,
scale byte, radius, flags). Prop z is negated exactly as the terrain's is, so
props stand on the mesh they shipped beside; the outline is *not* rotated (the
compiled ring is literally `x+dx, y+dy` — measured, no rotation term), while a
radius proxy carries the compiled basis as its object rotation.

**`--python-exit-code` is not decoration.** MEASURED on Blender 5.1.1:
`blender --background --python x.py` exits **0 even when the script raises**. The
traceback is printed and the process reports success. So every refusal this
importer makes — a sidecar whose sha256 disagrees, a missing sidecar, a manifest
from another format version — is invisible to a caller that trusts the exit code
unless that flag is passed. The test asserts the exact code, not just "non-zero".

## The conventions it honours, and where they were measured

All of these are MEASURED. None is ours to choose. `studies/customarea/FINDINGS.md`
§17.4 is where they were read out of the client; §16-P5 and §16-P6 record the
rival conventions as belonging to someone else's renderer.

| convention | what the importer does | where it came from |
|---|---|---|
| **Cell pitch is 96.0 world units** | vertex `(i,j)` at `x = x0 + i*pitch`, `y = y1 - j*pitch` | a compile-time constant on the client's Bloated path and a hard `== 96.0` gate on the Stripped one; `(x1-x0)/dimX` is exactly 96.0 on 349/349 maps, and the `(dim-1)` divisor — the control — is not |
| **Samples are at cell corners** | mesh is `(dimX+1) × (dimY+1)` vertices and `dimX × dimY` quads, spanning the rect exactly | the file stores `dimX*dimY`; the client manufactures the extra column and row by **replicating their neighbours** (a per-chunk min/max over 1089 = 33×33 samples for a 32-cell chunk) |
| **Grid row 0 is world maxY** | `j` increases as world y decreases | `gx = int((wx-x0)/96)`, `gy = int((y1-wy)/96)`; the client's own `x0 + 96*i` / `y1 - 96*j` with no half-cell term anywhere |
| **z is the NEGATION of the stored float** | the mesh is the right way up | **CORRECTED 2026-08-11 (§25).** This row read "heights are NOT negated" and cited the load path applying no transform — tag 1 does reach the client's buffers through `memcpy`, and that is a fact about BYTES, not about which way is up. Two client runs differing only in this sign settled it: a greater stored value is LOWER in the world. GuildWarsMapBrowser negates every height and is right to; §16-P5's filing of that as "ITS convention" is corrected |
| **Storage order is tiled 32×32** | nothing — `mapexport.py` has already de-tiled | the interchange is world row-major, `gy*dimX + gx`, by the time it gets here |

Two consequences worth stating outright:

* **Do not invent an edge.** The far column and far row are replications, not
  extrapolations and not omissions. Anything going the other way — a mesh back
  into a terrain chunk — has to *drop* that manufactured edge, because a chunk
  can only store `dims × dims`.
* **The quad winding is `(i,j) → (i,j+1) → (i+1,j+1) → (i+1,j)`.** Since world y
  decreases as `j` increases, that is the order whose face normal comes out +Z.
  The other order builds the same surface upside down, and the test counts
  normals rather than trusting this paragraph.

The pitch is read **from the interchange** rather than hard-coded to 96.0, for
one reason: a hard-coded constant would make the test's pitch control unable to
fail, and a check that cannot fail is not a check. The importer cross-checks
instead — `dims * pitch` must equal the map rect span, which is MEASURED true on
349/349 maps — and a disagreement is a loud stderr warning plus
`extent_matches_rect: false` in the dump.

## What the mesh is evidence of, and what it is not

The tile indices (`.tiles.u8`) and shade bytes (`.shade.u8`) are attached as
per-face integer attributes `gw_tile` and `gw_shade` when the export carries
them. Their **meaning is unsettled** — `toolkit/mapdata/terrain.py` labels both
NOT FOUND — so carrying them is transport, not understanding, and no geometry
reads them. Tag 3 is not exported at all: its bit-pair position inside a byte is
not established by anything measured.

Nothing here writes to an archive, and no water, prop, zone or navmesh data is
carried in either direction — `pathmap.py` already reads the last of those and
joining them is a separate rung. **So an author edits the height field and
nothing else**, and the navmesh, which is what the client actually collides
against (§23, §24), is still authored by hand: a sculpted hill changes what is
drawn and does not move a single trapezoid.

## `export_gwmap.py` — the way back out

```
blender --background --factory-startup --python-exit-code 66 \
    --python tools/blender/export_gwmap.py -- \
    --blend scene.blend --out <dir> [--name NAME] [--object NAME]
```

| flag | what it does |
|---|---|
| `--out DIR` | **required.** Destination; a git working tree is refused |
| `--blend FILE` | open this file first; default is the current scene |
| `--object NAME` | which mesh (required when the scene holds more than one) |
| `--dump FILE.json` | write the manifest for a checker as well |
| `--xy-tolerance N` | how far a vertex may sit off the lattice (default 0.0625) |
| `--refuse-unstorable-edge` | fail rather than warn on a far edge that cannot be kept |

**Four things are undone, and each is a place a silent exporter loses work.**

1. **The lattice is re-derived from world POSITIONS, never from vertex order.**
   Terrain is a height field on a regular grid; Blender is under no such
   constraint. A vertex dragged sideways cannot be written down, so the grid is
   rebuilt by clustering the coordinates the mesh actually carries and anything
   off it is **refused**. Two tolerances, because there are two bands: a vertex
   dragged far enough leaves its column and the lattice stops filling, and one
   nudged half a unit stays in its column and is caught only by the residual.
2. **The manufactured far edge is dropped, and what that costs is reported.**
   `manufactured_edge_unstorable` counts the far-edge vertices whose value is not
   the replication — i.e. the values that will change next time the map is read.
   It is named for the *effect*: sculpting the edge lands a vertex on it, and so
   does sculpting the last **real** column beside it.
3. **z is negated back**, the inverse of the importer's flip.
4. **The metadata is carried but cross-checked.** The importer stamps the whole
   manifest (minus the sidecars) onto the object as a `gwmap` custom property,
   because tag 0 and the tile tables are not recoverable from a mesh. `dims`, the
   rect and the pitch are **not** taken from it — they are re-derived from the
   geometry, and a disagreement is reported rather than resolved. An exporter
   preferring the stamp would emit the map that was *imported* however it had
   been edited since.

**An identity `matrix_world` multiply is not a bitwise no-op on signed zero.**
`-0.0 * 1.0 + 0.0` is `+0.0`, so a stored `0.0` came back `-0.0` — numerically
equal, one byte different in 24,576. The transform is skipped when there is no
transform; a genuinely moved object still loses the sign of zero.

## Provenance

An exported height field is **derived ArenaNet data**. `CLAUDE.md`'s provenance
gate keeps it out of the repo permanently, and `mapexport.resolve_outdir()`
enforces that with a refusal rather than a warning: exports default to
`vault/exports/` and the working tree is refused with no flag to override it.
Keep `.gwmap.json`, `.f32`, `.u8` and any `.blend` built from them in the vault
or in a scratch directory. **No fixture in this repo may be cut from one.**

`export_gwmap.resolve_outdir()` reimplements that rule, because Blender's
interpreter cannot import the authority — it refuses any destination inside a git
working tree (a worktree's `.git` is a *file*, and both count) unless it is under
a `vault` directory. `test_blenderroundtrip.py` asserts the reimplementation
refuses the same repo root, which is the only thing keeping the two from drifting.

## Tests

```
python toolkit/mapdata/test_blenderimport.py      # 75 checks, ~13 s
python toolkit/mapdata/test_blenderroundtrip.py   # 77 checks, ~39 s
```

Both find Blender via `RURIK_BLENDER`, then `--blender`, then the known install
path, then `PATH`, and skip loudly (and red) if there is none — a run that
measured nothing has not passed. An explicit path that does not exist is
**refused** rather than fallen through to the default, because it fell through
once and a run that asked for one Blender measured another and printed green.

**`test_blenderimport`** — sections 0–2 need no vault and score 39 of 75. The rest
runs the **prop-z oracle against Blender's own vertex buffer**: the props chunk
`0x20000004` is read by neither the exporter nor the importer, so a flipped row
order or a wrong pitch has nothing to hide behind. It resolves gross *layout*,
not registration — a one-cell shift scores inside the spread, and that limit is
measured rather than assumed.

**`test_blenderroundtrip`** — sections 0–4 need no vault and score 65 of 77. Its
headline is that ArenaNet's 212,992 heights, tiles and shade bytes survive a
`.blend` byte-for-byte, and **that headline is the weak half by measurement**: a
memcpy sabotage keeps all six byte-identity checks green, including the retail
ones, and is caught only by the sculpt control. See `studies/customarea/FINDINGS.md`
§32 for the three sabotages and where each landed.
