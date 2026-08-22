r"""Rung G: one command from `content/` to a map you can walk around.

    python toolkit/mapdata/deploy.py --area plaza
    python toolkit/mapdata/deploy.py --area plaza --blend scene.blend
    python toolkit/mapdata/deploy.py --area plaza --install --dat <copy>
    python toolkit/mapdata/deploy.py --area plaza --install --launch --dat <copy>

Everything under this was proved one rung at a time and then driven by a
bespoke script per rung, living in the vault. That is how research should go
and it is not a pipeline: nine scripts that each hard-code a row index, a
donor and a file path are nine places to get it wrong. This is the same ladder
with the numbers pulled out into `content/areas.toml`.

WHAT IT DOES, in order, refusing rather than continuing at each step:

  1. GEOMETRY.  A named generator, or `--blend` for a real Blender scene, which
     is run headless through `tools/blender/export_gwmap.py` and read back as a
     terrain interchange. Either way the field is SNAPPED onto the terrain
     codec's own lattice before anything else -- a freely authored height is
     essentially never representable (the transform's determinant is 8 per
     axis), and a builder that quantises silently loses the difference between
     "the artist put a hill here" and "the codec moved it".
  2. BORROW.  Textures, sun, environment and sound are read from ONE donor map
     in the owner's archive AT RUN TIME, never stored in this repo. One donor
     rather than four keeps the result coherent.
  3. ASSEMBLE.  `stripbuild.build`, which is where every earlier rung's proof
     now lives.
  4. VERIFY, offline and before any archive is touched: the map round-trips,
     the seed stands on walkable ground, the spawn lands in exactly ONE
     trapezoid of the mesh we authored, and the file fits the row's reservation
     -- judged on the bytes that will actually be STORED, which since
     2026-08-20 are compressed ones. A run WITHOUT `--install` says which row
     the stream would go into as well, including "none, this id binds nothing
     and would be created": a dry run whose output cannot tell those apart is
     one nobody can compare against a prediction.
  5. INSTALL (`--install`).  Resolve the row BY FILE ID, write the map into the
     Stripped partner as a compression-8 stream (`--stored-install` for the old
     uncompressed shape), arm the Bloated head to zero length so the client must
     recompile. Journalled; refuses `vault/dat_study` like every other writer.
     OR CREATE IT: when the area's map row carries `created = true` and its file
     id binds nothing, deploy allocates the chain instead of displacing a retail
     one -- two rows under a new id via `datalloc`, the head born empty. That is
     WORLDMAPS-W3; whether a retail client compiles a map from a chain it has
     never seen is WORLDMAPS-W4 and is a client question, not an offline one.
     An area may also declare `reserve_bytes`, the reservation its row is
     entitled to: creation asks the allocator for that many blocks instead of
     just enough, and a later install into THAT row -- the one we created --
     that outgrows its current reservation grows back into them in place
     rather than relocating (WORLDMAPS-W5). The archive records no such number
     anywhere, which is why the AREA states it and every run prints it; and a
     row ArenaNet made is never grown on the strength of it, because what that
     row was given is not ours to state.
  6. LAUNCH (`--launch`).  The harness, pointed at the area's own map id --
     which is a thing worth writing down, because a harness PASS means "the
     client reached A map", and pointing it at the wrong one produced two runs
     that looked green while compiling nothing (FINDINGS 54).
  7. READ BACK.  The compiled head, compared against what we authored.

WHAT IT IS NOT. It is not a hot reload: the client compiles a map when it
loads one, so "iterate" means run this again. It does not write to the owner's
install, and it cannot -- `datwrite` refuses anything but a copy.
"""

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from archive import (Archive, ENTRY_SIZE, file_id_table,  # noqa: E402
                     COMPRESSION_HUFFMAN, COMPRESSION_STORED, FILE_ID_HIGH_BIT)
import content as content_mod  # noqa: E402
import datalloc  # noqa: E402  -- the third verb: rows that did not exist
import datcheck  # noqa: E402  -- the launch-side archive gate
import datwrite  # noqa: E402  -- for the grow gate's TOKEN, never to write
import envchunk  # noqa: E402
import gwenc  # noqa: E402  -- the compression-8 encoder
import mapchunks  # noqa: E402
import mapexport  # noqa: E402
import mapfile as mfile  # noqa: E402
import pathchunk  # noqa: E402
import pathmap  # noqa: E402
from props import Prop, StrippedProps  # noqa: E402
import soundchunk  # noqa: E402
import stripbuild as sb  # noqa: E402
import strippedterrain as stx  # noqa: E402
import terrain as trn_mod  # noqa: E402
import vaultpath  # noqa: E402

TERRAIN_DEPS = 0x11000002
ENV, ENV_DEPS = 0x10000009, 0x11000009
SOUND, SOUND_DEPS = 0x10000012, 0x11000012
PROPS_CHUNK = 0x10000004

# The terrain chunk's sun byte and the environment chunk's are two quantisations
# of one authored angle, at a ratio of exactly 127/32 (FINDINGS 55). A map that
# sets one and not the other has a baked lightmap and a runtime sky pointing in
# different directions, which is what every rung before (e10i) shipped.
SUN_RATIO = 127.0 / 32.0


class Refused(Exception):
    """A stage refused. The message says which and why."""


# ------------------------------------------------------------- geometry

def gen_flat(dim, h=-13):
    return [h] * (dim * dim)


def gen_plaza(dim, base=-13):
    """A flat apron, a low rise to one side, a dip to the other.

    Deliberately gentle: every slope here is inside the walkable band measured
    in FINDINGS 48 (the boundary is 35 degrees), so the shape is about proving
    the pipeline rather than about re-testing the classifier.
    """
    out = [0] * (dim * dim)
    mid = dim // 2
    for gy in range(dim):
        for gx in range(dim):
            d = max(abs(gx - mid), abs(gy - mid))
            if d <= 5:
                h = base                      # the plaza itself, dead flat
            elif gx > mid:
                h = base - 8 * (d - 5)        # a rise (heights are negated)
            else:
                h = base + 4 * (d - 5)        # a shallow dip
            out[trn_mod.Terrain.index(gx, gy, dim)] = h
    return out


# FINDINGS 48's ramp, carried over verbatim from the run that measured the
# slope boundary (`vault/research/e10e-threshold-2026-08-12/build_ramp.py`,
# 2026-08-12). It is here rather than in the vault because WORLDMAPS-W17 varies
# the slope SET and needs the same ruler FINDINGS 48 used -- a re-derived ramp
# would make the two runs incomparable for a reason that has nothing to do with
# the flag.
#
# Five 6-cell strips whose snapped interior slopes bracket every candidate
# cutoff of BOTH threshold sets (10/45/40 and 15/35/30), so the pattern of which
# strips compile walkable names the set outright. A flat apron carries the seed
# and spawn; a flat plateau sits atop each strip -- and the plateau is not
# decoration: FINDINGS 48's second result is that walkable area is
# CONNECTIVITY-PRUNED from the flood seed, so a plateau above a too-steep ramp
# vanishes from the mesh entirely and repeats its ramp's verdict.
RAMP_APRON_TOP = 14      # gy >= this is flat apron at the base height
RAMP_TOP = 4             # gy in [RAMP_TOP, RAMP_APRON_TOP) rises northward
RAMP_STRIPS = (          # (label, dz per 96-unit cell, gx range inclusive)
    ("28.0 deg", 51, (1, 6)),
    ("32.0 deg", 60, (7, 12)),
    ("36.9 deg", 72, (13, 18)),
    ("41.9 deg", 86, (19, 24)),
    ("47.0 deg", 103, (25, 30)),
)


def gen_ramp(dim, base=-13):
    """Five ramps of increasing slope, an apron, and a plateau on each.

    32x32 only. The band rows and the strip columns are tuned to that size --
    APRON_TOP 14 and RAMP_TOP 4 are cell indices, not fractions -- and silently
    rescaling them would change the angles, which are the whole measurement.
    """
    if dim != 32:
        raise Refused(
            f"the ramp field is 32x32 by construction, not {dim}x{dim}: its "
            f"band rows (apron at gy>=14, ramp over gy 4..13) and its five "
            f"6-cell strips are cell indices from FINDINGS 48, and rescaling "
            f"them would move the very angles the map exists to measure")
    rise_cells = RAMP_APRON_TOP - RAMP_TOP
    out = [0] * (dim * dim)
    for gy in range(dim):
        for gx in range(dim):
            dz = 0
            for _label, d, (a, b) in RAMP_STRIPS:
                if a <= gx <= b:
                    dz = d
                    break
            if gy >= RAMP_APRON_TOP:
                lift = 0                       # the apron, flat, holds the seed
            elif gy >= RAMP_TOP:
                lift = dz * (RAMP_APRON_TOP - gy)
            else:
                lift = dz * rise_cells         # the plateau atop the strip
            out[gy * dim + gx] = base - lift   # more negative is HIGHER
    return out


# WORLDMAPS-W20's ramp: the same field as `gen_ramp` with five different
# slopes, chosen to BISECT the 45-degree cut rather than bracket it.
#
# Every dz is a MULTIPLE OF 4, and that is not cosmetic. MEASURED 2026-08-21:
# the codec's lattice snap leaves a multiple-of-4 dz EXACT (spread 0.00 across
# the whole ramp band), while the odd values between them spread 0.3-0.6 deg --
# and a strip whose own slope is uncertain by half a degree cannot bisect a cut
# to better than that. `gen_ramp`'s strips spread by up to 1.4 deg for exactly
# this reason, which is why WORLDMAPS-W19 could only bracket the cut to
# [42.51, 46.45].
#
# STRIPS CHOSEN 2026-08-21 AFTER A FAILED POSITIVE CONTROL. The first fine
# map ran 43.78/45.00/46.17/47.29 and compiled to the APRON ALONE -- pattern
# '....', 2 trapezoids -- because 43.78 was assumed to be comfortably below
# a 45-degree cut and is not: WORLDMAPS-W17 measured 41.52-42.51 WALKABLE and
# this map measured 43.78 EXCLUDED, so the cut sits in (42.51, 43.78) and the
# control was above it. These four now bracket that interval from BELOW, with
# two strips W17 already proved walkable.
#
# The last strip is dz 96 = atan(96/96) = EXACTLY 45.00 degrees, the threshold
# value itself. The classifier excludes on `slope > array[1]` -- strictly
# greater -- so a slope sitting exactly on the cut should be WALKABLE, and no
# map this project has built has ever put a slope there.
# FOUR strips of EIGHT columns, aligned to the codec's 4x4 sub-blocks.
# `snap_block` projects each 4x4 sub-block independently, so a strip boundary
# falling INSIDE one quantises the whole block: the first draft used five
# 6-wide strips at gx 1..30, every boundary landed mid-sub-block, worst sample
# moved 3, and only ONE column of the 45.00 strip survived exact -- its
# neighbours reached 45.59 and would have been excluded, which is precisely
# the ambiguity this map exists to remove. Aligned: worst sample moved 0 and
# EVERY interior column is exact.
RAMP_FINE_STRIPS = (
    ("18.43 deg", 32, (0, 7)),       # <- CANNOT-FAIL CONTROL: below BOTH cuts
                                     #    (35 and 45). If this is excluded the
                                     #    map is broken, not the threshold.
    ("42.51 deg", 88, (8, 15)),       # <- W17 strip 4's top value, walkable there
    ("43.78 deg", 92, (16, 23)),      # <- MEASURED EXCLUDED at cut 45, 2026-08-21
    ("45.00 deg", 96, (24, 31)),      # <- exactly the threshold float
)


def gen_ramp_fine(dim, base=-13):
    """`gen_ramp`'s shape with five slopes straddling 45.00 degrees exactly."""
    if dim != 32:
        raise Refused(
            f"the fine ramp is 32x32 by construction, not {dim}x{dim}: its band "
            f"rows and its five 6-cell strips are cell indices, and rescaling "
            f"them would move the angles the map exists to resolve")
    rise_cells = RAMP_APRON_TOP - RAMP_TOP
    out = [0] * (dim * dim)
    for gy in range(dim):
        for gx in range(dim):
            dz = 0
            for _label, d, (a, b) in RAMP_FINE_STRIPS:
                if a <= gx <= b:
                    dz = d
                    break
            if gy >= RAMP_APRON_TOP:
                lift = 0
            elif gy >= RAMP_TOP:
                lift = dz * (RAMP_APRON_TOP - gy)
            else:
                lift = dz * rise_cells
            out[gy * dim + gx] = base - lift
    return out


GENERATORS = {"flat": gen_flat, "plaza": gen_plaza, "ramp": gen_ramp,
              "ramp_fine": gen_ramp_fine}


