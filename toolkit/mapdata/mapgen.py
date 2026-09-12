"""The height-field generators and their design constants.

WHAT A GENERATOR IS. A name in `GENERATORS` mapped to a function of `(dim)`
that returns `dim * dim` stored heights -- negated elevation, "more negative is
HIGHER" -- in the terrain codec's own tiled order. `deploy.main` picks one by
name and hands it to the snap, and `--blend` swaps the whole stage out for
`heights_from_blend`, which runs a real Blender scene through
`tools/blender/export_gwmap.py` and reads the interchange back. Everything here
is OFFLINE arithmetic: no archive, no vault, no client.

WHY THE CONSTANTS TRAVEL WITH THE FUNCTIONS. `RAMP_STRIPS`, `RAMP_FINE_STRIPS`
and the twenty-one `ASH_*` values are not configuration -- they are the MEASUREMENT
each map was built to take, and the comments above them record the run that
chose them (FINDINGS 48's slope boundary, WORLDMAPS-W20's failed positive
control, the Ashcoil MASTER RULE that makes the caldera legal by construction).
Separating a ramp from the strip table that gives its angles their meaning
would leave two files each of which is wrong on its own.

POINTERS OUT, because several things named below did not move:

  * `deploy.main` is the only consumer INSIDE `deploy.py` -- the readers from
    outside it are the last bullet. It reads `GENERATORS` and
    `heights_from_blend` as BARE names through the re-export at the site this
    code left, and `inspect.signature(gen_fn).parameters` there is what lets
    `gen_ramp_uniform` take `area=` while the other five do not.
  * `Refused` is `deploy`'s own, from `deployrefuse.py`, for the reason that
    module's docstring gives: `test_deploy.py` §10(e2) asserts TYPE identity,
    so every refusal below must raise that class and not a new one.
  * The SNAP the comments keep referring to is `strippedterrain.snap_field` /
    `snap_block`, applied by `deploy.main` on the line after the generator
    returns -- `assemble` is handed a field that is already snapped and never
    snaps one itself. None of it happens here; a generator emits the authored
    field and the codec's lattice is allowed to move it, which is the
    difference these maps exist to print.
  * `HERE` is recomputed below rather than imported, and resolves identically:
    this module sits in `toolkit/mapdata/` beside `deploy.py`, so
    `heights_from_blend`'s `dirname(dirname(HERE))/tools/blender` is the same
    directory it always was. Moving this file elsewhere would silently change
    that path -- the same trap `harness_source_dir` stayed in `deploy.py` for.
  * `mapscale.py` and `tilerender.py` read `deploy.GENERATORS`, and
    `test_deploy.py` reads `deploy.gen_plaza` in five sections (4, 7, 8, 9 and
    10), through that re-export -- so the functions this module defines are the
    ones they run.
"""

import json
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapexport  # noqa: E402
import terrain as trn_mod  # noqa: E402
from deployrefuse import Refused  # noqa: E402


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


def gen_ramp_uniform(dim, base=-13, area=None):
    """`gen_ramp`'s bands with ONE slope everywhere -- no strips, no seams.

    The area declares `ramp_dz`, the height change per 96-unit cell. Keep it a
    multiple of 4 and the lattice snap moves nothing (WORLDMAPS-W20); the slope
    is then exactly atan(dz / 96).

    This exists because W20's four-strip map confounds two things at once. Its
    class-2 strips DID touch the flat class-0 apron and still did not mesh,
    which is not what "class 2 needs a class-0 neighbour" predicts, and the same
    map also varied the steep lateral seams between strips. One slope over the
    whole map removes the seams and the neighbours together, so what is left is
    the only question that matters: can the flood climb this slope out of a flat
    apron, on its own?
    """
    if dim != 32:
        raise Refused(f"the uniform ramp is 32x32 by construction, not "
                      f"{dim}x{dim}: its band rows are cell indices")
    dz = int((area or {}).get("ramp_dz", 88))
    rise_cells = RAMP_APRON_TOP - RAMP_TOP
    out = [0] * (dim * dim)
    for gy in range(dim):
        for gx in range(dim):
            if gy >= RAMP_APRON_TOP:
                lift = 0
            elif gy >= RAMP_TOP:
                lift = dz * (RAMP_APRON_TOP - gy)
            else:
                lift = dz * rise_cells
            out[gy * dim + gx] = base - lift
    return out


