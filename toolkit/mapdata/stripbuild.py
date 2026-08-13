"""Assemble a whole STRIPPED map the client will compile, from typed parameters.

`mapbuild.py` builds a Bloated map -- the finished article, which the client
loads directly. This builds the other stage: the input the client's own map
compiler reads, so the navmesh is produced by ArenaNet's converter rather than
by us. FINDINGS 43 put one of these through the retail client and got back a
mesh that follows ground we wrote.

    strip = build(32, 32, heights, seed=(2112.0, 1536.0),
                  constants=borrowed_constants(archive))
    open(path, "wb").write(strip.blob)      # -> a map row, then rebloat --arm

SEVEN CHUNKS, AND THE SET IS MEASURED RATHER THAN READ OFF A DISASSEMBLY.
FINDINGS 42 removed each one against a live client, one run apiece:

  0x10000000 Header       borrowed    absent -> `missing chunk`, no re-bloat
  0x1000000C Map Params   GENERATED   absent -> assert dims.x * XY_DIST == ...
  0x10000004 Props        GENERATED   absent -> `corrupt chunk 'Path ...'`
  0x10000003 Zones        borrowed    absent -> assert `state->zones`
  0x10000002 Terrain      GENERATED   absent -> `corrupt chunk 'Terrain ...'`
  0x11000002 Terrain Deps GENERATED   absent -> assert `deps`, TrnCreate:242
  0x10000008 Path         GENERATED   absent -> compiles, but NO MESH

An EIGHTH chunk exists exactly when the map places props: 0x11000004 Props
Dependencies, GENERATED from run-time file ids, rides immediately after the
props chunk the way retail carries it. FINDINGS 42's removal ladder ran on a
zero-prop map, which is why it is not in the table above; its absence has
never been client-measured against a props-bearing map and `build()` refuses
to produce that configuration.

FINDINGS 34's list, taken from the dispatch, had Collision in it (it is not
required) and did not have Terrain Dependencies (it is). This module follows the
measurement.

THREE RULES THAT ARE NOT STYLE, each of which cost a client run:

  * **Zones must precede Terrain in the file.** Terrain bloat reads
    `state->zones` and asserts on it, so chunk ORDER is load-bearing. `ORDER`
    below is the donor's own and `encode()` refuses any other.
  * **The rect is DERIVED, never passed in.** The converter asserts
    `dims.x * XY_DIST == mapRect.x1 - mapRect.x0`, which is `terrain.py`'s
    96.0 cell pitch in ArenaNet's own words. A rect that disagrees with the dims
    is an assert, not a wrong-looking map.
  * **The Path chunk's boundary point is a flood SEED and must stand on
    walkable ground.** FINDINGS 43: seeded at a rect corner that our own terrain
    made steep, the client asserted `segments->Count()` at PathData:365 -- zero
    segments for the decomposition. `check_seed()` refuses that here, because it
    is invisible from the corpus: every retail map's point is already somewhere
    sensible, so no amount of reading the archive would have found it.

PROVENANCE. Two chunks cannot be generated yet -- Header (8 B) and Zones
(34 B), 42 bytes in total. They are ArenaNet constants, and
`borrowed_constants()` reads them from the owner's own archive AT RUN TIME.
They are never stored here: not as literals, not as hex, not in a fixture.
`build()` raises `NoConstants` without them and `BuildReport` NAMES every
borrowed chunk rather than reporting one percentage.

PROPS WAS THE THIRD until 2026-08-12, and it was the one that mattered: it is
FINDINGS 34's hard gate, so while it was borrowed a map from this module could
not place a single object in the world. `props.StrippedProps` now generates it,
and `build()` takes a `props=` argument -- default `minimal()`, which is the
empty chunk and reproduces ArenaNet's own smallest one byte for byte. The
remaining two are 42 bytes of constant that nothing needs to vary.

The terrain dependency chunk is GENERATED, from file IDS read at run time --
ids are measurements and CLAUDE.md's ruling permits them. On the reference map
it lands byte-identical to ArenaNet's, which is a check the archive could have
failed.

    python toolkit/mapdata/stripbuild.py --dims 32 --out map.bin
"""

