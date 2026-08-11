# `tools/blender/` — the Blender half of the map pipeline

`import_gwmap.py` turns a `rurik.gwmap` terrain interchange into a Blender mesh.
The interchange is produced by `toolkit/mapdata/mapexport.py`, which reads one
map's terrain out of `Gw.dat` and writes a JSON manifest plus a de-tiled
float32 height field. Nothing here opens an archive, and nothing here writes one.

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
| `--dump FILE.json` | write the built mesh's summary (counts, bbox, named vertices, per-axis sha256) |
| `--dump-verts FILE.f32` | write every vertex as interleaved little-endian float32 x,y,z |
| `--name NAME` | name for the object and its mesh |
| `--clear` | empty the scene first (the startup cube, camera and light) |

Interactively: open the file in Blender's text editor and run it, or
`import import_gwmap; import_gwmap.import_gwmap(r"…\map.gwmap.json")` in the
Python console. `--clear` is off by default so running it inside a scene you
care about does not delete it.

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
| **Heights are NOT negated** | z is the stored float, unchanged | the client's load path applies no transform at all — tag 1 reaches its buffers through `memcpy` and nothing else. GuildWarsMapBrowser's renderer negates every height; §16-P5 records that as ITS convention |
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

This is not an authoring round-trip. Nothing here writes to an archive, and no
water, prop, zone or navmesh data is imported — `pathmap.py` already reads the
last of those and joining them is a separate rung.

## Provenance

An exported height field is **derived ArenaNet data**. `CLAUDE.md`'s provenance
gate keeps it out of the repo permanently, and `mapexport.resolve_outdir()`
enforces that with a refusal rather than a warning: exports default to
`vault/exports/` and the working tree is refused with no flag to override it.
Keep `.gwmap.json`, `.f32`, `.u8` and any `.blend` built from them in the vault
or in a scratch directory. **No fixture in this repo may be cut from one.**

## Test

```
python toolkit/mapdata/test_blenderimport.py
```

68 checks, ~13 s. It finds Blender via `RURIK_BLENDER`, then the known install
path, then `PATH`, and skips loudly (and red) if there is none. Sections 1 and 2
need no vault and score 34; section 3 needs `vault/dat_study/Gw.dat` and scores
the other 34 by running the **prop-z oracle against Blender's own vertex
buffer** — the props chunk `0x20000004` is read by neither the exporter nor the
importer, so a flipped row order or a wrong pitch has nothing to hide behind.
