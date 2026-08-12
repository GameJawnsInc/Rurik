"""The Stripped-map assembler: the three rules that each cost a client run.

`stripbuild.py` emits the input the CLIENT's map compiler reads, so most of what
it must get right is not checkable by decoding our own output -- the client is
the judge, and FINDINGS 43 is the run where it agreed. What this file can do is
pin the rules that run discovered, each of which is a refusal rather than a
convention, and each of which has a positive control so the refusal cannot be
"refuse everything".

  * ORDER. Zones must precede Terrain, because terrain bloat reads
    `state->zones` and asserts on it (FINDINGS 42).
  * THE RECT. Derived as `dims * 96.0`, because the converter asserts
    `dims.x * XY_DIST == mapRect.x1 - mapRect.x0` (FINDINGS 42). It cannot be
    passed in, so the test asserts it cannot be got wrong.
  * THE SEED. The Path chunk's boundary point must stand on walkable ground.
    FINDINGS 43 seeded a rect corner its own terrain made steep and the client
    asserted `segments->Count()` at PathData:365. Section 3 is the reason this
    file exists: the failure is invisible from the corpus, because every retail
    map's point is already somewhere sensible.

PROVENANCE IS TESTED, NOT ASSUMED. Section 5 reads this module's own syntax tree
and requires no bytes literal over two bytes in it, and greps the source for the
borrowed payloads it just read from the archive -- raw, hex, spaced hex and `\\x`
escapes -- because a draft that quoted constants in a DOCSTRING would pass the
syntax-tree scan (that is how `test_mapbuild.py` caught one).

Sections 0-3 need no vault: they run on PLACEHOLDER constants of our own, which
is also the only way to check that `NoConstants` refuses rather than falling
back to something. Sections 4-6 need `vault/dat_study/Gw.dat`.

    python toolkit/mapdata/test_stripbuild.py
"""