import argparse
import hashlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import Archive, ffna_chunks, DEFAULT_DAT  # noqa: E402
import mapbuild  # noqa: E402
import mapchunks  # noqa: E402
import mapfile  # noqa: E402
import pathchunk  # noqa: E402
import props as props_mod  # noqa: E402
import strippedterrain as stx  # noqa: E402
import terrain as trn_mod  # noqa: E402

HEADER = 0x10000000
MAP_PARAMS = 0x1000000C
PROPS = 0x10000004
PROPS_DEPS = 0x11000004
ZONES = 0x10000003
TERRAIN = 0x10000002
TERRAIN_DEPS = 0x11000002
PATH = 0x10000008
ENV = 0x10000009
ENV_DEPS = 0x11000009

# The donor's own order, which is also the corpus's single total order
# (FINDINGS §5: 321 ordered pairs, 0 contradictions). Zones before Terrain is
# the load-bearing part. PROPS_DEPS rides immediately after PROPS, exactly
# where retail puts it, and is present EXACTLY when the props chunk holds a
# prop -- `props.model` is an INDEX into it (0x0073DE0E), so a map with props
# and no list has models that cannot resolve, and a map without props never
# carries the list (the three zero-prop retail maps are exactly the three
# with no props-deps chunk).
ORDER = (HEADER, MAP_PARAMS, PROPS, PROPS_DEPS, ZONES, TERRAIN, TERRAIN_DEPS,
         PATH, ENV, ENV_DEPS)
#: The chunks encode() allows a payload to omit, each with its pairing rule
#: enforced in build(): PROPS_DEPS goes with props (retail 349/349), and the
#: ENV pair goes together or not at all -- FINDINGS 51's run put a borrowed
#: environment through the compiler and it carried VERBATIM, but the payload
#: is not understood, so it stays opt-in and BORROWED rather than generated.
OPTIONAL = (PROPS_DEPS, ENV, ENV_DEPS)
BORROWED = (HEADER, ZONES)
GENERATED = (MAP_PARAMS, PROPS, PROPS_DEPS, TERRAIN, TERRAIN_DEPS, PATH)

CELL = terrain_pitch = trn_mod.CELL_PITCH        # 96.0, and the client's XY_DIST
REFERENCE_PARTNER = 46197                        # the 32x32 template's stripped row

# FINDINGS 34 read two threshold sets off the classifier, 10/45/40 and
# 15/35/30 degrees, and could not say which is in force. MEASURED 2026-08-12
# by the ramp map (FINDINGS 48): the set is 15/35/30 and the walkable
# boundary is 35 -- a 32.0-degree strip compiled walkable and a 36.1-degree
# one did not, so the cut sits in (32.0, 36.1) and only 35 is inside it.
# The refusal below stays at 30 DELIBERATELY: it is now a measured 5-degree
# margin rather than merely the value safe under both readings, and a seed
# this close to the boundary would make every build a bet on the snap not
# steepening its cell.
SEED_UNWALKABLE_DEG = 30.0
SEED_UNSURE_DEG = 10.0


class NoConstants(ValueError):
    """No archive to read the three borrowed chunks from."""


class UnwalkableSeed(ValueError):
    """The Path chunk's boundary point stands on ground the flood cannot use."""


class BadOrder(ValueError):
    """Chunks in an order the converter's asserts do not survive."""


def borrowed_constants(archive=None, row=REFERENCE_PARTNER, path=None):
    """The three chunks we cannot generate, plus the terrain dependency IDS.

    Read at run time. The ids come back as NUMBERS, which is what makes the
    dependency chunk generated rather than copied.
    """
    own = archive is None
    if own:
        path = path or DEFAULT_DAT
        if not os.path.exists(path):
            raise NoConstants(
                f"no archive at {path}. The Header, Props and Zones chunks are "
                f"ArenaNet constants and are read at run time, never stored in "
                f"this repo. Point --dat at a copy of the owner's archive.")
        archive = Archive(path)
    try:
        entry = next((e for e in archive.entries if e.index == row), None)
        if entry is None:
            raise NoConstants(f"no MFT row {row} in this archive")
        blob = bytes(archive.read(entry))
    finally:
        if own:
            archive.close()

    out, dep_ids = {}, []
    for cid, off, size in ffna_chunks(blob):
        if cid in BORROWED:
            out[cid] = bytes(blob[off:off + size])
        elif cid == TERRAIN_DEPS:
            dep_ids = list(mapchunks.decode_dependencies(
                bytes(blob[off:off + size])).file_ids)
    missing = [f"0x{c:08X}" for c in BORROWED if c not in out]
    if missing:
        raise NoConstants(f"row {row} has no {', '.join(missing)}")
    if not dep_ids:
        raise NoConstants(f"row {row} has no terrain dependency chunk")
    return out, dep_ids


