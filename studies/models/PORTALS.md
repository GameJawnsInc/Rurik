# Portals — a corpus census

**MEASURED 2026-08-14** against `vault/dat_study/Gw.dat`, build 38797.

Portals are the props that warp a player between maps. They matter beyond
rendering: [studies/customarea/FINDINGS.md](../customarea/FINDINGS.md) §5 lists
"spawn points, portals or map links" as **NOT FOUND in map files**, and this
narrows that — a portal is a prop with a known model at a known world position,
so the geometry names **where** a map link is, even though nothing here says
where it leads.

Labels are the project vocabulary
([studies/character/FINDINGS.md](../character/FINDINGS.md)).

---

## 1. Two families, and the owner called it

**Owner's observation, 2026-08-14:** the black quads in the Kamadan render are
portals, and there is more than one kind — one for Prophecies/Factions and one
for Nightfall/Eye of the North. Both are confirmed from the archive, and the
second half is what stops a census keyed to one texture from missing half the
game.

| family | texture | image | models |
|---|---|---|---|
| **Prophecies / Factions** | `0x605E` | 128×128, blue-violet swirl, 16% fully transparent | `0xA825`, `0xE723`, `0x858B`, `0x21E82` |
| **Nightfall / EotN** | `0x28892` | 256×256, grey-white radial vortex, 35% fully transparent | `0x35140`, `0x2889A`, `0x33545` |

**Seven models in total**, found by scanning the `0x00000FA5` texture list of
every one of the **8,420** distinct prop models the corpus references (313 s;
no geometry decode needed, which is what makes it affordable). The families are
DISJOINT — no model references both textures.

`0xA825` is the workhorse: 22 triangles over 6 sub-models, in **152 maps** with
504 placements.

## 2. The census

Read from every map's Bloated props chunk `0x20000004` plus its dependency list
`0x21000004` — again no geometry decode, so all 346 readable map heads were
swept in 538 s.

```
346 maps swept
  with at least one portal   175  (50.6%)
  with none                  171
  total portal placements    656
```

**By family, in maps:**

| | maps |
|---|---|
| Prophecies/Factions only | 158 |
| Nightfall/EotN only | 14 |
| **both families in one map** | **3** |

The three mixed maps are the interesting rows and are not explained here.

**Portals per map**, over the 175 that have any: 1 → 35 maps, 2 → 22, 3 → 39,
4 → 25, 5 → 24, 6 → 9, 7 → 7, 8 → 5, 9 → 7, 11 → 1. The largest is map row
`0x8A1B` with **23**.

**The Nightfall count is low and that is a property of this ARCHIVE, not of the
game**: it holds 349 map heads against retail's several hundred more, so
absence here is not absence in Guild Wars. Treat 14 as a floor.

## 3. The control, and it is only suggestive

A portal is an exit, so it should sit nearer the map boundary than an ordinary
prop. Scored as distance to the nearest Map Parameters rect edge, normalised so
0.0 is the boundary and 1.0 the centre, with four random non-portal props
sampled per portal from the same maps:

| | n | median | under 0.25 |
|---|---|---|---|
| portals | 656 | **0.307** | 37.8% |
| other props | 2,624 | 0.449 | 24.2% |

**It points the right way and it is NOT decisive**, and the honest reading is
that the identification rests on the TEXTURE — a radial vortex is not
ambiguous — with this as weak corroboration. Two reasons it is weak are known:
the Map Parameters rect includes unwalkable margin, so "distance to the rect
edge" is not "distance to the playable edge"; and some portals are interior
(instanced-area entrances), which are not near any boundary by design. A
sharper version would measure against the navmesh's walkable bounds
(`pathmap.py`), which was not run here.

## 4. What this does NOT establish

- **Where a portal leads.** The destination is not in the prop record. The
  props chunk carries model, position, rotation, scale, flags and an outline —
  nothing that names another map.
- **That every map link is a portal prop.** 171 of 346 maps have none, and
  missions, cinematics and instanced areas plainly still connect to the world.
  Some transitions are certainly server-side or scripted.
- **What the two families MEAN.** They are named for the campaigns whose maps
  carry them, from the owner's identification and the corpus split; nothing
  here reads a campaign id out of a file.
- **The three mixed maps.** Not investigated.

## 5. Reproducing it

Three steps, none needing a geometry decode:

1. **Portal textures** — the two above, from the exported PNGs.
2. **Portal models** — for every prop model file id in the corpus, read
   `modelfile.ModelFile.texture_refs()` and keep those referencing a portal
   texture.
3. **Census** — for every map head (`flags == 259`), decode
   `props.BloatedProps` from `0x20000004` and resolve `record.model` through
   the `0x21000004` dependency list; count the records whose model is a portal
   model.

The intermediate JSON this run produced is in the session scratchpad, not the
vault, because it is a derived index rather than an artifact anything depends
on — re-running the three steps is cheaper than storing it.
