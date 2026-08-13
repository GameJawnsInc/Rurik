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
back to something. Sections 4-6 need `vault/dat_study/Gw.dat`, and score 41
against a floor of 54 without it -- a number that could not be observed at all
until the SystemExit bug in section 4's vault gate was fixed on 2026-08-12.

SECTION 3D IS THE PROPS-DEPS PAIRING (2026-08-12, for rung e10d): a build
placing a prop must list its model file ids for chunk 0x11000004 -- `model` is
an INDEX into that list -- and a build without props must not. Both directions
refuse, the positive control carries all eight chunks with the deps chunk
immediately after props (retail's slot), and a model index past the list is
refused because the client's failure mode for an unresolvable model has never
been measured.

SECTION 3E IS THE ENVIRONMENT PAIR (2026-08-13, rung e10i): `env_payload`
and `env_dep_ids` go together or not at all, the pair lands after the Path
chunk in retail's slot, and the payload counts BORROWED in the census -- the
chunk is not understood, and a borrowed byte reporting as generated is a
census lie. FINDINGS 51's run carried a borrowed environment VERBATIM
through the compiler and it brought the sky; FINDINGS 52's did the same
for the SOUND pair and the map played Pre-Searing's birds and wind.

THE BORROWED SET SHRANK on 2026-08-12: props is GENERATED now, by `props.py`,
so `BORROWED` is Header and Zones alone -- 42 bytes, down from 54, and 98.20%
of the map generated. Section 3c asserts that props is in `GENERATED` and not
in `BORROWED`, because the number moving is the least of it: props is
FINDINGS 34's hard gate, and while it was borrowed no map from this module
could place an object in the world.

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
import props  # noqa: E402
import stripbuild as sb  # noqa: E402
import strippedterrain as stx  # noqa: E402
import terrain as trn_mod  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR: 51, MEASURED from a green run on 2026-08-13 (guessed 44 first, which
# reddened the run at 39 -- which is what the floor is for; 40 since props left
# the borrowed set, 46 since section 3d pinned the props-deps pairing, 51
# since 3e pinned the environment pair, 54 since 3e grew the sound pair).
# Sections 0 to 3e score 41 and need no vault, so a vault-less run goes red
# rather than reporting a smaller success -- the corpus half is where
# "byte-identical to ArenaNet's" lives.
#
# 27 is MEASURED too, and it had to be: the vault-less path could not run at
# all until 2026-08-12. `vaultpath.require_dir` raises SystemExit, a
# BaseException, so the `except Exception` guarding it never fired and the run
# died before the verdict -- and the `LEDGER.skip` in that handler had never
# executed once, being called with one argument where it takes two. The 30 this
# comment used to claim was a number nobody had ever seen printed.
LEDGER = checks.Ledger("stripbuild", floor=54)
check = checks.adopt(LEDGER)

DIMS = 32
FLAT = -13
RAISE = -1000
SPLIT = 12

# Ours, and deliberately not ArenaNet's: two payloads of the right SHAPE and
# the wrong content, so sections 0-3 exercise the whole builder with no vault.
# Props left this dict on 2026-08-12 when `props.py` learned to generate it.
PLACEHOLDER = {
    sb.HEADER: bytes(8),
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
    payload[sb.PROPS] = props.StrippedProps.minimal().encode()
    payload[sb.TERRAIN] = stx.StrippedTerrain.build(
        DIMS, DIMS, flat_heights()).encode()
    payload[sb.TERRAIN_DEPS] = mapchunks.encode_dependencies(PLACEHOLDER_IDS)
    payload[sb.PATH] = pathchunk.StrippedPath(
        boundary=[(1536.0, 1536.0)]).encode()
    blob = sb.encode(payload)
    ids = [c.chunk_id for c in mapfile.MapFile.decode(blob).chunks]
    check(ids == [c for c in sb.ORDER if c not in sb.OPTIONAL],
          f"encode() emits ORDER  {len(ids)} chunks -- no props and no env, "
          f"so none of the OPTIONAL chunks, which is retail's own pairing")
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
    check(rep.borrowed == 42,
          f"borrowed is exactly the two chunks' 42 B  ({rep.borrowed})")
    check(sb.PROPS not in sb.BORROWED and sb.PROPS in sb.GENERATED,
          "and the props chunk is GENERATED, not borrowed",
          "FINDINGS 34's hard gate; while it was borrowed no map from this "
          "module could place an object")
    check(rep.borrowed_chunks() == sb.BORROWED,
          "and the report NAMES them rather than giving one percentage")
    check(rep.fraction_generated > 0.95,
          f"generated fraction {100 * rep.fraction_generated:.2f}%")
    check(sum(rep.sizes.values()) == rep.generated + rep.borrowed,
          "and the census accounts for every chunk byte")
    check(len(rep.blob) > sum(rep.sizes.values()),
          "the file is larger than its payloads -- there is a chunk table")

    print("\n3d. props and their model list are PAIRED, the way retail "
          "pairs them")
    one_prop = props.StrippedProps(
        props=[props.Prop(0, 1536.0, 1536.0, float(FLAT))],
        refs4=(), refs6=None)
    refused = False
    try:
        sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0), PLACEHOLDER,
                 PLACEHOLDER_IDS, props=one_prop)
    except ValueError:
        refused = True
    check(refused,
          "a build placing a prop with NO prop_dep_ids is refused",
          "`model` is an index into 0x11000004; a map that does not list the "
          "model cannot resolve it, and the client failure mode is unmeasured")
    refused = False
    try:
        sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0), PLACEHOLDER,
                 PLACEHOLDER_IDS, prop_dep_ids=[77])
    except ValueError:
        refused = True
    check(refused,
          "and a prop_dep_ids list with NO props is refused too",
          "the three zero-prop retail maps are exactly the three without the "
          "chunk, so this configuration has no retail precedent")
    refused = False
    try:
        sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0), PLACEHOLDER,
                 PLACEHOLDER_IDS,
                 props=props.StrippedProps(
                     props=[props.Prop(3, 1536.0, 1536.0, float(FLAT))],
                     refs4=(), refs6=None),
                 prop_dep_ids=[77])
    except ValueError:
        refused = True
    check(refused,
          "a model index past the end of the list is refused",
          "index 3 into a one-entry list")
    rep_p = sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0),
                     PLACEHOLDER, PLACEHOLDER_IDS, props=one_prop,
                     prop_dep_ids=[77])
    ids_p = [c.chunk_id for c in mapfile.MapFile.decode(rep_p.blob).chunks]
    check(ids_p == [c for c in sb.ORDER
                    if c == sb.PROPS_DEPS or c not in sb.OPTIONAL],
          f"POSITIVE CONTROL: a props-bearing build carries the props-deps "
          f"chunk in ORDER (and no other optional pair it was not given)")
    check(ids_p.index(sb.PROPS_DEPS) == ids_p.index(sb.PROPS) + 1,
          "and the props-deps chunk rides immediately after the props chunk, "
          "where retail puts it")
    dep_chunk = next(c for c in mapfile.MapFile.decode(rep_p.blob).chunks
                     if c.chunk_id == sb.PROPS_DEPS)
    back_ids = list(mapchunks.decode_dependencies(
        dep_chunk.payload()).file_ids)
    check(back_ids == [77],
          f"the generated list decodes back to the same file id  {back_ids}")

    print("\n3e. the environment pair goes together, or not at all")
    refused = False
    try:
        sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0), PLACEHOLDER,
                 PLACEHOLDER_IDS, env_payload=b"\x00" * 16)
    except ValueError:
        refused = True
    check(refused, "an env payload with NO id list is refused")
    refused = False
    try:
        sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0), PLACEHOLDER,
                 PLACEHOLDER_IDS, env_dep_ids=[9])
    except ValueError:
        refused = True
    check(refused, "an env id list with NO payload is refused")
    rep_e = sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0),
                     PLACEHOLDER, PLACEHOLDER_IDS,
                     env_payload=b"\x00" * 16, env_dep_ids=[9])
    ids_e = [c.chunk_id for c in mapfile.MapFile.decode(rep_e.blob).chunks]
    check(ids_e == [c for c in sb.ORDER
                    if c in (sb.ENV, sb.ENV_DEPS) or c not in sb.OPTIONAL],
          "POSITIVE CONTROL: the pair lands after the Path chunk, in ORDER")
    check(rep_e.origin[sb.ENV] == "borrowed"
          and sb.ENV not in sb.GENERATED,
          "and the env payload is counted BORROWED",
          "the chunk is not understood; a borrowed byte that reports as "
          "generated is a census lie")
    check(rep_e.borrowed == 42 + 16,
          f"the census moves by exactly the payload  ({rep_e.borrowed})")
    refused = False
    try:
        sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0), PLACEHOLDER,
                 PLACEHOLDER_IDS, sound_payload=bytes(1) * 8)
    except ValueError:
        refused = True
    check(refused, "a sound payload with NO id list is refused")
    rep_s = sb.build(DIMS, DIMS, flat_heights(), (1536.0, 1536.0),
                     PLACEHOLDER, PLACEHOLDER_IDS,
                     env_payload=bytes(1) * 16, env_dep_ids=[9],
                     sound_payload=bytes(1) * 8, sound_dep_ids=[5])
    ids_s = [c.chunk_id for c in mapfile.MapFile.decode(rep_s.blob).chunks]
    check(ids_s == [c for c in sb.ORDER if c != sb.PROPS_DEPS],
          "POSITIVE CONTROL: env and sound pairs both land in ORDER")
    check(rep_s.origin[sb.SOUND] == "borrowed"
          and rep_s.borrowed == 42 + 16 + 8,
          f"and the sound payload counts BORROWED  ({rep_s.borrowed})")

    print("\n4. against the archive: the borrowed two and the generated deps")
    # NOT `require_dir`, and that is the fix rather than the style. It raises
    # SystemExit, which is a BaseException -- so `except Exception` never caught
    # it, a vault-less run died here without ever printing a verdict, and the
    # `LEDGER.skip` below had never once executed (it was called with one
    # argument where `skip(label, why)` takes two, so it would have raised
    # TypeError the first time it ran). The docstring's "sections 0-3c score 30
    # against a floor of 39" was therefore a number nobody had seen.
    dat = os.path.join(vaultpath.vault_path("dat_study"), "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("sections 4-6, which need the archive",
                    f"no Gw.dat at {dat}; vault resolved to "
                    f"{vaultpath.vault_root()} ({vaultpath.vault_why()}). "
                    f"Sections 0-3c measured the builder against placeholder "
                    f"constants of our own and NOTHING about ArenaNet's.")
        return
    constants, dep_ids = sb.borrowed_constants(path=dat)
    check(set(constants) == set(sb.BORROWED),
          "the two borrowed chunks read back")
    check([len(constants[c]) for c in sb.BORROWED] == [8, 34],
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
    check(rep.borrowed == 42 and rep.generated > 2000,
          f"generated {rep.generated} B, borrowed {rep.borrowed} B")
    check(rep.fraction_generated > 0.97,
          f"{100 * rep.fraction_generated:.2f}% generated")
    mf = mapfile.MapFile.decode(rep.blob)
    check([c.chunk_id for c in mf.chunks]
          == [c for c in sb.ORDER if c not in sb.OPTIONAL],
          "the assembled map carries exactly the seven, in ORDER -- a "
          "zero-prop, no-env map has none of the OPTIONAL chunks")
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