def default_rect(dim_x, dim_y):
    """The ONLY rect the converter accepts for these dims. Not a preference.

    `dims * XY_DIST`, asserted by the client at TrnDataBloat:191. Derived here
    so a caller cannot pass one that disagrees.
    """
    return (0.0, 0.0, dim_x * CELL, dim_y * CELL)


def cell_of(rect, seed, dim_x, dim_y):
    """Which grid cell a world point falls in, or None if it is off the map.

    The clamp is not tidying. Grid row 0 is world maxY, so a point on the rect's
    MINIMUM y -- `(0, 0)`, the obvious corner to reach for -- divides to row
    `dim_y`, one past the last. The first version of this function returned that
    and `check_seed` reported "outside the map rect" for a point demonstrably
    inside it, which is a wrong answer with a confident message. A point on any
    edge belongs to the cell it bounds.
    """
    if not (rect[0] <= seed[0] <= rect[2] and rect[1] <= seed[1] <= rect[3]):
        return None
    gx = min(max(int((seed[0] - rect[0]) // CELL), 0), dim_x - 1)
    gy = min(max(int((rect[3] - seed[1]) // CELL), 0), dim_y - 1)
    return gx, gy


def quad_slope_deg(heights, dim_x, dim_y, gx, gy):
    """The steeper of the two triangles of one cell's quad, in degrees.

    Corner samples at CELL spacing, which is how FINDINGS 34's flood reads them
    (`0x0072CFD0` builds vec3s whose x/y are +/-96.0). Returns 90.0 at the far
    edge, where there is no quad -- a caller asking about a cell that has no
    ground under it should be refused, not answered.
    """
    if not (0 <= gx < dim_x - 1 and 0 <= gy < dim_y - 1):
        return 90.0
    def h(x, y):
        return heights[trn_mod.Terrain.index(x, y, dim_x)]
    worst = 0.0
    for (ax, ay), (bx, by), (cx, cy) in (
            ((0, 0), (1, 0), (0, 1)), ((1, 0), (1, 1), (0, 1))):
        za, zb, zc = h(gx + ax, gy + ay), h(gx + bx, gy + by), h(gx + cx, gy + cy)
        ux, uy, uz = (bx - ax) * CELL, (by - ay) * CELL, zb - za
        vx, vy, vz = (cx - ax) * CELL, (cy - ay) * CELL, zc - za
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        flat = math.hypot(nx, ny)
        worst = max(worst, math.degrees(math.atan2(flat, abs(nz))))
    return worst


def check_seed(heights, dim_x, dim_y, rect, seed):
    """Refuse a seed the flood cannot start from. Returns its slope in degrees.

    This exists because of one client run. FINDINGS 43 seeded the boundary
    point at the rect's corner, which that map's own terrain made steep, and
    the client asserted `segments->Count()` -- zero segments, no mesh, no
    diagnosis without diffing four chunks against a donor.
    """
    cell = cell_of(rect, seed, dim_x, dim_y)
    if cell is None:
        raise UnwalkableSeed(f"seed {seed} is outside the map rect {rect}")
    gx, gy = cell
    slope = quad_slope_deg(heights, dim_x, dim_y, gx, gy)
    if slope > SEED_UNWALKABLE_DEG:
        raise UnwalkableSeed(
            f"seed {seed} lands on grid cell ({gx}, {gy}), whose quad slopes "
            f"{slope:.1f} degrees. That is unwalkable under BOTH of FINDINGS "
            f"34's threshold sets, and a flood seeded there produces no "
            f"segments at all -- the client asserts `segments->Count()` at "
            f"PathData:365 rather than building an empty mesh. Put the point "
            f"on ground the map means to be walkable.")
    return slope


class BuildReport:
    """What was generated, what was borrowed, and which chunks each covers."""

    __slots__ = ("blob", "origin", "sizes", "seed_slope", "rect", "dims")

    def __init__(self, blob, origin, sizes, seed_slope, rect, dims):
        self.blob = blob
        self.origin = dict(origin)
        self.sizes = dict(sizes)
        self.seed_slope = seed_slope
        self.rect = rect
        self.dims = dims

    @property
    def generated(self):
        return sum(n for c, n in self.sizes.items()
                   if self.origin[c] != "borrowed")

    @property
    def borrowed(self):
        return sum(n for c, n in self.sizes.items()
                   if self.origin[c] == "borrowed")

    @property
    def fraction_generated(self):
        total = self.generated + self.borrowed
        return self.generated / total if total else 0.0

    def borrowed_chunks(self):
        return tuple(c for c in ORDER
                     if c in self.origin and self.origin[c] == "borrowed")

    def show(self):
        print(f"stripped map: {len(self.blob)} B, {len(self.sizes)} chunks, "
              f"sha256 {hashlib.sha256(self.blob).hexdigest()[:16]}")
        print(f"  dims {self.dims[0]}x{self.dims[1]}  rect {self.rect}  "
              f"pitch {(self.rect[2] - self.rect[0]) / self.dims[0]:.1f}")
        print(f"  seed slope {self.seed_slope:.1f} deg"
              + ("  (under 10 -- flat enough to be certain)"
                 if self.seed_slope <= SEED_UNSURE_DEG else
                 "  (10..30 -- walkable under one threshold set, unknown "
                 "under the other)"))
        for cid in ORDER:
            if cid not in self.sizes:
                continue
            print(f"    0x{cid:08X} {mapchunks.chunk_label(cid)[:26]:<28}"
                  f"{self.sizes[cid]:>6} B   {self.origin[cid]}")
        print(f"  GENERATED {self.generated} B "
              f"({100 * self.fraction_generated:.2f}%), "
              f"BORROWED {self.borrowed} B, in "
              f"{', '.join(f'0x{c:08X}' for c in self.borrowed_chunks())}")


def build(dim_x, dim_y, heights, seed, constants, dep_ids, sequence=0,
          tiles=None, sync_hash=0, sync_flag=0, props=None,
          prop_dep_ids=None, env_payload=None, env_dep_ids=None):
    """A whole Stripped map. `heights` is in `Terrain.index` order, integers.

    `props` is a `props.StrippedProps`, or None for an empty one. Empty is not
    the same as absent: FINDINGS 42 removed the chunk and the client refused the
    map, so `minimal()` is the floor rather than a shortcut.

    `prop_dep_ids` is the model file-id list for chunk 0x11000004, REQUIRED
    exactly when `props` holds a prop and REFUSED when it does not -- retail's
    own pairing. Every prop's `model` is an index into this list, and an index
    past its end is refused here because the client-side failure mode of an
    unresolvable model has never been measured and this module is not the
    place to find out by accident.

    `env_payload` + `env_dep_ids` are chunk 0x10000009 and its dependency
    ids, TOGETHER OR NOT AT ALL. The payload is an environment chunk this
    toolkit cannot author -- it is not understood -- so callers BORROW one
    from a donor map at run time (FINDINGS 51: Pre-Searing's carried
    VERBATIM through the compiler and brought the sky, the ambient light
    and the horizon water with it). It counts as borrowed in the report,
    named like every borrowed byte.
    """
    for cid in BORROWED:
        if cid not in constants:
            raise NoConstants(f"no borrowed chunk 0x{cid:08X}")
    rect = default_rect(dim_x, dim_y)
    slope = check_seed(heights, dim_x, dim_y, rect, seed)

    payload, origin = {}, {}
    for cid in BORROWED:
        payload[cid] = bytes(constants[cid])
        origin[cid] = "borrowed"

    payload[MAP_PARAMS] = mapbuild.encode_map_parameters(rect)
    origin[MAP_PARAMS] = "generated"

    sp = props_mod.StrippedProps.minimal() if props is None else props
    payload[PROPS] = sp.encode()
    origin[PROPS] = f"generated, {len(sp.props)} props"

    dep_list = list(prop_dep_ids or ())
    if sp.props and not dep_list:
        raise ValueError(
            f"{len(sp.props)} props but no prop_dep_ids. Every prop's `model` "
            f"is an INDEX into chunk 0x11000004 (0x0073DE0E), so a map that "
            f"places props must list the model files they resolve to. Pass "
            f"the file ids -- ids are measurements and are read at run time.")
    if dep_list and not sp.props:
        raise ValueError(
            f"{len(dep_list)} prop_dep_ids but no props. Retail never ships "
            f"the list without the props: the three zero-prop maps are "
            f"exactly the three with no props-deps chunk.")
    over = [(i, p.model) for i, p in enumerate(sp.props)
            if p.model >= len(dep_list)]
    if over:
        i, m = over[0]
        raise ValueError(
            f"prop {i} names model {m} but prop_dep_ids lists only "
            f"{len(dep_list)} file(s); an index past the list cannot resolve "
            f"and the client's failure mode for that has never been measured")
    if dep_list:
        payload[PROPS_DEPS] = mapchunks.encode_dependencies(dep_list)
        origin[PROPS_DEPS] = f"generated from {len(dep_list)} run-time ids"

    trn = stx.StrippedTerrain.build(dim_x, dim_y, heights, tiles=tiles)
    payload[TERRAIN] = trn.encode()
    origin[TERRAIN] = "generated"

    payload[TERRAIN_DEPS] = mapchunks.encode_dependencies(dep_ids)
    origin[TERRAIN_DEPS] = f"generated from {len(dep_ids)} run-time ids"

    payload[PATH] = pathchunk.StrippedPath(
        sequence=sequence, boundary=[tuple(seed)],
        sync_hash=sync_hash, sync_flag=sync_flag).encode()
    origin[PATH] = "generated"

    if (env_payload is None) != (env_dep_ids is None):
        raise ValueError(
            "env_payload and env_dep_ids go together or not at all: the "
            "payload references files only the id list can resolve, and an "
            "id list with no payload describes nothing")
    if env_payload is not None:
        payload[ENV] = bytes(env_payload)
        origin[ENV] = "borrowed"
        payload[ENV_DEPS] = mapchunks.encode_dependencies(list(env_dep_ids))
        origin[ENV_DEPS] = (f"generated from {len(list(env_dep_ids))} "
                            f"run-time ids")

    blob = encode(payload)
    return BuildReport(blob, origin, {c: len(payload[c]) for c in payload},
                       slope, rect, (dim_x, dim_y))


def encode(payload):
    """The container, in ORDER. Refuses any other, because order is a gate.

    The OPTIONAL chunks may be absent -- `build()` enforces their pairing
    rules. Everything else is FINDINGS 42's measured requirement, one client
    run per removal.
    """
    ids = tuple(payload)
    want = set(ORDER) - {c for c in OPTIONAL if c not in ids}
    if set(ids) != want:
        raise BadOrder(f"expected exactly {[f'0x{c:08X}' for c in sorted(want)]}, "
                       f"got {[f'0x{c:08X}' for c in ids]}")
    chunks = [mapfile.Chunk(cid, payload[cid], mapfile.FORM_OPAQUE)
              for cid in ORDER if cid in payload]
    return mapfile.MapFile(chunks=chunks).encode()


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--dims", type=int, default=32)
    ap.add_argument("--height", type=int, default=-13)
    ap.add_argument("--seed", default=None,
                    help="world x,y for the Path chunk's boundary point; "
                         "defaults to the middle of the map")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    n = a.dims
    heights = [a.height] * (n * n)
    rect = default_rect(n, n)
    if a.seed:
        seed = tuple(float(v) for v in a.seed.split(","))
    else:
        seed = ((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0)
    try:
        constants, dep_ids = borrowed_constants(path=a.dat)
    except NoConstants as exc:
        print(f"REFUSED: {exc}")
        return 2
    rep = build(n, n, heights, seed, constants, dep_ids)
    rep.show()
    if a.out:
        with open(a.out, "wb") as fh:
            fh.write(rep.blob)
        print(f"  wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