# Ashcoil Caldera -- WORLDMAPS showcase map, authored 2026-08-22. The design
# is the winner of a three-designer panel (vertical drama / enclosure and
# reveal / natural coherence) with the judge's grafts folded in; the geometry
# was validated OFFLINE before any compile: zero cells in the forbidden
# 40-45 degree band, flood(<=64 steps) == flood(<=111 steps) under 4- and
# 8-connected adjacency, every waypoint of the intended walk connected to the
# seed, exact codec round-trip, snap worst 4.
#
# MASTER RULE (what makes the whole surface legal by construction, under the
# cut-45 slope set -- the area row MUST carry top byte 2):
#   - walkable ground keeps its pre-quantization gradient <= 40 units/cell,
#     so after 48-quantization every axial step is 0 or 48 (30.2 deg) and no
#     triangle plane exceeds 35.3 deg;
#   - walls are hard discontinuities >= 192 (>= 144 after the snap, 56.3 deg);
#   - nothing between 48 and 144 ever appears, so the 40-45 band W20/W23
#     showed to be conditionally meshed is unreachable by construction;
#   - elevated roads leave flat ground only through SLOTS flanked by high
#     rock that terminates abruptly -- a tapering ledge always sweeps the
#     forbidden band somewhere on its flank; a slot never does.
ASH_TAU = 2.0 * math.pi
ASH_Q = 48.0
ASH_FLOOR = 48.0
ASH_CLIMB = 1008.0          # 21 risers of 48 over one full turn
ASH_RIM = ASH_FLOOR + ASH_CLIMB
ASH_FLANK = 432.0           # mouth-slot inner ridge (top is pruned)
ASH_KNOB = 1248.0           # top-out outer knob
ASH_BANK = 1248.0           # draw flanks
ASH_BOWL = 480.0            # terminal bowl floor
ASH_VALLEY = 672.0          # sealed remainder of the ring valley
ASH_CROWN = 288.0           # crown peak = rim + 288 = 1344
ASH_THETA0 = -0.25          # the seam (great scarp) angle
ASH_P_ENTER = 0.035         # open entrance arc (S - FLOOR <= 48)
ASH_P_SLOT = 4.0 / 21.0     # mouth slot ends where S - FLOOR = 192
ASH_P_KNOB = 17.0 / 21.0    # knob starts where RIM - S = 192
ASH_P_EXIT = 0.97           # knob ends; the road merges onto the rim
ASH_P_CROWN = 0.10          # crown centre angle (fraction of a turn)
ASH_P_DRAW = 0.50           # draw entrance angle
ASH_DRAW_LEN = 0.16         # draw arc length (fraction of a turn)
ASH_DRAW_GAP = 0.012        # bank gap at the draw entrance
ASH_POOL = (27.0, 27.0, 4.6, 1.3)   # cx, cy, outer radius, flat core