import ast
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
import mapbuild  # noqa: E402
import mapchunks  # noqa: E402
import mapfile  # noqa: E402
import pathchunk  # noqa: E402
import stripbuild as sb  # noqa: E402
import strippedterrain as stx  # noqa: E402
import terrain as trn_mod  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR: 39, MEASURED from a green run on 2026-08-12 (guessed 44 first, which
# reddened the run at 39 -- which is what the floor is for). Sections 0 to 3c
# score 30 and need no vault; a vault-less run goes red rather than reporting
# a smaller success, because the corpus half is where "byte-identical to
# ArenaNet's" lives and a run without it has not checked what can fail.
LEDGER = checks.Ledger("stripbuild", floor=39)
check = checks.adopt(LEDGER)

DIMS = 32
FLAT = -13
RAISE = -1000
SPLIT = 12

# Ours, and deliberately not ArenaNet's: three payloads of the right SHAPE and
# the wrong content, so sections 0-3 exercise the whole builder with no vault.
PLACEHOLDER = {
    sb.HEADER: bytes(8),
    sb.PROPS: bytes(12),
    sb.ZONES: bytes(34),
}
PLACEHOLDER_IDS = [1, 2, 3, 4]


def flat_heights(dim=DIMS, h=FLAT):
    return [h] * (dim * dim)


def ridged_heights(dim=DIMS):
    """FINDINGS 43's field: a sawtooth over the low-x columns, flat elsewhere."""
    out = [0] * (dim * dim)
    for gy in range(dim):
        for gx in range(dim):
            out[trn_mod.Terrain.index(gx, gy, dim)] = (
                FLAT + (RAISE if (gx < SPLIT and (gx + gy) & 1) else 0))
    return out


def sections():
    print("\n0. the rect is derived, and cannot be got wrong")
    rect = sb.default_rect(DIMS, DIMS)
    check(rect == (0.0, 0.0, DIMS * 96.0, DIMS * 96.0),
          f"default_rect({DIMS}) == {rect}")
    check((rect[2] - rect[0]) / DIMS == 96.0,
          "and rect/dims is exactly XY_DIST, which the converter asserts")
    tree = ast.parse(open(sb.__file__, encoding="utf-8").read())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "build")
    args = [a.arg for a in fn.args.args]
    check("rect" not in args,
          f"build() has no rect parameter, so a caller cannot disagree with "
          f"the dims  {args}")

    print("\n1. the order rule, and the refusal that enforces it")
    payload = dict(PLACEHOLDER)
    payload[sb.MAP_PARAMS] = mapbuild.encode_map_parameters(rect)
    payload[sb.TERRAIN] = stx.StrippedTerrain.build(
        DIMS, DIMS, flat_heights()).encode()
    payload[sb.TERRAIN_DEPS] = mapchunks.encode_dependencies(PLACEHOLDER_IDS)
    payload[sb.PATH] = pathchunk.StrippedPath(
        boundary=[(1536.0, 1536.0)]).encode()
    blob = sb.encode(payload)
    ids = [c.chunk_id for c in mapfile.MapFile.decode(blob).chunks]
    check(ids == list(sb.ORDER), f"encode() emits ORDER  {len(ids)} chunks")
    check(ids.index(sb.ZONES) < ids.index(sb.TERRAIN),
          "and Zones precedes Terrain, which terrain bloat asserts on")
    short = dict(payload)
    short.pop(sb.ZONES)
    refused = False
    try:
        sb.encode(short)
    except sb.BadOrder:
        refused = True
    check(refused, "a missing chunk is REFUSED, not emitted short")

    print("\n2. the container is real, and the terrain survives it")
    mf = mapfile.MapFile.decode(blob)
    check(mf.encode() == blob, "the container round-trips byte-identically")
    back = stx.StrippedTerrain.decode(
        next(c for c in mf.chunks if c.chunk_id == sb.TERRAIN).payload())
    check(back.heights == [float(v) for v in flat_heights()],
          "and the height field survives its own codec, sample for sample")
    check(back.dim_x == DIMS and back.dim_y == DIMS,
          f"dims come back {back.dim_x}x{back.dim_y}")

    print("\n3. THE SEED -- the rule FINDINGS 43 paid a client run for")
    ridged = ridged_heights()
    # Interior of the sawtooth: grid (5, 16), well away from any edge, so the
    # refusal below is about the SLOPE and not about running out of quad.
    IN_RIDGE = (480.0, 1536.0)
    refused, why = False, ""
    try:
        sb.check_seed(ridged, DIMS, DIMS, rect, IN_RIDGE)
    except sb.UnwalkableSeed as exc:
        refused, why = True, str(exc)
    check(refused, f"a seed on the sawtooth is REFUSED  {IN_RIDGE}")
    check("segments->Count()" in why,
          "and the message names the assert it prevents, so the next person "
          "does not have to diff four chunks to find out why")
    # The positive control. A guard that refuses every seed protects nothing.
    ok_slope = sb.check_seed(ridged, DIMS, DIMS, rect, (2112.0, 1536.0))
    check(ok_slope == 0.0,
          f"CONTROL: a seed in the flat half is accepted, slope "
          f"{ok_slope:.1f} deg")
    check(sb.check_seed(flat_heights(), DIMS, DIMS, rect, IN_RIDGE) == 0.0,
          "CONTROL: and the SAME POINT is accepted on flat ground -- so the "
          "rule is about the slope under it, not about where it is")
    # FINDINGS 43's literal seed, and the reason cell_of clamps: (0,0) is on
    # the rect's minimum y, which divides to row dim_y. It is INSIDE the map.
    check(sb.cell_of(rect, (0.0, 0.0), DIMS, DIMS) == (0, DIMS - 1),
          "the (0,0) corner resolves to a real cell rather than one past the "
          "end -- grid row 0 is world maxY, so this is the trap")
    corner = False
    try:
        sb.check_seed(ridged, DIMS, DIMS, rect, (0.0, 0.0))
    except sb.UnwalkableSeed:
        corner = True
    check(corner, "and FINDINGS 43's own seed is still refused")
    # Off the map is refused too, and for its own reason.
    off = False
    try:
        sb.check_seed(ridged, DIMS, DIMS, rect, (99999.0, 0.0))
    except sb.UnwalkableSeed:
        off = True
    check(off, "a seed outside the rect is refused")
    steep = sb.quad_slope_deg(ridged, DIMS, DIMS, 2, 2)
    check(steep > 80.0,
          f"the sawtooth really is near-vertical: {steep:.1f} deg")
    check(sb.quad_slope_deg(flat_heights(), DIMS, DIMS, 2, 2) == 0.0,
          "and flat ground really is flat")
    check(sb.quad_slope_deg(ridged, DIMS, DIMS, DIMS - 1, 0) == 90.0,
          "the far edge has no quad and reports 90, not a number invented "
          "from one row")

    print("\n3b. build() refuses without constants, rather than inventing them")
    refused = False
    try:
        sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0), {},
                 PLACEHOLDER_IDS)
    except sb.NoConstants:
        refused = True
    check(refused, "build() with no borrowed chunks raises NoConstants")
    missing = False
    try:
        sb.borrowed_constants(path=os.path.join(HERE, "no-such-archive.dat"))
    except sb.NoConstants:
        missing = True
    check(missing, "and borrowed_constants() refuses a path that is not there")

    print("\n3c. the census, on placeholders")
    rep = sb.build(DIMS, DIMS, ridged, (2112.0, 1536.0), PLACEHOLDER,
                   PLACEHOLDER_IDS)
    check(rep.borrowed == 54,
          f"borrowed is exactly the three chunks' 54 B  ({rep.borrowed})")
    check(rep.borrowed_chunks() == sb.BORROWED,
          "and the report NAMES them rather than giving one percentage")
    check(rep.fraction_generated > 0.95,
          f"generated fraction {100 * rep.fraction_generated:.2f}%")
    check(sum(rep.sizes.values()) == rep.generated + rep.borrowed,
          "and the census accounts for every chunk byte")
    check(len(rep.blob) > sum(rep.sizes.values()),
          "the file is larger than its payloads -- there is a chunk table")

    print("\n4. against the archive: the borrowed three and the generated deps")
    try:
        dat = os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    except Exception as exc:
        LEDGER.skip(f"sections 4-6 need vault/dat_study/Gw.dat: {exc}")
        return
    constants, dep_ids = sb.borrowed_constants(path=dat)
    check(set(constants) == set(sb.BORROWED),
          "the three borrowed chunks read back")
    check([len(constants[c]) for c in sb.BORROWED] == [8, 12, 34],
          f"at their measured sizes  "
          f"{[len(constants[c]) for c in sb.BORROWED]}")
    check(len(dep_ids) == 4 and all(isinstance(i, int) for i in dep_ids),
          f"and the dependency ids come back as NUMBERS  {dep_ids}")

    with Archive(dat) as ar:
        e = next(x for x in ar.entries if x.index == sb.REFERENCE_PARTNER)
        donor = bytes(ar.read(e))
    donor_deps = None
    from archive import ffna_chunks
    for cid, off, size in ffna_chunks(donor):
        if cid == sb.TERRAIN_DEPS:
            donor_deps = bytes(donor[off:off + size])
    ours = mapchunks.encode_dependencies(dep_ids)
    check(ours == donor_deps,
          f"OUR generated dependency chunk is byte-identical to ArenaNet's "
          f"({len(ours)} B) -- a check the archive could have failed")

    print("\n5. provenance: no ArenaNet bytes in this module's source")
    src = open(sb.__file__, encoding="utf-8").read()
    big = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
            if len(node.value) > 2:
                big.append(node.value)
    check(not big,
          f"no bytes literal over two bytes in stripbuild.py  "
          f"({len(big)} found)")
    # The docstring trap: a syntax-tree scan cannot see prose.
    hits = []
    for cid, blob_ in constants.items():
        forms = [blob_.hex(), blob_.hex(" "),
                 "".join(f"\\x{b:02x}" for b in blob_)]
        for f in forms:
            if len(f) > 8 and f.lower() in src.lower():
                hits.append(f"0x{cid:08X}")
    check(not hits,
          f"and none of the borrowed payloads appears in the source in any "
          f"form, docstrings included  {hits}")

    print("\n6. the whole build, on the real constants")
    rep = sb.build(DIMS, DIMS, ridged, (2112.0, 1536.0), constants, dep_ids)
    check(rep.borrowed == 54 and rep.generated > 2000,
          f"generated {rep.generated} B, borrowed {rep.borrowed} B")
    check(rep.fraction_generated > 0.97,
          f"{100 * rep.fraction_generated:.2f}% generated")
    mf = mapfile.MapFile.decode(rep.blob)
    check([c.chunk_id for c in mf.chunks] == list(sb.ORDER),
          "the assembled map carries exactly the seven, in ORDER")
    check(mf.encode() == rep.blob, "and round-trips")
    again = stx.StrippedTerrain.decode(
        next(c for c in mf.chunks if c.chunk_id == sb.TERRAIN).payload())
    check(again.heights == [float(v) for v in ridged],
          "the authored height field survives, sample for sample")
    sp = pathchunk.StrippedPath.from_chunk(
        next(c for c in mf.chunks if c.chunk_id == sb.PATH).payload())
    check(sp.boundary == [(2112.0, 1536.0)],
          f"and the seed is where we put it  {sp.boundary}")
    check(len(rep.blob) < 4608,
          f"the whole map is {len(rep.blob)} B, inside the reservation a "
          f"32x32 map row has -- which is what makes it writable at all")


def main():
    sections()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
