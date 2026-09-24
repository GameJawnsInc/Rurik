# `tools/viewer/` — the model viewer

A local window that browses every model in the owner's `Gw.dat`, textured, with
the skeleton drawn over it. The parade (`studies/slice/RUN-PARADE.md`) showed fifteen
bodies by launching the retail client; this shows all 20,775 without launching anything.

```
python tools/viewer/modelviewer.py                      # the app
python tools/viewer/modelviewer.py --file-id 116703     # open on the hatcher body
python tools/viewer/modelviewer.py --template hatcher   # body + the shell's skeleton
python tools/viewer/modelviewer.py --file-id 116703 --skeleton-from 116228 \
    --shot C:\somewhere\outside\the\tree\hatcher.png    # one frame, no window kept
pythonw apps/modelviewer.pyw                            # double-click launcher
python tools/viewer/modelviewer.py --smoke C:\scratch\out  # drive every panel once, exit
```

Left: **Models** (search by id, hex or decimal; `row N`; filters for skeletons, for the
skeletons the wire names as creature shells, and for collision; thumbnails render
lazily for the rows in view, one per event-loop turn, and the menu action still renders
every listed model at once), **Templates** (`content/npcs.toml` rows, drawn as the
client composes them: body mesh, shell skeleton), **Maps** (`content/maps.toml` rows;
picking one lists only the props that map references; the map → model index is cached
under the vault, so the tab opens in about a second after its first ~20 s build). Right:
toggles, a per-slot texture override, the info pane, export and screenshot. Drag orbits,
right-drag pans, wheel zooms, double-click fits.

## Why `PySide6` is allowed here and nowhere under `toolkit/`

`CLAUDE.md` pins `toolkit/` to the standard library so the server and every checker
run on a bare machine. `tools/` is where consumers that cannot meet that live —
`tools/blender/` for `bpy`, this directory for PySide6. The line is enforced by
shape, not by promise: **every archive fact comes from `toolkit/mapdata/modelcatalog.py`**,
which is stdlib, read-only, and tested in the suite (`test_modelcatalog.py`, 75 checks),
and `modelviewer.py` holds no knowledge of any ArenaNet layout. If a picture looks wrong,
the bug is in the catalog or a decoder under it; the viewer only draws arrays it is handed.

PySide6 is LGPLv3, dynamic-linked, never vendored or redistributed; its row is in
`PLAN.md` §6.1 and its credit in `THIRD-PARTY-NOTICES.md`.

## Shells, anim files, and what the archive will not tell you

A head with no geometry is one of two things: a **creature shell**, a skeleton whose body
the wire supplies (`0x0056` names the shell, `0x0057` its bodies, per definition), or an
**anim file**, a skeleton another model links to through its FA8 list for extra sequences.
The archive does not say which. MEASURED 2026-09-14 on all 759 geometry-less heads: the
`MODEL_SKELETON_FLAG_COMPOSITED` bit is set on 759 of 759 (it means "no FA0", full stop),
and FA8 linkage fails too -- 394 heads are link targets of other skeleton heads, but 13 of
the 32 shells the wire has named as creatures are targets as well. The 311 FA1-only heads
match the unitmodels study's ~312 anim-file class, and that is a floor, not a rule.

So the catalog's kind is `model` or `skel`, and the label "this is a creature you can
see" comes from the wire: `toolkit/mapdata/wireshells.py` inverts every keyed live tape
(`0x0056` names a definition's shell, `0x0057` its bodies) into shell → bodies with every
sighting's capture kept -- 105 shells, 212 bodies, 215 pairs from 19 tapes, rebuilt in
~3 s when a tape is added. The Models tab marks such rows `SHELL · N bodies · M tapes`
(plus a `content/npcs.toml` name where a client run has put one on a nameplate), the
third filter lists only the 82 skeleton heads the tapes dressed, and a skeleton head's
right pane lists its bodies most-seen first and draws the pick under it, with the
pairing's source stated. A skeleton no tape ever dressed is shown as unknown -- an
unspawned shell or an anim file -- rather than guessed. The hatcher shell (116228) is the
generic human male skeleton: 36 bodies over 18 tapes, "Hatcher [Collector]" one of them.

## What a frame means

- **The mesh is the FA0 geometry as stored** — the bind pose, flat, no node transform
  applied. `tools/blender/import_gwunit.py` established that this IS the rest pose:
  every keyed skeleton node sits inside the mesh's own box, and `test_modelcatalog.py`
  re-measures it on the worm (18/18).
- **The skeleton is the blk2C rest positions** joined along the measured link hierarchy.
  For a template it is the *shell's* skeleton over the *body's* mesh — the composite the
  client assembles from `0x0056` + `0x0057`. Green bones, magenta node crosses.
- **The texture is the material's diffuse under the measured rule**: `mtlIndex` → the
  layered material → the first layer sampling a *stored* UV set → its FA5 slot. Not
  layer 0 (92 of Kamadan's 1,063 sub-models put a generated layer first and rendered
  black). The other layers are listed in the info pane and not drawn: which is detail,
  lightmap or specular is still open (`studies/models/FINDINGS.md` §6.1). The slot
  override exists to look at them.
- **Alpha is a finding, not a rule.** Seven Kamadan textures and the hatcher's own
  diffuse are "erasers" whose alpha would delete the surface; those draw opaque.
  "cutout" textures are alpha-tested at 0.5; materials with a non-zero `blend` are
  blended. One checkbox turns all of that off.
- **Animation is not played.** The channels are decoded (`studies/anim/`), but nobody has
  driven vertices through node transforms and checked the result against the client. A
  still frame is what this viewer can stand behind; playback is a separate rung with its
  own study.
- **Conventions**: model −z is world-up (the scene flips z, camera up is +z); UVs are
  Direct3D's and are used unchanged — MEASURED 2026-09-14 that Qt's texture upload puts
  image row 0 at v = 0 on both upload paths, so no flip is applied.

## Checking it after a change

`test_modelcatalog.py` covers the stdlib half in the suite. The window itself is not a
suite test (PySide6 is not bare-machine), so `--smoke DIR` drives it by hand: every tab,
the hatcher template join, the Kamadan map filter, the search and shell filters, a grab
of the on-screen frame scored for coverage, three offscreen thumbnails, and the lazy
thumbnails arriving for the rows in view and again after a scroll to the end -- 20
steps, `[PASS]`/`[FAIL]` per line, non-zero exit on any failure. Run it before
committing a viewer change, always with a timeout (the offscreen QPA hangs outside
`--smoke`); `--shot` renders one frame the same way for a look.

## Where files go

The catalog cache (`vault/cache/modelcatalog/catalog-<mft sha>.json`, ~15 s to build on
first run, stamped and refused against another archive state), the map index
(`.../maps-<mft sha>.json`, keyed by map FILE id so a content-row change costs one decode
and never a rebuild; `test_modelcatalog.py` §4b) and thumbnails
(`.../thumbs/<sha>/<fid>.png`) live under the vault. Screenshots go through
`vaultpath.resolve_out` — the vault or a scratch directory, never the working tree.
Exports call `modelexport` / `unitexport`, which refuse the tree themselves.

## The one shortcut, and its test

The catalog classifies all 21,535 flags-515 heads from their **first chunk header**
(a ~0.5 ms prefix read instead of a ~34 ms full decode), on the measurement that a
geometry chunk is always first when present. `test_modelcatalog.py` §2 re-walks every
50th head in full and asserts the prefix verdict agrees with the whole chunk list
(431/431), so a build that broke the ordering would redden the suite rather than
silently shrink the model list.