def _ash_sstep(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


def _ash_elevation(gx, gy):
    """Elevation in world units, positive UP, in 64x64 design space."""
    dx = gx - 31.5
    dy = gy - 31.5
    r = math.hypot(dx, dy)
    theta = math.atan2(dy, dx)
    p = ((theta - ASH_THETA0) % ASH_TAU) / ASH_TAU   # coil progress from seam

    # strata crinkle: every radial boundary wobbles in lockstep, so band
    # widths -- and therefore every jump -- are preserved
    wob = (0.7 * math.sin(3.0 * theta + 1.7)
           + 0.4 * math.sin(7.0 * theta - 0.4))
    rw = r + wob

    S = ASH_FLOOR + ASH_CLIMB * p                    # the coil's profile

    if rw <= 11.0:
        # crater floor; the mouth-slot flank ridge; the sunken pool
        if 9.5 < rw and ASH_P_ENTER <= p <= ASH_P_SLOT:
            return ASH_FLANK
        f = ASH_FLOOR
        pcx, pcy, pro, prf = ASH_POOL
        dpool = math.hypot(gx - pcx, gy - pcy)
        if dpool < pro:
            # to -48: one quantum below the water plane, in case it renders
            f = ASH_FLOOR - 96.0 * _ash_sstep((pro - dpool) / (pro - prf))
        return f

    if rw <= 14.5:
        return S                                     # the coil shelf

    if rw <= 21.0:
        # rim plateau; the top-out knob; the crown cone
        if rw <= 16.5 and ASH_P_KNOB <= p <= ASH_P_EXIT:
            return ASH_KNOB
        # the draw's UPHILL bank is carved out of the rim annulus -- without
        # it the descending draw floor sits directly against the plateau and
        # their difference sweeps through the forbidden band (caught by the
        # offline validator as two 45.0-degree cells at the rw = 21 seam)
        dp = (p - ASH_P_DRAW) % 1.0
        if ASH_DRAW_GAP < dp <= ASH_DRAW_LEN and rw > 20.0:
            return ASH_BANK
        f = ASH_RIM
        tc = ASH_THETA0 + ASH_P_CROWN * ASH_TAU
        dc = math.hypot(gx - (31.5 + 17.75 * math.cos(tc)),
                        gy - (31.5 + 17.75 * math.sin(tc)))
        if dc < 11.0:
            f += ASH_CROWN * _ash_sstep(1.0 - dc / 11.0)
        return f

    if rw <= 26.0:
        # ring valley: the draw, its banks, the bowl, the sealed remainder
        dp = (p - ASH_P_DRAW) % 1.0
        if dp <= ASH_DRAW_LEN and 21.0 < rw <= 23.5:
            if dp <= ASH_DRAW_GAP:
                return ASH_RIM               # entrance gap: step off the rim
            t = (dp - ASH_DRAW_GAP) / (ASH_DRAW_LEN - ASH_DRAW_GAP)
            return ASH_RIM - (ASH_RIM - ASH_BOWL) * t
        if dp <= ASH_DRAW_LEN and 23.5 < rw <= 24.5:
            return ASH_BANK                  # downhill bank; top is pruned
        if ((p - (ASH_P_DRAW - 0.02)) % 1.0) <= 0.32:
            return ASH_BOWL                  # terminal bowl
        return ASH_VALLEY

    # edge bulwark: chunky 192-quantum terraces, serrated, capped at 1248 so
    # the crown (1344) stays the highest silhouette on the map
    db = min(gx, gy, 63.0 - gx, 63.0 - gy)
    ser = (0.5 * math.sin(0.9 * gx + 1.3 * gy)
           + 0.5 * math.sin(1.7 * gx - 0.7 * gy))
    k = max(0, min(4, int(round(2.0 + 2.0 * (1.0 - db / 7.0) + ser))))
    return ASH_BOWL + 192.0 * k


def gen_caldera(dim, base=None):
    """Ashcoil Caldera. Designed at 64x64; other dims sample the design.

    At any dim other than 64 the cell pitch changes and every slope with it,
    so ONLY dims = 64 is the map -- other sizes exist so the suite's lattice
    section can run every generator at its fixture's dims.

    Stored heights are negated elevation ("more negative is HIGHER") and are
    written through Terrain.index: at 64x64 the array is four tiles and a
    flat gy*dim+gx write would scramble the quadrants.
    """
    scale = 63.0 / (dim - 1) if dim > 1 else 1.0
    out = [0] * (dim * dim)
    for gy in range(dim):
        for gx in range(dim):
            e = _ash_elevation(gx * scale, gy * scale)
            out[trn_mod.Terrain.index(gx, gy, dim)] = -int(round(e))
    return out


# SLICE-B6: the corridor. A straight walkable floor between two walls the
# client will not mesh, running the LONG axis of a rectangular map -- the
# first non-square footprint this toolkit has authored (SLICE-U4).
#
# THE WALLS ARE SLOPE, NOT PROPS. WORLDMAPS-W20/W23: ground steeper than the
# slope set's cut is class-2 and does not mesh, and class-2 ground cannot be
# climbed out of flat ground -- so a bank of CORRIDOR_WALL_DZ per 96-unit cell
# (atan(120/96) = 51.3 degrees, past 45 in BOTH threshold sets of FINDINGS 34)
# is a wall the flood fill stops at, and the plateau above it is pruned by
# connectivity. Every rise is a multiple of 4 on 4x4-ALIGNED columns and rows
# so the lattice snap moves nothing (W20's instrument, `gen_ramp_fine`) -- the
# first draft put the floor's edge at column 10 and the snap moved one sample,
# because `snap_block` projects each 4x4 sub-block on its own and a boundary
# inside one quantises the whole block. 16 floor cells from a 32-wide map
# leaves banks at 4..7 and 24..27: every edge on a multiple of 4.
CORRIDOR_BASE = -13         # the floor, negated elevation like every field here
CORRIDOR_FLOOR = 16         # cells of flat floor across the short axis (1536 u)
CORRIDOR_WALL_CELLS = 4     # cells of bank on each side before the plateau
CORRIDOR_WALL_DZ = 120      # per cell; 51.3 degrees, class-2 under both sets
CORRIDOR_END_CELLS = 4      # the same bank closes both ends of the long axis


def gen_corridor(dim, dim_y=None, area=None):
    """A flat corridor along the long axis, walled by class-2 banks.

    `dim` is the SHORT axis (x) and `dim_y` the long one; called with one
    argument -- the way every other generator is, and the way `test_deploy`
    section 1 and `tilerender` call all of them -- it is a square corridor.
    """
    dim_y = dim if dim_y is None else dim_y
    out = [0] * (dim * dim_y)
    half = CORRIDOR_FLOOR // 2
    lo, hi = dim // 2 - half, dim // 2 + half - 1        # floor columns
    for gy in range(dim_y):
        for gx in range(dim):
            # distance in cells from the floor, on each axis
            dx = lo - gx if gx < lo else (gx - hi if gx > hi else 0)
            dy = (CORRIDOR_END_CELLS - gy if gy < CORRIDOR_END_CELLS
                  else (gy - (dim_y - 1 - CORRIDOR_END_CELLS)
                        if gy > dim_y - 1 - CORRIDOR_END_CELLS else 0))
            d = min(max(dx, dy), CORRIDOR_WALL_CELLS)
            out[trn_mod.Terrain.index(gx, gy, dim)] = (
                CORRIDOR_BASE - CORRIDOR_WALL_DZ * d)
    return out


GENERATORS = {"flat": gen_flat, "plaza": gen_plaza, "ramp": gen_ramp,
              "corridor": gen_corridor,
              "ramp_fine": gen_ramp_fine,
              "ramp_uniform": gen_ramp_uniform,
              "caldera": gen_caldera}


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