def heights_from_blend(blend, dim, blender=None, workdir=None):
    """Run the Blender exporter headless and read the interchange back."""
    from test_blenderimport import find_blender
    exe, why = (blender, "given") if blender else find_blender()
    if exe is None:
        raise Refused("no Blender found; pass --blender or use a generator")
    exporter = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                            "tools", "blender", "export_gwmap.py")
    outdir = workdir or os.path.join(os.path.dirname(blend), "_gwmap")
    os.makedirs(outdir, exist_ok=True)
    cmd = [exe, "--background", "--factory-startup", "--python-exit-code", "66",
           "--python", exporter, "--", "--blend", blend, "--out", outdir,
           "--name", "deploy"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise Refused(f"Blender export failed (rc {proc.returncode}):\n"
                      f"{(proc.stdout + proc.stderr)[-1500:]}")
    js = [f for f in os.listdir(outdir)
          if f.endswith(".json") and f != "manifest.json"]
    if len(js) != 1:
        raise Refused(f"expected one interchange json in {outdir}, found {js}")
    meta = json.load(open(os.path.join(outdir, js[0]), encoding="utf-8"))
    side = next(s for s in meta["sidecars"] if s["kind"] == "heights")
    blob = open(os.path.join(outdir, side["name"]), "rb").read()
    vals = list(struct.unpack("<%df" % (len(blob) // 4), blob))
    if len(vals) != dim * dim:
        raise Refused(f"{len(vals)} samples exported, area declares {dim}x{dim}"
                      f" = {dim * dim}")
    # A BRUSH PRODUCES FRACTIONS, and refusing them refuses the workflow this
    # command exists for. The first version raised here -- correct while the
    # only producer was a Python generator emitting integers, and wrong the
    # moment a real sculpt arrived: 1,010 of 4,225 vertices of the first
    # Blender scene came back non-integer, which is simply what moving a vertex
    # with a falloff does. So round, and REPORT, exactly as the lattice snap
    # does. The residual is <= 0.5 against a 96-unit cell pitch, and the snap
    # that follows moves samples by up to 3 anyway.
    if any(v != v or v in (float("inf"), float("-inf")) for v in vals):
        raise Refused("a non-finite height (NaN or inf) reached the exporter; "
                      "there is no value to round it to")
    ints = [round(v) for v in vals]
    worst = max((abs(i - v) for i, v in zip(ints, vals)), default=0.0)
    frac = sum(1 for i, v in zip(ints, vals) if float(i) != v)
    # world row-major -> the codec's tiled order
    return mapexport.retile(ints, dim, dim), exe, why, worst, frac


# --------------------------------------------------------------- borrow

def _donor_row(archive, area, what, id_key, row_key, default_row=None):
    """Which row `what` comes from IN THIS ARCHIVE, resolved by file id.

    A row index is meaningful only against the copy it was measured on
    (`mapchunks.py`:117), and build 38833 collected on that: the update recycled
    row 7982, so every area row named a 46,556-byte non-map (flags 3) as its
    biome donor while Pre-Searing Ascalon itself sat unharmed at row 177262.
    `_stripped_of` fails closed, so this was a refusal rather than a wrong map
    -- and a refusal on all three areas against any current archive.

    The pinned index survives as a CROSS-CHECK that prints when it disagrees,
    never as the lookup -- the same demotion `asserts.py` and `msgshape.py` gave
    their VAs. Disagreement is expected on any archive but 38797; what would not
    be acceptable is not knowing which row you got.
    """
    fid = area.get(id_key)
    pinned_row = area.get(row_key, default_row)
    if fid is None:
        if pinned_row is None:
            raise Refused(f"area names neither {id_key} nor {row_key} for {what}")
        print(f"  {what}: row {int(pinned_row)} (no {id_key}; an index alone, "
              f"which is only valid against build 38797's archive)")
        return int(pinned_row)
    row = file_id_table(archive).get(int(fid))
    if row is None:
        raise Refused(
            f"{what} file id 0x{int(fid):X} binds to no row in this archive. "
            f"That is the PORTABLE key, so this is a real absence rather than a "
            f"stale index -- check which archive generation you are installing "
            f"into before editing content.")
    if pinned_row is not None and int(pinned_row) != row:
        print(f"  {what}: file id 0x{int(fid):X} -> row {row} "
              f"(pinned {int(pinned_row)} is 38797's answer; this archive differs)")
    else:
        print(f"  {what}: file id 0x{int(fid):X} -> row {row}")
    return row


def _stripped_of(archive, head_row, what):
    mi = mapchunks.MapIndex(archive)
    head = next((h for h, _p in mi.pairs if h.index == head_row), None)
    if head is None:
        raise Refused(f"{what} row {head_row} is not a map head in this archive")
    return mfile.MapFile.decode(archive.read(mi.partner(head)), strict=False)


class Donor:
    """What a map lends, read once -- and it lends TWO different kinds of thing.

    THE STRUCTURAL CONSTANTS (`constants_row`) are Header and Zones, and they
    must come from a map SHAPED LIKE OURS. That is not a style point: Zones is
    per-map, and Pre-Searing's is 7,208 bytes against the 32x32 reference map's
    34. Taking constants from the biome donor built an 11,115-byte map for a
    4,608-byte reservation on the first run of this command -- the tool caught
    it, but the schema had invited it, so the two rows are separate fields now.

    THE BIOME (`head_row`) is everything a map wears: terrain textures, the sun
    angle, the environment chunk, the sound chunk, the prop models. Those are
    the parts that should come from one place so the result is coherent.
    """

    def __init__(self, archive, head_row, constants_row):
        self.stripped = _stripped_of(archive, head_row, "donor")
        cs = (self.stripped if constants_row == head_row
              else _stripped_of(archive, constants_row, "constants"))
        self.constants = {cid: cs.find(cid).payload() for cid in sb.BORROWED}
        self.constants_row = constants_row
        trn = stx.StrippedTerrain.decode(self.stripped.find(sb.TERRAIN).payload())
        self.angle_index = trn.angle_index
        self.table_a = bytes(trn.table_a)
        self.table_b = bytes(trn.table_b)
        self.tex_word = trn.tex_word
        d = self.stripped.find(TERRAIN_DEPS)
        self.terrain_dep_ids = list(
            mapchunks.decode_dependencies(d.payload()).file_ids) if d else []
        self.env = self._pair(ENV, ENV_DEPS)
        self.sound = self._pair(SOUND, SOUND_DEPS)
        self.prop_model_ids = self._prop_models()

    def _pair(self, cid, did):
        c, d = self.stripped.find(cid), self.stripped.find(did)
        if c is None or d is None:
            return None
        return (c.payload(),
                list(mapchunks.decode_dependencies(d.payload()).file_ids))

    def _prop_models(self):
        c = self.stripped.find(0x11000004)
        return list(mapchunks.decode_dependencies(c.payload()).file_ids) if c else []


# ---------------------------------------------------------------- build

def pick_tree_cells(heights, dim, n, seed_cell, pitch=96.0):
    """Deterministic farthest-point pick over FLAT cells, away from the seed.

    Flat matters: a prop on a corner-spread cell sits visibly off the ground,
    and the (e10-next) driver refused its own hard-coded list for exactly that.
    """
    flat = []
    for gy in range(1, dim - 1):
        for gx in range(1, dim - 1):
            hs = [heights[trn_mod.Terrain.index(gx + dx, gy + dy, dim)]
                  for dx in (0, 1) for dy in (0, 1)]
            if max(hs) - min(hs) <= 12 and (gx, gy) != seed_cell:
                flat.append((gx, gy))
    if not flat:
        return []
    picked = [flat[len(flat) // 2]]
    while len(picked) < n and len(picked) < len(flat):
        best, bestd = None, -1
        for c in flat:
            if c in picked:
                continue
            d = min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 for p in picked)
            if d > bestd:
                best, bestd = c, d
        if best is None:
            break
        picked.append(best)
    return picked[:n]


def assemble(area, heights, donor, dim, verbose=True):
    """Everything the area declares, into one Stripped map."""
    seed = (float(area["seed_x"]), float(area["seed_y"]))
    kw = dict(constants=donor.constants, dep_ids=donor.terrain_dep_ids)

    if area.get("textures", True):
        kw.update(table_a=donor.table_a, table_b=donor.table_b,
                  tex_word=donor.tex_word)
    if area.get("sun", True):
        kw["angle_index"] = donor.angle_index
    if area.get("environment", True):
        if donor.env is None:
            raise Refused("area asks for environment, donor carries none")
        payload, ids = donor.env
        if area.get("sun", True):
            # keep the two suns in step -- see SUN_RATIO
            ec = envchunk.EnvChunk.decode(payload)
            want = int(round(donor.angle_index / SUN_RATIO))
            g = bytearray(ec.global_env())
            if g[16] != want:
                g[16] = want
                ec.section(envchunk.TAG_GLOBAL).records[0] = bytes(g)
                payload = ec.encode()
                if verbose:
                    print(f"  sun: env byte adjusted to {want} to match "
                          f"terrain angle_index {donor.angle_index}")
        kw.update(env_payload=payload, env_dep_ids=ids)
    if area.get("sound", True):
        if donor.sound is None:
            raise Refused("area asks for sound, donor carries none")
        kw["sound_payload"], kw["sound_dep_ids"] = donor.sound

    n_trees = int(area.get("trees", 0) or 0)
    if n_trees:
        if not donor.prop_model_ids:
            raise Refused("area asks for trees, donor lists no prop models")
        seed_cell = (int(seed[0] // 96.0), int(seed[1] // 96.0))
        cells = pick_tree_cells(heights, dim, n_trees, seed_cell)
        if len(cells) < n_trees:
            raise Refused(f"only {len(cells)} flat cells for {n_trees} trees")
        # An area may give its props a FOOTPRINT. `outline` is prop-LOCAL
        # (i16 dx, i16 dy); the compiler rewrites it into the Bloated stream in
        # world coordinates. Absent, it is empty -- which is what every prop
        # this project placed before 2026-08-21 carried, and which is also what
        # the MAJORITY of retail props carry (Kamadan: 516 props, 280 outline
        # points between them). A square is used rather than a circle because
        # the footprint is a closed ring of integer offsets and four corners
        # plus the repeat is the smallest honest one; `Prop.closed` wants the
        # first point repeated last, as 37,505 of retail's 37,548 outlined
        # props do.
        r = int(area.get("prop_outline", 0) or 0)
        ring = ()
        if r:
            ring = ((-r, -r), (r, -r), (r, r), (-r, r), (-r, -r))
        props = []
        for gx, gy in cells:
            z = float(heights[trn_mod.Terrain.index(gx, gy, dim)])
            props.append(Prop(model=0, x=gx * 96.0 + 48.0, y=gy * 96.0 + 48.0,
                              z=z, rot=(0, 0, 0), scale=0x7F, flags=0,
                              outline=ring))
        kw["props"] = StrippedProps(props=props, refs4=[], refs6=None)
        kw["prop_dep_ids"] = [donor.prop_model_ids[0]]
        if verbose:
            print(f"  props: {len(props)} at {cells}"
                  + (f", each with a {2 * r}x{2 * r} footprint "
                     f"({len(ring)} points)" if r else ", no footprint"))

    # The area may state the Map Parameters flags dword. Absent, it is 0 --
    # which is what every area before WORLDMAPS-W11 shipped. See
    # stripbuild.build's own note: bit 0 gates the navmesh depth bound, and the
    # top byte selects the slope set, so a row setting one must not disturb the
    # other.
    kw["map_flags"] = int(area.get("map_flags", 0) or 0)
    return sb.build(dim, dim, heights, seed, **kw)


# --------------------------------------------------------------- verify

def verify(report, area, heights, dim, reservation=None, install_size=None,
           compression=COMPRESSION_STORED):
    """Refuse before the archive is touched. Returns a list of finding strings.

    `install_size` is the length of the bytes that will actually OCCUPY the row
    -- the compressed stream, unless `--stored-install`. It defaults to the
    blob's own length so a caller that has not compressed yet still gets the old
    preview. `compression` is carried only so the note can NAME which of the two
    sizes it judged: a preview that says "fits" without saying "fits as what" is
    the kind of line a later reader assumes the wrong meaning of, and the two
    numbers differ by 7.7x on a 96x96 map.
    """
    notes = []
    size = len(report.blob) if install_size is None else install_size
    how = "compression 8" if compression == COMPRESSION_HUFFMAN else "stored"
    back = mfile.MapFile.decode(report.blob)

    trn = stx.StrippedTerrain.decode(back.find(sb.TERRAIN).payload())
    same = sum(1 for a, b in zip(trn.heights, heights) if a == b)
    if same != len(heights):
        raise Refused(f"terrain round trip lost {len(heights) - same} of "
                      f"{len(heights)} samples -- the field was not on the "
                      f"codec's lattice and something quantised it silently")
    notes.append(f"terrain round trip {same}/{len(heights)} samples exact")

    # The STRIPPED path chunk is the compiler's INPUT and carries only the
    # boundary polygon -- the mesh is what the client builds FROM it, so the
    # spawn-in-one-trapezoid test cannot run here. It runs in readback(),
    # against the mesh the client produced. Decoding with the Bloated codec
    # would raise, and the two codecs refuse each other's bytes on purpose.
    sp = pathchunk.StrippedPath.from_chunk(back.find(sb.PATH).payload())
    notes.append(f"authored path chunk {len(back.find(sb.PATH).payload())} B, "
                 f"{len(sp.boundary)} boundary point(s), seq {sp.sequence}")
    if not sp.boundary:
        raise Refused("the authored path chunk carries no boundary point; the "
                      "client's flood fill has no seed and will build no mesh")

    # NOT a refusal any more, and the change is the point: over-reservation used
    # to be fatal because `datwrite` is the only writer that fits in place. The
    # install path relocates instead when it must, so size selects a VERB rather
    # than ending the run.
    #
    # AND THE SIZE IT JUDGES IS THE STORED ONE. This used to read len(report.blob)
    # unconditionally, which was the same number the row would hold; it is not any
    # more, and a preview computed on the plaintext would disagree with the verb
    # the install then picks -- exactly the "the plan said one thing and the run
    # did another" shape the readback below exists to catch after the fact.
    if reservation is None:
        notes.append(f"{size} B ({how})")
    elif size <= reservation:
        notes.append(f"{size} B ({how}) fits the {reservation} B "
                     f"reservation -- replace in place")
    else:
        notes.append(f"{size} B ({how}) exceeds the {reservation} B "
                     f"reservation -- install will RELOCATE the row")
    notes.append(f"{report.generated} B generated, {report.borrowed} B borrowed "
                 f"({100.0 * report.generated / max(1, len(report.blob)):.2f}% ours)")
    return notes


# -------------------------------------------------------------- install

def install_bytes(blob, stored=False):
    """The bytes that will actually OCCUPY the row. -> (stream, code, note).

    RETAIL'S OWN STRIPPED PARTNERS ARE COMPRESSION 8. Ours were stored, and that
    was the deviation rather than the shape -- readable (FINDINGS 35-58 are all
    on stored partners) but not what the client is shipped. It was also the
    ceiling: `datwrite --replace` fits a payload into the row's existing
    whole-block reservation or refuses, so an authored map had to be smaller
    UNCOMPRESSED than whatever ArenaNet had compressed into the same row. That
    is what capped every map this toolkit built at 32x32.

    THE GAIN IS MEASURED, EVERY RUN, AND NEVER ASSUMED. It is not a constant of
    the format: only tag 1 of the terrain chunk is entropy-coded, and the rest of
    an authored map -- tile indices, the bit field, the two tables, props, path
    and both deps chunks -- is raw and, on a generated shape, extremely
    repetitive. MEASURED on `gen_plaza` against build 38797's donors, 2026-08-20:

        32x32   3,941 B -> 1,316 B   (33.4%)
        64x64  10,654 B -> 2,012 B   (18.9%)
        96x96  21,786 B -> 2,828 B   (13.0%)

    against map 143's 4,608 B partner reservation -- so 96x96 now REPLACES in
    place where 32x32 was previously the largest that fit at all. Those are
    figures for one generator on one donor, which is why the note is printed
    rather than the numbers being relied upon.

    `gwenc.encode` keeps its `verify=True` default: it round-trips the stream
    through `gwdat.decompress` and raises before returning if the result is not
    the input. That is the same "refuse before the archive is touched" the whole
    command is built on, and the failure it catches is silent -- a stream one
    word short decodes SHORT rather than raising, and every checksum an archive
    applies is over the stored bytes.
    """
    if stored:
        return blob, COMPRESSION_STORED, (
            f"stored install: {len(blob)} B uncompressed, no gwenc -- the shape "
            f"every map this command installed before 2026-08-20")
    stream = gwenc.encode(blob)
    return stream, COMPRESSION_HUFFMAN, (
        f"compressed install: {len(blob)} B authored -> {len(stream)} B "
        f"compression 8 ({100.0 * len(stream) / len(blob):.1f}% of stored, "
        f"{len(blob) - len(stream)} B saved)")


def spill_stream(here, tag, stream, compression):
    """Write the exact bytes the ROW will hold, beside the archive. -> path|None

    `install_partner` HAS to: `datwrite` and `datmove` take `--data FILE` and a
    compressed stream exists only in memory until something writes it down.
    `create_chain` does NOT -- it hands `datalloc` the bytes directly -- and that
    asymmetry is why this is a function rather than four lines inside the writer's
    arm. It spilled on one path and not the other, so `<area>.c8.bin` existed
    after an install and not after a create, which is backwards: THE CREATE PATH
    IS THE ONE WHERE THESE BYTES ARE OTHERWISE UNRECOVERABLE. After an install
    the row can be read back and decompressed at any time; a created chain that
    the client then rewrites, deletes or refuses leaves no copy of the stream
    `gwenc` produced from this run's blob, and a red arm in WORLDMAPS-W4 has to
    be able to point at exactly what was handed over.

    A STORED WRITE SPILLS NOTHING, on purpose. For compression 0 the stream IS
    the plain payload, already written to `<area>.bin`; a second identical file
    beside it is one more thing that can drift out of step with the first.
    """
    if compression == COMPRESSION_STORED:
        return None
    path = os.path.join(here, f"{tag}.c8.bin")
    with open(path, "wb") as fh:
        fh.write(stream)
    print(f"  wrote {path}")
    return path


# THE FALLBACK JOIN, and only the fallback since 2026-08-20. A fragment of each
# of `_grow_gate`'s four sentences, in its order. `datwrite` now names its own
# refusals -- `GrowGateRefused`, carrying a `condition`, and one
# `GROW-GATE-REFUSED condition=<name>` line per refusal on the CLI -- so this
# list is what recognises an OLDER writer: a vault copy, a bisect, a subprocess
# resolved off a stale worktree. Keep it in step with the sentences; do not add
# to it as a way of recognising anything new. See `grow_gate_refusal`.
GROW_GATE_MARKERS = (
    "is CLAIMED by",                            # condition 1: other claimants
    "PAST THE END",                             # condition 2: EOF
    "LIVE MASTER FILE TABLE",                   # condition 3: the live MFT
    "datplan WITHHOLDS",                        # condition 4: a withheld run
)


def grow_gate_refusal(text):
    """The `_grow_gate` refusal inside a writer's output, or None.

    THE POINT IS TO TELL TWO FAILURES APART, and the reason it matters is that
    only one of them may be followed by a relocation. `datwrite --replace
    --grow-to` exits non-zero for the grow gate (some other row claims the
    blocks this one freed; the range runs past EOF, into the live MFT, or into a
    container generation `datplan` withholds) and ALSO for every ordinary
    reason -- a bad declaration, a missing file, a refused archive. Falling back
    to `datmove` on the first kind is correct and is what the row's own budget
    is for; falling back on the second would turn "these bytes are not what you
    declared" into a relocation that quietly succeeds.

    THE JOIN IS NOW TYPED, and this paragraph used to explain why it could not
    be. It said: "the recogniser is a fixed list of the gate's own four
    sentences rather than `rc != 0` ... Matching on message text is a weak join
    and it is named as one: if `datwrite`'s wording moves, this returns None and
    the install REFUSES, which is the safe direction." The direction was right
    and the join was still prose -- a reworded sentence turned every claimant
    conflict on this path into a refused install, silently, for a reason that
    has nothing to do with the archive. `datwrite._grow_gate` now raises
    `GrowGateRefused`, a `SystemExit` carrying a `condition`, and its CLI prints
    ONE machine-readable line per refusal: `GROW-GATE-REFUSED condition=<name>`.
    That line is what this joins on.

    THE FOUR SENTENCES REMAIN, DOCUMENTED AS THE FALLBACK. An older `datwrite`
    -- a vault copy, a bisect, a subprocess resolved off a stale worktree --
    prints no token at all, and a fallback that refused there would be this
    function's own failure mode in the other direction. So: token present is the
    verdict; token absent falls back to `GROW_GATE_MARKERS`; neither is None and
    the caller raises. The line RETURNED is the human sentence whenever there is
    one, because it is what gets printed and what an operator has to read; the
    token is the decision, not the report.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    worded = next((ln for ln in lines
                   if any(m in ln for m in GROW_GATE_MARKERS)), None)
    typed = next((ln for ln in lines
                  if datwrite.GROW_GATE_TOKEN in ln), None)
    if typed is None and worded is None:
        return None
    return worded or typed


def area_reserve(area):
    """The area row's `reserve_bytes`, or 0. -> int

    WHERE CONTENT BECOMES A NUMBER, which is the place to refuse a bad one. The
    field is optional and absent means 0 -- every area row said that before
    WORLDMAPS-W5 and three of them still do. What it may NOT be is almost a
    number: TOML will hand back `2048.5` or `-512` as happily as `8192`, and
    both of those travel a long way before anything notices. `int()` on the
    first truncates silently, so the run would reserve 2,048 while the row says
    2,048.5; the second is falsely truthy and would print "past the -512 B this
    area declares".

    `datalloc.Stream` refuses both, but only on the CREATE path -- the install
    path never builds a Stream, so a fraction there would reach `--grow-to` as
    an argparse type error out of a subprocess. Asking here covers both
    directions and names the file the operator has to edit.
    """
    raw = area.get("reserve_bytes", 0)
    if raw is None:
        return 0
    # BOOLS BOTH WAYS. `True` is an int in Python and would sail through as a
    # 1-byte budget; refusing only that one would leave `false` meaning 0, which
    # is a second spelling of absent and one more thing to read.
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise Refused(
            f"this area's `reserve_bytes` is {raw!r}, which is not a whole "
            f"number of bytes.\n"
            f"  A reservation is counted in bytes and rounded up to whole "
            f"512-byte blocks by the allocator. Edit the row in "
            f"content/areas.toml, or drop the field to state no budget.")
    if raw < 0:
        raise Refused(
            f"this area's `reserve_bytes` is {raw}, and a negative reservation "
            f"is not a budget.\n"
            f"  Drop the field from the row in content/areas.toml to state no "
            f"budget: absent is 0, which is the behaviour every area row had "
            f"before WORLDMAPS-W5.")
    return raw


def budget_note(size, reservation, reserve, created=False):
    """What a DECLARED budget does to the verb `verify` just predicted. -> str|None

    `verify` compares the stream against the row's CURRENT reservation and says
    "fits" or "will RELOCATE", which is the whole truth for a row with no
    declared entitlement. For a row that has one, the middle case exists and the
    two lines would otherwise contradict each other: the preview would announce
    a relocation and the install would grow the row back in place.

    Printed from `main` rather than folded into `verify`, deliberately. `verify`
    is about the map -- does it round-trip, does the seed stand up, does it fit
    -- and the budget is about the archive; a run that prints one line about the
    map and one about the row can be read against a prediction, where a single
    sentence hedged three ways cannot.

    `created` MIRRORS `install_partner`'S OWN GATE and defaults to False for the
    same reason it does there: a budget is only spent on a row this toolkit
    allocated. A preview that promised a grow for a displaced retail row would
    be predicting a verb the install will not pick, which is worse than saying
    nothing.
    """
    if not reserve:
        return None
    if not created:
        return (f"budget: {reserve} B declared, but this area's map row does "
                f"not carry `created = true` -- the budget is only spent on a "
                f"row this toolkit allocated, so an install here fits or "
                f"RELOCATES exactly as it did before the field existed")
    if reservation is None:
        return (f"budget: this area declares {reserve} B of reservation, which "
                f"the CREATE path will ask the allocator for")
    if size <= reservation:
        return (f"budget: {reserve} B declared, and the row's current "
                f"{reservation} B already holds this stream -- the budget is "
                f"not needed on this install")
    if size <= reserve:
        return (f"budget: {reserve} B declared, so the install will ask "
                f"datwrite to GROW the row back to its stated entitlement "
                f"rather than relocate it -- subject to the grow gate "
                f"(claimants, EOF, the live MFT, datplan's withheld runs)")
    return (f"budget: {reserve} B declared and this stream is {size} B, which "
            f"is past it -- the budget cannot help and the row RELOCATES")


def install_partner(dat, out, plain, stream, compression, head_row, partner_row,
                    reservation, tag, *, reserve=0, created=False):
    """Put `stream` in the Stripped partner row and PROVE the row holds it.

    `out` is the file already holding `plain`, and `plain` is the payload a
    READER must get back. That file is the `--expect` both writers demand for a
    compression-8 write, and it is passed on the stored arm too: for a stored row
    the bytes ARE the payload, so declaring them is a statement rather than an
    override -- `datwrite.declaration_fault` consults the decode either way, and
    C-6 (a green archive holding an unreadable file) is reachable through both.

    REPLACE IF IT FITS, RELOCATE IF IT DOES NOT, and the size that decides is the
    one the row will HOLD -- `len(stream)`, never `len(plain)`. This comment used
    to say `datwrite` "writes UNCOMPRESSED and
    refuses to grow a reservation -- correctly, since its invariant is same row,
    same offset, same length -- so an authored map only fits where it is smaller
    than what ArenaNet compressed into that row. That is what capped every map
    this toolkit built at 32x32." Half of that stands: `replace` still never
    relocates, and the reservation is still the row's own whole 512-byte blocks.
    What is gone is the asymmetry -- we compress now too, so the comparison is
    between like and like.

    GROWN BACK, SINCE WORLDMAPS-W5, AND ONLY WHEN THE AREA SAID SO. `replace`
    writes the size field, so a compressed install SHRINKS the row's reservation
    (map 143's partner: 4,608 B -> 1,536 B after a 1,316 B plaza). The next,
    larger authored map is then past a ceiling the row's own freed blocks sit
    behind. `datwrite`'s `grow_to` is the flag for it and this function now
    passes it -- but only up to `reserve`, the entitlement the area row declares
    in `content/areas.toml`, because the archive records no such number anywhere
    and `grow_to` is defined as a STATEMENT about what a row was given rather
    than a request for more. With no budget declared, this is byte-for-byte the
    old behaviour: fit, or relocate.

    THREE OUTCOMES NOW, AND EACH ONE IS PRINTED. The middle one is the whole
    change and it is invisible from the outside -- a row that grew back in place
    and a row that never needed to grow both read as "replace" afterwards, and a
    row that relocated is only distinguishable by its offset. So the run says
    which of the three happened, in the run's own log, at the moment it happens.

    A REFUSED GROW IS NEVER SWALLOWED. `_grow_gate` refuses for four reasons
    (claimants, EOF, the live MFT, a withheld container run) and the first of
    them means another row has taken the blocks this one freed -- which is a
    real fact about the archive that a silent relocation would erase. So the
    gate's own sentence is printed, then the relocation runs and says it is
    running BECAUSE of it. An unrecognised failure is not a grow-gate refusal
    and is raised, exactly as before: see `grow_gate_refusal`.

    ONLY INTO A ROW WE MADE, and `created` is the second half of the gate rather
    than a courtesy. `grow_to` is defined as a statement about what a row was
    GIVEN, and for a row THIS toolkit allocated, the area's `reserve_bytes` IS
    that statement -- `create_chain` asked the allocator for exactly it. For a
    displaced RETAIL row it is not: ArenaNet gave that row whatever it gave it,
    our recipe's budget says nothing about it, and annexing the blocks behind it
    on the strength of a number from `content/areas.toml` would be inventing an
    entitlement. So a displaced row keeps the pre-WORLDMAPS-W5 behaviour exactly
    -- fit, or relocate -- however large a budget its area declares. `created`
    is the maps.toml row's own claim, threaded from `main`; hardening THAT claim
    against a retail chain that happens to bind the id is the R2 residual
    (`resolve_or_create`'s fall-through is shape-only) and is not this gate's
    job. Default False, because the safe direction for a caller who did not
    think about it is the old behaviour.

    Returns the verb that ran: "replace", "grow" or "relocate".
    """
    here = os.path.dirname(out)
    # ONE FILE ON THE STORED ARM, deliberately: --data and --expect naming the
    # same bytes is the whole content of "stored" and keeps that arm byte-for-byte
    # what the command wrote before --stored-install existed. `spill_stream`
    # returns None there for exactly that reason.
    data_path = spill_stream(here, tag, stream, compression) or out

    def replace_argv(grow_to=None):
        # A SEPARATE JOURNAL FOR THE GROW ARM. A grow the gate refuses and the
        # relocation that follows it are two runs against one row, and a journal
        # file is the only way back from either of them.
        which = "grow" if grow_to else "replace"
        argv = [sys.executable, os.path.join(HERE, "datwrite.py"), "--dat", dat,
                "--replace", str(partner_row), "--data", data_path,
                "--compression", str(compression), "--expect", out,
                "--journal", os.path.join(here, f"{tag}_{which}.json")]
        if grow_to:
            argv += ["--grow-to", str(grow_to)]
        return argv + ["--verify"]

    def relocate_argv():
        # NO --check-overlaps here: it is a READ-ONLY verb that returns
        # before any move, so passing it got rc 0 with nothing written and
        # this function reported "installed". datmove runs the overlap
        # check itself after a real move.
        return [sys.executable, os.path.join(HERE, "datmove.py"), "--dat", dat,
                "--row", str(partner_row), "--data", data_path, "--move",
                "--confirm", "--compression", str(compression),
                "--expect", out,
                "--journal", os.path.join(here, f"{tag}_move.json")]

    def run(argv):
        rc = subprocess.run(argv, text=True).returncode
        if rc != 0:
            raise Refused(f"the archive writer refused (rc {rc})")

    if len(stream) <= reservation:
        verb = "replace"
        print(f"  FITS: {len(stream)} B in the {reservation} B reservation "
              f"-- replacing in place")
        run(replace_argv())
    elif reserve and created and len(stream) <= reserve:
        verb = "grow"
        print(f"  GROWS BACK: {len(stream)} B is past the row's current "
              f"{reservation} B, and this area declares a {reserve} B "
              f"entitlement -- asking datwrite to annex the blocks this row "
              f"freed rather than relocating it")
        # CAPTURED, not inherited, because the decision below is made from what
        # the writer SAID. Both streams are re-printed first so nothing the
        # operator would have seen is lost -- only its ordering changes.
        proc = subprocess.run(replace_argv(grow_to=reserve), text=True,
                              capture_output=True)
        sys.stdout.write(proc.stdout)
        sys.stdout.write(proc.stderr)
        if proc.returncode != 0:
            gate = grow_gate_refusal(proc.stdout + proc.stderr)
            if gate is None:
                raise Refused(f"the archive writer refused (rc "
                              f"{proc.returncode})")
            print(f"  THE GROW GATE REFUSED: {gate}")
            print(f"  RELOCATING instead, and saying so: the row could not take "
                  f"its own freed blocks back, which is a fact about this "
                  f"archive and not a detail of this install")
            verb = "relocate"
            run(relocate_argv())
    else:
        verb = "relocate"
        if not reserve:
            why = "and no entitlement is declared for this area"
        elif not created:
            # NAMED, because this is the one relocation whose cause is a rule
            # rather than a size: the budget would have covered this stream and
            # was not spent, and an operator reading the run would otherwise be
            # left comparing two numbers that fit.
            why = (f"and the {reserve} B this area declares is NOT spendable "
                   f"here -- this row was not created by us, so what it was "
                   f"given is ArenaNet's statement and not ours")
        else:
            why = f"past the {reserve} B this area declares"
        print(f"  RELOCATES: {len(stream)} B does NOT fit the {reservation} B "
              f"reservation, {why} -- moving the row")
        run(relocate_argv())
    prove_partner(dat, head_row, plain, compression)
    return verb


def prove_partner(dat, head_row, plain, compression):
    """Read the Stripped partner back and refuse unless it holds what we wrote.

    AN EXIT CODE IS NOT EVIDENCE. This exists because `rc 0` from a writer once
    meant "your flags selected a different verb and nothing happened", and the
    run went on to arm the head and print success over an archive that still
    held ArenaNet's own map.

    `Archive.read` DECOMPRESSES, so this compares what a reader gets back
    against what we authored -- which is the check that got stronger rather than
    weaker when the row stopped being stored. The compression code is asked
    separately, because "the payload is right" and "the row is marked the way
    retail marks it" are two claims and a stored write that silently ignored our
    flag would pass the first.

    SHARED BY BOTH WRITE PATHS, and that is the point of it being a function.
    `install_partner` puts bytes in a row ArenaNet made; `create_chain` makes the
    row. They fail differently and they are checked identically -- a created
    chain that reads back wrong is exactly as unusable as a replaced row that
    does, and WORLDMAPS-W4's whole question is what a client does with bytes it
    has never seen under an id nothing has ever named.

    Resolves the partner through `MapIndex`, i.e. through the head's own
    `nextStream`, rather than through a row index the caller remembers: for a
    created chain the caller's index came from the allocator's plan, and asking
    the archive is how a plan that was carried out wrongly gets caught.
    """
    with Archive(dat) as ar:
        partner = mapchunks.MapIndex(ar).partner(
            next(e for e in ar.entries if e.index == head_row))
        code = partner.compression
        got = ar.read(partner)
    if got != plain:
        raise Refused(
            f"the row does not hold what we wrote: {len(got)} B back "
            f"against {len(plain)} B written. The writer returned "
            f"success and the archive disagrees, so the archive wins")
    if code != compression:
        raise Refused(
            f"the row reads back correctly but is marked compression {code}, "
            f"not the {compression} this install asked for. The bytes and the "
            f"code are two declarations and only one of them was checked")
    print(f"  verified: the row reads back the {len(got)} B we wrote, "
          f"stored as compression {code} in {partner.size} B")
    return partner


# --------------------------------------------------------------- create
#
# WORLDMAPS-W3. Everything above puts an authored map into a row ArenaNet made,
# which means every authored area so far has DISPLACED a live retail one -- map
# 143, file id 0x287D3, and `content/maps.toml` says in its own note that we do
# not know which area we are sitting on. `datalloc` is the verb that stops
# needing a victim, and this is deploy learning to call it.
#
# WHAT IS NEW HERE IS THE SHAPE, NOT THE MECHANISM. A9 (2026-08-20,
# studies/archivewrite/FINDINGS.md 18.6) proved the retail client resolves,
# decompresses and parses a chain `datalloc.alloc` created under a brand-new
# file id. That chain was a model skeleton with real content on every stream. A
# MAP is two rows, and its head is EMPTY on purpose -- the zero-length re-bloat
# trigger -- so a created map chain combines "an id the client has never seen"
# with "a stream the client must COMPILE rather than read", and no run has ever
# put those two together. FINDINGS 36 item 4 names it open. That run is
# WORLDMAPS-W4 and nothing offline can answer it.

MAP_HEAD_FLAGS_U16 = mapchunks.MAP_HEAD_FLAGS_U16          # 259: stream 1, USED|FIRST
MAP_PARTNER_FLAGS_U16 = mapchunks.MAP_PARTNER_FLAGS_U16    # 1:   stream 0, USED


def sibling_of(file_id):
    """The bit-31 spelling of a plain file id: FcArchive's rename marker."""
    return file_id | FILE_ID_HIGH_BIT


def map_chain(ar, file_id):
    """The (head, partner) entries `file_id` names, or None if nothing names it.

    THE QUESTION IS ASKED OF THE RAW TABLE, and that is not a detail. The
    default `file_id_table` registers a bit-31 id under BOTH spellings as a
    convenience of ours; the client does no such thing and compares 32 bits
    exactly. Here the answer decides CREATE versus INSTALL -- that is, whether
    deploy writes into a row that a pending replacement already names, or
    allocates a fresh one -- so it has to be the client's answer.
    `archive.py`'s own docstring lists three failures from getting this
    backwards; this would have been the fourth.

    A BIT-31 SIBLING IS A REFUSAL EITHER WAY, and this is the known gap in the
    allocator rather than a new rule: `plan_alloc` tests `file_id in raw` and so
    ACCEPTS a plain id whose renamed spelling is already in the table, while
    `next_free_file_id` would never suggest it (studies/archivewrite/FINDINGS.md
    17.5, still open 2026-08-20). Allocating there produces two live
    registrations -- a rename pending and a fresh plain claim -- that no crc
    rule and none of `datcheck`'s ten open-time rules counts. `datalloc` is not
    modified to fix that; the caller refuses to walk into it.

    REFUSES rather than returning None when the id names something that is not a
    two-row map chain. "Nothing binds this id" and "this id binds somebody
    else's file" are different states with different remedies, and only the
    first one may create. The shape is checked positively -- head flags 259, a
    non-zero `nextStream`, a partner carrying flags 1 -- because
    `MapIndex.partner` reads `by_row.get(nextStream)` and `nextStream == 0`
    TERMINATES a chain while row 0 is a real MFT row, so a head with no partner
    resolves to the file header rather than to None.
    """
    raw = file_id_table(ar, raw=True)
    twin = sibling_of(file_id)
    if twin in raw:
        raise Refused(
            f"file id {file_id:#x} has a bit-31 sibling {twin:#x} bound to row "
            f"{raw[twin]} in this archive, and this command will not touch "
            f"either spelling.\n"
            f"  Bit 31 is not a spelling variant: FcArchive binds "
            f"`id | 0x80000000` and deletes the plain name when it has REQUESTED "
            f"A REPLACEMENT, so the sibling is the archive announcing that this "
            f"row is stale and a new file is on its way (content/maps.toml "
            f"[map.148] is the whole story).\n"
            f"  `plan_alloc` would accept the plain id here -- it tests exact "
            f"membership -- and leave two live registrations that nothing we own "
            f"counts (studies/archivewrite/FINDINGS.md 17.5). Choose another id "
            f"with `datalloc.py --next-id`, which skips both spellings.")
    row = raw.get(file_id)
    if row is None:
        return None
    by_row = {e.index: e for e in ar.entries}
    head = by_row.get(row)
    if head is None:
        raise Refused(f"file id {file_id:#x} names row {row}, which is absent")
    if not mapchunks.is_map_head(head):
        raise Refused(
            f"file id {file_id:#x} already binds row {row} in this archive, and "
            f"that row is NOT a Bloated map head: alloc.flags "
            f"0x{mapchunks.alloc_flags(head):02X}, stream "
            f"{mapchunks.alloc_stream(head)}, {head.size} B, compression "
            f"{head.compression}.\n"
            f"  A map head is flags 3 (USED|FIRST_STREAM) on stream 1, the u16 "
            f"259. What sits here is somebody else's file, and the remedy is a "
            f"different id rather than a different flag -- overwriting it would "
            f"make one of two files unreachable, which no rule in datcheck "
            f"counts.")
    nxt = mapchunks.next_stream(head)
    if not nxt:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, a map head whose nextStream "
            f"is 0 -- the chain terminates there, so this file has no Stripped "
            f"partner to install into.\n"
            f"  A map is TWO rows and this is one. Nothing here can repair it: "
            f"`datalloc` creates whole chains and `datwrite` writes rows that "
            f"exist.")
    partner = by_row.get(nxt)
    if partner is None:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, whose nextStream names row "
            f"{nxt}, which is absent from this archive's MFT")
    if partner.flags != MAP_PARTNER_FLAGS_U16:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, chained to row {nxt} with "
            f"flags 0x{partner.flags:04X} rather than the Stripped partner's "
            f"0x{MAP_PARTNER_FLAGS_U16:04X} (stream 0, USED).\n"
            f"  MEASURED corpus-wide, the nextStream link map is a bijection "
            f"and every Bloated head chains to exactly one stream-0 row. This "
            f"chain is a shape we have never seen the client produce, so it is "
            f"named rather than installed into.")
    return head, partner


def alloc_journal_path(here, tag):
    """Where `create_chain` writes an area's allocation journal. ONE expression.

    Named rather than spelled out at each of its three call sites, because the
    three now disagree about what they want from it and would drift: the create
    path REFUSES to write over one (R3), the install path READS one as evidence
    that a chain is ours (R2), and both have to be talking about the same file
    for either to mean anything.
    """
    return os.path.join(here, f"{tag}_alloc.json")


def archive_carries(dat, offset, blob):
    """Is `blob` sitting at `offset` in `dat` RIGHT NOW? -> bool

    Eight bytes and a seek, and it is the whole of what makes an allocation
    journal evidence about the copy in front of us rather than about a filename
    (`allocation_recorded`). Any read failure is a False rather than a raise:
    the caller is deciding whether something is evidence, and an archive it
    cannot read has not shown it anything.

    AN EMPTY `blob` IS A FALSE, not a vacuous True. Every file carries zero
    bytes at every offset, so the one-line version of this would hand a caller a
    check that cannot fail -- which is the failure this pass exists to close,
    one function smaller.
    """
    if not blob:
        return False
    try:
        with open(dat, "rb") as fh:
            fh.seek(offset)
            return fh.read(len(blob)) == blob
    except OSError:
        return False


def allocation_recorded(journal, dat, file_id, head_row, partner_row):
    """Does `journal` record US allocating THIS chain in THIS archive? -> bool

    READ STRUCTURALLY, NOT AS PROSE, and that is deliberate after the grow
    gate's four-sentence join (see `grow_gate_refusal`). `datalloc.alloc` writes
    the journal's `what` strings for a human; what is checked here is BYTES:

      * one edit's `after` is exactly `<II` (file_id, head_row) -- the file-id
        record going live, which is step 4 of the allocation and the moment the
        chain acquires its name;
      * the edit at `mft_offset + head_row * 24` writes a 24-byte row whose
        flags are the map head's and whose `nextStream` is `partner_row`;
      * the edit at `mft_offset + partner_row * 24` writes the partner's flags;
      * and the archive in front of us is the archive that file-id record went
        into.

    All four together say "this file recorded binding this id to this head,
    chained to this partner, in this archive". `mft_offset` is read from the
    JOURNAL rather than from the archive on purpose: the client relocates the
    master file table during ordinary play (`datwrite.Journal` records it for
    exactly that reason), so an offset compared against today's table would
    stop matching for a reason that says nothing about who made the rows.

    THE LAST CONJUNCT IS NOT A PATH COMPARE ANY MORE, and the fix is the same
    lesson as the one above it. `datalloc` records an ABSOLUTE path, and
    archives in this project are COPIED WHOLE as a matter of routine --
    `overlay.py` copies manifest archives with `shutil.copyfile`,
    `make_run_dir.py` stages one per run directory, and RUNBOOK's own procedure
    copies `run-live/<build>/Gw.dat` over `run/<build>/Gw.dat`. A copy that
    carries its journal beside it is OUR chain, described byte-exactly, and the
    path compare refused it -- with a closing remedy ("allocate under a fresh
    id") that is actively wrong advice in exactly that state. So the archive is
    asked DIRECTLY instead: does it carry, at the offset the journal recorded,
    the file-id record the journal says it wrote there? That survives a copy, a
    rename, an `--out` that moved the build products, and a later relocation of
    the partner. The path compare is KEPT as the FIRST route, cheap and not
    weaker than it was, for the archive that stayed where it was while the
    client rewrote the id table underneath it.

    THE ROWS ARE THE CALLER'S CURRENT ONES, and that is what keeps this from
    degenerating into "a journal exists": `resolve_or_create` reads
    `head_row`/`partner_row` out of the archive in front of it, so a journal
    describing some other allocation fails the `<II` conjunct before the archive
    is opened at all.

    A journal that will not parse is not evidence and is not an error here --
    `datwrite.read_journal` refuses an empty or malformed one by name, and the
    caller's job is to say what IS there rather than to re-raise.
    """
    try:
        doc, _dropped = datwrite.read_journal(journal)
    except (SystemExit, OSError, ValueError):
        return False
    if not isinstance(doc, dict):
        return False
    mft = doc.get("mft_offset")
    if not isinstance(mft, int):
        return False
    named = struct.pack("<II", file_id, head_row)
    rows_seen = {}
    id_offsets = []
    for ed in doc.get("edits", []):
        try:
            after = bytes.fromhex(ed.get("after", ""))
            off = int(ed["offset"])
        except (KeyError, TypeError, ValueError):
            continue
        if after == named:
            id_offsets.append(off)
        if len(after) != ENTRY_SIZE:
            continue
        for row in (head_row, partner_row):
            if off == mft + row * ENTRY_SIZE:
                rows_seen[row] = struct.unpack("<QIHHII", after)
    head = rows_seen.get(head_row)
    partner = rows_seen.get(partner_row)
    if not (id_offsets
            and head is not None and partner is not None
            and head[3] == MAP_HEAD_FLAGS_U16 and head[4] == partner_row
            and partner[3] == MAP_PARTNER_FLAGS_U16):
        return False
    # The binding, either way round: the name it was written under, or the
    # bytes it was written as. The second is the one that survives a copy.
    named_path = os.path.normcase(os.path.abspath(str(doc.get("dat", ""))))
    if named_path == os.path.normcase(os.path.abspath(dat)):
        return True
    return any(archive_carries(dat, off, named) for off in id_offsets)


def created_evidence(dat, here, tag, file_id, head_row, partner_row):
    """The journal proving we made this chain, or None. -> path|None

    Looks BESIDE THE ARCHIVE as well as in `here`, because those are the same
    directory on every default invocation and differ only when `--out` moves the
    build products somewhere else. Widening the search does not weaken the
    check: whichever file is found still has to describe this id and these two
    rows AND be bound to this archive by one of `allocation_recorded`'s two
    routes, so a journal from another area is not evidence about this one.

    A COPY OF THE ARCHIVE IS FOUND BY WHICHEVER JOURNAL TRAVELLED WITH IT. That
    is the case this pair exists to serve and the case the path compare used to
    refuse: copy `Gw.dat` and `<area>_alloc.json` into a fresh run directory --
    which is what `make_run_dir.py` and RUNBOOK's `Copy-Item` step do -- and the
    chain is still ours, because the copy carries the file-id record the journal
    recorded. What does NOT travel is nothing: a journal left behind is a
    refusal, and its remedy is to bring it along rather than to allocate again.
    """
    if not here or not tag:
        return None
    seen, out = set(), []
    for d in (here, os.path.dirname(os.path.abspath(dat))):
        if not d:
            continue
        p = os.path.abspath(alloc_journal_path(d, tag))
        if os.path.normcase(p) not in seen:
            seen.add(os.path.normcase(p))
            out.append(p)
    for p in out:
        if os.path.isfile(p) and allocation_recorded(p, dat, file_id, head_row,
                                                     partner_row):
            return p
    return None


def resolve_or_create(ar, file_id, created, *, here=None, tag=None):
    """(rows, create). `rows` is None exactly when the chain must be CREATED.

    `created` is the maps.toml row's own `created = true` -- an area that asked
    for a file of its own. It is deliberately NOT inferred from the archive: "the
    id does not resolve" is also what a WRONG id looks like, and until 2026-08-20
    that was this command's loudest refusal. A row that does not claim to be
    created keeps that refusal.

    AND THE FALL-THROUGH IS NOT SHAPE-ONLY ANY MORE (R2, WORLDMAPS residuals).
    `map_chain` checks that a chain LOOKS like a map -- head flags 259, a
    non-zero `nextStream`, a partner carrying flags 1 -- and 349 retail maps in
    the owner's own archive look exactly like that. So for a `created = true`
    row whose id already binds, this branch fired identically for OUR chain and
    for a genuine ArenaNet map that happens to sit under the id, and the second
    case installed our geometry over somebody's live area with no line of output
    to distinguish it. The claim "this file is ours" came from `content/`, which
    knows nothing about which copy is in front of it.

    So the claim now has to be EVIDENCED against the archive: the allocation
    journal `create_chain` wrote, describing this id and these exact two rows
    and bound to the copy in front of us (`created_evidence`). No journal, or
    one that describes something else, and this REFUSES naming what is actually
    there -- the rows, their flags and their sizes -- because the remedy depends
    on what a person makes of them.

    THE CASE THIS MUST NOT BREAK is the idempotent re-deploy, which is the loop
    an author actually runs: build, install, look, change the shape, install
    again. That run finds its own journal beside the archive and passes, and
    `test_deploy.py` section 10 drives exactly it. SO IS THE SAME LOOP ON A COPY
    of the archive -- staged into a run directory, or copied from `run-live/` --
    which the first version of this guard refused, because it joined on the
    absolute path `datalloc` records rather than on the bytes the allocation put
    in the file. `allocation_recorded` reads the archive now.

    `here`/`tag` say where to look and default to None, which for a `created`
    row means NO evidence can be found and the refusal fires. Fail-closed on
    purpose: a caller that did not think about it is the caller this is for.
    """
    chain = map_chain(ar, file_id)
    if chain is not None:
        # IDEMPOTENT BY DESIGN. A created chain that already exists is just a
        # map row, and re-deploying an area is the normal iterating loop -- the
        # second run replaces the partner in place and finds the head already
        # armed. Nothing about a row's origin survives into how it is written.
        rows = resolve_rows(ar, file_id)
        if created and created_evidence(ar.path, here, tag, file_id,
                                        rows[0], rows[1]) is None:
            head, partner = chain
            raise Refused(
                f"file id {file_id:#x} ALREADY BINDS a map chain in this "
                f"archive -- head row {head.index} ({head.size} B, flags "
                f"0x{head.flags:04X}), partner row {partner.index} "
                f"({partner.size} B, flags 0x{partner.flags:04X}, compression "
                f"{partner.compression}) -- and nothing here shows that WE made "
                f"it.\n"
                f"  This area's maps.toml row says `created = true`, which is a "
                f"claim about where the file came from and is made in "
                f"content/, against no archive in particular. `map_chain` "
                f"checks the SHAPE, and 349 retail maps in the owner's own copy "
                f"have exactly this shape -- so installing here would displace "
                f"a live ArenaNet area while every line of output said the "
                f"word 'created'.\n"
                f"  The evidence this wants is the allocation journal "
                f"`{tag or '<area>'}_alloc.json`, beside the archive or beside "
                f"--out, describing THIS id and THESE two rows. It is written "
                f"by the run that allocated the chain and it is the only record "
                f"that survives; the 24-byte MFT row has no field for who made "
                f"it.\n"
                f"  THE JOURNAL TRAVELS WITH THE ARCHIVE, so start there. A "
                f"whole-file copy of a Gw.dat -- a staged run directory, or "
                f"RUNBOOK's `Copy-Item run-live\\<build>\\Gw.dat "
                f"run\\<build>\\Gw.dat` -- carries this chain with it and is "
                f"still ours; the check follows it, because it asks whether "
                f"THIS file holds the file-id record the journal recorded "
                f"rather than what the file is called. What does not follow is "
                f"a journal left behind in the directory the archive was copied "
                f"FROM. Copy `{tag or '<area>'}_alloc.json` next to this "
                f"archive (or next to --out) and run it again.\n"
                f"  If the journal is genuinely gone, that is not recoverable "
                f"from here: allocate under a fresh id (`datalloc.py "
                f"--next-id`, which skips both spellings) and point the "
                f"maps.toml row at it.")
        return rows, False
    if not created:
        raise Refused(
            f"file id {file_id:#x} does not resolve in this archive, and its "
            f"maps.toml row does not carry `created = true`.\n"
            f"  That is the old refusal and it is kept: an id that resolves "
            f"nowhere is what a WRONG id looks like, and creating one silently "
            f"would turn a typo into two new MFT rows. If this area is meant to "
            f"own its file, say so in the row.")
    return None, True


def create_note(file_id, size, bound, created, install):
    """What this run says about the ROW the stream is going into. -> str|None

    ASKED ON EVERY RUN, INSTALL OR NOT, and that is the whole reason it is a
    function rather than a line under `if create:`. The decision to allocate is
    computed only under `--install`, correctly -- deciding costs a refusal and a
    build-only run must not refuse -- so a build-only run printed the two sizes
    and stopped, and a dry run against an id NOTHING binds was indistinguishable
    from a dry run against an id everything binds.

    THAT IS NOT COSMETIC, and it was found the way these things are found: by
    running the command. WORLDMAPS-W4's step 1 is a build-only run whose output
    the operator compares against a prediction registered beforehand, and the
    prediction that matters at that step is that the create branch WILL fire --
    that the area -> map row -> file id join lands on a row carrying
    `created = true` whose id binds nothing in this archive. A run that cannot
    say so leaves a correct dry run reading as a refutation of the join, which is
    the same defect as a check that cannot fail, from the other side.

    `bound` IS THE RAW TABLE'S ANSWER, or None: the row the CLIENT's own lookup
    would find (`map_chain`'s docstring has the three failures that come from
    asking the convenience form instead). It is asked here without the shape
    checks that can refuse, because a preview that refuses is not a preview --
    the shape is `map_chain`'s question and it is asked on the install path,
    where a refusal is the correct outcome.

    Returns None when the id binds something: `verify` has already said what that
    row's reservation does with these bytes, and two lines about one row is how
    they drift apart.
    """
    if bound is not None:
        return None
    if created and install:
        return (f"no reservation to judge: file id {file_id:#x} binds nothing "
                f"in this archive, so the {size} B stream will be given a row "
                f"of its own rather than fitted into one")
    if created:
        return (f"no reservation to judge: file id {file_id:#x} binds nothing "
                f"in this archive, so --install would CREATE the chain rather "
                f"than fit the {size} B stream into a row")
    return (f"file id {file_id:#x} binds nothing in this archive and this "
            f"area's map row does not carry `created = true`, so --install "
            f"would REFUSE here rather than allocate -- an id that resolves "
            f"nowhere is also what a WRONG id looks like")


def create_streams(plain, stream, compression, reserve=0):
    """The two rows of a NEW map chain, HEAD FIRST. -> [Stream, Stream].

    Separated from the write so the SHAPE can be inspected without an archive,
    because the shape is the part with a silent failure mode.

    THE HEAD IS EMPTY, and that emptiness is the whole mechanism. A zero-length
    Bloated row is the documented re-bloat trigger: the client fails to load the
    map, logs `Attempting to re-bloat`, compiles the Bloated form from the
    Stripped partner and writes it back. Everywhere else in this toolkit that
    state is produced by ARMING a row that had content (`rebloat.arm`); here it
    is the row's only state ever, which is precisely the case FINDINGS 36 item 4
    names untested.

    THE HEAD IS FIRST BECAUSE THE FILE ID LANDS ON `streams[0]`, and registering
    the partner instead is the natural symmetric mistake. It is refused by
    `plan_alloc`'s shape loop -- but MEASURED corpus-wide the file-id table names
    349 map heads and zero partners, and no crc rule, no `datcheck` rule and no
    overlap sweep would notice the swap. So the order is stated here, in one
    place, rather than at a call site.

    `expect` IS PASSED ON BOTH ARMS. For compression 8 it is mandatory and it is
    the only refutation that exists after the write (the entry crc is over the
    STORED bytes, so a stream that decodes to the wrong payload is green
    everywhere -- FINDINGS C-6). For a stored row the bytes ARE the payload, so
    passing it is the caller stating that positively, exactly as
    `install_partner` does.

    `reserve` GOES ON THE PARTNER AND ONLY THE PARTNER, and `datalloc.Stream`
    refuses it on the head rather than accepting it silently -- an empty row owns
    no extent, so a budget there would buy nothing. The partner is the row that
    holds the geometry and the row a later, larger authored map has to grow. 0
    is "no budget stated", which is what every area row said before
    WORLDMAPS-W5 and what the three that ride map 143 still say.
    """
    extra = 8 if compression == COMPRESSION_HUFFMAN else 0
    return [datalloc.Stream(b"", MAP_HEAD_FLAGS_U16),
            datalloc.Stream(stream, MAP_PARTNER_FLAGS_U16,
                            extra_bytes=extra, expect=plain, reserve=reserve)]


def create_chain(dat, file_id, plain, stream, compression, here, tag,
                 reserve=0):
    """Allocate a map's two rows under an id nothing binds yet. -> (head, partner).

    THE PLAN IS PRINTED AND THEN THROWN AWAY. `alloc(plan=...)` exists and is not
    used: a handed-in plan skips `plan_alloc` on the write path, and that gate is
    the whole safety argument (the id is free in the RAW table, exactly one row
    carries FIRST_STREAM, the MFT grows only into its own last block, placement
    consumes runs so two rows of one file cannot collide, every nextStream target
    lands in `[16, count)`). A plan computed a moment earlier is also a placement
    computed against an archive state that may have moved. So the preview is a
    preview -- it costs one read and it is what a person approves -- and the
    write re-plans under its own open.

    NOT ARMED AFTERWARDS, and nothing here calls `rebloat`. The head is BORN
    armed; `rebloat.arm` refuses a zero-length row anyway, correctly, since it
    cannot journal a baseline mesh from a row that has none. `main` reaches the
    same conclusion from the ARCHIVE rather than from this function's word for
    it, which is the stronger of the two checks and is why it was left in place.

    THE STREAM IS SPILLED even though nothing here needs a file: `datalloc` takes
    the bytes in memory, unlike the two CLI writers `install_partner` drives. It
    is written anyway because this is the path where those bytes have no other
    copy -- see `spill_stream`, and WORLDMAPS-W4's capture list, which names the
    file. It happens BEFORE the plan so that a chain the allocator refuses still
    leaves behind the thing that was refused.

    `reserve` IS THE ONE CHANCE TO CHOOSE THIS ROW'S CEILING, which is why the
    number is printed rather than merely passed. A created partner's reservation
    used to be exactly the first install's own length, so the second, larger
    authored map was already past a bound nobody had picked; the area's
    `reserve_bytes` picks it, once, here. It is stated in the run's own log
    because nothing on disk records it afterwards -- the 24-byte MFT row has no
    entitlement field, and `deploy.resolve_rows` recomputes a row's ceiling from
    its CURRENT size on every later run.

    AN EXISTING JOURNAL IS REFUSED, FIRST, BEFORE ANY FILE IS TOUCHED (R3).
    `datalloc`'s own CLI has refused this since it was written -- and this path
    never went through it. `create_chain` calls the `alloc()` API directly, so
    `_journal_path`'s check (`datalloc.py`, `_main`) was bypassed and a second
    create with the same area name truncated the first one's journal at its
    first record, then printed the file it had just destroyed as the way back.
    The reasoning is `datalloc`'s and is quoted rather than paraphrased: A
    JOURNAL IS THE ONLY WAY BACK FROM AN ALLOCATION. Overwriting one leaves the
    edits it recorded applied forever, and a later `--revert` of the new file
    would report success having restored none of them.

    It is checked FIRST -- before the spill, before the plan -- because a run
    that cannot be made revertible has not begun. That is a deliberate exception
    to the spill-before-plan ordering below: the spill exists so that a chain
    the ALLOCATOR refuses still leaves behind the bytes it refused, and this
    refusal is about the operator's directory rather than about the chain.
    """
    journal = alloc_journal_path(here, tag)
    if os.path.exists(journal):
        raise Refused(
            f"{journal} already exists, and this will not write over it.\n"
            f"  A journal is the only way back from an allocation. Overwriting "
            f"one leaves the edits it recorded applied forever, and a later "
            f"--revert of the new file would report success having restored "
            f"none of them.\n"
            f"  That is `datalloc`'s own refusal (its `_journal_path`), and it "
            f"has always been CLI-only -- this command calls `alloc()` "
            f"directly, so it was bypassed until 2026-08-20.\n"
            f"  It is also the record `resolve_or_create` reads to prove a "
            f"created chain is ours, so a clobbered one costs both the undo and "
            f"the evidence. Move or delete it deliberately, or deploy with "
            f"--out pointing somewhere else.")
    spill_stream(here, tag, stream, compression)
    # INSIDE A REFUSAL, because building the streams is now a place that can
    # refuse. `create_streams` puts `reserve` on a `datalloc.Stream`, and
    # `datalloc` checks the number there -- a fraction, a negative, a budget
    # under its own payload. That is an authoring mistake in
    # `content/areas.toml`, and an authoring mistake must reach the operator as
    # this command's own REFUSED line rather than as a traceback: `__main__`
    # catches `deploy.Refused` and nothing else, so a raw `datalloc.Refused`
    # from three lines above the try below exits 1 with a stack instead of 2
    # with a remedy.
    try:
        streams = create_streams(plain, stream, compression, reserve=reserve)
    except datalloc.Refused as exc:
        raise Refused(
            f"this area's declared reservation is not one the allocator will "
            f"take:\n  {exc}\n"
            f"  The number is `reserve_bytes` in content/areas.toml, so the "
            f"remedy is a content edit and not an archive one.") from exc
    try:
        with Archive(dat) as ar:
            preview = datalloc.plan_alloc(ar, streams, file_id)
    except datalloc.Refused as exc:
        raise Refused(f"the allocator will not plan this chain:\n  {exc}") from exc
    preview.show()
    part = preview.rows[1]
    if reserve:
        print(f"  reservation: {part.reservation} B for a {part.size} B "
              f"stream, from this area's declared {reserve} B entitlement -- "
              f"{part.reservation - part.size} B of headroom, so an authored "
              f"map up to {part.reservation} B compressed replaces this row in "
              f"place instead of relocating it")
    else:
        print(f"  reservation: {part.reservation} B for a {part.size} B "
              f"stream, {part.reservation - part.size} B of headroom -- this "
              f"area declares no `reserve_bytes`, so the row gets what the "
              f"payload needs and a larger map later will relocate it")

    try:
        plan = datalloc.alloc(dat, streams, file_id, journal, confirm=True)
    except datalloc.Refused as exc:
        raise Refused(f"the allocator refused the write:\n  {exc}") from exc
    head_row, partner_row = plan.rows[0].index, plan.rows[1].index

    # AND THE ARCHIVE IS ASKED WHETHER THE PLAN HAPPENED. Every claim below is
    # one the allocator could have got wrong in a way nothing else would catch:
    # the id must name the HEAD (a partner registration passes every checksum),
    # the head must be zero length (or the client has nothing to re-bloat), the
    # chain must link head -> partner, and both rows must sit at index >= 16
    # (LoadMft never recycles a row below that, and the open-time reconcile only
    # scans from there, so a row underneath is outside every rule we reasoned
    # about).
    with Archive(dat) as ar:
        raw = file_id_table(ar, raw=True)
        by_row = {e.index: e for e in ar.entries}
        bound = raw.get(file_id)
        head = by_row.get(head_row)
        partner = by_row.get(partner_row)
        also = sorted(k for k, v in raw.items() if v == partner_row)
    if bound != head_row:
        raise Refused(
            f"the chain was allocated but file id {file_id:#x} resolves to "
            f"{bound!r}, not to the head row {head_row}. The open-time reconcile "
            f"DELETES a USED|FIRST_STREAM row no file-id record names")
    if also:
        raise Refused(
            f"the partner row {partner_row} is named by file id(s) "
            f"{', '.join(hex(a) for a in also)}. Only the head may carry an id: "
            f"MEASURED, the table names 349 map heads and zero partners")
    if head is None or partner is None:
        raise Refused(f"rows {head_row}/{partner_row} are not in the MFT after "
                      f"the allocation")
    if head.flags != MAP_HEAD_FLAGS_U16 or partner.flags != MAP_PARTNER_FLAGS_U16:
        raise Refused(
            f"the created rows carry flags 0x{head.flags:04X}/"
            f"0x{partner.flags:04X}, not the map chain's "
            f"0x{MAP_HEAD_FLAGS_U16:04X}/0x{MAP_PARTNER_FLAGS_U16:04X}")
    if head.size != 0:
        raise Refused(
            f"the created head is {head.size} B, not zero. A map head is armed "
            f"by being empty, and a non-empty one is a Bloated map the client "
            f"will load instead of compiling ours")
    if mapchunks.next_stream(head) != partner_row:
        raise Refused(
            f"the created head chains to row {mapchunks.next_stream(head)}, not "
            f"to its partner {partner_row}")
    low = [r for r in (head_row, partner_row) if r < datalloc.FIRST_CLAIMABLE_ROW]
    if low:
        raise Refused(
            f"created row(s) {low} sit below FIRST_CLAIMABLE_ROW "
            f"({datalloc.FIRST_CLAIMABLE_ROW}); rows underneath it are never "
            f"recycled by LoadMft and the reconcile does not scan them")
    print(f"  created: head row {head_row} (zero length -- BORN armed, the "
          f"re-bloat trigger is its only state ever), partner row "
          f"{partner_row}, file id {file_id:#x} registered on the head")
    prove_partner(dat, head_row, plain, compression)
    return head_row, partner_row


def readback(dat, file_id, staged_blob, area):
    """What the client's compiler actually produced, against what we authored.

    The whole verdict is mechanical, which is the point: nobody has to look at
    or listen to anything for this to be a result. Every row here is a thing the
    compiler could have contradicted -- and that sentence was FALSE of the
    optional-chunk loop until 2026-08-21, which is what its comment is about: a
    row that does not print because the case it covers did not arise is not a
    row the compiler could have contradicted, it is a row nobody asked for.
    """
    import terrain as trn_bloated
    from props import BloatedProps

    staged = mfile.MapFile.decode(staged_blob, strict=False)
    with Archive(dat) as ar:
        row = file_id_table(ar)[file_id]        # re-resolve; the head RELOCATES
        head = next(e for e in ar.entries if e.index == row)
        blob = ar.read(head)

    # The head is still ARMED -- zero length -- so the client never re-bloated
    # it. Say that, rather than letting the decoder raise three layers down
    # about a 0-byte FFNA: on 2026-08-21 a harness that could not bind its
    # ports (another session held them) surfaced here as a ValueError about a
    # file header, which names neither the cause nor the thing that failed.
    # An empty head is a RESULT -- "the compiler never ran" -- not a corrupt
    # file, and it is the single most likely outcome of any launch that did
    # not happen.
    if not blob:
        return ([f"  [FAIL] the client never re-bloated {file_id:#08x} -- "
                 f"its head is still 0 B, exactly as --install armed it. "
                 f"The map was never compiled, so there is nothing to check "
                 f"it against. Look at the harness rc above and at "
                 f"Gw.log before looking at anything here."],
                ["head still armed"])

    hm = mfile.MapFile.decode(blob, strict=False)

    out, bad = [], []

    def row_(ok, label, detail=""):
        out.append(f"  [{'PASS' if ok else 'FAIL'}] {label}"
                   + (f"  {detail}" if detail else ""))
        if not ok:
            bad.append(label)

    path = hm.find(0x20000008)
    row_(path is not None and len(path.payload()) > 0,
         "the client re-compiled the map",
         f"{len(path.payload()) if path else 0} B path chunk")
    pm = None
    if path is not None:
        pm = pathmap.PathingMap.from_chunk(path.payload())
        out.append(f"         mesh: {len(pm.trapezoids)} trapezoids "
                   f"the client built from our terrain")

    st = stx.StrippedTerrain.decode(staged.find(sb.TERRAIN).payload())
    bt = hm.find(0x20000002)
    if bt is not None:
        same = sum(1 for a, b in zip(trn_bloated.Terrain.decode(bt.payload()).heights,
                                     st.heights) if a == b)
        row_(same == len(st.heights),
             "the compiled height field equals the one we authored",
             f"{same}/{len(st.heights)} samples")

    # THE OPTIONAL CHUNKS, BOTH WAYS -- and the absent way is the one worth
    # having. This loop used to read `if want is None: continue`, which made the
    # absent case a CHECK THAT CANNOT FIRE. WORLDMAPS-W8 installed a map with
    # `environment = false`, readback printed a clean 6/6, and it had asserted
    # NOTHING about the environment; the fact that actually mattered -- that the
    # client's COMPILED map carries no 0x20000009 either, so there was no donor,
    # global or cached environment to fall back on -- had to be established by
    # hand afterwards, out of the allocation journal. That fact is what makes
    # "we removed X and nothing changed" mean "X was not the cause"; without it
    # the null is a statement about an instrument that never looked. So an
    # omitted chunk INVERTS the assertion rather than skipping it.
    for cid, scid, what in ((0x20000009, ENV, "environment"),
                            (0x20000012, SOUND, "sound")):
        want = staged.find(scid)
        got = hm.find(cid)
        if want is None:
            row_(got is None,
                 f"our map carries no {what}, and the compiled map carries "
                 f"none either",
                 f"nothing to fall back on -- no donor, global or cached "
                 f"{what}" if got is None else
                 f"but the compiler produced {len(got.payload())} B of "
                 f"{what} we did not author, so anything this arm concludes "
                 f"from its absence is about a chunk that was THERE")
            continue
        row_(got is not None and got.payload() == want.payload(),
             f"our {what} payload carried VERBATIM", f"{len(want.payload())} B")

    bp = hm.find(0x20000004)
    n_want = len(StrippedProps.decode(staged.find(PROPS_CHUNK).payload()).props)
    if bp is not None:
        row_(len(BloatedProps.decode(bp.payload()).records) == n_want,
             f"our {n_want} prop(s) are in the compiled map")

    # THE AREA'S FLOOD SEED, against the CLIENT's mesh. NOT the player's
    # spawn -- that comes from the MAP row, and is what content.py's
    # map_static_config() hands the server. This comment used to read "the
    # spawn test every maps.toml row carries" while the code below reads
    # area["seed_x"], and on 2026-08-21 that wording put a claim into
    # WORLDMAPS-W13's write-up which the run had not measured: it moved a
    # flood seed and was reported as having moved the character. seed_x has
    # three consumers in this tree and none of them is the player.
    if pm is not None:
        sx, sy = float(area["seed_x"]), float(area["seed_y"])
        n = sum(1 for t in pm.trapezoids if t.contains(sx, sy))
        row_(n == 1, f"the flood seed ({sx:.0f}, {sy:.0f}) lands in exactly one "
                     f"trapezoid of the compiled mesh", f"{n}")
    return out, bad


# --------------------------------------------------------------- launch

def launch(exe, session, dat, map_id, hold, area=None):
    """Run the harness once, with the server pointed at OUR archive.

    `--dat` already decides which client runs, so it decides which world the
    server serves too: `RURIK_DAT` makes both halves name the same file, which
    is also what `contentids.preflight` requires (studies/maprows FINDINGS 8).
    """
    env = dict(os.environ)
    env["RURIK_DAT"] = os.path.abspath(dat)
    print(f"  server world: RURIK_DAT={env['RURIK_DAT']}")
    # The archive gate, run HERE and not left to the harness. session.py's own
    # rule about the cage applies unchanged: a guard that only guards one of two
    # doors is the shape of the defect it is here to prevent. This is also the
    # site with the most to lose -- the archive it is about is one we just WROTE
    # into, and an armed head or a half-finished replace is exactly the state the
    # ten open-time rules and the payload CRC sweep exist to name.
    print(f"  archive: {datcheck.assert_archive_safe(dat, why='serve')['summary']}")
    # --keep-open IS WHAT MAKES --hold MEAN ANYTHING. `session.hold_open` is
    # gated on `keep_open`, which otherwise only the tape chain sets -- so every
    # run of this command before 2026-08-13 asked for 40 s of client time and
    # held for none of it, tearing down as soon as the body reached the map
    # (MEASURED: the two runs of the serve pair started 17 s apart under
    # `--hold 40`). Nothing failed, because the client compiles the map during
    # LOAD and that fits; the flag was describing a wait that was not happening,
    # and a bigger map is exactly where that stops being free.
    # --area rides in --game-args, which session.py forwards to the gamesrv. It
    # is what makes the zone POPULATED rather than empty ground: the server
    # serves this area's spawn rows at their own coordinates and checks each one
    # against the navmesh it pre-warmed. Passed always, so an area with no rows
    # says so in the log rather than quietly serving the global test enemy in
    # the middle of somebody's arrangement.
    game_args = f"--map {map_id}" + (f" --area {area}" if area else "")
    return subprocess.run(
        [sys.executable, session, "--replace", "--keep-open", "--hold", str(hold),
         "--warn", "3", "--exe", exe,
         "--game-args", game_args], text=True, env=env).returncode


def trapezoid_count(dat, file_id):
    """How many trapezoids the client's compiler actually built, from the row."""
    with Archive(dat) as ar:
        pm = pathmap.PathingMap.load(file_id, archive=ar)
    return len(pm.trapezoids)


def harness_source_dir():
    """The `source:` line THIS tree's gamesrv prints. -> str

    `authsrv.py` prints `source:    <its own directory>` at start-up, so the
    line names the WORKTREE that produced a capture. deploy.py lives at
    <tree>/toolkit/mapdata/, so the authsrv beside it is <tree>/toolkit/authsrv.
    """
    return os.path.normcase(os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     os.pardir, "authsrv")))


def log_source(log, probe=8192):
    """The directory named by a gamesrv log's `source:` line, or None.

    Read from the HEAD of the file: the line is printed at start-up, and these
    logs run to megabytes.
    """
    try:
        with open(log, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(probe)
    except OSError:
        return None
    m = re.search(r"^source:\s+(.+?)\s*$", head, re.M)
    return os.path.normcase(os.path.abspath(m.group(1))) if m else None


def newest_harness_log(after, source=None):
    """The gamesrv log of the newest harness run started after `after`.

    `source`, when given, RESTRICTS the search to captures this tree produced.

    WHY, AND IT IS NOT HYPOTHETICAL. `vault/captures/harness/` is shared by
    every session on this machine, and on 2026-08-21 THREE were running at
    once. This function used to take the newest log by mtime across the whole
    directory, so a peer session's run that happened to land inside our window
    was indistinguishable from our own -- and `serve_run` would then score OUR
    verdict off THEIR navmesh line. That is not a far-fetched race: the same
    ambiguity misled a reader by hand the same day, and the fix they used by
    hand is the one applied here -- `authsrv` prints `source: <its directory>`,
    which names the worktree, and no two worktrees share one.

    Passing `source=None` restores the old behaviour deliberately, for callers
    with no tree to match against; it is not the default anywhere.
    """
    root = os.path.join(vaultpath.require_dir(), "captures", "harness")
    best, best_t, skipped = None, after, []
    for name in os.listdir(root):
        d = os.path.join(root, name)
        log = os.path.join(d, "gamesrv.log")
        if not os.path.isfile(log):
            continue
        t = os.path.getmtime(log)
        if t <= best_t:
            continue
        if source is not None:
            got = log_source(log)
            if got != source:
                skipped.append((name, got))
                continue
        best, best_t = log, t
    if best is None and skipped:
        # Say so. A silent None here reads as "the harness wrote nothing",
        # which is a different diagnosis with a different fix.
        print(f"  note: {len(skipped)} newer capture(s) skipped as another "
              f"tree's: " + ", ".join(f"{n} ({s})" for n, s in skipped[:3]))
    return best


NAVMESH_RE = re.compile(
    r"\[map\] navmesh 0x([0-9A-Fa-f]+): (\d+) planes, (\d+) trapezoids")

# `area 'sculpt': 3 of 3 placed`. Checked because the alternative was measured:
# on the first populated run `spawn_population` threw inside instance bring-up,
# every body was absent, and NOTHING said so -- harness rc 0, all six map
# readback checks green (correctly, they are about the map), the serve check
# matched the navmesh, exit 0. The only evidence was a traceback in a log
# nobody was reading.
PLACED_RE = re.compile(r"area '([^']+)': (\d+) of (\d+) placed")

# `area 'plaza': no population rows; the world is the player and the geometry`
# -- `spawn_population`'s OTHER legitimate exit, and it is a VERDICT rather than
# an absence. The distinction this pattern draws is the whole point: a server
# that threw on the way to placing bodies prints NEITHER line, so "no line at
# all" still means what it meant. This line is positive evidence the server
# reached spawn_population, evaluated the area and had nothing to place.
#
# It was scored as a serve FAILURE until 2026-08-20. Both arms of WORLDMAPS-W2
# hit it: the navmesh half of the check passed in each (55 trapezoids, the
# server's own number against the archive's), the map was correct, and deploy
# still exited 1 saying "the client walked on our map and the server did not" --
# which was false. `vault/research/worldmaps/WORLDMAPS-W2-RUN.md` RESULTS, P6.
UNPOPULATED_RE = re.compile(
    r"area '([^']+)': no population rows; the world is the player and the "
    r"geometry")

# The three verdicts a serve run can carry. UNPOPULATED is not a softened FAIL
# and not a quiet PASS: the mesh was served and proven, and the area is empty on
# purpose. It gets its own word so a transcript cannot be read either way.
SERVE_PASS = "PASS"
SERVE_UNPOPULATED = "SERVED-UNPOPULATED"
SERVE_FAILED = "FAILED"


def spawn_row_count(world, area):
    """How many spawn rows OUR content reader binds to `area`.

    Mirrors the two predicates `authsrv.area_population` filters on -- the row
    names this area, and the row is enabled -- and deliberately nothing else:
    the rest of that function is set validation that RAISES rather than
    filters, so a row it would reject is a row that stops the server, not one
    that quietly drops out of this count.

    It exists to be a SECOND READER. Without it `SERVED-UNPOPULATED` would be a
    verdict that cannot fail -- the server says "nothing to place", we write it
    down, done -- and a population that genuinely went missing would read as a
    clean run. With it, the server's claim is checked against the content the
    same content store hands us, and the two disagreeing is a real finding.
    """
    return sum(1 for row in world.rows("spawn").values()
               if row.get("area") == area and row.get("enabled", True))


def serve_run(exe, session, dat, map_id, hold, expect_traps, file_id,
              area=None, expect_rows=None):
    """A SECOND run, unarmed, that proves the SERVER read our mesh.

    WHY TWO RUNS, and it is not a scheduling detail. `--install` arms the head
    to zero so the client is forced to recompile, so at the moment the server
    starts there is no compiled mesh in the archive to read -- and once the
    client is up it holds the archive open exclusively, so reading it later
    fails (EACCES). The run that PRODUCES the mesh can therefore never serve it.
    This one starts from an archive that already holds it, with nothing else
    open, which is the only configuration where the server can win.

    The verdict is the server's OWN log line rather than anything we compute:
    `[map] navmesh 0x287D3: 1 planes, 13 trapezoids` must name the count we
    just read out of the archive. Comparing against a number we predicted would
    be a check that cannot fail -- this compares two independent readers of the
    same bytes, ours through `pathmap` and the server's through its own load.

    Returns `(verdict, note)` where verdict is one of `SERVE_PASS`,
    `SERVE_UNPOPULATED` or `SERVE_FAILED`. THE MESH IS THE LOAD-BEARING HALF and
    it is not negotiable by the other one: a trapezoid count that disagrees with
    the archive is `SERVE_FAILED` whatever the population did, and an empty area
    can only ever downgrade a PASS to UNPOPULATED, never lift a FAILED.
    """
    t0 = time.time()
    rc = launch(exe, session, dat, map_id, hold, area=area)

    # THE HARNESS RC IS A VERDICT, and this used to drop it into an f-string
    # and carry on. A run whose harness failed has no evidence worth reading:
    # whatever log turns up next is either truncated or somebody else's.
    if rc != 0:
        return SERVE_FAILED, (f"  harness rc {rc} -- the run itself failed, so "
                              f"nothing below was measured. Look at the "
                              f"harness output above before anything here.")

    log = newest_harness_log(t0, source=harness_source_dir())
    if log is None:
        return SERVE_FAILED, (f"  harness rc {rc}, but no gamesrv log from THIS "
                              f"tree ({harness_source_dir()}) was written after "
                              f"the launch")
    with open(log, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    hits = NAVMESH_RE.findall(text)
    where = os.path.basename(os.path.dirname(log))
    if not hits:
        why = ("PRE-WARM FAILED" if "PRE-WARM FAILED" in text
               else "no navmesh line at all")
        return SERVE_FAILED, (f"  harness rc {rc}; {where}: {why} -- the server "
                              f"served no collision")
    # WHICH MAP DID IT LOAD? `fid` used to reach only the note string, so a
    # navmesh line for a DIFFERENT map scored this run as long as its trapezoid
    # count matched -- and the biome donor 0x1B97D is pre-warmed at 6120
    # trapezoids in every run of this harness. Select the line for OUR file id
    # rather than reading hits[0] and hoping.
    ours = [h for h in hits if int(h[0], 16) == int(file_id)]
    if not ours:
        got = ", ".join(f"0x{h[0]} ({h[2]} traps)" for h in hits[:4])
        return SERVE_FAILED, (f"  harness rc {rc}; {where}: the server loaded "
                              f"no navmesh for OUR map {file_id:#x} -- it "
                              f"named {got}. A count that matches by accident "
                              f"is not this map being served.")
    fid, planes, traps = ours[0]
    traps = int(traps)
    mesh_ok = traps == expect_traps
    verdict = SERVE_PASS if mesh_ok else SERVE_FAILED
    note = (f"  harness rc {rc}; {where}: server loaded 0x{fid} with "
            f"{planes} plane(s), {traps} trapezoids "
            f"({'MATCHES' if mesh_ok else 'DISAGREES WITH'} the "
            f"{expect_traps} in the archive)")

    # AND THE POPULATION, if one was asked for. Separate from the mesh check
    # because they fail separately: the bodies are created at instance
    # bring-up, well after the navmesh is read, so a throw there leaves the
    # mesh line correct and every map check green.
    #
    # THREE OUTCOMES, not two. `spawn_population` has two legitimate exits and
    # this used to recognise one of them, so an area with nothing in it scored
    # the same as a server that crashed mid-placement.
    if area:
        placed_hits = PLACED_RE.findall(text)
        empty_hits = UNPOPULATED_RE.findall(text)
        if placed_hits:
            _, placed, total = placed_hits[0]
            good = placed == total and int(total) > 0
            if not good:
                verdict = SERVE_FAILED
            note += (f"\n  area {area!r}: {placed} of {total} bodies placed"
                     + ("" if good else "  <-- NOT ALL"))
            # Our reader against the server's, same as the mesh half.
            if expect_rows is not None and int(total) != expect_rows:
                verdict = SERVE_FAILED
                note += (f"\n  area {area!r}: but OUR content reader binds "
                         f"{expect_rows} enabled spawn row(s) to it and the "
                         f"server counted {total} -- the two readers disagree "
                         f"about what lives here")
        elif empty_hits:
            # The server got there and had nothing to place. Only a downgrade:
            # if the mesh disagreed this stays FAILED.
            if verdict == SERVE_PASS:
                verdict = SERVE_UNPOPULATED
            note += (f"\n  area {area!r}: no population rows -- the server "
                     f"reached spawn_population and the area is empty. The "
                     f"mesh above is the served claim; there were no bodies "
                     f"to place, which is a state and not a failure")
            if expect_rows:
                verdict = SERVE_FAILED
                note += (f"\n  area {area!r}: AND THAT IS WRONG -- our content "
                         f"reader binds {expect_rows} enabled spawn row(s) to "
                         f"this area. The server loaded a world that does not "
                         f"have them, so the two disagree about the content, "
                         f"not about the map")
        else:
            verdict = SERVE_FAILED
            note += (f"\n  area {area!r}: NO population line of EITHER kind -- "
                     f"the server never got as far as evaluating the area "
                     f"(look for a traceback in {where}/gamesrv.log)")
    return verdict, note


def head_is_armed(dat, head_row):
    """Is this map head ALREADY the zero-length re-bloat trigger? -> bool

    ASKED OF THE ARCHIVE, WHICH IS THE WHOLE POINT (R1). `rebloat --arm` refuses
    a zero-length head -- rightly, since it cannot record a baseline mesh from a
    row that has none, and a second arm would overwrite the first journal with
    nothing. But "already armed" is not an error to `deploy`: the client
    recompiles on load either way, and this command is meant to be run
    repeatedly while iterating on a shape. The version before this guard turned
    every re-run after an interrupted one into a dead end.

    A CREATED HEAD IS BORN ARMED and lands here already zero length, so it takes
    the same branch for the same reason. The archive is asked rather than
    `create` ON PURPOSE: "we just made it empty" is our word for it, and
    `head.size == 0` is the row's -- the stronger of the two, and the one that
    still holds if a create half-ran, if a client rewrote the head between two
    deploys, or if the caller threaded the wrong flag.

    Factored out of `main` in 2026-08-20's residual pass for one reason: the
    guard was live and untestable, three lines inside a function that needs a
    vault, an archive, a donor and a content row to reach. It is the same
    predicate, on the same field, asked at the same moment.
    """
    with Archive(dat) as ar:
        head = next(e for e in ar.entries if e.index == head_row)
        return head.size == 0


def resolve_rows(archive, file_id):
    """(head row, partner row, partner reservation). By FILE ID, never remembered."""
    row = file_id_table(archive).get(file_id)
    if row is None:
        raise Refused(f"file id {file_id:#x} does not resolve in this archive")
    head = next((e for e in archive.entries if e.index == row), None)
    if head is None:
        raise Refused(f"file id {file_id:#x} names row {row}, which is absent")
    mi = mapchunks.MapIndex(archive)
    partner = mi.partner(head)
    reservation = ((partner.size + 511) // 512) * 512
    return head.index, partner.index, reservation


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--area", required=True)
    ap.add_argument("--repo-content-only", action="store_true",
                    help="load content from the repo alone, ignoring the vault "
                         "overlay. For when another session is mid-edit in "
                         "vault/content/ and its rows will not load -- it "
                         "narrows the world, it does NOT relax a check")
    ap.add_argument("--blend", help="a .blend to author the terrain from")
    ap.add_argument("--blender", help="path to the Blender executable")
    ap.add_argument("--dat", help="archive COPY to install into")
    ap.add_argument("--out", help="write the assembled map here")
    ap.add_argument("--install", action="store_true",
                    help="write the map and arm the re-bloat (needs --dat)")
    ap.add_argument("--stored-install", action="store_true",
                    help="write the Stripped partner UNCOMPRESSED, as every run "
                         "of this command before 2026-08-20 did. The default is "
                         "compression 8 because that is the shape retail's own "
                         "Stripped partners have; this is the CONTROL arm for "
                         "the client run that settles whether the map loader "
                         "takes ours, and the escape hatch if it does not")
    ap.add_argument("--launch", action="store_true",
                    help="run the harness at the area's own map id")
    ap.add_argument("--serve", action="store_true",
                    help="after the compile run, launch a SECOND time without "
                         "arming, so the server reads the mesh the client just "
                         "built and paths against OUR geometry. Needs --launch; "
                         "see serve_run() for why one run cannot do both")
    ap.add_argument("--hold", type=int, default=45)
    ap.add_argument("--exe", help="client to launch; defaults to "
                                  "the one beside --dat")
    args = ap.parse_args(argv)

    # The vault overlay is shared between sessions, so a half-written row over
    # there stops this command dead. --repo-content-only skips the overlay; it
    # does not weaken the provenance gate, which still runs on every row that
    # remains, and an area row lives in the repo anyway.
    world = (content_mod.load(vault_dir="") if args.repo_content_only
             else content_mod.load())
    area = world.get("area", args.area)
    dim = int(area["dims"])
    map_id = int(area["map_id"])
    map_row = world.get("map", str(map_id))
    file_id = int(map_row["file_id"])
    # `created` is a CLAIM THE ROW MAKES, not a fact about any archive: the row
    # says this area owns its file rather than displacing a retail one. Whether
    # the file exists yet is the archive's answer and is asked below.
    created_row = bool(map_row.get("created", False))
    # `reserve_bytes` is the AREA's claim, not the map's: it says how much room
    # this recipe wants for the geometry it produces, and the archive records no
    # such number anywhere (see `content/areas.toml`'s header and
    # `install_partner`). Absent means "no budget" and reproduces every run of
    # this command before WORLDMAPS-W5 exactly. It is only SPENDABLE on a row
    # this toolkit created -- `created_row` above -- which is why the two are
    # read together and threaded together.
    reserve = area_reserve(area)
    print(f"area {args.area!r}: {area['name']} -- map {map_id}, "
          f"{dim}x{dim}, file id {file_id:#x}"
          + ("  (created: this area owns its file)" if created_row else "")
          + (f"  (reserve {reserve} B)" if reserve else ""))

    # 1. geometry
    if args.blend:
        heights, exe, why, wr, frac = heights_from_blend(
            args.blend, dim, args.blender)
        print(f"  geometry: {args.blend} via Blender ({why})")
        print(f"  rounding: {frac} of {dim * dim} heights were fractional, "
              f"worst moved {wr:.3f} (cell pitch is 96)")
    else:
        gen = area.get("heights", "flat")
        if gen not in GENERATORS:
            raise Refused(f"unknown generator {gen!r}; "
                          f"known: {', '.join(sorted(GENERATORS))}")
        heights = GENERATORS[gen](dim)
        print(f"  geometry: generator {gen!r}")
    heights, worst = stx.snap_field(heights, dim, dim)
    print(f"  lattice snap: worst sample moved {worst}")

    # 2. borrow
    dat = args.dat or os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    # HOISTED ABOVE THE ARCHIVE, and it used to be computed just before the
    # write. `resolve_or_create` now needs the directory this run's build
    # products live in, because that is where `<area>_alloc.json` -- the record
    # that a created chain is OURS -- was written by the run that allocated it.
    # The expression is unchanged and depends on nothing the archive says.
    out = args.out or os.path.join(os.path.dirname(dat), f"{args.area}.bin")
    here = os.path.dirname(out)
    with Archive(dat) as ar:
        biome_row = _donor_row(ar, area, "biome donor",
                               "donor_file_id", "donor_row")
        const_row = _donor_row(ar, area, "constants donor",
                               "constants_file_id", "constants_row", 46196)
        donor = Donor(ar, biome_row, const_row)
        print(f"  constants row {donor.constants_row}: "
              f"{sum(len(v) for v in donor.constants.values())} B "
              f"(Header + Zones, structural -- must match our shape)")
        print(f"  biome row {biome_row}: "
              f"{len(donor.terrain_dep_ids)} terrain dep(s), "
              f"angle {donor.angle_index}, "
              f"env {'yes' if donor.env else 'no'}, "
              f"sound {'yes' if donor.sound else 'no'}")
        # RESOLVE, OR DECIDE TO CREATE. `created = true` on the maps.toml row
        # plus an id that binds nothing is the one combination that allocates;
        # everything else either installs into the chain that is there or
        # refuses naming what sits in the way. See resolve_or_create().
        #
        # `bound` IS ASKED ON EVERY RUN and `rows`/`create` only under --install:
        # deciding costs a refusal, reporting does not, and a build-only run that
        # cannot say whether the id binds anything is a dry run whose output does
        # not distinguish the case it was run to preview. See create_note().
        bound = file_id_table(ar, raw=True).get(file_id)
        rows, create = ((None, False) if not args.install
                        else resolve_or_create(ar, file_id, created_row,
                                               here=here, tag=args.area))

    # 3. assemble
    report = assemble(area, heights, donor, dim)

    # 3b. compress. Run on EVERY invocation, install or not: the ratio is a
    # measurement of the map that was just authored, it costs 0.04 s on the
    # largest area in content/, and it is the number the size preview below and
    # the verb the install picks are both computed from. A build-only run that
    # printed the stored size alone would be reporting a number no writer uses.
    stream, compression, size_note = install_bytes(
        report.blob, stored=args.stored_install)
    print(f"  {size_note}")

    # 4. verify
    for note in verify(report, area, heights, dim,
                       reservation=rows[2] if rows else None,
                       install_size=len(stream), compression=compression):
        print(f"  {note}")
    row_note = create_note(file_id, len(stream), bound, created_row, args.install)
    if row_note:
        print(f"  {row_note}")
    # AFTER `verify`'s reservation line and never inside it. That line predicts
    # a verb from the row's CURRENT reservation, which is the whole truth for a
    # row with no declared entitlement and a contradiction for one that has --
    # see `budget_note`.
    bud = budget_note(len(stream), rows[2] if rows else None, reserve,
                      created=created_row)
    if bud:
        print(f"  {bud}")

    if args.out or args.install:
        with open(out, "wb") as fh:
            fh.write(report.blob)
        print(f"  wrote {out}")

    if not args.install and not args.launch:
        print("\nbuild only. --install --dat <copy> to deliver it.")
        return 0

    if args.install:
        if create:
            print(f"\ncreating file id {file_id:#x} in {dat}: nothing binds it, "
                  f"and this area's map row asked to own its file")
            head_row, partner_row = create_chain(
                dat, file_id, report.blob, stream, compression, here,
                args.area, reserve=reserve)
        else:
            head_row, partner_row, reservation = rows
            print(f"\ninstalling into {dat}: head {head_row}, "
                  f"partner {partner_row}")
            verb = install_partner(dat, out, report.blob, stream, compression,
                                   head_row, partner_row, reservation,
                                   args.area, reserve=reserve,
                                   created=created_row)
            print(f"  the partner row was written by {verb}")
        # ARM ONLY IF IT IS NOT ALREADY ARMED. `rebloat --arm` refuses a
        # zero-length head -- rightly, since it cannot record a baseline mesh
        # from a row that has none, and a second arm would overwrite the first
        # journal with nothing. But "already armed" is not an error HERE: the
        # client recompiles on load either way, and this command is meant to be
        # run repeatedly while iterating on a shape. The previous version turned
        # every re-run after an interrupted one into a dead end.
        #
        # A CREATED HEAD IS BORN ARMED and lands here already zero length, so
        # this takes the same branch for the same reason. It is asked of the
        # ARCHIVE rather than of `create` on purpose: "we just made it empty" is
        # our word for it, and `head.size == 0` is the row's. See
        # `head_is_armed`, which is that question and nothing else.
        already = head_is_armed(dat, head_row)
        if already:
            print("  the head is already zero length -- already armed, so the "
                  "client will recompile; not arming twice")
        else:
            rc = subprocess.run(
                [sys.executable, os.path.join(HERE, "rebloat.py"), "--dat", dat,
                 "--file-id", hex(file_id), "--arm", "--confirm",
                 "--baseline", os.path.join(here, f"{args.area}_baseline.json"),
                 "--journal", os.path.join(here, f"{args.area}_rebloat.json")],
                text=True).returncode
            if rc != 0:
                raise Refused(f"rebloat refused (rc {rc})")

    if not args.launch:
        print("\ninstalled and armed. --launch to run the client.")
        return 0

    # 6. launch -- at the area's OWN map id, with the client that OWNS this
    # archive. Both halves are earned. A harness PASS means the client reached
    # A map, so pointing it at the default one compiles nothing (FINDINGS 54);
    # and every run directory has its own Gw.dat, so launching the default
    # client after arming a different copy runs against unarmed bytes -- which
    # is the same defect from the other side, and is what the first run of this
    # command did before `--exe` was derived here.
    exe = args.exe or os.path.join(os.path.dirname(dat), "Gw.exe")
    if not os.path.isfile(exe):
        raise Refused(f"no client beside the archive at {exe}; the client that "
                      f"reads {dat} is the only one that can load what we armed")
    session = os.path.join(os.path.dirname(HERE), "harness", "session.py")

    # THE SERVER MUST READ THE ARCHIVE WE JUST WROTE TO, and this is the whole
    # reason `RURIK_DAT` is set here rather than typed into a shell. The server
    # takes its navmesh from `vault/dat_study/Gw.dat` by default; we install the
    # authored map into a COPY, so after an install the two disagree about this
    # very map id -- the server would path against ArenaNet's geometry while the
    # client draws ours, and `contentids.preflight` refuses the launch for
    # exactly that reason (studies/maprows FINDINGS 8). It is a good guard and
    # the fix is not to bypass it: `--dat` already decides which client runs, so
    # it decides which world the server serves too. Both halves then name the
    # same file and the guard passes because the situation is actually right.
    #
    # THE HAZARD IS REAL AND THIS COMMENT USED TO DENY IT. It said the run
    # completes "because the server reads the world at startup, before the
    # client is launched". The world, yes; the NAVMESH, no -- `load_pathmap`
    # ran at instance bring-up, after the client was up and holding this
    # archive open exclusively, so the read returned EACCES and collision
    # turned off silently. Before this env var existed it was quieter still:
    # the server read `dat_study` and got ARENANET's geometry for the same map
    # id, whose walkable set is disjoint from ours (0 of 4,096 grid points
    # shared). `authsrv.prewarm_pathmap` now reads it at startup, which is the
    # only moment the archive both holds our map and is unlocked -- and that is
    # why serving an authored mesh takes TWO runs. See serve_run().
    print(f"launching {exe} at map {map_id}")
    rc = launch(exe, session, dat, map_id, args.hold, area=args.area)
    print(f"\nharness rc {rc}")

    # 7. read back. A harness PASS says the client reached a map; only this
    # says it compiled OURS.
    print("\nreadback -- what the compiler produced, against what we authored:")
    lines, bad = readback(dat, file_id, report.blob, area)
    for line in lines:
        print(line)
    if bad:
        print(f"\n{len(bad)} READBACK CHECK(S) FAILED")
        return 1

    # 8. serve. Everything above is about the CLIENT: it compiled our geometry
    # and drew it. Whether the SERVER agrees about the ground is a separate
    # claim and was false for every run of this command until 2026-08-13.
    if args.serve:
        traps = trapezoid_count(dat, file_id)
        print(f"\nserve -- a second run, unarmed, so the server reads the "
              f"{traps}-trapezoid mesh the client just built:")
        # Only claim a row count when we are reading the same world the server
        # will. `--repo-content-only` narrows OURS and not the server's, so the
        # two would differ for a reason that is about this flag rather than
        # about the content -- and a cross-check that fires on its own harness
        # is worse than no cross-check.
        expect_rows = (None if args.repo_content_only
                       else spawn_row_count(world, args.area))
        verdict, note = serve_run(exe, session, dat, map_id, args.hold, traps,
                                  file_id, area=args.area,
                                  expect_rows=expect_rows)
        print(note)
        if verdict == SERVE_FAILED:
            print("\nSERVE CHECK FAILED -- the client walked on our map and "
                  "the server did not")
            return 1
        if verdict == SERVE_UNPOPULATED:
            print(f"\nSERVE CHECK {SERVE_UNPOPULATED} -- the server served our "
                  f"mesh and area {args.area!r} has nobody in it. The map half "
                  f"is proven; the population half had nothing to prove.")
        else:
            print(f"\nSERVE CHECK {SERVE_PASS}")
    else:
        print("\nnote: the SERVER did not path against this mesh. It is in the "
              "archive now, so --serve runs again unarmed and proves it does.")

    print("\nrung G: the area was authored, delivered, compiled and verified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as exc:
        print(f"\nREFUSED: {exc}")
        sys.exit(2)
